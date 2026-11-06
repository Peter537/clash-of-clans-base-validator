"""Prepared artifact families recover previous bytes after handled write failures."""

from contextlib import redirect_stderr, redirect_stdout
import importlib
from io import StringIO
from pathlib import Path
import unittest
from unittest.mock import patch

import coc_base.io as bundle_io
from coc_base.__main__ import main
from coc_base.export import export
from coc_base.io import OutputError, _publish_text_files, load_bundle, read_json
from test_project import ROOT, temporary_directory


class OutputPublicationTests(unittest.TestCase):
    def test_successful_replacement_preserves_unrelated_files_and_exact_text(self):
        with temporary_directory() as directory:
            existing, created, preview = (directory / name for name in ("old.txt", "new.csv", "preview.html"))
            existing.write_bytes(b"previous\r\n")
            preview.write_bytes(b"keep this preview")
            self.assertEqual(_publish_text_files({existing: "updated\n", created: "a,b\r\n1,2\r\n"}), [])
            self.assertEqual(existing.read_bytes(), b"updated\n")
            self.assertEqual(created.read_bytes(), b"a,b\r\n1,2\r\n")
            self.assertEqual(preview.read_bytes(), b"keep this preview")
            self.assertEqual(set(p.name for p in directory.iterdir()), {"old.txt", "new.csv", "preview.html"})

    def test_staging_and_backup_failures_leave_existing_bytes_unchanged(self):
        for failure in ("write", "backup"):
            with self.subTest(failure=failure), temporary_directory() as directory:
                existing, created = directory / "old.txt", directory / "new.txt"
                existing.write_bytes(b"previous bytes")
                if failure == "write":
                    real_write = Path.write_text

                    def write(path, *args, **kwargs):
                        if path.name == "new-1":
                            raise OSError("injected staging failure")
                        return real_write(path, *args, **kwargs)

                    failure_patch = patch.object(Path, "write_text", write)
                else:
                    failure_patch = patch("coc_base.io.shutil.copy2", side_effect=OSError("injected backup failure"))
                with failure_patch, self.assertRaisesRegex(OutputError, "Previous outputs restored"):
                    _publish_text_files({existing: "new bytes", created: "created"})
                self.assertEqual(existing.read_bytes(), b"previous bytes")
                self.assertFalse(created.exists())
                self.assertEqual(list(directory.iterdir()), [existing])

    def test_replacement_failure_restores_old_files_and_removes_new_files(self):
        with temporary_directory() as directory:
            first, new, third, preview = (directory / name for name in ("a.txt", "b.txt", "c.txt", "preview.html"))
            first.write_bytes(b"original a")
            third.write_bytes(b"original c")
            preview.write_bytes(b"unrelated")
            real_replace = bundle_io.os.replace

            def replace(source, destination):
                if Path(source).name == "new-2":
                    raise OSError("injected third replacement failure")
                return real_replace(source, destination)

            with patch("coc_base.io.os.replace", replace), self.assertRaisesRegex(OutputError, "Previous outputs restored"):
                _publish_text_files({first: "changed a", new: "created b", third: "changed c"})
            self.assertEqual(first.read_bytes(), b"original a")
            self.assertEqual(third.read_bytes(), b"original c")
            self.assertEqual(preview.read_bytes(), b"unrelated")
            self.assertFalse(new.exists())
            self.assertEqual(set(p.name for p in directory.iterdir()), {"a.txt", "c.txt", "preview.html"})

    def test_failed_restoration_retains_recovery_copy_and_reports_target(self):
        with temporary_directory() as directory:
            first, new, third = (directory / name for name in ("a.txt", "b.txt", "c.txt"))
            first.write_bytes(b"original a")
            real_replace = bundle_io.os.replace

            def replace(source, destination):
                if Path(source).name in {"new-2", "old-0"}:
                    raise OSError("injected replacement or restoration failure")
                return real_replace(source, destination)

            with patch("coc_base.io.os.replace", replace), self.assertRaises(OutputError) as caught:
                _publish_text_files({first: "changed a", new: "created b", third: "created c"})
            recovery = caught.exception.recovery_directory
            self.assertTrue(recovery.is_dir())
            self.assertEqual(recovery.parent, directory.resolve())
            self.assertEqual((recovery / "old-0").read_bytes(), b"original a")
            self.assertIn(str(recovery), str(caught.exception))
            self.assertIn(str(first), str(caught.exception))
            self.assertIn("Recovery required", str(caught.exception))
            self.assertFalse(new.exists())
            self.assertFalse(third.exists())

    def test_cleanup_failure_returns_warning_and_cli_preserves_model_exit(self):
        layout, rules, profile = load_bundle(ROOT / "examples/th3-hi/layout.json", historical=True)
        with temporary_directory() as directory:
            with patch("coc_base.io._remove_stage", side_effect=OSError("injected cleanup failure")):
                result = export(layout, rules, profile, directory / "bundle")
                stdout, stderr = StringIO(), StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    code = main(["render", str(ROOT / "examples/th3-hi/layout.json"), "--historical",
                                 "--output", str(directory / "preview.html")])
            self.assertEqual(result["status"], "PASS")
            self.assertIn("Outputs published", result["output_warnings"][0])
            self.assertEqual(read_json(directory / "bundle/validation.json")["status"], "PASS")
            self.assertEqual(code, 0)
            self.assertIn("Output warning:", stderr.getvalue())
            self.assertNotIn("Input error:", stderr.getvalue())
            self.assertTrue((directory / "preview.overhead.svg").is_file())

    def test_output_failures_are_labelled_and_keep_exit_three(self):
        render_module = importlib.import_module("coc_base.render")
        stdout, stderr = StringIO(), StringIO()
        with patch.object(render_module, "_publish_text_files", side_effect=OutputError("injected publication failure")):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = main(["render", str(ROOT / "examples/th3-hi/layout.json"), "--historical", "--output", "unused.html"])
        self.assertEqual(code, 3)
        self.assertIn("Output error:", stderr.getvalue())
        self.assertNotIn("Input error:", stderr.getvalue())

    def test_invalid_utf8_and_directory_targets_fail_before_staging(self):
        with temporary_directory() as directory:
            destination = directory / "absent"
            with self.assertRaises(UnicodeError):
                _publish_text_files({destination / "bad.txt": "\ud800"})
            self.assertFalse(destination.exists())
            with self.assertRaises(OutputError):
                _publish_text_files({directory: "cannot overwrite directory"})
            self.assertEqual(list(directory.iterdir()), [])


if __name__ == "__main__":
    unittest.main()

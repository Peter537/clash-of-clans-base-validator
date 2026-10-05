"""Check the public boundary in disposable repositories, never the workspace index."""

from pathlib import Path
import shutil
import subprocess
import unittest

from tools.check_docs import check
from tools.public_files import public_files
from test_accounts import public_checkout
from test_project import ROOT, temporary_directory


class PublicationTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("git"), "Git is needed for ignore-pattern verification")
    def test_ignore_patterns_in_temporary_git_repository(self):
        with temporary_directory() as directory:
            public_checkout(directory)
            ignored = [f"{name}/private.txt" for name in
                       ("reports", "layouts", "exports", ".skill-evaluation", "profiles", ".test-work")]
            ignored += ["coc_base/__pycache__/module.pyc", ".venv/private.txt"]
            for name in ignored:
                target = directory / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("synthetic disposable data", encoding="utf-8")
            run = subprocess.run(["git", "init", "--quiet", str(directory)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            for name in ignored:
                result = subprocess.run(["git", "check-ignore", "--no-index", name], cwd=directory,
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, name)
            visible = [p.relative_to(directory).as_posix() for p in public_files(directory)]
            result = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=directory,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(set(result.stdout.splitlines()), set(visible))
            self.assertIn("examples/th3-hi/layout.json", visible)
            self.assertIn("rulesets/current.json", visible)
            self.assertIn(".agents/skills/coc-name-base/SKILL.md", visible)
            self.assertIn("tests/test_accounts.py", visible)

    def test_documentation_check_ignores_private_content_and_rejects_links(self):
        with temporary_directory() as directory:
            public_checkout(directory)
            archived = directory / "reports/archive.md"
            archived.parent.mkdir()
            archived.write_text("[old link](missing-private-file.md)", encoding="utf-8")
            self.assertEqual(check(directory), [])
            readme = directory / "README.md"
            original = readme.read_text(encoding="utf-8")
            readme.write_text(original + "\n[private archive](reports/archive.md)\n", encoding="utf-8")
            self.assertTrue(any("non-public" in message for message in check(directory)))
            readme.write_text(original + "\n[bad anchor](docs/accounts.md#missing-heading)\n", encoding="utf-8")
            self.assertTrue(any("Broken anchor" in message for message in check(directory)))

    def test_public_files_exclude_private_root_directories(self):
        paths = [p.relative_to(ROOT) for p in public_files(ROOT)]
        excluded = {"reports", "layouts", "exports", ".skill-evaluation", "profiles", ".test-work"}
        self.assertFalse(any(p.parts[0] in excluded or "__pycache__" in p.parts for p in paths))
        self.assertTrue(all((ROOT / p).is_file() for p in paths))


if __name__ == "__main__":
    unittest.main()

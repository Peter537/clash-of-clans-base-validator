"""Complete review preparation preserves validated inputs and portable identities."""

from copy import deepcopy
import csv
from html import escape
from io import StringIO
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from coc_base.export import _prepare_export, export, export_paths
from coc_base.io import digest, load_bundle, read_json
from coc_base.render import _prepare_render, render, render_paths
from test_project import ROOT, temporary_directory


class ReviewOutputTests(unittest.TestCase):
    def setUp(self):
        self.layout, self.rules, self.profile = load_bundle(ROOT / "examples/th3-hi/layout.json", historical=True)

    def test_preparation_has_no_filesystem_effects_and_preserves_input_identity(self):
        original = deepcopy((self.layout, self.rules, self.profile))
        with (patch.object(Path, "mkdir", side_effect=AssertionError("mkdir during preparation")),
              patch.object(Path, "open", side_effect=AssertionError("open during preparation")),
              patch.object(Path, "write_text", side_effect=AssertionError("write during preparation"))):
            source, bundle = _prepare_export(self.layout, self.rules, self.profile, "unused-bundle")
            shown, preview = _prepare_render(self.layout, self.rules, self.profile, "unused.html")
        self.assertEqual(set(bundle), set(export_paths("unused-bundle")))
        self.assertEqual(set(preview), set(render_paths("unused.html")))
        for contents in (bundle, preview):
            for path, text in contents.items():
                self.assertIsInstance(path, Path)
                self.assertIsInstance(text, str)
                text.encode("utf-8")
        portable = json.loads(bundle[Path("unused-bundle/layout.json")])
        saved = json.loads(bundle[Path("unused-bundle/validation.json")])
        self.assertEqual(source["layout_sha256"], digest(self.layout))
        self.assertEqual(shown["layout_sha256"], digest(self.layout))
        self.assertEqual(saved["layout_sha256"], digest(portable))
        self.assertNotEqual(saved["layout_sha256"], source["layout_sha256"])
        self.assertEqual(portable["objects"], self.layout["objects"])
        self.assertEqual((self.layout, self.rules, self.profile), original)

    def test_invalid_and_unresolved_models_publish_complete_review_families(self):
        for state in ("INVALID", "UNRESOLVED"):
            with self.subTest(state=state), temporary_directory() as directory:
                layout, rules = deepcopy(self.layout), deepcopy(self.rules)
                wall = next(obj for obj in layout["objects"] if obj["type"] == "wall")
                if state == "INVALID":
                    wall["x"] = "unusable coordinate"
                else:
                    rules["objects"]["wall"]["status"] = "unverified"
                original = deepcopy((layout, rules, self.profile))
                bundle, preview = directory / "bundle", directory / "preview.html"
                exported = export(layout, rules, self.profile, bundle)
                shown = render(layout, rules, self.profile, preview)
                self.assertEqual(exported["status"], state)
                self.assertEqual(shown["status"], state)
                self.assertEqual({path.name for path in bundle.iterdir()}, {path.name for path in export_paths(bundle)})
                self.assertTrue(all(path.is_file() for path in render_paths(preview)))
                self.assertEqual(read_json(bundle / "validation.json")["status"], state)
                self.assertEqual(read_json(preview.with_suffix(".validation.json"))["status"], state)
                self.assertEqual(read_json(bundle / "layout.json")["objects"], layout["objects"])
                csv_bytes = (bundle / "coordinates.csv").read_bytes()
                self.assertNotIn(b"\r\r\n", csv_bytes)
                rows = list(csv.DictReader(StringIO(csv_bytes.decode("utf-8"))))
                self.assertEqual(len(rows), len(layout["objects"]))
                if state == "INVALID":
                    self.assertEqual(next(row for row in rows if row["id"] == wall["id"])["x"], wall["x"])
                    self.assertIn(wall["id"], (bundle / "construction.md").read_text(encoding="utf-8"))
                self.assertEqual((layout, rules, self.profile), original)

    def test_selected_rules_notice_survives_preparation(self):
        notice = "Current rules metadata unavailable: <missing selector>"
        context = {"rules_mode": "historical", "current_ruleset_id": None, "current_ruleset_notice": notice}
        result, bundle = _prepare_export(self.layout, self.rules, self.profile, "bundle", context=context)
        shown, preview = _prepare_render(self.layout, self.rules, self.profile, "preview.html", context=context)
        self.assertEqual(result["current_ruleset_notice"], notice)
        self.assertEqual(shown["current_ruleset_notice"], notice)
        self.assertIn(notice, bundle[Path("bundle/construction.md")])
        self.assertIn(escape(notice), preview[Path("preview.html")])
        self.assertEqual(json.loads(bundle[Path("bundle/validation.json")])["current_ruleset_notice"], notice)

    def test_structurally_invalid_inputs_still_fail_before_publication(self):
        for changes in ({"objects": ["invalid record"]}, {"objects": None}, {"visual_review": None}):
            with self.subTest(changes=changes):
                layout = dict(self.layout, **changes)
                for function, module, output in ((export, "coc_base.export", "unused-bundle"),
                                                  (render, "coc_base.render", "unused.html")):
                    with patch(f"{module}._publish_text_files") as publish:
                        with self.assertRaises(ValueError):
                            function(layout, self.rules, self.profile, output)
                        publish.assert_not_called()

    def test_csv_preparation_failure_leaves_existing_bundle_untouched(self):
        with temporary_directory() as directory:
            bundle = directory / "bundle"
            bundle.mkdir()
            for path in export_paths(bundle):
                path.write_bytes(b"previous output")
            with patch("coc_base.export.csv.DictWriter.writerow", side_effect=OSError("CSV preparation failed")):
                with self.assertRaisesRegex(OSError, "CSV preparation failed"):
                    export(self.layout, self.rules, self.profile, bundle)
                absent = directory / "absent/bundle"
                with self.assertRaises(OSError):
                    export(self.layout, self.rules, self.profile, absent)
            self.assertTrue(all(path.read_bytes() == b"previous output" for path in export_paths(bundle)))
            self.assertEqual(len(list(bundle.iterdir())), 6)
            self.assertFalse(absent.parent.exists())


if __name__ == "__main__":
    unittest.main()

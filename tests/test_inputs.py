"""Input rejection, safe diagnostic artifacts, and independent rule selections."""

from copy import deepcopy
from html import escape
from html.parser import HTMLParser
import csv
import unittest
import xml.etree.ElementTree as ET

from coc_base.export import export
from coc_base.io import load_bundle, read_json, write_json
from coc_base.profiles import create_profile
from coc_base.render import render
from coc_base.validate import validate
from test_accounts import cli, public_checkout
from test_project import ROOT, temporary_directory


class HTMLNodes(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.attributes = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attributes.extend(name for name, value in attrs)


class InputTests(unittest.TestCase):
    def setUp(self):
        self.layout, self.rules, self.profile = load_bundle(ROOT / "examples/th3-hi/layout.json")

    def malformed_inputs(self):
        yield "objects array", "layout", {"objects": None}
        yield "object entry", "layout", {"objects": [None]}
        yield "review object", "layout", {"visual_review": None}
        yield "review views", "layout", {"visual_review": {"views": "overhead"}}
        yield "name type", "layout", {"name": None}
        yield "Town Hall type", "layout", {"town_hall": 3.0}
        yield "reservation array", "layout", {"reserved_areas": None}
        for value in (None, "wallpaper", [None], {"wall": True}):
            area = {"x": 0, "y": 0, "width": 44, "height": 44, "allow_types": value}
            yield f"reservation permissions {value!r}", "layout", {"reserved_areas": [area]}
            yield f"blocker permissions {value!r}", "profile", {"blocked_areas": [area]}
        for field, value in (("group", None), ("settings", []), ("type", [])):
            objects = deepcopy(self.layout["objects"])
            objects[0][field] = value
            yield field, "layout", {"objects": objects}
        yield "inventory object", "profile", {"inventory": []}
        inventory = dict(self.profile["inventory"], wall="<script>unsafe()</script>")
        yield "inventory count", "profile", {"inventory": inventory}
        yield "level distribution", "profile", {"level_inventory": {"wall": []}}
        for document in ("layout", "profile", "rules"):
            for value in (True, 1.0, "1", 2):
                yield f"{document} schema {value!r}", document, {"schema_version": value}
        yield "profile Town Hall", "profile", {"town_hall": True}
        yield "object rules", "rules", {"objects": dict(self.rules["objects"], wall=None)}
        yield "merger rules", "rules", {"mergers": {"merged": {"consumes": None}}}
        yield "banner rules", "rules", {"banner_slots": [None]}
        yield "phase rules", "rules", {"crafted_phase": None}
        yield "uncertainty rules", "rules", {"uncertainties": [None]}
        specs = deepcopy(self.rules["objects"])
        specs["wall"]["settings"] = None
        yield "settings rules", "rules", {"objects": specs}

    def test_malformed_inputs_rejected_before_direct_output(self):
        with temporary_directory() as directory:
            for name, document, changes in self.malformed_inputs():
                with self.subTest(name=name):
                    inputs = {"layout": deepcopy(self.layout), "rules": deepcopy(self.rules),
                              "profile": deepcopy(self.profile)}
                    inputs[document].update(changes)
                    args = inputs["layout"], inputs["rules"], inputs["profile"]
                    with self.assertRaises(ValueError):
                        validate(*args)
                    output = directory / "new/report.html"
                    with self.assertRaises(ValueError):
                        render(*args, output)
                    self.assertFalse(output.parent.exists())
                    bundle = directory / "new-bundle"
                    with self.assertRaises(ValueError):
                        export(*args, bundle)
                    self.assertFalse(bundle.exists())

    def test_cli_rejects_malformed_inputs_without_overwriting_artifacts(self):
        with temporary_directory() as directory:
            originals = {"layout": self.layout, "rules": self.rules, "profile": self.profile}
            for name, document, changes in self.malformed_inputs():
                with self.subTest(name=name):
                    inputs = deepcopy(originals)
                    inputs[document].update(changes)
                    inputs["layout"].update(ruleset="rules.json", profile="profile.json")
                    for key in originals:
                        write_json(directory / f"{key}.json", inputs[key])
                    report = directory / "report.html"
                    report.write_text("existing report", encoding="utf-8")
                    bundle = directory / "bundle"
                    bundle.mkdir(exist_ok=True)
                    sentinel = bundle / "layout.json"
                    sentinel.write_text("existing bundle", encoding="utf-8")
                    for command, output in (("validate", directory / "diagnostics.json"),
                                            ("render", report), ("export", bundle)):
                        flags = ["--json" if command == "validate" else "--output", output]
                        run = cli(ROOT, command, directory / "layout.json", "--historical", *flags)
                        self.assertEqual(run.returncode, 3, run.stdout + run.stderr)
                        self.assertNotIn("Traceback", run.stderr)
                    self.assertFalse((directory / "diagnostics.json").exists())
                    self.assertEqual(report.read_text(encoding="utf-8"), "existing report")
                    self.assertFalse(report.with_suffix(".validation.json").exists())
                    self.assertEqual(sentinel.read_text(encoding="utf-8"), "existing bundle")
                    self.assertEqual([p.name for p in bundle.iterdir()], ["layout.json"])

    def test_profile_creation_rejects_malformed_area_permissions(self):
        for permissions in (None, "wall", [None]):
            account = {"inventory": {"builders_hut": 2}, "blocked_areas": [
                {"x": 0, "y": 0, "width": 1, "height": 1, "allow_types": permissions}]}
            with self.subTest(permissions=permissions), self.assertRaises(ValueError):
                create_profile(self.rules, 3, account=account)
            with temporary_directory() as directory:
                input_path = directory / "account.json"
                output = directory / "profile.json"
                write_json(input_path, account)
                output.write_text("existing profile", encoding="utf-8")
                run = cli(ROOT, "profile", "create", "--town-hall", 3,
                          "--inventory", input_path, "--output", output)
                self.assertEqual(run.returncode, 3, run.stdout + run.stderr)
                self.assertNotIn("Traceback", run.stderr)
                self.assertEqual(output.read_text(encoding="utf-8"), "existing profile")

    def test_permitted_text_is_escaped_in_html_and_svg(self):
        marker = '\"><script>unsafe()</script><img onerror="unsafe()">'
        self.layout["name"] = marker
        self.layout["visual_review"] = {"conclusion": marker}
        self.layout["objects"][0]["id"] = marker
        self.layout["objects"][0]["level"] = marker
        self.layout["reserved_areas"] = [{"x": 0, "y": 0, "width": 1, "height": 1,
                                           "label": marker, "allow_types": ["wall"]}]
        self.rules["objects"]["wall"]["name"] = marker
        with temporary_directory() as directory:
            output = directory / "review.html"
            result = render(self.layout, self.rules, self.profile, output)
            self.assertEqual(result["status"], "INVALID")
            source = output.read_text(encoding="utf-8")
            self.assertIn(escape(marker), source)
            nodes = HTMLNodes()
            nodes.feed(source)
            self.assertNotIn("script", nodes.tags)
            self.assertNotIn("img", nodes.tags)
            self.assertNotIn("onerror", nodes.attributes)
            for view in ("isometric", "overhead"):
                tree = ET.fromstring(output.with_suffix(f".{view}.svg").read_text(encoding="utf-8"))
                self.assertTrue(any(node.attrib.get("data-id") == marker for node in tree.iter()))

    def test_unusable_wall_coordinates_remain_in_json_and_csv(self):
        for value in (None, True, "bad", [1], {"bad": 1}):
            with self.subTest(value=value), temporary_directory() as directory:
                layout = deepcopy(self.layout)
                wall = next(o for o in layout["objects"] if o["type"] == "wall")
                wall["x"] = value
                result = render(layout, self.rules, self.profile, directory / "review.html")
                self.assertEqual(result["status"], "INVALID")
                bundle = directory / "bundle"
                result = export(layout, self.rules, self.profile, bundle)
                self.assertEqual(result["status"], "INVALID")
                self.assertEqual(read_json(bundle / "layout.json")["objects"], layout["objects"])
                with (bundle / "coordinates.csv").open(encoding="utf-8", newline="") as stream:
                    rows = list(csv.DictReader(stream))
                self.assertEqual(len(rows), len(layout["objects"]))
                guide = (bundle / "construction.md").read_text(encoding="utf-8")
                self.assertIn("omitted", guide.lower())
                self.assertIn(wall["id"], guide)

    def test_missing_wall_coordinate_and_unknown_type_can_be_exported(self):
        wall = next(o for o in self.layout["objects"] if o["type"] == "wall")
        del wall["y"]
        self.layout["objects"].append({"id": "unknown", "type": "unreviewed-object", "x": 43, "y": 43})
        with temporary_directory() as directory:
            result = export(self.layout, self.rules, self.profile, directory)
            self.assertEqual(result["status"], "INVALID")
            self.assertEqual(read_json(directory / "layout.json")["objects"], self.layout["objects"])
            self.assertIn(wall["id"], (directory / "construction.md").read_text(encoding="utf-8"))


class IndependentSelectionTests(unittest.TestCase):
    def test_historical_and_explicit_survive_unavailable_current_rules(self):
        with temporary_directory() as directory:
            checkout = directory / "public"
            public_checkout(checkout)
            selector = checkout / "rulesets/current.json"
            original_selector = selector.read_bytes()
            rules_path = checkout / "rulesets/home-2026-10-04.json"
            for source in (None, "{ broken", '{"schema_version":true,"ruleset":"missing.json"}',
                           '{"schema_version":1,"ruleset":"missing.json"}'):
                with self.subTest(selector=source):
                    if source is None:
                        selector.unlink()
                    else:
                        selector.write_text(source, encoding="utf-8")
                    for mode, flags in (("historical", ["--historical"]),
                                        ("explicit", ["--ruleset", rules_path])):
                        for command in ("validate", "render", "export"):
                            output = directory / (f"{mode}-{command}.html" if command == "render"
                                                   else f"{mode}-{command}")
                            run = cli(checkout, command, "examples/th3-hi/layout.json", *flags,
                                      "--json" if command == "validate" else "--output", output)
                            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                            report_path = (output if command == "validate" else
                                           output.with_suffix(".validation.json") if command == "render"
                                           else output / "validation.json")
                            report = read_json(report_path)
                            self.assertEqual(report["rules_mode"], mode)
                            self.assertIsNone(report["current_ruleset_id"])
                            self.assertIn("current_ruleset_notice", report)
                            self.assertEqual(report["status"], "PASS")
                    output = directory / "default.json"
                    run = cli(checkout, "validate", "examples/th3-hi/layout.json", "--json", output)
                    self.assertEqual(run.returncode, 3, run.stdout + run.stderr)
                    self.assertFalse(output.exists())
                    selector.write_bytes(original_selector)


if __name__ == "__main__":
    unittest.main()

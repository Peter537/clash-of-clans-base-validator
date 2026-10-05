"""Synthetic account and rules-selection regressions; no private artifact inputs."""

import copy
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

from coc_base.docs import generated_docs
from coc_base.io import load_bundle, read_json, selection_context, write_json
from coc_base.profiles import count_assignments, create_profile, profile_diagnostics
from coc_base.validate import validate
from tools.public_files import public_files
from test_project import ROOT, RULES, inventory_fixture, temporary_directory


def cli(root, *args):
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    return subprocess.run([sys.executable, "-m", "coc_base", *map(str, args)], cwd=root,
                          env=environment, capture_output=True, text=True)


def public_checkout(destination):
    for source in public_files(ROOT):
        target = destination / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


class AccountTests(unittest.TestCase):
    def test_all_supported_town_halls_actual_and_max(self):
        for th in map(int, RULES["town_halls"]):
            with self.subTest(th=th):
                actual = create_profile(RULES, th, counts={"builders_hut": 1})
                self.assertEqual(actual["inventory"], {"town_hall": 1, "builders_hut": 1})
                self.assertNotIn("level_inventory", actual)
                self.assertFalse(actual["fully_developed"])
                maximum = create_profile(RULES, th, preset="max")
                self.assertEqual(profile_diagnostics(maximum, RULES), [])
                self.assertNotIn("bobs_hut", maximum["inventory"])
                layout, _ = inventory_fixture(th)
                layout["objects"] = [o for o in layout["objects"] if o["type"] != "bobs_hut"]
                self.assertEqual(validate(layout, RULES, maximum)["status"], "PASS")
                layout["objects"] = [o for o in layout["objects"] if o["type"] == "town_hall"
                                     or o["type"] == "builders_hut" and o["id"].endswith("001")]
                report = validate(layout, RULES, actual)
                self.assertEqual(report["status"], "PASS", report["diagnostics"])
                self.assertEqual(report["account_levels"]["bounds_only_types"], ["builders_hut", "town_hall"])

    def test_counts_and_distribution_precedence(self):
        account = {"inventory": {"builders_hut": 2, "wall": 240},
                   "level_inventory": {"wall": {"11": 100, "12": 140}, "builders_hut": {"1": 2}}}
        profile = create_profile(RULES, 12, account=account, counts={"wall": 200},
                                 level_counts={"wall:10": 75, "wall:11": 125})
        self.assertEqual(profile["inventory"]["wall"], 200)
        self.assertEqual(profile["level_inventory"]["wall"], {"10": 75, "11": 125})
        self.assertEqual(profile["level_inventory"]["builders_hut"], {"1": 2})
        self.assertEqual(account["inventory"]["wall"], 240)
        with self.assertRaisesRegex(ValueError, "sum"):
            create_profile(RULES, 12, account=account, counts={"wall": 200})
        with self.assertRaisesRegex(ValueError, "sum"):
            create_profile(RULES, 12, account=account, level_counts={"wall:11": 200})

    def test_distribution_alone_derives_count_and_checks_placements(self):
        account = read_json(ROOT / "examples/th3-hi/inventory.json")
        account["inventory"].pop("wall")
        account["level_inventory"]["wall"] = {"2": 20, "3": 30}
        profile = create_profile(RULES, 3, account=account)
        self.assertEqual(profile["inventory"]["wall"], 50)
        layout, rules, _ = load_bundle(ROOT / "examples/th3-hi/layout.json")
        for wall in [o for o in layout["objects"] if o["type"] == "wall"][:20]:
            wall["level"] = 2
        result = validate(layout, rules, profile)
        self.assertEqual(result["status"], "PASS", result["diagnostics"])
        self.assertEqual(result["account_levels"]["bounds_only_types"], [])
        layout["objects"][0]["level"] = 3
        self.assertIn("ACCOUNT_LEVEL", {d["code"] for d in validate(layout, rules, profile)["diagnostics"]})
        del profile["level_inventory"]["wall"]
        result = validate(layout, rules, profile)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["account_levels"]["bounds_only_types"], ["wall"])
        self.assertIn("Actual account levels were not checked", result["account_levels"]["statement"])

    def test_flags_derive_totals_and_reject_duplicates(self):
        levels = count_assignments(["wall:11=100", "wall:12=140"], levels=True)
        profile = create_profile(RULES, 12, counts={"builders_hut": 2}, level_counts=levels)
        self.assertEqual(profile["inventory"]["wall"], 240)
        for flags, levels in [(["wall=3", "wall=4"], False), (["wall:3=1", "wall:3=2"], True),
                              (["wall=-1"], False), (["wall=1.5"], False), (["wall:03=1"], True)]:
            with self.subTest(flags=flags), self.assertRaises(ValueError):
                count_assignments(flags, levels=levels)

    def test_invalid_levels_types_counts_and_obstacles(self):
        cases = [
            {"inventory": {"wall": 301}}, {"inventory": {"builders_hut": 0}},
            {"inventory": {"wall": True}}, {"inventory": {"wall": -1}},
            {"inventory": {"unknown_building": 1}}, {"level_inventory": {"wall": {"99": 1}}},
            {"level_inventory": {"wall": {"01": 1}}}, {"level_inventory": {"wall": {"1": True}}},
            {"level_inventory": {"wall": {}}}, {"level_inventory": {"wall": {"1": -1}}},
            {"level_inventory": {"town_hall": {"11": 1}}}, {"bob_unlocked": "yes"},
            {"blocked_areas": [{"x": 44, "y": 0, "width": 1, "height": 1}]},
            {"blocked_areas": [{"x": 0, "y": 0, "width": 0, "height": 1}]},
            {"blocked_areas": "unknown"}, {"surprise": 1}]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                create_profile(RULES, 12, account=case, counts={} if "builders_hut" in case.get("inventory", {}) else {"builders_hut": 2})

    def test_hero_hall_banners_and_metadata_override(self):
        account = {"inventory": {"builders_hut": 2, "hero_hall": 1, "hero_banner": 1}, "hero_hall_level": 1}
        profile = create_profile(RULES, 4, account=account)
        self.assertEqual(profile["hero_hall_level"], 1)
        for case in ({"inventory": {"hero_banner": 1}}, {"inventory": {"hero_hall": 1}},
                     {"inventory": {"hero_banner": 2, "hero_hall": 1}, "hero_hall_level": 1},
                     {"hero_hall_level": 2}):
            with self.subTest(case=case), self.assertRaises(ValueError):
                create_profile(RULES, 4, account=case, counts={"builders_hut": 2})
        maximum = create_profile(RULES, 12, preset="max", hero_hall_level=2, counts={"hero_banner": 2})
        self.assertEqual(maximum["level_inventory"]["hero_hall"], {"2": 1})
        self.assertFalse(maximum["fully_developed"])
        overridden = create_profile(RULES, 12, account=account, hero_hall_level=2)
        self.assertEqual(overridden["hero_hall_level"], 2)

    def test_optional_purchases_bob_mergers_and_partial_max(self):
        for n in (1, 2, 5):
            self.assertEqual(create_profile(RULES, 18, counts={"builders_hut": n})["inventory"]["builders_hut"], n)
        with self.assertRaises(ValueError):
            create_profile(RULES, 18, counts={"builders_hut": 6})
        with self.assertRaises(ValueError):
            create_profile(RULES, 10, counts={"builders_hut": 2, "bobs_hut": 1})
        with self.assertRaises(ValueError):
            create_profile(RULES, 9, counts={"builders_hut": 2, "bobs_hut": 1}, bob_unlocked=True)
        profile = create_profile(RULES, 18, preset="max", bob_unlocked=True,
                                 counts={"wall": 240, "builders_hut": 2, "revenge_tower": 0})
        self.assertEqual(profile["inventory"]["bobs_hut"], 1)
        self.assertEqual(profile["level_inventory"]["wall"], {"19": 240})
        self.assertFalse(profile["fully_developed"])
        partial = create_profile(RULES, 18, counts={"builders_hut": 2, "ricochet_cannon": 2, "cannon": 3})
        self.assertEqual(partial["inventory"]["cannon"], 3)
        with self.assertRaisesRegex(ValueError, "MERGER"):
            create_profile(RULES, 18, counts={"builders_hut": 2, "ricochet_cannon": 3, "cannon": 2})

    def test_seasonal_state_and_unreviewed_input(self):
        counts = {"builders_hut": 2, "crafting_station": 1}
        with self.assertRaisesRegex(ValueError, "SEASONAL_PHASE"):
            create_profile(RULES, 11, counts=counts)
        profile = create_profile(RULES, 11, counts=counts, crafted_phase=RULES["crafted_phase"]["id"])
        self.assertEqual(profile["inventory"]["crafting_station"], 1)
        rules = copy.deepcopy(RULES)
        rules["objects"]["wall"]["status"] = "unreviewed"
        with self.assertRaises(ValueError):
            create_profile(rules, 3, counts={"builders_hut": 2, "wall": 25})
        rules["objects"]["wall"]["status"] = "reviewed"
        rules["uncertainties"].append({"types": ["wall"], "blocks_validation": True, "description": "unknown wall rule"})
        with self.assertRaisesRegex(ValueError, "unknown wall rule"):
            create_profile(rules, 3, counts={"builders_hut": 2, "wall": 25})

    def test_cli_invalid_input_never_overwrites_output(self):
        with temporary_directory() as directory:
            output = directory / "profile.json"
            output.write_text("keep existing file", encoding="utf-8")
            for flags in (["--count", "wall=240"], ["--count", "builders_hut=2", "--count", "wall=300", "--count", "wall=240"],
                          ["--count", "builders_hut=2", "--count", "wall=240", "--level-count", "wall:11=100"]):
                result = cli(ROOT, "profile", "create", "--town-hall", 12, "--output", output, *flags)
                self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(output.read_text(encoding="utf-8"), "keep existing file")
            output.unlink()
            self.assertEqual(cli(ROOT, "profile", "create", "--town-hall", 12, "--output", output).returncode, 3)
            self.assertFalse(output.exists())


class RulesSelectionTests(unittest.TestCase):
    def test_default_current_historical_explicit_and_frozen_portability(self):
        with temporary_directory() as directory:
            checkout = directory / "public"
            public_checkout(checkout)
            newer = copy.deepcopy(RULES)
            newer["id"] = "reviewed-future-synthetic"
            newer["verified_on"] = "2026-10-05"
            newer["objects"]["wall"]["max_levels"]["3"] = 4
            newer["town_halls"]["3"]["limits"]["wall"] = 51
            newer["crafted_phase"]["id"] = "future-synthetic-phase"
            write_json(checkout / "rulesets/new.json", newer)
            write_json(checkout / "rulesets/current.json", {"schema_version": 1, "ruleset": "new.json"})
            example = "examples/th3-hi/layout.json"
            original_layout = (checkout / example).read_bytes()
            original_profile = (checkout / "examples/th3-hi/profile.json").read_bytes()
            for mode, flags, expected in (("current", [], 2), ("historical", ["--historical"], 0),
                                          ("explicit", ["--ruleset", "rulesets/new.json"], 2)):
                with self.subTest(mode=mode):
                    report_path = directory / f"{mode}.json"
                    run = cli(checkout, "validate", example, *flags, "--json", report_path)
                    self.assertEqual(run.returncode, expected, run.stdout + run.stderr)
                    report = read_json(report_path)
                    self.assertEqual(report["rules_mode"], mode)
                    self.assertEqual(report["current_ruleset_id"], newer["id"])
                    if mode != "historical":
                        self.assertEqual(report["ruleset_verified_on"], "2026-10-05")
                        self.assertEqual(report["migration"]["count_changes"]["wall"], {"before": 50, "after": 51})
                        self.assertEqual(len(report["migration"]["affected_objects"]), 50)
                        self.assertTrue(report["migration"]["phase_changed"])
                        self.assertTrue(report["migration"]["review_required"])
            conflict = cli(checkout, "validate", example, "--historical", "--ruleset", "rulesets/new.json")
            self.assertEqual(conflict.returncode, 2)
            self.assertIn("not allowed", conflict.stderr)
            render_path = directory / "current.html"
            self.assertEqual(cli(checkout, "render", example, "--output", render_path).returncode, 2)
            self.assertEqual(read_json(render_path.with_suffix(".validation.json"))["rules_mode"], "current")
            self.assertIn("reviewed-future-synthetic", render_path.read_text(encoding="utf-8"))
            bundle = directory / "bundle"
            self.assertEqual(cli(checkout, "export", example, "--historical", "--output", bundle).returncode, 0)
            moved = directory / "moved-bundle"
            bundle.rename(moved)
            self.assertEqual(cli(checkout, "validate", moved / "layout.json", "--historical").returncode, 0)
            self.assertEqual(cli(checkout, "validate", moved / "layout.json").returncode, 2)
            self.assertEqual(read_json(moved / "ruleset.json"), RULES)
            self.assertEqual(read_json(moved / "layout.json")["objects"], read_json(ROOT / example)["objects"])
            profile_path = directory / "max.json"
            self.assertEqual(cli(checkout, "profile", "create", "--town-hall", 3, "--preset", "max", "--output", profile_path).returncode, 0)
            self.assertEqual(read_json(profile_path)["inventory"]["wall"], 51)
            self.assertEqual(read_json(profile_path)["level_inventory"]["wall"], {"4": 51})
            self.assertEqual(cli(checkout, "docs").returncode, 0)
            self.assertEqual((checkout / "docs/catalogue.md").read_text(encoding="utf-8"), generated_docs(newer))
            self.assertEqual((checkout / example).read_bytes(), original_layout)
            self.assertEqual((checkout / "examples/th3-hi/profile.json").read_bytes(), original_profile)
            reviewed_profile = read_json(checkout / "examples/th3-hi/profile.json")
            reviewed_profile["ruleset_id"] = newer["id"]
            write_json(checkout / "examples/th3-hi/profile.json", reviewed_profile)
            self.assertEqual(cli(checkout, "validate", example).returncode, 2)
            reviewed_layout = read_json(checkout / example)
            reviewed_layout["ruleset_id"] = newer["id"]
            reviewed_layout["ruleset"] = "../../rulesets/new.json"
            write_json(checkout / example, reviewed_layout)
            self.assertEqual(cli(checkout, "validate", example).returncode, 0)

    def test_board_and_merger_changes_identify_affected_objects(self):
        with temporary_directory() as directory:
            layout, profile = inventory_fixture(18)
            layout.update(ruleset="old.json", profile="profile.json")
            write_json(directory / "layout.json", layout)
            write_json(directory / "old.json", RULES)
            write_json(directory / "profile.json", profile)
            newer = copy.deepcopy(RULES)
            newer["mergers"]["ricochet_cannon"]["consumes"]["cannon"] = 1
            context = selection_context(directory / "layout.json", newer, explicit=True)
            self.assertIn("ricochet_cannon", context["migration"]["changed_types"])
            self.assertEqual(len(context["migration"]["affected_objects"]), 3)
            newer["board"]["width"] = 45
            context = selection_context(directory / "layout.json", newer)
            self.assertEqual(len(context["migration"]["affected_objects"]), len(layout["objects"]))
            self.assertTrue(context["migration"]["board_changed"])
            (directory / "old.json").unlink()
            self.assertFalse(selection_context(directory / "layout.json", newer)["migration"]["comparison_available"])


if __name__ == "__main__":
    unittest.main()

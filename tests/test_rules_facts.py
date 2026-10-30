"""Validation boundaries corrected by the October 30 official-data review."""

import copy
import unittest

from coc_base.io import read_json
from coc_base.profiles import create_profile
from coc_base.validate import validate
from test_project import ROOT, inventory_fixture


class ReviewedFactTests(unittest.TestCase):
    def setUp(self):
        self.rules = read_json(ROOT / "rulesets/home-2026-10-30.json")
        self.layout, self.profile = inventory_fixture(18)
        self.layout["ruleset_id"] = self.profile["ruleset_id"] = self.rules["id"]
        for obj in self.layout["objects"]:
            if obj["type"] == "multi_gear_tower":
                obj["settings"] = {"mode": "long_range"}

    def result(self):
        return validate(self.layout, self.rules, self.profile)

    def test_firespitter_uses_four_cardinal_directions_while_sweeper_keeps_eight(self):
        fire = next(o for o in self.layout["objects"] if o["type"] == "firespitter")
        sweeper = next(o for o in self.layout["objects"] if o["type"] == "air_sweeper")
        for direction in range(8):
            with self.subTest(type="firespitter", direction=direction):
                fire["settings"]["direction"] = direction
                result = self.result()
                self.assertEqual(result["status"], "PASS" if direction % 2 == 0 else "INVALID")
                if direction % 2:
                    self.assertIn("SETTINGS", {d["code"] for d in result["diagnostics"]})
            fire["settings"]["direction"] = 0
            sweeper["settings"]["direction"] = direction
            with self.subTest(type="air_sweeper", direction=direction):
                self.assertEqual(self.result()["status"], "PASS")

    def test_second_banner_requires_hero_hall_three(self):
        for hall, slots in ((1, 1), (2, 1), (3, 2), (4, 2), (5, 3), (6, 3), (7, 4)):
            with self.subTest(hall=hall):
                counts = {"builders_hut": 1, "hero_hall": 1, "hero_banner": slots}
                profile = create_profile(self.rules, 16, hero_hall_level=hall, counts=counts)
                self.assertEqual(profile["inventory"]["hero_banner"], slots)
                with self.assertRaisesRegex(ValueError, "INVENTORY_CAP"):
                    create_profile(self.rules, 16, hero_hall_level=hall,
                                   counts=dict(counts, hero_banner=slots + 1))
        maximum = create_profile(self.rules, 8, preset="max")
        self.assertEqual(maximum["hero_hall_level"], 2)
        self.assertEqual(maximum["inventory"]["hero_banner"], 1)
        self.assertEqual(self.rules["hero_min_hall"]["queen"], 2)

    def test_multi_gear_modes_are_required_and_checked(self):
        gear = next(o for o in self.layout["objects"] if o["type"] == "multi_gear_tower")
        for mode in ("long_range", "fast_attack"):
            with self.subTest(mode=mode):
                gear["settings"] = {"mode": mode}
                self.assertEqual(self.result()["status"], "PASS")
        for settings in ({}, {"mode": "unknown"}):
            with self.subTest(settings=settings):
                gear["settings"] = settings
                result = self.result()
                self.assertEqual(result["status"], "INVALID")
                self.assertIn("SETTINGS", {d["code"] for d in result["diagnostics"]})

    def test_october_four_snapshot_keeps_its_original_settings(self):
        old = read_json(ROOT / "rulesets/home-2026-10-04.json")
        layout, profile = copy.deepcopy(self.layout), copy.deepcopy(self.profile)
        layout["ruleset_id"] = profile["ruleset_id"] = old["id"]
        for obj in layout["objects"]:
            if obj["type"] == "multi_gear_tower":
                obj.pop("settings", None)
            if obj["type"] == "firespitter":
                obj["settings"]["direction"] = 1
        self.assertEqual(validate(layout, old, profile)["status"], "PASS")
        layout["ruleset_id"] = profile["ruleset_id"] = self.rules["id"]
        result = validate(layout, self.rules, profile)
        self.assertEqual(result["status"], "INVALID")
        self.assertIn("SETTINGS", {d["code"] for d in result["diagnostics"]})


if __name__ == "__main__":
    unittest.main()

"""Account-level evidence reflects comparisons actually performed."""

import copy
from pathlib import Path
import unittest

from coc_base.io import load_bundle
from coc_base.validate import validate


ROOT = Path(__file__).resolve().parents[1]


class ValidationEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.layout, self.rules, self.profile = load_bundle(ROOT / "examples/th3-hi/layout.json", historical=True)

    def evidence(self):
        return validate(self.layout, self.rules, self.profile)["account_levels"]

    def test_matched_mismatched_and_undeclared_are_distinct(self):
        levels = self.evidence()
        self.assertEqual(levels["per_type"]["wall"], "matched")
        self.assertIn("wall", levels["distribution_checked_types"])
        self.assertTrue(levels["stages"]["object_scan_completed"])
        self.assertTrue(levels["stages"]["distribution_comparison_completed"])

        next(o for o in self.layout["objects"] if o["type"] == "wall")["level"] = 2
        levels = self.evidence()
        self.assertEqual(levels["per_type"]["wall"], "mismatched")
        self.assertIn("wall", levels["distribution_checked_types"])
        self.assertIn("did not match", levels["statement"])

        del self.profile["level_inventory"]["wall"]
        levels = self.evidence()
        self.assertEqual(levels["per_type"]["wall"], "not_declared")
        self.assertNotIn("wall", levels["distribution_checked_types"])
        self.assertIn("wall", levels["bounds_only_types"])
        self.assertIn("Actual account levels were not checked", levels["statement"])

    def test_unsupported_town_hall_does_not_claim_comparisons(self):
        self.profile["town_hall"] = 99
        del self.profile["level_inventory"]["wall"]
        result = validate(self.layout, self.rules, self.profile)
        levels = result["account_levels"]
        self.assertEqual(result["status"], "INVALID")
        self.assertEqual(levels["distribution_checked_types"], [])
        self.assertEqual(levels["bounds_only_types"], [])
        self.assertFalse(levels["stages"]["object_scan_completed"])
        self.assertFalse(levels["stages"]["distribution_comparison_completed"])
        self.assertEqual(levels["per_type"]["town_hall"], "not_run")
        self.assertEqual(levels["per_type"]["wall"], "not_declared")
        self.assertIn("did not run", levels["statement"])

    def test_invalid_distribution_and_level_do_not_count_as_comparisons(self):
        for failure in ("empty", "out_of_bounds", "negative_count", "placed_level"):
            with self.subTest(failure=failure):
                layout, profile = copy.deepcopy(self.layout), copy.deepcopy(self.profile)
                if failure == "empty":
                    profile["level_inventory"]["wall"] = {}
                elif failure == "out_of_bounds":
                    profile["level_inventory"]["wall"] = {"99": 50}
                elif failure == "negative_count":
                    profile["level_inventory"]["wall"] = {"3": -1}
                else:
                    next(o for o in layout["objects"] if o["type"] == "wall")["level"] = "3"
                result = validate(layout, self.rules, profile)
                levels = result["account_levels"]
                self.assertEqual(result["status"], "INVALID")
                self.assertEqual(levels["per_type"]["wall"], "invalid_input")
                self.assertNotIn("wall", levels["distribution_checked_types"])
                self.assertEqual(levels["per_type"]["town_hall"], "matched")

    def test_negative_inventory_is_invalid_even_without_a_distribution_or_supported_th(self):
        self.profile["inventory"]["wall"] = -1
        del self.profile["level_inventory"]["wall"]
        for th in (3, 99):
            with self.subTest(th=th):
                self.profile["town_hall"] = th
                result = validate(self.layout, self.rules, self.profile)
                levels = result["account_levels"]
                self.assertEqual(result["status"], "INVALID")
                self.assertEqual(levels["per_type"]["wall"], "invalid_input")
                self.assertNotIn("wall", levels["distribution_checked_types"])
                self.assertNotIn("matched for all", levels["statement"])

    def test_bounds_only_requires_complete_valid_placements(self):
        del self.profile["level_inventory"]["wall"]
        wall = next(o for o in self.layout["objects"] if o["type"] == "wall")
        wall["level"] = None
        self.assertNotIn("wall", self.evidence()["bounds_only_types"])
        self.layout["objects"].remove(wall)
        self.assertNotIn("wall", self.evidence()["bounds_only_types"])

    def test_structural_failures_remain_input_errors(self):
        for field, value in (("inventory", None), ("inventory", {"wall": True}),
                             ("level_inventory", []), ("level_inventory", {"wall": []})):
            with self.subTest(field=field, value=value):
                profile = copy.deepcopy(self.profile)
                profile[field] = value
                with self.assertRaises(ValueError):
                    validate(self.layout, self.rules, profile)
        layout = copy.deepcopy(self.layout)
        layout["objects"] = None
        with self.assertRaises(ValueError):
            validate(layout, self.rules, self.profile)

    def test_error_still_takes_precedence_over_unknown(self):
        self.layout["ruleset_id"] = "old"
        self.layout["objects"][0]["x"] = -1
        result = validate(self.layout, self.rules, self.profile)
        self.assertEqual(result["status"], "INVALID")
        self.assertGreater(result["errors"], 0)
        self.assertGreater(result["unknowns"], 0)
        self.assertEqual(result["account_levels"]["per_type"]["wall"], "matched")


if __name__ == "__main__":
    unittest.main()

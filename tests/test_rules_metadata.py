"""Selected rules and optional current metadata have separate responsibilities."""

import unittest
from unittest.mock import patch

from coc_base.io import current_rules_path, load_bundle, read_json, selection_context
from test_project import ROOT


class RulesMetadataTests(unittest.TestCase):
    def test_current_context_uses_already_selected_rules(self):
        selected = read_json(current_rules_path())
        with patch("coc_base.io.current_rules_path", side_effect=AssertionError("second selector read")):
            context = selection_context(ROOT / "examples/th3-hi/layout.json", selected)
        self.assertEqual(context["rules_mode"], "current")
        self.assertEqual(context["current_ruleset_id"], selected["id"])

    def test_optional_metadata_unavailability_is_explicit(self):
        layout_path = ROOT / "examples/th3-hi/layout.json"
        layout, rules, profile = load_bundle(layout_path, historical=True)
        for options in ({"historical": True}, {"explicit": True}):
            with self.subTest(options=options):
                with patch("coc_base.io.current_rules_path", side_effect=FileNotFoundError("synthetic missing selector")):
                    context = selection_context(layout_path, rules, **options)
                self.assertIsNone(context["current_ruleset_id"])
                self.assertFalse(context["current_ruleset_available"])
                self.assertIn("synthetic missing selector", context["current_ruleset_unavailable_reason"])
                self.assertIn("Current rules metadata unavailable", context["current_ruleset_notice"])


if __name__ == "__main__":
    unittest.main()

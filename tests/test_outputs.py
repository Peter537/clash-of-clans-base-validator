"""CLI output preflights preserve source bundles and allow report regeneration."""

import os
from pathlib import Path
import unittest

from coc_base.io import current_rules_path, load_bundle, read_json, write_json
from test_accounts import cli, public_checkout
from test_project import ROOT, temporary_directory


class OutputTests(unittest.TestCase):
    def bundle(self, directory, layout_name="layout.json"):
        layout, rules, profile = load_bundle(ROOT / "examples/th3-hi/layout.json", historical=True)
        layout.update(ruleset="rules.json", profile="profile.json")
        paths = [directory / layout_name, directory / "rules.json", directory / "profile.json"]
        for path, document in zip(paths, (layout, rules, profile)):
            write_json(path, document)
        return paths

    def test_layout_commands_reject_source_collisions_before_any_write(self):
        with temporary_directory() as directory:
            paths = self.bundle(directory)
            original = {path: path.read_bytes() for path in paths}
            for source in paths:
                for command, flag in (("validate", "--json"), ("render", "--output")):
                    with self.subTest(command=command, source=source.name):
                        result = cli(ROOT, command, paths[0], "--historical", flag, source)
                        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
                        self.assertIn("would overwrite", result.stderr)
                        self.assertEqual({p: p.read_bytes() for p in directory.iterdir()}, original)
            result = cli(ROOT, "export", paths[0], "--historical", "--output", directory)
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertEqual({p: p.read_bytes() for p in directory.iterdir()}, original)
            report = directory / "report.json"
            for _ in range(2):
                result = cli(ROOT, "validate", paths[0], "--historical", "--json", report)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(read_json(report)["status"], "PASS")
            for path, content in original.items():
                self.assertEqual(path.read_bytes(), content)

    def test_render_preflights_sidecars(self):
        for sidecar in ("validation.json", "isometric.svg", "overhead.svg"):
            with self.subTest(sidecar=sidecar), temporary_directory() as directory:
                paths = self.bundle(directory, f"report.{sidecar}")
                original = {path: path.read_bytes() for path in paths}
                result = cli(ROOT, "render", paths[0], "--historical", "--output", directory / "report.html")
                self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
                self.assertEqual({p: p.read_bytes() for p in directory.iterdir()}, original)
    def test_existing_hardlink_alias_is_rejected(self):
        with temporary_directory() as directory:
            paths = self.bundle(directory)
            alias = directory / "alias.json"
            try:
                os.link(paths[0], alias)
            except OSError as exc:
                self.skipTest(f"Hardlinks unavailable: {exc}")
            original = paths[0].read_bytes()
            result = cli(ROOT, "validate", paths[0], "--historical", "--json", alias)
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertEqual(paths[0].read_bytes(), original)
            self.assertEqual(alias.read_bytes(), original)

    def test_linked_layout_protects_inputs_relative_to_its_real_location(self):
        with temporary_directory() as directory:
            paths = self.bundle(directory / "source")
            alias = directory / "linked-layout.json"
            try:
                alias.symlink_to(paths[0])
            except OSError as exc:
                self.skipTest(f"Symlinks unavailable: {exc}")
            original = {path: path.read_bytes() for path in paths}
            for source in paths[1:]:
                result = cli(ROOT, "validate", alias, "--historical", "--json", source)
                self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertEqual({path: path.read_bytes() for path in paths}, original)

    def test_current_explicit_and_frozen_rules_and_selector_are_protected(self):
        with temporary_directory() as directory:
            checkout = directory / "public"
            public_checkout(checkout)
            selector = checkout / "rulesets/current.json"
            selected = selector.parent / read_json(selector)["ruleset"]
            frozen = checkout / "rulesets/home-2026-10-04.json"
            for flags in ([], ["--historical"], ["--ruleset", selected]):
                for source in (selector, selected, frozen):
                    with self.subTest(flags=flags, source=source.name):
                        original = source.read_bytes()
                        result = cli(checkout, "validate", "examples/th3-hi/layout.json", *flags, "--json", source)
                        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
                        self.assertEqual(source.read_bytes(), original)

    def test_profile_and_docs_creation_preserve_inputs(self):
        with temporary_directory() as directory:
            account = directory / "account.json"
            rules = directory / "catalogue.md"
            write_json(account, {"inventory": {"builders_hut": 2}})
            write_json(rules, read_json(current_rules_path()))
            original = {path: path.read_bytes() for path in (account, rules)}
            for source in (account, rules):
                result = cli(ROOT, "profile", "create", "--town-hall", 3, "--inventory", account,
                             "--ruleset", rules, "--output", source)
                self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            result = cli(ROOT, "docs", "--ruleset", rules, "--output", directory)
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertEqual({p: p.read_bytes() for p in directory.iterdir()}, original)


if __name__ == "__main__":
    unittest.main()

"""Run with Python 3.14: python -m coc_base --help."""

import argparse
import json
from pathlib import Path
import sys

from .io import check_rules_structure, current_rules_path, load_bundle, read_json, selection_context, write_json
from .profiles import count_assignments, create_profile
from .validate import validate
from .render import render
from .export import export
from .docs import write_docs


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate and inspect LLM-authored Clash layouts")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "render", "export"):
        p = sub.add_parser(command)
        p.add_argument("layout", type=Path)
        modes = p.add_mutually_exclusive_group()
        modes.add_argument("--ruleset", type=Path, help="Compare against an explicit snapshot")
        modes.add_argument("--historical", action="store_true", help="Use the layout's frozen rules instead of current bundled rules")
        if command == "validate":
            p.add_argument("--json", type=Path, help="Write machine-readable diagnostics")
        else:
            p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("docs")
    p.add_argument("--ruleset", type=Path, help="Generate reference tables for an explicit snapshot")
    p.add_argument("--output", type=Path, default=Path("docs"))
    p = sub.add_parser("profile", help="Declare account inventory without generating placements")
    profiles = p.add_subparsers(dest="profile_command", required=True)
    p = profiles.add_parser("create")
    p.add_argument("--town-hall", type=int, required=True)
    p.add_argument("--inventory", type=Path, help="Account JSON input")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--id", help="Profile identifier; defaults to the output filename stem")
    p.add_argument("--preset", choices=["max"], help="Explicitly assume maximum inventory and levels")
    p.add_argument("--count", action="append", default=[], metavar="TYPE=COUNT")
    p.add_argument("--level-count", action="append", default=[], metavar="TYPE:LEVEL=COUNT")
    p.add_argument("--hero-hall-level", type=int)
    p.add_argument("--bob-unlocked", action=argparse.BooleanOptionalAction, default=None)
    p.add_argument("--crafted-phase", help="Confirmed seasonal phase identifier")
    p.add_argument("--ruleset", type=Path, help="Use an explicit snapshot instead of current bundled rules")
    args = parser.parse_args(argv)
    try:
        if args.command == "docs":
            rules = read_json(args.ruleset or current_rules_path())
            check_rules_structure(rules)
            write_docs(rules, args.output)
            print(f"Catalogue written to {args.output / 'catalogue.md'}")
            return 0
        if args.command == "profile":
            rules = read_json(args.ruleset or current_rules_path())
            profile = create_profile(
                rules, args.town_hall, account=read_json(args.inventory) if args.inventory else None,
                counts=count_assignments(args.count), level_counts=count_assignments(args.level_count, levels=True),
                preset=args.preset, profile_id=args.id or args.output.stem,
                hero_hall_level=args.hero_hall_level, bob_unlocked=args.bob_unlocked, crafted_phase=args.crafted_phase)
            write_json(args.output, profile)
            print(f"Profile written to {args.output}; rules {rules['id']} reviewed {rules['verified_on']}")
            print("Explicit max assumptions applied." if args.preset else "Only declared inventory included; Town Hall supplied automatically.")
            print("Profile creation produces inventory data, never placements.")
            return 0
        layout,rules,profile = load_bundle(args.layout, args.ruleset, historical=args.historical)
        context = selection_context(args.layout, rules, historical=args.historical, explicit=bool(args.ruleset))
        if args.command == "validate":
            result = validate(layout,rules,profile)
            result.update(context)
            if args.json:
                write_json(args.json,result)
        elif args.command == "render":
            result = render(layout,rules,profile,args.output,context=context)
        else:
            result = export(layout,rules,profile,args.output,context=context)
        print(f"{result['status']}: {result['errors']} errors, {result['unknowns']} unresolved rules; {result['placed_counts'].get('wall',0)} walls")
        print(result["verification"])
        print(f"Rules: {result['rules_mode']} | {result['ruleset_id']} | reviewed {result['ruleset_verified_on']}")
        print(result["account_levels"]["statement"])
        if "current_ruleset_notice" in result:
            print(result["current_ruleset_notice"])
        for d in result["diagnostics"]:
            print(f"{d['severity'].upper()} {d['code']}: {d['message']}")
        if "migration" in result:
            print("Migration: " + json.dumps(result["migration"]))
        return 1 if result["errors"] else 2 if result["unknowns"] else 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())

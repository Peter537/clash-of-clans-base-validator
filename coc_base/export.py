"""Portable coordinate bundle and a construction order from saved placements."""

import csv
import json
from pathlib import Path

from .io import integer, write_json
from .validate import validate


def export(layout, rules, profile, directory, *, context=None):
    directory = Path(directory)
    result = validate(layout, rules, profile)
    result.update(context or {})
    directory.mkdir(parents=True, exist_ok=True)
    portable = dict(layout, ruleset="ruleset.json", profile="profile.json")
    write_json(directory/"layout.json", portable)
    write_json(directory/"ruleset.json", rules)
    write_json(directory/"profile.json", profile)
    portable_result = validate(portable, rules, profile)
    portable_result.update(context or {})
    write_json(directory/"validation.json", portable_result)
    fields = ["id", "type", "level", "x", "y", "width", "height", "group", "settings"]
    objects = sorted(layout.get("objects", []), key=lambda o: (o.get("group", ""), o.get("type", ""), str(o.get("id", ""))))
    with (directory/"coordinates.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        for obj in objects:
            row = {key: obj.get(key, "") for key in fields}
            if obj.get("type") in rules["objects"]:
                row["width"], row["height"] = rules["objects"][obj["type"]]["width"], rules["objects"][obj["type"]]["height"]
            row["settings"] = json.dumps(obj.get("settings", {}), sort_keys=True)
            writer.writerow(row)
    lines = [f"# {layout.get('name', 'Layout')} · TH{profile['town_hall']} construction", "",
             f"Validation: **{result['status']}**. Model validation only; in-game acceptance unconfirmed.", "",
             f"Rules: {result.get('rules_mode', 'supplied')} · {rules['id']} · reviewed {rules['verified_on']}.", "",
             result['account_levels']['statement'], "",
             "Use a spare Clash layout slot. Confirm the account inventory and current Crafted Defense phase before building.", "",
             "1. Clear the layout editor and use the overhead view as the coordinate map. Set (0,0) at the upper corner of the buildable diamond. Increasing x goes down and right; increasing y goes down and left in the isometric view. Count buildable tiles, excluding the decorative border.",
             "2. Place the named wall groups first. Coordinates locate the tile, not the center of a building. Build one group at a time; use the wall rows below to check each group.",
             "3. Place framing walls, then the Town Hall and surrounding buildings using coordinates.csv. Rectangles occupy [x,x+width) and [y,y+height); adjacent footprints may touch.",
             "4. Place Hero Banners and traps. Apply the settings listed in coordinates.csv. Crafting Station and its selected defense are the same slot.",
             "5. Confirm that no objects remain unplaced. Inspect the name at normal game zoom and check tall buildings do not hide its strokes. Adjust only in a copied layout, then update the JSON and revalidate.",
             "6. Save the layout in Clash, use its own Share Layout feature, and store that genuine link as copy_link. A syntactically valid link does not prove it matches these coordinates.", "",
             "## Wall rows", "", "Each entry lists x coordinates for a fixed y. These lists describe existing placements; they are not a font or generation algorithm.", ""]
    groups = sorted({o.get("group", "ungrouped") for o in objects if o.get("type") == "wall"})
    omitted = [o for o in objects if o.get("type") == "wall"
               and not all(integer(o.get(k)) for k in ("x", "y"))]
    if omitted:
        lines += ["Wall rows omitted for objects without usable integer coordinates: "
                  + ", ".join(str(o.get("id", "missing ID")) for o in omitted)
                  + ". Their supplied values remain in layout.json and coordinates.csv.", ""]
    for group in groups:
        walls = [o for o in objects if o.get("type") == "wall" and o.get("group", "ungrouped") == group
                 and all(integer(o.get(k)) for k in ("x", "y"))]
        lines += [f"### {group} · {len(walls)} walls", "", "| y | x coordinates |", "| --- | --- |"]
        for y in sorted({o["y"] for o in walls}):
            lines.append(f"| {y} | {', '.join(str(o['x']) for o in sorted(walls,key=lambda o:o['x']) if o['y']==y)} |")
        lines.append("")
    if "current_ruleset_notice" in result:
        lines += [result["current_ruleset_notice"], ""]
    if 'migration' in result:
        lines += ["## Migration comparison", "", "```json", json.dumps(result['migration'], indent=2), "```", ""]
    lines += ["## Inspection", "", "Open the HTML report alongside this guide. The CSV contains every object, including individual walls. This portable folder includes frozen rules and the account profile. Use `py -3.14 -m coc_base validate PATH/TO/layout.json --historical` to reproduce the frozen check. Omit `--historical` to check current bundled rules instead.", "", "This project is unofficial and is not endorsed by Supercell. See [Supercell’s Fan Content Policy](https://supercell.com/en/fan-content-policy/).", ""]
    (directory/"construction.md").write_text("\n".join(lines), encoding="utf-8")
    return result

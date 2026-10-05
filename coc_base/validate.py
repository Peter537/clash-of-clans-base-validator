"""Inventory and geometric checks. Letter recognition is deliberately human-owned."""

from collections import Counter
import re
from urllib.parse import urlsplit, parse_qs

from .io import check_layout_structure, check_profile_structure, check_rules_structure, digest, footprint, integer
from .profiles import available_limits, profile_diagnostics


def allowed(value, options):
    return any(type(value) is type(option) and value == option for option in options)


def copy_link_info(url):
    if not isinstance(url, str):
        raise ValueError("Copy link must be a string")
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.netloc != "link.clashofclans.com"
            or parsed.fragment or not re.fullmatch(r"/[a-z]{2}(?:-[A-Za-z]{2})?", parsed.path)):
        raise ValueError("Expected an HTTPS link.clashofclans.com language URL")
    query = parse_qs(parsed.query, keep_blank_values=True)
    if set(query) != {"action", "id"} or query["action"] != ["OpenLayout"] or len(query["id"]) != 1:
        raise ValueError("Expected exactly one action=OpenLayout and one id")
    match = re.fullmatch(r"TH([1-9][0-9]*):(HV|WB):([A-Za-z0-9_-]+)", query["id"][0])
    if not match:
        raise ValueError("Expected TH<number>:HV|WB:<opaque payload>")
    return {"town_hall": int(match[1]), "village": match[2], "payload": match[3],
            "authenticity": "unconfirmed", "availability": "unconfirmed"}


def validate(layout, rules, profile):
    check_layout_structure(layout)
    check_rules_structure(rules)
    check_profile_structure(profile)
    diagnostics = []

    def issue(code, message, objects=(), severity="error"):
        diagnostics.append({"severity": severity, "code": code, "message": message,
                            "objects": list(objects)})

    th = profile.get("town_hall")
    if not integer(th) or str(th) not in rules.get("town_halls", {}):
        issue("TOWN_HALL", "Profile Town Hall is unsupported")
        return report(layout, rules, profile, diagnostics)
    if layout.get("town_hall") != th:
        issue("PROFILE_TH", "Layout and profile Town Halls differ")
    if not isinstance(layout.get("name"), str) or not layout["name"].strip():
        issue("NAME", "A nonempty intended name is required")
    if profile.get("ruleset_id") != rules.get("id") or layout.get("ruleset_id") != rules.get("id"):
        issue("RULESET_ID", "Ruleset identifiers differ; review this migration",
              severity="unknown")
    if rules.get("review_status") != "reviewed":
        issue("UNREVIEWED", "Ruleset has not been reviewed", severity="unknown")
    for fact in rules.get("uncertainties", []):
        if fact.get("blocks_validation") and (not fact.get("types") or
            any(o.get("type") in fact["types"] for o in layout.get("objects", []) if isinstance(o, dict))):
            issue("UNKNOWN_RULE", fact["description"], severity="unknown")
    inventory = profile.get("inventory")
    diagnostics.extend(profile_diagnostics(profile, rules))
    specs = rules["objects"]
    limits = available_limits(rules, profile)
    hall_level = profile.get("hero_hall_level", 0)

    objects = layout.get("objects")
    seen, occupied, counts = set(), {}, Counter()
    board = rules["board"]
    width, height = board["width"], board["height"]
    blockers = []
    areas = profile.get("blocked_areas", [])
    reserved = layout.get("reserved_areas", [])
    for area in [*areas, *reserved]:
        if not isinstance(area, dict) or not all(integer(area.get(k)) for k in ("x", "y", "width", "height")) or area["width"] <= 0 or area["height"] <= 0:
            issue("AREA_SCHEMA", "Every area needs integer coordinates and positive dimensions")
            continue
        if area["x"] < 0 or area["y"] < 0 or area["x"] + area["width"] > width or area["y"] + area["height"] > height:
            issue("AREA_BOUNDARY", "An area extends beyond the buildable board")
        blockers.append(area)

    for index, obj in enumerate(objects):
        oid = obj.get("id")
        if not isinstance(oid, str) or not oid:
            issue("OBJECT_ID", f"Object {index} needs a nonempty string id")
            oid = f"index-{index}"
        elif oid in seen:
            issue("DUPLICATE_ID", f"Duplicate ID {oid}", [oid])
        seen.add(oid)
        kind = obj.get("type")
        if not isinstance(kind, str) or kind not in specs:
            issue("UNKNOWN_TYPE", f"{oid}: unknown object type {kind}", [oid], "unknown")
            continue
        counts[kind] += 1
        spec = specs[kind]
        if spec.get("status") != "reviewed":
            issue("UNKNOWN_RULE", f"{kind} rules are unreviewed", [oid], "unknown")
        max_level = spec["max_levels"].get(str(th), 0)
        level = obj.get("level")
        if not max_level or not limits.get(kind, 0):
            issue("AVAILABILITY", f"{oid}: {kind} unavailable at TH{th}", [oid])
        if not integer(level) or not 1 <= level <= max_level:
            issue("LEVEL", f"{oid}: level must be 1..{max_level}", [oid])
        elif kind == "town_hall" and level != th:
            issue("LEVEL", "Town Hall level must equal profile Town Hall", [oid])
        elif kind == "hero_hall" and level != hall_level:
            issue("HERO_HALL", "Placed Hero Hall differs from account level", [oid])
        settings = obj.get("settings", {})
        for key, options in spec.get("settings", {}).items():
            if key not in settings or not allowed(settings[key], options):
                issue("SETTINGS", f"{oid}: {key} must be one of {options}", [oid])
            elif integer(level):
                prerequisite = spec.get("setting_min_levels", {}).get(key, {}).get(str(settings[key]), 1)
                if level < prerequisite:
                    issue("SETTINGS_LEVEL", f"{oid}: {key}={settings[key]} requires level {prerequisite}", [oid])
        if kind == "hero_banner" and settings.get("hero") != "unassigned":
            hero = settings.get("hero")
            if isinstance(hero, str) and integer(hall_level) and hall_level < rules.get("hero_min_hall", {}).get(hero, 999):
                issue("HERO_AVAILABILITY", f"{oid}: hero unavailable at this Hero Hall level", [oid])
        allowed_settings = set(spec.get("settings", {})) | set(spec.get("optional_settings", {}))
        if kind == "crafting_station":
            allowed_settings |= {"variant", "modules"}
            phase = rules["crafted_phase"]
            variant = settings.get("variant")
            if variant not in ["inactive", *phase["variants"]]:
                issue("SEASONAL_VARIANT", f"{oid}: variant outside phase {phase['id']}", [oid])
            modules = settings.get("modules")
            cap = phase["module_max_levels"][str(th)]
            if variant != "inactive" and (not isinstance(modules, dict) or set(modules) != {"hp", "attack", "effect"} or any(not integer(v) or not 0 <= v <= cap for v in modules.values())):
                issue("SEASONAL_MODULE", f"{oid}: three modules must be 0..{cap}", [oid])
        for key, value in settings.items():
            if key not in allowed_settings:
                issue("UNKNOWN_SETTING", f"{oid}: unsupported setting {key}", [oid], "unknown")
            elif key in spec.get("optional_settings", {}) and not allowed(value, spec["optional_settings"][key]):
                issue("SETTINGS", f"{oid}: invalid {key}", [oid])
            elif key in spec.get("optional_settings", {}) and integer(level):
                prerequisite = spec.get("setting_min_levels", {}).get(key, {}).get(str(value), 1)
                if level < prerequisite:
                    issue("SETTINGS_LEVEL", f"{oid}: {key}={value} requires level {prerequisite}", [oid])
        if not all(integer(obj.get(k)) for k in ("x", "y")):
            issue("COORDINATE", f"{oid}: x and y must be integers", [oid]); continue
        x, y, w, h = footprint(obj, rules)
        if x < 0 or y < 0 or x + w > width or y + h > height:
            issue("BOUNDARY", f"{oid}: footprint leaves the {width}x{height} board", [oid])
        for area in blockers:
            if (x < area["x"] + area["width"] and x + w > area["x"] and
                y < area["y"] + area["height"] and y + h > area["y"] and kind not in area.get("allow_types", [])):
                issue("BLOCKED", f"{oid}: intersects {area.get('label', 'blocked/reserved area')}", [oid])
        collisions = set()
        for tx in range(max(0, x), min(width, x + w)):
            for ty in range(max(0, y), min(height, y + h)):
                if (tx, ty) in occupied:
                    collisions.add(occupied[tx, ty])
                else:
                    occupied[tx, ty] = oid
        if collisions:
            issue("OVERLAP", f"{oid}: overlaps {', '.join(sorted(collisions))}", [oid, *sorted(collisions)])
    for kind in counts.keys() | inventory.keys():
        if counts[kind] != inventory.get(kind, 0):
            issue("INVENTORY", f"{kind}: placed {counts[kind]}, account requires {inventory.get(kind, 0)}")
    distributions = profile.get("level_inventory", {})
    if isinstance(distributions, dict):
        for kind, distribution in distributions.items():
            if not isinstance(distribution, dict):
                continue
            matching = [o for o in objects if isinstance(o, dict) and o.get("type") == kind]
            placed = Counter(str(o["level"]) for o in matching if integer(o.get("level")))
            expected = {level: n for level, n in distribution.items() if n != 0}
            if dict(placed) != expected:
                issue("ACCOUNT_LEVEL", f"{kind}: placed level counts differ from the account distribution",
                      [o["id"] for o in matching if isinstance(o.get("id"), str)])
    assigned = [o.get("settings", {}).get("hero") for o in objects if isinstance(o,dict) and o.get("type") == "hero_banner" and isinstance(o.get("settings",{}),dict)]
    for hero,n in Counter(h for h in assigned if isinstance(h,str) and h != "unassigned").items():
        if n > 1:
            issue("HERO_DUPLICATE", f"Hero {hero} assigned to more than one banner")
    for kind in ("cannon", "archer_tower", "mortar"):
        geared = [o for o in objects if isinstance(o,dict) and o.get("type")==kind and isinstance(o.get("settings",{}),dict) and o.get("settings",{}).get("geared")]
        consumed = inventory.get("multi_gear_tower",0)
        if len(geared) + (consumed if kind != "mortar" and integer(consumed) else 0) > 1:
            issue("GEAR_UP", f"Only one gear-up slot exists for {kind}, including consumed slots")
    if "copy_link" in layout:
        try:
            info = copy_link_info(layout["copy_link"])
            if info["town_hall"] != th or info["village"] != layout.get("village", "HV"):
                issue("COPY_LINK", "Copy link Town Hall or village does not match the layout")
        except ValueError as exc:
            issue("COPY_LINK", str(exc))
    if layout.get("village") not in ("HV", "WB"):
        issue("VILLAGE", "village must be HV (home) or WB (war snapshot)")
    return report(layout, rules, profile, diagnostics, counts, len(occupied))


def report(layout, rules, profile, diagnostics, counts=None, occupied=0):
    errors = sum(d["severity"] == "error" for d in diagnostics)
    unknowns = sum(d["severity"] == "unknown" for d in diagnostics)
    inventory = profile.get("inventory", {})
    levels = profile.get("level_inventory", {})
    declared = sorted(k for k, n in inventory.items() if integer(n) and n > 0) if isinstance(inventory, dict) else []
    checked = sorted(k for k in declared if isinstance(levels, dict) and k in levels)
    unchecked = sorted(set(declared) - set(checked))
    return {"schema_version": 1, "status": "INVALID" if errors else "UNRESOLVED" if unknowns else "PASS",
            "verification": "model validation only; in-game acceptance unconfirmed",
            "visual_review": "LLM/manual review required; Python does not recognize lettering",
            "ruleset_id": rules.get("id"), "ruleset_verified_on": rules.get("verified_on"),
            "profile_id": profile.get("id"),
            "account_levels": {"distribution_checked_types": checked, "bounds_only_types": unchecked,
                               "statement": "Actual account levels were not checked for: " + ", ".join(unchecked)
                               if unchecked else "Declared level distributions checked for all inventory types."},
            "layout_sha256": digest(layout), "ruleset_sha256": digest(rules),
            "profile_sha256": digest(profile), "errors": errors, "unknowns": unknowns,
            "placed_counts": dict(sorted((counts or {}).items())), "occupied_tiles": occupied,
            "diagnostics": diagnostics}

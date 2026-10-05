"""Load portable, versioned layout bundles without changing placements."""

import hashlib
import json
from pathlib import Path


def read_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=pairs)


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode()).hexdigest()


def current_rules_path():
    selector_path = Path(__file__).resolve().parents[1] / "rulesets/current.json"
    selector = read_json(selector_path)
    if (not isinstance(selector, dict) or not integer(selector.get("schema_version"))
            or selector["schema_version"] != 1 or not isinstance(selector.get("ruleset"), str)):
        raise ValueError("Current rules selector requires schema_version 1 and a ruleset path")
    return selector_path.parent / selector["ruleset"]


def load_bundle(path, rules_override=None, *, historical=False):
    path = Path(path).resolve()
    layout = read_json(path)
    check_layout_structure(layout)
    if historical and rules_override:
        raise ValueError("Historical mode and rules override are mutually exclusive")
    rules_path = (Path(rules_override).resolve() if rules_override else
                  path.parent / layout["ruleset"] if historical else current_rules_path())
    profile_path = path.parent / layout["profile"]
    rules, profile = read_json(rules_path), read_json(profile_path)
    check_rules_structure(rules)
    check_profile_structure(profile)
    return layout, rules, profile


def integer(value):
    return type(value) is int


def _mapping(value, label):
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ValueError(f"{label} must be an object with string keys")
    return value


def _schema(value, label):
    _mapping(value, label)
    if not integer(value.get("schema_version")) or value["schema_version"] != 1:
        raise ValueError(f"{label} requires integer schema_version 1")


def _strings(value, label):
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{label} must be an array of strings")


def _string_fields(document, fields, label):
    for field in fields:
        if field in document and not isinstance(document[field], str):
            raise ValueError(f"{label}.{field} must be a string")


def _areas(value, label):
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    for index, area in enumerate(value):
        item = f"{label}[{index}]"
        _mapping(area, item)
        _string_fields(area, ("label",), item)
        if "allow_types" in area:
            _strings(area["allow_types"], f"{item}.allow_types")


def check_layout_structure(layout):
    """Reject unusable containers and metadata; placements retain model diagnostics."""
    _schema(layout, "Layout")
    if not integer(layout.get("town_hall")):
        raise ValueError("Layout.town_hall must be an integer")
    _string_fields(layout, ("name", "village", "ruleset", "ruleset_id", "profile"), "Layout")
    objects = layout.get("objects")
    if not isinstance(objects, list):
        raise ValueError("Layout.objects must be an array")
    for index, obj in enumerate(objects):
        item = f"Layout.objects[{index}]"
        _mapping(obj, item)
        _string_fields(obj, ("id", "type", "group"), item)
        _mapping(obj.get("settings", {}), f"{item}.settings")
    if "visual_review" in layout:
        review = _mapping(layout["visual_review"], "Layout.visual_review")
        _string_fields(review, ("status", "conclusion", "reviewed_on"), "Layout.visual_review")
        if "views" in review:
            _strings(review["views"], "Layout.visual_review.views")
    _areas(layout.get("reserved_areas", []), "Layout.reserved_areas")


def check_profile_structure(profile):
    _schema(profile, "Profile")
    if not integer(profile.get("town_hall")):
        raise ValueError("Profile.town_hall must be an integer")
    _string_fields(profile, ("id", "ruleset_id"), "Profile")
    inventory = _mapping(profile.get("inventory"), "Profile.inventory")
    if any(not integer(count) for count in inventory.values()):
        raise ValueError("Profile.inventory counts must be integers")
    if not integer(profile.get("hero_hall_level", 0)):
        raise ValueError("Profile.hero_hall_level must be an integer")
    for field in ("fully_developed", "bob_unlocked"):
        if field in profile and type(profile[field]) is not bool:
            raise ValueError(f"Profile.{field} must be boolean")
    if profile.get("crafted_phase") is not None and not isinstance(profile["crafted_phase"], str):
        raise ValueError("Profile.crafted_phase must be a string or null")
    levels = _mapping(profile.get("level_inventory", {}), "Profile.level_inventory")
    for kind, distribution in levels.items():
        _mapping(distribution, f"Profile.level_inventory.{kind}")
        if any(not integer(count) for count in distribution.values()):
            raise ValueError(f"Profile.level_inventory.{kind} counts must be integers")
    _areas(profile.get("blocked_areas", []), "Profile.blocked_areas")


def check_rules_structure(rules):
    _schema(rules, "Ruleset")
    for field in ("id", "verified_on"):
        if not isinstance(rules.get(field), str):
            raise ValueError(f"Ruleset.{field} must be a string")
    board = _mapping(rules.get("board"), "Ruleset.board")
    if any(not integer(board.get(k)) or board[k] <= 0 for k in ("width", "height")):
        raise ValueError("Ruleset.board dimensions must be positive integers")
    specs = _mapping(rules.get("objects"), "Ruleset.objects")
    for kind, spec in specs.items():
        _mapping(spec, f"Ruleset.objects.{kind}")
        if any(not integer(spec.get(k)) or spec[k] <= 0 for k in ("width", "height")):
            raise ValueError(f"Ruleset.objects.{kind} dimensions must be positive integers")
        for field in ("name", "label", "category"):
            if not isinstance(spec.get(field), str):
                raise ValueError(f"Ruleset.objects.{kind}.{field} must be a string")
        maximums = _mapping(spec.get("max_levels"), f"Ruleset.objects.{kind}.max_levels")
        if any(not integer(level) for level in maximums.values()):
            raise ValueError(f"Ruleset.objects.{kind}.max_levels must contain integers")
        for field in ("settings", "optional_settings"):
            options = _mapping(spec.get(field, {}), f"Ruleset.objects.{kind}.{field}")
            if any(not isinstance(values, list) for values in options.values()):
                raise ValueError(f"Ruleset.objects.{kind}.{field} values must be arrays")
        prerequisites = _mapping(spec.get("setting_min_levels", {}), f"Ruleset.objects.{kind}.setting_min_levels")
        for field, levels in prerequisites.items():
            _mapping(levels, f"Ruleset.objects.{kind}.setting_min_levels.{field}")
            if any(not integer(level) for level in levels.values()):
                raise ValueError(f"Ruleset.objects.{kind}.setting_min_levels.{field} must contain integers")
    halls = _mapping(rules.get("town_halls"), "Ruleset.town_halls")
    for th, hall in halls.items():
        _mapping(hall, f"Ruleset.town_halls.{th}")
        limits = _mapping(hall.get("limits"), f"Ruleset.town_halls.{th}.limits")
        if any(not integer(count) for count in limits.values()):
            raise ValueError(f"Ruleset.town_halls.{th}.limits must contain integers")
    mergers = _mapping(rules.get("mergers"), "Ruleset.mergers")
    for kind, recipe in mergers.items():
        _mapping(recipe, f"Ruleset.mergers.{kind}")
        ingredients = _mapping(recipe.get("consumes"), f"Ruleset.mergers.{kind}.consumes")
        if any(not integer(count) for count in ingredients.values()):
            raise ValueError(f"Ruleset.mergers.{kind}.consumes must contain integers")
    slots = rules.get("banner_slots")
    if (not isinstance(slots, list) or any(not isinstance(pair, list) or len(pair) != 2
                                         or any(not integer(n) for n in pair) for pair in slots)):
        raise ValueError("Ruleset.banner_slots must be an array of integer pairs")
    heroes = _mapping(rules.get("hero_min_hall", {}), "Ruleset.hero_min_hall")
    if any(not integer(level) for level in heroes.values()):
        raise ValueError("Ruleset.hero_min_hall must contain integers")
    phase = _mapping(rules.get("crafted_phase"), "Ruleset.crafted_phase")
    if not isinstance(phase.get("id"), str):
        raise ValueError("Ruleset.crafted_phase.id must be a string")
    _strings(phase.get("variants"), "Ruleset.crafted_phase.variants")
    modules = _mapping(phase.get("module_max_levels"), "Ruleset.crafted_phase.module_max_levels")
    if any(not integer(level) for level in modules.values()):
        raise ValueError("Ruleset.crafted_phase.module_max_levels must contain integers")
    uncertainties = rules.get("uncertainties", [])
    if not isinstance(uncertainties, list):
        raise ValueError("Ruleset.uncertainties must be an array")
    for fact in uncertainties:
        _mapping(fact, "Ruleset uncertainty")
        if not isinstance(fact.get("description"), str):
            raise ValueError("Ruleset uncertainty description must be a string")
        if "types" in fact:
            _strings(fact["types"], "Ruleset uncertainty types")


def footprint(obj, rules):
    """Return half-open tile bounds, shared by validation and inspection exports."""
    spec = rules["objects"][obj["type"]]
    return obj["x"], obj["y"], spec["width"], spec["height"]


def changed_types(old, new):
    names = old["objects"].keys() | new["objects"].keys()
    return sorted(name for name in names if old["objects"].get(name) != new["objects"].get(name))


def selection_context(path, rules, *, historical=False, explicit=False):
    """Describe rule selection and affected placements without migrating saved inputs."""
    context = {"rules_mode": "historical" if historical else "explicit" if explicit else "current",
               "current_ruleset_id": None}
    try:
        current = read_json(current_rules_path())
        check_rules_structure(current)
        context["current_ruleset_id"] = current["id"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        if not (historical or explicit):
            raise
        context["current_ruleset_notice"] = f"Current rules metadata unavailable; selected rules are unchanged: {exc}"
    if historical:
        return context
    path = Path(path).resolve()
    layout = read_json(path)
    check_layout_structure(layout)
    try:
        old = read_json(path.parent / layout["ruleset"])
    except OSError:
        context["migration"] = {"comparison_available": False,
                                "reason": "Frozen snapshot is unavailable; comparison cannot be established."}
        return context
    check_rules_structure(old)
    if digest(old) == digest(rules):
        return context
    th = str(layout.get("town_hall"))
    before = old.get("town_halls", {}).get(th, {}).get("limits", {})
    after = rules.get("town_halls", {}).get(th, {}).get("limits", {})
    count_changes = {k: {"before": before.get(k, 0), "after": after.get(k, 0)}
                     for k in sorted(before.keys() | after.keys()) if before.get(k, 0) != after.get(k, 0)}
    changed = set(changed_types(old, rules)) | count_changes.keys()
    for target in old.get("mergers", {}).keys() | rules.get("mergers", {}).keys():
        a, b = old.get("mergers", {}).get(target, {}), rules.get("mergers", {}).get(target, {})
        if a != b:
            changed |= {target} | a.get("consumes", {}).keys() | b.get("consumes", {}).keys()
    if old.get("banner_slots") != rules.get("banner_slots") or old.get("hero_min_hall") != rules.get("hero_min_hall"):
        changed.add("hero_banner")
    board_changed = old.get("board") != rules.get("board")
    phase_changed = old.get("crafted_phase") != rules.get("crafted_phase")
    if phase_changed:
        changed.add("crafting_station")
    context["migration"] = {
        "comparison_available": True, "from_ruleset_id": old.get("id"), "to_ruleset_id": rules.get("id"),
        "changed_types": sorted(changed), "count_changes": count_changes,
        "affected_objects": [o["id"] for o in layout.get("objects", []) if isinstance(o, dict)
                             and isinstance(o.get("id"), str) and (board_changed or o.get("type") in changed)],
        "board_changed": board_changed, "phase_changed": phase_changed,
        "review_required": (layout.get("ruleset_id") != rules.get("id")
                            or read_json(path.parent / layout["profile"]).get("ruleset_id") != rules.get("id"))}
    return context

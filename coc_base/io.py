"""Load portable, versioned layout bundles without changing placements."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import uuid


CURRENT_SELECTOR = Path(__file__).resolve().parents[1] / "rulesets/current.json"


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


class OutputError(OSError):
    """Publication failed; recovery_directory identifies retained backups."""

    def __init__(self, message, *, recovery_directory=None):
        super().__init__(message)
        self.recovery_directory = recovery_directory

def _remove_stage(stage, parent):
    if stage.resolve().parent != parent.resolve():
        raise OSError(f"Refusing to clean staging directory outside {parent}")
    shutil.rmtree(stage)

def _publish_text_files(contents):
    """Stage a prepared file family and restore replaced files on handled failure.

    Replacements are atomic per file, not across the family. Callers must use a
    single writer; termination or power loss can interrupt publication.
    """
    if not contents:
        return []
    files = [(Path(path).absolute(), text) for path, text in contents.items()]
    parent = files[0][0].parent.resolve()
    if any(path.parent.resolve() != parent for path, text in files):
        raise ValueError("Prepared outputs must share one directory")
    files = [(parent / path.name, text) for path, text in files]
    if len({path for path, text in files}) != len(files):
        raise ValueError("Prepared outputs must have distinct paths")
    for path, text in files:
        text.encode("utf-8")
        if path.is_symlink() or path.exists() and not path.is_file():
            raise OutputError(f"Output target must be an ordinary file: {path}")
    stage = parent / f".coc-base-stage-{uuid.uuid4().hex}"
    backups, published = {}, []
    try:
        parent.mkdir(parents=True, exist_ok=True)
        stage.mkdir()
    except OSError as exc:
        raise OutputError(f"Could not create output staging directory in {parent}: {exc}") from exc
    try:
        for index, (path, text) in enumerate(files):
            (stage / f"new-{index}").write_text(text, encoding="utf-8", newline="")
        for index, (path, text) in enumerate(files):
            if path.exists():
                backup = stage / f"old-{index}"
                shutil.copy2(path, backup)
                backups[path] = backup
        for index, (path, text) in enumerate(files):
            os.replace(stage / f"new-{index}", path)
            published.append(path)
    except OSError as exc:
        unrestored = []
        for path in reversed(published):
            try:
                if path in backups:
                    os.replace(backups[path], path)
                else:
                    path.unlink()
            except OSError as recovery_exc:
                source = backups.get(path)
                action = f"restore from {source}" if source else "remove newly created output"
                unrestored.append(f"{path}: {action}: {recovery_exc}")
        if unrestored:
            raise OutputError(
                f"Output publication failed: {exc}. Recovery required; retained files at {stage}. "
                + "; ".join(unrestored), recovery_directory=stage) from exc
        try:
            _remove_stage(stage, parent)
        except OSError as cleanup_exc:
            raise OutputError(
                f"Output publication failed: {exc}. Previous outputs restored; staging files remain at "
                f"{stage}: {cleanup_exc}", recovery_directory=stage) from exc
        raise OutputError(f"Output publication failed: {exc}. Previous outputs restored.") from exc
    try:
        _remove_stage(stage, parent)
    except OSError as exc:
        return [f"Outputs published, but staging cleanup failed at {stage}: {exc}"]
    return []


def check_output_paths(outputs, inputs):
    """Reject source aliases and colliding artifacts before any output is written."""
    protected = [Path(path).resolve() for path in inputs]
    destinations = []
    for path in outputs:
        destination = Path(path).resolve()
        for other in [*protected, *destinations]:
            if destination == other or (destination.exists() and other.exists()
                                         and destination.samefile(other)):
                raise ValueError(f"Output {path} would overwrite an input or another output: {other}")
        if destination.is_dir():
            raise ValueError(f"Output file is an existing directory: {path}")
        destinations.append(destination)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode()).hexdigest()


def current_rules_path():
    selector_path = CURRENT_SELECTOR
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
    for th, hall in halls.items():
        minimums = _mapping(hall.get("minimum_mergers", {}), f"Ruleset.town_halls.{th}.minimum_mergers")
        for kind, count in minimums.items():
            if kind not in mergers or not integer(count) or not 0 <= count <= hall["limits"].get(kind, 0):
                raise ValueError(f"Ruleset.town_halls.{th}.minimum_mergers requires merger counts within limits")
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
        current = read_json(current_rules_path()) if historical or explicit else rules
        check_rules_structure(current)
        if not current["id"].strip():
            raise ValueError("Current ruleset metadata requires a nonempty string id")
        context["current_ruleset_id"] = current["id"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        if not (historical or explicit):
            raise
        context["current_ruleset_notice"] = f"Current rules metadata unavailable; selected rules are unchanged: {exc}"
        context["current_ruleset_available"] = False
        context["current_ruleset_unavailable_reason"] = str(exc)
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
    old_minimums = old.get("town_halls", {}).get(th, {}).get("minimum_mergers", {})
    new_minimums = rules.get("town_halls", {}).get(th, {}).get("minimum_mergers", {})
    minimum_changes = {k: {"before": old_minimums.get(k, 0), "after": new_minimums.get(k, 0)}
                       for k in sorted(old_minimums.keys() | new_minimums.keys())
                       if old_minimums.get(k, 0) != new_minimums.get(k, 0)}
    changed |= minimum_changes.keys()
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
        "minimum_merger_changes": minimum_changes,
        "affected_objects": [o["id"] for o in layout.get("objects", []) if isinstance(o, dict)
                             and isinstance(o.get("id"), str) and (board_changed or o.get("type") in changed)],
        "board_changed": board_changed, "phase_changed": phase_changed,
        "review_required": (layout.get("ruleset_id") != rules.get("id")
                            or read_json(path.parent / layout["profile"]).get("ruleset_id") != rules.get("id"))}
    return context

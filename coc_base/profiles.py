"""Create declared account inventories; never create layout placements."""

from copy import deepcopy

from .io import check_profile_structure, check_rules_structure, integer


def available_limits(rules, profile):
    limits = rules["town_halls"][str(profile["town_hall"])]["limits"].copy()
    inventory = profile["inventory"]
    for target, recipe in rules["mergers"].items():
        count = inventory.get(target, 0)
        if integer(count) and count >= 0:
            for ingredient, quantity in recipe["consumes"].items():
                limits[ingredient] = limits.get(ingredient, 0) - quantity * count
    hall = profile.get("hero_hall_level", 0)
    limits["hero_banner"] = next((n for level, n in reversed(rules["banner_slots"])
                                 if integer(hall) and hall >= level), 0)
    return limits


def profile_diagnostics(profile, rules):
    check_profile_structure(profile)
    check_rules_structure(rules)
    issues = []

    def issue(code, message, severity="error"):
        issues.append({"severity": severity, "code": code, "message": message, "objects": []})

    if not isinstance(profile, dict) or profile.get("schema_version") != 1:
        issue("PROFILE_SCHEMA", "Profile must be a schema_version 1 object")
        return issues
    th = profile.get("town_hall")
    if not integer(th) or str(th) not in rules["town_halls"]:
        issue("TOWN_HALL", "Profile Town Hall is unsupported")
        return issues
    inventory = profile.get("inventory")
    if not isinstance(inventory, dict):
        issue("PROFILE_SCHEMA", "Profile inventory must be an object")
        return issues
    specs = rules["objects"]
    limits = available_limits(rules, profile)
    ingredients = {i for recipe in rules["mergers"].values() for i in recipe["consumes"]}
    for kind, count in inventory.items():
        if kind not in specs:
            issue("UNKNOWN_TYPE", f"Unknown inventory type {kind}", "unknown")
            continue
        if not integer(count) or count < 0:
            issue("PROFILE_SCHEMA", f"Invalid inventory count for {kind}")
            continue
        cap = limits.get(kind, 0)
        if count > cap or cap < 0:
            issue("MERGER" if kind in ingredients else "INVENTORY_CAP",
                  f"{kind}: profile has {count}, available after merges {cap}")
        if kind == "bobs_hut" and count and profile.get("bob_unlocked") is not True:
            issue("BOB", "B.O.B.'s Hut requires a confirmed Builder Base unlock")
    if inventory.get("town_hall") != 1:
        issue("TOWN_HALL", "Exactly one Town Hall is required in the account profile")
    for kind, spec in specs.items():
        count = inventory.get(kind, 0)
        if integer(count) and 0 <= count < spec.get("min_count", 0):
            issue("INVENTORY_MIN", f"Account requires at least {spec['min_count']} {kind}")
    hall = profile.get("hero_hall_level", 0)
    if not integer(hall) or not 0 <= hall <= specs["hero_hall"]["max_levels"][str(th)]:
        issue("HERO_HALL", "Invalid profile Hero Hall level")
    if bool(inventory.get("hero_hall", 0)) != bool(hall):
        issue("HERO_HALL", "Hero Hall inventory and level disagree")
    for key in ("fully_developed", "bob_unlocked"):
        if key in profile and type(profile[key]) is not bool:
            issue("PROFILE_SCHEMA", f"{key} must be boolean")
    if profile.get("fully_developed") is True:
        for kind, cap in limits.items():
            if kind in specs and not specs[kind].get("optional") and inventory.get(kind, 0) != cap:
                issue("PROFILE_INCOMPLETE", f"Developed profile requires {cap} {kind}")
    if inventory.get("crafting_station", 0) and profile.get("crafted_phase") != rules["crafted_phase"]["id"]:
        issue("SEASONAL_PHASE", "Account phase has not been reconciled", "unknown")
    levels = profile.get("level_inventory", {})
    if not isinstance(levels, dict):
        issue("LEVEL_INVENTORY", "level_inventory must be an object")
        levels = {}
    for kind, distribution in levels.items():
        if kind not in specs:
            issue("UNKNOWN_TYPE", f"Unknown level inventory type {kind}", "unknown")
            continue
        if not isinstance(distribution, dict) or not distribution:
            issue("LEVEL_INVENTORY", f"{kind}: level distribution must be a nonempty object")
            continue
        valid = True
        for level, count in distribution.items():
            if (not isinstance(level, str) or not level.isdecimal() or str(int(level)) != level
                    or not integer(count) or count < 0):
                issue("LEVEL_INVENTORY", f"{kind}: use canonical integer level keys and nonnegative integer counts")
                valid = False
                continue
            n = int(level)
            if not 1 <= n <= specs[kind]["max_levels"][str(th)]:
                issue("LEVEL_INVENTORY", f"{kind}: level {n} is unavailable at TH{th}")
            if count and ((kind == "town_hall" and n != th) or (kind == "hero_hall" and n != hall)):
                issue("LEVEL_INVENTORY", f"{kind}: distribution differs from account level")
        if valid and sum(distribution.values()) != inventory.get(kind, 0):
            issue("LEVEL_INVENTORY", f"{kind}: level counts must sum to inventory count")
    areas = profile.get("blocked_areas", [])
    if not isinstance(areas, list):
        issue("AREA_SCHEMA", "blocked_areas must be an array")
    else:
        for area in areas:
            if (not isinstance(area, dict) or not all(integer(area.get(k)) for k in ("x", "y", "width", "height"))
                    or area["width"] <= 0 or area["height"] <= 0):
                issue("AREA_SCHEMA", "Blocked areas require integer coordinates and positive dimensions")
            elif (area["x"] < 0 or area["y"] < 0 or area["x"] + area["width"] > rules["board"]["width"]
                  or area["y"] + area["height"] > rules["board"]["height"]):
                issue("AREA_BOUNDARY", "Blocked area extends beyond the board")
    return issues


def max_profile(rules, th, *, bob_unlocked=False):
    if not integer(th) or str(th) not in rules["town_halls"]:
        raise ValueError("Unsupported Town Hall")
    inventory = rules["town_halls"][str(th)]["limits"].copy()
    for target, recipe in rules["mergers"].items():
        for ingredient, quantity in recipe["consumes"].items():
            inventory[ingredient] -= inventory.get(target, 0) * quantity
    inventory["bobs_hut"] = int(bob_unlocked)
    inventory = {k: v for k, v in inventory.items() if v}
    return {"schema_version": 1, "id": f"th{th}-max-template", "ruleset_id": rules["id"],
            "town_hall": th, "fully_developed": True,
            "hero_hall_level": rules["objects"]["hero_hall"]["max_levels"][str(th)],
            "bob_unlocked": bob_unlocked,
            "crafted_phase": rules["crafted_phase"]["id"] if inventory.get("crafting_station") else None,
            "blocked_areas": [], "inventory": inventory,
            "level_inventory": {k: {str(rules["objects"][k]["max_levels"][str(th)]): n}
                                for k, n in inventory.items()},
            "notes": ["Explicit max template: remaining inventory and ordinary levels are assumed max; five purchased Builder's Huts are assumed. External B.O.B. unlock is supplied separately."]}


def count_assignments(values, *, levels=False):
    assignments = {}
    for value in values:
        key, sep, text = value.partition("=")
        if not sep or not text.isdecimal() or not key or key in assignments:
            raise ValueError(f"Invalid or duplicate assignment: {value}")
        if levels:
            kind, sep, level = key.partition(":")
            if not sep or not kind or not level.isdecimal() or str(int(level)) != level:
                raise ValueError(f"Expected type:level=count: {value}")
        assignments[key] = int(text)
    return assignments


def create_profile(rules, th, *, account=None, counts=None, level_counts=None, preset=None,
                   profile_id="account", hero_hall_level=None, bob_unlocked=None, crafted_phase=None):
    check_rules_structure(rules)
    if not integer(th) or str(th) not in rules["town_halls"]:
        raise ValueError("Unsupported Town Hall")
    account = {} if account is None else account
    if not isinstance(account, dict):
        raise ValueError("Account input must be an object")
    fields = {"inventory", "level_inventory", "hero_hall_level", "bob_unlocked", "crafted_phase", "blocked_areas"}
    if set(account) - fields:
        raise ValueError(f"Unsupported account fields: {sorted(set(account) - fields)}")
    source_counts = account.get("inventory", {})
    source_levels = account.get("level_inventory", {})
    if not isinstance(source_counts, dict) or not isinstance(source_levels, dict):
        raise ValueError("inventory and level_inventory must be objects")
    counts = counts or {}
    level_counts = level_counts or {}
    if preset not in (None, "max"):
        raise ValueError("Unsupported preset")
    bob = bob_unlocked if bob_unlocked is not None else account.get("bob_unlocked", False)
    if type(bob) is not bool:
        raise ValueError("bob_unlocked must be boolean")
    profile = (max_profile(rules, th, bob_unlocked=bob) if preset == "max" else
               {"schema_version": 1, "ruleset_id": rules["id"], "town_hall": th,
                "fully_developed": False, "hero_hall_level": 0, "bob_unlocked": bob,
                "crafted_phase": None, "blocked_areas": [], "inventory": {"town_hall": 1}})
    profile["id"] = profile_id
    for key in ("hero_hall_level", "bob_unlocked", "crafted_phase", "blocked_areas"):
        if key in account:
            profile[key] = deepcopy(account[key])
    for key, value in (("hero_hall_level", hero_hall_level), ("bob_unlocked", bob_unlocked), ("crafted_phase", crafted_phase)):
        if value is not None:
            profile[key] = value
    profile["inventory"].update(source_counts)
    profile["inventory"].update(counts)
    explicit_counts = set(source_counts) | counts.keys()
    distributions = deepcopy(source_levels)
    flag_distributions = {}
    for key, n in level_counts.items():
        kind, level = key.split(":")
        flag_distributions.setdefault(kind, {})[level] = n
    distributions.update(flag_distributions)
    for kind, distribution in distributions.items():
        if kind not in explicit_counts and isinstance(distribution, dict) and all(integer(v) for v in distribution.values()):
            profile["inventory"][kind] = sum(distribution.values())
    if preset == "max":
        profile["notes"] = ["Max template baseline with declared overrides: remaining inventory and ordinary levels are assumed maximum. Builder's Hut count is recorded in inventory; B.O.B. unlock is supplied explicitly."]
        profile["level_inventory"] = {k: {str(profile["hero_hall_level"] if k == "hero_hall" else rules["objects"][k]["max_levels"][str(th)]): n}
                                      for k, n in profile["inventory"].items() if k in rules["objects"] and n}
        if explicit_counts or distributions or hero_hall_level is not None or "hero_hall_level" in account:
            profile["fully_developed"] = False
    profile.setdefault("level_inventory", {}).update(distributions)
    if not profile["level_inventory"]:
        del profile["level_inventory"]
    if rules.get("review_status") != "reviewed":
        raise ValueError("Ruleset must be reviewed before creating a profile")
    for kind, n in profile["inventory"].items():
        if n and kind in rules["objects"] and rules["objects"][kind].get("status") != "reviewed":
            raise ValueError(f"Unreviewed inventory rules for {kind}")
    for fact in rules.get("uncertainties", []):
        if fact.get("blocks_validation") and (not fact.get("types") or any(profile["inventory"].get(k, 0) for k in fact["types"])):
            raise ValueError(fact["description"])
    issues = profile_diagnostics(profile, rules)
    if issues:
        raise ValueError("; ".join(f"{d['code']}: {d['message']}" for d in issues))
    return profile

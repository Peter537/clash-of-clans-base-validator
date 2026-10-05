# Declare an actual account

`profile create` writes account inventory data. It does not create placements. Without a preset, it includes only the inventory you declare. Omitted object types count as zero; one Town Hall is supplied automatically. An explicit Town Hall count must still be one. Use catalogue type IDs such as `builders_hut`.

```powershell
py -3.14 -m coc_base profile create --town-hall 12 --inventory account.json --output profiles/account.json
```

`account.json` is a UTF-8 JSON file that you supply. Store personal input files inside ignored `profiles/`, for example `profiles/account-input.json`, and pass that path to `--inventory`. The JSON below describes a partial account. Add every owned building and trap before designing a complete layout:

```json
{
  "inventory": {"builders_hut": 3, "wall": 240, "hero_hall": 1, "hero_banner": 2},
  "level_inventory": {"wall": {"11": 100, "12": 140}},
  "hero_hall_level": 2,
  "bob_unlocked": false,
  "crafted_phase": null,
  "blocked_areas": [{"x": 8, "y": 9, "width": 2, "height": 2, "label": "saved tree"}]
}
```

Supported fields are `inventory`, optional `level_inventory`, `hero_hall_level`, `bob_unlocked`, `crafted_phase` and `blocked_areas`. Unknown fields and duplicate JSON keys are rejected. The saved profile adds a schema version, IDs and rules references to this input. See the [format](layout-format.md#account-profile).

## Counts and levels

Declare the actual Builder's Hut count. The reviewed starting-home model requires at least one hut; buying additional slots is optional. Hero Hall count and level must agree. Banner counts and assigned heroes depend on that level. A Crafting Station needs the matching seasonal `crafted_phase` identifier. B.O.B. requires you to confirm its Builder Base unlock and use a supported Town Hall.

```powershell
py -3.14 -m coc_base profile create --town-hall 12 --count builders_hut=3 --count wall=240 --level-count wall:11=100 --level-count wall:12=140 --output profiles/mixed.json
```

A level distribution lists how many objects you own at each ordinary upgrade level, excluding supercharges. If you provide a distribution without a count, its total supplies that type's quantity. When both are supplied, their totals must match. Level keys must be positive decimal integers written as strings without leading zeros; counts are nonnegative integers. Town Hall and Hero Hall distributions must agree with the corresponding account levels.

Validation compares supplied distributions with placed objects. For types without distributions, it checks the level limits for the Town Hall and the required settings. Reports list types whose actual account levels were not checked. Mixed wall levels are supported; supply a distribution to check the exact mix on your account.

## Override order

JSON input is applied first, then CLI flags. `--count TYPE=N` replaces that count. A set of `--level-count TYPE:LEVEL=N` flags replaces the entire supplied distribution for that type. Other types' distributions remain unchanged. Repeating a count key or type/level pair fails. A count override keeps any explicitly supplied distribution, so inconsistent totals fail.

Metadata flags `--hero-hall-level N`, `--bob-unlocked` or `--no-bob-unlocked`, and `--crafted-phase ID` override corresponding JSON values. Obstacles come from JSON. `--id NAME` sets the saved profile ID; otherwise it uses the output filename stem.

## Explicit max template

```powershell
py -3.14 -m coc_base profile create --town-hall 18 --preset max --output profiles/max.json
py -3.14 -m coc_base profile create --town-hall 18 --preset max --count builders_hut=3 --count wall=240 --bob-unlocked --output profiles/modified-max.json
```

`--preset max` calculates inventory from the selected catalogue after applying the maximum number of completed mergers. It assumes maximum ordinary levels, the maximum Hero Hall level and five purchased Builder's Huts. B.O.B. remains absent unless its external unlock is explicitly confirmed. The selected Crafted phase is also an assumption. Check these assumptions against your account before construction.

Use count and level overrides to describe an account that is not fully developed. The saved profile then permits unbuilt slots while retaining availability, count caps, minimum counts, Hero Hall and merger checks. The template cannot prove historical upgrades or completed merges.

Profiles normally use the [bundled rules](cli.md#rules-selection). `profile create --ruleset PATH` uses an explicit snapshot. Invalid or unresolved input is rejected before writing the output.

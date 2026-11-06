# Layout and profile format

Schema version **1** uses UTF-8 JSON. Duplicate JSON keys are rejected. Profile and frozen rules paths resolve relative to the layout file, so bundles move together. Normal commands select current bundled rules; `--historical` selects the referenced frozen rules. Reports hash all selected inputs and record the rules mode.

Schema versions and Town Hall values must be JSON integers; booleans and floating-point values are rejected. Structural errors prevent output files from being written. The Python validation, rendering and export functions reject these errors by raising `ValueError`. Well-formed inputs with placement errors still produce model diagnostics.

## Layout

Required fields: `schema_version`, `name`, `town_hall`, `village`, `ruleset`, `ruleset_id`, `profile`, `objects`. `village` is `HV` for the Home Village or `WB` for a war snapshot using the same Home Village inventory.

Every object has a unique nonempty `id`, catalogue `type`, integer `x`, integer `y`, and integer `level` for ordinary upgrades. Optional `group` labels guide construction. Required settings depend on the type; they are listed below. Optional `visual_review` and `design_notes` record LLM observations. The CLI never edits placements.

`visual_review` is an object containing a string `status` such as `pending`, `reviewed` or `blocked`, a string `conclusion`, an optional string `reviewed_on`, and an optional `views` array of strings. It records the LLM’s assessment; Python does not verify that assessment. State in the conclusion when a view could not be inspected. Omit an optional group or visual review when it is unavailable; do not use `null`.

This object fragment is valid at TH18; it is not a complete layout:

```json
{"id":"firespitter-001","type":"firespitter","x":35,"y":29,"level":3,"group":"outer-ring","settings":{"direction":2}}
```

`copy_link` optionally stores a genuine game-generated link. Format checking cannot prove authenticity, expiry, or correspondence to the coordinate file. See [sharing](sources.md#copy-base-links).

## Coordinate conventions

The buildable model is 44×44 tiles. The origin `(0,0)` is at the top corner of the diamond in the isometric view. Increasing x goes down and right; increasing y goes down and left. The overhead view puts x to the right and y downward.

A 3×3 object at `(10,12)` occupies x = 10,11,12 and y = 12,13,14. Bounds are half-open: `[x,x+width)` × `[y,y+height)`. Coordinates 0–43 locate tiles; 44 marks the boundary. Touching edges are legal; shared tiles are not. A 4×4 object at `(40,40)` fits exactly. At `(41,40)` it leaves the board. Rotating a square building does not change its footprint.

Isometric projection uses `(x−y, (x+y)/2)` with a fixed display scale. It adds no height. Both views, CSV dimensions and collision checks use the footprint recorded in the rules JSON.

## Settings

| Type | Required settings |
| --- | --- |
| x_bow | `mode`: `ground` or `ground_air` |
| inferno_tower | `mode`: `single` or `multi` |
| air_sweeper | `direction`: integer 0–7; project convention starts at +x and rotates in 45° steps |
| firespitter | `direction`: 0, 2, 4 or 6 in the same project index; rotation steps are 90° |
| multi_gear_tower | `mode`: `long_range` or `fast_attack` |
| spell_tower | `spell`: `rage`, `poison`, `invisibility`, `earthquake`; minimum ordinary levels 1,2,3,4 respectively |
| skeleton_trap | `mode`: `ground` or `air` |
| hero_banner | `hero`: `king`, `queen`, `minion_prince`, `warden`, `champion`, `dragon_duke`, `unassigned` |
| crafting_station | `variant`: a current phase variant or `inactive`; active variants need `modules` with integer `hp`, `attack`, `effect` |

Cannon, Archer Tower and Mortar optionally accept boolean `geared`. Each type has one gear-up slot; Cannon and Archer Tower slots are consumed by a Multi Gear Tower. Direction numbers follow this project’s orientation convention. They have not been verified against the game's internal direction values. Supercharge state and combat statistics are outside this geometry format.

## Account profile

Required fields: `schema_version`, `id`, `ruleset_id`, `town_hall`, `inventory`, `hero_hall_level`. Use `fully_developed: true` only when every non-optional slot is developed after the stated mergers. Purchased Builder’s Huts and B.O.B. still use the actual account counts. `bob_unlocked` confirms the external Builder Base prerequisite. `crafted_phase` identifies the account’s reviewed phase. `blocked_areas` contains obstacle rectangles.

Use [profile create](accounts.md) to save your account facts as a complete profile. Omitted object types count as zero. Every declared inventory count is exact: missing and excess placements both fail. `fully_developed: false` permits unbuilt slots while retaining count limits, mergers, the mandatory Town Hall and availability checks. Rules may specify per-Town-Hall `minimum_mergers`; these apply to partial accounts too. See [mandatory earlier mergers](rules.md#mandatory-earlier-mergers). Use `--preset max` explicitly to assume maximum inventory and levels.

Optional `level_inventory` records how many objects of each type are at each ordinary level, for example `{"wall":{"11":100,"12":140}}`. Counts must sum to that type's inventory. Placed levels must match each supplied distribution exactly. For types without a distribution, level checks cover only the Town Hall's level limits and relevant prerequisites; reports identify that coverage limit. The optional field is compatible with existing schema-1 profiles.

Profiles may describe obstacles with measured rectangles: `{"x":8,"y":9,"width":2,"height":2,"label":"saved tree"}`. A layout may add `reserved_areas` in the same format. `allow_types: ["wall"]` allows walls in a lettering reservation while excluding buildings and traps. If present, `allow_types` must be an array of strings; omitted or empty permissions allow no object types. Each area must fit within the board.

Invalid placements remain visible in reports. Objects whose footprints are unresolved use a visibly uncertain 1×1 marker; that marker does not establish their size.

## Validation reports

Report schema version 1 retains `account_levels.distribution_checked_types`, `bounds_only_types` and `statement`. Checked types are those whose declared level distribution was actually compared with usable placed-level data, whether it matched or differed. Bounds-only types have no distribution and a complete set of placements whose ordinary levels were checked. An early return does not establish either kind of coverage.

`account_levels.per_type` records the evidence for each inventory or distribution type:

| State | Meaning |
| --- | --- |
| `not_declared` | No level distribution was supplied for the type |
| `not_run` | Comparison did not run for a declared distribution |
| `invalid_input` | The distribution, inventory count or required placed-level data could not be compared |
| `matched` | A completed comparison matched the declared distribution |
| `mismatched` | A completed comparison differed from the declared distribution |

`account_levels.stages` records `inventory_available`, `level_inventory_available`, `object_scan_completed` and `distribution_comparison_completed`. Structural checks require usable inventory mappings before producing a report, so the availability fields are true in reports. Stage completion means that the stage ran, not that every input was valid or every comparison matched. Use these fields with diagnostics and the overall status. Model validation only; in-game acceptance remains unconfirmed.

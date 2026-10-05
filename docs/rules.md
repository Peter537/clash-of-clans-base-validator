# Inventory rules

The [catalogue](catalogue.md) lists reviewed count limits and levels for each Town Hall. Asset count limits are **unmerged**: merged defenses replace their ingredients. The explicit max template subtracts the consumed objects before recording account inventory.

At TH18, three Ricochet Cannons consume six Cannons; the Multi Gear Tower consumes the seventh Cannon and one Archer Tower. Three Multi Archer Towers consume six more Archer Towers, leaving **two** of the original nine. Two Super Wizard Towers consume four of six Wizard Towers, leaving **two**. TH17 merges Eagle Artillery into the Town Hall, so TH17–18 have no separate Eagle. Merged defenses are placed once; their historical ingredients are not placed alongside them.

Recipes store minimum ingredient levels and the Multi Gear Tower’s gear-up requirement for construction guidance. Inventory checks verify that enough ingredients are available for the declared merges. They cannot reconstruct an account’s previous upgrades or confirm that a merge actually happened in-game. Actual merged-object counts must come from the account.

## Heroes and optional objects

Hero Hall replaces old altars. It unlocks at TH4 in this snapshot. Banners are 2×2; available slots depend on the actual Hall level: 1 slot at level 1, 2 at level 2, 3 at level 5, 4 at level 7. More owned heroes do not mean more placeable banners. Assigned heroes must be unlocked and cannot be assigned twice. Guardian selection belongs to the TH18 Town Hall; Guardians are not extra buildings or banners.

The explicit `--preset max` template assumes five purchased Builder’s Huts. Actual profiles may have fewer, with at least one hut required by the reviewed starting-home model. B.O.B.’s Hut is optional and requires explicit Builder Base unlock confirmation; no template assumes that unlock. Helper Hut is separate from its resident helpers; those residents are not placeable inventory objects. Likewise, pets, troops, equipment, Trader, Forge, boats and scenery are not additional editable Home Village building footprints.

[Supercell’s builder requirements](https://support.supercell.com/clash-of-clans/en/articles/builders-4.html) require three Home Village gear-ups for B.O.B. The reviewed building asset enables gear-ups at Cannon 7, Archer Tower 10 and Mortar 8. Mortar 8 requires TH10, so the model infers that B.O.B. cannot exist below TH10, even though the raw hut asset has a TH1 prerequisite. A TH10+ account still needs a confirmed external unlock. Only one gear-up slot of each type exists, including Cannon and Archer slots consumed by a Multi Gear Tower.

Optional decorations and temporary event objects vary by account. Measure them as blocked areas when they occupy buildable tiles. If a footprint could affect validation and has not been measured, keep it unresolved. The model does not assume that every account owns the same decorations. Profile creation defaults to no obstacles, so check whether the canvas is clear.

## Crafted Defenses and levels

Phase 4 offers Hero Hunter, Hot Candle and Cake-A-Pult from TH11. One active variant occupies the Crafting Station’s 3×3 slot; these are not four separate objects. An inactive station uses the same slot. Settings store its variant and the three independently upgradeable modules. Module level 0 is the free initial state; TH18 permits level 9 for each module in the asset table.

Regular upgrade levels (ordinary levels) are checked for each object, so mixed wall levels are supported. Optional account distributions add exact level-count checks; without them, reports state that actual account levels were not checked. Exactly 325 walls are available at TH14–18. The June 2026 update opened the remaining level-19 upgrades at TH18. Combat behavior, supercharge counts, hero/pet/troop upgrade levels and economic prerequisites are outside geometric validation.

## Unknown facts

A ruleset or object without `status: reviewed`, a mismatched snapshot ID, a seasonal phase that does not match the selected rules, or a blocking `uncertainties` entry produces an unresolved diagnostic. Known placement mistakes produce errors. `INVALID` takes precedence if both exist; the report still lists unknowns. Neither state gives an unconditional pass.

Reviewed conventions such as the 44×44 canvas apply to this model. A model pass does not establish live game acceptance. Confirm the active seasonal phase and your account details before construction.

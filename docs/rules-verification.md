# Game-fact review: 2026-10-30

The review covered every fact category in [home-2026-10-30.json](../rulesets/home-2026-10-30.json). Corrections were applied directly to this unpublished snapshot, keeping its filename and ID. The older `home-2026-10-04.json` snapshot and saved layout/profile references are preserved.

The result is a reviewed model of the pinned official data, with live support corroboration. **It is not a certificate that every value matches the latest live client.** Apple's public listing returned version **18.647.5**, released October 21. The official pinned manifest identifies itself as **18.600.3**. Attempts to obtain a current package fingerprint did not succeed, and browser approval declined the package download. No further package extraction was attempted after that decision.

## Evidence and coverage

All downloaded official source files matched their recorded SHA256 values. The revised snapshot records the URLs, hashes and review date, including the newly inspected `heroes.csv`, `weapons.csv` and `fingerprint.json`. The comparison checked 2,055 grouped values and source hashes, including all 52 objects, 104 footprint dimensions and 1,872 per-Town-Hall count/ordinary-level values. It found no remaining differences within the pinned model and its listed interpretation overrides.

| Category | Evidence and result |
| --- | --- |
| Building/trap identities and completeness | All modeled permanent Home Village buildings/traps and the banner map to source entities. Builder Base, retired altars, NPC content, event objects and decorations are excluded or account-specific blockers. |
| Footprints | `Width`/`Height` checked for every ordinary level of every modeled object. These are placement dimensions; `BuildingW`/`BuildingH` describe smaller combat hitboxes. All 104 dimensions match. |
| Counts and ordinary levels, TH1–18 | All 1,872 values compared with inherited count rows and level/TH prerequisites, applying the interpretation overrides below. TH8's banner count needed correction. |
| Merger recipes | All four recipes checked against `MergeRequirement`, including quantities, ingredient levels and the Multi-Gear Tower's gear requirement. |
| Mandatory earlier mergers | Earlier Town Hall merger limits, the all-buildings upgrade flag and permanent-merger documentation support the existing TH17/18 minima. This is an inference, not an observed upgrade attempt. |
| Heroes and banners | All six hero prerequisites checked against `heroes.csv` and live [Hero Support](https://support.supercell.com/clash-of-clans/en/articles/about-heroes-pets-9.html). Banner slot thresholds checked independently against the full global array; the second slot starts at Hall 3. |
| Modes and level prerequisites | Building normal/alternate mode fields, spell unlock levels, Skeleton Trap alternate mode and first gear-up costs checked. The Multi-Gear Tower's modes were missing from the model. |
| Aim directions | `AimRotateStep` is 45 degrees for Air Sweeper and 90 degrees for Firespitter at every available level. Firespitter's permitted directions needed correction. |
| Crafted Defenses | All three Phase 4 archetypes and all nine HP/attack/effect module tracks checked, including zero-based module caps at TH11–18. Live [Crafted Support](https://support.supercell.com/clash-of-clans/en/articles/crafted-defenses-3.html) still names Hero Hunter, Hot Candle and Cake-A-Pult as current. |
| Huts, purchases and B.O.B. | Starting hut count, five-hut maximum, gear-up level prerequisites and the external unlock checked against assets and live [Builder Support](https://support.supercell.com/clash-of-clans/en/articles/builders-4.html). B.O.B.'s TH10 minimum remains a prerequisite inference. |
| October changes | Official [UI update](https://supercell.com/en/games/clashofclans/blog/news/weve-revamped-the-clash-of-clans-user-interface/) and [balance announcement](https://supercell.com/en/games/clashofclans/blog/news/balance-changes-incoming-october-2026/) reviewed. They do not announce new modeled counts, footprints or ordinary building levels; absence from notes does not prove a byte-identical current asset manifest. |
| Board, labels and coordinate format | The 44×44 board remains a reviewed model convention without independent live measurement. Labels, schematic categories, coordinate orientation and the banner's format level 1 are project conventions. |

## Corrections

- **Hero slots:** thresholds are `[[1,1],[3,2],[5,3],[7,4]]`, read from `TAVERN_LEVEL_TO_HERO_SLOT_COUNT`. TH8's maximum Hero Hall level is 2, so its modeled banner count is 1. Archer Queen still unlocks at Hero Hall 2; hero availability and active slots are different facts.
- **Firespitter:** retain the project's 45-degree direction index, but permit only `0`, `2`, `4`, `6`, corresponding to its 90-degree rotation steps. These indices are not claimed to be the game's serialization enum.
- **Multi-Gear Tower:** require `mode: long_range` or `mode: fast_attack`. These modes are corroborated by the building's normal/alternate mode fields and [Supercell's introduction](https://supercell.com/en/games/clashofclans/blog/news/get-geared-up-for-the-latest-update--3/).

Regression checks cover the corrected boundary behavior and historical reproduction. Numeric source comparison does not prove lettering quality, combat performance or in-game editor acceptance.

## Interpretation overrides and unresolved facts

The extraction retains the Town Hall singleton and ordinary level convention; Clan Castle rebuilding from TH3; B.O.B.'s TH10 minimum inferred from gear-up prerequisites; no separate Eagle Artillery at TH17–18; the phase-specific TH11 Crafting Station exception; and banner availability derived from Hero Hall thresholds. The [source notes](sources.md) explain the supporting evidence and conflicts. These interpretations are not raw CSV cells.

The latest client asset fingerprint, independently measured live board bounds and live phase expiration timestamp remain unconfirmed. The live support page and phase announcement support the recorded current variants, but the exact expiry still requires the in-game timer. The revised snapshot records these limits and keeps model-validation claims separate from live-game acceptance.

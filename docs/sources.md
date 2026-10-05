# Sources, conflicts and limits

The research was reviewed on **2026-10-04**. The rules JSON records exact URLs, SHA256 values and verification dates. Downloaded tables and external pages provide evidence; the rules JSON defines the project model. The maintained local snapshot is selected by `rulesets/current.json`; it does not automatically track live-game changes.

## Permanent game data

Selected Home Village facts come from Supercell’s public game asset snapshot `edaa611bbb095ac871fc3a692ae1a3251b5f2843`: [buildings.csv](https://game-assets.clashofclans.com/edaa611bbb095ac871fc3a692ae1a3251b5f2843/logic/buildings.csv), [townhall_levels.csv](https://game-assets.clashofclans.com/edaa611bbb095ac871fc3a692ae1a3251b5f2843/logic/townhall_levels.csv), [traps.csv](https://game-assets.clashofclans.com/edaa611bbb095ac871fc3a692ae1a3251b5f2843/logic/traps.csv), [hero_flags.csv](https://game-assets.clashofclans.com/edaa611bbb095ac871fc3a692ae1a3251b5f2843/logic/hero_flags.csv). The build was identified as 18.600.3; its hash identifies the exact snapshot. The version label alone does not establish which build or seasonal phase is current on live servers.

The files have a `Sig:` prefix with a 68-byte header, followed by LZMA with a four-byte size field. For decoding with Python’s standard library, expand that size field to the LZMA-alone eight-byte size field. CSV row 1 contains headers; row 2 contains type names. Blank continuation fields inherit the preceding value within an entity; Town Hall count blanks inherit the previous Town Hall. Retired altars, Builder Base objects, NPC-only content and unused placeholders are excluded. `tools/inspect_assets.py` inspects these reviewed fields from locally downloaded files; it neither installs code nor imports new rules automatically.

Official articles corroborate interpretation:

- [TH17 update](https://supercell.com/en/games/clashofclans/blog/game-updates/the-town-hall-17-update-is-here-2/): Eagle merge, Hero Hall/banners, Helper Hut.
- [Hero support](https://support.supercell.com/clash-of-clans/en/articles/about-heroes-pets-9.html): current Hall/hero availability.
- [TH18 update](https://supercell.com/en/games/clashofclans/blog/release-notes/town-hall-18-crash-lands-update/): Super Wizard mergers, Revenge Tower, Guardians and seasonal replacement behavior.
- [April 2026 update](https://supercell.com/en/games/clashofclans/blog/release-notes/the-sound-of-clash-update/): new ordinary levels, additional Air Bomb, wall upgrades.
- [June 2026 update](https://supercell.com/en/games/clashofclans/blog/release-notes/the-anime-fury-update-is-here/): remaining wall upgrades and further building levels.
- [August 2026 update](https://supercell.com/en/games/clashofclans/blog/release-notes/august-update-3/): later supercharges and seasonal bug fixes.

## Resolved discrepancies

| Claim | Evidence and treatment |
| --- | --- |
| TH18 has 400 walls | A community data repository added 75 upgradeable pieces to inventory. Official count data records 325. Upgrade batches do not add wall pieces. |
| Army Camp is 5×5 | Current official `Width`/`Height` are 4×4. Clan Castle is 3×3. Use current logical footprints, not sprite bounds or older tables. |
| Hero Hall unlocks at TH7 | Current assets and support put its first level at TH4. Old altars are excluded. Hero Journey’s TH7 unlock is a different feature. |
| All Crafted Defenses require the highest TH | [August phase announcement](https://supercell.com/en/games/clashofclans/blog/news/the-awesome-quest-is-here/) makes Phase 4 available from TH11. Current module assets also begin at TH11. This phase-specific evidence overrides the generic highest-TH sentence in [Crafted support](https://ingame.support.supercell.com/clash-of-clans/en/articles/crafted-defenses-3.html). |
| Three seasonal choices add three buildings | Choices use one Crafting Station footprint. Phase variants and module levels come from official seasonal asset tables. |

The 44×44 board is a **reviewed model convention**, corroborated by the [author’s grid implementation](https://github.com/laurentDellaNegra/coc-layout-ai). It was not extracted from the downloaded CSV globals; independent live-game bounds measurement is unconfirmed. This limits game-acceptance claims while making the model's checks explicit.

## Copy Base links

[Official sharing examples](https://supercell.com/en/games/clashofclans/blog/esports/queen-walkers-war-layouts-2/) use HTTPS `link.clashofclans.com/<language>?action=OpenLayout&id=...`, with decoded IDs such as `TH12:HV:<opaque>` and `TH12:WB:<opaque>`. The parser checks host, action, one ID, TH prefix, village type and URL-safe payload characters. It checks layout TH/village consistency when a link is attached.

The payload is treated as opaque. No supported coordinate-to-link API or codec was established. A published link's date does not prove it still imports successfully. Manual construction followed by the game's own Share Layout feature is the supported workflow. Keep genuine links in private layouts when they identify private designs.

## Consequential uncertainty

The CLI does not fetch live account inventory. The account owner must check the declared account facts and any explicit template assumptions. Obstacles and event objects need measured footprints. Phase timing, sprite occlusion and editor acceptance must be checked in Clash. Unknown footprints or counts that could affect validation block a pass through ruleset `uncertainties` or object review status. Source attribution does not grant a license to redistribute Supercell material; see the [Fan Content Policy](https://supercell.com/en/fan-content-policy/).

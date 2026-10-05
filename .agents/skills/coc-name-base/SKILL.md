---
name: coc-name-base
description: Design and revise complete Clash of Clans Home Village name bases through LLM-authored coordinates, Python validation, and schematic visual review; maintain versioned game rules when a Town Hall or seasonal change affects a design.
---

# Clash name-base design

Use the repository root as the working directory. This skill is ordinary Markdown and CLI instructions; it does not require a particular LLM client.

Read [design guidance](references/design.md) for name-base work. Read [rule maintenance](references/rules-maintenance.md) when current game facts are uncertain or an update changes inventory. Canonical tables live in the [wiki](../../../docs/README.md), not this skill.

1. Establish name/case, Town Hall, actual inventory and levels, completed mergers, Hero Hall, builder huts, B.O.B., Crafted Phase, obstacles and aesthetic priorities. Use confirmed preferences; ask only for material missing information. Follow [account inputs](../../../docs/accounts.md) and run `py -3.14 -m coc_base profile create --town-hall <TH> --inventory <account.json> --output profiles/account.json`. Omitted inventory means zero; use `--preset max` only when explicitly requested or acknowledged as an assumption. Do not depend on private preset files.
2. Read [inventory rules](../../../docs/rules.md), relevant [catalogue](../../../docs/catalogue.md) rows and [sources](../../../docs/sources.md). Research uncertain currency. Unresolved validation facts remain unresolved.
3. Author the **complete** layout in the [coordinate format](../../../docs/layout-format.md). Every wall, building, banner and trap needs an explicit origin and ID. Optional groups can label letters and construction sections. Any name and case are normal inputs.
4. Run `py -3.14 -m coc_base validate <layout> --json <report.json>`, then `py -3.14 -m coc_base render <layout> --output <report.html>`. Fix inventory/geometry/settings errors, resolve consequential unknowns, and inspect both views in a browser.
5. Judge lettering yourself at whole-village scale: counters, spacing, case, stroke weight and surrounding buildings. **Python cannot establish that walls spell the intended name attractively.** Revise saved coordinates and revalidate until the model passes and your visual review is convincing. Do not silently repair placements in the renderer.
6. Run `py -3.14 -m coc_base export <layout> --output <bundle directory>`, then `py -3.14 -m coc_base render <bundle directory>/layout.json --historical --output <bundle directory>/preview.html`. Deliver coordinate JSON, both schematic views, diagnostics, portable rules/profile and construction guide. Record visual conclusions separately from model results.

Commands normally use current bundled reviewed rules through `rulesets/current.json`. These are maintained local data, not an automatic live-game feed. Use `--historical` only to reproduce frozen checks; use `--ruleset PATH` for a reviewed comparison. Review migration differences and write new references before claiming a current pass. Keep personal inputs and generated outputs in ignored root folders; public examples use synthetic accounts.

If browser policy blocks a preview, respect that restriction. Use another permitted inspection method only when it is allowed; otherwise record visual review as incomplete and deliver the schematics for human review. A model pass remains valid within its scope, but it does not fulfill visual acceptance. Do not claim lettering was inspected when it was not.

Describe a successful check as “passes the reviewed model; in-game acceptance unconfirmed” until actual editor acceptance is observed. Schematics omit sprite heights. Use Clash’s own Share Layout feature after manual construction; keep genuine links opaque and never mint a copy link from coordinates.

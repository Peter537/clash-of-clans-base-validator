# Designer workflow

The LLM authors every placement. Python checks the saved layout against the model and renders schematics for inspection. Use the [agent skill](../.agents/skills/coc-name-base/SKILL.md) and [account inputs](accounts.md) to follow this workflow.

1. Establish the name and case, Town Hall, owned objects and levels, completed mergers, Hero Hall, optional huts, seasonal state, obstacles and visual preferences. Create a profile from declared facts. Use a max template only as an explicit assumption.
2. Read the selected catalogue, inventory rules and sources. Normal commands use the reviewed rules bundled with this project. Research uncertain game changes before claiming that a design matches the current game.
3. Reserve enough grass for lettering. Author explicit integer wall coordinates and place every declared building, banner and trap. Label letter and section groups for construction. Keep personal inputs in ignored folders.
4. Validate the layout and inspect both browser schematics. Correct geometry and inventory errors; resolve unknowns that could affect validation. Judge spelling, case, spacing, spaces inside letters (counters) and surrounding buildings at whole-village scale.
5. Export the frozen rules and profile, coordinate table and construction guide. Render the exported bundle with `--historical` for a reproducible preview.
6. Construct in a spare in-game layout slot. Check the actual inventory and phase, count tiles from the diamond's top origin, place wall groups, then buildings and traps. Apply settings and confirm nothing remains unplaced. Check whether real game sprites hide lettering and whether the name reads clearly at normal zoom.
7. Use Clash's Share Layout feature after saving. Store a genuine link privately when appropriate. Link format validation does not prove authenticity, availability or a coordinate match.

The public [TH3 Hi example](../examples/th3-hi/README.md) demonstrates this workflow using synthetic inventory. Follow the same procedure for a different name or lower Town Hall; the tools contain no hardcoded name design.

Report model validation and visual review separately. Use “passes the reviewed model; in-game acceptance unconfirmed” until actual construction is observed. A schematic cannot establish combat strength or reproduce game artwork.

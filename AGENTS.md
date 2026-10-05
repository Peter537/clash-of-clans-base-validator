# Project instructions

For designing or revising a Clash name base, read [.agents/skills/coc-name-base/SKILL.md](.agents/skills/coc-name-base/SKILL.md). Other LLM tools can follow the same Markdown and CLI commands.

- Target Python 3.14 and its standard library. No layout generator, font engine, editor or dashboard.
- The LLM authors every placement. Python checks coordinates and renders schematics; passing geometry does not establish attractive lettering.
- Rules JSON is canonical. Preserve existing snapshots and layouts when adding a new Town Hall or seasonal phase. Read [docs/updating-rules.md](docs/updating-rules.md) before changing game facts.
- Establish actual inventory first with `profile create`; max assumptions require explicit `--preset max`. Read [docs/accounts.md](docs/accounts.md).
- Normal commands resolve `rulesets/current.json`. Use `--historical` for frozen checks or `--ruleset PATH` for explicit comparison. Never silently rewrite old profile/layout references.
- Root `layouts/`, `profiles/`, `reports/`, `exports/`, `.skill-evaluation/` and `.test-work/` are private or disposable. Preserve personal artifacts and keep public tests independent of them. Public examples and synthetic fixtures belong in `examples/` and `tests/`.
- Reports must say model validation only, with in-game acceptance unconfirmed until actual construction is observed.
- Do not mint copy links. Preserve genuine game-generated links and treat their payloads as opaque.
- Regenerate tables with `py -3.14 -m coc_base docs`, run the documented tests and `py -3.14 tools/check_docs.py` after relevant changes.

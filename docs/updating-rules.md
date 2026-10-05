# Maintain current rules and preserve frozen designs

Use this procedure for a new Town Hall, building, level, seasonal phase or placement rule. Preserve dated snapshots and their IDs as permanent records of reviewed evidence. Everyday commands load the maintained version through `rulesets/current.json`.

1. Read official release notes and support articles. Inspect pinned game assets where counts or footprints lack evidence. Record URLs, verification date, build/hash and raw-file SHA256. Unknown facts that could affect validation remain blocking uncertainties.
2. Create a new JSON snapshot with a new ID and verification date. Extend Town Hall keys, object levels, count limits, merger recipes, hero prerequisites and seasonal caps as required. Preserve all prior snapshots. Review a future Town Hall's rules before treating it as supported.
3. Check the new snapshot with explicit `--ruleset PATH` commands. Create a profile from actual account facts or explicitly request a derived max template. No private preset file is required. Regenerate reference tables into a scratch documentation directory first.
4. Add synthetic regressions, run the documented checks, and inspect affected placements. Migration reports include type and count changes, affected IDs, board and phase changes. ID mismatches remain unresolved.
5. After reviewing the evidence, update the selector. Its schema is `{"schema_version":1,"ruleset":"home-YYYY-MM-DD.json"}`; the snapshot path is relative to `rulesets/`. Regenerate the current catalogue and update source explanations for changes that affect the model.
6. Review an old account and layout against the new current model. Write a new profile/layout version with reviewed IDs and references, revising placements or settings as needed. Never modify an old snapshot or silently rewrite a saved layout.
7. Repeat whole-village visual review and export a frozen bundle. Inventory changes can crowd lettering even when footprints stay the same. Use `--historical` when reproducing an old bundle's validation.

The CLI and max-template code derive supported Town Halls from selected rules. There is no hardcoded default snapshot path or automatic network update. Changing the selector does not verify future releases or live server timing.

Keep rule maintenance separate from design revision. When the model is wrong, review the evidence and update the rules. When coordinates are wrong, fix the placements. Do not weaken overlap or completeness checks to make an image pass.

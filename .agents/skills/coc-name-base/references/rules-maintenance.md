# Rule maintenance

Follow [updating rules](../../../../docs/updating-rules.md), with [sources and conflicts](../../../../docs/sources.md) as the evidence record. The JSON rules are canonical; change them before regenerating tables.

Keep permanent counts, merger consumption, optional account inventory and temporary seasonal variants distinct. A release note about upgrading more walls does not add wall pieces. A Crafted Defense choice replaces its platform state in the same footprint. More unlocked heroes do not add banners.

Version changes instead of overwriting frozen rules or old layouts. Update `rulesets/current.json` only after reviewing a new snapshot. Normal commands then compare old layouts against that bundled current model; `--historical` reproduces frozen checks. Inspect affected IDs and write a new account profile and layout after review. Unknown consequential facts must prevent an unconditional pass.

Use Python 3.14’s standard library. The public asset inspection helper only decodes and displays data; it does not auto-import rules or generate bases. Verify referenced commands against `py -3.14 -m coc_base --help`, run relevant regression checks and regenerate catalogue documentation.

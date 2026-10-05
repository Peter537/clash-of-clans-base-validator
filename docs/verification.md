# Reproducible verification

Run from the repository root with Python 3.14:

```powershell
py -3.14 -m unittest discover -s tests -v
py -3.14 -m coc_base docs
py -3.14 tools/check_docs.py
```

Tests use synthetic inventories and the public Hi example. They do not read personal layouts, profiles, exports, reports or skill evaluations from the root folders. Fixed arrangements of objects test inventory and geometry; they are not a production base generator.

The suite checks supported Town Halls, wall shortages, partial inventories, optional huts, Hero Hall and hero prerequisites, mergers, seasonal variants, mixed levels and account conflicts. It also checks boundaries, overlap, blockers, IDs, JSON round trips, export coordinates, rendered footprints, rules-selection modes and portability of frozen bundles.

Regression tests check that malformed input is rejected before output is written, existing files are preserved, HTML/SVG text is escaped, integer types are exact, and reservation permissions are enforced. They also check exports of placements with unusable coordinates. Historical and explicit checks also run with missing or malformed current selectors; default checks must still reject them.

`tools/check_docs.py` checks public local links and anchors, generated-catalogue consistency, skill structure, public content for stale private references, and standard-library runtime imports. It excludes ignored personal and disposable folders. Source review dates and hashes belong to the selected snapshot.

## Publication boundary

Keep source, rules, documentation, skills, synthetic fixtures and public examples in version control. Root `layouts/`, `profiles/`, `reports/`, `exports/`, `.skill-evaluation/` and `.test-work/` are ignored, alongside Python caches. Preserve personal designs locally. Output paths in documented commands are intentional; public Markdown must not depend on files inside ignored folders.

Before release, run the tests and quick-start commands from an isolated copy containing only public files. Verify ignore patterns in a separate temporary Git repository: ignored root folders stay excluded while examples, rules, skills and fixtures remain included. Do not alter the working project's Git state for that check.

If private files were committed previously, ignore patterns do not remove them from history or the index. Check the publication set before changing repository visibility. Personal reviews and one-time verification records belong in ignored reports.

## Claims and limits

A model pass confirms declared inventory, footprints, geometry, levels and settings under selected reviewed rules. Missing account level distributions limit checks to Town Hall bounds and prerequisites. Current bundled rules are maintained local data, not a live-game service.

Review visual readability in a browser, manually or with an LLM. The model does not check whether real game sprites hide lettering, whether the layout performs well in attacks, whether a copy link is authentic, or whether the in-game editor accepts the design. Record actual construction evidence separately before making stronger claims.

# Validator CLI

Run the CLI from the repository root with Python 3.14. It uses only Python's standard library, so no package installation is needed. On Windows, use the launcher command `py -3.14`.

```powershell
py -3.14 -m coc_base --help
py -3.14 -m coc_base profile create --town-hall 3 --inventory examples/th3-hi/inventory.json --output profiles/account.json
py -3.14 -m coc_base validate examples/th3-hi/layout.json --json reports/hi.validation.json
py -3.14 -m coc_base render examples/th3-hi/layout.json --output reports/hi.html
py -3.14 -m coc_base export examples/th3-hi/layout.json --output exports/hi
py -3.14 -m coc_base docs
```

`profile create` declares an account from JSON and flags. See [account inputs](accounts.md). Without `--preset max`, it includes only declared inventory and an automatically supplied Town Hall.

`validate` prints diagnostics and optionally writes JSON. Checks include exact inventory, walls, footprints, overlaps, boundaries, obstacles, reservations, IDs, availability, levels, supplied distributions, settings, banners and mergers. Unknown rules are reported separately from known errors.

`render` writes HTML, `.isometric.svg`, `.overhead.svg` and `.validation.json` files. Known invalid placements have red outlines. Out-of-bounds objects remain visible. Objects without usable coordinates cannot be drawn; their diagnostics are still included. Both views share identical coordinates and model footprints. Rendering never repairs placements.

`export` writes `layout.json`, frozen `ruleset.json`, `profile.json`, `validation.json`, `coordinates.csv` and `construction.md`. Well-formed layouts with invalid or unresolved placements can be exported for review with their status. The construction guide's wall rows omit objects without usable integer coordinates and explain the omissions. The supplied values remain in JSON and CSV. You can move the bundle files together; the CLI still runs from a project checkout.

If the input structure is malformed, the command returns exit code 3 before creating or overwriting output files. Examples include `objects: null`, non-object entries, null groups or visual reviews, non-integer inventory counts, and an `allow_types` value that is not an array of strings. Placement errors such as overlaps, out-of-bounds footprints and unusable coordinates still produce model diagnostics and outputs for review.

```powershell
py -3.14 -m coc_base validate exports/hi/layout.json --historical
py -3.14 -m coc_base render exports/hi/layout.json --historical --output exports/hi/preview.html
```

`docs` regenerates the catalogue using the snapshot chosen by the current selector. `--ruleset PATH` and `--output DIRECTORY` select another snapshot and destination. The rules JSON remains the authoritative source.

## Rules selection

Choose one rules mode for validation, rendering or export:

| Selection | Meaning |
| --- | --- |
| Default | Current bundled reviewed snapshot from `rulesets/current.json` |
| `--historical` | Frozen rules referenced relative to the layout |
| `--ruleset PATH` | Explicit snapshot, compared with the frozen reference |

"Current" means the reviewed rules bundled with this project; the CLI does not fetch live-game updates. Reports record the mode, selected snapshot, verification date and current snapshot ID. Every mode uses the account profile referenced by the layout.

Historical and explicit selections work even when current rules cannot be loaded. In that case reports set `current_ruleset_id` to `null` and include `current_ruleset_notice`. The notice is informational and does not change the selected model's result. Default mode still requires usable current rules and returns input-error code 3 when they are unavailable.

If current or explicit rules differ from frozen rules, migration diagnostics identify changed types, count limits, affected IDs, board changes and seasonal changes. ID mismatches remain unresolved until the designer reviews updated profile/layout references. A missing frozen file prevents comparison, but current rules can still check geometry. Updating the selector never edits saved inputs.

Replace `PATH/TO/reviewed-snapshot.json` with a real snapshot for an explicit comparison:

```powershell
py -3.14 -m coc_base validate examples/th3-hi/layout.json --ruleset PATH/TO/reviewed-snapshot.json --json reports/migration.json
```

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Model pass, or successful profile/docs creation |
| 1 | Known validation errors |
| 2 | Unresolved rules without known errors; argparse also uses 2 for usage errors |
| 3 | Unreadable, malformed or inconsistent input |

## Checks and browser inspection

```powershell
py -3.14 -m unittest discover -s tests -v
py -3.14 -m coc_base docs
py -3.14 tools/check_docs.py
```

Open HTML in a browser. If HTTP is required, start a temporary loopback server before opening the preview:

```powershell
py -3.14 -m http.server 8765 --bind 127.0.0.1 --directory reports
```

Open `http://127.0.0.1:8765/hi.html` and stop the server after review. Respect browser restrictions; record visual acceptance as incomplete if inspection is blocked. A model pass does not establish lettering quality or in-game acceptance.

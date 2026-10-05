# clash-of-clans-base-validator

Validate LLM-authored Clash of Clans Home Village layouts, inspect tile footprints, and export manual construction guides. Python 3.14 checks inventory and geometry; the LLM designs placements and reviews lettering. The runtime uses only the standard library.

## Quick start

Run from the repository root with Python 3.14. No package installation, API key or game login is required. The public [TH3 Hi example](examples/th3-hi/README.md) has a synthetic account, 50 walls and explicit placements.

```powershell
py -3.14 -m coc_base validate examples/th3-hi/layout.json --json reports/hi.validation.json
py -3.14 -m coc_base render examples/th3-hi/layout.json --output reports/hi.html
py -3.14 -m coc_base export examples/th3-hi/layout.json --output exports/hi
py -3.14 -m coc_base render exports/hi/layout.json --historical --output exports/hi/preview.html
```

Open `reports/hi.html` in a browser for overhead and isometric views. `exports/hi/` contains frozen inputs, coordinates and a construction guide. These output directories are ignored by Git.

## Use your account

Use the validator with your account’s current inventory and levels. List the objects you own; omitted object types count as zero. The command includes one Town Hall automatically. Include your Builder's Hut count and any required Hero Hall or seasonal information.

```powershell
py -3.14 -m coc_base profile create --town-hall 3 --inventory examples/th3-hi/inventory.json --output profiles/account.json
py -3.14 -m coc_base profile create --town-hall 12 --count builders_hut=3 --count wall=240 --output profiles/partial.json
```

The second command describes a partial account: one Town Hall, three huts and 240 walls. Include every object you own before designing a complete base. Use `--preset max` only when you explicitly want to assume maximum inventory and levels. See [account inputs](docs/accounts.md) for mixed levels, overrides, obstacles and optional unlocks.

An LLM can follow the [coc-name-base skill](.agents/skills/coc-name-base/SKILL.md) to author layouts for any name and supported Town Hall. The [wiki](docs/README.md) covers coordinates, commands, the game catalogue and maintenance.

## Rules and verification

Commands normally load the reviewed rules snapshot selected by `rulesets/current.json`. Here, "current" means the rules bundled with this project; the CLI does not fetch live game updates. `--historical` reproduces a layout's frozen check; `--ruleset PATH` compares an explicit snapshot. Existing layouts are never silently migrated.

```powershell
py -3.14 -m unittest discover -s tests -v
py -3.14 -m coc_base docs
py -3.14 tools/check_docs.py
```

A `PASS` means the declared inventory and placements satisfy the reviewed model. It does not confirm attractive lettering, attack performance or in-game acceptance. Schematics omit game sprites and heights. Genuine Copy Base links come from Clash's Share Layout feature; the CLI checks their format and does not generate them.

## License and attribution

Code and original project documentation are [MIT licensed](LICENSE), copyright Peter537. Game facts retain their [source attribution](docs/sources.md); this license does not grant rights to Supercell's trademarks, assets or other material.

This project is unofficial and is not endorsed by Supercell. See [Supercell's Fan Content Policy](https://supercell.com/en/fan-content-policy/).

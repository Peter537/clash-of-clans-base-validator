# TH3 Hi example

This LLM-authored display layout uses a synthetic TH3 account with two Builder's Huts and 50 walls. All 74 objects have explicit coordinates in [layout.json](layout.json). [profile.json](profile.json) records the full inventory and level distributions for the synthetic account. Use [inventory.json](inventory.json) as input to `profile create` to create another profile.

The capital H uses 34 walls. The dotted lowercase i uses 16, including its base. Upper buildings and lower defenses leave open grass around the lettering. Attack performance has not been evaluated.

On 2026-10-04, the designer inspected both browser schematics and judged the whole-village lettering to read clearly as **Hi**. The layout records this review separately from Python validation. Schematics omit sprite heights; in-game acceptance remains unconfirmed.

From the repository root:

```powershell
py -3.14 -m coc_base validate examples/th3-hi/layout.json --historical --json reports/hi.validation.json
py -3.14 -m coc_base render examples/th3-hi/layout.json --historical --output reports/hi.html
py -3.14 -m coc_base export examples/th3-hi/layout.json --historical --output exports/hi
```

Open `reports/hi.html` to inspect both views. Use `exports/hi/construction.md` and the exported CSV for manual construction. Outputs are ignored by Git; the example's input files remain public.

These inputs retain their `home-2026-10-04` snapshot references. The commands reproduce that historical model pass. To compare with newer bundled rules, omit `--historical`; the CLI reports the snapshot ID mismatch without rewriting these inputs.

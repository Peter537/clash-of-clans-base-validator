"""Static SVG inspection views from the same tile rectangles used by validation."""

from html import escape
import json
from pathlib import Path

from .io import footprint, write_json
from .validate import integer, validate


COLORS = {"wall": ("#f4d58a", "#b3914e"), "defense": ("#538e99", "#91bdc5"),
          "resource": ("#7d7198", "#b4a4d1"), "army": ("#7d9166", "#b5c799"),
          "town_hall": ("#ba775c", "#efb198"), "utility": ("#737d8f", "#aab7ce"),
          "trap": ("#455f57", "#92aa9d"), "hero": ("#99854c", "#d8c685")}


def project(x, y, isometric=False):
    return (52 + (x - y + 44) * 10, 36 + (x + y) * 5) if isometric else (48 + x * 18, 40 + y * 18)


def polygon(x, y, w, h, iso):
    return " ".join(f"{px:g},{py:g}" for px, py in
                    [project(x, y, iso), project(x+w, y, iso),
                     project(x+w, y+h, iso), project(x, y+h, iso)])


def svg(layout, rules, profile, result, iso=False):
    invalid = {oid for d in result["diagnostics"] for oid in d["objects"]}
    content = []
    board = rules["board"]
    w, h = board["width"], board["height"]
    extent = [project(0, 0, iso), project(w, h, iso), project(w, 0, iso), project(0, h, iso)]
    content.append(f'<polygon points="{polygon(0,0,w,h,iso)}" fill="#233b2d" stroke="#cad6c7" stroke-width="1.3"/>')
    for i in range(0, max(w, h)+1):
        for a, b in (((i, 0), (i, h)), ((0, i), (w, i))):
            ax, ay = project(*a, iso); bx, by = project(*b, iso)
            content.append(f'<path d="M{ax},{ay} L{bx},{by}" stroke="#bad0b6" stroke-opacity="{.17 if i%5==0 else .055}" stroke-width=".6"/>')
        if i % 5 == 0 or i == max(w, h):
            px, py = project(i, 0, iso); qx, qy = project(0, i, iso)
            content.append(f'<text x="{px}" y="{py-9}" class="axis">{i}</text><text x="{qx-16}" y="{qy+3}" class="axis">{i}</text>')
    px, py = project(w/2, 0, iso); qx, qy = project(0, h/2, iso)
    content.append(f'<text x="{px}" y="{py-23}" class="axis">x →</text><text x="{qx-30}" y="{qy}" class="axis">y ↓</text>')
    for area in [*profile.get("blocked_areas", []), *layout.get("reserved_areas", [])]:
        if not isinstance(area, dict) or not all(integer(area.get(k)) for k in ("x", "y", "width", "height")):
            continue
        content.append(f'<polygon points="{polygon(area["x"],area["y"],area["width"],area["height"],iso)}" fill="#ead997" fill-opacity=".03" stroke="#cfc59a" stroke-opacity=".45" stroke-dasharray="4 4"><title>{escape(str(area.get("label","reserved area")))}</title></polygon>')
    for obj in layout.get("objects", []):
        if not isinstance(obj, dict) or not all(integer(obj.get(k)) for k in ("x", "y")):
            continue
        if isinstance(obj.get("type"), str) and obj["type"] in rules["objects"]:
            x, y, ow, oh = footprint(obj, rules)
            spec = rules["objects"][obj["type"]]
        else:
            x, y, ow, oh = obj["x"], obj["y"], 1, 1
            spec = {"category": "utility", "label": "?", "name": "Unknown footprint"}
        oid = str(obj.get("id", "?"))
        extent += [project(x, y, iso), project(x+ow, y+oh, iso), project(x+ow, y, iso), project(x, y+oh, iso)]
        fill, stroke = COLORS.get(spec["category"], COLORS["utility"])
        is_wall = obj.get("type") == "wall"
        if oid in invalid:
            stroke = "#ff776d"
        title = f'{oid}: {spec["name"]} L{obj.get("level","?")} at ({x},{y}); {ow}x{oh}'
        if obj.get("settings"):
            title += "; " + json.dumps(obj["settings"], ensure_ascii=False)
        attrs = (f'data-id="{escape(oid,quote=True)}" data-type="{escape(str(obj.get("type")),quote=True)}" '
                 f'data-x="{x}" data-y="{y}" data-width="{ow}" data-height="{oh}"')
        content.append(f'<g {attrs}><title>{escape(title)}</title>')
        points = polygon(x, y, ow, oh, iso)
        content.append(f'<polygon points="{points}" fill="{fill}" fill-opacity="{1 if is_wall else .7}" stroke="{stroke}" stroke-width="{1.8 if oid in invalid else .75}"/>')
        if not is_wall:
            px, py = project(x+ow/2, y+oh/2, iso)
            label = spec["label"]
            suffix = oid.rsplit("-",1)[-1]
            text = f"{label}{int(suffix)}" if suffix.isdigit() else label
            size = (6 if iso else 8) if spec["category"] == "trap" else (8 if iso else 10)
            content.append(f'<text x="{px}" y="{py+3}" class="object-label" font-size="{size}">{escape(text)}</text>')
        content.append('</g>')
    minx, miny = min(x for x, y in extent)-45, min(y for x, y in extent)-40
    maxx, maxy = max(x for x, y in extent)+45, max(y for x, y in extent)+35
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{minx} {miny} {maxx-minx} {maxy-miny}" role="img" '
            f'aria-label="{"Isometric" if iso else "Overhead"} schematic; exact tile footprints">'
            '<style>.axis{font:10px system-ui;fill:#bdcdbc;text-anchor:middle}.object-label{font-family:system-ui;fill:#f6f1dd;text-anchor:middle;pointer-events:none}</style>'
            + ''.join(content) + '</svg>')


def render(layout, rules, profile, output, *, context=None):
    output = Path(output)
    result = validate(layout, rules, profile)
    result.update(context or {})
    iso, overhead = svg(layout, rules, profile, result, True), svg(layout, rules, profile, result)
    errors = ''.join(f'<li><strong>{escape(d["code"])}</strong> · {escape(d["message"])}</li>' for d in result["diagnostics"]) or '<li>No model errors or unresolved rules.</li>'
    counts = result["placed_counts"]
    rows = ''.join(f'<tr><th>{escape(rules["objects"].get(k,{}).get("name",k))}</th><td>{escape(str(counts.get(k,0)))}</td><td>{escape(str(profile["inventory"].get(k,0)))}</td></tr>' for k in sorted(counts.keys() | profile["inventory"].keys()))
    legend = ''.join(f'<span><i style="background:{c[0]}"></i>{escape(k.replace("_"," "))}</span>' for k,c in COLORS.items())
    selection = escape(f"Rules: {result.get('rules_mode', 'supplied')} · {rules['id']} · reviewed {rules['verified_on']}")
    if "current_ruleset_notice" in result:
        selection += "<br>" + escape(result["current_ruleset_notice"])
    migration = ('<details><summary>Migration comparison</summary><pre>' + escape(json.dumps(result['migration'], indent=2)) + '</pre></details>') if 'migration' in result else ''
    html = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(layout.get("name","Layout"))} · TH{profile["town_hall"]} inspection</title>
<style>
:root{{color-scheme:dark;font:16px system-ui;background:#101b17;color:#e7ecd9}}*{{box-sizing:border-box}}body{{margin:0}}main{{max-width:1180px;margin:auto;padding:28px}}header{{display:flex;align-items:end;justify-content:space-between;gap:20px;flex-wrap:wrap}}h1{{font:600 36px Georgia;margin:8px 0}}h2{{font-size:20px;margin:0 0 14px}}p{{line-height:1.55}}.eyebrow{{color:#beccba;font-size:13px;letter-spacing:.1em}}.status{{border:1px solid #8fad8d;padding:12px 18px;border-radius:6px;color:#d5eccd}}nav{{display:flex;gap:18px;margin:24px 0}}a{{color:#f4d58a}}.panel{{border:1px solid #35483b;background:#18281f;border-radius:8px;padding:22px;margin:22px 0}}.legend{{display:flex;gap:18px;flex-wrap:wrap;font-size:13px;color:#c2cebe}}i{{display:inline-block;width:10px;height:10px;margin-right:6px}}svg{{display:block;width:100%;height:auto}}.caption{{font-size:13px;color:#b8c8b7}}.columns{{display:grid;grid-template-columns:1fr 1fr;gap:22px}}table{{width:100%;border-collapse:collapse;font-size:14px}}th{{font-weight:400;text-align:left}}td{{text-align:right}}th,td{{padding:7px;border-bottom:1px solid #35483b}}code{{font-size:12px;overflow-wrap:anywhere}}li{{line-height:1.6}}details summary{{cursor:pointer;color:#f4d58a}}@media(max-width:700px){{main{{padding:16px}}.columns{{grid-template-columns:1fr}}.panel{{padding:12px}}h1{{font-size:30px}}}}
</style><main><header><div><div class="eyebrow">HOME VILLAGE · TH{profile["town_hall"]} · {escape(rules["verified_on"])}</div><h1>{escape(layout.get("name","Layout"))}</h1><p>{len(layout.get("objects",[]))} objects · {result["placed_counts"].get("wall",0)} walls · {result["occupied_tiles"]} occupied tiles</p></div><div class="status">{result["status"]} · reviewed model</div></header>
<p class="caption">Model validation only. In-game acceptance unconfirmed. Lettering needs LLM/manual visual review.<br>Inspection schematics use tile footprints; they do not reproduce building heights or game sprites.<br>{selection}<br>{escape(result['account_levels']['statement'])}</p>{migration}
<nav><a href="#isometric">Isometric view</a><a href="#overhead">Overhead view</a><a href="#checks">Validation & inventory</a></nav><div class="legend">{legend}</div>
<section class="panel" id="isometric"><h2>Isometric · whole village</h2>{iso}<p class="caption">Both views use the same coordinates. All walls have the same schematic color, including framing walls. Hover over a labelled shape for its full ID, level and origin.</p></section>
<section class="panel" id="overhead"><h2>Overhead · construction grid</h2>{overhead}<p class="caption">Origins are the upper-left corners of footprints. Tile coordinates run 0–{rules['board']['width']-1} on x and 0–{rules['board']['height']-1} on y. Reserved areas have dashed outlines. Red strokes identify reported object errors.</p></section>
<section class="columns" id="checks"><div class="panel"><h2>Validation</h2><p>{result["errors"]} errors · {result["unknowns"]} unresolved rules</p><ul>{errors}</ul><p>Visual review: {escape(str(layout.get("visual_review",{}).get("conclusion","pending")))}</p><details><summary>Snapshot identity</summary><p>{escape(rules["id"])}</p><code>Layout SHA256: {result["layout_sha256"]}<br>Rules SHA256: {result["ruleset_sha256"]}<br>Profile SHA256: {result["profile_sha256"]}</code></details></div>
<div class="panel"><h2>Complete inventory</h2><table><tr><th>Object</th><th>Placed</th><th>Required</th></tr>{rows}</table></div></section><p class="caption">This project is unofficial and is not endorsed by Supercell. See <a href="https://supercell.com/en/fan-content-policy/">Supercell’s Fan Content Policy</a>.</p></main></html>'''
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    write_json(output.with_suffix(".validation.json"), result)
    output.with_suffix(".isometric.svg").write_text(iso, encoding="utf-8")
    output.with_suffix(".overhead.svg").write_text(overhead, encoding="utf-8")
    return result

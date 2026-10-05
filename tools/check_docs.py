"""Offline wiki/skill link, generated-table, and runtime dependency checks."""

from pathlib import Path
import re
import sys
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from coc_base.docs import generated_docs
from coc_base.io import read_json
from tools.public_files import public_files


def anchors(source):
    result, used = set(), {}
    for title in re.findall(r"^#{1,6}\s+(.+)$", source, re.M):
        slug = re.sub(r"[^\w\s-]", "", title.lower()).replace(" ", "-")
        occurrence = used.get(slug, 0)
        used[slug] = occurrence + 1
        result.add(slug + (f"-{occurrence}" if occurrence else ""))
    return result


def check(root):
    errors = []
    root = Path(root).resolve()
    publication = {p.resolve() for p in public_files(root)}
    for path in sorted(publication):
        if path.suffix not in {".md", ".json", ".yaml", ".py"}:
            continue
        source = path.read_text(encoding="utf-8")
        if re.search(r"https?://chatgpt\.com/c/|[A-Za-z]:[\\/]Users[\\/]|th18-(?:uppercase|titlecase)|th4-al\.json", source):
            errors.append(f"Private or stale reference: {path.relative_to(root)}")
        if path.suffix != ".md":
            continue
        for link in re.findall(r"\]\(([^)]+)\)", source):
            if link.startswith(("https:", "http:")):
                continue
            target, _, fragment = unquote(link).partition("#")
            destination = (path.parent / target).resolve() if target else path
            if not destination.exists():
                errors.append(f"Broken link {path.relative_to(root)}: {link}")
            elif destination.is_file() and destination not in publication:
                errors.append(f"Link depends on non-public file {path.relative_to(root)}: {link}")
            elif fragment and destination.suffix == ".md" and fragment not in anchors(destination.read_text(encoding="utf-8")):
                errors.append(f"Broken anchor {path.relative_to(root)}: {link}")
        if (re.search(r"browser designer|font engine|graphical editor|dashboard",source,re.I)
                and path.name not in {"AGENTS.md"}):
            errors.append(f"Review obsolete architecture wording: {path.relative_to(root)}")
    selector = read_json(root/"rulesets/current.json")
    rules = read_json(root/"rulesets"/selector["ruleset"])
    if (root/"docs/catalogue.md").read_text(encoding="utf-8") != generated_docs(rules):
        errors.append("Generated catalogue differs from canonical JSON")
    skill = (root/".agents/skills/coc-name-base/SKILL.md").read_text(encoding="utf-8")
    if not re.match(r"\A---\nname: coc-name-base\ndescription: [^\n]+\n---\n",skill):
        errors.append("Skill frontmatter requires name and a single-line description")
    if "$coc-name-base" not in (root/".agents/skills/coc-name-base/agents/openai.yaml").read_text(encoding="utf-8"):
        errors.append("Skill UI invocation is missing")
    if not all(k in skill for k in ("profile create", "--preset max", "--historical", "validate", "render", "export", "in-game acceptance unconfirmed")):
        errors.append("Skill workflow lacks an acceptance step")
    imports = set()
    import ast
    for path in (root/"coc_base").glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node,ast.Import):
                imports.update(n.name.split(".")[0] for n in node.names)
            elif isinstance(node,ast.ImportFrom) and not node.level and node.module:
                imports.add(node.module.split(".")[0])
    if imports - sys.stdlib_module_names:
        errors.append(f"Non-standard-library runtime imports: {imports-sys.stdlib_module_names}")
    return errors


if __name__ == "__main__":
    failures = check(Path(__file__).resolve().parents[1])
    print("\n".join(failures) if failures else "PASS: local links, generated catalogue, skill structure and standard-library runtime")
    raise SystemExit(bool(failures))

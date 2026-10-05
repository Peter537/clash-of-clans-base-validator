"""The public source set used by offline documentation and release checks."""

from pathlib import Path


PUBLIC_DIRECTORIES = ("coc_base", "docs", "examples", "rulesets", "tests", "tools", ".agents")
PUBLIC_ROOT_FILES = ("README.md", "AGENTS.md", "LICENSE", ".gitignore")


def public_files(root):
    root = Path(root)
    paths = [root / name for name in PUBLIC_ROOT_FILES if (root / name).is_file()]
    for name in PUBLIC_DIRECTORIES:
        paths.extend(p for p in (root / name).rglob("*") if p.is_file()
                     and "__pycache__" not in p.parts and p.suffix not in (".pyc", ".pyo"))
    return sorted(paths)

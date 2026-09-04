"""Find maintenance gaps in the repo. Detection is code, no LLM.

Used by the sdlc workflow's janitor job when no `ready` ticket exists:

    python agents/janitor_scan.py [--root .] [--first]

Prints a JSON list of gaps `{"kind", "target", "detail"}`, highest priority
first. `--first` prints only the first gap.
"""

import argparse
import ast
import json
import re
import sys
from pathlib import Path

KIND_PRIORITY = ["unused_dependency", "missing_tests", "dead_code", "missing_docs"]
SKIP_DIRS = {".venv", ".git", "__pycache__", ".claude"}
SKIP_DEAD_CODE_NAMES = {"run", "main"}
MIN_README_CHARS = 300


def _py_files(root: Path, sub: str = "") -> list[Path]:
    base = root / sub if sub else root
    return sorted(
        p for p in base.rglob("*.py") if not (set(p.relative_to(root).parts) & SKIP_DIRS)
    )


def _casino_modules(root: Path) -> list[Path]:
    return [p for p in _py_files(root, "casino") if p.name != "__init__.py"]


def _gap(kind: str, target: str, detail: str) -> dict:
    return {"kind": kind, "target": target, "detail": detail}


def missing_tests(root: Path) -> list[dict]:
    """Modules under casino/ without a tests/test_<module>.py."""
    return [
        _gap("missing_tests", str(m.relative_to(root)), f"no tests/test_{m.stem}.py")
        for m in _casino_modules(root)
        if not (root / "tests" / f"test_{m.stem}.py").exists()
    ]


def unused_dependency(root: Path) -> list[dict]:
    """Names in requirements.txt never imported under casino/ or tests/."""
    req = root / "requirements.txt"
    if not req.exists():
        return []
    imported = set()
    for path in _py_files(root, "casino") + _py_files(root, "tests"):
        imported |= _imported_modules(path)
    gaps = []
    for line in req.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        name = re.split(r"[=<>!~\[; ]", line, maxsplit=1)[0].lower().replace("-", "_")
        if name and name not in imported:
            gaps.append(_gap("unused_dependency", name, f"{line} is declared but never imported"))
    return gaps


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0].lower() for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0].lower())
    return names


def dead_code(root: Path) -> list[dict]:
    """Public functions or methods under casino/ referenced nowhere else."""
    corpus = {p: p.read_text() for p in _py_files(root)}
    gaps = []
    for module in _casino_modules(root):
        for node in ast.walk(ast.parse(corpus[module])):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            name = node.name
            if name.startswith("_") or name in SKIP_DEAD_CODE_NAMES:
                continue
            pattern = re.compile(rf"\b{re.escape(name)}\b")
            refs = sum(len(pattern.findall(text)) for text in corpus.values())
            if refs <= 1:
                gaps.append(
                    _gap("dead_code", f"{module.relative_to(root)}::{name}", "defined but never called or tested")
                )
    return gaps


def missing_docs(root: Path) -> list[dict]:
    """Modules without a docstring, and a README shorter than the threshold."""
    gaps = [
        _gap("missing_docs", str(m.relative_to(root)), "no module docstring")
        for m in _casino_modules(root)
        if ast.get_docstring(ast.parse(m.read_text())) is None
    ]
    readme = root / "README.md"
    size = len(readme.read_text()) if readme.exists() else 0
    if size < MIN_README_CHARS:
        gaps.append(_gap("missing_docs", "README.md", f"README is {size} chars, under {MIN_README_CHARS}"))
    return gaps


DETECTORS = {
    "unused_dependency": unused_dependency,
    "missing_tests": missing_tests,
    "dead_code": dead_code,
    "missing_docs": missing_docs,
}


def scan(root: Path) -> list[dict]:
    """Run every detector, return gaps in kind priority order."""
    gaps = []
    for kind in KIND_PRIORITY:
        gaps.extend(DETECTORS[kind](root))
    return gaps


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--first", action="store_true", help="print only the first gap")
    args = parser.parse_args()
    gaps = scan(Path(args.root).resolve())
    print(json.dumps(gaps[0] if args.first and gaps else ({} if args.first else gaps), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

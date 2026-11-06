"""A33: the general kernel carries no ticker-specific patched answers.

Every module under ``engine/fundamental_forensics/`` is parsed and its string
constants (docstrings excluded) are checked for the five-issuer tickers and
CIKs.  The only admitted literals are the AAPL golden-layer accessions that pin
the offline golden fixtures; a new stress issuer must arrive through governed
packs and configuration, never through a branch on its ticker or CIK."""
from __future__ import annotations

import ast
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
KERNEL = ROOT / "engine" / "fundamental_forensics"
TICKERS = frozenset({"AAPL", "SNOW", "CAT", "BAC", "GOOGL", "GOOG"})
CIKS = ("320193", "1640147", "18230", "70858", "1652044")
CIK_RE = re.compile(r"(?<![0-9])0*(?:" + "|".join(CIKS) + r")(?![0-9])")
GOLDEN_LAYER = {
    "ixbrl_raw_ledger.py": {"0000320193-25-000079", "0000320193-26-000020"},
    "statement_graph.py": {"0000320193-25-000079", "0000320193-26-000020"},
}


def _docstring_ids(tree: ast.AST) -> set[int]:
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                ids.add(id(body[0].value))
    return ids


def _hits(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    docstrings = _docstring_ids(tree)
    allowed = GOLDEN_LAYER.get(path.name, set())
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str) or id(node) in docstrings:
            continue
        value = node.value
        if value in allowed:
            continue
        if value.strip().upper() in TICKERS and value.strip() == value.strip().upper():
            hits.append(f"{path.name}:{node.lineno} ticker {value!r}")
        elif CIK_RE.search(value):
            hits.append(f"{path.name}:{node.lineno} cik {value!r}")
    return hits


def test_a33_kernel_has_no_ticker_or_cik_literals_outside_the_golden_layer() -> None:
    modules = sorted(KERNEL.rglob("*.py"))
    assert len(modules) > 10
    hits = [hit for path in modules for hit in _hits(path)]
    assert hits == []


def test_a33_golden_layer_allowlist_is_still_live() -> None:
    for name, values in GOLDEN_LAYER.items():
        source = (KERNEL / name).read_text(encoding="utf-8")
        assert all(value in source for value in values), name


def test_a33_guard_detects_a_patched_ticker_branch(tmp_path: Path) -> None:
    patched = tmp_path / "patched.py"
    patched.write_text('def f(t):\n    if t == "SNOW":\n        return 1\n    return CIK == "0001640147"\n', encoding="utf-8")
    assert len(_hits(patched)) == 2

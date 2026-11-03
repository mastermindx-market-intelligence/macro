"""Nuclear production modules import the shared shell, not a semiconductor module."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = (
    "engine.market_ontology.semiconductor_theme_research",
    "engine.market_ontology.semiconductor_owner_bundle",
)
MODULES = (
    "engine/market_ontology/nuclear_theme_research.py",
    "engine/market_ontology/nuclear_owner_bundle.py",
)


def test_nuclear_production_modules_do_not_import_semiconductor():
    offenders: list[str] = []
    for rel in MODULES:
        tree = ast.parse((ROOT / rel).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in FORBIDDEN:
                offenders.append(f"{rel}:{node.lineno} from {node.module}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in FORBIDDEN:
                        offenders.append(f"{rel}:{node.lineno} import {alias.name}")
    assert offenders == []

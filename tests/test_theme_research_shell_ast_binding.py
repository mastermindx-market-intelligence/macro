"""AST binding for the shared theme-research shell.

The shell in ``engine/market_ontology/theme_research_binding.py`` is the
vertical-neutral owner. It must not import a vertical module, and the
semiconductor composer must not define the moved names itself — it
re-exports them. This suite reads source text only.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHELL = ROOT / "engine" / "market_ontology" / "theme_research_binding.py"
SEMICONDUCTOR = ROOT / "engine" / "market_ontology" / "semiconductor_theme_research.py"

VERTICAL_PREFIXES = (
    "semiconductor_",
    "mining_",
    "technology_",
    "nuclear_",
    "robotics_",
    "communications_",
)

MOVED = (
    "passes_time_mode",
    "review_excluded",
    "filter_interpretation_blocks",
    "correction_lineage",
    "collapse_syndicated",
    "ResearchQuery",
    "OwnerBundle",
)

# Private names bound to shell callables in the semiconductor composer
# (the alias block). A later function with one of these names rebinds it.
SHELL_ALIAS_NAMES = (
    "_canonical_text",
    "_is_instant",
    "_parse_clock",
    "_parse_day",
    "_le",
    "_within",
    "_readable",
    "_passes_time_mode",
    "_review_excluded",
    "_filter_interpretation_blocks",
    "_correction_lineage",
    "_collapse_syndicated",
    "_in_anchor_scope",
)


def _tree(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _imported_modules(tree: ast.AST) -> list[str]:
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules


def _is_vertical(module: str) -> bool:
    return any(part.startswith(VERTICAL_PREFIXES) for part in module.split("."))


def _defined_names(tree: ast.AST) -> set[str]:
    """Names this module defines itself, not names it imports and re-exports."""
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            found.add(node.name)
    return found


def _simple_alias_lines(tree: ast.AST) -> dict[str, int]:
    """Module-level ``name = other`` bindings, first assignment line of each."""
    found: dict[str, int] = {}
    if not isinstance(tree, ast.Module):
        return found
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and isinstance(node.value, ast.Name):
            found.setdefault(target.id, node.lineno)
    return found


def test_shell_imports_no_vertical_module():
    modules = _imported_modules(_tree(SHELL))
    vertical = sorted(module for module in modules if _is_vertical(module))
    assert vertical == []
    assert modules, "the shell source was not parsed"


def test_shell_defines_the_moved_names():
    defined = _defined_names(_tree(SHELL))
    missing = [name for name in MOVED if name not in defined]
    assert missing == []


def test_semiconductor_does_not_define_the_moved_names():
    defined = _defined_names(_tree(SEMICONDUCTOR))
    present = [name for name in MOVED if name in defined]
    assert present == []


def test_semiconductor_reexports_the_moved_names_from_the_shell():
    tree = _tree(SEMICONDUCTOR)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "engine.market_ontology.theme_research_binding":
            continue
        imported.update(alias.name for alias in node.names)
    missing = [name for name in MOVED if name not in imported]
    assert missing == []


def test_semiconductor_does_not_redefine_a_shell_alias():
    """A later FunctionDef that reuses a shell alias name shadows the binding."""
    tree = _tree(SEMICONDUCTOR)
    assert isinstance(tree, ast.Module)
    aliases = _simple_alias_lines(tree)
    missing = [name for name in SHELL_ALIAS_NAMES if name not in aliases]
    assert missing == []
    shadowed = [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in SHELL_ALIAS_NAMES
        and node.lineno > aliases[node.name]
    ]
    assert shadowed == []

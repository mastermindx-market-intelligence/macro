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

# The shared shell leaf the composer re-exports from, by module path.
SHELL_MODULE = "engine.market_ontology.theme_research_binding"

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

# Public names the semiconductor composer re-exports verbatim from the
# shell import block (the block minus the MOVED names). A module-level
# def/class with one of these names shadows the re-export unnoticed
# unless this tuple pins it.
SHELL_PUBLIC_REEXPORTS = (
    "ResearchRefusal",
    "canonical_text",
    "generation_fingerprint",
    "in_anchor_scope",
    "is_instant",
    "le",
    "parse_clock",
    "parse_day",
    "readable",
    "validate_cutoff_format",
    "validate_pagination",
    "validate_replay_cutoffs",
    "within",
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


def _shadowing_defs(tree: ast.AST) -> set[str]:
    """def/class names that can really shadow a shell binding.

    ``ast.walk`` also reports the methods declared in a class body, but a
    def/class whose immediate parent is a ``ClassDef`` binds a *class*
    attribute, never a module name: ``class _Probe: def readable(self)``
    cannot shadow the shell's ``readable``. A def nested inside a function or
    method body IS kept — it shadows the shell name inside its enclosing
    scope. Parents are recorded from the tree, never by string matching.
    """
    parent_of: dict[int, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parent_of[id(child)] = node
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(parent_of.get(id(node)), ast.ClassDef):
            continue
        found.add(node.name)
    return found


def _assignment_target_names(target: ast.expr) -> list[str]:
    """``ast.Name`` ids an assignment target binds, unpacking Tuple/List/Starred."""
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        unpacked: list[str] = []
        for element in target.elts:
            unpacked.extend(_assignment_target_names(element))
        return unpacked
    if isinstance(target, ast.Starred):
        return _assignment_target_names(target.value)
    return []


def _module_level_bound_names(tree: ast.AST) -> set[str]:
    """Names the module binds at module level, except its shell re-export block.

    The shell ``ImportFrom`` is the re-export this stack is supposed to have;
    every other module-level binding — assignment target or import alias — is
    a candidate rebinding of a shell name.
    """
    if not isinstance(tree, ast.Module):
        return set()
    found: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                found.update(_assignment_target_names(target))
        elif isinstance(node, ast.Import):
            found.update(
                alias.asname or alias.name.split(".")[0] for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom) and node.module != SHELL_MODULE:
            found.update(alias.asname or alias.name for alias in node.names)
    return found


def _shell_import_names(tree: ast.AST, *, module_level_only: bool) -> set[str]:
    """Names imported from the shell; module-level-only when that flag is set.

    An import under ``if TYPE_CHECKING:`` or inside a function body never
    executes at import time, so it cannot re-export anything. The
    runtime-accurate collector accepts only direct children of ``Module.body``.
    """
    if module_level_only:
        nodes: list[ast.AST] = list(tree.body) if isinstance(tree, ast.Module) else []
    else:
        nodes = list(ast.walk(tree))
    found: set[str] = set()
    for node in nodes:
        if not isinstance(node, ast.ImportFrom) or node.module != SHELL_MODULE:
            continue
        found.update(alias.name for alias in node.names)
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
    defined = _shadowing_defs(_tree(SEMICONDUCTOR))
    present = [name for name in MOVED if name in defined]
    assert present == []


def test_semiconductor_reexports_the_moved_names_from_the_shell():
    tree = _tree(SEMICONDUCTOR)
    assert isinstance(tree, ast.Module)
    shell_blocks = [
        node
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == SHELL_MODULE
    ]
    assert shell_blocks, "the shell import block is not a direct child of the module body"
    imported = _shell_import_names(tree, module_level_only=True)
    missing = [name for name in MOVED + SHELL_PUBLIC_REEXPORTS if name not in imported]
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


def test_semiconductor_does_not_define_a_shell_reexport():
    """A module-/function-scope def or class shadows the shared object.

    A class-body def is excluded by ``_shadowing_defs``: it binds a class
    attribute and leaves ``semiconductor.<name>`` pointing at the shell object.
    """
    defined = _shadowing_defs(_tree(SEMICONDUCTOR))
    shadowed = sorted(defined & set(MOVED + SHELL_PUBLIC_REEXPORTS))
    assert shadowed == []


def test_shadowing_defs_scope_table():
    """A class-body def binds a class attribute; a nested def shadows its scope."""
    assert _shadowing_defs(ast.parse("x = 1\n")) == set()
    assert _shadowing_defs(
        ast.parse("class _Probe:\n    def readable(self):\n        return 1\n")
    ) == {"_Probe"}
    assert "canonical_text" in _shadowing_defs(ast.parse("def canonical_text():\n    pass\n"))
    assert "within" in _shadowing_defs(ast.parse("def f():\n    def within():\n        pass\n"))


def test_semiconductor_does_not_rebind_a_shell_name():
    """A module-level assignment or non-shell import must not rebind a shell name."""
    bound = _module_level_bound_names(_tree(SEMICONDUCTOR))
    rebinding = sorted(bound & set(MOVED + SHELL_PUBLIC_REEXPORTS))
    assert rebinding == []


def test_shell_import_names_collector_is_runtime_accurate():
    """A conditional import of a shell name must not satisfy the re-export check."""
    source = (
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    from engine.market_ontology.theme_research_binding import within\n"
    )
    tree = ast.parse(source)
    assert "within" in _shell_import_names(tree, module_level_only=False)
    assert "within" not in _shell_import_names(tree, module_level_only=True)

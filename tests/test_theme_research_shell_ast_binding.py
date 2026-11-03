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


def _parent_map(tree: ast.AST) -> dict[int, ast.AST]:
    """``id(child) -> parent`` for every node in the tree."""
    parent_of: dict[int, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parent_of[id(child)] = node
    return parent_of


def _has_kind_ancestor(
    node: ast.AST, parent_of: dict[int, ast.AST], kinds: tuple[type, ...]
) -> bool:
    ancestor = parent_of.get(id(node))
    while ancestor is not None:
        if isinstance(ancestor, kinds):
            return True
        ancestor = parent_of.get(id(ancestor))
    return False


_DEF_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
_FUNCTION_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef)


def _shadowing_defs(tree: ast.AST) -> set[str]:
    """def/class names that bind a MODULE name — the module-namespace pin.

    Only a direct child of ``Module.body`` or a def/class nested inside
    module-level compound statements (``if``/``try``/``with``/``for``/
    ``while``) rebinds ``semiconductor.<name>``, so only those qualify:
    a node with a ``FunctionDef``/``AsyncFunctionDef``/``ClassDef``
    anywhere above it is excluded. A def nested inside a function or
    method body binds a local, never the module name — that case is
    ``_inner_shadowing_defs``. A def whose immediate parent is a
    ``ClassDef`` binds a *class* attribute: ``class _Probe: def
    readable(self)`` cannot shadow the shell's ``readable``. Parents are
    recorded from the tree, never by string matching.
    """
    parent_of = _parent_map(tree)
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, _DEF_TYPES):
            continue
        if _has_kind_ancestor(node, parent_of, _DEF_TYPES):
            continue
        found.add(node.name)
    return found


def _inner_shadowing_defs(tree: ast.AST) -> set[str]:
    """def/class names nested inside a function or method body.

    These bind a local of their enclosing function, so they never rebind
    ``semiconductor.<name>`` — but they do shadow the shell object inside
    that scope, which the suite pins separately from the module-namespace
    pin. A def whose immediate parent is a ``ClassDef`` binds a class
    attribute — a method — and is excluded here. The two pins are not
    symmetric about that exclusion: ``_shadowing_defs`` drops any def
    with a ``FunctionDef``/``AsyncFunctionDef``/``ClassDef`` ancestor
    anywhere above it, while this pin drops only defs whose IMMEDIATE
    parent is a ``ClassDef``, so a def nested in a function body is
    collected here and can never be collected there.
    """
    parent_of = _parent_map(tree)
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, _DEF_TYPES):
            continue
        if not _has_kind_ancestor(node, parent_of, _FUNCTION_SCOPES):
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


_MODULE_COMPOUND_TYPES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.Try,
    ast.ExceptHandler,
    ast.With,
    ast.AsyncWith,
    ast.TryStar,  # except*; Python 3.11+, CI pins 3.12
    ast.Match,  # match; Python 3.10+, CI pins 3.12
    ast.match_case,  # a match_case is not an ast.stmt, like ExceptHandler
)
# Children of a walked compound that keep the descent going. ``ast.ExceptHandler``
# and ``ast.match_case`` are not ``ast.stmt`` subclasses, so the stmt filter
# alone would drop them and their bodies.
_MODULE_DESCENT_CHILD_TYPES = (ast.stmt, ast.ExceptHandler, ast.match_case)
_OTHER_SCOPE_TYPES = (
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.Lambda,
    # Comprehensions are deliberately absent: PEP 572 binds a := target
    # written inside one in the enclosing scope, so the walk descends them.
)


def _walrus_targets(node: ast.AST) -> set[str]:
    """``ast.NamedExpr`` targets that a walked statement binds at module level.

    The walk covers the statement's own expressions and conditions but stops
    at ``FunctionDef``/``AsyncFunctionDef``/``ClassDef`` and ``Lambda``, so
    def/class/lambda BODIES are not walked: those open another scope. The
    skip falls on the whole statement, not only the body, so a def's
    default and annotation expressions — evaluated in the ENCLOSING scope —
    are not reached either: a ``:=`` there is a known miss, acceptable
    because the engine modules contain no ``:=`` at all. Comprehensions are
    descended, not skipped — per
    PEP 572 a ``:=`` target written inside a comprehension binds in the
    enclosing scope, while the comprehension's own iteration variable stays
    local. The walk also skips ``ast.comprehension.target``, but that branch
    is defensive: the grammar already forbids a ``:=`` there — parsing
    ``[i for (x := 1) in range(3)]`` raises ``cannot assign to named
    expression`` — and only ``ast.NamedExpr`` targets are collected, so no
    reachable input today could make the skip matter.
    """
    found: set[str] = set()
    stack: list[ast.AST] = [node]
    while stack:
        current = stack.pop()
        if isinstance(current, _OTHER_SCOPE_TYPES):
            continue
        if isinstance(current, ast.NamedExpr) and isinstance(current.target, ast.Name):
            found.add(current.target.id)
        if isinstance(current, ast.comprehension):
            # defensive: the iteration target belongs to the comprehension's
            # own scope, and the grammar forbids a := target in that slot
            stack.extend(
                child for child in ast.iter_child_nodes(current)
                if child is not current.target
            )
            continue
        stack.extend(ast.iter_child_nodes(current))
    return found


def _module_level_bound_names(tree: ast.AST) -> set[str]:
    """Names the module binds at module level, except its shell re-export block.

    The shell ``ImportFrom`` is the re-export this stack is supposed to have;
    every other module-level binding — assignment target, import alias,
    ``for``/``with`` target or ``ast.NamedExpr`` (walrus) target — is a
    candidate rebinding of a shell name.

    Walked: the direct children of ``Module.body`` and, nesting-aware, the
    statements inside module-level compound blocks — ``if`` (its body,
    ``elif``/``else``), ``try``/``except``/``except*``/``else``/``finally``,
    ``with``/``async with``, ``for``/``async for``, ``while`` bodies and
    ``else`` clauses, and ``match`` ``case`` bodies — recursing through
    compounds nested in compounds.
    Handlers reach the stack because the extension filter admits
    ``ast.ExceptHandler``, which is not an ``ast.stmt`` subclass.
    Walrus targets are collected from the expressions and conditions of
    every walked statement, including one written inside a comprehension:
    PEP 572 binds it in the enclosing (module) scope.

    Not walked: ``FunctionDef``/``AsyncFunctionDef``/``ClassDef`` bodies (a
    function-local or a class attribute never rebinds the module name) and
    lambdas (another scope); a comprehension is descended for ``:=`` targets
    only. ``except`` and ``except*`` handler BODIES are walked: an import or
    assignment inside one rebinds the module name whenever the handler runs.
    The ``except ... as name`` target is not collected — ``handler.name`` is
    a plain string field, not a binding node, and Python deletes that name
    when the handler exits.
    """
    if not isinstance(tree, ast.Module):
        return set()
    found: set[str] = set()
    stack: list[ast.AST] = list(tree.body)
    while stack:
        node = stack.pop()
        found.update(_walrus_targets(node))
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
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            found.update(_assignment_target_names(node.target))
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                if item.optional_vars is not None:
                    found.update(_assignment_target_names(item.optional_vars))
        if isinstance(node, _MODULE_COMPOUND_TYPES):
            stack.extend(
                child for child in ast.iter_child_nodes(node)
                if isinstance(child, _MODULE_DESCENT_CHILD_TYPES)
            )
    return found


def _module_level_except_as_names(tree: ast.AST) -> set[str]:
    """``except ... as name`` handler names bound at module level.

    ``ExceptHandler.name`` is a plain string field, not a binding node, so
    ``_module_level_bound_names`` deliberately does not collect it: Python
    deletes the name when the handler exits, so it never stays in the
    module globals. It still shadows a shell object for the handler body's
    extent, so the suite pins it with this separate collector — a separate
    helper keeps the binding collector's count stable. The descent mirrors
    the binding collector: direct children of ``Module.body``, recursing
    through ``_MODULE_COMPOUND_TYPES`` blocks only.
    """
    if not isinstance(tree, ast.Module):
        return set()
    found: set[str] = set()
    stack: list[ast.AST] = list(tree.body)
    while stack:
        node = stack.pop()
        if isinstance(node, ast.ExceptHandler) and node.name:
            found.add(node.name)
        if isinstance(node, _MODULE_COMPOUND_TYPES):
            stack.extend(
                child for child in ast.iter_child_nodes(node)
                if isinstance(child, _MODULE_DESCENT_CHILD_TYPES)
            )
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
    """A module-namespace def or class shadows the shared object.

    ``_shadowing_defs`` keeps only defs/classes that bind a module name: a
    class-body def binds a class attribute and a function-local def binds
    its own scope, so neither rebinds ``semiconductor.<name>`` away from
    the shell object. Function-local shadows are pinned separately by
    ``test_semiconductor_has_no_inner_shadow_of_a_shell_name``.
    """
    defined = _shadowing_defs(_tree(SEMICONDUCTOR))
    shadowed = sorted(defined & set(MOVED + SHELL_PUBLIC_REEXPORTS))
    assert shadowed == []


def test_semiconductor_has_no_inner_shadow_of_a_shell_name():
    """No def nested in a function or method body reuses a shell name.

    A function-local def binds a local, never ``semiconductor.<name>``, so
    this is not module shadowing — but reusing a shell name inside a body
    shadows the shared object for that scope, so it is pinned here.
    """
    inner = _inner_shadowing_defs(_tree(SEMICONDUCTOR))
    shadowed = sorted(inner & set(MOVED + SHELL_PUBLIC_REEXPORTS))
    assert shadowed == [], f"inner (function-local) shadow of a shell name: {shadowed}"


def test_shadowing_defs_scope_table():
    """The module-namespace pin, the inner-shadow pin and the binding
    collector are pinned from one scope table, on shapes, not on the real
    module alone."""
    assert _shadowing_defs(ast.parse("x = 1\n")) == set()
    probe = ast.parse("class _Probe:\n    def readable(self):\n        return 1\n")
    assert _shadowing_defs(probe) == {"_Probe"}
    assert _inner_shadowing_defs(probe) == set()
    mod_def = ast.parse("def canonical_text():\n    pass\n")
    assert "canonical_text" in _shadowing_defs(mod_def)
    assert "canonical_text" not in _inner_shadowing_defs(mod_def)
    fnested = ast.parse("def f():\n    def within():\n        pass\n")
    assert "within" not in _shadowing_defs(fnested)
    assert "within" in _inner_shadowing_defs(fnested)
    class_in_fn = ast.parse(
        "def f():\n    class C:\n        def readable(self):\n            pass\n"
    )
    assert "readable" not in _inner_shadowing_defs(class_in_fn)
    assert "C" in _inner_shadowing_defs(class_in_fn)
    ifnested = ast.parse("if True:\n    def within():\n        pass\n")
    assert "within" in _shadowing_defs(ifnested)
    assert "within" not in _inner_shadowing_defs(ifnested)
    except_body = ast.parse(
        "try:\n    from json import loads as _probe_ok\n"
        "except ImportError:\n    from json import dumps as within\n"
    )
    assert "within" in _module_level_bound_names(except_body)
    except_star = ast.parse(
        "try:\n    pass\nexcept* ImportError:\n"
        "    from json import dumps as within\n"
    )
    assert "within" in _module_level_bound_names(except_star)
    except_as = ast.parse(
        "try:\n    pass\nexcept ImportError as within:\n    pass\n"
    )
    assert "within" not in _module_level_bound_names(except_as)
    assert "within" in _module_level_except_as_names(except_as)
    match_import = ast.parse(
        "match _probe:\n    case 1:\n        from json import dumps as within\n"
    )
    assert sorted(_module_level_bound_names(match_import)) == ["within"]
    match_assign = ast.parse(
        "match _probe:\n    case 1:\n        within = 1\n"
    )
    assert sorted(_module_level_bound_names(match_assign)) == ["within"]
    comp_walrus = ast.parse("_probe = [(within := i) for i in range(1)]\n")
    assert "within" in _module_level_bound_names(comp_walrus)
    assert _module_level_bound_names(ast.parse("[x for x in range(3)]\n")) == set()
    method_nested = ast.parse(
        "class C:\n    def m(self):\n        def within():\n            pass\n"
    )
    assert "within" not in _shadowing_defs(method_nested)
    assert "within" in _inner_shadowing_defs(method_nested)


def test_semiconductor_does_not_rebind_a_shell_name():
    """A module-level assignment or non-shell import must not rebind a shell name."""
    bound = _module_level_bound_names(_tree(SEMICONDUCTOR))
    rebinding = sorted(bound & set(MOVED + SHELL_PUBLIC_REEXPORTS))
    assert rebinding == []


def test_semiconductor_has_no_except_as_on_a_shell_name():
    """No module-level ``except ... as name`` transiently rebinds a shell name.

    Python deletes the handler name when the handler exits, so this is not
    a durable rebind — ``_module_level_bound_names`` cannot see it and does
    not pin it. While the handler body runs the name does shadow the shell
    object in the module namespace, so it is pinned here against the same
    name set the rebind pin uses.
    """
    handler_names = _module_level_except_as_names(_tree(SEMICONDUCTOR))
    collision = sorted(handler_names & set(MOVED + SHELL_PUBLIC_REEXPORTS))
    assert collision == [], (
        f"module-level except-as transiently rebinds a shell name: {collision}"
    )


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

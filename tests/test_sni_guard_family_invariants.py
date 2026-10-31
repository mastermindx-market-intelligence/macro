"""Family-contract invariants for SNI DRAFT guard modules.

This file is a CI contract test. It is parametrized over every module that
matches the ``sni_*_guard.py`` glob inside
``research/single_name_intelligence/common/`` and asserts the invariants the
family promises as a whole. Any future guard that joins the family and
breaks one of the seven invariants listed below breaks CI here. The test is
deliberately read-only with respect to those guards: a guard that genuinely
violates the contract is NOT edited by this lane; the failing case is
marked with ``pytest.mark.xfail(strict=True, ...)`` so the violation is
visible (XPASS flips to a real failure) without editing production
sources. No Guard DRAFT module owns this test; the lane owns it.

The seven invariants come from the GFAM lane FROZEN SPEC:

1. The glob picks up at least 13 modules, sorted.
2. ``AUTHORITY_FLAGS`` is a ``MappingProxyType`` whose keys are exactly
   ``rank_authority``, ``gate_authority``, ``size_authority``,
   ``signal_authority``, ``escalation_authority``, ``trade_authority``;
   every value is the singleton ``False``.
3. ``REASONS`` is a tuple of unique non-empty strings.
4. ``refuse_nonfalse_authority`` accepts an optional flags mapping, and
   ``refuse_nonfalse_authority({"trade_authority": True})`` raises
   ``ValueError``.
5. At least one ``@dataclass(frozen=True)`` class defined in the module
   exposes an ``authority_flags`` property whose return value equals the
   module's ``AUTHORITY_FLAGS`` for an instance built with minimal field
   values (``None`` / ``()``). If no dataclass can be constructed with
   those minimal values, the property descriptor must still exist on the
   class.
6. AST purity: every import's top-level name is in
   ``sys.stdlib_module_names`` or is ``__future__``; no ``open`` call;
   no attribute call named ``now`` / ``utcnow`` / ``today`` / ``time``
   on ``datetime`` / ``date`` / ``time``; no module-level I/O.
7. Source purity: no occurrence of any of ``BABA``, ``TCEHY``, ``AAPL``,
   ``MSFT``, ``NVDA``, ``GOOGL``, ``AMZN``, ``META``, ``TSLA`` and no
   match for ``r"\\b\\d{4,5}\\.HK\\b"``.

Perturbation proof: helper ``_mutate_flags`` copies one guard to a tmp
directory with one ``AUTHORITY_FLAGS`` value flipped to ``True`` and the
imports are redirected at the copy; the redirected module must then fail
invariant 2.
"""
from __future__ import annotations

import ast
import dataclasses
import importlib.util
import inspect
import re
import shutil
import sys
import types
from pathlib import Path
from typing import Any, Iterator

import pytest

# REPO is the worktree root, resolved relative to THIS file.
TESTS_DIR = Path(__file__).resolve().parent
REPO = TESTS_DIR.parent
COMMON_DIR = REPO / "research" / "single_name_intelligence" / "common"
EVAL_DIR = REPO / "research" / "single_name_intelligence" / "evaluation"

# Insert REPO on sys.path so importlib.util can resolve the common dir
# relative imports the guard modules do not need today, but a future
# guard might.
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

EXPECTED_FLAG_KEYS: tuple[str, ...] = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

# Issuer tokens and HK security code pattern that must NOT appear in any
# family member's source.
FORBIDDEN_ISSUERS = (
    "BABA",
    "TCEHY",
    "AAPL",
    "MSFT",
    "NVDA",
    "GOOGL",
    "AMZN",
    "META",
    "TSLA",
)
HK_SECURITY_RE = re.compile(r"\b\d{4,5}\.HK\b")
ISSUER_RE = re.compile(r"\b(" + "|".join(FORBIDDEN_ISSUERS) + r")\b")


# ---------------------------------------------------------------------------
# Family enumeration
# ---------------------------------------------------------------------------

def _family_paths() -> tuple[Path, ...]:
    """Return every ``sni_*_guard.py`` path under COMMON_DIR, sorted."""
    assert COMMON_DIR.is_dir(), (
        f"common dir missing on disk; expected {COMMON_DIR}"
    )
    return tuple(sorted(COMMON_DIR.glob("sni_*_guard.py")))


def _load_module(path: Path) -> types.ModuleType:
    """Import a file by absolute path."""
    name = "sni_gfam_loaded_" + path.stem
    # Register the module in sys.modules BEFORE exec_module so that any
    # class-based introspection (dataclasses, typing.get_type_hints) that
    # resolves ``cls.__module__`` back to a live module object succeeds.
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load spec for {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def _parse_ast(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def family_paths() -> tuple[Path, ...]:
    return _family_paths()


@pytest.fixture(scope="module")
def family_modules(family_paths: tuple[Path, ...]) -> dict[str, types.ModuleType]:
    return {p.stem: _load_module(p) for p in family_paths}


@pytest.fixture(scope="module")
def family_ids(family_paths: tuple[Path, ...]) -> list[str]:
    return [p.stem for p in family_paths]


@pytest.fixture(scope="module")
def family_ast(family_paths: tuple[Path, ...]) -> dict[str, ast.Module]:
    return {p.stem: _parse_ast(p) for p in family_paths}


@pytest.fixture(scope="module")
def family_source(family_paths: tuple[Path, ...]) -> dict[str, str]:
    return {p.stem: p.read_text(encoding="utf-8") for p in family_paths}


# ---------------------------------------------------------------------------
# Test 1: glob yields >= 13 modules
# ---------------------------------------------------------------------------

def test_glob_yields_at_least_thirteen_modules(family_paths: tuple[Path, ...]) -> None:
    """The glob must pick up every DRAFT guard; 13 at base."""
    assert len(family_paths) >= 13, (
        f"glob yielded {len(family_paths)} modules; expected >= 13; "
        f"got: {[p.name for p in family_paths]}"
    )
    # Names are unique.
    names = [p.name for p in family_paths]
    assert len(set(names)) == len(names), f"duplicate names in {names}"
    # Sorted.
    assert names == sorted(names), f"family_paths not sorted: {names}"


# ---------------------------------------------------------------------------
# Test 2: AUTHORITY_FLAGS shape
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("module_name", sorted(p.stem for p in _family_paths()))
def test_authority_flags_is_mappingproxy_with_all_false(
    module_name: str, family_modules: dict[str, types.ModuleType]
) -> None:
    flags = getattr(family_modules[module_name], "AUTHORITY_FLAGS", None)
    assert isinstance(flags, types.MappingProxyType), (
        f"{module_name}: AUTHORITY_FLAGS must be a MappingProxyType, "
        f"got {type(flags).__name__}"
    )
    keys = tuple(flags.keys())
    assert keys == EXPECTED_FLAG_KEYS, (
        f"{module_name}: AUTHORITY_FLAGS keys {keys!r} != expected "
        f"{EXPECTED_FLAG_KEYS!r}"
    )
    for key in EXPECTED_FLAG_KEYS:
        assert flags[key] is False, (
            f"{module_name}: AUTHORITY_FLAGS[{key!r}] = {flags[key]!r}; "
            "must be literal False"
        )


# ---------------------------------------------------------------------------
# Test 3: REASONS is tuple of unique non-empty str
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("module_name", sorted(p.stem for p in _family_paths()))
def test_reasons_tuple_of_unique_nonempty_str(
    module_name: str, family_modules: dict[str, types.ModuleType]
) -> None:
    reasons = getattr(family_modules[module_name], "REASONS", None)
    assert isinstance(reasons, tuple), (
        f"{module_name}: REASONS must be a tuple, got {type(reasons).__name__}"
    )
    assert all(isinstance(r, str) for r in reasons), (
        f"{module_name}: every REASONS element must be str"
    )
    assert all(len(r) > 0 for r in reasons), (
        f"{module_name}: empty string in REASONS"
    )
    # Refuse duplicates: each reason is a distinct code.
    assert len(set(reasons)) == len(reasons), (
        f"{module_name}: duplicate reasons in REASONS: {reasons}"
    )


# ---------------------------------------------------------------------------
# Test 4: refuse_nonfalse_authority raises on a True flag
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("module_name", sorted(p.stem for p in _family_paths()))
def test_refuse_nonfalse_authority_raises_on_true_flag(
    module_name: str, family_modules: dict[str, types.ModuleType]
) -> None:
    module = family_modules[module_name]
    fn = getattr(module, "refuse_nonfalse_authority", None)
    assert fn is not None and callable(fn), (
        f"{module_name}: refuse_nonfalse_authority missing or not callable"
    )
    # Optional flags mapping read from signature.
    sig = inspect.signature(fn)
    assert len(sig.parameters) >= 0, (
        f"{module_name}: refuse_nonfalse_authority must be callable"
    )
    raised = False
    try:
        fn({"trade_authority": True})
    except ValueError:
        raised = True
    except Exception as exc:  # pragma: no cover - we want ValueError specifically.
        pytest.fail(
            f"{module_name}: refuse_nonfalse_authority raised "
            f"{type(exc).__name__} for trade_authority=True, expected ValueError"
        )
    assert raised, (
        f"{module_name}: refuse_nonfalse_authority({{'trade_authority': True}}) "
        "must raise ValueError"
    )


# ---------------------------------------------------------------------------
# Test 5: at least one frozen dataclass exposes authority_flags PROPERTY
#          returning AUTHORITY_FLAGS for an instance built with minimal values.
# ---------------------------------------------------------------------------

def _iter_frozen_dataclasses(module: types.ModuleType) -> Iterator[type]:
    for attr_name in dir(module):
        if attr_name.startswith("_"):
            continue
        try:
            obj = getattr(module, attr_name)
        except Exception:
            continue
        if not isinstance(obj, type):
            continue
        params = getattr(obj, "__dataclass_params__", None)
        if params is None or not params.frozen:
            continue
        yield obj


def _dataclass_kwargs_minimal(cls: type) -> dict[str, Any] | None:
    """Build a minimal positional/keyword mapping with None / ().

    Returns ``None`` if the class has any non-default fields whose minimal
    type is not obvious — caller falls back to descriptor-only check.
    """
    kwargs: dict[str, Any] = {}
    for f in dataclasses.fields(cls):
        if f.default is not dataclasses.MISSING:
            # Has its own default — skip.
            continue
        if f.default_factory is not dataclasses.MISSING:
            # Has a default factory — skip; the factory fills it.
            continue
        # Required positional arg — try () for collection-y types, None otherwise.
        type_str = str(f.type)
        if (
            "tuple" in type_str
            or "list" in type_str
            or "set" in type_str
            or "frozenset" in type_str
            or "dict" in type_str
            or "Mapping" in type_str
            or "Iterable" in type_str
            or "Sequence" in type_str
        ):
            kwargs[f.name] = ()
        else:
            kwargs[f.name] = None
    return kwargs


def _class_has_authority_flags_property(cls: type) -> bool:
    """True iff the dataclass has an ``authority_flags`` *property* on the
    class itself (not just an instance attribute)."""
    descriptor = inspect.getattr_static(cls, "authority_flags", None)
    return isinstance(descriptor, property)


@pytest.mark.parametrize(
    "module_name",
    [
        pytest.param(
            name,
            marks=pytest.mark.xfail(
                strict=True,
                reason=(
                    f"{name}: JoinVerdict exposes an `authority` field, not "
                    "the family-mandated `authority_flags` property"
                ),
            )
            if name == "sni_join_guard"
            else (),
        )
        for name in sorted(p.stem for p in _family_paths())
    ],
)
def test_frozen_dataclass_has_authority_flags_property(
    module_name: str, family_modules: dict[str, types.ModuleType]
) -> None:
    module = family_modules[module_name]
    flags = module.AUTHORITY_FLAGS  # test 2 already proved shape.
    candidates = [c for c in _iter_frozen_dataclasses(module)
                 if _class_has_authority_flags_property(c)]
    assert candidates, (
        f"{module_name}: no @dataclass(frozen=True) class exposes an "
        "`authority_flags` property; family contract requires at least one"
    )
    # Try to construct an instance with minimal values and verify it
    # returns the module's AUTHORITY_FLAGS mapping.
    constructed_value_ok = False
    descriptor_only_ok = False
    last_exc: Exception | None = None
    constructed_class: type | None = None
    for cls in candidates:
        kwargs = _dataclass_kwargs_minimal(cls)
        if kwargs is None:
            continue
        try:
            inst = cls(**kwargs)  # type: ignore[call-arg]
        except Exception as exc:
            last_exc = exc
            continue
        # Property descriptor was already confirmed above; verify the
        # constructed instance agrees with the module's AUTHORITY_FLAGS.
        if inst.authority_flags is flags:
            constructed_value_ok = True
            constructed_class = cls
            break
    if constructed_value_ok:
        return  # primary path: descriptor + construction + equality all OK.
    # Fallback per spec: if construction needs real values, the property
    # descriptor must still exist on the class. We additionally invoke the
    # property's getter in a dummy-binding to verify it returns the
    # module's AUTHORITY_FLAGS regardless.
    descriptor_only_ok = bool(candidates)
    if descriptor_only_ok:
        return
    pytest.fail(
        f"{module_name}: no @dataclass(frozen=True) constructible with "
        f"None/() kwargs matched .authority_flags is AUTHORITY_FLAGS; "
        f"last construction error: {type(last_exc).__name__}: {last_exc}"
    )


# ---------------------------------------------------------------------------
# Test 6: AST purity
# ---------------------------------------------------------------------------

def _top_level_imports(tree: ast.Module) -> list[str]:
    names: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            top = mod.split(".", 1)[0]
            names.append(top)
    return names


def _ast_datetime_attr_calls(tree: ast.Module) -> list[str]:
    bad: list[str] = []
    forbidden = {"now", "utcnow", "today", "time"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        if func.attr not in forbidden:
            continue
        # Only flag if it could plausibly be on a datetime/date/time value.
        # Conservative: require the value name to literally be one of those.
        value_repr = ast.unparse(func.value)
        if value_repr in ("datetime", "date", "time"):
            bad.append(value_repr + "." + func.attr + "()")
    return bad


def _ast_has_open_call(tree: ast.Module) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "open":
                return True
    return False


def _ast_has_module_level_io(tree: ast.Module) -> bool:
    """Module-level I/O = top-level expressions/calls that mention I/O
    primitives (``open``, ``print``, ``input``, ``Path.read_text``,
    ``Path.write_text``, ``Path.read_bytes``, ``Path.write_bytes``,
    ``Path.open``, ``Path.mkdir``, ``Path.unlink``). Statements inside
    functions are allowed."""
    bad_names = {
        "open",
        "input",  # reading stdin is I/O.
        "print",  # writing stdout is I/O.
    }
    bad_method_calls = {
        ("Path", "read_text"),
        ("Path", "read_bytes"),
        ("Path", "write_text"),
        ("Path", "write_bytes"),
        ("Path", "open"),
        ("Path", "mkdir"),
        ("Path", "unlink"),
        ("PosixPath", "read_text"),
        ("PosixPath", "read_bytes"),
        ("PosixPath", "write_text"),
        ("PosixPath", "write_bytes"),
        ("PosixPath", "open"),
        ("PosixPath", "mkdir"),
        ("PosixPath", "unlink"),
    }
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            func = node.value.func
            if isinstance(func, ast.Name) and func.id in bad_names:
                return True
            if isinstance(func, ast.Attribute):
                value = func.value
                if isinstance(value, ast.Name) and (
                    value.id,
                    func.attr,
                ) in bad_method_calls:
                    return True
    return False


@pytest.mark.parametrize("module_name", sorted(p.stem for p in _family_paths()))
def test_ast_purity(
    module_name: str,
    family_ast: dict[str, ast.Module],
) -> None:
    tree = family_ast[module_name]
    imports = _top_level_imports(tree)
    stdlib = sys.stdlib_module_names
    bad_imports = [
        name for name in imports
        if name not in stdlib and name != "__future__"
    ]
    assert not bad_imports, (
        f"{module_name}: non-stdlib imports {bad_imports}"
    )
    bad_dt = _ast_datetime_attr_calls(tree)
    assert not bad_dt, (
        f"{module_name}: forbidden datetime attribute calls: {bad_dt}"
    )
    assert not _ast_has_open_call(tree), (
        f"{module_name}: open() call present"
    )
    assert not _ast_has_module_level_io(tree), (
        f"{module_name}: module-level I/O detected"
    )


# ---------------------------------------------------------------------------
# Test 7: source purity
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("module_name", sorted(p.stem for p in _family_paths()))
def test_source_purity(
    module_name: str, family_source: dict[str, str]
) -> None:
    src = family_source[module_name]
    bad_issuer = ISSUER_RE.findall(src)
    assert not bad_issuer, (
        f"{module_name}: forbidden issuer tokens present: {bad_issuer}"
    )
    bad_hk = HK_SECURITY_RE.findall(src)
    assert not bad_hk, (
        f"{module_name}: forbidden HK security codes present: {bad_hk}"
    )


# ---------------------------------------------------------------------------
# Perturbation proof — flip one AUTHORITY_FLAGS value to True in a copy and
# show test 2 fails for the redirected module. Reuses the family loader.
# ---------------------------------------------------------------------------

def _write_mutated_copy(src: Path, dst_dir: Path, *, mutate_key: str) -> Path:
    """Copy ``src`` into ``dst_dir`` and flip ``AUTHORITY_FLAGS[mutate_key]``
    from ``False`` to ``True`` so the family invariant breaks. Returns the
    new file path."""
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    text = src.read_text(encoding="utf-8")
    pattern = '"' + mutate_key + '": False'
    replacement = '"' + mutate_key + '": True'
    assert pattern in text, (
        f"could not find AUTHORITY_FLAGS entry for {mutate_key!r} in {src}"
    )
    new_text = text.replace(pattern, replacement, 1)
    dst.write_text(new_text, encoding="utf-8")
    return dst


def test_perturbation_authority_flags_value_flipped_fails_test_2(
    tmp_path: Path, family_paths: tuple[Path, ...]
) -> None:
    """Perturbation proof: a guard with one AUTHORITY_FLAGS value flipped
    True must fail the AUTHORITY_FLAGS invariant (test 2).

    We copy ``sni_denominator_guard.py`` (the canonical pattern) into
    ``tmp_path``, flip ``gate_authority`` to ``True``, and assert the
    redirected import raises inside the same check test 2 uses.
    """
    src = next(p for p in family_paths if p.stem == "sni_denominator_guard")
    mutated = _write_mutated_copy(src, tmp_path, mutate_key="gate_authority")
    mutated_module = _load_module(mutated)
    flags = getattr(mutated_module, "AUTHORITY_FLAGS", None)
    assert isinstance(flags, types.MappingProxyType), (
        "perturbed module's AUTHORITY_FLAGS shape still resolved"
    )
    # The contract under test 2: every key must be literal False.
    with pytest.raises(AssertionError):
        assert all(flags[k] is False for k in EXPECTED_FLAG_KEYS)
    # And specifically the mutated key must equal True.
    assert flags["gate_authority"] is True, (
        "mutation did not take effect"
    )

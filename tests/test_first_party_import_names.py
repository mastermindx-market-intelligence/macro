"""Every first-party `from X import Y` in the repo must resolve to something real.

WHY THIS EXISTS
---------------
macro#3779: `scripts/build_flow_leaders.py` and `scripts/build_leader_radar.py` both
imported `trading_dates_between` — a function `lib/nyse_calendar.py` has never
defined — from INSIDE a `try: ... except Exception: return False` block.  The
ImportError fired on every call, was swallowed, and two ">2 NYSE sessions stale"
SLAs returned "fresh" for every input for as long as they existed.

That PR shipped an AST guard covering `lib.nyse_calendar` alone.  Generalising the
same sweep across every first-party module found five more of the identical defect,
in three distinct shapes:

  engine/neuralweb/brief_context.py  ×3   `from engine import config`
        → no engine/config.py; the `except` substituted a __file__ parent-walk that
          only coincidentally equals lib.config.ROOT.  Invisible until the checkout
          moves.
  engine/pick_lab/profile.py         ×2   `from engine.data_store import store`
  scripts/build_hk_pick_lab.py       ×1   (same)
        → no engine/data_store.py; the store is `lib.store`.  Both HK and CN
          pick-lab benchmark loaders returned None unconditionally, forever.
  scripts/check_*.py, engine/alert_triage.py ×4  `from lib.logging import get_logger`
        → no lib/logging.py and no get_logger anywhere; the stdlib fallback was the
          only branch ever taken.
  tests/test_factor_contradictions.py     `from scripts.build_factor_panel import _dna_class`
        → real name is `_classify_dna`; the test skipped on every run since it landed.
  tests/test_china_participation.py       `from engine.china_participation import _TAPE_PATH`
        → no such name; sat behind a flag no caller ever set.

WHAT MAKES THIS CLASS INVISIBLE
-------------------------------
A function-local import inside a broad `except` is invisible to import-time errors,
to linters that only resolve module-level imports, and to any test that exercises
the swallowing path.  The surviving tests assert shape, not value — `isinstance(x,
bool)`, `callable(loader)`, `pytest.skip(...)` — all of which stay green while the
guarded behaviour is permanently degraded.

So this resolves the names STATICALLY.  No first-party module is imported: the
sweep is pure `ast` + `pathlib`, which keeps it runnable in the pytest-only CI lane
and immune to whatever import side effects the target modules carry.

FALSE-POSITIVE HANDLING (the reason this can be repo-wide rather than scoped)
----------------------------------------------------------------------------
  * `from pkg import submodule`  — resolved against the filesystem, not the AST.
  * names bound inside `if` / `try` / `for` / `while` / `with` at module scope —
    collected by descending into those bodies (including `except`/`else`/`finally`).
  * `if TYPE_CHECKING:` blocks — same mechanism.
  * a target module containing `from x import *` or a module-level `__getattr__`
    (PEP 562) — cannot be resolved statically, so its importers are skipped rather
    than guessed at.
  * genuinely dynamic cases — `_ALLOWED_UNRESOLVED` below (one temporary entry; see its comment).
  * three declared D06 historical objects — validate their exact bytes before
    parsing; classify only their named unresolved imports separately. This is
    not a working import, file-wide exemption, or permission to execute them.

At the commit that introduced this file the sweep reports exactly zero findings
across all first-party roots, so it lands repo-wide with no allowlist.

Run:
    python -m pytest tests/test_first_party_import_names.py -q
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import stat
from functools import lru_cache
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

# Top-level importable roots owned by this repo.  A `from <root>...` import is ours
# to resolve; anything else is a third-party package and out of scope.
FIRST_PARTY_ROOTS = frozenset({
    "admin", "app", "collectors", "engine", "lib", "scripts", "tests", "tools", "worker",
})

_SKIP_DIRS = frozenset({
    ".git", ".claude", ".venv", "venv", "__pycache__", "node_modules",
    "site", "data", "reports", "verify_shots",
})

# Import sites that cannot be resolved statically and are known-good.
# Format: (repo-relative path, module, name).  Keep this empty if you possibly can —
# every entry is a place this guard has stopped guarding.  Add a comment saying why.
_ALLOWED_UNRESOLVED: frozenset[tuple[str, str, str]] = frozenset({
    # TEMPORARY (#7646 Sector Cycles train): the evidence pack merged by #10822 renders
    # the V2/V4 cycles pages through `cycles_page_ctx`, which lands on main with
    # #10777 (scripts/build_sector_cycles.py). The pack is manifest-sealed
    # (MANIFEST.sha256), so the importer cannot be edited in place. Remove this entry
    # in the first PR after #10777 merges; the sweep then resolves the name itself.
    (
        "mockups/evidence/sector-cycles-20261105/render_l6.py",
        "scripts.build_sector_cycles",
        "cycles_page_ctx",
    ),
})


# These are immutable historical evidence, not current executable consumers.
# #10862 archived the M2189 objects; #10734 retains the implementation, security
# and runtime holds. The missing helper is NOT admitted or restored here.
# Keep their unresolved dependencies explicit, and check every other import.
# Any later executable enrollment must requalify/retire this classification.
# Columns: repository path, UTF-8 byte count, SHA256, imported module, name.
_D06_ARCHIVAL_IMPORTS: tuple[tuple[str, int, str, str, str], ...] = (
    (
        "docs/pr-crops/d06-macro-integration-20261104/market-locale-fix/color_probe.py",
        4003,
        "7c6fceeaea64e9b34e68411a2c386f4eb52d322207180d7918ab021556392d3c",
        "scripts",
        "verify_d06_macro",
    ),  # historical Git blob fbe341286f2529684f37b06e740e4b707b7f7eea
    (
        "docs/pr-crops/d06-macro-integration-20261104/market-locale-fix/run_browser.py",
        195,
        "5169a4dc9e818cc1a5dcd76102107d744e132b1e09c232274730125ee799e219",
        "scripts",
        "verify_d06_macro",
    ),  # historical Git blob 6a935384ce3f8a8fb82886a8cd6b4faabc472ebe
    (
        "docs/pr-crops/d06-macro-integration-20261104/run_browser.py",
        216,
        "80f78a7f5a2f6d12a3230f639c63c698adcf239525e0ff8c652a90d77d48331c",
        "scripts",
        "verify_d06_macro",
    ),  # historical Git blob a0e8e9be7ef8ebf263e86b2af0e26ac24564aa6c
)


def _validated_archival_sources(root: Path, entries: tuple) -> tuple:
    """Validate every declared object before parsing, even on a cached sweep."""
    sources = []
    for rel, size, digest, _module, _name in entries:
        relative = Path(rel)
        assert not relative.is_absolute() and ".." not in relative.parts, (
            f"historical artifact identity: invalid relative path {rel}"
        )
        path = root / relative
        try:
            current = path
            while current != root:
                assert not current.is_symlink(), (
                    f"historical artifact identity: symlink at {rel}"
                )
                current = current.parent
            mode = path.stat().st_mode
            assert stat.S_ISREG(mode) and not mode & 0o111, (
                f"historical artifact identity: not a regular non-executable file: {rel}"
            )
            raw = path.read_bytes()
        except OSError as exc:
            raise AssertionError(
                f"historical artifact identity: unavailable {rel}: {type(exc).__name__}"
            ) from exc
        assert len(raw) == size and hashlib.sha256(raw).hexdigest() == digest, (
            f"historical artifact identity: changed bytes at {rel}"
        )
        sources.append((rel, raw))
    return tuple(sources)


def _sweep(root: Path, archival_imports: tuple = ()) -> tuple:
    """Return missing modules/names, checked count, and archival unresolved sites.

    The caller explicitly opts into the closed historical classification.
    Identity validation is outside the cache and precedes parsing. Validate again
    before returning so a changed artifact cannot reuse an earlier cached pass.
    """
    sources = _validated_archival_sources(root, archival_imports)
    result = _sweep_validated(root, archival_imports, sources)
    _validated_archival_sources(root, archival_imports)
    return result



# ---------------------------------------------------------------------------
# Static resolution
# ---------------------------------------------------------------------------

def test_parse_releases_raw_ast_after_caller_drops_reference(tmp_path):
    """A repo-wide sweep must not pin every parsed AST in an unbounded cache.

    The WSL trusted pool shares a 10 GiB MemoryHigh / 12 GiB MemoryMax envelope.
    Caching every source AST made two ordinary copies of this guard retain more
    than that envelope by themselves and stretched otherwise-small packs from
    seconds into tens of minutes. Module-scope summaries and the completed
    sweep may stay memoized; raw per-file ASTs must remain transient regardless
    of which caching implementation a future edit might otherwise choose.
    """
    import gc
    import weakref

    probe = tmp_path / "ast-lifetime-probe.py"
    probe.write_text("VALUE = 1\n", encoding="utf-8")
    tree = _parse(probe)
    retained = weakref.ref(tree)
    del tree
    gc.collect()

    assert retained() is None, (
        "_parse retained a raw AST after its caller released it; a repo-wide "
        "sweep would pin the first-party AST estate for the pytest lifetime"
    )


def _python_files(root: Path) -> list[Path]:
    """*.py under root, pruning _SKIP_DIRS without descending into them."""
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fn in filenames:
            if fn.endswith(".py"):
                out.append(Path(dirpath) / fn)
    return sorted(out)


def _parse(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return None


def _module_file(root: Path, module: str) -> Path | None:
    """Filesystem file backing a dotted module name, if any."""
    base = root / Path(*module.split("."))
    for cand in (base.with_suffix(".py"), base / "__init__.py"):
        if cand.is_file():
            return cand
    return None


def _is_package_dir(root: Path, module: str) -> bool:
    return (root / Path(*module.split("."))).is_dir()


def _is_submodule(root: Path, module: str, name: str) -> bool:
    """`from pkg import name` where name is a module, not an attribute."""
    base = root / Path(*module.split("."))
    return (base / f"{name}.py").is_file() or (base / name / "__init__.py").is_file()


@lru_cache(maxsize=None)
def _module_scope_names(path: Path) -> tuple[frozenset[str], bool]:
    """Names bound at module scope, and whether the module is statically opaque.

    Descends into `if` / `try` / `for` / `while` / `with` bodies (a name bound in a
    conditional branch is still a module attribute) but NOT into function or class
    bodies (those bind locals, not module attributes).
    """
    tree = _parse(path)
    if tree is None:
        return frozenset(), True  # not this guard's job to enforce parseability

    names: set[str] = set()
    opaque = False

    def bind(target: ast.expr) -> None:
        if isinstance(target, ast.Name):
            names.add(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                bind(elt)
        elif isinstance(target, ast.Starred):
            bind(target.value)

    def walk(body: list[ast.stmt]) -> None:
        nonlocal opaque
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    bind(t)
            elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
                bind(node.target)
            elif isinstance(node, ast.Import):
                for a in node.names:
                    names.add(a.asname or a.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                for a in node.names:
                    if a.name == "*":
                        opaque = True  # re-exports we cannot enumerate
                    else:
                        names.add(a.asname or a.name)
            elif isinstance(node, (ast.If, ast.Try, ast.While, ast.With,
                                   ast.For, ast.AsyncFor, ast.AsyncWith)):
                walk(node.body)
                walk(getattr(node, "orelse", []))
                walk(getattr(node, "finalbody", []))
                for handler in getattr(node, "handlers", []):
                    walk(handler.body)

    walk(tree.body)
    if "__getattr__" in names:
        opaque = True  # PEP 562 dynamic module attributes
    return frozenset(names), opaque


def _resolve_module(node: ast.ImportFrom, path: Path, root: Path) -> str | None:
    """Absolute dotted module for an ImportFrom, resolving relative levels."""
    if node.level == 0:
        return node.module
    pkg_parts = list(path.relative_to(root).parts[:-1])
    up = node.level - 1
    if up:
        if up > len(pkg_parts):
            return None
        pkg_parts = pkg_parts[:-up]
    return ".".join(pkg_parts + ([node.module] if node.module else []))


@lru_cache(maxsize=None)
def _sweep_validated(root: Path, archival_imports: tuple, sources: tuple) -> tuple:
    """Memoise the AST sweep, never the historical identity validation."""
    missing_modules: list[str] = []
    missing_names: list[str] = []
    archival_unresolved: list[tuple[str, str, str]] = []
    archival_sites = frozenset((rel, module, name) for rel, _, _, module, name in archival_imports)
    sealed_sources = dict(sources)
    checked = 0

    for path in _python_files(root):
        rel = path.relative_to(root).as_posix()
        if rel in sealed_sources:
            try:
                tree = ast.parse(sealed_sources[rel].decode("utf-8"), filename=str(path))
            except (SyntaxError, UnicodeDecodeError) as exc:
                raise AssertionError(
                    f"historical artifact identity: unparseable declared source {rel}"
                ) from exc
        else:
            tree = _parse(path)
        if tree is None:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            module = _resolve_module(node, path, root)
            if not module or module.split(".")[0] not in FIRST_PARTY_ROOTS:
                continue

            aliases = [a.name for a in node.names if a.name != "*"]
            if not aliases:
                continue

            mod_file = _module_file(root, module)
            if mod_file is None:
                # A package dir with no __init__.py can still host submodules.
                if _is_package_dir(root, module):
                    for name in aliases:
                        checked += 1
                        if _is_submodule(root, module, name):
                            continue
                        if (rel, module, name) in _ALLOWED_UNRESOLVED:
                            continue
                        if (rel, module, name) in archival_sites:
                            archival_unresolved.append((rel, module, name))
                            continue
                        missing_names.append(
                            f"{rel}:{node.lineno} — `from {module} import {name}`: "
                            f"{module} has no submodule or attribute `{name}`"
                        )
                    continue
                checked += len(aliases)
                active_aliases = []
                for name in aliases:
                    if (rel, module, name) in archival_sites:
                        archival_unresolved.append((rel, module, name))
                    else:
                        active_aliases.append(name)
                if active_aliases:
                    missing_modules.append(
                        f"{rel}:{node.lineno} — `from {module} import "
                        f"{', '.join(active_aliases)}`: module {module} does not exist"
                    )
                continue

            names, opaque = _module_scope_names(mod_file)
            if opaque:
                continue  # star-import or __getattr__ — not statically resolvable

            for name in aliases:
                checked += 1
                if name in names or _is_submodule(root, module, name):
                    continue
                if (rel, module, name) in _ALLOWED_UNRESOLVED:
                    continue
                if (rel, module, name) in archival_sites:
                    archival_unresolved.append((rel, module, name))
                    continue
                missing_names.append(
                    f"{rel}:{node.lineno} — `from {module} import {name}`: "
                    f"{mod_file.relative_to(root).as_posix()} defines no `{name}`"
                )

    # Tuples: the lru_cache hands the SAME object to every caller.
    return tuple(missing_modules), tuple(missing_names), checked, tuple(archival_unresolved)


# ---------------------------------------------------------------------------
# Guard the guard — a vacuous sweep would make every assertion below pass
# ---------------------------------------------------------------------------

def test_sweep_checks_a_meaningful_number_of_sites():
    """A broken walker would report zero findings AND zero work. Pin the work."""
    _, _, checked, _ = _sweep(REPO, _D06_ARCHIVAL_IMPORTS)
    assert checked > 200, (
        f"only {checked} first-party import names checked — the AST sweep is broken "
        "or _SKIP_DIRS has swallowed the source tree"
    )


def test_sweep_flags_a_known_bad_import(tmp_path):
    """Synthesise the #3779 defect and assert this guard catches it."""
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "__init__.py").write_text("")
    (tmp_path / "lib" / "cal.py").write_text("def is_session(d):\n    return True\n")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "builder.py").write_text(
        "def _check_stale(d):\n"
        "    try:\n"
        "        from lib.cal import trading_dates_between\n"
        "        return bool(trading_dates_between(d))\n"
        "    except Exception:\n"
        "        return False\n"
    )
    missing_modules, missing_names, _, _ = _sweep(tmp_path)
    assert not missing_modules
    assert len(missing_names) == 1, missing_names
    assert "trading_dates_between" in missing_names[0]


def test_sweep_flags_a_missing_module(tmp_path):
    """`from engine import config` where engine/config.py does not exist."""
    (tmp_path / "engine").mkdir()
    (tmp_path / "engine" / "__init__.py").write_text("")
    (tmp_path / "engine" / "user.py").write_text(
        "def f():\n"
        "    from engine.data_store import store\n"
        "    return store\n"
    )
    missing_modules, missing_names, _, _ = _sweep(tmp_path)
    assert len(missing_modules) == 1, missing_modules
    assert "engine.data_store" in missing_modules[0]


@pytest.mark.parametrize("source,should_flag", [
    # legitimate — submodule import
    ("from lib import sub", False),
    # legitimate — name bound inside a try at module scope
    ("from lib.cal import MAYBE", False),
    # legitimate — name bound inside an `if` at module scope
    ("from lib.cal import CONDITIONAL", False),
    # legitimate — name bound in an except handler
    ("from lib.cal import FALLBACK", False),
    # legitimate — aliased import re-export
    ("from lib.cal import aliased", False),
    # legitimate — class and async def
    ("from lib.cal import Thing", False),
    ("from lib.cal import go", False),
    # the real thing
    ("from lib.cal import nope", True),
])
def test_no_false_positives_on_conditional_definitions(tmp_path, source, should_flag):
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "__init__.py").write_text("")
    (tmp_path / "lib" / "sub.py").write_text("")
    (tmp_path / "lib" / "cal.py").write_text(
        "import os as _os\n"
        "try:\n"
        "    MAYBE = 1\n"
        "except Exception:\n"
        "    FALLBACK = 2\n"
        "else:\n"
        "    OTHER = 3\n"
        "if _os.name == 'posix':\n"
        "    CONDITIONAL = 4\n"
        "from json import dumps as aliased\n"
        "class Thing:\n"
        "    pass\n"
        "async def go():\n"
        "    pass\n"
    )
    (tmp_path / "user.py").write_text(f"def f():\n    {source}\n    return 1\n")

    missing_modules, missing_names, _, _ = _sweep(tmp_path)
    assert not missing_modules
    assert bool(missing_names) is should_flag, (source, missing_names)


def test_star_import_makes_a_module_opaque_rather_than_noisy(tmp_path):
    """A module that re-exports via `*` must not produce phantom findings."""
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "__init__.py").write_text("")
    (tmp_path / "lib" / "cal.py").write_text("from os.path import *\n")
    (tmp_path / "user.py").write_text("from lib.cal import join\n")
    _, missing_names, _, _ = _sweep(tmp_path)
    assert not missing_names


def test_module_getattr_makes_a_module_opaque(tmp_path):
    """PEP 562 modules resolve attributes at runtime — do not guess."""
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "__init__.py").write_text("")
    (tmp_path / "lib" / "cal.py").write_text("def __getattr__(name):\n    return 1\n")
    (tmp_path / "user.py").write_text("from lib.cal import anything\n")
    _, missing_names, _, _ = _sweep(tmp_path)
    assert not missing_names


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------

def test_every_first_party_import_resolves():
    missing_modules, missing_names, _, archived = _sweep(REPO, _D06_ARCHIVAL_IMPORTS)
    expected = tuple((rel, module, name) for rel, _, _, module, name in _D06_ARCHIVAL_IMPORTS)
    assert archived == expected, (
        "historical dependencies must remain explicitly unresolved and unenrolled; "
        f"requalify the archival classification if a dependency is admitted: {archived}"
    )
    problems = list(missing_modules) + list(missing_names)
    assert not problems, (
        "first-party imports that cannot resolve (each one is an ImportError waiting "
        "to be swallowed by an `except`):\n  " + "\n  ".join(problems)
    )


# ---------------------------------------------------------------------------
# Closed historical classification — adverse controls, never an execution grant
# ---------------------------------------------------------------------------

def _archive_fixture(root: Path) -> None:
    (root / "scripts").mkdir()
    (root / "scripts" / "__init__.py").write_text("")
    for rel, _, _, _, _ in _D06_ARCHIVAL_IMPORTS:
        destination = root / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((REPO / rel).read_bytes())
        destination.chmod(0o644)


def test_archival_policy_matches_the_unchanged_published_manifest():
    manifest_path = REPO / "docs/pr-crops/d06-macro-integration-20261104/manifest.json"
    raw = manifest_path.read_bytes()
    assert len(raw) == 20695
    assert hashlib.sha256(raw).hexdigest() == (
        "34069a8fea9cba7ff0a46a6bd327639bbbfea15824cf4df7f39df50259c7bda4"
    )
    manifest = json.loads(raw)
    assert manifest["schema"] == "d06.artifact_inventory.v1"
    assert manifest["member_count"] == len(manifest["members"]) == 94
    members = {row["path"]: row for row in manifest["members"]}
    assert len(_D06_ARCHIVAL_IMPORTS) == 3
    for rel, size, digest, module, name in _D06_ARCHIVAL_IMPORTS:
        assert members[rel] == {"path": rel, "bytes": size, "sha256": digest}
        assert (module, name) == ("scripts", "verify_d06_macro")


@pytest.mark.parametrize("package_kind", ["regular", "namespace", "missing"])
def test_exact_archives_are_visible_as_unresolved(tmp_path, package_kind):
    _archive_fixture(tmp_path)
    if package_kind != "regular":
        (tmp_path / "scripts" / "__init__.py").unlink()
    if package_kind == "missing":
        (tmp_path / "scripts").rmdir()
    modules, names, checked, archived = _sweep(tmp_path, _D06_ARCHIVAL_IMPORTS)
    assert not modules and not names
    assert checked == 3
    assert archived == tuple(
        (rel, module, name) for rel, _, _, module, name in _D06_ARCHIVAL_IMPORTS
    )


@pytest.mark.parametrize("relative", [
    "scripts/current_consumer.py",
    "engine/current_consumer.py",
    "docs/pr-crops/d06-macro-integration-20261104/unlisted_copy.py",
])
def test_unlisted_and_active_importers_still_fail(tmp_path, relative):
    _archive_fixture(tmp_path)
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("from scripts import verify_d06_macro\n")
    modules, names, _, archived = _sweep(tmp_path, _D06_ARCHIVAL_IMPORTS)
    assert not modules
    assert len(names) == 1 and relative in names[0]
    assert len(archived) == 3


@pytest.mark.parametrize("mutation", ["byte", "removed_import", "syntax", "encoding", "missing"])
def test_archive_identity_fails_before_parsing(tmp_path, monkeypatch, mutation):
    _archive_fixture(tmp_path)
    path = tmp_path / _D06_ARCHIVAL_IMPORTS[0][0]
    if mutation == "byte":
        path.write_bytes(path.read_bytes() + b"\n")
    elif mutation == "removed_import":
        path.write_bytes(path.read_bytes().replace(b"from scripts import verify_d06_macro", b""))
    elif mutation == "syntax":
        path.write_bytes(b"not valid Python (\n")
    elif mutation == "encoding":
        path.write_bytes(b"\xff")
    else:
        path.unlink()

    def must_not_sweep(*_args, **_kwargs):
        pytest.fail("cached sweep entered before the archival identity check")
    monkeypatch.setitem(globals(), "_sweep_validated", must_not_sweep)
    with pytest.raises(AssertionError, match="historical artifact identity"):
        _sweep(tmp_path, _D06_ARCHIVAL_IMPORTS)


def test_unreadable_archive_fails_explicitly(tmp_path, monkeypatch):
    _archive_fixture(tmp_path)
    path = tmp_path / _D06_ARCHIVAL_IMPORTS[0][0]
    original = Path.read_bytes
    def denied(target):
        if target == path:
            raise PermissionError("synthetic fixture refusal")
        return original(target)
    monkeypatch.setattr(Path, "read_bytes", denied)
    with pytest.raises(AssertionError, match="historical artifact identity: unavailable"):
        _sweep(tmp_path, _D06_ARCHIVAL_IMPORTS)


@pytest.mark.parametrize("mutation", ["executable", "symlink", "parent_symlink"])
def test_archive_mode_change_is_not_classified(tmp_path, mutation):
    _archive_fixture(tmp_path)
    path = tmp_path / _D06_ARCHIVAL_IMPORTS[0][0]
    if mutation == "executable":
        path.chmod(0o755)
    elif mutation == "parent_symlink":
        original_parent = path.parent
        relocated = tmp_path / "relocated_archive"
        original_parent.rename(relocated)
        original_parent.symlink_to(relocated, target_is_directory=True)
    else:
        target = tmp_path / "same_bytes.py"
        target.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(target)
    with pytest.raises(AssertionError, match="historical artifact identity"):
        _sweep(tmp_path, _D06_ARCHIVAL_IMPORTS)


def test_cached_sweep_cannot_hide_a_later_archive_change(tmp_path):
    _archive_fixture(tmp_path)
    assert len(_sweep(tmp_path, _D06_ARCHIVAL_IMPORTS)[3]) == 3
    path = tmp_path / _D06_ARCHIVAL_IMPORTS[0][0]
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(AssertionError, match="historical artifact identity: changed bytes"):
        _sweep(tmp_path, _D06_ARCHIVAL_IMPORTS)


def test_classification_is_per_import_and_ast_only(tmp_path):
    # Synthetic, explicitly sealed fixture. Executing it would raise immediately.
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "__init__.py").write_text("")
    rel = "historical_fixture.py"
    raw = (
        b"raise AssertionError('archival source must never execute')\n"
        b"from scripts import verify_d06_macro\n"
        b"from scripts import another_missing_name\n"
        b"from engine.missing_module import still_missing\n"
    )
    (tmp_path / rel).write_bytes(raw)
    (tmp_path / rel).chmod(0o644)
    entries = ((rel, len(raw), hashlib.sha256(raw).hexdigest(), "scripts", "verify_d06_macro"),)
    modules, names, checked, archived = _sweep(tmp_path, entries)
    assert checked == 3
    assert archived == ((rel, "scripts", "verify_d06_macro"),)
    assert len(names) == 1 and "another_missing_name" in names[0]
    assert len(modules) == 1 and "engine.missing_module" in modules[0]


@pytest.mark.parametrize("module,name", [("tools", "verify_d06_macro"), ("scripts", "other_name")])
def test_archival_classification_requires_the_exact_import_tuple(tmp_path, module, name):
    _archive_fixture(tmp_path)
    entries = list(_D06_ARCHIVAL_IMPORTS)
    rel, size, digest, _, _ = entries[0]
    entries[0] = (rel, size, digest, module, name)
    modules, names, _, archived = _sweep(tmp_path, tuple(entries))
    assert not modules
    assert len(names) == 1 and rel in names[0]
    assert len(archived) == 2

"""A GitHub Actions annotation must START its line — so it can never go through logging.

GitHub only parses a workflow command (``::warning ...``, ``::error ...``,
``::notice ...``) when ``::`` is the first thing on the line.  Every builder in
this repo configures logging with a prefixing format — ``"%(levelname)s %(message)s"``
and friends — so ``log.warning("::warning title=x::…")`` emits::

    WARNING ::warning title=x::…

and GitHub silently drops it.  The call looks like an alarm in code review, runs
without error, and produces NOTHING in the Actions summary.  That is the worst
possible failure mode for a fail-soft: the builder ships degraded output and the
only signal it was supposed to raise does not exist.

This has now shipped dead at least five separate times (#3487, #3515, #3563,
#3570, and #3562 — which merged a fresh one on 2026-07-26, the same day the
others were being fixed).  Hence a guard rather than another one-off repair.

The fix is always the same: emit the annotation with a bare ``print`` to stdout,
and keep a ``log.*`` line (with ``exc_info`` where there is a traceback worth
having) when the human-readable log deserves more detail than the annotation.

Run: .venv/bin/python -m pytest tests/test_gh_annotation_line_start.py -q
"""

from __future__ import annotations

import ast
import hashlib
import stat
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# Directories whose modules execute inside a GitHub Actions step (nightly
# builders, engines, collectors, checks).  ``tests/`` is excluded on purpose: a
# test may legitimately build an annotation string to assert on it.
SCAN_DIRS = ("scripts", "engine", "collectors", "app", "admin", "lib", "tools", "research")

LEVELS = {"debug", "info", "warning", "error", "critical", "exception"}

# Modules that never run inside an Actions step, so a "::" prefix in their log
# message is dead decoration rather than a dropped annotation.  Removing the
# prefix there is a separate, deliberate change to production request paths.
EXEMPT: dict[str, str] = {
    "engine/neuralweb/brain_gateway.py": "FastAPI request path (app/main.py) — VPS, not CI",
    "engine/research_vault/download_quota.py": "FastAPI request path (app/research.py)",
    "engine/research_vault/view_ratelimit.py": "FastAPI request path (app/research.py)",
}


# #7182 keeps this immutable upstream reference at its documented R14 filename.
# It is historical source, not an Actions annotation producer. Preserve every
# byte and reject operational imports; this is not a directory-wide exemption.
_ARCHIVE_REL = "research/research_vault_expectations_r3/upstream/view_ratelimit.py"
_ARCHIVE_MODULE = _ARCHIVE_REL[:-3].replace("/", ".")
_ARCHIVE_GIT_BLOB = "5e33b4d213ff3b9497134343712921e3d3ac6b77"


def _validated_archival_snapshot(root: Path) -> Path:
    path = root / _ARCHIVE_REL
    try:
        current = path
        while current != root:
            assert not current.is_symlink(), "archival snapshot: symlink"
            current = current.parent
        mode = path.stat().st_mode
        assert stat.S_ISREG(mode) and not mode & 0o111, (
            "archival snapshot: expected a regular non-executable file"
        )
        raw = path.read_bytes()
    except OSError as exc:
        raise AssertionError(
            f"archival snapshot: unavailable ({type(exc).__name__})"
        ) from exc
    framed = b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    assert hashlib.sha1(framed).hexdigest() == _ARCHIVE_GIT_BLOB, (
        "archival snapshot: changed bytes; explicitly requalify the source role"
    )
    return path


def _static_archive_uses(source: str) -> list[int]:
    """Recognize direct imports and literal import/loader calls, without exec.

    This bounded check does not claim to resolve arbitrary computed imports.
    Documentation strings alone are not execution; the offline research runner
    remains outside the operational-root check.
    """
    tree = ast.parse(source)
    # Keep every candidate binding: an unrelated nested import must not hide
    # an outer loader. This conservative check does not execute name resolution.
    aliases: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                aliases.setdefault(name.asname or name.name.split(".")[0], set()).add(
                    name.name if name.asname else name.name.split(".")[0]
                )
        elif isinstance(node, ast.ImportFrom) and not node.level:
            for name in node.names:
                aliases.setdefault(name.asname or name.name, set()).add(
                    f"{node.module}.{name.name}"
                )

    def qualified(node):
        if isinstance(node, ast.Name):
            return aliases.get(node.id, {node.id})
        if isinstance(node, ast.Attribute):
            return {f"{parent}.{node.attr}" for parent in qualified(node.value)}
        return set()

    def literal(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Div)):
            left, right = literal(node.left), literal(node.right)
            if right is None:
                return None
            if isinstance(node.op, ast.Add):
                return left + right if left is not None else None
            return (left.rstrip("/") + "/" if left else "") + right.lstrip("/")
        if isinstance(node, ast.Call) and qualified(node.func) & {
            "Path", "pathlib.Path", "PurePosixPath", "pathlib.PurePosixPath"
        } and len(node.args) == 1 and not node.keywords:
            return literal(node.args[0])
        return None

    def is_target(value):
        if value is None:
            return False
        normalized = value.replace("\\", "/")
        return (
            value == _ARCHIVE_MODULE
            or value.startswith(_ARCHIVE_MODULE + ".")
            or normalized == _ARCHIVE_REL
            or normalized.endswith("/" + _ARCHIVE_REL)
        )

    # Values identify the argument that is actually imported/read/executed.
    loaders = {
        "__import__": (0, "name"),
        "builtins.__import__": (0, "name"),
        "importlib.import_module": (0, "name"),
        "runpy.run_module": (0, "mod_name"),
        "runpy.run_path": (0, "path_name"),
        "importlib.util.spec_from_file_location": (1, "location"),
        "importlib.machinery.SourceFileLoader": (1, "path"),
    }
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(is_target(name.name) for name in node.names):
                found.append(node.lineno)
        elif isinstance(node, ast.ImportFrom) and not node.level:
            if is_target(node.module) or any(
                is_target(f"{node.module}.{name.name}") for name in node.names
            ):
                found.append(node.lineno)
        elif isinstance(node, ast.Call):
            for call_name in qualified(node.func):
                spec = loaders.get(call_name)
                if spec is None:
                    continue
                index, keyword = spec
                argument = node.args[index] if len(node.args) > index else next(
                    (item.value for item in node.keywords if item.arg == keyword), None
                )
                if argument is not None and is_target(literal(argument)):
                    found.append(node.lineno)
                    break
    return sorted(set(found))


def _operational_archive_uses(root: Path) -> list[tuple[str, int]]:
    found = []
    for directory in SCAN_DIRS:
        if directory == "research":
            continue  # Preserve the documented, offline R14 reproduction contract.
        for path in (root / directory).rglob("*.py"):
            raw = path.read_bytes()
            # Parse before spelling checks: supported literal concatenations
            # need not contain either target name contiguously in the raw file.
            source = raw.decode("utf-8")
            found.extend(
                (path.relative_to(root).as_posix(), line)
                for line in _static_archive_uses(source)
            )
    return sorted(found)


def _annotation_head(node: ast.expr) -> str | None:
    """The leading literal of a string or f-string argument, if it starts with '::'."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value if node.value.startswith("::") else None
    if isinstance(node, ast.JoinedStr) and node.values:
        head = node.values[0]
        if isinstance(head, ast.Constant) and isinstance(head.value, str) \
           and head.value.startswith("::"):
            return head.value
    return None


def _looks_annotationish(blob: bytes) -> bool:
    """True when a string literal anywhere in the file OPENS with '::'.

    Keyed on the literal's opening quote, not the call paren: the earlier
    ``("::`` family required the annotation to sit on the call's own line, so
    ``log.warning(\\n    "::warning ...")`` was never parsed at all
    (mutation-confirmed miss, 2026-08-02).  Matching ``"::`` / ``'::`` also
    covers f-/r-prefixed literals and keeps this a strict superset of what the
    AST matcher below can flag; the ~40 extra files it admits cost ~0.1s.
    """
    return b'"::' in blob or b"'::" in blob


def _candidates() -> list[Path]:
    """Files worth parsing — cheap byte prefilter keeps the whole guard ~1s."""
    out = []
    for d in SCAN_DIRS:
        for p in (ROOT / d).rglob("*.py"):
            try:
                blob = p.read_bytes()
            except OSError:
                continue
            if _looks_annotationish(blob):
                out.append(p)
    return out


def _offenders() -> list[tuple[str, int, str]]:
    archival = _validated_archival_snapshot(ROOT)
    found = []
    for path in _candidates():
        rel = path.relative_to(ROOT).as_posix()
        if rel in EXEMPT or path == archival:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            func = node.func
            if not isinstance(func, ast.Attribute) or func.attr not in LEVELS:
                continue
            head = _annotation_head(node.args[0])
            if head is not None:
                found.append((rel, node.lineno, head.splitlines()[0][:70]))
    _validated_archival_snapshot(ROOT)
    return sorted(found)


def test_no_annotation_goes_through_a_logger():
    offenders = _offenders()
    assert not offenders, (
        "GitHub annotation routed through a logger — it will NEVER appear in the "
        "Actions summary, because logging prefixes the line and GitHub only parses "
        "'::' at column 0.\n"
        "Emit it with a bare print(..., flush=True) instead (keep a plain log.* line "
        "for humans if the detail is worth it):\n\n"
        + "\n".join(f"  {f}:{n}  {msg}" for f, n, msg in offenders)
    )


def test_exempt_entries_still_exist_and_still_offend():
    """An exemption that no longer applies must be deleted, not left to rot."""
    stale = []
    for rel, why in EXEMPT.items():
        path = ROOT / rel
        if not path.exists():
            stale.append(f"{rel}: file is gone ({why})")
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        hit = any(
            isinstance(n, ast.Call) and n.args
            and isinstance(n.func, ast.Attribute) and n.func.attr in LEVELS
            and _annotation_head(n.args[0]) is not None
            for n in ast.walk(tree)
        )
        if not hit:
            stale.append(f"{rel}: no annotation-shaped log call left — drop the exemption")
    assert not stale, "EXEMPT is out of date:\n" + "\n".join(f"  {s}" for s in stale)


def test_guard_catches_a_planted_offender(tmp_path):
    """Selftest: the matcher must actually fire, including on f-string messages."""
    src = (
        'import logging\n'
        'log = logging.getLogger("x")\n'
        'log.warning("::warning title=t::plain")\n'
        'log.error(f"::error::{1}")\n'
        'print("::notice::this one is fine")\n'
    )
    assert _looks_annotationish(src.encode())
    tree = ast.parse(src)
    hits = [
        n.lineno for n in ast.walk(tree)
        if isinstance(n, ast.Call) and n.args
        and isinstance(n.func, ast.Attribute) and n.func.attr in LEVELS
        and _annotation_head(n.args[0]) is not None
    ]
    assert hits == [3, 4], f"matcher missed a planted offender: {hits}"


def test_prefilter_admits_a_call_split_across_lines():
    """The prefilter must be a superset of the matcher, and the matcher must fire.

    ``log.warning(`` followed by the annotation on its own line contains none of
    the old ``("::`` byte shapes, so the guard skipped the file before the AST
    matcher ever saw the call — an offender the guard reviews as covered but
    cannot flag (the same silent-drop class it exists to catch).
    """
    src = (
        'import logging\n'
        'log = logging.getLogger("x")\n'
        'log.warning(\n'
        '    "::warning title=t::split across lines")\n'
        'log.error(\n'
        "    f'::error title=u::{1}')\n"
    )
    blob = src.encode()
    assert not (b'("::' in blob or b"('::" in blob
                or b'(f"::' in blob or b"(f'::" in blob), \
        "fixture no longer reproduces the shape the old prefilter missed"
    assert _looks_annotationish(blob)
    hits = [
        n.lineno for n in ast.walk(ast.parse(src))
        if isinstance(n, ast.Call) and n.args
        and isinstance(n.func, ast.Attribute) and n.func.attr in LEVELS
        and _annotation_head(n.args[0]) is not None
    ]
    assert hits == [3, 5], f"matcher missed the split offenders: {hits}"


# Exact historical identity and ordinary-guard adverse controls.
def _copy_archival_fixture(root: Path) -> Path:
    target = root / _ARCHIVE_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((ROOT / _ARCHIVE_REL).read_bytes())
    target.chmod(0o644)
    return target


def test_archival_snapshot_is_exact_and_not_operationally_imported():
    assert _validated_archival_snapshot(ROOT) == ROOT / _ARCHIVE_REL
    uses = _operational_archive_uses(ROOT)
    assert not uses, (
        "historical reference used by operational code; requalify its role:\n"
        + "\n".join(f"  {path}:{line}" for path, line in uses)
    )


@pytest.mark.parametrize("mutation", [
    "byte", "annotation_removed", "missing", "executable", "symlink", "parent_symlink",
])
def test_archival_identity_is_checked_before_the_prefilter(tmp_path, monkeypatch, mutation):
    path = _copy_archival_fixture(tmp_path)
    if mutation == "byte":
        path.write_bytes(path.read_bytes() + b"\n")
    elif mutation == "annotation_removed":
        raw = path.read_bytes()
        changed = raw.replace(b"::", b"")
        assert changed != raw
        path.write_bytes(changed)
    elif mutation == "missing":
        path.unlink()
    elif mutation == "executable":
        path.chmod(0o755)
    elif mutation == "symlink":
        target = tmp_path / "same_bytes.py"
        target.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(target)
    else:
        parent = path.parent
        moved = tmp_path / "moved_upstream"
        parent.rename(moved)
        parent.symlink_to(moved, target_is_directory=True)
    monkeypatch.setitem(globals(), "ROOT", tmp_path)

    def must_not_scan():
        pytest.fail("annotation prefilter entered before identity validation")

    monkeypatch.setitem(globals(), "_candidates", must_not_scan)
    with pytest.raises(AssertionError, match="archival snapshot:"):
        _offenders()


def test_archival_read_error_is_not_an_exemption(tmp_path, monkeypatch):
    path = _copy_archival_fixture(tmp_path)
    read_bytes = Path.read_bytes

    def denied(candidate):
        if candidate == path:
            raise PermissionError("synthetic unreadable fixture")
        return read_bytes(candidate)

    monkeypatch.setattr(Path, "read_bytes", denied)
    with pytest.raises(AssertionError, match="archival snapshot: unavailable"):
        _validated_archival_snapshot(tmp_path)


def test_archival_identity_is_rechecked_after_scanning(tmp_path, monkeypatch):
    path = _copy_archival_fixture(tmp_path)
    monkeypatch.setitem(globals(), "ROOT", tmp_path)

    def mutate_after_validation():
        path.write_bytes(path.read_bytes() + b"\n")
        return []

    monkeypatch.setitem(globals(), "_candidates", mutate_after_validation)
    with pytest.raises(AssertionError, match="archival snapshot: changed bytes"):
        _offenders()


def test_archival_exception_does_not_hide_a_neighbor_or_active_logger(tmp_path, monkeypatch):
    _copy_archival_fixture(tmp_path)
    neighbor = tmp_path / "research" / "unlisted_copy.py"
    neighbor.write_bytes((tmp_path / _ARCHIVE_REL).read_bytes())
    active = tmp_path / "scripts" / "active.py"
    active.parent.mkdir()
    active.write_text(
        'log.warning(\n    "::warning::multiline")\n'
        'log.error(f"::error::{1}")\n'
    )
    monkeypatch.setitem(globals(), "ROOT", tmp_path)
    offenders = _offenders()
    assert any(path == "research/unlisted_copy.py" for path, _, _ in offenders)
    assert sum(path == "scripts/active.py" for path, _, _ in offenders) == 2
    assert not any(path == _ARCHIVE_REL for path, _, _ in offenders)


@pytest.mark.parametrize("source", [
    "import research.research_vault_expectations_r3.upstream.view_ratelimit",
    "import research.research_vault_expectations_r3.upstream.view_ratelimit as archived",
    "from research.research_vault_expectations_r3.upstream import view_ratelimit as archived",
    "from research.research_vault_expectations_r3.upstream.view_ratelimit import anything",
    'import importlib as il; il.import_module("research.research_vault_expectations_r3.upstream.view_ratelimit")',
    'from importlib import import_module as load; load(name="research.research_vault_expectations_r3.upstream.view_ratelimit")',
    '__import__("research.research_vault_expectations_r3.upstream.view_ratelimit")',
    'import runpy; runpy.run_path("research/research_vault_expectations_r3/upstream/view_ratelimit.py")',
    'from runpy import run_module as run; run("research.research_vault_expectations_r3.upstream.view_ratelimit")',
    'from importlib.util import spec_from_file_location as spec; spec("archived", "research/research_vault_expectations_r3/upstream/view_ratelimit.py")',
    'from importlib.machinery import SourceFileLoader as loader; loader("archived", "/repo/research/research_vault_expectations_r3/upstream/view_ratelimit.py")',
    'from pathlib import Path; import runpy; runpy.run_path(ROOT / "research" / "research_vault_expectations_r3" / "upstream" / "view_ratelimit.py")',
])
def test_literal_operational_archive_use_is_detected(source):
    assert _static_archive_uses(source)


@pytest.mark.parametrize(("source", "line"), [
    ("import runpy\nrunpy.run_path(\"research/\" + \"research_vault_\" + \"expectations_r3/upstream/\" + \"view_\" + \"ratelimit.py\")\n", 2),
    ("import importlib as loader\ndef unrelated():\n    import json as loader\nloader.import_module(\"research.research_vault_expectations_r3.upstream.view_ratelimit\")\n", 4),
])
def test_operational_wrapper_preserves_supported_literal_and_alias_detection(tmp_path, source, line):
    active = tmp_path / "scripts" / "consumer.py"
    active.parent.mkdir()
    active.write_text(source, encoding="utf-8")
    assert _operational_archive_uses(tmp_path) == [("scripts/consumer.py", line)]


@pytest.mark.parametrize("source", [
    "from engine.research_vault import view_ratelimit",
    "import engine.research_vault.view_ratelimit as limiter",
    'documentation = "import research.research_vault_expectations_r3.upstream.view_ratelimit"',
    'record_reference("research/research_vault_expectations_r3/upstream/view_ratelimit.py")',
])
def test_reference_text_and_current_runtime_module_are_not_archive_execution(source):
    assert _static_archive_uses(source) == []


def test_offline_reproduction_reference_is_preserved(tmp_path):
    offline = tmp_path / "research" / "r14" / "run_review.py"
    offline.parent.mkdir(parents=True)
    offline.write_text(
        'import runpy; runpy.run_path("research/research_vault_expectations_r3/upstream/view_ratelimit.py")'
    )
    assert _operational_archive_uses(tmp_path) == []
    active = tmp_path / "scripts" / "consumer.py"
    active.parent.mkdir()
    active.write_text(offline.read_text())
    assert _operational_archive_uses(tmp_path) == [("scripts/consumer.py", 1)]

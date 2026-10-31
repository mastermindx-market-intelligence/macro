"""Composition root, import closure, and the one public-preview owner (F11)."""
from __future__ import annotations

import ast
import importlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from engine.research_vault import catalog as catalog_mod
from engine.research_vault.r2_store import LocalStore
from engine.research_vault.read_service import ServerReadContext
from scripts.check_research_vault_source_freshness import evaluate

REPO = Path(__file__).resolve().parents[1]
# The historical app helper, frozen verbatim. This is the oracle, not a second
# production owner.
_PUBLIC_PREVIEW_COUNT = 3

FORBIDDEN = (
    "engine.research_vault.ingest",
    "engine.research_vault.probe",
    "engine.research_intelligence.vault_head",
    "engine.press",
    "app",
    "pypdf",
    "PyPDF2",
    "pdfminer",
    "fitz",
    "pymupdf",
    "pdfplumber",
    "pdftotext",
)


def _catalog_preview(catalog: dict, limit: int = _PUBLIC_PREVIEW_COUNT) -> dict:
    """Return only the newest summary-ready reports while retaining total count."""
    items = list(catalog.get("items") or [])
    ready = [
        item for item in items
        if any(str(point or "").strip() for point in ((item or {}).get("summary_points") or []))
    ]
    preview = ready[:limit]
    selected = {str((item or {}).get("id") or "") for item in preview}
    if len(preview) < limit:
        preview.extend(
            item for item in items
            if str((item or {}).get("id") or "") not in selected
        )
    public = dict(catalog)
    public["items"] = preview[:limit]
    public["count"] = len(items)
    public["preview"] = True
    public["summary"] = catalog.get("summary") or catalog_mod.public_summary(catalog)
    public["institutions"] = sorted({
        str((item or {}).get("institution") or "").strip()
        for item in public["items"]
        if str((item or {}).get("institution") or "").strip()
    })
    return public


def _is_forbidden(name: str) -> bool:
    return any(name == item or name.startswith(item + ".") for item in FORBIDDEN)


def _module_file(name: str) -> Path | None:
    if not name or name.startswith("."):
        return None
    parts = name.split(".")
    candidate = REPO.joinpath(*parts)
    module = candidate.with_suffix(".py")
    if module.is_file():
        return module
    init = candidate / "__init__.py"
    if init.is_file():
        return init
    return None


def _parents(name: str) -> list[str]:
    parts = name.split(".")
    return [".".join(parts[:index]) for index in range(1, len(parts))]


def _import_targets(module: str, path: Path, node: ast.AST) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if not isinstance(node, ast.ImportFrom):
        return []
    if node.level:
        parts = module.split(".")
        if path.name != "__init__.py":
            parts = parts[:-1]
        drop = node.level - 1
        if drop:
            parts = parts[:-drop]
        base_parts = parts
        if node.module:
            base_parts = parts + node.module.split(".")
        base = ".".join(base_parts)
        targets = [base] if base else []
        for alias in node.names:
            child = f"{base}.{alias.name}" if base else alias.name
            if _module_file(child) is not None:
                targets.append(child)
        return targets
    base = node.module or ""
    targets = [base] if base else []
    for alias in node.names:
        child = f"{base}.{alias.name}" if base else alias.name
        if _module_file(child) is not None:
            targets.append(child)
        elif not base:
            targets.append(alias.name)
    return targets


def import_closure(root: str) -> tuple[set[str], list[tuple[str, int, str]]]:
    """Transitive first-party import closure, including function-local imports."""
    recorded: set[str] = set()
    edges: list[tuple[str, int, str]] = []
    visited: set[str] = set()
    queue = [root]
    while queue:
        name = queue.pop()
        if name in visited:
            continue
        visited.add(name)
        recorded.add(name)
        path = _module_file(name)
        if path is None:
            continue
        for parent in _parents(name):
            if parent not in visited:
                queue.append(parent)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            for target in _import_targets(name, path, node):
                if not target:
                    continue
                edges.append((str(path), getattr(node, "lineno", 0), target))
                recorded.add(target)
                if _module_file(target) is not None and target not in visited:
                    queue.append(target)
    return recorded, edges


def _runtime_modules(statement: str) -> list[str]:
    proc = subprocess.run(
        [sys.executable, "-c", statement],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)


def _denied(names) -> list[str]:
    return sorted(name for name in names if _is_forbidden(name))


def test_read_runtime_closure_denies_ingest_probe_press_app_and_pdf():
    recorded, edges = import_closure("engine.research_vault.read_runtime")
    offenders = [
        f"{path}:{line} -> {module}"
        for path, line, module in edges
        if _is_forbidden(module)
    ]
    forbidden_names = _denied(recorded)
    assert not offenders, "forbidden import edges:\n" + "\n".join(offenders)
    assert not forbidden_names, forbidden_names

    modules = _runtime_modules(
        "import json, sys, engine.research_vault.read_runtime; "
        "print(json.dumps(sorted(sys.modules)))"
    )
    runtime_offenders = _denied(modules)
    assert not runtime_offenders, runtime_offenders


def test_closure_walker_positive_control_finds_probe_or_vault_head_from_ingest():
    recorded, _edges = import_closure("engine.research_vault.ingest")
    assert (
        "engine.research_vault.probe" in recorded
        or "engine.research_intelligence.vault_head" in recorded
    )


def test_runtime_closure_positive_control_vault_head_loads_ingest():
    modules = _runtime_modules(
        "import json, sys, engine.research_intelligence.vault_head; "
        "print(json.dumps(sorted(sys.modules)))"
    )
    assert "engine.research_vault.ingest" in modules


def test_importing_read_runtime_does_not_build_the_store(monkeypatch):
    import engine.research_vault.r2_store as r2_store

    def _boom(*_args, **_kwargs):
        raise AssertionError("build_store ran at import")

    monkeypatch.setattr(r2_store, "build_store", _boom)
    runtime = importlib.reload(importlib.import_module("engine.research_vault.read_runtime"))
    assert runtime.build_read_service is not None
    assert runtime._service is None


def test_zero_arg_build_uses_the_real_classifier(tmp_path, monkeypatch):
    store_dir = tmp_path / "store"
    monkeypatch.setenv("RESEARCH_LOCAL_STORE", str(store_dir))
    for name in (
        "R2_RESEARCH_BUCKET",
        "R2_RESEARCH_ENDPOINT",
        "R2_RESEARCH_ACCESS_KEY_ID",
        "R2_RESEARCH_SECRET_ACCESS_KEY",
        "R2_BUCKET",
        "R2_ENDPOINT",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
    ):
        monkeypatch.delenv(name, raising=False)

    now = datetime.now(timezone.utc) - timedelta(minutes=1)
    published = (now - timedelta(hours=1)).isoformat()
    document = {
        "schema": catalog_mod.SCHEMA,
        "generated_at": "",
        "count": 0,
        "institutions": [],
        "items": [{
            "id": "desk-note-1",
            "title": "Desk Note",
            "institution": "Example Bank",
            "side": "sell",
            "published_at": published,
            "summary_points": ["A ready summary."],
        }],
    }
    store = LocalStore(store_dir)
    store.put_bytes(
        catalog_mod.CATALOG_KEY,
        catalog_mod.serialize(document, now),
        "application/json",
    )
    parsed = catalog_mod.parse_strict(store.get_bytes_strict(catalog_mod.CATALOG_KEY), now=now)

    runtime = importlib.import_module("engine.research_vault.read_runtime")
    service = runtime.build_read_service()
    assert service._source_classifier is not None
    status = service.status(caller_context=ServerReadContext(
        principal_id="u-pro",
        entitlement="pro",
        scopes=frozenset({"status", "fetch", "find_evidence", "search"}),
        surface="brain",
    ))
    expected = evaluate(parsed, now=datetime.now(timezone.utc), source="catalog")
    assert status["ok"] is True
    assert status["source"]["state"] == expected["status"]
    assert status["source"]["state"] in {"SOURCE_FRESH", "PRODUCER_STALE"}


def _preview_catalogs() -> list[dict]:
    ready = lambda id_, points: {
        "id": id_, "summary_points": points, "institution": "Desk",
    }
    return [
        {"items": [ready("only", ["one ready"])]},
        {"items": [
            {"id": "blank-points", "summary_points": ["   ", ""]},
            {"id": "no-points"},
            None,
        ]},
        {"items": [ready(f"r{i}", [f"point {i}"]) for i in range(5)]},
        {"items": [
            {"id": "dup", "summary_points": []},
            {"id": "dup", "summary_points": []},
            {"id": "other", "summary_points": []},
        ]},
        {"items": [
            {"id": "", "summary_points": []},
            {"id": "", "summary_points": [""]},
            {"id": "kept", "summary_points": []},
        ]},
        {"items": [None, {"id": "a", "summary_points": [" ready "]}, None]},
        {"items": [
            {"id": "ws", "summary_points": [" \t ", None]},
            ready("real", ["kept"]),
            {"id": "tail", "summary_points": []},
        ]},
    ]


def test_backend_preview_matches_the_frozen_public_app_selection_rule():
    for catalog in _preview_catalogs():
        # The ordinary app remains unchanged in this backend-only source slice.
        # Check the backend selector against its frozen historical rule without
        # importing the full application and its unrelated runtime closure.
        old = _catalog_preview(catalog)
        assert catalog_mod.preview_items(catalog) == old["items"]
        assert catalog_mod.preview_ids(catalog) == [
            str((item or {}).get("id") or "") for item in old["items"]
        ]

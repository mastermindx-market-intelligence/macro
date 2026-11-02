"""FIF Z0 closure-matrix gap test: A23, the saved-research half.

A23 of research/financial_intelligence_fabric/FIF_Z0_CLOSURE_MATRIX.json
requires that saved research does not alter canonical facts. Generation
isolation is already proven by tests/test_fif_z0_gap_a23_a38.py::
test_a23_two_generations_one_store_one_provider. This module proves the
saved-research half over the code as it exists — tests only, no production
change.

A saved view lives only in the reader's browser briefcase
(``fundamental_forensics.saved_research.v1``). Restoring one re-POSTs its
stored ``request`` as ``JSON.stringify(view.request)``
(tests/fundamental_forensics_saved_research_roundtrip.test.mjs, "pinned
restore re-POSTs the stored request bytes verbatim"), and the briefcase
makes zero network calls when it saves ("the store makes zero network calls
and writes only its own key"). The server side:

- S1: every committed saved view, replayed with the page's wire bytes
  through the production query route, answers byte-identically to a direct
  query of the same request — on every repeat and interleaved with direct
  queries — and leaves the production store byte-identical (objects,
  versions, write counter). A pinned view whose clock predates the
  generation's admission fails closed byte-identically; it is never
  answered from that later generation.
- S2: the forensics router has no saved-research route; every write method
  on the query path is a private 405 that leaves the store untouched.
- S3: the saved-research notification producer and its runner never import
  the production dataset store or name a store write API.

Helpers are imported from tests/test_fif_z0_gap_a23_a38.py and
tests/test_fundamental_forensics_financial_query_api.py; they are not copied.
"""
from __future__ import annotations

import ast
import json
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.forensics as forensics_api
from engine.fundamental_forensics.api_client import encode_query_request
from tests.test_fif_z0_gap_a23_a38 import (  # noqa: F401 — pytest fixtures
    _post,
    _production_provider,
    aapl_material,
    router_app,
)
from tests.test_fundamental_forensics_financial_query_api import _QUERY_PATH, _assert_private_headers

ROOT = Path(__file__).resolve().parents[1]
_SAVED_DIR = ROOT / "tests" / "fixtures" / "fundamental_forensics" / "fif_saved_research"
_SAVED_CONTRACT = "fundamental_forensics.saved_research.v1"
_REPLAYS = 3

# The saved-research producer and its runner: neither may reach the
# production dataset store.
_SAVED_RESEARCH_SOURCES = (
    ROOT / "engine" / "fif_saved_research_notifications.py",
    ROOT / "scripts" / "run_fif_saved_research_notifications.py",
)
_STORE_WRITE_NAMES = frozenset(
    {
        "production_datasets",
        "publish_production_dataset",
        "put_bytes",
        "put_bytes_strict_conditional",
        "raw_put",
    }
)


def _saved_views() -> list[tuple[str, dict]]:
    views = []
    for path in sorted(_SAVED_DIR.glob("saved_*.json")):
        container = json.loads(path.read_text(encoding="utf-8"))
        assert container["contract"] == _SAVED_CONTRACT, path.name
        for view in container["saved_views"]:
            views.append((f"{path.name}:{view['id']}", view))
    return views


def _page_wire_bytes(request: dict) -> bytes:
    """The bytes the page posts on restore: ``JSON.stringify(view.request)``
    — insertion order, no whitespace, non-ASCII unescaped."""
    return json.dumps(request, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _store_state(store) -> tuple[dict, dict, int]:
    return dict(store._objects), dict(store._versions), store._counter


def _utc(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def test_a23_replaying_saved_views_leaves_store_and_answers_byte_identical(
    router_app, monkeypatch, aapl_material
) -> None:
    """S1: saved-view replays never alter canonical facts or their answers."""
    from engine.fundamental_forensics import production_datasets as PDS

    store = PDS.InMemoryStrictConditionalStore()
    g1 = PDS.publish_production_dataset(store, aapl_material)
    _production_provider(router_app, monkeypatch, store)
    baseline = _store_state(store)
    assert baseline[0], "the published generation wrote objects"

    views = _saved_views()
    assert len(views) >= 5, "every committed saved-view fixture is replayed"

    with TestClient(router_app, raise_server_exceptions=False) as client:
        # Direct answers first, from the canonical request encoding.
        direct = {}
        for name, view in views:
            response = _post(client, _QUERY_PATH, encode_query_request(view["request"]))
            _assert_private_headers(response)
            direct[name] = (response.status_code, response.content)
        assert _store_state(store) == baseline

        served = refused = 0
        for name, view in views:
            status, body = direct[name]
            recorded_at = _utc(view["request"]["policy"]["recorded_at"])
            if recorded_at >= _utc(g1.admitted_at):
                assert status == 200, name
                assert json.loads(body)["delivery"]["dataset_generation_id"] == g1.generation_id, name
                served += 1
            else:
                # A pinned clock before the generation's admission fails
                # closed; it is never answered from the later generation.
                assert status == 503, name
                assert json.loads(body)["detail"] == "financial query temporarily unavailable", name
                refused += 1
        assert served >= 1 and refused >= 1, (served, refused)

        # Replays with the page's wire bytes, interleaved with direct queries.
        for _ in range(_REPLAYS):
            for name, view in views:
                replay = _post(client, _QUERY_PATH, _page_wire_bytes(view["request"]))
                assert (replay.status_code, replay.content) == direct[name], name
                _assert_private_headers(replay)
                assert replay.headers["cache-control"] == "private, no-store", name
                assert _store_state(store) == baseline, name
                again = _post(client, _QUERY_PATH, encode_query_request(view["request"]))
                assert (again.status_code, again.content) == direct[name], name
                assert _store_state(store) == baseline, name

    # The saved fixtures themselves are untouched by the replays.
    assert [view for _, view in _saved_views()] == [view for _, view in views]


def test_a23_router_has_no_saved_research_write_path(router_app, monkeypatch, aapl_material) -> None:
    """S2: no saved-research route exists; write methods on the query path
    are a private 405 and leave the production store untouched."""
    from engine.fundamental_forensics import production_datasets as PDS

    paths = [route.path for route in forensics_api.router.routes]
    assert not [path for path in paths if "saved" in path.lower() or "briefcase" in path.lower()], paths
    for route in forensics_api.router.routes:
        if "POST" in (getattr(route, "methods", None) or ()):
            assert route.path.startswith("/api/forensics/v1/financial/"), route.path

    store = PDS.InMemoryStrictConditionalStore()
    PDS.publish_production_dataset(store, aapl_material)
    _production_provider(router_app, monkeypatch, store)
    baseline = _store_state(store)
    _, view = _saved_views()[0]
    with TestClient(router_app, raise_server_exceptions=False) as client:
        for method in ("PUT", "PATCH", "DELETE"):
            response = client.request(
                method,
                _QUERY_PATH,
                content=_page_wire_bytes(view["request"]),
                headers={"content-type": "application/json"},
            )
            assert response.status_code == 405, method
            _assert_private_headers(response)
            assert _store_state(store) == baseline, method


def _store_write_names(source: str) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            parts = {part for alias in node.names for part in alias.name.split(".")}
        elif isinstance(node, ast.ImportFrom):
            parts = set((node.module or "").split(".")) | {alias.name for alias in node.names}
        elif isinstance(node, ast.Attribute):
            parts = {node.attr}
        elif isinstance(node, ast.Name):
            parts = {node.id}
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            parts = set(node.value.replace("/", ".").split("."))
        else:
            continue
        found |= parts & _STORE_WRITE_NAMES
    return found


def test_a23_store_write_guard_flags_a_planted_writer() -> None:
    """The S3 guard is not vacuous: a planted store writer is named."""
    planted = (
        "from engine.fundamental_forensics import production_datasets\n"
        "def save(store, view):\n"
        "    store.put_bytes('k', b'v')\n"
        "    production_datasets.publish_production_dataset(store, view)\n"
    )
    assert _store_write_names(planted) == {"production_datasets", "put_bytes", "publish_production_dataset"}
    assert _store_write_names("import importlib\nimportlib.import_module('engine.fundamental_forensics.production_datasets')\n") == {
        "production_datasets"
    }


@pytest.mark.parametrize("path", _SAVED_RESEARCH_SOURCES, ids=lambda path: path.name)
def test_a23_saved_research_producer_never_reaches_the_production_store(path: Path) -> None:
    """S3: the producer and its runner name no production-store write API."""
    assert path.is_file(), path
    assert _store_write_names(path.read_text(encoding="utf-8")) == set(), path.name

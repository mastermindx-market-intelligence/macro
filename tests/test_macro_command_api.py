"""Offline API contract tests for ``GET /api/macro/command`` (F01 Macro Command).

The endpoint is an artifact reader, like every other production desk API: it
serves the FINAL Macro Command composition — ``read`` + ``strip`` + ``coverage``
from ``macro_suite_view.build_command_header``, restricted by
``scripts.build_macro_suite_pages._restrict_header_to_populated`` to the panels
that actually shipped, plus the projected ``sections`` and one honest row per
selected workspace — straight out of the qualified served root
(``/opt/macro/site.served``, never a repo/CWD fallback). These tests pin that
boundary hermetically:

* Bearer authentication for a REGISTERED user runs BEFORE any file read, and
  no paid tier is required (the override user carries no plan at all);
* the served root is the fixed qualified root: monkeypatched to a private tmp
  ``site.served`` tree built from the REAL composer, REAL contract and the
  REAL ``read_workspace`` — the composition itself is never monkeypatched
  except for the one narrow manifest-changed-during-composition race;
* a manifest that is missing, corrupt, oversized or changed mid-composition is
  a 503 ``{"error": "macro command unavailable"}`` with no partial body;
* ONE unreadable/mismatched workspace is a typed local refusal next to its
  healthy siblings — never a healthy-looking empty, never a 500;
* the response is private/no-store and noindex/noarchive, and the read is
  strictly read-only: no rendering, no fragments, no writes.

Runnable standalone:

    python3 -m pytest tests/test_macro_command_api.py -q
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

import pytest

pytest.importorskip("fastapi", reason="macro command API tests need fastapi")
pytest.importorskip("httpx", reason="FastAPI TestClient needs httpx")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import macro_command as mc  # noqa: E402
from engine.market_os.macro_workspaces import contract, liquidity_regime  # noqa: E402
from lib import macro_suite_view  # noqa: E402
from scripts import build_macro_suite_pages as builder  # noqa: E402

COMMAND_PATH = "/api/macro/command"
RESPONSE_SCHEMA = "mastermind.macro_command_read.v1"
DEFAULT_SERVED_ROOT = "/opt/macro/site.served"
HUB_PAGE_PATH = "/macro_monetary.html"
#: The producer stamp the fixture manifest carries — the response must pass it
#: through verbatim as ``source.manifest_generated_at``, never re-stamp it.
BUILT_AT = "2026-09-04T00:00:00Z"
EFFECTIVE_DATE = "2026-09-03"
MANIFEST_LIMIT_BYTES = 256 * 1024
BODY_LIMIT_BYTES = 2 * 1024 * 1024

TOP_LEVEL_KEYS = {"schema", "state", "source", "read", "strip", "coverage", "sections", "workspaces"}
SOURCE_KEYS = {"served_root_qualified", "manifest_generated_at", "manifest_sha256",
               "composed_at", "min_client_contract"}
ROW_KEYS = {"workspace_id", "region", "href", "title", "state", "effective_date",
            "calculation_as_of", "content_sha256", "generation_id", "availability", "failure"}
SECTION_KEYS = {"id", "label", "href", "deep_href", "detail_links", "subtabs"}
SUBTAB_KEYS = {"id", "label", "deep_href"}


def _page(workspace_id: str) -> builder.SuitePage:
    return next(page for page in builder.SUITE_PAGES if page.workspace_id == workspace_id)


#: The narrow admitted selection: the one workspace the real composer builds
#: hermetically. Everything else in these tests reads exactly this page.
NARROW_PAGES = (_page("liquidity_regime"),)
DUAL_PAGES = (_page("liquidity_regime"), _page("growth_real_economy"))


# --------------------------------------------------------------------------- #
# fixture: a private served tree from the real composer + contract
# --------------------------------------------------------------------------- #

def _regime() -> dict:
    """The committed liquidity-regime owner fixture (as in
    ``tests/test_macro_workspace_contract.py``) — real composer input."""
    return {
        "asof": EFFECTIVE_DATE, "date": EFFECTIVE_DATE,
        "liquidity_overlay": "contracting",
        "liquidity_quality": {
            "asof": EFFECTIVE_DATE, "label": "contracting", "quantity_roc_bn": -165.3,
            "rrp_buffer_bn": 6.7, "rrp_exhausted": True,
            "composition": {"mechanical": True},
            "stress_overlay": {"confirming_stress": False, "hy_oas_z": -0.2, "hy_oas_pct": 2.66},
            "walcl_stale_days": 1, "degraded": False,
        },
        "conditions": {
            "stale_inputs": [],
            "vintages": {
                "nfci": {"asof": "2026-08-28", "stale": False},
                "ofr_fsi": {"asof": "2026-08-30", "stale": False},
                "hy_oas": {"asof": "2026-09-02", "stale": False},
            },
            "financial_conditions": {"nfci": -0.558, "nfci_pctile": 0.046},
            "systemic_stress": {"ofr_fsi": -2.749, "ofr_fsi_pctile": 0.0278},
        },
        "regime_vector": {"rate_pressure_rates_scare_score": 43.2,
                          "rate_pressure_real10y_chg63_bp": 24.0},
    }


def _snapshot_for(workspace_id: str, *, effective_date: str | None = None) -> dict:
    """One sealed contract body. ``liquidity_regime`` is the real composer's
    own output; the other registry ids reuse that composed body under their own
    closed-registry identity (``finalize`` re-seals the relabeled content), so
    every row a test writes is a body the real ``read_workspace`` accepts."""
    body = liquidity_regime.compose(_regime(), built_at=BUILT_AT)
    if workspace_id != "liquidity_regime":
        body["workspace"]["id"] = workspace_id
    if effective_date is not None:
        body["headline"]["effective_date"] = effective_date
    return contract.finalize(body)


def _snapshot_bytes(snapshot: Mapping[str, Any]) -> bytes:
    # The producer's published form: human-diffable, digest-independent.
    return (json.dumps(snapshot, indent=2, ensure_ascii=False, sort_keys=True)
            + "\n").encode("utf-8")


class Served:
    """A private ``site.served`` root written the way the producer writes it:
    every selected body first, the combined manifest LAST."""

    def __init__(self, root: Path, pages: tuple[builder.SuitePage, ...],
                 *, effective_date: str | None = None) -> None:
        self.root = root
        self.data_root = root / "macrodata"
        self.pages = pages
        self.snapshots: dict[str, dict] = {}
        self.payloads: dict[str, bytes] = {}
        self._effective_date = effective_date
        self.rebuild()

    def rebuild(self) -> None:
        rows: dict[str, dict] = {}
        for page in self.pages:
            snapshot = _snapshot_for(page.workspace_id, effective_date=self._effective_date)
            payload = _snapshot_bytes(snapshot)
            relative = f"workspaces/{page.workspace_id}/{page.region}/latest.json"
            body_path = self.data_root / relative
            body_path.parent.mkdir(parents=True, exist_ok=True)
            body_path.write_bytes(payload)
            self.snapshots[page.workspace_id] = snapshot
            self.payloads[page.workspace_id] = payload
            rows[f"{page.workspace_id}/{page.region}"] = {
                "workspace": page.workspace_id,
                "region": page.region,
                "path": relative,
                "content_sha256": snapshot["generation"]["content_sha256"],
                "bytes": len(payload),
                "build_state": "BUILT",
                "generation_id": snapshot["generation"]["generation_id"],
                "built_at": BUILT_AT,
            }
        self.write_manifest({
            "schema": "mastermind.macro_workspace_manifest.v1",
            "generated_at": BUILT_AT,
            "min_client_contract": builder.MIN_CLIENT_CONTRACT,
            "workspaces": rows,
        })

    def write_manifest(self, manifest: Mapping[str, Any]) -> None:
        raw = (json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True)
               + "\n").encode("utf-8")
        path = self.data_root / "workspaces" / "manifest.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        self.manifest_raw = raw
        self.manifest_digest = sha256(raw).hexdigest()

    def rewrite_manifest(self, mutate) -> None:
        doc = json.loads(self.manifest_raw.decode("utf-8"))
        mutate(doc)
        self.write_manifest(doc)

    def manifest_path(self) -> Path:
        return self.data_root / "workspaces" / "manifest.json"

    def body_path(self, workspace_id: str) -> Path:
        page = _page(workspace_id)
        return (self.data_root / "workspaces" / workspace_id / page.region / "latest.json")

    def tree_digest(self) -> list[tuple[str, str]]:
        return sorted(
            (str(path.relative_to(self.root)), sha256(path.read_bytes()).hexdigest())
            for path in self.root.rglob("*") if path.is_file()
        )


# --------------------------------------------------------------------------- #
# fixtures: standalone app + dependency override + served-root binding
# --------------------------------------------------------------------------- #

def _patch_admitted_pages(monkeypatch: pytest.MonkeyPatch,
                          pages: tuple[builder.SuitePage, ...]) -> None:
    """Only SUITE_PAGES are admitted; the narrow fixture admits fewer so the
    composition runs over exactly the workspaces the tmp root publishes."""
    monkeypatch.setattr(builder, "SUITE_PAGES", pages)
    if hasattr(mc, "SUITE_PAGES"):
        monkeypatch.setattr(mc, "SUITE_PAGES", pages, raising=False)


def _bind_served_root(monkeypatch: pytest.MonkeyPatch, served: Served) -> None:
    monkeypatch.setattr(mc, "_served_root", lambda: served.root)


def _install_registered_user(app: FastAPI) -> None:
    """A REGISTERED reader with NO plan/entitlement/tier field at all: the
    endpoint must serve the full read without any paid tier."""
    app.dependency_overrides[mc.require_user] = lambda: {"id": "registered-reader"}


def _make_client(monkeypatch: pytest.MonkeyPatch, served: Served,
                 pages: tuple[builder.SuitePage, ...]) -> TestClient:
    _patch_admitted_pages(monkeypatch, pages)
    _bind_served_root(monkeypatch, served)
    app = FastAPI()
    app.include_router(mc.router)
    _install_registered_user(app)
    return TestClient(app)


@pytest.fixture()
def served(tmp_path: Path) -> Served:
    return Served(tmp_path / "site.served", NARROW_PAGES)


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, served: Served) -> TestClient:
    return _make_client(monkeypatch, served, NARROW_PAGES)


@pytest.fixture()
def dual(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Served, TestClient]:
    served = Served(tmp_path / "site.served", DUAL_PAGES)
    return served, _make_client(monkeypatch, served, DUAL_PAGES)


# --------------------------------------------------------------------------- #
# helpers: reader replication + response pins
# --------------------------------------------------------------------------- #

def _reader_entries(served: Served,
                    pages: tuple[builder.SuitePage, ...]) -> list[dict[str, Any]]:
    """The entries list, assembled exactly as the reader does: the REAL
    ``read_workspace`` against the SAME served tree."""
    entries: list[dict[str, Any]] = []
    for page in pages:
        identity = builder._identity(page)
        entry: dict[str, Any] = {
            "workspace_id": page.workspace_id, "region": page.region,
            "output": page.output, "title": identity["title"],
            "subtitle": identity["subtitle"], "snapshot": None, "failure": None,
        }
        try:
            snapshot, _artifact = builder.read_workspace(served.data_root, page)
            entry["snapshot"] = snapshot
        except builder.SnapshotRefused as refusal:
            entry["failure"] = {"kind": refusal.kind, "detail": refusal.detail}
        entries.append(entry)
    return entries


def _assert_private_output(response) -> None:
    cache = {token.strip().lower()
             for token in response.headers.get("cache-control", "").split(",")}
    assert cache == {"private", "no-store"}
    robots = {token.strip().lower()
              for token in response.headers.get("x-robots-tag", "").split(",")}
    assert robots == {"noindex", "noarchive"}


def _assert_unavailable(response) -> None:
    assert response.status_code == 503
    assert response.json() == {"error": "macro command unavailable"}
    _assert_private_output(response)


def _assert_typed_refusal(row: Mapping[str, Any], served: Served) -> None:
    """One unreadable workspace is a TYPED local refusal with a public generic
    detail — never a healthy-looking empty row, never a free-text leak."""
    assert set(row) == ROW_KEYS
    failure = row["failure"]
    assert isinstance(failure, Mapping) and set(failure) == {"kind", "detail"}
    assert re.fullmatch(r"[A-Z][A-Z0-9_]+", str(failure["kind"]))
    assert isinstance(failure["detail"], str) and failure["detail"]
    assert str(served.root) not in failure["detail"]
    assert not row["state"]
    assert row["content_sha256"] is None
    assert row["effective_date"] is None
    assert row["calculation_as_of"] is None


def _parse_utc(value: Any) -> datetime:
    assert isinstance(value, str) and value.strip()
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


# --------------------------------------------------------------------------- #
# authentication
# --------------------------------------------------------------------------- #

def test_get_requires_bearer_and_401s_before_any_file_read(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    empty_root = tmp_path / "site.served"
    empty_root.mkdir()
    monkeypatch.setattr(mc, "_served_root", lambda: empty_root)

    def _no_reads(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("no source may be read before authentication")

    monkeypatch.setattr(mc, "_bounded_bytes", _no_reads)
    monkeypatch.setattr(mc, "_served_root", _no_reads)
    for target in (mc, builder):
        for name in ("read_workspace", "_read_workspace"):
            if hasattr(target, name):
                monkeypatch.setattr(target, name, _no_reads, raising=False)

    app = FastAPI()
    app.include_router(mc.router)  # the REAL require_user — no override here
    client = TestClient(app)
    for headers in (None, {"Authorization": "Basic ZHVtbXk6ZHVtbXk="}):
        response = client.get(COMMAND_PATH, headers=headers)
        assert response.status_code == 401
        body = response.json()
        assert "schema" not in body and "sections" not in body
        assert "workspaces" not in body and "read" not in body
    # an empty served root stays empty: not a single path was touched
    assert list(empty_root.rglob("*")) == []


def test_registered_user_without_paid_entitlement_gets_the_full_read(
        client: TestClient) -> None:
    response = client.get(COMMAND_PATH)
    assert response.status_code == 200
    body = response.json()
    assert body["schema"] == RESPONSE_SCHEMA
    assert body["coverage"]["total"] >= 1
    assert isinstance(body["workspaces"], list) and body["workspaces"]


# --------------------------------------------------------------------------- #
# the 200 wire shape — exactly the final composition
# --------------------------------------------------------------------------- #

def test_success_serves_the_final_composition_exactly(
        client: TestClient, served: Served) -> None:
    started = datetime.now(timezone.utc)
    response = client.get(COMMAND_PATH)
    ended = datetime.now(timezone.utc)
    assert response.status_code == 200
    _assert_private_output(response)
    body = response.json()
    assert set(body) == TOP_LEVEL_KEYS
    assert body["schema"] == RESPONSE_SCHEMA

    source = body["source"]
    assert set(source) == SOURCE_KEYS
    assert source["served_root_qualified"] is True
    # truthful clocks: the manifest stamp passes through verbatim; composed_at
    # is this composition's own wall clock, not the manifest's.
    assert source["manifest_generated_at"] == BUILT_AT
    assert source["manifest_sha256"] == served.manifest_digest
    assert source["min_client_contract"] == builder.MIN_CLIENT_CONTRACT
    composed_at = _parse_utc(source["composed_at"])
    window = timedelta(seconds=2)
    assert started - window <= composed_at <= ended + window

    # The exact final pipeline, recomputed here over the SAME entries the real
    # reader assembles from the SAME tree:
    #   build_command_header -> _macro_command_sections
    #   -> _restrict_header_to_populated
    entries = _reader_entries(served, NARROW_PAGES)
    header = macro_suite_view.build_command_header(
        entries, page_built_at=source["composed_at"])
    sections = builder._macro_command_sections(
        entries, page_built_at=source["composed_at"])
    panel_ids = {section["id"] for section in sections}
    builder._restrict_header_to_populated(header, entries, panel_ids)
    assert body["read"] == header["read"]
    assert body["strip"] == header["strip"]
    assert body["coverage"] == header["coverage"]
    # populated parity: the coverage the page ships, not the raw unfiltered
    # tally. (Today the two coincide numerically — every rail section ships a
    # figure or a typed empty — so the exact pipeline equality above is the
    # load-bearing pin: the numbers must come out of
    # _restrict_header_to_populated, not out of a shortcut.)
    available, total = builder.populated_section_coverage_tally(entries, panel_ids)
    assert body["coverage"] == {"available": available, "total": total}
    assert body["coverage"]["total"] == len(panel_ids)

    # sections: the projected wire shape, and nothing more (no new scores)
    assert [section["id"] for section in body["sections"]] == [
        section["id"] for section in sections]
    full_by_id = {section["id"]: section for section in sections}
    for projected in body["sections"]:
        full = full_by_id[projected["id"]]
        assert set(projected) == SECTION_KEYS
        assert projected["href"] == f"{HUB_PAGE_PATH}#{projected['id']}"
        assert projected["label"] == full["label"]
        assert projected["deep_href"] == full["deep_href"]
        assert projected["detail_links"] == full["detail_links"]
        assert all(link.get("href") for link in projected["detail_links"])
        full_tabs = full.get("subtabs") or []
        assert len(projected["subtabs"]) == len(full_tabs)
        for tab, full_tab in zip(projected["subtabs"], full_tabs):
            assert set(tab) == SUBTAB_KEYS
            assert tab["id"] == full_tab["id"]
            assert tab["label"] == full_tab["label"]
            assert tab["deep_href"] == full_tab["deep_href"]
    assert any(section["subtabs"] for section in body["sections"])
    overview = next(s for s in body["sections"] if s["id"] == "overview")
    assert len(overview["detail_links"]) == len(builder.rail_workspace_ids())


def test_workspace_rows_reflect_the_real_reader(
        client: TestClient, served: Served) -> None:
    response = client.get(COMMAND_PATH)
    assert response.status_code == 200
    rows = response.json()["workspaces"]
    assert [row["workspace_id"] for row in rows] == [
        page.workspace_id for page in NARROW_PAGES]
    row = rows[0]
    assert set(row) == ROW_KEYS
    assert row["region"] == "US"
    assert row["failure"] is None
    snapshot = served.snapshots["liquidity_regime"]
    assert row["state"] == snapshot["availability"]["state"] == "CURRENT"
    assert row["availability"] == snapshot["availability"]
    assert row["generation_id"] == snapshot["generation"]["generation_id"]
    assert response.json()["state"] == "ready"
    assert row["effective_date"] == snapshot["headline"]["effective_date"]
    assert row["effective_date"] == EFFECTIVE_DATE
    assert row["calculation_as_of"] == snapshot["generation"]["calculation_as_of"]
    assert row["content_sha256"] == snapshot["generation"]["content_sha256"]
    assert isinstance(row["title"], Mapping)
    assert row["title"]["en"] and row["title"]["zh"]
    # the deep link to the workspace page is retained
    assert "macro_liquidity_regime.html" in row["href"]


# --------------------------------------------------------------------------- #
# manifest admission
# --------------------------------------------------------------------------- #

def test_unknown_manifest_workspace_rows_are_ignored(
        client: TestClient, served: Served) -> None:
    served.rewrite_manifest(lambda doc: doc["workspaces"].update({
        "future_workspace/US": {
            "workspace": "future_workspace", "region": "US",
            "path": "workspaces/future_workspace/US/latest.json",
            "content_sha256": "0" * 64, "bytes": 1,
        },
    }))
    response = client.get(COMMAND_PATH)
    assert response.status_code == 200
    body = response.json()
    assert [row["workspace_id"] for row in body["workspaces"]] == [
        page.workspace_id for page in NARROW_PAGES]
    assert body["source"]["manifest_sha256"] == served.manifest_digest


# --------------------------------------------------------------------------- #
# one unreadable workspace: a typed refusal beside healthy siblings
# --------------------------------------------------------------------------- #

def _assert_local_refusal_and_healthy_sibling(response, served: Served,
                                              failed_id: str, healthy_id: str) -> None:
    assert response.status_code == 200
    assert response.json()["state"] == "partial"
    rows = {row["workspace_id"]: row for row in response.json()["workspaces"]}
    _assert_typed_refusal(rows[failed_id], served)
    healthy = rows[healthy_id]
    assert healthy["failure"] is None
    assert healthy["state"] == "CURRENT"
    assert healthy["content_sha256"] == served.snapshots[healthy_id][
        "generation"]["content_sha256"]


def test_missing_selected_body_is_a_typed_refusal_with_healthy_siblings(
        dual) -> None:
    served, client = dual
    served.body_path("growth_real_economy").unlink()
    _assert_local_refusal_and_healthy_sibling(
        client.get(COMMAND_PATH), served,
        "growth_real_economy", "liquidity_regime")


def test_tampered_selected_body_is_a_typed_refusal_not_a_healthy_empty(
        dual) -> None:
    served, client = dual
    path = served.body_path("growth_real_economy")
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    snapshot["headline"]["effective_date"] = "1999-01-01"  # tamper after sealing
    path.write_text(json.dumps(snapshot), encoding="utf-8")
    _assert_local_refusal_and_healthy_sibling(
        client.get(COMMAND_PATH), served,
        "growth_real_economy", "liquidity_regime")


def test_manifest_digest_mismatch_is_a_typed_refusal_no_body_substitution(
        dual) -> None:
    served, client = dual
    served.rewrite_manifest(lambda doc: doc["workspaces"]["growth_real_economy/US"]
                            .update({"content_sha256": "f" * 64}))
    _assert_local_refusal_and_healthy_sibling(
        client.get(COMMAND_PATH), served,
        "growth_real_economy", "liquidity_regime")


def test_oversized_selected_body_is_a_typed_refusal(dual) -> None:
    served, client = dual
    path = served.body_path("growth_real_economy")
    bloated = path.read_bytes() + b" " * (BODY_LIMIT_BYTES + 1024)
    path.write_bytes(bloated)
    served.rewrite_manifest(lambda doc: doc["workspaces"]["growth_real_economy/US"]
                            .update({"bytes": len(bloated)}))
    _assert_local_refusal_and_healthy_sibling(
        client.get(COMMAND_PATH), served,
        "growth_real_economy", "liquidity_regime")


def test_manifest_path_traversal_is_refused(dual, tmp_path: Path) -> None:
    served, client = dual
    outside = tmp_path / "outside.json"
    payload = served.payloads["growth_real_economy"]
    outside.write_bytes(payload)  # a real body parked OUTSIDE the served root
    served.rewrite_manifest(lambda doc: doc["workspaces"]["growth_real_economy/US"]
                            .update({"path": "../../outside.json", "bytes": len(payload)}))
    _assert_local_refusal_and_healthy_sibling(
        client.get(COMMAND_PATH), served,
        "growth_real_economy", "liquidity_regime")


# --------------------------------------------------------------------------- #
# the overall manifest: missing / corrupt / oversized / changed -> 503
# --------------------------------------------------------------------------- #

def test_missing_manifest_is_unavailable(client: TestClient, served: Served) -> None:
    served.manifest_path().unlink()
    _assert_unavailable(client.get(COMMAND_PATH))


def test_corrupt_manifest_is_unavailable(client: TestClient, served: Served) -> None:
    served.manifest_path().write_bytes(b'{"workspaces": {"liquidity_regime/US"')
    _assert_unavailable(client.get(COMMAND_PATH))


def test_oversized_manifest_is_unavailable(client: TestClient, served: Served) -> None:
    served.rewrite_manifest(
        lambda doc: doc.update({"padding": "x" * (MANIFEST_LIMIT_BYTES + 1)}))
    _assert_unavailable(client.get(COMMAND_PATH))


def test_manifest_changed_during_composition_is_unavailable(
        client: TestClient, served: Served, monkeypatch: pytest.MonkeyPatch) -> None:
    """Torn-generation safety: the raw manifest bytes read at the beginning and
    at the end must match; a publish that lands mid-composition must never
    serve bodies read under the old manifest."""
    manifest_path = served.manifest_path()
    real_bounded_bytes = mc._bounded_bytes
    state = {"reads": 0}

    def publish_after_first_read(path, root, maximum):
        data = real_bounded_bytes(path, root, maximum)
        if path == manifest_path:
            state["reads"] += 1
            if state["reads"] == 1:
                # Publish after capturing the initial manifest. The second
                # real bounded read must observe and reject this generation.
                doc = json.loads(data)
                doc["generated_at"] = "2030-01-01T00:00:00Z"
                manifest_path.write_text(json.dumps(doc), encoding="utf-8")
        return data

    monkeypatch.setattr(mc, "_bounded_bytes", publish_after_first_read)
    _assert_unavailable(client.get(COMMAND_PATH))
    assert state["reads"] == 2


# --------------------------------------------------------------------------- #
# the served root is fixed: the qualified served root, nothing else
# --------------------------------------------------------------------------- #

def test_served_root_defaults_to_the_qualified_root_and_ignores_caller_env(
        monkeypatch: pytest.MonkeyPatch) -> None:
    assert os.fsdecode(mc._served_root()) == DEFAULT_SERVED_ROOT
    for name in ("MACRO_SERVED_ROOT", "MACRO_SITE_SERVED", "MACRO_SITE_ROOT",
                 "MACRO_DATA_ROOT", "MACRO_COMMAND_SERVED_ROOT", "SERVED_ROOT",
                 "SITE_SERVED_ROOT", "MACRO_ROOT", "MACRO_REPO"):
        monkeypatch.setenv(name, "/tmp/decoy-served-root-never-created")
    assert os.fsdecode(mc._served_root()) == DEFAULT_SERVED_ROOT


def test_default_root_never_falls_back_to_repo_or_cwd_trees(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """With the default root unpatched, a complete valid served tree parked in
    the CWD (both spellings: ``site.served`` and ``site/``) must never be read."""
    decoy = Served(tmp_path / "site.served", NARROW_PAGES,
                   effective_date="2001-01-01")
    shutil.copytree(decoy.root, tmp_path / "site")
    monkeypatch.chdir(tmp_path)
    app = FastAPI()
    app.include_router(mc.router)
    _install_registered_user(app)
    response = TestClient(app).get(COMMAND_PATH)
    if response.status_code == 200:
        body = response.json()
        assert body["source"]["manifest_sha256"] != decoy.manifest_digest
        assert all(row.get("effective_date") != "2001-01-01"
                   for row in body["workspaces"])
        repo_manifest = ROOT / "site" / "macrodata" / "workspaces" / "manifest.json"
        if repo_manifest.exists():
            assert body["source"]["manifest_sha256"] != sha256(
                repo_manifest.read_bytes()).hexdigest()
    else:
        _assert_unavailable(response)


# --------------------------------------------------------------------------- #
# read-only: no rendering, no fragments, no writes
# --------------------------------------------------------------------------- #

def test_command_read_never_renders_or_writes(
        monkeypatch: pytest.MonkeyPatch, served: Served) -> None:
    _patch_admitted_pages(monkeypatch, NARROW_PAGES)
    _bind_served_root(monkeypatch, served)

    def _boom(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("the command API must never render or write")

    for name in ("write_fragments", "build_hub", "render", "render_page", "build_page"):
        monkeypatch.setattr(builder, name, _boom, raising=False)
        if hasattr(mc, name):
            monkeypatch.setattr(mc, name, _boom, raising=False)
    from lib import pages as lib_pages  # noqa: PLC0415 — the builder's write path
    monkeypatch.setattr(lib_pages, "write_page", _boom, raising=False)

    before = served.tree_digest()
    app = FastAPI()
    app.include_router(mc.router)
    _install_registered_user(app)
    response = TestClient(app).get(COMMAND_PATH)
    assert response.status_code == 200
    assert response.json()["schema"] == RESPONSE_SCHEMA
    assert served.tree_digest() == before


@pytest.mark.parametrize("change", [
    {"schema": "unrecognized.v9"},
    {"min_client_contract": "unsupported.v9"},
    {"generated_at": "2026-09-04T00:00:00"},
    {"workspaces": []},
])
def test_incompatible_manifest_fails_closed(client, served, change):
    served.rewrite_manifest(lambda doc: doc.update(change))
    _assert_unavailable(client.get(COMMAND_PATH))


def test_symlink_served_root_is_unavailable(monkeypatch, served, tmp_path):
    alias = tmp_path / "served-alias"
    alias.symlink_to(served.root, target_is_directory=True)
    client = _make_client(monkeypatch, served, NARROW_PAGES)
    monkeypatch.setattr(mc, "_served_root", lambda: alias)
    _assert_unavailable(client.get(COMMAND_PATH))


def test_symlink_body_is_refused_even_when_bytes_are_valid(dual, tmp_path):
    served, client = dual
    path = served.body_path("growth_real_economy")
    outside = tmp_path / "valid-body.json"
    path.rename(outside)
    path.symlink_to(outside)
    _assert_local_refusal_and_healthy_sibling(
        client.get(COMMAND_PATH), served,
        "growth_real_economy", "liquidity_regime")


def test_all_missing_bodies_are_explicitly_unavailable(client, served):
    served.body_path("liquidity_regime").unlink()
    response = client.get(COMMAND_PATH)
    assert response.status_code == 200
    assert response.json()["state"] == "unavailable"
    _assert_typed_refusal(response.json()["workspaces"][0], served)


def test_aggregate_read_budget_fails_closed(dual, monkeypatch):
    served, client = dual
    # Allow the first body through the existing conservative budget guard,
    # then reject the next read without returning a partially built aggregate.
    monkeypatch.setattr(mc, "TOTAL_MAX_BYTES",
                        mc.BODY_MAX_BYTES + len(served.manifest_raw))
    _assert_unavailable(client.get(COMMAND_PATH))


def test_assembled_app_auth_success_and_failure_are_private_no_store(monkeypatch, served):
    import app.main as main_mod

    _patch_admitted_pages(monkeypatch, NARROW_PAGES)
    _bind_served_root(monkeypatch, served)
    assembled = TestClient(main_mod.app, raise_server_exceptions=False)
    overrides = dict(main_mod.app.dependency_overrides)
    try:
        main_mod.app.dependency_overrides.clear()
        response = assembled.get(COMMAND_PATH)
        assert response.status_code == 401
        assert response.headers["cache-control"] == "private, no-store"
        _install_registered_user(main_mod.app)
        response = assembled.get(COMMAND_PATH)
        assert response.status_code == 200
        assert response.json()["schema"] == RESPONSE_SCHEMA
        assert response.json()["state"] == "ready"
        assert response.headers["cache-control"] == "private, no-store"
        served.manifest_path().unlink()
        response = assembled.get(COMMAND_PATH)
        assert response.status_code == 503
        assert response.json() == {"error": "macro command unavailable"}
        assert response.headers["cache-control"] == "private, no-store"
    finally:
        main_mod.app.dependency_overrides.clear()
        main_mod.app.dependency_overrides.update(overrides)


def test_router_auth_survives_unavailable_composer_dependencies():
    import subprocess

    code = '''import sys, importlib.abc
class RefuseComposerDependency(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('jinja2', 'jsonschema'):
            raise ImportError('composer dependency intentionally unavailable')
sys.meta_path.insert(0, RefuseComposerDependency())
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app import macro_command
from fastapi import HTTPException
application = FastAPI()
application.include_router(macro_command.router)
def deny():
    raise HTTPException(status_code=401)
application.dependency_overrides[macro_command.require_user] = deny
client = TestClient(application)
assert client.get('/api/macro/command').status_code == 401
application.dependency_overrides[macro_command.require_user] = lambda: {'id': 'registered'}
response = client.get('/api/macro/command')
assert response.status_code == 503
assert response.json() == {'error': 'macro command unavailable'}
assert response.headers['cache-control'] == 'private, no-store'
'''
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True,
                   capture_output=True, text=True)

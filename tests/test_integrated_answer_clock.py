"""Composer current-source clock contract tests (C19 WP16, test-only).

Pins the clock contract of ``app/integrated_answer.py`` exactly as it behaves
at base 6ba70f04ec: page ``as_of`` = max surfaced leg clock with a
``composed_at`` fallback, the ``STALE_DAYS`` sweep boundary and its
``event_workspace`` exemption, the missing-owner-clock fallbacks, and the
``_make_ref`` shape. Time is injected exclusively through
``app.integrated_answer._utc_now`` — no assertion reads the wall clock.

ONE strict xfail names DEFECT C19-WP16-D1: the financial leg echoes the
literal request cutoff ``2026-08-23T12:00:00Z`` instead of a producer-derived
clock; the C19 WP05 fix flips it loudly (strict).

The cold-compose bound (blob-keyed k3e reuse, the overall leg deadline) is pinned
at the end of this file.

This lane never sets ``MACRO_INTEGRATED_ANSWER_ENABLED`` — the flag-off 404 is
pinned in :func:`test_route_stays_off_when_flag_unset`, and every composition
test drives ``_compose_page`` or the ``_leg_*`` builders directly.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import contextvars
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import threading

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.integrated_answer as integrated_answer
from app.forensics import require_site_full_user
from app.integrated_answer import router as integrated_answer_router
from engine.company_theme_exposure.views import build_bundle, write_generation
from engine.k3e_expectation_surface import ATTEMPTS_PATH, OBSERVATIONS_PATH, QueryRefusal
from scripts import query_k3e_expectation_surface as qk3e
from tests.test_company_theme_exposure import _company_tree, _crosswalk, _membership
from tests.test_integrated_answer_v0 import pin_capital_structure_leg

NOW = "2026-10-11T12:00:00Z"
FINANCIAL_ROUTE = "/api/forensics/v1/financial/query"
PUBLICATION_ROUTE = "/api/forensics/v1/attested-history/latest"


@pytest.fixture(autouse=True)
def _pin_capital_structure_leg(monkeypatch: pytest.MonkeyPatch) -> None:
    pin_capital_structure_leg(monkeypatch)

DEFECT_D1_REASON = (
    "DEFECT C19-WP16-D1: financial leg as_of echoes the literal request cutoff "
    "2026-08-23T12:00:00Z (app/integrated_answer.py :310/:334) and the request "
    "policy clocks are literals (:309-310); fix lands in C19 WP05 (ledger D13)"
)


def _ts(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)


def _shift(text: str, **delta) -> str:
    return (_ts(text) + timedelta(**delta)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _surfaced_leg(leg_id: str, *, route: str, as_of: str, payload: dict) -> dict:
    leg = integrated_answer._leg_shell(leg_id)
    leg["status"] = "ok"
    leg["payload"] = payload
    leg["ref"] = integrated_answer._make_ref(route=route, as_of=as_of, payload=payload)
    return leg


def _page_stamp_leg() -> dict:
    return _surfaced_leg(
        "publication_seam",
        route=PUBLICATION_ROUTE,
        as_of=NOW,
        payload={"published_at": NOW},
    )


def _absent_seams(monkeypatch) -> None:
    """Every un-stubbed seam answers absent, like tests/test_integrated_answer_v0.py."""
    monkeypatch.setattr(
        integrated_answer, "_k3e_source", lambda: (_ for _ in ()).throw(QueryRefusal("absent"))
    )
    monkeypatch.setattr(integrated_answer, "_expectation_chips", lambda _day: {})
    monkeypatch.setattr(
        integrated_answer, "_receipt_identity", lambda: (_ for _ in ()).throw(RuntimeError("off"))
    )
    monkeypatch.setattr(integrated_answer, "_event_result", lambda _t: {"available": False})
    monkeypatch.setattr(integrated_answer, "_theme_context", lambda: None)
    monkeypatch.setattr(integrated_answer, "_cte_dir", lambda: Path("/nonexistent"))


def _compose_with_legs(monkeypatch, *, financial: dict, publication: dict | None = None) -> dict:
    _absent_seams(monkeypatch)
    monkeypatch.setattr(integrated_answer, "_utc_now", lambda: NOW)
    monkeypatch.setattr(integrated_answer, "_leg_financial_facts", lambda _t, *_a, **_k: financial)
    if publication is not None:
        monkeypatch.setattr(integrated_answer, "_leg_publication_seam", lambda: publication)
    return integrated_answer._compose_page("AAPL")


def _leg(page: dict, leg_id: str) -> dict:
    for item in page["legs"]:
        if item["leg"] == leg_id:
            return item
    raise KeyError(leg_id)


def test_route_stays_off_when_flag_unset(monkeypatch) -> None:
    monkeypatch.delenv("MACRO_INTEGRATED_ANSWER_ENABLED", raising=False)
    assert os.environ.get("MACRO_INTEGRATED_ANSWER_ENABLED") != "1"
    app = FastAPI()
    app.include_router(integrated_answer_router)
    app.dependency_overrides[require_site_full_user] = lambda: {"id": "test-user"}
    client = TestClient(app)
    response = client.get("/api/integrated-answer/v1/AAPL")
    assert response.status_code == 404
    # this lane never arms the route: the env var was never set anywhere
    assert "MACRO_INTEGRATED_ANSWER_ENABLED" not in os.environ


def test_page_as_of_is_max_of_surfaced_leg_clocks(monkeypatch) -> None:
    financial = _surfaced_leg(
        "financial_facts", route=FINANCIAL_ROUTE, as_of=_shift(NOW, days=-21), payload={"request": {}}
    )
    publication = _surfaced_leg(
        "publication_seam",
        route=PUBLICATION_ROUTE,
        as_of=_shift(NOW, days=-6),
        payload={"published_at": _shift(NOW, days=-6)},
    )
    page = _compose_with_legs(monkeypatch, financial=financial, publication=publication)
    assert page["composed_at"] == NOW
    assert page["as_of"] == _shift(NOW, days=-6)
    assert page["as_of"] != NOW


def test_page_as_of_falls_back_to_composed_at(monkeypatch) -> None:
    page = _compose_with_legs(
        monkeypatch, financial=integrated_answer._leg_shell("financial_facts")
    )
    surfaced = [item for item in page["legs"] if item["status"] in {"ok", "stale"}]
    assert surfaced == []
    assert page["composed_at"] == NOW
    assert page["as_of"] == NOW


def test_stale_boundary_is_stale_days(monkeypatch) -> None:
    assert integrated_answer.STALE_DAYS == 4
    exact = _surfaced_leg(
        "financial_facts",
        route=FINANCIAL_ROUTE,
        as_of=_shift(NOW, days=-integrated_answer.STALE_DAYS),
        payload={"request": {}},
    )
    page = _compose_with_legs(monkeypatch, financial=exact, publication=_page_stamp_leg())
    leg = _leg(page, "financial_facts")
    assert page["as_of"] == NOW
    assert leg["status"] == "ok"
    assert leg["degraded_reason"] is None

    one_second_older = _surfaced_leg(
        "financial_facts",
        route=FINANCIAL_ROUTE,
        as_of=_shift(_shift(NOW, days=-integrated_answer.STALE_DAYS), seconds=-1),
        payload={"request": {}},
    )
    page_older = _compose_with_legs(
        monkeypatch, financial=one_second_older, publication=_page_stamp_leg()
    )
    leg_older = _leg(page_older, "financial_facts")
    assert page_older["as_of"] == NOW
    assert leg_older["status"] == "stale"
    assert leg_older["degraded_reason"] == "older_than_page_stamp"


def test_older_than_page_stamp_inside_window(monkeypatch) -> None:
    inside = _surfaced_leg(
        "financial_facts", route=FINANCIAL_ROUTE, as_of=_shift(NOW, days=-2), payload={"request": {}}
    )
    page = _compose_with_legs(monkeypatch, financial=inside, publication=_page_stamp_leg())
    leg = _leg(page, "financial_facts")
    assert page["as_of"] == NOW
    # scenario sanity: older than the page stamp, inside the STALE_DAYS window
    assert _ts(NOW) - timedelta(days=integrated_answer.STALE_DAYS) <= _ts(inside["ref"]["as_of"]) < _ts(NOW)
    # today's contract: the sweep does NOT fire inside the window
    assert leg["status"] == "ok"
    assert leg["degraded_reason"] is None

    # contrast: beyond the window the sweep fires with the exact reason string
    beyond = _surfaced_leg(
        "financial_facts",
        route=FINANCIAL_ROUTE,
        as_of=_shift(NOW, days=-(integrated_answer.STALE_DAYS + 1)),
        payload={"request": {}},
    )
    page_beyond = _compose_with_legs(monkeypatch, financial=beyond, publication=_page_stamp_leg())
    leg_beyond = _leg(page_beyond, "financial_facts")
    assert leg_beyond["status"] == "stale"
    assert leg_beyond["degraded_reason"] == "older_than_page_stamp"


def test_event_workspace_leg_is_exempt_from_stale_sweep(monkeypatch) -> None:
    _absent_seams(monkeypatch)
    monkeypatch.setattr(integrated_answer, "_utc_now", lambda: NOW)
    monkeypatch.setattr(
        integrated_answer, "_leg_financial_facts", lambda _t, *_a, **_k: _surfaced_leg(
            "financial_facts", route=FINANCIAL_ROUTE, as_of=NOW, payload={"request": {}}
        )
    )
    monkeypatch.setattr(
        integrated_answer,
        "_event_result",
        lambda _t: {
            "available": True,
            "workspace": {
                "generated_at": "2020-01-01T00:00:00Z",
                "generation_id": "evt-gen-1",
                "fiscal_period": {},
                "lifecycle": {},
            },
        },
    )
    page = integrated_answer._compose_page("AAPL")
    event = _leg(page, "event_workspace")
    assert event["status"] == "ok"
    assert event["ref"]["as_of"] == "2020-01-01T00:00:00Z"
    assert event["degraded_reason"] is None
    assert _ts(event["ref"]["as_of"]) < _ts(NOW) - timedelta(days=integrated_answer.STALE_DAYS)
    assert page["as_of"] == NOW


def test_missing_owner_clock_fallbacks(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(integrated_answer, "_utc_now", lambda: NOW)

    # :418-421 earnings_expectation — capture refused, chip present: no owner clock
    monkeypatch.setattr(
        integrated_answer,
        "_k3e_source",
        lambda: (_ for _ in ()).throw(QueryRefusal("refused-in-test")),
    )
    monkeypatch.setattr(
        integrated_answer,
        "_expectation_chips",
        lambda _day: {"AAPL": {"schema": "expectation_chip.v0", "ticker": "AAPL"}},
    )
    earnings = integrated_answer._leg_earnings_expectation("AAPL", NOW)
    assert earnings["status"] == "stale"
    assert earnings["degraded_reason"] == "no_owner_clock"
    assert earnings["ref"]["as_of"] == NOW

    # :517-520 theme_tape — owner clock present but unparsable: injected clock
    monkeypatch.setattr(
        integrated_answer,
        "_theme_context",
        lambda: {
            "schema": "theme_context.v1",
            "as_of": "not-a-clock",
            "region": "us",
            "display_only": True,
            "leadership": [],
        },
    )
    tape = integrated_answer._leg_theme_tape()
    assert tape["status"] == "stale"
    assert tape["degraded_reason"] == "no_owner_clock"
    assert tape["ref"]["as_of"] == NOW

    # :587-590 company_theme_exposure — published generation, theme_state has no as_of
    contexts, ci_manifest = _company_tree(tmp_path / "ci-src")
    exposures, manifest = build_bundle(
        contexts,
        company_manifest=ci_manifest,
        membership=_membership(),
        crosswalk=_crosswalk(),
        theme_state=None,
        as_of="2026-02-02",
    )
    write_generation(tmp_path, exposures, manifest)
    monkeypatch.setenv("MACRO_CTE_DIR", str(tmp_path))
    exposure = integrated_answer._leg_company_theme_exposure("AAPL", NOW)
    assert exposure["status"] == "stale"
    assert exposure["degraded_reason"] == "no_owner_clock"
    assert exposure["ref"]["as_of"] == NOW


def test_financial_leg_clock_is_threaded_and_producer_derived(monkeypatch) -> None:
    from engine.fundamental_forensics import query_service

    monkeypatch.setattr(integrated_answer, "_utc_now", lambda: NOW)
    monkeypatch.setattr(integrated_answer, "_financial_provider", lambda: object())

    def _node(cell_id: str, *, recorded_at: str, accepted_at: str) -> dict:
        # Minimal cell dict mirroring MetricMatrix node serialization
        # (_unsigned_dict -> cell.to_dict -> "provenance": CellProvenance.to_dict(),
        # engine/fundamental_forensics/query.py). The composer reads none of the
        # provenance keys today — only result.sha256 and receipt.query_hash.
        return {
            "cell_id": cell_id,
            "provenance": {
                "source_snapshot_at": "2026-08-01T00:00:00Z",
                "recorded_cutoff_at": "2026-08-23T12:00:00Z",
                "accepted_at": accepted_at,
                "recorded_at": recorded_at,
            },
        }

    envelope = {
        "receipt": {
            "query_hash": "q" * 64,
            "nodes": [
                _node("cell-1", recorded_at="2026-08-23T12:00:00Z", accepted_at="2026-08-23T11:00:00Z"),
                _node("cell-2", recorded_at="2026-09-15T00:00:00Z", accepted_at="2026-09-14T00:00:00Z"),
            ],
        },
        "delivery": {},
    }
    result_body = json.dumps(
        envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    captured: dict[str, bytes] = {}

    def _fake_execute(*, body: bytes, provider: object):
        captured["body"] = body
        return query_service.FinancialQueryResult(
            body=result_body,
            sha256=hashlib.sha256(result_body).hexdigest(),
            envelope=envelope,
        )

    monkeypatch.setattr(query_service, "execute_financial_query", _fake_execute)

    leg = integrated_answer._leg_financial_facts("AAPL")

    assert leg["status"] == "ok"
    # (i) the request policy clock must be threaded from the composer clock
    request = json.loads(captured["body"])
    assert request["policy"]["recorded_at"] == NOW
    # (ii) the leg's source clock must be producer-derived:
    #      max per-node provenance.recorded_at (recorded_at -> accepted_at ->
    #      threaded request clock when the receipt has no nodes)
    assert leg["ref"]["as_of"] == "2026-09-15T00:00:00Z"
    assert leg["ref"]["owner_hash"] == hashlib.sha256(result_body).hexdigest()


def test_make_ref_shape_and_stable_content_hash() -> None:
    payload_a = {"request": {"b": 2, "a": 1}}
    ref_a = integrated_answer._make_ref(
        route=FINANCIAL_ROUTE, as_of=NOW, payload=payload_a, generation_id=None, owner_hash=None
    )
    assert set(ref_a) == {"route", "as_of", "generation_id", "owner_hash", "content_hash"}
    assert ref_a["generation_id"] is None
    assert ref_a["owner_hash"] is None
    assert ref_a["content_hash"] == integrated_answer._content_hash(payload_a)

    # equal payloads hash equal — key order must not matter
    ref_b = integrated_answer._make_ref(
        route=FINANCIAL_ROUTE, as_of=NOW, payload={"request": {"a": 1, "b": 2}}, generation_id=None, owner_hash=None
    )
    assert ref_b["content_hash"] == ref_a["content_hash"]

    # a changed payload changes content_hash
    ref_c = integrated_answer._make_ref(
        route=FINANCIAL_ROUTE, as_of=NOW, payload={"request": {"a": 1, "b": 3}}, generation_id=None, owner_hash=None
    )
    assert ref_c["content_hash"] != ref_a["content_hash"]

    # the digest covers the payload only — route/as_of/identity do not feed it
    ref_d = integrated_answer._make_ref(
        route="other", as_of="2020-01-01T00:00:00Z", payload=payload_a, generation_id="g", owner_hash="h"
    )
    assert ref_d["content_hash"] == ref_a["content_hash"]


# --- Cold-compose bound: blob-keyed k3e reuse -------------------------------------------------

K3E_OBSERVATION_COLUMNS = (
    "observation_id", "collection_session_id", "attempt_id", "provider",
    "provider_record_class", "provider_payload_hash", "ticker_compat",
    "metric", "horizon_label_raw", "observation_type", "value",
    "missingness_reason", "provider_observed_at", "system_observed_at",
)
K3E_ATTEMPT_COLUMNS = (
    "attempt_id", "collection_session_id", "provider", "ticker_compat",
    "attempted_at", "completed_at", "status", "response_payload_hash",
)


def _k3e_git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True, stderr=subprocess.STDOUT
    ).strip()


def _k3e_commit(repo: Path, message: str) -> str:
    _k3e_git(repo, "add", "-A")
    _k3e_git(repo, "commit", "-q", "-m", message)
    return _k3e_git(repo, "rev-parse", "HEAD")


def _k3e_write_input(repo: Path, path: str, columns: tuple[str, ...], tag: str) -> None:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{column: tag for column in columns}]).to_parquet(target, engine="pyarrow")


@pytest.fixture
def k3e_repo(tmp_path, monkeypatch) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _k3e_git(repo, "init", "-q", "-b", "main")
    _k3e_git(repo, "config", "user.name", "K3E Test")
    _k3e_git(repo, "config", "user.email", "k3e-test@example.invalid")
    _k3e_git(repo, "config", "commit.gpgsign", "false")
    _k3e_write_input(repo, OBSERVATIONS_PATH, K3E_OBSERVATION_COLUMNS, "first")
    _k3e_write_input(repo, ATTEMPTS_PATH, K3E_ATTEMPT_COLUMNS, "first")
    _k3e_commit(repo, "seed inputs")
    monkeypatch.setattr(integrated_answer, "REPO", repo)
    monkeypatch.setattr(integrated_answer, "_k3e_cached_rev", None)
    monkeypatch.setattr(integrated_answer, "_k3e_cached_bundle", None)
    return repo


def _count_full_loads(monkeypatch) -> list[str]:
    real = qk3e.load_frozen_source
    loads: list[str] = []

    def counted(repository, revision):
        loads.append(revision)
        return real(repository, revision)

    monkeypatch.setattr(qk3e, "load_frozen_source", counted)
    return loads


def test_k3e_source_reuses_rows_when_input_blobs_did_not_move(k3e_repo, monkeypatch) -> None:
    expected_loader = qk3e.load_frozen_source
    loads = _count_full_loads(monkeypatch)
    first = integrated_answer._k3e_source()
    assert len(loads) == 1

    (k3e_repo / "unrelated.txt").write_text("the checkout moved\n")
    moved = _k3e_commit(k3e_repo, "unrelated change")
    rebound = integrated_answer._k3e_source()

    assert len(loads) == 1
    assert rebound[0] is first[0] and rebound[1] is first[1]
    assert integrated_answer._k3e_cached_rev == moved
    # Exactly what a full load at the new revision returns, provenance included.
    assert rebound == expected_loader(k3e_repo, moved)
    assert rebound[2]["source_revision"] == moved


def test_k3e_source_reloads_when_an_input_blob_moves(k3e_repo, monkeypatch) -> None:
    expected_loader = qk3e.load_frozen_source
    loads = _count_full_loads(monkeypatch)
    first = integrated_answer._k3e_source()

    _k3e_write_input(k3e_repo, ATTEMPTS_PATH, K3E_ATTEMPT_COLUMNS, "second")
    moved = _k3e_commit(k3e_repo, "new attempts")
    reloaded = integrated_answer._k3e_source()

    assert loads[1:] == [moved]
    assert reloaded[1] != first[1]
    assert reloaded == expected_loader(k3e_repo, moved)


def test_k3e_source_refuses_like_the_full_load_and_keeps_the_cache(k3e_repo, monkeypatch) -> None:
    expected_loader = qk3e.load_frozen_source
    first = integrated_answer._k3e_source()
    first_rev = integrated_answer._k3e_cached_rev

    _k3e_git(k3e_repo, "rm", "-q", ATTEMPTS_PATH)
    moved = _k3e_commit(k3e_repo, "input withdrawn")
    with pytest.raises(QueryRefusal) as full_load:
        expected_loader(k3e_repo, moved)
    with pytest.raises(QueryRefusal) as composed:
        integrated_answer._k3e_source()

    assert composed.value.reason == full_load.value.reason
    assert integrated_answer._k3e_cached_rev == first_rev
    assert integrated_answer._k3e_cached_bundle is first


def test_rebind_declines_a_bundle_without_the_inputs(k3e_repo) -> None:
    head = _k3e_git(k3e_repo, "rev-parse", "HEAD")
    assert qk3e.rebind_frozen_source(k3e_repo, head, ([], [], {"inputs": {"other": "other"}})) is None


# --- Cold-compose bound: the overall leg deadline ---------------------------------------------

READ_LEGS = {
    "_leg_financial_facts": "financial_facts",
    "_leg_earnings_expectation": "earnings_expectation",
    "_leg_capital_structure": "capital_structure",
    "_leg_publication_seam": "publication_seam",
    "_leg_event_workspace": "event_workspace",
    "_leg_theme_tape": "theme_tape",
    "_leg_company_theme_exposure": "company_theme_exposure",
}
PAGE_LEG_ORDER = [*READ_LEGS.values(), "basket_labels", "theme_membership_file"]


def _stub_read_legs(monkeypatch, **overrides) -> None:
    """Every read leg answers instantly unless the test overrides it."""
    monkeypatch.setattr(integrated_answer, "_utc_now", lambda: NOW)
    for attr, leg_id in READ_LEGS.items():
        answer = overrides.get(attr)
        if answer is None:
            answer = lambda *_a, _leg_id=leg_id, **_k: _surfaced_leg(
                _leg_id, route=PUBLICATION_ROUTE, as_of=NOW, payload={"leg": _leg_id}
            )
        monkeypatch.setattr(integrated_answer, attr, answer)


def test_leg_past_the_deadline_comes_back_absent_and_the_page_still_answers(monkeypatch) -> None:
    release = threading.Event()

    def blocked(*_a, **_k):
        release.wait(timeout=30)
        return _surfaced_leg("financial_facts", route=FINANCIAL_ROUTE, as_of=NOW, payload={})

    _stub_read_legs(monkeypatch, _leg_financial_facts=blocked)
    monkeypatch.setattr(integrated_answer, "COMPOSE_DEADLINE_SECONDS", 0.2)
    try:
        page, entries = integrated_answer._compose_page_with_receipts("AAPL")
        # The compose returned while the leg was still blocked: nothing waited for it.
        assert not release.is_set()
    finally:
        release.set()

    late = _leg(page, "financial_facts")
    assert late["status"] == "absent"
    assert late["degraded_reason"] == integrated_answer.COMPOSE_DEADLINE_REASON
    assert late["ref"] is None and late["payload"] is None
    assert late["copy"] is not None
    assert [item["leg"] for item in page["legs"]] == PAGE_LEG_ORDER
    assert _leg(page, "publication_seam")["status"] == "ok"
    assert page["coverage_note"] is not None
    by_leg = {entry["leg"]: entry for entry in entries}
    assert by_leg["financial_facts"]["status"] == "NO_REF"
    assert by_leg["publication_seam"]["status"] != "NO_REF"


def test_saturated_pool_degrades_and_never_runs_the_cancelled_legs(monkeypatch) -> None:
    release = threading.Event()
    ran: list[str] = []

    def recorded(leg_id):
        def read(*_a, **_k):
            ran.append(leg_id)
            release.wait(timeout=30)
            return integrated_answer._leg_fixed_absent(leg_id, "released")

        return read

    pool = ThreadPoolExecutor(max_workers=1)
    _stub_read_legs(monkeypatch, **{attr: recorded(leg_id) for attr, leg_id in READ_LEGS.items()})
    monkeypatch.setattr(integrated_answer, "_leg_pool", pool)
    monkeypatch.setattr(integrated_answer, "COMPOSE_DEADLINE_SECONDS", 0.2)
    try:
        page = integrated_answer._compose_page("AAPL")
    finally:
        release.set()
        pool.shutdown(wait=True)

    assert ran == ["financial_facts"]
    for leg_id in READ_LEGS.values():
        assert _leg(page, leg_id)["degraded_reason"] == integrated_answer.COMPOSE_DEADLINE_REASON


def test_legs_run_concurrently_and_keep_page_order(monkeypatch) -> None:
    last_leg_ran = threading.Event()
    waited: list[bool] = []

    def first_leg(*_a, **_k):
        # Sequential composition could never see the last leg while the first is running.
        waited.append(last_leg_ran.wait(timeout=10))
        return _surfaced_leg("financial_facts", route=FINANCIAL_ROUTE, as_of=NOW, payload={})

    def last_leg(*_a, **_k):
        last_leg_ran.set()
        return _surfaced_leg("company_theme_exposure", route=PUBLICATION_ROUTE, as_of=NOW, payload={})

    _stub_read_legs(monkeypatch, _leg_financial_facts=first_leg, _leg_company_theme_exposure=last_leg)
    page = integrated_answer._compose_page("AAPL")

    assert waited == [True]
    assert [item["leg"] for item in page["legs"]] == PAGE_LEG_ORDER
    assert _leg(page, "financial_facts")["status"] == "ok"


def test_leg_exception_still_propagates(monkeypatch) -> None:
    def broken(*_a, **_k):
        raise ValueError("leg bug")

    _stub_read_legs(monkeypatch, _leg_capital_structure=broken)
    with pytest.raises(ValueError, match="leg bug"):
        integrated_answer._compose_page("AAPL")


def test_legs_see_the_request_context(monkeypatch) -> None:
    probe: contextvars.ContextVar[str | None] = contextvars.ContextVar("probe", default=None)
    seen: list[str | None] = []

    def reader(*_a, **_k):
        seen.append(probe.get())
        return _surfaced_leg("capital_structure", route=PUBLICATION_ROUTE, as_of=NOW, payload={})

    _stub_read_legs(monkeypatch, _leg_capital_structure=reader)
    token = probe.set("request")
    try:
        integrated_answer._compose_page("AAPL")
    finally:
        probe.reset(token)

    assert seen == ["request"]

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

This lane never sets ``MACRO_INTEGRATED_ANSWER_ENABLED`` — the flag-off 404 is
pinned in :func:`test_route_stays_off_when_flag_unset`, and every composition
test drives ``_compose_page`` or the ``_leg_*`` builders directly.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.integrated_answer as integrated_answer
from app.forensics import require_site_full_user
from app.integrated_answer import router as integrated_answer_router
from engine.company_theme_exposure.views import build_bundle, write_generation
from engine.k3e_expectation_surface import QueryRefusal
from tests.test_company_theme_exposure import _company_tree, _crosswalk, _membership

NOW = "2026-10-11T12:00:00Z"
FINANCIAL_ROUTE = "/api/forensics/v1/financial/query"
PUBLICATION_ROUTE = "/api/forensics/v1/attested-history/latest"

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

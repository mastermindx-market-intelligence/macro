"""N0 — the integrated answer's capital-structure context leg over the served state.

The leg replaces the held stub: it resolves the page ticker through the SAME
verified, published capital-structure state the
``/api/capital-structure/v1/issuers/{issuer_id}/state`` route serves, via that
route's own ``_state_view`` (acceptance A44: one calculation path, no second
reader).  It carries facts and explicit negative answers only — no amounts, no
probability, no score, no rank, no sizing, no entry and no Prophet authority
(acceptance A48).

Every case runs against the state-API suite's own fixtures (``pack``/``built``/
``served``/``client`` imported into this module's namespace): the artifacts are
a tmp generation, never the committed ``data/capital_structure`` files.

Fixture ticker geometry: the S-1 lifecycle fixture gives BOTH issuers the
ticker ``ABC`` (issuer B takes it over later), so the unmutated served
generation is the shared-ticker case.  The single-holder cases rewrite the
served projection copy the same way ``tests/test_capital_structure_api.py``
does (identity mutation + cache reset); the state binding keys on
``projection_generation_id``, not on projection bytes, so the served state
stays bound.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("fastapi", reason="capital structure API tests need fastapi")
pytest.importorskip("httpx", reason="FastAPI TestClient needs httpx")

from fastapi.testclient import TestClient  # noqa: E402

import app.integrated_answer as integrated_answer  # noqa: E402
from app import capital_structure as cs  # noqa: E402
from engine.capital_structure.registration_integration import REGISTRATION_FAMILY  # noqa: E402
from tests.test_capital_structure_state_api import (  # noqa: E402
    AS_OF,
    ISSUER_ONE,
    ISSUER_TWO,
    TICKER,
    built,
    client,
    pack,
    served,
)

NOW = "2026-10-16T00:00:00Z"  # within STALE_DAYS of the fixture's 2026-10-14 bundle clock
STATE_ROUTE = f"/api/capital-structure/v1/issuers/{{issuer_id}}/state"
RESOLVE_ROUTE = "/api/capital-structure/v1/issuers/resolve"

_FORBIDDEN_KEY_TOKENS = (
    "amount",
    "dollar",
    "price",
    "proceeds",
    "capacity",
    "probability",
    "score",
    "rank",
    "sizing",
    "entry",
    "prophet",
    "shares",
)


# ---------------------------------------------------------------------------
# Served-generation helpers
# ---------------------------------------------------------------------------


def _rewrite_projection(served, mutate) -> None:
    """Rewrite this test's served projection copy and re-read it from disk."""
    projection = served.projection
    mutate(projection)
    served.projection_path.write_text(json.dumps(projection), encoding="utf-8")
    cs._reset_cache()


def _serve_single_holder(served) -> None:
    """Leave ``ABC`` on issuer A only: issuer B's identity drops the ticker."""

    def _mutate(projection: dict[str, Any]) -> None:
        for record in projection["records"]:
            if record["issuer_id"] == ISSUER_TWO:
                record["identity"]["ticker"] = None
                record["identity"]["observed_tickers"] = []

    _rewrite_projection(served, _mutate)


def _state_record_of(bundle: dict[str, Any], issuer_id: str) -> dict[str, Any]:
    return next(
        row
        for row in bundle["issuers"]
        if str((row.get("request") or {}).get("issuer_id") or "") == issuer_id
    )


def _leg(ticker: str = "abc", composed_at: str = NOW) -> dict[str, Any]:
    return integrated_answer._leg_capital_structure(ticker, composed_at)


def _assert_absent(leg: dict[str, Any], degraded_reason: str) -> None:
    assert leg["leg"] == "capital_structure"
    assert leg["status"] == "absent"
    assert leg["degraded_reason"] == degraded_reason
    assert leg["payload"] is None
    assert leg["ref"] is None
    assert isinstance(leg["copy"], dict)
    assert leg["copy"]["en"]
    assert leg["copy"]["zh"]


def _page_leg(page: dict[str, Any], leg_id: str) -> dict[str, Any]:
    return next(item for item in page["legs"] if item["leg"] == leg_id)


# ---------------------------------------------------------------------------
# 1. ok — facts come straight from the served bundle
# ---------------------------------------------------------------------------


def test_ok_leg_carries_the_served_bundle_facts(served, client: TestClient) -> None:
    _serve_single_holder(served)
    state = client.get(STATE_ROUTE.format(issuer_id=ISSUER_ONE))
    assert state.status_code == 200
    state_body = state.json()
    bundle = served.bundle

    leg = _leg()
    assert leg["leg"] == "capital_structure"
    assert leg["status"] == "ok"
    assert leg["degraded_reason"] is None
    assert leg["copy"] is None
    payload = leg["payload"]
    assert payload["schema"] == "capital_structure.context_leg.v1"
    assert payload["issuer_id"] == ISSUER_ONE
    assert payload["company_id"] == "cik:0000000001"
    assert payload["identity"] == next(
        record["identity"]
        for record in served.projection["records"]
        if record["issuer_id"] == ISSUER_ONE
    )
    assert payload["state_id"] == _state_record_of(bundle, ISSUER_ONE)["state_id"]
    assert payload["generation_id"] == bundle["generation_id"]
    assert payload["projection_generation_id"] == bundle["projection_generation_id"]
    assert payload["as_of"] == bundle["as_of"] == AS_OF
    assert payload["horizons"] == bundle["horizons"]
    assert payload["unavailable"] == _state_record_of(bundle, ISSUER_ONE)["unavailable"]
    assert payload["capabilities_proven"] == _state_record_of(bundle, ISSUER_ONE)[
        "capabilities_proven"
    ]
    assert payload["receipt_id"] == _state_record_of(bundle, ISSUER_ONE)["receipt"]["receipt_id"]
    assert payload["evidence_route"] == STATE_ROUTE.format(issuer_id=ISSUER_ONE)

    family = state_body["families"][REGISTRATION_FAMILY]
    registration = payload["registration"]
    assert registration["coverage"] == family["coverage"]
    assert registration["family_unavailable"] == list(family.get("unavailable") or [])
    paths = cs._path_rows(family)
    assert registration["path_count"] == len(paths)
    assert [row["path_id"] for row in registration["paths"]] == [
        row["path_id"] for row in paths
    ]
    for row, path in zip(registration["paths"], paths, strict=True):
        origin = path.get("origin") or {}
        source_registration = path.get("registration") or {}
        assert row == {
            "path_id": path.get("path_id"),
            "form": origin.get("form"),
            "accession": origin.get("accession"),
            "sec_accepted_at": origin.get("sec_accepted_at"),
            "mastermind_available_at": origin.get("mastermind_available_at"),
            "observed_registration_state": path.get("observed_registration_state"),
            "registration_family": source_registration.get("registration_family"),
            "file_number": source_registration.get("file_number"),
        }

    ref = leg["ref"]
    assert ref["route"] == "capital_structure:published_state_bundle"
    assert ref["as_of"] == AS_OF
    assert ref["generation_id"] == str(bundle["generation_id"])
    assert ref["owner_hash"] == (family.get("provenance") or {}).get("artifact_sha256")
    assert ref["owner_hash"]
    assert re.fullmatch(r"[0-9a-f]{64}", ref["owner_hash"])
    assert ref["content_hash"] == integrated_answer._content_hash(payload)

    consumed = ref.consumed_receipt
    receipt = consumed["receipt"]
    assert receipt["bytes_sha256"] is None
    assert receipt["producer_generation_id"] == str(bundle["generation_id"])
    assert receipt["data_interval"] is None
    assert receipt["contract_watermark"] == {
        "contract": bundle["schema"],
        "watermark": AS_OF,
    }
    assert receipt["denominator"] == family["coverage"]
    assert receipt["consumer_version"] == integrated_answer.CONSUMER_RECEIPT_VERSION
    assert consumed["null_reasons"] == {
        "bytes_sha256": "NOT_READ_AT_CONSUME",
        "data_interval": "NOT_EXPOSED_BY_PRODUCER",
    }


# ---------------------------------------------------------------------------
# 2. A44 parity — the same verified state, through one resolution path
# ---------------------------------------------------------------------------


def test_leg_reads_the_exact_state_route_resolution_path(
    served, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _serve_single_holder(served)
    state = client.get(STATE_ROUTE.format(issuer_id=ISSUER_ONE))
    assert state.status_code == 200
    state_body = state.json()
    payload = _leg()["payload"]

    assert payload["state_id"] == _state_record_of(served.bundle, ISSUER_ONE)["state_id"]
    assert payload["generation_id"] == served.bundle["generation_id"]
    assert state_body["view"]["generation_id"] == served.bundle["generation_id"]
    assert payload["identity"] == state_body["identity"]
    assert payload["unavailable"] == state_body["unavailable"]
    assert payload["capabilities_proven"] == state_body["capabilities_proven"]
    assert payload["receipt_id"] == state_body["receipt"]["receipt_id"]
    assert payload["registration"]["coverage"] == state_body["families"][REGISTRATION_FAMILY][
        "coverage"
    ]
    assert [row["path_id"] for row in payload["registration"]["paths"]] == [
        row["path_id"]
        for row in cs._path_rows(state_body["families"][REGISTRATION_FAMILY])
    ]

    calls: list[tuple[Any, Any, Any, Any]] = []
    real_state_view = cs._state_view

    def _spy(issuer_id, mode, cutoff, clock):
        calls.append((issuer_id, mode, cutoff, clock))
        return real_state_view(issuer_id, mode, cutoff, clock)

    monkeypatch.setattr(cs, "_state_view", _spy)
    assert _leg()["payload"]["issuer_id"] == ISSUER_ONE
    assert calls == [(ISSUER_ONE, None, None, None)]


# ---------------------------------------------------------------------------
# 3. negative answers — typed, never guessed
# ---------------------------------------------------------------------------


def test_unknown_ticker_is_absent_ticker_not_covered(served) -> None:
    _assert_absent(_leg("ZZZZ"), "ticker_not_covered")


def test_malformed_ticker_is_absent_ticker_not_covered(served) -> None:
    _assert_absent(_leg("1BC"), "ticker_not_covered")
    _assert_absent(_leg("  "), "ticker_not_covered")


def test_shared_ticker_is_absent_ambiguous(served) -> None:
    # The fixture's own geometry: both projection records carry ABC.
    projection = served.projection
    holders = sorted(
        record["issuer_id"]
        for record in projection["records"]
        if "ABC" in {
            str(record["identity"].get("ticker") or "").upper(),
            *(str(value).upper() for value in record["identity"].get("observed_tickers") or []),
        }
    )
    assert holders == sorted([ISSUER_ONE, ISSUER_TWO])
    _assert_absent(_leg(TICKER), "ambiguous_ticker")


# ---------------------------------------------------------------------------
# 4. fail-closed
# ---------------------------------------------------------------------------


def test_missing_state_file_is_absent_state_unavailable(served, tmp_path: Path) -> None:
    _serve_single_holder(served)
    served.state_path.unlink()
    cs._reset_state_cache()
    _assert_absent(_leg(), "state_unavailable")


def test_contract_violation_from_the_state_path_is_absent_contract_invalid(
    served, monkeypatch: pytest.MonkeyPatch
) -> None:
    _serve_single_holder(served)

    def _violating(*_args: Any) -> Any:
        raise cs.ContractViolation("state: tampered")

    monkeypatch.setattr(cs, "_state_view", _violating)
    _assert_absent(_leg(), "contract_invalid")


def test_empty_published_coverage_records_a_not_applicable_denominator(
    served, monkeypatch: pytest.MonkeyPatch
) -> None:
    _serve_single_holder(served)
    real_state_view = cs._state_view

    def _empty_coverage(*args: Any) -> Any:
        return real_state_view(*args)._replace(coverage={})

    monkeypatch.setattr(cs, "_state_view", _empty_coverage)
    leg = _leg()
    assert leg["status"] == "ok"
    consumed = leg["ref"].consumed_receipt
    assert consumed["receipt"]["denominator"] is None
    assert consumed["null_reasons"]["denominator"] == "NOT_APPLICABLE"


def test_projection_state_generation_mismatch_is_absent_state_not_bound(
    served,
) -> None:
    _serve_single_holder(served)

    def _mutate(projection: dict[str, Any]) -> None:
        projection["generation_id"] = "projection:cs:" + "F" * 24

    _rewrite_projection(served, _mutate)
    _assert_absent(_leg(), "state_not_bound")


def test_issuer_absent_from_the_bundle_is_absent_issuer_not_covered(served) -> None:
    def _mutate(projection: dict[str, Any]) -> None:
        for record in projection["records"]:
            if record["issuer_id"] == ISSUER_ONE:
                record["identity"]["ticker"] = None
                record["identity"]["observed_tickers"] = []
            elif record["issuer_id"] == ISSUER_TWO:
                # A projection record the served state bundle does not carry.
                record["issuer_id"] = "sec:cik:0000000009"

    _rewrite_projection(served, _mutate)
    _assert_absent(_leg(TICKER), "issuer_not_covered_by_state")


# ---------------------------------------------------------------------------
# 5. authority (A48)
# ---------------------------------------------------------------------------


def test_leg_authority_is_the_published_context_only_authority(served) -> None:
    _serve_single_holder(served)
    payload = _leg()["payload"]
    assert payload["authority"] == dict(cs.AUTHORITY)
    assert payload["authority"]["is_context_only"] is True
    for key, value in payload["authority"].items():
        if key.endswith("_authority"):
            assert value is False, key


# ---------------------------------------------------------------------------
# 6. no amounts, no sizing vocabulary (A48)
# ---------------------------------------------------------------------------


def _walk_keys(node: object, *, allow_authority_exception: bool = False) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if allow_authority_exception and key == "authority":
                # The published AUTHORITY dict itself is the one allowed
                # exception: its own keys name the refused authorities.
                continue
            lowered = str(key).lower()
            for token in _FORBIDDEN_KEY_TOKENS:
                assert token not in lowered, (key, token)
            _walk_keys(value)
    elif isinstance(node, list):
        for item in node:
            _walk_keys(item)


def test_payload_keys_carry_no_amount_or_sizing_vocabulary(served) -> None:
    _serve_single_holder(served)
    payload = _leg()["payload"]
    _walk_keys(payload, allow_authority_exception=True)


# ---------------------------------------------------------------------------
# 7. resolve_issuer is unchanged by the helper extraction
# ---------------------------------------------------------------------------


def test_resolve_route_matches_the_pre_extraction_loop(served, client: TestClient) -> None:
    _serve_single_holder(served)
    projection = served.projection
    normalized = TICKER
    expected = []
    for record in sorted(projection["records"], key=lambda item: str(item["issuer_id"])):
        identity = record["identity"]
        tickers = {
            str(identity.get("ticker") or "").upper(),
            *(str(value).upper() for value in identity.get("observed_tickers") or []),
        }
        if normalized in tickers:
            expected.append(record)
    assert [record["issuer_id"] for record in expected] == [ISSUER_ONE]

    response = client.get(RESOLVE_ROUTE, params={"ticker": TICKER.lower()})
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == {"ticker": TICKER}
    assert body["issuer"]["issuer_id"] == expected[0]["issuer_id"]
    assert body["issuer"]["identity"] == expected[0]["identity"]


def test_resolve_route_keeps_the_typed_failures(served, client: TestClient) -> None:
    unknown = client.get(RESOLVE_ROUTE, params={"ticker": "ZZZZ"})
    assert unknown.status_code == 404
    assert unknown.json()["detail"] == "ticker not covered"

    ambiguous = client.get(RESOLVE_ROUTE, params={"ticker": TICKER})
    assert ambiguous.status_code == 409
    detail = ambiguous.json()["detail"]
    assert detail["code"] == "ambiguous_ticker"
    assert detail["ticker"] == TICKER
    assert {item["issuer_id"] for item in detail["matches"]} == {ISSUER_ONE, ISSUER_TWO}


def test_resolve_route_answers_from_observed_tickers_alone(served, client: TestClient) -> None:
    """A holder whose identity carries the ticker only as an observed ticker.

    This is the mutant pin for ``_ticker_matches``: dropping the
    ``observed_tickers`` side of the match must fail here exactly as it would
    have failed the pre-extraction loop.
    """

    def _mutate(projection: dict[str, Any]) -> None:
        for record in projection["records"]:
            if record["issuer_id"] == ISSUER_ONE:
                record["identity"]["ticker"] = None
            elif record["issuer_id"] == ISSUER_TWO:
                record["identity"]["ticker"] = None
                record["identity"]["observed_tickers"] = []

    _rewrite_projection(served, _mutate)
    response = client.get(RESOLVE_ROUTE, params={"ticker": TICKER})
    assert response.status_code == 200
    assert response.json()["issuer"]["issuer_id"] == ISSUER_ONE


# ---------------------------------------------------------------------------
# 8. the composed page carries the leg
# ---------------------------------------------------------------------------


def test_composed_page_carries_the_capital_structure_leg(
    served, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.test_integrated_answer_v0 import _patch_all_seams

    _serve_single_holder(served)
    real_leg = integrated_answer._leg_capital_structure
    _patch_all_seams(monkeypatch, ticker="ABC")
    monkeypatch.setattr(integrated_answer, "_leg_capital_structure", real_leg)
    monkeypatch.setattr(integrated_answer, "_utc_now", lambda: NOW)
    # Hold every page clock near the fixture bundle's 2026-10-14 owner clock so
    # the STALE_DAYS sweep cannot fire on the capital_structure leg.
    monkeypatch.setattr(
        integrated_answer,
        "_theme_context",
        lambda: {
            "schema": "theme_context.v1",
            "as_of": "2026-10-16",
            "region": "us",
            "display_only": True,
            "leadership": [],
        },
    )

    page, entries = integrated_answer._compose_page_with_receipts("ABC")
    order = [item["leg"] for item in page["legs"]]
    assert order.index("capital_structure") == 2
    leg = _page_leg(page, "capital_structure")
    assert leg["status"] == "ok"
    assert leg["payload"]["schema"] == "capital_structure.context_leg.v1"

    assert [entry["leg"] for entry in entries] == list(integrated_answer.RECEIPT_LEGS)
    entry = next(item for item in entries if item["leg"] == "capital_structure")
    assert entry["status"] == "RECORDED"
    assert entry["ref_content_hash"] == leg["ref"]["content_hash"]
    assert entry["receipt"]["producer_generation_id"] == str(served.bundle["generation_id"])
    assert entry["null_reasons"] == {
        "bytes_sha256": "NOT_READ_AT_CONSUME",
        "data_interval": "NOT_EXPOSED_BY_PRODUCER",
    }

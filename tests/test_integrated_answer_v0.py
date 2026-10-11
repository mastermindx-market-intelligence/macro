"""Package I v0 integrated-answer composer tests."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import app.forensics as forensics_mod
from app.forensics import _PRIVATE_HEADERS, require_site_full_user
from app.integrated_answer import router as integrated_answer_router
import app.integrated_answer as integrated_answer
from engine.company_theme_exposure.contracts import company_filename
from engine.company_theme_exposure.views import write_generation
from engine.k3e_expectation_surface import QueryRefusal
from tests.test_company_theme_exposure import _bundle

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "app" / "integrated_answer.py"
MAIN_PATH = ROOT / "app" / "main.py"

TOP_LEVEL_KEYS = frozenset({
    "schema",
    "ticker",
    "as_of",
    "composed_at",
    "display_only",
    "stance",
    "footer",
    "coverage_note",
    "legs",
})
LEG_KEYS = frozenset({"leg", "status", "ref", "payload", "degraded_reason", "copy"})
REF_KEYS = frozenset({"route", "as_of", "generation_id", "owner_hash", "content_hash"})
FORBIDDEN_COMPOSITE = frozenset({"score", "probability", "rank", "composite", "confidence"})
FORBIDDEN_SOURCE_SUBSTRINGS = (
    "to_parquet",
    "to_csv",
    "write_text",
    "write_bytes",
    "sqlite3",
    "json.dump(",
)


def _client(monkeypatch, *, user_override=None, flag_on: bool = True) -> TestClient:
    monkeypatch.delenv("MACRO_INTEGRATED_ANSWER_ENABLED", raising=False)
    if flag_on:
        monkeypatch.setenv("MACRO_INTEGRATED_ANSWER_ENABLED", "1")
    app = FastAPI()
    app.include_router(integrated_answer_router)
    if user_override is None:
        app.dependency_overrides[require_site_full_user] = lambda: {"id": "test-user"}
    else:
        app.dependency_overrides[require_site_full_user] = user_override
    return TestClient(app)


def _page(client: TestClient, ticker: str = "AAPL") -> dict:
    response = client.get(f"/api/integrated-answer/v1/{ticker}")
    assert response.status_code == 200
    return json.loads(response.content)


def _leg_by_id(page: dict, leg_id: str) -> dict:
    for item in page["legs"]:
        if item["leg"] == leg_id:
            return item
    raise KeyError(leg_id)


def _patch_all_seams(monkeypatch, *, ticker: str = "AAPL") -> None:
    def _fake_k3e(*_a, **_k):
        return {
            "schema": "k3e.declared_capture_inspection.v1",
            "normalized_baseline": {"value": None, "status": "absent"},
            "latest_captured_snapshot": {
                "derived_capture_available_at": "2026-09-01T12:00:00Z",
            },
            "query_identity": "a" * 64,
        }

    monkeypatch.setattr(integrated_answer, "_k3e_source", lambda: ([], [], {"source_revision": "0" * 40, "inputs": {}}))
    monkeypatch.setattr(integrated_answer, "_expectation_chips", lambda _day: {ticker: {"schema": "expectation_chip.v0", "ticker": ticker}})
    monkeypatch.setattr("engine.k3e_expectation_surface.inspect_expectation_surface", _fake_k3e)

    snap = "ffqsv2_" + ("a" * 64)
    monkeypatch.setattr(
        integrated_answer,
        "_receipt_identity",
        lambda: {
            "snapshot_id": snap,
            "base_snapshot_id": "ffqs_base",
            "query_hash": "b" * 64,
            "published_at": "2026-09-02T00:00:00Z",
        },
    )
    monkeypatch.setattr(
        integrated_answer,
        "_event_result",
        lambda _t: {
            "available": True,
            "workspace": {"generated_at": "2026-09-03T00:00:00Z", "fiscal_period": {}, "lifecycle": {}},
        },
    )
    monkeypatch.setattr(
        integrated_answer,
        "_theme_context",
        lambda: {
            "schema": "theme_context.v1",
            "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "region": "us",
            "display_only": True,
            "leadership": [],
        },
    )
    monkeypatch.setattr(integrated_answer, "_leg_financial_facts", lambda _t: integrated_answer._leg_shell("financial_facts") | {
        "status": "ok",
        "payload": {"request": {}, "query_hash": "c" * 64, "response_sha256": "d" * 64, "replay_route": "/x"},
        "ref": {
            "route": "/api/forensics/v1/financial/query",
            "as_of": "2026-08-23T12:00:00Z",
            "generation_id": None,
            "owner_hash": "d" * 64,
            "content_hash": hashlib.sha256(
                json.dumps(
                    {"request": {}, "query_hash": "c" * 64, "response_sha256": "d" * 64, "replay_route": "/x"},
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ).encode()
            ).hexdigest(),
        },
    })


def test_flag_off_returns_404_before_entitlement(monkeypatch) -> None:
    def _boom():
        raise HTTPException(status_code=401, detail="nope")

    client = _client(monkeypatch, user_override=_boom, flag_on=False)
    response = client.get("/api/integrated-answer/v1/AAPL")
    assert response.status_code == 404


def test_unentitled_401_and_403(monkeypatch) -> None:
    for status in (401, 403):
        def _raise(_status=status):
            raise HTTPException(status_code=_status, detail="blocked")

        client = _client(monkeypatch, user_override=_raise)
        response = client.get("/api/integrated-answer/v1/AAPL")
        assert response.status_code == status


def test_trace_refs_on_every_surfaced_leg(monkeypatch) -> None:
    _patch_all_seams(monkeypatch)
    page = _page(_client(monkeypatch))
    for leg in page["legs"]:
        if leg["status"] in {"ok", "stale"}:
            ref = leg["ref"]
            assert ref and ref.get("route") and ref.get("as_of")
            assert re.fullmatch(r"[0-9a-f]{64}", ref["content_hash"])
            assert ref["content_hash"] == integrated_answer._content_hash(leg["payload"])
        else:
            assert leg["ref"] is None
            assert leg["payload"] is None


def test_known_at_vs_decision_at(monkeypatch) -> None:
    _patch_all_seams(monkeypatch)
    page = _page(_client(monkeypatch))
    composed = page["composed_at"]
    surfaced = [leg for leg in page["legs"] if leg["status"] in {"ok", "stale"}]
    assert surfaced
    max_as_of = max(leg["ref"]["as_of"] for leg in surfaced)
    assert page["as_of"] == max_as_of
    for leg in page["legs"]:
        if leg.get("ref"):
            assert leg["ref"]["as_of"] != composed or leg["degraded_reason"] == "no_owner_clock"
    assert page["composed_at"] == composed


def test_later_correction_under_earlier_cutoff(monkeypatch) -> None:
    seen: list[str] = []

    def _k3e(*_a, as_of=None, composed_at=None, **_k):
        seen.append(as_of)
        return {
            "latest_captured_snapshot": {"derived_capture_available_at": "2099-01-01T00:00:00Z"},
            "normalized_baseline": {"value": None},
        }

    monkeypatch.setattr("engine.k3e_expectation_surface.inspect_expectation_surface", _k3e)
    monkeypatch.setattr(integrated_answer, "_k3e_source", lambda: ([], [], {"source_revision": "0" * 40, "inputs": {}}))
    monkeypatch.setattr(integrated_answer, "_expectation_chips", lambda _d: {})
    monkeypatch.setattr(integrated_answer, "_receipt_identity", lambda: (_ for _ in ()).throw(RuntimeError()))
    monkeypatch.setattr(integrated_answer, "_event_result", lambda _t: {"available": False})
    monkeypatch.setattr(integrated_answer, "_theme_context", lambda: None)
    monkeypatch.setattr(integrated_answer, "_cte_dir", lambda: Path("/nonexistent"))
    monkeypatch.setattr(integrated_answer, "_leg_financial_facts", lambda _t: integrated_answer._leg_shell("financial_facts"))
    page = _page(_client(monkeypatch))
    leg = _leg_by_id(page, "earnings_expectation")
    assert leg["status"] in {"ok", "stale"}
    assert seen and seen[0] == page["composed_at"]


def test_unit_period_mismatch_never_fused(monkeypatch) -> None:
    _patch_all_seams(monkeypatch)
    page = _page(_client(monkeypatch))
    h01 = _leg_by_id(page, "financial_facts")
    h04 = _leg_by_id(page, "earnings_expectation")
    assert h01["payload"] is not None and h04["payload"] is not None
    _scan_forbidden_composite(page)


def test_missing_or_withdrawn_source(monkeypatch) -> None:
    def _refuse(*_a, **_k):
        raise QueryRefusal("SOURCE_WITHDRAWN")

    monkeypatch.setattr("engine.k3e_expectation_surface.inspect_expectation_surface", _refuse)
    monkeypatch.setattr(integrated_answer, "_k3e_source", lambda: ([], [], {"source_revision": "0" * 40, "inputs": {}}))
    monkeypatch.setattr(integrated_answer, "_expectation_chips", lambda _d: {})
    monkeypatch.setattr(integrated_answer, "_receipt_identity", lambda: {
        "snapshot_id": "ffqsv2_" + ("e" * 64),
        "base_snapshot_id": "ffqs_base",
        "query_hash": "e" * 64,
        "published_at": "2026-09-02T00:00:00Z",
    })
    monkeypatch.setattr(integrated_answer, "_event_result", lambda _t: {"available": False, "note": "n/a"})
    monkeypatch.setattr(integrated_answer, "_theme_context", lambda: None)
    monkeypatch.setattr(integrated_answer, "_leg_financial_facts", lambda _t: integrated_answer._leg_shell("financial_facts") | {"status": "absent", "degraded_reason": "x"})
    page = _page(_client(monkeypatch))
    leg = _leg_by_id(page, "earnings_expectation")
    assert leg["status"] == "absent"
    assert "k3e:SOURCE_WITHDRAWN" in leg["degraded_reason"]
    assert "chip:" in leg["degraded_reason"]


def _write_cte_root(tmp_path: Path) -> str:
    exposures, manifest = _bundle(tmp_path / "ci-src")
    write_generation(tmp_path, exposures, manifest)
    return manifest["generation_id"]


def test_incompatible_generations(monkeypatch, tmp_path) -> None:
    gid = _write_cte_root(tmp_path)
    rel = company_filename("AAPL")
    # gid mismatch
    root1 = tmp_path / "mismatch_gid"
    exposures, manifest = _bundle(root1 / "ci-src")
    write_generation(root1, exposures, manifest)
    imm = json.loads((root1 / "generations" / gid / "manifest.json").read_text())
    imm["generation_id"] = "deadbeefdeadbeefdeadbeefdeadbeef"
    (root1 / "generations" / gid / "manifest.json").write_text(json.dumps(imm))

    # hash mismatch
    root2 = tmp_path / "hash_mismatch"
    exposures2, manifest2 = _bundle(root2 / "ci-src")
    write_generation(root2, exposures2, manifest2)
    gid2 = manifest2["generation_id"]
    rel_path = root2 / "generations" / gid2 / rel
    rel_path.write_bytes(rel_path.read_bytes() + b" ")

    cases = [
        (root1, "generation_mismatch"),
        (root2, "generation_mismatch"),
        (tmp_path, None),
    ]
    for root, expected_reason in cases:
        monkeypatch.setenv("MACRO_CTE_DIR", str(root))
        monkeypatch.setattr(integrated_answer, "_k3e_source", lambda: (_ for _ in ()).throw(QueryRefusal("x")))
        monkeypatch.setattr(integrated_answer, "_expectation_chips", lambda _d: {})
        monkeypatch.setattr(integrated_answer, "_receipt_identity", lambda: (_ for _ in ()).throw(RuntimeError("off")))
        monkeypatch.setattr(integrated_answer, "_event_result", lambda _t: {"available": False})
        monkeypatch.setattr(integrated_answer, "_theme_context", lambda: None)
        monkeypatch.setattr(integrated_answer, "_leg_financial_facts", lambda _t: integrated_answer._leg_shell("financial_facts"))
        page = _page(_client(monkeypatch))
        leg = _leg_by_id(page, "company_theme_exposure")
        if expected_reason:
            assert leg["status"] == "absent"
            assert leg["degraded_reason"] == expected_reason
        else:
            assert leg["status"] == "ok"
            assert leg["ref"]["generation_id"] == gid
            assert re.fullmatch(r"[0-9a-f]{64}", leg["ref"]["owner_hash"] or "")


def test_raw_capture_vs_normalized_baseline(monkeypatch) -> None:
    capture = {
        "normalized_baseline": {"value": None, "status": "absent"},
        "latest_captured_snapshot": {"derived_capture_available_at": "2026-09-01T00:00:00Z"},
    }
    chip = {"schema": "chip.only", "ticker": "AAPL", "label": "separate"}

    monkeypatch.setattr(
        "engine.k3e_expectation_surface.inspect_expectation_surface",
        lambda *_a, **_k: capture,
    )
    monkeypatch.setattr(integrated_answer, "_k3e_source", lambda: ([], [], {"source_revision": "0" * 40, "inputs": {}}))
    monkeypatch.setattr(integrated_answer, "_expectation_chips", lambda _d: {"AAPL": chip})
    monkeypatch.setattr(integrated_answer, "_receipt_identity", lambda: (_ for _ in ()).throw(RuntimeError()))
    monkeypatch.setattr(integrated_answer, "_event_result", lambda _t: {"available": False})
    monkeypatch.setattr(integrated_answer, "_theme_context", lambda: None)
    monkeypatch.setattr(integrated_answer, "_leg_financial_facts", lambda _t: integrated_answer._leg_shell("financial_facts"))
    page = _page(_client(monkeypatch))
    leg = _leg_by_id(page, "earnings_expectation")
    assert leg["payload"]["capture_inspection"]["normalized_baseline"]["value"] is None
    assert leg["payload"]["expectation_chip"] == chip
    assert "normalized_baseline" not in (leg["payload"]["expectation_chip"] or {})


def test_unavailable_financial_component(monkeypatch) -> None:
    from engine.fundamental_forensics.query_service import (
        FinancialQueryAdmissionError,
        FinancialQueryUnavailableError,
    )

    monkeypatch.setattr(integrated_answer, "_k3e_source", lambda: (_ for _ in ()).throw(QueryRefusal("x")))
    monkeypatch.setattr(integrated_answer, "_expectation_chips", lambda _d: {})
    monkeypatch.setattr(integrated_answer, "_receipt_identity", lambda: (_ for _ in ()).throw(RuntimeError()))
    monkeypatch.setattr(integrated_answer, "_event_result", lambda _t: {"available": False})
    monkeypatch.setattr(integrated_answer, "_theme_context", lambda: None)

    page_nv = _page(_client(monkeypatch), "NVDA")
    leg = _leg_by_id(page_nv, "financial_facts")
    assert leg["status"] == "absent"
    assert leg["degraded_reason"] == "not_covered:golden_corpus_is_aapl_only"
    assert leg["copy"]["en"].startswith("Financial detail isn't available")

    def _unavail(*_a, **_k):
        raise FinancialQueryUnavailableError()

    monkeypatch.setattr("engine.fundamental_forensics.query_service.execute_financial_query", _unavail)
    page = _page(_client(monkeypatch), "AAPL")
    leg = _leg_by_id(page, "financial_facts")
    assert leg["status"] == "absent"
    assert leg["degraded_reason"].startswith("unavailable:")

    def _refuse(*_a, **_k):
        raise FinancialQueryAdmissionError(422, "bad")

    monkeypatch.setattr("engine.fundamental_forensics.query_service.execute_financial_query", _refuse)
    page = _page(_client(monkeypatch), "AAPL")
    leg = _leg_by_id(page, "financial_facts")
    assert leg["status"] == "refused"
    assert leg["degraded_reason"] == "admission:422"


def _deep_keys(obj, prefix=""):
    if isinstance(obj, dict):
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else key
            yield path, key
            yield from _deep_keys(value, path)
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from _deep_keys(value, f"{prefix}[{index}]")


def test_private_public_leakage(monkeypatch) -> None:
    _patch_all_seams(monkeypatch)
    client = _client(monkeypatch)
    response = client.get("/api/integrated-answer/v1/AAPL")
    for name, value in _PRIVATE_HEADERS.items():
        assert response.headers.get(name) == value
    body = response.text
    assert "FF_ATTESTED" not in body
    page = json.loads(body)
    pub = _leg_by_id(page, "publication_seam")
    if pub["payload"]:
        assert set(pub["payload"]) == {"snapshot_id", "base_snapshot_id", "query_hash", "published_at"}
    event = _leg_by_id(page, "event_workspace")
    if event["payload"]:
        for path, key in _deep_keys(event["payload"]):
            assert "receipt" not in key.lower()


def test_real_golden_h01_aapl(monkeypatch) -> None:
    monkeypatch.setenv("MACRO_INTEGRATED_ANSWER_ENABLED", "1")
    monkeypatch.setattr(forensics_mod, "REPO", ROOT)
    monkeypatch.setattr(integrated_answer, "_k3e_source", lambda: (_ for _ in ()).throw(QueryRefusal("x")))
    monkeypatch.setattr(integrated_answer, "_expectation_chips", lambda _d: {})
    monkeypatch.setattr(integrated_answer, "_receipt_identity", lambda: (_ for _ in ()).throw(RuntimeError()))
    monkeypatch.setattr(integrated_answer, "_event_result", lambda _t: {"available": False})
    monkeypatch.setattr(integrated_answer, "_theme_context", lambda: None)
    monkeypatch.setattr(integrated_answer, "_cte_dir", lambda: Path("/nonexistent"))
    app = FastAPI()
    app.include_router(integrated_answer_router)
    app.dependency_overrides[require_site_full_user] = lambda: {"id": "u"}
    client = TestClient(app)
    page = _page(client, "AAPL")
    leg = _leg_by_id(page, "financial_facts")
    assert leg["status"] == "ok"
    assert leg["ref"]["owner_hash"] and re.fullmatch(r"[0-9a-f]{64}", leg["ref"]["owner_hash"])
    assert leg["payload"]["query_hash"]
    assert leg["ref"]["as_of"] == "2026-08-23T12:00:00Z"


def test_stale_vs_page_stamp(monkeypatch) -> None:
    monkeypatch.setattr(forensics_mod, "REPO", ROOT)
    monkeypatch.setattr(
        integrated_answer,
        "_theme_context",
        lambda: {
            "schema": "theme_context.v1",
            "as_of": date.today().isoformat(),
            "region": "us",
            "display_only": True,
            "leadership": [],
        },
    )
    monkeypatch.setattr(integrated_answer, "_k3e_source", lambda: (_ for _ in ()).throw(QueryRefusal("x")))
    monkeypatch.setattr(integrated_answer, "_expectation_chips", lambda _d: {})
    monkeypatch.setattr(integrated_answer, "_receipt_identity", lambda: (_ for _ in ()).throw(RuntimeError()))
    monkeypatch.setattr(integrated_answer, "_event_result", lambda _t: {"available": False})
    monkeypatch.setattr(integrated_answer, "_cte_dir", lambda: Path("/nonexistent"))
    page = _page(_client(monkeypatch), "AAPL")
    h01 = _leg_by_id(page, "financial_facts")
    assert h01["status"] == "stale"
    assert h01["degraded_reason"] == "older_than_page_stamp"
    assert h01["payload"] is not None
    event = _leg_by_id(page, "event_workspace")
    assert event["status"] != "stale"


def test_h05_held_and_fixed_absent_legs(monkeypatch) -> None:
    monkeypatch.setattr(integrated_answer, "_k3e_source", lambda: (_ for _ in ()).throw(QueryRefusal("x")))
    monkeypatch.setattr(integrated_answer, "_expectation_chips", lambda _d: {})
    monkeypatch.setattr(integrated_answer, "_receipt_identity", lambda: (_ for _ in ()).throw(RuntimeError()))
    monkeypatch.setattr(integrated_answer, "_event_result", lambda _t: {"available": False})
    monkeypatch.setattr(integrated_answer, "_theme_context", lambda: None)
    monkeypatch.setattr(integrated_answer, "_cte_dir", lambda: Path("/nonexistent"))
    page = _page(_client(monkeypatch), "AAPL")
    cs = _leg_by_id(page, "capital_structure")
    assert cs["status"] == "held_unavailable"
    assert "W4/W6" in cs["degraded_reason"]
    for leg_id in ("basket_labels", "theme_membership_file"):
        leg = _leg_by_id(page, leg_id)
        assert leg["status"] == "absent"
        assert "I-R2" in leg["degraded_reason"]
    assert page["coverage_note"] is not None


def _scan_forbidden_composite(page: dict) -> None:
    for key in page:
        if key != "legs":
            assert key not in FORBIDDEN_COMPOSITE
            if key != "legs" and isinstance(page[key], (int, float)) and not isinstance(page[key], bool):
                raise AssertionError(f"top-level number {key}")
    for leg in page["legs"]:
        _walk_payload(leg.get("payload"))


def _walk_payload(node) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            assert key not in FORBIDDEN_COMPOSITE
            _walk_payload(value)
    elif isinstance(node, list):
        for item in node:
            _walk_payload(item)


def test_no_persistence_and_closed_shape(monkeypatch) -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    for token in FORBIDDEN_SOURCE_SUBSTRINGS:
        assert token not in source
    assert not re.search(r'open\([^)]*["\'][wax]', source)
    _patch_all_seams(monkeypatch)
    page = _page(_client(monkeypatch))
    assert set(page) == TOP_LEVEL_KEYS
    for leg in page["legs"]:
        assert set(leg) == LEG_KEYS
        if leg["ref"]:
            assert set(leg["ref"]) == REF_KEYS
    _scan_forbidden_composite(page)


def test_invalid_ticker_400(monkeypatch) -> None:
    client = _client(monkeypatch)
    response = client.get("/api/integrated-answer/v1/not a ticker")
    assert response.status_code == 400


def test_main_include_block_present() -> None:
    text = MAIN_PATH.read_text(encoding="utf-8")
    assert "from app.integrated_answer import router as integrated_answer_router" in text
    idx = text.index("from app.integrated_answer import router as integrated_answer_router")
    assert "try:" in text[max(0, idx - 200) : idx]


def test_macro_api_unit_enables_integrated_answer_exactly_once() -> None:
    text = (ROOT / "app" / "deploy" / "macro-api.service").read_text(encoding="utf-8")
    lines = [line.strip() for line in text.splitlines()]
    assert lines.count("Environment=MACRO_INTEGRATED_ANSWER_ENABLED=1") == 1
    service_idx = lines.index("[Service]")
    flag_idx = lines.index("Environment=MACRO_INTEGRATED_ANSWER_ENABLED=1")
    assert service_idx < flag_idx
    next_section_idx = next(
        (i for i in range(service_idx + 1, len(lines)) if lines[i].startswith("[")),
        len(lines),
    )
    assert flag_idx < next_section_idx
    for line in lines:
        if "MACRO_INTEGRATED_ANSWER_ENABLED" not in line:
            continue
        assert line == "Environment=MACRO_INTEGRATED_ANSWER_ENABLED=1"

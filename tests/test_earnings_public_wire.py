from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re

import pytest
import yaml

from engine.earnings_narrative.extract import build_evidence_pair
from engine.earnings_narrative.generation import EvidencePair, write_generation
from engine.earnings_narrative.public_wire import (
    PublicWireContractError,
    build_public_wire_manifest,
    compile_public_wire_article,
    verify_public_wire_article,
    verify_public_wire_manifest,
)
from engine.earnings_narrative.context_packets import (
    CONTEXT_MANIFEST_SCHEMA,
    MAX_CONTEXT_FACTS,
    WEEKLY_INTELLIGENCE_SCHEMA,
    EarningsContextContractError,
    build_context_manifest,
    build_context_generation,
    build_context_packet,
    build_weekly_intelligence,
    canonical_json_bytes as context_json_bytes,
    select_public_facts,
    validate_context_packet,
    validate_context_manifest,
    validate_weekly_intelligence,
)
from engine.neuralweb.earnings_context_reader import read_earnings_evidence
from engine.earnings_narrative.story_store import write_story_packet_generation
from engine.earnings_transcript_intake import canonical_body_sha256
from scripts import build_earnings_public_wire as wire_builder
from scripts.build_earnings_public_wire import (
    DEFAULT_SOURCE_BASE,
    MAX_MANIFEST_BYTES,
    ROUTE_CATALOG_FILENAME,
    PublicWireBuildError,
    _view_article,
    build,
    build_company_alignment,
    fetch_current_publication,
    publish_public_wire,
)


def _body() -> dict:
    return {
        "schema": "mastermind.tx/v1",
        "ticker": "AAPL",
        "id": "2026Q1",
        "period": "Q1 FY2026",
        "date": "2026-01-30",
        "title": "AAPL earnings call",
        "segments": [
            {
                "speaker": "Chief Executive Officer",
                "role": "executive",
                "text": "Revenue grew 12% to 120 million, while gross margin reached 45%.",
            },
            {
                "speaker": "Chief Financial Officer",
                "role": "executive",
                "text": "For the full year, we expect revenue of 500 million and an operating margin of 20%.",
            },
            {
                "speaker": "Chief Executive Officer",
                "role": "executive",
                "text": "We will invest 50 million in capacity and continue our share repurchase program.",
            },
            {
                "speaker": "Research Analyst",
                "role": "analyst",
                "text": "Can you discuss customer demand and the 10% slowdown in Europe?",
            },
            {
                "speaker": "Chief Financial Officer",
                "role": "executive",
                "text": "Demand remains strong, but supply constraints could pressure margins by 200 bps.",
            },
        ],
    }


def _story_packet(tmp_path: Path) -> tuple[dict, dict, bytes, bytes]:
    body = _body()
    body_sha = canonical_body_sha256(body)
    index = {
        "schema": "mastermind.tx-index/v1",
        "generated_at": "2026-02-01T00:00:00Z",
        "symbols": {"AAPL": ["2026Q1"]},
        "revisions": {"AAPL/2026Q1": body_sha},
        "dates": {"AAPL/2026Q1": "2026-01-30"},
        "body_count": 1,
        "symbol_count": 1,
    }
    fact_pack, claim_graph = build_evidence_pair(
        body,
        index_payload=index,
        indexed_body_sha256=body_sha,
        index_generated_at=index["generated_at"],
    )
    evidence = tmp_path / "evidence"
    write_generation(
        evidence,
        [EvidencePair(fact_pack=fact_pack, claim_graph=claim_graph, transcript=body)],
        coverage={
            "selection_policy": "explicit_input",
            "batch_limit": 1,
            "historical_completeness": False,
            "index_body_count": 1,
            "index_generated_at": index["generated_at"],
        },
    )
    store = tmp_path / "story-packets"
    _generation, manifest = write_story_packet_generation(store, evidence)
    manifest_raw = (store / "manifest.json").read_bytes()
    entry = manifest["packets"]["AAPL/2026Q1"]
    packet_raw = (store / entry["object_key"]).read_bytes()
    return json.loads(packet_raw), manifest, manifest_raw, packet_raw


def _story_generation(
    tmp_path: Path,
    specs: list[tuple[str, str, str]],
    *,
    generated_at: str,
) -> tuple[dict, bytes, dict[str, bytes], dict]:
    symbols: dict[str, list[str]] = {}
    revisions: dict[str, str] = {}
    dates: dict[str, str] = {}
    pairs: list[EvidencePair] = []
    for ticker, transcript_id, call_date in specs:
        body = deepcopy(_body())
        body.update({
            "ticker": ticker,
            "id": transcript_id,
            "period": transcript_id,
            "date": call_date,
            "title": f"{ticker} earnings call",
        })
        body_sha = canonical_body_sha256(body)
        key = f"{ticker}/{transcript_id}"
        symbols.setdefault(ticker, []).append(transcript_id)
        revisions[key] = body_sha
        dates[key] = call_date
        index = {
            "schema": "mastermind.tx-index/v1",
            "generated_at": generated_at,
            "symbols": symbols,
            "revisions": revisions,
            "dates": dates,
            "body_count": len(revisions),
            "symbol_count": len(symbols),
        }
        fact_pack, claim_graph = build_evidence_pair(
            body,
            index_payload=index,
            indexed_body_sha256=body_sha,
            index_generated_at=generated_at,
        )
        pairs.append(EvidencePair(fact_pack=fact_pack, claim_graph=claim_graph, transcript=body))

    evidence = tmp_path / "evidence"
    write_generation(
        evidence,
        pairs,
        coverage={
            "selection_policy": "explicit_input",
            "batch_limit": len(pairs),
            "historical_completeness": False,
            "index_body_count": len(pairs),
            "index_generated_at": generated_at,
        },
    )
    store = tmp_path / "story-packets"
    _generation, manifest = write_story_packet_generation(store, evidence)
    raw = (store / "manifest.json").read_bytes()
    packets = {
        key: (store / entry["object_key"]).read_bytes()
        for key, entry in manifest["packets"].items()
    }
    transcript_index = {
        "schema": "mastermind.tx-index/v1",
        "generated_at": generated_at,
        "symbols": {ticker: sorted(ids) for ticker, ids in symbols.items()},
        "revisions": revisions,
        "dates": dates,
        "body_count": len(revisions),
        "symbol_count": len(symbols),
    }
    return manifest, raw, packets, transcript_index


def _story_generation_from_bodies(
    evidence_root: Path,
    bodies: list[dict],
    *,
    generated_at: str,
    store: Path,
) -> tuple[dict, bytes, dict[str, bytes], dict]:
    symbols: dict[str, list[str]] = {}
    revisions: dict[str, str] = {}
    dates: dict[str, str] = {}
    pairs: list[EvidencePair] = []
    for body in bodies:
        ticker = str(body["ticker"])
        transcript_id = str(body["id"])
        call_date = str(body["date"])
        body_sha = canonical_body_sha256(body)
        key = f"{ticker}/{transcript_id}"
        symbols.setdefault(ticker, []).append(transcript_id)
        revisions[key] = body_sha
        dates[key] = call_date
        index = {
            "schema": "mastermind.tx-index/v1",
            "generated_at": generated_at,
            "symbols": {symbol: sorted(ids) for symbol, ids in symbols.items()},
            "revisions": dict(revisions),
            "dates": dict(dates),
            "body_count": len(revisions),
            "symbol_count": len(symbols),
        }
        fact_pack, claim_graph = build_evidence_pair(
            body,
            index_payload=index,
            indexed_body_sha256=body_sha,
            index_generated_at=generated_at,
        )
        pairs.append(EvidencePair(fact_pack=fact_pack, claim_graph=claim_graph, transcript=body))

    write_generation(
        evidence_root,
        pairs,
        coverage={
            "selection_policy": "explicit_input",
            "batch_limit": len(pairs),
            "historical_completeness": False,
            "index_body_count": len(pairs),
            "index_generated_at": generated_at,
        },
    )
    _generation, manifest = write_story_packet_generation(store, evidence_root)
    raw = (store / "manifest.json").read_bytes()
    packets = {
        key: (store / entry["object_key"]).read_bytes()
        for key, entry in manifest["packets"].items()
    }
    transcript_index = {
        "schema": "mastermind.tx-index/v1",
        "generated_at": generated_at,
        "symbols": {ticker: sorted(ids) for ticker, ids in symbols.items()},
        "revisions": revisions,
        "dates": dates,
        "body_count": len(revisions),
        "symbol_count": len(symbols),
    }
    return manifest, raw, packets, transcript_index


def _canonical_test_json(payload: object) -> bytes:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8") + b"\n"


def _generation_remote(
    manifest: dict,
    raw: bytes,
    packets: dict[str, bytes],
    *,
    include_marker: bool,
) -> dict[str, bytes]:
    remote = {
        f"{DEFAULT_SOURCE_BASE}/earnings_story_packets/generations/{manifest['generation_id']}/manifest.json": raw,
    }
    if include_marker:
        remote[f"{DEFAULT_SOURCE_BASE}/earnings_story_packets/manifest.json"] = raw
    for key, packet_raw in packets.items():
        object_key = manifest["packets"][key]["object_key"]
        remote[f"{DEFAULT_SOURCE_BASE}/earnings_story_packets/{object_key}"] = packet_raw
    return remote


def _article(tmp_path: Path) -> tuple[dict, dict, bytes, bytes]:
    packet, manifest, manifest_raw, packet_raw = _story_packet(tmp_path)
    entry = manifest["packets"]["AAPL/2026Q1"]
    receipt = manifest["files"][entry["object_key"]]
    article = compile_public_wire_article(
        packet,
        policy_snapshot=manifest["policy"]["snapshot"],
        generation_id=manifest["generation_id"],
        object_key=entry["object_key"],
        object_sha256=receipt["sha256"],
        object_bytes=receipt["bytes"],
    )
    return article, manifest, manifest_raw, packet_raw


def test_http_fetch_retries_transient_tls_failure_within_the_same_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = f"{DEFAULT_SOURCE_BASE}/earnings_story_packets/objects/example.json"
    body = b'{"ok":true}\n'
    attempts = 0

    class _Response:
        status_code = 200
        is_redirect = False
        headers = {"Content-Length": str(len(body))}

        def __init__(self) -> None:
            self.url = url

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def raise_for_status(self) -> None:
            return None

        def iter_content(self, *, chunk_size: int):
            assert chunk_size == 65_536
            yield body

    def _get(*_args, **_kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise wire_builder.requests.exceptions.SSLError("transient EOF")
        return _Response()

    monkeypatch.setattr(wire_builder.requests, "get", _get)
    monkeypatch.setattr(
        wire_builder,
        "HTTP_FETCH_RETRY_BACKOFF_SECONDS",
        0.0,
        raising=False,
    )

    assert wire_builder._http_fetch(url, timeout=5.0, max_bytes=1024) == body
    assert attempts == 2


def test_http_fetch_exhausts_a_bounded_transport_retry_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = f"{DEFAULT_SOURCE_BASE}/earnings_story_packets/objects/example.json"
    attempts = 0
    sleeps: list[float] = []

    def _get(*_args, **_kwargs):
        nonlocal attempts
        attempts += 1
        raise wire_builder.requests.exceptions.SSLError("persistent EOF")

    monkeypatch.setattr(wire_builder.requests, "get", _get)
    monkeypatch.setattr(wire_builder.time, "sleep", sleeps.append)

    with pytest.raises(PublicWireBuildError, match="persistent EOF"):
        wire_builder._http_fetch(url, timeout=5.0, max_bytes=1024)
    assert attempts == wire_builder.HTTP_FETCH_MAX_ATTEMPTS == 3
    assert sleeps == [
        wire_builder.HTTP_FETCH_RETRY_BACKOFF_SECONDS * attempt
        for attempt in range(1, wire_builder.HTTP_FETCH_MAX_ATTEMPTS)
    ]


def test_http_fetch_does_not_retry_source_policy_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = f"{DEFAULT_SOURCE_BASE}/earnings_story_packets/objects/example.json"
    attempts = 0

    class _RedirectResponse:
        status_code = 302
        is_redirect = True
        headers: dict[str, str] = {}

        def __init__(self) -> None:
            self.url = url

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

    def _get(*_args, **_kwargs):
        nonlocal attempts
        attempts += 1
        return _RedirectResponse()

    monkeypatch.setattr(wire_builder.requests, "get", _get)

    with pytest.raises(PublicWireBuildError, match="redirected or changed origin"):
        wire_builder._http_fetch(url, timeout=5.0, max_bytes=1024)
    assert attempts == 1


def test_http_fetch_does_not_retry_http_status_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = f"{DEFAULT_SOURCE_BASE}/earnings_story_packets/objects/example.json"
    attempts = 0

    class _ErrorResponse:
        status_code = 503
        is_redirect = False
        headers: dict[str, str] = {}

        def __init__(self) -> None:
            self.url = url

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def raise_for_status(self) -> None:
            raise wire_builder.requests.HTTPError("503 Server Error")

    def _get(*_args, **_kwargs):
        nonlocal attempts
        attempts += 1
        return _ErrorResponse()

    monkeypatch.setattr(wire_builder.requests, "get", _get)

    with pytest.raises(PublicWireBuildError, match="503 Server Error"):
        wire_builder._http_fetch(url, timeout=5.0, max_bytes=1024)
    assert attempts == 1


def test_http_fetch_does_not_retry_streamed_byte_bound_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = f"{DEFAULT_SOURCE_BASE}/earnings_story_packets/objects/example.json"
    attempts = 0

    class _OversizeResponse:
        status_code = 200
        is_redirect = False
        headers: dict[str, str] = {}

        def __init__(self) -> None:
            self.url = url

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def raise_for_status(self) -> None:
            return None

        def iter_content(self, *, chunk_size: int):
            assert chunk_size == 65_536
            yield b"x" * 1025

    def _get(*_args, **_kwargs):
        nonlocal attempts
        attempts += 1
        return _OversizeResponse()

    monkeypatch.setattr(wire_builder.requests, "get", _get)

    with pytest.raises(PublicWireBuildError, match="exceeds safe size bound"):
        wire_builder._http_fetch(url, timeout=5.0, max_bytes=1024)
    assert attempts == 1


def test_public_wire_compiler_only_emits_exact_approved_evidence(tmp_path: Path) -> None:
    article, manifest, manifest_raw, _packet_raw = _article(tmp_path)
    verify_public_wire_article(article)
    assert article["admission"]["status"] == "verified_exact_evidence"
    assert article["admission"]["copy_scope"] == "approved_spans_only"
    assert article["execution"]["model_calls"] == 0
    assert article["event"]["slug"] == "aapl-2026q1-call-record"
    assert article["facts"]
    visible_claims = {fact["quote"]["claim_id"] for fact in article["facts"]}
    visible_claims |= {item["claim_id"] for fact in article["facts"] for item in fact["numeric"]}
    assert visible_claims
    assert all(fact["quote"]["receipt"]["source_sha256"] == article["source"]["body_sha256"] for fact in article["facts"])
    assert all(item["receipt"]["source_sha256"] == article["source"]["body_sha256"] for fact in article["facts"] for item in fact["numeric"])

    publication = build_public_wire_manifest(
        [article],
        source_generation_id=manifest["generation_id"],
        source_manifest_sha256=sha256(manifest_raw).hexdigest(),
        source_packet_count=1,
        source_packet_manifest_schema=manifest["schema"],
    )
    verify_public_wire_manifest(publication)
    assert publication["routes"] == [{
        "article_id": article["article_id"],
        "url_path": "/stocks/earnings/aapl-2026q1-call-record.html",
        "canonical": "https://www.mastermind-x.com/stocks/earnings/aapl-2026q1-call-record.html",
        "lastmod": "2026-02-01T00:00:00Z",
    }]


def test_public_wire_rejects_tampered_or_nonempty_source_ready_copy(tmp_path: Path) -> None:
    article, _manifest, _raw, _packet_raw = _article(tmp_path)
    forged = deepcopy(article)
    forged["facts"][0]["quote"]["text"] = "Revenue reached 999 million."
    with pytest.raises(PublicWireContractError):
        verify_public_wire_article(forged)

    packet, manifest, _manifest_raw, _packet_raw = _story_packet(tmp_path / "second")
    forged_packet = deepcopy(packet)
    forged_packet["story"]["copy"]["headline"] = "A model-written headline"
    entry = manifest["packets"]["AAPL/2026Q1"]
    receipt = manifest["files"][entry["object_key"]]
    with pytest.raises(PublicWireContractError):
        compile_public_wire_article(
            forged_packet,
            policy_snapshot=manifest["policy"]["snapshot"],
            generation_id=manifest["generation_id"],
            object_key=entry["object_key"],
            object_sha256=receipt["sha256"],
            object_bytes=receipt["bytes"],
        )


def _remote(manifest: dict, manifest_raw: bytes, packet_raw: bytes) -> tuple[dict[str, bytes], str]:
    entry = manifest["packets"]["AAPL/2026Q1"]
    immutable = f"{DEFAULT_SOURCE_BASE}/earnings_story_packets/generations/{manifest['generation_id']}/manifest.json"
    return {
        f"{DEFAULT_SOURCE_BASE}/earnings_story_packets/manifest.json": manifest_raw,
        immutable: manifest_raw,
        f"{DEFAULT_SOURCE_BASE}/earnings_story_packets/{entry['object_key']}": packet_raw,
    }, f"{DEFAULT_SOURCE_BASE}/earnings_story_packets/{entry['object_key']}"


def _current_company(_params: dict) -> dict:
    return {
        "available": True,
        "generation_id": "c" * 24,
        "company": {"display_name": "Apple Inc."},
        "latest_event": {"fiscal_year": 2026, "fiscal_quarter": 1, "call_date": "2026-01-30"},
        "history": [{"fiscal_year": 2026, "fiscal_quarter": 1, "call_date": "2026-01-30"}],
    }


def _route_event(ticker: str, transcript_id: str, call_date: str) -> dict:
    return {
        "href": f"{ticker.lower()}-{transcript_id.lower()}-call-record.html",
        "period": transcript_id,
        "date": call_date,
        "transcript_id": transcript_id,
        "dossier_available": False,
    }


def _route_state(*, schema: str, floor: str | None = None) -> dict:
    aapl = _route_event("AAPL", "2026Q1", "2026-01-30")
    msft = _route_event("MSFT", "2026Q2", "2026-02-10")
    state = {
        "schema": schema,
        "source_generation_id": "a" * 32,
        "source_manifest_sha256": "b" * 64,
        "verified_at": "2026-02-11T00:00:00Z",
        "company_generation_id": None,
        "renderer_version": "c" * 64,
        "article_count": 2,
        "as_of": "2026-02-11T00:00:00Z",
        "routes": {
            "AAPL": {"company_name": "Apple Inc.", "latest": aapl, "events": {"2026Q1": aapl}},
            "MSFT": {"company_name": "Microsoft Corp.", "latest": msft, "events": {"2026Q2": msft}},
        },
    }
    if floor is not None:
        state["forward_selection_floor_date"] = floor
    return state


def test_route_catalog_v1_migrates_floor_and_v2_preserves_it(tmp_path: Path) -> None:
    out_dir = tmp_path / "wire"
    out_dir.mkdir()
    catalog = out_dir / ROUTE_CATALOG_FILENAME
    catalog.write_text(json.dumps(_route_state(schema="earnings.public_wire_routes/v1")), encoding="utf-8")

    migrated = wire_builder.load_public_build_state(out_dir)
    assert migrated is not None
    assert migrated["forward_selection_floor_date"] == "2026-02-10"
    assert migrated["deferred_packet_keys"] == []

    catalog.write_text(json.dumps(_route_state(
        schema="earnings.public_wire_routes/v2", floor="2026-01-30",
    )), encoding="utf-8")
    preserved = wire_builder.load_public_build_state(out_dir)
    assert preserved is not None
    assert preserved["forward_selection_floor_date"] == "2026-01-30"
    assert preserved["deferred_packet_keys"] == []


def test_route_catalog_v2_rejects_deferred_key_that_is_already_published(tmp_path: Path) -> None:
    out_dir = tmp_path / "wire"
    out_dir.mkdir()
    state = _route_state(schema="earnings.public_wire_routes/v2", floor="2026-01-30")
    state["deferred_packet_keys"] = ["AAPL/2026Q1"]
    (out_dir / ROUTE_CATALOG_FILENAME).write_text(json.dumps(state), encoding="utf-8")

    assert wire_builder.load_public_build_state(out_dir) is None
    with pytest.raises(PublicWireBuildError, match="overlap published routes"):
        wire_builder.load_public_build_state(out_dir, strict=True)


def test_admitted_packet_keys_normalize_route_identity() -> None:
    state = _route_state(schema="earnings.public_wire_routes/v2", floor="2026-01-30")
    event = state["routes"].pop("AAPL")["events"]["2026Q1"]
    event["transcript_id"] = " 2026q1 "
    state["routes"][" aapl "] = {
        "company_name": "Apple Inc.",
        "latest": event,
        "events": {"2026q1": event},
    }
    assert wire_builder._admitted_packet_keys(state) == frozenset({"AAPL/2026Q1", "MSFT/2026Q2"})


@pytest.mark.parametrize("value", ["20260130", "2026-W05-5", "2026-01-30T12:00:00Z"])
def test_iso_day_parser_rejects_non_canonical_dates(value: str) -> None:
    with pytest.raises(PublicWireBuildError, match="ISO date"):
        wire_builder._parse_iso_day(value, name="test date")


def test_iso_day_parser_accepts_trimmed_canonical_date() -> None:
    assert wire_builder._parse_iso_day(" 2026-01-30 ", name="test date").isoformat() == "2026-01-30"


def test_strict_route_state_load_preserves_invalid_date_cause(tmp_path: Path) -> None:
    out_dir = tmp_path / "wire"
    out_dir.mkdir()
    state = _route_state(schema="earnings.public_wire_routes/v2", floor="2026-01-30")
    state["routes"]["AAPL"]["events"]["2026Q1"]["date"] = "not-a-date"
    (out_dir / ROUTE_CATALOG_FILENAME).write_text(json.dumps(state), encoding="utf-8")

    assert wire_builder.load_public_build_state(out_dir) is None
    with pytest.raises(PublicWireBuildError, match="route event date"):
        wire_builder.load_public_build_state(out_dir, strict=True)


def test_incremental_selector_hydrates_admitted_changed_and_forward_new_only() -> None:
    prior_packets = {
        "AAPL/2026Q1": {"object_key": "objects/a.json", "source_sha256": "1"},
        "HOLD/2026Q1": {"object_key": "objects/h.json", "source_sha256": "2"},
        "CORR/2025Q4": {"object_key": "objects/c-old.json", "source_sha256": "3"},
    }
    current_packets = {
        **prior_packets,
        "CORR/2025Q4": {"object_key": "objects/c-new.json", "source_sha256": "4"},
        "NEW/2026Q2": {"object_key": "objects/n.json", "source_sha256": "5"},
        "BACK/2024Q4": {"object_key": "objects/b.json", "source_sha256": "6"},
    }
    state = _route_state(schema="earnings.public_wire_routes/v2", floor="2026-01-30")
    state["routes"] = {
        "AAPL": state["routes"]["AAPL"],
    }
    transcript_index = {
        "generated_at": "2026-03-01T00:00:00Z",
        "dates": {
            "NEW/2026Q2": "2026-02-20",
            "BACK/2024Q4": "2024-12-10",
        },
    }

    selection = wire_builder._select_incremental_packet_keys(
        prior_packets=prior_packets,
        current_packets=current_packets,
        prior_state=state,
        transcript_index=transcript_index,
    )

    assert selection.admitted_keys == frozenset({"AAPL/2026Q1"})
    assert selection.changed_keys == frozenset({"CORR/2025Q4"})
    assert selection.forward_new_keys == frozenset({"NEW/2026Q2"})
    assert selection.skipped_historical_keys == frozenset({"BACK/2024Q4"})
    assert selection.skipped_future_keys == frozenset()
    assert selection.selected_keys == frozenset({"AAPL/2026Q1", "CORR/2025Q4", "NEW/2026Q2"})
    assert "HOLD/2026Q1" not in selection.selected_keys


def test_incremental_selector_includes_new_packet_on_floor_date() -> None:
    state = _route_state(schema="earnings.public_wire_routes/v2", floor="2026-01-30")
    state["routes"] = {}
    selection = wire_builder._select_incremental_packet_keys(
        prior_packets={},
        current_packets={"SAME/2026Q1": {"object_key": "objects/same.json"}},
        prior_state=state,
        transcript_index={
            "generated_at": "2026-02-01T00:00:00Z",
            "dates": {"SAME/2026Q1": "2026-01-30"},
        },
    )
    assert selection.forward_new_keys == frozenset({"SAME/2026Q1"})
    assert selection.skipped_historical_keys == frozenset()



def test_incremental_selector_rejects_new_key_without_a_date() -> None:
    state = _route_state(schema="earnings.public_wire_routes/v2", floor="2026-01-30")
    state["routes"] = {}
    with pytest.raises(PublicWireBuildError, match="date"):
        wire_builder._select_incremental_packet_keys(
            prior_packets={},
            current_packets={"NEW/2026Q2": {"object_key": "objects/n.json"}},
            prior_state=state,
            transcript_index={"generated_at": "2026-03-01T00:00:00Z", "dates": {}},
        )


def test_incremental_selector_rejects_selected_packet_overflow(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _route_state(schema="earnings.public_wire_routes/v2", floor="2026-01-30")
    state["routes"] = {}
    monkeypatch.setattr(wire_builder, "MAX_SELECTED_PACKET_COUNT", 2, raising=False)
    current = {
        f"NEW{i}/2026Q1": {"object_key": f"objects/{i}.json"}
        for i in range(3)
    }
    dates = {key: "2026-02-01" for key in current}
    with pytest.raises(PublicWireBuildError, match="selected packet catalog exceeds safe count bound"):
        wire_builder._select_incremental_packet_keys(
            prior_packets={},
            current_packets=current,
            prior_state=state,
            transcript_index={"generated_at": "2026-02-02T00:00:00Z", "dates": dates},
        )


def test_hydration_rejects_selected_byte_overflow_before_packet_fetch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _article_payload, manifest, manifest_raw, packet_raw = _article(tmp_path / "byte-overflow")
    remote, packet_url = _remote(manifest, manifest_raw, packet_raw)
    calls: list[str] = []
    monkeypatch.setattr(
        wire_builder, "MAX_SELECTED_PACKET_BYTES", len(packet_raw) - 1, raising=False,
    )

    with pytest.raises(PublicWireBuildError, match="selected packet bytes exceed safe bound"):
        fetch_current_publication(
            fetch=lambda url: calls.append(url) or remote[url], workers=1,
        )

    assert packet_url not in calls



def test_incremental_selector_rejects_source_catalog_shrinkage() -> None:
    state = _route_state(schema="earnings.public_wire_routes/v2", floor="2026-01-30")
    state["routes"] = {}
    with pytest.raises(PublicWireBuildError, match="catalog shrank"):
        wire_builder._select_incremental_packet_keys(
            prior_packets={"OLD/2025Q4": {"object_key": "objects/old.json"}},
            current_packets={},
            prior_state=state,
            transcript_index=None,
        )


def test_incremental_selector_rejects_admitted_key_disappearance() -> None:
    state = _route_state(schema="earnings.public_wire_routes/v2", floor="2026-01-30")
    state["routes"] = {"AAPL": state["routes"]["AAPL"]}
    prior = {
        "AAPL/2026Q1": {"object_key": "objects/aapl.json"},
        "HOLD/2026Q1": {"object_key": "objects/hold.json"},
    }
    current = {"HOLD/2026Q1": prior["HOLD/2026Q1"]}

    with pytest.raises(PublicWireBuildError, match=r"lost admitted keys.*AAPL/2026Q1"):
        wire_builder._select_incremental_packet_keys(
            prior_packets=prior,
            current_packets=current,
            prior_state=state,
            transcript_index=None,
        )


def test_incremental_selector_defers_future_dated_new_packet_without_blocking_current() -> None:
    state = _route_state(schema="earnings.public_wire_routes/v2", floor="2026-01-30")
    state["routes"] = {}
    selection = wire_builder._select_incremental_packet_keys(
        prior_packets={},
        current_packets={
            "NOW/2026Q1": {"object_key": "objects/now.json"},
            "FUTURE/2026Q2": {"object_key": "objects/future.json"},
        },
        prior_state=state,
        transcript_index={
            "generated_at": "2026-02-01T23:59:59Z",
            "dates": {
                "NOW/2026Q1": "2026-02-01",
                "FUTURE/2026Q2": "2026-02-02",
            },
        },
    )
    assert selection.forward_new_keys == frozenset({"NOW/2026Q1"})
    assert selection.skipped_future_keys == frozenset({"FUTURE/2026Q2"})
    assert selection.selected_keys == frozenset({"NOW/2026Q1"})

    state["deferred_packet_keys"] = ["FUTURE/2026Q2"]
    matured = wire_builder._select_incremental_packet_keys(
        prior_packets={
            "NOW/2026Q1": {"object_key": "objects/now.json"},
            "FUTURE/2026Q2": {"object_key": "objects/future.json"},
        },
        current_packets={
            "NOW/2026Q1": {"object_key": "objects/now.json"},
            "FUTURE/2026Q2": {"object_key": "objects/future.json"},
        },
        prior_state=state,
        transcript_index={
            "generated_at": "2026-02-02T23:59:59Z",
            "dates": {
                "NOW/2026Q1": "2026-02-01",
                "FUTURE/2026Q2": "2026-02-02",
            },
        },
    )
    assert matured.forward_new_keys == frozenset({"FUTURE/2026Q2"})
    assert matured.skipped_future_keys == frozenset()
    assert matured.selected_keys == frozenset({"FUTURE/2026Q2"})


def test_build_persists_and_promotes_future_packet_without_story_generation_change(
    tmp_path: Path,
) -> None:
    prior, prior_raw, prior_packets, _prior_index = _story_generation(
        tmp_path / "future-prior",
        [("AAPL", "2026Q1", "2026-01-30")],
        generated_at="2026-02-01T00:00:00Z",
    )
    current, current_raw, current_packets, current_index = _story_generation(
        tmp_path / "future-current",
        [
            ("AAPL", "2026Q1", "2026-01-30"),
            ("NOW", "2026Q1", "2026-02-01"),
            ("FUTURE", "2026Q2", "2026-02-02"),
        ],
        generated_at="2026-02-02T00:00:00Z",
    )
    current_index["generated_at"] = "2026-02-01T23:59:59Z"
    out_dir = tmp_path / "site" / "stocks" / "earnings"

    prior_remote = _generation_remote(prior, prior_raw, prior_packets, include_marker=True)
    build(
        out_dir=out_dir,
        fetch=lambda url: prior_remote[url],
        workers=1,
        company_reader=_current_company,
        now=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )

    remote = _generation_remote(current, current_raw, current_packets, include_marker=True)
    remote.update(_generation_remote(prior, prior_raw, prior_packets, include_marker=False))
    index_url = wire_builder.DEFAULT_TRANSCRIPT_INDEX_URL
    remote[index_url] = _canonical_test_json(current_index)
    calls: list[str] = []

    def fetch(url: str, *_args: object) -> bytes:
        calls.append(url)
        return remote[url]

    first = build(
        out_dir=out_dir,
        fetch=fetch,
        workers=1,
        company_reader=_current_company,
        now=datetime(2026, 2, 1, 23, 59, tzinfo=timezone.utc),
    )
    assert first.source == "remote"
    assert first.article_count == 2

    catalog = json.loads((out_dir / ROUTE_CATALOG_FILENAME).read_text(encoding="utf-8"))
    assert set(catalog["routes"]) == {"AAPL", "NOW"}
    assert catalog["deferred_packet_keys"] == ["FUTURE/2026Q2"]
    future_url = (
        f"{DEFAULT_SOURCE_BASE}/earnings_story_packets/"
        f"{current['packets']['FUTURE/2026Q2']['object_key']}"
    )
    assert future_url not in calls

    calls.clear()
    still_future = build(
        out_dir=out_dir,
        fetch=fetch,
        workers=1,
        company_reader=_current_company,
        now=datetime(2026, 2, 2, 0, 30, tzinfo=timezone.utc),
    )
    assert still_future.source == "unchanged"
    assert index_url in calls
    assert future_url not in calls

    matured_index = deepcopy(current_index)
    matured_index["generated_at"] = "2026-02-02T23:59:59Z"
    remote[index_url] = _canonical_test_json(matured_index)
    calls.clear()

    matured = build(
        out_dir=out_dir,
        fetch=fetch,
        workers=1,
        company_reader=_current_company,
        now=datetime(2026, 2, 2, 23, 59, tzinfo=timezone.utc),
    )
    assert matured.source == "remote"
    assert matured.article_count == 3
    assert future_url in calls

    promoted = json.loads((out_dir / ROUTE_CATALOG_FILENAME).read_text(encoding="utf-8"))
    assert set(promoted["routes"]) == {"AAPL", "FUTURE", "NOW"}
    assert promoted["deferred_packet_keys"] == []


def test_deferred_overflow_falls_back_before_packet_hydration_or_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    prior, prior_raw, prior_packets, _prior_index = _story_generation(
        tmp_path / "deferred-overflow-prior",
        [("AAPL", "2026Q1", "2026-01-30")],
        generated_at="2026-02-01T00:00:00Z",
    )
    current, current_raw, current_packets, current_index = _story_generation(
        tmp_path / "deferred-overflow-current",
        [
            ("AAPL", "2026Q1", "2026-01-30"),
            ("FUT1", "2026Q2", "2026-02-02"),
            ("FUT2", "2026Q2", "2026-02-03"),
        ],
        generated_at="2026-02-03T00:00:00Z",
    )
    current_index["generated_at"] = "2026-02-01T23:59:59Z"
    out_dir = tmp_path / "site" / "stocks" / "earnings"
    private_dir = tmp_path / "private"

    prior_remote = _generation_remote(prior, prior_raw, prior_packets, include_marker=True)
    build(
        out_dir=out_dir,
        private_out_dir=private_dir,
        fetch=lambda url: prior_remote[url],
        workers=1,
        company_reader=_current_company,
        now=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )

    def snapshot(root: Path) -> dict[str, bytes]:
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*")
            if path.is_file()
        }

    public_before = snapshot(out_dir)
    private_before = snapshot(private_dir)
    remote = _generation_remote(current, current_raw, current_packets, include_marker=True)
    remote.update(_generation_remote(prior, prior_raw, prior_packets, include_marker=False))
    remote[wire_builder.DEFAULT_TRANSCRIPT_INDEX_URL] = _canonical_test_json(current_index)
    calls: list[str] = []

    def fetch(url: str, *_args: object) -> bytes:
        calls.append(url)
        return remote[url]

    monkeypatch.setattr(wire_builder, "MAX_DEFERRED_PACKET_COUNT", 1)
    retained = build(
        out_dir=out_dir,
        private_out_dir=private_dir,
        fetch=fetch,
        workers=1,
        company_reader=_current_company,
        now=datetime(2026, 2, 1, 12, tzinfo=timezone.utc),
    )

    assert retained.source == "existing"
    assert not any("/objects/" in url for url in calls), calls
    assert snapshot(out_dir) == public_before
    assert snapshot(private_dir) == private_before


def test_prior_story_manifest_must_match_route_catalog_receipt(tmp_path: Path) -> None:
    prior, prior_raw, prior_packets, _index = _story_generation(
        tmp_path / "prior-receipt",
        [("AAPL", "2026Q1", "2026-01-30")],
        generated_at="2026-02-01T00:00:00Z",
    )
    state = _route_state(schema="earnings.public_wire_routes/v2", floor="2026-01-30")
    state["routes"] = {"AAPL": state["routes"]["AAPL"]}
    state["source_generation_id"] = prior["generation_id"]
    state["source_manifest_sha256"] = "0" * 64
    remote = _generation_remote(prior, prior_raw, prior_packets, include_marker=False)

    with pytest.raises(PublicWireBuildError, match="sha256 does not match accepted route state"):
        wire_builder._load_prior_story_snapshot(
            state,
            source_base=DEFAULT_SOURCE_BASE,
            fetch=lambda url: remote[url],
            timeout=1.0,
        )


def test_large_catalog_without_prior_state_fails_before_packet_hydration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    current, current_raw, current_packets, _index = _story_generation(
        tmp_path / "large-bootstrap",
        [("AAPL", "2026Q1", "2026-01-30"), ("MSFT", "2026Q2", "2026-02-10")],
        generated_at="2026-02-11T00:00:00Z",
    )
    monkeypatch.setattr(wire_builder, "MAX_SELECTED_PACKET_COUNT", 1)
    remote = _generation_remote(current, current_raw, current_packets, include_marker=True)
    calls: list[str] = []

    def fetch(url: str) -> bytes:
        calls.append(url)
        return remote[url]

    with pytest.raises(PublicWireBuildError, match="requires a valid prior earnings-wire route catalog"):
        build(
            out_dir=tmp_path / "empty-wire",
            fetch=fetch,
            workers=1,
            company_reader=_current_company,
            now=datetime(2026, 2, 11, tzinfo=timezone.utc),
        )

    packet_urls = {
        f"{DEFAULT_SOURCE_BASE}/earnings_story_packets/{entry['object_key']}"
        for entry in current["packets"].values()
    }
    assert packet_urls.isdisjoint(calls)


def test_build_incrementally_hydrates_admitted_and_forward_events_only(tmp_path: Path) -> None:
    prior, prior_raw, prior_packets, _prior_index = _story_generation(
        tmp_path / "prior",
        [("AAPL", "2026Q1", "2026-01-30")],
        generated_at="2026-02-01T00:00:00Z",
    )
    current, current_raw, current_packets, current_index = _story_generation(
        tmp_path / "current",
        [
            ("AAPL", "2026Q1", "2026-01-30"),
            ("NEW", "2026Q2", "2026-02-20"),
            ("BACK", "2024Q4", "2024-12-10"),
        ],
        generated_at="2026-03-01T00:00:00Z",
    )
    out_dir = tmp_path / "site" / "stocks" / "earnings"

    prior_remote = _generation_remote(prior, prior_raw, prior_packets, include_marker=True)
    build(
        out_dir=out_dir,
        fetch=lambda url: prior_remote[url],
        workers=1,
        company_reader=_current_company,
        now=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )

    remote = _generation_remote(current, current_raw, current_packets, include_marker=True)
    remote.update(_generation_remote(prior, prior_raw, prior_packets, include_marker=False))
    remote["https://app.mastermind-x.com/data/tx/index.json"] = _canonical_test_json(current_index)
    calls: list[str] = []

    def fetch(url: str, *_args: object) -> bytes:
        calls.append(url)
        return remote[url]

    result = build(
        out_dir=out_dir,
        fetch=fetch,
        workers=1,
        company_reader=_current_company,
        now=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )

    assert result.article_count == 2
    catalog = json.loads((out_dir / ROUTE_CATALOG_FILENAME).read_text(encoding="utf-8"))
    assert catalog["schema"] == "earnings.public_wire_routes/v2"
    assert catalog["forward_selection_floor_date"] == "2026-01-30"
    assert set(catalog["routes"]) == {"AAPL", "NEW"}
    assert catalog["source_generation_id"] == current["generation_id"]

    current_urls = {
        key: f"{DEFAULT_SOURCE_BASE}/earnings_story_packets/{entry['object_key']}"
        for key, entry in current["packets"].items()
    }
    assert current_urls["AAPL/2026Q1"] in calls
    assert current_urls["NEW/2026Q2"] in calls
    assert current_urls["BACK/2024Q4"] not in calls
    assert (
        f"{DEFAULT_SOURCE_BASE}/earnings_story_packets/generations/"
        f"{prior['generation_id']}/manifest.json"
    ) in calls


def test_corrected_admitted_packet_that_becomes_held_removes_public_and_private_records(tmp_path: Path) -> None:
    store = tmp_path / "story-packets"
    aapl = deepcopy(_body())
    msft = deepcopy(_body())
    msft.update({
        "ticker": "MSFT",
        "id": "2026Q2",
        "period": "Q2 FY2026",
        "date": "2026-02-10",
        "title": "MSFT earnings call",
    })
    prior, prior_raw, prior_packets, _prior_index = _story_generation_from_bodies(
        tmp_path / "evidence-prior",
        [aapl, msft],
        generated_at="2026-02-11T00:00:00Z",
        store=store,
    )
    out_dir = tmp_path / "site" / "stocks" / "earnings"
    private_dir = tmp_path / "private-earnings"
    prior_remote = _generation_remote(prior, prior_raw, prior_packets, include_marker=True)
    build(
        out_dir=out_dir,
        private_out_dir=private_dir,
        fetch=lambda url: prior_remote[url],
        workers=1,
        company_reader=_current_company,
        now=datetime(2026, 2, 11, tzinfo=timezone.utc),
    )

    aapl_page = out_dir / "aapl-2026q1-call-record.html"
    msft_page = out_dir / "msft-2026q2-call-record.html"
    aapl_private = private_dir / "records" / "aapl-2026q1-call-record.json"
    msft_private = private_dir / "records" / "msft-2026q2-call-record.json"
    assert aapl_page.is_file() and msft_page.is_file()
    assert aapl_private.is_file() and msft_private.is_file()

    corrected_aapl = deepcopy(aapl)
    corrected_aapl["segments"] = [{
        "speaker": "Chief Executive Officer",
        "role": "executive",
        "text": "Thank you for joining today. We appreciate your interest in the company.",
    }]
    current, current_raw, current_packets, _current_index = _story_generation_from_bodies(
        tmp_path / "evidence-current",
        [corrected_aapl, msft],
        generated_at="2026-02-12T00:00:00Z",
        store=store,
    )
    corrected_packet = json.loads(current_packets["AAPL/2026Q1"])
    assert corrected_packet["story"]["promotion"]["tier"] == "C"
    assert corrected_packet["story"]["promotion"]["article_eligible"] is False

    remote = _generation_remote(current, current_raw, current_packets, include_marker=True)
    remote.update(_generation_remote(prior, prior_raw, prior_packets, include_marker=False))
    result = build(
        out_dir=out_dir,
        private_out_dir=private_dir,
        fetch=lambda url: remote[url],
        workers=1,
        company_reader=_current_company,
        now=datetime(2026, 2, 12, tzinfo=timezone.utc),
    )

    assert result.article_count == 1
    assert not aapl_page.exists()
    assert not aapl_private.exists()
    assert msft_page.is_file()
    assert msft_private.is_file()
    catalog = json.loads((out_dir / ROUTE_CATALOG_FILENAME).read_text(encoding="utf-8"))
    assert set(catalog["routes"]) == {"MSFT"}
    assert catalog["source_generation_id"] == current["generation_id"]
    assert catalog["forward_selection_floor_date"] == "2026-02-10"

    corrected_msft = deepcopy(msft)
    corrected_msft["segments"] = [{
        "speaker": "Chief Executive Officer",
        "role": "executive",
        "text": "Thank you for joining today. We appreciate your interest in the company.",
    }]
    empty_current, empty_raw, empty_packets, _empty_index = _story_generation_from_bodies(
        tmp_path / "evidence-empty-current",
        [corrected_aapl, corrected_msft],
        generated_at="2026-02-13T00:00:00Z",
        store=store,
    )
    empty_remote = _generation_remote(empty_current, empty_raw, empty_packets, include_marker=True)
    empty_remote.update(_generation_remote(current, current_raw, current_packets, include_marker=False))
    catalog_before = (out_dir / ROUTE_CATALOG_FILENAME).read_bytes()
    page_before = msft_page.read_bytes()
    private_before = msft_private.read_bytes()

    retained = build(
        out_dir=out_dir,
        private_out_dir=private_dir,
        fetch=lambda url: empty_remote[url],
        workers=1,
        company_reader=_current_company,
        now=datetime(2026, 2, 13, tzinfo=timezone.utc),
    )

    assert retained.source == "existing"
    assert retained.article_count == 1
    assert (out_dir / ROUTE_CATALOG_FILENAME).read_bytes() == catalog_before
    assert msft_page.read_bytes() == page_before
    assert msft_private.read_bytes() == private_before


def test_corrected_admitted_packet_that_remains_eligible_replaces_the_article(tmp_path: Path) -> None:
    store = tmp_path / "story-packets"
    prior_body = _body()
    prior, prior_raw, prior_packets, _prior_index = _story_generation_from_bodies(
        tmp_path / "eligible-prior",
        [prior_body],
        generated_at="2026-02-01T00:00:00Z",
        store=store,
    )
    out_dir = tmp_path / "site" / "stocks" / "earnings"
    private_dir = tmp_path / "private-earnings"
    prior_remote = _generation_remote(prior, prior_raw, prior_packets, include_marker=True)
    build(
        out_dir=out_dir,
        private_out_dir=private_dir,
        fetch=lambda url: prior_remote[url],
        workers=1,
        company_reader=_current_company,
        now=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )

    page = out_dir / "aapl-2026q1-call-record.html"
    private_record = private_dir / "records" / "aapl-2026q1-call-record.json"
    prior_page = page.read_bytes()
    prior_private = private_record.read_bytes()
    assert b"CORRECTED VALID ARTICLE TOKEN" not in prior_page

    corrected_body = deepcopy(prior_body)
    for segment in corrected_body["segments"]:
        segment["text"] = f'{segment["text"]} CORRECTED VALID ARTICLE TOKEN.'
    current, current_raw, current_packets, _current_index = _story_generation_from_bodies(
        tmp_path / "eligible-current",
        [corrected_body],
        generated_at="2026-02-02T00:00:00Z",
        store=store,
    )
    corrected_packet = json.loads(current_packets["AAPL/2026Q1"])
    assert corrected_packet["story"]["promotion"]["article_eligible"] is True

    remote = _generation_remote(current, current_raw, current_packets, include_marker=True)
    remote.update(_generation_remote(prior, prior_raw, prior_packets, include_marker=False))
    result = build(
        out_dir=out_dir,
        private_out_dir=private_dir,
        fetch=lambda url: remote[url],
        workers=1,
        company_reader=_current_company,
        now=datetime(2026, 2, 2, tzinfo=timezone.utc),
    )

    assert result.source == "remote"
    assert result.article_count == 1
    updated_page = page.read_bytes()
    updated_private = private_record.read_bytes()
    assert updated_page != prior_page
    assert updated_private != prior_private
    assert b"CORRECTED VALID ARTICLE TOKEN" not in prior_private
    assert b"CORRECTED VALID ARTICLE TOKEN" in updated_private
    catalog = json.loads((out_dir / ROUTE_CATALOG_FILENAME).read_text(encoding="utf-8"))
    assert catalog["source_generation_id"] == current["generation_id"]
    assert set(catalog["routes"]) == {"AAPL"}


def test_wire_builder_verifies_immutable_generation_aligns_and_persists_only_redacted_state(tmp_path: Path) -> None:
    _article_payload, manifest, manifest_raw, packet_raw = _article(tmp_path / "source")
    remote, packet_url = _remote(manifest, manifest_raw, packet_raw)
    calls: list[str] = []

    def fetch(url: str) -> bytes:
        calls.append(url)
        return remote[url]

    publication = fetch_current_publication(fetch=fetch, workers=1)
    assert publication["schema"] == "earnings.public_wire_manifest/v1"
    assert len(publication["articles"]) == 1
    assert packet_url in calls

    out_dir = tmp_path / "site" / "stocks" / "earnings"
    dossier = out_dir.parent / "AAPL.html"
    dossier.parent.mkdir(parents=True, exist_ok=True)
    dossier.write_text("<!doctype html><title>AAPL — Apple Inc. | MastermindX</title>", encoding="utf-8")
    root_sitemap = tmp_path / "site" / "sitemap.xml"
    root_sitemap.write_text("root sitemap stays untouched", encoding="utf-8")
    private_dir = tmp_path / "private-earnings"
    first = build(out_dir=out_dir, fetch=fetch, workers=1, company_reader=_current_company,
                  private_out_dir=private_dir,
                  now=datetime(2026, 2, 1, tzinfo=timezone.utc))
    assert first.source == "remote"
    assert (out_dir / "index.html").exists()
    assert (out_dir / "aapl-2026q1-call-record.html").exists()
    assert (out_dir / "feed.xml").exists()
    assert "/stocks/earnings/aapl-2026q1-call-record.html" in (out_dir / "sitemap.xml").read_text(encoding="utf-8")
    assert root_sitemap.read_text(encoding="utf-8") == "root sitemap stays untouched"
    assert not (out_dir / "article_manifest.json").exists()
    assert not (out_dir / "publications").exists()
    public_routes = json.loads((out_dir / ROUTE_CATALOG_FILENAME).read_text(encoding="utf-8"))
    assert public_routes["schema"] == "earnings.public_wire_routes/v2"
    assert public_routes["forward_selection_floor_date"] == "2026-01-30"
    assert public_routes["company_generation_id"] == "c" * 24
    assert re.fullmatch(r"[0-9a-f]{64}", public_routes["renderer_version"])
    assert public_routes["routes"]["AAPL"]["company_name"] == "Apple Inc."
    event = public_routes["routes"]["AAPL"]["events"]["2026Q1"]
    assert event == {
        "href": "aapl-2026q1-call-record.html", "period": "Q1 FY2026", "date": "2026-01-30",
        "transcript_id": "2026Q1", "dossier_available": True,
    }
    assert public_routes["routes"]["AAPL"]["latest"] == event
    public_route_bytes = (out_dir / ROUTE_CATALOG_FILENAME).read_bytes()
    for private_token in (b"facts", b"receipt", b"object_key", b"source_sha256", b"/data/tx/"):
        assert private_token not in public_route_bytes
    rendered = (out_dir / "aapl-2026q1-call-record.html").read_text(encoding="utf-8")
    assert "Apple Inc." in rendered
    assert "A model-written" not in rendered
    view = _view_article(publication["articles"][0], alignment={"company_name": "Apple Inc."})
    public_quotes = [fact["quote"]["text"] for fact in view["public_facts"]]
    locked_quotes = [fact["quote"]["text"] for fact in view["locked_facts"]]
    assert public_quotes and locked_quotes
    assert all(quote in rendered for quote in public_quotes)
    assert all(quote not in rendered for quote in locked_quotes)
    assert "Member evidence layer" in rendered
    assert "/api/earnings/v1/records/aapl-2026q1-call-record" in rendered
    payload_path = private_dir / "records" / "aapl-2026q1-call-record.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    assert payload["schema"] == "earnings.tier_payload/v1"
    assert payload["public_facts"] == 2
    assert payload["locked_facts"] == len(locked_quotes)
    assert all(quote in payload["facts_html"] for quote in locked_quotes)
    assert all(quote not in payload["facts_html"] for quote in public_quotes)
    weekly_page = out_dir / "weekly" / "2026-01-26.html"
    assert weekly_page.is_file()
    weekly_markup = weekly_page.read_text(encoding="utf-8")
    assert "The week in management language" in weekly_markup
    assert public_quotes[0] in weekly_markup
    assert all(quote not in weekly_markup for quote in locked_quotes)
    assert "/stocks/earnings/weekly/2026-01-26.html" in (out_dir / "sitemap.xml").read_text(encoding="utf-8")
    assert not (tmp_path / "site" / "premiumdata" / "earnings").exists()
    context_path = private_dir / "context" / "latest.json"
    context = json.loads(context_path.read_text(encoding="utf-8"))
    assert context["schema"] == CONTEXT_MANIFEST_SCHEMA
    receipt = context["objects"]["AAPL"]
    context_packet = json.loads((context_path.parent / receipt["path"]).read_text(encoding="utf-8"))
    assert context_packet["authority"]["prophet_authority"] is False
    assert context["execution"]["model_calls"] == 0
    assert '../AAPL.html?from=earnings-wire&amp;tx=2026Q1' in rendered
    assert "utm_source=earnings_wire" in rendered

    calls.clear()
    unchanged = build(out_dir=out_dir, fetch=fetch, workers=1, company_reader=_current_company,
                      now=datetime(2026, 2, 1, 1, tzinfo=timezone.utc))
    assert unchanged.source == "unchanged"
    assert packet_url not in calls, "same verified generation must not hydrate packets again"

    calls.clear()
    forced = build(
        out_dir=out_dir, fetch=fetch, workers=1, company_reader=_current_company,
        force=True, now=datetime(2026, 2, 1, 1, 15, tzinfo=timezone.utc),
    )
    assert forced.source == "remote"
    assert packet_url in calls, "--force must deliberately bypass the generation fast path"

    stale_renderer = json.loads((out_dir / ROUTE_CATALOG_FILENAME).read_text(encoding="utf-8"))
    stale_renderer["renderer_version"] = "0" * 64
    (out_dir / ROUTE_CATALOG_FILENAME).write_text(
        json.dumps(stale_renderer, sort_keys=True, separators=(",", ":")), encoding="utf-8",
    )
    calls.clear()
    rerendered = build(out_dir=out_dir, fetch=fetch, workers=1, company_reader=_current_company,
                       now=datetime(2026, 2, 1, 1, 30, tzinfo=timezone.utc))
    assert rerendered.source == "remote"
    assert packet_url in calls, "renderer changes must invalidate the source-generation fast path"

    def newer_company(params: dict) -> dict:
        result = _current_company(params)
        result["generation_id"] = "d" * 24
        return result

    calls.clear()
    refreshed = build(out_dir=out_dir, fetch=fetch, workers=1, company_reader=newer_company,
                      now=datetime(2026, 2, 1, 2, tzinfo=timezone.utc))
    assert refreshed.source == "remote"
    assert packet_url in calls
    assert json.loads((out_dir / ROUTE_CATALOG_FILENAME).read_text(encoding="utf-8"))["company_generation_id"] == "d" * 24


def test_injected_fetch_may_receive_the_enforced_byte_limit(tmp_path: Path) -> None:
    _article_payload, manifest, manifest_raw, packet_raw = _article(tmp_path / "two-arg-fetch")
    remote, _packet_url = _remote(manifest, manifest_raw, packet_raw)
    limits: list[int] = []

    def fetch(url: str, limit: int) -> bytes:
        limits.append(limit)
        return remote[url]

    publication = fetch_current_publication(fetch=fetch, workers=1)
    assert len(publication["articles"]) == 1
    assert limits and all(limit > 0 for limit in limits)


def test_wire_rejects_mutable_marker_mismatch_before_packet_hydration(tmp_path: Path) -> None:
    _article_payload, manifest, manifest_raw, packet_raw = _article(tmp_path)
    remote, packet_url = _remote(manifest, manifest_raw, packet_raw)
    forged = json.loads(manifest_raw)
    forged["generated_at"] = "2026-02-02T00:00:00Z"
    remote[next(key for key in remote if "/generations/" in key)] = json.dumps(forged, sort_keys=True, separators=(",", ":")).encode()
    calls: list[str] = []
    with pytest.raises(PublicWireBuildError):
        fetch_current_publication(fetch=lambda url: calls.append(url) or remote[url], workers=1)
    assert packet_url not in calls


def test_wire_caps_and_stale_existing_fallback_fail_closed(tmp_path: Path) -> None:
    out_dir = tmp_path / "site" / "stocks" / "earnings"
    with pytest.raises(PublicWireBuildError):
        build(out_dir=out_dir, fetch=lambda _url: b"x" * (MAX_MANIFEST_BYTES + 1), workers=1)

    _article_payload, manifest, manifest_raw, packet_raw = _article(tmp_path / "source")
    remote, _packet = _remote(manifest, manifest_raw, packet_raw)
    (out_dir.parent / "AAPL.html").parent.mkdir(parents=True, exist_ok=True)
    (out_dir.parent / "AAPL.html").write_text("<title>AAPL — Apple Inc.</title>", encoding="utf-8")
    build(out_dir=out_dir, fetch=lambda url: remote[url], workers=1, company_reader=_current_company,
          now=datetime(2026, 2, 1, tzinfo=timezone.utc))
    before = (out_dir / "index.html").read_bytes()
    retained = build(out_dir=out_dir, fetch=lambda _url: (_ for _ in ()).throw(RuntimeError("offline")), workers=1,
                     now=datetime(2026, 2, 2, 12, tzinfo=timezone.utc))
    assert retained.source == "existing"
    assert (out_dir / "index.html").read_bytes() == before
    with pytest.raises(PublicWireBuildError) as excinfo:
        build(out_dir=out_dir, fetch=lambda _url: (_ for _ in ()).throw(RuntimeError("offline")), workers=1,
              now=datetime(2026, 2, 3, 1, tzinfo=timezone.utc))
    message = str(excinfo.value)
    assert "offline" in message
    assert "older than 48 hours" in message


def test_company_alignment_requires_latest_event_not_only_history(tmp_path: Path) -> None:
    article, manifest, manifest_raw, _packet = _article(tmp_path)
    publication = build_public_wire_manifest(
        [article], source_generation_id=manifest["generation_id"], source_manifest_sha256=sha256(manifest_raw).hexdigest(),
        source_packet_count=1, source_packet_manifest_schema=manifest["schema"],
    )
    out_dir = tmp_path / "site" / "stocks" / "earnings"
    (out_dir.parent / "AAPL.html").parent.mkdir(parents=True, exist_ok=True)
    (out_dir.parent / "AAPL.html").write_text("<title>AAPL — Apple Inc.</title>", encoding="utf-8")
    alignment = build_company_alignment(publication, out_dir=out_dir, company_reader=lambda _params: {
        "available": True, "company": {"display_name": "Apple Inc."},
        "latest_event": {"fiscal_year": 2026, "fiscal_quarter": 2, "call_date": "2026-04-29"},
        "history": [
            {"fiscal_year": 2026, "fiscal_quarter": 2, "call_date": "2026-04-29"},
            {"fiscal_year": 2026, "fiscal_quarter": 1, "call_date": "2026-01-30"},
        ],
    })
    row = alignment[article["article_id"]]
    assert row["alignment_status"] == "historical_only"
    assert row["dossier_available"] is False


def test_publish_removes_stale_article_named_by_prior_redacted_routes(tmp_path: Path) -> None:
    article, manifest, manifest_raw, _packet = _article(tmp_path)
    publication = build_public_wire_manifest(
        [article], source_generation_id=manifest["generation_id"], source_manifest_sha256=sha256(manifest_raw).hexdigest(),
        source_packet_count=1, source_packet_manifest_schema=manifest["schema"],
    )
    out_dir = tmp_path / "site" / "stocks" / "earnings"
    (out_dir.parent / "AAPL.html").parent.mkdir(parents=True, exist_ok=True)
    (out_dir.parent / "AAPL.html").write_text("<title>AAPL — Apple Inc.</title>", encoding="utf-8")
    out_dir.mkdir(parents=True, exist_ok=True)
    stale = out_dir / "aapl-2025q4-call-record.html"
    stale.write_text("obsolete", encoding="utf-8")
    private_dir = tmp_path / "private-earnings"
    stale_payload = private_dir / "records" / "aapl-2025q4-call-record.json"
    stale_payload.parent.mkdir(parents=True, exist_ok=True)
    stale_payload.write_text("{}", encoding="utf-8")
    prior_state = {
        "routes": {"AAPL": {"events": {"2025Q4": {"href": stale.name}}}},
    }
    publish_public_wire(publication, out_dir=out_dir, prior_state=prior_state, company_reader=_current_company,
                        private_out_dir=private_dir,
                        now=datetime(2026, 2, 1, tzinfo=timezone.utc))
    assert not stale.exists()
    assert not stale_payload.exists()


def test_preview_prefers_management_material_evidence_over_boilerplate_or_qa(tmp_path: Path) -> None:
    article, _manifest, _raw, _packet = _article(tmp_path)
    forged = deepcopy(article)
    forged["facts"][0]["quote"]["text"] = "Operator: this replay contains forward-looking statements and safe harbor language."
    forged["facts"][0]["role"] = "analyst"
    forged["facts"][1]["quote"]["text"] = "Revenue grew 12% to 120 million and gross margin reached 45%."
    forged["facts"][1]["role"] = "executive"
    for fact in forged["facts"][2:]:
        fact["quote"]["text"] = "Operator: thank you for joining the replay and safe harbor statement."
        fact["role"] = "analyst"
    view = _view_article(forged, alignment={"company_name": "Apple Inc.", "dossier_available": False})
    assert view["preview_quote"].startswith("Revenue grew")
    assert "apple inc" in view["search_text"]


def test_preview_skips_excerpts_that_carry_the_validated_authority_token(tmp_path: Path) -> None:
    """WAVE-class marketing copy must not win the public card over a clean excerpt.

    The packet stays verbatim (receipt-bound). Public HTML is the gated surface.
    """
    article, _manifest, _raw, _packet = _article(tmp_path)
    forged = deepcopy(article)
    contaminated = (
        "Overall, we believe that the combination of validated technology, "
        "growing global project pipeline, improving cost discipline, and "
        "increasing global demand for clean energy driven by AI positions "
        "Eco Wave Power well for the next phase of growth."
    )
    forged["facts"][0]["quote"]["text"] = contaminated
    forged["facts"][0]["role"] = "executive"
    forged["facts"][1]["quote"]["text"] = (
        "As artificial intelligence continues to expand globally, it is driving "
        "significant growth in electricity demands, particularly from data centers."
    )
    forged["facts"][1]["role"] = "executive"
    for fact in forged["facts"][2:]:
        fact["quote"]["text"] = "Operator: thank you for joining the replay and safe harbor statement."
        fact["role"] = "analyst"
    view = _view_article(forged, alignment={"company_name": "Eco Wave Power", "dossier_available": False})
    assert "validated" not in view["preview_quote"].lower()
    assert view["preview_quote"].startswith("As artificial intelligence")
    public_texts = [fact["quote"]["text"] for fact in view["public_facts"]]
    assert all("validated" not in text.lower() for text in public_texts)
    locked_texts = [fact["quote"]["text"] for fact in view["locked_facts"]]
    assert contaminated in locked_texts


def test_exact_evidence_context_and_weekly_contracts_are_deterministic_and_context_only(tmp_path: Path) -> None:
    article, manifest, manifest_raw, _packet = _article(tmp_path)
    publication = build_public_wire_manifest(
        [article], source_generation_id=manifest["generation_id"],
        source_manifest_sha256=sha256(manifest_raw).hexdigest(), source_packet_count=1,
        source_packet_manifest_schema=manifest["schema"],
    )
    packet = build_context_packet(article)
    assert packet["schema"] == "earnings.context_packet/v1"
    assert packet["authority"] == {
        "class": "context_only", "may_add_candidate": False, "may_rank": False,
        "may_size": False, "may_gate": False, "may_escalate": False,
        "prophet_authority": False,
    }
    assert packet["execution"]["model_calls"] == 0
    assert len(packet["facts"]) <= MAX_CONTEXT_FACTS
    assert all(fact["quote"]["receipt"]["source_sha256"] == packet["source"]["source_sha256"] for fact in packet["facts"])

    context = build_context_manifest(publication)
    validate_context_manifest(context)
    assert context_json_bytes(context) == context_json_bytes(build_context_manifest(publication))
    assert context["objects"]["AAPL"]["context_id"] == packet["context_id"]

    weeks = build_weekly_intelligence(publication)
    assert len(weeks) == 1
    weekly = weeks[0]
    validate_weekly_intelligence(weekly)
    assert weekly["schema"] == WEEKLY_INTELLIGENCE_SCHEMA
    assert weekly["week_start"] == "2026-01-26"
    assert weekly["week_end"] == "2026-02-01"
    assert weekly["coverage"]["call_records"] == 1
    assert weekly["authority"]["may_rank"] is False
    assert weekly["disclosures"]["selection"] == "editorial_relevance_not_opportunity_rank"
    approved_public_claims = {
        fact["claim_id"] for fact in select_public_facts(article["facts"])
    }
    assert {
        fact["claim_id"]
        for record in weekly["notable_records"]
        for fact in record["facts"]
    } <= approved_public_claims

    with pytest.raises(EarningsContextContractError):
        validate_context_manifest({**context, "combined_rating": 99})


def test_context_packet_rejects_semantically_forged_nested_facts_even_with_rebound_id(tmp_path: Path) -> None:
    article, _manifest, _manifest_raw, _packet = _article(tmp_path)
    forged = deepcopy(build_context_packet(article))
    forged["facts"] = ["not a receipt-bound exact fact"]
    forged["categories"] = []
    forged["context_id"] = "earnctx_" + ("0" * 32)
    forged["context_id"] = "earnctx_" + sha256(context_json_bytes(forged)).hexdigest()[:32]
    with pytest.raises(EarningsContextContractError, match="exact facts invalid"):
        validate_context_packet(forged)


def test_neuralweb_exact_evidence_reader_hash_verifies_one_ticker_object(tmp_path: Path) -> None:
    article, manifest, manifest_raw, _packet = _article(tmp_path / "source")
    publication = build_public_wire_manifest(
        [article], source_generation_id=manifest["generation_id"],
        source_manifest_sha256=sha256(manifest_raw).hexdigest(), source_packet_count=1,
        source_packet_manifest_schema=manifest["schema"],
    )
    catalog, packets = build_context_generation(publication)
    private_root = tmp_path / "private-stage"
    directory = private_root / "context"
    directory.mkdir(parents=True)
    (directory / "latest.json").write_bytes(context_json_bytes(catalog))
    for ticker, packet in packets.items():
        (directory / catalog["objects"][ticker]["path"]).write_bytes(context_json_bytes(packet))

    result = read_earnings_evidence({"ticker": "aapl"}, root=private_root)
    assert result["available"] is True
    assert result["ticker"] == "AAPL"
    assert result["permissions"]["may_rank"] is False
    assert result["facts"][0]["quote"]["receipt"]["source_sha256"] == result["receipts"]["source_sha256"]

    before_ingestion = read_earnings_evidence(
        {"ticker": "AAPL", "as_of": "2026-01-31"}, root=private_root,
    )
    assert before_ingestion["available"] is False
    assert "point-in-time" in before_ingestion["note"]
    known_by_cutoff = read_earnings_evidence(
        {"ticker": "AAPL", "as_of": "2026-02-01T23:59:59Z"}, root=private_root,
    )
    assert known_by_cutoff["available"] is True

    object_path = directory / catalog["objects"]["AAPL"]["path"]
    object_path.write_bytes(object_path.read_bytes().replace(b"Revenue", b"REVENUe", 1))
    rejected = read_earnings_evidence({"ticker": "AAPL"}, root=private_root)
    assert rejected["available"] is False
    assert "integrity failure" in rejected["note"]


def test_committed_wire_is_redacted_and_uses_dedicated_sitemap_only() -> None:
    repo = Path(__file__).resolve().parents[1]
    wire = repo / "site" / "stocks" / "earnings"
    catalog = wire / ROUTE_CATALOG_FILENAME
    if not catalog.is_file():
        pytest.skip("committed public wire is not hydrated")
    assert not (repo / "data" / "earnings_public_wire").exists()
    assert not (wire / "article_manifest.json").exists()
    assert not (wire / "publications").exists()
    for candidate in wire.glob("*.json"):
        body = candidate.read_bytes()
        for private_token in (b'"facts"', b'"receipt"', b'"object_key"', b'"source_sha256"', b'"/data/tx/'):
            assert private_token not in body, candidate
    state = json.loads(catalog.read_text(encoding="utf-8"))
    assert state["schema"] in {
        "earnings.public_wire_routes/v1",
        "earnings.public_wire_routes/v2",
    }
    if state["schema"] == "earnings.public_wire_routes/v2":
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", state["forward_selection_floor_date"])
    sitemap = (wire / "sitemap.xml").read_text(encoding="utf-8")
    assert "/stocks/earnings/index.html" in sitemap
    assert "/stocks/earnings/" not in (repo / "site" / "sitemap.xml").read_text(encoding="utf-8")
    for ticker, row in state["routes"].items():
        for tx, event in row["events"].items():
            page = wire / event["href"]
            markup = page.read_text(encoding="utf-8")
            assert f"tx={tx}" in markup
            if event["dossier_available"]:
                assert f'../{ticker}.html?from=earnings-wire&amp;tx={tx}' in markup
            else:
                assert "utm_source=earnings_wire" in markup


def test_wire_filter_hidden_state_wins_over_card_layout() -> None:
    """Filtering must hide cards visually, not just update the result count."""
    repo = Path(__file__).resolve().parents[1]
    css = (repo / "templates" / "earnings_wire" / "earnings-wire.css").read_text(encoding="utf-8")
    committed_css = (repo / "site" / "stocks" / "earnings" / "assets" / "earnings-wire.css").read_text(
        encoding="utf-8"
    )
    script = (repo / "templates" / "earnings_wire" / "earnings-wire.js").read_text(encoding="utf-8")
    assert "card.hidden=!match" in script
    assert ".ew-card[hidden]{display:none!important}" in css
    assert ".ew-card[hidden]{display:none!important}" in committed_css


def test_wire_index_uses_a_contained_weekly_panel_and_ui_typography() -> None:
    """The weekly bridge must have intentional edges and localized copy must stay UI text."""
    repo = Path(__file__).resolve().parents[1]
    source_css = (repo / "templates" / "earnings_wire" / "earnings-wire.css").read_text(
        encoding="utf-8"
    )
    committed_css = (
        repo / "site" / "stocks" / "earnings" / "assets" / "earnings-wire.css"
    ).read_text(encoding="utf-8")
    index = (repo / "templates" / "earnings_wire" / "earnings_wire_index.html.j2").read_text(
        encoding="utf-8"
    )

    assert source_css == committed_css
    assert ".ew-weekly-bridge{padding-block:20px;background:transparent}" in source_css
    assert ".ew-weekly-bridge .ew-wrap{" in source_css
    assert "border-radius:16px" in source_css
    assert ".ew-weekly-bridge .ew-wrap::before{" in source_css
    assert not re.search(r"\.ew-weekly-bridge\{[^}]*gradient", source_css)
    assert index.count('class="ew-eyebrow"') >= 2
    assert ".ew-section-head span" not in source_css
    assert ".ew-protocol span" not in source_css
    assert ".earnings-wire-index{--num:var(--ew-ui)}" in source_css
    assert ".ew-tags span" in source_css and "font:700 9px var(--ew-ui)" in source_css


def test_member_gate_never_flashes_at_a_signed_in_reader() -> None:
    """The gate must not paint while the entitlement answer is still in flight.

    2026-08-04 (operator, on a call-record page opened logged in): "for a split second
    it will show the gating container and then it will disappear". The gate ships in
    the HTML and earnings-wire.js removes it only after auth settles AND the payload
    fetch returns — up to 3s of auth wait plus a round trip, all of it painted.

    Three legs hold this up, and each one is load-bearing on its own:
      1. a synchronous <head> script that reads the Supabase session COOKIE (theme.js
         uses cookie storage, so this is answerable before first paint) and holds the
         gate back — but ONLY when a session exists, so anonymous readers and crawlers
         are untouched;
      2. a CSS rule keyed to that hold and nothing else;
      3. an unconditional release on the failure path, ahead of every early return in
         revealSignin — the signed-in-but-not-entitled reader hits the FIRST of those
         returns, so a release placed after them would hide the gate from exactly the
         reader it is meant for.
    """
    repo = Path(__file__).resolve().parents[1]
    template = (repo / "templates" / "earnings_wire" / "earnings_wire_article.html.j2").read_text(
        encoding="utf-8"
    )
    css_paths = (
        repo / "templates" / "earnings_wire" / "earnings-wire.css",
        repo / "site" / "stocks" / "earnings" / "assets" / "earnings-wire.css",
    )
    js_paths = (
        repo / "templates" / "earnings_wire" / "earnings-wire.js",
        repo / "site" / "stocks" / "earnings" / "assets" / "earnings-wire.js",
    )

    # 1 — the pre-paint hold, gated on a real session cookie and self-expiring.
    assert "sb-[^=;]*-auth-token" in template
    assert "d.setAttribute('data-earnings-member','pending')" in template
    assert "d.removeAttribute('data-earnings-member')" in template
    assert "},8000);" in template, "the boot script must expire its own hold"

    # 2 — one rule, keyed to the hold. Anything broader would be an entitlement
    #     check in CSS, and the locked excerpts are not in this document anyway.
    rule = 'html[data-earnings-member="pending"] .ewa-member-gate{display:none}'
    for path in css_paths:
        css = path.read_text(encoding="utf-8")
        assert rule in css, path
        assert css.count("data-earnings-member") == 1, path

    # 3 — release before the early returns, not after them. Comments are stripped
    #     first: the guard has to read the code, not the prose explaining it.
    for path in js_paths:
        script = path.read_text(encoding="utf-8")
        halves = script.split("function revealSignin(){", 1)
        assert len(halves) == 2, path
        body = halves[1].split("\n  }", 1)[0]
        body = "\n".join(re.sub(r"//.*$", "", line) for line in body.splitlines())
        release = body.index("removeAttribute('data-earnings-member')")
        assert release < body.index("return"), f"{path}: gate release sits behind an early return"


def test_wire_header_cta_keeps_contrast_against_estate_link_rule() -> None:
    """The estate-wide anchor color must not turn the blue header CTA text blue."""
    repo = Path(__file__).resolve().parents[1]
    rule = ".earnings-wire .public-nav-cta,.earnings-wire .public-nav-cta:hover{color:#fff}"
    template_css = (repo / "templates" / "earnings_wire" / "earnings-wire.css").read_text(encoding="utf-8")
    committed_css = (repo / "site" / "stocks" / "earnings" / "assets" / "earnings-wire.css").read_text(
        encoding="utf-8"
    )
    assert rule in template_css
    assert rule in committed_css


def test_wire_light_theme_status_text_meets_normal_text_contrast() -> None:
    """Tiny provenance labels must remain legible on both light surfaces."""
    repo = Path(__file__).resolve().parents[1]

    def luminance(hex_color: str) -> float:
        channels = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [
            channel / 12.92 if channel <= 0.04045
            else ((channel + 0.055) / 1.055) ** 2.4
            for channel in channels
        ]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    def contrast(a: str, b: str) -> float:
        lighter, darker = sorted((luminance(a), luminance(b)), reverse=True)
        return (lighter + 0.05) / (darker + 0.05)

    for relative in (
        "templates/earnings_wire/earnings-wire.css",
        "site/stocks/earnings/assets/earnings-wire.css",
    ):
        css = (repo / relative).read_text(encoding="utf-8")
        override = re.search(
            r'html\[data-theme="light"\] \.earnings-wire\{([^}]+)\}',
            css,
        )
        assert override, relative
        colors = dict(re.findall(r"--([\w-]+):(#(?:[0-9a-fA-F]{6}))", override.group(1)))
        for token in ("ew-accent", "ew-hot", "ew-warm", "ew-quiet"):
            assert token in colors, (relative, token)
            assert contrast(colors[token], "#ffffff") >= 4.5, (relative, token)
            assert contrast(colors[token], "#f6f7fa") >= 4.5, (relative, token)


def test_wire_article_has_one_localized_breadcrumb_and_source_language() -> None:
    repo = Path(__file__).resolve().parents[1]
    article = (repo / "templates/earnings_wire/earnings_wire_article.html.j2").read_text(
        encoding="utf-8"
    )
    index = (repo / "templates/earnings_wire/earnings_wire_index.html.j2").read_text(
        encoding="utf-8"
    )
    facts = (repo / "templates/earnings_wire/_facts.html.j2").read_text(encoding="utf-8")
    css = (repo / "templates/earnings_wire/earnings-wire.css").read_text(encoding="utf-8")

    assert "{% block breadcrumb %}{% endblock %}" in article
    assert article.count('<nav class="ewa-crumb"') == 1
    assert 'aria-label="Breadcrumb"' in article
    assert 'aria-label="{{ t(' not in article
    assert 'aria-current="page"' in article
    assert '<blockquote lang="en">' in facts
    assert '<blockquote lang="en">' in index
    assert "overflow-x:auto" in css
    assert "justify-content:flex-start" in css


def test_public_wire_workflow_has_upstream_trigger_and_hourly_backstop() -> None:
    repo = Path(__file__).resolve().parents[1]
    workflow = (repo / ".github" / "workflows" / "earnings-public-wire.yml").read_text(encoding="utf-8")
    robots = (repo / "site" / "robots.txt").read_text(encoding="utf-8")
    assert "workflow_run:" in workflow
    assert "push:" in workflow
    assert 'workflows: ["earnings-story-packets", "company-intelligence"]' in workflow
    assert 'cron: "47 * * * *"' in workflow
    assert "python -m scripts.build_earnings_public_wire" in workflow
    assert "--private-out-dir" in workflow
    assert "python -m scripts.publish_earnings_private_store" in workflow
    assert "git add site/stocks/earnings" in workflow
    assert "site/premiumdata/earnings" not in workflow
    assert "data/earnings_public_wire" not in workflow
    assert "git add site/stocks/earnings site/sitemap.xml" not in workflow
    assert "--offline" not in workflow
    assert 'push_on_main_ok' in workflow
    assert 'push_retry_init "earnings public wire"' in workflow
    assert "while push_attempt" in workflow
    assert "push_fetch_main_for_rebase" in workflow
    assert "git reset --hard origin/main" in workflow
    assert "git clean -fd -- site/stocks/earnings" in workflow
    assert "push_staged_clean site/stocks/earnings" in workflow
    assert workflow.index("python -m scripts.publish_earnings_private_store") < workflow.index(
        "git add site/stocks/earnings"
    )
    assert workflow.index("while push_attempt") < workflow.index("python -m scripts.build_earnings_public_wire")
    assert workflow.index("git reset --hard origin/main") < workflow.index("python -m scripts.build_earnings_public_wire")
    assert "git pull --rebase" not in workflow
    assert "push_abort_rebase" not in workflow
    assert "push_do origin HEAD:main" in workflow
    assert "push_backoff" in workflow
    assert "secrets.ADMIN_GH_TOKEN" in workflow
    assert "ADMIN_GH_TOKEN is required to publish through the main freeze" in workflow
    assert "Sitemap: https://www.mastermind-x.com/stocks/earnings/sitemap.xml" in robots


def test_public_wire_checkout_materializes_required_full_tree_without_blobless_lazy_fetch() -> None:
    """The publisher consumes the full tree; fetch it once as a shallow pack.

    `filter: blob:none` without a sparse profile still checks out every tracked
    path, but materializes the blobs one-by-one. Production run 35020030398 spent
    13m09s in checkout before the bounded two-attempt publication loop began.
    """
    repo = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load(
        (repo / ".github" / "workflows" / "earnings-public-wire.yml").read_text(
            encoding="utf-8"
        )
    )
    checkout = next(
        step
        for step in workflow["jobs"]["publish"]["steps"]
        if step.get("uses") == "actions/checkout@v4"
    )
    options = checkout["with"]

    assert options["fetch-depth"] == 1
    assert "filter" not in options


def test_public_wire_retry_budget_covers_consecutive_fresh_main_regenerations() -> None:
    """The 2,400s loop must survive more than two consecutive ref races.

    Production run 35161404497 completed two full builds and private promotions,
    then lost both pushes to ordinary main contention.  Four allowed attempts
    preserve an initial try plus three bounded regenerations.  The audited
    attempt ceiling, loop budget, and outer timeout retain explicit margins.
    """
    repo = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load(
        (repo / ".github" / "workflows" / "earnings-public-wire.yml").read_text(encoding="utf-8")
    )
    job = workflow["jobs"]["publish"]
    publish = next(step for step in job["steps"] if step.get("name") == "regenerate current wire from latest main and publish")
    run = publish["run"]

    audited_max_attempt_seconds = 9 * 60
    assert job["timeout-minutes"] == 50
    assert "PUSH_BUDGET_SECS=2400" in run
    assert "PUSH_MAX_ATTEMPTS=4" in run
    assert run.index("PUSH_BUDGET_SECS=2400") < run.index('push_retry_init "earnings public wire"')
    assert run.index("PUSH_MAX_ATTEMPTS=4") < run.index('push_retry_init "earnings public wire"')
    assert 4 * audited_max_attempt_seconds < 2400
    assert 2400 + 10 * 60 == job["timeout-minutes"] * 60
    assert run.index("git reset --hard origin/main") < run.index(
        "python -m scripts.build_earnings_public_wire"
    )
    assert run.index("python -m scripts.publish_earnings_private_store") < run.index(
        "git add site/stocks/earnings"
    )
    assert "git add site/stocks/earnings site/premiumdata/earnings" not in run
    assert "git pull --rebase" not in run
    assert "push_abort_rebase" not in run

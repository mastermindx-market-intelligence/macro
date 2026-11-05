"""C19 WP12 proof module for event evolution across chained generations and views.

effective_at is PINNED as availability time (resolution.py ~:256), not
redefined here. Negative (a) "proposal treated as enacted policy" is NOT
MODELLED by the results carrier (no proposal/enacted vocabulary on main) —
receiver WP15. Negative (b) "framework ceiling treated as revenue" is NOT
MODELLED (no financial arithmetic in the event plane) — receiver WP15. A
materialized diff artifact is deferred to the #7426 clock-index owner; the
diff here is computed in-test only. The public teaser gains nothing (teaser
law intact).
"""
from __future__ import annotations

import gzip
import io
import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

import pytest

from app.company_intelligence import _public_workspace_glance
from engine.company_intelligence.documents import DocumentRevisionChain, SourceDocument
from engine.company_intelligence.event_workspace import (
    AAPL_ACCESSION,
    AAPL_CALL_DATE,
    AAPL_CIK,
    FLAGSHIP_EVENT_ID,
    LIVE_NARRATIVE_ALIAS,
    apple_registry,
    flagship_fiscal_period,
    write_workspace_generation,
)
from engine.company_intelligence.event_workspace_build import build_event_workspace
from engine.company_intelligence.events import CompanyEvent, EventError, FiscalPeriod, quarantine_verdict
from engine.company_intelligence.resolution import EventObservation
from engine.earnings_release.binding import collapse_release_events, revision_from_submissions_row
from engine.earnings_transcript_intake import TranscriptRef, canonical_body_sha256
from engine.neuralweb import company_intelligence_reader as reader
from scripts.publish_company_intelligence_r2 import publish_event_workspaces
from scripts.refresh_event_workspaces import refresh


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "company_intelligence"
EXHIBIT = FIXTURES / "aapl_fy2026_q3_ex99_1.htm"
TRANSCRIPT = FIXTURES / "aapl_fy2026_q3.json.gz"
FILING = FIXTURES / "aapl_fy2026_q3_filing.json"
COLLECTOR = FIXTURES / "aapl_edgar_8k_collector_legacy.json"
BASE = "https://company-intelligence.example/company_intelligence"
CLOCK = "2026-08-16T18:00:00Z"
WS_MARKER = "company_intelligence/event_workspaces/manifest.json"

_DHI_EVENT_ID = "evt_cik0000882184_2026q3_results"
_DHI_ORIGINAL_ACCESSION = "0000882184-26-000092"
_DHI_AMENDMENT_ACCESSION = "0000882184-26-000093"
_DHI_ORIGINAL_SHA = "a" * 64
_DHI_AMENDMENT_SHA = "b" * 64
_DHI_ORIGINAL_AVAILABLE = "2026-07-21T16:30:00Z"
_DHI_AMENDMENT_AVAILABLE = "2026-07-22T12:00:00Z"

ARCHIVE_BASE = (
    f"https://www.sec.gov/Archives/edgar/data/{int(AAPL_CIK)}/{AAPL_ACCESSION.replace('-', '')}"
)
HEADERS_URL = f"{ARCHIVE_BASE}/{AAPL_ACCESSION}-index-headers.html"
EXHIBIT_NAME = "a8-kex991q3202606272026.htm"
EXHIBIT_URL = f"{ARCHIVE_BASE}/{EXHIBIT_NAME}"
SUBMISSIONS_URL = f"https://data.sec.gov/submissions/CIK{AAPL_CIK}.json"


# ---------------------------------------------------------------------------
# DHI two-revision idiom (re-implemented privately; do not import helpers
# from tests/test_refresh_event_workspaces.py). refresh() is the path that
# actually chains: write_workspace_generation(out, mapping) defaults
# previous_generation_id=None (event_workspace.py:649-650) and records only
# the caller-supplied predecessor at event_workspace.py:743. refresh() reads
# the current marker and passes it in at refresh_event_workspaces.py:1836-1855.
# ---------------------------------------------------------------------------


class _PreconditionFailed(RuntimeError):
    response = {"Error": {"Code": "PreconditionFailed"}, "ResponseMetadata": {"HTTPStatusCode": 412}}


class _FakeR2:
    def __init__(
        self,
        remote_manifest: dict | None = None,
        objects: dict[str, tuple[bytes, dict]] | None = None,
        *,
        marker_key: str = WS_MARKER,
        conflict_on_cas: bool = False,
    ) -> None:
        self.marker_key = marker_key
        self.remote_manifest = remote_manifest
        self.objects = dict(objects or {})
        self.puts: list[tuple[str, dict]] = []
        self.conflict_on_cas = conflict_on_cas

    def get_object(self, *, Bucket, Key):
        if Key == self.marker_key and self.remote_manifest is not None:
            return {
                "Body": io.BytesIO(json.dumps(self.remote_manifest).encode()),
                "ETag": "prior-etag",
            }
        if Key in self.objects:
            body, _metadata = self.objects[Key]
            return {"Body": io.BytesIO(body)}
        raise RuntimeError("missing")

    def head_object(self, *, Bucket, Key):
        if Key in self.objects:
            body, metadata = self.objects[Key]
            return {"Metadata": metadata, "ContentLength": len(body)}
        raise RuntimeError("missing")

    def put_object(self, **kwargs):
        key = kwargs["Key"]
        if kwargs.get("IfMatch") and self.conflict_on_cas:
            raise _PreconditionFailed()
        if kwargs.get("IfNoneMatch") == "*" and (
            key in self.objects or (key == self.marker_key and self.remote_manifest is not None)
        ):
            raise _PreconditionFailed()
        self.puts.append((key, kwargs))
        body = kwargs["Body"]
        assert isinstance(body, bytes)
        self.objects[key] = (body, dict(kwargs.get("Metadata") or {}))
        if key == self.marker_key:
            self.remote_manifest = json.loads(body.decode("utf-8"))


def _transcript() -> tuple[dict, str]:
    raw = gzip.decompress(TRANSCRIPT.read_bytes())
    payload = json.loads(raw.decode("utf-8"))
    return payload, canonical_body_sha256(payload)


def _index_payload(tx_sha: str) -> dict:
    return {
        "schema": "mastermind.tx-index/v1",
        "symbols": {"AAPL": ["2026Q3"]},
        "revisions": {LIVE_NARRATIVE_ALIAS: tx_sha},
        "dates": {LIVE_NARRATIVE_ALIAS: "2026-07-30"},
        "body_count": 1,
        "symbol_count": 1,
        "generated_at": "2026-08-16T23:51:18Z",
    }


def _submissions() -> dict:
    return {
        "cik": AAPL_CIK,
        "filings": {
            "recent": {
                "accessionNumber": [AAPL_ACCESSION],
                "filingDate": ["2026-07-30"],
                "acceptanceDateTime": ["2026-07-30T16:30:00.000Z"],
                "reportDate": ["2026-06-27"],
                "form": ["8-K"],
                "primaryDocument": ["aapl-20260730.htm"],
                "items": ["2.02,9.01"],
            }
        },
    }


def _headers_html() -> str:
    return (
        "<HTML><HEAD><TITLE>SEC EDGAR Submission</TITLE></HEAD><BODY><PRE>"
        "&lt;DOCUMENT&gt;\n&lt;TYPE&gt;8-K\n"
        "&lt;FILENAME&gt;aapl-20260730.htm\n&lt;/DOCUMENT&gt;\n"
        f"&lt;DOCUMENT&gt;\n&lt;TYPE&gt;EX-99.1\n&lt;FILENAME&gt;{EXHIBIT_NAME}\n"
        "&lt;/DOCUMENT&gt;\n"
        "</PRE></BODY></HTML>"
    )


def _http_get_factory(exhibit_body: str | None = None):
    exhibit = (exhibit_body if exhibit_body is not None else EXHIBIT.read_text(encoding="utf-8")).encode("utf-8")
    submissions = json.dumps(_submissions()).encode("utf-8")
    headers = _headers_html().encode("utf-8")

    def http_get(url: str) -> tuple[int, bytes]:
        if url == SUBMISSIONS_URL:
            return 200, submissions
        if url == HEADERS_URL:
            return 200, headers
        if url == EXHIBIT_URL:
            return 200, exhibit
        return 404, b""

    return http_get


def _tx_fetchers():
    payload, tx_sha = _transcript()
    index = _index_payload(tx_sha)

    def fetch_index(_base: str) -> dict:
        return index

    def fetch_body(_base: str, ref: TranscriptRef) -> dict:
        if ref.pair != LIVE_NARRATIVE_ALIAS:
            raise ValueError(f"unexpected pair {ref.pair}")
        if ref.body_sha256 != tx_sha:
            raise ValueError(f"transcript body hash mismatch: {ref.body_sha256}")
        return payload

    return fetch_index, fetch_body, tx_sha


def _refresh(tmp_path: Path, fake: _FakeR2, **kwargs):
    fetch_index, fetch_body, _tx_sha = _tx_fetchers()
    return refresh(
        tmp_path,
        out_dir=tmp_path,
        http_get=kwargs.get("http_get", _http_get_factory()),
        fetch_index=fetch_index,
        fetch_body_fn=fetch_body,
        prior_workspace=kwargs.get("prior_workspace"),
        homebuilder_carry_forward_loader=kwargs.get(
            "homebuilder_carry_forward_loader", lambda ticker: None
        ),
        publish_generation=lambda out_dir, dry_run=False: publish_event_workspaces(
            out_dir, dry_run=dry_run, s3=fake, bucket="bucket"
        ),
        dry_run=kwargs.get("dry_run", False),
        current_marker_loader=kwargs.get("current_marker_loader", lambda: None),
        homebuilder_discovery=kwargs.get("homebuilder_discovery", lambda ticker, **_kw: []),
    )


def _marker(tmp_path: Path) -> dict:
    return json.loads((tmp_path / "event_workspaces" / "manifest.json").read_text(encoding="utf-8"))


def _stub_dhi_revision(
    *,
    event_id: str = _DHI_EVENT_ID,
    source_available_at: str,
    source_sha256: str,
    state: str = "complete",
    accession: str = _DHI_ORIGINAL_ACCESSION,
) -> dict:
    return {
        "schema": "event_workspace.v1",
        "event_id": event_id,
        "aliases": [],
        "issuer": {"company_id": "cik:0000882184", "display_name": "D.R. Horton, Inc.", "listings": []},
        "fiscal_period": {"year": 2026, "quarter": 3, "calendar_end": "2026-06-30"},
        "lifecycle": {
            "state": state,
            "observed_at": source_available_at,
            "source_available_at": source_available_at,
        },
        "completeness": {},
        "facts": [],
        "deltas": [],
        "guidance": [],
        "claims": [],
        "sources": [{
            "kind": "issuer_release",
            "document_id": "doc:1",
            "filing_key": {"cik": "0000882184", "accession": accession},
            "source_sha256": source_sha256,
            "form": "8-K",
            "url": None,
            "receipt_state": "byte_replayed",
        }],
        "warnings": [],
        "generation_id": "",
        "generated_at": source_available_at,
        "authority": "context_only",
        "prophet_flags": {
            "may_rank": False,
            "may_size": False,
            "may_gate": False,
            "prophet_authority": False,
        },
        "claim_citations_pending": False,
        "qa_exchanges": [],
    }


def _dhi_workspace(tmp_path: Path, generation_id: str) -> dict:
    return json.loads(
        (
            tmp_path
            / "event_workspaces"
            / "generations"
            / generation_id
            / "workspaces"
            / f"{_DHI_EVENT_ID}.json"
        ).read_text(encoding="utf-8")
    )


def _dhi_manifest(tmp_path: Path, generation_id: str) -> dict:
    return json.loads(
        (
            tmp_path / "event_workspaces" / "generations" / generation_id / "manifest.json"
        ).read_text(encoding="utf-8")
    )


def _publish_dhi_chained_generations(tmp_path: Path) -> tuple[str, str]:
    """Publish DHI original then amendment through refresh() (the path that chains)."""
    fake = _FakeR2()
    original = _stub_dhi_revision(
        source_available_at=_DHI_ORIGINAL_AVAILABLE,
        source_sha256=_DHI_ORIGINAL_SHA,
        accession=_DHI_ORIGINAL_ACCESSION,
    )
    amendment = _stub_dhi_revision(
        source_available_at=_DHI_AMENDMENT_AVAILABLE,
        source_sha256=_DHI_AMENDMENT_SHA,
        state="corrected",
        accession=_DHI_AMENDMENT_ACCESSION,
    )

    def stub_discovery(ticker: str, **_kwargs) -> list[tuple[str, dict]]:
        if ticker == "DHI":
            return [(_DHI_EVENT_ID, original), (_DHI_EVENT_ID, amendment)]
        return []

    assert _refresh(tmp_path, fake, homebuilder_discovery=stub_discovery) == 0
    final_marker = _marker(tmp_path)
    amendment_generation_id = final_marker["generation_id"]
    original_generation_id = next(
        path.name
        for path in sorted((tmp_path / "event_workspaces" / "generations").iterdir())
        if path.name != amendment_generation_id
    )
    return original_generation_id, amendment_generation_id


# ---------------------------------------------------------------------------
# AAPL flagship helpers (re-implemented privately from the event-workspace
# flagship tests). Used for ticker / research / glance views.
# ---------------------------------------------------------------------------


def _filing() -> dict:
    return json.loads(FILING.read_text(encoding="utf-8"))


def _flagship_transcript() -> tuple[dict, str]:
    raw = gzip.decompress(TRANSCRIPT.read_bytes())
    return json.loads(raw.decode("utf-8")), sha256(raw).hexdigest()


def _collector_rows() -> list[dict]:
    return [json.loads(COLLECTOR.read_text(encoding="utf-8"))]


def _build_flagship(
    *,
    exhibit_body: str | None = None,
    prior_sha: str | None = None,
    prior_state: str | None = None,
    filing_overrides: dict | None = None,
) -> dict:
    tx, tx_sha = _flagship_transcript()
    filing = _filing()
    if filing_overrides:
        filing = {**filing, **filing_overrides}
    return build_event_workspace(
        registry=apple_registry(),
        ticker="AAPL",
        asof=AAPL_CALL_DATE,
        fiscal_period=flagship_fiscal_period(),
        exhibit_body=exhibit_body if exhibit_body is not None else EXHIBIT.read_text(encoding="utf-8"),
        filing=filing,
        transcript=tx,
        transcript_sha256=tx_sha,
        observed_at=CLOCK,
        source_available_at="2026-07-30T16:30:00Z",
        collector_rows=_collector_rows(),
        wire_record_found=False,
        prior_source_sha256=prior_sha,
        prior_lifecycle_state=prior_state,
    )


def _published_workspaces(tmp_path: Path, *payloads: dict) -> dict[str, bytes]:
    out = tmp_path / "company_intelligence"
    mapping = {payload["event_id"]: payload for payload in payloads}
    generation = write_workspace_generation(out, mapping)
    generation_id = generation.name
    files = {
        f"{BASE}/event_workspaces/manifest.json": (out / "event_workspaces" / "manifest.json").read_bytes(),
        f"{BASE}/event_workspaces/generations/{generation_id}/manifest.json": (
            generation / "manifest.json"
        ).read_bytes(),
    }
    for event_id in mapping:
        files[f"{BASE}/event_workspaces/generations/{generation_id}/workspaces/{event_id}.json"] = (
            generation / "workspaces" / f"{event_id}.json"
        ).read_bytes()
    return files


def _wire_remote(monkeypatch, files: dict[str, bytes]) -> list[str]:
    calls: list[str] = []
    reader.clear_company_intelligence_cache()
    monkeypatch.setattr(reader, "_public_base_url", lambda: BASE)

    def fake_fetch(url: str, *, limit: int) -> bytes:
        calls.append(url)
        assert url in files, url
        assert len(files[url]) <= limit
        return files[url]

    monkeypatch.setattr(reader, "_fetch_bytes", fake_fetch)
    return calls


def _glance_denylist_tokens(workspace: dict) -> tuple[str, ...]:
    source = (workspace.get("sources") or [{}])[0]
    accession = str((source.get("filing_key") or {}).get("accession") or "")
    source_hash = str(source.get("source_sha256") or "")
    tokens = [
        "r2.dev",
        "workspace_url",
        "marker_url",
        "source_sha256",
        "text_sha256",
        "segment_sha256",
        "span_start_byte",
        "locator",
        "score_overlay",
        "prophet",
        "http://",
        "https://",
        "previous_generation_id",
        "history",
        "receipt_id",
        AAPL_ACCESSION,
    ]
    if accession:
        tokens.append(accession)
    if source_hash:
        tokens.append(source_hash)
    return tuple(tokens)


# ---------------------------------------------------------------------------
# E1
# ---------------------------------------------------------------------------


def test_corrected_generation_chains_to_original(tmp_path: Path) -> None:
    original_id, amendment_id = _publish_dhi_chained_generations(tmp_path)
    amendment_manifest = _dhi_manifest(tmp_path, amendment_id)

    assert amendment_id != original_id
    assert amendment_manifest["previous_generation_id"] == original_id
    walked = amendment_manifest["previous_generation_id"]
    assert walked == original_id
    assert _dhi_manifest(tmp_path, walked)["generation_id"] == original_id


# ---------------------------------------------------------------------------
# E2
# ---------------------------------------------------------------------------


def test_what_changed_is_computable_from_chained_generations(tmp_path: Path) -> None:
    original_id, amendment_id = _publish_dhi_chained_generations(tmp_path)
    original_ws = _dhi_workspace(tmp_path, original_id)
    amendment_ws = _dhi_workspace(tmp_path, amendment_id)

    original_source = original_ws["sources"][0]
    amendment_source = amendment_ws["sources"][0]
    assert original_source["filing_key"]["accession"] == _DHI_ORIGINAL_ACCESSION
    assert amendment_source["filing_key"]["accession"] == _DHI_AMENDMENT_ACCESSION
    assert original_source["source_sha256"] == _DHI_ORIGINAL_SHA
    assert amendment_source["source_sha256"] == _DHI_AMENDMENT_SHA
    assert original_ws["lifecycle"]["state"] == "complete"
    assert amendment_ws["lifecycle"]["state"] == "corrected"

    # Original evidence stays readable after the correction (not erased).
    assert original_source["filing_key"]["accession"] == _DHI_ORIGINAL_ACCESSION
    assert original_source["source_sha256"] == _DHI_ORIGINAL_SHA
    assert (
        tmp_path / "event_workspaces" / "generations" / original_id / "workspaces" / f"{_DHI_EVENT_ID}.json"
    ).is_file()


# ---------------------------------------------------------------------------
# E3
# ---------------------------------------------------------------------------


def test_ticker_and_research_views_read_same_generation(tmp_path: Path, monkeypatch) -> None:
    flagship = _build_flagship()
    files = _published_workspaces(tmp_path, flagship)
    _wire_remote(monkeypatch, files)

    ticker_view = reader.read_current_event_workspace({"ticker": "AAPL"})
    research_view = reader.read_event_workspace({"event_id": FLAGSHIP_EVENT_ID})
    assert ticker_view["available"] is True
    assert research_view["available"] is True
    ticker_generation = ticker_view["workspace"]["generation_id"]
    research_generation = research_view["workspace"]["generation_id"]
    assert ticker_generation == research_generation
    glance = _public_workspace_glance(ticker_view)
    assert glance["generation_id"] == ticker_generation


# ---------------------------------------------------------------------------
# E4
# ---------------------------------------------------------------------------


def test_public_glance_stays_teaser_after_correction(tmp_path: Path, monkeypatch) -> None:
    original = _build_flagship()
    original_sha = original["_source_sha256"]
    amended_body = EXHIBIT.read_text(encoding="utf-8") + "\n<!-- restatement -->\n"
    corrected = _build_flagship(exhibit_body=amended_body, prior_sha=original_sha)
    files = _published_workspaces(tmp_path, corrected)
    _wire_remote(monkeypatch, files)

    ticker_view = reader.read_current_event_workspace({"ticker": "AAPL"})
    assert ticker_view["available"] is True
    workspace = ticker_view["workspace"]
    assert workspace["lifecycle"]["state"] == "corrected"
    glance = _public_workspace_glance(ticker_view)
    assert glance["lifecycle_state"] == "corrected"
    assert glance["generation_id"] == workspace["generation_id"]

    dumped = json.dumps(glance, sort_keys=True, ensure_ascii=False)
    for forbidden in _glance_denylist_tokens(workspace):
        assert forbidden not in dumped, f"forbidden token {forbidden!r} found in glance"
    assert "history" not in glance
    assert "previous_generation_id" not in glance
    assert "receipt" not in glance


# ---------------------------------------------------------------------------
# E5
# ---------------------------------------------------------------------------


def _observation(*, effective_at: object) -> EventObservation:
    document = SourceDocument(
        document_id="doc_r1",
        event_id=FLAGSHIP_EVENT_ID,
        document_kind="release",
        source_class="issuer_release",
        content_sha256="c" * 64,
        revision=1,
    )
    return EventObservation(
        company_id="cik:0000320193",
        fiscal_period=FiscalPeriod(year=2026, quarter=3),
        tickers=("AAPL",),
        revisions=DocumentRevisionChain(revisions=(document,)),
        observation_ref="obs_e5",
        effective_at=effective_at,
    )


def test_future_effective_date_is_not_a_leak_when_available() -> None:
    clock = datetime(2026, 7, 21, 16, 30, tzinfo=timezone.utc)
    available = datetime(2026, 7, 21, 16, 30, tzinfo=timezone.utc)
    future = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)

    available_stamps = _observation(effective_at=available).availability_stamps()
    assert available_stamps["event.effective_at"] == available
    assert "scheduled_at" not in available_stamps
    assert quarantine_verdict(available_stamps, observed_at=clock) is None

    future_stamps = _observation(effective_at=future).availability_stamps()
    verdict = quarantine_verdict(future_stamps, observed_at=clock)
    assert verdict is not None
    assert verdict.offending_field == "event.effective_at"


# ---------------------------------------------------------------------------
# E6
# ---------------------------------------------------------------------------


def test_syndicated_copy_does_not_mint_independent_event() -> None:
    original = revision_from_submissions_row(
        cik=882184,
        row={
            "accessionNumber": _DHI_ORIGINAL_ACCESSION,
            "form": "8-K",
            "filingDate": "2026-07-21",
            "acceptanceDateTime": "2026-07-21T16:30:00Z",
            "reportDate": "2026-06-30",
        },
        source_sha256=_DHI_ORIGINAL_SHA,
    )
    # A plain 8-K that supersedes a revision already held is a syndicated copy,
    # not a new event (binding.py:365-371, reason="supersedes_without_amending").
    syndicated = revision_from_submissions_row(
        cik=882184,
        row={
            "accessionNumber": "0000882184-26-000099",
            "form": "8-K",
            "filingDate": "2026-07-21",
            "acceptanceDateTime": "2026-07-21T17:00:00Z",
            "reportDate": "2026-06-30",
        },
        source_sha256="c" * 64,
        supersedes_source_sha256=_DHI_ORIGINAL_SHA,
    )
    result = collapse_release_events([original, syndicated])
    assert len(result.events) == 1
    assert len(result.events[0].revisions) == 1
    assert result.events[0].original.filing_key.accession == _DHI_ORIGINAL_ACCESSION
    assert result.collapsed
    assert result.collapsed[0].reason == "supersedes_without_amending"
    assert "0000882184-26-000099" in result.collapsed[0].filing_key


# ---------------------------------------------------------------------------
# E7
# ---------------------------------------------------------------------------


def test_retraction_and_illegal_transitions_are_not_erasure(tmp_path: Path) -> None:
    period = FiscalPeriod(year=2026, quarter=3)
    distributed = CompanyEvent.create(
        company_id=320193,
        fiscal_period=period,
        state="distributed",
    )
    corrected = distributed.apply_transition(
        "corrected",
        observed_at=_DHI_AMENDMENT_AVAILABLE,
        source_available_at=_DHI_AMENDMENT_AVAILABLE,
    )
    assert corrected.state == "corrected"
    assert corrected.event_id == distributed.event_id

    for terminal in ("superseded", "cancelled"):
        event = CompanyEvent.create(
            company_id=320193,
            fiscal_period=period,
            state=terminal,
        )
        with pytest.raises(EventError, match="illegal transition"):
            event.apply_transition(
                "corrected",
                observed_at=_DHI_AMENDMENT_AVAILABLE,
                source_available_at=_DHI_AMENDMENT_AVAILABLE,
            )

    original_id, amendment_id = _publish_dhi_chained_generations(tmp_path)
    amendment_manifest = _dhi_manifest(tmp_path, amendment_id)
    assert amendment_manifest["previous_generation_id"] == original_id
    assert _dhi_workspace(tmp_path, original_id)["lifecycle"]["state"] == "complete"

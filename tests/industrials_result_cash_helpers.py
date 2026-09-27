"""SYNTHETIC result-to-cash test fixtures; test-only, never product code.

The comparison contract is exactly ``receipt_id`` (str), ``purpose`` (str),
``operand_refs`` (ordered owner refs), ``checked`` with ``basis``,
``currency``, ``scale``, ``duration``, ``perimeter``, ``definition`` and
``source_mode`` booleans, ``unknowns`` (field names), and ``transformations``
whose entries each contain ``kind`` (str), ``factor`` (decimal text) and
``lineage`` (str).  It precedes T04's production constructor.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from engine.earnings_narrative.private_publication import (
    _pointer_for,
    _put_verified,
    prepare_private_publication,
    validate_private_manifest,
    validate_private_pointer,
)
from engine.earnings_narrative.context_packets import (
    _context_id,
    canonical_json_bytes as _context_canonical_json_bytes,
)
from engine.company_intelligence.documents import ABSENCE_REASONS


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "industrials_result_cash"
FIXTURE_NAMES = frozenset(path.stem for path in FIXTURE_DIR.glob("*.json"))
_COMPARISON_PURPOSES = frozenset(
    {"same_period", "year_over_year", "final_vs_preview", "segment_bridge", "rollforward"}
)


def load_case(name: str) -> dict[str, Any]:
    """Return a fresh synthetic fixture and refuse every non-synthetic value."""
    # Mirrors Semiconductor B's unmerged test loader: fixture trust is explicit.
    if name not in FIXTURE_NAMES:
        raise KeyError(f"unknown fixture {name!r}; known names: {', '.join(sorted(FIXTURE_NAMES))}")
    value = json.loads((FIXTURE_DIR / f"{name}.json").read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("synthetic") is not True:
        raise ValueError("fixture must explicitly be synthetic")
    return deepcopy(value)


case = load_case


def cell(value: str, **overrides: Any) -> dict[str, Any]:
    """Build one native-shaped synthetic financial operand.

    ``unit`` is authoritative for the operand's reporting unit; ``scale`` is
    always 1 in this corpus (raw decimal text carries the magnitude, never a
    scaled multiplier).
    """
    if isinstance(value, (float, bool)) or not isinstance(value, str):
        raise TypeError("cell value must be decimal text")
    try:
        Decimal(value)
    except InvalidOperation as exc:
        raise TypeError("cell value must be decimal text") from exc
    operand: dict[str, Any] = {
        "owner_ref": "synthetic:cell:default",
        "revision": "r1",
        "digest": "a" * 64,
        "semantic_selector": {"statement": "cash-flow", "row": "operating-cash", "column": "quarter"},
        "value": value,
        "metric": "operating_cash_flow",
        "unit": "USD_millions",
        "scale": 1,
        "currency": "USD",
        "stock_or_flow": "flow",
        "period": {"start": "2026-04-03", "end": "2026-07-03", "fiscal_label": "FY2026 Q2", "duration": "quarter"},
        "business_dimensions": {"segment": "testing"},
        "basis": {"accounting": "GAAP", "recast": "as_reported"},
        "source_mode": "release",
        "quality": {"rights_profile": "rp_public_primary_v1", "rights_state": "public_primary", "definition": "cash_generated_by_operations"},
    }
    operand.update(overrides)
    return operand


def typed_absence(reason: str) -> dict[str, str]:
    """Return the owner's only allowed typed-absence shape."""
    if reason not in ABSENCE_REASONS:
        raise ValueError("unknown typed absence reason")
    return {"absence": reason}


def comparison(purpose: str, cells: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Build the closed T04 qualification receipt without qualifying meaning."""
    if purpose not in _COMPARISON_PURPOSES:
        raise ValueError(f"unknown comparison purpose: {purpose}")
    operands = list(cells)
    if not operands:
        raise ValueError("comparison requires operands")
    refs: list[str] = []
    for operand in operands:
        owner_ref = operand.get("owner_ref")
        if not isinstance(owner_ref, str) or not owner_ref:
            raise TypeError("comparison operand lacks owner_ref")
        refs.append(owner_ref)
    return {
        "receipt_id": "synthetic:comparison:1",
        "purpose": purpose,
        "operand_refs": refs,
        "checked": {name: True for name in ("basis", "currency", "scale", "duration", "perimeter", "definition", "source_mode")},
        "unknowns": [],
        "transformations": [],
    }


def dossier_inputs() -> dict[str, Any]:
    """Return a complete invented event, source and financial bundle."""
    return {
        "synthetic": True,
        "schema": {"role": "synthetic.financial-dossier-input/v1"},
        "subject": {"event_ref": "synthetic:event:flow-q2", "identity": shared_identity()},
        "sources": [case("service_net_gross")["sources"][0]],
        "cells": [cell("21", owner_ref="synthetic:cell:service-net")],
        "dependencies": {"refs": ["synthetic:cell:service-net"], "digests": ["a" * 64]},
        "rights": {"release": {"status": "candidate"}, "private": {"status": "candidate"}},
        "narrative": {"reviewed": True},
        "authority": {"rank": False, "gate": False, "size": False, "originate": False, "entry": False},
    }


def publication_harness() -> Any:
    """Return the six-method synthetic owner-function harness."""
    return _PublicationHarness()


def issuer_registry() -> frozenset[tuple[str, str]]:
    """Closed (company_id, cik) pairs registered by the synthetic corpus.

    Built from the 17 fixtures' ``issuer`` blocks; fixtures whose issuer block
    is null/missing contribute no pair. The validator refuses any well-formed
    10-digit CIK not in this set.
    """
    pairs: set[tuple[str, str]] = set()
    for name in FIXTURE_NAMES:
        value = json.loads((FIXTURE_DIR / f"{name}.json").read_text(encoding="utf-8"))
        if not isinstance(value, Mapping):
            continue
        issuer = value.get("issuer")
        if not isinstance(issuer, Mapping):
            continue
        company_id = issuer.get("company_id")
        external_ids = issuer.get("external_ids")
        if not isinstance(external_ids, Mapping):
            continue
        cik = external_ids.get("cik")
        if not isinstance(company_id, str) or not isinstance(cik, str):
            continue
        pairs.add((company_id, cik))
    return frozenset(pairs)


def shared_identity() -> dict[str, Any]:
    return {
        "company_id": "synthetic:northgate",
        "display_name": "Northgate Testing Services",
        "fiscal_year_end_month": 12,
        "reporting_currency": "USD",
        "listings": [],
        "issuer_kind": "industrial",
        "external_ids": {"cik": "0000987654"},
    }


class _MemoryPublicationStore:
    """Dict-backed store satisfying the full ``StrictBoundedReadStore`` chain.

    Implements every member of ``Store -> StrictReadStore -> StrictBoundedReadStore``
    so ``isinstance(store, StrictBoundedReadStore)`` is true and the owner's
    ``_bounded_read`` check passes. No filesystem, no parent class — the
    harness must never create side-effect bytes on disk in a sparse worktree.
    """

    def __init__(self) -> None:
        self._blobs: dict[str, bytes] = {}
        self._upload_times: dict[str, str] = {}
        self.read_count = 0

    def get_bytes(self, key: str) -> bytes | None:
        self.read_count += 1
        return self._blobs.get(key)

    def get_bytes_strict(self, key: str) -> bytes | None:
        self.read_count += 1
        return self._blobs.get(key)

    def get_bytes_strict_bounded(self, key: str, maximum_bytes: int) -> bytes | None:
        self.read_count += 1
        body = self._blobs.get(key)
        if body is None:
            return None
        if maximum_bytes is not None and len(body) > maximum_bytes:
            raise ValueError(f"object exceeds maximum_bytes: {key!r}")
        return body

    def put_bytes(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> bool:
        del content_type
        self._blobs[key] = data
        self._upload_times[key] = "2026-09-24T00:00:00Z"
        return True

    def exists(self, key: str) -> bool:
        return key in self._blobs

    def list_prefix(self, prefix: str) -> list[str]:
        return sorted(key for key in self._blobs if key.startswith(prefix))

    def upload_time(self, key: str) -> str | None:
        return self._upload_times.get(key)


class _SyntheticClient:
    """Holds a store reference so test_route_unbound_client_causes_no_read can
    assert that a route_unbound .get()/.post() never increments read_count."""

    def __init__(self, store: _MemoryPublicationStore) -> None:
        self._store = store

    def get(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        # Route remains intentionally unbound — no store read may happen here.
        return {"status": "unavailable", "reason": "route_unbound", "status_code": None}

    def post(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {"status": "unavailable", "reason": "route_unbound", "status_code": None}


def _build_minimal_staging_tree(stage_dir: Path) -> None:
    """Write the smallest staging tree that satisfies ``prepare_private_publication``.

    No network, no ``data/`` — the tree is built from synthetic receipts whose
    hashes are computed locally.  The staging tree is local to ``stage_dir``,
    which the test passes via pytest's ``tmp_path``.
    """
    from engine.earnings_narrative.context_packets import (
        EXECUTION_RECEIPT as _CONTEXT_EXEC,
    )

    body = b'{"speaker":"CEO","role":"executive","text":"We delivered 50 million in operating cash."}'
    source_sha256 = sha256(body).hexdigest()
    text = "We delivered 50 million in operating cash."
    text_bytes = text.encode("utf-8")
    text_start = body.index(text_bytes)
    text_end = text_start + len(text_bytes)
    receipt = {
        "source_sha256": source_sha256,
        "segment_index": 0,
        "segment_sha256": source_sha256,
        "segment_bytes": len(body),
        "span_start_byte": text_start,
        "span_end_byte": text_end,
        "text_sha256": sha256(text_bytes).hexdigest(),
    }
    claim_id = "claim_" + "0" * 32
    quote = {
        "claim_id": claim_id,
        "kind": "quote",
        "text": text,
        "receipt": receipt,
    }
    fact = {
        "claim_id": claim_id,
        "quote": quote,
        "speaker": "CEO",
        "role": "executive",
        "chapter": "performance",
        "categories": ["performance"],
        "numeric": [],
    }

    packet: dict[str, Any] = {
        "schema": "earnings.context_packet/v1",
        "context_id": "earnctx_" + "0" * 32,
        "event": {
            "ticker": "AAPL",
            "transcript_id": "abc123",
            "period": "2026Q1",
            "date": "2026-01-30",
        },
        "identities": {
            "article_id": "wirearticle_" + "0" * 32,
            "packet_id": "packet_001",
            "story_id": "story_001",
            "story_revision_id": "revision_001",
        },
        "source": {
            "kind": "transcript",
            "source_sha256": source_sha256,
            "known_at": "2026-02-01T00:00:00Z",
            "correction_status": "current",
        },
        "admission": {
            "promotion_tier": "A",
            "quality_status": "ready",
            "citation_coverage": 1.0,
        },
        "categories": ["performance"],
        "facts": [fact],
        "source_completeness": {
            "release": "not_ingested",
            "filing": "not_ingested",
            "transcript": "present",
            "slides": "not_ingested",
            "consensus": "unlicensed_absent",
        },
        "links": {
            "record": "/stocks/earnings/aapl-abc123-call-record.html",
            "dossier": "/stocks/AAPL.html",
            "terminal": (
                "https://app.mastermind-x.com/terminal?"
                "sym=AAPL&pane=transcripts&tx=abc123"
            ),
        },
        "authority": {
            "class": "context_only",
            "may_add_candidate": False,
            "may_rank": False,
            "may_size": False,
            "may_gate": False,
            "may_escalate": False,
            "prophet_authority": False,
        },
        "execution": dict(_CONTEXT_EXEC),
    }
    unsigned_packet = dict(packet)
    unsigned_packet["context_id"] = "earnctx_" + "0" * 32
    packet["context_id"] = _context_id(unsigned_packet)

    packet_bytes = _context_canonical_json_bytes(packet)
    packet_sha = sha256(packet_bytes).hexdigest()

    manifest: dict[str, Any] = {
        "schema": "earnings.context_manifest/v1",
        "generation_id": "earnctxgen_" + "0" * 32,
        "knowledge_cutoff": "2026-02-01T00:00:00Z",
        "source": {
            "generation_id": "a" * 32,
            "manifest_sha256": source_sha256,
            "wire_manifest_id": "wiremanifest_" + "a" * 32,
        },
        "ticker_count": 1,
        "event_count": 1,
        "objects": {
            "AAPL": {
                "path": "aapl.json",
                "context_id": packet["context_id"],
                "sha256": packet_sha,
                "bytes": len(packet_bytes),
            }
        },
        "execution": dict(_CONTEXT_EXEC),
    }
    unsigned_manifest = dict(manifest)
    unsigned_manifest["generation_id"] = "earnctxgen_" + "0" * 32
    manifest["generation_id"] = (
        "earnctxgen_" + sha256(_context_canonical_json_bytes(unsigned_manifest)).hexdigest()[:32]
    )

    record = {
        "schema": "earnings.tier_payload/v1",
        "page": "earnings_wire_article",
        "slug": "synth-001",
        "required_tier": "essential",
        "public_facts": 1,
        "locked_facts": 1,
        "facts_html": "<p>Test</p>",
        "receipt_rows_html": "<table><tr><td>1</td></tr></table>",
    }

    records_dir = stage_dir / "records"
    context_dir = stage_dir / "context"
    records_dir.mkdir(parents=True, exist_ok=True)
    context_dir.mkdir(parents=True, exist_ok=True)
    (records_dir / "synth-001.json").write_bytes(_context_canonical_json_bytes(record))
    (context_dir / "latest.json").write_bytes(_context_canonical_json_bytes(manifest))
    (context_dir / "aapl.json").write_bytes(_context_canonical_json_bytes(packet))


class _PublicationHarness:
    def __init__(self) -> None:
        self.store = _MemoryPublicationStore()

    @property
    def read_count(self) -> int:
        return self.store.read_count

    def run_refresh(
        self,
        _changes: Mapping[str, str],
        fail_sources: Iterable[str] = (),
    ) -> dict[str, Any]:
        """Inject ``acquire_results_filing`` with a fake ``http_get`` that
        serves the seam's own SEC submissions + SGML + exhibit shape, and
        returns an HTTP 503 for the submissions URL whenever ``fail_sources``
        is non-empty — that is what makes ``fail_sources`` causal: deleting
        the entry flips the result to ``ok`` on the very next call.

        The harness serves ONLY the URLs the real seam reaches for the
        synthetic CIK ``0000987654`` — the submissions JSON (one 8-K Item 2.02
        entry whose ``primaryDocument`` is the bare filename
        ``synthetic-exhibit.htm``, not a URL), that entry's archive
        ``-index-headers.html`` (an SGML manifest naming the same filename under
        EX-99.1), and the exhibit itself. The owner, not the harness, derives the
        SEC Archives URLs from the accession number
        (``.../Archives/edgar/data/987654/<acc_nodash>/<filename>``) — which is
        why the fake matches those two by suffix. Every entry in
        ``fail_sources`` is named as the ``source`` of the typed refusal; the
        first one wins.
        """
        from scripts.refresh_event_workspaces import (
            RefreshError,
            acquire_results_filing,
        )

        failed = sorted(set(fail_sources))
        synthetic_cik = "0000987654"
        submissions_url = "https://data.sec.gov/submissions/CIK0000987654.json"
        exhibit_filename = "synthetic-exhibit.htm"
        # Minimal valid submissions JSON — only the fields
        # ``acquire_results_filing`` and ``submissions_rows`` read:
        #   submissions["filings"]["recent"] with parallel arrays for
        #   form / accessionNumber / filingDate / acceptanceDateTime /
        #   reportDate / items / primaryDocument. One 8-K Item 2.02 entry
        #   whose primaryDocument is the bare exhibit FILENAME — the owner joins
        #   it onto the archive base it derives from the accession number, and
        #   the fake below matches that derived URL by suffix.
        submissions_body = json.dumps({
            "filings": {
                "recent": {
                    "form": ["8-K"],
                    "accessionNumber": ["0000987654-26-000001"],
                    "filingDate": ["2026-09-23"],
                    "acceptanceDateTime": ["2026-09-23T13:30:00Z"],
                    "reportDate": ["2026-09-22"],
                    "items": ["2.02"],
                    "primaryDocument": [exhibit_filename],
                }
            }
        }).encode("utf-8")
        # SGML manifest format the seam parses:
        #   unescaped text split on "<DOCUMENT>" with <TYPE>/<FILENAME> tags.
        index_headers_body = (
            "<DOCUMENT>"
            "<TYPE>EX-99.1\n"
            f"<FILENAME>{exhibit_filename}\n"
            "</DOCUMENT>"
        ).encode("utf-8")
        exhibit_body = (
            b"Three Months Ended September 30, 2026. "
            b"Operating cash flow was 50 million."
        )

        def fake_http_get(url: str) -> tuple[int, bytes]:
            if url == submissions_url:
                if failed:
                    return (503, b"")
                return (200, submissions_body)
            if url.endswith("-index-headers.html"):
                # archive URL = https://www.sec.gov/Archives/edgar/data/987654/...
                return (200, index_headers_body)
            if url.endswith(exhibit_filename):
                # The seam computes the exhibit URL as
                #   f"{archive_base}/{filename}" =
                #   https://www.sec.gov/Archives/edgar/data/987654/<acc_nodash>/synthetic-exhibit.htm
                # — the same exhibit the primaryDocument field named. Serve
                # the synthetic bytes for any URL ending with the named file.
                return (200, exhibit_body)
            return (404, b"")

        try:
            prepared = acquire_results_filing(cik=synthetic_cik, http_get=fake_http_get)
        except RefreshError as exc:
            source = failed[0] if failed else ""
            unavailable: dict[str, Any] = {
                "status": "unavailable",
                "reason": "refresh_source_failed",
                "detail": str(exc),
            }
            if source:
                unavailable["source"] = source
            return unavailable

        return {"status": "ok", **prepared}

    def members(self) -> set[str]:
        return set()

    def publish(self, changes: Mapping[str, Any], *, stage_dir: Path) -> dict[str, Any]:
        """Bind every owner entry point in the owner's real order.

        ``stage_dir`` is the REQUIRED keyword-only argument (a pytest
        ``tmp_path`` in T02/T04). The harness builds a minimal synthetic
        ``records/`` + ``context/`` tree inside it and lets the owner's
        ``prepare_private_publication`` validate it.

        Step 1: ``prepare_private_publication(stage_dir)`` validates a
        locally-built staging tree (records/ + context/) and freezes one
        generation. Step 2: ``_put_verified`` writes every prepared payload
        through the bounded strict store. Step 3: ``validate_private_manifest``
        re-checks the prepared manifest. Step 4: ``validate_private_pointer``
        re-checks the pointer built by the owner's ``_pointer_for``.

        If a precondition beyond ``stage_dir`` is missing, returns the typed
        refusal permitted by the META-CEO ruling.
        """
        del changes
        try:
            _build_minimal_staging_tree(stage_dir)
            prepared = prepare_private_publication(stage_dir)
        except Exception as exc:  # noqa: BLE001
            return {
                "status": "unavailable",
                "reason": "publication_seam_unbound",
                "needed": (
                    "prepare_private_publication(stage_dir) needs a complete "
                    "records/ + context/latest.json + context/<ticker>.json "
                    f"staging tree; got {type(exc).__name__}: {exc}"
                ),
            }

        for artifact in prepared.artifacts:
            body = prepared.payloads[artifact.object_key]
            _put_verified(
                self.store,
                key=artifact.object_key,
                body=body,
                maximum=artifact.maximum_bytes,
            )
        # The owner publishes the manifest via the same _put_verified path.
        _put_verified(
            self.store,
            key=prepared.manifest_key,
            body=prepared.manifest_bytes,
            maximum=len(prepared.manifest_bytes) * 2,
        )

        validated_manifest = validate_private_manifest(prepared.manifest)
        pointer = _pointer_for(prepared)
        validated_pointer = validate_private_pointer(pointer)

        return {
            "status": "ok",
            "generation_id": validated_manifest["generation_id"],
            "manifest_key": prepared.manifest_key,
            "pointer": validated_pointer,
            "read_count": self.store.read_count,
        }

    def client(self, entitled: bool) -> _SyntheticClient:
        del entitled
        return _SyntheticClient(self.store)

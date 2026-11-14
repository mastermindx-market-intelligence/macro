"""Pin SEC segment sources, build segment owner packets, propose activity membership.

Three subcommands (``pin`` / ``packet`` / ``propose``); each writes ONLY under an
explicit ``--out`` directory. This is a thin orchestration over the existing
owners — it never reimplements capture, custody, adoption or the membership CLI:

* ``pin`` reuses the SEC Submissions collector, the filing-manifest spine, the
  bounded archive collector (4 MB primary-document cap, never raised) and ONE
  ``sync_source_roots(..., publish_latest=False)``. It never publishes or moves
  the shared ``fundamental_forensics/sec-source/v1`` ``latest`` pointer.
* ``packet`` reads pinned bytes ONLY through ``PinnedSourceAuthority``, inspects
  via ``inspect_pinned_candidate``, reads current identity through the owner's
  own reader, then ``prepare_segment_input`` / ``adopt_segment_input`` with a
  source-purpose policy shaped like the installed SEC public-filing-fact basis.
* ``propose`` shells out to the unchanged ``propose_activity_membership.py`` CLI.

All refusals are typed; a completed run (even with per-row refusals) exits 0 and
a whole-run failure exits 2. No secret value or filing body byte is ever printed
or written to an output; outputs carry only the labels/figure texts the schemas
already carry, plus hashes and metadata.
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from collectors import edgar_forensics
from collectors.edgar_forensics import SecForensicsCollector, _user_agent
from collectors.sec_document_spine import (
    ArchiveResponseTooLarge,
    SecFilingArchiveCollector,
    persist_filing_manifest,
    read_archive_document,
)
from collectors.sec_request_pacer import SecRequestPacer
from engine.company_intelligence import issuer_disclosure_owner as owner
from engine.company_intelligence import issuer_disclosures as n
from engine.company_intelligence import sec_segment_adoption as segment
from engine.company_intelligence.pinned_relationship_candidates import (
    inspect_pinned_candidate,
)
from engine.company_intelligence.relationship_candidates import (
    SCHEMA as CANDIDATE_SCHEMA,
)
from engine.earnings_release.receipts import receipt_for_char_span
from engine.fundamental_forensics.filing_attestation import (
    PinnedSourceAuthority,
    gzip_stored_byte_ceiling,
)
from engine.fundamental_forensics.sec_document_spine import (
    HARD_MAX_FILING_MANIFEST_BYTES,
    archive_index_document,
    build_filing_manifests,
    documents_from_archive_index,
    manifest_from_json_bytes,
    with_archive_documents,
)
from engine.fundamental_forensics.source_sync import (
    build_private_source_store,
    sync_source_roots,
)

TARGETS_SCHEMA = "theme_graph.segment_source_targets/v1"
REQUEST_SCHEMA = "theme_graph.segment_packet_request/v1"
PIN_REPORT_SCHEMA = "theme_graph.segment_pin_report/v1"
PACKET_REPORT_SCHEMA = "theme_graph.segment_packet_report/v1"
PROPOSE_REPORT_SCHEMA = "theme_graph.segment_propose_report/v1"
_SNAPSHOT_RE = re.compile(r"ffsecsrc_[0-9a-f]{64}")
_TICKER_RE = re.compile(r"[A-Z0-9][A-Z0-9.-]{0,14}")
_ACCESSION_RE = re.compile(r"[0-9]{10}-[0-9]{2}-[0-9]{6}")
_OVER_CAP_FIGURES = re.compile(r"SEC archive response exceeds bounded ingest limit \(([0-9]+) > ([0-9]+)\)")
SIZE_BASIS_DECLARED = "declared_content_length"
SIZE_BASIS_CUT = "bytes_at_cut"


class PacketRefusal(ValueError):
    """Typed per-row packet refusal; never interpolates source prose."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class PacketRequestRefused(ValueError):
    """The whole packet request is refused before anything is written."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def packet_output_stem(row: dict) -> str:
    """Output file stem for one request row: ticker, accession and the disclosed line.

    The readable slug alone could merge two lines that differ only in punctuation,
    so a digest of the exact line text follows it.
    """
    line = row["disclosed_line"]
    slug = re.sub(r"[^A-Za-z0-9]+", "-", line).strip("-")[:48] or "line"
    digest = sha256(line.encode("utf-8")).hexdigest()[:12]
    return f"{row['ticker']}_{row['accession']}_{slug}_{digest}"


# disclosed_line is a segment label copied from the filing and is echoed in the
# packet report, so its length is bounded: a longer value is refused, not cut.
MAX_DISCLOSED_LINE_CHARS = 160

_REFUSAL_CODE_RE = re.compile(r"REFUSED: ([A-Z0-9_]{1,80})(?::|$)")
# The writer's contract: probation.activity_proposal_id is "actprop:" + 24 hex,
# and a proposer only ever writes status PROPOSED.
_PROPOSAL_ID_RE = re.compile(r"actprop:[0-9a-f]{24}")
_PROPOSAL_STATUS_RE = re.compile(r"PROPOSED")


def _refusal_codes(stderr: str) -> list[str]:
    """Only the fixed code token of each REFUSED line; the detail text is dropped."""
    codes = []
    for line in stderr.splitlines():
        match = _REFUSAL_CODE_RE.match(line)
        if line.startswith("REFUSED:"):
            codes.append(match.group(1) if match else "UNPARSED_REFUSAL")
    return codes


def _proposal_result(stdout: str) -> dict | None:
    """The writer's fixed result fields; the ledger path and any other output are dropped."""
    for line in stdout.splitlines():
        try:
            parsed = json.loads(line)
        except ValueError:
            continue
        if not isinstance(parsed, dict):
            continue
        pid, status = parsed.get("proposal_id"), parsed.get("status")
        if not (isinstance(pid, str) and _PROPOSAL_ID_RE.fullmatch(pid)
                and isinstance(status, str) and _PROPOSAL_STATUS_RE.fullmatch(status)):
            continue
        result = {"proposal_id": pid, "status": status}
        for key in ("appended", "unchanged"):
            value = parsed.get(key)
            if type(value) is int and value >= 0:
                result[key] = value
        return result
    return None


def _validate_packet_rows(rows: list) -> list[str]:
    """Check every row's naming fields and refuse colliding output names, before any write."""
    stems = []
    for index, row in enumerate(rows):
        if not (isinstance(row, dict)
                and isinstance(row.get("ticker"), str) and _TICKER_RE.fullmatch(row["ticker"])
                and isinstance(row.get("accession"), str) and _ACCESSION_RE.fullmatch(row["accession"])
                and isinstance(row.get("disclosed_line"), str) and row["disclosed_line"].strip()
                and len(row["disclosed_line"]) <= MAX_DISCLOSED_LINE_CHARS):
            raise PacketRequestRefused(f"PACKET_REQUEST_ROW_{index}_INVALID")
        stem = packet_output_stem(row)
        if stem in stems:
            raise PacketRequestRefused(
                f"PACKET_OUTPUT_NAME_COLLISION_ROWS_{stems.index(stem)}_{index}")
        stems.append(stem)
    return stems


def over_cap_size(exc: BaseException) -> tuple[int | None, str | None]:
    """What the refused fetch already knew about the document's size, and how it knew.

    The archive collector refuses either on the declared Content-Length (reporting
    the declared size) or while streaming (reporting the limit plus one byte, the
    point where the stream was cut). Nothing is downloaded to measure a refused
    document. A declared length of exactly limit+1 cannot be told apart and is
    reported as bytes_at_cut, which is still a true lower bound. Any other refusal
    shape reports no size.
    """
    match = _OVER_CAP_FIGURES.search(str(exc))
    if match is None:
        return None, None
    size, limit = int(match.group(1)), int(match.group(2))
    if size == limit + 1:
        return size, SIZE_BASIS_CUT
    if size > limit + 1:
        return size, SIZE_BASIS_DECLARED
    return None, None


def _canonical(value) -> bytes:
    return n._canonical(value)


# This lane's own run reports (pin/packet/propose) are not disclosure objects, so
# the owner's 16 KB object cap does not bound them: a 51-target pin report is
# larger than that. Same canonical encoding, a separate fixed ceiling.
MAX_REPORT_BYTES = 1024 * 1024
# Room kept for the two snapshot fields a pin report gains only after the sync
# (a fixed-width snapshot id and a UTC clock, ~130 bytes encoded).
REPORT_SNAPSHOT_ALLOWANCE = 256


class ReportRefused(ValueError):
    """A run report is refused (hard ceiling or invalid JSON); nothing more is written."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def report_bytes(report: dict, *, ceiling: int | None = None) -> bytes:
    limit = MAX_REPORT_BYTES if ceiling is None else ceiling
    try:
        raw = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                         allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        raise ReportRefused("REPORT_JSON_INVALID") from None
    if not 0 < len(raw) <= limit:
        raise ReportRefused("REPORT_TOO_LARGE")
    return raw


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _outcome(refused: int, total: int) -> str:
    """complete: every row went through; partial: some did, some were refused; refused: none did."""
    if refused == 0:
        return "complete"
    return "refused" if refused == total else "partial"


def _load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _require_anchor(source: str, anchor: str) -> int:
    """Return the unique position of a literal anchor, or a typed refusal."""
    if not isinstance(anchor, str) or not anchor:
        raise PacketRefusal("ANCHOR_MISSING")
    count = source.count(anchor)
    if count == 0:
        raise PacketRefusal("ANCHOR_MISSING")
    if count > 1:
        raise PacketRefusal("ANCHOR_NOT_UNIQUE")
    return source.index(anchor)


# ---------------------------------------------------------------------------
# pin
# ---------------------------------------------------------------------------

def _load_targets(targets_path: Path) -> list[dict]:
    payload = _load_json(targets_path)
    if not isinstance(payload, dict) or payload.get("schema") != TARGETS_SCHEMA:
        raise ValueError("TARGETS_SCHEMA_INVALID")
    targets = payload.get("targets")
    if not isinstance(targets, list) or not targets:
        raise ValueError("TARGETS_EMPTY")
    seen = set()
    for target in targets:
        if not isinstance(target, dict) or set(target) != {"ticker", "cik", "forms"}:
            raise ValueError("TARGET_SHAPE_INVALID")
        ticker = target["ticker"]
        if ticker in seen:
            raise ValueError("TARGET_DUPLICATE")
        seen.add(ticker)
        if not re.fullmatch(r"[0-9]{10}", str(target["cik"])):
            raise ValueError("TARGET_CIK_INVALID")
        forms = target["forms"]
        if not isinstance(forms, list) or not forms or not set(forms) <= set(n.SEGMENT_FORM_TYPES):
            raise ValueError("TARGET_FORMS_INVALID")
    return targets


def choose_filing(eligible: list[dict]) -> dict:
    """Latest original annual report; an amendment only when no original is eligible.

    A later Part III-only 10-K/A must not displace the 10-K that carries the
    segment note, so originals (forms without "/A") win whenever one exists.
    """
    originals = [m for m in eligible if not m["filing"]["form"].endswith("/A")]
    pool = originals or eligible
    return max(pool, key=_filing_order)


def _filing_order(manifest: dict):
    return (manifest["clocks"]["filed_on"], manifest["filing"]["accession"])


def later_amendments(eligible: list[dict], chosen: dict) -> list[str]:
    """Accessions of eligible "/A" filings later than the chosen one (possible restatements)."""
    return sorted(
        m["filing"]["accession"] for m in eligible
        if m["filing"]["form"].endswith("/A") and _filing_order(m) > _filing_order(chosen)
    )


def _pin_one(target, forensics, archive, raw_root, archive_root, now) -> dict:
    ticker = target["ticker"]
    cik = target["cik"]
    forms = set(target["forms"])
    accession = None
    # None until the filing choice is made: a refusal before that point cannot
    # know which later amendments exist.
    amendments = None

    def refused(code: str, **extra) -> dict:
        return {"ticker": ticker, "cik": cik, "accession": accession, "refusal": code,
                "later_amendments": amendments, **extra}

    try:
        receipt = forensics.fetch(cik, "submissions", retrieved_at=now)
        with gzip.open(raw_root / receipt.object_path, "rb") as handle:
            submissions = json.load(handle)
        manifests = build_filing_manifests(submissions, cik=cik, ticker=ticker, recorded_at=now)
        eligible = [m for m in manifests if m["filing"]["form"] in forms]
        if not eligible:
            amendments = []
            return refused("NO_ELIGIBLE_FILING")
        manifest = choose_filing(eligible)
        amendments = later_amendments(eligible, manifest)
        accession = manifest["filing"]["accession"]
        index_document = archive_index_document(manifest)
        index_receipt = archive.fetch_document(index_document, retrieved_at=now)
        if isinstance(index_receipt, dict):
            return refused("ARCHIVE_INDEX_MISSING")
        index_bytes = read_archive_document(archive_root, index_receipt)
        documents = documents_from_archive_index(manifest, json.loads(index_bytes))
        manifest = with_archive_documents(manifest, documents)
        manifest = archive.fetch_primary_document(
            manifest, retrieved_at=now, max_document_bytes=n.MAX_SEC_SOURCE_BYTES
        )
        primary = next(d for d in manifest["documents"] if d["role"] == "primary")
        if primary["availability"] != "stored":
            return refused("PRIMARY_DOCUMENT_MISSING")
        manifest_key = persist_filing_manifest(archive_root, manifest)
        return {
            "ticker": ticker, "cik": cik, "form": manifest["filing"]["form"],
            "accession": accession, "filed_on": manifest["clocks"]["filed_on"],
            "archive_url": primary["archive_url"], "document_id": primary["document_id"],
            "manifest_key": manifest_key, "raw_sha256": primary["content_sha256"],
            "byte_length": primary["byte_length"],
            # Later amendments the choice rule passed over: a reader must check
            # whether one restates the segment note before this row is used.
            "later_amendments": amendments,
        }
    except ArchiveResponseTooLarge as exc:
        # Only the size the refusal already carried; the message itself (which
        # names the URL) is never written.
        size, basis = over_cap_size(exc)
        return refused("DOCUMENT_OVER_CAP", size_bytes=size, size_basis=basis)
    except edgar_forensics.SecResponseTooLarge:
        return refused("SUBMISSIONS_OVER_CAP")
    except Exception:
        # A per-target failure is a typed skip, never a traceback to stdout and
        # never a reason to retry a refused document at a larger cap.
        return refused("PIN_TARGET_FAILED")


def run_pin(targets_path, raw_root, archive_root, out, *, local_store=None,
            session=None, pacer=None, now=None) -> dict:
    now = now or _utc_now()
    targets = _load_targets(Path(targets_path))
    raw_root = Path(raw_root)
    archive_root = Path(archive_root)
    out = Path(out)
    raw_root.mkdir(parents=True, exist_ok=True)
    archive_root.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    store = build_private_source_store(local_dir=local_store)
    user_agent = _user_agent(ROOT)
    pacer = pacer if pacer is not None else SecRequestPacer(min_interval_seconds=0.12)
    forensics = SecForensicsCollector(raw_root, user_agent=user_agent, session=session, pacer=pacer)
    archive = SecFilingArchiveCollector(
        archive_root, user_agent=user_agent, session=session, pacer=pacer,
        max_document_bytes=n.MAX_SEC_SOURCE_BYTES,
    )
    rows = [_pin_one(target, forensics, archive, raw_root, archive_root, now) for target in targets]
    # Size-check the report BEFORE the sync: a report that would be refused must
    # leave nothing in the store. Only the snapshot fields are added afterwards.
    report_bytes({"schema": PIN_REPORT_SCHEMA, "targets": rows},
                 ceiling=MAX_REPORT_BYTES - REPORT_SNAPSHOT_ALLOWANCE)
    snapshot = sync_source_roots(
        raw_root=raw_root, archive_root=archive_root, store=store,
        snapshot_at=now, publish_latest=False,
    )
    report = {
        "schema": PIN_REPORT_SCHEMA,
        "snapshot_id": snapshot.snapshot_id,
        "snapshot_at": snapshot.snapshot_at,
        "targets": rows,
    }
    (out / "pin_report.json").write_bytes(report_bytes(report))
    return report


# ---------------------------------------------------------------------------
# packet
# ---------------------------------------------------------------------------

def _default_identity_reader(ticker: str) -> dict:
    source = owner.CommittedDisclosureSource(ROOT)
    return owner.context.read_company_context(
        source.identity_owner, ticker, purpose=owner.PURPOSE, audience=owner.AUDIENCE
    )["identity_receipt"]


def _read_pinned_body(authority, manifest_key: str, document_id: str):
    """Return (pinned bytes, canonical archive_url) read ONLY via the authority.

    The archive_url comes from the pinned manifest document itself (the same
    locator the segment-route reference uses), never from the request row, so the
    candidate's source_ref is guaranteed to match the pinned source.
    """
    manifest_read = authority.read_file(
        kind="archive", relative_path=manifest_key, maximum_bytes=HARD_MAX_FILING_MANIFEST_BYTES
    )
    manifest = manifest_from_json_bytes(manifest_read.content)
    selected = [d for d in manifest["documents"] if d["document_id"] == document_id]
    if len(selected) != 1:
        raise PacketRefusal("DOCUMENT_NOT_UNIQUELY_SELECTED")
    document = selected[0]
    if document.get("availability") != "stored" or not isinstance(document.get("retrieval"), dict):
        raise PacketRefusal("DOCUMENT_NOT_STORED")
    retrieval = document["retrieval"]
    read = authority.read_archive_document(
        storage_key=document["storage_key"], expected_receipt=retrieval,
        maximum_bytes=n.MAX_SEC_SOURCE_BYTES,
        maximum_stored_bytes=gzip_stored_byte_ceiling(retrieval["byte_length"]),
    )
    return read.content, document["archive_url"]


def _locate_figures(source: str, body: bytes, row: dict, main_start: int, main_end: int):
    assertion_figures = {}
    figure_spans = {}
    for name in n.SEGMENT_FIGURE_NAMES:
        spec = (row.get("figures") or {}).get(name)
        if spec is None:
            figure_spans[name] = None
            assertion_figures[name] = None
            for suffix in ("text", "sign", "scale"):
                assertion_figures[f"{name}_{suffix}"] = None
            continue
        text, sign, scale, anchor = spec["text"], spec["sign"], spec["scale"], spec["anchor"]
        anchor_pos = _require_anchor(source, anchor)
        search_start = max(anchor_pos + len(anchor), main_start)
        pos = source.find(text, search_start, main_end)
        if pos < 0:
            raise PacketRefusal("FIGURE_TEXT_NOT_FOUND")
        start_byte = len(source[:pos].encode("utf-8"))
        end_byte = len(source[:pos + len(text)].encode("utf-8"))
        figure_spans[name] = {
            "start_byte": start_byte, "end_byte": end_byte,
            "text_sha256": sha256(body[start_byte:end_byte]).hexdigest(),
        }
        derived = (-1 if sign == "-" else 1) * int(text.replace(",", "")) * n.SEGMENT_FIGURE_SCALES[scale]
        assertion_figures[name] = float(derived)
        assertion_figures[f"{name}_text"] = text
        assertion_figures[f"{name}_sign"] = sign
        assertion_figures[f"{name}_scale"] = scale
    return assertion_figures, figure_spans


def _packet_row(row, authority, snapshot_id, identity_reader, identity_observed_at, theme_sources_raw) -> dict:
    ticker = row["ticker"]
    accession = row["accession"]
    body, archive_url = _read_pinned_body(authority, row["manifest_key"], row["document_id"])
    source = body.decode("utf-8")
    digest = sha256(body).hexdigest()

    start_anchor = row["span_start_anchor"]
    end_anchor = row["span_end_anchor"]
    main_start = _require_anchor(source, start_anchor)
    main_end = _require_anchor(source, end_anchor) + len(end_anchor)
    if main_start >= main_end:
        raise PacketRefusal("SPAN_EMPTY_OR_INVALID")
    receipt = receipt_for_char_span(
        source=source, source_sha256=digest, char_start=main_start, char_end=main_end
    ).to_dict()

    # The same single-party candidate construction the segment route uses: a
    # product_integration vehicle whose labels all occur in the replayed span.
    candidate = {
        "schema": CANDIDATE_SCHEMA,
        "candidate_id": f"gmi:segment:{ticker}:{accession}",
        "document": {
            "document_id": row["document_id"], "version": "sha256:" + digest,
            "source_ref": archive_url, "published_date": None,
        },
        "dataset_id": None, "temporal_row": None, "receipt": receipt,
        "assertion": {
            "kind": "product_integration", "subject_label": row["subject_label"],
            "object_label": row["disclosed_line"], "product_scope": row["disclosed_line"],
            "lifecycle": "planned", "magnitude": None,
        },
        "revision": {"supersedes_candidate_id": None, "relation": "original"},
        "identity_annotations": None,
    }
    inspection = inspect_pinned_candidate(
        candidate, authority=authority, snapshot_id=snapshot_id,
        manifest_key=row["manifest_key"], document_id=row["document_id"],
    )
    if inspection["inspection_status"] != "INSPECTABLE":
        code = (inspection.get("refusal") or {}).get("code", "INSPECTION_REFUSED")
        raise PacketRefusal(code)
    binding = inspection["native_source_binding"]

    assertion_figures, figure_spans = _locate_figures(source, body, row, main_start, main_end)
    assertion = {
        "subject_label": row["subject_label"], "disclosed_line": row["disclosed_line"],
        "share_scope": row["share_scope"], "profit_measure": row["profit_measure"],
        "fiscal_year": row["fiscal_year"], "figure_spans": figure_spans,
        **assertion_figures,
    }
    identities = {"subject": identity_reader(ticker)}
    role_review = {
        "decision": "supported_segment_activity_in_selected_filing",
        "source_sha256": binding["raw_sha256"], "span_sha256": receipt["span_sha256"],
        "snapshot_id": binding["snapshot_id"], "disclosed_line": row["disclosed_line"],
    }
    prepared = segment.prepare_segment_input(
        inspection, assertion=assertion, receipt=receipt, identities=identities,
        identity_queries={"subject": ticker}, identity_observed_at=identity_observed_at,
        reviewed_at=row["reviewed_at"], role_review=role_review,
    )
    edition, fact = prepared["edition"], prepared["proposed_fact"]
    sec_source = edition["sec_source"]
    policy = {
        "schema": segment.POLICY_SCHEMA,
        "basis_id": f"GMI-SEGMENT-{ticker}-{accession}",
        "recorded_at": row["policy_recorded_at"], "reviewer": row["reviewer"],
        "evidence_kind": "published_source_reuse_policy", "decision": "covered_for_described_use",
        "rights_family": "sec_public_filing_facts",
        "source_policy_evidence": [
            {"url": segment.POLICY_URLS[0],
             "section": "General Questions: Is content on sec.gov free? Do I need permission to reuse EDGAR content?",
             "finding": "The SEC expressly includes EDGAR public filing content in content free to access and reuse.",
             "verification": "Published SEC webmaster FAQ; a source-policy basis, not a Chairman grant."},
            {"url": segment.POLICY_URLS[1],
             "section": "Website Dissemination",
             "finding": "The SEC permits copying and distribution of information on its site without separate SEC permission, with appropriate source citation.",
             "verification": "Published SEC privacy/dissemination policy; a source-policy basis, not a Chairman grant."},
        ],
        "source": {
            "accession": sec_source["accession"], "reporting_cik": sec_source["issuer_cik"],
            "archive_url": sec_source["archive_url"], "raw_sha256": edition["source_sha256"],
            "byte_start": fact["span"]["start_byte"], "byte_end": fact["span"]["end_byte"],
            "span_sha256": fact["span"]["text_sha256"],
        },
        "permitted_use": {
            "purpose": n.SEC_SUPPLIER_PURPOSE, "audience": n.SEC_SUPPLIER_AUDIENCE,
            "paid_product_display": True, "fact_retention": True,
            "source_attribution_required": True, "kind": "segment_activity",
            "lifecycle": "reported", "subject": identities["subject"]["issuer_id"],
            "disclosed_line": row["disclosed_line"], "share_scope": row["share_scope"],
            "source_quotation": False, "source_body_export": False, "reviewer_text": False,
        },
        "scope_limits": [
            "Internal graph membership use only.",
            "Display false.",
            "Redistribution false.",
            "Ruling 102/105.",
        ],
    }
    spec = segment.adopt_segment_input(
        prepared, adopted_at=row["adopted_at"], ruling_raw=_canonical(policy),
        theme_sources_raw=theme_sources_raw, identity_observed_at=identity_observed_at,
    )
    return {"spec": spec, "policy": policy}


def run_packet(request_path, snapshot_id, out, *, local_store=None, identity_reader=None,
               theme_sources_raw=None, now=None) -> dict:
    if not isinstance(snapshot_id, str) or not _SNAPSHOT_RE.fullmatch(snapshot_id):
        raise ValueError("SNAPSHOT_SELECTOR_INVALID")
    request = _load_json(Path(request_path))
    if not isinstance(request, dict) or request.get("schema") != REQUEST_SCHEMA:
        raise ValueError("REQUEST_SCHEMA_INVALID")
    rows = request.get("rows")
    if not isinstance(rows, list):
        raise ValueError("REQUEST_ROWS_INVALID")
    # Every output name is fixed and checked before the output directory exists,
    # so a colliding request writes nothing at all.
    stems = _validate_packet_rows(rows)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    store = build_private_source_store(local_dir=local_store)
    authority = PinnedSourceAuthority(store=store, snapshot_id=snapshot_id)
    identity_reader = identity_reader or _default_identity_reader
    if theme_sources_raw is None:
        theme_sources_raw = (ROOT / "config" / "theme_sources.yml").read_bytes()
    identity_observed_at = now or _utc_now()
    results = []
    for row, stem in zip(rows, stems):
        ticker = row.get("ticker")
        accession = row.get("accession")
        line = row.get("disclosed_line")
        try:
            produced = _packet_row(
                row, authority, snapshot_id, identity_reader, identity_observed_at, theme_sources_raw
            )
        except PacketRefusal as exc:
            code = exc.code
        except n.DisclosureError as exc:
            code = str(exc)
        except Exception:
            code = "PACKET_ROW_FAILED"
        else:
            code = None
        base = {"ticker": ticker, "accession": accession, "disclosed_line": line, "stem": stem}
        if code is not None:
            results.append({**base, "status": "REFUSED", "refusal": code})
            continue
        (out / f"{stem}_SEGMENT_OWNER_DECISION.json").write_bytes(_canonical(produced["spec"]))
        (out / f"{stem}_SOURCE_POLICY.json").write_bytes(_canonical(produced["policy"]))
        results.append({**base, "status": "ADOPTED", "refusal": None})
    report = {"schema": PACKET_REPORT_SCHEMA, "snapshot_id": snapshot_id,
              "outcome": _outcome(sum(1 for r in results if r["status"] == "REFUSED"), len(results)),
              "rows": results}
    (out / "packet_report.json").write_bytes(report_bytes(report))
    return report


# ---------------------------------------------------------------------------
# propose
# ---------------------------------------------------------------------------

def profit_driver_flag(value) -> str:
    """Map a manifest's profit_driver to the CLI flag; only a JSON boolean is accepted."""
    if value is True:
        return "--profit-driver"
    if value is False:
        return "--no-profit-driver"
    raise ValueError("PROFIT_DRIVER_NOT_BOOLEAN")


PROPOSE_REQUIRED_KEYS = (
    "issuer", "theme", "role", "knowledge_cutoff", "created",
    "spec_path", "policy_path", "exposure_role", "profit_driver",
)


class ManifestRowRefused(ValueError):
    """A manifest row failed validation; carries only the row index and a fixed code."""

    def __init__(self, index: int, code: str):
        super().__init__(f"PROPOSE_MANIFEST_ROW_{index}_{code}")
        self.index = index
        self.code = code


def propose_command(row: dict, ledger: Path, interpreter: str) -> list[str]:
    """The unchanged membership CLI's argument list for one validated manifest row."""
    return [
        interpreter, str(ROOT / "scripts" / "propose_activity_membership.py"), "propose",
        "--issuer", row["issuer"], "--theme", row["theme"], "--role", row["role"],
        "--knowledge-cutoff", row["knowledge_cutoff"], "--created", row["created"],
        "--segment-packet", row["spec_path"], row["policy_path"], "config/theme_sources.yml",
        "--ledger", str(ledger), "--exposure-role", row["exposure_role"],
        profit_driver_flag(row["profit_driver"]),
    ]


def _validate_manifest_rows(rows: list) -> None:
    """Check EVERY row before any subprocess runs, so a bad row writes nothing."""
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ManifestRowRefused(index, "NOT_AN_OBJECT")
        for key in PROPOSE_REQUIRED_KEYS:
            if key not in row:
                raise ManifestRowRefused(index, f"MISSING_{key.upper()}")
            if key != "profit_driver" and not (isinstance(row[key], str) and row[key]):
                raise ManifestRowRefused(index, f"INVALID_{key.upper()}")
        if not isinstance(row["profit_driver"], bool):
            raise ManifestRowRefused(index, "PROFIT_DRIVER_NOT_BOOLEAN")
        # Optional, but echoed in the report: when given it must be a ticker.
        ticker = row.get("ticker")
        if ticker is not None and not (isinstance(ticker, str) and _TICKER_RE.fullmatch(ticker)):
            raise ManifestRowRefused(index, "INVALID_TICKER")


def run_propose(manifest_path, out, *, python=None, runner=None) -> dict:
    manifest = _load_json(Path(manifest_path))
    rows = manifest.get("rows") if isinstance(manifest, dict) else manifest
    if not isinstance(rows, list):
        raise ValueError("PROPOSE_MANIFEST_INVALID")
    _validate_manifest_rows(rows)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    ledger = out / "activity_proposals.jsonl"
    interpreter = python or sys.executable
    run = runner or subprocess.run
    results = []
    for row in rows:
        cmd = propose_command(row, ledger, interpreter)
        proc = run(cmd, capture_output=True, text=True, cwd=ROOT)
        # Fixed-shape fields only: no writer free text, detail strings or paths.
        results.append({
            "ticker": row.get("ticker"), "exit_code": proc.returncode,
            "proposal": _proposal_result(proc.stdout or ""),
            "refusal_codes": _refusal_codes(proc.stderr or ""),
        })
    report = {"schema": PROPOSE_REPORT_SCHEMA,
              "outcome": _outcome(sum(1 for r in results if r["exit_code"] != 0), len(results)),
              "rows": results}
    (out / "propose_report.json").write_bytes(report_bytes(report))
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    pin = sub.add_parser("pin", help="pin latest eligible annual reports into a private snapshot")
    pin.add_argument("--targets", required=True)
    pin.add_argument("--raw-root", required=True)
    pin.add_argument("--archive-root", required=True)
    pin.add_argument("--out", required=True)
    pin.add_argument("--local-store", default=None, help="test-only local store directory")

    packet = sub.add_parser("packet", help="build segment owner decisions from a pinned snapshot")
    packet.add_argument("--request", required=True)
    packet.add_argument("--snapshot-id", required=True)
    packet.add_argument("--out", required=True)
    packet.add_argument("--local-store", default=None, help="test-only local store directory")

    propose = sub.add_parser("propose", help="run the unchanged membership CLI per manifest row")
    propose.add_argument("--manifest", required=True)
    propose.add_argument("--out", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "pin":
            report = run_pin(args.targets, args.raw_root, args.archive_root, args.out,
                             local_store=args.local_store)
            refused = sum(1 for r in report["targets"] if "refusal" in r)
            print(f"pin: {len(report['targets'])} targets, {refused} refused, snapshot {report['snapshot_id']}")
        elif args.command == "packet":
            report = run_packet(args.request, args.snapshot_id, args.out, local_store=args.local_store)
            refused = sum(1 for r in report["rows"] if r["status"] == "REFUSED")
            print(f"packet: {report['outcome']}: {len(report['rows'])} rows, {refused} refused")
        else:
            report = run_propose(args.manifest, args.out)
            refused = sum(1 for r in report["rows"] if r["exit_code"] != 0)
            print(f"propose: {report['outcome']}: {len(report['rows'])} rows, {refused} refused")
    except (ManifestRowRefused, PacketRequestRefused, ReportRefused) as exc:
        # A fixed code only. Row and request refusals precede every write; a report
        # refusal from pin precedes the store sync, while packet/propose may already
        # have written their per-row output files.
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        # Whole-run failure: a typed code, never a traceback or a secret value.
        print(f"REFUSED: {type(exc).__name__}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

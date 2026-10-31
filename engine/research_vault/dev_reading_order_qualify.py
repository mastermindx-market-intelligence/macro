"""DEVELOPMENT-ONLY qualification CLI for the reading_order.v2 extraction candidate.

This tool exists so the opt-in ``reading_order.v2`` candidate can be qualified
against real local PDFs WITHOUT touching any production plane. It:

  * runs strictly offline, on strictly local files — no store client, no R2,
    no network, no receipt or catalog write, no production 95-credit path;
  * requires an explicit ``--development-only`` flag and refuses otherwise;
  * fails a mismatched PDF sha or mismatched legacy ``-layout`` body sha
    BEFORE any candidate extraction runs;
  * reuses the incumbent extractors (``ingest.extract_pdf_text`` and
    ``ingest.extract_pdf_text_reading_order_v2``) and the pure fulltext
    version/segment contract verbatim — no second extractor, no second store
    plane, no text cleanup of any kind;
  * writes ONLY into a brand-new caller-supplied output directory: the exact
    candidate UTF-8 body bytes, the canonical extracted-text record, the
    page-byte-v1 segments, and a qualification receipt carrying every
    identity hash. Inputs are never mutated.

The candidate stays DEVELOPMENT_ONLY_NOT_ADOPTED by construction: nothing here
can write a derivative into the vault, and every output lands in a local
scratch directory the operator names.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from typing import Any

from engine.research_vault import corpus as corpus_mod
from engine.research_vault import fulltext
from engine.research_vault import fulltext_store
from engine.research_vault import probe as probe_mod

QUALIFICATION_SCHEMA = "research_vault.dev_reading_order_qualification.v1"
_CANDIDATE_VERSION = fulltext_store.READING_ORDER_EXTRACTOR_VERSION
_SHA_RE = fulltext_store._SHA_RE


class QualificationRefusal(Exception):
    """A qualification gate failed; effects preceding that gate may have occurred."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _write_new_file(path: os.PathLike | str, blob: bytes) -> None:
    """Create-once write at mode 0600; an existing file is a hard refusal."""
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        remaining = memoryview(blob)
        while remaining:
            written = os.write(fd, remaining)
            if written <= 0:
                raise OSError("qualification output write made no progress")
            remaining = remaining[written:]
    finally:
        os.close(fd)


def _sha_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _build_candidate_record(report_id: str, pdf_sha: str, text: str, pdf: bytes) -> dict[str, Any]:
    """Build the canonical v2 record exactly as the materializer would."""
    pages = probe_mod.probe(pdf).get("pages")
    layer = probe_mod.text_facts(text, pages)["text_layer"]
    page_count = pages if type(pages) is int else None
    if (not text.strip()) or layer in ("none", "unavailable"):
        # Blank-normalized, never ``unavailable``: same law as the writer.
        return fulltext.build_extracted_text(
            report_id=report_id,
            source_pdf_sha256=pdf_sha,
            text="",
            extractor_name=fulltext_store.EXTRACTOR_NAME,
            extractor_version=_CANDIDATE_VERSION,
            page_count=page_count,
            text_layer_state="none",
        )
    return fulltext.build_extracted_text(
        report_id=report_id,
        source_pdf_sha256=pdf_sha,
        text=text,
        extractor_name=fulltext_store.EXTRACTOR_NAME,
        extractor_version=_CANDIDATE_VERSION,
        page_count=page_count,
        text_layer_state=layer,
    )


def run_qualification(
    *,
    development_only: bool,
    pdf_path: str,
    report_id: str,
    source_sha256: str,
    legacy_body_sha256: str,
    out_dir: str,
    extract_layout=None,
    extract_reading_order=None,
) -> dict[str, Any]:
    """Qualify one local PDF for the reading_order.v2 candidate.

    Returns the qualification receipt dict. Raises :class:`QualificationRefusal`
    on every contract violation, always BEFORE the first effect it guards.
    ``extract_layout``/``extract_reading_order`` default to the incumbent
    ingest extractors and exist only for hermetic tests; they never replace
    the version contract.
    """
    if not development_only:
        raise QualificationRefusal(
            "refusal: --development-only is required; this tool never runs in a "
            "production or non-development context"
        )
    if extract_layout is None or extract_reading_order is None:
        from engine.research_vault import ingest as ingest_mod
        extract_layout = extract_layout or ingest_mod.extract_pdf_text
        extract_reading_order = (
            extract_reading_order or ingest_mod.extract_pdf_text_reading_order_v2
        )

    if not corpus_mod.valid_doc_id(report_id):
        raise QualificationRefusal(
            f"refusal: report_id {report_id!r} is not a catalog slug"
        )
    for name, digest in (("source_sha256", source_sha256),
                         ("legacy_body_sha256", legacy_body_sha256)):
        if not isinstance(digest, str) or _SHA_RE.fullmatch(digest) is None:
            raise QualificationRefusal(
                f"refusal: {name} must be 64 lowercase hex characters"
            )

    # The output directory must be NEW: an occupied or existing path refuses
    # before anything is read or run, so a re-run can never mix generations.
    if os.path.exists(out_dir):
        raise QualificationRefusal(
            f"refusal: output directory already exists: {out_dir}"
        )
    parent = os.path.dirname(os.path.abspath(out_dir))
    if not os.path.isdir(parent):
        raise QualificationRefusal(
            f"refusal: output parent directory does not exist: {parent}"
        )

    try:
        with open(pdf_path, "rb") as fh:
            pdf = fh.read()
    except OSError as exc:
        raise QualificationRefusal(f"refusal: cannot read pdf: {exc}") from exc
    if not pdf:
        raise QualificationRefusal("refusal: pdf file is empty")

    # Identity gate BEFORE any extraction: the bytes must be exactly the
    # revision the operator names.
    pdf_sha = _sha_hex(pdf)
    if pdf_sha != source_sha256:
        raise QualificationRefusal(
            f"refusal: source sha mismatch: --source-sha256 {source_sha256} but "
            f"file hashes to {pdf_sha}"
        )

    # Legacy gate: the incumbent -layout extraction must reproduce the supplied
    # old-body sha BEFORE the candidate runs, pinning the comparison to the
    # real v1 body for this revision.
    legacy_text = extract_layout(pdf)
    if legacy_text is None:
        raise QualificationRefusal(
            "refusal: pdftotext (-layout) unavailable — legacy body cannot be "
            "verified; no candidate extraction attempted"
        )
    legacy_sha = _sha_hex(legacy_text.encode("utf-8"))
    if legacy_sha != legacy_body_sha256:
        raise QualificationRefusal(
            f"refusal: legacy body sha mismatch: --legacy-body-sha256 "
            f"{legacy_body_sha256} but -layout extraction hashes to {legacy_sha}"
        )

    # Candidate extraction. Unresolved table/header joins are retained
    # verbatim: no cleanup, no reassembly, no punctuation repair.
    candidate_text = extract_reading_order(pdf)
    if candidate_text is None:
        raise QualificationRefusal(
            "refusal: pdftotext (reading order) unavailable — no qualification "
            "is possible from an extraction that never ran"
        )

    record = _build_candidate_record(report_id, pdf_sha, candidate_text, pdf)
    record_blob = fulltext_store.encode_record(record)
    record_sha = _sha_hex(record_blob)

    from engine.research_vault.read_service import SEGMENT_MAX_BYTES
    segments = fulltext.build_segments(
        dict(record),
        segmenter_version=fulltext.SEGMENTER_VERSION,
        max_bytes=SEGMENT_MAX_BYTES,
    )
    replay_exact = all(
        fulltext.replay_segment(dict(record), segment) == segment["text"]
        for segment in segments
    )
    if not replay_exact:
        raise QualificationRefusal(
            "refusal: candidate segments failed exact replay — refusing to "
            "emit a qualification receipt for a non-replayable segmentation"
        )

    legacy_key = fulltext_store.derivative_key(report_id, pdf_sha)
    candidate_key = fulltext_store.derivative_key(
        report_id, pdf_sha, extractor_version=_CANDIDATE_VERSION,
    )
    if candidate_key == legacy_key:
        raise QualificationRefusal(
            "refusal: candidate derivative key collides with the v1 key"
        )

    candidate_body = record["text"].encode("utf-8")
    receipt: dict[str, Any] = {
        "schema": QUALIFICATION_SCHEMA,
        "candidate_status": "DEVELOPMENT_ONLY_NOT_ADOPTED",
        "development_only": True,
        "report_id": report_id,
        "source_pdf_sha256": pdf_sha,
        "legacy_extractor_version": fulltext_store.EXTRACTOR_VERSION,
        "candidate_extractor_version": _CANDIDATE_VERSION,
        "candidate_text_sha256": record["extracted_text_sha256"],
        "candidate_char_count": record["char_count"],
        "candidate_byte_count": record["byte_count"],
        "candidate_text_layer_state": record["text_layer_state"],
        "candidate_page_count": record["page_count"],
        "candidate_record_sha256": record_sha,
        "legacy_body_sha256_input": legacy_body_sha256,
        "legacy_body_sha256_reproduced": legacy_sha,
        "legacy_body_verified": True,
        "legacy_derivative_key": legacy_key,
        "candidate_derivative_key": candidate_key,
        "candidate_derivative_tag": fulltext_store.READING_ORDER_DERIVATIVE_TAG,
        "distinct_derivative_keys": candidate_key != legacy_key,
        "segmenter_version": fulltext.SEGMENTER_VERSION,
        "segment_max_bytes": SEGMENT_MAX_BYTES,
        "segment_count": len(segments),
        "all_segments_exact_replay": replay_exact,
        "model_calls": 0,
        "network_calls": 0,
        "store_writes": 0,
        "outputs": {
            "body": "candidate_body.txt",
            "record": "canonical_record.json",
            "segments": "segments.json",
            "receipt": "qualification_receipt.json",
        },
    }

    receipt_blob = (json.dumps(receipt, ensure_ascii=False, sort_keys=True,
                               indent=2) + "\n").encode("utf-8")
    segments_blob = (json.dumps(segments, ensure_ascii=False, sort_keys=True,
                                indent=2) + "\n").encode("utf-8")

    # Create only after the qualification gates pass. Partial files remain on
    # an I/O failure for diagnosis; no successful return is emitted. The receipt
    # is written last, and every file is create-once O_EXCL at mode 0600.
    try:
        os.mkdir(out_dir, mode=0o700)
    except OSError as exc:
        raise QualificationRefusal(
            f"refusal: cannot create output directory {out_dir}: {exc}"
        ) from exc
    _write_new_file(os.path.join(out_dir, "candidate_body.txt"), candidate_body)
    _write_new_file(os.path.join(out_dir, "canonical_record.json"), record_blob)
    _write_new_file(os.path.join(out_dir, "segments.json"), segments_blob)
    _write_new_file(os.path.join(out_dir, "qualification_receipt.json"), receipt_blob)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="DEVELOPMENT-ONLY qualification of the reading_order.v2 "
                    "pdftotext candidate against one local PDF (offline, "
                    "local files only, no store access).",
    )
    parser.add_argument("--development-only", action="store_true",
                        help="required: acknowledge this is a local development "
                             "qualification, not a production path")
    parser.add_argument("--pdf", required=True, help="path to the one source PDF")
    parser.add_argument("--report-id", required=True, help="existing catalog report id")
    parser.add_argument("--source-sha256", required=True,
                        help="expected sha256 of the PDF bytes")
    parser.add_argument("--legacy-body-sha256", required=True,
                        help="sha256 of the existing v1 (-layout) extracted body")
    parser.add_argument("--out", required=True,
                        help="NEW output directory to create (must not exist)")
    args = parser.parse_args(argv)
    try:
        receipt = run_qualification(
            development_only=args.development_only,
            pdf_path=args.pdf,
            report_id=args.report_id,
            source_sha256=args.source_sha256,
            legacy_body_sha256=args.legacy_body_sha256,
            out_dir=args.out,
        )
    except QualificationRefusal as exc:
        print(exc.reason, file=sys.stderr)
        return 2
    print(json.dumps({
        "status": "qualified",
        "report_id": receipt["report_id"],
        "candidate_text_sha256": receipt["candidate_text_sha256"],
        "candidate_record_sha256": receipt["candidate_record_sha256"],
        "candidate_derivative_key": receipt["candidate_derivative_key"],
        "segment_count": receipt["segment_count"],
        "all_segments_exact_replay": receipt["all_segments_exact_replay"],
        "output_dir": os.path.abspath(args.out),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

#!/usr/bin/env python3
"""GMI ORCH-REL M2 harvester: EDGAR fetch + candidate extraction.

``fetch`` pulls the latest annual filing (+ its amendments) per issuer of a
leaf from SEC EDGAR through the rate-limited cache client and writes
``fetch_ledger.jsonl``.  ``candidates`` re-reads that ledger CACHE-ONLY and
writes ``candidates.jsonl`` / ``parse_ledger.jsonl`` / ``harvest_report.json``.
Candidates are workdir artifacts for later judging lanes; nothing here judges,
scores or commits candidate text.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import jsonschema  # noqa: E402

from engine.company_intelligence.relationships import edgar as rel_edgar  # noqa: E402
from engine.company_intelligence.relationships import harvest as rel_harvest  # noqa: E402
from engine.company_intelligence.relationships import package_v2  # noqa: E402
from engine.company_intelligence.relationships import replay  # noqa: E402

FETCH_LEDGER_SCHEMA = "gmi_rel_m2.fetch_ledger/v1"
REPORT_SCHEMA = "gmi_rel_m2.harvest_report/v1"
CONTRACT_PATH = (
    REPO_ROOT
    / "contracts/company_intelligence/relationship_source_excerpt.v1.schema.json"
)
DEFAULT_INPUTS = "research/theme_graph/gmi_relationships_20261021/m2_inputs"
INPUT_NAMES = (
    "curated_aliases_v1.json",
    "filing_census_v1.json",
    "leaves_v1.json",
    "resolver_us_issuers_v1.json",
)
EXCERPT_NOTE_TEMPLATE = (
    "Verbatim byte excerpt of a public SEC EDGAR filing for research "
    "provenance; harvest candidate {candidate_id} (origin {origin}), not yet "
    "judged. public_display: unknown (F03 A7)."
)


def _cik_str(cik) -> str:
    return f"{int(cik):010d}"


def _write_jsonl(path: Path, rows) -> None:
    with path.open("wb") as handle:
        for row in rows:
            handle.write(
                (json.dumps(row, sort_keys=True) + "\n").encode("utf-8")
            )


def _resolve_selection(args):
    """(issuers, dirname, slice_label) after pin-verified input loading."""
    inputs = rel_harvest.load_inputs(args.inputs)
    issuers = rel_harvest.leaf_issuers(inputs["leaves"], args.leaf)
    slice_label = None
    if args.slice:
        i, n = args.slice.split("/", 1)
        i, n = int(i), int(n)
        issuers = rel_harvest.slice_issuers(issuers, i, n)
        slice_label = f"{i}/{n}"
    if args.issuers:
        wanted = [name.strip() for name in args.issuers.split(",") if name.strip()]
        unknown = [name for name in wanted if name not in set(issuers)]
        if unknown:
            raise ValueError(
                f"--issuers not in leaf {args.leaf} (after slice): {unknown}"
            )
        issuers = wanted
    dirname = args.leaf if not slice_label else f"{args.leaf}.{slice_label.replace('/', 'of')}"
    return inputs, sorted(issuers), dirname, slice_label


# --- fetch --------------------------------------------------------------------


def _fetch_index_row(client, leaf, issuer_id, entry, filing, filing_role):
    cik_str = _cik_str(entry["cik"])
    accession = filing["accessionNumber"]
    nodash = accession.replace("-", "")
    row = {
        "leaf": leaf,
        "issuer_id": issuer_id,
        "cik": cik_str,
        "sec_name": entry.get("sec_name"),
        "accession": accession,
        "form": filing.get("form"),
        "filing_role": filing_role,
        "state": "unavailable",
        "reason": None,
        "accepted_at": None,
        "sec_index_header_acceptance_et": None,
        "sec_submissions_acceptance_raw": filing.get("acceptanceDateTime"),
        "census_fetched_at": entry.get("fetched_at"),
        "filed_at": None,
        "period_of_report": None,
        "notes": [],
        "documents": [],
    }
    try:
        result = client.fetch(
            int(entry["cik"]), nodash, f"{accession}-index-headers.html"
        )
    except rel_edgar.HttpError as error:
        row["reason"] = f"INDEX_HEADERS_HTTP_{error.status}"
        return row
    except (rel_edgar.NetworkError, rel_edgar.NetworkDisabled) as error:
        row["reason"] = f"INDEX_HEADERS_{type(error).__name__.upper()}"
        return row
    header = rel_edgar.parse_index_headers(result.body)
    row = rel_harvest.resolve_filing(
        leaf=leaf,
        issuer_id=issuer_id,
        cik_str=cik_str,
        sec_name=entry.get("sec_name"),
        filing_role=filing_role,
        census_filing=filing,
        header=header,
        census_fetched_at=entry.get("fetched_at"),
    )
    row["sec_submissions_acceptance_raw"] = filing.get("acceptanceDateTime")
    if row["state"] == "rejected":
        return row
    documents, notes = rel_harvest.select_documents(
        header["documents"], filing["form"], filing.get("primaryDocument")
    )
    row["notes"] = sorted(set(notes))
    for document in documents:
        filename = document["filename"]
        doc_row = {
            "filename": filename,
            "type": document["type"],
            "state": "skipped",
            "reason": None,
            "http_status": None,
            "sha256": None,
            "byte_length": None,
            "fetched_at": None,
        }
        try:
            fetched = client.fetch(int(entry["cik"]), nodash, filename)
        except rel_edgar.HttpError as error:
            doc_row["state"] = "failed"
            doc_row["reason"] = f"HTTP_{error.status}"
            doc_row["http_status"] = error.status
        except (rel_edgar.NetworkError, rel_edgar.NetworkDisabled) as error:
            doc_row["state"] = "failed"
            doc_row["reason"] = (
                "NETWORK_DISABLED"
                if isinstance(error, rel_edgar.NetworkDisabled)
                else "NETWORK"
            )
        else:
            body = fetched.body
            if len(body) > rel_harvest.MAX_DOC_BYTES:
                doc_row["state"] = "skipped"
                doc_row["reason"] = "DOC_TOO_LARGE"
                doc_row["byte_length"] = len(body)
                doc_row["sha256"] = hashlib.sha256(body).hexdigest()
            else:
                doc_row["state"] = fetched.state
                doc_row["http_status"] = fetched.meta.get("http_status")
                doc_row["sha256"] = fetched.meta.get("sha256")
                doc_row["byte_length"] = fetched.meta.get("byte_length")
                doc_row["fetched_at"] = fetched.meta.get("fetched_at")
        row["documents"].append(doc_row)
    states = [doc["state"] for doc in row["documents"]]
    successes = [s for s in states if s in ("fetched", "cached")]
    failures = [s for s in states if s == "failed"]
    if not states or len(successes) == len(states):
        row["state"] = "collected"
    elif successes and not failures:
        row["state"] = "collected"
    elif successes and failures:
        row["state"] = "partial"
    elif failures:
        row["state"] = "unavailable"
        row["reason"] = "ALL_DOCUMENTS_FAILED"
    else:
        row["state"] = "collected"
    return row


def cmd_fetch(args) -> int:
    inputs, issuers, dirname, _slice_label = _resolve_selection(args)
    outdir = Path(args.workdir) / dirname
    outdir.mkdir(parents=True, exist_ok=True)
    client = rel_edgar.EdgarClient(rps=args.rps)
    rows: list = []
    for issuer_id in issuers:
        entry = (inputs["census"]["issuers"] or {}).get(issuer_id)
        if entry is None or entry.get("state") != "OK":
            rows.append(
                rel_harvest.build_unavailable_row(
                    args.leaf,
                    issuer_id,
                    entry
                    or {
                        "state": "MISSING_IN_CENSUS",
                        "fetched_at": None,
                        "cik": None,
                        "sec_name": None,
                    },
                )
            )
            continue
        filings = []
        if entry.get("latest"):
            filings.append(("latest", entry["latest"]))
        for amendment in entry.get("amendments_of_latest") or []:
            filings.append(("amendment_of_latest", amendment))
        for filing_role, filing in filings:
            rows.append(
                _fetch_index_row(client, args.leaf, issuer_id, entry, filing,
                                 filing_role)
            )
    rows.sort(
        key=lambda r: (
            r["issuer_id"],
            r["accession"] or "",
            r["filing_role"] or "",
        )
    )
    _write_jsonl(outdir / "fetch_ledger.jsonl", rows)
    return 0


# --- candidates (cache-only) ----------------------------------------------------


def _finalize_candidate(cand, row, document, contract_schema):
    cik_str = row["cik"]
    accession = row["accession"]
    filename = document["filename"]
    span = cand["span"]
    raw = span["raw"].encode("utf-8")
    normalized = package_v2.normalize_span(raw)
    candidate_id = "cand:" + package_v2.sha(
        package_v2.canon([accession, filename, span["byte_start"],
                          span["byte_end"]])
    )[:20]
    url = rel_edgar.document_url(int(cik_str), accession, filename)
    xbrl_contexts = [
        {
            "context_ref": ctx["context_ref"],
            "byte_start": ctx["byte_start"],
            "byte_end": ctx["byte_end"],
            "raw": ctx["raw"],
            "raw_sha256": package_v2.sha(ctx["raw"].encode("utf-8")),
        }
        for ctx in cand["excerpt_contexts"]
    ]
    excerpt = {
        "schema": "company_intelligence.relationship_source_excerpt/v1",
        "accession": accession,
        "cik": cik_str,
        "form": row["form"],
        "url": url,
        "primary_document": filename,
        "doc_sha256": document["sha256"],
        "doc_byte_length": document["byte_length"],
        "accepted_at": row["accepted_at"],
        "filed_at": row["filed_at"],
        "period_of_report": row["period_of_report"],
        "span": {
            "byte_start": span["byte_start"],
            "byte_end": span["byte_end"],
            "raw": span["raw"],
            "raw_sha256": package_v2.sha(raw),
            "normalized": normalized,
            "normalized_sha256": package_v2.sha(normalized),
        },
        "xbrl_contexts": xbrl_contexts,
        "excerpt_note": EXCERPT_NOTE_TEMPLATE.format(
            candidate_id=candidate_id, origin=cand["origin"]
        ),
    }
    return candidate_id, excerpt


def cmd_candidates(args) -> int:
    inputs, issuers, dirname, slice_label = _resolve_selection(args)
    outdir = Path(args.workdir) / dirname
    ledger_path = outdir / "fetch_ledger.jsonl"
    rows = [
        json.loads(line)
        for line in ledger_path.read_text("utf-8").splitlines()
        if line.strip()
    ]
    contract_schema = json.loads(CONTRACT_PATH.read_text("utf-8"))
    counters = rel_harvest.new_counters()
    hints_by_issuer = {}
    for issuer_id in issuers:
        hints_by_issuer[issuer_id] = rel_harvest.build_hints(
            inputs["resolver"], inputs["aliases"], issuer_id
        )
    candidates: list = []
    parse_rows: list = []
    cache = rel_edgar.EdgarCache(
        os.environ.get("GMI_EDGAR_CACHE")
        or os.path.expanduser("~/.cache/gmi_edgar")
    )
    doc_order = 0
    for row in sorted(
        rows, key=lambda r: (r["issuer_id"], r["accession"] or "")
    ):
        if row["state"] not in ("collected", "partial"):
            continue
        hints, own_hints = hints_by_issuer[row["issuer_id"]]
        nodash = row["accession"].replace("-", "")
        amendment_primary = row["form"] in rel_harvest.AMENDMENT_FORMS
        for document in row["documents"]:
            doc_order += 1
            if document["state"] not in ("fetched", "cached"):
                continue
            before = dict(counters)
            body, meta, integrity_ok = cache.load(
                int(row["cik"]), nodash, document["filename"]
            )
            state = "parsed"
            reason = None
            if body is None or not integrity_ok:
                state = "parse_failed"
                reason = "CACHE_MISS" if body is None else "CACHE_INTEGRITY"
                if body is not None:
                    counters["cache_integrity_refetch"] += 1
            else:
                if document["sha256"] and (
                    hashlib.sha256(body).hexdigest() != document["sha256"]
                ):
                    state = "parse_failed"
                    reason = "CACHE_LEDGER_SHA_MISMATCH"
                else:
                    cands = rel_harvest.extract_document_candidates(
                        body,
                        hints=hints,
                        own_hints=own_hints,
                        counters=counters,
                        amendment_primary=(
                            amendment_primary
                            and document["type"] == row["form"]
                        ),
                    )
                    for cand in cands:
                        candidate = dict(cand)
                        candidate["_doc_order"] = doc_order
                        candidate["_row"] = row
                        candidate["_document"] = document
                        candidates.append(candidate)
            delta = {
                key: counters[key] - before[key]
                for key in rel_harvest.COUNTER_KEYS
            }
            parse_rows.append(
                {
                    "accession": row["accession"],
                    "filename": document["filename"],
                    "state": state,
                    "reason": reason,
                    "counters": delta,
                }
            )
    kept = rel_harvest.apply_filing_caps(candidates, counters)
    out_rows: list = []
    for cand in kept:
        row = cand["_row"]
        document = cand["_document"]
        candidate_id, excerpt = _finalize_candidate(cand, row, document,
                                                    contract_schema)
        problems = None
        try:
            jsonschema.validate(excerpt, contract_schema)
            problems = replay.verify_excerpt(excerpt)
        except jsonschema.ValidationError as error:
            problems = [f"schema: {error.message}"]
        if problems:
            counters["excerpt_self_check_failed"] += 1
            continue
        out_rows.append(
            {
                "candidate_id": candidate_id,
                "leaf": row["leaf"],
                "issuer_id": row["issuer_id"],
                "cik": row["cik"],
                "sec_name": row["sec_name"],
                "accession": row["accession"],
                "form": row["form"],
                "filing_role": row["filing_role"],
                "document_type": document["type"],
                "primary_document": document["filename"],
                "url": excerpt["url"],
                "doc_sha256": document["sha256"],
                "doc_byte_length": document["byte_length"],
                "filed_at": row["filed_at"],
                "period_of_report": row["period_of_report"],
                "sec_index_header_acceptance_et": row[
                    "sec_index_header_acceptance_et"
                ],
                "accepted_at": row["accepted_at"],
                "sec_submissions_acceptance_raw": row[
                    "sec_submissions_acceptance_raw"
                ],
                "origin": cand["origin"],
                "rank": cand["rank"],
                "span_kind": cand["span_kind"],
                "cues": cand["cues"],
                "hints": cand["hints"],
                "xbrl_facts": cand["xbrl_facts"],
                "excerpt": excerpt,
            }
        )
    out_rows.sort(
        key=lambda r: (
            r["issuer_id"],
            r["accession"],
            r["primary_document"],
            r["excerpt"]["span"]["byte_start"],
            r["excerpt"]["span"]["byte_end"],
        )
    )
    _write_jsonl(outdir / "candidates.jsonl", out_rows)
    parse_rows.sort(key=lambda r: (r["accession"], r["filename"]))
    _write_jsonl(outdir / "parse_ledger.jsonl", parse_rows)
    filings_by_state: dict = {}
    documents_by_state: dict = {}
    for row in rows:
        filings_by_state[row["state"]] = (
            filings_by_state.get(row["state"], 0) + 1
        )
        for document in row["documents"]:
            documents_by_state[document["state"]] = (
                documents_by_state.get(document["state"], 0) + 1
            )
    by_origin: dict = {}
    by_rank: dict = {}
    for row in out_rows:
        by_origin[row["origin"]] = by_origin.get(row["origin"], 0) + 1
        by_rank[str(row["rank"])] = by_rank.get(str(row["rank"]), 0) + 1
    report = {
        "schema": REPORT_SCHEMA,
        "leaf": args.leaf,
        "slice": slice_label,
        "issuers_total": len(issuers),
        "filings_by_state": dict(sorted(filings_by_state.items())),
        "documents_by_state": dict(sorted(documents_by_state.items())),
        "candidates_total": len(out_rows),
        "candidates_by_origin": dict(sorted(by_origin.items())),
        "candidates_by_rank": dict(sorted(by_rank.items())),
        "counters": {key: counters[key] for key in rel_harvest.COUNTER_KEYS},
        "inputs": {
            os.path.relpath(
                os.path.join(str(args.inputs), name), str(REPO_ROOT)
            ): rel_harvest.PINS[name]
            for name in INPUT_NAMES
        },
    }
    (outdir / "harvest_report.json").write_bytes(
        (json.dumps(report, sort_keys=True, indent=1) + "\n").encode("utf-8")
    )
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    def common(sub_parser):
        sub_parser.add_argument(
            "--leaf", required=True, choices=["P", "D1a", "D1b", "D2a", "D2b"]
        )
        sub_parser.add_argument("--workdir", required=True)
        sub_parser.add_argument("--issuers", default=None)
        sub_parser.add_argument(
            "--slice", default=None, help="i/n — keeps sorted(leaf)[k], k %% n == i-1"
        )
        sub_parser.add_argument("--inputs", default=DEFAULT_INPUTS)

    fetch_parser = sub.add_parser("fetch")
    common(fetch_parser)
    fetch_parser.add_argument("--rps", type=float, default=rel_edgar.DEFAULT_RPS)

    common(sub.add_parser("candidates"))

    args = parser.parse_args(argv)
    try:
        if args.command == "fetch":
            return cmd_fetch(args)
        return cmd_candidates(args)
    except rel_harvest.InputPinMismatch as error:
        print(f"relationship_m2_harvest: input pin mismatch: {error}",
              file=sys.stderr)
        return 2
    except ValueError as error:
        print(f"relationship_m2_harvest: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

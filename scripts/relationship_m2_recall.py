#!/usr/bin/env python3
"""GMI ORCH-REL M2 recall: corpus fetch, independent lexicon scan, compare.

``fetch`` pulls the EXACT pinned corpus edition per issuer from SEC EDGAR
through the rate-limited cache client and writes ``fetch_ledger.jsonl`` (an
edition that no longer matches its pin is a counted CORPUS_EDITION_MISMATCH
row, never substituted).  ``scan`` re-reads that ledger CACHE-ONLY and emits
every lexicon sentence per document (R2) as ``sentences.jsonl`` plus blind
annotation ``packs/`` and ``packs/GUIDE.md``.  ``compare`` matches annotated
named relationships against the committed extraction rows and prints recall
with Wilson 95% intervals and an issuer-clustered jackknife.

Every command re-hashes the frozen corpus (rc 2 CORPUS_DRIFT on drift) and
refuses to write under data/ or site/ (rc 2 OUT_REFUSED).  Nothing here
annotates, scores, ranks or predicts: the annotation belongs to a later lane.
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
from engine.company_intelligence.relationships import recall as rel_recall  # noqa: E402

DEFAULT_CORPUS = (
    REPO_ROOT
    / "research/theme_graph/gmi_relationships_20261021/m2_recall"
    / "recall_corpus_v1.json"
)
DEFAULT_INPUTS = "research/theme_graph/gmi_relationships_20261021/m2_inputs"
DEFAULT_EXTRACTION = (
    REPO_ROOT / "research/theme_graph/gmi_relationships_20261021/extraction"
)
DEFAULT_MANIFEST = "research/theme_graph/coverage_20261019/UNIVERSE_MANIFEST.json"
DOMAINS = ("D1", "D2")
GUIDE_RULES = (
    "Judge ONLY from the sentence text.",
    "A named relationship requires a named counterparty (or a defined alias) "
    "with one of the five species.",
    "Generic risk language (\"a limited number of customers\") is "
    "named_relationship false.",
    "Affiliates and subsidiaries are never counterparties "
    "(named_relationship false).",
    "counterparty_quote values are exact substrings of the sentence text.",
    "Never write issuer ids or tickers in quotes.",
    "unclear is honest: use it when the sentence cannot be judged.",
)


def build_client(args):
    """The one client seam (tests inject openers here)."""
    return rel_edgar.EdgarClient(rps=args.rps, cache_root=args.cache_root)


def _cik_str(cik) -> str:
    return f"{int(cik):010d}"


def _write_jsonl(path: Path, rows) -> None:
    with path.open("wb") as handle:
        for row in rows:
            handle.write(
                (json.dumps(row, sort_keys=True) + "\n").encode("utf-8")
            )


def _load_corpus(args) -> dict:
    return rel_recall.load_corpus(args.corpus)


def _under(path: Path, parent: Path) -> bool:
    try:
        rel = os.path.relpath(str(path), str(parent))
    except ValueError:
        return False
    return rel == "." or not rel.startswith("..")


def _check_out(path) -> None:
    resolved = Path(os.path.abspath(str(path)))
    for guarded in ("data", "site"):
        if _under(resolved, REPO_ROOT / guarded):
            raise rel_recall.OutRefused(
                f"{resolved} is under {guarded}/ — OUT_REFUSED"
            )


def _read_jsonl(path: Path) -> list:
    rows = []
    for line in path.read_text("utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


# --- fetch --------------------------------------------------------------------


def _fetch_filing_row(client, domain, entry, edition):
    issuer_id = entry["issuer_id"]
    cik_str = _cik_str(entry["cik"])
    accession = edition["accessionNumber"]
    nodash = accession.replace("-", "")
    row = {
        "domain": domain,
        "leaf": f"recall-{domain}",
        "issuer_id": issuer_id,
        "cik": cik_str,
        "sec_name": entry.get("sec_name"),
        "accession": accession,
        "form": edition.get("form"),
        "filing_role": "latest",
        "state": "unavailable",
        "reason": None,
        "accepted_at": None,
        "sec_index_header_acceptance_et": None,
        "sec_submissions_acceptance_raw": edition.get("acceptanceDateTime"),
        "census_fetched_at": None,
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
        row["reason"] = f"HTTP_{error.status}"
        return row
    except rel_edgar.NetworkDisabled:
        row["reason"] = "NETWORKDISABLED"
        return row
    except rel_edgar.NetworkError:
        row["reason"] = "NETWORKERROR"
        return row
    header = rel_edgar.parse_index_headers(result.body)
    resolved = rel_harvest.resolve_filing(
        leaf=row["leaf"],
        issuer_id=issuer_id,
        cik_str=cik_str,
        sec_name=entry.get("sec_name"),
        filing_role="latest",
        census_filing=edition,
        header=header,
        census_fetched_at=None,
    )
    row["sec_index_header_acceptance_et"] = resolved[
        "sec_index_header_acceptance_et"
    ]
    row["accepted_at"] = resolved["accepted_at"]
    row["filed_at"] = resolved["filed_at"]
    row["period_of_report"] = resolved["period_of_report"]
    notes: list = []
    mismatch = resolved["state"] == "rejected" and (
        resolved["reason"] == "FORM_MISMATCH"
    )
    header_filenames = [doc["filename"] for doc in header["documents"]]
    if edition.get("primaryDocument") not in header_filenames:
        mismatch = True
        notes.append("PRIMARY_DOC_NOT_IN_HEADER")
    if mismatch:
        row["state"] = "edition_mismatch"
        row["reason"] = "CORPUS_EDITION_MISMATCH"
        row["notes"] = sorted(set(notes))
        return row
    if resolved["state"] == "rejected":
        row["state"] = "rejected"
        row["reason"] = resolved["reason"]
        return row
    documents, select_notes = rel_harvest.select_documents(
        header["documents"], edition["form"], edition.get("primaryDocument")
    )
    notes.extend(select_notes)
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
        except rel_edgar.NetworkDisabled:
            doc_row["state"] = "failed"
            doc_row["reason"] = "NETWORKDISABLED"
        except rel_edgar.NetworkError:
            doc_row["state"] = "failed"
            doc_row["reason"] = "NETWORK"
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
    successes = [state for state in states if state in ("fetched", "cached")]
    failures = [state for state in states if state == "failed"]
    if not states or (successes and not failures):
        row["state"] = "collected"
    elif successes and failures:
        row["state"] = "partial"
    else:
        row["state"] = "unavailable"
        row["reason"] = "ALL_DOCUMENTS_FAILED"
    return row


def cmd_fetch(args) -> int:
    corpus = _load_corpus(args)
    _check_out(args.workdir)
    domains = DOMAINS if args.domain is None else (args.domain,)
    client = build_client(args)
    for domain in domains:
        outdir = Path(args.workdir) / domain
        outdir.mkdir(parents=True, exist_ok=True)
        rows = [
            _fetch_filing_row(client, domain, entry, entry["edition"])
            for entry in corpus["selection"][domain]
        ]
        rows.sort(
            key=lambda r: (r["issuer_id"], r["accession"] or "",
                           r["filing_role"] or "")
        )
        _write_jsonl(outdir / "fetch_ledger.jsonl", rows)
        states: dict = {}
        reasons: dict = {}
        for row in rows:
            states[row["state"]] = states.get(row["state"], 0) + 1
            if row["reason"]:
                reasons[row["reason"]] = reasons.get(row["reason"], 0) + 1
        for state in sorted(states):
            print(f"fetch {domain} state {state} {states[state]}")
        for reason in sorted(reasons):
            print(f"fetch {domain} reason {reason} {reasons[reason]}")
    return 0


# --- scan ---------------------------------------------------------------------


def _default_cache_root() -> str:
    return (
        os.environ.get("GMI_EDGAR_CACHE")
        or os.path.expanduser("~/.cache/gmi_edgar")
    )


def guide_text() -> str:
    lines = [
        "# M2 recall annotation guide",
        "",
        "Rules:",
        "",
    ]
    lines.extend(f"- {rule}" for rule in GUIDE_RULES)
    lines.extend(
        [
            "",
            f"Species (the five): {', '.join(sorted(package_v2.SPECIES_ROLES))}",
            f"Roles: {', '.join(sorted(rel_recall.ROLES))} (or null)",
            "",
            "Annotation schema (one JSON object per sentence, one object per line",
            "in an annotations *.jsonl):",
            "",
            "```json",
            json.dumps(rel_recall.ANNOTATION_SCHEMA, indent=1, sort_keys=True),
            "```",
            "",
            "Example record:",
            "",
            "```json",
            json.dumps(
                {
                    "schema": rel_recall.ANNOTATION_SCHEMA_NAME,
                    "sentence_id": "rs:00000000000000000000",
                    "annotator": {"agent": "<annotator agent>",
                                  "lane_run_id": "<lane run id>"},
                    "named_relationship": True,
                    "unclear": False,
                    "relationships": [
                        {
                            "counterparty_quote": "Taiwan Manufacturing",
                            "species": "supplier_customer",
                            "subject_role": None,
                        }
                    ],
                },
                indent=1, sort_keys=True,
            ),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def cmd_scan(args) -> int:
    corpus = _load_corpus(args)
    _check_out(args.workdir)
    domains = DOMAINS if args.domain is None else (args.domain,)
    cache = rel_edgar.EdgarCache(args.cache_root or _default_cache_root())
    corpus_issuers = {
        entry["issuer_id"] for domain in DOMAINS
        for entry in corpus["selection"][domain]
    }
    counters = {
        "RECALL_SCAN_OVERFLOW": 0,
        "SCAN_CACHE_MISS": 0,
        "SCAN_SHA_MISMATCH": 0,
        "SCAN_SKIPPED_FILING": 0,
    }
    for domain in domains:
        ledger_path = Path(args.workdir) / domain / "fetch_ledger.jsonl"
        rows = _read_jsonl(ledger_path)
        items: list = []
        pack_items: list = []
        per_issuer: dict = {}
        for row in sorted(rows, key=lambda r: (r["issuer_id"],
                                               r["accession"] or "")):
            issuer_id = row["issuer_id"]
            if issuer_id not in corpus_issuers:
                counters["SCAN_SKIPPED_FILING"] += 1
                continue
            if row["state"] not in ("collected", "partial"):
                counters["SCAN_SKIPPED_FILING"] += 1
                continue
            stats = per_issuer.setdefault(
                issuer_id, {"documents": 0, "sentences": 0, "overflow": 0}
            )
            nodash = (row["accession"] or "").replace("-", "")
            for document in row["documents"]:
                if document["state"] not in ("fetched", "cached"):
                    continue
                body, _meta, integrity_ok = cache.load(
                    int(row["cik"]), nodash, document["filename"]
                )
                if body is None or not integrity_ok:
                    counters["SCAN_CACHE_MISS"] += 1
                    continue
                if document["sha256"] and (
                    hashlib.sha256(body).hexdigest() != document["sha256"]
                ):
                    counters["SCAN_SHA_MISMATCH"] += 1
                    continue
                doc_id = f"{row['accession']}:{document['filename']}"
                doc_items, overflow = rel_recall.scan_with_overflow(
                    body, doc_id=doc_id
                )
                stats["documents"] += 1
                stats["sentences"] += len(doc_items)
                stats["overflow"] += overflow
                counters["RECALL_SCAN_OVERFLOW"] += overflow
                items.extend(doc_items)
                pack_items.extend(
                    {
                        "sentence_id": item["sentence_id"],
                        "issuer_id": issuer_id,
                        "sec_name": row["sec_name"],
                        "form": row["form"],
                        "accession": row["accession"],
                        "text": item["text"],
                    }
                    for item in doc_items
                )
        items.sort(
            key=lambda item: (
                item["doc_id"], item["byte_start"], item["byte_end"]
            )
        )
        _write_jsonl(Path(args.workdir) / domain / "sentences.jsonl", items)
        packs_dir = Path(args.workdir) / domain / "packs"
        packs_dir.mkdir(parents=True, exist_ok=True)
        pack_items.sort(
            key=lambda item: (
                item["issuer_id"], item["accession"], item["sentence_id"]
            )
        )
        for start in range(0, len(pack_items), rel_recall.PACK_MAX_ITEMS):
            chunk = pack_items[start:start + rel_recall.PACK_MAX_ITEMS]
            pack_no = start // rel_recall.PACK_MAX_ITEMS + 1
            pack = {
                "schema": rel_recall.PACK_SCHEMA_NAME,
                "domain": domain,
                "pack": pack_no,
                "items": chunk,
            }
            (packs_dir / f"pack_{pack_no:03d}.json").write_bytes(
                (json.dumps(pack, indent=1, sort_keys=True) + "\n").encode(
                    "utf-8"
                )
            )
        (packs_dir / "GUIDE.md").write_text(guide_text(), "utf-8")
        for issuer_id in sorted(per_issuer):
            stats = per_issuer[issuer_id]
            print(
                f"scan {domain} {issuer_id} documents={stats['documents']} "
                f"sentences={stats['sentences']} "
                f"overflow={stats['overflow']}"
            )
        pack_count = (
            len(pack_items) + rel_recall.PACK_MAX_ITEMS - 1
        ) // rel_recall.PACK_MAX_ITEMS
        print(
            f"scan {domain} total documents="
            f"{sum(s['documents'] for s in per_issuer.values())} "
            f"sentences={len(items)} packs={pack_count}"
        )
    for code in sorted(counters):
        print(f"{code} {counters[code]}")
    return 0


# --- compare ------------------------------------------------------------------


def _corpus_maps(corpus: dict):
    accession_info: dict = {}
    issuer_domain: dict = {}
    for domain in DOMAINS:
        for entry in corpus["selection"][domain]:
            issuer_domain[entry["issuer_id"]] = domain
            accession_info[entry["edition"]["accessionNumber"]] = (
                entry["issuer_id"],
                entry["edition"]["form"],
            )
    return accession_info, issuer_domain


def _sentence_rows(workdir: Path, counters: dict):
    items = []
    for domain in DOMAINS:
        path = workdir / domain / "sentences.jsonl"
        if not path.exists():
            counters["RECALL_SENTENCES_DIR_MISSING"] = (
                counters.get("RECALL_SENTENCES_DIR_MISSING", 0) + 1
            )
            continue
        items.extend(_read_jsonl(path))
    return items


def _read_annotations(annotations_dir: Path, known_ids: set, counters: dict):
    annotated: set = set()
    named_rows = []
    for path in sorted(annotations_dir.glob("*.jsonl")):
        for line in path.read_text("utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except ValueError:
                counters["RECALL_ANNOTATION_UNPARSEABLE"] = (
                    counters.get("RECALL_ANNOTATION_UNPARSEABLE", 0) + 1
                )
                continue
            if rel_recall.validate_annotation(record):
                counters["RECALL_ANNOTATION_INVALID"] = (
                    counters.get("RECALL_ANNOTATION_INVALID", 0) + 1
                )
                continue
            sid = record["sentence_id"]
            if sid not in known_ids:
                counters["RECALL_ANNOTATION_UNKNOWN_ID"] = (
                    counters.get("RECALL_ANNOTATION_UNKNOWN_ID", 0) + 1
                )
                continue
            if sid in annotated:
                counters["RECALL_ANNOTATION_DUPLICATE"] = (
                    counters.get("RECALL_ANNOTATION_DUPLICATE", 0) + 1
                )
                continue
            annotated.add(sid)
            if record["named_relationship"]:
                named_rows.append((sid, record["relationships"]))
    return annotated, named_rows


def cmd_compare(args) -> int:
    corpus = _load_corpus(args)
    _check_out(args.workdir)
    report_path = Path(
        args.report
        or (Path(args.workdir) / "recall_report.json")
    )
    _check_out(report_path)
    workdir = Path(args.workdir)
    annotations_dir = Path(args.annotations)
    if not annotations_dir.is_dir():
        raise ValueError(f"annotations dir not found: {annotations_dir}")
    inputs = rel_harvest.load_inputs(args.inputs)
    _manifest_version, manifest_issuers = package_v2.load_manifest_issuers(
        args.manifest
    )
    accession_info, issuer_domain = _corpus_maps(corpus)
    counters: dict = {}

    sentences = _sentence_rows(workdir, counters)
    known_ids = {item["sentence_id"] for item in sentences}
    sid_issuer = {}
    for item in sentences:
        accession = str(item.get("doc_id", "")).split(":", 1)[0]
        info = accession_info.get(accession)
        if info is None:
            counters["RECALL_SENTENCE_UNKNOWN_ACCESSION"] = (
                counters.get("RECALL_SENTENCE_UNKNOWN_ACCESSION", 0) + 1
            )
            continue
        sid_issuer[item["sentence_id"]] = info[0]

    annotated, named_rows = _read_annotations(
        annotations_dir, known_ids, counters
    )
    missing = len(known_ids - annotated)
    counters["RECALL_ANNOTATION_MISSING"] = missing

    ref_items: list = []
    for sid, relationships in named_rows:
        subject = sid_issuer.get(sid)
        if subject is None:
            continue
        for relationship in relationships:
            issuer_id, key, display, refusal = rel_recall.resolve_quote(
                relationship["counterparty_quote"],
                subject_issuer_id=subject,
                aliases=inputs["aliases"]["aliases"],
                resolver_rows=inputs["resolver"]["rows"],
                manifest_issuers=manifest_issuers,
            )
            if refusal:
                counters["RECALL_RESOLVE_REFUSED"] = (
                    counters.get("RECALL_RESOLVE_REFUSED", 0) + 1
                )
            ref_items.append(
                {
                    "issuer_id": subject,
                    "species": relationship["species"],
                    "key": key,
                    "sentence_id": sid,
                    "counterparty": display,
                }
            )

    extraction_dir = Path(args.extraction)
    if not extraction_dir.is_dir():
        raise ValueError(f"extraction dir not found: {extraction_dir}")
    extraction_rows: list = []
    extraction_sha256: dict = {}
    for path in sorted(extraction_dir.rglob("*.jsonl")):
        extraction_sha256[str(path.relative_to(extraction_dir))] = (
            hashlib.sha256(path.read_bytes()).hexdigest()
        )
        extraction_rows.extend(_read_jsonl(path))
    corpus_issuers = set(issuer_domain)
    pipe_set, pipe_counters = rel_recall.pipeline_triples(
        extraction_rows, corpus_issuers
    )
    counters.update(pipe_counters)

    report = rel_recall.compute_recall_report(
        ref_items=ref_items,
        pipe_set=pipe_set,
        issuer_domain=issuer_domain,
        sentences_total=len(sentences),
        annotated_count=len(annotated),
        counters=counters,
        corpus_sha256=rel_recall.CORPUS_SHA256,
        lexicon_sha256=rel_recall.lexicon_sha256(),
        extraction_sha256=extraction_sha256,
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_bytes(
        (json.dumps(report, sort_keys=True, indent=1) + "\n").encode("utf-8")
    )
    _print_report(report)
    return 0


def _print_report(report: dict) -> None:
    recall_block = report["recall"]
    print("== GMI ORCH-REL M2 recall (compare) ==")
    print(f"schema              {report['schema']}")
    print(f"corpus_sha256       {report['corpus_sha256']}")
    print(f"lexicon_sha256      {report['lexicon_sha256']}")
    print(f"sentences_total     {report['sentences']['total']}")
    print(f"sentences_annotated {report['sentences']['annotated']}")
    print(f"coverage            {report['sentences']['coverage']}")
    print(f"reference_set_size  {report['reference_set_size']}")
    print(f"pipeline_set_size   {report['pipeline_set_size']}")
    print(f"hits                {report['hits']}")
    print(f"misses              {report['misses_count']}")
    print(
        f"recall              {recall_block['value']} "
        f"(wilson95 {recall_block['wilson_95']}, "
        f"jackknife95 {recall_block['jackknife_95']} "
        f"se {recall_block['jackknife_se']} "
        f"issuers {recall_block['jackknife_issuers']})"
    )
    print("-- by domain --")
    print(f"{'domain':<8} {'ref':>5} {'hit':>5} {'miss':>5} "
          f"{'recall':>7} wilson95")
    for domain in sorted(report["by_domain"]):
        entry = report["by_domain"][domain]
        print(
            f"{domain:<8} {entry['ref']:>5} {entry['hit']:>5} "
            f"{entry['ref'] - entry['hit']:>5} "
            f"{str(entry['recall']):>7} {entry['wilson_95']}"
        )
    print("-- by species --")
    print(f"{'species':<24} {'ref':>5} {'hit':>5} {'miss':>5} "
          f"{'recall':>7} wilson95")
    for species in sorted(report["by_species"]):
        entry = report["by_species"][species]
        print(
            f"{species:<24} {entry['ref']:>5} {entry['hit']:>5} "
            f"{entry['ref'] - entry['hit']:>5} "
            f"{str(entry['recall']):>7} {entry['wilson_95']}"
        )
    print("-- per issuer --")
    print(f"{'issuer':<34} {'dom':<4} {'ref':>5} {'hit':>5} {'miss':>5}")
    for row in report["per_issuer"]:
        print(
            f"{row['issuer_id']:<34} {row['domain']:<4} {row['ref']:>5} "
            f"{row['hit']:>5} {row['miss']:>5}"
        )
    print("-- misses (every miss, never hidden) --")
    for miss in report["misses"]:
        print(
            f"MISS {miss['issuer_id']} {miss['species']} "
            f"counterparty={miss['counterparty']} key={miss['key']} "
            f"sentence_id={miss['sentence_id']}"
        )
    print("-- counters --")
    for code in sorted(report["counters"]):
        print(f"{code} {report['counters'][code]}")
    print(f"caveat {report['caveat']}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    def common(sub_parser):
        sub_parser.add_argument("--corpus", default=str(DEFAULT_CORPUS))
        sub_parser.add_argument("--workdir", required=True)

    fetch_parser = sub.add_parser("fetch")
    common(fetch_parser)
    fetch_parser.add_argument(
        "--domain", default=None, choices=list(DOMAINS),
        help="restrict to one domain (default both)",
    )
    fetch_parser.add_argument("--rps", type=float, default=2.5)
    fetch_parser.add_argument("--cache-root", default=None)

    scan_parser = sub.add_parser("scan")
    common(scan_parser)
    scan_parser.add_argument("--domain", default=None, choices=list(DOMAINS))
    scan_parser.add_argument("--cache-root", default=None)

    compare_parser = sub.add_parser("compare")
    common(compare_parser)
    compare_parser.add_argument("--annotations", required=True)
    compare_parser.add_argument("--extraction", default=str(DEFAULT_EXTRACTION))
    compare_parser.add_argument("--inputs", default=DEFAULT_INPUTS)
    compare_parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    compare_parser.add_argument("--report", default=None)

    args = parser.parse_args(argv)
    try:
        if args.command == "fetch":
            return cmd_fetch(args)
        if args.command == "scan":
            return cmd_scan(args)
        return cmd_compare(args)
    except rel_recall.CorpusDrift as error:
        print(f"relationship_m2_recall: CORPUS_DRIFT: {error}", file=sys.stderr)
        print("CORPUS_DRIFT")
        return 2
    except rel_recall.OutRefused as error:
        print(f"relationship_m2_recall: {error}", file=sys.stderr)
        print("OUT_REFUSED")
        return 2
    except ValueError as error:
        print(f"relationship_m2_recall: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

"""M2 recall annotator: frozen corpus, lexicon scan, annotation packs, compare.

Pins the frozen REL-M2-RECALL-BUILD spec at the M2 base: the frozen 40-edition
corpus (sha256-verified on every command), an independent lexicon that shares
nothing with the harvester's cue patterns, a byte-exact full-text sentence
scan with a counted overflow ceiling, blind annotation packs, the annotation
schema, the fetch ledger with counted edition mismatches and unavailable
network rows, and the compare step's reference/pipeline sets, Wilson 95%
interval, issuer-clustered jackknife, exhaustive miss list and byte-identical
reruns.  No network: fetch tests inject openers; the module-level AST test
keeps recall.py network-free.
"""
from __future__ import annotations

import ast
import hashlib
import importlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from engine.company_intelligence.relationships import edgar as rel_edgar  # noqa: E402
from engine.company_intelligence.relationships import harvest as rel_harvest  # noqa: E402
from engine.company_intelligence.relationships import package_v2  # noqa: E402
from engine.company_intelligence.relationships import recall  # noqa: E402

CORPUS_PATH = (
    REPO_ROOT
    / "research/theme_graph/gmi_relationships_20261021/m2_recall"
    / "recall_corpus_v1.json"
)
CLI = importlib.import_module("scripts.relationship_m2_recall")

AMD = "ISS:US-XNAS-AMD"
INTC = "ISS:US-XNAS-INTC"
TSM = "ISS:US-XNYS-TSM"
AMD_ACC = "0000002488-26-000018"
AMD_DOC = "amd-20251227.htm"
INTC_ACC = "0000050863-26-000011"
INTC_DOC = "intc-20251227.htm"
AMD_DOC_ID = f"{AMD_ACC}:{AMD_DOC}"
INTC_DOC_ID = f"{INTC_ACC}:{INTC_DOC}"

LEXICON_SHA = "bb0add40bc10d88a6891eef2c4b7a339c321ec19bad2a536461f6e9d5157cc70"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --- fixtures -----------------------------------------------------------------


SCAN_HTML = (
    b"<html><head><title>Form 10-K</title>"
    b"<script>var customerTracking = 1;</script>"
    b"<style>.hidden { display:none }</style></head><body>"
    b"<p>Our largest customer is Alpha Metals Incorporated. "
    b"We depend on that order flow.</p>"
    b"<p style=\"display:none\">Hidden vendor disclosure text.</p>"
    b"<p>Wafers are purchased from Taiwan Manufacturing under a "
    b"wafer supply arrangement.</p>"
    b"<p>The weather was pleasant during the quarter.</p>"
    b"</body></html>"
)


def _hidden_only_html() -> bytes:
    return (
        b"<html><head><script>if (customerCount > 2) { reload(); }</script>"
        b"<style>.supplier { color: red }</style></head><body>"
        b"<p style=\"display:none\">A vendor and a smelter agree.</p>"
        b"<p>No signal words appear in this visible line.</p>"
        b"</body></html>"
    )


def _overflow_html() -> bytes:
    parts = [b"<html><body>"]
    for k in range(4):
        parts.append(
            f"<p>Supplier number {k} ships monthly. Idle filler {k} text.</p>".encode()
        )
    parts.append(b"</body></html>")
    return b"".join(parts)


def _index_headers_html(form: str, documents: list) -> bytes:
    doc_blocks = "".join(
        f"<DOCUMENT><TYPE>{dtype}<SEQUENCE>{seq}<FILENAME>{name}\n"
        f"<DESCRIPTION>doc</DESCRIPTION><TEXT>{name}</TEXT></DOCUMENT>\n"
        for seq, (dtype, name) in enumerate(documents, start=1)
    )
    return (
        "<html><head></head><body><pre>"
        f"CONFORMED SUBMISSION TYPE: {form}\n"
        "FILED AS OF DATE: 20260204\n"
        "CONFORMED PERIOD OF REPORT: 20251227\n"
        "ACCEPTANCE-DATETIME: 20260204041452\n"
        f"{doc_blocks}"
        "</pre></body></html>"
    ).encode("utf-8")


def _fake_client(tmp_path: Path, responses: dict, offline: bool = False):
    """An EdgarClient whose opener serves canned URLs (no sleeps, no network)."""
    calls = []

    def opener(url, headers):
        calls.append(url)
        for fragment, payload in responses.items():
            if fragment in url:
                status, body = payload
                return status, {}, body
        return 404, {}, b"not found"

    clock = [0.0]
    client = rel_edgar.EdgarClient(
        cache_root=str(tmp_path / "cache"),
        rps=8.0,
        clock=lambda: clock[0],
        sleep=lambda s: clock.__setitem__(0, clock[0] + s),
        opener=opener,
        offline=offline,
    )
    client.calls = calls
    return client


def _amd_ledger_row(domain: str = "D1", state: str = "collected",
                    reason: str | None = None) -> dict:
    return {
        "domain": domain,
        "leaf": f"recall-{domain}",
        "issuer_id": AMD,
        "cik": "0000002488",
        "sec_name": "ADVANCED MICRO DEVICES INC",
        "accession": AMD_ACC,
        "form": "10-K",
        "filing_role": "latest",
        "state": state,
        "reason": reason,
        "accepted_at": "2026-02-04T09:14:52Z",
        "sec_index_header_acceptance_et": "20260204041452",
        "sec_submissions_acceptance_raw": "2026-02-04T04:14:52.000Z",
        "census_fetched_at": None,
        "filed_at": "2026-02-04",
        "period_of_report": "2025-12-27",
        "notes": [],
        "documents": [
            {
                "filename": AMD_DOC,
                "type": "10-K",
                "state": "cached",
                "reason": None,
                "http_status": 200,
                "sha256": _sha(SCAN_HTML),
                "byte_length": len(SCAN_HTML),
                "fetched_at": "2026-01-01T00:00:00Z",
            }
        ],
    }


def _seed_cache(tmp_path: Path, cik: int, accession: str, filename: str,
                body: bytes) -> None:
    cache = rel_edgar.EdgarCache(str(tmp_path / "cache"))
    cache.store(
        cik, accession.replace("-", ""), filename, body,
        f"https://www.sec.gov/Archives/edgar/data/{cik}/x/{filename}", 200,
        "2026-01-01T00:00:00Z",
    )


def _write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        for row in rows:
            handle.write((json.dumps(row, sort_keys=True) + "\n").encode("utf-8"))


def _sentence_item(doc_id: str, byte_start: int, byte_end: int, text: str,
                   terms: list) -> dict:
    return {
        "sentence_id": recall.sentence_id(doc_id, byte_start, byte_end),
        "doc_id": doc_id,
        "byte_start": byte_start,
        "byte_end": byte_end,
        "raw_sha256": _sha(f"{doc_id} {byte_start} {text}".encode("utf-8")),
        "text": text,
        "terms": terms,
    }


def _annotation(sentence_id: str, relationships: list, *,
                named: bool = True, unclear: bool = False) -> dict:
    return {
        "schema": recall.ANNOTATION_SCHEMA_NAME,
        "sentence_id": sentence_id,
        "annotator": {"agent": "test-annotator", "lane_run_id": "lane-test"},
        "named_relationship": named,
        "unclear": unclear,
        "relationships": [
            {
                "counterparty_quote": quote,
                "species": species,
                "subject_role": role,
            }
            for quote, species, role in relationships
        ],
    }


def _synthetic_compare_workdir(tmp_path: Path) -> dict:
    """Four annotated sentences (AMD x2, INTC x2) + a synthetic extraction dir.

    REF has 4 triples, PIPE covers 3 of them: recall 3/4 with one named miss
    (INTC x "Acme Widgets").  One extra sentence is never annotated (missing),
    one more is annotated unclear (excluded from REF).
    """
    workdir = tmp_path / "workdir"
    items = [
        _sentence_item(AMD_DOC_ID, 100, 200, "Our largest customer is Intel.",
                       ["customer"]),
        _sentence_item(AMD_DOC_ID, 300, 400,
                       "Wafers are purchased from Acme Widgets.", ["purchased from"]),
        _sentence_item(INTC_DOC_ID, 100, 200,
                       "Foundries are contracted through TSMC.", ["foundries"]),
        _sentence_item(INTC_DOC_ID, 300, 400,
                       "Supplies come from Acme Widgets.", ["supplier"]),
        _sentence_item(AMD_DOC_ID, 500, 600,
                       "A vendor paragraph that is never annotated.", ["vendor"]),
        _sentence_item(AMD_DOC_ID, 700, 800,
                       "An unclear disclosure about partners.", ["partner"]),
    ]
    _write_jsonl(workdir / "D1" / "sentences.jsonl", items)
    sid = [item["sentence_id"] for item in items]
    annotations = [
        _annotation(sid[0], [("Intel", "supplier_customer", None)]),
        _annotation(sid[1], [("Acme Widgets", "supplier_customer", None)]),
        _annotation(sid[2], [("TSMC", "supplier_customer", None)]),
        _annotation(sid[3], [("Acme Widgets", "supplier_customer", None)]),
        _annotation(sid[5], [], named=False, unclear=True),
    ]
    anndir = tmp_path / "annotations"
    _write_jsonl(anndir / "annotator_a.jsonl", annotations)
    sc = "supplier_customer"
    obs = [
        {"row_kind": "observation", "species": sc,
         "subject": {"issuer_id": AMD},
         "object": {"issuer_id": INTC, "name_as_filed": "Intel"}},
        {"row_kind": "observation", "species": sc,
         "subject": {"issuer_id": AMD},
         "object": {"issuer_id": None, "name_as_filed": "Acme Widgets"}},
        {"row_kind": "observation", "species": sc,
         "subject": {"issuer_id": INTC},
         "object": {"issuer_id": TSM, "name_as_filed": "TSMC"}},
        {"row_kind": "observation", "species": sc,
         "subject": {"issuer_id": "ISS:US-XNAS-SWKS"},
         "object": {"issuer_id": "ISS:US-XNAS-AAPL", "name_as_filed": "Apple"}},
        {"row_kind": "coverage", "species": None,
         "subject": {"issuer_id": AMD}, "object": {}},
    ]
    extraction = tmp_path / "extraction"
    _write_jsonl(extraction / "synthetic_m2.jsonl", obs)
    return {
        "workdir": workdir,
        "annotations": anndir,
        "extraction": extraction,
        "sentence_ids": sid,
    }


def _run_cli(*argv: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env.setdefault("GMI_EDGAR_OFFLINE", "1")
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts/relationship_m2_recall.py")]
        + list(argv),
        capture_output=True, text=True, env=env,
    )


# --- frozen corpus ------------------------------------------------------------


def test_corpus_frozen_bytes_and_counts():
    raw = CORPUS_PATH.read_bytes()
    assert _sha(raw) == recall.CORPUS_SHA256
    doc = json.loads(raw.decode("utf-8"))
    assert doc["schema"] == recall.CORPUS_SCHEMA
    assert len(doc["selection"]["D1"]) == 20
    assert len(doc["selection"]["D2"]) == 20


# --- R1 lexicon -----------------------------------------------------------------


def test_lexicon_frozen_sha256():
    assert recall.lexicon_sha256() == LEXICON_SHA
    assert isinstance(recall.LEXICON, tuple)
    assert all(term == term.lower() for term in recall.LEXICON)
    assert recall.PREFIX_TERMS == frozenset(
        {"royalt", "collaborat", "licens", "distribut", "contract manufactur"}
    )


def test_lexicon_shares_no_harvest_cue_pattern():
    source = (REPO_ROOT / "engine/company_intelligence/relationships/recall.py").read_text("utf-8")
    for name in (
        "CUE_PATTERNS",
        "build_hints",
        "MAX_CANDIDATES_PER_DOCUMENT",
        "MAX_CANDIDATES_PER_FILING",
        "_ANON_RE",
        "_best_rank",
        "extract_document_candidates",
    ):
        assert name not in source
        assert not hasattr(recall, name)


# --- R2 scan --------------------------------------------------------------------


def test_scan_emits_every_lexicon_sentence_with_exact_bytes():
    doc_id = "0000002488-26-000018:amd-20251227.htm"
    items = recall.scan(SCAN_HTML, doc_id=doc_id)
    texts = [item["text"] for item in items]
    assert len(items) == 3
    assert any("largest customer" in text for text in texts)
    assert any("depend on that order flow" in text for text in texts)
    assert any("purchased from Taiwan Manufacturing" in text for text in texts)
    assert not any("weather" in text for text in texts)
    for item in items:
        raw_slice = SCAN_HTML[item["byte_start"]:item["byte_end"]]
        assert raw_slice.decode("utf-8", "replace") in SCAN_HTML.decode("latin-1")
        assert _sha(raw_slice) == item["raw_sha256"]
        assert package_v2.normalize_span(raw_slice) == item["text"]
        assert item["doc_id"] == doc_id
        assert item["sentence_id"] == recall.sentence_id(
            doc_id, item["byte_start"], item["byte_end"]
        )
        assert item["sentence_id"].startswith("rs:")
        assert len(item["sentence_id"]) == 23
        assert item["terms"] == sorted(item["terms"])
        assert item["terms"]
    by_text = {item["text"]: item["terms"] for item in items}
    assert "customer" in next(terms for text, terms in by_text.items()
                              if "largest customer" in text)
    assert "depend" in next(terms for text, terms in by_text.items()
                            if "depend on that order flow" in text)
    assert "purchased from" in next(terms for text, terms in by_text.items()
                                    if "purchased from" in text)


def test_scan_skips_hidden_and_script_text():
    items = recall.scan(_hidden_only_html(), doc_id="acc:hidden.htm")
    assert items == []


def test_scan_overflow_counted_not_dropped():
    items, overflow = recall.scan_with_overflow(
        _overflow_html(), doc_id="acc:over.htm", max_sentences=2
    )
    assert len(items) == 2
    assert overflow == 2
    # the uncapped scan signature still emits all four (no silent drop)
    assert len(recall.scan(_overflow_html(), doc_id="acc:over.htm")) == 4


def test_sentence_id_stable():
    first = recall.scan(SCAN_HTML, doc_id="acc:one.htm")
    again = recall.scan(SCAN_HTML, doc_id="acc:one.htm")
    assert [item["sentence_id"] for item in first] == [
        item["sentence_id"] for item in again
    ]
    other = recall.scan(SCAN_HTML, doc_id="acc:two.htm")
    assert [item["sentence_id"] for item in first] != [
        item["sentence_id"] for item in other
    ]
    assert re.fullmatch(r"rs:[0-9a-f]{20}", first[0]["sentence_id"])


# --- R5 annotation schema ---------------------------------------------------------


def test_annotation_schema_accepts_and_rejects():
    good = _annotation("rs:" + "a" * 20, [("Intel", "supplier_customer", None)])
    assert recall.validate_annotation(good) == []
    named_role = _annotation("rs:" + "a" * 20, [("Intel", "supplier_customer", "customer")])
    assert recall.validate_annotation(named_role) == []
    unclear = _annotation("rs:" + "b" * 20, [], named=False, unclear=True)
    assert recall.validate_annotation(unclear) == []
    empty = _annotation("rs:" + "c" * 20, [], named=False)
    assert recall.validate_annotation(empty) == []

    def rejected(record: dict, needle: str) -> None:
        problems = recall.validate_annotation(record)
        assert problems, f"expected rejection: {record}"
        assert any(needle in problem for problem in problems)

    named_empty = _annotation("rs:" + "d" * 20, [])
    rejected(named_empty, "NAMED_REQUIRES_RELATIONSHIPS")
    unclear_named = _annotation("rs:" + "e" * 20,
                                [("Intel", "supplier_customer", None)], unclear=True)
    rejected(unclear_named, "UNCLEAR_REQUIRES_NO_RELATIONSHIPS")
    unclear_with_rels = _annotation("rs:" + "f" * 20,
                                    [("Intel", "supplier_customer", None)],
                                    named=False, unclear=True)
    rejected(unclear_with_rels, "UNCLEAR_REQUIRES_NO_RELATIONSHIPS")
    rels_without_named = _annotation("rs:" + "0" * 20,
                                     [("Intel", "supplier_customer", None)],
                                     named=False)
    rejected(rels_without_named, "RELATIONSHIPS_REQUIRE_NAMED")
    bad_species = _annotation("rs:" + "1" * 20, [("Intel", "joint_venture", None)])
    rejected(bad_species, "species")
    bad_role = _annotation("rs:" + "2" * 20, [("Intel", "supplier_customer", "pilot")])
    rejected(bad_role, "subject_role")
    extra = dict(good)
    extra["surprise"] = True
    rejected(extra, "Additional properties are not allowed")
    missing = {k: v for k, v in good.items() if k != "named_relationship"}
    rejected(missing, "named_relationship")


# --- R3 fetch -------------------------------------------------------------------


def _fetch_args(tmp_path: Path, domain: str = "D1",
                workdir_name: str = "workdir") -> argparse_namespace:
    import argparse

    return argparse.Namespace(
        command="fetch",
        corpus=str(CORPUS_PATH),
        workdir=str(tmp_path / workdir_name),
        domain=domain,
        rps=8.0,
        cache_root=str(tmp_path / "cache"),
        inputs=str(REPO_ROOT / "research/theme_graph/gmi_relationships_20261021/m2_inputs"),
    )


def test_fetch_edition_mismatch_counted(tmp_path, monkeypatch):
    selection = json.loads(CORPUS_PATH.read_text("utf-8"))["selection"]["D1"]
    pinned, second = selection[0], selection[1]
    wrong_form = _index_headers_html(
        "8-K", [(pinned["edition"]["form"], pinned["edition"]["primaryDocument"])]
    )
    wrong_docs = _index_headers_html(
        pinned["edition"]["form"], [("EX-99.1", "other.htm")]
    )
    responses = {
        pinned["edition"]["accessionNumber"]: (200, wrong_form),
        second["edition"]["accessionNumber"]: (200, wrong_docs),
    }
    client = _fake_client(tmp_path, responses)
    monkeypatch.setattr(CLI, "build_client", lambda args: client)
    args = _fetch_args(tmp_path)
    assert CLI.cmd_fetch(args) == 0
    ledger = tmp_path / "workdir" / "D1" / "fetch_ledger.jsonl"
    rows = [json.loads(line) for line in ledger.read_text("utf-8").splitlines()]
    assert len(rows) == 20
    mismatches = [row for row in rows if row["state"] == "edition_mismatch"]
    assert len(mismatches) == 2
    assert all(row["reason"] == "CORPUS_EDITION_MISMATCH" for row in mismatches)
    assert {row["issuer_id"] for row in mismatches} == {
        pinned["issuer_id"], second["issuer_id"],
    }
    # the pinned edition is never substituted
    assert all(row["form"] == "10-K" for row in mismatches)


def test_fetch_unavailable_row_on_http_error(tmp_path, monkeypatch):
    http_client = _fake_client(tmp_path, {"index-headers": (404, b"nope")})
    monkeypatch.setattr(CLI, "build_client", lambda args: http_client)
    args = _fetch_args(tmp_path, domain="D2")
    assert CLI.cmd_fetch(args) == 0
    ledger = tmp_path / "workdir" / "D2" / "fetch_ledger.jsonl"
    rows = [json.loads(line) for line in ledger.read_text("utf-8").splitlines()]
    assert rows
    assert all(row["state"] == "unavailable" for row in rows)
    assert all(row["reason"] == "HTTP_404" for row in rows)

    offline_client = _fake_client(tmp_path, {}, offline=True)
    monkeypatch.setattr(CLI, "build_client", lambda args: offline_client)
    args = _fetch_args(tmp_path, domain="D2", workdir_name="offline")
    assert CLI.cmd_fetch(args) == 0
    ledger = tmp_path / "offline" / "D2" / "fetch_ledger.jsonl"
    rows = [json.loads(line) for line in ledger.read_text("utf-8").splitlines()]
    assert rows
    assert all(row["state"] == "unavailable" for row in rows)
    assert all(row["reason"] == "NETWORKDISABLED" for row in rows)


# --- R4 packs -------------------------------------------------------------------


def test_packs_blind_to_offsets_and_hashes(tmp_path):
    workdir = tmp_path / "workdir"
    _write_jsonl(workdir / "D1" / "fetch_ledger.jsonl", [_amd_ledger_row()])
    _seed_cache(tmp_path, 2488, AMD_ACC, AMD_DOC, SCAN_HTML)
    result = _run_cli(
        "scan", "--workdir", str(workdir), "--domain", "D1",
        "--corpus", str(CORPUS_PATH), "--cache-root", str(tmp_path / "cache"),
    )
    assert result.returncode == 0, result.stderr
    sentences = [
        json.loads(line)
        for line in (workdir / "D1" / "sentences.jsonl").read_text("utf-8").splitlines()
    ]
    assert sentences
    assert all(
        set(item) == {
            "sentence_id", "doc_id", "byte_start", "byte_end", "raw_sha256",
            "text", "terms",
        }
        for item in sentences
    )
    packs_dir = workdir / "D1" / "packs"
    pack_paths = sorted(packs_dir.glob("pack_*.json"))
    assert pack_paths
    total_items = 0
    for pack_path in pack_paths:
        pack_bytes = pack_path.read_bytes()
        assert b"byte_start" not in pack_bytes
        assert b"byte_end" not in pack_bytes
        assert b"raw_sha256" not in pack_bytes
        pack = json.loads(pack_bytes.decode("utf-8"))
        assert pack["schema"] == recall.PACK_SCHEMA_NAME
        assert len(pack["items"]) <= 40
        for item in pack["items"]:
            total_items += 1
            assert set(item) == {
                "sentence_id", "issuer_id", "sec_name", "form", "accession",
                "text",
            }
    assert total_items == len(sentences)
    guide = (packs_dir / "GUIDE.md").read_text("utf-8")
    assert "Judge ONLY from the sentence text" in guide
    assert recall.ANNOTATION_SCHEMA_NAME in guide
    assert "generic risk language" in guide.lower()
    assert "exact substrings" in guide


# --- R6 compare -------------------------------------------------------------------


def _run_compare(tmp_path: Path, fixture: dict, report_name: str = "recall_report.json"):
    report_path = fixture["workdir"] / report_name
    return _run_cli(
        "compare", "--workdir", str(fixture["workdir"]),
        "--annotations", str(fixture["annotations"]),
        "--extraction", str(fixture["extraction"]),
        "--corpus", str(CORPUS_PATH), "--report", str(report_path),
    ), report_path


def test_compare_reference_and_pipeline_sets_and_recall(tmp_path):
    fixture = _synthetic_compare_workdir(tmp_path)
    result, report_path = _run_compare(tmp_path, fixture)
    assert result.returncode == 0, result.stderr
    report = json.loads(report_path.read_bytes().decode("utf-8"))
    assert report["schema"] == recall.REPORT_SCHEMA_NAME
    assert report["reference_set_size"] == 4
    assert report["pipeline_set_size"] == 3
    assert report["hits"] == 3
    assert report["misses_count"] == 1
    assert report["recall"]["value"] == 0.75
    assert report["recall"]["wilson_95"] == [0.3006, 0.9544]
    assert "Misses outside both the harvester cue patterns and the recall lexicon are not measured." == (
        report["caveat"]
    )
    assert report["corpus_sha256"] == recall.CORPUS_SHA256
    assert report["lexicon_sha256"] == recall.lexicon_sha256()
    assert report["extraction_sha256"]
    table = result.stdout
    assert "recall" in table and "wilson" in table.lower()
    assert AMD in table and INTC in table
    assert "D1" in table


def test_compare_lists_every_miss(tmp_path):
    fixture = _synthetic_compare_workdir(tmp_path)
    result, report_path = _run_compare(tmp_path, fixture)
    assert result.returncode == 0, result.stderr
    report = json.loads(report_path.read_bytes().decode("utf-8"))
    assert len(report["misses"]) == 1
    miss = report["misses"][0]
    assert miss["issuer_id"] == INTC
    assert miss["species"] == "supplier_customer"
    assert miss["counterparty"] == "Acme Widgets"
    assert miss["sentence_id"] == fixture["sentence_ids"][3]
    assert miss["domain"] == "D1"
    assert miss["key"] == "name:acme widgets"
    assert fixture["sentence_ids"][3] in result.stdout
    assert "MISS" in result.stdout


def test_compare_jackknife_by_issuer(tmp_path):
    fixture = _synthetic_compare_workdir(tmp_path)
    result, report_path = _run_compare(tmp_path, fixture)
    assert result.returncode == 0, result.stderr
    report = json.loads(report_path.read_bytes().decode("utf-8"))
    jack = report["recall"]["jackknife_95"]
    # leave-one-out recalls: drop AMD -> 1/2 = 0.5; drop INTC -> 2/2 = 1.0;
    # mean 0.75, se = sqrt((2-1)/2 * (0.25^2 + 0.25^2)) = 0.25
    assert report["recall"]["jackknife_se"] == 0.25
    assert jack == [0.26, 1.0]
    assert jack != report["recall"]["wilson_95"]
    assert report["recall"]["jackknife_issuers"] == 2


def test_compare_missing_annotation_excluded_and_counted(tmp_path):
    fixture = _synthetic_compare_workdir(tmp_path)
    result, report_path = _run_compare(tmp_path, fixture)
    assert result.returncode == 0, result.stderr
    report = json.loads(report_path.read_bytes().decode("utf-8"))
    assert report["counters"]["RECALL_ANNOTATION_MISSING"] == 1
    assert report["sentences"]["total"] == 6
    assert report["sentences"]["annotated"] == 5
    assert report["sentences"]["coverage"] == round(5 / 6, 4)
    assert report["reference_set_size"] == 4


def test_compare_refuses_data_and_site_out(tmp_path):
    fixture = _synthetic_compare_workdir(tmp_path)
    for guarded in ("data", "site"):
        out = REPO_ROOT / guarded / "recall_out_refusal_test"
        result = _run_cli(
            "compare", "--workdir", str(fixture["workdir"]),
            "--annotations", str(fixture["annotations"]),
            "--extraction", str(fixture["extraction"]),
            "--corpus", str(CORPUS_PATH), "--report", str(out),
        )
        assert result.returncode == 2, (guarded, result.stdout, result.stderr)
        assert "OUT_REFUSED" in result.stdout + result.stderr
        assert not out.exists()


def test_compare_rerun_byte_identical(tmp_path):
    fixture = _synthetic_compare_workdir(tmp_path)
    result_one, report_one = _run_compare(tmp_path, fixture, "report_one.json")
    assert result_one.returncode == 0, result_one.stderr
    result_two, report_two = _run_compare(tmp_path, fixture, "report_two.json")
    assert result_two.returncode == 0, result_two.stderr
    assert report_one.read_bytes() == report_two.read_bytes()
    stdout_lines_one = [
        line for line in result_one.stdout.splitlines() if line.strip()
    ]
    stdout_lines_two = [
        line for line in result_two.stdout.splitlines() if line.strip()
    ]
    assert stdout_lines_one == stdout_lines_two


def test_cli_corpus_drift_refused(tmp_path):
    fixture = _synthetic_compare_workdir(tmp_path)
    doctored = tmp_path / "corpus_doctored.json"
    doc = json.loads(CORPUS_PATH.read_text("utf-8"))
    doc["selection"]["D1"] = doc["selection"]["D1"][:19]
    doctored.write_text(json.dumps(doc), "utf-8")
    result = _run_cli(
        "compare", "--workdir", str(fixture["workdir"]),
        "--annotations", str(fixture["annotations"]),
        "--extraction", str(fixture["extraction"]),
        "--corpus", str(doctored),
    )
    assert result.returncode == 2
    assert "CORPUS_DRIFT" in result.stdout + result.stderr


# --- no network ----------------------------------------------------------------


def test_recall_module_imports_no_network():
    source = (REPO_ROOT / "engine/company_intelligence/relationships/recall.py").read_text("utf-8")
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])
    banned = {"urllib", "requests", "http", "socket", "ssl", "ftplib"}
    assert not (imported & banned), imported & banned
    for name in ("urllib", "requests", "http.client", "socket"):
        assert name not in source

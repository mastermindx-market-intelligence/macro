"""M2 cap-fix lane: per-filing caps, doc-order tie-break, unjudged packing.

Pins the REL-M2-CAPFIX contract: ``MAX_CANDIDATES_PER_FILING`` is a
per-accession cap (not a per-leaf cap), ``_doc_index`` breaks rank ties, and
``pack --exclude-judged`` leaves already-judged candidates out of the packs
without changing a single byte of a plain ``pack`` run.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from engine.company_intelligence.relationships import harvest as rel_harvest  # noqa: E402
from engine.company_intelligence.relationships import judge as rel_judge  # noqa: E402

CLI_HARVEST = importlib.import_module("scripts.relationship_m2_harvest")
CLI_JUDGE = importlib.import_module("scripts.relationship_m2_judge")

SWKS = "ISS:US-XNAS-SWKS"
FILER_NAME = "SKYWORKS SOLUTIONS, INC."
ACC = "0000004127-25-000085"
ACC_NODASH = "000000412725000085"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _synthetic_cand(rank, accession, doc_index, byte_start, cand_id):
    """One in-memory candidate in the shape the cap functions consume."""
    return {
        "candidate_id": cand_id,
        "rank": rank,
        "_accession": accession,
        "_doc_index": doc_index,
        "span": {"byte_start": byte_start, "byte_end": byte_start + 100},
    }


# --- apply_per_filing_caps ------------------------------------------------------


def test_two_filings_capped_independently():
    cands = [
        _synthetic_cand(1, "0000004127-25-000001", k % 3, k * 200,
                        f"cand:a{k:03d}")
        for k in range(130)
    ] + [
        _synthetic_cand(1, "0000004127-25-000002", k % 3, k * 200,
                        f"cand:b{k:03d}")
        for k in range(130)
    ]
    per_filing = rel_harvest.new_counters()
    kept = rel_harvest.apply_per_filing_caps(cands, per_filing)
    assert len(kept) == 240
    by_accession: dict = {}
    for cand in kept:
        by_accession.setdefault(cand["_accession"], []).append(cand)
    assert sorted(
        (accession, len(group)) for accession, group in by_accession.items()
    ) == [("0000004127-25-000001", 120), ("0000004127-25-000002", 120)]
    assert per_filing["overflow_filing"] == 20
    # the old single leaf-wide call on the same list keeps only 120
    leaf_wide = rel_harvest.new_counters()
    kept_old = rel_harvest.apply_filing_caps(cands, leaf_wide)
    assert len(kept_old) == 120


def test_small_filing_untouched():
    cands = [
        _synthetic_cand(1, "0000004127-25-000003", 0, k * 50, f"cand:s{k}")
        for k in range(7)
    ]
    counters = rel_harvest.new_counters()
    kept = rel_harvest.apply_per_filing_caps(cands, counters)
    assert len(kept) == 7
    assert counters["overflow_filing"] == 0


def test_doc_index_breaks_rank_ties():
    # 121 rank-1 candidates, identical byte_start, doc_index 0..120: the
    # highest _doc_index is the one dropped
    cands = [
        _synthetic_cand(1, "0000004127-25-000085", doc_index, 500,
                        f"cand:t{doc_index:03d}")
        for doc_index in range(121)
    ]
    counters = rel_harvest.new_counters()
    kept = rel_harvest.apply_per_filing_caps(cands, counters)
    assert len(kept) == 120
    assert counters["overflow_filing"] == 1
    assert {c["_doc_index"] for c in kept} == set(range(120))


def test_missing_accession_fails_closed():
    counters = rel_harvest.new_counters()
    cand = _synthetic_cand(1, None, 0, 0, "cand:x")
    del cand["_accession"]
    with pytest.raises(ValueError):
        rel_harvest.apply_per_filing_caps([cand], counters)


# --- cmd_candidates wires _doc_index / _accession --------------------------------


def _write_synthetic_inputs(tmp_path, monkeypatch):
    resolver_doc = {
        "schema": "orch_rel.m2_resolver_us_issuers/v1",
        "rows": [
            {
                "issuer_id": SWKS,
                "cik": 4127,
                "sec_name": FILER_NAME,
                "tickers": ["SWKS"],
                "securities": ["SEC:US-XNAS-SWKS"],
                "sic": "3674",
                "annual_forms": ["10-K"],
                "census_state": "OK",
            },
            {
                "issuer_id": "ISS:US-XNAS-AAPL",
                "cik": 320193,
                "sec_name": "Apple Inc.",
                "tickers": ["AAPL"],
                "securities": ["SEC:US-XNAS-AAPL"],
                "sic": "3571",
                "annual_forms": ["10-K"],
                "census_state": "OK",
            },
        ],
    }
    aliases_doc = {
        "schema": "orch_rel.m2_curated_aliases/v1",
        "aliases": [
            {
                "alias": "Skyworks",
                "alias_norm": "skyworks",
                "issuer_id": SWKS,
                "target": "issuer",
                "non_edge_reason": None,
                "cn_security_id": None,
                "basis": "test",
            },
        ],
    }
    census = {
        "schema": "orch_rel.m2_filing_census/v1",
        "issuers": {
            SWKS: {
                "cik": 4127,
                "domain": "D1",
                "state": "OK",
                "sec_name": FILER_NAME,
                "fetched_at": "2026-10-22T01:50:17Z",
                "latest": {
                    "acceptanceDateTime": "2025-11-08T02:08:12.000Z",
                    "accessionNumber": ACC,
                    "filingDate": "2025-11-07",
                    "form": "10-K",
                    "isInlineXBRL": 1,
                    "isXBRL": 1,
                    "primaryDocument": "doc10k.htm",
                    "reportDate": "2025-10-03",
                },
                "amendments_of_latest": [],
                "prior": None,
                "amendments_of_prior": [],
            }
        },
    }
    leaves = {"schema": "orch_rel.m2_leaves/v1", "leaves": {"P": [SWKS]}}
    blobs = {
        "leaves_v1.json": leaves,
        "filing_census_v1.json": census,
        "curated_aliases_v1.json": aliases_doc,
        "resolver_us_issuers_v1.json": resolver_doc,
    }
    inputs = tmp_path / "m2_inputs"
    inputs.mkdir()
    pins = {}
    for name, doc in blobs.items():
        raw = (json.dumps(doc, sort_keys=True) + "\n").encode("utf-8")
        (inputs / name).write_bytes(raw)
        pins[name] = _sha(raw)
    monkeypatch.setattr(rel_harvest, "PINS", pins)
    return inputs


def _cache_document(cache_dir, filename, body):
    path = cache_dir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    meta = {
        "url": (
            "https://www.sec.gov/Archives/edgar/data/4127/" + ACC_NODASH
            + "/" + filename
        ),
        "sha256": _sha(body),
        "byte_length": len(body),
        "http_status": 200,
        "fetched_at": "2026-10-22T02:00:00Z",
    }
    Path(str(path) + ".meta.json").write_bytes(
        json.dumps(meta, sort_keys=True).encode("utf-8")
    )
    return meta


PRIMARY_DOC = (
    "<html><head><title>x</title></head><body>"
    "<p>Apple, in the aggregate accounted for 3% of the Company's "
    "net revenue.</p></body></html>"
).encode("utf-8")
EXHIBIT_DOC = (
    "<html><head><title>y</title></head><body>"
    "<p>Apple remained our largest customer in fiscal 2025.</p>"
    "</body></html>"
).encode("utf-8")


def _write_two_doc_ledger(workdir, monkeypatch):
    cache_dir = workdir.parent / "cache" / "4127" / ACC_NODASH
    meta_primary = _cache_document(cache_dir, "doc10k.htm", PRIMARY_DOC)
    meta_exhibit = _cache_document(cache_dir, "ex13.htm", EXHIBIT_DOC)
    monkeypatch.setenv("GMI_EDGAR_CACHE", str(workdir.parent / "cache"))
    row = {
        "leaf": "P",
        "issuer_id": SWKS,
        "cik": "0000004127",
        "sec_name": FILER_NAME,
        "accession": ACC,
        "form": "10-K",
        "filing_role": "latest",
        "state": "collected",
        "reason": None,
        "accepted_at": "2025-11-07T21:08:12Z",
        "sec_index_header_acceptance_et": "20251107160812",
        "sec_submissions_acceptance_raw": "2025-11-08T02:08:12.000Z",
        "census_fetched_at": "2026-10-22T01:50:17Z",
        "filed_at": "2025-11-07",
        "period_of_report": "2025-10-03",
        "notes": [],
        "documents": [
            {
                "filename": "doc10k.htm",
                "type": "10-K",
                "state": "fetched",
                "reason": None,
                "http_status": 200,
                "sha256": meta_primary["sha256"],
                "byte_length": len(PRIMARY_DOC),
                "fetched_at": meta_primary["fetched_at"],
            },
            {
                "filename": "ex13.htm",
                "type": "EX-13.1",
                "state": "fetched",
                "reason": None,
                "http_status": 200,
                "sha256": meta_exhibit["sha256"],
                "byte_length": len(EXHIBIT_DOC),
                "fetched_at": meta_exhibit["fetched_at"],
            },
        ],
    }
    workdir.mkdir(parents=True)
    (workdir / "fetch_ledger.jsonl").write_bytes(
        (json.dumps(row, sort_keys=True) + "\n").encode("utf-8")
    )


def test_cmd_candidates_sets_doc_index_and_accession(tmp_path, monkeypatch):
    inputs = _write_synthetic_inputs(tmp_path, monkeypatch)
    workdir = tmp_path / "work" / "P"
    _write_two_doc_ledger(workdir, monkeypatch)
    captured: list = []

    def _capture(cands, counters, max_filing=None):
        captured.extend(cands)
        return list(cands)

    monkeypatch.setattr(
        rel_harvest, "apply_per_filing_caps", _capture, raising=False
    )
    rc = CLI_HARVEST.main(
        [
            "candidates", "--leaf", "P",
            "--workdir", str(tmp_path / "work"),
            "--inputs", str(inputs),
        ]
    )
    assert rc == 0
    assert captured, "expected candidates from both documents"
    seen_docs = {}
    for cand in captured:
        assert cand["_accession"] == ACC
        seen_docs.setdefault(cand["_doc_index"], set()).add(
            cand["span"]["byte_start"]
        )
    # document order: doc10k.htm is 1, ex13.htm is 2 — both contribute
    assert sorted(seen_docs) == [1, 2]
    # underscore keys never reach candidates.jsonl
    out_rows = [
        json.loads(line)
        for line in (workdir / "candidates.jsonl")
        .read_text("utf-8")
        .splitlines()
    ]
    assert out_rows
    for row in out_rows:
        assert not any(key.startswith("_") for key in row)


# --- pack --exclude-judged -------------------------------------------------------


def _pack_candidate(cand_id, byte_start):
    return {
        "candidate_id": cand_id,
        "issuer_id": SWKS,
        "sec_name": FILER_NAME,
        "accession": ACC,
        "primary_document": "doc10k.htm",
        "form": "10-K",
        "filing_role": "latest",
        "origin": "cue",
        "rank": 1,
        "cues": ["major_customer"],
        "hints": ["apple"],
        "period_of_report": "2025-10-03",
        "xbrl_facts": [],
        "excerpt": {
            "span": {
                "byte_start": byte_start,
                "byte_end": byte_start + 10,
                "normalized": f"candidate {cand_id} text",
            },
        },
    }


def _write_candidates(workdir, cands):
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "candidates.jsonl").write_bytes(
        b"".join(
            (json.dumps(cand, sort_keys=True) + "\n").encode("utf-8")
            for cand in cands
        )
    )


def _pack_bytes(packs_dir: Path) -> list:
    return [
        (path.name, path.read_bytes())
        for path in sorted(packs_dir.iterdir())
    ]


def test_pack_exclude_judged(tmp_path, monkeypatch):
    inputs = _write_synthetic_inputs(tmp_path, monkeypatch)
    workdir = tmp_path / "work"
    cands = [
        _pack_candidate(f"cand:{k}", 100 * k) for k in range(5)
    ]
    _write_candidates(workdir / "P", cands)
    judged = workdir / "judged.jsonl"
    judged.write_bytes(
        b"".join(
            (
                json.dumps(
                    {"candidate_id": cand_id, "decision": "edge_yes"},
                    sort_keys=True,
                )
                + "\n"
            ).encode("utf-8")
            for cand_id in ("cand:0", "cand:3", "cand:unknown-1")
        )
    )
    rc = CLI_JUDGE.main(
        [
            "pack", "--leaf", "P",
            "--workdir", str(workdir),
            "--inputs", str(inputs),
            "--exclude-judged", str(judged),
        ]
    )
    assert rc == 0
    index = json.loads(
        (workdir / "P" / "packs" / "index.json").read_text("utf-8")
    )
    packed_ids = [
        cand_id
        for pack in index["packs"]
        for cand_id in pack["candidate_ids"]
    ]
    assert sorted(packed_ids) == ["cand:1", "cand:2", "cand:4"]
    full_sha = _sha((workdir / "P" / "candidates.jsonl").read_bytes())
    assert index["candidates_sha256"] == full_sha
    assert index["excluded_judged"] == 2


def test_pack_exclude_judged_directory(tmp_path, monkeypatch, capsys):
    inputs = _write_synthetic_inputs(tmp_path, monkeypatch)
    workdir = tmp_path / "work"
    _write_candidates(
        workdir / "P", [_pack_candidate(f"cand:{k}", 100 * k) for k in range(5)]
    )
    judgments_dir = workdir / "P" / "judgments"
    judgments_dir.mkdir(parents=True)
    (judgments_dir / "prior.jsonl").write_bytes(
        (json.dumps({"candidate_id": "cand:1"}) + "\n").encode("utf-8")
    )
    (judgments_dir / "more.jsonl").write_bytes(
        b"not json at all\n"
        + (json.dumps({"candidate_id": "cand:4"}) + "\n").encode("utf-8")
    )
    rc = CLI_JUDGE.main(
        [
            "pack", "--leaf", "P",
            "--workdir", str(workdir),
            "--inputs", str(inputs),
            "--exclude-judged", str(judgments_dir),
        ]
    )
    assert rc == 0
    index = json.loads(
        (workdir / "P" / "packs" / "index.json").read_text("utf-8")
    )
    packed_ids = [
        cand_id
        for pack in index["packs"]
        for cand_id in pack["candidate_ids"]
    ]
    assert sorted(packed_ids) == ["cand:0", "cand:2", "cand:3"]
    assert index["excluded_judged"] == 2
    out = capsys.readouterr().out
    assert "exclude_unknown=0" in out
    assert "excluded=2" in out


def test_pack_without_flag_is_byte_identical(tmp_path, monkeypatch):
    inputs = _write_synthetic_inputs(tmp_path, monkeypatch)
    workdir = tmp_path / "work"
    cands = [_pack_candidate(f"cand:{k}", 100 * k) for k in range(5)]
    _write_candidates(workdir / "P", cands)
    rc = CLI_JUDGE.main(
        [
            "pack", "--leaf", "P",
            "--workdir", str(workdir),
            "--inputs", str(inputs),
        ]
    )
    assert rc == 0
    # reference: the base algorithm over all candidates
    reference_packs, reference_index = rel_judge.build_packs(
        json.loads(
            json.dumps(cands)
        ),
        "P",
        "P",
    )
    packs_dir = workdir / "P" / "packs"
    expected = [("GUIDE.md", (rel_judge.JUDGING_GUIDE + "\n").encode("utf-8"))]
    for pack in reference_packs:
        expected.append(
            (
                f"pack_{pack['pack']:03d}.json",
                rel_judge.canonical_json_bytes(pack),
            )
        )
    reference_index = dict(reference_index)
    reference_index["candidates_sha256"] = _sha(
        (workdir / "P" / "candidates.jsonl").read_bytes()
    )
    expected.append(
        ("index.json", rel_judge.canonical_json_bytes(reference_index))
    )
    assert _pack_bytes(packs_dir) == sorted(expected)
    written_index = json.loads(
        (packs_dir / "index.json").read_text("utf-8")
    )
    assert "excluded_judged" not in written_index

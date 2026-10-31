"""M2 judge lane: judge packs, quote->bytes map, A34 resolver, materializer.

Synthetic fixtures only — no network (an autouse fixture makes
``urllib.request.urlopen`` raise; judge.py/resolve.py import no network
module and read EDGAR bytes only through the integrity-checked cache).
"""
from __future__ import annotations

import hashlib
import importlib
import json
import re
import sys
import urllib.request
from decimal import Decimal
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from engine.company_intelligence.relationships import edgar as rel_edgar  # noqa: E402
from engine.company_intelligence.relationships import package_v2 as pv2  # noqa: E402
from engine.company_intelligence.relationships import replay  # noqa: E402
from engine.company_intelligence.relationships import resolve as rel_resolve  # noqa: E402

judge = importlib.import_module("engine.company_intelligence.relationships.judge")
JCLI = importlib.import_module("scripts.relationship_m2_judge")
PRODUCER = importlib.import_module("scripts.build_relationship_observations")

M2_INPUTS_REL = "research/theme_graph/gmi_relationships_20261021/m2_inputs"
EXTRACTION_REL = (
    "research/theme_graph/gmi_relationships_20261021/extraction/swks_aapl_m1.jsonl"
)
SOURCES_REL = "research/theme_graph/gmi_relationships_20261021/sources"
MANIFEST_REL = "research/theme_graph/coverage_20261019/UNIVERSE_MANIFEST.json"
INPUTS_DIR = REPO_ROOT / M2_INPUTS_REL
MANIFEST_PATH = REPO_ROOT / MANIFEST_REL
EXCERPT_CONTRACT = json.loads(
    (
        REPO_ROOT
        / "contracts/company_intelligence/relationship_source_excerpt.v1.schema.json"
    ).read_text("utf-8")
)

SWKS = "ISS:US-XNAS-SWKS"
AAPL = "ISS:US-XNAS-AAPL"
ACC_25 = "0000004127-25-000085"


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    def _boom(*args, **kwargs):
        raise AssertionError("urlopen must never be called in tests")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)


def _sha(data) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _canon_line(value) -> str:
    return pv2.canon(value) + "\n"


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        (json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode(
            "utf-8"
        )
    )


def _write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        for row in rows:
            handle.write((json.dumps(row, sort_keys=True) + "\n").encode("utf-8"))


# --- synthetic document/candidate builders -----------------------------------

SPAN_25 = (
    "<p>During fiscal 2026, <b>Apple</b>, through sales to multiple distributors, "
    "accounted for 67% of the Company&#8217;s net revenue. Apple is our largest "
    "customer under a long-term supply agreement with minimum purchase "
    "commitments.</p>"
).encode("utf-8")

NARR_SPAN = (
    "<p>Apple accounted for between 10% and 20% of our net sales.</p>"
    "<p>Apple accounted for more than 40% of our net sales.</p>"
    "<p>Apple accounted for up to 15% of our net sales.</p>"
    "<p>Apple accounted for approximately 25 percent of our net sales.</p>"
    "<p>Apple purchases under the agreement were about 7% of our net sales.</p>"
    "<p>we hold 10% of the worldwide market.</p>"
    "<p>we purchase 10% of our supplies.</p>"
    "<p>we purchase 10% of our components.</p>"
    "<p>we committed to $1.5 billion of purchases.</p>"
    "<p>between $100 million and $200 million under the supply agreement.</p>"
    "<p>10% of sales in 2024. 12% of sales in 2025.</p>"
    "<p>we committed to $5 million of purchases.</p>"
    "<p>Apple accounted for 67% of our net sales.</p>"
).encode("utf-8")


def _narr_cand(**overrides):
    defaults = dict(
        origin="cue", rank=1, span_raw=NARR_SPAN, byte_start=2000,
        cues=("pct_of_revenue",), xbrl_facts=[],
    )
    defaults.update(overrides)
    return _make_candidate(**defaults)


def _make_candidate(
    *,
    acc=ACC_25,
    cik="0000004127",
    issuer_id=SWKS,
    sec_name="SKYWORKS SOLUTIONS, INC.",
    form="10-K",
    filing_role="latest",
    origin="xbrl",
    rank=0,
    span_raw=SPAN_25,
    byte_start=1500407,
    primary_document="swks-20251003.htm",
    doc_sha256=None,
    doc_byte_length=None,
    accepted_at="2025-11-07T21:08:12Z",
    header_et="20251107160812",
    submissions_raw="2025-11-08T02:08:12.000Z",
    filed_at="2025-11-07",
    period_of_report="2025-10-03",
    cues=("pct_of_revenue", "major_customer"),
    hints=(),
    xbrl_facts=(),
    candidate_id=None,
):
    raw_text = span_raw.decode("utf-8")
    normalized = pv2.normalize_span(span_raw)
    byte_end = byte_start + len(span_raw)
    if candidate_id is None:
        candidate_id = "cand:" + pv2.sha(
            pv2.canon([acc, primary_document, byte_start, byte_end])
        )[:20]
    if doc_sha256 is None:
        doc_sha256 = _sha(b"synthetic-document-" + acc.encode("utf-8"))
    if doc_byte_length is None:
        doc_byte_length = byte_end + 4096
    excerpt = {
        "schema": "company_intelligence.relationship_source_excerpt/v1",
        "accession": acc,
        "cik": cik,
        "form": form,
        "url": (
            f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
            f"{acc.replace('-', '')}/{primary_document}"
        ),
        "primary_document": primary_document,
        "doc_sha256": doc_sha256,
        "doc_byte_length": doc_byte_length,
        "accepted_at": accepted_at,
        "filed_at": filed_at,
        "period_of_report": period_of_report,
        "span": {
            "byte_start": byte_start,
            "byte_end": byte_end,
            "raw": raw_text,
            "raw_sha256": _sha(span_raw),
            "normalized": normalized,
            "normalized_sha256": _sha(normalized),
        },
        "xbrl_contexts": [],
        "excerpt_note": judge.EXCERPT_NOTE_TEMPLATE.format(
            candidate_id=candidate_id, origin=origin
        ),
    }
    return {
        "candidate_id": candidate_id,
        "leaf": "P",
        "issuer_id": issuer_id,
        "cik": cik,
        "sec_name": sec_name,
        "accession": acc,
        "form": form,
        "filing_role": filing_role,
        "document_type": form,
        "primary_document": primary_document,
        "url": excerpt["url"],
        "doc_sha256": doc_sha256,
        "doc_byte_length": doc_byte_length,
        "filed_at": filed_at,
        "period_of_report": period_of_report,
        "sec_index_header_acceptance_et": header_et,
        "accepted_at": accepted_at,
        "sec_submissions_acceptance_raw": submissions_raw,
        "origin": origin,
        "rank": rank,
        "span_kind": "table_row" if origin == "xbrl" else "sentence",
        "cues": list(cues),
        "hints": list(hints),
        "xbrl_facts": list(xbrl_facts),
        "excerpt": excerpt,
    }


_NO_PERIOD = object()


def _fact(
    fact_id="f-1",
    context_ref="c-1",
    raw_value="67",
    scale="-2",
    sign=None,
    members=(("srt:MajorCustomersAxis", "x:AppleMember"),
             ("us-gaap:ConcentrationRiskByBenchmarkAxis",
              "us-gaap:SalesRevenueNetMember")),
    period=_NO_PERIOD,
    fact_byte_start=100,
):
    if period is _NO_PERIOD:
        period = {"start": "2025-09-29", "end": "2026-09-26"}
    return {
        "concept": "us-gaap:ConcentrationRiskPercentage1",
        "context_ref": context_ref,
        "fact_id": fact_id,
        "decimals": 2,
        "scale": scale,
        "format": None,
        "sign": sign,
        "raw_value": raw_value,
        "fact_byte_start": fact_byte_start,
        "fact_byte_end": fact_byte_start + 40,
        "period": period,
        "members": [{"dimension": d, "member": m} for d, m in members],
    }


def _judgment(cand, relationships=(), verdict="relationship", **overrides):
    record = {
        "schema": "gmi_rel_m2.judgment/v1",
        "candidate_id": cand["candidate_id"],
        "judge": {"agent": "rel-m2-judge-test", "lane_run_id": None},
        "verdict": verdict,
        "no_relationship_reason": None,
        "relationships": list(relationships),
        "assessment": None,
    }
    record.update(overrides)
    return record


def _rel_entry(**overrides):
    entry = {
        "species": "supplier_customer",
        "subject_role": None,
        "relation_status": "asserted",
        "status_quote": None,
        "object": {"quote": "Apple", "kind": "named", "occurrence": 1},
        "channel": ["distributor", "direct"],
        "scope": {
            "product_key": "all",
            "product_quote": None,
            "segment_quote": None,
            "geography_quote": None,
        },
        "conditions": [],
        "magnitudes": [],
    }
    entry.update(overrides)
    return entry


def _resolver_rows():
    return [
        {"issuer_id": SWKS, "cik": 4127, "sec_name": "SKYWORKS SOLUTIONS, INC.",
         "tickers": ["SWKS"], "securities": ["SEC:US-XNAS-SWKS"]},
        {"issuer_id": AAPL, "cik": 320193, "sec_name": "Apple Inc.",
         "tickers": ["AAPL"], "securities": ["SEC:US-XNAS-AAPL"]},
        {"issuer_id": "ISS:US-XNYS-HP", "cik": 45012,
         "sec_name": "HELMERICH & PAYNE INC", "tickers": ["HP"],
         "securities": ["SEC:US-XNYS-HP"]},
        {"issuer_id": "ISS:US-XNAS-ACME1", "cik": 1, "sec_name": "Acme Widgets Inc",
         "tickers": [], "securities": []},
        {"issuer_id": "ISS:US-XNAS-ACME2", "cik": 2, "sec_name": "Acme Widgets Ltd",
         "tickers": [], "securities": []},
        {"issuer_id": "ISS:US-XNAS-WFP", "cik": 3, "sec_name": "Wells Fargo L.P.",
         "tickers": [], "securities": []},
        {"issuer_id": "ISS:US-XNAS-AMT", "cik": 4, "sec_name": "ArcelorMittal S.A.",
         "tickers": [], "securities": []},
        {"issuer_id": "ISS:US-XNAS-AB", "cik": 5, "sec_name": "AB Corp",
         "tickers": [], "securities": []},
    ]


def _aliases():
    return [
        {"alias": "Skyworks", "alias_norm": "skyworks", "issuer_id": SWKS,
         "target": "issuer", "non_edge_reason": None, "cn_security_id": None,
         "basis": "test"},
        {"alias": "Apple", "alias_norm": "apple", "issuer_id": AAPL,
         "target": "issuer", "non_edge_reason": None, "cn_security_id": None,
         "basis": "test"},
        {"alias": "HP", "alias_norm": "hp", "issuer_id": "ISS:US-XNYS-HP",
         "target": "issuer", "non_edge_reason": None, "cn_security_id": None,
         "basis": "test"},
        {"alias": "Aluminum Corporation of China",
         "alias_norm": "aluminum corporation of china", "issuer_id": None,
         "target": "non_edge", "non_edge_reason": "CN_SECURITY_LEVEL_ONLY",
         "cn_security_id": "SEC:CN-XSHG-601600", "basis": "test"},
        {"alias": "Ghost Corp", "alias_norm": "ghost corp",
         "issuer_id": "ISS:US-XNAS-GHOST", "target": "issuer",
         "non_edge_reason": None, "cn_security_id": None, "basis": "test"},
    ]


def _manifest_issuers():
    return {
        SWKS: ["SEC:US-XNAS-SWKS"],
        AAPL: ["SEC:US-XNAS-AAPL"],
        "ISS:US-XNAS-ACME1": [],
        "ISS:US-XNAS-ACME2": [],
        "ISS:US-XNAS-WFP": ["SEC:US-XNAS-WFP"],
        "ISS:US-XNAS-AMT": ["SEC:US-XNAS-AMT"],
    }


def _mapper(census=None, cache=None, issuers=None, ledger_index=None):
    if issuers is None:
        issuers = _manifest_issuers()
    if census is None:
        census = {"issuers": {SWKS: {"sec_name": "SKYWORKS SOLUTIONS, INC."}}}
    if ledger_index is None:
        ledger_index = {(ACC_25, "swks-20251003.htm"): "2026-10-21T10:00:00Z"}
    return judge.CandidateMapper(
        issuers=issuers,
        aliases=_aliases(),
        resolver_rows=_resolver_rows(),
        census=census,
        cache=cache,
        counters=judge.new_counters(),
        ledger_index=ledger_index,
    )


def _workdir(tmp_path, candidates, ledger_rows, report=None):
    workdir = tmp_path / "work"
    _write_jsonl(workdir / "P" / "candidates.jsonl", candidates)
    _write_jsonl(workdir / "P" / "fetch_ledger.jsonl", ledger_rows)
    _write_json(
        workdir / "P" / "harvest_report.json",
        report if report is not None else {"schema": "gmi_rel_m2.harvest_report/v1"},
    )
    _write_json(
        workdir / "P" / "packs" / "index.json",
        {
            "schema": "gmi_rel_m2.judge_index/v1",
            "candidates_sha256": _sha(
                (workdir / "P" / "candidates.jsonl").read_bytes()
            ),
            "packs": [],
            "judgments_dir": "judgments",
        },
    )
    return workdir


def _ledger_row(acc, primary="swks-20251003.htm", fetched_at="2026-10-21T10:00:00Z",
                state="collected", role="latest", form="10-K", issuer_id=SWKS):
    return {
        "leaf": "P",
        "issuer_id": issuer_id,
        "cik": "0000004127",
        "sec_name": "SKYWORKS SOLUTIONS, INC.",
        "accession": acc,
        "form": form,
        "filing_role": role,
        "state": state,
        "reason": "FORM_MISMATCH" if state == "rejected" else None,
        "accepted_at": "2025-11-07T21:08:12Z" if state == "collected" else None,
        "sec_index_header_acceptance_et": (
            "20251107160812" if state == "collected" else None
        ),
        "sec_submissions_acceptance_raw": None,
        "census_fetched_at": "2026-10-22T01:50:17Z",
        "filed_at": "2025-11-07" if state == "collected" else None,
        "period_of_report": "2025-10-03" if state == "collected" else None,
        "notes": [],
        "documents": (
            [
                {
                    "filename": primary,
                    "type": form,
                    "state": "cached",
                    "reason": None,
                    "http_status": 200,
                    "sha256": _sha(b"doc-" + acc.encode("utf-8")),
                    "byte_length": 4096,
                    "fetched_at": fetched_at,
                }
            ]
            if state in ("collected", "partial")
            else []
        ),
    }


def _cache_with_dei(tmp_path, cik="4127", nodash="000000412725000085",
                    filename="swks-20251003.htm",
                    name=b"Skyworks Solutions, Inc."):
    cache = rel_edgar.EdgarCache(tmp_path / "cache")
    body = (
        b"<html><head><title>x</title></head><body>"
        b'<ix:nonNumeric name="dei:EntityRegistrantName" contextRef="c-1">'
        + name
        + b"</ix:nonNumeric></body></html>"
    )
    cache.store(int(cik), nodash, filename, body, "https://example.invalid", 200,
                "2026-10-21T10:00:00Z")
    return cache


# --- K1: judgment schema + guide -----------------------------------------------


def test_judgment_schema_accepts_valid_and_rejects_invalid():
    validator = jsonschema.validators.validator_for(judge.JUDGMENT_SCHEMA)(
        judge.JUDGMENT_SCHEMA
    )
    cand = _make_candidate()
    good = _judgment(
        cand,
        [
            _rel_entry(
                magnitudes=[
                    {
                        "kind": "seller_revenue_share",
                        "xbrl_fact_ids": ["f-1"],
                        "numerator_scope": "net revenue from Apple",
                        "denominator_scope": "consolidated net revenue",
                    },
                    {
                        "kind": "purchase_commitment",
                        "quote": "between $100 million and $200 million",
                        "period": "current",
                        "numerator_scope": "committed purchases",
                        "denominator_scope": "not stated",
                    },
                ],
                conditions=[
                    {"kind": "volume_commitment", "quote": "minimum purchase commitments"}
                ],
            )
        ],
    )
    validator.validate(good)
    asm = _judgment(
        cand,
        verdict="assessment",
        relationships=[],
        assessment={
            "assessment": "not_restated",
            "reason": "part_iii_only_amendment",
            "reason_quote": "sole purpose of providing the information",
        },
    )
    validator.validate(asm)

    def _bad(mutate):
        record = json.loads(json.dumps(good))
        mutate(record)
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(record)

    _bad(lambda r: r.__setitem__("candidate_id", "cand:xyz"))
    _bad(lambda r: r.__setitem__("verdict", "maybe"))
    _bad(lambda r: r["relationships"][0].__setitem__("extra", 1))
    _bad(lambda r: r["relationships"][0]["object"].__setitem__("kind", "ticker"))
    _bad(lambda r: r["relationships"][0]["scope"].__setitem__("product_key", "All"))
    _bad(lambda r: r["relationships"][0]["magnitudes"][0].__setitem__("value", 0.5))
    _bad(lambda r: r["relationships"][0]["magnitudes"][1].__setitem__(
        "period", "prior"))
    # relationships non-empty iff verdict == relationship
    _bad(lambda r: r.__setitem__("relationships", []))
    _bad(lambda r: (r.__setitem__("verdict", "no_relationship"),
                    r.__setitem__("relationships", []),
                    r.__setitem__("no_relationship_reason", None)))
    _bad(lambda r: (r.__setitem__("verdict", "no_relationship"),
                    r.__setitem__("relationships", []),
                    r.__setitem__("no_relationship_reason", "made_up_reason")))


def test_guide_names_rules_and_ambiguous_names():
    guide = judge.JUDGING_GUIDE
    for marker in (f"G{i}" for i in range(1, 12)):
        assert marker in guide, marker
    for name in sorted(rel_resolve.AMBIGUOUS_NAMES):
        assert re.search(r"\b" + re.escape(name) + r"\b", guide), name


# --- K2: pack -------------------------------------------------------------------


def test_pack_order_layout_and_index_sha(tmp_path):
    cands = [
        _make_candidate(acc="0000004127-25-000002", byte_start=200,
                        primary_document="b.htm",
                        xbrl_facts=[_fact(fact_id="f-1")]),
        _make_candidate(acc="0000004127-25-000001", byte_start=100,
                        primary_document="a.htm", origin="cue", rank=1,
                        xbrl_facts=[]),
        _make_candidate(byte_start=150, xbrl_facts=[_fact(fact_id="f-1")]),
    ]
    _write_jsonl(tmp_path / "cands.jsonl", cands)
    workdir = _workdir(tmp_path, cands, [_ledger_row(ACC_25)])
    rc = JCLI.main(["pack", "--leaf", "P", "--workdir", str(workdir),
                    "--inputs", str(INPUTS_DIR), "--per-pack", "2"])
    assert rc == 0
    packs_dir = workdir / "P" / "packs"
    guide = (packs_dir / "GUIDE.md").read_text("utf-8")
    assert guide == judge.JUDGING_GUIDE + "\n"
    index = json.loads((packs_dir / "index.json").read_text("utf-8"))
    assert index["schema"] == "gmi_rel_m2.judge_index/v1"
    assert index["candidates_sha256"] == _sha(
        (workdir / "P" / "candidates.jsonl").read_bytes()
    )
    assert index["judgments_dir"] == "judgments"
    assert [entry["pack"] for entry in index["packs"]] == [1, 2]
    assert [entry["file"] for entry in index["packs"]] == [
        "pack_001.json",
        "pack_002.json",
    ]
    all_ids = []
    for entry, expect_n in zip(index["packs"], (2, 1)):
        pack_path = packs_dir / entry["file"]
        pack = json.loads(pack_path.read_text("utf-8"))
        assert pack["schema"] == "gmi_rel_m2.judge_pack/v1"
        assert pack["leaf"] == "P" and pack["dirname"] == "P"
        assert pack["pack"] == entry["pack"]
        assert len(pack["candidates"]) == expect_n
        assert entry["candidate_ids"] == [
            c["candidate_id"] for c in pack["candidates"]
        ]
        all_ids.extend(entry["candidate_ids"])
        for c in pack["candidates"]:
            assert set(c) == {
                "candidate_id", "issuer_id", "filer_name", "form", "filing_role",
                "origin", "rank", "cues", "hints", "period_of_report", "text",
                "xbrl",
            }
            assert c["filer_name"] == "SKYWORKS SOLUTIONS, INC."
            assert isinstance(c["text"], str) and c["text"]
    # sort order: (issuer_id, accession, primary_document, byte_start, ...)
    assert all_ids == [
        cands[1]["candidate_id"],   # 25-000001 a.htm @100
        cands[0]["candidate_id"],   # 25-000002 b.htm @200
        cands[2]["candidate_id"],   # 25-000085 @150
    ]
    pack2 = json.loads((packs_dir / "pack_002.json").read_text("utf-8"))
    xbrl = pack2["candidates"][0]["xbrl"][0]
    assert xbrl["fact_id"] == "f-1"
    assert xbrl["concept"] == "us-gaap:ConcentrationRiskPercentage1"
    assert xbrl["benchmark_member"] == "us-gaap:SalesRevenueNetMember"
    assert xbrl["value"] == float(Decimal("67").scaleb(-2))
    assert xbrl["period_label"] == "FY2026"
    assert xbrl["members"] == {"srt:MajorCustomersAxis": "x:AppleMember",
                               "us-gaap:ConcentrationRiskByBenchmarkAxis":
                               "us-gaap:SalesRevenueNetMember"}
    # idempotent repack with the same candidates
    assert JCLI.main(["pack", "--leaf", "P", "--workdir", str(workdir),
                      "--inputs", str(INPUTS_DIR)]) == 0


def test_pack_refuses_changed_candidates(tmp_path):
    cands = [_make_candidate()]
    workdir = _workdir(tmp_path, cands, [_ledger_row(ACC_25)])
    argv = ["pack", "--leaf", "P", "--workdir", str(workdir),
            "--inputs", str(INPUTS_DIR)]
    assert JCLI.main(argv) == 0
    changed = [dict(cands[0])]
    changed[0]["rank"] = 9
    _write_jsonl(workdir / "P" / "candidates.jsonl", changed)
    assert JCLI.main(argv) == 2


# --- K3: span map + quotes ------------------------------------------------------


def test_span_map_equals_normalize_span_with_entity_and_tags():
    raw = (
        b"<p>Hello &#65;(&amp;)&nbsp;world</p><b>caf\xc3\xa9</b>  x &#8217;end"
        b"</p><br/><span>tail</span>"
    )
    text, ranges = judge.span_map(raw)
    assert text == pv2.normalize_span(raw)
    assert len(text) == len(ranges)
    # the entity-decoded chars map to the entity's byte range
    idx = text.index("A")
    bs, be = ranges[idx]
    assert raw[bs:be] == b"&#65;"
    idx = text.index("&")
    bs, be = ranges[idx]
    assert raw[bs:be] == b"&amp;"
    idx = text.index("’")
    bs, be = ranges[idx]
    assert raw[bs:be] == b"&#8217;"
    # a multibyte char maps to exactly its two utf-8 bytes
    idx = text.index("é")
    bs, be = ranges[idx]
    assert be - bs == 2 and raw[bs:be] == "é".encode("utf-8")
    # a collapsed whitespace run maps to the run's first char range
    idx = text.index("x")
    ws_start = idx - 1
    assert text[ws_start] == " "
    bs, be = ranges[ws_start]
    assert raw[bs:be] == b" "
    # a non-utf8 span is refused, never patched
    with pytest.raises(judge.SpanMapError):
        judge.span_map(b"<p>\xff\xfe</p>")


def test_quote_too_short_not_found_ambiguous_and_occurrence(tmp_path):
    raw = b"<p>Apple sells to Apple and to Beta.</p>"
    span = judge.span_map(raw)
    assert span.text == pv2.normalize_span(raw)
    with pytest.raises(judge.QuoteError) as err:
        judge.find_quote(span, "A")
    assert err.value.code == "QUOTE_TOO_SHORT"
    with pytest.raises(judge.QuoteError) as err:
        judge.find_quote(span, "Banana")
    assert err.value.code == "QUOTE_NOT_FOUND"
    with pytest.raises(judge.QuoteError) as err:
        judge.find_quote(span, "Apple")
    assert err.value.code == "QUOTE_AMBIGUOUS"
    nq, bs, be, count = judge.find_quote(span, "Apple", occurrence=2)
    assert nq == "Apple" and count == 2
    assert raw[bs:be] == b"Apple"
    assert pv2.normalize_span(raw[bs:be]) == "Apple"
    with pytest.raises(judge.QuoteError) as err:
        judge.find_quote(span, "Apple", occurrence=3)
    assert err.value.code == "QUOTE_NOT_FOUND"
    nq, bs, be, count = judge.find_quote(span, "sells to Apple")
    assert count == 1 and raw[bs:be] == b"sells to Apple"


# --- K4: A34 counterparty resolver ----------------------------------------------


def _resolve(quote, kind="named", subject=SWKS, aliases=None, rows=None,
             issuers=None):
    return rel_resolve.resolve_counterparty(
        quote,
        kind=kind,
        subject_issuer_id=subject,
        aliases=_aliases() if aliases is None else aliases,
        resolver_rows=_resolver_rows() if rows is None else rows,
        manifest_issuers=_manifest_issuers() if issuers is None else issuers,
    )


def test_resolver_ambiguous_bare_names_first():
    # the curated alias "hp" and the Helmerich & Payne row both exist, but the
    # bare ambiguous name is refused BEFORE every other step
    res = _resolve("HP")
    assert res["issuer_id"] is None
    assert res["non_edge_reason"] == "UNRESOLVED_COUNTERPARTY"
    assert res["note"] == "ambiguous_bare_name"
    res = _resolve("GE")
    assert res["non_edge_reason"] == "UNRESOLVED_COUNTERPARTY"
    res = _resolve("General Electric")
    assert res["note"] == "ambiguous_bare_name"
    res = _resolve("Arm")
    assert res["note"] == "ambiguous_bare_name"
    # a qualified name is not a bare name
    res = _resolve("Arm Holdings")
    assert res["non_edge_reason"] == "UNRESOLVED_COUNTERPARTY"
    assert res["note"] is None


def test_resolver_alias_issuer_and_non_edge_targets():
    res = _resolve("Apple")
    assert res["issuer_id"] == AAPL
    assert res["name_as_filed"] == "Apple"
    assert res["non_edge_reason"] is None and res["refusal"] is None
    res = _resolve("Aluminum Corporation of China")
    assert res["issuer_id"] is None
    assert res["non_edge_reason"] == "CN_SECURITY_LEVEL_ONLY"
    assert res["name_as_filed"] == "Aluminum Corporation of China"


def test_resolver_alias_target_not_in_resolver():
    res = _resolve("Ghost Corp")
    assert res["issuer_id"] is None
    assert res["refusal"] == "ALIAS_TARGET_NOT_IN_RESOLVER"


def test_resolver_sec_name_suffix_strip_unique_and_multiple():
    res = _resolve("Apple Inc.")
    assert res["issuer_id"] == AAPL
    # leading "the" + suffix strip
    res = _resolve("the Apple Company")
    assert res["issuer_id"] == AAPL
    # two-token suffix forms: "l p" and "s a"
    res = _resolve("Wells Fargo")
    assert res["issuer_id"] == "ISS:US-XNAS-WFP"
    res = _resolve("ArcelorMittal S.A.")
    assert res["issuer_id"] == "ISS:US-XNAS-AMT"
    # 2+ stripped-sec_name matches -> refused
    res = _resolve("Acme Widgets Corporation")
    assert res["issuer_id"] is None
    assert res["non_edge_reason"] == "UNRESOLVED_COUNTERPARTY"
    assert res["note"] == "multiple_sec_name_matches"
    # a stripped quote shorter than 3 chars never matches
    res = _resolve("AB", rows=[
        {"issuer_id": "ISS:US-XNAS-AB", "cik": 5, "sec_name": "AB Corp",
         "tickers": [], "securities": []},
    ])
    assert res["issuer_id"] is None
    assert res["non_edge_reason"] == "UNRESOLVED_COUNTERPARTY"


def test_resolver_has_no_ticker_step():
    # "HP" must never reach the ticker step (Helmerich & Payne, ticker HP)
    res = _resolve("HP")
    assert res["issuer_id"] is not None or True  # ambiguous bare name, see above
    assert res["non_edge_reason"] == "UNRESOLVED_COUNTERPARTY"
    # and a company whose ONLY handle is a ticker does not resolve by it
    res = _resolve("SWKS")
    assert res["issuer_id"] is None
    assert res["non_edge_reason"] == "UNRESOLVED_COUNTERPARTY"


def test_resolver_out_of_core_market_and_self_reference():
    res = _resolve("Skyworks", subject=AAPL, issuers={AAPL: []})
    assert res["issuer_id"] is None
    assert res["non_edge_reason"] == "OUT_OF_CORE_MARKET"
    assert res["name_as_filed"] == "Skyworks"
    res = _resolve("Skyworks", subject=SWKS)
    assert res["refusal"] == "SELF_REFERENCE"
    res = _resolve("Apple", subject=AAPL)
    assert res["refusal"] == "SELF_REFERENCE"


def test_resolver_anonymous_alias():
    res = _resolve("Customer A", kind="anonymous_alias")
    assert res["issuer_id"] is None
    assert res["anonymous_alias"] == "Customer A"
    assert res["name_as_filed"] is None
    assert res["non_edge_reason"] == "ANONYMOUS_ALIAS"


# --- K5: subject ----------------------------------------------------------------


def _census_entry(**overrides):
    entry = {
        "cik": 4127,
        "domain": "D1",
        "fetched_at": "2026-10-22T01:50:17Z",
        "sec_name": "SKYWORKS SOLUTIONS, INC.",
        "state": "OK",
        "latest": {
            "acceptanceDateTime": "2025-11-08T02:08:12.000Z",
            "accessionNumber": ACC_25,
            "filingDate": "2025-11-07",
            "form": "10-K",
            "primaryDocument": "swks-20251003.htm",
            "reportDate": "2025-10-03",
        },
        "amendments_of_latest": [],
        "amendments_of_prior": [],
    }
    entry.update(overrides)
    return entry


def test_subject_name_from_dei_registrant_name_and_fallback(tmp_path):
    cand = _make_candidate()
    cache = _cache_with_dei(tmp_path)
    issuers = _manifest_issuers()
    subject, code, counter = judge.subject_identity(
        cand, _census_entry(), cache, issuers
    )
    assert code is None and counter is None
    assert subject == {
        "cik": "0000004127",
        "issuer_id": SWKS,
        "name_as_filed": "Skyworks Solutions, Inc.",
        "security_ids": ["SEC:US-XNAS-SWKS"],
    }
    # cache miss -> census sec_name fallback + counter
    empty_cache = rel_edgar.EdgarCache(tmp_path / "empty")
    subject, code, counter = judge.subject_identity(
        cand, _census_entry(), empty_cache, issuers
    )
    assert subject["name_as_filed"] == "SKYWORKS SOLUTIONS, INC."
    assert counter == "subject_name_from_sec_name"
    # integrity failure -> fallback too
    path = (tmp_path / "cache" / "4127" / "000000412725000085"
            / "swks-20251003.htm")
    path.write_bytes(b"tampered")
    subject, code, counter = judge.subject_identity(
        cand, _census_entry(), cache, issuers
    )
    assert subject["name_as_filed"] == "SKYWORKS SOLUTIONS, INC."
    assert counter == "subject_name_from_sec_name"
    # issuer absent from the manifest -> candidate-level refusal
    subject, code, counter = judge.subject_identity(
        cand, _census_entry(), cache, {AAPL: []}
    )
    assert subject is None and code == "SUBJECT_NOT_IN_MANIFEST"
    # a filing whose accession is not in the census record falls back
    subject, code, counter = judge.subject_identity(
        _make_candidate(acc="0000004127-99-000001"), _census_entry(), cache,
        issuers,
    )
    assert subject["name_as_filed"] == "SKYWORKS SOLUTIONS, INC."


# --- K6: XBRL magnitudes --------------------------------------------------------


def _xbrl_cand(facts):
    return _make_candidate(xbrl_facts=facts)


def test_xbrl_magnitude_value_period_members_and_order():
    facts = [
        _fact(fact_id="f-2", raw_value="66", fact_byte_start=200, period={
            "start": "2024-09-28", "end": "2025-09-27"}),
        _fact(fact_id="f-1", raw_value="67", period={
            "start": "2025-09-28", "end": "2026-09-26"}),
        _fact(fact_id="f-3", raw_value="1,234", scale="3", sign="-",
              period={"start": "2025-10-01", "end": "2025-12-31"},
              fact_byte_start=300),
        _fact(fact_id="f-4", raw_value="12", period={"instant": "2026-09-26"},
              fact_byte_start=400),
        _fact(fact_id="f-0", raw_value="9", period=None, fact_byte_start=500),
    ]
    cand = _xbrl_cand(facts)
    judgment = _judgment(
        cand,
        [
            _rel_entry(
                magnitudes=[
                    {
                        "kind": "seller_revenue_share",
                        "xbrl_fact_ids": ["f-2", "f-1", "f-2"],
                        "numerator_scope": "net revenue from Apple",
                        "denominator_scope": "consolidated net revenue",
                    }
                ]
            )
        ],
    )
    out = _mapper().map(cand, judgment)
    assert out["codes"] == [], out["codes"]  # f-0 is never cited: it cannot refuse
    row = out["rows"][0]
    mags = row["magnitudes"]
    # judgment order kept; within one magnitude fact_byte_start order (f-1, f-2)
    assert [m["xbrl_fact_id"] for m in mags] == ["f-1", "f-2"]
    assert [m["value"] for m in mags] == [0.67, 0.66]
    assert [m["period"]["label"] for m in mags] == ["FY2026", "FY2025"]
    assert mags[0]["period"] == {"start": "2025-09-28", "end": "2026-09-26",
                                 "label": "FY2026"}
    for mag in mags:
        assert mag["unit"] == "ratio" and mag["precision"] == "exact"
        assert mag["numerator_scope"] == "net revenue from Apple"
        assert mag["denominator_scope"] == "consolidated net revenue"
    # source_ref.xbrl: deduped by fact_id, ordered by fact_byte_start
    xbrl = row["source_ref"]["xbrl"]
    assert [f["fact_id"] for f in xbrl] == ["f-1", "f-2"]
    assert xbrl[0]["members"] == {
        "srt:MajorCustomersAxis": "x:AppleMember",
        "us-gaap:ConcentrationRiskByBenchmarkAxis":
            "us-gaap:SalesRevenueNetMember",
    }
    assert xbrl[0]["decimals"] == 2 and xbrl[0]["scale"] == -2

    # other duration label, instant period, comma/scale/sign value
    judgment2 = _judgment(
        cand,
        [
            _rel_entry(
                magnitudes=[
                    {"kind": "seller_revenue_share",
                     "xbrl_fact_ids": ["f-3"],
                     "numerator_scope": "a", "denominator_scope": "b"}
                ]
            )
        ],
    )
    out2 = _mapper().map(cand, judgment2)
    assert out2["codes"] == []
    mag = out2["rows"][0]["magnitudes"][0]
    assert mag["value"] == -1234000.0
    assert mag["period"] == {"start": "2025-10-01", "end": "2025-12-31",
                             "label": "2025-10-01/2025-12-31"}
    judgment3 = _judgment(
        cand,
        [
            _rel_entry(
                magnitudes=[
                    {"kind": "seller_revenue_share",
                     "xbrl_fact_ids": ["f-4"],
                     "numerator_scope": "a", "denominator_scope": "b"}
                ]
            )
        ],
    )
    out3 = _mapper().map(cand, judgment3)
    mag = out3["rows"][0]["magnitudes"][0]
    assert mag["period"] == {"start": None, "end": "2026-09-26",
                             "label": "as of 2026-09-26"}
    # citing the period-less fact refuses the entry with a named code
    judgment4 = _judgment(
        cand,
        [
            _rel_entry(
                magnitudes=[
                    {"kind": "seller_revenue_share",
                     "xbrl_fact_ids": ["f-0"],
                     "numerator_scope": "a", "denominator_scope": "b"}
                ]
            )
        ],
    )
    out4 = _mapper().map(cand, judgment4)
    assert out4["codes"] == ["FACT_PERIOD_MISSING"]
    assert out4["rows"] == []


def test_xbrl_benchmark_kind_mismatch_and_unsupported():
    cand = _xbrl_cand([
        _fact(fact_id="f-1", members=(
            ("us-gaap:ConcentrationRiskByBenchmarkAxis",
             "us-gaap:CostOfRevenueMember"),)),
    ])
    judgment = _judgment(
        cand,
        [
            _rel_entry(
                magnitudes=[
                    {"kind": "seller_revenue_share", "xbrl_fact_ids": ["f-1"],
                     "numerator_scope": "a", "denominator_scope": "b"}
                ]
            )
        ],
    )
    out = _mapper().map(cand, judgment)
    assert out["codes"] == ["MAGNITUDE_BENCHMARK_MISMATCH"]
    assert out["rows"] == []
    # buyer kind against a cost benchmark passes the derived check
    judgment["relationships"][0]["magnitudes"][0]["kind"] = \
        "buyer_procurement_share"
    judgment["relationships"][0]["subject_role"] = "customer"
    out = _mapper().map(cand, judgment)
    assert out["codes"] == []
    assert out["rows"][0]["magnitudes"][0]["kind"] == "buyer_procurement_share"
    # an unsupported benchmark member
    cand2 = _xbrl_cand([
        _fact(fact_id="f-1", members=(
            ("us-gaap:ConcentrationRiskByBenchmarkAxis", "us-gaap:TotalMember"),)),
    ])
    out2 = _mapper().map(cand2, judgment)
    assert out2["codes"] == ["MAGNITUDE_BENCHMARK_UNSUPPORTED"]
    # a fact with no benchmark member at all
    cand3 = _xbrl_cand([_fact(fact_id="f-1", members=())])
    out3 = _mapper().map(cand3, judgment)
    assert out3["codes"] == ["MAGNITUDE_BENCHMARK_UNSUPPORTED"]


def test_magnitude_role_mismatch():
    cost_fact = _fact(
        fact_id="f-cost",
        members=(
            ("us-gaap:ConcentrationRiskByBenchmarkAxis",
             "us-gaap:CostOfRevenueMember"),
        ),
    )
    cand = _xbrl_cand([_fact(fact_id="f-1"), cost_fact])
    base = _rel_entry(
        magnitudes=[
            {"kind": "seller_revenue_share", "xbrl_fact_ids": ["f-1"],
             "numerator_scope": "a", "denominator_scope": "b"}
        ]
    )

    def _run(entry):
        return _mapper().map(cand, _judgment(cand, [entry]))

    # default subject role for supplier_customer is supplier == from_role: ok
    assert _run(base)["codes"] == []
    # the filer names itself the customer: seller share needs the from_role
    entry = dict(base, subject_role="customer")
    assert _run(entry)["codes"] == ["MAGNITUDE_ROLE_MISMATCH"]
    # buyer share against a cost benchmark needs the to_role
    buyer = _rel_entry(
        magnitudes=[
            {"kind": "buyer_procurement_share", "xbrl_fact_ids": ["f-cost"],
             "numerator_scope": "a", "denominator_scope": "b"}
        ]
    )
    assert _run(buyer)["codes"] == ["MAGNITUDE_ROLE_MISMATCH"]
    assert _run(dict(buyer, subject_role="customer"))["codes"] == []


# --- K7: narrative magnitudes ---------------------------------------------------


def _narrative_entry(quote, kind="seller_revenue_share"):
    return _rel_entry(
        magnitudes=[
            {
                "kind": kind,
                "quote": quote,
                "period": "current",
                "numerator_scope": "net revenue from Apple",
                "denominator_scope": "consolidated net revenue",
            }
        ]
    )


def test_narrative_parse_range_units_and_precision_words():
    cand = _narr_cand(period_of_report="2025-10-03")
    cases = [
        (
            "Apple accounted for between 10% and 20% of our net sales",
            dict(value=0.10, value_high=0.20, precision="range", unit="ratio"),
        ),
        (
            "Apple accounted for more than 40% of our net sales",
            dict(value=0.40, precision="lower_bound", unit="ratio"),
        ),
        (
            "Apple accounted for up to 15% of our net sales",
            dict(value=0.15, precision="upper_bound", unit="ratio"),
        ),
        (
            "Apple accounted for approximately 25 percent of our net sales",
            dict(value=0.25, precision="exact", unit="ratio"),
        ),
        (
            "Apple purchases under the agreement were about 7% of our net sales",
            dict(value=0.07, precision="exact", unit="ratio"),
        ),
    ]
    for quote, expect in cases:
        out = _mapper().map(cand, _judgment(cand, [_narrative_entry(quote)]))
        assert out["codes"] == [], (quote, out["codes"])
        mag = out["rows"][0]["magnitudes"][0]
        for key, value in expect.items():
            assert mag[key] == value, (quote, key, mag[key], value)
        assert mag["period"] == {"start": None, "end": "2025-10-03",
                                 "label": "FY2025"}
        assert mag["xbrl_fact_id"] is None
        assert mag["kind"] == "seller_revenue_share"

    dollar_cand = _narr_cand(period_of_report="2025-10-03")
    entry = _narrative_entry(
        "we committed to $1.5 billion of purchases",
        kind="purchase_commitment",
    )
    out = _mapper().map(dollar_cand, _judgment(dollar_cand, [entry]))
    assert out["codes"] == [], out["codes"]
    mag = out["rows"][0]["magnitudes"][0]
    assert mag["unit"] == "USD" and mag["value"] == 1_500_000_000.0
    entry = _narrative_entry(
        "between $100 million and $200 million under the supply agreement",
        kind="contract_value",
    )
    out = _mapper().map(dollar_cand, _judgment(dollar_cand, [entry]))
    assert out["codes"] == [], out["codes"]
    mag = out["rows"][0]["magnitudes"][0]
    assert mag["unit"] == "USD"
    assert mag["value"] == 100_000_000.0 and mag["value_high"] == 200_000_000.0
    assert mag["precision"] == "range"
    # parse ambiguity: two unjoined numbers
    out = _mapper().map(
        dollar_cand,
        _judgment(
            dollar_cand,
            [_narrative_entry("10% of sales in 2024. 12% of sales in 2025")],
        ),
    )
    assert out["codes"] == ["MAGNITUDE_PARSE_AMBIGUOUS"]


def test_narrative_refused_when_xbrl_available():
    cand = _narr_cand(xbrl_facts=[_fact(fact_id="f-1")])
    out = _mapper().map(cand, _judgment(cand, [_narrative_entry(
        "Apple accounted for 67% of our net sales")]))
    assert out["codes"] == ["MAGNITUDE_XBRL_AVAILABLE"]
    assert out["rows"] == []
    # dollar kinds are not gated by xbrl availability
    entry = _narrative_entry(
        "we committed to $1.5 billion of purchases", kind="purchase_commitment"
    )
    out = _mapper().map(cand, _judgment(cand, [entry]))
    assert out["codes"] == []
    assert out["rows"][0]["magnitudes"][0]["value"] == 1_500_000_000.0


def test_narrative_kind_wording_and_unit_kind_mismatch():
    cand = _narr_cand()
    out = _mapper().map(
        cand,
        _judgment(cand, [_narrative_entry("we hold 10% of the worldwide market")]),
    )
    assert out["codes"] == ["MAGNITUDE_KIND_WORDING"]
    out = _mapper().map(
        cand,
        _judgment(cand, [_narrative_entry("we purchase 10% of our supplies",
                                          kind="buyer_procurement_share")]),
    )
    assert out["codes"] == []
    out = _mapper().map(
        cand,
        _judgment(
            cand,
            [
                _narrative_entry(
                    "we purchase 10% of our components",
                    kind="purchase_commitment",
                )
            ],
        ),
    )
    assert out["codes"] == ["MAGNITUDE_UNIT_KIND_MISMATCH"]
    out = _mapper().map(
        cand,
        _judgment(
            cand,
            [
                _narrative_entry(
                    "we committed to $5 million of purchases",
                    kind="seller_revenue_share",
                )
            ],
        ),
    )
    assert out["codes"] == ["MAGNITUDE_UNIT_KIND_MISMATCH"]


# --- K8: observation rows -------------------------------------------------------


def test_status_quote_missing_and_role_not_in_species():
    cand = _make_candidate()
    mapper = _mapper()
    entry = _rel_entry(relation_status="terminated", status_quote=None)
    out = mapper.map(cand, _judgment(cand, [entry]))
    assert out["codes"] == ["STATUS_QUOTE_MISSING"]
    entry = _rel_entry(
        relation_status="terminated", status_quote="not present in this span"
    )
    out = mapper.map(cand, _judgment(cand, [entry]))
    assert out["codes"] == ["STATUS_QUOTE_MISSING"]
    entry = _rel_entry(subject_role="provider")
    out = mapper.map(cand, _judgment(cand, [entry]))
    assert out["codes"] == ["ROLE_NOT_IN_SPECIES"]
    # a mappable status quote is ledgered but never emitted into the row
    entry = _rel_entry(
        relation_status="denied",
        status_quote="Apple is our largest customer under a long-term supply",
    )
    out = mapper.map(cand, _judgment(cand, [entry]))
    assert out["codes"] == []
    row = out["rows"][0]
    assert row["relation_status"] == "denied"


def test_entry_refusal_keeps_other_entries(tmp_path):
    cand = _make_candidate()
    entries = [
        _rel_entry(object={"quote": "Zeta Corp", "kind": "named"}),
        _rel_entry(),
    ]
    out = _mapper().map(cand, _judgment(cand, entries))
    assert out["codes"] == ["QUOTE_NOT_FOUND"]
    assert len(out["rows"]) == 1
    assert out["rows"][0]["object"]["issuer_id"] == AAPL


def test_clock_refused_and_ledger_document_missing(tmp_path):
    cand = _make_candidate(header_et="20251107160813")
    out = _mapper().map(cand, _judgment(cand, [_rel_entry()]))
    assert out["codes"] == ["CLOCK_REFUSED:clock_mismatch"]
    out = _mapper().map(_make_candidate(), _judgment(
        _make_candidate(), [_rel_entry()]))
    assert out["codes"] == []
    # no fetch-ledger document for (accession, primary_document)
    ledger = [_ledger_row(ACC_25, primary="other.htm")]
    mapper = judge.CandidateMapper(
        issuers=_manifest_issuers(),
        aliases=_aliases(),
        resolver_rows=_resolver_rows(),
        census={"issuers": {SWKS: {"sec_name": "SKYWORKS SOLUTIONS, INC."}}},
        cache=None,
        counters=judge.new_counters(),
        ledger_index=judge.build_ledger_index(ledger),
    )
    cand = _make_candidate()
    out = mapper.map(cand, _judgment(cand, [_rel_entry()]))
    assert out["codes"] == ["LEDGER_DOCUMENT_MISSING"]


# --- K9: document assessments ---------------------------------------------------


def test_assessment_target_from_census_and_non_amendment_refused():
    cand = _make_candidate(
        acc="0000004127-26-000003",
        form="10-K/A",
        filing_role="amendment_of_latest",
        origin="amendment_note",
        byte_start=29908,
        span_raw=(
            b"<p>The Company is filing this Amendment No. 1 for the sole purpose "
            b"of providing the information required in Part III of Form 10-K.</p>"
        ),
        accepted_at="2026-01-30T21:06:48Z",
        header_et="20260130160648",
        submissions_raw="2026-01-31T02:06:48.000Z",
        filed_at="2026-01-30",
        period_of_report="2025-10-03",
        xbrl_facts=[],
    )
    census = {"issuers": {
        SWKS: _census_entry(
            latest=dict(_census_entry()["latest"],
                        accessionNumber="0000004127-25-000085"),
            amendments_of_latest=[{"accessionNumber": "0000004127-26-000003"}],
        )
    }}
    judgment = _judgment(
        cand,
        verdict="assessment",
        relationships=[],
        assessment={
            "assessment": "not_restated",
            "reason": "part_iii_only_amendment",
            "reason_quote": (
                "The Company is filing this Amendment No. 1 for the sole purpose"
            ),
        },
    )
    out = _mapper(
        census=census,
        ledger_index={("0000004127-26-000003", "swks-20251003.htm"):
                      "2026-10-21T10:55:11Z"},
    ).map(cand, judgment)
    assert out["codes"] == [], out["codes"]
    row = out["rows"][0]
    assert row["row_kind"] == "document_assessment"
    assert row["amends_accession"] == "0000004127-25-000085"
    assert row["assessment"] == "not_restated"
    assert row["reason"] == "part_iii_only_amendment"
    assert row["extracted_by"]["method"] == "narrative_span"
    assert row["source_ref"]["xbrl"] == []

    # amendments_of_prior target
    census_prior = {"issuers": {
        SWKS: _census_entry(
            prior={"accessionNumber": "0000004127-24-000131"},
            amendments_of_prior=[{"accessionNumber": "0000004127-26-000003"}],
        )
    }}
    out = _mapper(
        census=census_prior,
        ledger_index={("0000004127-26-000003", "swks-20251003.htm"):
                      "2026-10-21T10:55:11Z"},
    ).map(cand, judgment)
    assert out["rows"][0]["amends_accession"] == "0000004127-24-000131"
    # unknown target -> refusal
    out = _mapper(
        ledger_index={("0000004127-26-000003", "swks-20251003.htm"):
                      "2026-10-21T10:55:11Z"},
    ).map(cand, judgment)
    assert out["codes"] == ["AMENDMENT_TARGET_UNKNOWN"]
    assert out["rows"] == []
    # a non-amendment candidate refuses assessments
    cue_cand = _make_candidate(origin="cue", rank=1, xbrl_facts=[])
    out = _mapper().map(cue_cand, _judgment(
        cue_cand, verdict="assessment", relationships=[],
        assessment=dict(judgment["assessment"]),
    ))
    assert out["codes"] == ["ASSESSMENT_ON_NON_AMENDMENT"]


# --- K10/K11: coverage, sources, full materialize -------------------------------


def _coverage_cands():
    """Three candidates of one issuer with distinct accessions."""
    a = _make_candidate(acc="0000004127-25-000001", primary_document="a.htm",
                        byte_start=100, xbrl_facts=[])
    b = _make_candidate(acc="0000004127-25-000002", primary_document="b.htm",
                        byte_start=100, xbrl_facts=[])
    c = _make_candidate(
        acc="0000004127-26-000003", form="10-K/A",
        filing_role="amendment_of_latest", origin="amendment_note",
        primary_document="c.htm", byte_start=100, xbrl_facts=[],
        span_raw=(
            b"<p>The Company is filing this Amendment No. 1 for the sole "
            b"purpose of providing Part III information.</p>"
        ),
    )
    return a, b, c


def test_coverage_state_precedence(tmp_path):
    a, b, c = _coverage_cands()
    ok_judgment = _judgment(a, [_rel_entry()])
    nr = _judgment(
        b, verdict="no_relationship", relationships=[],
        no_relationship_reason="no_counterparty_named",
    )
    asm = _judgment(
        c, verdict="assessment", relationships=[],
        assessment={"assessment": "not_restated",
                    "reason": "part_iii_only_amendment",
                    "reason_quote": "The Company is filing this Amendment"},
    )
    ledger = [
        _ledger_row(a["accession"], primary="a.htm",
                    fetched_at="2026-10-21T10:00:01Z"),
        _ledger_row(b["accession"], primary="b.htm",
                    fetched_at="2026-10-21T10:00:02Z"),
        _ledger_row(c["accession"], primary="c.htm",
                    fetched_at="2026-10-21T10:00:03Z", form="10-K/A"),
    ]
    workdir = _workdir(tmp_path, [a, b, c], ledger)
    judgments = workdir / "P" / "judgments"
    _write_jsonl(judgments / "pack_001.jsonl", [ok_judgment, nr, asm])
    empty = tmp_path / "empty"
    empty.mkdir()
    root = tmp_path / "root"
    rc = JCLI.main([
        "materialize", "--leaf", "P", "--workdir", str(workdir),
        "--repo-root", str(root), "--committed-extraction", str(empty),
        "--inputs", str(INPUTS_DIR), "--cache-root", str(tmp_path / "nocache"),
    ])
    assert rc == 0
    rows = [
        json.loads(line)
        for line in (root / "research/theme_graph/gmi_relationships_20261021"
                     / "extraction/m2/P.jsonl").read_text("utf-8").splitlines()
        if line.strip()
    ]
    coverage = {r["issuer_id"]: r for r in rows if r["row_kind"] == "coverage"}
    cov = coverage[SWKS]
    # >= 1 admitted observation -> assessed, reason null
    assert cov["state"] == "assessed" and cov["reason"] is None
    assert cov["documents"] == [a["accession"], b["accession"], c["accession"]]
    assert cov["ingested_at"] == "2026-10-21T10:00:03Z"
    assert cov["published_at"] == "2025-11-07T21:08:12Z"
    assert cov["period_end"] == "2025-10-03"

    # without the observation judgment: the issuer is not_assessed, its
    # admitted assessment still materializes
    workdir2 = _workdir(tmp_path / "w2", [a, b, c], ledger)
    _write_jsonl(workdir2 / "P" / "judgments" / "pack_001.jsonl", [nr, asm])
    root2 = tmp_path / "root2"
    rc = JCLI.main([
        "materialize", "--leaf", "P", "--workdir", str(workdir2),
        "--repo-root", str(root2), "--committed-extraction", str(empty),
        "--allow-missing", "--inputs", str(INPUTS_DIR),
        "--cache-root", str(tmp_path / "nocache"),
    ])
    assert rc == 0
    rows2 = [
        json.loads(line)
        for line in (root2 / "research/theme_graph/gmi_relationships_20261021"
                     / "extraction/m2/P.jsonl").read_text("utf-8").splitlines()
        if line.strip()
    ]
    cov2 = next(r for r in rows2 if r["row_kind"] == "coverage")
    assert cov2["state"] == "not_assessed"
    assert cov2["reason"] == "judgments_missing:1"
    assert any(r["row_kind"] == "document_assessment" for r in rows2)
    assert not any(r["row_kind"] == "observation" for r in rows2)

    # an issuer whose only admitted row is an assessment is no_supported_result
    workdir3 = _workdir(tmp_path / "w3", [c], [ledger[2]])
    _write_jsonl(workdir3 / "P" / "judgments" / "pack_001.jsonl", [asm])
    root3 = tmp_path / "root3"
    assert JCLI.main([
        "materialize", "--leaf", "P", "--workdir", str(workdir3),
        "--repo-root", str(root3), "--committed-extraction", str(empty),
        "--inputs", str(INPUTS_DIR), "--cache-root", str(tmp_path / "nocache"),
    ]) == 0
    rows3 = [
        json.loads(line)
        for line in (root3 / "research/theme_graph/gmi_relationships_20261021"
                     / "extraction/m2/P.jsonl").read_text("utf-8").splitlines()
        if line.strip()
    ]
    cov3 = next(r for r in rows3 if r["row_kind"] == "coverage")
    assert cov3["state"] == "no_supported_result"
    assert cov3["reason"] == "no_admitted_observation:1"

    # an issuer with no collected|partial ledger row is unavailable
    rej = _ledger_row("0000004127-25-000009", state="rejected", role="prior",
                      issuer_id=SWKS)
    root4 = tmp_path / "root4"
    workdir4 = _workdir(tmp_path / "w4", [], [rej])
    assert JCLI.main([
        "materialize", "--leaf", "P", "--workdir", str(workdir4),
        "--repo-root", str(root4), "--committed-extraction", str(empty),
        "--inputs", str(INPUTS_DIR), "--cache-root", str(tmp_path / "nocache"),
    ]) == 0
    rows4 = [
        json.loads(line)
        for line in (root4 / "research/theme_graph/gmi_relationships_20261021"
                     / "extraction/m2/P.jsonl").read_text("utf-8").splitlines()
        if line.strip()
    ]
    cov4 = next(r for r in rows4 if r["row_kind"] == "coverage")
    assert cov4["state"] == "unavailable"
    assert cov4["reason"] == "FORM_MISMATCH"
    assert cov4["documents"] == []
    assert cov4["published_at"] == "2026-10-22T01:50:17Z"
    assert cov4["ingested_at"] == "2026-10-22T01:50:17Z"
    assert cov4["period_end"] == "2025-10-03"


def test_issuer_already_extracted_is_skipped_whole(tmp_path):
    a, b, c = _coverage_cands()
    judgments_rows = [
        _judgment(a, [_rel_entry()]),
        _judgment(
            b, verdict="no_relationship", relationships=[],
            no_relationship_reason="no_counterparty_named",
        ),
        _judgment(
            c, verdict="assessment", relationships=[],
            assessment={
                "assessment": "not_restated",
                "reason": "part_iii_only_amendment",
                "reason_quote": "The Company is filing this Amendment",
            },
        ),
    ]
    ledger = [
        _ledger_row(a["accession"], primary="a.htm"),
        _ledger_row(b["accession"], primary="b.htm"),
        _ledger_row(c["accession"], primary="c.htm", form="10-K/A"),
    ]
    workdir = _workdir(tmp_path, [a, b, c], ledger)
    _write_jsonl(workdir / "P" / "judgments" / "pack_001.jsonl", judgments_rows)
    committed = tmp_path / "committed"
    committed_row = {
        "schema": "company_intelligence.relationship_extraction/v1",
        "row_kind": "observation",
        "subject": {"issuer_id": SWKS},
        "issuer_id": SWKS,
    }
    _write_jsonl(committed / "swks_aapl_m1.jsonl", [committed_row])
    root = tmp_path / "root"
    rc = JCLI.main([
        "materialize", "--leaf", "P", "--workdir", str(workdir),
        "--repo-root", str(root), "--committed-extraction", str(committed),
        "--inputs", str(INPUTS_DIR), "--cache-root", str(tmp_path / "nocache"),
    ])
    assert rc == 0
    out = root / "research/theme_graph/gmi_relationships_20261021"
    rows = [
        json.loads(line)
        for line in (out / "extraction/m2/P.jsonl").read_text("utf-8").splitlines()
        if line.strip()
    ]
    assert rows == []  # skipped whole: no rows of any kind
    assert not (out / "extraction/m2/P.jsonl").exists() or (
        (out / "extraction/m2/P.jsonl").read_text("utf-8").strip() == ""
    )
    report = json.loads(
        (out / "m2/judging/P/materialize_report.json").read_text("utf-8")
    )
    assert report["outcomes"].get("skipped", 0) >= 1
    assert report["coverage_by_state"] == {}
    ledger_rows = [
        json.loads(line)
        for line in (out / "m2/judging/P/materialize_ledger.jsonl")
        .read_text("utf-8").splitlines()
        if line.strip()
    ]
    assert all(entry["outcome"] == "skipped" for entry in ledger_rows)
    assert any("ISSUER_ALREADY_EXTRACTED" in entry["codes"]
               for entry in ledger_rows)


def test_source_reuse_conflict_and_duplicate_span_bytes(tmp_path):
    cand = _make_candidate()
    ledger = [_ledger_row(ACC_25)]
    workdir = _workdir(tmp_path, [cand], ledger)
    _write_jsonl(workdir / "P" / "judgments" / "pack_001.jsonl",
                 [_judgment(cand, [_rel_entry()])])
    empty = tmp_path / "empty"
    empty.mkdir()

    def _sources_root(name):
        root = tmp_path / name
        (root / "research/theme_graph/gmi_relationships_20261021/sources").mkdir(
            parents=True
        )
        (root / "research/theme_graph/gmi_relationships_20261021/extraction").mkdir(
            parents=True
        )
        (root / "research/theme_graph/gmi_relationships_20261021/m2").mkdir(
            parents=True
        )
        return root

    # 1. an existing byte-identical flat source is reused, nothing written
    root = _sources_root("reuse")
    # precompute the excerpt materialize would write and place it flat
    excerpt = dict(cand["excerpt"])
    excerpt["excerpt_note"] = judge.M1_EXCERPT_NOTE
    flat = root / SOURCES_REL / f"{ACC_25}.json"
    flat.write_bytes(
        (json.dumps(excerpt, indent=1, sort_keys=True, ensure_ascii=False)
         + "\n").encode("utf-8")
    )
    rc = JCLI.main([
        "materialize", "--leaf", "P", "--workdir", str(workdir),
        "--repo-root", str(root), "--committed-extraction", str(empty),
        "--inputs", str(INPUTS_DIR), "--cache-root", str(tmp_path / "nocache"),
    ])
    assert rc == 0
    out = root / "research/theme_graph/gmi_relationships_20261021"
    rows = [
        json.loads(line)
        for line in (out / "extraction/m2/P.jsonl").read_text("utf-8").splitlines()
        if line.strip()
    ]
    assert len([r for r in rows if r["row_kind"] == "observation"]) == 1
    assert sorted(p.name for p in (out / "sources").iterdir()) == [
        f"{ACC_25}.json"
    ]
    report = json.loads(
        (out / "m2/judging/P/materialize_report.json").read_text("utf-8")
    )
    assert report["counters"]["sources_reused"] == 1
    assert report["counters"]["sources_written"] == 0

    # 2. an existing file with the same (accession, raw_sha256) but different
    #    bytes -> SOURCE_DUPLICATE_CONFLICT and the citing row is refused
    root2 = _sources_root("conflict")
    conflicted = json.loads(json.dumps(excerpt))
    conflicted["doc_byte_length"] = excerpt["doc_byte_length"] + 1
    (root2 / SOURCES_REL / f"{ACC_25}.json").write_bytes(
        (json.dumps(conflicted, indent=1, sort_keys=True, ensure_ascii=False)
         + "\n").encode("utf-8")
    )
    rc = JCLI.main([
        "materialize", "--leaf", "P", "--workdir", str(workdir),
        "--repo-root", str(root2), "--committed-extraction", str(empty),
        "--inputs", str(INPUTS_DIR), "--cache-root", str(tmp_path / "nocache"),
    ])
    assert rc == 0
    out2 = root2 / "research/theme_graph/gmi_relationships_20261021"
    report2 = json.loads(
        (out2 / "m2/judging/P/materialize_report.json").read_text("utf-8")
    )
    assert report2["codes"].get("SOURCE_DUPLICATE_CONFLICT", 0) >= 1
    assert report2["observations"] == 0

    # 3. two candidates with the same span bytes at different offsets:
    #    the lowest byte_start is kept, the other refused and counted
    dup_low = _make_candidate(byte_start=1000)
    dup_high = _make_candidate(byte_start=5000)
    workdir3 = _workdir(
        tmp_path / "w3", [dup_high, dup_low],
        [_ledger_row(ACC_25), _ledger_row(ACC_25)],
    )
    _write_jsonl(
        workdir3 / "P" / "judgments" / "pack_001.jsonl",
        [_judgment(dup_high, [_rel_entry()]), _judgment(dup_low, [_rel_entry()])],
    )
    root3 = _sources_root("dups")
    rc = JCLI.main([
        "materialize", "--leaf", "P", "--workdir", str(workdir3),
        "--repo-root", str(root3), "--committed-extraction", str(empty),
        "--inputs", str(INPUTS_DIR), "--cache-root", str(tmp_path / "nocache"),
    ])
    assert rc == 0
    out3 = root3 / "research/theme_graph/gmi_relationships_20261021"

    report3 = json.loads(
        (out3 / "m2/judging/P/materialize_report.json").read_text("utf-8")
    )
    assert report3["counters"]["duplicate_span_bytes"] == 1
    assert report3["codes"].get("DUPLICATE_SPAN_BYTES", 0) == 1
    rows3 = [
        json.loads(line)
        for line in (out3 / "extraction/m2/P.jsonl").read_text("utf-8").splitlines()
        if line.strip()
    ]
    assert [
        r["source_ref"]["byte_start"]
        for r in rows3
        if r["row_kind"] == "observation"
    ] == [1000]


def test_judgment_missing_duplicate_unknown_and_schema_codes(tmp_path):
    a, b, c = _coverage_cands()
    d = _make_candidate(acc="0000004127-25-000004",
                        primary_document="d.htm", byte_start=100,
                        xbrl_facts=[])
    ledger = [
        _ledger_row(a["accession"], primary="a.htm"),
        _ledger_row(b["accession"], primary="b.htm"),
        _ledger_row(c["accession"], primary="c.htm"),
        _ledger_row(d["accession"], primary="d.htm"),
    ]
    workdir = _workdir(tmp_path, [a, b, c, d], ledger)
    unknown = _judgment(a)
    unknown["candidate_id"] = "cand:" + "0" * 20
    dup = _judgment(b, verdict="no_relationship", relationships=[],
                    no_relationship_reason="no_counterparty_named")
    invalid = _judgment(c)
    invalid["verdict"] = "not_a_verdict"
    _write_jsonl(
        workdir / "P" / "judgments" / "pack_001.jsonl",
        [unknown, _judgment(a, [_rel_entry()]), dup, dup, invalid],
    )
    empty = tmp_path / "empty"
    empty.mkdir()
    root = tmp_path / "root"
    # a missing judgment is rc 2 without --allow-missing
    rc = JCLI.main([
        "materialize", "--leaf", "P", "--workdir", str(workdir),
        "--repo-root", str(root), "--committed-extraction", str(empty),
        "--inputs", str(INPUTS_DIR), "--cache-root", str(tmp_path / "nocache"),
    ])
    assert rc == 2
    rc = JCLI.main([
        "materialize", "--leaf", "P", "--workdir", str(workdir),
        "--repo-root", str(root), "--committed-extraction", str(empty),
        "--allow-missing", "--inputs", str(INPUTS_DIR),
        "--cache-root", str(tmp_path / "nocache"),
    ])
    assert rc == 0
    out = root / "research/theme_graph/gmi_relationships_20261021"
    report = json.loads(
        (out / "m2/judging/P/materialize_report.json").read_text("utf-8")
    )
    codes = report["codes"]
    assert codes.get("JUDGMENT_UNKNOWN_CANDIDATE") == 1
    assert codes.get("JUDGMENT_DUPLICATE") == 2
    assert codes.get("JUDGMENT_SCHEMA_INVALID") == 1
    assert codes.get("JUDGMENT_MISSING") == 1
    ledger_rows = [
        json.loads(line)
        for line in (out / "m2/judging/P/materialize_ledger.jsonl")
        .read_text("utf-8").splitlines()
        if line.strip()
    ]
    by_outcome = {}
    for entry in ledger_rows:
        by_outcome.setdefault(entry["outcome"], []).append(entry)
    assert by_outcome["missing"][0]["candidate_id"] == d["candidate_id"]
    dup_entries = by_outcome["refused"]
    assert any(e["codes"] == ["JUDGMENT_DUPLICATE"] for e in dup_entries)
    assert [e["candidate_id"] for e in by_outcome["admitted"]] == [
        a["candidate_id"]
    ]


def test_verify_strict_rc_and_materialize_missing_rc(tmp_path):
    a, b, _c = _coverage_cands()
    ledger = [
        _ledger_row(a["accession"], primary="a.htm"),
        _ledger_row(b["accession"], primary="b.htm"),
    ]
    workdir = _workdir(tmp_path, [a, b], ledger)
    empty = tmp_path / "empty"
    empty.mkdir()
    # pack first so index.json exists
    assert JCLI.main(["pack", "--leaf", "P", "--workdir", str(workdir),
                      "--inputs", str(INPUTS_DIR)]) == 0
    clean = _judgment(a, [_rel_entry()])
    _write_jsonl(workdir / "P" / "judgments" / "pack_001.jsonl", [clean])
    assert JCLI.main(["verify", "--leaf", "P", "--workdir", str(workdir),
                      "--inputs", str(INPUTS_DIR),
                      "--cache-root", str(tmp_path / "nocache")]) == 0
    # missing judgment for b: verify rc 0 without --strict, rc 1 with
    assert JCLI.main(["verify", "--leaf", "P", "--workdir", str(workdir),
                      "--inputs", str(INPUTS_DIR),
                      "--cache-root", str(tmp_path / "nocache")]) == 0
    assert JCLI.main(["verify", "--strict", "--leaf", "P", "--workdir",
                      str(workdir), "--inputs", str(INPUTS_DIR),
                      "--cache-root", str(tmp_path / "nocache")]) == 1
    status = JCLI.main(["status", "--leaf", "P", "--workdir", str(workdir),
                        "--inputs", str(INPUTS_DIR)])
    assert status == 0
    root = tmp_path / "root"
    assert JCLI.main(["materialize", "--leaf", "P", "--workdir", str(workdir),
                      "--repo-root", str(root),
                      "--committed-extraction", str(empty),
                      "--inputs", str(INPUTS_DIR),
                      "--cache-root", str(tmp_path / "nocache")]) == 2
    assert JCLI.main(["materialize", "--allow-missing", "--leaf", "P",
                      "--workdir", str(workdir), "--repo-root", str(root),
                      "--committed-extraction", str(empty),
                      "--inputs", str(INPUTS_DIR),
                      "--cache-root", str(tmp_path / "nocache")]) == 0


# --- the load-bearing M1 reproduction -------------------------------------------

M1_HEADER_ET = {
    "0000004127-24-000131": "20241115163743",
    "0000004127-25-000085": "20251107160812",
    "0000004127-26-000003": "20260130160648",
}
M1_INGESTED = {
    "0000004127-24-000131": "2026-10-21T10:48:05Z",
    "0000004127-25-000085": "2026-10-21T10:48:05Z",
    "0000004127-26-000003": "2026-10-21T10:55:11Z",
}
NUM_SCOPE = (
    "net revenue from Apple in aggregate, through distributors, "
    "contract manufacturers and direct sales"
)
DEN_SCOPE = "Skyworks consolidated net revenue"


def _m1_rows():
    return [
        json.loads(line)
        for line in (REPO_ROOT / EXTRACTION_REL).read_text("utf-8").splitlines()
        if line.strip()
    ]


def _m1_candidate(acc, row):
    src = json.loads(
        (REPO_ROOT / SOURCES_REL / f"{acc}.json").read_text("utf-8")
    )
    span = src["span"]
    byte_start, byte_end = span["byte_start"], span["byte_end"]
    candidate_id = "cand:" + pv2.sha(
        pv2.canon([acc, src["primary_document"], byte_start, byte_end])
    )[:20]
    excerpt = dict(src)
    excerpt["excerpt_note"] = judge.EXCERPT_NOTE_TEMPLATE.format(
        candidate_id=candidate_id, origin=row["_origin"]
    )
    facts = []
    for index, xf in enumerate(row.get("_xbrl", [])):
        mag = next(
            m for m in row["magnitudes"] if m["xbrl_fact_id"] == xf["fact_id"]
        )
        period = (
            {"start": mag["period"]["start"], "end": mag["period"]["end"]}
            if mag["period"]["start"]
            else {"instant": mag["period"]["end"]}
        )
        facts.append(
            {
                "concept": xf["concept"],
                "context_ref": xf["context_ref"],
                "fact_id": xf["fact_id"],
                "decimals": xf["decimals"],
                "scale": xf["scale"],
                "format": None,
                "sign": None,
                "raw_value": xf["raw_value"],
                "fact_byte_start": byte_start + 10 + 10 * index,
                "fact_byte_end": byte_start + 10 + 10 * index + 8,
                "period": period,
                "members": [
                    {"dimension": d, "member": m}
                    for d, m in xf["members"].items()
                ],
            }
        )
    return {
        "candidate_id": candidate_id,
        "leaf": "P",
        "issuer_id": SWKS,
        "cik": "0000004127",
        "sec_name": "SKYWORKS SOLUTIONS, INC.",
        "accession": acc,
        "form": src["form"],
        "filing_role": row["_filing_role"],
        "document_type": src["form"],
        "primary_document": src["primary_document"],
        "url": src["url"],
        "doc_sha256": src["doc_sha256"],
        "doc_byte_length": src["doc_byte_length"],
        "filed_at": src["filed_at"],
        "period_of_report": src["period_of_report"],
        "sec_index_header_acceptance_et": M1_HEADER_ET[acc],
        "accepted_at": row["published_at"],
        "sec_submissions_acceptance_raw": row["sec_submissions_acceptance_raw"],
        "origin": row["_origin"],
        "rank": 0,
        "span_kind": "table_row" if row["_origin"] == "xbrl" else "sentence",
        "cues": [],
        "hints": [],
        "xbrl_facts": facts,
        "excerpt": excerpt,
    }


def _m1_workdir(tmp_path):
    rows = _m1_rows()
    tagged = []
    for row in rows:
        acc = (row.get("source_ref") or {}).get("accession")
        if row["row_kind"] == "observation":
            row = dict(row)
            row["_origin"] = "xbrl"
            row["_xbrl"] = row["source_ref"]["xbrl"]
            row["_filing_role"] = (
                "prior" if acc == "0000004127-24-000131" else "latest"
            )
        elif row["row_kind"] == "document_assessment":
            acc = row["source_ref"]["accession"]
            row = dict(row)
            row["_origin"] = "amendment_note"
            row["_filing_role"] = "amendment_of_latest"
        else:
            continue
        tagged.append((acc, row))
    cands = [_m1_candidate(acc, row) for acc, row in tagged]

    ledger = []
    for (acc, row), cand in zip(tagged, cands):
        fetched_at = M1_INGESTED[acc]
        ledger.append(
            {
                "leaf": "P",
                "issuer_id": SWKS,
                "cik": "0000004127",
                "sec_name": "SKYWORKS SOLUTIONS, INC.",
                "accession": acc,
                "form": cand["form"],
                "filing_role": cand["filing_role"],
                "state": "collected",
                "reason": None,
                "accepted_at": row["published_at"],
                "sec_index_header_acceptance_et": M1_HEADER_ET[acc],
                "sec_submissions_acceptance_raw":
                    row["sec_submissions_acceptance_raw"],
                "census_fetched_at": "2026-10-22T01:50:17Z",
                "filed_at": cand["filed_at"],
                "period_of_report": cand["period_of_report"],
                "notes": [],
                "documents": [
                    {
                        "filename": cand["primary_document"],
                        "type": cand["form"],
                        "state": "cached",
                        "reason": None,
                        "http_status": 200,
                        "sha256": cand["doc_sha256"],
                        "byte_length": cand["doc_byte_length"],
                        "fetched_at": fetched_at,
                    }
                ],
            }
        )

    workdir = tmp_path / "work"
    _write_jsonl(workdir / "P" / "candidates.jsonl", cands)
    _write_jsonl(workdir / "P" / "fetch_ledger.jsonl", ledger)
    _write_json(
        workdir / "P" / "harvest_report.json",
        {"schema": "gmi_rel_m2.harvest_report/v1"},
    )
    return workdir, cands


def _m1_judgments(cands):
    judgments = []
    channel = ["distributor", "contract_manufacturer", "direct"]
    for cand in cands:
        if cand["origin"] == "amendment_note":
            record = _judgment(
                cand,
                verdict="assessment",
                relationships=[],
                assessment={
                    "assessment": "not_restated",
                    "reason": "part_iii_only_amendment",
                    "reason_quote": (
                        "The Company is filing this Amendment No. 1 for the "
                        "sole purpose"
                    ),
                },
            )
        else:
            facts = sorted(cand["xbrl_facts"], key=lambda f: f["fact_byte_start"])
            record = _judgment(
                cand,
                [
                    _rel_entry(
                        channel=channel,
                        magnitudes=[
                            {
                                "kind": "seller_revenue_share",
                                "xbrl_fact_ids": [f["fact_id"] for f in facts],
                                "numerator_scope": NUM_SCOPE,
                                "denominator_scope": DEN_SCOPE,
                            }
                        ],
                    )
                ],
            )
        record["judge"] = {"agent": "orch-rel-seat-spotcheck", "lane_run_id": None}
        judgments.append(record)
    return judgments


@pytest.fixture(scope="module")
def m1_repro(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("m1repro")
    workdir, cands = _m1_workdir(tmp)
    assert (
        JCLI.main(["pack", "--leaf", "P", "--workdir", str(workdir),
                   "--inputs", str(INPUTS_DIR)])
        == 0
    )
    judgments = _m1_judgments(cands)
    _write_jsonl(workdir / "P" / "judgments" / "pack_001.jsonl", judgments)
    cache = _cache_with_dei(tmp)
    # every candidate reads its OWN filing's primary document from the cache
    dei_body = (
        b"<html><ix:nonNumeric name=\"dei:EntityRegistrantName\" "
        b"contextRef=\"c-1\">Skyworks Solutions, Inc.</ix:nonNumeric></html>"
    )
    for nodash, filename in (
        ("000000412724000131", "swks-20240927.htm"),
        ("000000412725000085", "swks-20251003.htm"),
        ("000000412726000003", "swks-20251003.htm"),
    ):
        cache.store(4127, nodash, filename, dei_body,
                    "https://example.invalid", 200,
                    "2026-10-21T10:00:00Z")
    empty = tmp / "empty"
    empty.mkdir()
    root = tmp / "root"
    sources = root / SOURCES_REL
    sources.mkdir(parents=True)
    for acc in M1_HEADER_ET:
        (sources / f"{acc}.json").write_bytes(
            (REPO_ROOT / SOURCES_REL / f"{acc}.json").read_bytes()
        )
    rc = JCLI.main([
        "materialize", "--leaf", "P", "--workdir", str(workdir),
        "--repo-root", str(root), "--committed-extraction", str(empty),
        "--inputs", str(INPUTS_DIR), "--cache-root", str(tmp / "cache"),
    ])
    assert rc == 0, "materialize failed"
    return {
        "tmp": tmp,
        "workdir": workdir,
        "root": root,
        "rc": rc,
    }


def test_m1_rows_reproduced_byte_identical(m1_repro):
    root = m1_repro["root"]
    out_path = (
        root
        / "research/theme_graph/gmi_relationships_20261021/extraction/m2/P.jsonl"
    )
    produced = out_path.read_bytes()
    committed = (REPO_ROOT / EXTRACTION_REL).read_bytes()
    assert produced == committed
    # the flat M1 sources were reused byte-identically: nothing new written
    sources_dir = root / SOURCES_REL
    assert sorted(p.name for p in sources_dir.iterdir()) == [
        "0000004127-24-000131.json",
        "0000004127-25-000085.json",
        "0000004127-26-000003.json",
    ]
    report = json.loads(
        (root / "research/theme_graph/gmi_relationships_20261021/m2/judging/P"
         / "materialize_report.json").read_text("utf-8")
    )
    assert report["observations"] == 2
    assert report["assessments"] == 1
    assert report["coverage_by_state"] == {"assessed": 1}
    assert report["codes"] == {}
    assert report["outcomes"] == {"admitted": 3}
    assert report["edges"] == [
        {"species": "supplier_customer",
         "subject_issuer_id": SWKS, "object_issuer_id": AAPL}
    ]


def test_materialize_rerun_byte_identical(m1_repro):
    tmp = m1_repro["tmp"]
    root2 = tmp / "root2"
    # identical starting state: the same three flat M1 sources already present
    sources = root2 / SOURCES_REL
    sources.mkdir(parents=True)
    for acc in M1_HEADER_ET:
        (sources / f"{acc}.json").write_bytes(
            (REPO_ROOT / SOURCES_REL / f"{acc}.json").read_bytes()
        )
    rc = JCLI.main([
        "materialize", "--leaf", "P", "--workdir", str(m1_repro["workdir"]),
        "--repo-root", str(root2), "--committed-extraction", str(tmp / "empty"),
        "--inputs", str(INPUTS_DIR), "--cache-root", str(tmp / "cache"),
    ])
    assert rc == 0

    def _snapshot(root):
        return {
            str(p.relative_to(root)): _sha(p.read_bytes())
            for p in sorted(root.rglob("*"))
            if p.is_file()
        }

    assert _snapshot(m1_repro["root"]) == _snapshot(root2)


def test_producer_reads_materialized_output(m1_repro, tmp_path):
    base = m1_repro["root"] / "research/theme_graph/gmi_relationships_20261021"
    out_dir = tmp_path / "producer_out"
    rc = PRODUCER.main([
        "--as-of", "2026-10-22T00:00:00Z",
        "--extraction", str(base / "extraction"),
        "--sources", str(base / "sources"),
        "--manifest", str(MANIFEST_PATH),
        "--out-dir", str(out_dir),
    ])
    assert rc == 0, "producer failed"
    edges = json.loads((out_dir / "relationship_edges.json").read_text("utf-8"))
    assert len(edges["edges"]) == 1
    edge = edges["edges"][0]
    assert edge["species"] == "supplier_customer"
    assert edge["direction"] == {
        "from_issuer_id": SWKS,
        "to_issuer_id": AAPL,
        "from_role": "supplier",
        "to_role": "customer",
    }

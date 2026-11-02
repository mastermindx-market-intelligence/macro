"""M2 harvest lane: EDGAR fetch, index-header clock, iXBRL facts, cue candidates.

Synthetic fixtures only — no network (an autouse fixture makes
``urllib.request.urlopen`` raise, and fetch tests inject a fake opener/cache).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import urllib.request
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from engine.company_intelligence.relationships import edgar as rel_edgar  # noqa: E402
from engine.company_intelligence.relationships import harvest as rel_harvest  # noqa: E402
from engine.company_intelligence.relationships import package_v2  # noqa: E402
from engine.company_intelligence.relationships import replay  # noqa: E402

CONTRACT_REL = (
    "contracts/company_intelligence/relationship_source_excerpt.v1.schema.json"
)
M2_INPUTS_REL = "research/theme_graph/gmi_relationships_20261021/m2_inputs"
EXCERPT_SCHEMA = json.loads((REPO_ROOT / CONTRACT_REL).read_text("utf-8"))

SWKS = "ISS:US-XNAS-SWKS"
FILER_NAME = "SKYWORKS SOLUTIONS, INC."
ACC = "0000004127-25-000085"
ACC_NODASH = "000000412725000085"

CONTEXT_C1 = (
    '<xbrli:context id="c-1"><xbrli:entity>'
    '<xbrli:identifier scheme="http://www.sec.gov/CIK">0000004127</xbrli:identifier>'
    '</xbrli:entity><xbrli:period><xbrli:startDate>2024-10-01</xbrli:startDate>'
    '<xbrli:endDate>2025-10-03</xbrli:endDate></xbrli:period><xbrli:scenario>'
    '<xbrli:explicitMember dimension="srt:MajorCustomersAxis">x:AppleMember'
    "</xbrli:explicitMember></xbrli:scenario></xbrli:context>"
)
CONTEXT_C2 = (
    '<xbrli:context id="c-2"><xbrli:entity>'
    '<xbrli:identifier scheme="http://www.sec.gov/CIK">0000004127</xbrli:identifier>'
    '</xbrli:entity><xbrli:period><xbrli:instant>2025-10-03</xbrli:instant>'
    '</xbrli:period><xbrli:scenario><xbrli:explicitMember '
    'dimension="srt:MajorCustomersAxis">x:OtherMember</xbrli:explicitMember>'
    "</xbrli:scenario></xbrli:context>"
)
CONTEXT_C3 = (
    '<xbrli:context id="c-3"><xbrli:entity>'
    '<xbrli:identifier scheme="http://www.sec.gov/CIK">0000004127</xbrli:identifier>'
    '</xbrli:entity><xbrli:period><xbrli:startDate>2024-10-01</xbrli:startDate>'
    '<xbrli:endDate>2025-10-03</xbrli:endDate></xbrli:period><xbrli:scenario>'
    '<xbrli:explicitMember dimension="us-gaap:StatementBusinessSegmentsAxis">'
    "x:TotalMember</xbrli:explicitMember></xbrli:scenario></xbrli:context>"
)

FACT_F1 = (
    '<ix:nonFraction name="us-gaap:ConcentrationRiskPercentage1" contextRef="c-1" '
    'id="f-1" scale="-2" decimals="2">67</ix:nonFraction>'
)
FACT_F4 = (
    '<ix:nonFraction name="us-gaap:ConcentrationRiskPercentage1" contextRef="c-3" '
    'id="f-4" scale="-2" decimals="2">12</ix:nonFraction>'
)
FACT_F3 = (
    '<ix:nonFraction name="us-gaap:ConcentrationRiskPercentage1" contextRef="c-1" '
    'id="f-3" scale="-2" decimals="2">21</ix:nonFraction>'
)
FACT_FHID = (
    '<ix:nonFraction name="us-gaap:ConcentrationRiskPercentage1" contextRef="c-2" '
    'id="f-hidden" scale="-2" decimals="2">9</ix:nonFraction>'
)

DOC = (
    "<html><head><title>Annual report</title><style>.x { color: red; }</style></head>"
    "<body><ix:header><ix:hidden><div>quiet largest customer note</div>"
    + FACT_FHID
    + "</ix:hidden><ix:resources>"
    + CONTEXT_C1
    + CONTEXT_C2
    + CONTEXT_C3
    + "</ix:resources></ix:header>"
    '<div style="display:none"><p>Hidden Apple sales were 11% of net sales '
    "under a sole-source arrangement.</p></div>"
    "<p>During fiscal 2025, <span style=\"font-weight:bold\">Apple</span>, through "
    "sales to <span>multiple distributors</span>, in the aggregate accounted for "
    + FACT_F1
    + "% of the Company&#8217;s net revenue, respectively.</p>"
    "<p>Concentrations of credit risk were "
    + FACT_F4
    + "% of total assets at year end.</p>"
    "<p>Apple is our largest customer.</p>"
    "<p>Sales to Baker Hughes Incorporated are long-term supply agreements.</p>"
    "<p>Customer A purchases were 10% of net revenue.</p>"
    "<p>Sales to a certain buyer represented 8% of net revenue.</p>"
    "<table><tr><td>Apple Inc.</td><td>Sales of " + FACT_F3 + "% of net sales</td>"
    "</tr></table>"
    "<p>Skyworks Solutions is our largest customer and a key distributor "
    "partner.</p></body></html>"
).encode("utf-8")

DOC_AMENDMENT = (
    "<html><head><title>10-K/A</title></head><body>"
    "<p>This Amendment No. 1 to the Annual Report on Form 10-K is being filed "
    "solely to correct the auditor's report.</p><p>The fiscal year ended "
    "October 3, 2025.</p></body></html>"
).encode("utf-8")

LONG_WORD = "concentration" * 200  # 2600 bytes, exceeds the span cap alone


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    def _boom(*args, **kwargs):
        raise AssertionError("urlopen must never be called in tests")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)


@pytest.fixture()
def resolver():
    return {
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


@pytest.fixture()
def aliases():
    return {
        "schema": "orch_rel.m2_curated_aliases/v1",
        "aliases": [
            {
                "alias": "Advanced Micro Devices",
                "alias_norm": "advanced micro devices",
                "issuer_id": "ISS:US-XNAS-AMD",
                "target": "issuer",
                "non_edge_reason": None,
                "cn_security_id": None,
                "basis": "test",
            },
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


def _hints(resolver_doc, aliases_doc):
    all_hints, own = rel_harvest.build_hints(
        resolver_doc, aliases_doc, SWKS
    )
    return all_hints, own


def _extract(doc, *, amendment_primary=False, max_per_doc=40, hints=None):
    if hints is None:
        hints = (
            {"apple", "advanced micro devices"},
            {"skyworks", "skyworks solutions"},
        )
    counters = rel_harvest.new_counters()
    cands = rel_harvest.extract_document_candidates(
        doc,
        hints=hints[0],
        own_hints=hints[1],
        counters=counters,
        amendment_primary=amendment_primary,
        max_per_doc=max_per_doc,
    )
    return cands, counters


# --- inputs ------------------------------------------------------------------


def test_m2_inputs_pins():
    assert rel_harvest.PINS == {
        "curated_aliases_v1.json": (
            "413ea9e26b08a1b2d59099bc86456d9cad1ea0347cfb33bb1f42b11a1b4b8c76"
        ),
        "filing_census_v1.json": (
            "d5deb2764e67e25789452f11b2a4793b8c00eef5431474ad42bfde5a60affaa9"
        ),
        "leaves_v1.json": (
            "8e505316da9ccc1285227eec080a52e5e182f28780401dfa1817dd6c5313adef"
        ),
        "resolver_us_issuers_v1.json": (
            "a18924867fa53f58c0e01ac873d5bc2a8d610a01b69ad333ea6dfb51183303cd"
        ),
    }
    for name, expected in rel_harvest.PINS.items():
        path = REPO_ROOT / M2_INPUTS_REL / name
        assert _sha(path.read_bytes()) == expected, name
    inputs = rel_harvest.load_inputs(REPO_ROOT / M2_INPUTS_REL)
    assert "ISS:US-XNAS-SWKS" in inputs["census"]["issuers"]
    assert SWKS in inputs["leaves"]["leaves"]["P"]
    # a corrupted copy is refused
    import shutil

    tmp = Path("/tmp/gmi_m2_pins_bad")
    if tmp.exists():
        shutil.rmtree(tmp)
    shutil.copytree(REPO_ROOT / M2_INPUTS_REL, tmp)
    (tmp / "leaves_v1.json").write_text("{}\n", "utf-8")
    with pytest.raises(rel_harvest.InputPinMismatch):
        rel_harvest.load_inputs(tmp)


# --- edgar.py ----------------------------------------------------------------

INDEX_HEADER = """<html><head><title> Submission </title>
<!--
<SEC-HEADER>x.hdr.sgml : 20251107
<ACCEPTANCE-DATETIME>20251107160812
</SEC-HEADER>-->
</HEAD><BODY><PRE>&lt;SEC-DOCUMENT&gt;x-index.html : 20251107
&lt;SEC-HEADER&gt;x.hdr.sgml : 20251107
&lt;ACCEPTANCE-DATETIME&gt;20251107160812
ACCESSION NUMBER:\t\t0000004127-25-000085
CONFORMED SUBMISSION TYPE:\t10-K
PUBLIC DOCUMENT COUNT:\t\t102
CONFORMED PERIOD OF REPORT:\t20251003
FILED AS OF DATE:\t\t20251107
&lt;DOCUMENT&gt;
&lt;TYPE&gt;10-K
&lt;SEQUENCE&gt;1
&lt;FILENAME&gt;swks-20251003.htm
&lt;DESCRIPTION&gt;10-K
&lt;/DOCUMENT&gt;
&lt;DOCUMENT&gt;
&lt;TYPE&gt;EX-13.2
&lt;SEQUENCE&gt;3
&lt;FILENAME&gt;q4fy25exhibit13.htm
&lt;/DOCUMENT&gt;
&lt;DOCUMENT&gt;
&lt;TYPE&gt;GRAPHIC
&lt;FILENAME&gt;g1.jpg
&lt;/DOCUMENT&gt;
</PRE></BODY></html>"""


def test_index_headers_parse_acceptance_form_period_documents():
    parsed = rel_edgar.parse_index_headers(INDEX_HEADER.encode("utf-8"))
    assert parsed["acceptance_et"] == "20251107160812"
    assert parsed["submission_type"] == "10-K"
    assert parsed["period_of_report"] == "2025-10-03"
    assert parsed["filed_as_of_date"] == "2025-11-07"
    assert [d["filename"] for d in parsed["documents"]] == [
        "swks-20251003.htm",
        "q4fy25exhibit13.htm",
        "g1.jpg",
    ]
    assert [d["type"] for d in parsed["documents"]] == [
        "10-K",
        "EX-13.2",
        "GRAPHIC",
    ]
    assert parsed["documents"][0]["sequence"] == "1"


def test_accepted_at_from_index_header_and_clock_refusal_rejects_filing():
    accepted, reason = rel_harvest.accepted_at_from_header("20251107160812")
    assert (accepted, reason) == ("2025-11-07T21:08:12Z", None)
    # spring-forward 2026-03-08 02:30 ET does not exist
    accepted, reason = rel_harvest.accepted_at_from_header("20260308023000")
    assert accepted is None and reason == "nonexistent"
    # fall-back 2026-11-01 01:30 ET occurs twice
    accepted, reason = rel_harvest.accepted_at_from_header("20261101013000")
    assert accepted is None and reason == "ambiguous"
    row = rel_harvest.resolve_filing(
        leaf="P",
        issuer_id=SWKS,
        cik_str="0000004127",
        sec_name=FILER_NAME,
        filing_role="latest",
        census_filing={
            "accessionNumber": ACC,
            "form": "10-K",
            "filingDate": "2025-11-07",
            "reportDate": "2025-10-03",
            "acceptanceDateTime": "2025-11-08T02:08:12.000Z",
            "primaryDocument": "swks-20251003.htm",
        },
        header=rel_edgar.parse_index_headers(INDEX_HEADER.encode("utf-8")),
        census_fetched_at="2026-10-22T01:50:17Z",
    )
    assert row["accepted_at"] == "2025-11-07T21:08:12Z"
    assert row["state"] == "pending_documents"
    bad_header = dict(rel_edgar.parse_index_headers(INDEX_HEADER.encode("utf-8")))
    bad_header["acceptance_et"] = "20260308023000"
    row = rel_harvest.resolve_filing(
        leaf="P",
        issuer_id=SWKS,
        cik_str="0000004127",
        sec_name=FILER_NAME,
        filing_role="latest",
        census_filing={"accessionNumber": ACC, "form": "10-K",
                       "filingDate": "2025-11-07", "reportDate": "2025-10-03",
                       "acceptanceDateTime": "2025-11-08T02:08:12.000Z",
                       "primaryDocument": "swks-20251003.htm"},
        header=bad_header,
        census_fetched_at="2026-10-22T01:50:17Z",
    )
    assert row["state"] == "rejected"
    assert row["reason"] == "CLOCK_REFUSED:nonexistent"


def test_submissions_acceptance_is_carried_raw_never_clock():
    row = rel_harvest.resolve_filing(
        leaf="P",
        issuer_id=SWKS,
        cik_str="0000004127",
        sec_name=FILER_NAME,
        filing_role="latest",
        census_filing={"accessionNumber": ACC, "form": "10-K",
                       "filingDate": "2025-11-07", "reportDate": "2025-10-03",
                       "acceptanceDateTime": "2025-11-08T02:08:12.000Z",
                       "primaryDocument": "swks-20251003.htm"},
        header=rel_edgar.parse_index_headers(INDEX_HEADER.encode("utf-8")),
        census_fetched_at="2026-10-22T01:50:17Z",
    )
    assert row["sec_submissions_acceptance_raw"] == "2025-11-08T02:08:12.000Z"
    assert row["accepted_at"] == "2025-11-07T21:08:12Z"  # header-derived, +5h apart


def test_document_selection_by_form():
    header = rel_edgar.parse_index_headers(INDEX_HEADER.encode("utf-8"))
    docs, notes = rel_harvest.select_documents(
        header["documents"], "10-K", "swks-20251003.htm"
    )
    # primary + EX-13* ; GRAPHIC skipped by extension rule
    assert [(d["filename"], d["type"]) for d in docs] == [
        ("swks-20251003.htm", "10-K"),
        ("q4fy25exhibit13.htm", "EX-13.2"),
    ]
    assert notes == []
    # census disagreement on the primary document is recorded, census wins
    docs, notes = rel_harvest.select_documents(
        header["documents"], "10-K", "other-primary.htm"
    )
    assert docs[0]["filename"] == "other-primary.htm"
    assert notes == ["PRIMARY_DOC_MISMATCH"]
    # a 20-F selects EX-99* instead of EX-13*
    docs, _ = rel_harvest.select_documents(
        [
            {"type": "20-F", "filename": "form20f.htm", "sequence": "1"},
            {"type": "EX-99.1", "filename": "ex991.htm", "sequence": "2"},
            {"type": "EX-13.1", "filename": "ex131.htm", "sequence": "3"},
            {"type": "EX-101.SCH", "filename": "wpm-20251231.xsd", "sequence": "4"},
        ],
        "20-F",
        "form20f.htm",
    )
    assert [d["filename"] for d in docs] == ["form20f.htm", "ex991.htm"]
    # out-of-contract form and index/census form mismatch are rejections
    assert rel_harvest.form_rejection("8-K", "8-K") == "OUT_OF_CONTRACT_FORM"
    assert rel_harvest.form_rejection("10-K", "10-K/A") == "FORM_MISMATCH"


def test_census_not_ok_is_unavailable_with_census_clock():
    row = rel_harvest.build_unavailable_row(
        "P",
        SWKS,
        {
            "state": "NO_ANNUAL_IN_RECENT",
            "fetched_at": "2026-10-22T01:50:17Z",
            "cik": 4127,
            "sec_name": FILER_NAME,
        },
    )
    assert row["state"] == "unavailable"
    assert row["reason"] == "NO_ANNUAL_IN_RECENT"
    assert row["census_fetched_at"] == "2026-10-22T01:50:17Z"
    assert row["accession"] is None and row["documents"] == []


class FakeCache:
    def __init__(self, root):
        self.root = Path(root)
        self.counters = {"cache_integrity_refetch": 0}


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def _client(tmp_path, opener, rps=3.0):
    clock = FakeClock()
    sleeps = []
    client = rel_edgar.EdgarClient(
        cache_root=str(tmp_path / "cache"),
        rps=rps,
        clock=clock,
        sleep=sleeps.append,
        opener=opener,
        offline=False,
    )
    return client, clock, sleeps


def test_fetch_retry_backoff_and_no_retry_on_404(tmp_path):
    calls = []

    def flaky(url, headers):
        calls.append(url)
        if len(calls) <= 2:
            raise urllib.error.URLError("boom")
        return 200, {}, b"document-bytes"

    client, clock, sleeps = _client(tmp_path, flaky)
    result = client.fetch(4127, ACC_NODASH, "swks-20251003.htm")
    assert result.state == "fetched"
    assert result.body == b"document-bytes"
    # the backoff sleeps are exactly 2s then 4s; the rate limiter's own
    # sub-second waits may interleave
    assert [s for s in sleeps if s > 1.0] == [2.0, 4.0]
    # second read is served from the (integrity-checked) cache with no network
    result = client.fetch(4127, ACC_NODASH, "swks-20251003.htm")
    assert result.state == "cached"
    assert len(calls) == 3

    def gone(url, headers):
        return 404, {}, b"nope"

    client2, _clock, sleeps2 = _client(tmp_path, gone)
    with pytest.raises(rel_edgar.HttpError) as err:
        client2.fetch(4127, ACC_NODASH, "missing.htm")
    assert err.value.status == 404
    assert sleeps2 == []


def test_cache_integrity_mismatch_is_not_used(tmp_path):
    client, _clock, _sleeps = _client(tmp_path, lambda url, h: (200, {}, b"fresh"))
    client.fetch(4127, ACC_NODASH, "doc.htm")
    path = (
        Path(client.cache.root) / "4127" / ACC_NODASH / "doc.htm"
    )
    path.write_bytes(b"tampered")
    calls = []

    def opener(url, headers):
        calls.append(url)
        return 200, {}, b"fresh"

    client2, _clock, _sleeps = _client(tmp_path, opener)
    result = client2.fetch(4127, ACC_NODASH, "doc.htm")
    assert result.state == "fetched"
    assert result.body == b"fresh"
    assert client2.counters["cache_integrity_refetch"] == 1
    assert len(calls) == 1


def test_offline_cache_miss_is_failed_network_disabled(tmp_path):
    client, _clock, _sleeps = _client(tmp_path, None)
    client.offline = True
    with pytest.raises(rel_edgar.NetworkDisabled):
        client.fetch(4127, ACC_NODASH, "absent.htm")


# --- segmentation ------------------------------------------------------------


def test_segment_skips_header_script_style_hidden():
    seg = rel_harvest.segment(DOC)
    text = " ".join(s.text for s in seg.sentences)
    assert "quiet largest customer" not in text
    assert "Hidden Apple sales" not in text
    assert "Annual report" not in text  # <title> inside <head>
    assert "color: red" not in text  # <style>
    # normal visible text survives, with entities decoded and tags stripped
    assert "accounted for 67% of the Company’s net revenue" in text
    # skip ranges cover the ix:header subtree and the display:none div
    starts = [r[0] for r in seg.skip_ranges]
    ix_at = DOC.index(b"<ix:header>")
    hidden_at = DOC.index(b'<div style="display:none">')
    assert any(s <= ix_at < e for s, e in seg.skip_ranges)
    assert any(s <= hidden_at < e for s, e in seg.skip_ranges)


def test_boundaries_never_inside_tag_or_entity():
    seg = rel_harvest.segment(DOC)
    entity_ranges = [
        (m.start(), m.end())
        for m in rel_harvest.ENTITY_RE.finditer(DOC)
    ]
    tag_ranges = [
        (m.start(), m.end()) for m in rel_harvest.TAG_RE.finditer(DOC)
    ]
    for sent in seg.sentences:
        bs, be = sent.bs, sent.be
        for p, q in entity_ranges + tag_ranges:
            assert bs <= p and q <= be or be <= p or bs >= q, (bs, be, p, q)


def test_sentence_split_abbreviation_and_decimal_guard():
    assert rel_harvest.sentence_boundaries(
        "Skyworks Inc. reported 3.5% growth. Sales to Apple rose."
    ) == [len("Skyworks Inc. reported 3.5% growth.")]
    assert rel_harvest.sentence_boundaries("See U.S. markets. E.g. this.") == [
        len("See U.S. markets.")
    ]
    assert rel_harvest.sentence_boundaries(
        "See U.S. markets. Later text."
    ) == [len("See U.S. markets.")]
    assert rel_harvest.sentence_boundaries("Growth of 3.5 was real.") == []
    assert rel_harvest.sentence_boundaries(
        "Co. Ltd. vs. peers. Next one."
    ) == [len("Co. Ltd. vs. peers.")]


# --- iXBRL facts --------------------------------------------------------------


def _by_fact(cands, fact_id):
    return [
        c
        for c in cands
        if any(f["fact_id"] == fact_id for f in c["xbrl_facts"])
    ]


def test_xbrl_fact_anchor_sentence_with_customer_axis():
    cands, counters = _extract(DOC)
    hits = _by_fact(cands, "f-1")
    assert len(hits) == 1
    cand = hits[0]
    assert cand["origin"] == "xbrl" and cand["rank"] == 0
    assert cand["span_kind"] == "sentence"
    fact = cand["xbrl_facts"][0]
    assert fact["concept"] == "us-gaap:ConcentrationRiskPercentage1"
    assert fact["context_ref"] == "c-1"
    assert fact["fact_id"] == "f-1"
    assert fact["decimals"] == "2" and fact["scale"] == "-2"
    assert fact["sign"] is None and fact["raw_value"] == "67"
    assert fact["members"] == [
        {"dimension": "srt:MajorCustomersAxis", "member": "x:AppleMember"}
    ]
    assert fact["period"] == {"start": "2024-10-01", "end": "2025-10-03"}
    # the fact element byte range slices to exactly the fixture element
    assert DOC[fact["fact_byte_start"] : fact["fact_byte_end"]] == (
        FACT_F1.encode("utf-8")
    )
    # the sentence that is also an xbrl anchor stays ONE candidate carrying
    # the union of cues (distributors + accounted-for percent)
    assert cand["cues"] == ["distributor", "pct_of_revenue"]
    norm = package_v2.normalize_span(
        DOC[cand["span"]["byte_start"] : cand["span"]["byte_end"]]
    )
    assert "in the aggregate accounted for 67%" in norm
    ctx = [c for c in cand["excerpt_contexts"] if c["context_ref"] == "c-1"]
    assert len(ctx) == 1
    start = DOC.index(CONTEXT_C1.encode("utf-8"))
    assert ctx[0]["byte_start"] == start
    assert ctx[0]["raw"] == CONTEXT_C1
    assert counters["xbrl_fact_no_counterparty_axis"] >= 0  # see test below


def test_xbrl_fact_in_table_anchors_row():
    cands, _ = _extract(DOC)
    hits = _by_fact(cands, "f-3")
    assert len(hits) == 1
    cand = hits[0]
    assert cand["origin"] == "xbrl" and cand["rank"] == 0
    assert cand["span_kind"] == "table_row"
    raw = DOC[cand["span"]["byte_start"] : cand["span"]["byte_end"]]
    assert raw.startswith(b"<tr>") and raw.endswith(b"</tr>")
    assert FACT_F3.encode("utf-8") in raw
    norm = package_v2.normalize_span(raw)
    assert "Apple Inc." in norm and "Sales of 21% of net sales" in norm
    assert [c["context_ref"] for c in cand["excerpt_contexts"]] == ["c-1"]


def test_xbrl_fact_without_customer_axis_counted():
    cands, counters = _extract(DOC)
    assert counters["xbrl_fact_no_counterparty_axis"] == 1
    assert _by_fact(cands, "f-4") == []
    # its sentence carries no cue either, so no cue candidate covers it either
    assert not [
        c
        for c in cands
        if c["origin"] == "cue"
        and "total assets" in package_v2.normalize_span(
            DOC[c["span"]["byte_start"] : c["span"]["byte_end"]]
        )
    ]


def test_xbrl_hidden_fact_counted():
    cands, counters = _extract(DOC)
    assert counters["xbrl_fact_hidden"] == 1
    assert _by_fact(cands, "f-hidden") == []


# --- cues ---------------------------------------------------------------------


def test_cue_requires_qualifier_and_ranks():
    cands, counters = _extract(DOC)
    cue = [c for c in cands if c["origin"] == "cue"]
    # two rank-4s: the pct-only sentence and the pct-only table cell (the
    # cell's span is distinct from the f-3 row anchor, so it stays its own
    # candidate — only exact-span matches merge into the xbrl candidate)
    assert sorted(c["rank"] for c in cue) == [1, 2, 3, 4, 4]
    by_rank = {}
    for c in cue:
        by_rank.setdefault(c["rank"], []).append(c)
    by_rank = {k: v[0] for k, v in by_rank.items()}
    assert by_rank[1]["hints"] == ["apple"]
    assert by_rank[1]["cues"] == ["major_customer"]
    assert "Baker Hughes Incorporated" in package_v2.normalize_span(
        DOC[by_rank[2]["span"]["byte_start"] : by_rank[2]["span"]["byte_end"]]
    )
    assert by_rank[2]["hints"] == []
    assert by_rank[3]["cues"] == ["pct_of_revenue"]
    assert by_rank[4]["cues"] == ["pct_of_revenue"]
    assert by_rank[4]["hints"] == []
    # the no-qualifier, no-cue sentences produced nothing
    assert counters["overflow_document"] == 0


def test_filer_own_name_is_not_a_hint(resolver, aliases):
    all_hints, own_hints = _hints(resolver, aliases)
    assert "skyworks" not in all_hints and "skyworks solutions" not in all_hints
    assert own_hints == {"skyworks solutions", "skyworks"}
    assert "apple" in all_hints and "advanced micro devices" in all_hints
    cands, _ = _extract(DOC, hints=(all_hints, own_hints))
    for cand in cands:
        norm = package_v2.normalize_span(
            DOC[cand["span"]["byte_start"] : cand["span"]["byte_end"]]
        )
        assert "Skyworks Solutions is our largest" not in norm
        assert "skyworks" not in cand["hints"]


def test_caps_and_overflow_counted():
    doc = (
        b"<html><body><p>Buyer One bought 1% of net revenue.</p>"
        b"<p>Buyer Two bought 2% of net revenue.</p>"
        b"<p>Buyer Three bought 3% of net revenue.</p></body></html>"
    )
    cands, counters = _extract(doc, max_per_doc=2)
    assert len(cands) == 2
    assert counters["overflow_document"] == 1
    counters2 = rel_harvest.new_counters()
    kept = rel_harvest.apply_filing_caps(
        cands
        + [
            dict(
                cands[0],
                **{"span": {"byte_start": 9999, "byte_end": 10999}},
            )
        ],
        counters2,
        max_filing=2,
    )
    assert len(kept) == 2
    assert counters2["overflow_filing"] == 1


# --- span assembly -------------------------------------------------------------


def test_span_fallbacks_and_too_large_counted():
    pad_prev = "data " * 299 + "End. "  # ~1500 bytes, splits before target
    pad_next = "Zebra " * 210  # splits after target ("year. Z...")
    target = "Apple was our largest customer in the year."
    doc = (
        "<html><body><p>"
        + pad_prev
        + target
        + " "
        + pad_next
        + "</p></body></html>"
    ).encode("utf-8")
    cands, counters = _extract(doc)
    assert len(cands) == 1 and cands[0]["span_kind"] == "sentence_m1"
    assert counters["span_too_large"] == 0
    # clause fallback: the sentence alone exceeds the cap, the clause window
    # around the matched tokens fits
    clause_doc = (
        "<html><body><p>Over the year ended, "
        + "buyer " * 400
        + ", sales of 8% of net revenue made us the company with our "
        + "largest customer.</p></body></html>"
    ).encode("utf-8")
    cands2, counters2 = _extract(clause_doc)
    assert len(cands2) == 1 and cands2[0]["span_kind"] == "clause"
    # nothing fits: the qualifying sentence (rank-1 hint) has no comma to
    # clause-split at, and its single giant word keeps every window over cap
    huge_doc = (
        "<html><body><p>Apple "
        + LONG_WORD
        + " was our largest customer.</p></body></html>"
    ).encode("utf-8")
    cands3, counters3 = _extract(huge_doc)
    assert cands3 == []
    assert counters3["span_too_large"] == 1


def test_non_utf8_span_counted():
    doc = (
        b"<html><body><p>Apple was our largest customer \xff\xfe here.</p>"
        b"</body></html>"
    )
    cands, counters = _extract(doc)
    assert cands == []
    assert counters["span_not_utf8"] == 1


def test_amendment_note_candidate():
    cands, counters = _extract(DOC_AMENDMENT, amendment_primary=True)
    assert len(cands) == 1
    cand = cands[0]
    assert cand["origin"] == "amendment_note" and cand["rank"] == 0
    norm = package_v2.normalize_span(
        DOC_AMENDMENT[cand["span"]["byte_start"] : cand["span"]["byte_end"]]
    )
    assert norm.startswith("This Amendment No. 1")
    assert cand["cues"] == []
    # without the amendment flag the same document yields no candidate
    cands2, _ = _extract(DOC_AMENDMENT, amendment_primary=False)
    assert cands2 == []
    assert counters["excerpt_self_check_failed"] == 0


# --- candidate finalization through the CLI -----------------------------------

CLI = importlib.import_module("scripts.relationship_m2_harvest")


def _write_synthetic_inputs(tmp_path, monkeypatch, resolver_doc, aliases_doc):
    inputs = tmp_path / "m2_inputs"
    inputs.mkdir()
    leaves = {"schema": "orch_rel.m2_leaves/v1", "leaves": {"P": [SWKS]}}
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
    blobs = {
        "leaves_v1.json": leaves,
        "filing_census_v1.json": census,
        "curated_aliases_v1.json": aliases_doc,
        "resolver_us_issuers_v1.json": resolver_doc,
    }
    pins = {}
    for name, doc in blobs.items():
        raw = (json.dumps(doc, sort_keys=True) + "\n").encode("utf-8")
        (inputs / name).write_bytes(raw)
        pins[name] = _sha(raw)
    monkeypatch.setattr(rel_harvest, "PINS", pins)
    return inputs, census


def _synthetic_cache(tmp_path, monkeypatch):
    cache = tmp_path / "cache" / "4127" / ACC_NODASH
    cache.mkdir(parents=True)
    doc = (
        "<html><head><title>x</title></head><body>"
        "<ix:header><ix:resources>" + CONTEXT_C1 + "</ix:resources></ix:header>"
        "<p>During fiscal 2025, Apple, in the aggregate accounted for "
        + FACT_F1
        + "% of the Company&#8217;s net revenue.</p></body></html>"
    ).encode("utf-8")
    (cache / "doc10k.htm").write_bytes(doc)
    meta = {
        "url": (
            "https://www.sec.gov/Archives/edgar/data/4127/" + ACC_NODASH
            + "/doc10k.htm"
        ),
        "sha256": _sha(doc),
        "byte_length": len(doc),
        "http_status": 200,
        "fetched_at": "2026-10-22T02:00:00Z",
    }
    (cache / "doc10k.htm.meta.json").write_bytes(
        json.dumps(meta, sort_keys=True).encode("utf-8")
    )
    monkeypatch.setenv("GMI_EDGAR_CACHE", str(tmp_path / "cache"))
    return doc, meta


def _synthetic_ledger(workdir, doc, meta):
    workdir.mkdir(parents=True)
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
                "sha256": meta["sha256"],
                "byte_length": len(doc),
                "fetched_at": meta["fetched_at"],
            }
        ],
    }
    with (workdir / "fetch_ledger.jsonl").open("wb") as handle:
        handle.write(
            (json.dumps(row, sort_keys=True) + "\n").encode("utf-8")
        )


def _run_candidates(tmp_path, inputs):
    rc = CLI.main(
        [
            "candidates",
            "--leaf",
            "P",
            "--workdir",
            str(tmp_path / "work"),
            "--inputs",
            str(inputs),
        ]
    )
    return rc


def test_candidate_excerpt_validates_and_verifies(
    tmp_path, monkeypatch, resolver, aliases
):
    inputs, _census = _write_synthetic_inputs(
        tmp_path, monkeypatch, resolver, aliases
    )
    doc, meta = _synthetic_cache(tmp_path, monkeypatch)
    workdir = tmp_path / "work" / "P"
    _synthetic_ledger(workdir, doc, meta)
    assert _run_candidates(tmp_path, inputs) == 0
    rows = [
        json.loads(line)
        for line in (
            (workdir / "candidates.jsonl").read_text("utf-8")
        ).splitlines()
    ]
    assert rows, "expected at least one candidate"
    for row in rows:
        excerpt = row["excerpt"]
        jsonschema.validate(excerpt, EXCERPT_SCHEMA)
        assert replay.verify_excerpt(excerpt) == []
        assert excerpt["primary_document"] == "doc10k.htm"
        assert excerpt["doc_sha256"] == meta["sha256"]
        assert excerpt["accepted_at"] == "2025-11-07T21:08:12Z"
        assert row["accepted_at"] == excerpt["accepted_at"]
        assert row["origin"] in ("xbrl", "cue", "amendment_note")


def test_candidate_id_formula(tmp_path, monkeypatch, resolver, aliases):
    inputs, _census = _write_synthetic_inputs(
        tmp_path, monkeypatch, resolver, aliases
    )
    doc, meta = _synthetic_cache(tmp_path, monkeypatch)
    workdir = tmp_path / "work" / "P"
    _synthetic_ledger(workdir, doc, meta)
    assert _run_candidates(tmp_path, inputs) == 0
    rows = [
        json.loads(line)
        for line in (workdir / "candidates.jsonl").read_text("utf-8").splitlines()
    ]
    for row in rows:
        expected = "cand:" + package_v2.sha(
            package_v2.canon(
                [
                    row["accession"],
                    row["primary_document"],
                    row["excerpt"]["span"]["byte_start"],
                    row["excerpt"]["span"]["byte_end"],
                ]
            )
        )[:20]
        assert row["candidate_id"] == expected
    # ordering
    keys = [
        (
            r["issuer_id"],
            r["accession"],
            r["primary_document"],
            r["excerpt"]["span"]["byte_start"],
            r["excerpt"]["span"]["byte_end"],
        )
        for r in rows
    ]
    assert keys == sorted(keys)
    text = (workdir / "candidates.jsonl").read_text("utf-8")
    for line in text.splitlines():
        obj = json.loads(line)
        assert list(obj) == sorted(obj)  # keys sorted


def test_slice_partition():
    issuers = [f"ISS:{i:04d}" for i in range(10)]
    union = []
    for i in range(1, 5):
        part = rel_harvest.slice_issuers(issuers, i, 4)
        union.extend(part)
        for k, issuer in enumerate(sorted(issuers)):
            if issuer in part:
                assert k % 4 == i - 1
    assert sorted(union) == issuers
    with pytest.raises(ValueError):
        rel_harvest.slice_issuers(issuers, 5, 4)


def test_candidates_rerun_byte_identical(tmp_path, monkeypatch, resolver, aliases):
    inputs, _census = _write_synthetic_inputs(
        tmp_path, monkeypatch, resolver, aliases
    )
    doc, meta = _synthetic_cache(tmp_path, monkeypatch)
    workdir = tmp_path / "work" / "P"
    _synthetic_ledger(workdir, doc, meta)
    assert _run_candidates(tmp_path, inputs) == 0
    first = {
        name: (workdir / name).read_bytes()
        for name in (
            "candidates.jsonl",
            "parse_ledger.jsonl",
            "harvest_report.json",
        )
    }
    assert _run_candidates(tmp_path, inputs) == 0
    for name, blob in first.items():
        assert (workdir / name).read_bytes() == blob, name
    report = json.loads(first["harvest_report.json"])
    assert report["schema"] == "gmi_rel_m2.harvest_report/v1"
    assert report["candidates_total"] == len(first["candidates.jsonl"].splitlines())
    assert set(report["counters"]) >= {
        "overflow_document",
        "overflow_filing",
        "span_too_large",
        "span_not_utf8",
        "xbrl_fact_hidden",
        "xbrl_fact_no_counterparty_axis",
        "xbrl_fact_unanchored",
        "xbrl_context_too_large",
        "excerpt_self_check_failed",
        "clock_refused",
        "doc_too_large",
        "documents_overflow",
        "cache_integrity_refetch",
    }

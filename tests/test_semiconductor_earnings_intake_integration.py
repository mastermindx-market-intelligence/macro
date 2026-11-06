"""T05a ∘ T05b — carrier-level integration of the Semiconductor B witnesses.

Operation gmi-semiconductors-fable-ceo-e2e-20260923-chairman-001 (carrier #7870).

The PRODUCTION TSMC and onsemi identities and profiles (no test seams, no
synthetic issuers) run through the intake's discovery
(:func:`scripts.refresh_event_workspaces.discover_new_homebuilder_revisions`)
on the REAL 2026 EDGAR submission rows and filing manifests of both issuers
— public SEC metadata reproduced byte-faithfully (accession numbers, filing
and report dates, acceptance clocks, primary documents, ``items`` strings,
and every SGML ``<TYPE>``/``<FILENAME>``/``<DESCRIPTION>`` of the text
documents) — while every exhibit BODY is the synthetic real-structure
look-alike from ``tests/test_semiconductor_earnings_witnesses.py`` (invented
figures; no real Exhibit 99.1 body is committed, per the Macro private-data
gate).

What this pins that neither unit suite can:
  * TSMC's real results 6-K manifest describes its EX-99.1 only as
    ``EX-99.1`` — admission rests on the ``a<q>q<yy>e…`` FILENAME convention
    (``a2q26e_withguidancexfinal.htm``), and the three real quarter-end-dated
    confounders in the same window (the June monthly-revenue 6-K, the
    month-end 6-K, and the consolidated financial-statements 6-K whose
    EX-99.1 is ``a2026q2consolidatedreport-.htm``) are each refused.
  * onsemi's real results 8-K carries ``items`` ``2.02,9.01`` and a BARE
    ``EX-99`` exhibit described ``EXHIBIT 99.1``; the two Item 8.01 8-Ks of
    the same month, each with a real ``EX-99.1``, are never admitted.
  * The admitted revision's payload carries the witness facts and guidance
    the closed grammars bind — the exact values the T05a suite certifies —
    so an empty economics panel cannot come from an intake seam.
"""
from __future__ import annotations

import json
import re
from datetime import date

import pytest

import scripts.refresh_event_workspaces as refresh_mod
from engine.company_intelligence.guidance_history import assess_management_sequence
from engine.company_intelligence.issuer_profiles import ON_CIK, TSM_CIK, on_profile, tsm_profile
from tests.test_semiconductor_earnings_witnesses import ON_SYNTHETIC_EXHIBIT, TSM_SYNTHETIC_EXHIBIT

# ── real EDGAR metadata (public; byte-faithful to data.sec.gov / Archives) ──

TSM_RESULTS_ACCESSION = "0001046179-26-000451"       # Q2-2026 results 6-K, filed 2026-07-16
TSM_FS_ACCESSION = "0001046179-26-000541"            # Q2-2026 consolidated financial statements 6-K
TSM_JUNE_REVENUE_ACCESSION = "0001046179-26-000447"  # June-2026 monthly revenue 6-K (quarter-end reportDate)
TSM_MONTHEND_ACCESSION = "0001046179-26-000459"      # month-end 6-K (quarter-end reportDate)

# real results 6-Ks filed BEFORE the TSMC identity's attested listing (valid_from 2026-04-16)
TSM_PRE_IDENTITY_ACCESSIONS = ("0001046179-26-000008", "0001046179-25-000035")
TSM_PRE_IDENTITY_ROWS = [
    {"form": "6-K", "accessionNumber": "0001046179-26-000008", "filingDate": "2026-01-15", "reportDate": "2025-12-31",
     "acceptanceDateTime": "2026-01-15T11:58:24.000Z", "primaryDocument": "tsm-20260115x6k.htm", "items": ""},  # Q4-2025 results
    {"form": "6-K", "accessionNumber": "0001046179-25-000035", "filingDate": "2025-04-17", "reportDate": "2025-03-31",
     "acceptanceDateTime": "2025-04-17T11:00:49.000Z", "primaryDocument": "tsm-20250417x6k.htm", "items": ""},  # Q1-2025 results
]

TSM_ROWS = [  # every 6-K TSMC filed 2026-07-01 .. 2026-08-31, newest first, as data.sec.gov lists them
    {"form": "6-K", "accessionNumber": "0001046179-26-000545", "filingDate": "2026-08-25", "reportDate": "2026-07-31",
     "acceptanceDateTime": "2026-08-25T10:17:27.000Z", "primaryDocument": "tsm-monthend6kx20260825.htm", "items": ""},
    {"form": "6-K", "accessionNumber": TSM_FS_ACCESSION, "filingDate": "2026-08-14", "reportDate": "2026-06-30",
     "acceptanceDateTime": "2026-08-14T10:02:33.000Z", "primaryDocument": "tsm-fsx20260814x6k.htm", "items": ""},
    {"form": "6-K", "accessionNumber": "0001046179-26-000539", "filingDate": "2026-08-11", "reportDate": "2026-08-11",
     "acceptanceDateTime": "2026-08-11T12:25:45.000Z", "primaryDocument": "sonysemiconductorsolutions.htm", "items": ""},
    {"form": "6-K", "accessionNumber": "0001046179-26-000536", "filingDate": "2026-08-11", "reportDate": "2026-08-11",
     "acceptanceDateTime": "2026-08-11T11:45:48.000Z", "primaryDocument": "tsm-boardx20260811.htm", "items": ""},
    {"form": "6-K", "accessionNumber": "0001046179-26-000471", "filingDate": "2026-08-10", "reportDate": "2026-07-31",
     "acceptanceDateTime": "2026-08-10T10:28:44.000Z", "primaryDocument": "tsm-revenue20260810.htm", "items": ""},
    {"form": "6-K", "accessionNumber": TSM_MONTHEND_ACCESSION, "filingDate": "2026-07-24", "reportDate": "2026-06-30",
     "acceptanceDateTime": "2026-07-24T10:33:23.000Z", "primaryDocument": "tsm-monthend6kx20260724.htm", "items": ""},
    {"form": "6-K", "accessionNumber": TSM_RESULTS_ACCESSION, "filingDate": "2026-07-16", "reportDate": "2026-06-30",
     "acceptanceDateTime": "2026-07-16T11:45:43.000Z", "primaryDocument": "tsm-20260716x6k.htm", "items": ""},
    {"form": "6-K", "accessionNumber": TSM_JUNE_REVENUE_ACCESSION, "filingDate": "2026-07-13", "reportDate": "2026-06-30",
     "acceptanceDateTime": "2026-07-13T11:01:35.000Z", "primaryDocument": "tsm-revenue20260713.htm", "items": ""},
    {"form": "6-K", "accessionNumber": "0001046179-26-000381", "filingDate": "2026-07-02", "reportDate": "2026-07-02",
     "acceptanceDateTime": "2026-07-02T11:10:57.000Z", "primaryDocument": "a20260702changeofaztreasur.htm", "items": ""},
]

# text documents of each filing's -index-headers.html (GRAPHIC/XBRL rows omitted; they never matter)
TSM_MANIFESTS = {
    # the real Q1-2025 results manifest: stubbed so the pre-identity test OWNS the regression it cites —
    # on the parent commit discovery fetched this manifest and its exhibit, then the builder raised
    # "TSM maps to no issuer at 2025-04-17"; now the row never reaches a fetch.
    "0001046179-25-000035": [("6-K", "tsm-20250417x6k.htm", "6-K"),
                             ("EX-99.1", "a1q25e_withguidancexfinal.htm", "EX-99.1"),
                             ("EX-99.2", "a1q25presentatione.htm", "EX-99.2")],
    TSM_RESULTS_ACCESSION: [("6-K", "tsm-20260716x6k.htm", "6-K"),
                            ("EX-99.1", "a2q26e_withguidancexfinal.htm", "EX-99.1"),
                            ("EX-99.2", "a2q26presentatione.htm", "EX-99.2")],
    TSM_FS_ACCESSION: [("6-K", "tsm-fsx20260814x6k.htm", "6-K"),
                       ("EX-99.1", "a2026q2consolidatedreport-.htm", "EX-99.1")],
    TSM_JUNE_REVENUE_ACCESSION: [("6-K", "tsm-revenue20260713.htm", "6-K")],
    TSM_MONTHEND_ACCESSION: [("6-K", "tsm-monthend6kx20260724.htm", "6-K")],
}

ON_RESULTS_ACCESSION = "0001140361-26-018868"  # Q1-2026 results 8-K (Items 2.02, 9.01), filed 2026-05-04

ON_ROWS = [  # every 8-K onsemi filed 2026-05-01 .. 2026-05-31, newest first
    {"form": "8-K", "accessionNumber": "0001140361-26-021907", "filingDate": "2026-05-18", "reportDate": "2026-05-14",
     "acceptanceDateTime": "2026-05-18T20:30:46.000Z", "primaryDocument": "ef20074056_8k.htm", "items": "5.02,5.07"},
    {"form": "8-K", "accessionNumber": "0001140361-26-020642", "filingDate": "2026-05-12", "reportDate": "2026-05-06",
     "acceptanceDateTime": "2026-05-11T22:37:57.000Z", "primaryDocument": "ef20072923_8k.htm", "items": "1.01,2.03,3.02,8.01,9.01"},
    {"form": "8-K", "accessionNumber": "0001140361-26-019416", "filingDate": "2026-05-07", "reportDate": "2026-05-06",
     "acceptanceDateTime": "2026-05-07T10:31:04.000Z", "primaryDocument": "ef20072662_8k.htm", "items": "8.01,9.01"},
    {"form": "8-K", "accessionNumber": "0001140361-26-019207", "filingDate": "2026-05-06", "reportDate": "2026-05-06",
     "acceptanceDateTime": "2026-05-06T11:31:28.000Z", "primaryDocument": "ef20066746_8k.htm", "items": "8.01,9.01"},
    {"form": "8-K", "accessionNumber": ON_RESULTS_ACCESSION, "filingDate": "2026-05-04", "reportDate": "2026-05-04",
     "acceptanceDateTime": "2026-05-04T20:10:34.000Z", "primaryDocument": "ef20072220_8k.htm", "items": "2.02,9.01"},
]

# real Item 2.02 8-K filed BEFORE the onsemi identity's attested listing (valid_from 2026-05-04)
ON_PRE_IDENTITY_ACCESSION = "0001140361-26-004405"
ON_PRE_IDENTITY_ROW = {
    "form": "8-K", "accessionNumber": ON_PRE_IDENTITY_ACCESSION, "filingDate": "2026-02-09", "reportDate": "2026-02-09",
    "acceptanceDateTime": "2026-02-09T21:21:26.000Z", "primaryDocument": "ef20065070_8k.htm", "items": "2.02,9.01",
}

ON_MANIFESTS = {
    ON_RESULTS_ACCESSION: [("8-K", "ef20072220_8k.htm", "8-K"), ("EX-99.1", "ef20072220_ex99-1.htm", "EXHIBIT 99.1")],
    "0001140361-26-021907": [("8-K", "ef20074056_8k.htm", "8-K")],
    "0001140361-26-019416": [("8-K", "ef20072662_8k.htm", "8-K"), ("EX-99.1", "ef20072662_ex99-1.htm", "EXHIBIT 99.1")],
    "0001140361-26-019207": [("8-K", "ef20066746_8k.htm", "8-K"), ("EX-99.1", "ef20066746_ex99-1.htm", "EXHIBIT 99.1")],
}

# onsemi's Q2-2026 results 8-K names its exhibit with the BARE type (real manifest row)
ON_Q2_BARE_EX99_MANIFEST = [("8-K", "ef20079200_8k.htm", "8-K"), ("EX-99", "ef20079200_ex99-1.htm", "EXHIBIT 99.1")]

ON_Q2_RESULTS_ACCESSION = "0001140361-26-030989"  # Q2-2026 results 8-K (Items 2.02, 9.01), filed 2026-08-03
ON_Q2_ROWS = [  # every 8-K onsemi filed 2026-08-01 .. 2026-08-31
    {"form": "8-K", "accessionNumber": "0001140361-26-032594", "filingDate": "2026-08-13", "reportDate": "2026-08-12",
     "acceptanceDateTime": "2026-08-13T10:01:02.000Z", "primaryDocument": "ef20080111_8k.htm", "items": "8.01"},
    {"form": "8-K", "accessionNumber": ON_Q2_RESULTS_ACCESSION, "filingDate": "2026-08-03", "reportDate": "2026-08-03",
     "acceptanceDateTime": "2026-08-03T20:54:23.000Z", "primaryDocument": "ef20079200_8k.htm", "items": "2.02,9.01"},
]
ON_Q2_MANIFESTS = {ON_Q2_RESULTS_ACCESSION: ON_Q2_BARE_EX99_MANIFEST}

# Q2-shaped look-alike of the synthetic exhibit: labels/dates rolled one quarter, and — as in the real
# Q2-2026 release — a free-cash-flow table whose "Quarters Ended" header names four quarter ends oldest-first
# BEFORE the summary table, so first-match dating would read October 3, 2025.
ON_Q2_SYNTHETIC_EXHIBIT = (
    "<table><tr><td>FREE CASH FLOW</td></tr>"
    "<tr><td>Quarters Ended October 3, 2025 December 31, 2025 April 3, 2026 July 3, 2026</td></tr></table>"
    + ON_SYNTHETIC_EXHIBIT
    .replace("Q1 2026", "Q2 2026").replace("Q4 2025", "Q1 2026")
    .replace("April 3, 2026", "July 3, 2026").replace("January 2, 2026", "April 3, 2026").replace("March 28, 2025", "June 27, 2025")
    .replace("projected second quarter of 2026", "projected third quarter of 2026")
)

CONFOUNDER_BODY = "<html><body><p>Synthetic non-results document; every figure here is invented.</p></body></html>"

_MANIFEST_URL_RE = re.compile(r"/(\d{10}-\d{2}-\d{6})-index-headers\.html$")


def _resolved_accessions(fetched: list[str]) -> set[str]:
    """Exactly the accessions whose filing manifest was fetched (reached the discriminator)."""
    return {m.group(1) for url in fetched for m in [_MANIFEST_URL_RE.search(url)] if m}


def _index_headers(docs) -> str:
    body = "".join(
        f"&lt;DOCUMENT&gt;\n&lt;TYPE&gt;{kind}\n&lt;FILENAME&gt;{name}\n&lt;DESCRIPTION&gt;{desc}\n&lt;/DOCUMENT&gt;\n"
        for kind, name, desc in docs
    )
    return f"<HTML><BODY><PRE>{body}</PRE></BODY></HTML>"


def _discover(monkeypatch, *, ticker: str, cik: str, rows, manifests, bodies):
    """Production identity + profile (resolved by the intake itself); only the network is replaced."""
    cols = ("accessionNumber", "filingDate", "acceptanceDateTime", "reportDate", "form", "primaryDocument", "items")
    submissions = {"cik": cik, "filings": {"recent": {c: [r[c] for r in rows] for c in cols}}}
    cik_int = int(cik)
    fetched: list[str] = []

    def http_get(url: str) -> tuple[int, bytes]:
        fetched.append(url)
        if url == f"https://data.sec.gov/submissions/CIK{cik}.json":
            return 200, json.dumps(submissions).encode("utf-8")
        for acc, docs in manifests.items():
            base = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc.replace('-', '')}"
            if url == f"{base}/{acc}-index-headers.html":
                return 200, _index_headers(docs).encode("utf-8")
            for kind, name, _desc in docs:
                if url == f"{base}/{name}":
                    return 200, bodies.get(acc, CONFOUNDER_BODY).encode("utf-8")
        return 404, b""

    def fetch_index(_base: str) -> dict:
        return {"schema": "mastermind.tx-index/v1", "symbols": {}, "revisions": {}, "dates": {},
                "body_count": 0, "symbol_count": 0, "generated_at": "2026-01-01T00:00:00Z"}

    def fetch_body(_base: str, _ref):  # pragma: no cover
        raise AssertionError("no transcript may be fetched")

    monkeypatch.setattr(refresh_mod.time, "sleep", lambda _s: None)
    revisions = refresh_mod.discover_new_homebuilder_revisions(
        ticker, http_get=http_get, fetch_index=fetch_index, fetch_body_fn=fetch_body,
        chain_state_loader=lambda _event_id: [], today=date(2026, 9, 24),
    )
    return revisions, fetched


def _by_id(facts):
    return {fact["fact_id"]: fact for fact in facts}


# ── TSMC ──

def test_tsm_production_identity_admits_only_the_real_results_six_k(monkeypatch, capsys) -> None:
    revisions, fetched = _discover(
        monkeypatch, ticker="TSM", cik=TSM_CIK, rows=TSM_ROWS, manifests=TSM_MANIFESTS,
        bodies={TSM_RESULTS_ACCESSION: TSM_SYNTHETIC_EXHIBIT},
    )
    assert [payload["sources"][0]["filing_key"]["accession"] for _eid, payload in revisions] == [TSM_RESULTS_ACCESSION]
    event_id, payload = revisions[0]
    assert event_id == payload["event_id"] and "2026q2" in event_id
    assert payload["fiscal_period"]["year"] == 2026 and payload["fiscal_period"]["quarter"] == 2
    assert payload["sources"][0]["form"] == "6-K"
    assert payload["sources"][0]["url"].endswith("/a2q26e_withguidancexfinal.htm")
    # the three quarter-end-dated confounders were each looked at and refused, never admitted
    out = capsys.readouterr().out
    assert TSM_JUNE_REVENUE_ACCESSION in out and TSM_MONTHEND_ACCESSION in out and TSM_FS_ACCESSION in out
    assert "6-K manifest refused by the results discriminator" in out
    for acc in (TSM_JUNE_REVENUE_ACCESSION, TSM_MONTHEND_ACCESSION, TSM_FS_ACCESSION):
        assert acc not in json.dumps(payload)
    # exactly the four quarter-end-dated rows reached the manifest stage; the five others were never resolved
    assert _resolved_accessions(fetched) == {
        TSM_RESULTS_ACCESSION, TSM_JUNE_REVENUE_ACCESSION, TSM_MONTHEND_ACCESSION, TSM_FS_ACCESSION,
    }


def test_tsm_admitted_payload_carries_the_closed_grammar_facts_and_guidance(monkeypatch) -> None:
    revisions, _ = _discover(
        monkeypatch, ticker="TSM", cik=TSM_CIK, rows=TSM_ROWS, manifests=TSM_MANIFESTS,
        bodies={TSM_RESULTS_ACCESSION: TSM_SYNTHETIC_EXHIBIT},
    )
    (_eid, payload), = revisions
    facts = _by_id(payload["facts"])
    usd, twd = facts["fact_revenue_usd"], facts["fact_revenue_twd"]
    assert (usd["value"], usd["unit"], usd["period"]) == (12.34, "usd_billions", "2026-06-30")
    assert twd["typed_absence"]["reason"] == "missing_units"
    (item,) = payload["guidance"]
    assert (item["low"], item["high"], item["unit"], item["horizon"]) == (13.0, 13.5, "usd_billions", "2026Q3")
    assert item["fx_assumption"] == "1 US dollar to 32 NT dollars"
    assert payload["authority"] and all(v is False for v in payload["prophet_flags"].values())
    # the payload's profile is the production one, not a seam
    assert tsm_profile().ticker == "TSM"


# ── onsemi ──

def test_on_production_identity_admits_only_the_item_202_eight_k(monkeypatch) -> None:
    revisions, fetched = _discover(
        monkeypatch, ticker="ON", cik=ON_CIK, rows=ON_ROWS, manifests=ON_MANIFESTS,
        bodies={ON_RESULTS_ACCESSION: ON_SYNTHETIC_EXHIBIT},
    )
    assert [payload["sources"][0]["filing_key"]["accession"] for _eid, payload in revisions] == [ON_RESULTS_ACCESSION]
    event_id, payload = revisions[0]
    assert "2026q1" in event_id
    assert payload["sources"][0]["form"] == "8-K"
    assert payload["sources"][0]["url"].endswith("/ef20072220_ex99-1.htm")
    # the Item 8.01 / 5.02 / 1.01 8-Ks carry real EX-99.1 exhibits but are never candidates: only the 2.02 row was resolved
    assert _resolved_accessions(fetched) == {ON_RESULTS_ACCESSION}


def test_on_admitted_payload_carries_the_label_bound_revenue_and_gaap_outlook(monkeypatch) -> None:
    revisions, _ = _discover(
        monkeypatch, ticker="ON", cik=ON_CIK, rows=ON_ROWS, manifests=ON_MANIFESTS,
        bodies={ON_RESULTS_ACCESSION: ON_SYNTHETIC_EXHIBIT},
    )
    (_eid, payload), = revisions
    # onsemi's Q1-2026 ended April 3, 2026 (52/53-week calendar); the event carries the issuer's stated end
    assert payload["fiscal_period"]["calendar_end"] == "2026-04-03"
    (rev,) = [f for f in payload["facts"] if f["fact_id"] == "fact_revenue"]
    assert (rev["value"], rev["unit"], rev["period"]) == (1234.5, "usd_millions", "2026-04-03")
    (item,) = payload["guidance"]
    assert (item["low"], item["high"], item["unit"], item["horizon"]) == (1400.0, 1500.0, "usd_millions", "2026Q2")
    assert item["fx_assumption"] is None and item["basis"] == "reported_gaap"
    assert on_profile().ticker == "ON"


def test_on_bare_ex99_manifest_of_the_real_q2_results_eight_k_is_admitted() -> None:
    """onsemi's Q2-2026 8-K types its release ``EX-99`` (no ``.1``); the
    pre-existing filename-hint rescue selects it as the sole text exhibit."""
    entries = refresh_mod._parse_sgml_manifest_entries(_index_headers(ON_Q2_BARE_EX99_MANIFEST))
    assert [e["type"] for e in entries] == ["8-K", "EX-99"]
    selected = refresh_mod._select_exhibit_99_1(refresh_mod._parse_sgml_manifest(_index_headers(ON_Q2_BARE_EX99_MANIFEST)))
    assert selected is not None and "ef20079200_ex99-1.htm" in str(selected)


# ── filings before the attested identity ──

def test_tsm_results_filed_before_the_attested_listing_are_skipped_never_built(monkeypatch, capsys) -> None:
    """First-ever discovery scans the prior fiscal year too; the live-EDGAR proof run
    reached TSMC's real Q1-2025 results 6-K and the workspace builder raised
    ``maps to no issuer at 2025-04-17``. Such rows are skipped on the raw row,
    before any per-accession fetch, and the 2026 results are still admitted."""
    revisions, fetched = _discover(
        monkeypatch, ticker="TSM", cik=TSM_CIK, rows=TSM_ROWS + TSM_PRE_IDENTITY_ROWS, manifests=TSM_MANIFESTS,
        bodies={TSM_RESULTS_ACCESSION: TSM_SYNTHETIC_EXHIBIT,
                "0001046179-25-000035": TSM_SYNTHETIC_EXHIBIT.replace("second quarter ended June 30, 2026", "first quarter ended March 31, 2025")},
    )
    assert [payload["sources"][0]["filing_key"]["accession"] for _eid, payload in revisions] == [TSM_RESULTS_ACCESSION]
    out = capsys.readouterr().out
    for acc in TSM_PRE_IDENTITY_ACCESSIONS:
        assert f"accession {acc} filed" in out and "precedes the issuer identity's attested listing" in out
        assert acc not in json.dumps([p for _e, p in revisions])
    assert _resolved_accessions(fetched) == {
        TSM_RESULTS_ACCESSION, TSM_JUNE_REVENUE_ACCESSION, TSM_MONTHEND_ACCESSION, TSM_FS_ACCESSION,
    }


def test_on_item_202_eight_k_filed_before_the_attested_listing_is_skipped_never_built(monkeypatch, capsys) -> None:
    revisions, fetched = _discover(
        monkeypatch, ticker="ON", cik=ON_CIK, rows=ON_ROWS + [ON_PRE_IDENTITY_ROW], manifests=ON_MANIFESTS,
        bodies={ON_RESULTS_ACCESSION: ON_SYNTHETIC_EXHIBIT},
    )
    assert [payload["sources"][0]["filing_key"]["accession"] for _eid, payload in revisions] == [ON_RESULTS_ACCESSION]
    out = capsys.readouterr().out
    assert f"accession {ON_PRE_IDENTITY_ACCESSION} filed 2026-02-09 precedes the issuer identity's attested listing" in out
    assert _resolved_accessions(fetched) == {ON_RESULTS_ACCESSION}


def test_on_real_q2_eight_k_is_admitted_on_the_unique_in_tolerance_stated_date(monkeypatch, capsys) -> None:
    """Live-EDGAR proof finding: onsemi's Q2-2026 exhibit names October 3, 2025 first under a
    "Quarters Ended" header (five trailing quarters, oldest first), so the first-match rule
    refused the real filing with drift=270d. The 52/53-week path now adopts the unique named
    date within tolerance (July 3, 2026) and the closed grammar binds against it."""
    revisions, fetched = _discover(
        monkeypatch, ticker="ON", cik=ON_CIK, rows=ON_Q2_ROWS, manifests=ON_Q2_MANIFESTS,
        bodies={ON_Q2_RESULTS_ACCESSION: ON_Q2_SYNTHETIC_EXHIBIT},
    )
    assert [payload["sources"][0]["filing_key"]["accession"] for _eid, payload in revisions] == [ON_Q2_RESULTS_ACCESSION]
    event_id, payload = revisions[0]
    assert "2026q2" in event_id
    assert payload["fiscal_period"] == {"year": 2026, "quarter": 2, "calendar_end": "2026-07-03"}
    assert payload["sources"][0]["url"].endswith("/ef20079200_ex99-1.htm")
    (rev,) = [f for f in payload["facts"] if f["fact_id"] == "fact_revenue"]
    assert (rev["value"], rev["unit"], rev["period"]) == (1234.5, "usd_millions", "2026-07-03")
    (item,) = payload["guidance"]
    assert (item["low"], item["high"], item["horizon"]) == (1400.0, 1500.0, "2026Q3")
    assert _resolved_accessions(fetched) == {ON_Q2_RESULTS_ACCESSION}
    assert "stated period end 2026-07-03 in place of the derived calendar quarter end 2026-06-30" in capsys.readouterr().out


# ── cross-release management sequences: prior outlook from one real filing, actual + new outlook from the next ──

TSM_Q1_RESULTS_ACCESSION = "0001046179-26-000199"  # Q1-2026 results 6-K, filed 2026-04-16 (the identity's valid_from day)
TSM_Q1_ROW = {"form": "6-K", "accessionNumber": TSM_Q1_RESULTS_ACCESSION, "filingDate": "2026-04-16", "reportDate": "2026-03-31",
              "acceptanceDateTime": "2026-04-16T12:00:18.000Z", "primaryDocument": "tsm-20260416x6k.htm", "items": ""}
TSM_Q1_MANIFEST = {TSM_Q1_RESULTS_ACCESSION: [("6-K", "tsm-20260416x6k.htm", "6-K"),
                                              ("EX-99.1", "a1q26e_withguidancexfinal.htm", "EX-99.1"),
                                              ("EX-99.2", "a1q26presentatione.htm", "EX-99.2")]}
TSM_Q1_SYNTHETIC_EXHIBIT = (
    TSM_SYNTHETIC_EXHIBIT
    .replace("second quarter ended June 30, 2026", "first quarter ended March 31, 2026")
    .replace("In US dollars, second quarter revenue", "In US dollars, first quarter revenue")
    .replace("for third quarter 2026 to be as follows", "for second quarter 2026 to be as follows")
)


def _composer_sequence(revisions, fact_id: str):
    """Mirror _build_economics: prior = the earlier release's outlook for the reported quarter; actual = the
    later release's present fact (fiscal_period from the workspace block); new outlook = its later-horizon item."""
    ordered = sorted(revisions, key=lambda r: (r[1]["fiscal_period"]["year"], r[1]["fiscal_period"]["quarter"]))
    (_e1, q_prior), (_e2, q_actual) = ordered
    label = f"{q_actual['fiscal_period']['year']}Q{q_actual['fiscal_period']['quarter']}"
    prior = next(i for i in q_prior["guidance"] if i["horizon"] == label)
    fact = next(f for f in q_actual["facts"] if f["fact_id"] == fact_id and "typed_absence" not in f)
    actual = {"metric": fact["metric"], "value": fact["value"], "unit": fact["unit"], "fiscal_period": label,
              "source_span": {"event_id": q_actual["event_id"]}}
    for optional in ("basis", "currency", "perimeter", "definition"):
        if optional in fact:
            actual[optional] = fact[optional]
    new_outlook = next(i for i in q_actual["guidance"] if i["horizon"] > label)
    return assess_management_sequence(prior, actual, new_outlook)


def test_tsm_two_real_filings_yield_a_comparable_sequence_with_the_fx_limitation(monkeypatch) -> None:
    revisions, _ = _discover(
        monkeypatch, ticker="TSM", cik=TSM_CIK, rows=TSM_ROWS + [TSM_Q1_ROW], manifests={**TSM_MANIFESTS, **TSM_Q1_MANIFEST},
        bodies={TSM_RESULTS_ACCESSION: TSM_SYNTHETIC_EXHIBIT, TSM_Q1_RESULTS_ACCESSION: TSM_Q1_SYNTHETIC_EXHIBIT},
    )
    assert sorted(e for e, _p in revisions) == ["evt_cik0001046179_2026q1_results", "evt_cik0001046179_2026q2_results"]
    result = _composer_sequence(revisions, "fact_revenue_usd")
    assert result["comparisons"]["prior_vs_actual"] == {"status": "comparable", "reason": None, "position": "below_range"}
    # Pinned exactly: the FX residual is present because TSMC guides at a stated
    # NT$ rate; the two definition tokens are present because neither the fact
    # nor the guidance qualifies perimeter/definition; nothing else may appear.
    assert result["limitations"] == [
        "no_external_consensus",
        "definition_unqualified:perimeter",
        "definition_unqualified:definition",
        "fx_assumption_unreconciled",
    ]


def test_on_two_real_filings_yield_a_comparable_sequence_across_caption_and_cell_units(monkeypatch) -> None:
    """The actual's unit comes from the Q2 summary caption ('in millions'); the prior's from the Q1 outlook
    cell word ('million') — two filings, two derivations, one closed token."""
    revisions, _ = _discover(
        monkeypatch, ticker="ON", cik=ON_CIK, rows=ON_ROWS + ON_Q2_ROWS, manifests={**ON_MANIFESTS, **ON_Q2_MANIFESTS},
        bodies={ON_RESULTS_ACCESSION: ON_SYNTHETIC_EXHIBIT, ON_Q2_RESULTS_ACCESSION: ON_Q2_SYNTHETIC_EXHIBIT},
    )
    assert sorted(e for e, _p in revisions) == ["evt_cik0001097864_2026q1_results", "evt_cik0001097864_2026q2_results"]
    result = _composer_sequence(revisions, "fact_revenue")
    assert result["comparisons"]["prior_vs_actual"] == {"status": "comparable", "reason": None, "position": "below_range"}
    # Pinned exactly: onsemi states no FX assumption, so no FX residual.
    assert result["limitations"] == [
        "no_external_consensus",
        "definition_unqualified:perimeter",
        "definition_unqualified:definition",
    ]


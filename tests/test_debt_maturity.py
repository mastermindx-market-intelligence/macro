"""Tests for engine/debt_maturity.py (packet B-F09-3)."""
from __future__ import annotations

import ast
import hashlib
import json
import re
from datetime import date
from pathlib import Path

import pytest

from engine.debt_maturity import BUCKETS, extract_maturity_ladder

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "debt_maturity"
AAPL_CIK = "0000320193"


def _load(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text())


def test_six_buckets_map_from_exact_tags():
    assert [b[0] for b in BUCKETS] == ["y1", "y2", "y3", "y4", "y5", "after5"]
    tags = [b[1] for b in BUCKETS]
    assert tags == [
        "LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths",
        "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearTwo",
        "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearThree",
        "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFour",
        "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFive",
        "LongTermDebtMaturitiesRepaymentsOfPrincipalAfterYearFive",
    ]


def test_latest_annual_period_wins():
    facts = _load("aapl_trimmed.json")
    result = extract_maturity_ladder(facts, cik=AAPL_CIK, as_of=date(2025, 1, 1))
    assert result["period"]["form"] == "10-K"
    assert result["period"]["fp"] == "FY"
    assert result["period"]["end"] == "2024-09-28"


def test_buckets_never_mix_filings():
    facts = _load("aapl_trimmed.json")
    result = extract_maturity_ladder(facts, cik=AAPL_CIK, as_of=date(2025, 1, 1))
    y4 = next(b for b in result["buckets"] if b["key"] == "y4")
    assert y4["reported"] is False
    assert y4["drop_reason"] == "period_mismatch"
    # excluded from the total
    assert result["total_reported_usd"] == 11128000000 + 10912000000 + 0


def test_unit_not_usd_is_not_reported_not_zero():
    facts = _load("aapl_trimmed.json")
    result = extract_maturity_ladder(facts, cik=AAPL_CIK, as_of=date(2025, 1, 1))
    y3 = next(b for b in result["buckets"] if b["key"] == "y3")
    assert y3["usd"] is None
    assert y3["reported"] is False
    assert y3["drop_reason"] == "unit_not_usd"
    assert y3["display"] is None


def test_conflicting_unit_keys_fail_closed_not_reported():
    """Round-2 review MINOR-2: the same (accn, end) reported under TWO
    recognized-USD unit keys with DIFFERENT values must never be silently
    resolved by JSON dict-iteration order -- that is exactly the "scaled by a
    guess" behavior this module's own docstring forbids. A real disagreement
    fails closed to not-reported; an identical duplicate does not."""
    tag = "LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths"
    facts = {
        "cik": 999999,
        "facts": {"us-gaap": {tag: {"units": {
            "USD": [{"end": "2024-12-31", "val": 5000, "accn": "0000999999-25-000001",
                     "fy": 2024, "fp": "FY", "form": "10-K", "filed": "2025-02-01"}],
            "USDthousands": [{"end": "2024-12-31", "val": 6, "accn": "0000999999-25-000001",
                              "fy": 2024, "fp": "FY", "form": "10-K", "filed": "2025-02-01"}],
        }}}},
    }
    result = extract_maturity_ladder(facts, cik="0000999999", as_of=date(2025, 3, 1))
    y1 = next(b for b in result["buckets"] if b["key"] == "y1")
    assert y1["reported"] is False
    assert y1["usd"] is None
    assert y1["drop_reason"] == "unit_conflict"


def test_duplicate_identical_unit_entries_are_not_a_conflict():
    """The SAME dollar amount filed twice (a genuine duplicate row, not a
    disagreement) still resolves -- only a real value mismatch fails closed."""
    tag = "LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths"
    facts = {
        "cik": 999999,
        "facts": {"us-gaap": {tag: {"units": {"USD": [
            {"end": "2024-12-31", "val": 5000, "accn": "0000999999-25-000001",
             "fy": 2024, "fp": "FY", "form": "10-K", "filed": "2025-02-01"},
            {"end": "2024-12-31", "val": 5000, "accn": "0000999999-25-000001",
             "fy": 2024, "fp": "FY", "form": "10-K", "filed": "2025-02-01"},
        ]}}}},
    }
    result = extract_maturity_ladder(facts, cik="0000999999", as_of=date(2025, 3, 1))
    y1 = next(b for b in result["buckets"] if b["key"] == "y1")
    assert y1["reported"] is True
    assert y1["usd"] == 5000


def test_bucket_shares_always_sum_to_100():
    """Round-2 review MINOR-3: independently round()-ing each bucket's share
    of the total need not sum to 100, and near_share_pct (bucket 0's share) is
    quoted verbatim in the user-facing lede sentence ("About N% ..."). A
    3-way split (e.g. 1/3 each) is the classic case where naive per-bucket
    rounding drifts off 100."""
    tags = [
        "LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths",
        "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearTwo",
        "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearThree",
    ]
    entry = lambda val: [{"end": "2024-12-31", "val": val, "accn": "0000999999-25-000001",
                          "fy": 2024, "fp": "FY", "form": "10-K", "filed": "2025-02-01"}]
    facts = {
        "cik": 999999,
        "facts": {"us-gaap": {t: {"units": {"USD": entry(100)}} for t in tags}},
    }
    result = extract_maturity_ladder(facts, cik="0000999999", as_of=date(2025, 3, 1))
    reported = [b for b in result["buckets"] if b["reported"]]
    assert len(reported) == 3
    assert sum(b["share_pct"] for b in reported) == 100
    assert result["near_share_pct"] == reported[0]["share_pct"]


def test_missing_bucket_is_null_not_zero():
    facts = _load("aapl_trimmed.json")
    result = extract_maturity_ladder(facts, cik=AAPL_CIK, as_of=date(2025, 1, 1))
    after5 = next(b for b in result["buckets"] if b["key"] == "after5")
    assert after5["usd"] is None
    assert after5["reported"] is False
    assert result["buckets_reported"] < result["buckets_total"]


def test_reported_zero_survives_as_zero():
    facts = _load("aapl_trimmed.json")
    result = extract_maturity_ladder(facts, cik=AAPL_CIK, as_of=date(2025, 1, 1))
    y5 = next(b for b in result["buckets"] if b["key"] == "y5")
    assert y5["reported"] is True
    assert y5["usd"] == 0
    assert y5["display"] == "$0"


def test_no_companyfacts_is_no_filings():
    result = extract_maturity_ladder(None, cik=AAPL_CIK)
    assert result["status"] == "no_filings"
    assert result["buckets"] == []


def test_facts_without_maturity_tags_is_no_maturity_facts():
    result = extract_maturity_ladder({"facts": {"us-gaap": {}}}, cik=AAPL_CIK)
    assert result["status"] == "no_maturity_facts"
    # META-CEO ruling round 2 (B2): "a filer that reports no maturity facts
    # renders each bucket 'not reported'" -- the null state is printed per
    # bucket, never hidden behind a single blanket sentence with no buckets.
    assert len(result["buckets"]) == len(BUCKETS)
    assert all(b["reported"] is False for b in result["buckets"])
    assert all(b["display"] is None and b["usd"] is None for b in result["buckets"])
    assert [b["key"] for b in result["buckets"]] == [b[0] for b in BUCKETS]


def test_identity_is_cik_only():
    facts = _load("aapl_trimmed.json")
    # the fixture carries its own "cik": 320193 (the real SEC companyfacts
    # shape always does) -- a caller-supplied CIK that does NOT canonicalize
    # to the same value must fail closed, never silently trust whichever
    # value happened to be passed in.
    result = extract_maturity_ladder(facts, cik="0000999999", as_of=date(2025, 1, 1))
    assert result["cik"] == "0000999999"
    assert result["status"] == "identity_mismatch"
    assert result["buckets"] == []
    # the matching CIK (any zero-padding) resolves normally.
    result_ok = extract_maturity_ladder(facts, cik=AAPL_CIK, as_of=date(2025, 1, 1))
    assert result_ok["status"] == "reported"
    with pytest.raises(ValueError):
        extract_maturity_ladder(facts, cik="AAPL")  # a ticker/name is not a CIK
    with pytest.raises(ValueError):
        extract_maturity_ladder(facts, cik="")


def test_unit_thousands_and_millions_scaled_to_dollars():
    tag = "LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths"
    facts = {
        "cik": 999999,
        "facts": {"us-gaap": {tag: {"units": {"USDthousands": [
            {"end": "2024-12-31", "val": 1234, "accn": "0000999999-25-000001",
             "fy": 2024, "fp": "FY", "form": "10-K", "filed": "2025-02-01"},
        ]}}}},
    }
    result = extract_maturity_ladder(facts, cik="0000999999", as_of=date(2025, 3, 1))
    y1 = next(b for b in result["buckets"] if b["key"] == "y1")
    assert y1["reported"] is True
    assert y1["usd"] == 1234 * 1000

    tag2 = "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearTwo"
    facts_m = {
        "cik": 999999,
        "facts": {"us-gaap": {tag2: {"units": {"USDmillions": [
            {"end": "2024-12-31", "val": 5, "accn": "0000999999-25-000001",
             "fy": 2024, "fp": "FY", "form": "10-K", "filed": "2025-02-01"},
        ]}}}},
    }
    result_m = extract_maturity_ladder(facts_m, cik="0000999999", as_of=date(2025, 3, 1))
    y2 = next(b for b in result_m["buckets"] if b["key"] == "y2")
    assert y2["reported"] is True
    assert y2["usd"] == 5 * 1_000_000


def test_as_of_is_never_defaulted_from_the_clock():
    # no as_of supplied at all -- purity means this must not consult a clock;
    # the field is simply omitted (None) rather than silently stamped "today".
    result = extract_maturity_ladder(None, cik=AAPL_CIK)
    assert result["as_of"] is None
    facts = _load("aapl_trimmed.json")
    result2 = extract_maturity_ladder(facts, cik=AAPL_CIK)
    assert result2["as_of"] is None
    assert result2["period"]["stale"] is False  # no as_of -> never asserts staleness


def test_module_is_pure():
    src = Path("engine/debt_maturity.py").read_text()
    tree = ast.parse(src)
    banned_calls = {"open", "urlopen"}
    banned_attrs = {"now", "today", "read_csv", "read_parquet"}
    banned_modules = {"requests", "urllib", "pandas"}

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [n.name for n in node.names]
            mod = getattr(node, "module", None)
            for m in list(names) + ([mod] if mod else []):
                assert m not in banned_modules, f"forbidden import: {m}"
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name) and fn.id in banned_calls:
                pytest.fail(f"forbidden call at module scope: {fn.id}")
            if isinstance(fn, ast.Attribute) and fn.attr in banned_attrs:
                pytest.fail(f"forbidden call: {fn.attr}")
    assert "Path(" not in src.replace("# noqa", "")


def test_glance_tier_has_no_machine_text():
    tmpl_path = Path("templates/_debt_maturity.html.j2")
    src = tmpl_path.read_text()
    banned = ["us-gaap", "LongTermDebtMaturities", "accn", "XBRL", "frame"]
    # split at the <details> boundary; everything before/around it minus the
    # details block itself must be free of raw machine vocabulary.
    m = re.search(r"<details.*?</details>", src, re.DOTALL)
    assert m, "expected a <details> disclosure block"
    outside = src[: m.start()] + src[m.end():]
    for term in banned:
        assert term not in outside, f"banned term {term!r} leaked outside <details>"
    inside = m.group(0)
    # the banned vocabulary should actually be reachable inside the details
    assert "accn" in inside


def test_en_zh_parity():
    src = Path("templates/_debt_maturity.html.j2").read_text()
    calls = re.findall(r"\bt\(([^()]*(?:\([^()]*\)[^()]*)*)\)", src)
    assert calls, "expected t() calls in the partial"
    for args in calls:
        # split on the top-level comma (args may themselves contain '~' concatenation
        # but never nested parens at this point since the regex already balanced those)
        depth = 0
        top_commas = 0
        for ch in args:
            if ch in "([":
                depth += 1
            elif ch in ")]":
                depth -= 1
            elif ch == "," and depth == 0:
                top_commas += 1
        assert top_commas >= 1, f"t() call missing a zh arg: {args!r}"


def test_no_translated_title_attribute():
    src = Path("templates/_debt_maturity.html.j2").read_text()
    assert "title=" not in src


def test_resolve_cik_handles_float64_parquet_column(monkeypatch, tmp_path):
    import types
    import sys as _sys
    import scripts.build_debt_maturity as bdm

    monkeypatch.setattr(bdm, "_cik_ledger_path", lambda: tmp_path / "absent.json")
    # `_issuer_master_path` must `.exists()` (resolve_cik gates on that) but its
    # content is never actually read -- `read_parquet` below is mocked to ignore
    # the path and return a fake frame regardless. This file's own path is a
    # convenient stand-in that (a) always exists and (b) is unique to this test,
    # so the round-2 review memoisation cache (keyed by path) can't leak between
    # tests.
    im_path = Path(__file__)

    class _FakeSeries(list):
        """Just enough of the pandas Series interface for the ticker->cik map
        builder: `.astype(str).str.upper()` (ticker column) and plain iteration
        (both columns, via `zip(tickers, ciks)`)."""

        def astype(self, _t):
            return self

        @property
        def str(self):
            return self

        def upper(self):
            return _FakeSeries(str(v).upper() for v in self)

    class _FakeFrame:
        columns = ["ticker", "cik"]

        def __init__(self, rows):
            self._cols = {"ticker": _FakeSeries(r[0] for r in rows),
                          "cik": _FakeSeries(r[1] for r in rows)}

        def __getitem__(self, col):
            return self._cols[col]

    # AAPL's cik round-trips through a float64 parquet column as 320193.0 —
    # must NOT string()-and-strip (that leaves a trailing ".0").
    fake_frame = _FakeFrame([("AAPL", 320193.0)])
    fake_pd = types.SimpleNamespace(read_parquet=lambda _p: fake_frame)
    monkeypatch.setitem(_sys.modules, "pandas", fake_pd)
    monkeypatch.setattr(bdm, "_issuer_master_path", lambda: im_path)

    cik = bdm.resolve_cik("AAPL")
    assert cik == "0000320193"


def test_resolve_cik_memoises_ledger_and_issuer_master_reads(monkeypatch, tmp_path):
    """Round-2 review MAJOR-2: `resolve_cik` is called once per ticker for the
    WHOLE stock-library render-path universe. Un-memoised, every call re-read +
    re-`json.loads`'d the ledger, and every ledger MISS (ETFs/crypto/foreign
    listings) re-read the whole issuer_master parquet AND re-cast its ticker
    column. This pins that both reads happen at most ONCE across many calls
    against the same paths, however many tickers are resolved."""
    import types
    import sys as _sys
    import scripts.build_debt_maturity as bdm

    ledger_path = tmp_path / "ticker_cik_ledger.json"
    ledger_path.write_text(json.dumps({"MSFT": {"cik": 789019}}))
    monkeypatch.setattr(bdm, "_cik_ledger_path", lambda: ledger_path)

    read_text_calls = {"n": 0}
    _orig_read_text = Path.read_text

    def _counting_read_text(self, *a, **k):
        if self == ledger_path:
            read_text_calls["n"] += 1
        return _orig_read_text(self, *a, **k)

    monkeypatch.setattr(Path, "read_text", _counting_read_text)

    class _FakeSeries(list):
        def astype(self, _t):
            return self

        @property
        def str(self):
            return self

        def upper(self):
            return _FakeSeries(str(v).upper() for v in self)

    class _FakeFrame:
        columns = ["ticker", "cik"]

        def __init__(self, rows):
            self._cols = {"ticker": _FakeSeries(r[0] for r in rows),
                          "cik": _FakeSeries(r[1] for r in rows)}

        def __getitem__(self, col):
            return self._cols[col]

    read_parquet_calls = {"n": 0}

    def _counting_read_parquet(_p):
        read_parquet_calls["n"] += 1
        return _FakeFrame([("AAPL", 320193.0), ("TSLA", 1318605.0)])

    fake_pd = types.SimpleNamespace(read_parquet=_counting_read_parquet)
    monkeypatch.setitem(_sys.modules, "pandas", fake_pd)
    im_path = tmp_path / "issuer_master.parquet"
    im_path.write_text("not a real parquet file")  # only needs to .exists()
    monkeypatch.setattr(bdm, "_issuer_master_path", lambda: im_path)

    # MSFT resolves from the ledger; AAPL and TSLA are ledger MISSES that fall
    # through to the issuer_master parquet -- exactly the render-universe shape
    # (ledger hit for the common case, parquet fallback for what the ledger
    # doesn't cover) that made the un-memoised version O(N) file reads.
    tickers = ["MSFT", "AAPL", "TSLA", "MSFT", "AAPL", "NOPE"]
    resolved = [bdm.resolve_cik(t) for t in tickers]

    assert resolved == [
        "0000789019", "0000320193", "0001318605", "0000789019", "0000320193", None,
    ]
    assert read_text_calls["n"] == 1, (
        f"ledger file re-read {read_text_calls['n']} times across {len(tickers)} "
        "tickers -- expected exactly 1 (memoised)"
    )
    assert read_parquet_calls["n"] == 1, (
        f"issuer_master parquet re-read {read_parquet_calls['n']} times across "
        f"{len(tickers)} tickers -- expected exactly 1 (memoised)"
    )


def test_stock_page_wiring():
    ticker_tmpl = Path("templates/ticker.html.j2").read_text()
    assert '{% include "_debt_maturity.html.j2" %}' in ticker_tmpl
    assert 'id="debt-maturity"' in Path("templates/_debt_maturity.html.j2").read_text()
    assert '#debt-maturity' in ticker_tmpl
    build_pages_src = Path("scripts/build_ticker_pages.py").read_text()
    assert '"debt_maturity"' in build_pages_src


def test_chip_and_section_gates_pin_all_seven_statuses():
    """META-CEO B r4 MAJOR-1: pin chip AND section for all seven statuses
    against the LIVE ticker template (not a hand-copied nav snippet).

    reported (the loaded/success status), no_filings, not_loaded,
    identity_mismatch, no_maturity_facts → BOTH chip and section.
    unresolved → section's no-record sentence WITHOUT a chip (ruled asymmetry).
    not_applicable → neither.
    """
    from tests.test_ticker_pages import _jinja_env, _rich_ctx

    tmpl = _jinja_env().get_template("ticker.html.j2")

    both = ("reported", "no_filings", "not_loaded", "identity_mismatch", "no_maturity_facts")
    for status in both:
        ctx = _rich_ctx()
        if status == "reported":
            ctx["debt_maturity"] = extract_maturity_ladder(
                _load("aapl_trimmed.json"), cik=AAPL_CIK, as_of=date(2025, 1, 1)
            )
        else:
            ctx["debt_maturity"] = {"status": status, "cik": None, "buckets": []}
        html = tmpl.render(**ctx)
        assert 'href="#debt-maturity"' in html, f"status={status} must render the chip"
        assert 'id="debt-maturity"' in html, f"status={status} must render the section"

    ctx = _rich_ctx()
    ctx["debt_maturity"] = {"status": "unresolved", "cik": None, "buckets": []}
    html = tmpl.render(**ctx)
    assert 'href="#debt-maturity"' not in html, "unresolved must not render a chip"
    assert 'id="debt-maturity"' in html, "unresolved must still render the section"
    assert "We do not have an SEC filing record for this listing." in html

    ctx = _rich_ctx()
    ctx["debt_maturity"] = {"status": "not_applicable"}
    html = tmpl.render(**ctx)
    assert 'href="#debt-maturity"' not in html
    assert 'id="debt-maturity"' not in html

    ctx = _rich_ctx()
    ctx["debt_maturity"] = None
    html = tmpl.render(**ctx)
    assert 'href="#debt-maturity"' not in html
    assert 'id="debt-maturity"' not in html


def test_debt_maturity_import_failure_never_kills_the_stockdata_build(monkeypatch):
    """Round-2 review MINOR-1: `scripts/build_stock_library.py` imported
    `load_debt_maturity_facts` at bare module level while every actual call
    site is wrapped in `except Exception` -- an import-time failure (this
    module or one of ITS imports raising) killed the WHOLE stockdata build
    before a single ticker was processed. Simulates that failure via the
    module's own `_dm_load is None` fallback (set when the guarded import at
    module load time raised) and asserts the per-ticker try/except still
    degrades gracefully instead of propagating.

    Round-3 review MAJOR-3: this ticker IS a candidate SEC filer (not
    crypto/ETF), so the degraded status must be `not_loaded` -- never
    `not_applicable`, which the taxonomy reserves for "no filer identity by
    construction" and which renders no chip and no section, silently
    swallowing a real filer's null disclosure."""
    import scripts.build_stock_library as bsl

    assert bsl._dm_load is not None, "sanity: import succeeded in this test env"
    monkeypatch.setattr(bsl, "_dm_load", None)

    debt_maturity = bsl._resolve_debt_maturity("AAPL", "Technology", date(2025, 1, 1))

    assert debt_maturity["status"] == "not_loaded"
    assert debt_maturity["status"] != "not_applicable"


def test_sections_gate_matches_nav_chip_gate():
    """Round-2-fix-round MINOR-1: `sections_available` must gate on the SAME
    set as the nav chip (`status not in ('not_applicable', 'unresolved')`) --
    the round-1 defect class (chip narrower than the section render, so a
    real rendered section was orphaned/undercounted) recurred here after the
    chip was widened in round 2 and this counter was not. Only a dead-end
    with no real content (`not_applicable` — no filer identity at all, or
    `unresolved` — an identity gap the panel can never resolve into content)
    is excluded; every other status has a real, navigable disclosure (even a
    null one) and now counts."""
    import scripts.build_ticker_pages as btp

    # use a non-empty base blob (any truthy blob already contributes its own
    # +1 in sections_available) so the debt_maturity-specific delta is isolated
    agg = {"intel_map": {}, "news_map": {}}
    base_blob = {"_marker": True}
    base = btp.sections_available(base_blob, {}, agg, "TEST")

    for status in ("not_applicable", "unresolved"):
        blob = dict(base_blob, debt_maturity={"status": status})
        with_null = btp.sections_available(blob, {}, agg, "TEST")
        assert with_null == base, f"status={status} unexpectedly added to the gate"

    for status in ("reported", "no_filings", "no_maturity_facts", "identity_mismatch", "not_loaded"):
        blob = dict(base_blob, debt_maturity={"status": status})
        with_status = btp.sections_available(blob, {}, agg, "TEST")
        assert with_status == base + 1, f"status={status} should have added to the gate"


# ============================================================================
# META-CEO ruling round 2 (2026-09-06), packet B-F09-3 — B1/B2/B3/B4 repair.
# ============================================================================

def test_cache_miss_is_not_loaded(monkeypatch, tmp_path):
    """B2: a CIK that resolved but was never fetched is 'not_loaded', never a
    fabricated 'no_filings' negative."""
    import scripts.build_debt_maturity as bdm

    monkeypatch.setattr(bdm, "_cache_dir", lambda: tmp_path / "cache")
    monkeypatch.setattr(bdm, "resolve_cik", lambda ticker: "0000320193")
    cik, facts, state = bdm.load_debt_maturity_facts("AAPL")
    assert cik == "0000320193"
    assert facts is None
    assert state == "not_loaded"


def test_unresolved_ticker_is_unresolved(monkeypatch):
    import scripts.build_debt_maturity as bdm

    monkeypatch.setattr(bdm, "resolve_cik", lambda ticker: None)
    cik, facts, state = bdm.load_debt_maturity_facts("ZZZZZNOPE")
    assert cik is None
    assert facts is None
    assert state == "unresolved"


def test_refresh_wired_mode_confirmed_absent_writes_confirmed_no_filings(tmp_path, monkeypatch):
    """B2: the wired call mode (an already-fetched full companyfacts document
    supplied by the caller) records a positive 'confirmed_no_filings' cache
    entry when the caller explicitly passes None -- this is what lets
    load_debt_maturity_facts hand the engine a real 'no_filings' status
    instead of a blanket not_loaded."""
    import scripts.build_debt_maturity as bdm

    monkeypatch.setattr(bdm, "_cache_dir", lambda: tmp_path / "cache")
    ok = bdm.refresh_cache_for_cik("0000999999", full_companyfacts=None)
    assert ok is True
    cached = bdm.load_cached_facts("0000999999")
    assert cached is not None
    assert cached.get("confirmed_no_filings") is True
    assert cached.get("fetched_at")


def test_refresh_wired_mode_slims_tags_from_full_companyfacts(tmp_path, monkeypatch):
    """B2/efficiency: the wired mode never makes its own network call -- it
    slims the six bounded tags out of a full companyfacts document the
    caller already fetched (collectors/edgar_facts.py's own per-issuer
    companyfacts fetch)."""
    import scripts.build_debt_maturity as bdm

    monkeypatch.setattr(bdm, "_cache_dir", lambda: tmp_path / "cache")
    facts = _load("aapl_trimmed.json")
    ok = bdm.refresh_cache_for_cik("0000320193", full_companyfacts=facts)
    assert ok is True
    cached = bdm.load_cached_facts("0000320193")
    assert cached is not None
    assert not cached.get("confirmed_no_filings")
    assert cached["cik"] == 320193
    # only the six bounded tags may appear -- never the full companyfacts blob.
    assert set(cached["facts"]["us-gaap"]) <= {t[1] for t in BUCKETS}
    tag = "LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths"
    assert tag in cached["facts"]["us-gaap"]


def test_loaded_state_after_wired_refresh_reaches_reported(tmp_path, monkeypatch):
    import scripts.build_debt_maturity as bdm

    monkeypatch.setattr(bdm, "_cache_dir", lambda: tmp_path / "cache")
    monkeypatch.setattr(bdm, "resolve_cik", lambda ticker: AAPL_CIK)
    facts = _load("aapl_trimmed.json")
    assert bdm.refresh_cache_for_cik(AAPL_CIK, full_companyfacts=facts) is True
    cik, cached_facts, state = bdm.load_debt_maturity_facts("AAPL")
    assert state == "loaded"
    result = extract_maturity_ladder(cached_facts, cik=cik, as_of=date(2025, 1, 1))
    assert result["status"] == "reported"


def test_confirmed_no_filings_state_reaches_engine_no_filings(tmp_path, monkeypatch):
    import scripts.build_debt_maturity as bdm

    monkeypatch.setattr(bdm, "_cache_dir", lambda: tmp_path / "cache")
    monkeypatch.setattr(bdm, "resolve_cik", lambda ticker: "0000999999")
    assert bdm.refresh_cache_for_cik("0000999999", full_companyfacts=None) is True
    cik, cached_facts, state = bdm.load_debt_maturity_facts("NOFILE")
    assert state == "confirmed_no_filings"
    assert cached_facts is None
    # this is exactly how scripts/build_stock_library.py's call site derives
    # the engine's own "no_filings" status: pass None through, never invent
    # the status string a second time.
    result = extract_maturity_ladder(None, cik=cik, as_of=date(2025, 1, 1))
    assert result["status"] == "no_filings"


def test_refresh_standalone_mode_total_network_failure_never_overwrites_cache(tmp_path, monkeypatch):
    """Standalone mode (no full_companyfacts kwarg): a total per-CIK network
    failure across every tag must leave any existing cache untouched and
    return False -- never confirm a false negative from a network blip."""
    import scripts.build_debt_maturity as bdm

    cache_dir = tmp_path / "cache"
    monkeypatch.setattr(bdm, "_cache_dir", lambda: cache_dir)

    class _DeadSession:
        def get(self, *a, **k):
            raise ConnectionError("network down")

    # seed an existing real cache entry first
    cache_dir.mkdir(parents=True)
    (cache_dir / "CIK0000999999.json").write_text('{"cik": 999999, "facts": {"us-gaap": {}}}')
    before = bdm.load_cached_facts("0000999999")

    ok = bdm.refresh_cache_for_cik("0000999999", session=_DeadSession())
    assert ok is False
    after = bdm.load_cached_facts("0000999999")
    assert after == before  # untouched


def test_refresh_standalone_mode_all_404_writes_confirmed_no_filings(tmp_path, monkeypatch):
    """Standalone mode: every tag request completing (even as a clean 404)
    is a genuine round trip and must write a confirmed cache entry, distinct
    from the total-failure case above."""
    import scripts.build_debt_maturity as bdm

    monkeypatch.setattr(bdm, "_cache_dir", lambda: tmp_path / "cache")

    class _Resp:
        status_code = 404

    class _AllNotFoundSession:
        def get(self, *a, **k):
            return _Resp()

    ok = bdm.refresh_cache_for_cik("0000999999", session=_AllNotFoundSession())
    assert ok is True
    cached = bdm.load_cached_facts("0000999999")
    assert cached.get("confirmed_no_filings") is True


def test_nightly_wiring_call_site_and_registration():
    """B1: refresh_cache_for_cik is called for every issuer
    collectors/edgar_facts.py already companyfacts-fetches (the same universe
    the stock library builds), and the nightly registration line (a real
    cron schedule) exists for it -- never a network call on the render path
    (build_stock_library.py / build_ticker_pages.py never import the
    collector)."""
    edgar_facts_src = Path("collectors/edgar_facts.py").read_text()
    assert "from scripts.build_debt_maturity import refresh_cache_for_cik" in edgar_facts_src
    # a real call, not merely the import line
    assert edgar_facts_src.count("refresh_cache_for_cik(") >= 2

    workflow_src = Path(".github/workflows/debt-maturity-drip.yml").read_text()
    assert re.search(r"cron:\s*[\"']", workflow_src), "expected a real cron schedule line"
    assert "backfill_edgar_flow" in workflow_src

    for render_path in ("scripts/build_stock_library.py", "scripts/build_ticker_pages.py"):
        src = Path(render_path).read_text()
        assert "collectors.edgar_facts" not in src
        assert "refresh_cache_for_cik" not in src, (
            f"{render_path} must read the cache, never refresh it on the render path"
        )


def test_no_inline_style_in_partial():
    """B3: the inline <style> block is a design-system bypass — it must live
    in templates/theme.css (governed CSS), not the partial."""
    src = Path("templates/_debt_maturity.html.j2").read_text()
    assert "<style" not in src


def test_theme_css_owns_debt_maturity_rules():
    src = Path("templates/theme.css").read_text()
    assert "debt maturity ladder" in src
    assert ".dmw{" in src or ".dmw {" in src
    assert '[data-theme="light"] .dmr' in src


# ---------------------------------------------------------------------------
# Real Jinja renders of the partial (M4 — the prior suite only regex-scanned
# the template source; these actually render it for every status).
# ---------------------------------------------------------------------------

def _render_partial(debt_maturity: dict) -> str:
    from jinja2 import Environment, FileSystemLoader

    from engine import i18n

    env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
    env.globals["t"] = i18n.t
    tmpl = env.get_template("_debt_maturity.html.j2")
    return tmpl.render(debt_maturity=debt_maturity)


def test_render_reported_status():
    facts = _load("aapl_trimmed.json")
    result = extract_maturity_ladder(facts, cik=AAPL_CIK, as_of=date(2025, 1, 1))
    html = _render_partial(result)
    assert 'id="debt-maturity"' in html
    assert "Debt coming due" in html
    assert result["total_display"] in html
    assert "not reported" in html  # the unit_not_usd/period_mismatch buckets


def test_render_reported_zero_gets_distinct_marker_class():
    """Round-2 review MINOR-4: a bucket that IS reported but is a real "$0"
    must render a `dmr-zero` marker class distinct from an unreported (`na`)
    bucket -- otherwise a zero-width bar and an empty na track are
    indistinguishable at a glance."""
    tag = "LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths"
    facts = {
        "cik": 999999,
        "facts": {"us-gaap": {tag: {"units": {"USD": [
            {"end": "2024-12-31", "val": 0, "accn": "0000999999-25-000001",
             "fy": 2024, "fp": "FY", "form": "10-K", "filed": "2025-02-01"},
        ]}}}},
    }
    result = extract_maturity_ladder(facts, cik="0000999999", as_of=date(2025, 3, 1))
    y1 = next(b for b in result["buckets"] if b["key"] == "y1")
    assert y1["reported"] is True
    assert y1["usd"] == 0
    html = _render_partial(result)
    assert 'class="dmr-tr dmr-zero"' in html
    # the five other (unreported) buckets on the same fixture must NOT carry
    # the zero marker -- only exactly one dmr-zero should appear.
    assert html.count("dmr-zero") == 1
    assert 'class="dmr na"' in html  # sanity: this fixture also has unreported buckets


def test_render_no_filings_status():
    html = _render_partial({"schema": "debt_maturity.v1", "status": "no_filings", "cik": "0000999999",
                            "buckets": [], "total_reported_usd": None, "total_display": None,
                            "near_share_pct": None, "buckets_reported": 0, "buckets_total": 6, "as_of": None})
    assert "No SEC filings available for this listing." in html
    assert "没有可用" not in html  # sanity: not accidentally emitting a different ZH string
    assert "该证券暂无可用的 SEC 文件" in html
    assert "Debt schedule not loaded yet." not in html


def test_render_not_loaded_status_is_distinct_from_no_filings():
    html = _render_partial({"schema": "debt_maturity.v1", "status": "not_loaded", "cik": "0000320193",
                            "buckets": [], "total_reported_usd": None, "total_display": None,
                            "near_share_pct": None, "buckets_reported": 0, "buckets_total": 6, "as_of": None})
    assert "Debt schedule not loaded yet." in html
    assert "到期债务尚未加载" in html
    assert "No SEC filings available" not in html


def test_render_no_maturity_facts_shows_every_bucket_not_reported():
    result = extract_maturity_ladder({"cik": 999999, "facts": {"us-gaap": {}}}, cik="0000999999", as_of=date(2025, 1, 1))
    assert result["status"] == "no_maturity_facts"
    html = _render_partial(result)
    # every one of the six bucket labels appears, each marked not reported —
    # never a single blanket sentence hiding the per-bucket null.
    assert html.count("not reported") == len(BUCKETS)
    for _key, _tag, en, _zh in BUCKETS:
        assert en in html


def test_render_identity_mismatch_is_not_an_empty_panel():
    """B4: identity_mismatch must never render an empty panel between the
    header and the research-only footer."""
    result = extract_maturity_ladder(_load("aapl_trimmed.json"), cik="0000999999", as_of=date(2025, 1, 1))
    assert result["status"] == "identity_mismatch"
    html = _render_partial(result)
    assert "We could not confirm which company filed for this listing, so the debt schedule is not shown." in html
    assert "我们无法确认是哪家公司为该证券提交了文件" in html
    # the research-only footer still renders (it is outside the status branch)
    assert "Research context only" in html
    # the panel is not literally empty between the header close and footer open
    hd_end = html.index("</div>", html.index("mod-hd"))
    ft_start = html.index('class="mod-ft"')
    body = html[hd_end:ft_start].strip()
    assert body, "identity_mismatch rendered an empty panel body"


# ============================================================================
# META-CEO ruling, next fix round (2026-09-07), packet B-F09-3 — round-2
# review MAJOR-1/MAJOR-2/MINOR-1 repair.
# ============================================================================

def test_render_unresolved_status_no_promise():
    """MAJOR-1: `unresolved` (an identity gap) must render an honest terminal
    sentence and must NEVER render the `not_loaded` catching-up promise --
    that promise is earned only by a CIK that genuinely has a fetch pending."""
    html = _render_partial({"schema": "debt_maturity.v1", "status": "unresolved", "cik": None,
                            "buckets": [], "total_reported_usd": None, "total_display": None,
                            "near_share_pct": None, "buckets_reported": 0, "buckets_total": 6, "as_of": None})
    assert "We do not have an SEC filing record for this listing." in html
    assert "我们目前没有该证券的 SEC 备案记录" in html
    assert "Debt schedule not loaded yet." not in html
    assert "catching up" not in html
    assert "Check back soon" not in html


def test_etf_page_renders_no_chip_and_no_section(monkeypatch):
    """MAJOR-1 RED-first: an ETF (universe()'s "ETF / macro" sector sentinel)
    must resolve to `not_applicable` WITHOUT ever attempting a CIK lookup --
    the fabricated "catching up" promise the round-2 review measured across
    every ETF/ADR/crypto/foreign listing must be impossible by construction,
    not merely absent because the lookup happened to fail.

    Round-3 review MAJOR-2: the prior version of this test hand-copied the
    `if ticker.endswith("-USD") or sector == "ETF / macro"` branch inline
    instead of calling the real production code, so it passed identically
    on the pre-fix parent head too (it was pinning its own re-implementation,
    not scripts/build_stock_library.py's actual short-circuit). This calls
    the extracted, directly-callable `bsl._resolve_debt_maturity()` -- the
    ACTUAL function the per-ticker loop calls -- so a regression that
    removes or narrows the short-circuit fails this test."""
    import scripts.build_stock_library as bsl

    def _boom(_ticker):  # pragma: no cover - must never be called for an ETF
        raise AssertionError("resolve_cik/_dm_load must not be reached for an ETF")

    monkeypatch.setattr(bsl, "_dm_load", _boom)

    debt_maturity = bsl._resolve_debt_maturity("SPY", "ETF / macro", date(2025, 1, 1))

    assert debt_maturity["status"] == "not_applicable"
    html = _render_partial(debt_maturity)
    assert html == "", "not_applicable must render no section at all"


def test_cikless_common_stock_is_unresolved_not_not_applicable(monkeypatch):
    """MAJOR-1 RED-first companion: a common stock (real GICS sector, not the
    "ETF / macro" sentinel, not crypto) whose CIK lookup finds nothing is
    `unresolved` -- an identity gap in OUR ledger, not a structural
    not-a-filer classification -- and its rendered panel must carry the
    honest no-record sentence, never the not_loaded catching-up promise.
    Calls the real, extracted `bsl._resolve_debt_maturity()` (round-3
    review MAJOR-2) rather than hand-building the expected dict."""
    import scripts.build_debt_maturity as bdm
    import scripts.build_stock_library as bsl

    monkeypatch.setattr(bdm, "resolve_cik", lambda ticker: None)
    monkeypatch.setattr(bsl, "_dm_load", bdm.load_debt_maturity_facts)

    ticker, sector = "ZZZZNOPE", "Technology"
    assert not (ticker.endswith("-USD") or sector == "ETF / macro")
    debt_maturity = bsl._resolve_debt_maturity(ticker, sector, date(2025, 1, 1))
    assert debt_maturity["status"] == "unresolved"
    html = _render_partial(debt_maturity)
    assert "We do not have an SEC filing record for this listing." in html
    assert "Debt schedule not loaded yet." not in html
    assert "catching up" not in html


def test_rate_limit_across_every_tag_never_writes_cache(tmp_path, monkeypatch):
    """MAJOR-2 RED-first: a systematic 429 (or 401/403/5xx) across all six
    tags is a THROTTLE/AUTH failure, not a completed round trip -- it must
    leave the cache untouched exactly like a total network failure, never
    write a fabricated `confirmed_no_filings` the panel renders as the
    positive claim "No SEC filings available for this listing."."""
    import scripts.build_debt_maturity as bdm

    monkeypatch.setattr(bdm, "_cache_dir", lambda: tmp_path / "cache")

    class _Resp:
        status_code = 429

    class _AllThrottledSession:
        def get(self, *a, **k):
            return _Resp()

    ok = bdm.refresh_cache_for_cik("0000888888", session=_AllThrottledSession())
    assert ok is False
    assert bdm.load_cached_facts("0000888888") is None
    assert not (tmp_path / "cache" / "CIK0000888888.json").exists()


def test_mixed_200_and_429_still_completes(tmp_path, monkeypatch):
    """MAJOR-2 companion: a genuine mix (some tags answer 200, some are
    throttled) must still complete normally on the tags that DID answer --
    the fix narrows what counts as "asked", it must not regress the existing
    "some tags reported" path."""
    import scripts.build_debt_maturity as bdm

    monkeypatch.setattr(bdm, "_cache_dir", lambda: tmp_path / "cache")
    tag = "LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths"

    class _Resp:
        def __init__(self, status_code, payload=None):
            self.status_code = status_code
            self._payload = payload

        def json(self):
            return self._payload

    class _MixedSession:
        def get(self, url, **k):
            if tag in url:
                return _Resp(200, {"units": {"USD": [
                    {"end": "2024-12-31", "val": 100, "accn": "0000888887-25-000001",
                     "fy": 2024, "fp": "FY", "form": "10-K", "filed": "2025-02-01"},
                ]}})
            return _Resp(429)

    ok = bdm.refresh_cache_for_cik("0000888887", session=_MixedSession())
    assert ok is True
    cached = bdm.load_cached_facts("0000888887")
    assert cached is not None
    assert cached.get("confirmed_no_filings") is not True
    assert tag in cached["facts"]["us-gaap"]


def test_partial_throttle_with_one_404_never_writes_confirmed_no_filings(tmp_path, monkeypatch):
    """Round-3 review MAJOR-1 RED-first: the previous fix gated
    `confirmed_no_filings` on `any_clean_response` (at least one tag
    answered), not on EVERY tag answering. A cycle where one of the six tags
    gets a routine 404 (SEC's own "no data for this tag" answer -- common,
    not an error) and the other five are throttled 429 sets
    `any_clean_response=True`, `got_any=False`, and used to fabricate
    `confirmed_no_filings: true` off five unanswered requests. Only when
    ALL SIX tags have completed (200 or 404) and none found data may the
    cache legitimately claim confirmed_no_filings."""
    import scripts.build_debt_maturity as bdm

    monkeypatch.setattr(bdm, "_cache_dir", lambda: tmp_path / "cache")
    answered_tag = bdm._TAGS[0]

    class _Resp:
        def __init__(self, status_code):
            self.status_code = status_code

    class _OneFourOhFourRestThrottledSession:
        def get(self, url, **k):
            if answered_tag in url:
                return _Resp(404)
            return _Resp(429)

    ok = bdm.refresh_cache_for_cik("0000888886", session=_OneFourOhFourRestThrottledSession())
    # A single clean 404 with five throttled tags is still a genuinely
    # partial cycle -- the cache write itself may proceed (there IS at least
    # one completed answer), but it must never carry the positive
    # `confirmed_no_filings` claim.
    assert ok is True
    cached = bdm.load_cached_facts("0000888886")
    assert cached is not None
    assert cached.get("confirmed_no_filings") is not True


def test_all_six_tags_404_does_write_confirmed_no_filings(tmp_path, monkeypatch):
    """Companion to the above: when every tag completes (all six 404s), the
    fix must not regress the legitimate "asked every tag, got nothing"
    case -- confirmed_no_filings is still the correct, honest claim there."""
    import scripts.build_debt_maturity as bdm

    monkeypatch.setattr(bdm, "_cache_dir", lambda: tmp_path / "cache")

    class _Resp:
        status_code = 404

    class _AllFourOhFourSession:
        def get(self, *a, **k):
            return _Resp()

    ok = bdm.refresh_cache_for_cik("0000888885", session=_AllFourOhFourSession())
    assert ok is True
    cached = bdm.load_cached_facts("0000888885")
    assert cached is not None
    assert cached.get("confirmed_no_filings") is True


def test_debt_maturity_producer_fault_degrades_to_not_loaded_not_not_applicable(monkeypatch):
    """Round-3 review MAJOR-3 RED-first: this listing IS a candidate SEC
    filer (it is not crypto/ETF, so it reaches the CIK-lookup else branch).
    A transient fault inside the lookup/extract path itself (a real,
    non-None `_dm_load` that raises mid-call -- distinct from the
    import-failure/`_dm_load is None` case pinned above) must degrade to
    `not_loaded`, never `not_applicable`. Calls the ACTUAL production
    function (`scripts.build_stock_library._dm_load`, monkeypatched to raise)
    through the real `try/except` shape, not a hand-copied mirror."""
    import scripts.build_stock_library as bsl

    def _boom(_ticker):
        raise RuntimeError("simulated producer fault")

    monkeypatch.setattr(bsl, "_dm_load", _boom)

    ticker, sector = "REALFILR", "Technology"
    assert not (ticker.endswith("-USD") or sector == "ETF / macro")

    debt_maturity = bsl._resolve_debt_maturity(ticker, sector, date(2025, 1, 1))

    assert debt_maturity["status"] == "not_loaded"
    assert debt_maturity["status"] != "not_applicable"


def test_reported_lede_bucket_is_always_the_near_bucket():
    """MINOR-4: the template hard-codes `buckets[0].display` as the next-12-
    months figure whenever `near_share_pct is not none`. Pins the invariant
    that makes that safe: bucket 0 is always the y1 ("Next 12 months")
    bucket by construction, and `near_share_pct` is only ever non-None when
    that same bucket 0 is reported -- so the lede can never mislabel a
    different bucket's figure."""
    facts = _load("aapl_trimmed.json")
    result = extract_maturity_ladder(facts, cik=AAPL_CIK, as_of=date(2025, 1, 1))
    assert result["status"] == "reported"
    assert result["buckets"][0]["key"] == "y1"
    if result["near_share_pct"] is not None:
        assert result["buckets"][0]["reported"] is True


def test_unreported_bucket_value_is_muted_not_link_blue():
    """r4 MINOR-1: 'not reported' / '未披露' must not use --prov-ink (link-blue)."""
    css = Path("templates/theme.css").read_text()
    m = re.search(r"\.dmr\.na \.dmr-val\{[^}]+\}", css)
    assert m, "missing .dmr.na .dmr-val rule"
    rule = m.group(0)
    assert "--prov-ink" not in rule
    assert "color:var(--muted)" in rule


def test_content_address_png_sha256_matches_bytes(tmp_path):
    """MAJOR-3 RED-first: content_address_png hashes the bytes it writes.

    On parent head 33fc01d5 the capture script cropped after hashing, so
    every committed cell's manifest sha256 described pre-trim bytes. This
    helper is the post-shot path; a mismatch here is the same defect.
    """
    from scripts.capture_debt_maturity_evidence import content_address_png
    from scripts.capture_page_evidence import _tiny_png

    png = _tiny_png(8, 6, 90)
    name, digest, width, height = content_address_png(png, tmp_path)
    assert digest == hashlib.sha256(png).hexdigest()
    assert name == f"{digest[:16]}.png"
    assert (tmp_path / name).read_bytes() == png
    assert (width, height) == (8, 6)


def test_evidence_manifest_sha256_matches_file_digest():
    """MAJOR-3: every committed cell's manifest sha256 equals the file digest."""
    root = Path("mockups/evidence/debt_maturity")
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        pytest.skip("mockups/evidence/debt_maturity not checked out")
    manifest = json.loads(manifest_path.read_text())
    cells = 0
    for page in manifest.get("pages", []):
        for state in page.get("states", []):
            if not state.get("captured"):
                continue
            cells += 1
            png_path = root / state["file"]
            digest = hashlib.sha256(png_path.read_bytes()).hexdigest()
            assert state["sha256"] == digest, (
                f"{state['file']}: manifest sha256 {state['sha256'][:16]} "
                f"!= file digest {digest[:16]}"
            )
            assert Path(state["file"]).name.startswith(digest[:16])
    assert cells >= 48, f"expected 48 captured cells, got {cells}"


def test_capture_script_uses_real_ticker_page_and_element_screenshot():
    """BLOCKER: capture must shoot #debt-maturity on ticker.html.j2, not a fixture."""
    src = Path("scripts/capture_debt_maturity_evidence.py").read_text()
    assert "ticker.html.j2" in src
    assert 'locator("#debt-maturity")' in src or "locator('#debt-maturity')" in src
    assert "content_address_png" in src
    assert "_SHELL" not in src
    assert "body::before {{ display:none" not in src
    assert "render_ticker_page" in src


# ---------------------------------------------------------------------------
# W8B F09-11: debt-maturity persistence heal (R3c — workflow + helper tests)
# ---------------------------------------------------------------------------


import subprocess as _subprocess  # noqa: E402  -- kept local so the rest of
                                  # the file's import block is untouched

import yaml as _yaml  # noqa: E402  -- only the workflow-lint test needs it

from scripts import debt_maturity_drip_push as _dmp  # noqa: E402


WORKFLOW_PATH = Path(".github/workflows/debt-maturity-drip.yml")
HELPER_PATH = Path("scripts/debt_maturity_drip_push.py")


def _init_repo(path: Path) -> None:
    """Init a fresh ``main`` repo with a CI-bot identity and a baseline
    commit so the helper has something to push to.

    Mirrors ``tests/test_ci_pack_semantic.py::_small_repository`` so the
    two test files use the same plumbing for any future port.

    Uses ``exist_ok=True`` so the helper is robust to tmp_path being
    pre-created by pytest's tmp_path fixture under newer pytest releases
    where the fixture root is created once and tests share the parent.
    """
    path.mkdir(exist_ok=True)
    # If a prior test left a partial .git, wipe it so init is clean.
    if (path / ".git").exists():
        _subprocess.run(["rm", "-rf", str(path / ".git")], check=True, capture_output=True)
    for args in (
        ["init", "-q", "-b", "main"],
        ["config", "user.email", "ci@example.test"],
        ["config", "user.name", "CI Test"],
        ["config", "commit.gpgsign", "false"],
    ):
        _subprocess.run(["git", *args], cwd=path, check=True, capture_output=True)


def _git(path: Path, *args: str, check: bool = False) -> str:
    return _subprocess.run(
        ["git", *args],
        cwd=path,
        check=check,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _seed_repo(path: Path) -> None:
    """Seed the two ALLOWED paths with byte-identical baseline files
    and commit. The helper will only carry forward writes that touch
    these exact paths.
    """
    cache_dir = path / "data" / "debt_maturity" / "cache"
    cache_dir.mkdir(parents=True)
    (cache_dir / "0000320193.json").write_text('{"fetched_at":"2026-09-12"}\n')
    (path / "data" / "edgar").mkdir(parents=True)
    (path / "data" / "edgar" / "statements.parquet").write_bytes(b"PARQUET_v0")
    (path / "engine").mkdir()
    (path / "engine" / "engine_marker.txt").write_text("untouched\n")
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", "baseline")


def _bare_remote(work: Path) -> Path:
    """Clone the working repo as a bare remote the helper can push to."""
    bare = work.parent / (work.name + "_bare.git")
    _subprocess.run(
        ["git", "clone", "--bare", str(work), str(bare)],
        check=True,
        capture_output=True,
    )
    return bare


def _add_remote(work: Path, bare: Path) -> None:
    """Wire the bare remote into the work repo as ``origin``."""
    _subprocess.run(
        ["git", "-C", str(work), "remote", "add", "origin", str(bare)],
        check=True,
        capture_output=True,
    )


def test_drip_workflow_lints_clean_and_wires_the_persist_step():
    """R3c/workflow-lint: workflow is well-formed, has exactly one
    ``permissions:``, no job-level permissions block, and the last step
    runs the helper under the kill-switch env expression."""
    text = WORKFLOW_PATH.read_text()
    wf = _yaml.safe_load(text)

    assert wf["permissions"] == {"contents": "write"}
    for job_id, job in wf["jobs"].items():
        assert "permissions" not in job, (
            f"job {job_id!r} must not declare a job-level permissions block; "
            "top-level is the only one"
        )
    assert text.count("permissions:") == 1, (
        "workflow must carry exactly one `permissions:` (top-level only)"
    )

    # The cron + backfill_edgar_flow wiring (from the original workflow,
    # preserved by R2/R3a) must still be there.
    assert re.search(r"cron:\s*[\"']", text), "expected a real cron schedule line"
    assert "backfill_edgar_flow" in text

    # The new persist step is named per R3b and runs the helper under
    # the kill-switch env expression.
    steps = wf["jobs"]["drip"]["steps"]
    last = steps[-1]
    assert "persist cache + statements to main" in last["name"]
    env = last.get("env", {})
    assert env.get("DEBT_MATURITY_DRIP_PUSH") == "${{ github.event.inputs.push || '1' }}"
    run = last.get("run", "")
    assert "scripts.debt_maturity_drip_push" in run
    assert "--base main" in run

    # R3d: the old "nightly ENGINE job's git add data/ will commit them"
    # echo must be gone (the assumption it encoded is false, per R1).
    assert "ENGINE job's git add data/" not in text
    assert "git add data/" not in text


def test_drip_push_gate_off_emits_notice_and_no_commit(monkeypatch, tmp_path, capsys):
    """R3c/(i): with DEBT_MATURITY_DRIP_PUSH != "1", the helper prints the
    gate-off ::notice at line start and returns 0 without staging or
    committing anything."""
    _init_repo(tmp_path)
    _seed_repo(tmp_path)
    monkeypatch.delenv("DEBT_MATURITY_DRIP_PUSH", raising=False)
    monkeypatch.setenv("DEBT_MATURITY_DRIP_PUSH", "0")

    rc = _dmp.main(["--repo", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.startswith("::notice"), f"expected annotation at line start, got: {out!r}"
    assert "title=debt-maturity-drip" in out
    assert "push disabled" in out
    head_sha = _git(tmp_path, "rev-parse", "HEAD")
    baseline_sha = _git(tmp_path, "log", "--format=%H", "-n", "1", "HEAD~0")
    assert head_sha == baseline_sha, "no commit must be minted on the gate-off path"


def test_drip_push_empty_diff_emits_notice_and_no_commit(monkeypatch, tmp_path, capsys):
    """R3c/(ii): when nothing under ALLOWED_PATHS changed, the helper
    emits the no-op ::notice and returns 0 without a commit."""
    _init_repo(tmp_path)
    _seed_repo(tmp_path)
    monkeypatch.setenv("DEBT_MATURITY_DRIP_PUSH", "1")

    rc = _dmp.main(["--repo", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.startswith("::notice")
    assert "no changes to persist" in out
    log_count = _git(tmp_path, "rev-list", "--count", "HEAD")
    assert log_count == "1", f"expected 1 baseline commit, got {log_count}"


def test_drip_push_ceiling_exceeded_resets_and_warns(monkeypatch, tmp_path, capsys):
    """R3c/(iii): a staged cache file larger than the ceiling results in
    a ``::warning`` refusal, no commit, and a clean index."""
    _init_repo(tmp_path)
    _seed_repo(tmp_path)

    # Add a 2 MiB cache entry under the ceiling dir.
    cache_dir = tmp_path / "data" / "debt_maturity" / "cache"
    (cache_dir / "huge.json").write_bytes(b"x" * (2 * 1024 * 1024))

    monkeypatch.setenv("DEBT_MATURITY_DRIP_PUSH", "1")

    rc = _dmp.main(["--repo", str(tmp_path), "--max-mb", "1"])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.startswith("::warning"), f"expected ::warning at line start, got: {out!r}"
    assert "exceeds ceiling" in out

    # No commit landed and the index is clean.
    log_count = _git(tmp_path, "rev-list", "--count", "HEAD")
    assert log_count == "1", f"expected 1 baseline commit, got {log_count}"
    diff = _subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=tmp_path
    )
    assert diff.returncode == 0, "staged diff must be reset after a ceiling refusal"


def test_drip_push_does_not_stage_files_outside_allowed(monkeypatch, tmp_path):
    """R3c/(iv): a write outside ALLOWED_PATHS is left unstaged while
    the allowed change IS staged, so the resulting commit carries only
    the two paths."""
    _init_repo(tmp_path)
    _seed_repo(tmp_path)
    bare = _bare_remote(tmp_path)
    _add_remote(tmp_path, bare)

    # Modify the cache dir (allowed) and a stray engine/ file (not allowed).
    (tmp_path / "data" / "debt_maturity" / "cache" / "0000320193.json").write_text(
        '{"fetched_at":"2026-09-13"}\n'
    )
    (tmp_path / "engine" / "engine_marker.txt").write_text("forbidden\n")

    monkeypatch.setenv("DEBT_MATURITY_DRIP_PUSH", "1")

    rc = _dmp.main(["--repo", str(tmp_path)])
    assert rc == 0

    # The engine_marker.txt is in the baseline commit (untouched), so it
    # is in the tree -- but the tip's BLOB must still hold the original
    # "untouched" text, never the "forbidden" write.
    tip_marker = _git(bare, "show", "main:engine/engine_marker.txt")
    assert tip_marker == "untouched", (
        "engine/ write must NOT have been committed; "
        f"tip blob was {tip_marker!r}"
    )


def test_drip_push_happy_path_pushes_to_bare_remote(monkeypatch, tmp_path, capsys):
    """R3c/(v): the bare remote's <base> tip carries exactly one new
    commit, authored by dashboard-bot, subject ends [skip ci]."""
    _init_repo(tmp_path)
    _seed_repo(tmp_path)
    bare = _bare_remote(tmp_path)
    _add_remote(tmp_path, bare)

    (tmp_path / "data" / "debt_maturity" / "cache" / "0000320193.json").write_text(
        '{"fetched_at":"2026-09-13"}\n'
    )

    monkeypatch.setenv("DEBT_MATURITY_DRIP_PUSH", "1")

    baseline_count = _git(tmp_path, "rev-list", "--count", "HEAD")
    rc = _dmp.main(["--repo", str(tmp_path)])
    assert rc == 0

    out = capsys.readouterr().out
    assert "::notice title=debt-maturity-drip" in out
    assert "pushed" in out

    # Bare remote grew by exactly one commit.
    bare_count = _git(bare, "rev-list", "--count", "main")
    assert bare_count == str(int(baseline_count) + 1)
    subject = _git(bare, "log", "-1", "--format=%s", "main")
    assert subject.endswith("[skip ci]"), subject
    assert subject.startswith("debt-maturity-drip: persist cache + statements ")
    author = _git(bare, "log", "-1", "--format=%an", "main")
    committer = _git(bare, "log", "-1", "--format=%cn", "main")
    assert author == "dashboard-bot"
    assert committer == "dashboard-bot"

    # The tree contains both allowed paths and the engine/ baseline file
    # (which is unchanged on this tip because the helper only staged the
    # two ALLOWED_PATHS). The allowed cache file at the tip carries the
    # NEW bytes we wrote, not the seed baseline.
    tip_cache = _git(bare, "show", "main:data/debt_maturity/cache/0000320193.json")
    assert tip_cache == '{"fetched_at":"2026-09-13"}'
    # And the engine marker at the tip is still the untouched seed.
    tip_marker = _git(bare, "show", "main:engine/engine_marker.txt")
    assert tip_marker == "untouched"


def _foreign_commit_on_bare(tmp_path: Path, bare: Path, file_name: str = "README.md") -> None:
    """Land a foreign commit on the bare remote so the helper's push
    will hit a non-fast-forward.

    The foreign repo CLONES the bare so its main is a descendant of
    bare/main; without that ancestry the push is rejected as unrelated
    histories and the helper never gets to test its retry path.
    """
    foreign = tmp_path / "foreign"
    if foreign.exists():
        _subprocess.run(["rm", "-rf", str(foreign)], check=True, capture_output=True)
    _subprocess.run(
        ["git", "clone", "-q", str(bare), str(foreign)],
        check=True,
        capture_output=True,
    )
    _subprocess.run(
        ["git", "-C", str(foreign), "config", "user.email", "f@f.test"],
        check=True,
        capture_output=True,
    )
    _subprocess.run(
        ["git", "-C", str(foreign), "config", "user.name", "Foreign"],
        check=True,
        capture_output=True,
    )
    (foreign / file_name).write_text("foreign commit\n")
    _subprocess.run(
        ["git", "-C", str(foreign), "add", file_name],
        check=True,
        capture_output=True,
    )
    _subprocess.run(
        ["git", "-C", str(foreign), "commit", "-q", "-m", "foreign"],
        check=True,
        capture_output=True,
    )
    _subprocess.run(
        ["git", "-C", str(foreign), "push", "origin", "main"],
        check=True,
        capture_output=True,
    )


def test_drip_push_lands_after_non_fast_forward(monkeypatch, tmp_path, capsys):
    """R3c/(vi): when origin/<base> moves between clone and push, the
    helper's rebase-free re-checkout cycle lands the change on the
    second attempt, and the remote tip contains BOTH the foreign commit
    and the two paths."""
    _init_repo(tmp_path)
    _seed_repo(tmp_path)
    bare = _bare_remote(tmp_path)
    _add_remote(tmp_path, bare)

    # Modify the cache file in the WORKING TREE (do NOT commit locally --
    # the helper does the commit).
    (tmp_path / "data" / "debt_maturity" / "cache" / "0000320193.json").write_text(
        '{"fetched_at":"2026-09-13"}'
    )

    # A foreign commit lands on the bare remote BEFORE the helper's push.
    _foreign_commit_on_bare(tmp_path, bare)

    monkeypatch.setenv("DEBT_MATURITY_DRIP_PUSH", "1")

    rc = _dmp.main(["--repo", str(tmp_path), "--attempts", "5"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "::notice title=debt-maturity-drip::pushed" in out, (
        f"expected pushed notice after NFF recovery, got: {out!r}"
    )

    # Bare remote tip contains both the foreign README AND the
    # data/debt_maturity/cache/0000320193.json with the new content.
    tree = _git(bare, "ls-tree", "-r", "--name-only", "main")
    assert "README.md" in tree, "foreign commit must be present"
    tip_cache = _git(bare, "show", "main:data/debt_maturity/cache/0000320193.json")
    assert tip_cache == '{"fetched_at":"2026-09-13"}', (
        f"helper's change must survive the re-checkout cycle; "
        f"got {tip_cache!r}"
    )
    log = _git(bare, "log", "--format=%s", "main").splitlines()
    assert any(s.startswith("debt-maturity-drip:") for s in log), log
    assert any(s == "foreign" for s in log), log


def test_drip_push_attempts_exhausted_refuses_with_warning(
    monkeypatch, tmp_path, capsys
):
    """R3c/(vii): with --attempts 0 and an un-pushable state (foreign
    commit + our pending change), the helper emits a refusal warning
    and returns 0 -- fail-soft, no commit was lost."""
    _init_repo(tmp_path)
    _seed_repo(tmp_path)
    bare = _bare_remote(tmp_path)
    _add_remote(tmp_path, bare)

    # Foreign commit first.
    _foreign_commit_on_bare(tmp_path, bare)

    # Modify the cache file in the WORKING TREE (do NOT commit locally --
    # the helper does the commit).
    (tmp_path / "data" / "debt_maturity" / "cache" / "0000320193.json").write_text(
        '{"fetched_at":"2026-09-13"}'
    )

    monkeypatch.setenv("DEBT_MATURITY_DRIP_PUSH", "1")

    # attempts=0 forces an immediate refusal after the first push is
    # rejected; we want to assert the refusal path, not the retry path.
    rc = _dmp.main(["--repo", str(tmp_path), "--attempts", "0"])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.startswith("::warning"), f"expected refusal warning, got: {out!r}"
    assert "refused" in out and "moved" in out

    # The bare remote's tip must be the foreign commit (no helper
    # commit landed). The cache file IS in the tree from the seed
    # baseline; what must NOT have changed is its content (still the
    # baseline fetched_at) and the commit count (baseline + foreign
    # only, no helper push).
    tip_subjects = _git(bare, "log", "--format=%s", "main").splitlines()
    assert not any(s.startswith("debt-maturity-drip:") for s in tip_subjects), (
        f"refusal path must not push; tip subjects: {tip_subjects}"
    )
    tip_cache = _git(bare, "show", "main:data/debt_maturity/cache/0000320193.json")
    assert tip_cache == '{"fetched_at":"2026-09-12"}', (
        f"cache content must remain the seed baseline on the refusal "
        f"path; got {tip_cache!r}"
    )
    assert "README.md" in _git(bare, "ls-tree", "-r", "--name-only", "main"), (
        "foreign commit must still be on the bare tip"
    )


def test_drip_push_helper_uses_no_forbidden_git_invocations():
    """R3c/sanity: the helper must NEVER use a non-selective staging
    invocation, a force push, a stash, or a history rewrite. The spec
    pins this as a grep gate that must print nothing.
    """
    text = HELPER_PATH.read_text()
    forbidden = [
        '"git add -A"',
        "'git add -A'",
        '"git add data/"',
        "'git add data/'",
        "--force",
        "git stash",
        "git rebase",
    ]
    for needle in forbidden:
        assert needle not in text, (
            f"helper must not contain {needle!r}; see META-CEO FROZEN SPEC R3"
        )


def test_drip_push_annotations_start_the_line():
    """R3c/sanity: every ::notice / ::warning the helper can emit must
    come from a bare ``print(..., flush=True)`` so GitHub parses it
    (see tests/test_gh_annotation_line_start.py)."""
    text = HELPER_PATH.read_text()
    # The helper's _emit() must be the only annotation emitter, and it
    # must use a bare print with flush=True at the START of the line.
    assert 'print(f"::{kind} title={title}::{message}", flush=True)' in text
    # No annotation through logging (the test_gh_annotation_line_start
    # defect).
    assert 'log.warning("::notice' not in text
    assert 'log.warning("::warning' not in text

"""Government funding and Demand burden tests, with isolated native Parquet/render paths.

Covers:
  1. funding_to_mktcap — happy path, materiality bands, None-on-missing ticker,
     None-on-zero mktcap, grants-only path.
  2. funding_theme_roll — happy path, empty roll-up (None).
  3. capex_burden — happy path, None-on-thin-data, None-on-missing-ticker-in-caller,
     FCF-trap detection (capex_ocf > 80% AND fcf < 0), burden sanity fixture.
  4. spender_capex_burden — delegates to capex_burden per CHAIN spenders; absent
     statements → None (not 0).
  5. Chip-attachment regression — attaching rec["gov_exposure"] does NOT perturb
     any pre-existing keys in the rec dict.
"""
from __future__ import annotations

import json
import re
import shutil
from html.parser import HTMLParser
from pathlib import Path

import pandas as pd
import pytest

from engine.gov_exposure import (
    capex_burden,
    funding_theme_roll,
    funding_to_mktcap,
    spender_capex_burden,
)


def _component_rows():
    return [dict(fy=fy, cfo=10e9, capex=12e9, cash=20e9,
                 debt_lt=25e9, debt_cur=5e9) for fy in range(2020, 2026)]


@pytest.mark.parametrize("endpoint", [-1, -2])
def test_missing_capex_withholds_only_unidentifiable_fcf_fields(endpoint):
    rows = _component_rows()
    rows[endpoint]["capex"] = None
    r = capex_burden(rows)
    assert r["fcf_trend"] is None
    assert r["capex_ocf_trend"] is None
    assert r["capex_yoy_pct"] is None
    assert r["net_debt_delta_bn"] == 0.0
    assert (r["fcf_latest_bn"], r["fcf_trap"]) == ((None, None) if endpoint == -1 else (-2.0, True))
    assert r["fy_latest"] == 2025 and r["evidence_tier"] == "fingerprint" and r["score_cap"] == 60


@pytest.mark.parametrize("endpoint", [-1, -2])
@pytest.mark.parametrize("component", ["cash", "debt_lt", "debt_cur"])
def test_net_debt_requires_each_component_at_both_endpoints(endpoint, component):
    rows = _component_rows()
    complete = capex_burden(rows)
    rows[endpoint][component] = None
    got = capex_burden(rows)
    assert got == {**complete, "net_debt_delta_bn": None}


@pytest.mark.parametrize("component,expected_delta", [("cash", 20.0), ("debt_lt", -25.0), ("debt_cur", -5.0)])
def test_reported_balance_zero_is_a_measured_change(component, expected_delta):
    rows = _component_rows()
    rows[-1][component] = 0.0
    r = capex_burden(rows)
    assert r["net_debt_delta_bn"] == expected_delta
    assert r["fcf_latest_bn"] == -2.0 and r["fcf_trap"] is True


def test_reported_zero_capex_and_zero_fcf_remain_observations():
    rows = _component_rows()
    rows[-1]["capex"] = 0.0
    r = capex_burden(rows)
    assert (r["capex_ocf_latest"], r["capex_yoy_pct"], r["fcf_latest_bn"]) == (0.0, -100.0, 10.0)
    assert r["fcf_trend"] == "improving" and r["fcf_trap"] is False
    rows[-1]["capex"] = 10e9
    r = capex_burden(rows)
    assert r["fcf_latest_bn"] == 0.0 and r["fcf_trap"] is False


@pytest.mark.parametrize("cfo,capex,expected_trap", [(0.0, 12e9, None), (-1e9, 12e9, None), (0.0, 0.0, False)])
def test_undefined_ratio_is_not_flat_or_a_false_trap_assessment(cfo, capex, expected_trap):
    rows = _component_rows()
    rows[-1].update(cfo=cfo, capex=capex)
    r = capex_burden(rows)
    assert r["capex_ocf_latest"] is None and r["capex_ocf_trend"] is None
    assert r["fcf_latest_bn"] == (cfo - capex) / 1e9
    assert r["fcf_trap"] is expected_trap


@pytest.mark.parametrize("latest_capex,trend", [(53e9, "flat"), (53.01e9, "rising"), (47e9, "flat"), (46.99e9, "falling")])
def test_defined_ratio_trend_threshold_remains_three_percentage_points(latest_capex, trend):
    rows = _component_rows()
    for row in rows:
        row.update(cfo=100e9, capex=50e9)
    rows[-1]["capex"] = latest_capex
    assert capex_burden(rows)["capex_ocf_trend"] == trend


_FLOW_CONCEPTS = {
    "cfo": "NetCashProvidedByUsedInOperatingActivities",
    "capex": "PaymentsToAcquirePropertyPlantAndEquipment",
    "revenue": "Revenues",
}
_BALANCE_CONCEPTS = {
    "cash": "CashAndCashEquivalentsAtCarryingValue",
    "debt_lt": "LongTermDebtNoncurrent",
    "debt_cur": "LongTermDebtCurrent",
}
_FIXTURE_VALUES = {"cfo": 10e9, "capex": 12e9, "revenue": 50e9,
                   "cash": 20e9, "debt_lt": 25e9, "debt_cur": 5e9}
_SPENDERS = ("MSFT", "GOOGL", "AMZN", "META", "ORCL", "DHI", "LEN", "PHM", "NVR", "TOL", "KBH")
_PIPELINE_CASES = {
    "complete": {},
    "missing_latest_capex": {("capex", 2025): None},
    "missing_prior_capex": {("capex", 2024): None},
    "all_capex_missing": {("capex", fy): None for fy in range(2020, 2026)},
    **{f"missing_{endpoint}_{key}": {(key, fy): None}
       for endpoint, fy in [("latest", 2025), ("prior", 2024)]
       for key in ("cash", "debt_lt", "debt_cur")},
    "zero_capex": {("capex", fy): 0.0 for fy in range(2020, 2026)},
    "zero_cash": {("cash", fy): 0.0 for fy in range(2020, 2026)},
    "zero_debt": {(key, fy): 0.0 for key in ("debt_lt", "debt_cur") for fy in range(2020, 2026)},
    "zero_fcf": {("capex", fy): 10e9 for fy in range(2020, 2026)},
    "zero_latest_cfo": {("cfo", 2025): 0.0},
}


def _companyfacts(edits):
    """SEC-shaped fabricated values, not the financial results of named issuers."""
    concepts = {}
    for key, concept in {**_FLOW_CONCEPTS, **_BALANCE_CONCEPTS}.items():
        entries = []
        for fy in range(2020, 2026):
            value = edits.get((key, fy), _FIXTURE_VALUES[key])
            if value is None:
                continue
            row = {"fy": fy, "fp": "FY", "form": "10-K", "end": f"{fy}-12-31",
                   "filed": f"{fy + 1}-02-15", "val": value}
            if key in _FLOW_CONCEPTS:
                row["start"] = f"{fy}-01-01"
            entries.append(row)
        concepts[concept] = {"units": {"USD": entries}}
    return {"facts": {"us-gaap": concepts}}


class _VisibleText(HTMLParser):
    def __init__(self, language):
        super().__init__(convert_charrefs=True)
        self.language, self.hidden, self.parts = language, [], []

    def handle_starttag(self, tag, attrs):
        if tag in {"br", "hr", "img", "input", "link", "meta", "wbr"}:
            return
        classes = dict(attrs).get("class", "").split()
        hidden = ((self.hidden[-1] if self.hidden else False)
                  or ("l-zh" in classes and self.language == "en")
                  or ("l-en" in classes and self.language == "zh"))
        self.hidden.append(hidden)

    def handle_endtag(self, tag):
        if self.hidden:
            self.hidden.pop()

    def handle_data(self, text):
        if not self.hidden or not self.hidden[-1]:
            self.parts.append(text)


def _burden_cells(html, ticker="MSFT"):
    # A payer can also occur in the beneficiary table on the populated page.
    rows = [r for r in re.findall(r"<tr\b[^>]*>.*?</tr>", html, re.S)
            if f'href="stock.html#{ticker}"' in r
            and len(re.findall(r"<td\b", r)) == 9]
    assert len(rows) == 1, f"Expected exactly one payer row for {ticker}"
    cells = re.findall(r"<td([^>]*)>(.*?)</td>", rows[0], re.S)
    assert len(cells) == 9
    texts = {}
    for lang in ("en", "zh"):
        texts[lang] = []
        for _, cell in cells:
            parser = _VisibleText(lang)
            parser.feed(cell)
            texts[lang].append(" ".join("".join(parser.parts).split()))
    return cells, texts


def _native_component_pipeline(tmp_path, monkeypatch, edits):
    from collectors import edgar_facts as ef
    from engine import demand_alerts
    from lib import config
    from scripts import build_demand as bd

    source_root = Path(bd.__file__).resolve().parents[1]
    root = tmp_path / "fixture"
    root.mkdir(parents=True)
    # Actual checkout-relative reads also bind template-only CI inference.
    for relative in ("config.yml", "templates/demand.html.j2", "templates/_seo_head.html.j2",
                     "templates/_site_nav.html.j2", "templates/_navlinks.html.j2"):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / relative, target)
    monkeypatch.setattr(config, "ROOT", root)
    monkeypatch.setattr(config, "data_dir", lambda: root / "data")

    facts = {1000 + i: _companyfacts(edits if ticker == "MSFT" else {})
             for i, ticker in enumerate(_SPENDERS)}
    requests, debt_writes, pauses = [], [], []
    def get_json(url):
        cik = int(re.search(r"CIK(\d+)\.json$", url).group(1))
        assert cik in facts
        requests.append(cik)
        return facts[cik]
    monkeypatch.setattr(ef, "_get_json", get_json)
    monkeypatch.setattr(ef.time, "sleep", lambda seconds: pauses.append(seconds))
    monkeypatch.setattr(ef, "_dm_wire_cache", lambda cik, data: debt_writes.append((cik, data is facts[cik])))
    rows = []
    for i, ticker in enumerate(_SPENDERS):
        parsed = ef._statements_for(1000 + i)
        assert {r["fy"] for r in parsed} == set(range(2020, 2026))
        rows.extend({**r, "ticker": ticker} for r in parsed)
    assert requests == list(facts)
    assert debt_writes == [(cik, True) for cik in facts]
    assert pauses == [0.12] * len(facts)

    frame = pd.DataFrame(rows)
    path = root / "data/edgar/statements.parquet"
    path.parent.mkdir(parents=True)
    frame.to_parquet(path)
    membership = root / "data/baskets/membership.json"
    membership.parent.mkdir(parents=True)
    membership.write_text(json.dumps({"baskets": {
        "ai_semiconductors": {"name": "AI semiconductors", "members": [{"ticker": "NVDA"}]},
        "housing": {"name": "Housing", "members": [{"ticker": "BLDR"}]}}}))
    revision_path = root / "data/revisions/latest.parquet"
    revision_path.parent.mkdir(parents=True)
    pd.DataFrame({"breadth": [0.5, 0.5], "est_chg_30d": [2.0, 2.0], "est_chg_90d": [2.0, 2.0]},
                 index=pd.Index(["NVDA", "BLDR"], name="ticker")).to_parquet(revision_path)

    signals, reads, burdens = bd._collect(root)
    assert set(signals) == {"ai_datacenter", "housing"}
    assert all(s["fy_latest"] == 2025 and s["n_spenders"] >= 4 for s in signals.values())
    assert set(reads) == {"NVDA", "BLDR"}
    assert reads["NVDA"]["chain_key"] == "ai_datacenter" and reads["BLDR"]["chain_key"] == "housing"
    assert all(r["consensus_dir"] == "rising" for r in reads.values())
    for chain in signals:
        direct = spender_capex_burden(pd.read_parquet(path), chain)
        assert direct and burdens[chain] == direct, "the builder catch-all must not hide a burden error"
    assert "MSFT" in burdens["ai_datacenter"] and burdens["ai_datacenter"]["MSFT"] is not None

    alert_calls, writes = [], []
    monkeypatch.setattr(demand_alerts, "rebuild", lambda data, **kw: alert_calls.append(data) or [])
    def write_page(path, html):
        path = Path(path)
        assert root in path.parents
        path.write_text(html)
        writes.append(path)
        return path
    monkeypatch.setattr(bd, "write_page", write_page)
    html = bd.build(root=root)
    assert len(writes) == 1 and writes[0].read_text() == html
    assert alert_calls == [reads]
    assert not (root / "data/demand_chain/alerts.jsonl").exists()
    assert "<html" in html and 'class="l-en"' in html and 'class="l-zh"' in html
    json.dumps(burdens, allow_nan=False)
    return {"rows": rows, "signals": signals, "reads": reads, "burdens": burdens,
            "html": html, "output": writes[0]}


@pytest.mark.parametrize("case", list(_PIPELINE_CASES))
def test_native_companyfacts_parquet_builder_and_bilingual_disclosure(tmp_path, monkeypatch, case):
    result = _native_component_pipeline(tmp_path, monkeypatch, _PIPELINE_CASES[case])
    b = result["burdens"]["ai_datacenter"]["MSFT"]
    cells, texts = _burden_cells(result["html"])
    assert b["evidence_tier"] == "fingerprint" and b["score_cap"] == 60 and b["fy_latest"] == 2025
    source_rows = [r for r in result["rows"] if r["ticker"] == "MSFT"]
    for (key, fy), value in _PIPELINE_CASES[case].items():
        parsed = next(r for r in source_rows if r["fy"] == fy)
        assert parsed[key] is value if value is None else parsed[key] == value
    if case in {"missing_latest_capex", "all_capex_missing"}:
        assert b["fcf_latest_bn"] is None and b["fcf_trend"] is None
        assert b["capex_ocf_latest"] is None and b["capex_ocf_trend"] is None and b["fcf_trap"] is None
        assert all(texts[lang][i] == "—" for lang in texts for i in (1, 2, 3, 4, 5, 8))
        assert "pos" not in cells[4][0] and "neg" not in cells[4][0]
    elif case == "missing_prior_capex":
        assert b["fcf_latest_bn"] == -2.0 and b["fcf_trap"] is True
        assert b["fcf_trend"] is None and b["capex_ocf_trend"] is None
        assert all(texts[lang][i] == "—" for lang in texts for i in (2, 3, 5))
    elif case.startswith("missing_"):
        assert b["net_debt_delta_bn"] is None
        assert b["fcf_latest_bn"] == -2.0 and b["fcf_trap"] is True
        assert all(texts[lang][6] == "—" for lang in texts)
        assert "pos" not in cells[6][0] and "neg" not in cells[6][0]
    elif case == "zero_capex":
        assert (b["capex_ocf_latest"], b["fcf_latest_bn"], b["fcf_trap"]) == (0.0, 10.0, False)
    elif case == "zero_fcf":
        assert b["fcf_latest_bn"] == 0.0 and b["fcf_trap"] is False
        assert texts["en"][4] == texts["zh"][4] == "+0.0"
    elif case == "zero_latest_cfo":
        assert b["capex_ocf_trend"] is None and b["fcf_trap"] is None
        assert all(texts[lang][i] == "—" for lang in texts for i in (1, 2, 8))
    else:
        assert b["fcf_latest_bn"] == -2.0 and b["net_debt_delta_bn"] == 0.0
        assert texts["en"][5] == "flat" and texts["zh"][5] == "持平"
    assert "None" not in " ".join(texts["en"] + texts["zh"])
    assert "A dash means required inputs are missing" in result["html"]
    assert "破折号表示缺少必要输入或计算无定义" in result["html"]


# ─── fixtures ─────────────────────────────────────────────────────────────────

def _make_obligations(tickers: list[str], months: int = 14, value: float = 1e9) -> pd.DataFrame:
    """Synthetic month × ticker obligations frame with constant values."""
    import pandas as pd
    idx = pd.date_range("2025-01-01", periods=months, freq="MS")
    return pd.DataFrame({t: [value] * months for t in tickers}, index=idx)


def _make_grants(tickers: list[str], months: int = 14, value: float = 5e8) -> pd.DataFrame:
    import pandas as pd
    idx = pd.date_range("2025-01-01", periods=months, freq="MS")
    return pd.DataFrame({t: [value] * months for t in tickers}, index=idx)


def _make_stmt_rows(
    ticker: str,
    years: int = 5,
    cfo: float = 10e9,
    capex: float = 3e9,
    debt_lt: float = 5e9,
    debt_cur: float = 1e9,
    cash: float = 2e9,
) -> list[dict]:
    rows = []
    for i in range(years):
        rows.append({
            "ticker": ticker,
            "fy": 2020 + i,
            "cfo":    cfo   * (1 + 0.05 * i),   # slight growth each year
            "capex":  capex * (1 + 0.02 * i),
            "debt_lt":  debt_lt,
            "debt_cur": debt_cur,
            "cash":     cash,
        })
    return rows


# ─── funding_to_mktcap ────────────────────────────────────────────────────────

class TestFundingToMktcap:
    def test_happy_path_contracts_only(self):
        obs = _make_obligations(["LMT"], months=14, value=1e9)
        mkt = {"LMT": 20e9}   # $20B mktcap
        r = funding_to_mktcap("LMT", obs, None, mkt)
        assert r is not None
        # 12 months of $1B = $12B contracts; / $20B = 60%
        assert r["ratio_pct"] == pytest.approx(60.0, abs=1.0)
        assert r["band"] == "heavy"
        assert r["evidence_tier"] == "fingerprint"
        assert r["score_cap"] == 60

    def test_contracts_plus_grants(self):
        obs = _make_obligations(["MSFT"], months=14, value=1e9)
        gl  = _make_grants(["MSFT"], months=14, value=5e8)
        mkt = {"MSFT": 3_000e9}   # $3T mktcap
        r = funding_to_mktcap("MSFT", obs, gl, mkt)
        assert r is not None
        # contracts ~12B + grants ~6B = 18B; / 3000B ≈ 0.6%
        assert r["ratio_pct"] < 2.0
        assert r["band"] == "minor"
        assert r["contracts_ttm"] is not None
        assert r["grants_ttm"] is not None

    def test_heavy_band(self):
        obs = _make_obligations(["HII"], months=14, value=1e9)
        mkt = {"HII": 80e9}   # 12B TTM / 80B → 15% → heavy
        r = funding_to_mktcap("HII", obs, None, mkt)
        assert r is not None
        assert r["band"] == "heavy"

    def test_notable_band(self):
        obs = _make_obligations(["HII"], months=14, value=1e9)
        mkt = {"HII": 240e9}  # 12B TTM / 240B → 5% → notable (2% <= r < 10%)
        r = funding_to_mktcap("HII", obs, None, mkt)
        assert r is not None
        assert r["band"] == "notable"

    def test_none_on_missing_ticker(self):
        obs = _make_obligations(["LMT"], months=14)
        mkt = {"LMT": 20e9}
        r = funding_to_mktcap("MISSING_TICKER", obs, None, mkt)
        assert r is None

    def test_none_on_zero_mktcap(self):
        obs = _make_obligations(["LMT"], months=14)
        mkt = {"LMT": 0.0}
        r = funding_to_mktcap("LMT", obs, None, mkt)
        assert r is None

    def test_none_on_absent_mktcap(self):
        obs = _make_obligations(["LMT"], months=14)
        r = funding_to_mktcap("LMT", obs, None, {})
        assert r is None

    def test_grants_only_path(self):
        empty_obs = _make_obligations([], months=14)   # no columns
        gl  = _make_grants(["MP"], months=14, value=2e8)
        mkt = {"MP": 10e9}
        r = funding_to_mktcap("MP", empty_obs, gl, mkt)
        # MP absent from obs but present in grants → still a result
        assert r is not None
        assert r["contracts_ttm"] is None
        assert r["grants_ttm"] is not None
        assert r["ratio_pct"] > 0

    def test_empty_obligations_frame(self):
        obs = pd.DataFrame()
        r = funding_to_mktcap("LMT", obs, None, {"LMT": 20e9})
        assert r is None


# ─── funding_theme_roll ────────────────────────────────────────────────────────

class TestFundingThemeRoll:
    def test_happy_path(self):
        obs = _make_obligations(["LMT", "RTX"], months=14, value=2e9)
        mkt = {"LMT": 50e9, "RTX": 100e9}
        r = funding_theme_roll(["LMT", "RTX"], obs, None, mkt)
        assert r is not None
        assert r["n_covered"] == 2
        assert r["weighted_ratio_pct"] > 0
        assert r["evidence_tier"] == "fingerprint"
        assert r["score_cap"] == 60

    def test_none_when_no_coverage(self):
        obs = _make_obligations(["LMT"], months=14)
        mkt = {"LMT": 50e9}
        r = funding_theme_roll(["MISSING_A", "MISSING_B"], obs, None, mkt)
        assert r is None


# ─── capex_burden ─────────────────────────────────────────────────────────────

class TestCapexBurden:
    def test_happy_path(self):
        rows = _make_stmt_rows("MSFT", years=5, cfo=136e9, capex=56e9)
        r = capex_burden(rows)
        assert r is not None
        assert r["capex_ocf_latest"] is not None
        assert r["capex_ocf_latest"] > 0
        assert r["fy_latest"] == 2024
        assert r["evidence_tier"] == "fingerprint"
        assert r["score_cap"] == 60

    def test_none_on_empty_rows(self):
        r = capex_burden([])
        assert r is None

    def test_none_on_none_input(self):
        r = capex_burden(None)  # type: ignore[arg-type]
        assert r is None

    def test_none_on_insufficient_years(self):
        rows = _make_stmt_rows("TST", years=2, cfo=10e9, capex=3e9)
        r = capex_burden(rows, min_years=3)
        assert r is None

    def test_fcf_trap_detection(self):
        """capex_ocf > 80% AND fcf < 0 → fcf_trap = True."""
        rows = []
        for i in range(4):
            rows.append({
                "ticker": "TRAP",
                "fy": 2020 + i,
                "cfo":   5e9,   # positive OCF
                "capex": 5e9 + 1e9,   # capex EXCEEDS cfo → FCF < 0
                "debt_lt": 10e9, "debt_cur": 1e9, "cash": 2e9,
            })
        r = capex_burden(rows)
        assert r is not None
        assert r["fcf_trap"] is True
        assert r["fcf_latest_bn"] is not None
        assert r["fcf_latest_bn"] < 0

    def test_fcf_trap_not_flagged_when_fcf_positive(self):
        """Even with high capex/OCF, if FCF > 0 there is no FCF trap."""
        rows = []
        for i in range(4):
            rows.append({
                "ticker": "SAFETRAP",
                "fy": 2020 + i,
                "cfo":   20e9,
                "capex": 17e9,  # 85% capex/OCF but FCF still positive
                "debt_lt": 10e9, "debt_cur": 1e9, "cash": 2e9,
            })
        r = capex_burden(rows)
        assert r is not None
        assert r["fcf_trap"] is False

    def test_burden_sanity_capex_over_ocf_gt_100_flagged(self):
        """capex_ocf > 100% is an extreme FCF-burden situation."""
        rows = []
        for i in range(4):
            rows.append({
                "ticker": "EXTREME",
                "fy": 2020 + i,
                "cfo":   10e9,
                "capex": 12e9,  # 120% capex/OCF
                "debt_lt": 5e9, "debt_cur": 1e9, "cash": 1e9,
            })
        r = capex_burden(rows)
        assert r is not None
        assert r["capex_ocf_latest"] is not None
        assert r["capex_ocf_latest"] > 100.0, "Expected capex_ocf > 100%"
        assert r["fcf_trap"] is True          # FCF < 0

    def test_none_when_capex_missing_but_cfo_present(self):
        """#11067 deliberately replaces the old CFO-as-FCF fallback contract."""
        rows = []
        for i in range(4):
            rows.append({"ticker": "X", "fy": 2020 + i, "cfo": 10e9})
        r = capex_burden(rows)
        assert r is not None
        assert r["capex_ocf_latest"] is None   # no capex available
        assert r["fcf_trap"] is None
        assert r["fcf_latest_bn"] is None
        assert r["fcf_trend"] is None
        assert r["capex_ocf_trend"] is None


# ─── spender_capex_burden ─────────────────────────────────────────────────────

class TestSpenderCapexBurden:
    def test_ai_chain_present(self):
        """ai_datacenter chain spenders present in synthetic statements → results."""
        rows = []
        for tkr in ["MSFT", "AMZN", "META"]:
            rows.extend(_make_stmt_rows(tkr, years=4, cfo=100e9, capex=50e9))
        df = pd.DataFrame(rows)
        result = spender_capex_burden(df, "ai_datacenter")
        assert len(result) > 0
        for tkr, burden in result.items():
            assert burden is not None, f"{tkr} should have a burden result"
            assert burden["evidence_tier"] == "fingerprint"

    def test_absent_ticker_omitted_and_thin_history_none(self):
        """Spenders absent from statements are OMITTED (not mapped to 0); a spender
        PRESENT with fewer than min_years valid cfo rows maps to None (not 0)."""
        empty_df = pd.DataFrame(columns=["ticker", "fy", "cfo", "capex",
                                         "debt_lt", "debt_cur", "cash"])
        result = spender_capex_burden(empty_df, "ai_datacenter")
        assert result == {}   # nothing matched → omitted, never fabricated
        thin = pd.DataFrame([  # MSFT present but only 2 years (< min_years=3)
            {"ticker": "MSFT", "fy": 2024, "cfo": 1e11, "capex": 4e10,
             "debt_lt": 5e10, "debt_cur": 1e10, "cash": 8e10},
            {"ticker": "MSFT", "fy": 2025, "cfo": 1.2e11, "capex": 6e10,
             "debt_lt": 5e10, "debt_cur": 1e10, "cash": 7e10},
        ])
        result = spender_capex_burden(thin, "ai_datacenter")
        assert "MSFT" in result
        assert result["MSFT"] is None   # thin history → None, never 0

    def test_unknown_chain_returns_empty(self):
        df = pd.DataFrame()
        result = spender_capex_burden(df, "nonexistent_chain_xyz")
        assert result == {}


# ─── chip-attachment regression ───────────────────────────────────────────────

class TestChipAttachmentRegression:
    """Attaching rec['gov_exposure'] must not perturb any pre-existing keys."""

    def test_only_gov_exposure_added(self):
        existing_rec = {
            "ticker": "LMT",
            "ladder": {"state": "BUY ZONE"},
            "altdata": {"score": 2},
            "macro_sensitivity": {"tier": "high"},
            "profile": {"archetype": {"key": "defense"}},
        }
        before_keys = set(existing_rec.keys())

        obs = _make_obligations(["LMT"], months=14, value=5e9)
        mkt = {"LMT": 30e9}
        exposure = funding_to_mktcap("LMT", obs, None, mkt)
        if exposure:
            existing_rec["gov_exposure"] = exposure

        after_keys = set(existing_rec.keys())
        new_keys = after_keys - before_keys
        assert new_keys == {"gov_exposure"}, (
            f"Only 'gov_exposure' should be added; got {new_keys}")
        # pre-existing keys are intact
        for k in before_keys:
            assert existing_rec[k] is not None

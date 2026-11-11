"""Methodology page: print what the committed artifacts actually say (lane W23-L3).

One class per accepted design spec (DESIGN.md §3 SPEC 1-4) plus the fail-open contract:
TestBackProjection, TestIcPanelBasis, TestSeasonalityYears, TestBasketPriceBasis,
TestFailOpen. Fixtures are inline dicts carrying exactly the seat-quoted values of the
committed copies (site/basketdata/baskets.json, data/edgar/ic_scorecard.json,
site/factordata/factor_seasonality.json at seed c3c67487). No network, no site/ or
data/ read, and never a call to main() (it writes site/methodology.html).
"""
from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from scripts import build_methodology as bm

ROOT = Path(__file__).resolve().parents[1]

# ---- seed sentences an unwired branch must reproduce verbatim ------------------------
SEED_TOTAL = "Returns are total returns (split- and dividend-adjusted prices)."
SEED_HORIZON63 = "<b>next 63-day return</b>"
SEED_IC_GAP = "that gap <i>is</i> the look-ahead/survivorship bias being removed"
SEED_JUDGE = "Judge every number against zero, and against n≈11."
SEED_HINDSIGHT = ("membership was curated knowing the period, so the full ~3y series is a backtest "
                  "of the as-of-creation membership")
SEED_NOT_TRACK = "an out-of-sample track and not a buy list"
SEED_SEASONS = "(Momentum 1927+, Value/Size/Profitability/Investment 1963+)"
SEED_WINDOW30 = "over both full history and a trailing-30-year window."
SEED_MILD = "mild survivorship bias"
SEED_UNIVERSE = "so the series is mildly <b>survivorship-biased</b> upward — stated, not hidden."
NEW_KEYS = ("bk_series_start", "bk_n_back_projected", "bk_n_total", "ic_survivorship_biased",
            "ic_universe_kind", "ic_price_span", "ic_horizon_d", "ic_survivors",
            "seasonality_styles", "seasonality_window_years", "bk_price_resolution",
            "bk_n_partial", "bk_n_observed", "bk_min_coverage")
PRICE_RESOLUTION = {"requested_n": 713, "resolved_n": 711, "unresolved_n": 2,
                    "unresolved_tickers": ["MAG", "GATO"],
                    "source_basis": {"primary_breadth": "closes_cache_UNADJUSTED",
                                     "baskets_extras": "tradj"},
                    "adjustment_vintage": "unrecorded", "authority": "measurement_only"}
SEAS_SPEC = [("value", "Value (HML)", "价值 (HML)", "1926-07", 1202),
             ("profitability", "Profitability (RMW)", "盈利 (RMW)", "1963-07", 758),
             ("investment", "Investment (CMA)", "投资 (CMA)", "1963-07", 758),
             ("momentum", "Momentum (Mom)", "动量 (Mom)", "1927-01", 1196),
             ("size", "Size (SMB)", "规模 (SMB)", "1926-07", 1202),
             ("market", "Market (Mkt-RF)", "市场 (Mkt-RF)", "1926-07", 1202)]

# ---- helpers -------------------------------------------------------------------------
def build(ic=None, fs=None, bk=None, seas=None):
    """The pure builder under test (Item 1). RED until `_build_meth` exists."""
    fn = getattr(bm, "_build_meth", None)
    assert callable(fn), "scripts/build_methodology.py must expose _build_meth(ic, fs, bk, seas)"
    return fn(ic or {}, fs or {}, bk or {}, seas or {})


def render(meth):
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True)
    return env.get_template("methodology.html.j2").render(
        meth=meth, generated_utc="2026-10-19 00:00 UTC")


def section(html, anchor):
    match = re.search(r'<h2 id="%s".*?(?=<h2 id="|\Z)' % anchor, html, re.S)
    assert match, "no #%s section in the rendered page" % anchor
    return match.group(0)


def flat(text):
    return " ".join(text.split())


def langs(fragment):
    grab = lambda rx: flat(" ".join(re.findall(rx, fragment, re.S)))
    return grab(r'<span class="l-en">(.*?)</span>'), grab(r'<span class="l-zh">(.*?)</span>')


def wo(d, key):
    return {k: v for k, v in d.items() if k != key}


def basket(bid, created, status="complete", coverage=1.0, observed_n=4, configured_n=4):
    obs = {"status": status, "coverage": coverage, "observed_n": observed_n}
    return {"id": bid, "created": created, "observation": dict(obs, configured_n=configured_n)}


def bk_full():
    """49 baskets: 35 created after the 2023-09-11 start, 22 partial, crypto 5/7 floor."""
    rows = [basket("crypto", "2026-06-15", "partial", 0.7143, 5, 7)]
    rows += [basket("late_p%02d" % i, "2026-06-19", "partial", 0.8, 4, 5) for i in range(21)]
    rows += [basket("late_c%02d" % i, "2026-06-20") for i in range(13)]
    rows += [basket("early_c%02d" % i, "2023-05-09", coverage=1.0, observed_n=6, configured_n=6)
             for i in range(14)]
    return {"as_of": "2026-10-14", "categories": [{"id": "cat%d" % i} for i in range(15)],
            "chart": {"dates": ["2023-09-11", "2023-09-12", "2023-09-13"]},
            "baskets": rows, "price_resolution": PRICE_RESOLUTION}


def ic_deep():
    return {"span": "2011-03-31..2025-12-31", "rebalances": 60, "median_universe": 1154,
            "survivorship_biased": True, "universe": "deep",
            "price_span": "1962-01-02..2026-06-17", "horizon_d": 63, "leak_free": True,
            "factors": {"payout": {"mean_ic": 0.0247, "t_hac": 2.723, "q_fdr": 0.0715,
                                   "survives_fdr": True},
                        "sue": {"mean_ic": 0.0006, "q_fdr": 0.9482, "survives_fdr": False}}}


def seas_v2(with_10y=True):
    rows = [{"key": k, "label_en": en, "label_zh": zh, "start": start, "n_months": n,
             "full": {}, "trailing_30y": {}} for k, en, zh, start, n in SEAS_SPEC]
    if with_10y:
        for row in rows:
            row["trailing_10y"] = {}
    return {"schema": "factor_seasonality.v2", "as_of": "2026-08", "trailing_years": 30,
            "factors": rows}


def fs_min():
    return {"as_of": "2026-10-14", "factors": ["value"] * 8,
            "chart_data": {"sector": {"s%d" % i: [] for i in range(11)}}}


def wired():
    return build(ic_deep(), fs_min(), bk_full(), seas_v2())


# ---- SPEC 1: the basket line is back-projected, with the real count -------------------
class TestBackProjection:
    def test_counts_derive_from_the_committed_shape(self):
        meth = wired()
        assert meth["bk_series_start"] == "2023-09-11"
        assert meth["bk_n_back_projected"] == 35 and meth["bk_n_total"] == 49

    def test_the_panel_prints_the_counts_and_drops_the_as_of_claim(self):
        frag = section(render(wired()), "baskets")
        assert "35 of 49" in flat(frag) and "2023-09-11" in flat(frag)
        assert ("carried backward" in flat(frag) and SEED_NOT_TRACK in flat(frag)
                and "as-of-creation membership" not in flat(frag))
        en, zh = langs(frag)
        assert "carried backward" in en and "回溯" in zh  # both toggles

    def test_created_equal_to_series_start_is_not_back_projected(self):
        bk = {"chart": {"dates": ["2023-09-11"]}, "baskets":
              [basket("on_seed", "2023-09-11"), basket("later", "2023-09-12")]}
        meth = build(ic_deep(), fs_min(), bk, seas_v2())
        assert meth["bk_n_back_projected"] == 1 and meth["bk_n_total"] == 2

    def test_missing_chart_or_empty_baskets_falls_back_to_the_seed_sentence(self):
        for bk in ({"baskets": [basket("no_dates", "2026-06-19")]},
                   {"chart": {"dates": ["2023-09-11"]}, "baskets": []}):
            meth = build(ic_deep(), fs_min(), bk, seas_v2())
            assert meth["bk_series_start"] is None
            assert meth["bk_n_back_projected"] is None and meth["bk_n_total"] is None
            got = flat(section(render(meth), "baskets"))
            assert SEED_HINDSIGHT in got and "carried backward" not in got


# ---- SPEC 2: the IC read is a deep, survivorship-biased panel -------------------------
class TestIcPanelBasis:
    def test_basis_keys_come_from_the_artifact(self):
        meth = wired()
        assert meth["ic_survivorship_biased"] is True and meth["ic_universe_kind"] == "deep"
        assert meth["ic_price_span"] == "1962-01-02..2026-06-17"
        assert meth["ic_horizon_d"] == 63
        assert meth["ic_survivors"] == [{"name": "payout", "q_fdr": 0.0715}]
        for bad in ("true", 1, None):   # the flag is read only as a real bool
            gone = build(dict(ic_deep(), survivorship_biased=bad), fs_min(), bk_full(),
                         seas_v2())["ic_survivorship_biased"]
            assert gone is None, bad

    def test_panel_names_the_basis_the_survivor_and_keeps_the_judge_clause(self):
        got = flat(section(render(wired()), "ic"))
        for token in ("deep", "1962-01-02..2026-06-17", "payout", "0.0715", "optimistic bound"):
            assert token in got, token
        assert "Judge every number against zero, and against n≈60." in got
        assert "look-ahead/survivorship bias being removed" not in got

    def test_survivors_are_read_from_the_factor_rows(self):
        ic = ic_deep()
        ic["factors"] = {"zeta": {"q_fdr": 0.041, "survives_fdr": True},
                         "alpha": {"q_fdr": 0.09, "survives_fdr": True},
                         "payout": {"q_fdr": 0.5, "survives_fdr": False}}
        meth = build(ic, fs_min(), bk_full(), seas_v2())
        assert [s["name"] for s in meth["ic_survivors"]] == ["zeta", "alpha"]
        got = flat(section(render(meth), "ic"))
        assert "zeta" in got and "0.041" in got and "alpha" in got and "0.09" in got
        assert "payout" not in got
        ic["factors"] = {"sue": {"q_fdr": 0.9482, "survives_fdr": False}}
        meth = build(ic, fs_min(), bk_full(), seas_v2())
        assert meth["ic_survivors"] == []
        assert "no factor clears BH-FDR(10%)" in flat(section(render(meth), "ic"))

    def test_horizon_d_is_printed_and_absent_falls_back_to_the_seed_literal(self):
        meth = build(dict(ic_deep(), horizon_d=21), fs_min(), bk_full(), seas_v2())
        assert meth["ic_horizon_d"] == 21
        assert "next 21-day return" in flat(section(render(meth), "ic"))
        meth = build(wo(ic_deep(), "horizon_d"), fs_min(), bk_full(), seas_v2())
        assert meth["ic_horizon_d"] is None
        assert SEED_HORIZON63 in flat(section(render(meth), "ic"))

    def test_limits_bullet_names_the_bound_and_the_universe_page_stays(self):
        page = render(wired())
        assert "survivorship bias (IC panel: an optimistic bound)" in flat(section(page, "limits"))
        assert SEED_MILD not in flat(section(page, "limits"))
        assert SEED_UNIVERSE in flat(section(page, "universe"))

    def test_false_bias_keeps_the_seed_panel_and_limits(self):
        meth = build(dict(ic_deep(), survivorship_biased=False), fs_min(), bk_full(), seas_v2())
        page = render(meth)
        assert SEED_IC_GAP in flat(section(page, "ic"))
        assert "optimistic bound" not in flat(section(page, "ic"))
        assert SEED_MILD in flat(section(page, "limits"))


# ---- SPEC 3: the per-style starts come from the committed artifact --------------------
class TestSeasonalityYears:
    def test_styles_and_windows_pass_through_in_artifact_order(self):
        meth = wired()
        assert meth["seasonality_styles"][0] == {
            "label_en": "Value (HML)", "label_zh": "价值 (HML)", "start": "1926-07",
            "n_months": 1202}
        assert [s["start"] for s in meth["seasonality_styles"]] == [
            "1926-07", "1963-07", "1963-07", "1927-01", "1926-07", "1926-07"]
        assert meth["seasonality_window_years"] == [30, 10]  # descending

    def test_per_style_starts_render_and_the_wrong_grouping_is_gone(self):
        frag = section(render(wired()), "seasonality")
        got = flat(frag)
        assert "Value (HML)" in got and "1926-07" in got and "1202" in got
        assert "Profitability (RMW)" in got and "1963-07" in got and "758" in got
        assert "Momentum (Mom)" in got and "1927-01" in got and "1196" in got
        assert "Value/Size/Profitability/Investment 1963+" not in got
        en, zh = langs(frag)
        assert "Value (HML)" in en and "价值 (HML)" in zh  # both toggles

    def test_window_set_comes_from_the_artifact_keys(self):
        only_30 = build({}, fs_min(), {}, seas_v2(with_10y=False))
        assert only_30["seasonality_window_years"] == [30]
        got = flat(section(render(only_30), "seasonality"))
        assert "trailing-30-year" in got and "10-year" not in got
        seas = seas_v2()
        for row in seas["factors"]:
            row["trailing_5y"] = {}
        assert build({}, fs_min(), {}, seas)["seasonality_window_years"] == [30, 10, 5]

    def test_wrong_schema_keeps_the_seed_sentence(self):
        meth = build({}, fs_min(), {}, dict(seas_v2(), schema="factor_seasonality.v1"))
        assert meth["seasonality_styles"] is None and meth["seasonality_window_years"] is None
        got = flat(section(render(meth), "seasonality"))
        assert SEED_SEASONS in got and SEED_WINDOW30 in got


# ---- SPEC 4: the basket panel's price basis and partial coverage ---------------------
class TestBasketPriceBasis:
    def test_resolution_subset_is_scoped_to_the_recorded_keys(self):
        assert wired()["bk_price_resolution"] == {
            "requested_n": 713, "resolved_n": 711, "unresolved_n": 2,
            "unresolved_tickers": ["MAG", "GATO"],
            "source_basis": {"primary_breadth": "closes_cache_UNADJUSTED",
                             "baskets_extras": "tradj"},
            "adjustment_vintage": "unrecorded"}

    def test_observation_counts_and_the_coverage_floor(self):
        meth = wired()
        assert (meth["bk_n_partial"], meth["bk_n_observed"]) == (22, 49)
        assert meth["bk_min_coverage"] == {"id": "crypto", "observed_n": 5, "configured_n": 7}

    def test_basis_panel_renders_the_recorded_basis_the_split_and_the_floor(self):
        page = render(wired())
        got = flat(section(page, "baskets"))
        assert "711 of 713" in got and "MAG" in got and "GATO" in got
        assert "unrecorded" in got and "<code>primary_breadth=closes_cache_UNADJUSTED" in got
        assert "<code>baskets_extras=tradj</code>" in got
        assert "22 of 49 baskets priced on a partial member set" in got
        assert "<code>crypto</code> 5/7." in got
        horizons = flat(section(page, "horizons"))
        assert SEED_TOTAL not in horizons
        assert "on the factor suite" in horizons and "Thematic baskets" in horizons

    def test_absent_basis_renders_nothing_and_zero_unresolved_drops_its_clause(self):
        bk = {"chart": {"dates": ["2023-09-11"]},
              "baskets": [{"id": "plain", "created": "2026-06-19"}, {"id": "x2"}]}
        meth = build(ic_deep(), fs_min(), bk, seas_v2())
        assert meth["bk_price_resolution"] is None
        assert (meth["bk_n_partial"], meth["bk_n_observed"],
                meth["bk_min_coverage"]) == (None, None, None)
        page = render(meth)
        assert "priced on a partial member set" not in flat(section(page, "baskets"))
        assert SEED_TOTAL in flat(section(page, "horizons"))
        pr = dict(PRICE_RESOLUTION, unresolved_n=0, unresolved_tickers=[])
        got = flat(section(render(build(ic_deep(), fs_min(),
                                      dict(bk_full(), price_resolution=pr), seas_v2())),
                           "baskets"))
        assert "711 of 713" in got and "unresolved" not in got and "MAG" not in got


# ---- fail open: nothing wired, the page is the seed page ------------------------------
class TestFailOpen:
    def test_the_nine_seed_defaults_are_untouched(self):
        meth = build()
        assert meth["as_of"] == "—" and meth["n_factors"] == 8
        assert meth["n_baskets"] == 14 and meth["n_categories"] == 7
        assert meth["n_sectors"] == 11 and meth["ic_rebalances"] == 11
        assert meth["ic_universe"] == 1300 and meth["ic_any_survive"] is False
        assert meth["ic_span"] == "the free-data window"

    def test_every_new_key_is_none_never_a_fabricated_value(self):
        meth = build()
        for key in NEW_KEYS:
            assert key in meth, key
            assert meth[key] is None, "%s defaults to %r" % (key, meth[key])

    def test_the_unwired_page_is_the_seed_page_with_no_placeholders(self):
        page = render(build())
        for seed in (SEED_TOTAL, SEED_HORIZON63, SEED_IC_GAP, SEED_JUDGE, SEED_HINDSIGHT,
                     SEED_SEASONS, SEED_WINDOW30, SEED_MILD, SEED_NOT_TRACK):
            assert seed in flat(page), seed
        for added in ("optimistic bound", "carried backward", "partial member set"):
            assert added not in page, added
        assert "None" not in page and "NaN" not in section(page, "baskets")

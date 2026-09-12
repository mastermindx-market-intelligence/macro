"""Thematic flow detector (engine/group_flow.py) — DISPLAY-ONLY characterization layer.

The load-bearing invariants: it is NEVER scored (nothing in axes/regime/conditions reads
it), every group is directional=false (the unbiased Phase-0 verdict is display_only), the
one-name HHI guard catches single-stock mirages, the universe-bias cap keeps hindsight
baskets below clean sectors, and the AI-handoff payload carries the do-not-conclude
guardrails + caveats so a downstream inference layer cannot over-trust it."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import baskets as bk  # noqa: E402
from engine import group_flow as gf  # noqa: E402
from engine import theme_scoring as ts  # noqa: E402
from lib.closes_panel import merge_close_caches  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"
CFG = gf._cfg({})


# ---- staging (no wrong-signed 'exhausted'; 'cooling' carries no exit call) ----
def test_stage_lifecycle_uses_cooling_not_exhausted():
    assert gf._stage(0.6, 0.5, 0.3, CFG) == "emerging"
    assert gf._stage(0.0, 0.85, 0.0, CFG) == "confirmed"
    assert gf._stage(-0.6, 0.6, -0.3, CFG) == "cooling"
    assert gf._stage(0.0, 0.5, 0.0, CFG) == "quiet"
    for args in [(0.6, 0.5, 0.3), (0.0, 0.85, 0.0), (-0.6, 0.6, -0.3), (0.0, 0.5, 0.0)]:
        assert gf._stage(*args, CFG) != "exhausted"


# ---- read-quality: universe cap + HHI one-name penalty ----
def test_read_quality_universe_cap_and_hhi_penalty():
    fp = {"breadth": 0.7, "cohesion": 0.4}
    sec = gf._read_quality(fp, 15, 1.0, False)
    bas = gf._read_quality(fp, 15, 0.55, False)
    assert bas < sec                                   # hindsight baskets capped below clean sectors
    narrow = gf._read_quality(fp, 15, 1.0, True)       # one name dominates
    assert narrow < sec
    assert 0.0 <= bas <= 1.0 and 0.0 <= sec <= 1.0


# ---- cluster map: real co-movement structure ----
def test_cluster_map_detects_comoving_cluster():
    idx = pd.bdate_range("2024-01-01", periods=120)
    rng = np.random.default_rng(0)
    common = rng.normal(0, 0.01, 120)
    levels = {}
    for g in ("A", "B", "C"):                          # co-moving cluster
        levels[g] = pd.Series((1 + (common + rng.normal(0, 0.002, 120))).cumprod(), index=idx)
    for g in ("D", "E"):                               # independent
        levels[g] = pd.Series((1 + rng.normal(0, 0.01, 120)).cumprod(), index=idx)
    cl = gf._cluster_map(levels, CFG)
    assert cl is not None
    assert 0.0 < cl["absorption"] <= 1.0
    assert cl["regime"] in ("concentrated", "mixed", "broad")
    assert set(cl["top_pair"]) <= {"A", "B", "C"}      # the tightest pair is inside the cluster


# ---- leadership: HHI flags a one-name mirage ----
def test_leadership_hhi_guard_flags_one_name():
    idx = pd.bdate_range("2024-01-01", periods=30)
    flat = np.ones(30)
    df = pd.DataFrame({f"N{i}": flat * (1 + 0.0001 * i) for i in range(6)}, index=idx)
    moon = flat.copy(); moon[-1] = 2.0                 # one name doubles -> mirage
    df["MOON"] = moon
    lead = gf._leadership(df, {}, {"MOON": ("Moonshot", "")})
    assert lead["top"][0]["ticker"] == "MOON"
    assert lead["breadth"] == "narrow" and lead["hhi"] > 0.5


# ---- AI handoff: guardrails + caveats travel ----
def test_ai_handoff_carries_guardrails():
    meta = {"verdict": "display_only", "cohesion_caveats": ["c1", "c2"],
            "residual_risks": ["r1"], "cohesion_gate": {"tier": "low"},
            "survivorship_gap_20d": {"flow_score": 0.09}}
    h = gf._ai_handoff(meta, {"elevated": False})
    assert h["overall_verdict"] == "display_only"
    assert isinstance(h["do_not_conclude"], list) and len(h["do_not_conclude"]) >= 3
    assert "directional" in h["ai_directive"].lower()
    assert h["caveats"] == ["c1", "c2"] and h["residual_risks"] == ["r1"]


# ---- integration on the real cache (skips if data absent) ----
def test_compute_group_flows_is_display_only_and_structured():
    p = gf.compute_group_flows()
    if p is None:
        import pytest
        pytest.skip("no equity cache in this checkout")
    assert p["verdict"] == "display_only" and p["calibrated"] is False
    assert p["sectors"] and p["baskets"] and p["ai_handoff"]
    assert "groups" not in p                           # no combined cross-universe ranking ships
    assert isinstance(p["emerging"], dict) and set(p["emerging"]) == {"sectors", "baskets"}
    for g in p["sectors"] + p["baskets"]:
        assert g["directional"] is False              # never a forecast
        assert g["directional_confidence"] == "low"
        assert 0.0 <= g["read_quality"] <= 1.0
        assert g["type"] in ("sector", "basket")
        assert "cohesion_gate" in g and "leadership" in g
    # sector read-quality should not be capped below baskets by construction
    assert max(g["read_quality"] for g in p["sectors"]) >= max(g["read_quality"] for g in p["baskets"])


# ---- the validated-honest metadata (skips if not generated) ----
def test_validation_meta_is_honest():
    from lib import config
    mp = config.data_dir() / "group_flow" / "validation_meta.json"
    if not mp.exists():
        import pytest
        pytest.skip("validation_meta.json not generated")
    import json
    m = json.loads(mp.read_text())
    assert m["verdict"] == "display_only"
    assert all(w == 0.0 for w in m["forecast_weights"].values())   # NO leg earns a forecast weight
    assert m["cohesion_gate"]["use"] == "context_gate"
    assert m["calibrated"] is False and len(m["cohesion_caveats"]) >= 5


# ---- DISPLAY-ONLY invariant: the scoring path must not import the detector ----
def test_never_scored_invariant():
    for mod in ("engine/axes.py", "engine/regime.py", "engine/conditions.py"):
        assert "group_flow" not in (ROOT / mod).read_text(), f"{mod} must not import group_flow"


# ---- the baskets.html.j2 money-flow surface ----
#
# These render the REAL template end-to-end.  The previous version sliced a fragment
# out of the template SOURCE on literal `{% if flow %}` .. `<div id="content">`
# offsets; #3282 (Rotation Map revamp, 2026-07-24) rebuilt the standalone "Flow lens"
# card into the Money-flow tile under "Under the hood", `{% if flow %}` stopped
# existing, and the slice raised ValueError from that day on — unnoticed, because no
# CI job named this suite.  A full render cannot rot the same way: it has no literal
# offsets to miss, and a template that stops rendering fails here with the real Jinja
# error instead of a substring-not-found from the harness.
def _render_baskets(flow=None):
    from jinja2 import Environment, FileSystemLoader, Undefined
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=True,
                      undefined=Undefined)
    ctx = {"basket_member_syms": []}
    if flow is not None:
        ctx["flow"] = flow
    return env.get_template("sector_central.html.j2").render(**ctx)


def _money_flow_card(html):
    """Slice the Money-flow tile out of the RENDERED page.

    Anchored on `mf-etf-chips`/`mf-vol-chip` — element ids the page's own JS calls
    getElementById() on — so renaming them breaks the visible card too, instead of
    silently rotting this guard the way the old source-offset slice did.
    """
    end = html.index('id="mf-vol-chip"')
    return html[html.rindex('<div class="rvx-gcard"', 0, end): end]


# The page reads only flow.cluster.regime today; the rest mirrors a real
# engine/group_flow.py payload so the fixture stays recognisable.
_SYNTH_FLOW = {
    "verdict": "display_only",
    "regime": {"vix": 16.0, "pctile": 0.32, "elevated": False},
    "cluster": {"absorption": 0.52, "regime": "concentrated",
                "dominant_cluster": ["Industrials", "Financials"],
                "top_pair": ["Industrials", "Financials"], "top_pair_corr": 0.81},
    "sectors": [{"name": "Industrials", "name_zh": "工业", "stage": "emerging",
                 "read_quality": 0.7, "leadership": {"breadth": "broad"},
                 "cohesion_gate": {"stress_conditional": False}}],
    "baskets": [{"name": "Retail", "name_zh": "零售", "stage": "emerging",
                 "read_quality": 0.35, "leadership": {"breadth": "narrow"},
                 "cohesion_gate": {"stress_conditional": False}}],
    "groups": [],
}


def test_money_flow_card_renders_bilingually():
    card = _money_flow_card(_render_baskets(_SYNTH_FLOW))
    assert "Money flow" in card and "资金流向" in card             # label, both languages
    assert "Crowding into a few" in card and "向少数板块集中" in card  # the regime verdict


@pytest.mark.parametrize("regime, en, zh", [
    ("concentrated", "Crowding into a few", "向少数板块集中"),
    ("broad",        "Spread across many",  "广泛分布"),
    ("mixed",        "No single group leads", "暂无单一板块主导"),
    ("bogus",        "No single group leads", "暂无单一板块主导"),  # unknown -> neutral default
])
def test_money_flow_verdict_is_plain_and_never_directional(regime, en, zh):
    """Display-only: the card says WHERE money is, never what to do about it."""
    flow = {**_SYNTH_FLOW, "cluster": {**_SYNTH_FLOW["cluster"], "regime": regime}}
    card = _money_flow_card(_render_baskets(flow))
    assert en in card and zh in card
    # Scan the visible copy, not the markup — `justify-content:center` is not a verb.
    text = re.sub(r"<[^>]+>", " ", card).lower()
    for verb in ("buy", "sell", "accumulate", "enter", "exit", "trim",
                 "forecast", "target", "will"):
        assert not re.search(rf"\b{verb}\b", text), \
            f"directional/forecast word {verb!r} in display-only card copy: {text.strip()!r}"


@pytest.mark.parametrize("flow", [
    None,                                   # key absent from the context entirely
    {},                                     # present but empty
    {"verdict": "display_only"},            # payload with no cluster leg
    {"verdict": "display_only", "cluster": None},
])
def test_money_flow_card_degrades_without_a_cluster(flow):
    card = _money_flow_card(_render_baskets(flow))
    assert "Money flow" in card and "—" in card        # placeholder, not a crash
    for en in ("Crowding into a few", "Spread across many", "No single group leads"):
        assert en not in card                          # and no invented verdict


@pytest.mark.parametrize("flow", [None, _SYNTH_FLOW])
def test_baskets_page_renders_with_no_unrendered_jinja(flow):
    html = _render_baskets(flow)
    assert "{{" not in html and "{%" not in html

# ---- W0 common-observation integrity across close-panel, Group Flow, Baskets, and Theme Scoring ----
def _member(ticker: str, *, removed: str | None = None) -> dict:
    row = {"ticker": ticker, "added": "2025-01-01", "rationale": ticker}
    if removed is not None:
        row["removed"] = removed
    return row


def _basket(name: str, tickers: str) -> dict:
    return {"name": name, "name_zh": name, "category": "Test", "created": "2025-01-01",
            "etf_proxy": None, "members": [_member(t) for t in tickers]}


def _write_close_cache(tmp_path, group: str, frame: pd.DataFrame) -> None:
    directory = tmp_path / group
    directory.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(directory / "_closes_cache.parquet")


def _w0_sessions(n: int) -> pd.DatetimeIndex:
    return pd.bdate_range("2026-01-05", periods=n)


class TestObservationCalendarIntegrity:
    """A calendar label with no prices is not a market observation."""

    def test_terminal_all_null_row_is_trimmed_but_internal_gap_is_preserved(self, tmp_path):
        idx = _w0_sessions(5)
        frame = pd.DataFrame({
            "AAA": [10.0, np.nan, 11.0, 12.0, np.nan],
            "BBB": [20.0, np.nan, 21.0, 22.0, np.nan],
        }, index=idx)
        _write_close_cache(tmp_path, "breadth", frame)

        panel, meta = merge_close_caches(("breadth",), data_dir=tmp_path)

        assert panel.index.tolist() == idx[:4].tolist()
        assert panel.loc[idx[1]].isna().all()       # internal outage remains explicit
        assert meta["raw_tip"] == idx[-1]
        assert meta["tip"] == idx[-2]
        assert meta["dropped_all_null_tail_rows"] == [idx[-1]]
        assert idx[1] in meta["all_null_rows"]

    def test_all_never_populated_columns_keep_schema_with_no_effective_tip(self, tmp_path):
        idx = _w0_sessions(4)
        _write_close_cache(tmp_path, "breadth", pd.DataFrame({"DEAD": np.nan}, index=idx))

        panel, meta = merge_close_caches(("breadth",), data_dir=tmp_path)

        assert list(panel.columns) == ["DEAD"]
        assert panel.empty
        assert meta["raw_tip"] == idx[-1]
        assert meta["tip"] is None
        assert meta["behind"]["DEAD"] == -1
        assert meta["dropped_all_null_tail_rows"] == list(idx)

    def test_latest_common_observation_requires_an_actual_benchmark_close(self):
        from lib.closes_panel import align_latest_common_observation

        idx = _w0_sessions(5)
        panel = pd.DataFrame({"AAA": [10, 11, 12, 13, 14]}, index=idx)
        benchmark = pd.Series([100, 101, 102, 103, np.nan], index=idx, name="close")

        aligned, bench, meta = align_latest_common_observation(panel, benchmark)

        assert aligned.index.max() == idx[-2]
        assert bench.index.equals(aligned.index)
        assert pd.notna(bench.iloc[-1])
        assert meta["effective_as_of"] == idx[-2].strftime("%Y-%m-%d")
        assert meta["panel_raw_tip"] == idx[-1].strftime("%Y-%m-%d")
        assert meta["benchmark_observed_tip"] == idx[-2].strftime("%Y-%m-%d")
        assert meta["dropped_panel_rows_after_effective"] == [idx[-1].strftime("%Y-%m-%d")]

    def test_complete_common_observation_is_byte_equivalent(self):
        from lib.closes_panel import align_latest_common_observation

        idx = _w0_sessions(5)
        panel = pd.DataFrame({"AAA": np.arange(5.0), "BBB": np.arange(5.0) + 10}, index=idx)
        benchmark = pd.Series(np.arange(5.0) + 100, index=idx)

        aligned, bench, meta = align_latest_common_observation(panel, benchmark)

        pd.testing.assert_frame_equal(aligned, panel)
        pd.testing.assert_series_equal(bench, benchmark, check_names=False)
        assert meta["effective_as_of"] == idx[-1].strftime("%Y-%m-%d")
        assert meta["dropped_panel_rows_after_effective"] == []


class TestPopulationObservationReceipt:
    def _members(self):
        return [
            {"ticker": "A", "added": "2025-01-01"},
            {"ticker": "B", "added": "2025-01-01"},
            {"ticker": "C", "added": "2025-01-01"},
            {"ticker": "D", "added": "2025-01-01"},
            {"ticker": "OLD", "added": "2025-01-01", "removed": "2025-02-01"},
        ]

    def test_receipt_separates_configured_present_and_observed(self):
        from lib.closes_panel import population_observation

        idx = pd.bdate_range("2026-01-05", periods=3)
        panel = pd.DataFrame({
            "A": [1.0, 1.1, 1.2],
            "B": [1.0, 1.1, 1.2],
            "C": [1.0, 1.1, np.nan],
            "OLD": [1.0, 1.1, 1.2],
        }, index=idx)

        receipt = population_observation(panel, self._members(), idx[-1])

        assert receipt["configured_members"] == ["A", "B", "C", "D"]
        assert receipt["configured_n"] == 4
        assert receipt["in_panel_n"] == 3
        assert receipt["observed_members"] == ["A", "B"]
        assert receipt["observed_n"] == 2
        assert receipt["missing_columns"] == ["D"]
        assert receipt["missing_at_asof"] == ["C"]
        assert receipt["coverage"] == 0.5
        assert receipt["status"] == "insufficient"
        assert receipt["aggregate_eligible"] is False

    def test_partial_above_the_floor_is_admissible_but_never_called_complete(self):
        from lib.closes_panel import population_observation

        idx = pd.bdate_range("2026-01-05", periods=3)
        panel = pd.DataFrame({
            "A": [1.0, 1.1, 1.2], "B": [1.0, 1.1, 1.2],
            "C": [1.0, 1.1, 1.2], "D": [1.0, 1.1, np.nan],
        }, index=idx)

        receipt = population_observation(panel, self._members(), idx[-1])

        assert receipt["observed_n"] == 3
        assert receipt["coverage"] == 0.75
        assert receipt["status"] == "partial"
        assert receipt["aggregate_eligible"] is True

    def test_three_observations_still_refuse_when_coverage_is_below_sixty_percent(self):
        from lib.closes_panel import population_observation

        idx = pd.bdate_range("2026-01-05", periods=3)
        members = [
            {"ticker": ticker, "added": "2025-01-01"}
            for ticker in ("A", "B", "C", "D", "E", "F")
        ]
        panel = pd.DataFrame({
            "A": [1.0, 1.1, 1.2],
            "B": [1.0, 1.1, 1.2],
            "C": [1.0, 1.1, 1.2],
            "D": [1.0, 1.1, np.nan],
            "E": [1.0, 1.1, np.nan],
            "F": [1.0, 1.1, np.nan],
        }, index=idx)

        receipt = population_observation(panel, members, idx[-1])

        assert receipt["observed_n"] == 3
        assert receipt["coverage"] == 0.5
        assert receipt["status"] == "insufficient"
        assert receipt["aggregate_eligible"] is False

    def test_complete_receipt(self):
        from lib.closes_panel import population_observation

        idx = pd.bdate_range("2026-01-05", periods=3)
        panel = pd.DataFrame({t: [1.0, 1.1, 1.2] for t in "ABCD"}, index=idx)

        receipt = population_observation(panel, self._members(), idx[-1])

        assert receipt["status"] == "complete"
        assert receipt["coverage"] == 1.0
        assert receipt["aggregate_eligible"] is True
        assert receipt["effective_as_of"] == idx[-1].strftime("%Y-%m-%d")


def test_disclose_merge_reports_all_null_terminal_calendar_once(capsys):
    from lib import closes_panel as cp

    cp._DISCLOSED.clear()
    meta = {
        "rescued": {},
        "raw_tip": pd.Timestamp("2026-09-09"),
        "tip": pd.Timestamp("2026-09-08"),
        "dropped_all_null_tail_rows": [pd.Timestamp("2026-09-09")],
    }
    cp.disclose_merge(meta, "equity_factors")
    cp.disclose_merge(meta, "equity_factors")

    lines = [line for line in capsys.readouterr().out.splitlines() if line]
    assert len(lines) == 1
    assert lines[0].startswith("::warning title=equity_factors observation calendar::")
    assert "2026-09-09" in lines[0]
    assert "effective 2026-09-08" in lines[0]

def test_group_flow_setup_holds_extras_to_the_base_common_session(monkeypatch):
    base_idx = pd.bdate_range("2025-01-02", periods=180)
    extra_idx = base_idx.append(pd.DatetimeIndex([base_idx[-1] + pd.offsets.BDay(1)]))
    base = pd.DataFrame({t: 100 * (1.001 ** np.arange(len(base_idx))) for t in "ABCDEF"},
                        index=base_idx)
    extras = pd.DataFrame({
        **{t: 50 * (1.002 ** np.arange(len(extra_idx))) for t in "GHI"},
        # An overlapping supplemental column must not replace Group Flow's primary tape.
        "A": 900 * (1.01 ** np.arange(len(extra_idx))),
    }, index=extra_idx)
    spy = pd.DataFrame({"close": 400 * (1.0008 ** np.arange(len(extra_idx)))}, index=extra_idx)
    members = {"nuclear_shape": _basket("Nuclear shape", "ABCDEFGHI")}

    monkeypatch.setattr(gf, "_membership", lambda: {"baskets": members})
    monkeypatch.setattr(gf, "_closes", lambda: base)
    monkeypatch.setattr(gf, "_basket_extras", lambda: extras)
    monkeypatch.setattr(gf.store, "read", lambda group, name: spy if (group, name) == ("yahoo", "SPY") else None)

    setup = gf._setup("us")

    assert setup is not None
    assert setup["idx"].max() == base_idx[-1]
    assert setup["closes"].iloc[-1].notna().sum() == 9
    assert setup["closes"].loc[base_idx[-1], "A"] == base.loc[base_idx[-1], "A"]
    assert setup["observation"]["effective_as_of"] == base_idx[-1].strftime("%Y-%m-%d")
    assert setup["observation"]["panel_raw_tip"] == base_idx[-1].strftime("%Y-%m-%d")


def test_group_flow_and_baskets_share_common_date_when_benchmark_tip_is_missing(monkeypatch):
    idx = pd.bdate_range("2025-01-02", periods=180)
    x = np.arange(len(idx))
    closes = pd.DataFrame({
        "A": 100 * (1.001 ** x),
        "B": 100 * (1.0005 ** x),
        "C": 100 * (0.9998 ** x),
    }, index=idx)
    spy = pd.DataFrame({"close": 400 * (1.0008 ** x)}, index=idx)
    spy.loc[idx[-1], "close"] = np.nan
    members = {"shared": _basket("Shared clock", "ABC")}

    def read_store(group, name):
        return spy if (group, name) == ("yahoo", "SPY") else None

    monkeypatch.setattr(gf, "_membership", lambda: {"baskets": members})
    monkeypatch.setattr(gf, "_closes", lambda: closes)
    monkeypatch.setattr(gf, "_basket_extras", lambda: None)
    monkeypatch.setattr(gf.store, "read", read_store)
    monkeypatch.setattr(bk, "_membership", lambda: {"baskets": members})
    monkeypatch.setattr(bk, "_closes", lambda: closes)
    monkeypatch.setattr(bk, "_basket_extras", lambda: None)
    monkeypatch.setattr(bk, "_names_sectors", lambda: {t: (t, "Test") for t in "ABC"})
    monkeypatch.setattr(bk.store, "read", read_store)

    setup = gf._setup("us")
    payload = bk.compute_baskets()

    expected = idx[-2].strftime("%Y-%m-%d")
    assert setup is not None
    assert payload is not None
    assert setup["observation"]["effective_as_of"] == expected
    assert setup["observation"]["benchmark_observed_tip"] == expected
    assert payload["observation"]["effective_as_of"] == expected
    assert payload["as_of"] == expected
    assert payload["chart"]["dates"][-1] == expected


def _basket_compute_fixture(
    monkeypatch,
    *,
    insufficient: str = "ABCD",
    missing: tuple[str, ...] = ("C", "D"),
    complete: str = "EFG",
):
    idx = pd.bdate_range("2025-01-02", periods=180)
    x = np.arange(len(idx))
    tickers = "".join(dict.fromkeys(insufficient + complete))
    closes = pd.DataFrame({t: 100 * (1.0005 + 0.00005 * k) ** x
                           for k, t in enumerate(tickers)}, index=idx)
    closes.loc[idx[-1], list(missing)] = np.nan
    spy = pd.DataFrame({"close": 400 * (1.0008 ** x)}, index=idx)
    members = {
        "insufficient": _basket("Insufficient", insufficient),
        "complete": _basket("Complete", complete),
    }
    monkeypatch.setattr(bk, "_membership", lambda: {"baskets": members})
    monkeypatch.setattr(bk, "_closes", lambda: closes)
    monkeypatch.setattr(bk, "_basket_extras", lambda: None)
    monkeypatch.setattr(bk, "_names_sectors", lambda: {t: (t, "Test") for t in tickers})
    monkeypatch.setattr(bk.store, "read", lambda group, name: spy if (group, name) == ("yahoo", "SPY") else None)
    return idx


def test_baskets_freezes_date_before_extras_and_preserves_deep_overlap_precedence(monkeypatch):
    base_idx = pd.bdate_range("2025-01-02", periods=180)
    extra_idx = base_idx.append(pd.DatetimeIndex([base_idx[-1] + pd.offsets.BDay(1)]))
    x = np.arange(len(base_idx))
    base = pd.DataFrame({
        "A": 100 * (1.001 ** x),
        "B": 100 * (1.0005 ** x),
        "C": 100 * (0.9998 ** x),
    }, index=base_idx)
    deep_a = 200 * (1.0015 ** np.arange(len(extra_idx)))
    extras = pd.DataFrame({
        "A": deep_a,
        "D": 50 * (1.002 ** np.arange(len(extra_idx))),
        "E": 75 * (1.001 ** np.arange(len(extra_idx))),
    }, index=extra_idx)
    spy = pd.DataFrame({"close": 400 * (1.0008 ** np.arange(len(extra_idx)))}, index=extra_idx)
    members = {"deep": _basket("Deep history", "ADE")}

    monkeypatch.setattr(bk, "_membership", lambda: {"baskets": members})
    monkeypatch.setattr(bk, "_closes", lambda: base)
    monkeypatch.setattr(bk, "_basket_extras", lambda: extras)
    monkeypatch.setattr(bk, "_names_sectors", lambda: {t: (t, "Test") for t in "ABCDE"})
    monkeypatch.setattr(
        bk.store, "read",
        lambda group, name: spy if (group, name) == ("yahoo", "SPY") else None,
    )

    out = bk.compute_baskets()

    assert out is not None
    assert out["as_of"] == base_idx[-1].strftime("%Y-%m-%d")
    assert len(out["chart"]["dates"]) == len(base_idx)
    assert out["chart"]["dates"][-1] == base_idx[-1].strftime("%Y-%m-%d")
    row = out["baskets"][0]
    assert row["observation"]["configured_n"] == 3
    assert row["observation"]["observed_n"] == 3
    by_symbol = {member["symbol"]: member for member in row["members"]}
    # This is the incumbent Baskets basis rule: deep extras wins on overlap after
    # the common date is frozen; it is not permission for extras to advance the date.
    assert by_symbol["A"]["last"] == round(float(deep_a[len(base_idx) - 1]), 2)


def test_baskets_refuses_below_population_floor_and_discloses_it(monkeypatch, capsys):
    idx = _basket_compute_fixture(monkeypatch)
    level_calls = []
    real_level = bk._ew_level
    monkeypatch.setattr(
        bk,
        "_ew_level",
        lambda *args, **kwargs: level_calls.append(args) or real_level(*args, **kwargs),
    )

    out = bk.compute_baskets()

    assert out is not None
    assert out["as_of"] == idx[-1].strftime("%Y-%m-%d")
    assert [row["id"] for row in out["baskets"]] == ["complete"]
    assert out["baskets"][0]["observation"]["status"] == "complete"
    assert out["baskets"][0]["observation"]["configured_n"] == 3
    refusal = out["observation_refusals"][0]
    assert refusal["basket_id"] == "insufficient"
    assert refusal["observation"]["observed_n"] == 2
    assert refusal["observation"]["configured_n"] == 4
    assert refusal["observation"]["aggregate_eligible"] is False
    assert len(level_calls) == 1  # complete basket only; refused basket never builds a level
    assert "::warning title=basket-observation-coverage::" in capsys.readouterr().out


def test_baskets_refuses_three_of_six_when_coverage_floor_fails(monkeypatch):
    idx = _basket_compute_fixture(
        monkeypatch,
        insufficient="ABCDEF",
        missing=("D", "E", "F"),
        complete="GHI",
    )
    level_calls = []
    real_level = bk._ew_level
    monkeypatch.setattr(
        bk,
        "_ew_level",
        lambda *args, **kwargs: level_calls.append(args) or real_level(*args, **kwargs),
    )

    out = bk.compute_baskets()

    assert out is not None
    assert out["as_of"] == idx[-1].strftime("%Y-%m-%d")
    assert [row["id"] for row in out["baskets"]] == ["complete"]
    refusal = out["observation_refusals"][0]
    assert refusal["basket_id"] == "insufficient"
    assert refusal["observation"]["observed_n"] == 3
    assert refusal["observation"]["configured_n"] == 6
    assert refusal["observation"]["coverage"] == 0.5
    assert refusal["observation"]["aggregate_eligible"] is False
    assert len(level_calls) == 1


def _theme_compute_fixture(
    monkeypatch,
    *,
    insufficient: str = "ABCD",
    missing: tuple[str, ...] = ("C", "D"),
    complete: str = "EFG",
):
    idx = pd.bdate_range("2025-01-02", periods=260)
    x = np.arange(len(idx))
    tickers = "".join(dict.fromkeys(insufficient + complete))
    closes = pd.DataFrame({t: 100 * (1.0005 + 0.00003 * k) ** x
                           for k, t in enumerate(tickers)}, index=idx)
    closes.loc[idx[-1], list(missing)] = np.nan
    rets = closes.pct_change(fill_method=None)
    bench = pd.Series(1.0007 ** x, index=idx)
    members = {
        "insufficient": _basket("Insufficient", insufficient),
        "complete": _basket("Complete", complete),
    }
    monkeypatch.setattr(ts.group_flow, "_setup", lambda region="us": {
        "mem": {"baskets": members}, "closes": closes, "rets": rets,
        "idx": idx, "bench": bench, "region": region,
        "observation": {"effective_as_of": idx[-1].strftime("%Y-%m-%d")},
    })
    monkeypatch.setattr(ts.group_flow, "_cfg", lambda cfg=None: {})
    monkeypatch.setattr(ts.group_flow, "prep_group", lambda *args, **kwargs: object())
    monkeypatch.setattr(ts.group_flow, "fingerprint_at", lambda *args, **kwargs: {
        "accel_z": 0.0, "rs_pctile": 0.5, "broadening_z": 0.0,
        "cohesion": 0.5, "cohesion_chg": 0.0, "persistence": 0.5,
    })
    monkeypatch.setattr(ts.group_flow, "_leadership", lambda *args, **kwargs: {
        "breadth": "broad", "top": [], "hhi": 0.2,
    })
    monkeypatch.setattr(ts, "_macro_context", lambda region="us": {
        "state": {}, "sector_rs": {}, "display": {},
    })
    monkeypatch.setattr(ts, "_signal_calibration", lambda: {})
    monkeypatch.setattr(ts, "_perf", lambda *args, **kwargs: {
        h: {"ret": 0.01, "rel": 0.0} for h in ("1d", "5d", "10d", "20d", "60d", "ytd")
    })
    monkeypatch.setattr(ts, "_macro_leg", lambda *args, **kwargs: (0.0, []))
    monkeypatch.setattr(ts, "_crowding_pen", lambda *args, **kwargs: (0.0, []))
    monkeypatch.setattr(ts, "_basket_signals", lambda *args, **kwargs: {})
    monkeypatch.setattr(ts.basket_score, "theme_textures", lambda *args, **kwargs: {
        "clean_entry": {"flag": False, "quality": 0.0, "reasons": []},
        "rollover_risk": {"band": "low", "risk": 0.0, "reasons": []},
        "bull_age": {"in_bull": False},
    })
    monkeypatch.setattr(ts.basket_score, "market_concentration", lambda *args, **kwargs: {})
    monkeypatch.setattr(ts.vol_regime, "published_snapshot", lambda: None)
    monkeypatch.setattr(ts.vol_regime, "overlay_config", lambda: {})
    monkeypatch.setattr(ts.vol_regime, "sizing_overlay", lambda *args, **kwargs: {
        "active": False, "gross_scalar": 1.0,
    })
    monkeypatch.setattr(ts.vol_regime, "regime_caution_scored", lambda: False)
    monkeypatch.setattr(ts, "_apply_sector_conflict_demotion", lambda *args, **kwargs: None)
    monkeypatch.setattr(ts, "_apply_momentum_cooling_demotion", lambda *args, **kwargs: None)
    return idx


def test_theme_scoring_refuses_below_floor_before_label_or_recommendation(monkeypatch):
    idx = _theme_compute_fixture(monkeypatch)
    level_calls = []
    prep_calls = []
    fingerprint_calls = []
    label_calls = []
    reco_calls = []
    monkeypatch.setattr(ts, "_ew_level", lambda *args, **kwargs: level_calls.append(args) or pd.Series(1.0, index=idx))
    monkeypatch.setattr(ts.group_flow, "prep_group", lambda *args, **kwargs: prep_calls.append(args) or object())
    monkeypatch.setattr(ts.group_flow, "fingerprint_at", lambda *args, **kwargs: fingerprint_calls.append(args) or {
        "accel_z": 0.0, "rs_pctile": 0.5, "broadening_z": 0.0,
        "cohesion": 0.5, "cohesion_chg": 0.0, "persistence": 0.5,
    })
    monkeypatch.setattr(ts, "_label", lambda *args, **kwargs: label_calls.append(args) or "neutral")
    monkeypatch.setattr(ts, "_reco", lambda *args, **kwargs: reco_calls.append(args) or "hold")

    out = ts.compute_theme_intel("us")

    assert out is not None
    assert out["as_of"] == idx[-1].strftime("%Y-%m-%d")
    assert [row["id"] for row in out["themes"]] == ["complete"]
    assert len(level_calls) == 1
    assert len(prep_calls) == 1
    assert len(fingerprint_calls) == 2  # current + five-session comparison, complete theme only
    assert len(label_calls) == 1
    assert len(reco_calls) == 1
    theme = out["themes"][0]
    assert theme["observation"]["status"] == "complete"
    assert theme["n_members"] == 3
    refusal = out["observation_refusals"][0]
    assert refusal["basket_id"] == "insufficient"
    assert refusal["observation"]["coverage"] == 0.5
    assert refusal["observation"]["aggregate_eligible"] is False

def test_theme_scoring_refuses_three_of_six_before_any_aggregate_effect(monkeypatch):
    idx = _theme_compute_fixture(
        monkeypatch,
        insufficient="ABCDEF",
        missing=("D", "E", "F"),
        complete="GHI",
    )
    level_calls = []
    prep_calls = []
    fingerprint_calls = []
    label_calls = []
    reco_calls = []
    monkeypatch.setattr(ts, "_ew_level", lambda *args, **kwargs: level_calls.append(args) or pd.Series(1.0, index=idx))
    monkeypatch.setattr(ts.group_flow, "prep_group", lambda *args, **kwargs: prep_calls.append(args) or object())
    monkeypatch.setattr(ts.group_flow, "fingerprint_at", lambda *args, **kwargs: fingerprint_calls.append(args) or {
        "accel_z": 0.0, "rs_pctile": 0.5, "broadening_z": 0.0,
        "cohesion": 0.5, "cohesion_chg": 0.0, "persistence": 0.5,
    })
    monkeypatch.setattr(ts, "_label", lambda *args, **kwargs: label_calls.append(args) or "neutral")
    monkeypatch.setattr(ts, "_reco", lambda *args, **kwargs: reco_calls.append(args) or "hold")

    out = ts.compute_theme_intel("us")

    assert out is not None
    assert [row["id"] for row in out["themes"]] == ["complete"]
    refusal = out["observation_refusals"][0]
    assert refusal["basket_id"] == "insufficient"
    assert refusal["observation"]["observed_n"] == 3
    assert refusal["observation"]["configured_n"] == 6
    assert refusal["observation"]["coverage"] == 0.5
    assert refusal["observation"]["aggregate_eligible"] is False
    assert len(level_calls) == 1
    assert len(prep_calls) == 1
    assert len(fingerprint_calls) == 2
    assert len(label_calls) == 1
    assert len(reco_calls) == 1

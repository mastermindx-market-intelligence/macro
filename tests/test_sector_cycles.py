"""Sector Cycle Intelligence engine tests — ZigZag turns, oscillator, phase
classification, projection, and an end-to-end compute() smoke test."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import sector_cycles as sc  # noqa: E402

IDX = pd.bdate_range("2020-01-01", periods=900)


def _saw(ampl=0.5, period=180, n=900, trend=0.0003):
    """Deterministic triangle-wave price with a gentle uptrend (clean major swings)."""
    t = np.arange(n)
    phase = (t % period) / period
    tri = np.where(phase < 0.5, phase * 2, 2 - phase * 2)        # 0..1..0
    return pd.Series(100 * np.exp(trend * t) * (1 + ampl * tri), index=IDX[:n])


# ── ZigZag swing detection ───────────────────────────────────────────────────

def test_cycle_tabs_wrap_on_a_phone() -> None:
    # A string pin cannot prove layout. The 375 browser read in the PR carries that.
    root = Path(__file__).resolve().parent.parent
    rule = "@media (max-width: 560px) { .sc-tabs { flex-wrap: wrap; } }"
    assert rule in (root / "templates" / "sector_cycles.css").read_text(encoding="utf-8")


def test_cycle_cards_keep_a_readable_width_on_a_phone() -> None:
    # Two narrow columns squeeze a name to one letter a line beside its tags.
    # A string pin cannot prove layout. The browser read in the PR carries that.
    root = Path(__file__).resolve().parent.parent
    rule = "@media (max-width: 880px) { .sc-page .cyc-cards { grid-template-columns: repeat(auto-fill, minmax(258px, 1fr)); } }"
    assert rule in (root / "templates" / "sector_cycles.css").read_text(encoding="utf-8")


def test_zigzag_alternates_and_is_significant():
    s = _saw(ampl=0.5, period=180)
    turns = sc._detect_swings(s, pct=12.0)
    assert len(turns) >= 5
    # strict alternation
    kinds = [t["k"] for t in turns]
    for a, b in zip(kinds, kinds[1:]):
        assert a != b, f"non-alternating turns: {kinds}"
    # every confirmed leg clears the threshold (provisional last leg may not)
    for t in turns[1:-1]:
        assert t["mag_pct"] is None or t["mag_pct"] >= 12.0 - 1e-6
    assert turns[-1]["provisional"] is True
    assert all(set(["date", "t", "x", "px", "k"]).issubset(t) for t in turns)


def test_zigzag_threshold_thins_turns():
    s = _saw(ampl=0.5, period=120)
    assert len(sc._detect_swings(s, pct=8.0)) >= len(sc._detect_swings(s, pct=20.0))


def test_zigzag_flat_series_no_swings():
    flat = pd.Series(np.full(400, 100.0) + np.random.default_rng(0).normal(0, 0.05, 400), index=IDX[:400])
    turns = sc._detect_swings(flat, pct=12.0)
    # a noisy-flat line never reverses 12% -> only the provisional leg, no confirmed turns
    assert len([t for t in turns if not t["provisional"]]) <= 1


# ── oscillator ───────────────────────────────────────────────────────────────

def test_detrended_osc_bounded_and_tracks_cycle():
    s = _saw(ampl=0.6, period=200)
    osc = sc._detrended_osc(s).dropna()
    assert osc.between(-0.01, 100.01).all()
    # the oscillator should be higher near a price peak than near the prior trough
    assert osc.max() > 60 and osc.min() < 40


# ── phase classification ─────────────────────────────────────────────────────

def test_classify_phase_buckets():
    up_w, up3 = {"macd_pos": True}, {"macd_pos": True}
    dn_w, dn3 = {"macd_pos": False}, {"macd_pos": False}
    # 2026-07 rollover-lag fix: high + rising WITHOUT deceleration evidence is a leader
    # in full thrust — Trending (extended), not Topping (XLV read Topping at breadth 81%)
    assert sc._classify_phase(85, +5, up_w, up3, True)[0] == "Expansion"
    # high + rising WITH confirmed deceleration (3D negative / weekly fading) = true Topping
    assert sc._classify_phase(85, +5, up_w, dn3, True)[0] == "Peak"
    assert sc._classify_phase(85, +5, {"macd_pos": True, "macd_approaching_dn": True},
                              up3, True)[0] == "Peak"
    assert sc._classify_phase(85, -5, dn_w, dn3, True)[0] == "Downturn"    # high + falling = rolling over
    assert sc._classify_phase(50, +5, up_w, up3, True)[0] == "Expansion"   # mid + rising
    assert sc._classify_phase(20, +5, up_w, up3, True)[0] == "Recovery"    # low + rising
    assert sc._classify_phase(15, -5, dn_w, dn3, False)[0] == "Trough"     # low + falling = bottoming
    # every phase is a known bucket with a hue
    for pos in (10, 50, 90):
        for sl in (-8, 8):
            ph, lab = sc._classify_phase(pos, sl, up_w, dn3, True)
            assert ph in sc.PHASES and isinstance(lab, str) and lab


def test_classify_phase_anticipates_rollover():
    """2026-07 sector-central audit: the weekly histogram holds positive for weeks after
    a real top, so the pre-cross deceleration window must flip the direction vote —
    XLK's exact stamp (weekly still positive but approaching its cross, 3D negative,
    oscillator collapsing) must read Rolling over, not Topping/Trending."""
    w_fading = {"macd_pos": True, "macd_approaching_dn": True}
    dn3 = {"macd_pos": False}
    # stretched (XLK 2026-07-16: pos 70.2, slope −20.7) → Downturn / Rolling over
    assert sc._classify_phase(70.2, -20.7, w_fading, dn3, True) == ("Downturn", "Rolling over")
    # mid position (ai_infra: pos 60.1, slope −30.4) → also Rolling over
    assert sc._classify_phase(60.1, -30.4, w_fading, dn3, True)[0] == "Downturn"
    # direction TIES break to the FASTER 3D clock, not the stale weekly sign
    # (weekly pos, 3D negative, slope down: votes 2−1−1=0 → 3D decides → falling)
    assert sc._classify_phase(60.0, -5.0, {"macd_pos": True}, dn3, True)[0] == "Downturn"
    # ... and the monthly kernel (t3={}) keeps the legacy weekly-sign tiebreak
    assert sc._classify_phase(60.0, -5.0, {"macd_pos": True}, {}, True)[0] == "Expansion"


# ── projection ───────────────────────────────────────────────────────────────

def test_project_next_alternates_and_ranges():
    s = _saw(ampl=0.5, period=180)
    turns = sc._detect_swings(s, pct=12.0)
    proj = sc._project_next(turns, s.index[-1])
    assert proj is not None
    assert proj["nextTurn"] in ("peak", "trough")
    # W1.6: projection anchors at the last CONFIRMED turn and projects its opposite
    # (which matches the provisional open-leg extreme, so compare vs confirmed only)
    last_confirmed = [t for t in turns if not t.get("provisional")][-1]
    assert proj["nextTurn"] != last_confirmed["k"]
    assert proj["period_yrs"]["lo"] <= proj["period_yrs"]["median"] <= proj["period_yrs"]["hi"]


def test_x_to_ym_roundtrips_month():
    assert sc._x_to_ym(2026.0) == "2026-01"
    assert sc._x_to_ym(2026.96) in ("2026-12", "2027-01")


# ── end-to-end ───────────────────────────────────────────────────────────────

def test_compute_smoke():
    try:
        data = sc.compute()
    except Exception as e:  # pragma: no cover - data env issue
        pytest.skip(f"yahoo_closes unavailable: {e}")
    if not data:
        pytest.skip("no sector data in this environment")
    assert data["meta"]["n_sectors"] >= 8
    assert set(data["phases"]) == {"Trough", "Recovery", "Expansion", "Peak", "Downturn"}
    for s in data["sectors"]:
        assert s["ticker"] in sc.SECTORS
        assert s["price"] and s["osc"], f"{s['ticker']} missing series"
        assert s["now"]["phase"] in sc.PHASES
        assert 0 <= s["now"]["pos"] <= 100
        # turns alternate
        kinds = [t["k"] for t in s["turns"]]
        for a, b in zip(kinds, kinds[1:]):
            assert a != b
        # rebased series starts ~100
        assert abs(s["price"][0]["v"] - 100.0) < 5.0
        if s["proj"]:
            assert s["proj"]["nextTurn"] in ("peak", "trough")


def test_compute_json_serialisable():
    import json
    data = sc.compute()
    if not data:
        pytest.skip("no sector data")
    js = json.dumps(data)            # must not raise (no numpy/Timestamp leakage)
    assert "NaN" not in js and "Infinity" not in js


# ── semantic session anchoring ───────────────────────────────────────────────

def test_latest_cycle_session_ignores_raw_calendar_tail_without_benchmark_price():
    idx = pd.to_datetime(["2026-09-14", "2026-09-15", "2026-09-16"])
    closes = pd.DataFrame(
        {
            "SPY": [760.0, np.nan, np.nan],
            "XLK": [184.0, 185.0, 186.0],
        },
        index=idx,
    )
    assert sc._latest_cycle_session(closes, "SPY") == pd.Timestamp("2026-09-14")


def test_latest_cycle_session_returns_none_without_benchmark_observation():
    closes = pd.DataFrame(
        {"SPY": [np.nan, np.nan], "XLK": [184.0, 185.0]},
        index=pd.to_datetime(["2026-09-14", "2026-09-15"]),
    )
    assert sc._latest_cycle_session(closes, "SPY") is None


def _minimal_cycle_record(ticker: str) -> dict:
    return {
        "id": ticker.lower(),
        "kind": "sector",
        "name": ticker,
        "now": {"rs_63d": 1.0, "rs_21d": 1.0},
    }


def test_compute_clips_every_sector_to_observed_benchmark_session(monkeypatch):
    idx = pd.to_datetime(["2026-09-12", "2026-09-14", "2026-09-15"])
    closes = pd.DataFrame(
        {
            "SPY": [755.0, 760.0, np.nan],
            "XLK": [183.0, 184.0, 185.0],
        },
        index=idx,
    )
    seen_tips: list[pd.Timestamp] = []

    monkeypatch.setattr(sc, "yahoo_closes", lambda basis=None: closes.copy())
    monkeypatch.setattr(
        sc.config,
        "load",
        lambda: {"engine": {"rs_ranking": {"benchmark": "SPY"}}},
    )
    monkeypatch.setattr(sc, "_load_baskets", lambda: {})
    monkeypatch.setattr(sc, "build_amalgam_family", lambda *args, **kwargs: [])

    def fake_build_sector(ticker, _meta, panel, _win_start, *, closes_px=None):
        seen_tips.append(pd.Timestamp(panel.index.max()))
        assert closes_px is not None
        assert pd.Timestamp(closes_px.index.max()) == pd.Timestamp("2026-09-14")
        return _minimal_cycle_record(ticker)

    monkeypatch.setattr(sc, "build_sector", fake_build_sector)
    data = sc.compute()

    assert data is not None
    assert data["meta"]["asOf"] == "2026-09-14"
    assert seen_tips
    assert set(seen_tips) == {pd.Timestamp("2026-09-14")}


def test_compute_refuses_to_fabricate_session_without_benchmark(monkeypatch):
    closes = pd.DataFrame(
        {"SPY": [np.nan, np.nan], "XLK": [184.0, 185.0]},
        index=pd.to_datetime(["2026-09-14", "2026-09-15"]),
    )
    called = False

    monkeypatch.setattr(sc, "yahoo_closes", lambda basis=None: closes.copy())
    monkeypatch.setattr(
        sc.config,
        "load",
        lambda: {"engine": {"rs_ranking": {"benchmark": "SPY"}}},
    )

    def should_not_build(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("sector construction must not run without a benchmark session")

    monkeypatch.setattr(sc, "build_sector", should_not_build)
    assert sc.compute() is None
    assert called is False


def test_broad_sector_cycles_builder_keeps_last_good_when_engine_has_no_session(
    monkeypatch, tmp_path,
):
    from scripts import build_sector_cycles

    site = tmp_path / "site"
    site.mkdir()
    last_good = site / "sector_cycles_data.js"
    last_good.write_text("window.SECTOR_CYCLES={old:true};\n")

    monkeypatch.setattr(build_sector_cycles.config, "ROOT", tmp_path)
    monkeypatch.setattr(
        build_sector_cycles.config,
        "load",
        lambda: {"storage": {"site_dir": "site"}},
    )
    monkeypatch.setattr(sc, "compute", lambda: None)

    assert build_sector_cycles.main() == 0
    assert last_good.read_text() == "window.SECTOR_CYCLES={old:true};\n"



# ── Leadership Migration W3A: truthful reconstructed daily RS history ────────

def _extract_js_fn(text, name):
    token = "function " + name + "("
    start = text.find(token)
    assert start != -1, name + " missing from sector_cycles.js"
    i = text.find("{", start)
    depth = 0
    for j, ch in enumerate(text[i:], i):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:j + 1]
    raise AssertionError("unbalanced " + name)


def _hz_fns(text):
    names = (
        "esc",
        "_hzPass",
        "_hzTip",
        "_hzBadge",
        "_hzPick",
        "_hzWithheld",
        "hazardLineHTML",
        "hazardCardChip",
    )
    chunks = []
    for name in names:
        if name == "_hzWithheld" and "function _hzWithheld(" not in text:
            continue
        chunks.append(_extract_js_fn(text, name))
    return "\n".join(chunks)


def _eval_hz_fn(fn_name, sector, lang):
    import json
    import shutil
    import subprocess

    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    text = _template_text("sector_cycles.js")
    source = "\n".join([
        "function curLang() { return " + json.dumps(lang) + "; }",
        'function L(en, zh) { return curLang() === "zh" ? (zh || en) : en; }',
        _hz_fns(text),
        "console.log(" + fn_name + "(" + json.dumps(sector) + "));",
    ])
    done = subprocess.run(
        [node, "-e", source],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return done.stdout.strip()


def test_sector_card_says_when_hazard_withheld():
    en_a = "Unavailable today — the model's short- and long-window reads disagreed, "
    en_b = "so no clean probability can be shown."
    en_cdf = en_a + en_b
    zh_cdf = (
        "今日暂不可用——模型的短窗与长窗读数不一致，无法给出可靠概率。"
    )
    en_def = "Unavailable today — a required input didn't settle cleanly."
    zh_def = "今日暂不可用——所需输入未能完整结算。"
    text = _template_text("sector_cycles.js")
    start = text.find("function hazardLineHTML")
    end = text.find("function forecastCardHTML")
    assert start != -1 and end > start
    hz_block = text[start:end]
    chip = _extract_js_fn(text, "hazardCardChip")
    line = _extract_js_fn(text, "hazardLineHTML")
    why = _extract_js_fn(text, "_hzWithheld")
    assert en_a in hz_block and en_b in hz_block
    assert zh_cdf in hz_block
    assert en_a in why and en_b in why
    assert zh_cdf in why
    assert en_def in why and zh_def in why
    assert "if (hz.unavailable)" in chip
    assert "if (hz.unavailable)" in line
    assert "_hzWithheld" in chip and "_hzWithheld" in line
    assert "non_monotone_cdf" not in chip
    assert "non_monotone_cdf" not in line
    assert "unavailable_reason" not in chip
    assert "unavailable_reason" not in line
    chip_head = chip.split("var pick = _hzPick")[0]
    line_head = line.split("function cell")[0]
    assert "%" not in chip_head and "_hzPick" not in chip_head
    assert "%" not in line_head and "_hzPick" not in line_head
    assert "_hzTip" not in chip_head and "_hzTip" not in line_head
    assert "cc-hz hz-muted" in chip_head
    assert "cyc-hazard sc-hazard" in line_head
    assert "Turn hazard unavailable" not in why
    assert "转折风险暂不可用" not in why
    withheld = {
        "now": {
            "hazard": {
                "unavailable": True,
                "unavailable_reason": "non_monotone_cdf",
            }
        }
    }
    other = {
        "now": {
            "hazard": {
                "unavailable": True,
                "unavailable_reason": "unknown_phase",
            }
        }
    }
    figures = {
        "now": {
            "hazard": {
                "direction": "down",
                "3m": {
                    "p": 0.25,
                    "cell_verdict": "PASS",
                    "source": "MODEL",
                },
            }
        }
    }
    chip_en = _eval_hz_fn("hazardCardChip", withheld, "en")
    chip_zh = _eval_hz_fn("hazardCardChip", withheld, "zh")
    assert '<span class="cc-hz-k">Turn hazard</span> Unavailable today</div>' in chip_en
    assert '<span class="cc-hz-k">转折风险</span> 今日暂不可用</div>' in chip_zh
    assert 'title="' + en_cdf + '"' in chip_en
    assert 'title="' + zh_cdf + '"' in chip_zh
    line_en = _eval_hz_fn("hazardLineHTML", withheld, "en")
    line_zh = _eval_hz_fn("hazardLineHTML", withheld, "zh")
    assert '<span class="hz-label">Turn hazard</span>' + en_cdf + "</div>" in line_en
    assert '<span class="hz-label">转折风险</span>' + zh_cdf + "</div>" in line_zh
    for fn in ("hazardCardChip", "hazardLineHTML"):
        en = _eval_hz_fn(fn, withheld, "en")
        zh = _eval_hz_fn(fn, withheld, "zh")
        assert en_cdf in en and zh_cdf not in en
        assert zh_cdf in zh and en_cdf not in zh
        assert "non_monotone_cdf" not in en
        assert "non_monotone_cdf" not in zh
        assert "%" not in en and "%" not in zh
        assert "unavailable_reason" not in en
        assert "unavailable_reason" not in zh
        assert _eval_hz_fn(fn, {}, "en") == ""
        assert _eval_hz_fn(fn, {"now": {}}, "zh") == ""
        fig_en = _eval_hz_fn(fn, figures, "en")
        fig_zh = _eval_hz_fn(fn, figures, "zh")
        assert en_cdf not in fig_en and zh_cdf not in fig_zh
        assert "Unavailable today" not in fig_en
        assert "今日暂不可用" not in fig_zh
        o_en = _eval_hz_fn(fn, other, "en")
        o_zh = _eval_hz_fn(fn, other, "zh")
        assert en_def in o_en and zh_def in o_zh
        assert en_cdf not in o_en and zh_cdf not in o_zh
        assert "non_monotone_cdf" not in o_en
        assert "%" not in o_en and "%" not in o_zh


def _rs_history_panel(n: int = 520) -> pd.DataFrame:
    idx = pd.bdate_range("2024-01-02", periods=n)
    # A non-linear benchmark plus a smoothly accelerating sector-relative ratio
    # makes both 21d and 63d legs non-zero and mutation-discriminating.
    spy = pd.Series(100.0 * np.exp(np.linspace(0.0, 0.24, n)), index=idx)
    rel = pd.Series(np.exp(np.linspace(-0.12, 0.31, n) ** 3), index=idx)
    xlk = spy * rel
    return pd.DataFrame({"SPY": spy, "XLK": xlk}, index=idx)


def test_leadership_history_endpoint_matches_live_leadership_formula():
    panel = _rs_history_panel()
    live = sc._leadership(panel, "XLK")
    history = sc._leadership_history(panel, "XLK")

    assert history
    assert history[-1]["date"] == panel.index[-1].date().isoformat()
    assert history[-1]["rs_21d"] == live["rs_21d"]
    assert history[-1]["rs_63d"] == live["rs_63d"]


def test_leadership_history_is_bounded_ordered_and_requires_live_eligibility():
    panel = _rs_history_panel(700)
    history = sc._leadership_history(panel, "XLK")

    assert len(history) == sc.RS_HISTORY_MAX_POINTS == 252
    assert [row["date"] for row in history] == sorted(row["date"] for row in history)
    assert all(set(row) == {"date", "rs_21d", "rs_63d"} for row in history)

    thin = _rs_history_panel(209)
    assert sc._leadership_history(thin, "XLK") == []


def test_leadership_history_asof_does_not_use_future_prices():
    panel = _rs_history_panel(520)
    cutoff = panel.index[399]
    expected = sc._leadership_history(panel, "XLK", asof=cutoff)

    mutated = panel.copy()
    mutated.loc[mutated.index > cutoff, "XLK"] *= 25.0
    mutated.loc[mutated.index > cutoff, "SPY"] *= 0.1
    observed = sc._leadership_history(mutated, "XLK", asof=cutoff)

    assert observed == expected
    assert observed[-1]["date"] == cutoff.date().isoformat()
    assert all(row["date"] <= cutoff.date().isoformat() for row in observed)


def _panel_with_zero_benchmark(n: int = 520, before_end: int = 10) -> pd.DataFrame:
    """`_rs_history_panel(n)` with the benchmark close forced to 0.0 on one session.

    A zero close is the degenerate owner case: the ratio blows up to +inf, which
    `json.dumps` would serialise as the non-standard `Infinity` token.
    """
    panel = _rs_history_panel(n)
    panel.loc[panel.index[-1 - before_end], "SPY"] = 0.0
    return panel


def test_rs_history_zero_benchmark_close_cannot_emit_infinity():
    # MUTATION A: drop the ratio filter in _relative_strength_series_counted
    #   (`rs = ratio[ratio.notna()]`) -> the zero-benchmark session survives as +inf,
    #   so the RS-series "all finite / zeroed date absent" assertions fail.
    # MUTATION B: drop BOTH that filter and the inf_rows filter in
    #   _leadership_history_counted -> a history row carries inf and
    #   json.dumps(..., allow_nan=False) raises ValueError.
    import json

    clean = _rs_history_panel(520)
    zeroed = _panel_with_zero_benchmark(520, 10)
    zero_date = zeroed.index[-11].date().isoformat()

    rs = sc._relative_strength_series(zeroed, "XLK")
    assert len(rs) > 0
    assert np.isfinite(rs.to_numpy()).all(), "RS series carries a non-finite ratio"
    assert zero_date not in [ts.date().isoformat() for ts in rs.index]

    live = sc._leadership(zeroed, "XLK")
    assert live.get("thin_history") is False
    for key in ("rs_21d", "rs_63d", "rs_126d"):
        assert np.isfinite(live[key]), f"_leadership {key} is not finite"

    rows, n_excluded = sc._leadership_history_counted(zeroed, "XLK")
    assert n_excluded >= 1, "the zero-close ratio row was not counted as excluded"
    assert rows == sc._leadership_history(zeroed, "XLK")
    json.dumps(rows, allow_nan=False)          # must not raise
    assert all(np.isfinite(row["rs_21d"]) and np.isfinite(row["rs_63d"]) for row in rows)
    assert all(row["date"] != zero_date for row in rows)

    clean_rows, clean_excluded = sc._leadership_history_counted(clean, "XLK")
    assert clean_excluded == 0
    assert clean_rows == sc._leadership_history(clean, "XLK")
    json.dumps(clean_rows, allow_nan=False)    # must not raise


def test_rs_benchmark_ffill_is_bounded():
    # MUTATION: `.ffill()` without `limit=RS_BENCH_FFILL_LIMIT` -> the benchmark gap is
    # carried forever, so the last 3 stale dates reappear in the RS series.
    n = 300
    idx = pd.bdate_range("2024-01-02", periods=n)
    spy = pd.Series(100.0 * np.exp(np.linspace(0.0, 0.2, n)), index=idx)
    gap_start = n - 30
    gap = idx[gap_start:gap_start + 8]
    spy.loc[gap] = np.nan
    panel = pd.DataFrame({"SPY": spy, "XLK": spy.ffill() * 1.05}, index=idx)

    rs = sc._relative_strength_series(panel, "XLK")
    dates = {ts.date().isoformat() for ts in rs.index}
    carried = [ts.date().isoformat() for ts in gap[:5]]
    stale = [ts.date().isoformat() for ts in gap[5:]]

    assert all(d in dates for d in carried), "bounded ffill dropped an in-limit session"
    assert not any(d in dates for d in stale), "benchmark ffill is unbounded"
    assert sc.RS_BENCH_FFILL_LIMIT == 5


def test_sector_page_says_rs_rank_is_rebuilt_from_price():
    """The sector page says the RS rank is rebuilt, from the record."""
    import re

    root = Path(__file__).resolve().parents[1]
    page = root / "templates" / "sector_cycles.html.j2"
    text = page.read_text(encoding="utf-8")
    guard = "naturally_observed === false"
    assert guard in text
    en = "RS rank is rebuilt from total-return price history against "
    zh = "相对强度排名由总回报价格历史重建，基准 "
    assert en in text
    assert ". It is not an observed record." in text
    assert zh in text
    assert "。并非当时观察到的记录。" in text
    assert 'basis === "tr"' in text
    en_at = text.find(en)
    zh_at = text.find(zh)
    assert "l-en" in text[max(0, en_at - 200):en_at]
    assert "l-zh" in text[max(0, zh_at - 200):zh_at]
    assert "h.benchmark" in text
    assert "h.as_of" in text
    piece = text[text.find(guard):]
    piece = piece[:piece.find("</script>")]
    assert re.search(r"\d{4}-\d{2}-\d{2}", piece) is None
    assert "SPY" not in piece


def test_compute_declares_reconstructed_rs_history_contract(monkeypatch):
    panel = _rs_history_panel(520)
    monkeypatch.setattr(sc, "yahoo_closes", lambda basis="tr": panel.copy())
    monkeypatch.setattr(
        sc.config,
        "load",
        lambda: {"engine": {"rs_ranking": {"benchmark": "SPY"}}},
    )

    def fake_build_sector(ticker, meta, closes, win_start, closes_px=None):
        if ticker != "XLK":
            return None
        live = sc._leadership(closes, ticker)
        return {
            "id": "xlk",
            "ticker": "XLK",
            "kind": "sector",
            "name": "Technology",
            "price": [{"x": 2026.0, "v": 100.0}],
            "osc": [{"x": 2026.0, "v": 50.0}],
            "turns": [],
            "proj": None,
            "now": {
                "phase": "Expansion",
                "pos": 50,
                "rs_21d": live["rs_21d"],
                "rs_63d": live["rs_63d"],
            },
            "rs_history": sc._leadership_history(closes, ticker),
        }

    monkeypatch.setattr(sc, "build_sector", fake_build_sector)
    monkeypatch.setattr(sc, "_load_baskets", lambda: {})
    monkeypatch.setattr(sc, "build_amalgam_family", lambda *args, **kwargs: [])

    data = sc.compute()
    assert data is not None
    assert data["meta"]["rs_history"] == {
        "schema": "sector_cycles.rs_history.v1",
        "mode": "reconstructed_price_history",
        "naturally_observed": False,
        "basis": "tr",
        "benchmark": "SPY",
        "horizons_sessions": [21, 63],
        "max_points_per_sector": 252,
        "as_of": str(panel.index[-1].date()),
        "min_history_sessions": 210,
        "rows_excluded_nonfinite": 0,
        "benchmark_ffill_limit_sessions": 5,
        "source_cohort": {"registry": "engine.sector_cycles.SECTORS", "tickers": ["XLK"]},
    }
    assert data["sectors"][0]["rs_history"]
    assert data["sectors"][0]["rs_history"][-1]["rs_21d"] == data["sectors"][0]["now"]["rs_21d"]
    assert data["sectors"][0]["rs_history"][-1]["rs_63d"] == data["sectors"][0]["now"]["rs_63d"]


def _run_page_date_scripts(meta, template="sector_cycles.html.j2"):
    """Runs the page's date scripts the way a browser orders them: parse, deferred data, DOMContentLoaded."""
    import json
    import re
    import shutil
    import subprocess

    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    root = Path(__file__).resolve().parents[1]
    text = (root / "templates" / template).read_text(encoding="utf-8")
    scripts = [b for b in re.findall(r"<script>(.*?)</script>", text, re.S) if "sc-asof" in b]
    assert scripts
    source = """
var listeners = {};
var kids = [];
var asofEl = {textContent: 'PARSED', parentNode: {appendChild: function (c) { kids.push(c); }}};
var document = {
  getElementById: function (id) { return id === 'sc-asof' ? asofEl : null; },
  createElement: function (tag) { return {tag: tag, className: '', textContent: ''}; },
  addEventListener: function (ev, fn) { (listeners[ev] = listeners[ev] || []).push(fn); },
};
var window = {};
""" + "\n".join(scripts) + """
var atParse = asofEl.textContent;
window.SECTOR_CYCLES = {meta: """ + json.dumps(meta) + """};
(listeners.DOMContentLoaded || []).forEach(function (f) { f(); });
console.log(JSON.stringify({atParse: atParse, date: asofEl.textContent, kids: kids}));
"""
    done = subprocess.run([node, "-e", source], capture_output=True, text=True, timeout=30, check=True)
    return json.loads(done.stdout)


@pytest.mark.parametrize(
    "template",
    ["sector_cycles.html.j2", "sector_cycles_china.html.j2", "country_cycles.html.j2"],
)
def test_cycle_page_prints_its_date_after_the_deferred_data(template):
    out = _run_page_date_scripts({"asOf": "2026-10-30"}, template)
    assert out["atParse"] == "PARSED"
    assert out["date"] == "2026-10-30"
    assert out["kids"] == []


def _two_fund_scorecard():
    """Two funds whose met turns (5) are not the same number as right calls (6)."""
    return {
        "as_of": "2026-07-02T18:59:30.481487+00:00",
        "cohorts": {
            "BACKTEST": {
                "cohort": "BACKTEST",
                "turn_pr": {
                    "per_instrument": {
                        "xlk": {
                            "tp": 2,
                            "fp": 32,
                            "fn": 13,
                            "n_truth_turns": 15,
                            "tau_months": 3,
                        },
                        "xle": {
                            "tp": 4,
                            "fp": 42,
                            "fn": 10,
                            "n_truth_turns": 13,
                            "tau_months": 3,
                        },
                    },
                    "pooled": {"tp": 6, "fp": 74, "fn": 23},
                },
            }
        },
    }


def _scorecard_path(tmp_path, payload):
    import json

    path = tmp_path / "score.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_backtest_turn_record_pools_met_apart_from_right(tmp_path):
    from scripts.build_sector_cycles import backtest_turn_record

    path = _scorecard_path(tmp_path, _two_fund_scorecard())
    got = backtest_turn_record(path)
    assert got == {
        "as_of": "2026-07-02",
        "tau_months": 3,
        "funds": ["xle", "xlk"],
        "turns": 28,
        "met": 5,
        "right": 6,
        "false": 74,
    }


def test_backtest_turn_record_missing_path_is_none(tmp_path):
    from scripts.build_sector_cycles import backtest_turn_record

    missing = tmp_path / "missing.json"
    assert backtest_turn_record(missing) is None


@pytest.mark.parametrize(
    "kind",
    ["bool", "fn_over", "tau", "pooled", "as_of", "empty", "cohort"],
)
def test_backtest_turn_record_rejects_a_bad_file(tmp_path, kind):
    from scripts.build_sector_cycles import backtest_turn_record

    payload = _two_fund_scorecard()
    cohort = payload["cohorts"]["BACKTEST"]
    turn = cohort["turn_pr"]
    rows = turn["per_instrument"]
    if kind == "bool":
        rows["xle"]["tp"] = True
    elif kind == "fn_over":
        rows["xle"]["fn"] = 14
    elif kind == "tau":
        rows["xlk"]["tau_months"] = 4
    elif kind == "pooled":
        turn["pooled"]["tp"] = 7
    elif kind == "as_of":
        payload["as_of"] = "July 2"
    elif kind == "empty":
        turn["per_instrument"] = {}
    elif kind == "cohort":
        cohort["cohort"] = "PAPER"
    else:
        raise AssertionError(kind)
    path = _scorecard_path(tmp_path, payload)
    assert backtest_turn_record(path) is None


def test_committed_turn_record_matches_its_pooled_counts():
    import json
    from scripts.build_sector_cycles import backtest_turn_record

    root = Path(__file__).resolve().parents[1]
    path = root / "data" / "sector_cycles" / "scorecards"
    path = path / "promises_price_v1_zz14_v0.json"
    if not path.is_file():
        pytest.skip("scorecard promises_price_v1_zz14_v0.json is absent")
    raw = json.loads(path.read_text(encoding="utf-8"))
    got = backtest_turn_record(path)
    pooled = raw["cohorts"]["BACKTEST"]["turn_pr"]["pooled"]
    assert got["right"] == pooled["tp"]
    assert got["false"] == pooled["fp"]
    assert got["turns"] - got["met"] == pooled["fn"]
    assert got["as_of"] == raw["as_of"][:10]


def test_sector_cycles_template_has_no_per_card_turn_count():
    text = _template_text("sector_cycles.js")
    assert "function turnRecordText(" in text
    assert "function mountTurnRecord(" in text
    assert "mountTurnRecord(sortedActive())" in text
    assert "turnCallLine" not in text
    assert "per_instrument" not in text
    assert "17 of 98" not in text
    assert "409" not in text


_TURN_BANNED = (
    "verdict",
    "falsified",
    "failed",
    "passed",
    "proven",
    "validated",
    "已验证",
    "live",
    "实时",
    "forecast",
    "falsifier",
    "refuted",
    "申报",
    "z-score",
    "percentile rank",
    "证伪",
)


def _turn_record_sentence(record, lang):
    """Run shipped turnRecordText in node, same pattern as _hz_tip."""
    import json
    import re
    import shutil
    import subprocess

    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    text = _template_text("sector_cycles.js")
    pattern = r"\n  function turnRecordText\(r\) \{\n(?:.*\n)*?  \}\n"
    match = re.search(pattern, text)
    assert match is not None
    header = (
        "function L(en, zh) { return "
        + json.dumps(lang)
        + ' === "zh" ? zh : en; }'
    )
    call = "console.log(turnRecordText(" + json.dumps(record) + "));"
    source = "\n".join([header, match.group(0), call])
    done = subprocess.run(
        [node, "-e", source],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return done.stdout.strip()


def _assert_no_turn_ban(text):
    folded = text.lower()
    for word in _TURN_BANNED:
        assert word.lower() not in folded


def test_turn_record_text_reads_the_record_in_both_languages():
    sample = {
        "as_of": "2026-07-02",
        "tau_months": 3,
        "funds": ["a", "b"],
        "turns": 28,
        "met": 5,
        "right": 6,
        "false": 74,
    }
    en = _turn_record_sentence(sample, "en")
    zh = _turn_record_sentence(sample, "zh")
    for bit in (
        "2026-07-02",
        "earlier version",
        "not a record of the method behind this month",
        "met 5 of 28 real turns",
        "6 calls were right and 74 were false",
        "within 3 months",
    ):
        assert bit in en
    for bit in (
        "2026-07-02",
        "早期版本",
        "28 个实际转折中的 5 个",
        "正确 6 次",
        "错误 74 次",
        "3 个月",
    ):
        assert bit in zh
    other = {
        "as_of": "2025-01-31",
        "tau_months": 4,
        "funds": ["a", "b", "c"],
        "turns": 40,
        "met": 9,
        "right": 11,
        "false": 2,
    }
    en2 = _turn_record_sentence(other, "en")
    zh2 = _turn_record_sentence(other, "zh")
    assert "2025-01-31" in en2
    assert "met 9 of 40 real turns" in en2
    assert "11 calls were right and 2 were false" in en2
    assert "within 4 months" in en2
    assert "2025-01-31" in zh2
    assert "40 个实际转折中的 9 个" in zh2
    assert "正确 11 次" in zh2
    assert "错误 2 次" in zh2
    assert "4 个月" in zh2
    _assert_no_turn_ban(en)
    _assert_no_turn_ban(zh)
    _assert_no_turn_ban(en2)
    _assert_no_turn_ban(zh2)


def test_backtest_turn_record_rejects_a_bool_fn_when_pooled_matches(tmp_path):
    from scripts.build_sector_cycles import backtest_turn_record

    payload = _two_fund_scorecard()
    turn = payload["cohorts"]["BACKTEST"]["turn_pr"]
    rows = turn["per_instrument"]
    # False is a bool. As a count it would add like 0 and still match pooled.
    rows["xle"]["fn"] = False
    turn["pooled"] = {"tp": 6, "fp": 74, "fn": 13}
    path = _scorecard_path(tmp_path, payload)
    assert backtest_turn_record(path) is None


def test_backtest_turn_record_rejects_fn_above_truth_when_pooled_matches(tmp_path):
    from scripts.build_sector_cycles import backtest_turn_record

    payload = _two_fund_scorecard()
    turn = payload["cohorts"]["BACKTEST"]["turn_pr"]
    rows = turn["per_instrument"]
    rows["xle"]["fn"] = 14
    turn["pooled"]["fn"] = 27
    path = _scorecard_path(tmp_path, payload)
    assert backtest_turn_record(path) is None


def test_backtest_turn_record_empty_rows_without_pooled_is_none(tmp_path):
    from scripts.build_sector_cycles import backtest_turn_record

    payload = _two_fund_scorecard()
    turn = payload["cohorts"]["BACKTEST"]["turn_pr"]
    turn["per_instrument"] = {}
    del turn["pooled"]
    path = _scorecard_path(tmp_path, payload)
    assert backtest_turn_record(path) is None


def test_backtest_turn_record_as_of_lacking_three_parts_is_none(tmp_path):
    from scripts.build_sector_cycles import backtest_turn_record

    payload = _two_fund_scorecard()
    # Ten characters, one hyphen, all digits: a missing part check must not raise.
    payload["as_of"] = "2026-07021"
    path = _scorecard_path(tmp_path, payload)
    assert backtest_turn_record(path) is None


def test_main_writes_turn_record_into_the_core_file(monkeypatch, tmp_path):
    import json
    from scripts import build_sector_cycles

    root = tmp_path
    folder = root / "data" / "sector_cycles" / "scorecards"
    folder.mkdir(parents=True)
    name = "promises_price_v1_zz14_v0.json"
    payload = _two_fund_scorecard()
    (folder / name).write_text(json.dumps(payload), encoding="utf-8")
    templates = root / "templates"
    templates.mkdir()
    page = templates / "sector_cycles.html.j2"
    page.write_text("ok\n", encoding="utf-8")
    monkeypatch.setattr(build_sector_cycles.config, "ROOT", root)
    monkeypatch.setattr(
        build_sector_cycles.config,
        "load",
        lambda: {"storage": {"site_dir": "site"}},
    )
    monkeypatch.setattr(sc, "compute", lambda: {"sectors": [{"id": "xlk"}]})
    assert build_sector_cycles.main() == 0
    path = root / "site" / "sector_cycles_data.js"
    text = path.read_text(encoding="utf-8")
    body = text.split("=", 1)[1]
    assert body.endswith(";\n")
    core = json.loads(body[:-2])
    got = core["turn_record"]
    assert got["funds"] == ["xle", "xlk"]
    assert got["turns"] == 28
    assert got["met"] == 5
    assert got["right"] == 6
    assert got["false"] == 74
    assert got["as_of"] == "2026-07-02"
    assert got["tau_months"] == 3


def _shown_turn_record():
    return {
        "as_of": "2026-07-02",
        "tau_months": 3,
        "funds": ["xle", "xlk"],
        "turns": 28,
        "met": 5,
        "right": 6,
        "false": 74,
    }


def _js_fn(name):
    import re

    text = _template_text("sector_cycles.js")
    head = "\n  function " + name + r"\("
    pattern = head + r"[^)]*\) \{\n(?:.*\n)*?  \}\n"
    found = re.search(pattern, text)
    assert found is not None
    return found.group(0)


def _mount_shots(lang, is_cn, record, lists):
    import json
    import shutil
    import subprocess

    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    flag = "true" if is_cn else "false"
    prelude = "\n".join([
        "function L(en, zh) { return " + json.dumps(lang) + ' === "zh" ? zh : en; }',
        "var IS_CN = " + flag + ";",
        "var DATA = { turn_record: " + json.dumps(record) + " };",
        "var created = [];",
        "var calls = [];",
        "var byId = {};",
        "var grid = {",
        "  insertAdjacentElement: function (where, node) {",
        '    calls.push({ op: "insertAdjacentElement", where: where });',
        "    if (node.id) byId[node.id] = node;",
        "  },",
        "  appendChild: function (node) {",
        '    calls.push({ op: "appendChild" });',
        "    if (node.id) byId[node.id] = node;",
        "  }",
        "};",
        "var document = {",
        "  createElement: function (tag) {",
        "    var node = {",
        "      tagName: tag,",
        '      id: "",',
        '      className: "",',
        "      hidden: false,",
        '      textContent: ""',
        "    };",
        "    created.push(node);",
        "    return node;",
        "  },",
        "  getElementById: function (id) {",
        '    if (id === "sc-cards") return grid;',
        "    return byId[id] || null;",
        "  }",
        "};",
        "function el(tag, cls) {",
        "  var node = document.createElement(tag);",
        "  if (cls) node.className = cls;",
        "  return node;",
        "}",
        _js_fn("turnRecordText"),
        _js_fn("mountTurnRecord"),
        "var lists = " + json.dumps(lists) + ";",
        "var shots = [];",
        "for (var n = 0; n < lists.length; n++) {",
        "  mountTurnRecord(lists[n]);",
        '  var node = byId["sc-turnrec"] || null;',
        "  var expect = turnRecordText(DATA.turn_record);",
        "  var ops = calls.map(function (c) {",
        '    return c.where ? c.op + ":" + c.where : c.op;',
        "  });",
        "  shots.push({",
        "    created: created.length,",
        "    hidden: node ? node.hidden : null,",
        '    text: node ? node.textContent : "",',
        "    match: !!(node && node.textContent === expect),",
        "    ops: ops",
        "  });",
        "}",
        "console.log(JSON.stringify(shots));",
    ])
    done = subprocess.run(
        [node, "-e", prelude],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def test_mount_turn_record_hides_matching_funds_when_is_cn():
    lists = [[{"id": "xle"}, {"id": "xlk"}]]
    shots = _mount_shots("en", True, _shown_turn_record(), lists)
    assert shots[0]["hidden"] is True
    assert shots[0]["text"] == ""


def test_mount_turn_record_hides_when_ids_miss_the_fund_list():
    # Shenwan ids from the China page, not the US funds on the record.
    lists = [[{"id": "801080"}, {"id": "801750"}]]
    shots = _mount_shots("en", False, _shown_turn_record(), lists)
    assert shots[0]["hidden"] is True
    assert shots[0]["text"] == ""


def test_mount_turn_record_places_the_note_after_the_grid():
    lists = [[{"id": "xlk"}]]
    shots = _mount_shots("en", False, _shown_turn_record(), lists)
    ops = shots[0]["ops"]
    assert "insertAdjacentElement:afterend" in ops
    assert "appendChild" not in "".join(ops)


def test_mount_turn_record_hides_same_element_after_the_match_goes():
    lists = [[{"id": "xlk"}], []]
    shots = _mount_shots("en", False, _shown_turn_record(), lists)
    assert shots[0]["hidden"] is False
    assert shots[0]["match"] is True
    assert shots[1]["hidden"] is True
    assert shots[1]["text"] == ""
    assert shots[0]["created"] == 1
    assert shots[1]["created"] == 1


@pytest.mark.parametrize("lang", ["en", "zh"])
def test_mount_turn_record_shows_the_sentence_for_a_matching_fund(lang):
    lists = [[{"id": "xlk"}]]
    shots = _mount_shots(lang, False, _shown_turn_record(), lists)
    assert shots[0]["hidden"] is False
    assert shots[0]["match"] is True
    assert shots[0]["text"] != ""


def test_sector_page_prints_the_rs_sentence_from_the_record():
    out = _run_page_date_scripts({
        "asOf": "2026-10-30",
        "rs_history": {"naturally_observed": False, "basis": "tr", "benchmark": "SPY", "as_of": "2026-10-29"},
    })
    assert [k["tag"] for k in out["kids"]] == ["br", "span", "span"]
    en, zh = out["kids"][1], out["kids"][2]
    assert en["className"] == "l-en"
    assert en["textContent"] == (
        "RS rank is rebuilt from total-return price history against SPY, through 2026-10-29."
        " It is not an observed record."
    )
    assert zh["className"] == "l-zh"
    assert zh["textContent"] == "相对强度排名由总回报价格历史重建，基准 SPY，截至 2026-10-29。并非当时观察到的记录。"


@pytest.mark.parametrize(
    "history",
    [
        {"naturally_observed": True, "basis": "tr", "benchmark": "SPY", "as_of": "2026-10-29"},
        {"naturally_observed": False, "basis": "pr", "benchmark": "SPY", "as_of": "2026-10-29"},
    ],
)
def test_sector_page_prints_no_rs_sentence_when_it_would_be_wrong(history):
    assert _run_page_date_scripts({"asOf": "2026-10-30", "rs_history": history})["kids"] == []


def _template_text(name):
    """A page source by name, for the tests that run a shipped function in node."""
    return (Path(__file__).resolve().parents[1] / "templates" / name).read_text(encoding="utf-8")


def _hz_tip(hz, key, passed, lang):
    """Run the shipped tooltip function in node with the page's picker for one language."""
    import json
    import re
    import shutil
    import subprocess

    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    text = _template_text("sector_cycles.js")
    match = re.search(r"\n  function _hzTip\(hz, key, pass\) \{\n(?:.*\n)*?  \}\n", text)
    assert match is not None
    source = "\n".join([
        "function L(en, zh) { return " + json.dumps(lang) + ' === "zh" ? zh : en; }',
        match.group(0),
        "console.log(_hzTip(" + json.dumps(hz) + ", " + json.dumps(key) + ", " + json.dumps(passed) + "));",
    ])
    done = subprocess.run([node, "-e", source], capture_output=True, text=True, timeout=30, check=True)
    return done.stdout.strip()


@pytest.mark.parametrize(
    "passed,lang,present,absent",
    [
        (True, "en", ["PASSED the W4.2 gate", "UP/13w", "Epoch: 2031-Q1.", "Cohort still accruing.", "Not checked against later outcomes."], ["validated", "live", "校准"]),
        (True, "zh", ["校准模型概率", "UP/13w", "Epoch: 2031-Q1。", "样本仍在累积。", "未用之后的结果核对。"], ["validated", "live", "Calibrated", "Not checked"]),
        (False, "en", ["did NOT pass the W4.2 gate", "UP/13w", "not a model output.", "Not checked against later outcomes."], ["validated", "live", "Cohort still", "基准率"]),
        (False, "zh", ["KM 基准率先验", "UP/13w", "不是模型输出。", "未用之后的结果核对。"], ["validated", "live", "样本仍在累积", "base-rate", "Not checked"]),
    ],
)
def test_hazard_tooltip_says_what_the_figure_is_in_the_readers_language(passed, lang, present, absent):
    got = _hz_tip({"epoch": "2031-Q1", "direction": "UP"}, "13w", passed, lang)
    assert [p for p in present if p not in got] == []
    assert [a for a in absent if a in got] == []


@pytest.mark.parametrize(
    "lang,want,other",
    [
        ("en", " · revision-optimistic (quad not PIT-vintaged)", "结果可能偏乐观"),
        ("zh", " · 结果可能偏乐观（象限未按当时版本回放）", "revision-optimistic"),
    ],
)
def test_hazard_tooltip_revision_clause_reads_in_the_readers_language(lang, want, other):
    hz = {"epoch": "2031-Q1", "direction": "UP", "revision_optimistic": True}
    got = _hz_tip(hz, "13w", True, lang)
    assert want in got and other not in got
    assert want not in _hz_tip({"epoch": "2031-Q1", "direction": "UP"}, "13w", True, lang)

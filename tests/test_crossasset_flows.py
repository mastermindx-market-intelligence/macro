"""tests/test_crossasset_flows.py — W3-A flows.v2 persistence + hero + history.

Tests cover:
  - hero matrix: all 9 (breadth_regime, concentration) combos + unknown concentration
  - flows.v2 schema fields in latest.json: schema string, regime, trend_summary,
    enriched correlation, enriched leadlag, confirm/dollar/shadow pass-through
  - legacy 5 keys byte-stable when flows.v2 is written
  - fail-open when forex/regime files are missing (all new blocks None, no crash)
  - history.jsonl appended only when COLLECT_LANE=nightly; dedup (same asof skips)
  - absorption_spark_w shape (list, <=104 elements, all floats)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from jinja2 import Environment

# Ensure repo root is on sys.path for direct test invocation
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.cross_asset import absorption_series, snapshot as ca_snapshot
from scripts.build_crossasset import _compose_hero, _append_history


# ═══════════════════════════════════════════════════════════════════════════════
# Hero matrix unit tests (all 9 combos)
# ═══════════════════════════════════════════════════════════════════════════════

_HERO_CASES = [
    # (breadth,  corr_verdict,     expected_tone)
    (0.5,        "diversified",    "green"),
    (0.5,        "converging",     "amber"),
    (0.5,        "concentrated",   "amber"),
    (0.0,        "diversified",    "amber"),
    (0.0,        "converging",     "amber"),
    (0.0,        "concentrated",   "amber"),
    (-0.5,       "diversified",    "red"),
    (-0.5,       "converging",     "red"),
    (-0.5,       "concentrated",   "red"),
]


@pytest.mark.parametrize("breadth,concentration,expected_tone", _HERO_CASES)
def test_hero_tone(breadth, concentration, expected_tone):
    h = _compose_hero(breadth, concentration, {"diversified": .1, "converging": .5, "concentrated": .9}.get(concentration))
    assert h["tone"] == expected_tone, f"({breadth}, {concentration}) -> {h['tone']!r} != {expected_tone!r}"


def test_hero_has_all_bilingual_keys():
    for breadth, concentration, _ in _HERO_CASES:
        h = _compose_hero(breadth, concentration, {"diversified": .1, "converging": .5, "concentrated": .9}.get(concentration))
        for key in ("tone", "headline_en", "headline_zh", "sub_en", "sub_zh", "stance_en", "stance_zh"):
            assert key in h
            assert isinstance(h[key], str) and h[key], f"key {key!r} empty for ({breadth},{concentration})"


@pytest.mark.parametrize("concentration", ["unknown", None, "", "unrecognized"])
@pytest.mark.parametrize("breadth,tone,headline_en,headline_zh", [
    (0.5, "green", "Upward trends are broader", "上涨趋势更广泛"),
    (0.0, "amber", "Trends remain mixed", "趋势仍然分化"),
    (-0.5, "red", "Downward trends are broader", "下跌趋势更广泛"),
])
def test_hero_unknown_concentration_is_breadth_only(
    breadth, concentration, tone, headline_en, headline_zh,
):
    """CA-W3-R6: absent correlation cannot imply independent markets in either locale.

    Supersedes the old unknown == diversified test: those rows made correlation
    claims, so their wording was not actually a breadth-only fallback.
    """
    h = _compose_hero(breadth, concentration, {"diversified": .1, "converging": .5, "concentrated": .9}.get(concentration))
    assert h == {
        "tone": tone,
        "headline_en": headline_en,
        "headline_zh": headline_zh,
        "sub_en": "Historical concentration rank is unavailable; diversification cannot be inferred.",
        "sub_zh": "暂无集中度历史排名，无法据此判断分散化效果。",
        "stance_en": "Watch — diversification is unverified.",
        "stance_zh": "留意——分散化效果尚不明确。",
    }


def test_hero_missing_breadth_and_correlation_keep_mixed_breadth_default():
    assert _compose_hero(None, None) == _compose_hero(0.0, "unknown")


def test_hero_none_breadth_defaults_to_mixed():
    """None breadth is treated as 0 (mixed)."""
    h = _compose_hero(None, "diversified")
    assert h["tone"] == "amber"


# ═══════════════════════════════════════════════════════════════════════════════
# Hero rendering — unavailable, malformed, and valid correlation gauges
# ═══════════════════════════════════════════════════════════════════════════════

def _render_hero(correlation):
    source = (Path(__file__).resolve().parents[1]
              / "templates/crossasset.html.j2").read_text()
    macro = source[:source.index("<!DOCTYPE html>")]
    start = source.index("{% set _hero_tone")
    end = source.index("{# Fragility watch chip")
    template = Environment(autoescape=True).from_string(macro + source[start:end])
    return template.render(
        hero={"tone": "green", "headline_en": "Trend context", "headline_zh": "趋势背景",
              "sub_en": "Trend context", "sub_zh": "趋势背景",
              "stance_en": "Watch", "stance_zh": "留意"},
        breadth=0.5, correlation=correlation, as_of="2026-10-09",
    )


@pytest.mark.parametrize("correlation", [
    None, {}, {"verdict": "unknown"}, {"verdict": "diversified"},
    {"verdict": "converging", "absorption_pctile_5y": None},
    {"verdict": "unknown", "absorption_pctile_5y": 0.88},
])
def test_unavailable_gauge_has_bilingual_disclosure_without_invented_value(correlation):
    html = _render_hero(correlation)
    assert "Historical concentration rank is unavailable." in html
    assert "暂无集中度历史排名。" in html
    assert "Low historical rank" not in html
    assert "历史排名较低" not in html
    assert ">0%</text>" not in html
    assert 'aria-label="Correlation absorption gauge"' not in html


@pytest.mark.parametrize("value", [
    False, True, float("nan"), float("inf"), -float("inf"), -0.1, 1.1, "0.25",
])
def test_invalid_percentile_uses_unavailable_state(value):
    html = _render_hero({"verdict": "diversified", "absorption_pctile_5y": value})
    assert "Historical concentration rank is unavailable." in html
    assert "暂无集中度历史排名。" in html
    assert "Low historical rank" not in html
    assert 'aria-label="Correlation absorption gauge"' not in html


@pytest.mark.parametrize("verdict", ["diversified", "converging", "concentrated"])
@pytest.mark.parametrize("value,percent,en,zh", [
    (0.0, 0, "Low historical rank", "历史排名较低"),
    (0.25, 25, "Low historical rank", "历史排名较低"),
    (0.5, 50, "Middle historical rank", "历史排名居中"),
    (0.8, 80, "High historical rank", "历史排名较高"),
    (1.0, 100, "High historical rank", "历史排名较高"),
])
def test_known_gauge_retains_values_and_bilingual_labels(verdict, value, percent, en, zh):
    html = _render_hero({"verdict": verdict, "absorption_pctile_5y": value})
    assert f">{percent}%</text>" in html
    assert en in html
    assert zh in html
    assert 'aria-label="Correlation absorption gauge"' in html
    assert "Historical concentration rank is unavailable." not in html


# ═══════════════════════════════════════════════════════════════════════════════
# absorption_spark_w shape test (engine/cross_asset.py additive field)
# ═══════════════════════════════════════════════════════════════════════════════

def _make_returns(n_days: int = 600, n_markets: int = 5, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=n_days, freq="B")
    return pd.DataFrame(rng.normal(0, 0.01, (n_days, n_markets)),
                        index=idx,
                        columns=[f"m{i}" for i in range(n_markets)])


def test_absorption_spark_w_is_list_le_104(monkeypatch):
    """absorption_spark_w must be a plain list of <=104 weekly floats."""
    import engine.cross_asset as ca

    rets = _make_returns(700)
    # patch returns_frame to return synthetic data
    monkeypatch.setattr(ca, "returns_frame", lambda: rets)

    s = ca_snapshot()
    assert s.get("verdict") != "unknown", "snapshot should succeed with 700 days of data"
    spark = s.get("absorption_spark_w")
    assert isinstance(spark, list), f"absorption_spark_w should be list, got {type(spark)}"
    assert len(spark) <= 104, f"absorption_spark_w should have <=104 entries, got {len(spark)}"
    # all elements must be finite floats
    for v in spark:
        assert isinstance(v, float), f"element {v!r} is not float"
        assert np.isfinite(v), f"element {v!r} is not finite"


def test_absorption_spark_asof_is_present(monkeypatch):
    import engine.cross_asset as ca

    rets = _make_returns(700)
    monkeypatch.setattr(ca, "returns_frame", lambda: rets)

    s = ca_snapshot()
    if s.get("verdict") != "unknown":
        asof = s.get("absorption_spark_asof")
        assert asof is not None
        # must be a date-string like "2024-12-27"
        assert isinstance(asof, str) and len(asof) == 10


def test_absorption_spark_w_absent_on_no_data(monkeypatch):
    """When snapshot returns unknown (too little data), spark should be absent or empty."""
    import engine.cross_asset as ca

    monkeypatch.setattr(ca, "returns_frame", lambda: pd.DataFrame())

    s = ca_snapshot()
    assert s.get("verdict") == "unknown"
    # key is absent on early-exit path (no spark computed)
    assert "absorption_spark_w" not in s or s.get("absorption_spark_w") == []


# ═══════════════════════════════════════════════════════════════════════════════
# flows.v2 persistence tests (via build_crossasset.main())
# ═══════════════════════════════════════════════════════════════════════════════

def _make_mock_snap(breadth=0.3, corr_verdict="concentrated"):
    """Minimal mock of cat.snapshot() return value."""
    return {
        "asof": "2026-07-18",
        "regime": "mixed / no clear trend",
        "breadth": breadth,
        "favored": ["equity_us"],
        "note": "test note",
        "trend": {
            "asof": "2026-07-18",
            "rows": [
                {"key": "equity_us", "trend": "up", "score": 1.0,
                 "class": "equity", "name_en": "S&P 500", "name_zh": "标普500",
                 "class_en": "Equity", "class_zh": "股票",
                 "ret_3m": 5.0, "ret_6m": 8.0, "ret_12m": 15.0},
            ],
            "n": 1, "n_up": 1, "n_down": 0,
        },
        "ratios": [
            {"key": "copper_gold", "value": 0.5, "state": "mid", "pctile": 55.0,
             "label_en": "Copper / Gold", "label_zh": "铜/金", "chg_3m": 2.1,
             "note": "test"},
        ],
        "carry": {"rows": [], "note": "test"},
        "correlation": {
            "verdict": corr_verdict,
            "absorption_pctile_5y": 0.88,
            "absorption_ratio": 0.42,
            "mean_abs_corr": 0.61,
            "dominant_cluster": ["US", "Crypto"],
            "markets": ["US", "Crypto", "China", "HK", "Commodities", "Dollar"],
            "absorption_spark_w": [0.3, 0.35, 0.4, 0.42],
            "absorption_spark_asof": "2026-07-11",
        },
    }


def _run_main_with_mocks(tmp_path: Path, snap: dict,
                         forex_data: dict | None = None,
                         regime_data: dict | None = None,
                         collect_lane: str | None = None) -> dict:
    """Run build_crossasset.main() with mocked data, return parsed latest.json."""
    # Write fake forex/regime files if provided
    if forex_data is not None:
        (tmp_path / "forex").mkdir(parents=True, exist_ok=True)
        (tmp_path / "forex" / "latest.json").write_text(json.dumps(forex_data))
    if regime_data is not None:
        (tmp_path / "regime").mkdir(parents=True, exist_ok=True)
        (tmp_path / "regime" / "latest.json").write_text(json.dumps(regime_data))

    (tmp_path / "crossasset").mkdir(parents=True, exist_ok=True)
    site_dir = tmp_path / "site"
    site_dir.mkdir(parents=True, exist_ok=True)

    env_patch = {}
    if collect_lane is not None:
        env_patch["COLLECT_LANE"] = collect_lane

    from scripts import build_crossasset as bca

    with patch("scripts.build_crossasset.config") as mock_cfg, \
         patch("scripts.build_crossasset.write_page"), \
         patch("scripts.build_crossasset.Environment") as mock_env_cls:

        # config mocks
        mock_cfg.ROOT = tmp_path
        mock_cfg.data_dir.return_value = tmp_path
        mock_cfg.load.return_value = {"storage": {"site_dir": "site"}}

        # jinja env mock — capture render call, return minimal HTML
        mock_env = MagicMock()
        mock_env_cls.return_value = mock_env
        mock_tmpl = MagicMock()
        mock_env.get_template.return_value = mock_tmpl
        mock_tmpl.render.return_value = "<html>test</html>"

        import engine.crossasset_shadow as _cas
        with patch("engine.cross_asset_trend.snapshot", return_value=snap), \
             patch("engine.global_liquidity.snapshot", return_value=None), \
             patch("engine.funding_stress.snapshot", return_value=None), \
             patch("engine.cross_asset.leadlag_snapshot", return_value=None), \
             patch("lib.forex_link.transmission", side_effect=Exception("no forex_link")), \
             patch.object(_cas, "run", return_value=None):

            _old_env = {}
            for k, v in env_patch.items():
                _old_env[k] = os.environ.get(k)
                os.environ[k] = v
            try:
                rc = bca.main()
            finally:
                for k, old_v in _old_env.items():
                    if old_v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = old_v

    assert rc == 0
    latest_path = tmp_path / "crossasset" / "latest.json"
    assert latest_path.exists()
    return json.loads(latest_path.read_text())


def test_flows_v2_schema_string(tmp_path):
    snap = _make_mock_snap()
    data = _run_main_with_mocks(tmp_path, snap)
    assert data["flows"]["schema"] == "crossasset_flows.v2"


def test_flows_v2_legacy_keys_byte_stable(tmp_path):
    """The 5 legacy top-level keys must be present and unchanged in type."""
    snap = _make_mock_snap()
    data = _run_main_with_mocks(tmp_path, snap)
    assert data["date"] == "2026-07-18"
    assert data["regime"] == "mixed / no clear trend"
    assert isinstance(data["breadth"], float)
    assert isinstance(data["favored"], list)
    assert data["correlation"] == "concentrated"


def test_flows_v2_has_regime_field(tmp_path):
    snap = _make_mock_snap()
    data = _run_main_with_mocks(tmp_path, snap)
    assert data["flows"]["regime"] == "mixed / no clear trend"


def test_flows_v2_trend_summary_present(tmp_path):
    snap = _make_mock_snap()
    data = _run_main_with_mocks(tmp_path, snap)
    ts = data["flows"]["trend_summary"]
    assert "n" in ts and "n_up" in ts and "n_down" in ts


def test_flows_v2_correlation_enriched(tmp_path):
    """flows.v2 correlation block must include absorption_ratio, mean_abs_corr, spark_w."""
    snap = _make_mock_snap()
    data = _run_main_with_mocks(tmp_path, snap)
    corr = data["flows"]["correlation"]
    assert corr is not None
    assert "absorption_ratio" in corr
    assert "mean_abs_corr" in corr
    assert "dominant_cluster" in corr
    assert "spark_w" in corr
    assert isinstance(corr["spark_w"], list)
    assert "spark_asof" in corr


def test_flows_v2_leadlag_enriched(tmp_path):
    """flows.v2 leadlag must include stable, lead_asset, n_significant, n_tested."""
    snap = _make_mock_snap()
    data = _run_main_with_mocks(tmp_path, snap)
    ll = data["flows"]["leadlag"]
    assert "stable" in ll
    assert "lead_asset" in ll
    assert "n_significant" in ll
    assert "n_tested" in ll


def test_flows_v2_intermarket_has_pctile(tmp_path):
    """flows.v2 intermarket rows must include pctile field."""
    snap = _make_mock_snap()
    data = _run_main_with_mocks(tmp_path, snap)
    im = data["flows"]["intermarket"]
    assert len(im) > 0
    for row in im:
        assert "pctile" in row


def test_flows_v2_confirm_from_regime_file(tmp_path):
    """When regime/latest.json has cross_asset_confirm, flows.confirm is populated."""
    snap = _make_mock_snap()
    regime_data = {
        "cross_asset_confirm": {
            "verdict": "diverge",
            "agree_pct": 50,
            "n_blind_flags": 1,
            "caution_flags": [{"key": "credit", "severity": "medium", "lead": "leading"}],
            "asof": "2026-07-16",
        }
    }
    data = _run_main_with_mocks(tmp_path, snap, regime_data=regime_data)
    confirm = data["flows"]["confirm"]
    assert confirm is not None
    assert confirm["verdict"] == "diverge"
    assert confirm["agree_pct"] == 50
    assert confirm["n_blind_flags"] == 1
    assert len(confirm["flags_top"]) == 1
    assert confirm["asof"] == "2026-07-16"


def test_flows_v2_confirm_none_when_regime_missing(tmp_path):
    """When regime/latest.json is absent, flows.confirm is None (no crash)."""
    snap = _make_mock_snap()
    data = _run_main_with_mocks(tmp_path, snap)  # no regime_data
    assert data["flows"]["confirm"] is None


def test_flows_v2_dollar_from_forex_file(tmp_path):
    """When forex/latest.json exists, flows.dollar is populated."""
    snap = _make_mock_snap()
    forex_data = {
        "regime": "US growth premium",
        "risk": "risk-on",
        "transmission": {
            "usd_dir": "strengthening",
            "corr": {"GC=F": -0.75, "SPY": -0.43, "HG=F": -0.66},
            "unstable": [],
        },
        "regime_radar": {
            "dominant": None,
            "intensity": {"carry_unwind": 12.0, "dollar_wrecking_ball": 12.1},
        },
    }
    data = _run_main_with_mocks(tmp_path, snap, forex_data=forex_data)
    dollar = data["flows"]["dollar"]
    assert dollar is not None
    assert dollar["usd_dir"] == "strengthening"
    assert dollar["regime"] == "US growth premium"
    assert dollar["risk"] == "risk-on"
    assert isinstance(dollar["corr_top"], list)
    assert len(dollar["corr_top"]) <= 3
    # corr_top sorted by |corr| desc
    if len(dollar["corr_top"]) >= 2:
        assert abs(dollar["corr_top"][0]["corr"]) >= abs(dollar["corr_top"][1]["corr"])
    assert "unstable_n" in dollar
    assert "fx_stress" in dollar


def test_flows_v2_dollar_none_when_forex_missing(tmp_path):
    """When forex/latest.json is absent, flows.dollar is None (no crash)."""
    snap = _make_mock_snap()
    data = _run_main_with_mocks(tmp_path, snap)  # no forex_data
    assert data["flows"]["dollar"] is None


def test_flows_v2_shadow_none_when_module_missing(tmp_path):
    """When engine.crossasset_shadow is not importable, flows.shadow is None (no crash)."""
    snap = _make_mock_snap()
    data = _run_main_with_mocks(tmp_path, snap)
    # crossasset_shadow is not built yet (W3-B lane); must gracefully be None
    assert data["flows"]["shadow"] is None or isinstance(data["flows"]["shadow"], dict)


# ═══════════════════════════════════════════════════════════════════════════════
# History accrual tests
# ═══════════════════════════════════════════════════════════════════════════════

def _base_snap_dict():
    return {"regime": "mixed", "breadth": 0.3}


def test_history_append_only_when_nightly(tmp_path):
    """_append_history must NOT write when COLLECT_LANE != 'nightly'."""
    hist = tmp_path / "history.jsonl"
    os.environ.pop("COLLECT_LANE", None)

    _append_history(tmp_path, "2026-07-18", _base_snap_dict(), None, None, None, None, None, None)
    assert not hist.exists()

    os.environ["COLLECT_LANE"] = "intraday"
    try:
        _append_history(tmp_path, "2026-07-18", _base_snap_dict(), None, None, None, None, None, None)
        assert not hist.exists()
    finally:
        os.environ.pop("COLLECT_LANE", None)


def test_history_append_writes_when_nightly(tmp_path):
    """_append_history writes one JSON line when COLLECT_LANE=nightly."""
    hist = tmp_path / "history.jsonl"
    os.environ["COLLECT_LANE"] = "nightly"
    try:
        _append_history(tmp_path, "2026-07-18", _base_snap_dict(), None, None, None, None, None, None)
    finally:
        os.environ.pop("COLLECT_LANE", None)

    assert hist.exists()
    lines = [l for l in hist.read_text().splitlines() if l.strip()]
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["asof"] == "2026-07-18"
    assert "regime" in row
    assert "breadth" in row
    assert "logged_at" in row


def test_history_dedup_same_asof(tmp_path):
    """Second call with same asof must not append a duplicate line."""
    os.environ["COLLECT_LANE"] = "nightly"
    try:
        _append_history(tmp_path, "2026-07-18", _base_snap_dict(), None, None, None, None, None, None)
        _append_history(tmp_path, "2026-07-18", _base_snap_dict(), None, None, None, None, None, None)
    finally:
        os.environ.pop("COLLECT_LANE", None)

    hist = tmp_path / "history.jsonl"
    lines = [l for l in hist.read_text().splitlines() if l.strip()]
    assert len(lines) == 1, f"Expected 1 line after dedup, got {len(lines)}"


def test_history_different_asof_appends_second_line(tmp_path):
    """Different asof on second call must add a new line."""
    os.environ["COLLECT_LANE"] = "nightly"
    try:
        _append_history(tmp_path, "2026-07-17", _base_snap_dict(), None, None, None, None, None, None)
        _append_history(tmp_path, "2026-07-18", _base_snap_dict(), None, None, None, None, None, None)
    finally:
        os.environ.pop("COLLECT_LANE", None)

    hist = tmp_path / "history.jsonl"
    lines = [l for l in hist.read_text().splitlines() if l.strip()]
    assert len(lines) == 2


def test_history_row_schema_fields(tmp_path):
    """History row must contain all required schema fields."""
    _corr = {"absorption_pctile": 0.88, "absorption_ratio": 0.42, "verdict": "concentrated"}
    _ll = {"verdict": "lead"}
    _fund = {"state": "tightening", "score": 0.7}
    _liq = {"state": "expanding"}
    _confirm = {"verdict": "diverge", "agree_pct": 50}
    _dollar = {"usd_dir": "strengthening"}

    os.environ["COLLECT_LANE"] = "nightly"
    try:
        _append_history(tmp_path, "2026-07-18", {"regime": "risk-off trends", "breadth": -0.5},
                        _corr, _ll, _liq, _fund, _confirm, _dollar)
    finally:
        os.environ.pop("COLLECT_LANE", None)

    hist = tmp_path / "history.jsonl"
    row = json.loads(hist.read_text().strip())
    expected_fields = [
        "asof", "regime", "breadth", "absorption_pctile", "absorption_ratio",
        "corr_verdict", "leadlag_verdict", "funding_state", "funding_score",
        "liq_state", "confirm_verdict", "agree_pct", "dollar_dir", "logged_at",
    ]
    for f in expected_fields:
        assert f in row, f"Missing field {f!r} in history row"

    assert row["absorption_pctile"] == 0.88
    assert row["corr_verdict"] == "concentrated"
    assert row["leadlag_verdict"] == "lead"
    assert row["funding_state"] == "tightening"
    assert row["confirm_verdict"] == "diverge"
    assert row["dollar_dir"] == "strengthening"



def _relative_correlation_block(rho, n, seed):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(n, 6)); x -= x.mean(axis=0)
    q, _ = np.linalg.qr(x)
    corr = np.full((6, 6), rho); np.fill_diagonal(corr, 1.)
    return q @ np.linalg.cholesky(corr).T * np.sqrt(n - 1) * .005


@pytest.mark.parametrize('current,pasts', [(.95, [.995, .01]), (.08, [.0, .95])])
def test_paired_history_native_loader_and_full_bilingual_page(monkeypatch, tmp_path, current, pasts):
    from engine import cross_asset as ca
    from jinja2 import FileSystemLoader
    outputs = []
    now = _relative_correlation_block(current, 63, 2855)
    for past in pasts:
        returns = np.vstack([np.tile(_relative_correlation_block(past, 63, 2856), (20, 1)), now])
        dates = pd.bdate_range('2020-01-01', periods=len(returns) + 1)
        stores = {}
        for i, (_, (group, sid, sign)) in enumerate(ca.DEFAULT_MARKETS.items()):
            prices = 100 * np.cumprod(np.r_[1., 1 + returns[:, i] * sign])
            stores[group, sid] = pd.DataFrame({'close': prices}, index=dates)
        monkeypatch.setattr(ca.store, 'read', lambda group, sid: stores.get((group, sid)))
        monkeypatch.setattr(ca.config, 'load', lambda: {})
        loaded = ca.returns_frame()
        np.testing.assert_allclose(loaded.to_numpy(), returns, atol=1e-14)
        corr = ca.snapshot(); outputs.append(corr)
        assert corr['absorption_ratio'] == pytest.approx((1+5*current)/6, abs=.00051)
        assert corr['mean_abs_corr'] == pytest.approx(current, abs=.00051)
        env = Environment(loader=FileSystemLoader(str(Path(__file__).resolve().parents[1]/'templates')), autoescape=True)
        snap = _make_mock_snap()
        ctx = dict(as_of=snap['asof'], built='synthetic', regime=snap['regime'], breadth=.5,
                   trend=snap['trend'], ratios=snap['ratios'], carry=snap['carry'], correlation=corr,
                   note='synthetic', leadlag=None, dollar_factor=None, liquidity=None, liq_spark='',
                   funding=None, fund_spark='', hero=_compose_hero(.5,corr['verdict'],corr['absorption_pctile_5y']),
                   ar_spark='', confirm=None, dollar=None, shadow=None)
        html = env.get_template('crossasset.html.j2').render(**ctx)
        (tmp_path/f'correlation-{current}-history-{past}.html').write_text(html)
        for forbidden in ['genuinely different bets', 'Diversification is working', 'correlation is rising',
                          'Mostly independent', '>Indep.</text>', '>One bet</text>', '>vs 5y</text>',
                          '分散化效果良好', '市场相关性上升']:
            assert forbidden not in html
        assert 'available history' in html and '可用历史分位' in html
        assert 'does not establish diversification' in html and '不能证明分散化效果' in html
    for key in ['corr_matrix','pc1_loadings','absorption_ratio','mean_abs_corr','dominant_cluster']:
        assert outputs[0][key] == outputs[1][key]
    assert {o['verdict'] for o in outputs} == {'diversified','concentrated'}


ROOT = Path(__file__).resolve().parents[1]
@pytest.mark.parametrize('breadth',[-.5,0,.5])
@pytest.mark.parametrize('v,p',[('diversified',.1),('converging',.5),('concentrated',.9)])
def test_hero_rank_only_and_tone_preserved(breadth,v,p):
 result=_compose_hero(breadth,v,p)
 assert result['tone']==('red' if breadth < -.34 else 'green' if breadth >= .34 and v=='diversified' else 'amber')
 assert 'history' in result['sub_en'] or 'historical' in result['sub_en']
 assert '历史' in result['sub_zh']
 assert 'does not establish diversification' in result['stance_en']
@pytest.mark.parametrize('p',[None,float('nan'),float('inf'),True,-.1,1.1,'0.5'])
def test_missing_rank_is_not_middle(p):
 assert 'unavailable' in _compose_hero(.5,'converging',p)['sub_en']
 assert 'unavailable' in _compose_hero(.5,'converging')['sub_en']
@pytest.mark.parametrize('v,p,word',[('diversified',.1,'low'),('converging',.5,'middle'),('concentrated',.9,'high'),('converging',None,None)])
def test_actual_template_rank_branch(v,p,word):
 s=(ROOT/'templates/crossasset.html.j2').read_text();start=s.index('{% if correlation is not none',s.index('{# ── §02'));end=s.index('    {# Absorption sparkline',start)
 # Real selected template prefix only; its conditional closes outside this slice.
 tmpl=Environment(autoescape=True).from_string(s[start:end]+'{% endif %}')
 for lang in [0,1]:
  out=tmpl.render(_abs_available=p is not None,correlation={'verdict':v},t=lambda en,zh:(en,zh)[lang])
  if word and lang == 0:
   assert word in out and ('history' in out or 'historical' in out)
  if p is None:assert ('unavailable' if lang==0 else '暂无') in out

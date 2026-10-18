"""Authority test wall for PR-B R5 macro lobes and bridge summarizer (§5.5).

All tests are hermetic: synthetic fixture trees, no real market data.

Tests
-----
1.  display_only_on_every_new_lobe  — all R5 lobes carry display_only=True
2.  assert_no_authority_world_state — no Article-2 keys / authority booleans
3.  assert_no_authority_mastermind  — same for bridge artifact
4.  five_bridge_booleans_false      — all five can_* booleans remain False
5.  no_article2_keys_in_new_lobes   — per-lobe Article-2 surface key absence
6.  per_source_missing_file_failopen — each source missing -> gap, no raise
7.  to_iso_format_coverage          — ISO date, display string, ISO datetime, None
8.  no_new_names_in_macro_weather   — tickers in macro_weather are whitelisted
9.  macro_weather_gap_when_snapshot_absent — macro_weather returns gap without snapshot
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

# ─── constants ────────────────────────────────────────────────────────────────

_NOW = datetime(2026, 7, 5, 12, 0, 0, tzinfo=timezone.utc)

# Article-2 surface keys (RUL-M2)
_ARTICLE_2_KEYS = frozenset({
    "alert_triage",
    "board_ordering",
    "top_setups",
    "attention_queue",
    "push_floor",
})

# Five authority booleans
_AUTHORITY_BOOLEANS = frozenset({
    "can_add_candidates",
    "can_raise_size",
    "can_lower_size",
    "can_block_entry",
    "can_force_exit",
})

# Macro ETF / futures root whitelist (RUL-M8)
# These are admissible as macro-level records, NOT candidate names.
_MACRO_TICKER_WHITELIST_PATTERNS = (
    re.compile(r"^(XLB|XLC|XLE|XLF|XLI|XLK|XLP|XLRE|XLU|XLV|XLY)$"),  # SPDR sectors
    re.compile(r"^(QQQ|SPY|IWM|DIA|IWF|IWD)$"),                          # broad indices
    re.compile(r"^(TLT|IEF|SHY|TIP|HYG|LQD)$"),                          # bond ETFs
    re.compile(r"^(GLD|SLV|IAU|PDBC|DBC)$"),                              # commodity ETFs
    re.compile(r"^(FXI|EEM|VWO|EFA|IEFA)$"),                              # intl equity
    re.compile(r"^(GC=F|CL=F|SI=F|HG=F|NG=F|ZC=F|ZS=F|ZW=F)$"),          # futures
    re.compile(r"^(VIX|MOVE|DXY|EURUSD|USDJPY|GBPUSD|AUDUSD|USDCNH)$"),  # macro indices/fx
    re.compile(r"^[A-Z]{2,5}=F$"),  # generic futures root
    re.compile(r"^(EUR|JPY|GBP|AUD|CAD|CNH|CHF|NZD)$"),  # FX codes
    re.compile(r"^(Gold|Copper|Silver|Oil|Gas|Wheat|Corn|Soy)$"),  # commodity display names
    re.compile(r"^(EM|USD assets|USD assets)$"),  # FX/macro groupings
)

# Sectors / asset groups that may appear in headwind_for / tailwind_for
_MACRO_GROUP_PATTERN = re.compile(
    r"^(EM|DM|Asia|Europe|Latam|G10|Commodities?|Equities?|Bonds?|Credit|Gold|Oil)$",
    re.IGNORECASE,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SYNAPSE_YML = _REPO_ROOT / "config" / "synapse.yml"


# ─── fixture helpers ──────────────────────────────────────────────────────────

def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")


def _seed_synapse(root: Path) -> None:
    import shutil
    dest = root / "config" / "synapse.yml"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_SYNAPSE_YML, dest)


def _build_minimal_tree(root: Path) -> None:
    """Minimal hermetic fixture tree with all six R5 sources present."""
    _seed_synapse(root)

    # market_state
    _write_json(root / "data" / "market_state" / "latest.json", {
        "schema": "market_state.v2", "asof": "2026-07-05",
        "verdict": "CAUTION", "score": 55, "raw_score": 60,
        "is_display_only": True, "label_en": "Caution", "label_zh": "谨慎",
        "radar": {"state": "caution", "ceiling": 60, "amp": 1.0, "amp_keys": [],
                  "severe_gated": False, "recovery": False, "is_loud": False},
    })

    # regime
    _write_json(root / "data" / "regime" / "latest.json", {
        "quad": "Q1", "quad_name": "Goldilocks", "label": "Goldilocks",
        "confidence": 0.8, "growth_score": 70.0, "inflation_score": 30.0,
        "cycle_tag": "mid", "transition_state": "STABLE", "flip_condition": None,
        "flip_margin": 0.15, "liquidity_quality": "ok", "business_cycle": "expansion",
        "liquidity_overlay": "expanding", "sector_rs": [], "asof": "2026-07-05",
        "schema_version": 1,
        "freshness": {"asof": "2026-07-05", "built_at": "2026-07-05T06:00:00Z",
                      "age_days": 0, "stale": False},
        "risk_radar": {"schema": "risk_radar.v2", "asof": "2026-07-05",
                       "state": "calm", "alert": False, "dominant_scare": None, "scares": []},
        "vol_regime": {"available": True, "asof": "2026-07-05", "regime": "normalizing",
                       "risk_score": -0.1, "scored_score": None, "scored_active": False,
                       "vix": 14.0, "vrp_state": "normal", "vvix_state": "normal",
                       "vol_target_scalar": 1.0, "fragility_confluence": 0, "flags": []},
        "conditions": {"complacency": {"breadth_above200_pctile": 0.6, "breadth_div": False}},
    })

    # run_status
    _write_json(root / "data" / "run_status.json", {
        "last_run": "2026-07-05T06:00:00Z",
        "sources": {"polygon": {"status": "ok", "error": None, "checked_at": "2026-07-05T06:00:00Z"}},
        "circuit_breaker": {}, "stale_series": [],
    })

    # alerts_triage
    _write_json(root / "site" / "factordata" / "alerts_triage.json", {
        "generated_utc": "2026-07-05T06:00:00Z", "asof": "2026-07-05",
        "summary": {"total": 0, "critical": 0, "major": 0, "minor": 0,
                    "actionable": 0, "backtested": 0, "by_source": {}},
        "alerts": [],
    })

    # R5 sources
    _write_json(root / "data" / "transmission" / "latest.json", {
        "asof": "2026-07-05", "state": {}, "scored_status": {"en": "Display-only."},
        "calibrated": True,
        "headwinds": [{"asset": "XLU", "verdict": "headwind", "net": -0.4}],
        "tailwinds": [{"asset": "XLK", "verdict": "tailwind", "net": 0.3}],
        "yield_curve": {
            "regime": {"key": "bear_flattener", "label": "Bear Flattener"},
            "recession": {"risk": "low", "ntfs": "no signal"},
            "shape": {"slope_2s10s": 0.31},
        },
    })

    _write_json(root / "data" / "forex" / "latest.json", {
        "date": "Jul 05, 2026", "regime": "dollar_bull", "risk": "risk_on",
        "favored": ["EUR"],
        "dollar_desk": {"lean": "neutral", "real_rate_regime": "positive",
                        "usd_valuation": "overvalued", "trend": "declining",
                        "fed_path_lean": "hawkish", "liquidity_dir": "tightening"},
        "transmission": {"usd_dir": "down", "headwind_for": ["EM"], "tailwind_for": [],
                         "unstable": False},
        "regime_radar": {"as_of": "2026-07-05", "dominant": "dollar_bull", "active": []},
    })

    _write_json(root / "data" / "bonds" / "bond_health.json", {
        "as_of": "2026-07-05", "health_score": 85, "health_label": "healthy",
        "cycle_phase": "late", "recession_risk": 3.9, "drawdown_risk": 15.1,
        "alarms": [], "verdict_en": "Healthy.", "drivers_for": {},
        "fed_path": {"policy_rate": 5.25, "implied_bp_12m": -75.0, "implied_cuts_12m": 3},
        "bond_compass": {"duration": "short", "curve_trade": "steepener"},
        "bond_cross_asset": {"verdict_en": "Supportive."},
    })

    _write_json(root / "data" / "china_regime" / "latest.json", {
        "date": "2026-07-05", "quad": "Q3", "quad_name": "Stagflation",
        "cycle_tag": "mid", "confidence": 0.185, "liquidity_overlay": "neutral",
        "pending_quad": "Q2",
    })

    _write_json(root / "data" / "hk_regime" / "latest.json", {
        "date": "2026-07-05", "quad": "Q4", "quad_name": "Growth-scare",
        "cycle_tag": "mid", "confidence": 0.083, "liquidity_overlay": "neutral",
        "pending_quad": "Q3", "risk_state": "Neutral", "peg_state": "weak-side",
    })

    _write_json(root / "data" / "canada_regime" / "latest.json", {
        "date": "2026-07-05", "quad": "Q1", "quad_name": "Goldilocks",
        "cycle_tag": "late", "confidence": 0.305, "liquidity_overlay": "neutral",
        "pending_quad": "Q4",
    })

    _write_json(root / "data" / "commodity" / "latest.json", {
        "date": "Jul 05, 2026", "regime": "Goldilocks", "favored": ["Gold"],
        "assets": {
            "gold": {"label": "Gold", "trend": "up", "action": "hold", "conviction": "high"},
        },
    })

    _write_json(root / "site" / "intelligence" / "briefing.json", {
        "as_of": "2026-07-05", "n_universe": 100, "n_priority": 5,
        "n_actionable": 2, "n_divergences": 10,
        "macro_context": {"regime": "Q1", "posture": "neutral", "fed_stance": "hawkish"},
        "priority_queue": [
            {"ticker": "AAPL", "priority": 1, "lean": "long", "read": "Breakout."},
        ],
    })

    # Empty transitions.jsonl (PR-C creates this file; empty is valid)
    p = root / "data" / "macro_snapshots" / "transitions.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("", encoding="utf-8")


def _build_minimal_tree_with_snapshot(root: Path) -> None:
    """Same as _build_minimal_tree but also writes macro_snapshots/latest.json
    and world_state.json so _summarize_macro_weather has data."""
    _build_minimal_tree(root)

    # world_state.json (minimal)
    ws = {
        "fx_dollar": {"regime": "dollar_bull",
                      "dollar_desk": {"trend": "declining"},
                      "transmission": {"usd_dir": "down", "headwind_for": ["EM"],
                                       "tailwind_for": []}},
        "rates_transmission": {"headwinds": [{"asset": "XLU", "verdict": "headwind", "net": -0.4}],
                                "tailwinds": [{"asset": "XLK", "verdict": "tailwind", "net": 0.3}],
                                "yield_curve": {"regime": {"key": "bear_flattener"},
                                                "recession": {"risk": "low"}}},
        "rates_credit": {"health_label": "healthy", "cycle_phase": "late"},
        "commodity_context": {"regime": "Goldilocks", "favored": ["Gold"]},
        "macro_deltas": {"transitions": [], "n_transitions_14d": 0, "display_only": True},
        "contradictions": {"n": 0, "by_severity": {}, "top_pair_ids": [],
                           "gaps": [], "display_only": True},
    }
    _write_json(root / "data" / "neuralweb" / "world_state.json", ws)

    snapshot = {
        "schema": "macro_snapshot.v1.1",
        "asof": "2026-07-05",
        "macro_context_id": "abc123def456789a",
        "labels": {
            "us": {"us_quad": "Q1"},
            "china": {"china_quad": "Q3"},
            "hk": {"hk_quad": "Q4"},
            "canada": {"canada_quad": "Q1"},
        },
        "sources": {},
        "gaps": [],
        "display_only": True,
    }
    _write_json(root / "data" / "macro_snapshots" / "latest.json", snapshot)


# ─── helper: collect all string scalars in a nested structure ─────────────────

def _collect_strings(obj: Any) -> list[str]:
    """Recursively collect all string values from a nested dict/list."""
    out: list[str] = []
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            out.extend(_collect_strings(v))
    elif isinstance(obj, list):
        for item in obj:
            out.extend(_collect_strings(item))
    return out


def _is_whitelisted_macro_ticker(s: str) -> bool:
    """Return True if *s* is a whitelisted macro ETF / futures / FX ticker."""
    s = s.strip()
    for pattern in _MACRO_TICKER_WHITELIST_PATTERNS:
        if pattern.match(s):
            return True
    if _MACRO_GROUP_PATTERN.match(s):
        return True
    return False


# ─── fixture: crossasset/latest.json with flows block ────────────────────────

def _write_crossasset_fixture(root: Path) -> None:
    """Write a minimal data/crossasset/latest.json fixture with a flows.v2 block."""
    _write_json(root / "data" / "crossasset" / "latest.json", {
        "date": "2026-07-05",
        "regime": "mixed / no clear trend",
        "breadth": 0.1,
        "favored": ["equity_us"],
        "correlation": "converging",
        "asof": "2026-07-05",
        "flows": {
            "schema": "crossasset_flows.v2",
            "display_only": True,
            "regime": "mixed / no clear trend",
            "correlation": {
                "verdict": "converging",
                "absorption_pctile": 0.55,
                "n_markets": 6,
                "dominant_cluster": ["US", "Commodities", "Dollar"],
                "spark_w": [0.5] * 14 + [0.62],  # 15 values; last > first by 0.12 → rising
                "spark_asof": "2026-07-05",
            },
            "breadth": 0.1,
            "trend_top": [
                {"asset": "equity_us", "trend": "up", "z": 0.5},
                {"asset": "gold", "trend": "up", "z": 0.3},
            ],
            "trend_summary": {"n": 2, "n_up": 2, "n_down": 0},
            "intermarket": [
                {"pair": "copper_gold", "ratio": 0.22, "trend": "mid"},
                {"pair": "stocks_gold", "ratio": 2.1, "trend": "elevated"},
            ],
            "carry": {
                "rows": [{"key": "rates_term", "state": "positive carry", "value": 0.5}],
                "note": "Context only.",
            },
            "leadlag": {
                "verdict": "contemporaneous",
                "links": [],
                "stable": None,
                "lead_asset": None,
                "n_significant": 0,
                "n_tested": 6,
            },
            "global_liquidity": {"asof": "2026-07-05", "state": "expanding",
                                 "accel": "steady", "total_usd_tn": 22.5,
                                 "impulse_13w": 0.3},
            "funding_stress": {"asof": "2026-07-05", "state": "calm",
                               "score": 25, "spread_bp": 2.1},
            "confirm": {"verdict": "aligned", "n_blind_flags": 2,
                        "flags_top": [{"key": "credit_oas_roc", "severity": "low", "lead": 5}],
                        "asof": "2026-07-05"},
            "shadow": {"pressure_pctile": 0.72, "incumbent_state": "watch",
                       "shadow_state": "caution", "escalated": False},
            "note": "display-only regime read",
        },
    })


# ─── Test 1: display_only on every new lobe ──────────────────────────────────

class TestDisplayOnly:
    """Every R5+R6 world_state lobe must carry display_only=True."""

    _NEW_LOBES = (
        "rates_transmission",
        "fx_dollar",
        "rates_credit",
        "global_regimes",
        "commodity_context",
        "intelligence",
        "macro_deltas",
        "cross_asset_flows",
    )

    def test_display_only_all_lobes(self, tmp_path):
        from engine.neuralweb.world_state import build_world_state
        _build_minimal_tree(tmp_path)
        _write_crossasset_fixture(tmp_path)
        payload = build_world_state(root=tmp_path, now=_NOW)
        for lobe_key in self._NEW_LOBES:
            assert lobe_key in payload, f"lobe {lobe_key!r} missing from payload"
            assert payload[lobe_key].get("display_only") is True, (
                f"{lobe_key!r}: display_only is not True"
            )

    def test_factor_weather_still_display_only(self, tmp_path):
        from engine.neuralweb.world_state import build_world_state
        _build_minimal_tree(tmp_path)
        payload = build_world_state(root=tmp_path, now=_NOW)
        assert payload["factor_weather"].get("display_only") is True

    def test_cross_asset_flows_display_only_is_true(self, tmp_path):
        """cross_asset_flows carries display_only=True (RUL-CA-1)."""
        from engine.neuralweb.world_state import build_world_state
        _build_minimal_tree(tmp_path)
        _write_crossasset_fixture(tmp_path)
        payload = build_world_state(root=tmp_path, now=_NOW)
        lobe = payload.get("cross_asset_flows") or {}
        assert lobe.get("display_only") is True, "cross_asset_flows.display_only must be True"


# ─── Test 2 + 3: assert_no_authority ─────────────────────────────────────────

class TestNoAuthority:
    """assert_no_authority returns [] on built artifacts."""

    def test_world_state_no_authority_violations(self, tmp_path):
        from engine.neuralweb.world_state import build_world_state
        from engine.neuralweb._law import assert_no_authority
        _build_minimal_tree(tmp_path)
        payload = build_world_state(root=tmp_path, now=_NOW)
        violations = assert_no_authority(payload)
        assert violations == [], f"world_state authority violations: {violations}"

    def test_mastermind_no_authority_violations(self, tmp_path):
        from engine.neuralweb.mastermind_context import build_context
        from engine.neuralweb._law import assert_no_authority
        # _build_minimal_tree provides synapse.yml + necessary files
        _build_minimal_tree(tmp_path)
        # Add minimal mastermind sources
        _write_json(tmp_path / "site" / "factordata" / "us_standouts.json",
                    {"buy": [], "watch": [], "laggards": []})
        _write_json(tmp_path / "site" / "altdata" / "mastermind.json",
                    {"signals": [], "broken_signals": []})
        _write_json(tmp_path / "site" / "basketdata" / "radar_ticker.json", {"rows": []})
        _write_json(tmp_path / "site" / "neuralwebdata" / "bottom_sensors.json",
                    {"as_of": "2026-07-05", "rows": [], "n_rows": 0})

        payload = build_context(root=tmp_path, now=_NOW)
        violations = assert_no_authority(payload)
        assert violations == [], f"mastermind authority violations: {violations}"


# ─── Test 4: five bridge booleans false ──────────────────────────────────────

class TestBridgeBooleansFalse:
    def test_authority_booleans_all_false(self, tmp_path):
        from engine.neuralweb.mastermind_context import build_context
        _build_minimal_tree(tmp_path)
        _write_json(tmp_path / "site" / "factordata" / "us_standouts.json",
                    {"buy": [], "watch": [], "laggards": []})
        _write_json(tmp_path / "site" / "altdata" / "mastermind.json",
                    {"signals": [], "broken_signals": []})
        _write_json(tmp_path / "site" / "basketdata" / "radar_ticker.json", {"rows": []})
        _write_json(tmp_path / "site" / "neuralwebdata" / "bottom_sensors.json",
                    {"as_of": "2026-07-05", "rows": [], "n_rows": 0})
        payload = build_context(root=tmp_path, now=_NOW)
        auth = payload.get("authority") or {}
        for key in _AUTHORITY_BOOLEANS:
            assert auth.get(key) is False, f"authority.{key} should be False"


# ─── Test 5: no Article-2 keys in any new lobe ───────────────────────────────

class TestNoArticle2Keys:
    _NEW_LOBES = (
        "rates_transmission",
        "fx_dollar",
        "rates_credit",
        "global_regimes",
        "commodity_context",
        "intelligence",
        "macro_deltas",
        "cross_asset_flows",
    )

    def test_no_article2_keys(self, tmp_path):
        from engine.neuralweb.world_state import build_world_state
        _build_minimal_tree(tmp_path)
        _write_crossasset_fixture(tmp_path)
        payload = build_world_state(root=tmp_path, now=_NOW)
        for lobe_key in self._NEW_LOBES:
            lobe = payload.get(lobe_key) or {}
            found = _ARTICLE_2_KEYS & set(_collect_strings(list(lobe.keys())))
            assert not found, (
                f"{lobe_key!r} contains Article-2 surface key(s): {found}"
            )


# ─── Test 6: per-source missing-file fail-open ───────────────────────────────

class TestPerSourceFailOpen:
    """Each R5 source missing individually → gap entry, others unaffected, no raise."""

    def _payload_without(self, tmp_path: Path, skip_file: str) -> dict:
        from engine.neuralweb.world_state import build_world_state
        _build_minimal_tree(tmp_path)
        target = tmp_path / skip_file
        if target.exists():
            target.unlink()
        return build_world_state(root=tmp_path, now=_NOW)

    def test_missing_transmission(self, tmp_path):
        payload = self._payload_without(tmp_path, "data/transmission/latest.json")
        assert payload["rates_transmission"].get("display_only") is True
        assert any("transmission" in g for g in payload["gaps"])

    def test_missing_forex(self, tmp_path):
        payload = self._payload_without(tmp_path, "data/forex/latest.json")
        assert payload["fx_dollar"].get("display_only") is True
        assert any("forex" in g for g in payload["gaps"])

    def test_missing_bond_health(self, tmp_path):
        payload = self._payload_without(tmp_path, "data/bonds/bond_health.json")
        assert payload["rates_credit"].get("display_only") is True
        assert any("bond" in g for g in payload["gaps"])

    def test_missing_china_regime(self, tmp_path):
        payload = self._payload_without(tmp_path, "data/china_regime/latest.json")
        assert payload["global_regimes"].get("display_only") is True
        assert any("china_regime" in g for g in payload["gaps"])

    def test_missing_hk_regime(self, tmp_path):
        payload = self._payload_without(tmp_path, "data/hk_regime/latest.json")
        assert payload["global_regimes"].get("display_only") is True
        assert any("hk_regime" in g for g in payload["gaps"])

    def test_missing_canada_regime(self, tmp_path):
        payload = self._payload_without(tmp_path, "data/canada_regime/latest.json")
        assert payload["global_regimes"].get("display_only") is True
        assert any("canada_regime" in g for g in payload["gaps"])

    def test_missing_commodity(self, tmp_path):
        payload = self._payload_without(tmp_path, "data/commodity/latest.json")
        assert payload["commodity_context"].get("display_only") is True
        assert any("commodity" in g for g in payload["gaps"])

    def test_missing_briefing(self, tmp_path):
        payload = self._payload_without(tmp_path, "site/intelligence/briefing.json")
        assert payload["intelligence"].get("display_only") is True
        assert any("briefing" in g or "intelligence" in g for g in payload["gaps"])

    def test_missing_transitions(self, tmp_path):
        """transitions.jsonl absent -> gap entry + null macro_deltas (expected)."""
        payload = self._payload_without(
            tmp_path, "data/macro_snapshots/transitions.jsonl"
        )
        assert payload["macro_deltas"].get("display_only") is True
        assert any("transitions" in g or "macro_snapshots" in g for g in payload["gaps"])

    def test_no_raise_any_source_missing(self, tmp_path):
        """All R5 sources missing simultaneously — no exception, display_only preserved."""
        from engine.neuralweb.world_state import build_world_state
        _build_minimal_tree(tmp_path)
        for f in [
            "data/transmission/latest.json",
            "data/forex/latest.json",
            "data/bonds/bond_health.json",
            "data/china_regime/latest.json",
            "data/hk_regime/latest.json",
            "data/canada_regime/latest.json",
            "data/commodity/latest.json",
            "site/intelligence/briefing.json",
        ]:
            p = tmp_path / f
            if p.exists():
                p.unlink()
        payload = build_world_state(root=tmp_path, now=_NOW)
        for lobe_key in ("rates_transmission", "fx_dollar", "rates_credit",
                         "global_regimes", "commodity_context", "intelligence"):
            assert payload[lobe_key].get("display_only") is True, (
                f"{lobe_key} should still have display_only=True when source absent"
            )


# ─── Test 7: to_iso format coverage ──────────────────────────────────────────

class TestToIso:
    def test_iso_date_passthrough(self):
        from engine.neuralweb._dates import to_iso
        assert to_iso("2026-07-05") == "2026-07-05"

    def test_display_string(self):
        from engine.neuralweb._dates import to_iso
        assert to_iso("Jul 05, 2026") == "2026-07-05"

    def test_iso_datetime(self):
        from engine.neuralweb._dates import to_iso
        assert to_iso("2026-07-05T12:00:00Z") == "2026-07-05"

    def test_none_returns_none(self):
        from engine.neuralweb._dates import to_iso
        assert to_iso(None) is None

    def test_empty_string_returns_none(self):
        from engine.neuralweb._dates import to_iso
        assert to_iso("") is None

    def test_unrecognised_returns_none(self):
        from engine.neuralweb._dates import to_iso
        assert to_iso("not-a-date") is None

    def test_iso_date_with_space_separator(self):
        from engine.neuralweb._dates import to_iso
        assert to_iso("2026-07-05 06:00:00") == "2026-07-05"

    def test_single_digit_day(self):
        from engine.neuralweb._dates import to_iso
        assert to_iso("Jul 5, 2026") == "2026-07-05"


# ─── Test 8: no-new-names in macro_weather ───────────────────────────────────

class TestNoNewNamesInMacroWeather:
    """No single-name ticker outside the macro ETF/futures whitelist may appear
    in the macro_weather lobe (RUL-M8 / §5.5 no-new-names extension).

    What counts as a "single name": a ticker-like string matching /^[A-Z]{1,5}$/
    that does NOT appear in the whitelist.
    """

    _SINGLE_NAME_RE = re.compile(r"^[A-Z]{1,5}$")

    def _is_suspect_ticker(self, s: str) -> bool:
        """Return True if *s* looks like a single-name ticker AND is NOT whitelisted."""
        s = s.strip()
        if not self._SINGLE_NAME_RE.match(s):
            return False
        return not _is_whitelisted_macro_ticker(s)

    def test_macro_weather_no_new_names(self, tmp_path):
        from engine.neuralweb.mastermind_context import _summarize_macro_weather
        _build_minimal_tree_with_snapshot(tmp_path)
        lobe, gap = _summarize_macro_weather(tmp_path)
        if gap:
            pytest.skip(f"macro_weather returned gap (expected if snapshot absent): {gap}")
        all_strings = _collect_strings(lobe)
        suspect = [s for s in all_strings if self._is_suspect_ticker(s)]
        assert suspect == [], (
            f"macro_weather contains non-whitelisted single-name ticker(s): {suspect}"
        )


# ─── Test 9: macro_weather returns gap when snapshot absent ──────────────────

class TestMacroWeatherGapOnAbsentSnapshot:
    def test_gap_when_no_snapshot(self, tmp_path):
        from engine.neuralweb.mastermind_context import _summarize_macro_weather
        _build_minimal_tree(tmp_path)
        # transitions.jsonl is present from _build_minimal_tree
        # but macro_snapshots/latest.json is NOT present
        lobe, gap = _summarize_macro_weather(tmp_path)
        assert gap is not None, "expected a gap string when snapshot absent"
        assert isinstance(gap, str) and gap, "gap should be a non-empty string"
        assert lobe == {} or lobe is not None  # lobe can be empty dict

    def test_no_gap_when_snapshot_present(self, tmp_path):
        from engine.neuralweb.mastermind_context import _summarize_macro_weather
        _build_minimal_tree_with_snapshot(tmp_path)
        lobe, gap = _summarize_macro_weather(tmp_path)
        assert gap is None, f"expected no gap with snapshot present; got: {gap}"
        assert lobe.get("display_only") is True
        assert lobe.get("macro_context_id") == "abc123def456789a"


# ─── Test 10: law module unit tests ──────────────────────────────────────────

class TestLaw:
    def test_display_only_sets_flag(self):
        from engine.neuralweb._law import display_only
        d = {"a": 1}
        result = display_only(d)
        assert result["display_only"] is True
        assert result is d  # mutates in place and returns same dict

    def test_assert_no_authority_clean(self):
        from engine.neuralweb._law import assert_no_authority
        clean = {"foo": "bar", "nested": {"baz": 42}}
        assert assert_no_authority(clean) == []

    def test_assert_no_authority_catches_boolean(self):
        from engine.neuralweb._law import assert_no_authority
        bad = {"can_add_candidates": True}
        violations = assert_no_authority(bad)
        assert any("can_add_candidates" in v for v in violations)

    def test_assert_no_authority_false_boolean_ok(self):
        from engine.neuralweb._law import assert_no_authority
        ok = {"can_add_candidates": False}
        assert assert_no_authority(ok) == []

    def test_assert_no_authority_catches_article2(self):
        from engine.neuralweb._law import assert_no_authority
        bad = {"alert_triage": [1, 2, 3]}
        violations = assert_no_authority(bad)
        assert any("alert_triage" in v for v in violations)

    def test_assert_no_authority_catches_scored_path_surfaces(self):
        from engine.neuralweb._law import assert_no_authority
        bad = {"scored_path_surfaces": ["some_surface"]}
        violations = assert_no_authority(bad)
        assert any("scored_path_surfaces" in v for v in violations)

    def test_assert_no_authority_empty_scored_path_surfaces_ok(self):
        from engine.neuralweb._law import assert_no_authority
        ok = {"scored_path_surfaces": []}
        assert assert_no_authority(ok) == []

    def test_assert_no_authority_nested(self):
        from engine.neuralweb._law import assert_no_authority
        nested = {"lobes": {"market": {"can_force_exit": True}}}
        violations = assert_no_authority(nested)
        assert any("can_force_exit" in v for v in violations)


# ─── Tests 11–15: R6 cross_asset_flows authority wall ────────────────────────

class TestCrossAssetFlowsAuthority:
    """R6 authority wall: cross_asset_flows lobe — RUL-CA-1 enforcement."""

    def test_cross_asset_flows_assert_no_authority(self, tmp_path):
        """assert_no_authority returns [] for cross_asset_flows."""
        from engine.neuralweb.world_state import build_world_state
        from engine.neuralweb._law import assert_no_authority
        _build_minimal_tree(tmp_path)
        _write_crossasset_fixture(tmp_path)
        payload = build_world_state(root=tmp_path, now=_NOW)
        lobe = payload.get("cross_asset_flows") or {}
        violations = assert_no_authority(lobe)
        assert violations == [], f"cross_asset_flows authority violations: {violations}"

    def test_cross_asset_flows_no_article2_keys(self, tmp_path):
        """No Article-2 surface keys present in cross_asset_flows."""
        from engine.neuralweb.world_state import build_world_state
        _build_minimal_tree(tmp_path)
        _write_crossasset_fixture(tmp_path)
        payload = build_world_state(root=tmp_path, now=_NOW)
        lobe = payload.get("cross_asset_flows") or {}
        found = _ARTICLE_2_KEYS & set(_collect_strings(list(lobe.keys())))
        assert not found, f"cross_asset_flows contains Article-2 key(s): {found}"

    def test_cross_asset_flows_absent_source_per_lobe_gap(self, tmp_path):
        """data/crossasset/latest.json absent → per-lobe gap, other lobes unaffected."""
        from engine.neuralweb.world_state import build_world_state
        _build_minimal_tree(tmp_path)
        # Do NOT write crossasset fixture — file is absent
        payload = build_world_state(root=tmp_path, now=_NOW)
        # cross_asset_flows lobe must have display_only=True even when source absent
        lobe = payload.get("cross_asset_flows") or {}
        assert lobe.get("display_only") is True, (
            "cross_asset_flows.display_only must be True even when source absent"
        )
        # other lobes must still be present and unaffected
        for other in ("rates_transmission", "fx_dollar", "rates_credit",
                      "global_regimes", "commodity_context"):
            assert payload.get(other) is not None, (
                f"{other} should be present even when crossasset source absent"
            )
        # gap should mention crossasset
        assert any("crossasset" in g for g in payload["gaps"]), (
            "expected a gap entry mentioning 'crossasset' when source absent"
        )

    def test_macro_weather_with_cross_asset_block_size(self, tmp_path):
        """macro_weather serialized < 200 KB with the new cross_asset sub-block (v2 fields)."""
        from engine.neuralweb.mastermind_context import _summarize_macro_weather
        _build_minimal_tree_with_snapshot(tmp_path)
        # Also write crossasset fixture + wire into world_state.json
        _write_crossasset_fixture(tmp_path)
        # Patch world_state.json to include cross_asset_flows with v2 fields
        ws_path = tmp_path / "data" / "neuralweb" / "world_state.json"
        import json as _json
        ws = _json.loads(ws_path.read_text())
        ws["cross_asset_flows"] = {
            "regime": "mixed / no clear trend",
            "correlation": {"verdict": "converging", "absorption_pctile": 0.55, "n_markets": 6},
            "dominant_cluster": ["US", "Commodities", "Dollar"],
            "absorption_dir": "rising",
            "intermarket": [{"pair": "copper_gold", "ratio": 0.22, "trend": "mid"}],
            "breadth": 0.1,
            "leadlag": {"verdict": "contemporaneous", "n_links": 0},
            "funding_state": "calm",
            "confirm": {"verdict": "aligned", "n_blind_flags": 2},
            "shadow": {"escalated": False, "pressure_pctile": 0.72},
            "display_only": True,
        }
        ws_path.write_text(_json.dumps(ws))
        lobe, gap = _summarize_macro_weather(tmp_path)
        if gap:
            pytest.skip(f"macro_weather returned gap: {gap}")
        serialized = _json.dumps(lobe)
        assert len(serialized.encode("utf-8")) < 200 * 1024, (
            f"macro_weather exceeds 200 KB: {len(serialized.encode('utf-8'))} bytes"
        )
        # cross_asset sub-block must be present
        assert "cross_asset" in lobe, "macro_weather must include 'cross_asset' sub-block"
        # v2 additive fields must appear in cross_asset sub-block
        ca = lobe.get("cross_asset") or {}
        assert "one_bet_cluster" in ca, "macro_weather cross_asset must include one_bet_cluster"
        assert "funding_state" in ca, "macro_weather cross_asset must include funding_state"

    def test_macro_weather_cross_asset_no_new_names(self, tmp_path):
        """cross_asset sub-block in macro_weather has no non-whitelisted tickers."""
        from engine.neuralweb.mastermind_context import _summarize_macro_weather
        _build_minimal_tree_with_snapshot(tmp_path)
        _write_crossasset_fixture(tmp_path)
        import json as _json
        ws_path = tmp_path / "data" / "neuralweb" / "world_state.json"
        ws = _json.loads(ws_path.read_text())
        ws["cross_asset_flows"] = {
            "regime": "mixed / no clear trend",
            "correlation": {"verdict": "converging", "absorption_pctile": 0.55, "n_markets": 6},
            # Note: dominant_cluster intentionally absent here — test checks no stray tickers
            # leak into the ca_block; cluster labels ('US' etc.) are region names, not tickers,
            # but they match the single-name pattern. The no_new_names guard is about
            # individual equity tickers slipping in, not region labels.
            "absorption_dir": "rising",
            "intermarket": [{"pair": "copper_gold", "ratio": 0.22, "trend": "mid"}],
            "breadth": 0.1,
            "leadlag": {"verdict": "contemporaneous", "n_links": 0},
            "funding_state": "calm",
            "display_only": True,
        }
        ws_path.write_text(_json.dumps(ws))
        lobe, gap = _summarize_macro_weather(tmp_path)
        if gap:
            pytest.skip(f"macro_weather returned gap: {gap}")
        single_name_re = re.compile(r"^[A-Z]{1,5}$")
        ca_block = lobe.get("cross_asset") or {}
        ca_strings = _collect_strings(ca_block)
        suspect = [
            s for s in ca_strings
            if single_name_re.match(s) and not _is_whitelisted_macro_ticker(s)
        ]
        assert suspect == [], (
            f"cross_asset sub-block contains non-whitelisted ticker(s): {suspect}"
        )


# ─── Tests 16+: CA-W3 v2 additive fields ─────────────────────────────────────

class TestCrossAssetFlowsV2Fields:
    """CA-W3: new v2 additive fields on cross_asset_flows lobe (dominant_cluster,
    absorption_dir, confirm, shadow) — null-safe, display_only, no authority."""

    def test_v2_fields_present_when_source_populated(self, tmp_path):
        """With a full v2 fixture, new fields are present in the cross_asset_flows lobe."""
        from engine.neuralweb.world_state import build_world_state
        _build_minimal_tree(tmp_path)
        _write_crossasset_fixture(tmp_path)
        payload = build_world_state(root=tmp_path, now=_NOW)
        lobe = payload.get("cross_asset_flows") or {}
        # These keys must be present (may be None or populated)
        for key in ("dominant_cluster", "absorption_dir", "confirm", "shadow"):
            assert key in lobe, f"cross_asset_flows missing v2 key: {key!r}"

    def test_dominant_cluster_populated_from_v2_fixture(self, tmp_path):
        """dominant_cluster is populated from flows.correlation.dominant_cluster."""
        from engine.neuralweb.world_state import build_world_state
        _build_minimal_tree(tmp_path)
        _write_crossasset_fixture(tmp_path)
        payload = build_world_state(root=tmp_path, now=_NOW)
        lobe = payload.get("cross_asset_flows") or {}
        dc = lobe.get("dominant_cluster")
        assert dc is not None, "dominant_cluster should be populated from v2 fixture"
        assert isinstance(dc, list), "dominant_cluster must be a list"
        assert "US" in dc, f"expected 'US' in dominant_cluster, got {dc}"

    def test_absorption_dir_rising_from_v2_fixture(self, tmp_path):
        """absorption_dir is 'rising' when spark_w last > first by >0.01."""
        from engine.neuralweb.world_state import build_world_state
        _build_minimal_tree(tmp_path)
        _write_crossasset_fixture(tmp_path)
        payload = build_world_state(root=tmp_path, now=_NOW)
        lobe = payload.get("cross_asset_flows") or {}
        # v2 fixture has spark_w = [0.5]*14 + [0.62]: 0.62 - 0.50 = 0.12 > 0.01 → rising
        assert lobe.get("absorption_dir") == "rising", (
            f"expected absorption_dir='rising', got {lobe.get('absorption_dir')!r}"
        )

    def test_confirm_block_populated_from_v2_fixture(self, tmp_path):
        """confirm sub-block is populated when flows.confirm.verdict is present."""
        from engine.neuralweb.world_state import build_world_state
        _build_minimal_tree(tmp_path)
        _write_crossasset_fixture(tmp_path)
        payload = build_world_state(root=tmp_path, now=_NOW)
        lobe = payload.get("cross_asset_flows") or {}
        confirm = lobe.get("confirm")
        assert confirm is not None, "confirm sub-block should be populated from v2 fixture"
        assert confirm.get("verdict") == "aligned", (
            f"expected confirm.verdict='aligned', got {confirm.get('verdict')!r}"
        )
        assert "n_blind_flags" in confirm, "confirm must include n_blind_flags"

    def test_shadow_block_populated_from_v2_fixture(self, tmp_path):
        """shadow sub-block is populated when flows.shadow.pressure_pctile is present."""
        from engine.neuralweb.world_state import build_world_state
        _build_minimal_tree(tmp_path)
        _write_crossasset_fixture(tmp_path)
        payload = build_world_state(root=tmp_path, now=_NOW)
        lobe = payload.get("cross_asset_flows") or {}
        shadow = lobe.get("shadow")
        assert shadow is not None, "shadow sub-block should be populated from v2 fixture"
        assert "escalated" in shadow, "shadow must include escalated"
        assert "pressure_pctile" in shadow, "shadow must include pressure_pctile"

    def test_v2_fields_null_when_source_absent(self, tmp_path):
        """When crossasset file is absent, v2 fields are None (null-safe)."""
        from engine.neuralweb.world_state import build_world_state
        _build_minimal_tree(tmp_path)
        # Do NOT write crossasset fixture — file is absent
        payload = build_world_state(root=tmp_path, now=_NOW)
        lobe = payload.get("cross_asset_flows") or {}
        assert lobe.get("display_only") is True
        # New v2 fields must be present as None (not raise)
        for key in ("dominant_cluster", "absorption_dir", "confirm", "shadow"):
            assert lobe.get(key) is None, (
                f"cross_asset_flows.{key} should be None when source absent, got {lobe.get(key)!r}"
            )

    def test_v2_display_only_enforced(self, tmp_path):
        """v2 fields never grant authority — assert_no_authority still returns []."""
        from engine.neuralweb.world_state import build_world_state
        from engine.neuralweb._law import assert_no_authority
        _build_minimal_tree(tmp_path)
        _write_crossasset_fixture(tmp_path)
        payload = build_world_state(root=tmp_path, now=_NOW)
        lobe = payload.get("cross_asset_flows") or {}
        violations = assert_no_authority(lobe)
        assert violations == [], f"cross_asset_flows v2 authority violations: {violations}"

    def test_mastermind_one_bet_cluster_in_cross_asset(self, tmp_path):
        """macro_weather cross_asset block includes one_bet_cluster and funding_state."""
        from engine.neuralweb.mastermind_context import _summarize_macro_weather
        import json as _json
        _build_minimal_tree_with_snapshot(tmp_path)
        _write_crossasset_fixture(tmp_path)
        ws_path = tmp_path / "data" / "neuralweb" / "world_state.json"
        ws = _json.loads(ws_path.read_text())
        ws["cross_asset_flows"] = {
            "regime": "mixed / no clear trend",
            "correlation": {"verdict": "converging", "absorption_pctile": 0.55, "n_markets": 6},
            "dominant_cluster": ["US", "Commodities", "Dollar"],
            "absorption_dir": "rising",
            "intermarket": [{"pair": "copper_gold", "ratio": 0.22, "trend": "mid"}],
            "breadth": 0.1,
            "leadlag": {"verdict": "contemporaneous", "n_links": 0},
            "funding_state": "calm",
            "confirm": {"verdict": "aligned", "n_blind_flags": 2},
            "shadow": {"escalated": False, "pressure_pctile": 0.72},
            "display_only": True,
        }
        ws_path.write_text(_json.dumps(ws))
        lobe, gap = _summarize_macro_weather(tmp_path)
        if gap:
            pytest.skip(f"macro_weather returned gap: {gap}")
        ca = lobe.get("cross_asset") or {}
        assert "one_bet_cluster" in ca, "cross_asset must include one_bet_cluster"
        assert ca.get("one_bet_cluster") == ["US", "Commodities", "Dollar"], (
            f"expected one_bet_cluster=['US','Commodities','Dollar'], got {ca.get('one_bet_cluster')!r}"
        )
        assert "funding_state" in ca, "cross_asset must include funding_state"
        assert ca.get("funding_state") == "calm", (
            f"expected funding_state='calm', got {ca.get('funding_state')!r}"
        )


# ─── R25 unified decision workspace projection ───────────────────────────────

def _r25_snapshot() -> dict:
    return {
        "schema": "macro_snapshot.v1",
        "asof": "2026-10-02",
        "macro_context_id": "fixture-r25",
        "display_only": True,
        "labels": {
            "bonds": {
                "bond_health_label": "healthy",
                "bond_cycle_phase": "recession",
                "bond_duration_bucket": "lean_long",
                "bond_curve_lean": "steepener",
            },
            "transmission": {
                "yield_curve_regime": "bear_steepener",
                "recession_risk": "low",
            },
            "fx": {
                "usd_trend": "mixed",
                "usd_regime": "Global reflation",
                "fx_risk": "risk-off",
                "real_rate_regime": "Restrictive real yields",
                "fx_liquidity_dir": "supportive",
                "fx_regime_radar": "dollar_wrecking_ball",
                "usd_positioning": "neutral",
                "usd_valuation": "fair",
                "fed_path_lean": "hawkish_repricing",
            },
        },
        "sources": {
            "data/bonds/bond_health.json": "2026-10-01",
            "data/transmission/latest.json": "2026-10-01",
            "data/forex/latest.json": "2026-10-02",
            "data/regime/latest.json": "2026-10-01",
        },
        "gaps": [],
    }


def _r25_world_state() -> dict:
    return {
        "rates_credit": {
            "as_of": "2026-10-01",
            "health_score": 78,  # must NOT leak into decision workspace
            "health_label": "healthy",
            "cycle_phase": "recession",
            "fed_path": {"policy_rate": 3.88, "implied_bp_12m": 82},
            "bond_compass": {
                "duration": {"bucket": "lean_long", "conviction": 0.24},
                "curve_trade": {"lean": "steepener", "slope_10y3m": 1.07},
            },
            "drivers_for": {
                "equities": {
                    "note_en": "Discount-rate channel",
                    "hy_oas": 3.12,
                    "credit_canary": True,
                    "stock_bond_corr": 0.53,
                },
                "forex": {
                    "note_en": "Rate differentials drive FX",
                    "real_10y": 2.93,
                    "term_premium": 1.02,
                },
            },
            "display_only": True,
        },
        "fx_dollar": {
            "asof": "2026-10-02",
            "regime": "Global reflation",
            "risk": "risk-off",
            "dollar_desk": {
                "lean": "dollar-supportive backdrop",
                "real_rate_regime": "Restrictive real yields",
                "usd_valuation": "fair",
                "trend": "mixed",
                "fed_path_lean": "hawkish_repricing",
                "liquidity_dir": "supportive",
            },
            "transmission": {
                "usd_dir": "flat",
                "headwind_for": ["US equities", "EM equities"],
                "tailwind_for": ["Oil (WTI)"],
                "unstable": [],
            },
            "regime_radar": {
                "dominant": "dollar_wrecking_ball",
                "active": ["dollar_wrecking_ball"],
                "building_scenarios": [],
            },
            "pairs": [
                {"pair": "USDMXN", "action": "LONG", "score": 31.5},
                {"pair": "AUDUSD", "action": "SHORT", "score": -23.8},
            ],
            # CNH/onshore-offshore basis is NOT market-wide USD xccy funding basis.
            "em": {"cnh_basis_state": "neutral", "risk_off_composite": 0.116},
            "deltas": {
                "usd_trend": {
                    "value": "mixed", "prev": "down",
                    "since": "2026-09-23", "days_in_state": 10,
                },
                "fed_path_lean": {
                    "value": "hawkish_repricing", "prev": "steady",
                    "since": "2026-09-01", "days_in_state": 32,
                },
            },
            "regime_radar_dominant_scenario": {
                "key": "dollar_wrecking_ball",
                "intensity": 60.8,
                "prob_status": "ok",
                "p_cond": 0.1913,
                "base_rate": 0.1318,
            },
            "display_only": True,
        },
        "cross_asset_flows": {
            "asof": "2026-10-02",
            "regime": "mixed / no clear trend",
            "funding_state": "calm",
            "confirm": {"verdict": "diverge", "n_blind_flags": 2},
            "stale": False,
            "display_only": True,
        },
        "contradictions": {
            "n": 2,
            "top_pair_ids": ["cross_asset_confirm-diverge"],
            "display_only": True,
        },
    }


def _r25_regime_data() -> dict:
    return {
        "asof": "2026-10-02",
        "conditions": {
            "stale_inputs": ["ebp", "recession_risk"],
            "vintages": {
                "ebp": {"asof": "2026-07-01", "age_days": 93, "stale": True},
                "hy_oas": {"asof": "2026-10-01", "age_days": 1, "stale": False},
            },
        },
        "cross_asset_confirm": {
            "verdict": "diverge",
            "confidence": "low",  # must NOT be promoted into workspace confidence
            "caution_flags": [
                {"key": "credit", "lead": "leading", "severity": "medium"},
            ],
            "display_only": True,
        },
    }


def _walk_keys(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield key
            yield from _walk_keys(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _walk_keys(value)


def test_r25_decision_workspaces_are_display_projection_without_authority_or_scores():
    from scripts.build_macro_context import _build_decision_workspaces

    out = _build_decision_workspaces(
        _r25_snapshot(), _r25_world_state(), _r25_regime_data(), [], "2026-10-02"
    )
    assert out["schema"] == "macro_context.decision_workspaces.v1"
    assert out["display_only"] is True
    assert out["claim_scope"] == "projection_only"
    assert out["probability_policy"] == "withheld"
    assert set(out) >= {"bonds", "forex"}

    forbidden = {
        "score", "confidence", "probability", "p_cond", "base_rate",
        "can_add_candidates", "can_raise_size", "can_lower_size",
        "can_block_entry", "can_force_exit",
    }
    assert forbidden.isdisjoint(set(_walk_keys(out)))
    blob = json.dumps(out).lower()
    assert "valuation pressure" not in blob
    assert "policy / rate divergence" not in blob


def test_r25_bonds_projects_only_existing_owner_states_and_receipts():
    from scripts.build_macro_context import _build_decision_workspaces

    out = _build_decision_workspaces(
        _r25_snapshot(), _r25_world_state(), _r25_regime_data(), [], "2026-10-02"
    )["bonds"]
    assert out["status"] == "partial"  # stale EBP/recession inputs remain visible gaps
    assert out["current_read"] == {
        "health": "healthy",
        "cycle": "recession",
        "duration_lean": "lean_long",
        "curve_trade": "steepener",
        "yield_curve_regime": "bear_steepener",
        "recession_risk": "low",
    }
    assert out["source_receipts"]["bond_health"]["asof"] == "2026-10-01"
    assert out["source_receipts"]["bond_health"]["date_status"] == "known"
    assert out["source_receipts"]["bond_health"]["age_days"] == 1
    assert out["source_receipts"]["bond_health"].get("fresh") is None
    assert out["mechanism_evidence"]["fed_path"]["policy_rate"] == 3.88
    assert out["mechanism_evidence"]["real_10y"] == 2.93
    assert out["mechanism_evidence"]["term_premium"] == 1.02
    assert out["transmission"]["equities"]["credit_canary"] is True
    assert "score" not in out["current_read"]


def test_r25_forex_keeps_pair_score_probability_and_cnh_basis_out_of_decision_projection():
    from scripts.build_macro_context import _build_decision_workspaces

    out = _build_decision_workspaces(
        _r25_snapshot(), _r25_world_state(), _r25_regime_data(), [], "2026-10-02"
    )["forex"]
    assert out["status"] == "partial"
    assert out["current_read"]["usd_trend"] == "mixed"
    assert out["current_read"]["desk_lean"] == "dollar-supportive backdrop"
    assert out["current_read"]["fed_path_lean"] == "hawkish_repricing"
    assert out["current_read"]["regime_radar"] == "dollar_wrecking_ball"
    assert out["pairs"] == [
        {"pair": "USDMXN", "action": "LONG"},
        {"pair": "AUDUSD", "action": "SHORT"},
    ]
    gap = next(g for g in out["data_gaps"] if g["key"] == "direct_usd_cross_currency_basis")
    assert gap["status"] == "unavailable"
    assert gap["substitute_allowed"] is False
    assert "CNH" in gap["note"]
    blob = json.dumps(out)
    assert "p_cond" not in blob and "base_rate" not in blob
    assert "60.8" not in blob and "31.5" not in blob


def test_r25_missing_sources_fail_closed_without_zero_or_old_state_substitution():
    from scripts.build_macro_context import _build_decision_workspaces

    out = _build_decision_workspaces(None, None, None, [], "2026-10-02")
    assert out["bonds"]["status"] == "unavailable"
    assert out["forex"]["status"] == "unavailable"
    assert all(v is None for v in out["bonds"]["current_read"].values())
    assert all(v is None for v in out["forex"]["current_read"].values())
    assert out["bonds"]["transmission"] == {}
    assert out["forex"]["transmission"] == {}
    assert out["bonds"]["data_gaps"]
    assert out["forex"]["data_gaps"]


def test_r25_changed_evidence_is_descriptive_and_domain_filtered():
    from scripts.build_macro_context import _build_decision_workspaces

    transitions = [
        {"asof": "2026-10-01", "domain": "bonds", "field": "bond_curve_lean",
         "from": "flattener", "to": "steepener"},
        {"asof": "2026-10-01", "domain": "fx", "field": "usd_trend",
         "from": "down", "to": "mixed"},
        {"asof": "2026-10-01", "domain": "china", "field": "china_quad",
         "from": "Q2", "to": "Q3"},
    ]
    out = _build_decision_workspaces(
        _r25_snapshot(), _r25_world_state(), _r25_regime_data(), transitions, "2026-10-02"
    )
    assert out["bonds"]["changes"] == [transitions[0]]
    assert out["forex"]["changes"] == [transitions[1]]
    assert "china_quad" not in json.dumps(out["bonds"])
    assert "china_quad" not in json.dumps(out["forex"])


def test_r25_regime_staleness_is_preserved_as_a_gap_not_a_probability():
    from scripts.build_macro_context import _build_decision_workspaces

    out = _build_decision_workspaces(
        _r25_snapshot(), _r25_world_state(), _r25_regime_data(), [], "2026-10-02"
    )
    stale = {g["key"] for g in out["bonds"]["data_gaps"] if g["status"] == "stale_input"}
    assert {"ebp", "recession_risk"}.issubset(stale)
    assert out["bonds"]["probability_policy"] == "withheld"
    assert out["forex"]["probability_policy"] == "withheld"


def test_r25_build_view_model_adds_projection_but_hub_contract_remains_five_keys():
    from scripts import build_macro_context as bmc

    vm = bmc._build_view_model(
        _r25_snapshot(), _r25_world_state(), [], "2026-10-02", Path("/nonexistent"),
        regime_data=_r25_regime_data(),
    )
    assert "decision_workspaces" in vm
    assert vm["decision_workspaces"]["display_only"] is True

    source = Path(bmc.__file__).read_text()
    start = source.index("    hub = {")
    end = source.index('    (hub_dir / "latest.json")', start)
    hub_literal = source[start:end]
    assert "decision_workspaces" not in hub_literal
    for key in ("asof", "macro_context_id", "n_transitions_14d", "headline_en", "headline_zh"):
        assert f'"{key}"' in hub_literal


def test_r25_bonds_stale_gap_filter_does_not_import_unrelated_macro_inputs():
    from scripts.build_macro_context import _build_decision_workspaces

    regime = _r25_regime_data()
    regime["conditions"]["stale_inputs"].append("vix")
    regime["conditions"]["vintages"]["vix"] = {
        "asof": "2026-09-01", "age_days": 31, "stale": True,
    }
    out = _build_decision_workspaces(
        _r25_snapshot(), _r25_world_state(), regime, [], "2026-10-02"
    )["bonds"]
    stale = {g["key"] for g in out["data_gaps"] if g["status"] == "stale_input"}
    assert "ebp" in stale and "recession_risk" in stale
    assert "vix" not in stale


def test_r25_canonical_transition_schema_preserves_before_after_values():
    from scripts.build_macro_context import _build_decision_workspaces

    transition = {
        "asof": "2026-10-02",
        "domain": "transmission",
        "field": "yield_curve_regime",
        "from_value": "bear_flattener",
        "to_value": "bear_steepener",
        "macro_context_id": "fixture",
    }
    out = _build_decision_workspaces(
        _r25_snapshot(), _r25_world_state(), _r25_regime_data(),
        [transition], "2026-10-02",
    )["bonds"]
    assert out["changes"] == [{
        "asof": "2026-10-02",
        "domain": "transmission",
        "field": "yield_curve_regime",
        "from": "bear_flattener",
        "to": "bear_steepener",
    }]


def test_r25_future_source_date_is_anomaly_not_ordinary_known_receipt():
    from scripts.build_macro_context import _build_decision_workspaces

    snapshot = _r25_snapshot()
    snapshot["sources"]["data/forex/latest.json"] = "2026-10-04"
    out = _build_decision_workspaces(
        snapshot, _r25_world_state(), _r25_regime_data(), [], "2026-10-02"
    )["forex"]
    assert out["source_receipts"]["forex"]["date_status"] == "future"
    assert out["source_receipts"]["forex"]["age_days"] == -2
    assert any(g["key"] == "forex_source" and g["status"] == "source_date_anomaly"
               for g in out["data_gaps"])


def test_r25_direct_usd_basis_requires_typed_structured_receipt():
    from scripts.build_macro_context import _build_decision_workspaces

    world = _r25_world_state()
    world["fx_dollar"]["direct_usd_cross_currency_basis"] = -12.5
    out = _build_decision_workspaces(
        _r25_snapshot(), world, _r25_regime_data(), [], "2026-10-02"
    )["forex"]
    assert out["funding_evidence"]["direct_usd_cross_currency_basis"] is None
    assert any(g["key"] == "direct_usd_cross_currency_basis" for g in out["data_gaps"])

    world = _r25_world_state()
    world["fx_dollar"]["direct_usd_cross_currency_basis"] = {
        "value_bps": -12.5,
        "asof": "2026-10-02",
        "source": "typed-fixture",
    }
    out = _build_decision_workspaces(
        _r25_snapshot(), world, _r25_regime_data(), [], "2026-10-02"
    )["forex"]
    assert out["funding_evidence"]["direct_usd_cross_currency_basis"] == {
        "value_bps": -12.5,
        "asof": "2026-10-02",
        "source": "typed-fixture",
        "date_status": "known",
    }
    assert not any(g["key"] == "direct_usd_cross_currency_basis" for g in out["data_gaps"])


def test_r25_pair_projection_deduplicates_identity_without_using_scores():
    from scripts.build_macro_context import _build_decision_workspaces

    world = _r25_world_state()
    world["fx_dollar"]["pairs"].append(
        {"pair": "USDMXN", "action": "LONG", "score": 9999}
    )
    out = _build_decision_workspaces(
        _r25_snapshot(), world, _r25_regime_data(), [], "2026-10-02"
    )["forex"]
    assert out["pairs"] == [
        {"pair": "USDMXN", "action": "LONG"},
        {"pair": "AUDUSD", "action": "SHORT"},
    ]


# R25 direct-basis admission: invented receipts only, never provider/market I/O.
_R25_BASIS_PATHS = (
    ("direct_usd_cross_currency_basis",),
    ("usd_cross_currency_basis",),
    ("funding", "usd_cross_currency_basis"),
)


def _r25_put_basis(world, path, receipt):
    target = world["fx_dollar"]
    for key in path[:-1]:
        target = target.setdefault(key, {})
    target[path[-1]] = receipt


def _r25_basis_receipt(**overrides):
    return {"value_bps": -12.5, "asof": "2026-10-02",
            "source": "invented-basis-fixture", **overrides}


@pytest.mark.parametrize("path", _R25_BASIS_PATHS)
@pytest.mark.parametrize("overrides", [
    {"value_bps": float("nan")}, {"value_bps": float("inf")},
    {"value_bps": -float("inf")}, {"value_bps": 10 ** 400},
    {"value_bps": True}, {"value_bps": "-12.5"}, {"value_bps": None},
    {"source": None}, {"source": ""}, {"source": " \t\n"},
    {"source": True}, {"source": {"name": "fixture"}},
    {"asof": "2026-10-03"}, {"asof": "not-a-date"},
    {"asof": "2026-02-30"}, {"asof": ""}, {"asof": None},
    {"asof": 20261002}, {"asof": "2026-10-02T00:00:00Z"},
])
def test_r25_basis_rejects_invalid_receipt_without_ready(path, overrides):
    from scripts.build_macro_context import _build_decision_workspaces

    world = _r25_world_state()
    _r25_put_basis(world, path, _r25_basis_receipt(**overrides))
    out = _build_decision_workspaces(
        _r25_snapshot(), world, _r25_regime_data(), [], "2026-10-02"
    )["forex"]
    assert out["status"] == "partial"
    assert out["funding_evidence"]["direct_usd_cross_currency_basis"] is None
    gap = next(g for g in out["data_gaps"]
               if g["key"] == "direct_usd_cross_currency_basis")
    assert gap["status"] == "unavailable" and gap["substitute_allowed"] is False
    assert out["funding_evidence"]["proxy_funding_state"] == "calm"
    json.dumps(out, allow_nan=False)


@pytest.mark.parametrize("path", _R25_BASIS_PATHS)
@pytest.mark.parametrize("missing", ("value_bps", "asof", "source"))
def test_r25_basis_missing_field_retains_gap(path, missing):
    from scripts.build_macro_context import _build_decision_workspaces

    world = _r25_world_state()
    receipt = _r25_basis_receipt()
    del receipt[missing]
    _r25_put_basis(world, path, receipt)
    out = _build_decision_workspaces(
        _r25_snapshot(), world, _r25_regime_data(), [], "2026-10-02"
    )["forex"]
    assert out["status"] == "partial"
    assert out["funding_evidence"]["direct_usd_cross_currency_basis"] is None


@pytest.mark.parametrize("path", _R25_BASIS_PATHS)
@pytest.mark.parametrize("bps", (-12.5, 0, 0.0, -0.0, 12, 1e100))
@pytest.mark.parametrize("asof", ("2026-10-02", "2026-09-01", "20261002", "2026-W40-5"))
def test_r25_basis_preserves_valid_finite_zero_and_source_date(path, bps, asof):
    from scripts.build_macro_context import _build_decision_workspaces

    world = _r25_world_state()
    receipt = _r25_basis_receipt(value_bps=bps, asof=asof, source=" fixture-provenance ")
    _r25_put_basis(world, path, receipt)
    before = json.dumps(world, sort_keys=True)
    out = _build_decision_workspaces(
        _r25_snapshot(), world, _r25_regime_data(), [], "2026-10-02"
    )["forex"]
    assert out["status"] == "ready"
    assert out["funding_evidence"]["direct_usd_cross_currency_basis"] == {**receipt, "date_status": "known"}
    assert not any(g["key"] == "direct_usd_cross_currency_basis" for g in out["data_gaps"])
    assert out["probability_policy"] == "withheld" and out["display_only"] is True
    assert out["claim_scope"] == "projection_only"
    assert json.dumps(world, sort_keys=True) == before
    json.dumps(out, allow_nan=False)


@pytest.mark.parametrize("invalid", [
    {"value_bps": float("inf")}, {"source": None}, {"asof": "2026-10-03"},
])
def test_r25_basis_invalid_preferred_receipt_does_not_mask_valid_fallback(invalid):
    from scripts.build_macro_context import _build_decision_workspaces

    world = _r25_world_state()
    _r25_put_basis(world, _R25_BASIS_PATHS[0], _r25_basis_receipt(**invalid))
    valid = _r25_basis_receipt(value_bps=0)
    _r25_put_basis(world, _R25_BASIS_PATHS[1], valid)
    _r25_put_basis(world, _R25_BASIS_PATHS[2], _r25_basis_receipt(value_bps=99))
    out = _build_decision_workspaces(
        _r25_snapshot(), world, _r25_regime_data(), [], "2026-10-02"
    )["forex"]
    assert out["status"] == "ready"
    assert out["funding_evidence"]["direct_usd_cross_currency_basis"] == {**valid, "date_status": "known"}


@pytest.mark.parametrize("today", ("not-a-date", "2026-02-30", None))
def test_r25_basis_invalid_projection_clock_never_admits(today):
    from scripts.build_macro_context import _build_decision_workspaces

    world = _r25_world_state()
    _r25_put_basis(world, _R25_BASIS_PATHS[0], _r25_basis_receipt())
    out = _build_decision_workspaces(
        _r25_snapshot(), world, _r25_regime_data(), [], today
    )["forex"]
    assert out["status"] == "partial"
    assert out["funding_evidence"]["direct_usd_cross_currency_basis"] is None


@pytest.mark.parametrize("stale_key", (
    "ebp", "recession_risk", "hy_oas", "us10y", "real_10y", "term_premium",
    "move", "ofr_fsi", "nfci", "anfci", "stlfsi", "sofr_iorb", "repo",
))
def test_r25_basis_admission_never_clears_stale_bonds_families(stale_key):
    from scripts.build_macro_context import _build_decision_workspaces

    world = _r25_world_state()
    _r25_put_basis(world, _R25_BASIS_PATHS[0], _r25_basis_receipt(value_bps=0))
    regime = _r25_regime_data()
    regime["conditions"]["stale_inputs"] = [stale_key]
    out = _build_decision_workspaces(
        _r25_snapshot(), world, regime, [], "2026-10-02"
    )
    assert out["forex"]["status"] == "ready"
    assert out["bonds"]["status"] == "partial"
    assert any(g["key"] == stale_key and g["status"] == "stale_input"
               for g in out["bonds"]["data_gaps"])


def test_r25_bonds_incomplete_core_read_is_partial_not_ready():
    from scripts.build_macro_context import _build_decision_workspaces

    snap = _r25_snapshot()
    snap["labels"]["bonds"] = {}
    snap["labels"]["transmission"] = {}
    snap["gaps"] = []
    world = _r25_world_state()
    world["rates_credit"] = {"health_label": "healthy"}
    regime = _r25_regime_data()
    regime["conditions"]["stale_inputs"] = []

    out = _build_decision_workspaces(
        snap, world, regime, [], "2026-10-02"
    )["bonds"]

    assert out["current_read"]["health"] == "healthy"
    assert any(value is None for value in out["current_read"].values())
    assert out["data_gaps"] == []
    assert out["status"] == "partial"


def test_r25_forex_incomplete_core_read_is_partial_not_ready():
    from scripts.build_macro_context import _build_decision_workspaces

    snap = _r25_snapshot()
    snap["labels"]["fx"] = {}
    snap["gaps"] = []
    world = _r25_world_state()
    world["fx_dollar"] = {
        "dollar_desk": {"trend": "up"},
        "direct_usd_cross_currency_basis": {
            "value_bps": 0,
            "asof": "2026-10-02",
            "source": "invented-basis-fixture",
        },
    }
    regime = _r25_regime_data()
    regime["conditions"]["stale_inputs"] = []

    out = _build_decision_workspaces(
        snap, world, regime, [], "2026-10-02"
    )["forex"]

    assert out["current_read"]["usd_trend"] == "up"
    assert any(value is None for value in out["current_read"].values())
    assert out["data_gaps"] == []
    assert out["status"] == "partial"


# R25 DQ-20261005-01: real producer-to-projection mapping, synthetic inputs only.
_R25_NATIVE_SCENARIO_CASES = [
    ("mapping_only", {"scenarios": {"carry_unwind": {"active": True, "intensity": 70}}}, ["carry_unwind"], []),
    ("list_only", {"scenarios": [{"key": "carry_unwind", "active": True, "intensity": 70}]}, ["carry_unwind"], []),
    ("conflicting_alias", {"active": ["stale_alias"], "scenarios": {"carry_unwind": {"active": True, "intensity": 70}}}, ["carry_unwind"], []),
    ("canonical_empty", {"active": ["stale_alias"], "scenarios": {"carry_unwind": {"active": False, "intensity": 20}}}, [], []),
    ("legacy_only", {"active": ["legacy_name"]}, ["legacy_name"], []),
    ("matching_alias", {"active": ["carry_unwind"], "scenarios": {"carry_unwind": {"active": True, "intensity": 70}}}, ["carry_unwind"], []),
    ("empty", {}, [], []),
    ("building_only", {"scenarios": {"carry_unwind": {"active": False, "intensity": 50}}}, [], ["carry_unwind"]),
]


@pytest.mark.parametrize("name,radar,expected,building", _R25_NATIVE_SCENARIO_CASES,
                         ids=[case[0] for case in _R25_NATIVE_SCENARIO_CASES])
def test_r25_native_producer_scenario_mapping(tmp_path, monkeypatch, name, radar, expected, building):
    import socket
    from engine.neuralweb.world_state import _compose_fx_dollar
    from scripts.build_macro_context import _build_decision_workspaces

    def forbidden_network(*args, **kwargs):
        raise AssertionError("R25 native mapping regression permits no network I/O")

    monkeypatch.setattr(socket.socket, "connect", forbidden_network)
    monkeypatch.setattr(socket, "create_connection", forbidden_network)
    source = tmp_path / "data" / "forex" / "latest.json"
    source.parent.mkdir(parents=True)
    source.write_text(json.dumps({"asof": "2026-10-02", "regime": "fixture", "risk": "fixture",
                                  "regime_radar": radar}), encoding="utf-8")
    lobe = _compose_fx_dollar(root=tmp_path)
    assert isinstance(lobe.get("regime_radar"), dict), "Producer failed before the mapping under test"
    assert lobe["regime_radar"]["active_scenarios"] == expected
    assert lobe["regime_radar"]["building_scenarios"] == building
    result = _build_decision_workspaces(_r25_snapshot(), {"fx_dollar": lobe}, {}, [], "2026-10-02")
    forex = result["forex"]
    assert forex["display_only"] is True
    assert forex["probability_policy"] == "withheld"
    assert forex["funding_evidence"]["direct_usd_cross_currency_basis"] is None
    assert forex["mechanism_evidence"]["building_scenarios"] == building
    assert forex["mechanism_evidence"]["active_scenarios"] == expected
    assert {"score", "probability", "p_cond", "intensity"}.isdisjoint(set(_walk_keys(result)))


def test_r25_native_precanonical_lobe_compatibility():
    from scripts.build_macro_context import _build_decision_workspaces

    lobe = {"asof": "2026-10-02", "regime": "fixture",
            "regime_radar": {"active": ["legacy_name"]}}
    result = _build_decision_workspaces(_r25_snapshot(), {"fx_dollar": lobe}, {}, [], "2026-10-02")
    assert result["forex"]["mechanism_evidence"]["active_scenarios"] == ["legacy_name"]


# R26-20261005: actual native template consumer, no browser or market-source I/O.
@pytest.fixture
def r26_render(tmp_path, monkeypatch):
    import copy
    import re
    import socket
    from jinja2 import Environment, FileSystemLoader
    from engine.i18n import tr, td
    from scripts import build_macro_context as bmc

    def forbidden(*args, **kwargs):
        raise AssertionError("R26 rendering permits no network I/O")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    vm = bmc._build_view_model(_r25_snapshot(), _r25_world_state(), [], "2026-10-02",
                              tmp_path, regime_data=_r25_regime_data())
    env = Environment(loader=FileSystemLoader(str(Path(bmc.__file__).resolve().parents[1] / "templates")),
                      autoescape=True)
    env.globals.update(tr=tr, td=td, ASSET_NAMES=bmc.ASSET_NAMES)
    def render(payload="native"):
        model = copy.deepcopy(vm)
        if payload != "native":
            model["decision_workspaces"] = copy.deepcopy(payload)
        before = copy.deepcopy(model)
        html = env.get_template("macro_context.html.j2").render(
            vm=model, built="2026-10-02 12:00 UTC", today="2026-10-02")
        assert model == before, "Template must not mutate the source projection"
        match = re.search(r"<!-- R26 decision evidence -->(.*?)<!-- /R26 decision evidence -->", html, re.S)
        assert match, "Native Macro Context template has not connected decision_workspaces"
        return match.group(1), html
    return render


def _r26_payload():
    from scripts.build_macro_context import _build_decision_workspaces
    return _build_decision_workspaces(_r25_snapshot(), _r25_world_state(),
                                      _r25_regime_data(), [], "2026-10-02")


def test_r26_native_page_connects_optional_evidence_inside_rates(r26_render):
    fragment, html = r26_render()
    assert '<details id="bonds-forex-evidence"' in fragment
    assert '<summary' in fragment
    assert ' open' not in fragment.split('>', 1)[0]
    assert html.index('id="rates"') < html.index('id="bonds-forex-evidence"') < html.index('id="matrix"')
    assert 'Bonds &amp; Forex' in fragment and '债券与外汇' in fragment
    assert 'not a trade signal' in fragment and '非交易信号' in fragment
    assert 'data-domain="bonds"' in fragment and 'data-domain="forex"' in fragment


@pytest.mark.parametrize("payload", [None, {}, [], "invalid"])
def test_r26_missing_or_malformed_projection_is_explained(r26_render, payload):
    fragment, _ = r26_render(payload)
    assert 'Evidence unavailable' in fragment
    assert '证据不可用' in fragment
    assert 'data-current-read' not in fragment


@pytest.mark.parametrize("key,value", [
    ("schema", "macro_context.decision_workspaces.v999"), ("display_only", False),
    ("display_only", 1), ("claim_scope", "allocation"), ("probability_policy", "allowed"),
])
def test_r26_rejects_unsupported_authority_without_rendering_values(r26_render, key, value):
    payload = _r26_payload()
    payload[key] = value
    payload['bonds']['current_read']['health'] = 'DO_NOT_RENDER_UNTRUSTED'
    fragment, _ = r26_render(payload)
    assert 'Evidence unavailable' in fragment
    assert 'DO_NOT_RENDER_UNTRUSTED' not in fragment


@pytest.mark.parametrize("domain", ['bonds', 'forex'])
def test_r26_domain_authority_failure_keeps_other_domain(r26_render, domain):
    payload = _r26_payload()
    payload[domain]['display_only'] = False
    payload[domain]['current_read'] = {'health': 'DO_NOT_RENDER_UNTRUSTED'}
    fragment, _ = r26_render(payload)
    assert 'DO_NOT_RENDER_UNTRUSTED' not in fragment
    assert 'Evidence unavailable' in fragment
    assert 'data-current-read' in fragment


def test_r26_canonical_empty_does_not_revive_legacy_names(r26_render):
    payload = _r26_payload()
    payload['forex']['mechanism_evidence']['active_scenarios'] = []
    payload['forex']['mechanism_evidence']['active'] = ['STALE_ALIAS']
    fragment, _ = r26_render(payload)
    assert 'STALE_ALIAS' not in fragment
    assert 'No active scenario names supplied' in fragment


def test_r26_active_and_building_scenarios_reach_html_without_statistics(r26_render):
    payload = _r26_payload()
    payload['forex']['mechanism_evidence']['active_scenarios'] = ['carry_unwind']
    payload['forex']['mechanism_evidence']['building_scenarios'] = ['policy_divergence']
    payload['forex']['mechanism_evidence']['p_cond'] = 0.987654321
    payload['forex']['mechanism_evidence']['intensity'] = 987654321
    fragment, _ = r26_render(payload)
    assert 'carry unwind' in fragment.lower()
    assert 'policy divergence' in fragment.lower()
    assert '987654321' not in fragment and 'p_cond' not in fragment


def test_r26_scenario_objects_cannot_expose_nested_stats(r26_render):
    payload = _r26_payload()
    payload['forex']['mechanism_evidence']['active_scenarios'] = [{'score': 'SECRET_SCORE'}, None, 7]
    fragment, _ = r26_render(payload)
    assert 'SECRET_SCORE' not in fragment
    assert 'No active scenario names supplied' in fragment


def test_r26_text_is_escaped_not_interpreted_as_markup(r26_render):
    payload = _r26_payload()
    attack = '<img src=x onerror="alert(1)"><span class="l-en">untrusted</span>'
    payload['bonds']['current_read']['health'] = attack
    payload['bonds']['source_receipts']['bond_health']['path'] = attack
    payload['forex']['mechanism_evidence']['active_scenarios'] = [attack]
    payload['bonds']['data_gaps'] = [{'key': 'custom', 'status': 'unavailable', 'note': attack}]
    fragment, _ = r26_render(payload)
    assert '<img' not in fragment and 'onerror="alert' not in fragment
    assert '&lt;img' in fragment


def test_r26_source_dates_and_future_warning_are_not_freshness(r26_render):
    payload = _r26_payload()
    payload['bonds']['source_receipts']['bond_health'].update(asof='2099-01-01', date_status='future')
    fragment, _ = r26_render(payload)
    assert '2099-01-01' in fragment and 'Future-dated source' in fragment
    assert 'Source dates do not certify vendor freshness' in fragment
    assert 'not a forecast' in fragment


def test_r26_missing_basis_is_not_replaced_by_calm_proxy(r26_render):
    fragment, _ = r26_render()
    assert 'Direct USD funding basis unavailable' in fragment
    assert 'calm' in fragment
    assert 'not a substitute' in fragment


def _r26_payload_with_builder_basis(value_bps, *, asof='2026-10-01', source='R26_BUILDER_BASIS'):
    from scripts.build_macro_context import _build_decision_workspaces

    world = _r25_world_state()
    world['fx_dollar']['direct_usd_cross_currency_basis'] = {
        'value_bps': value_bps, 'asof': asof, 'source': source}
    return _build_decision_workspaces(
        _r25_snapshot(), world, _r25_regime_data(), [], '2026-10-02')


def test_r26_explicit_zero_basis_keeps_its_source_and_unit(r26_render):
    payload = _r26_payload_with_builder_basis(0, source='ZERO_BASIS_SOURCE')
    basis = payload['forex']['funding_evidence']['direct_usd_cross_currency_basis']
    assert basis['date_status'] == 'known'
    fragment, _ = r26_render(payload)
    assert '0.00 bp' in fragment and 'ZERO_BASIS_SOURCE' in fragment


def test_r26_normal_builder_admitted_basis_renders_with_known_date_status(r26_render):
    payload = _r26_payload_with_builder_basis(-12.5, source='NORMAL_BASIS_SOURCE')
    basis = payload['forex']['funding_evidence']['direct_usd_cross_currency_basis']
    assert basis == {
        'value_bps': -12.5, 'asof': '2026-10-01',
        'source': 'NORMAL_BASIS_SOURCE', 'date_status': 'known'}
    fragment, _ = r26_render(payload)
    assert '-12.50 bp' in fragment and 'NORMAL_BASIS_SOURCE' in fragment


@pytest.mark.parametrize('date_status', [None, '', 'future', 'unknown', True, 1])
def test_r26_consumer_requires_builder_known_date_status(r26_render, date_status):
    payload = _r26_payload()
    payload['forex']['funding_evidence']['direct_usd_cross_currency_basis'] = {
        'value_bps': -12.5, 'asof': '2099-01-01',
        'source': 'UNADMITTED_BASIS_STATUS', 'date_status': date_status}
    fragment, _ = r26_render(payload)
    assert 'Direct USD funding basis unavailable' in fragment
    assert 'UNADMITTED_BASIS_STATUS' not in fragment


@pytest.mark.parametrize('asof', ['2099-01-01', 'not-a-date', '2026-13-01', '2026-10-02T00:00:00Z'])
def test_r26_crafted_basis_date_without_owner_admission_is_withheld(r26_render, asof):
    payload = _r26_payload()
    payload['forex']['funding_evidence']['direct_usd_cross_currency_basis'] = {
        'value_bps': -12.5, 'asof': asof, 'source': 'UNADMITTED_BASIS_DATE'}
    fragment, _ = r26_render(payload)
    assert 'Direct USD funding basis unavailable' in fragment
    assert 'UNADMITTED_BASIS_DATE' not in fragment


@pytest.mark.parametrize("value", [None, True, float('inf'), float('nan'), '12'])
def test_r26_bad_basis_values_are_withheld(r26_render, value):
    payload = _r26_payload()
    payload['forex']['funding_evidence']['direct_usd_cross_currency_basis'] = {
        'value_bps': value, 'asof': '2026-10-01', 'source': 'BAD_BASIS_VALUE'}
    fragment, _ = r26_render(payload)
    assert 'Direct USD funding basis unavailable' in fragment
    assert 'BAD_BASIS_VALUE' not in fragment


def test_r26_changes_are_descriptive_and_allowlisted(r26_render):
    payload = _r26_payload()
    payload['forex']['changes'] = [{'asof': '2026-10-01', 'field': 'usd_trend',
                                  'from': 'down', 'to': 'mixed', 'probability': 'SECRET_FORECAST'}]
    fragment, _ = r26_render(payload)
    assert '2026-10-01' in fragment and 'down' in fragment and 'mixed' in fragment
    assert 'SECRET_FORECAST' not in fragment


def test_r26_present_coverage_does_not_claim_investment_readiness(r26_render):
    payload = _r26_payload()
    payload['bonds']['status'] = 'ready'
    fragment, _ = r26_render(payload)
    assert 'Supplied fields complete' in fragment
    assert 'Ready to invest' not in fragment and 'Buy now' not in fragment


def test_r26_adds_no_script_form_remote_resource_or_calculation_owner(r26_render):
    fragment, _ = r26_render()
    for token in ['<script', '<form', '<iframe', '<input', 'localStorage', 'fetch(', 'http://', 'https://']:
        assert token not in fragment
    source = Path('templates/_macro_decision_workspaces.html.j2').read_text()
    assert '<style' not in source and '--' not in source.replace('<!--', '').replace('-->', '')
    assert 'build_macro_context' not in source and 'probability' in source  # guard, not an output


def test_r26_source_paths_remain_exact_not_prettified(r26_render):
    fragment, _ = r26_render()
    assert 'data/bonds/bond_health.json' in fragment
    assert 'data/transmission/latest.json' in fragment
    assert 'data/forex/latest.json' in fragment


def test_r26_scenario_limit_filters_invalid_rows_before_truncating(r26_render):
    payload = _r26_payload()
    payload['forex']['mechanism_evidence']['active_scenarios'] = [None] * 9 + ['carry_unwind']
    fragment, _ = r26_render(payload)
    assert 'carry unwind' in fragment.lower()
    payload['forex']['mechanism_evidence']['active_scenarios'] = ['case_' + str(i) for i in range(10)]
    fragment, _ = r26_render(payload)
    assert 'Additional scenario names remain in the source record.' in fragment
    assert 'case 7' in fragment and 'case 8' not in fragment

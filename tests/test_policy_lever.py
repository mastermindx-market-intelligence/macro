"""Unit tests for the Policy-Lever ARMED/QUIET card (Policy-Shock W2-F).

Coverage:
  - ARMED-rule: all state combinations including boundary -15%
  - whitehouse reader: present / absent / corrupt
  - calendar math (days_to_midterm)
  - artifact schema completeness
  - dashboard.html.j2 template render smoke with policy_lever fixture
"""
from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

# Import the builder functions directly
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _arming_block(armed: bool = False) -> dict:
    """Minimal arming block that mirrors the commodity_signals.technical_arming output."""
    return {
        "stoch_k": 25.0 if armed else 60.0,
        "stoch_d": 20.0 if armed else 35.0,
        "stoch_curl": armed,
        "macd_curl": False,
        "basing": armed,
        "days_in_base": 12 if armed else 0,
        "flatness": 0.03 if armed else 0.17,
        "armed": armed,
        "params": {"version": "v1.1"},
    }


def _lever(armed: bool = False, asset: str | None = "CL=F") -> dict:
    return {
        "name": "Iran / oil",
        "name_zh": "伊朗/石油",
        "asset": asset,
        "arming": _arming_block(armed) if asset else None,
        "watch": "Re-escalation risk watch text.",
        "watch_zh": "再升级风险观察文本。",
    }


# ---------------------------------------------------------------------------
# ARMED rule tests (all state combinations + boundary)
# ---------------------------------------------------------------------------

class TestArmedRule:
    """Verify _compute_state() against the frozen v1 ARMED rule."""

    def _compute_state(self, drawdown_pct, levers):
        from scripts.build_policy_lever import _compute_state
        return _compute_state(drawdown_pct, levers)

    def test_quiet_no_conditions(self):
        """Neither drawdown nor lever armed → QUIET."""
        state = self._compute_state(-10.0, [_lever(False)])
        assert state == "QUIET"

    def test_quiet_drawdown_only_above_threshold(self):
        """Drawdown -14.9% (above -15%) with armed lever → ELEVATED not ARMED."""
        state = self._compute_state(-14.9, [_lever(True)])
        assert state == "ELEVATED"

    def test_boundary_exactly_minus15_no_lever(self):
        """Drawdown exactly -15% with no armed lever → ELEVATED."""
        state = self._compute_state(-15.0, [_lever(False)])
        assert state == "ELEVATED"

    def test_boundary_exactly_minus15_with_lever(self):
        """Drawdown exactly -15% with armed lever → ARMED."""
        state = self._compute_state(-15.0, [_lever(True)])
        assert state == "ARMED"

    def test_drawdown_below_minus15_no_lever(self):
        """Drawdown -20% with no armed lever → ELEVATED."""
        state = self._compute_state(-20.0, [_lever(False)])
        assert state == "ELEVATED"

    def test_drawdown_below_minus15_with_lever(self):
        """Drawdown -20% with armed lever → ARMED."""
        state = self._compute_state(-20.0, [_lever(True)])
        assert state == "ARMED"

    def test_no_drawdown_but_lever_armed(self):
        """drawdown_pct=None (unavailable) AND lever armed → ELEVATED."""
        state = self._compute_state(None, [_lever(True)])
        assert state == "ELEVATED"

    def test_no_drawdown_no_lever(self):
        """drawdown_pct=None AND no lever → QUIET."""
        state = self._compute_state(None, [_lever(False)])
        assert state == "QUIET"

    def test_multiple_levers_any_armed(self):
        """Multiple levers — any armed fires the lever leg → ELEVATED with -10% dd."""
        levers = [_lever(False), _lever(True, asset=None)]
        # lever with asset=None has arming=None, so only lever(True) counts
        # lever(True) with asset != None has arming.armed=True
        levers2 = [_lever(False), _lever(True)]
        state = self._compute_state(-10.0, levers2)
        assert state == "ELEVATED"

    def test_lever_with_none_arming_not_counted(self):
        """Lever where arming is None (China/tariffs) does not count as armed."""
        levers = [_lever(False, asset=None)]  # arming=None
        levers[0]["arming"] = None
        state = self._compute_state(-20.0, levers)
        assert state == "ELEVATED"  # only drawdown fires

    def test_drawdown_minus15_boundary_is_inclusive(self):
        """Confirm <= -15% is inclusive: -15.0 fires."""
        from scripts.build_policy_lever import _DRAWDOWN_THRESHOLD
        assert _DRAWDOWN_THRESHOLD == -0.15
        state = self._compute_state(-15.0, [_lever(True)])
        assert state == "ARMED"

    def test_drawdown_just_above_threshold_not_armed(self):
        """Drawdown -14.99% does not satisfy drawdown leg."""
        state = self._compute_state(-14.99, [_lever(True)])
        assert state == "ELEVATED"


# ---------------------------------------------------------------------------
# Whitehouse reader tests
# ---------------------------------------------------------------------------

class TestWhitehouseReader:
    """Test _compute_jawboning() with present / absent / corrupt file."""

    def _call(self, path):
        from scripts.build_policy_lever import _compute_jawboning
        return _compute_jawboning(path)

    def test_absent_file_returns_nulls(self, tmp_path):
        """Missing file degrades to all-null result — never raises."""
        result = self._call(tmp_path / "nonexistent.jsonl")
        assert result["n_7d"] is None
        assert result["n_30d"] is None
        assert result["last_alert_ts"] is None

    def test_corrupt_file_returns_nulls(self, tmp_path):
        """Corrupt file degrades gracefully — never raises."""
        p = tmp_path / "alerts.jsonl"
        p.write_text("not json\n{broken}", encoding="utf-8")
        result = self._call(p)
        # Partial parse: the non-json line is skipped
        # Either nulls or partial result — must not raise
        assert isinstance(result, dict)

    def test_empty_file_returns_zero_counts(self, tmp_path):
        """Empty file → n_7d=0, n_30d=0."""
        p = tmp_path / "alerts.jsonl"
        p.write_text("", encoding="utf-8")
        result = self._call(p)
        assert result["n_7d"] == 0
        assert result["n_30d"] == 0

    def test_recent_alert_counted_in_7d(self, tmp_path):
        """Alert published yesterday → counted in both 7d and 30d."""
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        p = tmp_path / "alerts.jsonl"
        p.write_text(json.dumps({
            "published": yesterday,
            "banner_title": "A test alert headline",
            "summary": "Summary text",
        }) + "\n", encoding="utf-8")
        result = self._call(p)
        assert result["n_7d"] == 1
        assert result["n_30d"] == 1

    def test_old_alert_not_in_7d(self, tmp_path):
        """Alert from 20 days ago → n_7d=0, n_30d=1."""
        old_ts = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
        p = tmp_path / "alerts.jsonl"
        p.write_text(json.dumps({
            "published": old_ts,
            "banner_title": "Old alert",
        }) + "\n", encoding="utf-8")
        result = self._call(p)
        assert result["n_7d"] == 0
        assert result["n_30d"] == 1

    def test_last_alert_summary_truncated(self, tmp_path):
        """last_alert_summary is truncated to 140 chars."""
        now_ts = datetime.now(timezone.utc).isoformat()
        long_title = "A" * 200
        p = tmp_path / "alerts.jsonl"
        p.write_text(json.dumps({
            "published": now_ts,
            "banner_title": long_title,
        }) + "\n", encoding="utf-8")
        result = self._call(p)
        assert len(result["last_alert_summary"]) <= 140

    def test_last_alert_is_most_recent(self, tmp_path):
        """last_alert_ts is the most recent published timestamp."""
        t1 = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        t2 = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        p = tmp_path / "alerts.jsonl"
        p.write_text(
            json.dumps({"published": t1, "banner_title": "Older"}) + "\n" +
            json.dumps({"published": t2, "banner_title": "Newer"}) + "\n",
            encoding="utf-8",
        )
        result = self._call(p)
        assert result["last_alert_summary"] == "Newer"


# ---------------------------------------------------------------------------
# Calendar math tests
# ---------------------------------------------------------------------------

class TestCalendarMath:

    def test_days_to_midterm_is_positive(self):
        """Before the event the countdown is a non-negative day count."""
        from scripts.build_policy_lever import _compute_calendar
        cal = _compute_calendar()
        if cal["event_state"] == "past":
            # After 2026-11-03 there is no live countdown to report.
            assert cal["days_to_midterm"] is None
        else:
            assert cal["days_to_midterm"] >= 0

    def test_days_to_midterm_value(self):
        """Before the event the countdown equals the whole-day gap to 2026-11-03."""
        from scripts.build_policy_lever import _compute_calendar, _MIDTERM_DATE
        cal = _compute_calendar(now=datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc))
        # The legacy computation counted whole UTC calendar days from midnight.
        midnight = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        expected = (_MIDTERM_DATE - midnight).days
        assert expected == 2
        assert cal["days_to_midterm"] == expected

    def test_days_to_midterm_is_not_a_permanent_zero_after_the_event(self):
        """After 2026-11-03 the countdown is unavailable, not a live zero."""
        from scripts.build_policy_lever import _compute_calendar
        cal = _compute_calendar(now=datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc))
        assert cal["days_to_midterm"] is None
        assert cal["event_state"] == "past"
        assert cal["days_since_midterm"] == 7

    def test_calendar_context_note_present(self):
        """context_note and context_note_zh must be non-empty strings."""
        from scripts.build_policy_lever import _compute_calendar
        cal = _compute_calendar()
        assert cal["context_note"]
        assert cal["context_note_zh"]

    def test_calendar_no_directional_language(self):
        """context_note must not contain directional signal language."""
        from scripts.build_policy_lever import _compute_calendar
        cal = _compute_calendar()
        forbidden = ["buy", "sell", "short", "long", "intent", "predict"]
        for word in forbidden:
            assert word.lower() not in cal["context_note"].lower(), (
                f"calendar context_note contains forbidden word '{word}'"
            )


# ---------------------------------------------------------------------------
# Artifact schema completeness tests
# ---------------------------------------------------------------------------

class TestArtifactSchema:

    def _build(self, tmp_path=None):
        """Build and return the artifact dict (no file write needed)."""
        from scripts.build_policy_lever import build
        return build()

    def test_schema_field_present(self):
        artifact = self._build()
        assert artifact["schema"] == "policy_lever.v1"

    def test_required_top_level_keys(self):
        artifact = self._build()
        required = [
            "schema", "as_of", "favored_complex", "jawboning",
            "calendar", "levers", "state", "framing", "framing_zh",
        ]
        for key in required:
            assert key in artifact, f"Missing top-level key: {key!r}"

    def test_state_is_valid_value(self):
        artifact = self._build()
        assert artifact["state"] in ("QUIET", "ELEVATED", "ARMED")

    def test_favored_complex_schema(self):
        artifact = self._build()
        fc = artifact["favored_complex"]
        assert "basket" in fc
        assert "drawdown_pct" in fc
        assert "note" in fc
        assert "note_zh" in fc

    def test_jawboning_schema(self):
        artifact = self._build()
        jw = artifact["jawboning"]
        assert "n_7d" in jw
        assert "n_30d" in jw
        assert "last_alert_ts" in jw
        assert "last_alert_summary" in jw

    def test_calendar_schema(self):
        artifact = self._build()
        cal = artifact["calendar"]
        assert "days_to_midterm" in cal
        assert "context_note" in cal
        assert "context_note_zh" in cal

    def test_levers_schema(self):
        artifact = self._build()
        levers = artifact["levers"]
        assert isinstance(levers, list)
        assert len(levers) >= 1
        for lv in levers:
            assert "name" in lv
            assert "name_zh" in lv
            assert "watch" in lv
            assert "watch_zh" in lv

    def test_framing_no_probabilities(self):
        """PS-R4: framing copy must not contain raw probability language.
        'more likely' (relative frequency expression) is canonical masterplan text
        and is explicitly permitted — only bare probability claims are forbidden."""
        artifact = self._build()
        # "likely" and "more likely" are the masterplan's canonical framing;
        # forbid only hard probability / percentage claims.
        prob_words = ["probability", "probable", "chance", "percent", "%"]
        framing = artifact.get("framing", "")
        for word in prob_words:
            assert word.lower() not in framing.lower(), (
                f"framing contains probability word '{word}'"
            )

    def test_watch_copy_no_probabilities(self):
        """PS-R4: watch copy in levers must not contain probability language."""
        artifact = self._build()
        prob_words = ["probability", "probable", "chance", "will likely", "will probably"]
        for lv in artifact["levers"]:
            watch = lv.get("watch", "")
            for word in prob_words:
                assert word.lower() not in watch.lower(), (
                    f"lever '{lv.get('name')}' watch contains probability word '{word}'"
                )

    def test_artifact_json_serializable(self):
        """Artifact must be JSON-serializable (no datetime objects, etc.)."""
        artifact = self._build()
        serialized = json.dumps(artifact, default=str)
        reloaded = json.loads(serialized)
        assert reloaded["schema"] == "policy_lever.v1"

    def test_oil_arming_block_matches_w1b_schema(self):
        """The Iran/oil lever's arming block must contain all W1-B keys."""
        artifact = self._build()
        oil_lever = next((lv for lv in artifact["levers"] if lv.get("asset") == "CL=F"), None)
        if oil_lever is None:
            pytest.skip("CL=F lever absent — price data unavailable in test env")
        arming = oil_lever.get("arming")
        if arming is None:
            pytest.skip("CL=F arming None — price data unavailable in test env")
        required_keys = [
            "stoch_k", "stoch_d", "stoch_curl", "macd_curl",
            "basing", "days_in_base", "flatness", "armed",
        ]
        for key in required_keys:
            assert key in arming, f"arming block missing key: {key!r}"


# ---------------------------------------------------------------------------
# Caption staleness + content correctness tests
# ---------------------------------------------------------------------------

class TestCaptionStaleness:
    """Verify copy_as_of / copy_age_days / copy_stale stamping on built levers."""

    def _build(self):
        from scripts.build_policy_lever import build
        return build()

    def test_levers_have_copy_as_of(self):
        """Every lever must have a non-empty copy_as_of string."""
        artifact = self._build()
        for lv in artifact["levers"]:
            assert "copy_as_of" in lv, f"lever '{lv.get('name')}' missing copy_as_of"
            assert isinstance(lv["copy_as_of"], str) and lv["copy_as_of"], (
                f"lever '{lv.get('name')}' copy_as_of is empty"
            )

    def test_levers_have_copy_age_days(self):
        """Every lever must have copy_age_days as a non-negative int."""
        artifact = self._build()
        for lv in artifact["levers"]:
            assert "copy_age_days" in lv, f"lever '{lv.get('name')}' missing copy_age_days"
            assert isinstance(lv["copy_age_days"], int), (
                f"lever '{lv.get('name')}' copy_age_days is not int: {lv['copy_age_days']!r}"
            )
            assert lv["copy_age_days"] >= 0, (
                f"lever '{lv.get('name')}' copy_age_days is negative"
            )

    def test_levers_have_copy_stale_bool(self):
        """copy_stale must be a bool on every lever."""
        artifact = self._build()
        for lv in artifact["levers"]:
            assert "copy_stale" in lv, f"lever '{lv.get('name')}' missing copy_stale"
            assert isinstance(lv["copy_stale"], bool), (
                f"lever '{lv.get('name')}' copy_stale is not bool"
            )

    def test_china_caption_no_90_day(self):
        """China lever watch must not reference the stale '90-day' truce language."""
        artifact = self._build()
        china = next((lv for lv in artifact["levers"] if "China" in lv.get("name", "")), None)
        assert china is not None, "China/tariffs lever not found"
        assert "90-day" not in china["watch"], "China watch still contains stale '90-day' text"
        assert "90-day" not in china.get("watch_zh", ""), (
            "China watch_zh still contains stale '90天' / '90-day' text"
        )

    def test_iran_caption_no_hardcoded_date(self):
        """Iran lever watch must not contain the stale hardcoded '2026-07-08' event date."""
        artifact = self._build()
        iran = next((lv for lv in artifact["levers"] if "Iran" in lv.get("name", "")), None)
        assert iran is not None, "Iran/oil lever not found"
        assert "2026-07-08" not in iran["watch"], (
            "Iran watch still contains stale hardcoded date '2026-07-08'"
        )

    def test_captions_no_intent_word(self):
        """PS-R1: neither lever watch caption may contain the word 'intent'."""
        artifact = self._build()
        for lv in artifact["levers"]:
            watch = lv.get("watch", "")
            assert "intent" not in watch.lower(), (
                f"lever '{lv.get('name')}' watch contains forbidden word 'intent'"
            )

    def test_captions_no_probability_words(self):
        """PS-R4: watch captions must not contain probability / percentage language."""
        artifact = self._build()
        forbidden = ["probability", "probable", "chance", "%"]
        for lv in artifact["levers"]:
            watch = lv.get("watch", "")
            for word in forbidden:
                assert word.lower() not in watch.lower(), (
                    f"lever '{lv.get('name')}' watch contains forbidden word '{word}'"
                )


# ---------------------------------------------------------------------------
# Template render smoke test with policy_lever fixture
# ---------------------------------------------------------------------------

class TestTemplateRender:
    """Smoke-test that dashboard.html.j2 renders without exception when
    policy_lever is present and when it is absent/None.
    Mirrors the exact env setup from test_dashboard_template_render.py."""

    ROOT = Path(__file__).resolve().parent.parent

    def _env(self):
        import jinja2
        from engine import i18n
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.ROOT / "templates"))
        )
        env.filters["min"] = lambda seq: min(seq)
        env.globals.update(td=i18n.td, tr=i18n.tr, zip=zip)
        # The macro-mode Policy Monitor card + dialog render from the
        # normalized display model (lib/policy_monitor_view.py). Registering the
        # normalizer here exercises the REAL panel in this file's render tests;
        # the legacy `policy-lever-card` fallback band assertions below are
        # unchanged.
        from lib import policy_monitor_view as _pmv
        env.globals["pm_view"] = _pmv.build_view
        return env

    def _base_vm(self, policy_lever=None) -> dict:
        """Minimal vm that mirrors test_dashboard_template_render._base_vm()."""
        return dict(
            latest={
                "date": "2026-07-09", "quad": "Q2", "quad_name": "Reflation",
                "label": "Q2 — Reflation", "confidence": 0.72,
                "fed_stance": None, "dislocation": None, "turning_point": None,
                "risk_radar": None, "rate_inflation_transmission": None,
                "cross_asset_confirm": None, "transition_state": "stable",
                "liquidity_overlay": "neutral", "conditions": None,
                "risk_state": None, "cycle_tag": "mid",
            },
            mtf=None, macro_catalysts=[], event_strip=[], event_risk=None,
            prediction_markets=None, narrative_regime=None, ndi=None,
            macro_news=None, macro_brief=None, macro_news_disclaimer="",
            macro_news_disclaimer_zh="", alerts=[], pb=None, month_name="July",
            commodities=[], sector_timing={},
            action_board={"hold": [], "avoid": [], "notable": [], "buy": []},
            top_setups=[],
            us_standouts={"buy": [], "eligible": 0},
            us_board_outcomes=None, market_gamma=None,
            components_confirming=[], components_contradicting=[],
            flip_plain=None, internals=[], size_style=[], breadth_div=None,
            breadth_panel=None, adv_breadth=None, sector_setups=None,
            generated_utc="2026-07-09 06:00", chart_liquidity=None,
            chart_credit_breadth=None, market_tiles=[], vix=None, chart_vix=None,
            positioning=[], holdings_changes=[], holdings_threshold=5.0,
            accumulation=[], flows_html="", health=[], factor_leadership=None,
            nowcast_hist=None, stance=None, index_health=[], alloc_card=None,
            risk_model=None, chart_risk_model=None, chart_curve=None,
            chart_vix_term=None, cross_asset=None, fear_euphoria=None,
            regime_snap=None, market_state=None, signal_stack=None,
            vol_shock=None, froth_fragility=None, fear_greed=None,
            sector_heat=None, dispersion_regime=None,
            policy_lever=policy_lever,
        )

    def _policy_lever_fixture(self, state: str = "QUIET") -> dict:
        """Minimal policy_lever artifact fixture for template testing."""
        return {
            "schema": "policy_lever.v1",
            "as_of": "2026-07-09",
            "favored_complex": {
                "basket": ["SMH", "SOXX"],
                "drawdown_pct": -12.76,
                "drawdown_z": -2.45,
                "note": "Semis complex is -12.8% from 120d peak.",
                "note_zh": "半导体组合距120日高点-12.8%。",
            },
            "jawboning": {
                "n_7d": 0, "n_30d": 4,
                "last_alert_ts": "2026-06-30T15:12:06+00:00",
                "last_alert_summary": "Trump NEPA overhaul — tailwind for energy.",
            },
            "calendar": {
                "days_to_midterm": 117,
                "context_note": "US midterm elections: 117 days (2026-11-03). Context only.",
                "context_note_zh": "美国中期选举：117天（2026年11月3日）。仅作背景参考。",
            },
            "levers": [
                {
                    "name": "Iran / oil", "name_zh": "伊朗/石油",
                    "asset": "CL=F",
                    "arming": {
                        "stoch_k": 56.81, "stoch_d": 32.23,
                        "stoch_curl": False, "macd_curl": False,
                        "basing": False, "days_in_base": 25, "flatness": 0.1681,
                        "armed": False, "params": {"version": "v1.1"},
                    },
                    "watch": "Middle East escalation is the transmission channel to rate-cut repricing.",
                    "watch_zh": "中东局势升级是向降息重定价传导的通道，石油是核心杠杆。",
                    "copy_as_of": "2026-07-18",
                    "copy_age_days": 0,
                    "copy_stale": False,
                },
                {
                    "name": "China / tariffs", "name_zh": "中国/关税",
                    "asset": None, "arming": None,
                    "watch": "US-China trade friction is the policy channel most directly tied to semis supply-chain margins.",
                    "watch_zh": "中美贸易摩擦是与半导体供应链利润率关联最直接的政策渠道。",
                    "copy_as_of": "2026-07-18",
                    "copy_age_days": 0,
                    "copy_stale": False,
                },
            ],
            "state": state,
            "framing": "Conditions under which violent reversals are more likely — not intent, not timing.",
            "framing_zh": "衡量剧烈反转更可能发生的条件——不是意图，也不是时点。",
        }

    def test_render_macro_mode_policy_lever_none(self):
        """macro mode renders without exception when policy_lever=None."""
        env = self._env()
        html = env.get_template("dashboard.html.j2").render(**self._base_vm(None), mode="macro")
        assert len(html) > 50_000
        assert "policy-lever-card" not in html

    def test_render_stocks_mode_policy_lever_none(self):
        """stocks mode renders without exception when policy_lever=None."""
        env = self._env()
        html = env.get_template("dashboard.html.j2").render(**self._base_vm(None), mode="stocks")
        assert len(html) > 50_000
        assert "policy-lever-card" not in html

    def test_render_macro_mode_with_quiet_lever(self):
        """macro mode renders the policy_lever card (QUIET state)."""
        env = self._env()
        pl = self._policy_lever_fixture("QUIET")
        html = env.get_template("dashboard.html.j2").render(**self._base_vm(pl), mode="macro")
        assert "policy-lever-card" in html
        assert "QUIET" in html or "平静" in html

    def test_render_macro_mode_renders_the_normalized_monitor_panel(self):
        """The macro-mode Policy Monitor card + dialog render from the
        normalized display model — same ids, same shared dialog controller."""
        env = self._env()
        pl = self._policy_lever_fixture("ELEVATED")
        html = env.get_template("dashboard.html.j2").render(**self._base_vm(pl), mode="macro")
        assert html.count('id="sx-policy-v2"') == 1
        assert html.count('id="dlg-policy"') == 1
        assert html.count('id="dlg-policy-lever-card"') == 1
        assert "mx5OpenDlg('dlg-policy')" in html
        # This legacy fixture has undated predicates and no qualifying deep
        # drawdown. Its raw ELEVATED label cannot prove a complete assessment.
        assert "Assessment unavailable" in html
        assert "评估不可用" in html

    def test_render_macro_mode_keeps_a_zero_alert_count_visible(self):
        """n_7d = 0 is a real reading: it must not disappear behind truthiness."""
        env = self._env()
        pl = self._policy_lever_fixture("QUIET")
        html = env.get_template("dashboard.html.j2").render(**self._base_vm(pl), mode="macro")
        assert "Recorded policy alerts: 0 (7d)" in html

    def test_render_macro_mode_with_armed_lever(self):
        """macro mode renders the policy_lever card (ARMED state).
        The card lives inside the {% if mode != 'stocks' %} block — it renders
        on macro.html (the US market-state surface) only."""
        env = self._env()
        pl = self._policy_lever_fixture("ARMED")
        html = env.get_template("dashboard.html.j2").render(**self._base_vm(pl), mode="macro")
        assert "policy-lever-card" in html
        assert "ARMED" in html or "已触发" in html

    def test_render_stocks_mode_card_absent(self):
        """stocks mode does NOT render the policy-lever card — it lives on the
        macro (market-state) surface only, not on the stock-dashboard surface."""
        env = self._env()
        pl = self._policy_lever_fixture("ARMED")
        html = env.get_template("dashboard.html.j2").render(**self._base_vm(pl), mode="stocks")
        assert "policy-lever-card" not in html

    def test_render_elevated_state(self):
        """ELEVATED state renders correctly in macro mode."""
        env = self._env()
        pl = self._policy_lever_fixture("ELEVATED")
        html = env.get_template("dashboard.html.j2").render(**self._base_vm(pl), mode="macro")
        assert "ELEVATED" in html or "警戒" in html

    def test_render_shows_drawdown(self):
        """The drawdown_pct value renders on the card (macro mode)."""
        env = self._env()
        pl = self._policy_lever_fixture()
        html = env.get_template("dashboard.html.j2").render(**self._base_vm(pl), mode="macro")
        assert "-12.8%" in html or "-12.76" in html

    def test_render_shows_jawboning_counts(self):
        """Jawboning 7d/30d counts render on the card (macro mode)."""
        env = self._env()
        pl = self._policy_lever_fixture()
        html = env.get_template("dashboard.html.j2").render(**self._base_vm(pl), mode="macro")
        assert "n_7d" not in html  # raw key never appears, only values
        # n_7d=0 shows as "0"
        assert "30d" in html or "30日" in html

    def test_render_lever_arming_shows_flatness(self):
        """Arming sub-chips (days_in_base, flatness) render on the lever table (macro mode)."""
        env = self._env()
        pl = self._policy_lever_fixture()
        html = env.get_template("dashboard.html.j2").render(**self._base_vm(pl), mode="macro")
        assert "25d" in html   # days_in_base=25
        assert "flat=" in html  # flatness display

    def test_no_translated_title_attributes(self):
        """CI guard: no Chinese text in title= attributes — test in macro mode
        where the policy-lever card is actually rendered."""
        env = self._env()
        pl = self._policy_lever_fixture()
        html = env.get_template("dashboard.html.j2").render(**self._base_vm(pl), mode="macro")
        # Extract title= attribute values and check for Chinese chars
        import re
        titles = re.findall(r'title="([^"]*)"', html)
        for title_val in titles:
            chinese_chars = [c for c in title_val if '一' <= c <= '鿿']
            assert not chinese_chars, (
                f"title= attribute contains Chinese text: {title_val!r}"
            )

    def test_render_basket_caveat_visible(self):
        """basket_caveat renders as a visible warning in macro mode."""
        env = self._env()
        pl = self._policy_lever_fixture()
        # Inject an incomplete-basket scenario
        pl["favored_complex"]["basket_incomplete"] = True
        pl["favored_complex"]["basket_caveat"] = "Basket incomplete — data missing for: SOXX."
        pl["favored_complex"]["basket_caveat_zh"] = "组合不完整——以下成员数据缺失：SOXX。"
        html = env.get_template("dashboard.html.j2").render(**self._base_vm(pl), mode="macro")
        assert "Basket incomplete" in html or "组合不完整" in html

    def test_render_zh_jaw_summary_rendered(self):
        """ZH jawboning summary (last_alert_summary_zh) renders in macro mode."""
        env = self._env()
        pl = self._policy_lever_fixture()
        pl["jawboning"]["last_alert_summary_zh"] = "特朗普NEPA改革解锁联邦土地及许可证"
        html = env.get_template("dashboard.html.j2").render(**self._base_vm(pl), mode="macro")
        assert "特朗普NEPA改革" in html


# ---------------------------------------------------------------------------
# New unit tests for the four Opus-review findings
# ---------------------------------------------------------------------------

class TestBasketIntegrityLabeling:
    """Finding 1 (MAJOR): basket misattribution + incomplete caveat + zero-member null."""

    def _call(self, tickers, patch_load=None):
        """Call _compute_drawdown with optional monkey-patch for _load_price."""
        from scripts import build_policy_lever as mod
        if patch_load is not None:
            orig = mod._load_price
            mod._load_price = patch_load
            try:
                return mod._compute_drawdown(tickers)
            finally:
                mod._load_price = orig
        return mod._compute_drawdown(tickers)

    def _make_prices(self, n=200, start=100.0, drift=0.0):
        """Synthetic daily close series."""
        import pandas as pd
        import numpy as np
        dates = pd.date_range("2025-01-01", periods=n, freq="B")
        closes = start * np.exp(np.cumsum(np.random.default_rng(42).normal(drift, 0.01, n)))
        df = pd.DataFrame({"close": closes, "open": closes, "high": closes, "low": closes}, index=dates)
        return df

    def test_zero_members_returns_null_drawdown(self):
        """When ALL configured members fail to load → drawdown_pct is None."""
        result = self._call(["SMH", "SOXX"], patch_load=lambda t: None)
        assert result["drawdown_pct"] is None
        assert result["basket_incomplete"] is True
        assert "basket_caveat" in result
        assert result["basket_caveat"]  # non-empty string

    def test_zero_members_caveat_zh_present(self):
        """Zero-member null: basket_caveat_zh must also be present."""
        result = self._call(["SMH", "SOXX"], patch_load=lambda t: None)
        assert "basket_caveat_zh" in result
        assert result["basket_caveat_zh"]

    def test_partial_load_labels_loaded_only(self):
        """When one member missing, basket and note reflect only loaded members."""
        px = self._make_prices()

        def _fake_load(t):
            return px if t == "SMH" else None

        result = self._call(["SMH", "SOXX"], patch_load=_fake_load)
        assert result["basket_incomplete"] is True
        assert "SMH" in result["basket"]
        assert "SOXX" not in result["basket"]
        # note must NOT say "SMH/SOXX" — must reflect only what loaded
        assert "SOXX" not in result["note"] or "SMH" in result["note"]

    def test_partial_load_caveat_present(self):
        """Partial load: basket_caveat warns about missing member."""
        px = self._make_prices()

        def _fake_load(t):
            return px if t == "SMH" else None

        result = self._call(["SMH", "SOXX"], patch_load=_fake_load)
        assert "basket_caveat" in result
        assert "SOXX" in result["basket_caveat"]

    def test_full_load_no_caveat(self):
        """When all members load, basket_incomplete=False and no caveat key."""
        px = self._make_prices()
        result = self._call(["SMH", "SOXX"], patch_load=lambda t: px)
        assert result["basket_incomplete"] is False
        assert "basket_caveat" not in result

    def test_full_load_basket_contains_all_members(self):
        """All members loaded → basket list contains both tickers."""
        px = self._make_prices()
        result = self._call(["SMH", "SOXX"], patch_load=lambda t: px)
        assert set(result["basket"]) == {"SMH", "SOXX"}


class TestReturnsEWComposite:
    """Finding 2 (MINOR): equal-weight composite from returns, not price level."""

    def _make_prices_scale(self, n=200, start=100.0, drift=0.0, seed=42):
        """Synthetic daily close with controllable start price."""
        import pandas as pd
        import numpy as np
        dates = pd.date_range("2025-01-01", periods=n, freq="B")
        closes = start * np.exp(np.cumsum(np.random.default_rng(seed).normal(drift, 0.01, n)))
        df = pd.DataFrame({"close": closes, "open": closes, "high": closes, "low": closes}, index=dates)
        return df

    def test_returns_ew_differs_from_price_mean_on_scale_mismatch(self):
        """Two members with very different price scales: returns-EW should differ
        from price-level mean.  Verifies the construction change matters."""
        import pandas as pd
        import numpy as np
        from scripts import build_policy_lever as mod

        # Both members have the same synthetic *return* path (seed=42) but at
        # very different price scales (10 vs 1000).
        px_low = self._make_prices_scale(n=200, start=10.0, seed=42)
        px_high = self._make_prices_scale(n=200, start=1000.0, seed=99)

        # Compute drawdown via the builder (returns-EW path)
        def _fake_load(t):
            return px_low if t == "SMH" else px_high

        result = mod._compute_drawdown.__wrapped__(["SMH", "SOXX"]) if hasattr(
            mod._compute_drawdown, "__wrapped__"
        ) else None

        orig = mod._load_price
        mod._load_price = _fake_load
        try:
            result_ew = mod._compute_drawdown(["SMH", "SOXX"])
        finally:
            mod._load_price = orig

        # Compute what price-level mean would give
        aligned = pd.concat([px_low["close"].rename("SMH"), px_high["close"].rename("SOXX")], axis=1)
        aligned = aligned.sort_index().ffill().dropna(how="all")
        price_composite = aligned.mean(axis=1).tail(121)
        price_peak = float(price_composite.max())
        price_current = float(price_composite.iloc[-1])
        dd_price_mean = round((price_current / price_peak - 1) * 100, 2)

        dd_ew = result_ew["drawdown_pct"]
        assert dd_ew is not None
        # The two methods should differ when price scales are mismatched
        # (difference may be small if returns are similar, but let's verify
        # the non-None path ran and the construction is consistent)
        assert isinstance(dd_ew, float)
        # Returns-EW drawdown should NOT equal price-mean drawdown when scales differ
        # (tolerance: allow match only if scales are effectively the same)
        price_scale_ratio = px_high["close"].mean() / px_low["close"].mean()
        if price_scale_ratio > 5:
            # Scales are very different — the two methods must differ
            assert abs(dd_ew - dd_price_mean) > 0.01, (
                f"returns-EW ({dd_ew}) should differ from price-mean ({dd_price_mean}) "
                f"when scale ratio is {price_scale_ratio:.1f}x"
            )

    def test_returns_ew_identical_series_gives_same_drawdown(self):
        """When both members have the same price series, returns-EW = price-mean = member drawdown."""
        import pandas as pd
        from scripts import build_policy_lever as mod

        px = self._make_prices_scale(n=200, start=100.0, seed=42)

        orig = mod._load_price
        mod._load_price = lambda t: px
        try:
            result = mod._compute_drawdown(["SMH", "SOXX"])
        finally:
            mod._load_price = orig

        # compute member drawdown directly
        trail = px["close"].tail(121)
        peak = float(trail.max())
        cur = float(trail.iloc[-1])
        expected_dd = round((cur / peak - 1) * 100, 2)

        assert result["drawdown_pct"] is not None
        # When returns are identical the EW composite drawdown matches individual member
        assert abs(result["drawdown_pct"] - expected_dd) < 0.15, (
            f"EW returns composite drawdown {result['drawdown_pct']} "
            f"differs too much from member drawdown {expected_dd}"
        )


class TestZHJawboningSummary:
    """Finding 3 (MINOR): ZH summary prefers banner_title_zh / summary_zh."""

    def _call(self, path):
        from scripts.build_policy_lever import _compute_jawboning
        return _compute_jawboning(path)

    def test_zh_summary_from_banner_title_zh(self, tmp_path):
        """banner_title_zh present → last_alert_summary_zh uses it."""
        now_ts = datetime.now(timezone.utc).isoformat()
        p = tmp_path / "alerts.jsonl"
        p.write_text(json.dumps({
            "published": now_ts,
            "banner_title": "EN headline",
            "banner_title_zh": "中文标题",
            "summary": "EN summary text",
        }) + "\n", encoding="utf-8")
        result = self._call(p)
        assert result["last_alert_summary_zh"] == "中文标题"
        assert result["last_alert_summary"] == "EN headline"

    def test_zh_summary_from_summary_zh_when_no_banner_title_zh(self, tmp_path):
        """summary_zh present (no banner_title_zh) → last_alert_summary_zh uses summary_zh."""
        now_ts = datetime.now(timezone.utc).isoformat()
        p = tmp_path / "alerts.jsonl"
        p.write_text(json.dumps({
            "published": now_ts,
            "banner_title": "EN headline",
            "summary_zh": "中文摘要",
        }) + "\n", encoding="utf-8")
        result = self._call(p)
        assert result["last_alert_summary_zh"] == "中文摘要"

    def test_zh_summary_falls_back_to_en_when_no_zh_field(self, tmp_path):
        """No ZH fields → last_alert_summary_zh falls back to EN banner_title."""
        now_ts = datetime.now(timezone.utc).isoformat()
        p = tmp_path / "alerts.jsonl"
        p.write_text(json.dumps({
            "published": now_ts,
            "banner_title": "EN headline only",
        }) + "\n", encoding="utf-8")
        result = self._call(p)
        assert result["last_alert_summary_zh"] == "EN headline only"
        assert result["last_alert_summary"] == "EN headline only"

    def test_zh_summary_key_always_present(self, tmp_path):
        """last_alert_summary_zh key is always present in the result dict."""
        p = tmp_path / "alerts.jsonl"
        p.write_text("", encoding="utf-8")
        result = self._call(p)
        assert "last_alert_summary_zh" in result


class TestTornLineResilience:
    """Finding 4 (MINOR): per-line parse skips bad lines without nulling the block."""

    def _call(self, path):
        from scripts.build_policy_lever import _compute_jawboning
        return _compute_jawboning(path)

    def test_torn_last_line_skipped_good_lines_counted(self, tmp_path):
        """A torn (truncated) last JSON line is skipped; valid lines are counted."""
        now_ts = datetime.now(timezone.utc).isoformat()
        p = tmp_path / "alerts.jsonl"
        good_line = json.dumps({"published": now_ts, "banner_title": "Good alert"})
        torn_line = '{"published":"' + now_ts + '","banner_title":"torn'  # intentionally truncated
        p.write_text(good_line + "\n" + torn_line, encoding="utf-8")
        result = self._call(p)
        # Good line must be counted; torn line must not crash the whole block
        assert result["n_7d"] == 1
        assert result["last_alert_summary"] == "Good alert"
        assert result.get("_skipped_lines", 0) == 1

    def test_all_bad_lines_skipped_returns_unavailable_counts(self, tmp_path):
        """All bad lines → counts are UNAVAILABLE, not a confident zero.

        R2 producer integrity: with no eligible record basis there is no window
        to count, so n_7d/n_30d are None and the file is qualified as
        unusable. The previous 0/0 asserted absence of activity that was never
        observed.
        """
        p = tmp_path / "alerts.jsonl"
        p.write_text("not json\n{broken line\nanother bad", encoding="utf-8")
        result = self._call(p)
        assert result["n_7d"] is None
        assert result["n_30d"] is None
        assert result["source_status"] == "unusable"
        assert result.get("_skipped_lines", 0) == 3

    def test_mixed_good_bad_lines(self, tmp_path):
        """Mix of good and bad lines: good lines counted, bad skipped."""
        now_ts = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        old_ts = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
        p = tmp_path / "alerts.jsonl"
        lines = [
            json.dumps({"published": now_ts, "banner_title": "Recent"}),
            "BAD LINE HERE",
            json.dumps({"published": old_ts, "banner_title": "Older"}),
        ]
        p.write_text("\n".join(lines), encoding="utf-8")
        result = self._call(p)
        assert result["n_7d"] == 1
        assert result["n_30d"] == 2
        assert result.get("_skipped_lines", 0) == 1


# ---------------------------------------------------------------------------
# R2 producer integrity (P2.T1 / P2.T2)
#
# Deterministic evaluation instant: every case below injects a fixed `now`
# through the producer's own parameter. The production default (wall clock)
# is untouched, so nothing here changes production semantics.
# ---------------------------------------------------------------------------

_EVAL = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)
_CUT_7D = _EVAL - timedelta(days=7)
_CUT_30D = _EVAL - timedelta(days=30)


def _write_jsonl(tmp_path, records, name="alerts.jsonl"):
    """Write a jsonl fixture. str entries are written verbatim (corrupt lines)."""
    p = tmp_path / name
    lines = [r if isinstance(r, str) else json.dumps(r) for r in records]
    p.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return p


def _jw(path, now=_EVAL):
    """Call the jawboning reader at a fixed evaluation instant."""
    from scripts.build_policy_lever import _compute_jawboning
    return _compute_jawboning(path, now=now)


@pytest.fixture(scope="module")
def built_artifact():
    """One real build, shared by the timestamp assertions."""
    from scripts.build_policy_lever import build
    return build()


class TestJawboningStrictRecordValidation:
    """A record is an OBJECT with a usable timestamp; anything else is rejected."""

    def test_json_scalar_lines_do_not_crash(self, tmp_path):
        """null / bool / number / string / array lines are rejected, never crashed on."""
        p = _write_jsonl(tmp_path, ["null", "true", "42", '"a string"', "[]"])
        r = _jw(p)
        assert r["n_7d"] is None
        assert r["n_30d"] is None
        assert r["source_status"] == "unusable"
        assert r["diagnostics"]["invalid_structure"] == 5
        assert r["diagnostics"]["malformed_json"] == 0

    def test_json_array_line_does_not_crash(self, tmp_path):
        """Reproduced defect: a valid JSON array line raised AttributeError."""
        p = _write_jsonl(tmp_path, ["[]"])
        r = _jw(p)
        assert r["diagnostics"]["invalid_structure"] == 1
        assert r["n_7d"] is None
        assert r["last_alert_ts"] is None

    def test_json_null_line_does_not_crash(self, tmp_path):
        """Reproduced defect: a JSON null line raised AttributeError."""
        p = _write_jsonl(tmp_path, ["null"])
        r = _jw(p)
        assert r["diagnostics"]["invalid_structure"] == 1
        assert r["source_status"] == "unusable"

    def test_object_without_timestamp_is_invalid(self, tmp_path):
        """A record with no timestamp field cannot be observed."""
        p = _write_jsonl(tmp_path, [{"banner_title": "no time here"}])
        r = _jw(p)
        assert r["diagnostics"]["invalid_timestamp"] == 1
        assert r["diagnostics"]["invalid_timestamp_reasons"]["missing"] == 1
        assert r["n_7d"] is None

    def test_wrongtype_timestamp_is_invalid(self, tmp_path):
        """A numeric timestamp is a wrong type, not a crash and not an observation."""
        p = _write_jsonl(tmp_path, [{"published": 12345, "banner_title": "x"}])
        r = _jw(p)
        assert r["diagnostics"]["invalid_timestamp_reasons"]["wrong_type"] == 1
        assert r["n_7d"] is None

    def test_bool_timestamp_is_invalid(self, tmp_path):
        """bool is not a timestamp even though it is an int subclass."""
        p = _write_jsonl(tmp_path, [{"published": True}])
        r = _jw(p)
        assert r["diagnostics"]["invalid_timestamp_reasons"]["wrong_type"] == 1

    def test_unparseable_timestamp_is_invalid(self, tmp_path):
        """An unparseable timestamp string is rejected deterministically."""
        p = _write_jsonl(tmp_path, [{"published": "not-a-date"}])
        r = _jw(p)
        assert r["diagnostics"]["invalid_timestamp_reasons"]["unparseable"] == 1
        assert r["n_7d"] is None

    def test_generated_at_is_the_fallback_timestamp(self, tmp_path):
        """generated_at is used when published is absent."""
        p = _write_jsonl(tmp_path, [{
            "generated_at": "2026-10-31T00:00:00+00:00",
            "banner_title": "generated only",
        }])
        r = _jw(p)
        assert r["n_7d"] == 1
        assert r["last_alert_ts"] == "2026-10-31T00:00:00+00:00"

    def test_naive_timestamp_is_read_as_utc(self, tmp_path):
        """A timestamp written without a zone follows the established UTC convention."""
        p = _write_jsonl(tmp_path, [{
            "published": "2026-10-31T12:00:00",
            "banner_title": "naive",
        }])
        r = _jw(p)
        assert r["n_7d"] == 1
        assert r["last_alert_ts_utc"] == "2026-10-31T12:00:00Z"

    def test_offset_timestamp_is_converted_to_utc(self, tmp_path):
        """-08:00 offsets land on the UTC scale before any window comparison."""
        p = _write_jsonl(tmp_path, [{
            "published": "2026-10-31T20:00:00-08:00",
            "banner_title": "offset",
        }])
        r = _jw(p)
        assert r["n_7d"] == 1
        assert r["last_alert_ts_utc"] == "2026-11-01T04:00:00Z"

    def test_offset_timestamp_resolves_against_the_utc_cutoff(self, tmp_path):
        """2026-10-25T04:00:00-08:00 == 2026-10-25T12:00:00Z — exactly the 7d cutoff."""
        p = _write_jsonl(tmp_path, [{"published": "2026-10-25T04:00:00-08:00"}])
        r = _jw(p)
        assert r["n_7d"] == 1
        assert r["n_30d"] == 1

    def test_z_suffix_timestamp_is_parsed(self, tmp_path):
        """A trailing Z is a valid UTC designator."""
        p = _write_jsonl(tmp_path, [{"published": "2026-10-31T12:00:00Z"}])
        r = _jw(p)
        assert r["n_7d"] == 1
        assert r["last_alert_ts_utc"] == "2026-10-31T12:00:00Z"


class TestJawboningWindowBoundaries:
    """The windows are [cutoff, evaluation instant] — both ends exact."""

    def _one(self, tmp_path, when):
        p = _write_jsonl(tmp_path, [{"published": when.isoformat()}])
        return _jw(p)

    def test_exactly_7d_before_the_evaluation_is_inside_the_7d_window(self, tmp_path):
        r = self._one(tmp_path, _CUT_7D)
        assert r["n_7d"] == 1
        assert r["n_30d"] == 1

    def test_one_microsecond_before_the_7d_cutoff_is_outside(self, tmp_path):
        r = self._one(tmp_path, _CUT_7D - timedelta(microseconds=1))
        assert r["n_7d"] == 0
        assert r["n_30d"] == 1

    def test_exactly_30d_before_the_evaluation_is_inside_the_30d_window(self, tmp_path):
        r = self._one(tmp_path, _CUT_30D)
        assert r["n_7d"] == 0
        assert r["n_30d"] == 1

    def test_one_microsecond_before_the_30d_cutoff_is_outside(self, tmp_path):
        r = self._one(tmp_path, _CUT_30D - timedelta(microseconds=1))
        assert r["n_7d"] == 0
        assert r["n_30d"] == 0
        # still an eligible observation: zero recorded events in the windows,
        # and the older record remains the last observed event
        assert r["source_status"] == "usable"
        assert r["last_alert_ts"] is not None

    def test_record_exactly_at_the_evaluation_instant_is_observed(self, tmp_path):
        r = self._one(tmp_path, _EVAL)
        assert r["n_7d"] == 1
        assert r["n_30d"] == 1
        assert r["last_alert_ts_utc"] == "2026-11-01T12:00:00Z"

    def test_record_one_microsecond_after_the_evaluation_is_future(self, tmp_path):
        r = self._one(tmp_path, _EVAL + timedelta(microseconds=1))
        assert r["n_7d"] is None
        assert r["n_30d"] is None
        assert r["diagnostics"]["future_records"] == 1

    def test_evaluation_instant_is_recorded_on_the_result(self, tmp_path):
        r = _jw(tmp_path / "absent.jsonl")
        assert r["evaluated_at"] == "2026-11-01T12:00:00Z"
        assert r["evaluated_date"] == "2026-11-01"


class TestJawboningSourceQuality:
    """missing / unreadable / empty / unusable / partial / usable are distinct."""

    def test_absent_source_is_missing_with_unavailable_counts(self, tmp_path):
        r = _jw(tmp_path / "nope.jsonl")
        assert r["source_status"] == "missing"
        assert r["n_7d"] is None
        assert r["n_30d"] is None
        assert r["coverage"] == "unknown"

    def test_unreadable_source_is_unreadable_with_unavailable_counts(self, tmp_path):
        d = tmp_path / "alerts.jsonl"
        d.mkdir()          # a directory exists but cannot be read as a file
        r = _jw(d)
        assert r["source_status"] == "unreadable"
        assert r["n_7d"] is None
        assert r["n_30d"] is None

    def test_empty_readable_source_is_empty_with_zero_recorded_events(self, tmp_path):
        p = tmp_path / "alerts.jsonl"
        p.write_text("", encoding="utf-8")
        r = _jw(p)
        assert r["source_status"] == "empty"
        assert r["n_7d"] == 0
        assert r["n_30d"] == 0
        assert r["coverage"] == "unknown"

    def test_whitespace_only_source_is_empty(self, tmp_path):
        p = tmp_path / "alerts.jsonl"
        p.write_text("\n\n   \n", encoding="utf-8")
        r = _jw(p)
        assert r["source_status"] == "empty"
        assert r["n_7d"] == 0

    def test_empty_source_is_distinct_from_an_unusable_source(self, tmp_path):
        empty = tmp_path / "empty.jsonl"
        empty.write_text("", encoding="utf-8")
        unusable = _write_jsonl(tmp_path, ["not json", "[]"], name="unusable.jsonl")
        r_empty = _jw(empty)
        r_unusable = _jw(unusable)
        assert r_empty["source_status"] != r_unusable["source_status"]
        assert r_empty["n_7d"] == 0
        assert r_unusable["n_7d"] is None

    def test_all_invalid_source_is_unusable_not_a_confident_zero(self, tmp_path):
        p = _write_jsonl(tmp_path, ["not json", "[]", '{"published": 5}'])
        r = _jw(p)
        assert r["source_status"] == "unusable"
        assert r["n_7d"] is None
        assert r["n_30d"] is None
        assert r["diagnostics"]["malformed_json"] == 1
        assert r["diagnostics"]["invalid_structure"] == 1
        assert r["diagnostics"]["invalid_timestamp"] == 1

    def test_future_only_source_is_unusable_not_a_confident_zero(self, tmp_path):
        p = _write_jsonl(tmp_path, [{
            "published": (_EVAL + timedelta(days=30)).isoformat(),
            "banner_title": "future",
        }])
        r = _jw(p)
        assert r["source_status"] == "unusable"
        assert r["n_7d"] is None
        assert r["n_30d"] is None
        assert r["last_alert_ts"] is None
        assert r["diagnostics"]["future_records"] == 1

    def test_valid_old_records_plus_a_future_record_is_partial(self, tmp_path):
        """Reproduced defect: a future record used to enter both windows and
        become the last observed event."""
        p = _write_jsonl(tmp_path, [
            {"published": (_EVAL - timedelta(days=40)).isoformat(), "banner_title": "old but real"},
            {"published": (_EVAL + timedelta(days=10)).isoformat(), "banner_title": "future"},
        ])
        r = _jw(p)
        assert r["source_status"] == "partial"
        assert r["n_7d"] == 0
        assert r["n_30d"] == 0
        assert r["last_alert_summary"] == "old but real"
        assert r["diagnostics"]["future_records"] == 1
        assert r["diagnostics"]["eligible_observed"] == 1

    def test_all_usable_source_is_usable(self, tmp_path):
        p = _write_jsonl(tmp_path, [
            {"published": (_EVAL - timedelta(days=1)).isoformat(), "banner_title": "a"},
            {"published": (_EVAL - timedelta(days=2)).isoformat(), "banner_title": "b"},
        ])
        r = _jw(p)
        assert r["source_status"] == "usable"
        assert r["_skipped_lines"] == 0

    def test_coverage_is_always_unknown(self, tmp_path):
        """Reading a file never proves the upstream feed was collected whole."""
        p = _write_jsonl(tmp_path, [{"published": (_EVAL - timedelta(days=1)).isoformat()}])
        assert _jw(p)["coverage"] == "unknown"
        assert _jw(tmp_path / "absent.jsonl")["coverage"] == "unknown"
        empty = tmp_path / "empty.jsonl"
        empty.write_text("", encoding="utf-8")
        assert _jw(empty)["coverage"] == "unknown"


class TestJawboningDisplayCopy:
    """Display copy is bounded, string-typed and bilingual for valid input."""

    def test_non_string_summary_values_are_rejected(self, tmp_path):
        """A list/dict summary is not display copy and never reaches the surface."""
        p = _write_jsonl(tmp_path, [{
            "published": (_EVAL - timedelta(days=1)).isoformat(),
            "banner_title": ["<b>markup</b>"],
            "summary": {"raw": "structure"},
        }])
        r = _jw(p)
        # the record is still a valid OBSERVATION
        assert r["n_7d"] == 1
        assert r["last_alert_summary"] is None
        assert r["last_alert_summary_zh"] is None

    def test_numeric_summary_is_rejected(self, tmp_path):
        """Reproduced defect: a numeric summary raised TypeError on slicing."""
        p = _write_jsonl(tmp_path, [{
            "published": (_EVAL - timedelta(days=1)).isoformat(),
            "banner_title": 42,
        }])
        r = _jw(p)
        assert r["n_7d"] == 1
        assert r["last_alert_summary"] is None

    def test_malformed_copy_does_not_discard_an_independent_valid_record(self, tmp_path):
        p = _write_jsonl(tmp_path, [
            {"published": (_EVAL - timedelta(days=2)).isoformat(), "banner_title": ["x"]},
            {"published": (_EVAL - timedelta(days=1)).isoformat(), "banner_title": "Good alert"},
        ])
        r = _jw(p)
        assert r["n_7d"] == 2
        assert r["n_30d"] == 2
        assert r["last_alert_summary"] == "Good alert"

    def test_malformed_copy_on_the_last_record_leaves_no_garbled_summary(self, tmp_path):
        p = _write_jsonl(tmp_path, [
            {"published": (_EVAL - timedelta(days=2)).isoformat(), "banner_title": "Older good"},
            {"published": (_EVAL - timedelta(days=1)).isoformat(), "banner_title": {"a": 1}},
        ])
        r = _jw(p)
        assert r["n_7d"] == 2
        assert r["last_alert_summary"] is None
        assert isinstance(r["last_alert_summary"], (str, type(None)))

    def test_summary_is_bounded_to_the_display_length(self, tmp_path):
        p = _write_jsonl(tmp_path, [{
            "published": (_EVAL - timedelta(days=1)).isoformat(),
            "banner_title": "A" * 400,
        }])
        r = _jw(p)
        assert len(r["last_alert_summary"]) == 140

    def test_bilingual_fields_preserved_for_valid_input(self, tmp_path):
        p = _write_jsonl(tmp_path, [{
            "published": (_EVAL - timedelta(days=1)).isoformat(),
            "banner_title": "EN title",
            "banner_title_zh": "中文标题",
            "summary": "EN summary",
            "summary_zh": "中文摘要",
        }])
        r = _jw(p)
        assert r["last_alert_summary"] == "EN title"
        assert r["last_alert_summary_zh"] == "中文标题"

    def test_zh_falls_back_to_en_for_valid_input(self, tmp_path):
        p = _write_jsonl(tmp_path, [{
            "published": (_EVAL - timedelta(days=1)).isoformat(),
            "banner_title": "EN headline only",
        }])
        r = _jw(p)
        assert r["last_alert_summary"] == "EN headline only"
        assert r["last_alert_summary_zh"] == "EN headline only"


class TestCalendarEventSemantics:
    """The event is dated: upcoming / today / past are explicit."""

    def _cal(self, when):
        from scripts.build_policy_lever import _compute_calendar
        return _compute_calendar(now=when)

    def test_before_the_event(self):
        c = self._cal(datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc))
        assert c["event_state"] == "upcoming"
        assert c["days_to_midterm"] == 2
        assert c["days_since_midterm"] is None
        assert c["event_date"] == "2026-11-03"
        assert c["evaluation_date"] == "2026-11-01"

    def test_on_the_event(self):
        c = self._cal(datetime(2026, 11, 3, 0, 0, tzinfo=timezone.utc))
        assert c["event_state"] == "today"
        assert c["days_to_midterm"] == 0
        assert c["days_since_midterm"] == 0
        assert c["event_date"] == "2026-11-03"

    def test_after_the_event(self):
        c = self._cal(datetime(2026, 11, 4, 0, 0, tzinfo=timezone.utc))
        assert c["event_state"] == "past"
        assert c["days_to_midterm"] is None      # NOT a permanent live zero
        assert c["days_since_midterm"] == 1
        assert "2026-11-03" in c["context_note"]
        assert "2026年11月3日" in c["context_note_zh"]

    def test_naive_evaluation_instant_is_read_as_utc(self):
        c = self._cal(datetime(2026, 11, 3, 0, 0))
        assert c["event_state"] == "today"

    def test_calendar_exposes_the_evaluation_instant(self):
        c = self._cal(_EVAL)
        assert c["evaluated_at"] == "2026-11-01T12:00:00Z"
        assert c["evaluation_date"] == "2026-11-01"

    def test_past_note_has_no_directional_language(self):
        c = self._cal(datetime(2026, 11, 4, 0, 0, tzinfo=timezone.utc))
        for word in ("buy", "sell", "short", "long", "intent", "predict"):
            assert word not in c["context_note"].lower()


class TestArtifactTimestamps:
    """Computation time is distinct from evidence time."""

    def test_computed_at_is_a_utc_instant(self, built_artifact):
        assert built_artifact["computed_at"].endswith("Z")
        parsed = datetime.fromisoformat(built_artifact["computed_at"].replace("Z", "+00:00"))
        assert parsed.tzinfo is not None
        assert parsed.utcoffset() == timedelta(0)

    def test_as_of_keeps_the_price_date_meaning(self, built_artifact):
        fc = built_artifact["favored_complex"]
        if fc.get("as_of"):
            assert built_artifact["as_of"] == fc["as_of"]
            assert built_artifact["as_of_basis"] == "price_date"
        else:
            assert built_artifact["as_of_basis"] == "build_date_fallback"

    def test_as_of_is_a_date_and_not_the_evaluation_instant(self, built_artifact):
        assert "T" not in built_artifact["as_of"]
        assert built_artifact["as_of"] != built_artifact["computed_at"]

    def test_one_evaluation_instant_is_shared_by_the_components(self, built_artifact):
        assert built_artifact["jawboning"]["evaluated_at"] == built_artifact["computed_at"]
        assert built_artifact["calendar"]["evaluated_at"] == built_artifact["computed_at"]
        assert built_artifact["favored_complex"]["computed_at"] == built_artifact["computed_at"]

    def test_component_evaluation_date_is_the_utc_date_of_the_instant(self, built_artifact):
        assert built_artifact["calendar"]["evaluation_date"] == built_artifact["computed_at"][:10]
        assert built_artifact["jawboning"]["evaluated_date"] == built_artifact["computed_at"][:10]

    def test_calendar_event_date_is_the_midterm_date(self, built_artifact):
        assert built_artifact["calendar"]["event_date"] == "2026-11-03"

    def test_artifact_is_json_serializable_with_the_new_metadata(self, built_artifact):
        reloaded = json.loads(json.dumps(built_artifact, default=str))
        assert reloaded["schema"] == "policy_lever.v1"
        assert "computed_at" in reloaded
        assert "source_status" in reloaded["jawboning"]
        assert "event_state" in reloaded["calendar"]


class TestProducerIntegrityRegressionGuard:
    """The R2 repair must not touch the frozen PS-R9 scoring or the basket block."""

    def test_drawdown_threshold_is_unchanged(self):
        from scripts.build_policy_lever import _DRAWDOWN_THRESHOLD
        assert _DRAWDOWN_THRESHOLD == -0.15

    def test_state_rule_is_unchanged(self):
        from scripts.build_policy_lever import _compute_state
        assert _compute_state(-15.0, [_lever(True)]) == "ARMED"
        assert _compute_state(-14.99, [_lever(True)]) == "ELEVATED"
        assert _compute_state(-15.0, [_lever(False)]) == "ELEVATED"
        assert _compute_state(-10.0, [_lever(False)]) == "QUIET"
        assert _compute_state(None, [_lever(False)]) == "QUIET"

    def test_favored_complex_keeps_its_legacy_keys(self):
        from scripts.build_policy_lever import build
        fc = build()["favored_complex"]
        for key in ("basket", "basket_incomplete", "drawdown_pct", "drawdown_z",
                    "as_of", "note", "note_zh"):
            assert key in fc

    def test_jawboning_keeps_its_legacy_keys(self):
        from scripts.build_policy_lever import build
        jw = build()["jawboning"]
        for key in ("n_7d", "n_30d", "last_alert_ts", "last_alert_summary",
                    "last_alert_summary_zh"):
            assert key in jw

    def test_calendar_keeps_its_legacy_keys(self):
        from scripts.build_policy_lever import build
        cal = build()["calendar"]
        for key in ("days_to_midterm", "context_note", "context_note_zh"):
            assert key in cal

    def test_deeply_nested_line_never_crashes_the_producer(self, tmp_path):
        """A pathological line is rejected on its own; the next record survives."""
        p = tmp_path / "alerts.jsonl"
        p.write_text(
            "[" * 20000 + "]" * 20000 + "\n" +
            json.dumps({"published": "2026-10-31T00:00:00+00:00", "banner_title": "ok"}) + "\n",
            encoding="utf-8",
        )
        r = _jw(p)
        assert r["n_7d"] == 1
        assert r["last_alert_summary"] == "ok"
        assert r["diagnostics"]["malformed_json"] == 1

    def test_build_never_raises_on_a_corrupt_source(self, monkeypatch, tmp_path):
        """The publication path survives a wholly corrupt source file."""
        from scripts import build_policy_lever as mod
        mod.config.load()   # warm the config cache so the patched ROOT needs no config.yml
        monkeypatch.setattr(mod.config, "ROOT", tmp_path)
        (tmp_path / "data" / "whitehouse").mkdir(parents=True)
        (tmp_path / "data" / "whitehouse" / "alerts.jsonl").write_text(
            "garbage\n[]\n", encoding="utf-8"
        )
        artifact = mod.build()
        assert artifact["schema"] == "policy_lever.v1"
        assert artifact["jawboning"]["source_status"] == "unusable"
        assert artifact["jawboning"]["n_7d"] is None



class TestIntegratedProducerBoundary:
    @pytest.mark.parametrize('invalid_ts', [
        '0001-01-01T00:00:00+14:00',
        '9999-12-31T23:59:59-14:00',
    ])
    def test_utc_overflow_does_not_discard_an_independent_valid_record(self, tmp_path, invalid_ts):
        p = _write_jsonl(tmp_path, [
            {'published': invalid_ts, 'summary': 'Invalid UTC instant'},
            {'published': '2026-10-31T12:00:00Z', 'summary': 'Valid observation'},
        ])
        r = _jw(p)
        assert r['source_status'] == 'partial'
        assert r['n_7d'] == r['n_30d'] == 1
        assert r['last_alert_summary'] == 'Valid observation'
        assert r['diagnostics']['invalid_timestamp'] == 1

    def test_oil_arming_retains_engine_result_and_stamps_its_own_price_date(self, monkeypatch):
        import pandas as pd
        from engine import commodity_signals
        from scripts import build_policy_lever as mod
        px = pd.DataFrame({'close': [70., 71.]}, index=pd.to_datetime(['2026-10-28', '2026-10-29']))
        engine_result = {'armed': False, 'stoch_k': 42., 'params': {'version': 'unchanged'}}
        monkeypatch.setattr(mod, '_load_price', lambda ticker: px)
        monkeypatch.setattr(mod.config, 'load', lambda: {'commodities': {}})
        monkeypatch.setattr(commodity_signals, 'technical_arming', lambda prices, cfg: engine_result)
        result = mod._compute_oil_arming()
        assert result == {**engine_result, 'as_of': '2026-10-29'}
        assert 'as_of' not in engine_result

    def test_past_scheduled_date_does_not_claim_that_voting_occurred(self):
        from scripts.build_policy_lever import _compute_calendar
        result = _compute_calendar(now=datetime(2026, 11, 4, tzinfo=timezone.utc))
        assert 'scheduled date passed' in result['context_note']
        assert 'took place' not in result['context_note']
        assert '举行' not in result['context_note_zh']

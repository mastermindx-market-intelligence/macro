"""Owner-vocabulary positive controls for regime_context.

Round 3 closes a hardening regression where the round-2 _choice lists were
broader than the producers emit. This file pins the contract: for every
choice/slug field whose producer the round-1 review enumerated, the value set
must match the producer exactly (caller side), and the shipped fixture must
yield every owner row `available` with ZERO `unrecognized_owner_value:*`
issues and no `partial input` in the rendered REGIME DETAIL block.

(a) fixture-census positive control: every owner row `available`, no
    `unrecognized_owner_value:*` issues, no `partial input` suffix.
(b) producer-set positive control: for every choice/slug field, every value
    the producer can emit is accepted.
"""
from __future__ import annotations

import json
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from engine.neuralweb import market_packet as mp
from engine.neuralweb import regime_context as rc

NOW = datetime(2026, 10, 1, 23, 0, tzinfo=timezone.utc)

# Mirrors the fixture payload from tests/test_regime_context.py so this file
# stands alone if imported in isolation.
def _iso(dt):
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))


def _fixture_sources():
    """Minimal fixture where every producer field takes a value the round-3
    _choice/_slug lists are verified to accept. Quoted producers in comments.
    """
    regime = {
        "date": "2026-10-01",
        "freshness": {"stale": False},
        "quad": "Q1",
        "regime_one": {
            "tape": {"quad": "Q1"},
            "macro": {
                "quad": "Q1",
                # engine/regime_one.py:130 _freshness_state: fresh
                "worst_freshness": "fresh",
            },
        },
        "quad_vector": {
            "asof": _iso(NOW),
            "stale": False,
            "p": {"Q1": 0.55, "Q2": 0.20, "Q3": 0.15, "Q4": 0.10},
            "transition_momentum": {"gaining": "Q1", "losing": "Q4",
                                    "window_sessions": 5},
        },
        # engine/transition.py:235 : STABLE
        "transition_state": "STABLE",
        # engine/regime.py:227 : benign-expansion
        "liquidity_quality": {
            "asof": _iso(NOW), "stale": False,
            "label": "benign-expansion",
            "quantity_roc_bn": 12.3, "rrp_buffer_bn": 540.0,
            "stress_overlay": {
                # engine/regime.py:200 : tightening
                "nfci_trend": "tightening",
                "hy_oas_pct": 3.4, "hy_oas_chg_20d": -0.1, "nfci": -0.3,
            },
        },
        "liquidity_overlay": "neutral",
        "growth_score": 0.3, "inflation_score": 0.1,
        "theme_revisions": {
            "asof": "2026-10-01", "stale": False, "n_themes": 1,
            "themes": {
                # engine/theme_revisions.py:126 _accel_state: RISING
                "ai_semiconductors": {
                    "breadth": 0.42, "breadth_accel": 0.05,
                    "basis_days": 21, "est_drift_90d": 1.4,
                    "n_covered": 8, "n_members": 10, "coverage": 0.8,
                    "broadening_state": "RISING",
                },
            },
        },
    }
    transmission = {
        "asof": _iso(NOW), "stale": False,
        "state": {"rates": {
            "real_10y": 1.92, "real_10y_chg_22d_bp": -8.0,
            "real_10y_chg_63d_bp": -15.0, "real_10y_pctile": 0.41,
            "direction": "falling",
            # engine/rate_inflation_transmission.py:228 : neutral
            "regime": "neutral",
        }},
        "yield_momentum": {"series": {"10y": {
            "as_of": "2026-10-01", "status": "available",
            "path_qualified": True, "level": 4.32,
            "velocity_bp": {"5d": 3.0, "22d": -7.0, "63d": -12.0},
            "acceleration_bp": 1.0,
            # engine/yield_momentum.py:200 : fixed_weekday_grid_intervals
            "horizon_basis": "fixed_weekday_grid_intervals",
        }}},
    }
    participation = {
        "as_of": "2026-10-01", "stale": False, "young": False,
        "latest": {"ai_pct50": 70.0, "nonai_pct50": 52.0, "spread_50": 18.0,
                   "ai_pct200": 62.0, "nonai_pct200": 48.0},
        "cohort_sizes": {"ai_total": 30, "non_ai": 240, "universe": 270},
        # writer: scripts/build_ai_adjacency_tag.py:141-156 emits
        # f"finviz:<fv_asof>|membership:<mb_ver>" — this is the literal value
        # committed in data/breadth/ticker_ai_tag.version.
        "tag_version": "finviz:2026-06-27|membership:2026-08-07",
    }
    dispersion = {
        "as_of": "2026-10-01", "stale": False,
        "dispersion_pctile": 0.61, "avg_corr": -0.4,
    }
    options = {"chips": [
        {"key": "vix_level", "last_date": "2026-10-01",
         "value": 18.5, "pctile": 42.0, "freshness": "fresh"},
        {"key": "dspx", "last_date": "2026-10-01",
         "value": 4.2, "pctile": 55.0, "freshness": "fresh"},
        {"key": "cor1m", "last_date": "2026-10-01",
         "value": 65.0, "pctile": 48.0, "freshness": "fresh"},
        {"key": "cor3m", "last_date": "2026-10-01",
         "value": 60.0, "pctile": 50.0, "freshness": "fresh"},
    ]}
    world_state = {"factor_weather": {
        "factor_state_as_of": "2026-10-01", "stale": False,
        # scripts/build_factor_panel.py:403 : growth_momentum
        "style_regime": "growth_momentum",
        # engine/factor_series.py:38 SERIES_FACTORS : profitability
        "factor_leader": "profitability",
        "ratio_qqq_spy_20d": 0.041, "ratio_iwm_spy_20d": 0.012,
    }}
    leadership = {
        "asof": "2026-10-01", "stale": False,
        # engine/leadership_crack.py:237 + _state_machine: INTACT
        "state": "INTACT",
        # engine/leadership_crack.py:378 : tracked_ai_hardware_damage_monitor
        "cohort_role": "tracked_ai_hardware_damage_monitor",
        "high_window_sessions": 20,
        "med_dd": -0.05, "index_dd": -0.02,
        "n_fresh": 25, "n_total": 30,
        "state_since": "2026-09-15",
    }
    return {
        "regime": regime, "transmission": transmission,
        "participation": participation, "dispersion": dispersion,
        "options": options, "world_state": world_state,
        "leadership": leadership,
    }


def _populate_root() -> Path:
    """Write fixture sources to a tempdir like the other entitled-block tests."""
    src = _fixture_sources()
    paths = {
        "regime": ("data/regime/latest.json", src["regime"]),
        "transmission": ("data/transmission/latest.json", src["transmission"]),
        "participation": ("site/basketdata/breadth_split.json", src["participation"]),
        "options": ("site/basketdata/vol_weather.json", src["options"]),
        "dispersion": ("data/dispersion/regime.json", src["dispersion"]),
        "world_state": ("data/neuralweb/world_state.json", src["world_state"]),
        "leadership": ("data/leadership_crack/latest.json", src["leadership"]),
    }
    td = tempfile.mkdtemp()
    root = Path(td)
    for rel, payload in paths.values():
        _write(root / rel, payload)
    return root


# ---------------------------------------------------------------------------
# (a) fixture-census positive control
# ---------------------------------------------------------------------------

def test_fixture_cleans_all_owner_rows():
    """Every owner row available, no `unrecognized_owner_value:*` issues,
    no `partial input` suffix in the REGIME DETAIL block. Composed
    participation membership_version equals the literal the fixture sets."""
    ctx = rc.compose_context(_fixture_sources(), now=NOW)
    unrecognized = []
    for name, dim in ctx["dimensions"].items():
        if dim["status"] != "available":
            unrecognized.append((name, dim["status"], list(dim.get("issues", []))))
        for issue in dim.get("issues", []):
            if isinstance(issue, str) and issue.startswith("unrecognized_owner_value:"):
                unrecognized.append((name, "unrecognized", issue))
    assert not unrecognized, f"round-3 regression: {unrecognized}"

    assert ctx["dimensions"]["participation"]["values"]["membership_version"] == \
        "finviz:2026-06-27|membership:2026-08-07", \
        "participation membership_version must equal the literal fixture value"

    rendered = rc.render_context(ctx)
    assert "partial input" not in rendered, \
        "rendered REGIME DETAIL block must not carry the partial-input suffix when fixture is clean"


# ---------------------------------------------------------------------------
# membership_version: producer-format positive control, empty-absent contract,
# and rejection contract. The producer is engine/breadth_split.py:232-239,280;
# the writer is scripts/build_ai_adjacency_tag.py:141-156
# `_source_fingerprint()`.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", [
    # The literal value committed in data/breadth/ticker_ai_tag.version.
    "finviz:2026-06-27|membership:2026-08-07",
    # An earlier committed value with a different date.
    "finviz:2026-06-27|membership:2026-07-03",
    # Writer output when the finviz source is missing (empty date half).
    "finviz:|membership:2026-08-07",
])
def test_membership_version_accepts_producer_format(value):
    """Every value the writer at scripts/build_ai_adjacency_tag.py:141-156
    and the producer at engine/breadth_split.py:232-239,280 can emit must be
    accepted with ZERO issues."""
    issues: list[str] = []
    assert rc._membership_version(value, issues=issues) == value, \
        f"membership_version value {value!r} must be accepted"
    assert issues == [], \
        f"membership_version value {value!r} must not append any issue (got {issues!r})"


def test_membership_version_empty_is_absent_not_unrecognized():
    """Empty / None is ABSENT, not an unrecognized value: no issue appended."""
    # Direct call.
    for v in ("", None):
        issues: list[str] = []
        assert rc._membership_version(v, issues=issues) is None, \
            f"empty/None membership_version {v!r} must return None (absent)"
        assert issues == [], \
            f"empty/None membership_version {v!r} must not append any issue (got {issues!r})"
    # Through compose_context: mirror tests/test_regime_context.py:272 by setting
    # the participation input's `tag_version` to "" and confirm the composed
    # dimension carries no `unrecognized_owner_value:membership_version` issue.
    sources = _fixture_sources()
    sources["participation"]["tag_version"] = ""
    ctx = rc.compose_context(sources, now=NOW)
    membership_issues = ctx["dimensions"]["participation"].get("issues", []) or []
    assert "unrecognized_owner_value:membership_version" not in membership_issues, \
        f"empty tag_version must not surface as unrecognized_owner_value (issues={membership_issues!r})"


@pytest.mark.parametrize("value", [
    "garbage value!",
    "FINVIZ:2026-06-27",
    "finviz:26-06-27",
    "fixture-membership",
    "v2026-10-01",
    "finviz:2026-06-27|",
    "|".join(["finviz:2026-06-27"] * 8),  # 8*17+7 = 143 chars, over _MEMBERSHIP_VERSION_MAX
])
def test_membership_version_rejects_garbage(value):
    """Anything outside the producer format must return None and append
    exactly `unrecognized_owner_value:membership_version`."""
    issues: list[str] = []
    assert rc._membership_version(value, issues=issues) is None, \
        f"garbage membership_version {value!r} must return None"
    assert issues == ["unrecognized_owner_value:membership_version"], \
        f"garbage membership_version {value!r} must append exactly one issue (got {issues!r})"


# ---------------------------------------------------------------------------
# (b) producer-set positive control: every emitted value the producer can
# produce for each closed _choice field must be accepted.
# ---------------------------------------------------------------------------

def test_broadening_state_accepts_every_emitted_value():
    """engine/theme_revisions.py:126-135 _accel_state + line 220/193 default."""
    emitted = {"FLAT_LOW", "RISING", "ROLLING", "MIXED", "INSUFFICIENT_HISTORY"}
    for v in emitted:
        assert rc._choice(v, ("FLAT_LOW", "RISING", "ROLLING", "MIXED",
                              "INSUFFICIENT_HISTORY")) == v, \
            f"broadening_state value {v!r} must be accepted"


def test_cohort_role_accepts_producer_literal():
    """engine/leadership_crack.py:378 emits one literal:
    'tracked_ai_hardware_damage_monitor'."""
    assert rc._choice(
        "tracked_ai_hardware_damage_monitor",
        ("tracked_ai_hardware_damage_monitor",),
    ) == "tracked_ai_hardware_damage_monitor"


def test_transition_state_accepts_every_emitted_value():
    """engine/transition.py:133,150,154,159,206,235 — STABLE, WEAKENING,
    TRANSITIONING, NEW_REGIME. Cross-checked against engine/alerts.py:42-45."""
    emitted = {"STABLE", "WEAKENING", "TRANSITIONING", "NEW_REGIME"}
    for v in emitted:
        assert rc._choice(v, emitted) == v, \
            f"transition_state value {v!r} must be accepted"


def test_owner_style_accepts_every_emitted_value():
    """scripts/build_factor_panel.py:403 + returns 'mixed' fallback at
    line 1311, 1366, 1374, 1423-1425, 1467, 1497."""
    emitted = {"growth_momentum", "quality_defense", "value_cyclical",
               "junk_rally", "mixed"}
    for v in emitted:
        assert rc._choice(v, ("growth_momentum", "quality_defense",
                              "value_cyclical", "junk_rally", "mixed")) == v, \
            f"owner_style value {v!r} must be accepted"


def test_factor_leader_accepts_every_emitted_value():
    """engine/factor_series.py:38 SERIES_FACTORS."""
    emitted = {"value", "profitability", "quality", "investment", "payout",
               "low_vol", "low_beta", "composite"}
    for v in emitted:
        assert rc._choice(v, ("value", "profitability", "quality",
                              "investment", "payout", "low_vol", "low_beta",
                              "composite")) == v, \
            f"factor_leader value {v!r} must be accepted"


def test_leadership_state_accepts_every_emitted_value():
    """engine/leadership_crack.py:237 + _state_machine loop at 244-291."""
    emitted = {"INTACT", "CRACKING", "BROKEN"}
    for v in emitted:
        assert rc._choice(v, ("INTACT", "CRACKING", "BROKEN")) == v, \
            f"leadership state value {v!r} must be accepted"


def test_economic_freshness_accepts_every_emitted_value():
    """engine/regime_one.py:130-140 _freshness_state."""
    emitted = {"fresh", "slow", "stale", "dead", "unknown"}
    for v in emitted:
        assert rc._choice(v, ("fresh", "slow", "stale", "dead", "unknown")) == v, \
            f"economic_freshness value {v!r} must be accepted"


def test_horizon_basis_accepts_producer_literal():
    """engine/yield_momentum.py:200."""
    assert rc._choice("fixed_weekday_grid_intervals",
                      ("fixed_weekday_grid_intervals",)) == "fixed_weekday_grid_intervals"


def test_nfci_direction_accepts_every_emitted_value():
    """engine/regime.py:200."""
    emitted = {"tightening", "loose"}
    for v in emitted:
        assert rc._choice(v, ("tightening", "loose")) == v


def test_rejected_value_yields_issues():
    """Negative control: an unknown producer value must surface an issue."""
    issues: list[str] = []
    out = rc._choice("UNKNOWN", ("FRESH", "STALE"),
                     issues=issues, field="test_field")
    assert out is None
    assert issues == ["unrecognized_owner_value:test_field"]
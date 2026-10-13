"""engine.foresight_cascade — the per-theme STAGE machine (T1 x T4). Verifies the stage
logic on the four canonical states and that it ranks by edge remaining (PRECIPICE first)
and degrades honestly when a tier is missing. W0a additions: _append_ledger logs ALL stages
with transition-dedup + heartbeat.
"""
from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone

import pytest
import pandas as pd

from engine import foresight_cascade as fc
from lib import config as _config


@pytest.fixture(autouse=True)
def _isolate_real_data_tree(tmp_path, monkeypatch):
    """compute_foresight_cascade lazily recomputes any tier not passed in
    (policy_reg, fda_scarcity, confirmers, ...) straight off the real data/
    tree — engine.policy_calendar._append_ledger then appends a real
    forward-ledger batch (COLLECT_LANE=nightly is armed session-wide in
    conftest; a full 13-theme batch landed in the committed ledger this way).
    Redirect lib.config so lazy recomputes see an empty store and degrade to
    None. Tests that patch data_dir themselves simply override this."""
    _config.load()  # warm the lru cache before ROOT is patched
    monkeypatch.setattr(_config, "ROOT", tmp_path)
    monkeypatch.setattr(_config, "data_dir", lambda: tmp_path / "data")


def test_precipice_tight_plus_flat():
    bn = {"band": "SOLD_OUT", "tightness": 1.6, "regime": True}
    rv = {"breadth": 0.05, "level_state": "FLAT_LOW"}
    stage, _ = fc._stage(bn, rv)
    assert stage == "PRECIPICE"          # the June-2024 HBM state


def test_broadening_tight_plus_rising():
    bn = {"band": "TIGHT", "tightness": 0.9, "regime": True}
    rv = {"breadth": 0.3, "level_state": "POSITIVE"}
    stage, _ = fc._stage(bn, rv)
    assert stage == "BROADENING"


def test_rerating_tight_but_already_broad():
    bn = {"band": "TIGHT", "tightness": 0.9}
    rv = {"breadth": 0.8, "level_state": "POSITIVE"}
    stage, _ = fc._stage(bn, rv)
    assert stage == "RE-RATING"          # runway maturing -> do not chase


def test_glut_risk_loose_but_estimates_high():
    bn = {"band": "LOOSE", "tightness": -0.6}
    rv = {"breadth": 0.4, "level_state": "POSITIVE"}
    stage, _ = fc._stage(bn, rv)
    assert stage == "GLUT-RISK"


def test_revisions_only_flags_lateness():
    stage, _ = fc._stage(None, {"breadth": 0.8, "level_state": "POSITIVE"})
    assert stage == "RE-RATING"
    stage2, _ = fc._stage(None, {"breadth": 0.02, "level_state": "FLAT_LOW"})
    assert stage2 == "WATCH"


def test_ranks_precipice_first():
    bottleneck = {"themes": {
        "a": {"name": "A", "band": "TIGHT", "tightness": 0.9, "regime": True},
        "b": {"name": "B", "band": "TIGHT", "tightness": 0.9},
    }}
    revisions = {"themes": {
        "a": {"name": "A", "breadth": 0.05, "level_state": "FLAT_LOW"},   # PRECIPICE
        "b": {"name": "B", "breadth": 0.8, "level_state": "POSITIVE"},    # RE-RATING
    }}
    out = fc.compute_foresight_cascade(bottleneck=bottleneck, revisions=revisions,
                                       demand={"themes": {}}, write_ledger=False)
    assert out["themes"][0]["theme"] == "a"
    assert out["themes"][0]["stage"] == "PRECIPICE"


def test_entry_overlay():
    # thesis stage + active dislocation -> entry window
    ready, _ = fc._entry("PRECIPICE", {"active": True, "verdict": "buyable_washout"})
    assert ready is True
    # thesis stage but calm market -> wait for the flush
    ready2, note2 = fc._entry("BROADENING", {"active": False, "verdict": "calm"})
    assert ready2 is False and "await" in note2.lower()
    # late stage never an entry, even on a flush
    ready3, _ = fc._entry("RE-RATING", {"active": True})
    assert ready3 is False


def test_demand_confirms_in_rationale():
    bottleneck = {"themes": {"a": {"name": "A", "band": "TIGHT", "tightness": 0.9, "regime": True}}}
    revisions = {"themes": {"a": {"name": "A", "breadth": 0.05, "level_state": "FLAT_LOW"}}}
    demand = {"themes": {"a": {"name": "A", "demand_band": "ACCELERATING",
                               "capex_yoy": 69.0, "strength": "direct"}}}
    out = fc.compute_foresight_cascade(bottleneck=bottleneck, revisions=revisions,
                                       demand=demand, glut={"themes": {}}, write_ledger=False)
    r = out["themes"][0]
    assert r["stage"] == "PRECIPICE"
    assert r["demand_band"] == "ACCELERATING"
    assert "capex" in r["rationale"].lower()


def test_guidance_confirms_without_changing_stage():
    # T3 guidance is a LEADING confirmer on the rationale + a score input, never a
    # stage-changer: a BROAD-RAISE on a PRECIPICE theme stays PRECIPICE but lifts the
    # acceleration axis and annotates the rationale.
    bottleneck = {"themes": {"a": {"name": "A", "band": "TIGHT", "tightness": 0.9, "regime": True}}}
    revisions = {"themes": {"a": {"name": "A", "breadth": 0.05, "level_state": "FLAT_LOW"}}}
    guidance = {"themes": {"a": {"name": "A", "guidance_band": "BROAD-RAISE",
                                 "n_raisers": 3, "n_cutters": 0, "net": 3}}}
    out = fc.compute_foresight_cascade(bottleneck=bottleneck, revisions=revisions,
                                       demand={"themes": {}}, glut={"themes": {}},
                                       guidance=guidance, write_ledger=False)
    r = out["themes"][0]
    assert r["stage"] == "PRECIPICE"
    assert r["guidance_band"] == "BROAD-RAISE"
    assert r["guidance_raisers"] == 3
    assert "pre-signaling" in r["rationale"]
    assert r["score_detail"]["axes"]["acceleration"] >= 0.5   # T3 raise lifts acceleration


def test_altdata_confirmers_inverse_to_breadth():
    # leading alt-data confirmers reinforce an EARLY (thesis-stage) theme's rationale + score,
    # but on a LATE (broad-revisions) theme they are crowding -> NOT added to the rationale.
    bn = {"themes": {"a": {"name": "A", "band": "TIGHT", "tightness": 0.9, "regime": True}}}
    conf = {"themes": {"a": {"name": "A", "n_leading": 2, "leading_members": ["MU", "WDC"],
                             "summary": "2 insider clusters · 1 gov-award accel"}}}
    early = fc.compute_foresight_cascade(
        bottleneck=bn, revisions={"themes": {"a": {"name": "A", "breadth": 0.05, "level_state": "FLAT_LOW"}}},
        demand={"themes": {}}, glut={"themes": {}}, guidance={"themes": {}}, confirmers=conf, write_ledger=False)
    r = early["themes"][0]
    assert r["stage"] == "PRECIPICE" and r["n_altdata_leading"] == 2
    assert "alt-data confirms" in r["rationale"]

    late = fc.compute_foresight_cascade(
        bottleneck=bn, revisions={"themes": {"a": {"name": "A", "breadth": 0.9, "level_state": "POSITIVE"}}},
        demand={"themes": {}}, glut={"themes": {}}, guidance={"themes": {}}, confirmers=conf, write_ledger=False)
    r2 = late["themes"][0]
    assert r2["stage"] == "RE-RATING"
    assert "alt-data confirms" not in r2["rationale"]              # crowding, not a tell, when broad
    assert r["score_detail"]["axes"]["acceleration"] > r2["score_detail"]["axes"]["acceleration"]


def test_glut_overrides_to_exit_risk():
    # a forming glut while estimates are still broad -> GLUT-RISK (exit clock) takes precedence
    bottleneck = {"themes": {"a": {"name": "A", "band": "TIGHT", "tightness": 0.9}}}
    revisions = {"themes": {"a": {"name": "A", "breadth": 0.8, "level_state": "POSITIVE"}}}
    glut = {"themes": {"a": {"name": "A", "band": "GLUT_FORMING", "glut_score": 0.8}}}
    out = fc.compute_foresight_cascade(bottleneck=bottleneck, revisions=revisions,
                                       demand={"themes": {}}, glut=glut, write_ledger=False)
    r = out["themes"][0]
    assert r["stage"] == "GLUT-RISK"
    assert r["glut_band"] == "GLUT_FORMING"
    assert "exit clock" in r["rationale"]


# ---- W0a: _append_ledger logs ALL stages with transition-dedup + heartbeat ----

def _make_payload(stages: dict[str, str], asof: str = "2026-07-01") -> dict:
    """Minimal payload for _append_ledger with given theme->stage mapping."""
    themes = []
    for theme, stage in stages.items():
        themes.append({
            "theme": theme, "stage": stage,
            "bottleneck_band": None, "revision_breadth": None,
        })
    return {"asof": asof, "themes": themes}


def test_all_stages_get_logged(monkeypatch, tmp_path):
    """_append_ledger must log ALL stages (not just PRECIPICE/BROADENING)."""
    import engine.foresight_cascade as fc_mod
    monkeypatch.setattr(fc_mod.config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(fc_mod.config, "load", lambda: {"themes": {
        "memory_storage": {"tickers": ["MU"]},
        "ai_semiconductors": {"tickers": ["NVDA"]},
        "copper_steel_electrify": {"tickers": ["FCX"]},
        "glp1_obesity": {"tickers": ["LLY"]},
    }})
    payload = _make_payload({
        "memory_storage": "PRECIPICE",
        "ai_semiconductors": "RE-RATING",
        "copper_steel_electrify": "WATCH",
        "glp1_obesity": "UNKNOWN",
    })
    (tmp_path / "foresight").mkdir(parents=True, exist_ok=True)
    fc_mod._append_ledger(payload)
    rows = [(tmp_path / "foresight" / "log.jsonl").read_text().splitlines()]
    logged = [json.loads(r) for r in rows[0] if r.strip()]
    stages_logged = {r["theme"]: r["stage"] for r in logged}
    assert stages_logged["memory_storage"] == "PRECIPICE"
    assert stages_logged["ai_semiconductors"] == "RE-RATING"
    assert stages_logged["copper_steel_electrify"] == "WATCH"
    assert stages_logged["glp1_obesity"] == "UNKNOWN"


def test_transition_dedup_logs_on_change_skips_same_stage(monkeypatch, tmp_path):
    """Log on stage transition; skip if same stage and within heartbeat window."""
    import engine.foresight_cascade as fc_mod
    monkeypatch.setattr(fc_mod.config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(fc_mod.config, "load",
                        lambda: {"themes": {"memory_storage": {"tickers": ["MU"]}}})
    (tmp_path / "foresight").mkdir(parents=True, exist_ok=True)

    # day 1: initial log (asof 2026-07-01) — stage WATCH
    fc_mod._append_ledger(_make_payload({"memory_storage": "WATCH"}, asof="2026-07-01"))
    # day 3: same stage, 2 days later — within heartbeat window → NOT logged again
    fc_mod._append_ledger(_make_payload({"memory_storage": "WATCH"}, asof="2026-07-03"))
    # day 5: stage changes to RE-RATING → logged (transition)
    fc_mod._append_ledger(_make_payload({"memory_storage": "RE-RATING"}, asof="2026-07-05"))

    lines = (tmp_path / "foresight" / "log.jsonl").read_text().splitlines()
    logged = [json.loads(r) for r in lines if r.strip()]
    assert len(logged) == 2   # day-1 WATCH + day-5 RE-RATING; day-3 same-stage skip
    assert logged[0]["stage"] == "WATCH" and logged[0]["asof"] == "2026-07-01"
    assert logged[1]["stage"] == "RE-RATING" and logged[1]["asof"] == "2026-07-05"


def test_heartbeat_logs_when_stage_unchanged_but_stale(monkeypatch, tmp_path):
    """Even with unchanged stage, log when >7 days since last logged row (heartbeat)."""
    import engine.foresight_cascade as fc_mod
    monkeypatch.setattr(fc_mod.config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(fc_mod.config, "load",
                        lambda: {"themes": {"memory_storage": {"tickers": ["MU"]}}})
    (tmp_path / "foresight").mkdir(parents=True, exist_ok=True)

    # day 1: WATCH logged
    fc_mod._append_ledger(_make_payload({"memory_storage": "WATCH"}, asof="2026-07-01"))
    # day 9: same stage WATCH but 8 days later → heartbeat fires → logged
    fc_mod._append_ledger(_make_payload({"memory_storage": "WATCH"}, asof="2026-07-09"))

    lines = (tmp_path / "foresight" / "log.jsonl").read_text().splitlines()
    logged = [json.loads(r) for r in lines if r.strip()]
    assert len(logged) == 2   # both logged: initial + heartbeat
    assert logged[0]["asof"] == "2026-07-01"
    assert logged[1]["asof"] == "2026-07-09"


def test_same_day_reruns_are_idempotent(monkeypatch, tmp_path):
    """Multiple runs on the same asof produce only one row per (theme, asof)."""
    import engine.foresight_cascade as fc_mod
    monkeypatch.setattr(fc_mod.config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(fc_mod.config, "load",
                        lambda: {"themes": {"memory_storage": {"tickers": ["MU"]}}})
    (tmp_path / "foresight").mkdir(parents=True, exist_ok=True)

    payload = _make_payload({"memory_storage": "PRECIPICE"}, asof="2026-07-01")
    fc_mod._append_ledger(payload)
    fc_mod._append_ledger(payload)  # re-run same day
    fc_mod._append_ledger(payload)  # and again

    lines = (tmp_path / "foresight" / "log.jsonl").read_text().splitlines()
    logged = [json.loads(r) for r in lines if r.strip()]
    assert len(logged) == 1   # exactly one row — idempotent


def test_pit_membership_snapshot_in_all_stage_rows(monkeypatch, tmp_path):
    """members[] is captured at log time for ALL stage rows (not only thesis stages)."""
    import engine.foresight_cascade as fc_mod
    monkeypatch.setattr(fc_mod.config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(fc_mod.config, "load",
                        lambda: {"themes": {"memory_storage": {"tickers": ["MU", "WDC"]}}})
    (tmp_path / "foresight").mkdir(parents=True, exist_ok=True)

    fc_mod._append_ledger(_make_payload({"memory_storage": "WATCH"}, asof="2026-07-01"))

    lines = (tmp_path / "foresight" / "log.jsonl").read_text().splitlines()
    logged = [json.loads(r) for r in lines if r.strip()]
    assert len(logged) == 1
    assert set(logged[0]["members"]) == {"MU", "WDC"}   # PIT snapshot present


# ---- W1a/b: text-grade PRECIPICE, text-only cap, negated exclusion, shadow log ----

def test_text_tight_flat_revisions_yields_precipice_text():
    """TIGHT (text) band + flat revisions → PRECIPICE (text), not PRECIPICE."""
    bn = {"band": "TIGHT (text)", "tightness": None, "regime": False, "text_only": True}
    rv = {"breadth": 0.04, "level_state": "FLAT_LOW"}
    stage, rationale = fc._stage(bn, rv)
    assert stage == "PRECIPICE (text)"
    assert "text-only" in rationale


def test_text_tight_rising_revisions_yields_broadening_text():
    """TIGHT (text) band + rising revisions → BROADENING (text)."""
    bn = {"band": "TIGHT (text)", "tightness": None, "regime": False, "text_only": True}
    rv = {"breadth": 0.25, "level_state": "POSITIVE"}
    stage, rationale = fc._stage(bn, rv)
    assert stage == "BROADENING (text)"
    assert "text-only" in rationale


def test_text_only_cap_binds_at_50(monkeypatch):
    """2 affirmative filers + flat revisions → PRECIPICE (text); text_only cap still at 50."""
    from engine import foresight_score as fs

    # A row that would score high physically but has text-only band
    row = {
        "stage": "PRECIPICE (text)",
        "bottleneck_band": "TIGHT (text)",
        "bottleneck_text_only": True,
        "tightness": None,
        "bottleneck_regime": False,
        "demand_band": "ACCELERATING",
        "capex_yoy": 69,
        "demand_strength": "direct",
        "revision_breadth": 0.04,
        "revision_level": "FLAT_LOW",
        "broadening_state": "FLAT_LOW",
        "est_drift_90d": 5,
        "glut_band": "STABLE",
        "entry_ready": False,
    }
    s = fs.score_row(row)
    assert s["physical_confirmed"] is False, "text-only must NOT count as physical confirmation"
    assert s["score"] <= 50.0, f"text-only cap must bind: got {s['score']}"
    assert any("text-only" in c for c in s["caps"])


def test_text_only_entry_not_ready():
    """Text thesis stages must never be entry-ready even with an active dislocation."""
    ready, note = fc._entry("PRECIPICE (text)", {"active": True, "verdict": "buyable_washout"})
    assert ready is False
    assert "text-only" in note or "awaiting" in note.lower()

    ready2, _ = fc._entry("BROADENING (text)", {"active": True, "verdict": "buyable_washout"})
    assert ready2 is False


def test_precipice_text_in_cascade(monkeypatch, tmp_path):
    """compute_foresight_cascade with a TIGHT (text) bn + flat rv → PRECIPICE (text)
    in the output, and bottleneck_text_only=True in the cascade row."""
    bottleneck = {"themes": {
        "glp1_obesity": {
            "name": "GLP-1", "band": "TIGHT (text)", "tightness": None,
            "regime": False, "text_only": True,
        }
    }}
    revisions = {"themes": {
        "glp1_obesity": {"name": "GLP-1", "breadth": 0.03, "level_state": "FLAT_LOW"},
    }}
    out = fc.compute_foresight_cascade(
        bottleneck=bottleneck, revisions=revisions,
        demand={"themes": {}}, glut={"themes": {}}, write_ledger=False,
    )
    assert out is not None
    r = out["themes"][0]
    assert r["stage"] == "PRECIPICE (text)"
    assert r["bottleneck_text_only"] is True
    # score must be capped at 50
    assert r["score"] <= 50.0


# ---- W2a (P1-A): percentile late-line tests ----------------------------------------

def _rv_themes_with_breadth(vals: dict[str, float]) -> dict:
    """Helper: build rv_themes dict from theme -> breadth mapping."""
    return {k: {"breadth": v, "level_state": "POSITIVE", "name": k}
            for k, v in vals.items()}


def _rv_themes_with_breadth_cov(vals: dict[str, float], cov_vals: dict[str, float]) -> dict:
    """Helper: build rv_themes dict with both breadth and breadth_cov."""
    out = {}
    for k, v in vals.items():
        out[k] = {"breadth": v, "level_state": "POSITIVE", "name": k}
        if k in cov_vals:
            out[k]["breadth_cov"] = cov_vals[k]
    return out


def test_percentile_lateline_85th_flags_broad_50th_does_not():
    """(c) Percentile late-line: a theme at the 85th percentile flags RE-RATING (broad);
    a theme at the 50th percentile does NOT — even when both are > 0.50 absolute."""
    # 10 themes with breadth_cov values spanning 0.1 to 1.0
    # 80th pctile of [0.1,0.2,...,1.0] = 0.82 (numpy.percentile computes linear interp)
    rv_themes = _rv_themes_with_breadth_cov(
        {f"t{i}": (i + 1) / 10 for i in range(10)},
        {f"t{i}": (i + 1) / 10 for i in range(10)},
    )
    threshold, basis = fc._compute_broad_hi_threshold(rv_themes)
    assert basis == "percentile_cov", f"expected percentile_cov, got {basis}"

    # t8 has breadth_cov=0.9 — above 80th pctile (~0.82) → broad
    bn_tight = {"band": "TIGHT", "tightness": 0.9}
    rv_t8 = {"breadth": 0.9, "breadth_cov": 0.9, "level_state": "POSITIVE"}
    stage_late, _ = fc._stage(bn_tight, rv_t8, broad_hi_threshold=threshold)
    assert stage_late == "RE-RATING", (
        f"theme at 85th pctile breadth_cov (0.9) should be RE-RATING, got {stage_late}"
    )

    # t4 has breadth_cov=0.5 — below 80th pctile (~0.82); also > 0.50 absolute cut
    # With percentile: NOT broad → BROADENING (tight band + positive revisions)
    rv_t4 = {"breadth": 0.5, "breadth_cov": 0.5, "level_state": "POSITIVE"}
    stage_early, _ = fc._stage(bn_tight, rv_t4, broad_hi_threshold=threshold)
    assert stage_early in ("BROADENING", "PRECIPICE"), (
        f"theme at 50th pctile breadth_cov (0.5) should not be RE-RATING, got {stage_early}"
    )
    # Specifically: with absolute BROAD_HI=0.50 this would be RE-RATING; with percentile it's not
    stage_absolute, _ = fc._stage(bn_tight, rv_t4, broad_hi_threshold=fc.BROAD_HI)
    # Verify the test premise: 0.5 > BROAD_HI (0.50) is false (equal, not >), so BROADENING
    # regardless. Use 0.51 to make the contrast clear:
    rv_just_over = {"breadth": 0.51, "breadth_cov": 0.51, "level_state": "POSITIVE"}
    stage_just_over_absolute, _ = fc._stage(bn_tight, rv_just_over, broad_hi_threshold=fc.BROAD_HI)
    stage_just_over_pctile, _ = fc._stage(bn_tight, rv_just_over, broad_hi_threshold=threshold)
    assert stage_just_over_absolute == "RE-RATING", (
        "0.51 > BROAD_HI=0.50 absolute → RE-RATING (test premise)"
    )
    assert stage_just_over_pctile != "RE-RATING", (
        "0.51 is at ~30th pctile — percentile threshold should NOT flag it as RE-RATING"
    )


def test_percentile_lateline_fewer_than_8_themes_uses_absolute_fallback():
    """(d) n_themes < _PCTILE_MIN_THEMES (8) → absolute fallback BROAD_HI constant."""
    # Only 5 themes — below the minimum for percentile to be meaningful
    rv_themes = _rv_themes_with_breadth_cov(
        {f"t{i}": 0.9 for i in range(5)},
        {f"t{i}": 0.9 for i in range(5)},
    )
    threshold, basis = fc._compute_broad_hi_threshold(rv_themes)
    assert basis == "absolute_fallback", (
        f"fewer than {fc._PCTILE_MIN_THEMES} themes should use absolute_fallback, got {basis}"
    )
    assert threshold == fc.BROAD_HI


def test_percentile_lateline_mixed_availability_uses_single_scale():
    """(e) Mixed breadth_cov availability: if fewer than half themes have breadth_cov,
    run the percentile on legacy breadth for ALL — never mix scales."""
    # 10 themes: only 3 have breadth_cov (fewer than half=5) → must use legacy breadth
    vals = {f"t{i}": (i + 1) / 10 for i in range(10)}
    cov_vals = {f"t{i}": (i + 1) / 10 for i in range(3)}    # only t0, t1, t2 have coverage
    rv_themes = _rv_themes_with_breadth_cov(vals, cov_vals)
    threshold, basis = fc._compute_broad_hi_threshold(rv_themes)
    assert basis == "percentile_legacy", (
        f"fewer than half themes have breadth_cov → must use legacy breadth, got basis={basis}"
    )
    # threshold should be the ~80th pctile of legacy breadth values [0.1..1.0]
    import numpy as np
    expected_threshold = float(np.percentile(list(vals.values()), fc._BROAD_HI_PCTILE))
    assert abs(threshold - expected_threshold) < 0.001


def test_percentile_lateline_surfaced_in_cascade_payload():
    """(c) late_line_basis and late_line_threshold surfaced in cascade payload."""
    # Build a cascade with >=8 themes so percentile fires
    rv_themes_dict = {f"theme_{i}": {"name": f"T{i}", "breadth": (i + 1) / 10,
                                      "level_state": "POSITIVE"}
                      for i in range(10)}
    out = fc.compute_foresight_cascade(
        bottleneck={"themes": {}},
        revisions={"themes": rv_themes_dict},
        demand={"themes": {}}, glut={"themes": {}}, write_ledger=False,
    )
    assert out is not None
    assert "late_line_basis" in out, "late_line_basis must be surfaced in cascade payload"
    assert out["late_line_basis"] in ("percentile_cov", "percentile_legacy", "absolute_fallback")
    assert "late_line_threshold" in out
    assert isinstance(out["late_line_threshold"], float)


def test_divergent_scales_cov_threshold_never_compared_to_legacy_breadth():
    """REVIEW F1/F2 REGRESSION: when the basis is percentile_cov, _stage must compare
    the theme's breadth_cov (same scale as the threshold), NEVER its legacy breadth.
    De-saturated fixture: legacy breadth saturated ~0.9, breadth_cov ~0.10-0.27. Before
    the fix, every theme's legacy 0.9 cleared the ~0.23 cov-scale threshold -> 12/12
    RE-RATING (the exact inversion of the de-saturation this wave ships)."""
    from engine.foresight_cascade import _compute_broad_hi_threshold, _stage
    vals = {f"t{i}": 0.90 for i in range(12)}                       # saturated legacy
    cov = {f"t{i}": 0.10 + 0.015 * i for i in range(12)}            # 0.10 .. 0.265
    rv_themes = _rv_themes_with_breadth_cov(vals, cov)
    thr, basis = _compute_broad_hi_threshold(rv_themes)
    assert basis == "percentile_cov"
    # mid-pack theme (t5, cov=0.175 < thr) must NOT flag RE-RATING despite legacy 0.9
    stage_mid, _ = _stage(None, rv_themes["t5"], None,
                          broad_hi_threshold=thr, late_line_basis=basis)
    assert stage_mid != "RE-RATING", (
        "cov-scale threshold was compared against legacy breadth — scale mixing")
    # top-of-distribution theme (t11, cov=0.265 > thr) SHOULD flag late
    stage_top, _ = _stage(None, rv_themes["t11"], None,
                          broad_hi_threshold=thr, late_line_basis=basis)
    assert stage_top == "RE-RATING"


def test_cov_basis_theme_without_cov_not_flaggable_late():
    """In a percentile_cov build, a theme lacking breadth_cov is NOT flaggable late —
    it must never fall back to comparing legacy breadth against the cov threshold."""
    from engine.foresight_cascade import _compute_broad_hi_threshold, _stage
    vals = {f"t{i}": 0.95 for i in range(10)}
    cov = {f"t{i}": 0.10 + 0.02 * i for i in range(9)}   # t9 has NO breadth_cov
    rv_themes = _rv_themes_with_breadth_cov(vals, cov)
    thr, basis = _compute_broad_hi_threshold(rv_themes)
    assert basis == "percentile_cov"
    stage, _ = _stage(None, rv_themes["t9"], None,
                      broad_hi_threshold=thr, late_line_basis=basis)
    assert stage != "RE-RATING"


def test_late_line_provisional_flag_in_payload():
    """REVIEW F3: the p80 percentile choice is uncalibrated pending the shadow ledger —
    the payload must declare it provisional."""
    from engine.foresight_cascade import compute_foresight_cascade
    c = compute_foresight_cascade(write_ledger=False)
    if c is not None:
        assert c.get("late_line_provisional") is True


# ── W5b (Q4): two-tier desk — tier tagging ───────────────────────────────────

def test_tier_p_for_numeric_fred_band():
    """Tier spec contract for _compute_tier — tests the four cases the review specifies.

    (a) numeric_band=NEUTRAL → P  (NEUTRAL is a live FRED composite read, not language-only)
    (b) top band "TIGHT (text)" WITH live numeric_band=TIGHTENING → P
        (anti-laundering guard rewrites top band; numeric_band retains the real measurement)
    (c) numeric_band=None + top band NEUTRAL (language-only theme) → W
        (cybersecurity/solar: NEUTRAL top band but no FRED leg → must stay W)
    (d) numeric_band=None + live theme_feed_summary → P
        (orphan-rescue: FDA shortage promotes glp1_obesity even with no FRED bottleneck)
    """
    from engine.foresight_cascade import _compute_tier

    # (a) NEUTRAL is a live numeric FRED composite band → Tier P
    assert _compute_tier("NEUTRAL", None) == "P", "NEUTRAL numeric_band should be Tier P"

    # (a) Other numeric bands also qualify
    for numeric_band in ("TIGHT", "SOLD_OUT", "LOOSE", "TIGHTENING", "GLUT_FORMING", "GLUT"):
        assert _compute_tier(numeric_band, None) == "P", (
            f"numeric_band={numeric_band} should be Tier P"
        )

    # (b) anti-laundering guard rewrites top band to "TIGHT (text)" but numeric_band
    #     retains TIGHTENING — _compute_tier receives numeric_band, not top band → P
    assert _compute_tier("TIGHTENING", None) == "P", (
        "numeric_band=TIGHTENING (FRED-mapped theme with text top band) should be Tier P"
    )

    # (c) language-only theme: top band is NEUTRAL but numeric_band is None (no FRED leg)
    #     → must stay Tier W (cybersecurity / solar case)
    assert _compute_tier(None, None) == "W", (
        "numeric_band=None (language-only theme) must be Tier W, NOT promoted by top-level band"
    )

    # (d) numeric_band=None but live theme_feed_summary → Tier P (orphan-rescue)
    feed = {"source": "fda_shortages", "band": "SHORTAGE_ACTIVE", "label": "FDA shortage ACTIVE"}
    assert _compute_tier(None, feed) == "P", (
        "theme_feed_summary present → Tier P even with numeric_band=None"
    )


def test_tier_w_for_null_numeric_band():
    """Tier W when numeric_band is None (no FRED measurement — language-only / AWAITING / null).

    Note: _compute_tier now receives bn.get("numeric_band"), NOT the top-level band.
    Themes with AWAITING_DATA or text-only top bands have numeric_band=None → Tier W.
    """
    from engine.foresight_cascade import _compute_tier
    # All these represent the numeric_band=None case (no live FRED read)
    assert _compute_tier(None, None) == "W", "numeric_band=None → Tier W"


def test_tier_p_for_theme_feed_summary_present():
    """Tier P when a theme_feed_summary is present (orphan-rescue feed) — even with
    numeric_band=None (FDA shortages rescue glp1_obesity into Tier P when FRED leg absent)."""
    from engine.foresight_cascade import _compute_tier
    feed = {"source": "fda_shortages", "band": "SHORTAGE_ACTIVE", "label": "FDA shortage ACTIVE"}
    assert _compute_tier(None, feed) == "P"


def test_tier_field_in_cascade_rows():
    """Each cascade row has a 'tier' field of 'P' or 'W'.

    Tier P requires numeric_band (the FRED-backed measurement) to be non-None.
    The bottleneck engine populates numeric_band on FRED-mapped themes.
    Language-only/AWAITING themes have numeric_band=None → Tier W.
    """
    bottleneck = {"themes": {
        # memory_storage: real FRED leg → numeric_band present (e.g. TIGHT from PPI composite)
        "memory_storage": {"name": "Memory", "band": "TIGHT", "tightness": 0.9,
                           "numeric_band": "TIGHT"},
        # glp1_obesity: no FRED bottleneck → numeric_band absent → Tier W (no feed either)
        "glp1_obesity":   {"name": "GLP-1", "band": None, "numeric_band": None},
        # cybersecurity: AWAITING_DATA top band, no FRED → numeric_band None → Tier W
        "cybersecurity":  {"name": "Cyber", "band": "AWAITING_DATA", "numeric_band": None},
    }}
    revisions = {"themes": {
        "memory_storage": {"name": "Memory", "breadth": 0.1, "level_state": "FLAT_LOW"},
        "glp1_obesity":   {"name": "GLP-1",  "breadth": 0.2, "level_state": "POSITIVE"},
        "cybersecurity":  {"name": "Cyber",  "breadth": 0.15, "level_state": "FLAT_LOW"},
    }}
    out = fc.compute_foresight_cascade(
        bottleneck=bottleneck, revisions=revisions,
        demand={"themes": {}}, glut={"themes": {}},
        fda_scarcity={},   # empty — no feed for these themes
        write_ledger=False,
    )
    assert out is not None
    tiers = {r["theme"]: r["tier"] for r in out["themes"]}
    assert tiers["memory_storage"] == "P"   # numeric_band=TIGHT → Tier P
    assert tiers["glp1_obesity"]   == "W"   # numeric_band=None, no feed → Tier W
    assert tiers["cybersecurity"]  == "W"   # numeric_band=None → Tier W


def test_tier_p_via_fda_feed_no_fred():
    """(d) glp1_obesity tier-upgrades to P when theme_feed_summary is populated by fda_scarcity."""
    bottleneck = {"themes": {
        "glp1_obesity": {"name": "GLP-1", "band": "AWAITING_DATA"},
    }}
    revisions = {"themes": {
        "glp1_obesity": {"name": "GLP-1", "breadth": 0.1, "level_state": "FLAT_LOW"},
    }}
    # Synthetic fda_scarcity dict — shortage active
    fda_scarcity_data = {
        "glp1_obesity": {
            "band": "SHORTAGE_ACTIVE",
            "n_active": 2,
            "n_resolved": 0,
            "molecules_checked": ["semaglutide"],
            "details": ["Semaglutide Injection [Current/Limited Availability]"],
            "rationale": "2 active shortage records",
        }
    }
    out = fc.compute_foresight_cascade(
        bottleneck=bottleneck, revisions=revisions,
        demand={"themes": {}}, glut={"themes": {}},
        fda_scarcity=fda_scarcity_data,
        write_ledger=False,
    )
    assert out is not None
    r = out["themes"][0]
    assert r["theme"] == "glp1_obesity"
    assert r["tier"] == "P", "FDA shortage feed should promote glp1_obesity to Tier P"
    assert r["theme_feed_summary"] is not None
    assert r["theme_feed_summary"]["band"] == "SHORTAGE_ACTIVE"


# ── W5b (§3.4): FDA scarcity engine ─────────────────────────────────────────

def _make_shortage_df(rows: list[dict]) -> "pd.DataFrame":
    import pandas as pd
    return pd.DataFrame(rows)


def test_fda_scarcity_active_band():
    """(b) Active shortage records → SHORTAGE_ACTIVE band."""
    from engine.fda_scarcity import compute_fda_scarcity, SHORTAGE_ACTIVE
    df = _make_shortage_df([
        {"generic_name": "Semaglutide Injection", "status": "Current",
         "availability": "Limited Availability", "initial_posting_date": "07/01/2023"},
        {"generic_name": "Liraglutide Injection", "status": "Current",
         "availability": "Unavailable", "initial_posting_date": "06/15/2022"},
    ])
    result = compute_fda_scarcity(df)
    glp1 = result.get("glp1_obesity")
    assert glp1 is not None
    assert glp1["band"] == SHORTAGE_ACTIVE
    assert glp1["n_active"] >= 2


def test_fda_scarcity_resolved_band():
    """(b) All shortage records resolved → SHORTAGE_RESOLVED without economic wording."""
    from engine.fda_scarcity import compute_fda_scarcity, SHORTAGE_RESOLVED
    df = _make_shortage_df([
        {"generic_name": "Semaglutide Tablet", "status": "Resolved",
         "availability": "", "initial_posting_date": "03/01/2022"},
        {"generic_name": "Liraglutide Injection", "status": "Resolved",
         "availability": "", "initial_posting_date": "07/18/2023"},
    ])
    result = compute_fda_scarcity(df)
    glp1 = result.get("glp1_obesity")
    assert glp1 is not None
    assert glp1["band"] == SHORTAGE_RESOLVED
    assert glp1["n_resolved"] >= 2
    assert "resolved" in glp1["rationale"].lower()
    assert glp1["source_status"] == "RESOLVED_REPORTED"


def test_fda_scarcity_none_on_missing_cache(monkeypatch, tmp_path):
    """(c) Missing cache → every theme remains visible as unavailable.

    Hermetic: monkeypatches the observation reader so the test never touches real disk data
    (data/fda/shortages.parquet).  Without this patch the cache loader succeeds on
    checkouts that already have the file, making the test pass for the wrong reason.
    """
    import sys

    # R-T01-10: composition follows configuration, not acquisition.
    fake_collector = type(sys)("collectors.fda_shortages")
    fake_collector.read_shortage_observation = lambda **_kwargs: (_ for _ in ()).throw(
        FileNotFoundError("monkeypatched: no cache")
    )
    monkeypatch.setitem(sys.modules, "collectors.fda_shortages", fake_collector)

    from engine.fda_scarcity import compute_fda_scarcity
    result = compute_fda_scarcity(df=None)
    assert isinstance(result, dict)
    for v in result.values():
        assert v is not None
        assert v["source_status"] == "UNAVAILABLE"


def test_fda_scarcity_mixed_active_and_resolved():
    """(b) Mixed active + resolved → SHORTAGE_ACTIVE wins (active takes priority)."""
    from engine.fda_scarcity import compute_fda_scarcity, SHORTAGE_ACTIVE
    df = _make_shortage_df([
        {"generic_name": "Semaglutide Injection", "status": "Current",
         "availability": "Unavailable", "initial_posting_date": "07/01/2023"},
        {"generic_name": "Liraglutide Injection", "status": "Resolved",
         "availability": "", "initial_posting_date": "06/15/2022"},
    ])
    result = compute_fda_scarcity(df)
    glp1 = result.get("glp1_obesity")
    assert glp1 is not None
    assert glp1["band"] == SHORTAGE_ACTIVE


def test_fda_scarcity_no_glp1_records():
    """(b) No GLP-1 records in df → NONE band (not an error)."""
    from engine.fda_scarcity import compute_fda_scarcity, BAND_NONE
    df = _make_shortage_df([
        {"generic_name": "Bupivacaine Hydrochloride", "status": "Current",
         "availability": "Unavailable", "initial_posting_date": "07/01/2023"},
    ])
    result = compute_fda_scarcity(df)
    glp1 = result.get("glp1_obesity")
    assert glp1 is not None
    assert glp1["band"] == BAND_NONE
    assert glp1["source_status"] == "NO_MATCHING_RECORDS"


def test_theme_feed_summary_flows_into_glp1_row():
    """(d) theme_feed_summary is populated on the glp1_obesity cascade row when
    fda_scarcity has an active shortage for it."""
    bottleneck = {"themes": {
        "glp1_obesity": {"name": "GLP-1 / Obesity", "band": "AWAITING_DATA"},
    }}
    revisions = {"themes": {
        "glp1_obesity": {"name": "GLP-1 / Obesity", "breadth": 0.05, "level_state": "FLAT_LOW"},
    }}
    fda_scarcity_data = {
        "glp1_obesity": {
            "band": "SHORTAGE_ACTIVE",
            "source_status": "CURRENT_REPORTED",
            "freshness": {},
            "n_active": 3,
            "n_resolved": 0,
            "molecules_checked": ["semaglutide", "tirzepatide", "liraglutide"],
            "details": ["Semaglutide Injection [Current/Limited Availability]"],
            "rationale": "3 current regulator records observed",
        }
    }
    out = fc.compute_foresight_cascade(
        bottleneck=bottleneck, revisions=revisions,
        demand={"themes": {}}, glut={"themes": {}},
        fda_scarcity=fda_scarcity_data,
        write_ledger=False,
    )
    assert out is not None
    r = out["themes"][0]
    assert r["theme"] == "glp1_obesity"
    # feed summary must be present and correctly structured
    tfs = r.get("theme_feed_summary")
    assert tfs is not None, "theme_feed_summary should be populated for glp1_obesity"
    assert tfs["band"] == "SHORTAGE_ACTIVE"
    assert tfs["source"] == "fda_shortages"
    assert "shortage" in tfs["label"].lower()
    # stage is NOT changed by the feed — still driven by T1/T4
    assert r["stage"] in ("WATCH", "PRECIPICE (text)", "PRECIPICE", "BROADENING",
                          "RE-RATING", "UNKNOWN"), f"unexpected stage: {r['stage']}"


def test_theme_feed_summary_none_when_no_fda_data():
    """(c) theme_feed_summary is None when fda_scarcity is empty/absent."""
    bottleneck = {"themes": {
        "glp1_obesity": {"name": "GLP-1 / Obesity", "band": "AWAITING_DATA"},
    }}
    revisions = {"themes": {
        "glp1_obesity": {"name": "GLP-1 / Obesity", "breadth": 0.1, "level_state": "FLAT_LOW"},
    }}
    out = fc.compute_foresight_cascade(
        bottleneck=bottleneck, revisions=revisions,
        demand={"themes": {}}, glut={"themes": {}},
        fda_scarcity={},   # empty dict — no data for any theme
        write_ledger=False,
    )
    assert out is not None
    r = out["themes"][0]
    assert r.get("theme_feed_summary") is None


# ── W5b: Jinja render test — watch shelf renders; stage pills exclude Tier W ─

def test_jinja_watch_shelf_renders_and_pills_exclude_tier_w():
    """(e) Jinja render: Tier W themes appear in watch shelf; stage pills only count Tier P."""
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
    from jinja2 import Environment, FileSystemLoader
    import pathlib

    repo = pathlib.Path(__file__).resolve().parent.parent
    env = Environment(loader=FileSystemLoader(str(repo / "templates")), autoescape=True)
    tmpl = env.get_template("foresight.html.j2")

    # 2 Tier P themes (one TIGHT/numeric, one with FDA feed) + 1 Tier W
    themes_data = [
        {
            "theme": "memory_storage", "name": "Memory & Storage",
            "tier": "P", "stage": "PRECIPICE",
            "bottleneck_band": "TIGHT", "bottleneck_text_only": False, "tightness": 0.9,
            "bottleneck_regime": True, "demand_band": None, "demand_strength": None,
            "capex_yoy": None, "revision_breadth": 0.05, "revision_level": "FLAT_LOW",
            "broadening_state": "FLAT_LOW", "est_drift_90d": None,
            "guidance_band": None, "guidance_net": None, "guidance_raisers": None,
            "guidance_cutters": None, "altdata_summary": None, "n_altdata_leading": 0,
            "altdata_members": None, "glut_band": None, "glut_score": None,
            "theme_feed_summary": None,
            "rationale": "supply TIGHT while revisions not yet firing",
            "entry_ready": False, "entry_note": "thesis intact",
            "score": 62, "score_detail": {"verdict": "high-conviction", "axes": {}, "caps": []},
            "size_band": None, "size_note": None,
        },
        {
            "theme": "glp1_obesity", "name": "GLP-1 / Obesity",
            "tier": "P", "stage": "WATCH",
            "bottleneck_band": "AWAITING_DATA", "bottleneck_text_only": False, "tightness": None,
            "bottleneck_regime": False, "demand_band": None, "demand_strength": None,
            "capex_yoy": None, "revision_breadth": 0.08, "revision_level": "FLAT_LOW",
            "broadening_state": "FLAT_LOW", "est_drift_90d": None,
            "guidance_band": None, "guidance_net": None, "guidance_raisers": None,
            "guidance_cutters": None, "altdata_summary": None, "n_altdata_leading": 0,
            "altdata_members": None, "glut_band": None, "glut_score": None,
            "theme_feed_summary": {
                "source": "fda_shortages", "theme": "glp1_obesity",
                "band": "SHORTAGE_ACTIVE", "tone": "warn",
                "label": "FDA shortage: current (3)",
                "label_zh": "FDA短缺：当前（3）", "freshness": {},
                "source_status": "CURRENT_REPORTED",
                "rationale": "3 current regulator records observed",
                "n_active": 3, "n_resolved": 0,
            },
            "rationale": "supply not tight; FDA shortage ACTIVE — demand exceeds supply",
            "entry_ready": False, "entry_note": "not a thesis stage — no entry",
            "score": 42, "score_detail": {"verdict": "watch", "axes": {}, "caps": []},
            "size_band": None, "size_note": None,
        },
        {
            "theme": "cybersecurity", "name": "Cybersecurity",
            "tier": "W", "stage": "WATCH",
            "bottleneck_band": None, "bottleneck_text_only": False, "tightness": None,
            "bottleneck_regime": False, "demand_band": None, "demand_strength": None,
            "capex_yoy": None, "revision_breadth": 0.12, "revision_level": "FLAT_LOW",
            "broadening_state": "FLAT_LOW", "est_drift_90d": None,
            "guidance_band": None, "guidance_net": None, "guidance_raisers": None,
            "guidance_cutters": None, "altdata_summary": None, "n_altdata_leading": 0,
            "altdata_members": None, "glut_band": None, "glut_score": None,
            "theme_feed_summary": None,
            "rationale": "supply not tight; nothing actionable yet",
            "entry_ready": False, "entry_note": "not a thesis stage — no entry",
            "score": 38, "score_detail": {"verdict": "watch", "axes": {}, "caps": []},
            "size_band": None, "size_note": None,
        },
    ]
    stage_counts = {"PRECIPICE": 1, "BROADENING": 0, "RE-RATING": 0,
                    "GLUT-RISK": 0, "WATCH": 2, "UNKNOWN": 0}
    html = tmpl.render(
        cascade={"sizing": None, "demand_pool": None, "dislocation": None},
        themes=themes_data,
        stage_counts=stage_counts,
        stage_order=["PRECIPICE", "BROADENING", "RE-RATING", "GLUT-RISK", "WATCH", "UNKNOWN"],
        demand_pool=None, dislocation=None,
        track={"foresight": 0, "bottleneck": 0, "glut": 0, "revisions": 0,
               "guidance": 0, "emergence": 0, "subsector": 0, "recent": []},
        grade=None, emergence=None, subsectors=None,
        convergence=None, power=None, analyst=None, monitor=None, health=None,
        asof="2026-07-02", generated_utc="2026-07-02 00:00 UTC",
        nav_prefix="", active_section="research", active_page="foresight",
    )
    # Watch shelf must render with cybersecurity in it
    assert "fx-watch-shelf" in html, "watch shelf container missing"
    assert "Cybersecurity" in html
    # Watch shelf caveat must contain the honesty text (plain-word rewrite, DESIGN_DOCTRINE):
    # explains why these themes can't be confirmed truly early without a hard supply read.
    assert "no hard supply number yet" in html or "no numeric physical correlate" in html
    # Stage pills region: stage counts are Tier P only — cybersecurity (Tier W, WATCH) excluded
    # The pills only show Tier P themes: 1 PRECIPICE (memory_storage) + 1 WATCH (glp1_obesity,
    # BUT glp1_obesity is Tier P despite WATCH stage because of FDA feed)
    # Count "PRECIPICE" in the stage pills area (before watch shelf)
    assert "PRECIPICE" in html  # Tier P PRECIPICE card renders
    # Watch shelf chip ("+N on watch shelf") must appear
    assert "watch shelf" in html.lower() or "观察架" in html
    # FDA chip must appear for glp1_obesity
    assert "FDA shortage: current (3)" in html
    assert "FDA短缺：当前（3）" in html
    # Cybersecurity should appear in watch shelf, not as a full card
    # (It has tier=W so it should be in .fx-watch-rows not .fx-cards)
    watch_shelf_pos = html.find("fx-watch-shelf")
    tier_p_cards_pos = html.find("fx-cards")
    # watch shelf comes after tier P cards section
    assert watch_shelf_pos > tier_p_cards_pos, (
        "watch shelf should render below Tier P cards"
    )


def test_jinja_tier_less_row_defaults_to_shelf():
    """F4: a row with no 'tier' field must land on the watch shelf, not silently vanish.

    Old cached JSON consumers (no tier key) must degrade visibly: the row appears in
    the watch shelf instead of dropping out of both selectattr/rejectattr filters.
    """
    import sys
    import pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
    from jinja2 import Environment, FileSystemLoader

    repo = pathlib.Path(__file__).resolve().parent.parent
    env = Environment(loader=FileSystemLoader(str(repo / "templates")), autoescape=True)
    tmpl = env.get_template("foresight.html.j2")

    # One row WITH tier=P, one WITHOUT tier key (simulates old cached JSON)
    themes_data = [
        {
            "theme": "memory_storage", "name": "Memory & Storage",
            "tier": "P", "stage": "PRECIPICE",
            "bottleneck_band": "TIGHT", "bottleneck_text_only": False, "tightness": 0.9,
            "bottleneck_regime": True, "demand_band": None, "demand_strength": None,
            "capex_yoy": None, "revision_breadth": 0.05, "revision_level": "FLAT_LOW",
            "broadening_state": "FLAT_LOW", "est_drift_90d": None,
            "guidance_band": None, "guidance_net": None, "guidance_raisers": None,
            "guidance_cutters": None, "altdata_summary": None, "n_altdata_leading": 0,
            "altdata_members": None, "glut_band": None, "glut_score": None,
            "theme_feed_summary": None,
            "rationale": "supply TIGHT while revisions not yet firing",
            "entry_ready": False, "entry_note": "thesis intact",
            "score": 62, "score_detail": {"verdict": "high-conviction", "axes": {}, "caps": []},
            "size_band": None, "size_note": None,
        },
        {
            # NO 'tier' key — simulates old cached JSON row
            "theme": "old_cached_theme", "name": "Old Cached Theme",
            "stage": "WATCH",
            "bottleneck_band": None, "bottleneck_text_only": False, "tightness": None,
            "bottleneck_regime": False, "demand_band": None, "demand_strength": None,
            "capex_yoy": None, "revision_breadth": 0.03, "revision_level": "FLAT_LOW",
            "broadening_state": "FLAT_LOW", "est_drift_90d": None,
            "guidance_band": None, "guidance_net": None, "guidance_raisers": None,
            "guidance_cutters": None, "altdata_summary": None, "n_altdata_leading": 0,
            "altdata_members": None, "glut_band": None, "glut_score": None,
            "theme_feed_summary": None,
            "rationale": "no bottleneck data yet",
            "entry_ready": False, "entry_note": "not a thesis stage — no entry",
            "score": 30, "score_detail": {"verdict": "watch", "axes": {}, "caps": []},
            "size_band": None, "size_note": None,
        },
    ]
    stage_counts = {"PRECIPICE": 1, "BROADENING": 0, "RE-RATING": 0,
                    "GLUT-RISK": 0, "WATCH": 1, "UNKNOWN": 0}
    html = tmpl.render(
        cascade={"sizing": None, "demand_pool": None, "dislocation": None},
        themes=themes_data,
        stage_counts=stage_counts,
        stage_order=["PRECIPICE", "BROADENING", "RE-RATING", "GLUT-RISK", "WATCH", "UNKNOWN"],
        demand_pool=None, dislocation=None,
        track={"foresight": 0, "bottleneck": 0, "glut": 0, "revisions": 0,
               "guidance": 0, "emergence": 0, "subsector": 0, "recent": []},
        grade=None, emergence=None, subsectors=None,
        convergence=None, power=None, analyst=None, monitor=None, health=None,
        asof="2026-07-02", generated_utc="2026-07-02 00:00 UTC",
        nav_prefix="", active_section="research", active_page="foresight",
    )
    # Tier-less row must appear somewhere in the rendered HTML (not silently dropped)
    assert "Old Cached Theme" in html, "tier-less row must not be silently dropped"
    # The watch shelf must render (tier-less row defaults to W → shelf visible)
    assert "fx-watch-shelf" in html, "watch shelf must render for tier-less row"
    # The tier-less row must appear INSIDE the watch shelf (after fx-watch-shelf),
    # not before it (which would mean it was rendered as a Tier P card)
    shelf_pos = html.find("fx-watch-shelf")
    theme_pos = html.find("Old Cached Theme")
    assert theme_pos > shelf_pos, (
        "tier-less row must land in the watch shelf, not in the Tier P cards section"
    )


# ── W5a: fingerprint sub-object passthrough (2026-08-04 health coherence) ────
# The health surface counts t1_fingerprint liveness from CASCADE rows
# (foresight_health._assess_t1_fingerprint reads t["fingerprint"]["n_legs_live"]);
# before 2026-08-04 the row assembly dropped the bottleneck payload's fingerprint
# sub-object, so the leg read structurally DARK 0/N while fingerprint-variant
# stages sat on the board.

_FP_SUB = {"theme": "a", "fingerprint_tightness": 0.61, "leg7_member_inventory": 0.61,
           "leg8_member_backlog": None, "n_legs_live": 1, "basis": "annual",
           "provisional": True}


def _fp_cascade():
    bottleneck = {"themes": {"a": {"name": "A", "band": "TIGHTENING (fingerprint)",
                                   "tightness": 0.37, "fingerprint_only": True,
                                   "fingerprint": dict(_FP_SUB)}}}
    revisions = {"themes": {"a": {"name": "A", "breadth": 0.05, "level_state": "FLAT_LOW"}}}
    return fc.compute_foresight_cascade(bottleneck=bottleneck, revisions=revisions,
                                        demand={"themes": {}}, glut={"themes": {}},
                                        write_ledger=False)


def test_fingerprint_subobject_passes_through_to_row():
    """The bottleneck payload's fingerprint sub-object must ride the cascade row."""
    out = _fp_cascade()
    r = out["themes"][0]
    assert r["stage"] == "PRECIPICE (fingerprint)"   # mirrors shipped medical_devices
    assert r["bottleneck_fingerprint_only"] is True
    assert r["fingerprint"] == _FP_SUB


def test_fingerprint_stage_implies_health_leg_not_dark():
    """Coherence invariant: a board carrying a fingerprint-variant stage can never
    yield a health block that reports t1_fingerprint fully DARK. (The autouse
    _isolate_real_data_tree fixture points the health-log append at tmp_path.)"""
    from engine.foresight_health import compute_foresight_health

    out = _fp_cascade()
    assert any(t["stage"] in fc.FINGERPRINT_THESIS_STAGES for t in out["themes"])

    h = compute_foresight_health(cascade=out)
    leg = h["legs"]["t1_fingerprint"]
    assert leg["status"] != "DARK"
    assert leg["detail"] == "1/1"


# ── Healthcare D1 T01: scoped FDA supply observations ────────────────────────

UTC = timezone.utc

_STATUSES = (
    "CURRENT_REPORTED",
    "RESOLVED_REPORTED",
    "DISCONTINUATION_REPORTED",
    "MIXED_REPORTED",
    "UNCLASSIFIED",
    "NO_MATCHING_RECORDS",
    "UNAVAILABLE",
)


def _capture(now, generation="2026-09-23"):
    return {
        "qualified": True,
        "finished_at": now.isoformat(),
        "source_generation": generation,
        "atomic_snapshot_proven": False,
    }


def _failed_capture(now, generation=""):
    return {
        "qualified": False,
        "finished_at": (now - timedelta(days=30)).isoformat(),
        "source_generation": generation,
        "atomic_snapshot_proven": False,
        "failure_code": "FIRST_PAGE_OUTAGE",
    }


def _retained_capture_with_failed_refresh(now, generation="2026-08-20"):
    return {
        **_capture(now - timedelta(days=31), generation),
        "refresh_failed": True,
        "refresh_failure_code": "FIRST_PAGE_OUTAGE",
        "refresh_at": "2026-09-22T09:00:00+00:00",
    }


def _summary_row(status="Current", availability="Available", ndc="TEST-A"):
    return {
        "generic_name": "Synthetic Theme A",
        "package_ndc": ndc,
        "status": status,
        "availability": availability,
        "initial_posting_date": "2026-03-02",
    }


def test_current_available_does_not_become_resolved():
    from engine.fda_scarcity import summarize_supply

    now = datetime(2026, 9, 23, 12, tzinfo=UTC)
    out = summarize_supply(
        [_summary_row()],
        capture=_capture(now),
        now=now,
        max_capture_age=timedelta(days=2),
    )
    assert out["source_status"] == "CURRENT_REPORTED"
    assert out["rows"][0]["regulator_status"] == "current"
    assert out["rows"][0]["manufacturer_availability"] == "Available"
    assert out["counts"]["current"] == 1
    assert "glut" not in out["label"].casefold()


def test_supply_table_states_and_legacy_bands(monkeypatch):
    import engine.fda_scarcity as fda_module
    from engine.fda_scarcity import (
        BAND_NONE, SHORTAGE_ACTIVE, compute_fda_scarcity,
        summarize_supply,
    )

    monkeypatch.setattr(fda_module, "MOLECULE_THEME_MAP", {"synthetic theme a": ["glp1_obesity"]})

    now = datetime(2026, 9, 23, 12, tzinfo=UTC)
    cases = [
        ([_summary_row("Current"), _summary_row("Resolved", ndc="TEST-B")],
         "MIXED_REPORTED", SHORTAGE_ACTIVE),
        ([_summary_row("To Be Discontinued")],
         "DISCONTINUATION_REPORTED", BAND_NONE),
        ([_summary_row("Under Review")], "UNCLASSIFIED", BAND_NONE),
        ([], "NO_MATCHING_RECORDS", BAND_NONE),
    ]
    for rows, source_status, band in cases:
        summary = summarize_supply(
            rows, capture=_capture(now), now=now, max_capture_age=timedelta(days=2)
        )
        assert summary["source_status"] == source_status
        frame = pd.DataFrame(rows)
        computed = compute_fda_scarcity(frame)["glp1_obesity"]
        assert computed["source_status"] == source_status
        assert computed["band"] == band


def test_no_qualified_capture_is_unavailable_but_retains_rows():
    from engine.fda_scarcity import summarize_supply

    now = datetime(2026, 9, 23, 12, tzinfo=UTC)
    out = summarize_supply(
        [_summary_row()],
        capture=_failed_capture(now),
        now=now,
        max_capture_age=timedelta(days=2),
    )
    assert out["source_status"] == "UNAVAILABLE"
    assert out["freshness"]["capture_qualified"] is False
    assert out["freshness"]["stale"] is True
    assert out["freshness"]["failed_refresh"] is None
    assert out["counts"]["current"] == 1
    assert out["rows"][0]["regulator_status"] == "current"
    assert out["label"] == (
        "FDA source unavailable — no qualified generation on file, refresh failed · "
        "captured 30 d ago"
    )
    assert out["label_zh"] == "FDA来源不可用——无合格来源生成日期，刷新失败 · 采集于30天前"


def test_known_and_unrecognized_rows_expose_both_parts():
    from engine.fda_scarcity import summarize_supply

    now = datetime(2026, 9, 23, 12, tzinfo=UTC)
    out = summarize_supply(
        [_summary_row("Current"), _summary_row("Under Review", ndc="TEST-B")],
        capture=_capture(now), now=now, max_capture_age=timedelta(days=2),
    )
    assert out["source_status"] == "CURRENT_REPORTED"
    assert out["counts"]["current"] == 1
    assert out["counts"]["unrecognized"] == 1
    assert out["counts"]["matched"] == 2
    assert out["coverage"]["matched_rows"] == 2
    assert out["coverage"]["unclassified_rows"] == 1
    assert "1 record unclassified" in out["label"]


def test_fresh_capture_with_old_generation_is_not_called_fresh():
    from engine.fda_scarcity import summarize_supply

    now = datetime(2026, 9, 23, 12, tzinfo=UTC)
    out = summarize_supply(
        [_summary_row()], capture=_capture(now, "2026-07-25"),
        now=now, max_capture_age=timedelta(days=2),
    )
    assert out["freshness"]["capture_qualified"] is True
    assert out["freshness"]["stale"] is False
    assert out["freshness"]["source_generation_age_days"] == 60
    assert "fresh" not in out["label"].casefold()


def test_legacy_dataframe_path_has_unknown_capture(monkeypatch):
    import engine.fda_scarcity as fda_module
    from engine.fda_scarcity import compute_fda_scarcity

    monkeypatch.setattr(fda_module, "MOLECULE_THEME_MAP", {"synthetic theme a": ["glp1_obesity"]})
    frame = pd.DataFrame([_summary_row()])
    row = compute_fda_scarcity(frame)["glp1_obesity"]
    assert row["source_status"] == "CURRENT_REPORTED"
    assert row["summary"]["freshness"]["capture_qualified"] is None
    assert row["summary"]["freshness"]["stale"] is None
    assert row["summary"]["label"].endswith("capture time unknown")


def test_observation_attrs_can_report_failed_or_inconsistent_refresh(monkeypatch):
    import engine.fda_scarcity as fda_module

    monkeypatch.setattr(fda_module, "MOLECULE_THEME_MAP", {"synthetic theme a": ["glp1_obesity"]})
    now = datetime(2026, 9, 23, 12, tzinfo=UTC)
    frame = pd.DataFrame([_summary_row()])
    frame.attrs["fda_observation"] = {
        "capture": _capture(now), "last_refresh": None,
        "legacy": False, "inconsistent": True, "failed_refresh": False,
    }
    capture, _ = fda_module._observation_capture(frame.attrs["fda_observation"])
    row = {"band": fda_module.BAND_NONE}
    row["summary"] = fda_module.summarize_supply(
        [_summary_row()], capture=capture, now=now, max_capture_age=None,
    )
    row["source_status"] = row["summary"]["source_status"]
    assert row["source_status"] == "UNAVAILABLE"
    assert row["band"] == "NONE"
    assert row["summary"]["freshness"]["capture_qualified"] is False
    assert row["summary"]["freshness"]["failed_refresh"] is None
    assert row["summary"]["counts"]["matched"] == 1
    assert row["summary"]["label"] == (
        "FDA source unavailable — last observation unreadable · captured 0 d ago"
    )
    assert row["summary"]["label_zh"] == "FDA来源不可用——上次观测无法读取 · 采集于0天前"
    chip = fda_module.format_theme_feed_chip(row, "glp1_obesity")
    assert chip["tone"] == "mute"
    assert chip["rationale"] == "The FDA source is unavailable."


def test_all_supply_chip_statuses_render_with_distinct_plain_text():
    from engine.fda_scarcity import format_theme_feed_chip

    now = datetime(2026, 9, 23, 12, tzinfo=UTC)
    rows = {
        "CURRENT_REPORTED": [_summary_row("Current")],
        "RESOLVED_REPORTED": [_summary_row("Resolved")],
        "DISCONTINUATION_REPORTED": [_summary_row("To Be Discontinued")],
        "MIXED_REPORTED": [_summary_row("Current"), _summary_row("Resolved", ndc="TEST-B")],
        "UNCLASSIFIED": [_summary_row("Under Review")],
        "NO_MATCHING_RECORDS": [],
    }
    chips = {}
    for status, case_rows in rows.items():
        summary = summarize_supply_for_test(case_rows, now)
        row = {status: _computed_row_for_summary(summary)}
        chip = format_theme_feed_chip(row[status], "glp1_obesity")
        assert chip is not None
        assert chip["source_status"] == status
        assert chip["label_zh"]
        assert chip["tone"] in {"warn", "cool", "mute"}
        assert chip["rationale"] != summary["label"]
        chips[status] = chip
    from engine.fda_scarcity import summarize_supply
    unavailable_summary = summarize_supply(
        [_summary_row()], capture=_failed_capture(now), now=now,
        max_capture_age=timedelta(days=2),
    )
    unavailable = _computed_row_for_summary(unavailable_summary)
    chip = format_theme_feed_chip(unavailable, "glp1_obesity")
    assert chip is not None and chip["source_status"] == "UNAVAILABLE"
    assert "no qualified generation on file" in chip["label"]
    chips["UNAVAILABLE"] = chip
    assert len({chip["label"] for chip in chips.values()}) == 7
    assert len({chip["label_zh"] for chip in chips.values()}) == 7
    assert len({chip["rationale"] for chip in chips.values()}) == 7
    banned = ("glut", "tell", "all-clear", "catching up", "demand exceeds supply", "supply constraint lifted")
    for chip in chips.values():
        text = " ".join(str(chip[key]) for key in ("label", "label_zh", "rationale"))
        assert all(word not in text.casefold() for word in banned)


def test_chip_zh_labels_translate_every_appended_fact():
    from engine.fda_scarcity import summarize_supply

    now = datetime(2026, 9, 23, 12, tzinfo=UTC)
    current_with_remainder = summarize_supply(
        [_summary_row("Current"), _summary_row("Under Review", ndc="TEST-B")],
        capture=_capture(now - timedelta(days=3), "2026-09-20"), now=now, max_capture_age=None,
    )
    legacy = summarize_supply(
        [_summary_row("Current")], capture=None, now=now, max_capture_age=None,
    )
    unavailable = summarize_supply(
        [_summary_row()], capture=_failed_capture(now), now=now,
        max_capture_age=timedelta(days=2),
    )

    assert current_with_remainder["label"] == (
        "FDA shortage: current (1) · captured 3 d ago · "
        "source generation 2026-09-20 · 1 record unclassified"
    )
    assert current_with_remainder["label_zh"] == (
        "FDA短缺：当前（1） · 采集于3天前 · "
        "来源生成日期2026-09-20 · 1条记录未分类"
    )
    assert legacy["label"].endswith("capture time unknown")
    assert legacy["label_zh"].endswith("采集时间未知")
    assert unavailable["label"] == (
        "FDA source unavailable — no qualified generation on file, refresh failed · captured 30 d ago"
    )
    assert unavailable["label_zh"] == (
        "FDA来源不可用——无合格来源生成日期，刷新失败 · 采集于30天前"
    )
    for summary in (current_with_remainder, legacy, unavailable):
        chinese = summary["label_zh"].casefold()
        assert "source generation" not in chinese
        assert "record unclassified" not in chinese
        assert "capture time unknown" not in chinese


def test_failed_refresh_discloses_the_retained_qualified_capture(monkeypatch):
    import engine.fda_scarcity as fda_module
    from engine.fda_scarcity import compute_fda_scarcity, format_theme_feed_chip

    monkeypatch.setattr(fda_module, "MOLECULE_THEME_MAP", {"synthetic theme a": ["glp1_obesity"]})
    # `compute_fda_scarcity` reads the wall clock (it has no injected `now` seam and passes
    # max_capture_age=None per R-T01-12), so the capture has to be anchored to that SAME
    # clock. A fixed calendar date here renders a different "captured N d ago" on every
    # later day: the assertion would pass only on the day it was written.
    now = datetime.now(UTC)
    frame = pd.DataFrame([_summary_row()])
    frame.attrs["fda_observation"] = {
        "capture": _retained_capture_with_failed_refresh(now),
        "last_refresh": {"qualified": False, "failure_code": "FIRST_PAGE_OUTAGE",
                         "attempted_at": "2026-09-22T09:00:00+00:00"},
        "legacy": False, "inconsistent": False, "failed_refresh": True,
    }
    row = compute_fda_scarcity(frame)["glp1_obesity"]
    chip = format_theme_feed_chip(row, "glp1_obesity")
    assert chip["source_status"] == "CURRENT_REPORTED"
    assert chip["tone"] == "warn"
    assert chip["label"] == (
        "FDA shortage: current (1) · captured 31 d ago · source generation 2026-08-20 · "
        "refresh failed 2026-09-22"
    )
    assert chip["label_zh"] == (
        "FDA短缺：当前（1） · 采集于31天前 · 来源生成日期2026-08-20 · 刷新失败 2026-09-22"
    )
    assert chip["freshness"]["failed_refresh"]["failure_code"] == "FIRST_PAGE_OUTAGE"
    assert chip["freshness"]["failed_refresh"]["attempted_at"] == "2026-09-22T09:00:00+00:00"


def test_legacy_chip_rows_preserve_discontinued_and_unclassified_states():
    from engine.fda_scarcity import format_theme_feed_chip

    discontinued = format_theme_feed_chip(
        {"band": "NONE", "n_active": 0, "n_resolved": 0, "n_discontinued": 2,
         "details": ["Synthetic A [To Be Discontinued]"]},
        "glp1_obesity",
    )
    assert discontinued["source_status"] == "DISCONTINUATION_REPORTED"
    assert discontinued["band"] == "NONE"
    assert "discontinuation reported (2)" in discontinued["label"]

    unrecognized = format_theme_feed_chip(
        {"band": "NONE", "n_active": 0, "n_resolved": 0, "n_discontinued": 0,
         "details": ["Synthetic A [Under Review]"]},
        "glp1_obesity",
    )
    assert unrecognized["source_status"] == "UNCLASSIFIED"
    assert unrecognized["band"] == "NONE"
    assert "status unclassified" in unrecognized["label"]
    bottleneck = {"themes": {"glp1_obesity": {"name": "GLP-1 / Obesity", "band": "AWAITING_DATA"}}}
    revisions = {"themes": {"glp1_obesity": {"name": "GLP-1 / Obesity", "breadth": 0.05,
                                              "level_state": "FLAT_LOW"}}}

    def run(source_status):
        scarcity = {"glp1_obesity": {"band": "SHORTAGE_ACTIVE",
                                     "source_status": source_status,
                                     "freshness": {}, "n_active": 1, "n_resolved": 0,
                                     "rationale": "one regulator record observed"}}
        return fc.compute_foresight_cascade(
            bottleneck=bottleneck, revisions=revisions, demand={"themes": {}},
            glut={"themes": {}}, fda_scarcity=scarcity, write_ledger=False,
        )["themes"][0]

    current = run("CURRENT_REPORTED")
    resolved = run("RESOLVED_REPORTED")
    assert current["stage"] == resolved["stage"] == "WATCH"
    assert current.get("entry") == resolved.get("entry") is None
    assert current["tier"] == resolved["tier"] == "P"


def test_rendered_html_shows_zh_chip_and_no_banned_words():
    import pathlib
    from jinja2 import Environment, FileSystemLoader

    repo = pathlib.Path(__file__).resolve().parent.parent
    env = Environment(loader=FileSystemLoader(str(repo / "templates")), autoescape=True)
    template = env.get_template("foresight.html.j2")
    now = datetime(2026, 9, 23, 12, tzinfo=UTC)
    unavailable_summary = summarize_supply_for_test(
        [_summary_row()], now, capture=_failed_capture(now),
    )
    failed_refresh_summary = summarize_supply_for_test(
        [_summary_row()], now,
        capture={**_capture(now - timedelta(days=30), "2026-08-20"),
                 "refresh_failed": True, "refresh_failure_code": "FIRST_PAGE_OUTAGE",
                 "refresh_at": "2026-09-22T09:00:00+00:00"},
    )
    chips = [format_chip_for_render(summarize_supply_for_test([_summary_row()], now)),
             format_chip_for_render(unavailable_summary),
             format_chip_for_render(failed_refresh_summary)]
    html = template.render(
        cascade={"sizing": None, "demand_pool": None, "dislocation": None},
        themes=[{"theme": "glp1_obesity", "name": "Synthetic Theme", "tier": "P",
                 "stage": "WATCH", "bottleneck_band": None,
                 "bottleneck_text_only": False, "tightness": None,
                 "bottleneck_regime": False, "demand_band": None,
                 "demand_strength": None, "capex_yoy": None,
                 "revision_breadth": None, "revision_level": None,
                 "broadening_state": None, "est_drift_90d": None,
                 "guidance_band": None, "guidance_net": None,
                 "guidance_raisers": None, "guidance_cutters": None,
                 "altdata_summary": None, "n_altdata_leading": 0,
                 "altdata_members": None, "glut_band": None, "glut_score": None,
                 "theme_feed_summary": chip, "rationale": "one regulator record observed",
                 "entry_ready": False, "entry_note": "not a thesis stage — no entry",
                 "score": 42, "score_detail": {"verdict": "watch", "axes": {}, "caps": []},
                 "size_band": None, "size_note": None} for chip in chips],
        stage_counts={}, stage_order=[], demand_pool=None, dislocation=None,
        track={"recent": []}, grade=None, emergence=None, subsectors=None,
        convergence=None, power=None, analyst=None, monitor=None, health=None,
        asof="2026-09-23", generated_utc="2026-09-23 00:00 UTC",
        nav_prefix="", active_section="research", active_page="foresight",
    )
    assert "FDA短缺：当前（1）" in html
    assert "FDA来源不可用" in html
    assert "刷新失败 2026-09-22" in html
    banned = ("glut", "tell", "all-clear", "catching up", "demand exceeds supply", "supply constraint lifted")
    chip_html = " ".join(
        segment.split("</span>")[0] for segment in html.split("fx-chip feed-")[1:]
    )
    for word in banned:
        assert word not in chip_html.casefold()


def summarize_supply_for_test(rows, now, capture=None):
    from engine.fda_scarcity import summarize_supply
    return summarize_supply(
        rows, capture=capture or _capture(now), now=now, max_capture_age=None,
    )


def format_chip_for_render(summary):
    from engine.fda_scarcity import format_theme_feed_chip
    return format_theme_feed_chip(_computed_row_for_summary(summary), "glp1_obesity")


def _computed_row_for_summary(summary):
    status = summary["source_status"]
    return {
        "band": "SHORTAGE_ACTIVE" if status in {"CURRENT_REPORTED", "MIXED_REPORTED"}
                else ("SHORTAGE_RESOLVED" if status == "RESOLVED_REPORTED" else "NONE"),
        "source_status": status,
        "summary": summary,
        "freshness": summary["freshness"],
        "n_active": summary["counts"]["current"],
        "n_resolved": summary["counts"]["resolved"],
        "n_discontinued": summary["counts"]["discontinued"],
        "molecules_checked": summary["coverage"]["molecules_checked"],
        "details": [], "rationale": summary["label"],
    }


def test_cache_absent_fda_source_never_changes_cascade_tier_stage_or_entry():
    import engine.foresight_cascade as fc

    bottleneck = {"themes": {"glp1_obesity": {"name": "GLP-1 / Obesity", "band": "AWAITING_DATA"}}}
    revisions = {"themes": {"glp1_obesity": {"name": "GLP-1 / Obesity", "breadth": 0.05,
                                             "level_state": "FLAT_LOW"}}}

    def run(source_status, band):
        scarcity = {"glp1_obesity": {"band": band, "source_status": source_status,
                                     "freshness": {"capture_qualified": False}, "n_active": 1, "n_resolved": 0,
                                     "n_discontinued": 0, "molecules_checked": [],
                                     "details": [], "rationale": "synthetic"}}
        return fc.compute_foresight_cascade(
            bottleneck=bottleneck, revisions=revisions, demand={"themes": {}},
            glut={"themes": {}}, fda_scarcity=scarcity, write_ledger=False,
        )["themes"][0]

    current = run("CURRENT_REPORTED", "SHORTAGE_ACTIVE")
    unavailable = run("UNAVAILABLE", "NONE")
    empty = run("NO_MATCHING_RECORDS", "NONE")
    assert current["tier"] == unavailable["tier"] == empty["tier"] == "P"
    assert current["stage"] == unavailable["stage"] == empty["stage"]
    assert current.get("entry") == unavailable.get("entry") == empty.get("entry")
    assert unavailable["theme_feed_summary"]["label"] == (
        "FDA source unavailable — no qualified generation on file, refresh failed"
    )


def test_missing_generation_on_qualified_capture_renders_authored_unknown_copy():
    from engine.fda_scarcity import summarize_supply

    now = datetime(2026, 9, 23, 12, tzinfo=UTC)
    out = summarize_supply(
        [_summary_row()], capture=_capture(now, ""), now=now, max_capture_age=None,
    )
    assert out["freshness"]["source_generation"] is None
    assert out["label"] == (
        "FDA shortage: current (1) · captured 0 d ago · source generation unknown"
    )
    assert out["label_zh"] == "FDA短缺：当前（1） · 采集于0天前 · 来源生成日期未知"


def test_iso_datetime_generation_parses_to_its_date():
    from engine.fda_scarcity import summarize_supply

    now = datetime(2026, 9, 23, 12, tzinfo=UTC)
    out = summarize_supply(
        [_summary_row()], capture=_capture(now, "2026-07-25T00:00:00+00:00"),
        now=now, max_capture_age=None,
    )
    assert out["freshness"]["source_generation"] == "2026-07-25"
    assert "source generation 2026-07-25" in out["label"]
    assert "来源生成日期2026-07-25" in out["label_zh"]


def test_resolved_and_discontinued_mixture_names_both_counts(monkeypatch):
    import engine.fda_scarcity as fda_module
    from engine.fda_scarcity import format_theme_feed_chip

    monkeypatch.setattr(fda_module, "MOLECULE_THEME_MAP", {"synthetic theme a": ["glp1_obesity"]})
    now = datetime(2026, 9, 23, 12, tzinfo=UTC)
    row = {"band": fda_module.BAND_NONE}
    row["summary"] = fda_module.summarize_supply(
        [_summary_row("Resolved"), _summary_row("To Be Discontinued", ndc="TEST-B")],
        capture=_capture(now), now=now, max_capture_age=None,
    )
    row["source_status"] = row["summary"]["source_status"]
    assert row["source_status"] == "DISCONTINUATION_REPORTED"
    row["rationale"] = (
        "regulator status: resolved (1 record) and discontinued (1 record) — supply status only"
    )
    assert row["rationale"] == (
        "regulator status: resolved (1 record) and discontinued (1 record) — supply status only"
    )
    assert row["rationale"] == (
        "regulator status: resolved (1 record) and discontinued (1 record) — supply status only"
    )
    chip = format_theme_feed_chip(row, "glp1_obesity")
    assert chip["label"] == (
        "FDA: resolved 1 / discontinued 1 — supply status only · captured 0 d ago · "
        "source generation 2026-09-23"
    )


def _observation_sweep(collector, generation, record, start, finish, *, outage=False):
    def fetch_page(skip, limit):
        if outage:
            raise OSError("synthetic outage")
        return {
            "meta": {"last_updated": generation, "results": {"total": 1}},
            "results": [] if skip else [record],
        }

    return collector.collect_shortage_sweep(
        fetch_page, clock=_observation_clock(start, finish), page_size=100, max_pages=3,
    )


def _observation_clock(start, finish):
    calls = iter((start, finish))
    return lambda: next(calls)


def _observation_digest(path):
    import hashlib

    sidecar = path.with_suffix(".observation.json")
    return hashlib.sha256(sidecar.read_bytes()).hexdigest() if sidecar.exists() else None


def _render_observation(tmp_path, monkeypatch, state_name):
    import collectors.fda_shortages as collector
    import engine.fda_scarcity as scarcity

    path = tmp_path / state_name / "shortages.parquet"
    path.parent.mkdir()
    monkeypatch.setattr(collector, "_shortages_path", lambda: path)
    monkeypatch.setattr(scarcity, "MOLECULE_THEME_MAP", {"Synthetic A": ["synthetic_theme"]})
    record = {
        "package_ndc": "TEST-A", "generic_name": "Synthetic A", "status": "Current",
        "availability": "Available", "initial_posting_date": "2026-03-02",
    }
    start = datetime(2026, 9, 23, 12, tzinfo=UTC)
    finish = start.replace(second=6)

    if state_name == "REFRESH_FAILED":
        first = _observation_sweep(collector, None, record, start, finish, outage=True)
        assert first["qualified"] is False
        collector.save_shortage_observation(first, path=path, expected_predecessor=None)
    elif state_name != "NOT_OBSERVED":
        first = _observation_sweep(collector, "2026-09-23", record, start, finish)
        assert first["qualified"] is True
        assert collector.save_shortage_observation(
            first, path=path, expected_predecessor=None
        )["promoted"] is True

    if state_name == "UNREADABLE":
        path.write_bytes(b"synthetic unreadable parquet")
    elif state_name == "LEGACY":
        path.with_suffix(".observation.json").unlink()

    row = scarcity.compute_fda_scarcity().get("synthetic_theme")
    return scarcity.format_theme_feed_chip(row, "synthetic_theme")


def test_observation_states_render_distinct_unavailable_truths(tmp_path, monkeypatch):
    from engine.foresight_cascade import _compute_tier

    expected = {
        "NOT_OBSERVED": (
            "FDA source not yet observed — no qualified generation on file",
            "FDA来源尚未观测——无合格来源生成日期",
        ),
        "UNREADABLE": (
            "FDA source unavailable — last observation unreadable",
            "FDA来源不可用——上次观测无法读取",
        ),
        "REFRESH_FAILED": (
            "FDA source unavailable — no qualified generation on file, refresh failed",
            "FDA来源不可用——无合格来源生成日期，刷新失败",
        ),
        "LEGACY": (
            "FDA shortage: current (1) · capture time unknown",
            "FDA短缺：当前（1） · 采集时间未知",
        ),
    }
    baseline = None
    for state_name, (english, chinese) in expected.items():
        chip = _render_observation(tmp_path, monkeypatch, state_name)
        assert chip is not None
        if state_name == "LEGACY":
            assert chip["source_status"] == "CURRENT_REPORTED"
            assert chip["tone"] == "warn"
            assert chip["freshness"]["capture_qualified"] is None
            assert "capture time unknown" in chip["label"]
        else:
            assert chip["source_status"] == "UNAVAILABLE"
            assert chip["tone"] == "mute"
            assert chip["freshness"]["capture_qualified"] is False
            assert "capture time unknown" not in chip["label"]
        assert chip["label"] == english
        assert chip["label_zh"] == chinese
        assert chip["band"] == "NONE" if state_name != "LEGACY" else chip["band"] == "SHORTAGE_ACTIVE"
        tier = _compute_tier(None, chip)
        if baseline is None:
            baseline = tier
        assert tier == baseline


def test_non_ascii_chip_rationale_is_rejected(monkeypatch):
    import pytest
    import engine.fda_scarcity as fda_module

    monkeypatch.setattr(
        fda_module,
        "_chip_rationale",
        lambda status, counts: "FDA来源不可用",
    )
    with pytest.raises(ValueError, match="ASCII text only"):
        fda_module.format_theme_feed_chip(
            {"summary": {"source_status": "CURRENT_REPORTED", "counts": {"current": 1},
                         "coverage": {}, "freshness": {}, "label": "synthetic",
                         "label_zh": "synthetic"},
             "band": "SHORTAGE_ACTIVE", "source_status": "CURRENT_REPORTED"},
            "glp1_obesity",
        )

"""SIC-D-B12 — live-vs-training hazard feature parity harness tests.

Synthetic only: no network, no site, no data/ writes (data/hazard is read
read-only for the artifact-backed deep-equality test; every other test is pure
or runs on the seeded synthetic tape).
"""
from __future__ import annotations

import copy

import pandas as pd
import pytest

from engine import hazard_parity as hp
from engine.cycle_rhythm import estimate_kinds
from engine.hazard_score import (_MODEL_PATH, _build_feature_vector,
                                 score as hz_score)

# ─────────────────────────────────────────────────────────────────────────────
# Shared fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def tape():
    return hp.synthetic_tape()


@pytest.fixture(scope="module")
def one_record(tape):
    """One live record on the full synthetic tape (the live builder, not a mock)."""
    rec = hp.live_record(tape, tape["index"][-1])
    assert rec is not None
    return rec


@pytest.fixture(scope="module")
def full_report(tape):
    """The full harness run on the canonical fixture (module-scoped: ~10s once)."""
    return hp.parity_report(tape)


# ─────────────────────────────────────────────────────────────────────────────
# 1. _stamp_hazard byte-identity across the _live_hazard_inputs extraction
# ─────────────────────────────────────────────────────────────────────────────


def _legacy_inline_inputs(rec: dict, family: str = "sector"):
    """The PRE-B12 inline assembly, reproduced verbatim from the packet's premise
    (the body _stamp_hazard carried at the base commit).  The extraction must
    return exactly this."""
    from engine.hazard_score import _UP_PHASES

    nw = rec.get("now") or {}
    turns = rec.get("turns") or []
    if "hazard_features" in nw:
        hf = nw["hazard_features"]
    else:
        confirmed = [t for t in turns if not t.get("provisional")]
        last_conf = confirmed[-1] if confirmed else None
        last_t = turns[-1] if turns else None
        proj = rec.get("proj") or {}
        period_yrs = proj.get("period_yrs") or {}
        median_half_yrs = float(period_yrs.get("median") or 0.0) / 2.0
        now_x_approx = 0.0
        osc_pts = rec.get("osc") or []
        if osc_pts:
            now_x_approx = float(osc_pts[-1].get("x") or osc_pts[-1]["x"])
        age_turn_yrs = 0.0
        if last_conf and last_conf.get("x") is not None:
            age_turn_yrs = max(0.0, now_x_approx - float(last_conf["x"]))
        hf = {
            "age_since_turn_bars": int(round(age_turn_yrs * 252.0)),
            "pos": float(nw.get("pos") or 50.0),
            "osc_slope": float(nw.get("osc_slope") or 0.0),
            "amp_leg_pct": last_t.get("mag_pct") if last_t else None,
            "median_half_yrs": median_half_yrs,
            "n_turns_all": len(turns),
            "freq": "D",
            "family": family,
            "mom_score": nw.get("rs_63d"),
            "rs_63d": nw.get("rs_63d"),
            "vol_pctile": None,
            "trend_pass": float(bool(nw.get("above200d"))),
        }
    phase = nw.get("phase") or nw.get("phase_v2") or ""
    direction = "up" if phase in _UP_PHASES else "down"
    return hf, direction, nw.get("quad"), nw.get("liq_expanding")


def test_stamp_hazard_identical_before_after_extraction(one_record, tape):
    """The extracted helper returns the pre-B12 inline assembly verbatim, the
    stamped now.hazard equals scoring exactly those inputs, and a second build
    of the same record stamps the identical block."""
    import engine.sector_cycles as sc

    rec = copy.deepcopy(one_record)
    legacy = _legacy_inline_inputs(rec, "sector")
    extracted = sc._live_hazard_inputs(rec, "sector")
    assert extracted == legacy

    # B12r2 (RB12 repair): without the admitted model artifact the stamp is a
    # no-op, so the two equality asserts below would compare nothing — skip with
    # a reason instead of passing vacuously (or key-erroring in a sparse tree).
    if not _MODEL_PATH.exists():
        pytest.skip(f"admitted model artifact absent ({_MODEL_PATH.name}) — "
                    "now.hazard stamp assertions need it")

    sc._stamp_hazard(rec, family="sector")
    hf, direction, quad, liq = sc._live_hazard_inputs(rec, family="sector")
    assert rec["now"]["hazard"] is not None          # never a vacuous None==None
    assert rec["now"]["hazard"] == hz_score(hf, direction, "sector", quad, liq)

    rec2 = hp.live_record(tape, tape["index"][-1])
    sc._stamp_hazard(rec2, family="sector")
    assert rec2["now"]["hazard"] == rec["now"]["hazard"]


# ─────────────────────────────────────────────────────────────────────────────
# 2. The training side IMPORTS the panel functions (monkeypatch moves them)
# ─────────────────────────────────────────────────────────────────────────────


def test_training_side_uses_imported_panel_functions(tape, monkeypatch):
    mes = hp.month_end_grid(tape)[::24][-3:]          # three cheap month-ends
    design, _ = hp.training_side(tape, pd.DatetimeIndex(mes))
    before = list(design["mom_score"])

    panel = hp.panel_module()
    monkeypatch.setattr(panel, "_mom_score", lambda close: close * 0.0)
    design2, _ = hp.training_side(tape, pd.DatetimeIndex(mes))
    after = list(design2["mom_score"])

    assert len(before) == len(after) == 3
    assert before != after, "monkeypatching the panel module must move the row"
    assert all(v == 0.0 for v in after)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Hand-built equal vectors → MATCH everywhere → PARITY_HOLDS
# ─────────────────────────────────────────────────────────────────────────────


def test_equal_vectors_match_and_parity_holds():
    # Live side: a real hf through the real scorer vector construction.
    # log_age_ratio lands ≥1.63 so the scorer's b5 equals the panel's b5 bucket
    # (ratio ≥1.5) — the only region where the two bucket ladders agree.
    hf = {"age_since_turn_bars": 252 * 24, "median_half_yrs": 1.0, "pos": 71.3,
          "osc_slope": 4.2, "amp_leg_pct": 38.0, "mom_score": 0.06,
          "rs_63d": 0.031, "vol_pctile": 0.44, "trend_pass": 1.0, "freq": "D",
          "family": "sector"}
    live_vec = _build_feature_vector(hf, "up", "sector", None, None)
    assert live_vec is not None

    # Training side: a hand-built panel row through the real build_design.
    fit = hp.fit_module()
    row = pd.DataFrame([{
        "age_bucket": "b5", "log_age_ratio": live_vec["log_age_ratio"],
        "amp_proxy": live_vec["amp_proxy"], "pos_osc": hf["pos"],
        "osc_slope": hf["osc_slope"], "trend_pass": hf["trend_pass"],
        "mom_score": hf["mom_score"], "rs_63d": hf["rs_63d"],
        "vol_pctile": hf["vol_pctile"], "quad": None, "liquidity": None,
        "family": "us_sector",
    }])
    train_vec = {k: float(v) for k, v in fit.build_design(row).iloc[0].items()
                 if k in live_vec}

    cmp_ = hp.compare_vectors(train_vec, live_vec, "up")
    assert all(c["match"] for c in cmp_.values()), \
        {f: c for f, c in cmp_.items() if not c["match"]}
    verdict, failing = hp.verdict_from(
        {f: c["match"] for f, c in cmp_.items()},
        {"n": 2, "agree": 2, "disagree": 0},
        {"live_epoch_matches_artifact": True, "detector_version_agrees": True,
         "training_epoch_matches_artifact": True})
    assert (verdict, failing) == ("PARITY_HOLDS", [])


def test_verdict_from_fails_when_training_epoch_mismatches():
    """B12r2 (RB12 repair): training_epoch_matches_artifact is now PART of the
    basis_epoch gate — a synthetic report failing only that check must return
    PARITY_FAILS naming basis_epoch."""
    verdict, failing = hp.verdict_from(
        {f: True for f in hp.STATIC_CLASSES},
        {"n": 2, "agree": 2, "disagree": 0},
        {"live_epoch_matches_artifact": True, "detector_version_agrees": True,
         "training_epoch_matches_artifact": False})
    assert verdict == "PARITY_FAILS"
    assert failing == ["basis_epoch"]


# ─────────────────────────────────────────────────────────────────────────────
# 4. vol_pctile=None is IMPUTED_CONSTANT and fails
# ─────────────────────────────────────────────────────────────────────────────


def test_vol_pctile_imputed_constant_class_and_mismatch():
    assert hp.STATIC_CLASSES["vol_pctile"]["class"] == "IMPUTED_CONSTANT"

    live_hf = {"age_since_turn_bars": 3024, "median_half_yrs": 1.0, "pos": 50.0,
               "osc_slope": 0.0, "amp_leg_pct": 30.0, "mom_score": 0.0,
               "rs_63d": 0.0, "vol_pctile": None, "trend_pass": 0.0,
               "freq": "D", "family": "sector"}
    live_vec = _build_feature_vector(live_hf, "up", "sector", None, None)
    assert live_vec["vol_pctile"] == 0.42          # the scorer's constant
    train_vec = dict(live_vec, vol_pctile=0.10)    # a real panel measurement
    cmp_ = hp.compare_vectors(train_vec, live_vec, "up")
    assert cmp_["vol_pctile"]["match"] is False
    assert cmp_["vol_pctile"]["diff_sd"] > 0.05


# ─────────────────────────────────────────────────────────────────────────────
# 5. The direction check counts a planted disagreement
# ─────────────────────────────────────────────────────────────────────────────


def test_direction_check_counts_planted_disagreement():
    out = hp.direction_check([("up", "up"), ("down", "up"), ("down", "down")])
    assert out == {"n": 3, "agree": 2, "disagree": 1, "agree_frac": round(2 / 3, 4)}


# ─────────────────────────────────────────────────────────────────────────────
# 6. The recorded constant equals the harness verdict on the fixture
# ─────────────────────────────────────────────────────────────────────────────


def test_recorded_verdict_matches_harness(full_report):
    const = hp.LIVE_HAZARD_PARITY
    assert const["verdict"] == full_report["verdict"]
    assert list(const["failing"]) == list(full_report["failing"])
    assert const["measured_on"] == hp.BASE_SHA
    assert full_report["input"]["kind"].startswith("seeded_synthetic")
    # B12r2: the drift check is not verdict/failing-only — the direction counts
    # and every per-feature worst diff must reproduce the frozen report too (so
    # the widened basis_epoch gate provably leaves the verdict what it is today).
    assert const["report"]["direction"] == full_report["direction"]
    frozen_feats = {r["feature"]: r for r in const["report"]["features"]}
    fresh_feats = {r["feature"]: r for r in full_report["features"]}
    assert set(frozen_feats) == set(fresh_feats)
    for feat, fresh in fresh_feats.items():
        frozen = frozen_feats[feat]
        assert frozen["match"] == fresh["match"], feat
        assert frozen["worst_abs_diff_sd"] == fresh["worst_abs_diff_sd"], feat
        assert frozen["worst_abs_diff"] == fresh["worst_abs_diff"], feat


# ─────────────────────────────────────────────────────────────────────────────
# 7. estimate_kinds follows the constant; `now` is untouched
# ─────────────────────────────────────────────────────────────────────────────


_NOW_WITH_MODEL_CELL = {
    "hazard": {
        "1m": {"p": 0.12, "source": "MODEL", "cell_verdict": "PASS"},
        "3m": {"p": 0.3, "source": "PRIOR", "cell_verdict": "PRIOR"},
        "6m": {"p": 0.4, "source": "PRIOR", "cell_verdict": "PRIOR"},
    }
}


def test_estimate_kinds_claim_follows_constant(monkeypatch):
    frozen = copy.deepcopy(hp.LIVE_HAZARD_PARITY)
    try:
        ek = estimate_kinds(copy.deepcopy(_NOW_WITH_MODEL_CELL), None)
        assert ek["model_cell_current_claim"] == (
            "parity_holds" if frozen["verdict"] == "PARITY_HOLDS" else "parity_failed")
        assert ek["live_feature_parity"]["verdict"] == frozen["verdict"]
        assert ek["live_feature_parity"]["failing"] == frozen["failing"]
        # B12r2 (RB12 repair): the record carries a pointer, never the report —
        # the full report is published once in compute()'s meta.
        assert "report" not in ek["live_feature_parity"]
        assert ek["live_feature_parity"]["report_ref"] == "meta.live_hazard_parity"

        monkeypatch.setitem(hp.LIVE_HAZARD_PARITY, "verdict", "PARITY_HOLDS")
        ek2 = estimate_kinds(copy.deepcopy(_NOW_WITH_MODEL_CELL), None)
        assert ek2["model_cell_current_claim"] == "parity_holds"
        monkeypatch.setitem(hp.LIVE_HAZARD_PARITY, "verdict", "PARITY_FAILS")
        ek3 = estimate_kinds(copy.deepcopy(_NOW_WITH_MODEL_CELL), None)
        assert ek3["model_cell_current_claim"] == "parity_failed"
    finally:
        hp.LIVE_HAZARD_PARITY.clear()
        hp.LIVE_HAZARD_PARITY.update(frozen)


def test_estimate_kinds_never_writes_now():
    now = copy.deepcopy(_NOW_WITH_MODEL_CELL)
    before = copy.deepcopy(now)
    estimate_kinds(now, None)
    estimate_kinds(now, {"status": "unavailable"})
    assert now == before


# ─────────────────────────────────────────────────────────────────────────────
# 8. The report carries schema/version and no score/rank/win-rate field
# ─────────────────────────────────────────────────────────────────────────────


def _walk_keys(o):
    if isinstance(o, dict):
        for k, v in o.items():
            yield str(k)
            yield from _walk_keys(v)
    elif isinstance(o, list):
        for v in o:
            yield from _walk_keys(v)


def test_report_schema_and_no_score_rank_win_fields(full_report):
    assert full_report["schema"] == hp.PARITY_SCHEMA == "sector_cycles.hazard_parity.v1"
    assert isinstance(full_report["version"], int)
    bad = [k for k in _walk_keys(full_report)
           if "score" in k.lower() or "rank" in k.lower() or "win" in k.lower()]
    assert bad == []
    assert full_report["verdict"] in ("PARITY_HOLDS", "PARITY_FAILS")
    # same contract on the frozen constant's report
    bad2 = [k for k in _walk_keys(hp.LIVE_HAZARD_PARITY["report"])
            if "score" in k.lower() or "rank" in k.lower() or "win" in k.lower()]
    assert bad2 == []

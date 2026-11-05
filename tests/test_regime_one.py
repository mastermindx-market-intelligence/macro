"""Regime One tests — masterplan W2 acceptance (one test per mechanism).

Mechanisms guarded here:
  1. Flip attribution & veto — a dead-feed (renormalization) flip is VETOED and the
     label freezes; a genuine data flip passes. (The chaos-test core, #3.)
  2. Forward-filtered P(Quad) — a proper simplex, with reconstructed historical
     probabilities explicitly distinguished from saved issuance records. The flag
     smoothed_hindsight=False distinguishes the algorithm, not PIT eligibility.
  3. Fused risk — confidence DEGRADES when tape & macro disagree on the inflation
     axis (the 84.2%/inflection leakage finding encoded as an explicit input, #1/#4).
  4. Freshness ledger — the compact bitmask round-trips per-leg availability + the
     degraded flag (#32).
  5. Passports — every regime_one number carries {basis, frame, freshness, n}.
  6. Gross mapping — the single versioned table is the one source; degraded holds
     gross no looser than caution.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from engine import regime_one as R

_CENTROID = {"Q1": (0.5, -0.5), "Q2": (0.5, 0.5), "Q3": (-0.5, 0.5), "Q4": (-0.5, -0.5)}


def _synthetic_scores(block=200, cycles=2, seed=1):
    rng = np.random.default_rng(seed)
    order = ["Q1", "Q2", "Q3", "Q4"] * cycles
    rows, quads = [], []
    for q in order:
        gc, ic = _CENTROID[q]
        rows.append(rng.normal([gc, ic], 0.15, (block, 2)))
        quads += [q] * block
    X = np.vstack(rows)
    idx = pd.bdate_range("2005-01-03", periods=len(X))
    return pd.DataFrame({"growth_score": X[:, 0], "inflation_score": X[:, 1], "quad": quads},
                        index=idx)


# --- helpers to fabricate a tape/macro read without touching the store ------- #
def _legs(names, weight=1.0, value=1):
    """A leg dict as _subread emits: {leg: {value, weight}}."""
    return {n: {"value": value, "weight": weight} for n in names}


def _read(growth_legs, inflation_legs, gscore, iscore, asof="2026-06-30"):
    """Minimal tape/macro-shaped dict for attribute_flip / fused_risk."""
    return {
        "growth": gscore, "inflation": iscore,
        "growth_legs": growth_legs, "inflation_legs": inflation_legs,
        "n_available": sum(1 for c in {**growth_legs, **inflation_legs}.values()
                           if c["value"] is not None),
        "passport": R._passport(basis="market", frame="latest",
                                freshness={"asof": asof, "expected_cadence": "D",
                                           "state": "fresh"}, n=0),
    }


# --------------------------------------------------------------------------- #
# 1. Flip attribution & veto — THE chaos test
# --------------------------------------------------------------------------- #
# A mildly-negative tape growth read: three legs +1, three -1 -> tape-only weighted
# mean is slightly NEGATIVE (the -1 legs carry equal or more weight). payrolls+indpro
# (+1, w0.5 each) are what hold the FULL axis positive; when they die the axis flips.
_TAPE_G_MIXED = {"copper_gold": {"value": 1, "weight": 1.0},
                 "xly_xlp": {"value": 1, "weight": 1.0},
                 "us2y_direction": {"value": 1, "weight": 0.5},
                 "iwm_spy": {"value": -1, "weight": 1.0},
                 "cyclical_defensive": {"value": -1, "weight": 1.0},
                 "breadth_direction": {"value": -1, "weight": 1.0}}


def test_dead_feed_flip_is_vetoed():
    """Kill payrolls+indpro (they go NaN) so the growth axis renormalizes over the
    survivors and the quad flips Q1->Q4 with NO leg-value change — the flip must be
    VETOED and the label frozen at Q1, degraded published loudly."""
    # PREV: tape mixed (slightly negative alone) + payrolls/indpro +1 hold axis positive.
    prev = {"tape": _read(dict(_TAPE_G_MIXED), _legs(R._TAPE_INFL, value=-1), 0.077, -0.5),
            "macro": _read({"payrolls_trend": {"value": 1, "weight": 0.5},
                            "indpro_trend": {"value": 1, "weight": 0.5}}, {}, 1.0, None),
            "_legacy_quad": "Q1"}
    # CUR: IDENTICAL tape values; payrolls & indpro DIED (value None). Axis renormalizes
    # over the tape survivors -> now slightly negative -> raw quad Q4.
    tape = _read(dict(_TAPE_G_MIXED), _legs(R._TAPE_INFL, value=-1), -0.09, -0.5)
    macro = _read({"payrolls_trend": {"value": None, "weight": 0.5},
                   "indpro_trend": {"value": None, "weight": 0.5}}, {}, None, None)

    flip = R.attribute_flip(prev, tape, macro, legacy_quad="Q4")
    assert flip["flipped"] is True
    assert flip["degraded"] is True, flip
    assert flip["label_quad"] == "Q1", "label must freeze at prior on a renorm-driven flip"
    assert set(flip["components"]["vanished_legs"]) >= {"payrolls_trend", "indpro_trend"}
    assert flip["components"]["renorm_share"] > 0.50
    assert flip["components"]["data_delta"] == 0.0, "no leg value changed"


def test_genuine_data_flip_passes():
    """When leg VALUES flip (no legs vanish), the flip is data-driven and must PASS —
    label moves to the new quad, not degraded."""
    prev_g = {**_legs(R._TAPE_GROWTH, value=1),
              "payrolls_trend": {"value": 1, "weight": 0.5},
              "indpro_trend": {"value": 1, "weight": 0.5}}
    prev = {"tape": _read({k: v for k, v in prev_g.items() if k in R._TAPE_GROWTH}, {}, 0.9, None),
            "macro": _read({k: v for k, v in prev_g.items() if k in R._MACRO_GROWTH}, {}, 1.0, None),
            "_legacy_quad": "Q1"}
    # CUR: every growth leg VALUE flips to -1, all legs still AVAILABLE (nothing died).
    cur_g = {**_legs(R._TAPE_GROWTH, value=-1),
             "payrolls_trend": {"value": -1, "weight": 0.5},
             "indpro_trend": {"value": -1, "weight": 0.5}}
    tape = _read({k: v for k, v in cur_g.items() if k in R._TAPE_GROWTH}, {}, -0.9, None)
    macro = _read({k: v for k, v in cur_g.items() if k in R._MACRO_GROWTH}, {}, -1.0, None)

    flip = R.attribute_flip(prev, tape, macro, legacy_quad="Q4")
    assert flip["flipped"] is True
    assert flip["degraded"] is False, flip
    assert flip["label_quad"] == "Q4", "a genuine data flip must be honored"
    assert flip["components"]["renorm_share"] <= 0.50


def test_first_run_no_prev_never_flips():
    tape = _read(_legs(R._TAPE_GROWTH, value=1), _legs(R._TAPE_INFL, value=-1), 0.5, -0.5)
    macro = _read({}, {}, None, None)
    flip = R.attribute_flip(None, tape, macro, legacy_quad="Q1")
    assert flip["flipped"] is False
    assert flip["degraded"] is False
    assert flip["label_quad"] == "Q1"


# --------------------------------------------------------------------------- #
# 2. Causal filtered P(Quad)
# --------------------------------------------------------------------------- #
def test_filtered_pquad_is_a_simplex_and_causal_flagged():
    out = R._causal_filtered_pquad(_synthetic_scores())
    assert out is not None
    p = out["regime_probs_filtered"]
    assert abs(sum(p.values()) - 1.0) < 1e-6
    assert all(0.0 <= v <= 1.0 for v in p.values())
    assert out["smoothed_hindsight"] is False
    # last synthetic block is Q4 -> filtered read should favor Q4
    assert out["modal_quad"] == "Q4"


def _overlapping_scores(seed=3):
    """A NOISY 4-quad cycle whose states OVERLAP (0.55 noise) so the smoother's
    future-peeking materially changes the posterior at transitions. The final cycle's
    Q3->Q4 transition sits inside the last-252 history window."""
    rng = np.random.default_rng(seed)
    order = (["Q1"] * 300 + ["Q2"] * 300 + ["Q3"] * 300 + ["Q4"] * 300
             + ["Q1"] * 300 + ["Q2"] * 300 + ["Q3"] * 120 + ["Q4"] * 120)
    rows = []
    for q in order:
        gc, ic = _CENTROID[q]
        rows.append(rng.normal([gc, ic], 0.55, 2))
    X = np.array(rows)
    idx = pd.bdate_range("2004-01-01", periods=len(X))
    return pd.DataFrame({"growth_score": X[:, 0], "inflation_score": X[:, 1],
                         "quad": order}, index=idx)


def test_filtered_differs_from_smoothed_at_a_transition():
    """The filtered posterior must NOT equal the smoothed (full-sample) posterior at a
    regime transition. Both historical series still use the current fitted parameters;
    neither is thereby an as-issued history. This test distinguishes algorithms."""
    from hmmlearn.hmm import GaussianHMM
    scores = _overlapping_scores()
    feats = ["growth_score", "inflation_score"]
    X = scores[feats].to_numpy(float)
    labels = scores["quad"].to_numpy()
    present = list(dict.fromkeys(labels))
    k = len(present)
    idx = {q: j for j, q in enumerate(present)}
    means = np.array([X[labels == q].mean(0) for q in present])
    covs = np.array([np.cov(X[labels == q].T) + np.eye(2) * 1e-3 for q in present])
    tm = np.full((k, k), 1e-6)
    for a, b in zip(labels[:-1], labels[1:]):
        tm[idx[a], idx[b]] += 1.0
    tm /= tm.sum(1, keepdims=True)
    sp = np.array([(labels == q).mean() for q in present]); sp /= sp.sum()
    m = GaussianHMM(n_components=k, covariance_type="full", init_params="", params="")
    m.startprob_, m.transmat_, m.means_, m.covars_ = sp, tm, means, covs
    smoothed = m.predict_proba(X)               # forward-backward (uses future)
    out = R._causal_filtered_pquad(scores)
    hist = out["history_filtered"]
    assert len(hist) > 10
    diffs = []
    for h in hist[1:]:
        d = scores.index.get_loc(pd.Timestamp(h["date"]))
        filt_vec = np.array([h[q] for q in present])
        sm_vec = smoothed[d]
        diffs.append(float(np.abs(filt_vec - sm_vec).max()))
    assert max(diffs) > 0.02, \
        f"filtered must diverge from smoothed somewhere; max diff {max(diffs):.4f}"


# --------------------------------------------------------------------------- #
# 3. Fused risk — confidence degrades at inflation inflection
# --------------------------------------------------------------------------- #
def test_confidence_degrades_on_inflation_axis_disagreement():
    # AGREE case: tape & macro both inflation -0.5 -> low uncertainty
    tape_ag = _read({}, {}, 0.5, -0.5)
    macro_ag = _read({}, {}, 0.5, -0.5)
    flip_ag = R.attribute_flip(None, tape_ag, macro_ag, "Q1")
    fused_ag = R._fused_risk(tape_ag, macro_ag, "Q1", flip_ag, base_conf=0.8)
    # DISAGREE case: tape inflation +0.5, macro inflation -0.5 -> inflection
    tape_dis = _read({}, {}, 0.5, 0.5)
    macro_dis = _read({}, {}, 0.5, -0.5)
    flip_dis = R.attribute_flip(None, tape_dis, macro_dis, "Q2")
    fused_dis = R._fused_risk(tape_dis, macro_dis, "Q2", flip_dis, base_conf=0.8)
    assert fused_dis["inflation_inflection"]["disagree"] is True
    assert fused_ag["inflation_inflection"]["disagree"] is False
    assert fused_dis["confidence"] < fused_ag["confidence"], \
        "inflation-axis inflection must drop confidence"


def test_degraded_read_holds_gross_at_caution_or_tighter():
    tape = _read(_legs(R._TAPE_GROWTH, value=1), _legs(R._TAPE_INFL, value=-1), 0.5, -0.5)
    macro = _read({}, {}, 0.5, -0.5)
    degraded = {"degraded": True, "label_quad": "Q1", "asof": "2026-06-30"}
    fused = R._fused_risk(tape, macro, "Q1", degraded, base_conf=0.9)
    assert fused["gross_factor"] <= R.RISK_STATE_GROSS["caution"]
    assert fused["degraded"] is True


# --------------------------------------------------------------------------- #
# 4. Freshness ledger — compact bitmask
# --------------------------------------------------------------------------- #
def test_freshness_bitmask_roundtrips():
    macro = {
        "growth_legs": {
            "payrolls_trend": {"value": 1, "weight": 0.5, "freshness": {"state": "fresh"}},
            "indpro_trend": {"value": 1, "weight": 0.5, "freshness": {"state": "dead"}},
            "wei_trend": {"value": 1, "weight": 0.5, "freshness": {"state": "slow"}},
            "gdpnow_trend": {"value": 1, "weight": 0.5, "freshness": {"state": "stale"}},
        },
        "inflation_legs": {
            "sticky_cpi_direction": {"value": 1, "weight": 0.5, "freshness": {"state": "fresh"}},
        },
    }
    mask = R.freshness_bitmask(macro, degraded=True)
    dec = R.decode_bitmask(mask)
    assert dec["payrolls"] is True     # fresh
    assert dec["indpro"] is False      # dead
    assert dec["wei"] is True          # slow counts as available
    assert dec["gdpnow"] is False      # stale drops out
    assert dec["sticky_cpi"] is True
    assert dec["degraded"] is True


def test_bitmask_is_a_small_int():
    macro = {"growth_legs": {}, "inflation_legs": {}}
    assert R.freshness_bitmask(macro, degraded=False) == 0
    # every bit set stays well within an int16
    full = {"growth_legs": {k + "_trend": {"value": 1, "weight": 1,
                                           "freshness": {"state": "fresh"}}
                            for k in ("payrolls", "indpro", "wei", "gdpnow")},
            "inflation_legs": {"sticky_cpi_direction": {"value": 1, "weight": 1,
                                                        "freshness": {"state": "fresh"}}}}
    assert 0 < R.freshness_bitmask(full, degraded=True) < 2 ** 16


# --------------------------------------------------------------------------- #
# 5. Passports on every number
# --------------------------------------------------------------------------- #
def test_passport_shape():
    p = R._passport(basis="release", frame="pit",
                    freshness={"asof": "2026-06-30", "expected_cadence": "M",
                               "state": "fresh"}, n=42)
    assert set(p) >= {"basis", "frame", "freshness", "n", "validation"}
    assert p["basis"] == "release" and p["frame"] == "pit" and p["n"] == 42


def test_gross_mapping_is_single_versioned_table():
    # the fused gross for every state must come from RISK_STATE_GROSS, floored
    for st, gf in R.RISK_STATE_GROSS.items():
        assert R._GROSS_FLOOR <= gf <= 1.0
    assert R.RISK_STATE_GROSS_VERSION   # a version string exists


# --------------------------------------------------------------------------- #
# 6. Full compute smoke on a synthetic classify-shaped frame (no store I/O for the
#    tape/HMM; macro falls back to reference legs)
# --------------------------------------------------------------------------- #
def test_compute_smoke_with_synthetic_frame(tmp_path):
    scores = _synthetic_scores()
    # add the c_ leg columns the tape read needs (all +/-1 matching the quad)
    frame = scores.copy()
    for leg in R._TAPE_GROWTH + R._MACRO_GROWTH:
        frame[f"c_growth_{leg}"] = 1
    for leg in R._TAPE_INFL + R._MACRO_INFL:
        frame[f"c_inflation_{leg}"] = -1
    frame["regime_confidence"] = 0.4
    out = R.compute(frame, release_axis_row=None, base_effect=None,
                    legacy_latest={}, prev=None, data_dir=tmp_path)
    assert out["schema"] == R.SCHEMA
    assert out["shadow"] is True
    for key in ("tape", "macro", "forward", "fused_risk", "flip_attribution"):
        assert key in out
    # passports present on the decision-facing reads
    assert "passport" in out["tape"] and "passport" in out["fused_risk"]
    assert out["fused_risk"]["gross_mapping_version"] == R.RISK_STATE_GROSS_VERSION


# --------------------------------------------------------------------------- #
# 7. FRED-OUTAGE CHAOS TEST end-to-end through compute() — the masterplan
#    acceptance: a dead payrolls/indpro feed must FREEZE the label, not flip the quad.
# --------------------------------------------------------------------------- #
def _classify_frame_from_row(gscore, iscore, growth_leg_vals, infl_leg_vals):
    """Build a minimal classify()-shaped one-row frame (with the c_ leg columns and a
    2y history so the HMM can fit) whose LAST row carries the given leg values."""
    scores = _synthetic_scores()            # 2y+ history so the causal HMM fits
    # append one crafted final row
    last_idx = scores.index[-1] + pd.tseries.offsets.BDay(1)
    row = {"growth_score": gscore, "inflation_score": iscore,
           "quad": R.raw_quad(gscore, iscore)}
    for leg in R._TAPE_GROWTH + R._MACRO_GROWTH:
        row[f"c_growth_{leg}"] = growth_leg_vals.get(leg)
    for leg in R._TAPE_INFL + R._MACRO_INFL:
        row[f"c_inflation_{leg}"] = infl_leg_vals.get(leg)
    row["regime_confidence"] = 0.4
    frame = scores.copy()
    for leg in R._TAPE_GROWTH + R._MACRO_GROWTH:
        frame[f"c_growth_{leg}"] = 1
    for leg in R._TAPE_INFL + R._MACRO_INFL:
        frame[f"c_inflation_{leg}"] = -1
    frame.loc[last_idx] = pd.Series(row)
    return frame


def test_fred_outage_chaos_freezes_label_not_flips(tmp_path):
    """END-TO-END: a prior regime_one on Q1 (payrolls/indpro alive) meets a session where
    payrolls & indpro are DEAD (NaN) and the raw growth axis renormalizes negative -> the
    legacy quad would read Q4. regime_one.compute() must VETO the flip, freeze label at Q1,
    and publish degraded=True — proving an outage cannot flip the quad (#3)."""
    # tape growth mixed -> slightly negative alone; infl legs all -1.
    tape_g = {"copper_gold": 1, "xly_xlp": 1, "us2y_direction": 1,
              "iwm_spy": -1, "cyclical_defensive": -1, "breadth_direction": -1}
    infl = {leg: -1 for leg in R._TAPE_INFL + R._MACRO_INFL}

    # PREV read: payrolls/indpro alive (+1) hold growth positive -> Q1.
    prev_growth = {**tape_g, "payrolls_trend": 1, "indpro_trend": 1,
                   "wei_trend": None, "gdpnow_trend": None}
    prev_frame = _classify_frame_from_row(0.08, -0.5, prev_growth, infl)
    prev_out = R.compute(prev_frame, release_axis_row=None, base_effect=None,
                         legacy_latest={}, prev=None, data_dir=tmp_path)
    assert prev_out["legacy_quad"] == "Q1"

    # CUR read: SAME tape values, payrolls & indpro DEAD (None). Renormalized growth axis
    # is now negative -> the legacy quad reads Q4.
    cur_growth = {**tape_g, "payrolls_trend": None, "indpro_trend": None,
                  "wei_trend": None, "gdpnow_trend": None}
    cur_frame = _classify_frame_from_row(-0.09, -0.5, cur_growth, infl)
    assert str(cur_frame["quad"].iloc[-1]) == "Q4", "raw legacy quad should have flipped to Q4"

    cur_out = R.compute(cur_frame, release_axis_row=None, base_effect=None,
                        legacy_latest={}, prev=prev_out, data_dir=tmp_path)

    # THE PROOF: legacy quad flipped to Q4, but the LABEL is frozen at Q1 and degraded.
    assert cur_out["legacy_quad"] == "Q4"
    assert cur_out["label_quad"] == "Q1", "label must FREEZE at Q1, not follow the renorm flip"
    assert cur_out["degraded"] is True
    assert "degraded_reason" in cur_out
    fa = cur_out["flip_attribution"]["components"]
    assert set(fa["vanished_legs"]) >= {"payrolls_trend", "indpro_trend"}
    assert fa["renorm_share"] > 0.50
    # fused risk on a degraded read holds gross no looser than caution
    assert cur_out["fused_risk"]["gross_factor"] <= R.RISK_STATE_GROSS["caution"]


# W0: forward recursion is not an as-issued historical record.
def test_hmm_history_discloses_reconstruction_after_future_extension():
    rng = np.random.default_rng(90210)
    labels = np.array(["Q1" if (i // 30) % 2 == 0 else "Q2" for i in range(720)])
    x = rng.normal(0, .35, (720, 2))
    x[:, 0] += np.where(labels == "Q1", .25, -.25)
    frame = pd.DataFrame(x, index=pd.bdate_range("2021-01-01", periods=720),
                         columns=["growth_score", "inflation_score"])
    frame["quad"] = labels
    before = R._causal_filtered_pquad(frame.iloc[:600].copy())
    later = frame.copy()
    later.iloc[600:, 0] += 1.2
    after = R._causal_filtered_pquad(later)
    a = {r["date"]: r for r in before["history_filtered"]}
    b = {r["date"]: r for r in after["history_filtered"]}
    assert max(abs(a[d]["Q1"] - b[d]["Q1"]) for d in a.keys() & b.keys()) > .5
    for out, date in ((before, frame.index[599]), (after, frame.index[-1])):
        assert out["history_basis"] == "reconstructed_with_current_fit"
        assert out["history_replay_eligible"] is False
        assert out["model_fit_asof"] == str(date.date())
        assert out["smoothed_hindsight"] is False


def test_forward_read_carries_historical_basis(tmp_path):
    out = R._forward_read(_synthetic_scores(), None, tmp_path)["p_quad"]
    assert out["history_basis"] == "reconstructed_with_current_fit"
    assert out["history_replay_eligible"] is False
    assert out["model_fit_asof"] == str(_synthetic_scores().index[-1].date())


def _saved_hmm_row(asof="2026-07-01"):
    return {"asof": asof, "pred_modal_quad": "Q1",
            "p_quad_filtered": {"Q1": .9913, "Q2": .0006, "Q3": .0001, "Q4": .0081},
            "realized_quad_at_21d": None}


def _write_hmm_test_ledger(tmp_path, rows):
    import json
    p = tmp_path / "regime" / "regime_fwd_hmm.jsonl"
    p.parent.mkdir(exist_ok=True)
    p.write_text("".join(json.dumps(row) + "\n" for row in rows))
    return p


def test_hmm_issuance_reads_saved_legacy_probability_without_refitting(tmp_path, monkeypatch):
    row = _saved_hmm_row()
    p = _write_hmm_test_ledger(tmp_path, [row])
    before = p.read_bytes()
    def forbidden(*args, **kwargs):
        pytest.fail("inspection must not fit or read the historical frame")
    monkeypatch.setattr(R, "_causal_filtered_pquad", forbidden)
    monkeypatch.setattr(pd, "read_parquet", forbidden)
    out = R.read_hmm_issuance(row["asof"], tmp_path)
    assert out["status"] == "legacy_record"
    assert out["recorded_prediction"] == row["p_quad_filtered"]
    assert out["issued_at"] is None and out["historical_replay_eligible"] is False
    assert "realized_quad_at_21d" not in out
    assert p.read_bytes() == before


@pytest.mark.parametrize("case,status", [("absent", "missing_ledger"),
    ("missing-date", "missing_record"), ("duplicate", "ambiguous_record"),
    ("corrupt", "invalid_ledger"), ("bad-date", "invalid_date")])
def test_hmm_issuance_refuses_missing_or_ambiguous_evidence(tmp_path, case, status):
    date = "2026-07-01"
    if case != "absent":
        rows = [_saved_hmm_row()]
        if case == "duplicate": rows.append(_saved_hmm_row())
        p = _write_hmm_test_ledger(tmp_path, rows)
        if case == "corrupt": p.write_text(p.read_text() + "{broken\n")
        if case == "missing-date": date = "2026-07-02"
        if case == "bad-date": date = "2026-7-1"
    out = R.read_hmm_issuance(date, tmp_path)
    assert out["status"] == status
    assert out["recorded_prediction"] is None
    assert out["historical_replay_eligible"] is False
    assert out["reason"]


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -.1, 1.1, True, "0.9"])
def test_hmm_issuance_refuses_invalid_probability(tmp_path, bad):
    row = _saved_hmm_row()
    row["p_quad_filtered"]["Q1"] = bad
    _write_hmm_test_ledger(tmp_path, [row])
    out = R.read_hmm_issuance(row["asof"], tmp_path)
    assert out["recorded_prediction"] is None
    assert out["status"] in {"invalid_ledger", "invalid_record"}


@pytest.mark.parametrize("change", ["mass", "missing-key", "extra-key", "wrong-modal"])
def test_hmm_issuance_refuses_noncanonical_prediction(tmp_path, change):
    row = _saved_hmm_row()
    if change == "mass": row["p_quad_filtered"]["Q1"] = .5
    if change == "missing-key": del row["p_quad_filtered"]["Q4"]
    if change == "extra-key": row["p_quad_filtered"]["Q5"] = 0
    if change == "wrong-modal": row["pred_modal_quad"] = "Q4"
    _write_hmm_test_ledger(tmp_path, [row])
    assert R.read_hmm_issuance(row["asof"], tmp_path)["recorded_prediction"] is None


def test_hmm_issuance_rejects_duplicate_json_members(tmp_path):
    p = _write_hmm_test_ledger(tmp_path, [])
    p.write_text('{"asof":"2026-07-01","asof":"2026-07-02"}\n')
    assert R.read_hmm_issuance("2026-07-02", tmp_path)["status"] == "invalid_ledger"


def test_hmm_record_metadata_does_not_certify_source_vintages(tmp_path):
    row = {**_saved_hmm_row(), "issued_at": "2026-07-02T04:00:00+00:00",
           "model_fit_asof": "2026-07-01", "model_method": "quad_supervised_gaussian_hmm.v1",
           "source_basis": "regime_history_vintages_unverified"}
    _write_hmm_test_ledger(tmp_path, [row])
    out = R.read_hmm_issuance("2026-07-01", tmp_path)
    assert out["status"] == "recorded"
    assert out["issued_at"] == row["issued_at"]
    assert out["historical_replay_eligible"] is False


@pytest.mark.parametrize("field,bad", [("issued_at", "yesterday"),
    ("issued_at", "2026-07-02T04:00:00"), ("model_fit_asof", "2026-07-03"),
    ("model_method", "unknown"), ("source_basis", "fully_pit")])
def test_hmm_issuance_does_not_accept_false_provenance(tmp_path, field, bad):
    row = {**_saved_hmm_row(), "issued_at": "2026-07-02T04:00:00+00:00",
           "model_fit_asof": "2026-07-01", "model_method": "quad_supervised_gaussian_hmm.v1",
           "source_basis": "regime_history_vintages_unverified"}
    row[field] = bad
    _write_hmm_test_ledger(tmp_path, [row])
    out = R.read_hmm_issuance("2026-07-01", tmp_path)
    assert out["status"] == "invalid_record"
    assert out["historical_replay_eligible"] is False


def _stub_hmm_accrual(tmp_path, monkeypatch, asof="2026-07-01"):
    root = tmp_path / "regime"
    root.mkdir(exist_ok=True)
    frame = pd.DataFrame(index=pd.DatetimeIndex([asof]))
    frame.to_parquet(root / "regime_history.parquet")
    row = _saved_hmm_row(asof)
    monkeypatch.setattr(R, "_causal_filtered_pquad", lambda data: {
        "asof": asof, "modal_quad": row["pred_modal_quad"], "model_fit_asof": asof,
        "regime_probs_filtered": row["p_quad_filtered"]})


@pytest.mark.parametrize("case", ["old-duplicate", "regressed", "corrupt", "duplicate-ledger"])
def test_hmm_accrual_does_not_reissue_or_repair_history(tmp_path, monkeypatch, case):
    rows = [_saved_hmm_row("2026-07-01"), _saved_hmm_row("2026-07-03")]
    if case == "duplicate-ledger": rows.append(_saved_hmm_row("2026-07-03"))
    p = _write_hmm_test_ledger(tmp_path, rows)
    if case == "corrupt": p.write_text(p.read_text() + "{broken\n")
    date = {"old-duplicate": "2026-07-01", "regressed": "2026-07-02",
            "corrupt": "2026-07-06", "duplicate-ledger": "2026-07-06"}[case]
    _stub_hmm_accrual(tmp_path, monkeypatch, date)
    before = p.read_bytes()
    assert R.accrue_hmm_row(tmp_path) is False
    assert p.read_bytes() == before


def test_hmm_accrual_adds_metadata_without_rewriting_saved_predictions(tmp_path, monkeypatch):
    import json
    from datetime import datetime, timezone
    p = _write_hmm_test_ledger(tmp_path, [_saved_hmm_row("2026-07-01")])
    before = p.read_bytes()
    _stub_hmm_accrual(tmp_path, monkeypatch, "2026-07-02")
    started = datetime.now(timezone.utc)
    assert R.accrue_hmm_row(tmp_path) is True
    assert p.read_bytes().startswith(before)
    rows = [json.loads(line) for line in p.read_text().splitlines()]
    issued = datetime.fromisoformat(rows[-1]["issued_at"])
    assert started <= issued <= datetime.now(timezone.utc)
    assert rows[-1]["model_fit_asof"] == "2026-07-02"
    assert rows[-1]["model_method"] == "quad_supervised_gaussian_hmm.v1"
    assert rows[-1]["source_basis"] == "regime_history_vintages_unverified"
    assert R.read_hmm_issuance("2026-07-02", tmp_path)["status"] == "recorded"
    saved = p.read_bytes()
    assert R.accrue_hmm_row(tmp_path) is False
    assert p.read_bytes() == saved


def test_hmm_accrual_refuses_unterminated_ledger(tmp_path, monkeypatch):
    p = _write_hmm_test_ledger(tmp_path, [_saved_hmm_row()])
    p.write_bytes(p.read_bytes().rstrip(b"\n"))
    before = p.read_bytes()
    _stub_hmm_accrual(tmp_path, monkeypatch, "2026-07-02")
    assert R.accrue_hmm_row(tmp_path) is False
    assert p.read_bytes() == before


@pytest.mark.parametrize("case", ["wrong-cutoff", "future-date", "invalid-probability"])
def test_hmm_accrual_never_appends_a_record_its_reader_would_refuse(tmp_path, monkeypatch, case):
    from datetime import datetime, timedelta, timezone
    asof = "2026-07-02"
    if case == "future-date":
        asof = (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()
    p = _write_hmm_test_ledger(tmp_path, [_saved_hmm_row("2026-07-01")])
    _stub_hmm_accrual(tmp_path, monkeypatch, asof)
    prediction = {"asof": asof, "modal_quad": "Q1", "model_fit_asof": asof,
                  "regime_probs_filtered": _saved_hmm_row()["p_quad_filtered"]}
    if case == "wrong-cutoff": prediction["model_fit_asof"] = "2026-07-03"
    if case == "invalid-probability": prediction["regime_probs_filtered"]["Q1"] = .5
    monkeypatch.setattr(R, "_causal_filtered_pquad", lambda data: prediction)
    before = p.read_bytes()
    assert R.accrue_hmm_row(tmp_path) is False
    assert p.read_bytes() == before


@pytest.mark.parametrize("oversized", [10**400, -(10**400)], ids=["huge-positive", "huge-negative"])
def test_hmm_oversized_integer_refuses_in_reader_and_append(tmp_path, monkeypatch, oversized):
    row = _saved_hmm_row()
    row["p_quad_filtered"]["Q1"] = oversized
    p = _write_hmm_test_ledger(tmp_path, [row])
    before = p.read_bytes()
    out = R.read_hmm_issuance(row["asof"], tmp_path)
    assert out["status"] == "invalid_record"
    assert out["recorded_prediction"] is None
    _stub_hmm_accrual(tmp_path, monkeypatch, "2026-07-02")
    assert R.accrue_hmm_row(tmp_path) is False
    assert p.read_bytes() == before


@pytest.mark.parametrize("values,valid", [
    ((.2499, .2499, .25, .25), True),
    ((.2501, .2501, .25, .25), True),
    ((.2499, .2499, .2499, .25), False),
    ((.2501, .2501, .2501, .25), False),
])
def test_hmm_reader_preserves_exact_rounding_boundary(tmp_path, values, valid):
    row = _saved_hmm_row()
    row["p_quad_filtered"] = dict(zip(("Q1", "Q2", "Q3", "Q4"), values))
    row["pred_modal_quad"] = max(row["p_quad_filtered"], key=row["p_quad_filtered"].get)
    p = _write_hmm_test_ledger(tmp_path, [row])
    before = p.read_bytes()
    out = R.read_hmm_issuance(row["asof"], tmp_path)
    assert out["status"] == ("legacy_record" if valid else "invalid_record")
    assert out["recorded_prediction"] == (row["p_quad_filtered"] if valid else None)
    assert p.read_bytes() == before


def test_hmm_history_suites_are_named_by_real_ci_run_steps():
    from scripts import audit_unrun_tests as audit
    blob = audit._workflow_blob()
    for name in ("test_regime_one.py", "test_regime_hmm.py",
                 "test_validate_regime_fwd.py", "test_perception_contracts.py"):
        assert audit._named_by_a_run_step("tests/" + name, blob, frozenset()), name


def test_hmm_history_suites_are_in_the_code_gate_not_only_data_health():
    from pathlib import Path
    from scripts import audit_unrun_tests as audit
    from scripts.run_ci_pack import load_legacy_jobs
    manifest = Path(__file__).resolve().parents[1] / ".github/ci/legacy-jobs.yml"
    jobs = load_legacy_jobs(manifest, gate="code")
    for name in ("test_regime_one.py", "test_regime_hmm.py",
                 "test_validate_regime_fwd.py", "test_perception_contracts.py"):
        owners = [job for job in jobs if any(
            audit._named_by_a_run_step("tests/" + name, step.get("run", ""), frozenset())
            for step in job.definition.get("steps", []))]
        assert len(owners) == 1, (name, [job.job_id for job in owners])
        installs = [step.get("run", "") for step in owners[0].definition["steps"]
                    if "pip install" in step.get("run", "")]
        assert len(installs) == 1 and "hmmlearn==0.3.3" in installs[0]


# W0 native issuance receipts: no horizon forecasting or retrospective certification.
def _hmm_input_evidence_row():
    row = {**_saved_hmm_row(), "issued_at": "2026-07-02T04:00:05+00:00",
           "model_fit_asof": "2026-07-01", "model_method": "quad_supervised_gaussian_hmm.v1",
           "source_basis": "regime_history_vintages_unverified",
           "record_assembled_at": "2026-07-02T04:00:04+00:00"}
    row["input_evidence"] = {
        "schema": "regime_hmm_input_evidence.v1",
        "source_path": "regime/regime_history.parquet", "content_sha256": "a" * 64,
        "byte_count": 2048, "decoded_row_count": 390,
        "decoded_first_asof": "2025-01-01", "decoded_last_asof": "2026-07-01",
        "read_started_at": "2026-07-02T04:00:00+00:00",
        "read_completed_at": "2026-07-02T04:00:01+00:00",
        "source_vintages_verified": False,
    }
    row["fit"] = {"started_at": "2026-07-02T04:00:02+00:00",
                  "completed_at": "2026-07-02T04:00:03+00:00",
                  "model_fit_asof": row["asof"], "model_method": row["model_method"]}
    return row


def test_engine_run_regime_one_data_root_reads_existing_ledgers(tmp_path):
    """Use the real runtime's argument expression and the real status consumer."""
    import ast
    import json
    from pathlib import Path
    source = Path(__file__).resolve().parents[1] / "engine" / "run.py"
    calls = [node for node in ast.walk(ast.parse(source.read_text()))
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
             and isinstance(node.func.value, ast.Name)
             and node.func.value.id == "_r1" and node.func.attr == "compute"]
    assert len(calls) == 1
    expr = next(k.value for k in calls[0].keywords if k.arg == "data_dir")
    actual_root = eval(compile(ast.Expression(expr), str(source), "eval"),
                       {"p": tmp_path / "regime"})
    _write_hmm_test_ledger(tmp_path, [_saved_hmm_row(), _saved_hmm_row("2026-07-02")])
    (tmp_path / "regime" / "base_effect_fwd.jsonl").write_text(json.dumps({
        "asof": "2026-07-01", "realized_growth_2d_at_63d": None,
        "realized_infl_2d_at_63d": None}) + "\n")
    out = R._forward_read(pd.DataFrame(columns=["growth_score", "inflation_score"]), None, actual_root)
    assert out["p_quad"]["graded"]["n"] == 2
    assert out["p_quad"]["graded"]["n_matured"] == 0
    assert out["base_effect"]["graded"]["n"] == 1
    assert not (tmp_path / "regime" / "regime").exists()


def test_hmm_same_byte_native_issuance_and_reader(tmp_path, monkeypatch):
    """Real Parquet + real native HMM; replace the path after the owner's read."""
    import hashlib
    import io
    import json
    from datetime import datetime, timezone
    frame = _synthetic_scores(block=140, cycles=1)
    expected = R._causal_filtered_pquad(frame)
    assert expected is not None
    ledger = _write_hmm_test_ledger(tmp_path, [_saved_hmm_row("2004-12-31")])
    prior = ledger.read_bytes()
    history = tmp_path / "regime" / "regime_history.parquet"
    frame.to_parquet(history)
    original = history.read_bytes()
    native_decode = pd.read_parquet
    seen = []

    def replace_then_decode(source, *args, **kwargs):
        seen.append(source)
        history.write_bytes(b"changed-after-owner-read")
        return native_decode(source, *args, **kwargs)

    monkeypatch.setattr(pd, "read_parquet", replace_then_decode)
    started = datetime.now(timezone.utc)
    assert R.accrue_hmm_row(tmp_path) is True
    assert len(seen) == 1 and isinstance(seen[0], io.BytesIO)
    assert seen[0].getvalue() == original
    assert ledger.read_bytes().startswith(prior)
    row = json.loads(ledger.read_text().splitlines()[-1])
    evidence = row["input_evidence"]
    assert evidence["schema"] == "regime_hmm_input_evidence.v1"
    assert evidence["source_path"] == "regime/regime_history.parquet"
    assert evidence["content_sha256"] == hashlib.sha256(original).hexdigest()
    assert evidence["byte_count"] == len(original)
    assert evidence["decoded_row_count"] == len(frame)
    assert evidence["decoded_first_asof"] == str(frame.index.min().date())
    assert evidence["decoded_last_asof"] == str(frame.index.max().date()) == row["asof"]
    assert row["p_quad_filtered"] == expected["regime_probs_filtered"]
    assert row["pred_modal_quad"] == expected["modal_quad"]
    assert row["fit"]["model_fit_asof"] == row["model_fit_asof"] == row["asof"]
    assert row["fit"]["model_method"] == row["model_method"]
    observations = [evidence["read_started_at"], evidence["read_completed_at"],
                    row["fit"]["started_at"], row["fit"]["completed_at"],
                    row["record_assembled_at"], row["issued_at"]]
    clocks = [datetime.fromisoformat(x) for x in observations]
    assert started <= clocks[0] and clocks == sorted(clocks)
    assert clocks[-1] <= datetime.now(timezone.utc)
    assert all(x.utcoffset().total_seconds() == 0 for x in clocks)
    assert evidence["source_vintages_verified"] is False
    assert row["realized_quad_at_21d"] is None and "forecast" not in row

    def forbidden(*args, **kwargs):
        pytest.fail("the saved-evidence reader must neither refit nor decode parquet")

    monkeypatch.setattr(R, "_causal_filtered_pquad", forbidden)
    monkeypatch.setattr(pd, "read_parquet", forbidden)
    saved = ledger.read_bytes()
    out = R.read_hmm_issuance(row["asof"], tmp_path)
    assert out["status"] == "recorded"
    assert out["input_evidence_status"] == "recorded"
    assert out["input_evidence"] == evidence and out["fit"] == row["fit"]
    assert out["record_assembled_at"] == row["record_assembled_at"]
    assert out["recorded_prediction"] == expected["regime_probs_filtered"]
    assert out["source_vintages_verified"] is False
    assert out["historical_replay_eligible"] is False
    assert ledger.read_bytes() == saved


@pytest.mark.parametrize("case", ["source-after-fit", "nat-index", "duplicate-index", "empty-frame"])
def test_hmm_input_evidence_refuses_ambiguous_decoded_cutoff(tmp_path, monkeypatch, case):
    _stub_hmm_accrual(tmp_path, monkeypatch)
    path = tmp_path / "regime" / "regime_history.parquet"
    indices = {
        "source-after-fit": ["2026-07-01", "2026-07-02"],
        "nat-index": ["2026-07-01", None],
        "duplicate-index": ["2026-07-01", "2026-07-01"],
        "empty-frame": [],
    }
    pd.DataFrame(index=pd.DatetimeIndex(indices[case])).to_parquet(path)
    ledger = _write_hmm_test_ledger(tmp_path, [_saved_hmm_row("2026-06-30")])
    before = ledger.read_bytes()
    assert R.accrue_hmm_row(tmp_path) is False
    assert ledger.read_bytes() == before


@pytest.mark.parametrize("position", [1, 2, 3, 4, 5])
def test_hmm_input_evidence_refuses_clock_regression(tmp_path, monkeypatch, position):
    from datetime import datetime, timedelta, timezone
    _stub_hmm_accrual(tmp_path, monkeypatch)
    origin = datetime(2026, 7, 2, 4, tzinfo=timezone.utc)
    clocks = [origin + timedelta(seconds=i) for i in range(6)]
    clocks[position] = clocks[position - 1] - timedelta(microseconds=1)
    iterator = iter(clocks)
    monkeypatch.setattr(R, "_hmm_utc_now", lambda: next(iterator), raising=False)
    ledger = _write_hmm_test_ledger(tmp_path, [_saved_hmm_row("2026-06-30")])
    before = ledger.read_bytes()
    assert R.accrue_hmm_row(tmp_path) is False
    assert ledger.read_bytes() == before


@pytest.mark.parametrize("field,value", [
    ("input_evidence.schema", "unknown"),
    ("input_evidence.source_path", "other/regime_history.parquet"),
    ("input_evidence.content_sha256", "not-a-digest"),
    ("input_evidence.byte_count", 0),
    ("input_evidence.byte_count", True),
    ("input_evidence.decoded_row_count", -1),
    ("input_evidence.decoded_row_count", True),
    ("input_evidence.decoded_first_asof", "2026-07-03"),
    ("input_evidence.decoded_last_asof", "2026-07-02"),
    ("input_evidence.read_started_at", "2026-07-02T04:00:02+00:00"),
    ("input_evidence.read_completed_at", "2026-07-02T04:00:04+00:00"),
    ("input_evidence.source_vintages_verified", True),
    ("fit.started_at", "2026-07-02T04:00:00+00:00"),
    ("fit.completed_at", "2026-07-02T04:00:01+00:00"),
    ("fit.model_fit_asof", "2026-07-02"),
    ("fit.model_method", "unknown"),
    ("record_assembled_at", "2026-07-02T04:00:02+00:00"),
    ("issued_at", "2026-07-02T04:00:03+00:00"),
    ("fit.completed_at", "2026-07-02T04:00:03"),
    ("fit.completed_at", "2026-07-02T04:00:03+01:00"),
])
def test_hmm_input_evidence_reader_refuses_inconsistent_receipts(tmp_path, field, value):
    row = _hmm_input_evidence_row()
    keys = field.split(".")
    target = row if len(keys) == 1 else row[keys[0]]
    target[keys[-1]] = value
    ledger = _write_hmm_test_ledger(tmp_path, [row])
    before = ledger.read_bytes()
    out = R.read_hmm_issuance(row["asof"], tmp_path)
    assert out["status"] == "invalid_record"
    assert out["recorded_prediction"] is None
    assert out["historical_replay_eligible"] is False
    assert ledger.read_bytes() == before


@pytest.mark.parametrize("missing", ["fit", "input_evidence", "record_assembled_at"])
def test_hmm_input_evidence_reader_refuses_partial_receipt(tmp_path, missing):
    row = _hmm_input_evidence_row()
    del row[missing]
    _write_hmm_test_ledger(tmp_path, [row])
    assert R.read_hmm_issuance(row["asof"], tmp_path)["status"] == "invalid_record"


def test_hmm_input_evidence_reader_preserves_metadata_light_records(tmp_path):
    legacy = _saved_hmm_row()
    metadata_only = {**_saved_hmm_row("2026-07-02"),
                     "issued_at": "2026-07-03T04:00:00+00:00",
                     "model_fit_asof": "2026-07-02",
                     "model_method": "quad_supervised_gaussian_hmm.v1",
                     "source_basis": "regime_history_vintages_unverified"}
    ledger = _write_hmm_test_ledger(tmp_path, [legacy, metadata_only])
    before = ledger.read_bytes()
    for row, status in [(legacy, "legacy_record"), (metadata_only, "recorded")]:
        out = R.read_hmm_issuance(row["asof"], tmp_path)
        assert out["status"] == status
        assert out["input_evidence_status"] == "not_recorded"
        assert out["input_evidence"] is None and out["fit"] is None
        assert out["source_vintages_verified"] is False
        assert out["historical_replay_eligible"] is False
    assert ledger.read_bytes() == before


def test_hmm_input_evidence_corrupt_existing_receipt_blocks_append(tmp_path, monkeypatch):
    row = _hmm_input_evidence_row()
    row["input_evidence"]["decoded_last_asof"] = "2026-07-03"
    ledger = _write_hmm_test_ledger(tmp_path, [row])
    before = ledger.read_bytes()
    _stub_hmm_accrual(tmp_path, monkeypatch, "2026-07-02")
    assert R.accrue_hmm_row(tmp_path) is False
    assert ledger.read_bytes() == before

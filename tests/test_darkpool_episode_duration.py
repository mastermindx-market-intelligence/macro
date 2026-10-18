"""Q11 reference filter: one test per brief requirement (req1..req6) + no-silent-activation.

Hermetic: synthetic data on integer session indexes, fixed seeds, no repo files, no network,
no clock.
"""
from __future__ import annotations

import importlib
import inspect
import os
import types

import numpy as np
import pytest

import engine.darkpool_episode_duration as ed
from engine.darkpool_episode_duration import (
    DurationFilterParams,
    episodes_from_path,
    filter_path,
    fit_emission_params,
    onset_indicator,
    robust_activity_z,
    update_detection_records,
)

P = DurationFilterParams()  # nu=4, scale=1
TAU = 0.6


def _baseline(n: int = 300, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return np.exp(np.log(0.45) + 0.12 * rng.standard_t(4, n))


def _z(v: np.ndarray) -> np.ndarray:
    return robust_activity_z(v)


# ---------------------------------------------------------------- req1
def test_req1_isolated_spike_and_sustained_shift_have_distinguishable_diagnostics():
    spike = _baseline()
    spike[200] *= 3.0
    shift = _baseline()
    shift[200:240] *= 1.5
    ps, pt = filter_path(_z(spike), P), filter_path(_z(shift), P)
    # the spike is maximally surprising at the time ...
    assert ps.surprise[200] > np.nanpercentile(ps.surprise[60:199], 99)
    # ... but leaves no regime: probability stays low and no episode opens
    assert ps.p_elevated[200:206].max() < 0.2
    assert not any(200 <= e.detected_at < 215 for e in episodes_from_path(ps, tau_on=TAU))
    # the sustained shift builds probability and an ageing duration posterior
    assert pt.p_elevated[210] > 0.9
    assert pt.exp_duration[215] > pt.exp_duration[210] > 5
    assert pt.p_duration_ge5[212] > 0.8
    ev = [e for e in episodes_from_path(pt, tau_on=TAU) if 200 <= e.detected_at < 215]
    assert len(ev) == 1


# ---------------------------------------------------------------- req2
def test_req2_detection_is_stamped_when_knowable_and_never_backdated():
    v = _baseline()
    v[200:240] *= 1.5
    x = _z(v)
    full = filter_path(x, P)
    for t in (150, 201, 205, 230):  # prefix invariance: output at t uses only x[:t+1]
        pre = filter_path(x[: t + 1], P)
        assert pre.p_elevated[-1] == pytest.approx(full.p_elevated[t], abs=1e-12)
        assert pre.exp_duration[-1] == pytest.approx(full.exp_duration[t], abs=1e-9)
    eps = episodes_from_path(full, tau_on=TAU)
    ev = [e for e in eps if 200 <= e.detected_at < 240][0]
    assert ev.retro_onset_at_detection <= ev.detected_at
    ind = onset_indicator(eps, len(x))
    assert ind[ev.detected_at] and (ev.retro_onset_at_detection == ev.detected_at or not ind[ev.retro_onset_at_detection])

    # revision: vintage A (as-of 210) shows no elevation; vintage B (as-of 211) restates
    # sessions 195..211 upward, so B alone would have alarmed before 211.
    a = _baseline()
    recs = update_detection_records([], asof=210, x_asof=_z(a[:211]), params=P, tau_on=TAU)
    assert not any(r["event"] == "detected" and r["detected_at"] > 150 for r in recs)
    b = a.copy()
    b[195:212] *= 1.5
    recs_b = update_detection_records(recs, asof=211, x_asof=_z(b[:212]), params=P, tau_on=TAU)
    assert recs_b[: len(recs)] == recs  # append-only
    new = [r for r in recs_b[len(recs):] if r["event"] == "detected"]
    assert len(new) == 1
    assert new[0]["detected_at"] == 211  # stamped when this run first saw it
    assert new[0]["backfilled_detection_index"] < 211  # what a backdated system would claim
    assert new[0]["retro_onset_estimate"] <= new[0]["detected_at"]


def test_req2_new_episode_while_record_open_closes_old_and_stamps_new():
    # Two separate shifts; the first episode ends and the second begins between two runs, so
    # no run ever observes the first episode closed. The open record must still be closed.
    v = _baseline(n=400)
    v[200:230] *= 1.5
    v[300:340] *= 1.5
    x = _z(v)
    recs = update_detection_records([], asof=215, x_asof=x[:216], params=P, tau_on=TAU)
    assert [r["event"] for r in recs] == ["detected"] and recs[0]["detected_at"] == 215
    # same episode on the next run: nothing appended
    assert update_detection_records(recs, asof=216, x_asof=x[:217], params=P, tau_on=TAU) == recs
    recs2 = update_detection_records(recs, asof=320, x_asof=x[:321], params=P, tau_on=TAU)
    assert recs2[: len(recs)] == recs  # append-only
    added = recs2[len(recs):]
    assert [r["event"] for r in added] == ["closed", "detected"]
    assert added[0]["episode_seq"] == 1 and added[0]["closed_at"] == 320
    assert added[1]["episode_seq"] == 2 and added[1]["detected_at"] == 320
    assert 215 < added[1]["backfilled_detection_index"] < 320
    assert added[1]["retro_onset_estimate"] <= added[1]["detected_at"]


# ---------------------------------------------------------------- req3
def test_req3_missing_sessions_and_revisions_cannot_create_persistence():
    v = _baseline()
    v[200:206] *= 1.6
    x = _z(v)
    # (a) missing sessions are skipped, never interpolated, in the input transform
    vm = v.copy()
    vm[206:216] = np.nan
    xm = _z(vm)
    assert np.all(np.isnan(xm[206:216]))
    keep = np.isfinite(vm)
    assert np.allclose(xm[keep], robust_activity_z(vm[keep])[: keep.sum()], equal_nan=True)
    # (b) a gap is a prediction-only step: an above-stationary probability is non-increasing
    pm = filter_path(xm, P)
    stationary = P.enter_hazard * P.mean_duration
    seg = pm.p_elevated[205:216]
    assert seg[0] > stationary
    assert np.all(np.diff(seg) <= 1e-12)
    # (c) a gap longer than max_gap resets the filter and closes the episode
    assert pm.gap_reset[216]
    eps = episodes_from_path(pm, tau_on=0.5)
    gap_ep = [e for e in eps if 200 <= e.detected_at < 206]
    assert gap_ep and gap_ep[0].closed_by in {"gap_reset", "hysteresis"} and gap_ep[0].end_at <= 216
    # (d) observed-evidence count excludes missing sessions
    vs = _baseline()
    vs[200:240] *= 1.5
    vs2 = vs.copy()
    vs2[[210, 215, 220, 225]] = np.nan  # short holes (< max_gap)
    e1 = [e for e in episodes_from_path(filter_path(_z(vs), P), tau_on=TAU) if 200 <= e.detected_at < 215][0]
    e2 = [e for e in episodes_from_path(filter_path(_z(vs2), P), tau_on=TAU) if 200 <= e.detected_at < 215][0]
    assert e2.n_observed <= e1.n_observed - 4 + 1


# ---------------------------------------------------------------- req4
def test_req4_heavy_tailed_shocks_do_not_force_regime_resets():
    shocks_in = [215, 235, 255, 275]   # extreme negative shocks inside a sustained regime
    shocks_out = [80, 120, 160, 340, 370]  # extreme positive shocks in the normal regime
    extra = {4.0: 0, 1e6: 0}
    spurious = {4.0: 0, 1e6: 0}
    for seed in (11, 12, 13):
        rng = np.random.default_rng(seed)
        clean = 0.9 * rng.standard_t(4, 400)
        clean[200:300] += 1.2
        shocked = clean.copy()
        shocked[shocks_in] = -9.0
        shocked[shocks_out] = 9.0
        for nu in (4.0, 1e6):
            prm = DurationFilterParams(nu=nu, scale=0.9)
            e0 = episodes_from_path(filter_path(clean, prm), tau_on=TAU)
            e1 = episodes_from_path(filter_path(shocked, prm), tau_on=TAU)
            in0 = [e for e in e0 if 195 <= e.detected_at < 300]
            in1 = [e for e in e1 if 195 <= e.detected_at < 300]
            extra[nu] += len(in1) - len(in0)  # regime resets caused only by the shocks
            spurious[nu] += sum(1 for e in e1 if any(0 <= e.detected_at - s <= 2 for s in shocks_out))
    # heavy tails: one-session shocks almost never split a regime and never open one
    assert extra[4.0] <= 1
    assert spurious[4.0] == 0
    # the Gaussian control shows the failure the heavy tail removes
    assert extra[1e6] >= 5
    assert spurious[1e6] >= 5


# ---------------------------------------------------------------- req5
def test_req5_model_choices_are_not_tuned_to_return_outcomes():
    # no price/return input exists anywhere in the public API
    banned = {"ret", "return", "returns", "price", "close", "pnl", "outcome", "forward"}
    for name in ed.__all__:
        obj = getattr(ed, name)
        if callable(obj) and not isinstance(obj, type):
            params = set(inspect.signature(obj).parameters)
            assert not any(any(b in p.lower() for b in banned) for p in params), (name, params)
    fields = set(DurationFilterParams.__dataclass_fields__)
    assert not any(any(b in f.lower() for b in banned) for f in fields)
    assert ed.CONTRACT["uses_returns_or_prices"] is False
    # the only fitted quantities are a pure deterministic function of the training values
    rng = np.random.default_rng(3)
    xtr = 0.8 * rng.standard_t(5, 5000)
    a, b = fit_emission_params(xtr), fit_emission_params(xtr.copy())
    assert a == b
    assert 2.1 <= a[0] <= 50 and a[1] > 0
    # the hazards and duration law are fixed constants, not fitted
    d = DurationFilterParams()
    assert (d.enter_hazard, d.mean_duration, d.duration_shape) == (1.0 / 250.0, 20.0, 2)


# ---------------------------------------------------------------- req6
def test_req6_existing_events_labels_policy_and_alert_owners_unchanged():
    assert ed.CONTRACT["modifies_owners"] == ()
    assert ed.CONTRACT["consumers"] == ()
    for v in vars(ed).values():  # imports no incumbent owner module
        if isinstance(v, types.ModuleType):
            assert not v.__name__.startswith("engine."), v.__name__
            assert "darkpool" not in v.__name__ and "alert" not in v.__name__
    # detection records are plain in-memory dicts; nothing is persisted or delivered
    v = _baseline()
    v[200:240] *= 1.5
    recs = update_detection_records([], asof=239, x_asof=_z(v[:240]), params=P, tau_on=TAU)
    assert all(isinstance(r, dict) for r in recs)
    assert all(set(r) <= {"event", "episode_seq", "detected_at", "retro_onset_estimate", "p_elevated",
                          "backfilled_detection_index", "closed_at"} for r in recs)


# ---------------------------------------------------------------- no silent activation
def test_no_silent_activation_module_contract(tmp_path, monkeypatch):
    work = tmp_path / "cwd"
    work.mkdir()
    monkeypatch.chdir(work)
    mod = importlib.reload(ed)
    monkeypatch.chdir(tmp_path)
    try:
        work.rmdir()  # import performs no I/O: fails with ENOTEMPTY if anything was written
    except OSError as exc:
        pytest.fail(f"import wrote into its working directory: {exc}")
    assert mod.RESEARCH_ONLY is True
    assert (mod.__doc__ or "").startswith("RESEARCH REFERENCE — NOT WIRED")
    st = mod.activation_status()
    assert st["research_only"] is True
    assert st["wired"] is False and st["emits_alerts"] is False
    assert st["writes_files"] is False and st["persists_records"] is False

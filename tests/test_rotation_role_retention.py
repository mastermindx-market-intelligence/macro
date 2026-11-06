"""T09 (lane LR-T09-1): transition ROLES, prior-leader identity, stale as_of and
valid-empty corrections hold through the ACTUAL rotation consumers.

Tests only — no engine change. Every passing test names, in its leading comment,
the exact one-line engine mutation that would make it fail; each such mutation
was applied locally, run to FAIL, and reverted with git checkout (never
committed).  The two xfail(strict) tests pin deterministically reproducing
engine defects (DEFECT A22-CTX, DEFECT A23) — the un-mutated engine already
fails them, and once a fix lands they XPASS-fail the run until the marker is
removed.

Consumers driven (no new evaluator/store/schedule/candidate/ranking/alert):
  engine/rotation_events.py                  step_pairs, emit_v2, to_alerts,
                                             step_cross_pairs, closed_recent,
                                             read_ledger_history, run_nightly,
                                             early_rotation_context
  scripts/build_risk_envelope.py             _rotation_read / _compact_early_context
  engine/risk_envelope.py                    _rotation_context
  engine/neuralweb/world_state.py            _compose_rotation_events (lobe)
  engine/neuralweb/rotation_risk_context.py  compact_context / render_context
"""
from __future__ import annotations

import copy
import json
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import pytest

from engine import rotation_events as RE
from engine.oracle import ratio_lens as RL
from engine.risk_envelope import SourceRead, _rotation_context, compose_envelope
from engine.neuralweb import rotation_risk_context as rc
from engine.neuralweb import world_state as ws
from scripts.build_risk_envelope import _rotation_read
from tests.test_rotation_events import _blowoff_leg, _turn_leg
from tests.test_rotation_early_context import (
    ASOF,
    context as early_context_from,
    levels,
    pair,
    receipt,
)

SESSION = ASOF  # 2026-10-06, a real NY session
NOW = datetime(2026, 10, 8, 22, tzinfo=timezone.utc)

_LEG_NAMES = {
    "memory": ("Memory", "存储", "secondary"),
    "mag7": ("Mag 7", "七巨头", "primary"),
}


def _sector_cfg(leg_keys):
    return {
        "key": "xlk", "etf": "XLK", "name_en": "Technology", "name_zh": "科技",
        "legs": [{"key": k, "tier": _LEG_NAMES[k][2], "name_en": _LEG_NAMES[k][0],
                  "name_zh": _LEG_NAMES[k][1]} for k in leg_keys],
    }


def _sectors(legs_map):
    closes = list(legs_map.values())
    return {"xlk": {"cfg": _sector_cfg(tuple(legs_map)), "etf_close": closes[0],
                    "legs": dict(legs_map), "leg_meta": {}}}


def _aligned_pair():
    a, b = _blowoff_leg(), _turn_leg()
    n = min(len(a), len(b))
    a, b = a.iloc[-n:], b.iloc[-n:]
    b.index = a.index
    return a, b


def _cross_universe():
    return {
        "bench": {"key": "spy"},
        "series": [
            {"key": "xlk_etf", "kind": "etf", "ticker": "XLK", "label_en": "Technology",
             "label_zh": "科技", "sector": "xlk"},
            {"key": "xlu_etf", "kind": "etf", "ticker": "XLU", "label_en": "Utilities",
             "label_zh": "公用事业", "sector": "xlu"},
        ],
        "pairs": [{"id": "xlk_etf->xlu_etf", "donor": "xlk_etf", "receiver": "xlu_etf",
                   "tier": "primary"}],
        "contagion_pairs": [], "complexes": [], "velocity_series": [],
    }


def _cross_closes():
    n = 306
    spy = pd.Series([100.0] * n, index=pd.bdate_range("2024-01-02", periods=n), dtype=float)
    d, r = _blowoff_leg(), _turn_leg()
    m = min(len(d), len(r), n)
    d, r, spy = d.iloc[-m:], r.iloc[-m:], spy.iloc[-m:]
    r.index = spy.index = d.index
    return {"spy": spy, "xlk_etf": d, "xlu_etf": r}


def _v1_base(active, created):
    return {
        "schema": RE.SCHEMA, "ok": True, "as_of": SESSION,
        "generated_utc": "2026-10-06 05:00 UTC",
        "authority": {"tier": "display", "may_rank": False, "may_gate": False,
                      "may_size": False, "may_escalate": False},
        "params": {}, "n_pairs_scanned": 0,
        "active": active, "created_tonight": created,
        "closed_tonight": [], "coldstart": False,
    }


def _rotation_doc(early_ctx):
    return {
        "schema": "rotation_events.v1", "as_of": SESSION,
        "generated_utc": "2026-10-06 05:00 UTC",
        "active": [], "created_tonight": [],
        "early_context": copy.deepcopy(early_ctx),
    }


def _write(root, rel, payload):
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload))


def _measured_and_hazard():
    return [
        SourceRead(source_id="market-state-latest", role="measured_state",
                   state="RISK_ON", score=75, as_of=SESSION, required=True),
        SourceRead(source_id="leadership-crack-latest", role="hazard_evidence",
                   state="HEALTHY", hazard_stage="NONE", as_of=SESSION, required=True),
    ]


# ---------------------------------------------------------------- A22: roles ----

def test_a22_reversed_intra_sector_evidence_never_fires_the_registered_direction():
    # MUTATION (proved: applied → FAIL → reverted): engine/rotation_events.py,
    # step_pairs events_active row: `"from_leg": {"key": out_key,` → `"key": in_key,`.
    # Registered spec: out=memory, in=mag7. Evidence reversed (memory turns, mag7
    # crashes): the registered direction must stay silent while the correctly
    # oriented ordered pair carries the evidence identities verbatim.
    a, b = _aligned_pair()                      # a crashes, b turns
    cfg = _sector_cfg(("memory", "mag7"))
    reversed_evidence = {"xlk": {"cfg": cfg, "etf_close": b,
                                 "legs": {"memory": b, "mag7": a}, "leg_meta": {}}}
    state, active, created, closed = RE.step_pairs(reversed_evidence, {})
    assert created == ["xlk:mag7->memory"]      # the reversed registration stays silent
    assert "xlk:memory->mag7" not in created
    assert all(e["id"] != "xlk:memory->mag7" for e in active)
    fired = next(e for e in active if e["id"] == "xlk:mag7->memory")
    assert fired["from_leg"]["key"] == "mag7"   # the crashing leg is the outgoing leg
    assert fired["to_leg"]["key"] == "memory"   # the turning leg is the incoming leg
    payload = RE.emit_v2(_v1_base(active, created), [], [])
    assert payload["active"][0]["from_leg"]["key"] == "mag7"
    alerts = RE.to_alerts(payload)
    assert len(alerts) == 1
    assert "Mag 7 → Memory" in alerts[0]["headline"]
    assert alerts[0]["context"]["receipts"]["blowoff"]["drawdown_pct"] > 0


def test_a22_reversed_cross_evidence_never_enters_candidates_or_events():
    # MUTATION (proved: applied → FAIL → reverted): engine/rotation_events.py,
    # step_cross_pairs: `receipts = evaluate_cross(d_cl, r_cl, bench,` →
    # `receipts = evaluate_cross(r_cl, d_cl, bench,`.
    universe = _cross_universe()
    closes = _cross_closes()
    bench = closes["spy"]
    p2 = {"confirm_days": 2}
    # donor key carries the TURN series, receiver key carries the BLOWOFF series
    reversed_closes = {"spy": closes["spy"],
                       "xlk_etf": closes["xlu_etf"], "xlu_etf": closes["xlk_etf"]}
    state: dict = {}
    for _ in range(2):
        state, events, created, closed = RE.step_cross_pairs(
            universe, reversed_closes, bench, state, p2=p2)
    assert created == []
    assert state.get("candidates") == {}
    assert state.get("active") == {}
    assert all(e["id"] != "xlk_etf->xlu_etf" for e in events)
    # positive control: the same evaluator fires on the correctly oriented series
    st1, _, _, _ = RE.step_cross_pairs(universe, closes, bench, {}, p2=p2)
    assert "xlk_etf->xlu_etf" in st1["candidates"]
    st2, ev2, cr2, _ = RE.step_cross_pairs(universe, closes, bench, st1, p2=p2)
    assert cr2 == ["xlk_etf->xlu_etf"]
    assert any(e["id"] == "xlk_etf->xlu_etf" for e in ev2)


def test_a22_confirmed_cross_event_keeps_registered_donor_receiver_identities():
    # MUTATION (proved: applied → FAIL → reverted): engine/rotation_events.py,
    # step_cross_pairs promotion-night events_active row:
    # `"donor": {"key": donor_key,` → `"key": recv_key,`.
    universe = _cross_universe()
    closes = _cross_closes()
    bench = closes["spy"]
    p2 = {"confirm_days": 2}
    state: dict = {}
    for _ in range(2):
        state, ev2, cr2, closed = RE.step_cross_pairs(
            universe, closes, bench, state, p2=p2)
    assert cr2 == ["xlk_etf->xlu_etf"]
    ev = next(e for e in ev2 if e["id"] == "xlk_etf->xlu_etf")
    assert ev["donor"]["key"] == "xlk_etf"          # never swapped
    assert ev["receiver"]["key"] == "xlu_etf"
    assert ev["from_sector"] == "xlk" and ev["to_sector"] == "xlu"
    assert ev["event_type"] == "cross_handoff"
    payload = RE.emit_v2(_v1_base([], []), ev2, cr2, n_cross_pairs_scanned=1)
    assert payload["created_tonight"] == ["xlk_etf->xlu_etf"]
    assert payload["active"][0]["donor"]["key"] == "xlk_etf"
    alerts = RE.to_alerts(payload)
    assert len(alerts) == 1
    assert "Technology → Utilities" in alerts[0]["headline"]
    assert "Utilities → Technology" not in alerts[0]["headline"]


@pytest.mark.xfail(strict=True, reason=(
    "DEFECT A22-CTX: engine/rotation_events.py early_rotation_context (pair "
    "canonicalization key=(num, den), positive count at `if relative > 0`) accepts an "
    "orientation-flipped receipt whose numerator is the registered donor and counts it "
    "toward the receiver group's positive_2s, reporting DEFENSIVE_RELATIVE_STRENGTH "
    "from donor-side strength. Deterministic; no registry-direction check exists."))
def test_a22_flipped_receipt_numerator_donor_never_reports_receiver_group_positive():
    # The registered defensive pairs are (XLP, XLK) et al: num = the defensive
    # receiver leg, den = the donor complex. A receipt whose NUMERATOR is the
    # registered donor (XLK) must never read as a positive for the receiver group.
    # Mutation proof: N/A — the un-mutated engine already fails this test (the live
    # defect IS the discriminator). Verified deterministically on this base.
    flipped = receipt(group="defensive_sector", num_daily=.003, den_daily=.001,
                      num="XLK", den="XLP")
    out = early_context_from(flipped)
    assert out["coverage"]["groups"]["defensive_sector"]["positive_2s"] == 0
    assert out["state"] != "DEFENSIVE_RELATIVE_STRENGTH"


# ------------------------------------------------------------ A23: retention ----

@pytest.mark.xfail(strict=True, reason=(
    "DEFECT A23: engine/rotation_events.py step_pairs (active_out rebuild, ~L257-358) "
    "drops an active episode whose receiver leg is absent from tonight's sectors: the "
    "pair leaves state['active'] with NO closure row, no closed_tonight entry and no "
    "coverage trace; identity survives only in the prior night's raw ledger row. "
    "Deterministic."))
def test_a23_active_episode_is_not_silently_dropped_when_receiver_leg_leaves(
        tmp_path, monkeypatch):
    # Mutation proof: N/A — the un-mutated engine already fails the `retained`
    # assertion below (verified deterministically on this base).
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    a, b = _aligned_pair()
    night1 = RE.run_nightly(_sectors({"memory": a, "mag7": b}), tmp_path,
                            generated_utc="2026-10-05 05:00 UTC")
    assert night1["created_tonight"] == ["xlk:memory->mag7"]
    # tonight: the receiver leg (mag7) is absent from the current sectors
    night2 = RE.run_nightly(_sectors({"memory": a}), tmp_path,
                            generated_utc="2026-10-06 05:00 UTC")
    state2 = json.loads((tmp_path / "rotation_events" / "state.json").read_text())
    # the created row the writer DID keep still carries the original identity …
    hist = RE.read_ledger_history(tmp_path / "rotation_events" / "events.jsonl")
    assert [(r["native_id"], r["from_key"], r["to_key"]) for r in hist["rows"]] == [
        ("xlk:memory->mag7", "memory", "mag7")]
    # … and the episode itself must survive in a consumer-output form: active,
    # closed-with-reason, or an explicit coverage disclosure — never a silent drop.
    retained = (
        any(e["id"] == "xlk:memory->mag7" for e in night2["active"])
        or bool(state2.get("closed", {}).get("xlk:memory->mag7"))
        or any(c.get("pair_id") == "xlk:memory->mag7" for c in night2["closed_tonight"])
    )
    assert retained


def test_a23_recently_closed_episode_identity_survives_the_leg_leaving(
        tmp_path, monkeypatch):
    # MUTATION (proved: applied → FAIL → reverted): engine/rotation_events.py,
    # closed_recent: `if row.get("event") == "closed":` → `if False:`.
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    a, b = _aligned_pair()
    night1 = RE.run_nightly(_sectors({"memory": a, "mag7": b}), tmp_path,
                            generated_utc="2026-10-05 05:00 UTC")
    assert night1["created_tonight"] == ["xlk:memory->mag7"]
    state1 = json.loads((tmp_path / "rotation_events" / "state.json").read_text())
    started = state1["active"]["xlk:memory->mag7"]["started"]
    idx = pd.bdate_range(a.index[-1] + pd.Timedelta(days=1), periods=40)
    flat_a = pd.concat([a, pd.Series(float(a.iloc[-1]), index=idx)])
    flat_b = pd.concat([b, pd.Series(float(b.iloc[-1]), index=idx)])
    closed_row = None
    stamps: list[str] = []
    for k in range(RE.PARAMS["lapse_run"] + RE.PARAMS["ttl_sessions"] + 2):
        # real calendar dates: the old f"2026-10-{6 + k:02d}" minted 2026-10-32 once
        # k ran past the end of October, which run_nightly now rejects.
        stamp = (date(2026, 10, 6) + timedelta(days=k)).isoformat() + " 05:00 UTC"
        stamps.append(stamp)
        payload = RE.run_nightly(
            _sectors({"memory": flat_a.iloc[:len(a) + k + 1],
                      "mag7": flat_b.iloc[:len(b) + k + 1]}),
            tmp_path, generated_utc=stamp)
        if payload["closed_tonight"]:
            closed_row = payload["closed_tonight"][0]
            break
    assert closed_row is not None
    fmt = "%Y-%m-%d %H:%M UTC"
    assert stamps
    assert all(datetime.strptime(s, fmt).strftime(fmt) == s for s in stamps), (
        f"run_nightly was handed a non-canonical build stamp: {stamps}"
    )
    assert closed_row["reason"] in ("conditions_lapsed", "ttl", "ratio_slope_flipped")
    ledger = tmp_path / "rotation_events" / "events.jsonl"
    # tonight: the receiver leg is gone from the current list — the closure row must
    # still hand back the ORIGINAL identity (pair id, legs, start date)
    RE.run_nightly(_sectors({"memory": flat_a}), tmp_path,
                   generated_utc="2026-11-06 05:00 UTC")
    cr = RE.closed_recent(ledger, n_sessions=5)
    row = next(r for r in cr if r.get("pair_id") == "xlk:memory->mag7")
    assert row["from_leg"] == "memory" and row["to_leg"] == "mag7"
    assert row["started"] == started
    hist = RE.read_ledger_history(ledger)
    closed_rows = [r for r in hist["rows"] if r["row"]["event"] == "closed"]
    assert closed_rows
    assert closed_rows[-1]["from_key"] == "memory"
    assert closed_rows[-1]["to_key"] == "mag7"
    assert closed_rows[-1]["lifecycle_id"] == f"xlk:memory->mag7@{started}"
    # and it is never resurrected as a current positive
    state_now = json.loads((tmp_path / "rotation_events" / "state.json").read_text())
    assert "xlk:memory->mag7" not in state_now.get("active", {})


def test_a23_registered_pair_absent_from_receipts_is_disclosed_not_silently_dropped(
        tmp_path, monkeypatch):
    # MUTATION (proved: applied → FAIL → reverted): engine/rotation_events.py,
    # early_rotation_context: `out["coverage"]["missing_pair_ids"].append(row["pair_id"])`
    # → `pass`.
    (tmp_path / "oracle").mkdir()
    (tmp_path / "oracle" / "ratio_pairs.json").write_text(json.dumps(
        {"version": "test", "taxonomy": {},
         "pairs": [pair(), pair("WMT", "XLK", "retailer_context")]}))

    def load(sym, root):
        if sym == "WMT":
            return None
        return levels(daily=.003 if sym == "XLP" else .001)

    monkeypatch.setattr(RL, "_etf_close", load)
    result = RL.registered_short_horizon_context(tmp_path, as_of=ASOF)
    out = RE.early_rotation_context(result, as_of=ASOF)
    # the absent receiver's identity is disclosed, not dropped
    assert "wmt_vs_xlk" in out["coverage"]["missing_pair_ids"]
    assert "PARTIAL_PAIR_COVERAGE" in out["reason_codes"]
    assert out["coverage"]["groups"]["retailer_context"]["positive_2s"] == 0
    # the present pair still evaluates — the disclosure is per-pair, not a global null
    assert out["coverage"]["groups"]["defensive_sector"]["positive_2s"] == 1
    assert out["state"] == "DEFENSIVE_RELATIVE_STRENGTH"


# ------------------------------------------------- stale as_of never current ----

def test_stale_child_as_of_is_never_surfaced_as_current_by_any_consumer(tmp_path):
    # MUTATION (proved: applied → FAIL → reverted): scripts/build_risk_envelope.py,
    # _rotation_read: `as_of = early.get("as_of") if early else confirmed_asof` →
    # `as_of = confirmed_asof`.
    ctx = early_context_from(receipt(),
                             receipt("broadening_proxy", .003, .001, "IWM", "QQQ"))
    assert ctx["state"] == "MIXED_ROTATION"
    doc = _rotation_doc(ctx)
    doc["early_context"]["as_of"] = "2026-10-05"       # older session than expected
    src = _rotation_read(doc, SESSION, now=NOW)
    assert src.usable is False and src.stale is True
    assert src.detail["excluded_reason"] == "off_session"
    rctx = _rotation_context([src])
    assert rctx["usable"] is False and rctx["state"] is None
    assert rctx["early_context"] is None and rctx["coverage"] == "STALE"
    _write(tmp_path, "site/marketdata/rotation_events.json", doc)
    lobe = ws._compose_rotation_events(tmp_path, expected_session=SESSION, now=NOW)
    assert lobe["early_context"] is None
    settled = compose_envelope(
        sources=[*_measured_and_hazard(), src], market="US", source_session=SESSION,
        observed_at="2026-10-06T12:00:00Z", produced_at="2026-10-06T12:00:00Z")
    out = rc.compact_context(settled, now=NOW, expected_session=SESSION)
    assert out["usable"] is True and out["rotation_context"]["usable"] is False
    assert out["rotation_context"]["state"] is None
    assert out["rotation_context"]["early_context"] is None
    text = rc.render_context(out)
    assert "Rotation coverage unavailable" in text
    assert "gaining relative strength" not in text


# ------------------------------------------- A24: valid-empty correction ----

def test_a24_valid_empty_correction_clears_every_consumer_in_one_process(
        tmp_path, monkeypatch):
    # MUTATION (proved: applied → FAIL → reverted): engine/rotation_events.py,
    # early_rotation_context: `if relative > 0:` → `if relative >= 0:` (a zero-ratio
    # corrected read would then still count positive, so the valid-empty correction
    # could never clear the first read's state).
    monkeypatch.delenv("COLLECT_LANE", raising=False)
    positive = early_context_from(
        receipt(), receipt("broadening_proxy", .003, .001, "IWM", "QQQ"))
    proportional_def = RL.short_horizon_receipt(
        pair(), levels(daily=.002), levels(daily=.002) * 1.73, as_of=ASOF)
    proportional_broad = RL.short_horizon_receipt(
        pair("IWM", "QQQ", "broadening_proxy"),
        levels(daily=.003), levels(daily=.003) * 1.73, as_of=ASOF)
    corrected = early_context_from(proportional_def, proportional_broad)
    assert positive["state"] == "MIXED_ROTATION"
    assert positive["coverage"]["positive_2s"] == 2
    assert corrected["state"] == "NO_EARLY_SHIFT"      # real engine valid-empty shape
    assert corrected["coverage"]["positive_2s"] == 0

    doc_pos, doc_fix = _rotation_doc(positive), _rotation_doc(corrected)
    # same process: source read + envelope context, first positive then corrected
    c1 = _rotation_context([_rotation_read(doc_pos, SESSION, now=NOW)])
    assert c1["state"] == "MIXED_ROTATION" and c1["usable"] is True
    src2 = _rotation_read(doc_fix, SESSION, now=NOW)
    c2 = _rotation_context([src2])
    assert c2["state"] == "NO_EARLY_SHIFT" and c2["usable"] is True
    assert c2["early_context"]["coverage"]["positive_2s"] == 0
    # nothing from the first read survives: identical to an independent first read
    assert c2 == _rotation_context([_rotation_read(_rotation_doc(corrected), SESSION,
                                                   now=NOW)])
    # world_state lobe, same root, same process, corrected file replaces positive file
    _write(tmp_path, "site/marketdata/rotation_events.json", doc_pos)
    lobe1 = ws._compose_rotation_events(tmp_path, expected_session=SESSION, now=NOW)
    assert lobe1["early_context"]["state"] == "MIXED_ROTATION"
    _write(tmp_path, "site/marketdata/rotation_events.json", doc_fix)
    lobe2 = ws._compose_rotation_events(tmp_path, expected_session=SESSION, now=NOW)
    assert lobe2["early_context"]["state"] == "NO_EARLY_SHIFT"
    assert lobe2["early_context"]["coverage"]["positive_2s"] == 0
    control_root = tmp_path / "control"
    _write(control_root, "site/marketdata/rotation_events.json", doc_fix)
    lobe_ctrl = ws._compose_rotation_events(control_root, expected_session=SESSION,
                                            now=NOW)
    assert lobe2 == lobe_ctrl
    # settled consumer chain carries the correction, not the earlier positive state
    settled1 = compose_envelope(sources=[*_measured_and_hazard(),
                                         _rotation_read(doc_pos, SESSION, now=NOW)],
                                market="US", source_session=SESSION,
                                observed_at="2026-10-06T12:00:00Z",
                                produced_at="2026-10-06T12:00:00Z")
    out1 = rc.compact_context(settled1, now=NOW, expected_session=SESSION)
    assert out1["rotation_context"]["state"] == "MIXED_ROTATION"
    settled2 = compose_envelope(sources=[*_measured_and_hazard(), src2],
                                market="US", source_session=SESSION,
                                observed_at="2026-10-06T12:00:00Z",
                                produced_at="2026-10-06T12:00:00Z")
    out2 = rc.compact_context(settled2, now=NOW, expected_session=SESSION)
    assert out2["rotation_context"]["state"] == "NO_EARLY_SHIFT"
    text = rc.render_context(out2)
    assert "No short-term relative shift measured" in text
    assert "gaining relative strength" not in text


# ------------------------------- temporal coincidence is not a transfer ----

def _coincident_series():
    """Donor blowoff-crash + receiver turn coincide in time, but the ratio
    confirmation is absent: no negative 10s slope inside the flip window and no
    fresh 20s ratio high (the pop peak at t-9 dominates the trailing window)."""
    idx = pd.bdate_range("2024-06-03", periods=318)
    donor = [100.0] * 318
    for i in range(280, 300):
        donor[i] = donor[i - 1] * 1.02            # melt-up into the peak
    for i in range(300, 304):
        donor[i] = donor[i - 1] * 0.96            # crash off it
    for i in range(304, 318):
        donor[i] = donor[i - 1] * 1.002           # drift keeps drawdown >= 10%
    recv = [100.0] * 318
    recv[305], recv[306], recv[307] = 98.0, 97.0, 97.5   # fresh 40d low, 11 back
    recv[308] = recv[307] * 1.09                   # pop (reclaim) — but 9 sessions ago
    for i in range(309, 318):
        recv[i] = recv[i - 1] * 1.001              # slower than the donor's drift
    s = lambda vals: pd.Series(vals, index=idx, dtype=float)
    return s(donor), s(recv), s([100.0] * 318)


def test_temporal_coincidence_without_confirmation_stays_silent_and_transfer_free(
        tmp_path):
    # MUTATION (proved: applied → FAIL → reverted): engine/rotation_events.py,
    # evaluate_pair: `if c is None:` → `if False:` (the ratio-confirmation gate of
    # the three-way AND removed — a bare coincidence would then create an event).
    donor, recv, spy = _coincident_series()
    assert RE.blowoff_crash(donor) is not None
    assert RE.turn_up(recv) is not None
    assert RE.pair_confirm(recv, donor) is None    # the engine's confirmation absent
    assert RE.evaluate_pair(donor, recv) is None
    state, active, created, closed = RE.step_pairs(
        _sectors({"memory": donor, "mag7": recv}), {})
    assert created == [] and active == [] and closed == []
    universe = _cross_universe()
    st1, ev1, cr1, _ = RE.step_cross_pairs(
        universe, {"spy": spy, "xlk_etf": donor, "xlu_etf": recv}, spy, {},
        p2={"confirm_days": 2})
    st2, ev2, cr2, _ = RE.step_cross_pairs(
        universe, {"spy": spy, "xlk_etf": donor, "xlu_etf": recv}, spy, st1,
        p2={"confirm_days": 2})
    assert st1.get("candidates") == {} and st2.get("candidates") == {}
    assert cr1 == [] and cr2 == [] and ev1 == [] and ev2 == []
    doc = {"schema": "rotation_events.v1", "as_of": SESSION,
           "generated_utc": "2026-10-06 05:00 UTC", "active": [],
           "created_tonight": []}
    payload = RE.emit_v2(_v1_base(active, created), ev2, cr2)
    alerts = RE.to_alerts(payload)
    assert alerts == []
    src = _rotation_read(doc, SESSION, now=NOW)
    rctx = _rotation_context([src])
    _write(tmp_path, "site/marketdata/rotation_events.json", doc)
    lobe = ws._compose_rotation_events(tmp_path, expected_session=SESSION, now=NOW)
    blob = json.dumps(
        {"active": active, "created": created, "closed": closed, "cross_events": ev2,
         "cross_created": cr2, "alerts": alerts, "payload": payload,
         "source_read": {"state": src.state, "detail": src.detail},
         "rotation_context": rctx, "lobe": lobe, "candidates": st2.get("candidates")},
        default=str)
    for banned in ("causal_handoff", "measured_inflow", "transferred", "capital"):
        assert banned not in blob

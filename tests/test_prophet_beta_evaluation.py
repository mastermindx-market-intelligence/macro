"""Tests for the frozen Prophet beta-first evaluation harness (synthetic, known answers)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engine import prophet_beta_evaluation as ev

ROOT = Path(__file__).resolve().parents[1]


def _cal(n=300, start="2025-01-02"):
    return pd.bdate_range(start, periods=n)


def _panel(cal, drifts: dict[str, float], seed=0, vol=0.0):
    rng = np.random.default_rng(seed)
    out = {}
    for t, mu in drifts.items():
        r = mu + vol * rng.standard_normal(len(cal))
        out[t] = 100 * np.cumprod(1 + r)
    return pd.DataFrame(out, index=cal)


ETFS = list(ev.SECTOR_ETFS)


# ── header binding ────────────────────────────────────────────────────────────

def test_header_hash_binding_accepts_frozen_file():
    h = ev.verify_header(ROOT / ev.HEADER_REL_PATH)
    assert h["protocol_id"] == "prophet-beta-first-evaluation-v1"


def test_header_hash_binding_refuses_modified_header(tmp_path):
    raw = (ROOT / ev.HEADER_REL_PATH).read_bytes()
    p = tmp_path / "h.json"
    p.write_bytes(raw.replace(b'"stock": 10.0', b'"stock": 5.0'))
    with pytest.raises(ev.HeaderMismatch):
        ev.verify_header(p)


def test_runner_refuses_when_header_differs(monkeypatch):
    import scripts.run_prophet_beta_evaluation as runner
    monkeypatch.setattr(ev, "FROZEN_HEADER_SHA256", "0" * 64)
    # verify_header's default argument was bound at import; the runner passes none, so
    # patch the function's default through a wrapper to prove the refusal path.
    orig = ev.verify_header
    monkeypatch.setattr(ev, "verify_header", lambda p: orig(p, "0" * 64))
    with pytest.raises(ev.HeaderMismatch):
        runner.main(["--prices-dir", "/nonexistent"])


# ── baselines with known answers ─────────────────────────────────────────────

def test_buy_and_hold_known_return_and_entry_cost():
    cal = _cal(5)
    closes = pd.DataFrame({"SPY": [100, 101, 102.01, 103.0301, 104.060401], "BIL": 100.0}, index=cal)
    rets = closes.pct_change()
    b = ev.simulate_book(list(cal), rets, rets["BIL"].fillna(0), {cal[0]: {"SPY": 1.0}},
                         closes.notna(), lambda a: 3.0)
    assert np.allclose(b.gross.to_numpy(), 0.01)
    # 3 bp entry cost charged once, into the first day's net return
    assert b.net.iloc[0] == pytest.approx(1.01 * (1 - 3e-4) - 1)
    assert np.allclose(b.net.iloc[1:].to_numpy(), 0.01)
    assert b.invested.iloc[0] == pytest.approx(1.0)


def test_beta_known_answer():
    rng = np.random.default_rng(1)
    rm = 0.01 * rng.standard_normal(500)
    rc = np.zeros(500)
    b, a = ev.beta_ols(1.5 * rm + 0.0002 - rc, rm - rc)
    assert b == pytest.approx(1.5)
    assert a == pytest.approx(0.0002)


def test_participation_rule_known_answer():
    cal = _cal(260)
    up = pd.Series(100 * 1.001 ** np.arange(260), index=cal)
    down = pd.Series(100 * 0.999 ** np.arange(260), index=cal)
    assert ev.sma_signal(up, cal[-1]) is True
    assert ev.sma_signal(down, cal[-1]) is False
    assert ev.sma_signal(up, cal[100]) is None   # not enough history


def test_top_sectors_known_order():
    cal = _cal(100)
    drifts = {e: 0.0005 for e in ETFS}
    drifts.update({"XLK": 0.003, "XLE": 0.002, "XLV": 0.001, "SPY": 0.0005})
    closes = _panel(cal, drifts)
    assert ev.top_sectors(closes, cal[-1]) == ["XLK", "XLE", "XLV"]


def test_capture_guard_near_zero_benchmark():
    rm = np.array([0.001, -0.001, 0.0005])
    assert ev.capture(rm, rm, True) is None


def test_capture_known_answer():
    rm = np.array([0.02, -0.01, 0.03, -0.02])
    assert ev.capture(0.5 * rm, rm, True) == pytest.approx(0.5, rel=0.02)


def test_style_weights_recover_mixture():
    rng = np.random.default_rng(3)
    cal = _cal(252)
    etf = pd.DataFrame(0.01 * rng.standard_normal((252, len(ETFS))), index=cal, columns=ETFS)
    w = pd.Series(0.0, index=ETFS); w["XLK"] = 0.6; w["XLF"] = 0.4
    spy = etf @ w
    est = ev.style_weights(spy, etf)
    assert est["XLK"] == pytest.approx(0.6, abs=1e-6) and est.sum() == pytest.approx(1.0)


# ── no look-ahead ─────────────────────────────────────────────────────────────

def test_signals_invariant_to_future_data():
    cal = _cal(200)
    closes = _panel(cal, {**{e: 0.0004 for e in ETFS}, "SPY": 0.0004, "AAA": 0.001, "BBB": 0.0},
                    vol=0.01, seed=5)
    t = cal[150]
    before = (ev.top_sectors(closes, t), ev.sma_signal(closes["SPY"], cal[-1]))
    poisoned = closes.copy()
    poisoned.loc[poisoned.index > t] *= 50.0   # wild future
    assert ev.top_sectors(poisoned, t) == before[0]
    elig = {"AAA": "XLK", "BBB": "XLK"}
    assert ev.member_picks(t, elig, closes) == ev.member_picks(t, elig, poisoned)


def test_rule_executes_one_session_after_decision():
    cal = _cal(50)
    sched = ev.rule_schedule(cal, cal[10], cal[-1], 21)
    assert all(cal.get_loc(x) == cal.get_loc(d) + 1 for d, x in sched)
    assert [cal.get_loc(d) for d, _ in sched] == [10, 31]


def test_publication_session_never_precedes_recording():
    cal = _cal(30, "2026-08-03")
    # basis Friday 08-07 recorded Sunday 08-09 -> Monday 08-10
    assert ev.publication_session(cal, "2026-08-07", "2026-08-09") == pd.Timestamp("2026-08-10")
    # recorded the same day as the basis -> strictly next session
    assert ev.publication_session(cal, "2026-08-10", "2026-08-10") == pd.Timestamp("2026-08-11")


def _plan(pid, basis, rec, state="filled", filled=None, **kw):
    return {"id": pid, "asset": kw.pop("asset", "AAA"), "direction": "BULL",
            "selection_era": ev.INCUMBENT_ERA, "price_basis_date": basis, "recorded_at": rec,
            "entry_zone_state": {"state": state, "filled_date": filled},
            "invalidation": kw.pop("inv", 1.0), "targets": kw.pop("targets", [1e9]),
            "horizon_days": kw.pop("hz", 45), "admission_class": "patience", **kw}


def test_build_positions_rules():
    cal = _cal(40, "2026-08-03")
    closes = _panel(cal, {**{e: 0.0 for e in ETFS}, "SPY": 0.0, "AAA": 0.001})
    raw = closes.copy()
    plans = [
        _plan("P1", "2026-08-07", "2026-08-09", filled="2026-08-05"),   # filled before publication
        _plan("P2", "2026-08-07", "2026-08-09", filled="2026-08-14"),   # filled after publication
        _plan("P3", "2026-08-07", "2026-08-09", state="live"),          # never entered
        _plan("P4", "2026-08-07", "2026-08-09"),                        # ledger NO_ENTRY
        _plan("P5", "2026-08-07", "2026-08-09"),                        # resolved before fill
        _plan("P6", "2026-08-07", "2026-08-09", selection_era="legacy"),
    ]
    ledger = {"P4": {"outcome": "NO_ENTRY", "close_date": "2026-08-20"},
              "P5": {"outcome": "INVALIDATED", "close_date": "2026-08-08"},
              "P2": {"outcome": "T1_HIT", "close_date": "2026-08-21"}}
    pos, excl, extra = ev.build_positions(plans, ledger, cal, closes, raw, {}, "2026-08-10", cal[-1])
    by = {p.plan_id: p for p in pos}
    assert set(by) == {"P1", "P2"}
    assert by["P1"].entry == pd.Timestamp("2026-08-10")          # never before publication
    assert by["P2"].entry == pd.Timestamp("2026-08-14")
    assert by["P2"].exit == pd.Timestamp("2026-08-21") and not by["P2"].censored
    assert excl == {"not_entered_zone_live": 1, "recorded_no_entry": 1,
                    "resolved_at_or_before_follower_fill": 1}
    assert extra["era_plans"] == 5 and extra["entry_shifted_to_publication"] == 1


def test_mechanical_exit_uses_published_levels():
    cal = _cal(40, "2026-08-03")
    raw = pd.DataFrame({"AAA": np.r_[np.full(10, 10.0), np.full(30, 8.0)]}, index=cal)
    closes = pd.concat([raw, _panel(cal, {**{e: 0.0 for e in ETFS}, "SPY": 0.0})], axis=1)
    p = _plan("Q", "2026-08-03", "2026-08-03", inv=9.0, filled=None)
    pos, _, _ = ev.build_positions([p], {}, cal, closes, raw, {}, cal[0], cal[-1])
    assert pos[0].exit == cal[10] and pos[0].exit_basis == "mechanical_invalidation"


# ── origination availability (deviation D5) ───────────────────────────────────

def _bf_plan(pid, basis, rec, executed_at, **kw):
    p = _plan(pid, basis, rec, **kw)
    p["origination_mode"] = "outage_backfill_2026_08_09"
    p["backfill_executed_at"] = executed_at
    return p


def test_auditable_first_availability_uses_utc_receipt_date():
    bf = _bf_plan("B1", "2026-08-07", "2026-08-09", "2026-08-11T05:32:28.853265+00:00")
    # pre-open UTC execution on 08-11 -> the 08-11 session is the first a user could see
    assert ev.auditable_first_availability(bf) == pd.Timestamp("2026-08-11")
    live = _plan("L1", "2026-08-07", "2026-08-09")
    assert ev.auditable_first_availability(live) is None and not ev.is_backfilled(live)


def test_backfilled_plans_excluded_from_primary_book_detected_from_data():
    cal = _cal(40, "2026-08-03")
    closes = _panel(cal, {**{e: 0.0 for e in ETFS}, "SPY": 0.0, "AAA": 0.001, "ZZZ": 0.0})
    raw = closes.copy()
    plans = [
        _plan("LIVE", "2026-08-07", "2026-08-09", asset="AAA"),
        _bf_plan("BF1", "2026-08-07", "2026-08-09", "2026-08-11T05:32:28+00:00", asset="AAA"),
    ]
    not_live = frozenset(p["id"] for p in plans if ev.is_backfilled(p))   # detected, not listed
    assert not_live == {"BF1"}
    pos, excl, _ = ev.build_positions(plans, {}, cal, closes, raw, {}, "2026-08-10", cal[-1],
                                      not_live_ids=not_live)
    assert [p.plan_id for p in pos] == ["LIVE"]
    assert excl == {ev.NOT_LIVE_EXCLUSION_REASON: 1}
    assert excl[ev.NOT_LIVE_EXCLUSION_REASON] == 1 and pos[0].entry == pd.Timestamp("2026-08-10")


def test_no_position_enters_before_its_auditable_availability():
    """A backfilled replay admitted at all must enter no earlier than the first session
    at/after its backfill receipt; in the primary population it must not enter at all."""
    cal = _cal(40, "2026-08-03")
    closes = _panel(cal, {**{e: 0.0 for e in ETFS}, "SPY": 0.0, "AAA": 0.001})
    raw = closes.copy()
    bf = _bf_plan("BF1", "2026-08-07", "2026-08-09", "2026-08-11T05:32:28.853265+00:00")
    # old (defective) clock: basis 08-07 + recorded 08-09 -> publication session 08-10
    assert ev.publication_session(cal, "2026-08-07", "2026-08-09") == pd.Timestamp("2026-08-10")
    avail = {"BF1": ev.auditable_first_availability(bf)}
    pos, _, _ = ev.build_positions([bf], {}, cal, closes, raw, {}, "2026-08-10", cal[-1],
                                   avail_floor=avail)
    assert [p.plan_id for p in pos] == ["BF1"]
    assert pos[0].entry == pd.Timestamp("2026-08-11")      # receipt UTC date, not the nominal 08-10
    # the invariant in general: every position enters at/after its plan's auditable availability
    for p in pos:
        a = ev.auditable_first_availability(bf)
        assert a is None or p.entry >= ev.session_on_or_after(cal, a)
    # availability beyond the window end excludes the plan outright
    bf_late = _bf_plan("BF2", "2026-08-07", "2026-08-09", "2026-11-30T05:00:00+00:00")
    pos2, excl2, _ = ev.build_positions([bf_late], {}, cal, closes, raw, {}, "2026-08-10",
                                        pd.Timestamp("2026-11-06"), avail_floor={"BF2": ev.auditable_first_availability(bf_late)})
    assert pos2 == [] and excl2 == {"published_after_window": 1}


def test_per_position_weights_with_staggered_same_ticker_overlap():
    cal = _cal(10)
    # two staggered same-ticker positions in AAA plus one BBB: on overlap days AAA
    # must carry 2/N (per open position), not 1/N (per distinct ticker).
    pos = [ev.Position("p1", "AAA", None, cal[1], cal[4], False, "x", None, None),
           ev.Position("p2", "AAA", None, cal[2], cal[8], False, "x", None, None),
           ev.Position("p3", "BBB", None, cal[0], cal[6], False, "x", None, None)]
    t = ev.prophet_targets(pos, list(cal))
    assert t[cal[3]] == {"AAA": 2.0 / 3.0, "BBB": 1.0 / 3.0}    # both AAA positions live
    assert t[cal[1]] == {"AAA": 0.5, "BBB": 0.5}                # one AAA live
    assert t[cal[6]] == {"AAA": 1.0}                            # BBB exited at cal[6]
    assert t[cal[8]] == {}                                      # everything closed
    assert all(abs(sum(w.values()) - 1.0) < 1e-12 for w in t.values() if w)


def test_per_position_weights_equal_per_asset_without_overlap():
    cal = _cal(8)
    pos = [ev.Position("p1", "AAA", None, cal[0], cal[5], False, "x", None, None),
           ev.Position("p2", "BBB", None, cal[2], cal[7], False, "x", None, None)]
    t = ev.prophet_targets(pos, list(cal))
    assert t[cal[3]] == {"AAA": 0.5, "BBB": 0.5} and t[cal[6]] == {"BBB": 1.0}


def test_ledger_loader_skips_comment_lines_and_counts_real_bad_rows(tmp_path):
    from scripts.run_prophet_beta_evaluation import load_jsonl
    f = tmp_path / "ledger.jsonl"
    f.write_text('# prophet ledger schema v3 — documentation header\n'
                 '{"id": "A"}\n'
                 '\n'
                 '{"id": (not json\n'
                 '# another comment\n'
                 '{"id": "B"}\n', encoding="utf-8")
    rows, bad = load_jsonl(f)
    assert [r["id"] for r in rows] == ["A", "B"]
    assert bad == 1     # only the genuinely malformed data row counts


# ── costs and no-fill accounting ─────────────────────────────────────────────

def test_no_fill_stays_in_cash_and_costs_scale():
    cal = _cal(4)
    closes = pd.DataFrame({"A": [10, 11, 12, 13], "B": [np.nan, np.nan, 5, 5], "BIL": 100.0}, index=cal)
    rets = closes.pct_change(fill_method=None)
    tgt = {cal[0]: {"A": 0.5, "B": 0.5}}
    b = ev.simulate_book(list(cal), rets, rets["BIL"].fillna(0), tgt, closes.notna(), lambda a: 10.0)
    assert b.no_fill == 1
    assert b.invested.iloc[0] == pytest.approx(0.5)
    assert -b.cost.iloc[0] == pytest.approx(0.5 * 10e-4 * 1.05, rel=1e-6)
    b2 = ev.simulate_book(list(cal), rets, rets["BIL"].fillna(0), tgt, closes.notna(), lambda a: 20.0)
    assert -b2.cost.sum() == pytest.approx(2 * -b.cost.sum(), rel=1e-3)


def test_attribution_identity_exact():
    cal = _cal(60)
    closes = _panel(cal, {"SPY": 0.0005, "XLK": 0.001, "XLF": 0.0, "A": 0.002, "B": -0.001, "BIL": 0.0001},
                    vol=0.01, seed=9)
    rets = closes.pct_change()
    pos = [ev.Position("p1", "A", "XLK", cal[2], cal[40], False, "x", None, True),
           ev.Position("p2", "B", "XLF", cal[10], cal[59], True, "x", None, False)]
    t = ev.prophet_targets(pos, list(cal))
    b = ev.simulate_book(list(cal), rets, rets["BIL"].fillna(0), t, closes.notna(), lambda a: 10.0)
    att = ev.attribution_bridge(b, rets, rets["BIL"].fillna(0), ev.asset_sector_map(pos))
    assert abs(att["identity_error"]) < 1e-12
    br = att["gap_vs_benchmark_bridge"]
    total = br["benchmark"] + br["uninvested_market_shortfall"] + br["sector_allocation"] + \
        br["selection_within_sector"] + br["cash"] + br["costs"]
    assert total == pytest.approx(br["strategy"], abs=1e-12)


# ── statistics and determinism ───────────────────────────────────────────────

def test_bootstrap_deterministic_and_seed_sensitive():
    a = ev.stationary_bootstrap_indices(63, 200, 10, 20261110)
    b = ev.stationary_bootstrap_indices(63, 200, 10, 20261110)
    c = ev.stationary_bootstrap_indices(63, 200, 10, 1)
    assert np.array_equal(a, b) and not np.array_equal(a, c)
    assert a.min() >= 0 and a.max() < 63


def test_bootstrap_vs_reproducible_and_centered_pvalue():
    rng = np.random.default_rng(2)
    rm = 0.01 * rng.standard_normal(63)
    rc = np.zeros(63)
    idx = ev.stationary_bootstrap_indices(63, 2000, 10, 7)
    r1 = ev.bootstrap_vs(rm + 0.002, rm, rm, rc, idx)
    r2 = ev.bootstrap_vs(rm + 0.002, rm, rm, rc, idx)
    assert r1 == r2
    assert r1["p_one_sided"] < 0.05 and r1["beta_ci95"][0] > 0.9
    r0 = ev.bootstrap_vs(rm, rm, rm, rc, idx)
    assert r0["ann_diff"] == 0.0


def test_holm_known_answer():
    out = ev.holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert out["a"]["p_holm"] == pytest.approx(0.03)
    assert out["c"]["p_holm"] == pytest.approx(0.06)
    assert out["b"]["p_holm"] == pytest.approx(0.06)
    assert out["a"]["reject_h0"] and not out["c"]["reject_h0"] and not out["b"]["reject_h0"]


def test_wilson_bounds():
    lo, hi = ev.wilson(5, 10)
    assert lo < 0.5 < hi and 0 <= lo and hi <= 1
    assert ev.wilson(0, 0) is None


def test_release_capped_below_global_minimum():
    header = json.loads((ROOT / ev.HEADER_REL_PATH).read_text())
    good = {"p_holm": 0.001, "ann_diff": 0.5}
    rel = ev.release_assessment(
        header, window_sessions=64, spy_mdd=-0.20, resolved_positions=500,
        c6={"beta_vs_market": 1.0, "upside_capture": 1.0, "mean_invested": 0.99},
        c6_vs_c1={"beta_ci95": [0.9, 1.1], "upside_capture_ci95": [0.9, 1.1], "ann_diff_ci95": [0.1, 0.2]},
        c6_stress={"ann_diff": 0.1}, contrasts={f"K{i}": good for i in range(1, 9)},
        stress_contrasts={f"K{i}": {"ann_diff": 0.4} for i in range(1, 9)},
        k3_vs_exposure={"ann_diff_ci95": [0.1, 0.2]},
        l0_checks={"classified_share": 1.0, "priced_share": 1.0})
    assert not rel["global_minimum_met"]
    assert {j["level"] for j in rel["jobs"].values()} == {"L0_descriptive"}
    rel2 = ev.release_assessment(
        header, window_sessions=300, spy_mdd=-0.20, resolved_positions=500,
        c6={"beta_vs_market": 1.0, "upside_capture": 1.0, "mean_invested": 0.99},
        c6_vs_c1={"beta_ci95": [0.9, 1.1], "upside_capture_ci95": [0.9, 1.1], "ann_diff_ci95": [0.1, 0.2]},
        c6_stress={"ann_diff": 0.1}, contrasts={f"K{i}": good for i in range(1, 9)},
        stress_contrasts={f"K{i}": {"ann_diff": 0.4} for i in range(1, 9)},
        k3_vs_exposure={"ann_diff_ci95": [0.1, 0.2]},
        l0_checks={"classified_share": 1.0, "priced_share": 1.0})
    assert rel2["jobs"]["A_market_participation"]["level"] == "L1_accepted_historical"


def test_forbidden_key_names_detected():
    assert ev.assert_no_forbidden_keys({"a": {"intercept_ann": 1}}) == []
    assert ev.assert_no_forbidden_keys({"a": [{"alpha_ann": 1}]}) == ["/a[0]/alpha_ann"]


def test_published_artifact_contract_if_present():
    p = ROOT / "site/prophet/beta_evaluation.json"
    if not p.exists():
        pytest.skip("artifact not generated in this checkout")
    a = json.loads(p.read_text())
    assert a["schema"] == ev.SCHEMA
    assert a["protocol"]["header_sha256"] == ev.FROZEN_HEADER_SHA256
    ids = {c["id"] for c in a["comparators"]}
    assert set(ev.COMPARATOR_IDS) <= ids
    assert ev.assert_no_forbidden_keys(a) == []
    assert not any(a[k] for k in ev.AUTHORITY)
    for att in a["attribution"].values():
        assert abs(att["identity_error"]) < 1e-9


# ── independent audit RUN-D corrections (2026-11-11) — regression block ──────
# Known-answer locks for: (1) the trading cost of a target set at the FINAL close is
# charged against the final day's net return instead of being dropped; (2) the
# disclosure-sensitivity helpers undated_converted_ids / held_path_gaps /
# first_gap_total_loss_rets and the split of resolved_at_or_before_follower_fill;
# (3) the runner verifies every price parquet against the frozen git data pin.

def _one_etf_book(rets_spy, targets, charge):
    cal = _cal(len(rets_spy))
    rets = pd.DataFrame({"SPY": rets_spy}, index=cal)
    tradable = pd.DataFrame({"SPY": True}, index=cal)
    cash = pd.Series(0.0, index=cal)
    tg = {cal[i]: w for i, w in targets.items()}
    return ev.simulate_book(list(cal), rets, cash, tg, tradable, lambda a: 3.0,
                            charge_terminal_trade_cost=charge)


def test_terminal_trade_cost_charged_at_final_close():
    targets = {0: {"SPY": 1.0}, 1: {}}       # full liquidation AT the final close
    b = _one_etf_book([np.nan, 0.0], targets, charge=True)
    assert b.gross.tolist() == [0.0]
    expected = (1 - 3e-4) * (1 - 3e-4) - 1       # entry 3bp + terminal liquidation 3bp
    assert b.net.iloc[0] == pytest.approx(expected, abs=1e-15)
    assert b.net.iloc[0] == pytest.approx(-5.9991e-4, abs=1e-15)
    assert b.cost.iloc[0] == pytest.approx(b.net.iloc[0] - b.gross.iloc[0], abs=1e-18)
    # superseded behaviour: the terminal cost is silently absent
    s = _one_etf_book([np.nan, 0.0], targets, charge=False)
    assert s.gross.tolist() == [0.0]
    assert s.net.iloc[0] == pytest.approx(-3e-4, abs=1e-15)
    assert s.cost.iloc[0] == pytest.approx(s.net.iloc[0] - s.gross.iloc[0], abs=1e-18)
    assert s.cost.iloc[0] == pytest.approx(-3e-4, abs=1e-15)


def test_c1_passive_held_through_invariant_under_flag():
    targets = {0: {"SPY": 1.0}}               # no target at the final close: never sold
    rs = [np.nan, 0.10, 0.10]
    on = _one_etf_book(rs, targets, charge=True)
    off = _one_etf_book(rs, targets, charge=False)
    pd.testing.assert_series_equal(on.net, off.net)
    pd.testing.assert_series_equal(on.cost, off.cost)
    pd.testing.assert_series_equal(on.gross, off.gross)
    comp = float(np.prod(1 + on.net.to_numpy()) - 1)
    assert comp == pytest.approx(1.10 * (1 - 3e-4) * 1.10 - 1, abs=1e-12)
    assert comp == pytest.approx(0.209637, abs=1e-12)   # 1.21 * 0.9997 - 1


def test_undated_converted_ids():
    def p(pid, zs, era=ev.INCUMBENT_ERA):
        return {"id": pid, "selection_era": era, "entry_zone_state": zs}
    plans = [
        p("a", {"state": "converted", "filled_date": "2026-08-20"}),
        p("b", {"state": "converted", "filled_date": None}),
        p("c", {"state": "converted", "filled_date": ""}),
        p("d", {"state": "converted", "converted_at": "2026-08-20T14:00:00Z"}),
        p("e", {"state": "filled"}),
        p("f", {"state": "converted", "filled_date": None}, era="legacy"),
    ]
    assert ev.undated_converted_ids(plans) == frozenset({"b", "c"})


def _gap_fixture():
    cal = _cal(5)
    closes = pd.DataFrame({"SPY": [100.0, 101, 102, 103, 104],
                           "XXX": [10.0, 11, 12, np.nan, np.nan],
                           "YYY": [5.0, 5, 5, 0.0, 0.0]}, index=cal)
    P = lambda pid, a, i, j: ev.Position(pid, a, None, cal[i], cal[j], False, "x", None, None)  # noqa: E731
    pos = [P("s", "SPY", 0, 4), P("x", "XXX", 0, 4), P("y", "YYY", 0, 4), P("x2", "XXX", 0, 2)]
    return cal, closes, pos


def test_held_path_gaps():
    cal, closes, pos = _gap_fixture()
    gaps = ev.held_path_gaps(pos, closes)
    assert gaps == [
        {"plan_id": "x", "asset": "XXX", "entry": cal[0], "first_missing_close": cal[3],
         "missing_sessions": 2},
        {"plan_id": "y", "asset": "YYY", "entry": cal[0], "first_missing_close": cal[3],
         "missing_sessions": 2},
    ]


def test_first_gap_total_loss_rets():
    cal, closes, pos = _gap_fixture()
    rets = closes.pct_change(fill_method=None)
    before = rets.copy()
    out = ev.first_gap_total_loss_rets(rets, pos, closes)
    pd.testing.assert_frame_equal(rets, before)            # original unmutated
    assert out.at[cal[3], "XXX"] == -1.0 and out.at[cal[3], "YYY"] == -1.0
    mask = pd.DataFrame(False, index=cal, columns=closes.columns)
    mask.loc[cal[3], ["XXX", "YYY"]] = True
    pd.testing.assert_frame_equal(out.mask(mask), before.mask(mask))


def test_resolved_at_or_before_split_counters():
    cal = _cal(40, "2026-08-03")
    closes = _panel(cal, {**{e: 0.0 for e in ETFS}, "SPY": 0.0, "AAA": 0.001})
    we = cal[-1]
    plans = [
        # filled exactly at the window end: open, censored to we, X == E == we
        _plan("END", "2026-08-07", "2026-08-09", filled=we.strftime("%Y-%m-%d")),
        # ledger resolution before the publication/fill session
        _plan("EARLY", "2026-08-07", "2026-08-09"),
    ]
    ledger = {"EARLY": {"outcome": "INVALIDATED", "close_date": "2026-08-08"}}
    pos, excl, extra = ev.build_positions(plans, ledger, cal, closes, closes.copy(), {},
                                          "2026-08-10", we)
    assert pos == []
    assert extra["entered_at_final_close"] == 1
    assert extra["resolved_before_follower_fill"] == 1
    assert excl == {"resolved_at_or_before_follower_fill": 2}
    assert excl["resolved_at_or_before_follower_fill"] == (
        extra["entered_at_final_close"] + extra["resolved_before_follower_fill"])


def test_load_prices_verifies_against_pin(tmp_path):
    import subprocess
    import scripts.run_prophet_beta_evaluation as runner
    repo = tmp_path / "repo"
    yd = repo / "data" / "yahoo"
    yd.mkdir(parents=True)
    cal = _cal(4)

    def frame(base):
        v = [base, base + 1, base + 2, base + 3]
        return pd.DataFrame({"close": v, "close_price": v}, index=cal)

    def g(*a):
        subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)

    g("init", "-q")
    g("config", "user.email", "t@example.invalid")
    g("config", "user.name", "t")
    g("config", "commit.gpgsign", "false")
    frame(10.0).to_parquet(yd / "AAA.parquet")
    frame(20.0).to_parquet(yd / "BBB.parquet")
    g("add", "data/yahoo")
    g("commit", "-q", "-m", "pin")
    pin = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True,
                         capture_output=True, text=True).stdout.strip()
    frame(999.0).to_parquet(yd / "AAA.parquet")       # corrupted local bytes
    (yd / "BBB.parquet").unlink()                     # absent locally, present in pin
    frame(30.0).to_parquet(yd / "CCC.parquet")        # local only, never pinned

    adj, raw, missing, digest, from_pin = runner.load_prices(
        ["AAA", "BBB", "CCC", "DDD"], yd, cal, repo, pin)
    assert missing == ["CCC", "DDD"]       # the pin decides: CCC has no pinned blob
    assert from_pin == ["AAA", "BBB"]
    assert adj["AAA"].tolist() == [10.0, 11.0, 12.0, 13.0]   # pinned, not corrupted 999
    assert adj["BBB"].tolist() == [20.0, 21.0, 22.0, 23.0]
    assert "CCC" not in adj.columns and len(digest) == 64


# ── independent-audit correction (2026-11-11): yardstick member benchmark + event rows ──
# ── independent-audit correction (2026-11-11): yardstick member benchmark + event rows ──
# Appended by Lead D; mirrors the house style above (synthetic known-answer fixtures).


def _mb_fixture():
    """140-session panel: XLV members A/B/C, XLF members E/F, non-member D, ETFs + SPY."""
    cal = _cal(140, "2026-01-05")
    cols = ["SPY", "XLV", "XLF", "A", "B", "C", "D", "E", "F"]
    idx = pd.DataFrame({"ticker": ["A", "B", "C", "E", "F"],
                        "start_date": [cal[0]] * 5,
                        "end_date": [pd.NaT] * 5})
    sector_of = {"A": "XLV", "B": "XLV", "C": "XLV", "E": "XLF", "F": "XLF"}
    closes = pd.DataFrame(index=cal, columns=cols, dtype=float)
    rng = np.random.default_rng(7)
    lvl = {c: 100.0 for c in cols}
    for d in cal:
        for c in cols:
            closes.at[d, c] = lvl[c]
            lvl[c] *= 1.0 + 0.001
    # deterministic hand returns over the measured windows
    P = cal[130]
    for c, r5 in (("A", 0.10), ("B", 0.02), ("C", -0.04), ("XLV", 0.03), ("XLF", 0.05), ("SPY", 0.01)):
        closes.at[cal[135], c] = closes.at[P, c] * (1 + r5)
    raw = closes.copy()
    return cal, idx, sector_of, closes, raw, P


def test_event_rows_ruler_and_legs():
    cal, pit, sector_of, closes, raw, P = _mb_fixture()
    pub = {"P1": P}
    df = ev.event_rows(pub, {"P1": "A"}, {"P1": "XLV"}, closes, cal, cal[-1], horizons=(5,))
    assert len(df) == 1
    row = df.iloc[0]
    assert row["signal"] == cal[129]          # session before P, next-bar ruler
    assert row["stock_ret"] == pytest.approx(0.10)
    assert row["etf_ret"] == pytest.approx(0.03)
    assert row["spy_ret"] == pytest.approx(0.01)
    assert row["sel"] == pytest.approx(0.07)   # 0.10 - 0.03
    assert row["x"] == pytest.approx(0.09)     # 0.10 - 0.01


def test_member_benchmark_identity_peers_and_published_exclusion():
    cal, pit, sector_of, closes, raw, P = _mb_fixture()
    pub = {"P1": P, "P2": P}
    out = ev.member_benchmark_event_study(pub, {"P1": "A", "P2": "B"}, {"P1": "XLV", "P2": "XLV"},
                                          closes, raw, cal, cal[-1], pit, sector_of,
                                          B=200, seed=1, horizons=(5,), n_placebo=50)
    m = out["5"]
    assert m["n"] == 2
    # peers of P1 (asset A, published B same day): eligible XLV members minus {A, B} = {C}
    assert m["median_peers_per_plan"] == 1
    # bench for both plans = C's forward return; identity sel == drag + (stock - bench), exact
    bench = -0.04
    dr = bench - 0.03
    assert m["equal_weight_member_minus_sector_etf"]["mean"] == pytest.approx(dr)
    assert m["stock_minus_equal_weight_members"]["mean"] == pytest.approx(((0.10 - bench) + (0.02 - bench)) / 2)
    assert m["stock_minus_sector_etf"]["mean"] == pytest.approx(((0.10 - 0.03) + (0.02 - 0.03)) / 2)
    assert m["identity_check_max_abs"] == pytest.approx(0.0, abs=1e-12)
    # single-peer placebo: every draw picks C -> degenerate at the drag value
    pl = m["placebo_random_same_sector"]
    assert pl["mean"] == pytest.approx(dr)
    assert pl["p2_5"] == pytest.approx(dr)
    assert pl["p97_5"] == pytest.approx(dr)


def test_member_benchmark_two_peers_placebo_spans_their_range():
    cal, pit, sector_of, closes, raw, P = _mb_fixture()
    pub = {"P1": P}
    out = ev.member_benchmark_event_study(pub, {"P1": "A"}, {"P1": "XLV"},
                                          closes, raw, cal, cal[-1], pit, sector_of,
                                          B=200, seed=1, horizons=(5,), n_placebo=400)
    m = out["5"]
    assert m["median_peers_per_plan"] == 2      # B and C
    pl = m["placebo_random_same_sector"]
    # draws pick B (+0.02) or C (-0.04) vs XLV (+0.03): range brackets both, mean at their midpoint
    assert pl["p2_5"] <= 0.02 - 0.03 + 1e-9 and pl["p97_5"] >= -0.04 - 0.03 - 1e-9
    # Monte-Carlo mean over 400 draws: per-draw spread 0.06 -> sigma(mean) ~ 0.0015; allow 3+ sigma
    assert pl["mean"] == pytest.approx(((0.02 - 0.03) + (-0.04 - 0.03)) / 2, abs=0.005)

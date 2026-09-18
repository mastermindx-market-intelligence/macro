"""Tests for engine.grading — the one honest grader (W1c, audit #15/#46).

Covers the four axes it standardizes:
  1. next-bar fill (entry = bar AFTER the signal; forward window strictly forward of it)
  2. survivorship via as_of_members (the panel changes vs today's survivors)
  3. dual return basis (documented; total-return is the default free basis)
  4. delisting terminal values — a name that dies mid-horizon grades as a LOSS, not vanishing
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from engine import grading


def _series(vals, start="2020-01-01"):
    idx = pd.bdate_range(start, periods=len(vals))
    return pd.Series([float(v) for v in vals], index=idx)


# --------------------------------------------------------------------------- #
# 1. NEXT-BAR FILL
# --------------------------------------------------------------------------- #
class TestNextBarFill:
    def test_fill_index_is_signal_bar_plus_one(self):
        s = _series(range(10, 30))            # 20 bars
        sig_date = str(s.index[5].date())
        assert grading.fill_index(s, sig_date) == 6

    def test_fill_index_none_when_no_next_bar(self):
        s = _series(range(10, 30))
        last = str(s.index[-1].date())
        assert grading.fill_index(s, last) is None    # nothing to fill into

    def test_entry_price_is_next_bar_close(self):
        s = _series([100, 101, 102, 103, 104, 105, 106, 107, 108, 109])
        sig = str(s.index[2].date())          # signal on bar 2 (close 102)
        m = grading.forward_metrics(s, sig, horizons=(3,))
        assert m["entry_price"] == 103.0      # NEXT bar (index 3)
        assert m["fill_offset"] == 1

    def test_forward_return_measured_from_fill(self):
        # entry at fill (bar 3, price 103); +3 bars -> bar 6 price 106
        s = _series([100, 101, 102, 103, 104, 105, 106, 107, 108, 109])
        sig = str(s.index[2].date())
        m = grading.forward_metrics(s, sig, horizons=(3,))
        assert abs(m["fwd_ret_3"] - (106.0 / 103.0 - 1.0)) < 1e-9

    def test_mdd_window_strictly_forward_of_fill(self):
        # Trough is the ENTRY bar itself — a strictly-forward window must NOT see it as a drawdown.
        s = _series([100, 100, 90, 110, 120, 130, 140])
        sig = str(s.index[1].date())          # signal bar 1 -> fill bar 2 (price 90)
        m = grading.forward_metrics(s, sig, horizons=(3,))
        assert m["entry_price"] == 90.0
        # forward window is bars 3,4,5 (all above 90) -> no drawdown from the 90 fill
        assert m["fwd_mdd_3"] == 0.0

    def test_same_bar_shadow_differs_from_next_bar(self):
        s = _series([100, 90, 95, 105, 110, 120])
        sig = str(s.index[0].date())
        nb = grading.forward_metrics(s, sig, horizons=(3,))
        sb = grading.forward_metrics(s, sig, horizons=(3,), same_bar=True)
        assert nb["entry_price"] == 90.0 and sb["entry_price"] == 100.0
        assert nb["fwd_ret_3"] != sb["fwd_ret_3"]  # the correction is real & measurable

    def test_horizon_not_matured_is_none(self):
        s = _series(range(100, 105))          # only 5 bars
        sig = str(s.index[0].date())
        m = grading.forward_metrics(s, sig, horizons=(60,))
        assert m["fwd_ret_60"] is None


# --------------------------------------------------------------------------- #
# 4. DELISTING TERMINAL VALUES — the loss must be realized, not dropped
# --------------------------------------------------------------------------- #
class TestDelistingTerminal:
    def test_dead_name_graded_as_loss_not_vanished(self):
        # A name whose live cache stops early, extended by an imputed −100% bankruptcy
        # terminal, must grade its horizon as a total loss — never disappear.
        live = _series([100, 100, 100], start="2020-01-01")    # trades 3 days then gone
        # dead store: a −100% terminal AFTER the live series ends
        dead_idx = pd.bdate_range("2020-01-06", periods=2)
        dead = {"ZOMB": pd.Series([50.0, 0.0], index=dead_idx)}  # imputed bankruptcy → 0
        resolved = grading.resolve_series("ZOMB", live, dead_prices=dead)
        # the resolved series must carry the terminal 0.0 (the wipe)
        assert resolved.iloc[-1] == 0.0
        assert len(resolved) == 5

        sig = str(live.index[0].date())        # signal on day 0 -> fill day 1 (price 100)
        m = grading.forward_metrics(resolved, sig, horizons=(3,))
        assert m["entry_price"] == 100.0
        # 3 bars past the fill lands on the imputed 0.0 -> −100% return, graded as the LOSS
        assert m["fwd_ret_3"] == pytest.approx(-1.0)
        assert m["fwd_mdd_3"] == pytest.approx(-1.0)

    def test_resolve_series_no_dead_returns_live(self):
        live = _series([10, 11, 12])
        assert grading.resolve_series("X", live, dead_prices={}).equals(live)

    def test_resolve_series_dead_only_when_no_live(self):
        dead = {"D": _series([5, 4, 0])}
        out = grading.resolve_series("D", None, dead_prices=dead)
        assert out is not None and out.iloc[-1] == 0.0


# --------------------------------------------------------------------------- #
# 2. SURVIVORSHIP — the as-of panel differs from today's survivors
# --------------------------------------------------------------------------- #
class TestSurvivorshipPanel:
    def _ledger(self):
        # A member that DROPPED (last_seen before asof) and one that survived.
        return pd.DataFrame([
            {"ticker": "SURV", "group": "sp500", "name": "Surv", "sector": "Tech",
             "first_seen": pd.Timestamp("2015-01-01"), "last_seen": pd.Timestamp("2026-01-01"),
             "active": True},
            {"ticker": "GONE", "group": "sp500", "name": "Gone", "sector": "Fin",
             "first_seen": pd.Timestamp("2015-01-01"), "last_seen": pd.Timestamp("2017-06-01"),
             "active": False},
        ])

    def test_as_of_members_excludes_names_not_yet_or_no_longer_members(self):
        from engine.universe_history import as_of_members
        led = self._ledger()
        # In 2016 BOTH were members; in 2020 only SURV (GONE dropped 2017-06).
        m2016 = as_of_members("2016-06-01", ledger=led)
        m2020 = as_of_members("2020-06-01", ledger=led)
        assert set(m2016) == {"SURV", "GONE"}
        assert set(m2020) == {"SURV"}
        # PROOF the panel differs: the as-of-2016 universe carries a name today's survivor
        # panel (2020) has erased — the exact survivorship the grader must respect.
        assert "GONE" in m2016 and "GONE" not in m2020

    def test_as_of_panel_reconstructs_2016_universe(self):
        led = self._ledger()
        closes = {
            "SURV": _series(range(10, 400), start="2015-06-01"),
            "GONE": _series(range(20, 60), start="2015-06-01"),
        }
        panel = grading.as_of_panel(closes, "2016-06-01", ledger=led,
                                    include_dead=False)
        assert panel["survivorship"] == "as-of"
        assert set(panel["members"]) == {"SURV", "GONE"}
        assert "GONE" in panel["closes"]      # the dropped name is IN the 2016 panel

    def test_cold_start_falls_back_and_is_flagged(self):
        # asof before accrual (empty ledger) AND no PIT file -> cold-start tag + today's panel.
        # Pass pit_path pointing to a nonexistent file so the PIT fallback is bypassed.
        closes = {"A": _series(range(10, 400))}
        panel = grading.as_of_panel(closes, "2010-01-01", ledger=pd.DataFrame(),
                                    include_dead=False, pit_path="/nonexistent/pit.parquet")
        assert panel["survivorship"] == "cold-start"
        assert set(panel["members"]) == {"A"}


# --------------------------------------------------------------------------- #
# 3. DUAL RETURN BASIS — tags exist and are distinct
# --------------------------------------------------------------------------- #
def test_grade_basis_tags():
    assert grading.GradeBasis.TOTAL == "total_return"
    assert grading.GradeBasis.PRICE == "price_return"
    assert grading.GradeBasis.TOTAL != grading.GradeBasis.PRICE


def test_grade_next_bar_return_single_horizon():
    s = _series([100, 101, 102, 103, 104, 105])
    sig = str(s.index[0].date())           # fill bar 1 (101); +2 -> bar 3 (103)
    assert grading.grade_next_bar_return(s, sig, 2) == pytest.approx(103.0 / 101.0 - 1.0)


# --------------------------------------------------------------------------- #
# Prophet HK/CA discovery outcome evaluator — governed Lane-B "third door"
# --------------------------------------------------------------------------- #
def _discovery_rows(*raw_refs, session_date="2026-01-12", market="HK", definition="disc_v1"):
    rows = []
    for raw in raw_refs:
        rows.append({
            "session_date": session_date,
            "market": market,
            "security_ref": str(raw).strip(),
            "security_ref_raw": raw,
            "challenger_definition": definition,
            "candidate_origin": "research_only",
        })
    return pd.DataFrame(rows)


def _trend(n=120, start="2025-12-01", step=1.0):
    idx = pd.bdate_range(start, periods=n)
    return pd.Series(100.0 + step * np.arange(n), index=idx)

def test_prophet_discovery_outcome_parity_with_shared_grader_and_benchmark(monkeypatch):
    from engine import prophet_discovery_grade as pdg
    close = _trend(180, step=1.0)
    bench = _trend(180, step=0.4)
    sig = str(close.index[5].date())
    discovery = _discovery_rows("0005.HK", session_date=sig)

    monkeypatch.setattr(pdg.board_ledger, "_name_close", lambda *_a, **_k: close)
    monkeypatch.setattr(pdg.board_ledger, "_bench_close", lambda *_a, **_k: bench)
    monkeypatch.setattr(pdg.board_ledger, "_is_suspended", lambda *_a, **_k: False)

    out = pdg.grade_frame("HK", discovery)
    assert len(out) == 1
    row = out.iloc[0]
    expected = grading.forward_metrics(close, sig, horizons=pdg.HORIZONS)
    expected_bench = grading.forward_metrics(bench, sig, horizons=pdg.HORIZONS)
    assert row["fill_date"] == expected["fill_date"]
    assert row["fill_offset"] == 1
    assert row["fwd_ret_21"] == pytest.approx(expected["fwd_ret_21"])
    assert row["bench_ret_21"] == pytest.approx(expected_bench["fwd_ret_21"])
    assert row["excess_ret_21"] == pytest.approx(
        expected["fwd_ret_21"] - expected_bench["fwd_ret_21"]
    )
    expected_ts8 = grading.terminal_state(
        close, sig,
        liftoff_mult=grading.LIFTOFF_8,
        liftoff_horizon=grading.LIFTOFF_HORIZON_21,
    )
    expected_ts15 = grading.terminal_state(
        close, sig,
        liftoff_mult=grading.LIFTOFF_15,
        liftoff_horizon=grading.LIFTOFF_HORIZON_126,
    )
    assert row["terminal_state_clean8_21"] == expected_ts8["state"]
    assert row["terminal_state_clean15_126"] == expected_ts15["state"]
    assert row["outcome_state"] == pdg.MATURED
    assert row["survivorship"] == "no_dead_name_store"

def test_prophet_discovery_outcome_uses_shared_suspension_law(monkeypatch):
    from engine import prophet_discovery_grade as pdg
    close = _trend(30)
    sig = str(close.index[5].date())
    called = {"n": 0}

    monkeypatch.setattr(pdg.board_ledger, "_name_close", lambda *_a, **_k: close)
    monkeypatch.setattr(pdg.board_ledger, "_bench_close", lambda *_a, **_k: None)

    def suspended(series, fill_date):
        called["n"] += 1
        assert series is close
        assert fill_date == close.index[6]
        return True

    monkeypatch.setattr(pdg.board_ledger, "_is_suspended", suspended)
    monkeypatch.setattr(
        pdg.grading, "terminal_state",
        lambda *_a, **_k: (_ for _ in ()).throw(
            AssertionError("terminal-state math must not run for suspended rows")
        ),
    )
    row = pdg.grade_frame("HK", _discovery_rows("0005.HK", session_date=sig)).iloc[0]
    assert called["n"] == 1
    assert row["outcome_state"] == pdg.SUSPENDED
    assert bool(row["suspended"]) is True
    assert pd.isna(row["fwd_ret_5"])
    assert pd.isna(row["entry_price"])
    assert pd.isna(row["terminal_state_clean8_21"])
    assert pd.isna(row["terminal_state_clean15_126"])

def test_prophet_discovery_missing_price_is_explicit_not_zero(monkeypatch):
    from engine import prophet_discovery_grade as pdg
    monkeypatch.setattr(pdg.board_ledger, "_name_close", lambda *_a, **_k: None)
    monkeypatch.setattr(pdg.board_ledger, "_bench_close", lambda *_a, **_k: None)
    row = pdg.grade_frame("CA", _discovery_rows("ABC.TO", market="CA")).iloc[0]
    assert row["outcome_state"] == pdg.UNAVAILABLE_PRICE
    assert pd.isna(row["fwd_ret_5"])
    assert pd.isna(row["entry_price"])


def test_prophet_discovery_outcomes_preserve_raw_identity_collisions(monkeypatch):
    from engine import prophet_discovery_grade as pdg
    close = _trend(100)
    monkeypatch.setattr(pdg.board_ledger, "_name_close", lambda *_a, **_k: close)
    monkeypatch.setattr(pdg.board_ledger, "_bench_close", lambda *_a, **_k: None)
    monkeypatch.setattr(pdg.board_ledger, "_is_suspended", lambda *_a, **_k: False)
    d = _discovery_rows("ABC.TO", " ABC.TO ", market="CA")
    out = pdg.grade_frame("CA", d)
    assert len(out) == 2
    assert set(out["security_ref_raw"]) == {"ABC.TO", " ABC.TO "}
    assert not {"rank", "score", "board_pos", "featured", "published_authority"} & set(out.columns)

def test_prophet_discovery_store_upserts_maturation_without_duplicate(tmp_path, monkeypatch):
    from engine import prophet_discovery_grade as pdg
    from lib import config
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    src = tmp_path / "prophet_shadow"
    src.mkdir(parents=True)
    sig = "2026-01-12"
    _discovery_rows("ABC.TO", session_date=sig, market="CA").to_parquet(
        src / "ca_discovery.parquet", index=False
    )
    short = _trend(45)
    long = _trend(180)
    current = {"series": short}
    monkeypatch.setattr(
        pdg.board_ledger, "_name_close",
        lambda *_a, **_k: current["series"],
    )
    monkeypatch.setattr(pdg.board_ledger, "_bench_close", lambda *_a, **_k: None)
    monkeypatch.setattr(pdg.board_ledger, "_is_suspended", lambda *_a, **_k: False)

    first = pdg.grade_market("CA")
    assert first["n_rows"] == 1
    stored = pd.read_parquet(src / "ca_discovery_outcomes.parquet")
    assert len(stored) == 1
    assert stored.iloc[0]["outcome_state"] == pdg.ACCRUING

    current["series"] = long
    second = pdg.grade_market("CA")
    assert second["n_rows"] == 1
    stored2 = pd.read_parquet(src / "ca_discovery_outcomes.parquet")
    assert len(stored2) == 1
    assert stored2.iloc[0]["outcome_state"] == pdg.MATURED
    assert pd.notna(stored2.iloc[0]["fwd_ret_63"])
    assert pd.notna(stored2.iloc[0]["terminal_state_clean8_21"])
    assert pd.notna(stored2.iloc[0]["terminal_state_clean15_126"])
    assert second["terminal_clean8_21"] == {grading.TerminalState.CLEAN_LIFTOFF: 1}
    assert second["terminal_clean15_126"] == {grading.TerminalState.CLEAN_LIFTOFF: 1}
    # Deterministic rerun with unchanged prices: no duplicate and identical values.
    before = stored2.copy()
    third = pdg.grade_market("CA")
    after = pd.read_parquet(src / "ca_discovery_outcomes.parquet")
    assert third["n_rows"] == 1
    pd.testing.assert_frame_equal(before, after)


def test_prophet_discovery_grader_is_explicit_and_not_render_wired():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    render = (root / ".github/workflows/render.yml").read_text()
    dag = (root / "config/dag.yml").read_text()
    assert "scripts.grade_prophet_discovery" not in render
    # Scheduler ownership is intentionally separate: the core evaluator lands
    # without silently inserting itself into the shared DAG while another
    # carrier owns that file. The CLI remains an explicit modifying action.
    assert "scripts.grade_prophet_discovery" not in dag

def test_prophet_discovery_cli_runs_both_markets_once(monkeypatch):
    import scripts.grade_prophet_discovery as runner
    called = {"n": 0}

    def fake():
        called["n"] += 1
        return {"HK": {"n_rows": 1}, "CA": {"n_rows": 2}}

    monkeypatch.setattr(runner.prophet_discovery_grade, "grade_all", fake)
    assert runner.main() == 0
    assert called["n"] == 1


def test_prophet_discovery_summary_reports_only_canonical_measured_metrics():
    from engine import prophet_discovery_grade as pdg

    frame = pd.DataFrame([
        {
            "outcome_state": pdg.MATURED,
            "fwd_mfe_5": 0.04, "fwd_mdd_5": -0.02, "excess_ret_5": 0.01,
            "terminal_state_clean8_21": grading.TerminalState.CLEAN_LIFTOFF,
            "terminal_state_clean15_126": None,
        },
        {
            "outcome_state": pdg.ACCRUING,
            "fwd_mfe_5": 0.02, "fwd_mdd_5": -0.06, "excess_ret_5": -0.01,
            "terminal_state_clean8_21": grading.TerminalState.STOPPED,
            "terminal_state_clean15_126": None,
        },
        {
            "outcome_state": pdg.UNAVAILABLE_PRICE,
            "fwd_mfe_5": None, "fwd_mdd_5": None, "excess_ret_5": None,
            "terminal_state_clean8_21": None,
            "terminal_state_clean15_126": None,
        },
    ])

    summary = pdg.summarize_outcomes(frame)
    assert summary["n_observations"] == 3
    assert summary["price_store_coverage_rate"] == pytest.approx(2 / 3)

    h5 = summary["horizons"]["5d"]
    assert h5["n_matured"] == 2
    assert h5["mfe_median"] == pytest.approx(0.03)
    assert h5["mae_median"] == pytest.approx(-0.04)
    assert h5["excess_ret_median"] == pytest.approx(0.0)

    clean8 = summary["terminal_states"]["clean8_21"]
    assert clean8["n_matured"] == 2
    assert clean8["clean_liftoff_rate"] == pytest.approx(0.5)
    assert clean8["stopped_dead_money_rate"] == pytest.approx(0.5)
    assert clean8["cushioned_rate"] == pytest.approx(0.0)

    clean15 = summary["terminal_states"]["clean15_126"]
    assert clean15["n_matured"] == 0
    assert clean15["clean_liftoff_rate"] is None
    assert clean15["stopped_dead_money_rate"] is None

    serialized = repr(summary).lower()
    assert "eventual_winner" not in serialized
    assert "top_k_regret" not in serialized
    assert "catastrophic" not in serialized


def test_prophet_discovery_grade_market_receipt_includes_candidate_summary(tmp_path, monkeypatch):
    from engine import prophet_discovery_grade as pdg
    from lib import config

    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    src = tmp_path / "prophet_shadow"
    src.mkdir(parents=True)
    sig = "2026-01-12"
    _discovery_rows("ABC.TO", session_date=sig, market="CA").to_parquet(
        src / "ca_discovery.parquet", index=False
    )
    close = _trend(180)
    monkeypatch.setattr(pdg.board_ledger, "_name_close", lambda *_a, **_k: close)
    monkeypatch.setattr(pdg.board_ledger, "_bench_close", lambda *_a, **_k: close)
    monkeypatch.setattr(pdg.board_ledger, "_is_suspended", lambda *_a, **_k: False)

    receipt = pdg.grade_market("CA")
    assert receipt["candidate_metrics"]["n_observations"] == 1
    assert receipt["candidate_metrics"]["horizons"]["21d"]["n_matured"] == 1
    assert receipt["candidate_metrics"]["terminal_states"]["clean8_21"]["n_matured"] == 1

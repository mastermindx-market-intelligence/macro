"""Tests for engine.grading — the one honest grader (W1c, audit #15/#46).

Covers the four axes it standardizes:
  1. next-bar fill (entry = bar AFTER the signal; forward window strictly forward of it)
  2. survivorship via as_of_members (the panel changes vs today's survivors)
  3. dual return basis (documented; total-return is the default free basis)
  4. delisting terminal values — a name that dies mid-horizon grades as a LOSS, not vanishing
"""
from __future__ import annotations

import json

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


def test_prophet_discovery_uses_canonical_split_adjusted_series(monkeypatch):
    from engine import prophet_discovery_grade as pdg

    adjusted = _trend(180, step=1.0)
    raw_with_split_gap = adjusted.copy()
    raw_with_split_gap.iloc[:8] *= 4.0
    sig = str(adjusted.index[5].date())

    monkeypatch.setattr(pdg.board_ledger, "_name_close", lambda *_a, **_k: adjusted)
    monkeypatch.setattr(pdg.board_ledger, "_bench_close", lambda *_a, **_k: adjusted)
    monkeypatch.setattr(pdg.board_ledger, "_is_suspended", lambda *_a, **_k: False)

    row = pdg.grade_frame("HK", _discovery_rows("0005.HK", session_date=sig)).iloc[0]
    canonical = grading.forward_metrics(adjusted, sig, horizons=pdg.HORIZONS)
    false_raw = grading.forward_metrics(raw_with_split_gap, sig, horizons=pdg.HORIZONS)
    assert row["fwd_ret_5"] == pytest.approx(canonical["fwd_ret_5"])
    assert row["fwd_ret_5"] > -0.5
    assert false_raw["fwd_ret_5"] < -0.5


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


def test_prophet_discovery_refuses_duplicate_observation_identity(monkeypatch):
    from engine import prophet_discovery_grade as pdg

    discovery = _discovery_rows("0005.HK")
    discovery = pd.concat([discovery, discovery.copy()], ignore_index=True)
    monkeypatch.setattr(
        pdg.board_ledger,
        "_name_close",
        lambda *_a, **_k: (_ for _ in ()).throw(
            AssertionError("corrupt identity must fail before price access")
        ),
    )

    with pytest.raises(ValueError, match="duplicate observation identity"):
        pdg.grade_frame("HK", discovery)


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


def test_prophet_discovery_grade_market_reports_current_source_receipt(
    tmp_path, monkeypatch
):
    from engine import prophet_discovery_grade as pdg
    from lib import config

    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    src = tmp_path / "prophet_shadow"
    src.mkdir(parents=True)
    sig = "2026-01-12"
    _discovery_rows("ABC.TO", session_date=sig, market="CA").to_parquet(
        src / "ca_discovery.parquet", index=False
    )
    (src / "ca_discovery_receipt.json").write_text(json.dumps({
        "market": "CA",
        "as_of": sig,
        "registry_state": "wrote_n_rows n=1",
        "written": 1,
        "definitions": ["ca_discovery_v1"],
        "challenger_failures": [],
        "stamped_at": "2026-01-12T23:00:00+00:00",
    }))

    close = _trend(180)
    monkeypatch.setattr(pdg.board_ledger, "_name_close", lambda *_a, **_k: close)
    monkeypatch.setattr(pdg.board_ledger, "_bench_close", lambda *_a, **_k: close)
    monkeypatch.setattr(pdg.board_ledger, "_is_suspended", lambda *_a, **_k: False)

    receipt = pdg.grade_market("CA", expected_source_asof=sig)
    assert receipt["source_receipt"]["available"] is True
    assert receipt["source_receipt"]["healthy"] is True
    assert receipt["source_receipt"]["as_of"] == sig
    assert receipt["source_receipt"]["registry_state"] == "wrote_n_rows n=1"
    assert receipt["source_receipt"]["challenger_failures"] == []


@pytest.mark.parametrize(
    ("receipt_asof", "registry_state", "failures", "match"),
    [
        ("2026-01-11", "wrote_n_rows n=1", [], "source receipt as_of mismatch"),
        (
            "2026-01-12",
            "wrote_n_rows n=0",
            [{"definition": "ca_discovery_v1", "error": "producer failed"}],
            "source receipt unhealthy",
        ),
    ],
)
def test_prophet_discovery_expected_source_receipt_fails_closed(
    receipt_asof, registry_state, failures, match, tmp_path, monkeypatch
):
    from engine import prophet_discovery_grade as pdg
    from lib import config

    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    src = tmp_path / "prophet_shadow"
    src.mkdir(parents=True)
    _discovery_rows("ABC.TO", session_date="2026-01-12", market="CA").to_parquet(
        src / "ca_discovery.parquet", index=False
    )
    (src / "ca_discovery_receipt.json").write_text(json.dumps({
        "market": "CA",
        "as_of": receipt_asof,
        "registry_state": registry_state,
        "written": 0,
        "definitions": ["ca_discovery_v1"],
        "challenger_failures": failures,
        "stamped_at": "2026-01-12T23:00:00+00:00",
    }))

    with pytest.raises(RuntimeError, match=match):
        pdg.grade_market("CA", expected_source_asof="2026-01-12")
    assert not (src / "ca_discovery_outcomes.parquet").exists()


@pytest.mark.parametrize("mutation", ["rewrite_metadata", "delete_identity"])
def test_prophet_discovery_replay_refuses_source_revision_or_deletion(
    mutation, tmp_path, monkeypatch
):
    from engine import prophet_discovery_grade as pdg
    from lib import config

    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    src = tmp_path / "prophet_shadow"
    src.mkdir(parents=True)
    source_path = src / "ca_discovery.parquet"
    source = pd.concat([
        _discovery_rows("ABC.TO", session_date="2026-01-12", market="CA"),
        _discovery_rows("XYZ.TO", session_date="2026-01-13", market="CA"),
    ], ignore_index=True)
    source.to_parquet(source_path, index=False)

    close = _trend(180)
    monkeypatch.setattr(pdg.board_ledger, "_name_close", lambda *_a, **_k: close)
    monkeypatch.setattr(pdg.board_ledger, "_bench_close", lambda *_a, **_k: close)
    monkeypatch.setattr(pdg.board_ledger, "_is_suspended", lambda *_a, **_k: False)

    first = pdg.grade_market("CA")
    assert first["n_rows"] == 2
    outcome_path = src / "ca_discovery_outcomes.parquet"
    before = pd.read_parquet(outcome_path)

    revised = source.copy()
    if mutation == "rewrite_metadata":
        revised.loc[0, "candidate_origin"] = "revised_without_lineage"
    else:
        revised = revised.iloc[:1].copy()
    revised.to_parquet(source_path, index=False)

    with pytest.raises(RuntimeError, match="append-only source continuity"):
        pdg.grade_market("CA")
    after = pd.read_parquet(outcome_path)
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


def test_prophet_discovery_grader_has_zero_live_publication_or_brain_authority():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    evaluator = (root / "engine/prophet_discovery_grade.py").read_text()
    runner = (root / "scripts/grade_prophet_discovery.py").read_text()
    for forbidden in (
        "site/factordata/hk_standouts.json",
        "site/factordata/canada_standouts.json",
        "scripts.build_hk_library",
        "scripts.build_canada_library",
    ):
        assert forbidden not in evaluator
        assert forbidden not in runner


def test_prophet_discovery_cli_runs_both_markets_once(monkeypatch):
    import scripts.grade_prophet_discovery as runner
    called = {"n": 0}

    def fake():
        called["n"] += 1
        return {"HK": {"n_rows": 1}, "CA": {"n_rows": 2}}

    monkeypatch.setattr(runner.prophet_discovery_grade, "grade_all", fake)
    assert runner.main() == 0
    assert called["n"] == 1


def test_prophet_discovery_cli_market_scope_calls_only_selected_market(monkeypatch, capsys):
    import scripts.grade_prophet_discovery as runner

    calls = []
    monkeypatch.setattr(
        runner.prophet_discovery_grade,
        "grade_all",
        lambda: pytest.fail("market-scoped invocation must not grade sibling market"),
    )

    def grade_market(market, *, expected_source_asof=None):
        calls.append((market, expected_source_asof))
        return {"market": market, "available": True, "state": "UPDATED", "n_rows": 7}

    monkeypatch.setattr(runner.prophet_discovery_grade, "grade_market", grade_market)

    assert runner.main(["--market", "HK", "--source-asof", "2026-01-12"]) == 0
    assert calls == [("HK", "2026-01-12")]
    assert json.loads(capsys.readouterr().out) == {
        "HK": {"market": "HK", "available": True, "state": "UPDATED", "n_rows": 7}
    }


def test_prophet_discovery_cli_market_scope_preserves_error_receipt(monkeypatch, capsys):
    import scripts.grade_prophet_discovery as runner

    calls = []

    def grade_market(market, *, expected_source_asof=None):
        calls.append((market, expected_source_asof))
        raise RuntimeError("HK source continuity violated")

    monkeypatch.setattr(runner.prophet_discovery_grade, "grade_market", grade_market)

    assert runner.main(["--market", "HK", "--source-asof", "2026-01-12"]) == 1
    assert calls == [("HK", "2026-01-12")]
    assert json.loads(capsys.readouterr().out) == {
        "HK": {
            "market": "HK",
            "available": False,
            "state": "ERROR",
            "error_type": "RuntimeError",
            "error": "HK source continuity violated",
        }
    }


def test_prophet_discovery_cli_market_scope_requires_source_asof():
    import scripts.grade_prophet_discovery as runner

    with pytest.raises(SystemExit) as exc:
        runner.main(["--market", "HK"])
    assert exc.value.code == 2


def test_prophet_discovery_cli_source_asof_is_forwarded_to_selected_market(
    monkeypatch, capsys
):
    import scripts.grade_prophet_discovery as runner

    calls = []

    def grade_market(market, *, expected_source_asof=None):
        calls.append((market, expected_source_asof))
        return {"market": market, "available": True, "state": "UNCHANGED", "n_rows": 3}

    monkeypatch.setattr(runner.prophet_discovery_grade, "grade_market", grade_market)

    assert runner.main(["--market", "CA", "--source-asof", "2026-01-12"]) == 0
    assert calls == [("CA", "2026-01-12")]
    assert json.loads(capsys.readouterr().out)["CA"]["state"] == "UNCHANGED"


def test_prophet_discovery_cli_reports_structured_failure(monkeypatch, capsys):
    import scripts.grade_prophet_discovery as runner

    def fail():
        raise RuntimeError("source continuity violated")

    monkeypatch.setattr(runner.prophet_discovery_grade, "grade_all", fail)
    assert runner.main() == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "available": False,
        "state": "ERROR",
        "error_type": "RuntimeError",
        "error": "source continuity violated",
    }


def test_prophet_discovery_grade_all_preserves_success_receipt_when_other_market_fails(
    monkeypatch,
):
    from engine import prophet_discovery_grade as pdg

    calls = []

    def grade_market(market):
        calls.append(market)
        if market == "HK":
            return {"market": "HK", "available": True, "state": "UPDATED", "n_rows": 7}
        raise RuntimeError("CA source continuity violated")

    monkeypatch.setattr(pdg, "grade_market", grade_market)
    result = pdg.grade_all()

    assert calls == ["HK", "CA"]
    assert result["HK"] == {
        "market": "HK", "available": True, "state": "UPDATED", "n_rows": 7,
    }
    assert result["CA"] == {
        "market": "CA",
        "available": False,
        "state": "ERROR",
        "error_type": "RuntimeError",
        "error": "CA source continuity violated",
    }


def test_prophet_discovery_cli_returns_nonzero_with_partial_market_receipt(
    monkeypatch, capsys,
):
    import scripts.grade_prophet_discovery as runner

    result = {
        "HK": {"market": "HK", "available": True, "state": "UPDATED", "n_rows": 7},
        "CA": {
            "market": "CA",
            "available": False,
            "state": "ERROR",
            "error_type": "RuntimeError",
            "error": "CA source continuity violated",
        },
    }
    monkeypatch.setattr(runner.prophet_discovery_grade, "grade_all", lambda: result)

    assert runner.main() == 1
    assert json.loads(capsys.readouterr().out) == result


def test_prophet_discovery_summary_reports_only_canonical_measured_metrics():
    from engine import prophet_discovery_grade as pdg

    frame = pd.DataFrame([
        {
            "outcome_state": pdg.MATURED,
            "fwd_mfe_5": 0.04, "fwd_mdd_5": -0.02, "excess_ret_5": 0.01,
            "fwd_ret_21": -0.20,
            "terminal_state_clean8_21": grading.TerminalState.CLEAN_LIFTOFF,
            "terminal_state_clean15_126": None,
        },
        {
            "outcome_state": pdg.ACCRUING,
            "fwd_mfe_5": 0.02, "fwd_mdd_5": -0.06, "excess_ret_5": -0.01,
            "fwd_ret_21": 0.05,
            "terminal_state_clean8_21": grading.TerminalState.STOPPED,
            "terminal_state_clean15_126": None,
        },
        {
            "outcome_state": pdg.UNAVAILABLE_PRICE,
            "fwd_mfe_5": None, "fwd_mdd_5": None, "excess_ret_5": None,
            "fwd_ret_21": None,
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

    catastrophic = summary["catastrophic_outcome_21d"]
    assert catastrophic["definition"] == "fwd_ret_21<=-0.15"
    assert catastrophic["n_matured"] == 2
    assert catastrophic["n_catastrophic"] == 1
    assert catastrophic["rate"] == pytest.approx(0.5)

    serialized = repr(summary).lower()
    assert "eventual_winner" not in serialized
    assert "top_k_regret" not in serialized


def test_prophet_catastrophic_h21_unmatured_is_not_zero():
    from engine import prophet_discovery_grade as pdg

    summary = pdg.summarize_outcomes(pd.DataFrame([{
        "outcome_state": pdg.ACCRUING,
        "fwd_ret_21": None,
    }]))
    catastrophic = summary["catastrophic_outcome_21d"]
    assert catastrophic["n_matured"] == 0
    assert catastrophic["n_catastrophic"] == 0
    assert catastrophic["rate"] is None


def test_prophet_discovery_summary_names_missing_benchmark_coverage(monkeypatch):
    from engine import prophet_discovery_grade as pdg

    close = _trend(180)
    sig = str(close.index[5].date())
    monkeypatch.setattr(pdg.board_ledger, "_name_close", lambda *_a, **_k: close)
    monkeypatch.setattr(pdg.board_ledger, "_bench_close", lambda *_a, **_k: None)
    monkeypatch.setattr(pdg.board_ledger, "_is_suspended", lambda *_a, **_k: False)

    frame = pdg.grade_frame("HK", _discovery_rows("0005.HK", session_date=sig))
    summary = pdg.summarize_outcomes(frame)
    assert bool(frame.iloc[0]["benchmark_available"]) is False
    assert summary["n_benchmark_available"] == 0
    assert summary["benchmark_coverage_rate"] == pytest.approx(0.0)
    assert summary["horizons"]["21d"]["n_matured"] == 1
    assert summary["horizons"]["21d"]["excess_ret_median"] is None


def test_prophet_discovery_grade_market_receipt_includes_candidate_summary(tmp_path, monkeypatch):
    from engine import prophet_discovery_grade as pdg
    from lib import config

    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    src = tmp_path / "prophet_shadow"
    src.mkdir(parents=True)
    sig = "2026-01-12"
    source_path = src / "ca_discovery.parquet"
    _discovery_rows("ABC.TO", session_date=sig, market="CA").to_parquet(
        source_path, index=False
    )
    source_before = source_path.read_bytes()
    close = _trend(180)
    monkeypatch.setattr(pdg.board_ledger, "_name_close", lambda *_a, **_k: close)
    monkeypatch.setattr(pdg.board_ledger, "_bench_close", lambda *_a, **_k: close)
    monkeypatch.setattr(pdg.board_ledger, "_is_suspended", lambda *_a, **_k: False)

    receipt = pdg.grade_market("CA")
    assert receipt["candidate_metrics"]["n_observations"] == 1
    assert receipt["candidate_metrics"]["horizons"]["21d"]["n_matured"] == 1
    assert receipt["candidate_metrics"]["terminal_states"]["clean8_21"]["n_matured"] == 1
    assert receipt["source_artifact"] == "prophet_shadow/ca_discovery.parquet"
    assert receipt["output_artifact"] == "prophet_shadow/ca_discovery_outcomes.parquet"
    assert receipt["source_cutoff"] == sig
    assert receipt["source_session_count"] == 1
    assert len(receipt["source_identity_digest"]) == 64
    assert len(receipt["outcome_identity_digest"]) == 64
    assert receipt["source_identity_digest"] == receipt["outcome_identity_digest"]
    assert receipt["identity_parity"] is True
    assert len(receipt["source_cohort_digest"]) == 64
    assert len(receipt["outcome_cohort_digest"]) == 64
    assert receipt["source_cohort_digest"] == receipt["outcome_cohort_digest"]
    assert receipt["cohort_parity"] is True
    assert receipt["source_contract"] == "lane_b_append_only_keep_first"
    assert source_path.read_bytes() == source_before
    assert sorted(path.name for path in src.iterdir()) == [
        "ca_discovery.parquet",
        "ca_discovery_outcomes.parquet",
    ]


def test_prophet_discovery_outcome_preserves_discovery_reason_and_availability(monkeypatch):
    from engine import prophet_discovery_grade as pdg

    close = _trend(180)
    sig = str(close.index[5].date())
    discovery = _discovery_rows("0005.HK", session_date=sig)
    discovery["candidate_origin"] = "washout_reclaim+hk_native_onset(southbound)"
    discovery["availability_status"] = "WAIT_CONFLUENCE"
    discovery["availability_source"] = "hk_signal_gate"

    monkeypatch.setattr(pdg.board_ledger, "_name_close", lambda *_a, **_k: close)
    monkeypatch.setattr(pdg.board_ledger, "_bench_close", lambda *_a, **_k: close)
    monkeypatch.setattr(pdg.board_ledger, "_is_suspended", lambda *_a, **_k: False)

    row = pdg.grade_frame("HK", discovery).iloc[0]
    assert row["candidate_origin"] == "washout_reclaim+hk_native_onset(southbound)"
    assert row["availability_status"] == "WAIT_CONFLUENCE"
    assert row["availability_source"] == "hk_signal_gate"


def test_prophet_discovery_summary_stratifies_origin_tokens_and_availability():
    from engine import prophet_discovery_grade as pdg

    frame = pd.DataFrame([
        {
            "outcome_state": pdg.MATURED,
            "candidate_origin": "washout_reclaim+hk_native_onset(southbound)",
            "availability_status": "WAIT_CONFLUENCE",
            "fwd_mfe_5": 0.06, "fwd_mdd_5": -0.01, "excess_ret_5": 0.03,
            "terminal_state_clean8_21": None, "terminal_state_clean15_126": None,
        },
        {
            "outcome_state": pdg.MATURED,
            "candidate_origin": "hk_native_onset(southbound)",
            "availability_status": "ENTRY_OPEN",
            "fwd_mfe_5": 0.04, "fwd_mdd_5": -0.02, "excess_ret_5": 0.01,
            "terminal_state_clean8_21": None, "terminal_state_clean15_126": None,
        },
        {
            "outcome_state": pdg.ACCRUING,
            "candidate_origin": "ripening",
            "availability_status": "WAIT_PULLBACK",
            "fwd_mfe_5": None, "fwd_mdd_5": None, "excess_ret_5": None,
            "terminal_state_clean8_21": None, "terminal_state_clean15_126": None,
        },
    ])

    summary = pdg.summarize_outcomes(frame)
    native = summary["by_origin_token"]["hk_native_onset(southbound)"]
    assert native["n_observations"] == 2
    assert native["horizons"]["5d"]["n_matured"] == 2
    assert native["horizons"]["5d"]["mfe_median"] == pytest.approx(0.05)
    assert native["horizons"]["5d"]["excess_ret_median"] == pytest.approx(0.02)

    wash = summary["by_origin_token"]["washout_reclaim"]
    assert wash["n_observations"] == 1
    assert wash["horizons"]["5d"]["mfe_median"] == pytest.approx(0.06)

    entry = summary["by_availability"]["ENTRY_OPEN"]
    assert entry["n_observations"] == 1
    assert entry["horizons"]["5d"]["excess_ret_median"] == pytest.approx(0.01)

    wait = summary["by_availability"]["WAIT_CONFLUENCE"]
    assert wait["n_observations"] == 1
    assert wait["horizons"]["5d"]["excess_ret_median"] == pytest.approx(0.03)

    # Token cohorts overlap by design; they are descriptive evidence, never a
    # partition whose counts may be summed or a hidden promotion/ranking rule.
    assert summary["cohort_semantics"] == "overlapping_descriptive_only"


def test_prophet_discovery_board_admission_bridge_separates_prior_same_day_and_miss():
    from engine import prophet_discovery_grade as pdg

    discovery = pd.DataFrame([
        {"session_date": "2026-01-01", "security_ref_raw": "A.HK"},
        {"session_date": "2026-01-03", "security_ref_raw": "B.HK"},
        {"session_date": "2026-01-05", "security_ref_raw": "C.HK"},
        # repeated discovery must not double-count the first-surface clock
        {"session_date": "2026-01-04", "security_ref_raw": "A.HK"},
    ])
    board = pd.DataFrame([
        {"date": "2026-01-05", "ticker": "A.HK"},
        {"date": "2026-01-03", "ticker": "B.HK"},
        {"date": "2026-01-05", "ticker": "D.HK"},
        # outside the observed discovery-history window; excluded from denominator
        {"date": "2026-01-06", "ticker": "E.HK"},
        # duplicate same-day board row must not widen the denominator
        {"date": "2026-01-05", "ticker": "A.HK"},
    ])

    s = pdg.summarize_board_admission_bridge(discovery, board)
    assert s["available"] is True
    assert s["window"] == {"from": "2026-01-01", "to": "2026-01-05"}
    assert s["n_first_board_admissions"] == 3
    assert s["n_prior_discovered"] == 1
    assert s["n_same_day_only"] == 1
    assert s["n_never_discovered"] == 1
    assert s["prior_discovery_recall_rate"] == pytest.approx(1 / 3)
    assert s["prior_or_same_day_surface_rate"] == pytest.approx(2 / 3)
    assert s["calendar_lead_days"]["n"] == 1
    assert s["calendar_lead_days"]["median"] == pytest.approx(4.0)
    assert s["calendar_lead_days"]["p25"] == pytest.approx(4.0)
    assert s["calendar_lead_days"]["p75"] == pytest.approx(4.0)
    assert s["metric_semantics"] == "board_admission_not_eventual_winner"
    assert "eventual_winner_recall" not in s
    assert s["history_coverage"] == "window_bounded_positive_records_only"
    assert s["continuous_tenure_supported"] is False
    assert s["exact_exit_supported"] is False
    assert s["exit_reason_supported"] is False


def test_prophet_discovery_board_admission_bridge_excludes_pre_window_positive_records():
    from engine import prophet_discovery_grade as pdg

    discovery = pd.DataFrame([
        {"session_date": "2026-01-01", "security_ref_raw": "OLD.HK"},
        {"session_date": "2026-01-01", "security_ref_raw": "NEW.HK"},
        {"session_date": "2026-01-05", "security_ref_raw": "TAIL.HK"},
    ])
    board = pd.DataFrame([
        # OLD is positively recorded before the discovery window. Its Jan-03
        # reappearance cannot be relabeled as a first admission.
        {"date": "2025-12-31", "ticker": "OLD.HK"},
        {"date": "2026-01-03", "ticker": "OLD.HK"},
        {"date": "2026-01-04", "ticker": "NEW.HK"},
        # Post-window first records remain outside the denominator.
        {"date": "2026-01-06", "ticker": "TAIL.HK"},
    ])

    s = pdg.summarize_board_admission_bridge(discovery, board)
    assert s["available"] is True
    assert s["n_first_board_admissions"] == 1
    assert s["n_prior_discovered"] == 1
    assert s["prior_discovery_recall_rate"] == pytest.approx(1.0)
    assert s["n_pre_window_positive_board_records_excluded"] == 1
    assert s["first_admission_basis"] == "first_positive_board_record_in_available_ledger"


def test_prophet_discovery_board_admission_bridge_degrades_without_board_store():
    from engine import prophet_discovery_grade as pdg

    discovery = pd.DataFrame([
        {"session_date": "2026-01-01", "security_ref_raw": "A.HK"},
    ])
    s = pdg.summarize_board_admission_bridge(discovery, None)
    assert s == {
        "available": False,
        "reason": "board_store_absent",
        "metric_semantics": "board_admission_not_eventual_winner",
        "history_coverage": "window_bounded_positive_records_only",
        "continuous_tenure_supported": False,
        "exact_exit_supported": False,
        "exit_reason_supported": False,
    }


def test_prophet_discovery_grade_market_receipt_includes_board_admission_bridge(
    tmp_path, monkeypatch
):
    from engine import prophet_discovery_grade as pdg
    from lib import config

    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    src = tmp_path / "prophet_shadow"
    src.mkdir(parents=True)
    discovery = _discovery_rows("ABC.TO", session_date="2026-01-02", market="CA")
    pd.concat([
        discovery,
        _discovery_rows("XYZ.TO", session_date="2026-01-03", market="CA"),
    ], ignore_index=True).to_parquet(src / "ca_discovery.parquet", index=False)

    close = _trend(180)
    monkeypatch.setattr(pdg.board_ledger, "_name_close", lambda *_a, **_k: close)
    monkeypatch.setattr(pdg.board_ledger, "_bench_close", lambda *_a, **_k: close)
    monkeypatch.setattr(pdg.board_ledger, "_is_suspended", lambda *_a, **_k: False)
    monkeypatch.setattr(
        pdg.board_shadow,
        "_read_board_parquet",
        lambda *_a, **_k: pd.DataFrame([
            {"date": "2026-01-03", "ticker": "ABC.TO"},
            {"date": "2026-01-03", "ticker": "XYZ.TO"},
        ]),
    )

    receipt = pdg.grade_market("CA")
    bridge = receipt["board_admission_bridge"]
    assert bridge["available"] is True
    assert bridge["n_first_board_admissions"] == 2
    assert bridge["n_prior_discovered"] == 1
    assert bridge["n_same_day_only"] == 1
    assert bridge["prior_discovery_recall_rate"] == pytest.approx(0.5)

def _rank_race_fixture(*, challenger="hk_h3_ah_discount_rank_v1", covered=10):
    pairs = []
    outcomes = []
    dates = pd.bdate_range("2026-01-05", periods=6)
    for d in dates:
        ds = str(d.date())
        for i in range(1, 11):
            ticker = f"T{i:02d}.HK"
            pairs.append({
                "date": ds,
                "market": "HK",
                "ticker": ticker,
                "incumbent_definition": "hk_prophet_v2",
                "incumbent_rank": i,
                "incumbent_lane": "buy",
                "challenger_definition": challenger,
                "challenger_rank": (11 - i) if i <= covered else None,
                "challenger_rank_domain": "minted_population",
                "challenger_score_raw": float(11 - i) if i <= covered else None,
                "challenger_score_conservative": None,
                "challenger_coverage": covered / 10,
                "population_n": 10,
                "challenger_offlist_n": 0,
            })
            outcomes.append({
                "session_date": ds,
                "security_ref": ticker,
                "security_ref_raw": ticker,
                "excess_ret_5": float(11 - i) / 100.0,
                "excess_ret_21": float(11 - i) / 100.0,
            })
    return pd.DataFrame(pairs), pd.DataFrame(outcomes)


def test_prophet_rank_race_uses_same_covered_names_and_canonical_rank_ic():
    from engine import prophet_discovery_grade as pdg

    pairs, outcomes = _rank_race_fixture()
    summary = pdg.summarize_rank_races(pairs, outcomes)
    assert summary["available"] is True
    assert summary["metric_semantics"] == "same_population_same_outcomes_shadow_rank_race"

    race = summary["challengers"]["hk_h3_ah_discount_rank_v1"]
    assert race["n_population_rows"] == 60
    assert race["n_ranked_rows"] == 60
    assert race["observed_coverage_rate"] == pytest.approx(1.0)
    assert race["challenger_offlist_n_max"] == 0

    h5 = race["horizons"]["5d"]
    assert h5["n_paired_dates"] == 6
    assert h5["incumbent_rank_ic"]["mean_ic"] == pytest.approx(1.0)
    assert h5["challenger_rank_ic"]["mean_ic"] == pytest.approx(-1.0)
    assert h5["challenger_minus_incumbent_ic"]["mean_ic"] == pytest.approx(-2.0)
    assert h5["incumbent_rank_ic"]["hac_lags_requested"] == 5
    assert h5["challenger_rank_ic"]["hac_lags_requested"] == 5


def test_prophet_rank_race_h21_reports_preregistered_top_k_regret():
    from engine import prophet_discovery_grade as pdg

    pairs, outcomes = _rank_race_fixture()
    summary = pdg.summarize_rank_races(pairs, outcomes)
    h21 = summary["challengers"]["hk_h3_ah_discount_rank_v1"]["horizons"]["21d"]
    regret = h21["top_k_regret"]

    assert regret["definition"] == (
        "oracle_mean_excess_21-minus-arm_topk_mean_excess_21"
    )
    assert regret["1"]["n_dates"] == 6
    assert regret["1"]["incumbent_mean_regret"] == pytest.approx(0.0)
    assert regret["1"]["challenger_mean_regret"] == pytest.approx(0.09)
    assert regret["5"]["incumbent_mean_regret"] == pytest.approx(0.0)
    assert regret["5"]["challenger_mean_regret"] == pytest.approx(0.05)
    assert regret["top_decile"]["k_min"] == 1
    assert regret["top_decile"]["k_max"] == 1
    assert regret["top_decile"]["challenger_mean_regret"] == pytest.approx(0.09)


def test_prophet_rank_race_h21_regret_unmatured_is_not_zero():
    from engine import prophet_discovery_grade as pdg

    pairs, outcomes = _rank_race_fixture()
    outcomes = outcomes.drop(columns=["excess_ret_21"])
    summary = pdg.summarize_rank_races(pairs, outcomes)
    regret = summary["challengers"]["hk_h3_ah_discount_rank_v1"]["horizons"]["21d"][
        "top_k_regret"
    ]
    assert regret["1"]["n_dates"] == 0
    assert regret["1"]["incumbent_mean_regret"] is None
    assert regret["1"]["challenger_mean_regret"] is None
    assert regret["5"]["n_dates"] == 0
    assert regret["top_decile"]["n_dates"] == 0


def test_prophet_rank_race_surfaces_offlist_attempt_without_widening_population():
    from engine import prophet_discovery_grade as pdg

    pairs, outcomes = _rank_race_fixture()
    pairs["challenger_offlist_n"] = 3
    outcomes = pd.concat([
        outcomes,
        pd.DataFrame([{
            "session_date": str(pd.bdate_range("2026-01-05", periods=1)[0].date()),
            "security_ref": "OFFLIST.HK",
            "security_ref_raw": "OFFLIST.HK",
            "excess_ret_5": 9.99,
        }]),
    ], ignore_index=True)

    summary = pdg.summarize_rank_races(pairs, outcomes)
    race = summary["challengers"]["hk_h3_ah_discount_rank_v1"]
    assert summary["available"] is True
    assert race["n_population_rows"] == 60
    assert race["n_ranked_rows"] == 60
    assert race["challenger_offlist_n_max"] == 3
    assert race["horizons"]["5d"]["n_paired_dates"] == 6


def test_prophet_rank_race_never_gives_incumbent_credit_on_names_challenger_could_not_rank():
    from engine import prophet_discovery_grade as pdg

    pairs, outcomes = _rank_race_fixture(covered=5)
    summary = pdg.summarize_rank_races(pairs, outcomes)
    race = summary["challengers"]["hk_h3_ah_discount_rank_v1"]
    assert race["observed_coverage_rate"] == pytest.approx(0.5)
    h5 = race["horizons"]["5d"]
    # Canonical rank_ic requires 10 joint names. If incumbent were evaluated
    # on its full population instead of the challenger's covered subset, this
    # would report six positive IC dates and falsely flatter the incumbent.
    assert h5["n_paired_dates"] == 0
    assert h5["incumbent_rank_ic"] == {"n": 0}
    assert h5["challenger_rank_ic"] == {"n": 0}
    assert h5["challenger_minus_incumbent_ic"] == {"n": 0}


def test_prophet_rank_race_refuses_corrupt_population_denominator():
    from engine import prophet_discovery_grade as pdg

    pairs, outcomes = _rank_race_fixture()
    pairs.loc[
        (pairs["date"] == pairs["date"].iloc[0])
        & (pairs["ticker"] == "T10.HK"),
        "population_n",
    ] = 11
    summary = pdg.summarize_rank_races(pairs, outcomes)
    assert summary["available"] is False
    assert summary["reason"] == "rank_pair_population_contract_violation"
    assert summary["metric_semantics"] == "same_population_same_outcomes_shadow_rank_race"


def test_prophet_rank_race_refuses_fractional_population_denominator():
    from engine import prophet_discovery_grade as pdg

    pairs, outcomes = _rank_race_fixture()
    pairs["population_n"] = pairs["population_n"].astype(float)
    first_date = pairs["date"].iloc[0]
    pairs.loc[pairs["date"] == first_date, "population_n"] = 10.5
    summary = pdg.summarize_rank_races(pairs, outcomes)
    assert summary["available"] is False
    assert summary["reason"] == "rank_pair_population_contract_violation"
    assert summary["metric_semantics"] == "same_population_same_outcomes_shadow_rank_race"


@pytest.mark.parametrize(
    ("column", "bad_value"),
    [
        ("incumbent_rank", np.inf),
        ("challenger_rank", np.inf),
        ("challenger_offlist_n", np.inf),
    ],
)
def test_prophet_rank_race_refuses_non_finite_persisted_inputs(column, bad_value):
    from engine import prophet_discovery_grade as pdg

    pairs, outcomes = _rank_race_fixture()
    pairs[column] = pairs[column].astype(float)
    pairs.loc[pairs.index[0], column] = bad_value
    summary = pdg.summarize_rank_races(pairs, outcomes)
    assert summary["available"] is False
    assert summary["reason"] == "rank_pair_population_contract_violation"
    assert summary["metric_semantics"] == "same_population_same_outcomes_shadow_rank_race"


@pytest.mark.parametrize(
    ("column", "bad_value"),
    [
        ("population_n", None),
        ("challenger_coverage", None),
        ("challenger_offlist_n", None),
        ("challenger_offlist_n", -1),
        ("challenger_offlist_n", 0.5),
        ("challenger_offlist_n", 1),
    ],
)
def test_prophet_rank_race_refuses_partial_or_invalid_group_metadata(
    column, bad_value,
):
    from engine import prophet_discovery_grade as pdg

    pairs, outcomes = _rank_race_fixture()
    pairs[column] = pairs[column].astype(object)
    pairs.loc[pairs.index[0], column] = bad_value

    summary = pdg.summarize_rank_races(pairs, outcomes)
    assert summary["available"] is False
    assert summary["reason"] == "rank_pair_population_contract_violation"


def test_prophet_rank_race_refuses_missing_incumbent_rank():
    from engine import prophet_discovery_grade as pdg

    pairs, outcomes = _rank_race_fixture()
    pairs["incumbent_rank"] = pairs["incumbent_rank"].astype(float)
    pairs.loc[pairs.index[0], "incumbent_rank"] = np.nan

    summary = pdg.summarize_rank_races(pairs, outcomes)
    assert summary["available"] is False
    assert summary["reason"] == "rank_pair_population_contract_violation"


def test_prophet_rank_race_store_absence_is_explicit(tmp_path, monkeypatch):
    from engine import prophet_discovery_grade as pdg
    from lib import config

    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    result = pdg.evaluate_rank_races("HK")
    assert result == {
        "available": False,
        "reason": "rank_pair_store_absent",
        "metric_semantics": "same_population_same_outcomes_shadow_rank_race",
    }

def test_prophet_rank_race_refuses_stored_coverage_mismatch():
    from engine import prophet_discovery_grade as pdg

    pairs, outcomes = _rank_race_fixture(covered=5)
    pairs["challenger_coverage"] = 1.0
    summary = pdg.summarize_rank_races(pairs, outcomes)
    assert summary["available"] is False
    assert summary["reason"] == "rank_pair_population_contract_violation"


def test_prophet_rank_race_store_refuses_foreign_market_rows(tmp_path, monkeypatch):
    from engine import prophet_discovery_grade as pdg
    from lib import config

    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    pairs, _outcomes = _rank_race_fixture()
    pairs["market"] = "CA"
    path = tmp_path / "prophet_shadow" / "hk_rank_pairs.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pairs.to_parquet(path, index=False)

    result = pdg.evaluate_rank_races("HK")
    assert result == {
        "available": False,
        "reason": "rank_pair_store_foreign_market",
        "metric_semantics": "same_population_same_outcomes_shadow_rank_race",
    }

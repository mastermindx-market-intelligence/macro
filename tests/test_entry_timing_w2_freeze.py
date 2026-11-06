"""Entry Timing W2 freeze inputs — synthetic contract tests (no price, outcome or registry read)."""
import pandas as pd
import pytest

from research.prophet_v4 import entry_timing_w2_freeze as fz


def _sessions(n=300, start="2025-06-02"):
    return [d.strftime("%Y-%m-%d") for d in pd.bdate_range(start, periods=n)]


def test_extend_projects_weekdays_minus_declared_holidays(monkeypatch):
    monkeypatch.setattr(fz, "NYSE_HOLIDAYS_AHEAD", ["2026-11-26"])
    s = ["2026-11-24", "2026-11-25"]
    out = fz.extend(s, 4)
    assert out == ["2026-11-24", "2026-11-25", "2026-11-27", "2026-11-30", "2026-12-01"]


def test_t3_gate_reads_only_the_panel_date_index_and_counts_session_missing(tmp_path, monkeypatch):
    s = _sessions()
    monkeypatch.setattr(fz, "PANEL", str(tmp_path / "{ticker}.parquet"))
    full = pd.DataFrame({"close": 1.0}, index=pd.to_datetime(s))
    full.to_parquet(tmp_path / "AAA.parquet")
    holey = full.drop(pd.Timestamp(s[150]))
    holey.to_parquet(tmp_path / "BBB.parquet")
    units = [{"episode_id": "e1", "ticker": "AAA", "t_disc": s[200], "status": "IDENTIFIED_EXACT"},
             {"episode_id": "e2", "ticker": "BBB", "t_disc": s[200], "status": "IDENTIFIED_EXACT"},
             {"episode_id": "e3", "ticker": "ZZZ", "t_disc": s[200], "status": "IDENTIFIED_EXACT"},
             {"episode_id": "e4", "ticker": "AAA", "t_disc": s[200], "status": "CENSORED"}]
    g = fz.t3_gate(units, s)
    assert g["exact_pairs"] == 3 and g["pairs_passing"] == 1 and g["t3_in_p_family"] is False
    by = {r["episode_id"]: r for r in g["pairs"]}
    assert by["e2"]["missing_sessions"] == 1 and by["e2"]["first_missing"] == [s[150]]
    assert by["e3"]["panel"] == "absent" and by["e3"]["missing_sessions"] == fz.T3_LOOKBACK_SESSIONS
    # the lookback window ends at t_disc - 1: a hole AT t_disc does not count
    holey2 = full.drop(pd.Timestamp(s[200]))
    holey2.to_parquet(tmp_path / "BBB.parquet")
    assert {r["episode_id"]: r["pass"] for r in fz.t3_gate(units[:2], s)["pairs"]}["e2"] is True


def test_maturity_is_first_session_after_latest_fill_plus_H():
    s = _sessions()
    units = [{"status": "IDENTIFIED_EXACT", "t_disc": s[100], "k_disc": s[101], "k_cur": s[105]},
             {"status": "CENSORED", "t_disc": s[120], "k_disc": s[121], "k_cur": None},
             {"status": "INCUMBENT_LED", "t_disc": s[250], "k_disc": s[251], "k_cur": None}]
    m = fz.maturity(units, s, K=10, H=10)
    assert m["latest_t_exec"] == {"T0": s[122], "T1": s[106], "T2": s[124], "T3_bound": s[131]}
    assert m["maturity_session_observed_arms"] == s[124 + 10 + 1]
    assert m["maturity_session_with_t3_bound"] == s[131 + 10 + 1]

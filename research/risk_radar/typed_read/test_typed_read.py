"""Tests for the typed-read harness. Synthetic data only.

Run from the worktree root:
    python3 -m pytest research/risk_radar/typed_read -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import typed_read as tr  # noqa: E402


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def types_frame(dates, labels, reasons=None, **flag_overrides) -> pd.DataFrame:
    n = len(dates)
    df = pd.DataFrame({
        "date": list(dates),
        "core_label": list(labels),
        "core_reason": list(reasons) if reasons is not None else [""] * n,
    })
    for col in tr.FLAG_COLUMNS:
        df[col] = "present"
    for col, values in flag_overrides.items():
        df[col] = values
    return df


def turns_frame(dates, clusters, series="SPY") -> pd.DataFrame:
    return pd.DataFrame({"date": list(dates), "series": series,
                         "cluster_id": list(clusters)})


def one_era(name="T", start="2021-01-01", end="2021-12-31"):
    return (tr.era(name, start, end),)


def cell(result, era, dimension, value):
    hits = [c for c in result["cells"]
            if c["era"] == era and c["dimension"] == dimension and c["value"] == value]
    assert len(hits) == 1, f"expected one cell for {era}/{dimension}/{value}, got {len(hits)}"
    return hits[0]


# --------------------------------------------------------------------------
# format validation
# --------------------------------------------------------------------------
def test_unknown_core_label_raises():
    df = types_frame(["2021-01-04"], ["X"])
    with pytest.raises(tr.TypedReadError, match="unknown label"):
        tr.validate_types(df)


def test_unknown_flag_state_raises():
    df = types_frame(["2021-01-04"], ["B"], flag_rate=["maybe"])
    with pytest.raises(tr.TypedReadError, match="unknown state"):
        tr.validate_types(df)


def test_price_stress_easing_partial_only_on_easing():
    ok = types_frame(["2021-01-04"], ["B"], flag_easing=[tr.PRICE_STRESS_EASING_PARTIAL])
    tr.validate_types(ok)                       # accepted on easing
    bad = types_frame(["2021-01-04"], ["B"], flag_rate=[tr.PRICE_STRESS_EASING_PARTIAL])
    with pytest.raises(tr.TypedReadError, match="unknown state"):
        tr.validate_types(bad)


def test_duplicate_dates_raise():
    df = types_frame(["2021-01-04", "2021-01-04"], ["B", "N"])
    with pytest.raises(tr.TypedReadError, match="duplicate date"):
        tr.validate_types(df)


def test_non_u_label_with_reason_raises():
    df = types_frame(["2021-01-04"], ["B"], reasons=["MISSING_INPUT"])
    with pytest.raises(tr.TypedReadError, match="non-U label carries a reason"):
        tr.validate_types(df)


def test_u_without_reason_raises():
    df = types_frame(["2021-01-04"], ["U"], reasons=[""])
    with pytest.raises(tr.TypedReadError, match="U without a reason"):
        tr.validate_types(df)


def test_unknown_reason_code_raises():
    df = types_frame(["2021-01-04"], ["U"], reasons=["SOMETHING_ELSE"])
    with pytest.raises(tr.TypedReadError, match="unknown reason code"):
        tr.validate_types(df)


def test_blank_flag_value_raises():
    df = types_frame(["2021-01-04"], ["B"], flag_credit=[""])
    with pytest.raises(tr.TypedReadError, match="unknown state"):
        tr.validate_types(df)


def test_missing_column_raises():
    df = types_frame(["2021-01-04"], ["B"]).drop(columns=["flag_dollar"])
    with pytest.raises(tr.TypedReadError, match="missing required column"):
        tr.validate_types(df)


def test_turn_without_cluster_id_raises():
    df = pd.DataFrame({"date": ["2021-01-04"], "series": ["SPY"], "cluster_id": [None]})
    with pytest.raises(tr.TypedReadError, match="blank value"):
        tr.validate_turns(df)


def test_column_map_is_the_only_place_a_name_appears(monkeypatch):
    """Renaming the RD's columns needs only a COLUMNS edit, no logic change."""
    renamed = {k: "rd_" + v for k, v in tr.COLUMNS.items()}
    monkeypatch.setattr(tr, "COLUMNS", renamed)
    df = types_frame(["2021-01-04"], ["B"]).rename(columns=renamed)
    out = tr.validate_types(df)
    assert out.loc[pd.Timestamp("2021-01-04"), "core_label"] == "B"


# --------------------------------------------------------------------------
# unavailable is never absent
# --------------------------------------------------------------------------
def test_unavailable_is_not_counted_as_absent():
    dates = pd.bdate_range("2021-01-04", periods=10)
    df = types_frame(dates, ["B"] * 10,
                     flag_rate=["unavailable"] * 4 + ["absent"] * 3 + ["present"] * 3)
    types = tr.validate_types(df)
    res = tr.describe(types, tr.validate_turns(turns_frame([dates[0]], ["c1"])),
                      eras=one_era())
    assert cell(res, "T", "flag_rate", "unavailable")["sessions"] == 4
    assert cell(res, "T", "flag_rate", "absent")["sessions"] == 3
    assert cell(res, "T", "flag_rate", "present")["sessions"] == 3
    cov = res["coverage"][0]
    rate = [f for f in cov["flags"] if f["flag"] == "rate"][0]
    assert rate["unavailable"] == 4
    assert rate["unavailable_share"] == pytest.approx(0.4)
    assert rate["within_line"] is True          # exactly on the 40% line counts as within


def test_all_unavailable_flag_has_zero_absent():
    dates = pd.bdate_range("2021-01-04", periods=5)
    df = types_frame(dates, ["B"] * 5, flag_real_rate=["unavailable"] * 5)
    types = tr.validate_types(df)
    res = tr.describe(types, tr.validate_turns(turns_frame([dates[0]], ["c1"])),
                      eras=one_era())
    assert cell(res, "T", "flag_real_rate", "absent")["sessions"] == 0
    assert cell(res, "T", "flag_real_rate", "unavailable")["sessions"] == 5


# --------------------------------------------------------------------------
# <8 cluster suppression
# --------------------------------------------------------------------------
def _suppression_case(n_clusters: int):
    dates = pd.bdate_range("2021-01-04", periods=40)
    types = tr.validate_types(types_frame(dates, ["B"] * 40))
    turns = tr.validate_turns(turns_frame(dates[:n_clusters],
                                          [f"c{i}" for i in range(n_clusters)]))
    return tr.describe(types, turns, eras=one_era())


def test_seven_clusters_is_suppressed():
    c = cell(_suppression_case(7), "T", "core_label", "B")
    assert c["clusters"] == 7
    assert c["suppressed"] is True
    rendered = tr.render_output1(_suppression_case(7))
    assert "counts only" in rendered


def test_eight_clusters_is_not_suppressed():
    c = cell(_suppression_case(8), "T", "core_label", "B")
    assert c["clusters"] == 8
    assert c["suppressed"] is False


def test_suppressed_cell_prints_no_share():
    rendered = tr.render_output1(_suppression_case(7))
    row = [ln for ln in rendered.splitlines() if ln.startswith("| core_label | B |")][0]
    assert "counts only" in row
    assert "%" not in row


# --------------------------------------------------------------------------
# 2024 refusal
# --------------------------------------------------------------------------
def test_types_date_on_cutoff_raises():
    df = types_frame(["2024-01-02"], ["B"])
    with pytest.raises(tr.TypedReadError, match="refused"):
        tr.validate_types(df)


def test_types_date_after_cutoff_raises():
    df = types_frame(["2024-06-03"], ["B"])
    with pytest.raises(tr.TypedReadError, match="refused"):
        tr.validate_types(df)


def test_turns_date_on_cutoff_raises():
    df = turns_frame(["2024-01-02"], ["c1"])
    with pytest.raises(tr.TypedReadError, match="refused"):
        tr.validate_turns(df)


def test_alerts_date_on_cutoff_raises():
    df = pd.DataFrame({"date": ["2024-01-02"], "alert": [True]})
    with pytest.raises(tr.TypedReadError, match="refused"):
        tr.validate_alerts(df)


def test_era_ending_on_cutoff_raises():
    with pytest.raises(tr.TypedReadError, match="sealed cutoff"):
        tr.normalise_eras((tr.era("X", "2020-01-02", "2024-01-02"),))


def test_last_permitted_date_is_accepted():
    df = types_frame(["2024-01-01"], ["B"])
    tr.validate_types(df)                       # 2024-01-01 < 2024-01-02


# --------------------------------------------------------------------------
# guard
# --------------------------------------------------------------------------
def _ledger(tmp_path, rows) -> Path:
    p = tmp_path / "ledger.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return p


def test_guard_refuses_with_no_authority():
    with pytest.raises(tr.GuardRefusal, match="refused"):
        tr.check_guard()


def test_guard_refuses_ledger_without_row_id():
    with pytest.raises(tr.GuardRefusal, match="refused"):
        tr.check_guard(ledger_path="/nonexistent/ledger.jsonl")


def test_guard_refuses_missing_ledger_file(tmp_path):
    with pytest.raises(tr.GuardRefusal, match="ledger not found"):
        tr.check_guard(ledger_path=tmp_path / "nope.jsonl", row_id="r1")


def test_guard_refuses_unknown_row(tmp_path):
    p = _ledger(tmp_path, [{"id": "other", "typed_read_joint": True, "approved_by_rd": True}])
    with pytest.raises(tr.GuardRefusal, match="not found"):
        tr.check_guard(ledger_path=p, row_id="r1")


def test_guard_refuses_row_without_flags(tmp_path):
    p = _ledger(tmp_path, [{"id": "r1"}])
    with pytest.raises(tr.GuardRefusal, match="lacks"):
        tr.check_guard(ledger_path=p, row_id="r1")


def test_guard_refuses_row_with_only_one_flag(tmp_path):
    p = _ledger(tmp_path, [{"id": "r1", "typed_read_joint": True}])
    with pytest.raises(tr.GuardRefusal, match="approved_by_rd"):
        tr.check_guard(ledger_path=p, row_id="r1")


def test_guard_refuses_false_flags(tmp_path):
    p = _ledger(tmp_path, [{"id": "r1", "typed_read_joint": False, "approved_by_rd": True}])
    with pytest.raises(tr.GuardRefusal, match="typed_read_joint"):
        tr.check_guard(ledger_path=p, row_id="r1")


def test_guard_accepts_synthetic():
    assert tr.check_guard(synthetic=True) == {"mode": "synthetic"}


def test_guard_accepts_authorised_row(tmp_path):
    p = _ledger(tmp_path, [{"id": "r1", "typed_read_joint": True, "approved_by_rd": True}])
    assert tr.check_guard(ledger_path=p, row_id="r1") == {"mode": "ledger", "row_id": "r1"}


def test_guard_accepts_flags_inside_primary_spec(tmp_path):
    p = _ledger(tmp_path, [{"id": "r1", "primary_spec": {"typed_read_joint": True,
                                                         "approved_by_rd": True}}])
    assert tr.check_guard(ledger_path=p, row_id="r1")["mode"] == "ledger"


def test_per_leg_table_refuses_without_guard():
    dates = pd.bdate_range("2021-01-04", periods=30)
    types = tr.validate_types(types_frame(dates, ["B"] * 30))
    turns = turns_frame([dates[5]], ["c1"])
    alerts = pd.Series(False, index=dates)
    with pytest.raises(tr.GuardRefusal):
        tr.per_leg_table(alerts, turns, types)


def test_per_leg_table_runs_with_authorised_ledger_row(tmp_path):
    dates = pd.bdate_range("2021-01-04", periods=30)
    types = tr.validate_types(types_frame(dates, ["B"] * 30))
    turns = turns_frame([dates[5]], ["c1"])
    alerts = pd.Series(False, index=dates)
    p = _ledger(tmp_path, [{"id": "r1", "typed_read_joint": True, "approved_by_rd": True}])
    res = tr.per_leg_table(alerts, turns, types, ledger_path=p, row_id="r1",
                           eras=one_era())
    assert res["guard"] == {"mode": "ledger", "row_id": "r1"}


# --------------------------------------------------------------------------
# hand-computed small synthetic case, checked exactly
# --------------------------------------------------------------------------
def test_output1_hand_computed_case():
    """8 sessions, 3 turns, 3 clusters. Every number below is counted by hand."""
    dates = pd.date_range("2021-01-04", periods=8, freq="D")
    df = types_frame(
        dates,
        ["B", "B", "U", "N", "N", "U", "D", "S"],
        reasons=["", "", "MISSING_INPUT", "", "", "MISSING_INPUT", "", ""],
        flag_rate=["present"] * 5 + ["absent", "absent", "unavailable"],
    )
    types = tr.validate_types(df)
    turns = tr.validate_turns(turns_frame(dates[:3], ["c1", "c2", "c3"]))
    res = tr.describe(types, turns, eras=one_era())

    assert res["sessions_total"] == 8
    assert res["turns_total"] == 3
    assert res["unlabelled_turns"] == 0

    # core label: B 2 sessions (2 turns, 2 clusters), U 2 (1 turn, 1 cluster),
    # N 2 (0 turns), D 1, S 1
    b = cell(res, "T", "core_label", "B")
    assert (b["sessions"], b["turns"], b["clusters"]) == (2, 2, 2)
    assert b["session_share"] == pytest.approx(2 / 8)
    assert b["suppressed"] is True

    u = cell(res, "T", "core_label", "U")
    assert (u["sessions"], u["turns"], u["clusters"]) == (2, 1, 1)

    n = cell(res, "T", "core_label", "N")
    assert (n["sessions"], n["turns"], n["clusters"]) == (2, 0, 0)

    assert cell(res, "T", "core_label", "D")["sessions"] == 1
    assert cell(res, "T", "core_label", "S")["sessions"] == 1

    # flag_rate: present 5 sessions (all 3 turns), absent 2, unavailable 1
    assert cell(res, "T", "flag_rate", "present")["sessions"] == 5
    assert cell(res, "T", "flag_rate", "present")["turns"] == 3
    assert cell(res, "T", "flag_rate", "absent")["sessions"] == 2
    assert cell(res, "T", "flag_rate", "unavailable")["sessions"] == 1

    # coverage: U share 2/8 = 25% <= 40%; rate unavailable 1/8 = 12.5% <= 40%
    cov = res["coverage"][0]
    assert cov["sessions"] == 8
    assert cov["u_sessions"] == 2
    assert cov["u_share"] == pytest.approx(0.25)
    assert cov["u_share_within_line"] is True
    assert cov["u_reasons"] == {"MISSING_INPUT": 2, "CONFLICTING_STRUCTURE": 0,
                                "ENTRY_CONFIRMATION": 0}
    rate = [f for f in cov["flags"] if f["flag"] == "rate"][0]
    assert rate["unavailable"] == 1
    assert rate["unavailable_share"] == pytest.approx(0.125)
    assert rate["within_line"] is True
    for f in cov["flags"]:
        if f["flag"] != "rate":
            assert f["unavailable"] == 0


def test_output1_u_share_above_line_is_reported_not_applied():
    """Addendum A's 40% line is reported; nothing is suppressed or refused."""
    dates = pd.bdate_range("2021-01-04", periods=10)
    df = types_frame(dates, ["U"] * 6 + ["B"] * 4,
                     reasons=["MISSING_INPUT"] * 6 + [""] * 4)
    types = tr.validate_types(df)
    res = tr.describe(types, tr.validate_turns(turns_frame([dates[0]], ["c1"])),
                      eras=one_era())
    cov = res["coverage"][0]
    assert cov["u_share"] == pytest.approx(0.6)
    assert cov["u_share_within_line"] is False
    assert "no" in tr.render_output1(res)


def test_output2_hand_computed_case():
    """200 sessions, 2 turns, 2 clusters, 2 raw ON days. Counted by hand.

    raw ON at 44 and 100; the declared t+1 shift makes used ON at 45 and 101.
    turn c1 at 40 -> window [19,45] contains 45 -> caught.
    turn c2 at 160 -> window [139,165] contains neither -> not caught.
    starts at 45 (5 sessions after turn 40, inside post=5 -> not false) and at
    101 (nearest turn 59 sessions away -> false).
    """
    cal = pd.bdate_range("2021-01-04", periods=200)
    types = tr.validate_types(types_frame(cal, ["B"] * 200))
    turns = tr.validate_turns(turns_frame([cal[40], cal[160]], ["c1", "c2"]))
    alerts = pd.Series(False, index=cal)
    alerts.iloc[44] = True
    alerts.iloc[100] = True

    res = tr.per_leg_table(alerts, turns, types, synthetic=True, eras=one_era())
    assert res["clusters"] == 2
    assert res["catch_window"] == [-21, 5]
    assert res["shift_sessions"] == 1

    b = cell(res, "T", "core_label", "B")
    assert b["sessions"] == 200
    assert b["clusters"] == 2
    assert b["caught"] == 1
    assert b["catch_share"] == pytest.approx(0.5)
    assert b["false_calls"] == 1
    assert b["false_per_session_year"] == pytest.approx(1 / (200 / 252))
    assert b["suppressed"] is True              # 2 clusters < 8

    era_row = [c for c in res["cells"] if c["dimension"] == "__era__"][0]
    assert (era_row["clusters"], era_row["caught"], era_row["false_calls"]) == (2, 1, 1)


def test_output2_shift_is_applied():
    """An ON day exactly at the turn is NOT used at the turn; it is used one session later."""
    cal = pd.bdate_range("2021-01-04", periods=60)
    types = tr.validate_types(types_frame(cal, ["B"] * 60))
    turns = tr.validate_turns(turns_frame([cal[30]], ["c1"]))
    alerts = pd.Series(False, index=cal)
    alerts.iloc[30] = True                      # raw ON at the turn itself
    res = tr.per_leg_table(alerts, turns, types, synthetic=True, eras=one_era())
    b = cell(res, "T", "core_label", "B")
    # used ON at 31, which is still inside [30-21, 30+5] -> caught
    assert b["caught"] == 1
    # and the start is at 31, 1 session after the turn -> not false
    assert b["false_calls"] == 0


def test_output2_false_call_outside_window():
    cal = pd.bdate_range("2021-01-04", periods=60)
    types = tr.validate_types(types_frame(cal, ["B"] * 60))
    turns = tr.validate_turns(turns_frame([cal[5]], ["c1"]))
    alerts = pd.Series(False, index=cal)
    alerts.iloc[40] = True                      # used ON at 41, 36 sessions after turn 5
    res = tr.per_leg_table(alerts, turns, types, synthetic=True, eras=one_era())
    b = cell(res, "T", "core_label", "B")
    assert b["caught"] == 0
    assert b["false_calls"] == 1


def test_output2_cluster_caught_by_any_of_its_turns():
    cal = pd.bdate_range("2021-01-04", periods=120)
    types = tr.validate_types(types_frame(cal, ["B"] * 120))
    # one cluster, two turn dates far apart
    turns = tr.validate_turns(turns_frame([cal[10], cal[100]], ["c1", "c1"]))
    alerts = pd.Series(False, index=cal)
    alerts.iloc[99] = True                      # used ON at 100 -> catches the second turn
    res = tr.per_leg_table(alerts, turns, types, synthetic=True, eras=one_era())
    b = cell(res, "T", "core_label", "B")
    assert b["clusters"] == 1
    assert b["caught"] == 1


def test_output2_cell_uses_earliest_turn_date_for_its_label():
    """A cluster spanning two labels is assigned to the label of its earliest turn."""
    cal = pd.bdate_range("2021-01-04", periods=40)
    labels = ["B"] * 20 + ["D"] * 20
    types = tr.validate_types(types_frame(cal, labels))
    turns = tr.validate_turns(turns_frame([cal[5], cal[30]], ["c1", "c1"]))
    alerts = pd.Series(False, index=cal)
    res = tr.per_leg_table(alerts, turns, types, synthetic=True, eras=one_era())
    assert cell(res, "T", "core_label", "B")["clusters"] == 1
    assert cell(res, "T", "core_label", "D")["clusters"] == 0


def test_output2_suppression_prints_counts_only():
    cal = pd.bdate_range("2021-01-04", periods=60)
    types = tr.validate_types(types_frame(cal, ["B"] * 60))
    turns = tr.validate_turns(turns_frame([cal[5]], ["c1"]))
    alerts = pd.Series(False, index=cal)
    res = tr.per_leg_table(alerts, turns, types, synthetic=True, eras=one_era())
    rendered = tr.render_output2(res)
    row = [ln for ln in rendered.splitlines() if ln.startswith("| T | core_label | B |")][0]
    assert "counts only" in row


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def test_cli_describe_default_subcommand(tmp_path, capsys):
    dates = pd.bdate_range("2021-01-04", periods=10)
    tp = tmp_path / "types.csv"
    up = tmp_path / "turns.csv"
    types_frame(dates, ["B"] * 10).to_csv(tp, index=False)
    turns_frame(dates[:2], ["c1", "c2"]).to_csv(up, index=False)
    rc = tr.main(["--types", str(tp), "--turns", str(up),
                  "--eras", "T=2021-01-01:2021-12-31"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Typed read" in out
    assert "| core_label | B |" in out


def test_cli_per_leg_refuses_without_guard(tmp_path, capsys):
    dates = pd.bdate_range("2021-01-04", periods=10)
    tp, up, ap = tmp_path / "t.csv", tmp_path / "u.csv", tmp_path / "a.csv"
    types_frame(dates, ["B"] * 10).to_csv(tp, index=False)
    turns_frame(dates[:1], ["c1"]).to_csv(up, index=False)
    pd.DataFrame({"date": dates, "alert": False}).to_csv(ap, index=False)
    rc = tr.main(["per-leg", "--types", str(tp), "--turns", str(up), "--alerts", str(ap)])
    assert rc == 3
    assert "refused" in capsys.readouterr().err


def test_cli_per_leg_synthetic(tmp_path, capsys):
    dates = pd.bdate_range("2021-01-04", periods=10)
    tp, up, ap = tmp_path / "t.csv", tmp_path / "u.csv", tmp_path / "a.csv"
    types_frame(dates, ["B"] * 10).to_csv(tp, index=False)
    turns_frame(dates[:1], ["c1"]).to_csv(up, index=False)
    pd.DataFrame({"date": dates, "alert": False}).to_csv(ap, index=False)
    rc = tr.main(["per-leg", "--types", str(tp), "--turns", str(up), "--alerts", str(ap),
                  "--synthetic", "--eras", "T=2021-01-01:2021-12-31"])
    assert rc == 0
    assert "guard: synthetic" in capsys.readouterr().out


def test_parquet_roundtrip(tmp_path):
    dates = pd.bdate_range("2021-01-04", periods=10)
    p = tmp_path / "types.parquet"
    types_frame(dates, ["B"] * 10).to_parquet(p, index=False)
    out = tr.load_types(p)
    assert len(out) == 10


# --- RD FORMAT_RULINGS_001 #4: cluster cell = earliest turn's session; multi-label count ---
def test_cluster_takes_earliest_turn_label_and_multi_label_is_counted():
    dates = list(pd.bdate_range("2021-03-01", periods=4))
    types = tr.validate_types(types_frame(dates, ["B", "B", "D", "D"]))
    # c1 spans B then D (earliest B); c2 sits on D only
    turns = tr.validate_turns(pd.DataFrame({
        "date": [dates[0], dates[2], dates[3]], "series": ["SPY", "QQQ", "SPY"],
        "cluster_id": ["c1", "c1", "c2"]}))
    res = tr.describe(types, turns, eras=one_era())
    assert cell(res, "T", "core_label", "B")["clusters"] == 1
    assert cell(res, "T", "core_label", "D")["clusters"] == 1   # c2 only; c1 belongs to B
    assert cell(res, "T", "core_label", "D")["turns"] == 2      # turns stay on own session
    m = [x for x in res["multi_label_clusters"] if x["era"] == "T"][0]
    assert m == {"era": "T", "clusters": 2, "multi_core_label_clusters": 1}


def test_partial_easing_is_available_for_the_line():
    dates = list(pd.bdate_range("2021-03-01", periods=4))
    types = tr.validate_types(types_frame(
        dates, ["B"] * 4,
        flag_easing=[tr.PRICE_STRESS_EASING_PARTIAL, tr.PRICE_STRESS_EASING_PARTIAL, "absent", "present"]))
    res = tr.describe(types, tr.validate_turns(turns_frame([dates[0]], ["c1"])), eras=one_era())
    cov = [c for c in res["coverage"] if c["era"] == "T"][0]
    easing = [f for f in cov["flags"] if f["flag"] == "easing"][0]
    assert easing["unavailable"] == 0 and easing["within_line"]
    assert cell(res, "T", "flag_easing", tr.PRICE_STRESS_EASING_PARTIAL)["sessions"] == 2


# --------------------------------------------------------------------------
# the RD's type_history_v1 shape (synthetic values; TYPE_HISTORY_FORMAT.md v1)
# --------------------------------------------------------------------------
def _rd_v1_frame():
    idx = pd.DatetimeIndex(["2021-01-04", "2021-01-05", "2021-01-06"], name="date").astype("datetime64[ms]")
    df = pd.DataFrame({
        "raw_label": ["B", "B", "S"], "pub_label": ["U", "B", "U"],
        "reason": ["ENTRY_CONFIRMATION", "", "CONFLICTING_STRUCTURE"],
        "src_b": "dated", "src_db": "dated", "src_d": "dated", "src_q": "dated",
        "b": 0.5, "db": 0.0, "d": 1.0, "q_participation": 0.0,
        "median_b": 0.5, "p20_b": 0.3, "p80_d": 1.2,
        "flag_rate": ["present", "absent", "unavailable"], "flag_real_rate": "absent",
        "flag_credit_pressure": ["absent", "present", "absent"], "flag_credit_level": "absent",
        "flag_dollar": "absent", "flag_easing": ["absent", "PRICE_STRESS_EASING_PARTIAL", "absent"],
    }, index=idx)
    return df


def test_rd_v1_parquet_loads_by_index_with_pub_label_and_sha(tmp_path):
    import hashlib
    p = tmp_path / "type_history_v1.parquet"
    _rd_v1_frame().to_parquet(p)
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    out = tr.load_types(p, tr.RD_V1_COLUMNS, expect_sha256=sha)
    assert list(out["core_label"]) == ["U", "B", "U"]          # pub_label, never raw_label
    assert list(out["flag_credit"]) == ["absent", "present", "absent"]   # credit_pressure
    assert out.loc[pd.Timestamp("2021-01-06"), "flag_rate"] == "unavailable"
    with pytest.raises(tr.TypedReadError, match="differs from the pin"):
        tr.load_types(p, tr.RD_V1_COLUMNS, expect_sha256="0" * 64)


def test_rd_v1_refuses_blank_u_reason(tmp_path):
    df = _rd_v1_frame()
    df.loc[df.index[0], "reason"] = ""
    p = tmp_path / "t.parquet"
    df.to_parquet(p)
    with pytest.raises(tr.TypedReadError, match="U without a reason"):
        tr.load_types(p, tr.RD_V1_COLUMNS)

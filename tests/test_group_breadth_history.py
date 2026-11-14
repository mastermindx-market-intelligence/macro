"""Tests for engine.group_breadth_history — within-group breadth, one code path.

Synthetic made-up numbers only; no file reads. What is pinned:

  (a) causality — every output column of daily_group_breadth and
      weekly_fixed_set at row t is identical whether computed on closes[:t+1]
      or on the full matrix (a value never uses data dated after its own row);
  (b) hand-checked level arithmetic on a tiny matrix with windows=(3,) /
      min_members=2, and the ruled MIN_MEMBERS=10 rule: 9 qualifying members
      -> shares, changes and ranks are MISSING, never zero;
  (c) fixed-set arithmetic — membership reassignment moves the plain level
      difference but not the fixed-set change (hand-computed), and a name
      lacking history at t-k is excluded from the fixed set;
  (d) dated membership — start_date inclusive, end_date exclusive;
  (e) cross_rank — ties share the lower rank, NaN stays NaN, n_ranked counts
      valid groups;
  (f) sign_state — flat at exactly 0, None for NaN, run lengths reset on a
      sign change and after NaN;
  (g) week_end_rows — last session of each calendar week, including a
      holiday-shortened week and a trailing partial week;
  (h) member_rows — exact schema/order, non-members excluded, has/above flags,
      source_asof = the ticker's last valid close date.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import engine.group_breadth_history as gbh


def _cell(df: pd.DataFrame, d, group: str, col: str):
    """One (date, group) value from a long frame — asserts the row is unique."""
    row = df[(df["date"] == d) & (df["group"] == group)]
    assert len(row) == 1, f"expected exactly one row for {d}/{group}, got {len(row)}"
    return row.iloc[0][col]


# ── fixture: a random 260-session x 30-ticker universe ───────────────────────

def _random_universe(seed: int = 7, n_sessions: int = 260):
    """30 tickers in Tech(12) / Health(10) / Tiny(8), with gaps and late starts.

    Tiny has fewer than MIN_MEMBERS members — its shares must come out missing.
    """
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2025-01-02", periods=n_sessions)
    tickers = [f"T{i:02d}" for i in range(30)]
    closes = pd.DataFrame(
        100.0 * np.cumprod(1.0 + rng.normal(0.0, 0.012, (n_sessions, 30)), axis=0),
        index=idx, columns=tickers)
    mask = pd.DataFrame(rng.random((n_sessions, 30)) < 0.02,
                        index=idx, columns=tickers)
    mask.iloc[:30, :5] = True                       # five tickers start a month late
    closes = closes.mask(mask)
    membership = pd.DataFrame({
        "ticker": tickers,
        "group": ["Tech"] * 12 + ["Health"] * 10 + ["Tiny"] * 8,
    })
    return closes, membership


# ── (a) causality ────────────────────────────────────────────────────────────

def test_daily_causality_prefix_equals_full():
    """Row t of every daily column is identical on closes[:t+1] and the full matrix."""
    closes, membership = _random_universe()
    full = gbh.daily_group_breadth(closes, membership)
    for t in (60, 203, 240, 259):
        part = gbh.daily_group_breadth(closes.iloc[:t + 1], membership)
        f = full[full["date"] == closes.index[t]].reset_index(drop=True)
        p = part[part["date"] == closes.index[t]].reset_index(drop=True)
        assert len(f) == 3 and len(p) == 3
        pd.testing.assert_frame_equal(f, p)


def test_weekly_causality_prefix_equals_full():
    """Same for the weekly frame, cut at a full-matrix week-end session."""
    closes, membership = _random_universe()
    full = gbh.weekly_fixed_set(closes, membership)
    we = gbh.week_end_rows(closes.index)
    for t in (we[30], we[45]):
        part = gbh.weekly_fixed_set(closes.iloc[:t + 1], membership)
        f = full[full["date"] == closes.index[t]].reset_index(drop=True)
        p = part[part["date"] == closes.index[t]].reset_index(drop=True)
        assert len(f) == 3 and len(p) == 3
        pd.testing.assert_frame_equal(f, p)
    # a MID-week cut yields a partial-week row the full frame does not carry
    # (include_last_partial_week=True semantics), so nothing to compare there
    mid = we[30] + 2
    part = gbh.weekly_fixed_set(closes.iloc[:mid + 1], membership)
    assert closes.index[mid] not in set(full["date"])
    assert (part["date"] == closes.index[mid]).any()


def test_small_group_shares_missing_not_zero():
    """Fewer than MIN_MEMBERS qualifying members -> missing shares, never 0."""
    closes, membership = _random_universe()
    d = gbh.daily_group_breadth(closes, membership)
    tiny = d[d["group"] == "Tiny"]
    hot = tiny[tiny["n_above_50"] > 0]
    assert len(hot) > 0, "fixture must exercise above-counts > 0 for Tiny"
    for col in ("pct_above_50", "pct_above_200"):
        assert hot[col].isna().all(), f"{col} must be missing, not 0, under 10 members"


# ── (b) hand-checked level arithmetic + the 10-member rule ──────────────────

def test_hand_checked_level_arithmetic_small_windows():
    """windows=(3,), min_members=2 on a 5x4 matrix, verified by hand.

    MA3 (defined from row 2): A flat 10 -> never strictly above;
    B rising -> above on rows 2-4; C flat 5 -> never above;
    D [9,10,11,12,10]: above on rows 2,3, below on row 4.
    """
    idx = pd.bdate_range("2025-01-01", periods=5)
    closes = pd.DataFrame({
        "A": [10.0, 10, 10, 10, 10],
        "B": [1.0, 2, 3, 4, 5],
        "C": [5.0, 5, 5, 5, 5],
        "D": [9.0, 10, 11, 12, 10],
    }, index=idx)
    membership = pd.DataFrame({
        "ticker": ["A", "B", "C", "D"],
        "group": ["G1", "G1", "G2", "G2"],
    })
    d = gbh.daily_group_breadth(closes, membership, windows=(3,), horizons=(1,),
                                min_members=2)

    # no average exists before row 2 -> shares missing
    for g in ("G1", "G2"):
        assert np.isnan(_cell(d, idx[0], g, "pct_above_3"))
        assert np.isnan(_cell(d, idx[1], g, "pct_above_3"))

    # hand-checked shares: 100 * above / has, one rounding step
    for i in (2, 3):
        assert _cell(d, idx[i], "G1", "pct_above_3") == 50.0   # B above, A not
        assert _cell(d, idx[i], "G2", "pct_above_3") == 50.0   # D above, C not
    assert _cell(d, idx[4], "G1", "pct_above_3") == 50.0
    assert _cell(d, idx[4], "G2", "pct_above_3") == 0.0        # D closed below

    # counts are counts — never fenced to missing
    for g in ("G1", "G2"):
        assert [_cell(d, dt, g, "n_has_3") for dt in idx] == [0, 0, 2, 2, 2]
        assert [_cell(d, dt, g, "n_members") for dt in idx] == [2] * 5

    # changes: an exactly-unchanged share is exactly 0 (same-float subtraction)
    assert _cell(d, idx[3], "G1", "lvl_chg_pct_above_3_1") == 0.0
    assert _cell(d, idx[4], "G1", "lvl_chg_pct_above_3_1") == 0.0
    assert _cell(d, idx[4], "G2", "lvl_chg_pct_above_3_1") == -50.0
    assert _cell(d, idx[3], "G1", "fix_chg_pct_above_3_1") == 0.0
    assert _cell(d, idx[4], "G1", "fix_chg_pct_above_3_1") == 0.0
    assert _cell(d, idx[4], "G2", "fix_chg_pct_above_3_1") == -50.0  # 0% - 50%
    assert _cell(d, idx[4], "G2", "n_fixed_3_1") == 2


def test_ten_member_rule_nine_members_missing():
    """9 qualifying members -> NaN shares, NaN changes, NaN rank (ruled, not tuned)."""
    rng = np.random.default_rng(11)
    idx = pd.bdate_range("2025-01-02", periods=120)
    tick = [f"N{i}" for i in range(9)] + [f"W{i}" for i in range(12)]
    closes = pd.DataFrame(
        50.0 * np.cumprod(1.0 + rng.normal(0.0, 0.01, (120, 21)), axis=0),
        index=idx, columns=tick)
    membership = pd.DataFrame({
        "ticker": tick,
        "group": ["Nine"] * 9 + ["Twelve"] * 12,
    })
    d = gbh.daily_group_breadth(closes, membership, windows=(50,), horizons=(5,),
                                min_members=gbh.MIN_MEMBERS)
    nine = d[d["group"] == "Nine"]
    twelve = d[d["group"] == "Twelve"]

    for col in ("pct_above_50", "lvl_chg_pct_above_50_5", "fix_chg_pct_above_50_5",
                "rank_fix_chg_pct_above_50_5", "run_fix_chg_pct_above_50_5",
                "state_fix_chg_pct_above_50_5"):
        assert nine[col].isna().all(), f"Nine.{col} must be missing under 10 members"
    # counts stay counts; missing-not-zero is visible where above-counts exist
    assert (nine["n_above_50"] > 0).any()
    assert nine.loc[nine["n_above_50"] > 0, "pct_above_50"].isna().all()
    # the 12-member control group does produce shares and is the only ranked one
    assert twelve["pct_above_50"].notna().any()
    live = twelve[twelve["fix_chg_pct_above_50_5"].notna()]
    assert (live["n_ranked_fix_chg_pct_above_50_5"] == 1).all()


# ── (c) fixed-set arithmetic vs plain, under membership reassignment ────────

def test_fixed_set_change_vs_plain_under_reassignment():
    """C moves H -> G on d4; the plain difference moves, the fixed set does not.

    A flat 10 (never above), B rising (always above from row 2),
    C starts d1 (no 3-session history until row 3, above from then on).
    """
    idx = pd.bdate_range("2025-01-01", periods=6)
    closes = pd.DataFrame({
        "A": [10.0, 10, 10, 10, 10, 10],
        "B": [1.0, 2, 3, 4, 5, 6],
        "C": [np.nan, 20, 30, 40, 50, 60],
    }, index=idx)
    d4 = idx[4]
    membership = pd.DataFrame([
        {"ticker": "A", "group": "G"},
        {"ticker": "B", "group": "G"},
        {"ticker": "C", "group": "H", "end_date": d4},   # in H on d < d4
        {"ticker": "C", "group": "G", "start_date": d4},  # in G from d4
    ])
    d = gbh.daily_group_breadth(closes, membership, windows=(3,), horizons=(1, 2),
                                min_members=2)

    # before the move G = {A, B}: 1 of 2 above -> 50%
    assert _cell(d, idx[3], "G", "n_members") == 2
    assert _cell(d, idx[3], "G", "pct_above_3") == 50.0
    assert _cell(d, idx[3], "H", "n_members") == 1

    # at d4 G = {A, B, C}: 2 of 3 above -> 66.67%
    assert _cell(d, d4, "G", "n_members") == 3
    assert _cell(d, d4, "G", "pct_above_3") == pytest.approx(200.0 / 3)
    # plain difference: 66.67% now minus 50% then — the reassignment moved it
    assert _cell(d, d4, "G", "lvl_chg_pct_above_3_1") == pytest.approx(200.0 / 3 - 50.0)
    assert _cell(d, d4, "G", "lvl_chg_pct_above_3_2") == pytest.approx(200.0 / 3 - 50.0)
    # fixed set: the SAME three names are 2-for-3 above at d4 AND at d3 -> 0
    assert _cell(d, d4, "G", "fix_chg_pct_above_3_1") == 0.0
    assert _cell(d, d4, "G", "n_fixed_3_1") == 3
    # k=2: C has no 3-session history at d2 -> excluded from the fixed set
    assert _cell(d, d4, "G", "n_fixed_3_2") == 2
    # the remaining two (A, B) are 1-for-2 above at both d4 and d2 -> 0
    assert _cell(d, d4, "G", "fix_chg_pct_above_3_2") == 0.0


# ── (d) dated membership ─────────────────────────────────────────────────────

def test_dated_membership_windows_honoured():
    """Member ON start_date, OFF end_date (half-open interval); open ends work."""
    idx = pd.bdate_range("2025-01-01", periods=6)
    closes = pd.DataFrame({"X": [1.0] * 6, "Y": [2.0] * 6}, index=idx)
    membership = pd.DataFrame([
        {"ticker": "X", "group": "G", "start_date": idx[2], "end_date": idx[4]},
        {"ticker": "Y", "group": "G"},                    # open to past and future
    ])
    codes, groups = gbh.assign_groups(idx, ["X", "Y"], membership)
    assert groups == ["G"]
    assert list(codes[:, 0]) == [-1, -1, 0, 0, -1, -1], \
        "X must be a member on start_date..end_date-1 only"
    assert (codes[:, 1] == 0).all()

    d = gbh.daily_group_breadth(closes, membership, windows=(3,), horizons=(1,),
                                min_members=1)
    nm = d.set_index(["date", "group"])["n_members"]
    assert [nm.loc[(dt, "G")] for dt in idx] == [1, 1, 2, 2, 1, 1]


# ── (e) cross_rank ───────────────────────────────────────────────────────────

def test_cross_rank_ties_share_lower_rank_nan_stays_nan():
    chg = np.array([
        [5.0, 5.0, 3.0, np.nan, -1.0],
        [np.nan, np.nan, 1.0, 2.0, 0.0],
    ])
    rank, n_ranked = gbh.cross_rank(chg)
    np.testing.assert_array_equal(
        rank, np.array([[1.0, 1.0, 3.0, np.nan, 4.0],
                        [np.nan, np.nan, 2.0, 1.0, 3.0]]))
    assert list(n_ranked) == [4, 3]


# ── (f) sign_state ───────────────────────────────────────────────────────────

def test_sign_state_flat_at_zero_and_run_resets():
    chg = np.array([[1.0], [2.0], [0.0], [-1.0], [np.nan], [-2.0], [-3.0]])
    state, run = gbh.sign_state(chg)
    assert list(state[:, 0]) == [
        gbh.STATE_IMPROVING, gbh.STATE_IMPROVING, gbh.STATE_FLAT,
        gbh.STATE_DETERIORATING, None, gbh.STATE_DETERIORATING,
        gbh.STATE_DETERIORATING,
    ]
    # 1,2 (same state) | 1 (sign change) | 1 | NaN (missing) | 1 (reset after NaN), 2
    np.testing.assert_array_equal(
        run[:, 0], np.array([1.0, 2.0, 1.0, 1.0, np.nan, 1.0, 2.0]))


# ── (g) week_end_rows ────────────────────────────────────────────────────────

def test_week_end_rows_last_session_of_each_calendar_week():
    # week 1 holiday-shortened (no Fri 2025-11-07), week 2 full, week 3 partial
    idx = pd.DatetimeIndex([
        "2025-11-03", "2025-11-04", "2025-11-05", "2025-11-06",
        "2025-11-10", "2025-11-11", "2025-11-12", "2025-11-13", "2025-11-14",
        "2025-11-17", "2025-11-18", "2025-11-19",
    ])
    pos = gbh.week_end_rows(idx)
    assert pos.tolist() == [3, 8, 11]
    assert [idx[p].date().isoformat() for p in pos] == [
        "2025-11-06",   # Thursday ends the holiday-shortened week
        "2025-11-14",   # Friday ends the full week
        "2025-11-19",   # Wednesday ends the (partial) final week
    ]


def test_weekly_final_week_rule_keeps_thursday_drops_wednesday():
    idx = pd.bdate_range("2025-01-02", "2025-12-31")
    closes = pd.DataFrame({f"T{i}": 100.0 + np.arange(len(idx)) * (i + 1) * 0.01
                           for i in range(12)}, index=idx)
    mem = pd.DataFrame({"ticker": closes.columns, "group": "G"})
    thu = closes.loc[:"2025-12-18"]   # Thursday end (Good Friday-like week)
    wed = closes.loc[:"2025-12-17"]   # Wednesday end, week in progress
    w_thu = gbh.weekly_fixed_set(thu, mem, include_last_partial_week=False)
    w_wed = gbh.weekly_fixed_set(wed, mem, include_last_partial_week=False)
    assert pd.Timestamp(w_thu["date"].max()) == pd.Timestamp("2025-12-18")
    assert pd.Timestamp(w_wed["date"].max()) == pd.Timestamp("2025-12-12")


def test_through_last_complete_row_drops_partial_tail():
    idx = pd.bdate_range("2025-01-02", periods=30)
    closes = pd.DataFrame(100.0, index=idx, columns=[f"T{i}" for i in range(10)])
    closes.iloc[-1, 3:] = np.nan          # last row priced 3/10: in progress
    cut = gbh.through_last_complete_row(closes)
    assert cut.index[-1] == idx[-2]
    m = gbh.member_rows(cut, pd.DataFrame({"ticker": closes.columns, "group": "G"}))
    assert (m["date"] == idx[-2].date().isoformat()).all()
    assert gbh.through_last_complete_row(closes.iloc[:0]).empty


def test_duplicate_series_scan_flags_copy_and_counts_it_once():
    from scripts.build_group_breadth_history import count_duplicates_once, duplicate_series_pairs
    rng = np.random.default_rng(7)
    idx = pd.bdate_range("2020-01-01", periods=400)
    closes = pd.DataFrame({t: 50 * np.exp(np.cumsum(rng.normal(0, 0.01, 400)))
                           for t in ("AAA", "BBB", "CCC")}, index=idx)
    closes.loc[idx[200]:, "BBB"] = closes.loc[idx[200]:, "AAA"] * 0.5   # copied, scaled
    closes["FLAT"] = 20.75                                               # flat, never matched
    closes["FLT2"] = 20.75
    mem = pd.DataFrame({"ticker": list(closes.columns), "group": "G"})
    pairs = duplicate_series_pairs(closes, mem)
    assert list(zip(pairs["ticker_a"], pairs["ticker_b"])) == [("AAA", "BBB")]
    p = pairs.iloc[0]
    assert p["identical_from"] == str(idx[201].date()) and p["ratio_cv"] < 1e-6
    once = count_duplicates_once(closes, pairs)
    assert once.loc[idx[201]:, "BBB"].isna().all() and once["AAA"].notna().all()
    assert closes.loc[idx[201]:, "BBB"].notna().all(), "input is never modified"


def test_basket_build_counts_a_name_in_every_basket(tmp_path):
    import json
    from scripts.build_basket_breadth_history import build, expand_multi, membership_baskets
    doc = {"baskets": {
        "b1": {"members": [{"ticker": f"T{i}", "removed": None} for i in range(12)]},
        "b2": {"members": [{"ticker": f"T{i}", "removed": None} for i in range(6, 18)]
               + [{"ticker": "GONE", "removed": "2026-01-01"}]},
    }}
    mp = tmp_path / "membership.json"
    mp.write_text(json.dumps(doc))
    mem = membership_baskets(mp)
    assert "GONE" not in set(mem["ticker"]) and len(mem) == 24
    idx = pd.bdate_range("2024-01-01", periods=260)
    rng = np.random.default_rng(3)   # independent series: identical returns would be flagged as copies
    closes = pd.DataFrame({f"T{i}": 100 * np.exp(np.cumsum(0.004 + rng.normal(0, 0.002, 260)))
                           for i in range(18)}, index=idx)
    wide, emem = expand_multi(closes, mem)
    assert wide.shape[1] == 24 and emem.groupby("group").size().to_dict() == {"b1": 12, "b2": 12}
    cp = tmp_path / "closes.parquet"
    closes.to_parquet(cp)
    meta = build(cp, mp, tmp_path / "out")
    d = pd.read_parquet(tmp_path / "out" / "basket_breadth_daily_current.parquet")
    last = d[d["date"] == d["date"].max()].set_index("group")
    assert last.loc["b1", "n_members"] == 12 and last.loc["b2", "n_members"] == 12
    assert last.loc["b1", "pct_above_200"] == 100.0
    assert meta["coverage"]["names_in_several_baskets"] == 6


# ── (h) member_rows ──────────────────────────────────────────────────────────

def test_member_rows_schema_flags_and_source_asof():
    idx = pd.bdate_range("2025-01-02", periods=205)
    closes = pd.DataFrame({
        "M1": np.full(205, 100.0),                                    # flat
        "M2": 100.0 + 0.5 * np.arange(205),                           # rising
        "M3": np.where(np.arange(205) <= 184, 100.0 + 0.25 * np.arange(205),
                       np.nan),                                       # stops at row 184
        "X": np.full(205, 7.0),                                       # NOT a member
    }, index=idx)
    membership = pd.DataFrame({"ticker": ["M1", "M2", "M3"], "group": "G"})

    m = gbh.member_rows(closes, membership)
    assert list(m.columns) == ["date", "ticker", "group",
                               "has_200_sessions", "above_200", "source_asof"]
    assert set(m["ticker"]) == {"M1", "M2", "M3"}, "non-members must be excluded"
    assert (m["date"] == idx[-1].date().isoformat()).all()
    assert (m["group"] == "G").all()

    by = m.set_index("ticker")
    assert bool(by.loc["M1", "has_200_sessions"]) is True
    assert bool(by.loc["M1", "above_200"]) is False      # close == average, not above
    assert bool(by.loc["M2", "has_200_sessions"]) is True
    assert bool(by.loc["M2", "above_200"]) is True
    assert bool(by.loc["M3", "has_200_sessions"]) is False  # no defined MA at t
    assert bool(by.loc["M3", "above_200"]) is False
    # source_asof = the ticker's own last valid close on/before date
    assert by.loc["M1", "source_asof"] == idx[-1].date().isoformat()
    assert by.loc["M3", "source_asof"] == idx[184].date().isoformat()

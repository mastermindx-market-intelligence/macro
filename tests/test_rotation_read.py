"""Fixture-only tests for the SI rotation read (scripts/build_rotation_read).

Synthetic made-up numbers only — no real data/ reads, every write under
tmp_path. Pins the frozen contract: exact key/field order, the completed-
weekly-close vintage rule (calendar only), the two-close stale rule, the
unavailable-reason ladder, family-scoped ranks, the active-roster companies
map, and the freshness gate's vintage-split error.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import build_rotation_read as brr

NOW_OK = datetime(2026, 10, 13, 22, 0, tzinfo=timezone.utc)
NOW_STALE = datetime(2026, 11, 13, 22, 0, tzinfo=timezone.utc)

# v1 keys, then the three additive input fields (ruling 108), in this exact order.
TOP_KEYS = ["schema", "as_of", "built_at", "status", "basis", "copy", "groups", "companies",
            "input", "input_start", "field_notes"]
ROW_FIELDS = [
    "group_id", "family", "name", "parent", "as_of", "status",
    "unavailable_reason", "n_members", "n_counted", "pct_above_200",
    "chg_13w", "chg_26w", "direction", "run_weeks", "rank_13w", "n_ranked",
]
MEASURES = ["pct_above_200", "chg_13w", "chg_26w", "direction", "run_weeks",
            "rank_13w", "n_ranked"]

# group -> (pct_above_200, chg_13w, chg_26w, state, run_weeks, n_has_200)
VALUES = {
    "us_sector_a": (60.0, 5.0, 8.0, "improving", 3, 12),
    "us_sector_b": (40.0, 1.0, 2.0, "improving", 1, 11),
    "us_theme_x": (70.0, 9.0, 13.0, "improving", 4, 14),
    "us_theme_y": (55.0, 7.0, -1.0, "deteriorating", 2, 13),
}


def _membership() -> dict:
    return {"baskets": {
        "us_sector_a": {"name": "Sector A", "parent": None, "members": [
            {"ticker": "AAA", "removed": None},
            {"ticker": "BBB", "removed": None},
            {"ticker": "ZZZ", "removed": "2026-09-01"},
        ]},
        "us_sector_b": {"name": "Sector B", "parent": None, "members": [
            {"ticker": "CCC", "removed": None},
        ]},
        "us_theme_x": {"name": "Theme X", "parent": "us_sector_a", "members": [
            {"ticker": "AAA", "removed": None},
            {"ticker": "DDD", "removed": None},
        ]},
        "us_theme_y": {"name": "Theme Y", "parent": None, "members": [
            {"ticker": "CCC", "removed": None},
            {"ticker": "EEE", "removed": None},
        ]},
    }}


def _hist() -> pd.DataFrame:
    """~30 weekly Friday dates in 2026 ending 2026-10-09, four groups."""
    dates = pd.date_range(end="2026-10-09", periods=30, freq="W-FRI")
    rows = []
    for d in dates:
        for gid, (pct, c13, c26, state, run, n_has) in VALUES.items():
            rows.append({
                "date": d, "group": gid,
                "n_members": n_has, "n_has_200": n_has,
                "pct_above_200": pct,
                "fix_chg_pct_above_200_13w": c13,
                "state_fix_chg_pct_above_200_13w": state,
                "run_fix_chg_pct_above_200_13w": float(run),
                "n_fixed_200_13w": n_has,
                "fix_chg_pct_above_200_26w": c26,
                "n_fixed_200_26w": n_has,
            })
    return pd.DataFrame(rows)


def _write_inputs(root: Path, hist: pd.DataFrame | None, membership: dict | None) -> None:
    if hist is not None:
        hist_path = root / "data/breadth/history/basket_breadth_weekly_current.parquet"
        hist_path.parent.mkdir(parents=True, exist_ok=True)
        hist.to_parquet(hist_path)
    if membership is not None:
        mem_path = root / "data/baskets/membership.json"
        mem_path.parent.mkdir(parents=True, exist_ok=True)
        mem_path.write_text(json.dumps(membership), encoding="utf-8")


def _rows_by_id(payload: dict) -> dict:
    return {g["group_id"]: g for g in payload["groups"]}


# 1 — exact shape -------------------------------------------------------------

def test_exact_top_level_and_row_shape():
    payload = brr.build(_hist(), _membership(), NOW_OK)
    assert payload is not None
    assert list(payload.keys()) == TOP_KEYS
    assert payload["schema"] == "si.rotation_read/v1"
    assert payload["copy"] == brr.COPY
    assert payload["basis"] == "current_roster"
    assert payload["built_at"].endswith("Z")
    assert payload["groups"], "fixture must produce rows"
    for row in payload["groups"]:
        assert list(row.keys()) == ROW_FIELDS


# 2 — as_of is a strict ISO date on both the ok and the stale panel -----------

@pytest.mark.parametrize("now", [NOW_OK, NOW_STALE])
def test_as_of_strict_iso_ok_and_stale(now):
    payload = brr.build(_hist(), _membership(), now)
    assert payload["as_of"] == "2026-10-09"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", payload["as_of"])
    for row in payload["groups"]:
        assert row["as_of"] == "2026-10-09"


# 3 — stale panel --------------------------------------------------------------

def test_stale_panel_every_row_unavailable():
    payload = brr.build(_hist(), _membership(), NOW_STALE)
    assert payload["status"] == "stale"
    for row in payload["groups"]:
        assert row["status"] == "unavailable"
        assert row["unavailable_reason"] == "stale"
        assert row["n_counted"] is None
        for field in MEASURES:
            assert row[field] is None
        assert isinstance(row["n_members"], int)


# 4 — too few members ----------------------------------------------------------

def test_too_few_members_row():
    hist = _hist()
    last = hist["date"].max()
    mask = (hist["group"] == "us_sector_b") & (hist["date"] == last)
    hist.loc[mask, "pct_above_200"] = np.nan
    payload = brr.build(hist, _membership(), NOW_OK)
    rows = _rows_by_id(payload)
    row = rows["us_sector_b"]
    assert row["status"] == "unavailable"
    assert row["unavailable_reason"] == "too_few_members"
    for field in MEASURES:
        assert row[field] is None
    assert isinstance(row["n_counted"], int)
    assert row["n_counted"] == 11
    # the other sector stays ok and is ranked alone inside its family
    assert rows["us_sector_a"]["status"] == "ok"
    assert rows["us_sector_a"]["rank_13w"] == 1
    assert rows["us_sector_a"]["n_ranked"] == 1


# 5 — basket absent from the history -------------------------------------------

def test_no_history_row():
    hist = _hist()
    hist = hist[hist["group"] != "us_theme_y"]
    payload = brr.build(hist, _membership(), NOW_OK)
    row = _rows_by_id(payload)["us_theme_y"]
    assert row["status"] == "unavailable"
    assert row["unavailable_reason"] == "no_history"
    assert row["n_counted"] is None
    for field in MEASURES:
        assert row[field] is None
    assert row["n_members"] == 2


# 6 — ranks are family-scoped ---------------------------------------------------

def test_rank_inside_family_only():
    payload = brr.build(_hist(), _membership(), NOW_OK)
    assert [g["group_id"] for g in payload["groups"]] == [
        "us_sector_a", "us_sector_b", "us_theme_x", "us_theme_y",
    ]
    rows = _rows_by_id(payload)
    # theme changes (9, 7) are larger than sector changes (5, 1): a global
    # rank would put the sectors at 3/4 — family ranks must stay 1/2.
    assert rows["us_sector_a"]["rank_13w"] == 1
    assert rows["us_sector_b"]["rank_13w"] == 2
    assert rows["us_theme_x"]["rank_13w"] == 1
    assert rows["us_theme_y"]["rank_13w"] == 2
    for gid in VALUES:
        assert rows[gid]["n_ranked"] == 2


# 7 — companies map is the active roster ----------------------------------------

def test_companies_equal_active_roster():
    payload = brr.build(_hist(), _membership(), NOW_OK)
    assert payload["companies"] == {
        "AAA": {"sector": "us_sector_a", "themes": ["us_theme_x"]},
        "BBB": {"sector": "us_sector_a", "themes": []},
        "CCC": {"sector": "us_sector_b", "themes": ["us_theme_y"]},
        "DDD": {"sector": None, "themes": ["us_theme_x"]},
        "EEE": {"sector": None, "themes": ["us_theme_y"]},
    }
    assert list(payload["companies"]) == sorted(payload["companies"])
    assert "ZZZ" not in payload["companies"]  # removed member excluded


# 8 — no vendor / internal_only strings ------------------------------------------

def test_no_vendor_or_internal_only_strings():
    payload = brr.build(_hist(), _membership(), NOW_OK)
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "vendor" not in serialized
    assert "internal_only" not in serialized


# 9 — missing inputs: no file, rc 0 ----------------------------------------------

def test_main_missing_history_writes_nothing(tmp_path):
    _write_inputs(tmp_path, None, _membership())
    out = tmp_path / "site/sectordata/rotation_read.json"
    assert brr.main(["--root", str(tmp_path)]) == 0
    assert not out.exists()


def test_main_missing_membership_writes_nothing(tmp_path):
    _write_inputs(tmp_path, _hist(), None)
    out = tmp_path / "site/sectordata/rotation_read.json"
    assert brr.main(["--root", str(tmp_path)]) == 0
    assert not out.exists()


def test_main_empty_history_writes_nothing(tmp_path):
    _write_inputs(tmp_path, _hist().iloc[0:0], _membership())
    out = tmp_path / "site/sectordata/rotation_read.json"
    assert brr.main(["--root", str(tmp_path)]) == 0
    assert not out.exists()


# 10 — a trailing partial week is not a completed close ---------------------------

def test_partial_last_week_uses_prior_friday():
    hist = _hist()
    extra = hist[hist["date"] == hist["date"].max()].copy()
    extra["date"] = pd.Timestamp("2026-10-14")  # Wednesday; Thu/Fri sessions follow
    hist = pd.concat([hist, extra], ignore_index=True)
    payload = brr.build(hist, _membership(), NOW_OK)
    assert payload["as_of"] == "2026-10-09"
    assert payload["status"] == "ok"


# 11 — completed-close counting -----------------------------------------------------

def test_completed_weekly_closes_between():
    from datetime import date
    assert brr.completed_weekly_closes_between(date(2026, 10, 9), date(2026, 10, 16)) == 1
    assert brr.completed_weekly_closes_between(date(2026, 10, 9), date(2026, 10, 23)) == 2
    assert brr.completed_weekly_closes_between(date(2026, 10, 9), date(2026, 10, 14)) == 0


# 12 — freshness gate ---------------------------------------------------------------

def test_check_rotation_read(tmp_path):
    from scripts import check_sector_intelligence_freshness as freshness

    root = tmp_path / "root"
    _write_inputs(root, _hist(), _membership())
    out = root / "site/sectordata/rotation_read.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = brr.build(_hist(), _membership(), NOW_OK)

    # coherent file
    out.write_text(json.dumps(payload), encoding="utf-8")
    assert freshness.check_rotation_read(root) == []

    # vintage split
    split = dict(payload, as_of="2026-10-02")
    out.write_text(json.dumps(split), encoding="utf-8")
    errors = freshness.check_rotation_read(root)
    assert len(errors) == 1
    assert "VINTAGE SPLIT" in errors[0]

    # wrong schema is named
    out.write_text(json.dumps(dict(payload, schema="si.other/v9")), encoding="utf-8")
    errors = freshness.check_rotation_read(root)
    assert len(errors) == 1
    assert "rotation_read.json" in errors[0]

    # missing json although the history exists
    out.unlink()
    errors = freshness.check_rotation_read(root)
    assert len(errors) == 1
    assert "missing" in errors[0]

    # no history at all -> nothing to check
    empty_root = tmp_path / "empty"
    empty_root.mkdir()
    assert freshness.check_rotation_read(empty_root) == []


# 13 — pipeline step order -----------------------------------------------------------

def test_default_steps_order():
    from scripts import build_sector_intelligence as bsi

    names = [name for name, _ in bsi.default_steps()]
    assert names[-2:] == [
        "scripts.build_rotation_read",
        "scripts.check_sector_intelligence_freshness",
    ]
    assert names[0] == "scripts.build_baskets"
    assert names[2] == "scripts.build_sector_central"


# 14 — main() writes and round-trips ----------------------------------------------------

def test_main_writes_and_round_trips(tmp_path):
    root = tmp_path / "root"
    _write_inputs(root, _hist(), _membership())
    out = tmp_path / "elsewhere" / "rotation_read.json"
    assert brr.main(["--root", str(root), "--out", str(out)]) == 0
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert list(payload.keys()) == TOP_KEYS
    assert payload["schema"] == "si.rotation_read/v1"
    assert payload["as_of"] == "2026-10-09"
    assert payload["basis"] == "current_roster"
    assert payload["copy"] == brr.COPY
    assert payload["built_at"].endswith("Z")
    assert payload["status"] in {"ok", "stale", "unavailable"}
    assert [g["group_id"] for g in payload["groups"]] == [
        "us_sector_a", "us_sector_b", "us_theme_x", "us_theme_y",
    ]
    assert payload["companies"] == brr.build(_hist(), _membership(), NOW_OK)["companies"]
    assert not out.with_name(out.name + ".tmp").exists()

# 15 — stale boundary through build(): one close behind is ok, two is stale ------------

@pytest.mark.parametrize("now, status", [
    (datetime(2026, 10, 19, 22, 0, tzinfo=timezone.utc), "ok"),     # 10-16 completed
    (datetime(2026, 10, 26, 22, 0, tzinfo=timezone.utc), "stale"),  # 10-16, 10-23
])
def test_stale_boundary_through_build(now, status):
    payload = brr.build(_hist(), _membership(), now)
    assert payload["as_of"] == "2026-10-09"
    assert payload["status"] == status


# 16 — a holiday week closes on its last session, not on Friday ---------------------------

def test_holiday_week_closes_on_last_session():
    # Good Friday 2026-04-03: the NYSE is closed, so Thursday 2026-04-02 is the
    # week's completed close.
    hist = _hist()
    hist = hist[hist["date"] <= pd.Timestamp("2026-03-27")].copy()
    extra = hist[hist["date"] == hist["date"].max()].copy()
    extra["date"] = pd.Timestamp("2026-04-02")
    hist = pd.concat([hist, extra], ignore_index=True)
    payload = brr.build(hist, _membership(), datetime(2026, 4, 7, 22, 0, tzinfo=timezone.utc))
    assert payload["as_of"] == "2026-04-02"
    assert payload["status"] == "ok"


# 17 — input hygiene: string dates read the same; a missing column writes nothing ----------

def test_string_dates_read_as_dates():
    hist = _hist()
    hist["date"] = hist["date"].dt.strftime("%Y-%m-%d")
    payload = brr.build(hist, _membership(), NOW_OK)
    assert payload["as_of"] == "2026-10-09"
    assert all(g["status"] == "ok" for g in payload["groups"])


def test_missing_engine_column_projects_nothing():
    hist = _hist().drop(columns=["fix_chg_pct_above_200_13w"])
    assert brr.build(hist, _membership(), NOW_OK) is None


# 18 — a failed write leaves no partial file and does not raise ------------------------------

def test_failed_write_leaves_no_partial_file(tmp_path):
    root = tmp_path / "root"
    _write_inputs(root, _hist(), _membership())
    out = tmp_path / "blocked"
    out.mkdir()  # a directory in the way: os.replace cannot put the file there
    assert brr.main(["--root", str(root), "--out", str(out)]) == 0
    assert out.is_dir()
    assert not out.with_name(out.name + ".tmp").exists()


# 19 — freshness gate: a file written with no completed close in its history is named --------

def test_check_rotation_read_no_completed_close(tmp_path):
    from scripts import check_sector_intelligence_freshness as freshness

    hist = _hist()
    hist = hist[hist["date"] == hist["date"].max()].copy()
    hist["date"] = pd.Timestamp("2026-10-14")  # Wednesday only: no completed close
    root = tmp_path / "root"
    _write_inputs(root, hist, _membership())
    assert brr.build(hist, _membership(), NOW_OK) is None
    assert freshness.check_rotation_read(root) == []
    out = root / "site/sectordata/rotation_read.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"schema": "si.rotation_read/v1"}), encoding="utf-8")
    errors = freshness.check_rotation_read(root)
    assert len(errors) == 1
    assert "no completed weekly close" in errors[0]


# 20 — one-file input rule (ruling 108) ------------------------------------------------------

NIGHTLY = "data/breadth/history/basket_breadth_weekly_current_live.parquet"


def _write_nightly(root: Path, hist: pd.DataFrame) -> None:
    p = root / NIGHTLY
    p.parent.mkdir(parents=True, exist_ok=True)
    hist.to_parquet(p)


def _later(hist: pd.DataFrame, weeks: int) -> pd.DataFrame:
    out = hist.copy()
    out["date"] = out["date"] + pd.Timedelta(weeks=weeks)
    return out


def test_nightly_used_only_when_later_than_archive(tmp_path):
    from scripts import check_sector_intelligence_freshness as freshness

    root = tmp_path / "r"
    _write_inputs(root, _hist(), _membership())
    assert freshness.select_rotation_input(root)[0] == "archive"
    _write_nightly(root, _hist())  # same last close: not later -> archive
    assert freshness.select_rotation_input(root)[0] == "archive"
    _write_nightly(root, _later(_hist(), 1))  # one completed week later -> nightly
    name, frame = freshness.select_rotation_input(root)
    assert name == "nightly"
    assert frame["date"].max() == pd.Timestamp("2026-10-16")


def test_bad_nightly_falls_back_to_archive(tmp_path):
    from scripts import check_sector_intelligence_freshness as freshness

    root = tmp_path / "r"
    _write_inputs(root, _hist(), _membership())
    p = root / NIGHTLY
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"not a parquet file")  # unreadable
    assert freshness.select_rotation_input(root)[0] == "archive"
    _write_nightly(root, _later(_hist(), 1).drop(columns=["fix_chg_pct_above_200_13w"]))
    assert freshness.select_rotation_input(root)[0] == "archive"  # fails its column check


def test_one_file_never_spliced(tmp_path):
    """The nightly frame alone is read: no archive week appears in the payload's input."""
    root = tmp_path / "r"
    _write_inputs(root, _hist(), _membership())
    short = _later(_hist(), 1)
    short = short[short["date"] >= pd.Timestamp("2026-08-01")]
    _write_nightly(root, short)
    out = tmp_path / "o.json"
    assert brr.main(["--root", str(root), "--out", str(out)]) == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["input"] == "nightly"
    assert payload["input_start"] == short["date"].min().date().isoformat()
    assert payload["as_of"] == "2026-10-16"


def test_run_reaching_input_start_is_withheld():
    """A run as long as the input's defined history may have begun earlier: withheld, with a reason."""
    hist = _hist()
    n_weeks = hist["date"].nunique()
    hist.loc[hist["group"] == "us_theme_x", "run_fix_chg_pct_above_200_13w"] = float(n_weeks)
    payload = brr.build(hist, _membership(), NOW_OK, input_name="nightly")
    rows = _rows_by_id(payload)
    assert rows["us_theme_x"]["run_weeks"] is None
    assert rows["us_theme_x"]["status"] == "ok"  # the other measures still print
    assert payload["field_notes"] == [{
        "group_id": "us_theme_x", "field": "run_weeks", "reason": brr.RUN_CENSORED_REASON}]
    assert rows["us_sector_a"]["run_weeks"] == 3  # a shorter run is reported as is


@pytest.mark.parametrize("offset, withheld", [(0, True), (1, False)])
def test_run_boundary_at_input_start(offset, withheld):
    """run == number of weeks reaches the first row (withheld); one less starts after a defined week."""
    hist = _hist()
    n_weeks = hist["date"].nunique()
    hist.loc[hist["group"] == "us_theme_x", "run_fix_chg_pct_above_200_13w"] = float(n_weeks - offset)
    rows = _rows_by_id(brr.build(hist, _membership(), NOW_OK, input_name="nightly"))
    assert rows["us_theme_x"]["run_weeks"] == (None if withheld else n_weeks - offset)


def test_run_after_undefined_gap_is_withheld():
    """A run that restarts right after weeks with no defined change has an unknown start."""
    hist = _hist()
    dates = sorted(hist["date"].unique())
    x = hist["group"] == "us_theme_x"
    gap = x & hist["date"].isin(dates[10:14])          # four undefined weeks mid-history
    hist.loc[gap, "fix_chg_pct_above_200_13w"] = np.nan
    run_after_gap = len(dates) - 14                     # the run fills every week after the gap
    hist.loc[x, "run_fix_chg_pct_above_200_13w"] = float(run_after_gap)
    rows = _rows_by_id(brr.build(hist, _membership(), NOW_OK, input_name="archive"))
    assert rows["us_theme_x"]["run_weeks"] is None
    hist.loc[x, "run_fix_chg_pct_above_200_13w"] = float(run_after_gap - 1)  # starts after a defined week
    rows = _rows_by_id(brr.build(hist, _membership(), NOW_OK, input_name="archive"))
    assert rows["us_theme_x"]["run_weeks"] == run_after_gap - 1


def test_check_names_unreadable_nightly_when_archive_absent(tmp_path):
    from scripts import check_sector_intelligence_freshness as freshness

    root = tmp_path / "r"
    p = root / NIGHTLY
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"not a parquet file")
    errors = freshness.check_rotation_read(root)
    assert len(errors) == 1 and Path(NIGHTLY).name in errors[0]


def test_input_name_is_neutral_and_checked():
    payload = brr.build(_hist(), _membership(), NOW_OK)
    assert payload["input"] == "archive"
    with pytest.raises(ValueError):
        brr.build(_hist(), _membership(), NOW_OK, input_name="vendor_x")


def test_check_names_an_input_split(tmp_path):
    from scripts import check_sector_intelligence_freshness as freshness

    root = tmp_path / "r"
    _write_inputs(root, _hist(), _membership())
    _write_nightly(root, _later(_hist(), 1))
    out = root / "site/sectordata/rotation_read.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    good = brr.build(_later(_hist(), 1), _membership(), NOW_OK, input_name="nightly")
    out.write_text(json.dumps(good), encoding="utf-8")
    assert freshness.check_rotation_read(root) == []
    out.write_text(json.dumps(dict(good, input="archive")), encoding="utf-8")
    errors = freshness.check_rotation_read(root)
    assert len(errors) == 1 and "INPUT SPLIT" in errors[0]

"""L1-FO1 (COO ruling 26): the Brief breadth-change frame + the member's own
above_200 flag, carried from #11094's already-computed weekly fixed-set history.

FIXTURE Every input here is a SYNTHETIC parquet/JSON fixture mirroring the exact
        schema of ``engine.group_breadth_history.weekly_fixed_set`` / ``member_rows``
        and ``scripts.build_group_breadth_history``'s meta sidecar. The real breadth
        history lives off-git in ``data/breadth/`` (``config/sparse_worktree.json``
        excludes ``data/``), so no real-data measurement is possible in this tree;
        the encoded-size test reports bytes on a representative synthetic frame and
        pins the 4 MiB bound. The carry under test is NEW code; it recomputes no
        signal — it copies the producer's MIN_MEMBERS=10 floors verbatim.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from engine.sector_native_view import (
    _TYPED_ROW_BLOCK_MAX_BYTES, _typed_blocks, _typed_row_block,
)
from lib import sector_central_carry as carry
from lib.sector_generation_wire import (
    MAX_ENCODED_BYTES, SectorGenerationTooLarge, encode_sector_generation,
)

BASIS = "reconstructed_current_membership"
LATEST = "2026-11-06"
EARLIER = "2026-10-30"

#: One weekly row per group at the latest session, exercising BOTH producer floors:
#:  - "Software" is fully measured (>=10 counted today, n_fixed_200_13w >= 10);
#:  - "Tiny Industry" has <10 counted today -> pct_above_200 null (level floor);
#:  - "Young Industry" has >=10 counted today but n_fixed_200_13w < 10 -> the
#:    change/rank/state/run are null (fixed-set floor) while the level stays.
_WEEKLY_ROWS = [
    {"group": "Software", "n_members": 70, "n_has_200": 68, "pct_above_200": 61.8,
     "fix_chg_pct_above_200_13w": 4.4, "rank_fix_chg_pct_above_200_13w": 2.0,
     "n_ranked_fix_chg_pct_above_200_13w": 11.0, "state_fix_chg_pct_above_200_13w": "improving",
     "run_fix_chg_pct_above_200_13w": 3.0, "n_fixed_200_13w": 65,
     "lvl_diff_pct_above_200_13w": 5.1},
    {"group": "Tiny Industry", "n_members": 8, "n_has_200": 8, "pct_above_200": float("nan"),
     "fix_chg_pct_above_200_13w": float("nan"), "rank_fix_chg_pct_above_200_13w": float("nan"),
     "n_ranked_fix_chg_pct_above_200_13w": float("nan"),
     "state_fix_chg_pct_above_200_13w": None, "run_fix_chg_pct_above_200_13w": float("nan"),
     "n_fixed_200_13w": 8, "lvl_diff_pct_above_200_13w": float("nan")},
    {"group": "Young Industry", "n_members": 30, "n_has_200": 28, "pct_above_200": 50.0,
     "fix_chg_pct_above_200_13w": float("nan"), "rank_fix_chg_pct_above_200_13w": float("nan"),
     "n_ranked_fix_chg_pct_above_200_13w": float("nan"),
     "state_fix_chg_pct_above_200_13w": None, "run_fix_chg_pct_above_200_13w": float("nan"),
     "n_fixed_200_13w": 6, "lvl_diff_pct_above_200_13w": float("nan")},
]


def _weekly_frame() -> pd.DataFrame:
    rows = []
    for day in (EARLIER, LATEST):
        for row in _WEEKLY_ROWS:
            rows.append({"date": pd.Timestamp(day), **row})
    return pd.DataFrame(rows)


def _ledger_frame() -> pd.DataFrame:
    rows = []
    for day in (EARLIER, LATEST):
        rows.append({"date": pd.Timestamp(day), "ticker": "AAPL", "group": "Software",
                     "has_200_sessions": True, "above_200": True, "source_asof": day})
        rows.append({"date": pd.Timestamp(day), "ticker": "MSFT", "group": "Software",
                     "has_200_sessions": True, "above_200": False, "source_asof": day})
        rows.append({"date": pd.Timestamp(day), "ticker": "NEW", "group": "Young Industry",
                     "has_200_sessions": False, "above_200": False, "source_asof": None})
    return pd.DataFrame(rows)


def _meta(basis: str = BASIS) -> dict:
    return {"basis": basis, "span": {"first_valid_pct_above_200": "2010-01-08"},
            "rules": {"min_members": 10, "headline": "fix_chg_pct_above_200_13w"}}


@pytest.fixture()
def breadth_dir(tmp_path: Path) -> Path:
    """A synthetic data/breadth directory: history weekly frame + meta + ledger."""
    root = tmp_path / "breadth"
    (root / "history").mkdir(parents=True)
    _weekly_frame().to_parquet(root / "history" / "group_breadth_weekly_current.parquet",
                               index=False)
    (root / "history" / "group_breadth_current.meta.json").write_text(
        json.dumps(_meta()), encoding="utf-8")
    _ledger_frame().to_parquet(root / "member_breadth_ledger.parquet", index=False)
    return root


def _sector(block: dict, group: str) -> dict:
    return next(s for s in block["sectors"] if s["group"] == group)


# ---------------------------------------------------------------------------
# The carry: available path, verbatim floors, basis, dating, member flag
# ---------------------------------------------------------------------------

def test_carries_the_current_weekly_frame_with_basis_and_first_valid_date(breadth_dir):
    block = carry.sector_breadth(breadth_dir)
    assert block is not None
    assert block["as_of"] == LATEST  # the latest weekly session, not the earlier one
    assert block["basis"] == BASIS
    assert block["first_valid_date"] == "2010-01-08"
    assert block["min_members"] == 10
    assert block["headline"] == "fix_chg_pct_above_200_13w"
    assert block["window_sessions"] == 200 and block["horizon_weeks"] == 13
    assert [s["group"] for s in block["sectors"]] == ["Software", "Tiny Industry", "Young Industry"]
    soft = _sector(block, "Software")
    assert soft["pct_above_200"] == 61.8
    assert soft["fix_chg_pct_above_200_13w"] == 4.4
    assert soft["rank_fix_chg_pct_above_200_13w"] == 2  # rank carried as an integer
    assert soft["n_ranked_fix_chg_pct_above_200_13w"] == 11
    assert soft["state_fix_chg_pct_above_200_13w"] == "improving"
    assert soft["run_fix_chg_pct_above_200_13w"] == 3
    assert soft["n_fixed_200_13w"] == 65
    assert soft["lvl_diff_pct_above_200_13w"] == 5.1


def test_level_floor_pct_above_200_null_only_when_under_ten_counted_today(breadth_dir):
    """The producer's level floor is copied verbatim: <10 counted today -> null."""
    block = carry.sector_breadth(breadth_dir)
    tiny = _sector(block, "Tiny Industry")
    assert tiny["n_members"] == 8 and tiny["n_has_200"] == 8
    assert tiny["pct_above_200"] is None  # floored by the producer, never re-derived
    # a fully-measured industry keeps its level
    assert _sector(block, "Software")["pct_above_200"] == 61.8


def test_fixed_set_floor_change_and_rank_null_when_n_fixed_under_ten(breadth_dir):
    """The producer's fixed-set floor: n_fixed_200_13w < 10 -> change/rank/state/run
    null, while the level (counted today >= 10) stays."""
    block = carry.sector_breadth(breadth_dir)
    young = _sector(block, "Young Industry")
    assert young["n_fixed_200_13w"] == 6
    assert young["pct_above_200"] == 50.0  # level stays: >=10 counted today
    assert young["fix_chg_pct_above_200_13w"] is None
    assert young["rank_fix_chg_pct_above_200_13w"] is None
    assert young["state_fix_chg_pct_above_200_13w"] is None
    assert young["run_fix_chg_pct_above_200_13w"] is None
    # the tiny industry is under BOTH floors
    tiny = _sector(block, "Tiny Industry")
    assert tiny["fix_chg_pct_above_200_13w"] is None
    assert tiny["rank_fix_chg_pct_above_200_13w"] is None


def test_carries_each_members_own_above_200_flag_from_the_latest_ledger_session(breadth_dir):
    block = carry.sector_breadth(breadth_dir)
    members = {m["ticker"]: m for m in block["members"]}
    assert set(members) == {"AAPL", "MSFT", "NEW"}  # latest session only, deduped by day
    assert members["AAPL"]["above_200"] is True
    assert members["AAPL"]["has_200_sessions"] is True
    assert members["MSFT"]["above_200"] is False
    assert members["NEW"]["has_200_sessions"] is False
    assert members["NEW"]["above_200"] is False
    assert members["NEW"]["source_asof"] is None
    assert all(m["group"] for m in members.values())


def test_no_members_key_when_the_ledger_is_absent(tmp_path):
    root = tmp_path / "breadth"
    (root / "history").mkdir(parents=True)
    _weekly_frame().to_parquet(root / "history" / "group_breadth_weekly_current.parquet",
                               index=False)
    (root / "history" / "group_breadth_current.meta.json").write_text(json.dumps(_meta()))
    block = carry.sector_breadth(root)
    assert block is not None and "members" not in block
    assert block["sectors"]  # the frame is still carried without the flag


# ---------------------------------------------------------------------------
# Fail-soft: absent / unreadable / wrong-basis sources carry nothing
# ---------------------------------------------------------------------------

def test_absent_directory_carries_nothing(tmp_path):
    assert carry.sector_breadth(None) is None
    assert carry.sector_breadth(tmp_path / "missing") is None


def test_absent_meta_or_weekly_carries_nothing(tmp_path):
    root = tmp_path / "breadth"
    (root / "history").mkdir(parents=True)
    assert carry.sector_breadth(root) is None  # no meta, no frame
    (root / "history" / "group_breadth_current.meta.json").write_text(json.dumps(_meta()))
    assert carry.sector_breadth(root) is None  # meta but no frame


def test_dated_basis_is_not_carried(tmp_path):
    """Only the reconstructed-current-membership frame is carried; a dated basis is
    a different measurement and is never copied under the current label."""
    root = tmp_path / "breadth"
    (root / "history").mkdir(parents=True)
    _weekly_frame().to_parquet(root / "history" / "group_breadth_weekly_current.parquet",
                               index=False)
    (root / "history" / "group_breadth_current.meta.json").write_text(
        json.dumps(_meta(basis="dated")))
    assert carry.sector_breadth(root) is None


def test_non_finite_source_value_is_refused_not_serialized(tmp_path):
    """A frame whose only group row is non-finite JSON drops the block (never ships
    a NaN): the carry's finite-JSON encoder refuses it."""
    root = tmp_path / "breadth"
    (root / "history").mkdir(parents=True)
    bad = pd.DataFrame([{"date": pd.Timestamp(LATEST), "group": "Software",
                         "n_members": 70, "pct_above_200": float("inf")}])
    bad.to_parquet(root / "history" / "group_breadth_weekly_current.parquet", index=False)
    (root / "history" / "group_breadth_current.meta.json").write_text(json.dumps(_meta()))
    # inf is not finite JSON: the whole block is refused (absent), never serialized
    assert carry.sector_breadth(root) is None


# ---------------------------------------------------------------------------
# build_carry registration: the block is dated and appears under its closed key
# ---------------------------------------------------------------------------

def test_build_carry_registers_sector_breadth_when_present(tmp_path, breadth_dir):
    site = tmp_path / "site"
    site.mkdir()
    built = carry.build_carry(site, {}, breadth_dir=breadth_dir)
    assert "sector_breadth" in built
    assert built["sector_breadth"]["as_of"] == LATEST
    # without a breadth dir the key is absent (not_produced), never guessed
    assert "sector_breadth" not in carry.build_carry(site, {})


# ---------------------------------------------------------------------------
# Projection admission: the typed row block reader and the audience gate
# ---------------------------------------------------------------------------

def test_typed_row_block_admits_a_well_formed_breadth_frame(breadth_dir):
    block = carry.sector_breadth(breadth_dir)
    admitted = _typed_row_block(block, name="sector_breadth")
    assert admitted["status"] == "available" and admitted["reason"] is None
    assert admitted["value"] == block


@pytest.mark.parametrize("mutate", [
    lambda b: b.pop("sectors"),
    lambda b: b.update(sectors={"group": "x"}),  # not a list
    lambda b: b.pop("basis"),
    lambda b: b.update(basis=""),
    lambda b: b.update(as_of=None),
    lambda b: b.update(members={"ticker": "AAPL"}),  # members must be a list
])
def test_typed_row_block_refuses_a_malformed_breadth_frame(breadth_dir, mutate):
    block = carry.sector_breadth(breadth_dir)
    mutate(block)
    assert _typed_row_block(block, name="sector_breadth") == {
        "status": "unavailable", "reason": "invalid_shape", "value": None}


def test_typed_row_block_breadth_stub_reads_by_its_reason(breadth_dir):
    stub = {"source": "x", "as_of": LATEST, "basis": BASIS,
            "status": "unavailable", "reason": "block_too_large"}
    assert _typed_row_block(stub, name="sector_breadth") == {
        "status": "unavailable", "reason": "block_too_large", "value": None}
    other = {**stub, "reason": "producer_refused"}
    assert _typed_row_block(other, name="sector_breadth") == {
        "status": "unavailable", "reason": "invalid_shape", "value": None}


class _Inputs:
    """Minimal SectorViewInputs stand-in: only ``central`` is read by _typed_blocks."""
    def __init__(self, central):
        self.central = central


def test_typed_blocks_audience_gate_and_not_produced(breadth_dir):
    block = carry.sector_breadth(breadth_dir)
    entitled = _typed_blocks(_Inputs({"carried": {"sector_breadth": block}}), "entitled")
    assert entitled["sector_breadth"]["status"] == "available"
    preview = _typed_blocks(_Inputs({"carried": {"sector_breadth": block}}), "preview")
    assert preview["sector_breadth"] == {"status": "unavailable",
                                         "reason": "audience_not_entitled", "value": None}
    absent = _typed_blocks(_Inputs({"carried": {}}), "entitled")
    assert absent["sector_breadth"] == {"status": "unavailable",
                                        "reason": "not_produced", "value": None}


# ---------------------------------------------------------------------------
# Encoded size: pin the 4 MiB bound and report bytes (representative synthetic frame)
# ---------------------------------------------------------------------------

def _representative_block(n_sectors: int = 11, n_members: int = 500) -> dict:
    """A representative current frame: 11 GICS sectors + ~500 member flags, the
    shape the nightly carry produces for the S&P 500 current-basis universe."""
    sectors = []
    for i in range(n_sectors):
        sectors.append({
            "group": f"Sector {i}", "n_members": 45, "n_has_200": 44,
            "pct_above_200": 55.0 + i, "fix_chg_pct_above_200_13w": 1.0 + i,
            "rank_fix_chg_pct_above_200_13w": i + 1,
            "n_ranked_fix_chg_pct_above_200_13w": n_sectors,
            "state_fix_chg_pct_above_200_13w": "improving",
            "run_fix_chg_pct_above_200_13w": 2, "n_fixed_200_13w": 40,
            "lvl_diff_pct_above_200_13w": 1.5,
        })
    members = [{"ticker": f"T{i:04d}", "group": f"Sector {i % n_sectors}",
                "has_200_sessions": True, "above_200": i % 2 == 0,
                "source_asof": LATEST} for i in range(n_members)]
    return {"source": carry.BREADTH_WEEKLY_SOURCE, "as_of": LATEST, "basis": BASIS,
            "first_valid_date": "2010-01-08", "min_members": 10,
            "headline": carry.BREADTH_HEADLINE, "window_sessions": 200,
            "horizon_weeks": 13, "member_flag_source": carry.BREADTH_LEDGER_SOURCE,
            "sectors": sectors, "members": members}


def test_representative_breadth_block_fits_the_row_cap_and_reports_bytes():
    block = _representative_block()
    raw = json.dumps(block, ensure_ascii=False, allow_nan=False, sort_keys=True,
                     separators=(",", ":")).encode("utf-8")
    # report the measured bytes (visible with -s / on failure)
    print(f"\nsector_breadth representative encoded bytes: {len(raw)}")
    assert len(raw) <= _TYPED_ROW_BLOCK_MAX_BYTES
    assert len(raw) <= carry.MAX_ROW_BLOCK_BYTES
    # the carry itself accepts it (not stubbed)
    assert _typed_row_block(block, name="sector_breadth")["status"] == "available"


def test_generation_with_breadth_block_stays_under_the_four_mebibyte_bound():
    """An entitled generation envelope carrying the breadth block plus a generous
    legacy projection stays under the 4 MiB encoded bound; the bound is pinned, not
    moved. The breadth block is a small fraction of the budget."""
    block = _representative_block()
    breadth_bytes = len(json.dumps(block, ensure_ascii=False, allow_nan=False,
                                   sort_keys=True, separators=(",", ":")).encode("utf-8"))

    def envelope(filler_len: int) -> bytes:
        # A legacy projection filler standing in for the rest of the generation:
        # the bound check is on the COMPLETE envelope, exactly as the wire enforces.
        projection = {"data": {"typed_blocks": {"sector_breadth": {
            "status": "available", "reason": None, "value": block}},
            "filler": "x" * filler_len}, "receipt": {"content_sha256": "0" * 64}}
        return encode_sector_generation(
            audience="entitled", source_session=LATEST,
            published_at="2026-11-06T23:00:00+00:00", qualification="accepted",
            projection=projection)

    overhead = len(envelope(0))  # exact wrapper + breadth block + receipt bytes
    at_cap = envelope(MAX_ENCODED_BYTES - overhead)
    assert len(at_cap) == MAX_ENCODED_BYTES  # served at exactly the bound
    with pytest.raises(SectorGenerationTooLarge):  # one byte over is refused, never cut
        envelope(MAX_ENCODED_BYTES - overhead + 1)
    # A realistic generation (breadth block + a modest legacy projection) is well
    # under the bound; report the measured bytes.
    realistic = envelope(100_000)
    print(f"\nsector_breadth block: {breadth_bytes} bytes; envelope overhead {overhead}; "
          f"realistic generation {len(realistic)} bytes (bound {MAX_ENCODED_BYTES})")
    assert len(realistic) < MAX_ENCODED_BYTES
    assert breadth_bytes < MAX_ENCODED_BYTES // 10  # the frame is a small fraction

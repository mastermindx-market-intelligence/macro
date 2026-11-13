"""Tests for scripts.build_coverage_companion — listed-member coverage (counts only).

Made-up tickers and groups only; no reads outside tmp_path, no network, no skip.
Pinned:
  (a) hand-checked listed counts per session under the engine's half-open
      windows (start_date inclusive, end_date exclusive, open ends);
  (b) the 'unmapped' row carries listed members with no sector label — never
      dropped, never guessed into a sector;
  (c) no threshold / flag / floor column exists;
  (d) the sidecar carries the exact counts-only line and the house-registry
      sentence, with the commit each registry was read from.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.build_coverage_companion import (
    COUNTS_ONLY, HOUSE_NOTE, UNMAPPED, build, coverage_frame,
)

CAL = pd.bdate_range("2020-01-01", periods=5)  # Jan 1, 2, 3, 6, 7


def _mem() -> pd.DataFrame:
    return pd.DataFrame([
        {"ticker": "T1", "group": "Alpha", "start_date": CAL[0], "end_date": CAL[3]},
        {"ticker": "T2", "group": "Alpha", "start_date": pd.NaT, "end_date": pd.NaT},
        {"ticker": "T3", "group": "Beta", "start_date": CAL[2], "end_date": pd.NaT},
        {"ticker": "T4", "group": None, "start_date": pd.NaT, "end_date": pd.NaT},
        {"ticker": "T5", "group": "Beta", "start_date": CAL[0], "end_date": CAL[1]},
    ])


def _cell(df: pd.DataFrame, d, g: str) -> int:
    row = df[(df["session_date"] == d) & (df["group_key"] == g)]
    assert len(row) == 1, f"expected one row for {d}/{g}, got {len(row)}"
    return int(row.iloc[0]["n_listed"])


# ── (a) hand-checked listed counts per date ──────────────────────────────────

def test_listed_counts_per_date_hand_checked():
    df = coverage_frame(_mem(), CAL, ["Alpha", "Beta"], "sp500")
    # Alpha = T1 (on Jan 1,2,3; off Jan 6) + T2 (always)
    assert [_cell(df, d, "Alpha") for d in CAL] == [2, 2, 2, 1, 1]
    # Beta = T3 (from Jan 3) + T5 (Jan 1 only)
    assert [_cell(df, d, "Beta") for d in CAL] == [1, 0, 1, 1, 1]
    # unmapped = T4 (always)
    assert [_cell(df, d, UNMAPPED) for d in CAL] == [1, 1, 1, 1, 1]
    # total listed per session (T1..T5 under their windows)
    tot = df.groupby("session_date")["n_listed"].sum()
    assert [int(tot[d]) for d in CAL] == [4, 3, 4, 3, 3]


# ── (b) unmapped row ─────────────────────────────────────────────────────────

def test_unmapped_not_dropped_or_guessed():
    df = coverage_frame(_mem(), CAL, ["Alpha", "Beta"], "sp500")
    assert set(df["group_key"]) == {"Alpha", "Beta", UNMAPPED}
    # T4 (no label) is counted only under unmapped, on every session
    assert (df[df["group_key"] == UNMAPPED]["n_listed"] == 1).all()


# ── (c) no flag / threshold / floor column ───────────────────────────────────

def test_no_flag_or_threshold_column():
    df = coverage_frame(_mem(), CAL, ["Alpha", "Beta"], "sp500")
    assert list(df.columns) == ["src", "group_key", "session_date", "n_listed"]
    banned = ("flag", "usable", "thin", "threshold", "floor")
    assert not any(b in c.lower() for c in df.columns for b in banned)


# ── (d) end-to-end build on a made-up fixture ────────────────────────────────

def _write_fixture(tmp_path: Path):
    breadth = tmp_path / "breadth"
    breadth.mkdir()
    mem = pd.DataFrame([
        # sp500
        {"ticker": "T1", "start_date": CAL[0], "end_date": CAL[3], "src": "sp500"},
        {"ticker": "T2", "start_date": pd.NaT, "end_date": pd.NaT, "src": "sp500"},
        {"ticker": "T3", "start_date": CAL[2], "end_date": pd.NaT, "src": "sp500"},
        {"ticker": "T4", "start_date": pd.NaT, "end_date": pd.NaT, "src": "sp500"},
        {"ticker": "T5", "start_date": CAL[0], "end_date": CAL[1], "src": "sp500"},
        # sp400 (map covers U1; U2 unlabeled)
        {"ticker": "U1", "start_date": pd.NaT, "end_date": pd.NaT, "src": "sp400"},
        {"ticker": "U2", "start_date": pd.NaT, "end_date": pd.NaT, "src": "sp400"},
        # sp600 (map covers U3)
        {"ticker": "U3", "start_date": pd.NaT, "end_date": pd.NaT, "src": "sp600"},
    ])
    mem.to_parquet(breadth / "sp1500_pit_membership.parquet", index=False)
    sec = pd.DataFrame({
        "ticker": ["T1", "T2", "T3", "T4", "T5", "U1", "U2", "U3"],
        "sector": ["Alpha", "Alpha", "Beta", None, "Beta", "Alpha", None, "Beta"],
    })
    sec.to_parquet(breadth / "sp1500_pit_sectors.parquet", index=False)

    dated = tmp_path / "dated.parquet"
    pd.DataFrame({"date": CAL}).to_parquet(dated, index=False)

    reg_json = tmp_path / "membership.json"
    reg_json.write_text(json.dumps({"baskets": {
        "bx": {"members": [{"ticker": "T1", "removed": None},
                            {"ticker": "T2", "removed": "2020-01-01"}]},
    }}))
    reg_dir = tmp_path / "registry"
    reg_dir.mkdir()
    pd.DataFrame({"ticker": ["T1", "T2", "T3"], "group": ["g1", "g1", "g2"]}).to_csv(
        reg_dir / "fam.csv", index=False)
    return breadth, dated, reg_json, reg_dir


def test_build_end_to_end_fixture(tmp_path):
    breadth, dated, reg_json, reg_dir = _write_fixture(tmp_path)
    out = tmp_path / "out"
    mc, bc, fc, cc = "m" * 40, "b" * 40, "f" * 40, "c" * 40
    meta = build(breadth, dated, reg_json, reg_dir, out, mc, bc, fc, cc)

    cov = pd.read_parquet(out / "coverage_listed_dated.parquet")
    assert list(cov.columns) == ["src", "group_key", "session_date", "n_listed"]
    assert not any(b in c.lower() for c in cov.columns
                   for b in ("flag", "usable", "thin", "threshold", "floor"))
    # all three srcs are covered by the same map -> included
    assert set(cov["src"]) == {"sp500", "sp400", "sp600"}
    assert UNMAPPED in set(cov["group_key"])
    # hand-checked sp500 Alpha on the first session
    assert _cell(cov[cov["src"] == "sp500"], CAL[0], "Alpha") == 2
    # sp400 U2 unlabeled -> unmapped on every session
    sp400 = cov[cov["src"] == "sp400"]
    assert (sp400[sp400["group_key"] == UNMAPPED]["n_listed"] == 1).all()

    side = json.loads((out / "coverage_listed.meta.json").read_text())
    assert side["counts_only"] == COUNTS_ONLY
    assert side["house_registry_sizes"]["note"] == HOUSE_NOTE
    assert side["group_map"]["commit"] == mc
    assert side["house_registry_sizes"]["baskets"]["commit"] == bc
    assert side["house_registry_sizes"]["families"]["commit"] == fc
    assert side["calendar"]["commit"] == cc
    assert side["rows"] == len(cov)
    # active basket members only (T2 removed) -> size 1
    assert side["house_registry_sizes"]["baskets"]["sizes"]["bx"] == 1
    assert side["house_registry_sizes"]["families"]["sizes"]["fam.csv"] == {"g1": 2, "g2": 1}
    # blob SHAs are present for the data inputs
    assert all(len(i["blob_sha"]) == 40 for i in side["inputs"])

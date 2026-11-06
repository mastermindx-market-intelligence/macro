"""CN live-pack frozen board — canonical factordata projection (China P1).

`load_frozen` reads `site/factordata/china_standouts.json`: the four primary
arrays projected exactly once, `prophet.score` → flat score input, published
`board_rank` → flat rank input, `score_rank` kept as a separately named leg.
Fixtures are tmp_path only — the repository's real board is never read.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from engine.prophet_live import cn_pack as CP
from scripts.build_cn_live_pack import load_frozen

ROOT = Path(__file__).resolve().parent.parent
BASE_SHA = "e5dd30c6344e4b62a0beba054ac4da97e00bab36"
FACTORDATA = "site/factordata/china_standouts.json"
LEGACY_SITE = "site/china_standouts.json"

PRIMARY_TICKERS = ("600519.SS", "300750.SZ", "688981.SS", "000001.SZ", "601318.SS")
WATCH_ONLY = "002594.SZ"
REVERSAL_ONLY = "601899.SS"


def _row(ticker: str, score: object = 75.0, board_rank: object = 5,
         score_rank: object = 9) -> dict:
    return {
        "ticker": ticker,
        "name": ticker,
        "prophet": {"version": "cn_prophet_v4", "score": score},
        "board_rank": board_rank,
        "score_rank": score_rank,
        "display_rank": board_rank,
    }


def _primary_doc() -> dict:
    """Four unique primary rows, a watch alias repeating two of them plus one
    watch-only ticker, and a reversal_watch row — the nightly shape."""
    return {
        "as_of": "2026-10-16",
        "buy": [_row("600519.SS", score=78.75, board_rank=1, score_rank=2),
                _row("300750.SZ", score=71.0, board_rank=4, score_rank=1)],
        "more_actionable": [_row("688981.SS", score=68.5, board_rank=7, score_rank=5)],
        "late_or_unfillable": [_row("000001.SZ", score=55.0, board_rank=9, score_rank=12)],
        "forming": [_row("601318.SS", score=48.0, board_rank=11, score_rank=20)],
        "watch": [_row("688981.SS"), _row("000001.SZ"),
                  _row(WATCH_ONLY, board_rank=30, score_rank=31)],
        "reversal_watch": [_row(REVERSAL_ONLY, board_rank=40, score_rank=41)],
    }


def _write(root: Path, rel: str, doc: object) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc), encoding="utf-8")


def test_p1_primary_arrays_projected_exactly_once(tmp_path: Path) -> None:
    _write(tmp_path, FACTORDATA, _primary_doc())
    frozen = load_frozen(tmp_path)
    assert set(frozen) == set(PRIMARY_TICKERS)
    assert WATCH_ONLY not in frozen
    assert REVERSAL_ONLY not in frozen
    assert len(frozen) == 5  # the primary row count, not the alias-inflated one


def test_p2_score_and_board_rank_map_score_rank_rides_separately(tmp_path: Path) -> None:
    doc = _primary_doc()
    doc["buy"][0]["board_rank"], doc["buy"][0]["score_rank"] = 3, 8
    doc["buy"][0]["prophet"]["score"] = 62.5
    _write(tmp_path, FACTORDATA, doc)
    frozen = load_frozen(tmp_path)
    blob = frozen["600519.SS"]
    assert blob["prophet_score"] == 62.5
    assert blob["prophet_rank"] == 3
    assert blob["score_rank"] == 8

    entry = CP.attach_frozen({}, blob)
    assert entry["frozen"]["rank"] == 3  # published board rank, never score_rank
    assert entry["frozen"]["score_rank"] == 8
    assert entry["frozen"]["score"] == 62.5
    assert entry["repaint_disclosure"]["frozen_as_of"][-1] == "score_rank"


def test_p3_zero_is_a_valid_score(tmp_path: Path) -> None:
    _write(tmp_path, FACTORDATA,
           {"as_of": "2026-10-16", "buy": [_row("600519.SS", score=0)]})
    frozen = load_frozen(tmp_path)
    assert frozen["600519.SS"]["prophet_score"] == 0
    entry = CP.attach_frozen({}, frozen["600519.SS"])
    assert entry["frozen"]["score"] == 0


def test_p4_bad_rows_refuse_under_their_own_reason_only() -> None:
    bad_score = [None, float("nan"), float("inf"), -0.1, 100.1, "80", True]
    bad_rank = [0, None, True, "1"]
    bad_ticker = ["AAPL", "600519.HK"]
    rows = ([_row(f"6000{i:02d}.SS", score=s) for i, s in enumerate(bad_score)]
            + [_row(f"6001{i:02d}.SS", board_rank=r) for i, r in enumerate(bad_rank)]
            + [_row(t) for t in bad_ticker]
            + [_row("600519.SS")])  # valid sibling still projects
    doc = {"as_of": "2026-10-16", "buy": rows}
    projected, receipt = CP.project_primary_board(doc)
    assert set(projected) == {"600519.SS"}
    assert receipt["primary_rows"] == len(rows)
    assert receipt["projected"] == 1
    assert receipt["excluded"] == {"score": len(bad_score), "board_rank": len(bad_rank),
                                   "ticker": len(bad_ticker)}


def test_p5_duplicate_across_primary_arrays_refuses(tmp_path: Path) -> None:
    doc = {"as_of": "2026-10-16", "buy": [_row("600519.SS")],
           "forming": [_row("600519.SS")]}
    _write(tmp_path, FACTORDATA, doc)
    assert load_frozen(tmp_path) == {}
    assert CP.project_primary_board(doc) == (
        {}, {"refused": "duplicate_ticker", "ticker": "600519.SS"})


def test_p6_bad_as_of_missing_file_and_unreadable_fallback(tmp_path: Path) -> None:
    for bad_as_of in ("2026-10-16T00:00Z", "2026-13-40", "not-a-date"):
        _write(tmp_path, FACTORDATA, {"as_of": bad_as_of, "buy": [_row("600519.SS")]})
        assert load_frozen(tmp_path) == {}

    shutil.rmtree(tmp_path / "site")
    assert load_frozen(tmp_path) == {}  # missing file

    # Unreadable factordata JSON falls through to a valid legacy lanes doc.
    (tmp_path / "site" / "factordata").mkdir(parents=True, exist_ok=True)
    (tmp_path / "site" / "factordata" / "china_standouts.json").write_text(
        "{not json", encoding="utf-8")
    _write(tmp_path, LEGACY_SITE,
           {"lanes": {"featured": [{"ticker": "600519.SS"}]}})
    frozen = load_frozen(tmp_path)
    assert set(frozen) == {"600519.SS"}
    assert frozen["600519.SS"]["lane"] == "featured"


def test_p7_factordata_wins_and_legacy_alone_stays_base_shaped(tmp_path: Path) -> None:
    _write(tmp_path, FACTORDATA, _primary_doc())
    _write(tmp_path, LEGACY_SITE,
           {"lanes": {"featured": [{"ticker": "600519.SS"},
                                   {"ticker": "AAPL"}]}})
    frozen = load_frozen(tmp_path)
    assert set(frozen) == set(PRIMARY_TICKERS)  # factordata doc wins

    root2 = tmp_path / "legacy-only"
    _write(root2, LEGACY_SITE,
           {"lanes": {"featured": [{"ticker": "600519.SS"}],
                      "watch": [{"symbol": "000001.SZ"}]}})
    legacy = load_frozen(root2)
    assert set(legacy) == {"600519.SS", "000001.SZ"}
    assert legacy["600519.SS"]["lane"] == "featured"
    assert legacy["000001.SZ"]["lane"] == "watch"


def test_p8_base_load_frozen_ignored_the_factordata_board(tmp_path: Path) -> None:
    """BASE proof: the pre-fix loader returned {} for the canonical board."""
    if subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e",
                       f"{BASE_SHA}^{{commit}}"]).returncode != 0:
        pytest.skip(f"BASE {BASE_SHA[:8]} absent from this clone (shallow checkout)")
    src = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{BASE_SHA}:scripts/build_cn_live_pack.py"],
        capture_output=True, text=True, check=True).stdout
    mod_path = tmp_path / "_base_build_cn_live_pack.py"  # throwaway, outside the repo
    mod_path.write_text(src, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("_base_build_cn_live_pack", mod_path)
    base_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base_mod)
    _write(tmp_path, FACTORDATA, _primary_doc())
    assert base_mod.load_frozen(tmp_path) == {}


def test_module_contract_survives_the_projection() -> None:
    assert CP.PRIMARY_BOARD_ARRAYS == ("buy", "more_actionable", "late_or_unfillable",
                                       "forming")
    assert CP.FROZEN_LEG_KEYS[-1] == "score_rank"
    assert "score_rank" not in CP.FROZEN_LEG_KEYS[:-1]

"""Tests for scripts/extend_group_breadth_weekly.py (the live weekly file, ruling 27 section 5).

Network-free: a fake downloader returns synthetic, independent random walks.
These are made-up numbers only. What is pinned:

  (a) rerun on the same data writes nothing (the files' mtimes do not change);
  (b) final week: kept when it ends on Thursday (a holiday week), dropped when it ends on Wednesday;
  (c) a sector with fewer than 10 priced members stays missing (NaN level and change);
  (d) an alias: a member listed as MMC and priced via MRSH appears under MMC;
  (e) the download goes to the scratch path and never to a file named _closes_cache.parquet;
  (f) the archive comparison is recorded in the meta and never raises, even on a large difference.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.extend_group_breadth_weekly as ext

NOW = datetime(2026, 11, 12, 7, 0, tzinfo=timezone.utc)


def _members(tmp: Path, groups: dict[str, list[str]]) -> Path:
    bd = tmp / "breadth"
    bd.mkdir(parents=True, exist_ok=True)
    rows = [(t, g) for g, ts in groups.items() for t in ts]
    pd.DataFrame(rows, columns=["symbol", "sector"]).set_index("symbol").to_parquet(bd / "constituents.parquet")
    return bd


def _fake(end: str, n: int = 320, seed: int = 0):
    """Downloader returning independent random walks for exactly the requested symbols."""
    idx = pd.bdate_range(end=end, periods=n)

    def dl(tickers, period):
        rng = np.random.default_rng(seed)
        data = {t: 100 * np.exp(np.cumsum(rng.normal(0, 0.02, n))) for t in tickers}
        return pd.DataFrame(data, index=idx)
    return dl


def _groups(big: int = 12, small: int = 4):
    return {"Alpha": [f"A{i:02d}" for i in range(big)],
            "Beta": [f"B{i:02d}" for i in range(big)],
            "Tiny": [f"T{i:02d}" for i in range(small)]}


def test_rerun_on_same_data_writes_nothing(tmp_path):
    bd, out = _members(tmp_path, _groups()), tmp_path / "out"
    dl = _fake("2026-11-06")
    assert ext.build(bd, out, downloader=dl, scratch=tmp_path / "s", now=NOW)["status"] == "written"
    pq = out / f"{ext.LIVE_NAME}.parquet"
    meta = out / f"{ext.LIVE_NAME}.meta.json"
    m1, m2 = pq.stat().st_mtime_ns, meta.stat().st_mtime_ns
    assert ext.build(bd, out, downloader=dl, scratch=tmp_path / "s", now=NOW)["status"] == "unchanged"
    assert (pq.stat().st_mtime_ns, meta.stat().st_mtime_ns) == (m1, m2)


def test_final_week_thursday_kept_wednesday_dropped(tmp_path):
    bd = _members(tmp_path, _groups())
    thu = ext.build(bd, tmp_path / "thu", downloader=_fake("2026-11-26"), scratch=tmp_path / "s1", now=NOW)
    assert thu["as_of_week"] == "2026-11-26"  # Thursday (Thanksgiving week) kept
    wed = ext.build(bd, tmp_path / "wed", downloader=_fake("2026-11-04"), scratch=tmp_path / "s2", now=NOW)
    assert wed["as_of_week"] == "2026-10-30"  # Wednesday end dropped -> prior Friday


def test_sector_below_ten_members_stays_missing(tmp_path):
    bd, out = _members(tmp_path, _groups(big=12, small=4)), tmp_path / "out"
    ext.build(bd, out, downloader=_fake("2026-11-06"), scratch=tmp_path / "s", now=NOW)
    w = pd.read_parquet(out / f"{ext.LIVE_NAME}.parquet")
    tiny = w[w["group"] == "Tiny"]
    assert len(tiny) and tiny["pct_above_200"].isna().all()
    assert tiny[ext.HEADLINE].isna().all()
    assert w[w["group"] == "Alpha"]["pct_above_200"].notna().any()


def test_alias_member_priced_under_its_listed_ticker(tmp_path):
    g = _groups()
    g["Alpha"] = g["Alpha"][:-1] + ["MMC"]
    bd, out = _members(tmp_path, g), tmp_path / "out"
    asked: list[str] = []
    base = _fake("2026-11-06")

    def dl(tickers, period):
        asked.extend(tickers)
        return base(tickers, period)
    r = ext.build(bd, out, downloader=dl, scratch=tmp_path / "s", now=NOW)
    assert "MRSH" in asked and "MMC" not in asked
    assert "MMC" not in r["members"]["unpriced"]
    assert r["aliases"]["MMC"]["downloaded_as"] == "MRSH"
    alpha = r["counts_last_week"]["by_sector"]["Alpha"]
    assert alpha["in_map"] == alpha["n_members"] == 12
    assert alpha["n_fixed_200_13w"] <= alpha["n_has_200"] <= alpha["n_members"]


def test_download_never_lands_in_the_collector_cache(tmp_path):
    bd, out, scratch = _members(tmp_path, _groups()), tmp_path / "out", tmp_path / "scratch"
    ext.build(bd, out, downloader=_fake("2026-11-06"), scratch=scratch, now=NOW)
    assert (scratch / "live_download.parquet").exists()
    assert not list(tmp_path.rglob("_closes_cache.parquet"))


def test_comparison_recorded_never_a_gate(tmp_path):
    bd, out = _members(tmp_path, _groups()), tmp_path / "out"
    ext.build(bd, out, downloader=_fake("2026-11-06"), scratch=tmp_path / "s1", now=NOW)
    live = pd.read_parquet(out / f"{ext.LIVE_NAME}.parquet")
    arch = live.copy()
    arch[ext.HEADLINE] = arch[ext.HEADLINE] + 50.0  # a large, deliberate difference
    arch.to_parquet(out / ext.ARCHIVE_NAME, index=False)
    (out / f"{ext.LIVE_NAME}.parquet").unlink()
    r = ext.build(bd, out, downloader=_fake("2026-11-06"), scratch=tmp_path / "s2", now=NOW)
    cmp = json.loads((out / f"{ext.LIVE_NAME}.meta.json").read_text())["comparison_vs_archive"]
    assert r["status"] == "written" and cmp["is_gate"] is False
    assert abs(cmp["each_file_own_members"]["max_abs_diff"] - 50.0) < 1e-6
    assert cmp["each_file_own_members"]["common_weeks"] > 0


def test_comparison_records_both_member_sets(tmp_path):
    """Own members vs common members: the second drops the names the archive could not price."""
    bd, out = _members(tmp_path, _groups()), tmp_path / "out"
    ext.build(bd, out, downloader=_fake("2026-11-06"), scratch=tmp_path / "s1", now=NOW)
    live = pd.read_parquet(out / f"{ext.LIVE_NAME}.parquet")
    live.to_parquet(out / ext.ARCHIVE_NAME, index=False)
    (out / ext.ARCHIVE_META).write_text(json.dumps(
        {"coverage": {"members_unpriced": 2, "unpriced_sample": ["A00", "A01"]}}))
    (out / f"{ext.LIVE_NAME}.parquet").unlink()
    ext.build(bd, out, downloader=_fake("2026-11-06"), scratch=tmp_path / "s2", now=NOW)
    cmp = json.loads((out / f"{ext.LIVE_NAME}.meta.json").read_text())["comparison_vs_archive"]
    assert cmp["each_file_own_members"]["max_abs_diff"] == 0.0
    assert cmp["members_priced_only_in_live"] == {"count": 2, "tickers": ["A00", "A01"]}
    assert "common_members_only" in cmp


def test_truncated_archive_sample_skips_common_comparison(tmp_path):
    meta = tmp_path / "m.json"
    meta.write_text(json.dumps({"coverage": {"members_unpriced": 30, "unpriced_sample": ["X"]}}))
    assert ext.archive_unpriced(meta) is None



# --- house-basket live file (ruling 108) -------------------------------------------------------

def _roster(tmp: Path, baskets: dict[str, list[str]], removed: tuple[str, ...] = ()) -> Path:
    p = tmp / "membership.json"
    p.write_text(json.dumps({"baskets": {
        b: {"name": b, "members": [{"ticker": t, "removed": ("2026-01-01" if t in removed else None)}
                                    for t in ts]}
        for b, ts in baskets.items()}}))
    return p


def _two_call_fake(end: str, fail_second: bool = False, drop: int = 0, lose: int = 0, n: int = 320):
    """First call (sectors) succeeds; the second (basket extras) can raise, miss the last
    session for ``drop`` names, or return no data at all for ``lose`` names."""
    base = _fake(end, n=n)
    calls: list[list[str]] = []

    def dl(tickers, period):
        calls.append(list(tickers))
        if len(calls) > 1:
            if fail_second:
                raise RuntimeError("rate limited")
            df = base(tickers, period)
            if drop:
                df.loc[df.index[-1], list(df.columns[:drop])] = float("nan")
            if lose:
                df.loc[:, list(df.columns[:lose])] = float("nan")
            return df
        return base(tickers, period)
    dl.calls = calls
    return dl


def _baskets():
    return {"hb_alpha": [f"A{i:02d}" for i in range(6)] + [f"X{i:02d}" for i in range(6)],
            "hb_new": [f"X{i:02d}" for i in range(12)]}


def test_basket_file_written_with_counts_and_start(tmp_path):
    bd, out = _members(tmp_path, _groups()), tmp_path / "out"
    mp = _roster(tmp_path, _baskets(), removed=("X11",))
    dl = _two_call_fake("2026-11-06")
    r = ext.build(bd, out, downloader=dl, scratch=tmp_path / "s", now=NOW, membership_path=mp)
    assert r["baskets"]["status"] == "written"
    # the second call asks only for names the sector download did not already hold
    assert sorted(dl.calls[1]) == [f"X{i:02d}" for i in range(11)]
    w = pd.read_parquet(out / f"{ext.BASKET_LIVE_NAME}.parquet")
    assert set(w["group"]) == {"hb_alpha", "hb_new"}
    assert list(w.columns) == list(pd.read_parquet(out / f"{ext.LIVE_NAME}.parquet").columns)
    meta = json.loads((out / f"{ext.BASKET_LIVE_NAME}.meta.json").read_text())
    assert meta["counts"]["by_basket"]["hb_alpha"] == {"listed": 12, "priced": 12, "absent": 0}
    assert meta["counts"]["by_basket"]["hb_new"] == {"listed": 11, "priced": 11, "absent": 0}
    assert meta["history_start"] == meta["span"]["closes_start"]
    assert meta["coverage_floor"]["value"] == ext.BASKET_COVERAGE_FLOOR == 0.90
    # the source is described neutrally: the field is exactly the generic wording
    assert meta["price_source"].startswith("full-window download (period ")
    assert meta["price_source"].endswith("auto-adjusted closes; never the collector's cache (#11124)")
    assert not list(out.glob("*.tmp"))


def _boom(*_a, **_k):
    raise RuntimeError("failure after the download")


@pytest.mark.parametrize("mode", ["second_call_raises", "below_floor", "raises_after_download"])
def test_sector_file_unchanged_when_basket_names_fail(tmp_path, monkeypatch, mode):
    bd = _members(tmp_path, _groups())
    mp = _roster(tmp_path, _baskets())
    ext.build(bd, tmp_path / "plain", downloader=_fake("2026-11-06"), scratch=tmp_path / "s0", now=NOW)
    dl = {"second_call_raises": _two_call_fake("2026-11-06", fail_second=True),
          "below_floor": _two_call_fake("2026-11-06", lose=6),
          "raises_after_download": _two_call_fake("2026-11-06")}[mode]
    if mode == "raises_after_download":
        monkeypatch.setattr(ext, "expand_multi", _boom)
    r = ext.build(bd, tmp_path / "fail", downloader=dl, scratch=tmp_path / "s1", now=NOW, membership_path=mp)
    assert r["status"] == "written" and r["baskets"]["status"] == "not_written"
    for name in (f"{ext.LIVE_NAME}.parquet", f"{ext.LIVE_NAME}.meta.json"):
        assert (tmp_path / "plain" / name).read_bytes() == (tmp_path / "fail" / name).read_bytes()
    assert not (tmp_path / "fail" / f"{ext.BASKET_LIVE_NAME}.parquet").exists()
    assert not (tmp_path / "fail" / f"{ext.BASKET_LIVE_NAME}.meta.json").exists()


def test_bad_night_keeps_previous_basket_file(tmp_path):
    bd, out = _members(tmp_path, _groups()), tmp_path / "out"
    mp = _roster(tmp_path, _baskets())
    ext.build(bd, out, downloader=_two_call_fake("2026-10-30"), scratch=tmp_path / "s0", now=NOW,
              membership_path=mp)
    pq = out / f"{ext.BASKET_LIVE_NAME}.parquet"
    mj = out / f"{ext.BASKET_LIVE_NAME}.meta.json"
    before, before_meta = pq.read_bytes(), mj.read_bytes()
    for dl in (_two_call_fake("2026-11-06", fail_second=True),
               _two_call_fake("2026-11-06", lose=6)):  # 6 of 18 names absent: below the floor
        r = ext.build(bd, out, downloader=dl, scratch=tmp_path / "s1", now=NOW, membership_path=mp)
        assert r["baskets"]["status"] == "not_written"
        assert pq.read_bytes() == before
        assert mj.read_bytes() == before_meta
        assert not list(out.glob("*.tmp"))


def test_coverage_floor_is_data_quality_only(tmp_path):
    """At the floor the file is written; a basket under MIN_MEMBERS still reads missing (unchanged rule)."""
    bd, out = _members(tmp_path, _groups()), tmp_path / "out"
    mp = _roster(tmp_path, {"hb_big": [f"X{i:02d}" for i in range(18)] + [f"A{i:02d}" for i in range(2)],
                            "hb_small": ["A00", "A01", "A02"]})
    # 2 of 20 distinct names absent = 0.90 coverage: exactly at the floor -> written
    r = ext.build(bd, out, downloader=_two_call_fake("2026-11-06", drop=2), scratch=tmp_path / "s",
                  now=NOW, membership_path=mp)
    assert r["baskets"]["status"] == "written"
    w = pd.read_parquet(out / f"{ext.BASKET_LIVE_NAME}.parquet")
    assert w[w["group"] == "hb_small"]["pct_above_200"].isna().all()


def test_without_roster_only_the_sector_file_is_built(tmp_path):
    bd, out = _members(tmp_path, _groups()), tmp_path / "out"
    r = ext.build(bd, out, downloader=_fake("2026-11-06"), scratch=tmp_path / "s", now=NOW)
    assert "baskets" not in r
    assert not (out / f"{ext.BASKET_LIVE_NAME}.parquet").exists()

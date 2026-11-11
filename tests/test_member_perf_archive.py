"""Tests for the per-MEMBER perf archive in scripts/fetch_finviz_themes.py.

Covers three contracts (commission 2026-11-11, rotation breadth research):
  (a) rows written == memberships provided (with perf), all horizons present
      and unchanged — capture-only, no adjustment, no derived field;
  (b) a second run for the same session date leaves the file byte-identical
      (immutable once written), and the payload itself is deterministic;
  (c) an exception inside the archive step does NOT propagate to the build —
      main() completes and still writes perf_snapshot.json.

All fixtures are synthetic and in-memory (tmp_path). Zero network calls, and
every date is pinned — a fixture that reads the wall clock is a scheduled
failure (same convention as tests/test_finviz_archival.py).
"""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import pytest

import scripts.fetch_finviz_themes as fft
from scripts.fetch_finviz_themes import write_member_perf_archive

TFS = ["1D", "1W", "1M", "MTD", "3M", "6M", "1Y", "YTD"]

# One theme, two subsectors; DECK appears in BOTH (a ticker may hold multiple
# memberships — breadth denominators are per-group); GONE is in the tree but not
# priced by the vendor (absent from member_perf).
TREE = [
    {"key": "tech", "theme": "Technology", "subsectors": [
        {"key": "aicompute", "name": "AI Compute", "members": ["NVDA", "AMD", "DECK"]},
        {"key": "fintech", "name": "Fintech", "members": ["DECK", "GONE"]},
    ]},
    {"key": "energy", "theme": "Energy", "subsectors": [
        {"key": "oilservices", "name": "Oil Services", "members": ["HAL"]},
    ]},
]
MEMBER_PERF = {
    "NVDA": {"1D": -1.27, "1W": 1.38, "1M": 3.82, "MTD": 1.72,
             "3M": 20.0, "6M": 57.55, "1Y": 21.54, "YTD": 30.73},
    "AMD": {"1D": 0.5, "1W": -2.0, "1M": 0.0, "MTD": -4.5,
            "3M": 1.25, "6M": 10.1, "1Y": -3.0, "YTD": 5.0},
    "DECK": {"1D": 2.2, "1W": 0.4, "1M": 6.6, "MTD": 6.6,
             "3M": 12.75, "6M": 4.0, "1Y": 44.0, "YTD": 9.99},
    "HAL": {"1D": -0.1, "1W": 3.3, "1M": -1.0, "MTD": 2.0,
            "3M": -8.8, "6M": -12.5, "1Y": -20.0, "YTD": -7.7},
}
FETCHED_AT = "2026-11-11T22:30:41+00:00"
#: priced memberships in TREE: aicompute(NVDA, AMD, DECK) + fintech(DECK) + oilservices(HAL)
EXPECTED_ROWS = 5


def _read(path: Path) -> tuple[dict, list[dict]]:
    """Decode one archive file: (meta, rows). First line is the meta record."""
    lines = gzip.decompress(path.read_bytes()).decode("utf-8").splitlines()
    parsed = [json.loads(x) for x in lines if x.strip()]
    return parsed[0], parsed[1:]


# ------------------------------------------------------------------ #
# (a) rows == memberships provided; horizons exact and unchanged
# ------------------------------------------------------------------ #

class TestRowsMatchMemberships:
    def test_row_count_equals_priced_memberships(self, tmp_path):
        written, p, rows = write_member_perf_archive(
            "2026-11-11", FETCHED_AT, TREE, MEMBER_PERF, dir_path=tmp_path)
        assert written is True
        assert rows == EXPECTED_ROWS
        _, file_rows = _read(p)
        assert len(file_rows) == EXPECTED_ROWS

    def test_multi_membership_ticker_gets_one_row_per_group(self, tmp_path):
        _, p, _ = write_member_perf_archive(
            "2026-11-11", FETCHED_AT, TREE, MEMBER_PERF, dir_path=tmp_path)
        decks = [r for r in _read(p)[1] if r["ticker"] == "DECK"]
        assert sorted(r["subsector"] for r in decks) == ["aicompute", "fintech"]

    def test_unpriced_member_is_absent(self, tmp_path):
        _, p, _ = write_member_perf_archive(
            "2026-11-11", FETCHED_AT, TREE, MEMBER_PERF, dir_path=tmp_path)
        assert all(r["ticker"] != "GONE" for r in _read(p)[1])

    def test_every_row_has_all_horizons_unchanged(self, tmp_path):
        _, p, _ = write_member_perf_archive(
            "2026-11-11", FETCHED_AT, TREE, MEMBER_PERF, dir_path=tmp_path)
        for r in _read(p)[1]:
            assert r["asof"] == "2026-11-11"
            assert r["theme"] and r["subsector"]
            # exactly the fetched horizons, values untouched — no derived field
            assert r["perf"] == MEMBER_PERF[r["ticker"]]
            assert sorted(r["perf"]) == sorted(TFS)

    def test_meta_line_carries_fetch_timestamp_once(self, tmp_path):
        _, p, _ = write_member_perf_archive(
            "2026-11-11", FETCHED_AT, TREE, MEMBER_PERF, dir_path=tmp_path)
        meta, rows = _read(p)
        assert meta["fetched_at_utc"] == FETCHED_AT
        assert meta["row_count"] == EXPECTED_ROWS
        assert all("fetched_at_utc" not in r for r in rows)  # once per FILE, not per row

    def test_file_name_contains_iso_date(self, tmp_path):
        _, p, _ = write_member_perf_archive(
            "2026-11-11", FETCHED_AT, TREE, MEMBER_PERF, dir_path=tmp_path)
        assert p.name == "2026-11-11.jsonl.gz"
        assert p.parent == tmp_path  # default lives under data/themes_heatmap/ in prod


# ------------------------------------------------------------------ #
# (b) immutable once written + deterministic payload
# ------------------------------------------------------------------ #

class TestImmutability:
    def test_second_run_same_session_is_skip_and_byte_identical(self, tmp_path):
        _, p, _rows = write_member_perf_archive(
            "2026-11-11", FETCHED_AT, TREE, MEMBER_PERF, dir_path=tmp_path)
        first_bytes = p.read_bytes()
        written2, p2, rows2 = write_member_perf_archive(  # DIFFERENT data, same asof
            "2026-11-11", "2026-11-12T22:30:00+00:00", TREE, {"NVDA": {"1D": 9.9}},
            dir_path=tmp_path)
        assert written2 is False and rows2 == 0 and p2 == p
        assert p.read_bytes() == first_bytes  # not overwritten, not even re-written

    def test_payload_is_deterministic_across_fresh_writes(self, tmp_path):
        """mtime=0: the same inputs in a fresh dir give identical bytes — the
        file is reproducible, not just append-once."""
        _, p1, _ = write_member_perf_archive(
            "2026-11-11", FETCHED_AT, TREE, MEMBER_PERF, dir_path=tmp_path / "a")
        _, p2, _ = write_member_perf_archive(
            "2026-11-11", FETCHED_AT, TREE, MEMBER_PERF, dir_path=tmp_path / "b")
        assert p1.read_bytes() == p2.read_bytes()

    def test_distinct_sessions_are_distinct_files(self, tmp_path):
        write_member_perf_archive("2026-11-11", FETCHED_AT, TREE, MEMBER_PERF, dir_path=tmp_path)
        w2, _p2, r2 = write_member_perf_archive(
            "2026-11-12", FETCHED_AT, TREE, MEMBER_PERF, dir_path=tmp_path)
        assert w2 is True and r2 == EXPECTED_ROWS
        assert sorted(x.name for x in tmp_path.glob("*.jsonl.gz")) == [
            "2026-11-11.jsonl.gz", "2026-11-12.jsonl.gz"]

    def test_no_tmp_leftover_after_success(self, tmp_path):
        write_member_perf_archive("2026-11-11", FETCHED_AT, TREE, MEMBER_PERF, dir_path=tmp_path)
        assert list(tmp_path.glob("*.tmp")) == []


# ------------------------------------------------------------------ #
# (c) an archive-step exception never fails the build
# ------------------------------------------------------------------ #

class TestFailureIsolation:
    def _run_main(self, monkeypatch, tmp_path, archive_impl):
        """Drive real main() with the network and every data path redirected.

        fetch_subsector_perf/fetch_member_perf are stubbed (no network); all five
        output paths land in tmp_path; _asof_stamp is pinned. Returns the
        SystemExit code, or None when main() returned normally."""
        out = tmp_path / "out"
        out.mkdir()
        tree_path = out / "themes_tree.json"
        tree_path.write_text(json.dumps(TREE))
        monkeypatch.setattr(fft, "OUT_DIR", out)
        monkeypatch.setattr(fft, "TREE_PATH", tree_path)
        monkeypatch.setattr(fft, "PERF_PATH", out / "perf_snapshot.json")
        monkeypatch.setattr(fft, "SUBSECTOR_PERF_HISTORY_PATH",
                            out / "subsector_perf_history.jsonl")
        monkeypatch.setattr(fft, "TREE_HISTORY_PATH", out / "tree_history.jsonl")
        monkeypatch.setattr(fft, "MEMBER_PERF_ARCHIVE_DIR", out / "member_perf_archive")
        # member price state (2026-11-11, lane 10): main() now writes a SECOND
        # archive on this same path; redirect it too, or this harness writes a
        # synthetic-roster file into the real data/ tree — where the exists→skip
        # immutability rule would then block that date's true nightly capture.
        monkeypatch.setattr(fft, "MEMBER_PRICE_STATE_DIR", out / "member_price_state")
        monkeypatch.setattr(fft, "PRICE_STATE_YAHOO_DIR", out / "yahoo")
        monkeypatch.setattr(fft, "PRICE_STATE_UNIVERSE_LEDGER",
                            out / "membership.parquet")
        monkeypatch.setattr(fft, "PRICE_STATE_SPY_HOLDINGS_DIR", out / "spy")
        # elapsed-seconds record (COO ruling 9): main() merges the step timing
        # into data/run_status.json now; redirect that too — same exposure class.
        monkeypatch.setattr(fft, "PRICE_STATE_RUN_STATUS", out / "run_status.json")
        monkeypatch.setattr(fft, "fetch_subsector_perf",
                            lambda: {"aicompute": {"1D": 1.0}, "fintech": {"1D": -2.0}})
        monkeypatch.setattr(fft, "fetch_member_perf", lambda tickers: MEMBER_PERF)
        monkeypatch.setattr(fft, "_asof_stamp", lambda now_utc=None: "2026-11-11")
        monkeypatch.setattr(fft, "write_member_perf_archive", archive_impl)
        monkeypatch.setattr(sys, "argv", ["fetch_finviz_themes.py"])
        try:
            fft.main()
            return None
        except SystemExit as e:
            return e.code

    def test_archive_exception_does_not_propagate(self, monkeypatch, tmp_path, capsys):
        def boom(*a, **kw):
            raise OSError("disk full mid-archive")

        code = self._run_main(monkeypatch, tmp_path, boom)
        assert code is None, "archive failure must not exit the build"
        # the snapshot and BOTH irreplaceable PIT archives were still written
        assert json.loads((tmp_path / "out" / "perf_snapshot.json").read_text())["asof"] \
            == "2026-11-11"
        assert (tmp_path / "out" / "subsector_perf_history.jsonl").exists()
        assert (tmp_path / "out" / "tree_history.jsonl").exists()
        # and the failure was LOUD, as a line-start annotation (house law)
        err = capsys.readouterr().err
        assert any(l.startswith("::error::") and "member perf archive" in l
                   for l in err.splitlines())

    def test_healthy_main_writes_archive(self, monkeypatch, tmp_path):
        code = self._run_main(monkeypatch, tmp_path, fft.write_member_perf_archive)
        assert code is None
        d = tmp_path / "out" / "member_perf_archive"
        (p,) = list(d.glob("*.jsonl.gz"))
        meta, rows = _read(p)
        assert meta["asof"] == "2026-11-11" and len(rows) == EXPECTED_ROWS

    def test_real_function_ok_when_dir_unwritable_raises_only_inside(self, tmp_path):
        """Sanity on the isolation boundary itself: the real function CAN raise
        (here: parent dir path occupied by a file); the caller's try/except in
        main() is what keeps that from failing the build (proven above)."""
        blocker = tmp_path / "blocked"
        blocker.write_text("not a dir")
        with pytest.raises(OSError):
            write_member_perf_archive("2026-11-11", FETCHED_AT, TREE,
                                      MEMBER_PERF, dir_path=blocker / "x")

"""B11 — the cycle forward log refuses lane-off, future and replay appends.

Masterplan B11: "Replays cannot advance live ledgers or send alerts." House law
HOUSE-U5 makes nightly the SOLE advancer of data/ forward ledgers, but the shared
writer (engine/cycle_forward_log.py) had no gate: render.yml's replay band runs
build_sector_cycles with no lane env and stamped rows into the live
data/sector_cycles/forward_log.parquet just like the nightly engine job did.

Pins (all via a temp data dir; the real ledger is never opened):
  * off-lane append (no COLLECT_LANE/US_LANE) for sector_cycles → 0 rows, no file;
  * nightly append works unchanged;
  * a FUTURE asOf (after today's UTC date) → 0 rows;
  * a REPLAY asOf (older than the newest prior date) → 0 rows;
  * an EQUAL date keeps the keep-FIRST behaviour (first write wins);
  * prior rows are byte-identical after every refusal — the log is never
    rewritten, truncated or deleted by a refused append.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pandas as pd


def _fake_data(asof: str) -> dict:
    """Minimal compute()-shaped dict: one sector + one basket (2 rows)."""
    def _rec(sid, kind):
        return {
            "id": sid, "kind": kind, "name": sid.upper(),
            "now": {"phase": "Expansion", "pos": 55.0, "osc_slope": 1.2,
                    "signal": None, "timing_state": "TRENDING",
                    "above200d": True, "rs_63d": 3.5},
            "proj": {"nextTurn": "peak", "central": "2027-03",
                     "low": "2026-11", "high": "2027-07"},
        }
    return {"meta": {"asOf": asof, "region": "us"},
            "sectors": [_rec("xlk", "sector")],
            "baskets": [_rec("b-mag7", "basket")]}


def _today() -> str:
    """The fence's clock is UTC — use the same one so a local-behind-UTC host
    (e.g. 2026-10-20 local while UTC already rolled to 10-21) never makes a
    'tomorrow' fixture land on UTC today."""
    return datetime.now(timezone.utc).date().isoformat()


def _patch(tmp_path, monkeypatch) -> None:
    """Temp data dir + a lane-clean env (no inherited COLLECT_LANE/US_LANE)."""
    import lib.config as config_mod
    monkeypatch.setattr(config_mod, "data_dir", lambda: tmp_path)
    for var in ("COLLECT_LANE", "US_LANE"):
        monkeypatch.delenv(var, raising=False)


def _log_bytes(tmp_path) -> bytes:
    return (tmp_path / "sector_cycles" / "forward_log.parquet").read_bytes()


def test_offlane_append_refused_and_no_file(tmp_path, monkeypatch):
    """No COLLECT_LANE (the render.yml replay band's env) → 0 rows, no ledger."""
    _patch(tmp_path, monkeypatch)
    import engine.cycle_forward_log as clf

    assert clf.append_forward_log(_fake_data(_today()), "sector_cycles") == 0
    assert not (tmp_path / "sector_cycles" / "forward_log.parquet").exists()


def test_nightly_append_works(tmp_path, monkeypatch):
    """COLLECT_LANE=nightly (the daily.yml engine job) appends as before."""
    _patch(tmp_path, monkeypatch)
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    import engine.cycle_forward_log as clf

    assert clf.append_forward_log(_fake_data(_today()), "sector_cycles") == 2
    p = tmp_path / "sector_cycles" / "forward_log.parquet"
    assert p.exists()
    df = pd.read_parquet(p)
    assert len(df) == 2 and set(df["id"]) == {"xlk", "b-mag7"}


def test_future_asof_refused(tmp_path, monkeypatch):
    """An asOf after today's UTC date never takes a real day's keep-FIRST slot."""
    _patch(tmp_path, monkeypatch)
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    import engine.cycle_forward_log as clf

    tomorrow = (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()
    assert clf.append_forward_log(_fake_data(tomorrow), "sector_cycles") == 0
    assert not (tmp_path / "sector_cycles" / "forward_log.parquet").exists()


def test_replay_asof_refused_and_prior_rows_byte_identical(tmp_path, monkeypatch):
    """An older session must not be backfilled after a newer one was observed."""
    _patch(tmp_path, monkeypatch)
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    import engine.cycle_forward_log as clf

    today = _today()
    older = (datetime.now(timezone.utc).date() - timedelta(days=5)).isoformat()
    assert clf.append_forward_log(_fake_data(today), "sector_cycles") == 2
    before = _log_bytes(tmp_path)

    assert clf.append_forward_log(_fake_data(older), "sector_cycles") == 0
    assert _log_bytes(tmp_path) == before, "replay refusal rewrote the ledger"

    # and the off-lane refusal leaves the nightly prior untouched too
    monkeypatch.delenv("COLLECT_LANE", raising=False)
    assert clf.append_forward_log(_fake_data(today), "sector_cycles") == 0
    assert _log_bytes(tmp_path) == before, "lane refusal rewrote the ledger"


def test_equal_date_keep_first_unchanged(tmp_path, monkeypatch):
    """Equal date is NOT a replay — the existing keep-FIRST path still applies."""
    _patch(tmp_path, monkeypatch)
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    import engine.cycle_forward_log as clf

    today = _today()
    first = _fake_data(today)
    first["sectors"][0]["proj"]["central"] = "2027-03"
    assert clf.append_forward_log(first, "sector_cycles") == 2

    second = _fake_data(today)
    second["sectors"][0]["proj"]["central"] = "2029-01"
    assert clf.append_forward_log(second, "sector_cycles") == 2

    df = pd.read_parquet(tmp_path / "sector_cycles" / "forward_log.parquet")
    xlk = df[df["id"] == "xlk"]
    assert len(xlk) == 1, "keep-FIRST violated: duplicate (date, id)"
    assert xlk.iloc[0]["proj_central"] == "2027-03", \
        "keep-FIRST violated: second write's value replaced the first"

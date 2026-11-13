"""Tests for engine.member_breadth_ledger — the nightly member-level breadth record.

Pins the writer against tmp_path ledgers (the real data/ ledger is never
opened), synthetic made-up rows only:

  * keep-FIRST per (date, ticker): a same-night re-run with a changed value
    never rewrites the first stamp;
  * the three B11 fences, in order — lane (no COLLECT_LANE/US_LANE → 0 rows,
    no file), future (a date after today's UTC date → 0 rows), replay (a date
    older than the newest prior date → 0 rows, prior bytes identical);
  * an EQUAL date is not a replay: new tickers on the same night append;
  * a multi-date batch is refused; missing columns → 0;
  * a corrupt prior file does not raise and is left untouched (no write);
  * the default path resolves through lib.config.data_dir() to
    data/breadth/member_breadth_ledger.parquet.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

import engine.member_breadth_ledger as mbl


def _rows(d: str, tickers, above=True, group="Tech") -> pd.DataFrame:
    """A one-night member_rows-shaped batch with made-up values."""
    return pd.DataFrame({
        "date": d,
        "ticker": list(tickers),
        "group": group,
        "has_200_sessions": True,
        "above_200": above,
        "source_asof": d,
    })


def _today() -> str:
    """The fence's clock is UTC — same one, so a local-behind-UTC host never
    turns a 'today' fixture into 'tomorrow'."""
    return datetime.now(timezone.utc).date().isoformat()


def _patch_lane(monkeypatch, on: bool = True) -> None:
    for var in ("COLLECT_LANE", "US_LANE"):
        monkeypatch.delenv(var, raising=False)
    if on:
        monkeypatch.setenv("COLLECT_LANE", "nightly")


# ── B11 fence 1 — lane ───────────────────────────────────────────────────────

def test_lane_refusal_without_collect_lane(tmp_path, monkeypatch):
    """No COLLECT_LANE (the off-lane env) → 0 rows, no ledger file."""
    _patch_lane(monkeypatch, on=False)
    p = tmp_path / "member_breadth_ledger.parquet"
    assert mbl.append_member_rows(_rows(_today(), ["AAPL", "MSFT"]), p) == 0
    assert not p.exists()


def test_legacy_us_lane_alias_accepted(tmp_path, monkeypatch):
    """US_LANE=nightly (the legacy alias) opens the lane like COLLECT_LANE."""
    for var in ("COLLECT_LANE", "US_LANE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("US_LANE", "nightly")
    p = tmp_path / "member_breadth_ledger.parquet"
    assert mbl.append_member_rows(_rows(_today(), ["AAPL"]), p) == 1
    assert p.exists()


# ── keep-FIRST per (date, ticker) ────────────────────────────────────────────

def test_keep_first_on_duplicate_key_with_changed_value(tmp_path, monkeypatch):
    """A same-night re-run never rewrites the first stamp for (date, ticker)."""
    _patch_lane(monkeypatch)
    p = tmp_path / "member_breadth_ledger.parquet"
    d = _today()

    assert mbl.append_member_rows(_rows(d, ["AAPL", "MSFT"], above=True), p) == 2
    assert mbl.append_member_rows(_rows(d, ["AAPL", "MSFT"], above=False), p) == 2

    df = pd.read_parquet(p)
    assert len(df) == 2, "keep-FIRST violated: duplicate (date, ticker) rows"
    by_t = df.set_index("ticker")
    assert bool(by_t.loc["AAPL", "above_200"]) is True, \
        "keep-FIRST violated: second write replaced the first value"
    assert bool(by_t.loc["MSFT", "above_200"]) is True


def test_equal_date_appends_new_tickers(tmp_path, monkeypatch):
    """Equal date is NOT a replay — new tickers append, old rows keep-first."""
    _patch_lane(monkeypatch)
    p = tmp_path / "member_breadth_ledger.parquet"
    d = _today()

    assert mbl.append_member_rows(_rows(d, ["AAPL"], above=True), p) == 1
    second = pd.concat([_rows(d, ["AAPL"], above=False), _rows(d, ["NVDA"])],
                       ignore_index=True)
    assert mbl.append_member_rows(second, p) == 2

    df = pd.read_parquet(p)
    assert sorted(df["ticker"]) == ["AAPL", "NVDA"], \
        "equal-date append must add new tickers without dropping old rows"
    assert bool(df.set_index("ticker").loc["AAPL", "above_200"]) is True, \
        "keep-FIRST violated on the equal-date append"


# ── B11 fence 2 — future ─────────────────────────────────────────────────────

def test_future_date_refused(tmp_path, monkeypatch):
    """A date after today's UTC date never takes a real day's keep-FIRST slot."""
    _patch_lane(monkeypatch)
    monkeypatch.setattr(mbl, "_utc_today", lambda: "2026-01-01")
    p = tmp_path / "member_breadth_ledger.parquet"

    assert mbl.append_member_rows(_rows("2026-01-02", ["AAPL"]), p) == 0
    assert not p.exists(), "future refusal must not create the ledger"

    # today itself is fine
    assert mbl.append_member_rows(_rows("2026-01-01", ["AAPL"]), p) == 1
    assert p.exists()


# ── B11 fence 3 — replay ─────────────────────────────────────────────────────

def test_replay_refused_and_prior_bytes_identical(tmp_path, monkeypatch):
    """A batch older than the newest prior date is refused without rewriting."""
    _patch_lane(monkeypatch)
    monkeypatch.setattr(mbl, "_utc_today", lambda: "2026-06-30")
    p = tmp_path / "member_breadth_ledger.parquet"

    assert mbl.append_member_rows(_rows("2026-06-10", ["AAPL"]), p) == 1
    before = p.read_bytes()

    assert mbl.append_member_rows(_rows("2026-06-03", ["MSFT"]), p) == 0
    assert p.read_bytes() == before, "replay refusal rewrote the ledger"

    # the lane refusal leaves the nightly prior untouched too
    monkeypatch.delenv("COLLECT_LANE", raising=False)
    assert mbl.append_member_rows(_rows("2026-06-10", ["MSFT"]), p) == 0
    assert p.read_bytes() == before, "lane refusal rewrote the ledger"


# ── batch shape ──────────────────────────────────────────────────────────────

def test_multi_date_batch_refused(tmp_path, monkeypatch):
    """A batch carrying two nights has no single PIT slot — refused whole."""
    _patch_lane(monkeypatch)
    monkeypatch.setattr(mbl, "_utc_today", lambda: "2026-06-30")
    p = tmp_path / "member_breadth_ledger.parquet"
    batch = pd.concat([_rows("2026-06-09", ["AAPL"]), _rows("2026-06-10", ["MSFT"])],
                      ignore_index=True)
    assert mbl.append_member_rows(batch, p) == 0
    assert not p.exists()


def test_unparseable_date_refused(tmp_path, monkeypatch):
    _patch_lane(monkeypatch)
    p = tmp_path / "member_breadth_ledger.parquet"
    assert mbl.append_member_rows(_rows("not-a-date", ["AAPL"]), p) == 0
    assert not p.exists()


def test_missing_columns_returns_zero(tmp_path, monkeypatch):
    """A batch lacking a schema column is refused, not partially written."""
    _patch_lane(monkeypatch)
    p = tmp_path / "member_breadth_ledger.parquet"
    bad = _rows(_today(), ["AAPL"]).drop(columns=["above_200"])
    assert mbl.append_member_rows(bad, p) == 0
    assert not p.exists()

    # extra columns are dropped, the six schema columns still land in order
    extra = _rows(_today(), ["AAPL"]).assign(weight=1.5)
    assert mbl.append_member_rows(extra, p) == 1
    df = pd.read_parquet(p)
    assert list(df.columns) == list(mbl.SCHEMA)


def test_empty_and_none_batches_return_zero(tmp_path, monkeypatch):
    _patch_lane(monkeypatch)
    p = tmp_path / "member_breadth_ledger.parquet"
    assert mbl.append_member_rows(pd.DataFrame(columns=list(mbl.SCHEMA)), p) == 0
    assert mbl.append_member_rows(None, p) == 0
    assert not p.exists()


# ── corrupt prior file ───────────────────────────────────────────────────────

def test_corrupt_prior_file_is_left_untouched(tmp_path, monkeypatch):
    """An unreadable prior ledger is never overwritten by one night, never a raise."""
    _patch_lane(monkeypatch)
    p = tmp_path / "member_breadth_ledger.parquet"
    p.write_bytes(b"this is not a parquet file")

    n = mbl.append_member_rows(_rows(_today(), ["AAPL", "MSFT"]), p)
    assert n == 0
    assert p.read_bytes() == b"this is not a parquet file"


# ── default path through lib.config.data_dir() ───────────────────────────────

def test_default_path_resolves_via_data_dir(tmp_path, monkeypatch):
    """path=None lands at data/breadth/member_breadth_ledger.parquet."""
    _patch_lane(monkeypatch)
    import lib.config as config_mod
    monkeypatch.setattr(config_mod, "data_dir", lambda: tmp_path)

    assert mbl.append_member_rows(_rows(_today(), ["AAPL"]), None) == 1
    p = tmp_path / "breadth" / "member_breadth_ledger.parquet"
    assert p.exists()
    assert pd.read_parquet(p)["ticker"].tolist() == ["AAPL"]


def test_offlane_default_path_resolves_nothing(tmp_path, monkeypatch):
    """The lane fence fires before the data dir is ever touched (a broken
    config cannot make an off-lane run write)."""
    _patch_lane(monkeypatch, on=False)

    def _boom():
        raise RuntimeError("data_dir must not be resolved off-lane")

    import lib.config as config_mod
    monkeypatch.setattr(config_mod, "data_dir", _boom)
    assert mbl.append_member_rows(_rows(_today(), ["AAPL"]), None) == 0

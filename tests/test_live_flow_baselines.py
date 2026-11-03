"""tests/test_live_flow_baselines.py — behaviour tests for the display-tier builder.

Exercises the ACTUAL scripts.build_live_flow_baselines functions against
isolated fake data: the resolver/loader layer (engine.thetadata_store) and
lib.config.data_dir are monkeypatched at their real seams — the builder
implementation itself is never copied or stubbed.

Covered (EOD252 baseline-binding repair):
  1. canonical licensed store vs absent checkout-local store
  2. missing-store refusal leaves an existing artifact untouched
  3. dry-run writes nothing
  4. latest-252 window over >252 unsorted observations
  5. MIN_SESSIONS boundary (120 pass / 119 skip) + retained existing entries
  6. one canonical binding per run (no per-root re-resolve)
  7. source-window metadata: source_session_start/end report the actual
     selected window (distinct from the computed_asof build date) in results,
     dry-run returns, retained/merged artifacts and the per-root log
"""
from __future__ import annotations

import json
import logging
import random
import sys
import types
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import engine.thetadata_store as ets
import scripts.build_live_flow_baselines as bl


def test_configured_universe_uses_consumer_resolver(sb, monkeypatch):
    sb.prebind()
    cfg = {"etf_anchors": ["SOXX"], "top_names": 1}
    seen = []
    monkeypatch.setitem(sys.modules, "scripts.live_flow_poller", types.SimpleNamespace(
        _cfg=lambda: cfg, _resolve_universe=lambda c: seen.append(c) or ["SOXX", "XLC"]))
    calls = []
    monkeypatch.setattr(bl, "run", lambda roots, **kw: calls.append((roots, kw)))
    with pytest.raises(_HardExit) as ex:
        bl.main(["--poll-universe", "--dry-run"])
    assert ex.value.code == 0
    assert seen == [cfg]
    assert calls[0][0] == ["SOXX", "XLC"]


@pytest.mark.parametrize("kind", ["missing", "stale", "future", "constant", "nonfinite"])
def test_strict_maintenance_preserves_old_bytes_on_any_unready_root(sb, monkeypatch, kind):
    sb.prebind()
    old = sb.write_existing_artifact({"SPY": {"mean": 1}, "QQQ": {"mean": 9}})
    good = {"mean": 100, "std": 20, "n_obs": 252, "source_session_end": "2026-10-16"}
    bad = dict(good)
    if kind == "missing": bad = None
    elif kind == "stale": bad["source_session_end"] = "2026-10-15"
    elif kind == "future": bad["source_session_end"] = "2026-10-19"
    elif kind == "constant": bad["std"] = 0
    else: bad["mean"] = float("nan")
    monkeypatch.setattr(bl, "compute_baseline", lambda root, **kw: good if root == "SPY" else bad)
    with pytest.raises(RuntimeError, match="QQQ"):
        bl.run(["SPY", "QQQ"], require_source_session=date(2026, 10, 16))
    assert sb.out_path().read_text() == old
    assert list(sb.out_path().parent.iterdir()) == [sb.out_path()]


def test_strict_complete_build_reaches_consumer_output_atomically(sb, monkeypatch):
    sb.prebind()
    sb.write_existing_artifact({"NO_LONGER_POLLED": {"mean": 42}})
    value = {"mean": 100, "std": 20, "n_obs": 252, "source_session_end": "2026-10-16"}
    calls = []
    monkeypatch.setattr(bl, "compute_baseline", lambda root, **kw: calls.append(root) or dict(value))
    result = bl.run(["spy", "SPY", "QQQ"], require_source_session=date(2026, 10, 16))
    assert calls == ["SPY", "QQQ"]
    assert sb.read_artifact() == result
    assert set(result) == {"SPY", "QQQ"}
    assert not list(sb.out_path().parent.glob(".baselines-*.tmp"))


def test_expected_store_mismatch_refuses_before_computation_or_output(sb, monkeypatch):
    sb.prebind()
    old = sb.write_existing_artifact({"OLD": {"mean": 7}})
    monkeypatch.setattr(bl, "run", lambda *a, **kw: pytest.fail("must refuse before build"))
    with pytest.raises(_HardExit) as ex:
        bl.main(["--roots", "SPY", "--expected-store", str(sb.store / "different")])
    assert ex.value.code == 1
    assert sb.out_path().read_text() == old


class _HardExit(Exception):
    """Sandbox stand-in for lib.procutil.hard_exit (os._exit is untestable)."""

    def __init__(self, code: int):
        super().__init__(f"hard_exit({code})")
        self.code = code


def _fake_hard_exit(code: int) -> None:
    raise _HardExit(code)


class Sandbox:
    """Isolated world: checkout-local data dir + separate licensed host store."""

    def __init__(self, tmp_path: Path):
        self.checkout_data = tmp_path / "liveflow-ops-wt" / "data"
        self.checkout_data.mkdir(parents=True)
        # M1 reality: the checkout-local thetadata_eod store does NOT exist;
        # the licensed host store lives elsewhere.
        self.store = tmp_path / "theta-ops-wt" / "data" / "thetadata_eod"
        self.resolve_calls = 0
        self.resolve_kwargs: dict | None = None
        self.resolve_result: Path | None = None  # default: nothing resolves
        self.resolve_raises: Exception | None = None
        self.load_calls: list[dict] = []
        self.frames: dict[str, pd.DataFrame] = {}

    # -- data seams ----------------------------------------------------------
    def set_frame(self, root: str, frame: pd.DataFrame) -> None:
        self.frames[root.upper()] = frame

    def seed_store_dirs(self, roots: list[str]) -> None:
        for r in roots:
            (self.store / "eod" / r.upper()).mkdir(parents=True, exist_ok=True)

    def prebind(self) -> None:
        """Make the sandbox resolver hand back the licensed host store."""
        self.resolve_result = self.store

    # -- artifact seams ------------------------------------------------------
    def out_path(self) -> Path:
        return self.checkout_data / "live_flow_baselines" / "baselines.json"

    def write_existing_artifact(self, payload: dict) -> str:
        p = self.out_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(payload, indent=2, sort_keys=True)
        p.write_text(text)
        return text

    def read_artifact(self) -> dict:
        return json.loads(self.out_path().read_text())

    # -- loader seam (data lives ONLY in the licensed store) ------------------
    def fake_load(self, kind, root, years=None, store=None):
        self.load_calls.append(
            {"kind": kind, "root": root, "years": years, "store": store}
        )
        if store != str(self.store):
            return None  # no EOD data outside the licensed host store
        return self.frames.get(str(root).upper())


def _sb(tmp_path, monkeypatch) -> Sandbox:
    sb = Sandbox(tmp_path)
    monkeypatch.setattr(bl.config, "data_dir", lambda: sb.checkout_data)
    monkeypatch.setattr(bl, "hard_exit", _fake_hard_exit)

    def fake_resolve(required: bool = False, purpose: str = "") -> Path | None:
        sb.resolve_calls += 1
        sb.resolve_kwargs = {"required": required, "purpose": purpose}
        if sb.resolve_raises is not None:
            raise sb.resolve_raises
        return sb.resolve_result

    monkeypatch.setattr(ets, "resolve_thetadata_store", fake_resolve)
    monkeypatch.setattr(ets, "_load_parquets", sb.fake_load)
    return sb


@pytest.fixture()
def sb(tmp_path, monkeypatch) -> Sandbox:
    return _sb(tmp_path, monkeypatch)


def _bdates(n: int, end: str = "2025-12-31") -> list[str]:
    return [d.strftime("%Y-%m-%d") for d in pd.bdate_range(end=end, periods=n)]


def gross_frame(dates: list[str], gross: list[float]) -> pd.DataFrame:
    """EOD frame whose per-day gross premium (close*volume*100) equals `gross`."""
    close = 100.0
    return pd.DataFrame(
        {
            "date": dates,
            "close": close,
            "volume": [g / (close * 100.0) for g in gross],
        }
    )


def ramp_gross(n: int, start: float = 1_000_000.0, step: float = 1_000.0) -> list[float]:
    return [start + i * step for i in range(n)]


# ---------------------------------------------------------------------------
# 1. canonical licensed store vs absent checkout-local store
# ---------------------------------------------------------------------------

def test_compute_uses_canonical_store_not_absent_checkout_local(sb):
    sb.prebind()
    sb.set_frame("SPY", gross_frame(_bdates(130), ramp_gross(130)))
    assert not sb.checkout_data.joinpath("thetadata_eod").exists()  # decoy absent

    result = bl.compute_baseline("SPY")

    assert result is not None
    assert result["n_obs"] == 130
    # the builder fed the LOADER the licensed host store, not config.data_dir()
    assert sb.load_calls, "loader must be consulted"
    assert sb.load_calls[0]["store"] == str(sb.store)
    assert Path(sb.load_calls[0]["store"]) != sb.checkout_data / "thetadata_eod"


def test_run_skips_everything_when_only_checkout_local_store_exists(sb, monkeypatch):
    # Resolver never yields the licensed store -> the run must refuse, not
    # silently produce a merge-only artifact as if healthy.
    sb.set_frame("SPY", gross_frame(_bdates(130), ramp_gross(130)))  # unreachable data
    sb.resolve_result = None
    with pytest.raises(RuntimeError, match="refusing"):
        bl.run(["SPY"])
    assert sb.load_calls == []  # no scan/work happened against a refused store


def test_resolver_called_with_required_true_and_purpose(sb):
    sb.prebind()
    sb.set_frame("SPY", gross_frame(_bdates(120), ramp_gross(120)))
    bl.compute_baseline("SPY")
    assert sb.resolve_kwargs == {"required": True, "purpose": "live_flow_baselines"}


# ---------------------------------------------------------------------------
# 2. missing-store refusal leaves an existing artifact untouched
# ---------------------------------------------------------------------------

def test_bind_store_refuses_when_resolver_returns_none(sb):
    assert sb.resolve_result is None
    with pytest.raises(RuntimeError, match="no thetadata store resolved"):
        bl.bind_store()


def test_bind_store_propagates_resolver_refusal(sb):
    sb.resolve_raises = RuntimeError("licensed host store missing")
    with pytest.raises(RuntimeError, match="licensed host store missing"):
        bl.bind_store()


def test_main_missing_store_refusal_preserves_existing_artifact(sb):
    existing = {
        "SPY": {"mean": 4242424.0, "std": 12345.0, "n_obs": 252,
                "computed_asof": "2026-01-01"},
    }
    before = sb.write_existing_artifact(existing)

    # No store resolves (M1 checkout-local reality) -> refusal via hard_exit(1)
    with pytest.raises(_HardExit) as ei:
        bl.main(["--dry-run"])
    assert ei.value.code == 1

    assert sb.resolve_kwargs == {"required": True, "purpose": "live_flow_baselines"}
    assert sb.load_calls == []          # refused BEFORE any store scan / data work
    assert sb.out_path().read_text() == before  # artifact byte-identical


def test_main_all_mode_empty_canonical_store_refusal(sb):
    sb.prebind()  # store resolves, but eod/ has no roots
    sb.write_existing_artifact({"OLD": {"mean": 1.0, "std": 1.0, "n_obs": 252,
                                        "computed_asof": "2026-01-01"}})
    before = sb.out_path().read_text()

    with pytest.raises(_HardExit) as ei:
        bl.main(["--all"])
    assert ei.value.code == 1
    assert sb.out_path().read_text() == before


# ---------------------------------------------------------------------------
# 3. dry-run no-write
# ---------------------------------------------------------------------------

def test_dry_run_writes_nothing(sb):
    sb.prebind()
    sb.write_existing_artifact({"KEEP": {"mean": 7.0, "std": 2.0, "n_obs": 252,
                                         "computed_asof": "2026-01-01"}})
    before = sb.out_path().read_text()
    spy_dates = _bdates(150)
    sb.set_frame("SPY", gross_frame(spy_dates, ramp_gross(150)))

    updated = bl.run(["SPY"], dry_run=True)

    assert "SPY" in updated and "KEEP" in updated      # computed in-memory
    # the dry-run result still carries the source-window metadata
    assert updated["SPY"]["source_session_start"] == spy_dates[0]
    assert updated["SPY"]["source_session_end"] == spy_dates[-1]
    assert sb.out_path().read_text() == before          # file untouched
    assert not sb.out_path().with_suffix(".tmp.json").exists()  # no temp left
    assert not (sb.checkout_data / "live_flow_baselines").is_dir() or (
        sb.out_path().exists()
    )


# ---------------------------------------------------------------------------
# 4. latest-252 window over >252 unsorted observations
# ---------------------------------------------------------------------------

def test_latest_252_window_from_unsorted_observations(sb):
    sb.prebind()
    n = 300
    dates = _bdates(n)
    gross = ramp_gross(n)  # value i encodes chronological position i
    rows = list(zip(dates, gross))
    random.Random(7).shuffle(rows)  # feed deliberately unsorted rows
    sb.set_frame("SPY", gross_frame([d for d, _ in rows], [g for _, g in rows]))

    result = bl.compute_baseline("SPY")

    assert result is not None
    assert result["n_obs"] == 252  # window, not all-history (300)

    window = np.array(gross[-252:], dtype=float)  # latest 252, chronological
    assert result["mean"] == pytest.approx(float(np.mean(window)), rel=1e-12)
    assert result["std"] == pytest.approx(float(np.std(window, ddof=1)), rel=1e-12)

    all_hist = np.array(gross, dtype=float)
    assert result["mean"] != pytest.approx(float(np.mean(all_hist)), rel=1e-4)
    assert result["std"] != pytest.approx(float(np.std(all_hist, ddof=1)), rel=1e-4)

    # the reported source range is the ACTUAL selected (chronological) window,
    # independent of the shuffled row order the data arrived in
    window_dates = dates[-252:]
    assert result["source_session_start"] == window_dates[0]
    assert result["source_session_end"] == window_dates[-1]


def test_window_is_latest_not_first_252(sb):
    sb.prebind()
    n = 260
    gross = ramp_gross(n)  # distinct values make first/last windows differ
    sb.set_frame("QQQ", gross_frame(_bdates(n), gross))

    result = bl.compute_baseline("QQQ")

    assert result is not None
    assert result["n_obs"] == 252
    expected_latest = float(np.mean(np.array(gross[-252:], dtype=float)))
    expected_first = float(np.mean(np.array(gross[:252], dtype=float)))
    assert result["mean"] == pytest.approx(expected_latest, rel=1e-12)
    assert result["mean"] != pytest.approx(expected_first, rel=1e-4)


def test_source_dates_stay_old_despite_current_computed_asof(sb):
    sb.prebind()
    dates = _bdates(252, end="2024-06-28")  # window ended long ago
    sb.set_frame("SPY", gross_frame(dates, ramp_gross(252)))

    result = bl.compute_baseline("SPY")

    assert result is not None
    assert result["computed_asof"] == str(date.today())  # build date: today
    # the source range stays the historical window actually selected —
    # recomputing today does not redate the source data
    assert result["source_session_start"] == dates[0]
    assert result["source_session_end"] == dates[-1]
    assert result["source_session_end"] < result["computed_asof"]


def test_per_root_log_reports_selected_source_range(sb, caplog):
    sb.prebind()
    dates = _bdates(130)
    sb.set_frame("SPY", gross_frame(dates, ramp_gross(130)))

    with caplog.at_level(logging.INFO, logger="scripts.build_live_flow_baselines"):
        bl.compute_baseline("SPY")

    lines = [r.getMessage() for r in caplog.records
             if r.name == "scripts.build_live_flow_baselines"
             and "n_obs=" in r.getMessage()]
    assert lines, "per-root log line missing"
    assert dates[0] in lines[-1] and dates[-1] in lines[-1]


# ---------------------------------------------------------------------------
# 5. MIN_SESSIONS boundary + retained existing entries
# ---------------------------------------------------------------------------

def test_min_sessions_120_passes_119_skips(sb):
    sb.prebind()
    good_dates = _bdates(120)
    sb.set_frame("GOOD", gross_frame(good_dates, ramp_gross(120)))
    sb.set_frame("SHORT", gross_frame(_bdates(119), ramp_gross(119)))

    good = bl.compute_baseline("GOOD")
    assert good is not None
    assert good["n_obs"] == 120
    # a 120-session entry still carries honest source-window metadata
    assert good["source_session_start"] == good_dates[0]
    assert good["source_session_end"] == good_dates[-1]
    assert bl.compute_baseline("SHORT") is None

    updated = bl.run(["GOOD", "SHORT"], dry_run=True)
    assert "GOOD" in updated
    assert "SHORT" not in updated


def test_existing_entries_retained_when_root_skipped(sb):
    sb.prebind()
    old_entry = {"mean": 31337.0, "std": 42.0, "n_obs": 252,
                 "computed_asof": "2026-01-01"}
    sb.write_existing_artifact({"OLDNAME": old_entry})
    spy_dates = _bdates(120)
    sb.set_frame("SPY", gross_frame(spy_dates, ramp_gross(120)))
    # OLDNAME has no data in the store -> skipped this run

    updated = bl.run(["SPY", "OLDNAME"], dry_run=False)

    assert updated["OLDNAME"] == old_entry  # retained verbatim
    # entries this run did NOT compute get no invented metadata
    assert "source_session_start" not in updated["OLDNAME"]
    assert "source_session_end" not in updated["OLDNAME"]
    assert updated["SPY"]["n_obs"] == 120   # fresh entry merged in
    assert updated["SPY"]["source_session_start"] == spy_dates[0]
    assert updated["SPY"]["source_session_end"] == spy_dates[-1]
    on_disk = sb.read_artifact()
    assert on_disk["OLDNAME"] == old_entry
    assert on_disk["SPY"]["n_obs"] == 120
    assert not sb.out_path().with_suffix(".tmp.json").exists()  # atomic rename


# ---------------------------------------------------------------------------
# 6. one canonical binding per run
# ---------------------------------------------------------------------------

def test_store_resolved_once_across_multiple_roots(sb):
    sb.prebind()
    for r in ("AAA", "BBB", "CCC"):
        sb.set_frame(r, gross_frame(_bdates(130), ramp_gross(130)))

    bl.run(["AAA", "BBB", "CCC"], dry_run=True)

    assert sb.resolve_calls == 1  # bound once, no per-root re-resolve
    assert all(call["store"] == str(sb.store) for call in sb.load_calls)
    assert len(sb.load_calls) == 3


def test_all_mode_lists_canonical_store_roots(sb):
    sb.prebind()
    sb.seed_store_dirs(["SPY", "QQQ"])
    sb.set_frame("SPY", gross_frame(_bdates(130), ramp_gross(130)))
    sb.set_frame("QQQ", gross_frame(_bdates(125), ramp_gross(125)))

    roots = bl._all_roots_in_store()
    assert roots == ["QQQ", "SPY"]  # scanned the licensed host store

    updated = bl.run(roots, dry_run=True)
    assert updated["SPY"]["n_obs"] == 130
    assert updated["QQQ"]["n_obs"] == 125
    assert all(call["store"] == str(sb.store) for call in sb.load_calls)


def test_new_invocation_revalidates_store_before_preserving_artifact(sb):
    sb.prebind()
    sb.set_frame("SPY", gross_frame(_bdates(120), ramp_gross(120)))
    bl.run(["SPY"])
    before = sb.out_path().read_bytes()
    sb.resolve_result = None
    with pytest.raises(RuntimeError, match="refusing"):
        bl.run(["SPY"])
    assert sb.out_path().read_bytes() == before


@pytest.mark.parametrize("case", ["valid", "missing_column", "read_error"])
def test_daily_reader_releases_parquet_cache(monkeypatch, tmp_path, case):
    ets.clear_parquet_cache()
    frame = pd.DataFrame({
        "date": pd.date_range("2025-01-01", periods=120),
        "close": [1.0] * 120,
        "volume": [10] * 120,
    })
    if case == "missing_column":
        frame = frame.drop(columns="close")

    def load(*args, **kwargs):
        ets._PARQUET_CACHE[str(tmp_path / "2025.parquet")] = frame
        if case == "read_error":
            raise OSError("isolated read failure after retaining a frame")
        return frame.copy()

    monkeypatch.setattr(ets, "_load_parquets", load)
    monkeypatch.setattr(bl, "_store_root", lambda: tmp_path)
    try:
        result = bl._daily_gross_premium("SPY")
        if case == "valid":
            assert len(result) == 120
        else:
            assert result is None
        assert not ets._PARQUET_CACHE, "per-root frames leaked past the read"
    finally:
        ets.clear_parquet_cache()

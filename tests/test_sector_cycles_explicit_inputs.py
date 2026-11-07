"""Focused tests for the EXPLICIT-INPUT boundary of engine/sector_cycles.py.

The US sector-cycle calculation is split into an acquisition layer
(`acquire_inputs`) and a pure calculation layer (`compute_from_inputs`), with
`compute()` kept as the compatibility adapter that acquires once and delegates.

What these tests prove:

  1. the payload is IDENTICAL for the pre-extraction computation, the adapter
     and the explicit core (the actual base module is frozen byte-for-byte and hash checked);
  2. the explicit core touches NONE of the legacy acquisition readers — no
     panel reader, no membership loader, no deep-member-store reader, no
     retained-forward-log reader — and reads no config, no file, no network and
     no wall clock on behalf of the sector-cycles module;
  3. field bindings are frozen and supplied values are not mutated by calculation;
  4. a supplied empty / None input is EXPLICIT ABSENCE: it never triggers a
     fallback loader, and the published payload says so;
  5. the published payload never aliases a mutable input payload.
"""
from __future__ import annotations

import builtins
import dataclasses
import json
import pathlib
import socket
import sys

import numpy as np
import pandas as pd
import pytest

from engine import sector_cycles as sc


ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent


# ── deterministic fixture ────────────────────────────────────────────────────

_PANEL_TICKERS = ("SPY", "XLK", "XLF", "XLE", "QQQ", "IWM")


def _panel(n: int = 420) -> pd.DataFrame:
    """A deterministic TR close panel: the RS benchmark, three sector ETFs and
    the two index-family benchmarks."""
    idx = pd.bdate_range("2024-06-03", periods=n)
    cols = {}
    for i, tk in enumerate(_PANEL_TICKERS):
        t = np.arange(n, dtype=float)
        wave = (0.22 * np.sin(t / 17.0 + 0.7 * i)
                + 0.10 * np.sin(t / 43.0 + 0.3 * i))
        cols[tk] = (60.0 + 7.0 * i
                    + 100.0 * (wave + 0.00035 * t)
                    + 0.35 * np.cos(t / 5.0 + i))
    return pd.DataFrame(cols, index=idx)


def _member_index(idx: pd.Index) -> pd.Series:
    """A deterministic equal-weight member-index close series."""
    t = np.arange(len(idx), dtype=float)
    return pd.Series(50.0 + 30.0 * np.sin(t / 13.0 + 0.4) + 0.02 * t, index=idx)


@pytest.fixture
def wired(monkeypatch):
    """Wire every external dependency to a deterministic source."""
    panel = _panel()
    members = [{"ticker": f"M{i}", "weight": 1.0} for i in range(4)]

    monkeypatch.setattr(sc, "yahoo_closes", lambda basis=None: panel.copy())
    monkeypatch.setattr(
        sc.config, "load",
        lambda: {"engine": {"rs_ranking": {"benchmark": "SPY"}}},
    )
    monkeypatch.setattr(sc, "_load_baskets", lambda: {
        "semis": {"name": "Semis", "name_zh": "半导体",
                  "members": members, "category": "Thematic",
                  "etf_proxy": "SMH", "theme": "semis"},
    })
    monkeypatch.setattr(sc, "_load_amalgams", lambda ns: (
        {"ai-power": {"name": "AI Power", "members": members}}
        if ns == "nasdaq" else {}))
    monkeypatch.setattr(sc.basket_index, "deep_calendar",
                        lambda members, min_start=None: panel.index)

    def _candle(members, idx, mode="equal", pit=False):
        return (pd.DataFrame({"close": _member_index(idx)}, index=idx),
                {"coverage_pct": 96.5, "n_live": 4, "n_stale_tail": 1})

    monkeypatch.setattr(sc.basket_index, "consolidated_candle", _candle)
    monkeypatch.setattr(sc.basket_index, "_load_member_ohlcv", lambda ticker: None)
    monkeypatch.setattr(sc.cycle_phase_age, "load_phase_history",
                        lambda engine="sector_cycles": (None, "absent"))
    # Deterministic, valid calibration documents; never depend on local data mounts.
    from engine import hazard_score as hs
    coefficient = {"w": {}, "b": -2.0, "mu": {}, "sd": {}}
    model = {
        "config": {"design": list(hs._DESIGN)}, "turn_def_version": hs._EPOCH,
        "coefficients": {"up": coefficient, "down": coefficient},
        "ledger": {direction: {h: {"verdict": "PASS"} for h in ("1m", "3m", "6m")}
                   for direction in ("up", "down")},
        "calibration": {},
    }
    km = {"pooled": {direction: {"km_by_month": [
        {"age_m": 1, "survival": .9}, {"age_m": 3, "survival": .8},
        {"age_m": 6, "survival": .7}]} for direction in ("up", "down")}}
    monkeypatch.setattr(hs, "_load_model", lambda: model)
    monkeypatch.setattr(hs, "_load_km", lambda: km)
    return {"panel": panel, "members": members}


# Actual pinned pre-extraction source, not a reimplementation of its body.
def _legacy_compute(asof: str | None = None) -> dict | None:
    """Run the actual pinned base source against the same controlled acquisitions."""
    import hashlib
    import importlib.util
    path = ROOT / "tests/fixtures/base_sector_cycles_86e8.py"
    raw = path.read_bytes()
    assert hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == \
        "0ee680d46574723cd9bff07fff777b8005529186"
    name = "frozen_sector_cycles_86e8"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    module.yahoo_closes = sc.yahoo_closes
    module._load_baskets = sc._load_baskets
    module._load_amalgams = sc._load_amalgams
    return module.compute(asof=asof)


def _canonical(payload) -> str:
    return json.dumps(payload, sort_keys=True, default=str)


# ── 1. the payload is identical across the three paths ──────────────────────

def test_legacy_adapter_and_explicit_core_publish_the_same_payload(wired):
    legacy = _legacy_compute()
    adapter = sc.compute()
    inputs = sc.acquire_inputs()
    core = sc.compute_from_inputs(inputs)

    assert legacy is not None and adapter is not None and core is not None
    # the fixture actually exercises the whole payload surface
    assert adapter["meta"]["n_sectors"] >= 3
    assert adapter["meta"]["n_baskets"] == 1
    assert adapter["meta"]["families"], "the amalgamation family must be built"
    assert adapter["sectors"][0]["turns"], "the sector record carries turns"

    assert _canonical(adapter) == _canonical(legacy)
    assert _canonical(core) == _canonical(legacy)
    assert adapter == core


def test_the_explicit_evaluation_clock_is_honoured_identically(wired, monkeypatch):
    # a clock that still leaves every sector above the 300-row floor
    asof = str(wired["panel"].index[330].date())
    # A valid historical capture has member observations bounded to this same date.
    monkeypatch.setattr(sc.basket_index, "deep_calendar",
                        lambda members, min_start=None: wired["panel"].index[:331])
    legacy = _legacy_compute(asof=asof)
    adapter = sc.compute(asof=asof)
    core = sc.compute_from_inputs(sc.acquire_inputs(asof), asof=asof)

    assert legacy is not None and adapter is not None and core is not None
    assert adapter["meta"]["asOf"] == asof
    assert core["meta"]["asOf"] == asof
    assert _canonical(adapter) == _canonical(legacy)
    assert _canonical(core) == _canonical(legacy)


# ── 2. the explicit core touches no legacy reader ───────────────────────────

# Retained module-local traps cover the first extraction. The whole-chain test
# below additionally refuses shared-kernel files, settings, clocks and providers
# after capture, including when ambient caches have been replaced.
_MODULE = "engine/sector_cycles.py"


def _caller_file(depth: int = 2) -> str:
    try:
        return (sys._getframe(depth).f_globals.get("__file__") or "").replace("\\", "/")
    except ValueError:                                   # pragma: no cover
        return ""


def _guard_module_reads(real, what: str):
    """Wrap a reader so a call made FROM engine/sector_cycles.py raises."""
    def guarded(*args, **kwargs):
        if _caller_file(2).endswith(_MODULE):
            raise AssertionError(f"the pure core must not {what}")
        return real(*args, **kwargs)
    return guarded


def _arm_legacy_reader_traps(monkeypatch) -> list:
    """Trap every reader the pre-extraction compute() acquired its inputs with.

    Returns the list that records every file the guarded code opens, so a test
    can assert that no calibration artifact was read.
    """
    opened: list = []
    def boom(*args, **kwargs):
        raise AssertionError("the pure core must not acquire an input")

    monkeypatch.setattr(sc, "yahoo_closes", boom)
    monkeypatch.setattr(sc, "_load_baskets", boom)
    monkeypatch.setattr(sc, "_load_amalgams", boom)
    monkeypatch.setattr(sc.basket_index, "deep_calendar", boom)
    monkeypatch.setattr(sc.basket_index, "consolidated_candle", boom)
    monkeypatch.setattr(sc.basket_index, "_load_member_ohlcv", boom)
    monkeypatch.setattr(sc.cycle_phase_age, "load_phase_history", boom)

    # CONFIG: the sector-cycles module must read no config of its own.
    monkeypatch.setattr(sc.config, "load",
                        _guard_module_reads(sc.config.load, "read config"))

    # FILESYSTEM: the sector-cycles module must open no file of its own.
    real_open = builtins.open

    def guarded_open(file, *args, **kwargs):
        opened.append(str(file))
        if _caller_file(2).endswith(_MODULE):
            raise AssertionError("the pure core must not open a file")
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded_open)
    monkeypatch.setattr(pathlib.Path, "read_text",
                        _guard_module_reads(pathlib.Path.read_text, "read a file"))
    monkeypatch.setattr(pd, "read_parquet",
                        _guard_module_reads(pd.read_parquet, "read a file"))

    # NETWORK
    def net_boom(*args, **kwargs):
        raise AssertionError("the pure core must not touch the network")

    monkeypatch.setattr(socket, "create_connection", net_boom)
    monkeypatch.setattr(socket.socket, "connect", net_boom, raising=False)
    return opened


_CLOCK_NAMES = {"now", "utcnow", "today", "time", "time_ns", "monotonic",
                "perf_counter", "localtime", "gmtime"}
_CLOCK_MODULES = ("engine.", "lib.", "pandas.", "numpy.")


def _clock_trap(frame, event, arg):
    """Raise if the CALCULATION CHAIN reads the wall clock.

    `datetime.datetime` is an immutable stdlib type, so it cannot be
    monkeypatched; a profile hook can.  A clock read from the C library (the
    usual case: `time.time()`, `datetime.datetime.now()`) arrives as a
    'c_call' event whose `arg` is the C callable itself; a Python-level clock
    read arrives as a 'call' event whose code object names it.  The hook fires
    only for a read made FROM the calculation chain, so the test harness' own
    timing and the logging module's record timestamp are not mistaken for a
    calculation read.
    """
    if event == "c_call":
        name = getattr(arg, "__name__", "")
    elif event == "call":
        name = frame.f_code.co_name
    else:
        return
    if name not in _CLOCK_NAMES:
        return
    mod = frame.f_globals.get("__name__", "") or ""
    if mod.startswith(_CLOCK_MODULES):
        raise AssertionError(
            f"the pure core read the wall clock: {mod}.{name}")


def test_explicit_core_reads_no_legacy_reader(wired, monkeypatch):
    inputs = sc.acquire_inputs()
    assert inputs is not None
    # The frozen hazard calibration is resolved by the ACQUISITION layer, so the
    # calculation scores from a resolved calibration and reads no artifact.  The
    # artifact must be PRESENT for that claim to be a proof — without it the
    # scorer could not read it anyway.
    if not sc._warm_hazard_calibration():
        pytest.skip("the frozen hazard calibration artifact is absent here")

    opened = _arm_legacy_reader_traps(monkeypatch)

    sys.setprofile(_clock_trap)
    try:
        payload = sc.compute_from_inputs(inputs)
    finally:
        sys.setprofile(None)

    assert payload is not None
    assert payload["meta"]["n_sectors"] >= 3
    assert payload["meta"]["n_baskets"] == 1
    assert payload["meta"]["families"]
    # the scorer really ran (from the resolved calibration) and read nothing
    assert payload["sectors"][0]["now"].get("hazard") is not None
    assert not [f for f in opened if "hazard" in f], opened


def test_neither_the_module_nor_its_kernel_chain_reads_a_wall_clock():
    """Source pin: the calculation chain carries no wall-clock read at all."""
    for rel in ("engine/sector_cycles.py", "engine/cycles.py",
                "engine/cycle_ontology.py", "engine/cycle_rhythm.py",
                "engine/basket_index.py", "engine/hazard_score.py",
                "engine/hazard_parity.py", "engine/cycle_phase_age.py",
                "engine/vol_regime.py", "engine/inputs.py"):
        src = (ROOT / rel).read_text(encoding="utf-8")
        for token in ("datetime.now(", "Timestamp.now(", "date.today(",
                      "utcnow(", "time.time(", "time.monotonic("):
            assert token not in src, f"{rel} reads the wall clock: {token}"


def test_the_acquisition_layer_is_what_reads_the_world(wired, monkeypatch):
    """The adapter reads; the core does not.

    With every reader trapped the ADAPTER cannot produce a payload — it takes
    the legacy refusal (None) instead of a half-built one — while the CORE
    still produces the complete payload from the bundle it was handed.
    """
    inputs = sc.acquire_inputs()
    assert inputs is not None

    _arm_legacy_reader_traps(monkeypatch)

    assert sc.acquire_inputs() is None, "the adapter must refuse without its readers"

    payload = sc.compute_from_inputs(inputs)
    assert payload is not None
    assert payload["meta"]["n_sectors"] >= 3
    assert payload["meta"]["n_baskets"] == 1
    assert payload["meta"]["families"]


# ── 3. the bundle is frozen and is not mutated ──────────────────────────────

def test_the_input_bundle_is_frozen(wired):
    inputs = sc.acquire_inputs()
    with pytest.raises(dataclasses.FrozenInstanceError):
        inputs.benchmark = "QQQ"


def test_a_calculation_does_not_mutate_its_inputs(wired):
    inputs = sc.acquire_inputs()
    before_panel = inputs.closes_tr.copy(deep=True)
    before_px = (inputs.closes_px.copy(deep=True)
                 if inputs.closes_px is not None else None)
    before_specs = {k: dict(v) for k, v in inputs.basket_specs.items()}
    before_candles = {k: (None if v is None else v.close.copy(deep=True))
                      for k, v in inputs.basket_candles.items()}
    before_history = (None if inputs.phase_history is None
                      else inputs.phase_history.copy(deep=True))
    before_amalgam = {ns: {k: (None if v is None else v.close.copy(deep=True))
                            for k, v in src.candles.items()}
                      for ns, src in inputs.amalgams.items()}
    before_parity = (None if inputs.live_hazard_parity is None
                     else json.dumps(inputs.live_hazard_parity, sort_keys=True,
                                    default=str))

    payload = sc.compute_from_inputs(inputs)
    assert payload is not None

    pd.testing.assert_frame_equal(inputs.closes_tr, before_panel)
    if before_px is not None:
        pd.testing.assert_frame_equal(inputs.closes_px, before_px)
    assert {k: dict(v) for k, v in inputs.basket_specs.items()} == before_specs
    for key, series in before_candles.items():
        got = inputs.basket_candles[key]
        if series is None:
            assert got is None
        else:
            pd.testing.assert_series_equal(got.close, series)
    if before_history is None:
        assert inputs.phase_history is None
    else:
        pd.testing.assert_frame_equal(inputs.phase_history, before_history)
    for ns, before in before_amalgam.items():
        for key, series in before.items():
            got = inputs.amalgams[ns].candles[key]
            if series is None:
                assert got is None
            else:
                pd.testing.assert_series_equal(got.close, series)
    if before_parity is None:
        assert inputs.live_hazard_parity is None
    else:
        assert json.dumps(inputs.live_hazard_parity, sort_keys=True,
                          default=str) == before_parity


def test_the_bundle_does_not_carry_the_live_parity_global(wired):
    """The frozen bundle must not hand out the module constant by reference."""
    from engine import hazard_parity as hp
    inputs = sc.acquire_inputs()
    assert inputs.live_hazard_parity is not None
    assert inputs.live_hazard_parity is not hp.LIVE_HAZARD_PARITY
    inputs.live_hazard_parity["verdict"] = "MUTATED-BY-CONSUMER"
    assert hp.LIVE_HAZARD_PARITY["verdict"] != "MUTATED-BY-CONSUMER"


def test_an_absent_hazard_calibration_is_explicit_absence(wired, monkeypatch):
    """A bundle with NO hazard calibration must read no calibration and stamp no
    hazard — an absent input never falls back to a loader."""
    inputs = sc.acquire_inputs()
    assert inputs.hazard_calibration is not None

    absent = dataclasses.replace(inputs, hazard_calibration=None)

    opened = []
    real_open = builtins.open

    def spy_open(file, *args, **kwargs):
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", spy_open)
    payload = sc.compute_from_inputs(absent)

    assert payload is not None
    assert not [f for f in opened if "hazard" in f], opened
    for rec in payload["sectors"]:
        assert "hazard" not in rec["now"]


def test_the_bundle_carries_its_own_evaluation_clock(wired, monkeypatch):
    """A bundle acquired under a clock keeps that clock: the core cannot be
    handed a bundle and a different clock by accident."""
    asof = str(wired["panel"].index[330].date())
    # A valid historical capture has member observations bounded to this same date.
    monkeypatch.setattr(sc.basket_index, "deep_calendar",
                        lambda members, min_start=None: wired["panel"].index[:331])
    legacy = _legacy_compute(asof=asof)
    inputs = sc.acquire_inputs(asof)
    assert inputs.asof == asof
    # no explicit asof -> the bundle's own clock applies
    core = sc.compute_from_inputs(inputs)
    assert core is not None
    assert core["meta"]["asOf"] == asof
    assert _canonical(core) == _canonical(legacy)
    # an omitted override still uses the captured clock
    other = sc.compute_from_inputs(inputs, asof=None)
    assert other["meta"]["asOf"] == asof


# ── 4. explicit absence never falls back to a loader ────────────────────────

def test_a_missing_basket_candle_is_explicit_absence(wired, monkeypatch):
    inputs = sc.acquire_inputs()
    assert inputs.basket_candles["semis"] is not None

    # the basket's candle is unavailable -> the basket is simply absent
    absent = dataclasses.replace(inputs, basket_candles={"semis": None})
    _arm_legacy_reader_traps(monkeypatch)
    payload = sc.compute_from_inputs(absent)
    assert payload is not None
    assert payload["meta"]["n_baskets"] == 0
    assert payload["baskets"] == []


def test_a_missing_amalgam_family_is_explicit_absence(wired, monkeypatch):
    inputs = sc.acquire_inputs()
    assert "nasdaq" in inputs.amalgams

    absent = dataclasses.replace(inputs, amalgams={})
    _arm_legacy_reader_traps(monkeypatch)
    payload = sc.compute_from_inputs(absent)
    assert payload is not None
    assert payload["meta"]["families"] == []
    assert "nasdaq" not in payload


def test_a_missing_price_panel_degrades_to_the_labelled_tr_basis(wired, monkeypatch):
    inputs = sc.acquire_inputs()
    assert inputs.closes_px is not None
    tr_only = dataclasses.replace(inputs, closes_px=None)
    _arm_legacy_reader_traps(monkeypatch)
    payload = sc.compute_from_inputs(tr_only)
    assert payload is not None
    assert {rec["basis"] for rec in payload["sectors"]} == {"tr"}


def test_an_absent_forward_log_reads_as_source_unavailable(wired):
    inputs = sc.acquire_inputs()
    assert inputs.phase_history is None
    assert inputs.phase_history_status == "absent"
    payload = sc.compute_from_inputs(inputs)
    assert payload is not None
    for rec in payload["sectors"]:
        assert rec["now"]["phase_v2_age_status"] == "source_unavailable"


def test_the_core_refuses_without_a_benchmark_observation(wired):
    panel = wired["panel"].copy()
    panel["SPY"] = np.nan
    inputs = sc.acquire_inputs()
    assert inputs is not None
    blind = dataclasses.replace(inputs, closes_tr=panel, closes_px=panel)
    assert sc.compute_from_inputs(blind) is None


def test_an_empty_panel_produces_no_payload(wired):
    inputs = sc.acquire_inputs()
    empty = dataclasses.replace(inputs, closes_tr=pd.DataFrame())
    assert sc.compute_from_inputs(empty) is None


# ── 5. the payload never aliases a mutable input payload ────────────────────

def test_two_calculations_from_one_bundle_do_not_share_mutable_state(wired):
    inputs = sc.acquire_inputs()
    first = sc.compute_from_inputs(inputs)
    second = sc.compute_from_inputs(inputs)
    assert _canonical(first) == _canonical(second)

    parity = first["meta"]["live_hazard_parity"]
    parity_2 = second["meta"]["live_hazard_parity"]
    assert parity is not None and parity_2 is not None
    assert parity is not parity_2, "the parity report must be copied per payload"

    parity["verdict"] = "MUTATED"
    assert second["meta"]["live_hazard_parity"]["verdict"] != "MUTATED"
    assert inputs.live_hazard_parity["verdict"] != "MUTATED"


def test_the_bundle_survives_repeated_use(wired):
    inputs = sc.acquire_inputs()
    payloads = [sc.compute_from_inputs(inputs) for _ in range(3)]
    assert all(_canonical(p) == _canonical(payloads[0]) for p in payloads)


# Parent regressions for the complete runtime input boundary.
def test_conflicting_evaluation_clock_is_refused_before_calculation(wired, monkeypatch):
    inputs = sc.acquire_inputs()
    invoked = []
    monkeypatch.setattr(sc, "build_sector", lambda *a, **k: invoked.append(True))
    other = (wired["panel"].index[-1] + pd.Timedelta(days=1)).date().isoformat()
    with pytest.raises(ValueError, match="evaluation clock"):
        sc.compute_from_inputs(inputs, asof=other)
    assert invoked == []


def test_future_member_candle_is_refused_before_calculation(wired, monkeypatch):
    inputs = sc.acquire_inputs()
    candle = inputs.basket_candles["semis"]
    future = candle.close.copy()
    future.loc[future.index[-1] + pd.Timedelta(days=1)] = 9999.0
    bad = dataclasses.replace(inputs, basket_candles={
        "semis": dataclasses.replace(candle, close=future)})
    invoked = []
    monkeypatch.setattr(sc, "build_sector", lambda *a, **k: invoked.append(True))
    with pytest.raises(ValueError, match="member candle"):
        sc.compute_from_inputs(bad)
    assert invoked == []


def test_future_family_benchmark_is_refused(wired):
    inputs = sc.acquire_inputs()
    source = inputs.amalgams["nasdaq"]
    future = source.bench_close.copy()
    future.loc[future.index[-1] + pd.Timedelta(days=1)] = 9999.0
    bad = dataclasses.replace(inputs, amalgams={"nasdaq":
        dataclasses.replace(source, bench_close=future)})
    with pytest.raises(ValueError, match="family benchmark"):
        sc.compute_from_inputs(bad)


def test_malformed_optional_basket_preserves_actual_base_failure_isolation(wired, monkeypatch):
    specs = sc._load_baskets()
    specs["malformed"] = None
    monkeypatch.setattr(sc, "_load_baskets", lambda: specs)
    actual_base = _legacy_compute()
    adapter = sc.compute()
    explicit = sc.compute_from_inputs(sc.acquire_inputs())
    assert adapter["meta"]["n_baskets"] == 1
    assert _canonical(adapter) == _canonical(actual_base) == _canonical(explicit)


def test_malformed_family_preserves_other_family_and_actual_base(wired, monkeypatch):
    def families(ns):
        return ({"malformed": None} if ns == "nasdaq" else {
            "healthy": {"name": "Healthy", "members": wired["members"]}})
    monkeypatch.setattr(sc, "_load_amalgams", families)
    actual_base = _legacy_compute()
    adapter = sc.compute()
    assert adapter["meta"]["n_sectors"] >= 3
    assert adapter["meta"]["families"]
    assert all(row["key"] != "nasdaq" for row in adapter["meta"]["families"])
    assert _canonical(adapter) == _canonical(actual_base)


def test_malformed_candle_metadata_keeps_healthy_sectors(wired, monkeypatch):
    idx = wired["panel"].index
    monkeypatch.setattr(sc.basket_index, "consolidated_candle", lambda *a, **k:
                        (pd.DataFrame({"close": _member_index(idx)}, index=idx), object()))
    actual_base = _legacy_compute()
    adapter = sc.compute()
    assert adapter["meta"]["n_sectors"] >= 3
    assert adapter["meta"]["n_baskets"] == 0
    assert _canonical(adapter) == _canonical(actual_base)


def test_entire_cycle_chain_ignores_ambient_caches_and_all_io_after_capture(wired, monkeypatch):
    import datetime
    import os
    import time
    from engine import cycles, session_anchor, hazard_score, vol_regime
    inputs = sc.acquire_inputs()
    expected = _canonical(sc.compute_from_inputs(inputs))
    attempts = []
    def forbidden(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("ambient operation after cycle input capture")
    class NoClock(datetime.date):
        @classmethod
        def today(cls):
            return forbidden()
    with monkeypatch.context() as m:
        m.setattr(cycles, "_FITTED_BANDS", {"equity": {"dc_band": [1, 2]}})
        m.setattr(cycles, "_FITTED_BANDS_LOADED", False)
        m.setattr(cycles, "_RISK_CALIB", {})
        m.setattr(cycles, "_RISK_CALIB_LOADED", False)
        m.setattr(session_anchor, "_REF_CACHE", {})
        m.setattr(session_anchor, "date", NoClock)
        m.setattr(hazard_score, "_model_cache", None)
        m.setattr(hazard_score, "_km_cache", None)
        for owner, name in ((sc.config, "load"), (sc.config, "data_dir"),
                            (cycles, "_load_fitted_bands"), (cycles, "_load_risk_calib"),
                            (session_anchor, "reference_sessions"),
                            (hazard_score, "_load_model"), (hazard_score, "_load_km"),
                            (vol_regime, "load_overlay_gate"),
                            (builtins, "open"), (os, "open"),
                            (pathlib.Path, "read_text"), (pathlib.Path, "read_bytes"),
                            (pd, "read_parquet"), (socket.socket, "connect"),
                            (time, "time"), (time, "monotonic")):
            m.setattr(owner, name, forbidden)
        actual = sc.compute_from_inputs(inputs)
    assert attempts == []
    assert _canonical(actual) == expected


def test_cycle_contexts_restore_after_nested_failure_and_change_real_entry_output(wired):
    from engine import cycles
    inputs = sc.acquire_inputs().calculation_inputs
    a = dataclasses.replace(inputs, entry_gate={**inputs.entry_gate,
        "stoch_overbought": 80, "daily_rsi_extension_cap": 62},
        fitted_bands={"equity": {"dc_band": [36, 42]}},
        risk_calibration={"us_sector": {"FRESH BUY": .8}})
    b = dataclasses.replace(inputs, entry_gate={**inputs.entry_gate,
        "stoch_overbought": 99, "daily_rsi_extension_cap": 99},
        fitted_bands={"equity": {"dc_band": [50, 60]}},
        risk_calibration={"us_sector": {"FRESH BUY": .6}})
    mtf = {"D": {"stoch": 85, "rsi14": 65}}
    with cycles.bind_calculation_inputs(a):
        assert cycles._overextension_legs(mtf, ext_pct=0)
        assert cycles._preset("equity")["dc_band"] == (36, 42)
        assert cycles.risk_size_mult("FRESH BUY", "sector") == .8
        with pytest.raises(RuntimeError):
            with cycles.bind_calculation_inputs(b):
                assert cycles._overextension_legs(mtf, ext_pct=0) == []
                assert cycles._preset("equity")["dc_band"] == (50, 60)
                assert cycles.risk_size_mult("FRESH BUY", "sector") == .6
                raise RuntimeError("injected nested calculation failure")
        assert cycles._overextension_legs(mtf, ext_pct=0)
        assert cycles._preset("equity")["dc_band"] == (36, 42)
    assert not cycles.has_explicit_calculation_inputs()


def test_captured_parity_controls_both_record_claim_and_payload(wired, monkeypatch):
    from engine import hazard_parity
    inputs = dataclasses.replace(sc.acquire_inputs(), live_hazard_parity={
        "verdict": "PARITY_HOLDS", "failing": []})
    monkeypatch.setattr(hazard_parity, "LIVE_HAZARD_PARITY", {
        "verdict": "PARITY_FAILS", "failing": ["changed ambient report"]})
    payload = sc.compute_from_inputs(inputs)
    qualified = [row for row in payload["sectors"] if
                 row["estimate_kinds"]["model_cell_current_claim"] is not None]
    assert qualified
    assert all(row["estimate_kinds"]["model_cell_current_claim"] == "parity_holds"
               for row in qualified)
    assert payload["meta"]["live_hazard_parity"]["verdict"] == "PARITY_HOLDS"


def test_public_cycle_results_do_not_alias_module_taxonomy(wired):
    inputs = sc.acquire_inputs()
    result = sc.compute_from_inputs(inputs)
    expected = _canonical(result)
    result["phases"]["Trough"]["label"] = "consumer mutation"
    result["meta"]["semantic_families"]["schema"] = "consumer mutation"
    assert _canonical(sc.compute_from_inputs(inputs)) == expected
    assert sc.PHASES["Trough"]["label"] == "Trough"


def test_hazard_calibration_is_detached_and_never_reloads(wired, monkeypatch):
    from engine import hazard_score as hs
    model, km = hs._load_model(), hs._load_km()
    captured = hs.HazardCalibration(model, km)
    features = {"age_since_turn_bars": 42, "median_half_yrs": 1,
                "pos": 65, "freq": "D"}
    expected = hs.score_from_calibration(features, "up", calibration=captured)
    model["coefficients"]["up"]["b"] = 1000
    def forbidden():
        raise AssertionError("calibration reloaded")
    monkeypatch.setattr(hs, "_load_model", forbidden)
    monkeypatch.setattr(hs, "_load_km", forbidden)
    assert hs.score_from_calibration(features, "up", calibration=captured) == expected
    assert hs.score_from_calibration(features, "up", calibration=None) is None


def test_explicit_reference_uses_same_absolute_ordinal_algorithm(wired, monkeypatch):
    from engine import session_anchor as sa
    inputs = sc.acquire_inputs().calculation_inputs
    reference = inputs.reference_sessions["US"]
    idx = wired["panel"].index
    expected = sa.session_positions(idx)
    monkeypatch.setattr(sa, "reference_sessions", lambda *a, **k:
                        (_ for _ in ()).throw(AssertionError("ambient reference")))
    assert np.array_equal(sa.session_positions(idx, reference=reference), expected)
    with pytest.raises(ValueError, match="empty"):
        sa.session_positions(idx, reference=pd.DatetimeIndex([]))
    with pytest.raises(ValueError, match="ordered"):
        sa.session_positions(idx, reference=reference[::-1])


@pytest.mark.parametrize("bad_reference", [None, [], pd.DatetimeIndex([])])
def test_invalid_explicit_calendar_is_refused_without_ambient_acquisition(wired, monkeypatch, bad_reference):
    from engine import cycles, session_anchor
    inputs = sc.acquire_inputs().calculation_inputs
    attempted = []
    def forbidden(*a, **k):
        attempted.append(True)
        raise AssertionError("calendar acquisition during explicit admission")
    monkeypatch.setattr(session_anchor, "reference_sessions", forbidden)
    monkeypatch.setattr(session_anchor, "capture_reference_sessions", forbidden)
    with pytest.raises((TypeError, ValueError)):
        dataclasses.replace(inputs, reference_sessions={"US": bad_reference})
    assert attempted == []
    assert not cycles.has_explicit_calculation_inputs()


def test_missing_us_calendar_refuses_before_sector_record_is_skipped(wired, monkeypatch):
    inputs = sc.acquire_inputs()
    captured = dataclasses.replace(inputs.calculation_inputs, reference_sessions={
        "HK": inputs.calculation_inputs.reference_sessions["US"]})
    calls = []
    monkeypatch.setattr(sc, "_compute_captured", lambda *a, **k: calls.append(True))
    with pytest.raises(ValueError, match="US session reference"):
        sc.compute_from_inputs(dataclasses.replace(inputs, calculation_inputs=captured))
    assert calls == []


def test_mutated_contained_calendar_is_revalidated_before_binding(wired, monkeypatch):
    from engine import cycles, session_anchor
    inputs = sc.acquire_inputs()
    inputs.calculation_inputs.reference_sessions["US"] = None
    attempted = []
    def forbidden(*a, **k):
        attempted.append(True)
        raise AssertionError("legacy calendar fallback")
    monkeypatch.setattr(session_anchor, "reference_sessions", forbidden)
    monkeypatch.setattr(sc, "_compute_captured", forbidden)
    with pytest.raises(TypeError, match="DatetimeIndex"):
        sc.compute_from_inputs(inputs)
    assert attempted == []
    assert not cycles.has_explicit_calculation_inputs()


@pytest.mark.parametrize("clock", ["now", "today", "2026-2-01", "2026-02-30"])
def test_relative_or_invalid_dates_refuse_before_capture_or_calculation(wired, monkeypatch, clock):
    from engine import cycles
    inputs = sc.acquire_inputs()
    attempted = []
    def forbidden(*a, **k):
        attempted.append(True)
        raise AssertionError("ambient acquisition during explicit date admission")
    monkeypatch.setattr(sc, "yahoo_closes", forbidden)
    monkeypatch.setattr(sc.config, "load", forbidden)
    monkeypatch.setattr(pd, "Timestamp", forbidden)
    for call in (lambda: sc.compute_from_inputs(inputs, asof=clock),
                 lambda: sc.acquire_inputs(clock),
                 lambda: cycles.acquire_calculation_inputs(evaluation_date=clock),
                 lambda: dataclasses.replace(inputs.calculation_inputs, evaluation_date=clock)):
        with pytest.raises(ValueError):
            call()
    assert attempted == []


@pytest.mark.parametrize("settings", [
    {}, {"stoch_oversold": 20},
    {"stoch_overbought": float("nan")}, {"approach_days": "3"},
    {"approach_days": 3.5}, {"stoch_oversold": True},
])
def test_missing_or_invalid_effective_settings_refuse_at_admission(wired, settings):
    inputs = sc.acquire_inputs().calculation_inputs
    supplied = settings if len(settings) == 0 or settings == {"stoch_oversold": 20} else {
        **inputs.entry_gate, **settings}
    with pytest.raises(ValueError, match="explicit"):
        dataclasses.replace(inputs, entry_gate=supplied)


def test_bound_settings_are_detached_from_mutable_capture(wired):
    from engine import cycles
    inputs = sc.acquire_inputs().calculation_inputs
    original = inputs.entry_gate["stoch_overbought"]
    with cycles.bind_calculation_inputs(inputs):
        inputs.entry_gate["stoch_overbought"] = 0
        assert cycles._entry_value("stoch_overbought", None) == original
    assert not cycles.has_explicit_calculation_inputs()

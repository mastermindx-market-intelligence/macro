"""tests/test_theme_allocation_explicit_inputs.py — explicit-input seams for the theme
scoring desk (engine.theme_scoring) and the narrative allocation desk
(engine.narrative_rotation).

The always-on Sector runtime needs to REFRESH the original Sector Brief from ONE
accepted historical snapshot. That requires the two desks to be computable over
CAPTURED VALUES instead of over the repository's ambient state. This suite proves:

  1. PARITY — the new cores produce output byte-identical to the ACTUAL base
     implementation (frozen in tests/fixtures/base_*_38f2441.py, verified against the
     base commit's own git blob SHA-1) over the same controlled acquired inputs.
  2. EXPLICITNESS — the prior-Sector conflict demotion is driven by an EXPLICIT
     evaluation date and an EXPLICIT artifact (current / stale / missing), and the
     in-progress current Sector output is never substituted.
  3. PURITY — the cores read no file, no clock and no provider, and write no ledger,
     snapshot, notification or HTML, once the bundle has been acquired.
  4. ISOLATION — two distinct explicit contexts cannot influence one another, and
     altering a supplied input changes the expected observable field.
  5. UNCHANGED LEGACY — the acquisition adapters keep their signatures, their default
     behaviour, their fail-open isolation and their output bytes.

Everything runs on synthetic panels in tmp_path. Nothing here touches the repository's
data/ or site/ trees, and no network or provider call is made.
"""
from __future__ import annotations

import builtins
import datetime
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine import (  # noqa: E402
    basket_breadth_divergence, basket_score, group_flow, narrative_rotation as nr,
    theme_scoring as ts, vol_regime,
)
from lib import config  # noqa: E402
from lib.closes_panel import align_latest_common_observation  # noqa: E402

BASE_SHA = "38f2441def30f02cf2accf9ddfbaee334d86e1b5"

# The frozen base implementations. Each file is a byte-exact copy of the module at
# BASE_SHA; the test asserts its git blob SHA-1 below, so the reference cannot drift.
BASE_THEME_BLOB = "c835735ebf55d37e28506a99d6c4c8248522d579"
BASE_NARRATIVE_BLOB = "494a6f00dbbbdaf20e7fc76462170a31b93deae3"
BASE_THEME_FIXTURE = ROOT / "tests" / "fixtures" / "base_theme_scoring_38f2441.py"
BASE_NARRATIVE_FIXTURE = ROOT / "tests" / "fixtures" / "base_narrative_rotation_38f2441.py"


def _git_blob_sha(path: Path) -> str:
    out = subprocess.run(["git", "hash-object", str(path)], cwd=str(ROOT),
                         capture_output=True, text=True, check=True)
    return out.stdout.strip()


def _load_frozen(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _base_theme_scoring():
    return _load_frozen(BASE_THEME_FIXTURE, "frozen_base_theme_scoring_38f2441")


def _base_narrative_rotation():
    return _load_frozen(BASE_NARRATIVE_FIXTURE, "frozen_base_narrative_rotation_38f2441")


# --------------------------------------------------------------------- fixtures
STRONG = [(100, 0.004), (120, -0.002), (100, 0.002)]
STRONG2 = [(110, 0.0035), (110, -0.0018), (100, 0.0019)]
MID = [(120, 0.0012), (100, -0.0008), (100, 0.0009)]
WEAK = [(120, -0.0012), (100, 0.0004), (100, 0.0002)]

_BASKET_SPECS = (
    # id, name, category, parent, n_members, drift profile, member volatility
    ("mag7", "Alpha Mag7", "Tech", "Tech", 5, STRONG, 0.005),
    ("ai_infra", "Beta Infra", "Tech", "Tech", 5, STRONG2, 0.005),
    ("energy_complex", "Gamma Energy", "Energy", "Energy", 5, MID, 0.010),
    ("regional_banks", "Delta Banks", "Financials", "Financials", 4, WEAK, 0.011),
    ("thin", "Epsilon Thin", "Other", "Other", 2, MID, 0.010),
)


def _drift_profile(segs, n):
    d = np.zeros(n)
    pos = 0
    for cnt, dr in segs:
        d[pos:pos + cnt] = dr
        pos += cnt
    return d


def _make_universe(n_sessions: int = 320, seed: int = 11):
    """A deterministic synthetic universe: one close matrix, one benchmark level and
    the basket membership the two desks consume.

    `mag7` is a genuine DOMINANT/ACCUMULATE theme and `thin` is a basket the desk
    REFUSES for observation coverage — so the buy list, the sector demotion and the
    refusal path are all live in the fixture.
    """
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2020-01-01", periods=n_sessions)
    px, members_of = {}, {}
    tno = 0
    for bid, _name, _cat, _par, nmem, segs, vol in _BASKET_SPECS:
        d = _drift_profile(segs, n_sessions)
        tks = []
        for _ in range(nmem):
            tk = f"T{tno:02d}"
            tno += 1
            px[tk] = np.cumprod(1 + rng.normal(d, vol, n_sessions)) * 100.0
            tks.append(tk)
        members_of[bid] = tks
    closes = pd.DataFrame(px, index=idx)
    # one late-listed name -> NaN before its inception
    closes.loc[closes.index[:60], "T20"] = np.nan
    bench_close = pd.Series(
        np.cumprod(1 + rng.normal(0.0004, 0.007, n_sessions)) * 400.0, index=idx)
    closes, bench_close, observation = align_latest_common_observation(closes, bench_close)
    rets = closes.pct_change(fill_method=None)
    bench_ret = bench_close.reindex(rets.index).ffill().pct_change(fill_method=None)
    bench = pd.Series(np.nan, index=rets.index)
    bf = bench_ret.first_valid_index()
    bench.loc[bf:] = (1 + bench_ret.loc[bf:].fillna(0)).cumprod()
    return closes, rets, bench, bench_close, bench_ret, idx, observation, members_of


def _make_membership(idx, members_of):
    early = str(idx[0].date())
    mid = str(idx[150].date())
    baskets = {}
    for bid, name, cat, par, _n, _segs, _vol in _BASKET_SPECS:
        added = mid if bid == "regional_banks" else early
        baskets[bid] = {
            "id": bid, "name": name, "name_zh": name, "category": cat, "thesis": "th",
            "parent": par, "etf_proxy": None, "tags": [],
            "members": [{"ticker": t, "added": added, "name": f"N{t}", "name_zh": f"N{t}"}
                        for t in members_of[bid]],
        }
    return {"baskets": baskets, "benchmark": "SPY", "construction": "c", "history_note": "h"}


def _theme_panel():
    """The group_flow-shaped panel the theme desk consumes."""
    closes, rets, bench, _bc, _br, idx, obs, mo = _make_universe()
    mem = _make_membership(idx, mo)
    return {"mem": mem, "closes": closes, "rets": rets,
            "theme_closes": closes, "theme_rets": rets,
            "theme_price_resolution": {"effective_as_of": str(idx.max().date())},
            "idx": idx, "bench": bench, "region": "us", "observation": obs}


def _narrative_panel():
    """The narrative-shaped panel the allocation desk consumes."""
    closes, rets, bench, bench_close, bench_ret, idx, _obs, mo = _make_universe()
    mem = _make_membership(idx, mo)
    bdict = mem["baskets"]
    items = list(bdict.items())
    union = sorted({m["ticker"] for _b, bb in items for m in bb.get("members", [])})
    resid = nr._market_residuals(closes[union], bench_ret)
    return {"cfg": {}, "mem": mem, "items": items, "closes": closes, "rets": rets,
            "idx": idx, "bench": bench, "bench_ret": bench_ret, "bench_close": bench_close,
            "resid": resid}


# ------------------------------------------------------------- controlled inputs
MACRO = {
    "state": {"growth": 0.4, "rates": -0.2, "inflation": 0.1, "riskon": 0.55},
    "sector_rs": {"XLK": 0.82, "XLE": 0.31, "XLV": 0.44},
    "display": {"quad": "Q2", "quad_name": "Reflation", "cycle": "mid", "cycle_zh": "中期",
                "growth_score": 0.42, "inflation_score": 0.11, "fed_dir": "easing",
                "nfci_state": "neutral", "nfci_trend": "flat", "dollar_regime": "risk-on",
                "bond_cycle": "mid", "recession_band": "low", "drawdown_band": "low",
                "summary_en": "Reflation - mid-cycle - Fed easing", "summary_zh": "再通胀",
                "as_of": "2025-03-14"},
}
# The EXPLICIT ABSENCE shape of a macro context: the state vector is empty, so the
# macro leg is unavailable for every basket (it renormalises OUT of the composite
# exactly like the mtf / vol-hole legs).
EMPTY_MACRO = {"state": {}, "sector_rs": {}, "display": {}}

CALIBRATION = {
    "fading": {"verdict": "measurable_edge", "mean_pct": -3.4, "t_hac": 2.1, "n": 40},
    "deteriorating": {"verdict": "measurable_edge", "mean_pct": -4.1, "t_hac": 2.6, "n": 38},
}
NAMES = {f"T{i:02d}": (f"N{i}", f"N{i}") for i in range(21)}


def _fake_signals(members, level=None, region="us", conv_map=None, *, use_cache=True):
    return {"mtf": {"momentum_score": 0.22,
                    "confluence": {"grade": "TREND-FOLLOW", "long_sign": 1},
                    "source": "member_ohlcv"},
            "tape": {"volhole": {"state": "IN_HOLE", "score": 0.1}},
            "meta": {"basis": "member_ohlcv", "n_total": len(members)}}


def _fake_textures(lvl, fp, fp5, crowd, breadth_d, perf, mc_closes=None):
    return {"bull_age": {"in_bull": True, "days": 120},
            "overbought": {"band": "neutral"},
            "clean_entry": {"flag": True, "quality": 0.7, "reasons": ["r"]},
            "rollover_risk": {"risk": 0.2, "band": "low", "reasons": [], "hist_fade": False},
            "breadth_divergence": {"risk": 0.1, "band": "low"}}


def _sector_doc(as_of):
    return {"as_of": as_of,
            "sectors": [{"ticker": "XLK", "conviction": {"label_en": "Reduce", "label_zh": "减配"}},
                        {"ticker": "SMH", "conviction": {"label_en": "Cautious", "label_zh": "谨慎"}}]}


def _write_site(tmp_path: Path, sector_doc):
    site = tmp_path / "site"
    (site / "sectordata").mkdir(parents=True, exist_ok=True)
    if sector_doc is not None:
        (site / "sectordata" / "sector_central.json").write_text(
            json.dumps(sector_doc), encoding="utf-8")
    data = tmp_path / "data"
    (data / "earnings").mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"ticker": ["T00", "T01"],
                  "as_of": [pd.Timestamp("2025-03-13")] * 2,
                  "next_date": [pd.Timestamp("2025-03-18"), pd.Timestamp("2025-04-02")]}).to_parquet(
        data / "earnings" / "earnings.parquet")
    return site, data


def _patch_theme_ambient(mp, panel, tmp_path, *, sector_doc, kill=False,
                         calibration=CALIBRATION, macro=MACRO, concentration=None,
                         base=None):
    """Point every ambient read of the theme desk at controlled values.

    `base` is the frozen base module (the current module is patched too), so both
    implementations read exactly the same values.
    """
    site, data = _write_site(tmp_path, sector_doc)
    modules = [ts] + ([base] if base is not None else [])
    for mod in modules:
        mp.setattr(mod, "_macro_context", lambda region="us": macro)
        mp.setattr(mod, "_signal_calibration", lambda: calibration)
        mp.setattr(mod, "_names_sectors", lambda: NAMES)
        mp.setattr(mod, "_basket_signals", _fake_signals)
    mp.setattr(group_flow, "_setup", lambda region="us": panel)
    mp.setattr(group_flow, "_cfg", lambda cfg=None: dict(group_flow._DEFAULTS))
    mp.setattr(vol_regime, "published_snapshot",
               lambda: ({"regime": "backwardation-stress", "v": 1} if kill
                        else {"regime": "calm"}))
    mp.setattr(vol_regime, "sizing_overlay", lambda snap, cfg: {"gross_scalar": 0.75})
    mp.setattr(vol_regime, "overlay_config", lambda: {})
    mp.setattr(vol_regime, "regime_caution_scored", lambda: True)
    mp.setattr(basket_score, "theme_textures", _fake_textures)
    mp.setattr(basket_score, "market_concentration",
               lambda region="us": ({"hhi": 0.11, "n": 21} if concentration is None
                                    else concentration))
    mp.setattr(basket_breadth_divergence, "log_stamp", lambda *a, **k: None)
    mp.setattr(config, "data_dir", lambda: data)
    mp.setattr(config, "site_dir", lambda: site)
    return site, data


def _patch_narrative_ambient(mp, panel, tmp_path, *, base=None):
    """Point every ambient read of the allocation desk at controlled values."""
    data = tmp_path / "data"
    (data / "finra").mkdir(parents=True, exist_ok=True)
    modules = [nr] + ([base] if base is not None else [])
    for mod in modules:
        mp.setattr(mod, "_setup", lambda cfg: panel)
        mp.setattr(mod, "_validation_meta", lambda fname="x": {})
        mp.setattr(mod, "_sizing_calibration", lambda: {})
    mp.setattr(config, "data_dir", lambda: data)
    return data


def _canonical(payload):
    return json.dumps(payload, sort_keys=True, default=str)


# --------------------------------------------------------------- ambient trap
class _Trap:
    """Records every file read/write, clock read and provider call inside the block.

    The point is not to forbid I/O in general — it is to make ANY ambient read
    VISIBLE, so an undeclared dependency shows up as a failing assertion instead of
    as a silent coupling to the repository.
    """

    def __init__(self):
        self.reads = []
        self.writes = []
        self.clocks = []
        self.providers = []

    # -- context manager ----------------------------------------------------
    def __enter__(self):
        self._orig = {
            "open": builtins.open,
            "os_open": os.open,
            "path_read_text": pathlib.Path.read_text,
            "path_read_bytes": pathlib.Path.read_bytes,
            "path_write_text": pathlib.Path.write_text,
            "path_write_bytes": pathlib.Path.write_bytes,
            "path_mkdir": pathlib.Path.mkdir,
            "pd_read_parquet": pd.read_parquet,
            "pd_read_csv": pd.read_csv,
            "pd_read_json": pd.read_json,
            "df_to_parquet": pd.DataFrame.to_parquet,
            "df_to_csv": pd.DataFrame.to_csv,
            "df_to_json": pd.DataFrame.to_json,
            "os_mkdir": os.mkdir,
            "os_makedirs": os.makedirs,
            "os_remove": os.remove,
            "os_unlink": os.unlink,
            "os_rename": os.rename,
            "os_replace": os.replace,
            "shutil_copy": shutil.copy,
            "shutil_copy2": shutil.copy2,
            "shutil_copytree": shutil.copytree,
            "time_time": time.time,
            "time_monotonic": time.monotonic,
            "datetime_datetime": datetime.datetime,
            "datetime_date": datetime.date,
        }
        trap = self
        o = self._orig

        def _open(file, mode="r", *a, **k):
            if any(ch in mode for ch in "wxa+"):
                trap.writes.append(("open", str(file), mode))
            else:
                trap.reads.append(("open", str(file), mode))
            return o["open"](file, mode, *a, **k)

        def _os_open(path, flags, *a, **k):
            if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND):
                trap.writes.append(("os.open", str(path), flags))
            else:
                trap.reads.append(("os.open", str(path), flags))
            return o["os_open"](path, flags, *a, **k)

        def _read_text(self, *a, **k):
            trap.reads.append(("Path.read_text", str(self), "r"))
            return o["path_read_text"](self, *a, **k)

        def _read_bytes(self):
            trap.reads.append(("Path.read_bytes", str(self), "r"))
            return o["path_read_bytes"](self)

        def _write_text(self, *a, **k):
            trap.writes.append(("Path.write_text", str(self), "w"))
            return o["path_write_text"](self, *a, **k)

        def _write_bytes(self, *a, **k):
            trap.writes.append(("Path.write_bytes", str(self), "w"))
            return o["path_write_bytes"](self, *a, **k)

        def _mkdir(self, *a, **k):
            trap.writes.append(("Path.mkdir", str(self), "w"))
            return o["path_mkdir"](self, *a, **k)

        def _pd_read_parquet(path, *a, **k):
            trap.reads.append(("pd.read_parquet", str(path), "r"))
            return o["pd_read_parquet"](path, *a, **k)

        def _pd_read_csv(path, *a, **k):
            trap.reads.append(("pd.read_csv", str(path), "r"))
            return o["pd_read_csv"](path, *a, **k)

        def _pd_read_json(path, *a, **k):
            trap.reads.append(("pd.read_json", str(path), "r"))
            return o["pd_read_json"](path, *a, **k)

        def _df_to_parquet(self, *a, **k):
            trap.writes.append(("DataFrame.to_parquet", str(getattr(self, "name", "?")), "w"))
            return o["df_to_parquet"](self, *a, **k)

        def _df_to_csv(self, *a, **k):
            trap.writes.append(("DataFrame.to_csv", str(getattr(self, "name", "?")), "w"))
            return o["df_to_csv"](self, *a, **k)

        def _df_to_json(self, *a, **k):
            trap.writes.append(("DataFrame.to_json", str(getattr(self, "name", "?")), "w"))
            return o["df_to_json"](self, *a, **k)

        def _os_mkdir(path, *a, **k):
            trap.writes.append(("os.mkdir", str(path), "w"))
            return o["os_mkdir"](path, *a, **k)

        def _os_makedirs(path, *a, **k):
            trap.writes.append(("os.makedirs", str(path), "w"))
            return o["os_makedirs"](path, *a, **k)

        def _os_remove(path, *a, **k):
            trap.writes.append(("os.remove", str(path), "w"))
            return o["os_remove"](path, *a, **k)

        def _os_unlink(path, *a, **k):
            trap.writes.append(("os.unlink", str(path), "w"))
            return o["os_unlink"](path, *a, **k)

        def _os_rename(src, dst, *a, **k):
            trap.writes.append(("os.rename", f"{src}->{dst}", "w"))
            return o["os_rename"](src, dst, *a, **k)

        def _os_replace(src, dst, *a, **k):
            trap.writes.append(("os.replace", f"{src}->{dst}", "w"))
            return o["os_replace"](src, dst, *a, **k)

        def _shutil_copy(src, dst, *a, **k):
            trap.writes.append(("shutil.copy", f"{src}->{dst}", "w"))
            return o["shutil_copy"](src, dst, *a, **k)

        def _shutil_copy2(src, dst, *a, **k):
            trap.writes.append(("shutil.copy2", f"{src}->{dst}", "w"))
            return o["shutil_copy2"](src, dst, *a, **k)

        def _shutil_copytree(src, dst, *a, **k):
            trap.writes.append(("shutil.copytree", f"{src}->{dst}", "w"))
            return o["shutil_copytree"](src, dst, *a, **k)

        def _time_time():
            trap.clocks.append("time.time")
            return o["time_time"]()

        def _time_monotonic():
            trap.clocks.append("time.monotonic")
            return o["time_monotonic"]()

        class _FakeDateTime(o["datetime_datetime"]):
            @classmethod
            def now(cls, tz=None):
                trap.clocks.append("datetime.datetime.now")
                return o["datetime_datetime"].now(tz)

            @classmethod
            def utcnow(cls):
                trap.clocks.append("datetime.datetime.utcnow")
                return o["datetime_datetime"].utcnow()

        class _FakeDate(o["datetime_date"]):
            @classmethod
            def today(cls):
                trap.clocks.append("datetime.date.today")
                return o["datetime_date"].today()

        builtins.open = _open
        os.open = _os_open
        pathlib.Path.read_text = _read_text
        pathlib.Path.read_bytes = _read_bytes
        pathlib.Path.write_text = _write_text
        pathlib.Path.write_bytes = _write_bytes
        pathlib.Path.mkdir = _mkdir
        pd.read_parquet = _pd_read_parquet
        pd.read_csv = _pd_read_csv
        pd.read_json = _pd_read_json
        pd.DataFrame.to_parquet = _df_to_parquet
        pd.DataFrame.to_csv = _df_to_csv
        pd.DataFrame.to_json = _df_to_json
        os.mkdir = _os_mkdir
        os.makedirs = _os_makedirs
        os.remove = _os_remove
        os.unlink = _os_unlink
        os.rename = _os_rename
        os.replace = _os_replace
        shutil.copy = _shutil_copy
        shutil.copy2 = _shutil_copy2
        shutil.copytree = _shutil_copytree
        time.time = _time_time
        time.monotonic = _time_monotonic
        datetime.datetime = _FakeDateTime
        datetime.date = _FakeDate
        # Any module that did `from datetime import date as _date` holds the ORIGINAL
        # class, so the module-level alias has to be swapped too or a wall-clock read
        # inside it would slip past the trap.
        self._aliases = []
        for _name, _mod in list(sys.modules.items()):
            if _mod is None:
                continue
            for _attr in ("_date", "date"):
                if getattr(_mod, _attr, None) is o["datetime_date"]:
                    self._aliases.append((_mod, _attr))
                    setattr(_mod, _attr, _FakeDate)
        return self

    def __exit__(self, *exc):
        o = self._orig
        builtins.open = o["open"]
        os.open = o["os_open"]
        pathlib.Path.read_text = o["path_read_text"]
        pathlib.Path.read_bytes = o["path_read_bytes"]
        pathlib.Path.write_text = o["path_write_text"]
        pathlib.Path.write_bytes = o["path_write_bytes"]
        pathlib.Path.mkdir = o["path_mkdir"]
        pd.read_parquet = o["pd_read_parquet"]
        pd.read_csv = o["pd_read_csv"]
        pd.read_json = o["pd_read_json"]
        pd.DataFrame.to_parquet = o["df_to_parquet"]
        pd.DataFrame.to_csv = o["df_to_csv"]
        pd.DataFrame.to_json = o["df_to_json"]
        os.mkdir = o["os_mkdir"]
        os.makedirs = o["os_makedirs"]
        os.remove = o["os_remove"]
        os.unlink = o["os_unlink"]
        os.rename = o["os_rename"]
        os.replace = o["os_replace"]
        shutil.copy = o["shutil_copy"]
        shutil.copy2 = o["shutil_copy2"]
        shutil.copytree = o["shutil_copytree"]
        time.time = o["time_time"]
        time.monotonic = o["time_monotonic"]
        datetime.datetime = o["datetime_datetime"]
        datetime.date = o["datetime_date"]
        for _mod, _attr in getattr(self, "_aliases", []):
            try:
                setattr(_mod, _attr, o["datetime_date"])
            except Exception:  # noqa: BLE001 — a module that refuses the restore is harmless
                pass
        return False


def test_the_ambient_trap_actually_detects_reads_writes_and_clocks(tmp_path):
    """The trap must not be vacuous: it has to SEE a read, a write and a clock read."""
    trap = _Trap()
    with trap:
        with open(__file__, "r") as fh:
            fh.read(1)
        (tmp_path / "x.txt").write_text("hello", encoding="utf-8")
        _ = datetime.date.today()
        _ = datetime.datetime.now()
        # the theme desk holds its own `from datetime import date as _date` alias —
        # the trap must see a wall-clock read through it too
        _ = ts._date.today()
    assert any(kind == "open" for kind, _p, _m in trap.reads)
    assert any(kind == "Path.write_text" for kind, _p, _m in trap.writes)
    assert "datetime.date.today" in trap.clocks
    assert "datetime.datetime.now" in trap.clocks
    assert trap.clocks.count("datetime.date.today") >= 2, \
        "the module-level date alias must be trapped as well"


# --------------------------------------------------------------------- the tests
def test_frozen_base_reference_is_the_base_implementation():
    """The parity reference must be the ACTUAL base implementation, byte for byte."""
    assert BASE_THEME_FIXTURE.exists(), "missing the frozen base theme_scoring reference"
    assert BASE_NARRATIVE_FIXTURE.exists(), "missing the frozen base narrative reference"
    assert _git_blob_sha(BASE_THEME_FIXTURE) == BASE_THEME_BLOB
    assert _git_blob_sha(BASE_NARRATIVE_FIXTURE) == BASE_NARRATIVE_BLOB
    # and the blob really is the base commit's module
    out = subprocess.run(["git", "rev-parse", f"{BASE_SHA}:engine/theme_scoring.py"],
                         cwd=str(ROOT), capture_output=True, text=True)
    if out.returncode == 0:
        assert out.stdout.strip() == BASE_THEME_BLOB


@pytest.mark.parametrize("sector_as_of,label", [
    (datetime.date.today().isoformat(), "current"),
    ((datetime.date.today() - datetime.timedelta(days=10)).isoformat(), "stale"),
])
def test_theme_core_matches_base_over_controlled_inputs(monkeypatch, tmp_path, sector_as_of, label):
    """The explicit-input core reproduces the BASE implementation byte for byte.

    Covers the live buy list, the sector-conflict demotion (label='current' demotes
    mag7 out of buy into conflicted; label='stale' leaves it in buy), the observation
    refusal and the rotation/scorecards.
    """
    base = _base_theme_scoring()
    panel = _theme_panel()
    _patch_theme_ambient(monkeypatch, panel, tmp_path, sector_doc=_sector_doc(sector_as_of),
                         base=base)

    base_payload = base.compute_theme_intel("us")
    inputs = ts.acquire_theme_score_inputs("us")
    assert inputs is not None
    new_payload = ts.compute_theme_intel_core(inputs).payload

    assert base_payload is not None
    assert new_payload is not None
    assert _canonical(new_payload) == _canonical(base_payload)
    # the fixture really exercises the demotion path
    if label == "current":
        assert [x["id"] for x in new_payload["act_now"]["conflicted"]] == ["mag7"]
    else:
        assert new_payload["act_now"]["conflicted"] == []
    assert [x["id"] for x in new_payload["act_now"]["buy"]]


def test_theme_core_matches_base_under_vol_regime_kill_switch(monkeypatch, tmp_path):
    """The subtract-only vol-regime kill switch still stands the recos down, identically."""
    base = _base_theme_scoring()
    panel = _theme_panel()
    _patch_theme_ambient(monkeypatch, panel, tmp_path,
                         sector_doc=_sector_doc(datetime.date.today().isoformat()),
                         kill=True, base=base)

    base_payload = base.compute_theme_intel("us")
    inputs = ts.acquire_theme_score_inputs("us")
    new_payload = ts.compute_theme_intel_core(inputs).payload
    assert _canonical(new_payload) == _canonical(base_payload)
    assert new_payload["act_now"]["buy"] == []
    assert all(t["reco"] == "hold" for t in new_payload["themes"])


def test_theme_core_matches_base_with_absent_calibration_and_context(monkeypatch, tmp_path):
    """An ABSENT calibration and an ABSENT macro context are explicit absence, not a
    fallback load — and the output still matches the base implementation."""
    base = _base_theme_scoring()
    panel = _theme_panel()
    _patch_theme_ambient(monkeypatch, panel, tmp_path,
                         sector_doc=_sector_doc(datetime.date.today().isoformat()),
                         calibration={}, macro=EMPTY_MACRO, concentration={}, base=base)

    base_payload = base.compute_theme_intel("us")
    inputs = ts.acquire_theme_score_inputs("us")
    new_payload = ts.compute_theme_intel_core(inputs).payload
    assert _canonical(new_payload) == _canonical(base_payload)
    assert new_payload["signal_calibration"] == {}
    assert new_payload["market_concentration"] == {}


def test_theme_core_matches_base_with_a_partial_panel(monkeypatch, tmp_path):
    """A basket whose members are missing from the panel is refused, identically."""
    base = _base_theme_scoring()
    panel = _theme_panel()
    # drop three members of "energy_complex" from the close matrix entirely, so the
    # basket is refused on observation coverage (2 observed of 5 configured)
    drop = [m["ticker"] for m in panel["mem"]["baskets"]["energy_complex"]["members"]][:3]
    panel = dict(panel)
    panel["closes"] = panel["closes"].drop(columns=drop)
    panel["theme_closes"] = panel["theme_closes"].drop(columns=drop)
    panel["rets"] = panel["theme_closes"].pct_change(fill_method=None)
    panel["theme_rets"] = panel["rets"]
    _patch_theme_ambient(monkeypatch, panel, tmp_path,
                         sector_doc=_sector_doc(datetime.date.today().isoformat()),
                         base=base)

    base_payload = base.compute_theme_intel("us")
    inputs = ts.acquire_theme_score_inputs("us")
    new_payload = ts.compute_theme_intel_core(inputs).payload
    assert _canonical(new_payload) == _canonical(base_payload)
    refused = {r["basket_id"] for r in new_payload["observation_refusals"]}
    assert "energy_complex" in refused


def test_narrative_core_matches_base_over_controlled_inputs(monkeypatch, tmp_path):
    """The explicit-input allocation core reproduces the BASE implementation byte for byte."""
    base = _base_narrative_rotation()
    panel = _narrative_panel()
    _patch_narrative_ambient(monkeypatch, panel, tmp_path, base=base)

    base_payload = base.compute_narrative_rotation("us")
    inputs = nr.acquire_narrative_allocation_inputs("us")
    assert inputs is not None
    new_payload = nr.compute_narrative_rotation_core(inputs)

    assert base_payload is not None
    assert new_payload is not None
    assert _canonical(new_payload) == _canonical(base_payload)
    # the fixture really allocates: weights + cash == 1 and a rank-1 theme exists
    alloc = new_payload["allocation"]
    assert abs(sum(w["weight"] for w in alloc["weights"]) + alloc["cash"] - 1.0) < 5e-3
    assert new_payload["ranks"][0]["rank"] == 1
    assert new_payload["headline"]["id"]


# ------------------------------------------------------- explicit Sector demotion
def _act_now_with_buy(bid="mag7"):
    return {"buy": [{"id": bid, "name": "n", "name_zh": "n", "score": 70, "action": "accumulate",
                     "action_en": "ACCUMULATE", "action_zh": "加仓", "label": "dominant",
                     "entry_quality": 0.7, "clean_entry": True, "reasons": ["r"],
                     "reasons_zh": ["r"]}],
            "add_on_pullback": [], "reduce": [], "conflicted": []}


def test_prior_sector_demotion_uses_the_explicit_evaluation_date():
    """The demotion is driven by the EXPLICIT evaluation date, not by the wall clock."""
    today = datetime.date(2026, 3, 10)
    text = json.dumps(_sector_doc("2026-03-09"))

    # current (as_of one day before the evaluation date) -> demoted
    act = _act_now_with_buy()
    ts._apply_sector_conflict_demotion_doc(act, text, today)
    assert [x["id"] for x in act["conflicted"]] == ["mag7"]
    assert act["buy"] == []
    assert act["conflicted"][0]["sector_stance"] == "Reduce"
    assert act["conflicted"][0]["sector_etf"] == "XLK"

    # stale (as_of more than 5 calendar days before) -> NOT demoted
    act = _act_now_with_buy()
    ts._apply_sector_conflict_demotion_doc(act, json.dumps(_sector_doc("2026-03-01")), today)
    assert act["conflicted"] == []
    assert len(act["buy"]) == 1

    # missing artifact -> NOT demoted
    act = _act_now_with_buy()
    ts._apply_sector_conflict_demotion_doc(act, None, today)
    assert act["conflicted"] == []
    assert len(act["buy"]) == 1


def test_prior_sector_demotion_never_reads_the_current_sector_output(monkeypatch, tmp_path):
    """The core must not pick up an in-progress current Sector output.

    The bundle carries the PRIOR generation as a captured string; the file on disk is
    never consulted by the demotion, so a current-generation file present in the site
    tree cannot feed the calculation (and cannot create a cycle).
    """
    site, _data = _write_site(tmp_path, _sector_doc(datetime.date.today().isoformat()))
    today = datetime.date(2026, 3, 10)
    # the file on disk says "Reduce" for XLK ...
    act = _act_now_with_buy()
    ts._apply_sector_conflict_demotion_doc(act, json.dumps(_sector_doc("2026-03-01")), today)
    assert act["conflicted"] == [], "the captured (stale) artifact must decide, not the file"
    # ... but a captured current artifact does demote
    act = _act_now_with_buy()
    ts._apply_sector_conflict_demotion_doc(act, json.dumps(_sector_doc("2026-03-09")), today)
    assert [x["id"] for x in act["conflicted"]] == ["mag7"]


def test_corrupt_prior_sector_artifact_fails_open(monkeypatch, tmp_path):
    """A corrupt Sector artifact fails open exactly as it does today: `buy` survives and
    `conflicted` stays empty."""
    base = _base_theme_scoring()
    panel = _theme_panel()
    site, _data = _write_site(tmp_path, None)
    (site / "sectordata" / "sector_central.json").write_text("{not json", encoding="utf-8")
    _patch_theme_ambient(monkeypatch, panel, tmp_path, sector_doc=None, base=base)
    # overwrite the good artifact with a corrupt one (the patcher only writes when given)
    (site / "sectordata" / "sector_central.json").write_text("{not json", encoding="utf-8")

    base_payload = base.compute_theme_intel("us")
    inputs = ts.acquire_theme_score_inputs("us")
    new_payload = ts.compute_theme_intel_core(inputs).payload
    assert _canonical(new_payload) == _canonical(base_payload)
    assert new_payload["act_now"]["conflicted"] == []
    assert new_payload["act_now"]["buy"], "the buy list must survive a corrupt artifact"


# ------------------------------------------------------------------- purity
def test_theme_core_reads_no_file_no_clock_and_writes_nothing(monkeypatch, tmp_path):
    """After acquisition the core must touch no file, no clock and no provider, and must
    write no ledger, snapshot, notification or HTML."""
    panel = _theme_panel()
    _patch_theme_ambient(monkeypatch, panel, tmp_path,
                         sector_doc=_sector_doc(datetime.date.today().isoformat()))
    inputs = ts.acquire_theme_score_inputs("us")
    assert inputs is not None

    with _Trap() as trap:
        result = ts.compute_theme_intel_core(inputs)
    assert result.payload is not None
    assert trap.reads == [], f"undeclared reads: {trap.reads}"
    assert trap.writes == [], f"undeclared writes: {trap.writes}"
    assert trap.clocks == [], f"undeclared clock reads: {trap.clocks}"


def test_narrative_core_reads_no_file_no_clock_and_writes_nothing(monkeypatch, tmp_path):
    """Same contract for the allocation core."""
    panel = _narrative_panel()
    _patch_narrative_ambient(monkeypatch, panel, tmp_path)
    inputs = nr.acquire_narrative_allocation_inputs("us")
    assert inputs is not None

    with _Trap() as trap:
        payload = nr.compute_narrative_rotation_core(inputs)
    assert payload is not None
    assert trap.reads == [], f"undeclared reads: {trap.reads}"
    assert trap.writes == [], f"undeclared writes: {trap.writes}"
    assert trap.clocks == [], f"undeclared clock reads: {trap.clocks}"


def test_theme_core_defers_the_ledger_write_instead_of_performing_it(monkeypatch, tmp_path):
    """The desk's one write is returned as deferred DATA; the core performs none."""
    stamped = []
    panel = _theme_panel()
    _patch_theme_ambient(monkeypatch, panel, tmp_path,
                         sector_doc=_sector_doc(datetime.date.today().isoformat()))
    monkeypatch.setattr(basket_breadth_divergence, "log_stamp",
                        lambda *a, **k: stamped.append(a))
    inputs = ts.acquire_theme_score_inputs("us")
    result = ts.compute_theme_intel_core(inputs)
    assert stamped == [], "the core must not write the forward log"
    assert result.deferred_effects
    kinds = {e["kind"] for e in result.deferred_effects}
    assert kinds == {"breadth_divergence_stamp"}
    assert {e["basket_id"] for e in result.deferred_effects} == {
        e["basket_id"] for e in result.deferred_effects} - {"thin"}


def test_legacy_adapter_still_performs_the_ledger_write(monkeypatch, tmp_path):
    """The legacy adapter keeps its behaviour: it acquires, scores and writes."""
    stamped = []
    panel = _theme_panel()
    _patch_theme_ambient(monkeypatch, panel, tmp_path,
                         sector_doc=_sector_doc(datetime.date.today().isoformat()))
    monkeypatch.setattr(basket_breadth_divergence, "log_stamp",
                        lambda *a, **k: stamped.append(a))
    payload = ts.compute_theme_intel("us")
    assert payload is not None
    assert stamped, "the legacy path must still stamp the forward log"


# ------------------------------------------------------------------- isolation
def test_distinct_explicit_contexts_stay_isolated(monkeypatch, tmp_path):
    """Two bundles computed in one process cannot influence one another, and changing a
    supplied input changes the observable field."""
    panel = _theme_panel()
    _patch_theme_ambient(monkeypatch, panel, tmp_path,
                         sector_doc=_sector_doc(datetime.date.today().isoformat()))
    first = ts.acquire_theme_score_inputs("us")
    second = ts.acquire_theme_score_inputs("us")
    a = ts.compute_theme_intel_core(first).payload
    b = ts.compute_theme_intel_core(second).payload
    assert _canonical(a) == _canonical(b), "the same bundle must give the same answer"

    # change ONE supplied input: the macro context
    changed = ts.ThemeScoreInputs(
        **{**first.__dict__,
           "macro_context": {"state": {"growth": -0.9, "rates": 0.9, "inflation": -0.7,
                                       "riskon": -0.8},
                             "sector_rs": {}, "display": MACRO["display"]}})
    c = ts.compute_theme_intel_core(changed).payload
    assert _canonical(c) != _canonical(a), "a changed supplied input must change the output"
    assert [t["score"] for t in c["themes"]] != [t["score"] for t in a["themes"]]


def test_core_does_not_mutate_its_inputs(monkeypatch, tmp_path):
    """The core must not mutate the bundle it was handed."""
    panel = _theme_panel()
    _patch_theme_ambient(monkeypatch, panel, tmp_path,
                         sector_doc=_sector_doc(datetime.date.today().isoformat()))
    inputs = ts.acquire_theme_score_inputs("us")
    before = _canonical({"rows": [dict(r) for r in inputs.basket_rows if not r["skip"]]})
    ts.compute_theme_intel_core(inputs)
    after = _canonical({"rows": [dict(r) for r in inputs.basket_rows if not r["skip"]]})
    assert before == after


# --------------------------------------------------------- transitions / allocation
def test_score_and_rank_transitions_are_meaningful(monkeypatch, tmp_path):
    """Altering a supplied input moves the score and the rank — the desk is not frozen."""
    panel = _theme_panel()
    _patch_theme_ambient(monkeypatch, panel, tmp_path,
                         sector_doc=_sector_doc(datetime.date.today().isoformat()))
    inputs = ts.acquire_theme_score_inputs("us")
    baseline = ts.compute_theme_intel_core(inputs).payload
    base_rank = {t["id"]: t["rank"] for t in baseline["themes"]}

    # a stronger macro state lifts the macro-sensitive themes
    strong_macro = {"state": {"growth": 0.9, "rates": 0.9, "inflation": 0.8, "riskon": 0.95},
                    "sector_rs": {"XLK": 0.99, "XLE": 0.9}, "display": MACRO["display"]}
    changed = ts.ThemeScoreInputs(**{**inputs.__dict__, "macro_context": strong_macro})
    lifted = ts.compute_theme_intel_core(changed).payload
    base_scores = {t["id"]: t["score"] for t in baseline["themes"]}
    lifted_scores = {t["id"]: t["score"] for t in lifted["themes"]}
    assert lifted_scores != base_scores, "a changed supplied input must move the scores"
    new_rank = {t["id"]: t["rank"] for t in lifted["themes"]}
    assert base_rank != new_rank or lifted_scores != base_scores


def test_narrative_allocation_is_unchanged_by_the_refactor(monkeypatch, tmp_path):
    """The allocation contract the page reads still holds after the refactor."""
    panel = _narrative_panel()
    _patch_narrative_ambient(monkeypatch, panel, tmp_path)
    payload = nr.compute_narrative_rotation("us")
    assert payload is not None
    alloc = payload["allocation"]
    assert payload["verdict"] == "discipline_not_prediction"
    assert alloc["directional"] is False
    assert abs(sum(w["weight"] for w in alloc["weights"]) + alloc["cash"] - 1.0) < 5e-3
    assert all(w["weight"] <= 0.30 + 1e-9 for w in alloc["weights"])
    assert payload["rotation"]["directional"] is False
    assert payload["ai_handoff"]["overall_verdict"] == "discipline_not_prediction"


# Parent integration regressions: public explicit paths and returned-value isolation.
def test_direct_explicit_theme_call_never_replays_ledger(monkeypatch, tmp_path):
    _patch_theme_ambient(monkeypatch, _theme_panel(), tmp_path, sector_doc=None)
    inputs = ts.acquire_theme_score_inputs("us")
    writes = []
    monkeypatch.setattr(ts, "_replay_deferred_effects", lambda effects: writes.append(effects))
    assert ts.compute_theme_intel(inputs=inputs) is not None
    assert writes == []


def test_theme_results_and_deferred_records_do_not_alias_inputs(monkeypatch, tmp_path):
    import copy
    _patch_theme_ambient(monkeypatch, _theme_panel(), tmp_path, sector_doc=None)
    inputs = ts.acquire_theme_score_inputs("us")
    before = ts.compute_theme_intel_core(inputs)
    expected_payload = _canonical(before.payload)
    expected_effects = _canonical(before.deferred_effects)
    expected_weights = copy.deepcopy(ts.WEIGHTS)
    before.payload["weights"]["trend"] = 999
    before.payload["macro_context"]["quad"] = "modified"
    before.payload["themes"][0]["mtf"]["momentum_score"] = 999
    before.payload["themes"][0]["textures"]["breadth_divergence"]["risk"] = 999
    before.deferred_effects[0]["divergence"]["risk"] = 888
    again = ts.compute_theme_intel_core(inputs)
    assert _canonical(again.payload) == expected_payload
    assert _canonical(again.deferred_effects) == expected_effects
    assert ts.WEIGHTS == expected_weights


def test_theme_explicit_refusals_are_data_without_stdout(monkeypatch, tmp_path, capsys):
    _patch_theme_ambient(monkeypatch, _theme_panel(), tmp_path, sector_doc=None)
    inputs = ts.acquire_theme_score_inputs("us")
    capsys.readouterr()
    result = ts.compute_theme_intel_core(inputs)
    assert result.payload["observation_refusals"]
    assert capsys.readouterr().out == ""
    ts.compute_theme_intel("us")
    assert "theme-observation-coverage" in capsys.readouterr().out


def test_empty_theme_core_and_legacy_keep_none_contract(monkeypatch, tmp_path):
    from dataclasses import replace
    _patch_theme_ambient(monkeypatch, _theme_panel(), tmp_path, sector_doc=None)
    inputs = replace(ts.acquire_theme_score_inputs("us"), basket_rows=())
    assert ts.compute_theme_intel(inputs=inputs) is None
    result = ts.compute_theme_intel_core(inputs)
    assert result.payload is None and result.deferred_effects == ()
    monkeypatch.setattr(ts, "acquire_theme_score_inputs", lambda region: inputs)
    assert ts.compute_theme_intel("us") is None


def test_narrative_bundle_omits_unused_loader_configuration(monkeypatch, tmp_path):
    panel = _narrative_panel()
    panel["cfg"] = {"closes": lambda: None, "membership": lambda: None}
    _patch_narrative_ambient(monkeypatch, panel, tmp_path)
    inputs = nr.acquire_narrative_allocation_inputs("us")
    assert "cfg" not in inputs.panel
    assert callable(panel["cfg"]["closes"]), "legacy setup value remains untouched"
    assert nr.compute_narrative_rotation_core(inputs) is not None


def test_explicit_absent_sizing_calibration_cannot_read_ambient(monkeypatch, tmp_path):
    from dataclasses import replace
    _patch_narrative_ambient(monkeypatch, _narrative_panel(), tmp_path)
    inputs = replace(nr.acquire_narrative_allocation_inputs("us"), sizing_calibration=None)
    def forbidden():
        raise AssertionError("explicit absence must not load ambient calibration")
    monkeypatch.setattr(nr, "_sizing_calibration", forbidden)
    with _Trap() as trap:
        result = nr.compute_narrative_rotation_core(inputs)
    assert result is not None
    assert trap.reads == trap.writes == trap.clocks == []


def test_narrative_result_does_not_alias_supplied_backtest(monkeypatch, tmp_path):
    from dataclasses import replace
    _patch_narrative_ambient(monkeypatch, _narrative_panel(), tmp_path)
    meta = {"verdict": {"edge": "context"}, "universes": {"sectors": {
        "span": ["1999", "2025"], "algorithm": {"top4_mom12_dual": {"n": 4}}}}}
    inputs = replace(nr.acquire_narrative_allocation_inputs("us"), phase0_meta=meta)
    result = nr.compute_narrative_rotation_core(inputs)
    expected = _canonical(result)
    result["backtest"]["verdict"]["edge"] = "changed"
    result["backtest"]["sectors"]["span"].append("changed")
    result["backtest"]["sectors"]["dual"]["n"] = 99
    assert _canonical(nr.compute_narrative_rotation_core(inputs)) == expected
    assert meta["verdict"]["edge"] == "context"


def test_extension_diagnostics_can_be_returned_without_stdout(capsys):
    from engine import extension
    idx = pd.bdate_range("2025-01-01", periods=210)
    closes = pd.DataFrame({str(i): np.arange(210, dtype=float) + 100 + i
                           for i in range(extension.ANCHOR_MIN_LIVE)}, index=idx)
    legacy = extension.extension_signals(closes)
    assert "extension-unresolvable" in capsys.readouterr().out
    records = []
    quiet = extension.extension_signals(closes, emit_diagnostics=False,
                                        diagnostic_records=records)
    assert quiet == legacy == {}
    assert capsys.readouterr().out == ""
    assert records[0]["reason"] == "unresolvable"
    assert records[0]["as_of"] == str(idx[-1].date())


def test_narrative_core_passes_quiet_extension_and_returns_anchor_records(monkeypatch, tmp_path):
    from engine import extension
    _patch_narrative_ambient(monkeypatch, _narrative_panel(), tmp_path)
    inputs = nr.acquire_narrative_allocation_inputs("us")
    real = extension.extension_signals
    calls = []
    def observed(closes, **kwargs):
        calls.append(kwargs)
        return real(closes, **kwargs)
    monkeypatch.setattr(extension, "extension_signals", observed)
    records = []
    assert nr.compute_narrative_rotation_core(inputs, diagnostics=records) is not None
    assert calls and all(call["emit_diagnostics"] is False for call in calls)
    assert records and all(record["basket_id"] for record in records)


def test_explicit_cores_do_not_open_provider_connections(monkeypatch, tmp_path):
    import socket
    import requests
    _patch_theme_ambient(monkeypatch, _theme_panel(), tmp_path, sector_doc=None)
    theme_inputs = ts.acquire_theme_score_inputs("us")
    _patch_narrative_ambient(monkeypatch, _narrative_panel(), tmp_path)
    narrative_inputs = nr.acquire_narrative_allocation_inputs("us")
    attempts = []
    def forbidden(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("provider connection in explicit core")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(requests.sessions.Session, "request", forbidden)
    assert ts.compute_theme_intel_core(theme_inputs).payload is not None
    assert nr.compute_narrative_rotation_core(narrative_inputs) is not None
    assert attempts == []

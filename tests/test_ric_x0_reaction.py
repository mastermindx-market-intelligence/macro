"""X0 release-reaction runner — the 29-test synthetic family (E0 section 2.H3).

Every input is synthetic: injected loaders or monkeypatched default factories.
No real data is read; nothing outside pytest's tmp_path is written. The
planted co-movement (CPI:DGS2, beta = 3 bp/sd, same sign in both eras) is the
family's positive control; every other id is noise or a deliberate sign flip.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats as sps

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MODULE_PATH = ROOT / "research/rates_inflation_command/seat_20261014/x0_reaction.py"
_spec = importlib.util.spec_from_file_location("x0_reaction", MODULE_PATH)
x0 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(x0)

from engine.challenger_spa_comparison import newey_west_lrvar  # noqa: E402
from engine.desk_placebo import holm_adjust  # noqa: E402
from engine.grading_stats import wilson_ci  # noqa: E402

PPI_RECEIPT = {
    "rows": [
        {
            "period": "2019-11",
            "ppiaco_first_realtime_start": "2019-12-06",
            "wpsfd49207_first_realtime_start": "2019-12-06",
            "agree": True,
        }
    ],
    "inputs": {"ppi_date_disagreements": []},
}
GDP_RECEIPT = {
    "rows": [
        {
            "quarter": "2019Q4",
            "gdp_first_realtime_start": "2020-01-30",
            "gdpc1_first_realtime_start": "2020-01-30",
            "agree": True,
        }
    ]
}


class _Recorder:
    def __init__(self):
        self.calls = []

    def log_declared_budget(self, n, *, family=None, reason=None):
        self.calls.append({"n": n, "family": family, "reason": reason})
        return True


def _month_range(start: str, end: str) -> list[str]:
    out = []
    t = pd.Timestamp(start + "-01")
    stop = pd.Timestamp(end + "-01")
    while t <= stop:
        out.append(t.strftime("%Y-%m"))
        t += pd.offsets.MonthBegin(1)
    return out


def _nth_weekday(year: int, month: int, n: int, weekday: int) -> pd.Timestamp:
    d = pd.Timestamp(year=year, month=month, day=1)
    offset = (weekday - d.dayofweek) % 7
    return d + pd.Timedelta(days=offset + 7 * (n - 1))


def _roll_forward(d: pd.Timestamp) -> pd.Timestamp:
    while d.dayofweek >= 5:
        d = d + pd.Timedelta(days=1)
    return d


def _cpi_day(period: str) -> str:
    y, m = (int(x) for x in period.split("-"))
    return _roll_forward(pd.Timestamp(year=y, month=m, day=12)).strftime("%Y-%m-%d")


def _nfp_day(period: str) -> str:
    y, m = (int(x) for x in period.split("-"))
    return _nth_weekday(y, m, 1, 4).strftime("%Y-%m-%d")


def _rt_loader(core, core_days, headline, headline_days, payroll, nfp_days):
    def rt(series_id, period):
        if series_id == "CPILFESL":
            src, days = core, core_days
        elif series_id == "CPIAUCSL":
            src, days = headline, headline_days
        elif series_id == "PAYEMS":
            src, days = payroll, nfp_days
        else:
            raise AssertionError(f"unexpected series {series_id}")
        val = src.get(period, "MISSING")
        if val == "MISSING" or val is None:
            return {
                "status": "unavailable",
                "release_date": None,
                "published_proxy_1dp": None,
                "payroll_change_thousands": None,
            }
        rec = {
            "status": "ok",
            "release_date": days[period],
            "published_proxy_1dp": None,
            "payroll_change_thousands": None,
        }
        if series_id == "PAYEMS":
            rec["payroll_change_thousands"] = float(val)
        else:
            rec["published_proxy_1dp"] = float(val)
        return rec

    return rt


def _write_receipts(root: Path, ppi=None, gdp=None) -> tuple[Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    ppi_path = root / "ppi_receipt.json"
    gdp_path = root / "gdp_receipt.json"
    ppi_path.write_text(json.dumps(ppi or PPI_RECEIPT), encoding="utf-8")
    gdp_path.write_text(json.dumps(gdp or GDP_RECEIPT), encoding="utf-8")
    return ppi_path, gdp_path


def _run_world(tmp_path, loaders, *, asof=None, declare_budget=False, root=None):
    root = Path(root) if root else tmp_path / "root"
    root.mkdir(parents=True, exist_ok=True)
    ppi_path, gdp_path = _write_receipts(root)
    out = tmp_path / "out"
    receipt = x0.run(
        root,
        out,
        asof=asof,
        declare_budget=declare_budget,
        loaders=loaders,
        ppi_dates_path=ppi_path,
        gdp_dates_path=gdp_path,
    )
    return receipt, out


def _default_tier1():
    return {k: set() for k in x0.TIER1_KEYS}


def _ep(receipt, release, period):
    for e in receipt["episodes"]:
        if e["release"] == release and e["period"] == period:
            return e
    raise AssertionError(f"episode not found: {release} {period}")


def _status_counts(receipt, release):
    return receipt["counts"][release]


# ---------------------------------------------------------------------------
# The big planted world (positive control + sign flip + weak id)
# ---------------------------------------------------------------------------

_BIG_SEED = 20261014
_WEAK = (0.55, 2.75)  # (bp per sd, noise sd) for the CPI:T10YIE weak plant
_SC = math.sqrt(24.0 / 23.0)  # rolling sd of any 24 alternating +1/-1 surprises


def _big_world(seed=_BIG_SEED, weak=_WEAK):
    rng = np.random.default_rng(seed)
    periods = _month_range("2007-02", "2026-06")
    core, core_days, headline, headline_days = {}, {}, {}, {}
    payroll, nfp_days = {}, {}
    for i, p in enumerate(periods):
        core[p] = 0.0 if i % 2 == 0 else 1.0
        core_days[p] = _cpi_day(p)
        headline[p] = 0.2 + rng.normal(0.0, 1.0)
        headline_days[p] = _cpi_day(p)
        payroll[p] = 100.0 + (0.0 if i % 2 == 0 else 1.0)
        nfp_days[p] = _nfp_day(p)
    headline_days["2014-06"] = "2014-06-13"  # headline day differs -> None
    headline_days["2023-02"] = "2023-02-14"
    core_surprise = {
        periods[i]: core[periods[i]] - core[periods[i - 1]]
        for i in range(1, len(periods))
    }
    nfp_surprise = {
        periods[i]: payroll[periods[i]] - payroll[periods[i - 1]]
        for i in range(1, len(periods))
    }
    headline_surprise = {
        periods[i]: headline[periods[i]] - headline[periods[i - 1]]
        for i in range(1, len(periods))
        if headline_days[periods[i]] == core_days[periods[i]]
    }
    tier1 = _default_tier1()
    fomc_cpi = [core_days[p] for p in ("2013-05", "2019-08", "2024-03")]
    ppi_nfp = [nfp_days[p] for p in ("2012-04", "2022-09")]
    tier1["FOMC"] = set(fomc_cpi)
    tier1["PPI"] = set(ppi_nfp)

    cpi_day_to_p = {core_days[p]: p for p in periods}
    nfp_day_to_p = {nfp_days[p]: p for p in periods}
    bdays = pd.bdate_range("2007-01-01", "2026-07-31")
    series: dict[str, pd.Series] = {}
    w_eps, sd_eps = weak

    def _bp(v):
        # series are in percent; h0/h1 are in bp, so a v bp move is v/100
        return v / 100.0

    for name in x0.RESPONSES:
        base = {"DGS2": 2.0, "DGS10": 4.0, "DFII10": 1.8, "T10YIE": 2.2}[name]
        inc = np.zeros(len(bdays))
        for i, d in enumerate(bdays):
            ds = d.strftime("%Y-%m-%d")
            if name == "DGS2":
                if ds in cpi_day_to_p and cpi_day_to_p[ds] in core_surprise:
                    x = core_surprise[cpi_day_to_p[ds]] / _SC
                    inc[i] = _bp(3.0 * x + rng.normal(0.0, 0.25))
                elif ds in nfp_day_to_p and nfp_day_to_p[ds] in nfp_surprise:
                    x = nfp_surprise[nfp_day_to_p[ds]] / _SC
                    sgn = -1.0 if d >= pd.Timestamp("2021-01-01") else 1.0
                    inc[i] = _bp(sgn * 3.0 * x + rng.normal(0.0, 0.25))
                else:
                    inc[i] = _bp(rng.normal(0.0, 0.05))
            elif name == "DGS10":
                if ds in cpi_day_to_p:
                    p = cpi_day_to_p[ds]
                    inc[i] = _bp(1.3 * headline_surprise.get(p, 0.0)
                                 + rng.normal(0.0, 0.40))
                else:
                    inc[i] = _bp(rng.normal(0.0, 0.05))
            elif name == "T10YIE":
                if ds in cpi_day_to_p and cpi_day_to_p[ds] in core_surprise:
                    x = core_surprise[cpi_day_to_p[ds]] / _SC
                    inc[i] = _bp(w_eps * x + rng.normal(0.0, sd_eps))
                else:
                    inc[i] = _bp(rng.normal(0.0, 0.05))
            else:
                inc[i] = _bp(rng.normal(0.0, 0.05))
        series[name] = pd.Series(base + np.cumsum(inc), index=bdays)

    rt = _rt_loader(core, core_days, headline, headline_days, payroll, nfp_days)
    loaders = {
        "release_target": rt,
        "periods": lambda sid: list(periods),
        "tier1_dates": lambda: {k: set(v) for k, v in tier1.items()},
        "response": lambda name: series[name],
    }
    return {
        "periods": periods,
        "loaders": loaders,
        "tier1": tier1,
        "core_days": core_days,
        "nfp_days": nfp_days,
        "core_surprise": core_surprise,
        "nfp_surprise": nfp_surprise,
        "series": series,
        "fomc_cpi": fomc_cpi,
        "ppi_nfp": ppi_nfp,
    }


@pytest.fixture(scope="module")
def big_receipt(tmp_path_factory):
    world = _big_world()
    root = tmp_path_factory.mktemp("bigroot")
    ppi_path, gdp_path = _write_receipts(root)
    out = tmp_path_factory.mktemp("bigout")
    receipt = x0.run(
        root,
        out,
        loaders=world["loaders"],
        ppi_dates_path=ppi_path,
        gdp_dates_path=gdp_path,
    )
    return receipt, out, world


# ---------------------------------------------------------------------------
# Group A — core
# ---------------------------------------------------------------------------

def test_constants_frozen():
    assert x0.SCHEMA == "ric_x0_reaction.v1"
    assert x0.TRIAL_FAMILY == "ric_x0_release_reaction_v1"
    assert x0.TRIAL_BUDGET == 8
    assert x0.PROTOCOL_PATH == (
        "research/rates_inflation_command/seat_20261014/E0_RESEARCH_PROTOCOL.md"
    )
    assert x0.PROTOCOL_SHA256 == (
        "87b51dcad66c6f84989675e9cce91eb5b46b3888d60b2e599a8736d87e2309df"
    )
    assert x0.RELEASES == ("CPI", "NFP")
    assert x0.TESTED_SERIES == {"CPI": "CPILFESL", "NFP": "PAYEMS"}
    assert x0.DESCRIPTIVE_SERIES == {"CPI_HEADLINE": "CPIAUCSL"}
    assert x0.RESPONSES == ("DGS2", "DGS10", "DFII10", "T10YIE")
    assert x0.ERAS == {
        "2010s": ("2010-01-01", "2019-12-31"),
        "2021+": ("2021-01-01", None),
    }
    assert x0.SCALE_WINDOW == 24
    assert x0.MIN_EPISODES_PER_ERA == 40
    assert x0.ALPHA == 0.05
    assert x0.PRIOR_CLOSE_MAX_GAP_DAYS == 7
    assert x0.FIRST_PERIOD == "2007-02"
    assert x0.BENCHMARK_LABEL == "change vs a no-change benchmark"
    assert x0.TEST_IDS == (
        "CPI:DGS2", "CPI:DGS10", "CPI:DFII10", "CPI:T10YIE",
        "NFP:DGS2", "NFP:DGS10", "NFP:DFII10", "NFP:T10YIE",
    )


def test_surprise_is_first_print_minus_prior_first_print(tmp_path):
    core_vals = [0.2, 0.5, -0.1, 0.3, 0.0, 0.4]
    periods = _month_range("2010-01", "2010-06")
    core = dict(zip(periods, core_vals))
    core_days = {p: _cpi_day(p) for p in periods}
    payroll_vals = [120.0, -30.0, 210.0, 0.0, 65.0, -140.0]
    payroll = dict(zip(periods, payroll_vals))
    nfp_days = {p: _nfp_day(p) for p in periods}
    headline = {p: 0.1 for p in periods}
    headline_days = dict(core_days)
    rt = _rt_loader(core, core_days, headline, headline_days, payroll, nfp_days)
    flat_idx = pd.bdate_range("2010-01-04", "2010-03-01")
    loaders = {
        "release_target": rt,
        "periods": lambda sid: list(periods),
        "tier1_dates": _default_tier1,
        "response": lambda name: pd.Series(1.0, index=flat_idx),
    }
    receipt, _ = _run_world(tmp_path, loaders)
    for i in range(1, len(periods)):
        ep = _ep(receipt, "CPI", periods[i])
        assert ep["first_print"] == core_vals[i]
        assert ep["naive_prior"] == core_vals[i - 1]
        assert ep["surprise_raw"] == pytest.approx(core_vals[i] - core_vals[i - 1])
        assert ep["units"] == "pp m/m (first print, 0.1 pp)"
        nep = _ep(receipt, "NFP", periods[i])
        assert nep["first_print"] == payroll_vals[i]
        assert nep["naive_prior"] == payroll_vals[i - 1]
        assert nep["surprise_raw"] == pytest.approx(payroll_vals[i] - payroll_vals[i - 1])
        assert nep["units"] == "thousands of jobs m/m (first print)"


def test_cpi_tested_surprise_is_core(tmp_path):
    # core and headline deliberately disagree: the TESTED surprise must be core
    periods = _month_range("2008-01", "2011-12")
    core = {p: (0.0 if i % 2 == 0 else 1.0) for i, p in enumerate(periods)}
    headline = {p: (0.3 if i % 3 == 0 else -0.2) for i, p in enumerate(periods)}
    core_days = {p: _cpi_day(p) for p in periods}
    headline_days = dict(core_days)
    payroll = {p: (0.0 if i % 2 == 0 else 1.0) for i, p in enumerate(periods)}
    nfp_days = {p: _nfp_day(p) for p in periods}
    rt = _rt_loader(core, core_days, headline, headline_days, payroll, nfp_days)
    bdays = pd.bdate_range("2007-12-01", "2012-03-01")
    series = {n: pd.Series(np.linspace(2.0, 3.0, len(bdays)), index=bdays)
              for n in x0.RESPONSES}
    loaders = {
        "release_target": rt,
        "periods": lambda sid: list(periods),
        "tier1_dates": _default_tier1,
        "response": lambda name: series[name],
    }
    receipt, _ = _run_world(tmp_path, loaders)
    for i, p in enumerate(periods[1:], start=1):
        ep = _ep(receipt, "CPI", p)
        if ep["surprise_raw"] is not None:
            assert ep["surprise_raw"] == pytest.approx(core[p] - core[periods[i - 1]])
    # a period where headline and core differ must NOT change the tested x
    probe = periods[-1]
    ep = _ep(receipt, "CPI", probe)
    assert ep["x"] == pytest.approx(ep["surprise_raw"] / ep["scale"])


def test_scale_uses_strictly_prior_24(tmp_path):
    periods = _month_range("2007-02", "2009-12")  # 35 periods
    s_vals = [1.0, -1.0] * 18  # alternating surprises...
    s_vals = s_vals[:34]
    s_vals[5] = 3.7  # ...except one extreme episode
    core = {periods[0]: 0.0}
    for i in range(1, len(periods)):
        core[periods[i]] = core[periods[i - 1]] + s_vals[i - 1]
    core_days = {p: _cpi_day(p) for p in periods}
    headline = {p: 0.2 for p in periods}
    payroll = {p: 100.0 for p in periods}
    nfp_days = {p: _nfp_day(p) for p in periods}
    rt = _rt_loader(core, core_days, headline, dict(core_days), payroll, nfp_days)
    bdays = pd.bdate_range("2007-01-01", "2010-03-01")
    series = {n: pd.Series(np.linspace(2.0, 3.0, len(bdays)), index=bdays)
              for n in x0.RESPONSES}
    loaders = {
        "release_target": rt,
        "periods": lambda sid: list(periods),
        "tier1_dates": _default_tier1,
        "response": lambda name: series[name],
    }
    receipt, _ = _run_world(tmp_path, loaders)
    surprises = [core[periods[i]] - core[periods[i - 1]] for i in range(1, len(periods))]
    # episodes 1..24 (0-based over episode list) lack 24 prior surprises
    for k in range(24):
        ep = receipt["episodes"][k]
        assert ep["status"] == "INSUFFICIENT_HISTORY"
        assert ep["scale"] is None
    # E[24] scales on exactly the first 24 surprises
    ep25 = receipt["episodes"][24]
    assert ep25["status"] != "INSUFFICIENT_HISTORY"
    assert ep25["scale"] == pytest.approx(float(np.std(surprises[0:24], ddof=1)))
    # E[5]'s extreme surprise (3.7) enters later windows but never its own:
    # E[5] itself has only 5 priors, so it is insufficient regardless
    ep6 = receipt["episodes"][5]
    assert ep6["status"] == "INSUFFICIENT_HISTORY"
    assert ep6["scale"] is None
    # E[26]'s window is surprises[2:26] and DOES include the extreme E[5]
    ep27 = receipt["episodes"][26]
    assert ep27["scale"] == pytest.approx(float(np.std(surprises[2:26], ddof=1)))
    assert _status_counts(receipt, "CPI")["INSUFFICIENT_HISTORY"] == 24


def test_insufficient_history_excluded_and_listed(big_receipt):
    receipt, _, _ = big_receipt
    counts = _status_counts(receipt, "CPI")
    assert counts["INSUFFICIENT_HISTORY"] == 24
    listed = [e for e in receipt["episodes"]
              if e["release"] == "CPI"
              and e["status"] == "INSUFFICIENT_HISTORY"]
    assert len(listed) == 24
    assert all(e["x"] is None and e["scale"] is None for e in listed)
    # none of them reaches any era statistic
    for tid in x0.TEST_IDS:
        for era in ("2010s", "2021+"):
            assert receipt["tests"][tid]["eras"][era]["n"] > 0


def test_missing_source_and_no_benchmark_listed(tmp_path):
    periods = _month_range("2010-01", "2010-08")
    core = {p: 0.2 for p in periods}
    core["2010-04"] = None          # its own cur missing; and 2010-05 loses its
                                    # benchmark -> MISSING_SOURCE + NO_BENCHMARK
    core_days = {p: _cpi_day(p) for p in periods}
    # prev of 2010-08 released ON 2010-08's day -> benchmark not public before D
    core_days["2010-07"] = core_days["2010-08"]
    headline = {p: 0.1 for p in periods}
    headline_days = dict(core_days)
    payroll = {p: 100.0 for p in periods}
    nfp_days = {p: _nfp_day(p) for p in periods}
    rt = _rt_loader(core, core_days, headline, headline_days, payroll, nfp_days)
    bdays = pd.bdate_range("2010-01-01", "2010-10-01")
    series = {n: pd.Series(np.linspace(2.0, 3.0, len(bdays)), index=bdays)
              for n in x0.RESPONSES}
    loaders = {
        "release_target": rt,
        "periods": lambda sid: list(periods),
        "tier1_dates": _default_tier1,
        "response": lambda name: series[name],
    }
    receipt, _ = _run_world(tmp_path, loaders)
    ms = _ep(receipt, "CPI", "2010-04")
    assert ms["status"] == "MISSING_SOURCE"
    assert ms["surprise_raw"] is None and ms["first_print"] is None
    nb1 = _ep(receipt, "CPI", "2010-05")
    assert nb1["status"] == "NO_BENCHMARK"
    assert nb1["surprise_raw"] is None
    nb2 = _ep(receipt, "CPI", "2010-08")
    assert nb2["status"] == "NO_BENCHMARK"  # prev release_date >= D
    assert nb2["surprise_raw"] is None
    counts = _status_counts(receipt, "CPI")
    assert counts["MISSING_SOURCE"] == 1
    assert counts["NO_BENCHMARK"] == 2


def _small_world(tmp_path, periods, *, core=None, headline=None, payroll=None,
                 core_days=None, headline_days=None, nfp_days=None, tier1=None,
                 series=None, asof=None):
    core = core if core is not None else {p: (0.0 if i % 2 == 0 else 1.0)
                                          for i, p in enumerate(periods)}
    headline = headline if headline is not None else {p: 0.2 for p in periods}
    payroll = payroll if payroll is not None else {
        p: (100.0 if i % 2 == 0 else 101.0) for i, p in enumerate(periods)}
    core_days = core_days if core_days is not None else {p: _cpi_day(p) for p in periods}
    headline_days = headline_days if headline_days is not None else dict(core_days)
    nfp_days = nfp_days if nfp_days is not None else {p: _nfp_day(p) for p in periods}
    tier1 = tier1 if tier1 is not None else _default_tier1()
    if series is None:
        bdays = pd.bdate_range(
            pd.Timestamp(periods[0] + "-01") - pd.Timedelta(days=10),
            pd.Timestamp(periods[-1] + "-01") + pd.offsets.MonthEnd(1),
        )
        series = {n: pd.Series(np.linspace(2.0, 3.0, len(bdays)), index=bdays)
                  for n in x0.RESPONSES}
    rt = _rt_loader(core, core_days, headline, headline_days, payroll, nfp_days)
    loaders = {
        "release_target": rt,
        "periods": lambda sid: list(periods),
        "tier1_dates": lambda: {k: set(v) for k, v in tier1.items()},
        "response": lambda name: series[name],
    }
    return _run_world(tmp_path, loaders, asof=asof)


def test_h0_uses_last_close_strictly_before_D(tmp_path):
    periods = _month_range("2007-02", "2010-07")
    core_days = {p: _cpi_day(p) for p in periods}
    core_days["2010-07"] = "2010-07-13"  # Tuesday after a Monday holiday
    base = list(pd.bdate_range("2010-01-01", "2010-07-20"))

    def _mk(drop):
        idx = [d for d in base if d not in drop]
        return pd.Series(np.arange(1.0, len(idx) + 1.0), index=pd.DatetimeIndex(idx))

    holiday_week = set(pd.bdate_range("2010-05-04", "2010-05-11"))
    series = {
        "DGS2": _mk({pd.Timestamp("2010-07-12")} | holiday_week),
        "DGS10": _mk({pd.Timestamp("2010-04-12")}),
        "DFII10": _mk(set()),
        "T10YIE": _mk(set()),
    }
    receipt, _ = _small_world(
        tmp_path, periods, core_days=core_days, series=series
    )
    s2 = series["DGS2"]
    # D = 2010-07-13: prior close is Friday 2010-07-09 (07-12 is a holiday),
    # never the calendar day D-1
    ep = _ep(receipt, "CPI", "2010-07")
    assert ep["h0_bp"]["DGS2"] == pytest.approx(
        100.0 * (s2[pd.Timestamp("2010-07-13")] - s2[pd.Timestamp("2010-07-09")])
    )
    assert ep["missing_response"] == []
    # h1 uses the next trading day after D
    assert ep["h1_bp"]["DGS2"] == pytest.approx(
        100.0 * (s2[pd.Timestamp("2010-07-14")] - s2[pd.Timestamp("2010-07-13")])
    )
    # D = 2010-05-12: last DGS2 close is 9 calendar days back -> too far
    ep_gap = _ep(receipt, "CPI", "2010-05")
    assert "DGS2" in ep_gap["missing_response"]
    assert ep_gap["h0_bp"]["DGS2"] is None
    assert "DGS10" not in ep_gap["missing_response"]  # intact index, 1-day gap
    # D = 2010-04-12 absent from the DGS10 index entirely
    ep_abs = _ep(receipt, "CPI", "2010-04")
    assert "DGS10" in ep_abs["missing_response"]
    assert ep_abs["h0_bp"]["DGS10"] is None


def test_missing_response_counted_and_listed(tmp_path):
    periods = _month_range("2007-02", "2010-07")
    core_days = {p: _cpi_day(p) for p in periods}
    base = list(pd.bdate_range("2007-01-01", "2010-07-20"))
    series = {
        "DGS2": pd.Series(np.arange(1.0, len(base) + 1.0),
                          index=pd.DatetimeIndex(base)),
        "DGS10": pd.Series(
            np.arange(1.0, len(base)),
            index=pd.DatetimeIndex([d for d in base
                                    if d != pd.Timestamp("2010-04-12")]),
        ),
        "DFII10": pd.Series(np.arange(1.0, len(base) + 1.0),
                            index=pd.DatetimeIndex(base)),
        "T10YIE": pd.Series(np.arange(1.0, len(base) + 1.0),
                            index=pd.DatetimeIndex(base)),
    }
    receipt, _ = _small_world(tmp_path, periods, core_days=core_days, series=series)
    assert _status_counts(receipt, "CPI")["MISSING_RESPONSE"] == 1
    ep = _ep(receipt, "CPI", "2010-04")
    assert ep["missing_response"] == ["DGS10"]
    assert ep["h0_bp"]["DGS2"] is not None  # still counts for other responses
    n_dgs10 = receipt["tests"]["CPI:DGS10"]["eras"]["2010s"]["n"]
    n_dgs2 = receipt["tests"]["CPI:DGS2"]["eras"]["2010s"]["n"]
    assert n_dgs10 == n_dgs2 - 1


def _scale_window(core, core_days, periods, target_period, exclude=()):
    """Replicate the spec 2.3 scale window independently of the module."""
    cand = []
    for i in range(1, len(periods)):
        p = periods[i]
        if p in exclude:
            continue
        cand.append(
            (pd.Timestamp(core_days[p]), core[p] - core[periods[i - 1]])
        )
    cand.sort(key=lambda t: t[0])
    day = pd.Timestamp(core_days[target_period])
    return [s for d, s in cand if d < day][-x0.SCALE_WINDOW:]


def test_tier1_collision_excluded_and_listed(tmp_path):
    periods = _month_range("2007-02", "2011-12")
    s_vals = [1.0, -1.0] * 30
    core = {periods[0]: 0.0}
    for i in range(1, len(periods)):
        core[periods[i]] = core[periods[i - 1]] + s_vals[i - 1]
    core_days = {p: _cpi_day(p) for p in periods}
    tier1 = _default_tier1()
    tier1["FOMC"] = {core_days["2010-04"]}
    tier1["PPI"] = {core_days["2010-09"]}
    receipt, _ = _small_world(tmp_path, periods, core=core,
                              core_days=core_days, tier1=tier1)
    ep1 = _ep(receipt, "CPI", "2010-04")
    ep2 = _ep(receipt, "CPI", "2010-09")
    assert ep1["status"] == "TIER1_COLLISION" and ep1["collided_with"] == ["FOMC"]
    assert ep2["status"] == "TIER1_COLLISION" and ep2["collided_with"] == ["PPI"]
    assert _status_counts(receipt, "CPI")["TIER1_COLLISION"] == 2
    # the collided episodes' surprises still feed later scales (spec 2.3)
    ep_after = _ep(receipt, "CPI", "2010-10")
    window = _scale_window(core, core_days, periods, "2010-10")
    assert len(window) == x0.SCALE_WINDOW
    assert ep_after["scale"] == pytest.approx(float(np.std(window, ddof=1)))
    # no TIER1 episode reaches a statistic: 2010s CPI has 24 months - 2
    assert receipt["tests"]["CPI:DGS2"]["eras"]["2010s"]["n"] == 22


def test_multi_period_release_day_excluded_and_listed(tmp_path):
    periods = _month_range("2007-02", "2011-12")
    s_vals = [1.0, -1.0] * 30
    core = {periods[0]: 0.0}
    for i in range(1, len(periods)):
        core[periods[i]] = core[periods[i - 1]] + s_vals[i - 1]
    core_days = {p: _cpi_day(p) for p in periods}
    # two NON-adjacent periods share one release day (2011-03 is released
    # very late, on 2011-05's day); adjacent periods cannot test this because
    # the later one loses its benchmark first
    core_days["2011-03"] = core_days["2011-05"]
    receipt, _ = _small_world(tmp_path, periods, core=core, core_days=core_days)
    e1 = _ep(receipt, "CPI", "2011-03")
    e2 = _ep(receipt, "CPI", "2011-05")
    assert e1["status"] == "MULTI_PERIOD_RELEASE_DAY"
    assert e2["status"] == "MULTI_PERIOD_RELEASE_DAY"
    assert e1["x"] is None and e2["scale"] is None
    assert _status_counts(receipt, "CPI")["MULTI_PERIOD_RELEASE_DAY"] == 2
    # 2011-04's benchmark (2011-03) is not public before 2011-04's own day
    mid = _ep(receipt, "CPI", "2011-04")
    assert mid["status"] == "NO_BENCHMARK"
    # none of the three surprises feeds a later scale
    ep = _ep(receipt, "CPI", "2011-06")
    window = _scale_window(core, core_days, periods, "2011-06",
                           exclude=("2011-03", "2011-04", "2011-05"))
    assert len(window) == x0.SCALE_WINDOW
    assert ep["scale"] == pytest.approx(float(np.std(window, ddof=1)))


def test_eras_split_and_2020_excluded(big_receipt):
    receipt, _, _ = big_receipt
    assert _status_counts(receipt, "CPI")["OUT_OF_ERA"] == 22  # 10x 2009 + 12x 2020
    e2020 = [e for e in receipt["episodes"] if e["release"] == "CPI"
             and e["period"].startswith("2020")]
    assert len(e2020) == 12
    assert all(e["status"] == "OUT_OF_ERA" and e["era"] is None for e in e2020)
    for e in receipt["episodes"]:
        if e["status"] == "OK":
            assert e["era"] in ("2010s", "2021+")
            if e["era"] == "2010s":
                assert "2010-01-01" <= e["release_day"] <= "2019-12-31"
            else:
                assert e["release_day"] >= "2021-01-01"
    n1 = receipt["tests"]["CPI:DGS2"]["eras"]["2010s"]["n"]
    n2 = receipt["tests"]["CPI:DGS2"]["eras"]["2021+"]["n"]
    assert n1 == 118 and n2 == 65


def test_after_asof_excluded(tmp_path):
    world = _big_world()
    root = tmp_path / "root"
    ppi_path, gdp_path = _write_receipts(root)
    receipt = x0.run(root, tmp_path / "out1", asof="2024-06-30",
                     loaders=world["loaders"], ppi_dates_path=ppi_path,
                     gdp_dates_path=gdp_path)
    assert receipt["asof"] == "2024-06-30"
    after = [e for e in receipt["episodes"]
             if e["status"] == "AFTER_ASOF" and e["release"] == "CPI"]
    assert len(after) == 24  # CPI 2024-07..2026-06
    assert all(e["release_day"] > "2024-06-30" for e in after)
    assert _status_counts(receipt, "CPI")["AFTER_ASOF"] == 24
    # default as-of: the minimum last date across the four responses
    root2 = tmp_path / "root2"
    p2, g2 = _write_receipts(root2)
    receipt2 = x0.run(root2, tmp_path / "out2", loaders=world["loaders"],
                      ppi_dates_path=p2, gdp_dates_path=g2)
    assert receipt2["asof"] == "2026-07-31"
    assert _status_counts(receipt2, "CPI").get("AFTER_ASOF", 0) == 0


def test_slope_and_hac_se_match_owner(big_receipt):
    receipt, _, _ = big_receipt
    for tid, era in (("CPI:DGS2", "2010s"), ("NFP:DGS2", "2021+"),
                     ("CPI:T10YIE", "2010s")):
        release, resp = tid.split(":")
        pairs = [
            (e["x"], e["h0_bp"][resp]) for e in receipt["episodes"]
            if e["release"] == release and e["status"] == "OK"
            and e["era"] == era and e["h0_bp"][resp] is not None
        ]
        xv = np.array([p[0] for p in pairs])
        yv = np.array([p[1] for p in pairs])
        n = len(pairs)
        xt = xv - xv.mean()
        sxx = float(xt @ xt)
        beta = float(xt @ yv) / sxx
        u = yv - yv.mean() - beta * xt
        se = math.sqrt(n * newey_west_lrvar(xt * u)) / sxx
        blk = receipt["tests"][tid]["eras"][era]
        assert blk["n"] == n
        assert blk["beta_bp_per_sd"] == pytest.approx(beta, abs=2e-6)
        assert blk["se"] == pytest.approx(se, abs=2e-6)
        assert blk["z"] == pytest.approx(beta / se, rel=1e-6)


def test_p_values_normal_and_t(big_receipt):
    receipt, _, _ = big_receipt
    seen = 0
    for tid in x0.TEST_IDS:
        for era in ("2010s", "2021+"):
            blk = receipt["tests"][tid]["eras"][era]
            if blk["p_normal"] is None:
                assert blk["beta_bp_per_sd"] is None
                assert blk["degenerate_reason"] is not None
                continue
            z = blk["z"]
            assert blk["p_normal"] == pytest.approx(
                2.0 * float(sps.norm.sf(abs(z))), abs=2e-6)
            assert blk["p_t"] == pytest.approx(
                2.0 * float(sps.t.sf(abs(z), df=blk["n"] - 2)), abs=2e-6)
            seen += 1
    assert seen >= 14


def test_holm_applied_within_era(big_receipt):
    receipt, _, _ = big_receipt
    for era in ("2010s", "2021+"):
        raw_n = {tid: receipt["tests"][tid]["eras"][era]["p_normal"]
                 for tid in x0.TEST_IDS}
        raw_t = {tid: receipt["tests"][tid]["eras"][era]["p_t"]
                 for tid in x0.TEST_IDS}
        exp_n = holm_adjust(raw_n)
        exp_t = holm_adjust(raw_t)
        for tid in x0.TEST_IDS:
            blk = receipt["tests"][tid]["eras"][era]
            if exp_n[tid] is None:
                assert blk["p_holm_normal"] is None
            else:
                assert blk["p_holm_normal"] == pytest.approx(exp_n[tid], abs=1e-5)
                assert blk["p_holm_normal"] >= blk["p_normal"] - 1e-9
                assert blk["p_holm_t"] == pytest.approx(exp_t[tid], abs=1e-5)
    # the weak plant clears nothing: raw p < alpha, Holm-adjusted p >= alpha
    blk = receipt["tests"]["CPI:T10YIE"]["eras"]["2021+"]
    assert blk["p_normal"] < x0.ALPHA
    assert blk["p_holm_normal"] >= x0.ALPHA
    assert blk["clears"] is False
    assert receipt["tests"]["CPI:T10YIE"]["label"] == "NOT_IDENTIFIED"
    assert "not_significant:2010s" in receipt["tests"]["CPI:T10YIE"]["reasons"]
    # the strong plant clears Holm in both eras
    for era in ("2010s", "2021+"):
        blk = receipt["tests"]["CPI:DGS2"]["eras"][era]
        assert blk["p_holm_normal"] < x0.ALPHA and blk["p_holm_t"] < x0.ALPHA
        assert blk["clears"] is True


_BORDER_EPS = [1.28, -1.01, 0.72, -0.43, 0.14, -0.72]
_BORDER_B = 0.18  # tuned so z clears Holm-normal but not Holm-t at n=6 (df=4)


def test_clear_requires_both_p_types(tmp_path):
    periods = _month_range("2007-02", "2010-06")
    core = {p: (0.0 if i % 2 == 0 else 1.0) for i, p in enumerate(periods)}
    core_days = {p: _cpi_day(p) for p in periods}
    bdays = pd.bdate_range("2007-01-01", "2010-07-31")
    era_periods = _month_range("2010-01", "2010-06")
    dgs2 = pd.Series(np.linspace(2.0, 2.5, len(bdays)), index=bdays)
    dgs2_vals = dict(zip(era_periods, _BORDER_EPS))
    # DGS2 moves ONLY on the six 2010 CPI days, by B*x + eps (in bp)
    day_to_p = {core_days[p]: p for p in periods}
    for i, d in enumerate(bdays):
        p = day_to_p.get(d.strftime("%Y-%m-%d"))
        if p in dgs2_vals:
            j = periods.index(p)
            x = (core[p] - core[periods[j - 1]]) / _SC
            dgs2.iloc[i] = dgs2.iloc[i - 1] + (_BORDER_B * x + dgs2_vals[p]) / 100.0
    series = {"DGS2": dgs2}
    for name in ("DGS10", "DFII10", "T10YIE"):
        series[name] = pd.Series(np.linspace(2.0, 3.0, len(bdays)), index=bdays)
    receipt, _ = _small_world(tmp_path, periods, core=core,
                              core_days=core_days, series=series)
    blk = receipt["tests"]["CPI:DGS2"]["eras"]["2010s"]
    assert blk["n"] == 6
    assert blk["p_normal"] < x0.ALPHA
    assert blk["p_holm_normal"] < x0.ALPHA
    assert blk["p_holm_t"] >= x0.ALPHA
    assert blk["clears"] is False
    assert blk["borderline"] is True
    assert receipt["tests"]["CPI:DGS2"]["label"] == "NOT_IDENTIFIED"
    assert "not_significant:2010s" in receipt["tests"]["CPI:DGS2"]["reasons"]


def test_label_requires_same_sign_both_eras(big_receipt):
    receipt, _, _ = big_receipt
    strong = receipt["tests"]["CPI:DGS2"]
    assert strong["label"] == "DESCRIPTIVE_ONLY"
    assert strong["reasons"] == []
    flip = receipt["tests"]["NFP:DGS2"]
    assert flip["label"] == "NOT_IDENTIFIED"
    assert flip["reasons"] == ["sign_flip"]
    b1 = flip["eras"]["2010s"]["beta_bp_per_sd"]
    b2 = flip["eras"]["2021+"]["beta_bp_per_sd"]
    assert b1 > 2.0 and b2 < -2.0
    # the ONLY failed condition is the sign: both eras clear on their own
    assert flip["eras"]["2010s"]["clears"] is True
    assert flip["eras"]["2021+"]["clears"] is True


def test_label_requires_40_per_era(tmp_path):
    periods = _month_range("2009-01", "2019-12") + _month_range("2021-01", "2023-06")
    core = {p: (0.0 if i % 2 == 0 else 1.0) for i, p in enumerate(periods)}
    # bridge the skipped 2020 so 2021-01 has a benchmark
    core["2020-12"] = 1.0
    core_days = {p: _cpi_day(p) for p in periods}
    core_days["2020-12"] = "2020-12-10"
    rng = np.random.default_rng(41)
    bdays = pd.bdate_range("2008-12-01", "2023-08-31")
    day_to_p = {core_days[p]: p for p in periods}
    dgs2_inc = np.zeros(len(bdays))
    for i, d in enumerate(bdays):
        p = day_to_p.get(d.strftime("%Y-%m-%d"))
        if p is not None:
            j = periods.index(p)
            x = (core[p] - core[periods[j - 1]]) / _SC
            dgs2_inc[i] = (3.0 * x + rng.normal(0.0, 0.05)) / 100.0
    series = {"DGS2": pd.Series(2.0 + np.cumsum(dgs2_inc), index=bdays)}
    for name in ("DGS10", "DFII10", "T10YIE"):
        series[name] = pd.Series(np.linspace(2.0, 3.0, len(bdays)), index=bdays)
    receipt, _ = _small_world(tmp_path, periods, core=core,
                              core_days=core_days, series=series)
    blk1 = receipt["tests"]["CPI:DGS2"]["eras"]["2010s"]
    blk2 = receipt["tests"]["CPI:DGS2"]["eras"]["2021+"]
    assert blk1["n"] >= 40 and blk1["clears"] is True
    assert blk2["n"] == 30 and blk2["clears"] is True
    assert receipt["tests"]["CPI:DGS2"]["label"] == "NOT_IDENTIFIED"
    assert receipt["tests"]["CPI:DGS2"]["reasons"] == ["n_below_40:2021+"]


def test_degenerate_design_not_identified(tmp_path):
    periods = (_month_range("2007-02", "2019-12")
               + _month_range("2021-01", "2021-02"))
    core = {p: (0.0 if i % 2 == 0 else 1.0) for i, p in enumerate(periods)}
    # bridge the skipped 2020 so 2021-01 has a benchmark
    core["2020-12"] = 1.0
    core_days = {p: _cpi_day(p) for p in periods}
    core_days["2020-12"] = "2020-12-10"
    rng = np.random.default_rng(43)
    bdays = pd.bdate_range("2007-01-01", "2021-04-30")
    day_to_p = {core_days[p]: p for p in periods}
    dgs2_inc = np.zeros(len(bdays))
    for i, d in enumerate(bdays):
        p = day_to_p.get(d.strftime("%Y-%m-%d"))
        if p is not None:
            j = periods.index(p)
            x = (core[p] - core[periods[j - 1]]) / _SC
            dgs2_inc[i] = (3.0 * x + rng.normal(0.0, 0.25)) / 100.0
    series = {"DGS2": pd.Series(2.0 + np.cumsum(dgs2_inc), index=bdays)}
    for name in ("DGS10", "DFII10", "T10YIE"):
        series[name] = pd.Series(np.linspace(2.0, 3.0, len(bdays)), index=bdays)
    receipt, _ = _small_world(tmp_path, periods, core=core,
                              core_days=core_days, series=series)
    blk = receipt["tests"]["CPI:DGS2"]["eras"]["2021+"]
    assert blk["n"] == 2
    assert blk["beta_bp_per_sd"] is None
    assert blk["se"] is None and blk["z"] is None
    assert blk["p_normal"] is None and blk["p_holm_normal"] is None
    assert blk["degenerate_reason"] is not None
    assert blk["clears"] is False and blk["borderline"] is False
    assert receipt["tests"]["CPI:DGS2"]["eras"]["2010s"]["clears"] is True
    assert receipt["tests"]["CPI:DGS2"]["label"] == "NOT_IDENTIFIED"
    reasons = receipt["tests"]["CPI:DGS2"]["reasons"]
    for needle in ("n_below_40:2021+", "not_significant:2021+",
                   "degenerate:2021+"):
        assert needle in reasons


def test_budget_declared_only_with_flag_once(tmp_path, monkeypatch):
    world = _big_world()
    events: list[tuple] = []
    ledger = _Recorder()

    class _Ordered(_Recorder):
        def log_declared_budget(self, n, *, family=None, reason=None):
            events.append(("budget",))
            return super().log_declared_budget(n, family=family, reason=reason)

    ordered = _Ordered()
    orig_rt = world["loaders"]["release_target"]

    def rt(series_id, period):
        if not any(e[0] == "rt" for e in events):
            events.append(("rt", series_id, period))
        return orig_rt(series_id, period)

    def _no_default():
        raise AssertionError("default TrialLedger must never be constructed "
                             "in a test run")

    monkeypatch.setattr(x0, "default_trial_ledger", _no_default)
    loaders = dict(world["loaders"])
    loaders["release_target"] = rt
    loaders["trial_ledger"] = lambda: ordered  # injected from the first run on
    root = tmp_path / "root"
    ppi_path, gdp_path = _write_receipts(root)

    receipt = x0.run(root, tmp_path / "out1", loaders=loaders,
                     ppi_dates_path=ppi_path, gdp_dates_path=gdp_path)
    assert ledger.calls == [] and ordered.calls == []
    assert not any(e[0] == "budget" for e in events)
    assert receipt["trial"] == {
        "family": x0.TRIAL_FAMILY, "budget": 8, "declared": False,
    }

    events.clear()
    receipt2 = x0.run(root, tmp_path / "out2", declare_budget=True,
                      loaders=loaders, ppi_dates_path=ppi_path,
                      gdp_dates_path=gdp_path)
    assert len(ordered.calls) == 1
    assert ordered.calls[0] == {
        "n": 8,
        "family": "ric_x0_release_reaction_v1",
        "reason": f"E0 H3 {x0.PROTOCOL_PATH} sha256={x0.PROTOCOL_SHA256}",
    }
    assert events[0] == ("budget",)  # declared before any computation call
    assert receipt2["trial"]["declared"] is True


# ---------------------------------------------------------------------------
# Group B — descriptives, receipt, surface, language, CLI
# ---------------------------------------------------------------------------

def test_headline_slope_descriptive_not_in_holm(big_receipt):
    receipt, _, _ = big_receipt
    for response in x0.RESPONSES:
        for era in ("2010s", "2021+"):
            blk = receipt["descriptive"]["cpi_headline_slope"][response][era]
            assert set(blk) <= {
                "n", "beta_bp_per_sd", "se", "p_normal", "p_t",
                "degenerate_reason",
            }
            assert "p_holm_normal" not in blk and "clears" not in blk
    blk = receipt["descriptive"]["cpi_headline_slope"]["DGS10"]["2010s"]
    assert blk["n"] >= 40
    assert 1.4 < blk["beta_bp_per_sd"] < 2.3  # planted at 1.3 x headline sd
    assert blk["p_t"] < 1e-6
    # the tested CPI:DGS10 statistic (core) must stay unidentified even though
    # the headline descriptive slope is strong
    core_blk = receipt["tests"]["CPI:DGS10"]["eras"]["2010s"]
    assert core_blk["clears"] is False
    assert receipt["tests"]["CPI:DGS10"]["label"] == "NOT_IDENTIFIED"
    assert "headline" not in json.dumps(receipt["tests"])
    # headline day mismatch (2014-06) -> that episode contributes no headline x
    assert receipt["descriptive"]["cpi_headline_slope"]["DGS10"]["2010s"]["n"] == 117


def test_h1_descriptive_only(big_receipt):
    receipt, _, _ = big_receipt
    for tid in x0.TEST_IDS:
        release, resp = tid.split(":")
        for era in ("2010s", "2021+"):
            blk = receipt["descriptive"]["h1"][tid][era]
            assert set(blk) == {"n", "mean_bp", "median_bp", "sd_bp"}
            vals = [e["h1_bp"][resp] for e in receipt["episodes"]
                    if e["release"] == release and e["status"] == "OK"
                    and e["era"] == era and e["h1_bp"][resp] is not None]
            assert blk["n"] == len(vals)
            if vals:
                assert blk["mean_bp"] == pytest.approx(
                    float(np.mean(vals)), abs=2e-6)
                assert blk["median_bp"] == pytest.approx(
                    float(np.median(vals)), abs=2e-6)
                assert blk["sd_bp"] == pytest.approx(
                    float(np.std(vals, ddof=1)), abs=2e-6)
    assert "beta" not in json.dumps(receipt["descriptive"]["h1"])
    assert receipt["descriptive"]["h1"]["CPI:DGS2"]["2010s"]["n"] > 0


def test_tercile_distributions(tmp_path, big_receipt):
    # big world: x takes only two distinct values -> qcut ties -> NOT_COMPUTABLE
    receipt, _, _ = big_receipt
    for tid in x0.TEST_IDS:
        for era in ("2010s", "2021+"):
            assert receipt["descriptive"]["terciles"][tid][era] == {
                "status": "NOT_COMPUTABLE"
            }
    # a continuous world: h0 rises monotonically across surprise terciles
    periods = _month_range("2007-02", "2015-12")
    rng = np.random.default_rng(99)
    core = {periods[0]: 0.0}
    for i in range(1, len(periods)):
        core[periods[i]] = core[periods[i - 1]] + rng.uniform(-2.0, 2.0)
    core_days = {p: _cpi_day(p) for p in periods}
    bdays = pd.bdate_range("2007-01-01", "2016-03-31")
    day_to_p = {core_days[p]: p for p in periods}
    dgs2 = pd.Series(np.linspace(2.0, 3.0, len(bdays)), index=bdays)
    for i, d in enumerate(bdays):
        p = day_to_p.get(d.strftime("%Y-%m-%d"))
        if p is not None:
            s = core[p] - core[periods[periods.index(p) - 1]]
            dgs2.iloc[i] = dgs2.iloc[i - 1] + (2.0 * s + rng.normal(0.0, 0.3)) / 100.0
    series = {"DGS2": dgs2}
    for name in ("DGS10", "DFII10", "T10YIE"):
        series[name] = pd.Series(np.linspace(2.0, 3.0, len(bdays)), index=bdays)
    receipt2, _ = _small_world(tmp_path, periods, core=core,
                               core_days=core_days, series=series)
    bins = receipt2["descriptive"]["terciles"]["CPI:DGS2"]["2010s"]
    assert isinstance(bins, list) and len(bins) == 3
    n_era = receipt2["tests"]["CPI:DGS2"]["eras"]["2010s"]["n"]
    assert sum(b["n"] for b in bins) == n_era
    assert all(b["n"] > 0 for b in bins)
    for a, b in zip(bins, bins[1:]):
        assert a["x_hi"] <= b["x_lo"]
    means = [b["h0_mean_bp"] for b in bins]
    assert means[0] < means[1] < means[2]
    for b in bins:
        assert set(b) == {"n", "x_lo", "x_hi", "h0_mean_bp", "h0_median_bp"}


def test_sign_agreement_wilson(tmp_path, big_receipt):
    receipt, _, _ = big_receipt
    blk = receipt["descriptive"]["sign_agreement"]["CPI:DGS2"]["2010s"]
    lo, hi = wilson_ci(blk["k"], blk["n"])
    assert blk["share"] == pytest.approx(blk["k"] / blk["n"])
    assert blk["wilson95"] == [pytest.approx(lo, abs=2e-6),
                               pytest.approx(hi, abs=2e-6)]
    assert blk["n"] >= 40
    # a crafted world pins k, n and the zero-exclusion count exactly
    periods = _month_range("2007-02", "2010-12")
    core = {p: (0.0 if i % 2 == 0 else 1.0) for i, p in enumerate(periods)}
    core_days = {p: _cpi_day(p) for p in periods}
    bdays = pd.bdate_range("2007-01-01", "2011-02-28")
    day_to_p = {core_days[p]: p for p in periods}
    dgs2 = pd.Series(np.linspace(2.0, 3.0, len(bdays)), index=bdays)
    for i, d in enumerate(bdays):
        p = day_to_p.get(d.strftime("%Y-%m-%d"))
        if p is not None:
            s = core[p] - core[periods[periods.index(p) - 1]]
            move = 0.0 if p == "2010-04" else 2.0 * s  # one exact-zero h0
            dgs2.iloc[i] = dgs2.iloc[i - 1] + move / 100.0
    series = {"DGS2": dgs2}
    for name in ("DGS10", "DFII10", "T10YIE"):
        series[name] = pd.Series(np.linspace(2.0, 3.0, len(bdays)), index=bdays)
    receipt2, _ = _small_world(tmp_path, periods, core=core,
                               core_days=core_days, series=series)
    blk2 = receipt2["descriptive"]["sign_agreement"]["CPI:DGS2"]["2010s"]
    assert blk2["n"] == 11
    assert blk2["k"] == 11  # h0 = 2 * sign-matched surprise everywhere used
    assert blk2["zero_excluded"] == 1
    lo2, hi2 = wilson_ci(11, 11)
    assert blk2["wilson95"] == [pytest.approx(lo2, abs=2e-6),
                                pytest.approx(hi2, abs=2e-6)]


def test_receipt_schema_and_provenance(tmp_path):
    world = _big_world()
    root = tmp_path / "provenance"
    proto = root / x0.PROTOCOL_PATH
    proto.parent.mkdir(parents=True, exist_ok=True)
    proto.write_bytes((ROOT / x0.PROTOCOL_PATH).read_bytes())
    ppi_path, gdp_path = _write_receipts(root)
    out = tmp_path / "out"
    receipt = x0.run(root, out, loaders=world["loaders"],
                     ppi_dates_path=ppi_path, gdp_dates_path=gdp_path)
    assert receipt["schema"] == x0.SCHEMA
    assert receipt["protocol"]["path"] == x0.PROTOCOL_PATH
    assert receipt["protocol"]["sha256"] == x0.PROTOCOL_SHA256
    assert receipt["asof"] == "2026-07-31"
    assert receipt["benchmark_label"] == x0.BENCHMARK_LABEL
    assert receipt["scope_note"] == x0.SCOPE_NOTE
    inputs = receipt["inputs"]
    assert inputs["release_series"] == {
        "tested": {"CPI": "CPILFESL", "NFP": "PAYEMS"},
        "descriptive": {"CPI_HEADLINE": "CPIAUCSL"},
    }
    for name in x0.RESPONSES:
        assert inputs["responses"][name]["last_date"] == "2026-07-31"
        assert inputs["responses"][name]["n_obs"] == len(world["series"][name])
    assert inputs["ppi_dates"]["sha256"] == hashlib.sha256(
        ppi_path.read_bytes()).hexdigest()
    assert inputs["ppi_dates"]["rows"] == 1
    assert inputs["gdp_dates"]["sha256"] == hashlib.sha256(
        gdp_path.read_bytes()).hexdigest()
    assert inputs["gdp_dates"]["rows"] == 1
    assert inputs["tier1_counts"] == {
        "CPI": 0, "NFP": 0, "PCE": 0, "PPI": 2, "GDP_ADVANCE": 0, "FOMC": 3,
    }
    assert receipt["trial"] == {
        "family": "ric_x0_release_reaction_v1", "budget": 8, "declared": False,
    }
    ep_keys = {
        "release", "series", "period", "release_day", "first_print",
        "naive_prior", "surprise_raw", "units", "scale", "x", "era", "status",
        "collided_with", "h0_bp", "h1_bp", "missing_response",
    }
    assert all(set(e) == ep_keys for e in receipt["episodes"])
    assert set(receipt["tests"]) == set(x0.TEST_IDS)
    era_keys = {
        "n", "distinct_years", "beta_bp_per_sd", "se", "z", "p_normal", "p_t",
        "p_holm_normal", "p_holm_t", "clears", "borderline", "degenerate_reason",
    }
    for tid in x0.TEST_IDS:
        block = receipt["tests"][tid]
        assert set(block["eras"]) == {"2010s", "2021+"}
        for era in ("2010s", "2021+"):
            assert set(block["eras"][era]) == era_keys
    assert receipt["family_summary"] == {
        "DESCRIPTIVE_ONLY": 1, "NOT_IDENTIFIED": 7,
    }
    assert set(receipt["descriptive"]) == {
        "cpi_headline_slope", "h1", "terciles", "sign_agreement",
    }
    text = (out / "x0_reaction.json").read_text()
    parsed = json.loads(text)
    assert text == json.dumps(parsed, sort_keys=True, indent=1) + "\n"
    assert "NaN" not in text and "Infinity" not in text

    def _walk(o):
        if isinstance(o, dict):
            for v in o.values():
                yield from _walk(v)
        elif isinstance(o, list):
            for v in o:
                yield from _walk(v)
        elif isinstance(o, float):
            yield o

    assert all(f == round(f, 6) for f in _walk(parsed))


def test_surface_hides_slope_when_not_identified(big_receipt):
    receipt, _, _ = big_receipt
    hidden = receipt["tests"]["NFP:DGS10"]
    assert hidden["label"] == "NOT_IDENTIFIED"
    surf = hidden["surface"]
    assert set(surf) == {"label", "show_slope", "raw_window"}
    assert surf["label"] == "NOT_IDENTIFIED"
    assert surf["show_slope"] is False
    dumped = json.dumps(surf)
    for banned in ("beta", "_se", "p_normal", "p_t", "holm"):
        assert banned not in dumped
    for era in ("2010s", "2021+"):
        assert set(surf["raw_window"][era]) == {"n", "h0_mean_bp", "h0_median_bp"}
        assert surf["raw_window"][era]["n"] == hidden["eras"][era]["n"]
    shown = receipt["tests"]["CPI:DGS2"]["surface"]
    assert shown["show_slope"] is True
    assert shown["label"] == "DESCRIPTIVE_ONLY"


def test_language_guard(big_receipt):
    _, out, _ = big_receipt
    texts = {
        (out / "x0_reaction.json").read_text(),
        (out / "x0_reaction.md").read_text(),
    }
    banned = (
        "consensus", "expectation", "expected", "causal", "caused", "drove",
        "drives", "forecast", "predicts", "signal", "position size",
    )
    md = (out / "x0_reaction.md").read_text()
    assert x0.SCOPE_NOTE in md
    for text in texts:
        stripped = text.replace(x0.SCOPE_NOTE, " ").lower()
        for word in banned:
            assert word not in stripped, f"{word!r} leaked into a receipt"


def test_outputs_only_under_out_dir(tmp_path):
    world = _big_world()
    root = tmp_path / "strict"
    ppi_path, gdp_path = _write_receipts(root)
    out = root / "out"
    x0.run(root, out, loaders=world["loaders"],
           ppi_dates_path=ppi_path, gdp_dates_path=gdp_path)
    files = sorted(str(p.relative_to(root)) for p in root.rglob("*")
                   if p.is_file())
    assert files == [
        "gdp_receipt.json",
        "out/x0_reaction.json",
        "out/x0_reaction.md",
        "ppi_receipt.json",
    ]


def test_cli_main_roundtrip(tmp_path, monkeypatch):
    world = _big_world()
    monkeypatch.setattr(x0, "default_release_target_loader",
                        lambda root: world["loaders"]["release_target"])
    monkeypatch.setattr(x0, "default_periods_loader",
                        lambda: world["loaders"]["periods"])
    monkeypatch.setattr(x0, "default_tier1_dates_loader",
                        lambda p, g: world["loaders"]["tier1_dates"])
    monkeypatch.setattr(x0, "default_response_loader",
                        lambda: world["loaders"]["response"])
    monkeypatch.setattr(x0, "default_input_files", lambda root: [])
    root = tmp_path / "cliroot"
    ppi_path, gdp_path = _write_receipts(root)
    out = tmp_path / "cliout"
    rc = x0.main([
        "--root", str(root), "--out-dir", str(out),
        "--ppi-dates", str(ppi_path), "--gdp-dates", str(gdp_path),
        "--asof", "2025-12-31",
    ])
    assert rc == 0
    assert (out / "x0_reaction.json").is_file()
    assert (out / "x0_reaction.md").is_file()
    data = json.loads((out / "x0_reaction.json").read_text())
    assert data["asof"] == "2025-12-31"
    assert data["trial"]["declared"] is False
    direct = x0.run(root, tmp_path / "direct", asof="2025-12-31",
                    loaders=world["loaders"], ppi_dates_path=ppi_path,
                    gdp_dates_path=gdp_path)
    assert data == json.loads(json.dumps(direct))


def test_ppi_disagreements_listed(tmp_path, monkeypatch):
    from engine.event_window import _fomc_announcement_dates

    def _ts(days):
        return [pd.Timestamp(d) for d in days]

    frame = pd.DataFrame({
        "series": (["CPILFESL"] * 2 + ["PAYEMS"] + ["PCEPI"] + ["PPIFIS"] * 2),
        "period": _ts(["2010-01-01", "2010-02-01", "2010-01-01", "2010-01-01",
                       "2010-01-01", "2010-02-01"]),
        "realtime_start": _ts(["2010-01-01", "2010-02-01", "2010-01-08",
                               "2010-02-05", "2010-01-06", "2010-02-10"]),
        "value": [1.0, 1.0, 130.0, 1.0, 1.0, 1.0],
    })
    disagreements = [{
        "period": "2010-02",
        "ppiaco_first_realtime_start": "2010-03-09",
        "wpsfd49207_first_realtime_start": "2010-03-10",
        "agree": False,
    }]
    ppi_rec = {
        "rows": [
            {
                "period": "2010-01",
                "ppiaco_first_realtime_start": "2010-02-10",
                "wpsfd49207_first_realtime_start": "2010-02-10",
                "agree": True,
            },
            disagreements[0],
        ],
    }
    gdp_rec = {
        "rows": [
            {
                "quarter": "2019Q4",
                "gdp_first_realtime_start": "2020-01-30",
                "gdpc1_first_realtime_start": "2020-01-30",
                "agree": True,
            },
            {
                "quarter": "2013Q1",
                "gdp_first_realtime_start": "2013-04-26",
                "gdpc1_first_realtime_start": "2013-04-27",
                "agree": True,
            },
        ]
    }
    monkeypatch.setattr(x0, "load_vintages", lambda: frame)
    tier1 = x0.default_tier1_dates_loader(ppi_rec, gdp_rec)()
    assert tier1["CPI"] == {"2010-01-01", "2010-02-01"}
    assert tier1["NFP"] == {"2010-01-08"}
    assert tier1["PCE"] == {"2010-02-05"}
    # both disagreeing dates stay in the PPI set
    assert tier1["PPI"] == {"2010-01-06", "2010-02-10",
                            "2010-03-09", "2010-03-10"}
    assert tier1["GDP_ADVANCE"] == {"2020-01-30", "2013-04-26", "2013-04-27"}
    assert tier1["FOMC"] == set(_fomc_announcement_dates())

    # end to end: the receipt lists the receipt's own disagreement rows
    world = _big_world()
    loaders = {k: v for k, v in world["loaders"].items() if k != "tier1_dates"}
    root = tmp_path / "root"
    ppi_path, gdp_path = _write_receipts(root, ppi=ppi_rec, gdp=gdp_rec)
    receipt = x0.run(root, tmp_path / "out", loaders=loaders,
                     ppi_dates_path=ppi_path, gdp_dates_path=gdp_path)
    # SF1: read from the receipt's own rows (the real receipt has no inputs key)
    assert receipt["inputs"]["ppi_date_disagreements"] == ["2010-02"]
    assert receipt["inputs"]["tier1_counts"]["PPI"] == 4
    assert receipt["inputs"]["tier1_counts"]["GDP_ADVANCE"] == 3


def test_gdp_keys_are_pinned_not_suffix_matched(monkeypatch):
    frame = pd.DataFrame({
        "series": ["CPILFESL"], "period": [pd.Timestamp("2010-01-01")],
        "realtime_start": [pd.Timestamp("2010-01-15")], "value": [1.0],
    })
    gdp_rec = {"rows": [{
        "period": "2019Q4",
        "gdp_first_realtime_start": "2020-01-30",
        "gdpc1_first_realtime_start": "2020-01-31",
        "other_realtime_start": "2020-02-03",
    }]}
    monkeypatch.setattr(x0, "load_vintages", lambda: frame)
    tier1 = x0.default_tier1_dates_loader({"rows": []}, gdp_rec)()
    assert tier1["GDP_ADVANCE"] == {"2020-01-30", "2020-01-31"}


def test_input_files_and_tier1_digests_recorded(tmp_path):
    world = _big_world()
    root = tmp_path / "root"
    ppi_path, gdp_path = _write_receipts(root)
    a = root / "data" / "fred" / "A.parquet"
    a.parent.mkdir(parents=True, exist_ok=True)
    a.write_bytes(b"alpha")
    b = root / "data" / "fred_vintage" / "B.parquet"
    b.parent.mkdir(parents=True, exist_ok=True)
    b.write_bytes(b"beta")
    missing = root / "data" / "fred" / "absent.parquet"
    loaders = dict(world["loaders"])
    loaders["input_files"] = lambda r: [a, b, missing]
    receipt = x0.run(root, tmp_path / "out", loaders=loaders,
                     ppi_dates_path=ppi_path, gdp_dates_path=gdp_path)
    import hashlib
    assert receipt["inputs"]["files"] == [
        {"path": "data/fred/A.parquet",
         "sha256": hashlib.sha256(b"alpha").hexdigest()},
        {"path": "data/fred_vintage/B.parquet",
         "sha256": hashlib.sha256(b"beta").hexdigest()},
    ]
    digests = receipt["inputs"]["tier1_digests"]
    assert set(digests) == set(x0.TIER1_KEYS)
    tier1 = world["loaders"]["tier1_dates"]()
    for key in x0.TIER1_KEYS:
        assert digests[key] == x0._set_digest(tier1.get(key, set()))
    # SF7: receipt paths are relative to root, never host paths
    assert receipt["inputs"]["ppi_dates"]["path"] == x0._rel(ppi_path, root)
    assert not receipt["inputs"]["ppi_dates"]["path"].startswith("/")
    assert not receipt["inputs"]["gdp_dates"]["path"].startswith("/")
    assert receipt["deviations"] == []


RIGHTS = {"registry_id": "macro.fred.vintages", "licensing": "public_domain",
          "source": "FRED/ALFRED (St. Louis Fed)"}


def test_receipt_rights_carried_into_output(tmp_path):
    world = _big_world()
    root = tmp_path / "root"
    root.mkdir(parents=True, exist_ok=True)
    ppi_path = root / "ppi_receipt.json"
    gdp_path = root / "gdp_receipt.json"
    ppi_path.write_text(json.dumps({**PPI_RECEIPT, "rights": RIGHTS}))
    gdp_path.write_text(json.dumps(GDP_RECEIPT))
    receipt = x0.run(root, tmp_path / "out", loaders=world["loaders"],
                     ppi_dates_path=ppi_path, gdp_dates_path=gdp_path)
    assert receipt["inputs"]["ppi_dates"]["rights"] == RIGHTS
    # a receipt without a rights stanza reports none, never a guessed licence
    assert receipt["inputs"]["gdp_dates"]["rights"] is None


def test_committed_date_receipts_carry_rights():
    base = ROOT / "research" / "rates_inflation_command" / "seat_20261014" / "x0_inputs"
    for name in ("ppi_release_dates_receipt.json", "gdp_advance_dates_receipt.json"):
        assert json.loads((base / name).read_text())["rights"] == RIGHTS


def test_default_input_files_are_the_eight_opened_files():
    rels = [x0._rel(p, ROOT) for p in x0.default_input_files(ROOT)]
    assert rels == [
        "data/fred_vintage/vintages.parquet",
        "data/fred_vintage/release_targets/CPILFESL_all_vintages.parquet",
        "data/fred_vintage/release_targets/CPIAUCSL_all_vintages.parquet",
        "data/fred_vintage/release_targets/PAYEMS_all_vintages.parquet",
        "data/fred/DGS2.parquet",
        "data/fred/DGS10.parquet",
        "data/fred/DFII10.parquet",
        "data/fred/T10YIE.parquet",
    ]


def test_holm_keeps_m_at_eight_when_a_p_is_missing(monkeypatch):
    orig = x0._slope_stat
    calls = {"n": 0}

    def _stat(pairs):
        out = dict(orig(pairs))
        calls["n"] += 1
        if calls["n"] == 1:  # first (test, era) cell = TEST_IDS[0] / 2010s
            out["p_normal"] = None
            out["p_t"] = None
        return out

    monkeypatch.setattr(x0, "_slope_stat", _stat)
    rng = np.random.default_rng(7)
    eps = []
    for rel in x0.RELEASES:
        for era, year in (("2010s", 2015), ("2021+", 2022)):
            for i in range(50):
                x = float(rng.normal())
                eps.append({
                    "release": rel, "status": x0.STATUS_OK, "era": era,
                    "_day_ts": pd.Timestamp(f"{year}-01-01") + pd.Timedelta(days=i),
                    "x": x,
                    "h0_bp": {r: 0.4 * x + float(rng.normal()) for r in x0.RESPONSES},
                })
    tests = x0._compute_tests(eps)
    first = x0.TEST_IDS[0]
    assert tests[first]["eras"]["2010s"]["p_normal"] is None
    for era in ("2010s", "2021+"):
        raw = {tid: tests[tid]["eras"][era]["p_normal"] for tid in x0.TEST_IDS}
        filled = {tid: (1.0 if p is None else p) for tid, p in raw.items()}
        expect = holm_adjust(filled)
        for tid in x0.TEST_IDS:
            got = tests[tid]["eras"][era]["p_holm_normal"]
            if raw[tid] is None:
                assert got is None
                continue
            assert got == pytest.approx(expect[tid])
    # discriminating: dropping the None (m=7) would give a different adjustment
    raw = {tid: tests[tid]["eras"]["2010s"]["p_normal"] for tid in x0.TEST_IDS}
    shrunk = holm_adjust({t: p for t, p in raw.items() if p is not None})
    smallest = min((t for t in raw if raw[t] is not None), key=lambda t: raw[t])
    assert shrunk[smallest] < tests[smallest]["eras"]["2010s"]["p_holm_normal"]
    assert tests[first]["eras"]["2010s"]["clears"] is False
    assert tests[first]["label"] == "NOT_IDENTIFIED"


def test_protocol_sha_mismatch_fails_closed_before_ledger(tmp_path):
    world = _big_world()
    root = tmp_path / "root"
    ppi_path, gdp_path = _write_receipts(root)
    proto = root / x0.PROTOCOL_PATH
    proto.parent.mkdir(parents=True, exist_ok=True)
    proto.write_bytes(b"drifted protocol\n")
    calls = []

    class _L:
        def log_declared_budget(self, n, family, reason):
            calls.append(n)

    loaders = dict(world["loaders"])
    loaders["trial_ledger"] = lambda: _L()
    with pytest.raises(x0.MissingInput):
        x0.run(root, tmp_path / "out", declare_budget=True, loaders=loaders,
               ppi_dates_path=ppi_path, gdp_dates_path=gdp_path)
    assert calls == []
    assert not (tmp_path / "out").exists()


def test_default_ledger_is_bound_to_root(tmp_path):
    led = x0.default_trial_ledger(tmp_path)
    assert Path(led.path) == tmp_path / "data" / "trial_ledger.jsonl"

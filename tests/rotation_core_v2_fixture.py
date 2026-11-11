"""Synthetic Ken-French-format fixtures for the v2 tests and the in-memory fixture dry run (random returns; no real
data). `edge` plants a regime: on date t, industries in the top third of the fixture's betas get +edge(t) per day and
the bottom third -edge(t) (the beta order is the industry order, so offence/defence legs follow it)."""
from pathlib import Path
import numpy as np
import pandas as pd


def fixture_texts(start="1926-07-01", end="1997-12-31", n_ind=49, seed=7, extra_after=None, edge=None):
    s = pd.bdate_range(start, extra_after or end)
    rng = np.random.default_rng(seed)
    m = rng.normal(0.0003, 0.01, len(s))
    betas = np.linspace(0.5, 1.6, n_ind)
    vw = m[:, None] * betas + rng.normal(0, 0.008, (len(s), n_ind))
    if edge is not None:
        g = np.asarray([edge(t) for t in s], dtype=float)
        k = n_ind // 3
        vw[:, -k:] += g[:, None]; vw[:, :k] -= g[:, None]
    ew = vw + rng.normal(0, 0.003, (len(s), n_ind))
    vw[:300, :6] = -99.99 / 100; ew[:300, :6] = -99.99 / 100        # late-starting industries, as in the real file
    cols = [f"I{i:02d}" for i in range(n_ind)]

    def block(title, X):
        out = [f"  {title}", "," + ",".join(cols)]
        out += [f"{t.strftime('%Y%m%d')}," + ",".join(f"{100 * v:.2f}" for v in row) for t, row in zip(s, X)]
        return out
    lines = ["This file was created synthetically for tests.", ""] + block("Average Value Weighted Returns -- Daily", vw) \
        + ["", ""] + block("Average Equal Weighted Returns -- Daily", ew)
    rf = np.full(len(s), 0.01)
    f = ["synthetic factors", ",Mkt-RF,SMB,HML,RF"] + [f"{t.strftime('%Y%m%d')},{100 * (mm - 0.0001):.2f},0.00,0.00,{r:.3f}"
                                                        for t, mm, r in zip(s, m, rf)]
    return "\n".join(lines) + "\n", "\n".join(f) + "\n"


def make_fixture(d, start="1926-07-01", end="1997-12-31", n_ind=49, seed=7, extra_after=None, edge=None):
    d = Path(d); d.mkdir(parents=True, exist_ok=True)
    ind, fac = fixture_texts(start, end, n_ind, seed, extra_after, edge)
    (d / "49_Industry_Portfolios_Daily.csv").write_text(ind)
    (d / "F-F_Research_Data_Factors_daily.csv").write_text(fac)
    return d


def make_fund_fixture(d, start="1998-12-22", end="2025-12-31", seed=11, edge=None, edge_sign=1.0):
    """Synthetic Yahoo-format parquet files (Date, Adj Close) for SPY, RSP and the SPDR funds. Fund betas rise with
    the list order; `edge` adds edge_sign * edge(t) to the three highest-beta funds and subtracts it from the three
    lowest (edge_sign = -1 reverses the regime on funds: the veto fixture)."""
    import pyarrow as pa, pyarrow.parquet as pq
    d = Path(d); d.mkdir(parents=True, exist_ok=True)
    s = pd.bdate_range(start, end)
    rng = np.random.default_rng(seed)
    m = rng.normal(0.0003, 0.01, len(s))
    funds = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY", "XLRE", "XLC"]
    late = {"XLRE": "2015-10-08", "XLC": "2018-06-19"}
    g = np.asarray([edge(t) for t in s], dtype=float) * edge_sign if edge is not None else np.zeros(len(s))
    series = {"SPY": m, "RSP": m + rng.normal(0, 0.002, len(s))}
    for i, f in enumerate(funds):
        series[f] = m * (0.4 + 0.12 * i) + rng.normal(0, 0.004, len(s))
    for f in ("XLY", "XLRE", "XLC"):      # the highest betas in this fixture
        series[f] = series[f] + g
    for f in ("XLB", "XLE", "XLF"):       # the lowest
        series[f] = series[f] - g
    for t, r in series.items():
        px = 100 * np.cumprod(1 + r)
        keep = s >= pd.Timestamp(late.get(t, start))
        tbl = pa.table({"Date": pa.array(s[keep].to_pydatetime()), "Adj Close": pa.array(px[keep])})
        pq.write_table(tbl, d / f"{t}.parquet")
    return d

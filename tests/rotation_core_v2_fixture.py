"""Synthetic Ken-French-format fixture for the v2 stage-1 dry run (random returns; no real data)."""
from pathlib import Path
import numpy as np
import pandas as pd


def make_fixture(d, start="1926-07-01", end="1997-12-31", n_ind=49, seed=7, extra_after=None):
    d = Path(d); d.mkdir(parents=True, exist_ok=True)
    s = pd.bdate_range(start, extra_after or end)
    rng = np.random.default_rng(seed)
    m = rng.normal(0.0003, 0.01, len(s))
    betas = np.linspace(0.5, 1.6, n_ind)
    vw = m[:, None] * betas + rng.normal(0, 0.008, (len(s), n_ind))
    ew = vw + rng.normal(0, 0.003, (len(s), n_ind))
    vw[:300, :6] = -99.99 / 100; ew[:300, :6] = -99.99 / 100        # late-starting industries, as in the real file
    cols = [f"I{i:02d}" for i in range(n_ind)]
    def block(title, X):
        out = [f"  {title}", "," + ",".join(cols)]
        out += [f"{t.strftime('%Y%m%d')}," + ",".join(f"{100 * v:.2f}" for v in row) for t, row in zip(s, X)]
        return out
    lines = ["This file was created synthetically for tests.", ""] + block("Average Value Weighted Returns -- Daily", vw) \
        + ["", ""] + block("Average Equal Weighted Returns -- Daily", ew)
    (d / "49_Industry_Portfolios_Daily.csv").write_text("\n".join(lines) + "\n")
    rf = np.full(len(s), 0.01)
    f = ["synthetic factors", ",Mkt-RF,SMB,HML,RF"] + [f"{t.strftime('%Y%m%d')},{100 * (mm - 0.0001):.2f},0.00,0.00,{r:.3f}"
                                                        for t, mm, r in zip(s, m, rf)]
    (d / "F-F_Research_Data_Factors_daily.csv").write_text("\n".join(f) + "\n")
    return d

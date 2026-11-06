#!/usr/bin/env python3
"""Meaningful checks of chronology, execution, adjustment and matching."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

import analyze


def bars(n=30):
    ix = pd.date_range("2000-01-01", periods=n, freq="B")
    return pd.DataFrame({"open": 100., "high": 102., "low": 98., "close": 100.,
                         "adjclose": 100., "volume": 1000.}, index=ix)


def run():
    checks = []
    d = bars()
    d.iloc[0, d.columns.get_loc("close")] = 50.
    d.iloc[0, d.columns.get_loc("adjclose")] = 50.
    out = analyze.forward_outcomes(d, np.ones(len(d)), 5)
    assert abs(out.iloc[0].gross) < 1e-12
    checks.append("decision close is not executable entry; next open is used")
    d = bars()
    d.iloc[1, d.columns.get_loc("low")] = 96.
    out = analyze.forward_outcomes(d, np.ones(len(d)), 5)
    assert out.iloc[0].stop_hit == 1 and out.iloc[0].stop_exit_t == 1
    assert np.isclose(out.iloc[0].stop_net20, .97*.999/1.001-1)
    checks.append("entry-session stop is included at fixed signal ATR")
    d = bars()
    d.iloc[2, d.columns.get_loc("open")] = 90.
    d.iloc[2, d.columns.get_loc("low")] = 89.
    out = analyze.forward_outcomes(d, np.ones(len(d)), 5)
    assert np.isclose(out.iloc[0].stop_net20, .90*.999/1.001-1)
    checks.append("opening gap through stop fills at open, not stop")
    d = bars()
    d.iloc[5, d.columns.get_loc("adjclose")] = 110.
    out = analyze.forward_outcomes(d, np.ones(len(d)), 5)
    assert np.isclose(out.iloc[0].gross, .10)
    assert out.iloc[-5:].net20.isna().all()
    checks.append("adjustment factor applied to correct dates; incomplete outcomes unknown")
    d = bars(45)
    d.iloc[25, d.columns.get_loc("high")] = 110.
    d.iloc[30, d.columns.get_loc("low")] = 103.
    d.loc[d.index[26:35], "low"] = 105.
    d.iloc[30, d.columns.get_loc("low")] = 103.
    d.iloc[35, d.columns.get_loc("close")] = 107.
    a = np.full(len(d), 2.)
    reset, p, q = analyze.reset_state(d, a)
    assert reset[35] and p[35] == 25 and q[35] == 30
    for end in (34, 36, 40):
        rr, pp, qq = analyze.reset_state(d.iloc[:end], a[:end])
        assert np.array_equal(reset[:end], rr)
        assert np.array_equal(p[:end], pp) and np.array_equal(q[:end], qq)
    checks.append("peak then trough before decision; prefix invariance")
    # A fresh prior-session peak cannot borrow a trough from before that peak.
    d.iloc[34, d.columns.get_loc("high")] = 112.
    rr, _, _ = analyze.reset_state(d, a)
    assert not rr[35]
    checks.append("pre-peak low cannot masquerade as a post-peak reset")
    x = pd.DataFrame({"cell": ["x"]*12, "net20": np.arange(12)/100,
                      "win": np.ones(12), "stop_net20": np.arange(12)/100,
                      "stop_win": np.ones(12)})
    analyze.add_leave_one_out(x, ["cell"], "test")
    assert np.isclose(x.iloc[0].test_net20, np.arange(1, 12).mean()/100)
    assert np.isclose(x.iloc[11].test_net20, np.arange(11).mean()/100)
    checks.append("comparator excludes the focal observation")
    x = pd.DataFrame({"ticker": ["A"]*4, "date": pd.date_range("2000-01-01", periods=4),
                      "t": [0, 21, 63, 84]})
    assert analyze.nonoverlap(x, 63).t.tolist() == [0, 63]
    checks.append("nonoverlap uses fixed endpoint without reading stop outcomes")
    return {"passed": len(checks), "checks": checks}


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2))
    out = Path(__file__).parent/"results"
    out.mkdir(exist_ok=True)
    (out/"mechanical_verification.json").write_text(json.dumps(result, indent=2))

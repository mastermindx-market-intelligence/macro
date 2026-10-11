"""Q16 baseline reproduction (pre-freeze, TRAINING WINDOW ONLY).

Reproduces the incumbent engine.vol_forecast cone on the licensed panel and reports the
coverage of its naive Gaussian 80% reading (+-1.2816 * sigma_h) using only origins whose
labels matured by the training cutoff. No test-window label is read. Writes
baseline_train.json and appends one RUNS.log record.
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import q16_common as C  # noqa: E402

OUT = C.HERE / "baseline_train.json"
Z80 = 1.2815515655446004


def main() -> dict:
    panel = C.load_panel()
    axis = next(iter(panel.values())).index
    te_pos = int(np.searchsorted(axis.values, np.datetime64(C.TRAIN_END_DATE), side="right") - 1)
    res = {"assets": {}, "axis_first": str(axis[0].date()), "axis_last": str(axis[-1].date()),
           "n_axis": int(len(axis)), "train_end_pos": te_pos,
           "train_end_date": str(axis[te_pos].date()), "horizon": C.HORIZON,
           "nominal": 1 - C.ALPHA, "window": "training only (labels matured <= train_end)"}
    for a, close in panel.items():
        fr = C.asset_frame(close)
        pos = np.arange(len(fr))
        matured = pos + C.HORIZON <= te_pos
        ok = matured & fr["sigma_h"].notna().values & fr["y"].notna().values
        s = (fr["y"].values[ok] / fr["sigma_h"].values[ok])
        cov = float(np.mean(np.abs(s) <= Z80))
        res["assets"][a] = {"n_train_origins": int(ok.sum()),
                            "honest_train_blocks": int(ok.sum() // C.HORIZON),
                            "naive_gauss80_coverage_train": round(cov, 4),
                            "train_abs_score_q80": round(float(np.quantile(np.abs(s), 0.8)), 4),
                            "n_test_origins_available": int(((pos > te_pos) &
                                                             fr["y"].notna().values &
                                                             fr["sigma_h"].notna().values).sum())}
    return res


if __name__ == "__main__":
    rc = 0
    outputs = {}
    try:
        r = main()
        OUT.write_text(json.dumps(r, indent=2, sort_keys=True) + "\n")
        outputs = {OUT.name: C.sha256_file(OUT)}
        print(json.dumps(r, indent=1, sort_keys=True))
    except Exception:
        traceback.print_exc()
        rc = 1
    C.append_run([sys.executable] + sys.argv, rc, C.input_hashes(), outputs,
                 note="baseline reproduction, pre-freeze, training window only")
    sys.exit(rc)

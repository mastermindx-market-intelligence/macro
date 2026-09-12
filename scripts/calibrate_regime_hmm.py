"""Nightly calibration for the continuous-regime HMM (v1, L2).

Fits the 4-state informed Gaussian HMM (engine/regime_hmm.py) on the committed axis-score
history and writes data/regime/hmm_latest.json. This runs in the CALIBRATION lane (like the
ladder/business-cycle calibrations), NOT the render or engine.run path — engine/run.py only
READS the JSON as a display-only leaf (so a ~1s fit never lands in the fast render, per the
plan's compute-budget rule §S5).

DISPLAY-ONLY: the output does not drive any weight, size, or gross dial. It is gated behind
`engine.regime_fwd.enabled` when consumed, and scored promotion waits on validate_regime_fwd.py.

Run:  python -m scripts.calibrate_regime_hmm
"""
from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from io import BytesIO
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.regime_hmm import fit_regime_hmm  # noqa: E402
from lib import config  # noqa: E402


def main() -> int:
    p = config.data_dir() / "regime"
    hist = p / "regime_history.parquet"
    if not hist.exists():
        print(f"error: {hist} not found (run engine.run first)", file=sys.stderr)
        return 1
    # Read once: legacy HMM and additive research bind the SAME history bytes.
    history_bytes = hist.read_bytes()
    df = pd.read_parquet(BytesIO(history_bytes))
    out = fit_regime_hmm(df)
    if out is None:
        print("error: HMM fit returned None (insufficient history?)", file=sys.stderr)
        return 1
    # Additive, bounded research remains in this existing calibration lane.
    # No page/render fit, second writer, forecast ledger or allocation effect.
    try:
        from engine.regime_research import build_research
        out["transition_research"] = build_research(
            config.data_dir(), analysis_cutoff=datetime.now(timezone.utc),
            history_snapshot=(df, {"path": "data/regime/regime_history.parquet",
                                  "sha256": hashlib.sha256(history_bytes).hexdigest(),
                                  "status": "present", "availability_basis": "latest_revised_store_not_vintage_attested"}))
    except Exception as exc:
        # Preserve the legacy owner's output; do not publish a fake new forecast.
        # No re-import from the failed optional dependency: even an import error
        # must leave the legacy calibration publishable. This deliberately unsealed
        # diagnostic is rejected as a forecast by the consumer.
        out["transition_research"] = {
            "schema": "regime_one.integrated_research.v1", "status": "UNAVAILABLE",
            "source_basis": "LATEST_REVISED_EXPLORATORY", "reason": "calibration_research_failed",
            "error_type": type(exc).__name__, "analysis_cutoff": datetime.now(timezone.utc).isoformat(),
            "forecast": None, "historical_comparisons": None, "evaluation": None,
            "authority": {"can_rank": False, "can_size": False, "can_gate": False,
                          "can_trade": False, "can_originate_signal": False, "can_execute": False},
            "forward_ledger_advanced": False,
            "historical_live_issuance_claimed": False, "empirically_calibrated": False}
        print("::warning title=regime-transition-research::Additive research unavailable; legacy HMM retained", flush=True)
    dst = p / "hmm_latest.json"
    dst.write_text(json.dumps(out, indent=2, default=str))
    rp = out["regime_probs"]
    print(f"wrote {dst}: {out['asof']} modal={out['modal_quad']} "
          f"P={ {k: round(v, 2) for k, v in rp.items()} } "
          f"hazard={out['hazard']} dwell={out['expected_dwell_months']}mo", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

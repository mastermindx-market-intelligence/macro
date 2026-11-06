"""Literal original owner functions at 84f1b7287c8f7298e502eb67949f01ee7c40ef1e."""
from __future__ import annotations
from datetime import date
from pathlib import Path
import json, logging
from lib import config
log = logging.getLogger(__name__)

def _signal_calibration() -> dict:
    """The backtested signal-PRECISION verdict from scripts.calibrate_baskets
    (data/strategies/baskets_calibration.json — the 27y SPDR-sector proxy kill-test).
    Display/grade only, additive — returns {} if absent so the page falls back to the
    honest 'descriptive' framing. The signal LOGIC (_label) is shared across regions, so
    the US-proxy verdict is cited cross-market, exactly as engine.narrative_rotation cites
    its 27y phase0 (HK already falls back to the US sector run)."""
    try:
        p = config.data_dir() / "strategies" / "baskets_calibration.json"
        d = json.loads(p.read_text()) if p.exists() else {}
        return d.get("verdict", {}) if isinstance(d, dict) else {}
    except Exception:  # noqa: BLE001 — grading is enrichment, never fatal
        return {}

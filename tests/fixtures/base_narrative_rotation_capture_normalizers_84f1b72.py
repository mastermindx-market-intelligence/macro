"""Literal original owner functions at 84f1b7287c8f7298e502eb67949f01ee7c40ef1e."""
from __future__ import annotations
from datetime import date
from pathlib import Path
import json, logging
from lib import config
log = logging.getLogger(__name__)

def _sizing_calibration() -> dict:
    """The book-level vol-target SIZING verdict from scripts.calibrate_baskets (the 27y
    SPDR-sector proxy). Display-framed; the signal LOGIC is shared cross-region so the
    US-proxy verdict is cited cross-market (as the phase0 already is). {} if absent."""
    try:
        p = config.data_dir() / "strategies" / "baskets_calibration.json"
        d = json.loads(p.read_text()) if p.exists() else {}
        return d.get("sizing", {}) if isinstance(d, dict) else {}
    except Exception:  # noqa: BLE001
        return {}

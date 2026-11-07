"""Literal original owner functions at 84f1b7287c8f7298e502eb67949f01ee7c40ef1e."""
from __future__ import annotations
from datetime import date
from pathlib import Path
import json, logging
from lib import config
log = logging.getLogger(__name__)

def _resolve_fusion_calibration(rec: dict) -> tuple[float, float]:
    """Legacy acquisition only; retain the established fail-soft calibration rules."""
    key, family, state = fusion_calibration_key(rec)
    try:
        from engine.conditions import sector_macro_beta
        beta = sector_macro_beta(key)
    except Exception:  # noqa: BLE001
        beta = 0.0
    try:
        from engine.cycles import risk_size_mult
        size_mult = float(risk_size_mult(state, family))
    except Exception:  # noqa: BLE001
        size_mult = 1.0
    return beta, size_mult

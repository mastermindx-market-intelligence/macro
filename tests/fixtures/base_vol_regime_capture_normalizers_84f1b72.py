"""Literal original owner functions at 84f1b7287c8f7298e502eb67949f01ee7c40ef1e."""
from __future__ import annotations
from datetime import date
from pathlib import Path
import json, logging
from lib import config
log = logging.getLogger(__name__)

def load_overlay_gate(data_dir: Path | None = None) -> dict:
    """Read data/vol_regime/basket_overlay_gate.json — the additive-value verdict for the
    REGIME-STATE caution haircut (audit #30 firewall). The regime-state caution leg binds
    real basket gross ONLY when its own OOS study says it adds value over the mechanical
    vol-target: ``regime_marginal_over_voltarget == True``. Absent/malformed -> a CLOSED
    gate (caution is display-only), matching the validate-before-weight default. The
    mechanical vol-target is a documented sizing mechanism, not gated by this file."""
    try:
        from lib import config
        p = (data_dir or config.data_dir()) / OVERLAY_GATE_PATH
        if p.exists():
            g = json.loads(p.read_text())
            if isinstance(g, dict):
                return g
    except Exception as e:  # noqa: BLE001 — a missing/broken gate must never break the build
        log.warning("vol_regime: overlay gate read failed (%s) — caution display-only", e)
    return {"regime_marginal_over_voltarget": False, "live_overlay_helps": False,
            "note": "missing/unreadable overlay gate -> caution display-only (validate-first)"}

def published_snapshot(data_dir: Path | None = None, site_dir: Path | None = None) -> dict:
    """Load the freshest PUBLISHED regime snapshot for a consumer (baskets / per-stock ladder /
    run.py). Tries, in order: site/vol/regime.json['snapshot'] (build_vol_regime output),
    data/regime/latest.json['vol_regime'] (run.py mirror). Returns {} when none is present —
    a consumer then applies NO overlay (inert), never imputing a regime. Pure read; guarded."""
    try:
        from lib import config
        sdir = site_dir if site_dir is not None else (config.ROOT / config.load()["storage"]["site_dir"])
        p = Path(sdir) / "vol" / "regime.json"
        if p.exists():
            snap = (json.loads(p.read_text()) or {}).get("snapshot")
            if isinstance(snap, dict) and snap:
                return snap
    except Exception as e:  # noqa: BLE001 — a missing/broken file must never break the build
        log.warning("vol_regime: published site snapshot read failed (%s)", e)
    try:
        from lib import config
        ddir = data_dir if data_dir is not None else config.data_dir()
        p = Path(ddir) / "regime" / "latest.json"
        if p.exists():
            snap = (json.loads(p.read_text()) or {}).get("vol_regime")
            if isinstance(snap, dict) and snap:
                return snap
    except Exception as e:  # noqa: BLE001
        log.warning("vol_regime: latest.json vol_regime read failed (%s)", e)
    return {}

def overlay_config() -> dict:
    """Merge engine.vol_regime_overlay from config over OVERLAY_DEFAULTS (graceful)."""
    try:
        from lib import config
        c = (config.load().get("engine", {}) or {}).get("vol_regime_overlay") or {}
    except Exception:  # noqa: BLE001
        c = {}
    return {**OVERLAY_DEFAULTS, **(c if isinstance(c, dict) else {})}

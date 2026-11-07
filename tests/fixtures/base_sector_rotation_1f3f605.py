"""Literal rotation stamp at Macro 1f3f605; test-only baseline."""
from pathlib import Path
import json
import logging
from lib import config
log = logging.getLogger(__name__)

def _stamp_rotation_context(payload: dict, *, site_root=None, today=None) -> None:
    """SIC-D-B02: stamp a backend-stamped, guarded rotation context into the cycles payload.

    Adds top-level ``rotation_context`` (schema sector_cycles.rotation_context.v1) and
    ``rotation_alignment_version``; every other payload byte is untouched.  The page
    receiver (templates/sector_cycles.js loadRotation) can consume this block; its
    raw marketdata read path is unchanged until the receiver is switched over, so
    the stamp is additive, not a replacement (RB02 #3).

    Events (site/marketdata/rotation_events.json): schema must be rotation_events.v1
    and ok is True, else invalid_payload; alignment compares the payload's top-level
    ``as_of`` — the SAME field the Central measured adapter compares
    (engine/leadership_rotation_context.py, measured_group_read:
    rotation_payload["as_of"] != session_end).  ``active`` is copied only when
    aligned and list-typed.

    Fragmentation (site/marketdata/sector_fragmentation.json): alignment compares its
    top-level ``as_of`` (written by engine/sector_fragmentation.py compute() as the
    max per-sector ``asof`` bar date); per-sector rows are copied only when aligned.

    Missing files → missing_input.  Any exception in here degrades the whole block
    to {"schema", "status": "unavailable", "reason": "projection_error"} — never
    breaks the rest of the cycles build.
    """
    import datetime as _dt

    def _aligned_copy(align: dict, ok_payload, data_key) -> dict:
        out = dict(align)
        out[data_key] = None
        if align["status"] == "aligned" and isinstance(ok_payload.get(data_key), (list, tuple)):
            out[data_key] = list(ok_payload[data_key])
        return out

    try:
        from engine import sector_generation_guard as _sgg

        root = Path(site_root) if site_root is not None else (
            config.ROOT / config.load().get("storage", {}).get("site_dir", "site"))
        today = today if today is not None else _dt.datetime.now(_dt.timezone.utc).date()
        consumer = (payload.get("meta") or {}).get("asOf")

        ctx: dict = {"schema": "sector_cycles.rotation_context.v1"}

        # --- events ---
        ev_path = root / "marketdata" / "rotation_events.json"
        try:
            ev = json.loads(ev_path.read_text(encoding="utf-8")) if ev_path.exists() else None
        except Exception:  # noqa: BLE001 — unreadable is missing, not fatal
            ev = None
        if ev is None:
            ctx["events"] = {"status": "missing_input", "reason": "missing_input",
                             "artifact_session": None,
                             "consumer_session": _sgg.parse_session(consumer).isoformat()
                             if _sgg.parse_session(consumer) else None,
                             "clock": "settled_daily_session", "active": None}
        elif ev.get("schema") != "rotation_events.v1" or ev.get("ok") is not True:
            ctx["events"] = {"status": "invalid_payload", "reason": "invalid_payload",
                             "artifact_session": None,
                             "consumer_session": _sgg.parse_session(consumer).isoformat()
                             if _sgg.parse_session(consumer) else None,
                             "clock": "settled_daily_session", "active": None}
        else:
            ctx["events"] = _aligned_copy(
                _sgg.session_alignment(ev.get("as_of"), consumer, today=today), ev, "active")

        # --- fragmentation ---
        fr_path = root / "marketdata" / "sector_fragmentation.json"
        try:
            fr = json.loads(fr_path.read_text(encoding="utf-8")) if fr_path.exists() else None
        except Exception:  # noqa: BLE001
            fr = None
        if fr is None:
            ctx["fragmentation"] = {"status": "missing_input", "reason": "missing_input",
                                    "artifact_session": None,
                                    "consumer_session": _sgg.parse_session(consumer).isoformat()
                                    if _sgg.parse_session(consumer) else None,
                                    "clock": "settled_daily_session", "sectors": None}
        else:
            ctx["fragmentation"] = _aligned_copy(
                _sgg.session_alignment(fr.get("as_of"), consumer, today=today), fr, "sectors")

        payload["rotation_context"] = ctx
        payload["rotation_alignment_version"] = 1
    except Exception as e:  # noqa: BLE001 — projection never breaks the build
        log.warning("sector_cycles: rotation_context projection failed (%s) — stamped unavailable", e)
        payload["rotation_context"] = {"schema": "sector_cycles.rotation_context.v1",
                                       "status": "unavailable", "reason": "projection_error"}
        payload["rotation_alignment_version"] = 1

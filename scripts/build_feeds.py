"""Assemble site/feeds/ — the machine-consumable contract plane (R2-only).

The 2026-07-02 semis-breakdown incident (signals.md §4 item 5) showed the
Mastermind bot acting blind on exactly the products the dashboard had already
computed: the risk_radar snapshot said caution/growth-scare with rising
pullback odds, but only latest.json's rosier top-levels were in the bot's
vendored sparse set. This script publishes the handoff-H4 artifact list to a
single flat directory that ships to R2 via scripts/publish_r2.py (dir
`feeds`), where the per-dir `_manifest.json` is the authoritative name list
bulk consumers sync against.

Contract hygiene (research/PERCEPTION_CONTRACTS.md): every JSON artifact
carries `asof` = TRUE data timestamp (never build time; build time lives in
feeds_meta.json:generated_utc). Copies are byte-verbatim — the source engine
owns the schema; this script never reshapes what it copies. Each artifact is
independent: a missing source skips that feed (logged), never fails the build.

Run AFTER the engine + site builders in the daily lane, BEFORE publish_r2.
Usage: python -m scripts.build_feeds
"""
from __future__ import annotations

import json
import logging
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import config  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("build_feeds")

SCHEMA_VERSION = 1
EVENT_HORIZON_D = 21


def _feeds_dir() -> Path:
    p = config.ROOT / config.load()["storage"]["site_dir"] / "feeds"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _read_json(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text()) if p.exists() else None
    except Exception as e:  # noqa: BLE001
        log.warning("unreadable json %s: %s", p, e)
        return None


def _write_json(out: Path, name: str, obj) -> Path:
    p = out / name
    with open(p, "w") as fh:
        json.dump(obj, fh, indent=2, default=str)
    return p


def _asof_of(obj) -> str | None:
    # "as_of" is the pre-standardization spelling still used by some producers
    # (e.g. group_flow validation_meta) — read both, WRITE only "asof" (H6).
    if isinstance(obj, dict):
        for k in ("asof", "as_of", "date"):
            v = obj.get(k)
            if isinstance(v, str) and v:
                return v[:10]
    return None


def build(*, render_only: bool = False, output_dir: Path | None = None) -> dict:
    """Assemble every feed; returns {artifact_name: asof|None} for the meta."""
    out = _feeds_dir() if output_dir is None else Path(output_dir)
    if not out.is_dir() or out.is_symlink():
        raise ValueError("feed output must be an existing real directory")
    data = config.data_dir()
    meta: dict[str, dict] = {}

    def note(name: str, asof: str | None, source: str):
        p = out / name
        meta[name] = {"asof": asof, "source": source,
                      "bytes": p.stat().st_size if p.exists() else None}

    def copy(src: Path, name: str, asof: str | None, source: str | None = None):
        if not src.exists():
            log.warning("feed %s: source absent (%s) — skipped", name, src)
            return
        shutil.copyfile(src, out / name)
        note(name, asof, source or str(src.relative_to(config.ROOT)))

    latest = _read_json(data / "regime" / "latest.json") or {}

    # 1. risk_radar snapshot — published VERBATIM (schema risk_radar.v2 carries
    #    its own asof); the leg the bot's sparse set stripped during the incident.
    rr = latest.get("risk_radar")
    if isinstance(rr, dict) and rr.get("state") is not None:
        _write_json(out, "risk_radar.json", rr)
        note("risk_radar.json", _asof_of(rr), "data/regime/latest.json:risk_radar")
    else:
        log.warning("feed risk_radar.json: no radar snapshot in latest.json — skipped")

    # 2-4. verbatim copies of the graded logs / validation meta
    froth_asof = None
    fl = data / "froth_fragility" / "log.jsonl"
    if fl.exists():
        try:
            lines = fl.read_text().splitlines()
            froth_asof = _asof_of(json.loads(lines[-1])) if lines else None
        except Exception:  # noqa: BLE001
            froth_asof = None
    copy(fl, "froth_fragility_log.jsonl", froth_asof)

    dl = data / "dislocation" / "state_log.parquet"
    disl_asof = None
    if dl.exists():
        try:
            import pandas as pd
            df = pd.read_parquet(dl)
            disl_asof = (str(df["date"].iloc[-1])[:10] if "date" in df.columns
                         else str(df.index.max())[:10])
        except Exception:  # noqa: BLE001
            disl_asof = None
    copy(dl, "dislocation_state_log.parquet", disl_asof)

    gf = data / "group_flow" / "validation_meta.json"
    copy(gf, "group_flow_validation_meta.json", _asof_of(_read_json(gf)))

    # 5. the RRG plane (268 subsectors x 8 timeframes) — already a contract on
    #    site/marketdata; mirrored here so the feeds manifest is one-stop.
    sr = config.ROOT / config.load()["storage"]["site_dir"] / "marketdata" / "subsector_rotation.json"
    copy(sr, "subsector_rotation.json", _asof_of(_read_json(sr)), "site/marketdata/subsector_rotation.json")

    # 6. event calendar — first persistent artifact (engine/event_calendar.py was
    #    render-inline only). asof = the schedule-pull date: calendar data IS
    #    forward-looking; freshness means "assembled today".
    if render_only:
        # The default normal feed builder retains acquisition behavior. The
        # explicit durable render cannot obtain a calendar release/auction feed:
        # retain an existing calendar's actual bytes/asof, or omit it honestly.
        retained_calendar = out / "event_calendar.json"
        retained_value = _read_json(retained_calendar)
        if isinstance(retained_value, dict):
            # Preserve the incumbent producer provenance as well as the old
            # payload/asof. This invocation did not pull or reassemble it.
            note("event_calendar.json", _asof_of(retained_value), "engine/event_calendar.py")
    else:
        try:
            from engine import event_calendar as ec
            today = datetime.now(timezone.utc).date()
            cal = {
                "schema_version": SCHEMA_VERSION,
                "asof": today.isoformat(),
                "horizon_days": EVENT_HORIZON_D,
                "us_macro": ec.us_macro_events(today, EVENT_HORIZON_D),
                "high_impact": ec.high_impact_strip(today, EVENT_HORIZON_D),
                "commodity": ec.commodity_events(today, EVENT_HORIZON_D),
                "is_context_only": True,
            }
            _write_json(out, "event_calendar.json", cal)
            note("event_calendar.json", cal["asof"], "engine/event_calendar.py")
        except Exception as e:  # noqa: BLE001
            log.warning("feed event_calendar.json failed: %s — skipped", e)
    # 7. intl spillover — the per-market intl radars (engine/risk_radar_intl)
    #    were RENDER-INLINE only (computed inside build_china/build_hk, never
    #    persisted); this makes them a durable plane. snapshot() never raises
    #    and reads the committed stores, so a thin data day just degrades.
    try:
        from engine.risk_radar_intl import PROFILES
        from engine.risk_radar_intl import snapshot as intl_snapshot
        markets = {}
        for key, profile in PROFILES.items():
            m = intl_snapshot(profile)
            if isinstance(m, dict) and m.get("state") is not None:
                markets[key] = m
        if markets:
            spill = {
                "schema_version": SCHEMA_VERSION,
                "asof": max(filter(None, (_asof_of(m) for m in markets.values())),
                            default=None),
                "markets": markets,
                "note": ("per-market risk_radar_intl snapshots (same _trajectory/"
                         "state grammar as the US radar); market absent = radar "
                         "not computable that day"),
            }
            _write_json(out, "intl_spillover.json", spill)
            note("intl_spillover.json", spill["asof"], "engine/risk_radar_intl.py")
        else:
            log.warning("feed intl_spillover.json: no intl radar snapshots — skipped")
    except Exception as e:  # noqa: BLE001
        log.warning("feed intl_spillover.json failed: %s — skipped", e)

    # 8. per-sector breadth (handoff H5) — latest row of the collector's
    #    sector split (collectors/breadth.py:compute_sectors).
    sb = data / "breadth" / "sector_breadth.parquet"
    if sb.exists():
        try:
            import pandas as pd
            df = pd.read_parquet(sb)
            row = df.iloc[-1]
            sectors: dict[str, dict] = {}
            for col, v in row.items():
                sector, metric = str(col).rsplit("|", 1)
                if pd.isna(v):
                    continue
                d = sectors.setdefault(sector, {})
                d[metric if metric != "n" else "n_members"] = (
                    int(v) if metric == "n" else round(float(v), 1))
            obj = {
                "schema_version": SCHEMA_VERSION,
                "asof": str(df.index[-1])[:10],
                "universe": "S&P 500 (current members; survivorship caveat)",
                "ma_windows": [50, 200],
                "sectors": sectors,
            }
            _write_json(out, "sector_breadth.json", obj)
            note("sector_breadth.json", obj["asof"], "data/breadth/sector_breadth.parquet")
        except Exception as e:  # noqa: BLE001
            log.warning("feed sector_breadth.json failed: %s — skipped", e)
    else:
        log.info("feed sector_breadth.json: parquet not yet collected — skipped")

    # 9. world_state — Neural Web N1 composed blackboard (byte-verbatim copy).
    #    The envelope sibling keys are already in-place on the source JSON, so
    #    a verbatim copy preserves the full contract shape unchanged.
    ws = data / "neuralweb" / "world_state.json"
    copy(ws, "world_state.json", _asof_of(_read_json(ws)), "data/neuralweb/world_state.json")

    # 10. nw_mastermind_context — Neural Web → Mastermind bridge artifact.
    #     Canonical lives at data/neuralweb/mastermind_context.json (git).
    #     Site copy at site/neuralwebdata/mastermind_context.json (git, zero-touch transport).
    #     This feeds copy lands in site/feeds/ for the R2 machine plane.
    #     Byte-verbatim copy preserves the envelope contract.
    mc = data / "neuralweb" / "mastermind_context.json"
    copy(mc, "nw_mastermind_context.json", _asof_of(_read_json(mc)), "data/neuralweb/mastermind_context.json")

    # 11. International native generation, on this incumbent R2-only machine
    # plane. Never reshape the producer's bytes or replace the full manifest
    # from a partial International fixture. Exact source files are independent
    # of any user account, question, Saved record or authenticated read.
    try:
        from lib.intl_generation_publication import read_generation_publication, publish_unavailable_generation
        publication = read_generation_publication(data_root=data)
        if publication.get("status") != "ready":
            # Invalidate a stale current selector when its dependent immutable
            # bytes are missing/corrupt. No old/current generation fallback.
            publish_unavailable_generation(data_root=data)
            publication = read_generation_publication(data_root=data)
        descriptor = publication.get("descriptor")
        if type(descriptor) is not dict:
            raise ValueError("International descriptor unavailable")
        source_dir = data / "intl/publication/generations"
        if descriptor.get("state") == "ready":
            name = descriptor["artifact_name"]
            copy(source_dir / name, name, None, "data/intl/publication/generations/" + name)
            generation_contract = json.loads(publication["artifact_bytes"])
            points = generation_contract.get("policy_points_ref")
            if points is not None:
                point_name = points["artifact_name"]
                copy(source_dir / point_name, point_name, None, "data/intl/publication/generations/" + point_name)
        # Preserve the original immutable descriptor witness as well as the
        # mutable current selector; neither acquires a build-time asof.
        current = source_dir / "intl_generation_current.json"
        import hashlib
        witness = "intl_generation_descriptor_" + hashlib.sha256(current.read_bytes()).hexdigest() + ".json"
        copy(source_dir / witness, witness, None, "data/intl/publication/generations/" + witness)
        copy(current, "intl_generation_current.json", None,
             "data/intl/publication/generations/intl_generation_current.json")
    except Exception as exc:
        log.warning("International native generation feed unavailable (%s)", type(exc).__name__)

    _write_json(out, "feeds_meta.json", {
        "schema_version": SCHEMA_VERSION,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "artifacts": meta,
        "note": ("asof = TRUE data timestamp per artifact, never build time; "
                 "see research/PERCEPTION_CONTRACTS.md"),
    })
    log.info("feeds assembled: %d artifacts -> %s", len(meta), out)
    return {k: v.get("asof") for k, v in meta.items()}


if __name__ == "__main__":
    build()
    raise SystemExit(0)

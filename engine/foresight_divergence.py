"""Narrative-to-Money Divergence Board — W1a of the Institutional Sector Intelligence
Masterplan (research/INSTITUTIONAL_SECTOR_INTELLIGENCE_MASTERPLAN_BY_FABLE.md §3 W1a).

Per-theme rank-percentile of NARRATIVE legs vs MONEY legs to surface the four quadrants:
  hype-risk         narrative high, money quiet  — crowd ahead of capital
  confirmed         both high                    — full confirmation
  hidden-opportunity money high, narrative quiet — capital arriving before narrative (the claim)
  ignore            both quiet                   — nothing actionable

Anti-laundering:
  • Each axis must have ≥1 live leg, else the theme is excluded from the cross-section.
  • The cross-section must contain ≥MIN_THEMES_FOR_RANK themes (both axes live) before any
    quadrant label is published — a rank-percentile over <6 themes is noise.
  • New confirmers never change cascade stage logic (house rule).
  • Evidence-class: narrative legs are TEXT_CLASS (≤50); money legs are FINGERPRINT_CLASS (≤60).

Forward-graded ledger (data/foresight/divergence_log.jsonl):
  • One row per (theme, asof) when quadrant == "hidden-opportunity".
  • Dedup by (theme, asof) — idempotent across same-day re-runs.
  • Weekly heartbeat for unchanged quadrant.
  • PIT member snapshot at log time (not today's config).
  • Transition alert (hidden-opportunity → confirmed) emitted as a separate row type.

Nothing here reaches stock_score, spotlight, or regime.classify. Display-only until
the forward-graded ledger clears Phase-0 validation (house rule).
"""
from __future__ import annotations

import copy
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from engine.ledger_lane import nightly_advance_enabled as _ledger_advance_enabled
from lib import config

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

# Mirror LEG_MIN_COVERAGE=6 in foresight_earliness.py — a rank-percentile over <6
# valid values is too thin to be meaningful.
MIN_THEMES_FOR_RANK = 6

# Quadrant assignment thresholds — provisional, pending shadow-calibration ledger
# (same pattern as HEAT_HOT=0.40 in foresight_convergence.py).
# Candidate set: [0.50, 0.60, 0.70] — future shadow grid will promote the best.
NARRATIVE_HI_THRESHOLD = 0.60
MONEY_HI_THRESHOLD = 0.60

# The incumbent catch-up claim uses calendar days, separately from return grading.
CATCHUP_DAYS = 60


def catchup_observed(flag_asof, theme_rows):
    """The unchanged native catch-up predicate, without grading/price I/O.

    Rows must already belong to the flag's theme. This intentionally retains the
    grader's any()/short-circuit and timestamp behavior; it asserts no coverage,
    episode independence, constant cohort, causality or calibrated prediction.
    """
    import pandas as pd
    flag_ts = pd.Timestamp(flag_asof)
    cutoff = flag_ts + pd.Timedelta(days=CATCHUP_DAYS)
    return any(
        e.get("quadrant") == "confirmed"
        for e in theme_rows
        if e.get("asof") and flag_ts < pd.Timestamp(e["asof"]) <= cutoff
    )

# Heartbeat: re-log for hidden-opportunity even when unchanged if this many days old.
# Mirrors _HEARTBEAT_DAYS=7 in foresight_cascade.py.
_HEARTBEAT_DAYS = 7

# Broadening-state → float mapping for the money axis.
_BROADENING_MAP: dict[str, float] = {
    "RISING": 1.0,
    "FLAT_LOW": 0.0,
    "ROLLING": -0.5,
    "MIXED": 0.2,
}


# ─────────────────────────────────────────────────────────────────────────────
# Pure math helpers
# ─────────────────────────────────────────────────────────────────────────────

def _axis_raw(legs: list[tuple[float, float]]) -> float | None:
    """Weighted mean of (value, weight) pairs. Returns None if no legs.

    legs = [(value, weight), ...] — caller excludes None values.
    The result is an internal aggregate; its scale is NOT a z-score.
    The cross-sectional rank-pct step (below) absorbs any scale mismatch.
    """
    if not legs:
        return None
    num = sum(w * v for v, w in legs)
    den = sum(w for _, w in legs)
    return num / den if den > 0 else None


def _rank_pct(values: list[float | None]) -> list[float | None]:
    """Cross-sectional rank-percentile, identical logic to foresight_earliness._rank_pct.

    Kept inline to avoid a circular import (foresight_earliness imports foresight_score
    which imports nothing from this module, but import-time coupling grows).
    None → None (absent stays absent, never laundered as 0.5).
    Ties broken by averaging ranks. Returns floats in [0, 1].
    Returns all-None when fewer than 2 valid values (undefined percentile).
    """
    indexed = [(i, v) for i, v in enumerate(values) if v is not None]
    if len(indexed) < 2:
        return [None] * len(values)
    n = len(indexed)
    sorted_vals = sorted(indexed, key=lambda x: x[1])
    ranks: dict[int, float] = {}
    j = 0
    while j < n:
        k = j
        while k + 1 < n and sorted_vals[k + 1][1] == sorted_vals[j][1]:
            k += 1
        avg_rank = (j + k) / 2 / (n - 1) if n > 1 else 0.5
        for idx in range(j, k + 1):
            ranks[sorted_vals[idx][0]] = avg_rank
        j = k + 1
    result = [None] * len(values)
    for i, _ in indexed:
        result[i] = ranks[i]
    return result


def _quadrant(narrative_pct: float, money_pct: float) -> str:
    """Four-cell quadrant label based on provisional 0.60/0.60 thresholds."""
    high_n = narrative_pct >= NARRATIVE_HI_THRESHOLD
    high_m = money_pct >= MONEY_HI_THRESHOLD
    if high_n and high_m:
        return "confirmed"
    if high_n and not high_m:
        return "hype-risk"
    if not high_n and high_m:
        return "hidden-opportunity"
    return "ignore"


# ─────────────────────────────────────────────────────────────────────────────
# Per-theme leg extraction
# ─────────────────────────────────────────────────────────────────────────────

def _narrative_legs(
    cascade_row: dict,
    activity_entry: dict | None,
) -> tuple[list[tuple[float, float]], dict]:
    """Collect live narrative-axis legs for one theme.

    Returns (legs, raw_values_dict).

    Leg 1 — news_velocity (z from theme_activity sources list; weight 1.0).
             Only themes with a GDELT mapping have this. The news_velocity leg
             in activity["sources"] is already cross-sectionally z-scored by
             compute_real_activity.
    Leg 2 — language_accel from cascade row (EDGAR text-accel; weight 0.8).
             Already a float from the bottleneck language leg (accel ratio, unitless).
    Leg 3 — text_only_bottleneck: binary (1.0 if bottleneck is text-only AND band
             is not None; weight 0.5). Weak presence/absence signal.
    """
    legs: list[tuple[float, float]] = []
    raw: dict = {}

    # Leg 1: news_velocity z from activity sources
    news_z: float | None = None
    if activity_entry is not None:
        for src in (activity_entry.get("sources") or []):
            if src.get("name") == "news_velocity":
                news_z = src.get("z")
                break
    raw["news_z"] = news_z
    if news_z is not None:
        legs.append((news_z, 1.0))

    # Leg 2: language_accel from cascade row
    lang_accel = cascade_row.get("language_accel")
    raw["language_accel"] = lang_accel
    if lang_accel is not None:
        legs.append((float(lang_accel), 0.8))

    # Leg 3: text_only_bottleneck — bottleneck supported by text ONLY (no physical)
    text_only = bool(cascade_row.get("bottleneck_text_only", False))
    band_present = cascade_row.get("bottleneck_band") is not None
    text_flag = 1.0 if (text_only and band_present) else 0.0
    raw["text_only_flag"] = text_flag if band_present else None
    if band_present:
        legs.append((text_flag, 0.5))

    return legs, raw


def _money_legs(
    cascade_row: dict,
    activity_entry: dict | None,
) -> tuple[list[tuple[float, float]], dict]:
    """Collect live money-axis legs for one theme.

    Leg 1 — fused_obs_z from theme_activity (cross-sectional robust-z; weight 1.0).
    Leg 2 — revision_breadth from cascade row ∈ [-1, 1] (weight 1.0).
    Leg 3 — broadening_state from cascade row mapped to float (weight 0.6).
    Leg 4 — fingerprint_tightness NOT in cascade rows (theme_fingerprint runs separately
             and is not injected into compute_foresight_cascade output). Omitted to stay
             within the anti-laundering discipline (absent = excluded, not default-filled).
    """
    legs: list[tuple[float, float]] = []
    raw: dict = {}

    # Leg 1: fused_obs_z from theme_activity
    fused_z: float | None = None
    if activity_entry is not None:
        fused_z = activity_entry.get("fused_obs_z")
    raw["fused_obs_z"] = fused_z
    if fused_z is not None:
        legs.append((float(fused_z), 1.0))

    # Leg 2: revision_breadth ∈ [-1, 1]
    rev_breadth = cascade_row.get("revision_breadth")
    raw["revision_breadth"] = rev_breadth
    if rev_breadth is not None:
        legs.append((float(rev_breadth), 1.0))

    # Leg 3: broadening_state mapped to float
    broadening = cascade_row.get("broadening_state")
    broadening_mapped = _BROADENING_MAP.get(str(broadening)) if broadening is not None else None
    raw["broadening_state"] = broadening_mapped
    if broadening_mapped is not None:
        legs.append((broadening_mapped, 0.6))

    return legs, raw


# ─────────────────────────────────────────────────────────────────────────────
# Ledger append
# ─────────────────────────────────────────────────────────────────────────────

def _append_divergence_ledger(
    rows_to_log: list[dict],
    *,
    root: Path | None = None,
) -> int:
    """Append hidden-opportunity (and transition) rows to divergence_log.jsonl.

    Dedup by (theme, asof) — idempotent across same-day re-runs.
    Weekly heartbeat: re-log a theme whose quadrant is unchanged if >7 days old.
    PIT member snapshot: tickers come from config at call time.

    Returns number of rows appended.

    Gate: COLLECT_LANE=nightly — nightly is the sole advancer of forward ledgers.
    Off-lane this returns 0 without touching the file; the board itself still renders
    (it is computed from the cascade + activity, not from the ledger).
    """
    if not _ledger_advance_enabled():
        log.debug("foresight_divergence._append_divergence_ledger: skipped "
                  "(COLLECT_LANE != nightly)")
        return 0
    d = (Path(root) if root else config.data_dir()) / "foresight"
    d.mkdir(parents=True, exist_ok=True)
    p = d / "divergence_log.jsonl"

    # Build indexes over existing rows
    seen_pairs: set[tuple] = set()
    last_logged: dict[str, tuple] = {}  # theme -> (last_date, last_quadrant)

    if p.exists():
        for line in p.read_text().splitlines():
            try:
                e = json.loads(line)
                t, a, q = e.get("theme"), e.get("asof"), e.get("quadrant")
                if t and a:
                    seen_pairs.add((t, a))
                    try:
                        d_date = datetime.fromisoformat(a).date()
                    except Exception:  # noqa: BLE001
                        continue
                    prev = last_logged.get(t)
                    if prev is None or d_date > prev[0]:
                        last_logged[t] = (d_date, q)
            except Exception:  # noqa: BLE001
                continue

    ts = datetime.now(timezone.utc).isoformat()
    cfg_themes = (config.load() or {}).get("themes") or {}
    lines_to_write: list[str] = []

    for r in rows_to_log:
        theme = r["theme"]
        asof = r["asof"]
        quadrant = r["quadrant"]
        row_type = r.get("row_type", "observation")

        # Hard dedup: same (theme, asof) already written
        if (theme, asof) in seen_pairs:
            continue

        prev = last_logged.get(theme)
        if prev is not None and row_type == "observation":
            prev_date, prev_quadrant = prev
            quadrant_changed = (quadrant != prev_quadrant)
            try:
                asof_date = datetime.fromisoformat(asof).date()
                days_since = (asof_date - prev_date).days
            except Exception:  # noqa: BLE001
                days_since = None
            heartbeat_due = days_since is not None and days_since >= _HEARTBEAT_DAYS
            # Only log observations if quadrant changed OR heartbeat overdue.
            # Transition rows always log (they carry their own event type).
            if not quadrant_changed and not heartbeat_due:
                continue

        members = (cfg_themes.get(theme) or {}).get("tickers") or []
        entry = {
            "theme": theme,
            "asof": asof,
            "ts": ts,
            "row_type": row_type,
            "quadrant": quadrant,
            "narrative_pct": r.get("narrative_pct"),
            "money_pct": r.get("money_pct"),
            "divergence": r.get("divergence"),
            "n_narrative_legs_live": r.get("n_narrative_legs_live"),
            "n_money_legs_live": r.get("n_money_legs_live"),
            "members": members,
        }
        if "transition" in r:
            entry["transition"] = r["transition"]
        lines_to_write.append(json.dumps(entry, separators=(",", ":")))

    if lines_to_write:
        with p.open("a") as fh:
            fh.write("\n".join(lines_to_write) + "\n")

    return len(lines_to_write)


# ─────────────────────────────────────────────────────────────────────────────
# Main engine
# ─────────────────────────────────────────────────────────────────────────────

def compute_divergence_board(
    cascade: dict | None,
    activity: dict | None = None,
    *,
    write_ledger: bool = True,
    root: Path | None = None,
    provenance_sink: dict | None = None,
    capture_optional: bool = False,
) -> dict | None:
    """Compute the Narrative-to-Money Divergence board.

    Args:
        cascade:      foresight_cascade output dict (has cascade["themes"] list).
        activity:     theme_activity.compute_real_activity() output, keyed by basket_id.
                      May be None — themes without an activity entry will have no money
                      legs from fused_obs_z and may be excluded from the cross-section.
        write_ledger: if True, append hidden-opportunity and transition rows to the ledger.
        root:         override data root (tests only).
        provenance_sink: optional empty internal dict for same-call provenance.
                      Never included in the board or written by this function.
                      This is unqualified input/computation evidence, not a
                      historical-availability, rights or eligibility receipt.
        capture_optional: ordinary caller may withhold failed capture while
                      preserving the one native board/ledger execution.

    Returns dict with:
        {
          "items": [per-theme dicts with quadrant / narrative_pct / money_pct / ...],
          "n_cross_section": int,   # themes with BOTH axes live
          "n_total": int,           # themes attempted
          "quadrant_counts": {...},
          "thin_cross_section": bool,  # True when n_cross_section < MIN_THEMES_FOR_RANK
          "note": str,
        }
    or None on fatal error.
    """
    capture_started = None
    capture_inputs = None
    if provenance_sink is not None:
        if type(provenance_sink) is not dict or provenance_sink:
            raise ValueError("same-run provenance requires an empty dict")
        try:
            capture_started = datetime.now(timezone.utc).isoformat()
            if not isinstance(cascade, dict) or not isinstance(cascade.get("themes"), list) or not cascade["themes"]:
                raise ValueError("same-run capture requires an attempted population")
            if any(not isinstance(row, dict) for row in cascade["themes"]):
                raise ValueError("same-run capture contains malformed population row")
            # Only fields actually used by this native computation enter the private
            # capture. Source prose and arbitrary upstream metadata are not retained.
            field_names = ("theme", "name", "stage", "language_accel",
                           "bottleneck_text_only", "bottleneck_band",
                           "revision_breadth", "broadening_state")
            projected_cascade = {
                "themes": [{k: copy.deepcopy(row[k]) for k in field_names if k in row}
                           for row in cascade["themes"]]}
            if "asof" in cascade:
                projected_cascade["asof"] = copy.deepcopy(cascade["asof"])
            projected_activity = {}
            for row in cascade["themes"]:
                key = row.get("theme")
                entry = (activity or {}).get(key) if key else None
                if entry is not None:
                    projected_activity[key] = {
                        "fused_obs_z": copy.deepcopy(entry.get("fused_obs_z")),
                        "sources": [{"name": "news_velocity", "z": copy.deepcopy(src.get("z"))}
                                    for src in (entry.get("sources") or [])
                                    if src.get("name") == "news_velocity"]}
            capture_inputs = {"cascade": projected_cascade, "activity": projected_activity}
            # Freeze the exact computation inputs. No re-read or later recomputation
            # is used to manufacture a same-run observation.
            raw = json.dumps(capture_inputs, sort_keys=True, ensure_ascii=False,
                             allow_nan=False, separators=(",", ":")).encode()
            if len(raw) > 8 * 1024 * 1024:
                raise ValueError("same-run input capture resource bound exceeded")
            cascade, activity = copy.deepcopy(projected_cascade), copy.deepcopy(projected_activity)
            capture_input_sha256 = hashlib.sha256(raw).hexdigest()
        except Exception as exc:
            if not capture_optional: raise
            log.warning("native input capture unavailable: %s", type(exc).__name__)
            provenance_sink = None

    if not cascade:
        return None

    themes_rows = cascade.get("themes") or []
    if not themes_rows:
        return None

    asof = cascade.get("asof") or datetime.now(timezone.utc).date().isoformat()
    act = activity or {}

    # ── Pass 1: per-theme axis raw values ──────────────────────────────────
    per_theme: list[dict] = []
    capture_axes = []
    for source_position, r in enumerate(themes_rows):
        theme = r.get("theme")
        if not theme:
            continue
        activity_entry = act.get(theme)

        n_legs, n_raw = _narrative_legs(r, activity_entry)
        m_legs, m_raw = _money_legs(r, activity_entry)

        narrative_raw = _axis_raw(n_legs)
        money_raw = _axis_raw(m_legs)
        if provenance_sink is not None:
            try:
                capture_axes.append({
                    "source_position": source_position, "theme": theme,
                    "narrative_legs": copy.deepcopy(n_legs),
                    "money_legs": copy.deepcopy(m_legs),
                    "narrative_native_values": copy.deepcopy(n_raw),
                    "money_native_values": copy.deepcopy(m_raw),
                    "narrative_raw": narrative_raw, "money_raw": money_raw,
                })
            except Exception as exc:
                if not capture_optional: raise
                log.warning("native axis capture unavailable: %s", type(exc).__name__)
                provenance_sink = None

        per_theme.append({
            "theme": theme,
            "name": r.get("name", theme),
            "stage": r.get("stage"),
            "narrative_raw": narrative_raw,
            "money_raw": money_raw,
            "n_narrative_legs_live": len(n_legs),
            "n_money_legs_live": len(m_legs),
            "_n_raw": n_raw,
            "_m_raw": m_raw,
        })

    # ── Pass 2: cross-section — themes where BOTH axes are live ───────────
    cross_section = [t for t in per_theme
                     if t["narrative_raw"] is not None and t["money_raw"] is not None]
    n_cross = len(cross_section)
    thin = n_cross < MIN_THEMES_FOR_RANK

    # ── Pass 3: rank-percentile on the cross-section ──────────────────────
    narrative_pcts: list[float | None] = [None] * len(cross_section)
    money_pcts: list[float | None] = [None] * len(cross_section)

    if not thin:
        narrative_raws = [t["narrative_raw"] for t in cross_section]
        money_raws = [t["money_raw"] for t in cross_section]
        narrative_pcts = _rank_pct(narrative_raws)
        money_pcts = _rank_pct(money_raws)

    # ── Pass 4: quadrant labels + transition detection ─────────────────────
    # Read last-known quadrant per theme from the ledger for transition detection.
    last_quadrant: dict[str, tuple[str, str]] = {}   # theme -> (asof, quadrant)
    ledger_path = (Path(root) if root else config.data_dir()) / "foresight" / "divergence_log.jsonl"
    ledger_capture = {"state": "ABSENT_AT_CHECK", "sha256": None, "bytes": None}
    if ledger_path.exists():
        # One original predecessor read feeds the native computation. Capture
        # size failure may withhold provenance, never rerun or drop the board.
        ledger_raw = ledger_path.read_bytes()
        ledger_text = ledger_raw.decode("utf-8")
        if provenance_sink is not None:
            try:
                if len(ledger_raw) > 8 * 1024 * 1024:
                    raise ValueError("same-run predecessor capture resource bound exceeded")
                ledger_capture = {"state": "READ", "sha256": hashlib.sha256(ledger_raw).hexdigest(),
                                  "bytes": len(ledger_raw)}
            except Exception as exc:
                if not capture_optional: raise
                log.warning("native predecessor capture unavailable: %s", type(exc).__name__)
                provenance_sink = None
        for line in ledger_text.splitlines():
            try:
                e = json.loads(line)
                t, q, a = e.get("theme"), e.get("quadrant"), e.get("asof")
                if t and q and a:
                    prev = last_quadrant.get(t)
                    if prev is None or a > prev[0]:
                        last_quadrant[t] = (a, q)
            except Exception:  # noqa: BLE001
                continue
    last_q: dict[str, str] = {t: v[1] for t, v in last_quadrant.items()}

    items: list[dict] = []
    to_log: list[dict] = []

    # Themes not in cross-section: emit with quadrant=None
    cross_themes = {t["theme"] for t in cross_section}
    for t in per_theme:
        if t["theme"] not in cross_themes:
            items.append({
                "theme": t["theme"],
                "name": t["name"],
                "stage": t["stage"],
                "quadrant": None,
                "narrative_pct": None,
                "money_pct": None,
                "divergence": None,
                "n_narrative_legs_live": t["n_narrative_legs_live"],
                "n_money_legs_live": t["n_money_legs_live"],
                "excluded": True,
                "transition": None,
            })

    quadrant_counts: dict[str, int] = {
        "confirmed": 0, "hype-risk": 0, "hidden-opportunity": 0, "ignore": 0,
    }

    for i, t in enumerate(cross_section):
        npct = narrative_pcts[i]
        mpct = money_pcts[i]

        if thin or npct is None or mpct is None:
            quad = None
            divergence = None
        else:
            quad = _quadrant(npct, mpct)
            divergence = round(npct - mpct, 4)
            quadrant_counts[quad] = quadrant_counts.get(quad, 0) + 1

        # Transition detection: hidden-opportunity → confirmed
        prev_quad = last_q.get(t["theme"])
        transition: str | None = None
        if quad == "confirmed" and prev_quad == "hidden-opportunity":
            transition = "hidden→confirmed"

        item = {
            "theme": t["theme"],
            "name": t["name"],
            "stage": t["stage"],
            "quadrant": quad,
            "narrative_pct": round(npct, 4) if npct is not None else None,
            "money_pct": round(mpct, 4) if mpct is not None else None,
            "divergence": divergence,
            "n_narrative_legs_live": t["n_narrative_legs_live"],
            "n_money_legs_live": t["n_money_legs_live"],
            "excluded": False,
            "transition": transition,
        }
        items.append(item)

        # Queue ledger appends
        if write_ledger and quad is not None:
            if quad == "hidden-opportunity":
                to_log.append({
                    "theme": t["theme"],
                    "asof": asof,
                    "row_type": "observation",
                    "quadrant": quad,
                    "narrative_pct": item["narrative_pct"],
                    "money_pct": item["money_pct"],
                    "divergence": divergence,
                    "n_narrative_legs_live": t["n_narrative_legs_live"],
                    "n_money_legs_live": t["n_money_legs_live"],
                })
            if transition == "hidden→confirmed":
                to_log.append({
                    "theme": t["theme"],
                    "asof": asof,
                    "row_type": "transition",
                    "quadrant": quad,
                    "narrative_pct": item["narrative_pct"],
                    "money_pct": item["money_pct"],
                    "divergence": divergence,
                    "n_narrative_legs_live": t["n_narrative_legs_live"],
                    "n_money_legs_live": t["n_money_legs_live"],
                    "transition": transition,
                })

    # Sort: hidden-opportunity first (the claim), then confirmed, hype-risk, ignore
    _QUAD_RANK = {"hidden-opportunity": 0, "confirmed": 1, "hype-risk": 2, "ignore": 3}
    items.sort(key=lambda x: (
        _QUAD_RANK.get(x["quadrant"] or "ignore", 4),
        -(x["money_pct"] or 0),
    ))

    note_parts = []
    if thin:
        note_parts.append(
            f"cross-section too thin for reliable ranks (n={n_cross} < {MIN_THEMES_FOR_RANK})"
        )
    note_parts.append(
        "Quadrant thresholds (0.60/0.60) PROVISIONAL — pending forward-graded ledger significance. "
        "Display-only. Ledger accrues to data/foresight/divergence_log.jsonl."
    )

    board = {
        "items": items,
        "n_cross_section": n_cross,
        "n_total": len(per_theme),
        "quadrant_counts": quadrant_counts,
        "thin_cross_section": thin,
        "note": " ".join(note_parts),
    }
    if provenance_sink is not None:
        try:
            attempted = [{"source_position": i, "theme": row.get("theme"),
                          "status": "ATTEMPTED" if row.get("theme") else "MISSING_NATIVE_KEY"}
                         for i, row in enumerate(themes_rows)]
            keys = [row["theme"] for row in attempted if row["theme"]]
            record = {
                "schema": "gmi.divergence_same_run_capture/v1",
                "capture_started_at": capture_started,
                "capture_completed_at": datetime.now(timezone.utc).isoformat(),
                "effective_at": asof,
                "effective_at_declared": bool(cascade.get("asof")),
                "source_available_at": None,
                "producer_revision": None,
                "input_scope": "NATIVE_DIVERGENCE_FIELDS_NOT_UPSTREAM_PROVENANCE",
                "input_sha256": capture_input_sha256,
                "inputs": capture_inputs,
                "attempted_population": attempted,
                "n_input_rows": len(themes_rows),
                "identity_status": ("UNQUALIFIED" if len(keys) != len(themes_rows)
                                    or len(set(keys)) != len(keys) else "NATIVE_KEYS_UNIQUE"),
                "axis_computations": capture_axes,
                "cross_section_positions": [row["source_position"] for row in capture_axes
                                           if row["narrative_raw"] is not None
                                           and row["money_raw"] is not None],
                "method": {"rank": "cross_section_average_ties_v1",
                           "minimum_rank_population": MIN_THEMES_FOR_RANK,
                           "narrative_high": NARRATIVE_HI_THRESHOLD,
                           "money_high": MONEY_HI_THRESHOLD,
                           "catchup_calendar_days": CATCHUP_DAYS,
                           "provisional": True},
                "predecessor_ledger": ledger_capture,
                "last_quadrants_used": copy.deepcopy(last_quadrant),
                "board": copy.deepcopy(board),
                "member_identity_receipts": None,
                "source_purpose_receipts": None,
                "qualification": "UNQUALIFIED_NATIVE_COMPUTATION",
                "publication_allowed": False,
            }
            # Commit the caller-visible result once, after complete finite encoding.
            encoded = json.dumps(record, sort_keys=True, ensure_ascii=False,
                                 allow_nan=False, separators=(",", ":")).encode()
            if len(encoded) > 8 * 1024 * 1024:
                raise ValueError("same-run provenance resource bound exceeded")
            record["capture_sha256"] = hashlib.sha256(encoded).hexdigest()
            provenance_sink.update(copy.deepcopy(record))
        except Exception as exc:
            if not capture_optional: raise
            log.warning("native final capture unavailable: %s", type(exc).__name__)
    # Optional capture failure cannot suppress the original ledger effect.
    # Capture metadata never claims that append succeeded.
    if write_ledger and to_log:
        try:
            n_written = _append_divergence_ledger(to_log, root=root)
            log.info("divergence_log: %d rows appended", n_written)
        except Exception as e:  # noqa: BLE001
            log.warning("divergence_log append failed (non-fatal): %s", e)

    return board


# ─────────────────────────────────────────────────────────────────────────────
# Forward-grading of divergence ledger
# ─────────────────────────────────────────────────────────────────────────────

def grade_divergence_ledger(
    *,
    root: Path | None = None,
    today: str | None = None,
) -> dict:
    """Grade matured hidden-opportunity rows from divergence_log.jsonl.

    Two graded claims per hidden-opportunity flag:
      1. Catch-up grade  — did the quadrant flip to "confirmed" within 60 days?
         Read from the ledger itself (no price data needed).
      2. Return grade    — did the theme outperform SPY at 90d?
         Reuses foresight_grader._theme_excess() (survivorship-free, PIT members).

    Returns a summary dict. Runs silently if the ledger is absent or too fresh to grade.
    Both sub-grades are tracked SEPARATELY so FDR correction treats them as distinct signals.
    """
    try:
        import pandas as pd
        from engine.foresight_grader import _read_ledger, _theme_excess, _closes
        from engine.foresight_grader import HORIZONS
    except Exception as e:  # noqa: BLE001
        log.debug("grade_divergence_ledger imports failed: %s", e)
        return {"error": str(e)}

    data_dir = Path(root) if root else config.data_dir()
    log_path = data_dir / "foresight" / "divergence_log.jsonl"
    if not log_path.exists():
        return {"n_graded": 0, "note": "ledger absent"}

    rows = []
    for line in log_path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except Exception:  # noqa: BLE001
            continue

    today_ts = pd.Timestamp(today) if today else pd.Timestamp.now(tz='UTC').tz_localize(None).normalize()
    RETURN_DAYS = 90

    # Index all rows by theme for catch-up detection
    by_theme: dict[str, list[dict]] = {}
    for r in rows:
        by_theme.setdefault(r["theme"], []).append(r)

    # SPY closes for return grading
    try:
        spy = _closes("SPY")
    except Exception:  # noqa: BLE001
        spy = None

    catchup_results: list[dict] = []
    return_results: list[dict] = []

    for r in rows:
        if r.get("row_type") not in (None, "observation"):
            continue
        if r.get("quadrant") != "hidden-opportunity":
            continue
        try:
            flag_ts = pd.Timestamp(r["asof"])
        except Exception:  # noqa: BLE001
            continue
        days_elapsed = (today_ts - flag_ts).days

        # Catch-up grade (60-day horizon)
        if days_elapsed >= CATCHUP_DAYS:
            theme_rows = by_theme.get(r["theme"], [])
            caught_up = catchup_observed(flag_ts, theme_rows)
            catchup_results.append({
                "theme": r["theme"],
                "flag_date": r["asof"],
                "caught_up": caught_up,
            })

        # Return grade (90-day horizon)
        if days_elapsed >= RETURN_DAYS:
            members = r.get("members") or []
            start = flag_ts
            end = flag_ts + pd.Timedelta(days=RETURN_DAYS)
            try:
                excess = _theme_excess(members, start, end, spy)
            except Exception:  # noqa: BLE001
                excess = None
            return_results.append({
                "theme": r["theme"],
                "flag_date": r["asof"],
                "excess_return": excess,
            })

    n_catchup = len(catchup_results)
    n_return = len(return_results)
    catchup_hits = sum(1 for r in catchup_results if r["caught_up"])
    return_hits = sum(1 for r in return_results
                      if r["excess_return"] is not None and r["excess_return"] > 0)

    return {
        "n_graded_catchup": n_catchup,
        "n_graded_return": n_return,
        "catchup_hit_rate": round(catchup_hits / n_catchup, 3) if n_catchup else None,
        "return_hit_rate": round(return_hits / n_return, 3) if n_return else None,
        "catchup_detail": catchup_results[-20:],
        "return_detail": return_results[-20:],
        "note": (
            "Two separately-graded claims: (1) catch-up=narrative reaches confirmed within 60d; "
            "(2) return=theme outperforms SPY at 90d. FDR correction treats them independently. "
            "Accruing — Phase-0 significance requires ≥30 mature flags (BY-FDR corrected)."
        ),
    }

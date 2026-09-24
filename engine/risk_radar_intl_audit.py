"""International Risk Radar — per-market forward-outcome log + deterministic grading.

The sibling of engine/risk_radar_audit.py (US) for the China / HK / Canada radars
(engine/risk_radar_intl.py). Every daily snapshot is APPENDED to
data/risk_radar_intl/<market>_forward_log.jsonl (idempotent by as-of). Once an entry's
horizon matures it is GRADED against that market's OWN realized index path: did a
>=5% drawdown actually occur within H business days? Each loud call is then a true- or
false-positive. The rolling scorecard (realized precision / per-state hit-rate /
predicted-vs-realized odds) is what the card surfaces, what the bounded tuner
(engine/risk_radar_intl_tune.py) recalibrates from, and what gates whether a market's
radar has earned the right to HARD-FORCE the Market-State verdict (`can_force`).

These radars ship DISPLAY-ONLY (verdict untouched) until each one's own log matures and
clears the bar — accountable by construction, never trusted on faith. Never raises.

CAN_FORCE — ARTICLE-3 GATE (W7a / authority.v2)
------------------------------------------------
`can_force` is the conjunction of two deterministic gates.  The first replays the exact
pre-v2 raw-row inputs (graded rows, alert rows, alert hits, all-row base rate, and last
graded as-of) as a compatibility fence.  The second derives non-overlapping base windows
and loud stress episodes from the same append-only JSONL, then compares a one-sided 90%
Wilson lower bound for episode precision against a one-sided 90% Wilson upper bound for
the independent base rate.  Both gates require named sample floors, valid non-future
fresh evidence, and lift strictly above 1.25.  Therefore the migration may revoke
row-level authority but cannot create authority that the pre-v2 implementation refused.

When the grant state changes vs the previous scorecard call, authority_grant or
authority_lapse events are appended to data/neuralweb/governance.jsonl via
engine.neuralweb.governance (fail-open — a governance-write failure never aborts the
audit).  Historical events and forward rows are never rewritten.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from engine.risk_radar_intl_evidence import derive_evidence, parse_asof_date
from lib import config, store

log = logging.getLogger(__name__)

HORIZONS = {"h5": 5, "h10": 10, "h21": 21}        # business-day forward windows
DD_THRESHOLDS = (0.05, 0.08)
PRIMARY_DD = 0.05
ALERT_STATES = ("elevated", "risk-off")            # the loud tiers, for precision
# --- gate for earning the right to hard-force the verdict (Article 3) ---
AUTHORITY_CONTRACT = "risk_radar_intl.authority.v2"
MIN_GRADED_FORCE = 30
MIN_ALERTS_FORCE = 8
# Migration fence: this is the exact effective pre-v2 min_n behavior. Keeping it
# conjunctive makes the episode migration mechanically no-grant-more.
LEGACY_MIN_ALERT_ROWS_FORCE = 30
MIN_ROW_HITS_FORCE = 8
MIN_INDEPENDENT_EPISODES_FORCE = 30
MIN_LOUD_EPISODES_FORCE = 8
MIN_EPISODE_HITS_FORCE = 8
# NOTE: MIN_FORCE_LIFT (point-estimate 1.25) REMOVED — replaced by Wilson CI lift > 1.25
# The Wilson lower-bound gate (z=1.645, 90% one-sided) is evaluated inside scorecard().
# Threshold 1.25 matches the retired point-estimate floor; because wilson_lb <= point_estimate
# always, the CI gate is strictly tighter everywhere (zero grant-more cases, verified in tests).
# At n_alerts=8 the old gate false-granted ~44% under the null; Wilson reduces this to ~5.8%.


def ledger_lane_armed() -> bool:
    """True only on the nightly collect lane (COLLECT_LANE=nightly, legacy alias
    US_LANE). House law: nightly is the SOLE advancer of data/ forward ledgers —
    the engine-render/render re-render lanes and closing-bell run the CN/HK/CA/intl
    builds too; on those lanes the radar snapshot still renders but snapshot_and_grade
    and the tuner must not advance (a mid-session append is PIT-inconsistent and,
    being idempotent-by-asof, would permanently displace the nightly row). Canonical
    home for the gate; engine/intl_run._ledger_lane_armed delegates here."""
    import os
    lane = os.environ.get("COLLECT_LANE", "") or os.environ.get("US_LANE", "")
    return lane.lower() == "nightly"


def _path(market: str, root=None) -> Path:
    base = config.data_dir() if root is None else (Path(root) / "data")
    p = base / "risk_radar_intl" / f"{market}_forward_log.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _read(p: Path) -> list[dict]:
    if not p.exists():
        return []
    rows = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:  # noqa: BLE001
            continue
    return rows


def _write(p: Path, rows: list[dict]) -> None:
    p.write_text("\n".join(json.dumps(r, separators=(",", ":"), default=str) for r in rows) + "\n")


def _entry_from_snapshot(snap: dict) -> dict | None:
    if not snap or not snap.get("asof") or snap.get("state") is None:
        return None
    return {
        "asof": str(snap["asof"]),
        "market": snap.get("market"),
        "state": snap.get("state"),
        "alert": snap.get("state") in ALERT_STATES,
        "dominant_scare": snap.get("dominant_scare"),
        "top_score": snap.get("top_score"),
        "conjunction": bool(snap.get("conjunction")),
        "scares": {s["scare"]: {"score": s.get("score"), "band": s.get("band")}
                   for s in (snap.get("scares") or [])},
        "drawdown_prob": snap.get("drawdown_prob"),
        # de-escalation trajectory (engine/risk_radar_intl._trajectory) — for a future recovery audit.
        "traj_phase": (snap.get("trajectory") or {}).get("phase"),
        "traj_intensity": (snap.get("trajectory") or {}).get("intensity"),
        "traj_off_peak": (snap.get("trajectory") or {}).get("off_peak"),
        "traj_odds_now": (snap.get("trajectory") or {}).get("odds_now"),
        "logged_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "graded": None,
    }


def log_snapshot(snap: dict, market: str, root=None) -> bool:
    """Append today's snapshot to the market's forward log (idempotent by as-of)."""
    try:
        entry = _entry_from_snapshot(snap)
        if entry is None:
            return False
        p = _path(market, root)
        rows = _read(p)
        if any(r.get("asof") == entry["asof"] for r in rows):
            return False
        rows.append(entry)
        _write(p, rows)
        return True
    except Exception as e:  # noqa: BLE001
        log.warning("risk_radar_intl_audit log(%s) failed: %s", market, e)
        return False


def _bench(profile) -> pd.Series | None:
    try:
        df = store.read(*profile.bench)
        if df is None or getattr(df, "empty", True):
            return None
        c = "close" if "close" in df.columns else df.columns[0]
        s = df[c].dropna()
        s.index = pd.to_datetime(s.index)
        return s.sort_index()
    except Exception:  # noqa: BLE001
        return None


def _grade_entry(entry: dict, px: pd.Series) -> dict | None:
    """Realized forward max-drawdown per horizon from the as-of date; mark hit + outcome.
    None until the longest horizon has matured."""
    asof = pd.Timestamp(entry["asof"])
    loc = px.index.searchsorted(asof, side="right")
    maxH = max(HORIZONS.values())
    if loc + maxH > len(px):
        return None
    base_px = float(px.iloc[max(0, loc - 1)])
    fwd_dd, hit = {}, {}
    for hk, hd in HORIZONS.items():
        w = px.iloc[loc: loc + hd]
        dd = float(w.min() / base_px - 1.0) if len(w) else None
        fwd_dd[hk] = None if dd is None else round(dd, 4)
        hit[hk] = {f"dd{int(t*100)}": (dd is not None and dd <= -t) for t in DD_THRESHOLDS}
    any_primary = any(fwd_dd[hk] is not None and fwd_dd[hk] <= -PRIMARY_DD for hk in HORIZONS)
    st = entry.get("state")
    if st in ALERT_STATES:
        outcome = "true_positive" if any_primary else "false_positive"
    elif st in ("watch", "caution"):
        outcome = "tp_watch" if any_primary else "tn_watch"
    else:
        outcome = "calm_dd" if any_primary else "calm_quiet"
    return {"base_px": round(base_px, 2), "fwd_dd": fwd_dd, "hit": hit,
            "outcome": outcome, "any_dd5_within_h21": bool(any_primary),
            "graded_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def grade_log(profile, root=None) -> int:
    """Grade every matured, ungraded entry against the market's realized index path."""
    try:
        p = _path(profile.key, root)
        rows = _read(p)
        if not rows:
            return 0
        px = _bench(profile)
        if px is None:
            return 0
        n = 0
        for r in rows:
            if r.get("graded"):
                continue
            g = _grade_entry(r, px)
            if g is not None:
                r["graded"] = g
                n += 1
        if n:
            _write(p, rows)
        return n
    except Exception as e:  # noqa: BLE001
        log.warning("risk_radar_intl_audit grade(%s) failed: %s", getattr(profile, "key", "?"), e)
        return 0


def realized_odds(market: str, root=None) -> dict:
    """Per-state realized P(>=5% drawdown within h) from the graded log — the empirical truth
    the tuner recalibrates the prob surface toward. {state: {h5,h10,h21, n}}."""
    rows = [r for r in _read(_path(market, root)) if r.get("graded")]
    out: dict[str, dict] = {}
    for r in rows:
        st = r.get("state")
        d = out.setdefault(st, {"n": 0, "h5": 0, "h10": 0, "h21": 0})
        d["n"] += 1
        g = r["graded"]
        for hk in HORIZONS:
            fdd = (g.get("fwd_dd") or {}).get(hk)
            d[hk] += int(fdd is not None and fdd <= -PRIMARY_DD)
    return {st: {"n": d["n"], **{hk: round(d[hk] / d["n"], 3) for hk in HORIZONS}}
            for st, d in out.items() if d["n"]}


def _evidence_day(value: object):
    return parse_asof_date(value)


def _valid_evidence_asof(value: object) -> bool:
    return _evidence_day(value) is not None


def _utc_now(now: datetime | None) -> datetime:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _evaluate_authority_contract(
    metrics: dict,
    *,
    now: datetime | None = None,
) -> dict:
    """Evaluate the monotone v2 authority contract without IO.

    The exact pre-v2 row gate remains a conjunctive migration fence. The episode
    gate uses independent episode units and a conservative upper bound for the
    base rate. Shared constitution semantics remain unchanged.
    """
    from engine.neuralweb.constitution import grant_authority  # type: ignore[import]

    evaluation_now = _utc_now(now)

    # Canonical/deduplicated row metrics feed the new episode contract.
    n_total = int(metrics.get("n_total_graded_rows") or 0)
    n_loud = int(metrics.get("n_loud_rows") or 0)

    # Raw legacy metrics preserve the exact pre-v2 denominator and base-rate inputs.
    # Fallbacks keep the pure adapter backward-compatible for direct callers/tests.
    legacy_n_total = int(
        metrics.get("legacy_n_total_graded_rows", n_total) or 0
    )
    legacy_n_alerts = int(
        metrics.get("legacy_n_alert_rows", n_loud) or 0
    )
    legacy_n_hits = int(
        metrics.get("legacy_n_alert_hits", metrics.get("n_row_hits")) or 0
    )
    legacy_n_incomplete = int(
        metrics.get("legacy_n_incomplete_authority_rows") or 0
    )
    legacy_base = float(
        metrics.get(
            "legacy_row_base_rate_dd5_h21",
            metrics.get("row_base_rate_dd5_h21"),
        )
        or 0.0
    )
    legacy_asof = metrics.get(
        "legacy_row_evidence_asof", metrics.get("row_evidence_asof")
    )

    row_gate_granted = False
    row_gate_reason: str
    row_wilson_lb = None
    row_lift_lb = None
    row_lapses_at = None

    if legacy_n_total < MIN_GRADED_FORCE:
        row_gate_reason = (
            "row-accrual-refused: "
            f"legacy_n_total_graded_rows={legacy_n_total} "
            f"< min_total_graded_rows={MIN_GRADED_FORCE}"
        )
    elif legacy_n_alerts < MIN_ALERTS_FORCE:
        row_gate_reason = (
            "row-accrual-refused: "
            f"legacy_n_alert_rows={legacy_n_alerts} "
            f"< min_alert_rows={MIN_ALERTS_FORCE}"
        )
    elif legacy_n_alerts < LEGACY_MIN_ALERT_ROWS_FORCE:
        row_gate_reason = (
            "legacy-row-gate-refused: "
            f"n_alert_rows={legacy_n_alerts} "
            f"< legacy_min_alert_rows={LEGACY_MIN_ALERT_ROWS_FORCE}"
        )
    elif legacy_n_incomplete:
        row_gate_reason = (
            "legacy-row-gate-refused: "
            f"incomplete-authority-outcomes={legacy_n_incomplete}"
        )
    elif legacy_n_hits < MIN_ROW_HITS_FORCE:
        row_gate_reason = (
            "legacy-row-gate-refused: "
            f"n_alert_hits={legacy_n_hits} "
            f"< legacy_min_alert_hits={MIN_ROW_HITS_FORCE}"
        )
    elif not legacy_asof:
        row_gate_reason = "legacy-row-gate-refused: missing-row-evidence-asof"
    elif not _valid_evidence_asof(legacy_asof):
        row_gate_reason = (
            "legacy-row-gate-refused: invalid-row-evidence-asof="
            f"{legacy_asof!r}"
        )
    elif _evidence_day(legacy_asof) > evaluation_now.date():
        row_gate_reason = (
            "legacy-row-gate-refused: future-row-evidence-asof="
            f"{_evidence_day(legacy_asof).isoformat()} "
            f"> now={evaluation_now.date().isoformat()}"
        )
    else:
        try:
            row_result = grant_authority(
                evidence={
                    "hits": legacy_n_hits,
                    "n": legacy_n_alerts,
                    "base_rate": legacy_base,
                    "evidence_asof": legacy_asof,
                },
                floors={
                    "min_n": LEGACY_MIN_ALERT_ROWS_FORCE,
                    "min_events": MIN_ROW_HITS_FORCE,
                },
                now=evaluation_now,
            )
            row_gate_granted = bool(row_result.granted)
            row_wilson_lb = row_result.wilson_lb
            row_lift_lb = row_result.lift_lb
            row_lapses_at = row_result.lapses_at
            prefix = (
                "legacy-row-gate-granted"
                if row_gate_granted
                else "legacy-row-gate-refused"
            )
            row_gate_reason = f"{prefix}: {row_result.reason}"
        except Exception as exc:  # noqa: BLE001
            row_gate_reason = f"legacy-row-gate-refused: gate-error: {exc}"

    n_independent = int(metrics.get("n_independent_episodes") or 0)
    n_loud_episodes = int(metrics.get("n_loud_episodes") or 0)
    n_episode_hits = int(metrics.get("n_episode_hits") or 0)
    base_upper_raw = metrics.get("episode_base_rate_upper_90")
    episode_asof = metrics.get("episode_evidence_asof")
    canonical_row_asof = metrics.get("row_evidence_asof")

    episode_gate_granted = False
    episode_gate_reason: str
    episode_wilson_lb = None
    episode_lift_lb = None
    episode_lapses_at = None

    if n_total < MIN_GRADED_FORCE:
        episode_gate_reason = (
            "episode-gate-refused: "
            f"n_total_graded_rows={n_total} < min_total_graded_rows={MIN_GRADED_FORCE}"
        )
    elif n_loud < MIN_ALERTS_FORCE:
        episode_gate_reason = (
            "episode-gate-refused: "
            f"n_loud_rows={n_loud} < min_loud_rows={MIN_ALERTS_FORCE}"
        )
    elif n_independent < MIN_INDEPENDENT_EPISODES_FORCE:
        episode_gate_reason = (
            "episode-gate-refused: "
            f"n_independent_episodes={n_independent} "
            f"< min_independent_episodes={MIN_INDEPENDENT_EPISODES_FORCE}"
        )
    elif n_loud_episodes < MIN_LOUD_EPISODES_FORCE:
        episode_gate_reason = (
            "episode-gate-refused: "
            f"n_loud_episodes={n_loud_episodes} "
            f"< min_loud_episodes={MIN_LOUD_EPISODES_FORCE}"
        )
    elif n_episode_hits < MIN_EPISODE_HITS_FORCE:
        episode_gate_reason = (
            "episode-gate-refused: "
            f"n_episode_hits={n_episode_hits} "
            f"< min_episode_hits={MIN_EPISODE_HITS_FORCE}"
        )
    elif not episode_asof:
        episode_gate_reason = "episode-gate-refused: missing-episode-evidence-asof"
    elif not _valid_evidence_asof(episode_asof):
        episode_gate_reason = (
            "episode-gate-refused: invalid-episode-evidence-asof="
            f"{episode_asof!r}"
        )
    elif _evidence_day(episode_asof) > evaluation_now.date():
        episode_gate_reason = (
            "episode-gate-refused: future-episode-evidence-asof="
            f"{_evidence_day(episode_asof).isoformat()} "
            f"> now={evaluation_now.date().isoformat()}"
        )
    elif not canonical_row_asof:
        episode_gate_reason = (
            "episode-gate-refused: missing-canonical-row-evidence-asof"
        )
    elif not _valid_evidence_asof(canonical_row_asof):
        episode_gate_reason = (
            "episode-gate-refused: invalid-canonical-row-evidence-asof="
            f"{canonical_row_asof!r}"
        )
    elif _evidence_day(canonical_row_asof) > evaluation_now.date():
        episode_gate_reason = (
            "episode-gate-refused: future-canonical-row-evidence-asof="
            f"{_evidence_day(canonical_row_asof).isoformat()} "
            f"> now={evaluation_now.date().isoformat()}"
        )
    elif base_upper_raw is None or not (0.0 < float(base_upper_raw) <= 1.0):
        episode_gate_reason = (
            "episode-gate-refused: invalid-episode-base-rate-upper="
            f"{base_upper_raw!r}"
        )
    else:
        try:
            episode_result = grant_authority(
                evidence={
                    "hits": n_episode_hits,
                    "n": n_loud_episodes,
                    "base_rate": float(base_upper_raw),
                    "evidence_asof": episode_asof,
                },
                floors={
                    "min_n": MIN_LOUD_EPISODES_FORCE,
                    "min_events": MIN_EPISODE_HITS_FORCE,
                },
                now=evaluation_now,
            )
            episode_gate_granted = bool(episode_result.granted)
            episode_wilson_lb = episode_result.wilson_lb
            episode_lift_lb = episode_result.lift_lb
            episode_lapses_at = episode_result.lapses_at
            prefix = (
                "episode-gate-granted"
                if episode_gate_granted
                else "episode-gate-refused"
            )
            episode_gate_reason = f"{prefix}: {episode_result.reason}"
        except Exception as exc:  # noqa: BLE001
            episode_gate_reason = f"episode-gate-refused: gate-error: {exc}"

    can_force = row_gate_granted and episode_gate_granted
    if not row_gate_granted:
        grant_reason = row_gate_reason
    elif not episode_gate_granted:
        grant_reason = episode_gate_reason
    else:
        grant_reason = "granted: legacy row gate and episode gate cleared"

    return {
        "authority_contract": AUTHORITY_CONTRACT,
        "can_force": can_force,
        "grant_reason": grant_reason,
        "row_gate_granted": row_gate_granted,
        "row_gate_reason": row_gate_reason,
        "row_wilson_lb": row_wilson_lb,
        "row_wilson_lift_lb": row_lift_lb,
        "row_lapses_at": row_lapses_at,
        "episode_gate_granted": episode_gate_granted,
        "episode_gate_reason": episode_gate_reason,
        "episode_wilson_lb": episode_wilson_lb,
        "episode_gate_lift_lb": episode_lift_lb,
        "episode_lapses_at": episode_lapses_at,
    }


def _load_previous_can_force(market: str, root=None) -> bool | None:
    """Read the last can_force value written for this market (for change detection).

    Returns None when no previous scorecard exists.  Never raises.
    """
    try:
        if root is None:
            base = config.data_dir()
        else:
            base = Path(root) / "data"
        # Previous can_force lives in the risk_radar payload inside latest.json
        for region_dir in ("", "china_regime/", "hk_regime/", "canada_regime/"):
            p = Path(base) / f"{region_dir}latest.json"
            if p.exists():
                try:
                    obj = json.loads(p.read_text())
                    fwd = (obj.get("risk_radar") or {}).get("forward_log") or {}
                    if fwd.get("market") == market and "can_force" in fwd:
                        return bool(fwd["can_force"])
                except Exception:  # noqa: BLE001
                    pass
        # 7-market intl payload: data/intl/latest.json records[*].risk_radar.forward_log
        p = Path(base) / "intl" / "latest.json"
        if p.exists():
            try:
                obj = json.loads(p.read_text())
                for rec in (obj.get("records") or []):
                    fwd = ((rec.get("risk_radar") or {}).get("forward_log") or {})
                    if fwd.get("market") == market and "can_force" in fwd:
                        return bool(fwd["can_force"])
            except Exception:  # noqa: BLE001
                pass
    except Exception:  # noqa: BLE001
        pass
    return None


def _log_can_force_governance(
    market: str,
    can_force: bool,
    prev_can_force: bool | None,
    metrics: dict,
    authority: dict,
    root=None,
) -> None:
    """Append an additive v2 grant/lapse event when `can_force` changes.

    The existing governance ledger remains canonical. Historical events are never
    rewritten; new transitions carry both legacy row evidence and episode evidence.
    Fail-open: exceptions are logged but never propagated.
    """
    try:
        if prev_can_force is None or can_force == prev_can_force:
            return
        from engine.neuralweb.governance import append_event  # type: ignore[import]

        row_base = metrics.get("legacy_row_base_rate_dd5_h21")
        event_type = "authority_grant" if can_force else "authority_lapse"
        target = f"engine/risk_radar_intl_audit.can_force:{market}"
        append_event(
            event_type,
            target,
            article=3,
            authored_by="risk_radar_intl_audit",
            evidence={
                # Legacy keys retained for readers of prior transition events.
                "hits": metrics.get("legacy_n_alert_hits"),
                "n_alerts": metrics.get("legacy_n_alert_rows"),
                "base_rate": round(float(row_base), 4) if row_base is not None else None,
                "wilson_lb": authority.get("row_wilson_lb"),
                "lift_lb": authority.get("row_wilson_lift_lb"),
                "evidence_asof": metrics.get("legacy_row_evidence_asof"),
                # Additive, denominator-explicit v2 evidence.
                "authority_contract": authority.get("authority_contract"),
                "legacy_n_total_graded_rows": metrics.get("legacy_n_total_graded_rows"),
                "legacy_n_alert_rows": metrics.get("legacy_n_alert_rows"),
                "legacy_n_alert_hits": metrics.get("legacy_n_alert_hits"),
                "legacy_n_incomplete_authority_rows": metrics.get(
                    "legacy_n_incomplete_authority_rows"
                ),
                "n_total_graded_rows": metrics.get("n_total_graded_rows"),
                "n_loud_rows": metrics.get("n_loud_rows"),
                "n_row_hits": metrics.get("n_row_hits"),
                "n_independent_episodes": metrics.get("n_independent_episodes"),
                "n_loud_episodes": metrics.get("n_loud_episodes"),
                "n_episode_hits": metrics.get("n_episode_hits"),
                "episode_base_rate_upper_90": metrics.get("episode_base_rate_upper_90"),
                "episode_wilson_lb": authority.get("episode_wilson_lb"),
                "episode_lift_lb": authority.get("episode_gate_lift_lb"),
                "episode_evidence_asof": metrics.get("episode_evidence_asof"),
                "row_gate_reason": authority.get("row_gate_reason"),
                "episode_gate_reason": authority.get("episode_gate_reason"),
            },
            before={"can_force": prev_can_force},
            after={"can_force": can_force},
            note=str(authority.get("grant_reason") or ""),
            root=root,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("risk_radar_intl_audit: governance log failed for %s: %s", market, exc)


def scorecard(market: str, root=None, log_governance: bool = True) -> dict:
    """Return row diagnostics plus the episode-aware authority scorecard.

    Existing row-level fields retain their meanings. Authority contract v2 derives
    independent evidence from the same canonical JSONL and grants only when both the
    exact pre-v2 row gate and the episode gate clear. ``log_governance=False`` keeps
    this call fully read-only; nightly remains the sole governance writer.
    """
    try:
        all_rows = _read(_path(market, root))
    except Exception:  # noqa: BLE001
        all_rows = []

    try:
        metrics = derive_evidence(all_rows)
    except Exception as exc:  # noqa: BLE001
        log.warning("risk_radar_intl_audit: evidence derivation failed for %s: %s", market, exc)
        metrics = derive_evidence([])

    authority = _evaluate_authority_contract(metrics)
    public_metric_keys = (
        "legacy_n_total_graded_rows",
        "legacy_n_alert_rows",
        "legacy_n_alert_hits",
        "legacy_n_incomplete_authority_rows",
        "legacy_row_base_rate_dd5_h21",
        "legacy_row_evidence_asof",
        "n_total_graded_rows",
        "n_loud_rows",
        "n_row_hits",
        "daily_row_precision",
        "row_base_rate_dd5_h21",
        "row_evidence_asof",
        "n_independent_episodes",
        "n_independent_episode_hits",
        "independent_evidence_asof",
        "n_loud_episodes",
        "n_episode_hits",
        "loud_episode_evidence_asof",
        "n_unmatured_loud_episodes",
        "episode_precision",
        "episode_precision_lower_90",
        "episode_base_rate_dd5_h21",
        "episode_base_rate_upper_90",
        "episode_lift_lb",
        "episode_evidence_asof",
    )
    public_metrics = {key: metrics.get(key) for key in public_metric_keys}

    rows = sorted(
        (
            row
            for row in all_rows
            if isinstance(row, dict)
            and isinstance(row.get("graded"), dict)
            and bool(row.get("graded"))
            and row.get("asof")
        ),
        key=lambda row: str(row["asof"]),
    )
    if not rows:
        return {
            "market": market,
            "n_graded": 0,
            "base_rate_dd5_h21": None,
            "alert_precision": None,
            "n_alerts": 0,
            "alert_hit_rate": None,
            "force_lift": None,
            "wilson_lift_lb": authority.get("row_wilson_lift_lb"),
            "evidence_asof": metrics.get("legacy_row_evidence_asof"),
            "authority_grant_reason": authority.get("grant_reason"),
            "episode_definition": (
                "re-arm after 21 observed quiet rows or observed quiet plus 42 days; "
                "independent anchors are 21 observations or 42 days apart"
            ),
            "by_state": {},
            "realized_odds": {},
            "recent_mistakes": [],
            "asof_range": [],
            "note": "accruing — grades begin once calls mature (~21 trading days)",
            **public_metrics,
            **authority,
        }

    n = len(rows)
    base_value = metrics.get("legacy_row_base_rate_dd5_h21")
    base = float(base_value) if base_value is not None else 0.0
    alerts = [row for row in rows if row.get("alert")]
    true_positives = [
        row for row in alerts if (row.get("graded") or {}).get("outcome") == "true_positive"
    ]
    alert_hit_count = sum(
        int(bool((row.get("graded") or {}).get("any_dd5_within_h21")))
        for row in alerts
    )
    alert_hit = alert_hit_count / len(alerts) if alerts else None

    by_state: dict = {}
    for row in rows:
        state = row.get("state")
        cell = by_state.setdefault(state, {"n": 0, "dd": 0})
        cell["n"] += 1
        cell["dd"] += int(
            bool((row.get("graded") or {}).get("any_dd5_within_h21"))
        )
    by_state = {
        state: {"n": cell["n"], "hit_rate": round(cell["dd"] / cell["n"], 3)}
        for state, cell in by_state.items()
    }

    force_lift = round(alert_hit / base, 2) if (alert_hit is not None and base) else None
    can_force = bool(authority["can_force"])

    if log_governance:
        try:
            previous = _load_previous_can_force(market, root)
            _log_can_force_governance(
                market=market,
                can_force=can_force,
                prev_can_force=previous,
                metrics=metrics,
                authority=authority,
                root=root,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("risk_radar_intl_audit: governance logging failed for %s: %s", market, exc)

    mistakes = [
        {
            "asof": row["asof"],
            "state": row.get("state"),
            "dominant_scare": row.get("dominant_scare"),
            "fwd_dd_h21": ((row.get("graded") or {}).get("fwd_dd") or {}).get("h21"),
            "kind": (row.get("graded") or {}).get("outcome"),
        }
        for row in rows
        if (row.get("graded") or {}).get("outcome") == "false_positive"
        or (
            not row.get("alert")
            and (row.get("graded") or {}).get("any_dd5_within_h21")
        )
    ]

    return {
        "market": market,
        "n_graded": n,
        "base_rate_dd5_h21": round(base, 3),
        "alert_precision": (
            round(len(true_positives) / len(alerts), 3) if alerts else None
        ),
        "n_alerts": len(alerts),
        "alert_hit_rate": round(alert_hit, 3) if alert_hit is not None else None,
        "force_lift": force_lift,
        "wilson_lift_lb": authority.get("row_wilson_lift_lb"),
        "evidence_asof": metrics.get("legacy_row_evidence_asof"),
        "authority_grant_reason": authority.get("grant_reason"),
        "episode_definition": (
            "re-arm after 21 observed quiet rows or observed quiet plus 42 days; "
            "independent anchors are 21 observations or 42 days apart"
        ),
        "by_state": by_state,
        "realized_odds": realized_odds(market, root),
        "recent_mistakes": sorted(
            mistakes, key=lambda mistake: mistake["asof"], reverse=True
        )[:20],
        "asof_range": [rows[0]["asof"], rows[-1]["asof"]],
        **public_metrics,
        **authority,
    }

def snapshot_and_grade(snap: dict, profile, root=None) -> dict:
    """Log today's snapshot, grade matured entries, return the scorecard (attached to
    latest['risk_radar']['forward_log'] by the build)."""
    log_snapshot(snap, profile.key, root=root)
    grade_log(profile, root=root)
    return scorecard(profile.key, root=root)

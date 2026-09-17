"""Append-only prospective research journey for the raw BTC D2 observation.

This module owns no persistence.  ``btc_impulse_ledger`` remains the sole store;
this module only defines immutable generation semantics and pure projections.
A generation identity binds kind + semantic payload.  Lifecycle metadata such as
recording time is deliberately outside that identity.

The journey is research-only.  It never grants alert, sizing, or trading authority.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

SCHEMA = "btc_d2_forward.v1"
LABEL_H = 3
LABEL_THR = 0.05
DVOL_WINDOW = 60
SOURCE_ROWS_REQUIRED = DVOL_WINDOW + 2
SOURCE_EVALUATOR_VERSION = "btc_d2_source.v1"
OUTCOME_EVALUATOR_VERSION = "btc_d2_outcome.v1"
COLLECTOR_VERSION = "btc_impulse_radar._d2_cond.v1"


class GenerationConflict(ValueError):
    """A claimed generation identity does not match its semantic payload."""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _recorded_at(value: str | None) -> str:
    if value:
        return str(value)
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def new_journey() -> dict:
    return {"schema": SCHEMA, "generations": []}


def make_generation(kind: str, semantic: dict, *, recorded_at: str | None = None) -> dict:
    if kind not in {"source", "outcome", "correction"}:
        raise ValueError(f"unsupported D2 generation kind: {kind}")
    frozen = copy.deepcopy(semantic)
    identity_payload = {"kind": kind, "semantic": frozen}
    return {
        "generation_id": _digest(identity_payload),
        "kind": kind,
        "semantic": frozen,
        "lifecycle": {"recorded_at": _recorded_at(recorded_at)},
    }


def _validate_journey(journey: dict) -> None:
    if journey.get("schema") != SCHEMA or not isinstance(journey.get("generations"), list):
        raise GenerationConflict("invalid D2 journey envelope")
    seen: set[str] = set()
    source_generation = None
    outcome_generation = None
    for generation in journey["generations"]:
        if not isinstance(generation, dict):
            raise GenerationConflict("invalid D2 generation envelope")
        kind = generation.get("kind")
        semantic = generation.get("semantic")
        claimed = generation.get("generation_id")
        lifecycle = generation.get("lifecycle")
        if kind not in {"source", "outcome", "correction"} or not isinstance(semantic, dict):
            raise GenerationConflict("invalid D2 generation envelope")
        if not isinstance(lifecycle, dict) or not isinstance(lifecycle.get("recorded_at"), str):
            raise GenerationConflict("invalid D2 lifecycle metadata")
        expected = _digest({"kind": kind, "semantic": semantic})
        if claimed != expected:
            raise GenerationConflict("generation_id does not bind the supplied semantic payload")
        if claimed in seen:
            raise GenerationConflict("duplicate D2 generation identity")
        seen.add(claimed)

        if kind == "source":
            if source_generation is not None:
                raise GenerationConflict("D2 journey has more than one source root")
            source_generation = generation
            outcome_generation = None
            continue
        if kind == "outcome":
            if source_generation is None:
                raise GenerationConflict("D2 outcome has no source generation")
            if semantic.get("source_generation_id") != source_generation.get("generation_id"):
                raise GenerationConflict("D2 outcome is not bound to the current source generation")
            if outcome_generation is not None:
                raise GenerationConflict("D2 outcome replacement must be a correction generation")
            outcome_generation = generation
            continue

        target_kind = semantic.get("target_kind")
        replacement = semantic.get("replacement")
        if not isinstance(replacement, dict):
            raise GenerationConflict("D2 correction replacement is missing")
        if target_kind == "source":
            if source_generation is None:
                raise GenerationConflict("D2 source correction has no source root")
            if semantic.get("supersedes_generation_id") != source_generation.get("generation_id"):
                raise GenerationConflict("D2 source correction does not supersede the current source")
            source_generation = generation
            outcome_generation = None
        elif target_kind == "outcome":
            if source_generation is None or outcome_generation is None:
                raise GenerationConflict("D2 outcome correction has no current outcome")
            if semantic.get("supersedes_generation_id") != outcome_generation.get("generation_id"):
                raise GenerationConflict("D2 outcome correction does not supersede the current outcome")
            if replacement.get("source_generation_id") != source_generation.get("generation_id"):
                raise GenerationConflict("D2 outcome correction is not bound to the current source")
            outcome_generation = generation
        else:
            raise GenerationConflict("unsupported D2 correction target")


def append_generation(journey: dict, generation: dict) -> bool:
    _validate_journey(journey)
    kind = generation.get("kind")
    semantic = generation.get("semantic")
    claimed = generation.get("generation_id")
    if kind not in {"source", "outcome", "correction"} or not isinstance(semantic, dict):
        raise GenerationConflict("invalid D2 generation envelope")
    expected = _digest({"kind": kind, "semantic": semantic})
    if claimed != expected:
        raise GenerationConflict("generation_id does not bind the supplied semantic payload")
    for existing in journey["generations"]:
        if existing.get("generation_id") == claimed:
            if existing.get("kind") != kind or existing.get("semantic") != semantic:
                raise GenerationConflict("same generation_id carries conflicting semantics")
            return False
    candidate = copy.deepcopy(journey)
    candidate["generations"].append(copy.deepcopy(generation))
    _validate_journey(candidate)
    journey["generations"].append(copy.deepcopy(generation))
    return True


def _spec(*, dvol_w: int) -> dict:
    return {
        "identity": "d2",
        "direction": "down",
        "source": "deribit/dvol",
        "source_columns": ["dvol_high", "dvol_low", "dvol_close"],
        "input_transform": "(dvol_high-dvol_low)/dvol_close",
        "dvol_z_window": int(dvol_w),
        "fire_rule": "z>=2.0 OR (z>=1.5 AND lag1(z)>=1.5)",
        "entry_clock": "next_complete_btc_daily_close_after_source_observation",
        "horizon_bars": LABEL_H,
        "target_window": "(t,t+3 daily closes]",
        "threshold_pct": -LABEL_THR * 100.0,
        "trading_authority": False,
    }


def _normalize_frame(frame: pd.DataFrame | None) -> pd.DataFrame | None:
    if frame is None or not isinstance(frame, pd.DataFrame) or frame.empty:
        return None
    out = frame.copy()
    out.index = pd.to_datetime(out.index, errors="coerce")
    out = out.loc[~out.index.isna()].sort_index()
    if getattr(out.index, "tz", None) is not None:
        out.index = out.index.tz_convert("UTC").tz_localize(None)
    out.index = out.index.normalize()
    return out[~out.index.duplicated(keep="last")]


def _date(value: Any) -> pd.Timestamp | None:
    try:
        ts = pd.Timestamp(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(ts):
        return None
    if ts.tzinfo is not None:
        ts = ts.tz_convert("UTC").tz_localize(None)
    return ts.normalize()


def _finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _unavailable_source(
    *, entry: pd.Timestamp | None, source: pd.Timestamp | None, dvol_w: int,
    reason: str, observed_rows: int = 0,
) -> dict:
    entry_text = str(entry.date()) if entry is not None else None
    source_text = str(source.date()) if source is not None else None
    check_after = str((entry + timedelta(days=LABEL_H)).date()) if entry is not None else None
    return {
        "status": "unavailable",
        "entry_asof": entry_text,
        "source_asof": source_text,
        "check_after": check_after,
        "reason": reason,
        "spec": _spec(dvol_w=dvol_w),
        "inputs": {"observed_rows": int(observed_rows), "source_rows": []},
        "evaluator": {
            "version": SOURCE_EVALUATOR_VERSION,
            "collector": COLLECTOR_VERSION,
        },
        "prediction": {"fired": None, "trading_authority": False},
    }


def build_source_semantic(
    *, entry_asof: Any, sig_df: pd.DataFrame | None, dvol_df: pd.DataFrame | None,
    dvol_w: int = DVOL_WINDOW,
) -> dict:
    entry = _date(entry_asof)
    if entry is None:
        return _unavailable_source(
            entry=None, source=None, dvol_w=dvol_w, reason="entry_asof_invalid",
        )
    sig = _normalize_frame(sig_df)
    if sig is None or "close" not in sig.columns:
        return _unavailable_source(
            entry=entry, source=None, dvol_w=dvol_w, reason="btc_close_source_unavailable",
        )
    prior = sig.index[sig.index < entry]
    if entry not in sig.index or len(prior) == 0 or not _finite(sig.loc[entry, "close"]):
        return _unavailable_source(
            entry=entry, source=None, dvol_w=dvol_w,
            reason="requires_previous_complete_source_and_entry_close",
        )
    source = entry - timedelta(days=1)
    if source not in sig.index or not _finite(sig.loc[source, "close"]):
        return _unavailable_source(
            entry=entry, source=None, dvol_w=dvol_w,
            reason="previous_daily_btc_close_missing",
        )
    dvol = _normalize_frame(dvol_df)
    if dvol is None:
        return _unavailable_source(
            entry=entry, source=source, dvol_w=dvol_w, reason="dvol_source_unavailable",
        )
    required = {"dvol_high", "dvol_low", "dvol_close"}
    if not required <= set(dvol.columns):
        return _unavailable_source(
            entry=entry, source=source, dvol_w=dvol_w, reason="dvol_columns_incomplete",
            observed_rows=len(dvol),
        )
    through_source = dvol.loc[dvol.index <= source, list(sorted(required))]
    if source not in through_source.index:
        return _unavailable_source(
            entry=entry, source=source, dvol_w=dvol_w,
            reason="previous_complete_dvol_bar_missing", observed_rows=len(through_source),
        )
    needed = int(dvol_w) + 2
    window = through_source.tail(needed).copy()
    if len(window) < needed:
        return _unavailable_source(
            entry=entry, source=source, dvol_w=dvol_w,
            reason="dvol_history_incomplete", observed_rows=len(window),
        )
    rows: list[dict] = []
    for idx, row in window.iterrows():
        high, low, close = row["dvol_high"], row["dvol_low"], row["dvol_close"]
        if not all(_finite(v) for v in (high, low, close)) or float(close) <= 0:
            return _unavailable_source(
                entry=entry, source=source, dvol_w=dvol_w,
                reason="dvol_values_invalid", observed_rows=len(window),
            )
        rng = (float(high) - float(low)) / float(close)
        if not _finite(rng):
            return _unavailable_source(
                entry=entry, source=source, dvol_w=dvol_w,
                reason="dvol_range_invalid", observed_rows=len(window),
            )
        rows.append({
            "asof": str(pd.Timestamp(idx).date()),
            "dvol_high": float(high),
            "dvol_low": float(low),
            "dvol_close": float(close),
            "range": float(rng),
        })

    from engine import btc_impulse_radar

    ranges = pd.Series(
        [row["range"] for row in rows],
        index=pd.to_datetime([row["asof"] for row in rows]),
        dtype=float,
    )
    fired_series = btc_impulse_radar._d2_cond(ranges, int(dvol_w), ranges.index)
    fired = bool(fired_series.iloc[-1])
    entry_close = float(sig.loc[entry, "close"])
    return {
        "status": "available",
        "entry_asof": str(entry.date()),
        "source_asof": str(source.date()),
        "check_after": str((entry + timedelta(days=LABEL_H)).date()),
        "reason": None,
        "spec": _spec(dvol_w=dvol_w),
        "inputs": {
            "entry_close": entry_close,
            "source_rows": rows,
            "source_digest": _digest(rows),
        },
        "evaluator": {
            "version": SOURCE_EVALUATOR_VERSION,
            "collector": COLLECTOR_VERSION,
        },
        "prediction": {"fired": fired, "trading_authority": False},
    }


def _effective_source(journey: dict) -> tuple[dict | None, dict | None]:
    current_generation = None
    current_semantic = None
    for generation in journey.get("generations", []):
        if generation.get("kind") == "source":
            current_generation = generation
            current_semantic = generation.get("semantic")
        elif generation.get("kind") == "correction":
            semantic = generation.get("semantic") or {}
            if (
                semantic.get("target_kind") == "source"
                and current_generation is not None
                and semantic.get("supersedes_generation_id") == current_generation.get("generation_id")
                and isinstance(semantic.get("replacement"), dict)
            ):
                current_generation = generation
                current_semantic = semantic["replacement"]
    return current_generation, current_semantic


def _effective_outcome(
    journey: dict, source_generation_id: str,
) -> tuple[dict | None, dict | None]:
    current_generation = None
    current_semantic = None
    for generation in journey.get("generations", []):
        kind = generation.get("kind")
        semantic = generation.get("semantic") or {}
        if kind == "outcome" and semantic.get("source_generation_id") == source_generation_id:
            current_generation = generation
            current_semantic = semantic
        elif kind == "correction" and semantic.get("target_kind") == "outcome":
            replacement = semantic.get("replacement")
            if (
                current_generation is not None
                and semantic.get("supersedes_generation_id") == current_generation.get("generation_id")
                and isinstance(replacement, dict)
                and replacement.get("source_generation_id") == source_generation_id
            ):
                current_generation = generation
                current_semantic = replacement
    return current_generation, current_semantic


def capture_source(
    journey: dict, *, entry_asof: Any, sig_df: pd.DataFrame | None,
    dvol_df: pd.DataFrame | None, recorded_at: str | None = None,
    dvol_w: int = DVOL_WINDOW,
) -> bool:
    candidate = build_source_semantic(
        entry_asof=entry_asof, sig_df=sig_df, dvol_df=dvol_df, dvol_w=dvol_w,
    )
    current_generation, current_semantic = _effective_source(journey)
    if current_generation is None:
        return append_generation(
            journey, make_generation("source", candidate, recorded_at=recorded_at),
        )
    if current_semantic == candidate:
        return False
    current_status = (current_semantic or {}).get("status")
    candidate_status = candidate.get("status")
    # A later read outage is not a correction to a frozen historical source.
    # Likewise, repeated unavailable snapshots add no useful generation.  Only
    # late arrival (unavailable -> available) or an available-data restatement
    # may advance the append-only source chain.
    if candidate_status != "available":
        return False
    reason = (
        "late_source_arrival"
        if current_status != "available"
        else "source_restatement"
    )
    correction = {
        "target_kind": "source",
        "supersedes_generation_id": current_generation["generation_id"],
        "reason": reason,
        "replacement": candidate,
    }
    return append_generation(
        journey, make_generation("correction", correction, recorded_at=recorded_at),
    )


def build_outcome_semantic(
    source_generation_id: str, source_semantic: dict, sig_df: pd.DataFrame | None,
) -> dict | None:
    if source_semantic.get("status") != "available":
        return None
    entry = _date(source_semantic.get("entry_asof"))
    sig = _normalize_frame(sig_df)
    if entry is None or sig is None or "close" not in sig.columns or entry not in sig.index:
        return None
    close = pd.to_numeric(sig["close"], errors="coerce").sort_index()
    expected_future = pd.DatetimeIndex(
        [entry + timedelta(days=offset) for offset in range(1, LABEL_H + 1)]
    )
    if not expected_future.isin(close.index).all():
        return None
    future = close.reindex(expected_future)
    base = close.loc[entry]
    values = [base, *future.tolist()]
    if not all(_finite(value) for value in values) or float(base) <= 0:
        return None
    base_f = float(base)
    forward = [float(value) for value in future.tolist()]
    fwd_min = min(forward) / base_f - 1.0
    fwd_max = max(forward) / base_f - 1.0
    inputs = [{"asof": str(entry.date()), "close": base_f}]
    inputs.extend(
        {"asof": str(pd.Timestamp(idx).date()), "close": float(value)}
        for idx, value in future.items()
    )
    fired = bool((source_semantic.get("prediction") or {}).get("fired"))
    return {
        "source_generation_id": source_generation_id,
        "entry_asof": str(entry.date()),
        "spec": {
            "direction": "down",
            "horizon_bars": LABEL_H,
            "target_window": "(t,t+3 daily closes]",
            "threshold_pct": -LABEL_THR * 100.0,
            "trading_authority": False,
        },
        "inputs": {"close_rows": inputs, "close_digest": _digest(inputs)},
        "evaluator": {"version": OUTCOME_EVALUATOR_VERSION},
        "result": {
            "matured": True,
            "fwd_min_pct": round(fwd_min * 100.0, 2),
            "fwd_max_pct": round(fwd_max * 100.0, 2),
            "down_hit": bool(fired and fwd_min <= -LABEL_THR),
        },
        "trading_authority": False,
    }


def mature_outcome(
    journey: dict, sig_df: pd.DataFrame | None, *, recorded_at: str | None = None,
) -> bool:
    source_generation, source_semantic = _effective_source(journey)
    if source_generation is None or source_semantic is None:
        return False
    candidate = build_outcome_semantic(
        source_generation["generation_id"], source_semantic, sig_df,
    )
    if candidate is None:
        return False
    current_generation, current_semantic = _effective_outcome(
        journey, source_generation["generation_id"],
    )
    if current_generation is None:
        return append_generation(
            journey, make_generation("outcome", candidate, recorded_at=recorded_at),
        )
    if current_semantic == candidate:
        return False
    correction = {
        "target_kind": "outcome",
        "supersedes_generation_id": current_generation["generation_id"],
        "reason": "outcome_input_restatement",
        "replacement": candidate,
    }
    return append_generation(
        journey, make_generation("correction", correction, recorded_at=recorded_at),
    )


def project(journey: dict | None) -> dict:
    base = {
        "schema": SCHEMA,
        "status": "unavailable",
        "entry_asof": None,
        "source_asof": None,
        "check_after": None,
        "fired": None,
        "trading_authority": False,
        "source_generation_id": None,
        "outcome_generation_id": None,
        "generation_count": 0,
        "outcome": None,
        "reason": "no_source_generation",
    }
    if not isinstance(journey, dict) or journey.get("schema") != SCHEMA:
        return base
    base["generation_count"] = len(journey.get("generations", []))
    try:
        _validate_journey(journey)
    except GenerationConflict:
        base["reason"] = "generation_integrity_error"
        return base
    source_generation, source_semantic = _effective_source(journey)
    if source_generation is None or not isinstance(source_semantic, dict):
        return base
    prediction = source_semantic.get("prediction") or {}
    base.update({
        "entry_asof": source_semantic.get("entry_asof"),
        "source_asof": source_semantic.get("source_asof"),
        "check_after": source_semantic.get("check_after"),
        "fired": prediction.get("fired"),
        "source_generation_id": source_generation.get("generation_id"),
        "reason": source_semantic.get("reason"),
    })
    if source_semantic.get("status") != "available":
        return base
    base["status"] = "pending"
    outcome_generation, outcome_semantic = _effective_outcome(
        journey, source_generation["generation_id"],
    )
    if outcome_generation is None or not isinstance(outcome_semantic, dict):
        return base
    base.update({
        "status": "matured",
        "outcome_generation_id": outcome_generation.get("generation_id"),
        "outcome": copy.deepcopy(outcome_semantic.get("result")),
        "reason": None,
    })
    return base

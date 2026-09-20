#!/usr/bin/env python3
"""Run the frozen TTI R1-B v4 corrected-history study offline.

Admission is fail-closed and precedes every market-input read.  This consumer
uses existing D0/Radar owners; it opens no network/provider path and has no live
rank, alert, sizing, event-emission, options or trade authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from engine.entry_radar import tactical_exhaustion as te  # noqa: E402
from engine.session_digest import session_window_et  # noqa: E402
from scripts.research import terminal_tactical_r1_study as r1  # noqa: E402

CONFIG_PATH = ROOT / "research/species/tti_r1b/config_v4.json"
PREREG_PATH = ROOT / "research/species/TTI_R1B_V4_PREREG.md"
RECEIPT_PATH = ROOT / "research/species/tti_r1b/REGISTRATION_RECEIPT_V4.json"
LEDGER_PATH = ROOT / "data/trial_ledger.jsonl"
STUDY_ID = "tti-r1b-exhaustion-reclaim-v4"
UTC = timezone.utc


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _grid_cells(cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {"study_id": cfg["study_id"], "selector": selector,
         "horizon": horizon, "round_trip_cost_bps": int(cost)}
        for selector in cfg["selectors"]
        for horizon in cfg["horizons"]
        for cost in cfg["round_trip_cost_bps"]
    ]


def verify_admission(
    *, config_path: Path = CONFIG_PATH, prereg_path: Path = PREREG_PATH,
    receipt_path: Path = RECEIPT_PATH, ledger_path: Path = LEDGER_PATH,
    enforce_receipt_ledger_sha: bool = True,
    before_input: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Verify frozen scientific identity and 60-cell registration before inputs."""
    receipt = json.loads(receipt_path.read_text())
    config_bytes = config_path.read_bytes()
    cfg = json.loads(config_bytes)
    if cfg.get("study_id") != STUDY_ID:
        raise ValueError("study_id_mismatch")
    config_sha = hashlib.sha256(config_bytes).hexdigest()
    prereg_sha = _sha(prereg_path)
    if config_sha != receipt.get("config_sha256") or config_sha != te.CONFIG_SHA256:
        raise ValueError("config_sha256_mismatch")
    if prereg_sha != receipt.get("prereg_sha256"):
        raise ValueError("prereg_sha256_mismatch")
    if receipt.get("study_id") != STUDY_ID or receipt.get("family") != cfg.get("trial_family"):
        raise ValueError("registration_receipt_identity_mismatch")
    if receipt.get("prefix_preserved") is not True:
        raise ValueError("registration_prefix_not_preserved")
    if receipt.get("market_outcomes_opened_before_registration") is not False:
        raise ValueError("registration_precedes_outcomes_not_proven")
    wanted = {json.dumps(x, sort_keys=True, separators=(",", ":")) for x in _grid_cells(cfg)}
    if len(wanted) != int(cfg.get("full_grid_size", -1)) or len(wanted) != 60:
        raise ValueError("frozen_grid_size_mismatch")
    raw_ledger = ledger_path.read_bytes()
    if enforce_receipt_ledger_sha and hashlib.sha256(raw_ledger).hexdigest() != receipt.get("ledger_after_sha256"):
        raise ValueError("ledger_sha256_mismatch")
    found: set[str] = set()
    for line in raw_ledger.decode("utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        value = row.get("config")
        if row.get("family") == cfg["trial_family"] and isinstance(value, dict) and value.get("study_id") == STUDY_ID:
            found.add(json.dumps(value, sort_keys=True, separators=(",", ":")))
    if found != wanted:
        raise ValueError(f"registered_grid_mismatch:{len(found)}/{len(wanted)}")
    if int(receipt.get("study_rows", -1)) != len(wanted):
        raise ValueError("registration_receipt_cell_count_mismatch")
    if before_input is not None:
        before_input()
    return {
        "study_id": STUDY_ID,
        "study_cells": len(wanted),
        "registration_commit": receipt.get("registration_commit"),
        "config_sha256": config_sha,
        "prereg_sha256": prereg_sha,
        "ledger_sha256": hashlib.sha256(raw_ledger).hexdigest(),
        "market_outcomes_opened_before_registration": False,
        "market_data_read": False,
        "outcomes_computed": False,
    }


def qqq_open_to_decision_sign(
    frame: pd.DataFrame, decision_at: pd.Timestamp | datetime,
    *, expected_start: pd.Timestamp | datetime | None = None,
) -> int | None:
    """Candidate-time QQQ sign from an exact positive-volume five-minute prefix."""
    if not isinstance(frame, pd.DataFrame) or any(c not in frame.columns for c in
            ("open", "high", "low", "close", "volume")):
        return None
    if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.tz is None or frame.index.hasnans:
        return None
    decision = pd.Timestamp(decision_at)
    if decision.tzinfo is None:
        return None
    start = pd.Timestamp(expected_start) if expected_start is not None else (frame.index[0] if len(frame) else None)
    if start is None or start.tzinfo is None:
        return None
    frame_tz = frame.index.tz
    decision = decision.tz_convert(frame_tz)
    start = start.tz_convert(frame_tz)
    if decision <= start:
        return None
    expected = list(pd.date_range(start, decision - pd.Timedelta(minutes=5), freq="5min"))
    rows = frame[(frame.index >= start) & (frame.index < decision)]
    if len(rows) != len(expected) or list(rows.index) != expected or rows.index.has_duplicates:
        return None
    values: list[tuple[float, float]] = []
    for _, row in rows.iterrows():
        raw = [row[c] for c in ("open", "high", "low", "close", "volume")]
        try:
            o, h, low, c, v = map(float, raw)
        except (TypeError, ValueError):
            return None
        if not all(math.isfinite(x) for x in (o, h, low, c, v)) or min(o, h, low, c) <= 0 or v <= 0:
            return None
        if not low <= min(o, c) <= max(o, c) <= h:
            return None
        values.append((o, c))
    if not values:
        return None
    change = values[-1][1] - values[0][0]
    return 1 if change > 0 else -1 if change < 0 else 0



def construct_one_day(
    symbol: str, session: date, stock_frame: pd.DataFrame,
    benchmark_frame: pd.DataFrame, stock_daily: pd.DataFrame,
    benchmark_daily: pd.DataFrame, *, config_bytes: bytes | None = None,
) -> dict[str, Any]:
    """Compose frozen v4 normalization + construction for one symbol/session."""
    frozen = CONFIG_PATH.read_bytes() if config_bytes is None else config_bytes
    normalization = te.build_prior_normalization(
        stock_daily, benchmark_daily, session=session, config_bytes=frozen)
    empty = {"normalization": normalization, "construction": None,
             "events": [], "controls": [], "anchors": {}}
    if normalization.get("availability") != "AVAILABLE":
        return empty
    prior_text = normalization.get("prior_session")
    if not isinstance(prior_text, str):
        return empty
    start, close = session_window_et(session)
    construction = te.construct_session(
        stock_frame, symbol=symbol, session=session,
        prior_session=date.fromisoformat(prior_text),
        prior_close=float(normalization["prior_close"]),
        prior_atr=float(normalization["prior_atr"]), asof=close,
        config_bytes=frozen, price_basis="adjusted")
    anchors = {str(row["anchor_id"]): dict(row)
               for row in construction.get("anchors", [])
               if isinstance(row, dict) and isinstance(row.get("anchor_id"), str)}
    events: list[dict[str, Any]] = []
    for raw in construction.get("events", []):
        event = dict(raw)
        candidate_at = pd.Timestamp(event["candidate_at"])
        sign = qqq_open_to_decision_sign(
            benchmark_frame, candidate_at, expected_start=start)
        event.update(symbol=symbol, session=session.isoformat(),
                     qqq_open_to_decision_sign=sign,
                     beta=normalization.get("beta") if normalization.get("beta_available") else None,
                     market_outcomes_computed=False)
        events.append(event)
    controls: list[dict[str, Any]] = []
    for raw in construction.get("control_census", []):
        control = dict(raw)
        candidate_at = pd.Timestamp(control["candidate_at"])
        control["qqq_open_to_decision_sign"] = qqq_open_to_decision_sign(
            benchmark_frame, candidate_at, expected_start=start)
        controls.append(control)
    return {"normalization": normalization, "construction": construction,
            "events": events, "controls": controls, "anchors": anchors}


def measure_event_grid(
    event: Mapping[str, Any], stock_frame: pd.DataFrame,
    benchmark_frame: pd.DataFrame, *, session: date,
    config_bytes: bytes | None = None,
) -> list[dict[str, Any]]:
    """Measure all 4×3 registered v4 cells for one already-fired event."""
    frozen = CONFIG_PATH.read_bytes() if config_bytes is None else config_bytes
    cfg = json.loads(frozen)
    rows: list[dict[str, Any]] = []
    beta = event.get("beta")
    beta_value = float(beta) if isinstance(beta, (int, float)) and not isinstance(beta, bool) and math.isfinite(float(beta)) else None
    for horizon in cfg["horizons"]:
        for cost in cfg["round_trip_cost_bps"]:
            measured = te.measure_event_outcome(
                stock_frame, benchmark_frame, event=dict(event), session=session,
                horizon=str(horizon), beta=beta_value, cost_bps=int(cost),
                config_bytes=frozen)
            row = dict(measured)
            row.update(symbol=event.get("symbol"), date=session.isoformat(),
                       qqq_open_to_decision_sign=event.get("qqq_open_to_decision_sign"))
            rows.append(row)
    return rows


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--terminal-root", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        admitted = verify_admission()
        if args.verify_only:
            print(json.dumps(admitted, sort_keys=True))
            return 0
        if None in (args.input_dir, args.manifest, args.terminal_root, args.output_dir):
            raise ValueError("full_run_requires_input_manifest_terminal_output")
        raise ValueError("empirical_runner_not_yet_implemented")
    except Exception as exc:
        print(f"R1-B study refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

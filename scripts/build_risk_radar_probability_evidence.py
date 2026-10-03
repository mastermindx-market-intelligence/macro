"""Publish display-only Risk Radar probability evidence from the accepted audit.

This is a provenance projection only. It never writes calibration.json and never
changes the probability surface, state machine, policy, sizing or authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "research/grey_deer/evidence/displayed-probability-audit-20260922/result.json"
OUTPUT = ROOT / "data/risk_radar/probability_evidence.json"

SOURCE_SCHEMA = "risk_radar_displayed_probability_audit.v1"
OUTPUT_SCHEMA = "risk_radar_probability_evidence.v1"
WINDOW = "y2020"
HORIZONS = ("h5", "h10", "h21")
_CELL_FIELDS = (
    "probability",
    "n",
    "events",
    "observed_rate",
    "observed_minus_displayed",
    "observed_rate_ci90",
    "thin",
    "composition",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_payload(source: Path = SOURCE) -> dict[str, Any]:
    doc = json.loads(source.read_text(encoding="utf-8"))
    if doc.get("schema") != SOURCE_SCHEMA:
        raise ValueError(f"unexpected source schema: {doc.get('schema')!r}")

    targets = doc.get("targets") or {}
    if targets.get("depth") != 0.05 or targets.get("horizons") != [5, 10, 21]:
        raise ValueError("source target drifted from the accepted >=5% / H5,H10,H21 audit")

    horizons: dict[str, Any] = {}
    for horizon in HORIZONS:
        result = ((doc.get("results") or {}).get(horizon) or {}).get(WINDOW)
        if not isinstance(result, dict):
            raise ValueError(f"missing accepted {horizon}/{WINDOW} result")
        cells = result.get("cells") or {}
        out_cells: dict[str, Any] = {}
        for key, cell in sorted(cells.items(), key=lambda item: float(item[0])):
            out_cells[str(key)] = {field: cell.get(field) for field in _CELL_FIELDS}
        horizons[horizon] = {
            "from": result.get("from"),
            "through": result.get("through"),
            "n": result.get("n"),
            "events": result.get("events"),
            "base_rate": result.get("base_rate"),
            "mean_displayed_probability": result.get("mean_displayed_probability"),
            "brier_skill_score": result.get("brier_skill_score"),
            "weighted_absolute_calibration_error": result.get("weighted_absolute_calibration_error"),
            "population_sha256": result.get("population_sha256"),
            "cells": out_cells,
        }

    return {
        "schema": OUTPUT_SCHEMA,
        "evidence_class": "reconstructed_historical",
        "precision_grade": False,
        "use": "Display evidence depth only; never calibration, gating, sizing or authority.",
        "window": WINDOW,
        "target": {
            "depth": 0.05,
            "horizons": [5, 10, 21],
            "price_path": "native SPY closing observations",
        },
        "limitations": [
            "Overlapping forward windows are not independent episodes.",
            "Reconstructed historical states are not genuinely issued forecasts.",
            "Exact-cell evidence supports a risk gradient, not actuarial precision.",
        ],
        "source": {
            "path": str(source.relative_to(ROOT)),
            "sha256": _sha256(source),
            "schema": doc.get("schema"),
            "protocol_commit": doc.get("protocol_commit"),
            "source_base": doc.get("source_base"),
        },
        "model_surface": {
            "state_probability_surface": doc.get("state_probability_surface"),
            "conjunction_bump": doc.get("conjunction_bump"),
        },
        "horizons": horizons,
    }


def write_payload(output: Path = OUTPUT, source: Path = SOURCE) -> dict[str, Any]:
    payload = build_payload(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    write_payload(args.output, args.source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

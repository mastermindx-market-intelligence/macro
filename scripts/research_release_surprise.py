"""Reproduce MRI surprise/confirmation studies from source-bound local inputs.

Uses the incumbent TrialLedger BEFORE return evaluation. No network, provider
purchase, live ranking, execution, or promotion. The dataset must name an actual
exchange-calendar source and adjusted-price evidence. Synthetic fixtures must be
labeled synthetic; retrospective reconstruction never becomes prospective proof.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from engine.release_surprise_confirmation import (
    ACTUALS_PATH, CONSENSUS_PATH, DEFECTS_PATH, MAX_INPUT_BYTES, PAIR_DEFINITIONS,
    EvidenceError, authority, build_confirmation_pairs, build_surprise_history,
    digest, instant, read_jsonl,
)
from engine.release_surprise_study import (
    CONDITIONS, DEFAULT_HORIZONS, DEFAULT_SYMBOLS, FEATURES, SCHEMA,
    evaluate_matrix, forward_outcomes, join_regime_features, walk_forward,
)
from engine.trial_ledger import TrialLedger

FAMILY = "macro_surprise_confirmation_v1"


def run_study(root: Path, dataset: dict, *, asof: str, trial_ledger: Path,
              symbols=DEFAULT_SYMBOLS, horizons=DEFAULT_HORIZONS,
              round_trip_cost_bps: float = 0, draws: int = 800,
              min_cell_n: int = 30, min_train: int = 60,
              regime_names=(), consensus_source_id: str | None = None) -> dict:
    instant(asof)
    if not isinstance(dataset, dict) or dataset.get("schema") != "release_surprise_dataset.v1":
        raise EvidenceError("dataset_schema_mismatch")
    for field in ("calendar_source_ref", "price_source_ref", "rights_ref"):
        if not isinstance(dataset.get(field), str) or not dataset[field]:
            raise EvidenceError("dataset_" + field + "_missing")
    if dataset.get("evidence_class") not in {"synthetic", "retrospective_pit", "prospective_capture"}:
        raise EvidenceError("dataset_evidence_class_required")
    if "internal_research" not in dataset.get("use_scopes", []):
        raise EvidenceError("dataset_research_rights_not_supplied")
    if not isinstance(dataset.get("session_closes"), list) or not isinstance(dataset.get("bars"), list):
        raise EvidenceError("dataset_calendar_or_prices_missing")
    actuals, actual_meta = read_jsonl(root / ACTUALS_PATH)
    polls, consensus_meta = read_jsonl(root / CONSENSUS_PATH)
    if any(meta["status"] not in {"ready", "empty", "missing"} for meta in (actual_meta, consensus_meta)):
        raise EvidenceError("release_input_integrity_failure")
    config = {"version": 1, "pairs": [row[0] for row in PAIR_DEFINITIONS],
              "symbols": list(symbols), "horizons": list(horizons), "conditions": list(CONDITIONS),
              "round_trip_cost_bps": round_trip_cost_bps, "bootstrap_draws": draws,
              "bootstrap_mean_block": 3, "bootstrap_seed": 7, "min_cell_n": min_cell_n,
              "features": [*FEATURES, *("regime:" + name for name in regime_names)],
              "min_train": min_train, "ridge_alpha": 10, "embargo_hours": 24,
              "consensus_source_id": consensus_source_id,
              "entry": "first_session_close_strictly_after_signal_known_at"}
    ledger = TrialLedger(trial_ledger, family=FAMILY)
    if ledger.load_error or ledger.corrupt_lines:
        raise EvidenceError("trial_ledger_integrity_failure")
    ledger.log_grid([config], info_cutoff=asof, source="release_surprise_study",
                    note="Whole declared family; before evaluating returns; not proof of preregistration before source inspection")
    trial_receipt = digest({"family": FAMILY, "config": config})
    history = build_surprise_history(actuals, polls, asof=asof, defects_path=root / DEFECTS_PATH,
                                    consensus_source_id=consensus_source_id)
    pairs = build_confirmation_pairs(history["events"])
    if regime_names:
        pairs = join_regime_features(pairs, dataset.get("regime_observations", []), names=regime_names)
    outcomes = forward_outcomes(pairs, dataset["bars"], dataset["session_closes"],
                                symbols=symbols, horizons=horizons, asof=asof,
                                round_trip_cost_bps=round_trip_cost_bps)
    # Individual releases keep THEIR OWN entry clocks and are descriptive only;
    # they are not added to the paired inferential family after seeing a result.
    individual = forward_outcomes(history["events"], dataset["bars"], dataset["session_closes"],
                                  symbols=symbols, horizons=horizons, asof=asof,
                                  round_trip_cost_bps=round_trip_cost_bps)
    matrix = evaluate_matrix(outcomes["rows"], symbols=symbols, horizons=horizons,
                             draws=draws, min_cell_n=min_cell_n)
    challenger = walk_forward(outcomes["rows"], min_train=min_train, features=config["features"])
    result = {"schema": SCHEMA, "asof": asof, "status": "evaluated_exploratory" if outcomes["rows"] else "insufficient_data",
              "authority": authority(), "research_status": "not_validated_for_live_use",
              "dataset_evidence_class": dataset["evidence_class"],
              "prospective_validation_claim": False,
              "input_receipts": {"actuals": actual_meta, "consensus": consensus_meta,
                                 "dataset_sha256": digest(dataset), "calendar_source_ref": dataset["calendar_source_ref"],
                                 "price_source_ref": dataset["price_source_ref"], "rights_ref": dataset["rights_ref"]},
              "trial_family": FAMILY, "trial_receipt": trial_receipt, "declared_config": config,
              "history_quality": {k: v for k, v in history.items() if k != "events"},
              "paired_outcomes": outcomes, "individual_outcomes_descriptive_only": individual,
              "matrix": matrix, "walk_forward": challenger,
              "limitations": ["Matched event-date baseline is not a continuous investable portfolio backtest.",
                              "Bootstrap mean-gap intervals are not individual outcome prediction intervals.",
                              "Costs are an explicit scenario; spread and execution feasibility need separate evidence.",
                              "Rights references require the existing data owner's qualification.",
                              "Synthetic or retrospectively reconstructed observations do not establish prospective alpha."]}
    result["evidence_digest"] = digest(result)
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=_ROOT)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--asof", required=True)
    parser.add_argument("--trial-ledger", type=Path, required=True, help="Existing owner TrialLedger path; use a fixture path for synthetic runs")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cost-bps", type=float, default=0)
    parser.add_argument("--consensus-source-id")
    parser.add_argument("--regime", action="append", default=[], help="Predeclared existing-owner regime feature name")
    args = parser.parse_args(argv)
    try:
        with args.dataset.open("rb") as handle:
            raw = handle.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise EvidenceError("dataset_oversized")
        dataset = json.loads(raw)
        result = run_study(args.root, dataset, asof=args.asof, trial_ledger=args.trial_ledger,
                           round_trip_cost_bps=args.cost_bps, regime_names=args.regime,
                           consensus_source_id=args.consensus_source_id)
        encoded = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            # Results are evidence, not a mutable latest pointer. Never silently
            # overwrite a previous run or a live producer artifact.
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(encoded)
            print(json.dumps({"status": result["status"], "output": str(args.output), "evidence_digest": result["evidence_digest"]}))
        else:
            print(encoded)
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "refused", "reason": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run the PB-D research adapters from explicit, replayable JSON inputs.

Examples (from repository root)::

    python -m scripts.query_pb_d_event_quality quality --input review.json
    python -m scripts.query_pb_d_event_quality freeze --input cohort.json
    python -m scripts.query_pb_d_event_quality run --input research_packet.json

The integrated path is an offline consumer. It does not register a cohort,
fetch news/prices, schedule collection, or modify any source/forward ledger.
Supplied owner receipts are structurally checked, not independently acquired.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import fields, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping

from engine.company_intelligence.pb_d_quality import build_quality_receipt
from engine.pb_d_cohort import freeze_cohort, rematch_omission, verify_manifest
from engine.pb_d_evaluation import EvaluationContext, FrozenPair, OmissionSensitivity, Outcome, evaluate_pb_d


RESEARCH_HEAD = "df2091915159dab94f316718caa9b2662098eae4"
HORIZONS = (1, 5, 10, 21)
DATASET_KINDS = {"SYNTHETIC_DRY_RUN", "OFFLINE_OBSERVATION"}
_OUTCOME_FIELDS = {field.name for field in fields(Outcome)}
_RECEIPT_FIELDS = {
    "observation_id", "price_receipt_ref", "entry_session_date", "entry_close_at_utc",
    "outcome_observed_at", "outcome_available_at",
    *(f"h{h}_exit_session_date" for h in HORIZONS),
    *(f"h{h}_exit_close_at_utc" for h in HORIZONS),
}


def _object(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a JSON object")
    return value


def _instant(value: Any, name: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be an aware ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name} must be an aware ISO timestamp") from exc
    if parsed.utcoffset() is None:
        raise ValueError(f"{name} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _canonical_digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                     allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _quality_and_cohort(packet: Mapping[str, Any]) -> tuple[dict, dict]:
    cohort = deepcopy(dict(_object(packet["cohort"], "cohort")))
    requests = _object(packet.get("quality_requests", {}), "quality_requests")
    indexed: dict[str, tuple[dict, Mapping[str, Any]]] = {}
    for cut in cohort.get("cuts", []):
        for row in cut.get("rows", []):
            observation = row["observation_id"]
            if observation in indexed:
                raise ValueError("duplicate observation_id across cuts")
            indexed[observation] = (cut, row)
    receipts = {}
    for observation, request in sorted(requests.items()):
        if observation not in indexed:
            raise ValueError("quality request has no matching board observation")
        cut, row = indexed[observation]
        request = dict(_object(request, "quality request"))
        if request.get("issuer_id") != row.get("canonical_issuer_id"):
            raise ValueError("quality request issuer differs from the board observation")
        if request.get("ticker_at_cut", row.get("ticker_at_cut")) != row.get("ticker_at_cut"):
            raise ValueError("quality request ticker differs from the board observation")
        count = row.get("attention_n_recent")
        attention = count >= 3 if (row.get("attention_coverage_complete") is True
                                   and type(count) is int and count >= 0) else None
        if "raw_attention" in request and request["raw_attention"] is not attention:
            raise ValueError("quality request attention differs from the frozen board attention")
        request["ticker_at_cut"] = row.get("ticker_at_cut")
        request["raw_attention"] = attention
        target = cut.setdefault("quality_by_observation", {})
        if observation in target:
            raise ValueError("quality request would replace an existing as-known receipt")
        receipt = build_quality_receipt(**dict(request))
        target[observation] = receipt
        receipts[observation] = receipt
    return receipts, freeze_cohort(cohort)


def _outcomes_by_observation(rows: Any, first_rows: Mapping[str, Mapping]) -> dict[str, dict]:
    if not isinstance(rows, list):
        raise ValueError("outcomes must be an array")
    result = {}
    for raw in rows:
        row = dict(_object(raw, "outcome"))
        unknown = set(row) - _OUTCOME_FIELDS - _RECEIPT_FIELDS
        if unknown:
            raise ValueError(f"unknown outcome fields: {sorted(unknown)}")
        observation = row.get("observation_id")
        if observation not in first_rows:
            raise ValueError("outcome must refer to a retained first-T2 observation")
        if observation in result:
            raise ValueError("duplicate outcome for one observation")
        frozen = first_rows[observation]
        if row.get("issuer_id") != frozen["canonical_issuer_id"]:
            raise ValueError("outcome issuer differs from the frozen observation")
        if row.get("ticker_at_cut") != frozen["ticker_at_cut"]:
            raise ValueError("outcome ticker differs from the frozen observation")
        result[observation] = row
    return result


def _leg_outcome(observation: str, frozen: Mapping, pair: Mapping,
                 outcomes: Mapping[str, Mapping]) -> Outcome:
    raw = outcomes.get(observation)
    if raw is None:
        return Outcome(
            issuer_id=frozen["canonical_issuer_id"], ticker_at_cut=frozen["ticker_at_cut"],
            **{f"h{h}_missing_reason": "NO_OUTCOME_RECEIPT" for h in HORIZONS},
        )
    values = {key: raw[key] for key in _OUTCOME_FIELDS if key in raw}
    numeric_horizons = [
        h for h in HORIZONS
        if any(raw.get(f"h{h}_{suffix}") is not None
               for suffix in ("spy_excess_pp", "absolute_return_pp", "sector_excess_pp"))
        or (h == 5 and raw.get("h5_clean_liftoff") is not None)
    ]
    if numeric_horizons:
        if raw.get("entry_status") != "FILLED":
            raise ValueError("observed outcomes require an explicitly filled entry")
        if not isinstance(raw.get("price_receipt_ref"), str) or not raw["price_receipt_ref"].strip():
            raise ValueError("observed outcomes require an owner price receipt reference")
        if raw.get("entry_session_date") != pair["entry_session_date"]:
            raise ValueError("outcome entry session differs from the frozen pair")
        if _instant(raw.get("entry_close_at_utc"), "entry close") != _instant(
            pair["entry_close_at_utc"], "frozen entry close"
        ):
            raise ValueError("outcome entry close differs from the frozen pair")
        observed = _instant(raw.get("outcome_observed_at"), "outcome observed")
        available = _instant(raw.get("outcome_available_at"), "outcome available")
        if available < observed:
            raise ValueError("outcome availability precedes its observation")
        for horizon in numeric_horizons:
            endpoint = pair["exits"][f"H{horizon}"]
            if raw.get(f"h{horizon}_exit_session_date") != endpoint["session_date"]:
                raise ValueError("outcome exit session differs from the frozen horizon")
            scheduled = _instant(endpoint["close_at_utc"], "frozen exit close")
            if _instant(raw.get(f"h{horizon}_exit_close_at_utc"), "outcome exit close") != scheduled:
                raise ValueError("outcome exit close differs from the frozen horizon")
            if observed < scheduled:
                raise ValueError("outcome was observed before its scheduled exit")
    return Outcome(**values)


def _compile_pairs(records: list, first_rows: Mapping, checked_outcomes: Mapping,
                   sessions: tuple[str, ...]) -> list[FrozenPair]:
    frozen_pairs = []
    for pair in records:
        q1_id, q0_id = pair["q1_observation_id"], pair["q0_observation_id"]
        q1 = checked_outcomes.get(q1_id) or _leg_outcome(q1_id, first_rows[q1_id], pair, {})
        q0 = checked_outcomes.get(q0_id) or _leg_outcome(q0_id, first_rows[q0_id], pair, {})
        # Both arms share the exact date and benchmarks. Where supplied, the
        # three paired mean increments must therefore agree algebraically.
        for horizon in HORIZONS:
            increments = [
                getattr(q1, f"h{horizon}_{kind}") - getattr(q0, f"h{horizon}_{kind}")
                for kind in ("spy_excess_pp", "absolute_return_pp", "sector_excess_pp")
                if getattr(q1, f"h{horizon}_{kind}") is not None
                and getattr(q0, f"h{horizon}_{kind}") is not None
            ]
            if increments and max(increments) - min(increments) > 1e-9:
                raise ValueError("paired absolute/SPY/sector increments disagree; verify benchmark windows")
        frozen_pairs.append(FrozenPair(
            pair_id=pair["pair_id"], session_index=sessions.index(pair["decision_date"]),
            q1=q1, q0=q0, sector=pair["sector"],
        ))
    return frozen_pairs


def _coverage_flow(first_rows: Mapping, pairs: list, outcomes: Mapping) -> dict:
    """Describe every consumed first T2, including unknown/unmatched rows."""
    matched = {observation for pair in pairs
               for observation in (pair["q1_observation_id"], pair["q0_observation_id"])}
    result = {}
    for field in ("decision_date", "sector", "raw_attention", "q"):
        groups = {}
        for observation, row in first_rows.items():
            value = row.get(field)
            label = "UNKNOWN" if value is None else str(value)
            group = groups.setdefault(label, {
                "first_t2_count": 0, "quality_known_count": 0, "quality_unknown_count": 0,
                "q_true_count": 0, "q_false_count": 0, "matching_eligible_count": 0,
                "matched_issuer_count": 0, "filled_entry_count": 0, "known_h5_count": 0,
            })
            group["first_t2_count"] += 1
            group["quality_known_count"] += row["q"] in {"TRUE", "FALSE"}
            group["quality_unknown_count"] += row["q"] == "UNKNOWN"
            group["q_true_count"] += row["q"] == "TRUE"
            group["q_false_count"] += row["q"] == "FALSE"
            group["matching_eligible_count"] += row["matching_eligible"]
            group["matched_issuer_count"] += observation in matched
            outcome = outcomes.get(observation)
            group["filled_entry_count"] += outcome is not None and outcome.entry_status == "FILLED"
            group["known_h5_count"] += outcome is not None and outcome.h5_spy_excess_pp is not None
        for group in groups.values():
            group["quality_coverage_fraction"] = group["quality_known_count"] / group["first_t2_count"]
        result[field] = dict(sorted(groups.items()))
    return {"scope": "ALL_RETAINED_FIRST_T2_OBSERVATIONS", "groups": result}


def evaluate_manifest(envelope: Mapping[str, Any], outcomes: list,
                      *, dataset_kind: str = "OFFLINE_OBSERVATION") -> dict:
    """Join outcome receipts after verifying a frozen selector manifest.

    This does not offer an activation flag. The nightly registration owner has
    not admitted PB-D's same-day premarket clock; supplied data remain offline.
    The 252-session population cannot be replaced by only active dates.
    """
    if dataset_kind not in DATASET_KINDS:
        raise ValueError("this consumer supports synthetic or offline data, not activation")
    if not verify_manifest(envelope):
        raise ValueError("frozen cohort manifest failed integrity verification")
    manifest = envelope["manifest"]
    first_rows = {row["observation_id"]: row for row in manifest["first_t2"]}
    by_observation = _outcomes_by_observation(outcomes, first_rows)
    # Validate every supplied record, including retained but unmatched issuers.
    # The latter do not enter the primary statistic, but cannot acquire a false
    # provenance label merely because the matching loop never visits them.
    checked_outcomes = {
        observation: _leg_outcome(observation, first_rows[observation],
                                  first_rows[observation], by_observation)
        for observation in by_observation
    }
    scheduled = [session["session_date"] for session in manifest["schedule"]["sessions"]]
    first_index = scheduled.index(manifest["first_cut_date"])
    sessions = tuple(scheduled[first_index:first_index + 252])
    if len(sessions) != 252:
        raise ValueError("analysis requires all 252 scheduled enrollment sessions, including inactive dates")
    frozen_pairs = _compile_pairs(manifest["pairs"], first_rows, checked_outcomes, sessions)
    accounting = manifest["accounting"]
    eligible = [row for row in first_rows.values() if row["matching_eligible"]]
    context = EvaluationContext(
        cohort_id=manifest["cohort_id"], session_dates=sessions, dataset_kind=dataset_kind,
        first_t2_count=accounting["first_observed_t2"],
        complete_primary_exposure_count=accounting["quality_known"],
        eligible_q1_count=accounting["eligible_q_true"],
        calendar_receipt_ref=manifest["schedule"]["validation_receipt_id"],
        calendar_complete=None,  # A supplied validation flag is not independent calendar proof.
        enrollment_complete=False, final_h21_matured=None,
        frozen_matching_receipt_ref=envelope["manifest_sha256"],
        eligible_pool_receipt_ref=envelope["manifest_sha256"],
        eligible_issuer_ids=tuple(sorted(row["canonical_issuer_id"] for row in eligible)),
        intc_issuer_ids=tuple(sorted(row["canonical_issuer_id"] for row in eligible
                                    if row["ticker_at_cut"].upper() == "INTC")),
    )
    # Each sensitivity reruns the frozen matcher over both original eligible
    # pools. Outcome values are joined only after the alternate pairs exist.
    omission_receipts, omissions = [], []
    omission_specs = [
        *( ("ISSUER", f"without:{issuer}", (issuer,)) for issuer in context.eligible_issuer_ids ),
        ("INTC", "without:INTC", context.intc_issuer_ids),
    ]
    for field, kind in (("decision_date", "DATE"), ("sector", "SECTOR")):
        for value in sorted({pair[field] for pair in manifest["pairs"]}):
            ids = tuple(sorted(row["canonical_issuer_id"] for row in eligible if row[field] == value))
            omission_specs.append((kind, f"without-{field}:{value}", ids))
    for kind, label, ids in omission_specs:
        receipt = rematch_omission(envelope, ids)
        omission_receipts.append({"kind": kind, "label": label, "receipt": receipt})
        omissions.append(OmissionSensitivity(
            kind=kind, label=label,
            pairs=tuple(_compile_pairs(receipt["pairs"], first_rows, checked_outcomes, sessions)),
            omitted_issuer_ids=tuple(ids), full_pool_rematch_receipt_ref=receipt["receipt_sha256"],
            eligible_q1_count=receipt["eligible_q1_count"],
        ))
    corrections = [entry["correction"] for entry in envelope["corrections"]]
    integrity_targets = {entry["target_observation_id"] for entry in corrections
                         if entry["correction_type"] == "DATA_INTEGRITY_EXCEPTION"}
    if integrity_targets:
        context = replace(context, integrity_audit_passed=False,
                          integrity_audit_receipt_ref=_canonical_digest(envelope["corrections"]))
    report = evaluate_pb_d(frozen_pairs, context, omissions=omissions)
    report["flow"]["stratified_coverage"] = _coverage_flow(first_rows, manifest["pairs"], checked_outcomes)
    report["omission_receipts"] = omission_receipts
    report["correction_review"] = {
        "correction_count": len(corrections), "corrections_sha256": _canonical_digest(envelope["corrections"]),
        "chain_head_sha256": envelope["corrections"][-1]["correction_sha256"] if corrections else None,
        "integrity_exception_observations": sorted(integrity_targets),
        "original_as_known_labels_and_pairs_preserved": True,
        "corrected_truth_analysis": "UNKNOWN_CORRECTED_LABELS_AND_POOL_NOT_SUPPLIED" if corrections else "NO_CORRECTIONS_SUPPLIED",
    }
    if integrity_targets:
        excluded_ids = {pair["pair_id"] for pair in manifest["pairs"]
                        if {pair["q1_observation_id"], pair["q0_observation_id"]} & integrity_targets}
        kept = [pair for pair in frozen_pairs if pair.pair_id not in excluded_ids]
        sensitivity = evaluate_pb_d(kept, context)
        report["integrity_exception_sensitivity"] = {
            "descriptive_only": True, "whole_pairs_excluded": sorted(excluded_ids),
            "rematching_performed": False, "primary_excluding_flagged_pairs": sensitivity["primary"],
            "original_primary_included_for_audit": True,
        }
    report["consumer_receipts"] = {
        "cohort_manifest_sha256": envelope["manifest_sha256"],
        "cohort_envelope_sha256": _canonical_digest(envelope),
        "outcomes_sha256": _canonical_digest(outcomes),
        "supplied_outcome_count": len(by_observation),
        "matched_pair_count": len(frozen_pairs),
        "outcome_provenance": "CALLER_SUPPLIED_OWNER_RECEIPTS_STRUCTURALLY_CHECKED",
        "calendar_provenance": "CALLER_SUPPLIED_SCHEDULE_NOT_INDEPENDENTLY_VERIFIED",
        "omission_sensitivity": "DETERMINISTIC_FULL_ORIGINAL_ELIGIBLE_POOL_REMATCH",
    }
    return report


def run_packet(packet: Mapping[str, Any]) -> dict:
    """Quality → immutable first-T2/pairs → separate outcomes, in that order."""
    packet = _object(packet, "packet")
    allowed = {"schema", "dataset_kind", "cohort", "quality_requests", "outcomes"}
    if set(packet) - allowed:
        raise ValueError(f"unknown research packet fields: {sorted(set(packet) - allowed)}")
    if packet.get("schema") != "pb_d_research_input.v1":
        raise ValueError("schema must be pb_d_research_input.v1")
    kind = packet.get("dataset_kind", "OFFLINE_OBSERVATION")
    if kind not in DATASET_KINDS:
        raise ValueError("this consumer cannot enroll a prospective cohort")
    receipts, envelope = _quality_and_cohort(packet)
    report = evaluate_manifest(envelope, packet.get("outcomes", []), dataset_kind=kind)
    return {
        "schema": "pb_d_research_run.v1",
        "state": "FROZEN_DESIGN_NOT_ENROLLED", "dataset_kind": kind,
        "research_source_sha": RESEARCH_HEAD, "input_sha256": _canonical_digest(packet),
        "quality_receipts": receipts, "cohort": envelope, "evaluation": report,
        "authority_flags": {"rank": False, "size": False, "entry": False,
                            "enroll": False, "promote": False},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("quality", "freeze", "evaluate", "run"))
    parser.add_argument("--input", required=True, type=Path, help="explicit JSON input file")
    parser.add_argument("--output", type=Path, help="optional report file; otherwise stdout")
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"),
                             parse_constant=lambda value: (_ for _ in ()).throw(
                                 ValueError(f"nonfinite JSON constant {value}")))
        payload = _object(payload, "input")
        if args.command == "quality":
            result = build_quality_receipt(**dict(payload))
        elif args.command == "freeze":
            result = freeze_cohort(payload)
        elif args.command == "evaluate":
            if set(payload) - {"cohort", "outcomes", "dataset_kind"}:
                raise ValueError("evaluate accepts cohort, outcomes, and dataset_kind only")
            result = evaluate_manifest(payload["cohort"], payload.get("outcomes", []),
                                       dataset_kind=payload.get("dataset_kind", "OFFLINE_OBSERVATION"))
        else:
            result = run_packet(payload)
        rendered = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False,
                              allow_nan=False) + "\n"
        if args.output:
            if args.output.resolve() == args.input.resolve():
                raise ValueError("output cannot replace the input receipt")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            # Research receipts are append-only artifacts. Exclusive creation
            # also refuses existing symlinks and concurrent writers.
            with args.output.open("x", encoding="utf-8") as output:
                output.write(rendered)
        else:
            sys.stdout.write(rendered)
        return 0
    except (ValueError, TypeError, KeyError, OSError) as exc:
        sys.stderr.write(json.dumps({"status": "REFUSED", "reason": str(exc)}) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

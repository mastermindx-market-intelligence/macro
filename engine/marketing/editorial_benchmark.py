"""Held-out editorial benchmark for Marketing Content Studio.

This module is an evaluation instrument, not an authority.  It freezes packet
identity and family-level train/holdout assignment before model outputs exist,
blinds output/runtime identity for human review, and aggregates review plus
runtime receipts without changing generation, approval, delivery, learning, or
provider configuration.

The benchmark deliberately does not generate prose. Candidate runs are supplied
as data after the packet manifest has been frozen. Human judgements are supplied
as separate packet/output review rows. Missing rows, errors, unknown source
state, and no-post decisions remain in denominators.

CLI:
    python -m engine.marketing.editorial_benchmark freeze packets.json --out manifest.json
    python -m engine.marketing.editorial_benchmark prepare manifest.json runs.json \
        --review-out review.json --key-out answer_key.json
    python -m engine.marketing.editorial_benchmark grade manifest.json runs.json \
        answer_key.json packet_labels.json ratings.json --out report.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Sequence


SCHEMA = "mastermind.marketing.editorial_benchmark.v1"
REVIEW_SCHEMA = "mastermind.marketing.editorial_review.v1"
REPORT_SCHEMA = "mastermind.marketing.editorial_report.v1"

# Explicitly non-authoritative.  A future promotion decision requires its own
# accepted owner and evidence; benchmark output alone changes nothing.
GATES_NOTHING: bool = True
# This module consumes already-produced rows and never invokes a model.
CALLS_MODELS: bool = False

_DECISIONS = {"post", "no_post", "error"}
_PACKET_SOURCE_STATES = {"complete", "partial", "unknown", "conflicting", "missing"}
_REQUIRED_PACKET_FIELDS = ("packet_id", "family", "kind", "account")
_RATING_SCORES = ("factual_correctness", "usefulness", "naturalness")


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _json_clone(value: Any) -> Any:
    return json.loads(_canonical(value))


def _family_rank(seed: str, family: str) -> str:
    return hashlib.sha256(f"{seed}|{family}".encode("utf-8")).hexdigest()


def _review_id(manifest_id: str, packet_id: str) -> str:
    return hashlib.sha256(
        f"{manifest_id}|{packet_id}".encode("utf-8")
    ).hexdigest()[:20]


def _mean(values: Iterable[float | int | None]) -> float | None:
    clean = [float(v) for v in values if v is not None]
    if not clean:
        return None
    return sum(clean) / len(clean)


def _rate(n: int, d: int) -> dict[str, Any]:
    if d <= 0:
        return {"n": int(n), "d": int(d), "rate": None, "wilson_95": None}
    p = n / d
    z = 1.96
    denom = 1.0 + z * z / d
    centre = (p + z * z / (2.0 * d)) / denom
    margin = z * math.sqrt((p * (1.0 - p) / d) + z * z / (4.0 * d * d)) / denom
    return {
        "n": int(n),
        "d": int(d),
        "rate": p,
        "wilson_95": [max(0.0, centre - margin), min(1.0, centre + margin)],
    }


def _normalise_packet(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("packet must be an object")
    row = _json_clone(raw)
    for field in _REQUIRED_PACKET_FIELDS:
        if not str(row.get(field) or "").strip():
            raise ValueError(f"packet missing {field}")
    state = str(row.get("source_state") or "unknown")
    if state not in _PACKET_SOURCE_STATES:
        raise ValueError(f"{row['packet_id']}: invalid source_state {state!r}")
    row["source_state"] = state
    row["packet_id"] = str(row["packet_id"])
    row["family"] = str(row["family"])
    row["kind"] = str(row["kind"])
    row["account"] = str(row["account"])
    row["ticker"] = None if row.get("ticker") in (None, "") else str(row.get("ticker"))
    row.setdefault("observation_clock", None)
    row.setdefault("source_clock", None)
    row.setdefault("facts", {})
    row.setdefault("image", {"present": False, "digest": None})
    if not isinstance(row["facts"], dict):
        raise ValueError(f"{row['packet_id']}: facts must be an object")
    if not isinstance(row["image"], dict):
        raise ValueError(f"{row['packet_id']}: image must be an object")
    row["image"].setdefault("present", False)
    row["image"].setdefault("digest", None)
    return row


def freeze_packets(
    packets: Sequence[dict[str, Any]],
    *,
    seed: str = "mx-x-b2-v1",
    holdout_fraction: float = 0.40,
) -> dict[str, Any]:
    """Freeze packet bytes and a family-safe split before outputs are observed."""
    if not 0.0 < float(holdout_fraction) <= 1.0:
        raise ValueError("holdout_fraction must be in (0, 1]")
    normalised = [_normalise_packet(row) for row in packets]
    by_id: dict[str, dict[str, Any]] = {}
    for row in normalised:
        packet_id = row["packet_id"]
        if packet_id in by_id:
            raise ValueError(f"duplicate packet_id {packet_id}")
        by_id[packet_id] = row
    ordered = [by_id[k] for k in sorted(by_id)]
    families = sorted({row["family"] for row in ordered})
    ranked_families = sorted(families, key=lambda f: (_family_rank(seed, f), f))

    if not families:
        holdout_families: set[str] = set()
        split_state = "empty"
    elif holdout_fraction >= 1.0 or len(families) == 1:
        holdout_families = set(families)
        split_state = "all_holdout" if holdout_fraction >= 1.0 else "single_family_all_holdout"
    else:
        n_holdout = int(round(len(families) * float(holdout_fraction)))
        n_holdout = max(1, min(len(families) - 1, n_holdout))
        holdout_families = set(ranked_families[:n_holdout])
        split_state = "train_holdout"

    packet_digest = _digest(ordered)
    manifest_id = _digest({
        "schema": SCHEMA,
        "seed": str(seed),
        "holdout_fraction": float(holdout_fraction),
        "packet_digest": packet_digest,
    })[:24]

    frozen_rows: list[dict[str, Any]] = []
    for row in ordered:
        frozen = _json_clone(row)
        frozen["split"] = "holdout" if row["family"] in holdout_families else "train"
        frozen["packet_sha256"] = _digest(row)
        frozen_rows.append(frozen)

    return {
        "schema": SCHEMA,
        "manifest_id": manifest_id,
        "seed": str(seed),
        "holdout_fraction": float(holdout_fraction),
        "packet_digest": packet_digest,
        "split_state": split_state,
        "families": len(families),
        "packets": frozen_rows,
    }


def _manifest_packets(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA:
        raise ValueError("invalid benchmark manifest schema")
    rows = manifest.get("packets") or []
    if not isinstance(rows, list):
        raise ValueError("manifest packets must be a list")
    by_id: dict[str, dict[str, Any]] = {}
    digest_rows: list[dict[str, Any]] = []
    for raw in rows:
        if not isinstance(raw, dict):
            raise ValueError("manifest packet must be an object")
        row = _json_clone(raw)
        split = row.pop("split", None)
        packet_sha = row.pop("packet_sha256", None)
        base = _normalise_packet(row)
        packet_id = base["packet_id"]
        if packet_id in by_id:
            raise ValueError(f"duplicate manifest packet_id {packet_id}")
        if split not in ("train", "holdout"):
            raise ValueError(f"{packet_id}: invalid split {split!r}")
        if packet_sha != _digest(base):
            raise ValueError(f"{packet_id}: packet bytes changed after freeze")
        frozen = _json_clone(base)
        frozen["split"] = split
        frozen["packet_sha256"] = packet_sha
        by_id[packet_id] = frozen
        digest_rows.append(base)
    if manifest.get("packet_digest") != _digest(sorted(digest_rows, key=lambda r: r["packet_id"])):
        raise ValueError("manifest packet digest mismatch")
    return by_id


def _normalise_run(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("run row must be an object")
    row = _json_clone(raw)
    packet_id = str(row.get("packet_id") or "")
    candidate_id = str(row.get("candidate_id") or "")
    decision = str(row.get("decision") or "")
    if not packet_id or not candidate_id:
        raise ValueError("run row requires packet_id and candidate_id")
    if decision not in _DECISIONS:
        raise ValueError(f"{packet_id}/{candidate_id}: invalid decision {decision!r}")
    text = str(row.get("text") or "")
    if decision == "post" and not text.strip():
        raise ValueError(f"{packet_id}/{candidate_id}: post decision requires text")
    if decision != "post" and text.strip():
        raise ValueError(f"{packet_id}/{candidate_id}: {decision} decision must not carry text")
    row["packet_id"] = packet_id
    row["candidate_id"] = candidate_id
    row["decision"] = decision
    row["text"] = text
    first_pass = row.get("first_pass_accepted")
    row["first_pass_accepted"] = None if first_pass is None else bool(first_pass)
    repair_count = row.get("repair_count")
    row["repair_count"] = (
        None if repair_count is None else max(0, int(repair_count))
    )
    for field in ("latency_ms", "cost_usd"):
        value = row.get(field)
        row[field] = None if value is None else float(value)
        if row[field] is not None and row[field] < 0:
            raise ValueError(f"{packet_id}/{candidate_id}: {field} must be >= 0")
    row["validator_reasons"] = [
        str(v) for v in (row.get("validator_reasons") or []) if str(v)
    ]
    for field in ("requested_model", "served_provider", "served_model", "failure_class"):
        row[field] = None if row.get(field) in (None, "") else str(row.get(field))
    return row


def _index_runs(
    manifest: dict[str, Any],
    runs: Sequence[dict[str, Any]],
) -> tuple[dict[tuple[str, str], dict[str, Any]], list[str]]:
    packets = _manifest_packets(manifest)
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    candidates: set[str] = set()
    for raw in runs:
        row = _normalise_run(raw)
        if row["packet_id"] not in packets:
            raise ValueError(f"run references unknown packet {row['packet_id']}")
        key = (row["candidate_id"], row["packet_id"])
        if key in indexed:
            raise ValueError(f"duplicate run row {key[0]}/{key[1]}")
        indexed[key] = row
        candidates.add(row["candidate_id"])
    return indexed, sorted(candidates)


def prepare_blinded_review(
    manifest: dict[str, Any],
    runs: Sequence[dict[str, Any]],
    *,
    seed: str = "mx-x-b2-review-v1",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build holdout-only human-review rows plus a separate identity key."""
    packets = _manifest_packets(manifest)
    indexed, candidate_ids = _index_runs(manifest, runs)
    manifest_id = str(manifest.get("manifest_id") or "")
    items: list[dict[str, Any]] = []
    assignments: list[dict[str, str]] = []

    holdout = [p for p in packets.values() if p["split"] == "holdout"]
    holdout.sort(key=lambda p: p["packet_id"])
    for packet in holdout:
        packet_id = packet["packet_id"]
        review_id = _review_id(manifest_id, packet_id)
        present = [
            indexed[(candidate_id, packet_id)]
            for candidate_id in candidate_ids
            if (candidate_id, packet_id) in indexed
        ]
        present.sort(
            key=lambda row: (
                _family_rank(seed, f"{packet_id}|{row['candidate_id']}"),
                row["candidate_id"],
            )
        )
        variants: list[dict[str, Any]] = []
        for i, run in enumerate(present):
            variant = chr(ord("A") + i) if i < 26 else f"V{i + 1}"
            variants.append({
                "variant": variant,
                "decision": run["decision"],
                "text": run["text"],
            })
            assignments.append({
                "review_id": review_id,
                "packet_id": packet_id,
                "variant": variant,
                "candidate_id": run["candidate_id"],
            })

        packet_view = {
            k: _json_clone(packet.get(k))
            for k in (
                "packet_id", "family", "kind", "account", "ticker", "source_state",
                "observation_clock", "source_clock", "facts", "image",
            )
        }
        items.append({
            "review_id": review_id,
            "packet": packet_view,
            "variants": variants,
        })

    review = {
        "schema": REVIEW_SCHEMA,
        "manifest_id": manifest_id,
        "items": items,
    }
    review["review_digest"] = _digest(review)
    key = {
        "schema": REVIEW_SCHEMA + ".answer_key",
        "manifest_id": manifest_id,
        "review_digest": review["review_digest"],
        "candidate_ids": candidate_ids,
        "assignments": assignments,
    }
    key["answer_key_digest"] = _digest(key)
    return review, key


def _rating_index(
    ratings: Sequence[dict[str, Any]],
) -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for raw in ratings:
        if not isinstance(raw, dict):
            raise ValueError("rating must be an object")
        review_id = str(raw.get("review_id") or "")
        variant = str(raw.get("variant") or "")
        if not review_id or not variant:
            raise ValueError("rating requires review_id and variant")
        key = (review_id, variant)
        if key in out:
            raise ValueError(f"duplicate output rating {review_id}/{variant}")
        row = _json_clone(raw)
        for field in _RATING_SCORES:
            value = row.get(field)
            if value is None:
                continue
            score = int(value)
            if not 1 <= score <= 5:
                raise ValueError(f"{review_id}/{variant}: {field} must be 1..5")
            row[field] = score
        image_score = row.get("image_text_consistency")
        if image_score is not None:
            image_score = int(image_score)
            if not 1 <= image_score <= 5:
                raise ValueError(
                    f"{review_id}/{variant}: image_text_consistency must be 1..5"
                )
            row["image_text_consistency"] = image_score
        row["repetitive_framing"] = bool(row.get("repetitive_framing", False))
        row["publishable_without_rewrite"] = bool(
            row.get("publishable_without_rewrite", False)
        )
        row["critical_fabrication"] = bool(row.get("critical_fabrication", False))
        out[key] = row
    return out


def _packet_label_index(
    packet_labels: Sequence[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for raw in packet_labels:
        if not isinstance(raw, dict):
            raise ValueError("packet label must be an object")
        review_id = str(raw.get("review_id") or "")
        if not review_id:
            raise ValueError("packet label requires review_id")
        if review_id in out:
            raise ValueError(f"duplicate packet label {review_id}")
        if "should_post" not in raw:
            raise ValueError(f"{review_id}: packet label requires should_post")
        row = _json_clone(raw)
        row["should_post"] = bool(raw["should_post"])
        row["source_sufficient"] = bool(raw.get("source_sufficient", False))
        out[review_id] = row
    return out


def _answer_map(answer_key: dict[str, Any]) -> dict[tuple[str, str], str]:
    assignments = answer_key.get("assignments") or []
    out: dict[tuple[str, str], str] = {}
    for row in assignments:
        key = (str(row.get("review_id") or ""), str(row.get("variant") or ""))
        candidate_id = str(row.get("candidate_id") or "")
        if not all((*key, candidate_id)):
            raise ValueError("invalid answer-key assignment")
        if key in out:
            raise ValueError(f"duplicate answer-key assignment {key}")
        out[key] = candidate_id
    return out


def _identity_counts(rows: Sequence[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        identity = "|".join(
            str(row.get(field) or "UNKNOWN")
            for field in ("requested_model", "served_provider", "served_model")
        )
        counts[identity] += 1
    return dict(sorted(counts.items()))


def grade(
    manifest: dict[str, Any],
    runs: Sequence[dict[str, Any]],
    answer_key: dict[str, Any],
    packet_labels: Sequence[dict[str, Any]],
    ratings: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate observed results. No candidate is selected or promoted."""
    packets = _manifest_packets(manifest)
    indexed, observed_candidates = _index_runs(manifest, runs)
    candidate_ids = sorted(set(answer_key.get("candidate_ids") or observed_candidates))
    answer = _answer_map(answer_key)
    p_labels = _packet_label_index(packet_labels)
    rating_idx = _rating_index(ratings)
    manifest_id = str(manifest.get("manifest_id") or "")

    holdout = {
        packet_id: row
        for packet_id, row in packets.items()
        if row["split"] == "holdout"
    }
    review_by_packet = {
        packet_id: _review_id(manifest_id, packet_id)
        for packet_id in holdout
    }

    valid_review_ids = set(review_by_packet.values())
    missing_packet_labels = sum(
        1 for review_id in valid_review_ids if review_id not in p_labels
    )
    expected_ratings: set[tuple[str, str]] = set()
    assignment_by_candidate_packet: dict[tuple[str, str], str] = {}
    for (review_id, variant), candidate_id in answer.items():
        packet_id = next(
            (pid for pid, rid in review_by_packet.items() if rid == review_id),
            None,
        )
        if packet_id is None:
            continue
        assignment_by_candidate_packet[(candidate_id, packet_id)] = variant
        run = indexed.get((candidate_id, packet_id))
        if run and run["decision"] == "post":
            expected_ratings.add((review_id, variant))

    missing_output_ratings = sum(1 for key in expected_ratings if key not in rating_idx)
    candidate_reports: dict[str, Any] = {}
    total_missing_runs = 0

    from engine.marketing.copy_review import detect_repetition  # local, deterministic

    for candidate_id in candidate_ids:
        candidate_runs = [
            indexed[(candidate_id, pid)]
            for pid in holdout
            if (candidate_id, pid) in indexed
        ]
        posted = [row for row in candidate_runs if row["decision"] == "post"]
        missing_runs = len(holdout) - len(candidate_runs)
        total_missing_runs += missing_runs

        selection = {
            "correct_post": 0,
            "correct_abstain": 0,
            "forced_post": 0,
            "missed_opportunity": 0,
            "missing_or_error": 0,
            "unknown_label": 0,
        }
        candidate_ratings: list[dict[str, Any]] = []
        image_ratings: list[dict[str, Any]] = []
        accepted_count = 0

        for packet_id, packet in holdout.items():
            review_id = review_by_packet[packet_id]
            label = p_labels.get(review_id)
            run = indexed.get((candidate_id, packet_id))
            if run is None or run["decision"] == "error":
                selection["missing_or_error"] += 1
                continue
            if label is None:
                selection["unknown_label"] += 1
            else:
                should_post = bool(label["should_post"])
                if run["decision"] == "post" and should_post:
                    selection["correct_post"] += 1
                elif run["decision"] == "post" and not should_post:
                    selection["forced_post"] += 1
                elif run["decision"] == "no_post" and should_post:
                    selection["missed_opportunity"] += 1
                elif run["decision"] == "no_post" and not should_post:
                    selection["correct_abstain"] += 1

            if run["decision"] != "post":
                continue
            variant = assignment_by_candidate_packet.get((candidate_id, packet_id))
            rating = rating_idx.get((review_id, variant or ""))
            if rating is None:
                continue
            candidate_ratings.append(rating)
            if bool(packet.get("image", {}).get("present")):
                image_ratings.append(rating)
            if rating["publishable_without_rewrite"]:
                accepted_count += 1

        repetition_posts = [
            {"id": row["packet_id"], "headline": "", "body": row["text"]}
            for row in posted
        ]
        repetition_findings = detect_repetition(repetition_posts)
        repeated_ids = sorted({
            str(pid)
            for finding in repetition_findings
            for pid in (finding.get("ids") or [])
        })

        critical_fabrications = sum(
            bool(row["critical_fabrication"]) for row in candidate_ratings
        )
        publishable = sum(
            bool(row["publishable_without_rewrite"]) for row in candidate_ratings
        )
        human_repetitive = sum(
            bool(row["repetitive_framing"]) for row in candidate_ratings
        )
        validator_failures = sum(bool(row["validator_reasons"]) for row in posted)
        first_pass_rows = [
            row for row in posted if row.get("first_pass_accepted") is not None
        ]
        first_pass = sum(bool(row["first_pass_accepted"]) for row in first_pass_rows)
        repair_values = [
            int(row["repair_count"])
            for row in candidate_runs if row.get("repair_count") is not None
        ]
        repair_total = sum(repair_values) if repair_values else None
        latency_values = [
            float(row["latency_ms"])
            for row in candidate_runs if row.get("latency_ms") is not None
        ]
        latency_total = sum(latency_values) if latency_values else None
        cost_values = [
            float(row["cost_usd"])
            for row in candidate_runs if row.get("cost_usd") is not None
        ]
        cost_total = sum(cost_values) if cost_values else None

        content = {
            "rated_outputs": len(candidate_ratings),
            "factual_correctness_mean": _mean(
                row.get("factual_correctness") for row in candidate_ratings
            ),
            "usefulness_mean": _mean(row.get("usefulness") for row in candidate_ratings),
            "naturalness_mean": _mean(row.get("naturalness") for row in candidate_ratings),
            "human_repetitive_framing": _rate(
                human_repetitive, len(candidate_ratings)
            ),
            "mechanical_repetition_findings": len(repetition_findings),
            "mechanical_repeated_packet_ids": repeated_ids,
            "image_text_consistency_mean": _mean(
                row.get("image_text_consistency") for row in image_ratings
            ),
            "publishable_without_rewrite": _rate(
                publishable, len(candidate_ratings)
            ),
            "critical_fabrications": critical_fabrications,
            "critical_fabrication_rate": _rate(
                critical_fabrications, len(candidate_ratings)
            ),
            "validator_failure_outputs": validator_failures,
        }
        runtime = {
            "first_pass_acceptance": _rate(first_pass, len(first_pass_rows)),
            "first_pass_coverage": len(first_pass_rows),
            "repair_count_total": repair_total,
            "repair_coverage": len(repair_values),
            "repairs_per_observed_run": (
                repair_total / len(repair_values) if repair_values else None
            ),
            "repairs_per_accepted": (
                repair_total / accepted_count
                if accepted_count and len(repair_values) == len(candidate_runs)
                else None
            ),
            "latency_ms_total": latency_total,
            "latency_coverage": len(latency_values),
            "latency_ms_per_output": (
                latency_total / len(latency_values) if latency_values else None
            ),
            "latency_ms_per_accepted": (
                latency_total / accepted_count
                if accepted_count and len(latency_values) == len(candidate_runs)
                else None
            ),
            "cost_usd_total": cost_total,
            "cost_coverage": len(cost_values),
            "cost_usd_per_accepted": (
                cost_total / accepted_count
                if accepted_count and len(cost_values) == len(candidate_runs)
                else None
            ),
            "requested_served_identity_counts": _identity_counts(candidate_runs),
        }
        candidate_reports[candidate_id] = {
            "denominators": {
                "holdout_packets": len(holdout),
                "observed_run_rows": len(candidate_runs),
                "posted_outputs": len(posted),
                "rated_outputs": len(candidate_ratings),
                "accepted_outputs": accepted_count,
                "image_present_packets": sum(
                    bool(p.get("image", {}).get("present")) for p in holdout.values()
                ),
                "unknown_or_noncomplete_source_packets": sum(
                    p.get("source_state") != "complete" for p in holdout.values()
                ),
            },
            "selection": selection,
            "content": content,
            "runtime": runtime,
        }

    state = "complete"
    if missing_packet_labels or missing_output_ratings or total_missing_runs:
        state = "partial"
    return {
        "schema": REPORT_SCHEMA,
        "manifest_id": manifest_id,
        "state": state,
        "gates_nothing": GATES_NOTHING,
        "missing": {
            "packet_labels": missing_packet_labels,
            "output_ratings": missing_output_ratings,
            "run_rows": total_missing_runs,
        },
        "candidates": candidate_reports,
    }


def _read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: str | Path, value: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p_freeze = sub.add_parser("freeze")
    p_freeze.add_argument("packets")
    p_freeze.add_argument("--out", required=True)
    p_freeze.add_argument("--seed", default="mx-x-b2-v1")
    p_freeze.add_argument("--holdout-fraction", type=float, default=0.40)

    p_prepare = sub.add_parser("prepare")
    p_prepare.add_argument("manifest")
    p_prepare.add_argument("runs")
    p_prepare.add_argument("--review-out", required=True)
    p_prepare.add_argument("--key-out", required=True)
    p_prepare.add_argument("--seed", default="mx-x-b2-review-v1")

    p_grade = sub.add_parser("grade")
    p_grade.add_argument("manifest")
    p_grade.add_argument("runs")
    p_grade.add_argument("answer_key")
    p_grade.add_argument("packet_labels")
    p_grade.add_argument("ratings")
    p_grade.add_argument("--out", required=True)

    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command == "freeze":
        packets = _read_json(args.packets)
        manifest = freeze_packets(
            packets,
            seed=args.seed,
            holdout_fraction=args.holdout_fraction,
        )
        _write_json(args.out, manifest)
        return 0
    if args.command == "prepare":
        manifest = _read_json(args.manifest)
        runs = _read_json(args.runs)
        review, key = prepare_blinded_review(manifest, runs, seed=args.seed)
        _write_json(args.review_out, review)
        _write_json(args.key_out, key)
        return 0
    if args.command == "grade":
        report = grade(
            _read_json(args.manifest),
            _read_json(args.runs),
            _read_json(args.answer_key),
            _read_json(args.packet_labels),
            _read_json(args.ratings),
        )
        _write_json(args.out, report)
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())

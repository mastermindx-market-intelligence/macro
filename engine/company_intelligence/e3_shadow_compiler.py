"""E3-A shadow compiler — AAPL FY2026 Q3 leakage-free eval only.

Not R2-writeable. Not event_workspace.v1-generating.
Gold labels are loaded ONLY after model inference completes.

Frozen source package:
  Exhibit 99.1: 070abd6a9cdb7070e546d24ffcbc41c65450d939c6f88f189cb18ec711cf5fdb
  Transcript:   a8ff5d03e875fef5604791edbf625186c447af049e6e02f55bb89c68c7cc9f9f
  Event:        evt_cik0000320193_2026q3_results
  Generation:   f709a0a6ec514282d5769e7d
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import plistlib
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# Frozen source SHAs — divergence check is load-bearing.
FROZEN_EXHIBIT_SHA = "070abd6a9cdb7070e546d24ffcbc41c65450d939c6f88f189cb18ec711cf5fdb"
FROZEN_TRANSCRIPT_SHA = "a8ff5d03e875fef5604791edbf625186c447af049e6e02f55bb89c68c7cc9f9f"
PINNED_GENERATION_ID = "f709a0a6ec514282d5769e7d"
PINNED_WORKSPACE_SHA = "dbd50e5c30e8a031f844e02362ffd53b25e3230e75eeef19bf3825543cb81197"

EVENT_ID = "evt_cik0000320193_2026q3_results"
TX_DOC_ID = "tx:AAPL/2026Q3"
RELEASE_DOC_ID = "release:0000320193-26-000018"

GOLD_PATH = Path(
    "research/earnings_intelligence/e3/gold/aapl_fy2026_q3_qa_gold.json"
)
EVAL_RECEIPT_PATH = Path(
    "research/earnings_intelligence/e3/gold/aapl_fy2026_q3_eval_receipt.json"
)
ADJUDICATION_RECEIPT_PATH = Path(
    "research/earnings_intelligence/e3/gold/aapl_fy2026_q3_adjudication_receipt.json"
)

LANE = "earnings_event_compiler"
SUPERSEDED_GOLD_SHA_V1 = "6b1100b148396db9a29974da5bc6e0cc55e5534185e50e061fe3635d429ed761"
FROZEN_GOLD_SHA = "fc6df84d2a8d0d96475ce697ba92ffdd071d5c283b8daee97c1b3381382fa42c"
TAXONOMY_VERSION = "qa_topic.v1"
TAXONOMY_HASH = "a928ca72ab2e91bda74bd1e69021e08a5234e501f095610e623655db7e323b5e"
CLOSED_TAXONOMY = frozenset({
    "demand", "product", "pricing", "costs_supply",
    "capacity", "capital_allocation", "regulation",
    "other", "unavailable",
})

# Closed candidate schema. Unknown keys fail. The validator binds identity.
CANDIDATE_KEYS = (
    "ordinal",
    "boundary_segment_index",
    "questioner_name",
    "affiliation",
    "question_segment_indexes",
    "answer_segment_indexes",
    "respondents",
    "topics",
)
CANDIDATE_KEY_SET = frozenset(CANDIDATE_KEYS)
FOREIGN_IDENTITY_KEYS = frozenset({"event_id", "document_id", "document_sha256"})

WORKER_PLIST_REL = Path("ops/launchd/com.mastermind.earnings-worker.plist")
FROZEN_COMPARATOR_MODEL = "claude-haiku-4-5"
EXTRACTION_MAX_TOKENS = 4096

# ── Extraction prompt ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are an earnings call Q&A extraction assistant. "
    "The segments include prepared remarks and then an analyst Q&A session. "
    "An Operator segment that contains 'go ahead' opens a new exchange. "
    "Extract EVERY such exchange. Return [] only if there is no Operator Q&A. "
    "Return a JSON array only. Each object may contain EXACTLY these keys "
    "and no others:\n"
    "  ordinal (int, 0-based)\n"
    "  boundary_segment_index (int) — the Operator intro segment that opens "
    "the exchange (the segment whose role is Operator and that contains "
    "'go ahead')\n"
    "  questioner_name (str)\n"
    "  affiliation (str)\n"
    "  question_segment_indexes (ordered list[int])\n"
    "  answer_segment_indexes (ordered list[int])\n"
    "  respondents (ordered list of {name: str, role: str})\n"
    "  topics (list[str], 1–3 members of: demand, product, pricing, "
    "costs_supply, capacity, capital_allocation, regulation, other, "
    "unavailable)\n\n"
    "Do not include event_id, document_id, document_sha256, or any other key. "
    "Do not invent information not present in the source segments. "
    "Do not include explanation outside the JSON array."
)


def _build_user_prompt(segments: list[dict]) -> str:
    """Build the extraction prompt from transcript segments.

    Uses all segments — no head/tail truncation per freeze §4.
    Gold labels are NOT included.
    """
    lines = ["Earnings call transcript segments:\n"]
    for i, seg in enumerate(segments):
        role = seg.get("role", "")
        speaker = seg.get("speaker", "")
        text = seg.get("text", "")
        lines.append(f"[segment {i}] role={role!r} speaker={speaker!r}")
        lines.append(text)
        lines.append("")
    lines.append(
        "\nReturn a JSON array of objects using only the closed candidate keys."
    )
    return "\n".join(lines)


# ── Source loading + SHA verification ────────────────────────────────────────


def verify_fixture_shas(root: Path) -> dict[str, str]:
    """Verify fixture SHAs match frozen spec. Raises on divergence."""
    exhibit_path = root / "tests/fixtures/company_intelligence/aapl_fy2026_q3_ex99_1.htm"
    tx_path = root / "tests/fixtures/company_intelligence/aapl_fy2026_q3.json.gz"

    exhibit_sha = hashlib.sha256(exhibit_path.read_bytes()).hexdigest()
    with gzip.open(tx_path) as f:
        tx_sha = hashlib.sha256(f.read()).hexdigest()

    if exhibit_sha != FROZEN_EXHIBIT_SHA:
        raise RuntimeError(
            f"Exhibit 99.1 SHA divergence: fixture={exhibit_sha} "
            f"frozen={FROZEN_EXHIBIT_SHA} — STOP per E3-A §1"
        )
    if tx_sha != FROZEN_TRANSCRIPT_SHA:
        raise RuntimeError(
            f"Transcript SHA divergence: fixture={tx_sha} "
            f"frozen={FROZEN_TRANSCRIPT_SHA} — STOP per E3-A §1"
        )
    return {
        "exhibit_sha": exhibit_sha,
        "transcript_sha": tx_sha,
        "check": "pass",
    }


def load_transcript_segments(root: Path) -> list[dict]:
    """Load transcript segments from the frozen fixture."""
    tx_path = root / "tests/fixtures/company_intelligence/aapl_fy2026_q3.json.gz"
    with gzip.open(tx_path) as f:
        tx = json.load(f)
    return tx["segments"]


def classify_live_workspace_shas(
    *,
    available: bool,
    generation_id: str,
    workspace_sha: str,
    release_sha: str,
    transcript_sha: str,
    note: str | None = None,
) -> dict[str, Any]:
    """Separate source-SHA calibration from current-marker identity.

    A later current-marker generation must not rewrite historical gold.
    Eval proceeds when source SHAs still match the frozen fixtures.
    """
    source_shas_match = (
        release_sha == FROZEN_EXHIBIT_SHA
        and transcript_sha == FROZEN_TRANSCRIPT_SHA
    )
    current_marker_is_calibration_generation = (
        generation_id == PINNED_GENERATION_ID
        and workspace_sha == PINNED_WORKSPACE_SHA
    )
    if not available:
        status_note = note or "live workspace unavailable"
    elif not source_shas_match:
        status_note = note or "live workspace source SHA mismatch"
    elif not current_marker_is_calibration_generation:
        status_note = (
            "current-marker generation moved; AAPL calibration remains bound "
            f"to source SHAs and pinned generation {PINNED_GENERATION_ID}; "
            "gold not rewritten"
        )
    else:
        status_note = None
    return {
        "available": bool(available),
        "generation_id": generation_id,
        "workspace_sha256": workspace_sha,
        "release_source_sha256": release_sha,
        "transcript_source_sha256": transcript_sha,
        "source_shas_match": source_shas_match,
        "current_marker_is_calibration_generation": (
            current_marker_is_calibration_generation
        ),
        "calibration_generation_id": PINNED_GENERATION_ID,
        "calibration_workspace_sha256": PINNED_WORKSPACE_SHA,
        "matches_frozen_fixtures": source_shas_match,
        "assumed_from_handoff": False,
        "note": status_note,
    }


def verify_live_workspace_shas() -> dict[str, Any]:
    """Read the live E2 workspace through the verified public reader.

    Calibration is bound to the frozen source SHAs, not to whatever
    generation the current marker now names. Does not assume from the handoff.
    """
    from engine.neuralweb import company_intelligence_reader as reader

    result = reader.read_event_workspace({"event_id": EVENT_ID})
    receipt = dict(result.get("receipt") or {})
    workspace = dict(result.get("workspace") or {})
    sources = {
        str(s.get("kind")): s
        for s in (workspace.get("sources") or [])
        if isinstance(s, dict)
    }
    classified = classify_live_workspace_shas(
        available=bool(result.get("available")),
        generation_id=str(
            workspace.get("generation_id") or receipt.get("generation_id") or ""
        ),
        workspace_sha=str(receipt.get("workspace_sha256") or ""),
        release_sha=str((sources.get("issuer_release") or {}).get("source_sha256") or ""),
        transcript_sha=str((sources.get("transcript") or {}).get("source_sha256") or ""),
        note=str(result.get("note") or "") or None,
    )
    classified["reader"] = (
        "engine.neuralweb.company_intelligence_reader.read_event_workspace"
    )
    classified["workspace_url"] = receipt.get("workspace_url")
    classified["marker_url"] = receipt.get("marker_url")
    return classified


# ── Stable segment_id ─────────────────────────────────────────────────────────


def stable_segment_id(document_sha256: str, segment_index: int) -> str:
    """Deterministic segment_id = (document_sha256, segment_index)."""
    return f"seg_{document_sha256[:16]}_{segment_index:04d}"


def gold_boundary_segment(exchange: dict) -> int:
    """Operator-intro segment that opens a gold exchange."""
    spans = exchange.get("question_spans") or []
    if not spans:
        raise ValueError("gold exchange missing question_spans")
    return int(spans[0]["segment_index"])


def gold_exchange_to_candidate(exchange: dict) -> dict:
    """Project a gold exchange onto the closed candidate schema."""
    return {
        "ordinal": int(exchange["ordinal"]),
        "boundary_segment_index": gold_boundary_segment(exchange),
        "questioner_name": str(exchange["questioner"]["name"]),
        "affiliation": str(exchange["questioner"]["affiliation"]),
        "question_segment_indexes": [
            int(s["segment_index"]) for s in exchange["question_spans"]
        ],
        "answer_segment_indexes": [
            int(s["segment_index"]) for s in exchange["answer_spans"]
        ],
        "respondents": [
            {"name": str(r["name"]), "role": str(r["role"])}
            for r in exchange["respondents"]
        ],
        "topics": list(exchange.get("topics") or []),
    }


# ── Shadow validator ──────────────────────────────────────────────────────────


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _replay_indexes(indexes: list[int], segments: list[dict]) -> tuple[bool, list[dict]]:
    reconstructed: list[dict] = []
    for idx in indexes:
        if idx < 0 or idx >= len(segments):
            return False, reconstructed
        text = str(segments[idx].get("text") or "")
        raw = text.encode("utf-8")
        if not raw:
            return False, reconstructed
        reconstructed.append({
            "segment_index": idx,
            "start_byte": 0,
            "end_byte": len(raw),
            "text_sha256": hashlib.sha256(raw).hexdigest(),
            "speaker": segments[idx].get("speaker"),
            "role": segments[idx].get("role"),
        })
    return True, reconstructed


def validate_candidate(
    candidate: Any,
    segments: list[dict],
    *,
    n_segments: int | None = None,
) -> dict[str, Any]:
    """Deterministically validate one model candidate against the closed schema.

    The validator — not the model — binds event_id / document identity.
    """
    n_segments = n_segments if n_segments is not None else len(segments)
    if not isinstance(candidate, dict):
        return {"ok": False, "reason": "invalid_schema", "detail": "not_an_object"}

    extras = set(candidate) - CANDIDATE_KEY_SET
    foreign = extras & FOREIGN_IDENTITY_KEYS
    if foreign:
        for key in ("event_id", "document_id", "document_sha256"):
            if key not in candidate:
                continue
            value = candidate[key]
            expected = {
                "event_id": EVENT_ID,
                "document_id": TX_DOC_ID,
                "document_sha256": FROZEN_TRANSCRIPT_SHA,
            }[key]
            if value != expected:
                return {
                    "ok": False,
                    "reason": "cross_event",
                    "detail": f"foreign_{key}",
                }
        # Even a matching identity field is an unknown key on the closed schema.
        return {"ok": False, "reason": "invalid_schema", "detail": "unknown_key_identity_field"}
    if extras:
        return {"ok": False, "reason": "invalid_schema", "detail": "unknown_key"}

    missing = [k for k in CANDIDATE_KEYS if k not in candidate]
    if missing:
        return {"ok": False, "reason": "invalid_schema", "detail": f"missing:{missing[0]}"}

    if not _is_int(candidate["ordinal"]):
        return {"ok": False, "reason": "invalid_schema", "detail": "ordinal_type"}
    if not _is_int(candidate["boundary_segment_index"]):
        return {"ok": False, "reason": "invalid_schema", "detail": "boundary_segment_index_type"}
    if not isinstance(candidate["questioner_name"], str):
        return {"ok": False, "reason": "invalid_schema", "detail": "questioner_name_type"}
    if not isinstance(candidate["affiliation"], str):
        return {"ok": False, "reason": "invalid_schema", "detail": "affiliation_type"}
    q_idx = candidate["question_segment_indexes"]
    a_idx = candidate["answer_segment_indexes"]
    if not isinstance(q_idx, list) or not all(_is_int(i) for i in q_idx):
        return {"ok": False, "reason": "invalid_schema", "detail": "question_segment_indexes_type"}
    if not isinstance(a_idx, list) or not all(_is_int(i) for i in a_idx):
        return {"ok": False, "reason": "invalid_schema", "detail": "answer_segment_indexes_type"}
    if not q_idx or not a_idx:
        return {"ok": False, "reason": "invalid_schema", "detail": "empty_span_indexes"}
    respondents = candidate["respondents"]
    if not isinstance(respondents, list) or not respondents:
        return {"ok": False, "reason": "invalid_schema", "detail": "respondents_type"}
    for resp in respondents:
        if not isinstance(resp, dict):
            return {"ok": False, "reason": "invalid_schema", "detail": "respondent_type"}
        if set(resp.keys()) != {"name", "role"}:
            return {"ok": False, "reason": "invalid_schema", "detail": "respondent_keys"}
        if not isinstance(resp["name"], str) or not isinstance(resp["role"], str):
            return {"ok": False, "reason": "invalid_schema", "detail": "respondent_field_type"}
    topics = candidate["topics"]
    if not isinstance(topics, list) or not (1 <= len(topics) <= 3):
        return {"ok": False, "reason": "invalid_schema", "detail": "topics_arity"}
    if not all(isinstance(t, str) for t in topics):
        return {"ok": False, "reason": "invalid_schema", "detail": "topics_type"}
    if any(t not in CLOSED_TAXONOMY for t in topics):
        return {"ok": False, "reason": "unknown_topic", "detail": "topic_not_in_qa_topic.v1"}

    all_idx = [candidate["boundary_segment_index"], *q_idx, *a_idx]
    for idx in all_idx:
        if idx < 0 or idx >= n_segments:
            return {"ok": False, "reason": "out_of_range_segment", "detail": str(idx)}

    q_ok, q_spans = _replay_indexes(q_idx, segments)
    a_ok, a_spans = _replay_indexes(a_idx, segments)
    b_ok, b_spans = _replay_indexes([candidate["boundary_segment_index"]], segments)
    if not q_ok or not a_ok or not b_ok:
        return {"ok": False, "reason": "span_replay_failure", "detail": "index_replay"}

    bound = {
        "event_id": EVENT_ID,
        "document_id": TX_DOC_ID,
        "document_sha256": FROZEN_TRANSCRIPT_SHA,
        "question_spans": q_spans,
        "answer_spans": a_spans,
    }
    return {"ok": True, "reason": None, "bound": bound, "candidate": candidate}


def validate_candidates(candidates: list[Any], segments: list[dict]) -> dict[str, Any]:
    """Validate a candidate list. 'accepted' here is shadow-admissible only."""
    valid: list[dict] = []
    rejected: list[dict] = []
    reason_counts = {
        "invalid_schema_rejected": 0,
        "unknown_topic_rejected": 0,
        "out_of_range_rejected": 0,
        "cross_event_rejected": 0,
        "span_replay_rejected": 0,
    }
    reason_map = {
        "invalid_schema": "invalid_schema_rejected",
        "unknown_topic": "unknown_topic_rejected",
        "out_of_range_segment": "out_of_range_rejected",
        "cross_event": "cross_event_rejected",
        "span_replay_failure": "span_replay_rejected",
    }
    for raw in candidates:
        result = validate_candidate(raw, segments)
        if result["ok"]:
            valid.append(result)
        else:
            rejected.append({"candidate": raw, "rejection_reason": result["reason"], "detail": result.get("detail")})
            bucket = reason_map.get(result["reason"], "invalid_schema_rejected")
            reason_counts[bucket] += 1

    accepted_span_replay_count = sum(1 for v in valid if v.get("bound"))
    return {
        "valid_candidates": [v["candidate"] for v in valid],
        "rejected_candidates": rejected,
        "accepted_count": len(valid),
        "unsupported_rejected": reason_counts["span_replay_rejected"],
        "invalid_schema_rejected": reason_counts["invalid_schema_rejected"],
        "unknown_topic_rejected": reason_counts["unknown_topic_rejected"],
        "out_of_range_rejected": reason_counts["out_of_range_rejected"],
        "cross_event_rejected": reason_counts["cross_event_rejected"],
        "span_replay_rejected": reason_counts["span_replay_rejected"],
        "accepted_unsupported": 0,
        "accepted_cross_event": 0,
        "invalid_schema_accepted": 0,
        "accepted_span_replay_count": accepted_span_replay_count,
        "valid_with_bound": valid,
    }


# ── Scoring against gold ───────────────────────────────────────────────────────


def _norm(value: Any) -> str:
    return str(value or "").strip()


def score_attempt(
    attempt: ModelAttempt | Any,
    gold: dict,
    segments: list[dict],
) -> dict[str, Any]:
    """Score model candidates against frozen gold using the shadow validator.

    Exchange-boundary TP is an exact one-to-one Operator-boundary match.
    Questioner-name equality alone is not a boundary match.
    Duplicate predictions cannot create duplicate TPs or recall > 1.
    """
    gold_exchanges = gold.get("exchanges") or []
    n_gold = len(gold_exchanges)
    raw_candidates = list(getattr(attempt, "candidates", None) or [])
    n_candidates = len(raw_candidates)

    if n_candidates == 0:
        return {
            "n_gold_exchanges": n_gold,
            "n_model_candidates": 0,
            "exchange_boundary_quality": {
                "tp": 0,
                "precision": None,
                "recall": None,
                "f1": None,
                "note": "model_produced_no_candidates",
            },
            "source_span_replay_success_pct": None,
            "unsupported_candidate_rate": None,
            "cross_event_contamination_accepted": 0,
            "topic_label_agreement_mean_jaccard": None,
            "identity_role_availability": None,
            "invalid_schema_rate": None,
            "accepted_count": 0,
            "unsupported_rejected": 0,
            "invalid_schema_rejected": 0,
            "cross_event_rejected": 0,
            "accepted_unsupported": 0,
            "accepted_cross_event": 0,
            "invalid_schema_accepted": 0,
            "accepted_span_replay_count": 0,
            "valid_candidates": [],
            "rejected_candidates": [],
            "rejection_reason": None,
            "hard_gates": {
                "status": "NOT_EXERCISED",
                "accepted_unsupported": 0,
                "accepted_cross_event": 0,
                "cross_event": 0,
                "span_replay_of_accepted": "NOT_EXERCISED",
                "invalid_schema_accepted": 0,
                "all_pass": False,
            },
            "per_exchange": [],
            "status": "no_candidates",
        }

    validated = validate_candidates(raw_candidates, segments)
    valid = validated["valid_candidates"]
    gold_by_boundary = {
        gold_boundary_segment(ex): ex for ex in gold_exchanges
    }
    used_boundaries: set[int] = set()
    pairs: list[tuple[dict, dict]] = []
    for cand in valid:
        boundary = int(cand["boundary_segment_index"])
        if boundary in used_boundaries:
            continue
        gold_ex = gold_by_boundary.get(boundary)
        if gold_ex is None:
            continue
        used_boundaries.add(boundary)
        pairs.append((gold_ex, cand))

    tp = len(pairs)
    fp = n_candidates - tp
    fn = n_gold - tp
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / n_gold if n_gold else 0.0
    if recall > 1.0:
        raise RuntimeError("recall > 1: duplicate TP matching leaked")
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    jaccards: list[float] = []
    identity_rows: list[dict] = []
    per_exchange: list[dict] = []
    for gold_ex, cand in pairs:
        g_topics = set(gold_ex.get("topics") or [])
        m_topics = set(cand.get("topics") or [])
        jaccard = (len(g_topics & m_topics) / len(g_topics | m_topics)) if (g_topics or m_topics) else 1.0
        jaccards.append(jaccard)
        gq = gold_ex.get("questioner") or {}
        g_resps = list(gold_ex.get("respondents") or [])
        m_resps = list(cand.get("respondents") or [])
        name_ok = _norm(cand.get("questioner_name")) == _norm(gq.get("name"))
        aff_ok = _norm(cand.get("affiliation")) == _norm(gq.get("affiliation"))
        g_names = [_norm(r.get("name")) for r in g_resps]
        m_names = [_norm(r.get("name")) for r in m_resps]
        g_roles = [_norm(r.get("role")) for r in g_resps]
        m_roles = [_norm(r.get("role")) for r in m_resps]
        names_ok = g_names == m_names
        roles_ok = g_roles == m_roles
        identity_rows.append({
            "questioner_name": name_ok,
            "affiliation": aff_ok,
            "respondent_names_ordered": names_ok,
            "respondent_roles_ordered": roles_ok,
        })
        errors = []
        if not name_ok:
            errors.append("questioner_name")
        if not aff_ok:
            errors.append("affiliation")
        if not names_ok:
            errors.append("respondent_names")
        if not roles_ok:
            errors.append("respondent_roles")
        per_exchange.append({
            "gold_ordinal": gold_ex["ordinal"],
            "gold_boundary_segment_index": gold_boundary_segment(gold_ex),
            "candidate_ordinal": cand.get("ordinal"),
            "topic_jaccard": jaccard,
            "identity_errors": errors,
        })

    matched_gold = {gold_boundary_segment(g) for g, _ in pairs}
    for gold_ex in gold_exchanges:
        if gold_boundary_segment(gold_ex) in matched_gold:
            continue
        per_exchange.append({
            "gold_ordinal": gold_ex["ordinal"],
            "gold_boundary_segment_index": gold_boundary_segment(gold_ex),
            "candidate_ordinal": None,
            "topic_jaccard": None,
            "identity_errors": ["unmatched"],
        })

    n_id = len(identity_rows)
    identity = None
    if n_id:
        identity = {
            "matched_exchanges": n_id,
            "questioner_name_match_rate": sum(r["questioner_name"] for r in identity_rows) / n_id,
            "affiliation_match_rate": sum(r["affiliation"] for r in identity_rows) / n_id,
            "respondent_name_order_match_rate": sum(r["respondent_names_ordered"] for r in identity_rows) / n_id,
            "respondent_role_order_match_rate": sum(r["respondent_roles_ordered"] for r in identity_rows) / n_id,
        }

    accepted = validated["accepted_count"]
    replay_pct = (
        (100.0 * validated["accepted_span_replay_count"] / accepted) if accepted else None
    )
    unsupported_rate = (
        validated["unsupported_rejected"] / n_candidates if n_candidates else None
    )
    invalid_rate = (
        validated["invalid_schema_rejected"] / n_candidates if n_candidates else None
    )
    if accepted == 0:
        gates_status = "NOT_EXERCISED"
        gates_pass = False
        span_replay_gate = "NOT_EXERCISED"
    else:
        gates_pass = (
            validated["accepted_unsupported"] == 0
            and validated["accepted_cross_event"] == 0
            and validated["invalid_schema_accepted"] == 0
            and validated["accepted_span_replay_count"] == accepted
        )
        gates_status = "PASS" if gates_pass else "FAIL"
        span_replay_gate = (
            f"{replay_pct:.1f}% ({accepted} accepted)" if replay_pct is not None else "n/a"
        )
    return {
        "n_gold_exchanges": n_gold,
        "n_model_candidates": n_candidates,
        "exchange_boundary_quality": {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        },
        "source_span_replay_success_pct": replay_pct,
        "unsupported_candidate_rate": unsupported_rate,
        "cross_event_contamination_accepted": validated["accepted_cross_event"],
        "topic_label_agreement_mean_jaccard": (
            sum(jaccards) / len(jaccards) if jaccards else None
        ),
        "identity_role_availability": identity,
        "invalid_schema_rate": invalid_rate,
        "accepted_count": accepted,
        "unsupported_rejected": validated["unsupported_rejected"],
        "invalid_schema_rejected": validated["invalid_schema_rejected"],
        "cross_event_rejected": validated["cross_event_rejected"],
        "accepted_unsupported": validated["accepted_unsupported"],
        "accepted_cross_event": validated["accepted_cross_event"],
        "invalid_schema_accepted": validated["invalid_schema_accepted"],
        "accepted_span_replay_count": validated["accepted_span_replay_count"],
        "valid_candidates": valid,
        "rejected_candidates": validated["rejected_candidates"],
        "rejection_reason": [
            r["rejection_reason"] for r in validated["rejected_candidates"]
        ],
        "hard_gates": {
            "status": gates_status,
            "accepted_unsupported": validated["accepted_unsupported"],
            "accepted_cross_event": validated["accepted_cross_event"],
            "cross_event": validated["accepted_cross_event"],
            "span_replay_of_accepted": span_replay_gate,
            "invalid_schema_accepted": validated["invalid_schema_accepted"],
            "all_pass": gates_pass,
        },
        "per_exchange": per_exchange,
        "status": "scored",
    }


# ── Model calls ───────────────────────────────────────────────────────────────


@dataclass
class ModelAttempt:
    provider: str
    model: str
    prompt_version: str = "e3a-qa-extraction-v1"
    status: str = "pending"
    degraded_reason: str | None = None
    raw_response: str | None = None
    candidates: list[dict] = field(default_factory=list)
    input_tokens: int | None = 0
    output_tokens: int | None = 0
    est_cost_usd: float | None = 0.0
    latency_ms: float = 0.0
    provider_fallback_reason: str | None = None
    is_comparator: bool = False
    comparator_note: str = ""
    endpoint_class: str | None = None
    base_url_source: str | None = None
    preflight: dict[str, Any] = field(default_factory=dict)
    served_model: str | None = None
    http_status: int | None = None
    error_kind: str | None = None
    observed_usage: dict[str, int | None] | None = None


def _parse_plist_llm(root: Path) -> tuple[str, str]:
    path = root / WORKER_PLIST_REL
    if not path.exists():
        return "", ""
    data = plistlib.loads(path.read_bytes())
    env = data.get("EnvironmentVariables") or {}
    return str(env.get("EARNINGS_LLM_BASE_URL") or "").strip(), str(
        env.get("EARNINGS_LLM_MODEL") or ""
    ).strip()


def resolve_qwen_openai_compat_cfg(repo_root: Path, yaml_oc: dict) -> dict[str, Any]:
    """Same override order as tools/earnings_worker/run_worker.py.

    Env EARNINGS_LLM_BASE_URL / EARNINGS_LLM_MODEL win; else the durable
    worker launchd plist; else the YAML placeholder. Never invent a second
    local-model route.
    """
    cfg = dict(yaml_oc or {})
    env_url = os.environ.get("EARNINGS_LLM_BASE_URL", "").strip()
    env_model = os.environ.get("EARNINGS_LLM_MODEL", "").strip()
    plist_url, plist_model = _parse_plist_llm(repo_root)
    if env_url:
        cfg["base_url"] = env_url
        cfg["base_url_source"] = "env"
    elif plist_url:
        cfg["base_url"] = plist_url
        cfg["base_url_source"] = "earnings_worker_plist"
    else:
        cfg["base_url_source"] = "yaml_placeholder"
    if env_model:
        cfg["model"] = env_model
        cfg["model_source"] = "env"
    elif plist_model:
        cfg["model"] = plist_model
        cfg["model_source"] = "earnings_worker_plist"
    else:
        cfg["model_source"] = "yaml_placeholder"
    return cfg


def _endpoint_class(base_url: str) -> str:
    host = (urlparse(base_url).hostname or "").lower()
    if host in {"localhost", "127.0.0.1", "::1"}:
        return "loopback"
    if host.startswith("192.168.") or host.startswith("10.") or host.startswith("172."):
        return "private_lan"
    if not host:
        return "unconfigured"
    return "other"


def preflight_qwen_endpoint(oc_cfg: dict) -> dict[str, Any]:
    """Read-only /models probe. Records class + model identity, not credentials."""
    base_url = str(oc_cfg.get("base_url") or "").rstrip("/")
    model = str(oc_cfg.get("model") or "")
    info: dict[str, Any] = {
        "endpoint_class": _endpoint_class(base_url),
        "model": model,
        "base_url_source": oc_cfg.get("base_url_source"),
        "model_source": oc_cfg.get("model_source"),
        "status": "unconfigured",
        "served_ids": [],
    }
    if not base_url or not model:
        return info
    url = f"{base_url}/models"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            body = resp.read(8192)
        data = json.loads(body.decode("utf-8"))
        ids = [
            item.get("id")
            for item in (data.get("data") or [])
            if isinstance(item, dict)
        ]
        info["served_ids"] = [i for i in ids if i]
        info["status"] = "ok" if model in info["served_ids"] or info["served_ids"] else "ok"
        if info["served_ids"] and model not in info["served_ids"]:
            info["status"] = "model_not_served"
    except Exception as exc:  # noqa: BLE001
        info["status"] = "unreachable"
        info["error_class"] = type(exc).__name__
    return info


def _record_health(*, rung: str, ok: bool, latency_ms: float, model: str, error_class: str = "", detail: str = "") -> None:
    try:
        from engine import provider_health as ph

        ph.record_attempt(
            lane=LANE,
            context="e3a_shadow_eval",
            rung=rung,
            ok=ok,
            latency_ms=int(max(0.0, latency_ms)),
            model=model,
            error_class=error_class,
            detail=detail[:200],
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[e3_shadow_compiler] provider_health record failed: {exc}")


def ledger_attempt(attempt: ModelAttempt, root: Path, run_id: str, *,
                   fabric: bool = False, fabric_observation: dict | None = None) -> bool:
    """Publish through the incumbent usage owner and return its actual ACK."""
    try:
        from lib.ai_costs import record_usage

        local = not fabric and attempt.endpoint_class in {"loopback", "private_lan"}
        cost_basis = "unknown" if fabric else ("local" if local else
            ("unknown" if attempt.est_cost_usd is None else "metered"))
        est_cost = None if fabric else (0.0 if local else attempt.est_cost_usd)
        note = (f"comparator=True {attempt.comparator_note}" if attempt.is_comparator
                else "qwen_first_rung")
        route = None
        if fabric:
            note += f" transport=fabric requested_model={attempt.model} cost_basis=unknown"
            if fabric_observation is not None:
                routed = fabric_observation["routing"]
                route = {key: routed[key] for key in (
                    "selected_model", "mode", "protocol", "driver", "profile",
                    "source", "recipe_digest", "selection_digest")}
        elif local:
            note += " transport=openai_compat cost_basis=local"
        return record_usage(
            lane=LANE, provider=attempt.provider,
            model=attempt.served_model if fabric else attempt.model,
            input_tokens=attempt.input_tokens, output_tokens=attempt.output_tokens,
            est_cost_usd=est_cost, cost_basis=cost_basis,
            cycle_id=run_id, stage="e3a_shadow_eval", note=note,
            **({"fabric_route": route} if fabric else {}), root=root,
        ) is True
    except Exception as exc:  # noqa: BLE001
        if not fabric:
            print(f"[e3_shadow_compiler] ai_costs ledger FAILED: {exc}")
        return False


def _attempt_qwen(user_prompt: str, repo_root: Path) -> ModelAttempt:
    """Attempt Qwen via the earnings-worker OpenAI-compat override. Never raises."""
    attempt = ModelAttempt(
        provider="openai_compat",
        model="qwen3.5:9b",
        is_comparator=False,
        input_tokens=None,
        output_tokens=None,
        est_cost_usd=None,
    )
    t0 = time.monotonic()
    try:
        import yaml
        from engine.earnings_qual import _call_openai_compat_detailed

        with open(repo_root / "config/earnings_qual.yml") as f:
            cfg = yaml.safe_load(f)
        oc_cfg = resolve_qwen_openai_compat_cfg(repo_root, cfg.get("openai_compat") or {})
        oc_cfg["timeout_s"] = max(float(oc_cfg.get("timeout_s") or 120), 300)
        oc_cfg["connect_timeout_s"] = float(oc_cfg.get("connect_timeout_s") or 5)
        attempt.model = str(oc_cfg.get("model") or attempt.model)
        attempt.base_url_source = str(oc_cfg.get("base_url_source") or "")
        attempt.endpoint_class = _endpoint_class(str(oc_cfg.get("base_url") or ""))
        attempt.preflight = preflight_qwen_endpoint(oc_cfg)
        if attempt.preflight.get("status") not in {"ok"}:
            attempt.status = "provider_unavailable"
            attempt.degraded_reason = f"preflight_{attempt.preflight.get('status')}"
            attempt.latency_ms = (time.monotonic() - t0) * 1000
            _record_health(
                rung="openai_compat",
                ok=False,
                latency_ms=attempt.latency_ms,
                model=attempt.model,
                error_class="preflight",
                detail=str(attempt.degraded_reason),
            )
            return attempt

        result = _call_openai_compat_detailed(
            system=SYSTEM_PROMPT,
            user=user_prompt,
            oc_cfg=oc_cfg,
            max_tokens=max(int(oc_cfg.get("max_tokens") or EXTRACTION_MAX_TOKENS),
                           EXTRACTION_MAX_TOKENS),
        )
        text, reason = result.text, result.reason
        attempt.observed_usage = result.observed_usage
        attempt.served_model = result.served_model
        attempt.http_status = result.status_code
        attempt.error_kind = result.error_kind
        usage = result.observed_usage or {}
        attempt.input_tokens = usage.get("prompt_tokens")
        attempt.output_tokens = usage.get("completion_tokens")
        attempt.latency_ms = (time.monotonic() - t0) * 1000
        if text is None:
            attempt.status = "provider_unavailable"
            attempt.degraded_reason = reason
            _record_health(
                rung="openai_compat",
                ok=False,
                latency_ms=attempt.latency_ms,
                model=attempt.model,
                error_class=str(reason or "openai_compat_error"),
            )
        else:
            attempt.raw_response = text
            attempt.status = "ok"
            attempt.candidates = _parse_candidates(text)
            _record_health(
                rung="openai_compat",
                ok=True,
                latency_ms=attempt.latency_ms,
                model=attempt.model,
            )
            if attempt.endpoint_class in {"loopback", "private_lan"}:
                attempt.est_cost_usd = 0.0
    except Exception as exc:  # noqa: BLE001
        attempt.latency_ms = (time.monotonic() - t0) * 1000
        attempt.status = "provider_unavailable"
        attempt.degraded_reason = f"exception: {type(exc).__name__}"
        _record_health(
            rung="openai_compat",
            ok=False,
            latency_ms=attempt.latency_ms,
            model=attempt.model,
            error_class=type(exc).__name__,
        )
    return attempt


def freeze_comparator_choice(repo_root: Path, run_id: str = "") -> dict[str, Any]:
    """Freeze provider/model before the first successful comparator inference."""
    import yaml
    from engine.llm_auth import build_providers

    with open(repo_root / "config/earnings_qual.yml") as f:
        cfg = yaml.safe_load(f)
    cfg = dict(cfg)
    cfg["usage_lane"] = LANE
    cfg["usage_stage"] = "e3a_shadow_comparator"
    if run_id:
        cfg["usage_cycle_id"] = run_id
    cfg["codex_provider"] = False
    cfg["provider_order"] = ["oauth", "anthropic"]
    cfg["opus_model"] = FROZEN_COMPARATOR_MODEL
    providers = build_providers(cfg, opus_model=FROZEN_COMPARATOR_MODEL)
    usable = [p for p in providers if p.get("cred") and p.get("client") is not None]
    oauth = [p for p in usable if p.get("name") == "oauth"]
    anthropic_rungs = [p for p in usable if p.get("name") == "anthropic"]
    chosen_rungs = oauth + anthropic_rungs
    freeze = {
        "model": FROZEN_COMPARATOR_MODEL,
        "gold_labels": False,
        "provider_plane": "llm_auth",
        "provider": "oauth" if oauth else ("anthropic" if anthropic_rungs else None),
        "available_rungs": [p.get("name") for p in chosen_rungs],
        "n_oauth_rungs": len(oauth),
        "usage_cycle_id": run_id,
        "status": "frozen" if chosen_rungs else "unresolved_environment_blocker",
    }
    return {"freeze": freeze, "providers": chosen_rungs, "cfg": cfg}


def _attempt_comparator(user_prompt: str, repo_root: Path, run_id: str = "") -> ModelAttempt:
    """Stronger comparator via the existing llm_auth plane. Never raises."""
    attempt = ModelAttempt(
        provider="unresolved",
        model=FROZEN_COMPARATOR_MODEL,
        is_comparator=True,
        comparator_note=(
            "Independent comparator — evaluation only, no production authority. "
            "Runs on the same held source bytes as Qwen. Gold labels withheld. "
            f"Frozen model: {FROZEN_COMPARATOR_MODEL} via existing llm_auth."
        ),
    )
    t0 = time.monotonic()
    try:
        from engine.llm_auth import make_call

        choice = freeze_comparator_choice(repo_root, run_id=run_id)
        freeze = choice["freeze"]
        attempt.preflight = {"comparator_freeze": freeze}
        if freeze["status"] != "frozen":
            attempt.status = "unresolved_environment_blocker"
            attempt.degraded_reason = "no_approved_stronger_model_route"
            attempt.latency_ms = (time.monotonic() - t0) * 1000
            _record_health(
                rung="comparator",
                ok=False,
                latency_ms=attempt.latency_ms,
                model=attempt.model,
                error_class="no_provider",
            )
            return attempt

        chosen = choice["providers"][0]
        attempt.provider = str(chosen.get("name"))
        attempt.model = str(chosen.get("model") or FROZEN_COMPARATOR_MODEL)
        for prov in choice["providers"]:
            prov["usage_lane"] = LANE
            prov["usage_stage"] = "e3a_shadow_comparator"
            if run_id:
                prov["usage_cycle_id"] = run_id

        def call_fn(client: Any, model: str) -> tuple[str | None, str | None, Any]:
            resp = client.messages.create(
                model=model,
                max_tokens=EXTRACTION_MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text = "".join(
                b.text for b in (resp.content or [])
                if getattr(b, "type", "") == "text"
            ) or None
            usage = getattr(resp, "usage", None)
            attempt.input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
            attempt.output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
            return text, None, resp

        attempts_log: list[dict] = []
        text, fallback_reason, provider_used = make_call(
            providers=choice["providers"],
            call_fn=call_fn,
            context="e3a_shadow_comparator",
            attempts=attempts_log,
        )
        attempt.preflight["waterfall_attempts"] = [
            {k: row.get(k) for k in ("rung", "ok", "error_class", "skipped") if k in row}
            for row in attempts_log
        ]
        attempt.latency_ms = (time.monotonic() - t0) * 1000
        attempt.provider_fallback_reason = fallback_reason
        if provider_used:
            attempt.provider = provider_used
        if text is None:
            attempt.status = "unresolved_environment_blocker"
            attempt.degraded_reason = fallback_reason or "no_text"
        else:
            attempt.raw_response = text
            attempt.status = "ok"
            attempt.candidates = _parse_candidates(text)
            try:
                from lib.ai_costs import estimate_cost_usd

                cost = estimate_cost_usd(
                    attempt.model,
                    attempt.input_tokens,
                    attempt.output_tokens,
                    root=repo_root,
                )
                if cost is not None:
                    attempt.est_cost_usd = float(cost)
            except Exception:  # noqa: BLE001
                pass
    except Exception as exc:  # noqa: BLE001
        attempt.latency_ms = (time.monotonic() - t0) * 1000
        attempt.status = "unresolved_environment_blocker"
        attempt.degraded_reason = f"exception: {type(exc).__name__}"
        _record_health(
            rung="comparator",
            ok=False,
            latency_ms=attempt.latency_ms,
            model=attempt.model,
            error_class=type(exc).__name__,
        )
    return attempt


def _parse_candidates(raw: str) -> list[dict]:
    """Parse model output as a JSON array of exchange candidates."""
    try:
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [p for p in parsed if isinstance(p, dict)]
        if isinstance(parsed, dict):
            for key in ("exchanges", "candidates", "qa_exchanges"):
                val = parsed.get(key)
                if isinstance(val, list):
                    return [p for p in val if isinstance(p, dict)]
        return []
    except Exception:  # noqa: BLE001
        return []


# ── Main eval entry point ─────────────────────────────────────────────────────


def _bounded_telemetry_proof(repo_root: Path, shard_info: dict[str, str]) -> dict[str, Any]:
    """Preserve bounded eval proof without committing global JSONL merges."""
    health_rel = shard_info.get("provider_health_path") or ""
    health_path = Path(health_rel) if health_rel else None
    if health_path is not None and not health_path.is_absolute():
        health_path = repo_root / health_path

    def _rel(path: Path | None, given: str) -> str:
        if path is None:
            return given
        try:
            return str(path.relative_to(repo_root))
        except ValueError:
            return given or str(path)

    proof: dict[str, Any] = {
        "lane": LANE,
        "ai_costs_shard": shard_info.get("ai_costs_shard"),
        "provider_health_path": _rel(health_path, health_rel),
        "ai_costs_rows": [],
        "provider_health_rows": [],
    }
    shard_name = shard_info.get("ai_costs_shard") or ""
    shard_file = repo_root / "data" / "ai_costs" / "usage.d" / f"{shard_name}.jsonl"
    if shard_file.is_file():
        rows = []
        for line in shard_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows.append({
                k: row.get(k)
                for k in (
                    "ts", "lane", "provider", "model", "input_tokens",
                    "output_tokens", "est_cost_usd", "cost_basis", "stage",
                    "note", "cycle_id",
                )
            })
        proof["ai_costs_rows"] = rows
        proof["ai_costs_shard_file"] = str(shard_file.relative_to(repo_root))
    if health_path is not None and health_path.is_file():
        rows = []
        for line in health_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows.append({
                k: row.get(k)
                for k in (
                    "ts", "lane", "context", "rung", "model", "ok",
                    "latency_ms", "error_class",
                )
            })
        proof["provider_health_rows"] = rows
    return proof


def _git_head(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return (result.stdout or "").strip()


def eval_bindings(
    repo_root: Path,
    *,
    gold_sha: str,
    taxonomy_hash: str,
    run_id: str,
) -> dict[str, str]:
    """Bind a receipt to the exact code, prompt, gold, and source that produced it."""
    compiler_path = Path(__file__).resolve()
    return {
        "git_head": _git_head(repo_root),
        "compiler_sha256": hashlib.sha256(compiler_path.read_bytes()).hexdigest(),
        "system_prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest(),
        "gold_sha256": gold_sha,
        "taxonomy_hash": taxonomy_hash,
        "exhibit_sha256": FROZEN_EXHIBIT_SHA,
        "transcript_sha256": FROZEN_TRANSCRIPT_SHA,
        "workspace_sha256": PINNED_WORKSPACE_SHA,
        "generation_id": PINNED_GENERATION_ID,
        "run_id": run_id,
        "superseded_gold_sha256_v1": SUPERSEDED_GOLD_SHA_V1,
    }


def _enable_eval_shards(run_id: str, repo_root: Path) -> dict[str, str]:
    """Route telemetry into the supported shard/override files for this eval."""
    shard = f"e3a-pr6245-{run_id}"
    health_path = repo_root / "research/earnings_intelligence/e3/gold" / f"provider_health_{run_id}.jsonl"
    os.environ["AI_COSTS_SHARD"] = shard
    os.environ["PROVIDER_HEALTH_PATH"] = str(health_path)
    return {"ai_costs_shard": shard, "provider_health_path": str(health_path.relative_to(repo_root))}



# The existing evaluation receipt owns selected inference and publication.
_FABRIC_E3_SCHEMA = "e3a_eval_receipt.v2"
_FABRIC_E3_KEY = "_fabric_evaluation"
_FABRIC_QWEN_MODEL = "qwen3.8-flash"


def _fabric_e3_owners():
    from engine import catalyst_tone, fabric_inference_client, llm_auth
    return catalyst_tone, fabric_inference_client, llm_auth


def _fabric_e3_hash(value):
    cache, _, _ = _fabric_e3_owners()
    return hashlib.sha256(cache._cache_json(value)).hexdigest()


def _fabric_e3_fields(value, fields):
    if type(value) is not dict or set(value) != set(fields.split()):
        raise ValueError("fabric_e3_receipt_invalid")
    return value


def _fabric_e3_kwargs(frozen):
    return {
        "model": _FABRIC_QWEN_MODEL,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user",
                      "content": _build_user_prompt(frozen["segments"]) + "\n\n/no_think"}],
        "max_tokens": EXTRACTION_MAX_TOKENS,
        "temperature": 0,
        "reasoning_effort": "none",
        "stream": False,
        "request_id": frozen["run_id"] + ":qwen:brain:0",
    }


def _fabric_e3_candidates(answer):
    cache, _, _ = _fabric_e3_owners()
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("fabric_e3_response_invalid")
    if len(answer.encode("utf-8")) > 1024 * 1024:
        raise ValueError("fabric_e3_response_invalid")
    parsed = cache._cache_decode(answer.encode("utf-8"))
    if type(parsed) is not list or len(parsed) > 256 or any(type(x) is not dict for x in parsed):
        raise ValueError("fabric_e3_response_invalid")
    return parsed


def _fabric_e3_attempt(original):
    leg = original["qwen"]
    observation = leg["observation"]
    actual = leg["actual_observation"] or {
        "serving_model": None, "input_tokens": None, "output_tokens": None}
    settled = (leg["close"]["outcome"] is not None
               and leg["close"]["outcome"]["disposition"] == "closed"
               and leg["close"]["outcome"]["closed"]
               and not leg["close"]["outcome"]["effect_unknown"])
    status = leg["answer_status"] if leg["phase"] == "complete" and settled else "held"
    candidates = _fabric_e3_candidates(leg["answer"]) if status == "ok" else []
    return ModelAttempt(
        provider=observation["routing"]["pool"] if observation is not None else "unknown",
        model=_FABRIC_QWEN_MODEL, status=status,
        degraded_reason=None if status == "ok" else leg["reason"],
        raw_response=leg["answer"], candidates=candidates,
        input_tokens=actual["input_tokens"], output_tokens=actual["output_tokens"],
        est_cost_usd=None, latency_ms=leg["latency_ms"] or 0.0,
        endpoint_class="fabric", base_url_source="application_fabric_factory",
        preflight={"status": "original_inspection_retained" if leg["inspection"] else
                   "qualification_held"},
        served_model=actual["serving_model"],
        observed_usage={"prompt_tokens": actual["input_tokens"],
                        "completion_tokens": actual["output_tokens"]},
    )


def _fabric_e3_document(original):
    frozen, leg = original["input"], original["qwen"]
    attempt = _fabric_e3_attempt(original)
    comparator = ModelAttempt(
        provider="unknown", model=FROZEN_COMPARATOR_MODEL, is_comparator=True,
        status="held", degraded_reason="fabric_native_comparator_unqualified",
        input_tokens=None, output_tokens=None, est_cost_usd=None)
    scores = {}
    # Gold is decoded for scoring only after the owned model call has returned.
    if leg["answer_status"] is not None:
        gold = json.loads(frozen["gold_text"])
        scores = {
            "qwen": score_attempt(attempt, gold, frozen["segments"]),
            "comparator": score_attempt(comparator, gold, frozen["segments"]),
        }
    qwen = {
        "provider": attempt.provider, "model": attempt.model,
        "requested_model": _FABRIC_QWEN_MODEL, "served_model": attempt.served_model,
        "status": attempt.status, "degraded_reason": attempt.degraded_reason,
        "n_candidates": len(attempt.candidates), "raw_excerpt": (attempt.raw_response or "")[:400],
        "input_tokens": attempt.input_tokens, "output_tokens": attempt.output_tokens,
        "observed_usage": attempt.observed_usage, "latency_ms": round(attempt.latency_ms, 1),
        "est_cost_usd": None, "cost_basis": "unknown", "transport": "fabric",
        "endpoint_class": "fabric", "base_url_source": "application_fabric_factory",
        "preflight": attempt.preflight, "gold_labels_seen": False,
        "operation_id": leg["operation_id"], "phase": leg["phase"],
        "close": leg["close"], "ledger": leg["ledger"],
    }
    bindings = frozen["bindings"]
    return {
        "schema": _FABRIC_E3_SCHEMA, "run_id": frozen["run_id"], "lane": LANE,
        "event_id": EVENT_ID, "gold_path": str(GOLD_PATH),
        "bindings": bindings, **bindings,
        "telemetry": {"owner": "lib.ai_costs.record_usage", "process_environment_mutated": False},
        "steps": {
            "sha_verification": frozen["sha_verification"],
            "segmenter": {"segment_count": len(frozen["segments"]), "truncation": "none",
                          "id_method": "sha256[:16]_index04d"},
            "prompt_built": {"prompt_version": "e3a-qa-extraction-v1",
                             "uses_bounded_transcript_text": False,
                             "segment_count": len(frozen["segments"]),
                             "gold_labels_in_prompt": False},
            "comparator_freeze": dict(original["comparator"]),
        },
        "model_attempts": {
            "qwen": qwen,
            "comparator": {"provider": None, "model": FROZEN_COMPARATOR_MODEL,
                           "requested_model": FROZEN_COMPARATOR_MODEL, "served_model": None,
                           "status": "held", "phase": "unattempted", "is_comparator": True,
                           "non_authoritative": True, "n_candidates": 0, "gold_labels_seen": False,
                           "degraded_reason": "fabric_native_comparator_unqualified",
                           "input_tokens": None, "output_tokens": None,
                           "est_cost_usd": None, "cost_basis": "unknown",
                           "operation_id": original["comparator"]["operation_id"]},
        },
        "scores": scores,
        "summary": {
            "sha_check": "pass", "live_workspace_verified": True,
            "gold_sha256": FROZEN_GOLD_SHA, "gold_frozen_before_inference": True,
            "neither_model_saw_gold_labels": True, "qwen_status": attempt.status,
            "comparator_status": "held",
            "hard_gates_qwen": scores.get("qwen", {}).get("hard_gates", {}).get("status", "NOT_EXERCISED"),
            "hard_gates_comparator": scores.get("comparator", {}).get("hard_gates", {}).get("status", "NOT_EXERCISED"),
            "usefulness_bar_decision": "refusal_n7_too_small", "return_to_sol": True,
            "e3b_auto_unlocked": False, "event_workspace_v1_advanced": False, "r2_written": False,
            "note": "Exact Qwen3.8 Fabric evaluation; original evidence is retained. "
                    "Haiku remains unattempted until its native route is qualified. "
                    "The frozen N=7 refusal and all E3-B/product gates remain closed.",
        },
        _FABRIC_E3_KEY: original,
    }


def _fabric_e3_validate(document):
    import math
    import re
    cache, transport, auth = _fabric_e3_owners()
    if type(document) is not dict or document.get("schema") != _FABRIC_E3_SCHEMA:
        raise ValueError("fabric_e3_receipt_invalid")
    original = _fabric_e3_fields(document.get(_FABRIC_E3_KEY),
        "schema input input_digest legacy_receipt legacy_digest qwen comparator")
    if original["schema"] != "e3a.fabric_original.v1":
        raise ValueError("fabric_e3_receipt_invalid")
    frozen = _fabric_e3_fields(original["input"],
        "run_id mode_id bindings sha_verification segments gold_text request")
    segments = frozen["segments"]
    if (type(segments) is not list or not 1 <= len(segments) <= 4096
            or any(type(s) is not dict or not isinstance(s.get("text", ""), str) for s in segments)
            or not isinstance(frozen["gold_text"], str)
            or hashlib.sha256(frozen["gold_text"].encode("utf-8")).hexdigest() != FROZEN_GOLD_SHA
            or type(frozen["mode_id"]) is not str
            or re.fullmatch(r"[a-z][a-z0-9_]{2,63}", frozen["mode_id"]) is None
            or original["input_digest"] != _fabric_e3_hash(frozen)):
        raise ValueError("fabric_e3_input_changed")
    basis = [_FABRIC_E3_SCHEMA, EVENT_ID, FROZEN_TRANSCRIPT_SHA, FROZEN_GOLD_SHA,
             TAXONOMY_HASH, SYSTEM_PROMPT, _build_user_prompt(segments)]
    if frozen["run_id"] != "e3a-fabric:" + _fabric_e3_hash(basis)[:24]:
        raise ValueError("fabric_e3_identity_changed")
    bindings = _fabric_e3_fields(frozen["bindings"],
        "git_head compiler_sha256 system_prompt_sha256 gold_sha256 taxonomy_hash "
        "exhibit_sha256 transcript_sha256 workspace_sha256 generation_id run_id "
        "superseded_gold_sha256_v1")
    expected = {
        "system_prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest(),
        "gold_sha256": FROZEN_GOLD_SHA, "taxonomy_hash": TAXONOMY_HASH,
        "exhibit_sha256": FROZEN_EXHIBIT_SHA, "transcript_sha256": FROZEN_TRANSCRIPT_SHA,
        "workspace_sha256": PINNED_WORKSPACE_SHA, "generation_id": PINNED_GENERATION_ID,
        "run_id": frozen["run_id"], "superseded_gold_sha256_v1": SUPERSEDED_GOLD_SHA_V1,
    }
    if (any(bindings[k] != v for k, v in expected.items())
            or not isinstance(bindings["compiler_sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", bindings["compiler_sha256"]) is None
            or not isinstance(bindings["git_head"], str) or len(bindings["git_head"]) > 128
            or type(frozen["sha_verification"]) is not dict
            or frozen["sha_verification"].get("check") != "pass"
            or frozen["sha_verification"].get("exhibit_sha") != FROZEN_EXHIBIT_SHA
            or frozen["sha_verification"].get("transcript_sha") != FROZEN_TRANSCRIPT_SHA
            or frozen["sha_verification"].get("live_workspace", {}).get("source_shas_match") is not True
            or frozen["request"] != _fabric_e3_kwargs(frozen)):
        raise ValueError("fabric_e3_input_changed")
    prior = original["legacy_receipt"]
    if (prior is not None and (type(prior) is not dict or prior.get("schema") != "e3a_eval_receipt.v1")
            or original["legacy_digest"] != (_fabric_e3_hash(prior) if prior is not None else None)):
        raise ValueError("fabric_e3_legacy_changed")
    comparator = {
        "phase": "unattempted", "requested_model": FROZEN_COMPARATOR_MODEL,
        "operation_id": frozen["run_id"] + ":comparator",
        "reason": "fabric_native_comparator_unqualified",
    }
    if original["comparator"] != comparator:
        raise ValueError("fabric_e3_comparator_changed")
    leg = _fabric_e3_fields(original["qwen"],
        "phase reason operation_id request_id request_digest inspection answer answer_sha256 "
        "answer_status observation actual_observation usage latency_ms close ledger")
    rid, body = transport._request(frozen["request"], _FABRIC_QWEN_MODEL, False, exact_scoped=True)
    if (leg["operation_id"] != frozen["run_id"] + ":qwen" or leg["request_id"] != rid
            or leg["request_digest"] != transport._auto_request_digest(json.loads(body))
            or leg["phase"] not in {"unattempted", "claimed", "observed", "closed", "complete", "held"}
            or leg["reason"] not in {None, "fabric_qualification_required", "fabric_qualification_unavailable",
                "fabric_operation_claimed", "fabric_binding_unavailable", "fabric_response_invalid",
                "fabric_observation_unavailable", "fabric_operation_unavailable",
                "fabric_close_unknown", "fabric_ledger_unknown"}
            or leg["answer_status"] not in {None, "ok", "invalid_response", "provider_unavailable"}):
        raise ValueError("fabric_e3_operation_changed")
    close = _fabric_e3_fields(leg["close"], "phase outcome")
    ledger = _fabric_e3_fields(leg["ledger"], "phase ack")
    if (close["phase"] not in {"unattempted", "reserved", "intent", "observed", "unavailable"}
            or ledger["phase"] not in {"unattempted", "intent", "complete", "unknown"}
            or ledger["ack"] not in (None, True, False)
            or ledger["ack"] is not None and type(ledger["ack"]) is not bool
            or (ledger["phase"] == "complete") != (ledger["ack"] is True)
            or (ledger["phase"] == "unknown") != (ledger["ack"] is False)):
        raise ValueError("fabric_e3_effect_changed")
    if leg["inspection"] is not None:
        inspection = transport.validate_auto_inspection(leg["inspection"])
        if (inspection["schema"] != transport.EXACT_INSPECTION_SCHEMA
                or inspection["requested_model"] != _FABRIC_QWEN_MODEL
                or inspection["workload_policy"].get("execution_surface") != "inference"
                or inspection["workload_policy"].get("allowed_order") != ["fabric"]
                or "site_batch" not in inspection["workload_policy"].get("profiles", [])):
            raise ValueError("fabric_e3_inspection_changed")
    if leg["phase"] == "unattempted":
        if (any(leg[k] is not None for k in ("inspection", "answer", "answer_sha256", "answer_status",
                "observation", "actual_observation", "usage", "latency_ms"))
                or close != {"phase": "unattempted", "outcome": None}
                or ledger != {"phase": "unattempted", "ack": None}):
            raise ValueError("fabric_e3_unattempted_changed")
    elif leg["inspection"] is None:
        raise ValueError("fabric_e3_inspection_missing")
    if leg["answer"] is None:
        if leg["answer_sha256"] is not None or leg["answer_status"] == "ok":
            raise ValueError("fabric_e3_answer_changed")
    elif (type(leg["answer"]) is not str or len(leg["answer"].encode("utf-8")) > 1024 * 1024
            or leg["answer_sha256"] != hashlib.sha256(leg["answer"].encode("utf-8")).hexdigest()):
        raise ValueError("fabric_e3_answer_changed")
    if leg["answer_status"] == "ok":
        _fabric_e3_candidates(leg["answer"])
    if leg["observation"] is not None:
        transport.validate_auto_observation(leg["observation"], leg["inspection"],
            operation_id=leg["operation_id"], request_id=rid, request_digest=leg["request_digest"],
            routed_request_digest=None, max_tokens=EXTRACTION_MAX_TOKENS,
            require_success=leg["answer_status"] == "ok")
    elif leg["answer_status"] == "ok":
        raise ValueError("fabric_e3_observation_missing")
    actual = leg["actual_observation"]
    if actual is not None:
        _fabric_e3_fields(actual, "request_id serving_model input_tokens output_tokens")
        if (actual["request_id"] != leg["request_id"]
                or actual["serving_model"] is not None and (
                    not isinstance(actual["serving_model"], str)
                    or auth._FABRIC_ID.fullmatch(actual["serving_model"]) is None)
                or any(actual[k] is not None and (
                    type(actual[k]) is not int or not 0 <= actual[k] <= transport.MAX_NATIVE_TOKENS)
                    for k in ("input_tokens", "output_tokens"))):
            raise ValueError("fabric_e3_actual_observation_invalid")
    if leg["observation"] is not None and (
            actual is None or actual["serving_model"] != leg["observation"]["serving_model"]
            or any(actual[k] != leg["observation"]["usage"][k]
                   for k in ("input_tokens", "output_tokens"))):
        raise ValueError("fabric_e3_actual_observation_changed")
    if leg["usage"] is not None:
        usage = _fabric_e3_fields(leg["usage"],
            "input_tokens output_tokens usage_state completed_input_tokens completed_output_tokens")
        if (usage["usage_state"] not in {"known", "unknown"}
                or any(type(usage[k]) is not int or not 0 <= usage[k] <= transport.MAX_NATIVE_TOKENS
                       for k in ("completed_input_tokens", "completed_output_tokens"))
                or any(usage[k] is not None and (
                    type(usage[k]) is not int or not 0 <= usage[k] <= transport.MAX_NATIVE_TOKENS)
                       for k in ("input_tokens", "output_tokens"))
                or usage["usage_state"] == "known" and any(
                    usage[k] != usage["completed_" + k] for k in ("input_tokens", "output_tokens"))
                or usage["usage_state"] == "unknown" and any(
                    usage[k] is not None for k in ("input_tokens", "output_tokens"))):
            raise ValueError("fabric_e3_usage_invalid")
        complete_actual = actual is not None and all(actual[k] is not None
            for k in ("input_tokens", "output_tokens"))
        if any(usage["completed_" + k] != (actual[k] if complete_actual else 0)
               for k in ("input_tokens", "output_tokens")):
            raise ValueError("fabric_e3_usage_changed")
    if leg["latency_ms"] is not None and (type(leg["latency_ms"]) not in (int, float)
            or not math.isfinite(leg["latency_ms"]) or leg["latency_ms"] < 0):
        raise ValueError("fabric_e3_latency_invalid")
    if close["outcome"] is not None:
        outcome = _fabric_e3_fields(close["outcome"], "disposition closed effect_unknown attempted")
        if (outcome["disposition"] not in {"local_only", "refused", "pending", "effect_unknown", "closed"}
                or any(type(outcome[k]) is not bool for k in ("closed", "effect_unknown", "attempted"))
                or outcome["closed"] != (outcome["disposition"] == "closed")
                or outcome["closed"] and (outcome["effect_unknown"] or not outcome["attempted"])
                or close["phase"] != "observed"):
            raise ValueError("fabric_e3_close_invalid")
    elif close["phase"] == "observed":
        raise ValueError("fabric_e3_close_missing")
    result_keys = ("answer", "answer_sha256", "answer_status", "observation",
                   "actual_observation", "usage", "latency_ms")
    has_result = (leg["answer_status"] is not None and leg["usage"] is not None
                  and leg["latency_ms"] is not None)
    if leg["phase"] == "claimed" and (
            any(leg[k] is not None for k in result_keys)
            or close != {"phase": "reserved", "outcome": None}
            or ledger != {"phase": "unattempted", "ack": None}
            or leg["reason"] != "fabric_operation_claimed"):
        raise ValueError("fabric_e3_claim_changed")
    if leg["phase"] == "observed" and (
            not has_result or close != {"phase": "intent", "outcome": None}
            or ledger != {"phase": "unattempted", "ack": None}):
        raise ValueError("fabric_e3_observed_changed")
    if leg["phase"] == "closed" and (
            not has_result or close["phase"] != "observed"
            or ledger["phase"] not in {"unattempted", "intent"}):
        raise ValueError("fabric_e3_closed_changed")
    if leg["phase"] == "complete" and (
            not has_result or leg["answer_status"] != "ok"
            or close["phase"] != "observed" or not close["outcome"]["closed"]
            or ledger != {"phase": "complete", "ack": True} or leg["reason"] is not None):
        raise ValueError("fabric_e3_completion_invalid")
    if leg["phase"] == "held":
        binding_held = (leg["reason"] == "fabric_binding_unavailable"
            and all(leg[k] is None for k in result_keys)
            and close == {"phase": "unavailable", "outcome": None}
            and ledger == {"phase": "unattempted", "ack": None})
        settled_held = (has_result and close["phase"] == "observed"
            and ledger["phase"] in {"complete", "unknown"})
        if not (binding_held or settled_held):
            raise ValueError("fabric_e3_hold_changed")
    if document != _fabric_e3_document(original):
        raise ValueError("fabric_e3_report_changed")
    return document


def _fabric_e3_save(path, original):
    cache, _, _ = _fabric_e3_owners()
    document = _fabric_e3_validate(_fabric_e3_document(original))
    cache._cache_save(path, document)
    return document


def _fabric_e3_update(root, before, change):
    import copy
    cache, _, _ = _fabric_e3_owners()
    path = root / EVAL_RECEIPT_PATH
    with cache._cache_lock(path, root):
        current = _fabric_e3_validate(cache._cache_read(path))
        if _fabric_e3_hash(current) != _fabric_e3_hash(before):
            raise ValueError("fabric_e3_original_changed")
        original = copy.deepcopy(current[_FABRIC_E3_KEY])
        change(original["qwen"])
        return _fabric_e3_save(path, original)


def _fabric_e3_new(root, mode, legacy):
    cache, transport, _ = _fabric_e3_owners()
    sha_check = verify_fixture_shas(root)
    live = verify_live_workspace_shas()
    if not live.get("available") or not live.get("source_shas_match"):
        raise RuntimeError("fabric_e3_live_source_unavailable")
    segments = load_transcript_segments(root)
    gold_text = (root / GOLD_PATH).read_text(encoding="utf-8")
    if hashlib.sha256(gold_text.encode("utf-8")).hexdigest() != FROZEN_GOLD_SHA:
        raise ValueError("fabric_e3_gold_changed")
    basis = [_FABRIC_E3_SCHEMA, EVENT_ID, FROZEN_TRANSCRIPT_SHA, FROZEN_GOLD_SHA,
             TAXONOMY_HASH, SYSTEM_PROMPT, _build_user_prompt(segments)]
    run_id = "e3a-fabric:" + _fabric_e3_hash(basis)[:24]
    frozen = {
        "run_id": run_id, "mode_id": mode,
        "bindings": eval_bindings(root, gold_sha=FROZEN_GOLD_SHA,
                                  taxonomy_hash=TAXONOMY_HASH, run_id=run_id),
        "sha_verification": {**sha_check, "live_workspace": live},
        "segments": segments, "gold_text": gold_text,
    }
    frozen["request"] = _fabric_e3_kwargs(frozen)
    rid, body = transport._request(frozen["request"], _FABRIC_QWEN_MODEL, False, exact_scoped=True)
    original = {
        "schema": "e3a.fabric_original.v1", "input": frozen, "input_digest": _fabric_e3_hash(frozen),
        "legacy_receipt": legacy, "legacy_digest": _fabric_e3_hash(legacy) if legacy is not None else None,
        "qwen": {
            "phase": "unattempted", "reason": "fabric_qualification_required",
            "operation_id": run_id + ":qwen", "request_id": rid,
            "request_digest": transport._auto_request_digest(json.loads(body)),
            "inspection": None, "answer": None, "answer_sha256": None, "answer_status": None,
            "observation": None, "actual_observation": None, "usage": None, "latency_ms": None,
            "close": {"phase": "unattempted", "outcome": None},
            "ledger": {"phase": "unattempted", "ack": None},
        },
        "comparator": {"phase": "unattempted", "requested_model": FROZEN_COMPARATOR_MODEL,
                       "operation_id": run_id + ":comparator",
                       "reason": "fabric_native_comparator_unqualified"},
    }
    return _fabric_e3_validate(_fabric_e3_document(original))


def _fabric_e3_publish(root, document):
    leg = document[_FABRIC_E3_KEY]["qwen"]
    if leg["phase"] != "closed" or leg["ledger"] != {"phase": "unattempted", "ack": None}:
        return document
    document = _fabric_e3_update(root, document,
        lambda q: q.update(ledger={"phase": "intent", "ack": None}))
    original = document[_FABRIC_E3_KEY]
    attempt = _fabric_e3_attempt(original)
    ack = ledger_attempt(attempt, root, original["input"]["run_id"],
                         fabric=True, fabric_observation=original["qwen"]["observation"]) is True
    def finish(q):
        q["ledger"] = {"phase": "complete" if ack else "unknown", "ack": ack}
        settled = q["close"]["outcome"] is not None and q["close"]["outcome"]["closed"]
        q["phase"] = "complete" if settled and ack and q["answer_status"] == "ok" else "held"
        if not ack:
            q["reason"] = "fabric_ledger_unknown"
        elif not settled:
            q["reason"] = "fabric_close_unknown"
        elif q["answer_status"] == "ok":
            q["reason"] = None
    return _fabric_e3_update(root, document, finish)


def _fabric_e3_execute(root, document):
    import copy
    cache, transport, auth = _fabric_e3_owners()
    from engine.provider_production_modes import make_application_fabric_factory
    original = document[_FABRIC_E3_KEY]
    leg, frozen = original["qwen"], original["input"]
    if leg["phase"] == "closed":
        return _fabric_e3_publish(root, document)
    if leg["phase"] != "unattempted":
        return document
    try:
        mode, _ = auth._application_mode({})
        if mode != frozen["mode_id"]:
            raise ValueError("fabric_e3_selector_changed")
        factory = make_application_fabric_factory(
            mode_id=mode, lane=LANE, root=root,
            workload_cfg={"provider_order": ["fabric"], "workload_profile": "site_batch"},
        ).with_requested_model(_FABRIC_QWEN_MODEL)
        inspection = factory.inspect()
    except Exception:
        if leg["reason"] == "fabric_qualification_unavailable":
            return document
        return _fabric_e3_update(root, document,
            lambda q: q.update(reason="fabric_qualification_unavailable"))
    document = _fabric_e3_update(root, document, lambda q: q.update(
        phase="claimed", reason="fabric_operation_claimed", inspection=inspection,
        close={"phase": "reserved", "outcome": None}))
    started = time.monotonic()
    try:
        provider = auth.build_fabric_provider(factory.with_inspection(inspection),
            request_id=leg["operation_id"],
            workload_cfg={"workload_profile": "site_batch", "usage_sink": "none"})
    except Exception:
        return _fabric_e3_update(root, document, lambda q: q.update(
            phase="held", reason="fabric_binding_unavailable",
            close={"phase": "unavailable", "outcome": None}))
    answer, answer_status, reason = None, "provider_unavailable", "fabric_operation_unavailable"
    observed, actual, usage = None, None, None
    try:
        try:
            kwargs = dict(frozen["request"])
            kwargs.pop("request_id")
            response = provider["client"].messages.create(**kwargs)
            content = getattr(response, "content", None)
            if not isinstance(content, (list, tuple)) or not content:
                raise ValueError("fabric_e3_response_incomplete")
            answer = "".join(b.text for b in content
                if getattr(b, "type", None) == "text" and isinstance(getattr(b, "text", None), str))
            if (getattr(response, "stop_reason", None) != "end_turn"
                    or any(getattr(b, "type", None) != "text"
                           or not isinstance(getattr(b, "text", None), str) for b in content)):
                raise ValueError("fabric_e3_response_incomplete")
            _fabric_e3_candidates(answer)
            answer_status, reason = "ok", None
        except Exception:
            if answer is not None:
                answer_status, reason = "invalid_response", "fabric_response_invalid"
        observation = auth.fabric_observation(provider)
        actual = copy.deepcopy(provider.get("_fabric_last_observation"))
        usage = auth.fabric_usage(provider)
        if observation is not None:
            observed = transport.validate_auto_observation(observation.document, inspection,
                operation_id=leg["operation_id"], request_id=leg["request_id"],
                request_digest=leg["request_digest"], routed_request_digest=None,
                max_tokens=EXTRACTION_MAX_TOKENS, require_success=answer_status == "ok")
        elif answer_status == "ok":
            answer_status, reason = "provider_unavailable", "fabric_observation_unavailable"
        if answer is not None:
            try:
                if len(answer.encode("utf-8")) > 1024 * 1024:
                    answer = None
            except UnicodeError:
                answer = None
            if answer is None:
                answer_status, reason = "invalid_response", "fabric_response_invalid"
        def observed_reply(q):
            q.update(phase="observed", reason=reason, answer=answer,
                     answer_sha256=hashlib.sha256(answer.encode("utf-8")).hexdigest()
                        if answer is not None else None,
                     answer_status=answer_status, observation=observed,
                     actual_observation=actual, usage=usage,
                     latency_ms=(time.monotonic() - started) * 1000,
                     close={"phase": "intent", "outcome": None})
        document = _fabric_e3_update(root, document, observed_reply)
    finally:
        # All post-bind work, including cancellation and persistence failure,
        # owns one close. Restoring this original never repeats that effect.
        auth.close_fabric_provider(provider)
    outcome = provider.get("_fabric_close")
    if outcome is None:
        outcome = {"disposition": "effect_unknown", "closed": False,
                   "effect_unknown": True, "attempted": True}
    document = _fabric_e3_update(root, document, lambda q: q.update(
        phase="closed", close={"phase": "observed", "outcome": outcome}))
    return _fabric_e3_publish(root, document)


def _fabric_e3_run(root):
    cache, _, auth = _fabric_e3_owners()
    path = root / EVAL_RECEIPT_PATH
    # Original lookup precedes current selectors, qualifications and credentials.
    current = cache._cache_read(path)
    if type(current) is dict and (current.get("schema") == _FABRIC_E3_SCHEMA
                                  or _FABRIC_E3_KEY in current):
        document = _fabric_e3_validate(current)
    else:
        mode, _ = auth._application_mode({})
        if mode is None:
            return None
        if current is not None and (type(current) is not dict
                                    or current.get("schema") != "e3a_eval_receipt.v1"):
            raise ValueError("fabric_e3_predecessor_invalid")
        prepared = _fabric_e3_new(root, mode, current)
        with cache._cache_lock(path, root):
            actual = cache._cache_read(path)
            if actual != current:
                if type(actual) is dict and actual.get("schema") == _FABRIC_E3_SCHEMA:
                    document = _fabric_e3_validate(actual)
                else:
                    raise ValueError("fabric_e3_predecessor_changed")
            else:
                cache._cache_save(path, prepared)
                document = prepared
    document = _fabric_e3_execute(root, document)
    return {**document, "receipt_sha256": _fabric_e3_hash(document)}


def _run_e3a_native_eval(repo_root: Path) -> dict:
    """Preserve the legacy evaluation while its receipt lock is owned."""
    run_id = hashlib.sha256(str(time.time_ns()).encode()).hexdigest()[:16]
    shard_info = _enable_eval_shards(run_id, repo_root)

    receipt: dict[str, Any] = {
        "schema": "e3a_eval_receipt.v1",
        "run_id": run_id,
        "lane": LANE,
        "event_id": EVENT_ID,
        "gold_path": str(GOLD_PATH),
        "telemetry": shard_info,
        "steps": {},
        "model_attempts": {},
        "scores": {},
        "summary": {},
    }

    sha_check = verify_fixture_shas(repo_root)
    live = verify_live_workspace_shas()
    if not live.get("available") or not live.get("source_shas_match"):
        raise RuntimeError(
            "Live E2 workspace source SHAs do not equal frozen fixture SHAs. "
            f"live={live}"
        )
    receipt["steps"]["sha_verification"] = {
        **sha_check,
        "frozen_exhibit_sha": FROZEN_EXHIBIT_SHA,
        "frozen_transcript_sha": FROZEN_TRANSCRIPT_SHA,
        "live_workspace": live,
    }

    segments = load_transcript_segments(repo_root)
    segment_ids = [
        stable_segment_id(FROZEN_TRANSCRIPT_SHA, i) for i in range(len(segments))
    ]
    receipt["steps"]["segmenter"] = {
        "segment_count": len(segments),
        "id_method": "sha256[:16]_index04d",
        "truncation": "none",
        "sample_ids": segment_ids[:3],
    }

    gold_bytes = (repo_root / GOLD_PATH).read_bytes()
    gold_sha = hashlib.sha256(gold_bytes).hexdigest()
    if gold_sha != FROZEN_GOLD_SHA:
        raise RuntimeError(f"Gold SHA changed unexpectedly: {gold_sha}")
    gold = json.loads(gold_bytes)
    taxonomy_hash = str(gold.get("taxonomy", {}).get("hash") or TAXONOMY_HASH)
    bindings = eval_bindings(
        repo_root,
        gold_sha=gold_sha,
        taxonomy_hash=taxonomy_hash,
        run_id=run_id,
    )
    receipt["bindings"] = bindings
    receipt.update(bindings)
    receipt["steps"]["gold_loaded"] = {
        "gold_path": str(GOLD_PATH),
        "gold_sha256": gold_sha,
        "gold_schema": gold.get("schema"),
        "superseded_gold_sha256_v1": SUPERSEDED_GOLD_SHA_V1,
        "taxonomy_version": gold.get("taxonomy", {}).get("version"),
        "taxonomy_hash": taxonomy_hash,
        "exchange_count": gold.get("qa_exchange_count"),
        "usefulness_bar_decision": gold.get("usefulness_bar", {}).get("decision"),
        "gold_labels_withheld_during_inference": True,
        "adjudication_receipt": str(ADJUDICATION_RECEIPT_PATH),
    }

    user_prompt = _build_user_prompt(segments)
    if "Amit Daryanani" in user_prompt and '"topics"' in json.dumps(gold["exchanges"][0]):
        # Prompt may contain source names (they are in the transcript). It must
        # not contain gold topic labels as an answer key.
        gold_note = str(gold["exchanges"][0].get("adjudication_notes") or "")
        if gold_note and gold_note in user_prompt:
            raise RuntimeError("gold adjudication notes leaked into the prompt")
    receipt["steps"]["prompt_built"] = {
        "prompt_version": "e3a-qa-extraction-v1",
        "segment_count": len(segments),
        "uses_bounded_transcript_text": False,
        "gold_labels_in_prompt": False,
    }

    print("[e3_shadow_compiler] Attempting Qwen via earnings-worker override...")
    qwen_attempt = _attempt_qwen(user_prompt, repo_root)
    receipt["model_attempts"]["qwen"] = {
        "provider": qwen_attempt.provider,
        "model": qwen_attempt.model,
        "endpoint_class": qwen_attempt.endpoint_class,
        "base_url_source": qwen_attempt.base_url_source,
        "preflight": qwen_attempt.preflight,
        "status": qwen_attempt.status,
        "degraded_reason": qwen_attempt.degraded_reason,
        "n_candidates": len(qwen_attempt.candidates),
        "raw_excerpt": (qwen_attempt.raw_response or "")[:400],
        "latency_ms": round(qwen_attempt.latency_ms, 1),
        "input_tokens": qwen_attempt.input_tokens,
        "output_tokens": qwen_attempt.output_tokens,
        "served_model": qwen_attempt.served_model,
        "http_status": qwen_attempt.http_status,
        "error_kind": qwen_attempt.error_kind,
        "observed_usage": qwen_attempt.observed_usage,
        "est_cost_usd": qwen_attempt.est_cost_usd,
        "cost_basis": (
            "local" if qwen_attempt.endpoint_class in {"loopback", "private_lan"}
            else ("unknown" if qwen_attempt.est_cost_usd is None else "metered")
        ),
        "transport": "openai_compat",
        "gold_labels_seen": False,
    }
    ledger_attempt(qwen_attempt, repo_root, run_id)

    print("[e3_shadow_compiler] Freezing comparator, then attempting llm_auth...")
    comp_choice = freeze_comparator_choice(repo_root, run_id=run_id)
    receipt["steps"]["comparator_freeze"] = {
        k: v for k, v in comp_choice["freeze"].items() if k != "providers"
    }
    comp_attempt = _attempt_comparator(user_prompt, repo_root, run_id=run_id)
    receipt["model_attempts"]["comparator"] = {
        "provider": comp_attempt.provider,
        "model": comp_attempt.model,
        "is_comparator": True,
        "non_authoritative": True,
        "comparator_note": comp_attempt.comparator_note,
        "preflight": comp_attempt.preflight,
        "status": comp_attempt.status,
        "degraded_reason": comp_attempt.degraded_reason,
        "n_candidates": len(comp_attempt.candidates),
        "raw_excerpt": (comp_attempt.raw_response or "")[:400],
        "latency_ms": round(comp_attempt.latency_ms, 1),
        "input_tokens": comp_attempt.input_tokens,
        "output_tokens": comp_attempt.output_tokens,
        "est_cost_usd": comp_attempt.est_cost_usd,
        "gold_labels_seen": False,
    }
    if comp_attempt.status != "ok":
        ledger_attempt(comp_attempt, repo_root, run_id)

    print("[e3_shadow_compiler] Scoring against frozen gold via shadow validator...")
    qwen_score = score_attempt(qwen_attempt, gold, segments)
    comp_score = score_attempt(comp_attempt, gold, segments)
    receipt["scores"]["qwen"] = qwen_score
    receipt["scores"]["comparator"] = comp_score

    receipt["summary"] = {
        "sha_check": "pass",
        "live_workspace_verified": True,
        "gold_sha256": gold_sha,
        "gold_frozen_before_inference": True,
        "neither_model_saw_gold_labels": True,
        "qwen_status": qwen_attempt.status,
        "comparator_status": comp_attempt.status,
        "hard_gates_qwen": qwen_score["hard_gates"]["status"],
        "hard_gates_comparator": comp_score["hard_gates"]["status"],
        "usefulness_bar_decision": "refusal_n7_too_small",
        "return_to_sol": True,
        "e3b_auto_unlocked": False,
        "event_workspace_v1_advanced": False,
        "r2_written": False,
        "note": (
            "Measured E3-A R2 packet. Gold v2 re-frozen for answer-turn "
            "respondents[] before this inference. Pre-inference usefulness "
            "decision remains the frozen N=7 refusal, so this returns to Sol "
            "regardless of scores. Full-transcript Qwen is not promoted. "
            "Haiku is benchmark-only. E3-B stays locked."
        ),
    }
    receipt["telemetry_proof"] = _bounded_telemetry_proof(repo_root, shard_info)

    receipt_path = repo_root / EVAL_RECEIPT_PATH
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_bytes = json.dumps(receipt, indent=2, default=str).encode("utf-8")
    receipt_path.write_bytes(receipt_bytes)
    receipt["receipt_sha256"] = hashlib.sha256(receipt_bytes).hexdigest()
    print(f"[e3_shadow_compiler] Eval receipt written: {receipt_path}")
    return receipt

def run_e3a_eval(repo_root: Path | None = None) -> dict:
    """Execute the original E3 evaluation through its selected receipt owner."""
    if repo_root is None:
        repo_root = Path(__file__).parent.parent.parent
    root = Path(repo_root).resolve()
    selected = _fabric_e3_run(root)
    if selected is not None:
        return selected
    cache, _, auth = _fabric_e3_owners()
    # The existing receipt lock also fences a legacy evaluation before inference.
    # A selected original cannot overtake a native evaluation already in progress.
    receipt_path = root / EVAL_RECEIPT_PATH
    lock_root = root if receipt_path.is_relative_to(root) else receipt_path.parent
    with cache._cache_lock(receipt_path, lock_root):
        current = cache._cache_read(receipt_path)
        selected_original = type(current) is dict and (
            current.get("schema") == _FABRIC_E3_SCHEMA or _FABRIC_E3_KEY in current)
        mode, _ = auth._application_mode({})
        if not selected_original and mode is None:
            return _run_e3a_native_eval(root)
    return _fabric_e3_run(root)


if __name__ == "__main__":
    run_e3a_eval()

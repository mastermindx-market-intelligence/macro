"""Source-qualified later NBBO labels for an immutable private R0 feature.

The feature and its original TP-1 quote generation stay frozen. Later quote,
policy and source-health evidence can qualify a horizon-bound observation,
never repair the original decision or confer signal/publication authority.
This adapter reuses TP-1 quote admission and the existing R0 maturity engine;
it neither signs trades nor implements another endpoint selector.

`source_evidence` is an explicit, receipt-bound owner assertion, not a new
source-owner service or proof that capture actually occurred. Its exact
fields bind the feature, combined normalized quote generation and canonical
endpoint minute. Its available_ns is the normalized-generation wrapper receipt;
health_available_ns is the underlying source-health receipt. Original evidence
separately binds a receipt-time snapshot at T, its verdict digest, and the
original event watermark through feature.end. Original health is the latest
status received by T, independently of receipt-snapshot continuity. No event-
time health completeness through T or invented status-age policy is claimed.
Its wrapper may be created later. The later Q fingerprint excludes full typed-verdict metadata; that metadata has
its own label digest and availability clock. External custody/completeness proof
remains outstanding, including the original frozen verdict fingerprint receipt.
"""

from __future__ import annotations

from hashlib import sha256
import json

from engine.market_microstructure.matured_response import measure_matured_response
from engine.market_microstructure.private_context_view import (
    verify_private_research_context_bytes,
)
from engine.market_microstructure.tp1_context import (
    MAX_QUOTES, MINUTE_NS, TP1_MINUTE_SCHEMA, TP1ContextRefusal,
    _QuoteQualificationRefusal, _normalize_tp1_quotes, _tp1_quote_digest,
    _id, _int, _sha,
)

SCHEMA = "equity.pressure_response.tp1_matured_label/v0"
SOURCE_EVIDENCE_SCHEMA = "equity.pressure_response.tp1_label_source_evidence/v0"
ORIGINAL_EVIDENCE_SCHEMA = "equity.pressure_response.tp1_original_source_evidence/v0"
_ORIGINAL_EVIDENCE_KEYS = frozenset({
    "schema", "authority", "ticker", "session", "feature_sha256",
    "source_manifest_sha256", "quote_observations_sha256",
    "quote_condition_receipts_sha256", "quote_condition_receipts_frozen_ns",
    "quote_condition_receipts_receipt", "coverage_clock", "snapshot_cutoff_ns",
    "health_available_ns", "health_basis", "source_watermark_receipt", "source_complete_through_ns",
    "watermark_available_ns", "coverage_start_ns", "coverage_end_ns",
    "available_ns", "receipt_id", "market_health", "gap_state",
    "source_completeness_attested", "original_reference_custody_attested",
})
HORIZONS_NS = frozenset({30_000_000_000, 120_000_000_000, 300_000_000_000})
_SOURCE_EVIDENCE_KEYS = frozenset({
    "schema", "authority", "ticker", "session", "feature_sha256",
    "source_manifest_sha256", "quote_observations_sha256",
    "endpoint_minute_sha256", "source_watermark_receipt",
    "coverage_start_ns", "coverage_end_ns", "available_ns", "receipt_id",
    "health_available_ns", "market_health", "gap_state", "source_completeness_attested",
    "original_reference_custody_attested",
})
_EXCHANGE_KEYS = frozenset({
    "schema", "reference_available_ns", "original_reference_receipt",
    "source_request_id", "reference_sha256", "source_types",
    "source_vintage", "authority",
})
_POLICY_KEYS = frozenset({
    "schema", "policy_sha256", "policy_received_ns", "policy_receipt_id",
    "source_reference_sha256", "reviewer_receipt", "allowed_quote_conditions",
    "allowed_nbbo_indicators", "unknown_action", "authority",
})


class _LabelAbstention(Exception):
    def __init__(self, reason, state="SOURCE_NOT_QUALIFIED"):
        self.reason, self.state = reason, state


def _require(condition, reason, state="SOURCE_NOT_QUALIFIED"):
    if not condition:
        raise _LabelAbstention(reason, state)


def _clock(value, field, cutoff):
    _require(type(value) is int and value >= 0,
             "MISSING_OR_INVALID_" + field.upper())
    _require(value <= cutoff, field.upper() + "_NOT_AVAILABLE_AT_CUTOFF")
    return value


def _digest(value):
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True, allow_nan=False).encode()
    except (TypeError, ValueError) as exc:
        raise TP1ContextRefusal("source evidence is not canonical JSON data") from exc
    return sha256(raw).hexdigest()


def _original_source(evidence, feature, feature_digest, original_cutoff, cutoff, max_age):
    _require(isinstance(evidence, dict) and set(evidence) == _ORIGINAL_EVIDENCE_KEYS,
             "MISSING_FROZEN_ORIGINAL_SOURCE_EVIDENCE")
    _require(evidence["schema"] == ORIGINAL_EVIDENCE_SCHEMA
             and evidence["authority"] == "SOURCE_OWNER_ASSERTION_REQUIRES_EXTERNAL_PROOF",
             "ORIGINAL_SOURCE_AUTHORITY_UNQUALIFIED")
    receipt = _id(evidence["source_watermark_receipt"], "original watermark receipt")
    _require(evidence["ticker"] == feature["ticker"] and evidence["session"] == feature["session"]
             and evidence["feature_sha256"] == feature_digest
             and evidence["source_manifest_sha256"] == feature["source_manifest_sha256"]
             and evidence["quote_observations_sha256"] == feature["quote_observations_sha256"]
             and sha256(receipt.encode()).hexdigest() == feature["source_watermark_receipt_sha256"],
             "ORIGINAL_SOURCE_GENERATION_MISMATCH")
    # SIP-event maturity and the receipt-snapshot boundary are different clocks.
    # A watermark can lag T while the frozen capture contains exactly the Q and
    # verdict receipts available by T. No event completeness through T is claimed.
    _require(evidence["coverage_clock"] == "ORIGINAL_FRAME_RECEIPT"
             and evidence["snapshot_cutoff_ns"] == original_cutoff,
             "ORIGINAL_RECEIPT_SNAPSHOT_BOUNDARY_MISMATCH")
    available = _clock(evidence["available_ns"], "original_source_evidence_available_ns", cutoff)
    complete = _clock(evidence["source_complete_through_ns"], "original_source_complete_ns", original_cutoff)
    watermark = _clock(evidence["watermark_available_ns"], "original_watermark_available_ns", original_cutoff)
    _require(evidence["health_basis"] == "LATEST_STATUS_AS_SEEN_AT_SNAPSHOT",
             "ORIGINAL_HEALTH_BASIS_UNQUALIFIED")
    health = _clock(evidence["health_available_ns"], "original_health_available_ns", original_cutoff)
    start = _clock(evidence["coverage_start_ns"], "original_coverage_start_ns", original_cutoff)
    end = _clock(evidence["coverage_end_ns"], "original_coverage_end_ns", original_cutoff)
    _require(feature["end_ns"] <= complete <= watermark <= original_cutoff
             and start <= max(0, feature["start_ns"] - max_age) and end == original_cutoff,
             "ORIGINAL_SOURCE_DOES_NOT_QUALIFY_DECISION_ANCHOR")
    # The immutable wrapper may be serialized later. Its timestamp must not be
    # mistaken for the original snapshot cutoff or an original emission claim.
    _require(available >= max(original_cutoff, watermark, health),
             "ORIGINAL_EVIDENCE_WRAPPER_PRECEDES_BOUND_RECEIPTS")
    _sha(evidence["quote_condition_receipts_sha256"], "original quote verdict generation")
    _clock(evidence["quote_condition_receipts_frozen_ns"], "original_verdict_fingerprint_available_ns", original_cutoff)
    _id(evidence["quote_condition_receipts_receipt"], "original verdict fingerprint receipt")
    _id(evidence["receipt_id"], "original source receipt")
    _require(evidence["source_completeness_attested"] is True
             and evidence["original_reference_custody_attested"] is True,
             "ORIGINAL_SOURCE_COMPLETENESS_OR_CUSTODY_UNATTESTED")
    _require(evidence["market_health"] == "NORMAL" and evidence["gap_state"] == "CONTIGUOUS",
             "ORIGINAL_SOURCE_HEALTH_UNQUALIFIED", "CENSORED")
    return available


def _source_references(exchange, policy, feature, original_cutoff):
    _require(isinstance(exchange, dict) and set(exchange) == _EXCHANGE_KEYS,
             "MISSING_CANONICAL_EXCHANGE_REFERENCE")
    _require(exchange["schema"] == "equity.tick_plane.exchange_reference/v0"
             and exchange["authority"] == "SOURCE_REFERENCE_ONLY"
             and exchange["source_vintage"] == "AS_RECEIVED_NOT_RETROACTIVE",
             "EXCHANGE_REFERENCE_AUTHORITY_UNQUALIFIED")
    _require(_sha(exchange["reference_sha256"], "exchange reference")
             == feature["source_exchange_rules_sha256"],
             "FEATURE_AND_LABEL_EXCHANGE_GENERATION_DISAGREE")
    exchange_time = _clock(exchange["reference_available_ns"],
                           "exchange_reference_available_ns", original_cutoff)
    _id(exchange["original_reference_receipt"], "exchange receipt")
    _id(exchange["source_request_id"], "exchange source request")
    codes = exchange["source_types"]
    _require(isinstance(codes, dict) and 0 < len(codes) <= 512
             and all(type(k) is int and k >= 0 and v in ("exchange", "SIP", "TRF")
                     for k, v in codes.items()), "INVALID_EXCHANGE_REFERENCE_CODES")
    _require(isinstance(policy, dict) and set(policy) == _POLICY_KEYS,
             "MISSING_CANONICAL_QUOTE_POLICY")
    _require(policy["schema"] == "equity.tick_plane.quote_condition_policy/v0"
             and policy["authority"] == "SOURCE_POLICY_CANDIDATE_REQUIRES_CUSTODY"
             and policy["unknown_action"] == "ABSTAIN",
             "QUOTE_POLICY_AUTHORITY_UNQUALIFIED")
    _require(_sha(policy["policy_sha256"], "quote policy")
             == feature["source_quote_condition_rules_sha256"],
             "FEATURE_AND_LABEL_QUOTE_POLICY_DISAGREE")
    _sha(policy["source_reference_sha256"], "quote condition reference")
    policy_time = _clock(policy["policy_received_ns"],
                         "quote_policy_available_ns", original_cutoff)
    for key in ("policy_receipt_id", "reviewer_receipt"):
        _id(policy[key], key)
    # Consume the canonical policy receipt, never reevaluate or re-sign its
    # per-quote verdict. Shape/bounds are checked without a second allowlist.
    for key in ("allowed_quote_conditions", "allowed_nbbo_indicators"):
        values = policy[key]
        _require(isinstance(values, (tuple, list)) and 0 < len(values) <= 8
                 and all(type(v) is int and v >= 0 for v in values)
                 and len(set(values)) == len(values), "INVALID_QUOTE_POLICY_SHAPE")
    return max(exchange_time, policy_time)


def _admit_generation(*, quotes, receipts, feature, cutoff, original,
                       policy, exchange, sequence_ids):
    _require(isinstance(quotes, (list, tuple)) and len(quotes) <= MAX_QUOTES,
             "UNBOUNDED_SOURCE_QUOTE_GENERATION")
    _require(isinstance(receipts, dict) and len(receipts) <= MAX_QUOTES,
             "UNBOUNDED_QUOTE_VERDICT_GENERATION")
    kept, clocks, raw_clocks = [], [], []
    for q in quotes:
        _require(isinstance(q, dict), "INVALID_CANONICAL_QUOTE")
        seen = q.get("original_frame_received_ns")
        # A later archive entry is not evidence at this label cutoff.
        _require(type(seen) is int and seen >= 0, "MISSING_OR_INVALID_QUOTE_AVAILABLE_NS")
        if seen > cutoff and not original:
            continue
        _clock(seen, "quote_available_ns", cutoff)
        _require(original or seen > feature["decision_ns"],
                 "LATER_GENERATION_WOULD_REWRITE_ORIGINAL_SNAPSHOT")
        stamp = _clock(q.get("sip_timestamp_ns"), "quote_sip_ns", seen)
        _require(q.get("source_timestamp_precision") == "MILLISECONDS"
                 and stamp % 1_000_000 == 0, "UNQUALIFIED_NATIVE_QUOTE_CLOCK")
        _require(q.get("correction_status") == "STREAM_PROVISIONAL_UNRECONCILED"
                 and q.get("source_status") == "RECEIPT_UNQUALIFIED_UNTIL_OWNER_ATTESTS",
                 "QUOTE_CORRECTION_OR_SOURCE_VINTAGE_UNQUALIFIED")
        seq = _int(q.get("native_sequence"), "quote.native_sequence")
        _require(seq not in sequence_ids, "CONFLICTING_NATIVE_QUOTE_SEQUENCE")
        sequence_ids.add(seq)
        expected_id = f'{feature["session"]}:{feature["ticker"]}:Q:{seq}:{stamp}'
        _require(q.get("quote_id") == expected_id, "NATIVE_QUOTE_IDENTITY_MISMATCH")
        _require(type(q.get("valid_firm_nbbo")) is bool
                 and type(q.get("bid_size")) is int and q["bid_size"] >= 0
                 and type(q.get("ask_size")) is int and q["ask_size"] >= 0
                 and all(q.get(side) is None or (isinstance(q[side], str) and len(q[side]) <= 100)
                         for side in ("bid", "ask"))
                 and isinstance(q.get("quote_indicators"), list)
                 and len(q["quote_indicators"]) <= 32
                 and all(type(v) is int and v >= 0 for v in q["quote_indicators"]),
                 "INVALID_NATIVE_QUOTE_SHAPE")
        verdict = receipts.get(q["quote_id"])
        _require(isinstance(verdict, dict), "MISSING_TYPED_QUOTE_VERDICT")
        verdict_time = _clock(verdict.get("decision_ns"), "quote_verdict_available_ns", cutoff)
        policy_time = _clock(verdict.get("policy_available_ns"),
                             "quote_policy_available_ns", cutoff)
        _require(verdict.get("policy_rules_sha256") == policy["policy_sha256"]
                 and verdict.get("source_reference_sha256") == policy["source_reference_sha256"]
                 and policy_time == policy["policy_received_ns"],
                 "QUOTE_VERDICT_POLICY_GENERATION_MISMATCH")
        # Unknown/nonfirm updates remain in the shared admission chain. A firm
        # price additionally needs both native quote venues in the frozen stock
        # exchange reference; a numeric venue ID by itself is insufficient.
        if q["valid_firm_nbbo"] and verdict.get("eligible") is True:
            _require(all(type(q.get(side)) is int
                         and exchange["source_types"].get(q[side]) == "exchange"
                         for side in ("bid_exchange", "ask_exchange")),
                     "QUOTE_VENUE_UNQUALIFIED")
        kept.append(q)
        clocks.extend((seen, verdict_time, policy_time))
        raw_clocks.append(seen)
    normalized, refs, _ = _normalize_tp1_quotes(
        ticker=feature["ticker"], session=feature["session"],
        decision_ns=cutoff, source_quotes=kept,
        quote_condition_receipts=receipts, allow_empty=not original,
    )
    _require(not refs or refs == {feature["source_quote_condition_rules_sha256"]},
             "FEATURE_AND_LABEL_QUOTE_POLICY_DISAGREE")
    return (normalized, max(clocks, default=0), max(raw_clocks, default=0),
            {q["quote_id"]: receipts[q["quote_id"]] for q in kept})


def _endpoint_maturity(minute, feature, label_end, cutoff):
    _require(isinstance(minute, dict) and len(minute) <= 100
             and all(isinstance(k, str) and len(k) <= 100
                     and (v is None or type(v) in (bool, int)
                          or (isinstance(v, str) and len(v) <= 300)
                          or (isinstance(v, dict) and len(v) <= 64
                              and all(isinstance(x, str) and len(x) <= 100
                                      and type(y) is int and y >= 0 for x, y in v.items())))
                     for k, v in minute.items()), "UNBOUNDED_ENDPOINT_MINUTE")
    _require(isinstance(minute, dict) and minute.get("schema") == TP1_MINUTE_SCHEMA,
             "MISSING_CANONICAL_ENDPOINT_MINUTE")
    _require(minute.get("ticker") == feature["ticker"]
             and minute.get("session") == feature["session"],
             "ENDPOINT_SOURCE_IDENTITY_MISMATCH")
    _require(minute.get("authority") == "OBSERVATIONAL_PROVISIONAL_ONLY"
             and minute.get("correction_status") == "STREAM_PROVISIONAL_UNRECONCILED"
             and minute.get("source_mode") == "ACTUAL_AS_SEEN_ONLY_WHEN_OWNER_PROVES_RECEIPTS"
             and minute.get("rank_or_trade_authority") is False
             and minute.get("absorption_signal") is None
             and minute.get("forward_response_label") is None
             and minute.get("forward_return_label") is None
             and minute.get("price_response_label") is None
             and minute.get("market_capture_coverage") is None,
             "ENDPOINT_SOURCE_AUTHORITY_UNQUALIFIED")
    start = _clock(minute.get("start_ns"), "endpoint_minute_start_ns", cutoff)
    end = _clock(minute.get("end_ns"), "endpoint_minute_end_ns", cutoff)
    _require(start % MINUTE_NS == 0 and end == start + MINUTE_NS
             and start < label_end <= end, "ENDPOINT_MINUTE_DOES_NOT_COVER_HORIZON")
    decision = _clock(minute.get("decision_ns"), "endpoint_minute_available_ns", cutoff)
    complete = _clock(minute.get("source_complete_through_ns"), "source_complete_through_ns", cutoff)
    watermark = _clock(minute.get("watermark_available_ns"), "watermark_available_ns", cutoff)
    _require(end <= complete <= watermark <= decision,
             "ENDPOINT_MINUTE_WATERMARK_NOT_MATURE", "NOT_MATURE")
    _id(minute.get("source_watermark_receipt"), "endpoint watermark receipt")
    if minute.get("state") == "NO_SAMPLED_PRINTS":
        _require(minute.get("n_sampled_prints") == 0
                 and type(minute.get("n_sampled_prints")) is int
                 and minute.get("reason") == "NO_OBSERVED_ROWS_IS_NOT_PROOF_OF_ZERO_MARKET_VOLUME",
                 "INVALID_QUOTE_ONLY_MINUTE")
        # A mature quote-only minute supports quote context, never zero volume.
    else:
        _require(minute.get("state") == "PROVISIONAL_MEASURED_CONTEXT",
                 "ENDPOINT_MINUTE_NOT_QUALIFIED")
        _clock(minute.get("original_latest_available_ns"), "endpoint_observations_available_ns", decision)
        for key, frozen in (
            ("condition_rules_ref", "source_condition_rules_sha256"),
            ("exchange_reference_sha256", "source_exchange_rules_sha256"),
            ("quote_condition_rules_sha256", "source_quote_condition_rules_sha256"),
        ):
            _require(minute.get(key) == feature[frozen],
                     "ENDPOINT_MINUTE_REFERENCE_GENERATION_MISMATCH")
        _sha(minute.get("source_observation_sha256"), "endpoint source observations")
    return decision


def project_tp1_matured_response(
    *, feature_blob, feature_sha256, feature_byte_length,
    feature_available_ns, feature_availability_receipt,
    horizon_ns, evaluation_cutoff_ns, max_quote_age_ns,
    original_source_quotes, original_quote_condition_receipts,
    later_source_quotes, later_quote_condition_receipts,
    exchange_reference, quote_policy, endpoint_minute,
    original_source_evidence, source_evidence,
):
    """Label one frozen feature using separately knowable original evidence.

    Horizons are the predeclared R0 30 s / 2 min / 5 min observations. The
    returned specification digest freezes horizon, evaluation cutoff and age
    policy for this record; it is not evidence of preregistration or emission.
    Feature byte integrity failures raise the existing private verifier error.
    Missing, future or unqualified material evidence returns a typed abstention.
    """
    feature = verify_private_research_context_bytes(
        expected_sha256=feature_sha256, expected_byte_length=feature_byte_length,
        blob=feature_blob,
    )
    for key, value in (("horizon_ns", horizon_ns), ("evaluation_cutoff_ns", evaluation_cutoff_ns),
                       ("max_quote_age_ns", max_quote_age_ns)):
        _int(value, key)
    if horizon_ns not in HORIZONS_NS or not 0 < max_quote_age_ns <= feature["source_quote_age_limit_ns"]:
        raise TP1ContextRefusal("unsupported horizon or weaker frozen quote-age policy")
    original_cutoff = feature["decision_ns"]
    label_end = original_cutoff + horizon_ns
    specification = {
        "feature_sha256": feature_sha256, "horizon_ns": horizon_ns,
        "evaluation_cutoff_ns": evaluation_cutoff_ns, "max_quote_age_ns": max_quote_age_ns,
    }
    head = {
        "schema": SCHEMA, "authority": "RESEARCH_OUTCOME_LABEL_ONLY",
        "ticker": feature["ticker"], "session": feature["session"],
        "feature_sha256": feature_sha256, "feature_byte_length": feature_byte_length,
        "original_decision_ns": original_cutoff, "anchor_ns": original_cutoff,
        "label_end_ns": label_end, **specification,
        "label_specification_sha256": _digest(specification),
        "correction_status": "STREAM_PROVISIONAL_UNRECONCILED",
        "source_mode": "AS_SEEN_REQUIRES_ORIGINAL_OWNER_PROOF",
        "source_authenticity": "ORIGINAL_TQ_RECEIPTS_REQUIRE_EXTERNAL_OWNER_PROOF",
        "distribution_class": "PRIVATE_SERVICE_HOLD_PENDING_LICENSE_REVIEW",
        "public_delivery_allowed": False, "rank_trade_alert_authority": False,
        "forward_label_not_available_to_original_decision": True,
        "signal": None, "absorption_signal": None, "alpha_signal": None,
        "promotion_authority": False, "trade_fill": None,
        "execution_adjusted_return": None, "market_capture_completeness": None,
        "midpoint_response_bps": None, "label_first_knowable_ns": None,
        "label_knowability_basis": "EARLIEST_FROM_SUPPLIED_EVIDENCE_NOT_ACTUAL_EMISSION",
    }
    try:
        _require(evaluation_cutoff_ns >= label_end, "FUTURE_HORIZON_NOT_MATURE", "NOT_MATURE")
        feature_time = _clock(feature_available_ns, "feature_available_ns", evaluation_cutoff_ns)
        _require(feature_time >= original_cutoff, "FEATURE_RECEIPT_PRECEDES_ORIGINAL_DECISION")
        _id(feature_availability_receipt, "feature availability receipt")
        original_source_time = _original_source(
            original_source_evidence, feature, feature_sha256, original_cutoff,
            evaluation_cutoff_ns, max_quote_age_ns,
        )
        reference_time = _source_references(exchange_reference, quote_policy, feature, original_cutoff)
        _require(isinstance(original_source_quotes, (tuple, list))
                 and isinstance(later_source_quotes, (tuple, list))
                 and len(original_source_quotes) + len(later_source_quotes) <= MAX_QUOTES,
                 "UNBOUNDED_COMBINED_QUOTE_GENERATION")
        sequence_ids = set()
        original, original_time, original_raw_time, original_verdicts = _admit_generation(
            quotes=original_source_quotes, receipts=original_quote_condition_receipts,
            feature=feature, cutoff=original_cutoff, original=True,
            policy=quote_policy, exchange=exchange_reference, sequence_ids=sequence_ids,
        )
        _require(_tp1_quote_digest(original) == feature["quote_observations_sha256"]
                 and len(original) == feature["n_observations"]["n_quote_updates"],
                 "ORIGINAL_FEATURE_QUOTE_GENERATION_MISMATCH")
        _require(_digest(original_verdicts) == original_source_evidence["quote_condition_receipts_sha256"],
                 "FROZEN_ORIGINAL_QUOTE_VERDICT_GENERATION_MISMATCH")
        _require(original_source_time >= max(original_time, reference_time),
                 "ORIGINAL_EVIDENCE_WRAPPER_PRECEDES_BOUND_RECEIPTS")
        _require(original_source_evidence["quote_condition_receipts_frozen_ns"] >= original_time,
                 "ORIGINAL_VERDICT_FINGERPRINT_PRECEDES_GENERATION")
        later, later_time, later_raw_time, later_verdicts = _admit_generation(
            quotes=later_source_quotes, receipts=later_quote_condition_receipts,
            feature=feature, cutoff=evaluation_cutoff_ns, original=False,
            policy=quote_policy, exchange=exchange_reference, sequence_ids=sequence_ids,
        )
        combined = sorted(original + later, key=lambda q: (q["sip_ns"], q["id"]))
        combined_digest = _tp1_quote_digest(combined)
        minute_time = _endpoint_maturity(endpoint_minute, feature, label_end, evaluation_cutoff_ns)
        _require(isinstance(source_evidence, dict) and set(source_evidence) == _SOURCE_EVIDENCE_KEYS,
                 "MISSING_TYPED_SOURCE_HEALTH_EVIDENCE")
        evidence = source_evidence
        _require(evidence["schema"] == SOURCE_EVIDENCE_SCHEMA
                 and evidence["authority"] == "SOURCE_OWNER_ASSERTION_REQUIRES_EXTERNAL_PROOF",
                 "SOURCE_HEALTH_AUTHORITY_UNQUALIFIED")
        _require(evidence["ticker"] == feature["ticker"] and evidence["session"] == feature["session"]
                 and evidence["feature_sha256"] == feature_sha256
                 and evidence["quote_observations_sha256"] == combined_digest
                 and evidence["endpoint_minute_sha256"] == _digest(endpoint_minute)
                 and evidence["source_watermark_receipt"] == endpoint_minute["source_watermark_receipt"],
                 "SOURCE_HEALTH_GENERATION_MISMATCH")
        _sha(evidence["source_manifest_sha256"], "label source manifest")
        _id(evidence["receipt_id"], "source health receipt")
        evidence_time = _clock(evidence["available_ns"], "source_evidence_available_ns", evaluation_cutoff_ns)
        health_time = _clock(evidence["health_available_ns"], "source_health_available_ns", evaluation_cutoff_ns)
        coverage_start = _clock(evidence["coverage_start_ns"], "source_coverage_start_ns", evidence_time)
        coverage_end = _clock(evidence["coverage_end_ns"], "source_coverage_end_ns", health_time)
        _require(coverage_start <= max(0, original_cutoff - max_quote_age_ns)
                 and coverage_end >= label_end,
                 "SOURCE_HEALTH_COVERAGE_OR_RECEIPT_INCOMPLETE")
        # This wrapper binds normalized Q content and the endpoint minute, not
        # the full later verdict metadata. It cannot fingerprint a future raw
        # Q receipt. A separately supplied delayed verdict contributes its own
        # first-knowable clock and separate digest after all evidence qualifies.
        _require(evidence_time >= max(minute_time, original_raw_time, later_raw_time, health_time),
                 "SOURCE_EVIDENCE_WRAPPER_PRECEDES_BOUND_GENERATION")
        _require(evidence["source_completeness_attested"] is True
                 and evidence["original_reference_custody_attested"] is True,
                 "ORIGINAL_SOURCE_COMPLETENESS_OR_CUSTODY_UNATTESTED")
        _require(evidence["gap_state"] == "CONTIGUOUS", "SOURCE_GAP_OR_UNKNOWN_CONTINUITY", "CENSORED")
        _require(evidence["market_health"] == "NORMAL", "HALT_OR_UNKNOWN_MARKET_STATUS", "CENSORED")
        result = measure_matured_response(
            ticker=feature["ticker"], session=feature["session"],
            original_decision_ns=original_cutoff, anchor_ns=original_cutoff,
            label_end_ns=label_end, evaluation_cutoff_ns=evaluation_cutoff_ns,
            source_watermark_ns=endpoint_minute["source_complete_through_ns"],
            watermark_received_ns=endpoint_minute["watermark_available_ns"],
            watermark_receipt=endpoint_minute["source_watermark_receipt"],
            source_manifest=evidence["source_manifest_sha256"],
            source_mode="ACTUAL_AS_SEEN", max_quote_age_ns=max_quote_age_ns,
            market_health=evidence["market_health"], market_health_receipt=evidence["receipt_id"],
            quotes=combined,
        )
        if result["state"] != "MATURED_EVALUATION_LABEL":
            return {**head, "state": result["state"], "reason": result["reason"]}
        clocks = {
            "feature": feature_time, "original_quotes_and_verdicts": original_time,
            "later_quotes_and_verdicts": later_time, "source_references": reference_time,
            "endpoint_minute_and_watermark": minute_time, "source_health": health_time,
            "source_generation_wrapper": evidence_time,
            "original_source_health_and_watermark": original_source_time,
            "original_verdict_fingerprint": original_source_evidence["quote_condition_receipts_frozen_ns"],
        }
        return {
            **head, "state": result["state"], "reason": None,
            "midpoint_response_bps": result["midpoint_response_bps"],
            "label_first_knowable_ns": max(clocks.values()),
            "first_knowable_components_ns": clocks,
            "anchor_quote_age_ns": result["anchor_quote_age_ns"],
            "label_quote_age_ns": result["label_quote_age_ns"],
            "source_manifest_sha256": evidence["source_manifest_sha256"],
            "original_quote_observations_sha256": feature["quote_observations_sha256"],
            "later_quote_observations_sha256": _tp1_quote_digest(later),
            "combined_quote_observations_sha256": combined_digest,
            "original_quote_verdicts_sha256": _digest(original_verdicts),
            "later_quote_verdicts_sha256": _digest(later_verdicts),
            "source_exchange_reference_sha256": exchange_reference["reference_sha256"],
            "source_quote_policy_sha256": quote_policy["policy_sha256"],
            "source_quote_condition_reference_sha256": quote_policy["source_reference_sha256"],
            "endpoint_minute_sha256": _digest(endpoint_minute),
            "source_health_evidence_sha256": _digest(evidence),
            "original_source_evidence_sha256": _digest(original_source_evidence),
            "original_snapshot_clock": "ORIGINAL_FRAME_RECEIPT",
            "original_snapshot_cutoff_ns": original_cutoff,
            "original_health_basis": original_source_evidence["health_basis"],
            "original_health_available_ns": original_source_evidence["health_available_ns"],
            "original_health_age_at_snapshot_ns": original_cutoff - original_source_evidence["health_available_ns"],
            "original_event_complete_through_ns": original_source_evidence["source_complete_through_ns"],
            "original_event_watermark_lag_ns": original_cutoff - original_source_evidence["source_complete_through_ns"],
            "original_watermark_receipt_lag_ns": original_source_evidence["watermark_available_ns"] - original_source_evidence["source_complete_through_ns"],
            "feature_availability_receipt_sha256": sha256(feature_availability_receipt.encode()).hexdigest(),
            "endpoint_minute_state": endpoint_minute["state"],
            "sampled_trade_volume_inferred": None,
        }
    except _LabelAbstention as exc:
        return {**head, "state": exc.state, "reason": exc.reason}
    except _QuoteQualificationRefusal as exc:
        return {**head, "state": "QUOTE_REFERENCE_UNQUALIFIED", "reason": str(exc)}

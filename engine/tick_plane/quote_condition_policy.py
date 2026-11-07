"""Source-reviewed NBBO quote-condition policy for the canonical TP-1 source.

This is a pure parser/evaluator, NOT a quote feed, a new policy authority, or
proof of original vendor/source possession. A source owner must separately
review and attest the policy from the actual condition and NBBO-indicator
references before any observed quote is considered eligible.

See Massive /v3/reference/conditions and conditions-indicators glossary.
Only regular 0 / regular-two-sided 1 conditions and NBBO indicators 602,
604, 605 can ever enter this conservative first pilot. No condition,
unknown indicator, non-firm, crossed, closed, and SIP-generated codes abstain.
"""

from __future__ import annotations

import hashlib
import json
from engine.tick_plane.stream_events import (
    SCHEMA as QUOTE_SCHEMA, FrameContractError, _integer, _text,
)

POLICY_SCHEMA = "equity.tick_plane.quote_condition_policy/v0"
VERDICT_SCHEMA = "equity.tick_plane.quote_condition_admission/v0"
MAX_POLICY_BYTES = 16 * 1024
# Conservatively bounded known regular quote markers; no default permit.
_FIRM_CONDITIONS = frozenset({0, 1})
_NBBO_INDICATORS = frozenset({602, 604, 605})


def parse_quote_policy(*, original_policy_bytes, policy_received_ns,
                       policy_receipt_id):
    """Parse a receipt-bound, independently approved source-versioned policy."""
    _integer(policy_received_ns, "policy_received_ns", minimum=1)
    _text(policy_receipt_id, "policy_receipt_id")
    if (type(original_policy_bytes) is not bytes
            or not 0 < len(original_policy_bytes) <= MAX_POLICY_BYTES):
        raise FrameContractError("source quote condition policy missing or oversized")
    try:
        raw=json.loads(original_policy_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise FrameContractError("invalid quote policy JSON") from exc
    if (not isinstance(raw,dict)
            or raw.get("schema") != POLICY_SCHEMA
            or not isinstance(raw.get("source_reference_sha256"), str)
            or len(raw["source_reference_sha256"]) != 64
            or not isinstance(raw.get("reviewer_receipt"), str)
            or not raw["reviewer_receipt"].strip()
            or raw.get("unknown_action") != "ABSTAIN"):
        raise FrameContractError("quote policy lacks source or independent review provenance")
    for key in ("allowed_quote_conditions", "allowed_nbbo_indicators"):
        val=raw.get(key)
        if not isinstance(val,list) or not val or len(val)>8 or any(type(x) is not int for x in val):
            raise FrameContractError("invalid source quote condition allowlist")
        if len(set(val)) != len(val):
            raise FrameContractError("duplicate source quote condition code")
    conditions=frozenset(raw["allowed_quote_conditions"])
    indicators=frozenset(raw["allowed_nbbo_indicators"])
    if not conditions <= _FIRM_CONDITIONS or not indicators <= _NBBO_INDICATORS:
        raise FrameContractError("unreviewed non-firm or non-NBBO quote code")
    return {
        "schema":POLICY_SCHEMA, "policy_sha256":hashlib.sha256(original_policy_bytes).hexdigest(),
        "policy_received_ns":policy_received_ns,"policy_receipt_id":policy_receipt_id,
        "source_reference_sha256":raw["source_reference_sha256"],
        "reviewer_receipt":raw["reviewer_receipt"],
        "allowed_quote_conditions":tuple(sorted(conditions)),
        "allowed_nbbo_indicators":tuple(sorted(indicators)),
        "unknown_action":"ABSTAIN",
        "authority":"SOURCE_POLICY_CANDIDATE_REQUIRES_CUSTODY",
    }


def evaluate_quote_condition(*, quote, policy, decision_ns,
                             original_policy_custody_attested):
    """Return typed, quote-exact receipt. Unknowns never become firm evidence."""
    qid=quote.get("quote_id") if isinstance(quote,dict) else None
    sha=quote.get("source_frame_sha256") if isinstance(quote,dict) else None
    stamp=quote.get("original_frame_received_ns") if isinstance(quote,dict) else None
    def result(eligible, reason):
        return {
            "schema":VERDICT_SCHEMA,"eligible":eligible,"reason":reason,
            "quote_id":qid,"source_frame_sha256":sha,
            "original_frame_received_ns":stamp,
            "quote_condition":quote.get("quote_condition") if isinstance(quote,dict) else None,
            "quote_indicators":quote.get("quote_indicators") if isinstance(quote,dict) else None,
            "decision_ns":decision_ns,
            "policy_available_ns":policy.get("policy_received_ns") if isinstance(policy,dict) else None,
            "policy_rules_sha256":policy.get("policy_sha256") if isinstance(policy,dict) else None,
            "source_reference_sha256":policy.get("source_reference_sha256") if isinstance(policy,dict) else None,
            "authority":"ORIGINAL_QUOTE_POLICY_CONTEXT_ONLY",
        }
    if (not isinstance(quote,dict)
            or quote.get("schema")!=QUOTE_SCHEMA or quote.get("event_type")!="Q"
            or not isinstance(qid,str) or not qid.strip()
            or not isinstance(sha,str) or len(sha)!=64):
        return result(None,"UNQUALIFIED_QUOTE_IDENTITY")
    if (not isinstance(policy,dict) or policy.get("schema")!=POLICY_SCHEMA
            or policy.get("authority")!="SOURCE_POLICY_CANDIDATE_REQUIRES_CUSTODY"
            or not isinstance(policy.get("policy_sha256"),str) or len(policy["policy_sha256"])!=64):
        return result(None,"MISSING_SOURCE_REVIEWED_QUOTE_POLICY")
    if original_policy_custody_attested is not True:
        return result(None,"ORIGINAL_POLICY_CUSTODY_NOT_ATTESTED")
    if (type(decision_ns) is not int or type(stamp) is not int
            or type(policy.get("policy_received_ns")) is not int
            or decision_ns<0 or stamp<0 or policy["policy_received_ns"]<0):
        return result(None,"INVALID_QUOTE_OR_POLICY_CLOCK")
    if stamp>decision_ns or policy["policy_received_ns"]>decision_ns:
        return result(None,"QUOTE_OR_POLICY_NOT_AVAILABLE_AT_DECISION")
    if quote.get("valid_firm_nbbo") is not True:
        return result(False,"INVALID_NONFIRM_TOP_OF_BOOK")
    condition=quote.get("quote_condition")
    indicators=quote.get("quote_indicators")
    if type(condition) is not int or not isinstance(indicators,list):
        return result(None,"UNRESOLVED_NATIVE_QUOTE_CONDITION")
    if not indicators or any(type(x) is not int for x in indicators):
        return result(None,"INDICATORS_MISSING_OR_INVALID")
    if condition not in policy["allowed_quote_conditions"]:
        return result(False,"QUOTE_CONDITION_NOT_FIRM_OR_UNKNOWN")
    if any(x not in policy["allowed_nbbo_indicators"] for x in indicators):
        return result(None,"NON_ADMITTED_NBBO_INDICATOR")
    return result(True,"SOURCE_CONDITION_ELIGIBLE_FOR_OBSERVATION_ONLY")

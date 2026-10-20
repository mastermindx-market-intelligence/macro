"""Pure research outcome codec for one published exact-expression selection.

Binds an incumbent private intent readback (``resolve_intent_availability`` on the
sealed pair) plus the caller's native OA-3 ``ExpressionReceipt`` to exactly one
result of the unchanged ``options_alpha_exact_option_outcome.evaluate`` owner.
Representation only: no I/O, clock reads, network, defaults, quote selection or
return math happen here; the whole OA-3 record is preserved.  Authority boundaries
(explicit): neither this codec, ``validate_expression_outcome`` nor any persistence
of a row establishes natural, prospective, training or execution admission -- a row
proves persisted shape/binding only, never original provider authenticity or an
actual live capture, and every input is caller-supplied retained evidence, not
source authentication.  Unknown contract terms remain unavailable: no default 100
multiplier, no default standard-deliverable flag, no absence-of-memo rule; terms
come solely from the validated intent's explicit ``terms_observation``.  The
selection-frozen flag and selection fence are never inferred, flipped or set here;
the unchanged OA-3 evaluator validates the caller's original fields.  Publication
values come from the actual resolved pair readback, never from caller arguments.
"""
from __future__ import annotations

import copy
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from typing import Any

from engine import options_alpha_exact_option_outcome as oa3
from engine import options_alpha_expression_intent as intent_codec
from engine import options_alpha_expression_publication as intent_readback
from engine import options_nbbo_cohort as cohort
from engine import options_signal_campaign as campaigns

EXPRESSION_OUTCOME_SCHEMA = "options.signal_campaign_expression_outcome/v1"
HORIZON = "h60"
KEY_KIND = "exact_option_expression"
LABEL_AUTHORITY = "research_only"
EVIDENCE_ADMISSION = "local_retained_evidence_not_source_admission"
PUBLICATION_CONSUMER = "incumbent_private_publisher_owner"
OUTCOME_ID_PREFIX = "ocexout_"
FACTUAL_CLOCK_FIELDS = ("request_started_at", "response_observed_at", "retrieval_observed_at",
                        "computed_at")
_ROW_KEYS = frozenset({"schema", "expression_outcome_id", "campaign_id", "campaign_revision_id",
    "expression_id", "source_candidate_id", "horizon", "policy_id", "policy_sha256",
    "observed_at", "intent", "publication", "evaluation", "evaluation_sha256",
    "label_authority", "evidence_admission", "training_eligible", "authority"})
_PUBLICATION_KEYS = frozenset({"manifest_sha256", "receipt_id", "feed_payload_sha256",
    "first_receipt_id", "commitment_published_at", "intent_bytes_sha256", "consumer",
    "public_consumer_available"})
_TERMINAL_STATUSES = frozenset({oa3.STATUS_COMPLETE, oa3.STATUS_UNAVAILABLE, oa3.STATUS_EXCLUDED,
                                oa3.STATUS_INVALID})
_CONTRACT_FIELDS = ("root", "expiration", "right", "strike", "strike_millis", "occ_symbol")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
# Exact terminal record shape of the unchanged native OA-3 builders
# (``oa3._build_complete_fixture`` / ``oa3._build_invalid_fixture``): one key
# set for every status, the status deciding which values are required versus
# null.  Read from that owner at the pinned schema/policy identity, never
# inferred or re-evaluated here.
_EVALUATION_KEYS = frozenset({
    "schema", "policy_id", "policy_version", "policy_sha256", "expression_id",
    "expression_digest_sha256", "expression_upstream_digest_sha256",
    "expression_raw_response_sha256", "expression_raw_response_bytes",
    "expression_source_candidate_id", "expression_decision_receipt_sha256",
    "expression_source_rule_digest_sha256", "selection_frozen_before_outcomes",
    "selection_fence_at", "contract", "standard_deliverable",
    "expression_decision_at", "expression_available_at", "session_date",
    "session_rth_open", "session_rth_close", "position", "quantity_contracts",
    "multiplier", "status", "reason", "entry", "exit", "net_return_pct", "cost",
    "quote_source", "authority"})
_EVIDENCE_BLOCK_KEYS = frozenset({"role", "side", "query_bounds", "query",
    "raw_response_sha256", "raw_response_bytes", "raw_payload_sha256",
    "raw_payload_bytes", "selected", "parse_error", "clocks"})
_CLOCK_KEYS = frozenset(FACTUAL_CLOCK_FIELDS)
_QUERY_BOUNDS_KEYS = frozenset({"start_at", "end_at"})
_SELECTED_KEYS = frozenset({"event_at", "price", "size", "exchange", "condition"})
_COST_KEYS = frozenset({"multiplier", "fee_per_side_usd", "return_formula",
                        "cost_interpretation"})
_QUOTE_SOURCE_KEYS = frozenset({"endpoint", "interval", "quote_rule_id",
    "exact_contract_required", "firm_condition_required", "known_exchange_required",
    "raw_response_receipt_required", "executable_fill_claim"})


class ExpressionOutcomeError(ValueError):
    """A caller-supplied expression outcome input is not bindable as-is."""


@dataclass(frozen=True)
class ExpressionOutcomeEvidence:
    """Typed retained inputs; their presence proves nothing about origin."""

    publication_pair: Any
    expression: oa3.ExpressionReceipt
    entry: oa3.QuoteEvidence
    exit: oa3.QuoteEvidence
    observed_at: str


def _fail(message: str) -> None:
    raise ExpressionOutcomeError(message)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ExpressionOutcomeError(message)


def _wrap(message: str, action: Any, *args: Any, **kwargs: Any) -> Any:
    try:
        return action(*args, **kwargs)
    except ValueError as exc:
        raise ExpressionOutcomeError(f"{message}: {exc}") from exc


def _digest(value: Any) -> str:
    return sha256(_wrap("value is not canonical finite JSON", campaigns.canonical_bytes,
                        value)).hexdigest()


def _hex64(value: Any, name: str) -> str:
    _require(isinstance(value, str) and _HEX64.fullmatch(value) is not None,
             f"{name} must be a 64-character lowercase hex digest")
    return value


def _require_keys(value: Any, keys: frozenset[str], message: str) -> None:
    _require(isinstance(value, dict) and set(value) == keys, message)


def _finite_decimal_string(value: Any, name: str) -> None:
    # Native Decimal values are persisted as strings; a nonempty string alone
    # would also admit malformed or nonfinite values after a digest is rebound.
    _require(isinstance(value, str) and re.fullmatch(
        r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", value) is not None,
        f"{name} must be a finite decimal string")
    _require(Decimal(value).is_finite(), f"{name} must be finite")


def _aware(value: Any, name: str) -> datetime:
    """Any aware datetime/ISO clock, UTC-normalized; naive values are refused."""
    if isinstance(value, datetime):
        stamp = value
    elif isinstance(value, str):
        stamp = _wrap(f"{name} is not an ISO clock", datetime.fromisoformat,
                      value.replace("Z", "+00:00"))
    else:
        _fail(f"{name} must be an aware clock value")
    _require(stamp.tzinfo is not None and stamp.tzinfo.utcoffset(stamp) is not None,
             f"{name} is naive; a timezone-aware clock is required")
    return stamp.astimezone(timezone.utc)


def _z_clock(value: Any, name: str) -> datetime:
    _require(isinstance(value, str) and value.endswith("Z"),
             f"{name} must be a canonical UTC Z clock")
    return _aware(value, name)


def _clock_equal(a: Any, b: Any) -> bool:
    try:
        return _aware(a, "clock") == _aware(b, "clock")
    except ExpressionOutcomeError:
        return False


def _covers(observed: datetime, clock: Any, label: str) -> None:
    _require(not observed < _aware(clock, label),
             f"observed_at precedes the factual {label} clock")


def _json_value(value: Any, path: str) -> Any:
    """Strict JSON representation of the native record; not an evaluation."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        _require(math.isfinite(value), f"{path} contains a non-finite number")
        return value
    if isinstance(value, Decimal):
        _require(value.is_finite(), f"{path} contains a non-finite Decimal")
        return str(value)
    if isinstance(value, datetime):
        return _aware(value, path).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            _require(isinstance(key, str), f"{path} contains a non-string mapping key")
            out[key] = _json_value(item, f"{path}.{key}")
        return out
    if isinstance(value, (list, tuple)):
        return [_json_value(item, f"{path}[{index}]") for index, item in enumerate(value)]
    _fail(f"{path} contains unsupported value type {type(value).__name__}")


def _check_evaluation(evaluation: dict, *, intent: dict, intent_bytes: str,
                      commitment: str, observed: datetime) -> None:
    """Exact native terminal shape plus the retained identity/clock bindings.

    Shape-only and status-dependent: the unchanged OA-3 builders always emit
    exactly one record key set and one evidence-block key set for every
    status, always carry the contract/clock/quote-block fields, and populate
    or null them per status.  A complete record must retain the bound
    contract, explicit terms, session, receipt identity, selection-frozen
    flag, decimal-string return and both observed quote blocks with their
    full factual clock sets and native query windows.  This re-checks the
    persisted representation only: it never recomputes the frozen return
    math, never re-runs the ruler, and proves nothing about origin.
    """
    _require_keys(evaluation, _EVALUATION_KEYS,
                  "evaluation is not the exact native OA-3 terminal record shape")
    status = evaluation["status"]
    _require(status != oa3.STATUS_PENDING,
             "pending is not terminal; an outcome row cannot be built yet")
    _require(status in _TERMINAL_STATUSES,
             f"evaluation status {status!r} is not a native terminal status")
    complete = status == oa3.STATUS_COMPLETE
    ruler, terms = intent["oa3_ruler"], intent["terms_observation"]
    for name, expected in (("schema", oa3.SCHEMA), ("policy_id", ruler["policy_id"]),
                           ("policy_sha256", ruler["policy_sha256"]),
                           ("policy_version", ruler["policy_version"]),
                           ("expression_id", intent["expression_id"]),
                           ("expression_source_candidate_id", intent["candidate_id"]),
                           ("expression_decision_receipt_sha256", intent_bytes),
                           ("expression_source_rule_digest_sha256", intent["selection_policy_sha256"])):
        _require(evaluation[name] == expected,
                 f"evaluation {name} is not bound to the resolved intent/policy")
    # The native builders always carry the contract field: a complete record
    # always retains the canonical contract, and any non-null reject value
    # must still be that contract.  Identity-defective native reject records
    # legitimately keep it null (no canonical contract ever existed there).
    if complete:
        _require(evaluation["contract"] is not None,
                 "a complete native record always retains its canonical contract; "
                 "a null contract is only the identity-defective reject shape")
        _require(evaluation["contract"] == intent["contract"],
                 "evaluation contract differs from the intent contract")
    elif evaluation["contract"] is not None:
        _require(evaluation["contract"] == intent["contract"],
                 "evaluation contract differs from the intent contract")
    for name, anchor in (("expression_decision_at", intent["decision_at"]),
                         ("expression_available_at", commitment)):
        if complete:
            _require(evaluation[name] is not None
                     and _clock_equal(evaluation[name], anchor),
                     f"a complete native record retains {name} bound to its "
                     "intent/commitment clock")
        elif evaluation[name] is not None:
            _require(_clock_equal(evaluation[name], anchor),
                     f"evaluation {name} is not bound to its intent/commitment clock")
    if complete:
        _require(type(evaluation["multiplier"]) is int
                 and evaluation["multiplier"] == terms["multiplier"],
                 "a complete native record retains the explicit terms multiplier")
        _require(evaluation["standard_deliverable"] is terms["standard_deliverable"],
                 "a complete native record retains the explicit terms deliverable flag")
    else:
        if evaluation["multiplier"] is not None:
            _require(evaluation["multiplier"] == terms["multiplier"],
                     "evaluation multiplier differs from the explicit terms observation")
        if evaluation["standard_deliverable"] is not None:
            _require(evaluation["standard_deliverable"] is terms["standard_deliverable"],
                     "evaluation deliverable differs from the explicit terms observation")
    _require(type(evaluation["selection_frozen_before_outcomes"]) is bool,
             "evaluation selection_frozen_before_outcomes is not the native boolean field")
    if complete:
        _require(evaluation["selection_frozen_before_outcomes"] is True,
                 "a complete native record is only emitted selection-frozen")
    reason = evaluation["reason"]
    if complete:
        _require(reason is None, "a complete native record must carry reason null")
        _finite_decimal_string(evaluation["net_return_pct"], "net_return_pct")
    else:
        _require(isinstance(reason, str) and bool(reason.strip()),
                 "terminal reject records must retain their native reason")
        _require(evaluation["net_return_pct"] is None,
                 "only a complete native record carries a return value")
    _hex64(evaluation["expression_raw_response_sha256"],
           "evaluation expression_raw_response_sha256")
    _hex64(evaluation["expression_upstream_digest_sha256"],
           "evaluation expression_upstream_digest_sha256")
    _require(type(evaluation["expression_raw_response_bytes"]) is int
             and not isinstance(evaluation["expression_raw_response_bytes"], bool)
             and evaluation["expression_raw_response_bytes"] > 0,
             "evaluation expression_raw_response_bytes is not the native receipt size")
    if complete:
        _hex64(evaluation["expression_digest_sha256"],
               "evaluation expression_digest_sha256")
        _require(isinstance(evaluation["session_date"], str)
                 and bool(evaluation["session_date"].strip()),
                 "a complete native record retains its session date")
        session_date = _wrap("session_date is not an ISO date", date.fromisoformat,
                             evaluation["session_date"])
        _require(session_date.isoformat() == evaluation["session_date"],
                 "session_date is not the native ISO date representation")
        for name in ("session_rth_open", "session_rth_close", "selection_fence_at"):
            _require(isinstance(evaluation[name], str) and bool(evaluation[name].strip()),
                     f"a complete native record retains its {name} clock")
            _aware(evaluation[name], name)
        _require(evaluation["position"] == "long",
                 "a complete native record retains its research position")
        _require(type(evaluation["quantity_contracts"]) is int
                 and evaluation["quantity_contracts"] == oa3.QUANTITY_CONTRACTS,
                 "a complete native record retains its integer contract quantity")
    else:
        _require(isinstance(evaluation["expression_digest_sha256"], str),
                 "evaluation expression_digest_sha256 is not the native string field")
        for name in ("session_date", "session_rth_open", "session_rth_close"):
            _require(evaluation[name] is None or isinstance(evaluation[name], str),
                     f"evaluation {name} is not the native session field")
    _require_keys(evaluation["cost"], _COST_KEYS,
                  "evaluation cost block is not the exact native frozen cost shape")
    _require(type(evaluation["cost"]["multiplier"]) is int
             and evaluation["cost"]["multiplier"] == oa3.MULTIPLIER
             and evaluation["cost"]["fee_per_side_usd"] == oa3.FEE_PER_SIDE_USD_STR,
             "evaluation cost block is not the native frozen multiplier/fee")
    for name in ("return_formula", "cost_interpretation"):
        _require(isinstance(evaluation["cost"][name], str)
                 and bool(evaluation["cost"][name].strip()),
                 f"evaluation cost {name} is not the native formula string")
    quote_source = evaluation["quote_source"]
    _require_keys(quote_source, _QUOTE_SOURCE_KEYS,
                  "evaluation quote_source block is not the exact native source shape")
    _require(quote_source["endpoint"] == cohort.SOURCE_ENDPOINT
             and quote_source["interval"] == cohort.SOURCE_INTERVAL
             and quote_source["quote_rule_id"] == cohort.QUOTE_RULE_ID,
             "evaluation quote_source is not bound to the native source identity")
    _require(quote_source["exact_contract_required"] is True
             and quote_source["firm_condition_required"] is True
             and quote_source["known_exchange_required"] is True
             and quote_source["raw_response_receipt_required"] is True
             and quote_source["executable_fill_claim"] is False,
             "evaluation quote_source is not the native literal flag mapping")
    authority = evaluation["authority"]
    _require(isinstance(authority, dict) and authority == dict(oa3.ALL_FALSE_AUTHORITY)
             and all(value is False for value in authority.values()),
             "evaluation authority is not the native all-false literal mapping")
    for role in (oa3.ROLE_ENTRY, oa3.ROLE_EXIT):
        block = evaluation[role]
        _require_keys(block, _EVIDENCE_BLOCK_KEYS,
                      f"evaluation {role} block is not the exact native evidence shape")
        _require(block["role"] == role
                 and block["side"] == (oa3.SIDE_ASK if role == oa3.ROLE_ENTRY
                                       else oa3.SIDE_BID),
                 f"evaluation {role} block is not bound to its native role and side")
        for name in ("raw_response_sha256", "raw_payload_sha256"):
            if block[name] is not None:
                _hex64(block[name], f"evaluation {role}.{name}")
        for name in ("raw_response_bytes", "raw_payload_bytes"):
            _require(type(block[name]) is int and not isinstance(block[name], bool)
                     and block[name] >= 0,
                     f"evaluation {role}.{name} is not the native byte count")
        _require(block["parse_error"] is None
                 or (isinstance(block["parse_error"], str)
                     and bool(block["parse_error"].strip())),
                 f"evaluation {role}.parse_error is neither null nor a native reason")
        _require(block["query"] is None or isinstance(block["query"], dict),
                 f"evaluation {role}.query is malformed")
        query_bounds = block["query_bounds"]
        if query_bounds is not None:
            _require_keys(query_bounds, _QUERY_BOUNDS_KEYS,
                          f"evaluation {role}.query_bounds is malformed")
            _aware(query_bounds["start_at"], f"{role}.query_bounds.start_at")
            _aware(query_bounds["end_at"], f"{role}.query_bounds.end_at")
        clocks = block["clocks"]
        _require_keys(clocks, _CLOCK_KEYS,
                      f"evaluation {role} clocks are not the exact native factual clock set")
        for name in FACTUAL_CLOCK_FIELDS:
            if clocks[name] is not None:
                _covers(observed, clocks[name], f"{role}.{name}")
        selected = block["selected"]
        if selected is not None:
            _require_keys(selected, _SELECTED_KEYS,
                          f"evaluation {role}.selected is not the exact native quote shape")
            _aware(selected["event_at"], f"{role}.selected.event_at")
            _covers(observed, selected["event_at"], f"{role}.selected.event_at")
            _require(isinstance(selected["price"], str)
                     and bool(selected["price"].strip())
                     and type(selected["size"]) is int
                     and type(selected["exchange"]) is int
                     and type(selected["condition"]) is int,
                     f"evaluation {role}.selected is not the native quote value shape")
            _finite_decimal_string(selected["price"], f"{role}.selected.price")
        if complete:
            # A complete record always retains both observed quotes: receipt
            # identity, the exact source query and every factual clock.
            _require(block["raw_response_sha256"] is not None
                     and block["raw_payload_sha256"] is not None
                     and block["raw_response_bytes"] > 0
                     and block["raw_payload_bytes"] > 0,
                     f"a complete native record retains the {role} raw receipt identity")
            _require(block["parse_error"] is None,
                     f"a complete native record carries no {role} parse error")
            _require(isinstance(block["query"], dict) and bool(block["query"])
                     and query_bounds is not None,
                     f"a complete native record retains the exact {role} source query")
            _require(all(clocks[name] is not None for name in FACTUAL_CLOCK_FIELDS),
                     f"a complete native record retains every factual {role} clock")
            _require(selected is not None and selected["event_at"] is not None,
                     f"a complete native record retains its observed {role} quote")
    if complete:
        # The native ruler binds each 60s query window (entry at the
        # commitment clock, exit at the observed entry event + 60m); the
        # persisted record must retain exactly those windows.
        entry_block = evaluation[oa3.ROLE_ENTRY]
        exit_block = evaluation[oa3.ROLE_EXIT]
        entry_start = _aware(entry_block["query_bounds"]["start_at"],
                             "entry.query_bounds.start_at")
        _require(_clock_equal(entry_start, commitment),
                 "a complete native record binds the entry window to the "
                 "commitment clock")
        for block in (entry_block, exit_block):
            start = _aware(block["query_bounds"]["start_at"], "query_bounds.start_at")
            end = _aware(block["query_bounds"]["end_at"], "query_bounds.end_at")
            _require(end - start == timedelta(seconds=oa3.ENTRY_WINDOW_SECONDS),
                     "a complete native record retains the exact native "
                     f"{oa3.ENTRY_WINDOW_SECONDS}s query window")
        _require(_clock_equal(_aware(exit_block["query_bounds"]["start_at"],
                                     "exit.query_bounds.start_at"),
                              _aware(entry_block["selected"]["event_at"],
                                     "entry.selected.event_at") + oa3.EXIT_HORIZON),
                 "a complete native record binds the exit window to the observed "
                 "entry event + 60m")


def make_expression_outcome(*, campaign: dict, evidence: ExpressionOutcomeEvidence) -> dict:
    """Build one research-only outcome row; admission is never established.

    All intent/receipt/candidate/campaign bindings are checked before the native
    evaluator runs; its whole record is then preserved (strict JSON) and re-bound
    to the resolved intent.
    """
    _require(isinstance(evidence, ExpressionOutcomeEvidence),
             "typed ExpressionOutcomeEvidence is required")
    _require(isinstance(campaign, dict), "campaign must be the native campaign mapping")
    _require(isinstance(evidence.expression, oa3.ExpressionReceipt),
             "the caller must supply the native oa3.ExpressionReceipt; a bare claimed "
             "payload is refused")
    _require(isinstance(evidence.entry, oa3.QuoteEvidence)
             and evidence.entry.role == oa3.ROLE_ENTRY
             and isinstance(evidence.exit, oa3.QuoteEvidence)
             and evidence.exit.role == oa3.ROLE_EXIT,
             "entry/exit must be native oa3.QuoteEvidence under their roles")
    pair = evidence.publication_pair
    payload = evidence.expression.parsed_payload
    expression_id = payload.get("expression_id")
    _require(isinstance(expression_id, str) and bool(expression_id.strip()),
             "receipt expression_id must be a non-empty string")
    availability = _wrap("private intent readback failed",
                         intent_readback.resolve_intent_availability, pair, expression_id)
    for name, expected in (("status", "available"), ("reason", None),
                           ("consumer_expression_bytes_resolved", True),
                           ("public_consumer_available", False),
                           ("consumer", PUBLICATION_CONSUMER),
                           ("commitment_published_at", availability.get("available_at"))):
        _require(availability.get(name) == expected,
                 f"availability is not a resolved incumbent-private commitment ({name})")
    _require(isinstance(availability.get("intent"), dict)
             and isinstance(availability.get("first_receipt_id"), str),
             "availability lacks the resolved intent or first receipt identity")
    commitment = availability["commitment_published_at"]
    intent_bytes = _hex64(availability["intent_bytes_sha256"], "availability intent_bytes_sha256")
    _z_clock(commitment, "commitment_published_at")
    intent = _wrap("retained intent failed the intent codec",
                   intent_codec.validate_expression_intent, availability["intent"])
    _require(intent == availability["intent"] and intent["expression_id"] == expression_id
             and intent_bytes == intent_readback.digest(intent),
             "retained intent is not the canonical digest-bound intent for this expression")
    feed, receipt_pair = getattr(pair, "feed", None), getattr(pair, "receipt", None)
    payload_bytes = getattr(pair, "payload", None)
    _require(isinstance(feed, dict) and isinstance(receipt_pair, dict)
             and isinstance(payload_bytes, bytes),
             "publication pair must expose the sealed feed, receipt and payload bytes")
    matches = [item for item in (feed.get("formed_candidates") or ())
               if isinstance(item, dict) and item.get("candidate_id") == intent["candidate_id"]]
    _require(len(matches) == 1,
             "the intent candidate must appear exactly once in the sealed feed")
    candidate, frozen = matches[0], matches[0].get("frozen_formation")
    _require(isinstance(candidate.get("campaign_id"), str) and isinstance(frozen, dict)
             and candidate["campaign_id"] == campaign.get("campaign_id")
             and frozen.get("campaign_revision_id") == campaign.get("campaign_revision_id"),
             "the caller campaign is not the intent candidate's frozen formation")
    _wrap("native campaign validation refused", campaigns.validate_campaign, campaign)
    bound = [update for update in (candidate.get("versioned_updates") or ())
             if isinstance(update, dict)
             and update.get("campaign_revision_id") == frozen["campaign_revision_id"]]
    _require(len(bound) == 1 and bound[0].get("revision_digest_sha256") == _digest(campaign),
             "exactly one frozen-revision versioned update must bind the caller campaign's "
             "canonical bytes")
    ruler, terms = intent["oa3_ruler"], intent["terms_observation"]
    _require(ruler["policy_id"] == oa3.FROZEN_POLICY_ID
             and ruler["policy_sha256"] == oa3.FROZEN_POLICY_SHA256
             and ruler["policy_version"] == oa3.FROZEN_POLICY_VERSION,
             "the intent oa3 ruler is not the native frozen policy identity")

    def _field(name: str) -> Any:
        _require(name in payload, f"expression receipt is missing immutable field {name}")
        return payload[name]

    for name, expected in (("source_candidate_id", intent["candidate_id"]),
                           ("policy_version", ruler["policy_version"]),
                           ("source_rule_digest_sha256", intent["selection_policy_sha256"]),
                           ("decision_receipt_sha256", intent_bytes)):
        _require(_field(name) == expected,
                 f"receipt {name} is not bound to the resolved intent/policy")
    receipt_contract = _wrap("receipt contract is invalid", cohort.validate_contract,
                             {key: _field(key) for key in _CONTRACT_FIELDS})
    _require(receipt_contract == intent["contract"],
             "receipt canonical contract differs from the intent contract")
    _require(_clock_equal(_field("decision_at"), intent["decision_at"]),
             "receipt decision_at is not clock-equivalent to the intent decision")
    _require(_clock_equal(_field("available_at"), commitment),
             "receipt available_at is not the expression-specific first commitment clock")
    _require(type(_field("multiplier")) is int and _field("multiplier") == terms["multiplier"]
             and _field("standard_deliverable") is terms["standard_deliverable"],
             "receipt multiplier/deliverable must equal the explicit intent terms_observation; "
             "nothing is defaulted")
    observed = _z_clock(evidence.observed_at, "observed_at")
    _require(observed >= _aware(intent["decision_at"], "intent decision_at")
             and observed >= _aware(commitment, "commitment clock"),
             "observed_at precedes the intent decision or commitment clock")
    for item in (evidence.entry, evidence.exit):
        for name in FACTUAL_CLOCK_FIELDS:
            _require(observed >= getattr(item, name),
                     f"observed_at precedes the factual evidence {name} clock")
    record = _wrap("native OA-3 evaluation refused the caller inputs", oa3.evaluate,
                   evidence.expression, entry_evidence=evidence.entry,
                   exit_evidence=evidence.exit)
    evaluation = _json_value(record, "evaluation")
    _require(evaluation.get("expression_raw_response_sha256") == evidence.expression.raw_sha256
             and evaluation.get("expression_raw_response_bytes") == evidence.expression.raw_size
             and evaluation.get("expression_upstream_digest_sha256")
             == evidence.expression.upstream_digest_sha256,
             "evaluation does not retain the provided receipt raw identity")
    _check_evaluation(evaluation, intent=intent, intent_bytes=intent_bytes,
                      commitment=commitment, observed=observed)
    feed_payload_sha256 = sha256(payload_bytes).hexdigest()
    _require(receipt_pair.get("payload_sha256") == feed_payload_sha256
             and isinstance(receipt_pair.get("receipt_id"), str)
             and bool(receipt_pair["receipt_id"]),
             "the sealed receipt does not digest the pair payload bytes")
    row = {
        "schema": EXPRESSION_OUTCOME_SCHEMA,
        "expression_outcome_id": OUTCOME_ID_PREFIX + _digest({
            "expression_id": intent["expression_id"], "policy_id": oa3.FROZEN_POLICY_ID,
            "policy_sha256": oa3.FROZEN_POLICY_SHA256, "horizon": HORIZON})[:24],
        "campaign_id": campaign["campaign_id"],
        "campaign_revision_id": campaign["campaign_revision_id"],
        "expression_id": intent["expression_id"],
        "source_candidate_id": intent["candidate_id"],
        "horizon": HORIZON,
        "policy_id": oa3.FROZEN_POLICY_ID,
        "policy_sha256": oa3.FROZEN_POLICY_SHA256,
        "observed_at": evidence.observed_at,
        "intent": intent,
        "publication": {
            "manifest_sha256": _hex64(getattr(pair, "expression_manifest_sha256", None),
                                      "pair expression_manifest_sha256"),
            "receipt_id": receipt_pair["receipt_id"],
            "feed_payload_sha256": feed_payload_sha256,
            "first_receipt_id": availability["first_receipt_id"],
            "commitment_published_at": commitment,
            "intent_bytes_sha256": intent_bytes,
            "consumer": PUBLICATION_CONSUMER,
            "public_consumer_available": False},
        "evaluation": evaluation,
        "evaluation_sha256": _digest(evaluation),
        "label_authority": LABEL_AUTHORITY,
        "evidence_admission": EVIDENCE_ADMISSION,
        "training_eligible": False,
        "authority": copy.deepcopy(campaigns.FALSE_AUTHORITY),
    }
    return validate_expression_outcome(row)


def validate_expression_outcome(row: dict) -> dict:
    """Recheck the persisted shape/binding; return a deep copy.

    This validates nothing about original provider authenticity or an actual live
    capture; neither it nor persistence establishes natural, prospective, training
    or execution admission.
    """
    _require(isinstance(row, dict) and set(row) == _ROW_KEYS, "row keys are not exact")
    for name, expected in (("schema", EXPRESSION_OUTCOME_SCHEMA), ("horizon", HORIZON),
                           ("label_authority", LABEL_AUTHORITY),
                           ("evidence_admission", EVIDENCE_ADMISSION),
                           ("training_eligible", False), ("policy_id", oa3.FROZEN_POLICY_ID),
                           ("policy_sha256", oa3.FROZEN_POLICY_SHA256)):
        _require(row[name] == expected, f"row {name} literal mismatch")
    _require(row["training_eligible"] is False, "training_eligible must be the literal False")
    authority = row["authority"]
    _require(isinstance(authority, dict) and authority == campaigns.FALSE_AUTHORITY
             and all(value is False for value in authority.values()),
             "row authority is not the exact all-false literal mapping")
    for name in ("campaign_id", "campaign_revision_id", "expression_id", "source_candidate_id"):
        _require(isinstance(row[name], str) and bool(row[name].strip()),
                 f"row {name} must be a non-empty string")
    observed = _z_clock(row["observed_at"], "observed_at")
    _require(row["expression_outcome_id"] == OUTCOME_ID_PREFIX + _digest({
        "expression_id": row["expression_id"], "policy_id": oa3.FROZEN_POLICY_ID,
        "policy_sha256": oa3.FROZEN_POLICY_SHA256, "horizon": HORIZON})[:24],
        "expression_outcome_id does not rebind its identities")
    intent = _wrap("row intent failed the intent codec",
                   intent_codec.validate_expression_intent, row["intent"])
    _require(row["expression_id"] == intent["expression_id"]
             and row["source_candidate_id"] == intent["candidate_id"]
             and intent["oa3_ruler"]["policy_id"] == row["policy_id"]
             and intent["oa3_ruler"]["policy_sha256"] == row["policy_sha256"],
             "row identities/policy are not bound to the intent")
    publication = row["publication"]
    _require(isinstance(publication, dict) and set(publication) == _PUBLICATION_KEYS
             and publication["consumer"] == PUBLICATION_CONSUMER
             and publication["public_consumer_available"] is False
             and all(isinstance(publication[name], str) and publication[name].strip()
                     for name in ("receipt_id", "first_receipt_id")),
             "publication block does not bind its exact private-readback shape")
    for name in ("manifest_sha256", "feed_payload_sha256", "intent_bytes_sha256"):
        _hex64(publication[name], f"publication.{name}")
    _require(publication["intent_bytes_sha256"] == intent_readback.digest(intent),
             "publication intent_bytes_sha256 does not digest the full intent")
    commitment = _z_clock(publication["commitment_published_at"],
                          "publication.commitment_published_at")
    _require(commitment >= _aware(intent["decision_at"], "intent decision_at")
             and observed >= commitment, "commitment/observed clock order violated")
    _require(isinstance(row["evaluation"], dict)
             and row["evaluation_sha256"] == _digest(row["evaluation"]),
             "evaluation_sha256 does not rebind the canonical evaluation record")
    _check_evaluation(row["evaluation"], intent=intent,
                      intent_bytes=publication["intent_bytes_sha256"],
                      commitment=publication["commitment_published_at"], observed=observed)
    return copy.deepcopy(row)


def expression_outcome_key(row: dict) -> tuple[str, str, str, str]:
    """Return the exact expression-specific outcome key for a persisted row."""
    _require(isinstance(row, dict), "outcome key requires a materialized row")
    expression_id = row.get("expression_id")
    _require(isinstance(expression_id, str) and bool(expression_id.strip()),
             "outcome key requires a bound expression id")
    _hex64(row.get("policy_sha256"), "outcome key policy_sha256")
    _require(row.get("horizon") == HORIZON, "the expression outcome key is horizon-exact")
    return (KEY_KIND, expression_id, row["policy_sha256"], HORIZON)


__all__ = ["EVIDENCE_ADMISSION", "EXPRESSION_OUTCOME_SCHEMA", "HORIZON", "LABEL_AUTHORITY",
           "PUBLICATION_CONSUMER", "ExpressionOutcomeError", "ExpressionOutcomeEvidence",
           "expression_outcome_key", "make_expression_outcome", "validate_expression_outcome"]

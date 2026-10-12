"""Options Alpha OA-3 exact-option outcome evaluator (pure fixture-only).

This module is the pure evaluator mandated by
``DEC:OPTIONS-ALPHA-EXACT-OPTION-OUTCOME-RULER`` /
``research/options_estate/OPTIONS_ALPHA_EXACT_OPTION_OUTCOME_PREREG_2026-09-19.md``.

It consumes an already-frozen OA expression receipt (raw upstream bytes plus
parsed payload plus the caller-supplied upstream immutable digest), per-role
``QuoteEvidence`` records carrying the exact source query, raw private-source
bytes, strictly parsed payload, and independent request/response/retrieval/
computed clocks for the entry and exit windows, plus the frozen policy bytes
that pin the policy identity the evaluator obeys.  It emits a single OA-3
fixture record and writes no durable object — there is no I/O here, no
registry, no second outcome ledger, no scheduler.

The module imports *no* on-disk artefacts: the frozen policy mapping is
hardcoded in this module and verified at import time against the SHA pinned
in the preregistration; the evaluator refuses to operate against a caller-
authored policy override.

The module reuses only generic mechanics from ``engine/options_nbbo_cohort.py``:

* ``validate_contract`` — exact OCC identity validation;
* ``parse_quote_response`` — firm OPRA + known exchange + RTH + crossed
  /conflict filtering, first valid quote selection inside the closed window;
* ``canonical_json_bytes`` — strict canonical JSON for receipt bindings;
* ``source_query`` / ``validate_source_query`` — exact query contract binding;
* ``net_return_pct`` — the frozen 100-multiplier / USD 0.65-per-side ruler;
* the ``SOURCE_ENDPOINT`` / ``SOURCE_INTERVAL`` / ``QUOTE_RULE_ID`` /
  ``FEE_PER_SIDE_USD`` constants.

It deliberately does **not** reuse the benchmark cohort's event identity,
capture registry, trigger-boundary semantics, 600-second availability rule,
or comparison-session coverage; the OA-3 rule starts evaluation from the frozen
expression's own ``available_at`` and the exit target is fixed at the admitted
entry quote's event clock plus exactly sixty minutes, not at any earlier or
later benchmark boundary.
"""

from __future__ import annotations

import copy as _copy
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime as _datetime_cls, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from types import MappingProxyType
from typing import Any
from zoneinfo import ZoneInfo

from engine import options_nbbo_cohort as cohort
from engine.session_digest import session_window_et
from lib import nyse_calendar


SCHEMA = "options.oa3_exact_option_outcome_fixture/v1"
POLICY_SCHEMA = "options.alpha_exact_option_outcome_policy/v1"

# Frozen policy identity — pinned once in code so the evaluator never reads
# artefacts and cannot be redirected to a different policy by a caller.
FROZEN_POLICY_ID = "oa3.long_single_leg_h60_nbbo/v1"
FROZEN_POLICY_VERSION = "v1"
FROZEN_POLICY_SHA256 = (
    "00b9eb94a97233215dff416975e42a8705cb4fc3c9a3524f9168ee66645098bf"
)

ENTRY_WINDOW_SECONDS = 60
EXIT_WINDOW_SECONDS = 60
EXIT_HORIZON = timedelta(minutes=60)
QUANTITY_CONTRACTS = 1
MULTIPLIER = 100
FEE_PER_SIDE_USD_STR = "0.65"

STATUS_PENDING = "pending"
STATUS_COMPLETE = "complete"
STATUS_UNAVAILABLE = "unavailable"
STATUS_EXCLUDED = "excluded"
STATUS_INVALID = "invalid"
ROLE_ENTRY = "entry"
ROLE_EXIT = "exit"
SIDE_ASK = "ask"
SIDE_BID = "bid"

ET = ZoneInfo("America/New_York")
UTC = timezone.utc

# Canonical frozen policy mapping — hardcoded so the module imports no
# artefact.  The structural assert below proves the hardcoded bytes equal the
# pinned FROZEN_POLICY_SHA256; any drift fails closed at import.
_FROZEN_POLICY_DICT: dict[str, Any] = {
    "schema": POLICY_SCHEMA,
    "policy_id": FROZEN_POLICY_ID,
    "state": "preregistered_inactive",
    "population": {
        "exact_expression_receipt_required": True,
        "selection_before_outcomes": True,
        "position": "long",
        "quantity_contracts": 1,
        "standard_multiplier": 100,
        "standard_deliverable_only": True,
        "same_day_expiration_allowed": False,
        "package_supported": False,
        "short_option_supported": False,
    },
    "entry": {
        "boundary": "expression.available_at",
        "selected_side": SIDE_ASK,
        "quote_event_window_seconds": ENTRY_WINDOW_SECONDS,
        "minimum_displayed_contracts": 1,
    },
    "exit": {
        "target": "entry_quote.event_at+PT60M",
        "selected_side": SIDE_BID,
        "quote_event_window_seconds": EXIT_WINDOW_SECONDS,
        "minimum_displayed_contracts": 1,
    },
    "quote_source": {
        "endpoint": cohort.SOURCE_ENDPOINT,
        "interval": cohort.SOURCE_INTERVAL,
        "quote_rule_reference": cohort.QUOTE_RULE_ID,
        "exact_contract_required": True,
        "firm_condition_required": True,
        "known_exchange_required": True,
        "raw_response_receipt_required": True,
        "executable_fill_claim": False,
    },
    "cost": {
        "fee_per_side_usd": FEE_PER_SIDE_USD_STR,
        "multiplier": MULTIPLIER,
        "return_formula": (
            "100*((100*exit_bid-0.65)-(100*entry_ask+0.65))/(100*entry_ask+0.65)"
        ),
        "cost_interpretation": (
            "frozen_research_quote_ruler_not_actual_account_fee_or_fill"
        ),
    },
    "clock": {
        "same_nyse_rth_session_required": True,
        "entry_never_precedes_expression_availability": True,
        "retrieval_after_maturity_allowed": True,
        "actual_retrieval_available_at_recorded": True,
        "benchmark_live_capture_lag_rule_inherited": False,
    },
    "status_vocabulary": [
        STATUS_PENDING,
        STATUS_COMPLETE,
        STATUS_UNAVAILABLE,
        STATUS_EXCLUDED,
        STATUS_INVALID,
    ],
    "forbidden_substitutes": [
        "mid",
        "last",
        "eod_mark",
        "intrinsic",
        "black_scholes",
        "neighbor_contract",
        "underlying_return",
        "later_best_print",
    ],
    "authority": {
        "may_originate_signal": False,
        "may_score": False,
        "may_rank": False,
        "may_select": False,
        "may_issue": False,
        "may_size": False,
        "may_trade": False,
        "may_publish_pick": False,
        "may_train_prophet": False,
        "may_feed_neural_web": False,
        "may_claim_fill": False,
    },
}
_FROZEN_POLICY_BYTES: bytes = cohort.canonical_json_bytes(_FROZEN_POLICY_DICT)
_FROZEN_POLICY_COMPUTED_SHA: str = sha256(_FROZEN_POLICY_BYTES).hexdigest()
if _FROZEN_POLICY_COMPUTED_SHA != FROZEN_POLICY_SHA256:
    raise AssertionError(
        "OA-3 frozen policy bytes drifted from pinned SHA256 "
        f"({_FROZEN_POLICY_COMPUTED_SHA} != {FROZEN_POLICY_SHA256}); the "
        "FROZEN_POLICY_SHA256 constant must be updated only via a new "
        "preregistration, never by hand-editing source"
    )
FROZEN_POLICY: Mapping[str, Any] = MappingProxyType(dict(_FROZEN_POLICY_DICT))

ALL_FALSE_AUTHORITY: Mapping[str, bool] = MappingProxyType(
    {key: bool(value) for key, value in FROZEN_POLICY["authority"].items()}
)

EXCLUDED_REASONS: frozenset[str] = frozenset(
    {
        "SAME_DAY_EXPIRATION",
        "EXPRESSION_CONTRACT_EXPIRED",
        "NON_STANDARD_DELIVERABLE",
        "NON_STANDARD_MULTIPLIER",
        "QUANTITY_NOT_ONE",
        "POSITION_NOT_LONG",
        "PACKAGE_NOT_SUPPORTED",
        "SHORT_OPTION_NOT_SUPPORTED",
        "HORIZON_CROSSES_SESSION_CLOSE",
        "ENTRY_BOUNDARY_OUTSIDE_RTH",
        "EXIT_BOUNDARY_OUTSIDE_RTH",
        "EXPRESSION_DATE_NOT_NYSE_SESSION",
        "EXPRESSION_FENCE_BROKEN",
    }
)

UNAVAILABLE_REASONS: frozenset[str] = frozenset(
    {
        "ENTRY_QUOTE_UNAVAILABLE",
        "EXIT_QUOTE_UNAVAILABLE",
        "SOURCE_UNAVAILABLE",
        "QUOTE_RESPONSE_INVALID",
        "RAW_BYTES_PAYLOAD_MISMATCH",
        "EVIDENCE_INTEGRITY_FAILURE",
    }
)

INVALID_REASONS: frozenset[str] = frozenset(
    {
        "EXPRESSION_IDENTITY_MALFORMED",
        "EXPRESSION_POLICY_VERSION_MISMATCH",
        "EXPRESSION_DIGEST_MISMATCH",
        "EXPRESSION_IMMUTABLE_FIELDS_MISSING",
        "EXPRESSION_SELECTION_FENCE_NOT_FROZEN",
        "EXPRESSION_FENCE_ORDER_VIOLATED",
        "CAUSAL_CLOCK_MISMATCH",
        "EXPRESSION_NOT_FROZEN_BEFORE_OUTCOME",
        "EVIDENCE_RAW_BYTES_MALFORMED",
        "EVIDENCE_QUERY_MISMATCH",
        "EVIDENCE_ROLE_MISMATCH",
        "EVIDENCE_CLOCK_INTEGRITY_FAILURE",
        "EVIDENCE_COMPUTED_BEFORE_RETRIEVAL",
        "EVIDENCE_SELECTED_EVENT_FUTURE",
    }
)


class Oa3InputError(ValueError):
    """An OA-3 expression receipt, raw quote bytes, or clock is malformed."""


class Oa3ExcludedError(Oa3InputError):
    """The expression is outside the v1 measurement domain."""


class Oa3InvalidError(Oa3InputError):
    """The expression or its receipts violate immutable identity / clock / receipt law."""


# ─── Expression receipt ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class ExpressionReceipt:
    """Frozen upstream expression receipt: exact raw bytes + parsed payload + upstream digest.

    The wrapper holds three views:

    * ``raw_bytes`` — exact upstream bytes, preserved verbatim so the record can
      carry their SHA-256 and byte count separately from the canonical payload.
    * ``parsed_payload`` — strictly parsed JSON value of the raw bytes; the
      two views must agree view-for-view (no caller-claimed payload allowed).
    * ``upstream_digest_sha256`` — caller-supplied SHA-256 over the canonical
      immutable expression fields; this is the upstream frozen identity the
      evaluator compares against and the binding the record rejects on mismatch
      (``EXPRESSION_DIGEST_MISMATCH``).

    The constructor deep-copies all caller views into a stable, mutable-immune
    form so a caller cannot mutate the receipt's parsed payload or raw bytes
    after the fact and silently re-evaluate; the evaluator revalidates the
    digest binding at the evaluate boundary regardless.
    """

    raw_bytes: bytes
    parsed_payload: Mapping[str, Any]
    upstream_digest_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.raw_bytes, bytes) or len(self.raw_bytes) == 0:
            raise Oa3InputError("expression receipt raw_bytes must be non-empty bytes")
        # Deep-freeze raw bytes: bytes are immutable; if the caller passed a
        # bytearray, accept it but copy into a fresh immutable bytes.
        if type(self.raw_bytes) is not bytes:
            object.__setattr__(self, "raw_bytes", bytes(self.raw_bytes))
        if not isinstance(self.parsed_payload, Mapping):
            raise Oa3InputError("expression receipt parsed_payload must be a mapping")
        # Deep-freeze parsed_payload so caller mutations cannot corrupt the
        # receipt: copy.deepcopy on a Mapping produces a stable view.
        object.__setattr__(
            self, "parsed_payload", MappingProxyType(_copy.deepcopy(dict(self.parsed_payload)))
        )
        if not (
            isinstance(self.upstream_digest_sha256, str)
            and len(self.upstream_digest_sha256) == 64
            and all(ch in "0123456789abcdef" for ch in self.upstream_digest_sha256)
        ):
            raise Oa3InvalidError(
                "expression receipt upstream_digest_sha256 must be a 64-char lowercase hex digest"
            )
        # Re-parse raw_bytes strictly and require view-equality to the payload
        # the caller passed: a receipt whose raw bytes and parsed payload
        # disagree is a contract violation, not a JSON whitespace variant.
        try:
            parsed_from_bytes = cohort.strict_json_value(
                self.raw_bytes, label="expression receipt raw_bytes"
            )
        except cohort.NbboCohortError as exc:
            raise Oa3InvalidError(
                f"expression receipt raw_bytes are not strict JSON: {exc}"
            ) from exc
        if not isinstance(parsed_from_bytes, Mapping):
            raise Oa3InvalidError(
                "expression receipt raw_bytes must parse to a JSON object"
            )
        if dict(parsed_from_bytes) != dict(self.parsed_payload):
            raise Oa3InvalidError(
                "expression receipt parsed_payload disagrees with raw_bytes"
            )
        # Require meaningful expression_id / source_candidate_id — a receipt
        # carrying empty / whitespace strings or non-strings for the upstream
        # identity fields is malformed upstream and must be rejected.
        for identity_field in ("expression_id", "source_candidate_id"):
            value = self.parsed_payload.get(identity_field)
            if not isinstance(value, str) or not value.strip():
                raise Oa3InvalidError(
                    f"expression receipt {identity_field!r} must be a non-empty string"
                )

    @property
    def raw_sha256(self) -> str:
        """SHA-256 of the exact raw bytes (not the canonical payload)."""

        return sha256(self.raw_bytes).hexdigest()

    @property
    def raw_size(self) -> int:
        """Byte count of the exact raw upstream payload."""

        return len(self.raw_bytes)


def expression_receipt_from_bytes(
    raw_bytes: bytes, upstream_digest_sha256: str
) -> ExpressionReceipt:
    """Build an ``ExpressionReceipt`` from raw upstream bytes."""

    try:
        parsed = cohort.strict_json_value(raw_bytes, label="expression receipt bytes")
    except cohort.NbboCohortError as exc:
        raise Oa3InvalidError(
            f"expression receipt bytes are not strict JSON: {exc}"
        ) from exc
    if not isinstance(parsed, Mapping):
        raise Oa3InvalidError(
            "expression receipt bytes must parse to a JSON object"
        )
    return ExpressionReceipt(
        raw_bytes=raw_bytes,
        parsed_payload=parsed,
        upstream_digest_sha256=upstream_digest_sha256,
    )


# ─── Per-role quote evidence ─────────────────────────────────────────────────


@dataclass(frozen=True)
class QuoteEvidence:
    """Per-role private-source evidence: query, raw bytes, payload, clocks.

    Each role (``entry`` / ``exit``) carries its own evidence so that the
    exact query sent to the source, the raw private bytes received, the
    strictly parsed payload, and the live retrieval clocks are all bound to
    the role they were observed under.  Two views are preserved:

    * ``raw_bytes`` — exact private HTTP body, hashed separately so a JSON
      whitespace / key-order variation produces a different raw digest but the
      same parsed payload.
    * ``parsed_payload`` — strictly parsed JSON array; ``None`` if and only if
      ``raw_bytes`` failed strict JSON validation.  In that case the source is
      malformed and the evaluator emits ``QUOTE_RESPONSE_INVALID`` unavailability
      (NOT an integrity failure).  Raw bytes are NOT required to equal the
      canonical serialisation of the parsed payload; only to parse to it when
      parsing succeeds.

    Clock causality must hold inside the evidence
    (``request_started_at <= response_observed_at <= retrieval_observed_at
    <= computed_at``) and is enforced by ``__post_init__`` regardless of
    whether parsing succeeded.

    The constructor deep-freezes raw bytes, parsed payload, contract, and
    query, and re-validates every causal clock at evaluate (a frozen dataclass
    only prevents reassignment, not mutation of nested Mapping / list values).
    """

    role: str
    contract: Mapping[str, Any]
    boundary_at: _datetime_cls
    query_end_at: _datetime_cls
    query: Mapping[str, Any]
    raw_bytes: bytes
    parsed_payload: Sequence[Mapping[str, Any]] | None
    parse_error: str | None
    endpoint: str
    request_started_at: _datetime_cls
    response_observed_at: _datetime_cls
    retrieval_observed_at: _datetime_cls
    computed_at: _datetime_cls

    def __post_init__(self) -> None:
        if self.role not in {ROLE_ENTRY, ROLE_EXIT}:
            raise Oa3InvalidError(
                f"quote evidence role must be {ROLE_ENTRY!r} or {ROLE_EXIT!r}; got {self.role!r}"
            )
        # raw_bytes must be present; a missing byte payload is malformed.
        if not isinstance(self.raw_bytes, bytes) or len(self.raw_bytes) == 0:
            raise Oa3InvalidError(
                "quote evidence raw_bytes must be non-empty bytes"
            )
        if type(self.raw_bytes) is not bytes:
            object.__setattr__(self, "raw_bytes", bytes(self.raw_bytes))
        # Deep-freeze contract and query mappings: the caller must not be able
        # to mutate them post-construction.  parsed_payload is deep-copied
        # below when parsing succeeds.
        object.__setattr__(
            self, "contract", MappingProxyType(_copy.deepcopy(dict(self.contract)))
        )
        object.__setattr__(
            self, "query", MappingProxyType(_copy.deepcopy(dict(self.query)))
        )
        # Endpoint must equal the cohort's frozen source endpoint identity.
        if not isinstance(self.endpoint, str) or self.endpoint != cohort.SOURCE_ENDPOINT:
            raise Oa3InvalidError(
                f"oa3 {self.role} quote evidence endpoint must equal "
                f"{cohort.SOURCE_ENDPOINT!r}; got {self.endpoint!r}"
            )
        # Query keyset must be EXACTLY the cohort query keyset — no extra,
        # no missing fields.
        if set(self.query) != cohort._QUERY_FIELDS:
            raise Oa3InvalidError(
                f"oa3 {self.role} quote evidence query keyset is not exact: "
                f"missing={sorted(cohort._QUERY_FIELDS - set(self.query))} "
                f"extra={sorted(set(self.query) - cohort._QUERY_FIELDS)}"
            )
        # Strict clock causality inside the evidence (always enforced, even
        # when raw bytes are malformed).  Naive datetimes are REJECTED — we
        # never infer a timezone; the analyst must specify tzinfo.
        for clock_name in (
            "boundary_at",
            "query_end_at",
            "request_started_at",
            "response_observed_at",
            "retrieval_observed_at",
            "computed_at",
        ):
            value = getattr(self, clock_name)
            if not isinstance(value, _datetime_cls):
                raise Oa3InvalidError(
                    f"oa3 {self.role} {clock_name} must be a datetime"
                )
            if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
                raise Oa3InvalidError(
                    f"oa3 {self.role} {clock_name} is naive; timezone-aware required"
                )
        if self.request_started_at > self.response_observed_at:
            raise Oa3InvalidError(
                "EVIDENCE_CLOCK_INTEGRITY_FAILURE: request_started_at follows response_observed_at"
            )
        if self.response_observed_at > self.retrieval_observed_at:
            raise Oa3InvalidError(
                "EVIDENCE_CLOCK_INTEGRITY_FAILURE: response_observed_at follows retrieval_observed_at"
            )
        if self.retrieval_observed_at > self.computed_at:
            raise Oa3InvalidError(
                "EVIDENCE_COMPUTED_BEFORE_RETRIEVAL: retrieval_observed_at follows computed_at"
            )
        # Preserve the caller-provided parsed view until it is checked against
        # the exact raw response. A direct constructor must not substitute a
        # convenient payload for bytes the source did not send.
        supplied_payload = self.parsed_payload
        # Strict JSON parse. On failure, parsed_payload must be None and
        # parse_error must carry the label; the wrapper must NOT fabricate
        # a parsed_payload from the empty default.  This is the load-bearing
        # distinction between QUOTE_RESPONSE_INVALID (unavailable) and
        # EVIDENCE_RAW_BYTES_MALFORMED (invalid integrity).
        try:
            parsed_from_bytes = cohort.strict_json_value(
                self.raw_bytes, label=f"oa3 {self.role} quote raw bytes"
            )
        except cohort.NbboCohortError as exc:
            if supplied_payload is not None:
                raise Oa3InvalidError(
                    f"oa3 {self.role} quote parsed_payload disagrees with malformed raw_bytes"
                ) from exc
            object.__setattr__(self, "parse_error", f"QUOTE_RESPONSE_INVALID:{exc}")
            object.__setattr__(self, "parsed_payload", None)
        else:
            if not isinstance(parsed_from_bytes, list):
                if supplied_payload is not None:
                    raise Oa3InvalidError(
                        f"oa3 {self.role} quote parsed_payload disagrees with raw_bytes"
                    )
                object.__setattr__(
                    self, "parse_error",
                    f"QUOTE_RESPONSE_INVALID:not_a_json_array",
                )
                object.__setattr__(self, "parsed_payload", None)
            else:
                try:
                    supplied_normalized = (
                        [dict(item) for item in supplied_payload]
                        if supplied_payload is not None
                        else None
                    )
                except (TypeError, ValueError) as exc:
                    raise Oa3InvalidError(
                        f"oa3 {self.role} quote parsed_payload is not a sequence of mappings"
                    ) from exc
                if supplied_normalized != parsed_from_bytes:
                    raise Oa3InvalidError(
                        f"oa3 {self.role} quote parsed_payload disagrees with raw_bytes"
                    )
                # parsed_payload is parsed correctly; deep-freeze it.  Each
                # element is a MappingProxyType over a deep-copied dict so a
                # caller who fetches parsed_payload[0] cannot mutate the
                # stored state in place — only read it.
                object.__setattr__(
                    self,
                    "parsed_payload",
                    tuple(
                        MappingProxyType(_copy.deepcopy(dict(item)))
                        for item in parsed_from_bytes
                    ),
                )

    @property
    def raw_sha256(self) -> str:
        return sha256(self.raw_bytes).hexdigest()

    @property
    def raw_size(self) -> int:
        return len(self.raw_bytes)

    @property
    def canonical_payload_sha256(self) -> str:
        if self.parsed_payload is None:
            return ""
        return sha256(
            cohort.canonical_json_bytes([dict(item) for item in self.parsed_payload])
        ).hexdigest()

    @property
    def canonical_payload_size(self) -> int:
        if self.parsed_payload is None:
            return 0
        return len(
            cohort.canonical_json_bytes([dict(item) for item in self.parsed_payload])
        )


def quote_evidence_from_bytes(
    *,
    role: str,
    contract: Mapping[str, Any],
    boundary_at: _datetime_cls,
    query_end_at: _datetime_cls,
    query: Mapping[str, Any],
    raw_bytes: bytes,
    request_started_at: _datetime_cls,
    response_observed_at: _datetime_cls,
    retrieval_observed_at: _datetime_cls,
    computed_at: _datetime_cls,
    endpoint: str = cohort.SOURCE_ENDPOINT,
) -> QuoteEvidence:
    """Build ``QuoteEvidence`` from raw source bytes and explicit clocks.

    The wrapper parses raw_bytes strictly; on JSON failure the resulting
    evidence carries ``parsed_payload=None`` and ``parse_error`` describing
    the failure so the evaluator can emit ``QUOTE_RESPONSE_INVALID``
    unavailability rather than an integrity-invalid record.
    """

    if role not in {ROLE_ENTRY, ROLE_EXIT}:
        raise Oa3InvalidError(
            f"quote evidence role must be {ROLE_ENTRY!r} or {ROLE_EXIT!r}; got {role!r}"
        )
    try:
        parsed = cohort.strict_json_value(raw_bytes, label=f"oa3 {role} quote bytes")
    except cohort.NbboCohortError as exc:
        parse_error = f"QUOTE_RESPONSE_INVALID:{exc}"
        parsed_payload = None
    else:
        if not isinstance(parsed, list):
            parse_error = "QUOTE_RESPONSE_INVALID:not_a_json_array"
            parsed_payload = None
        else:
            parse_error = None
            parsed_payload = parsed
    return QuoteEvidence(
        role=role,
        contract=dict(contract),
        boundary_at=boundary_at,
        query_end_at=query_end_at,
        query=dict(query),
        raw_bytes=raw_bytes,
        parsed_payload=parsed_payload,
        parse_error=parse_error,
        endpoint=endpoint,
        request_started_at=request_started_at,
        response_observed_at=response_observed_at,
        retrieval_observed_at=retrieval_observed_at,
        computed_at=computed_at,
    )


# ─── Expression validation helpers ───────────────────────────────────────────


def _require_str(receipt: Mapping[str, Any], field: str) -> str:
    value = receipt.get(field)
    if not isinstance(value, str) or not value:
        raise Oa3InvalidError(
            f"expression receipt {field!r} is missing or non-string"
        )
    return value


def _parse_clock(value: Any, *, label: str) -> _datetime_cls:
    if not isinstance(value, str) or not value:
        raise Oa3InvalidError(f"{label} must be an ISO datetime string")
    try:
        parsed = _datetime_cls.fromisoformat(value)
    except ValueError as exc:
        raise Oa3InvalidError(f"{label} is not ISO datetime: {exc}") from exc
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        raise Oa3InvalidError(
            f"{label} is naive; timezone-aware required"
        )
    return parsed.astimezone(UTC)


def _coerce_clock(value: Any, *, label: str) -> _datetime_cls:
    if isinstance(value, _datetime_cls):
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise Oa3InvalidError(
                f"{label} is naive; timezone-aware required"
            )
        return value.astimezone(UTC)
    return _parse_clock(value, label=label)


def _require_int(receipt: Mapping[str, Any], field: str) -> int:
    """Require an integer value, refusing bool-as-int and string-as-int.

    A receipt that encodes ``quantity_contracts`` / ``multiplier`` / ``strike``
    as ``True`` / ``False`` or ``"1"`` is silently coerced to ``1`` by a
    permissive validator; that is exactly how a v1 quantity / multiplier
    drift could ship unnoticed.  Refuse any non-true-int.
    """

    value = receipt.get(field)
    if isinstance(value, bool):
        raise Oa3InvalidError(
            f"expression receipt {field!r} is bool; int required"
        )
    if not isinstance(value, int):
        raise Oa3InvalidError(
            f"expression receipt {field!r} must be int; got {type(value).__name__}"
        )
    return value


def _canonical_expression_fields(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Canonical form used for the immutable expression-digest hash."""

    return {
        "expression_id": receipt["expression_id"],
        "policy_version": receipt["policy_version"],
        "source_candidate_id": receipt["source_candidate_id"],
        "decision_receipt_sha256": receipt["decision_receipt_sha256"],
        "source_rule_digest_sha256": receipt["source_rule_digest_sha256"],
        "selection_frozen_before_outcomes": receipt["selection_frozen_before_outcomes"],
        "selection_fence_at": receipt["selection_fence_at"],
        "root": receipt["root"],
        "expiration": receipt["expiration"],
        "right": receipt["right"],
        "strike": receipt["strike"],
        "strike_millis": receipt["strike_millis"],
        "occ_symbol": receipt["occ_symbol"],
        "position": receipt["position"],
        "quantity_contracts": receipt["quantity_contracts"],
        "multiplier": receipt["multiplier"],
        "standard_deliverable": receipt["standard_deliverable"],
        "single_leg": receipt["single_leg"],
        "package": receipt["package"],
        "decision_at": receipt["decision_at"],
        "available_at": receipt["available_at"],
    }


def _validate_expression_payload(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the canonical immutable fields of one OA expression receipt.

    Returns the canonical form plus pre-parsed clocks / contract.  Raises
    ``Oa3InvalidError`` for identity / fence / clock-law defects and
    ``Oa3ExcludedError`` for population defects (the v1 domain only).
    """

    if not isinstance(receipt, Mapping):
        raise Oa3InvalidError("expression receipt payload must be a mapping")
    required = {
        "expression_id",
        "policy_version",
        "source_candidate_id",
        "decision_receipt_sha256",
        "source_rule_digest_sha256",
        "selection_frozen_before_outcomes",
        "selection_fence_at",
        "root",
        "expiration",
        "right",
        "strike",
        "strike_millis",
        "occ_symbol",
        "position",
        "quantity_contracts",
        "multiplier",
        "standard_deliverable",
        "single_leg",
        "package",
        "decision_at",
        "available_at",
    }
    missing = sorted(required - set(receipt))
    if missing:
        raise Oa3InvalidError(
            "expression receipt is missing immutable fields: " + ", ".join(missing)
        )

    policy_version = receipt.get("policy_version")
    if not isinstance(policy_version, str) or not policy_version:
        raise Oa3InvalidError("expression policy_version is missing")
    if not policy_version.startswith("v"):
        raise Oa3InvalidError("expression policy_version must be a v-prefixed tag")
    if policy_version != FROZEN_POLICY_VERSION:
        raise Oa3InvalidError("EXPRESSION_POLICY_VERSION_MISMATCH")

    for digest_field in (
        "decision_receipt_sha256",
        "source_rule_digest_sha256",
    ):
        digest = receipt[digest_field]
        if not (
            isinstance(digest, str)
            and len(digest) == 64
            and all(ch in "0123456789abcdef" for ch in digest)
        ):
            raise Oa3InvalidError(
                f"expression {digest_field!r} must be a 64-character lowercase hex digest"
            )

    if receipt.get("selection_frozen_before_outcomes") is not True:
        raise Oa3InvalidError("EXPRESSION_SELECTION_FENCE_NOT_FROZEN")

    selection_fence_at = _coerce_clock(
        receipt["selection_fence_at"], label="expression.selection_fence_at"
    )

    contract = {
        "root": _require_str(receipt, "root"),
        "expiration": _require_str(receipt, "expiration"),
        "right": _require_str(receipt, "right"),
        "strike": _require_str(receipt, "strike"),
        "strike_millis": _require_int(receipt, "strike_millis"),
        "occ_symbol": _require_str(receipt, "occ_symbol"),
    }
    try:
        contract = cohort.validate_contract(contract)
    except cohort.NbboCohortError as exc:
        raise Oa3InvalidError(
            f"expression contract identity is invalid: {exc}"
        ) from exc

    # quantity / multiplier / strike_millis are integers, not bools (Ruling B:
    # no bool-as-int).  Compare against the frozen constants via strict-int
    # equality.
    quantity_contracts = _require_int(receipt, "quantity_contracts")
    multiplier = _require_int(receipt, "multiplier")
    if quantity_contracts != QUANTITY_CONTRACTS:
        raise Oa3ExcludedError("QUANTITY_NOT_ONE")
    if multiplier != MULTIPLIER:
        raise Oa3ExcludedError("NON_STANDARD_MULTIPLIER")
    position = receipt.get("position")
    if not isinstance(position, str):
        raise Oa3InvalidError("expression.position must be a string")
    if position != "long":
        raise Oa3ExcludedError("SHORT_OPTION_NOT_SUPPORTED")
    if receipt.get("single_leg") is not True:
        raise Oa3ExcludedError("PACKAGE_NOT_SUPPORTED")
    if receipt.get("package") is not False:
        raise Oa3ExcludedError("PACKAGE_NOT_SUPPORTED")
    if receipt.get("standard_deliverable") is not True:
        raise Oa3ExcludedError("NON_STANDARD_DELIVERABLE")

    decision_at = _coerce_clock(receipt["decision_at"], label="expression.decision_at")
    available_at = _coerce_clock(
        receipt["available_at"], label="expression.available_at"
    )
    if available_at < decision_at:
        raise Oa3InvalidError(
            "expression available_at precedes decision_at (causal clock mismatch)"
        )
    if selection_fence_at > decision_at:
        raise Oa3InvalidError(
            "EXPRESSION_FENCE_ORDER_VIOLATED: selection_fence_at must precede decision_at"
        )

    available_et_date = available_at.astimezone(ET).date()
    try:
        expiration_date = _datetime_cls.strptime(
            receipt["expiration"], "%Y-%m-%d"
        ).date()
    except ValueError as exc:
        raise Oa3InvalidError("expression expiration is not YYYY-MM-DD") from exc
    # Ruling D: contract expiration BEFORE the session date is also invalid
    # (an expired contract cannot be traded today).  Same-day is excluded.
    if expiration_date < available_et_date:
        raise Oa3ExcludedError("EXPRESSION_CONTRACT_EXPIRED")
    if expiration_date == available_et_date:
        raise Oa3ExcludedError("SAME_DAY_EXPIRATION")

    if not nyse_calendar.is_session(available_et_date):
        raise Oa3ExcludedError("EXPRESSION_DATE_NOT_NYSE_SESSION")

    open_dt, close_dt = session_window_et(available_et_date)
    open_utc = open_dt.astimezone(UTC)
    close_utc = close_dt.astimezone(UTC)
    if not (open_utc <= available_at < close_utc):
        raise Oa3ExcludedError("ENTRY_BOUNDARY_OUTSIDE_RTH")

    # Pre-check: the entire 60-second entry window must lie STRICTLY BEFORE
    # the RTH session close (Ruling D: equality to close is also excluded).
    # An expression whose available_at+60s reaches OR crosses the session
    # close is excluded under HORIZON_CROSSES_SESSION_CLOSE BEFORE any quote
    # parsing — even if no entry quote is ever observed.
    if available_at + timedelta(seconds=ENTRY_WINDOW_SECONDS) >= close_utc:
        raise Oa3ExcludedError("HORIZON_CROSSES_SESSION_CLOSE")

    canonical = _canonical_expression_fields(receipt)
    canonical.update(
        {
            "contract": contract,
            "decision_at": decision_at,
            "available_at": available_at,
            "selection_fence_at": selection_fence_at,
            "session_date": available_et_date,
            "rth_open": open_utc,
            "rth_close": close_utc,
        }
    )
    return canonical


# ─── Helpers shared by validate and reject paths ──────────────────────────────


def _selected_quote_dict(quote: cohort.SourceQuote, *, side: str) -> dict[str, Any]:
    if side == SIDE_ASK:
        return {
            "event_at": quote.event_at,
            "price": quote.ask,
            "size": quote.ask_size,
            "exchange": quote.ask_exchange,
            "condition": quote.ask_condition,
        }
    if side == SIDE_BID:
        return {
            "event_at": quote.event_at,
            "price": quote.bid,
            "size": quote.bid_size,
            "exchange": quote.bid_exchange,
            "condition": quote.bid_condition,
        }
    raise Oa3InputError(f"unknown selected side: {side!r}")


def _validate_evidence_query(
    evidence: QuoteEvidence,
    *,
    canonical: dict[str, Any],
    expected_boundary_at: _datetime_cls,
    expected_window_end_at: _datetime_cls,
) -> None:
    """Confirm the evidence query matches the reusable source-query contract.

    Beyond self-consistency, this enforces three window-binding invariants:

    * ``evidence.boundary_at`` must equal the canonical expression's
      ``available_at`` (entry) or the admitted entry quote's ``event_at+60m``
      (exit).  The evaluator supplies ``expected_boundary_at``; the evidence
      boundary that disagrees is ``EVIDENCE_QUERY_MISMATCH``.
    * ``evidence.query_end_at`` must equal ``expected_boundary_at + 60s``;
      windows of any other length are rejected with the same reason.
    * The evidence ``query`` must rebuild the exact cohort source query under
      that boundary and request clock; the analyst cannot have actually sent
      the query they recorded if any field differs.

    Endpoint identity is bound by the ``QuoteEvidence`` constructor.
    """

    if evidence.boundary_at != expected_boundary_at:
        raise Oa3InvalidError(
            f"oa3 {evidence.role} evidence boundary_at disagrees with the "
            f"canonical window boundary ({evidence.boundary_at} != "
            f"{expected_boundary_at})"
        )
    if evidence.query_end_at != expected_window_end_at:
        raise Oa3InvalidError(
            f"oa3 {evidence.role} evidence query_end_at disagrees with the "
            f"canonical window end ({evidence.query_end_at} != "
            f"{expected_window_end_at})"
        )
    if evidence.request_started_at < evidence.boundary_at:
        raise Oa3InvalidError(
            f"oa3 {evidence.role} request_started_at precedes the contract boundary"
        )
    expected = cohort.source_query(
        contract=evidence.contract,
        boundary_at=evidence.boundary_at,
        available_at=evidence.request_started_at,
        ceiling_at=evidence.query_end_at,
    )
    observed = {key: str(evidence.query.get(key, "")) for key in expected}
    if observed != expected:
        raise Oa3InvalidError(
            f"oa3 {evidence.role} evidence query disagrees with the contract-bound source query contract"
        )


def _validate_evidence_selected_event(evidence: QuoteEvidence) -> _datetime_cls | None:
    """Return the evidence selected-event clock (none if no quote inside window).

    The selected event must lie inside the requested window and not exceed
    the analyst's retrieval clock; the analyst cannot have observed a quote
    timestamp they had not yet seen.  This is the load-bearing per-role
    invariant the ruling requires at the evaluate boundary, not only at
    construction.

    The ruling's "selected event after actual query end/request cannot be
    admitted" is enforced here: the selected event must satisfy
    ``boundary_at <= event_at <= query_end_at`` and must precede the
    retrieval clock.  It need not precede the response_observed_at clock —
    a streaming analyst may receive a partial response before the quote's
    server-side timestamp settles, and the load-bearing guard is on
    query-end + retrieval, not on response.
    """

    if evidence.parsed_payload is None:
        return None
    try:
        quote = cohort.parse_quote_response(
            [dict(item) for item in evidence.parsed_payload],
            role=evidence.role,
            contract=evidence.contract,
            boundary_at=evidence.boundary_at,
            query_end_at=evidence.query_end_at,
        )
    except (cohort.NbboSourceError, cohort.NbboCohortError):
        # Conflicting / malformed rows invalidate the candidate; do not raise
        # here — the evaluator's parse path will emit QUOTE_RESPONSE_INVALID.
        return None
    if quote is None:
        return None
    if quote.event_at > evidence.response_observed_at:
        raise Oa3InvalidError(
            "EVIDENCE_SELECTED_EVENT_FUTURE: selected quote event_at exceeds response_observed_at"
        )
    if quote.event_at > evidence.retrieval_observed_at:
        raise Oa3InvalidError(
            "EVIDENCE_SELECTED_EVENT_FUTURE: selected quote event_at exceeds retrieval_observed_at"
        )
    return quote.event_at


def _parse_window_or_raise_unavailable(
    evidence: QuoteEvidence,
) -> tuple[cohort.SourceQuote | None, str | None]:
    """Parse one QuoteEvidence; map parser failure to ``QUOTE_RESPONSE_INVALID``."""

    if evidence.parsed_payload is None:
        # Malformed source JSON — bind raw SHA/size and emit QUOTE_RESPONSE_INVALID.
        return None, evidence.parse_error or "QUOTE_RESPONSE_INVALID"
    try:
        quote = cohort.parse_quote_response(
            [dict(item) for item in evidence.parsed_payload],
            role=evidence.role,
            contract=evidence.contract,
            boundary_at=evidence.boundary_at,
            query_end_at=evidence.query_end_at,
        )
    except cohort.NbboSourceError as exc:
        return None, f"QUOTE_RESPONSE_INVALID:{exc}"
    except cohort.NbboCohortError as exc:
        return None, f"QUOTE_RESPONSE_INVALID:{exc}"
    return quote, None


# ─── Evidence / window block builders ─────────────────────────────────────────


def _evidence_block(
    evidence: QuoteEvidence,
    *,
    quote: cohort.SourceQuote | None,
    parse_error: str | None,
) -> dict[str, Any]:
    raw_sha = evidence.raw_sha256
    canonical_sha = evidence.canonical_payload_sha256
    selected = _selected_quote_dict(quote, side=SIDE_ASK if evidence.role == ROLE_ENTRY else SIDE_BID) if quote is not None else None
    return {
        "role": evidence.role,
        "side": SIDE_ASK if evidence.role == ROLE_ENTRY else SIDE_BID,
        "query_bounds": {
            "start_at": evidence.boundary_at,
            "end_at": evidence.query_end_at,
        },
        "query": dict(evidence.query),
        "raw_response_sha256": raw_sha,
        "raw_response_bytes": evidence.raw_size,
        "raw_payload_sha256": canonical_sha,
        "raw_payload_bytes": evidence.canonical_payload_size,
        "selected": selected,
        "parse_error": parse_error,
        "clocks": {
            "request_started_at": evidence.request_started_at,
            "response_observed_at": evidence.response_observed_at,
            "retrieval_observed_at": evidence.retrieval_observed_at,
            "computed_at": evidence.computed_at,
        },
    }


def _empty_evidence_block(role: str) -> dict[str, Any]:
    side = SIDE_ASK if role == ROLE_ENTRY else SIDE_BID
    return {
        "role": role,
        "side": side,
        "query_bounds": None,
        "query": None,
        "raw_response_sha256": None,
        "raw_response_bytes": 0,
        "raw_payload_sha256": None,
        "raw_payload_bytes": 0,
        "selected": None,
        "parse_error": None,
        "clocks": {
            "request_started_at": None,
            "response_observed_at": None,
            "retrieval_observed_at": None,
            "computed_at": None,
        },
    }


# ─── Fixture record builders ─────────────────────────────────────────────────


def _map_invalid_reason(exc: Exception) -> str:
    """Map an exception to a closed invalid reason from the INVALID vocabulary."""

    text = str(exc)
    for candidate in INVALID_REASONS:
        if text.startswith(candidate):
            return candidate
    # Map known integrity classes that escape the literal prefix path:
    lowered = text.lower()
    if "causal clock" in lowered or "request_started_at" in lowered and "follows" in lowered:
        return "CAUSAL_CLOCK_MISMATCH"
    if "evidence_clock_integrity_failure" in lowered:
        return "EVIDENCE_CLOCK_INTEGRITY_FAILURE"
    if "evidence_computed_before_retrieval" in lowered:
        return "EVIDENCE_COMPUTED_BEFORE_RETRIEVAL"
    if "evidence_selected_event_future" in lowered:
        return "EVIDENCE_SELECTED_EVENT_FUTURE"
    if "evidence_query_mismatch" in lowered or "evidence query disagrees" in lowered:
        return "EVIDENCE_QUERY_MISMATCH"
    if "evidence" in lowered and "disagrees" in lowered and "canonical window boundary" in lowered:
        return "EVIDENCE_QUERY_MISMATCH"
    if "evidence" in lowered and "query_end_at disagrees" in lowered:
        return "EVIDENCE_QUERY_MISMATCH"
    if "evidence_role_mismatch" in lowered:
        return "EVIDENCE_ROLE_MISMATCH"
    if "expression_identity_malformed" in lowered:
        return "EXPRESSION_IDENTITY_MALFORMED"
    if "raw_bytes" in lowered and "invalid json" in lowered:
        return "EVIDENCE_RAW_BYTES_MALFORMED"
    if "disagrees with raw_bytes" in lowered:
        return "EVIDENCE_RAW_BYTES_MALFORMED"
    # Final catch-all: integrity defect without a closed reason — refuse
    # arbitrary caller labels.
    return "EXPRESSION_IDENTITY_MALFORMED"


def _map_unavailable_reason(text: str) -> str:
    for candidate in UNAVAILABLE_REASONS:
        if text.startswith(candidate):
            return candidate
    if "parse_error" in text:
        return "QUOTE_RESPONSE_INVALID"
    return "QUOTE_RESPONSE_INVALID"


def _map_excluded_reason(exc: Exception) -> str:
    text = str(exc)
    for candidate in EXCLUDED_REASONS:
        if text.startswith(candidate):
            return candidate
    # Unknown exclusion label — fall back to a known closed reason rather
    # than surfacing an arbitrary caller label.
    return "EXPRESSION_FENCE_BROKEN"


def _expression_digest(receipt_payload: Mapping[str, Any]) -> str:
    """Hash the canonical immutable expression fields only.

    The digest MUST be reproducible from the original receipt payload
    (string-valued, frozen upstream identity) and MUST NOT depend on any
    session / contract / datetime fields that ``_validate_expression_payload``
    augments after the fact.  The augmentations exist to drive the rest of
    the evaluation; the digest is the upstream-binding identity.
    """

    return sha256(
        cohort.canonical_json_bytes(_canonical_expression_fields(receipt_payload))
    ).hexdigest()


def _frozen_policy_block() -> dict[str, Any]:
    return {
        "policy_id": FROZEN_POLICY_ID,
        "policy_version": FROZEN_POLICY_VERSION,
        "policy_sha256": FROZEN_POLICY_SHA256,
    }


def _build_invalid_fixture(
    *,
    status: str,
    reason: str,
    canonical: dict[str, Any] | None,
    raw_expression: Mapping[str, Any] | None,
    entry_block: dict[str, Any],
    exit_block: dict[str, Any],
    expression_raw_sha: str | None,
    expression_raw_size: int | None,
    upstream_digest_sha: str | None,
) -> dict[str, Any]:
    if status == STATUS_INVALID and reason not in INVALID_REASONS:
        raise Oa3InputError(f"invalid reason {reason!r} is not in vocabulary")
    if status == STATUS_UNAVAILABLE and reason not in UNAVAILABLE_REASONS:
        raise Oa3InputError(f"unavailable reason {reason!r} is not in vocabulary")
    if status == STATUS_EXCLUDED and reason not in EXCLUDED_REASONS:
        raise Oa3InputError(f"excluded reason {reason!r} is not in vocabulary")
    if status in (STATUS_PENDING, STATUS_COMPLETE):
        raise Oa3InputError(
            f"status {status!r} must not be produced by the integrity reject path"
        )
    if status == STATUS_EXCLUDED and (canonical is None or raw_expression is None):
        # excluded before any quote observation; identity fields must still be
        # present from the raw receipt
        ...
    expression_id = ""
    source_candidate_id = ""
    decision_receipt_sha = ""
    source_rule_sha = ""
    selection_fence_at = ""
    policy_version = FROZEN_POLICY_VERSION
    expression_digest_sha = ""
    session_date = None
    rth_open = None
    rth_close = None
    decision_at = None
    available_at = None
    contract = None
    position = None
    quantity_contracts = None
    multiplier = None
    if canonical is not None:
        expression_id = canonical["expression_id"]
        source_candidate_id = canonical["source_candidate_id"]
        decision_receipt_sha = canonical["decision_receipt_sha256"]
        source_rule_sha = canonical["source_rule_digest_sha256"]
        selection_fence_at = canonical["selection_fence_at"]
        session_date = canonical["session_date"]
        rth_open = canonical["rth_open"]
        rth_close = canonical["rth_close"]
        decision_at = canonical["decision_at"]
        available_at = canonical["available_at"]
        contract = canonical["contract"]
        position = canonical["position"]
        quantity_contracts = canonical["quantity_contracts"]
        multiplier = canonical["multiplier"]
        expression_digest_sha = _expression_digest(raw_expression)
    elif raw_expression is not None:
        expression_id = str(raw_expression.get("expression_id", "")) if isinstance(
            raw_expression.get("expression_id"), str
        ) else ""
        source_candidate_id = (
            raw_expression["source_candidate_id"]
            if isinstance(raw_expression.get("source_candidate_id"), str)
            else ""
        )
        decision_receipt_sha = (
            raw_expression["decision_receipt_sha256"]
            if isinstance(raw_expression.get("decision_receipt_sha256"), str)
            else ""
        )
        source_rule_sha = (
            raw_expression["source_rule_digest_sha256"]
            if isinstance(raw_expression.get("source_rule_digest_sha256"), str)
            else ""
        )
        selection_fence_at = (
            raw_expression["selection_fence_at"]
            if isinstance(raw_expression.get("selection_fence_at"), str)
            else ""
        )
        contract = None
        position = raw_expression.get("position")
        quantity_contracts = raw_expression.get("quantity_contracts")
        multiplier = raw_expression.get("multiplier")

    record: dict[str, Any] = {
        "schema": SCHEMA,
        "policy_id": FROZEN_POLICY_ID,
        "policy_version": policy_version,
        "policy_sha256": FROZEN_POLICY_SHA256,
        "expression_id": expression_id,
        "expression_digest_sha256": expression_digest_sha,
        "expression_upstream_digest_sha256": upstream_digest_sha or "",
        "expression_raw_response_sha256": expression_raw_sha or "",
        "expression_raw_response_bytes": expression_raw_size or 0,
        "expression_source_candidate_id": source_candidate_id,
        "expression_decision_receipt_sha256": decision_receipt_sha,
        "expression_source_rule_digest_sha256": source_rule_sha,
        "selection_frozen_before_outcomes": bool(
            raw_expression.get("selection_frozen_before_outcomes")
            if raw_expression is not None
            else False
        ),
        "selection_fence_at": selection_fence_at,
        "contract": contract,
        "expression_decision_at": decision_at,
        "expression_available_at": available_at,
        "session_date": session_date.isoformat() if session_date is not None else None,
        "session_rth_open": rth_open,
        "session_rth_close": rth_close,
        "position": position,
        "quantity_contracts": quantity_contracts,
        "multiplier": multiplier,
        "status": status,
        "reason": reason,
        "entry": entry_block,
        "exit": exit_block,
        "net_return_pct": None,
        "cost": {
            "multiplier": MULTIPLIER,
            "fee_per_side_usd": FEE_PER_SIDE_USD_STR,
            "return_formula": (
                "100*((100*exit_bid-0.65)-(100*entry_ask+0.65))/(100*entry_ask+0.65)"
            ),
            "cost_interpretation": (
                "frozen_research_quote_ruler_not_actual_account_fee"
            ),
        },
        "quote_source": {
            "endpoint": cohort.SOURCE_ENDPOINT,
            "interval": cohort.SOURCE_INTERVAL,
            "quote_rule_id": cohort.QUOTE_RULE_ID,
            "exact_contract_required": True,
            "firm_condition_required": True,
            "known_exchange_required": True,
            "raw_response_receipt_required": True,
            "executable_fill_claim": False,
        },
        "authority": {key: value for key, value in ALL_FALSE_AUTHORITY.items()},
    }
    return record


def _build_complete_fixture(
    *,
    canonical: dict[str, Any],
    receipt_payload: Mapping[str, Any],
    entry_evidence: QuoteEvidence,
    exit_evidence: QuoteEvidence,
    entry_quote: cohort.SourceQuote,
    exit_quote: cohort.SourceQuote,
    net_return: Decimal,
) -> dict[str, Any]:
    expression_digest_sha = _expression_digest(receipt_payload)
    entry_block = _evidence_block(
        entry_evidence, quote=entry_quote, parse_error=None
    )
    exit_block = _evidence_block(
        exit_evidence, quote=exit_quote, parse_error=None
    )
    return {
        "schema": SCHEMA,
        "policy_id": FROZEN_POLICY_ID,
        "policy_version": FROZEN_POLICY_VERSION,
        "policy_sha256": FROZEN_POLICY_SHA256,
        "expression_id": canonical["expression_id"],
        "expression_digest_sha256": expression_digest_sha,
        "expression_upstream_digest_sha256": "",  # filled by evaluate()
        "expression_raw_response_sha256": "",
        "expression_raw_response_bytes": 0,
        "expression_source_candidate_id": canonical["source_candidate_id"],
        "expression_decision_receipt_sha256": canonical["decision_receipt_sha256"],
        "expression_source_rule_digest_sha256": canonical["source_rule_digest_sha256"],
        "selection_frozen_before_outcomes": True,
        "selection_fence_at": canonical["selection_fence_at"],
        "contract": canonical["contract"],
        "expression_decision_at": canonical["decision_at"],
        "expression_available_at": canonical["available_at"],
        "session_date": canonical["session_date"].isoformat(),
        "session_rth_open": canonical["rth_open"],
        "session_rth_close": canonical["rth_close"],
        "position": canonical["position"],
        "quantity_contracts": canonical["quantity_contracts"],
        "multiplier": canonical["multiplier"],
        "status": STATUS_COMPLETE,
        "reason": None,
        "entry": entry_block,
        "exit": exit_block,
        "net_return_pct": net_return,
        "cost": {
            "multiplier": MULTIPLIER,
            "fee_per_side_usd": FEE_PER_SIDE_USD_STR,
            "return_formula": (
                "100*((100*exit_bid-0.65)-(100*entry_ask+0.65))/(100*entry_ask+0.65)"
            ),
            "cost_interpretation": (
                "frozen_research_quote_ruler_not_actual_account_fee"
            ),
        },
        "quote_source": {
            "endpoint": cohort.SOURCE_ENDPOINT,
            "interval": cohort.SOURCE_INTERVAL,
            "quote_rule_id": cohort.QUOTE_RULE_ID,
            "exact_contract_required": True,
            "firm_condition_required": True,
            "known_exchange_required": True,
            "raw_response_receipt_required": True,
            "executable_fill_claim": False,
        },
        "authority": {key: value for key, value in ALL_FALSE_AUTHORITY.items()},
    }


def _build_pending_fixture(
    *,
    canonical: dict[str, Any],
    receipt_payload: Mapping[str, Any],
    entry_evidence: QuoteEvidence | None,
    exit_evidence: QuoteEvidence | None,
    entry_block: dict[str, Any],
    exit_block: dict[str, Any],
) -> dict[str, Any]:
    expression_digest_sha = _expression_digest(receipt_payload)
    record = _build_complete_fixture(
        canonical=canonical,
        receipt_payload=receipt_payload,
        entry_evidence=entry_evidence or _placeholder_evidence_for_block(ROLE_ENTRY, canonical),
        exit_evidence=exit_evidence or _placeholder_evidence_for_block(ROLE_EXIT, canonical),
        entry_quote=cohort.SourceQuote(
            event_at=canonical["available_at"],
            bid=Decimal(0),
            ask=Decimal(0),
            bid_size=0,
            ask_size=0,
            bid_exchange=0,
            ask_exchange=0,
            bid_condition=0,
            ask_condition=0,
        ),
        exit_quote=cohort.SourceQuote(
            event_at=canonical["available_at"],
            bid=Decimal(0),
            ask=Decimal(0),
            bid_size=0,
            ask_size=0,
            bid_exchange=0,
            ask_exchange=0,
            bid_condition=0,
            ask_condition=0,
        ),
        net_return=Decimal(0),
    )
    record["status"] = STATUS_PENDING
    record["reason"] = None
    record["entry"] = entry_block
    record["exit"] = exit_block
    record["net_return_pct"] = None
    return record


def _bind_expression_receipt(
    record: dict[str, Any],
    *,
    upstream_digest_sha: str,
    raw_sha: str,
    raw_size: int,
) -> dict[str, Any]:
    """Attach original ExpressionReceipt evidence to a record of any status."""

    record["expression_upstream_digest_sha256"] = upstream_digest_sha
    record["expression_raw_response_sha256"] = raw_sha
    record["expression_raw_response_bytes"] = raw_size
    return record


def _placeholder_evidence_for_block(
    role: str, canonical: dict[str, Any]
) -> QuoteEvidence:
    """Build a sentinel evidence whose only purpose is to populate the clocks
    of a pending fixture; the record's entry/exit blocks carry the canonical
    block shape and the caller's evidence, not this sentinel."""

    return QuoteEvidence(
        role=role,
        contract=canonical["contract"],
        boundary_at=canonical["available_at"],
        query_end_at=canonical["available_at"],
        query={"symbol": "", "expiration": "", "strike": "", "right": "", "date": "", "start_time": "", "end_time": "", "interval": "", "format": ""},
        raw_bytes=b"[]",
        parsed_payload=[],
        request_started_at=canonical["available_at"],
        response_observed_at=canonical["available_at"],
        retrieval_observed_at=canonical["available_at"],
        computed_at=canonical["available_at"],
    )


# ─── Evaluate ────────────────────────────────────────────────────────────────


def evaluate(
    expression: ExpressionReceipt,
    *,
    entry_evidence: QuoteEvidence,
    exit_evidence: QuoteEvidence,
) -> dict[str, Any]:
    """Evaluate one exact OA expression under the OA-3 v1 ruler.

    Parameters
    ----------
    expression:
        The frozen OA expression.  Must be an ``ExpressionReceipt`` carrying
        raw upstream bytes + caller-bound upstream digest; bare bytes /
        parsed mappings are no longer accepted (Ruling G: no inventing raw
        provenance).
    entry_evidence, exit_evidence:
        Per-role private-source evidence.  Each carries the exact source
        query, raw private bytes, strictly parsed payload, and independent
        request / response / retrieval / computed clocks.

    Returns
    -------
    dict
        The OA-3 fixture record.  No raw quote rows / payload / PnL claim
        appears in the output; ``net_return_pct`` is populated only when the
        status is ``complete`` and the frozen one-contract USD 0.65/side
        arithmetic is reproducible.
    """

    if not isinstance(entry_evidence, QuoteEvidence):
        raise Oa3InputError(
            "entry_evidence must be a QuoteEvidence instance"
        )
    if not isinstance(exit_evidence, QuoteEvidence):
        raise Oa3InputError(
            "exit_evidence must be a QuoteEvidence instance"
        )
    if entry_evidence.role != ROLE_ENTRY:
        raise Oa3InputError(
            f"entry_evidence role must be {ROLE_ENTRY!r}; got {entry_evidence.role!r}"
        )
    if exit_evidence.role != ROLE_EXIT:
        raise Oa3InputError(
            f"exit_evidence role must be {ROLE_EXIT!r}; got {exit_evidence.role!r}"
        )
    # The expression MUST be an ExpressionReceipt — bare bytes / Mapping
    # would invent raw provenance the evaluator cannot bind (Ruling G).
    if not isinstance(expression, ExpressionReceipt):
        raise Oa3InputError(
            "evaluate(expression=...) must be an ExpressionReceipt; bare bytes "
            "and Mapping inputs are refused (raw provenance would be invented)"
        )

    receipt = expression
    raw_expression = dict(receipt.parsed_payload)
    upstream_digest = receipt.upstream_digest_sha256
    expression_raw_sha = receipt.raw_sha256
    expression_raw_size = receipt.raw_size

    # Revalidate clocks, raw, payload at evaluate boundary (Ruling B: a
    # frozen dataclass prevents reassignment of fields but does NOT prevent
    # mutation of nested Mapping / list values).
    _revalidate_receipt_at_evaluate(receipt)

    # Validate the expression's immutable identity (raises on
    # invalid / excluded).  This is also where we verify the upstream
    # digest BEFORE outcomes are emitted (Ruling G).
    try:
        canonical = _validate_expression_payload(receipt.parsed_payload)
    except Oa3ExcludedError as exc:
        reason = _map_excluded_reason(exc)
        return _build_invalid_fixture(
            status=STATUS_EXCLUDED,
            reason=reason,
            canonical=None,
            raw_expression=raw_expression,
            entry_block=_empty_evidence_block(ROLE_ENTRY),
            exit_block=_empty_evidence_block(ROLE_EXIT),
            expression_raw_sha=expression_raw_sha,
            expression_raw_size=expression_raw_size,
            upstream_digest_sha=upstream_digest,
        )
    except Oa3InvalidError as exc:
        reason = _map_invalid_reason(exc)
        return _build_invalid_fixture(
            status=STATUS_INVALID,
            reason=reason,
            canonical=None,
            raw_expression=raw_expression,
            entry_block=_empty_evidence_block(ROLE_ENTRY),
            exit_block=_empty_evidence_block(ROLE_EXIT),
            expression_raw_sha=expression_raw_sha,
            expression_raw_size=expression_raw_size,
            upstream_digest_sha=upstream_digest,
        )

    # Confirm the upstream digest matches the canonical-immutable digest
    # BEFORE any outcome is emitted (Ruling G).
    computed_digest = _expression_digest(raw_expression)
    if upstream_digest != computed_digest:
        return _build_invalid_fixture(
            status=STATUS_INVALID,
            reason="EXPRESSION_DIGEST_MISMATCH",
            canonical=None,
            raw_expression=raw_expression,
            entry_block=_empty_evidence_block(ROLE_ENTRY),
            exit_block=_empty_evidence_block(ROLE_EXIT),
            expression_raw_sha=expression_raw_sha,
            expression_raw_size=expression_raw_size,
            upstream_digest_sha=upstream_digest,
        )

    # Validate entry evidence query contracts and clocks (Ruling A: window
    # boundary must equal canonical expression.available_at, window end must
    # equal +60s; reject wrong per-role windows even if the query is
    # self-consistent against cohort.source_query).
    entry_boundary_at = canonical["available_at"]
    entry_window_end = entry_boundary_at + timedelta(seconds=ENTRY_WINDOW_SECONDS)
    try:
        _validate_evidence_query(
            entry_evidence,
            canonical=canonical,
            expected_boundary_at=entry_boundary_at,
            expected_window_end_at=entry_window_end,
        )
        # Enforce per-role selected event ordering (Ruling B: dead-code
        # helper now wired into the live evaluate path for BOTH roles).
        _validate_evidence_selected_event(entry_evidence)
    except Oa3InvalidError as exc:
        reason = _map_invalid_reason(exc)
        return _build_invalid_fixture(
            status=STATUS_INVALID,
            reason=reason,
            canonical=canonical,
            raw_expression=raw_expression,
            entry_block=_empty_evidence_block(ROLE_ENTRY),
            exit_block=_empty_evidence_block(ROLE_EXIT),
            expression_raw_sha=expression_raw_sha,
            expression_raw_size=expression_raw_size,
            upstream_digest_sha=upstream_digest,
        )

    # Entry window maturity BEFORE terminal quote outcomes (Ruling C): if
    # the whole 60-second window has not elapsed at retrieval, the outcome
    # is pending regardless of whether a quote was observed.
    entry_quote_for_block: cohort.SourceQuote | None = None
    if entry_evidence.parsed_payload is not None:
        try:
            entry_quote_for_block = cohort.parse_quote_response(
                [dict(item) for item in entry_evidence.parsed_payload],
                role=ROLE_ENTRY,
                contract=entry_evidence.contract,
                boundary_at=entry_evidence.boundary_at,
                query_end_at=entry_evidence.query_end_at,
            )
        except (cohort.NbboSourceError, cohort.NbboCohortError):
            entry_quote_for_block = None
    if (
        entry_evidence.request_started_at < entry_window_end
        or entry_evidence.retrieval_observed_at < entry_window_end
    ):
        return _bind_expression_receipt(
            _build_pending_fixture(
                canonical=canonical,
                receipt_payload=raw_expression,
                entry_evidence=entry_evidence,
                exit_evidence=exit_evidence,
                entry_block=_evidence_block(
                    entry_evidence,
                    quote=entry_quote_for_block,
                    parse_error=None,
                ),
                exit_block=_empty_evidence_block(ROLE_EXIT),
            ),
            upstream_digest_sha=upstream_digest,
            raw_sha=expression_raw_sha,
            raw_size=expression_raw_size,
        )

    # Per-role contract must equal the expression contract
    if dict(entry_evidence.contract) != dict(canonical["contract"]):
        return _build_invalid_fixture(
            status=STATUS_INVALID,
            reason="EVIDENCE_QUERY_MISMATCH",
            canonical=canonical,
            raw_expression=raw_expression,
            entry_block=_empty_evidence_block(ROLE_ENTRY),
            exit_block=_empty_evidence_block(ROLE_EXIT),
            expression_raw_sha=expression_raw_sha,
            expression_raw_size=expression_raw_size,
            upstream_digest_sha=upstream_digest,
        )
    if dict(exit_evidence.contract) != dict(canonical["contract"]):
        return _build_invalid_fixture(
            status=STATUS_INVALID,
            reason="EVIDENCE_QUERY_MISMATCH",
            canonical=canonical,
            raw_expression=raw_expression,
            entry_block=_empty_evidence_block(ROLE_ENTRY),
            exit_block=_empty_evidence_block(ROLE_EXIT),
            expression_raw_sha=expression_raw_sha,
            expression_raw_size=expression_raw_size,
            upstream_digest_sha=upstream_digest,
        )

    # Fence ordering: selection_fence_at <= decision_at <= available_at <= entry.request_started_at
    if entry_evidence.request_started_at < canonical["available_at"]:
        return _build_invalid_fixture(
            status=STATUS_INVALID,
            reason="EXPRESSION_FENCE_ORDER_VIOLATED",
            canonical=canonical,
            raw_expression=raw_expression,
            entry_block=_empty_evidence_block(ROLE_ENTRY),
            exit_block=_empty_evidence_block(ROLE_EXIT),
            expression_raw_sha=expression_raw_sha,
            expression_raw_size=expression_raw_size,
            upstream_digest_sha=upstream_digest,
        )

    # Parse entry evidence
    entry_quote, entry_parse_error = _parse_window_or_raise_unavailable(entry_evidence)

    if entry_quote is None:
        # Window maturity test: if the entry window has NOT yet fully elapsed
        # (entry.query_end_at > retrieval_observed_at), status is pending.
        if entry_evidence.retrieval_observed_at < entry_evidence.query_end_at:
            return _build_pending_fixture(
                canonical=canonical,
                receipt_payload=raw_expression,
                entry_evidence=entry_evidence,
                exit_evidence=exit_evidence,
                entry_block=_evidence_block(
                    entry_evidence, quote=None, parse_error=entry_parse_error
                ),
                exit_block=_empty_evidence_block(ROLE_EXIT),
            )
        reason = _map_unavailable_reason(entry_parse_error or "ENTRY_QUOTE_UNAVAILABLE")
        return _build_invalid_fixture(
            status=STATUS_UNAVAILABLE,
            reason=reason,
            canonical=canonical,
            raw_expression=raw_expression,
            entry_block=_evidence_block(
                entry_evidence, quote=None, parse_error=entry_parse_error
            ),
            exit_block=_empty_evidence_block(ROLE_EXIT),
            expression_raw_sha=expression_raw_sha,
            expression_raw_size=expression_raw_size,
            upstream_digest_sha=upstream_digest,
        )

    # Selected event clock causality at the evaluate boundary (Ruling B):
    # selected_event must precede retrieval (analyst cannot have observed a
    # quote timestamped after they retrieved).  Response clock is NOT
    # compared — the load-bearing guard is on retrieval, and
    # _validate_evidence_selected_event already raises on retrieval violation.
    if entry_quote.event_at > entry_evidence.retrieval_observed_at:
        return _build_invalid_fixture(
            status=STATUS_INVALID,
            reason="EVIDENCE_SELECTED_EVENT_FUTURE",
            canonical=canonical,
            raw_expression=raw_expression,
            entry_block=_evidence_block(
                entry_evidence, quote=entry_quote, parse_error=None
            ),
            exit_block=_empty_evidence_block(ROLE_EXIT),
            expression_raw_sha=expression_raw_sha,
            expression_raw_size=expression_raw_size,
            upstream_digest_sha=upstream_digest,
        )

    # Compute exit target — actual entry.event_at + 60m (Ruling D), NEVER
    # expression.available_at + 60m.
    exit_target = entry_quote.event_at + EXIT_HORIZON
    exit_window_end = exit_target + timedelta(seconds=EXIT_WINDOW_SECONDS)
    rth_close = canonical["rth_close"]
    # The full exit window (entry.event_at + 60m, +60s) MUST lie strictly
    # BEFORE the session close (Ruling D).
    if exit_window_end >= rth_close:
        return _build_invalid_fixture(
            status=STATUS_EXCLUDED,
            reason="HORIZON_CROSSES_SESSION_CLOSE",
            canonical=canonical,
            raw_expression=raw_expression,
            entry_block=_evidence_block(
                entry_evidence, quote=entry_quote, parse_error=None
            ),
            exit_block=_empty_evidence_block(ROLE_EXIT),
            expression_raw_sha=expression_raw_sha,
            expression_raw_size=expression_raw_size,
            upstream_digest_sha=upstream_digest,
        )
    if not (canonical["rth_open"] <= exit_target < rth_close):
        return _build_invalid_fixture(
            status=STATUS_EXCLUDED,
            reason="EXIT_BOUNDARY_OUTSIDE_RTH",
            canonical=canonical,
            raw_expression=raw_expression,
            entry_block=_evidence_block(
                entry_evidence, quote=entry_quote, parse_error=None
            ),
            exit_block=_empty_evidence_block(ROLE_EXIT),
            expression_raw_sha=expression_raw_sha,
            expression_raw_size=expression_raw_size,
            upstream_digest_sha=upstream_digest,
        )

    # Exit window: boundary_at MUST equal exit_target, query_end_at MUST
    # equal exit_target + 60s (Ruling A: actual entry + 60m, not
    # expression + 60m; window length is 60s, not whatever the analyst
    # claimed).
    try:
        _validate_evidence_query(
            exit_evidence,
            canonical=canonical,
            expected_boundary_at=exit_target,
            expected_window_end_at=exit_window_end,
        )
        _validate_evidence_selected_event(exit_evidence)
    except Oa3InvalidError as exc:
        reason = _map_invalid_reason(exc)
        return _build_invalid_fixture(
            status=STATUS_INVALID,
            reason=reason,
            canonical=canonical,
            raw_expression=raw_expression,
            entry_block=_evidence_block(
                entry_evidence, quote=entry_quote, parse_error=None
            ),
            exit_block=_empty_evidence_block(ROLE_EXIT),
            expression_raw_sha=expression_raw_sha,
            expression_raw_size=expression_raw_size,
            upstream_digest_sha=upstream_digest,
        )

    # Exit window maturity BEFORE terminal quote outcomes (Ruling C).
    if (
        exit_evidence.request_started_at < exit_window_end
        or exit_evidence.retrieval_observed_at < exit_window_end
    ):
        return _bind_expression_receipt(
            _build_pending_fixture(
                canonical=canonical,
                receipt_payload=raw_expression,
                entry_evidence=entry_evidence,
                exit_evidence=exit_evidence,
                entry_block=_evidence_block(
                    entry_evidence, quote=entry_quote, parse_error=None
                ),
                exit_block=_evidence_block(
                    exit_evidence, quote=None, parse_error=None
                ),
            ),
            upstream_digest_sha=upstream_digest,
            raw_sha=expression_raw_sha,
            raw_size=expression_raw_size,
        )

    # Parse exit evidence (raw source JSON).  Malformed source JSON is
    # QUOTE_RESPONSE_INVALID unavailable — preserved with raw SHA/size.
    exit_quote, exit_parse_error = _parse_window_or_raise_unavailable(exit_evidence)

    if exit_quote is None:
        reason = _map_unavailable_reason(exit_parse_error or "EXIT_QUOTE_UNAVAILABLE")
        return _build_invalid_fixture(
            status=STATUS_UNAVAILABLE,
            reason=reason,
            canonical=canonical,
            raw_expression=raw_expression,
            entry_block=_evidence_block(
                entry_evidence, quote=entry_quote, parse_error=None
            ),
            exit_block=_evidence_block(
                exit_evidence, quote=None, parse_error=exit_parse_error
            ),
            expression_raw_sha=expression_raw_sha,
            expression_raw_size=expression_raw_size,
            upstream_digest_sha=upstream_digest,
        )

    # Selected event clock causality for the exit role (Ruling B: must
    # precede retrieval; _validate_evidence_selected_event already raises
    # on retrieval violation, but re-check here for the live path).
    if exit_quote.event_at > exit_evidence.retrieval_observed_at:
        return _build_invalid_fixture(
            status=STATUS_INVALID,
            reason="EVIDENCE_SELECTED_EVENT_FUTURE",
            canonical=canonical,
            raw_expression=raw_expression,
            entry_block=_evidence_block(
                entry_evidence, quote=entry_quote, parse_error=None
            ),
            exit_block=_evidence_block(
                exit_evidence, quote=exit_quote, parse_error=None
            ),
            expression_raw_sha=expression_raw_sha,
            expression_raw_size=expression_raw_size,
            upstream_digest_sha=upstream_digest,
        )

    # Complete path: full window matured, selected quote exists inside the
    # window, both clocks causally ordered.  Compute the frozen
    # 100-multiplier / USD 0.65-per-side return.
    net_return = cohort.net_return_pct(entry_quote.ask, exit_quote.bid)
    record = _build_complete_fixture(
        canonical=canonical,
        receipt_payload=raw_expression,
        entry_evidence=entry_evidence,
        exit_evidence=exit_evidence,
        entry_quote=entry_quote,
        exit_quote=exit_quote,
        net_return=net_return,
    )
    record["expression_upstream_digest_sha256"] = upstream_digest or ""
    record["expression_raw_response_sha256"] = expression_raw_sha or ""
    record["expression_raw_response_bytes"] = expression_raw_size or 0
    return record


def _revalidate_receipt_at_evaluate(receipt: ExpressionReceipt) -> None:
    """Re-verify the receipt at the evaluate boundary (Ruling B).

    A frozen dataclass prevents field reassignment but does NOT prevent
    mutation of nested Mapping / list values; a caller can mutate
    ``receipt.parsed_payload`` in place and silently corrupt the binding.
    Re-parse raw_bytes and require view-equality to parsed_payload, plus
    re-verify the upstream digest format and clock timezone-awareness.
    """

    # Re-parse raw_bytes strictly and require view-equality to parsed_payload.
    try:
        parsed_from_bytes = cohort.strict_json_value(
            receipt.raw_bytes, label="evaluate(expression=...) raw_bytes revalidation"
        )
    except cohort.NbboCohortError as exc:
        raise Oa3InvalidError(
            f"evaluate(expression=...) raw_bytes revalidation failed: {exc}"
        ) from exc
    if not isinstance(parsed_from_bytes, Mapping):
        raise Oa3InvalidError(
            "evaluate(expression=...) raw_bytes must parse to a JSON object"
        )
    if dict(parsed_from_bytes) != dict(receipt.parsed_payload):
        raise Oa3InvalidError(
            "evaluate(expression=...) parsed_payload disagrees with raw_bytes at revalidation"
        )
    # Re-validate clocks: parsed_payload clocks must still be timezone-aware.
    for clock_field in ("selection_fence_at", "decision_at", "available_at"):
        value = receipt.parsed_payload.get(clock_field)
        if isinstance(value, str):
            try:
                parsed_dt = _datetime_cls.fromisoformat(value)
            except ValueError as exc:
                raise Oa3InvalidError(
                    f"evaluate(expression=...) {clock_field} is not ISO datetime: {exc}"
                ) from exc
            if parsed_dt.tzinfo is None or parsed_dt.tzinfo.utcoffset(parsed_dt) is None:
                raise Oa3InvalidError(
                    f"evaluate(expression=...) {clock_field} is naive; timezone-aware required"
                )


def evaluate_or_raise(
    expression: ExpressionReceipt,
    *,
    entry_evidence: QuoteEvidence,
    exit_evidence: QuoteEvidence,
) -> dict[str, Any]:
    """Evaluate and re-raise EVERY integrity defect the ruler can detect.

    ``evaluate`` returns a fixture record for any non-pending / non-unavailable
    status (the typical contract this ruler ships under).  This wrapper
    re-raises the underlying ``Oa3InvalidError`` or ``Oa3ExcludedError`` for
    EVERY invalid / excluded path the evaluator would otherwise emit —
    identity-defective expression, mismatched upstream digest, mismatched
    per-role contract, mismatched-window boundary, evidence query
    disagreement, clock integrity failure, selected-event-in-future —
    so callers may branch on them.  pending and complete outcomes still
    return a record; unavailability from malformed source JSON still returns
    a record (it is a data state, not an integrity failure).

    The previous incarnation was a preflight-only wrapper that only re-raised
    on _validate_expression_payload failures and silently swallowed every
    other invalid / excluded path the live evaluate emits (digest / query /
    window / clock / selected-event / fence / raw-shape mismatches).
    """

    if not isinstance(expression, ExpressionReceipt):
        raise Oa3InputError(
            "evaluate_or_raise(expression=...) must be an ExpressionReceipt"
        )
    # Re-run the full evaluate path and inspect the resulting record; if
    # the record's status is invalid or excluded, re-raise the matching
    # exception.  This guarantees every integrity defect the ruler can
    # detect is re-raised, not just expression-validation defects.
    record = evaluate(
        expression,
        entry_evidence=entry_evidence,
        exit_evidence=exit_evidence,
    )
    status = record.get("status")
    reason = record.get("reason")
    if status == STATUS_INVALID:
        raise Oa3InvalidError(f"{reason}")
    if status == STATUS_EXCLUDED:
        raise Oa3ExcludedError(f"{reason}")
    return record


__all__ = [
    "ALL_FALSE_AUTHORITY",
    "ENTRY_WINDOW_SECONDS",
    "EXCLUDED_REASONS",
    "EXIT_HORIZON",
    "EXIT_WINDOW_SECONDS",
    "ExpressionReceipt",
    "FROZEN_POLICY",
    "FROZEN_POLICY_ID",
    "FROZEN_POLICY_SHA256",
    "FROZEN_POLICY_VERSION",
    "INVALID_REASONS",
    "Oa3ExcludedError",
    "Oa3InputError",
    "Oa3InvalidError",
    "POLICY_SCHEMA",
    "QuoteEvidence",
    "ROLE_ENTRY",
    "ROLE_EXIT",
    "SCHEMA",
    "SIDE_ASK",
    "SIDE_BID",
    "STATUS_COMPLETE",
    "STATUS_EXCLUDED",
    "STATUS_INVALID",
    "STATUS_PENDING",
    "STATUS_UNAVAILABLE",
    "UNAVAILABLE_REASONS",
    "evaluate",
    "evaluate_or_raise",
    "expression_receipt_from_bytes",
    "quote_evidence_from_bytes",
]

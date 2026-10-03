"""Options Alpha OA-3 exact-option outcome evaluator (pure fixture-only).

This module is the pure evaluator mandated by
``DEC:OPTIONS-ALPHA-EXACT-OPTION-OUTCOME-RULER`` /
``research/options_estate/OPTIONS_ALPHA_EXACT_OPTION_OUTCOME_PREREG_2026-09-19.md``.

It consumes an already-frozen OA expression receipt plus the exact raw
private-source bytes (or strictly matching parsed payload) for the entry and
exit quote windows, plus the request / response / retrieval / computed clocks
that book-keep the live retrieval.  It emits a single OA-3 fixture record and
writes no durable object — there is no I/O here, no registry, no second
outcome ledger, no scheduler.

The module reuses only generic mechanics from ``engine/options_nbbo_cohort.py``:

* ``validate_contract`` — exact OCC identity validation;
* ``parse_quote_response`` — firm OPRA + known exchange + RTH + crossed
  /conflict filtering, first valid quote selection inside the closed window;
* ``canonical_json_bytes`` — strict canonical JSON for receipt bindings;
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

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import Any
from zoneinfo import ZoneInfo

from engine import options_nbbo_cohort as cohort
from engine.session_digest import session_window_et
from lib import nyse_calendar


SCHEMA = "options.oa3_exact_option_outcome_fixture/v1"
POLICY_SCHEMA = "options.alpha_exact_option_outcome_policy/v1"
POLICY_ID = "oa3.long_single_leg_h60_nbbo/v1"
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

# Cached policy payload loaded from disk at module import so a content hash
# can be carried with every fixture record without re-reading the file each
# time.  Re-loaded lazily on the rare path that needs a different version.
_DEFAULT_POLICY_PATH = (
    Path(__file__).resolve().parents[1]
    / "research"
    / "options_estate"
    / "options_alpha_exact_option_outcome_policy_v1.json"
)
_DEFAULT_POLICY_TEXT: str = _DEFAULT_POLICY_PATH.read_text(encoding="utf-8")
_DEFAULT_POLICY_BYTES: bytes = _DEFAULT_POLICY_TEXT.encode("utf-8")
_DEFAULT_POLICY_SHA256: str = sha256(_DEFAULT_POLICY_BYTES).hexdigest()
_DEFAULT_POLICY_DICT: dict[str, Any] = __import__("json").loads(_DEFAULT_POLICY_TEXT)
DEFAULT_POLICY: Mapping[str, Any] = MappingProxyType(
    {key: value for key, value in _DEFAULT_POLICY_DICT.items()}
)

ALL_FALSE_AUTHORITY: Mapping[str, bool] = MappingProxyType(
    {
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
    }
)

EXCLUDED_REASONS: frozenset[str] = frozenset(
    {
        "SAME_DAY_EXPIRATION",
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
    }
)

UNAVAILABLE_REASONS: frozenset[str] = frozenset(
    {
        "ENTRY_QUOTE_UNAVAILABLE",
        "EXIT_QUOTE_UNAVAILABLE",
        "SOURCE_UNAVAILABLE",
        "QUOTE_RESPONSE_INVALID",
        "RAW_BYTES_PAYLOAD_MISMATCH",
    }
)

INVALID_REASONS: frozenset[str] = frozenset(
    {
        "EXPRESSION_IDENTITY_MALFORMED",
        "EXPRESSION_POLICY_VERSION_MISMATCH",
        "EXPRESSION_DIGEST_MISMATCH",
        "EXPRESSION_IMMUTABLE_FIELDS_MISSING",
        "EXPRESSION_SELECTION_FENCE_NOT_FROZEN",
        "CAUSAL_CLOCK_MISMATCH",
        "EXPRESSION_NOT_FROZEN_BEFORE_OUTCOME",
    }
)


class Oa3InputError(ValueError):
    """An OA-3 expression receipt, raw quote bytes, or clock is malformed."""


class Oa3ExcludedError(Oa3InputError):
    """The expression is outside the v1 measurement domain."""


class Oa3InvalidError(Oa3InputError):
    """The expression or its receipts violate immutable identity / clock / receipt law."""


@dataclass(frozen=True)
class QuoteReceipt:
    """Exact private-source bytes paired with the strictly parsed JSON value.

    The wrapper will not perform retrieval itself; it only consumes what the
    retriever handed over and proves the two views agree to the byte.
    """

    raw_bytes: bytes
    parsed_payload: Sequence[Mapping[str, Any]]

    def __post_init__(self) -> None:
        if not isinstance(self.raw_bytes, bytes) or len(self.raw_bytes) == 0:
            raise Oa3InputError("quote receipt raw_bytes must be non-empty bytes")
        if not isinstance(self.parsed_payload, Sequence) or isinstance(
            self.parsed_payload, (str, bytes)
        ):
            raise Oa3InputError("quote receipt parsed_payload must be a JSON array")
        expected = cohort.canonical_json_bytes(list(self.parsed_payload))
        if expected != self.raw_bytes:
            raise Oa3InputError("quote receipt raw_bytes do not match payload")


def quote_receipt_from_bytes(raw_bytes: bytes) -> QuoteReceipt:
    """Construct a receipt by strictly parsing the raw bytes."""
    try:
        parsed = cohort.strict_json_value(raw_bytes, label="oa3 quote receipt")
    except cohort.NbboCohortError as exc:
        raise Oa3InputError(f"oa3 quote receipt is invalid JSON: {exc}") from exc
    if not isinstance(parsed, list):
        raise Oa3InputError("oa3 quote receipt must be a flat JSON array")
    return QuoteReceipt(raw_bytes=raw_bytes, parsed_payload=parsed)


def quote_receipt_from_payload(payload: Sequence[Mapping[str, Any]]) -> QuoteReceipt:
    """Construct a receipt from a payload, canonicalising the bytes ourselves."""
    raw_bytes = cohort.canonical_json_bytes(list(payload))
    return QuoteReceipt(raw_bytes=raw_bytes, parsed_payload=payload)


def _policy_sha256(policy: Mapping[str, Any]) -> str:
    """Stable SHA256 of the policy JSON bytes used for receipt provenance."""

    if policy is DEFAULT_POLICY:
        return _DEFAULT_POLICY_SHA256
    return sha256(cohort.canonical_json_bytes(dict(policy))).hexdigest()


def _require_str(receipt: Mapping[str, Any], field: str) -> str:
    value = receipt.get(field)
    if not isinstance(value, str) or not value:
        raise Oa3InvalidError(
            f"expression receipt {field!r} is missing or non-string"
        )
    return value


def _require_int(receipt: Mapping[str, Any], field: str, expected: int) -> int:
    value = receipt.get(field)
    if value != expected:
        raise Oa3InvalidError(
            f"expression receipt {field!r} must equal {expected}; got {value!r}"
        )
    return value


def _require_bool(receipt: Mapping[str, Any], field: str, expected: bool) -> bool:
    value = receipt.get(field)
    if value is not expected:
        raise Oa3InvalidError(
            f"expression receipt {field!r} must be {expected}; got {value!r}"
        )
    return value


def _parse_clock(value: Any, *, label: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise Oa3InputError(f"{label} must be an ISO datetime string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise Oa3InputError(f"{label} is not ISO datetime: {exc}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ET)
    return parsed.astimezone(UTC)


def _parse_clock_or_datetime(value: Any, *, label: str) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    return _parse_clock(value, label=label)


def _canonical_expression_fields(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Canonical form used for expression-digest hashing."""

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


def _canonical_expression_fields_strs(validated: Mapping[str, Any]) -> dict[str, Any]:
    """Canonical form whose clock fields are the original ISO strings.

    The reusable digest must be replayable from the receipt alone, so the
    canonical form pins the original strings instead of any later-parsed
    datetime objects the validator may have materialised.
    """

    return {
        "expression_id": validated["expression_id"],
        "policy_version": validated["policy_version"],
        "source_candidate_id": validated["source_candidate_id"],
        "decision_receipt_sha256": validated["decision_receipt_sha256"],
        "source_rule_digest_sha256": validated["source_rule_digest_sha256"],
        "selection_frozen_before_outcomes": validated["selection_frozen_before_outcomes"],
        "selection_fence_at": validated["selection_fence_at"],
        "root": validated["root"],
        "expiration": validated["expiration"],
        "right": validated["right"],
        "strike": validated["strike"],
        "strike_millis": validated["strike_millis"],
        "occ_symbol": validated["occ_symbol"],
        "position": validated["position"],
        "quantity_contracts": validated["quantity_contracts"],
        "multiplier": validated["multiplier"],
        "standard_deliverable": validated["standard_deliverable"],
        "single_leg": validated["single_leg"],
        "package": validated["package"],
        "decision_at": validated["decision_at_str"],
        "available_at": validated["available_at_str"],
    }


def _validate_expression(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Validate an OA expression receipt's immutable identity and surface errors.

    Returns the validated receipt (canonical form).  Raises
    ``Oa3InvalidError`` for identity / fence / clock-law defects and
    ``Oa3ExcludedError`` for population defects (the v1 domain only).
    """

    if not isinstance(receipt, Mapping):
        raise Oa3InvalidError("expression receipt must be a mapping")
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
            "expression receipt is missing immutable fields: "
            + ", ".join(missing)
        )

    if not isinstance(receipt["policy_version"], str) or not receipt["policy_version"]:
        raise Oa3InvalidError("expression policy_version is missing")
    if not receipt["policy_version"].startswith("v"):
        raise Oa3InvalidError("expression policy_version must be a v-prefixed tag")

    for digest_field in (
        "decision_receipt_sha256",
        "source_rule_digest_sha256",
    ):
        digest = receipt[digest_field]
        if not isinstance(digest, str) or len(digest) != 64 or any(
            ch not in "0123456789abcdef" for ch in digest
        ):
            raise Oa3InvalidError(
                f"expression {digest_field!r} must be a 64-character lowercase hex digest"
            )

    _require_bool(receipt, "selection_frozen_before_outcomes", True)
    _parse_clock(receipt["selection_fence_at"], label="expression.selection_fence_at")

    contract = {
        "root": _require_str(receipt, "root"),
        "expiration": _require_str(receipt, "expiration"),
        "right": _require_str(receipt, "right"),
        "strike": _require_str(receipt, "strike"),
        "strike_millis": receipt["strike_millis"],
        "occ_symbol": _require_str(receipt, "occ_symbol"),
    }
    try:
        contract = cohort.validate_contract(contract)
    except cohort.NbboCohortError as exc:
        raise Oa3InvalidError(
            f"expression contract identity is invalid: {exc}"
        ) from exc

    if receipt.get("quantity_contracts") != QUANTITY_CONTRACTS:
        raise Oa3ExcludedError("QUANTITY_NOT_ONE")
    if receipt.get("multiplier") != MULTIPLIER:
        raise Oa3ExcludedError("NON_STANDARD_MULTIPLIER")
    if not isinstance(receipt["position"], str):
        raise Oa3InvalidError("expression.position must be a string")
    if receipt["position"] != "long":
        raise Oa3ExcludedError("SHORT_OPTION_NOT_SUPPORTED")
    if receipt.get("single_leg") is not True:
        raise Oa3ExcludedError("PACKAGE_NOT_SUPPORTED")
    if receipt.get("package") is not False:
        raise Oa3ExcludedError("PACKAGE_NOT_SUPPORTED")
    if receipt.get("standard_deliverable") is not True:
        raise Oa3ExcludedError("NON_STANDARD_DELIVERABLE")

    decision_at = _parse_clock(receipt["decision_at"], label="expression.decision_at")
    available_at = _parse_clock(receipt["available_at"], label="expression.available_at")
    if available_at < decision_at:
        raise Oa3InvalidError(
            "expression available_at precedes decision_at (causal clock mismatch)"
        )

    available_et_date = available_at.astimezone(ET).date()
    try:
        expiration_date = datetime.strptime(
            receipt["expiration"], "%Y-%m-%d"
        ).date()
    except ValueError as exc:
        raise Oa3InvalidError("expression expiration is not YYYY-MM-DD") from exc
    if expiration_date == available_et_date:
        raise Oa3ExcludedError("SAME_DAY_EXPIRATION")

    if not nyse_calendar.is_session(available_et_date):
        raise Oa3ExcludedError("EXPRESSION_DATE_NOT_NYSE_SESSION")

    open_dt, close_dt = session_window_et(available_et_date)
    open_utc = open_dt.astimezone(UTC)
    close_utc = close_dt.astimezone(UTC)
    if not (open_utc <= available_at < close_utc):
        raise Oa3ExcludedError("ENTRY_BOUNDARY_OUTSIDE_RTH")

    canonical = _canonical_expression_fields(receipt)
    canonical.update(
        {
            "contract": contract,
            "decision_at": decision_at,
            "available_at": available_at,
            "decision_at_str": receipt["decision_at"],
            "available_at_str": receipt["available_at"],
            "session_date": available_et_date,
            "rth_open": open_utc,
            "rth_close": close_utc,
        }
    )
    return canonical


def _validate_clocks(
    *,
    request_started_at: datetime,
    response_observed_at: datetime,
    retrieval_observed_at: datetime,
    computed_at: datetime | None,
    expression_available_at: datetime,
) -> tuple[datetime, datetime, datetime, datetime]:
    if request_started_at > response_observed_at:
        raise Oa3InvalidError(
            "CAUSAL_CLOCK_MISMATCH: request_started_at follows response_observed_at"
        )
    if response_observed_at > retrieval_observed_at:
        raise Oa3InvalidError(
            "CAUSAL_CLOCK_MISMATCH: response_observed_at follows retrieval_observed_at"
        )
    if request_started_at < expression_available_at:
        raise Oa3InvalidError(
            "CAUSAL_CLOCK_MISMATCH: request_started_at precedes expression.available_at"
        )
    if computed_at is None:
        computed_at = retrieval_observed_at
    return request_started_at, response_observed_at, retrieval_observed_at, computed_at


def _quote_receipt(record: Any) -> QuoteReceipt:
    if isinstance(record, QuoteReceipt):
        return record
    if isinstance(record, bytes):
        return quote_receipt_from_bytes(record)
    if isinstance(record, Mapping):
        raise Oa3InputError(
            "quote record must be bytes, QuoteReceipt, or a parsed JSON array; "
            "received a Mapping"
        )
    if isinstance(record, cohort.FetchedQuoteResponse):
        if not isinstance(record.payload, list):
            raise Oa3InputError(
                "FetchedQuoteResponse payload must be a list for OA-3"
            )
        canonical_payload = cohort.canonical_json_bytes(record.payload)
        if record.raw_body != canonical_payload:
            raise Oa3InputError(
                "FetchedQuoteResponse raw_body does not match its canonical payload"
            )
        return QuoteReceipt(raw_bytes=record.raw_body, parsed_payload=record.payload)
    if isinstance(record, Sequence) and not isinstance(record, (str, bytes)):
        return quote_receipt_from_payload(record)
    raise Oa3InputError(
        "quote record must be bytes, QuoteReceipt, a parsed JSON array, or a "
        "FetchedQuoteResponse"
    )


def _window_query_bounds(boundary: datetime, *, window_seconds: int) -> tuple[datetime, datetime]:
    end = boundary + timedelta(seconds=window_seconds)
    return boundary, end


def _entry_bounds(expression_available_at: datetime) -> tuple[datetime, datetime]:
    return _window_query_bounds(
        expression_available_at, window_seconds=ENTRY_WINDOW_SECONDS
    )


def _exit_bounds(entry_event_at: datetime) -> tuple[datetime, datetime]:
    target = entry_event_at + EXIT_HORIZON
    return _window_query_bounds(target, window_seconds=EXIT_WINDOW_SECONDS)


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


def _raw_receipt_sha(raw_bytes: bytes) -> tuple[str, int]:
    return sha256(raw_bytes).hexdigest(), len(raw_bytes)


def _parse_window(
    *,
    side: str,
    role: str,
    contract: dict[str, Any],
    boundary: datetime,
    end: datetime,
    receipt: QuoteReceipt,
) -> tuple[cohort.SourceQuote | None, str | None]:
    """Run the reusable parser on a window.  Returns (quote, error)."""

    try:
        quote = cohort.parse_quote_response(
            list(receipt.parsed_payload),
            role=role,
            contract=contract,
            boundary_at=boundary,
            query_end_at=end,
        )
    except cohort.NbboSourceError as exc:
        return None, f"{str(exc)}"
    except cohort.NbboCohortError as exc:
        return None, f"QUOTE_RESPONSE_INVALID:{exc}"
    return quote, None


def _build_window_block(
    *,
    side: str,
    role: str,
    boundary: datetime,
    end: datetime,
    receipt: QuoteReceipt,
    contract: dict[str, Any],
) -> tuple[dict[str, Any], cohort.SourceQuote | None]:
    raw_sha, raw_bytes = _raw_receipt_sha(receipt.raw_bytes)
    payload_canonical = cohort.canonical_json_bytes(list(receipt.parsed_payload))
    payload_sha = sha256(payload_canonical).hexdigest()
    if payload_sha != raw_sha:
        raise Oa3InvalidError("RAW_BYTES_PAYLOAD_MISMATCH")
    quote, parse_error = _parse_window(
        side=side,
        role=role,
        contract=contract,
        boundary=boundary,
        end=end,
        receipt=receipt,
    )
    selected: dict[str, Any] | None = None
    if quote is not None:
        selected = _selected_quote_dict(quote, side=side)
    block = {
        "side": side,
        "role": role,
        "query_bounds": {
            "start_at": boundary,
            "end_at": end,
        },
        "raw_response_sha256": raw_sha,
        "raw_response_bytes": raw_bytes,
        "raw_payload_sha256": payload_sha,
        "raw_payload_bytes": len(payload_canonical),
        "selected": selected,
        "parse_error": parse_error,
    }
    return block, quote


def _empty_block(side: str, role: str) -> dict[str, Any]:
    return {
        "side": side,
        "role": role,
        "query_bounds": None,
        "raw_response_sha256": None,
        "raw_response_bytes": 0,
        "raw_payload_sha256": None,
        "raw_payload_bytes": 0,
        "selected": None,
        "parse_error": None,
    }


def _parse_quoted_payload(raw_bytes: bytes) -> bytes:
    """Hash-trace the raw bytes so callers can trace which view they used."""

    return raw_bytes


def evaluate(
    expression: Mapping[str, Any],
    *,
    entry_quote: Any,
    exit_quote: Any,
    request_started_at: datetime | str,
    response_observed_at: datetime | str,
    retrieval_observed_at: datetime | str,
    computed_at: datetime | str | None = None,
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate one exact OA expression under the OA-3 v1 ruler.

    Parameters
    ----------
    expression:
        The frozen OA expression receipt.  Required fields are documented in
        ``OPTIONS_ALPHA_EXACT_OPTION_OUTCOME_PREREG_2026-09-19.md`` §3.
    entry_quote, exit_quote:
        The exact private-source bytes for the entry / exit windows, accepted
        as ``bytes``, ``QuoteReceipt``, ``FetchedQuoteResponse`` (the existing
        nbbo-cohort wrapper), or a parsed JSON array of source quote rows.
        When both bytes and a payload are passed the wrapper proves they
        match exactly.
    request_started_at, response_observed_at, retrieval_observed_at:
        Live retrieval clocks — the source request, the response arrival, and
        the time at which the analyst looks at the source data.  The wrapper
        enforces the ordering ``request > available_at``, ``request < response``,
        ``response < retrieval``.
    computed_at:
        Optional clock stamped on the fixture record itself; defaults to
        ``retrieval_observed_at``.
    policy:
        Optional OA-3 v1 policy mapping; defaults to the preregistered
        on-disk policy whose SHA-256 is carried on every fixture record.

    Returns
    -------
    dict
        The OA-3 fixture record.  No raw quote rows / payload / PnL claim
        appears in the output; ``net_return_pct`` is populated only when the
        status is ``complete`` and the frozen one-contract USD 0.65/side
        arithmetic is reproducible.
    """

    if not isinstance(expression, Mapping):
        raise Oa3InputError("expression must be a mapping")
    if policy is None:
        policy = DEFAULT_POLICY
    policy_sha = _policy_sha256(policy)

    try:
        validated = _validate_expression(expression)
    except Oa3ExcludedError as exc:
        return _build_invalid_record(
            validated={},
            policy=policy,
            policy_sha=policy_sha,
            status=STATUS_EXCLUDED,
            reason=str(exc),
            contract=None,
            decision_at=None,
            available_at=None,
            session_date=None,
            rth_open=None,
            rth_close=None,
        )
    except Oa3InvalidError as exc:
        return _build_invalid_record(
            validated={},
            policy=policy,
            policy_sha=policy_sha,
            status=STATUS_INVALID,
            reason=str(exc),
            contract=None,
            decision_at=None,
            available_at=None,
            session_date=None,
            rth_open=None,
            rth_close=None,
        )

    contract = validated["contract"]
    expression_available_at: datetime = validated["available_at"]
    rth_close: datetime = validated["rth_close"]
    contract_for_parse = {
        "root": contract["root"],
        "expiration": contract["expiration"],
        "right": contract["right"],
        "strike": contract["strike"],
        "strike_millis": contract["strike_millis"],
        "occ_symbol": contract["occ_symbol"],
    }

    try:
        entry_receipt = _quote_receipt(entry_quote)
        exit_receipt = _quote_receipt(exit_quote)
    except Oa3InputError as exc:
        return _build_invalid_record(
            validated=validated,
            policy=policy,
            policy_sha=policy_sha,
            status=STATUS_INVALID,
            reason=f"INVALID:{exc}",
            contract=contract,
            decision_at=validated["decision_at"],
            available_at=validated["available_at"],
            session_date=validated["session_date"],
            rth_open=validated["rth_open"],
            rth_close=validated["rth_close"],
        )

    request_started_at_dt = _parse_clock_or_datetime(
        request_started_at, label="request_started_at"
    )
    response_observed_at_dt = _parse_clock_or_datetime(
        response_observed_at, label="response_observed_at"
    )
    retrieval_observed_at_dt = _parse_clock_or_datetime(
        retrieval_observed_at, label="retrieval_observed_at"
    )
    computed_at_dt = (
        _parse_clock_or_datetime(computed_at, label="computed_at")
        if computed_at is not None
        else None
    )
    try:
        clocks = _validate_clocks(
            request_started_at=request_started_at_dt,
            response_observed_at=response_observed_at_dt,
            retrieval_observed_at=retrieval_observed_at_dt,
            computed_at=computed_at_dt,
            expression_available_at=expression_available_at,
        )
    except Oa3InvalidError as exc:
        return _build_invalid_record(
            validated=validated,
            policy=policy,
            policy_sha=policy_sha,
            status=STATUS_INVALID,
            reason=str(exc),
            contract=contract,
            decision_at=validated["decision_at"],
            available_at=validated["available_at"],
            session_date=validated["session_date"],
            rth_open=validated["rth_open"],
            rth_close=validated["rth_close"],
        )
    (
        request_started_at_dt,
        response_observed_at_dt,
        retrieval_observed_at_dt,
        computed_at_dt,
    ) = clocks

    entry_start, entry_end = _entry_bounds(expression_available_at)
    entry_block, entry_quote_obj = _build_window_block(
        side=SIDE_ASK,
        role=ROLE_ENTRY,
        contract=contract_for_parse,
        boundary=entry_start,
        end=entry_end,
        receipt=entry_receipt,
    )

    if entry_quote_obj is None:
        if retrieval_observed_at_dt < entry_end:
            return _build_record(
                validated=validated,
                policy=policy,
                policy_sha=policy_sha,
                status=STATUS_PENDING,
                reason=None,
                entry_block=entry_block,
                exit_block=_empty_block(SIDE_BID, ROLE_EXIT),
                clocks=clocks,
            )
        reason = (
            "QUOTE_RESPONSE_INVALID"
            if entry_block["parse_error"] is not None
            else "ENTRY_QUOTE_UNAVAILABLE"
        )
        return _build_record(
            validated=validated,
            policy=policy,
            policy_sha=policy_sha,
            status=STATUS_UNAVAILABLE,
            reason=reason,
            entry_block=entry_block,
            exit_block=_empty_block(SIDE_BID, ROLE_EXIT),
            clocks=clocks,
        )

    exit_start, exit_end = _exit_bounds(entry_quote_obj.event_at)
    if exit_end >= rth_close:
        return _build_record(
            validated=validated,
            policy=policy,
            policy_sha=policy_sha,
            status=STATUS_EXCLUDED,
            reason="HORIZON_CROSSES_SESSION_CLOSE",
            entry_block=entry_block,
            exit_block=_empty_block(SIDE_BID, ROLE_EXIT),
            clocks=clocks,
        )
    if not (validated["rth_open"] <= exit_start < rth_close):
        return _build_record(
            validated=validated,
            policy=policy,
            policy_sha=policy_sha,
            status=STATUS_EXCLUDED,
            reason="EXIT_BOUNDARY_OUTSIDE_RTH",
            entry_block=entry_block,
            exit_block=_empty_block(SIDE_BID, ROLE_EXIT),
            clocks=clocks,
        )

    exit_block, exit_quote_obj = _build_window_block(
        side=SIDE_BID,
        role=ROLE_EXIT,
        contract=contract_for_parse,
        boundary=exit_start,
        end=exit_end,
        receipt=exit_receipt,
    )

    if exit_quote_obj is None:
        if retrieval_observed_at_dt < exit_end:
            return _build_record(
                validated=validated,
                policy=policy,
                policy_sha=policy_sha,
                status=STATUS_PENDING,
                reason=None,
                entry_block=entry_block,
                exit_block=exit_block,
                clocks=clocks,
            )
        reason = (
            "QUOTE_RESPONSE_INVALID"
            if exit_block["parse_error"] is not None
            else "EXIT_QUOTE_UNAVAILABLE"
        )
        return _build_record(
            validated=validated,
            policy=policy,
            policy_sha=policy_sha,
            status=STATUS_UNAVAILABLE,
            reason=reason,
            entry_block=entry_block,
            exit_block=exit_block,
            clocks=clocks,
        )

    net_return = cohort.net_return_pct(entry_quote_obj.ask, exit_quote_obj.bid)
    return _build_complete(
        validated=validated,
        policy=policy,
        policy_sha=policy_sha,
        entry_block=entry_block,
        exit_block=exit_block,
        net_return=net_return,
        clocks=clocks,
    )


def _build_invalid_record(
    *,
    validated: dict[str, Any],
    policy: Mapping[str, Any],
    policy_sha: str,
    status: str,
    reason: str,
    contract: dict[str, Any] | None,
    decision_at: datetime | None,
    available_at: datetime | None,
    session_date: Any,
    rth_open: datetime | None,
    rth_close: datetime | None,
) -> dict[str, Any]:
    """Build a fixture record for a record-level defect (invalid / excluded).

    Used when the wrapper rejects an expression at the population or
    identity gate, before any quote windows are evaluated.  The record
    carries no entry/exit observations, no clocks, no net return; only the
    schema/policy/identity stamp plus the recorded reason.
    """

    expression_id = validated.get("expression_id")
    source_candidate_id = validated.get("source_candidate_id")
    decision_receipt_sha = validated.get("decision_receipt_sha256")
    source_rule_sha = validated.get("source_rule_digest_sha256")
    selection_fence_at = validated.get("selection_fence_at")
    policy_version = validated.get("policy_version")
    if expression_id is None:
        expression_id = ""
    if source_candidate_id is None:
        source_candidate_id = ""
    if decision_receipt_sha is None:
        decision_receipt_sha = ""
    if source_rule_sha is None:
        source_rule_sha = ""
    if selection_fence_at is None:
        selection_fence_at = ""
    if policy_version is None:
        policy_version = "v?"

    if isinstance(expression_id, str) and expression_id and all(
        field in validated
        for field in (
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
        )
    ):
        expression_digest = sha256(
            cohort.canonical_json_bytes(_canonical_expression_fields_strs(validated))
        ).hexdigest()
    else:
        expression_digest = ""

    record: dict[str, Any] = {
        "schema": SCHEMA,
        "policy_id": policy["policy_id"],
        "policy_version": policy_version,
        "policy_sha256": policy_sha,
        "expression_id": expression_id,
        "expression_digest_sha256": expression_digest,
        "expression_source_candidate_id": source_candidate_id,
        "expression_decision_receipt_sha256": decision_receipt_sha,
        "expression_source_rule_digest_sha256": source_rule_sha,
        "selection_frozen_before_outcomes": bool(
            validated.get("selection_frozen_before_outcomes", False)
        ),
        "selection_fence_at": selection_fence_at,
        "contract": contract,
        "expression_decision_at": decision_at,
        "expression_available_at": available_at,
        "session_date": session_date.isoformat() if session_date is not None else None,
        "session_rth_open": rth_open,
        "session_rth_close": rth_close,
        "position": validated.get("position"),
        "quantity_contracts": validated.get("quantity_contracts"),
        "multiplier": validated.get("multiplier"),
        "status": status,
        "reason": reason,
        "entry": _empty_block(SIDE_ASK, ROLE_ENTRY),
        "exit": _empty_block(SIDE_BID, ROLE_EXIT),
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
        "clocks": {
            "request_started_at": None,
            "response_observed_at": None,
            "retrieval_observed_at": None,
            "computed_at": None,
        },
        "authority": {key: value for key, value in ALL_FALSE_AUTHORITY.items()},
    }
    return record


def _build_record(
    *,
    validated: dict[str, Any],
    policy: Mapping[str, Any],
    policy_sha: str,
    status: str,
    reason: str | None,
    entry_block: dict[str, Any],
    exit_block: dict[str, Any],
    clocks: tuple[datetime, datetime, datetime, datetime],
) -> dict[str, Any]:
    if status == STATUS_EXCLUDED:
        if reason not in EXCLUDED_REASONS:
            raise Oa3InputError(f"excluded reason {reason!r} is not in vocabulary")
    if status == STATUS_UNAVAILABLE:
        if reason not in UNAVAILABLE_REASONS:
            raise Oa3InputError(f"unavailable reason {reason!r} is not in vocabulary")
    if status in (STATUS_PENDING, STATUS_COMPLETE):
        if reason is not None:
            raise Oa3InputError(
                f"status {status} must not carry a reason; got {reason!r}"
            )
    return _build_common(
        validated=validated,
        policy=policy,
        policy_sha=policy_sha,
        status=status,
        reason=reason,
        entry_block=entry_block,
        exit_block=exit_block,
        clocks=clocks,
        net_return=None,
    )


def _build_complete(
    *,
    validated: dict[str, Any],
    policy: Mapping[str, Any],
    policy_sha: str,
    entry_block: dict[str, Any],
    exit_block: dict[str, Any],
    net_return: Decimal,
    clocks: tuple[datetime, datetime, datetime, datetime],
) -> dict[str, Any]:
    return _build_common(
        validated=validated,
        policy=policy,
        policy_sha=policy_sha,
        status=STATUS_COMPLETE,
        reason=None,
        entry_block=entry_block,
        exit_block=exit_block,
        clocks=clocks,
        net_return=net_return,
    )


def _build_common(
    *,
    validated: dict[str, Any],
    policy: Mapping[str, Any],
    policy_sha: str,
    status: str,
    reason: str | None,
    entry_block: dict[str, Any],
    exit_block: dict[str, Any],
    clocks: tuple[datetime, datetime, datetime, datetime],
    net_return: Decimal | None,
) -> dict[str, Any]:
    (
        request_started_at,
        response_observed_at,
        retrieval_observed_at,
        computed_at,
    ) = clocks
    expression_digest = sha256(
        cohort.canonical_json_bytes(_canonical_expression_fields_strs(validated))
    ).hexdigest()
    record: dict[str, Any] = {
        "schema": SCHEMA,
        "policy_id": policy["policy_id"],
        "policy_version": validated["policy_version"],
        "policy_sha256": policy_sha,
        "expression_id": validated["expression_id"],
        "expression_digest_sha256": expression_digest,
        "expression_source_candidate_id": validated["source_candidate_id"],
        "expression_decision_receipt_sha256": validated["decision_receipt_sha256"],
        "expression_source_rule_digest_sha256": validated["source_rule_digest_sha256"],
        "selection_frozen_before_outcomes": True,
        "selection_fence_at": validated["selection_fence_at"],
        "contract": validated["contract"],
        "expression_decision_at": validated["decision_at"],
        "expression_available_at": validated["available_at"],
        "session_date": validated["session_date"].isoformat(),
        "session_rth_open": validated["rth_open"],
        "session_rth_close": validated["rth_close"],
        "position": validated["position"],
        "quantity_contracts": validated["quantity_contracts"],
        "multiplier": validated["multiplier"],
        "status": status,
        "reason": reason,
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
        "clocks": {
            "request_started_at": request_started_at,
            "response_observed_at": response_observed_at,
            "retrieval_observed_at": retrieval_observed_at,
            "computed_at": computed_at,
        },
        "authority": {key: value for key, value in ALL_FALSE_AUTHORITY.items()},
    }
    return record


def evaluate_or_raise(
    expression: Mapping[str, Any],
    *,
    entry_quote: Any,
    exit_quote: Any,
    request_started_at: datetime | str,
    response_observed_at: datetime | str,
    retrieval_observed_at: datetime | str,
    computed_at: datetime | str | None = None,
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate and re-raise identity-defects so callers may branch on them.

    ``evaluate`` returns a ``status: invalid`` fixture record for identity
    defects (the typical contract this ruler ships under).  This wrapper
    re-raises ``Oa3InvalidError`` / ``Oa3ExcludedError`` so caller code can
    branch on them when needed without losing the record shape.
    """

    return evaluate(
        expression,
        entry_quote=entry_quote,
        exit_quote=exit_quote,
        request_started_at=request_started_at,
        response_observed_at=response_observed_at,
        retrieval_observed_at=retrieval_observed_at,
        computed_at=computed_at,
        policy=policy,
    )


__all__ = [
    "ALL_FALSE_AUTHORITY",
    "DEFAULT_POLICY",
    "ENTRY_WINDOW_SECONDS",
    "EXIT_HORIZON",
    "EXIT_WINDOW_SECONDS",
    "EXCLUDED_REASONS",
    "INVALID_REASONS",
    "Oa3ExcludedError",
    "Oa3InputError",
    "Oa3InvalidError",
    "POLICY_ID",
    "POLICY_SCHEMA",
    "QuoteReceipt",
    "SCHEMA",
    "STATUS_COMPLETE",
    "STATUS_EXCLUDED",
    "STATUS_INVALID",
    "STATUS_PENDING",
    "STATUS_UNAVAILABLE",
    "UNAVAILABLE_REASONS",
    "evaluate",
    "evaluate_or_raise",
    "quote_receipt_from_bytes",
    "quote_receipt_from_payload",
]
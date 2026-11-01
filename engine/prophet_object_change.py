"""Source-only what-changed comparison for two reads of one native object.

Presentation-only component for the Daily Desk per-object what-changed
display.  ``compare_object_reads`` compares exactly ONE native object per
call: given an already validated previous read and an already validated
current read of the same object identity, it reports which owner facts
differ.  Quote changes never cascade into an assessment or a Plan; each
call is a single-object comparison.

Binding limitations, by contract:

* The caller supplies reads already validated and normalized by the native
  owner into this contract.  This module can check structure and matching
  identity.  It CANNOT authenticate ``owner_receipt`` and cannot prove
  source or review acceptance; no acceptance is inferred from any
  reference, digest or lineage field, and a successful comparison is not
  an acceptance.
* Facts are copied OWNER facts, never computed, defaulted or repaired.  A
  missing fact key makes the record unavailable instead of becoming an
  empty or "unchanged" value.
* Only facts decide ``changed``.  Movement of ``source_ref``,
  ``generation_ref``, ``owner_receipt`` or ``clocks`` alone is metadata
  movement, not a content change.
* Clocks are preserved verbatim (missing stays ``null``; no assembly-time
  substitution).  Late or future clocks carry no freshness or economic
  authority and never change the comparison outcome.
* ``review_ref`` is review lineage only.  Requiring it for an assessment
  is a structural rule of this contract, not a review acceptance verdict.
* Candidate-generation cross-comparison is deliberately unavailable:
  reads must share the same ``candidate_generation_id``; no relation
  between different generations is invented in this API.
* Symbols/tickers are never identifiers or a fallback.  Identity is
  ``object_type`` + ``object_id`` + ``owner`` plus all four binding
  fields, matched exactly.
* Unknown envelope, binding, clock or fact keys make the record invalid,
  so uncontracted authority cannot be forwarded through this API.
* Malformed, missing, failed or ambiguous input fails closed to
  ``state="comparison_unavailable"`` with a stable ``reason``.  Nothing is
  raised for bad JSON shapes and no default "unchanged" is invented.  A
  missing read (``None``) is reported as ``previous_unavailable`` /
  ``current_unavailable``; anything present that violates the contract is
  reported as ``previous_invalid`` / ``current_invalid``.
* The result carries no merged record, no new receipt, no accepted bit and
  no entry or trade action.  P1a #8444 and Daily Brief #8249
  integration/source holds elsewhere remain binding.

Standard library only; no I/O, no clock reads, no digest minting, no side
effects, and no mutation of caller data (results are detached deep copies).
"""

from __future__ import annotations

import copy
import datetime
import math
import re

__all__ = ["compare_object_reads"]

_STATE_CHANGED = "changed"
_STATE_UNCHANGED = "unchanged"
_STATE_UNAVAILABLE = "comparison_unavailable"

_REASON_FACTS_CHANGED = "facts_changed"
_REASON_FACTS_UNCHANGED = "facts_unchanged"

# Closed-failure reasons: which side failed, missing vs malformed, or identity.
_REASON_PREVIOUS_UNAVAILABLE = "previous_unavailable"
_REASON_PREVIOUS_INVALID = "previous_invalid"
_REASON_CURRENT_UNAVAILABLE = "current_unavailable"
_REASON_CURRENT_INVALID = "current_invalid"
_REASON_IDENTITY_MISMATCH = "identity_mismatch"

_ENVELOPE_STATE = "available"

_ENVELOPE_KEYS = frozenset(
    {
        "object_type",
        "object_id",
        "owner",
        "state",
        "binding",
        "source_ref",
        "generation_ref",
        "owner_receipt",
        "clocks",
        "facts",
        "review_ref",
    }
)
_BINDING_KEYS = frozenset(
    {
        "security_id",
        "episode_id",
        "candidate_generation_id",
        "market_session",
    }
)
_BINDING_IDENTITY_KEYS = (
    "security_id",
    "episode_id",
    "candidate_generation_id",
    "market_session",
)
_CLOCK_KEYS = frozenset({"source_time", "observed_time", "published_time"})

_FACT_KEYS = {
    "quote": frozenset({"price", "currency"}),
    "assessment": frozenset({"summary", "evidence_refs", "counterevidence_refs"}),
    "plan": frozenset({"status", "change_reason", "invalidation"}),
}

_MARKET_SESSION_PATTERN = re.compile(r"\A\d{4}-\d{2}-\d{2}\Z")


def _is_text(value):
    # Reject missing text without changing the owner's original spelling.
    return isinstance(value, str) and bool(value.strip())


def _is_positive_number(value):
    # ``bool`` is an ``int`` subclass; boolean numbers are refused everywhere.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value) and value > 0
    except OverflowError:
        # Arbitrarily large JSON integers must not escape the unavailable path.
        return False


def _is_text_list(value):
    return isinstance(value, list) and all(_is_text(item) for item in value)


def _has_exact_keys(value, keys):
    return isinstance(value, dict) and set(value) == keys


def _is_market_session(value):
    if not isinstance(value, str) or _MARKET_SESSION_PATTERN.match(value) is None:
        return False
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _is_aware_iso_text(value):
    """True for a nonempty ISO-8601 text carrying an explicit UTC offset."""
    if not _is_text(value):
        return False
    try:
        parsed = datetime.datetime.fromisoformat(value)
    except ValueError:
        if not value.endswith("Z"):
            return False
        try:  # ``Z`` is valid ISO-8601 UTC; normalized only for this check.
            parsed = datetime.datetime.fromisoformat(value[:-1] + "+00:00")
        except ValueError:
            return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _facts_are_valid(object_type, facts):
    if object_type == "quote":
        return _is_positive_number(facts["price"]) and _is_text(facts["currency"])
    if object_type == "assessment":
        return (
            _is_text(facts["summary"])
            and _is_text_list(facts["evidence_refs"])
            and _is_text_list(facts["counterevidence_refs"])
        )
    # plan
    if not _is_text(facts["status"]):
        return False
    change_reason = facts["change_reason"]
    if change_reason is not None and not _is_text(change_reason):
        return False
    invalidation = facts["invalidation"]
    return invalidation is None or _is_positive_number(invalidation)


def _validate_record(record):
    """Return ``record`` unchanged when it satisfies the contract, else ``None``.

    Structural only: this never authenticates the owner receipt and never
    judges acceptance; it refuses only shapes this contract does not define.
    """
    if not _has_exact_keys(record, _ENVELOPE_KEYS):
        return None

    object_type = record["object_type"]
    if not _is_text(object_type) or object_type not in _FACT_KEYS:
        return None
    if not _is_text(record["object_id"]) or not _is_text(record["owner"]):
        return None
    if record["state"] != _ENVELOPE_STATE:
        return None
    if not _is_text(record["source_ref"]):
        return None
    if not _is_text(record["generation_ref"]):
        return None
    if not _is_text(record["owner_receipt"]):
        return None

    binding = record["binding"]
    if not _has_exact_keys(binding, _BINDING_KEYS):
        return None
    for key in ("security_id", "episode_id", "candidate_generation_id"):
        if not _is_text(binding[key]):
            return None
    if not _is_market_session(binding["market_session"]):
        return None

    clocks = record["clocks"]
    if not _has_exact_keys(clocks, _CLOCK_KEYS):
        return None
    for value in clocks.values():
        if value is not None and not _is_aware_iso_text(value):
            return None

    review_ref = record["review_ref"]
    if object_type == "assessment":
        if not _is_text(review_ref):
            return None
    elif review_ref is not None:
        return None

    facts = record["facts"]
    if not _has_exact_keys(facts, _FACT_KEYS[object_type]):
        return None
    if not _facts_are_valid(object_type, facts):
        return None
    return record


def _same_identity(previous, current):
    if (
        previous["object_type"] != current["object_type"]
        or previous["object_id"] != current["object_id"]
        or previous["owner"] != current["owner"]
    ):
        return False
    previous_binding = previous["binding"]
    current_binding = current["binding"]
    return all(
        previous_binding[key] == current_binding[key]
        for key in _BINDING_IDENTITY_KEYS
    )


def _changed_fact_keys(previous_facts, current_facts):
    return sorted(
        key for key, value in previous_facts.items() if current_facts[key] != value
    )


def _unavailable(reason):
    return {
        "state": _STATE_UNAVAILABLE,
        "reason": reason,
        "changed_fields": [],
        "before": None,
        "after": None,
    }


def _validated_side(record, unavailable_reason, invalid_reason):
    """Return ``(record, None)`` or ``(None, closed_failure_reason)``."""
    if record is None:
        return None, unavailable_reason
    if _validate_record(record) is None:
        return None, invalid_reason
    return record, None


def compare_object_reads(previous: object, current: object) -> dict[str, object]:
    """Compare two validated reads of ONE native object by owner facts only.

    Returns a dict with exactly the keys ``state``, ``reason``,
    ``changed_fields``, ``before`` and ``after``:

    * ``state`` -- ``"changed"``, ``"unchanged"`` or
      ``"comparison_unavailable"``.
    * ``reason`` -- ``"facts_changed"`` / ``"facts_unchanged"``, or a
      stable closed-failure reason: ``"previous_unavailable"`` (no prior
      read), ``"previous_invalid"``, ``"current_unavailable"``,
      ``"current_invalid"`` or ``"identity_mismatch"``.
    * ``changed_fields`` -- sorted fact keys that differ (empty unless
      changed).
    * ``before`` / ``after`` -- detached deep copies of the complete input
      records; both ``None`` on an unavailable result.

    Comparison is presentation-only: it never authenticates receipts,
    never proves source or review acceptance, and returns no merged
    record, new receipt, accepted bit or entry/trade action.
    """
    previous_record, previous_failure = _validated_side(
        previous, _REASON_PREVIOUS_UNAVAILABLE, _REASON_PREVIOUS_INVALID
    )
    if previous_failure is not None:
        return _unavailable(previous_failure)
    current_record, current_failure = _validated_side(
        current, _REASON_CURRENT_UNAVAILABLE, _REASON_CURRENT_INVALID
    )
    if current_failure is not None:
        return _unavailable(current_failure)
    if not _same_identity(previous_record, current_record):
        return _unavailable(_REASON_IDENTITY_MISMATCH)

    changed_fields = _changed_fact_keys(
        previous_record["facts"], current_record["facts"]
    )
    if changed_fields:
        state, reason = _STATE_CHANGED, _REASON_FACTS_CHANGED
    else:
        state, reason = _STATE_UNCHANGED, _REASON_FACTS_UNCHANGED
    return {
        "state": state,
        "reason": reason,
        "changed_fields": changed_fields,
        "before": copy.deepcopy(previous_record),
        "after": copy.deepcopy(current_record),
    }

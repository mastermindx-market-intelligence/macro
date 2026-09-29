"""GD-6A: exact-source, zero-policy SHADOW intake for Prophet market eligibility.

This implements the existing prophet.market_eligibility/v1 sidecar owner. It is
not a detector, policy registry, risk scorer, allocator, B4 gate or publisher.
Current Grey Deer v0 emits zero policies. A nonempty policy input is therefore
UNAVAILABLE, never guessed into a permission or a suppression. Supporting an
individually authorized policy requires a separately reviewed definition change.

An AVAILABLE / ELIGIBLE row means *no market-policy constraint in this bound
zero-policy observation*, NOT permission to buy. Production behavior is always
UNCHANGED. The raw board and every row/order remain untouched. Hashes bind bytes;
they are NOT proof of identity, entitlement, source authority or live freshness.
The caller must obtain expected session/definition/hash and validity cutoff from
its existing source owner, not an untrusted web request or this module's output.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
from hashlib import sha256
import json
import re
from typing import Any, Mapping

SCHEMA = "prophet.market_eligibility/v1"
DEFINITION_ID = "gd6a-us-zero-policy-shadow-v1-2026-09-28"
ENVELOPE_SCHEMA = "mastermind.risk_envelope/v1"
ENVELOPE_DEFINITION = "grey-deer-v1-2026-08-19"
SUPPORTED_BOARD_DEFINITIONS = frozenset({"us_prophet_v3", "us_prophet_v2_fallback"})
MAX_INPUT_BYTES = 32 * 1024 * 1024
MAX_BOARD_ROWS = 50000
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z\Z")
_ENVELOPE_AUTHORITY = {
    "envelope_may_rank": False, "envelope_may_gate": False,
    "envelope_may_size": False, "envelope_may_execute": False,
    "policy_actions_require_individual_authority": True,
}
_AUTHORITY = {
    "can_rank": False, "can_change_population": False,
    "can_gate_new_entry": False, "can_originate_plan": False,
    "can_size": False, "can_manage_held_positions": False,
    "can_send_buy_alert": False, "can_execute": False,
}
_ENVELOPE_KEYS = frozenset({
    "schema", "definition_id", "market", "revision", "source_session", "as_of",
    "measured_state", "hazard_summary", "episodes", "policies", "policy_summary",
    "data_state", "repair_state", "coherence", "coverage", "freshness", "correction",
    "provenance", "authority", "bundle_id", "observed_at", "produced_at", "stale_after",
})


class MarketEligibilityError(ValueError):
    """A stable, non-payload-bearing contract refusal."""


def _canonical(value: Any) -> str:
    # Same serialization settings as the native envelope composer; finite-only
    # admission additionally prevents its default NaN allowance crossing here.
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False)
        encoded.encode("utf-8")  # Reject lone surrogates as well as nonfinite floats.
        return encoded
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise MarketEligibilityError("NON_CANONICAL_JSON") from exc


def _digest(value: Any) -> str:
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def _text(value: Any, code: str) -> str:
    if (not isinstance(value, str) or not value or len(value) > 512
            or any(ord(c) < 32 for c in value)):
        raise MarketEligibilityError(code)
    return value


def _utc(value: Any, code: str) -> datetime:
    if not isinstance(value, str) or not _UTC.fullmatch(value):
        raise MarketEligibilityError(code)
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00").astimezone(timezone.utc)
    except ValueError as exc:
        raise MarketEligibilityError(code) from exc


def _session(value: Any) -> str:
    try:
        if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
            raise ValueError
    except ValueError as exc:
        raise MarketEligibilityError("INVALID_EXPECTED_SESSION") from exc
    return value


def _hash(value: Any, code: str) -> str:
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        raise MarketEligibilityError(code)
    return value


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise MarketEligibilityError("DUPLICATE_JSON_KEY")
        out[key] = value
    return out


def _bad_constant(_: str) -> None:
    raise MarketEligibilityError("NON_FINITE_JSON")


def _load(raw: Any, code: str) -> dict[str, Any]:
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_INPUT_BYTES:
        raise MarketEligibilityError(code)
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_object,
                           parse_constant=_bad_constant)
        if not isinstance(value, dict):
            raise MarketEligibilityError(code)
        _canonical(value)  # Reject float overflow (e.g. 1e999), not just NaN tokens.
        return value
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise MarketEligibilityError(code) from exc


def _exact(a: Any, b: Any) -> bool:
    # Python equality would accept 0 == False and 1 == True at authority fields.
    return _canonical(a) == _canonical(b)


def _row_ref(row: Mapping[str, Any], index: int) -> dict[str, Any]:
    # Array location is an exact-board pointer, not a security/issuer/episode ID.
    # Never deduplicate aliases or manufacture a B1 identity here.
    prophet = row.get("prophet")
    return {
        "source_position": index + 1,
        "source_pointer": f"/buy/{index}",
        "source_row_sha256": _digest(row),
        "ticker": deepcopy(row.get("ticker")),
        "raw_lane": deepcopy(row.get("lane")),
        "raw_rank": deepcopy(prophet.get("rank") if isinstance(prophet, dict) else None),
        "raw_rank_basis": "prophet.rank" if isinstance(prophet, dict) and "rank" in prophet else None,
    }


def _check_envelope(doc: dict[str, Any], session: str, now: datetime,
                    cutoff: datetime) -> list[str]:
    errors: list[str] = []
    if set(doc) != _ENVELOPE_KEYS:
        return ["ENVELOPE_SHAPE_UNSUPPORTED"]
    if doc["schema"] != ENVELOPE_SCHEMA or doc["definition_id"] != ENVELOPE_DEFINITION:
        errors.append("ENVELOPE_DEFINITION_UNSUPPORTED")
    if doc["market"] != "US":
        errors.append("ENVELOPE_MARKET_MISMATCH")
    if doc["revision"] not in ("settled", "corrected"):
        errors.append("UNSETTLED_ENVELOPE")
    if doc["source_session"] != session or doc["as_of"] != session:
        errors.append("ENVELOPE_SESSION_MISMATCH")
    semantic = {k: v for k, v in doc.items()
                if k not in {"bundle_id", "observed_at", "produced_at", "stale_after"}}
    if doc["bundle_id"] != _digest(semantic)[:16]:
        errors.append("ENVELOPE_BUNDLE_MISMATCH")
    if not _exact(doc["authority"], _ENVELOPE_AUTHORITY):
        errors.append("ENVELOPE_AUTHORITY_UNSUPPORTED")
    # Native v0 supplies no policy objects. Presence is not permission to evaluate
    # caller-supplied rules. Empty/null/malformed are distinct, not truthiness.
    if not _exact(doc["policies"], []) or not _exact(doc["episodes"], []):
        errors.append("POLICY_PRODUCER_NOT_SUPPORTED")
    expected_policy = {"posture": "NORMAL", "active_policy_ids": [], "policy_count": 0,
                       "basis": "zero_active_policies", "display_only": True}
    if not _exact(doc["policy_summary"], expected_policy):
        errors.append("POLICY_SUMMARY_NOT_ZERO_POLICY")
    if doc["repair_state"] is not None:
        errors.append("REPAIR_PRODUCER_NOT_SUPPORTED")
    if doc["data_state"] != "FRESH":
        errors.append("ENVELOPE_DATA_NOT_FRESH")
    # A coverage summary can be FRESH while a required hazard is unmapped.
    # Missing interpretation is not a qualified risk reading, even in shadow.
    measured = doc["measured_state"]
    hazard = doc["hazard_summary"]
    if (not isinstance(measured, dict) or measured.get("usable") is not True
            or measured.get("verdict") not in ("RISK_ON", "MIXED", "RISK_OFF")):
        errors.append("ENVELOPE_MEASURED_STATE_UNAVAILABLE")
    if (not isinstance(hazard, dict)
            or hazard.get("stage") not in ("NONE", "FRAGILE", "TRANSMITTING", "BREAKDOWN")):
        errors.append("ENVELOPE_HAZARD_UNAVAILABLE")
    freshness = doc["freshness"]
    if (not isinstance(freshness, dict) or freshness.get("source_session") != session
            or freshness.get("all_on_session") is not True
            or not _exact(freshness.get("off_session_sources"), [])):
        errors.append("ENVELOPE_SOURCE_SESSION_UNQUALIFIED")
    coverage = doc["coverage"]
    per_source = freshness.get("per_source") if isinstance(freshness, dict) else None
    # FRESH is not clock qualification. Native optional sources can contribute
    # evidence while carrying as_of=None and all_on_session=True. This narrow
    # zero-policy intake requires every declared present source to be qualified;
    # it neither changes native source requirements nor changes live behavior.
    inventory: list[str] = []
    if (not isinstance(coverage, dict)
            or not all(isinstance(coverage.get(key), list)
                       for key in ("required", "optional", "fresh"))
            or not coverage["required"]
            or not _exact(coverage.get("missing"), [])
            or not _exact(coverage.get("stale"), [])):
        errors.append("ENVELOPE_COVERAGE_UNQUALIFIED")
    else:
        required, optional, fresh = (coverage[key] for key in ("required", "optional", "fresh"))
        if not all(isinstance(source, str) and source for source in required + optional + fresh):
            errors.append("ENVELOPE_COVERAGE_UNQUALIFIED")
        else:
            inventory = required + optional
            if (len(set(inventory)) != len(inventory)
                    or len(set(fresh)) != len(fresh)
                    or set(inventory) != set(fresh)
                    or type(coverage.get("source_count")) is not int
                    or coverage["source_count"] != len(inventory)):
                errors.append("ENVELOPE_COVERAGE_UNQUALIFIED")
    if not isinstance(per_source, dict):
        errors.append("ENVELOPE_SOURCE_CLOCKS_UNQUALIFIED")
    else:
        if set(per_source) != set(inventory):
            errors.append("ENVELOPE_COVERAGE_UNQUALIFIED")
        for source in inventory:
            entry = per_source.get(source)
            if (not isinstance(entry, dict) or entry.get("state") != "FRESH"
                    or entry.get("as_of") != session or entry.get("matches_session") is not True):
                errors.append("ENVELOPE_SOURCE_CLOCKS_UNQUALIFIED")
                break
    try:
        observed = _utc(doc["observed_at"], "ENVELOPE_CLOCK_INVALID")
        produced = _utc(doc["produced_at"], "ENVELOPE_CLOCK_INVALID")
        if not observed <= produced <= now:
            errors.append("ENVELOPE_NOT_AVAILABLE_AT_DECISION")
        if doc["stale_after"] is not None:
            expiry = _utc(doc["stale_after"], "ENVELOPE_EXPIRY_INVALID")
            if expiry <= produced or now >= expiry:
                errors.append("ENVELOPE_EXPIRED")
            if cutoff > expiry:
                errors.append("WINDOW_EXCEEDS_ENVELOPE_EXPIRY")
    except MarketEligibilityError as exc:
        errors.append(str(exc))
    return sorted(set(errors))


def compose_market_eligibility(
    raw_board: bytes, raw_envelope: bytes | None, *,
    expected_board_sha256: str, expected_board_definition: str,
    expected_source_session: str, expected_envelope_sha256: str | None,
    decision_at: str, valid_until: str,
) -> dict[str, Any]:
    """Return a lossless GD-6A SHADOW projection; never a new-long permission.

    Malformed board / caller binding is a hard refusal because there is no safe
    candidate denominator. Bad/missing envelope becomes one UNAVAILABLE disposition
    for each intact board row. The explicit validity window is caller-owned;
    this function creates no market calendar or inferred expiry policy.
    """
    expected_hash = _hash(expected_board_sha256, "INVALID_BOARD_HASH")
    definition = _text(expected_board_definition, "INVALID_BOARD_DEFINITION")
    session = _session(expected_source_session)
    if definition not in SUPPORTED_BOARD_DEFINITIONS:
        raise MarketEligibilityError("BOARD_DEFINITION_UNSUPPORTED")
    now = _utc(decision_at, "INVALID_DECISION_CLOCK")
    cutoff = _utc(valid_until, "INVALID_VALIDITY_CLOCK")
    if now >= cutoff or date.fromisoformat(session) > now.date():
        raise MarketEligibilityError("INVALID_PROJECTION_WINDOW")
    board = _load(raw_board, "BOARD_UNREADABLE")
    if sha256(raw_board).hexdigest() != expected_hash:
        raise MarketEligibilityError("BOARD_HASH_MISMATCH")
    if board.get("board_definition") != definition:
        raise MarketEligibilityError("BOARD_DEFINITION_OR_SESSION_MISMATCH")
    try:
        board_asof = _session(board.get("as_of"))
    except MarketEligibilityError as exc:
        raise MarketEligibilityError("BOARD_PUBLICATION_CLOCK_INVALID") from exc
    if not session <= board_asof <= now.date().isoformat():
        raise MarketEligibilityError("BOARD_PUBLICATION_CLOCK_INVALID")
    rows = board.get("buy")
    if (not isinstance(rows, list) or len(rows) > MAX_BOARD_ROWS
            or any(not isinstance(row, dict) for row in rows)):
        raise MarketEligibilityError("BOARD_POPULATION_UNREADABLE")
    if "market" in board and board["market"] != "US":
        raise MarketEligibilityError("BOARD_MARKET_MISMATCH")

    errors: list[str] = []
    health = board.get("staleness")
    if (not isinstance(health, dict) or health.get("price_through") != session
            or health.get("delayed") is not False or health.get("unknown") is not False
            or health.get("basis") != "panel_majority"):
        errors.append("BOARD_SOURCE_HEALTH_UNQUALIFIED")
    envelope: dict[str, Any] | None = None
    actual_envelope_hash = sha256(raw_envelope).hexdigest() if isinstance(raw_envelope, bytes) else None
    if expected_envelope_sha256 is not None:
        _hash(expected_envelope_sha256, "INVALID_ENVELOPE_HASH")
    if raw_envelope is None:
        errors.append("ENVELOPE_MISSING")
    elif expected_envelope_sha256 is None:
        errors.append("ENVELOPE_EXPECTED_HASH_MISSING")
    elif actual_envelope_hash != expected_envelope_sha256:
        errors.append("ENVELOPE_RAW_HASH_MISMATCH")
    else:
        try:
            envelope = _load(raw_envelope, "ENVELOPE_UNREADABLE")
            errors.extend(_check_envelope(envelope, session, now, cutoff))
        except MarketEligibilityError as exc:
            errors.append(str(exc))
    errors = sorted(set(errors))
    available = not errors
    disposition = {
        "state": "AVAILABLE" if available else "UNAVAILABLE",
        "action": "ELIGIBLE" if available else None,
        "action_meaning": "NO_MARKET_POLICY_CONSTRAINT_NOT_BUY_PERMISSION" if available else None,
        "policy_ids": [], "constraints": [],
        "reasons": ["ZERO_ACTIVE_POLICIES"] if available else errors,
    }
    out: dict[str, Any] = {
        "schema": SCHEMA, "definition_id": DEFINITION_ID, "mode": "SHADOW_ONLY",
        "implementation_scope": "NATIVE_V0_ZERO_POLICY_INTAKE_ONLY",
        "market": "US", "decision_at": decision_at, "valid_until": valid_until,
        "validity_basis": "EXPLICIT_CALLER_WINDOW_AND_NATIVE_SOURCE_SESSION",
        "board": {"sha256": expected_hash, "definition": definition,
                  "source_session": session, "source_board_asof": board_asof,
                  "population_pointer": "/buy", "row_count": len(rows)},
        "risk_envelope": {
            "sha256": actual_envelope_hash, "expected_sha256": expected_envelope_sha256,
            "bundle_id": envelope.get("bundle_id") if envelope else None,
            "definition_id": envelope.get("definition_id") if envelope else None,
        },
        "source_state": disposition["state"], "errors": errors,
        "production_behavior": "UNCHANGED",
        "authority": dict(_AUTHORITY),
        "rows": [{**_row_ref(row, i), "market_eligibility": deepcopy(disposition)}
                 for i, row in enumerate(rows)],
    }
    out["sidecar_id"] = "pme:" + _digest(out)
    return out


def bind_shadow_view(
    sidecar: Mapping[str, Any], raw_board: bytes, raw_envelope: bytes | None, *,
    expected_board_sha256: str, expected_board_definition: str,
    expected_source_session: str, expected_envelope_sha256: str | None,
    expected_decision_at: str, expected_valid_until: str, read_at: str,
) -> dict[str, Any]:
    """Rebind an exact sidecar to complete raw rows for a read-only consumer.

    Every semantic field is recomputed using independently supplied binding facts.
    A self-consistent forged hash/permission/row/expiry cannot pass by rehashing.
    This makes no browser join and never mints a plan, entry, alert or trade.
    """
    if not isinstance(sidecar, Mapping):
        raise MarketEligibilityError("SIDECAR_NOT_OBJECT")
    expected = compose_market_eligibility(
        raw_board, raw_envelope, expected_board_sha256=expected_board_sha256,
        expected_board_definition=expected_board_definition,
        expected_source_session=expected_source_session,
        expected_envelope_sha256=expected_envelope_sha256,
        decision_at=expected_decision_at, valid_until=expected_valid_until,
    )
    if not _exact(dict(sidecar), expected):
        raise MarketEligibilityError("SIDECAR_SEMANTIC_MISMATCH")
    now = _utc(read_at, "INVALID_READ_CLOCK")
    if not _utc(expected_decision_at, "INVALID_DECISION_CLOCK") <= now < _utc(expected_valid_until, "INVALID_VALIDITY_CLOCK"):
        raise MarketEligibilityError("SIDECAR_OUTSIDE_VALIDITY_WINDOW")
    board = _load(raw_board, "BOARD_UNREADABLE")
    return {
        "sidecar_id": expected["sidecar_id"], "mode": "SHADOW_ONLY",
        "production_behavior": "UNCHANGED", "authority": dict(_AUTHORITY),
        "source_state": expected["source_state"], "errors": list(expected["errors"]),
        "rows": [{"candidate": deepcopy(candidate), "sidecar": deepcopy(row)}
                 for candidate, row in zip(board["buy"], expected["rows"], strict=True)],
    }


# Individually authorized-policy consumption, separate from the V0 shadow
# definition above. There is deliberately no production grant or config switch
# here. expected_rule_hashes is an INTERNAL trusted-owner input: a public caller
# must never supply both it and the records it purportedly authorizes. Hashes
# verify an already accepted source identity; they do not mint authority.
from dataclasses import dataclass

_POLICY_KEYS = frozenset({
    "policy_id", "rule_id", "rule_version", "authority_basis", "grant_ref",
    "action", "state", "market", "board_definition", "lifecycle", "tickers",
    "starts_at", "expires_at", "restore_condition",
})


@dataclass(frozen=True)
class NewLongRestrictionRead:
    """Immutable, subtract-only read for an explicitly adopted internal caller.

    It cannot authorize a buy, rank, position size, liquidation or alert. The
    existing source/grant owner supplies accepted records and a read-validity
    window. No policy detector, registry, ledger or scheduler is added here.
    """
    board_digest: str
    records: tuple[str, ...]
    observed_at: str
    valid_until: str
    errors: tuple[str, ...]

    def bind_board(self, board: Mapping[str, Any]) -> None:
        if _digest(board) != self.board_digest:
            raise MarketEligibilityError("POLICY_BOARD_BINDING_MISMATCH")

    def decision(self, ticker: str, *, read_at: str) -> dict[str, Any]:
        now = _utc(read_at, "POLICY_READ_CLOCK_INVALID")
        start = _utc(self.observed_at, "POLICY_OBSERVATION_INVALID")
        cutoff = _utc(self.valid_until, "POLICY_VALIDITY_INVALID")
        if not start <= now < cutoff:
            return {"state": "UNAVAILABLE", "policy_ids": [], "rules": [],
                    "errors": ["POLICY_READ_OUTSIDE_VALIDITY"]}
        matched = []
        for encoded in self.records:
            policy = json.loads(encoded)
            if (policy["state"] == "ACTIVE"
                    and _utc(policy["starts_at"], "POLICY_START_INVALID") <= now
                    < _utc(policy["expires_at"], "POLICY_EXPIRY_INVALID")
                    and (policy["tickers"] == ["*"] or ticker in policy["tickers"])):
                matched.append({k: policy[k] for k in (
                    "policy_id", "rule_id", "rule_version", "grant_ref", "action",
                    "authority_basis", "expires_at", "restore_condition")})
        # A source gap never erases a still-valid, separately accepted restriction.
        # All applicable rules survive; there is no voting, score or bullish offset.
        state = "DENY_NEW_LONG" if matched else (
            "UNAVAILABLE" if self.errors else "NO_POLICY_CONSTRAINT")
        return {"state": state, "policy_ids": [p["policy_id"] for p in matched],
                "rules": matched, "errors": list(self.errors)}


def bind_new_long_restrictions(
    board: Mapping[str, Any], records: list[dict[str, Any]], *,
    expected_rule_hashes: Mapping[str, str], observed_at: str,
    valid_until: str, source_available: bool = True,
) -> NewLongRestrictionRead:
    """Bind policy-owner receipts without accepting a new financial-policy grant.

    The caller must already have adoption and individual rule authority from the
    existing owner. No native caller is automatically opted in. A malformed,
    missing or unrecognized expected record makes the controlled action unknown,
    never a fabricated all-clear. Future/expired/revoked accepted rules cannot
    cancel another active rule. Only US board new-long restrictions are supported.
    """
    if not isinstance(board, Mapping) or board.get("board_definition") not in SUPPORTED_BOARD_DEFINITIONS:
        raise MarketEligibilityError("POLICY_BOARD_DEFINITION_UNSUPPORTED")
    start = _utc(observed_at, "POLICY_OBSERVATION_INVALID")
    end = _utc(valid_until, "POLICY_VALIDITY_INVALID")
    if end <= start:
        raise MarketEligibilityError("POLICY_WINDOW_INVALID")
    if not isinstance(expected_rule_hashes, Mapping) or not expected_rule_hashes or len(expected_rule_hashes) > 128:
        raise MarketEligibilityError("POLICY_OWNER_BINDING_REQUIRED")
    approved = {}
    for key, value in expected_rule_hashes.items():
        approved[_text(key, "POLICY_EXPECTED_ID_INVALID")] = _hash(value, "POLICY_EXPECTED_HASH_INVALID")
    errors = [] if source_available is True else ["POLICY_SOURCE_UNAVAILABLE"]
    if not isinstance(records, list) or len(records) > 128:
        records = []
        errors.append("POLICY_RECORDS_UNREADABLE")
    seen = set()
    accepted = []
    for record in records:
        try:
            if not isinstance(record, dict) or set(record) != _POLICY_KEYS:
                raise MarketEligibilityError("POLICY_RECORD_SHAPE_INVALID")
            pid = _text(record["policy_id"], "POLICY_ID_INVALID")
            if pid in seen:
                raise MarketEligibilityError("POLICY_ID_DUPLICATE")
            seen.add(pid)
            if approved.get(pid) != _digest(record):
                raise MarketEligibilityError("POLICY_OWNER_DIGEST_MISMATCH")
            for field in ("rule_id", "rule_version", "grant_ref", "restore_condition"):
                _text(record[field], "POLICY_" + field.upper() + "_INVALID")
            if record["authority_basis"] not in {"earned", "temporary_operator_safety", "emergency_user_opt_in"}:
                raise MarketEligibilityError("POLICY_AUTHORITY_BASIS_UNSUPPORTED")
            if record["action"] not in {"SUPPRESS_NEW_ENTRY", "NO_NEW_LONG_RISK"}:
                raise MarketEligibilityError("POLICY_ACTION_UNSUPPORTED")
            if record["state"] not in {"ACTIVE", "REVOKED"}:
                raise MarketEligibilityError("POLICY_STATE_UNSUPPORTED")
            if (record["market"] != "US" or record["lifecycle"] != "NEW_LONG_RECOMMENDATION"
                    or record["board_definition"] != board["board_definition"]):
                raise MarketEligibilityError("POLICY_SCOPE_MISMATCH")
            names = record["tickers"]
            if (not isinstance(names, list) or not names or len(names) > MAX_BOARD_ROWS
                    or any(not isinstance(n, str) or not n or len(n) > 32 or n != n.upper() or n != n.strip() for n in names)
                    or names != sorted(set(names)) or ("*" in names and names != ["*"])):
                raise MarketEligibilityError("POLICY_TICKER_SCOPE_INVALID")
            if _utc(record["expires_at"], "POLICY_EXPIRY_INVALID") <= _utc(record["starts_at"], "POLICY_START_INVALID"):
                raise MarketEligibilityError("POLICY_RULE_WINDOW_INVALID")
            accepted.append(_canonical(record))
        except MarketEligibilityError as exc:
            errors.append(str(exc))
    if set(approved) != seen:
        errors.append("POLICY_EXPECTED_SET_INCOMPLETE")
    accepted.sort(key=lambda text: json.loads(text)["policy_id"])
    return NewLongRestrictionRead(
        board_digest=_digest(board), records=tuple(accepted), observed_at=observed_at,
        valid_until=valid_until, errors=tuple(sorted(set(errors))),
    )


def project_new_long_intake(
    intake: Mapping[str, Any], restrictions: NewLongRestrictionRead, *, read_at: str,
) -> dict[str, Any]:
    """Publish the native disposition, never reclassify a missing row as a bad chart.

    Called only by the explicitly adopted internal builder. Recompute each policy
    disposition from the same immutable read before exposing its accounting. This
    proves composition with an already accepted source, not a grant or live policy.
    """
    if not isinstance(restrictions, NewLongRestrictionRead):
        raise MarketEligibilityError("POLICY_READ_TYPE_INVALID")
    if not isinstance(intake, Mapping) or intake.get("market_policy_mode") != "EXPLICIT_INTERNAL_ADOPTION":
        raise MarketEligibilityError("POLICY_INTAKE_MODE_INVALID")
    counts = {}
    for key in ("admitted", "duplicate_id_blocked", "reorigination_blocked",
                "market_policy_suppressed", "eligible_after_skips", "validation_failed",
                "originated", "unaccounted"):
        n = intake.get(key)
        if not isinstance(n, int) or isinstance(n, bool) or n < 0:
            raise MarketEligibilityError("POLICY_INTAKE_COUNT_INVALID")
        counts[key] = n
    if (counts["unaccounted"] != 0 or intake.get("lossless") is not True
            or counts["admitted"] != sum(counts[k] for k in (
                "duplicate_id_blocked", "reorigination_blocked", "market_policy_suppressed",
                "validation_failed", "originated"))
            or counts["eligible_after_skips"] != counts["validation_failed"] + counts["originated"]):
        raise MarketEligibilityError("POLICY_INTAKE_BALANCE_INVALID")
    rows = intake.get("market_policy_dispositions")
    failures = intake.get("validation_failures")
    if (not isinstance(rows, list) or len(rows) > MAX_BOARD_ROWS
            or not isinstance(failures, list) or len(failures) != counts["validation_failed"]
            or any(not isinstance(f, dict) for f in failures)):
        raise MarketEligibilityError("POLICY_INTAKE_ROWS_INVALID")
    identity_failures = sum(f.get("stage") == "candidate_identity" for f in failures)
    if len(rows) != counts["admitted"] - counts["duplicate_id_blocked"] - counts["reorigination_blocked"] - identity_failures:
        raise MarketEligibilityError("POLICY_INTAKE_POPULATION_MISMATCH")
    denied = unavailable = 0
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise MarketEligibilityError("POLICY_INTAKE_ROW_INVALID")
        pid = _text(row.get("id"), "POLICY_PLAN_ID_INVALID")
        ticker = _text(row.get("ticker"), "POLICY_TICKER_INVALID")
        if pid in seen:
            raise MarketEligibilityError("POLICY_INTAKE_DUPLICATE")
        seen.add(pid)
        expected = {"ticker": ticker, "id": pid, **restrictions.decision(ticker, read_at=read_at)}
        if not _exact(row, expected):
            raise MarketEligibilityError("POLICY_INTAKE_DISPOSITION_MISMATCH")
        denied += row["state"] == "DENY_NEW_LONG"
        unavailable += row["state"] == "UNAVAILABLE"
    if denied + unavailable != counts["market_policy_suppressed"]:
        raise MarketEligibilityError("POLICY_INTAKE_SUPPRESSION_MISMATCH")
    return {
        "market_policy_mode": "EXPLICIT_INTERNAL_ADOPTION",
        "market_policy_suppressed": denied + unavailable,
        "market_policy_denied": denied,
        "market_policy_unavailable": unavailable,
        "market_policy_dispositions": deepcopy(rows),
        "market_policy_read": {
            "board_digest": restrictions.board_digest,
            "observed_at": restrictions.observed_at,
            "valid_until": restrictions.valid_until,
            "read_at": read_at,
            "capability": "SUBTRACT_ONLY_NEW_LONG_RECOMMENDATION",
            "not_buy_permission": True,
        },
    }


def new_long_candidate_card_context(
    card: Mapping[str, Any], candidate: Mapping[str, Any], board: Mapping[str, Any], *,
    restrictions: NewLongRestrictionRead | None = None, read_at: str | None = None,
) -> dict[str, Any]:
    """Bind a prospective candidate's presentation to the existing policy read.

    This is a read-side projection for the existing shared card, not an HTTP
    endpoint, a fresh grant, an entry validator or an alert sender. Neither the
    caller's original research row nor the card's technical fields are changed.
    The policy owner must supply the trusted current read. No read means exact
    legacy rendering; an explicitly supplied unusable read never means Buy.
    Existing-position/lifecycle cards are a different intent and are refused here.
    """
    if not isinstance(card, Mapping):
        raise MarketEligibilityError("POLICY_CARD_INVALID")
    out = deepcopy(dict(card))
    if restrictions is None:
        if read_at is not None or "new_long_policy" in out:
            raise MarketEligibilityError("POLICY_CARD_UNBOUND_INPUT")
        return out
    if not isinstance(restrictions, NewLongRestrictionRead):
        raise MarketEligibilityError("POLICY_READ_TYPE_INVALID")
    if (card.get("record_only") is True or card.get("lifecycle") or card.get("life")
            or str(card.get("mkt") or "").lower() not in {"us", "usa"}):
        raise MarketEligibilityError("POLICY_CARD_INTENT_MISMATCH")
    restrictions.bind_board(board)
    if not isinstance(candidate, Mapping):
        raise MarketEligibilityError("POLICY_CARD_CANDIDATE_INVALID")
    rows = board.get("buy")
    fingerprint = _digest(candidate)
    if (not isinstance(rows, list) or len(rows) > MAX_BOARD_ROWS
            or not any(isinstance(row, Mapping) and _digest(row) == fingerprint for row in rows)):
        raise MarketEligibilityError("POLICY_CARD_CANDIDATE_MISMATCH")
    ticker = _text(candidate.get("ticker"), "POLICY_CARD_TICKER_INVALID").strip().upper()
    if str(card.get("tk") or "").strip().upper() != ticker:
        raise MarketEligibilityError("POLICY_CARD_TICKER_MISMATCH")
    decision = restrictions.decision(ticker, read_at=read_at)
    out["new_long_policy"] = {
        "schema": "prophet.new_long_card/v1", "market": "US",
        "lifecycle": "NEW_LONG_RECOMMENDATION", "ticker": ticker,
        "board_digest": restrictions.board_digest, "candidate_digest": fingerprint,
        "checked_at": read_at, "valid_until": restrictions.valid_until,
        "not_buy_permission": True, **deepcopy(decision),
    }
    return out

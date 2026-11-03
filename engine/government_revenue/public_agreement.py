# engine/government_revenue/public_agreement.py
"""Identity and payload validation for the public_agreement documentary contract.

This helper is intentionally narrow: it validates the shape and clocks of one
public_agreement observation row, computes its canonical content identity, and
checks the qualified source receipt metadata in evidence_index. Actual source
bytes, literal replay and rights remain the existing owner/caller obligations.
The parent graph owns predecessor existence, retire overrides and PIT.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping
from urllib.parse import urlsplit


AGREEMENT_KEYS: frozenset = frozenset(
    {
        "id",
        "revision",
        "source_url",
        "program_label",
        "umbrella_label",
        "agreement_form",
        "parties",
        "collective_value",
        "expected_launch_year",
        "published_on",
        "known_at",
        "verification_state",
        "evidence_refs",
        "predecessor_id",
        "succession_reason",
    }
)

EXACT_AGREEMENT_FORM = "firm_fixed_price_ota_prototype"
EXACT_VERIFICATION_STATE = "reviewed"
EXACT_SUCCESSION_REVISED = "corrected"

_MONEY_UNITS: frozenset = frozenset({"USD_million", "USD_billion"})
_EVIDENCE_CLASSES: frozenset = frozenset(
    {"official_contract_announcement", "issuer_disclosure"}
)
_OFFICIAL_HOST = "www.sda.mil"
_ISSUER_HOST = "www.l3harris.com"
_PUBLIC_AGREEMENT_SCOPE = "public_agreement"

_PARTY_KEYS: frozenset = frozenset(
    {"name_literal", "entity_id", "potential_value", "announced_vehicles"}
)
_VALUE_KEYS: frozenset = frozenset({"value", "unit", "approximate"})
_COLLECTIVE_KEYS: frozenset = frozenset(
    {"value", "unit", "approximate", "overlaps_named_party_values"}
)

_PREDECESSOR_RE = re.compile(r"^prog-agreement:[a-f0-9]{24}$")
_EVIDENCE_REF_RE = re.compile(r"^ev:[a-f0-9]{12}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


# ---------------------------------------------------------------------------
# Atomic helpers
# ---------------------------------------------------------------------------


def _is_finite_real_number(value: Any) -> bool:
    """A real number that is not bool and not NaN/Inf."""
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    return False


def _parse_utc_clock(value: Any):
    """Parse a strict UTC clock: trailing Z or explicit +00:00, not naive/date-only."""
    if not isinstance(value, str):
        return None
    if value.endswith("Z"):
        candidate = value[:-1] + "+00:00"
    elif value.endswith("+00:00"):
        candidate = value
    else:
        return None
    try:
        dt = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    if dt.utcoffset() != timedelta(0):
        return None
    return dt.astimezone(timezone.utc)


def _parse_iso_ymd(value: Any):
    if not isinstance(value, str):
        return None
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _check_text_label(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if value != value.strip():
        return False
    if len(value) == 0:
        return False
    if len(value) > 256:
        return False
    if any(unicodedata.category(ch) in {"Cc", "Cf", "Zl", "Zp"} for ch in value):
        return False
    return True


def _split_source_url(value: Any):
    """Return urlsplit result for a strict HTTPS URL, or None on any violation."""
    if not isinstance(value, str):
        return None
    for ch in value:
        code = ord(ch)
        if code < 0x20 or code == 0x7F:
            return None
        if ch in " \t\n\r\v\f\\":
            return None
    if value != value.strip():
        return None
    if not value.startswith("https://"):
        return None
    try:
        parts = urlsplit(value)
    except ValueError:
        return None
    if parts.scheme != "https":
        return None
    if parts.username is not None or parts.password is not None:
        return None
    try:
        if parts.port is not None:
            return None
    except ValueError:
        return None
    if not parts.hostname or not parts.path.startswith("/"):
        return None
    return parts


def _validate_money_block(
    block: Any,
    prefix: str,
    errors: list,
    *,
    require_overlaps: bool,
) -> bool:
    if not isinstance(block, Mapping):
        errors.append(f"{prefix}:must_be_object")
        return False
    required = _COLLECTIVE_KEYS if require_overlaps else _VALUE_KEYS
    keys = set(block.keys())
    for unknown in sorted(keys - required):
        errors.append(f"{prefix}:unknown_key:{unknown}")
    for missing in sorted(required - keys):
        errors.append(f"{prefix}:missing_key:{missing}")
    if (keys - required) or (required - keys):
        return False
    if not _is_finite_real_number(block["value"]) or block["value"] <= 0:
        errors.append(f"{prefix}:invalid_value")
    if not isinstance(block["unit"], str) or block["unit"] not in _MONEY_UNITS:
        errors.append(f"{prefix}:invalid_unit")
    if not isinstance(block["approximate"], bool):
        errors.append(f"{prefix}:invalid_approximate")
    if require_overlaps and block["overlaps_named_party_values"] is not True:
        errors.append(f"{prefix}:overlaps_must_be_true")
    return True


def _expected_evidence_id(sha256: str):
    return "ev:" + sha256[:12]


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


def agreement_assertion_id(row: Mapping) -> str:
    """Compute the canonical content identity for an agreement row.

    The hash covers every key in AGREEMENT_KEYS except ``id`` itself, with
    ``evidence_refs`` sorted but ``parties`` preserved in source order.
    Raises ``KeyError`` for missing/extra row keys and ``ValueError`` for
    values that cannot be canonicalized (NaN, Inf, non-serializable types).
    """
    if not isinstance(row, Mapping):
        raise ValueError("row must be a mapping")
    keys = set(row.keys())
    if keys != AGREEMENT_KEYS:
        missing = sorted(AGREEMENT_KEYS - keys)
        extra = sorted(keys - AGREEMENT_KEYS)
        raise KeyError(
            "agreement row keys mismatch: missing={} extra={}".format(missing, extra)
        )

    canonical = {}
    for key in AGREEMENT_KEYS:
        if key == "id":
            continue
        value = row[key]
        if key == "evidence_refs":
            if not isinstance(value, list):
                raise ValueError("evidence_refs must be a list")
            try:
                canonical[key] = sorted(value)
            except TypeError as exc:
                raise ValueError("evidence_refs must be comparable strings") from exc
        elif key == "parties":
            if not isinstance(value, list):
                raise ValueError("parties must be a list")
            canonical[key] = list(value)
        else:
            canonical[key] = value

    try:
        encoded = json.dumps(
            canonical,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("canonical JSON failed: {}".format(exc)) from exc

    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return "prog-agreement:" + digest[:24]


# ---------------------------------------------------------------------------
# Payload validation
# ---------------------------------------------------------------------------


def agreement_payload_errors(
    row: Any,
    evidence_index: Any,
    *,
    graph_known_at: Any,
) -> list:
    """Return a list of stable ``public_agreement_*`` error strings.

    An empty list means the row is structurally valid against this contract.
    Never raises on malformed input; the loader accumulates these strings.
    """
    errors: list = []

    graph_dt = _parse_utc_clock(graph_known_at)
    if graph_dt is None:
        errors.append("public_agreement_graph_known_at_malformed")

    if not isinstance(row, Mapping):
        errors.append("public_agreement_row_must_be_object")
        return errors

    row_keys = set(row.keys())
    for missing in sorted(AGREEMENT_KEYS - row_keys):
        errors.append("public_agreement_missing_key:{}".format(missing))
    for unknown in sorted(row_keys - AGREEMENT_KEYS):
        errors.append("public_agreement_unknown_key:{}".format(unknown))
    if row_keys != AGREEMENT_KEYS:
        return errors

    # --- source_url
    parts = _split_source_url(row["source_url"])
    if parts is None:
        errors.append("public_agreement_invalid_source_url")
        host = None
    else:
        host = parts.hostname

    # --- text labels
    if not _check_text_label(row["program_label"]):
        errors.append("public_agreement_invalid_program_label")
    umbrella = row["umbrella_label"]
    if umbrella is not None and not _check_text_label(umbrella):
        errors.append("public_agreement_invalid_umbrella_label")

    # --- agreement_form
    if row["agreement_form"] != EXACT_AGREEMENT_FORM:
        errors.append("public_agreement_invalid_agreement_form")

    # --- verification_state
    if row["verification_state"] != EXACT_VERIFICATION_STATE:
        errors.append("public_agreement_invalid_verification_state")

    # --- revision and predecessor chain
    revision = row["revision"]
    revision_valid = (
        not isinstance(revision, bool)
        and isinstance(revision, int)
        and revision >= 1
    )
    if not revision_valid:
        errors.append("public_agreement_invalid_revision")
    predecessor = row["predecessor_id"]
    succession = row["succession_reason"]
    if revision_valid and revision == 1:
        if predecessor is not None:
            errors.append("public_agreement_first_revision_predecessor_must_be_null")
        if succession is not None:
            errors.append("public_agreement_first_revision_succession_must_be_null")
    elif revision_valid and revision > 1:
        if not isinstance(predecessor, str) or not _PREDECESSOR_RE.fullmatch(predecessor):
            errors.append("public_agreement_invalid_predecessor_id")
        if succession != EXACT_SUCCESSION_REVISED:
            errors.append("public_agreement_invalid_succession_reason")

    # --- known_at
    known_dt = _parse_utc_clock(row["known_at"])
    if known_dt is None:
        errors.append("public_agreement_invalid_known_at")
    if known_dt is not None and graph_dt is not None and known_dt > graph_dt:
        errors.append("public_agreement_known_at_after_graph")

    # --- published_on
    published_date = _parse_iso_ymd(row["published_on"])
    if published_date is None:
        errors.append("public_agreement_invalid_published_on")
    elif known_dt is not None and published_date > known_dt.date():
        errors.append("public_agreement_published_after_known_at")

    # --- expected_launch_year
    target_year = row["expected_launch_year"]
    if target_year is not None:
        if (
            isinstance(target_year, bool)
            or not isinstance(target_year, int)
            or target_year < 1900
            or target_year > 2200
        ):
            errors.append("public_agreement_invalid_expected_launch_year")

    # --- collective_value
    collective = row["collective_value"]
    if collective is not None:
        _validate_money_block(
            collective,
            "public_agreement_collective_value",
            errors,
            require_overlaps=True,
        )

    # --- parties
    parties = row["parties"]
    parties_iterable: list = []
    if not isinstance(parties, list) or len(parties) == 0 or len(parties) > 8:
        errors.append("public_agreement_invalid_parties_count")
    else:
        parties_iterable = parties

    seen_literals: set = set()
    for index, party in enumerate(parties_iterable):
        prefix = "public_agreement_party_{}".format(index)
        if not isinstance(party, Mapping):
            errors.append("{}:must_be_object".format(prefix))
            continue
        party_keys = set(party.keys())
        for missing in sorted(_PARTY_KEYS - party_keys):
            errors.append("{}:missing_key:{}".format(prefix, missing))
        for unknown in sorted(party_keys - _PARTY_KEYS):
            errors.append("{}:unknown_key:{}".format(prefix, unknown))
        if party_keys != _PARTY_KEYS:
            continue
        name_literal = party["name_literal"]
        if not _check_text_label(name_literal):
            errors.append("{}:invalid_name_literal".format(prefix))
        else:
            trimmed = name_literal.strip()
            if trimmed in seen_literals:
                errors.append("{}:duplicate_name_literal".format(prefix))
            else:
                seen_literals.add(trimmed)
        if party["entity_id"] is not None:
            errors.append("{}:entity_id_must_be_null".format(prefix))
        _validate_money_block(
            party["potential_value"],
            "{}:potential_value".format(prefix),
            errors,
            require_overlaps=False,
        )
        vehicles = party["announced_vehicles"]
        if vehicles is not None:
            if (
                isinstance(vehicles, bool)
                or not isinstance(vehicles, int)
                or vehicles < 1
            ):
                errors.append("{}:invalid_announced_vehicles".format(prefix))

    # --- evidence_refs
    evidence_refs = row["evidence_refs"]
    ev_id = None
    if not isinstance(evidence_refs, list) or len(evidence_refs) != 1:
        errors.append("public_agreement_invalid_evidence_refs_count")
    else:
        candidate = evidence_refs[0]
        if isinstance(candidate, str) and _EVIDENCE_REF_RE.fullmatch(candidate):
            ev_id = candidate
        else:
            errors.append("public_agreement_invalid_evidence_ref_format")

    # --- evidence_index
    evidence = None
    if ev_id is not None:
        if not isinstance(evidence_index, Mapping):
            errors.append("public_agreement_invalid_evidence_index")
        elif ev_id not in evidence_index:
            errors.append("public_agreement_missing_evidence_ref")
        else:
            evidence = evidence_index[ev_id]

    if ev_id is not None and not isinstance(evidence, Mapping):
        errors.append("public_agreement_evidence_must_be_object")
    if isinstance(evidence, Mapping):
        # evidence_class
        ev_class = evidence.get("evidence_class")
        if not isinstance(ev_class, str) or ev_class not in _EVIDENCE_CLASSES:
            errors.append("public_agreement_invalid_evidence_class")

        # source URLs match
        if evidence.get("source_url") != row["source_url"]:
            errors.append("public_agreement_evidence_source_url_mismatch")
        if evidence.get("retrieved_from_url") != row["source_url"]:
            errors.append("public_agreement_evidence_retrieved_url_mismatch")

        # claim_scopes contains public_agreement
        scopes = evidence.get("claim_scopes")
        if not isinstance(scopes, list) or _PUBLIC_AGREEMENT_SCOPE not in scopes:
            errors.append("public_agreement_evidence_missing_scope")

        # sha256 + evidence_id agreement
        sha = evidence.get("sha256")
        sha_valid = isinstance(sha, str) and bool(_SHA256_RE.fullmatch(sha))
        if not sha_valid:
            errors.append("public_agreement_invalid_evidence_sha256")
        else:
            expected_id = _expected_evidence_id(sha)
            if evidence.get("evidence_id") != expected_id:
                errors.append("public_agreement_evidence_id_field_mismatch")
            if expected_id != ev_id:
                errors.append("public_agreement_evidence_ref_sha256_mismatch")

        # clocks
        retrieved_dt = _parse_utc_clock(evidence.get("retrieved_at"))
        if retrieved_dt is None:
            errors.append("public_agreement_invalid_evidence_retrieved_at")
        evidence_known_dt = _parse_utc_clock(evidence.get("known_at"))
        if evidence_known_dt is None:
            errors.append("public_agreement_invalid_evidence_known_at")
        if retrieved_dt is not None and evidence_known_dt is not None:
            if evidence_known_dt < retrieved_dt:
                errors.append("public_agreement_evidence_known_before_retrieved")
        if evidence_known_dt is not None and known_dt is not None:
            if known_dt < evidence_known_dt:
                errors.append("public_agreement_known_at_before_evidence_known_at")
        if evidence_known_dt is not None and published_date is not None:
            if published_date > evidence_known_dt.date():
                errors.append("public_agreement_published_after_evidence_known_at")

        # host and pin checks (only meaningful when class is valid)
        if ev_class == "official_contract_announcement":
            if host != _OFFICIAL_HOST:
                errors.append("public_agreement_invalid_official_source_host")
        elif ev_class == "issuer_disclosure":
            if host != _ISSUER_HOST:
                errors.append("public_agreement_invalid_issuer_source_host")
            if evidence.get("pinned_issuer_host") != _ISSUER_HOST:
                errors.append("public_agreement_invalid_issuer_pin_host")
            basis = evidence.get("pinned_issuer_host_basis")
            if not isinstance(basis, str) or len(basis.strip()) == 0:
                errors.append("public_agreement_invalid_issuer_pin_basis")

    # --- identity check (last so partial rows still report upstream issues)
    try:
        expected_id = agreement_assertion_id(row)
        if row["id"] != expected_id:
            errors.append("public_agreement_identity_mismatch")
    except (KeyError, TypeError, ValueError):
        errors.append("public_agreement_identity_uncanonicalizable")

    return errors

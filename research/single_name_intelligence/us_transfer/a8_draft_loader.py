"""SNI-local DRAFT loader for the A8 US residual-transfer preregistration contract.

DRAFT ONLY. Descriptive-only. Does not register or seal anything. Does not
mint identity ids. Does not read parquet, network, or engine modules.

This module CONSUMES owner-supplied values from Data OS identity, Company
Event/Earnings, FIF, Capital Structure, Stock Identity, Options, Research
Vault, and qledger/Evaluation. It does not fork or re-implement those
owners. Canonical issuer and security identifiers are caller-supplied
opaque strings owned by Stock Identity / Data OS; unknown identity stays
UNRESOLVED / null.

All six authority flags stay false everywhere: rank_authority,
gate_authority, size_authority, signal_authority, escalation_authority,
trade_authority. A caller that sets any of them to a truthy value is
refused (raise). Nothing in this draft feeds a ranker, gate, sizer,
signal, escalation path, or trade path.
"""
from __future__ import annotations

import json
from pathlib import Path

REFUSAL_CODES = frozenset(
    {
        "REGISTERED_NOT_FALSE",
        "AUTHORITY_TRUTHY",
        "IDENTITY_NON_NULL",
        "COHORT_NOT_HINDSIGHT",
        "COHORT_SURVIVORSHIP_NOT_TRUE",
        "HORIZONS_MISMATCH",
        "CELL_COUNT_MISMATCH",
        "THEN_KNOWN_INCOMPLETE",
        "BANNED_PHRASE",
        "UNKNOWN_TOP_LEVEL_KEY",
    }
)

ALLOWED_TOP_LEVEL_KEYS = frozenset(
    {
        "module_docstring",
        "family_id",
        "version",
        "status",
        "registered",
        "outcome",
        "drafted_by",
        "drafted_at",
        "registration_note",
        "data_read",
        "authority_flags",
        "s0_blobs",
        "input_pins",
        "engine_citations",
        "cohort",
        "names",
        "horizons",
        "arms",
        "cells",
        "benches",
        "then_known",
        "splits",
        "p01_copy",
        "budget",
        "multiplicity",
        "grading",
        "identity",
        "kill_retirement",
        "registration_gate",
        "frozen_decisions",
        "labels",
    }
)

AUTHORITY_KEY_NAMES = frozenset(
    {
        "rank_authority",
        "gate_authority",
        "size_authority",
        "signal_authority",
        "escalation_authority",
        "trade_authority",
    }
)

IDENTITY_KEY_NAMES = frozenset(
    {
        "canonical_issuer_id",
        "security_id",
    }
)

THEN_KNOWN_FIELDS = ("fact", "effective_date_or_null", "source", "treatment")

BANNED_PHRASES = (
    "validated",
    "transfer shown",
    "forecast skill",
    "calibrated",
    "P07",
)

REQUIRED_HORIZONS = [5, 21, 63]

_TRUTHY_STRINGS = frozenset({"true", "yes", "1", "y"})


class A8DraftRefused(Exception):
    """Raised when the DRAFT JSON is in an unsafe state. ``code`` is a REFUSAL_CODES member."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        if detail:
            super().__init__(f"{code}: {detail}")
        else:
            super().__init__(code)


def _refuse(code: str, detail: str = "") -> None:
    if code not in REFUSAL_CODES:
        raise RuntimeError(f"loader bug: {code!r} is not in REFUSAL_CODES")
    raise A8DraftRefused(code, detail)


def _norm_key(key: object) -> str:
    if not isinstance(key, str):
        return ""
    return key.strip().lower().replace("-", "_")


def _authority_value_is_truthy(value: object) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value != 0:
        return True
    if isinstance(value, str) and value.strip().lower() in _TRUTHY_STRINGS:
        return True
    return False


def _walk(obj: object):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _walk(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk(item)


def _string_values(obj: object):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from _string_values(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _string_values(item)


def validate_draft(draft: dict) -> None:
    """Refuse unsafe DRAFT states. Never registers, seals, or reads market data."""
    if not isinstance(draft, dict):
        _refuse("UNKNOWN_TOP_LEVEL_KEY", "draft is not an object")

    unknown = [key for key in draft.keys() if key not in ALLOWED_TOP_LEVEL_KEYS]
    if unknown:
        _refuse("UNKNOWN_TOP_LEVEL_KEY", ",".join(sorted(map(str, unknown))))

    if draft.get("registered") is not False:
        _refuse("REGISTERED_NOT_FALSE", repr(draft.get("registered")))

    for node in _walk(draft):
        for key, value in node.items():
            norm = _norm_key(key)
            if norm in AUTHORITY_KEY_NAMES and _authority_value_is_truthy(value):
                _refuse("AUTHORITY_TRUTHY", f"{key}={value!r}")
            if norm in IDENTITY_KEY_NAMES and value is not None:
                _refuse("IDENTITY_NON_NULL", f"{key}={value!r}")

    for text in _string_values(draft):
        lowered = text.lower()
        for phrase in BANNED_PHRASES:
            if phrase.lower() in lowered:
                _refuse("BANNED_PHRASE", phrase)

    cohort = draft.get("cohort")
    if not isinstance(cohort, dict):
        _refuse("COHORT_NOT_HINDSIGHT", "cohort missing")
    selection = cohort.get("selection")
    if not isinstance(selection, str) or not selection.startswith("HINDSIGHT"):
        _refuse("COHORT_NOT_HINDSIGHT", repr(selection))
    if cohort.get("survivorship") is not True:
        _refuse("COHORT_SURVIVORSHIP_NOT_TRUE", repr(cohort.get("survivorship")))

    horizons = draft.get("horizons")
    if horizons != REQUIRED_HORIZONS:
        _refuse("HORIZONS_MISMATCH", repr(horizons))

    names = draft.get("names")
    cells = draft.get("cells")
    if not isinstance(names, list) or not isinstance(cells, list):
        _refuse("CELL_COUNT_MISMATCH", "names or cells missing")
    expected = len(names) * len(horizons)
    if len(cells) != expected:
        _refuse(
            "CELL_COUNT_MISMATCH",
            f"len(cells)={len(cells)} != {len(names)}*{len(horizons)}",
        )

    then_known = draft.get("then_known")
    if not isinstance(then_known, list) or not then_known:
        _refuse("THEN_KNOWN_INCOMPLETE", "then_known missing or empty")
    for index, row in enumerate(then_known):
        if not isinstance(row, dict):
            _refuse("THEN_KNOWN_INCOMPLETE", f"row {index} is not an object")
        missing = [field for field in THEN_KNOWN_FIELDS if field not in row]
        if missing:
            _refuse("THEN_KNOWN_INCOMPLETE", f"row {index} missing {missing}")


def load_draft(path) -> dict:
    """Parse the DRAFT JSON and refuse unsafe states. Does not register or seal."""
    text = Path(path).read_text(encoding="utf-8")
    draft = json.loads(text)
    validate_draft(draft)
    return draft

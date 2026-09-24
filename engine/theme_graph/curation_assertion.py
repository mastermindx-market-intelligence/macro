"""``theme_graph.curation_assertion.v1`` — one curated statement, tamper-evident.

Shared contract (Robotics plan Task 1 / Semiconductor plan §3.1; decision R1):
there is exactly ONE grammar and ONE module behind it. An assertion is a
statement about what a SOURCE said, never a market judgment — authority is
structurally all-false, in this module AND in the schema.

The revision is a pure function of the payload's content minus the revision
itself, over canonical JSON bytes. Two statements that differ in any retained
byte (locator, native digest, retention time…) are two revisions; a correction
is a new row that POINTS at its predecessor and never changes it. Nothing nets,
nothing is superseded in place — the same law the evidence store runs on.

Error protocol: every refusal raises :class:`CurationAssertionError` (a
``ValueError``) whose message STARTS with a short snake_case code —
``schema_violation`` for shape breaches (the JSON schema is the contract),
named codes for the semantic rules (``authority_not_all_false``,
``observation_value_invalid``, ``quantity_basis_required``,
``predicate_mode_pairing_invalid``, ``published_at_grain_mismatch``,
``duplicate_local_selector``, ``relation_endpoint_missing``,
``containment_cycle``, ``purchase_boundary_double_count``,
``unstamped_not_allowed``, ``curation_revision_mismatch``).
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Mapping

import jsonschema

#: Frozen schema id string — also the required ``schema`` property's const.
SCHEMA_ID = "theme_graph.curation_assertion.v1"

#: Revision grammar: ``gmirca_`` + 32 lowercase hex.
REVISION_PREFIX = "gmirca_"
REVISION_RE = re.compile(r"^gmirca_[0-9a-f]{32}$")

#: Authority is structurally absent. The schema pins each flag ``const: false``;
#: the code pins it again so a payload cannot smuggle authority past a schema
#: bug, a hand-rolled validator, or a copy of the schema that drifted.
AUTHORITY_FLAGS: tuple[str, ...] = (
    "can_rank", "can_gate", "can_size", "can_originate", "can_open_entry",
)

#: predicate × statement_mode pairings that launder a claim into a fact (or a
#: fact into a promise) — the two the Robotics contract pins. A REPORTED
#: DEPLOYMENT cannot be a FORWARD_TARGET, and a DEPLOYMENT_TARGET cannot be
#: reported as an accomplished REPORTED_FACT.
FORBIDDEN_PREDICATE_MODE_PAIRS: frozenset[tuple[str, str]] = frozenset({
    ("REPORTED_DEPLOYMENT", "FORWARD_TARGET"),
    ("DEPLOYMENT_TARGET", "REPORTED_FACT"),
})

_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_CLOCK_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(\.[0-9]+)?(Z|[+-][0-9]{2}:[0-9]{2})$"
)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMA_PATH = _REPO_ROOT / "contracts" / "theme_graph" / "curation_assertion.v1.schema.json"

#: The schema is the contract; loaded once, validated once at import so a
#: malformed schema file fails loudly at import rather than per-payload.
_SCHEMA: dict[str, Any] = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
_VALIDATOR = jsonschema.Draft202012Validator(_SCHEMA)  # matches evidence.v1's draft


class CurationAssertionError(ValueError):
    """A refused assertion. ``str(exc)`` starts with a short snake_case code."""


# ---------------------------------------------------------------------------
# Canonical bytes and the revision
# ---------------------------------------------------------------------------

def _canonical_bytes(payload: Mapping[str, Any]) -> bytes:
    """Canonical JSON: sorted keys, no whitespace, UTF-8, NaN/inf refused."""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def curation_revision(payload: Mapping[str, Any]) -> str:
    """``gmirca_`` + sha256 of the canonical bytes of the payload WITHOUT the
    ``curation_revision`` field — a pure function of content, so the same
    statement is always the same revision and any retained edit is a new one."""
    body = {k: v for k, v in dict(payload).items() if k != "curation_revision"}
    digest = hashlib.sha256(_canonical_bytes(body)).hexdigest()[:32]
    return REVISION_PREFIX + digest


# ---------------------------------------------------------------------------
# Semantic checks — named codes, tolerant of malformed shape (the schema pass
# below is what rejects malformed structure; these rules must never crash on it)
# ---------------------------------------------------------------------------

def _check_authority(data: dict[str, Any]) -> None:
    auth = data.get("authority")
    if not isinstance(auth, Mapping):
        return  # shape is the schema's job
    for flag in AUTHORITY_FLAGS:
        if auth.get(flag) is not False:
            raise CurationAssertionError(
                f"authority_not_all_false: authority.{flag} must be literal false — "
                f"an assertion informs, it never ranks/gates/sizes/originates/opens")


def _check_observation(data: dict[str, Any]) -> None:
    obs = data.get("observation")
    if not isinstance(obs, Mapping):
        return
    for key in ("value", "value_high"):
        v = obs.get(key)
        if v is None:
            continue
        if isinstance(v, bool) or not isinstance(v, (int, float)) \
                or not math.isfinite(v) or v < 0:
            raise CurationAssertionError(
                f"observation_value_invalid: observation.{key} must be a finite "
                f"non-negative number (got {v!r})")
    if obs.get("value") is not None and obs.get("quantity_basis") is None:
        raise CurationAssertionError(
            "quantity_basis_required: observation.value carries no quantity_basis — "
            "a number nobody can say the basis of is not an observation")


def _check_predicate_mode(data: dict[str, Any]) -> None:
    pair = (data.get("predicate"), data.get("statement_mode"))
    if pair in FORBIDDEN_PREDICATE_MODE_PAIRS:
        raise CurationAssertionError(
            "predicate_mode_pairing_invalid: "
            f"predicate {pair[0]!r} cannot carry statement_mode {pair[1]!r}")


def _check_published_at_grain(data: dict[str, Any]) -> None:
    src = data.get("source")
    if not isinstance(src, Mapping):
        return
    grain = src.get("published_at_grain")
    published = src.get("published_at")
    if grain == "unknown":
        if published is not None:
            raise CurationAssertionError(
                "published_at_grain_mismatch: grain 'unknown' requires published_at "
                "null — an unknown publication is never dated by borrowing")
    elif grain == "date":
        if not isinstance(published, str) or not _DATE_RE.match(published):
            raise CurationAssertionError(
                "published_at_grain_mismatch: grain 'date' requires a plain "
                f"YYYY-MM-DD published_at (got {published!r})")
    elif grain == "instant":
        if not isinstance(published, str) or not _CLOCK_RE.match(published):
            raise CurationAssertionError(
                "published_at_grain_mismatch: grain 'instant' requires a full "
                f"date-time published_at (got {published!r})")


def _check_industrial_context(data: dict[str, Any]) -> None:
    ctx = data.get("industrial_context")
    if not isinstance(ctx, Mapping):
        return
    objects = ctx.get("local_objects")
    objects = list(objects) if isinstance(objects, list) else []

    selectors = [o.get("selector") for o in objects if isinstance(o, Mapping)]
    if len(selectors) != len(set(selectors)):
        raise CurationAssertionError(
            "duplicate_local_selector: local_objects selectors must be unique within "
            "the assertion — one handle, one object")
    known = set(selectors)

    relation = ctx.get("relation")
    if isinstance(relation, Mapping):
        for end in ("src_selector", "dst_selector"):
            endpoint = relation.get(end)
            if endpoint not in known and not (
                    isinstance(endpoint, str) and REVISION_RE.match(endpoint)):
                raise CurationAssertionError(
                    f"relation_endpoint_missing: relation.{end} {endpoint!r} is "
                    f"neither a local selector nor an immutable native assertion "
                    f"reference ({REVISION_PREFIX}…)")
        if relation.get("kind") == "contains" \
                and relation.get("src_selector") == relation.get("dst_selector"):
            raise CurationAssertionError(
                "containment_cycle: a contains relation whose src == dst contains "
                "itself — within one assertion a relation is a single edge, so the "
                "cycle the contract refuses is the self-edge")

    scope = ctx.get("measure_scope")
    if isinstance(scope, Mapping) and scope.get("purchase_boundary") == "integrated_assembly":
        # The frozen simplest deterministic form (documented in the README
        # section): refuse an integrated_assembly total when any kind=configuration
        # object's configuration string equals ANOTHER local object's model — the
        # assembly total and the contained configuration cannot both be counted
        # as purchases of the same thing.
        for i, obj in enumerate(objects):
            if not isinstance(obj, Mapping) or obj.get("kind") != "configuration":
                continue
            config = obj.get("configuration")
            if config is None:
                continue
            if any(config == other.get("model")
                   for j, other in enumerate(objects) if j != i
                   and isinstance(other, Mapping)):
                raise CurationAssertionError(
                    "purchase_boundary_double_count: purchase_boundary "
                    "integrated_assembly with a kind=configuration object whose "
                    f"configuration {config!r} equals another local object's model — "
                    f"the assembly total already contains that configuration's value")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_assertion(payload: Mapping[str, Any],
                       *, allow_unstamped: bool = False) -> dict[str, Any]:
    """Validate one assertion and return it as a deep-copied plain dict.

    Raises :class:`CurationAssertionError` (message starts with a snake_case
    code) on any breach. With ``allow_unstamped=True`` a null
    ``curation_revision`` is accepted — the unstamped working state BEFORE the
    author stamps it; every encoded assertion is stamped.
    """
    if not isinstance(payload, Mapping):
        raise CurationAssertionError(
            f"not_a_mapping: an assertion is a JSON object (got {type(payload).__name__})")
    data = copy.deepcopy(dict(payload))

    # Named semantic rules first, so a breach names its rule even when the
    # schema would also (more generically) reject the same payload.
    _check_authority(data)
    _check_observation(data)
    _check_predicate_mode(data)
    _check_published_at_grain(data)
    _check_industrial_context(data)

    errs = sorted(_VALIDATOR.iter_errors(data), key=lambda e: str(e.path))
    if errs:
        raise CurationAssertionError(f"schema_violation: {errs[0].message}")

    stamp = data.get("curation_revision")
    if stamp is None:
        if not allow_unstamped:
            raise CurationAssertionError(
                "unstamped_not_allowed: curation_revision is null — stamp the "
                "payload (curation_revision(payload)) or pass allow_unstamped=True "
                "for the working state")
    elif stamp != curation_revision(data):
        raise CurationAssertionError(
            f"curation_revision_mismatch: stamped {stamp!r} but the payload's "
            f"content hashes to {curation_revision(data)!r}")
    return data


def encode_assertion(payload: Mapping[str, Any]) -> str:
    """Canonical JSON text of the STAMPED, VALIDATED payload — the exact string
    an evidence row's ``curation_assertion`` cell carries. Refuses unstamped or
    wrongly-stamped payloads: the cell must be tamper-evident at write time."""
    return _canonical_bytes(validate_assertion(payload)).decode("utf-8")


def decode_assertion(value: object) -> dict[str, Any] | None:
    """Parse and fully validate an encoded assertion.

    ``None``/``""`` → ``None`` (a null cell is not a breach). Malformed JSON,
    schema breaches, unknown keys and stamp mismatches all raise
    :class:`CurationAssertionError`.
    """
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise CurationAssertionError(
            f"not_a_string: an encoded assertion is JSON text or null "
            f"(got {type(value).__name__})")
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise CurationAssertionError(f"malformed_json: {exc}") from exc
    return validate_assertion(parsed)


def source_ref_for(payload: Mapping[str, Any]) -> str:
    """``gmi-curation://<scope.canonical_theme_id>/<curation_revision>`` — the
    evidence-row ``source_ref`` for a stamped assertion. The theme id comes
    from the payload (shared decision R1: generalized from the Robotics literal
    so every vertical shares ONE resolver)."""
    stamped = validate_assertion(payload)
    return (f"gmi-curation://{stamped['scope']['canonical_theme_id']}"
            f"/{stamped['curation_revision']}")

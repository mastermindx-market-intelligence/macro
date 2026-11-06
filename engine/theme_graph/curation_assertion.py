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
``unstamped_not_allowed``, ``curation_revision_mismatch``), plus the shape
codes ``not_a_mapping`` (payload is not an object), ``not_a_string`` and
``malformed_json`` (an encoded cell that is not JSON text).
``published_at_grain_mismatch`` is the one rule beyond the frozen Robotics
list (a grain/date consistency strengthening; the Robotics pinned
unknown+null case passes it) — recorded in the contracts README.

Mint protocol: ``encode_assertion`` stamps an unstamped payload; strict
``validate_assertion`` (the decode path) refuses one, because every STORED
cell is stamped. Nullable-by-contract: ``review.review_due_at`` and
``source.native_digest`` (an unknown due date / digest stays null, never
fabricated — the frozen Robotics reference payload carries both as null).
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Mapping

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

#: The schema is the contract; the FILE is loaded at import, so a malformed
#: schema still fails loudly there. The VALIDATOR is built on first use: this
#: module sits in the shared ``app.main`` import closure, and a hard
#: ``import jsonschema`` here made an unprovisioned app import raise
#: ModuleNotFoundError instead of degrading (pinned by
#: ``test_unprovisioned_app_import_defers_biocatalyst_contract_runtime``).
#: Deferral is the convention ``engine/options_nbbo_cohort.py`` already uses.
#: Nothing is lost by building it lazily — constructing a Draft202012Validator
#: never validated the schema in the first place; that is ``check_schema``.
_SCHEMA: dict[str, Any] = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
_VALIDATOR: Any | None = None


def _validator() -> Any:
    """The Draft 2020-12 validator for :data:`_SCHEMA`, built once on first use."""
    global _VALIDATOR
    if _VALIDATOR is None:
        from jsonschema import Draft202012Validator  # noqa: PLC0415

        _VALIDATOR = Draft202012Validator(_SCHEMA)  # matches evidence.v1's draft
    return _VALIDATOR


class CurationAssertionError(ValueError):
    """A refused assertion. ``str(exc)`` starts with a short snake_case code."""


# ---------------------------------------------------------------------------
# Canonical bytes and the revision
# ---------------------------------------------------------------------------

def _canonical_bytes(payload: Mapping[str, Any]) -> bytes:
    """Canonical JSON: sorted keys, no whitespace, UTF-8, NaN/inf refused."""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _revision_of(data: Mapping[str, Any]) -> str:
    """The stamp of an already content-validated payload (no validation here)."""
    body = {k: v for k, v in dict(data).items() if k != "curation_revision"}
    digest = hashlib.sha256(_canonical_bytes(body)).hexdigest()[:32]
    return REVISION_PREFIX + digest


def curation_revision(payload: Mapping[str, Any]) -> str:
    """``gmirca_`` + sha256 of the canonical bytes of the payload WITHOUT the
    ``curation_revision`` field — a pure function of content, so the same
    statement is always the same revision and any retained edit is a new one.

    The payload is content-validated first (semantic rules + schema; any
    existing stamp is ignored here — the frozen Robotics reference calls
    ``validate_assertion(candidate, allow_unstamped=True)`` before hashing), so
    structurally invalid garbage never receives a well-formed stamp."""
    return _revision_of(_validated_content(payload))


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

def _validated_content(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Semantic rules + schema over a deep copy; the stamp is NOT checked here
    (``validate_assertion`` layers that on). Shared by the validator and the
    revision function so neither can recurse into the other."""
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

    errs = sorted(_validator().iter_errors(data), key=lambda e: str(e.path))
    if errs:
        raise CurationAssertionError(f"schema_violation: {errs[0].message}")
    return data


def validate_assertion(payload: Mapping[str, Any],
                       *, allow_unstamped: bool = False) -> dict[str, Any]:
    """Validate one assertion and return it as a deep-copied plain dict.

    Raises :class:`CurationAssertionError` (message starts with a snake_case
    code) on any breach. With ``allow_unstamped=True`` a null
    ``curation_revision`` is accepted — the unstamped working state BEFORE the
    author stamps it; every encoded assertion is stamped (``encode_assertion``
    is the mint path that stamps it).
    """
    data = _validated_content(payload)
    stamp = data.get("curation_revision")
    if stamp is None:
        if not allow_unstamped:
            raise CurationAssertionError(
                "unstamped_not_allowed: curation_revision is null — stamp the "
                "payload (curation_revision(payload)) or pass allow_unstamped=True "
                "for the working state")
    elif stamp != _revision_of(data):
        raise CurationAssertionError(
            f"curation_revision_mismatch: stamped {stamp!r} but the payload's "
            f"content hashes to {_revision_of(data)!r}")
    return data


def encode_assertion(payload: Mapping[str, Any]) -> str:
    """Canonical JSON text of the STAMPED, VALIDATED payload — the exact string
    an evidence row's ``curation_assertion`` cell carries.

    This is the MINT path (frozen Robotics reference, Task 1 Step 4): an
    unstamped payload (``curation_revision`` null) is content-validated,
    stamped with its :func:`curation_revision` and serialized. An
    already-stamped payload must carry the stamp its content hashes to
    (``curation_revision_mismatch`` otherwise) and encodes byte-identically to
    the mint of its unstamped form — so the cell is tamper-evident at write
    time either way, and no caller needs to hand-roll the stamp."""
    data = validate_assertion(payload, allow_unstamped=True)
    if data.get("curation_revision") is None:
        data["curation_revision"] = _revision_of(data)
    return _canonical_bytes(data).decode("utf-8")


def decode_assertion(value: object) -> dict[str, Any] | None:
    """Parse and fully validate an encoded assertion.

    ``None``/``""``/``NaN`` → ``None`` (a null cell is not a breach; a parquet
    column that mixes legacy null cells with curated rows reads its nulls
    back as ``float('nan')``). Malformed JSON, schema breaches, unknown keys
    and stamp mismatches all raise :class:`CurationAssertionError`.
    """
    if value is None or value == "":
        return None
    if isinstance(value, float) and math.isnan(value):
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
    so every vertical shares ONE resolver). Accepts the unstamped working
    state too (the frozen reference is ``decode_assertion(encode_assertion(
    payload))`` over an unstamped payload) — the ref is the mint's ref."""
    data = validate_assertion(payload, allow_unstamped=True)
    revision = data.get("curation_revision") or _revision_of(data)
    return f"gmi-curation://{data['scope']['canonical_theme_id']}/{revision}"


# ---------------------------------------------------------------------------
# K1 Evidence Foundation binding (semiconductor T04): the assertion is ONE
# owner subtype of the shared Evidence Foundation, with native clocks under
# their native dotted field names and the theme-evidence identity preserved.
# ---------------------------------------------------------------------------

#: The K1 owner store these assertions bind as (must stay in lockstep with
#: ``contracts/evidence_foundation/vocabulary.v1.json``).
K1_OWNER_STORE = "theme_graph.curation_assertion"

#: statement_mode → the ONE K1 object_class the mode projects onto. Total over
#: the schema's statement_mode enum and one-way: a FORWARD_TARGET is never a
#: world observation, an ATTRIBUTED_INTERPRETATION is never a fact.
_OBJECT_CLASS_BY_STATEMENT_MODE: Mapping[str, str] = {
    "REPORTED_FACT": "world_observation",
    "CATALOG_DESCRIPTION": "world_observation",
    "ANNOUNCED_ARRANGEMENT": "world_observation",
    "FORWARD_TARGET": "forward_claim",
    "ATTRIBUTED_INTERPRETATION": "derived_view",
}

#: object_class → K1 authority_class. A curation assertion is a statement a
#: human curator read out of a source — never model output — so forward_claim
#: and derived_view project onto ``human`` (both admitted by K1's own
#: object_class → authority_class map).
_AUTHORITY_CLASS_BY_OBJECT_CLASS: Mapping[str, str] = {
    "world_observation": "fact",
    "forward_claim": "human",
    "derived_view": "human",
}

#: Clock fields that live inside the assertion body; every other bound clock
#: (``computed_at``) is an evidence-row column.
_ASSERTION_CLOCK_PREFIXES = ("source.", "review.", "temporal.")

#: Evidence-row columns that attest the row's licensing state.
_LICENSING_FLAGS = (
    "licensing_internal_ok",
    "licensing_display_ok",
    "licensing_redistribution_ok",
)


def _clock_cell(cells: Mapping[str, Any], field: str) -> Any:
    """Dotted-path lookup into an assertion body (``source.published_at``)."""
    node: Any = cells
    for part in field.split("."):
        if not isinstance(node, Mapping):
            return None
        node = node.get(part)
    return node


def _native_clock(
    field: str, binding: Mapping[str, Any], cells: Mapping[str, Any]
) -> dict[str, Any]:
    """One K1 clock for one bound native field — present exactly once, with a
    typed unknown for a cell the assertion does not know (never a value
    borrowed from a clock that does exist, never a synthesized midnight)."""
    clock_class = binding["class"]
    grains = list(binding["grains"])
    cell = _clock_cell(cells, field)
    if cell is None or cell == "" or cell == "unknown":
        return {
            "class": clock_class,
            "field": field,
            "value_state": "unknown",
            "value": None,
            "grain": grains[0],
        }
    if field == "source.published_at":
        # The assertion's own grain discriminator separates a date-only
        # publication from an instant; a date stays a date.
        source = cells.get("source")
        grain_discriminator = (
            source.get("published_at_grain")
            if isinstance(source, Mapping) else None)
        grain = "date" if grain_discriminator == "date" else "datetime"
    elif len(grains) == 1:
        grain = grains[0]
    else:
        raise CurationAssertionError(
            f"clock_grain_unresolved: {field} binds {grains!r} with no "
            f"native grain discriminator")
    return {
        "class": clock_class,
        "field": field,
        "value_state": "known",
        "value": cell,
        "grain": grain,
    }


def _rights_and_missingness(
    row: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Rights + missingness read off the row's licensing attestation: any
    denied right is a rights-blocked object, all rights attested is permitted,
    and a right that is neither attested nor denied is UNKNOWN — never
    silently permitted, never a fabricated absence.

    The licensing flags are the row's MINT-TIME snapshot (evidence.v1 says so:
    no enforcement power). ``permitted`` here therefore means "attested at
    mint", not "may be emitted now"; the serving path re-checks the fresh
    rights snapshot through ``engine.theme_graph.rights`` before any body or
    conclusion is emitted (T03), and ``policy_id`` stays None because this
    projection consults no policy."""
    flags = [row.get(name) for name in _LICENSING_FLAGS]
    if all(flag is True for flag in flags):
        return (
            {"state": "permitted", "policy_id": None},
            {"state": "present", "reason": None, "zero_substituted": False},
        )
    if any(flag is False for flag in flags):
        return (
            {"state": "rights_blocked", "policy_id": None},
            {"state": "absent", "reason": "rights_blocked", "zero_substituted": False},
        )
    return (
        {"state": "unknown", "policy_id": None},
        {"state": "present", "reason": None, "zero_substituted": False},
    )


def reference_for_assertion(row: Mapping[str, Any]) -> dict[str, Any]:
    """Project ONE stamped curation-assertion evidence row onto an
    ``evidence_foundation.reference.v1`` that
    ``lib.evidence_foundation.validate_reference`` accepts unchanged —
    pointer-only, zero-authority, no K1 validator change, no physical mesh.

    The binding law (semiconductor T04):

    * Identity stays owner-native and in its OWN namespace —
      ``{evidence_id, curation_revision}`` with the shared theme-graph
      evidence id grammar and the module's revision grammar. The reference's
      only subject is the theme-evidence identity: a venue:symbol never
      becomes a cik/security subject, and a resolved
      ``subject.company_node_id`` inside the assertion never mints one.
    * Every clock the owner binds appears EXACTLY once under its native
      dotted field name. A cell the assertion does not know is a typed
      unknown — an unknown publication is never borrowed from
      ``observed_at``/``retained_at``/``reviewed_at``, and a date-only
      publication keeps grain ``date`` instead of becoming a midnight
      instant. The publication clock is the assertion's OWN publication
      time, never the row's flat projection column.
    * The reference is a pointer: the owner body (limitations, observation,
      source_uri) never rides along — the vocabulary's owner reader
      (``decode_assertion``) stays the only path back to the statement.
    * Correction lineage stays owner-native. A
      ``correction.predecessor_revision`` names a curation revision, not a
      computable K1 reference id, so none is fabricated here: the reference
      carries ``kind: "none"`` and no relations, and the assertion body
      remains the lineage of record.

    Raises :class:`CurationAssertionError` for a row with no stamped
    assertion, a row without its evidence id, a statement_mode with no K1
    object_class, or any drift between this module and the K1 vocabulary.
    """
    from lib.evidence_foundation import (
        ALL_FALSE_AUTHORITY,
        compute_reference_id,
        load_vocabulary,
        render_owner_pointer,
    )

    assertion = decode_assertion(
        row.get("curation_assertion") if isinstance(row, Mapping) else row)
    if assertion is None:
        raise CurationAssertionError(
            "no_assertion_to_reference: an evidence row without a stamped "
            "curation assertion has no object to reference")
    evidence_id = row.get("evidence_id")
    if not isinstance(evidence_id, str) or not evidence_id:
        raise CurationAssertionError(
            "row_identity_missing: an evidence row must carry its "
            "theme-graph evidence_id to be referenced")

    vocabulary = load_vocabulary()
    owner = vocabulary["owner_stores"].get(K1_OWNER_STORE)
    if not isinstance(owner, Mapping):
        raise CurationAssertionError(
            f"k1_owner_store_missing: {K1_OWNER_STORE} is not a K1 owner store")
    if owner.get("native_schemas") != [SCHEMA_ID]:
        raise CurationAssertionError(
            f"k1_owner_schema_drift: {K1_OWNER_STORE} binds "
            f"{owner.get('native_schemas')!r} but this module owns {SCHEMA_ID!r}")

    statement_mode = assertion.get("statement_mode")
    object_class = _OBJECT_CLASS_BY_STATEMENT_MODE.get(statement_mode)
    if object_class is None:
        raise CurationAssertionError(
            f"statement_mode_unmapped: {statement_mode!r} has no K1 object_class")

    identity = {
        "evidence_id": evidence_id,
        "curation_revision": assertion["curation_revision"],
    }
    clocks: list[dict[str, Any]] = []
    for field, binding in owner["clock_bindings"].items():
        if field.startswith(_ASSERTION_CLOCK_PREFIXES):
            clocks.append(_native_clock(field, binding, assertion))
        else:
            # An evidence-row column (computed_at): absent stays a typed
            # unknown clock, never a fabricated time.
            cells = {field: row.get(field)}
            clocks.append(_native_clock(field, binding, cells))
    fields = [clock["field"] for clock in clocks]
    if len(fields) != len(set(fields)) or set(fields) != set(owner["clock_bindings"]):
        raise CurationAssertionError(
            "clock_binding_drift: bound clocks and emitted clocks disagree")

    rights, missingness = _rights_and_missingness(row)
    payload: dict[str, Any] = {
        "schema": "evidence_foundation.reference.v1",
        "version": "1.0.0",
        "reference_id": "",
        "object_class": object_class,
        "owner_store": K1_OWNER_STORE,
        "native_identity": identity,
        "native_schema": SCHEMA_ID,
        "native_digest": {
            "state": "known",
            "sha256": hashlib.sha256(_canonical_bytes(assertion)).hexdigest(),
        },
        "coverage_class": owner["coverage_classes"][0],
        "freshness": {"state": "unknown", "clock_field": None, "policy_id": None},
        "rights": rights,
        "authority_class": _AUTHORITY_CLASS_BY_OBJECT_CLASS[object_class],
        "subject": {"key_type": owner["subject_key_types"][0], "key": evidence_id},
        "secondary_subjects": [],
        "clocks": clocks,
        "provenance": {
            "pointer_only": True,
            "body_embedded": False,
            "owner_reader": owner["reader"],
            "owner_reader_kind": owner["reader_kind"],
            # render_owner_pointer is the single source of truth and refuses
            # an identity outside the owner's own grammars.
            "pointer": render_owner_pointer(owner, identity),
        },
        "relations": [],
        "missingness": missingness,
        "correction": {
            "kind": "none",
            "predecessor_reference_ids": [],
            "clock_field": None,
            "chronology_state": "not_applicable",
            "append_only": True,
            "mutates_predecessor": False,
        },
        "replay": {
            "mode": "live",
            "cutoffs": {
                clock_class: {"state": "unknown", "value": None, "grain": "date"}
                for clock_class in vocabulary["clock_classes"]
            },
            "code_revision": None,
            "input_digest": None,
            "vintage_state": owner["replay_capabilities"]["live"][0],
        },
        "authority": dict(ALL_FALSE_AUTHORITY),
    }
    payload["reference_id"] = compute_reference_id(payload)
    return payload

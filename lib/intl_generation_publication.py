"""Public International generation contract and bounded publication.

This module owns two things and nothing else:

1. the *public* International generation contract - a closed, caller-independent
   description of what the incumbent Macro builder actually admitted for the
   native International workspace, and
2. a bounded, atomic publication of that contract into an existing data root,
   so that the feeds pipeline can copy the exact published bytes later.

It is deliberately a *public* contract.  The contract carries no owner, no
question, no query, no cohort, no Saved state, no principal and no account:
the generation is a description of admitted market facts, not of a person.
The caller supplies the native config, the closed native measures and their
evidence, the evaluation clock and the policy-document digests; this module
copies, derives and scrubs - it never invents a grant, an owner, a clock or a
source.

Guarantees:

* every emitted value is copied from an explicit caller input or derived from
  one; nothing is inferred from a URL, a wall clock or a hash;
* a measure is exported only when the admitted unit is supported, the value is
  finite, the receipt matches, the publication decision matches this
  generation, and the adopted policy document is identified by a caller
  supplied digest;
* an unqualified, denied, unknown or stale measure keeps its *actual* negative
  quality, reason and permissions and loses every number, unit, instrument,
  period, observation, calculation, source reference and evidence key - no
  decision binding is ever copied into an unqualified output;
* context identifiers are derived from the native binding dimensions only, so
  they are stable across publication nonces, while the generation nonce, the
  receipts and the policies stay separate;
* publication writes immutable, content addressed files and replaces the
  mutable current selector atomically; a failed publication leaves the
  previous selector untouched;
* the reader verifies every binding it can (shape, file name, generation,
  digest, size, selector/sidecar equality) before it hands out bytes, and it
  never falls back to an older artifact when the current one is missing or
  broken.

The reader's integrity checks protect a publication that already lives in a
trusted store; they are not an authentication mechanism against an arbitrary
writer of the file system.

The module performs no clock reading, no network access and no source lookup.
"""

from __future__ import annotations

import copy
import errno
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from uuid import uuid4

from lib.intl_investigation_owner import MACRO_FIELDS
from lib.intl_investigation_projection import (
    _canonical_json,
    _content_identity,
    _decision_ok,
    _GENERATION_RE,
    _is_number,
    _plain_json,
    _qualification_identity,
    _receipt_ok,
    _sha256_hex,
    _validate_evidence,
    _validate_measures,
    SUPPORTED_UNITS,
)
from lib.intl_macro_publication import _read_stable_once
from lib.intl_workspace_macro import _PERMISSIONS, _QUALITIES, _UNITS


# ---------------------------------------------------------------------------
# Closed constants
# ---------------------------------------------------------------------------

#: Schema identifier of the published generation contract.
GENERATION_SCHEMA = "intl.workspace_generation.v1"

#: Schema identifier of the mutable current descriptor.
DESCRIPTOR_SCHEMA = "intl.workspace_generation_current.v1"

#: Every native context identifier starts with this prefix.
CONTEXT_ID_PREFIX = "intl-workspace-context:sha256:"

#: Domain separation for the policy identity hash.
POLICY_IDENTITY_DOMAIN = "intl-workspace-generation:policy-identity:v1"

#: The only supported native binding version.
BINDING_VERSION = 2

#: The only supported native return basis.
RETURN_BASIS = "price"

#: An upper bound on the enumerated contexts of one generation.
MAX_CONTEXTS = 128

#: An upper bound on the published artifact bytes.
MAX_ARTIFACT_BYTES = 8 * 1024 * 1024

#: An upper bound on the published descriptor bytes.
MAX_DESCRIPTOR_BYTES = 256 * 1024

#: The directory below the data root that holds the published files.
GENERATIONS_DIR = ("intl", "publication", "generations")

#: The immutable artifact file name prefix.
ARTIFACT_PREFIX = "intl_generation_"

#: The immutable descriptor sidecar file name prefix.
DESCRIPTOR_PREFIX = "intl_generation_descriptor_"

#: The mutable current selector file name.
CURRENT_NAME = "intl_generation_current.json"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
_ARTIFACT_NAME_RE = re.compile(
    r"^intl_generation_[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}"
    r"-[89ab][0-9a-f]{3}-[0-9a-f]{12}_[0-9a-f]{64}\.json$")
_DESCRIPTOR_NAME_RE = re.compile(r"^intl_generation_descriptor_[0-9a-f]{64}\.json$")
_EVALUATED_AT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$")

_CONFIG_KEYS = frozenset({"markets", "horizons", "bases", "fields"})
_CONTRACT_KEYS = frozenset({
    "schema", "asof", "generation", "binding_version", "evaluated_at",
    "contexts", "measures", "policies"})
_CONTEXT_KEYS = frozenset({
    "id", "market", "horizon", "currency_basis", "return_basis", "measure_ids"})
_MEASURE_KEYS = frozenset({
    "native_measure", "native_evidence", "content_identity", "qualification_identity", "policy_identity"})
_EVIDENCE_KEYS = frozenset({"receipt_identity", "publication_decision", "clocks"})
_POLICY_KEYS = frozenset({
    "metadata", "value_permission", "policy_ref", "policy_document_sha256",
    "policy_identity"})
_DESCRIPTOR_KEYS = frozenset({
    "schema", "asof", "state", "generation", "artifact_name", "artifact_sha256",
    "artifact_bytes", "current_policies"})


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _need(condition, message):
    if not condition:
        raise ValueError(message)


def _require_keys(name, obj, keys):
    _need(type(obj) is dict, "%s must be an object" % name)
    _need(set(obj) == set(keys),
          "%s must carry exactly: %s" % (name, ", ".join(sorted(keys))))


def _text(name, value):
    _need(type(value) is str and value, "%s must be a non-empty string" % name)
    return value


def _texts(name, values, *, allow_empty=False):
    _need(type(values) is list, "%s must be a list" % name)
    if not values and not allow_empty:
        raise ValueError("%s must not be empty" % name)
    out = []
    for item in values:
        _need(type(item) is str and item, "%s must hold non-empty strings" % name)
        _need(item not in out, "%s must not repeat %s" % (name, item))
        out.append(item)
    return out


def _digest(name, value):
    _need(type(value) is str and _SHA256_RE.match(value),
          "%s must be a 64 hex digest" % name)
    return value


def _optional_digest(name, value):
    if value is None:
        return None
    return _digest(name, value)


# ---------------------------------------------------------------------------
# Contract inputs
# ---------------------------------------------------------------------------

def _generation(generation):
    """The workspace generation nonce: supplied and validated, never invented."""
    if generation is None:
        return "im-workspace-generation:" + str(uuid4())
    _need(type(generation) is str and _GENERATION_RE.match(generation),
          "generation must be im-workspace-generation:<canonical uuid4>")
    return generation


def _evaluated_at(evaluated_at):
    """The supplied UTC evaluation stamp; it is copied, never read from a clock."""
    _need(type(evaluated_at) is str, "evaluated_at must be a string")
    _need(_EVALUATED_AT_RE.match(evaluated_at),
          "evaluated_at must be a supplied UTC timestamp")
    return evaluated_at


def _market_ids(name, values):
    """Normalize the native market dimension.

    The incumbent builder carries the market dimension in two shapes: the
    plain market ids of the workspace config and the display registry entries
    that also carry the English and Chinese names.  Both name the same
    market, so both are accepted; the display names are not part of the
    public contract and are dropped here.
    """
    _need(type(values) is list and values, "%s must be a non-empty list" % name)
    out = []
    for entry in values:
        if type(entry) is str:
            market_id = entry
        elif type(entry) is dict:
            market_id = entry.get("market_id")
        else:
            market_id = None
        _need(type(market_id) is str and market_id,
              "%s must hold market ids or market entries" % name)
        _need(market_id not in out, "%s must not repeat %s" % (name, market_id))
        out.append(market_id)
    return out


def _config(config):
    """Validate the native config and return its explicit dimensions."""
    _require_keys("config", config, _CONFIG_KEYS)
    markets = _market_ids("config.markets", config["markets"])
    horizons = _texts("config.horizons", config["horizons"])
    bases = _texts("config.bases", config["bases"])
    raw_fields = config["fields"]
    _need(type(raw_fields) is dict, "config.fields must be an object")
    _need(set(raw_fields) == set(markets),
          "config.fields must cover exactly the configured markets")
    fields = {}
    for market in markets:
        fields[market] = _texts("config.fields[%s]" % market, raw_fields[market],
                                allow_empty=True)
    _need(len(markets) * len(horizons) * len(bases) <= MAX_CONTEXTS,
          "config enumerates more than %d contexts" % MAX_CONTEXTS)
    return markets, horizons, bases, fields


def _policy_documents(policy_document_sha256):
    """The caller supplied policy revision digests, keyed by measure id."""
    if policy_document_sha256 is None:
        return {}
    _need(type(policy_document_sha256) is dict,
          "policy_document_sha256 must be an object")
    out = {}
    for sid, digest in policy_document_sha256.items():
        _need(type(sid) is str and sid,
              "policy_document_sha256 keys must be non-empty strings")
        out[sid] = _optional_digest("policy_document_sha256[%s]" % sid, digest)
    return out


def _supported_units(sid):
    """The closed unit set a measure id may carry, or None when unsupported.

    The native Macro field vocabulary and the accepted investigation field
    vocabulary are both closed.  When both name the same field their units
    must agree; a measure whose unit is outside the closed set is never
    exported.
    """
    field = sid.split(".", 1)[1] if "." in sid else ""
    exact = SUPPORTED_UNITS.get(sid)
    native = _UNITS.get(field)
    candidates = []
    if exact is not None:
        candidates.append({exact})
    if native is not None:
        candidates.append(set(native))
    if not candidates:
        return None
    units = set.intersection(*candidates)
    return units or None


def _policy_identity(decision, metadata, permission, digest):
    """The policy identity: owner, policy reference, permissions and revision."""
    return _sha256_hex(_canonical_json({
        "domain": POLICY_IDENTITY_DOMAIN,
        "owner_ref": decision["owner_ref"],
        "policy_ref": decision["policy_ref"],
        "metadata": metadata,
        "value_permission": permission,
        "policy_document_sha256": digest,
    }))


# ---------------------------------------------------------------------------
# Contract assembly
# ---------------------------------------------------------------------------

def _negative_measure(quality, reason, metadata, permission):
    """The closed negative shape: permissions kept, every dynamic field dropped."""
    return {
        "quality": quality,
        "reason": reason,
        "metadata": metadata,
        "value_permission": permission,
        "value": None,
        "unit": None,
        "instrument": None,
        "period": None,
        "observation_at": None,
        "calculation_at": None,
        "source_reference": None,
        "evidence_key": None,
    }


def _negative_evidence():
    """The closed empty evidence shape."""
    return {"receipt_identity": None, "publication_decision": None, "clocks": {}}


def _assess(sid, measure, entry, generation, digest):
    """Assess one admitted measure against the export gates.

    Returns ``(native_measure, native_evidence, content_identity,
    qualification_identity, policy)``.  Only a fully qualified measure keeps
    its numbers, its source and its decision; every other case keeps the
    actual negative quality, reason and permissions and loses the rest.
    """
    receipt = entry["receipt_identity"]
    decision = entry["publication_decision"]
    quality = measure["quality"]
    metadata = measure["metadata"]
    permission = measure["value_permission"]

    policy = {"metadata": metadata, "value_permission": permission,
              "policy_ref": None, "policy_document_sha256": None,
              "policy_identity": None}
    adopted = (metadata == "allowed" and decision is not None
               and _decision_ok(decision, sid, measure, receipt, generation))

    def negative(outcome_quality, outcome_reason):
        policy_entry = dict(policy)
        if adopted:
            policy_entry["policy_ref"] = decision["policy_ref"]
            policy_entry["policy_document_sha256"] = digest
            if digest is not None:
                policy_entry["policy_identity"] = _policy_identity(
                    decision, metadata, permission, digest)
        return (_negative_measure(outcome_quality, outcome_reason, metadata, permission),
                _negative_evidence(), None, None, policy_entry)

    if quality != "qualified":
        # A stale, denied, missing, failed, unsupported or unknown field keeps
        # the quality and the reason the admit helper actually reported.
        return negative(quality, measure["reason"])
    if metadata == "denied" or permission == "denied":
        reason = "metadata_denied" if metadata == "denied" else "value_denied"
        return negative("denied", reason)
    if metadata != "allowed" or permission != "allowed":
        return negative("unknown", "disclosure_unknown")
    if not _is_number(measure["value"]):
        return negative("unknown", "source_unknown")
    units = _supported_units(sid)
    if units is None or measure["unit"] not in units:
        return negative("unknown", "source_unknown")
    if receipt is None or not _receipt_ok(receipt, sid):
        return negative("unknown", "disclosure_unknown")
    if decision is None or not adopted:
        return negative("unknown", "disclosure_unknown")
    if digest is None:
        # Without the adopted policy revision the export is withheld.
        return negative("unknown", "disclosure_unknown")

    content_identity = _content_identity(sid, measure, receipt)
    qualification_identity = _qualification_identity(sid, decision, receipt)
    policy_entry = {
        "metadata": metadata,
        "value_permission": permission,
        "policy_ref": decision["policy_ref"],
        "policy_document_sha256": digest,
        "policy_identity": _policy_identity(decision, metadata, permission, digest),
    }
    return (copy.deepcopy(measure),
            {"receipt_identity": copy.deepcopy(receipt),
             "publication_decision": copy.deepcopy(decision),
             "clocks": copy.deepcopy(entry["clocks"])},
            content_identity,
            qualification_identity,
            policy_entry)


def _context_id(binding_version, market, horizon, currency_basis):
    """The native context identifier: the binding dimensions and nothing else."""
    payload = _canonical_json({
        "binding_version": binding_version,
        "market": market,
        "horizon": horizon,
        "currency_basis": currency_basis,
        "return_basis": RETURN_BASIS,
    })
    return CONTEXT_ID_PREFIX + _sha256_hex(payload)


def build_generation_contract(*, config, binding_version, measures, evidence,
                              evaluated_at, policy_document_sha256,
                              generation=None):
    """Build the public International generation contract.

    ``config`` carries the explicit native dimensions: ``markets``,
    ``horizons``, ``bases`` and the per market ``fields`` that the native
    builder supports.  A market may be given as its plain id or as the
    display registry entry that also carries its names.  ``measures`` maps a
    measure id to the closed native measure admitted by the actual admit
    helper, and ``evidence`` maps the same ids to their receipt, publication
    decision and clocks.  The ``generation`` nonce is supplied by the caller
    so that the publication decision can be bound to it; when it is omitted a
    fresh nonce is minted, and no publication decision can match a nonce that
    the admit helpers never saw.

    Returns the contract dictionary.  Raises ``ValueError`` for a malformed
    config, a malformed measure, a malformed evidence entry, an extra
    measure or evidence id, an unsupported dimension or an oversized input.
    """
    _need(type(binding_version) is int and binding_version == BINDING_VERSION,
          "binding_version must be the integer %d" % BINDING_VERSION)
    _need(_plain_json(measures), "measures must be plain JSON")
    _need(_plain_json(evidence), "evidence must be plain JSON")
    _need(type(measures) is dict, "measures must be an object")
    _need(type(evidence) is dict, "evidence must be an object")

    nonce = _generation(generation)
    stamp = _evaluated_at(evaluated_at)
    markets, horizons, bases, fields = _config(config)
    documents = _policy_documents(policy_document_sha256)

    supported = {}
    for market in markets:
        supported[market] = ["%s.%s" % (market, field) for field in fields[market]]
    allowed = {sid for sids in supported.values() for sid in sids}

    for name, supplied in (("measures", measures), ("evidence", evidence)):
        extra = sorted(set(supplied) - allowed)
        _need(not extra,
              "%s contains ids outside the configured fields: %s"
              % (name, extra[0] if extra else ""))

    # Per market validation through the accepted projection helpers.
    normalized_evidence = {}
    for market in markets:
        market_sids = supported[market]
        if not market_sids:
            continue
        market_measures = {sid: measures[sid] for sid in market_sids if sid in measures}
        _validate_measures(market_measures, list(market_sids), market)
        market_evidence = {sid: evidence[sid] for sid in market_sids if sid in evidence}
        normalized_evidence.update(_validate_evidence(market_evidence, list(market_sids)))

    measures_out = {}
    policies_out = {}
    for market in markets:
        for sid in supported[market]:
            entry = normalized_evidence.get(sid) or _negative_evidence()
            measure = measures.get(sid)
            if measure is None:
                # A configured field without an admitted measure stays visible
                # as an explicit, fully negative entry.
                native = _negative_measure("missing", "not_supplied", "unknown", "unknown")
                measures_out[sid] = {
                    "native_measure": native,
                    "native_evidence": _negative_evidence(),
                    "content_identity": None,
                    "qualification_identity": None,
                    "policy_identity": None,
                }
                policies_out[sid] = {
                    "metadata": "unknown", "value_permission": "unknown",
                    "policy_ref": None, "policy_document_sha256": None,
                    "policy_identity": None,
                }
                continue
            native, native_evidence, content, qualification, policy = _assess(
                sid, measure, entry, nonce, documents.get(sid))
            measures_out[sid] = {
                "native_measure": native,
                "native_evidence": native_evidence,
                "content_identity": content,
                "qualification_identity": qualification,
                "policy_identity": policy["policy_identity"] if native["quality"] == "qualified" else None,
            }
            policies_out[sid] = policy

    contexts = []
    seen_contexts = set()
    for market in markets:
        for horizon in horizons:
            for basis in bases:
                identifier = _context_id(BINDING_VERSION, market, horizon, basis)
                _need(identifier not in seen_contexts,
                      "config enumerates a duplicate context identifier")
                seen_contexts.add(identifier)
                contexts.append({
                    "id": identifier,
                    "market": market,
                    "horizon": horizon,
                    "currency_basis": basis,
                    "return_basis": RETURN_BASIS,
                    "measure_ids": list(supported[market]),
                })

    return {
        "schema": GENERATION_SCHEMA,
        "asof": None,
        "generation": nonce,
        "binding_version": BINDING_VERSION,
        "evaluated_at": stamp,
        "contexts": contexts,
        "measures": measures_out,
        "policies": policies_out,
    }


# ---------------------------------------------------------------------------
# Contract validation and serialization
# ---------------------------------------------------------------------------

def _validate_policy_entry(name, entry):
    _require_keys(name, entry, _POLICY_KEYS)
    _need(entry["metadata"] in _PERMISSIONS, "%s.metadata is not a known permission" % name)
    _need(entry["value_permission"] in _PERMISSIONS,
          "%s.value_permission is not a known permission" % name)
    if entry["policy_ref"] is not None:
        _text("%s.policy_ref" % name, entry["policy_ref"])
    _optional_digest("%s.policy_document_sha256" % name, entry["policy_document_sha256"])
    if entry["policy_identity"] is not None:
        _digest("%s.policy_identity" % name, entry["policy_identity"])
    return entry


def _validate_contract(contract):
    """Validate the exact public shape of a generation contract."""
    _need(_plain_json(contract), "contract must be plain JSON")
    _require_keys("contract", contract, _CONTRACT_KEYS | ({"policy_points_ref"} if "policy_points_ref" in contract else set()))
    if contract.get("policy_points_ref") is not None:
        from lib.intl_policy_publication import validate_policy_points_reference
        validate_policy_points_reference(contract["policy_points_ref"], contract["generation"])
    _need(contract["schema"] == GENERATION_SCHEMA,
          "contract.schema must be %s" % GENERATION_SCHEMA)
    _need(contract["asof"] is None, "contract.asof must be null")
    _need(type(contract["generation"]) is str and _GENERATION_RE.match(contract["generation"]),
          "contract.generation must be im-workspace-generation:<canonical uuid4>")
    _need(type(contract["binding_version"]) is int
          and contract["binding_version"] == BINDING_VERSION,
          "contract.binding_version must be the integer %d" % BINDING_VERSION)
    _need(type(contract["evaluated_at"]) is str
          and _EVALUATED_AT_RE.match(contract["evaluated_at"]),
          "contract.evaluated_at must be a supplied UTC timestamp")

    contexts = contract["contexts"]
    _need(type(contexts) is list and contexts, "contract.contexts must be a list")
    _need(len(contexts) <= MAX_CONTEXTS,
          "contract.contexts must not exceed %d entries" % MAX_CONTEXTS)
    market_of = {}
    seen_contexts = set()
    for index, context in enumerate(contexts):
        name = "contract.contexts[%d]" % index
        _require_keys(name, context, _CONTEXT_KEYS)
        _need(type(context["id"]) is str
              and context["id"].startswith(CONTEXT_ID_PREFIX)
              and _SHA256_RE.match(context["id"][len(CONTEXT_ID_PREFIX):]),
              "%s.id must be a native context identifier" % name)
        _need(context["id"] not in seen_contexts, "%s.id is duplicated" % name)
        seen_contexts.add(context["id"])
        for key in ("market", "horizon", "currency_basis"):
            _text("%s.%s" % (name, key), context[key])
        _need(context["return_basis"] == RETURN_BASIS,
              "%s.return_basis must be %r" % (name, RETURN_BASIS))
        measure_ids = _texts("%s.measure_ids" % name, context["measure_ids"],
                             allow_empty=True)
        for sid in measure_ids:
            _need(market_of.setdefault(sid, context["market"]) == context["market"],
                  "%s.measure_ids crosses a market boundary" % name)

    measures = contract["measures"]
    _need(type(measures) is dict, "contract.measures must be an object")
    policies = contract["policies"]
    _need(type(policies) is dict, "contract.policies must be an object")
    _need(set(policies) == set(measures),
          "contract.policies must cover exactly the contract measures")
    _need(set(measures) == set(market_of),
          "contract.measures must cover exactly the context measure ids")

    by_market = {}
    for sid, market in market_of.items():
        by_market.setdefault(market, {})[sid] = measures[sid]["native_measure"]
    for market, entries in by_market.items():
        _validate_measures(entries, sorted(entries), market)

    for sid, entry in measures.items():
        name = "contract.measures[%s]" % sid
        _require_keys(name, entry, _MEASURE_KEYS)
        native = entry["native_measure"]
        _require_keys("%s.native_measure" % name, native, MACRO_FIELDS)
        _need(native["quality"] in _QUALITIES,
              "%s.native_measure.quality is not a known quality" % name)
        _need(native["metadata"] in _PERMISSIONS,
              "%s.native_measure.metadata is not a known permission" % name)
        _need(native["value_permission"] in _PERMISSIONS,
              "%s.native_measure.value_permission is not a known permission" % name)
        _need(native["value"] is None or _is_number(native["value"]),
              "%s.native_measure.value must be a finite number or null" % name)
        for key in ("reason", "unit", "source_reference", "evidence_key",
                    "observation_at", "calculation_at"):
            _need(native[key] is None or (type(native[key]) is str and native[key]),
                  "%s.native_measure.%s must be null or a non-empty string" % (name, key))
        native_evidence = entry["native_evidence"]
        _require_keys("%s.native_evidence" % name, native_evidence, _EVIDENCE_KEYS)
        for key in ("content_identity", "qualification_identity", "policy_identity"):
            value = entry[key]
            _need(value is None or (type(value) is str and _SHA256_RE.match(value)),
                  "%s.%s must be null or a 64 hex digest" % (name, key))
        _validate_evidence({sid: native_evidence}, [sid])
        if native["quality"] != "qualified":
            _need(all(entry[key] is None for key in ("content_identity", "qualification_identity", "policy_identity")),
                  "negative measures must have null identities")
        else:
            _need(entry["policy_identity"] is not None
                  and entry["policy_identity"] == policies[sid]["policy_identity"],
                  "qualified policy identity must match adopted policy")

    for sid, entry in policies.items():
        _validate_policy_entry("contract.policies[%s]" % sid, entry)

    return contract


def serialize_generation(contract):
    """Return the canonical publication bytes of one generation contract.

    The bytes are canonical: sorted keys, no insignificant whitespace and no
    non-finite numbers.  The same contract always serializes to the same
    bytes, which is what makes the published digest meaningful.
    """
    validated = _validate_contract(contract)
    payload = _canonical_json(validated).encode("utf-8")
    _need(len(payload) <= MAX_ARTIFACT_BYTES,
          "the generation artifact exceeds %d bytes" % MAX_ARTIFACT_BYTES)
    return payload


# ---------------------------------------------------------------------------
# Publication
# ---------------------------------------------------------------------------

def _artifact_name(generation, digest):
    """The immutable artifact name of one generation and its content digest."""
    return "%s%s_%s.json" % (ARTIFACT_PREFIX, generation.split(":", 1)[1], digest)


def _unavailable_descriptor():
    """The explicit unavailable descriptor: no generation, no policy, no file."""
    return {
        "schema": DESCRIPTOR_SCHEMA,
        "asof": None,
        "state": "unavailable",
        "generation": None,
        "artifact_name": None,
        "artifact_sha256": None,
        "artifact_bytes": None,
        "current_policies": {},
    }


def _parse_json(payload):
    """Parse JSON strictly: no duplicate keys, no non-standard constants."""
    def _pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON object key")
            result[key] = value
        return result

    def _constant(value):
        raise ValueError("nonstandard JSON constant: %s" % value)

    return json.loads(payload.decode("utf-8"), object_pairs_hook=_pairs,
                      parse_constant=_constant)


def _fsync_directory(directory):
    """Flush a directory entry so a rename survives a crash."""
    try:
        fd = os.open(str(directory), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _generations_dir(data_root, *, create):
    """Resolve the publication directory, refusing symlinked components."""
    _need(data_root is not None, "data_root is required")
    root = Path(data_root)
    _need(root.is_dir(), "data_root must be an existing directory")
    directory = root
    parts = []
    for part in GENERATIONS_DIR:
        directory = directory / part
        parts.append(directory)
        if directory.is_symlink():
            raise ValueError("the publication path must not traverse a symlink")
    if not create:
        return directory if directory.is_dir() else None
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except (FileExistsError, NotADirectoryError):
        raise ValueError("the publication path is not a directory")
    for candidate in parts:
        if candidate.is_symlink():
            raise ValueError("the publication path must not traverse a symlink")
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("the publication path must be a real directory")
    return directory


def _write_immutable(path, payload, limit):
    """Write an immutable, content addressed file; refuse to change its bytes."""
    directory = path.parent
    descriptor, temporary_name = tempfile.mkstemp(
        dir=str(directory), prefix="." + path.name + ".", suffix=".tmp")
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(str(temporary), str(path))
        except FileExistsError:
            existing = _read_stable_once(path, limit)
            _need(existing == payload,
                  "immutable publication collision: %s" % path.name)
        except OSError as exc:
            if exc.errno not in (errno.EPERM, errno.ENOTSUP, errno.EOPNOTSUPP):
                raise
            # A file system without hard links still refuses to overwrite a
            # different published file.
            if path.exists():
                existing = _read_stable_once(path, limit)
                _need(existing == payload,
                      "immutable publication collision: %s" % path.name)
            else:
                os.replace(str(temporary), str(path))
        _fsync_directory(directory)
    finally:
        temporary.unlink(missing_ok=True)


def _replace_atomically(path, payload):
    """Replace a mutable file atomically and durably."""
    directory = path.parent
    descriptor, temporary_name = tempfile.mkstemp(
        dir=str(directory), prefix="." + path.name + ".", suffix=".tmp")
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(temporary), str(path))
        _fsync_directory(directory)
    finally:
        temporary.unlink(missing_ok=True)


def _publish_descriptor(directory, descriptor):
    """Write the immutable descriptor sidecar, then move the current selector."""
    payload = _canonical_json(descriptor).encode("utf-8")
    _need(len(payload) <= MAX_DESCRIPTOR_BYTES,
          "the current descriptor exceeds %d bytes" % MAX_DESCRIPTOR_BYTES)
    digest = hashlib.sha256(payload).hexdigest()
    sidecar = directory / ("%s%s.json" % (DESCRIPTOR_PREFIX, digest))
    _write_immutable(sidecar, payload, MAX_DESCRIPTOR_BYTES)
    _replace_atomically(directory / CURRENT_NAME, payload)
    return payload


def publish_generation(*, data_root, contract):
    """Publish one generation contract and return its current descriptor.

    The artifact and the descriptor sidecar are immutable and content
    addressed; the mutable current selector is replaced atomically once both
    are on disk.  A failed publication leaves the previous selector in place.
    """
    payload = serialize_generation(contract)
    generation = contract["generation"]
    digest = hashlib.sha256(payload).hexdigest()
    artifact_name = _artifact_name(generation, digest)
    directory = _generations_dir(data_root, create=True)
    _write_immutable(directory / artifact_name, payload, MAX_ARTIFACT_BYTES)
    descriptor = {
        "schema": DESCRIPTOR_SCHEMA,
        "asof": None,
        "state": "ready",
        "generation": generation,
        "artifact_name": artifact_name,
        "artifact_sha256": digest,
        "artifact_bytes": len(payload),
        "current_policies": copy.deepcopy(contract["policies"]),
    }
    ref = contract.get("policy_points_ref")
    if ref is not None:
        _verify_policy_points(directory, ref, generation)
        descriptor["current_policy_points"] = {"metadata": "allowed", "value_permission": "allowed", "mapping_identity": ref["mapping_identity"]}
    _publish_descriptor(directory, descriptor)
    return descriptor


def publish_unavailable_generation(*, data_root):
    """Point the current selector at an explicit unavailable generation.

    The unavailable descriptor never carries a generation, an artifact or a
    policy, so a reader can never mistake an older publication for the
    current one.
    """
    directory = _generations_dir(data_root, create=True)
    descriptor = _unavailable_descriptor()
    _publish_descriptor(directory, descriptor)
    return descriptor


def _validate_descriptor(descriptor):
    """Validate the exact shape of a current descriptor."""
    _require_keys("descriptor", descriptor, _DESCRIPTOR_KEYS | ({"current_policy_points"} if "current_policy_points" in descriptor else set()))
    if "current_policy_points" in descriptor:
        point_policy = descriptor["current_policy_points"]
        _require_keys("current policy points", point_policy, {"metadata", "value_permission", "mapping_identity"})
        _need(point_policy["metadata"] == "allowed" and point_policy["value_permission"] == "allowed", "invalid current point permission")
        _digest("current point mapping", point_policy["mapping_identity"])
    _need(descriptor["schema"] == DESCRIPTOR_SCHEMA,
          "descriptor.schema must be %s" % DESCRIPTOR_SCHEMA)
    _need(descriptor["asof"] is None, "descriptor.asof must be null")
    _need(descriptor["state"] in ("ready", "unavailable"),
          "descriptor.state must be ready or unavailable")
    if descriptor["state"] == "unavailable":
        _need(descriptor["generation"] is None
              and descriptor["artifact_name"] is None
              and descriptor["artifact_sha256"] is None
              and descriptor["artifact_bytes"] is None
              and descriptor["current_policies"] == {} and "current_policy_points" not in descriptor,
              "an unavailable descriptor must not carry a publication")
        return descriptor
    _need(type(descriptor["generation"]) is str
          and _GENERATION_RE.match(descriptor["generation"]),
          "descriptor.generation must be im-workspace-generation:<canonical uuid4>")
    name = descriptor["artifact_name"]
    _need(type(name) is str and _ARTIFACT_NAME_RE.match(name),
          "descriptor.artifact_name must be an immutable artifact name")
    _need(name == _artifact_name(descriptor["generation"], descriptor["artifact_sha256"]),
          "descriptor.artifact_name must bind the generation and the digest")
    _digest("descriptor.artifact_sha256", descriptor["artifact_sha256"])
    size = descriptor["artifact_bytes"]
    _need(type(size) is int and 0 < size <= MAX_ARTIFACT_BYTES,
          "descriptor.artifact_bytes must be a bounded positive integer")
    policies = descriptor["current_policies"]
    _need(type(policies) is dict, "descriptor.current_policies must be an object")
    for sid, entry in policies.items():
        _need(type(sid) is str and sid, "descriptor.current_policies keys must be ids")
        _validate_policy_entry("descriptor.current_policies[%s]" % sid, entry)
    return descriptor


def _verify_policy_points(directory, ref, generation):
    from lib.intl_policy_publication import validate_policy_points_reference, POINTS_MAX_BYTES, POINTS_SCHEMA
    validate_policy_points_reference(ref, generation)
    raw = _read_stable_once(directory / ref["artifact_name"], POINTS_MAX_BYTES)
    _need(len(raw) == ref["artifact_bytes"] and hashlib.sha256(raw).hexdigest() == ref["artifact_sha256"], "policy points identity mismatch")
    points = _parse_json(raw)
    _need(type(points) is dict and points.get("schema") == POINTS_SCHEMA
          and points.get("generation") == generation
          and points.get("mapping_identity") == ref["mapping_identity"]
          and points.get("qualification_identity") == ref["qualification_identity"], "policy points binding mismatch")
    return raw


def _verify_ready(directory, descriptor, selector_payload):
    """Verify every binding of a ready descriptor and return the artifact bytes."""
    sidecar_name = "%s%s.json" % (
        DESCRIPTOR_PREFIX, hashlib.sha256(selector_payload).hexdigest())
    sidecar = _read_stable_once(directory / sidecar_name, MAX_DESCRIPTOR_BYTES)
    _need(sidecar == selector_payload,
          "the current descriptor does not match its immutable sidecar")
    artifact = _read_stable_once(directory / descriptor["artifact_name"],
                                 MAX_ARTIFACT_BYTES)
    _need(len(artifact) == descriptor["artifact_bytes"],
          "the published artifact size does not match the descriptor")
    _need(hashlib.sha256(artifact).hexdigest() == descriptor["artifact_sha256"],
          "the published artifact digest does not match the descriptor")
    contract = _validate_contract(_parse_json(artifact))
    _need(contract["generation"] == descriptor["generation"],
          "the published artifact generation does not match the descriptor")
    _need(contract["policies"] == descriptor["current_policies"],
          "the published policies do not match the descriptor")
    ref = contract.get("policy_points_ref")
    if ref is not None:
        _verify_policy_points(directory, ref, contract["generation"])
        _need(descriptor.get("current_policy_points") == {"metadata": "allowed", "value_permission": "allowed", "mapping_identity": ref["mapping_identity"]}, "current point policy differs")
    else:
        _need("current_policy_points" not in descriptor, "unexpected current point policy")
    return artifact


def read_generation_publication(*, data_root):
    """Read the published generation and verify every binding before use.

    Returns ``{"status": ..., "descriptor": ..., "artifact_bytes": ...}`` where
    the status is ``ready``, ``unavailable`` (the publisher declared that no
    generation is available), ``missing`` (nothing was ever published here) or
    ``failed`` (a publication exists but is not verifiable).

    Every outcome other than ``ready`` carries the explicit unavailable
    descriptor: no generation, no artifact and no policy.  A missing or
    broken publication therefore never falls back to an older artifact, and
    the status alone says which of the two happened.
    """
    unavailable = _unavailable_descriptor()
    try:
        directory = _generations_dir(data_root, create=False)
    except ValueError:
        return {"status": "missing", "descriptor": unavailable, "artifact_bytes": None}
    except OSError:
        return {"status": "failed", "descriptor": unavailable, "artifact_bytes": None}
    if directory is None:
        return {"status": "missing", "descriptor": unavailable, "artifact_bytes": None}
    try:
        selector_payload = _read_stable_once(directory / CURRENT_NAME,
                                              MAX_DESCRIPTOR_BYTES)
    except FileNotFoundError:
        return {"status": "missing", "descriptor": unavailable, "artifact_bytes": None}
    except (OSError, ValueError):
        return {"status": "failed", "descriptor": unavailable, "artifact_bytes": None}
    try:
        descriptor = _validate_descriptor(_parse_json(selector_payload))
    except (ValueError, UnicodeDecodeError):
        return {"status": "failed", "descriptor": unavailable, "artifact_bytes": None}
    if descriptor["state"] == "unavailable":
        return {"status": "unavailable", "descriptor": descriptor,
                "artifact_bytes": None}
    try:
        artifact = _verify_ready(directory, descriptor, selector_payload)
    except (OSError, ValueError, UnicodeDecodeError):
        return {"status": "failed", "descriptor": unavailable, "artifact_bytes": None}
    return {"status": "ready", "descriptor": descriptor, "artifact_bytes": artifact}


__all__ = [
    "build_generation_contract",
    "serialize_generation",
    "publish_generation",
    "read_generation_publication",
    "publish_unavailable_generation",
]


# Closed public-disclosure validation of serialized bytes. The durable caller
# supplies its actual protected configuration/policy revisions; this contract
# owner performs no source lookup, network call or runtime authorization.
_intl_need = _need

_INTL_PUBLIC = {
    'EZ.policy_rate': 'official-ecb-deposit-level-admission',
    'GB.policy_rate': 'official-boe-bank-rate-admission',
    'EZ.gdp_yoy': 'official-eurostat-ea21-gdp-and-hicp',
    'EZ.cpi_yoy': 'official-eurostat-ea21-gdp-and-hicp',
    'EZ.annual_current_account': 'official-eurostat-ea21-annual-current-account',
}


_INTL_HELD = {'JP.yield_10y', 'JP.annual_current_account'}


def _intl_stamp(value):
    from datetime import datetime
    _intl_need(type(value) is str and len(value) <= 40, 'invalid public clock')
    try:
        datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError('invalid public clock') from None


def _intl_source_url(sid, value, receipt=None):
    from urllib.parse import urlsplit, parse_qs
    from lib.intl_boe_publication import _source_window
    from lib.intl_eurostat_publication import _source_url
    _intl_need(type(value) is str and len(value) <= 2048, 'invalid public source')
    if sid == 'EZ.policy_rate':
        prefix = 'https://data.ecb.europa.eu/data/datasets/FM/FM.D.U2.EUR.4F.KR.DFR.LEV#'
        _intl_need(value.startswith(prefix), 'unadmitted ECB source')
        q = parse_qs(value[len(prefix):], strict_parsing=True)
        _intl_need(q == {'artifact': [receipt['artifact_sha256']],
                          'provenance': [receipt['provenance_sha256']]}, 'ECB source identity differs')
    elif sid == 'GB.policy_rate':
        base, mark, frag = value.partition('#')
        _source_window(base)
        if mark:
            q = parse_qs(frag, strict_parsing=True)
            _intl_need(set(q) == {'receipt', 'artifact', 'endpoint', 'vintage'}
                        and q['receipt'] == [receipt['receipt_sha256']]
                        and len(q['artifact']) == 1 and re.fullmatch('[0-9a-f]{64}', q['artifact'][0])
                        and q['endpoint'] == ['current_latest']
                        and q['vintage'] == ['latest_retrieval'], 'BoE source identity differs')
    else:
        _source_url(sid, value)
        q = parse_qs(urlsplit(value).query, strict_parsing=True)
        _intl_need(q.get('lang', ['en']) == ['en'] and all(
            re.fullmatch(r'\d{4}(?:-\d{2}|-Q[1-4])?', x)
            for x in q.get('sinceTimePeriod', [])), 'unadmitted source query')


def _intl_disclosure(contract, settings, documents):
    """Re-assess exact serialized fields under the existing public feed policy."""
    from lib.intl_generation_publication import _validate_contract, _assess, _context_id, _policy_identity
    from lib.intl_eurostat_publication import instrument_id
    _validate_contract(contract)
    _intl_need(set(contract['measures']) <= set(_INTL_PUBLIC) | _INTL_HELD,
                'unadmitted public field')
    for c in contract['contexts']:
        _intl_need(c['market'] in {'JP', 'KR', 'TW', 'IN', 'AU', 'GB', 'EZ'}
                    and c['horizon'] in {'1m', '3m', '6m', '12m', 'ytd'}
                    and c['currency_basis'] in {'local', 'usd_unhedged'}
                    and c['id'] == _context_id(2, c['market'], c['horizon'], c['currency_basis']),
                    'unadmitted public context')
    qualified = []
    for sid, entry in contract['measures'].items():
        m, e, p = entry['native_measure'], entry['native_evidence'], contract['policies'][sid]
        _intl_need(m['reason'] in {None, 'not_supplied', 'source_unknown', 'disclosure_unknown',
                    'metadata_denied', 'value_denied', 'source_stale', 'source_failed',
                    'method_unsupported', 'instrument_mismatch', 'cycle_support_missing', 'component_disagreement'},
                    'unadmitted public reason')
        if p['policy_ref'] is not None:
            _intl_need(sid in _INTL_PUBLIC, 'held public policy')
            expected_ref = 'docs/INTERNATIONAL_MACRO_DATA_CONTRACT.md#' + _INTL_PUBLIC[sid]
            decision = {'owner_ref': 'scripts/build_intl.py', 'policy_ref': expected_ref}
            digest = documents.get(sid)
            _intl_need(p['policy_ref'] == expected_ref and digest == p['policy_document_sha256']
                        and p['policy_identity'] == _policy_identity(decision, p['metadata'], p['value_permission'], digest),
                        'unadmitted public policy identity')
        else:
            _intl_need(p['policy_document_sha256'] is None and p['policy_identity'] is None,
                        'negative policy contains dynamic identity')
        if m['quality'] != 'qualified':
            _intl_need(all(m[k] is None for k in set(m) - {'quality', 'reason', 'metadata', 'value_permission'})
                        and e == {'receipt_identity': None, 'publication_decision': None, 'clocks': {}}
                        and all(entry[k] is None for k in ('content_identity', 'qualification_identity', 'policy_identity')),
                        'negative public row contains dynamic data')
            continue
        _intl_need(sid in _INTL_PUBLIC and m['metadata'] == m['value_permission'] == 'allowed'
                    and p['metadata'] == p['value_permission'] == 'allowed', 'field not publicly admitted')
        ref = 'docs/INTERNATIONAL_MACRO_DATA_CONTRACT.md#' + _INTL_PUBLIC[sid]
        _intl_need(p['policy_ref'] == ref and documents.get(sid) == p['policy_document_sha256'],
                    'current public policy differs')
        if sid != 'EZ.policy_rate':
            field_setting = (settings.get('intl') or {}).get('field_publication', {}).get(sid)
            _intl_need(field_setting == {'status': 'confirmed', 'policy_ref': ref,
                                   'metadata': 'allowed', 'value_permission': 'allowed'},
                        'public field decision not confirmed')
        assessed = _assess(sid, m, e, contract['generation'], documents[sid])
        _intl_need(assessed == (m, e, entry['content_identity'], entry['qualification_identity'], p),
                    'serialized public qualification differs')
        kind = 'current_account' if sid == 'EZ.annual_current_account' else 'macro_yoy'
        instrument = {'kind': 'official_policy', 'id': 'deposit_facility' if sid == 'EZ.policy_rate' else 'bank_rate',
                      'market_id': sid.split('.')[0]} if sid in {'EZ.policy_rate', 'GB.policy_rate'} else {
                          'kind': kind, 'id': instrument_id(sid), 'market_id': 'EZ'}
        _intl_need(m['instrument'] == instrument, 'unadmitted public instrument')
        _intl_source_url(sid, m['source_reference'], e['receipt_identity'])
        from datetime import date
        for key in ('observation_at', 'calculation_at'):
            if m[key] is not None:
                _intl_stamp(m[key])
        period = m['period']
        if period is not None:
            _intl_need(type(period) is dict and set(period) == {'start', 'end', 'count', 'count_basis'}
                        and type(period['count']) is int and 0 < period['count'] <= 10000
                        and period['count_basis'] in {'release_periods', 'trading_days', 'calendar_days'},
                        'unadmitted public period')
            try:
                _intl_need(all(type(period[k]) is str and len(period[k]) == 10
                            for k in ('start', 'end'))
                            and date.fromisoformat(period['start']) <= date.fromisoformat(period['end']),
                            'invalid public period')
            except ValueError:
                raise ValueError('invalid public period') from None
        _intl_need(e['clocks'].get('period') == period, 'period clocks differ')
        _intl_need(re.fullmatch(r'(?:ecb-deposit:|boe-bank-rate:)?[0-9a-f]{64}', m['evidence_key']) is not None,
                    'invalid public evidence identity')
        for k, value in e['clocks'].items():
            if value is not None and k != 'period':
                _intl_stamp(value)
        qualified.append(sid)
    return sorted(qualified)


def _intl_points(contract, raw, settings, documents):
    """Finite admitted nominal-policy companion; never a private row dump."""
    import math
    from lib.intl_generation_publication import _parse_json
    from lib.intl_policy_publication import METHOD, MAPPING_POLICY, INSTRUMENTS, _digest
    from lib.intl_boe_source import _parse_source_clock
    from lib.intl_ecb_policy_publication import SOURCE_URL
    from lib.intl_boe_publication import _source_window
    p = _parse_json(raw); ref = contract['policy_points_ref']; generation = contract['generation']
    _intl_need(set(p) == {'schema', 'asof', 'generation', 'mapping', 'mapping_identity', 'qualification_identity', 'series'}
                and p['schema'] == 'intl.policy_points.v1' and p['asof'] is None
                and p['generation'] == generation and p['mapping_identity'] == ref['mapping_identity']
                and p['qualification_identity'] == ref['qualification_identity'], 'policy companion identity differs')
    m = p['mapping']
    _intl_need(set(m) == {'owner_ref', 'policy_ref', 'method_version', 'metadata', 'value_permission', 'policy_document_sha256', 'instruments'}
                and m['owner_ref'] == 'scripts/build_intl.py' and m['policy_ref'] == MAPPING_POLICY
                and m['method_version'] == METHOD and m['metadata'] == m['value_permission'] == 'allowed'
                and m['instruments'] == {e: {'instrument_id': i, 'instrument_ref': e + '.policy_rate', 'unit': 'percent'}
                                         for e, i in INSTRUMENTS.items()}
                and (settings.get('intl') or {}).get('policy_comparison_publication') == {
                    'status': 'confirmed', 'policy_ref': MAPPING_POLICY, 'metadata': 'allowed', 'value_permission': 'allowed'}
                and documents.get('mapping') == m['policy_document_sha256'],
                'policy companion not publicly admitted')
    mapping = _digest({'domain': 'intl-policy-mapping-v1', 'mapping': m,
                       'series_policies': {sid: contract['policies'][sid] for sid in ('EZ.policy_rate', 'GB.policy_rate')}})
    _intl_need(mapping == p['mapping_identity'] and set(p['series']) == {'EZ', 'GB'}, 'policy mapping differs')
    for economy, s in p['series'].items():
        _intl_need(set(s) == {'instrument_id', 'instrument_ref', 'unit', 'receipt_sha256', 'source_reference', 'clocks', 'rows'}
                    and s['instrument_id'] == INSTRUMENTS[economy] and s['instrument_ref'] == economy + '.policy_rate'
                    and s['unit'] == 'percent' and re.fullmatch('[0-9a-f]{64}', s['receipt_sha256']), 'unadmitted policy series')
        if economy == 'EZ':
            _intl_need(s['source_reference'] == SOURCE_URL, 'wrong ECB point source')
        else:
            _source_window(s['source_reference'])
        clocks = s['clocks']
        _intl_need(set(clocks) == {'requested_at', 'response_received_at', 'input_verified_at', 'committed_at',
                                  'provider_published_at', 'revision_vintage'}
                    and clocks['provider_published_at'] is None and clocks['revision_vintage'] is None,
                    'unadmitted point clocks')
        for k in ('requested_at', 'response_received_at', 'input_verified_at', 'committed_at'):
            _intl_stamp(clocks[k])
        _intl_need(type(s['rows']) is list and 0 < len(s['rows']) <= 50000, 'unbounded policy rows')
        dates = []
        for row in s['rows']:
            keys = {'date', 'value', 'status', 'source_updated_raw'} if economy == 'GB' else {
                'date', 'value', 'status', 'source_status_raw', 'source_confidentiality_raw'}
            _intl_need(set(row) == keys and re.fullmatch(r'\d{4}-\d{2}-\d{2}', row['date'])
                        and row['status'] in {'observed', 'withheld'}, 'unadmitted policy row')
            _intl_stamp(row['date']); dates.append(row['date'])
            _intl_need((row['status'] == 'observed' and type(row['value']) in {int, float} and math.isfinite(row['value']))
                        or (row['status'] == 'withheld' and row['value'] is None), 'invalid public point value')
            if economy == 'GB':
                if row['source_updated_raw'] is not None:
                    _parse_source_clock(row['source_updated_raw'])
            else:
                _intl_need(all(type(row[k]) is str and re.fullmatch('[A-Z -]{0,3}', row[k]) is not None
                                for k in ('source_status_raw', 'source_confidentiality_raw')), 'unadmitted source code')
                _intl_need(row['status'] != 'observed' or (row['source_status_raw'].strip() == 'A'
                            and row['source_confidentiality_raw'].strip() == 'F'), 'nonpublic point')
        _intl_need(dates == sorted(set(dates)), 'ambiguous point dates')
    expected = _digest({'domain': 'intl-policy-source-qualification-v1', 'mapping_identity': mapping,
                        'receipts': {e: s['receipt_sha256'] for e, s in p['series'].items()}})
    _intl_need(expected == p['qualification_identity'], 'point qualification differs')

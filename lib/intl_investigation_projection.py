"""IntlInvestigation resolved-packet projection (T007.S5).

Pure projection from explicit caller scope / requirements / presentation /
prior, a native binding, native closed measure payloads and receipt-bound
publication decisions into the frozen TypeScript packet shape::

    {exactContext, prior, current, requirements, owner}

No I/O, no clock reading, no network, no formula beyond a domain-separated
SHA-256 identity hash.  Every emitted value is copied from the caller's
explicit inputs or derived from them; nothing is inferred from a URL, a wall
clock or a hash.  A malformed scope or contract raises ``ValueError``; a
missing source never does - the measure becomes an ``unavailable``
observation and stays visible.

Guarantees:
* scope is explicit - the native binding and the request context must agree;
* qualification needs an admitted measure *and* a receipt-bound decision;
* denied / unknown / unavailable measures keep their negative distinction
  but lose every numeric, source, clock, identity and policy detail;
* the frozen packet shape is unchanged; provenance travels in a sidecar;
* "now" is never invented - caller clocks are copied as supplied.
"""

from __future__ import annotations

import hashlib
import json
import math
import re

from lib.intl_investigation_owner import MACRO_FIELDS, build_intl_owner_result
from lib.intl_workspace_macro import _period as _native_period

#: Measure ids this projection can qualify, with their exact admitted unit.
SUPPORTED_UNITS = {
    "JP.yield_10y": "percent",
    "JP.annual_current_account": "percent_gdp",
    "EZ.policy_rate": "percent",
    "GB.policy_rate": "percent",
    "EZ.gdp_yoy": "percent",
    "EZ.cpi_yoy": "percent",
    "EZ.annual_current_account": "percent_gdp",
}

_ECB_ID = "EZ.policy_rate"
_ECB_SOURCE_ID = "D.U2.EUR.4F.KR.DFR.LEV"
_ECB_INSTRUMENT_ID = "deposit_facility"
_OWNER_REF = "scripts/build_intl.py"

_CONTEXT_STRINGS = (
    "researchMarket", "toolBindingVersion", "periodIdentity", "currencyBasis",
    "returnBasis", "owner", "query", "cohort", "temporalPolicy",
)
_CONTEXT_KEYS = frozenset(_CONTEXT_STRINGS + ("selectedMeasureIds",))
_BINDING_KEYS = frozenset({
    "market", "horizon", "currency_basis", "return_basis", "binding_version", "generation"})
_REQUEST_KEYS = frozenset({
    "context", "requirements", "owner", "prior", "prior_authorized", "read",
    "membership", "enumerated_measure_ids", "facts", "tombstones"})
_REQUIREMENTS_KEYS = frozenset({"requiredMeasureIds", "unmetPrerequisites"})
_OWNER_KEYS = frozenset({
    "lang", "question", "marketLabel", "toolLabel", "periodLabel", "basisLabel",
    "savedAt", "updatedAt", "sourceGenerationAt", "rightsAt", "measureLabels", "unmetLabels"})
_OWNER_CLOCKS = ("savedAt", "updatedAt", "sourceGenerationAt", "rightsAt")
_OWNER_LABELS = ("question", "marketLabel", "toolLabel", "periodLabel", "basisLabel")
_FACT_KEYS = frozenset({"excluded", "correction"})
_EVIDENCE_KEYS = frozenset({"receipt_identity", "publication_decision", "clocks"})
_DECISION_KEYS = frozenset({
    "owner_ref", "policy_ref", "decision_ref", "metadata", "value_permission", "binding"})
_CLOCK_KEYS = frozenset({
    "observation_at", "calculation_at", "period", "vintage_at", "dataset_updated_at",
    "source_updated_at", "requested_at", "response_received_at", "input_verified_at",
    "committed_at"})
_PERIOD_KEYS = frozenset({"start", "end", "count", "count_basis"})
_INSTRUMENT_KEYS = frozenset({"kind", "id", "market_id"})
_READ_VALUES = frozenset({"ok", "denied", "unavailable"})
_MEMBERSHIP_VALUES = frozenset({"complete", "page", "top_k", "unknown"})
_PERMISSION_VALUES = frozenset({"allowed", "unknown", "denied"})
_PRIOR_KEYS = frozenset(set(_CONTEXT_STRINGS) | {
    "generation", "read", "membership", "observations", "tombstones"})
_OBSERVATION_KEYS = frozenset({
    "id", "availability", "qualified", "excluded", "correction", "contentIdentity",
    "qualificationIdentity", "interpretation"})
_INTERPRETATION_KEYS = frozenset({"value", "unit", "basis", "cohort"})
_AVAILABILITY_VALUES = frozenset({
    "available", "stale", "denied", "unavailable", "not_applicable"})
_CONTENT_DOMAIN = "intl-investigation-projection:content-identity:v1"
_QUALIFICATION_DOMAIN = "intl-investigation-projection:qualification-identity:v1"
_GENERATION_RE = re.compile(
    r"^im-workspace-generation:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}"
    r"-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_JS_SAFE_MAX = (1 << 53) - 1
_JS_SAFE_MIN = -(1 << 53) + 1


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def _is_text(value):
    return type(value) is str and len(value) > 0


def _is_number(value):
    """True for a finite, JS-representable number (never a bool)."""
    if type(value) is int:
        return _JS_SAFE_MIN <= value <= _JS_SAFE_MAX
    if type(value) is float:
        return math.isfinite(value)
    return False


def _plain_json(value, _seen=None):
    """True iff value is a plain JSON tree (no cycles, no exotic types)."""
    if value is None or type(value) in (bool, str, int):
        return True
    if type(value) is float:
        return math.isfinite(value)
    if type(value) not in (list, dict):
        return False
    seen = set() if _seen is None else _seen
    if id(value) in seen:
        return False
    seen.add(id(value))
    try:
        if type(value) is list:
            return all(_plain_json(item, seen) for item in value)
        return all(type(key) is str and _plain_json(item, seen)
                   for key, item in value.items())
    finally:
        seen.discard(id(value))


def _canonical_json(obj):
    """Deterministic JSON text used for identity hashing."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _sha256_hex(payload):
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _require_keys(name, obj, keys):
    _need(type(obj) is dict, "%s must be an object" % name)
    _need(set(obj) == set(keys),
          "%s must carry exactly: %s" % (name, ", ".join(sorted(keys))))


def _text(name, value):
    _need(_is_text(value), "%s must be a non-empty string" % name)
    return value


def _texts(name, value):
    _need(type(value) is list, "%s must be a list" % name)
    out = []
    for item in value:
        _need(_is_text(item), "%s must hold non-empty strings" % name)
        _need(item not in out, "%s must not repeat %s" % (name, item))
        out.append(item)
    return out


def _clock(name, value):
    _need(value is None or _is_text(value),
          "%s must be null or a non-empty string" % name)
    return value


def _typed_period(period, name):
    """Native period: null, a scalar string, or a typed period object."""
    if period is None:
        return None
    if type(period) is str:
        _need(period, "%s must not be an empty string" % name)
        return period
    _need(type(period) is dict,
          "%s must be null, a string or a typed period object" % name)
    return _native_period(period)


def _validate_binding(binding):
    _require_keys("native_binding", binding, _BINDING_KEYS)
    out = {}
    for key in ("market", "horizon", "currency_basis", "return_basis"):
        out[key] = _text("native_binding." + key, binding[key])
    version = binding["binding_version"]
    _need(type(version) is int and version == 2,
          "native_binding.binding_version must be the integer 2")
    out["binding_version"] = 2
    generation = binding["generation"]
    _need(type(generation) is str and _GENERATION_RE.match(generation),
          "native_binding.generation must be im-workspace-generation:<canonical uuid4>")
    out["generation"] = generation
    return out


def _validate_context(context, binding):
    _require_keys("request.context", context, _CONTEXT_KEYS)
    ctx = {}
    for key in _CONTEXT_STRINGS:
        ctx[key] = _text("request.context." + key, context[key])
    selected = _texts("request.context.selectedMeasureIds", context["selectedMeasureIds"])
    for key, expected in (("researchMarket", "market"), ("periodIdentity", "horizon"),
                          ("currencyBasis", "currency_basis"),
                          ("returnBasis", "return_basis")):
        _need(ctx[key] == binding[expected],
              "request.context.%s must equal native_binding.%s" % (key, expected))
    _need(ctx["toolBindingVersion"] == str(binding["binding_version"]),
          "request.context.toolBindingVersion must equal str(binding_version)")
    prefix = binding["market"] + "."
    for sid in selected:
        _need(sid.startswith(prefix),
              "selected measure ids must stay inside the native market prefix")
    return ctx, selected


def _validate_requirements(requirements, selected):
    _require_keys("request.requirements", requirements, _REQUIREMENTS_KEYS)
    required = _texts("request.requirements.requiredMeasureIds",
                      requirements["requiredMeasureIds"])
    unmet = _texts("request.requirements.unmetPrerequisites",
                   requirements["unmetPrerequisites"])
    for sid in required:
        _need(sid in selected,
              "requiredMeasureIds must be a subset of the selected measure ids")
    return required, unmet


def _validate_owner(owner, selected, unmet):
    _require_keys("request.owner", owner, _OWNER_KEYS)
    _need(owner["lang"] in ("en", "zh"), "request.owner.lang must be 'en' or 'zh'")
    for key in _OWNER_LABELS:
        _text("request.owner." + key, owner[key])
    for key in _OWNER_CLOCKS:
        _clock("request.owner." + key, owner[key])
    labels = owner["measureLabels"]
    _need(type(labels) is dict, "request.owner.measureLabels must be an object")
    _need(set(labels) == set(selected),
          "request.owner.measureLabels must cover exactly the selected measure ids")
    for sid, label in labels.items():
        _text("request.owner.measureLabels[%s]" % sid, label)
    unmet_labels = owner["unmetLabels"]
    _need(type(unmet_labels) is list, "request.owner.unmetLabels must be a list")
    _need(len(unmet_labels) == len(unmet),
          "request.owner.unmetLabels must align with requirements.unmetPrerequisites")
    for index, label in enumerate(unmet_labels):
        _text("request.owner.unmetLabels[%d]" % index, label)
    return dict(owner)


def _validate_prior(prior, authorized):
    """Validate the prior; it is never rewritten nor replaced by the current."""
    _need(type(authorized) is bool, "request.prior_authorized must be a boolean")
    if prior is None:
        _need(not authorized,
              "request.prior_authorized must be false when request.prior is null")
        return None, False
    _need(authorized,
          "request.prior_authorized must be true when request.prior is supplied")
    _require_keys("request.prior", prior, _PRIOR_KEYS)
    for key in _CONTEXT_STRINGS:
        _text("request.prior." + key, prior[key])
    _text("request.prior.generation", prior["generation"])
    _need(prior["read"] in _READ_VALUES, "request.prior.read must be ok|denied|unavailable")
    _need(prior["membership"] in _MEMBERSHIP_VALUES,
          "request.prior.membership must be complete|page|top_k|unknown")
    observations = prior["observations"]
    _need(type(observations) is list, "request.prior.observations must be a list")
    seen = set()
    for observation in observations:
        _require_keys("request.prior.observations[]", observation, _OBSERVATION_KEYS)
        oid = _text("request.prior.observations[].id", observation["id"])
        _need(oid not in seen, "request.prior.observations contains duplicate ids")
        seen.add(oid)
        _need(observation["availability"] in _AVAILABILITY_VALUES,
              "request.prior.observations[].availability is not a known value")
        for flag in ("qualified", "excluded", "correction"):
            _need(type(observation[flag]) is bool,
                  "request.prior.observations[].%s must be a boolean" % flag)
        for identity in ("contentIdentity", "qualificationIdentity"):
            value = observation[identity]
            _need(value is None or _is_text(value),
                  "request.prior.observations[].%s must be null or a string" % identity)
        interpretation = observation["interpretation"]
        if interpretation is not None:
            _require_keys("request.prior.observations[].interpretation",
                          interpretation, _INTERPRETATION_KEYS)
            value = interpretation["value"]
            _need(value is None or _is_number(value),
                  "request.prior.observations[].interpretation.value must be a number or null")
            for key in ("unit", "basis", "cohort"):
                item = interpretation[key]
                _need(item is None or _is_text(item),
                      "request.prior.observations[].interpretation.%s must be null or a string"
                      % key)
    tombstones = prior["tombstones"]
    _need(type(tombstones) is list, "request.prior.tombstones must be a list")
    tombstone_ids = set()
    for tombstone in tombstones:
        _text("request.prior.tombstones[]", tombstone)
        _need(tombstone not in tombstone_ids, "request.prior.tombstones contains duplicates")
        _need(tombstone not in seen, "request.prior.tombstones collides with prior observations")
        tombstone_ids.add(tombstone)
    return prior, True


def _validate_enumeration(enumerated, selected, membership):
    ids = _texts("request.enumerated_measure_ids", enumerated)
    for sid in ids:
        _need(sid in selected,
              "request.enumerated_measure_ids must be a subset of the selected ids")
    _need(membership != "complete" or set(ids) == set(selected),
          "request.enumerated_measure_ids must enumerate the full selected set "
          "when membership is complete")
    return ids


def _validate_facts(facts, selected):
    _need(type(facts) is dict, "request.facts must be an object")
    for sid, entry in facts.items():
        _need(sid in selected, "request.facts contains an id outside the selected set")
        _require_keys("request.facts[%s]" % sid, entry, _FACT_KEYS)
        for flag in ("excluded", "correction"):
            _need(type(entry[flag]) is bool,
                  "request.facts[%s].%s must be a boolean" % (sid, flag))
    return facts


def _validate_tombstones(tombstones, selected, measures, read, membership):
    ids = _texts("request.tombstones", tombstones)
    for sid in ids:
        _need(sid in selected, "request.tombstones must contain selected measure ids")
    _need(not ids or (read == "ok" and membership == "complete"),
          "request.tombstones requires read=ok and membership=complete")
    _need(not (set(ids) & set(measures)),
          "request.tombstones collides with supplied measures")
    return ids


def _validate_measures(measures, selected, market):
    _need(type(measures) is dict, "measures must be an object")
    for sid in sorted(set(measures) - set(selected)):
        raise ValueError("measures contains an id outside the selected set: %s" % sid)
    for sid, measure in measures.items():
        _require_keys("measures[%s]" % sid, measure, MACRO_FIELDS)
        _need(measure["value"] is None or _is_number(measure["value"]),
              "measures[%s].value must be a finite native number or null" % sid)
        _typed_period(measure["period"], "measures[%s].period" % sid)
        instrument = measure["instrument"]
        if instrument is not None:
            _require_keys("measures[%s].instrument" % sid, instrument, _INSTRUMENT_KEYS)
            _need(instrument["market_id"] == market,
                  "measures[%s].instrument.market_id must match the request market" % sid)
    return measures


def _validate_evidence(evidence, selected):
    _need(type(evidence) is dict, "evidence must be an object")
    for sid in sorted(set(evidence) - set(selected)):
        raise ValueError("evidence contains an id outside the selected set: %s" % sid)
    out = {}
    for sid in selected:
        entry = evidence.get(sid)
        if entry is None:
            out[sid] = {"receipt_identity": None, "publication_decision": None, "clocks": {}}
            continue
        _require_keys("evidence[%s]" % sid, entry, _EVIDENCE_KEYS)
        receipt = entry["receipt_identity"]
        _need(receipt is None or type(receipt) is dict,
              "evidence[%s].receipt_identity must be null or an object" % sid)
        decision = entry["publication_decision"]
        _need(decision is None or type(decision) is dict,
              "evidence[%s].publication_decision must be null or an object" % sid)
        clocks = entry["clocks"]
        _need(type(clocks) is dict, "evidence[%s].clocks must be an object" % sid)
        for key in sorted(set(clocks) - _CLOCK_KEYS):
            raise ValueError("evidence[%s].clocks has an unknown key: %s" % (sid, key))
        for key, value in clocks.items():
            if value is None:
                continue
            if key == "period":
                _typed_period(value, "evidence[%s].clocks.period" % sid)
            else:
                _need(_is_text(value),
                      "evidence[%s].clocks.%s must be null or a non-empty string" % (sid, key))
        out[sid] = {"receipt_identity": receipt,
                    "publication_decision": decision,
                    "clocks": dict(clocks)}
    return out


def _receipt_ok(receipt, sid):
    """A receipt identity is valid only in the exact family shape."""
    if type(receipt) is not dict:
        return False
    keys = ({"artifact_sha256", "provenance_sha256"} if sid == _ECB_ID else {"receipt_sha256"})
    if set(receipt) != keys:
        return False
    return all(type(value) is str and _SHA256_RE.match(value)
               for value in receipt.values())


def _expected_binding(sid, receipt, measure):
    """The only decision binding this projection will ever accept."""
    if receipt is None:
        return None
    if sid == _ECB_ID:
        if set(receipt) != {"artifact_sha256", "provenance_sha256"}:
            return None
        return {"market_id": "EZ",
                "field": "policy_rate",
                "instrument_id": _ECB_INSTRUMENT_ID,
                "source_id": _ECB_SOURCE_ID,
                "artifact_sha256": receipt["artifact_sha256"],
                "provenance_sha256": receipt["provenance_sha256"],
                "observation_at": measure["observation_at"],
                "value": measure["value"],
                "unit": measure["unit"]}
    if set(receipt) != {"receipt_sha256"}:
        return None
    return {"field": sid, "receipt_sha256": receipt["receipt_sha256"]}


def _same_value(expected, actual):
    if type(expected) in (int, float) and type(actual) in (int, float):
        return expected == actual
    return type(expected) is type(actual) and expected == actual


def _decision_ok(decision, sid, measure, receipt, generation):
    """True only for an actual, adopted, receipt-bound decision."""
    if type(decision) is not dict or set(decision) != _DECISION_KEYS:
        return False
    if decision["owner_ref"] != _OWNER_REF:
        return False
    if not _is_text(decision["policy_ref"]):
        return False
    if decision["decision_ref"] != generation + ":" + sid:
        return False
    if decision["metadata"] != "allowed" or decision["value_permission"] != "allowed":
        return False
    if decision["metadata"] != measure["metadata"]:
        return False
    if decision["value_permission"] != measure["value_permission"]:
        return False
    expected = _expected_binding(sid, receipt, measure)
    if expected is None:
        return False
    binding = decision["binding"]
    if type(binding) is not dict or set(binding) != set(expected):
        return False
    return all(_same_value(value, binding[key]) for key, value in expected.items())


def _content_identity(sid, measure, receipt):
    """Content identity: receipt-bound and policy-free (same value, same content)."""
    return _sha256_hex(_canonical_json({
        "domain": _CONTENT_DOMAIN,
        "receiptIdentity": receipt,
        "field": sid,
        "sourceReference": measure["source_reference"],
        "instrument": measure["instrument"],
        "period": measure["period"],
        "value": measure["value"],
    }))


def _qualification_identity(sid, decision, receipt):
    """Bind substantive adopted policy/permission, keeping generation separate."""
    return _sha256_hex(_canonical_json({
        "domain": _QUALIFICATION_DOMAIN,
        "decision": {key: value for key, value in decision.items() if key != "decision_ref"},
        "field": sid,
        "receiptIdentity": receipt,
    }))


def _frozen_observation(observation):
    """Require the actual accepted bridge's frozen observation shape."""
    _require_keys("owner_bridge.observation", observation, _OBSERVATION_KEYS)
    return dict(observation)


def _diag(diagnostics, code, measure_id=None, field=None):
    entry = {"code": code, "measure_id": measure_id}
    if field is not None:
        entry["field"] = field
    diagnostics.append(entry)
    return entry


def project_intl_resolved_packet(*, request, native_binding, measures, evidence):
    """Project explicit scope / prior / evidence into the frozen packet shape.

    Returns ``{"packet": dict, "diagnostics": list, "provenance": dict}``.
    Raises ``ValueError`` for a malformed scope or contract.  A missing
    source is never an error: the affected measure becomes an
    ``unavailable`` observation and stays visible.
    """
    for name, value in (("request", request), ("native_binding", native_binding),
                        ("measures", measures), ("evidence", evidence)):
        _need(_plain_json(value), "%s must be plain JSON" % name)

    diagnostics = []
    binding = _validate_binding(native_binding)
    _require_keys("request", request, _REQUEST_KEYS)
    ctx, selected = _validate_context(request["context"], binding)
    required, unmet = _validate_requirements(request["requirements"], selected)
    owner = _validate_owner(request["owner"], selected, unmet)
    prior, has_prior = _validate_prior(request["prior"], request["prior_authorized"])
    read, membership = request["read"], request["membership"]
    _need(read in _READ_VALUES, "request.read must be ok|denied|unavailable")
    _need(membership in _MEMBERSHIP_VALUES,
          "request.membership must be complete|page|top_k|unknown")
    enumerated = _validate_enumeration(request["enumerated_measure_ids"], selected, membership)
    facts = _validate_facts(request["facts"], selected)
    _validate_measures(measures, selected, ctx["researchMarket"])
    tombstones = _validate_tombstones(request["tombstones"], selected, measures, read, membership)
    evidence_map = _validate_evidence(evidence, selected)

    bridge_measures = {}
    bridge_origins = {}
    states = {}

    for sid in selected:
        measure = measures.get(sid)
        entry = evidence_map[sid]
        receipt = entry["receipt_identity"]
        decision = entry["publication_decision"]
        fact = facts.get(sid) or {}
        excluded = bool(fact.get("excluded", False))
        correction = bool(fact.get("correction", False))
        expected_unit = SUPPORTED_UNITS.get(sid)

        receipt_ok = receipt is not None and _receipt_ok(receipt, sid)
        if receipt is not None and not receipt_ok:
            _diag(diagnostics, "invalid_receipt_identity", sid, "receipt_identity")

        content_identity = None
        qualification_identity = None
        dynamic_ok = False
        downgraded = False

        if measure is not None:
            quality = measure["quality"]
            if (quality != "qualified" and measure["metadata"] == "allowed"
                    and read == "ok" and measure["reason"] is not None):
                diagnostics.append({"code": "source_state", "measure_id": sid,
                                    "source_reason": measure["reason"]})
            unit_ok = expected_unit is not None and measure["unit"] == expected_unit
            content_eligible = (measure["metadata"] == "allowed"
                                 and measure["value_permission"] == "allowed"
                                 and quality in ("qualified", "stale")
                                 and _is_number(measure["value"]))
            if expected_unit is None:
                _diag(diagnostics, "unsupported_measure", sid)
                downgraded = True
            elif not unit_ok:
                _diag(diagnostics, "unit_mismatch", sid, "unit")
                downgraded = True
            if content_eligible and not receipt_ok:
                if receipt is None:
                    _diag(diagnostics, "missing_receipt_identity", sid, "receipt_identity")
                downgraded = True

            bridged = dict(measure)
            if downgraded:
                # No receipt, no supported id, no admitted unit: the measure is
                # downgraded and every numeric / source / clock detail is
                # scrubbed rather than left to a fallback hash.
                bridged["quality"] = "unknown"
                for field_name in ("value", "unit", "source_reference", "observation_at",
                                    "calculation_at", "evidence_key", "period", "instrument"):
                    bridged[field_name] = None
            else:
                if type(measure["period"]) is dict:
                    # Deterministic compatibility representation for the
                    # bridge; the native typed period stays in the sidecar.
                    bridged["period"] = _canonical_json(measure["period"])
                if content_eligible and receipt_ok:
                    content_identity = _content_identity(sid, measure, receipt)
                if (quality == "qualified" and read == "ok" and not excluded
                        and content_eligible and receipt_ok):
                    if _decision_ok(decision, sid, measure, receipt, binding["generation"]):
                        qualification_identity = _qualification_identity(sid, decision, receipt)
                    else:
                        _diag(diagnostics,
                              "missing_publication_decision" if decision is None
                              else "invalid_publication_decision",
                              sid, "publication_decision")
            bridge_measures[sid] = bridged
            dynamic_ok = (read == "ok" and not downgraded
                          and measure["metadata"] == "allowed"
                          and measure["value_permission"] == "allowed"
                          and quality in ("qualified", "stale") and receipt_ok)

        bridge_origins[sid] = {"content_identity": content_identity,
                               "qualification_identity": qualification_identity,
                               "excluded": excluded,
                               "correction": correction}
        states[sid] = {"quality": measure["quality"] if measure is not None else None,
                       "excluded": excluded,
                       "correction": correction,
                       "dynamic_ok": dynamic_ok,
                       "reason": measure["reason"] if measure is not None else None,
                       "receipt": receipt,
                       "decision": decision,
                       "clocks": entry["clocks"],
                       "period": measure["period"] if measure is not None else None,
                       "source_reference": measure["source_reference"] if measure is not None else None,
                       "instrument": measure["instrument"] if measure is not None else None}

    built = build_intl_owner_result(
        context=dict(ctx, selectedMeasureIds=list(selected)),
        generation=binding["generation"],
        measures=bridge_measures,
        origins=bridge_origins,
        clocks=None,
        membership=membership,
        read=read,
    )
    if built["result"] is None:
        raise ValueError("the accepted owner bridge rejected the measure contract: %s"
                         % _canonical_json(built["diagnostics"]))

    current = dict(built["result"])
    # The frozen TS packet's current never carries selectedMeasureIds.
    current.pop("selectedMeasureIds", None)
    frozen = [_frozen_observation(item) for item in current["observations"]]
    by_id = {item["id"]: item for item in frozen}
    tombstone_ids = set(tombstones)
    current["observations"] = [item for item in frozen if item["id"] not in tombstone_ids]
    current["tombstones"] = list(tombstones)
    for sid in tombstones:
        _diag(diagnostics, "tombstone_applied", sid)

    for item in built["diagnostics"]:
        # The bridge's own clock envelope is deliberately left unpopulated:
        # this projection never invents a publication clock, and the source
        # clocks travel in the sidecar instead.
        if item.get("code") != "missing_clock":
            diagnostics.append(item)

    observed_at_by_id = {}
    for sid in selected:
        observation = by_id.get(sid)
        interpretation = observation["interpretation"] if observation else None
        measure = measures.get(sid)
        observed_at_by_id[sid] = (measure["observation_at"]
                                  if interpretation is not None and measure is not None
                                  else None)
    owner["observedAtByMeasureId"] = observed_at_by_id

    scope_changed = False
    if has_prior:
        scope_changed = any(prior[key] != ctx[key] for key in _CONTEXT_STRINGS)
        if scope_changed:
            _diag(diagnostics, "scope_changed", None, "prior")

    prov_measures = {}
    for sid in selected:
        state = states[sid]
        observation = by_id.get(sid)
        entry = {"quality": state["quality"],
                 "availability": observation["availability"] if observation else "unavailable",
                 "qualified": observation["qualified"] if observation else False,
                 "excluded": state["excluded"],
                 "correction": state["correction"]}
        if state["dynamic_ok"]:
            entry["reason"] = state["reason"]
            entry["receiptIdentity"] = state["receipt"]
            # Stale/unqualified metadata may remain disclosed, but its old
            # ECB decision can contain a numeric binding. Do not carry that
            # number as an alternative to the withheld interpretation.
            entry["publicationDecision"] = state["decision"] if entry["qualified"] else None
            decision = state["decision"]
            metric = measures.get(sid)
            entry["policyReference"] = (decision["policy_ref"]
                if metric is not None and _decision_ok(decision, sid, metric, state["receipt"], binding["generation"])
                else None)
            entry["clocks"] = dict(state["clocks"])
            entry["period"] = state["period"]
            entry["sourceReference"] = state["source_reference"]
            entry["instrument"] = state["instrument"]
            entry["contentIdentity"] = (observation["contentIdentity"]
                                        if observation else None)
            entry["qualificationIdentity"] = (observation["qualificationIdentity"]
                                              if observation else None)
        prov_measures[sid] = entry

    exact_context = dict(ctx)
    exact_context["selectedMeasureIds"] = list(selected)
    packet = {
        "exactContext": exact_context,
        "prior": prior,
        "current": current,
        "requirements": {"requiredMeasureIds": list(required),
                         "unmetPrerequisites": list(unmet)},
        "owner": owner,
    }
    provenance = {
        "generation": binding["generation"],
        "bindingVersion": str(binding["binding_version"]),
        "researchMarket": binding["market"],
        "enumeratedMeasureIds": list(enumerated),
        "priorScopeChanged": scope_changed,
        "publicationClock": None,
        "measures": prov_measures,
    }
    return {"packet": packet, "diagnostics": diagnostics, "provenance": provenance}


__all__ = ["project_intl_resolved_packet", "SUPPORTED_UNITS"]

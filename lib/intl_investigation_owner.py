"""IntlInvestigation owner bridge.

Pure-Python bridge that converts trusted caller inputs (the admitted
per-measure macro payload plus caller-supplied pre-presentation origins)
into a frozen IntlOwnerResult envelope.

This module performs no I/O, no config, no clock reading, and no formulas
beyond a domain-separated SHA-256 content identity hash. It is a trusted
caller contract: it does NOT authenticate, validate, or grant anything.

Spec highlights (from the binding brief):
* Exactly nine non-empty context strings plus a unique-listed
  ``selectedMeasureIds`` are required inside ``context``.
* ``generation`` is supplied by the publisher and never generated here.
* ``read`` is one of ``ok|denied|unavailable``; ``membership`` is one of
  ``complete|page|top_k|unknown`` -- completeness is never inferred.
* Measures admit a closed Macro field set; everything else is rejected.
* Availability: denied (whole read or metadata/value denied); unavailable
  (whole read, unknown/missing/failed/unsupported, or huge int);
  stale (quality==stale); available (only qualified with metadata+value
  allowed and a finite JS-representable numeric value).
* Qualified interpretation is emitted only when available AND qualified AND
  not excluded AND whole read OK AND a finite numeric value AND an explicit
  origin ``qualification_identity``. It contains only {value, unit,
  basis=context.currencyBasis, cohort=context.cohort}.
* Denied/unknown metadata never includes content identities, qualification
  identities, value, or source in the result. Whole denied scrubs all
  identities; whole unavailable scrubs interpretation and may preserve
  only already-allowed-metadata identities.
* Clocks (separate envelope) never enter the frozen IntlOwnerResult.
"""

from __future__ import annotations

import hashlib
import json
import math


# ---------------------------------------------------------------------------
# Closed constants
# ---------------------------------------------------------------------------

MACRO_FIELDS = frozenset({
    "quality",
    "reason",
    "metadata",
    "value_permission",
    "value",
    "unit",
    "instrument",
    "period",
    "observation_at",
    "calculation_at",
    "source_reference",
    "evidence_key",
})

_QUALITY_VALUES = frozenset({
    "qualified",
    "stale",
    "missing",
    "denied",
    "failed",
    "unsupported",
    "unknown",
})

_PERMISSION_VALUES = frozenset({"allowed", "unknown", "denied"})
_READ_VALUES = frozenset({"ok", "denied", "unavailable"})
_MEMBERSHIP_VALUES = frozenset({"complete", "page", "top_k", "unknown"})

_STRING_CONTEXT_KEYS = (
    "researchMarket",
    "toolBindingVersion",
    "periodIdentity",
    "currencyBasis",
    "returnBasis",
    "owner",
    "query",
    "cohort",
    "temporalPolicy",
)
_CONTEXT_KEYS = frozenset(_STRING_CONTEXT_KEYS + ("selectedMeasureIds",))

_INSTRUMENT_KEYS = frozenset({"kind", "id", "market_id"})

# JavaScript safe integer bounds. Values outside this range are refused.
_JS_SAFE_MAX = (1 << 53) - 1
_JS_SAFE_MIN = -(1 << 53) + 1

# Domain separation for the content-identity hash. Changing this string
# invalidates all previously-emitted content identities.
_CONTENT_HASH_DOMAIN = b"intl-investigation-owner:content-identity:v1\n"


# ---------------------------------------------------------------------------
# Small helpers (pure; no I/O, no clock, no config, no formula)
# ---------------------------------------------------------------------------

def _is_nonempty_str(v):
    return type(v) is str and len(v) > 0


def _is_finite_js_numeric(v):
    """True iff v is a finite, JS-representable numeric (not bool/str/NaN/Inf)."""
    if isinstance(v, bool):
        return False
    if isinstance(v, int):
        return _JS_SAFE_MIN <= v <= _JS_SAFE_MAX
    if isinstance(v, float):
        return not (math.isnan(v) or math.isinf(v))
    return False


def _is_huge_int(v):
    """True iff v is an integer outside the JS-safe range."""
    return (
        isinstance(v, int)
        and not isinstance(v, bool)
        and (v > _JS_SAFE_MAX or v < _JS_SAFE_MIN)
    )


def _canonical_json(obj):
    """Deterministic JSON for hashing (sorted keys, no spaces)."""
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _compute_content_identity(sid, m):
    """SHA-256 (hex) over canonical, qualification-excluded payload."""
    canonical = {
        "calculation_at": m["calculation_at"],
        "instrument": m["instrument"],
        "measure_id": sid,
        "observation_at": m["observation_at"],
        "period": m["period"],
        "source_reference": m["source_reference"],
        "unit": m["unit"],
        "value": m["value"],
    }
    payload = _CONTENT_HASH_DOMAIN + _canonical_json(canonical).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _diag(diagnostics, code, measure_id=None, field=None):
    entry = {"code": code, "measure_id": measure_id}
    if field is not None:
        entry["field"] = field
    diagnostics.append(entry)
    return entry


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def build_intl_owner_result(
    *,
    context,
    generation,
    measures,
    origins=None,
    clocks=None,
    membership="unknown",
    read="ok",
):
    """Build a frozen IntlOwnerResult envelope.

    Returns ``{result: IntlOwnerResult|null,
                diagnostics: list[{code, measure_id, [field]}],
                clocks: {published_at, source_observed_at, rights_at}}``.

    The result never contains clocks. Clocks are returned as a separate
    envelope alongside ``diagnostics``.
    """
    def plain(v, seen=None):
        if v is None or type(v) in (str, bool, int, float): return True
        if type(v) not in (dict, list): return False
        seen = set() if seen is None else seen
        if id(v) in seen: return False
        seen.add(id(v))
        try:
            return (all(type(k) is str and plain(x, seen) for k, x in v.items())
                    if type(v) is dict else all(plain(x, seen) for x in v))
        finally: seen.remove(id(v))
    if not plain(context):
        return {"result": None, "diagnostics": [{"code": "invalid_context", "measure_id": None}],
                "clocks": {"published_at": None, "source_observed_at": None, "rights_at": None}}
    if not all(plain(v) for v in (measures, origins, clocks, read, membership)):
        return {"result": None, "diagnostics": [{"code": "invalid_owner_input", "measure_id": None}],
                "clocks": {"published_at": None, "source_observed_at": None, "rights_at": None}}
    diagnostics = []

    # --- Clocks envelope ----------------------------------------------------
    clocks_out = {
        "published_at": None,
        "source_observed_at": None,
        "rights_at": None,
    }
    if clocks is None:
        for key in clocks_out:
            _diag(diagnostics, "missing_clock", measure_id=None, field=key)
    if clocks is not None:
        if type(clocks) is not dict or set(clocks) - set(clocks_out):
            return {"result": None, "diagnostics": [{"code": "invalid_owner_input", "measure_id": None}], "clocks": clocks_out}
        if not isinstance(clocks, dict):
            _diag(diagnostics, "invalid_owner_input",
                  measure_id=None, field="clocks")
            return {"result": None, "diagnostics": diagnostics, "clocks": clocks_out}
        for key in ("published_at", "source_observed_at", "rights_at"):
            if key not in clocks:
                clocks_out[key] = None
                _diag(diagnostics, "missing_clock", measure_id=None, field=key)
                continue
            v = clocks[key]
            if v is None:
                clocks_out[key] = None
                _diag(diagnostics, "missing_clock", measure_id=None, field=key)
            elif _is_nonempty_str(v):
                clocks_out[key] = v
            else:
                _diag(diagnostics, "invalid_owner_input", measure_id=None, field=key)
                return {"result": None, "diagnostics": diagnostics, "clocks": clocks_out}

    # --- Generation ---------------------------------------------------------
    if not _is_nonempty_str(generation):
        _diag(diagnostics, "missing_owner_input",
              measure_id=None, field="generation")
        return {"result": None, "diagnostics": diagnostics, "clocks": clocks_out}

    # --- Enums --------------------------------------------------------------
    if type(read) is not str or read not in _READ_VALUES:
        _diag(diagnostics, "invalid_owner_input",
              measure_id=None, field="read")
        return {"result": None, "diagnostics": diagnostics, "clocks": clocks_out}
    if type(membership) is not str or membership not in _MEMBERSHIP_VALUES:
        _diag(diagnostics, "invalid_owner_input",
              measure_id=None, field="membership")
        return {"result": None, "diagnostics": diagnostics, "clocks": clocks_out}

    # --- Context ------------------------------------------------------------
    if not isinstance(context, dict):
        _diag(diagnostics, "invalid_context",
              measure_id=None, field="context")
        return {"result": None, "diagnostics": diagnostics, "clocks": clocks_out}

    ctx_out = {}
    for key in _STRING_CONTEXT_KEYS:
        if key not in context:
            _diag(diagnostics, "invalid_context",
                  measure_id=None, field=key)
            return {"result": None,
                    "diagnostics": diagnostics,
                    "clocks": clocks_out}
        v = context[key]
        if not _is_nonempty_str(v):
            _diag(diagnostics, "invalid_context",
                  measure_id=None, field=key)
            return {"result": None,
                    "diagnostics": diagnostics,
                    "clocks": clocks_out}
        ctx_out[key] = v

    if "selectedMeasureIds" not in context:
        _diag(diagnostics, "invalid_context",
              measure_id=None, field="selectedMeasureIds")
        return {"result": None, "diagnostics": diagnostics, "clocks": clocks_out}

    sel_raw = context["selectedMeasureIds"]
    if not isinstance(sel_raw, list):
        _diag(diagnostics, "invalid_context",
              measure_id=None, field="selectedMeasureIds")
        return {"result": None, "diagnostics": diagnostics, "clocks": clocks_out}

    selected = []
    seen = set()
    for item in sel_raw:
        if not _is_nonempty_str(item):
            _diag(diagnostics, "invalid_context",
                  measure_id=None, field="selectedMeasureIds")
            return {"result": None,
                    "diagnostics": diagnostics,
                    "clocks": clocks_out}
        if item in seen:
            _diag(diagnostics, "invalid_context",
                  measure_id=None, field="selectedMeasureIds")
            return {"result": None,
                    "diagnostics": diagnostics,
                    "clocks": clocks_out}
        seen.add(item)
        selected.append(item)
    # empty list is explicitly valid per spec

    # Reject any extra keys in context.
    for key in context:
        if key not in _CONTEXT_KEYS:
            _diag(diagnostics, "invalid_context",
                  measure_id=None, field=key)
            return {"result": None, "diagnostics": diagnostics, "clocks": clocks_out}

    market = ctx_out["researchMarket"]
    prefix = market + "."
    for sid in selected:
        if not sid.startswith(prefix):
            _diag(diagnostics, "invalid_owner_input",
                  measure_id=None, field="scope_mismatch")
            return {"result": None, "diagnostics": diagnostics, "clocks": clocks_out}

    # --- Measures -----------------------------------------------------------
    if not isinstance(measures, dict):
        _diag(diagnostics, "invalid_owner_input",
              measure_id=None, field="measures")
        return {"result": None, "diagnostics": diagnostics, "clocks": clocks_out}

    for key in measures:
        if key not in seen:
            _diag(diagnostics, "invalid_owner_input",
                  measure_id=None, field="scope_mismatch")
            return {"result": None, "diagnostics": diagnostics, "clocks": clocks_out}
        if not key.startswith(prefix):
            _diag(diagnostics, "invalid_owner_input",
                  measure_id=None, field="scope_mismatch")
            return {"result": None, "diagnostics": diagnostics, "clocks": clocks_out}

    # --- Origins ------------------------------------------------------------
    origins_map = {}
    if origins is not None:
        if not isinstance(origins, dict):
            _diag(diagnostics, "invalid_owner_input",
                  measure_id=None, field="origins")
            return {"result": None, "diagnostics": diagnostics, "clocks": clocks_out}
        for ok in origins:
            if ok not in seen:
                _diag(diagnostics, "invalid_owner_input",
                      measure_id=None, field="origins_scope")
                return {"result": None,
                        "diagnostics": diagnostics,
                        "clocks": clocks_out}
            ov = origins[ok]
            if ov is None:
                origins_map[ok] = {
                    "content_identity": None,
                    "qualification_identity": None,
                    "excluded": False,
                    "correction": False,
                }
                continue
            if not isinstance(ov, dict):
                _diag(diagnostics, "invalid_owner_input",
                      measure_id=ok, field="origins")
                return {"result": None,
                        "diagnostics": diagnostics,
                        "clocks": clocks_out}
            if set(ov) - {"content_identity", "qualification_identity", "excluded", "correction"}:
                _diag(diagnostics, "invalid_owner_input", measure_id=ok, field="origins")
                return {"result": None, "diagnostics": diagnostics, "clocks": clocks_out}
            ci = ov.get("content_identity", None)
            qi = ov.get("qualification_identity", None)
            excl = ov.get("excluded", False)
            corr = ov.get("correction", False)
            if ci is not None and not _is_nonempty_str(ci):
                _diag(diagnostics, "invalid_owner_input",
                      measure_id=ok, field="origins_content_identity")
                return {"result": None,
                        "diagnostics": diagnostics,
                        "clocks": clocks_out}
            if qi is not None and not _is_nonempty_str(qi):
                _diag(diagnostics, "invalid_owner_input",
                      measure_id=ok, field="origins_qualification_identity")
                return {"result": None,
                        "diagnostics": diagnostics,
                        "clocks": clocks_out}
            if not isinstance(excl, bool):
                _diag(diagnostics, "invalid_owner_input",
                      measure_id=ok, field="origins_excluded")
                return {"result": None,
                        "diagnostics": diagnostics,
                        "clocks": clocks_out}
            if not isinstance(corr, bool):
                _diag(diagnostics, "invalid_owner_input",
                      measure_id=ok, field="origins_correction")
                return {"result": None,
                        "diagnostics": diagnostics,
                        "clocks": clocks_out}
            origins_map[ok] = {
                "content_identity": ci,
                "qualification_identity": qi,
                "excluded": excl,
                "correction": corr,
            }

    # --- Whole-read state ---------------------------------------------------
    whole_denied = (read == "denied")
    whole_unavailable = (read == "unavailable")
    whole_ok = (read == "ok")

    observations = []

    for sid in selected:
        origin_entry = origins_map.get(
            sid,
            {
                "content_identity": None,
                "qualification_identity": None,
                "excluded": False,
                "correction": False,
            },
        )

        if sid not in measures or measures[sid] is None:
            observations.append({
                "id": sid,
                "availability": "unavailable",
                "qualified": False,
                "excluded": origin_entry["excluded"],
                "correction": origin_entry["correction"],
                "contentIdentity": None,
                "qualificationIdentity": None,
                "interpretation": None,
            })
            _diag(diagnostics, "missing_owner_input", measure_id=sid)
            continue

        m = measures[sid]

        if not isinstance(m, dict):
            _diag(diagnostics, "invalid_owner_input",
                  measure_id=sid, field="measure_type")
            return {"result": None, "diagnostics": diagnostics, "clocks": clocks_out}

        if set(m.keys()) != MACRO_FIELDS:
            _diag(diagnostics, "invalid_owner_input",
                  measure_id=sid, field="macro_fields")
            return {"result": None, "diagnostics": diagnostics, "clocks": clocks_out}

        quality = m["quality"]
        reason = m["reason"]
        metadata = m["metadata"]
        value_permission = m["value_permission"]
        value = m["value"]
        unit = m["unit"]
        instrument = m["instrument"]
        period = m["period"]
        observation_at = m["observation_at"]
        calculation_at = m["calculation_at"]
        source_reference = m["source_reference"]
        evidence_key = m["evidence_key"]

        # Type validators ----------------------------------------------------
        if type(quality) is not str or quality not in _QUALITY_VALUES:
            _diag(diagnostics, "invalid_owner_input",
                  measure_id=sid, field="quality")
            return {"result": None,
                    "diagnostics": diagnostics,
                    "clocks": clocks_out}
        if type(metadata) is not str or metadata not in _PERMISSION_VALUES:
            _diag(diagnostics, "invalid_owner_input",
                  measure_id=sid, field="metadata")
            return {"result": None,
                    "diagnostics": diagnostics,
                    "clocks": clocks_out}
        if type(value_permission) is not str or value_permission not in _PERMISSION_VALUES:
            _diag(diagnostics, "invalid_owner_input",
                  measure_id=sid, field="value_permission")
            return {"result": None,
                    "diagnostics": diagnostics,
                    "clocks": clocks_out}

        for fld, name in (
            (reason, "reason"),
            (unit, "unit"),
            (period, "period"),
            (observation_at, "observation_at"),
            (calculation_at, "calculation_at"),
            (source_reference, "source_reference"),
            (evidence_key, "evidence_key"),
        ):
            if fld is not None and not _is_nonempty_str(fld):
                _diag(diagnostics, "invalid_owner_input",
                      measure_id=sid, field=name)
                return {"result": None,
                        "diagnostics": diagnostics,
                        "clocks": clocks_out}

        # Instrument ---------------------------------------------------------
        if instrument is not None:
            if (not isinstance(instrument, dict)
                    or set(instrument.keys()) != _INSTRUMENT_KEYS):
                _diag(diagnostics, "invalid_owner_input",
                      measure_id=sid, field="instrument")
                return {"result": None,
                        "diagnostics": diagnostics,
                        "clocks": clocks_out}
            ik = instrument.get("kind")
            iid = instrument.get("id")
            imkt = instrument.get("market_id")
            if not _is_nonempty_str(ik):
                _diag(diagnostics, "invalid_owner_input",
                      measure_id=sid, field="instrument_kind")
                return {"result": None,
                        "diagnostics": diagnostics,
                        "clocks": clocks_out}
            if not _is_nonempty_str(iid):
                _diag(diagnostics, "invalid_owner_input",
                      measure_id=sid, field="instrument_id")
                return {"result": None,
                        "diagnostics": diagnostics,
                        "clocks": clocks_out}
            if imkt != market:
                _diag(diagnostics, "invalid_owner_input",
                      measure_id=sid, field="instrument_market")
                return {"result": None,
                        "diagnostics": diagnostics,
                        "clocks": clocks_out}

        # Value validation ---------------------------------------------------
        huge_int = False
        if value is not None:
            if type(value) not in (int, float):
                _diag(diagnostics, "invalid_owner_input", measure_id=sid, field="value")
                return {"result": None, "diagnostics": diagnostics, "clocks": clocks_out}
            if isinstance(value, bool):
                _diag(diagnostics, "invalid_owner_input",
                      measure_id=sid, field="value")
                return {"result": None,
                        "diagnostics": diagnostics,
                        "clocks": clocks_out}
            if isinstance(value, str):
                _diag(diagnostics, "invalid_owner_input",
                      measure_id=sid, field="value")
                return {"result": None,
                        "diagnostics": diagnostics,
                        "clocks": clocks_out}
            if isinstance(value, float) and (
                math.isnan(value) or math.isinf(value)
            ):
                _diag(diagnostics, "invalid_owner_input",
                      measure_id=sid, field="value")
                return {"result": None,
                        "diagnostics": diagnostics,
                        "clocks": clocks_out}
            if isinstance(value, int):
                if value > _JS_SAFE_MAX or value < _JS_SAFE_MIN:
                    huge_int = True

        # Availability -------------------------------------------------------
        if huge_int:
            avail = "unavailable"
            _diag(diagnostics, "invalid_owner_input",
                  measure_id=sid, field="value_huge")
        elif whole_denied:
            avail = "denied"
        elif metadata == "denied" or value_permission == "denied":
            avail = "denied"
        elif whole_unavailable:
            avail = "unavailable"
        elif quality in ("unknown", "missing", "failed", "unsupported"):
            avail = "unavailable"
        elif quality == "denied":
            avail = "denied"
        elif quality == "stale":
            avail = "stale"
        elif quality == "qualified":
            if (
                metadata == "allowed"
                and value_permission == "allowed"
                and value is not None
                and _is_finite_js_numeric(value)
            ):
                avail = "available"
            else:
                avail = "unavailable"
        else:
            avail = "unavailable"

        # Content identity eligibility --------------------------------------
        content_eligible = (
            metadata == "allowed"
            and value_permission == "allowed"
            and quality in ("qualified", "stale")
            and value is not None
            and not isinstance(value, bool)
            and not isinstance(value, str)
            and not huge_int
            and (
                (isinstance(value, float)
                 and not math.isnan(value)
                 and not math.isinf(value))
                or (
                    isinstance(value, int)
                    and _JS_SAFE_MIN <= value <= _JS_SAFE_MAX
                )
            )
        )

        # Identities --------------------------------------------------------
        identities = None
        if not whole_denied:
            ci = origin_entry["content_identity"]
            qi = origin_entry["qualification_identity"]

            if ci is None and content_eligible:
                ci = _compute_content_identity(sid, m)

            if whole_unavailable:
                # May preserve only already allowed-metadata identities.
                if metadata == "allowed":
                    id_obj = {}
                    if ci is not None:
                        id_obj["content"] = ci
                    if qi is not None:
                        id_obj["qualification"] = qi
                    if id_obj:
                        identities = id_obj
                # else: stays None
            elif metadata in ("denied", "unknown"):
                # denied/unknown metadata MUST NEVER include identities.
                identities = None
            else:
                id_obj = {}
                if ci is not None:
                    id_obj["content"] = ci
                if qi is not None:
                    id_obj["qualification"] = qi
                if id_obj:
                    identities = id_obj

        # Qualified ----------------------------------------------------------
        qualified = False
        if avail == "available":
            qualified = (
                _is_finite_js_numeric(value)
                and unit is not None
                and source_reference is not None
                and observation_at is not None
                and instrument is not None
                and origin_entry["qualification_identity"] is not None
            )

        # Interpretation ----------------------------------------------------
        interpretation = None
        if (
            avail == "available"
            and qualified
            and not origin_entry["excluded"]
            and whole_ok
            and _is_finite_js_numeric(value)
            and origin_entry["qualification_identity"] is not None
        ):
            interpretation = {
                "value": value,
                "unit": unit,
                "basis": ctx_out["currencyBasis"],
                "cohort": ctx_out["cohort"],
            }

        # Missing qualification identity diagnostic -------------------------
        if avail == "available" and origin_entry["qualification_identity"] is None:
            _diag(diagnostics, "missing_qualification_identity",
                  measure_id=sid)

        observations.append({
            "id": sid,
            "availability": avail,
            "qualified": qualified,
            "excluded": origin_entry["excluded"],
            "correction": origin_entry["correction"],
            "contentIdentity": (identities or {}).get("content"),
            "qualificationIdentity": (identities or {}).get("qualification"),
            "interpretation": interpretation,
        })

    # --- Frozen IntlOwnerResult (no clocks) -------------------------------
    result = {
        "researchMarket": ctx_out["researchMarket"],
        "toolBindingVersion": ctx_out["toolBindingVersion"],
        "periodIdentity": ctx_out["periodIdentity"],
        "currencyBasis": ctx_out["currencyBasis"],
        "returnBasis": ctx_out["returnBasis"],
        "owner": ctx_out["owner"],
        "query": ctx_out["query"],
        "cohort": ctx_out["cohort"],
        "temporalPolicy": ctx_out["temporalPolicy"],
        "generation": generation,
        "read": read,
        "membership": membership,
        "observations": list(observations),
        "tombstones": [],
    }

    return {
        "result": result,
        "diagnostics": list(diagnostics),
        "clocks": clocks_out,
    }


__all__ = ["build_intl_owner_result", "MACRO_FIELDS"]

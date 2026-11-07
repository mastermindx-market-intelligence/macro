"""Bind the incumbent derived Risk summary to its successful native publication.

This issues evidence for existing state/boolean output, not additional raw-data
disclosure, model authority or provider rights. Input fingerprints describe the
calculation frames; they are explicitly not parquet/vendor payload hashes.
"""
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re

from lib.intl_workspace_risk import (
    qualify_us_transmission, _NATIVE_RISK_SOURCES as _SOURCES,
    _NATIVE_ORIGIN_LEGS as _ORIGIN_LEGS, _risk_snapshot_bytes as _body,
    _native_clock as _clock, _native_observation as _observation,
)


_POLICY_REF = "docs/INTERNATIONAL_MACRO_DATA_CONTRACT.md#incumbent-us-transmission-derived-summary"
_PUBLIC_FIELDS = {"state", "evidence_refs", "diagnostic.reported_state",
                  "calculation_at", "observation_dates", "origin_coverage"}


def _summary_policy_allowed(policy):
    if type(policy) is not dict:
        return False
    if not all(type(policy.get(key)) is str for key in
               ("status", "scope", "policy_ref", "metadata", "value_permission", "audience")):
        return False
    fields = policy.get("fields")
    return (
        policy.get("status") == "confirmed"
        and policy.get("scope") == "intl-us-transmission-derived-summary-v1"
        and policy.get("policy_ref") == _POLICY_REF
        and policy.get("metadata") == "allowed"
        and policy.get("value_permission") == "allowed"
        and policy.get("audience") == "anonymous-and-registered-intl-html"
        and type(fields) is list and len(fields) == len(_PUBLIC_FIELDS)
        and all(type(field) is str for field in fields) and set(fields) == _PUBLIC_FIELDS
    )



@dataclass(frozen=True)
class RiskPublication:
    """An owned successful write/read identity, never a supplied data grant."""

    path: Path
    artifact_sha256: str


def publish_risk_snapshot(path, payload):
    """Write the existing latest.json and return only verified success.

    Exceptions remain with the incumbent publisher's original error boundary.
    A failed write cannot fall back to an older otherwise-identical file.
    """
    path = Path(path)
    expected = _body(payload)
    path.write_text(expected.decode("utf-8"), encoding="utf-8")
    if path.read_bytes() != expected:
        raise OSError("native Risk publication readback mismatch")
    return RiskPublication(path, sha256(expected).hexdigest())


def _receipt(value, reference, observed, source_reference=None):
    return {
        "quality": "qualified", "metadata": "allowed", "value_permission": "allowed",
        "reported_value": value, "evidence_key": reference,
        "source_reference": source_reference or reference, "observation_at": observed,
    }


def risk_summary_eligibility(*, risk_desk, publication, policy=None):
    """Project only the successfully published, complete native summary inputs.

    No build clock substitutes for an observation. Model-qualified partial
    origin coverage (the incumbent minimum three) remains distinct from six
    observed inputs. The optional safety bid never fills a required leg.
    """
    if (not _summary_policy_allowed(policy)
            or type(publication) is not RiskPublication or type(risk_desk) is not dict):
        return {}
    try:
        body = publication.path.read_bytes()
        if sha256(body).hexdigest() != publication.artifact_sha256 or body != _body(risk_desk):
            return {}
        payload = json.loads(body)
        raw = payload["two_tier"]
        origin = payload["em_stress"]
        if type(raw) is not dict or type(origin) is not dict:
            return {}
        built = _clock(raw["built"])
        origin_built = _clock(origin["built"])
        if not origin_built <= built <= _clock(payload["built"]):
            return {}
        if origin["state"] != raw["tier1"]["em_stress_state"]:
            return {}
        if origin["state"] not in {"calm", "strained", "stressed"}:
            return {}
        available = origin["n_legs_available"]
        minimum = origin["k_of_n_params"]["min_legs_for_state"]
        if (type(available) is not int or type(minimum) is not int
                or minimum != 3 or available < minimum
                or available != len(origin["legs"])
                or type(origin["n_legs_total"]) is not int or origin["n_legs_total"] != 6
                or available > origin["n_legs_total"]):
            return {}
        if not set(origin["legs"]) <= set(_ORIGIN_LEGS):
            return {}
        origin_at = _observation(origin["as_of"], origin_built)
        # The producer's as_of is its newest contributing leg, not a common
        # release/availability clock; preserve and check the individual dates.
        origin_dates = [_observation(leg["asof"], origin_built) for leg in origin["legs"].values()]
        if origin_at != max(origin_dates):
            return {}
        observations = raw["publication_inputs"]
        if type(observations) is not dict or set(observations) != set(_SOURCES):
            return {}
        artifact = "sha256:" + publication.artifact_sha256
        leg_receipts = {}
        for key, sources in _SOURCES.items():
            observation = observations[key]
            if type(observation) is not dict or observation["calculation_available"] is not True:
                return {}
            observed = _observation(observation["observation_at"], built)
            inputs = observation["inputs"]
            if type(inputs) is not list or len(inputs) != len(sources):
                return {}
            for item, source in zip(inputs, sources):
                if type(item) is not dict or item["source_reference"] != source:
                    return {}
                _observation(item["observation_at"], built)
                digest = item["calculation_input_sha256"]
                if type(digest) is not str or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
                    return {}
            reference = artifact + "#/two_tier/tier2/legs/" + key + "/hot"
            source = artifact + "#/two_tier/publication_inputs/" + key
            leg_receipts[key] = _receipt(raw["tier2"]["legs"][key]["hot"], reference, observed, source)
        support = {
            "quality": "qualified", "metadata": "allowed", "value_permission": "allowed",
            "owner_ref": "scripts/build_intl.py",
            "method_ref": _POLICY_REF,
            "source_reference": artifact + "#/two_tier", "asof": raw["built"],
            "origin": _receipt(origin["state"], artifact + "#/em_stress", origin_at),
            "legs": leg_receipts, "diagnostic_permission": "allowed",
        }
        # Reuse the incumbent state, exact-boolean and four-leg consistency
        # validator; this adapter never calculates or repairs a market state.
        if qualify_us_transmission(two_tier=raw, eligibility=support)["quality"] != "qualified":
            return {}
        return support
    except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError):
        return {}

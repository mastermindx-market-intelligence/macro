"""Qualify a US transmission statement without exposing unsupported raw data."""


_STATES = frozenset(("quiet", "contained", "watching", "transmitting"))
_ORIGIN_STATES = frozenset(("calm", "strained", "stressed"))
_LEG_KEYS = (
    "us_hy_oas_vel",
    "kre_spy_rs",
    "move_pctile",
    "sofr_iorb_corridor",
)
_LEG_KEY_SET = frozenset(_LEG_KEYS)
_OPTIONAL_RAW_LEG = "safety_bid_flag"
_ELIGIBILITY_KEYS = frozenset(
    (
        "quality",
        "metadata",
        "value_permission",
        "owner_ref",
        "method_ref",
        "source_reference",
        "asof",
        "origin",
        "legs",
        "diagnostic_permission",
    )
)
_RECEIPT_KEYS = frozenset(
    (
        "quality",
        "metadata",
        "value_permission",
        "reported_value",
        "evidence_key",
        "source_reference",
        "observation_at",
    )
)


def _unknown(reason_code, diagnostic=None):
    return {
        "quality": "unknown",
        "state": None,
        "reason_codes": [reason_code],
        "evidence_refs": [],
        "diagnostic": _detach_diagnostic(diagnostic),
    }


def _detach_diagnostic(diagnostic):
    if diagnostic is None:
        return None
    return {"reported_state": diagnostic["reported_state"]}


def _plain(value, kind):
    return type(value) is kind


def _plain_dict(value):
    return _plain(value, dict)


def _plain_string(value):
    return _plain(value, str) and bool(value)


def _plain_str_keys(value):
    for key in value:
        if type(key) is not str:
            return False
    return True


def _is_int(value):
    return _plain(value, int)


def _is_bool(value):
    return _plain(value, bool)


def _allowed(value):
    return _plain_string(value) and value == "allowed"


def _parse_datetime(value):
    from datetime import datetime

    if not _plain_string(value):
        return False
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return False
    return parsed.tzinfo is not None


def _parse_observation(value):
    if not _plain_string(value):
        return False
    if _parse_datetime(value):
        return True
    from datetime import date

    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _exact_keys(value, keys):
    if not _plain_dict(value) or not _plain_str_keys(value):
        return False
    if len(value) != len(keys):
        return False
    for key in keys:
        if key not in value:
            return False
    return True


def _raw_legs_allowed(value):
    if not _plain_dict(value) or not _plain_str_keys(value):
        return False
    required = 0
    for key in value:
        if key in _LEG_KEY_SET:
            required += 1
        elif key != _OPTIONAL_RAW_LEG:
            return False
    return required == len(_LEG_KEYS)


def _receipt(value, expected_value):
    if not _exact_keys(value, _RECEIPT_KEYS):
        return False
    if not _plain_string(value["quality"]) or not _plain_string(value["metadata"]):
        return False
    if value["quality"] != "qualified" or value["metadata"] != "allowed" or not _allowed(value["value_permission"]):
        return False
    if not _plain_string(value["evidence_key"]) or not _plain_string(value["source_reference"]):
        return False
    if not _parse_observation(value["observation_at"]):
        return False
    reported = value["reported_value"]
    if _is_bool(expected_value):
        return _is_bool(reported) and reported is expected_value
    return _plain_string(reported) and reported == expected_value


def _permitted_diagnostic(two_tier, eligibility):
    quality = eligibility.get("quality")
    metadata = eligibility.get("metadata")
    diagnostic_permission = eligibility.get("diagnostic_permission")
    if not _plain_string(quality) or not _plain_string(metadata) or not _plain_string(diagnostic_permission):
        return None
    if quality != "qualified" or metadata != "allowed" or diagnostic_permission != "allowed":
        return None
    raw_state = two_tier.get("state")
    if not _plain_string(raw_state) or raw_state not in _STATES:
        return None
    return {"reported_state": raw_state}


def qualify_us_transmission(*, two_tier, eligibility):
    """Return a detached, permission-safe transmission qualification summary."""
    if not _plain_dict(two_tier) or not _plain_dict(eligibility):
        return _unknown("input_unavailable")
    if not _plain_str_keys(two_tier):
        return _unknown("input_unavailable")
    if not _plain_str_keys(eligibility):
        return _unknown("support_unavailable")

    diagnostic = _permitted_diagnostic(two_tier, eligibility)

    if not _exact_keys(eligibility, _ELIGIBILITY_KEYS):
        return _unknown("support_unavailable", diagnostic)

    permission_values = (
        eligibility["quality"],
        eligibility["metadata"],
        eligibility["value_permission"],
        eligibility["diagnostic_permission"],
    )
    if not all(_plain_string(value) for value in permission_values):
        return _unknown("support_unavailable", diagnostic)

    if eligibility["quality"] != "qualified" or eligibility["metadata"] != "allowed":
        return _unknown("support_denied", diagnostic)
    if not _allowed(eligibility["value_permission"]):
        return _unknown("support_denied", diagnostic)
    if not all(_plain_string(eligibility[key]) for key in ("owner_ref", "method_ref", "source_reference")):
        return _unknown("support_unavailable", diagnostic)
    if not _parse_datetime(eligibility["asof"]):
        return _unknown("support_unavailable", diagnostic)

    raw_built = two_tier.get("built")
    if not _parse_datetime(raw_built) or eligibility["asof"] != raw_built:
        return _unknown("support_unavailable", diagnostic)

    tier1 = two_tier.get("tier1")
    tier2 = two_tier.get("tier2")
    if not _plain_dict(tier1) or not _plain_dict(tier2):
        return _unknown("input_unavailable", diagnostic)
    if not _plain_str_keys(tier1) or not _plain_str_keys(tier2):
        return _unknown("input_unavailable", diagnostic)
    origin_raw = tier1.get("em_stress_state")
    if not _plain_string(origin_raw) or origin_raw not in _ORIGIN_STATES:
        return _unknown("input_unavailable", diagnostic)
    raw_legs = tier2.get("legs")
    if not _raw_legs_allowed(raw_legs):
        return _unknown("input_unavailable", diagnostic)
    raw_count = tier2.get("hot_count")
    if not _is_int(raw_count) or not 0 <= raw_count <= 4:
        return _unknown("input_unavailable", diagnostic)

    hot_values = []
    for key in _LEG_KEYS:
        raw_leg = raw_legs.get(key)
        if not _plain_dict(raw_leg) or not _plain_str_keys(raw_leg):
            return _unknown("input_unavailable", diagnostic)
        hot = raw_leg.get("hot")
        if not _is_bool(hot):
            return _unknown("input_unavailable", diagnostic)
        hot_values.append(hot)
    if raw_count != sum(hot_values):
        return _unknown("input_unavailable", diagnostic)

    raw_state = two_tier.get("state")
    if not _plain_string(raw_state) or raw_state not in _STATES:
        return _unknown("input_unavailable", diagnostic)
    if origin_raw == "calm":
        expected_state = "quiet"
    else:
        hot_count = sum(hot_values)
        if hot_count == 0:
            expected_state = "contained"
        elif hot_count == 1:
            expected_state = "watching"
        else:
            expected_state = "transmitting"
    if raw_state != expected_state:
        return _unknown("state_inconsistent", diagnostic)

    origin = eligibility.get("origin")
    if not _receipt(origin, origin_raw):
        return _unknown("support_unavailable", diagnostic)

    legs = eligibility.get("legs")
    if not _exact_keys(legs, _LEG_KEY_SET):
        return _unknown("support_unavailable", diagnostic)
    origin_receipt = eligibility["origin"]
    evidence_refs = [
        eligibility["source_reference"],
        origin_receipt["evidence_key"],
        origin_receipt["source_reference"],
    ]
    for key, hot_value in zip(_LEG_KEYS, hot_values):
        leg_receipt = legs.get(key)
        if not _receipt(leg_receipt, hot_value):
            return _unknown("support_unavailable", diagnostic)
        evidence_refs.append(leg_receipt["evidence_key"])
        evidence_refs.append(leg_receipt["source_reference"])

    return {
        "quality": "qualified",
        "state": raw_state,
        "reason_codes": [],
        "evidence_refs": list(dict.fromkeys(evidence_refs)),
        "diagnostic": _detach_diagnostic(diagnostic),
    }





# Exact native inputs for the incumbent derived summary, not a provider grant.
_NATIVE_RISK_SOURCES = {
    "us_hy_oas_vel": ("data/fred/BAMLH0A0HYM2.parquet",),
    "kre_spy_rs": ("data/yahoo/KRE.parquet", "data/yahoo/SPY.parquet"),
    "move_pctile": ("data/yahoo/_MOVE.parquet",),
    "sofr_iorb_corridor": ("data/fred/SOFR.parquet", "data/fred/IORB.parquet"),
}
_NATIVE_ORIGIN_LEGS = ("em_hy_oas", "vxeem", "em_fx_basket", "em_equity_breadth",
                       "em_dollar_vel", "emb_ief")


def _risk_snapshot_bytes(payload):
    import json
    return json.dumps(payload, indent=2, default=str, ensure_ascii=False).encode("utf-8")


def _native_clock(value):
    from datetime import datetime
    if type(value) is not str:
        raise ValueError("missing native calculation clock")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError("unqualified native calculation clock")
    return result


def _native_observation(value, built):
    from datetime import date
    if type(value) is not str:
        raise ValueError("missing native observation clock")
    result = date.fromisoformat(value)
    if result > built.date():
        raise ValueError("observation after native calculation")
    return value

def risk_summary_observations(*, risk_desk, support):
    """Detach public clock captions from the same byte-bound summary evidence.

    This confers no state/permission. Legacy or unbound support cannot borrow
    dates from a nearby raw packet. Source observation dates are not PIT,
    acquisition, release or independently certified market-freshness clocks.
    """
    from hashlib import sha256
    try:
        if qualify_us_transmission(two_tier=risk_desk["two_tier"], eligibility=support)["quality"] != "qualified":
            return None
        artifact = "sha256:" + sha256(_risk_snapshot_bytes(risk_desk)).hexdigest()
        if support["source_reference"] != artifact + "#/two_tier":
            return None
        raw, origin = risk_desk["two_tier"], risk_desk["em_stress"]
        built = _native_clock(raw["built"])
        origin_inputs = []
        for key in _NATIVE_ORIGIN_LEGS:
            leg = origin["legs"].get(key)
            observed = None if leg is None else _native_observation(leg["asof"], built)
            origin_inputs.append({"key": key, "observation_at": observed})
        legs = []
        for key, sources in _NATIVE_RISK_SOURCES.items():
            observed = raw["publication_inputs"][key]
            if (support["legs"][key]["source_reference"] !=
                    artifact + "#/two_tier/publication_inputs/" + key):
                return None
            inputs = []
            for item, source in zip(observed["inputs"], sources):
                if item["source_reference"] != source:
                    return None
                inputs.append({"key": source.rsplit("/", 1)[-1].removesuffix(".parquet"),
                               "observation_at": _native_observation(item["observation_at"], built)})
            legs.append({"key": key, "observation_at": _native_observation(observed["observation_at"], built),
                         "inputs": inputs})
        return {"calculation_at": raw["built"], "origin_calculation_at": origin["built"],
                "origin_observation_at": _native_observation(origin["as_of"], built),
                "origin_coverage": {"available": origin["n_legs_available"], "total": origin["n_legs_total"]},
                "origin_inputs": origin_inputs, "legs": legs,
                "freshness": "not_established"}
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
        return None


__all__ = ["qualify_us_transmission", "risk_summary_observations"]

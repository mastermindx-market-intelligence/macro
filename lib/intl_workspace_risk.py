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


__all__ = ["qualify_us_transmission"]

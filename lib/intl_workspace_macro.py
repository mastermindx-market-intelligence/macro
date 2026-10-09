"""Pure, supplied-field macro workspace projection."""

import math
import re
from datetime import datetime
from fractions import Fraction


_FIELDS = (
    "gdp_yoy",
    "cpi_yoy",
    "policy_rate",
    "policy_proxy",
    "yield_10y",
    "yield_change",
)
_MEASURE_KEYS = {
    "quality", "reason", "metadata", "value_permission", "value", "unit",
    "instrument", "period", "observation_at", "calculation_at",
    "source_reference", "evidence_key",
}
_QUALITIES = {"qualified", "stale", "missing", "denied", "failed", "unsupported", "unknown"}
_PERMISSIONS = {"allowed", "unknown", "denied"}
_REASONS = {
    None, "not_supplied", "source_unknown", "disclosure_unknown", "metadata_denied",
    "value_denied", "source_stale", "source_failed", "method_unsupported",
    "instrument_mismatch", "cycle_support_missing", "component_disagreement",
}
_UNITS = {
    "gdp_yoy": {"percent"}, "cpi_yoy": {"percent"}, "policy_rate": {"percent"},
    "policy_proxy": {"percent"}, "yield_10y": {"percent"}, "yield_change": {"bp", "pp"},
}
_INSTRUMENT_KINDS = {
    "gdp_yoy": {"macro_yoy"}, "cpi_yoy": {"macro_yoy"},
    "policy_rate": {"official_policy"}, "policy_proxy": {"effective_rate", "policy_proxy"},
    "yield_10y": {"sovereign_10y"}, "yield_change": {"yield_change"},
}
_COUNT_BASES = {"observations", "sessions", "release_periods"}
_QUADS = {"Q1", "Q2", "Q3", "Q4"}
_HEADINGS = {"Q1": "goldilocks", "Q2": "reflation", "Q3": "stagflation", "Q4": "growth_scare"}
_SUPPORT_KEYS = {
    "owner_ref", "decision_ref", "method_ref", "asof", "dependency_keys",
    "component_keys", "heading_key", "disagreement",
}
_CYCLE_KEYS = {
    "quality", "reason", "metadata", "value_permission", "reported_quad", "raw_quad",
    "method_ref", "method_kind", "asof", "components", "economic_support",
}
_READ_KEYS = ("economic_cycle", "realized_policy", "market_response")
_DATE_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_MONTH_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}")
_TIMESTAMP_PATTERN = re.compile(
    r"(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})[T ]"
    r"(?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):(?P<second>[0-9]{2})"
    r"(?:[.,](?P<fraction>[0-9]+))?"
    r"(?P<zone>Z|[+-][0-9]{2}:[0-9]{2})?"
)
_GROWTH_GEOMETRY = (
    ("gdp_trend", 1.0),
    ("unemployment_trend", 1.0),
    ("index_trend", 1.0),
    ("global_growth", 0.5),
)
_INFLATION_GEOMETRY = (
    ("cpi_direction", 1.5),
    ("oil_trend", 0.75),
    ("yield_trend", 0.75),
)


def _exact(value, keys, label):
    if type(value) is not dict or any(type(key) is not str for key in value) or set(value) != set(keys):
        raise ValueError(f"invalid {label} shape")


def _text(value, label, nullable=True):
    if value is None and nullable:
        return None
    if type(value) is not str or not value or value.strip() != value:
        raise ValueError(f"invalid {label}")
    return value


def _enum(value, allowed, label, nullable=False):
    if nullable and value is None:
        return None
    if value is None and None in allowed:
        return None
    if type(value) is not str or value not in allowed:
        raise ValueError(f"invalid {label}")
    return value


def _date(value, month_allowed=False):
    if value is None:
        return None
    if type(value) is not str or _parse_date(value, month_allowed) is None:
        raise ValueError("invalid date")
    return value


def _utc_offset(value):
    if len(value) != 6 or value[0] not in "+-" or value[3] != ":":
        return False
    hours, minutes = value[1:3], value[4:6]
    return hours.isdigit() and minutes.isdigit() and int(hours) <= 23 and int(minutes) <= 59


def _parse_date(value, month_allowed):
    if type(value) is not str:
        return None
    if _MONTH_PATTERN.fullmatch(value):
        if not month_allowed:
            return None
        year, month = int(value[:4]), int(value[5:7])
        if year < 1 or not 1 <= month <= 12:
            return None
        return (value, "month", "", Fraction(0), Fraction(0))
    if _DATE_PATTERN.fullmatch(value):
        year, month, day = int(value[:4]), int(value[5:7]), int(value[8:10])
        seconds = _utc_seconds(year, month, day, 0, 0, 0)
        return (value, "day", "", seconds, Fraction(0))
    match = _TIMESTAMP_PATTERN.fullmatch(value)
    if match is None:
        return None
    parts = match.groupdict()
    seconds = _utc_seconds(
        int(parts["date"][:4]), int(parts["date"][5:7]), int(parts["date"][8:10]),
        int(parts["hour"]), int(parts["minute"]), int(parts["second"] or 0),
    )
    digits = parts["fraction"] or ""
    fraction = Fraction(int(digits), 10 ** len(digits)) if digits else Fraction(0)
    zone = parts["zone"] or ""
    offset = Fraction(0)
    if zone not in {"", "Z"}:
        if not _utc_offset(zone):
            raise ValueError("invalid timezone offset")
        offset = Fraction(int(zone[1:3]) * 3600 + int(zone[4:6]) * 60)
        if zone[0] == "-":
            offset = -offset
    return (value, "timestamp", zone, seconds - offset, fraction)


def _utc_seconds(year, month, day, hour, minute, second):
    try:
        moment = datetime(year, month, day, hour, minute, second)
    except ValueError as error:
        raise ValueError("invalid date") from error
    return moment.toordinal() * 86400 + hour * 3600 + minute * 60 + second


def _precision(value):
    parsed = _parse_date(value, True)
    return None if parsed is None else parsed[1:3]


def _canonical_zone(value):
    return "UTC" if value in {"Z", "+00:00", "-00:00"} else value


def _compatible_zone(left, right):
    # Compare aware instants in UTC without assigning a zone to naive inputs.
    return bool(left) == bool(right)


def _instant(value):
    parsed = _parse_date(value, True)
    if parsed is None:
        raise ValueError("invalid date")
    if parsed[1] == "month":
        return int(parsed[0][:4]) * 12 + int(parsed[0][5:7]), parsed[4]
    return parsed[3], parsed[4]


def _period(value):
    if value is None:
        return None
    _exact(value, {"start", "end", "count", "count_basis"}, "period")
    start = _date(value["start"], month_allowed=True)
    end = _date(value["end"], month_allowed=True)
    if start is None or end is None:
        raise ValueError("invalid period interval")
    start_precision, start_zone = _precision(start)
    end_precision, end_zone = _precision(end)
    if (
        start_precision != end_precision
        or not _compatible_zone(start_zone, end_zone) or _instant(start) >= _instant(end)
    ):
        raise ValueError("invalid period interval")
    count = value["count"]
    if type(count) is not int or count <= 0:
        raise ValueError("invalid period count")
    _enum(value["count_basis"], _COUNT_BASES, "count_basis")
    return {"start": start, "end": end, "count": count, "count_basis": value["count_basis"]}


def _instrument(value, field, market_id):
    if value is None:
        return None
    _exact(value, {"kind", "id", "market_id"}, "instrument")
    kind = _enum(value["kind"], _INSTRUMENT_KINDS[field], f"{field} instrument kind")
    identifier = _text(value["id"], "instrument id", nullable=False)
    market = _text(value["market_id"], "instrument market_id", nullable=False)
    if market != market_id:
        raise ValueError("instrument market mismatch")
    if field == "policy_rate":
        if identifier == "deposit_facility" and market != "EZ":
            raise ValueError("deposit_facility is EZ only")
        if identifier == "DFF":
            raise ValueError("DFF is not official policy")
        if identifier in {"short_3m", "IR3", "IRST"}:
            raise ValueError("proxy cannot be official policy")
    if field == "policy_proxy" and kind == "official_policy":
        raise ValueError("proxy field cannot contain official policy")
    if field == "yield_10y" and (identifier == "ez_aaa_10y" or market == "DE"):
        raise ValueError("unsupported curve proxy")
    return {"kind": kind, "id": identifier, "market_id": market}


def _optional_score(value):
    if value is None:
        return None
    if type(value) not in {int, float}:
        raise ValueError("component score must be numeric or null")
    return value if type(value) is int or math.isfinite(value) else None


def _measure(key, market_id, configured):
    field = key[len(market_id) + 1 :]
    value = configured.get(key)
    if value is None:
        return {"field": field, "quality": "unknown", "reason": "not_supplied"}, None
    _exact(value, _MEASURE_KEYS, "measure")
    quality = _enum(value["quality"], _QUALITIES, "measure quality")
    reason = _enum(value["reason"], _REASONS, "measure reason")
    metadata = _enum(value["metadata"], _PERMISSIONS, "metadata permission")
    value_permission = _enum(value["value_permission"], _PERMISSIONS, "value permission")
    numeric = value["value"]
    instrument = _instrument(value["instrument"], field, market_id)
    period = _period(value["period"])
    observation = _date(value["observation_at"])
    calculation = _date(value["calculation_at"])
    source = _text(value["source_reference"], "source_reference")
    evidence = _text(value["evidence_key"], "evidence_key")
    unit = _enum(value["unit"], _UNITS[field], f"{field} unit", nullable=True)
    if numeric is not None and (type(numeric) not in {int, float} or
                                (type(numeric) is float and not math.isfinite(numeric))):
        raise ValueError("value must be finite builtin numeric or null")
    if quality == "qualified":
        if metadata != "allowed" or value_permission != "allowed":
            raise ValueError("qualified permission mismatch")
        if type(numeric) not in {int, float} or (type(numeric) is float and not math.isfinite(numeric)):
            raise ValueError("qualified value must be finite builtin numeric")
        if unit is None or instrument is None or observation is None or source is None or evidence is None:
            raise ValueError("qualified evidence is incomplete")
    if field == "yield_change" and quality in {"qualified", "stale"} and numeric is not None and period is None:
        raise ValueError("yield change requires its actual interval")
    if metadata == "allowed":
        output = {
            "field": field, "quality": quality, "reason": reason, "unit": unit,
            "instrument": instrument, "period": period, "observation_at": observation,
            "calculation_at": calculation, "source_reference": source,
            "evidence_key": evidence, "value": numeric if value_permission == "allowed" and quality in {"qualified", "stale"} else None,
        }
    else:
        output = {"field": field, "quality": quality, "reason": reason}
    return output, value


def _registry(value):
    _exact(value, {"markets", "horizons", "bases"}, "registry")
    if type(value["markets"]) is not list or type(value["horizons"]) is not list or type(value["bases"]) is not list:
        raise ValueError("invalid registry containers")
    markets, ids = [], []
    for market in value["markets"]:
        _exact(market, {"market_id", "name_en", "name_zh"}, "market registry entry")
        market_id = _text(market["market_id"], "market_id", nullable=False)
        markets.append({
            "market_id": market_id,
            "name_en": _text(market["name_en"], "name_en", nullable=False),
            "name_zh": _text(market["name_zh"], "name_zh", nullable=False),
        })
        ids.append(market_id)
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("duplicate or empty market population")
    if any(type(item) is not str or not item for item in value["horizons"] + value["bases"]):
        raise ValueError("invalid registry basis")
    return markets, set(value["horizons"]), set(value["bases"])


def _destination(value):
    _exact(value, {"key", "title_en", "title_zh", "destination"}, "destination")
    key = _text(value["key"], "destination key", nullable=False)
    _text(value["title_en"], "destination English title", nullable=False)
    _text(value["title_zh"], "destination Chinese title", nullable=False)
    destination = value["destination"]
    if destination is not None:
        if type(destination) is not str or not destination or any(
            ord(char) <= 0x1F or 0x7F <= ord(char) <= 0x9F for char in destination
        ):
            raise ValueError("unsafe destination")
        if destination.startswith("#"):
            if (
                len(destination) == 1 or "\\" in destination or "%" in destination
                or any(not char.isalnum() and char not in "-_.!$&'()*+,;=:@~" for char in destination[1:])
            ):
                raise ValueError("unsafe destination")
        elif not destination.startswith("/") or destination.startswith("//"):
            raise ValueError("non-local destination")
        elif "\\" in destination or "%" in destination or any(
            part in {"", ".", ".."} for part in destination.split("/")[1:]
        ):
            raise ValueError("unsafe destination")
    return key


def _components(value):
    if value is None:
        return None
    _exact(value, {
        "asof", "growth", "inflation", "growth_score", "inflation_score",
        "growth_n_components", "inflation_n_components",
    }, "components")
    asof = _date(value["asof"])
    if asof is None:
        raise ValueError("component asof required")
    result = {"asof": asof, "growth": [], "inflation": []}
    for axis in ("growth", "inflation"):
        if type(value[axis]) is not list:
            raise ValueError("component axis must be list")
        keys = []
        for component in value[axis]:
            _exact(component, {"key", "score", "weight"}, "component")
            component_key = _text(component["key"], "component key", nullable=False)
            if component_key in keys:
                raise ValueError("duplicate component key")
            keys.append(component_key)
            result[axis].append({
                "key": component_key,
                "score": _optional_score(component["score"]),
                "weight": _optional_score(component["weight"]),
            })
        count = value[f"{axis}_n_components"]
        if count is not None and (type(count) is not int or count < 0):
            raise ValueError("component count")
        result[f"{axis}_score"] = _optional_score(value[f"{axis}_score"])
        result[f"{axis}_n_components"] = count
    return result


def _native_component_geometry(value):
    geometry_by_axis = {"growth": _GROWTH_GEOMETRY, "inflation": _INFLATION_GEOMETRY}
    for axis, geometry in geometry_by_axis.items():
        components = value[axis]
        if len(components) != len(geometry):
            return False
        for component, (key, weight) in zip(components, geometry):
            if (
                component["key"] != key
                or type(component["weight"]) not in {int, float}
                or component["weight"] != weight
            ):
                return False
    return True


def _heading_reason(cycle, market_id, admitted_measures):
    if cycle["quality"] != "qualified" or cycle["metadata"] != "allowed" or cycle["value_permission"] != "allowed":
        return cycle["reason"] or "cycle_support_missing"
    if cycle["method_kind"] != "economic_cycle" or cycle["economic_support"] is None:
        return "method_unsupported"
    support = cycle["economic_support"]
    if support["disagreement"] or cycle["reported_quad"] != cycle["raw_quad"] or cycle["raw_quad"] is None:
        return "component_disagreement"
    if support["method_ref"] != cycle["method_ref"] or support["asof"] != cycle["asof"]:
        return "cycle_support_missing"
    if cycle["components"]["asof"] != cycle["asof"] or support["asof"] != cycle["asof"]:
        return "cycle_support_missing"
    if _HEADINGS[cycle["reported_quad"]] != support["heading_key"]:
        return "component_disagreement"
    if not support["component_keys"] or not _native_component_geometry(cycle["components"]):
        return "cycle_support_missing"
    available = {
        f"{axis}.{component['key']}": component["score"]
        for axis in ("growth", "inflation") for component in cycle["components"][axis]
    }
    if any(component_key not in available for component_key in support["component_keys"]):
        raise ValueError("component admission references unknown component")
    if any(available.get(component_key) is None for component_key in support["component_keys"]):
        raise ValueError("component admission references unknown or nonfinite component")
    dependencies = set(support["dependency_keys"])
    if not {f"{market_id}.gdp_yoy", f"{market_id}.cpi_yoy"}.issubset(dependencies):
        return "cycle_support_missing"
    for dependency in dependencies:
        measure = admitted_measures.get(dependency)
        if measure is None or measure["quality"] != "qualified":
            return "cycle_support_missing"
    return None


def _cycle(value, market_id):
    _exact(value, _CYCLE_KEYS, "cycle evidence")
    quality = _enum(value["quality"], _QUALITIES, "cycle quality")
    reason = _enum(value["reason"], _REASONS, "cycle reason")
    metadata = _enum(value["metadata"], _PERMISSIONS, "cycle metadata permission")
    value_permission = _enum(value["value_permission"], _PERMISSIONS, "cycle value permission")
    reported = _enum(value["reported_quad"], _QUADS, "reported_quad", nullable=True)
    raw = _enum(value["raw_quad"], _QUADS, "raw_quad", nullable=True)
    method_ref = _text(value["method_ref"], "method_ref")
    method_kind = _enum(value["method_kind"], {"mixed_composite", "economic_cycle"}, "method_kind")
    asof = _date(value["asof"])
    components = _components(value["components"])
    support = value["economic_support"]
    if support is not None:
        _exact(support, _SUPPORT_KEYS, "economic_support")
        for field in ("owner_ref", "decision_ref", "method_ref"):
            _text(support[field], field, nullable=False)
        support_asof = _date(support["asof"])
        if support_asof is None:
            raise ValueError("support asof required")
        if type(support["dependency_keys"]) is not list or type(support["component_keys"]) is not list:
            raise ValueError("support key lists")
        if any(type(item) is not str or not item for item in support["dependency_keys"] + support["component_keys"]):
            raise ValueError("support key")
        if len(support["dependency_keys"]) != len(set(support["dependency_keys"])) or len(support["component_keys"]) != len(set(support["component_keys"])):
            raise ValueError("duplicate support key")
        _enum(support["heading_key"], set(_HEADINGS.values()), "heading_key", nullable=False)
        if type(support["disagreement"]) is not bool:
            raise ValueError("support disagreement")
    if quality == "qualified":
        if metadata != "allowed" or value_permission != "allowed":
            raise ValueError("qualified cycle permission mismatch")
        if method_ref is None or asof is None or components is None:
            raise ValueError("qualified cycle evidence incomplete")
    return {
        "quality": quality, "reason": reason, "metadata": metadata,
        "value_permission": value_permission, "reported_quad": reported, "raw_quad": raw,
        "method_ref": method_ref, "method_kind": method_kind, "asof": asof,
        "components": components, "economic_support": support,
    }


def _read(reason):
    return {"title_key": reason, "destination": None, "reason": "target_unavailable"}


def _check_builtin_tree(value, ancestors=None):
    """Refuse custom containers/accessors before projecting a detached result."""
    if value is None or type(value) in {str, int, float, bool}:
        return
    if type(value) not in {dict, list}:
        raise ValueError("input must contain builtin JSON types")
    ancestors = set() if ancestors is None else ancestors
    identity = id(value)
    if identity in ancestors:
        raise ValueError("cyclic input")
    ancestors.add(identity)
    try:
        if type(value) is dict:
            if any(type(key) is not str for key in value):
                raise ValueError("input keys must be builtin strings")
            children = value.values()
        else:
            children = value
        for child in children:
            _check_builtin_tree(child, ancestors)
    finally:
        ancestors.remove(identity)


def build_macro_section(*, context, registry, measures, cycle_evidence, destinations):
    for value in (context, registry, measures, cycle_evidence, destinations):
        _check_builtin_tree(value)
    _exact(context, {"selected_market", "horizon", "currency_basis", "return_basis"}, "context")
    if type(measures) is not dict or type(cycle_evidence) is not dict or type(destinations) is not dict:
        raise ValueError("mapping containers must be builtin dict")
    markets, horizons, bases = _registry(registry)
    market_ids = [market["market_id"] for market in markets]
    selected = context["selected_market"]
    if selected is not None and (type(selected) is not str or selected not in market_ids):
        raise ValueError("unknown selected market")
    for name in ("horizon", "currency_basis", "return_basis"):
        _text(context[name], "context " + name, nullable=False)
    if (
        context["horizon"] not in horizons
        or context["currency_basis"] not in bases
        or context["return_basis"] != "price"
    ):
        raise ValueError("unknown context basis")
    if not set(measures).issubset({f"{market_id}.{field}" for market_id in market_ids for field in _FIELDS}):
        raise ValueError("unknown measure key")
    if not set(cycle_evidence).issubset(set(market_ids)):
        raise ValueError("unknown cycle market")
    destination_by_key = {}
    if any(type(key) is not str for key in destinations):
        raise ValueError("destination key")
    for map_key, entry in destinations.items():
        if type(entry) is not dict:
            raise ValueError("destination entry")
        key = _destination(entry)
        if key != map_key:
            raise ValueError("destination entry does not match catalogue key")
        destination_by_key[key] = entry
    market_rows, cycle_rows, classified, unclassified, admitted_measures = [], [], [], [], {}
    selected_cycle_seen = False
    selected_cycle_reason = None
    selected_cycle_heading = None
    for market_id in market_ids:
        row = {"market_id": market_id}
        for field in _FIELDS:
            key = f"{market_id}.{field}"
            projected, supplied = _measure(key, market_id, measures)
            row[field] = projected
            if supplied is not None:
                admitted_measures[key] = supplied
        market_rows.append(row)
    # Registry display order cannot change eligibility of supplied dependencies.
    for market_id in market_ids:
        if market_id not in cycle_evidence:
            unclassified.append({"market_id": market_id, "reason": "not_supplied"})
            continue
        cycle = _cycle(cycle_evidence[market_id], market_id)
        reason = _heading_reason(cycle, market_id, admitted_measures)
        if market_id == selected:
            selected_cycle_seen = True
            selected_cycle_reason = reason
        if reason is None:
            heading = cycle["economic_support"]["heading_key"]
            classified.append(market_id)
        else:
            heading = None
            unclassified.append({"market_id": market_id, "reason": reason})
        if market_id == selected:
            selected_cycle_heading = heading
        if (
            cycle["quality"] in {"qualified", "stale"}
            and cycle["metadata"] == "allowed"
            and cycle["value_permission"] == "allowed"
        ):
            cycle_rows.append({
                "market_id": market_id, "reported_quad": cycle["reported_quad"],
                "reported_method_ref": cycle["method_ref"], "method_kind": cycle["method_kind"],
                "presentation_quality": cycle["quality"],
                "supported_heading": heading, "components": cycle["components"],
            })

    reads = {
        "economic_cycle": _read("economic_cycle"),
        "realized_policy": _read("realized_policy"),
        "market_response": {"title_key": "market_response", "destination": None, "reason": "method_unsupported"},
    }
    if selected is not None:
        selected_cycle = cycle_evidence.get(selected)
        if selected_cycle_seen:
            if selected_cycle_reason is None:
                destination = destination_by_key.get("economic_cycle", {}).get("destination")
                reads["economic_cycle"] = {
                    "title_key": selected_cycle_heading,
                    "destination": destination,
                    "reason": None if destination is not None else "target_unavailable",
                }
            else:
                reads["economic_cycle"] = {
                    "title_key": selected_cycle_reason,
                    "destination": None,
                    "reason": selected_cycle_reason,
                }
        policy = admitted_measures.get(f"{selected}.policy_rate")
        proxy = admitted_measures.get(f"{selected}.policy_proxy")
        selected_policy = policy if policy is not None and policy["quality"] == "qualified" else proxy
        if selected_policy is not None and selected_policy["quality"] == "qualified":
            reads["realized_policy"] = {
                "title_key": selected_policy["instrument"]["id"],
                "destination": destination_by_key.get("realized_policy", {}).get("destination"),
                "reason": (
                    None
                    if destination_by_key.get("realized_policy", {}).get("destination") is not None
                    else "target_unavailable"
                ),
            }

    deep_research = [{
        "key": entry["key"], "title": {"en": entry["title_en"], "zh": entry["title_zh"]},
        "destination": entry["destination"],
        "capability_reason": None if entry["destination"] is not None else "target_unavailable",
    } for entry in destinations.values()]
    return {
        "selected_market": selected,
        "coverage": {"configured_ids": market_ids, "classified_ids": classified, "unclassified": unclassified},
        "cycle_rows": cycle_rows, "market_rows": market_rows, "selected_reads": reads,
        "deep_research": deep_research,
    }

"""Pure projection for the international library catalogue."""

import math


_BINDINGS_SCHEMA = "handoff.intl_tool_bindings.v1"
_TOOL_COUNT = 18
_GROUP_COUNT = 6
_METRIC_UNITS = frozenset(
    {"percent", "percentage_points", "basis_points", "index_level", "count", "ratio"}
)
_METRIC_INTERPRETATIONS = frozenset(
    {"observed", "proxy", "model_estimate", "descriptive_composite"}
)
_METRIC_QUALITIES = frozenset(
    {"qualified", "stale", "missing", "denied", "failed", "unsupported", "unknown"}
)
_FAMILY_STATES = frozenset({"supported", "partial", "not_applicable", "missing", "stale", "denied", "failed", "unknown"})
_QUALIFICATIONS = frozenset({"allowed", "denied", "unknown"})
_CONTEXT_KEYS = frozenset(
    {
        "research_market",
        "market_ids",
        "horizon",
        "horizons",
        "currency_basis",
        "return_basis",
        "source_reference",
    }
)
_WORKSPACE_KEYS = frozenset(
    {"source_reference", "catalogue_generation", "families"}
)
_FAMILY_KEYS = frozenset(
    {
        "metadata",
        "values",
        "data_state",
        "owner_ref",
        "decision_ref",
        "source_reference",
        "metrics",
    }
)
_METRIC_KEYS = frozenset({"key", "value", "unit", "interpretation", "quality"})
_TARGET_KEYS = frozenset({"page_id", "route", "region_id", "verified"})


def _is_string(value):
    return isinstance(value, str)


def _is_nonempty_string(value):
    return isinstance(value, str) and bool(value)


def _is_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, int):
        return True
    return math.isfinite(value)


def _is_unique_string_list(value):
    return (
        isinstance(value, list)
        and all(_is_string(item) for item in value)
        and len(set(value)) == len(value)
    )


def _exact_keys(value, keys, error):
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(error)


def _enum(value, choices):
    return _is_string(value) and value in choices


def _validated_bindings(route_bindings):
    _exact_keys(route_bindings, {"bindings", "targets"}, "invalid_bindings:route_table")
    bindings = route_bindings["bindings"]
    if not isinstance(bindings, dict) or bindings.get("schema") != _BINDINGS_SCHEMA:
        raise ValueError("invalid_bindings:schema")
    groups = bindings.get("groups")
    tools = bindings.get("tools")
    if not isinstance(groups, list) or len(groups) != _GROUP_COUNT:
        raise ValueError("invalid_bindings:groups")
    if not isinstance(tools, list) or len(tools) != _TOOL_COUNT:
        raise ValueError("invalid_bindings:tools")

    group_ids = []
    group_labels = {}
    for slot, group in enumerate(groups):
        if not isinstance(group, dict):
            raise ValueError("invalid_bindings:group")
        for field in ("id", "label_en", "label_zh"):
            if not _is_string(group.get(field)):
                raise ValueError(f"invalid_bindings:group_{field}")
        group_id = group["id"]
        if not group_id or group_id in group_labels:
            raise ValueError("invalid_bindings:group_id")
        group_ids.append(group_id)
        group_labels[group_id] = (group["label_en"], group["label_zh"])

    ordered_tools = []
    tool_keys = set()
    tool_group_counts = {group_id: 0 for group_id in group_ids}
    tool_by_key = {}
    for binding in tools:
        if not isinstance(binding, dict):
            raise ValueError("invalid_bindings:tool")
        required = {
            "presentation_key",
            "group_id",
            "order",
            "label_en",
            "label_zh",
            "question_en",
            "question_zh",
            "aliases",
            "analytical_scope",
            "page_id",
            "existing_route",
        }
        if not required.issubset(binding):
            raise ValueError("invalid_bindings:tool_fields")
        key = binding["presentation_key"]
        order = binding["order"]
        group_id = binding["group_id"]
        if not _is_nonempty_string(key) or key in tool_keys:
            raise ValueError("invalid_bindings:tool_key")
        if not isinstance(order, int) or isinstance(order, bool) or not 0 <= order < _TOOL_COUNT:
            raise ValueError("invalid_bindings:tool_order")
        if not _is_nonempty_string(group_id) or group_id not in tool_group_counts:
            raise ValueError("invalid_bindings:tool_group")
        for field in ("label_en", "label_zh", "question_en", "question_zh", "analytical_scope"):
            if not _is_string(binding[field]):
                raise ValueError(f"invalid_bindings:tool_{field}")
            if field != "analytical_scope" and not binding[field]:
                raise ValueError(f"invalid_bindings:tool_{field}")
        if not isinstance(binding["aliases"], list) or not all(
            _is_string(item) for item in binding["aliases"]
        ):
            raise ValueError("invalid_bindings:tool_aliases")
        if not _is_nonempty_string(binding["page_id"]) or not _is_nonempty_string(binding["existing_route"]):
            raise ValueError("invalid_bindings:tool_target")
        tool_keys.add(key)
        tool_group_counts[group_id] += 1
        tool_by_key[key] = binding
        ordered_tools.append(binding)
    if any(order != index for index, order in enumerate(sorted(item["order"] for item in ordered_tools))):
        raise ValueError("invalid_bindings:tool_order")
    ordered_tools.sort(key=lambda binding: binding["order"])
    if any(count != 3 for count in tool_group_counts.values()):
        raise ValueError("invalid_bindings:group_membership")

    targets = route_bindings["targets"]
    if not isinstance(targets, dict):
        raise ValueError("invalid_bindings:targets")
    region_states = {}
    for key, target in targets.items():
        if key not in tool_by_key:
            raise ValueError("invalid_target:unknown_key")
        _exact_keys(target, _TARGET_KEYS, "invalid_target:fields")
        binding = tool_by_key[key]
        expected_route = (
            "/intl_stocks.html"
            if binding["page_id"] == "macro:intl_stocks"
            else "/intl.html"
        )
        if (
            not _is_nonempty_string(binding["page_id"])
            or binding["page_id"] not in {"macro:intl", "macro:intl_stocks"}
            or binding["existing_route"] != expected_route
        ):
            raise ValueError("invalid_target:binding_pair")
        if target["page_id"] != binding["page_id"] or target["route"] != binding["existing_route"]:
            raise ValueError("invalid_target:binding_pair")
        if not isinstance(target["verified"], bool):
            raise ValueError("invalid_target:verified")
        region_id = target["region_id"]
        if region_id is not None:
            if not _is_string(region_id) or not region_id or len(region_id) > 128:
                raise ValueError("invalid_target:region")
            first = region_id[0]
            if not (("A" <= first <= "Z") or ("a" <= first <= "z")):
                raise ValueError("invalid_target:region")
            if any(not (character.isascii() and (character.isalnum() or character in "_-")) for character in region_id):
                raise ValueError("invalid_target:region")
        region_states[key] = target
    return group_ids, group_labels, ordered_tools, tool_by_key, targets


def _validated_context(context):
    _exact_keys(context, _CONTEXT_KEYS, "invalid_context:fields")
    if not _is_unique_string_list(context["market_ids"]):
        raise ValueError("invalid_context:market_ids")
    if not _is_unique_string_list(context["horizons"]):
        raise ValueError("invalid_context:horizons")
    research_market = context["research_market"]
    if research_market is not None and not _is_string(research_market):
        raise ValueError("invalid_context:research_market")
    if research_market is not None and research_market not in context["market_ids"]:
        raise ValueError("invalid_context:research_market")
    horizon = context["horizon"]
    if not _is_string(horizon) or horizon not in context["horizons"]:
        raise ValueError("invalid_context:horizon")
    if not _is_string(context["currency_basis"]) or context["currency_basis"] not in {"local", "usd_unhedged"}:
        raise ValueError("invalid_context:currency_basis")
    if not _is_string(context["return_basis"]) or context["return_basis"] != "price":
        raise ValueError("invalid_context:return_basis")
    source_reference = context["source_reference"]
    if source_reference is not None and not _is_string(source_reference):
        raise ValueError("invalid_context:source_reference")
    return context


def _validated_metrics(metrics):
    if not isinstance(metrics, list):
        raise ValueError("invalid_workspace:metrics")
    result = []
    for metric in metrics:
        _exact_keys(metric, _METRIC_KEYS, "invalid_workspace:metric_fields")
        if not _is_nonempty_string(metric["key"]):
            raise ValueError("invalid_workspace:metric_key")
        value = metric["value"]
        if value is not None and not _is_number(value):
            raise ValueError("invalid_workspace:metric_value")
        if not _enum(metric["unit"], _METRIC_UNITS):
            raise ValueError("invalid_workspace:metric_unit")
        if not _enum(metric["interpretation"], _METRIC_INTERPRETATIONS):
            raise ValueError("invalid_workspace:metric_interpretation")
        if not _enum(metric["quality"], _METRIC_QUALITIES):
            raise ValueError("invalid_workspace:metric_quality")
        result.append(metric)
    return result


def _validated_workspace(workspace, context, tool_keys):
    _exact_keys(workspace, _WORKSPACE_KEYS, "invalid_workspace:fields")
    if workspace["source_reference"] != context["source_reference"]:
        raise ValueError("invalid_workspace:source")
    generation = workspace["catalogue_generation"]
    if generation is not None and not _is_string(generation):
        raise ValueError("invalid_workspace:generation")
    families = workspace["families"]
    if not isinstance(families, dict) or not set(families).issubset(tool_keys):
        raise ValueError("invalid_workspace:family_keys")
    for family in families.values():
        _exact_keys(family, _FAMILY_KEYS, "invalid_workspace:family_fields")
        if not _enum(family["metadata"], _QUALIFICATIONS) or not _enum(family["values"], _QUALIFICATIONS):
            raise ValueError("invalid_workspace:qualification")
        if not _enum(family["data_state"], _FAMILY_STATES):
            raise ValueError("invalid_workspace:data_state")
        if not _is_nonempty_string(family["owner_ref"]) or not _is_nonempty_string(family["decision_ref"]):
            raise ValueError("invalid_workspace:refs")
        source = family["source_reference"]
        if source is not None and not _is_string(source):
            raise ValueError("invalid_workspace:family_source")
        _validated_metrics(family["metrics"])
    return workspace


def _target_for(key, tool, targets):
    target = targets.get(key)
    if target is None or not target["verified"]:
        return None, "missing_target"
    if key == "country_sectors_stocks" and target["region_id"] is None:
        return {"page_id": target["page_id"], "route": target["route"], "region_id": None}, None
    if target["region_id"] is None:
        return None, "missing_target"
    return {"page_id": target["page_id"], "route": target["route"], "region_id": target["region_id"]}, None


def _family_projection(tool, family, workspace, targets):
    key = tool["presentation_key"]
    if family is None:
        return {
            "route_state": "unavailable",
            "data_state": "unknown",
            "target": None,
            "reason": "missing_family",
            "metadata": "unknown",
            "publication": None,
        }
    if family["source_reference"] != workspace["source_reference"]:
        return {
            "route_state": "unavailable",
            "data_state": "unknown",
            "target": None,
            "reason": "binding_mismatch",
            "metadata": "unknown",
            "publication": None,
        }
    qualification = family["metadata"]
    if qualification != "allowed":
        reason = "metadata_denied" if qualification == "denied" else "metadata_unknown"
        return {
            "route_state": "unavailable",
            "data_state": qualification,
            "target": None,
            "reason": reason,
            "metadata": qualification,
            "publication": None,
        }
    if not family["owner_ref"] or not family["decision_ref"] or family["source_reference"] is None:
        return {
            "route_state": "unavailable",
            "data_state": "unknown",
            "target": None,
            "reason": "metadata_unknown",
            "metadata": "unknown",
            "publication": None,
        }
    target, target_reason = _target_for(key, tool, targets)
    return {
        "route_state": "available" if target is not None else "unavailable",
        "data_state": family["data_state"],
        "target": target,
        "reason": target_reason,
        "metadata": "allowed",
        "publication": family,
    }


def _public_tool(tool, context, projection):
    key = tool["presentation_key"]
    family = projection["publication"]
    metrics = []
    if family is not None:
        values_available = family["values"] == "allowed" and family["data_state"] in {"supported", "partial"}
        for metric in family["metrics"]:
            public_metric = dict(metric)
            if values_available and metric["quality"] == "qualified":
                metrics.append(public_metric)
            else:
                public_metric["value"] = None
                public_metric["reason"] = "unavailable_value"
                metrics.append(public_metric)
    analytical_market = "EZ" if key == "euro_fragmentation" else None
    notice = "model_context_not_company_exposure" if key == "trade_supply_links" else None
    return {
        "presentation_key": key,
        "group_id": tool["group_id"],
        "order": tool["order"],
        "label_en": tool["label_en"],
        "label_zh": tool["label_zh"],
        "question_en": tool["question_en"],
        "question_zh": tool["question_zh"],
        "aliases": list(tool["aliases"]),
        "research_market": context["research_market"],
        "analytical_scope": tool["analytical_scope"],
        "analytical_market": analytical_market,
        "route_state": projection["route_state"],
        "data_state": projection["data_state"],
        "target": projection["target"],
        "reason": projection["reason"],
        "metrics": metrics,
        "interpretation_notice": notice,
    }


def _build_projection(context, qualified_workspace, route_bindings):
    context = _validated_context(context)
    group_ids, group_labels, tools, tool_by_key, targets = _validated_bindings(route_bindings)
    workspace = _validated_workspace(
        qualified_workspace, context, {tool["presentation_key"] for tool in tools}
    )
    projections = {}
    for tool in tools:
        key = tool["presentation_key"]
        projections[key] = _family_projection(
            tool, workspace["families"].get(key), workspace, targets
        )
    return group_ids, group_labels, tools, workspace, projections


def build_intl_library_view(context, qualified_workspace, route_bindings):
    group_ids, group_labels, tools, workspace, projections = _build_projection(
        context, qualified_workspace, route_bindings
    )
    allowed_keys = {
        key for key, projection in projections.items() if projection["metadata"] == "allowed"
    }
    public_tools = []
    search_rows = []
    for tool in tools:
        key = tool["presentation_key"]
        if key in allowed_keys:
            public_tool = _public_tool(tool, context, projections[key])
            public_tools.append(public_tool)
            search_rows.append(
                {
                    "presentation_key": public_tool["presentation_key"],
                    "group_id": public_tool["group_id"],
                    "order": public_tool["order"],
                    "label_en": public_tool["label_en"],
                    "label_zh": public_tool["label_zh"],
                    "question_en": public_tool["question_en"],
                    "question_zh": public_tool["question_zh"],
                    "aliases": list(public_tool["aliases"]),
                }
            )

    group_entries = []
    for slot, group_id in enumerate(group_ids):
        members = [
            tool["presentation_key"]
            for tool in tools
            if tool["group_id"] == group_id and tool["presentation_key"] in allowed_keys
        ]
        if members:
            label_en, label_zh = group_labels[group_id]
            group_entries.append(
                {
                    "slot": slot,
                    "id": group_id,
                    "label_en": label_en,
                    "label_zh": label_zh,
                    "tool_keys": members,
                }
            )
        else:
            group_entries.append({"slot": slot, "state": "withheld"})

    exclusions = []
    for tool in tools:
        key = tool["presentation_key"]
        if key in allowed_keys:
            continue
        projection = projections[key]
        if projection["reason"] == "binding_mismatch":
            state = "unknown"
            reason = "binding_mismatch"
        elif projection["metadata"] == "denied":
            state = "denied"
            reason = "metadata_denied"
        else:
            state = "unknown"
            reason = "metadata_unknown"
        exclusions.append({"slot": tool["order"], "state": state, "reason": reason})

    permitted_count = len(allowed_keys)
    if permitted_count == _TOOL_COUNT:
        catalogue_state = "available"
    elif permitted_count:
        catalogue_state = "partial"
    else:
        catalogue_state = "unavailable"
    return {
        "catalogue_state": catalogue_state,
        "catalogue_generation": workspace["catalogue_generation"],
        "context": {
            "research_market": context["research_market"],
            "horizon": context["horizon"],
            "currency_basis": context["currency_basis"],
            "return_basis": context["return_basis"],
            "source_reference": context["source_reference"],
        },
        "groups": group_entries,
        "tools": public_tools,
        "search_catalogue": search_rows,
        "exclusions": exclusions,
    }


def resolve_intl_tool(presentation_key, context, qualified_workspace, route_bindings):
    if not isinstance(presentation_key, str):
        raise ValueError("invalid_tool:key")
    _, _, tools, _, projections = _build_projection(
        context, qualified_workspace, route_bindings
    )
    if presentation_key not in {tool["presentation_key"] for tool in tools}:
        raise ValueError("invalid_tool:key")
    projection = projections[presentation_key]
    if projection["metadata"] != "allowed":
        return {
            "route_state": projection["route_state"],
            "data_state": projection["data_state"],
            "target": None,
            "reason": projection["reason"],
        }
    tool = next(tool for tool in tools if tool["presentation_key"] == presentation_key)
    public = _public_tool(tool, context, projection)
    return {
        "presentation_key": public["presentation_key"],
        "route_state": public["route_state"],
        "data_state": public["data_state"],
        "research_market": public["research_market"],
        "analytical_scope": public["analytical_scope"],
        "analytical_market": public["analytical_market"],
        "target": public["target"],
        "reason": public["reason"],
        "metrics": public["metrics"],
        "interpretation_notice": public["interpretation_notice"],
    }

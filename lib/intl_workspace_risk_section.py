"""Pure Risk section assembler over accepted currency, pressure and summary helpers."""
from copy import deepcopy
from math import isfinite

from lib.intl_workspace_macro import (
    _check_builtin_tree,
    _destination,
    _exact,
    _registry,
    _text,
)
from lib.intl_workspace_risk import qualify_us_transmission
from lib.intl_workspace_risk_currency import build_currency_channel
from lib.intl_workspace_risk_pressure import build_pressure_rows


_ERROR = "invalid_risk_section_input"
_CONTEXT_KEYS = ("horizon", "currency_basis", "return_basis")
_DOMAIN_KEYS = (
    "origin_stress",
    "us_transmission",
    "statistical_connectedness",
    "return_correlation",
    "directed_pressure",
    "structural_fragility",
)
_DESTINATION_KEYS = _DOMAIN_KEYS + ("company_research",)
_EXPOSURE_MISSING = (
    "issuer_identity",
    "revenue_currency",
    "cost_currency",
    "debt_currency",
    "hedges",
    "effective_date",
)


def _fail():
    raise ValueError(_ERROR)


def _reject_nonfinite(value):
    if type(value) is float and not isfinite(value):
        _fail()
    if type(value) is dict:
        for child in value.values():
            _reject_nonfinite(child)
    elif type(value) is list:
        for child in value:
            _reject_nonfinite(child)


def _check_tree(value):
    _check_builtin_tree(value)
    _reject_nonfinite(value)


def _copy_entry(entry):
    return None if entry is None else deepcopy(entry)


def build_risk_section(
    *,
    context,
    registry,
    overview,
    risk_desk,
    cgl,
    measures,
    field_support,
    summary_eligibility,
    destinations,
):
    """Compose a detached Risk section without inventing domain metrics."""
    try:
        for value in (
            context,
            registry,
            overview,
            risk_desk,
            cgl,
            measures,
            field_support,
            summary_eligibility,
            destinations,
        ):
            _check_tree(value)
        _exact(context, {"selected_market", "horizon", "currency_basis", "return_basis"}, "context")
        if type(destinations) is not dict or type(measures) is not dict or type(field_support) is not dict:
            _fail()
        if not set(destinations) <= set(_DESTINATION_KEYS):
            _fail()
        destination_by_key = {}
        for map_key, entry in destinations.items():
            if type(entry) is not dict:
                _fail()
            key = _destination(entry)
            if key != map_key:
                _fail()
            destination_by_key[key] = deepcopy(entry)
        if summary_eligibility is not None:
            if type(summary_eligibility) is not dict:
                _fail()
            if not set(summary_eligibility) <= {"us_transmission"}:
                _fail()
        if risk_desk is not None and type(risk_desk) is not dict:
            _fail()
        if cgl is not None and type(cgl) is not dict:
            _fail()
        markets, horizons, bases = _registry(registry)
        market_ids = [market["market_id"] for market in markets]
        selected = context["selected_market"]
        if selected is not None and (type(selected) is not str or selected not in market_ids):
            _fail()
        for name in _CONTEXT_KEYS:
            _text(context[name], "context " + name, nullable=False)
        if (
            context["horizon"] not in horizons
            or context["currency_basis"] not in bases
            or context["return_basis"] != "price"
        ):
            _fail()
        if type(overview) is not dict or type(overview.get("context")) is not dict:
            _fail()
        overview_context = overview["context"]
        if any(overview_context.get(name) != context[name] for name in _CONTEXT_KEYS):
            _fail()
        if type(overview.get("rows")) is not list or len(overview["rows"]) != len(markets):
            _fail()
        channels = []
        for slot, market in enumerate(markets):
            channel = build_currency_channel(overview, selected_slot=slot)
            disclosed = channel.get("market")
            if disclosed is not None and disclosed.get("market_id") != market["market_id"]:
                _fail()
            channels.append(deepcopy(channel))
        pressure_rows = build_pressure_rows(
            registry=registry,
            measures=measures,
            field_support=field_support,
        )
        rows = []
        for index, row in enumerate(pressure_rows):
            item = deepcopy(row)
            item["currency_return"] = deepcopy(channels[index]["fx_return_usd_per_local"])
            rows.append(item)
        two_tier = None if risk_desk is None else risk_desk.get("two_tier")
        eligibility = None if summary_eligibility is None else summary_eligibility.get("us_transmission")
        summary = qualify_us_transmission(two_tier=two_tier, eligibility=eligibility)
        domain_panels = {}
        for key in _DOMAIN_KEYS:
            entry = destination_by_key.get(key)
            panel = {
                "key": key,
                "kind": "transmission_summary" if key == "us_transmission" else "retained_research",
                "destination": _copy_entry(entry),
            }
            if key == "us_transmission":
                panel["summary"] = deepcopy(summary)
            domain_panels[key] = panel
        deep_research = []
        for key in _DOMAIN_KEYS:
            entry = destination_by_key.get(key)
            if entry is not None and entry.get("destination") is not None:
                deep_research.append(deepcopy(entry))
        company = destination_by_key.get("company_research")
        selected_channel = None if selected is None else deepcopy(channels[market_ids.index(selected)])
        return {
            "context": deepcopy(context),
            "selected_market": selected,
            "currency_channel": selected_channel,
            "currency_channels": channels,
            "pressure_rows": rows,
            "domain_panels": domain_panels,
            "exposure_boundary": {
                "quality": "unsupported",
                "reason": "issuer_exposure_not_supplied",
                "missing_evidence": list(_EXPOSURE_MISSING),
                "destination": _copy_entry(company),
            },
            "deep_research": deep_research,
        }
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
        raise ValueError(_ERROR) from None


__all__ = ["build_risk_section"]

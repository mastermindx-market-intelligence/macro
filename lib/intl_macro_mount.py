"""Attach admitted Macro projections to existing workspace envelopes."""
from copy import deepcopy
import math
import re

from lib.intl_workspace_binding import binding_version, panel_generation
from lib.intl_workspace_macro import build_macro_section


_CONTEXT = ("horizon", "currency_basis", "return_basis", "source_reference")
_BASES = ("local", "usd_unhedged")
_CONTEXT_ID = re.compile(r"[A-Za-z][A-Za-z0-9_:-]*")
_NOTICE = {
    "market_id": "EZ",
    "field": "policy_rate",
    "instrument_id": "deposit_facility",
    "origin_url": "https://data.ecb.europa.eu/data/datasets/FM/FM.D.U2.EUR.4F.KR.DFR.LEV",
}
_MAX_DEPTH = 64


def _fail():
    raise ValueError("invalid_macro_workspace")


def _text(value, *, nullable=False):
    if value is None and nullable:
        return
    if type(value) is not str or not value:
        _fail()


def _builtin_tree(value, ancestors=None, depth=0):
    if depth > _MAX_DEPTH:
        _fail()
    if value is None or type(value) in {str, int, bool}:
        return
    if type(value) is float:
        if not math.isfinite(value):
            _fail()
        return
    if type(value) not in {dict, list}:
        _fail()
    ancestors = set() if ancestors is None else ancestors
    identity = id(value)
    if identity in ancestors:
        _fail()
    ancestors.add(identity)
    try:
        if type(value) is dict:
            if any(type(key) is not str for key in value):
                _fail()
            children = value.values()
        else:
            children = value
        for child in children:
            _builtin_tree(child, ancestors, depth + 1)
    finally:
        ancestors.remove(identity)


def _bound(value):
    try:
        _builtin_tree(value)
    except RecursionError:
        _fail()


def _notice(value):
    if value is None:
        return None
    if type(value) is not dict or any(type(key) is not str for key in value):
        _fail()
    if set(value) != set(_NOTICE) or value != _NOTICE:
        _fail()
    return dict(value)


def _validate_config(config):
    required = {
        "markets", "horizons", "bases", "default_horizon", "default_basis",
        "source_reference", "anchor_ids", "library_group_ids",
    }
    if type(config) is not dict or not required.issubset(config):
        _fail()
    for key in ("markets", "horizons", "bases"):
        values = config[key]
        if type(values) is not list or not values:
            _fail()
        seen = set()
        for value in values:
            if type(value) is not str or not value or value in seen:
                _fail()
            seen.add(value)
    _text(config["default_horizon"])
    _text(config["default_basis"])
    if config["default_horizon"] not in config["horizons"]:
        _fail()
    if config["default_basis"] not in config["bases"]:
        _fail()
    if any(basis not in _BASES for basis in (*config["bases"], config["default_basis"])):
        _fail()
    _text(config["source_reference"], nullable=True)
    for key in ("anchor_ids", "library_group_ids"):
        values = config[key]
        if type(values) is not list or any(type(value) is not str for value in values):
            _fail()


def _registry(registry, config):
    if type(registry) is not dict or set(registry) != {"markets", "horizons", "bases"}:
        _fail()
    markets = registry["markets"]
    horizons = registry["horizons"]
    bases = registry["bases"]
    if any(type(values) is not list for values in (markets, horizons, bases)):
        _fail()
    market_ids = []
    for market in markets:
        if type(market) is not dict or set(market) != {"market_id", "name_en", "name_zh"}:
            _fail()
        market_id = market["market_id"]
        if (type(market_id) is not str or not market_id
                or market_id in market_ids
                or type(market["name_en"]) is not str or not market["name_en"]
                or type(market["name_zh"]) is not str or not market["name_zh"]):
            _fail()
        market_ids.append(market_id)
    if not market_ids:
        _fail()
    seen_horizons = set()
    for horizon in horizons:
        if type(horizon) is not str or not horizon or horizon in seen_horizons:
            _fail()
        seen_horizons.add(horizon)
    seen_bases = set()
    for basis in bases:
        if type(basis) is not str or not basis or basis in seen_bases:
            _fail()
        seen_bases.add(basis)
    if (market_ids != config["markets"] or horizons != config["horizons"]
            or bases != config["bases"]):
        _fail()
    return market_ids


def _contexts(panels, config, version, generation):
    if version == 1:
        source_reference = config["source_reference"]
    else:
        source_reference = None
    contexts, seen_pairs = {}, set()
    expected_pairs = {(horizon, basis) for horizon in config["horizons"] for basis in config["bases"]}
    for panel in panels:
        if type(panel) is not dict or not {"context_id", "overview"}.issubset(panel):
            _fail()
        context_id = panel["context_id"]
        if (type(context_id) is not str or _CONTEXT_ID.fullmatch(context_id) is None
                or context_id in contexts):
            _fail()
        overview = panel["overview"]
        if type(overview) is not dict:
            _fail()
        context = overview.get("context")
        if type(context) is not dict:
            _fail()
        allowed = {*_CONTEXT, "source_reference_reason"}
        if any(type(key) is not str for key in context) or set(context) != allowed:
            _fail()
        _text(context["horizon"])
        _text(context["currency_basis"])
        _text(context["return_basis"])
        _text(context["source_reference"], nullable=True)
        if version == 1 and context["source_reference"] != source_reference:
            _fail()
        horizon = context["horizon"]
        basis = context["currency_basis"]
        if (horizon not in config["horizons"] or basis not in config["bases"]
                or context["return_basis"] != "price"):
            _fail()
        pair = (horizon, basis)
        if pair in seen_pairs or pair not in expected_pairs:
            _fail()
        seen_pairs.add(pair)
        panel_generation(panel, generation) if version == 2 else None
        contexts[context_id] = {
            key: context[key] for key in ("horizon", "currency_basis", "return_basis")
        }
    if seen_pairs != expected_pairs:
        _fail()
    return contexts


def _eligible_policy(section):
    rows = section.get("market_rows", ()) if type(section) is dict else ()
    if type(rows) is not list:
        return False
    for row in rows:
        if type(row) is not dict or row.get("market_id") != "EZ":
            continue
        projected = row.get("policy_rate")
        instrument = projected.get("instrument") if type(projected) is dict else None
        value = projected.get("value") if type(projected) is dict else None
        return (
            type(projected) is dict
            and projected.get("quality") in {"qualified", "stale"}
            and type(value) in {int, float}
            and type(instrument) is dict
            and instrument.get("kind") == "official_policy"
            and instrument.get("id") == "deposit_facility"
            and instrument.get("market_id") == "EZ"
        )
    return False


def attach_macros(workspace, *, registry, measures, cycle_evidence, destinations,
                  source_notice=None):
    """Publish detached Macro sidecars without changing the owner workspace."""
    if workspace is None:
        _bound(source_notice)
        _notice(source_notice)
        return None
    for value in (workspace, registry, measures, cycle_evidence, destinations, source_notice):
        _bound(value)
    if type(workspace) is not dict or "macros" in workspace:
        _fail()
    _validate_config(workspace.get("config"))
    if (type(workspace.get("binding_version", 1)) is not int
            or workspace.get("binding_version", 1) not in {1, 2}):
        _fail()
    version, generation = binding_version(workspace)
    market_ids = _registry(registry, workspace["config"])
    panels = workspace.get("panels")
    if type(panels) is not list:
        _fail()
    contexts = _contexts(panels, workspace["config"], version, generation)

    notice = _notice(source_notice)
    safe_inputs = {
        "registry": deepcopy(registry),
        "measures": deepcopy(measures),
        "cycle_evidence": deepcopy(cycle_evidence),
        "destinations": deepcopy(destinations),
    }
    first_context = contexts[panels[0]["context_id"]]
    build_macro_section(context={**first_context, "selected_market": None}, **safe_inputs)
    include_notice = version == 2 and notice is not None
    if not include_notice:
        notice = None
    if version == 1:
        projected_measures, projected_cycle = {}, {}
    elif notice is None and "EZ.policy_rate" in safe_inputs["measures"]:
        projected_measures = deepcopy(safe_inputs["measures"])
        del projected_measures["EZ.policy_rate"]
        projected_cycle = safe_inputs["cycle_evidence"]
    else:
        projected_measures = safe_inputs["measures"]
        projected_cycle = safe_inputs["cycle_evidence"]

    sections = []
    for panel in panels:
        context = contexts[panel["context_id"]]
        section = build_macro_section(
            context={**context, "selected_market": None},
            registry=safe_inputs["registry"],
            measures=projected_measures,
            cycle_evidence=projected_cycle,
            destinations=safe_inputs["destinations"],
        )
        sections.append((context, section))
    if include_notice and not any(_eligible_policy(section) for _, section in sections):
        notice = None

    result = deepcopy(workspace)
    macros = []
    for panel, (context, section) in zip(panels, sections, strict=True):
        macro = {
            "context_id": panel["context_id"],
            "context": deepcopy(context),
            "macro_section": section,
            "source_notice": deepcopy(notice),
        }
        if version == 2:
            macro["generation"] = panel["generation"]
        macros.append(macro)
    result["macros"] = macros
    return result

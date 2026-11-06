"""Join Risk sections to an existing International publication."""
from copy import deepcopy

from lib.intl_macro_mount import _bound, _contexts, _registry, _validate_config
from lib.intl_workspace_binding import binding_version
from lib.intl_workspace_risk_section import build_risk_section


def attach_risks(workspace, *, registry, risk_desk, cgl, measures, field_support,
                 summary_eligibility, destinations):
    """Reuse the existing generation contract; never acquire or grant evidence."""
    if workspace is None:
        return None
    try:
        for value in (workspace, registry, risk_desk, cgl, measures, field_support,
                      summary_eligibility, destinations):
            _bound(value)
        if type(workspace) is not dict or "risks" in workspace or "risk_registry" in workspace:
            raise ValueError
        _validate_config(workspace.get("config"))
        version, generation = binding_version(workspace)
        _registry(registry, workspace["config"])
        panels = workspace.get("panels")
        if type(panels) is not list or not panels:
            raise ValueError
        contexts = _contexts(panels, workspace["config"], version, generation)
        sections = []
        for panel in panels:
            context = {**contexts[panel["context_id"]], "selected_market": None}
            args = dict(context=context, registry=registry, overview=panel["overview"],
                        risk_desk=risk_desk, cgl=cgl, measures=measures,
                        field_support=field_support, summary_eligibility=summary_eligibility,
                        destinations=destinations)
            section = build_risk_section(**args)
            if version == 1:
                # Legacy bindings retain admitted currency; new fields need V2.
                section = build_risk_section(**{**args, "measures": {}, "field_support": {},
                                                "summary_eligibility": {}})
            sections.append({
                "context_id": panel["context_id"], "context": deepcopy(context),
                "risk_section": section,
                **({"generation": panel["generation"]} if version == 2 else {}),
            })
        result = deepcopy(workspace)
        result["risks"] = sections
        result["risk_registry"] = deepcopy(registry)
        return result
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
        raise ValueError("invalid_risk_workspace") from None

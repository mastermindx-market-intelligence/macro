"""Attach read-only Inspector projections to the existing rendered workspace."""
from copy import deepcopy
import re

from lib.intl_inspector_view import INSPECTOR_COPY, build_inspector_view
from lib.intl_workspace_binding import binding_version, panel_generation


def attach_inspectors(workspace, *, public_targets=()):
    """Use only already disclosed Overview rows and resolved public destinations.

    No input loading, source qualification, research state or arithmetic lives in
    this composition layer. Unknown rows remain unknown; denied rows have no
    identifiable Inspector. Every horizon/basis uses its original Overview.
    """
    if workspace is None:
        return None
    if (type(workspace) is not dict
            or not {'config', 'panels'}.issubset(workspace)
            or type(workspace['panels']) is not list):
        raise ValueError('invalid Inspector workspace envelope')
    version, generation = binding_version(workspace)
    result = deepcopy(workspace)
    contexts, panels = set(), []
    for panel in workspace["panels"]:
        context_id = panel["context_id"]
        if (type(context_id) is not str or
                not re.fullmatch(r"[A-Za-z][A-Za-z0-9_:-]*", context_id) or
                context_id in contexts):
            raise ValueError("invalid or duplicate Inspector context")
        contexts.add(context_id)
        overview = panel["overview"]
        panel_generation(panel, generation) if version == 2 else None
        context = {key: overview["context"][key] for key in
                   ("horizon", "currency_basis", "return_basis", "source_reference")}
        for row in overview["rows"]:
            if "market_id" not in row:
                continue
            market = row["market_id"]
            links = [{**deepcopy(target), "market_id": market} for target in public_targets]
            inspector = build_inspector_view(
                overview, selected_market=market, context=context, deeper_links=links,
            )
            if inspector["market"] is not None:
                panels.append({"context_id": context_id,
                               **({"generation": panel["generation"]} if version == 2 else {}),
                               "binding": {**context, "market_id": market},
                               "inspector": inspector})
    result["inspectors"] = panels
    result["inspector_copy"] = deepcopy(INSPECTOR_COPY)
    return result

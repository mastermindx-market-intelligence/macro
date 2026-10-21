"""One Global Surveillance section in the existing International workspace.

Wave 2 foundation (packet INTL-GS-W2F, spec R14 §14, seat ruling
DEC:INTL-GS-R14-DESIGN-FREEZE rulings 1–2). This mount owns NO view of its
own: it registers the seven surveillance sub-tabs (scanner, dislocations,
transmission, dossier, scenario, replay, coverage), loads the Wave 1 universe
and rights documents once, and hands each view to its builder module.

Builder contract (W2A = IM13 scanner/coverage, W2B = IM14 dossier):
    build_view(*, universe, rights, contexts, workspace) -> list[dict]
Each returned panel dict is {view, context_id, context, generation, payload}:
  - ``view`` is checked against the invoking view key;
  - ``context_id`` anchors the panel root id (default ``im-gs-<view>``);
  - ``context`` overrides the default binding context
    {horizon, currency_basis, return_basis, source_reference} — horizon and
    currency_basis MUST stay values the workspace config declares, because
    templates/intl_workspace.js panelValid() rejects anything else;
  - ``generation`` defaults to the workspace binding generation (v2);
  - ``payload`` is the view template's data, untouched here.
View templates open their panel with the ``gs_panel_root`` macro in
``templates/intl_workspace/_gs_macros.html.j2`` so panelValid sees exactly the
attributes it requires.

A builder module that does not exist yet is ``not_built`` (its tab renders
disabled); any other failure is ``error`` on that view alone and never
suppresses the page. No network, no file writes, no registry, no store: the
only reads are the two frozen Wave 1 documents via their engine loaders.
"""
from copy import deepcopy
import importlib
import logging

from engine import intl_global_universe as _universe
from lib.intl_macro_mount import _bound, _contexts, _validate_config
from lib.intl_workspace_binding import binding_version

log = logging.getLogger(__name__)

GS_VIEWS = ("scanner", "dislocations", "transmission", "dossier", "scenario", "replay", "coverage")
BUILDERS = {view: f"lib.intl_gs_{view}_view" for view in GS_VIEWS}


def _view_status(status, reason=None):
    entry = {"status": status}
    if reason is not None:
        entry["reason"] = reason
    return entry


def attach_surveillance(workspace, *, universe_loader=None, rights_loader=None):
    """Attach the surveillance view table and panels to a composed workspace.

    Mirrors attach_history(): returns None for None, deep-copies, validates the
    binding, and never mutates the caller's dict. Loaders default to the Wave 1
    engine functions and are resolved at call time so operators (and tests) can
    substitute them on the engine module.
    """
    if workspace is None:
        return None
    try:
        _bound(workspace)
        if type(workspace) is not dict or "surveillance" in workspace or "surveillance_panels" in workspace:
            raise ValueError
        _validate_config(workspace.get("config"))
        version, generation = binding_version(workspace)
        contexts = _contexts(workspace["panels"], workspace["config"], version, generation)
        try:
            universe = universe_loader() if universe_loader is not None else _universe.load_universe()
            rights = rights_loader() if rights_loader is not None else _universe.load_rights_matrix()
        except Exception as exc:
            # A failed universe/rights read authorizes nothing and suppresses
            # nothing: every view reports error and the page stays intact.
            log.error("International Surveillance universe unavailable (%s)", type(exc).__name__)
            result = deepcopy(workspace)
            result["surveillance"] = {
                "views": {view: _view_status("error", type(exc).__name__) for view in GS_VIEWS},
            }
            result["surveillance_panels"] = []
            return result
        default_context = dict(
            horizon=workspace["config"]["default_horizon"],
            currency_basis=workspace["config"]["default_basis"],
            return_basis="price",
            source_reference=workspace["config"]["source_reference"] if version == 1 else None,
        )
        views = {}
        panels = []
        for view in GS_VIEWS:
            module_name = BUILDERS[view]
            try:
                builder = importlib.import_module(module_name)
            except ModuleNotFoundError as exc:
                if exc.name == module_name:
                    views[view] = _view_status("not_built")
                else:
                    views[view] = _view_status("error", type(exc).__name__)
                continue
            try:
                built = builder.build_view(universe=universe, rights=rights,
                                           contexts=contexts, workspace=workspace)
            except Exception as exc:
                views[view] = _view_status("error", type(exc).__name__)
                continue
            if not built:
                views[view] = _view_status("empty")
                continue
            views[view] = _view_status("available")
            for panel in built:
                context = dict(default_context)
                context.update(panel.get("context") or {})
                panels.append(dict(view=view,
                                   context_id=panel.get("context_id") or f"im-gs-{view}",
                                   context=context,
                                   generation=panel.get("generation") or generation,
                                   payload=panel.get("payload")))
        result = deepcopy(workspace)
        result["surveillance"] = {
            "views": views,
            # Counts only (Wave 1 IM11 contract): no per-market claims here.
            "universe": {capability: _universe.coverage_summary(universe, capability)
                         for capability in _universe.CAPABILITIES},
        }
        result["surveillance_panels"] = panels
        return result
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
        raise ValueError("invalid_surveillance_workspace") from None

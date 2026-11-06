"""One Global Surveillance section in the existing International workspace.

Wave 2 foundation (packet INTL-GS-W2F, spec R14 §14, seat ruling
DEC:INTL-GS-R14-DESIGN-FREEZE rulings 1–2). This mount owns NO view of its
own: it registers the seven surveillance sub-tabs (scanner, dislocations,
transmission, dossier, scenario, replay, coverage), loads the Wave 1 universe
and rights documents once, and hands each view to its builder module.

Builder contract (W2A = IM13 scanner/coverage, W2B = IM14 dossier):
    build_view(*, universe, rights, contexts, workspace, observations=None) -> list[dict]
  ``observations`` is the caller's X2 observation set (or None) exactly as the
  ``attach_surveillance(observations=...)`` kwarg received it (each builder
  gets its own deep copy).
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
from engine.intl_global_observation import REQUIRED_CLOCKS
from lib.intl_gs_display import horizon_label, snapshot_display
from lib.intl_macro_mount import _bound, _contexts, _validate_config
from lib.intl_workspace_binding import binding_version

log = logging.getLogger(__name__)

GS_VIEWS = ("scanner", "dislocations", "transmission", "dossier", "scenario", "replay", "coverage")
BUILDERS = {view: f"lib.intl_gs_{view}_view" for view in GS_VIEWS}
OBSERVATION_BASES = ("local", "usd_unhedged", "usd_hedged")


def _view_status(status, reason=None):
    entry = {"status": status}
    if reason is not None:
        entry["reason"] = reason
    return entry


def _observation_counts(observations):
    """Counts-only projection of an X2 observation set; never a value."""
    if observations is None:
        return {basis: {"total": 0, "qualified": 0, "abstain": 0}
                for basis in OBSERVATION_BASES}
    counts = {}
    for basis in OBSERVATION_BASES:
        entries = (observations.get("bases") or {}).get(basis) or []
        qualified = sum(1 for entry in entries
                        if isinstance(entry, dict) and entry.get("state") == "qualified")
        counts[basis] = {"total": len(entries), "qualified": qualified,
                         "abstain": len(entries) - qualified}
    return counts


def _snapshot_clocks(observations):
    """Per basis: the latest `at` among QUALIFIED observations per required
    clock, or None; hedged never has a qualified observation, so it is all
    None. Counts only — no observation value ever leaves this projection."""
    snapshot = {}
    for basis in OBSERVATION_BASES:
        entries = ((observations or {}).get("bases") or {}).get(basis) or []
        qualified = [entry for entry in entries
                     if isinstance(entry, dict) and entry.get("state") == "qualified"]
        clocks = {}
        for clock in REQUIRED_CLOCKS:
            instants = []
            for entry in qualified:
                moment = (entry.get("clocks") or {}).get(clock) or {}
                at = moment.get("at") if isinstance(moment, dict) else None
                if isinstance(at, str) and at:
                    instants.append(at)
            clocks[clock] = max(instants) if instants else None
        snapshot[basis] = {"clocks": clocks, "qualified": len(qualified),
                           "total": len(entries)}
    return snapshot


def attach_surveillance(workspace, *, universe_loader=None, rights_loader=None,
                        observations=None):
    """Attach the surveillance view table and panels to a composed workspace.

    Mirrors attach_history(): returns None for None, deep-copies, validates the
    binding, and never mutates the caller's dict. Loaders default to the Wave 1
    engine functions and are resolved at call time so operators (and tests) can
    substitute them on the engine module. ``observations`` is the X2
    observation set (or None): each builder receives its own deep copy, and the
    workspace keeps only counts and clock instants — never a value.
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
                built = builder.build_view(
                    universe=universe, rights=rights, contexts=contexts,
                    workspace=workspace,
                    observations=deepcopy(observations) if observations is not None else None)
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
            # X3: counts-only projection of the X2 observation set.
            "observations": {
                "status": None if observations is None else observations.get("status"),
                "source_reference": (None if observations is None
                                     else observations.get("source_reference")),
                "counts": _observation_counts(observations),
            },
            # X5: snapshot clock instants per basis (no values), each with the
            # FX1 §13.3 display added through the single composition path
            # (lib.intl_gs_display.snapshot_display) — raw clocks unchanged.
            "snapshot": snapshot_display(_snapshot_clocks(observations)),
            # FX5: one horizon vocabulary for every config horizon (IM13's
            # segmented controls and read-outs bind the same labels).
            "horizon_labels": {
                horizon: {"en": en, "zh": zh}
                for horizon, (en, zh) in (
                    (horizon, horizon_label(horizon))
                    for horizon in workspace["config"]["horizons"])
            },
        }
        result["surveillance_panels"] = panels
        return result
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
        raise ValueError("invalid_surveillance_workspace") from None

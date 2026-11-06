"""INTL-GS §14 graph-boundary label rule (ORCH-5 SPEC_A1 part A).

An out-of-graph market displays structural research or a qualified candidate
label, never an invented graph score. This module is a pure classification
over one existing ``engine.intl_transmission_evidence.market_summary``
receipt: it reads the summary's closed facts, chooses one of three closed
labels, and invents nothing — no signal, coefficient, weight, rank, count or
causal verb. Membership itself stays owned by the frozen structural graph;
the frozen 11-market graph and the 14-ETF VAR are read-only upstream.

Rendering the label on any view surface (W2B dossier, W4B markets[]) is a
later UI lane's work: this module owns the label contract only.
"""
from __future__ import annotations

CONTRACT_VERSION = "intl-global-graph-boundary-v1"

#: Closed label vocabulary; (label_en, label_zh) per label id.
LABELS = {
    "structural_graph_member": ("In structural graph", "结构图成员"),
    "qualified_candidate": ("Qualified candidate, outside structural graph",
                            "合格候选（结构图外）"),
    "structural_research": ("Structural research only", "仅结构研究"),
}

#: Closed interpretation limits; text only, no numbers, no causal verbs.
INTERPRETATION_LIMITS = (
    "Research labeling only: not a trading signal, a valuation or a "
    "recommendation.",
    "A qualified candidate label records that a frozen statistical "
    "association exists outside the structural graph; it is not graph "
    "membership and not a promotion into any model.",
    "Qualified observations are observations, not a model; they never "
    "promote a market to a candidate.",
    "No graph quantity is invented here: membership, edge ids and model "
    "statuses are read from the frozen contracts unchanged.",
    "Labels are point-in-time: they describe the summary's evidence and "
    "carry no expectation about the next session.",
)


class GraphBoundaryError(ValueError):
    """Raised when a summary does not carry the market_summary shape."""


def graph_boundary_label(summary: dict) -> dict:
    """One closed graph-boundary label for one market_summary receipt.

    First match wins: structural graph member, then qualified candidate
    (outside the graph with statistical evidence), then structural research
    only. The input is never mutated.
    """
    if (not isinstance(summary, dict)
            or not isinstance(summary.get("structural_graph"), dict)
            or "market_id" not in summary):
        raise GraphBoundaryError("summary_shape")

    graph = summary["structural_graph"]
    member = graph.get("member") is True
    statistical = summary.get("statistical_evidence") or []
    research = summary.get("structural_research") or []
    observation_ids = ((summary.get("qualified_observations") or {})
                       .get("observation_ids") or [])

    if member:
        label = "structural_graph_member"
        candidate_basis: list[dict] = []
        reasons: list[str] = []
    elif statistical:
        label = "qualified_candidate"
        candidate_basis = sorted(
            ({"edge_id": edge.get("edge_id"),
              "model_status": edge.get("model_status")}
             for edge in statistical
             if isinstance(edge, dict)),
            key=lambda item: item["edge_id"])
        reasons = []
    else:
        label = "structural_research"
        candidate_basis = []
        reasons = ["no_candidate_evidence"]
        if not research:
            reasons.append("no_structural_research")

    label_en, label_zh = LABELS[label]
    return {
        "contract_version": CONTRACT_VERSION,
        "market_id": summary["market_id"],
        "label": label,
        "label_en": label_en,
        "label_zh": label_zh,
        "graph_member": member,
        "structural_version": graph.get("structural_version"),
        "candidate_basis": candidate_basis,
        "reasons": reasons,
        "has_qualified_observations": bool(observation_ids),
        "interpretation_limits": list(INTERPRETATION_LIMITS),
    }

"""FIF A1: typed per-cell causes for unlinked-vintage lineage refusals.

The production lineage mint (``engine/fundamental_forensics/lineage_evidence.py``
``derive_confirmation_receipts`` / ``derive_chain_confirmation_receipts``)
returns ACCEPTED receipts only and discards refusals, so a query cell refused
with the runtime reason ``unlinked source vintages require an explicit typed
revision lineage`` (``engine/fundamental_forensics/query.py``,
``_select_source_group``) hides its real cause.  This module recovers the typed
cause PER CELL by calling the kernel's own guard functions —
``lineage_evidence.evaluate_confirmation`` for each adjacent edge and
``lineage_evidence.classify_filing_chain`` for 3+ accession chains.  No guard
logic is re-implemented or copied here.

Cause vocabulary (general, issuer-neutral; no ticker/CIK special case exists
anywhere in this module):

* ``restatement_requires_revision_lineage`` — any adjacent edge refused by
  guard 8 (``changed_value``) or guard 12 (``nil_state_difference``), or any
  chain state ``contradictory``.  Takes precedence and is never folded into
  the cross-taxonomy code.
* ``precision_consistent_unconfirmed`` — any adjacent edge refused by kernel
  guard 8 (unequal parsed values that still agree under the kernel's own
  rounding intervals) or guard 9 (equal values at different accuracy tokens).
  Restatement takes precedence over it, and it takes precedence over the
  cross-taxonomy code.  The cell stays refused: no rounding tolerance,
  rescue or value substitution is applied.
* ``cross_taxonomy_version_confirmation_unavailable`` — every failing edge
  fails ONLY by guard 11 (``source_taxonomy_namespace_version_mismatch``).
  Bucketed per logical key as ``v1_pair`` (exactly 2 accessions) or
  ``v2_unproven_chain`` (3+ accessions whose chain state is ``unproven``);
  ``cascade`` counts derived cells whose EVERY not-evaluable dependency LEAF
  classifies to this code.  A leaf is a dependency node with no
  ``dependency_cell_ids`` of its own (``dependency_nodes`` holds ALL
  transitive nodes, so intermediate derived nodes never count as leaves);
  one non-cross leaf disqualifies the cascade.
* ``mixed_leaf_causes`` — a derived cell with at least one cross-taxonomy
  leaf AND at least one other not-evaluable leaf: too mixed to call a pure
  cascade, it carries the cross verdicts' basis and accessions plus the
  other leaves' reasons in ``leaf_reasons``.
* ``unclassified_lineage_refusal`` — anything else, carrying the raw kernel
  codes verbatim.

A cause is carried, never a failed check: the ledger records evidence, it does
not gate publication.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from engine.fundamental_forensics.lineage_evidence import (
    CHAIN_STATE_CONTRADICTORY,
    CHAIN_STATE_UNPROVEN,
    REFUSAL_CHANGED_VALUE,
    REFUSAL_NIL_STATE_DIFFERENCE,
    REFUSAL_PRECISION_CONSISTENT_UNCONFIRMED,
    REFUSAL_TAXONOMY_NAMESPACE_VERSION_MISMATCH,
    classify_filing_chain,
    evaluate_confirmation,
)

# The canonical duplicate representative is the kernel's own grouping
# primitive (lineage_evidence imports it from raw_ledger at
# engine/fundamental_forensics/lineage_evidence.py:43-52); import it from the
# same module the kernel does — never a re-implementation.
from engine.fundamental_forensics.raw_ledger import (  # noqa: E402
    RawFactOccurrence,
    _canonical_duplicate_representative,
)

# The runtime refusal whose cause this module recovers
# (engine/fundamental_forensics/query.py, _select_source_group).
UNLINKED_VINTAGES_REASON = (
    "unlinked source vintages require an explicit typed revision lineage"
)
# The derived-cell dependency refusal prefix
# (engine/fundamental_forensics/query.py, _evaluate_formula).
INCOMPATIBLE_DEPENDENCIES_PREFIX = "incompatible_dependencies: "

CODE_RESTATEMENT = "restatement_requires_revision_lineage"
# The kernel's own precision-consistent refusal code (guards 8/9), imported —
# never a copied string literal.
CODE_PRECISION = REFUSAL_PRECISION_CONSISTENT_UNCONFIRMED
CODE_CROSS_TAXONOMY = "cross_taxonomy_version_confirmation_unavailable"
CODE_MIXED_LEAF_CAUSES = "mixed_leaf_causes"
CODE_UNCLASSIFIED = "unclassified_lineage_refusal"

BUCKET_V1_PAIR = "v1_pair"
BUCKET_V2_UNPROVEN_CHAIN = "v2_unproven_chain"
BUCKET_CASCADE = "cascade"

BASIS_KERNEL_GUARD_11 = "kernel_guard_11"
BASIS_ELIMINATION = "elimination_without_namespace_uris"

_RESTATEMENT_EDGE_CODES = frozenset({REFUSAL_CHANGED_VALUE, REFUSAL_NIL_STATE_DIFFERENCE})


def _ordered_accession_groups(
    events: Sequence[RawFactOccurrence],
) -> list[tuple[str, list[RawFactOccurrence]]]:
    """Group one logical key's events by accession, ordered by accepted_at.

    Ordering uses each group's canonical duplicate representative's
    ``accepted_at`` (the same clock the kernel's guards use for the
    parent-before-child test), then the accession string for determinism.
    """
    by_accession: dict[str, list[RawFactOccurrence]] = {}
    for event in events:
        by_accession.setdefault(event.source.accession, []).append(event)
    def _order(item: tuple[str, list[RawFactOccurrence]]) -> tuple[Any, str]:
        representative = _canonical_duplicate_representative(item[1])
        accepted = representative.accepted_at
        return (accepted.isoformat() if accepted is not None else "", item[0])
    return [(a, by_accession[a]) for a in sorted(by_accession, key=lambda a: _order((a, by_accession[a])))]


def _uri_for(
    group: Sequence[RawFactOccurrence],
    taxonomy_uris: Mapping[tuple[str, str], str],
) -> str | None:
    """The original Clark namespace URI keyed by the group's representative."""
    representative = _canonical_duplicate_representative(group)
    return taxonomy_uris.get(
        (representative.source.accession, representative.source_occurrence_key or "")
    )


def classify_logical_key(
    events: Sequence[RawFactOccurrence],
    *,
    taxonomy_uris: Mapping[tuple[str, str], str],
    archive_available: bool,
) -> dict[str, Any]:
    """Classify one logical key's cross-filing refusal cause.

    Calls ONLY the kernel's own functions: ``evaluate_confirmation`` per
    adjacent accession pair (guarded with URIs when the archive supplies
    them, and unguarded) and ``classify_filing_chain`` for 3+ accession
    keys.  Without an archive the guarded form is never called without URIs
    (it always refuses on the missing URI alone), so the cross-taxonomy
    conclusion rests on elimination: every edge passes the unguarded call.
    """
    groups = _ordered_accession_groups(events)
    accessions = [name for name, _group in groups]
    edges: list[tuple[str | None, str | None]] = []
    for index in range(len(groups) - 1):
        parent_group = groups[index][1]
        child_group = groups[index + 1][1]
        parent_uri = _uri_for(parent_group, taxonomy_uris)
        child_uri = _uri_for(child_group, taxonomy_uris)
        if archive_available:
            guarded = evaluate_confirmation(
                parent_group,
                child_group,
                parent_taxonomy_uri=parent_uri,
                child_taxonomy_uri=child_uri,
                require_taxonomy_uri=True,
            )
        else:
            # Guard 11 without URIs refuses on the absent URI alone; calling
            # it would say nothing about the real taxonomy versions.
            guarded = None
        unguarded = evaluate_confirmation(
            parent_group, child_group, require_taxonomy_uri=False
        )
        edges.append((guarded, unguarded))
    chain_state = None
    if len(groups) >= 3:
        # classify_filing_chain is the kernel's own chain classifier; with an
        # archive it sees the real URIs, without one the elimination basis.
        chain_state = classify_filing_chain(
            events, original_taxonomy_uris=taxonomy_uris
        ).state
    raw_codes = [code for pair in edges for code in pair if code is not None]
    if chain_state is not None:
        raw_codes.append(f"chain_state:{chain_state}")

    # Precedence 1: a restatement (guards 8/12) or a contradictory chain.
    if (
        any(
            code in _RESTATEMENT_EDGE_CODES
            for pair in edges
            for code in pair
            if code is not None
        )
        or chain_state == CHAIN_STATE_CONTRADICTORY
    ):
        return {
            "code": CODE_RESTATEMENT,
            "bucket": None,
            "basis": None,
            "kernel_codes": raw_codes,
            "accessions": accessions,
        }

    # Precedence 2: any edge the kernel itself refused as precision-consistent
    # (guard 8 — unequal values whose rounding intervals still agree — or
    # guard 9 — equal values at different accuracy tokens).  Read only the
    # edge codes evaluate_confirmation already returned; no guard logic here.
    if any(
        code == REFUSAL_PRECISION_CONSISTENT_UNCONFIRMED
        for pair in edges
        for code in pair
        if code is not None
    ):
        return {
            "code": CODE_PRECISION,
            "bucket": None,
            "basis": None,
            "kernel_code": REFUSAL_PRECISION_CONSISTENT_UNCONFIRMED,
            "kernel_codes": raw_codes,
            "accessions": accessions,
        }

    # Precedence 3: every FAILING edge fails ONLY by guard 11.  An edge that
    # passes the guarded call outright (an exact confirmation) is not a
    # failing edge and does not disqualify the key.
    if archive_available:
        failing = [
            (guarded, unguarded)
            for guarded, unguarded in edges
            if guarded is not None
        ]
        only_guard_11 = bool(failing) and all(
            guarded == REFUSAL_TAXONOMY_NAMESPACE_VERSION_MISMATCH
            and unguarded is None
            for guarded, unguarded in failing
        )
        basis = BASIS_KERNEL_GUARD_11
    else:
        # Elimination: the guarded form is never called without URIs (it
        # refuses on the absent URI alone), so the conclusion rests on every
        # edge passing the unguarded call — the only guard that can then fail
        # is guard 11.
        only_guard_11 = bool(edges) and all(
            unguarded is None for _guarded, unguarded in edges
        )
        basis = BASIS_ELIMINATION
    if only_guard_11:
        bucket: str | None = None
        if len(accessions) == 2:
            bucket = BUCKET_V1_PAIR
        elif len(accessions) >= 3 and chain_state == CHAIN_STATE_UNPROVEN:
            bucket = BUCKET_V2_UNPROVEN_CHAIN
        if bucket is not None:
            return {
                "code": CODE_CROSS_TAXONOMY,
                "bucket": bucket,
                "basis": basis,
                "kernel_code": REFUSAL_TAXONOMY_NAMESPACE_VERSION_MISMATCH,
                "kernel_codes": raw_codes,
                "accessions": accessions,
            }

    # Precedence 4: anything else carries the raw kernel codes verbatim.
    return {
        "code": CODE_UNCLASSIFIED,
        "bucket": None,
        "basis": None,
        "kernel_codes": raw_codes,
        "accessions": accessions,
    }


def _key_classification_for_ids(
    occurrence_ids: Sequence[str],
    *,
    event_by_id: Mapping[str, RawFactOccurrence],
    events_by_logical_key: Mapping[str, Sequence[RawFactOccurrence]],
    taxonomy_uris: Mapping[tuple[str, str], str],
    archive_available: bool,
) -> dict[str, Any] | None:
    """The single logical-key classification behind a cell's occurrences."""
    if not occurrence_ids:
        return None
    events = [event_by_id[i] for i in occurrence_ids if i in event_by_id]
    if not events:
        return None
    logical_keys = {event.logical_key for event in events}
    if len(logical_keys) != 1:
        return None
    key_events = events_by_logical_key.get(next(iter(logical_keys)))
    if not key_events:
        return None
    return classify_logical_key(
        key_events,
        taxonomy_uris=taxonomy_uris,
        archive_available=archive_available,
    )


def classify_refusal_causes(
    *,
    cells: Sequence[Any],
    event_by_id: Mapping[str, RawFactOccurrence],
    events_by_logical_key: Mapping[str, Sequence[RawFactOccurrence]],
    taxonomy_uris: Mapping[tuple[str, str], str],
    archive_available: bool,
) -> dict[str, Any]:
    """Typed causes for every unlinked-vintage cell plus the strict cascade.

    ``cells`` are ``MetricCell`` receipts from the kernel's own
    ``BitemporalMetricQueryEngine.query_matrix``.  Direct cells refused with
    the unlinked-vintages reason are classified through their
    ``provenance.source_occurrence_ids``.  Derived cells refused with
    ``incompatible_dependencies:`` are decided over their not-evaluable
    dependency LEAVES (the receipt DAG nodes the kernel itself recorded with
    no ``dependency_cell_ids`` of their own, resolving the dependency
    declaration the registry contract carries —
    ``engine/fundamental_forensics/metric_registry.py``
    ``MetricContract.formula_dependencies`` at metric_registry.py:365-366):

    * EVERY leaf classifies to the cross-taxonomy code → ``cascade``;
    * at least one cross leaf AND at least one other not-evaluable leaf →
      ``mixed_leaf_causes``, carrying the cross verdicts and the other
      leaves' reasons;
    * no cross leaf → the cell is skipped (no cause is invented).
    """
    from engine.fundamental_forensics.query import CellState  # local: avoid cycle at import

    def _is_cross(verdict: dict[str, Any] | None) -> bool:
        return verdict is not None and verdict["code"] == CODE_CROSS_TAXONOMY

    classified: list[dict[str, Any]] = []
    cascade_classified: list[dict[str, Any]] = []
    mixed_classified: list[dict[str, Any]] = []
    for cell in cells:
        reason = getattr(cell, "reason", None)
        if reason == UNLINKED_VINTAGES_REASON:
            verdict = _key_classification_for_ids(
                tuple(cell.provenance.source_occurrence_ids or ()),
                event_by_id=event_by_id,
                events_by_logical_key=events_by_logical_key,
                taxonomy_uris=taxonomy_uris,
                archive_available=archive_available,
            )
            if verdict is None:
                verdict = {
                    "code": CODE_UNCLASSIFIED,
                    "bucket": None,
                    "basis": None,
                    "kernel_codes": [],
                    "accessions": [],
                }
            classified.append(
                {
                    "metric_id": cell.metric_id,
                    "period": _period_key_text(cell),
                    "code": verdict["code"],
                    "bucket": verdict["bucket"],
                    "basis": verdict["basis"],
                    "kernel_code": verdict.get("kernel_code"),
                    "kernel_codes": verdict["kernel_codes"],
                    "accessions": verdict["accessions"],
                    "cascade": False,
                }
            )
        elif isinstance(reason, str) and reason.startswith(INCOMPATIBLE_DEPENDENCIES_PREFIX):
            # Leaves are the DAG nodes with no dependency_cell_ids of their
            # own; intermediate derived nodes (non-empty dependency_cell_ids)
            # are never leaves.  getattr keeps hand-built receipt nodes
            # without the field in the leaf set.
            ne_leaves = [
                node
                for node in cell.dependency_nodes
                if node.state is CellState.NOT_EVALUABLE
                and not tuple(getattr(node.provenance, "dependency_cell_ids", ()) or ())
            ]
            if not ne_leaves:
                continue
            leaf_verdicts: list[tuple[Any, dict[str, Any] | None]] = []
            for node in ne_leaves:
                verdict = None
                if node.reason == UNLINKED_VINTAGES_REASON:
                    verdict = _key_classification_for_ids(
                        tuple(node.provenance.source_occurrence_ids or ()),
                        event_by_id=event_by_id,
                        events_by_logical_key=events_by_logical_key,
                        taxonomy_uris=taxonomy_uris,
                        archive_available=archive_available,
                    )
                leaf_verdicts.append((node, verdict))
            cross_pairs = [
                (node, verdict) for node, verdict in leaf_verdicts if _is_cross(verdict)
            ]
            if not cross_pairs:
                continue
            other_pairs = [
                (node, verdict) for node, verdict in leaf_verdicts if not _is_cross(verdict)
            ]
            cross_accessions = sorted(
                {
                    accession
                    for _node, verdict in cross_pairs
                    for accession in verdict["accessions"]
                }
            )
            if other_pairs:
                # A mixed leaf set is never a cascade: the cross verdicts are
                # carried, and every OTHER leaf's reason is named.
                leaf_reasons = sorted(
                    {
                        (
                            verdict["code"]
                            if verdict is not None
                            else CODE_UNCLASSIFIED
                        )
                        if node.reason == UNLINKED_VINTAGES_REASON
                        else str(node.reason or "")
                        for node, verdict in other_pairs
                    }
                )
                mixed_classified.append(
                    {
                        "metric_id": cell.metric_id,
                        "period": _period_key_text(cell),
                        "code": CODE_MIXED_LEAF_CAUSES,
                        "bucket": None,
                        "basis": cross_pairs[0][1]["basis"],
                        "kernel_code": None,
                        "kernel_codes": [],
                        "accessions": cross_accessions,
                        "cascade": False,
                        "leaf_reasons": leaf_reasons,
                    }
                )
            else:
                basis = next(
                    (verdict["basis"] for _node, verdict in cross_pairs), None
                )
                cascade_classified.append(
                    {
                        "metric_id": cell.metric_id,
                        "period": _period_key_text(cell),
                        "code": CODE_CROSS_TAXONOMY,
                        "bucket": BUCKET_CASCADE,
                        "basis": basis,
                        "kernel_code": REFUSAL_TAXONOMY_NAMESPACE_VERSION_MISMATCH,
                        "kernel_codes": [],
                        "accessions": cross_accessions,
                        "cascade": True,
                    }
                )

    all_cells = classified + cascade_classified + mixed_classified
    histogram: dict[str, Any] = {
        CODE_RESTATEMENT: 0,
        CODE_PRECISION: 0,
        CODE_CROSS_TAXONOMY: {
            BUCKET_V1_PAIR: 0,
            BUCKET_V2_UNPROVEN_CHAIN: 0,
            BUCKET_CASCADE: 0,
        },
        CODE_MIXED_LEAF_CAUSES: 0,
        CODE_UNCLASSIFIED: 0,
    }
    for row in all_cells:
        if row["code"] == CODE_CROSS_TAXONOMY:
            histogram[CODE_CROSS_TAXONOMY][row["bucket"]] += 1
        else:
            histogram[row["code"]] += 1
    return {
        "basis": (
            BASIS_KERNEL_GUARD_11 if archive_available else BASIS_ELIMINATION
        ),
        "histogram": histogram,
        "cells": sorted(
            all_cells,
            key=lambda row: (row["metric_id"], row["period"]),
        ),
    }


def _period_key_text(cell: Any) -> str:
    """The cell's period as ``kind|start|end`` display text."""
    period = cell.period
    kind = getattr(period, "kind", None)
    kind_value = getattr(kind, "value", kind)
    start = getattr(period, "start", None)
    end = getattr(period, "end", None)
    return "|".join(
        [
            str(kind_value or ""),
            str(start) if start else "",
            str(end) if end else "",
        ]
    )


__all__ = [
    "BASIS_ELIMINATION",
    "BASIS_KERNEL_GUARD_11",
    "BUCKET_CASCADE",
    "BUCKET_V1_PAIR",
    "BUCKET_V2_UNPROVEN_CHAIN",
    "CODE_CROSS_TAXONOMY",
    "CODE_MIXED_LEAF_CAUSES",
    "CODE_PRECISION",
    "CODE_RESTATEMENT",
    "CODE_UNCLASSIFIED",
    "INCOMPATIBLE_DEPENDENCIES_PREFIX",
    "UNLINKED_VINTAGES_REASON",
    "classify_logical_key",
    "classify_refusal_causes",
]

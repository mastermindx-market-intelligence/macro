"""Original issuer economics + reporting denominators over the declared
cohort — the lane-5 v1.1 amendment block (COO delta 2026-11-10).

What this serves
----------------
An ADDITIVE ``sector_intelligence.issuer_economics.v1`` block attached to the
v2 THEME query envelope by the registration seam
(:mod:`app.theme_research._call_v2_query`). It carries, per amendment §6.2
/:§6.3 / LANE_DELTAS_V11 lane 5:

* original dated ISSUER observations — every ``reported`` fact row the owner
  bundle served, VERBATIM and signed, negative values included, never dropped;
* reporting denominators — eligible / identified / reported / comparable with
  the explicit unknown and noncomparable classes. UNREPORTED IS UNKNOWN, never
  zero, never a deterioration; NONCOMPARABLE IS NOT A NEGATIVE RESULT and
  never enters the same denominator;
* NO selected-winner feed — every cohort issuer is listed with its own state;
  there is no ranking, no winner, no aggregate that depends on a selection;
* all-issuer-alias exclusion — the leave-issuer-out projection excludes the
  candidate by ``issuer_id`` AND CIK over every alias the Data OS master
  currently evidences (``IssuerMaster.securities_of_issuer``, the §9.7
  canonical enumeration), not just the primary listing;
* shared roots — :func:`engine.leadership_rotation_context.dedupe_source_roots`
  families over the evidence rows (one workspace = one lineage root; "three
  measures from one filing", never "three independent confirmations");
* concentration — HHI over the declared-cohort weights, both raw and
  leave-issuer-out.

Frozen-input invariance (SP04): the leave-issuer-out membership, weights and
peer measures are computed over the NON-candidate rows only. Perturbing the
candidate's own rows — across every alias — cannot change them by
construction. Where the separately recomputed whole-cohort benchmark still
contains the candidate, the mediated effect is LABELLED
(``mediated_benchmark: true``), never presented as independent peer
confirmation.

What this declares absent
-------------------------
No membership, breadth or rank authority (the witness cohort is a declared
proof cohort carrying ``slice_scope_unowned`` upstream already). No ranking,
gating, sizing, entry or origination flag is read or written; the only
arithmetic is equal-weight renormalization over the DECLARED cohort, an HHI
over those weights, and signed differences of same-metric adjacent-period
reported facts (the NESTED ``row["reported"]`` entries; the fiscal period is
the owning row's). The fixed wording law is carried in the response: raw relative
strength is not estimated alpha; positive selection contribution is not
evidence of portfolio skill.

Purity: stdlib-only at import (the reuse import of ``dedupe_source_roots``
is lazy, inside the build function, so no consumer drags the rotation module
at import time). Never raises for mapping-shaped inputs; a failed owner read
degrades to typed unknowns.
"""
from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping, Sequence
from typing import Any

__all__ = [
    "ISSUER_ECONOMICS_SCHEMA",
    "build_issuer_economics",
]

ISSUER_ECONOMICS_SCHEMA = "sector_intelligence.issuer_economics.v1"

#: Fixed wording law (amendment §4C / §7): carried verbatim in every block so
#: a consumer cannot misread a descriptive aggregate as alpha or skill.
WORDING = {
    "relative_strength": (
        "Raw relative strength is not estimated alpha."
    ),
    "selection_contribution": (
        "Positive selection contribution is not evidence of portfolio skill."
    ),
    "lineage": (
        "Deduplicated source roots establish lineage uniqueness, "
        "not statistical independence."
    ),
    "unreported": "An unreported issuer is unknown, not a deterioration or zero.",
    "noncomparable": "A noncomparable report is not a negative result.",
}

#: The declared renormalization method (§6.3: "renormalize the remaining
#: weights under the declared method" — the method is DECLARED here, once).
_RENORM_METHOD = "equal_weight_over_declared_cohort"

#: The six false authority flags — same ceiling shape the vertical envelopes
#: carry (may_rank/may_gate/may_size/may_veto/may_originate/may_open_entry).
AUTHORITY = {
    "rank": False,
    "gate": False,
    "size": False,
    "veto": False,
    "originate": False,
    "open_entry": False,
}


def _rows(bundle: Any) -> list[Mapping[str, Any]]:
    """Materialise the bundle's event-workspace rows; non-iterable or absent
    means no rows, never a raise."""
    if not hasattr(bundle, "event_workspaces"):
        return []
    raw = bundle.event_workspaces
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
        return []
    return [row for row in raw if isinstance(row, Mapping)]


def _same_issuer(row_cik: object, identity_cik: object) -> bool:
    """Exact string equality, bound on the identity's plain ``str`` — same
    hardening shape as ``semiconductor_witness_scope.verify_workspace_cik``."""
    return isinstance(row_cik, str) and str.__eq__(identity_cik, row_cik) is True


def _fact_rows(
    rows: list[Mapping[str, Any]],
) -> Iterator[tuple[Mapping[str, Any], Mapping[str, Any]]]:
    """Yield ``(row, fact)`` over the rows' NESTED ``reported`` facts — the
    one place facts are read. A row that served no fact yields nothing, so
    "the issuer has rows" and "the issuer reported" can never be conflated
    (SP12: a row with an empty ``reported`` list is an unreported issuer)."""
    for row in rows:
        for fact in row.get("reported") or ():
            if isinstance(fact, Mapping):
                yield row, fact


def _row_period_index(row: Mapping[str, Any]) -> int | None:
    """The row's structured fiscal period as a comparable index
    (``year * 4 + quarter``), or ``None`` when the row carries no well-formed
    period. The fact's own ``fiscal_period`` is a LABEL (``"2026Q2"``); the
    structured period is the row's, so adjacency is decided on the row."""
    period = row.get("fiscal_period")
    if not isinstance(period, Mapping):
        return None
    year, quarter = period.get("year"), period.get("quarter")
    if not (isinstance(year, int) and not isinstance(year, bool)
            and isinstance(quarter, int) and not isinstance(quarter, bool)):
        return None
    return year * 4 + quarter


def _cohort_state(rows: list[Mapping[str, Any]]) -> str:
    """eligible_unreported | reported_noncomparable | comparable.

    ``comparable`` means the issuer REPORTED at least one metric in two
    adjacent fiscal periods (an economics-grade pair exists for that metric);
    ``reported_noncomparable`` means reported facts exist but no metric spans
    adjacent periods — REPORTED, an honest state, never a negative one. An
    issuer whose rows carry no nested ``reported`` facts is UNREPORTED
    (SP12: unreported is unknown, never "reported but degraded"), exactly as
    an identified issuer with no rows at all is.
    """
    reported_any = False
    periods_by_metric: dict[tuple[object, object], set[int]] = {}
    for _row, fact in _fact_rows(rows):
        reported_any = True
        index = _row_period_index(_row)
        if index is None:
            continue
        periods_by_metric.setdefault(
            (fact.get("metric"), fact.get("unit")), set(),
        ).add(index)
    if not reported_any:
        return "eligible_unreported"
    adjacent = any(
        right - left == 1
        for indexes in periods_by_metric.values()
        for left, right in zip(sorted(indexes), sorted(indexes)[1:])
    )
    return "comparable" if adjacent else "reported_noncomparable"


def _signed_changes(rows: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Same-metric signed differences over adjacent labelled periods, read
    from the NESTED ``row["reported"]`` facts (metric/unit/value are the
    fact's own; the period is the owning ROW's structured fiscal period).

    Original observations stay in ``reported`` VERBATIM; this adds the
    descriptive bridge only where two adjacent periods of one metric exist.
    A negative change is displayed, never dropped; incomparable units are
    not differenced (they are not folded into one denominator). Duplicate
    facts for one (period, metric, unit) — the same filing re-served under
    several alias listings — must AGREE before a difference is emitted: a
    disagreement is ambiguous, never averaged and never picked."""
    facts: dict[tuple[int, str, object], list[tuple[str, float]]] = {}
    period_of: dict[int, Mapping[str, Any] | None] = {}
    for row, fact in _fact_rows(rows):
        index = _row_period_index(row)
        metric = fact.get("metric")
        if index is None or not isinstance(metric, str) or not metric:
            continue
        value = fact.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        event_id = row.get("event_id")
        facts.setdefault((index, metric, fact.get("unit")), []).append(
            (str(event_id) if event_id is not None else "", value),
        )
        period_of.setdefault(index, row.get("fiscal_period"))

    def _agreed(entries: list[tuple[str, float]]) -> float | None:
        ordered = sorted(entries)
        return ordered[0][1] if all(v == ordered[0][1] for _, v in ordered) else None

    # Compare WITHIN one (metric, unit) series. A global key sort would
    # interleave same-period/different-metric keys and never place two
    # adjacent-period/same-metric entries next to each other whenever a row
    # serves more than one metric — the change bridge would silently vanish.
    by_metric: dict[tuple[str, object], list[int]] = {}
    for index, metric, unit in facts:
        by_metric.setdefault((metric, unit), []).append(index)
    changes: list[Mapping[str, Any]] = []
    for (metric, unit), indexes in sorted(
        by_metric.items(), key=lambda kv: (kv[0][0], str(kv[0][1])),
    ):
        ordered = sorted(indexes)
        for left, right in zip(ordered, ordered[1:]):
            if right - left != 1:
                continue
            lv = _agreed(facts[(left, metric, unit)])
            rv = _agreed(facts[(right, metric, unit)])
            if lv is None or rv is None:
                continue
            changes.append({
                "metric": metric,
                "unit": unit,
                "from_fiscal_period": period_of.get(left),
                "to_fiscal_period": period_of.get(right),
                "from_value": lv,
                "to_value": rv,
                "signed_change": rv - lv,
            })
    return changes


def _issuer_reported(rows: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """The issuer's original reported facts, verbatim, one row per fact with
    the owning event id as the lineage root. Negative values preserved."""
    out: list[Mapping[str, Any]] = []
    for row in rows:
        for fact in row.get("reported") or ():
            if not isinstance(fact, Mapping):
                continue
            entry = {
                "metric": fact.get("metric"),
                "value": fact.get("value"),
                "unit": fact.get("unit"),
                "fiscal_period": fact.get("fiscal_period"),
                "event_id": row.get("event_id"),
            }
            for optional in ("basis", "currency", "perimeter", "definition"):
                if optional in fact:
                    entry[optional] = fact[optional]
            out.append(entry)
    out.sort(key=lambda f: (
        str(f.get("fiscal_period")), str(f.get("metric")), str(f.get("event_id")),
    ))
    return out


def _unknowns(rows: list[Mapping[str, Any]]) -> list[str]:
    """The issuer's unknown inputs: every typed omission its rows carry,
    deduplicated, order-preserving. Displayed, never dropped."""
    seen: list[str] = []
    for row in rows:
        for token in row.get("omissions") or ():
            if isinstance(token, str) and token not in seen:
                seen.append(token)
    return seen


def _hhi(weights: Sequence[float]) -> float:
    """Herfindahl–Hirschman over non-negative weights (the same pure-math
    shape :mod:`engine.offexchange_venue_concentration` uses for venue
    shares; re-declared here because that module's numpy import would break
    this module's stdlib-only import law)."""
    total = sum(weights)
    if total <= 0 or not weights:
        return 0.0
    return sum((w / total) ** 2 for w in weights)


def _lineage(rows: list[Mapping[str, Any]]) -> Mapping[str, Any]:
    """``dedupe_source_roots`` families over the evidence rows — one root per
    event workspace, so N metrics from one filing are ONE lineage family."""
    from engine.leadership_rotation_context import dedupe_source_roots  # noqa: PLC0415 — lazy: keeps this module stdlib-only at import

    evidence = [
        {"id": str(row.get("event_id")), "source_roots": (f"workspace:{row.get('event_id')}",)}
        for row in rows
        if row.get("event_id") is not None
    ]
    return dedupe_source_roots(evidence)


def build_issuer_economics(
    query: Any,
    bundle: Any,
    *,
    scope: Any,
    eligible_count: int,
    alias_resolver: Callable[[str], tuple[str, ...]] | None,
    dropped: bool = False,
) -> Mapping[str, Any]:
    """Build the additive issuer-economics block for one v2 theme request.

    Parameters are owner reads the REGISTRATION SEAM performs (never this
    module): ``scope`` is a resolved
    :class:`~engine.market_ontology.semiconductor_witness_scope.WitnessScope`,
    ``eligible_count`` the DECLARED cohort size (the roster, independent of
    identity resolution), ``alias_resolver`` is
    ``IssuerMaster.securities_of_issuer`` (``None`` when the master is
    unreadable — aliases then carry the typed unknown, and CIK-based
    exclusion still removes every alias ROW the bundle served).

    Pure over mapping-shaped inputs; never raises; finite JSON by
    construction (the workspace projector already refuses non-finite facts
    with typed omissions, which land in ``unknowns``).
    """
    identities = tuple(getattr(scope, "identities", ()) or ())
    rows = _rows(bundle)
    scope_omissions = tuple(getattr(scope, "omissions", ()) or ())

    # --- per-issuer attribution over the declared cohort ------------------
    by_issuer: dict[str, list[Mapping[str, Any]]] = {}
    attribution: dict[str, str] = {}
    for identity in identities:
        issuer_id = getattr(identity, "issuer_id", None)
        cik = getattr(identity, "cik", None)
        key = str(issuer_id) if issuer_id else f"cik:{cik}"
        attribution[key] = str(cik)
        by_issuer.setdefault(key, [])
    unattributed = 0
    for row in rows:
        cik = row.get("cik")
        owner = next(
            (key for key, want in attribution.items() if _same_issuer(cik, want)),
            None,
        )
        if owner is None:
            unattributed += 1
            continue
        by_issuer[owner].append(row)

    aliases_by_issuer: dict[str, tuple[str, ...]] = {}
    aliases_unknown = False
    if alias_resolver is not None:
        for key in by_issuer:
            issuer_id = key if not key.startswith("cik:") else None
            if issuer_id is None:
                aliases_unknown = True
                continue
            try:
                aliases_by_issuer[key] = tuple(alias_resolver(issuer_id))
            except Exception:  # noqa: BLE001 — an owner refusal is a typed unknown, never a raise
                aliases_unknown = True
    elif identities:
        aliases_unknown = True

    states = {key: _cohort_state(by_issuer[key]) for key in by_issuer}
    reported = {key for key, state in states.items() if state != "eligible_unreported"}
    comparable = {key for key, state in states.items() if state == "comparable"}
    identified = len(identities)
    unknown_count = max(0, eligible_count - len(reported))

    issuers_block: list[Mapping[str, Any]] = []
    for key in sorted(by_issuer):
        identity = next(i for i in identities if (
            str(getattr(i, "issuer_id", "")) == key
            or f"cik:{getattr(i, 'cik', '')}" == key
        ))
        issuer_rows = by_issuer[key]
        issuers_block.append({
            "issuer_id": getattr(identity, "issuer_id", None),
            "cik": getattr(identity, "cik", None),
            "ticker": getattr(identity, "ticker", None),
            "company_node_id": getattr(identity, "company_node_id", None),
            "aliases": list(aliases_by_issuer.get(key, ())),
            "aliases_unknown": aliases_unknown and key not in aliases_by_issuer,
            "cohort_state": states[key],
            "row_count": len(issuer_rows),
            "reported": _issuer_reported(issuer_rows),
            "signed_changes": _signed_changes(issuer_rows),
            "unknowns": _unknowns(issuer_rows),
        })

    # --- leave-issuer-out projections (frozen-input shape) ----------------
    # Membership and weights come from the DECLARED cohort only; peer
    # measures are computed over NON-candidate rows. Nothing here reads the
    # candidate's own rows, which is exactly the SP04 invariance property.
    leave_out: dict[str, Mapping[str, Any]] = {}
    weight = 1.0 / eligible_count if eligible_count else 0.0
    for key in sorted(by_issuer):
        identity = next(i for i in identities if (
            str(getattr(i, "issuer_id", "")) == key
            or f"cik:{getattr(i, 'cik', '')}" == key
        ))
        candidate_cik = getattr(identity, "cik", None)
        peer_rows = [
            row for row in rows
            if not _same_issuer(row.get("cik"), candidate_cik)
        ]
        remaining = eligible_count - 1
        peer_states = {
            other: _cohort_state(by_issuer[other])
            for other in by_issuer if other != key
        }
        peer_reported = sum(
            1 for state in peer_states.values() if state != "eligible_unreported"
        )
        leave_out[key] = {
            "excluded_weight": weight,
            "remaining_count": remaining,
            "removed_aliases": list(aliases_by_issuer.get(key, ())),
            "renormalization": _RENORM_METHOD,
            "remaining_weight_each": (
                1.0 / remaining if remaining > 0 else None
            ),
            "concentration_hhi": _hhi([1.0] * remaining) if remaining > 0 else 0.0,
            "peer_evidence_rows": len(peer_rows),
            "peer_lineage": _lineage(peer_rows),
            "peer_reported_count": peer_reported,
            "independent_peer_support": (
                "none_singleton_cohort" if remaining <= 0
                else "declared_cohort_only"
            ),
            # The whole-cohort aggregate this block also serves contains the
            # candidate: the mediated benchmark effect, labelled, never
            # presented as independent peer confirmation.
            "mediated_benchmark": True,
        }

    limitations: list[str] = [
        "slice_scope_unowned",
        *scope_omissions,
    ]
    if aliases_unknown:
        limitations.append("issuer_aliases_unknown")
    if dropped:
        limitations.append("rights_refused_families_hidden")
    if unattributed:
        limitations.append(f"unattributed_workspace_rows:{unattributed}")

    return {
        "schema": ISSUER_ECONOMICS_SCHEMA,
        "cohort": {
            "eligible": eligible_count,
            "identified": identified,
            "reported": len(reported),
            "comparable": len(comparable),
            "unknown": unknown_count,
            "noncomparable": len(reported) - len(comparable),
            "denominator_rule": (
                "unreported is unknown; noncomparable is reported but not "
                "comparable and is not a negative result; different accounting "
                "periods, restatements and incomparable definitions do not enter "
                "one denominator"
            ),
        },
        "issuers": issuers_block,
        "leave_issuer_out": leave_out,
        "lineage": _lineage(rows),
        "concentration": {
            "method": "hhi_over_declared_cohort_equal_weights",
            "hhi": _hhi([1.0] * eligible_count) if eligible_count else 0.0,
            "effective_issuer_count": (
                float(eligible_count) if eligible_count else 0.0
            ),
        },
        "limitations": sorted(set(limitations)),
        "wording": dict(WORDING),
        "authority": dict(AUTHORITY),
    }

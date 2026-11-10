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
  never enters the same denominator; ``unknown = eligible - reported`` and
  counts that cannot satisfy ``reported + unknown = eligible`` are never
  published (the typed inconsistent form is);
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
  leave-issuer-out, under STATED equal weighting.

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
over those weights, and signed differences of same-series adjacent-period
reported facts (the NESTED ``row["reported"]`` entries; the fiscal period is
the owning row's). The fixed wording law is carried in the response: raw relative
strength is not estimated alpha; positive selection contribution is not
evidence of portfolio skill.

Purity and faults (exactly what is guaranteed)
----------------------------------------------
Purity: stdlib-only at import (the reuse import of ``dedupe_source_roots``
is lazy, inside the build function, so no consumer drags the rotation module
at import time). :func:`build_issuer_economics` performs no owner reads and
never raises over plain mapping-shaped inputs:

* a non-string or missing identity CIK is a TYPED UNKNOWN that matches no
  row — never a ``TypeError`` (``_same_issuer`` guards the identity side);
* a non-finite fact value (NaN, infinity) is not a reported number and is
  refused BY THIS MODULE'S OWN CHECK, with a typed omission — the upstream
  projector's refusal is not relied on;
* denominator inputs that cannot satisfy ``reported + unknown = eligible``
  publish the typed inconsistent form with the raw inputs and NULL derived
  counts — never counts that fail the sum.

Owner reads (witness-scope resolution, the security master) belong to the
REGISTRATION SEAM, not this module; a fault inside the seam's binding
degrades to :func:`unavailable_block` (the typed unavailable form, reason
naming the exception class only), so the query route still succeeds. What is
NOT promised: behaviour for hostile ``Mapping``/``str`` subclasses whose
``get``/``__str__``/``zfill`` run code, or for fact key fields outside the
projector's closed token contract (those facts simply never enter a bridge).
"""
from __future__ import annotations

import math
from collections.abc import Callable, Iterator, Mapping, Sequence
from typing import Any

__all__ = [
    "ISSUER_ECONOMICS_SCHEMA",
    "build_issuer_economics",
    "unavailable_block",
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

#: The concentration weighting, stated in the block (N7): the figure is
#: equal weights over the DECLARED cohort — it measures cohort size, not
#: economic concentration — and says so in one line.
_CONC_WEIGHTING = "equal_over_declared_cohort"
_CONC_NOTE = (
    "The concentration figure is equal weights over the declared cohort, so "
    "it measures cohort size, not economic concentration."
)

#: The denominator rule, stated in the block (N6): the unknown class is the
#: arithmetic difference, and the sum law is checkable by the reader.
_DENOMINATOR_RULE = (
    "unreported is unknown: unknown = eligible - reported; noncomparable is "
    "reported but not comparable and is not a negative result; different "
    "accounting periods, restatements and incomparable definitions do not "
    "enter one denominator"
)

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

#: The series-identity fields of a reported fact — the PROJECTOR'S OWN field
#: names (``workspace_projection._REPORTED_OPTIONAL_KEYS``): a bridge is
#: built only inside one (metric, unit, basis, currency, perimeter,
#: definition) series (S1).
_SERIES_FIELDS = ("metric", "unit", "basis", "currency", "perimeter", "definition")

#: Sentinel for "this field is ABSENT on the fact". Absent is NOT stated: a
#: field absent on one fact and stated on the other does not match, and no
#: bridge is built across them.
_ABSENT = object()


def unavailable_block(reason: str) -> Mapping[str, Any]:
    """The typed unavailable form a REGISTRATION-SEAM fault degrades to (N1):
    the schema, the unavailable state, the ``reason`` (exception CLASS only —
    never message text, which can carry paths) and the all-false authority
    ceiling. No counts, no ranking, finite JSON."""
    return {
        "schema": ISSUER_ECONOMICS_SCHEMA,
        "state": "issuer_economics_unavailable",
        "reason": reason,
        "authority": dict(AUTHORITY),
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
    """Equality of two CIKs in their TEN-DIGIT ZERO-PADDED comparison form
    (N5: a row served as ``"1"`` belongs to identity ``"0000000001"``), bound
    on plain-``str`` equality. A non-string on EITHER side — including a
    missing identity CIK — matches nothing: a TYPED UNKNOWN, never a
    ``TypeError`` (N1)."""
    if not isinstance(row_cik, str) or not isinstance(identity_cik, str):
        return False
    return str.__eq__(identity_cik.zfill(10), row_cik.zfill(10)) is True


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


def _reported_number(value: object) -> bool:
    """A REPORTED NUMBER: a non-bool ``int``, or a FINITE ``float``. NaN and
    infinity are refused HERE, by this module's own check (N3) — the
    upstream projector's refusal is not relied on, and a non-finite value
    never enters a bridge or the served facts, so the block is finite JSON."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(value) if isinstance(value, float) else True


def _series_key(fact: Mapping[str, Any]) -> tuple[object, ...] | None:
    """The bridge identity of a fact (S1): the projector's own field names —
    (metric, unit, basis, currency, perimeter, definition) — with ABSENT
    distinct from stated. GAAP is never subtracted from non-GAAP, a segment
    from the consolidated company, TWD from USD, and a fact that merely
    omits a field never bridges against one that states it. ``None`` when a
    stated field is unhashable (outside the projector's token contract):
    such a fact never enters a bridge."""
    parts = tuple(
        _ABSENT if field not in fact else fact[field]
        for field in _SERIES_FIELDS
    )
    try:
        hash(parts)
    except TypeError:
        return None
    return parts


def _series_sort_key(series: tuple[object, ...]) -> tuple[tuple[int, str], ...]:
    """A deterministic display order over series keys: absent < stated-None
    < stated-token, each compared as text."""
    def rank(part: object) -> tuple[int, str]:
        if part is _ABSENT:
            return (0, "")
        if part is None:
            return (1, "")
        return (2, str(part))

    return tuple(rank(part) for part in series)


def _issuer_state_and_changes(
    rows: list[Mapping[str, Any]],
) -> tuple[str, list[Mapping[str, Any]]]:
    """``eligible_unreported | reported_noncomparable | comparable`` AND the
    issuer's signed changes — ONE rule, in one place (S2): an issuer is
    ``comparable`` exactly when :func:`_signed_changes` emits at least one
    change for it, never on a mere inspection of shapes. Reported facts with
    no emitted change are ``reported_noncomparable`` — REPORTED, an honest
    state, never a negative one. An issuer whose rows carry no nested
    ``reported`` facts is UNREPORTED (SP12: unreported is unknown, never
    "reported but degraded"), exactly as an identified issuer with no rows
    at all is."""
    changes = _signed_changes(rows)
    if changes:
        return "comparable", changes
    if any(True for _ in _fact_rows(rows)):
        return "reported_noncomparable", changes
    return "eligible_unreported", changes


def _signed_changes(rows: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Same-series signed differences over adjacent labelled periods, read
    from the NESTED ``row["reported"]`` facts (metric/unit/value are the
    fact's own; the period is the owning ROW's structured fiscal period).

    A SERIES is one (metric, unit, basis, currency, perimeter, definition)
    key — the projector's own field names (S1) — so the bridge never
    subtracts across accounting basis, currency, reporting perimeter or
    definition, and never across a field one fact states and the other
    omits. Original observations stay in ``reported`` VERBATIM; this adds
    the descriptive bridge only where two ADJACENT periods (index step
    exactly 1 — a missing quarter is a gap, never a span) of one series
    exist. A negative change is displayed, never dropped; incomparable
    units are not differenced (they are not folded into one denominator).
    Duplicate facts for one (period, series) — the same filing re-served
    under several alias listings — must AGREE before a difference is
    emitted: a disagreement is ambiguous, never averaged and never picked.
    A non-finite value is not a reported number and never enters (N3)."""
    facts: dict[tuple[object, ...], list[tuple[str, float]]] = {}
    period_of: dict[int, Mapping[str, Any] | None] = {}
    indexes_by_series: dict[tuple[object, ...], set[int]] = {}
    for row, fact in _fact_rows(rows):
        index = _row_period_index(row)
        metric = fact.get("metric")
        if index is None or not isinstance(metric, str) or not metric:
            continue
        value = fact.get("value")
        if not _reported_number(value):
            continue
        series = _series_key(fact)
        if series is None:
            continue
        event_id = row.get("event_id")
        facts.setdefault((index, *series), []).append(
            (str(event_id) if event_id is not None else "", value),
        )
        indexes_by_series.setdefault(series, set()).add(index)
        period_of.setdefault(index, row.get("fiscal_period"))

    def _agreed(entries: list[tuple[str, float]]) -> float | None:
        ordered = sorted(entries)
        return ordered[0][1] if all(v == ordered[0][1] for _, v in ordered) else None

    # Compare WITHIN one series. A global key sort would interleave
    # same-period/different-metric keys and never place two
    # adjacent-period/same-series entries next to each other whenever a row
    # serves more than one metric — the change bridge would silently vanish.
    changes: list[Mapping[str, Any]] = []
    for series in sorted(indexes_by_series, key=_series_sort_key):
        ordered = sorted(indexes_by_series[series])
        for left, right in zip(ordered, ordered[1:]):
            if right - left != 1:
                continue
            lv = _agreed(facts[(left, *series)])
            rv = _agreed(facts[(right, *series)])
            if lv is None or rv is None:
                continue
            changes.append({
                "metric": series[0],
                "unit": series[1],
                "from_fiscal_period": period_of.get(left),
                "to_fiscal_period": period_of.get(right),
                "from_value": lv,
                "to_value": rv,
                "signed_change": rv - lv,
            })
    return changes


def _issuer_reported(
    rows: list[Mapping[str, Any]],
) -> tuple[list[Mapping[str, Any]], list[str]]:
    """The issuer's original reported facts, verbatim, one row per fact with
    the owning event id as the lineage root. Negative values preserved.
    A fact whose value is not a reported NUMBER (NaN, infinity — N3) is not
    a reported fact: it is refused here, by this module's own check, and
    surfaces as a typed ``reported_non_finite:<metric>`` omission token
    instead — displayed, never silently dropped, and never non-finite JSON."""
    out: list[Mapping[str, Any]] = []
    nonfinite: list[str] = []
    for row in rows:
        for fact in row.get("reported") or ():
            if not isinstance(fact, Mapping):
                continue
            metric = fact.get("metric")
            value = fact.get("value")
            # N3: ONLY a non-finite float is refused (it cannot be finite
            # JSON); a string or None value is out of the numeric contract
            # but is still finite JSON and stays VERBATIM, as always.
            if isinstance(value, float) and not math.isfinite(value):
                token_metric = metric if isinstance(metric, str) and metric else "<unkeyed>"
                nonfinite.append(f"reported_non_finite:{token_metric}")
                continue
            entry = {
                "metric": metric,
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
    return out, nonfinite


def _unknowns(rows: list[Mapping[str, Any]]) -> list[str]:
    """The issuer's unknown inputs: every typed omission its rows carry,
    deduplicated, order-preserving. Displayed, never dropped."""
    seen: list[str] = []
    for row in rows:
        for token in row.get("omissions") or ():
            if isinstance(token, str) and token not in seen:
                seen.append(token)
    return seen


def _ordered_union(*groups: list[str]) -> list[str]:
    """Order-preserving dedupe across token groups (row omissions first,
    then this module's own typed refusals)."""
    seen: list[str] = []
    for group in groups:
        for token in group:
            if token not in seen:
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
    event workspace, so N metrics from one filing are ONE lineage family.

    N4: the family key is the event id with surrounding whitespace STRIPPED
    (no case folding — ``ACC-0001`` and ``acc-0001`` stay distinct). A row
    with facts but no event id roots no family: it is counted in the stated
    ``unrooted_rows``, never silently absorbed as zero families. The rule is
    stated in the block: families are DISTINCT EVENT IDS — two workspaces
    citing one filing under different ids are not detected as one family."""
    from engine.leadership_rotation_context import dedupe_source_roots  # noqa: PLC0415 — lazy: keeps this module stdlib-only at import

    evidence: list[dict[str, Any]] = []
    unrooted = 0
    for row in rows:
        event_id = row.get("event_id")
        if event_id is None or (isinstance(event_id, str) and not event_id.strip()):
            unrooted += 1
            continue
        key = event_id.strip() if isinstance(event_id, str) else str(event_id)
        evidence.append({"id": key, "source_roots": (f"workspace:{key}",)})
    out = dict(dedupe_source_roots(evidence))
    out["unrooted_rows"] = unrooted
    out["family_rule"] = (
        "families are distinct event ids; two workspaces citing one filing "
        "under different ids are not detected"
    )
    return out


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

    Guarantees (see the module docstring's fault law): no owner reads, never
    a raise over plain mapping-shaped inputs, finite JSON by this module's
    own check, and denominator counts that always satisfy
    ``reported + unknown = eligible`` — or the typed inconsistent form that
    says they cannot."""
    identities = tuple(getattr(scope, "identities", ()) or ())
    rows = _rows(bundle)
    scope_omissions = tuple(getattr(scope, "omissions", ()) or ())

    # --- per-issuer attribution over the declared cohort ------------------
    # The attribution value is the identity's RAW cik object: ``_same_issuer``
    # requires a real str on the identity side, so a missing/non-string CIK
    # is a typed unknown that matches no row (N1) — never str()-coerced into
    # matching a row that literally carries "None".
    by_issuer: dict[str, list[Mapping[str, Any]]] = {}
    attribution: dict[str, object] = {}
    identity_cik_not_string = 0
    for identity in identities:
        issuer_id = getattr(identity, "issuer_id", None)
        cik = getattr(identity, "cik", None)
        key = str(issuer_id) if issuer_id else f"cik:{cik}"
        attribution[key] = cik
        if not isinstance(cik, str):
            identity_cik_not_string += 1
        by_issuer.setdefault(key, [])
    owners: list[str | None] = []
    unattributed = 0
    for row in rows:
        row_cik = row.get("cik")
        owner = next(
            (key for key, want in attribution.items() if _same_issuer(row_cik, want)),
            None,
        )
        owners.append(owner)
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

    states: dict[str, str] = {}
    changes_by_key: dict[str, list[Mapping[str, Any]]] = {}
    for key in by_issuer:
        state, changes = _issuer_state_and_changes(by_issuer[key])
        states[key] = state
        changes_by_key[key] = changes
    reported = {key for key, state in states.items() if state != "eligible_unreported"}
    comparable = {key for key, state in states.items() if state == "comparable"}
    # N6: one issuer per distinct key — two identities sharing one issuer id
    # are ONE issuer, counted once everywhere.
    identified = len(by_issuer)
    reported_total = len(reported)

    issuers_block: list[Mapping[str, Any]] = []
    for key in sorted(by_issuer):
        identity = next(i for i in identities if (
            str(getattr(i, "issuer_id", "")) == key
            or f"cik:{getattr(i, 'cik', '')}" == key
        ))
        issuer_rows = by_issuer[key]
        reported_facts, nonfinite_tokens = _issuer_reported(issuer_rows)
        issuers_block.append({
            "issuer_id": getattr(identity, "issuer_id", None),
            "cik": getattr(identity, "cik", None),
            "ticker": getattr(identity, "ticker", None),
            "company_node_id": getattr(identity, "company_node_id", None),
            "aliases": list(aliases_by_issuer.get(key, ())),
            "aliases_unknown": aliases_unknown and key not in aliases_by_issuer,
            "cohort_state": states[key],
            "row_count": len(issuer_rows),
            "reported": reported_facts,
            "signed_changes": changes_by_key[key],
            "unknowns": _ordered_union(_unknowns(issuer_rows), nonfinite_tokens),
        })

    limitations: list[str] = [
        "slice_scope_unowned",
        *scope_omissions,
    ]
    if aliases_unknown:
        limitations.append("issuer_aliases_unknown")
    if dropped:
        limitations.append("rights_refused_families_hidden")
    if identity_cik_not_string:
        limitations.append(f"identity_cik_not_string:{identity_cik_not_string}")
    if unattributed:
        # N5: rows belonging to NO cohort member are not peers of anyone —
        # counted separately and stated, never folded into peer evidence.
        limitations.append(f"unattributed_workspace_rows:{unattributed}")

    # --- N6: the counts must add up or say they cannot ---------------------
    inconsistent: str | None = None
    if eligible_count < 0:
        inconsistent = "eligible_is_negative"
    elif reported_total > eligible_count:
        inconsistent = "reported_exceeds_eligible"
    if inconsistent is not None:
        return {
            "schema": ISSUER_ECONOMICS_SCHEMA,
            "state": "cohort_counts_inconsistent",
            "cohort": {
                # raw inputs, stated as received
                "eligible": eligible_count,
                "identified": identified,
                "reported": reported_total,
                # derived counts: NULL, never a sum that fails
                "unknown": None,
                "comparable": None,
                "noncomparable": None,
                "denominator_rule": _DENOMINATOR_RULE,
                "inconsistency": inconsistent,
            },
            "issuers": issuers_block,
            "leave_issuer_out": None,
            "lineage": _lineage(rows),
            "concentration": {
                "state": "unavailable_cohort_counts_inconsistent",
                "weighting": _CONC_WEIGHTING,
                "weighting_note": _CONC_NOTE,
            },
            "limitations": sorted(set(
                limitations + [f"cohort_counts_inconsistent:{inconsistent}"],
            )),
            "wording": dict(WORDING),
            "authority": dict(AUTHORITY),
        }

    # --- leave-issuer-out projections (frozen-input shape) ----------------
    # Membership and weights come from the DECLARED cohort only; peer
    # measures are computed over rows attributed to OTHER cohort members
    # (N5) — never "every row whose CIK differs", so a row belonging to no
    # cohort member is not peer evidence. Nothing here reads the candidate's
    # own rows, which is exactly the SP04 invariance property.
    leave_out: dict[str, Mapping[str, Any]] = {}
    weight = 1.0 / eligible_count if eligible_count > 0 else 0.0
    for key in sorted(by_issuer):
        peer_rows = [
            row for row, owner in zip(rows, owners)
            if owner is not None and owner != key
        ]
        remaining = eligible_count - 1
        peer_reported = sum(
            1 for other in by_issuer
            if other != key and states[other] != "eligible_unreported"
        )
        leave_out[key] = {
            "excluded_weight": weight,
            "remaining_count": max(remaining, 0),
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

    # --- concentration (N7): arithmetic kept, weighting STATED ------------
    if eligible_count > 0:
        concentration: Mapping[str, Any] = {
            "method": "hhi_over_declared_cohort_equal_weights",
            "weighting": _CONC_WEIGHTING,
            "weighting_note": _CONC_NOTE,
            "hhi": _hhi([1.0] * eligible_count),
            "effective_issuer_count": float(eligible_count),
        }
    else:
        concentration = {
            "state": "unavailable_eligible_not_positive",
            "weighting": _CONC_WEIGHTING,
            "weighting_note": _CONC_NOTE,
        }

    return {
        "schema": ISSUER_ECONOMICS_SCHEMA,
        "cohort": {
            "eligible": eligible_count,
            "identified": identified,
            "reported": reported_total,
            "comparable": len(comparable),
            "unknown": eligible_count - reported_total,
            "noncomparable": reported_total - len(comparable),
            "denominator_rule": _DENOMINATOR_RULE,
        },
        "issuers": issuers_block,
        "leave_issuer_out": leave_out,
        "lineage": _lineage(rows),
        "concentration": concentration,
        "limitations": sorted(set(limitations)),
        "wording": dict(WORDING),
        "authority": dict(AUTHORITY),
    }

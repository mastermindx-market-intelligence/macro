"""Reconcile earnings-release figures against the FILED statement packet.

A29: *retain issuer definition/version and reconciliation; do not splice unlike
histories*.  Nothing links the release engine's ``ReleaseFigureSet`` to the FIF
packet today, so nothing can state whether the number the issuer publicized in
its Exhibit 99.1 agrees with the number it filed in XBRL.  This module states
exactly that, per concept, and nothing more.

It is PURE and CONTEXT-ONLY:

* it never edits the release side, never edits the packet side, and never
  overwrites a filed value — both inputs are read-only mappings;
* it never merges a non-GAAP figure into a GAAP series: a non-GAAP figure is
  ``non_gaap_retained`` with its label kept verbatim and no filed value, no
  delta, no tolerance, no filed cell ids compared against;
* it never computes a filed ratio to compare against a released margin
  (``derived_ratio_not_compared``);
* output carries strings only — no floats — so a reconciled number cannot lose
  its exactness by being serialized.

Decision order for one figure (first match wins):

1. margin concepts (``gross_margin_pct``, ``operating_margin_pct``)
   → ``derived_ratio_not_compared``;
2. guidance/outlook figures → ``guidance_context_only`` (how ``figures.py``
   names them: the ``guidance_*`` concept stems, ``figures.py`` roster lines
   ``guidance_revenue_low``/``guidance_revenue_high``, and the guidance
   sentence vocabulary ``expect|guidance|outlook|anticipat|forecast|guiding``);
3. concepts outside the frozen map → ``unmapped_concept`` (reported, never
   compared);
4. any basis other than the figures module's GAAP name (``Basis.GAAP.value ==
   "gaap"``, ``figures.py`` ``Basis``) → ``non_gaap_retained``;
5. period length class unknown → ``period_length_unknown``;
6. no candidate cell → ``no_packet_cell``;
7. matching cells disagree with each other → ``ambiguous_filed_cell``;
8. the matching cell carries no value → ``packet_cell_without_value``;
9. the matching cell's value is not a finite decimal →
   ``filed_value_unparseable``;
10. release units unrecognized → ``unit_unrecognized``;
11. cell unit shape/currency wrong → ``unit_mismatch`` (a cell unit currency
   may carry a leading ``iso4217:`` namespace: ``iso4217:USD`` equals ``USD``);
12. the release's displayed precision is held as no accepted literal →
   ``display_precision_unknown`` (the pinned per-share tolerance reads no
   displayed precision);
13. otherwise ``agrees`` / ``differs``.  Tolerance is half of one unit of the
   release's displayed precision: ``0.5 * scale`` at zero displayed decimals
   (the packet's millions example: 500,000), tightened by the decimals the
   release shows — a ``94.93``-billions display is precise to 0.005 billions,
   so a 100,000,000 filed gap DIFFERS.  Per-share tolerance is pinned flat at
   0.005.

Mapped metric ids were read out of
``config/fundamental_forensics/metrics/v1/metric_catalog.yaml`` (``revenue``,
``gross_profit``, ``operating_income_loss``, ``net_income_loss``,
``basic_earnings_per_share``, ``diluted_earnings_per_share``); the test module
pins that membership so a catalog rename cannot pass silently.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
import re
from typing import Any, Mapping, Sequence

from engine.earnings_release.binding import ReleaseEvent
from engine.earnings_release.figures import (
    _SCALE_FACTOR,
    Basis,
    ReleaseFigure,
    ReleaseFigureSet,
    TypedAbsence,
)
from engine.fundamental_forensics.financial_intelligence_packet import all_packet_cells

SCHEMA_ID = "fif_release_reconciliation.v1"
_AUTHORITY = {"class": "context_only", "display_only": True}

# Frozen: release concept -> filed metric_id.  No other concept is compared.
CONCEPT_TO_METRIC: Mapping[str, str] = {
    "revenue": "revenue",
    "gross_profit": "gross_profit",
    "operating_income": "operating_income_loss",
    "net_income": "net_income_loss",
    "eps_basic": "basic_earnings_per_share",
    "eps_diluted": "diluted_earnings_per_share",
}

# Released margins are derived ratios; a filed counterpart would itself be a
# computation, and comparing two computations is not reconciliation.
_RATIO_CONCEPTS = frozenset({"gross_margin_pct", "operating_margin_pct"})
_PER_SHARE_CONCEPTS = frozenset({"eps_basic", "eps_diluted"})

# The only basis names the figures module mints are Basis.GAAP.value ("gaap")
# and Basis.NON_GAAP.value ("non_gaap"); everything else is retained, never
# compared, never spliced.
_COMPARED_BASIS = Basis.GAAP.value

_KNOWN_RELEASE_UNITS = frozenset(_SCALE_FACTOR) | {"per_share"}

# Guidance naming, read off figures.py: the guidance concept stems plus the
# guidance sentence vocabulary (_GUIDANCE_SENTENCE_RE, figures.py).
_GUIDANCE_CONCEPT_PREFIX = "guidance_"
_GUIDANCE_TEXT_RE = re.compile(
    r"\b(?:expect\w*|guidance|outlook|anticipat\w*|forecast\w*|guiding)\b", re.I
)

# Length classes for the period label, and the filed-cell day windows they
# admit (91 ± 20 / 365 ± 20).
_QUARTER_LABEL_RE = re.compile(
    r"\bQ[1-4]\b|\bquarter\b|three\s+months?|13\s+weeks?|第.{0,6}季度", re.I
)
_ANNUAL_LABEL_RE = re.compile(
    r"\bfull\s+year\b|\bfiscal\s+year\b|twelve\s+months?|5[23]\s+weeks?|\bFY\b|年度", re.I
)
_LENGTH_WINDOW = {"quarter": (71, 111), "annual": (345, 385)}

_PER_SHARE_TOLERANCE = Decimal("0.005")
_HALF = Decimal("0.5")
_DISPLAY_NUMERIC_RE = re.compile(r"\A-?\d+(?:\.\d+)?\Z")


def _displayed_decimals(figure: ReleaseFigure) -> int | None:
    """Decimal places the release itself shows for this figure.

    The receipt's ``value_text`` is the literal as typeset — ``94,930`` shows
    zero decimals even though the parsed float's repr adds ``.0`` — and it is
    the ONLY display of record.  When it is missing, or is not the accepted
    literal form (``94,930 (1)`` carries a footnote marker), the precision is
    unknown and the caller reports ``display_precision_unknown``; decimals
    are never guessed from the parsed float's repr.
    """
    text = ""
    if figure.receipt is not None:
        text = str(figure.receipt.value_text or "").strip().rstrip("%").replace(",", "")
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1]
    if text and _DISPLAY_NUMERIC_RE.match(text):
        return len(text.partition(".")[2])
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Inputs
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ReleaseInput:
    """One release event's figures, addressed for reconciliation."""

    event_key: str
    report_date: str          # ISO date
    accession: str | None     # the filing the release is bound to, if any
    figure_set: ReleaseFigureSet
    company_event_id: str | None = None


def release_input_from_event(
    event: ReleaseEvent, figure_set: ReleaseFigureSet
) -> ReleaseInput:
    """Address a real ``ReleaseEvent``'s figures for reconciliation.

    ``event_key`` and ``report_date`` are the event's own properties; the
    binding accession is the CURRENT revision's filing (an amendment corrects
    the event, and the current filing is the one whose packet applies).
    ``ReleaseEvent`` declares no company_event_id, so it stays None.
    """
    return ReleaseInput(
        event_key=event.event_key,
        report_date=event.report_date,
        accession=event.current.filing_key.accession if event.revisions else None,
        figure_set=figure_set,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Output
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ReleaseReconciliation:
    """The reconciliation of one release event against one filed packet."""

    event_key: str
    report_date: str
    release_accession: str | None
    packet_accessions: tuple[str, ...]
    rows: tuple[Mapping[str, Any], ...]
    schema: str = SCHEMA_ID
    authority: Mapping[str, Any] = field(default_factory=lambda: dict(_AUTHORITY))

    def to_dict(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for row in self.rows:
            counts[row["outcome"]] = counts.get(row["outcome"], 0) + 1
        return {
            "schema": self.schema,
            "authority": dict(self.authority),
            "event_key": self.event_key,
            "report_date": self.report_date,
            "release_accession": self.release_accession,
            "packet_accessions": list(self.packet_accessions),
            "rows": [dict(row) for row in self.rows],
            "outcome_counts": {key: counts[key] for key in sorted(counts)},
        }


# ─────────────────────────────────────────────────────────────────────────────
# Small deterministic readers
# ─────────────────────────────────────────────────────────────────────────────

def _dec_str(value: Decimal) -> str:
    """Plain decimal string: no exponent, no trailing zeros, no float."""
    return format(value.normalize(), "f")


def _period_length_class(period_label: str) -> str | None:
    """Classify a release period label as ``quarter``/``annual``, else None.

    Never guessed: a label outside both vocabularies (six months, an unlabeled
    column) has no length class and the figure is never compared.
    """
    if _QUARTER_LABEL_RE.search(period_label):
        return "quarter"
    if _ANNUAL_LABEL_RE.search(period_label):
        return "annual"
    return None


def _is_guidance(figure: ReleaseFigure) -> bool:
    if figure.concept.startswith(_GUIDANCE_CONCEPT_PREFIX):
        return True
    return bool(
        _GUIDANCE_TEXT_RE.search(figure.label)
        or _GUIDANCE_TEXT_RE.search(figure.period_label)
    )


def _cell_unit_role(unit: object) -> str:
    text = str(unit if unit is not None else "").strip()
    if not text:
        return "absent"
    lowered = text.lower()
    if "/share" in lowered or "/shares" in lowered:
        return "per_share"
    if "/" in text:
        return "ratio"
    return "plain"


def _cell_currency(unit: object) -> str | None:
    text = str(unit if unit is not None else "").strip()
    if not text:
        return None
    prefix = text.split("/", 1)[0].strip()
    # A leading iso4217: namespace is the same currency: iso4217:USD == USD.
    if prefix[:8].lower() == "iso4217:":
        prefix = prefix[8:].strip()
    return prefix.upper() or None


def _candidate_cells(
    packet: Mapping[str, Any],
    *,
    metric_id: str,
    period_end: str,
    length_class: str,
) -> list[dict[str, Any]]:
    """Cells that could be the filed counterpart of one released figure.

    Same metric, a duration, the same period end, a period length inside the
    label's class window, and a start (an instant-width cell has no length and
    is not a candidate).
    """
    low, high = _LENGTH_WINDOW[length_class]
    matches: list[dict[str, Any]] = []
    for cell in all_packet_cells(packet):
        if cell.get("metric_id") != metric_id:
            continue
        period = cell.get("period") or {}
        if period.get("kind") != "duration" or period.get("end") != period_end:
            continue
        start = period.get("start")
        if not start:
            continue
        try:
            days = (date.fromisoformat(period["end"]) - date.fromisoformat(start)).days
        except (TypeError, ValueError):
            continue
        if low <= days <= high:
            matches.append(cell)
    return sorted(matches, key=lambda cell: cell["cell_id"])


def _filed_value_key(cell: Mapping[str, Any]) -> str:
    """Comparable identity of a filed cell for ambiguity detection.

    ``94930000000`` and ``94930000000.0`` are the same filed number; a cell
    without a value is keyed by its ``non_value_state`` (or its absence), so
    two matching valueless cells with different states never collapse to one
    picked cell; a value that is not a decimal string is its own key.
    """
    if cell.get("value") is None or cell.get("non_value_state"):
        return f"<no-value:{cell.get('non_value_state')!r}>"
    try:
        return _dec_str(Decimal(str(cell["value"])))
    except ArithmeticError:
        return f"<unparseable:{cell['value']!r}>"


def _filed_decimal(value: object) -> Decimal | None:
    """Parse a filed cell value, or None when it is not a finite decimal.

    A value like ``n/a`` is a typed finding (``filed_value_unparseable``),
    never a raw ``InvalidOperation``; NaN and infinities parse as Decimals
    but poison every delta, so they are unparseable here too.
    """
    try:
        parsed = Decimal(str(value))
    except ArithmeticError:
        return None
    return parsed if parsed.is_finite() else None


def _released_scale(figure: ReleaseFigure) -> Decimal:
    if figure.scale_factor is not None:
        return Decimal(str(figure.scale_factor))
    if figure.units in _SCALE_FACTOR:
        return Decimal(str(_SCALE_FACTOR[figure.units]))
    return Decimal(1)


def _sort_key(row: Mapping[str, Any]) -> tuple[str, str, str]:
    return (str(row["concept"]), row["basis"] or "", row["period_end"] or "")


# ─────────────────────────────────────────────────────────────────────────────
# Row builders
# ─────────────────────────────────────────────────────────────────────────────

def _row_skeleton(figure: ReleaseFigure, *, metric_id: str | None) -> dict[str, Any]:
    return {
        "concept": figure.concept,
        "metric_id": metric_id,
        "basis": figure.basis,
        "label": figure.label,
        "period_end": figure.period_end,
        "period_length_class": _period_length_class(figure.period_label),
        "outcome": None,
        "released_value": None,
        "filed_value": None,
        "delta": None,
        "tolerance": None,
        "filed_cell_ids": [],
        "receipt": figure.receipt.to_dict() if figure.receipt is not None else None,
    }


def _retained_row(figure: ReleaseFigure, outcome: str) -> dict[str, Any]:
    """A row for a figure that is reported but never compared.

    ``metric_id`` names the filed series the figure is RETAINED beside (and
    must never be merged into); margins, guidance and unmapped concepts have
    no mapped metric and carry None.
    """
    row = _row_skeleton(figure, metric_id=CONCEPT_TO_METRIC.get(figure.concept))
    row["outcome"] = outcome
    return row


def _compare_row(
    figure: ReleaseFigure, metric_id: str, candidates: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    row = _row_skeleton(figure, metric_id=metric_id)
    cell_ids = [cell["cell_id"] for cell in candidates]
    representative = candidates[0]

    # Sole/collapsed cell with no filed value: the state is the finding.
    if representative.get("value") is None or representative.get("non_value_state"):
        row["outcome"] = "packet_cell_without_value"
        row["filed_cell_ids"] = cell_ids
        row["non_value_state"] = representative.get("non_value_state")
        return row

    filed = _filed_decimal(representative.get("value"))
    if filed is None:
        row["outcome"] = "filed_value_unparseable"
        row["filed_cell_ids"] = cell_ids
        return row

    if figure.units not in _KNOWN_RELEASE_UNITS:
        row["outcome"] = "unit_unrecognized"
        row["filed_cell_ids"] = cell_ids
        row["filed_value"] = _dec_str(filed)
        return row

    # Unit shape: per-share concepts need a per-share cell unit; monetary
    # concepts need a slash-free currency unit.
    role = _cell_unit_role(representative.get("unit"))
    wants_per_share = figure.concept in _PER_SHARE_CONCEPTS
    unit_ok = role == "per_share" if wants_per_share else role == "plain"
    currency_ok = True
    if figure.currency is not None:
        cell_currency = _cell_currency(representative.get("unit"))
        currency_ok = cell_currency is not None and cell_currency == figure.currency.upper()
    if not unit_ok or not currency_ok:
        row["outcome"] = "unit_mismatch"
        row["filed_cell_ids"] = cell_ids
        row["filed_value"] = _dec_str(filed)
        return row

    scale = _released_scale(figure)
    released = Decimal(repr(figure.value)) * scale
    if wants_per_share:
        # Pinned flat by the spec for per-share amounts.
        tolerance = _PER_SHARE_TOLERANCE
    else:
        decimals = _displayed_decimals(figure)
        if decimals is None:
            # No accepted literal: the displayed precision is unknown, so no
            # tolerance is minted and no verdict is stated.  The two values
            # remain on the row as observed facts.
            row["outcome"] = "display_precision_unknown"
            row["filed_cell_ids"] = cell_ids
            row["released_value"] = _dec_str(released)
            row["filed_value"] = _dec_str(filed)
            return row
        # Half of one unit of the release's DISPLAYED precision: 0.5 * scale
        # for a whole-unit display (the spec's millions example: 500,000),
        # tightened by the decimals the release actually shows — a 94.93
        # billions display is precise to 0.005 billions, and a 100,000,000
        # filed gap on that display DIFFERS.
        tolerance = scale * _HALF * Decimal(10) ** (-decimals)
    row["released_value"] = _dec_str(released)
    row["filed_value"] = _dec_str(filed)
    row["tolerance"] = _dec_str(tolerance)
    row["filed_cell_ids"] = cell_ids
    delta = released - filed
    row["delta"] = _dec_str(delta)
    row["outcome"] = "agrees" if abs(delta) <= tolerance else "differs"
    return row


def _figure_row(figure: ReleaseFigure, packet: Mapping[str, Any]) -> dict[str, Any]:
    if figure.concept in _RATIO_CONCEPTS:
        return _retained_row(figure, "derived_ratio_not_compared")
    if _is_guidance(figure):
        return _retained_row(figure, "guidance_context_only")
    metric_id = CONCEPT_TO_METRIC.get(figure.concept)
    if metric_id is None:
        return _retained_row(figure, "unmapped_concept")
    if figure.basis != _COMPARED_BASIS:
        return _retained_row(figure, "non_gaap_retained")

    length_class = _period_length_class(figure.period_label)
    if length_class is None:
        row = _row_skeleton(figure, metric_id=metric_id)
        row["outcome"] = "period_length_unknown"
        return row

    candidates = _candidate_cells(
        packet,
        metric_id=metric_id,
        period_end=figure.period_end,
        length_class=length_class,
    )
    if not candidates:
        row = _row_skeleton(figure, metric_id=metric_id)
        row["outcome"] = "no_packet_cell"
        return row
    values = {
        _filed_value_key(cell) for cell in candidates
    }
    if len(values) > 1:
        row = _row_skeleton(figure, metric_id=metric_id)
        row["outcome"] = "ambiguous_filed_cell"
        row["filed_cell_ids"] = [cell["cell_id"] for cell in candidates]
        return row
    return _compare_row(figure, metric_id, candidates)


def _absence_row(absence: TypedAbsence) -> dict[str, Any]:
    return {
        "concept": absence.concept,
        "metric_id": CONCEPT_TO_METRIC.get(absence.concept),
        "basis": None,
        "label": absence.label,
        "period_end": None,
        "period_length_class": None,
        "outcome": "release_absence",
        "released_value": None,
        "filed_value": None,
        "delta": None,
        "tolerance": None,
        "filed_cell_ids": [],
        "receipt": None,
        "reason": absence.reason,
        "detail": absence.detail,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Reconciliation
# ─────────────────────────────────────────────────────────────────────────────

def reconcile_release(
    release: ReleaseInput, packet: Mapping[str, Any]
) -> ReleaseReconciliation:
    """State, per concept, whether the released number agrees with the filed one.

    Reads both sides; edits neither.  Every row is context: nothing here ranks,
    gates, sizes or escalates, and no row authorizes overwriting a filed value.
    """
    rows: list[dict[str, Any]] = [
        _figure_row(figure, packet) for figure in release.figure_set.figures
    ]
    rows.extend(_absence_row(absence) for absence in release.figure_set.absences)
    rows.sort(key=_sort_key)
    packet_accessions = sorted({
        str(cell["accession"])
        for cell in all_packet_cells(packet)
        if cell.get("accession")
    })
    return ReleaseReconciliation(
        event_key=release.event_key,
        report_date=release.report_date,
        release_accession=release.accession,
        packet_accessions=tuple(packet_accessions),
        rows=tuple(rows),
    )


# ─────────────────────────────────────────────────────────────────────────────
# A29 series (no splicing)
# ─────────────────────────────────────────────────────────────────────────────

def _label_key(label: object) -> str:
    return " ".join(str(label if label is not None else "").split()).casefold()


def _label_set_transitions(
    previous: frozenset[str], current: frozenset[str]
) -> list[tuple[str | None, str | None]]:
    """Label-key pairs that express one set change, deterministically.

    Removed and added labels pair up index-wise in sorted order; an uneven
    side leaves a ``None`` beside the orphan, so a pure addition or removal
    is still one retained change.
    """
    removed = sorted(previous - current)
    added = sorted(current - previous)
    return [
        (
            removed[index] if index < len(removed) else None,
            added[index] if index < len(added) else None,
        )
        for index in range(max(len(removed), len(added)))
    ]


def build_release_series(
    reconciliations: Sequence[ReleaseReconciliation],
) -> dict[str, Any]:
    """Group reconciled rows into issuer-defined series, never splicing.

    The series key is ``(concept, basis, label_key, period_length_class)``:
    a relabel under the same concept and basis starts a NEW series, rows
    with a different basis or label never share a list with it, and a
    release that reports both a quarter and a full-year column under one
    label and ``period_end`` yields one series per period length — the two
    columns never share a point list.  A label that reverts to an
    already-seen spelling rejoins that spelling's series, and the return is
    itself recorded as a definition change: A29 retains every definition
    change, including the return to a definition used before.  Definition
    changes compare the SET of labels one event carries for one
    ``(concept, basis, period_length_class)`` pair against the previous
    event that reported that pair, so two labels inside one event never
    record a change against each other, in any figure order.
    ``release_absence`` rows carry no released number and form no series.
    """
    ordered = sorted(reconciliations, key=lambda item: (item.report_date, item.event_key))
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    previous_sets: dict[tuple[str, str, str], frozenset[str]] = {}
    verbatim: dict[str, str] = {}
    changes: list[dict[str, Any]] = []

    for reconciliation in ordered:
        event_labels: dict[tuple[str, str, str], set[str]] = {}
        for row in reconciliation.rows:
            if row["outcome"] == "release_absence":
                continue
            concept = str(row["concept"])
            basis = row["basis"] or ""
            label_key = _label_key(row["label"])
            length_class = row["period_length_class"] or ""
            verbatim.setdefault(label_key, str(row["label"]))
            grouped.setdefault((concept, basis, label_key, length_class), []).append({
                "event_key": reconciliation.event_key,
                "report_date": reconciliation.report_date,
                "period_end": row["period_end"],
                "period_length_class": row["period_length_class"],
                "released_value": row["released_value"],
                "outcome": row["outcome"],
            })
            event_labels.setdefault((concept, basis, length_class), set()).add(label_key)

        for pair_key in sorted(event_labels):
            labels = frozenset(event_labels[pair_key])
            previous = previous_sets.get(pair_key)
            if previous is not None and previous != labels:
                for from_key, to_key in _label_set_transitions(previous, labels):
                    changes.append({
                        "concept": pair_key[0],
                        "basis": pair_key[1] or None,
                        "period_length_class": pair_key[2] or None,
                        "from_label": verbatim[from_key] if from_key is not None else None,
                        "to_label": verbatim[to_key] if to_key is not None else None,
                        "first_event_key": reconciliation.event_key,
                    })
            previous_sets[pair_key] = labels

    series = [
        {"key": {"concept": key[0], "basis": key[1], "label_key": key[2],
                 "period_length_class": key[3] or None},
         "points": sorted(points, key=lambda p: (p["report_date"], p["event_key"], p["period_end"] or ""))}
        for key, points in sorted(grouped.items())
    ]
    changes.sort(
        key=lambda change: (
            change["concept"], change["basis"] or "", change["first_event_key"],
            change["from_label"] or "", change["to_label"] or "",
        )
    )
    return {
        "schema": SCHEMA_ID + "#series",
        "series": series,
        "definition_changes": changes,
    }


__all__ = [
    "CONCEPT_TO_METRIC",
    "ReleaseInput",
    "ReleaseReconciliation",
    "SCHEMA_ID",
    "build_release_series",
    "reconcile_release",
    "release_input_from_event",
]

"""Peer-cohort lab: eligibility, A35 exclusion codes, and rank emission.

A pure, deterministic table builder.  Callers supply a cohort definition and
a member×metric observation map; this module never reads files, clocks, or
the query kernel beyond :data:`HARD_MAX_TICKERS`.  Ranks, percentiles, and
means are defined only over the eligible denominator of that metric.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from engine.fundamental_forensics.query import HARD_MAX_TICKERS


_PERCENTILE_QUANTUM = Decimal("0.0001")
_DURATION_TOLERANCE_DAYS = 20
_AUTHORITY: Mapping[str, Any] = MappingProxyType(
    {"class": "context_only", "display_only": True}
)


@dataclass(frozen=True)
class CohortMember:
    issuer_id: str
    cik: str
    tickers: tuple[str, ...]
    issuer_class: str
    sic: str


@dataclass(frozen=True)
class MetricObservation:
    value: Decimal | None
    period_end: date | None
    period_basis: str
    applicable: bool
    withheld: bool = False
    period_start: date | None = None
    unit: str | None = None
    metric_version: str | None = None


@dataclass(frozen=True)
class CohortDefinition:
    cohort_id: str
    anchor_issuer_id: str
    members: tuple[CohortMember, ...]
    metric_ids: tuple[str, ...]
    alignment_mode: str = "exclude"
    period_tolerance_days: int = 45
    min_n: int = 3


@dataclass(frozen=True)
class Exclusion:
    issuer_id: str
    metric_id: str
    code: str
    reason: str


@dataclass(frozen=True)
class MemberRow:
    issuer_id: str
    metric_id: str
    value: Decimal
    period_end: date | None
    period_label: str
    shifted: bool


@dataclass(frozen=True)
class MetricEmission:
    metric_id: str
    emission_state: str
    eligible_n: int
    rows: tuple[MemberRow, ...]
    ranks: Mapping[str, int] | None
    percentiles: Mapping[str, Decimal] | None
    mean: Decimal | None
    members_considered: int = 0
    exclusion_counts: Mapping[str, int] = MappingProxyType({})
    shifted_n: int = 0


@dataclass(frozen=True)
class CohortTable:
    cohort_id: str
    members_n: int
    members: tuple[CohortMember, ...]
    emissions: tuple[MetricEmission, ...]
    exclusions: tuple[Exclusion, ...]
    authority: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable snapshot; members, exclusions, and rows sorted."""
        members = sorted(self.members, key=lambda item: item.issuer_id)
        exclusions = sorted(
            self.exclusions, key=lambda item: (item.metric_id, item.issuer_id)
        )
        emissions = [
            _emission_to_dict(item)
            for item in sorted(self.emissions, key=lambda item: item.metric_id)
        ]
        return {
            "cohort_id": self.cohort_id,
            "members_n": self.members_n,
            "members": [_member_to_dict(item) for item in members],
            "emissions": emissions,
            "exclusions": [_exclusion_to_dict(item) for item in exclusions],
            "authority": dict(self.authority),
        }


def build_cohort_table(
    definition: CohortDefinition,
    observations: Mapping[str, Mapping[str, MetricObservation]],
) -> CohortTable:
    """Build a deterministic cohort table from caller-supplied observations.

    ``observations`` is keyed ``issuer_id → metric_id → MetricObservation``.
    Duplicate ``issuer_id`` values raise the query-kernel unique-entity
    message.  ``CohortMember.cik`` is the owner-binding cik the caller
    supplies (A14) and is the only collapse key: members sharing it collapse
    to the lexicographically first ``issuer_id`` and dropped aliases emit
    ``A35-I1`` — this module never derives, re-keys, or second-guesses
    issuer identity.
    """
    issuer_ids = [member.issuer_id for member in definition.members]
    if len(set(issuer_ids)) != len(issuer_ids):
        raise ValueError("entity_ids must be unique")
    if len(definition.members) > HARD_MAX_TICKERS:
        raise ValueError(
            f"ticker count exceeds HARD_MAX_TICKERS={HARD_MAX_TICKERS}"
        )

    kept, identity_exclusions, issuer_remap = _collapse_share_classes(
        definition.members
    )
    anchor_id = issuer_remap.get(
        definition.anchor_issuer_id, definition.anchor_issuer_id
    )

    exclusions: list[Exclusion] = list(identity_exclusions)
    emissions: list[MetricEmission] = []
    for metric_id in definition.metric_ids:
        emission, metric_exclusions = _emit_metric(
            definition,
            metric_id=metric_id,
            kept=kept,
            observations=observations,
            anchor_id=anchor_id,
        )
        emissions.append(emission)
        exclusions.extend(metric_exclusions)

    exclusions.sort(key=lambda item: (item.metric_id, item.issuer_id))
    return CohortTable(
        cohort_id=definition.cohort_id,
        members_n=len(kept),
        members=tuple(kept),
        emissions=tuple(emissions),
        exclusions=tuple(exclusions),
        authority=_AUTHORITY,
    )


def _collapse_share_classes(
    members: tuple[CohortMember, ...],
) -> tuple[list[CohortMember], list[Exclusion], dict[str, str]]:
    grouped: dict[str, list[CohortMember]] = {}
    for member in members:
        grouped.setdefault(member.cik, []).append(member)

    kept: list[CohortMember] = []
    exclusions: list[Exclusion] = []
    issuer_remap: dict[str, str] = {}
    for group in grouped.values():
        group_sorted = sorted(group, key=lambda item: item.issuer_id)
        winner = group_sorted[0]
        merged = CohortMember(
            issuer_id=winner.issuer_id,
            cik=winner.cik,
            tickers=tuple(sorted({ticker for item in group for ticker in item.tickers})),
            issuer_class=winner.issuer_class,
            sic=winner.sic,
        )
        kept.append(merged)
        issuer_remap[winner.issuer_id] = winner.issuer_id
        for alias in group_sorted[1:]:
            issuer_remap[alias.issuer_id] = winner.issuer_id
            exclusions.append(
                Exclusion(
                    issuer_id=alias.issuer_id,
                    metric_id="",
                    code="A35-I1",
                    reason="duplicate_share_class",
                )
            )
    kept.sort(key=lambda item: item.issuer_id)
    exclusions.sort(key=lambda item: (item.metric_id, item.issuer_id))
    return kept, exclusions, issuer_remap


def _emit_metric(
    definition: CohortDefinition,
    *,
    metric_id: str,
    kept: list[CohortMember],
    observations: Mapping[str, Mapping[str, MetricObservation]],
    anchor_id: str,
) -> tuple[MetricEmission, list[Exclusion]]:
    anchor_obs = _lookup(observations, anchor_id, metric_id)
    if anchor_obs is None and definition.anchor_issuer_id != anchor_id:
        anchor_obs = _lookup(observations, definition.anchor_issuer_id, metric_id)
    # A withheld anchor still sets the reference month (it is excluded
    # itself as W1); only an anchor with no reference period is unusable.
    anchor_usable = (
        anchor_obs is not None
        and anchor_obs.applicable
        and (anchor_obs.value is not None or anchor_obs.withheld)
        and anchor_obs.period_end is not None
    )

    rows: list[MemberRow] = []
    exclusions: list[Exclusion] = []
    removed_counts: dict[str, int] = {}
    for member in kept:
        if anchor_usable or member.issuer_id == anchor_id:
            # the anchor member keeps its own ordinary exclusion (X1/B1/P1)
            # even when the anchor reference is unusable for ranking
            row, exclusion = _evaluate_member(
                definition,
                member=member,
                metric_id=metric_id,
                observations=observations,
                anchor_obs=anchor_obs if anchor_usable else None,
            )
        else:
            row = None
            exclusion = Exclusion(
                issuer_id=member.issuer_id,
                metric_id=metric_id,
                code="A35-R1",
                reason="anchor_reference_unavailable",
            )
        if exclusion is not None:
            exclusions.append(exclusion)
            if row is None:
                removed_counts[exclusion.code] = (
                    removed_counts.get(exclusion.code, 0) + 1
                )
                continue
        if row is not None:
            rows.append(row)

    rows.sort(key=lambda item: (item.metric_id, item.issuer_id))
    exclusions.sort(key=lambda item: (item.metric_id, item.issuer_id))
    eligible_n = len(rows)
    exclusion_counts = MappingProxyType(dict(sorted(removed_counts.items())))
    shifted_n = sum(1 for row in rows if row.shifted)
    if not anchor_usable:
        emission = MetricEmission(
            metric_id=metric_id,
            emission_state="anchor_unavailable",
            eligible_n=0,
            rows=(),
            ranks=None,
            percentiles=None,
            mean=None,
            members_considered=len(kept),
            exclusion_counts=exclusion_counts,
        )
    elif eligible_n < definition.min_n:
        emission = MetricEmission(
            metric_id=metric_id,
            emission_state="below_min_n",
            eligible_n=eligible_n,
            rows=tuple(rows),
            ranks=None,
            percentiles=None,
            mean=None,
            members_considered=len(kept),
            exclusion_counts=exclusion_counts,
            shifted_n=shifted_n,
        )
    else:
        ranks, percentiles, mean = _rank_stats(rows)
        emission = MetricEmission(
            metric_id=metric_id,
            emission_state="ranked",
            eligible_n=eligible_n,
            rows=tuple(rows),
            ranks=MappingProxyType(ranks),
            percentiles=MappingProxyType(percentiles),
            mean=mean,
            members_considered=len(kept),
            exclusion_counts=exclusion_counts,
            shifted_n=shifted_n,
        )
    return emission, exclusions


def _evaluate_member(
    definition: CohortDefinition,
    *,
    member: CohortMember,
    metric_id: str,
    observations: Mapping[str, Mapping[str, MetricObservation]],
    anchor_obs: MetricObservation | None,
) -> tuple[MemberRow | None, Exclusion | None]:
    observation = _lookup(observations, member.issuer_id, metric_id)
    if observation is None:
        return None, Exclusion(
            issuer_id=member.issuer_id,
            metric_id=metric_id,
            code="A35-X1",
            reason="missing_peer_observation",
        )
    if not observation.applicable:
        return None, Exclusion(
            issuer_id=member.issuer_id,
            metric_id=metric_id,
            code="A35-B1",
            reason="metric_not_applicable",
        )
    if observation.withheld:
        return None, Exclusion(
            issuer_id=member.issuer_id,
            metric_id=metric_id,
            code="A35-W1",
            reason="statement_withheld",
        )
    if observation.value is None:
        return None, Exclusion(
            issuer_id=member.issuer_id,
            metric_id=metric_id,
            code="A35-X1",
            reason="missing_peer_observation",
        )

    shifted = False
    period_label = (
        observation.period_end.isoformat() if observation.period_end is not None else ""
    )
    note: Exclusion | None = None
    if observation.period_end is None:
        return None, Exclusion(
            issuer_id=member.issuer_id,
            metric_id=metric_id,
            code="A35-P1",
            reason="period_misaligned",
        )
    if anchor_obs is not None:
        # A35 comparability controls: each check is skipped when the anchor
        # field it reads is unset, so legacy observation maps see no change.
        if anchor_obs.period_basis and observation.period_basis != anchor_obs.period_basis:
            return None, Exclusion(
                issuer_id=member.issuer_id,
                metric_id=metric_id,
                code="A35-K1",
                reason="period_basis_incompatible",
            )
        if anchor_obs.unit is not None and observation.unit != anchor_obs.unit:
            return None, Exclusion(
                issuer_id=member.issuer_id,
                metric_id=metric_id,
                code="A35-U1",
                reason="unit_incompatible",
            )
        if (
            anchor_obs.period_basis == "duration"
            and anchor_obs.period_start is not None
            and (
                observation.period_start is None
                or abs(
                    (observation.period_end - observation.period_start).days
                    - (anchor_obs.period_end - anchor_obs.period_start).days
                )
                > _DURATION_TOLERANCE_DAYS
            )
        ):
            return None, Exclusion(
                issuer_id=member.issuer_id,
                metric_id=metric_id,
                code="A35-D1",
                reason="duration_incompatible",
            )
        if (
            anchor_obs.metric_version is not None
            and observation.metric_version != anchor_obs.metric_version
        ):
            return None, Exclusion(
                issuer_id=member.issuer_id,
                metric_id=metric_id,
                code="A35-V1",
                reason="metric_version_incompatible",
            )
    anchor_end = None if anchor_obs is None else anchor_obs.period_end
    if anchor_end is not None:
        delta = (observation.period_end - anchor_end).days
        if abs(delta) > definition.period_tolerance_days:
            if definition.alignment_mode == "shift_labeled":
                shifted = True
                period_label = _shifted_label(delta)
                note = Exclusion(
                    issuer_id=member.issuer_id,
                    metric_id=metric_id,
                    code="A35-P2",
                    reason="period_shifted-and-labeled",
                )
            else:
                return None, Exclusion(
                    issuer_id=member.issuer_id,
                    metric_id=metric_id,
                    code="A35-P1",
                    reason="period_misaligned",
                )

    row = MemberRow(
        issuer_id=member.issuer_id,
        metric_id=metric_id,
        value=observation.value,
        period_end=observation.period_end,
        period_label=period_label,
        shifted=shifted,
    )
    return row, note


def _lookup(
    observations: Mapping[str, Mapping[str, MetricObservation]],
    issuer_id: str,
    metric_id: str,
) -> MetricObservation | None:
    inner = observations.get(issuer_id)
    if inner is None:
        return None
    return inner.get(metric_id)


def _shifted_label(delta_days: int) -> str:
    if delta_days >= 0:
        return f"shifted:+{delta_days}d"
    return f"shifted:{delta_days}d"


def _rank_stats(
    rows: Sequence[MemberRow],
) -> tuple[dict[str, int], dict[str, Decimal], Decimal]:
    n = Decimal(len(rows))
    ordered = sorted(rows, key=lambda item: item.value, reverse=True)
    ranks: dict[str, int] = {}
    percentiles: dict[str, Decimal] = {}
    current_rank = 0
    previous: Decimal | None = None
    for row in ordered:
        if previous is None or row.value != previous:
            current_rank += 1
            previous = row.value
        ranks[row.issuer_id] = current_rank
        n_below = sum(1 for other in rows if other.value < row.value)
        percentiles[row.issuer_id] = (Decimal(n_below) / n).quantize(
            _PERCENTILE_QUANTUM, rounding=ROUND_HALF_EVEN
        )
    max_scale = max(_decimal_scale(row.value) for row in rows)
    total = sum((row.value for row in rows), start=Decimal(0))
    mean = (total / n).quantize(Decimal(10) ** -max_scale, rounding=ROUND_HALF_EVEN)
    return ranks, percentiles, mean


def _decimal_scale(value: Decimal) -> int:
    exponent = value.as_tuple().exponent
    if not isinstance(exponent, int):
        return 0
    return max(0, -exponent)


def _member_to_dict(member: CohortMember) -> dict[str, Any]:
    return {
        "issuer_id": member.issuer_id,
        "cik": member.cik,
        "tickers": list(member.tickers),
        "issuer_class": member.issuer_class,
        "sic": member.sic,
    }


def _exclusion_to_dict(exclusion: Exclusion) -> dict[str, str]:
    return {
        "issuer_id": exclusion.issuer_id,
        "metric_id": exclusion.metric_id,
        "code": exclusion.code,
        "reason": exclusion.reason,
    }


def _row_to_dict(row: MemberRow) -> dict[str, Any]:
    return {
        "issuer_id": row.issuer_id,
        "metric_id": row.metric_id,
        "value": str(row.value),
        "period_end": None if row.period_end is None else row.period_end.isoformat(),
        "period_label": row.period_label,
        "shifted": row.shifted,
    }


def _emission_to_dict(emission: MetricEmission) -> dict[str, Any]:
    rows = sorted(emission.rows, key=lambda item: (item.metric_id, item.issuer_id))
    ranks: dict[str, int] | None
    percentiles: dict[str, str] | None
    if emission.ranks is None:
        ranks = None
    else:
        ranks = {key: emission.ranks[key] for key in sorted(emission.ranks)}
    if emission.percentiles is None:
        percentiles = None
    else:
        percentiles = {
            key: str(emission.percentiles[key]) for key in sorted(emission.percentiles)
        }
    return {
        "metric_id": emission.metric_id,
        "emission_state": emission.emission_state,
        "eligible_n": emission.eligible_n,
        "rows": [_row_to_dict(row) for row in rows],
        "ranks": ranks,
        "percentiles": percentiles,
        "mean": None if emission.mean is None else str(emission.mean),
        "members_considered": emission.members_considered,
        "exclusion_counts": {
            key: emission.exclusion_counts[key]
            for key in sorted(emission.exclusion_counts)
        },
        "shifted_n": emission.shifted_n,
    }

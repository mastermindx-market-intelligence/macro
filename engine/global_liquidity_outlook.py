"""Measurement-only component-outlook accounting for the global-liquidity programme (GLT T08).

Every path this module produces is either an announced scenario (a published
schedule applied exactly as stated), a conditional accounting path (a caller
supplied, labelled assumption), or explicitly unavailable. There is no
statistical model here and none is pretended at: the residual block is
permanently unavailable pending a later task. ``VALIDATED`` is ``False``;
every claim is conditional-accounting display tier.

Point-in-time law (C15): an announcement is admissible only if its
publication was already available at the decision cutoff (T05 knowledge-time
law); an announcement published after ``as_of`` can never move a path, and a
revision that is not yet admissible can never displace the schedule it will
eventually replace.

Reserve identity (C16): the H.4.1 Table 5 reserve line is reconciled against
total assets minus every non-reserve liability line plus capital (T04
identity arithmetic). A dropped line or a double-counted line surfaces as a
non-zero residual; a null line makes the identity unavailable -- a null is
never read as zero.

Stdlib plus the T04/T05 engine modules only. No I/O except the availability
probe inside ``snapshot``; the system clock is never read.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from engine.global_liquidity_accounting import (
    DEFAULT_ABS_TOL,
    DEFAULT_REL_TOL,
    AccountingReconciliationError,
    ReserveIdentity,
    assert_reserve_identity,
    reserves_from_balance_sheet,
)
from engine.global_liquidity_knowledge_time import (
    KnowledgeTimeError,
    availability_start_utc,
    cutoff_utc,
)

__all__ = [
    "VALIDATED",
    "AUTHORITY",
    "CLAIM_LEVEL",
    "SCHEMA",
    "BASELINE_SCHEMA",
    "ESTIMATE_TYPES",
    "DEFAULT_HORIZONS_WEEKS",
    "DEFAULT_DECISION_TZ",
    "DEFAULT_PUBLICATION_TZ",
    "H41_BASIS",
    "H41_ASSETS_LINE",
    "H41_RESERVES_LINE",
    "H41_CAPITAL_LINE",
    "H41_TGA_LINE",
    "H41_RRP_FOREIGN_LINE",
    "H41_RRP_OTHERS_LINE",
    "H41_FR_NOTES_LINE",
    "H41_NONRESERVE_LIABILITY_LINES",
    "COMPONENT_LINES",
    "COMPONENT_SIGN",
    "SNAPSHOT_OWNER_INPUTS",
    "reconcile_reserve_identity",
    "admissible_announcements",
    "compose_component_paths",
    "baseline_comparison",
    "snapshot",
]

VALIDATED = False
AUTHORITY = "measurement_only"
CLAIM_LEVEL = "conditional_accounting_display_tier"
SCHEMA = "glt_component_outlook_v1"
BASELINE_SCHEMA = "glt_component_outlook_baselines_v1"
ESTIMATE_TYPES = ("announced_scenario", "conditional_accounting", "unavailable")
DEFAULT_HORIZONS_WEEKS = (4, 8, 13)
DEFAULT_DECISION_TZ = "America/New_York"
DEFAULT_PUBLICATION_TZ = "America/New_York"

H41_BASIS = "H.4.1 Table 5 Consolidated Statement of Condition of All Federal Reserve Banks"
H41_ASSETS_LINE = "Total assets"
H41_RESERVES_LINE = "Reserve balances with Federal Reserve Banks"
H41_CAPITAL_LINE = "Total capital"
H41_TGA_LINE = "Deposits: U.S. Treasury, General Account"
H41_RRP_FOREIGN_LINE = "Reverse repurchase agreements: Foreign official and international accounts"
H41_RRP_OTHERS_LINE = "Reverse repurchase agreements: Others"
H41_FR_NOTES_LINE = "Federal Reserve notes, net of F.R. Bank holdings"

H41_NONRESERVE_LIABILITY_LINES = (
    "Federal Reserve notes, net of F.R. Bank holdings",
    "Reverse repurchase agreements: Foreign official and international accounts",
    "Reverse repurchase agreements: Others",
    "Deposits: Term deposits held by depository institutions",
    "Deposits: U.S. Treasury, General Account",
    "Deposits: Foreign official",
    "Deposits: Other",
    "Deferred availability cash items",
    "Treasury contributions to credit facilities",
    "Earnings remittances due to the U.S. Treasury",
    "Other liabilities and accrued dividends",
)

COMPONENT_LINES = {
    "total_assets": ("Total assets",),
    "treasury_general_account": ("Deposits: U.S. Treasury, General Account",),
    "reverse_repo_others": ("Reverse repurchase agreements: Others",),
    "reverse_repo_foreign_official": (
        "Reverse repurchase agreements: Foreign official and international accounts",
    ),
    "federal_reserve_notes": ("Federal Reserve notes, net of F.R. Bank holdings",),
    "other_nonreserve_and_capital": (
        "Deposits: Term deposits held by depository institutions",
        "Deposits: Foreign official",
        "Deposits: Other",
        "Deferred availability cash items",
        "Treasury contributions to credit facilities",
        "Earnings remittances due to the U.S. Treasury",
        "Other liabilities and accrued dividends",
        "Total capital",
    ),
}

COMPONENT_SIGN = {
    "total_assets": 1,
    "treasury_general_account": -1,
    "reverse_repo_others": -1,
    "reverse_repo_foreign_official": -1,
    "federal_reserve_notes": -1,
    "other_nonreserve_and_capital": -1,
}

SNAPSHOT_OWNER_INPUTS = (
    "data/fred/WALCL.parquet",
    "data/fred/RRPONTSYD.parquet",
    "data/treasury/tga.parquet",
    "data/fred/WRESBAL.parquet",
)


# ---------------------------------------------------------------------------
# number law
# ---------------------------------------------------------------------------


def _is_null(value):
    """``None``, or a float/Decimal that is NaN or +/-infinity."""
    if value is None:
        return True
    if isinstance(value, float):
        return not math.isfinite(value)
    if isinstance(value, Decimal):
        return not value.is_finite()
    return False


def _row_number(row, line):
    """Read one H.4.1 line value; a bool is refused, a missing line is None."""
    value = row.get(line)
    if isinstance(value, bool):
        raise TypeError(f"H.4.1 line {line!r} is a bool; bool is not a number here")
    return value


def _sum_occurrences(occurrences, names):
    """Sum the occurrences whose line name is in ``names``; absent sums to 0."""
    total = 0
    for name, value in occurrences:
        if name in names:
            total = total + value
    return total


# ---------------------------------------------------------------------------
# 1) C16 reserve identity reconciliation
# ---------------------------------------------------------------------------


def reconcile_reserve_identity(
    h41_row,
    *,
    nonreserve_lines=H41_NONRESERVE_LIABILITY_LINES,
    abs_tol=DEFAULT_ABS_TOL,
    rel_tol=DEFAULT_REL_TOL,
):
    """Reconcile the H.4.1 Table 5 reserve line against assets minus N.

    ``N`` is every non-reserve liability occurrence plus capital. Every
    occurrence of a duplicated line is summed (double counting is exposed,
    never silently de-duplicated); a dropped line leaves a non-zero residual;
    a null line makes the implied reserves unavailable (never zero).
    """
    lines_used = list(nonreserve_lines) + [H41_CAPITAL_LINE]
    occurrences = [(name, _row_number(h41_row, name)) for name in lines_used]

    counts = {}
    for name in nonreserve_lines:
        counts[name] = counts.get(name, 0) + 1
    duplicate_lines = sorted(name for name, count in counts.items() if count > 1)
    undeclared_lines = sorted(name for name in counts if name not in H41_NONRESERVE_LIABILITY_LINES)

    assets = _row_number(h41_row, H41_ASSETS_LINE)
    reserves_reported = _row_number(h41_row, H41_RESERVES_LINE)
    capital = _row_number(h41_row, H41_CAPITAL_LINE)

    nonreserve_liabilities = {}
    for name in nonreserve_lines:
        if name not in nonreserve_liabilities:
            nonreserve_liabilities[name] = _row_number(h41_row, name)

    null_lookup = {H41_ASSETS_LINE: assets, H41_RESERVES_LINE: reserves_reported}
    for name, value in occurrences:
        null_lookup.setdefault(name, value)
    missing = []
    for name in [H41_ASSETS_LINE, H41_RESERVES_LINE] + lines_used:
        if name not in missing and _is_null(null_lookup[name]):
            missing.append(name)

    used_null = any(_is_null(value) for _name, value in occurrences)
    nonreserve_total = None
    if not used_null:
        nonreserve_total = 0
        for _name, value in occurrences:
            nonreserve_total = nonreserve_total + value

    treasury_cash = reverse_repo = other_nonreserve = None
    reserves_implied = None
    if not _is_null(assets) and not used_null:
        treasury_cash = _sum_occurrences(occurrences, {H41_TGA_LINE})
        reverse_repo = _sum_occurrences(
            occurrences, {H41_RRP_FOREIGN_LINE, H41_RRP_OTHERS_LINE}
        )
        rrp_names = {H41_RRP_FOREIGN_LINE, H41_RRP_OTHERS_LINE, H41_TGA_LINE}
        other_nonreserve = 0
        for name, value in occurrences:
            if name not in rrp_names:
                other_nonreserve = other_nonreserve + value
        ri = reserves_from_balance_sheet(
            assets=assets,
            treasury_cash=treasury_cash,
            reverse_repo=reverse_repo,
            other_nonreserve_liabilities_and_capital=other_nonreserve,
        )
        reserves_implied = ri.reserves

    residual = None
    reconciles = False
    if not _is_null(reserves_reported) and reserves_implied is not None:
        residual = reserves_reported - reserves_implied
        try:
            assert_reserve_identity(
                ReserveIdentity(
                    assets=assets,
                    treasury_cash=treasury_cash,
                    reverse_repo=reverse_repo,
                    other_nonreserve_liabilities_and_capital=other_nonreserve,
                    reserves=reserves_reported,
                    missing=(),
                    null_reason=None,
                ),
                abs_tol=abs_tol,
                rel_tol=rel_tol,
            )
            reconciles = True
        except AccountingReconciliationError:
            reconciles = False

    return {
        "basis": H41_BASIS,
        "assets": assets,
        "reserves_reported": reserves_reported,
        "nonreserve_liabilities": nonreserve_liabilities,
        "capital": capital,
        "nonreserve_total": nonreserve_total,
        "reserves_implied": reserves_implied,
        "residual": residual,
        "reconciles": reconciles,
        "lines_used": lines_used,
        "duplicate_lines": duplicate_lines,
        "undeclared_lines": undeclared_lines,
        "missing": missing,
    }


# ---------------------------------------------------------------------------
# 2) C15 point-in-time announcement admissibility
# ---------------------------------------------------------------------------


def _valid_change(change):
    if not isinstance(change, dict):
        return False
    effective = change.get("effective")
    if isinstance(effective, datetime) or not isinstance(effective, date):
        return False  # a datetime is invalid; effective must be a plain date
    has_level = "level" in change
    has_delta = "delta" in change
    if has_level == has_delta:
        return False  # exactly one of level/delta
    value = change["level"] if has_level else change["delta"]
    if isinstance(value, bool) or _is_null(value):
        return False
    return True


def admissible_announcements(announcements, *, as_of, decision_tz=DEFAULT_DECISION_TZ):
    """Split announcements into admitted / excluded at the ``as_of`` cutoff.

    First matching reason wins per announcement: ``missing_published_at``,
    ``invalid_published_at`` (naive datetime or anything T05 refuses),
    ``unknown_component``, ``invalid_change``, ``published_after_as_of``.
    An admitted announcement is then excluded with ``superseded_by:<id>``
    only when the superseding announcement is itself ADMITTED; an excluded
    revision never displaces the schedule it names. Inputs are not mutated.
    """
    cutoff = cutoff_utc(as_of, decision_tz)
    announcement_list = list(announcements)

    seen_ids = set()
    for announcement in announcement_list:
        announcement_id = announcement.get("id")
        if announcement_id in seen_ids:
            raise ValueError(f"duplicate announcement id: {announcement_id!r}")
        seen_ids.add(announcement_id)

    stage = []  # (announcement, reason-or-None, availability-start-or-None)
    for announcement in announcement_list:
        published_at = announcement.get("published_at")
        publication_tz = announcement.get("publication_tz", DEFAULT_PUBLICATION_TZ)
        reason = None
        start = None
        if published_at is None:
            reason = "missing_published_at"
        else:
            try:
                start = availability_start_utc(published_at, publication_tz)
            except (KnowledgeTimeError, TypeError, ValueError):
                reason = "invalid_published_at"
        if reason is None and announcement.get("component") not in COMPONENT_LINES:
            reason = "unknown_component"
        if reason is None:
            kind = announcement.get("kind")
            changes = announcement.get("changes")
            if (
                kind not in ("schedule", "financing_source")
                or not isinstance(changes, list)
                or not changes
                or not all(_valid_change(change) for change in changes)
            ):
                reason = "invalid_change"
        if reason is None and start > cutoff:
            reason = "published_after_as_of"
        stage.append((announcement, reason, start))

    superseder = {}
    for announcement, reason, _start in stage:
        if reason is None:
            target = announcement.get("supersedes")
            if target is not None and target not in superseder:
                superseder[target] = announcement["id"]

    admitted = []
    excluded = []
    for announcement, reason, start in stage:
        if reason is None and announcement["id"] in superseder:
            reason = "superseded_by:" + superseder[announcement["id"]]
        if reason is None:
            admitted.append(announcement)
        else:
            excluded.append(
                {
                    "id": announcement["id"],
                    "reason": reason,
                    "published_at_utc": start.isoformat() if start is not None else None,
                    "cutoff_utc": cutoff.isoformat(),
                }
            )
    return {"admitted": admitted, "excluded": excluded}


# ---------------------------------------------------------------------------
# 3) component paths
# ---------------------------------------------------------------------------


def _announcement_start(announcement):
    return availability_start_utc(
        announcement.get("published_at"),
        announcement.get("publication_tz", DEFAULT_PUBLICATION_TZ),
    )


def _point(horizon, target, level, anchor_level):
    return {
        "horizon_weeks": horizon,
        "target_date": target.isoformat(),
        "level": level,
        "change_from_anchor": level - anchor_level,
    }


def _path(component, lines, estimate_type, anchor_level, points, support, unavailable_reason):
    return {
        "component": component,
        "h41_lines": list(lines),
        "sign": COMPONENT_SIGN[component],
        "estimate_type": estimate_type,
        "anchor_level": anchor_level,
        "points": points,
        "support": support,
        "authority": AUTHORITY,
        "validated": VALIDATED,
        "unavailable_reason": unavailable_reason,
    }


def _unavailable_path(component, lines, reason):
    support = {"announcement_ids": [], "assumption_id": None, "ignored_assumption_ids": []}
    return _path(component, lines, "unavailable", None, [], support, reason)


def _component_anchor_level(row, lines):
    """Sum the component's lines from the row; None if any of them is null."""
    total = 0
    for line in lines:
        value = _row_number(row, line)
        if _is_null(value):
            return None
        total = total + value
    return total


def _assumption_map(assumptions):
    by_component = {}
    for assumption in assumptions:
        component = assumption.get("component")
        if component in by_component:
            raise ValueError(f"two assumptions for one component: {component!r}")
        by_component[component] = assumption
    return by_component


def _validate_horizons(horizons_weeks):
    horizons = list(horizons_weeks)
    if not horizons:
        raise ValueError("horizons_weeks must be non-empty")
    previous = None
    for horizon in horizons:
        if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
            raise ValueError(
                f"horizons_weeks entries must be positive ints, got {horizon!r}"
            )
        if previous is not None and horizon <= previous:
            raise ValueError(
                f"horizons_weeks must be strictly increasing, got {previous!r} then {horizon!r}"
            )
        previous = horizon
    return horizons


def _component_path(
    component,
    lines,
    row,
    observed_on,
    horizons,
    targets,
    admitted,
    by_component,
    assumptions,
):
    anchor_level = _component_anchor_level(row, lines)
    if anchor_level is None:
        return _unavailable_path(component, lines, "anchor_incomplete")

    component_announcements = [a for a in admitted if a.get("component") == component]
    if component_announcements:
        changes = []
        for announcement in component_announcements:
            start = _announcement_start(announcement)
            for change in announcement["changes"]:
                effective = change["effective"]
                if observed_on < effective:
                    changes.append((effective, start, announcement["id"], change))
        changes.sort(key=lambda item: (item[0], item[1], item[2]))
        points = []
        for horizon, target in zip(horizons, targets):
            level = anchor_level
            for effective, _start, _aid, change in changes:
                if effective <= target:
                    if "level" in change:
                        level = change["level"]
                    else:
                        level = level + change["delta"]
            points.append(_point(horizon, target, level, anchor_level))
        support = {
            "announcement_ids": [a["id"] for a in component_announcements],
            "assumption_id": None,
            "ignored_assumption_ids": [
                a["id"] for a in assumptions if a.get("component") == component
            ],
        }
        return _path(
            component, lines, "announced_scenario", anchor_level, points, support, None
        )

    assumption = by_component.get(component)
    if assumption is not None:
        kind = assumption.get("kind")
        if kind == "hold_level":
            points = [
                _point(horizon, target, anchor_level, anchor_level)
                for horizon, target in zip(horizons, targets)
            ]
        elif kind == "weekly_delta":
            value = assumption.get("value")
            if isinstance(value, bool):
                raise TypeError(
                    f"weekly_delta value for assumption {assumption.get('id')!r} "
                    "is a bool; bool is not a number here"
                )
            if _is_null(value):
                raise ValueError(
                    f"weekly_delta value for assumption {assumption.get('id')!r} "
                    "is null; a null is never read as zero"
                )
            points = [
                _point(horizon, target, anchor_level + value * horizon, anchor_level)
                for horizon, target in zip(horizons, targets)
            ]
        else:
            return _unavailable_path(component, lines, "unsupported_assumption_kind:" + str(kind))
        support = {
            "announcement_ids": [],
            "assumption_id": assumption.get("id"),
            "ignored_assumption_ids": [],
        }
        return _path(
            component, lines, "conditional_accounting", anchor_level, points, support, None
        )

    return _unavailable_path(component, lines, "no_admissible_announcement_or_assumption")


def _reserves_block(recon, paths, horizons, targets):
    """Aggregate the component paths onto the reserves line, or explain why not."""
    if recon["missing"]:
        reason = "anchor_incomplete"
    elif not recon["reconciles"]:
        reason = "anchor_identity_does_not_reconcile"
    else:
        first_unavailable = next(
            (name for name, path in paths.items() if path["estimate_type"] == "unavailable"),
            None,
        )
        reason = (
            "component_unavailable:" + first_unavailable
            if first_unavailable is not None
            else None
        )
    if reason is not None:
        return {
            "target": H41_RESERVES_LINE,
            "estimate_type": "unavailable",
            "points": [],
            "anchor_residual": recon["residual"],
            "authority": AUTHORITY,
            "validated": VALIDATED,
            "unavailable_reason": reason,
        }

    observed_anchor = recon["reserves_reported"]
    estimate_type = (
        "announced_scenario"
        if all(path["estimate_type"] == "announced_scenario" for path in paths.values())
        else "conditional_accounting"
    )
    points = []
    for horizon, target in zip(horizons, targets):
        announced_change = 0
        assumed_change = 0
        for path in paths.values():
            point = next(q for q in path["points"] if q["horizon_weeks"] == horizon)
            contribution = path["sign"] * point["change_from_anchor"]
            if path["estimate_type"] == "announced_scenario":
                announced_change = announced_change + contribution
            else:
                assumed_change = assumed_change + contribution
        points.append(
            {
                "horizon_weeks": horizon,
                "target_date": target.isoformat(),
                "level": observed_anchor + announced_change + assumed_change,
                "announced_change": announced_change,
                "assumed_change": assumed_change,
                "statistical_residual": None,
            }
        )
    return {
        "target": H41_RESERVES_LINE,
        "estimate_type": estimate_type,
        "points": points,
        "anchor_residual": recon["residual"],
        "authority": AUTHORITY,
        "validated": VALIDATED,
        "unavailable_reason": None,
    }


def compose_component_paths(
    anchor,
    announcements,
    assumptions,
    *,
    as_of,
    decision_tz=DEFAULT_DECISION_TZ,
    horizons_weeks=DEFAULT_HORIZONS_WEEKS,
):
    """Compose conditional accounting paths per component onto reserves.

    The anchor H.4.1 row must itself have been published at or before the
    ``as_of`` cutoff; otherwise no anchor number may appear anywhere in the
    output and every path (reserves included) is unavailable with reason
    ``anchor_published_after_as_of``.
    """
    by_component = _assumption_map(assumptions)
    horizons = _validate_horizons(horizons_weeks)
    cutoff = cutoff_utc(as_of, decision_tz)
    publication_tz = anchor.get("publication_tz", DEFAULT_PUBLICATION_TZ)
    anchor_start = availability_start_utc(anchor.get("published_at"), publication_tz)
    anchor_admissible = anchor_start <= cutoff
    observed_on = anchor.get("observed_on")
    targets = [observed_on + timedelta(days=7 * horizon) for horizon in horizons]

    adm = admissible_announcements(announcements, as_of=as_of, decision_tz=decision_tz)
    document = {
        "schema": SCHEMA,
        "as_of": as_of.isoformat(),
        "as_of_cutoff_utc": cutoff.isoformat(),
        "decision_tz": decision_tz,
        "horizons_weeks": horizons,
        "anchor": None,
        "anchor_lineage": {
            "observed_on": observed_on.isoformat(),
            "published_at_utc": anchor_start.isoformat(),
            "admissible": anchor_admissible,
        },
        "paths": {},
        "reserves": None,
        "statistical_residual": {
            "estimate_type": "unavailable",
            "unavailable_reason": "no_statistical_model_until_T09",
        },
        "admitted_announcement_ids": [a["id"] for a in adm["admitted"]],
        "excluded_announcements": adm["excluded"],
        "authority": AUTHORITY,
        "validated": VALIDATED,
        "claim_level": CLAIM_LEVEL,
    }

    if not anchor_admissible:
        for component, lines in COMPONENT_LINES.items():
            document["paths"][component] = _unavailable_path(
                component, lines, "anchor_published_after_as_of"
            )
        document["reserves"] = {
            "target": H41_RESERVES_LINE,
            "estimate_type": "unavailable",
            "points": [],
            "anchor_residual": None,
            "authority": AUTHORITY,
            "validated": VALIDATED,
            "unavailable_reason": "anchor_published_after_as_of",
        }
        return document

    row = anchor.get("row", {})
    document["anchor"] = reconcile_reserve_identity(row)
    for component, lines in COMPONENT_LINES.items():
        document["paths"][component] = _component_path(
            component,
            lines,
            row,
            observed_on,
            horizons,
            targets,
            adm["admitted"],
            by_component,
            assumptions,
        )
    document["reserves"] = _reserves_block(document["anchor"], document["paths"], horizons, targets)
    return document


# ---------------------------------------------------------------------------
# 4) baseline comparison (plain numbers; realized history never moves a path)
# ---------------------------------------------------------------------------


def baseline_comparison(outlook, *, realized_reserves=None):
    """Compare the outlook's reserves paths against persistence and realized.

    ``persistence_level`` holds the reported reserves anchor; the
    ``announced_only_level`` moves ONLY the announced-scenario components
    (everything else held). Realized reserves, where supplied, are recorded
    as plain misses and never fed back into any path.
    """
    anchor = outlook.get("anchor")
    if anchor is None:
        return {
            "schema": BASELINE_SCHEMA,
            "authority": AUTHORITY,
            "validated": VALIDATED,
            "rows": [],
            "unavailable_reason": "anchor_published_after_as_of",
        }
    if not anchor.get("reconciles"):
        return {
            "schema": BASELINE_SCHEMA,
            "authority": AUTHORITY,
            "validated": VALIDATED,
            "rows": [],
            "unavailable_reason": "anchor_identity_does_not_reconcile",
        }

    reserves_reported = anchor["reserves_reported"]
    announced_paths = [
        path
        for path in outlook.get("paths", {}).values()
        if path.get("estimate_type") == "announced_scenario"
    ]
    rows = []
    for point in outlook["reserves"]["points"]:
        horizon = point["horizon_weeks"]
        target_iso = point["target_date"]
        announced_total = 0
        for path in announced_paths:
            component_point = next(
                q for q in path["points"] if q["horizon_weeks"] == horizon
            )
            announced_total = announced_total + (
                path["sign"] * component_point["change_from_anchor"]
            )
        persistence_level = reserves_reported
        announced_only_level = reserves_reported + announced_total
        realized_level = None
        if realized_reserves is not None:
            realized_level = realized_reserves.get(date.fromisoformat(target_iso))
        rows.append(
            {
                "horizon_weeks": horizon,
                "target_date": target_iso,
                "persistence_level": persistence_level,
                "announced_only_level": announced_only_level,
                "difference": announced_only_level - persistence_level,
                "realized_level": realized_level,
                "persistence_miss": (
                    realized_level - persistence_level
                    if realized_level is not None
                    else None
                ),
                "announced_only_miss": (
                    realized_level - announced_only_level
                    if realized_level is not None
                    else None
                ),
            }
        )
    return {
        "schema": BASELINE_SCHEMA,
        "rows": rows,
        "unavailable_reason": None,
        "authority": AUTHORITY,
        "validated": VALIDATED,
    }


# ---------------------------------------------------------------------------
# 5) snapshot: fail-open availability probe (no file contents are read)
# ---------------------------------------------------------------------------


def snapshot(root=None, *, as_of, decision_tz=DEFAULT_DECISION_TZ):
    """Name the owner inputs a full component outlook would need (T22).

    Fail-open and degraded by construction: this probe only checks that the
    owner input paths exist; it never reads a file, never computes a path,
    and always reports ``data_degraded``.
    """
    if root is None:
        root = Path(__file__).resolve().parents[1]
    base = Path(root)
    gaps = []
    for relative in SNAPSHOT_OWNER_INPUTS:
        if not (base / relative).exists():
            gaps.append(relative + " not found")
    for line in H41_NONRESERVE_LIABILITY_LINES:
        if line != H41_TGA_LINE:
            gaps.append("no owner loader for H.4.1 line: " + line)
    gaps.append("no owner loader for H.4.1 line: " + H41_CAPITAL_LINE)
    return {
        "schema": SCHEMA,
        "as_of": as_of.isoformat(),
        "as_of_cutoff_utc": cutoff_utc(as_of, decision_tz).isoformat(),
        "authority": AUTHORITY,
        "validated": VALIDATED,
        "degraded": True,
        "headline": {
            "state": "data_degraded",
            "summary": (
                "component outlook needs a full H.4.1 Table 5 owner loader "
                "(routed to T22); no paths computed"
            ),
        },
        "gaps": gaps,
        "paths": {},
    }

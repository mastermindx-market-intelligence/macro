"""Price-participation context for the existing Finviz theme/subtheme plane.

Answers a bounded question the heatmap alone cannot: is a move broad participation,
narrow leadership, or a single-name impulse? Inputs are only the incumbent Finviz
theme tree plus subtheme/member horizon returns.

This is descriptive context, not a durable-fundamental-rerating verdict. A durable
investment thesis still requires independent earnings/revision/catalyst/economic and
valuation evidence from their existing owners. This module creates no membership,
event, thesis, ranking, gating, sizing, or trading authority.
"""
from __future__ import annotations

import math
from statistics import median
from typing import Mapping, Sequence

SCHEMA = "theme_repricing_context.v1"

AUTHORITY = {
    "context_only": True,
    "display_only": True,
    "not_a_signal": True,
    "may_rank": False,
    "may_gate": False,
    "may_size": False,
    "may_escalate": False,
    "may_trade": False,
}

# Descriptive cut points, deliberately not fitted to forward returns.
PARAMS = {
    "min_members": 3,
    "min_coverage": 0.60,
    "broad_up_share_1w": 0.70,
    "broad_up_share_1m": 0.60,
    "narrow_up_share": 0.60,
    "single_name_top_positive_share": 0.60,
    "narrow_top_positive_share": 0.45,
    "theme_broad_subtheme_share": 0.60,
    "theme_isolated_top_positive_share": 0.55,
}

HORIZONS = ("1W", "1M", "3M")


def _fin(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(out) or abs(out) > 100000:
        return None
    return out


def _rnd(value: float | None, places: int = 3) -> float | None:
    return None if value is None else round(float(value), places)


def _positive_share(values: Sequence[float], top_n: int = 1) -> float | None:
    """Top-N positive-return magnitude / all positive-return magnitude.

    Equal-member diagnostic only: this is NOT a market-cap contribution share.
    """
    pos = sorted((max(0.0, float(v)) for v in values), reverse=True)
    total = sum(pos)
    if total <= 1e-12:
        return None
    return sum(pos[:top_n]) / total


def _horizon_stats(
    expected_members: Sequence[str],
    member_perf: Mapping[str, Mapping[str, float]],
    group_perf: Mapping[str, float],
    horizon: str,
) -> dict:
    rows: list[tuple[str, float]] = []
    for ticker in expected_members:
        value = _fin((member_perf.get(ticker) or {}).get(horizon))
        if value is not None:
            rows.append((ticker, value))

    expected_n = len(expected_members)
    observed_n = len(rows)
    coverage = observed_n / expected_n if expected_n else None
    group_value = _fin(group_perf.get(horizon))
    if not rows:
        return {
            "expected_n": expected_n,
            "observed_n": 0,
            "coverage": _rnd(coverage),
            "group_return": _rnd(group_value, 2),
            "mean_member_return": None,
            "median_member_return": None,
            "up_share": None,
            "beat_group_share": None,
            "top_positive_move_share": None,
            "top3_positive_move_share": None,
            "leader": None,
        }

    values = [value for _, value in rows]
    med = float(median(values))
    mean = float(sum(values) / observed_n)
    leader_ticker, leader_return = max(rows, key=lambda row: (row[1], row[0]))
    beat_group = (
        sum(value > group_value for _, value in rows) / observed_n
        if group_value is not None
        else None
    )
    return {
        "expected_n": expected_n,
        "observed_n": observed_n,
        "coverage": _rnd(coverage),
        "group_return": _rnd(group_value, 2),
        "mean_member_return": _rnd(mean, 2),
        "median_member_return": _rnd(med, 2),
        "up_share": _rnd(sum(value > 0 for value in values) / observed_n),
        "beat_group_share": _rnd(beat_group),
        "top_positive_move_share": _rnd(_positive_share(values)),
        "top3_positive_move_share": _rnd(_positive_share(values, 3)),
        "leader": {
            "ticker": leader_ticker,
            "return": _rnd(leader_return, 2),
            "vs_member_median": _rnd(leader_return - med, 2),
            "vs_group": (
                _rnd(leader_return - group_value, 2)
                if group_value is not None
                else None
            ),
        },
    }


def _price_leader(
    expected_members: Sequence[str],
    member_perf: Mapping[str, Mapping[str, float]],
) -> dict | None:
    """Multi-horizon price leader; explicitly not a validated alpha leader."""
    medians: dict[str, float] = {}
    for horizon in HORIZONS:
        vals = [
            value
            for ticker in expected_members
            if (value := _fin((member_perf.get(ticker) or {}).get(horizon))) is not None
        ]
        if vals:
            medians[horizon] = float(median(vals))

    candidates: list[dict] = []
    for ticker in expected_members:
        perf = member_perf.get(ticker) or {}
        observed: dict[str, float] = {}
        above_median = positive = 0
        for horizon in HORIZONS:
            value = _fin(perf.get(horizon))
            if value is None:
                continue
            observed[horizon] = value
            positive += int(value > 0)
            above_median += int(horizon in medians and value > medians[horizon])
        if observed:
            candidates.append({
                "ticker": ticker,
                "observed_horizons": len(observed),
                "above_member_median_horizons": above_median,
                "positive_horizons": positive,
                "perf": {h: _rnd(v, 2) for h, v in observed.items()},
            })

    if not candidates:
        return None

    def order(row: Mapping) -> tuple:
        perf = row.get("perf") or {}
        return (
            int(row.get("above_member_median_horizons") or 0),
            int(row.get("positive_horizons") or 0),
            _fin(perf.get("1M")) or -1e9,
            _fin(perf.get("1W")) or -1e9,
            str(row.get("ticker") or ""),
        )

    return dict(max(candidates, key=order))


def _group_residual_leader(
    expected_members: Sequence[str],
    member_perf: Mapping[str, Mapping[str, float]],
    group_perf: Mapping[str, float],
) -> dict | None:
    """Leader after subtracting the source subtheme return at each horizon.

    This is a GROUP-RELATIVE candidate only. It is not market/sector/factor neutral and
    therefore must never be called alpha. The explicit limitation is part of the payload.
    """
    candidates: list[dict] = []
    for ticker in expected_members:
        perf = member_perf.get(ticker) or {}
        residual: dict[str, float] = {}
        for horizon in HORIZONS:
            member = _fin(perf.get(horizon))
            group = _fin(group_perf.get(horizon))
            if member is None or group is None:
                continue
            residual[horizon] = member - group
        if len(residual) < 2:
            continue
        values = list(residual.values())
        candidates.append({
            "ticker": ticker,
            "observed_horizons": len(residual),
            "positive_residual_horizons": sum(value > 0 for value in values),
            "mean_residual": _rnd(sum(values) / len(values), 2),
            "residual": {h: _rnd(v, 2) for h, v in residual.items()},
        })
    if not candidates:
        return None

    def order(row: Mapping) -> tuple:
        residual = row.get("residual") or {}
        return (
            int(row.get("positive_residual_horizons") or 0),
            _fin(row.get("mean_residual")) or -1e9,
            _fin(residual.get("1M")) or -1e9,
            _fin(residual.get("1W")) or -1e9,
            str(row.get("ticker") or ""),
        )

    winner = dict(max(candidates, key=order))
    winner["semantics"] = "group_relative_leader_candidate_not_alpha"
    winner["limitations"] = [
        "subtracts source subtheme return only",
        "not market sector or factor neutral",
        "not validated forward alpha",
    ]
    return winner


def _leadership_context(
    expected_members: Sequence[str],
    member_perf: Mapping[str, Mapping[str, float]],
    group_perf: Mapping[str, float],
) -> dict:
    """Cross-horizon leader continuity / handoff context.

    A handoff is a PRICE observation: the recent leader changed and the former medium-
    horizon leader is no longer beating the group over 1W. It is not evidence that
    capital literally flowed from one security to another, and it is not an exit order.
    """
    leaders: dict[str, dict] = {}
    for horizon in HORIZONS:
        rows = []
        for ticker in expected_members:
            value = _fin((member_perf.get(ticker) or {}).get(horizon))
            if value is not None:
                rows.append((ticker, value))
        if rows:
            ticker, value = max(rows, key=lambda row: (row[1], row[0]))
            leaders[horizon] = {"ticker": ticker, "return": _rnd(value, 2)}

    unique = sorted({row["ticker"] for row in leaders.values()})
    recent = (leaders.get("1W") or {}).get("ticker")
    medium = (leaders.get("1M") or {}).get("ticker")
    long = (leaders.get("3M") or {}).get("ticker")
    group_1w = _fin(group_perf.get("1W"))

    former_1w = (
        _fin((member_perf.get(medium) or {}).get("1W"))
        if medium
        else None
    )
    recent_1w = (
        _fin((member_perf.get(recent) or {}).get("1W"))
        if recent
        else None
    )

    if len(leaders) < 2:
        state = "insufficient"
    elif recent == medium and (long is None or long == recent):
        state = "stable_multihorizon"
    elif recent == medium:
        state = "stable_recent_leader"
    elif (
        recent is not None
        and medium is not None
        and group_1w is not None
        and recent_1w is not None
        and former_1w is not None
        and recent_1w > group_1w
        and former_1w <= group_1w
    ):
        state = "handoff_candidate"
    elif len(unique) >= 3:
        state = "fragmented"
    else:
        state = "leader_rotation"

    return {
        "state": state,
        "leaders": leaders,
        "n_unique_leaders": len(unique),
        "recent_leader": recent,
        "medium_horizon_leader": medium,
        "long_horizon_leader": long,
        "recent_leader_1w_vs_group": (
            _rnd(recent_1w - group_1w, 2)
            if recent_1w is not None and group_1w is not None
            else None
        ),
        "former_medium_leader_1w_vs_group": (
            _rnd(former_1w - group_1w, 2)
            if former_1w is not None and group_1w is not None
            else None
        ),
        "semantics": "price_leadership_continuity_not_capital_flow",
        "can_support_exit_decision": False,
        "can_support_rotate_decision": False,
    }


def _shape(h1w: Mapping, h1m: Mapping) -> str:
    expected = int(h1w.get("expected_n") or 0)
    observed = int(h1w.get("observed_n") or 0)
    coverage = _fin(h1w.get("coverage"))
    g1w = _fin(h1w.get("group_return"))
    g1m = _fin(h1m.get("group_return"))
    up1w = _fin(h1w.get("up_share"))
    up1m = _fin(h1m.get("up_share"))
    top1 = _fin(h1w.get("top_positive_move_share"))

    if (
        expected < PARAMS["min_members"]
        or observed < PARAMS["min_members"]
        or coverage is None
        or coverage < PARAMS["min_coverage"]
        or g1w is None
        or up1w is None
    ):
        return "insufficient_data"

    if g1w > 0:
        if (
            top1 is not None
            and top1 >= PARAMS["single_name_top_positive_share"]
            and up1w < PARAMS["narrow_up_share"]
        ):
            return "single_name_impulse"
        if (
            up1w >= PARAMS["broad_up_share_1w"]
            and up1m is not None
            and up1m >= PARAMS["broad_up_share_1m"]
            and (top1 is None or top1 < PARAMS["narrow_top_positive_share"])
        ):
            return "broad_price_repricing"
        if (
            up1w >= PARAMS["broad_up_share_1w"]
            and (g1m is None or g1m <= 0 or up1m is None
                 or up1m < PARAMS["broad_up_share_1m"])
        ):
            return "early_diffusion"
        if (
            up1w < PARAMS["narrow_up_share"]
            or (top1 is not None and top1 >= PARAMS["narrow_top_positive_share"])
        ):
            return "narrow_leadership"
        return "mixed_positive"

    if g1w < 0:
        if g1m is not None and g1m > 0 and up1w < 0.50:
            return "leadership_break"
        if up1w <= 0.40:
            return "fading"
        return "mixed_negative"

    return "range"


def analyze_subtheme(
    *,
    key: str,
    theme: str,
    name: str,
    members: Sequence[str],
    group_perf: Mapping[str, float],
    member_perf: Mapping[str, Mapping[str, float]],
) -> dict:
    expected = [str(t).strip().upper() for t in members if str(t).strip()]
    horizons = {
        horizon: _horizon_stats(expected, member_perf, group_perf, horizon)
        for horizon in HORIZONS
    }
    shape = _shape(horizons["1W"], horizons["1M"])
    h1w, h1m = horizons["1W"], horizons["1M"]
    leadership = _leadership_context(expected, member_perf, group_perf)
    if shape == "broad_price_repricing" and (_fin(h1m.get("group_return")) or 0) > 0:
        price_durability = "confirming"
    elif shape == "early_diffusion":
        price_durability = "forming"
    elif shape in {"single_name_impulse", "narrow_leadership"}:
        price_durability = "fragile"
    elif shape in {"leadership_break", "fading"}:
        price_durability = "weakening"
    elif shape in {"insufficient_data", "range"}:
        price_durability = "insufficient"
    else:
        price_durability = "mixed"

    g1w = _fin(h1w.get("group_return"))
    up1w = _fin(h1w.get("up_share"))
    top1 = _fin(h1w.get("top_positive_move_share"))
    return {
        "key": key,
        "theme": theme,
        "name": name,
        "expected_members": len(expected),
        "shape": shape,
        "horizons": horizons,
        "price_leader": _price_leader(expected, member_perf),
        "group_residual_leader_candidate": _group_residual_leader(
            expected, member_perf, group_perf,
        ),
        "leadership": leadership,
        "durability_evidence": {
            "scope": "price_participation_only",
            "status": price_durability,
            "fundamental_confirmation": "not_in_this_contract",
            "event_confirmation": "not_in_this_contract",
            "valuation_confirmation": "not_in_this_contract",
            "can_support_buy_decision": False,
            "can_support_exit_decision": False,
        },
        "exit_watch": {
            "breadth_narrowing": bool(
                g1w is not None and g1w > 0 and up1w is not None and up1w < 0.50
            ),
            "move_concentration": bool(
                top1 is not None and top1 >= PARAMS["narrow_top_positive_share"]
            ),
            "leadership_break": shape == "leadership_break",
            "fading": shape == "fading",
            "leader_handoff_candidate": leadership["state"] == "handoff_candidate",
            "leadership_fragmented": leadership["state"] == "fragmented",
        },
    }


def _theme_summary(theme: str, rows: Sequence[Mapping]) -> dict:
    usable = [row for row in rows if row.get("shape") != "insufficient_data"]
    one_week = [
        value
        for row in usable
        if (value := _fin(
            ((row.get("horizons") or {}).get("1W") or {}).get("group_return")
        )) is not None
    ]
    positive = [max(0.0, value) for value in one_week]
    total_positive = sum(positive)
    top_share = max(positive) / total_positive if total_positive > 1e-12 else None
    advancing = (
        sum(value > 0 for value in one_week) / len(one_week)
        if one_week
        else None
    )
    broad_n = sum(row.get("shape") == "broad_price_repricing" for row in usable)
    early_n = sum(row.get("shape") == "early_diffusion" for row in usable)
    narrow_n = sum(
        row.get("shape") in {"single_name_impulse", "narrow_leadership"}
        for row in usable
    )
    handoff_n = sum(
        ((row.get("leadership") or {}).get("state") == "handoff_candidate")
        for row in usable
    )
    fragmented_n = sum(
        ((row.get("leadership") or {}).get("state") == "fragmented")
        for row in usable
    )

    if not usable or advancing is None:
        state = "insufficient_data"
    elif (
        advancing >= PARAMS["theme_broad_subtheme_share"]
        and (broad_n + early_n) >= max(2, math.ceil(len(usable) * 0.40))
        and (
            top_share is None
            or top_share < PARAMS["theme_isolated_top_positive_share"]
        )
    ):
        state = "broad_subtheme_diffusion"
    elif (
        top_share is not None
        and top_share >= PARAMS["theme_isolated_top_positive_share"]
    ):
        state = "isolated_subtheme_move"
    elif advancing <= 0.35:
        state = "theme_fading"
    else:
        state = "mixed"

    return {
        "theme": theme,
        "n_subthemes": len(rows),
        "usable_subthemes": len(usable),
        "advancing_subtheme_share_1w": _rnd(advancing),
        "top_positive_subtheme_move_share_1w": _rnd(top_share),
        "broad_price_repricing_subthemes": broad_n,
        "early_diffusion_subthemes": early_n,
        "narrow_or_single_name_subthemes": narrow_n,
        "leader_handoff_candidate_subthemes": handoff_n,
        "fragmented_leadership_subthemes": fragmented_n,
        "state": state,
    }


def build_context(
    tree: Sequence[Mapping],
    subsector_perf: Mapping[str, Mapping[str, float]],
    member_perf: Mapping[str, Mapping[str, float]] | None = None,
    *,
    asof: str = "",
    source: str = "finviz-themes",
) -> dict:
    member_perf = member_perf or {}
    subthemes: list[dict] = []
    by_theme: dict[str, list[dict]] = {}

    for theme_row in tree:
        theme = str(theme_row.get("theme") or theme_row.get("key") or "").strip()
        if not theme:
            continue
        for sub in theme_row.get("subsectors", []) or []:
            key = str(sub.get("key") or "").strip()
            if not key:
                continue
            row = analyze_subtheme(
                key=key,
                theme=theme,
                name=str(sub.get("name") or key).strip(),
                members=sub.get("members") or [],
                group_perf=subsector_perf.get(key) or {},
                member_perf=member_perf,
            )
            subthemes.append(row)
            by_theme.setdefault(theme, []).append(row)

    return {
        "schema": SCHEMA,
        "asof": asof,
        "source": source,
        "authority": dict(AUTHORITY),
        "scope": {
            "uses_existing_finviz_snapshot": True,
            "price_participation_only": True,
            "move_concentration_basis":
                "equal_member_positive_return_magnitude_not_market_cap_contribution",
            "leader_semantics": "price_leader_not_validated_alpha_leader",
            "group_residual_leader_semantics":
                "subtheme_relative_candidate_not_market_sector_factor_neutral_alpha",
            "leadership_semantics":
                "cross_horizon_continuity_handoff_context_not_capital_flow_or_exit_order",
            "durability_semantics":
                "price_participation_confirmation_not_investment_durability",
            "creates_membership": False,
            "creates_event_truth": False,
            "creates_trade_authority": False,
        },
        "themes": [_theme_summary(theme, rows) for theme, rows in by_theme.items()],
        "subthemes": subthemes,
        "n_themes": len(by_theme),
        "n_subthemes": len(subthemes),
    }

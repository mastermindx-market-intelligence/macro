"""Prior PUBLICATION resolution for Macro workspace ``changes``.

The previously written ``latest.json`` is a build artifact, not automatically
the previous publication. R1: "earlier" means a strictly earlier
``headline.effective_date`` (date-only), never an earlier ``built_at``.

When this build's effective date equals the stored artifact's, the stored
artifact's own ``changes.prior_*`` snapshot is the genuine earlier publication
(if it had one). The stored current values become the prior only when the new
effective date is strictly later.
"""
from __future__ import annotations

from typing import Any, Mapping

COMPARABILITY_NO_EARLIER = "NO_EARLIER_PUBLICATION"

NO_EARLIER_VOICE = {
    "en": "No earlier reading yet",
    "zh": "暂无更早读数",
}


def date_key(value: Any) -> str | None:
    """YYYY-MM-DD prefix of an ISO date or datetime. None if unusable."""
    if value is None:
        return None
    text = str(value).strip()
    if len(text) < 10:
        return None
    return text[:10]


def is_strictly_earlier(candidate: Any, current: Any) -> bool:
    cand = date_key(candidate)
    cur = date_key(current)
    if cand is None or cur is None:
        return False
    return cand < cur


def effective_date_of(snapshot: Mapping[str, Any] | None) -> Any:
    if not isinstance(snapshot, Mapping):
        return None
    headline = snapshot.get("headline")
    if not isinstance(headline, Mapping):
        return None
    return headline.get("effective_date")


def no_earlier_publication() -> dict[str, Any]:
    """Typed absence: no genuine earlier publication to compare against.

    Schema keys stay; values are null / empty. ``null_reason`` uses the closed
    ``INSUFFICIENT_HISTORY`` token (no fabricated 0). ``sign`` is not a
    changes-block field in the contract — consumers treat a missing/null delta
    as a null sign.
    """
    return {
        "comparability": COMPARABILITY_NO_EARLIER,
        "prior_generation_id": None,
        "prior_effective_date": None,
        "prior_method_version": None,
        "deltas": [],
        "status": "ABSENT",
        "null_reason": "INSUFFICIENT_HISTORY",
    }


def _items_from_prior_deltas(changes: Mapping[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for delta in changes.get("deltas") or []:
        if not isinstance(delta, Mapping):
            continue
        mid = delta.get("metric_id")
        if mid:
            items.append({"metric_id": mid, "value": delta.get("prior_value")})
    return items


# Axis metric_ids the five quadrant composers emit as (x, y) in ``changes.deltas``.
# Keying by id keeps a reordered delta tuple from silently swapping the carried
# prior quadrant (positional mapping was an unpinned invariant).
_QUADRANT_X_METRIC_IDS = frozenset({
    "growth_momentum",
    "inflation_impulse",
    "financial_conditions_level",
    "labor_demand",
    "funding_pressure",
    "cash_flow_momentum",
})
_QUADRANT_Y_METRIC_IDS = frozenset({
    "growth_level_breadth",
    "persistence_breadth",
    "financial_conditions_impulse",
    "labor_supply_tightness",
    "balance_sheet_support",
    "credit_stress",
})


def _quadrant_from_prior_deltas(changes: Mapping[str, Any]) -> dict[str, Any]:
    by_id: dict[str, Any] = {}
    ordered: list[Any] = []
    for delta in changes.get("deltas") or []:
        if not isinstance(delta, Mapping):
            continue
        mid = delta.get("metric_id")
        val = delta.get("prior_value")
        ordered.append(val)
        if mid:
            by_id[str(mid)] = val
    x = next((by_id[k] for k in by_id if k in _QUADRANT_X_METRIC_IDS), None)
    y = next((by_id[k] for k in by_id if k in _QUADRANT_Y_METRIC_IDS), None)
    if x is None and y is None and ordered:
        x = ordered[0] if len(ordered) > 0 else None
        y = ordered[1] if len(ordered) > 1 else None
    return {"x": x, "y": y}


def synthetic_prior_from_changes(stored: Mapping[str, Any]) -> dict[str, Any] | None:
    """Rebuild a prior-publication snapshot from ``stored.changes.prior_*``."""
    changes = stored.get("changes")
    if not isinstance(changes, Mapping):
        return None
    prior_eff = changes.get("prior_effective_date")
    if date_key(prior_eff) is None:
        return None
    return {
        "headline": {
            "effective_date": prior_eff,
            "method_version": changes.get("prior_method_version"),
            "quadrant": _quadrant_from_prior_deltas(changes),
        },
        "generation": {
            "generation_id": changes.get("prior_generation_id"),
        },
        "metrics": {"items": _items_from_prior_deltas(changes)},
    }


def resolve_publication_prior(
    stored: Mapping[str, Any] | None,
    current_effective_date: Any,
) -> Mapping[str, Any] | None:
    """Return the snapshot that is the last strictly-earlier publication.

    * stored is None → None (first build)
    * stored.effective_date < current → stored (new publication; replace prior)
    * stored.effective_date == current (or stored is later / look-ahead) →
      carry forward ``stored.changes`` when *that* prior date is strictly
      earlier; otherwise None
    """
    if not isinstance(stored, Mapping):
        return None
    stored_eff = effective_date_of(stored)
    if is_strictly_earlier(stored_eff, current_effective_date):
        return stored
    changes = stored.get("changes")
    carried_eff = changes.get("prior_effective_date") if isinstance(changes, Mapping) else None
    if is_strictly_earlier(carried_eff, current_effective_date):
        return synthetic_prior_from_changes(stored)
    return None


def _is_num(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def apply_headline_publication_fields(
    headline: dict[str, Any],
    resolved: Mapping[str, Any] | None,
    *,
    raw_prior: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Stamp typed-null movement fields when this build has no earlier publication.

    First print (``raw_prior is None``) keeps the composer's existing WARMUP /
    refusal vector object. A same-dated rebuild whose resolved prior is None
    is ``NO_EARLIER_PUBLICATION``: ``one_month_vector`` and
    ``transition_distance`` become JSON null, never ``Δx 0.0``.
    """
    if resolved is None and raw_prior is not None:
        headline["one_month_vector"] = None
        headline["transition_distance"] = None
        headline["movement_state"] = COMPARABILITY_NO_EARLIER
    else:
        headline["movement_state"] = None
    return headline


def _null_headline_movement(headline: dict[str, Any]) -> None:
    headline["one_month_vector"] = None
    headline["transition_distance"] = None
    headline["movement_state"] = COMPARABILITY_NO_EARLIER
    prior_state = headline.get("prior_state")
    if isinstance(prior_state, dict):
        headline["prior_state"] = {
            "state_id": None,
            "effective_date": None,
            "method_version": None,
        }


def _metric_value_from_snapshot(snapshot: Mapping[str, Any], metric_id: Any) -> Any:
    metrics = snapshot.get("metrics")
    items = metrics.get("items") if isinstance(metrics, Mapping) else None
    if isinstance(items, list):
        for item in items:
            if isinstance(item, Mapping) and item.get("metric_id") == metric_id:
                return item.get("value")
    return None


def _recompute_changes_from_resolved(
    changes: Mapping[str, Any],
    resolved: Mapping[str, Any],
) -> dict[str, Any]:
    """Rewrite a same-dated COMPARABLE block against the resolved earlier publication."""
    prior_h = resolved.get("headline") if isinstance(resolved.get("headline"), Mapping) else {}
    prior_g = resolved.get("generation") if isinstance(resolved.get("generation"), Mapping) else {}
    new_deltas: list[dict[str, Any]] = []
    for delta in changes.get("deltas") or []:
        if not isinstance(delta, Mapping):
            continue
        mid = delta.get("metric_id")
        cur = delta.get("current_value")
        prev = _metric_value_from_snapshot(resolved, mid)
        computed = None
        if _is_num(cur) and _is_num(prev):
            computed = round(float(cur) - float(prev), 4)
        new_deltas.append({
            "metric_id": mid,
            "prior_value": prev,
            "current_value": cur,
            "delta": computed,
            "note": delta.get("note"),
        })
    return {
        "comparability": "COMPARABLE",
        "prior_generation_id": prior_g.get("generation_id"),
        "prior_effective_date": effective_date_of(resolved),
        "prior_method_version": prior_h.get("method_version"),
        "deltas": new_deltas,
        "status": "PRESENT",
        "null_reason": None,
    }


def _recompute_headline_from_resolved(
    headline: dict[str, Any],
    resolved: Mapping[str, Any],
) -> None:
    q = headline.get("quadrant") if isinstance(headline.get("quadrant"), Mapping) else {}
    prior_h = resolved.get("headline") if isinstance(resolved.get("headline"), Mapping) else {}
    pq = prior_h.get("quadrant") if isinstance(prior_h.get("quadrant"), Mapping) else {}
    cx, cy, px, py = q.get("x"), q.get("y"), pq.get("x"), pq.get("y")
    if _is_num(cx) and _is_num(cy) and _is_num(px) and _is_num(py):
        dx = round(float(cx) - float(px), 2)
        dy = round(float(cy) - float(py), 2)
        headline["one_month_vector"] = {
            "dx": dx, "dy": dy, "status": "PRESENT", "null_reason": None,
        }
        headline["transition_distance"] = round((dx * dx + dy * dy) ** 0.5, 2)
        headline["movement_state"] = None
    prior_state = headline.get("prior_state")
    if isinstance(prior_state, dict):
        headline["prior_state"] = {
            "state_id": prior_h.get("state_id"),
            "effective_date": effective_date_of(resolved),
            "method_version": prior_h.get("method_version"),
        }


def apply_producer_prior_seal(
    body: Mapping[str, Any],
    stored: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Fail-closed producer seal after compose.

    Composers should already have resolved the prior publication. If a
    ``COMPARABLE`` block still names a prior whose effective date is not
    strictly earlier than this build, either substitute the resolved earlier
    publication and recompute the deltas from it, or emit the typed null —
    never return the body unchanged (never a fabricated 0 delta against the
    same publication).
    """
    out = dict(body)
    current_eff = effective_date_of(out)
    changes = out.get("changes")
    if isinstance(changes, Mapping) and changes.get("comparability") == "COMPARABLE":
        prior_eff = changes.get("prior_effective_date")
        if not is_strictly_earlier(prior_eff, current_eff):
            resolved = resolve_publication_prior(stored, current_eff)
            headline = dict(out["headline"]) if isinstance(out.get("headline"), Mapping) else {}
            if resolved is None:
                out["changes"] = no_earlier_publication()
                if headline:
                    _null_headline_movement(headline)
                    out["headline"] = headline
            else:
                out["changes"] = _recompute_changes_from_resolved(changes, resolved)
                if headline:
                    _recompute_headline_from_resolved(headline, resolved)
                    out["headline"] = headline
            return out

    headline = out.get("headline")
    if isinstance(headline, Mapping):
        prior_state = headline.get("prior_state")
        prior_eff = (
            prior_state.get("effective_date") if isinstance(prior_state, Mapping) else None
        )
        vec = headline.get("one_month_vector")
        vec_present = isinstance(vec, Mapping) and vec.get("status") == "PRESENT"
        if vec_present and not is_strictly_earlier(prior_eff, current_eff):
            resolved = resolve_publication_prior(stored, current_eff)
            stamped = dict(headline)
            if resolved is None:
                _null_headline_movement(stamped)
            else:
                _recompute_headline_from_resolved(stamped, resolved)
            out["headline"] = stamped
    return out

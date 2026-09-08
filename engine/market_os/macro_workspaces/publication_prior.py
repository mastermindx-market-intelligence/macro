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


def _quadrant_from_prior_deltas(changes: Mapping[str, Any]) -> dict[str, Any]:
    values: list[Any] = []
    for delta in changes.get("deltas") or []:
        if isinstance(delta, Mapping):
            values.append(delta.get("prior_value"))
    return {
        "x": values[0] if len(values) > 0 else None,
        "y": values[1] if len(values) > 1 else None,
    }


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


def apply_producer_prior_seal(
    body: Mapping[str, Any],
    stored: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Fail-closed producer seal after compose.

    Composers should already have resolved the prior publication. If a
    ``COMPARABLE`` block still names a prior whose effective date is not
    strictly earlier than this build, replace it with the typed null — never
    a fabricated 0 delta against the same publication.
    """
    out = dict(body)
    current_eff = effective_date_of(out)
    changes = out.get("changes")
    if not isinstance(changes, Mapping):
        return out
    if changes.get("comparability") != "COMPARABLE":
        return out
    prior_eff = changes.get("prior_effective_date")
    if is_strictly_earlier(prior_eff, current_eff):
        return out
    resolved = resolve_publication_prior(stored, current_eff)
    if resolved is None:
        out["changes"] = no_earlier_publication()
    return out

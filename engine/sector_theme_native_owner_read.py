"""P2d: bind one U.S. research preview to the incumbent rights and membership readers.

This function is a **fail-closed read boundary**, not an identity mapper, rights
registry, collector, data scheduler, vintage authenticator, customer publisher,
risk/entry signal, or historical score. It uses the *existing* source-use
kernel and native PIT basket reader. A current snapshot is not a receipt of
when that snapshot first became knowable.

A successful call only produces the same RESEARCH_PREVIEW_ONLY packet as the
pure P2 bridge. Data OS security/issuer and price/parent/original-vintage
custody remain separate, explicitly unproven downstream owner obligations.

The optional reader parameters exist solely for isolated deterministic tests;
they are not a way to grant privileges in an actual product publisher.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from datetime import date
import re
from zoneinfo import ZoneInfo

from engine.sector_theme_owner_bridge import (
    PURPOSE, _day, _held, _name, _timestamp, preview_us_theme_packet,
)

SCHEMA = "sector_theme_owner_preview/v1"
HOUSE_SOURCE = "data/baskets/membership.json"
MARKET = "us_today"
PHASE = "read_use"
NY = ZoneInfo("America/New_York")
_NATIVE_COMPARE = (
    "suite", "basket_id", "asof", "snapshot_date", "pit", "basis", "source_shape"
)


def _valid_members(value: object) -> list[str] | None:
    if (not isinstance(value, list) or not value
            or any(_name(member) is None for member in value)):
        return None
    if len(value) != len(set(value)):
        return None
    return sorted(value)


def _use_request(packet: Mapping) -> dict | None:
    request = packet.get("source_use_request")
    if not isinstance(request, Mapping):
        return None
    if (request.get("source_ref") != HOUSE_SOURCE
            or request.get("purpose") != PURPOSE
            or request.get("phase") != PHASE
            or request.get("market") != MARKET):
        return None
    sha = request.get("source_sha256")
    generation = _name(request.get("generation_id"))
    if (type(sha) is not str or re.fullmatch(r"[0-9a-f]{64}", sha) is None
            or generation is None or len(generation) > 160
            or re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", generation) is None):
        return None
    return {
        "source_ref": HOUSE_SOURCE, "source_sha256": sha,
        "generation_id": generation, "purpose": PURPOSE,
        "phase": PHASE, "market": MARKET,
    }


def preview_native_us_theme(
    packet: object, *,
    member_read: Callable | None = None,
    use_read: Callable | None = None,
) -> dict:
    """One read-only owner-bound P2 preview; refuses before unqualified source reads.

    Default read functions are the actual incumbent owner APIs. No permission
    for this purpose has been inferred from the house-curated source or the
    separate selection_cohort_internal_capture use path.
    """
    if not isinstance(packet, Mapping):
        return _held("missing_owner_packet")
    market, claimed = packet.get("market"), packet.get("membership_asof")
    if (not isinstance(market, Mapping) or not isinstance(claimed, Mapping)
            or market.get("origin") != "owner_reported"
            or packet.get("membership_mode") != "PIT_AS_KNOWN"):
        return _held("requires_owner_reported_pit_packet")
    basket_id = _name(packet.get("group_id"))
    asof = _day(claimed.get("asof"))
    end = _timestamp(market.get("period_end"))
    decision = _timestamp(market.get("decision_at"))
    if basket_id is None or asof is None or end is None or decision is None:
        return _held("missing_canonical_basket_or_market_clock")
    if (end > decision
            or asof > end.astimezone(NY).date()):
        return _held("native_membership_day_after_local_market_close")
    request = _use_request(packet)
    if request is None:
        return _held("unsupported_source_use_request")

    if use_read is None:
        from engine.theme_graph.rights_use import current_use_verdict
        use_read = current_use_verdict
    try:
        verdict = use_read(dict(request))
    except Exception:  # noqa: BLE001 - owner failure is never use permission
        return _held("source_use_owner_unavailable")
    if (not isinstance(verdict, Mapping)
            or verdict.get("verdict") != "ALLOWED"
            or _name(verdict.get("registry_revision")) is None
            or any(verdict.get(key) != value for key, value in request.items())):
        return _held("source_use_owner_denied")
    caller_rights = packet.get("use_verdict")
    if caller_rights is not None and (
        not isinstance(caller_rights, Mapping)
        or any(caller_rights.get(key) != verdict.get(key) for key in (
            "verdict", "purpose", "source_ref", "source_sha256",
            "generation_id", "registry_revision"
        ))
    ):
        return _held("caller_rights_verdict_disagrees_with_owner")

    # The incumbent US nightly owner is the only source of its PIT membership
    # read. This is a fresh *current* owner read, not original first-availability
    # evidence. Preserve the original receipt requirement in the P2 bridge.
    if member_read is None:
        from engine.basket_membership_pit import members_asof
        member_read = members_asof
    try:
        native = member_read(basket_id, asof.isoformat(), suite="baskets")
    except Exception:  # noqa: BLE001 - no fallback to current roster
        return _held("native_membership_owner_unavailable")
    if not isinstance(native, Mapping):
        return _held("native_membership_not_pit")
    if (native.get("pit") is not True or native.get("basis") != "pit_snapshot"
            or native.get("source_shape") != "membership"):
        return _held("native_membership_not_pit")
    native_members = _valid_members(native.get("members"))
    claimed_members = _valid_members(claimed.get("members"))
    snap = _day(native.get("snapshot_date"))
    if (native_members is None or claimed_members is None
            or snap is None or snap > asof or _day(native.get("asof")) != asof):
        return _held("native_membership_owner_disagreement")
    if (any(native.get(key) != claimed.get(key) for key in _NATIVE_COMPARE)
            or native_members != claimed_members
            or native.get("basket_id") != basket_id
            or native.get("suite") != "baskets"):
        return _held("native_membership_owner_disagreement")

    try:
        owner_snapshot = deepcopy(dict(packet))
        owner_snapshot["membership_asof"] = {
            **dict(claimed), **{key: native.get(key) for key in _NATIVE_COMPARE},
            "members": native_members,
        }
        owner_snapshot["use_verdict"] = deepcopy(dict(verdict))
        return preview_us_theme_packet(owner_snapshot)
    except (TypeError, ValueError, OverflowError, AttributeError):
        return _held("native_owner_projection_failed")

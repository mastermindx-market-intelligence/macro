"""WEB-P1 G1: explicit PRIVATE-only official-first-print acceptance witness.

This is a dormant adapter over the *existing* official RSS preview, Press scorer,
IntelligenceDesk SQLite/JSON owner and source ack. No daemon, scheduler, event
ledger, quote feed, public publisher, rights issuer or parallel cursor is created.

Only a currently bound single-writer may supply the incumbent press-state
identity checkpoint callback. This module has no live caller and does NOT grant
source copyright/use rights; its path restrictions prohibit the public Desk
sink. See held PR #8704. Same-GUID corrections remain News owner's responsibility.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
from typing import Any, Callable

from engine.marketing.breaking_feed import (
    OfficialFeedPreview, ack_official_preview,
    _OFFICIAL_PREVIEW_URLS, _qualified_official_item_url,
)

log = logging.getLogger(__name__)

_PRIVATE_DIR = Path("data/marketing/press")


def _private_targets(root: Path | str) -> tuple[Path, Path] | None:
    """Allow only the incumbent host-local private Desk filenames.

    Refuse symlinked parents/files, directory traversal and public website
    destinations before *any* input source or identity/store mutation.
    """
    root_path = Path(root).resolve()
    private = root_path / _PRIVATE_DIR
    candidate = Path(root) / _PRIVATE_DIR
    if candidate.resolve() != private:
        return None
    db_path = candidate / "intelligence.db"
    snapshot_path = candidate / "intelligence.json"
    if db_path.resolve() != private / db_path.name:
        return None
    if snapshot_path.resolve() != private / snapshot_path.name:
        return None
    return db_path, snapshot_path


def _packet_event_ids(packets: object) -> set[str]:
    """Event evidence actually present in an incumbent Desk packet list."""
    if not isinstance(packets, list):
        return set()
    from engine.marketing.intelligence_desk import PACKET_SCHEMA
    return {
        str(row["event_id"])
        for packet in packets
        if isinstance(packet, dict) and packet.get("schema") == PACKET_SCHEMA
        for row in (packet.get("evidence")
                    if isinstance(packet.get("evidence"), list) else [])
        if isinstance(row, dict) and row.get("event_id")
    }


def accept_private_official_preview(
    preview: OfficialFeedPreview,
    *,
    root: Path | str,
    now: datetime,
    marketing_cfg: dict,
    press_cfg: dict,
    current_state: dict[str, Any],
    persist_identity: Callable[[dict[str, Any]], None],
    load_identity: Callable[[], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Test/validate existing official -> scorer -> private Desk -> source ack.

    The caller, not this adapter, must already hold the one-writer custody for
    the incumbent press state and provide its synchronous durable identity
    checkpoint. Publishing/copyright rights are NOT implied by any outcome.
    Production must not call this until source rights, correction authority,
    admission and real consumer gates are independently proven.

    Failure after SQLite commit but before JSON projection retains unconsumed
    original official source. Failure DURING ack can partially write seen/state:
    it propagates to the same original owner for effect reconciliation, NEVER
    silently replays it or moves to another state store.
    """
    if (not isinstance(preview, OfficialFeedPreview)
            or preview.root_key != str(Path(root).resolve())
            or not isinstance(current_state, dict)
            or not callable(persist_identity)
            or not callable(load_identity)
            or not isinstance(marketing_cfg, dict)
            or not isinstance(press_cfg, dict)
            or not isinstance(now, datetime)
            or now.tzinfo is None or now.utcoffset() is None):
        return {"status": "UNQUALIFIED_SOURCE_PREVIEW"}

    targets = _private_targets(root)
    if targets is None:
        return {"status": "PRIVATE_DESTINATION_NOT_ADMITTED"}
    wire_cfg = press_cfg.get("wire")
    intel_cfg = wire_cfg.get("intelligence") if isinstance(wire_cfg, dict) else None
    if not isinstance(intel_cfg, dict):
        return {"status": "SOURCE_NOT_QUALIFIED"}

    if not preview.items:
        # Quiet provider-fetch state is acked by the original source owner,
        # never as a fabricated downstream News event receipt.
        return {"status": "NO_EVENTS_TO_ACCEPT"}

    expected = {str(row.get("id") or "") for row in preview.items
                if isinstance(row, dict)}
    if len(expected) != len(preview.items) or "" in expected:
        return {"status": "SOURCE_NOT_QUALIFIED"}

    # A frozen dataclass is not a signed source-rights or publisher-identity
    # receipt. Repeat the same source-owner checks before the private store:
    # an internal caller must not smuggle a wire/third-party item by forging
    # OfficialFeedPreview(items=...). This STILL does not establish licensing.
    for row in preview.items:
        source = str(row.get("source") or "")
        raw_date = row.get("published_at")
        if (source not in _OFFICIAL_PREVIEW_URLS
                or row.get("source_tier") != "official"
                or not _qualified_official_item_url(row.get("url"), source)
                or not isinstance(raw_date, str) or not raw_date.strip()):
            return {"status": "SOURCE_NOT_QUALIFIED"}
        try:
            publication = datetime.fromisoformat(
                raw_date.replace("Z", "+00:00")
            )
        except ValueError:
            return {"status": "SOURCE_NOT_QUALIFIED"}
        if (publication.tzinfo is None or publication.utcoffset() is None
                or publication > now + timedelta(minutes=5)):
            return {"status": "SOURCE_NOT_QUALIFIED"}

    from engine.marketing.press_lane import run_press_tick
    from engine.marketing.intelligence_desk import update_intelligence_desk

    # Never persist scoring/corrob/budget state ahead of downstream admission.
    # Only the two incumbent deterministic story identity keys are permitted
    # to cross the checkpoint boundary. No newly minted identity system.
    working_state = deepcopy(current_state)
    cfg = dict(marketing_cfg)
    breaking_cfg = dict(cfg.get("breaking") or {})
    breaking_cfg["llm"] = {"enabled": False}
    cfg["breaking"] = breaking_cfg
    try:
        result = run_press_tick(
            list(preview.items),
            root=root, now=now, cfg=cfg, press_cfg=press_cfg,
            state=working_state, seen_ids=set(), dry_run=True,
            prime=False, spool=False, llm_override=lambda *_: None,
        )
    except Exception as exc:  # noqa: BLE001
        log.error("official-private scorer failed: %s", type(exc).__name__)
        return {"status": "SCORING_FAILED"}
    packets = result.get("intelligence")
    if not expected.issubset(_packet_event_ids(packets)):
        return {"status": "SOURCE_NOT_QUALIFIED"}

    if not all(isinstance(working_state.get(key), dict)
               for key in ("story_spine", "intel_claims")):
        return {"status": "IDENTITY_CONTEXT_UNAVAILABLE"}
    identity_update = dict(current_state)
    for key in ("story_spine", "intel_claims"):
        identity_update[key] = working_state[key]
    try:
        persist_identity(identity_update)
    except Exception as exc:  # noqa: BLE001
        log.error("official-private identity checkpoint failed: %s",
                  type(exc).__name__)
        return {"status": "IDENTITY_CHECKPOINT_FAILED"}

    # A callback returning successfully is not proof the incumbent state
    # file actually changed. Require a *separate read* through that SAME
    # owner before any SQLite/store effect; a lost story identity causes
    # a second story after an interrupted post-commit projection.
    try:
        observed_identity = load_identity()
    except Exception as exc:  # noqa: BLE001
        log.error("official-private identity readback failed: %s",
                  type(exc).__name__)
        return {"status": "IDENTITY_CHECKPOINT_UNVERIFIED"}
    if (not isinstance(observed_identity, dict)
            or any(observed_identity.get(key) != identity_update[key]
                   for key in ("story_spine", "intel_claims"))):
        return {"status": "IDENTITY_CHECKPOINT_UNVERIFIED"}

    try:
        served = update_intelligence_desk(
            packets,
            root=root, now=now, cfg=intel_cfg,
            db_path=targets[0], snapshot_path=targets[1],
        )
        if not isinstance(served, dict):
            return {"status": "SOURCE_NOT_SERVED"}
        stored = json.loads(targets[1].read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        log.error("official-private store/projection failed: %s",
                  type(exc).__name__)
        return {"status": "STORE_OR_PROJECTION_FAILED"}

    if (not isinstance(stored, dict)
            or not expected.issubset(_packet_event_ids(served.get("stories")))
            or not expected.issubset(_packet_event_ids(stored.get("stories")))):
        return {"status": "SOURCE_NOT_SERVED"}

    # ack_official_preview checks the unchanged original state/seen digest.
    # Let partial ack write exceptions propagate for same-carrier recovery.
    if not ack_official_preview(root, preview, accepted_ids=expected):
        return {"status": "SOURCE_CAS_REFUSED"}
    return {"status": "ACCEPTED", "accepted_ids": sorted(expected)}

"""Pure current-state reducer for immutable qbus news revisions.

The reducer owns no persistence and reads no ambient state. It refuses arbitrary
last-write-wins behavior across incomparable provider clock domains, preserves
explicit withdrawals, and returns exact ticker-index deltas for a transactional
store to apply atomically with the state transition.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from engine.qbus_news_contract import NewsRevision

STATE_SCHEMA = "qbus.news_state.v1"
REDUCTION_SCHEMA = "qbus.news_reduction.v1"
_DIRECT_DOMAINS = {
    "benzinga_article_updated",
    "benzinga_stream_event",
    "benzinga_rest_observed",
}
_MIRROR_DOMAINS = {"massive_benzinga_system_updated"}


class NewsReductionError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"qbus_news_reducer:{code}")


@dataclass(frozen=True, slots=True)
class NewsState:
    schema: str
    source: str
    source_item_id: str
    status: str
    current_revision_id: str
    content_hash: str
    transport: str
    action_explicit: bool
    published_at: datetime | None
    updated_at: datetime | None
    source_event_at: datetime | None
    version_at: datetime
    version_clock_domain: str
    first_received_at: datetime
    last_received_at: datetime
    title: str
    url: str
    teaser: str
    provider_tickers: tuple[str, ...]
    channels: tuple[str, ...]
    tags: tuple[str, ...]
    body_sha256: str


@dataclass(frozen=True, slots=True)
class Reduction:
    schema: str
    disposition: str
    reason: str
    state: NewsState
    added_tickers: tuple[str, ...]
    removed_tickers: tuple[str, ...]


def _is_direct(domain: str) -> bool:
    return domain in _DIRECT_DOMAINS


def _is_mirror(domain: str) -> bool:
    return domain in _MIRROR_DOMAINS


def _state_from_revision(
    previous: NewsState | None, revision: NewsRevision
) -> NewsState:
    first = (
        revision.received_at
        if previous is None
        else min(previous.first_received_at, revision.received_at)
    )
    last = (
        revision.received_at
        if previous is None
        else max(previous.last_received_at, revision.received_at)
    )
    withdrawn = revision.action == "removed"
    return NewsState(
        schema=STATE_SCHEMA,
        source=revision.source,
        source_item_id=revision.source_item_id,
        status="withdrawn" if withdrawn else "active",
        current_revision_id=revision.revision_id,
        content_hash=revision.content_hash,
        transport=revision.transport,
        action_explicit=revision.action_explicit,
        published_at=revision.published_at,
        updated_at=revision.updated_at,
        source_event_at=revision.source_event_at,
        version_at=revision.version_at,
        version_clock_domain=revision.version_clock_domain,
        first_received_at=first,
        last_received_at=last,
        title="" if withdrawn else revision.title,
        url="" if withdrawn else revision.url,
        teaser="" if withdrawn else revision.teaser,
        provider_tickers=() if withdrawn else revision.provider_tickers,
        channels=() if withdrawn else revision.channels,
        tags=() if withdrawn else revision.tags,
        body_sha256="" if withdrawn else revision.body_sha256,
    )


def _touch_receipt(state: NewsState, revision: NewsRevision) -> NewsState:
    first = min(state.first_received_at, revision.received_at)
    last = max(state.last_received_at, revision.received_at)
    if first == state.first_received_at and last == state.last_received_at:
        return state
    return replace(state, first_received_at=first, last_received_at=last)


def _delta(
    previous: NewsState | None, current: NewsState
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    before = (
        set(previous.provider_tickers)
        if previous is not None and previous.status == "active"
        else set()
    )
    after = set(current.provider_tickers) if current.status == "active" else set()
    return tuple(sorted(after - before)), tuple(sorted(before - after))


def _result(
    disposition: str,
    reason: str,
    state: NewsState,
    previous: NewsState | None = None,
) -> Reduction:
    added, removed = _delta(previous, state)
    return Reduction(
        schema=REDUCTION_SCHEMA,
        disposition=disposition,
        reason=reason,
        state=state,
        added_tickers=added,
        removed_tickers=removed,
    )


def _unchanged(
    disposition: str, reason: str, state: NewsState
) -> Reduction:
    return Reduction(
        schema=REDUCTION_SCHEMA,
        disposition=disposition,
        reason=reason,
        state=state,
        added_tickers=(),
        removed_tickers=(),
    )


def reduce_revision(
    previous: NewsState | None,
    incoming: NewsRevision,
    *,
    restoration_qualified: bool = False,
) -> Reduction:
    """Reduce one immutable source observation into current state.

    restoration_qualified is a trusted-caller decision. This function never
    derives it from provider payload fields or delivery route.
    """
    if previous is None:
        state = _state_from_revision(None, incoming)
        if state.status == "withdrawn":
            return _result("withdrawn", "first_withdrawal", state, None)
        return _result("accepted", "first_active_revision", state, None)

    if (
        previous.source != incoming.source
        or previous.source_item_id != incoming.source_item_id
    ):
        raise NewsReductionError("source_item_mismatch")

    if incoming.revision_id == previous.current_revision_id:
        return _unchanged(
            "duplicate", "same_revision", _touch_receipt(previous, incoming)
        )

    incoming_direct = _is_direct(incoming.version_clock_domain)
    incoming_mirror = _is_mirror(incoming.version_clock_domain)
    previous_direct = _is_direct(previous.version_clock_domain)
    previous_mirror = _is_mirror(previous.version_clock_domain)

    if not (incoming_direct or incoming_mirror):
        raise NewsReductionError("unknown_incoming_clock_domain")
    if not (previous_direct or previous_mirror):
        raise NewsReductionError("unknown_previous_clock_domain")

    if incoming.action == "removed":
        if incoming_mirror or not incoming.action_explicit:
            return _unchanged("conflict", "unqualified_withdrawal", previous)
        if previous.status == "withdrawn":
            if incoming.version_clock_domain == previous.version_clock_domain:
                if incoming.version_at < previous.version_at:
                    return _unchanged(
                        "stale", "older_same_domain_revision", previous
                    )
                if incoming.version_at == previous.version_at:
                    return _unchanged(
                        "conflict", "same_version_content_conflict", previous
                    )
            state = _state_from_revision(previous, incoming)
            return _result("withdrawn", "newer_withdrawal", state, previous)
        if (
            previous_direct
            and incoming.source_event_at is not None
            and previous.updated_at is not None
            and incoming.source_event_at < previous.updated_at
        ):
            return _unchanged(
                "stale", "older_explicit_withdrawal", previous
            )
        state = _state_from_revision(previous, incoming)
        return _result(
            "withdrawn", "explicit_source_withdrawal", state, previous
        )

    if previous.status == "withdrawn":
        if incoming_mirror:
            return _unchanged(
                "stale", "mirror_cannot_restore_withdrawal", previous
            )
        if not restoration_qualified:
            return _unchanged(
                "stale",
                "withdrawn_requires_qualified_restoration",
                previous,
            )
        state = _state_from_revision(previous, incoming)
        return _result(
            "accepted", "qualified_restoration", state, previous
        )

    if previous_direct and incoming_mirror:
        if previous.content_hash == incoming.content_hash:
            return _unchanged(
                "duplicate",
                "mirror_same_content",
                _touch_receipt(previous, incoming),
            )
        return _unchanged(
            "conflict", "lower_authority_mirror_conflict", previous
        )

    if previous_mirror and incoming_direct:
        state = _state_from_revision(previous, incoming)
        return _result(
            "accepted",
            "higher_authority_source_revision",
            state,
            previous,
        )

    if incoming.version_clock_domain == previous.version_clock_domain:
        if incoming.version_at < previous.version_at:
            return _unchanged(
                "stale", "older_same_domain_revision", previous
            )
        if incoming.version_at == previous.version_at:
            if incoming.content_hash == previous.content_hash:
                return _unchanged(
                    "duplicate",
                    "same_version_same_content",
                    _touch_receipt(previous, incoming),
                )
            return _unchanged(
                "conflict", "same_version_content_conflict", previous
            )
        state = _state_from_revision(previous, incoming)
        return _result(
            "accepted", "newer_same_domain_revision", state, previous
        )

    if previous.content_hash == incoming.content_hash:
        return _unchanged(
            "duplicate",
            "cross_domain_same_content",
            _touch_receipt(previous, incoming),
        )
    return _unchanged(
        "conflict", "incomparable_clock_domains", previous
    )

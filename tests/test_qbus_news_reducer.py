from __future__ import annotations

from datetime import timedelta

import pytest

from engine.qbus_news_contract import normalize_news
from engine.qbus_news_reducer import NewsReductionError, reduce_revision
from tests.test_qbus_news_contract import RECEIVED, massive_payload, rest_payload, ws_payload


def rest_revision(**kw):
    return normalize_news(rest_payload(**kw), transport="benzinga_rest", received_at=RECEIVED)


def ws_revision(*, received_at=RECEIVED, **kw):
    return normalize_news(ws_payload(**kw), transport="benzinga_ws", received_at=received_at)


def massive_revision(*, received_at=RECEIVED, **kw):
    return normalize_news(massive_payload(**kw), transport="massive_benzinga_v2", received_at=received_at)


def test_first_article_is_accepted_and_adds_tickers():
    incoming = rest_revision(tickers=("NVDA", "AMD"))
    out = reduce_revision(None, incoming)
    assert out.disposition == "accepted"
    assert out.reason == "first_active_revision"
    assert out.state.status == "active"
    assert out.state.current_revision_id == incoming.revision_id
    assert out.state.first_received_at == RECEIVED
    assert out.added_tickers == ("AMD", "NVDA")
    assert out.removed_tickers == ()


def test_exact_current_revision_is_duplicate_and_keeps_state():
    incoming = rest_revision()
    first = reduce_revision(None, incoming)
    again = reduce_revision(first.state, incoming)
    assert again.disposition == "duplicate"
    assert again.state == first.state
    assert again.added_tickers == () and again.removed_tickers == ()


def test_newer_same_domain_update_is_accepted_with_atomic_ticker_delta():
    first = reduce_revision(None, rest_revision(tickers=("NVDA", "AMD"))).state
    newer = normalize_news(
        rest_payload(updated="Sun, 04 Oct 2026 17:59:01 -0400", title="Updated headline", tickers=("NVDA", "AVGO")),
        transport="benzinga_rest",
        received_at=RECEIVED + timedelta(minutes=1),
    )
    out = reduce_revision(first, newer)
    assert out.disposition == "accepted"
    assert out.state.title == "Updated headline"
    assert out.added_tickers == ("AVGO",)
    assert out.removed_tickers == ("AMD",)
    assert out.state.first_received_at == RECEIVED
    assert out.state.last_received_at == RECEIVED + timedelta(minutes=1)


def test_older_same_domain_update_is_stale():
    current = reduce_revision(None, normalize_news(
        rest_payload(updated="Sun, 04 Oct 2026 18:00:01 -0400"),
        transport="benzinga_rest", received_at=RECEIVED,
    )).state
    older = normalize_news(
        rest_payload(updated="Sun, 04 Oct 2026 17:59:01 -0400", title="Old headline"),
        transport="benzinga_rest", received_at=RECEIVED + timedelta(minutes=1),
    )
    out = reduce_revision(current, older)
    assert out.disposition == "stale"
    assert out.reason == "older_same_domain_revision"
    assert out.state == current


def test_same_version_different_content_is_conflict_not_last_write_wins():
    current = reduce_revision(None, rest_revision(title="Original")).state
    conflict = rest_revision(title="Different bytes at same provider version")
    out = reduce_revision(current, conflict)
    assert out.disposition == "conflict"
    assert out.reason == "same_version_content_conflict"
    assert out.state == current


def test_explicit_delete_with_newer_direct_event_withdraws_and_removes_index_memberships():
    current = reduce_revision(None, rest_revision(tickers=("NVDA", "AMD"))).state
    deleted = ws_payload(action="Deleted", event_ts="2026-10-04T21:59:05Z")
    deleted["data"].pop("content")
    incoming = normalize_news(deleted, transport="benzinga_ws", received_at=RECEIVED + timedelta(minutes=1))
    out = reduce_revision(current, incoming)
    assert out.disposition == "withdrawn"
    assert out.state.status == "withdrawn"
    assert out.state.provider_tickers == ()
    assert out.removed_tickers == ("AMD", "NVDA")
    assert out.added_tickers == ()


def test_stale_direct_update_after_withdrawal_cannot_resurrect():
    active = reduce_revision(None, rest_revision()).state
    deleted_payload = ws_payload(action="deleted", event_ts="2026-10-04T22:00:00Z")
    deleted_payload["data"].pop("content")
    withdrawn = reduce_revision(
        active,
        normalize_news(deleted_payload, transport="benzinga_ws", received_at=RECEIVED + timedelta(minutes=1)),
    ).state
    later_delivery_of_old_article = normalize_news(
        rest_payload(updated="Sun, 04 Oct 2026 17:58:01 -0400"),
        transport="benzinga_rest", received_at=RECEIVED + timedelta(minutes=2),
    )
    out = reduce_revision(withdrawn, later_delivery_of_old_article)
    assert out.disposition == "stale"
    assert out.reason == "withdrawn_requires_qualified_restoration"
    assert out.state == withdrawn


def test_qualified_direct_reinstatement_can_restore_with_new_revision():
    active = reduce_revision(None, rest_revision()).state
    deleted_payload = ws_payload(action="deleted", event_ts="2026-10-04T22:00:00Z")
    deleted_payload["data"].pop("content")
    withdrawn = reduce_revision(
        active,
        normalize_news(deleted_payload, transport="benzinga_ws", received_at=RECEIVED + timedelta(minutes=1)),
    ).state
    restored = ws_revision(
        received_at=RECEIVED + timedelta(minutes=2),
        action="created",
        updated="Sun, 04 Oct 2026 18:01:01 -0400",
        event_ts="2026-10-04T22:01:02Z",
        title="Restored corrected story",
    )
    held = reduce_revision(withdrawn, restored)
    assert held.disposition == "stale"
    accepted = reduce_revision(withdrawn, restored, restoration_qualified=True)
    assert accepted.disposition == "accepted"
    assert accepted.reason == "qualified_restoration"
    assert accepted.state.status == "active"
    assert accepted.state.title == "Restored corrected story"


def test_massive_mirror_same_content_does_not_take_over_direct_clock_domain():
    direct = rest_revision()
    current = reduce_revision(None, direct).state
    mirror = massive_revision()
    out = reduce_revision(current, mirror)
    assert out.disposition == "duplicate"
    assert out.reason == "mirror_same_content"
    assert out.state == current
    assert out.state.version_clock_domain == "benzinga_article_updated"


def test_massive_different_content_cannot_overwrite_direct_revision():
    current = reduce_revision(None, rest_revision(title="Direct source")).state
    mirror = massive_revision(title="Mirror differs")
    out = reduce_revision(current, mirror)
    assert out.disposition == "conflict"
    assert out.reason == "lower_authority_mirror_conflict"
    assert out.state == current


def test_direct_revision_supersedes_massive_mirror_without_comparing_incomparable_clocks():
    mirror = massive_revision(updated="2026-10-04T23:30:00Z", title="Mirror copy")
    current = reduce_revision(None, mirror).state
    direct = rest_revision(title="Direct source")
    out = reduce_revision(current, direct)
    assert out.disposition == "accepted"
    assert out.reason == "higher_authority_source_revision"
    assert out.state.title == "Direct source"
    assert out.state.version_clock_domain == "benzinga_article_updated"


def test_massive_mirror_cannot_restore_explicit_direct_withdrawal_even_when_qualified():
    active = reduce_revision(None, rest_revision()).state
    deleted_payload = ws_payload(action="deleted", event_ts="2026-10-04T22:00:00Z")
    deleted_payload["data"].pop("content")
    withdrawn = reduce_revision(
        active,
        normalize_news(deleted_payload, transport="benzinga_ws", received_at=RECEIVED + timedelta(minutes=1)),
    ).state
    mirror = massive_revision(received_at=RECEIVED + timedelta(minutes=2), updated="2026-10-04T23:30:00Z")
    out = reduce_revision(withdrawn, mirror, restoration_qualified=True)
    assert out.disposition == "stale"
    assert out.reason == "mirror_cannot_restore_withdrawal"
    assert out.state == withdrawn


def test_direct_vs_mirror_arrival_order_converges_to_direct_state():
    direct = rest_revision(title="Canonical direct")
    mirror = massive_revision(title="Canonical direct")
    a = reduce_revision(reduce_revision(None, direct).state, mirror).state
    b = reduce_revision(reduce_revision(None, mirror).state, direct).state
    assert a.status == b.status == "active"
    assert a.current_revision_id == b.current_revision_id == direct.revision_id
    assert a.content_hash == b.content_hash == direct.content_hash
    assert a.version_clock_domain == b.version_clock_domain == "benzinga_article_updated"


def test_wrong_source_item_is_rejected_without_mutating_state():
    current = reduce_revision(None, rest_revision(item_id=1)).state
    with pytest.raises(NewsReductionError) as exc:
        reduce_revision(current, rest_revision(item_id=2))
    assert exc.value.code == "source_item_mismatch"
    assert current.source_item_id == "1"


def test_first_received_at_preserves_earliest_observed_receipt():
    first = normalize_news(rest_payload(), transport="benzinga_rest", received_at=RECEIVED + timedelta(minutes=5))
    state = reduce_revision(None, first).state
    replay_with_earlier_known_receipt = normalize_news(rest_payload(), transport="benzinga_rest", received_at=RECEIVED)
    out = reduce_revision(state, replay_with_earlier_known_receipt)
    assert out.disposition == "duplicate"
    assert out.state.first_received_at == RECEIVED
    assert out.state.last_received_at == RECEIVED + timedelta(minutes=5)

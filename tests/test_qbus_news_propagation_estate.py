"""NE-A3 cross-read-model propagation proofs for the qbus news estate.

Frozen lane test list (run ne-a3-prop-20261022-r1). Each test proves one
propagation contract: a correction, a provider removal, a rights withdrawal and
an equivalent administrative rights renewal must hold identically across EVERY
current read model — the store projection (``news_state_projection``), the
snapshot row, the story detail, the grouped (cluster) member, the change log
(raw and projected), evidence, news flow, the ``/api/ticker-news`` HTTP reads
and the SSE replay. Immutable history (``news_revisions``, and a raw journal
row at its own sequence) is the ONLY permitted carrier of superseded or
withdrawn protected text.

The rights-renewal test (d) ignores exactly the receipt identity fields the
snapshot response carries in ``rights_basis``: ``receipt_id``, ``effective_at``
and ``expires_at``. Every news-bearing field must be identical.
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta, timezone
import json
import sqlite3

from fastapi import FastAPI
from fastapi.testclient import TestClient

from engine import qbus_news_store as m
from engine.qbus_news_contract import normalize_news
from engine.qbus_news_receipts import parse_rights_receipt


UTC = timezone.utc
T0 = datetime(2026, 10, 5, 20, 0, tzinfo=UTC)
SEC = "SEC:US-XNAS-NVDA"

# Frozen propagation fixtures. Rev1 wording shares no substring with rev2
# wording, so a resurrected revision can never hide inside newer prose.
T1_TITLE = "Nvidia launches its new AI accelerator"
T1_TEASER = "teaser-original-accelerator"
T1_URL = "https://www.benzinga.com/news/12"
T2_TITLE = "Nvidia unveils corrected roadmap for accelerator line"
T2_TEASER = "teaser-corrected-accelerator"
Y_TITLE = "Nvidia launches new AI accelerator"
Y_TEASER = "teaser-member-y"


# ---------------------------------------------------------------- helpers


def _serialize(result: object) -> str:
    """JSON/repr-serialize any read result (dataclass, mapping, HTTP, SSE text)."""
    if isinstance(result, str):
        return result
    if isinstance(result, bytes):
        return result.decode("utf-8", "replace")
    if is_dataclass(result):
        result = asdict(result)
    try:
        return json.dumps(result, default=str, sort_keys=True)
    except (TypeError, ValueError):
        return repr(result)


def _assert_absent(result: object, *needles: str) -> None:
    text = _serialize(result)
    for needle in needles:
        assert needle not in text, (
            f"protected text {needle!r} leaked into a current read model: "
            f"{text[:500]!r}"
        )


def _rights():
    return m.NewsReadRights.all_internal()


def _title_only():
    return m.NewsReadRights(
        allowed_sources=frozenset({"benzinga"}),
        allow_title=True,
        allow_url=False,
        allow_teaser=False,
    )


def _excluded():
    return m.NewsReadRights(allowed_sources=frozenset())


def _routed(item_id, title, minute, *, teaser, security_ids=(SEC,)):
    t = T0 + timedelta(minutes=minute)
    revision = normalize_news(
        {
            "id": item_id,
            "created": (t - timedelta(seconds=1)).isoformat(),
            "updated": t.isoformat(),
            "title": title,
            "teaser": teaser,
            "url": f"https://www.benzinga.com/news/{item_id}",
            "stocks": [{"name": "NVDA"}],
            "channels": [{"name": "News"}],
            "tags": [],
        },
        transport="benzinga_rest",
        received_at=t + timedelta(seconds=2),
    )
    return m.RoutedRevision(
        revision=revision,
        security_ids=tuple(security_ids),
        universe_revision="sp500-r1",
    )


def _removed(item_id, *, minute):
    t = T0 + timedelta(minutes=minute)
    revision = normalize_news(
        {
            "id": f"delete-{item_id}",
            "kind": "news",
            "data": {
                "action": "deleted",
                "id": item_id,
                "timestamp": t.isoformat(),
            },
        },
        transport="benzinga_ws",
        received_at=t + timedelta(seconds=1),
    )
    return m.RoutedRevision(
        revision=revision,
        security_ids=(),
        universe_revision="sp500-r1",
    )


def _snap(store, rights=None):
    return store.snapshot(SEC, limit=20, cursor=None, rights=rights or _rights())


def _changes(store, *, after_sequence=0, rights=None, security_id=None):
    effective = rights or _rights()
    if security_id is None:
        return store.changes(
            after_sequence=after_sequence, limit=20, rights=effective
        )
    return store.changes_for_security(
        SEC,
        after_sequence=after_sequence,
        limit=20,
        rights=effective,
    )


def _projected(store, *, after_sequence=0, rights=None):
    return store.projected_changes_for_security(
        SEC,
        after_sequence=after_sequence,
        limit=20,
        rights=rights or _rights(),
    )


def _api_app(monkeypatch, db, *, rights_fn=None, receipt_path=None):
    """Private-API fixture shaped like tests/test_ticker_news_api.py._app."""
    from app import ticker_news

    monkeypatch.setattr(ticker_news, "_news_db_path", lambda: db)
    monkeypatch.setattr(
        ticker_news,
        "_security_for_ticker",
        lambda ticker, now: SEC if ticker.upper() == "NVDA" else None,
    )
    monkeypatch.setattr(ticker_news, "_flow_now", lambda: T0 + timedelta(hours=1))
    if receipt_path is not None:
        monkeypatch.setattr(
            ticker_news, "_rights_receipt_path", lambda: receipt_path
        )
    else:
        def _fixture_rights(user):
            if isinstance(rights_fn, m.NewsReadRights):
                return rights_fn
            return (rights_fn or _rights)()

        monkeypatch.setattr(ticker_news, "_rights_for_user", _fixture_rights)
    monkeypatch.setattr(
        ticker_news,
        "_source_health",
        lambda: {"state": "live", "last_successful_catchup": T0.isoformat()},
    )
    ticker_news._reset_rate_limit_for_tests()
    app = FastAPI()
    app.include_router(ticker_news.router)
    app.dependency_overrides[ticker_news.require_site_full_user] = lambda: {
        "id": "user-1",
        "email": "user@example.test",
    }
    return ticker_news, app


def _sse_frames(ticker_news, *, after_sequence=0, max_cycles=1):
    async def collect():
        return [
            chunk
            async for chunk in ticker_news._sse_events(
                ticker="NVDA",
                user={"id": "user-1"},
                after_sequence=after_sequence,
                poll_seconds=0,
                max_cycles=max_cycles,
            )
        ]

    return "".join(asyncio.run(collect()))


def _receipt_payload(receipt_id, *, effective_at, expires_at):
    return {
        "schema": "qbus.news_rights_receipt.v1",
        "status": "approved",
        "receipt_id": receipt_id,
        "owner_ref": "test/source-rights",
        "source": "benzinga",
        "provider": "alpaca",
        "product_id": "macro-ticker-news",
        "audiences": ["site_full"],
        "effective_at": effective_at,
        "expires_at": expires_at,
        "capabilities": {
            "internal_ingestion": True,
            "historical_retention": True,
            "headline_display": True,
            "source_link_display": True,
            "teaser_display": True,
            "derivative_processing": True,
            "body_display": False,
            "image_display": False,
        },
    }


# ------------------------------------------------- (a) SAME ITEM, NEW REVISION


def test_a_new_revision_is_current_in_projection_snapshot_detail_and_group_member(tmp_path):
    member_y = _routed(11, Y_TITLE, 0, teaser=Y_TEASER)
    original_x = _routed(12, T1_TITLE, 1, teaser=T1_TEASER)
    corrected_x = _routed(12, T2_TITLE, 5, teaser=T2_TEASER)
    assert original_x.revision.revision_id != corrected_x.revision.revision_id

    with m.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        store.commit([member_y, original_x], expected_cursor=None, next_cursor="c1")
        first = _snap(store)
        assert len(first.rows) == 1
        assert first.rows[0].item_count == 2
        story_id = first.rows[0].story_id

        store.commit([corrected_x], expected_cursor="c1", next_cursor="c2")

        snap = _snap(store)
        detail = store.story(story_id, rights=_rights())
        projected = _projected(store, after_sequence=0)

    # Snapshot row carries rev2 and no rev1 text.
    assert len(snap.rows) == 1
    row = snap.rows[0]
    assert row.story_id == story_id
    assert row.source_item_id == "12"
    assert row.title == T2_TITLE
    assert row.teaser == T2_TEASER
    _assert_absent(snap, T1_TITLE, T1_TEASER)

    # Story detail: the grouped member row of the corrected item carries rev2.
    assert detail is not None
    assert detail.item_count == 2
    assert {member.source_item_id for member in detail.members} == {"11", "12"}
    member = next(m for m in detail.members if m.source_item_id == "12")
    assert member.title == T2_TITLE
    assert member.teaser == T2_TEASER
    assert member.received_at == corrected_x.revision.received_at
    _assert_absent(detail, T1_TITLE, T1_TEASER)

    # Projected change view shows the current revision exactly once.
    assert [change.kind for change in projected.rows] == ["upsert"]
    assert projected.rows[0].title == T2_TITLE
    assert projected.rows[0].source_item_id == "12"
    _assert_absent(projected, T1_TITLE, T1_TEASER)


def test_a_old_revision_is_only_in_immutable_history_and_change_log(tmp_path):
    db = tmp_path / "q.sqlite3"
    member_y = _routed(11, Y_TITLE, 0, teaser=Y_TEASER)
    original_x = _routed(12, T1_TITLE, 1, teaser=T1_TEASER)
    corrected_x = _routed(12, T2_TITLE, 5, teaser=T2_TEASER)

    with m.NewsStore(db, source_key="benzinga-rest") as store:
        store.commit([member_y, original_x], expected_cursor=None, next_cursor="c1")
        store.commit([corrected_x], expected_cursor="c1", next_cursor="c2")
        feed = _changes(store, after_sequence=0)
        snap = _snap(store)
        detail = store.story(snap.rows[0].story_id, rights=_rights())
        projected = _projected(store, after_sequence=0)

    # Immutable history keeps rev1 verbatim (this is the one permitted carrier).
    conn = sqlite3.connect(db)
    try:
        history = conn.execute(
            "SELECT revision_json FROM news_revisions WHERE revision_id=?",
            (original_x.revision.revision_id,),
        ).fetchone()
    finally:
        conn.close()
    assert history is not None
    assert T1_TITLE in history[0]
    assert T1_TEASER in history[0]

    # The raw change log carries rev1 only at its own earliest sequence.
    x_rows = sorted(
        (row for row in feed.rows if row.source_item_id == "12"),
        key=lambda row: row.sequence,
    )
    assert len(x_rows) == 2
    first_x, second_x = x_rows
    assert first_x.title == T1_TITLE  # its own immutable journal row
    _assert_absent(second_x, T1_TITLE, T1_TEASER)
    for row in feed.rows:
        if row.sequence > first_x.sequence:
            _assert_absent(row, T1_TITLE, T1_TEASER)

    # No CURRENT read model carries rev1 text.
    _assert_absent(snap, T1_TITLE, T1_TEASER)
    _assert_absent(detail, T1_TITLE, T1_TEASER)
    _assert_absent(projected, T1_TITLE, T1_TEASER)

    # The projection/state tables are current-only.
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        projection = conn.execute(
            "SELECT title, teaser FROM news_state_projection"
            " WHERE source='benzinga' AND source_item_id='12'"
        ).fetchone()
        state = conn.execute(
            "SELECT current_revision_id FROM news_states"
            " WHERE source='benzinga' AND source_item_id='12'"
        ).fetchone()
    finally:
        conn.close()
    assert projection["title"] == T2_TITLE
    assert projection["teaser"] == T2_TEASER
    assert state["current_revision_id"] == corrected_x.revision.revision_id


# --------------------- (b) CORRECTION BETWEEN A SNAPSHOT READ AND A DETAIL READ


def test_b_correction_between_snapshot_and_detail_read_never_resurrects(tmp_path):
    original = _routed(12, T1_TITLE, 1, teaser=T1_TEASER)
    corrected = _routed(12, T2_TITLE, 5, teaser=T2_TEASER)

    with m.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        store.commit([original], expected_cursor=None, next_cursor="c1")
        held = _snap(store)  # snapshot read BEFORE the correction lands
        assert len(held.rows) == 1
        assert held.rows[0].title == T1_TITLE
        story_id = held.rows[0].story_id
        watermark = held.change_sequence

        store.commit([corrected], expected_cursor="c1", next_cursor="c2")

        detail = store.story(story_id, rights=_rights())
        feed = _changes(store, after_sequence=watermark)
        scoped = _changes(store, after_sequence=watermark, security_id=SEC)
        projected = _projected(store, after_sequence=watermark)
        fresh = _snap(store)
        evidence = store.evidence_for_security(SEC, limit=20, rights=_rights())

    assert detail is not None
    assert [member.title for member in detail.members] == [T2_TITLE]
    _assert_absent(detail, T1_TITLE, T1_TEASER)

    # The change feed after the snapshot cursor emits rev2 exactly once.
    for page in (feed, scoped, projected):
        assert len(page.rows) == 1
        assert page.rows[0].kind == "upsert"
        assert page.rows[0].title == T2_TITLE
        assert page.rows[0].source_item_id == "12"
        _assert_absent(page, T1_TITLE, T1_TEASER)

    _assert_absent(fresh, T1_TITLE, T1_TEASER)
    assert fresh.rows[0].title == T2_TITLE
    report = evidence["stories"][0]["reports"][0]
    assert report["revision_id"] == corrected.revision.revision_id
    assert report["title"] == T2_TITLE
    _assert_absent(evidence, T1_TITLE, T1_TEASER)


def test_b_api_detail_after_correction_returns_newer_revision_or_superseded_marker(
    monkeypatch, tmp_path
):
    db = tmp_path / "q.sqlite3"
    original = _routed(12, T1_TITLE, 1, teaser=T1_TEASER)
    corrected = _routed(12, T2_TITLE, 5, teaser=T2_TEASER)
    with m.NewsStore(db, source_key="benzinga-rest") as store:
        store.commit([original], expected_cursor=None, next_cursor="c1")

    ticker_news, app = _api_app(monkeypatch, db)
    client = TestClient(app)

    before = client.get("/api/ticker-news/NVDA")
    assert before.status_code == 200
    body = before.json()
    assert body["rows"][0]["title"] == T1_TITLE
    story_id = body["rows"][0]["story_id"]
    watermark = body["change_sequence"]

    with m.NewsStore(db, source_key="benzinga-rest") as store:
        store.commit([corrected], expected_cursor="c1", next_cursor="c2")

    detail = client.get(f"/api/ticker-news/stories/{story_id}")
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["schema"] == "ticker_news.story.v1"
    assert detail_body["story_id"] == story_id
    assert [member["title"] for member in detail_body["members"]] == [T2_TITLE]
    _assert_absent(detail.text, T1_TITLE, T1_TEASER)

    changes = client.get(f"/api/ticker-news/NVDA/changes?after_sequence={watermark}")
    assert changes.status_code == 200
    changes_body = changes.json()
    assert changes_body["schema"] == "ticker_news.changes.v1"
    assert len(changes_body["rows"]) == 1
    assert changes_body["rows"][0]["kind"] == "upsert"
    assert changes_body["rows"][0]["title"] == T2_TITLE
    _assert_absent(changes.text, T1_TITLE, T1_TEASER)

    after = client.get("/api/ticker-news/NVDA")
    assert after.status_code == 200
    assert after.json()["rows"][0]["title"] == T2_TITLE
    _assert_absent(after.text, T1_TITLE, T1_TEASER)


# ------------------------------------- (c) REMOVAL OR RIGHTS WITHDRAWAL


def test_c_provider_removal_suppresses_every_current_read_model_and_sse_replay(
    monkeypatch, tmp_path
):
    db = tmp_path / "q.sqlite3"
    member_y = _routed(11, Y_TITLE, 0, teaser=Y_TEASER)
    original_x = _routed(12, T1_TITLE, 1, teaser=T1_TEASER)
    protected = (T1_TITLE, T1_TEASER, T1_URL, Y_TITLE, Y_TEASER)

    with m.NewsStore(db, source_key="benzinga-rest") as store:
        store.commit([member_y, original_x], expected_cursor=None, next_cursor="c1")
        story_id = _snap(store).rows[0].story_id
        assert store.story(story_id, rights=_rights()).item_count == 2

        store.commit(
            [_removed(12, minute=6), _removed(11, minute=7)],
            expected_cursor="c1",
            next_cursor="c2",
        )

        snap = _snap(store)
        detail = store.story(story_id, rights=_rights())
        projected = _projected(store, after_sequence=0)
        feed = _changes(store, after_sequence=0)
        evidence = store.evidence_for_security(SEC, limit=20, rights=_rights())
        flow = store.news_flow(SEC, now=T0 + timedelta(hours=2), rights=_rights())

    assert snap.rows == ()
    assert detail is None
    assert len(projected.rows) == 1
    assert projected.rows[0].kind == "remove"
    _assert_absent(projected, *protected)
    _assert_absent(snap, *protected)
    _assert_absent(evidence, *protected)
    _assert_absent(flow, *protected)

    # The raw journal keeps each upsert verbatim at its own sequence only:
    # rev1 text appears on exactly one journal row (its own upsert), and no
    # row after that sequence carries it.
    carriers = [
        row.sequence
        for row in feed.rows
        if T1_TITLE in _serialize(row) or T1_TEASER in _serialize(row)
    ]
    x_sequences = [
        row.sequence for row in feed.rows if row.source_item_id == "12"
    ]
    assert carriers == [min(x_sequences)]

    # The final provider removal is journaled as a removal row, never
    # relabeled as an upsert: the raw change log's kind is audit truth.
    assert max(feed.rows, key=lambda row: row.sequence).kind == "remove"

    # SSE replay from sequence 0 delivers a removal, never rev1 text.
    ticker_news, app = _api_app(monkeypatch, db)
    replay = _sse_frames(ticker_news, after_sequence=0, max_cycles=1)
    assert "event: remove" in replay
    _assert_absent(replay, *protected)


def test_c_rights_withdrawal_leaves_no_protected_text_in_reads_cache_or_sse_replay(
    monkeypatch, tmp_path
):
    db = tmp_path / "q.sqlite3"
    original = _routed(12, T1_TITLE, 1, teaser=T1_TEASER)
    excluded = _excluded()
    limited = _title_only()

    with m.NewsStore(db, source_key="benzinga-rest") as store:
        store.commit([original], expected_cursor=None, next_cursor="c1")
        full_snap = _snap(store)
        story_id = full_snap.rows[0].story_id
        assert full_snap.rows[0].title == T1_TITLE
        assert full_snap.rows[0].teaser == T1_TEASER  # fixture really carries it

        # (1) Source withdrawal: the source leaves allowed_sources entirely.
        assert _snap(store, rights=excluded).rows == ()
        assert store.story(story_id, rights=excluded) is None
        assert _changes(store, after_sequence=0, rights=excluded).rows == ()
        assert _projected(store, after_sequence=0, rights=excluded).rows == ()
        evidence_excluded = store.evidence_for_security(
            SEC, limit=20, rights=excluded
        )
        assert evidence_excluded["stories"] == []
        _assert_absent(evidence_excluded, T1_TITLE, T1_TEASER, T1_URL)

        # (2) Field withdrawal: title remains visible, teaser/url withdrawn.
        field_views = (
            _snap(store, rights=limited),
            store.story(story_id, rights=limited),
            _changes(store, after_sequence=0, rights=limited),
            _projected(store, after_sequence=0, rights=limited),
            store.evidence_for_security(SEC, limit=20, rights=limited),
        )

    for view in field_views:
        _assert_absent(view, T1_TEASER, T1_URL)

    # (3) Cache path: a redacted read served from the module's short-read cache
    # after a full-rights read must still carry no withdrawn field text.
    from app import ticker_news

    cache = ticker_news._STREAM_CHANGE_READER
    calls = {"full": 0, "limited": 0}

    def _reader(rights, counter):
        def read_page():
            calls[counter] += 1
            with m.NewsStore.open_readonly(
                db, source_key="benzinga-rest"
            ) as store:
                return store.projected_changes_for_security(
                    SEC, after_sequence=0, limit=200, rights=rights
                )

        return read_page

    key_full = (str(db.resolve()), SEC, 0, _rights(), None)
    key_limited = (str(db.resolve()), SEC, 0, limited, None)

    async def scenario():
        full_page = await cache.read(key_full, _reader(_rights(), "full"))
        limited_page = await cache.read(key_limited, _reader(limited, "limited"))
        limited_cached = await cache.read(
            key_limited, _reader(limited, "limited")
        )
        return full_page, limited_page, limited_cached

    full_page, limited_page, limited_cached = asyncio.run(scenario())
    assert full_page.rows[0].teaser == T1_TEASER
    assert calls["limited"] == 1  # the second limited read was cache-served
    _assert_absent(limited_page, T1_TEASER, T1_URL)
    _assert_absent(limited_cached, T1_TEASER, T1_URL)

    # (4) SSE replay under the field-withdrawn rights: title only, no teaser/url.
    ticker_news, _app = _api_app(monkeypatch, db, rights_fn=limited)
    replay = _sse_frames(ticker_news, after_sequence=0, max_cycles=1)
    assert "event: upsert" in replay
    assert T1_TITLE in replay  # title display is still granted
    _assert_absent(replay, T1_TEASER, T1_URL)

    # (5) SSE replay under the source-withdrawn rights: restricted, no text.
    _ticker_news2, _app2 = _api_app(monkeypatch, db, rights_fn=excluded)
    restricted = _sse_frames(_ticker_news2, after_sequence=0, max_cycles=2)
    assert "event: restricted" in restricted
    _assert_absent(restricted, T1_TITLE, T1_TEASER, T1_URL)


# --------------------------- (d) EQUIVALENT ADMINISTRATIVE RIGHTS RENEWAL


def test_d_equivalent_rights_renewal_creates_no_revision_no_change_row_and_identical_reads(
    monkeypatch, tmp_path
):
    now = datetime.now(UTC)
    first_payload = _receipt_payload(
        "rights-orig",
        effective_at=(now - timedelta(hours=2)).isoformat(),
        expires_at=(now + timedelta(hours=1)).isoformat(),
    )
    renewed_payload = _receipt_payload(
        "rights-renewed",
        effective_at=(now - timedelta(hours=1)).isoformat(),
        expires_at=(now + timedelta(hours=2)).isoformat(),
    )
    q_first = parse_rights_receipt(first_payload, now=now)
    q_renewed = parse_rights_receipt(renewed_payload, now=now)
    assert q_first.source == q_renewed.source
    assert q_first.product_id == q_renewed.product_id
    assert q_first.audience == q_renewed.audience
    assert q_first.receipt_id != q_renewed.receipt_id
    assert q_first.expires_at != q_renewed.expires_at
    assert q_first.rights == q_renewed.rights  # equivalent administrative grant

    db = tmp_path / "q.sqlite3"
    original = _routed(12, T1_TITLE, 1, teaser=T1_TEASER)
    replay = _routed(12, T1_TITLE, 1, teaser=T1_TEASER)
    assert replay.revision == original.revision  # identical article redelivery

    def read_store(store, rights):
        story_id = _snap(store, rights=rights).rows[0].story_id
        return {
            "snapshot": asdict(_snap(store, rights=rights)),
            "detail": asdict(store.story(story_id, rights=rights)),
            "feed": asdict(_changes(store, after_sequence=0, rights=rights)),
            "scoped": asdict(
                _changes(store, after_sequence=0, rights=rights, security_id=SEC)
            ),
            "projected": asdict(
                _projected(store, after_sequence=0, rights=rights)
            ),
            "evidence": store.evidence_for_security(SEC, limit=20, rights=rights),
            "counts": store.counts(),
            "journal": [
                dict(row)
                for row in store._conn.execute(
                    "SELECT sequence, kind, source, source_item_id,"
                    " revision_id, cluster_id FROM news_changes ORDER BY sequence"
                ).fetchall()
            ],
            "revision_rows": int(
                store._conn.execute(
                    "SELECT count(*) FROM news_revisions"
                ).fetchone()[0]
            ),
        }

    with m.NewsStore(db, source_key="benzinga-rest") as store:
        store.commit([original], expected_cursor=None, next_cursor="c1")
        before = read_store(store, q_first.rights)
        receipt = store.commit(
            [replay],
            expected_cursor="c1",
            next_cursor="c2",
        )
        after = read_store(store, q_renewed.rights)

    # The identical redelivery counts as duplicate: no revision, no change row,
    # no sequence, no state mutation.
    assert receipt.inserted_revisions == 0
    assert receipt.duplicate_revisions == 1
    assert receipt.applied_states == 0
    assert receipt.withdrawn_states == 0
    assert receipt.first_sequence is None
    assert receipt.last_sequence is None
    assert after == before
    assert after["revision_rows"] == before["revision_rows"] == 1
    assert after["counts"]["changes"] == before["counts"]["changes"] == 1

    # HTTP reads under the renewed receipt: only the receipt identity fields in
    # rights_basis (receipt_id, effective_at, expires_at) may differ.
    receipt_file = tmp_path / "rights.json"
    receipt_file.write_text(json.dumps(first_payload))
    ticker_news, app = _api_app(monkeypatch, db, receipt_path=receipt_file)
    client = TestClient(app)

    first_view = client.get("/api/ticker-news/NVDA")
    assert first_view.status_code == 200
    first_body = first_view.json()
    assert first_body["rights_basis"]["receipt_id"] == "rights-orig"

    receipt_file.write_text(json.dumps(renewed_payload))
    renewed_view = client.get("/api/ticker-news/NVDA")
    assert renewed_view.status_code == 200
    renewed_body = renewed_view.json()
    assert renewed_body["rights_basis"]["receipt_id"] == "rights-renewed"
    ignored = ("schema", "rights_basis")
    assert {
        key: value
        for key, value in renewed_body.items()
        if key not in ignored
    } == {
        key: value
        for key, value in first_body.items()
        if key not in ignored
    }
    assert renewed_body["rows"] == first_body["rows"]
    assert (
        renewed_body["rights_basis"]["effective_at"]
        != first_body["rights_basis"]["effective_at"]
    )
    assert (
        renewed_body["rights_basis"]["expires_at"]
        != first_body["rights_basis"]["expires_at"]
    )

    story_id = first_body["rows"][0]["story_id"]
    detail = client.get(f"/api/ticker-news/stories/{story_id}")
    assert detail.status_code == 200
    _assert_absent(detail.text, "rights-orig", "rights-renewed")

    # SSE replay: the renewal creates no new event and changes no event.
    frames_first = _sse_frames(ticker_news, after_sequence=0, max_cycles=1)
    receipt_file.write_text(json.dumps(renewed_payload))
    frames_renewed = _sse_frames(ticker_news, after_sequence=0, max_cycles=1)
    assert frames_first == frames_renewed
    assert frames_renewed.count("event: upsert") == 1
    _assert_absent(frames_renewed, "rights-orig", "rights-renewed")

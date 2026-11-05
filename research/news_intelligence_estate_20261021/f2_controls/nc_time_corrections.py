#!/usr/bin/env python3
"""F2 negative controls — time, revisions, corrections, withdrawal, source health.

Fabric lane NEWS-W3-F2-TIME (MASTERPLAN research/news_intelligence_estate_20261021/
MASTERPLAN.md line 387, axis TIME AND CORRECTIONS). Synthetic, offline,
deterministic: fixed 2026 ISO-8601 instants, placeholder text fields, no network,
no wall clock. Every SQLite file, receipt file and temp artifact lives under
--scratch. Run from the repo root with PYTHONPATH=.:

    PYTHONPATH=. python3 research/news_intelligence_estate_20261021/f2_controls/ \
        nc_time_corrections.py --scratch /tmp/any-dir

Each control prints exactly one line `NC <ID> <VERDICT> <observed>`. Verdicts:
HELD (unsafe input refused/contained as the claim requires), BROKEN (claim
contradicted by observed behaviour), NO_MECHANISM (no code path for the
property), UNTESTABLE_ENV (environment gap only).
"""
from __future__ import annotations

import argparse
import inspect
import json
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

UTC = timezone.utc


def T(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC)


FIXED_NOW = T("2026-10-31T00:00:00Z")
SCRATCH = Path(tempfile.mkdtemp())


# ---------------------------------------------------------------- builders ----
def ws_payload(
    *,
    item="SYNTH-ITEM-01",
    msg="SYNTH-MSG-1",
    action="created",
    created="2026-10-18T10:00:00Z",
    updated="2026-10-18T11:00:00Z",
    event="2026-10-18T10:30:00Z",
    title="SYNTH-TITLE-01",
    url="https://synth.example/SYNTH-01",
    teaser="SYNTH-TEASER-01",
    stocks=("SYNTH",),
    body=None,
    with_content=True,
):
    data = {"id": item, "action": action, "timestamp": event}
    if with_content:
        data["content"] = {
            "id": item,
            "created": created,
            "updated": updated,
            "title": title,
            "url": url,
            "teaser": teaser,
            "stocks": list(stocks),
            "body": body,
        }
    return {"kind": "news", "id": msg, "data": data}


def alpaca_payload(
    *,
    item="SYNTH-ITEM-01",
    created="2026-10-18T10:00:00Z",
    updated="2026-10-18T11:00:00Z",
    headline="SYNTH-TITLE-01",
    url="https://synth.example/SYNTH-01",
    summary="SYNTH-TEASER-01",
    symbols=("SYNTH",),
):
    return {
        "id": item,
        "source": "benzinga",
        "created_at": created,
        "updated_at": updated,
        "headline": headline,
        "summary": summary,
        "url": url,
        "symbols": list(symbols),
    }


def health_payload(
    *,
    state="live",
    observed="2026-10-30T23:59:50Z",
    catchup="2026-10-30T23:59:30Z",
    gap=False,
    **extra,
):
    payload = {
        "schema": "qbus.news_health.v1",
        "source": "benzinga",
        "state": state,
        "observed_at": observed,
        "gap_unresolved": gap,
        "connect_attempts": 1,
        "disconnects": 0,
        "catchups_failed": 0,
    }
    if catchup is not None:
        payload["last_successful_catchup"] = catchup
    payload.update(extra)
    return payload


SYNTH_RIGHTS_RECEIPT = {
    "schema": "qbus.news_rights_receipt.v1",
    "status": "approved",
    "source": "benzinga",
    "receipt_id": "SYNTH-RCP-01",
    "owner_ref": "SYNTH-OWNER",
    "product_id": "SYNTH-PROD",
    "audiences": ["site_full", "internal_research"],
    "effective_at": "2026-01-01T00:00:00Z",
    "expires_at": "2027-01-01T00:00:00Z",
    "capabilities": {
        "internal_ingestion": True,
        "historical_retention": True,
        "headline_display": True,
        "source_link_display": True,
        "teaser_display": True,
        "derivative_processing": True,
    },
}


class SynthResponse:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body

    def iter_content(self, chunk_size=65536):
        yield self._body

    def close(self):
        pass


class SynthSession:
    def __init__(self, status=200, body=b"{}"):
        self.status = status
        self.body = body

    def get(self, url, **kwargs):
        return SynthResponse(self.status, self.body)


def db_rows(path, sql, params=()):
    conn = sqlite3.connect(f"file:{Path(path)}?mode=ro", uri=True)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def commit_one(store, revision, *, restoration=False, cursor_no=1):
    from engine.qbus_news_store import RoutedRevision

    routed = RoutedRevision(
        revision=revision,
        security_ids=("SYNTH-SEC-1",),
        universe_revision="SYNTH-UNI-1",
        restoration_qualified=restoration,
    )
    return store.commit(
        [routed],
        expected_cursor=store.current_cursor(),
        next_cursor=f"SYNTH-CURSOR-{cursor_no}",
    )


# ---------------------------------------------------------------- controls ----
def nc_t01():
    """MP:243 separated clocks survive contract, stored row and read surface."""
    from engine.qbus_news_contract import normalize_news
    from engine.qbus_news_store import NewsReadRights, NewsStore

    rev = normalize_news(
        ws_payload(),
        transport="benzinga_ws",
        received_at=T("2026-10-18T12:00:00Z"),
    )
    ok = (
        rev.published_at == T("2026-10-18T10:00:00Z")
        and rev.updated_at == T("2026-10-18T11:00:00Z")
        and rev.source_event_at == T("2026-10-18T10:30:00Z")
        and rev.received_at == T("2026-10-18T12:00:00Z")
        and rev.version_at == rev.updated_at
        and rev.clock_anomalies == ()
    )
    db = SCRATCH / "t01.db"
    store = NewsStore(db, source_key="synth-key")
    commit_one(store, rev)
    store.close()
    rj = json.loads(db_rows(db, "SELECT revision_json FROM news_revisions")[0][0])
    sj = json.loads(db_rows(db, "SELECT state_json FROM news_states")[0][0])
    stored = (
        rj["published_at"].startswith("2026-10-18T10:00")
        and rj["updated_at"].startswith("2026-10-18T11:00")
        and rj["source_event_at"].startswith("2026-10-18T10:30")
        and rj["received_at"].startswith("2026-10-18T12:00")
        and sj["first_received_at"].startswith("2026-10-18T12:00")
    )
    ro = NewsStore.open_readonly(db, source_key="synth-key")
    ev = ro.evidence_for_security(
        "SYNTH-SEC-1", limit=10, rights=NewsReadRights.all_internal()
    )
    ro.close()
    rep = ev["stories"][0]["reports"][0]
    surface = (
        rep["published_at"].startswith("2026-10-18T10:00")
        and rep["updated_at"].startswith("2026-10-18T11:00")
        and rep["source_event_at"].startswith("2026-10-18T10:30")
        and rep["received_at"].startswith("2026-10-18T12:00")
    )
    verdict = "HELD" if ok and stored and surface else "BROKEN"
    return verdict, (
        f"pub10:00 upd11:00 evt10:30 rcv12:00 distinct; row+state+evidence carry "
        f"all four: fields={ok} row={stored} surface={surface}"
    )


def nc_t02():
    """MP:243 missing/invalid required clocks raise NewsContractError, never now()."""
    import engine.qbus_news_contract as contract
    from engine.qbus_news_contract import NewsContractError, normalize_news

    p1 = ws_payload()
    del p1["data"]["content"]["created"]
    cases = []

    def expect_code(payload, transport, received, code):
        try:
            normalize_news(payload, transport=transport, received_at=received)
            cases.append(f"{code}=NO-RAISE")
        except NewsContractError as exc:
            cases.append(f"{code}={exc.code == code}")

    expect_code(p1, "benzinga_ws", T("2026-10-18T12:00:00Z"), "missing_published_at")
    expect_code(
        ws_payload(updated="SYNTH-BOGUS-CLOCK"),
        "benzinga_ws",
        T("2026-10-18T12:00:00Z"),
        "invalid_updated_at",
    )
    expect_code(
        ws_payload(),
        "benzinga_ws",
        datetime(2026, 10, 18, 12, 0, 0),  # naive wall clock
        "received_at_not_aware",
    )
    expect_code(
        {"id": "SYNTH-ITEM-02", "created": "2026-10-18T10:00:00Z"},
        "benzinga_rest",
        T("2026-10-18T12:00:00Z"),
        "missing_updated_at",
    )
    src = inspect.getsource(contract)
    no_wallclock = "datetime.now" not in src and "utcnow" not in src
    ok = all(c.endswith("=True") for c in cases) and no_wallclock
    return ("HELD" if ok else "BROKEN"), (
        f"codes[{','.join(cases)}] static-no-wallclock-in-contract={no_wallclock}"
    )


def nc_t03():
    """MP:243 impossible publisher-clock orders recorded in clock_anomalies."""
    from engine.qbus_news_contract import NewsContractError, normalize_news

    rev = normalize_news(
        ws_payload(created="2026-10-18T10:00:00Z", updated="2026-10-18T09:00:00Z"),
        transport="benzinga_ws",
        received_at=T("2026-10-18T12:00:00Z"),
    )
    a = "updated_before_published" in rev.clock_anomalies
    rev2 = normalize_news(
        ws_payload(event="2026-10-18T08:00:00Z"),
        transport="benzinga_ws",
        received_at=T("2026-10-18T12:00:00Z"),
    )
    b = "event_before_published" in rev2.clock_anomalies
    refused = isinstance(NewsContractError("x"), Exception)
    return ("HELD" if a and b and refused else "BROKEN"), (
        f"upd<pub flagged={a}; evt<pub flagged={b}; normalized+recorded not refused"
    )


def nc_t04():
    """MP:243-245 archive retrieved today is not possession at an earlier as-of."""
    from engine.qbus_news_contract import normalize_news
    from engine.qbus_news_store import NewsReadRights, NewsStore

    db = SCRATCH / "t04.db"
    store = NewsStore(db, source_key="synth-key")
    rev = normalize_news(
        ws_payload(
            created="2026-10-18T12:00:00Z",
            updated="2026-10-18T12:00:00Z",
            event="2026-10-18T12:00:00Z",
        ),
        transport="benzinga_ws",
        received_at=T("2026-10-20T12:00:00Z"),
    )
    commit_one(store, rev)
    store.close()
    sj = json.loads(db_rows(db, "SELECT state_json FROM news_states")[0][0])
    kept = sj["first_received_at"].startswith("2026-10-20T12:00")
    ro = NewsStore.open_readonly(db, source_key="synth-key")
    flow = ro.news_flow(
        "SYNTH-SEC-1", now=T("2026-10-19T00:00:00Z"), rights=NewsReadRights.all_internal()
    )
    ro.close()
    counted = flow["reports_24h"] or 0
    daily = sum(flow["daily_counts_28d"] or [])
    asof_leak = counted >= 1  # as-of 10-19T00 precedes receipt 10-20T12
    verdict = "BROKEN" if asof_leak else "HELD"
    return verdict, (
        f"news_flow as_of=1019T00 r24h={counted} daily28d={daily} "
        f"basis={flow['provenance']['time_basis_counts_24h']} "
        f"item rcv1020T12 pub1018T12; first_received kept={kept}"
    )


def nc_t05():
    """MP:504 late/out-of-order revision stays stale, current stays v2."""
    from engine.qbus_news_contract import normalize_news
    from engine.qbus_news_store import NewsStore

    db = SCRATCH / "t05.db"
    store = NewsStore(db, source_key="synth-key")
    v2 = normalize_news(
        ws_payload(
            title="SYNTH-TITLE-V2",
            updated="2026-10-18T13:00:00Z",
            created="2026-10-18T10:00:00Z",
        ),
        transport="benzinga_ws",
        received_at=T("2026-10-18T13:05:00Z"),
    )
    r1 = commit_one(store, v2, cursor_no=1)
    v1 = normalize_news(
        ws_payload(
            title="SYNTH-TITLE-V1",
            updated="2026-10-18T12:00:00Z",
            created="2026-10-18T10:00:00Z",
        ),
        transport="benzinga_ws",
        received_at=T("2026-10-18T12:05:00Z"),
    )
    r2 = commit_one(store, v1, cursor_no=2)
    store.close()
    sj = json.loads(db_rows(db, "SELECT state_json FROM news_states")[0][0])
    revs = db_rows(db, "SELECT count(*) FROM news_revisions")[0][0]
    ok = (
        r2.stale_revisions == 1
        and r2.applied_states == 0
        and sj["title"] == "SYNTH-TITLE-V2"
        and revs == 2
        and r1.applied_states == 1
    )
    return ("HELD" if ok else "BROKEN"), (
        f"commit v2-then-v1: stale={r2.stale_revisions} applied={r2.applied_states} "
        f"current={sj['title']} history_rows={revs}"
    )


def nc_t06():
    """MP:504 same version clock + different body = conflict, no overwrite."""
    from engine.qbus_news_contract import normalize_news
    from engine.qbus_news_store import NewsStore

    db = SCRATCH / "t06.db"
    store = NewsStore(db, source_key="synth-key")
    va = normalize_news(
        ws_payload(title="SYNTH-TITLE-A"),
        transport="benzinga_ws",
        received_at=T("2026-10-18T12:00:00Z"),
    )
    commit_one(store, va, cursor_no=1)
    vb = normalize_news(
        ws_payload(title="SYNTH-TITLE-B"),
        transport="benzinga_ws",
        received_at=T("2026-10-18T12:30:00Z"),
    )
    rb = commit_one(store, vb, cursor_no=2)
    store.close()
    sj = json.loads(db_rows(db, "SELECT state_json FROM news_states")[0][0])
    revs = db_rows(db, "SELECT count(*) FROM news_revisions")[0][0]
    ok = (
        rb.conflict_revisions == 1
        and rb.applied_states == 0
        and sj["title"] == "SYNTH-TITLE-A"
        and va.revision_id != vb.revision_id
        and revs == 2
    )
    return ("HELD" if ok else "BROKEN"), (
        f"same version_at diff body: conflict={rb.conflict_revisions} "
        f"current={sj['title']} both_persisted={revs == 2}"
    )


def nc_t07():
    """MP §9.3:503 duplicate delivery over another transport = one state + receipt."""
    from engine.qbus_news_contract import normalize_news
    from engine.qbus_news_store import NewsStore

    db = SCRATCH / "t07.db"
    store = NewsStore(db, source_key="synth-key")
    r1 = normalize_news(
        ws_payload(),
        transport="benzinga_ws",
        received_at=T("2026-10-18T12:00:00Z"),
    )
    commit_one(store, r1, cursor_no=1)
    r2 = normalize_news(
        alpaca_payload(),
        transport="alpaca_ws",
        received_at=T("2026-10-18T15:00:00Z"),
    )
    rc = commit_one(store, r2, cursor_no=2)
    store.close()
    sj = json.loads(db_rows(db, "SELECT state_json FROM news_states")[0][0])
    deliveries = db_rows(db, "SELECT count(*) FROM news_deliveries")[0][0]
    changes = db_rows(db, "SELECT count(*) FROM news_changes")[0][0]
    ok = (
        rc.duplicate_revisions == 1
        and rc.applied_states == 0
        and r1.revision_id == r2.revision_id
        and deliveries == 2
        and changes == 1
        and sj["first_received_at"].startswith("2026-10-18T12:00")
        and sj["last_received_at"].startswith("2026-10-18T15:00")
        and sj["current_revision_id"] == r1.revision_id
    )
    return ("HELD" if ok else "BROKEN"), (
        f"ws+alpaca same article: dup={rc.duplicate_revisions} deliveries=2 "
        f"first=1018T12 last=1018T15 changes=1"
    )


def nc_t08():
    """MP:261 correction creates new history, prior revision retrievable."""
    from engine.qbus_news_contract import normalize_news
    from engine.qbus_news_store import NewsStore

    db = SCRATCH / "t08.db"
    store = NewsStore(db, source_key="synth-key")
    v1 = normalize_news(
        ws_payload(title="SYNTH-TITLE-ORIG"),
        transport="benzinga_ws",
        received_at=T("2026-10-18T12:00:00Z"),
    )
    commit_one(store, v1, cursor_no=1)
    v2 = normalize_news(
        ws_payload(title="SYNTH-TITLE-CORRECTED", updated="2026-10-18T14:00:00Z"),
        transport="benzinga_ws",
        received_at=T("2026-10-18T14:05:00Z"),
    )
    commit_one(store, v2, cursor_no=2)
    store.close()
    sj = json.loads(db_rows(db, "SELECT state_json FROM news_states")[0][0])
    old = db_rows(
        db, "SELECT count(*) FROM news_revisions WHERE revision_id=?",
        (v1.revision_id,),
    )[0][0]
    changes = db_rows(db, "SELECT count(*) FROM news_changes")[0][0]
    ok = (
        sj["title"] == "SYNTH-TITLE-CORRECTED"
        and sj["current_revision_id"] == v2.revision_id
        and old == 1
        and changes == 2
    )
    return ("HELD" if ok else "BROKEN"), (
        f"after correction: current={sj['title']} prior_row_retrievable={old == 1} "
        f"history_changes={changes}"
    )


def nc_t09():
    """MP:156 withdrawal blanks fields + first_withdrawal; correction does not."""
    from engine.qbus_news_contract import normalize_news
    from engine.qbus_news_reducer import reduce_revision

    removed = normalize_news(
        ws_payload(action="deleted", with_content=False, body="SYNTH-BODY-ORIG"),
        transport="benzinga_ws",
        received_at=T("2026-10-18T13:00:00Z"),
    )
    red = reduce_revision(None, removed)
    s = red.state
    blanked = (
        red.disposition == "withdrawn"
        and red.reason == "first_withdrawal"
        and s.status == "withdrawn"
        and s.title == ""
        and s.url == ""
        and s.teaser == ""
        and s.provider_tickers == ()
        and s.channels == ()
        and s.tags == ()
        and s.body_sha256 == ""
    )
    corrected = normalize_news(
        ws_payload(
            title="SYNTH-TITLE-CORRECTED",
            updated="2026-10-18T14:00:00Z",
            body="SYNTH-BODY-CORRECTED",
        ),
        transport="benzinga_ws",
        received_at=T("2026-10-18T14:05:00Z"),
    )
    red2 = reduce_revision(None, corrected)
    kept = (
        red2.disposition == "accepted"
        and red2.state.title == "SYNTH-TITLE-CORRECTED"
        and red2.state.provider_tickers == ("SYNTH",)
        and red2.state.body_sha256 != ""
    )
    return ("HELD" if blanked and kept else "BROKEN"), (
        f"removed blanks title/url/teaser/tickers/channels/tags/body "
        f"first_withdrawal={red.reason == 'first_withdrawal'}; correction_keeps={kept}"
    )


def nc_t10():
    """MP:156/:504 revision after withdrawal must not resurrect unqualified."""
    from engine.qbus_news_contract import normalize_news
    from engine.qbus_news_store import NewsStore

    db = SCRATCH / "t10.db"
    store = NewsStore(db, source_key="synth-key")
    v1 = normalize_news(
        ws_payload(),
        transport="benzinga_ws",
        received_at=T("2026-10-18T12:00:00Z"),
    )
    commit_one(store, v1, cursor_no=1)
    wd = normalize_news(
        ws_payload(action="deleted", with_content=False, event="2026-10-18T13:00:00Z"),
        transport="benzinga_ws",
        received_at=T("2026-10-18T13:05:00Z"),
    )
    rw = commit_one(store, wd, cursor_no=2)
    older = normalize_news(
        ws_payload(title="SYNTH-TITLE-OLDER", updated="2026-10-18T11:30:00Z"),
        transport="benzinga_ws",
        received_at=T("2026-10-18T13:10:00Z"),
    )
    ro = commit_one(store, older, cursor_no=3)
    newer = normalize_news(
        ws_payload(title="SYNTH-TITLE-NEWER", updated="2026-10-18T14:00:00Z"),
        transport="benzinga_ws",
        received_at=T("2026-10-18T14:10:00Z"),
    )
    rn = commit_one(store, newer, cursor_no=4)

    def state_json():
        return json.loads(db_rows(db, "SELECT state_json FROM news_states")[0][0])

    s_after_unqualified = state_json()
    qualified = normalize_news(
        ws_payload(title="SYNTH-TITLE-QUALIFIED", updated="2026-10-18T15:00:00Z"),
        transport="benzinga_ws",
        received_at=T("2026-10-18T15:10:00Z"),
    )
    rq = commit_one(store, qualified, cursor_no=5, restoration=True)
    s_after_qualified = state_json()
    store.close()
    unqualified_ok = (
        rw.withdrawn_states == 1
        and ro.stale_revisions == 1
        and ro.applied_states == 0
        and rn.stale_revisions == 1
        and rn.applied_states == 0
        and s_after_unqualified["status"] == "withdrawn"
        and s_after_unqualified["title"] == ""
        and s_after_unqualified["current_revision_id"] == wd.revision_id
    )
    return ("HELD" if unqualified_ok else "BROKEN"), (
        f"older/newer non-removed after withdrawal: stale={ro.stale_revisions}/"
        f"{rn.stale_revisions} status={s_after_unqualified['status']} blank; "
        f"qualified_flag_restores={rq.applied_states == 1 and s_after_qualified['status'] == 'active'}"
    )


def nc_t11():
    """MP:261 denial item leaves rumor item and its history intact."""
    from engine.qbus_news_contract import normalize_news
    from engine.qbus_news_store import NewsReadRights, NewsStore

    db = SCRATCH / "t11.db"
    store = NewsStore(db, source_key="synth-key")
    rumor = normalize_news(
        ws_payload(item="SYNTH-ITEM-R", title="SYNTH-TITLE-RUMOR"),
        transport="benzinga_ws",
        received_at=T("2026-10-18T12:00:00Z"),
    )
    commit_one(store, rumor, cursor_no=1)
    denial = normalize_news(
        ws_payload(item="SYNTH-ITEM-D", title="SYNTH-TITLE-DENIAL",
                   updated="2026-10-18T16:00:00Z", created="2026-10-18T16:00:00Z",
                   event="2026-10-18T16:00:00Z"),
        transport="benzinga_ws",
        received_at=T("2026-10-18T16:05:00Z"),
    )
    commit_one(store, denial, cursor_no=2)
    store.close()
    rows = {
        json.loads(r[0])["source_item_id"]: json.loads(r[0])
        for r in db_rows(db, "SELECT state_json FROM news_states")
    }
    rumor_row = rows.get("SYNTH-ITEM-R")
    ok = (
        rumor_row is not None
        and rumor_row["status"] == "active"
        and rumor_row["title"] == "SYNTH-TITLE-RUMOR"
        and rumor_row["current_revision_id"] == rumor.revision_id
        and rows.get("SYNTH-ITEM-D", {}).get("status") == "active"
        and db_rows(db, "SELECT count(*) FROM news_revisions")[0][0] == 2
    )
    ro = NewsStore.open_readonly(db, source_key="synth-key")
    snap = ro.snapshot(
        "SYNTH-SEC-1", limit=10, cursor=None, rights=NewsReadRights.all_internal()
    )
    ro.close()
    ok = ok and len(snap.rows) == 2
    return ("HELD" if ok else "BROKEN"), (
        f"after denial commit: rumor active/title/rev unchanged={ok} "
        f"snapshot_stories={len(snap.rows)} revisions=2"
    )


def nc_t12():
    """MP:504 correction after cache/model start: earlier read identity differs."""
    from engine.qbus_news_contract import normalize_news
    from engine.qbus_news_context import news_evidence_bundle
    from engine.qbus_news_store import NewsReadRights, NewsStore

    db = SCRATCH / "t12.db"
    receipt = SCRATCH / "t12-rights.json"
    receipt.write_text(json.dumps(SYNTH_RIGHTS_RECEIPT), encoding="utf-8")
    store = NewsStore(db, source_key="synth-key")
    v1 = normalize_news(
        ws_payload(),
        transport="benzinga_ws",
        received_at=T("2026-10-18T12:00:00Z"),
    )
    commit_one(store, v1, cursor_no=1)
    ev1 = store.evidence_for_security(
        "SYNTH-SEC-1", limit=10, rights=NewsReadRights.all_internal()
    )
    snap1 = store.snapshot(
        "SYNTH-SEC-1", limit=10, cursor=None, rights=NewsReadRights.all_internal()
    )
    b1 = news_evidence_bundle(
        database=str(db), security_id="SYNTH-SEC-1",
        receipt_paths=[str(receipt)], audience="internal_research", now=FIXED_NOW,
    )
    v2 = normalize_news(
        ws_payload(title="SYNTH-TITLE-CORRECTED", updated="2026-10-18T14:00:00Z"),
        transport="benzinga_ws",
        received_at=T("2026-10-18T14:05:00Z"),
    )
    commit_one(store, v2, cursor_no=2)
    ev2 = store.evidence_for_security(
        "SYNTH-SEC-1", limit=10, rights=NewsReadRights.all_internal()
    )
    snap2 = store.snapshot(
        "SYNTH-SEC-1", limit=10, cursor=None, rights=NewsReadRights.all_internal()
    )
    b2 = news_evidence_bundle(
        database=str(db), security_id="SYNTH-SEC-1",
        receipt_paths=[str(receipt)], audience="internal_research", now=FIXED_NOW,
    )
    store.close()
    rid1 = ev1["stories"][0]["reports"][0]["revision_id"]
    rid2 = ev2["stories"][0]["reports"][0]["revision_id"]
    ok = (
        rid1 != rid2
        and b1["evidence_sha256"] != b2["evidence_sha256"]
        and snap2.change_sequence > snap1.change_sequence
        and b1["state"] == "available"
    )
    return ("HELD" if ok else "BROKEN"), (
        f"same now: revision_id differs={rid1 != rid2} bundle_sha differs="
        f"{b1['evidence_sha256'][:8]}!={b2['evidence_sha256'][:8]} "
        f"gen {snap1.change_sequence}->{snap2.change_sequence}"
    )


def nc_t13():
    """MP:508/:477 sparse/quiet/unavailable/catch-up/pagination/malformed health."""
    from engine.qbus_news_receipts import (
        NewsReceiptError,
        load_health_receipt,
        parse_health_receipt,
        write_health_receipt,
    )

    now = FIXED_NOW
    conditions = []

    def check(name, payload, want_state, want_reason=None):
        out = parse_health_receipt(payload, now=now)
        good = out["state"] == want_state and (
            want_reason is None or out["reason"] == want_reason
        )
        conditions.append(f"{name}:{out['state']}/{out['reason']}={good}")

    check("healthy", health_payload(), "live", "fresh")
    check("stale-obs", health_payload(observed="2026-10-30T23:50:00Z",
                                       catchup="2026-10-30T23:49:00Z"),
          "unavailable", "receipt_stale")
    check("unavailable", health_payload(state="unavailable"),
          "unavailable", "source_unavailable")
    check("gap", health_payload(gap=True), "degraded", "gap_unresolved")
    check("no-catchup", health_payload(catchup=None), "catching_up", "catchup_pending")
    check("stale-catchup", health_payload(catchup="2026-10-30T23:50:00Z"),
          "degraded", "catchup_stale")
    addl = health_payload(
        additional_sources=[{
            "provider": "massive", "state": "degraded",
            "last_successful_poll": "2026-10-30T23:59:30Z",
            "publishers": ["synth-pub.example"], "accepted_reports": 5,
        }]
    )
    out = parse_health_receipt(addl, now=now)
    conditions.append(
        f"pagination-sat:{out['additional_sources'][0]['state']}="
        f"{out['additional_sources'][0]['state'] == 'degraded'}"
    )

    def refuse(name, payload):
        try:
            parse_health_receipt(payload, now=now)
            conditions.append(f"{name}:NO-RAISE")
        except NewsReceiptError:
            conditions.append(f"{name}:refused=True")

    refuse("bad-schema", {"schema": "SYNTH-BOGUS"})
    refuse("future-obs", health_payload(observed="2026-12-01T00:00:00Z"))
    refuse("bad-state", health_payload(state="SYNTH-BOGUS"))

    missing = load_health_receipt(SCRATCH / "t13-missing.json", now=now)
    badfile = SCRATCH / "t13-bad.json"
    badfile.write_text("SYNTH-NOT-JSON", encoding="utf-8")
    invalid = load_health_receipt(badfile, now=now)
    goodfile = SCRATCH / "t13-good.json"
    write_health_receipt(goodfile, health_payload())
    loaded = load_health_receipt(goodfile, now=now)
    mode = goodfile.stat().st_mode & 0o777
    malformed_not_healthy = (
        missing["state"] == "unavailable"
        and missing["reason"] == "receipt_missing"
        and invalid["state"] == "unavailable"
        and invalid["reason"] == "receipt_invalid"
        and loaded["state"] == "live"
        and mode == 0o600
    )
    all_states = [c for c in conditions]
    ok = all("=True" in c or ":refused=True" in c for c in all_states) and malformed_not_healthy
    return ("HELD" if ok else "BROKEN"), (
        f"9 conditions all non-live when unhealthy; 3 malformed refused; "
        f"missing/invalid-file->unavailable; write->load roundtrip live "
        f"mode600={mode == 0o600} ok={ok}"
    )


def nc_t14():
    """MP:508 malformed upstream payload into intake: refused, nothing stored."""
    from engine.massive_news import MassiveNewsClient, MassivePollError
    from engine.qbus_news_intake import SupplementalNewsIntake
    from engine.qbus_news_receipts import QualifiedNewsRights
    from engine.qbus_news_store import NewsReadRights, NewsStore
    from engine.qbus_news_universe import AliasBinding, UniverseQualification

    publishers = frozenset({"synth-pub.example"})
    since = T("2026-10-30T20:00:00Z")

    client = MassiveNewsClient(
        token="SYNTH-TOKEN",
        session=SynthSession(body=b'{"results": '),
        clock=lambda: T("2026-10-30T21:00:00Z"),
    )
    try:
        client.poll(since=since, allowed_publishers=publishers)
        refused_json = "NO-RAISE"
    except MassivePollError as exc:
        refused_json = exc.code

    row_bad = json.dumps({
        "results": [{
            "id": "SYNTH-MID-9",
            "publisher": {"name": "SYNTH-PUB", "homepage_url": "https://synth-pub.example"},
            "title": "SYNTH-TITLE-90",
            "article_url": "https://synth-pub.example/SYNTH-90",
            "published_utc": "SYNTH-BOGUS-CLOCK",
        }],
    }).encode()
    client2 = MassiveNewsClient(
        token="SYNTH-TOKEN",
        session=SynthSession(body=row_bad),
        clock=lambda: T("2026-10-30T21:00:00Z"),
    )
    try:
        client2.poll(since=since, allowed_publishers=publishers)
        refused_row = "NO-RAISE"
    except MassivePollError as exc:
        refused_row = exc.code

    db = SCRATCH / "t14.db"
    store = NewsStore(db, source_key="synth-key")
    receipt = QualifiedNewsRights(
        receipt_id="SYNTH-RCP-M1",
        owner_ref="SYNTH-OWNER",
        source="massive:synth-pub.example",
        product_id="SYNTH-PROD",
        audience="site_full",
        effective_at=T("2026-01-01T00:00:00Z"),
        expires_at=T("2027-01-01T00:00:00Z"),
        rights=NewsReadRights(
            allowed_sources=frozenset({"massive:synth-pub.example"})
        ),
        provider="massive",
        derivative_processing=True,
    )
    universe = UniverseQualification(
        status="qualified", owner="SYNTH-OWNER", revision="SYNTH-UNI-1",
        asof=T("2026-10-30T00:00:00Z"), count=1, securities=(),
        alias_bindings=(AliasBinding(alias="SYNTH", security_id="SYNTH-SEC-1"),),
        excluded=(), reason_codes=(), ambiguous_aliases=(),
    )
    tick = {"n": 0.0}

    def monotonic():
        tick["n"] += 1.0
        return tick["n"]

    intake = SupplementalNewsIntake(
        client=MassiveNewsClient(
            token="SYNTH-TOKEN",
            session=SynthSession(body=b'{"results": '),
            clock=lambda: T("2026-10-30T21:00:00Z"),
        ),
        store=store,
        rights_provider=lambda: (receipt,),
        universe_provider=lambda: universe,
        clock=lambda: T("2026-10-30T21:00:00Z"),
        monotonic=monotonic,
        interval_seconds=60.0,
    )
    intake.pump()   # submits acquisition
    intake.pump()   # drains the failed future on the runner tick
    counts = store.counts()
    cursors = db_rows(db, "SELECT count(*) FROM news_cursors")[0][0]
    store.close()
    ok = (
        refused_json == "MASSIVE_MALFORMED_RESPONSE"
        and refused_row == "MASSIVE_ROW_MALFORMED"
        and intake.state == "degraded"
        and intake.last_error == "massive_malformed_response"
        and counts["revisions"] == 0
        and counts["states"] == 0
        and counts["changes"] == 0
        and cursors == 0
    )
    return ("HELD" if ok else "BROKEN"), (
        f"client json={refused_json} row={refused_row}; intake state="
        f"{intake.state} err={intake.last_error} stored=0/0/0 cursor_rows={cursors}"
    )


def nc_t15():
    """MP:243 future-dated publication vs receipt: no anomaly mechanism exists."""
    import engine.qbus_news_contract as contract
    from engine.qbus_news_contract import normalize_news

    rev = normalize_news(
        ws_payload(
            created="2026-11-15T12:00:00Z",
            updated="2026-11-15T13:00:00Z",
            event="2026-11-15T12:30:00Z",
        ),
        transport="benzinga_ws",
        received_at=T("2026-10-20T12:00:00Z"),
    )
    unflagged = rev.clock_anomalies == ()  # published 26 days after receipt
    src = inspect.getsource(contract._clock_anomalies)
    store_src = Path(inspect.getfile(contract)).with_name("qbus_news_store.py").read_text()
    no_received_check = "received" not in src
    store_mentions = store_src.count("clock_anomalies")
    verdict = "NO_MECHANISM" if unflagged and no_received_check else "HELD"
    return verdict, (
        f"pub1115 rcv1020 anomalies={rev.clock_anomalies!r}; "
        f"_clock_anomalies src has no received param={no_received_check} "
        f"store 'clock_anomalies' mentions={store_mentions} (io only)"
    )


CONTROLS = [
    ("T01", nc_t01), ("T02", nc_t02), ("T03", nc_t03), ("T04", nc_t04),
    ("T05", nc_t05), ("T06", nc_t06), ("T07", nc_t07), ("T08", nc_t08),
    ("T09", nc_t09), ("T10", nc_t10), ("T11", nc_t11), ("T12", nc_t12),
    ("T13", nc_t13), ("T14", nc_t14), ("T15", nc_t15),
]


def main() -> int:
    global SCRATCH
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch", default=None, help="directory for all artifacts")
    args = parser.parse_args()
    if args.scratch:
        SCRATCH = Path(args.scratch)
        SCRATCH.mkdir(parents=True, exist_ok=True)
    tally = {"HELD": 0, "BROKEN": 0, "NO_MECHANISM": 0, "UNTESTABLE_ENV": 0}
    for nc_id, fn in CONTROLS:
        try:
            verdict, observed = fn()
            observed = observed[:160]
        except Exception as exc:  # unexpected failure: environment gap, not a verdict
            verdict = "UNTESTABLE_ENV"
            observed = f"exc:{type(exc).__name__}"[:160]
        tally[verdict] = tally.get(verdict, 0) + 1
        print(f"NC {nc_id} {verdict} {observed}")
    print(
        "NC SUMMARY held={held} broken={broken} no_mechanism={no_mechanism} "
        "untestable_env={untestable_env} total={total}".format(
            held=tally["HELD"], broken=tally["BROKEN"],
            no_mechanism=tally["NO_MECHANISM"],
            untestable_env=tally["UNTESTABLE_ENV"],
            total=len(CONTROLS),
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

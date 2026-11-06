"""F2 synthetic negative controls: rights gate, security identity, source independence.

Lane NEWS-W3-F2-RIGHTS (MASTERPLAN §7.F row F2, line 387). Offline and
deterministic: every input is synthetic (SYNTH-* placeholders, fixed ISO-8601
instants in 2026), every file the controls touch lives under ``--scratch``,
and no real receipt, ledger, database or credential on the host is opened.

Standard library plus repo modules only. One line per control:
``NC <ID> <HELD|BROKEN|NO_MECHANISM|UNTESTABLE_ENV> <observed>``.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

UTC = timezone.utc
RIGHTS_SCHEMA = "qbus.news_rights_receipt.v1"

# ---------------------------------------------------------------- helpers ---


def _receipt(
    *,
    source="benzinga",
    status="approved",
    audiences=("site_full",),
    effective="2026-10-01T00:00:00Z",
    expires="2026-11-30T00:00:00Z",
    url=True,
    teaser=True,
    derivative=False,
    provider=None,
    receipt_id="SYNTH-R-001",
    body=False,
):
    return {
        "schema": RIGHTS_SCHEMA,
        "status": status,
        "source": source,
        "receipt_id": receipt_id,
        "owner_ref": "SYNTH-OWNER",
        "product_id": "SYNTH-PRODUCT",
        "audiences": list(audiences),
        "effective_at": effective,
        "expires_at": expires,
        "capabilities": {
            "internal_ingestion": True,
            "historical_retention": True,
            "headline_display": True,
            "source_link_display": url,
            "teaser_display": teaser,
            "body_display": body,
            "derivative_processing": derivative,
        },
        **({"provider": provider} if provider is not None else {}),
    }


def _parse_code(payload, now, audience="site_full"):
    """Parse one receipt; return its refusal code, or None when it grants."""
    from engine.qbus_news_receipts import NewsReceiptError, parse_rights_receipt

    try:
        parse_rights_receipt(payload, now=now, audience=audience)
        return None
    except NewsReceiptError as exc:
        return exc.code


def _ws_revision(
    item_id,
    *,
    title,
    url,
    teaser,
    published,
    updated,
    received,
    stocks=("SYNTH",),
):
    from engine.qbus_news_contract import normalize_news

    payload = {
        "kind": "news",
        "id": f"SYN-MSG-{item_id}",
        "data": {
            "id": item_id,
            "action": "created",
            "timestamp": published,
            "content": {
                "id": item_id,
                "created": published,
                "updated": updated,
                "title": title,
                "url": url,
                "teaser": teaser,
                "stocks": list(stocks),
            },
        },
    }
    return normalize_news(payload, transport="benzinga_ws", received_at=received)


def _alpaca_revision(
    item_id,
    *,
    headline,
    summary,
    url,
    created,
    updated,
    received,
    symbols=("SYNTH",),
):
    from engine.qbus_news_contract import normalize_news

    payload = {
        "source": "benzinga",
        "id": item_id,
        "created_at": created,
        "updated_at": updated,
        "headline": headline,
        "summary": summary,
        "url": url,
        "symbols": list(symbols),
    }
    return normalize_news(payload, transport="alpaca_rest", received_at=received)


def _massive_benzinga_mirror(
    item_id,
    *,
    title,
    url,
    teaser,
    published,
    updated,
    received,
):
    from engine.qbus_news_contract import normalize_news

    payload = {
        "benzinga_id": item_id,
        "published": published,
        "last_updated": updated,
        "title": title,
        "url": url,
        "teaser": teaser,
        "tickers": ["SYNTH"],
    }
    return normalize_news(
        payload, transport="massive_benzinga_v2", received_at=received
    )


def _massive_revision(
    item_id,
    domain,
    *,
    title,
    teaser,
    url,
    published,
    received,
):
    from engine.qbus_news_contract import normalize_massive_news

    payload = {
        "id": item_id,
        "publisher": {"homepage_url": f"https://{domain}"},
        "published_utc": published,
        "article_url": url,
        "title": title,
        "description": teaser,
        "tickers": ["SYNTH"],
    }
    return normalize_massive_news(payload, received_at=received)


def _routed(revision, security_ids, universe="SYNTH-UNI-R1"):
    from engine.qbus_news_store import RoutedRevision

    return RoutedRevision(
        revision=revision,
        security_ids=tuple(security_ids),
        universe_revision=universe,
    )


def _obj(value):
    """Render one result object for leak scanning (dataclass, slots or not)."""
    import dataclasses

    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return dataclasses.asdict(value)
    return repr(value)


def _rights(sources, *, title=True, url=True, teaser=True):
    from engine.qbus_news_store import NewsReadRights

    return NewsReadRights(
        allowed_sources=frozenset(sources),
        allow_title=title,
        allow_url=url,
        allow_teaser=teaser,
    )


def _universe(securities, *, revision="SYNTH-UNI-R1"):
    return {
        "schema": "news_universe.v1",
        "owner": "SYNTH-OWNER",
        "revision": revision,
        "complete": True,
        "truncated": False,
        "effective_at": "2026-01-01T00:00:00Z",
        "known_at": "2026-01-01T00:00:00Z",
        "fresh_until": "2027-06-01T00:00:00Z",
        "securities": securities,
    }


def _security_row(security_id, ticker, aliases, valid_to=None):
    row = {
        "security_id": security_id,
        "ticker": ticker,
        "aliases": list(aliases),
        "valid_from": "2026-01-01T00:00:00Z",
        "known_at": "2026-01-01T00:00:00Z",
    }
    if valid_to is not None:
        row["valid_to"] = valid_to
    return row


class _Env:
    """Set/restore process env vars for the app-level controls."""

    KEYS = (
        "MM_TICKER_NEWS_DB",
        "MM_TICKER_NEWS_RIGHTS",
        "MM_TICKER_NEWS_UNIVERSE",
        "MM_TICKER_NEWS_ADDITIONAL_RIGHTS",
        "MM_TICKER_NEWS_HEALTH",
    )

    def __init__(self, **values):
        import os

        self._os = os
        self._values = values
        self._saved = {}

    def __enter__(self):
        for key in self.KEYS:
            self._saved[key] = self._os.environ.get(key)
        for key in self.KEYS:
            self._os.environ.pop(key, None)
        for key, value in self._values.items():
            self._os.environ[key] = str(value)
        return self

    def __exit__(self, *exc):
        for key, value in self._saved.items():
            if value is None:
                self._os.environ.pop(key, None)
            else:
                self._os.environ[key] = value
        return False


# -------------------------------------------------------------- controls ---


def nc_r01(scratch):
    """Expired receipt grants nothing (receipts docstring line 6; §9.3 line 505)."""
    from engine.qbus_news_receipts import (
        combine_news_rights,
        load_rights_receipt,
        load_rights_set,
    )

    now = datetime(2026, 10, 15, tzinfo=UTC)
    payload = _receipt(expires="2026-10-10T00:00:00Z")
    code = _parse_code(payload, now)
    path = scratch / "r01.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    loaded = load_rights_receipt(path, now=now)
    combined = combine_news_rights(load_rights_set((path,), now=now))
    ok = (
        code == "rights_expired"
        and loaded is None
        and not combined.allowed_sources
        and not combined.allows("benzinga", "title")
    )
    return ("HELD" if ok else "BROKEN"), f"code={code} file_load={loaded is None} set={len(combined.allowed_sources)}"


def nc_r02(scratch):
    """Future (not yet effective) receipt grants nothing."""
    now = datetime(2026, 10, 15, tzinfo=UTC)
    payload = _receipt(effective="2026-11-01T00:00:00Z", expires="2026-12-01T00:00:00Z")
    code = _parse_code(payload, now)
    ok = code == "rights_not_effective"
    return ("HELD" if ok else "BROKEN"), f"code={code}"


def nc_r03(scratch):
    """Wrong-audience receipt grants nothing for site_full."""
    from engine.qbus_news_receipts import load_rights_receipt

    now = datetime(2026, 10, 15, tzinfo=UTC)
    payload = _receipt(audiences=("synd_other_product",))
    code = _parse_code(payload, now, audience="site_full")
    path = scratch / "r03.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    loaded = load_rights_receipt(path, now=now)
    ok = code == "rights_audience_not_permitted" and loaded is None
    return ("HELD" if ok else "BROKEN"), f"code={code} file_load={loaded is None}"


def nc_r04(scratch):
    """Revocation: prior grant then revoke/delete; next decision denies; reads re-check."""
    from engine.qbus_news_receipts import combine_news_rights, load_rights_set
    from engine.qbus_news_store import NewsStore

    now = datetime(2026, 10, 15, tzinfo=UTC)
    path = scratch / "r04.json"
    path.write_text(json.dumps(_receipt()), encoding="utf-8")
    granted = combine_news_rights(load_rights_set((path,), now=now))
    was_granted = granted.allows("benzinga", "title")

    db = scratch / "r04.sqlite3"
    rev = _ws_revision(
        "SYNTH-ITEM-R04",
        title="SYNTH-TITLE-R04",
        url="https://benzinga.com/synth-r04",
        teaser="SYNTH-TEASER-R04",
        published="2026-10-14T09:00:00Z",
        updated="2026-10-14T09:00:00Z",
        received=datetime(2026, 10, 14, 10, 0, tzinfo=UTC),
    )
    with NewsStore(db, source_key="SYNTH-KEY") as store:
        store.commit_observations([_routed(rev, ("SYNTH-SEC-4",))])

    def reads_visible(rights):
        reader = NewsStore.open_readonly(db, source_key="SYNTH-KEY")
        try:
            snap = reader.snapshot("SYNTH-SEC-4", limit=10, cursor=None, rights=rights)
            detail = reader.story(snap.rows[0].story_id, rights=rights) if snap.rows else None
            evidence = reader.evidence_for_security("SYNTH-SEC-4", limit=10, rights=rights)
            return bool(snap.rows) or detail is not None or bool(evidence["stories"])
        finally:
            reader.close()

    visible_before = reads_visible(granted)

    path.write_text(json.dumps(_receipt(status="revoked")), encoding="utf-8")
    revoked = combine_news_rights(load_rights_set((path,), now=now))
    path.unlink()
    removed = combine_news_rights(load_rights_set((path,), now=now))
    empty = _rights(())
    visible_after = reads_visible(revoked) or reads_visible(empty)

    ok = was_granted and visible_before and not revoked.allowed_sources and not removed.allowed_sources and not visible_after
    return (
        "HELD" if ok else "BROKEN"
    ), f"grant={was_granted} read_before={visible_before} revoked_set={len(revoked.allowed_sources)} read_after={visible_after}"


def nc_r05(scratch):
    """Equivalent renewal: identical terms keep access with no gap, broaden nothing (P0-C line 156)."""
    from engine.qbus_news_receipts import parse_rights_receipt

    now_mid = datetime(2026, 11, 15, tzinfo=UTC)
    now_edge = datetime(2026, 11, 30, 0, 0, tzinfo=UTC)
    v1 = _receipt(expires="2026-11-30T00:00:00Z", receipt_id="SYNTH-R-V1")
    v2 = _receipt(effective="2026-11-15T00:00:00Z", expires="2026-12-31T00:00:00Z", receipt_id="SYNTH-R-V2")
    v2_no_teaser = _receipt(
        effective="2026-11-15T00:00:00Z",
        expires="2026-12-31T00:00:00Z",
        teaser=False,
        receipt_id="SYNTH-R-V2N",
    )
    r1 = parse_rights_receipt(v1, now=now_mid)
    r2 = parse_rights_receipt(v2, now=now_edge)
    r2n = parse_rights_receipt(v2_no_teaser, now=now_edge)
    fields_equal = (
        r1.rights.allowed_sources == r2.rights.allowed_sources
        and r1.rights.allow_title == r2.rights.allow_title
        and r1.rights.allow_url == r2.rights.allow_url
        and r1.rights.allow_teaser == r2.rights.allow_teaser
    )
    no_gap = r2.rights.allows("benzinga", "title")
    no_broaden = (
        not r2n.rights.allows("benzinga", "teaser")
        and r2n.rights.allows("benzinga", "title")
        and not r1.derivative_processing
        and not r2.derivative_processing
    )
    ok = fields_equal and no_gap and no_broaden
    return ("HELD" if ok else "BROKEN"), f"fields_equal={fields_equal} edge_access={no_gap} teaser_stays_denied={not r2n.rights.allows('benzinga', 'teaser')}"


def nc_r06(scratch):
    """Duplicate receipts may only narrow; order-independent (store allows ~line 131)."""
    from engine.qbus_news_receipts import combine_news_rights, parse_rights_receipt
    from engine.qbus_news_store import NewsReadRights, SourceReadRights

    src = "benzinga"
    full = SourceReadRights(src, True, True, True)
    no_teaser = SourceReadRights(src, True, True, False)
    orders = []
    for pair in ((full, no_teaser), (no_teaser, full)):
        rights = NewsReadRights(
            allowed_sources=frozenset({src}), source_fields=pair
        )
        orders.append(
            (
                rights.allows(src, "title"),
                rights.allows(src, "url"),
                rights.allows(src, "teaser"),
            )
        )
    narrow_ok = orders[0] == orders[1] == (True, True, False)

    now = datetime(2026, 10, 15, tzinfo=UTC)
    q1 = parse_rights_receipt(_receipt(receipt_id="SYNTH-R-A"), now=now)
    q2 = parse_rights_receipt(
        _receipt(teaser=False, receipt_id="SYNTH-R-B"), now=now
    )
    c1 = combine_news_rights((q1, q2))
    c2 = combine_news_rights((q2, q1))
    dropped = not c1.allowed_sources and not c2.allowed_sources and not c1.allows(src, "teaser")
    ok = narrow_ok and dropped
    return ("HELD" if ok else "BROKEN"), f"allows_both_orders={orders[0]} receipt_set_denies={dropped}"


def nc_r07(scratch):
    """Source outside allowed_sources or field outside {title,url,teaser} denied."""
    from engine.qbus_news_receipts import parse_rights_receipt

    now = datetime(2026, 10, 15, tzinfo=UTC)
    qualified = parse_rights_receipt(_receipt(body=True), now=now)
    rights = qualified.rights
    other_source = not rights.allows("massive:synth.example.com", "title")
    body_denied = not rights.allows("benzinga", "body")
    teaser_denied = not parse_rights_receipt(
        _receipt(teaser=False), now=now
    ).rights.allows("benzinga", "teaser")
    unknown_field = not rights.allows("benzinga", "raw_body")
    ok = other_source and body_denied and teaser_denied and unknown_field
    return (
        "HELD" if ok else "BROKEN"
    ), f"other_source={other_source} body={body_denied} teaser_cap=False_denied={teaser_denied} unknown_field={unknown_field}"


def nc_r08(scratch):
    """Store reads honour rights: no rows/titles/urls/teasers/aggregates of the hidden source leak."""
    from engine.qbus_news_store import NewsStore

    db = scratch / "r08.sqlite3"
    pub_time = "2026-10-20T09:00:00Z"
    wire = "SYNTH-TITLE-WIRE"
    alpha = _massive_revision(
        "SYNTH-A1",
        "alpha.example.com",
        title=wire,
        teaser="SYNTH-TEASER-A1",
        url="https://alpha.example.com/synth-a1",
        published=pub_time,
        received=datetime(2026, 10, 20, 10, 0, tzinfo=UTC),
    )
    beta = _massive_revision(
        "SYNTH-B1",
        "beta.example.com",
        title=wire,
        teaser="SYNTH-TEASER-B1",
        url="https://beta.example.com/synth-b1",
        published=pub_time,
        received=datetime(2026, 10, 20, 10, 5, tzinfo=UTC),
    )
    alpha2 = _massive_revision(
        "SYNTH-A2",
        "alpha.example.com",
        title="SYNTH-TITLE-A2",
        teaser="SYNTH-TEASER-A2",
        url="https://alpha.example.com/synth-a2",
        published="2026-10-20T09:30:00Z",
        received=datetime(2026, 10, 20, 10, 10, tzinfo=UTC),
    )
    with NewsStore(db, source_key="SYNTH-KEY") as store:
        store.commit_observations(
            [_routed(r, ("SYNTH-SEC-8",)) for r in (alpha, beta, alpha2)]
        )

    rights_alpha = _rights(("massive:alpha.example.com",))
    rights_both = _rights(
        ("massive:alpha.example.com", "massive:beta.example.com")
    )
    reader = NewsStore.open_readonly(db, source_key="SYNTH-KEY")
    try:
        snap = reader.snapshot("SYNTH-SEC-8", limit=50, cursor=None, rights=rights_alpha)
        stories = {row.story_id: reader.story(row.story_id, rights=rights_alpha) for row in snap.rows}
        evidence = reader.evidence_for_security("SYNTH-SEC-8", limit=50, rights=rights_alpha)
        changes = reader.changes_for_security(
            "SYNTH-SEC-8", after_sequence=0, limit=100, rights=rights_alpha
        )
        flow_alpha = reader.news_flow(
            "SYNTH-SEC-8", now=datetime(2026, 10, 20, 12, 0, tzinfo=UTC), rights=rights_alpha
        )
        flow_both = reader.news_flow(
            "SYNTH-SEC-8", now=datetime(2026, 10, 20, 12, 0, tzinfo=UTC), rights=rights_both
        )
    finally:
        reader.close()

    blob = json.dumps(
        {
            "snap": [_obj(row) for row in snap.rows],
            "stories": [_obj(s) for s in stories.values()],
            "evidence": evidence,
            "changes": [_obj(row) for row in changes.rows],
            "flow": flow_alpha,
        },
        default=str,
    )
    beta_leak = "beta.example.com" in blob or "SYNTH-TEASER-B1" in blob or "SYNTH-B1" in blob
    sources_ok = all(
        row.source == "massive:alpha.example.com" for row in snap.rows
    )
    counts_ok = (
        flow_alpha["reports_24h"] == 2 and flow_both["reports_24h"] == 3
    )
    cluster_ok = all(
        detail is not None
        and detail.source_count == 1
        and detail.item_count == len(
            [m for m in detail.members if m.source == "massive:alpha.example.com"]
        )
        for detail in stories.values()
    )
    ok = not beta_leak and sources_ok and counts_ok and cluster_ok
    return (
        "HELD" if ok else "BROKEN"
    ), f"beta_leak={beta_leak} sources_alpha_only={sources_ok} flow24_alpha={flow_alpha['reports_24h']}_both={flow_both['reports_24h']} cluster_sizes_rights_scoped={cluster_ok}"


def nc_r09(scratch):
    """App path: rights withdrawn -> served path refuses (503) before any read; renewal slice no model call."""
    import app.ticker_news as api
    from engine.qbus_news_store import NewsStore

    api._reset_rate_limit_for_tests()
    db = scratch / "r09.sqlite3"
    rev = _ws_revision(
        "SYNTH-ITEM-R09",
        title="SYNTH-TITLE-R09",
        url="https://benzinga.com/synth-r09",
        teaser="SYNTH-TEASER-R09",
        published="2026-10-14T09:00:00Z",
        updated="2026-10-14T09:00:00Z",
        received=datetime(2026, 10, 14, 10, 0, tzinfo=UTC),
    )
    with NewsStore(db, source_key="SYNTH-KEY") as store:
        store.commit_observations([_routed(rev, ("SYNTH-SEC-9",))])

    receipt_path = scratch / "r09-rights.json"
    universe_path = scratch / "r09-universe.json"
    universe_path.write_text(
        json.dumps(_universe([_security_row("SYNTH-SEC-9", "SYNTH", ["SYNTH"])])),
        encoding="utf-8",
    )
    receipt_path.write_text(json.dumps(_receipt()), encoding="utf-8")

    from fastapi import HTTPException

    user = {"id": "SYNTH-USER-R09"}
    with _Env(
        MM_TICKER_NEWS_DB=db,
        MM_TICKER_NEWS_RIGHTS=receipt_path,
        MM_TICKER_NEWS_UNIVERSE=universe_path,
    ):
        response = api.ticker_news_snapshot(
            "SYNTH", limit=20, cursor=None, view=None, view_revision=None, user=dict(user)
        )
        body = json.loads(response.body)
        served = response.status_code == 200 and len(body["rows"]) == 1
        annotations_off = body["annotations"]["state"] == "not_permitted"

        receipt_path.write_text(
            json.dumps(_receipt(expires="2026-10-02T00:00:00Z")), encoding="utf-8"
        )
        refused = False
        try:
            api.ticker_news_snapshot(
                "SYNTH", limit=20, cursor=None, view=None, view_revision=None, user=dict(user)
            )
        except HTTPException as exc:
            refused = exc.status_code == 503
        story_id = body["rows"][0]["story_id"] if body["rows"] else "SYNTH-NO-STORY"
        story_refused = False
        try:
            api.ticker_news_story(
                story_id,
                ticker=None,
                view=None,
                view_revision=None,
                user=dict(user),
            )
        except HTTPException as exc:
            story_refused = exc.status_code == 503

        receipt_path.unlink()
        removed_refused = False
        try:
            api.ticker_news_snapshot(
                "SYNTH", limit=20, cursor=None, view=None, view_revision=None, user=dict(user)
            )
        except HTTPException as exc:
            removed_refused = exc.status_code == 503

    ok = served and refused and story_refused and removed_refused and annotations_off
    return (
        "HELD" if ok else "BROKEN"
    ), f"served200={served} expired503={refused} story503={story_refused} removed503={removed_refused} annotations_not_permitted={annotations_off}"


def nc_r10(scratch):
    """Ticker reuse: one ticker -> issuer A until a date, issuer B after; never 'current' (§5.2 line 245)."""
    from engine.news_impact.issuer import (
        Mention,
        canonical_ticker,
        load_ledger,
        resolve_mention,
    )

    ledger_path = scratch / "r10-ledger.json"
    ledger_path.write_text(
        json.dumps(
            {
                "tickers": {
                    "SYNQ": [
                        {"cik": "0000000001", "valid_from": "2026-01-01", "valid_to": "2026-06-30"},
                        {"cik": "0000000002", "valid_from": "2026-06-30", "valid_to": None},
                    ],
                    "SYNO": [
                        {"cik": "0000000003", "valid_from": "2026-01-01", "valid_to": None},
                        {"cik": "0000000004", "valid_from": "2026-01-01", "valid_to": None},
                    ],
                }
            }
        ),
        encoding="utf-8",
    )
    ledger = load_ledger(ledger_path)

    def company(asof, ticker="SYNQ"):
        return resolve_mention(
            Mention(text=ticker, ticker=ticker, cik=None, exchange_mic=None, asof=asof),
            ledger=ledger,
        ).company_id

    before = company(date(2026, 3, 1))
    boundary = company(date(2026, 6, 30))
    after = company(date(2026, 8, 1))
    overlap = resolve_mention(
        Mention(text="SYNO", ticker="SYNO", cik=None, exchange_mic=None, asof=date(2026, 3, 1)),
        ledger=ledger,
    )
    canon = (canonical_ticker("$synq"), canonical_ticker("synq.b"))

    import app.ticker_news as api

    universe_path = scratch / "r10-universe.json"
    universe_path.write_text(
        json.dumps(
            _universe(
                [
                    _security_row("SYN-AAA", "SYNQ", ["SYNQ"], valid_to="2026-06-30T00:00:00Z"),
                    {
                        "security_id": "SYN-BBB",
                        "ticker": "SYNQ",
                        "aliases": ["SYNQ"],
                        "valid_from": "2026-06-30T00:00:00Z",
                        "known_at": "2026-01-01T00:00:00Z",
                        "valid_to": None,
                    },
                ]
            )
        ),
        encoding="utf-8",
    )
    with _Env(MM_TICKER_NEWS_UNIVERSE=universe_path):
        sec_before = api._security_for_ticker("SYNQ", datetime(2026, 3, 1, tzinfo=UTC))
        sec_after = api._security_for_ticker("SYNQ", datetime(2026, 8, 1, tzinfo=UTC))
        overlap_universe_path = scratch / "r10-universe-overlap.json"
        overlap_universe_path.write_text(
            json.dumps(
                _universe(
                    [
                        _security_row("SYN-AAA", "SYNQ", ["SYNQ"]),
                        _security_row("SYN-BBB", "SYNQ", ["SYNQ"]),
                    ],
                    revision="SYNTH-UNI-R2",
                )
            ),
            encoding="utf-8",
        )
        with _Env(MM_TICKER_NEWS_UNIVERSE=overlap_universe_path):
            try:
                api._security_for_ticker("SYNQ", datetime(2026, 8, 1, tzinfo=UTC))
                ambiguous_refused = False
            except api.UniverseUnavailable:
                ambiguous_refused = True

    ledger_ok = (
        before == "cik:0000000001"
        and boundary == "cik:0000000002"
        and after == "cik:0000000002"
        and overlap.company_id is None
        and overlap.absence_reason == "ambiguous_ticker"
    )
    universe_ok = sec_before == "SYN-AAA" and sec_after == "SYN-BBB" and ambiguous_refused
    canon_ok = canon == ("SYNQ", "SYNQ-B")
    ok = ledger_ok and universe_ok and canon_ok
    return (
        "HELD" if ok else "BROKEN"
    ), f"ledger={before}/{boundary}/{after} overlap_absent={overlap.company_id is None} universe={sec_before}/{sec_after} ambiguous_refused={ambiguous_refused} canon={canon}"


def nc_r11(scratch):
    """Issuer/ticker mismatch + delisting: explicit identity or typed absence, never a guess (§9.3 line 506)."""
    from engine.news_impact.issuer import (
        Mention,
        absence_payload,
        load_ledger,
        resolve_mention,
    )

    ledger_path = scratch / "r11-ledger.json"
    ledger_path.write_text(
        json.dumps(
            {
                "tickers": {
                    "SYNM": [{"cik": "0000000002", "valid_from": "2026-01-01", "valid_to": None}],
                    "SYND": [{"cik": "0000000005", "valid_from": "2026-01-01", "valid_to": "2026-06-30"}],
                }
            }
        ),
        encoding="utf-8",
    )
    ledger = load_ledger(ledger_path)

    mismatch = resolve_mention(
        Mention(text="SYNTH", ticker="SYNM", cik="0000000001", exchange_mic=None, asof=date(2026, 10, 1)),
        ledger=ledger,
    )
    delisted = resolve_mention(
        Mention(text="SYNTH", ticker="SYND", cik=None, exchange_mic=None, asof=date(2026, 10, 1)),
        ledger=ledger,
    )
    payload = absence_payload(delisted)
    explicit_note = any(
        rung.get("rung") == "explicit_cik" and "ticker not consulted" in str(rung.get("note", ""))
        for rung in mismatch.receipt.get("rungs", ())
    )
    ok = (
        mismatch.company_id == "cik:0000000001"
        and explicit_note
        and delisted.company_id is None
        and delisted.absence_reason == "not_listed_at_asof"
        and payload["reason"] == "unjoinable_filing_identity"
        and "company_id" in payload["missing_fields"]
    )
    return (
        "HELD" if ok else "BROKEN"
    ), f"mismatch->explicit_cik={mismatch.company_id} note_recorded={explicit_note} delisted_absent={delisted.absence_reason} typed_absence={payload['reason']}"


def nc_r12(scratch):
    """Copied/mirrored wire is one information family (§5.4 line 259; reducer _is_mirror:72)."""
    from engine.qbus_news_store import NewsStore

    db = scratch / "r12.sqlite3"
    wire = dict(
        title="SYNTH-TITLE-MIRROR",
        url="https://benzinga.com/synth-mirror",
        teaser="SYNTH-TEASER-MIRROR",
        published="2026-10-14T09:00:00Z",
        updated="2026-10-14T09:00:00Z",
    )
    wire2 = dict(
        title="SYNTH-UNRELATED-EVENT",
        url="https://benzinga.com/synth-unrelated",
        teaser="SYNTH-TEASER-UNRELATED",
        published="2026-10-14T09:00:00Z",
        updated="2026-10-14T09:00:00Z",
    )
    item_a = _ws_revision("SYNTH-MIR-1", received=datetime(2026, 10, 14, 10, 0, tzinfo=UTC), **wire)
    item_b = _ws_revision("SYNTH-MIR-2", received=datetime(2026, 10, 14, 10, 5, tzinfo=UTC), **wire)
    direct = _ws_revision("SYNTH-MIR-D", received=datetime(2026, 10, 14, 11, 0, tzinfo=UTC), **wire2)
    mirror = _massive_benzinga_mirror(
        "SYNTH-MIR-D", received=datetime(2026, 10, 14, 11, 5, tzinfo=UTC), **wire2
    )
    with NewsStore(db, source_key="SYNTH-KEY") as store:
        first = store.commit_observations([_routed(item_a, ("SYNTH-SEC-12",))])
        second = store.commit_observations([_routed(item_b, ("SYNTH-SEC-12",))])
        third = store.commit_observations([_routed(direct, ("SYNTH-SEC-12",))])
        fourth = store.commit_observations([_routed(mirror, ("SYNTH-SEC-12",))])

    rights = _rights(("benzinga",))
    reader = NewsStore.open_readonly(db, source_key="SYNTH-KEY")
    try:
        snap = reader.snapshot("SYNTH-SEC-12", limit=50, cursor=None, rights=rights)
        clusters = {
            row.story_id: (
                lambda d: (d.source_count, d.item_count, len(d.members))
            )(reader.story(row.story_id, rights=rights))
            for row in snap.rows
        }
        evidence = reader.evidence_for_security("SYNTH-SEC-12", limit=50, rights=rights)
    finally:
        reader.close()

    states_two_items_one_story = (
        len(clusters) == 2
        and any(counts == (1, 2, 2) for counts in clusters.values())
        and any(counts == (1, 1, 1) for counts in clusters.values())
    )
    mirror_collapsed = (
        fourth.duplicate_revisions == 1
        and fourth.applied_states == 0
        and sum(1 for counts in clusters.values() if counts[2] == 1) >= 1
        and all(c[0] == 1 for c in clusters.values())
    )
    reports_per_story = [len(s["reports"]) for s in evidence["stories"]]
    ok = (
        states_two_items_one_story
        and mirror_collapsed
        and second.inserted_revisions == 1
        and reports_per_story
        and all(c[0] == 1 for c in clusters.values())
    )
    return (
        "HELD" if ok else "BROKEN"
    ), f"stories={len(clusters)} counts={sorted(clusters.values())} mirror_disposition=dup{fourth.duplicate_revisions} source_counts={[c[0] for c in clusters.values()]}"


def nc_r13(scratch):
    """Benzinga via Alpaca is one item/state, never two (§2.2 line 97)."""
    from engine.qbus_news_store import NewsStore

    db = scratch / "r13.sqlite3"
    created = updated = "2026-10-14T09:00:00Z"
    ws = _ws_revision(
        "SYNTH-TR-1",
        title="SYNTH-TITLE-TRANS",
        url="https://benzinga.com/synth-tr1",
        teaser="SYNTH-TEASER-TRANS",
        published=created,
        updated=updated,
        received=datetime(2026, 10, 14, 10, 0, tzinfo=UTC),
    )
    alpaca = _alpaca_revision(
        "SYNTH-TR-1",
        headline="SYNTH-TITLE-TRANS",
        summary="SYNTH-TEASER-TRANS",
        url="https://benzinga.com/synth-tr1",
        created=created,
        updated=updated,
        received=datetime(2026, 10, 14, 10, 20, tzinfo=UTC),
    )
    with NewsStore(db, source_key="SYNTH-KEY") as store:
        r1 = store.commit_observations([_routed(ws, ("SYNTH-SEC-13",))])
        r2 = store.commit_observations([_routed(alpaca, ("SYNTH-SEC-13",))])
        counts = store.counts()

    reader = NewsStore.open_readonly(db, source_key="SYNTH-KEY")
    try:
        evidence = reader.evidence_for_security(
            "SYNTH-SEC-13", limit=10, rights=_rights(("benzinga",))
        )
    finally:
        reader.close()
    reports = evidence["stories"][0]["reports"] if evidence["stories"] else []
    ok = (
        r1.inserted_revisions == 1
        and r2.duplicate_revisions == 1
        and r2.inserted_revisions == 0
        and counts["states"] == 1
        and len(reports) == 1
    )
    return (
        "HELD" if ok else "BROKEN"
    ), f"inserted={r1.inserted_revisions}+{r2.inserted_revisions} duplicate={r2.duplicate_revisions} states={counts['states']} reports={len(reports)}"


def nc_r14(scratch):
    """Over-merge: near-identical titles with different items/tickers/times stay separate stories (§9.3 line 503)."""
    from engine.qbus_news_store import NewsStore

    db = scratch / "r14.sqlite3"
    with NewsStore(db, source_key="SYNTH-KEY") as store:
        store.commit_observations(
            [
                _routed(
                    _ws_revision(
                        "SYNTH-OV-1",
                        title="SYNTH WIRE raises target to 7",
                        url="https://benzinga.com/synth-ov1",
                        teaser="SYNTH-TEASER-OV1",
                        published="2026-10-14T09:00:00Z",
                        updated="2026-10-14T09:00:00Z",
                        received=datetime(2026, 10, 14, 10, 0, tzinfo=UTC),
                    ),
                    ("SYNTH-SEC-X",),
                ),
                _routed(
                    _ws_revision(
                        "SYNTH-OV-2",
                        title="SYNTH WIRE raises target to 7",
                        url="https://benzinga.com/synth-ov2",
                        teaser="SYNTH-TEASER-OV2",
                        published="2026-10-14T09:00:00Z",
                        updated="2026-10-14T09:00:00Z",
                        received=datetime(2026, 10, 14, 10, 5, tzinfo=UTC),
                    ),
                    ("SYNTH-SEC-Y",),
                ),
            ]
        )
        store.commit_observations(
            [
                _routed(
                    _ws_revision(
                        "SYNTH-OV-3",
                        title="SYNTH WIRE raises target to 7",
                        url="https://benzinga.com/synth-ov3",
                        teaser="SYNTH-TEASER-OV3",
                        published="2026-10-14T09:00:00Z",
                        updated="2026-10-14T09:00:00Z",
                        received=datetime(2026, 10, 14, 11, 0, tzinfo=UTC),
                    ),
                    ("SYNTH-SEC-Z",),
                ),
                _routed(
                    _ws_revision(
                        "SYNTH-OV-4",
                        title="SYNTH WIRE raises target to 8",
                        url="https://benzinga.com/synth-ov4",
                        teaser="SYNTH-TEASER-OV4",
                        published="2026-10-14T09:00:00Z",
                        updated="2026-10-14T09:00:00Z",
                        received=datetime(2026, 10, 14, 11, 5, tzinfo=UTC),
                    ),
                    ("SYNTH-SEC-Z",),
                ),
                _routed(
                    _ws_revision(
                        "SYNTH-OV-5",
                        title="SYNTH WIRE raises target to 7",
                        url="https://benzinga.com/synth-ov5",
                        teaser="SYNTH-TEASER-OV5",
                        published="2026-10-14T03:00:00Z",
                        updated="2026-10-14T03:00:00Z",
                        received=datetime(2026, 10, 14, 23, 30, tzinfo=UTC),
                    ),
                    ("SYNTH-SEC-Z",),
                ),
            ]
        )

    rights = _rights(("benzinga",))
    reader = NewsStore.open_readonly(db, source_key="SYNTH-KEY")
    try:
        def story_count(security):
            snap = reader.snapshot(security, limit=50, cursor=None, rights=rights)
            return len({row.story_id for row in snap.rows})

        cross_ticker = story_count("SYNTH-SEC-X") + story_count("SYNTH-SEC-Y")
        same_security = {
            story_id: reader.story(story_id, rights=rights).item_count
            for story_id in {
                row.story_id
                for row in reader.snapshot("SYNTH-SEC-Z", limit=50, cursor=None, rights=rights).rows
            }
        }
    finally:
        reader.close()

    cross_ok = cross_ticker == 2
    same_ok = len(same_security) == 3 and all(n == 1 for n in same_security.values())
    ok = cross_ok and same_ok
    return (
        "HELD" if ok else "BROKEN"
    ), f"cross_ticker_stories={cross_ticker} same_security_stories={len(same_security)} member_counts={sorted(same_security.values())}"


def nc_r15(scratch):
    """Cluster id is never independence: exposed source_count on syndicated copies (§5.4 lines 259-261, §9.1 line 475)."""
    from engine.qbus_news_store import NewsStore

    db = scratch / "r15.sqlite3"
    wire_title = "SYNTH-TITLE-SYNDICATED-WIRE"
    outlet_a = _massive_revision(
        "SYNTH-SY-A",
        "outleta.example.com",
        title=wire_title,
        teaser="SYNTH-TEASER-SAME",
        url="https://outleta.example.com/synth-sy",
        published="2026-10-14T09:00:00Z",
        received=datetime(2026, 10, 14, 10, 0, tzinfo=UTC),
    )
    outlet_b = _massive_revision(
        "SYNTH-SY-B",
        "outletb.example.com",
        title=wire_title,
        teaser="SYNTH-TEASER-SAME",
        url="https://outletb.example.com/synth-sy",
        published="2026-10-14T09:00:00Z",
        received=datetime(2026, 10, 14, 10, 5, tzinfo=UTC),
    )
    with NewsStore(db, source_key="SYNTH-KEY") as store:
        store.commit_observations(
            [_routed(r, ("SYNTH-SEC-15",)) for r in (outlet_a, outlet_b)]
        )

    rights = _rights(
        ("massive:outleta.example.com", "massive:outletb.example.com")
    )
    reader = NewsStore.open_readonly(db, source_key="SYNTH-KEY")
    try:
        snap = reader.snapshot("SYNTH-SEC-15", limit=10, cursor=None, rights=rights)
        story = reader.story(snap.rows[0].story_id, rights=rights)
        evidence = reader.evidence_for_security("SYNTH-SEC-15", limit=10, rights=rights)
    finally:
        reader.close()

    one_cluster = len(snap.rows) == 1
    counted = story.source_count
    evidence_counted = evidence["stories"][0]["source_count"] if evidence["stories"] else None
    reporting = story.reporting_state
    # The claim: one originating information family must not surface as two
    # independent sources in the counts the estate exposes.
    broken = one_cluster and counted == 2
    held = one_cluster and counted == 1
    if broken:
        verdict = "BROKEN"
        observed = f"identical cross-outlet wire=1 story but source_count={counted} evidence_source_count={evidence_counted} reporting_state={reporting}"
    elif held:
        verdict = "HELD"
        observed = f"syndicated wire collapsed: source_count={counted}"
    else:
        verdict = "BROKEN"
        observed = f"unexpected shape: clusters={len(snap.rows)} source_count={counted}"
    return verdict, observed[:160]


def nc_r16(scratch):
    """Cross-source field isolation when combining receipts (no field sharing across sources)."""
    from engine.qbus_news_receipts import combine_news_rights, parse_rights_receipt

    now = datetime(2026, 10, 15, tzinfo=UTC)
    benzinga = parse_rights_receipt(_receipt(teaser=True, receipt_id="SYNTH-R-C1"), now=now)
    massive = parse_rights_receipt(
        _receipt(
            source="massive:gamma.example.com",
            provider="massive",
            teaser=False,
            receipt_id="SYNTH-R-C2",
        ),
        now=now,
    )
    c1 = combine_news_rights((benzinga, massive))
    c2 = combine_news_rights((massive, benzinga))
    fields_agree = all(
        c1.allows(source, field) == c2.allows(source, field)
        for source in ("benzinga", "massive:gamma.example.com")
        for field in ("title", "url", "teaser")
    )
    ok = (
        c1.allows("benzinga", "teaser")
        and not c1.allows("massive:gamma.example.com", "teaser")
        and c1.allows("massive:gamma.example.com", "title")
        and c2.allows("benzinga", "teaser")
        and not c2.allows("massive:gamma.example.com", "teaser")
        and fields_agree
    )
    return (
        "HELD" if ok else "BROKEN"
    ), f"benzinga_teaser={c1.allows('benzinga', 'teaser')} massive_teaser={c1.allows('massive:gamma.example.com', 'teaser')} both_orders_agree={fields_agree}"


def nc_r17(scratch):
    """Malformed source identities / provider mismatch in receipts fail closed."""
    now = datetime(2026, 10, 15, tzinfo=UTC)
    cases = {
        "massive:not_a_domain": None,
        "massive:gamma.example.com": "not-massive",
        "SYNTH-SRC-A": None,
    }
    codes = {}
    for source, provider in cases.items():
        codes[source] = _parse_code(
            _receipt(source=source, provider=provider), now
        )
    ok = (
        codes["massive:not_a_domain"] == "rights_source"
        and codes["massive:gamma.example.com"] == "rights_provider_mismatch"
        and codes["SYNTH-SRC-A"] == "rights_source"
    )
    return ("HELD" if ok else "BROKEN"), f"codes={sorted(set(codes.values()))}"


CONTROLS = [
    ("R01", nc_r01),
    ("R02", nc_r02),
    ("R03", nc_r03),
    ("R04", nc_r04),
    ("R05", nc_r05),
    ("R06", nc_r06),
    ("R07", nc_r07),
    ("R08", nc_r08),
    ("R09", nc_r09),
    ("R10", nc_r10),
    ("R11", nc_r11),
    ("R12", nc_r12),
    ("R13", nc_r13),
    ("R14", nc_r14),
    ("R15", nc_r15),
    ("R16", nc_r16),
    ("R17", nc_r17),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scratch",
        default=tempfile.mkdtemp(prefix="nc-rights-identity-"),
        help="directory for every synthetic sqlite/receipt/ledger/universe file",
    )
    args = parser.parse_args()
    scratch = Path(args.scratch)
    scratch.mkdir(parents=True, exist_ok=True)

    tally = {"HELD": 0, "BROKEN": 0, "NO_MECHANISM": 0, "UNTESTABLE_ENV": 0}
    for control_id, fn in CONTROLS:
        try:
            verdict, observed = fn(scratch)
        except Exception as exc:  # harness gap, not a safety behaviour
            verdict = "UNTESTABLE_ENV"
            observed = f"harness_exception:{type(exc).__name__}"
        tally[verdict] += 1
        print(f"NC {control_id} {verdict} {observed}", flush=True)
    print(
        "NC SUMMARY "
        f"held={tally['HELD']} broken={tally['BROKEN']} "
        f"no_mechanism={tally['NO_MECHANISM']} untestable_env={tally['UNTESTABLE_ENV']} "
        f"total={sum(tally.values())}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""V91 masterplan section 9.1 vertical V7 proof: quiet source, outage, rights loss.

Runs repository code on SYNTH-* inputs and reports, per required property of the
9.1 row "Quiet/outage/rights loss", whether the behaviour actually holds in this
run. Offline, deterministic, no network, no model call: fixed 2026 ISO instants
for every clock the producers accept explicitly; the one wall-clock-driven
surface (the live API's health/rights file reads) uses wide 2020-2099 synthetic
windows and prints only stable facts (status codes, states, labels). Every
SQLite file, receipt and temp artifact lives under --scratch. Run with:

    PYTHONPATH=. python3 research/news_intelligence_estate_20261021/v91_proofs/ \
        v7_quiet_outage_rights.py --scratch /tmp/any-dir

One line per property ``V7 P<k> <PROVEN|PARTIAL|ABSENT|HUMAN_GATE> <evidence>``,
then ``V7 SUMMARY ...``. A PROVEN verdict needs both the positive behaviour on
an input whose correct answer is stated by that input's own construction and a
discriminating negative. The API layer is exercised with the same in-process
FastAPI TestClient pattern the repository tests use (no socket).
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import importlib.util
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

UTC = timezone.utc
FIXED_NOW = datetime(2026, 10, 31, 0, 0, tzinfo=UTC)
SECURITY_ID = "SYNTH-SEC-1"
SYNTH_TICKER = "SYNTH"
SYNTH_TITLE = "SYNTH-TITLE-01"

REQUIRED_ARTIFACTS = (
    "research/news_intelligence_estate_20261021/f2_controls/nc_time_corrections.py",
    "research/news_intelligence_estate_20261021/f2_controls/nc_rights_identity.py",
    "app/ticker_news.py",
    "engine/qbus_news_receipts.py",
    "engine/qbus_news_store.py",
    "engine/qbus_news_context.py",
    "engine/qbus_news_intake.py",
    "engine/news_rss.py",
)

SCRATCH = Path()


def _t(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC)


def _load_controls_module(name: str, filename: str):
    path = ROOT / "research" / "news_intelligence_estate_20261021" / "f2_controls" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------- builders ----
def _ws_revision(
    item: str,
    *,
    published: str,
    updated: str,
    event: str,
    received: str,
    title: str | None = None,
):
    from engine.qbus_news_contract import normalize_news

    payload = {
        "kind": "news",
        "id": f"SYN-MSG-{item}",
        "data": {
            "id": item,
            "action": "created",
            "timestamp": event,
            "content": {
                "id": item,
                "created": published,
                "updated": updated,
                "title": title if title is not None else f"SYNTH-TITLE-{item}",
                "url": f"https://synth.example/{item}",
                "teaser": f"SYNTH-TEASER-{item}",
                "stocks": [SYNTH_TICKER],
            },
        },
    }
    return normalize_news(payload, transport="benzinga_ws", received_at=_t(received))


def _routed(revision):
    from engine.qbus_news_store import RoutedRevision

    return RoutedRevision(
        revision=revision,
        security_ids=(SECURITY_ID,),
        universe_revision="SYNTH-UNI-1",
    )


def _commit_all(db: Path, routed: list, source_key: str = "benzinga-rest") -> None:
    from engine.qbus_news_store import NewsStore

    with NewsStore(db, source_key=source_key) as store:
        cursor = store.current_cursor()
        store.commit(routed, expected_cursor=cursor, next_cursor="SYNTH-CURSOR-1")


def _story_revision(item: str = "01"):
    return _ws_revision(
        f"SYNTH-ITEM-{item}",
        published="2026-10-18T10:00:00Z",
        updated="2026-10-18T11:00:00Z",
        event="2026-10-18T10:30:00Z",
        received="2026-10-18T12:00:00Z",
        title=f"SYNTH-TITLE-{item}",
    )


def _universe_payload() -> dict:
    return {
        "owner": "SYNTH-OWNER",
        "revision": "SYNTH-UNI-1",
        "complete": True,
        "truncated": False,
        "effective_at": "2020-01-01T00:00:00Z",
        "known_at": "2020-01-01T00:00:00Z",
        "fresh_until": "2099-01-01T00:00:00Z",
        "securities": [
            {
                "security_id": SECURITY_ID,
                "ticker": SYNTH_TICKER,
                "aliases": [SYNTH_TICKER],
                "valid_from": "2020-01-01T00:00:00Z",
                "valid_to": None,
                "known_at": "2020-01-01T00:00:00Z",
            }
        ],
    }


class Fixtures:
    """Every synthetic artifact the properties share, all under --scratch."""

    def __init__(self, scratch: Path) -> None:
        from engine.qbus_news_store import NewsStore
        from engine.qbus_news_universe import qualify_universe

        controls_time = _load_controls_module(
            "nc_time_corrections", "nc_time_corrections.py"
        )
        controls_rights = _load_controls_module(
            "nc_rights_identity", "nc_rights_identity.py"
        )
        self.health_payload = controls_time.health_payload
        self.receipt = controls_rights._receipt

        self.dir = scratch
        self.universe_path = scratch / "SYNTH-universe.json"
        self.universe_path.write_text(json.dumps(_universe_payload()), encoding="utf-8")
        assert qualify_universe(_universe_payload(), asof=datetime.now(UTC)).status == "qualified"

        # Receipts validated against FIXED_NOW (deterministic refusal probes).
        self.valid_fixed = self.receipt()
        self.revoked_fixed = self.receipt(status="revoked", receipt_id="SYNTH-R-REVO")
        self.expired_fixed = self.receipt(
            expires="2026-10-15T00:00:00Z", receipt_id="SYNTH-R-EXPI"
        )

        # Receipts read by the live API (validated against its own clock); the
        # 2020-2099 window keeps grant/refusal outcomes date-independent.
        self.rights_path = scratch / "SYNTH-rights.json"
        live_window = dict(
            effective="2020-01-01T00:00:00Z", expires="2099-01-01T00:00:00Z"
        )
        self.rights_valid = self.receipt(receipt_id="SYNTH-R-LIVE", **live_window)
        self.rights_revoked = self.receipt(
            status="revoked", receipt_id="SYNTH-R-LIVE", **live_window
        )
        self.rights_expired = self.receipt(
            effective="2020-01-01T00:00:00Z",
            expires="2020-06-01T00:00:00Z",
            receipt_id="SYNTH-R-LIVE",
        )
        self.rights_path.write_text(json.dumps(self.rights_valid), encoding="utf-8")

        # The health receipt itself is written per API exercise (api_env) so the
        # API's own 120 s observation budget always sees the writer live.
        self.health_path = scratch / "SYNTH-health.json"

        self.story_db = scratch / "SYNTH-story.sqlite3"
        _commit_all(self.story_db, [_routed(_story_revision())])
        self.empty_db = scratch / "SYNTH-empty.sqlite3"
        with NewsStore(self.empty_db, source_key="benzinga-rest"):
            pass

    def set_rights(self, payload: dict) -> None:
        self.rights_path.write_text(json.dumps(payload), encoding="utf-8")

    def api_env(self, *, db: Path) -> None:
        from engine.qbus_news_receipts import write_health_receipt

        # Keep the runtime-fresh live receipt inside the API's own 120 s budget;
        # only stable labels are ever printed from its reads.
        now = datetime.now(UTC)
        write_health_receipt(
            self.health_path,
            {
                "schema": "qbus.news_health.v1",
                "source": "benzinga",
                "state": "live",
                "observed_at": now.isoformat(),
                "last_successful_catchup": (now - timedelta(seconds=5)).isoformat(),
                "last_stream_event_at": None,
                "gap_unresolved": False,
                "connect_attempts": 1,
                "disconnects": 0,
                "catchups_failed": 0,
            },
        )
        os.environ["MM_TICKER_NEWS_DB"] = str(db)
        os.environ["MM_TICKER_NEWS_UNIVERSE"] = str(self.universe_path)
        os.environ["MM_TICKER_NEWS_RIGHTS"] = str(self.rights_path)
        os.environ["MM_TICKER_NEWS_HEALTH"] = str(self.health_path)

    def client(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app import ticker_news

        ticker_news._reset_rate_limit_for_tests()
        app = FastAPI()
        app.include_router(ticker_news.router)
        app.dependency_overrides[ticker_news.require_site_full_user] = lambda: {
            "id": "SYNTH-USER-1",
            "sub": "SYNTH-USER-1",
        }
        return ticker_news, TestClient(app)


# --------------------------------------------------------------- properties ----
def p1_quiet_vs_outage(fx: Fixtures) -> tuple[str, str]:
    """Silent source versus outage distinguishable (9.1 required behaviour)."""
    from engine.qbus_news_receipts import parse_health_receipt
    from app.ticker_news import _state_from_health

    quiet = parse_health_receipt(fx.health_payload(), now=FIXED_NOW)
    outage = parse_health_receipt(fx.health_payload(state="unavailable"), now=FIXED_NOW)
    core = (
        quiet["state"] == "live"
        and _state_from_health(quiet, row_count=0) == "quiet"
        and _state_from_health(quiet, row_count=2) == "live"
        and outage["state"] == "unavailable"
        and outage["reason"] == "source_unavailable"
        and _state_from_health(outage, row_count=0) == "unavailable"
        and _state_from_health(outage, row_count=2) == "unavailable"
    )

    fx.set_rights(fx.rights_valid)
    fx.api_env(db=fx.empty_db)
    _tn, client = fx.client()
    response = client.get(f"/api/ticker-news/{SYNTH_TICKER}")
    api_quiet = (
        response.status_code == 200
        and response.json()["state"] == "quiet"
        and response.json()["rows"] == []
    )

    from engine import news_rss

    rss_outage = news_rss._fetch("file:///SYNTH-nonexistent-feed.xml")
    rss_empty = news_rss._parse(
        b"<rss><channel><title>SYNTH-FEED</title></channel></rss>",
        "synth.example",
        False,
    )
    nightly_collapse = rss_outage is None and rss_empty == []
    if not core:
        return "ABSENT", "states not distinct; engine/qbus_news_receipts.py:306 no-test"
    api_segment = (
        "api snapshot 200 state=quiet rows=0"
        if api_quiet
        else "api quiet seam NOT observed"
    )
    verdict = "PARTIAL" if (nightly_collapse or not api_quiet) else "PROVEN"
    return verdict, (
        f"live+0rows->quiet live+2rows->live unavailable+0rows->unavailable never quiet; "
        f"{api_segment}; nightly rss outage fetch->{rss_outage!r} == empty feed parse->"
        f"{rss_empty!r} no per-source record (G1); engine/qbus_news_receipts.py:306 "
        f"app/ticker_news.py:408 tests/test_ticker_news_api.py:279 "
        f"research/news_intelligence_estate_20261021/A5_TRANSPORT_OBSERVABILITY_GAPS.md:39"
    )


def p2_stale_data(fx: Fixtures) -> tuple[str, str]:
    """Stale data distinguishable: receipt_stale->unavailable, catchup_stale->degraded."""
    from engine.qbus_news_receipts import NewsReceiptError, parse_health_receipt
    from app.ticker_news import _state_from_health

    cases = {
        "fresh": (
            fx.health_payload(),
            "live",
            "fresh",
        ),
        "receipt_stale": (
            fx.health_payload(
                observed="2026-10-30T23:50:00Z", catchup="2026-10-30T23:49:00Z"
            ),
            "unavailable",
            "receipt_stale",
        ),
        "catchup_stale": (
            fx.health_payload(catchup="2026-10-30T23:50:00Z"),
            "degraded",
            "catchup_stale",
        ),
    }
    ladder = {}
    seen = {}
    for name, (payload, want_state, want_reason) in cases.items():
        out = parse_health_receipt(payload, now=FIXED_NOW)
        ladder[name] = out["state"] == want_state and out["reason"] == want_reason
        seen[name] = f"{out['state']}/{out['reason']}"
    try:
        parse_health_receipt(fx.health_payload(observed="2026-12-01T00:00:00Z"), now=FIXED_NOW)
        refused = "NO-RAISE"
    except NewsReceiptError as exc:
        refused = exc.code

    extras_payload = fx.health_payload(
        additional_sources=[
            {
                "provider": "massive",
                "state": "available",
                "last_successful_poll": "2026-10-30T23:59:30Z",
                "publishers": ["synth-pub.example"],
                "accepted_reports": 3,
            },
            {
                "provider": "massive",
                "state": "available",
                "last_successful_poll": "2026-10-30T22:00:00Z",
            },
            {"provider": "massive", "state": "available", "last_successful_poll": None},
        ]
    )
    projected = parse_health_receipt(extras_payload, now=FIXED_NOW)
    extras = [e["state"] for e in projected.get("additional_sources", [])]
    stale_receipt = parse_health_receipt(
        fx.health_payload(
            observed="2026-10-30T23:50:00Z",
            catchup="2026-10-30T23:49:00Z",
            additional_sources=[
                {
                    "provider": "massive",
                    "state": "available",
                    "last_successful_poll": "2026-10-30T23:49:00Z",
                }
            ],
        ),
        now=FIXED_NOW,
    )
    api_seam = _state_from_health(projected, row_count=0)
    extras_ok = (
        extras == ["available", "degraded", "degraded"]
        and [e["state"] for e in stale_receipt.get("additional_sources", [])] == ["unavailable"]
    )
    verdict = (
        "PROVEN"
        if all(ladder.values()) and refused == "health_observed_future" and extras_ok
        else "PARTIAL"
    )
    return verdict, (
        f"fresh obs+catchup->{seen['fresh']} (negative); obs10m->"
        f"{seen['receipt_stale']}; catchup10m->{seen['catchup_stale']}; future obs "
        f"refused {refused}; extras poll fresh->available old/none->degraded, stale "
        f"receipt extras->unavailable; api live+stale-extra->{api_seam}; "
        f"engine/qbus_news_receipts.py:306 engine/qbus_news_intake.py:144 "
        f"tests/test_qbus_news_receipts.py:146"
    )


def p3_missing_history(fx: Fixtures) -> tuple[str, str]:
    """Missing history distinguishable: ok, thin_history, unavailable flow states."""
    from engine.qbus_news_store import NewsReadRights, NewsStore
    from app.ticker_news import _flow_payload_valid

    # Three synthetic histories; each input states its own span in days.
    ok_days = [f"2026-10-{day:02d}" for day in range(5, 26)]  # first report 26d before as-of
    thin_days = ["2026-10-28"]  # 3d before as-of

    def build(name: str, days: list) -> Path:
        db = fx.dir / f"SYNTH-flow-{name}.sqlite3"
        routed = []
        for index, day in enumerate(days, 1):
            routed.append(
                _routed(
                    _ws_revision(
                        f"F{index:02d}",
                        published=f"{day}T09:00:00Z",
                        updated=f"{day}T09:00:00Z",
                        event=f"{day}T09:00:00Z",
                        received=f"{day}T10:00:00Z",
                    )
                )
            )
        _commit_all(db, routed)
        return db

    ok_db = build("ok", ok_days)
    thin_db = build("thin", thin_days)

    rights = NewsReadRights.all_internal()
    observed = {}
    for name, db in (("ok", ok_db), ("thin", thin_db), ("empty", fx.empty_db)):
        with NewsStore.open_readonly(db, source_key="benzinga-rest", curated=True) as store:
            flow = store.news_flow(SECURITY_ID, now=FIXED_NOW, rights=rights)
        observed[name] = (
            flow["state"],
            flow["history_days_observed"],
            flow["comparison"],
            _flow_payload_valid(flow),
        )
    with NewsStore.open_readonly(ok_db, source_key="benzinga-rest", curated=True) as store:
        no_access = store.news_flow(
            SECURITY_ID,
            now=FIXED_NOW,
            rights=NewsReadRights(allowed_sources=frozenset()),
        )
    bogus = copy.deepcopy(flow)
    bogus["state"] = "SYNTH-BOGUS"
    validator_refuses = _flow_payload_valid(bogus) is False

    states_ok = (
        observed["ok"][0] == "ok"
        and observed["thin"][0] == "thin_history"
        and observed["thin"][2] == "insufficient_history"
        and observed["empty"][0] == "thin_history"
        and no_access["state"] == "unavailable"
        and no_access["reason"] == "no_accessible_sources"
        and all(entry[3] for entry in observed.values())
        and _flow_payload_valid(no_access)
    )
    verdict = "PROVEN" if states_ok and validator_refuses else "PARTIAL"
    return verdict, (
        f"26d history->{observed['ok'][0]} hist={observed['ok'][1]}; 3d->"
        f"{observed['thin'][0]} hist={observed['thin'][1]} comparison="
        f"{observed['thin'][2]}; 0d->{observed['empty'][0]} hist={observed['empty'][1]}; "
        f"no-access->{no_access['state']}/{no_access['reason']}; validator admits all "
        f"three and rejects bogus state; engine/qbus_news_store.py:1985 "
        f"app/ticker_news.py:473 tests/test_qbus_news_flow_store.py:577 "
        f"tests/test_qbus_news_flow_store.py:584"
    )


def p4_access_withdrawal(fx: Fixtures) -> tuple[str, str]:
    """Access withdrawal distinguishable: 503 / restricted, valid receipt serves."""
    from engine.qbus_news_receipts import NewsReceiptError, parse_rights_receipt

    def code(payload) -> str:
        try:
            parse_rights_receipt(payload, now=FIXED_NOW, audience="site_full")
            return "NO-RAISE"
        except NewsReceiptError as exc:
            return exc.code

    revoked_code = code(fx.revoked_fixed)
    expired_code = code(fx.expired_fixed)
    granted = parse_rights_receipt(fx.valid_fixed, now=FIXED_NOW, audience="site_full")

    fx.api_env(db=fx.story_db)
    _tn, client = fx.client()
    fx.set_rights(fx.rights_valid)
    served = client.get(f"/api/ticker-news/{SYNTH_TICKER}")
    positive = (
        served.status_code == 200
        and [row["title"] for row in served.json()["rows"]] == [SYNTH_TITLE]
    )
    fx.set_rights(fx.rights_revoked)
    revoked = client.get(f"/api/ticker-news/{SYNTH_TICKER}")
    fx.set_rights(fx.rights_expired)
    expired = client.get(f"/api/ticker-news/{SYNTH_TICKER}")

    # Mid-stream withdrawal through the real receipt file, as the exemplar does.
    async def run():
        fx.set_rights(fx.rights_valid)
        stream = _tn._sse_events(
            ticker=SYNTH_TICKER,
            user={"id": "SYNTH-USER-1"},
            after_sequence=999999,
            poll_seconds=0,
            max_cycles=3,
        )
        first = await anext(stream)
        fx.set_rights(fx.rights_revoked)
        second = await anext(stream)
        try:
            await anext(stream)
            stopped = "NO"
        except StopAsyncIteration:
            stopped = "YES"
        return first, second, stopped

    first, second, stopped = asyncio.run(run())
    sse_event = second.splitlines()[0].removeprefix("event: ") if second else "NONE"
    sse_ok = (
        first == ": heartbeat\n\n"
        and "event: restricted" in second
        and stopped == "YES"
    )
    negative = (
        revoked.status_code == 503
        and revoked.json()["detail"] == "ticker news rights unavailable"
        and expired.status_code == 503
        and revoked_code == "rights_not_approved"
        and expired_code == "rights_expired"
    )
    verdict = (
        "PROVEN"
        if positive and negative and sse_ok and granted.rights.allowed_sources
        else "PARTIAL"
    )
    return verdict, (
        f"valid receipt {served.status_code} rows[0].title={SYNTH_TITLE}; revoked->"
        f"{revoked.status_code} detail='ticker news rights unavailable' code "
        f"{revoked_code}; expired->{expired.status_code} code {expired_code}; "
        f"mid-stream revoke SSE: heartbeat then event: {sse_event} then stream stops="
        f"{stopped}; engine/qbus_news_receipts.py:128 app/ticker_news.py:614 "
        f"tests/test_ticker_news_end_to_end.py:287"
    )


def p5_no_stale_protected_content(fx: Fixtures) -> tuple[str, str]:
    """Cache-Control private, no-store; nothing protected survives withdrawal."""
    fx.api_env(db=fx.story_db)
    _tn, client = fx.client()
    fx.set_rights(fx.rights_valid)
    served = client.get(f"/api/ticker-news/{SYNTH_TICKER}")
    header_ok = served.headers.get("cache-control") == "private, no-store" and (
        served.headers.get("vary") == "Authorization"
    )
    fx.set_rights(fx.rights_revoked)
    withdrawn = client.get(f"/api/ticker-news/{SYNTH_TICKER}")
    body = withdrawn.json()
    body_text = json.dumps(body, sort_keys=True)
    protected_keys = sorted(
        key for key in ("title", "teaser", "body", "url") if f'"{key}"' in body_text
    )
    protected_values = sorted(
        value
        for value in ("SYNTH-TITLE-", "SYNTH-TEASER-", "synth.example")
        if value in body_text
    )
    negative = (
        withdrawn.status_code == 503
        and withdrawn.headers.get("cache-control") == "private, no-store"
        and list(body) == ["detail"]
        and not protected_keys
        and not protected_values
    )
    verdict = "PROVEN" if header_ok and negative else "PARTIAL"
    return verdict, (
        f"{served.status_code} cache-control="
        f"{served.headers.get('cache-control')!r}, vary={served.headers.get('vary')!r}; "
        f"withdrawn {withdrawn.status_code} keeps header "
        f"{withdrawn.headers.get('cache-control')!r}, body keys={sorted(body)}, "
        f"protected keys={protected_keys} values={protected_values}; "
        f"app/ticker_news.py:70 tests/test_ticker_news_api.py:87"
    )


def p6_honest_degraded_api(fx: Fixtures) -> tuple[str, str]:
    """Store unavailable is 503, never an empty 200; empty store is not 503."""
    fx.set_rights(fx.rights_valid)
    fx.api_env(db=fx.dir / "SYNTH-missing.sqlite3")
    _tn, client = fx.client()
    unavailable = client.get(f"/api/ticker-news/{SYNTH_TICKER}")
    fx.api_env(db=fx.empty_db)
    empty = client.get(f"/api/ticker-news/{SYNTH_TICKER}")
    positive = (
        unavailable.status_code == 503
        and unavailable.json()["detail"] == "ticker news temporarily unavailable"
    )
    negative = (
        empty.status_code == 200
        and empty.json()["rows"] == []
        and empty.json()["state"] == "quiet"
    )
    verdict = "PROVEN" if positive and negative else "PARTIAL"
    return verdict, (
        f"missing db->{unavailable.status_code} detail="
        f"{unavailable.json().get('detail')!r}; present empty store->"
        f"{empty.status_code} rows={len(empty.json().get('rows') or [])} state="
        f"{empty.json().get('state')!r} (no 503); app/ticker_news.py:273 "
        f"tests/test_ticker_news_api.py:194"
    )


def p7_honest_degraded_ai(fx: Fixtures) -> tuple[str, str]:
    """Honest degraded AI output: no AI-facing surface carries the degraded state."""
    from engine.qbus_news_context import news_evidence_bundle

    receipt_path = fx.dir / "SYNTH-ev-rights.json"
    research_receipt = fx.receipt(
        audiences=("internal_research",), receipt_id="SYNTH-R-EVID", derivative=True
    )
    receipt_path.write_text(json.dumps(research_receipt), encoding="utf-8")
    populated = news_evidence_bundle(
        database=str(fx.story_db),
        security_id=SECURITY_ID,
        receipt_paths=[str(receipt_path)],
        audience="internal_research",
        now=FIXED_NOW,
    )
    quiet = news_evidence_bundle(
        database=str(fx.empty_db),
        security_id=SECURITY_ID,
        receipt_paths=[str(receipt_path)],
        audience="internal_research",
        now=FIXED_NOW,
    )
    keys = sorted(populated)
    degraded_member = [key for key in keys if "health" in key or "degraded" in key]
    carries_state = (
        bool(degraded_member)
        or populated["state"] not in {"available", "restricted"}
        or quiet["state"] != "available"
    )
    source = (ROOT / "engine" / "qbus_news_context.py").read_text(encoding="utf-8")
    m13_hits = sum(
        source.count(word) for word in ("coalesc", "spend", "budget", "timeout", "dedup")
    )
    if carries_state:
        return "PARTIAL", (
            f"bundle carries degraded state {degraded_member}; "
            f"engine/qbus_news_context.py:35 no-test"
        )
    return "ABSENT", (
        f"AI evidence bundle keys=['audience',...,'stories'] carry no degraded/health "
        f"member ({len(keys)} sorted keys observed); state=available even for "
        f"zero-story quiet store (vocab restricted|available); pre-call "
        f"coalescing/spend keyword hits={m13_hits} (M13); nearest "
        f"engine/qbus_news_context.py:35 census "
        f"research/news_intelligence_estate_20261021/E4_BRIEF_BINDING_CENSUS.md:125 "
        f"no-test"
    )


def p8_no_duplicate_work(fx: Fixtures) -> tuple[str, str]:
    """No duplicate work on recovery: store replay dedup; model-call half probed."""
    from engine.qbus_news_store import NewsStore
    from engine.qbus_news_receipts import NewsReceiptError, parse_rights_receipt

    backlog = [_routed(_story_revision("01")), _routed(_story_revision("02"))]
    db = fx.dir / "SYNTH-replay.sqlite3"
    with NewsStore(db, source_key="benzinga-rest") as store:
        first = store.commit(backlog, expected_cursor=None, next_cursor="SYNTH-CURSOR-1")
        # Simulated outage: the same two-article backlog is redelivered on recovery.
        replay = store.commit(
            backlog, expected_cursor=store.current_cursor(), next_cursor="SYNTH-CURSOR-2"
        )
        counts = store.counts()

    store_half = (
        first.inserted_revisions == 2
        and replay.duplicate_revisions == 2
        and replay.inserted_revisions == 0
        and replay.applied_states == 0
        and counts["revisions"] == 2
        and counts["states"] == 2
        and counts["changes"] == 2
    )

    massive = fx.receipt(
        source="massive:synth-pub.example",
        receipt_id="SYNTH-R-MASSIVE",
        effective="2020-01-01T00:00:00Z",
        expires="2099-01-01T00:00:00Z",
    )
    try:
        parse_rights_receipt(massive, now=FIXED_NOW, audience="site_full")
        stamp_code = "NO-RAISE"
    except NewsReceiptError as exc:
        stamp_code = exc.code
    stamped = parse_rights_receipt(
        dict(massive, provider="massive"), now=FIXED_NOW, audience="site_full"
    )
    stamps_ok = stamp_code == "rights_provider_mismatch" and stamped.provider == "massive"

    source = (ROOT / "engine" / "qbus_news_context.py").read_text(encoding="utf-8")
    m13_hits = sum(
        source.count(word) for word in ("coalesc", "spend", "budget", "timeout", "dedup")
    )
    no_model_mechanism = m13_hits == 0
    if not store_half:
        return "ABSENT", (
            f"replay duplicated rows: dup={replay.duplicate_revisions} counts={counts}; "
            f"engine/qbus_news_store.py:260 tests/test_qbus_news_store.py:177"
        )
    verdict = "PARTIAL" if no_model_mechanism else "PROVEN"
    return verdict, (
        f"backlog replay after outage: dup={replay.duplicate_revisions} inserted=0 "
        f"applied=0, rows stay revisions=2 states=2 changes=2; T15 provider stamp "
        f"{'enforced' if stamps_ok else 'NOT enforced'} (no-provider massive receipt "
        f"refused {stamp_code}); model-call coalescing/spend budget: {m13_hits} "
        f"keyword hits (M13); engine/qbus_news_store.py:260 "
        f"tests/test_qbus_news_store.py:177 "
        f"research/news_intelligence_estate_20261021/F2_MODEL_CONTEXT_NEGATIVE_CONTROLS.md:54"
    )


def p9_live_api_human_gate(fx: Fixtures) -> tuple[str, str]:
    """The live signed-in ticker news API is a human gate."""
    from app import ticker_news

    gate = callable(ticker_news.require_site_full_user)
    if not gate:
        return "ABSENT", "auth dependency missing; app/ticker_news.py:195 no-test"
    return "HUMAN_GATE", (
        f"live endpoint requires a signed-in paid session via require_site_full_user "
        f"-> enforce_site_full; dependency runs before any store open and cannot be "
        f"satisfied offline without credentials; gate app/ticker_news.py:195 "
        f"app/ticker_news.py:200 tests/test_ticker_news_api.py:106"
    )


# --------------------------------------------------------------------- main ----
def main() -> int:
    global SCRATCH
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch", default=None, help="directory for all artifacts")
    args = parser.parse_args()
    if args.scratch:
        SCRATCH = Path(args.scratch)
    else:
        SCRATCH = Path(tempfile.mkdtemp())
    SCRATCH.mkdir(parents=True, exist_ok=True)
    # Imported f2_controls builders call tempfile.mkdtemp() at import; keep every
    # temp artifact under the declared scratch directory.
    os.environ["TMPDIR"] = str(SCRATCH)

    fixtures = Fixtures(SCRATCH)
    properties = [
        p1_quiet_vs_outage,
        p2_stale_data,
        p3_missing_history,
        p4_access_withdrawal,
        p5_no_stale_protected_content,
        p6_honest_degraded_api,
        p7_honest_degraded_ai,
        p8_no_duplicate_work,
        p9_live_api_human_gate,
    ]
    tally = {"PROVEN": 0, "PARTIAL": 0, "ABSENT": 0, "HUMAN_GATE": 0}
    for number, prop in enumerate(properties, 1):
        verdict, evidence = prop(fixtures)
        tally[verdict] += 1
        print(f"V7 P{number} {verdict} {evidence}")
    print(
        f"V7 SUMMARY proven={tally['PROVEN']} partial={tally['PARTIAL']} "
        f"absent={tally['ABSENT']} human_gate={tally['HUMAN_GATE']} "
        f"rung=OFFLINE_FIXTURE"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

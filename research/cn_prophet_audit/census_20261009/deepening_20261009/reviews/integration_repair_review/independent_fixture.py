#!/usr/bin/env python3
"""Review-owned synthetic scenario executed through unchanged pinned natives.

Only the prior immutable laboratory's three-name armed fixture and synthetic
prices are reused. Quote bytes, native passes, source receipts, compact canonical
board and envelope objects are independently constructed here.
"""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json

SESSION = "2026-10-12"
NOW = datetime(2026, 10, 12, 12, tzinfo=timezone.utc)


def at(hour, minute=0, second=0):
    return datetime(2026, 10, 12, hour, minute, second, tzinfo=timezone.utc)


def payload(pack, prices, quote_at):
    return {"spark": {"result": [
        {"symbol": ticker, "response": [{"meta": {
            "regularMarketPrice": prices[ticker],
            "previousClose": entry["as_of_close"],
            "regularMarketTime": int(quote_at.timestamp()),
            "currency": "CNY",
        }}]}
        for ticker, entry in sorted(pack["names"].items())
    ]}}


def build(B, modules, resolver, prior_fixture):
    LS = modules["engine/prophet_live/live_states.py"]
    CS = modules["engine/prophet_live/cn_states.py"]
    clock = modules["engine/prophet_live/cn_clock.py"]
    R2 = modules["engine/prophet_live/r2io.py"]
    pack = deepcopy(prior_fixture["base_pack"])
    initial = next(doc for doc in prior_fixture["events"].values()
                   if doc["built_at"] == "2026-10-12T02:00:00Z")
    prices = {event["ticker"]: event["price"] for event in initial["events"]}
    cfg = LS.live_cfg({"live": {"delayed_min": 0}})
    canonical = {
        "as_of": SESSION, "board_definition": "cn_prophet_v4",
        "research_fixture": "INDEPENDENT_INTEGRATION_REPAIR_REVIEW_ONLY",
        "buy": [{"ticker": "002460.SZ"}], "more_actionable": [],
        "forming": [{"ticker": "300750.SZ"}], "late_or_unfillable": [],
    }
    canonical_raw = json.dumps(canonical, sort_keys=True, separators=(",", ":"),
                               ensure_ascii=False, allow_nan=False).encode()
    settlement = deepcopy(prior_fixture["settlement_pack"])
    settlement["source_board"]["artifact_sha256"] = sha256(canonical_raw).hexdigest()
    settlement.pop("pack_id")
    settlement["pack_id"] = B.digest(settlement)
    B.validate_pack(pack)
    B.validate_pack(settlement)
    artifacts, payloads, quote_sets, documents = [], {}, {}, {}
    previous = None
    for observed_at, quoted_at in ((at(2), at(2)), (at(2, 5), at(2, 5)),
                                   (at(7, 1), at(7)), (at(7, 6), at(7))):
        raw = json.dumps(payload(pack, prices, quoted_at), sort_keys=True,
                         separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
        quotes = resolver.quotes(raw, recorded_at=observed_at)
        artifact = B.evaluate_checked(CS.evaluate, LS, clock, pack, quotes, previous,
                                      now=observed_at, cfg=cfg, delay_min=0,
                                      quote_resolver=resolver)
        doc = B.envelope(artifact, artifact["events"], pack)
        documents[B.spool_key(doc, R2)] = doc
        label = observed_at.isoformat()
        artifacts.append(artifact)
        payloads[label] = raw.decode()
        quote_sets[label] = quotes
        previous = artifact
    fixture = {
        "schema": "independent_cn_integration_repair_fixture/v1",
        "origin": "EXPLICITLY_SYNTHETIC_REVIEW_ONLY",
        "base_pack": pack, "settlement_pack": settlement,
        "canonical_board": canonical, "canonical_board_utf8": canonical_raw.decode(),
        "events": documents, "quote_payloads_utf8": payloads,
        "quote_contract": deepcopy(resolver.contract),
        "quote_contract_id": resolver.contract_id,
        "prices": prices, "session": SESSION, "settled_at": NOW.isoformat(),
        "limits": [
            "The compact canonical board is newly synthetic and its exact bytes are bound into a separately sealed settlement generation.",
            "Provider-shaped quote bytes are generated here, not received from Yahoo or any vendor.",
            "Native parser, state and reconciliation bodies execute unchanged from their pinned code identities.",
        ],
    }
    return fixture, artifacts, quote_sets, cfg


def store_for(B, R2, fixture):
    store = B.MemoryR2(page_size=2)
    for key, doc in fixture["events"].items():
        store.put(key, doc)
    for name in ("base_pack", "settlement_pack"):
        pack = fixture[name]
        store.put(B.pack_key(pack, R2), pack)
    # Deliberate rollover: the archived armed generation must remain authority.
    store.put(R2.CN_PACK_KEY, fixture["settlement_pack"])
    return store


def ingest(B, modules, resolver, fixture, *, store=None, existing=None,
           settlement=None, canonical=True):
    R2 = modules["engine/prophet_live/r2io.py"]
    return B.consume(store_for(B, R2, fixture) if store is None else store,
        R2, modules["engine/prophet_live/cn_reconcile.py"],
        modules["engine/prophet_live/cn_clock.py"], modules["lib/cn_calendar.py"],
        modules["engine/prophet_live/live_states.py"],
        session=SESSION, now=NOW, existing=[] if existing is None else existing,
        settlement_pack=fixture["settlement_pack"] if settlement is None else settlement,
        canonical_board=fixture["canonical_board"] if canonical else None,
        canonical_board_raw=fixture["canonical_board_utf8"].encode() if canonical else None,
        quote_resolver=resolver)

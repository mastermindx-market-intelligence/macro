"""Bounded bulk adapters with private resumable acquisition and source checks.

Follow the yfinance 1.5.1 calendar protocol and Massive v1 endpoints. Raw
normalization preserves legitimate zero values. Existing authentication is reused.
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import date, timedelta
from typing import Callable
from urllib.parse import urlsplit

from engine.market_calendar.contracts import massive_dividend, yahoo_earning, yahoo_economic

YAHOO_FIELDS = ["ticker", "companyshortname", "intradaymarketcap", "eventname",
                "startdatetime", "startdatetimetype", "epsestimate", "epsactual", "epssurprisepct"]
YAHOO_ECON_FIELDS = ["econ_release", "country_code", "startdatetime", "period",
                     "after_release_actual", "consensus_estimate", "prior_release_actual", "originally_reported_actual"]


class SourceFailure(Exception):
    """Coarse non-secret failure safe for a source health record."""


def yahoo_body(start: str, end: str, offset: int, economic: bool = False) -> dict:
    def op(operator, operands):
        return {"operator": operator, "operands": operands}
    # Overfetch the date boundary, then filter normalized dates. The observed
    # vendor response can include its boundary timestamp despite an LT operand.
    exclusive_end = (date.fromisoformat(end) + timedelta(days=2 if economic else 1)).isoformat()
    if economic:
        return {"sortType": "DESC", "entityIdType": "economic_event", "sortField": "startdatetime",
                "includeFields": YAHOO_ECON_FIELDS, "size": 100, "offset": offset,
                "query": op("AND", [op("GTE", ["startdatetime", start]), op("LT", ["startdatetime", exclusive_end])])}
    return {"sortType": "DESC", "entityIdType": "sp_earnings", "sortField": "intradaymarketcap",
            "includeFields": YAHOO_FIELDS, "size": 100, "offset": offset,
            "query": op("AND", [op("EQ", ["region", "us"]),
                op("OR", [op("EQ", ["eventtype", "EAD"]), op("EQ", ["eventtype", "ERA"])]),
                op("GTE", ["startdatetime", start]), op("LT", ["startdatetime", exclusive_end])])}


def yahoo_page(payload: dict, fields: list[str] = YAHOO_FIELDS) -> tuple[list[dict], int | None]:
    try:
        finance = payload["finance"]
        if finance.get("error"):
            raise SourceFailure("provider_error")
        result = finance["result"][0]
        document = result["documents"][0]
        columns = [col["id"] for col in document["columns"]]
        if len(set(columns)) != len(columns) or not set(fields).issubset(columns):
            raise SourceFailure("schema_changed")
        rows = document["rows"]
        if not isinstance(rows, list) or len(rows) > 100 or any(not isinstance(row, list) or len(row) != len(columns) for row in rows):
            raise SourceFailure("schema_changed")
        total = result.get("total")
        return [dict(zip(columns, row)) for row in rows], total if type(total) is int and total >= 0 else None
    except (KeyError, TypeError, IndexError):
        raise SourceFailure("schema_changed") from None


def _query_key(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def yahoo_earnings(start: str, end: str, observed_at: str, deadline: float,
                   post: Callable | None = None, resume: dict | None = None) -> tuple[list[dict], dict]:
    return _yahoo_calendar(start, end, observed_at, deadline, post, resume=resume)


def yahoo_economics(start: str, end: str, observed_at: str, deadline: float,
                    post: Callable | None = None, resume: dict | None = None) -> tuple[list[dict], dict]:
    return _yahoo_calendar(start, end, observed_at, deadline, post, economic=True, resume=resume)


def _yahoo_calendar(start: str, end: str, observed_at: str, deadline: float,
                    post: Callable | None = None, economic: bool = False,
                    resume: dict | None = None) -> tuple[list[dict], dict]:
    if post is None:
        from yfinance.data import YfData
        post = YfData().post
    query = _query_key(yahoo_body(start, end, 0, economic))
    state = dict(resume) if isinstance(resume, dict) and resume.get("query") == query else {}
    events = list(state.get("events", []))
    hashes, identities = set(state.get("hashes", [])), set(state.get("identities", []))
    offset = int(state.get("offset", 0))
    if not 0 <= offset <= 12000 or len(events) > 12000:
        raise SourceFailure("invalid_progress")
    meta = {"pages": int(state.get("pages", 0)), "expectedRecords": state.get("total"),
            "complete": False, "invalidRecords": 0, "asOf": state.get("asOf") or observed_at}
    first = state.get("first")
    finished = bool(state.get("finished"))
    reset = False
    identity_fields = (("econ_release", "country_code", "startdatetime", "period") if economic
                       else ("ticker", "eventname", "startdatetime", "startdatetimetype"))

    def identity(row):
        return _query_key([row.get(field) for field in identity_fields])

    def fetch(page_offset):
        remaining = deadline - time.monotonic()
        if remaining < 1:
            raise SourceFailure("budget_exhausted")
        response = post("https://query1.finance.yahoo.com/v1/finance/visualization",
                        params={"lang": "en-US", "region": "US"},
                        body=yahoo_body(start, end, page_offset, economic), timeout=min(8, remaining))
        if response.status_code != 200:
            raise SourceFailure("restricted" if response.status_code in (401, 403) else "provider_unavailable")
        return yahoo_page(response.json(), YAHOO_ECON_FIELDS if economic else YAHOO_FIELDS)

    def verify_head():
        rows, total = fetch(0)
        # Earnings order contains a live capitalization value. Compare identities,
        # not volatile EPS/cap values; reject moved ordering or changing totals.
        if total != meta["expectedRecords"] or _query_key([identity(r) for r in rows]) != first:
            raise SourceFailure("source_changed")

    try:
        if offset:
            verify_head()
        if finished:
            meta["complete"] = True
        while not meta["complete"] and not finished and meta["pages"] < 120:
            rows, total = fetch(offset)
            if meta["pages"] and total != meta["expectedRecords"]:
                raise SourceFailure("changing_total")
            fingerprint = _query_key(rows)
            if rows and fingerprint in hashes:
                raise SourceFailure("repeated_page")
            hashes.add(fingerprint)
            if offset == 0:
                first = _query_key([identity(r) for r in rows])
            meta["pages"] += 1
            meta["expectedRecords"] = total
            for row in rows:
                raw_identity = identity(row)
                if raw_identity in identities:
                    meta["invalidRecords"] += 1
                    meta["error"] = "overlapping_pages"
                    continue
                identities.add(raw_identity)
                event = (yahoo_economic if economic else yahoo_earning)(row, observed_at)
                if event and start <= event["date"] <= end:
                    events.append(event)
                elif event is None:
                    meta["invalidRecords"] += 1
            offset += len(rows)
            if meta["invalidRecords"]:
                reset = True
                break
            finished = offset >= total if total is not None else len(rows) < 100
            if not rows and not finished:
                raise SourceFailure("truncated_page")
            if finished:
                if meta["pages"] > 1:
                    verify_head()
                meta["complete"] = True
        if not meta["complete"] and meta["pages"] >= 120:
            raise SourceFailure("record_limit")
    except Exception as exc:
        code = str(exc) if isinstance(exc, SourceFailure) else "provider_unavailable"
        if code == "restricted":
            raise SourceFailure(code) from None
        meta["error"] = code
        reset = code not in {"budget_exhausted", "provider_unavailable"}
    meta["rawRecords"] = offset
    meta["_resume"] = None if meta["complete"] or reset or not offset else {
        "query": query, "events": events, "hashes": sorted(hashes), "identities": sorted(identities),
        "offset": offset, "pages": meta["pages"], "total": meta["expectedRecords"],
        "first": first, "finished": finished, "asOf": meta["asOf"], "lastProgress": observed_at,
    }
    if reset:
        meta["discard"] = True
    return events, meta


def massive_pages(path: str, params: dict, key: str, deadline: float,
                   get: Callable | None = None, resume: dict | None = None,
                   observed_at: str | None = None) -> tuple[list[dict], dict]:
    if get is None:
        import requests
        get = requests.get
    query = _query_key([path, params])
    state = dict(resume) if isinstance(resume, dict) and resume.get("query") == query else {}
    url = state.get("next") or "https://api.massive.com" + path
    rows, seen = list(state.get("rows", [])), set(state.get("seen", []))
    identities = set(state.get("identities", []))
    meta = {"pages": int(state.get("pages", 0)), "complete": False, "expectedRecords": None,
            "asOf": state.get("asOf") or observed_at}
    reset = False
    try:
        while meta["pages"] < 12:
            if time.monotonic() >= deadline - 1:
                raise SourceFailure("budget_exhausted")
            if url in seen:
                raise SourceFailure("repeated_page")
            parsed = urlsplit(url)
            if (parsed.scheme != "https" or parsed.netloc != "api.massive.com" or parsed.path != path
                    or parsed.username or parsed.password or "apikey=" in parsed.query.lower()
                    or "api_key=" in parsed.query.lower()):
                raise SourceFailure("invalid_continuation")
            response = get(url, params=params if meta["pages"] == 0 else None,
                           headers={"Authorization": "Bearer " + key},
                           timeout=min(8, max(1, deadline - time.monotonic())), allow_redirects=False)
            if response.status_code != 200:
                raise SourceFailure("restricted" if response.status_code in (401, 403) else "provider_unavailable")
            payload = response.json()
            batch = payload.get("results")
            if not isinstance(batch, list) or len(batch) > 5000 or any(not isinstance(row, dict) for row in batch):
                raise SourceFailure("schema_changed")
            if len(rows) + len(batch) > 20000:
                raise SourceFailure("record_limit")
            batch_ids = [str(row.get("id") or row.get("ticker")) for row in batch]
            if any(i in identities for i in batch_ids) or len(set(batch_ids)) != len(batch_ids):
                raise SourceFailure("overlapping_pages")
            rows.extend(batch)
            identities.update(batch_ids)
            seen.add(url)
            meta["pages"] += 1
            next_url = payload.get("next_url")
            if not next_url:
                meta["complete"] = True
                break
            if not isinstance(next_url, str) or len(next_url) > 3000:
                raise SourceFailure("invalid_continuation")
            url = next_url
        if not meta["complete"] and meta["pages"] >= 12:
            raise SourceFailure("record_limit")
    except Exception as exc:
        code = str(exc) if isinstance(exc, SourceFailure) else "provider_unavailable"
        if code in {"restricted", "invalid_continuation"}:
            raise SourceFailure(code) from None
        meta["error"] = code
        reset = code not in {"budget_exhausted", "provider_unavailable"}
    meta["_resume"] = None if meta["complete"] or reset or not rows else {
        "query": query, "rows": rows, "seen": sorted(seen), "identities": sorted(identities),
        "next": url, "pages": meta["pages"], "asOf": meta["asOf"], "lastProgress": observed_at,
    }
    if reset:
        meta["discard"] = True
    return rows, meta


def dividends(start: str, end: str, observed_at: str, key: str,
              deadline: float, get: Callable | None = None,
              resume: dict | None = None) -> tuple[list[dict], dict]:
    rows, meta = massive_pages("/stocks/v1/dividends", {"ex_dividend_date.gte": start,
        "ex_dividend_date.lte": end, "limit": 5000, "sort": "ex_dividend_date.asc,ticker.asc"},
        key, deadline, get, resume, observed_at)
    events = [event for row in rows if (event := massive_dividend(row, meta.get("asOf") or observed_at)) is not None]
    meta["invalidRecords"] = len(rows) - len(events)
    if meta["invalidRecords"]:
        meta.update({"complete": False, "_resume": None, "discard": True})
    return events, meta

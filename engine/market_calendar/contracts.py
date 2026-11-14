"""Provider normalization using the shared, API-owned calendar value contract."""
from __future__ import annotations
from datetime import date, datetime, timezone
from app.market_calendar_contracts import (
    SCHEMA, MAX_BYTES, MAX_EVENTS, NY, SYMBOL, number, text, day, stamp,
    source_url, event_id, base_event,
)

def yahoo_earning(row: dict, observed_at: str) -> dict | None:
    symbol = text(row.get("ticker"), 32)
    if not SYMBOL.fullmatch(symbol):
        return None
    raw_date = row.get("startdatetime")
    timestamp = stamp(raw_date)
    # BMO/AMC timestamps are vendor placeholders, NOT exact release times.
    parsed = datetime.fromisoformat(timestamp) if timestamp else None
    # Midnight UTC with a session-only calendar row is a date placeholder.
    # Shifting it to New York would silently move the announced date backward.
    event_day = (parsed.astimezone(NY).date().isoformat()
                 if parsed and (parsed.hour or parsed.minute or parsed.second) else day(raw_date))
    if not event_day:
        return None
    label = text(row.get("eventname"))
    identity = event_id("yahoo", symbol + "|" + (label or event_day))
    event = base_event("earnings", identity, event_day,
                       text(row.get("companyshortname")) or symbol, "yahoo", observed_at, symbol)
    cap = number(row.get("intradaymarketcap"))
    event.update({
        "session": {"BMO": "before_open", "AMC": "after_close", "DMH": "during_market"}.get(
            text(row.get("startdatetimetype")), "unknown"),
        "marketCap": cap if cap is not None and cap >= 0 else None,
        "capCurrency": "USD" if cap is not None and cap >= 0 else None,
        # The acquisition time is not a supplied market-cap timestamp.
        "sourceLabel": label or None,
        "sourceUrl": "https://finance.yahoo.com/calendar/earnings?day=" + event_day,
        "earnings": {"epsEstimate": number(row.get("epsestimate")),
                     "epsActual": number(row.get("epsactual")), "epsBasis": "unspecified",
                     "currency": None, "revenueEstimate": None, "revenueActual": None,
                     "providerSurprisePct": number(row.get("epssurprisepct"))},
    })
    if event["earnings"]["epsActual"] is not None:
        event["status"] = "reported"
    elif event_day < datetime.fromisoformat(observed_at).astimezone(NY).date().isoformat():
        event["status"] = "results_pending"
    return event


def massive_dividend(row: dict, observed_at: str) -> dict | None:
    symbol, event_day = text(row.get("ticker"), 32), day(row.get("ex_dividend_date"))
    if not SYMBOL.fullmatch(symbol) or not event_day:
        return None
    identity = event_id("massive", text(row.get("id"), 160) or
                        f"{symbol}|{event_day}|{row.get('cash_amount')}|{row.get('currency')}")
    event = base_event("dividends", identity, event_day, symbol, "massive", observed_at, symbol)
    currency = text(row.get("currency"), 8) or None  # Case matters: GBP and GBp differ.
    event.update({"sourceUrl": "https://massive.com/docs/rest/stocks/corporate-actions/dividends",
                  "confirmation": "confirmed", "dividend": {
                      "exDate": event_day, "payDate": day(row.get("pay_date")),
                      "recordDate": day(row.get("record_date")),
                      "declarationDate": day(row.get("declaration_date")),
                      "amount": number(row.get("cash_amount")), "currency": currency,
                      "frequency": number(row.get("frequency")),
                      "distributionType": text(row.get("distribution_type"), 30) or "unknown",
                      "yield": None, "yieldAsOf": None,
                  }})
    return event


def yahoo_economic(row: dict, observed_at: str) -> dict | None:
    """Supplemental vendor series; never an official verification or unit inference."""
    name, country = text(row.get("econ_release")), text(row.get("country_code"), 8)
    raw_date = row.get("startdatetime")
    timestamp = stamp(raw_date)
    # Observed asterisk entries use midnight placeholders; conservatively keep
    # the provider date until an exact release time is supplied independently.
    known_time = bool(timestamp) and not name.endswith("*")
    event_day = (datetime.fromisoformat(timestamp).astimezone(NY).date().isoformat()
                 if known_time else day(raw_date))
    if not name or not country or not event_day:
        return None
    period = text(row.get("period"), 80) or None
    identity = event_id("yahoo-economic", f"{country}|{name}|{period}|{event_day}")
    event = base_event("economics", identity, event_day, name, "yahoo-economic", observed_at)
    values = {key: text(row.get(field), 100) or None for key, field in (
        ("actualDisplay", "after_release_actual"), ("consensusDisplay", "consensus_estimate"),
        ("previousDisplay", "prior_release_actual"), ("originallyReportedDisplay", "originally_reported_actual"))}
    event.update({"country": country, "scheduledAt": timestamp if known_time else None,
                  "session": "scheduled_time" if known_time else "unknown",
                  "sourceUrl": "https://finance.yahoo.com/calendar/economic?day=" + event_day,
                  "sourceLabel": "Provider economic series", "economic": {
                      "actual": None, "consensus": None, "previous": None, "unit": None,
                      "period": period, "metrics": [], "headline": None, "headlineZh": None, **values}})
    if values["actualDisplay"] is not None:
        event["status"] = "reported"
    elif event_day < datetime.fromisoformat(observed_at).astimezone(NY).date().isoformat():
        event["status"] = "results_pending"
    return event


def reconcile_events(events: list[dict], previous: list[dict], observed_at: str) -> list[dict]:
    """No date change silently becomes a second event; no missing row means cancelled."""
    previous_by_id = {e["id"]: e for e in previous if isinstance(e, dict) and "id" in e}
    result: dict[str, dict] = {}
    for event in events:
        prior_in_batch = result.get(event["id"])
        if prior_in_batch:
            if event["observedAt"] > prior_in_batch["observedAt"]:
                # A newly fetched week supersedes a retained old week. Conflicts
                # only describe simultaneous observations, not known reschedules.
                event["changes"] = list(prior_in_batch.get("changes", []))[-3:]
                if prior_in_batch["date"] != event["date"]:
                    event["changes"].append({"field": "date", "before": prior_in_batch["date"],
                                             "after": event["date"], "observedAt": observed_at})
                result[event["id"]] = event
                continue
            if event["observedAt"] < prior_in_batch["observedAt"]:
                continue
            if prior_in_batch["date"] != event["date"]:
                prior_in_batch["scheduleConflict"] = True
                prior_in_batch["confirmation"] = "unknown"
                prior_in_batch["alternateDates"] = sorted(set(prior_in_batch["alternateDates"] + [event["date"]]))
            continue
        prior = previous_by_id.get(event["id"])
        if prior:
            event["changes"] = list(prior.get("changes", []))[-3:]
            for field in ("date", "session"):
                if prior.get(field) != event.get(field):
                    event["changes"].append({"field": field, "before": prior.get(field),
                                             "after": event.get(field), "observedAt": observed_at})
            event["changes"] = event["changes"][-4:]
        result[event["id"]] = event
    return list(result.values())

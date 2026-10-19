"""Dated central-bank decisions, independent of monthly policy-rate history.

No rate-minus-inflation stance score is inferred. A decision establishes the
named instrument on its effective date; it does not refresh a different series.
"""
from __future__ import annotations

from calendar import monthrange
from copy import deepcopy
from datetime import date, datetime, time, timezone
from hashlib import sha256
import json
import math
from urllib.parse import urlparse

SCHEMA = "intl_policy_decision.v1"
INSTRUMENTS = {
    ("GB", "bank_rate"): ("Bank of England", "bankofengland.co.uk", "Bank Rate", "英国央行基准利率"),
    ("TW", "discount_rate"): ("Central Bank of the Republic of China (Taiwan)", "cbc.gov.tw", "Discount rate", "贴现率"),
}
MAX_DECISION_AGE_DAYS = 75


def _day(value):
    if type(value) is not str or len(value) != 10:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _time(value):
    if type(value) is not str:
        return None
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return moment.replace(tzinfo=timezone.utc) if moment.tzinfo is None else moment.astimezone(timezone.utc)
    except ValueError:
        return None


def _finite(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value) and -5 <= value <= 100
    except (OverflowError, ValueError):
        return False


def normalize_policy_decision(raw, *, observed_at=None):
    if type(raw) is not dict:
        return None
    cc, instrument = raw.get("cc"), raw.get("instrument")
    if type(cc) is not str or type(instrument) is not str or (cc, instrument) not in INSTRUMENTS:
        return None
    provider, host, en, zh = INSTRUMENTS[(cc, instrument)]
    if raw.get("schema") != SCHEMA or raw.get("provider") != provider or raw.get("unit") != "percent":
        return None
    try:
        url = urlparse(raw.get("source_url", ""))
        if url.scheme != "https" or url.username or url.password or not (url.hostname == host or (url.hostname or "").endswith("." + host)):
            return None
    except (ValueError, TypeError, AttributeError):
        return None
    decision, published, effective = (_day(raw.get(k)) for k in ("decision_date", "published", "effective_date"))
    if None in (decision, published, effective) or published < decision or effective < decision:
        return None
    value, previous = raw.get("value"), raw.get("previous_value")
    if any(not _finite(v) for v in (value, previous)):
        return None
    action = raw.get("action")
    expected = "hold" if value == previous else "increase" if value > previous else "decrease"
    if action != expected:
        return None
    last_change = _day(raw.get("last_change_date")) if raw.get("last_change_date") else None
    if raw.get("last_change_date") and (last_change is None or last_change > effective):
        return None
    if action != "hold" and last_change is not None and last_change != effective:
        return None
    # A hold verifies the existing setting; it does not establish the original
    # rate-change date. That date stays absent without its own source evidence.
    observed = raw.get("first_observed_at") or observed_at or datetime.now(timezone.utc).isoformat()
    if _time(observed) is None or _time(observed).date() < published:
        return None
    source_hash = raw.get("source_sha256")
    if source_hash is not None and (type(source_hash) is not str or len(source_hash) > 128):
        return None
    for key in ("rationale_en", "rationale_zh"):
        if type(raw.get(key)) is not str or not 1 <= len(raw[key]) <= 1200:
            return None
    votes = raw.get("votes")
    if votes is not None:
        if (type(votes) is not dict or set(votes) != {"hold", "increase", "decrease"}
                or any(type(v) is not int or not 0 <= v <= 30 for v in votes.values()) or not 1 <= sum(votes.values()) <= 30):
            return None
    content = {key: deepcopy(raw.get(key)) for key in
               ("cc", "instrument", "provider", "unit", "value", "previous_value", "action",
                "decision_date", "published", "effective_date", "last_change_date",
                "source_url", "rationale_en", "rationale_zh", "votes")}
    digest = sha256(json.dumps(content, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    return {**content, "schema": SCHEMA, "record_id": cc + ":" + instrument + ":" + digest[:24],
            "source_sha256": source_hash, "first_observed_at": observed,
            "instrument_en": en, "instrument_zh": zh, "change_pp": round(value - previous, 6)}


def merge_policy_decisions(previous, incoming, *, observed_at=None):
    now = observed_at or datetime.now(timezone.utc).isoformat()
    rows = {}
    for is_new, source in ((False, previous), (True, incoming)):
        for raw in source if type(source) is list else []:
            candidate = deepcopy(raw) if type(raw) is dict else raw
            if is_new and type(candidate) is dict:
                candidate["first_observed_at"] = now
            record = normalize_policy_decision(candidate, observed_at=now)
            if record and record["record_id"] not in rows:
                rows[record["record_id"]] = record
    if len(rows) > 120:
        raise ValueError("policy_decision_archive_capacity")
    return sorted(rows.values(), key=lambda r: (r["cc"], r["decision_date"], r["record_id"]))


def select_policy_decision(records, cc, *, today=None, monthly=None, operational_as_of=None):
    cutoff = _time(operational_as_of) if operational_as_of is not None else None
    if operational_as_of is not None and cutoff is None:
        raise ValueError("invalid_policy_replay_cutoff")
    today = cutoff.date() if cutoff else today or date.today()
    if type(today) is not date:
        raise ValueError("invalid_policy_evaluation_date")
    knowledge_cutoff = cutoff or min(datetime.now(timezone.utc), datetime.combine(today, time.max, timezone.utc))
    known = []
    for raw in records if type(records) is list else []:
        record = normalize_policy_decision(raw)
        if (record and record["cc"] == cc and _day(record["published"]) <= today
                and _time(record["first_observed_at"]) <= knowledge_cutoff):
            known.append(record)
    if not known:
        return None
    latest_date = max(r["decision_date"] for r in known)
    newest = [r for r in known if r["decision_date"] == latest_date]
    def semantics(row):
        return (row["instrument"], row["value"], row["previous_value"], row["action"],
                row["effective_date"], row["last_change_date"], json.dumps(row["votes"], sort_keys=True),
                row["rationale_en"], row["rationale_zh"])
    conflicting = len({semantics(row) for row in newest}) > 1
    # Resolve versions before filtering by effective date. A contradictory
    # future-effective version is still a known conflict in this announcement.
    effective = [r for r in known if _day(r["effective_date"]) <= today]
    announced = [r for r in newest if _day(r["effective_date"]) > today]
    if conflicting:
        selected = deepcopy(sorted(newest, key=lambda r: r["record_id"])[0])
        state = "conflict"
    elif effective:
        selected = deepcopy(max(effective, key=lambda r: (r["decision_date"], r["record_id"])))
        same_decision = [r for r in effective if r["decision_date"] == selected["decision_date"]]
        conflict = len({semantics(row) for row in same_decision}) > 1
        state = "conflict" if conflict else "verified" if (today - _day(selected["decision_date"])).days <= MAX_DECISION_AGE_DAYS else "dated"
    else:
        selected = deepcopy(sorted(newest, key=lambda r: r["record_id"])[0])
        state = "announced"
    context = None
    if type(monthly) is dict and _finite(monthly.get("value")):
        label = monthly.get("period")
        month_end = None
        if type(label) is str and len(label) == 7:
            try:
                year, month = map(int, label.split("-"))
                month_end = date(year, month, monthrange(year, month)[1])
            except (ValueError, TypeError):
                pass
        observed = _time(monthly.get("first_observed_at"))
        if (month_end is not None and month_end <= today
                and (observed is None or observed <= knowledge_cutoff)
                and (cutoff is None or observed is not None)):
            context = deepcopy(monthly)
    if (context and context.get("instrument") == selected["instrument"]
            and context.get("observation_convention") == "end_of_period"
            and _day(selected["effective_date"]) <= month_end
            and context["value"] != selected["value"]):
        state = "conflict"
    selected["state"] = state
    selected["current"] = state == "verified"
    selected["conflicting_records"] = [r["record_id"] for r in newest] if conflicting else []
    selected["monthly_context"] = context
    selected["announced"] = deepcopy(announced[0]) if announced and not conflicting else None
    return selected

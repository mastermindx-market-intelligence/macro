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
    ("JP", "uncollateralized_overnight_call_rate_target"): ("Bank of Japan", "boj.or.jp", "Overnight call-rate target", "无担保隔夜拆借利率目标"),
    ("KR", "bok_base_rate"): ("Bank of Korea", "bok.or.kr", "BOK Base Rate", "韩国央行基准利率"),
    ("AU", "cash_rate_target"): ("Reserve Bank of Australia", "rba.gov.au", "Cash-rate target", "现金利率目标"),
    ("EZ", "deposit_facility_rate"): ("European Central Bank", "ecb.europa.eu", "Deposit-facility rate", "存款便利利率"),
    ("IN", "policy_repo_rate"): ("Reserve Bank of India", "rbi.org.in", "Policy repo rate · LAF", "流动性调节机制政策回购利率"),
}
APPROXIMATE_TARGETS = {("JP", "uncollateralized_overnight_call_rate_target")}
REQUIRED_SUPPORT = {
    "JP": {"previous_value"}, "KR": {"previous_value", "effective_date"},
    "AU": {"previous_value", "effective_date"}, "EZ": {"previous_value", "votes"},
    "IN": {"previous_value", "effective_date"},
}
SUPPORT_LABELS = {
    "rate_history": ("Rate history", "利率记录"),
    "implementation": ("Implementation notice", "生效通知"),
    "decision_reference": ("Decision reference", "决定参考资料"),
    "policy_discussion": ("Policy discussion", "政策讨论"),
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


def _official_url(value, host):
    try:
        url = urlparse(value)
        return (url.scheme == "https" and not url.username and not url.password
                and (url.hostname == host or (url.hostname or "").endswith("." + host)))
    except (ValueError, TypeError, AttributeError):
        return False


def _supporting_sources(raw, *, cc, host, observed):
    items = raw.get("supporting_sources", [])
    if type(items) is not list or len(items) > 3:
        return None
    result, urls, covered = [], set(), set()
    for item in items:
        if type(item) is not dict:
            return None
        url, roles, label = item.get("source_url"), item.get("roles"), item.get("label")
        digest, retrieved = item.get("source_sha256"), item.get("retrieved_at")
        if (not _official_url(url, host) or url in urls
                or type(roles) is not list or not roles or len(roles) > 3
                or any(type(role) is not str for role in roles)
                or len(set(roles)) != len(roles)
                or not set(roles) <= {"previous_value", "effective_date", "votes"}
                or type(label) is not str or label not in SUPPORT_LABELS
                or type(digest) is not str or len(digest) != 64
                or any(ch not in "0123456789abcdef" for ch in digest)
                or _time(retrieved) is None or _time(retrieved) > _time(observed)):
            return None
        urls.add(url)
        covered.update(roles)
        en, zh = SUPPORT_LABELS[label]
        result.append({"source_url": url, "roles": sorted(roles), "label": label,
                       "label_en": en, "label_zh": zh, "source_sha256": digest,
                       "retrieved_at": retrieved})
    if not REQUIRED_SUPPORT.get(cc, set()) <= covered:
        return None
    return sorted(result, key=lambda item: item["source_url"])


def normalize_policy_decision(raw, *, observed_at=None):
    if type(raw) is not dict:
        return None
    cc, instrument = raw.get("cc"), raw.get("instrument")
    if type(cc) is not str or type(instrument) is not str or (cc, instrument) not in INSTRUMENTS:
        return None
    provider, host, en, zh = INSTRUMENTS[(cc, instrument)]
    if raw.get("schema") != SCHEMA or raw.get("provider") != provider or raw.get("unit") != "percent":
        return None
    if not _official_url(raw.get("source_url", ""), host):
        return None
    approximate = (cc, instrument) in APPROXIMATE_TARGETS
    if raw.get("setting_qualifier") != ("around" if approximate else None):
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
    supporting = _supporting_sources(raw, cc=cc, host=host, observed=observed)
    if supporting is None:
        return None
    source_hash = raw.get("source_sha256")
    if source_hash is not None and (type(source_hash) is not str or len(source_hash) > 128):
        return None
    if cc in REQUIRED_SUPPORT and (type(source_hash) is not str or len(source_hash) != 64
                                  or any(ch not in "0123456789abcdef" for ch in source_hash)):
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
    # New semantic fields are conditional so existing GB/TW identities survive.
    if approximate:
        content["setting_qualifier"] = "around"
    if supporting:
        content["supporting_sources"] = [
            {key: item[key] for key in ("source_url", "roles", "label")} for item in supporting]
    digest = sha256(json.dumps(content, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    result = {**content, "schema": SCHEMA, "record_id": cc + ":" + instrument + ":" + digest[:24],
              "source_sha256": source_hash, "first_observed_at": observed,
              "instrument_en": en, "instrument_zh": zh, "change_pp": round(value - previous, 6)}
    if supporting:
        result["supporting_sources"] = supporting
    if approximate:
        result.update(setting_qualifier_en="Around", setting_qualifier_zh="约")
    return result


def merge_policy_decisions(previous, incoming, *, observed_at=None, preserve_custody=False):
    now = observed_at or datetime.now(timezone.utc).isoformat()
    rows = {}
    for is_new, source in ((False, previous), (True, incoming)):
        for raw in source if type(source) is list else []:
            candidate = deepcopy(raw) if type(raw) is dict else raw
            if is_new and type(candidate) is dict and not preserve_custody:
                candidate["first_observed_at"] = now
            record = normalize_policy_decision(candidate, observed_at=now)
            if record:
                previous_record = rows.get(record["record_id"])
                if (previous_record is None or (preserve_custody and
                        _time(record["first_observed_at"]) < _time(previous_record["first_observed_at"]))):
                    # Reconstruction chooses one complete custody record. Never
                    # combine an earlier timestamp with later document receipts.
                    rows[record["record_id"]] = record
    if len(rows) > 120:
        raise ValueError("policy_decision_archive_capacity")
    return sorted(rows.values(), key=lambda r: (r["cc"], r["decision_date"], r["record_id"]))


def select_policy_decision(records, cc, *, today=None, monthly=None, operational_as_of=None, review_events=None):
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
        review = _current_policy_review(review_events, cc, knowledge_cutoff)
        if not review:
            return None
        _, _, instrument_en, instrument_zh = INSTRUMENTS[(cc, review["instrument"])]
        # Expose a qualification gap even on the first acquisition. This is a
        # view state, with no invented accepted record, rate or rationale.
        return {**{key: review[key] for key in ("cc", "instrument", "provider",
                    "source_url", "decision_date", "published")},
                "schema": "intl_policy_review_view.v1", "record_id": None,
                "instrument_en": instrument_en, "instrument_zh": instrument_zh,
                "state": "review_required", "current": False, "review": review,
                "has_accepted_decision": False, "announced": None,
                "monthly_context": None, "conflicting_records": []}
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
            and context.get("setting_qualifier") == selected.get("setting_qualifier")
            and _day(selected["effective_date"]) <= month_end
            and context["value"] != selected["value"]):
        state = "conflict"
    review = _current_policy_review(review_events, cc, knowledge_cutoff, record=selected)
    needs_review = review and (review["status"] == "review_required"
                              or review["record_id"] != selected["record_id"])
    newer_review = _current_policy_review(review_events, cc, knowledge_cutoff, after=selected)
    if newer_review and (newer_review["status"] == "review_required"
            or newer_review["record_id"] not in {record["record_id"] for record in known}):
        # A newly encountered but unqualified decision prevents a current-rate
        # claim. A verified future announcement cannot restore the old source.
        if not needs_review:
            review = newer_review
        needs_review = True
    if needs_review and state != "conflict":
        state = "review_required"
    next_decision = deepcopy(sorted(announced, key=lambda r: r["record_id"])[0]) if announced and not conflicting else None
    if next_decision:
        next_review = _current_policy_review(review_events, cc, knowledge_cutoff, record=next_decision)
        next_needs_review = next_review and (next_review["status"] == "review_required"
                                             or next_review["record_id"] != next_decision["record_id"])
        next_decision.update(review=next_review, current=False,
                             state="review_required" if next_needs_review else "announced")
    selected["review"] = review
    selected["state"] = state
    selected["current"] = state == "verified"
    selected["conflicting_records"] = [r["record_id"] for r in newest] if conflicting else []
    selected["monthly_context"] = context
    selected["announced"] = next_decision
    return selected



def normalize_policy_review(raw, *, observed_at=None):
    """A dated qualification event; never a replacement for a rate decision."""
    if type(raw) is not dict or raw.get("schema") != "intl_policy_review.v1":
        return None
    cc, instrument = raw.get("cc"), raw.get("instrument")
    if type(cc) is not str or type(instrument) is not str or (cc, instrument) not in INSTRUMENTS:
        return None
    provider, host, _, _ = INSTRUMENTS[(cc, instrument)]
    observed = observed_at or raw.get("observed_at")
    decision, published = _day(raw.get("decision_date")), _day(raw.get("published"))
    status, record_id, digest = raw.get("status"), raw.get("record_id"), raw.get("source_sha256")
    if (raw.get("provider") != provider or not _official_url(raw.get("source_url"), host)
            or _time(observed) is None or decision is None or published is None
            or published < decision or published > _time(observed).date()
            or status not in ("verified", "review_required")
            or type(digest) is not str or len(digest) != 64
            or any(ch not in "0123456789abcdef" for ch in digest)):
        return None
    prefix = cc + ":" + instrument + ":"
    if status == "verified":
        if (type(record_id) is not str or not record_id.startswith(prefix)
                or len(record_id) != len(prefix) + 24
                or any(ch not in "0123456789abcdef" for ch in record_id[len(prefix):])):
            return None
    elif record_id is not None:
        return None
    content = {"schema": "intl_policy_review.v1", "cc": cc, "instrument": instrument,
               "provider": provider, "source_url": raw["source_url"],
               "decision_date": decision.isoformat(), "published": published.isoformat(),
               "observed_at": _time(observed).isoformat(),
               "status": status, "record_id": record_id, "source_sha256": digest}
    event_id = sha256(json.dumps(content, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]
    return {**content, "event_id": cc + ":policy_review:" + event_id}


def merge_policy_reviews(previous, incoming, *, observed_at=None, preserve_custody=False):
    now = observed_at or datetime.now(timezone.utc).isoformat()
    events = {}
    for is_new, items in ((False, previous), (True, incoming)):
        for raw in items if type(items) is list else []:
            event = normalize_policy_review(raw, observed_at=now if is_new and not preserve_custody else None)
            if event:
                events[event["event_id"]] = event
    groups = {}
    for event in events.values():
        identity = tuple(event[k] for k in ("cc", "instrument", "source_url", "decision_date"))
        groups.setdefault(identity, []).append(event)
    result = []
    for group in groups.values():
        prior_state = None
        # At the same instant, failed qualification takes precedence over success.
        for event in sorted(group, key=lambda e: (_time(e["observed_at"]), e["status"] == "review_required", e["event_id"])):
            state = event["status"], event["record_id"]
            if state != prior_state:
                result.append(event)
                prior_state = state
    if len(result) > 240:
        raise ValueError("policy_review_archive_capacity")
    return sorted(result, key=lambda e: (e["cc"], e["observed_at"], e["event_id"]))


def _current_policy_review(events, cc, knowledge_cutoff, *, record=None, after=None):
    known = []
    for raw in events if type(events) is list else []:
        event = normalize_policy_review(raw)
        if not event or event["cc"] != cc or _time(event["observed_at"]) > knowledge_cutoff:
            continue
        if record and any(event[key] != record[key] for key in
                          ("instrument", "decision_date", "source_url")):
            continue
        if after and (event["instrument"] != after["instrument"]
                      or event["decision_date"] <= after["decision_date"]):
            continue
        known.append(event)
    if not known:
        return None
    # Qualification belongs to a specific announcement document. Later decisions
    # and alternative release URLs never requalify this document implicitly.
    return max(known, key=lambda e: (e["decision_date"], _time(e["observed_at"]),
                                     e["status"] == "review_required", e["event_id"]))

"""Versioned country outlooks: publication identity, periods, and honest revisions.

This is an input/view helper owned by the existing International collector. It
does not publish, fetch, score countries, or turn reconstructed history into a
real-time backtest. Prior accepted releases survive partial refreshes.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
import math
import re
from urllib.parse import urlparse

PUBLICATION_SCHEMA = "intl_forecast_publication.v1"
COUNTRIES = frozenset(("JP", "KR", "TW", "IN", "AU", "GB", "EZ", "WORLD"))
SERIES = {
    "real_gdp_growth": ("percent", -100, 100),
    "inflation_average": ("percent", -100, 10000),
    "current_account": ("percent_gdp", -1000, 1000),
    "fiscal_balance": ("percent_gdp", -1000, 1000),
    "government_debt": ("percent_gdp", 0, 2000),
}
PROVIDERS = {"IMF": (("imf.org",), 0), "DGBAS": (("stat.gov.tw", "dgbas.gov.tw"), 1), "CBC": (("cbc.gov.tw",), 1)}
MAX_ARCHIVE_RECORDS = 700
MAX_FORECAST_AGE_DAYS = 270


def _day(value):
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _time(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _number(value):
    if type(value) not in (int, float):
        return None
    try:
        return float(value) if math.isfinite(value) else None
    except (OverflowError, ValueError):
        return None


def _source(value, provider):
    if not isinstance(value, str) or provider not in PROVIDERS:
        return False
    try:
        url = urlparse(value)
        host = url.hostname or ""
        allowed = PROVIDERS[provider][0]
        return (url.scheme == "https" and not url.username and not url.password
                and any(host == domain or host.endswith("." + domain) for domain in allowed))
    except ValueError:
        return False


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def period(year, *, fiscal_start_month=1):
    """A source year is the start year, including India's April--March year."""
    if type(year) is not int or not 1980 <= year <= 2150:
        raise ValueError("invalid_forecast_year")
    if type(fiscal_start_month) is not int or not 1 <= fiscal_start_month <= 12:
        raise ValueError("invalid_fiscal_start_month")
    start = date(year, fiscal_start_month, 1)
    end = date(year, 12, 31) if fiscal_start_month == 1 else date(year + 1, fiscal_start_month, 1) - timedelta(days=1)
    return {"year": year, "label": str(year) if fiscal_start_month == 1 else f"FY{year}/{str(year + 1)[2:]}",
            "start": start.isoformat(), "end": end.isoformat()}


def normalize_publication(raw, *, observed_at=None):
    """Admit only defined public series. Unknown/malformed data remain absent.

    Old GDP snapshots migrate without changing their source values. A legacy
    unkeyed revision is bound to its publication year, never today's year.
    """
    if type(raw) is not dict:
        return None
    cc, provider = raw.get("cc"), raw.get("provider")
    series = raw.get("series_id", "real_gdp_growth")
    published = _day(raw.get("published"))
    if (not all(isinstance(x, str) for x in (cc, provider, series))
            or cc not in COUNTRIES or provider not in PROVIDERS or series not in SERIES
            or published is None or not _source(raw.get("source_url"), provider)
            or raw.get("kind") != "sourced_forecast"):
        return None
    unit, lower, upper = SERIES[series]
    if raw.get("unit") != unit:
        return None
    basis = raw.get("period_basis")
    if basis not in ("calendar_year", "fiscal_year"):
        return None
    month = raw.get("fiscal_start_month", 4 if cc == "IN" and basis == "fiscal_year" else 1)
    if (type(month) is not int or not 1 <= month <= 12
            or (basis == "calendar_year") != (month == 1)):
        return None
    family = raw.get("family", "WEO" if provider == "IMF" else "National accounts")
    edition = raw.get("edition", published.strftime("%Y-%m") if provider == "IMF" else published.isoformat())
    if not all(isinstance(x, str) and 0 < len(x) <= 100 for x in (family, edition)):
        return None
    cutoff = raw.get("information_cutoff")
    if cutoff is not None and (_day(cutoff) is None or _day(cutoff) > published):
        return None
    values = raw.get("values")
    if type(values) is not dict or not 1 <= len(values) <= 30:
        return None
    actual_through = raw.get("actual_through")
    if actual_through is not None and (type(actual_through) is not int or not 0 <= actual_through <= published.year):
        return None
    if any(type(key) is not str or not re.fullmatch(r"(19|20|21)\d{2}", key)
           or not 1980 <= int(key) <= 2150 for key in values):
        return None
    points = []
    source_periods = raw.get("periods", [])
    if type(source_periods) is not list:
        return None
    supplied = {str(p.get("year")): p for p in source_periods if type(p) is dict}
    for key, value in sorted(values.items()):
        if type(key) is not str or not re.fullmatch(r"(19|20|21)\d{2}", key):
            return None
        value = _number(value)
        if value is None or not lower <= value <= upper:
            return None
        p = period(int(key), fiscal_start_month=month)
        existing = supplied.get(key, {})
        if any(existing.get(k, p[k]) != p[k] for k in ("start", "end", "label")):
            return None
        p["value"] = value
        # "Past year" is not an actual unless the source documents that status.
        status = ("actual" if actual_through and p["year"] <= actual_through else
                  "projection" if _day(p["end"]) >= published else
                  "historical_unclassified" if actual_through is None else "estimate")
        if existing.get("status", status) != status:
            return None
        p["status"] = status
        points.append(p)
    now = observed_at or datetime.now(timezone.utc).isoformat()
    retrieved = raw.get("retrieved_at") or now
    first = raw.get("first_observed_at") or retrieved
    admitted = raw.get("admitted_at") or now
    if any(_time(x) is None for x in (retrieved, first, admitted)):
        return None
    if _time(first) > _time(admitted):
        return None
    precision = raw.get("precision", 1 if provider == "IMF" else 2)
    if type(precision) is not int or not 0 <= precision <= 4:
        return None
    definition = raw.get("definition_id", series + ":" + unit + ":" + basis)
    if not isinstance(definition, str) or not 0 < len(definition) <= 200:
        return None
    revisions = {}
    supplied_revisions = raw.get("reported_revisions", {})
    if type(supplied_revisions) is not dict:
        return None
    supplied_revisions = deepcopy(supplied_revisions)
    legacy_delta, legacy_from = _number(raw.get("revision_current_pp")), raw.get("revision_from")
    if legacy_delta is not None:
        supplied_revisions.setdefault(str(published.year), {"delta_pp": legacy_delta, "prior_edition": legacy_from,
                                                           "method": "provider_reported"})
    for target, entry in supplied_revisions.items():
        if type(target) is not str or target not in values or type(entry) is not dict:
            return None
        prior = entry.get("prior_edition")
        delta = _number(entry.get("delta_pp"))
        if (not isinstance(prior, str) or not re.fullmatch(r"\d{4}-\d{2}(?:-\d{2})?", prior)
                or _day(prior + "-01" if len(prior) == 7 else prior) is None
                or _day(prior + "-01" if len(prior) == 7 else prior) >= published
                or delta is None or abs(delta) > 200):
            return None
        revisions[target] = {"delta_pp": delta, "prior_edition": prior, "method": "provider_reported"}
    sequence = raw.get("correction_sequence", 0)
    if type(sequence) is not int or not 0 <= sequence <= 99:
        return None
    for event in ("withdrawn_at", "withdrawal_admitted_at", "superseded_at"):
        if raw.get(event) is not None and _time(raw[event]) is None:
            return None

    # Optional provenance is still untrusted input. Validate it before hashing
    # or serializing so one malformed source cannot abort unrelated countries.
    for key, limit in (("coverage_note", 2000), ("coverage_note_zh", 2000), ("parser_version", 100),
                       ("source_table", 100), ("source_sha256", 128),
                       ("source_row_sha256", 128), ("supersedes_record_id", 200)):
        if raw.get(key) is not None and (not isinstance(raw[key], str) or len(raw[key]) > limit):
            return None
    if raw.get("source_page") is not None and (type(raw["source_page"]) is not int or not 1 <= raw["source_page"] <= 2000):
        return None
    for key in ("dataset_url", "documentation_url", "correction_source_url", "withdrawal_source_url"):
        if raw.get(key) is not None and not _source(raw[key], provider):
            return None

    semantic = {"cc": cc, "provider": provider, "family": family, "edition": edition,
                "published": published.isoformat(), "series_id": series, "unit": unit,
                "period_basis": basis, "fiscal_start_month": month,
                "definition_id": definition, "periods": points,
                "information_cutoff": cutoff, "actual_through": actual_through,
                "reported_revisions": revisions, "precision": precision,
                "coverage_note": raw.get("coverage_note")}
    if raw.get("coverage_note_zh") is not None:
        semantic["coverage_note_zh"] = raw["coverage_note_zh"]
    identity = _digest({k: semantic[k] for k in ("cc", "provider", "family", "edition", "series_id")})[:20]
    normalized_hash = _digest(semantic)
    result = {**semantic, "schema": PUBLICATION_SCHEMA, "kind": "sourced_forecast",
              "publication_key": identity, "record_id": identity + ":" + normalized_hash[:20] + ":" + str(sequence),
              "normalized_sha256": normalized_hash, "values": {str(p["year"]): p["value"] for p in points},
              "source_url": raw["source_url"], "dataset_url": raw.get("dataset_url"),
              "source_sha256": raw.get("source_sha256"),
              "parser_version": raw.get("parser_version", "legacy_gdp_v1"),
              "source_table": raw.get("source_table"), "source_page": raw.get("source_page"),
              "source_row_sha256": raw.get("source_row_sha256"), "documentation_url": raw.get("documentation_url"),
              "coverage_note": raw.get("coverage_note"), "precision": precision,
              "retrieved_at": retrieved, "first_observed_at": first, "admitted_at": admitted,
              "admission_status": "accepted", "correction_sequence": sequence}
    for key in ("correction_sequence", "supersedes_record_id", "withdrawn_at", "superseded_at",
                "admission_status", "correction_source_url", "withdrawal_source_url", "withdrawal_admitted_at"):
        if key in raw:
            result[key] = deepcopy(raw[key])
    if type(result["correction_sequence"]) is not int or result["correction_sequence"] < 0:
        return None
    if result["admission_status"] not in ("accepted", "conflict"):
        return None
    return result


def merge_publications(previous, incoming, *, observed_at=None):
    """Stable content plus explicitly ordered admission and withdrawal events."""
    now = observed_at or datetime.now(timezone.utc).isoformat()
    if _time(now) is None:
        raise ValueError("invalid_forecast_custody_clock")
    archive, diagnostics, lookup = [], [], {}
    # Existing archive custody is trusted; incoming publication metadata cannot
    # backdate first observation/admission for previously unseen content.
    for raw in previous if type(previous) is list else []:
        record = normalize_publication(raw, observed_at=now)
        if record is None:
            diagnostics.append({"kind": "invalid_archived_publication"})
            continue
        if record["record_id"] not in lookup:
            archive.append(record)
            lookup[record["record_id"]] = record
    pending = {}
    for raw in incoming if type(incoming) is list else []:
        record = normalize_publication(raw, observed_at=now)
        if record is None:
            diagnostics.append({"kind": "invalid_publication"})
            continue
        known = lookup.get(record["record_id"])
        if known is None and record["correction_sequence"] == 0 and not record.get("supersedes_record_id"):
            # A stateless source refresh can repeat a previously corrected
            # publication. Bind only identical content to its real latest
            # accepted identity; never create a sequence-zero alias or rebase a
            # withdrawal/correction onto different or superseded content.
            accepted = [r for r in archive if r["publication_key"] == record["publication_key"]
                        and r["admission_status"] == "accepted"]
            latest = max(accepted, key=lambda r: r["correction_sequence"]) if accepted else None
            if latest is not None and latest["normalized_sha256"] == record["normalized_sha256"]:
                known = latest
        if known:
            # A withdrawal is an event, even when the underlying numbers match.
            if record.get("withdrawn_at") and not known.get("withdrawn_at"):
                event = _time(record["withdrawn_at"])
                if (event and _time(known["published"]) <= event <= _time(now)
                        and _source(record.get("withdrawal_source_url"), record["provider"])):
                    known["withdrawn_at"] = record["withdrawn_at"]
                    known["withdrawal_source_url"] = record["withdrawal_source_url"]
                    known["withdrawal_admitted_at"] = now
                else:
                    diagnostics.append({"kind": "invalid_withdrawal", "record_id": record["record_id"]})
            continue
        record["first_observed_at"] = now
        record["admitted_at"] = now
        # Future/lifecycle fields from untrusted incoming records cannot erase
        # other records. Valid supersession is established below.
        record.pop("superseded_at", None)
        if record.get("withdrawn_at"):
            if (not _source(record.get("withdrawal_source_url"), record["provider"])
                    or not _time(record["published"]) <= _time(record["withdrawn_at"]) <= _time(now)):
                diagnostics.append({"kind": "invalid_withdrawal", "record_id": record["record_id"]})
                continue
            record["withdrawal_admitted_at"] = now
        pending[record["record_id"]] = record
    groups = {}
    for record in pending.values():
        groups.setdefault((record["publication_key"], record["correction_sequence"]), []).append(record)
    for (key, sequence), records in sorted(groups.items(), key=lambda item: (item[0][1], item[0][0])):
        accepted = [r for r in archive if r["publication_key"] == key and r["admission_status"] == "accepted"]
        prior = max(accepted, key=lambda r: r["correction_sequence"]) if accepted else None
        ambiguous = len(records) > 1
        for record in sorted(records, key=lambda r: r["record_id"]):
            predecessor = lookup.get(record.get("supersedes_record_id"))
            ordered = (sequence > 0 and predecessor is not None
                       and predecessor["publication_key"] == key
                       and sequence > predecessor["correction_sequence"]
                       and _source(record.get("correction_source_url"), record["provider"])
                       and (prior is None or predecessor["record_id"] == prior["record_id"]))
            accepted_new = not ambiguous and (ordered or (prior is None and sequence == 0))
            record["admission_status"] = "accepted" if accepted_new else "conflict"
            if accepted_new and ordered:
                predecessor["superseded_at"] = now
            if not accepted_new:
                diagnostics.append({"kind": "publication_conflict", "cc": record["cc"],
                                    "series_id": record["series_id"], "edition": record["edition"],
                                    "retained_record_id": prior["record_id"] if prior else None,
                                    "candidate_record_id": record["record_id"]})
            archive.append(record)
            lookup[record["record_id"]] = record
    if len(archive) > MAX_ARCHIVE_RECORDS:
        raise ValueError("forecast_archive_capacity")
    archive.sort(key=lambda r: (r["published"], r["cc"], r["series_id"], r["correction_sequence"], r["record_id"]))
    return archive, diagnostics


def _evaluation(today, operational_as_of):
    if operational_as_of is not None:
        clock = _time(operational_as_of)
        if clock is None:
            raise ValueError("invalid_operational_replay_cutoff")
        return clock.date(), clock
    day = today or date.today()
    return day, datetime.combine(day, datetime.max.time(), timezone.utc)


def _event_applies(record, clock):
    for key in ("withdrawal_admitted_at", "superseded_at"):
        event = _time(record.get(key))
        if event is not None and event <= clock:
            return True
    return False


def _eligible(record, today, *, operational_as_of=None):
    today, clock = _evaluation(today, operational_as_of)
    published = _day(record.get("published"))
    if (record.get("admission_status") != "accepted" or published is None
            or not 0 <= (today - published).days <= MAX_FORECAST_AGE_DAYS):
        return False
    if any(_time(record.get(k)) is None or _time(record[k]) > clock
           for k in ("first_observed_at", "admitted_at")) or _event_applies(record, clock):
        return False
    active_year = today.year - (today.month < record["fiscal_start_month"])
    return any(p["year"] in (active_year, active_year + 1) for p in record["periods"])


def select_publications(archive, cc, series_id="real_gdp_growth", *, today=None, operational_as_of=None):
    today, _ = _evaluation(today, operational_as_of)
    candidates = [r for r in archive if r["cc"] == cc and r["series_id"] == series_id
                  and _eligible(r, today, operational_as_of=operational_as_of)]
    # Most recently published; an explicit provider preference resolves date ties.
    return sorted(candidates, key=lambda r: (-_day(r["published"]).toordinal(),
                  PROVIDERS[r["provider"]][1], -r["correction_sequence"], r["record_id"]))


def revision_for(record, point, archive, *, operational_as_of=None):
    """Same provider, family, definition and exact target period only."""
    candidates = []
    as_of = _time(operational_as_of) if operational_as_of is not None else None
    for other in archive:
        if (other["admission_status"] != "accepted" or other["published"] >= record["published"]
                or any(other[k] != record[k] for k in ("cc", "provider", "family", "series_id",
                       "unit", "definition_id", "period_basis", "fiscal_start_month"))):
            continue
        if operational_as_of is not None and (as_of is None or any(_time(other.get(k)) is None or _time(other[k]) > as_of for k in ("first_observed_at", "admitted_at"))):
            continue
        if _event_applies(other, as_of or datetime.now(timezone.utc)):
            continue
        matching = next((p for p in other["periods"] if p["start"] == point["start"] and p["end"] == point["end"]), None)
        if matching:
            candidates.append((other, matching))
    if candidates:
        prior, old = max(candidates, key=lambda pair: (pair[0]["published"], pair[0]["correction_sequence"]))
        return {"target_label": point["label"], "target_year": point["year"],
                "delta_pp": round(point["value"] - old["value"], min(record["precision"], prior["precision"])),
                "prior_value": old["value"], "prior_edition": prior["edition"],
                "prior_published": prior["published"], "prior_record_id": prior["record_id"],
                "new_record_id": record["record_id"], "method": "calculated_from_published_values"}
    reported = record.get("reported_revisions", {}).get(str(point["year"]))
    if type(reported) is dict and _number(reported.get("delta_pp")) is not None and reported.get("prior_edition"):
        return {"target_label": point["label"], "target_year": point["year"],
                "delta_pp": reported["delta_pp"], "prior_edition": reported["prior_edition"],
                "new_record_id": record["record_id"], "method": "provider_reported"}
    return None


def publication_view(record, archive, *, today=None, operational_as_of=None):
    today, _ = _evaluation(today, operational_as_of)
    active_year = today.year - (today.month < record["fiscal_start_month"])
    relevant = [p for p in record["periods"] if p["year"] in (active_year, active_year + 1)]
    if not relevant:
        return None
    first = relevant[0]
    second = next((p for p in relevant[1:] if p["year"] == first["year"] + 1), None)
    revision = revision_for(record, first, archive, operational_as_of=operational_as_of)
    previous = next((p for p in record["periods"] if p["year"] == first["year"] - 1), None)
    return {**deepcopy(record), "year": first["year"], "year_label": first["label"],
            "next_year": second["year"] if second else None, "next_label": second["label"] if second else None,
            "current": first["value"], "next": second["value"] if second else None,
            "previous": previous["value"] if previous else None,
            "current_period": first, "next_period": second,
            "change": round(second["value"] - first["value"], record["precision"]) if second else None,
            "revision": revision["delta_pp"] if revision else None,
            "revision_from": revision["prior_edition"] if revision else None, "revision_detail": revision,
            "revisions": {str(p["year"]): revision_for(record, p, archive, operational_as_of=operational_as_of)
                          for p in relevant[:2]},
            "is_active_period": _day(first["start"]) <= today,
            "coverage": "two_periods" if second else "one_period"}

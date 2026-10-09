"""Display-only reader of Macro's nested sovereign auction context.

No producer execution, network, cache, risk/decision imports, score or freshness
policy. validate_context is pure and clock-injectable. The page request reads the
existing producer artifact afresh; absence is the production OFF boundary.
"""
from __future__ import annotations

import copy
import json
import re
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from http.client import HTTPS_PORT
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

SCHEMA = "sovereign_auction_context_v1"
FEED_PATH = Path(__file__).resolve().parent.parent / "vendor/macro/site/feeds/event_calendar.json"
MAX_FEED_BYTES = 32 * 1024 * 1024
MAX_EVENTS = 2048
_OFFICIAL_HOSTS = frozenset({"treasurydirect.gov", "www.treasurydirect.gov", "fiscaldata.treasury.gov",
                             "home.treasury.gov", "treasury.gov", "www.treasury.gov"})
_CLOCK = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})\Z")
_RESULT_EVIDENCE_FIELDS = frozenset({"pdfFilenameCompetitiveResults", "xmlFilenameCompetitiveResults", "competitiveAccepted",
    "competitiveTendered", "bidToCoverRatio", "highYield", "highDiscountRate", "highDiscountMargin"})
_RESULT_FIELDS = ("competitive_accepted_usd", "competitive_tendered_usd", "total_accepted_usd",
                  "primary_dealer_accepted_usd", "direct_bidder_accepted_usd", "indirect_bidder_accepted_usd",
                  "bid_to_cover_ratio", "high_discount_rate_pct", "high_discount_margin_pct",
                  "frn_spread_pct", "real_yield_pct", "nominal_yield_pct")
_ROW_TEXT = ("episode_id", "label", "normalized_class", "announced_cusip", "issued_cusip",
             "security_term", "source_state", "physical_state", "issue_calendar_state", "time_et",
             "competitive_deadline_raw", "known_at_basis", "first_observed_at_basis", "source_kind", "schema_id",
             "payload_sha256", "row_sha256", "deadline_timezone")
_HEALTH_TEXT = ("source_kind", "latest_attempt_status", "freshness_basis")
_HEALTH_CLOCKS = ("latest_attempt_at", "last_successful_body_receipt_at", "last_valid_observation_at", "latest_failure_at")
_COVERAGE_DATES = ("upcoming_start_date", "upcoming_end_date_inclusive", "recent_start_date_inclusive")
_COVERAGE_COUNTS = ("known_upcoming_count", "recently_resulted_or_issue_future_count", "unresolved_tentative_count",
                    "awaiting_result_count", "excluded_after_as_of_count", "holiday_nodes_skipped")


class InvalidContext(ValueError):
    """Unsupported or unsafe context must fail closed to an unavailable display."""


def _clock(value, name: str) -> datetime:
    if isinstance(value, str):
        if not _CLOCK.fullmatch(value):
            raise InvalidContext(f"invalid_clock:{name}")
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise InvalidContext(f"invalid_clock:{name}") from exc
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise InvalidContext(f"invalid_clock:{name}")
    return value.astimezone(timezone.utc)


def _text(value, name: str, *, nullable=False):
    if value is None and nullable:
        return None
    if not isinstance(value, str) or len(value) > 4096:
        raise InvalidContext(f"invalid_text:{name}")
    return value


def _texts(value, name: str) -> list:
    if not isinstance(value, list) or len(value) > MAX_EVENTS:
        raise InvalidContext(f"invalid_list:{name}")
    return [_text(item, name) for item in value]


def _day(value, name: str, *, nullable=False):
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise InvalidContext(f"invalid_date:{name}")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise InvalidContext(f"invalid_date:{name}") from exc
    return value


def _number(value, name: str, *, nonnegative=False):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise InvalidContext(f"invalid_number:{name}")
    if isinstance(value, str) and (len(value) > 128 or not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", value)):
        raise InvalidContext(f"invalid_number:{name}")
    try:
        parsed = Decimal(str(value))
    except InvalidOperation as exc:
        raise InvalidContext(f"invalid_number:{name}") from exc
    if not parsed.is_finite() or (nonnegative and parsed < 0):
        raise InvalidContext(f"invalid_number:{name}")
    return value  # preserve producer units and exact decimal strings


def _url(value):
    _text(value, "source_url")
    try:
        parts = urlsplit(value)
        valid = (parts.scheme == "https" and parts.hostname in _OFFICIAL_HOSTS
                 and not parts.username and not parts.password and parts.port in (None, HTTPS_PORT)
                 and not re.search(r"[\s\x00-\x1f\x7f]", value))
    except ValueError:
        valid = False
    if not valid:
        raise InvalidContext("unofficial_source_url")
    return value


def _authority(value):
    if (value.get("is_context_only") is not True or value.get("forecast_authority") != "RESEARCH_ONLY"
            or "probabilities" not in value or value["probabilities"] is not None
            or value.get("importance") != "NOT_SCORED"):
        raise InvalidContext("invalid_context_authority")
    return {"is_context_only": True, "forecast_authority": "RESEARCH_ONLY", "probabilities": None, "importance": "NOT_SCORED"}


def _instrument_class(row):
    """Reject contradictory explicit class facts retained by the W1 producer."""
    classes = {name.casefold(): name for name in ("Bill", "CMB", "Note", "Bond", "TIPS", "FRN")}

    def raw_text(value, name):
        value = _text(value, name, nullable=True)
        value = value.strip().casefold() if value is not None else None
        return None if value in (None, "", "null", "none", "nan") else value

    base = classes.get(raw_text(row.get("raw_security_type"), "raw_security_type"))
    raw_type = raw_text(row.get("raw_type"), "raw_type")
    explicit = classes.get(raw_type)
    flags = row.get("raw_class_flags")
    if base not in ("Bill", "Note", "Bond") or (raw_type is not None and explicit is None) or not isinstance(flags, dict):
        raise InvalidContext("invalid_instrument_class_facts")
    parsed_flags = {}
    for kind, field in (("CMB", "cashManagementBillCMB"), ("TIPS", "tips"), ("FRN", "floatingRate")):
        flag = raw_text(flags.get(field), field)
        if flag not in (None, "yes", "y", "no", "n"):
            raise InvalidContext("invalid_class_flag")
        parsed_flags[kind] = None if flag is None else flag in ("yes", "y")
    flagged = [kind for kind, enabled in parsed_flags.items() if enabled is True]
    inferred = flagged[0] if flagged else base
    kind = explicit or inferred
    allowed_base = {"CMB": ("Bill",), "TIPS": ("Note", "Bond"), "FRN": ("Note",)}
    if (len(flagged) > 1 or (flagged and kind != inferred)
            or (kind in parsed_flags and parsed_flags[kind] is False)
            or (kind in allowed_base and base not in allowed_base[kind])
            or (kind in ("Bill", "Note", "Bond") and kind != base)
            or row.get("normalized_class") != kind):
        raise InvalidContext("instrument_class_conflict")


def unavailable(reason: str) -> dict:
    return {"available": False, "schema_version": SCHEMA, **_authority({"is_context_only": True,
            "forecast_authority": "RESEARCH_ONLY", "probabilities": None, "importance": "NOT_SCORED"}),
            "note": reason, "freshness_label": "Freshness unassessed"}


def validate_context(value: dict, *, now: datetime | str) -> dict:
    """Allowlist a 30-day W1 context; no coercion of authority or evidence clocks.

    Raises InvalidContext for malformed/unsupported input. Scheduled future dates
    and deadlines are permitted. Evidence must be no later than cutoff AND now.
    Unknown fields never leave this projection, including generic band/stressed.
    """
    current = _clock(now, "now")
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA:
        raise InvalidContext("unsupported_schema")
    authority = _authority(value)
    cutoff = _clock(value.get("decision_cutoff_utc"), "decision_cutoff_utc")
    if cutoff > current or _clock(value.get("as_of"), "as_of") != cutoff:
        raise InvalidContext("invalid_producer_cutoff")
    cutoff_day_et = cutoff.astimezone(ZoneInfo("America/New_York")).date().isoformat()

    def evidence(stamp, name, *, nullable=False):
        if stamp is None and nullable:
            return None
        if not isinstance(stamp, str):
            raise InvalidContext(f"invalid_clock:{name}")
        clock = _clock(stamp, name)
        if clock > cutoff or clock > current:
            raise InvalidContext(f"future_evidence:{name}")
        return stamp

    observed = evidence(value.get("source_observed_at"), "source_observed_at", nullable=True)
    asof = _day(value.get("asof"), "asof", nullable=True)
    if asof != (_clock(observed, "source_observed_at").date().isoformat() if observed else None):
        raise InvalidContext("observation_date_mismatch")
    status = value.get("status")
    if status not in ("available", "degraded", "unavailable", "unsupported"):
        raise InvalidContext("invalid_status")
    result = {"available": status in ("available", "degraded"), "schema_version": SCHEMA,
              **authority, "status": status, "as_of": value["as_of"],
              "decision_cutoff_utc": value["decision_cutoff_utc"], "source_observed_at": observed,
              "asof": asof, "freshness_label": "Freshness unassessed"}
    health = value.get("source_health")
    if not isinstance(health, list) or len(health) > 128:
        raise InvalidContext("invalid_source_health")
    result["source_health"] = []
    for source in health:
        if not isinstance(source, dict) or source.get("stale_after_seconds") is not None or "stale_after_seconds" not in source:
            raise InvalidContext("unsupported_freshness_policy")
        item = {name: _text(source.get(name), name) for name in _HEALTH_TEXT}
        item["source_url"] = _url(source.get("source_url"))
        item.update({name: evidence(source.get(name), name, nullable=name != "latest_attempt_at") for name in _HEALTH_CLOCKS})
        item["latest_attempt_states"] = _texts(source.get("latest_attempt_states"), "latest_attempt_states")
        item["latest_failure_reasons"] = _texts(source.get("latest_failure_reasons"), "latest_failure_reasons")
        item["last_valid_observation_age_seconds"] = _number(source.get("last_valid_observation_age_seconds"), "last_valid_observation_age_seconds", nonnegative=True)
        clocks = {name: _clock(item[name], name) if item[name] is not None else None for name in _HEALTH_CLOCKS}
        if any(stamp is not None and stamp > clocks["latest_attempt_at"]
               for name, stamp in clocks.items() if name != "latest_attempt_at"):
            raise InvalidContext("source_health_clock_order")
        valid_at = clocks["last_valid_observation_at"]
        # Body arrival and valid-observation time are distinct aggregate maxima.
        # Arrival may precede parsing, follow an older valid observation after a
        # malformed response, or be unknown for a retained availability bound.
        # Each remains bounded by latest_attempt_at and cutoff; neither orders
        # the other and an unknown arrival must not be invented from known_at.
        age = item["last_valid_observation_age_seconds"]
        # Validate the producer-cutoff age, without inventing a staleness policy
        # or silently refreshing it to this web request's current clock.
        if ((valid_at is None) != (age is None) or
                (valid_at is not None and Decimal(str(age)) != Decimal(str((cutoff - valid_at).total_seconds())))):
            raise InvalidContext("source_observation_age_mismatch")
        item["stale_after_seconds"] = None
        result["source_health"].append(item)
    valid_observations = [_clock(s["last_valid_observation_at"], "last_valid_observation_at")
                          for s in result["source_health"] if s["last_valid_observation_at"]]
    if (_clock(observed, "source_observed_at") if observed else None) != max(valid_observations, default=None):
        raise InvalidContext("source_observation_mismatch")
    events = value.get("events")
    if not isinstance(events, list) or len(events) > MAX_EVENTS:
        raise InvalidContext("invalid_events")
    result["events"] = []
    for row in events:
        if not isinstance(row, dict) or row.get("type") != "AUCTION" or row.get("impact") is not None or row.get("assets") != ["bonds"]:
            raise InvalidContext("invalid_auction_row")
        item = {**_authority(row), "type": "AUCTION", "impact": None, "assets": ["bonds"]}
        item.update({name: _text(row.get(name), name, nullable=name not in ("episode_id", "label", "normalized_class", "source_state", "physical_state", "issue_calendar_state")) for name in _ROW_TEXT})
        if item["normalized_class"] not in ("Bill", "CMB", "Note", "Bond", "TIPS", "FRN"):
            raise InvalidContext("unsupported_instrument_class")
        _instrument_class(row)
        if item["source_state"] not in ("TENTATIVE", "ANNOUNCED", "RESULT_OBSERVED") or item["physical_state"] not in ("TENTATIVE", "ANNOUNCED", "AWAITING_RESULT", "RESULT_OBSERVED"):
            raise InvalidContext("unsupported_lifecycle_state")
        if item["issue_calendar_state"] not in ("ISSUE_DATE_PASSED", "ISSUE_DATE_NOT_PASSED"):
            raise InvalidContext("unsupported_issue_calendar_state")
        if (item["source_state"] == "RESULT_OBSERVED") != (item["physical_state"] == "RESULT_OBSERVED"):
            raise InvalidContext("inconsistent_result_state")
        item.update({name: _day(row.get(name), name, nullable=name == "announcement_date") for name in ("date", "auction_date", "issue_date", "announcement_date")})
        if item["date"] != item["auction_date"]:
            raise InvalidContext("auction_date_mismatch")
        if item["issue_date"] < item["auction_date"]:
            raise InvalidContext("issue_before_auction")
        expected_issue_state = "ISSUE_DATE_PASSED" if item["issue_date"] < cutoff_day_et else "ISSUE_DATE_NOT_PASSED"
        if item["issue_calendar_state"] != expected_issue_state:
            raise InvalidContext("issue_calendar_state_mismatch")
        item["known_at"] = evidence(row.get("known_at"), "known_at")
        item["first_observed_at"] = evidence(row.get("first_observed_at"), "first_observed_at", nullable=True)
        known_at = _clock(item["known_at"], "known_at")
        if observed is None or known_at > _clock(observed, "source_observed_at"):
            raise InvalidContext("row_evidence_after_source_observation")
        if item["first_observed_at"] is not None and _clock(item["first_observed_at"], "first_observed_at") > known_at:
            raise InvalidContext("first_observation_after_selected_vintage")
        deadline = row.get("competitive_deadline_utc")
        if deadline is not None:
            if not isinstance(deadline, str):
                raise InvalidContext("invalid_clock:competitive_deadline_utc")
            _clock(deadline, "competitive_deadline_utc")  # event clock may be future
        item["competitive_deadline_utc"] = deadline
        if item["source_state"] == "RESULT_OBSERVED":
            expected_physical_state = "RESULT_OBSERVED"
        elif ((deadline is not None and _clock(deadline, "competitive_deadline_utc") <= cutoff)
              or item["auction_date"] < cutoff_day_et):
            expected_physical_state = "AWAITING_RESULT"
        else:
            expected_physical_state = item["source_state"]
        if item["physical_state"] != expected_physical_state:
            raise InvalidContext("physical_state_cutoff_mismatch")
        item["source_url"] = _url(row.get("source_url"))
        item["source"] = _url(row.get("source"))
        item["offering_amount_usd"] = _number(row.get("offering_amount_usd"), "offering_amount_usd", nonnegative=True)
        item["null_reasons"] = _texts(row.get("null_reasons"), "null_reasons")
        item["result_evidence_fields"] = _texts(row.get("result_evidence_fields"), "result_evidence_fields")
        if any(field not in _RESULT_EVIDENCE_FIELDS for field in item["result_evidence_fields"]):
            raise InvalidContext("unsupported_result_evidence_field")
        supplied_result = row.get("result")
        if supplied_result is None:
            if item["result_evidence_fields"] or item["source_state"] == "RESULT_OBSERVED":
                raise InvalidContext("inconsistent_result_evidence")
            item["result"] = None
        else:
            if not isinstance(supplied_result, dict) or not item["result_evidence_fields"] or item["source_state"] != "RESULT_OBSERVED":
                raise InvalidContext("inconsistent_result_evidence")
            known = _clock(item["known_at"], "known_at")
            if (item["auction_date"] > known.astimezone(ZoneInfo("America/New_York")).date().isoformat()
                    or (deadline is not None and _clock(deadline, "competitive_deadline_utc") > known)):
                raise InvalidContext("future_result_bearing_contradiction")
            item["result"] = {name: _number(supplied_result.get(name), name, nonnegative=name.endswith("_usd")) for name in _RESULT_FIELDS}
            if supplied_result.get("bidder_shares") is not None:
                raise InvalidContext("unsupported_bidder_shares")
            item["result"]["bidder_shares"] = None
        # Historical versions are not served, but later-known evidence hidden in
        # them cannot pass PIT validation of a claimed exact producer context.
        versions = row.get("observation_versions", [])
        if not isinstance(versions, list) or len(versions) > MAX_EVENTS:
            raise InvalidContext("invalid_observation_versions")
        for version in versions:
            if not isinstance(version, dict):
                raise InvalidContext("invalid_observation_version")
            evidence(version.get("known_at"), "version_known_at")
        result["events"].append(item)
    receipts = value.get("observation_receipts", [])
    if not isinstance(receipts, list) or len(receipts) > 128:
        raise InvalidContext("invalid_observation_receipts")
    for receipt in receipts:
        if not isinstance(receipt, dict):
            raise InvalidContext("invalid_observation_receipt")
        evidence(receipt.get("observed_at"), "receipt_observed_at")
        _url(receipt.get("source_url"))
    coverage = value.get("coverage")
    if not isinstance(coverage, dict) or type(coverage.get("horizon_days")) is not int or coverage["horizon_days"] != 30:
        raise InvalidContext("unsupported_coverage_horizon")
    result["coverage"] = {"horizon_days": 30, "timezone": _text(coverage.get("timezone"), "timezone"),
                          "universe": _text(coverage.get("universe"), "universe")}
    result["coverage"].update({name: _day(coverage.get(name), name) for name in _COVERAGE_DATES})
    for name in _COVERAGE_COUNTS:
        count = coverage.get(name)
        if count is not None and (type(count) is not int or count < 0):
            raise InvalidContext(f"invalid_count:{name}")
        result["coverage"][name] = count
    for name in ("truncated", "counts_are_observed_not_complete_universe"):
        if type(coverage.get(name)) is not bool:
            raise InvalidContext(f"invalid_boolean:{name}")
        result["coverage"][name] = coverage[name]
    # Failure/quarantine reasons stay separate from valid source observations.
    for name, fields in (("source_states", ("source_kind", "source_url", "schema_id", "observed_at", "payload_sha256", "receipt_status", "status", "reason")),
                         ("quarantine", ("reason", "source_url", "payload_sha256", "row_index", "envelope_index")),
                         ("conflicts", ("reason", "episode_id", "tentative_slot_id", "known_at", "conflicting_fields", "candidate_episode_ids", "row_sha256s"))):
        rows = value.get(name, [])
        if not isinstance(rows, list) or len(rows) > MAX_EVENTS:
            raise InvalidContext(f"invalid_list:{name}")
        projected = []
        for row in rows:
            if not isinstance(row, dict):
                raise InvalidContext(f"invalid_record:{name}")
            item = {}
            for field in fields:
                if field not in row:
                    continue
                entry = row[field]
                if field in ("known_at", "observed_at"):
                    entry = evidence(entry, field)
                elif field == "source_url":
                    entry = _url(entry)
                elif field in ("row_index", "envelope_index"):
                    if type(entry) is not int or entry < 0:
                        raise InvalidContext(f"invalid_count:{field}")
                elif isinstance(entry, list):
                    entry = _texts(entry, field)
                else:
                    entry = _text(entry, field, nullable=True)
                item[field] = entry
            projected.append(item)
        result[name] = projected
    return copy.deepcopy(result)


def read_context(path: Path | None = None, *, now: datetime | str | None = None) -> dict:
    """Fresh local read, fail-soft; missing nested producer publication stays OFF."""
    try:
        with (Path(path) if path is not None else FEED_PATH).open("rb") as source:
            raw = source.read(MAX_FEED_BYTES + 1)
        if len(raw) > MAX_FEED_BYTES:
            return unavailable("auction_feed_size_limit")
        wrapper = json.loads(raw)
        if not isinstance(wrapper, dict) or "sovereign_auction_context" not in wrapper:
            return unavailable("sovereign_auction_context_not_published")
        return validate_context(wrapper["sovereign_auction_context"], now=now if now is not None else datetime.now(timezone.utc))
    except FileNotFoundError:
        return unavailable("auction_feed_not_available")
    except InvalidContext as exc:
        return unavailable(str(exc))
    except (OSError, ValueError, TypeError, RecursionError):
        return unavailable("auction_feed_unreadable")

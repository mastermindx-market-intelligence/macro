"""EXP-1 declared-capture inspection; no normalized financial admission."""
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
import hashlib
import json
import math
import re

from lib.dataos.identity import AliasRow, IdentityError, VendorAliasTable

SCHEMA = "k3e.declared_capture_inspection.v1"
ALIASES_PATH = "data/reference/vendor_aliases.parquet"
PROVIDER_VENDOR_SPACE = {"yfinance": "yahoo"}
IDENTITY_UNRESOLVED = "SECURITY_IDENTITY_UNRESOLVED_AT_CUTOFF"
IDENTITY_GATE_CONTRACT = "k3e.identity_gate.v1"
EXPECTATION_STATES = {"CURRENT", "WITHDRAWN", "STALE"}
OBSERVATIONS_PATH = "data/revisions/expectation_observations.parquet"
ATTEMPTS_PATH = "data/revisions/expectation_attempts.parquet"
STATUSES = {"success", "partial", "null", "http_401", "http_403",
            "http_429", "malformed", "error"}
ESTIMATE_TYPES = {"average", "median", "high", "low", "growth", "year_ago"}
BLOCKED_RIGHTS = {"RIGHTS_BLOCKED", "UNLICENSED", "PROHIBITED", "BLOCKED"}
DISPLAY_ONLY_RIGHTS = {"DISPLAY_ONLY"}
GROUP_FIELDS = ("collection_session_id", "attempt_id", "provider",
                "provider_record_class", "provider_payload_hash",
                "ticker_compat", "metric", "horizon_label_raw")
RAW_FIELDS = ("observation_id", "observation_type", "value", "missingness_reason",
              "correction_state", "supersedes_observation_id", "rights_class",
              "source_effective_at", "source_published_at", "provider_observed_at",
              "system_observed_at", "period_end", "fiscal_period", "fiscal_year",
              "unit", "currency", "basis", "issuer_ref", "security_ref",
              "market_session", "aggregation_level", "contributor_id", "provenance_note",
              "expectation_state", "expectation_state_as_of")
ATTEMPT_FIELDS = ("attempt_id", "collection_session_id", "provider", "ticker_compat",
                  "attempted_at", "completed_at", "status", "http_status",
                  "latency_ms", "response_payload_hash", "safe_error_class",
                  "observation_count")


class QueryRefusal(ValueError):
    """Typed refusal for malformed query/input envelope."""
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


def parse_utc(value):
    """Require an ISO clock with an explicit zero UTC offset."""
    if not isinstance(value, str):
        raise QueryRefusal("INVALID_UTC_CLOCK")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise QueryRefusal("INVALID_UTC_CLOCK") from exc
    if result.tzinfo is None or result.utcoffset().total_seconds() != 0:
        raise QueryRefusal("INVALID_UTC_CLOCK")
    return result.astimezone(timezone.utc)


def _clock(value):
    if value is None:
        return None
    try:
        return parse_utc(value)
    except QueryRefusal:
        return None


def _strict_clock(value):
    if value is None:
        return None
    return parse_utc(value)


def _iso(value):
    return value.isoformat().replace("+00:00", "Z")


def _digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def _number(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))


def _count(value):
    return _number(value) and value >= 0 and int(value) == value


def _raw(row, mask_state=False):
    raw = {key: row.get(key) for key in RAW_FIELDS}
    if mask_state:
        # A state whose clock is after the query cutoff was not knowable then.
        raw["expectation_state"] = None
        raw["expectation_state_as_of"] = None
    return raw


def _latest(items, clock_key):
    if not items:
        return {"status": "UNAVAILABLE", "snapshot": None, "candidates": []}
    newest = max(item[clock_key] for item in items)
    tied = [item for item in items if item[clock_key] == newest]
    if len(tied) != 1:
        return {"status": "UNESTIMABLE", "snapshot": None,
                "reason": "AMBIGUOUS_EQUAL_CAPTURE_CLOCK",
                "candidates": sorted(
                    [item["identity"] for item in tied],
                    key=lambda item: json.dumps(item, sort_keys=True))}
    return {"status": "AVAILABLE", "snapshot": tied[0]["public"], "candidates": []}


def _validate_provenance(provenance):
    if not isinstance(provenance, dict):
        raise QueryRefusal("INVALID_SOURCE_PROVENANCE")
    revision = provenance.get("source_revision")
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise QueryRefusal("FULL_IMMUTABLE_SOURCE_REVISION_REQUIRED")
    inputs = provenance.get("inputs", {})
    if not isinstance(inputs, dict):
        raise QueryRefusal("PAIRED_INPUT_HASHES_REQUIRED")
    for path in (OBSERVATIONS_PATH, ATTEMPTS_PATH):
        item = inputs.get(path, {})
        if not isinstance(item, dict):
            raise QueryRefusal("PAIRED_INPUT_HASHES_REQUIRED")
        if (not isinstance(item.get("sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"])
                or not isinstance(item.get("git_blob_id"), str)
                or not re.fullmatch(r"[0-9a-f]{40}", item["git_blob_id"])):
            raise QueryRefusal("PAIRED_INPUT_HASHES_REQUIRED")


def _knowledge_clock(value):
    if isinstance(value, str):
        return parse_utc(value)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        else:
            value = value.astimezone(timezone.utc)
        return datetime(value.year, value.month, value.day, value.hour, value.minute,
                        value.second, value.microsecond, tzinfo=timezone.utc)
    raise TypeError("invalid knowledge clock")


def _window_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise TypeError("invalid window date")


def _alias_pin(entry):
    return (isinstance(entry, dict)
            and isinstance(entry.get("sha256"), str)
            and re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])
            and isinstance(entry.get("git_blob_id"), str)
            and re.fullmatch(r"[0-9a-f]{40}", entry["git_blob_id"]))


def _build_alias_index(records):
    rows_for_table = []
    index = defaultdict(list)
    try:
        for record in records:
            if not isinstance(record, dict):
                raise TypeError("alias record must be mapping")
            vendor = record.get("vendor")
            if vendor not in PROVIDER_VENDOR_SPACE.values():
                continue
            vendor_symbol = record.get("vendor_symbol")
            security_id = record.get("security_id")
            if not isinstance(vendor, str) or not vendor:
                raise ValueError("invalid vendor")
            if not isinstance(vendor_symbol, str) or not vendor_symbol:
                raise ValueError("invalid vendor_symbol")
            if not isinstance(security_id, str) or not security_id:
                raise ValueError("invalid security_id")
            valid_from = _window_date(record.get("valid_from"))
            valid_to = _window_date(record.get("valid_to"))
            ingested = _knowledge_clock(record.get("ingested_at"))
            alias_row = AliasRow(vendor, vendor_symbol, security_id, valid_from, valid_to)
            rows_for_table.append(alias_row)
            index[(vendor, vendor_symbol)].append((alias_row, ingested))
        VendorAliasTable(rows_for_table)
    except (ValueError, TypeError, IdentityError):
        return "ALIAS_TABLE_INVALID", {}
    return "CHECKED", dict(index)


def _resolve_security(index, space, symbol, on_date, known_at):
    if space is None:
        return None
    found = {row.security_id for row, ingested in index.get((space, symbol), ())
             if ingested <= known_at and row.covers(on_date)}
    return next(iter(found)) if len(found) == 1 else None


def inspect_expectation_surface(observations, attempts, *, source_provenance,
                                ticker, metric, horizon, as_of,
                                provider="yfinance", composed_at=None,
                                identity_aliases=None):
    """Read mappings without mutation; source clocks are declarations, not PIT proof.

    Callers must supply JSON-compatible mappings (including real nulls). The CLI
    verifies source bytes. Caller labels never authorize normalized consumption.
    """
    cutoff = parse_utc(as_of)
    if (not isinstance(ticker, str) or not ticker.strip() or ticker != ticker.strip()
            or not isinstance(provider, str) or not provider.strip()
            or not isinstance(horizon, str) or not horizon.strip()
            or metric not in {"EPS", "revenue"}):
        raise QueryRefusal("INVALID_QUERY_DIMENSIONS")
    _validate_provenance(source_provenance)
    identity_status = "NOT_CHECKED"
    alias_input = None
    alias_index = {}
    query_security = None
    identity_resolved_records = None
    identity_unresolved_records = None
    if identity_aliases is None:
        provenance_inputs = {
            path: {key: source_provenance["inputs"][path][key]
                   for key in ("sha256", "git_blob_id")}
            for path in (OBSERVATIONS_PATH, ATTEMPTS_PATH)}
    else:
        if not isinstance(identity_aliases, (list, tuple)):
            raise QueryRefusal("RECORD_MAPPINGS_REQUIRED")
        if not all(isinstance(record, dict) for record in identity_aliases):
            raise QueryRefusal("RECORD_MAPPINGS_REQUIRED")
        entry = source_provenance["inputs"].get(ALIASES_PATH)
        absent_marker = dict(absent_at_revision=True)
        if _alias_pin(entry):
            alias_input = {key: entry[key] for key in ("sha256", "git_blob_id")}
            identity_status, alias_index = _build_alias_index(identity_aliases)
        elif entry == absent_marker and not identity_aliases:
            alias_input = absent_marker
            identity_status = "ALIAS_PATH_ABSENT_AT_REVISION"
        else:
            raise QueryRefusal("ALIAS_PROVENANCE_REQUIRED")
        provenance_inputs = {
            path: {key: source_provenance["inputs"][path][key]
                   for key in ("sha256", "git_blob_id")}
            for path in (OBSERVATIONS_PATH, ATTEMPTS_PATH)}
        provenance_inputs[ALIASES_PATH] = alias_input
    obs = list(observations)
    att = list(attempts)
    if not all(isinstance(row, dict) for row in obs + att):
        raise QueryRefusal("RECORD_MAPPINGS_REQUIRED")
    composition = parse_utc(composed_at) if composed_at else datetime.now(timezone.utc)
    query = {"provider": provider, "ticker_compat": ticker, "metric": metric,
             "horizon_label_raw": horizon, "as_of": _iso(cutoff)}
    provenance = {"source_revision": source_provenance["source_revision"],
                  "inputs": provenance_inputs}
    query_identity = _digest({"schema": SCHEMA, "query": query, "source": provenance})
    space = PROVIDER_VENDOR_SPACE.get(provider)
    if identity_status == "CHECKED":
        query_security = _resolve_security(alias_index, space, ticker, cutoff.date(), cutoff)
    reasons = Counter()
    eligible_attempts = []
    pending_attempts = []
    invalid_attempts = []
    attempt_by_id = defaultdict(list)
    provider_family_mismatches = 0
    # Start visibility and completion visibility are separate. No pending
    # classification may inspect the final outcome, including invalid labels.
    for row in att:
        if row.get("provider") != provider or row.get("ticker_compat") != ticker:
            if (row.get("ticker_compat") == ticker
                    and isinstance(row.get("provider"), str) and row["provider"] != provider):
                provider_family_mismatches += 1
            continue
        start = _clock(row.get("attempted_at"))
        identity = row.get("attempt_id")
        if start is None:
            continue
        if start > cutoff:
            continue
        end = _clock(row.get("completed_at"))
        start_identity_valid = (
            isinstance(identity, str) and bool(identity)
            and isinstance(row.get("collection_session_id"), str)
            and bool(row["collection_session_id"]))
        pending = (row.get("completed_at") is None
                   or (end is not None and end > cutoff))
        if pending:
            valid = False
            public = {key: row.get(key) for key in
                      ("attempt_id", "collection_session_id", "provider",
                       "ticker_compat", "attempted_at")}
            public.update(status=None, completed_at=None,
                          derived_query_state="INCOMPLETE_AT_CUTOFF")
            if not start_identity_valid:
                public["start_identity_degradation"] = "INVALID_ATTEMPT_START_IDENTITY"
            pending_attempts.append({"time": start, "identity": {"attempt_id": identity},
                                     "public": public})
        else:
            valid = (start_identity_valid and end is not None
                     and start <= end <= cutoff and row.get("status") in STATUSES)
            if valid:
                public = {key: row.get(key) for key in ATTEMPT_FIELDS}
                public["age_seconds_since_completed"] = (cutoff - end).total_seconds()
                eligible_attempts.append({"time": start, "identity": {"attempt_id": identity},
                                          "public": public})
            else:
                reasons["INVALID_ATTEMPT_RECEIPT"] += 1
                invalid_attempts.append({
                    "time": start, "identity": {"attempt_id": identity},
                    "public": {"attempt_id": identity, "attempted_at": row["attempted_at"],
                               "status": None, "completed_at": None,
                               "derived_query_state": "INVALID_ATTEMPT_RECEIPT"}})
        attempt_by_id[identity].append(
            {"row": row, "start": start, "end": end,
             "valid": valid, "pending": pending})
    for identity, entries in attempt_by_id.items():
        if len(entries) > 1:
            reasons["DUPLICATE_ATTEMPT_ID"] += len(entries)
    attempt_views = eligible_attempts + pending_attempts + invalid_attempts

    relevant = []
    # Establish the whole declared temporal boundary before reading observation
    # IDs, values, missingness, rights, payloads or group multiplicity. Explicit
    # not-yet-completed observations have no historical diagnostic population.
    # Locatable missing/malformed receipts remain eligible for exclusion reasons.
    for row in obs:
        if any(row.get(key) != query[key] for key in
               ("provider", "ticker_compat", "metric", "horizon_label_raw")):
            if (row.get("ticker_compat") == query["ticker_compat"]
                    and row.get("metric") == query["metric"]
                    and row.get("horizon_label_raw") == query["horizon_label_raw"]
                    and isinstance(row.get("provider"), str)
                    and row["provider"] != query["provider"]):
                provider_family_mismatches += 1
            continue
        entries = attempt_by_id.get(row.get("attempt_id"), [])
        # Any pending receipt makes a reused attempt ID temporally ambiguous.
        # Withhold every observation under it, including completed candidates;
        # the known starts still supply duplicate-attempt diagnostics above.
        if any(entry["pending"] for entry in entries):
            continue
        captures = [_clock(row.get(key)) for key in
                    ("provider_observed_at", "system_observed_at")]
        present = [clock for clock in captures if clock is not None]
        if not present or any(clock > cutoff for clock in present):
            continue
        try:
            published = _strict_clock(row.get("source_published_at"))
        except QueryRefusal:
            reasons["MALFORMED_SOURCE_PUBLISHED_AT"] += 1
            continue
        if published is not None and published > cutoff:
            reasons["SOURCE_PUBLISHED_AFTER_CUTOFF"] += 1
            continue
        relevant.append((row, captures))
    if provider_family_mismatches:
        reasons["PROVIDER_FAMILY_UNRESOLVED"] += provider_family_mismatches
    ids = Counter(row.get("observation_id") for row, _ in relevant)
    groups = defaultdict(list)
    excluded = 0
    true_missing = 0
    if identity_status != "NOT_CHECKED":
        identity_resolved_records = 0
        identity_unresolved_records = 0
    for row, captures in relevant:
        capture_clock = min(clock for clock in captures if clock is not None)
        known_at = min(capture_clock, cutoff)
        if identity_status == "CHECKED":
            row_security = _resolve_security(
                alias_index, space, row["ticker_compat"], capture_clock.date(), known_at)
            identity_resolved = (query_security is not None and row_security == query_security)
        else:
            identity_resolved = False
        if identity_status != "NOT_CHECKED":
            if identity_resolved:
                identity_resolved_records += 1
            else:
                identity_unresolved_records += 1
        faults = []
        if None in captures:
            faults.append("MISSING_OR_MALFORMED_CAPTURE_CLOCK")
        entries = attempt_by_id.get(row.get("attempt_id"), [])
        receipt = entries[0] if len(entries) == 1 else None
        if not entries:
            faults.append("MISSING_LINKED_ATTEMPT")
        elif len(entries) != 1:
            faults.append("DUPLICATE_LINKED_ATTEMPT")
        elif not receipt["valid"]:
            faults.append("INVALID_LINKED_ATTEMPT")
        if not row.get("observation_id") or ids[row.get("observation_id")] != 1:
            faults.append("MISSING_OR_DUPLICATE_OBSERVATION_ID")
        identifiable = all(isinstance(row.get(key), str) and row[key]
                           for key in GROUP_FIELDS)
        if not identifiable:
            faults.append("INCOMPLETE_SNAPSHOT_IDENTITY")
        if row.get("observation_type") not in ESTIMATE_TYPES | {"covering_analyst_count"}:
            faults.append("INVALID_OBSERVATION_TYPE")
        if row.get("value") is None:
            if row.get("missingness_reason") is None:
                faults.append("NULL_WITHOUT_MISSINGNESS")
            else:
                true_missing += 1
        elif not _number(row["value"]) or row.get("missingness_reason") is not None:
            faults.append("INVALID_VALUE_MISSINGNESS")
        if (receipt and receipt["valid"] and None not in captures):
            attempt = receipt["row"]
            if any(row.get(key) != attempt.get(key) for key in
                   ("collection_session_id", "provider", "ticker_compat")):
                faults.append("ATTEMPT_IDENTITY_MISMATCH")
            if row.get("provider_payload_hash") != attempt.get("response_payload_hash"):
                faults.append("ATTEMPT_PAYLOAD_MISMATCH")
            if any(clock < receipt["start"] for clock in captures):
                faults.append("CAPTURE_PRECEDES_ATTEMPT")
            if captures[1] < captures[0]:
                faults.append("SYSTEM_CAPTURE_PRECEDES_PROVIDER_CAPTURE")
            published = _clock(row.get("source_published_at"))
            effective = _clock(row.get("source_effective_at"))
            for field, parsed in (("source_published_at", published),
                                  ("source_effective_at", effective)):
                if row.get(field) is not None and parsed is None:
                    faults.append("MALFORMED_" + field.upper())
            if published and any(published > clock for clock in captures):
                faults.append("PUBLICATION_AFTER_CAPTURE")
            # Economic effective dates may be future dates; they are not known_at.
        reasons.update(set(faults))
        if not identifiable:
            excluded += 1
            continue
        # Retain invalid identifiable members until field and clock coherence
        # adjudication. Dropping a bad duplicate first would manufacture support.
        availability = (max(*captures, receipt["end"])
                        if not faults else None)
        groups[tuple(row[key] for key in GROUP_FIELDS)].append(
            {"row": row, "availability": availability,
             "receipt": receipt, "faults": faults,
             "identity_resolved": identity_resolved})

    snapshots = []
    supported = []
    supported_records = 0
    inconsistent_records = 0
    for key, members in groups.items():
        rows = [item["row"] for item in members]
        fields = defaultdict(list)
        for row in rows:
            fields[row.get("observation_type")].append(row)
        faults = []
        if any(len(items) > 1 for items in fields.values()):
            faults.append("DUPLICATE_SNAPSHOT_FIELD")
        for field in ("period_end", "provider_observed_at", "system_observed_at"):
            if len({row.get(field) for row in rows}) > 1:
                faults.append("INCONSISTENT_SNAPSHOT_" + field.upper())
        if faults:
            reasons.update(faults)
            inconsistent_records += len(rows)
            continue
        valid_members = [item for item in members if not item["faults"]]
        excluded += len(members) - len(valid_members)
        if not valid_members:
            continue
        rows = [item["row"] for item in valid_members]
        fields = {row["observation_type"]: [row] for row in rows}
        chosen = fields.get("average", [None])[0]
        coverage = fields.get("covering_analyst_count", [None])[0]
        coverage_valid = (coverage is not None and coverage.get("missingness_reason") is None
                          and _count(coverage.get("value")))
        if coverage is not None and coverage.get("value") is not None and not coverage_valid:
            reasons["INVALID_COVERING_ANALYST_COUNT"] += 1
        attempt = valid_members[0]["receipt"]["row"]
        is_supported = (attempt["status"] == "success" and chosen is not None
                        and _number(chosen.get("value"))
                        and chosen.get("missingness_reason") is None
                        and coverage_valid and coverage["value"] > 0)
        contributor_fault = (
            chosen is not None and chosen.get("aggregation_level") == "single_contributor"
            and not (isinstance(chosen.get("contributor_id"), str) and chosen["contributor_id"]))
        state_faults = []
        state = (chosen.get("expectation_state") if chosen is not None else None) or "CURRENT"
        state_clock_value = (chosen.get("expectation_state_as_of")
                             if state != "CURRENT" else None)
        try:
            state_clock = _strict_clock(state_clock_value)
        except QueryRefusal:
            state_clock = None
        if state not in EXPECTATION_STATES:
            state_faults.append("INVALID_EXPECTATION_STATE")
        elif state != "CURRENT" and state_clock is None:
            state_faults.append("INVALID_EXPECTATION_STATE_CLOCK")
        # Only a state whose own clock is at or before the cutoff is visible.
        state_visible = (state not in {"WITHDRAWN", "STALE"} or state_clock is None
                         or state_clock <= cutoff)
        public_state = state if state_visible else "CURRENT"
        public_state_clock = state_clock if state_visible else None
        support_reasons = []
        if contributor_fault:
            support_reasons.append("CONTRIBUTOR_IDENTITY_UNAVAILABLE")
            reasons["CONTRIBUTOR_IDENTITY_UNAVAILABLE"] += 1
            is_supported = False
        if (identity_status != "NOT_CHECKED"
                and not all(item["identity_resolved"] for item in valid_members)):
            support_reasons.append(IDENTITY_UNRESOLVED)
            reasons[IDENTITY_UNRESOLVED] += 1
            is_supported = False
        if state_faults:
            support_reasons.append("INVALID_EXPECTATION_STATE_ENVELOPE")
            reasons.update(state_faults)
            is_supported = False
        elif state in {"WITHDRAWN", "STALE"} and state_clock <= cutoff:
            is_supported = False
            support_reasons.append("EXPECTATION_STATE_UNAVAILABLE_AT_CUTOFF")
        if attempt["status"] != "success":
            support_reasons.append("ATTEMPT_NOT_SUCCESSFUL")
        if chosen is None:
            support_reasons.append("AVERAGE_FIELD_ABSENT")
        elif chosen.get("value") is None or chosen.get("missingness_reason") is not None:
            support_reasons.append("AVERAGE_UNAVAILABLE")
        if not coverage_valid:
            support_reasons.append("COVERING_ANALYST_COUNT_UNAVAILABLE_OR_INVALID")
        elif coverage["value"] == 0:
            support_reasons.append("ZERO_COVERING_ANALYST_COUNT")
        availability = max(item["availability"] for item in valid_members)
        identity = dict(zip(GROUP_FIELDS, key))
        public = {"identity": identity, "derived_capture_available_at": _iso(availability),
                  "derived_capture_availability_rule":
                      "max(system_observed_at,provider_observed_at,linked_attempt_completed_at)",
                  "age_seconds": (cutoff - availability).total_seconds(),
                  "expectation_state": public_state,
                  "expectation_state_as_of": _iso(public_state_clock) if public_state_clock else None,
                  "expectation_state_age_seconds": (
                      (cutoff - public_state_clock).total_seconds()
                      if public_state_clock else None),
                  "selected_raw_field": "average",
                  "selected_observation": _raw(chosen, not state_visible) if chosen else None,
                  "provider_reported_covering_analyst_count":
                      coverage["value"] if coverage_valid else None,
                  "covering_count_observation": _raw(coverage, not state_visible) if coverage else None,
                  "structurally_supported": is_supported, "support_reasons": support_reasons,
                  "attempt_status": attempt["status"], "attempted_at": attempt["attempted_at"],
                  "completed_at": attempt["completed_at"],
                  "raw_fields": {name: _raw(items[0], not state_visible)
                                 for name, items in sorted(fields.items())},
                  "evidence_use": "RAW_CAPTURE_INSPECTION_ONLY"}
        item = {"time": availability, "identity": identity, "public": public}
        snapshots.append(item)
        if is_supported:
            supported.append(item)
        if attempt["status"] == "success" and coverage_valid and coverage["value"] > 0:
            supported_records += sum(row["observation_type"] in ESTIMATE_TYPES
                                     and _number(row.get("value"))
                                     and row.get("missingness_reason") is None for row in rows)

    latest_capture = _latest(snapshots, "time")
    last_supported = _latest(supported, "time")
    latest_attempt = _latest(attempt_views, "time")
    # The governing state is the cutoff-visible state of the LATEST captured
    # snapshot; a superseded historical withdrawal does not poison the surface.
    # Equal-clock ties fail closed: any tied WITHDRAWN/STALE state governs.
    newest_capture = max((item["time"] for item in snapshots), default=None)
    governing_states = {item["public"]["expectation_state"] for item in snapshots
                        if item["time"] == newest_capture
                        and item["public"]["expectation_state_age_seconds"] is not None}
    withdrawn_now = "WITHDRAWN" in governing_states
    stale_now = "STALE" in governing_states
    if withdrawn_now or stale_now:
        last_supported = {"status": "UNAVAILABLE", "snapshot": None, "candidates": []}
    current = latest_capture["snapshot"]
    previous = last_supported["snapshot"]
    current_anchor = current["selected_observation"].get("period_end") if current and current["selected_observation"] else None
    previous_anchor = previous["selected_observation"].get("period_end") if previous else None
    continuity = ("ANCHOR_UNAVAILABLE" if not current_anchor or not previous_anchor else
                  "SAME_NATIVE_PERIOD" if current_anchor == previous_anchor else
                  "NATIVE_PERIOD_CHANGED_NO_REVISION_INFERENCE")
    raw_rights = sorted({row.get("rights_class") or "UNKNOWN" for row, _ in relevant})
    rights_blocked = (any(right in BLOCKED_RIGHTS for right in raw_rights)
                      or any(right in DISPLAY_ONLY_RIGHTS for right in raw_rights))
    expectation_state = ("WITHDRAWN" if withdrawn_now else
                         "STALE" if stale_now else "CURRENT")
    baseline_reasons = ["NORMALIZED_CONSUMER_ADMISSION_NOT_GRANTED"]
    if withdrawn_now:
        baseline_reasons.append("EXPECTATION_WITHDRAWN_AT_CUTOFF")
    if stale_now:
        baseline_reasons.append("EXPECTATION_STALE_AT_CUTOFF")
    if not rights_blocked:
        baseline_reasons.append("SOURCE_USE_RIGHTS_UNKNOWN")
    if rights_blocked:
        baseline_reasons.append("SOURCE_USE_RIGHTS_BLOCKED")
        candidate = None
    else:
        candidate = previous["selected_observation"] if previous else None
    for field in ("issuer_ref", "security_ref", "unit", "currency", "basis", "period_end"):
        if candidate is None or candidate.get(field) is None:
            baseline_reasons.append("CANONICAL_" + field.upper() + "_UNAVAILABLE")
    if previous is None:
        baseline_reasons.append("NO_UNAMBIGUOUS_STRUCTURALLY_SUPPORTED_SNAPSHOT")
    baseline_status = ("RIGHTS_BLOCKED" if rights_blocked else
                       "WITHDRAWN_UNAVAILABLE" if withdrawn_now else
                       "STALE_UNAVAILABLE" if stale_now else
                       "UNESTIMABLE" if relevant else "UNAVAILABLE")
    if identity_status == "NOT_CHECKED":
        identity_gate = {
            "contract": IDENTITY_GATE_CONTRACT,
            "status": identity_status,
            "alias_input": None,
            "vendor_space": PROVIDER_VENDOR_SPACE.get(provider),
            "provider_vendor_space_map": dict(PROVIDER_VENDOR_SPACE),
            "query_security_id_at_cutoff": None,
            "resolved_records": None,
            "unresolved_records": None,
            "reason_code": IDENTITY_UNRESOLVED,
            "rule": "a relevant row is identity-resolved only if a vendor_aliases row in the provider vendor space for its ticker has ingested_at <= min(row capture clock, cutoff), its validity window (valid_from inclusive, valid_to exclusive, per lib/dataos/identity.AliasRow.covers; null bounds open) covers the capture date, and its security_id equals the query ticker security_id resolved at the cutoff under the same rule; undated rows are usable from ingested_at forward, never before; unresolved rows stay in denominators and are snapshot-ineligible",
            "schema_note": "payload schema string unchanged (pinned by engine/k3e_coupling.py); identity_gate is an additive block, contract k3e.identity_gate.v1; receipts produced before this change reproduce only at their own code revision",
        }
    else:
        identity_gate = {
            "contract": IDENTITY_GATE_CONTRACT,
            "status": identity_status,
            "alias_input": alias_input,
            "vendor_space": PROVIDER_VENDOR_SPACE.get(provider),
            "provider_vendor_space_map": dict(PROVIDER_VENDOR_SPACE),
            "query_security_id_at_cutoff": query_security,
            "resolved_records": identity_resolved_records,
            "unresolved_records": identity_unresolved_records,
            "reason_code": IDENTITY_UNRESOLVED,
            "rule": "a relevant row is identity-resolved only if a vendor_aliases row in the provider vendor space for its ticker has ingested_at <= min(row capture clock, cutoff), its validity window (valid_from inclusive, valid_to exclusive, per lib/dataos/identity.AliasRow.covers; null bounds open) covers the capture date, and its security_id equals the query ticker security_id resolved at the cutoff under the same rule; undated rows are usable from ingested_at forward, never before; unresolved rows stay in denominators and are snapshot-ineligible",
            "schema_note": "payload schema string unchanged (pinned by engine/k3e_coupling.py); identity_gate is an additive block, contract k3e.identity_gate.v1; receipts produced before this change reproduce only at their own code revision",
        }
    payload = {"schema": SCHEMA, "query_identity": query_identity, "query": query,
               "source": provenance,
               "identity_gate": identity_gate,
               "replay_basis": "declared_capture_at_frozen_source_revision",
               "historical_public_availability_verified": False,
               "historical_repository_visibility_verified": False,
               "latest_captured_snapshot": latest_capture,
               "last_structurally_supported_snapshot": last_supported,
               "latest_attempt": latest_attempt, "period_continuity": continuity,
               "freshness_policy": {"status": "UNAVAILABLE", "reason": "NO_ADMITTED_FRESHNESS_POLICY"},
               "normalized_baseline": {"value": None, "status": baseline_status,
                                       "expectation_state": expectation_state,
                                       "rights_state": "RIGHTS_BLOCKED" if rights_blocked else "UNKNOWN",
                                       "source_declared_rights_labels": raw_rights,
                                       "reasons": baseline_reasons,
                                       "candidate_observation_id": candidate["observation_id"] if candidate else None},
               "denominators": {
                   "capture_clock_bounded_relevant_records": len(relevant),
                   "valid_captured_records": len(relevant) - excluded - inconsistent_records,
                   "structurally_supported_estimate_records": supported_records,
                   "true_missing_records": true_missing,
                   "invalid_or_inconsistent_excluded_records": excluded + inconsistent_records,
                   "distinct_coherent_source_snapshots": len(snapshots),
                   "distinct_structurally_supported_snapshots": len(supported),
                   "started_attempt_records_by_cutoff": sum(len(items) for items in attempt_by_id.values()),
                   "unique_completed_valid_attempts_by_cutoff": len([item for item in eligible_attempts
                                                                    if len(attempt_by_id[item["identity"]["attempt_id"]]) == 1]),
                   "reason_counts": dict(sorted(reasons.items())),
                   "identity_resolved_records": identity_resolved_records,
                   "identity_unresolved_records": identity_unresolved_records,
                   "population_notes": {
                       "records": "query-dimension rows temporally available by cutoff, plus historically locatable missing/malformed receipts; explicitly pending linked captures excluded before all observation adjudication",
                       "support": "finite nonmissing estimate fields with a same-group positive integral covering count and successful completed linked attempt",
                       "true_missing": "null value with explicit missingness in capture-clock-bounded relevant records; may overlap excluded records",
                       "attempts": "provider/ticker attempts with valid attempted_at <= cutoff; not metric-specific",
                       "reasons": "nonexclusive diagnostic counts; not additive partitions",
                       "identity": "relevant records whose security identity resolved under identity_gate.rule; unresolved records stay in every other denominator"}}}
    return {"semantic_payload": payload, "semantic_digest": _digest(payload),
            "composition_time": _iso(composition),
            "input_provenance": {"full_input_observation_records": len(obs),
                                 "full_input_attempt_records": len(att),
                                 "historical_population": False}}

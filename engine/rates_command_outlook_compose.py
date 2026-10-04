"""Outlooks evidence rows + state families — display research slice E1c1.

First slice of the regime-outlook COMPOSER: builds the input record from
the owners' bytes, 30 evidence rows with their clocks, and 10 state-family
rows. Does not read path conditions, baselines or changes; the builder
script is not touched.

This module is pure: every byte is an argument, every clock is supplied.
It opens no file, no socket, and never takes the wall-clock time.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import date, datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from engine import rates_command_outlook as rco

AGE_RULE_NOTE = "age is not checked yet: only the producer's own stale flag is applied"

STATE_FAMILIES: tuple[tuple[str, str], ...] = (
    ("growth_and_inflation", "covered"),
    ("rates_and_discounting", "covered"),
    ("liquidity_and_financing", "partial"),
    ("market_structure", "partial"),
    ("leadership_and_fundamentals", "partial"),
    ("valuation_and_exposures", "not_covered"),
    ("volatility_correlation_positioning", "partial"),
    ("flows_and_reflexive_effects", "not_covered"),
    ("cross_asset_and_regional", "not_covered"),
    ("change_and_outlook", "covered"),
)

EVIDENCE_FAMILY_TO_STATE_FAMILY: dict[str, str] = {
    "core_pce": "growth_and_inflation",
    "labour": "growth_and_inflation",
    "wages_services": "growth_and_inflation",
    "inflation_breadth": "growth_and_inflation",
    "real_activity": "growth_and_inflation",
    "macro_confirmation": "growth_and_inflation",
    "treasury_curve": "rates_and_discounting",
    "policy_pricing": "rates_and_discounting",
    "issuance_and_demand": "rates_and_discounting",
    "credit_and_funding": "liquidity_and_financing",
    "participation": "market_structure",
    "dispersion": "market_structure",
    "concentration": "market_structure",
    "leader_damage": "leadership_and_fundamentals",
    "leader_turnover": "leadership_and_fundamentals",
    "revision_breadth": "leadership_and_fundamentals",
    "earnings": "leadership_and_fundamentals",
    "correlation": "volatility_correlation_positioning",
    "volatility": "volatility_correlation_positioning",
    "positioning": "volatility_correlation_positioning",
    "dollar": "cross_asset_and_regional",
    "oil": "cross_asset_and_regional",
}


def read_inputs(
    mapping: dict[str, Any],
    input_bytes: dict[str, bytes | None],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Parse input bytes into ``(docs, record)``.

    ``input_bytes`` maps a letter to its raw bytes (or ``None``). A letter
    not declared in ``mapping["artifacts"]`` raises ``ValueError``. A
    mapping letter absent from ``input_bytes`` counts as ``None``.

    ``docs`` holds the parsed object only for ``"available"`` letters.
    ``record`` is per-letter with keys ``path``, ``sha256`` (hex or
    ``None``) and ``read_status`` (``"missing"`` / ``"malformed"`` /
    ``"available"``).
    """
    artifacts = mapping["artifacts"]
    unknown_letters = set(input_bytes) - set(artifacts)
    if unknown_letters:
        raise ValueError(f"unknown letter(s) in input_bytes: {sorted(unknown_letters)}")

    docs: dict[str, Any] = {}
    record: dict[str, dict[str, Any]] = {}
    for letter, path in artifacts.items():
        raw = input_bytes.get(letter)
        if raw is None:
            record[letter] = {"path": path, "sha256": None, "read_status": "missing"}
            continue
        sha = hashlib.sha256(raw).hexdigest()
        try:
            text = raw.decode("utf-8")
            parsed = json.loads(text)
        except (UnicodeDecodeError, json.JSONDecodeError):
            record[letter] = {"path": path, "sha256": sha, "read_status": "malformed"}
            continue
        if not isinstance(parsed, dict):
            record[letter] = {"path": path, "sha256": sha, "read_status": "malformed"}
            continue
        docs[letter] = parsed
        record[letter] = {"path": path, "sha256": sha, "read_status": "available"}
    return docs, record


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def date_info(value: Any, cutoff: datetime) -> dict[str, Any]:
    """Convert a stamp into ``{as_of, precision, age_calendar_days, future_dated}``.

    ``cutoff`` must be timezone-aware. Non-strings, malformed strings and
    naive datetimes return the start dict unchanged. A plain date string
    yields precision ``"date"``; an offset-aware datetime string yields
    ``"datetime"`` in UTC.
    """
    out: dict[str, Any] = {
        "as_of": None,
        "precision": None,
        "age_calendar_days": None,
        "future_dated": False,
    }
    if cutoff.tzinfo is None:
        raise ValueError("cutoff must be timezone-aware")
    cutoff_utc = cutoff.astimezone(timezone.utc)
    cutoff_d = cutoff_utc.date()
    if not isinstance(value, str):
        return out
    if _DATE_RE.match(value):
        try:
            day = date.fromisoformat(value)
        except ValueError:
            return out
        return {
            "as_of": value,
            "precision": "date",
            "age_calendar_days": (cutoff_d - day).days,
            "future_dated": day > cutoff_d,
        }
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError, OverflowError):
        return out
    if dt.tzinfo is None:
        return out
    dt_utc = dt.astimezone(timezone.utc)
    return {
        "as_of": dt_utc.isoformat(),
        "precision": "datetime",
        "age_calendar_days": (cutoff_d - dt_utc.date()).days,
        "future_dated": dt_utc > cutoff_utc,
    }


def _render_pointer(path: list[Any]) -> str:
    parts: list[str] = []
    for seg in path:
        if isinstance(seg, str):
            parts.append(seg)
        elif isinstance(seg, dict):
            key, val = next(iter(seg.items()))
            parts.append(f"[{key}={val}]")
    return "/" + "/".join(parts)


def _family_id_for(evidence_family_id: str) -> str:
    return EVIDENCE_FAMILY_TO_STATE_FAMILY[evidence_family_id]


def _readable_value(value: Any) -> bool:
    """str / bool / int / finite float; ABSENT, None, lists, dicts, NaN/inf are not."""
    if value is rco.ABSENT:
        return False
    if isinstance(value, bool):
        return True
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return rco.finite(value)
    if isinstance(value, str):
        return True
    return False


def _resolve_clock(
    docs: dict[str, Any], artifact: str, path: list[Any], semantics: str
) -> Any:
    if semantics == "unknown":
        return None
    if artifact not in docs:
        return None
    stamp = rco.resolve(docs[artifact], path)
    if stamp is rco.ABSENT:
        return None
    return stamp


def _row_day(source: dict[str, Any], us_session: date | None) -> date | None:
    if us_session is None or source["as_of"] is None:
        return None
    if source["precision"] == "date":
        return date.fromisoformat(source["as_of"])
    dt = datetime.fromisoformat(source["as_of"])
    if dt.tzinfo is None:
        return None
    return dt.astimezone(ZoneInfo("America/New_York")).date()


def _session_relation(row_day: date | None, us_session: date | None) -> str | None:
    if row_day is None or us_session is None:
        return None
    if row_day == us_session:
        return "same_completed_session"
    if row_day < us_session:
        return "older_than_completed_session"
    return "after_completed_session"


def _last_string_segment(path: list[Any]) -> str | None:
    for seg in reversed(path):
        if isinstance(seg, str):
            return seg
    return None


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _hashable_path(path: list[Any]) -> tuple:
    out: list[Any] = []
    for seg in path:
        if isinstance(seg, dict):
            out.append(tuple(sorted(seg.items())))
        else:
            out.append(seg)
    return tuple(out)


def _zero_path_set(mapping: dict[str, Any]) -> set[tuple[str, tuple]]:
    spec = mapping.get("possible_missing_as_zero") or {}
    artifact = spec.get("artifact")
    paths = spec.get("paths") or []
    return {(artifact, _hashable_path(p)) for p in paths}


def _collect_issues(
    *,
    admission_issue: str | None,
    stale_flag_value: Any,
    stale_flag_present: bool,
    zero_match: bool,
    raw: Any,
    is_field_row: bool,
) -> list[str]:
    issues: list[str] = []
    if is_field_row:
        if admission_issue is not None and admission_issue != "missing":
            issues.append(admission_issue)
    else:
        if admission_issue is not None:
            issues.append(admission_issue)
    if stale_flag_present and stale_flag_value is not True and stale_flag_value is not False:
        issues.append("malformed")
    if zero_match and (
        (isinstance(raw, int) and not isinstance(raw, bool)) or isinstance(raw, float)
    ) and raw == 0:
        issues.append("possible_missing_as_zero")
    return _dedupe_keep_order(issues)


def _compute_status(
    *,
    in_docs: bool,
    readable: bool,
    raw: Any,
    admission_issue: str | None,
    is_field_row: bool,
    info: dict[str, Any],
    stale_flag_value: Any,
    guard_fail_status: str | None,
    guard_fail_issue: str | None,
    issues: list[str],
) -> str:
    # A field row whose admission accepted the value is never missing on
    # "not readable" grounds — None is an authored token for some fields
    # and NaN-style artefacts land elsewhere. For everything else the
    # readability check is strict (str / bool / int / finite float).
    field_admitted = is_field_row and admission_issue is None and in_docs
    scalar_readable = readable or (is_field_row and raw is None and field_admitted)
    if (not in_docs) or (not scalar_readable) or (is_field_row and admission_issue == "missing"):
        return "missing"
    if info["as_of"] is None:
        return "unknown_date"
    if info["future_dated"]:
        return "future_dated"
    if stale_flag_value is True:
        return "stale"
    if (
        is_field_row
        and guard_fail_status == "stale"
        and admission_issue == guard_fail_issue
    ):
        return "stale"
    if issues:
        return "partial"
    return "available"


def _build_source(
    *,
    artifact: str,
    path: list[Any],
    clock_semantics: str,
    info: dict[str, Any],
    sha256: str | None,
    us_session: date | None,
) -> dict[str, Any]:
    row_day = _row_day(info, us_session)
    return {
        "artifact": artifact,
        "pointer": _render_pointer(path),
        "sha256": sha256,
        "clock_semantics": clock_semantics,
        "as_of": info["as_of"],
        "precision": info["precision"],
        "age_calendar_days": info["age_calendar_days"],
        "future_dated": info["future_dated"],
        "known_at": None,
        "available_at": None,
        "expected_us_session": us_session.isoformat() if us_session else None,
        "session_relation": _session_relation(row_day, us_session),
        "reference_period": None,
    }


def evidence_rows(
    mapping: dict[str, Any],
    docs: dict[str, Any],
    record: dict[str, dict[str, Any]],
    *,
    analysis_cutoff: datetime,
    us_session: date | None,
) -> list[dict[str, Any]]:
    """Build the 30 evidence rows in mapping order."""
    admission = rco.admit_fields(mapping, docs)
    zero_paths = _zero_path_set(mapping)
    rows: list[dict[str, Any]] = []

    for field in mapping["fields"]:
        field_id = field["field_id"]
        artifact = field["artifact"]
        path = field["path"]
        clock = field["clock"]
        stamp = _resolve_clock(docs, clock["artifact"], clock["path"], clock["semantics"])
        info = date_info(stamp, analysis_cutoff)

        raw = rco.resolve(docs.get(artifact), path)
        in_docs = artifact in docs
        readable = _readable_value(raw)
        admission_issue = admission[field_id]["issue"]

        stale_flag_path = clock.get("stale_flag_path")
        stale_flag_present = stale_flag_path is not None
        if stale_flag_present and in_docs:
            stale_flag_value = rco.resolve(docs[artifact], stale_flag_path)
        else:
            stale_flag_value = None

        zero_match = (artifact, _hashable_path(path)) in zero_paths

        issues = _collect_issues(
            admission_issue=admission_issue,
            stale_flag_value=stale_flag_value,
            stale_flag_present=stale_flag_present,
            zero_match=zero_match,
            raw=raw,
            is_field_row=True,
        )

        guard = field.get("guard") or {}
        status = _compute_status(
            in_docs=in_docs,
            readable=readable,
            raw=raw,
            admission_issue=admission_issue,
            is_field_row=True,
            info=info,
            stale_flag_value=stale_flag_value,
            guard_fail_status=guard.get("fail_status"),
            guard_fail_issue=guard.get("fail_issue"),
            issues=issues,
        )

        if status in ("missing", "unknown_date", "future_dated"):
            values: dict[str, Any] = {}
        else:
            seg = _last_string_segment(path)
            values = {seg: raw} if seg else {}

        if status in ("stale", "partial", "available"):
            owner_verdict: dict[str, Any] | None = {
                "token": raw,
                "verdict_class": field["verdict_class"],
            }
        else:
            owner_verdict = None

        notes: list[str] = []
        if info["as_of"] is not None:
            notes.append(AGE_RULE_NOTE)

        sha256 = record.get(artifact, {}).get("sha256")
        source = _build_source(
            artifact=artifact,
            path=path,
            clock_semantics=clock["semantics"],
            info=info,
            sha256=sha256,
            us_session=us_session,
        )

        rows.append({
            "id": field_id,
            "family_id": _family_id_for(field["evidence_family_id"]),
            "evidence_family_id": field["evidence_family_id"],
            "kind": field["kind"],
            "values": values,
            "unit": None,
            "window": None,
            "scope": "US",
            "owner_verdict": owner_verdict,
            "status": status,
            "issues": issues,
            "notes": notes,
            "currentness_certified": False,
            "source": source,
        })

    for row_spec in mapping["evidence_only"]:
        evidence_id = row_spec["evidence_id"]
        artifact = row_spec["artifact"]
        path = row_spec["path"]
        clock = row_spec["clock"]
        stamp = _resolve_clock(docs, clock["artifact"], clock["path"], clock["semantics"])
        info = date_info(stamp, analysis_cutoff)

        raw = rco.resolve(docs.get(artifact), path)
        in_docs = artifact in docs
        readable = _readable_value(raw)
        own_issue = row_spec.get("issue")

        stale_flag_path = clock.get("stale_flag_path")
        stale_flag_present = stale_flag_path is not None
        if stale_flag_present and in_docs:
            stale_flag_value = rco.resolve(docs[artifact], stale_flag_path)
        else:
            stale_flag_value = None

        zero_match = (artifact, _hashable_path(path)) in zero_paths

        issues = _collect_issues(
            admission_issue=own_issue,
            stale_flag_value=stale_flag_value,
            stale_flag_present=stale_flag_present,
            zero_match=zero_match,
            raw=raw,
            is_field_row=False,
        )

        status = _compute_status(
            in_docs=in_docs,
            readable=readable,
            raw=raw,
            admission_issue=None,
            is_field_row=False,
            info=info,
            stale_flag_value=stale_flag_value,
            guard_fail_status=None,
            guard_fail_issue=None,
            issues=issues,
        )

        if status in ("missing", "unknown_date", "future_dated"):
            values = {}
        else:
            seg = _last_string_segment(path)
            values = {seg: raw} if seg else {}

        notes = []
        note = row_spec.get("note")
        if isinstance(note, str) and note:
            notes.append(note)
        if info["as_of"] is not None:
            notes.append(AGE_RULE_NOTE)

        sha256 = record.get(artifact, {}).get("sha256")
        source = _build_source(
            artifact=artifact,
            path=path,
            clock_semantics=clock["semantics"],
            info=info,
            sha256=sha256,
            us_session=us_session,
        )

        rows.append({
            "id": evidence_id,
            "family_id": _family_id_for(row_spec["evidence_family_id"]),
            "evidence_family_id": row_spec["evidence_family_id"],
            "kind": row_spec["kind"],
            "values": values,
            "unit": None,
            "window": None,
            "scope": "US",
            "owner_verdict": None,
            "status": status,
            "issues": issues,
            "notes": notes,
            "currentness_certified": False,
            "source": source,
        })

    return rows


def state_families(
    mapping: dict[str, Any], evidence: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Ten rows of ``{family_id, coverage, reason, evidence_ids}`` in canonical order."""
    field_state_families: set[str] = set()
    for field in mapping["fields"]:
        sf = EVIDENCE_FAMILY_TO_STATE_FAMILY.get(field["evidence_family_id"])
        if sf is not None:
            field_state_families.add(sf)

    rows: list[dict[str, Any]] = []
    for family_id, authored_cov in STATE_FAMILIES:
        evidence_ids = [r["id"] for r in evidence if r["family_id"] == family_id]
        if family_id == "change_and_outlook":
            coverage = "covered"
        elif family_id not in field_state_families:
            coverage = "not_covered"
        else:
            coverage = authored_cov
        reason = None if coverage == "covered" else "no_admitted_owner_field"
        rows.append({
            "family_id": family_id,
            "coverage": coverage,
            "reason": reason,
            "evidence_ids": evidence_ids,
        })
    return rows


def clock_range(evidence: list[dict[str, Any]]) -> dict[str, Any]:
    """``oldest`` / ``newest`` ``as_of`` for ``source_observation_date`` rows + counts."""
    by_clock: dict[str, int] = {}
    oldest: str | None = None
    newest: str | None = None
    for row in evidence:
        sem = row["source"]["clock_semantics"]
        by_clock[sem] = by_clock.get(sem, 0) + 1
        if sem != "source_observation_date":
            continue
        as_of = row["source"]["as_of"]
        if as_of is None or row["source"]["future_dated"]:
            continue
        head = as_of[:10]
        if oldest is None or head < oldest[:10]:
            oldest = as_of
        if newest is None or head > newest[:10]:
            newest = as_of
    return {"oldest": oldest, "newest": newest, "by_clock_semantics": by_clock}


def _outlook_producer_by_field(mapping: dict[str, Any]) -> dict[str, str]:
    return {f["field_id"]: f["producer"] for f in mapping["fields"]}


def _outlook_evidence_ids(field_id: str | None, evidence_refs: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    if field_id is not None:
        ordered.append(field_id)
        seen.add(field_id)
    for eid in evidence_refs:
        if eid in seen:
            continue
        seen.add(eid)
        ordered.append(eid)
    return ordered


def outlook_paths(
    mapping: dict[str, Any],
    docs: dict[str, Any],
    evidence: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build the nine path cards and what each is waiting on.

    One dict per path in mapping order. Each card carries the five keys
    ``path_id``, ``family``, ``conditions``, ``family_readings`` and ``watch``.
    ``conditions`` lists every authored condition for the card with the keys
    ``condition_id``, ``statement_id``, ``evidence_ids``, ``reading`` and
    ``reason`` (no ``field_id``). ``evidence_ids`` is the condition's field id
    (when it has one) followed by its ``evidence_refs``, deduped and in
    authored order. ``family_readings`` is the reader's roll-up, passed
    through unchanged. ``watch`` lists every condition whose reading is
    ``unknown`` in authored order; each entry carries ``condition_id``,
    ``next_scheduled`` (always ``None`` in this slice) and ``owner_ref``
    (the field's producer, or ``None`` when the condition has no field).

    The function never sorts, ranks, counts or totals paths or readings, and
    adds no key beyond those named.
    """
    admissions = rco.admit_fields(mapping, docs)
    field_ids = {f["field_id"] for f in mapping["fields"]}
    evidence_status: dict[str, str] = {
        r["id"]: r["status"]
        for r in evidence
        if r["id"] in field_ids
    }
    unreadable: dict[str, str] = {
        fid: status
        for fid, status in evidence_status.items()
        if status != "available" and admissions[fid]["admitted"]
    }
    producer_by_field = _outlook_producer_by_field(mapping)
    read = rco.read_paths(mapping, docs, unreadable=unreadable)
    cards: list[dict[str, Any]] = []
    for path_in, path_out in zip(mapping["paths"], read):
        conditions_in = path_in["conditions"]
        conditions_out: list[dict[str, Any]] = []
        watch: list[dict[str, Any]] = []
        for cond_in, cond_out in zip(conditions_in, path_out["conditions"]):
            fid = cond_in["field_id"]
            conditions_out.append({
                "condition_id": cond_in["condition_id"],
                "statement_id": cond_in["statement_id"],
                "evidence_ids": _outlook_evidence_ids(fid, cond_in["evidence_refs"]),
                "reading": cond_out["reading"],
                "reason": cond_out["reason"],
            })
            if cond_out["reading"] == "unknown":
                watch.append({
                    "condition_id": cond_in["condition_id"],
                    "next_scheduled": None,
                    "owner_ref": producer_by_field.get(fid) if fid is not None else None,
                })
        cards.append({
            "path_id": path_in["path_id"],
            "family": path_in["family"],
            "conditions": conditions_out,
            "family_readings": path_out["family_readings"],
            "watch": watch,
        })
    return cards


def pick_baseline(
    previous: dict | None,
    *,
    us_session: date | None,
    session_of,
) -> dict:
    """Pick which earlier regime-outlook read (if any) is this build's baseline.

    Returns either a baseline dict
    ``{"analysis_cutoff": str, "us_session": str, "evidence": {id: snapshot}}``
    or an absence dict ``{"status": "absent", "reason": <word>}``.

    First match wins:
      (a) ``previous`` is None -> absent ``no_earlier_projection``.
      (b) structural checks fail -> absent ``previous_unreadable``.
      (c) ``us_session`` is None and ``previous`` carries a usable stored
          baseline -> a deep copy of it; otherwise absent
          ``us_session_unavailable``.
      (d) ``session_of(previous cutoff)`` is strictly earlier than
          ``us_session`` -> a NEW baseline built from previous's evidence;
          a stored baseline (if any) is ignored.
      (e) ``previous`` carries a stored baseline whose ``us_session`` is
          strictly earlier than ``us_session.isoformat()`` -> a deep copy.
      (f) otherwise absent ``no_earlier_projection``.

    A snapshot entry has exactly the four keys ``values``, ``owner_verdict``,
    ``status`` and ``as_of`` (where ``as_of`` comes from
    ``row["source"]["as_of"]``); missing row keys read as ``None``. The
    function never looks at git, files or the wall clock, and never
    mutates ``previous``; nothing it returns shares an object with it.
    A row id that is not a string, an id that appears twice, and a
    ``session_of`` that returns anything but a plain date all read as
    ``previous_unreadable``.
    """
    if previous is None:
        return {"status": "absent", "reason": "no_earlier_projection"}

    if not isinstance(previous, dict):
        return {"status": "absent", "reason": "previous_unreadable"}
    if previous.get("schema_version") != "regime_outlook.v1":
        return {"status": "absent", "reason": "previous_unreadable"}
    evidence_in = previous.get("evidence")
    if not isinstance(evidence_in, list):
        return {"status": "absent", "reason": "previous_unreadable"}
    seen_ids: set[str] = set()
    for row in evidence_in:
        if not isinstance(row, dict):
            return {"status": "absent", "reason": "previous_unreadable"}
        row_id = row.get("id")
        if not isinstance(row_id, str) or row_id in seen_ids:
            return {"status": "absent", "reason": "previous_unreadable"}
        seen_ids.add(row_id)
        if not isinstance(row.get("source"), dict):
            return {"status": "absent", "reason": "previous_unreadable"}

    cutoff_str = previous.get("analysis_cutoff")
    if not isinstance(cutoff_str, str):
        return {"status": "absent", "reason": "previous_unreadable"}
    try:
        cutoff_dt = datetime.fromisoformat(cutoff_str.replace("Z", "+00:00"))
    except (ValueError, TypeError, OverflowError):
        return {"status": "absent", "reason": "previous_unreadable"}
    if cutoff_dt.tzinfo is None:
        return {"status": "absent", "reason": "previous_unreadable"}

    if us_session is None:
        baseline = previous.get("baseline")
        if (
            isinstance(baseline, dict)
            and isinstance(baseline.get("evidence"), dict)
            and isinstance(baseline.get("us_session"), str)
        ):
            return copy.deepcopy(baseline)
        return {"status": "absent", "reason": "us_session_unavailable"}

    try:
        prev_session = session_of(cutoff_dt)
    except Exception:
        return {"status": "absent", "reason": "previous_unreadable"}
    if not isinstance(prev_session, date) or isinstance(prev_session, datetime):
        return {"status": "absent", "reason": "previous_unreadable"}

    if prev_session < us_session:
        evidence_out: dict[str, dict[str, Any]] = {}
        for row in evidence_in:
            source = row.get("source") or {}
            evidence_out[row.get("id")] = {
                "values": copy.deepcopy(row.get("values")),
                "owner_verdict": copy.deepcopy(row.get("owner_verdict")),
                "status": row.get("status"),
                "as_of": source.get("as_of"),
            }
        return {
            "analysis_cutoff": cutoff_str,
            "us_session": prev_session.isoformat(),
            "evidence": evidence_out,
        }

    baseline = previous.get("baseline")
    if (
        isinstance(baseline, dict)
        and isinstance(baseline.get("evidence"), dict)
        and isinstance(baseline.get("us_session"), str)
        and baseline.get("us_session") < us_session.isoformat()
    ):
        return copy.deepcopy(baseline)

    return {"status": "absent", "reason": "no_earlier_projection"}


# ---------------------------------------------------------------------------
# E1c2 list_changes / CHANGE_KINDS — appended; no existing symbol is changed
# ---------------------------------------------------------------------------


CHANGE_KINDS: tuple[str, ...] = (
    "observation_advanced",
    "value_revised",
    "owner_verdict_changed",
    "became_stale",
    "became_available",
    "became_unavailable",
    "clock_only",
    "mapping_version_changed",
    "unattributed",
)


def list_changes(baseline: Any, evidence: list) -> list[dict[str, Any]]:
    """List what changed between an earlier baseline and the current evidence rows.

    ``evidence`` is the current list of evidence rows. Returns ``[]`` when
    ``baseline`` is not a dict or has no dict under ``evidence``. Otherwise
    walks the current rows in their given order, then ids found only in the
    baseline in sorted order, and appends
    ``{"evidence_id", "change_kind", "from", "to"}`` only where a rule
    below names a kind. ``from`` and ``to`` are deep copies of the snapshot
    entry on each side (``None`` when the id is not on that side).

    A snapshot entry has exactly ``values``, ``owner_verdict``, ``status``
    and ``as_of``; the current-row's snapshot is built from
    ``row["values"]``, ``row["owner_verdict"]``, ``row["status"]`` and
    ``row["source"]["as_of"]`` (the row's ``source["clock_semantics"]``
    drives the same-status branch but is not stored on the snapshot).

    First match wins:

    1. id is on one side only -> ``"mapping_version_changed"``.
    2. ``b["status"] != c["status"]``: ``c["status"] == "stale"`` ->
       ``"became_stale"``; ``c["status"] == "available"`` ->
       ``"became_available"``; ``b["status"]`` in
       ``("available", "stale", "partial")`` and ``c["status"]`` in
       ``("missing", "unknown_date", "future_dated")`` ->
       ``"became_unavailable"``; ``b["status"]`` in
       ``("available", "stale")`` and ``c["status"] == "partial"`` ->
       ``"became_unavailable"``; otherwise ``"unattributed"``.
    3. same status in ``("missing", "unknown_date", "future_dated")``:
       ``"clock_only"`` when ``as_of`` differs, otherwise no entry.
    4. same status otherwise. Let ``changed`` = ``values`` or
       ``owner_verdict`` differ; ``verdict`` = ``owner_verdict`` differs;
       ``moved`` = ``as_of`` differs; ``later`` = both ``as_of`` are
       strings and ``c["as_of"] > b["as_of"]``. If nothing differs -> no
       entry. When the current row's ``source["clock_semantics"]`` is
       exactly ``"source_observation_date"``: not moved and changed ->
       ``"value_revised"``; later and verdict ->
       ``"owner_verdict_changed"``; later and changed ->
       ``"observation_advanced"``; later and not changed ->
       ``"clock_only"``; moved but not later, and changed ->
       ``"unattributed"``; moved but not later, not changed ->
       ``"clock_only"``. For any other clock semantics: changed ->
       ``"unattributed"``; moved only -> ``"clock_only"``.

    The function never mutates its arguments and reads no clock, file or
    network.
    """
    if not isinstance(baseline, dict):
        return []
    baseline_evidence = baseline.get("evidence")
    if not isinstance(baseline_evidence, dict):
        return []

    by_id: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for row in evidence:
        if not isinstance(row, dict):
            continue
        rid = row.get("id")
        if not isinstance(rid, str) or rid in by_id:
            continue
        source = row.get("source") or {}
        by_id[rid] = {
            "snap": {
                "values": copy.deepcopy(row.get("values")),
                "owner_verdict": copy.deepcopy(row.get("owner_verdict")),
                "status": row.get("status"),
                "as_of": source.get("as_of"),
            },
            "clock_semantics": source.get("clock_semantics"),
        }
        order.append(rid)

    baseline_only = sorted(set(baseline_evidence) - set(by_id))
    ids_to_walk: list[str] = list(order) + baseline_only

    entries: list[dict[str, Any]] = []
    for rid in ids_to_walk:
        b = baseline_evidence.get(rid)
        cur = by_id.get(rid)
        c = cur["snap"] if cur is not None else None
        b_copy = copy.deepcopy(b) if b is not None else None
        c_copy = copy.deepcopy(c) if c is not None else None

        # Rule 1: id on one side only.
        if b is None or c is None:
            entries.append({
                "evidence_id": rid,
                "change_kind": "mapping_version_changed",
                "from": b_copy,
                "to": c_copy,
            })
            continue

        # Rule 2: status differs.
        if b["status"] != c["status"]:
            cs = c["status"]
            bs = b["status"]
            if cs == "stale":
                kind = "became_stale"
            elif cs == "available":
                kind = "became_available"
            elif bs in ("available", "stale", "partial") and cs in (
                "missing", "unknown_date", "future_dated"
            ):
                kind = "became_unavailable"
            elif bs in ("available", "stale") and cs == "partial":
                kind = "became_unavailable"
            else:
                kind = "unattributed"
            entries.append({
                "evidence_id": rid,
                "change_kind": kind,
                "from": b_copy,
                "to": c_copy,
            })
            continue

        # Rule 3: same non-data status.
        if b["status"] in ("missing", "unknown_date", "future_dated"):
            if b["as_of"] != c["as_of"]:
                entries.append({
                    "evidence_id": rid,
                    "change_kind": "clock_only",
                    "from": b_copy,
                    "to": c_copy,
                })
            continue

        # Rule 4: same data status.
        changed = b["values"] != c["values"] or b["owner_verdict"] != c["owner_verdict"]
        verdict = b["owner_verdict"] != c["owner_verdict"]
        moved = b["as_of"] != c["as_of"]
        later = (
            isinstance(b["as_of"], str)
            and isinstance(c["as_of"], str)
            and c["as_of"] > b["as_of"]
        )
        if not changed and not moved:
            continue

        clock_semantics = cur["clock_semantics"]
        if clock_semantics == "source_observation_date":
            if not moved and changed:
                kind = "value_revised"
            elif later and verdict:
                kind = "owner_verdict_changed"
            elif later and changed:
                kind = "observation_advanced"
            elif later and not changed:
                kind = "clock_only"
            elif moved and not later and changed:
                kind = "unattributed"
            elif moved and not later and not changed:
                kind = "clock_only"
            else:
                kind = None
        else:
            if changed:
                kind = "unattributed"
            elif moved:
                kind = "clock_only"
            else:
                kind = None

        if kind is not None:
            entries.append({
                "evidence_id": rid,
                "change_kind": kind,
                "from": b_copy,
                "to": c_copy,
            })

    return entries


# ---------------------------------------------------------------------------
# E1c1 compose_outlook — the assembled projection (appended; no existing
# symbol is touched)
# ---------------------------------------------------------------------------


def compose_outlook(
    mapping: dict[str, Any],
    input_bytes: dict[str, bytes | None],
    *,
    mapping_sha256: str,
    analysis_cutoff: datetime,
    built_at: datetime,
    session_of,
    previous: dict | None = None,
) -> dict[str, Any]:
    """Assemble the regime-outlook projection dict from owner bytes.

    ``mapping_sha256`` is the producer-supplied digest of the mapping bytes
    and is stored verbatim. ``analysis_cutoff`` and ``built_at`` must be
    timezone-aware datetimes (a naive value raises ``ValueError``).
    ``session_of`` resolves ``analysis_cutoff`` to a US-session date; an
    exception is caught and the US session is treated as unavailable.
    ``previous`` is deep-copied before being read so it is never mutated,
    and the returned dict never shares a nested object with ``previous``
    or ``input_bytes``.

    The function calls the existing helpers exactly as ``_build_at_pin``
    does (``read_inputs`` then ``evidence_rows``) and uses ``pick_baseline``
    for the baseline and ``list_changes`` for the change list. An absent
    baseline (``{"status": "absent", ...}``) yields ``[]`` for changes.

    The return survives ``json.loads(json.dumps(...))`` unchanged; the only
    clock artefacts are UTC ISO strings, and the authority dict holds only
    booleans. The function reads no wall clock, no file and no network.
    """
    if analysis_cutoff.tzinfo is None:
        raise ValueError("analysis_cutoff must be timezone-aware")
    if built_at.tzinfo is None:
        raise ValueError("built_at must be timezone-aware")

    try:
        us_session = session_of(analysis_cutoff)
    except Exception:
        us_session = None

    previous_safe = copy.deepcopy(previous) if previous is not None else None

    docs, record = read_inputs(mapping, input_bytes)
    evidence = evidence_rows(
        mapping,
        docs,
        record,
        analysis_cutoff=analysis_cutoff,
        us_session=us_session,
    )
    families = state_families(mapping, evidence)
    evidence_clock_range = clock_range(evidence)
    conditional_paths = outlook_paths(mapping, docs, evidence)
    baseline = pick_baseline(
        previous_safe, us_session=us_session, session_of=session_of
    )
    changes = list_changes(baseline, evidence)

    return {
        "schema_version": "regime_outlook.v1",
        "scope": "US",
        "analysis_cutoff": analysis_cutoff.astimezone(timezone.utc).isoformat(),
        "built_at": built_at.astimezone(timezone.utc).isoformat(),
        "mapping_version": mapping["mapping_version"],
        "mapping_sha256": mapping_sha256,
        "inputs": record,
        "evidence_clock_range": evidence_clock_range,
        "families": families,
        "evidence": evidence,
        "conditional_paths": conditional_paths,
        "baseline": baseline,
        "changes": changes,
        "historical_comparisons": {
            "status": "absent",
            "reason": "history_not_qualified",
            "qualification": {},
        },
        "forecast_distributions": {
            "status": "absent",
            "reason": "no_admitted_owner",
        },
        "conditional_exposures": {
            "status": "absent",
            "reason": "no_admitted_owner",
        },
        "authority": {
            "may_rank": False,
            "may_gate": False,
            "may_size": False,
            "may_trade": False,
            "may_forecast": False,
            "may_escalate": False,
        },
        "tier": "display_research",
        "notes": [AGE_RULE_NOTE],
    }
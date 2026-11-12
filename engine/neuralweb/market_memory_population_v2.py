"""Outcome-blind reader for the existing, disjoint W2C experience-v2 owner.

This is a native v2 diagnostic, never a v1 population-manifest adapter.  Rights
precede owner I/O and are rechecked with the real registration before disclosure.
No production policy, API, writer or study admission is installed here.

V2's records are not a content-addressed experience ledger.  We validate bounded
record bytes, close admitted pins through the incumbent technical/source owners,
and recheck our sampled local inputs.  This does not authenticate external custody,
natural issuance, an independent registration-publication clock, or ABA resistance.
Historical abstention reasons remain assertions; current absence cannot prove them.
"""

from __future__ import annotations

import json
import os
import re
import stat
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path

from engine.neuralweb import market_memory as memory
from engine.neuralweb import market_memory_experience_accrual as accrual
from engine.neuralweb import market_memory_population as population
from engine.neuralweb import market_memory_source_kernel as kernel
from engine.neuralweb import market_memory_sources_spy as sources
from lib import nyse_calendar
from scripts import accrue_market_memory_spy_experience_v2 as owner
from scripts import capture_market_memory_technicals_v2 as technical

SCHEMA = "market_memory.spy_experience_v2_population.v1"
MAX_SESSIONS = 256  # diagnostic work bound, not a new pilot/sample definition
MAX_RECORD_BYTES = 16 * 1024
_BASE = {"schema", "session", "registration_id", "disposition", "recorded_at"}
_REASONS = {"no_opportunity_eligible_sealed_bar", "no_technicals_v2_capture", "lookback_incomplete"}


class PopulationV2Error(ValueError):
    """An owner input cannot support the requested v2 diagnostic."""


def _root(value, *, leaf=None):
    raw = Path(value).expanduser()
    if not raw.is_absolute() or raw != Path(os.path.abspath(raw)):
        raise PopulationV2Error("absolute normalized population roots required")
    if leaf is not None and (raw.name != leaf or raw.parent.name != "state"):
        raise PopulationV2Error("wrong native v2 owner root")
    return raw


def _safe_parents(path):
    for parent in (path, *path.parents):
        try:
            metadata = parent.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(metadata.st_mode):
            raise PopulationV2Error("symlinked population input refused")


def _session(value):
    if type(value) is not str or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise PopulationV2Error("exact XNYS session required")
    result = date.fromisoformat(value)
    if not nyse_calendar.is_session(result):
        raise PopulationV2Error("exact XNYS session required")
    return result


def _utc(value):
    try:
        result, _ = kernel._parse_utc(value, field="v2 population clock")
        return result
    except (kernel.MarketMemorySourceError, ValueError, TypeError) as exc:
        raise PopulationV2Error("invalid v2 population clock") from exc


def _json(body):
    try:
        value = json.loads(body.decode("utf-8"), object_pairs_hook=kernel._reject_duplicate_pairs,
                           parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
        if type(value) is not dict:
            raise ValueError("not an object")
        return value
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise PopulationV2Error("invalid bounded v2 JSON") from exc


def read_population_v2(repository_root, *, experience_root, source_root,
                       technicals_v2_root, through_session, policy):
    """Read one bounded metadata-only census; no writer or outcome path is called.

    The existing PopulationAccessPolicy explicitly authorizes the native roots
    and registration.  ``store_id=None`` is intentional: v2 has no native
    content-addressed experience store identity.  A site entitlement is not a
    policy. Source and technical roots must be the existing disjoint siblings.
    """
    repository = _root(repository_root)
    experience = _root(experience_root, leaf="experience-v2")
    source = _root(source_root, leaf="sources-spy-rest-v1")
    tech = _root(technicals_v2_root, leaf="technicals-v2")
    if source.parent != experience.parent or tech.parent != experience.parent:
        raise PopulationV2Error("native v2 roots must be disjoint state siblings")
    through = _session(through_session)
    observed = datetime.now(timezone.utc)
    # No unelapsed session can be called missing, even with an explicit cutoff.
    closed = datetime.combine(through + timedelta(days=1), datetime.min.time(),
                              tzinfo=timezone.utc) + timedelta(hours=4, minutes=45)
    if closed > observed:
        raise PopulationV2Error("through-session admission window has not elapsed")

    def permit(registration_id=None):
        return population._require_grant(
            policy, repository_root=str(repository), experience_root=str(experience),
            through_session=through_session, registration_id=registration_id, store_id=None)

    permit()  # all filesystem inspection and reads occur after this rights check
    snapshots, absent = {}, set()

    def read(path, limit):
        _safe_parents(path)
        try:
            body = kernel._read_bounded(path, limit=limit, label="v2 population input").body
        except kernel.MarketMemorySourceError as exc:
            raise PopulationV2Error("v2 population input unavailable or unsafe") from exc
        snapshots[path] = (limit, body)
        return body

    reg_body = read(repository / "config/market_memory_spy_experience_registration.v2.json", 64 * 1024)
    registration = _json(reg_body)
    spec = accrual._expected_registration_spec_v2()
    spec_body = kernel._canonical_bytes(spec)
    digest = sha256(spec_body).hexdigest()
    if (set(registration) != {"schema", "spec", "registration_id", "content_sha256", "content_bytes"}
            or registration["schema"] != owner.REGISTRATION_SCHEMA_V2
            or kernel._canonical_bytes(registration["spec"]) != spec_body
            or registration["content_sha256"] != digest
            or type(registration["content_bytes"]) is not int
            or registration["content_bytes"] != len(spec_body)
            or registration["registration_id"] != "mmspyexpreg_" + digest):
        raise PopulationV2Error("v2 registration content identity mismatch")
    registration_id = registration["registration_id"]
    permit(registration_id)
    calendar_body = read(repository / spec["calendar"]["owner_path"], 128 * 1024)
    loaded_calendar = read(Path(nyse_calendar.__file__).resolve(), 128 * 1024)
    if (sha256(calendar_body).hexdigest() != spec["calendar"]["owner_sha256"]
            or loaded_calendar != calendar_body):
        raise PopulationV2Error("declared and executing XNYS calendar source differ")
    marker = read(experience / owner.V2_INSTALL_MARKER_FILENAME, 128)
    installed = _utc(marker.decode("utf-8").strip())
    if installed > observed:
        raise PopulationV2Error("installation marker is in the future")
    if (through - installed.date()).days > 2 * MAX_SESSIONS:
        raise PopulationV2Error("v2 activation interval exceeds diagnostic work bound")
    # Match actual check_activation: it excludes install calendar day entirely.
    # Do not silently repair its pre-open install discrepancy or fabricate clocks.
    expected = nyse_calendar.sessions_between(installed.date() + timedelta(days=1), through)
    if not expected or len(expected) > MAX_SESSIONS:
        raise PopulationV2Error("v2 denominator is empty or exceeds diagnostic bound")
    head_body = read(experience / "EXP_V2_HEAD.json", 4096)
    head = _json(head_body)
    if (set(head) != {"schema", "registration_id", "latest_session", "latest_disposition"}
            or head["schema"] != owner.EXPERIENCE_V2_HEAD_SCHEMA
            or head["registration_id"] != registration_id
            or head["latest_disposition"] not in {"admitted", "abstained"}):
        raise PopulationV2Error("v2 HEAD binding mismatch")
    latest = _session(head["latest_session"])
    if latest < expected[0] or latest > observed.date():
        raise PopulationV2Error("v2 HEAD session outside activation/read boundary")
    rows = []
    for session in expected:
        path = experience / "records" / f"{session.isoformat()}.json"
        _safe_parents(path)
        try:
            path.lstat()
        except FileNotFoundError:
            if session == latest:
                raise PopulationV2Error("v2 HEAD latest record is absent")
            absent.add(path)
            rows.append({"session": session.isoformat(), "disposition": "unrecorded",
                         "reason": "expected_v2_session_without_record", "source_closure": "not_applicable"})
            continue
        body = read(path, MAX_RECORD_BYTES)
        record = _json(body)
        if body != kernel._canonical_bytes(record):
            raise PopulationV2Error("v2 record is not canonical")
        recorded = _utc(record.get("recorded_at"))
        opened = datetime.combine(session + timedelta(days=1), datetime.min.time(),
                                  tzinfo=timezone.utc) + timedelta(hours=4, minutes=30)
        if (record.get("schema") != owner.EXPERIENCE_V2_RECORD_SCHEMA
                or record.get("session") != session.isoformat()
                or record.get("registration_id") != registration_id
                or not opened <= recorded < opened + timedelta(minutes=15)
                or recorded > observed or session > latest):
            raise PopulationV2Error("v2 record identity or admission clock mismatch")
        disposition = record.get("disposition")
        row = {"session": session.isoformat(), "disposition": disposition,
               "recorded_at": record["recorded_at"], "record_bytes": len(body),
               "record_sha256": sha256(body).hexdigest()}
        if disposition == "abstained":
            if set(record) != _BASE | {"reason"} or record["reason"] not in _REASONS:
                raise PopulationV2Error("unsupported v2 abstention record")
            row.update(reason=record["reason"], source_closure="historical_absence_not_reproven")
        elif disposition == "admitted":
            if set(record) != _BASE | {"source_generation_id", "technical_capture_id", "feature"}:
                raise PopulationV2Error("unsupported v2 admitted record")
            capture = technical.read_latest_capture_for_session(tech, session=session)
            if (capture is None or capture["capture_id"] != record["technical_capture_id"]
                    or capture["source_generation_id"] != record["source_generation_id"]):
                raise PopulationV2Error("record differs from published technical/source pin")
            sealed = sources.read_verified_spy_rest_bar(
                source, session=session, generation_id=record["source_generation_id"])
            if sealed is None:
                raise PopulationV2Error("record source pin has no eligible sealed session")
            technical.validate_capture_source_binding(capture, sealed, session=session, as_of=recorded)
            feature = capture["feature_object"]
            expected_feature = {"session": session.isoformat(), "profile": spec["profile"],
                "ticker": "SPY", "regular_session_close_authenticated": feature["regular_session_close_authenticated"],
                "price_basis": feature["price_basis"],
                "price_raw_close_ratio_20_sessions": feature["state"]["price"]["raw_close_ratio_20_sessions"]}
            if (expected_feature["price_raw_close_ratio_20_sessions"] is None
                    or kernel._canonical_bytes(record["feature"]) != kernel._canonical_bytes(expected_feature)):
                raise PopulationV2Error("record feature differs from exact owner projection")
            row.update(source_generation_id=record["source_generation_id"],
                       technical_capture_id=record["technical_capture_id"],
                       source_closure="published_exact_pin_and_projection_validated")
        else:
            raise PopulationV2Error("unsupported v2 disposition")
        if session == latest and disposition != head["latest_disposition"]:
            raise PopulationV2Error("v2 HEAD disposition differs from record")
        rows.append(row)
    # No sampled file may change during closure or disappear/reappear unnoticed.
    # This deliberately does not claim resistance to an unobserved ABA sequence.
    for path, (limit, body) in snapshots.items():
        _safe_parents(path)
        if kernel._read_bounded(path, limit=limit, label="v2 population final input").body != body:
            raise PopulationV2Error("v2 input changed during population read")
    for path in absent:
        _safe_parents(path)
        try:
            path.lstat()
        except FileNotFoundError:
            continue
        raise PopulationV2Error("v2 absent record appeared during population read")
    permit(registration_id)
    counts = Counter(row["disposition"] for row in rows)
    result = {"schema": SCHEMA, "registration_id": registration_id,
        "through_session": through_session, "expected_sessions": [s.isoformat() for s in expected],
        "activation": {"install_marker": installed.isoformat().replace("+00:00", "Z"),
            "basis": "existing_v2_owner_excludes_install_calendar_day",
            "strict_open_rule_conformance_authenticated": False,
            "registration_publication_clock_authenticated": False},
        "counts": {"expected": len(expected), "recorded": len(expected) - counts["unrecorded"],
            **{name: counts[name] for name in ("admitted", "abstained", "unrecorded")}},
        "rows": rows, "authority": dict(memory.AUTHORITY),
        "claims": {"native_v2_only": True, "record_bytes_and_registration_validated": True,
            "experience_content_addressed_store_authenticated": False,
            "external_custody_authenticated": False, "natural_issuance_authenticated": False,
            "external_clock_authenticated": False, "aba_resistance_authenticated": False,
            "comparison_performed": False, "training_eligible": False,
            "promotion_eligible": False, "operational_admission": False}}
    return result

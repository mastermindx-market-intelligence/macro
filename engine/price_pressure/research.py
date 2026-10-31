"""Bounded retrospective reads of the existing DRL display artifact.

The capture clock proves only that this reader had these bytes by that time.
Neither the event date, harvest session nor artifact build time proves historical
availability. No ledger write, collection, residual calculation or ranking occurs.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import stat

SCHEMA = "price_pressure.captured_event.v1"
SOURCE = "data/price_pressure/latest.json"
MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 64
_SYMBOL = re.compile(r"[A-Z0-9][A-Z0-9.-]{0,14}")
_AUTHORITY = {"can_rank": False, "can_size": False, "can_gate": False,
              "can_originate_signal": False, "can_escalate": False}
_FAMILIES = {"earnings-filing", "other-filing", "no-filing", "filing-coverage-unknown"}


class CaptureUnavailable(ValueError):
    """Stable refusal token; no paths, raw source or request values in errors."""


def _day(value: object) -> str:
    if not isinstance(value, str):
        raise CaptureUnavailable("invalid_native_date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise CaptureUnavailable("invalid_native_date") from None
    if parsed.isoformat() != value:
        raise CaptureUnavailable("invalid_native_date")
    return value


def _instant(value: object) -> datetime:
    if not isinstance(value, str):
        raise CaptureUnavailable("invalid_build_clock")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise CaptureUnavailable("invalid_build_clock") from None
    if "T" not in value or parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CaptureUnavailable("invalid_build_clock")
    return parsed.astimezone(timezone.utc)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _object(pairs: list[tuple]) -> dict:
    out = {}
    for key, value in pairs:
        if key in out:
            raise CaptureUnavailable("duplicate_json_key")
        out[key] = value
    return out


def _read(root: Path) -> tuple[bytes, datetime]:
    try:
        fd = os.open(Path(root) / SOURCE, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= MAX_BYTES:
                raise CaptureUnavailable("snapshot_bound_invalid")
            chunks, remaining = [], MAX_BYTES + 1
            while remaining:
                chunk = os.read(fd, min(remaining, 65536))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            captured_at = _utc_now()
            after = os.fstat(fd)
            signature = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
            raw = b"".join(chunks)
            if signature(before) != signature(after) or len(raw) != before.st_size:
                raise CaptureUnavailable("snapshot_changed_during_read")
            return raw, captured_at
        finally:
            os.close(fd)
    except OSError:
        raise CaptureUnavailable("snapshot_unavailable") from None


def capture_event(root: Path, *, event_date: str, ticker: str, side: str) -> dict:
    """Read one exact native event from one coherent, bounded snapshot.

    The captured digest describes the whole artifact, not a native immutable
    event object or an independent corroborating source. No caller-supplied
    timestamp, identity bridge, path or entitlement is accepted.
    """
    event_date = _day(event_date)
    if (not isinstance(ticker, str) or not _SYMBOL.fullmatch(ticker)
            or not isinstance(side, str) or side not in {"up", "down"}):
        raise CaptureUnavailable("invalid_event_key")
    raw, captured_at = _read(Path(root))
    try:
        source = json.loads(raw, object_pairs_hook=_object,
                            parse_constant=lambda _: (_ for _ in ()).throw(CaptureUnavailable("nonfinite_json")))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
        raise CaptureUnavailable("invalid_snapshot_json") from None
    if not isinstance(source, dict) or source.get("schema") != "price_pressure.v1":
        raise CaptureUnavailable("snapshot_schema_invalid")
    authority = source.get("authority")
    if (source.get("display_only") is not True or not isinstance(authority, dict)
            or set(authority) != set(_AUTHORITY) or any(v is not False for v in authority.values())):
        raise CaptureUnavailable("snapshot_authority_invalid")
    generated = source.get("generated_utc")
    if _instant(generated) > captured_at:
        raise CaptureUnavailable("build_after_capture")
    groups = [source.get("open_events"), source.get("recently_resolved")]
    if any(not isinstance(rows, list) for rows in groups) or sum(map(len, groups)) > MAX_ROWS:
        raise CaptureUnavailable("event_population_invalid")
    rows = groups[0] + groups[1]
    if any(not isinstance(row, dict) for row in rows):
        raise CaptureUnavailable("event_population_invalid")
    matches = [r for r in rows if (r.get("date"), r.get("ticker"), r.get("side"))
               == (event_date, ticker, side)]
    if len(matches) != 1:
        raise CaptureUnavailable("event_not_found" if not matches else "event_key_conflicted")
    row = matches[0]
    if event_date > captured_at.date().isoformat():
        raise CaptureUnavailable("event_after_capture")
    values = {}
    for key in ("ret", "peer_ret", "resid", "resid_z"):
        value = row.get(key)
        try:
            finite = type(value) in (int, float) and math.isfinite(value)
        except OverflowError:
            finite = False
        if not finite:
            raise CaptureUnavailable("native_value_unavailable")
        values[key] = value
    if not isinstance(row.get("peer_basis"), str) or row["peer_basis"] not in {"market", "sector"}:
        raise CaptureUnavailable("native_basis_invalid")
    covered, family = row.get("edgar_covered"), row.get("family")
    if (type(covered) is not bool or not isinstance(family, str) or family not in _FAMILIES
            or (not covered and family != "filing-coverage-unknown")):
        raise CaptureUnavailable("filing_coverage_incoherent")
    harvested = row.get("harvested_asof")
    if harvested is not None:
        if _day(harvested) < event_date or harvested > captured_at.date().isoformat():
            raise CaptureUnavailable("harvest_session_incoherent")
    version = row.get("engine_version")
    if version is not None and (not isinstance(version, str) or not version.strip() or len(version) > 128):
        raise CaptureUnavailable("native_version_invalid")
    era = row.get("era")
    if not isinstance(era, str) or era not in {"forward", "gap", "backfill"}:
        raise CaptureUnavailable("native_era_invalid")
    return {
        "schema": SCHEMA,
        "native_identity": {"date": event_date, "ticker": ticker, "side": side},
        "source": {"artifact": SOURCE, "schema": "price_pressure.v1",
                   "snapshot_sha256": sha256(raw).hexdigest(), "bytes": len(raw),
                   "generated_utc": generated},
        "capture": {"captured_at": captured_at.isoformat().replace("+00:00", "Z"),
                    "clock_class": "system_recorded", "historical_availability": "unknown",
                    "scope": "retrospective_captured_read"},
        "native": {**values, "peer_basis": row["peer_basis"], "family": family,
                   "edgar_covered": covered, "era": era,
                   "harvested_asof": harvested, "engine_version": version},
        "authority": dict(_AUTHORITY),
    }


def validate_capture(capture: object) -> dict:
    """Validate a retained reader receipt, not authenticate caller-provided bytes.

    capture_event is the native observation boundary. Validation cannot establish
    its provenance anew, or manufacture original arrival time from its contents.
    """
    try:
        raw = json.dumps(capture, allow_nan=False, separators=(",", ":"))
        if len(raw) > 8192:
            raise ValueError
        out = json.loads(raw)
        expected = {
            "root": {"schema", "native_identity", "source", "capture", "native", "authority"},
            "native_identity": {"date", "ticker", "side"},
            "source": {"artifact", "schema", "snapshot_sha256", "bytes", "generated_utc"},
            "capture": {"captured_at", "clock_class", "historical_availability", "scope"},
            "native": {"ret", "peer_ret", "resid", "resid_z", "peer_basis", "family", "edgar_covered", "era", "harvested_asof", "engine_version"},
        }
        if not isinstance(out, dict) or set(out) != expected["root"] or out["schema"] != SCHEMA:
            raise ValueError
        for key in ("native_identity", "source", "capture", "native"):
            if not isinstance(out[key], dict) or set(out[key]) != expected[key]:
                raise ValueError
        identity, source, clock, native = (out[k] for k in ("native_identity", "source", "capture", "native"))
        event_date = _day(identity["date"])
        if (not isinstance(identity["ticker"], str) or not _SYMBOL.fullmatch(identity["ticker"])
                or identity["side"] not in ("up", "down")):
            raise ValueError
        if (source["artifact"] != SOURCE or source["schema"] != "price_pressure.v1"
                or not isinstance(source["snapshot_sha256"], str)
                or re.fullmatch(r"[a-f0-9]{64}", source["snapshot_sha256"]) is None
                or type(source["bytes"]) is not int or not 0 < source["bytes"] <= MAX_BYTES):
            raise ValueError
        captured = _instant(clock["captured_at"])
        if (clock != {"captured_at": captured.isoformat().replace("+00:00", "Z"),
                      "clock_class": "system_recorded", "historical_availability": "unknown",
                      "scope": "retrospective_captured_read"}
                or _instant(source["generated_utc"]) > captured
                or event_date > captured.date().isoformat()):
            raise ValueError
        for key in ("ret", "peer_ret", "resid", "resid_z"):
            if type(native[key]) not in (int, float) or not math.isfinite(native[key]):
                raise ValueError
        if (native["peer_basis"] not in ("market", "sector")
                or type(native["edgar_covered"]) is not bool or native["family"] not in tuple(_FAMILIES)
                or not native["edgar_covered"] and native["family"] != "filing-coverage-unknown"
                or native["era"] not in ("forward", "gap", "backfill")):
            raise ValueError
        harvest, version = native["harvested_asof"], native["engine_version"]
        if harvest is not None and not event_date <= _day(harvest) <= captured.date().isoformat():
            raise ValueError
        if version is not None and (not isinstance(version, str) or not version.strip() or len(version) > 128):
            raise ValueError
        if (not isinstance(out["authority"], dict) or set(out["authority"]) != set(_AUTHORITY)
                or any(v is not False for v in out["authority"].values())):
            raise ValueError
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
        raise CaptureUnavailable("capture_contract_invalid") from None
    return out


def compose_captured_evidence(capture: dict) -> dict:
    """Return K1/K3 inputs for K5 over ONE already captured native event.

    No owner reread, canonical identity resolution, policy grant, source body
    copy into K1, store or lifecycle mutation occurs. The caller retains the
    original capture; its hash identifies the captured artifact, not a new fact.
    """
    from lib import evidence_foundation as ef
    from lib import opportunity_evidence as oe

    capture = validate_capture(capture)
    identity, source, clock, native = (capture[k] for k in ("native_identity", "source", "capture", "native"))
    captured_at = clock["captured_at"]
    subject = {"key_type": "drl_event_key", "key": json.dumps(
        [identity[k] for k in ("date", "ticker", "side")], separators=(",", ":"))}
    authority = dict(ef.ALL_FALSE_AUTHORITY)
    clocks = [
        {"class": "world_valid", "field": "native_identity.date", "value_state": "known", "value": identity["date"], "grain": "date"},
        {"class": "belief_or_build", "field": "source.generated_utc", "value_state": "known", "value": source["generated_utc"], "grain": "datetime"},
        {"class": "system_recorded", "field": "capture.captured_at", "value_state": "known", "value": captured_at, "grain": "datetime"},
    ]
    cutoff = {"state": "known", "value": captured_at, "grain": "datetime"}
    cutoffs = {c: dict(cutoff) if c in {"world_valid", "belief_or_build", "system_recorded"}
               else {"state": "unknown", "value": None, "grain": "datetime"}
               for c in ef.load_vocabulary()["clock_classes"]}
    cutoffs["world_valid"] = {"state": "known", "value": captured_at[:10], "grain": "date"}
    owner = ef.load_vocabulary()["owner_stores"]["price_pressure.event"]
    reference = {
        "schema": ef.SCHEMA, "version": ef.VERSION,
        "object_class": "derived_view", "owner_store": "price_pressure.event",
        "native_identity": identity, "native_schema": SCHEMA,
        "native_digest": {"state": "known", "sha256": source["snapshot_sha256"]},
        "coverage_class": "source_release_snapshot_only",
        "freshness": {"state": "unknown", "clock_field": None, "policy_id": None},
        "rights": {"state": "unknown", "policy_id": None}, "authority_class": "deterministic",
        "subject": subject, "secondary_subjects": [], "clocks": clocks,
        "provenance": {"pointer_only": True, "body_embedded": False, "owner_reader": owner["reader"],
                       "owner_reader_kind": owner["reader_kind"], "pointer": ef.render_owner_pointer(owner, identity)},
        "relations": [], "missingness": {"state": "present", "reason": None, "zero_substituted": False},
        "correction": {"kind": "none", "predecessor_reference_ids": [], "clock_field": None,
                       "chronology_state": "not_applicable", "append_only": True, "mutates_predecessor": False},
        "replay": {"mode": "retrospective_research", "cutoffs": cutoffs, "code_revision": None,
                   "input_digest": source["snapshot_sha256"], "vintage_state": "owner_native"},
        "authority": authority,
    }
    reference["reference_id"] = ef.compute_reference_id(reference)
    reference = ef.validate_reference(reference)
    ref_id = reference["reference_id"]
    consumer = {"workstream": "WS:ALPHA-INTELLIGENCE-INTEGRATION", "job": "captured DRL event research",
                "output_contract": "opportunity_case.research.v1"}
    block = {
        "schema": ef.BLOCK_SCHEMA, "version": ef.VERSION, "block_key": "drl_event_research",
        "consumer": consumer, "supported_claim": {"kind": "claim", "state": "partial",
            "text": "Captured native event-day residual and filing coverage; original availability and economic cause remain unknown."},
        "reference_ids": [ref_id], "owner_stores": ["price_pressure.event"], "object_classes": ["derived_view"],
        "evidence_class": "deterministic", "clock_summary": {"collapsed": False, "entries": [{"reference_id": ref_id, **c} for c in clocks]},
        "coverage": {"state": "unknown", "total": 1, "included": 1, "excluded": 0, "missing": 0,
                     "stale": 0, "rights_blocked": 0, "fallback": 0,
                     "basis": "one captured source version; original availability, freshness policy and rights policy unknown",
                     "reconciliation_state": "reconciled"},
        "uncertainty": {"state": "none", "probability": None, "derivation_ref": None, "calibration_ref": None},
        "dependence": {"state": "independent", "independent_evidence_count": 1, "groups": []},
        "conflict_correction": {"state": "none", "reference_ids": []},
        "next_observable": {"state": "unknown", "description": None, "owner_clock_field": None},
        "permitted_consumers": [consumer["output_contract"]],
        "lineage": {"state": "original", "predecessor_block_ids": [], "invalidated_by_reference_ids": []}, "authority": authority,
    }
    block["evidence_block_id"] = ef.compute_block_id(block)
    block = ef.validate_block(block, references={ref_id: reference})
    recipe = {
        "schema": ef.RECIPE_SCHEMA, "version": ef.VERSION, "recipe_name": "drl_event_research.v1",
        "consumer": consumer, "subject_instance": subject, "subject_key_types": ["drl_event_key"],
        "block_specs": [{"order": 1, "block_key": "drl_event_research", "requirement": "required",
                         "allowed_owner_stores": ["price_pressure.event"], "allowed_object_classes": ["derived_view"],
                         "evidence_class": "deterministic", "minimum_references": 1, "maximum_references": 1,
                         "on_absent": "refuse", "output_fields": ["reality.drl_event"]}],
        "identity_joins": [],
        "refusal_degradation_rules": [
            {"code": code, "condition": condition, "effect": effect} for code, condition, effect in [
                ("REQUIRED_BLOCK_ABSENT", "required captured event block absent", "refuse"),
                ("OPTIONAL_BLOCK_ABSENT", "optional block absent", "degrade"),
                ("IDENTITY_UNRESOLVED", "native event tuple unresolved", "refuse"),
                ("RIGHTS_BLOCKED", "required reference rights blocked", "refuse"),
                ("CONFLICTED_REQUIRED_BLOCK", "required event conflicted", "abstain"),
            ]],
        "dedup_dependence_rules": {"automatic_relation_types": [], "nonautomatic_relation_types": ["exact_duplicate", "same_fact", "same_event", "corroborates", "contradicts", "shares_upstream", "corrects", "supersedes", "projects"], "reference_count_implies_independence": False},
        "output_mappings": [{"output_field": "reality.drl_event", "block_key": "drl_event_research", "when_unavailable": "refuse"}],
        "integrity": {"denominator_receipt_required": True, "dominant_degradation_required": True,
                      "partial_may_look_complete": False, "confidence_requires_receipt": True,
                      "correction_recompilation_required": True, "owner_payload_copy_allowed": False}, "authority": authority,
    }
    recipe["recipe_id"] = ef.compute_recipe_id(recipe)
    recipe = ef.validate_recipe(recipe)
    ef.compile_recipe(recipe, blocks=[block], references={ref_id: reference})
    receipt = {"schema": "drl_captured_read.v1", "snapshot_sha256": source["snapshot_sha256"],
               "captured_at": captured_at, "event_date": identity["date"], "ticker": identity["ticker"],
               "side": identity["side"], "historical_availability": "unknown",
               "harvested_asof": native["harvested_asof"], "engine_version": native["engine_version"]}
    owner_ref = {"owner": "engine/price_pressure/", "artifact": SOURCE,
                 "reader": "engine.price_pressure.research.capture_event", "evidence_ref_id": ref_id}
    slots = []
    for construct, value, basis in [
        ("drl_resid_shock", {k: native[k] for k in ("ret", "peer_ret", "resid", "resid_z")}, {"peer_basis": native["peer_basis"]}),
        ("drl_filing_coverage", native["family"], None),
    ]:
        slots.append({"construct": construct, "state": "observed", "value_or_null": value,
                      "asof": {"value": identity["date"], "grain": "date"},
                      "known_at": {"value": captured_at, "grain": "datetime"}, "basis": basis,
                      "captured_read": receipt, "owner_ref": owner_ref,
                      "coverage_flag": {"state": "partial", "note": "captured display subset; original historical availability unknown"}})
    recorded = {"value": captured_at, "grain": "datetime", "clock_class": "system_recorded", "native_field": "captured_at", "state": "known"}
    asof = {"value": captured_at, "grain": "datetime", "t0_source": "drl_captured_read", "t0_mode": "retrospective_research",
            "t0_evidence_ref": {"owner_store": "price_pressure.event", "native_identity": identity,
                                "native_digest": reference["native_digest"], "recorded_clock": recorded}}
    vector = oe.compose_vector({"subject_type": "us_listing_symbol", "value": identity["ticker"],
                                "identity_state": "single_owner_native", "identity_bridge": None}, asof, slots,
                               generated_at=captured_at, permitted_consumers=["opportunity_case_k5"])
    if oe.validate_vector(vector):
        raise CaptureUnavailable("captured_vector_invalid")
    return {"recipe": recipe, "blocks": [block], "references": {ref_id: reference}, "vector": vector}

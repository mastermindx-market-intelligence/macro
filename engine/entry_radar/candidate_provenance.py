"""Prospective, descriptive quote/observation/identity/commit composition.

Only new journal admissions/frozen observations carry these receipts. Provider
namespace is declared by the native endpoint parser, not authenticated by this
module. No historical repair, detector input, lifecycle, spool read/write, rights
or live-evidence eligibility is supplied here.
"""
from datetime import datetime, timedelta, timezone, date
from hashlib import sha256
import json
import re

from lib import evidence_foundation as ef
from lib.quote_native_metadata import copy_native_metadata

SCHEMA = "entry_radar.quote_candidate_provenance/v1"


class CandidateProvenanceUnavailable(ValueError):
    """Closed refusal token, without source bodies."""


def _need(ok, code):
    if not ok:
        raise CandidateProvenanceUnavailable(code)


def _instant(value):
    from engine.company_intelligence.opportunity_qualification import _instant as parse
    try:
        return parse(value)
    except ValueError:
        raise CandidateProvenanceUnavailable("quote_clock_unknown") from None


def _hash(value):
    return sha256(ef.canonical_json_bytes(value)).hexdigest()


def _sampled_point(record, observation):
    """Same last-lawful-minute ordering as JournalRecord.tape/sample_session_path.

    Stable ordering retains the last point in a minute, just as the native tape.
    No close-return computation or indicator replay is performed.
    """
    from engine.entry_radar import challengers as ch
    cutoff = _instant(observation["observed_at"])
    opening, closing = ch.session_window_et(date.fromisoformat(record.session))
    lawful = []
    for index, point in enumerate(record.points):
        stamp = _instant(point["ts"])
        start = stamp.astimezone(opening.tzinfo).replace(second=0, microsecond=0)
        if opening <= start and start + timedelta(minutes=1) <= min(cutoff, closing):
            lawful.append((start, index, point))
    _need(bool(lawful), "quote_sample_unavailable")
    point = max(lawful, key=lambda item: (item[0], item[1]))[2]
    _need(type(point.get("price")) in (int, float)
          and point["price"] == observation["sampled_close"], "quote_sample_mismatch")
    return point


def capture_observation_quote_reference(record, observation, *, recorded_at):
    """Freeze the exact selected point hash BESIDE a newly frozen observation.

    Optional metadata failure cannot alter observation admission. Old observations
    are never revisited, including equal-priced later quotes in the same minute.
    """
    try:
        point = _sampled_point(record, observation)
        metadata = copy_native_metadata(point.get("native_quote_metadata"))
        _need(metadata is not None and "response_identity" in metadata,
              "quote_response_identity_unavailable")
        _need(_instant(point["quote_recorded_at"]) <= _instant(recorded_at), "quote_clock_order")
        return {"schema": "entry_radar.observation_quote_reference/v1",
                "observation_sha256": _hash(observation), "quote_point_sha256": _hash(point),
                "recorded_at": recorded_at, "point_count": len(record.points),
                "point_index": record.points.index(point)}
    except (ValueError, KeyError, TypeError, OverflowError):
        return None


def _spool(value, session):
    _need(type(value) is str and re.fullmatch(
        r"live_flow/entry_radar_events/" + re.escape(session) + r"/[0-9]{6}-[a-z0-9_-]+\.json", value)
        is not None, "candidate_origin_uncommitted")
    return value


def compose_candidate_quote_provenance(episode, *, record, identity_read, origin, composed_at):
    """Bind an existing native C1/C2 candidate; all I/O remains with its owners.

    The native candidate clock is an effective observation cutoff. Actual point
    admission, observation freeze and composition clocks remain separately named.
    The commit receipt is taken from the ORIGINAL retained event/transition, never
    the latest pass health/spool key. This receipt does not re-read a spool object.
    """
    from engine.entry_radar.earnings_context import _candidate
    from engine.entry_radar import challengers as ch, live_eval as le
    from engine.entry_radar.entry_events import EntryEvent
    from engine.entry_radar.quote_context import _check_native_read
    from lib.dataos.identity import IssuerMaster
    try:
        row = _candidate(episode)
        _need(row.detector_id in {ch.C1_DETECTOR_ID, ch.C2_DETECTOR_ID},
              "candidate_quote_mechanism_unsupported")
        cutoff = _instant(row.candidate_at)
        _need(cutoff <= _instant(composed_at), "quote_clock_order")
        _need(record is not None and record.ticker == row.ticker
              and record.session == row.market_session and bool(record.pack_hash), "quote_journal_mismatch")
        _need(len(record.points) <= 4096 and len(record.observations) <= 512
              and len(origin['events']) <= 64 and len(origin['transitions']) <= 2,
              "quote_provenance_input_bound")
        observations = [o for o in record.observations if o.get("observed_at") == row.candidate_at]
        _need(len(observations) == 1, "candidate_observation_unavailable")
        observation = observations[0]
        native = le.observation_from_dict(observation)
        _need(native.ticker == row.ticker and native.market_session == row.market_session
              and native.availability == "provisional" and native.bar_state == "provisional"
              and native.price_basis == native.daily_price_basis == record.price_basis
              and native.data_vintage == "journal:" + record.pack_hash[:12], "candidate_observation_mismatch")
        ref = record.observation_quote_refs.get(native.interval_start)
        _need(type(ref) is dict and set(ref) == {"schema", "observation_sha256", "quote_point_sha256", "recorded_at", "point_count", "point_index"}
              and ref["schema"] == "entry_radar.observation_quote_reference/v1"
              and ref["observation_sha256"] == _hash(observation), "quote_frozen_reference_unavailable")
        _need(type(ref['point_count']) is int and type(ref['point_index']) is int
              and 0 <= ref['point_index'] < ref['point_count'] <= len(record.points), "quote_frozen_point_mismatch")
        point = record.points[ref['point_index']]
        from dataclasses import replace
        captured = replace(record, points=record.points[:ref['point_count']])
        _need(_hash(point) == ref['quote_point_sha256']
              and _hash(_sampled_point(captured,observation)) == ref['quote_point_sha256'],
              "quote_frozen_point_mismatch")
        _need(point["price"] == native.sampled_close and point["source"] == "quotes",
              "quote_sample_mismatch")
        metadata = copy_native_metadata(point.get("native_quote_metadata"))
        _need(metadata is not None and "response_identity" in metadata,
              "quote_response_identity_unavailable")
        response = metadata["response_identity"]
        _need(response["vendor_symbol"].upper() == row.ticker
              and metadata["basis"] in {"trade", "minute", "regular"}
              and (point["basis"] is None or metadata["basis"] == point["basis"])
              and metadata["quote_ts_synthetic"] is False and metadata["tsSynthetic"] in (None, False)
              and type(metadata["ts"]) in (int, float)
              and int(_instant(metadata["quote_ts"]).timestamp() * 1000) == metadata["ts"]
              == int(_instant(point["ts"]).timestamp() * 1000), "quote_native_inputs_mismatch")
        admitted, frozen = _instant(point["quote_recorded_at"]), _instant(ref["recorded_at"])
        _need(_instant(metadata["quote_ts"]) <= admitted <= cutoff and admitted <= frozen <= _instant(composed_at),
              "quote_not_observed_by_candidate")
        # The snapshot was genuinely read before this cutoff; actual provider
        # symbol/namespace is used without rewriting an episode or inferring it.
        _check_native_read(identity_read)
        receipt = identity_read.receipt.as_record()
        _need(int(receipt["read_completed_at_utc_ns"]) <= int(cutoff.timestamp() * 10**9),
              "quote_identity_read_after_candidate")
        answer = identity_read.alias_table().resolve_binding(response["vendor"], response["vendor_symbol"],
            cutoff.date(), decision_at=row.candidate_at, snapshot_receipts=(identity_read.receipt,))
        _need(answer.status == "BOUND", "quote_alias_not_bound")
        master = IssuerMaster.from_records(json.loads(identity_read.snapshot.master_json))
        issuer = master.issuer_of_security(answer.security_id)
        cik = master.cik_of_issuer(issuer) if issuer else None
        _need(issuer is not None and cik is not None, "quote_issuer_unresolved")
        events = []
        for item in origin["events"]:
            event = EntryEvent.from_dict({k:v for k,v in item.items() if k != "spool_key"})
            if event.signal_ts == row.candidate_at and event.event_id in row.evidence_refs:
                events.append((event, item))
        _need(len(events) == 1 and len(origin["transitions"]) == 1, "candidate_origin_ambiguous")
        event, event_record = events[0]
        transition = origin["transitions"][0]
        _need(event.ticker == row.ticker and event.detector_id == row.detector_id
              and event.signal_known_ts == row.candidate_at
              and event.source_identity.detector_spec_hash == row.detector_spec_hash
              and event.context.get("sampled_close") == native.sampled_close
              and all(event.context.get(key) == getattr(native,key)
                      for key in (("k","d") if row.detector_id == ch.C1_DETECTOR_ID else ("k","d","hist")))
              and event.bar_state == native.bar_state
              and event.context.get("market_session") == row.market_session
              and (row.detector_id != ch.C2_DETECTOR_ID or event.subtype == row.variant)
              and transition.get("ticker") == row.ticker and transition.get("detector_id") == row.detector_id
              and transition.get("variant") == row.variant and transition.get("at") == row.candidate_at
              and transition.get("from_state") == "ARMED" and transition.get("to_state") == "CANDIDATE"
              and transition.get("evidence_refs") == [event.event_id], "candidate_origin_mismatch")
        result = {"schema": SCHEMA,
            "episode_binding": {"episode_id": row.episode_id, "candidate_at": row.candidate_at,
                                "canonical_sha256": sha256(row.canonical.encode()).hexdigest()},
            "scope": "prospective_native_quote_observation", "composed_at": composed_at,
            "candidate_clock_semantics": "detector_effective_observation_cutoff",
            "quote": {**response, "namespace_basis": "native_endpoint_parser",
                "provider_identity_attestation": "not_available", "vendor_timestamp": metadata["quote_ts"],
                "normalized_timestamp": point["ts"], "native_basis": metadata["basis"],
                "normalized_basis": point["basis"], "recorded_at": point["quote_recorded_at"], "point_sha256": _hash(point)},
            "observation": {"sha256": _hash(observation), "recorded_at": ref["recorded_at"],
                            "interval_start": native.interval_start, "pack_hash": record.pack_hash},
            "identity": {"security_id": answer.security_id, "issuer_id": issuer, "cik": cik,
                "alias_revision_id": answer.alias_revision_id, "alias_known_at_utc_ns": answer.known_at_utc_ns,
                "identity_read_receipt": receipt, "identity_snapshot_sha256": answer.receipt_sha256},
            "origin": {"event_id": event.event_id, "event_sha256": _hash(event.to_dict()),
                "transition_sha256": _hash({k:v for k,v in transition.items() if k != "spool_key"}),
                "event_spool_key": _spool(event_record.get("spool_key"), row.market_session),
                "transition_spool_key": _spool(transition.get("spool_key"), row.market_session),
                "receipt_scope": "ordinary_ledger_commit_not_spool_replay"},
            "live_projection_eligible": False, "rights_state": "not_granted_by_provenance",
            "authority": dict(ef.ALL_FALSE_AUTHORITY)}
        result["sha256"] = _hash(result)
        return result
    except CandidateProvenanceUnavailable:
        raise
    except Exception:
        raise CandidateProvenanceUnavailable("candidate_quote_provenance_unavailable") from None

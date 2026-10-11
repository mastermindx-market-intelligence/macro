"""Inspect the HELD Macro retained-minute decoder shape without source admission.

The original reader's file read, revision selector and rights/basis owner keep
custody. This module never reads raw source bytes, selects a revision, attempts
to authenticate source ownership or converts null basis to unadjusted USD.

ABI is pinned to Macro #8623 exact head 6cff6ef8...; source changes require
separate owner-driven compatibility review, not automatic adoption.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict,dataclass
from datetime import datetime,timezone,timedelta
from hashlib import sha256
import json,math
from typing import Mapping

import pressure as m
import source_preflight as sp

SOURCE_OWNER_PR=8623
SOURCE_OWNER_HEAD="6cff6ef8aba28dc7ee6f7779a81ef18856d9b3b6"
DECODER_SCHEMA="mastermind.entry_radar.terminal_minute_observations.v1"
BASIS_REFUSAL="TERMINAL_BASIS_UNPROVEN"
_EPOCH=datetime(1970,1,1,tzinfo=timezone.utc)


@dataclass(frozen=True)
class CandidateInterop:
    decoder_schema: str
    source_owner_head: str
    stage: str
    mapped_rows: int
    mapped_volume_states: tuple[tuple[str,int],...]
    preflight: sp.Preflight
    mapped_listing_refs_are_null: bool
    mapped_basis_refs_are_null: bool
    fully_selected_revisions: bool
    source_authenticated: bool
    verified_rights: bool
    pit_listing_verified: bool
    owner_admission_required: bool
    market_pilot_admitted: bool
    customer_publishable: bool
    knowledge_class: str
    evidence_digest: str
    authority: tuple[tuple[str,bool],...]=m.AUTHORITY


def _ns_from_iso(value: object) -> int:
    if not isinstance(value,str) or not value.endswith("Z"):
        raise ValueError("owner_timestamp_requires_utc_iso")
    try:
        instant=datetime.fromisoformat(value[:-1]+"+00:00")
        if instant.utcoffset()!=timedelta(0):
            raise ValueError
        delta=instant.astimezone(timezone.utc)-_EPOCH
    except (ValueError,OverflowError,TypeError):
        raise ValueError("owner_timestamp_invalid") from None
    return ((delta.days*86400+delta.seconds)*1000000+delta.microseconds)*1000


def _ns_to_ceiled_micro_iso(value: int) -> str:
    if type(value) is not int or value<=0:
        raise ValueError("owner_read_clock_invalid")
    try:
        actual=_EPOCH+timedelta(microseconds=(value+999)//1000)
    except OverflowError:
        raise ValueError("owner_read_clock_invalid") from None
    return actual.isoformat().replace("+00:00","Z")


def _readrow(item: Mapping[str,object], scope: sp.IntakeScope) -> sp.MinuteClaim:
    if not isinstance(item,Mapping):
        raise ValueError("decoded_minute_mapping_required")
    if item.get("basis_id") is not None or item.get("basis_refusals") != [BASIS_REFUSAL]:
        raise ValueError("candidate_basis_claim_not_supported")
    sid=item.get("security_id")
    if not isinstance(sid,str) or sid not in scope.securities:
        raise ValueError("canonical_security_id_required")
    try:
        source=item["source_observation"]
    except KeyError:
        raise ValueError("source_observation_required") from None
    if not isinstance(source,Mapping):
        raise ValueError("source_observation_required")
    csha=source.get("capture_sha256")
    ssha=source.get("source_response_sha256")
    rsha=source.get("owner_read_receipt_sha256")
    for label,sha in (("capture",csha),("response",ssha),("reader_receipt",rsha)):
        if not sp._digest(sha,label):
            raise ValueError("missing_owner_"+label)
    read_ns=source.get("owner_read_completed_at_utc_ns")
    received_ns=source.get("source_received_at_utc_ns")
    sp._timestamp(read_ns,"read")
    sp._timestamp(received_ns,"response")
    if item.get("known_at") != _ns_to_ceiled_micro_iso(read_ns):
        raise ValueError("read_clock_mismatch")
    start_ns=_ns_from_iso(item.get("start"))
    end_ns=_ns_from_iso(item.get("end"))
    if start_ns%1_000_000_000 or end_ns-start_ns!=60*1_000_000_000:
        raise ValueError("owner_event_one_minute_clock_mismatch")
    start=start_ns//1_000_000_000
    end=end_ns//1_000_000_000
    segment=next((s for s in scope.segments
                  if s.start_utc_s<=start<end<=s.end_utc_s),None)
    if segment is None:
        raise ValueError("owner_event_outside_supplied_calendar")
    if m._et_clock(start)[0]!=segment.session_id:
        raise ValueError("owner_event_session_mismatch")
    page=source.get("page_index")
    row=source.get("row_index")
    if type(page) is not int or page<0 or type(row) is not int or row<0:
        raise ValueError("page_or_row_index_invalid")
    ref=f"terminal-minute-capture:{csha}:{page}:{row}"
    if item.get("source_ref")!=ref:
        raise ValueError("source_ref_mismatch")
    revision=item.get("revision_id")
    m._text(revision,"revision")
    seal=item.get("receipt_sha256")
    if not sp._digest(seal,"row_receipt"):
        raise ValueError("row_receipt_invalid")
    content={k:v for k,v in item.items() if k!="receipt_sha256"}
    try:
        canonical=json.dumps(content,sort_keys=True,separators=(",",":"),
                             ensure_ascii=True,allow_nan=False)
    except (ValueError,TypeError):
        raise ValueError("invalid_owner_row_json") from None
    if sha256(canonical.encode()).hexdigest()!=seal:
        raise ValueError("row_receipt_digest_mismatch")

    close=item.get("close")
    m._finite(close,"owner_close",positive=True)
    volume=item.get("volume")
    declared=source.get("volume_state")
    if declared=="null" and volume is None:
        value_state="UNKNOWN"
    elif declared=="missing" and volume is None:
        value_state="UNKNOWN"
    elif declared=="observed":
        amount=m._finite(volume,"owner_volume",nonnegative=True)
        value_state="EXPLICIT_ZERO_VOLUME" if amount==0 else "PRESENT"
    else:
        raise ValueError("owner_volume_state_inconsistent")

    return sp.MinuteClaim(
        security_id=sid,listing_ref=None,segment=segment,
        start_utc_s=start,end_utc_s=end,
        source_receipt_utc_ns=received_ns,
        reader_completed_utc_ns=read_ns,
        source_object_sha256=ssha,
        sealed_capture_prefix_sha256=csha,
        reader_receipt_sha256=rsha,
        selection_receipt_sha256=None,
        source_revision_ref=revision,
        owner_reader_ref=source.get("owner_reader_identity"),
        rights_ref=None,dataset_use_ref=None,
        acquisition_role=source.get("acquisition_role") or "UNPROVEN",
        request_adjusted=source.get("request_adjusted"),
        response_adjusted=source.get("response_adjusted"),
        basis_id=None,basis_receipt_sha256=None,
        action_vintage_ref=None,
        volume_convention_ref=None,
        value_state=value_state)


def inspect_candidate(decoded: Mapping[str,object],
                      scope: sp.IntakeScope) -> CandidateInterop:
    """Return only candidate-source refusal and metadata coverage evidence.

    Internal hashes are self-consistency checks, not cryptographic attestation
    or a model for a separate admission/identity authority.
    """
    if not isinstance(decoded,Mapping) or decoded.get("schema")!=DECODER_SCHEMA:
        raise ValueError("decoder_schema_mismatch")
    if not isinstance(scope,sp.IntakeScope):
        raise ValueError("intake_scope_required")
    authority=decoded.get("authority")
    if (not isinstance(authority,Mapping) or not authority or
            any(type(value) is not bool or value for value in authority.values())):
        raise ValueError("owner_authority_not_closed")
    if "price_volume_corporate_action_basis" not in (
            decoded.get("unproven_owner_requirements") or ()):
        raise ValueError("missing_mandatory_basis_refusal")
    rows=decoded.get("minutes")
    if not isinstance(rows,list):
        raise ValueError("decoder_minutes_required")
    status=decoded.get("status")
    if status=="UNAVAILABLE":
        if rows:
            raise ValueError("decoder_status_payload_conflict")
    elif status!="REVISION_INPUTS_BUILT_NOT_ADMITTED":
        raise ValueError("unadmitted_decoder_status_required")
    claims=tuple(_readrow(x,scope) for x in rows)
    pre=sp.preflight(scope,claims)
    counts=Counter(r.value_state for r in claims)
    return CandidateInterop(
        DECODER_SCHEMA,SOURCE_OWNER_HEAD,
        "OWNER_READER_UNAVAILABLE" if not claims else "OWNER_BASIS_UNPROVEN",
        len(claims),tuple(sorted(counts.items())),pre,
        True,True,False,False,False,False,True,False,False,
        "HELD_TERMINAL_READER_INTEROP_NOT_MARKET_MEASUREMENT",
        m.digest({"decoder_schema":DECODER_SCHEMA,
                  "owner_head":SOURCE_OWNER_HEAD,
                  "preflight":pre.input_digest,
                  "candidate_row_count":len(claims),
                  "volume_states":tuple(sorted(counts.items()))}))

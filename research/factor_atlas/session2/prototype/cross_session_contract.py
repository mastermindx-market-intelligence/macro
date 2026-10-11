"""S1 total-return index / S2 minute pressure boundary: read-only structural audit.

Pins the source-shaped Factor Atlas S1 candidate from Macro PR #8680;
never selects members, fetches prices, converts TRADJ to raw USD notional,
authenticates source receipts, publishes a factor or controls trading.
A syntactically matching roster is NOT historical PIT owner confirmation.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from datetime import date
from hashlib import sha256
import json

import pressure as m
import window_pressure as wp

S1_SOURCE_HEAD="ddf1f07f2059caebb4bfa6b1db6c4008dd97859c"
S1_SOURCE_SCHEMA="factor_atlas_read.v1"
S1_RETURN_BASIS="tradj"
S2_NOTIONAL_BASIS="unadjusted/USD"


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(value,sort_keys=True,ensure_ascii=False,
                          allow_nan=False,separators=(",",":")).encode("utf-8")
    except (TypeError,ValueError,OverflowError):
        raise ValueError("s1_json_invalid") from None


def fingerprint_s1(value: Mapping) -> str:
    """Match the owner's S1 canonical JSON result hash (not source attestation)."""
    if not isinstance(value,Mapping):
        raise ValueError("s1_native_mapping_required")
    return sha256(_canonical({k:v for k,v in value.items()
                              if k!="result_digest"})).hexdigest()


def _date(value: object) -> str:
    if not isinstance(value,str):
        raise ValueError("owner_cohort_date_invalid")
    try:
        if date.fromisoformat(value).isoformat()!=value:
            raise ValueError
    except ValueError:
        raise ValueError("owner_cohort_date_invalid") from None
    return value


def _identity(value: object,field: str) -> str:
    if not isinstance(value,str) or not value.strip() or len(value)>512:
        raise ValueError(field+"_missing_or_invalid")
    return value


@dataclass(frozen=True)
class S1S2BoundaryReview:
    schema: str
    status: str
    source_s1_head: str
    s1_factor_ref: str
    s2_factor_ref: str
    s1_mode: str
    s1_return_basis: str
    s2_required_source_basis: str
    s1_observation_date: str
    s2_session: str
    compared_member_count: int | None
    member_id_sets_match: bool | None
    reasons: tuple[str,...]
    pit_roster_verified: bool
    source_receipts_authenticated: bool
    data_use_rights_proven: bool
    source_measurement_basis_compatible: bool
    allow_joint_numeric_arithmetic: bool
    allow_use_s1_prices_for_s2_notional: bool
    market_pilot_admitted: bool
    customer_publishable: bool
    input_digest: str
    authority: tuple[tuple[str,bool],...]=m.AUTHORITY


def review_s1_s2(s1: Mapping, s2: wp.WindowPressure, *,
                 factor_ref: str) -> S1S2BoundaryReview:
    """Never report a positive source join from candidate-only S1+S2 outputs.

    Structural comparison is useful for future separate research panels.
    Nothing in the two candidates is an authenticated selected PIT source
    packet or a valid rights/basis/monetary transformation.
    """
    if not isinstance(s1,Mapping) or s1.get("schema")!=S1_SOURCE_SCHEMA:
        raise ValueError("s1_schema_unsupported")
    if not isinstance(s2,wp.WindowPressure):
        raise ValueError("s2_window_required")
    if s2.authority!=m.AUTHORITY:
        raise ValueError("s2_authority_overclaim")
    if s1.get("result_digest")!=fingerprint_s1(s1):
        raise ValueError("s1_result_digest_mismatch")
    if s1.get("release_state")!="CANDIDATE_NOT_ADMITTED" or (
        s1.get("input_admission")!="REFERENCE_CHECKS_ONLY_NOT_RECEIPT_AUTHENTICATION"):
        raise ValueError("s1_unqualified_admission_state")
    attrs=s1.get("authority")
    if (not isinstance(attrs,Mapping) or
            frozenset(attrs)!=frozenset(("may_rank","may_gate","may_size","may_trade","may_publish","may_escalate"))
            or any(type(v) is not bool or v for v in attrs.values())):
        raise ValueError("s1_authority_overclaim")
    mode=s1.get("history_mode")
    if mode not in ("CURRENT_ROSTER","PIT_AS_KNOWN"):
        raise ValueError("s1_history_mode_invalid")
    method=s1.get("method")
    if not isinstance(method,Mapping):
        raise ValueError("s1_method_required")
    basis=method.get("return_basis")
    if basis!=S1_RETURN_BASIS:
        raise ValueError("invalid_s1_return_basis")
    if method.get("currency")!="USD" or method.get("session")!="regular":
        raise ValueError("incompatible_s1_method_scope")
    observation=_date(s1.get("as_of"))
    _identity(s1.get("basket_id"),"s1_basket_id")
    _identity(factor_ref,"s2_factor_ref")
    _date(s2.session_id)
    _identity(s2.input_digest,"s2_window_digest")
    if not isinstance(s2.factors,tuple) or len({f.factor_id for f in s2.factors})!=len(s2.factors):
        raise ValueError("s2_factors_required")
    source_refs=s1.get("source_refs")
    if not isinstance(source_refs,Mapping):
        raise ValueError("s1_source_refs_required")
    cohorts=source_refs.get("cohorts")
    if not isinstance(cohorts,list):
        raise ValueError("s1_cohorts_required")
    normalized=deepcopy(dict(s1))
    normalized.pop("result_digest",None)
    rows=[];by_date={}
    for row in cohorts:
        if not isinstance(row,Mapping):
            raise ValueError("owner_cohort_mapping_required")
        when=_date(row.get("effective_close"))
        ids=row.get("members")
        if (not isinstance(ids,list) or
                any(not isinstance(i,str) or not i.strip() or len(i)>512 for i in ids)):
            raise ValueError("owner_cohort_members_invalid")
        if len(ids)!=len(set(ids)):
            raise ValueError("duplicate_cohort_member")
        if when in by_date:
            raise ValueError("duplicate_owner_cohort_at_clock")
        if not isinstance(row.get("snapshot_ref"),str) or not row["snapshot_ref"].strip():
            raise ValueError("cohort_snapshot_ref_required")
        by_date[when]=tuple(sorted(ids))
        rowcopy=deepcopy(dict(row))
        rowcopy["members"]=sorted(ids)
        rows.append(rowcopy)
    normalized["source_refs"]=deepcopy(dict(source_refs))
    normalized["source_refs"]["cohorts"]=sorted(rows,key=lambda c:c["effective_close"])
    reasons={"TRADJ_RETURN_VS_UNADJUSTED_NOTIONAL",
             "REAL_SOURCE_BASIS_RIGHTS_NOT_ADMITTED",
             "UNVERIFIED_S1_SOURCE_CUSTODY",
             "S1_PIT_SELECTION_RECEIPT_NOT_EXPOSED",
             "S2_RAW_BASIS_NOT_ATTESTED_BY_WINDOW_PROJECTION"}
    if mode!="PIT_AS_KNOWN":
        reasons.add("S1_CURRENT_ROSTER_NOT_PIT")
    if s2.mode!="as_observed":
        reasons.add("S2_CORRECTED_HISTORY_NOT_AS_OBSERVED")
    if s1["basket_id"]!=factor_ref:
        reasons.add("FACTOR_ID_MISMATCH")
    factor=next((f for f in s2.factors if f.factor_id==factor_ref),None)
    if factor is None:
        reasons.add("S2_FACTOR_NOT_IN_WINDOW")
    elif factor.membership_basis!="point_in_time":
        reasons.add("S2_ROSTER_NOT_PIT")
    if observation<s2.session_id:
        reasons.add("S1_MEASUREMENT_STALE_FOR_S2_SESSION")
    if s2.session_id not in by_date:
        reasons.add("NO_SAME_SESSION_COHORT_OBSERVATION")

    compare=(factor is not None and factor.membership_basis=="point_in_time"
             and mode=="PIT_AS_KNOWN" and s1["basket_id"]==factor_ref
             and s2.session_id in by_date)
    n=None;match=None
    if compare:
        selected=by_date[s2.session_id]
        given=tuple(sorted(c.security_id for c in factor.contributions))
        if len(given)!=len(set(given)):
            raise ValueError("s2_duplicate_member_contribution")
        n=len(selected)
        match=selected==given
        if not match:
            reasons.add("SELECTED_MEMBER_SET_MISMATCH")
    # S1's reduced cohort is a monthly closing observation, not an
    # owner-selected minute-by-minute PIT membership receipt; even a
    # syntactically matching list cannot establish real historical membership.
    digest=m.digest({"s1_shape":normalized,"s2_input":s2.input_digest,
                     "s2_factor":factor_ref,
                     "s2_members":tuple(sorted(c.security_id for c in factor.contributions))
                     if factor is not None else None,
                     "s2_window_mode":s2.mode})
    return S1S2BoundaryReview(
        "factor_atlas.s1_s2_boundary_review.v1",
        "HOLD_SEPARATE_READ_MODELS",S1_SOURCE_HEAD,
        s1["basket_id"],factor_ref,mode,basis,S2_NOTIONAL_BASIS,
        observation,s2.session_id,n,match,
        tuple(sorted(reasons)),False,False,False,False,False,False,
        False,False,digest)

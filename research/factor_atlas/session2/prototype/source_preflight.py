"""S2-P1 source-claim coverage census; never an admissibility authority.

Inspects OWNER-SUPPLIED METADATA, not raw market data, files, permissions,
revisions, source signatures or captured bytes. A complete *claim* is an
unverified candidate for review by the incumbent source/basis/license owner.
No caller input can turn this routine into an admission decision.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from decimal import Decimal, localcontext
import re
from typing import Iterable
import pressure as m

COHORT=frozenset(("AAPL","MSFT","NVDA","SPY"))
HEX=re.compile(r"^[0-9a-fA-F]{64}$")
UNVERIFIED=(
    "UNCHECKED_CUSTODY",
    "INPUT_DIGEST_NOT_AUTHENTICATED",
    "EXTERNAL_SOURCE_RIGHTS_UNPROVEN",
    "SOURCE_BASIS_OWNER_UNVERIFIED",
    "CALENDAR_OWNER_UNVERIFIED",
    "LISTING_IDENTITY_OWNER_UNVERIFIED",
    "DATASET_CONDITIONS_UNVERIFIED",
)

@dataclass(frozen=True)
class IntakeScope:
    securities: tuple[str,...]
    segments: tuple[m.Segment,...]
    cutoff_utc_ns: int

@dataclass(frozen=True)
class MinuteClaim:
    security_id: str
    listing_ref: str | None
    segment: m.Segment
    start_utc_s: int
    end_utc_s: int
    source_receipt_utc_ns: int | None
    reader_completed_utc_ns: int | None
    source_object_sha256: str | None
    sealed_capture_prefix_sha256: str | None
    reader_receipt_sha256: str | None
    selection_receipt_sha256: str | None
    source_revision_ref: str | None
    owner_reader_ref: str | None
    rights_ref: str | None
    dataset_use_ref: str | None
    acquisition_role: str
    request_adjusted: bool
    response_adjusted: str
    basis_id: str | None
    basis_receipt_sha256: str | None
    action_vintage_ref: str | None
    volume_convention_ref: str | None
    value_state: str

@dataclass(frozen=True)
class CellIssue:
    security_id: str
    start_utc_s: int
    reasons: tuple[str,...]
    reason: str

@dataclass(frozen=True)
class Preflight:
    status: str
    owner_review_candidate: bool
    metadata_complete: bool
    expected_cells: int
    represented_cells: int
    missing_cells: int
    unknown_cells: int
    explicit_zero_cells: int
    coverage_ratio: str
    exceptions: tuple[CellIssue,...]
    unverified_authorities: tuple[str,...]
    external_owner_admission_required: bool
    may_execute_market_pilot: bool
    input_digest: str
    authority: tuple[tuple[str,bool],...]=m.AUTHORITY


def _timestamp(value: object,kind: str) -> int|None:
    if value is None:
        return None
    if type(value) is not int or value<=0:
        raise ValueError(kind+"_invalid_timestamp")
    return value

def _digest(value: str|None,kind: str) -> bool:
    if value is None:
        return False
    if not isinstance(value,str) or HEX.fullmatch(value) is None:
        raise ValueError(kind+"_invalid_digest")
    return True

def _optional_ref(value: str|None,kind: str) -> bool:
    if value is None:
        return False
    m._text(value,kind)
    return True

def _scope(scope: IntakeScope) -> tuple[m.Segment,...]:
    if not isinstance(scope,IntakeScope):
        raise ValueError("input_scope_required")
    if (not isinstance(scope.securities,tuple) or
            len(scope.securities)!=4 or frozenset(scope.securities)!=COHORT):
        raise ValueError("expected_explicit_four_security_cohort")
    if any(type(s) is not str for s in scope.securities):
        raise ValueError("canonical_symbol_labels_required")
    if not isinstance(scope.segments,tuple) or not 1<=len(scope.segments)<=3:
        raise ValueError("calendar_segments_required")
    segs=tuple(sorted(scope.segments,key=lambda s:s.start_utc_s))
    if any(not isinstance(s,m.Segment) for s in segs):
        raise ValueError("calendar_segments_required")
    for s in segs:
        s.validate()
        if s.start_utc_s%60 or s.end_utc_s%60 or s.end_utc_s-s.start_utc_s>960*60:
            raise ValueError("calendar_minute_alignment")
    if len({(s.session_id,s.calendar_ref,s.session_class) for s in segs})!=1:
        raise ValueError("mixed_calendar_identity")
    if any(a.end_utc_s>b.start_utc_s for a,b in zip(segs,segs[1:])):
        raise ValueError("calendar_overlap")
    if sum((s.end_utc_s-s.start_utc_s)//60 for s in segs)>960:
        raise ValueError("source_scope_too_large")
    _timestamp(scope.cutoff_utc_ns,"as_of")
    return segs

def _checks(row: MinuteClaim,cutoff: int) -> tuple[str,...]:
    issues=[]
    for value,kind,label in (
      (row.source_object_sha256,"source_object","SOURCE_BINDING_MISSING"),
      (row.sealed_capture_prefix_sha256,"prefix","SOURCE_BINDING_MISSING"),
      (row.reader_receipt_sha256,"reader","READER_RECEIPT_MISSING"),
      (row.selection_receipt_sha256,"selection","REVISION_SELECTION_UNPROVEN"),
      (row.basis_receipt_sha256,"basis","MONETARY_BASIS_UNPROVEN"),
    ):
        if not _digest(value,kind):
            issues.append(label)
    for value,kind,label in (
      (row.listing_ref,"listing","LISTING_IDENTITY_UNPROVEN"),
      (row.source_revision_ref,"revision","REVISION_SELECTION_UNPROVEN"),
      (row.owner_reader_ref,"reader_owner","READER_OWNER_UNKNOWN"),
      (row.rights_ref,"rights","DATASET_RIGHTS_UNPROVEN"),
      (row.dataset_use_ref,"dataset_use","DATASET_RIGHTS_UNPROVEN"),
    ):
        if not _optional_ref(value,kind):
            issues.append(label)
    if not (isinstance(row.basis_id,str) and
            (row.basis_id=="unadjusted/USD" or
             row.basis_id.startswith("unadjusted/USD/"))):
        issues.append("MONETARY_BASIS_UNPROVEN")
    for attr in (row.action_vintage_ref,row.volume_convention_ref):
        if not _optional_ref(attr,"basis_derivation"):
            issues.append("MONETARY_BASIS_UNPROVEN")
    src=_timestamp(row.source_receipt_utc_ns,"source_receipt")
    read=_timestamp(row.reader_completed_utc_ns,"reader_completed")
    close_ns=row.end_utc_s*1_000_000_000
    if src is None:
        issues.append("SOURCE_RECEIPT_MISSING")
    elif src<close_ns:
        raise ValueError("source_before_bar_close")
    elif src>cutoff:
        issues.append("SOURCE_AFTER_CUTOFF")
    if read is None:
        issues.append("READER_RECEIPT_MISSING")
    elif src is not None and read<src:
        raise ValueError("reader_before_source")
    elif ((read+999)//1000)*1000>cutoff:
        # Incumbent reader rounds actual ns read completion upward to the
        # supported microsecond clock. Never admit an earlier decision by
        # rounding this receipt backward or by using the original ns alone.
        issues.append("READER_AFTER_CUTOFF")
    if row.acquisition_role!="research_unadjusted":
        issues.append("NOT_RESEARCH_UNADJUSTED")
    if row.request_adjusted is not False:
        issues.append("NOT_RAW_REQUEST")
    if row.response_adjusted!="FALSE":
        issues.append("RAW_RESPONSE_NOT_CONFIRMED")
    if row.value_state not in ("PRESENT","EXPLICIT_ZERO_VOLUME"):
        issues.append("MINUTE_VALUE_UNAVAILABLE")
    return tuple(sorted(set(issues)))

def preflight(scope: IntakeScope,rows: Iterable[MinuteClaim]) -> Preflight:
    """Metadata completeness is no replacement for owner admission.

    Only selected, prequalified row claims should be supplied; any identity or
    revision collision is refused. Unsupported future-window rows are ignored
    so a later store append cannot mutate an earlier scoped census.
    """
    segs=_scope(scope)
    expected={(sid,t) for sid in scope.securities
                       for seg in segs
                       for t in range(seg.start_utc_s,seg.end_utc_s,60)}
    selected={}
    for row in rows:
        if not isinstance(row,MinuteClaim):
            raise ValueError("minute_claim_required")
        m._integer(row.start_utc_s,"claim_start")
        m._integer(row.end_utc_s,"claim_end")
        if row.start_utc_s>=max(s.end_utc_s for s in segs):
            continue
        if row.security_id not in COHORT:
            raise ValueError("unexpected_security")
        if row.segment not in segs:
            raise ValueError("segment_identity_mismatch")
        if (row.end_utc_s-row.start_utc_s!=60 or row.start_utc_s%60 or
                not row.segment.start_utc_s<=row.start_utc_s<
                row.end_utc_s<=row.segment.end_utc_s):
            raise ValueError("not_an_exact_owner_one_minute")
        key=(row.security_id,row.start_utc_s)
        if key not in expected:
            raise ValueError("outside_qualified_calendar_scope")
        if key in selected:
            raise ValueError("duplicate_slot_requires_incumbent_revision_selector")
        selected[key]=row
    # Cross-minute identity and monetary basis are a separate consistency gate.
    # A caller's valid-looking labels are not authoritative merely by existing.
    by_security={sid:[] for sid in scope.securities}
    for (sid,start),row in selected.items():
        by_security[sid].append(row)
    conflicts={}
    for sid,own_rows in by_security.items():
        own_conflicts=[]
        if len({r.listing_ref for r in own_rows if r.listing_ref is not None})>1:
            own_conflicts.append("LISTING_IDENTITY_CONFLICT")
        if len({r.basis_id for r in own_rows if r.basis_id is not None})>1:
            own_conflicts.append("MONETARY_BASIS_CONFLICT")
        conflicts[sid]=tuple(own_conflicts)
    exceptions=[]
    unknown=zero=0
    for sid,start in sorted(expected):
        row=selected.get((sid,start))
        if row is None:
            reasons=("MISSING_SOURCE_MINUTE",)
            unknown+=1
        else:
            reasons=tuple(sorted(set(_checks(row,scope.cutoff_utc_ns)+conflicts[sid])))
            if reasons or row.value_state=="MISSING_VOLUME":
                unknown+=1
            if row.value_state=="EXPLICIT_ZERO_VOLUME":
                zero+=1
        if reasons:
            exceptions.append(CellIssue(sid,start,reasons,reasons[0]))
    total=len(expected)
    represented=len(selected)
    with localcontext() as ctx:
        ctx.prec=64
        coverage=format(Decimal(represented)/Decimal(total),"f")
    return Preflight(
        "NOT_ADMITTED",not bool(exceptions),not bool(exceptions),
        total,represented,total-represented,unknown,zero,
        coverage,tuple(exceptions),UNVERIFIED,True,False,
        m.digest({"scope":asdict(scope),
                  "claims":[asdict(selected[key]) for key in sorted(selected)],
                  "exceptions":[asdict(x) for x in exceptions]}))

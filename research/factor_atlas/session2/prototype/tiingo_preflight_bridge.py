"""Real Tiingo L1 source-value shape -> EXISTING S2 metadata preflight only.

Pure consumer: no vendor/file/API access, no pressure calculation, no alias
selection, no financial source/PIT/license admission. Caller supplies original
Data OS TiingoView objects and caller-selected *unverified* calendar segments.

An immutable source capture receipt (received Oct 11) is not a historical
market event time (Oct 9). Reader-completion and source selection clocks,
canonical issuer/PIT listing, vendor volume-money basis and rights remain
NULL unless the actual ORIGINAL owner supplies and accepts them elsewhere.
"""
from __future__ import annotations

from dataclasses import asdict,dataclass
from datetime import datetime, timezone
from collections.abc import Iterable
from typing import Any
import re

import pressure as m
import source_preflight as sp
from tiingo_source_fitness import assess_tiingo_view, aggregate_cohort_fitness, _request

_NANO=1_000_000_000
_TIME=re.compile(
    r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d{1,9}))?"
    r"(Z|[+-]\d\d:\d\d)$")


@dataclass(frozen=True)
class TiingoPreflightReview:
    schema: str
    status: str
    source_population: str
    expected_vendor_symbols: tuple[str,...]
    observed_vendor_tickers: tuple[str,...]
    preflight: sp.Preflight
    source_view_count: int
    source_rows_in_calendar_scope: int
    out_of_calendar_source_minutes: int
    vendor_zero_rows_in_scope: int
    vendor_missing_volume_rows_in_scope: int
    source_capture_is_after_decision_for_some_rows: bool
    source_owner_revision_selection_proven: bool
    reader_receipts_attested: bool
    calendar_attested: bool
    canonical_identity_admitted: bool
    source_rights_admitted: bool
    derived_cutoff_from_processing_time: bool
    actual_market_flow_computed: bool
    market_pilot_admitted: bool
    may_execute_market_pilot: bool
    customer_publishable: bool
    refusal_reasons: tuple[str,...]
    input_digest: str
    authority: tuple[tuple[str,bool],...]=m.AUTHORITY


def _utc_ns(value: object) -> int:
    """Parse exact original aware UTC source receipt with <= 9 fractional digits.

    Do not trust floating-point epoch conversion or quietly truncate
    source evidence to a decision time that preceded it.
    """
    if type(value) is not str:
        raise ValueError("source_timestamp_precision_invalid")
    match=_TIME.fullmatch(value)
    if match is None:
        raise ValueError("source_timestamp_precision_invalid")
    try:
        parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
        if parsed.utcoffset() is None:
            raise ValueError
        utc=parsed.astimezone(timezone.utc)
        seconds=int(utc.replace(microsecond=0).timestamp())
        fraction=int((match.group(2) or "").ljust(9,"0"))
        return seconds*_NANO+fraction
    except (TypeError,ValueError,OverflowError,OSError):
        raise ValueError("source_timestamp_precision_invalid") from None


def inspect_tiingo_preflight(views: Iterable[Any], *,
                             scope: sp.IntakeScope) -> TiingoPreflightReview:
    """Conservatively map original research-view receipts into S2 refusals.

    Consumes Tiingo L1 row CLOCKS, source receipt hashes, vendor volume
    present/missing and vendor reported-zero state only. Does not output prices,
    compute signed pressure, or adopt research input as canonical market data.
    """
    # Existing native preflight is the ONLY source-grid/status calculation.
    if not isinstance(scope,sp.IntakeScope):
        raise ValueError("original_source_scope_required")
    # Passing no claims validates caller's original calendar shape too.
    sp.preflight(scope,())
    material=tuple(views)
    if len(material)>4:
        raise ValueError("bounded_four_symbol_views_only")
    seen={}
    docs=[]
    source_fitness=[]
    claims=[]
    outside=zeros=nulls=0
    after=False
    segments=scope.segments
    for view in material:
        if getattr(view,"source",None)!="equity-intraday-bars":
            raise ValueError("consolidated_equity_source_required")
        qualified=assess_tiingo_view(view,required_symbols=scope.securities)
        if qualified.source_admitted or qualified.customer_publishable:
            raise ValueError("dataos_research_authority_overclaim")
        symbol,_,_=_request(view.source,view.source_request_path)
        if symbol not in scope.securities:
            raise ValueError("vendor_source_outside_pilot")
        if symbol in seen:
            raise ValueError("competing_source_partitions_require_original_owner")
        seen[symbol]=qualified
        source_fitness.append(qualified)
        source_at_ns=_utc_ns(view.source_observed_at_utc)
        for original in view.rows:
            at=original.get("bar_at_vendor")
            exact_ns=_utc_ns(at)
            if exact_ns%_NANO:
                raise ValueError("source_event_not_exact_minute")
            start=exact_ns//_NANO
            end=start+60
            seg=next((s for s in segments
                      if s.start_utc_s<=start<end<=s.end_utc_s),None)
            if seg is None:
                outside+=1
                continue
            if original.get("ticker_vendor")!=symbol:
                raise ValueError("source_ticker_context_mismatch")
            # The Tiingo research projector labels vendor volume unit
            # UNQUALIFIED. A vendor 0 is NOT a selected no-trade interval.
            volume=original.get("vendor_volume")
            if volume is None:
                nulls+=1
                value_state="MISSING_VOLUME"
            else:
                if volume==0:
                    zeros+=1
                value_state="UNKNOWN"
            claim=sp.MinuteClaim(
                security_id=symbol,  # vendor study label, NOT canonical Data OS ID
                listing_ref=None,segment=seg,
                start_utc_s=start,end_utc_s=end,
                source_receipt_utc_ns=source_at_ns,
                reader_completed_utc_ns=None,
                source_object_sha256=view.source_sha256,
                sealed_capture_prefix_sha256=None,
                reader_receipt_sha256=None,
                selection_receipt_sha256=None,
                source_revision_ref=None,
                owner_reader_ref="lib.dataos.tiingo_reader.read_research_view",
                rights_ref=None,dataset_use_ref=None,
                acquisition_role="vendor_retrospective_research",
                request_adjusted=None,  # no attested unadjusted request
                response_adjusted="UNQUALIFIED",
                basis_id=None,
                basis_receipt_sha256=None,
                action_vintage_ref=None,
                volume_convention_ref=None,
                value_state=value_state)
            claims.append(claim)
            if source_at_ns>scope.cutoff_utc_ns:
                after=True
        docs.append((symbol,view.source_sha256,
                     qualified.evidence_digest,
                     view.source_observed_at_utc))
    # Reuse the already-accepted Tiingo source-context identity check rather
    # than maintaining a parallel SHA/source-symbol ambiguity validator.
    if source_fitness:
        aggregate_cohort_fitness(source_fitness,required_symbols=scope.securities)
    pre=sp.preflight(scope,claims)
    # Native S2 preflight says every actual source entry remains unresolved.
    assert pre.status=="NOT_ADMITTED"
    reasons={reason for issue in pre.exceptions for reason in issue.reasons}
    reasons.update({
       "TIINGO_VENDOR_REFERENCE_NOT_CANONICAL",
       "ORIGINAL_EXCHANGE_CALENDAR_NOT_ATTESTED",
       "DATASET_LICENSE_OWNER_BINDING_REQUIRED",
       "UNQUALIFIED_VENDOR_VOLUME_NOT_EXPLICIT_NO_TRADE",
       "READER_COMPLETION_AND_SELECTED_REVISION_UNKNOWN",
    })
    payload=m.digest({"scope":asdict(scope),
                      "preflight":pre.input_digest,
                      "original_research_view_refs":sorted(docs),
                      "zero_vendor":zeros,"null_vendor_volume":nulls,
                      "outside_calendar":outside})
    return TiingoPreflightReview(
       schema="factor_atlas.tiingo_l1_source_preflight_bridge.v1",
       status="SOURCE_METADATA_NOT_ADMITTED",
       source_population="TIINGO_CONSOLIDATED_RESEARCH_L1",
       expected_vendor_symbols=scope.securities,
       observed_vendor_tickers=tuple(s for s in scope.securities if s in seen),
       preflight=pre,
       source_view_count=len(material),
       source_rows_in_calendar_scope=len(claims),
       out_of_calendar_source_minutes=outside,
       vendor_zero_rows_in_scope=zeros,
       vendor_missing_volume_rows_in_scope=nulls,
       source_capture_is_after_decision_for_some_rows=after,
       source_owner_revision_selection_proven=False,
       reader_receipts_attested=False,
       calendar_attested=False,
       canonical_identity_admitted=False,
       source_rights_admitted=False,
       derived_cutoff_from_processing_time=False,
       actual_market_flow_computed=False,
       market_pilot_admitted=False,
       may_execute_market_pilot=False,
       customer_publishable=False,
       refusal_reasons=tuple(sorted(reasons)),
       input_digest=payload)

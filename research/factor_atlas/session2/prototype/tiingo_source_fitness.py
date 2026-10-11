"""Factor Atlas S2 read-only Tiingo L1 source-fitness adapter.

Accepts the *existing* lib.dataos.tiingo_reader.TiingoView shape; never
reads vendor files, invokes an API, performs market normalization, or grants
source, PIT, rights, NBBO, publication or trading admission. This is a
retrospective SOURCE-COVERAGE diagnostic, not a BVC market pilot.

The original Tiingo Data OS source/reader and original S2 BVC engine keep
their existing ownership and permission controls.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta, timezone
import math
import re
from typing import Any, Iterable, Mapping
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

import pressure as m

_SHA=re.compile(r"^[0-9a-f]{64}$")
_SYMBOL=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,35}$")
_PILOT=("AAPL","MSFT","NVDA","SPY")
_ET=ZoneInfo("America/New_York")
_SOURCE_FORMAT={
    "boats-bars":("BOATS","single_ats","overnight","shares",
                  "/boats/{symbol}/prices"),
    "iex-bars":("IEX","single_exchange","vendor_request_session","shares",
                "/iex/{symbol}/prices"),
    "equity-intraday-bars":(None,"vendor_equity_reference","unqualified",
                            "unqualified",
                            "/tiingo/equity/intraday/{symbol}/prices"),
    "eod-bars":(None,"daily_composite","daily","shares",
                "/tiingo/daily/{symbol}/prices"),
}
_STATUS={
    "boats-bars":"BOATS_OVERNIGHT_SINGLE_ATS_RESEARCH_ONLY",
    "iex-bars":"IEX_SINGLE_EXCHANGE_RESEARCH_ONLY",
    "equity-intraday-bars":"CONSOLIDATED_BETA_CANDIDATE_NOT_ADMITTED",
    "eod-bars":"EOD_NOT_INTRADAY",
}


@dataclass(frozen=True)
class OvernightRequestCoverage:
    date_end_et: str
    requested_minute_slots: int
    observed_unique_minutes: int
    unreported_minutes: int
    zero_vendor_volume_rows: int
    missing_volume_rows: int
    request_left_clipped: bool
    request_right_clipped: bool


@dataclass(frozen=True)
class TiingoSourceFitness:
    schema: str
    status: str
    source: str
    source_sha256: str
    source_kind: str
    source_observed_at_utc: str
    read_purpose: str
    vendor: str
    venue: str|None
    venue_scope: str
    expected_pilot_symbols: tuple[str,...]
    observed_in_pilot: tuple[str,...]
    unobserved_in_pilot_partition: tuple[str,...]
    observed_vendor_symbols: tuple[str,...]
    audited_rows: int
    vendor_volume_present: int
    vendor_zero_volume_rows: int
    overnight_sessions: tuple[OvernightRequestCoverage,...]
    refusals: tuple[str,...]
    source_admitted: bool
    pit_backtest_eligible: bool
    redistribution_admitted: bool
    may_compute_daytime_pressure: bool
    customer_publishable: bool
    source_dataos_identity_verified: bool
    knowledge_class: str
    evidence_digest: str
    authority: tuple[tuple[str,bool],...]=m.AUTHORITY


@dataclass(frozen=True)
class TiingoCohortFitness:
    schema: str
    sampled_sources: int
    sampled_symbols: tuple[str,...]
    requested_pilot_symbols: tuple[str,...]
    pilot_symbols_with_retained_rows: tuple[str,...]
    pilot_symbols_not_in_examined_partitions: tuple[str,...]
    outside_pilot_sampled_symbols: tuple[str,...]
    unexamined_archives_are_unknown: bool
    qualified_four_stock_daytime_source: bool
    all_dataos_rights_admitted: bool
    customer_publishable: bool
    may_trade: bool
    evidence_digest: str
    authority: tuple[tuple[str,bool],...]=m.AUTHORITY


def _date(x: str) -> date:
    try:
        d=date.fromisoformat(x)
        if d.isoformat()!=x:
            raise ValueError
        return d
    except (TypeError,ValueError):
        raise ValueError("source_request_dates_invalid") from None


def _timestamp(x: object, name: str) -> datetime:
    if not isinstance(x,str):
        raise ValueError(name+"_invalid")
    try:
        d=datetime.fromisoformat(x.replace("Z","+00:00"))
    except ValueError:
        raise ValueError(name+"_invalid") from None
    if d.utcoffset() is None:
        raise ValueError(name+"_invalid")
    return d.astimezone(timezone.utc)


def _finite_positive(x: object, name: str) -> float:
    if type(x) not in (float,int) or not math.isfinite(x) or x<=0:
        raise ValueError(name+"_invalid")
    return float(x)


def _member_set(ids: Iterable[str]) -> tuple[str,...]:
    v=tuple(ids)
    if (not v or len(v)!=len(set(v)) or
            any(not isinstance(x,str) or _SYMBOL.fullmatch(x) is None for x in v)):
        raise ValueError("registered_source_pilot_symbols_invalid")
    return tuple(sorted(v))


def _meta(view: object) -> dict[str,Any]:
    keys=("source","source_sha256","source_observed_at_utc",
          "purpose","pit_backtest_eligible","redistribution_admitted",
          "rows","authority","source_request_path")
    try:
        d={k:getattr(view,k) for k in keys}
    except AttributeError:
        raise ValueError("owner_tiingo_view_contract_required") from None
    if d["source"] not in _SOURCE_FORMAT:
        raise ValueError("unsupported_tiingo_source")
    if not isinstance(d["source_sha256"],str) or not _SHA.fullmatch(d["source_sha256"]):
        raise ValueError("owner_source_sha256_required")
    if (d["pit_backtest_eligible"] is not False or
            d["redistribution_admitted"] is not False or
            d["authority"]!="RESEARCH_ONLY_VENDOR_SOURCE" or
            d["purpose"] not in ("INSPECTION","RETROSPECTIVE_EXPLORATORY")):
        raise ValueError("owner_view_authority_or_purpose_invalid")
    _timestamp(d["source_observed_at_utc"],"source_observed_at")
    if not isinstance(d["rows"],(tuple,list)) or len(d["rows"])>20000:
        raise ValueError("bounded_owner_rows_required")
    return d


def _request(source: str, uri: str) -> tuple[str,date,date]:
    if not isinstance(uri,str):
        raise ValueError("original_source_request_required")
    parsed=urlsplit(uri)
    if parsed.scheme or parsed.netloc or parsed.fragment:
        raise ValueError("original_source_request_path_only")
    components=parsed.path.split("/")
    if source=="boats-bars":
        parts=("", "boats", "{symbol}", "prices")
    elif source=="iex-bars":
        parts=("", "iex", "{symbol}", "prices")
    elif source=="equity-intraday-bars":
        parts=("", "tiingo", "equity", "intraday", "{symbol}", "prices")
    else:
        parts=("", "tiingo", "daily", "{symbol}", "prices")
    if len(components)!=len(parts) or any(
         part!=parts[i] for i,part in enumerate(components) if parts[i]!="{symbol}"):
        raise ValueError("source_family_request_path_mismatch")
    symbol=components[parts.index("{symbol}")]
    if not _SYMBOL.fullmatch(symbol):
        raise ValueError("source_vendor_symbol_invalid")
    q=parse_qs(parsed.query,keep_blank_values=True)
    # Tiingo original producer forbids arbitrary URL/token parameters. A
    # research consumer must not reinterpret duplicate query choices as one
    # successful source receipt or silently include a credential in a URL.
    allowed={"startDate","endDate","resampleFreq","columns","afterHours","forceFill"}
    if any(k not in allowed or len(values)!=1 for k,values in q.items()):
        raise ValueError("source_request_query_identity_invalid")
    if len(q.get("startDate",()))!=1 or len(q.get("endDate",()))!=1:
        raise ValueError("source_request_dates_invalid")
    start=_date(q["startDate"][0]);end=_date(q["endDate"][0])
    if start>end or (end-start).days>366:
        raise ValueError("source_request_dates_invalid")
    if source!="eod-bars":
        fields=set(q.get("columns",[""])[-1].split(","))
        if (q.get("resampleFreq")!=["1min"] or
                not {"open","high","low","close","volume"}.issubset(fields) or
                "forceFill" in q and q["forceFill"]!=["false"]):
            raise ValueError("requested_one_minute_unfilled_volume_invalid")
    return symbol,start,end


def _request_clip(when: str, start: date,end: date) -> tuple[int,bool,bool]:
    last=_date(when)
    def wall(d:date,h:int)->datetime:
        return datetime.combine(d,time(h,0),_ET)
    source_start=wall(start,0).astimezone(timezone.utc)
    source_end=wall(end+timedelta(days=1),0).astimezone(timezone.utc)
    window_start=wall(last-timedelta(days=1),20).astimezone(timezone.utc)
    window_end=wall(last,4).astimezone(timezone.utc)
    lo=max(window_start,source_start)
    hi=min(window_end,source_end)
    size=(hi-lo).total_seconds()/60
    if size<=0 or not size.is_integer():
        raise ValueError("vendor_overnight_request_overlap_invalid")
    return int(size),lo!=window_start,hi!=window_end


def assess_tiingo_view(view: object, *,
                       required_symbols: tuple[str,...]=_PILOT) -> TiingoSourceFitness:
    """Source fitness only, never producer authority or pressure calculation."""
    pilot=_member_set(required_symbols)
    selected=_meta(view)
    source=selected["source"]
    vendor_symbol,start,end=_request(source,selected["source_request_path"])
    venue,scope,session,unit,_=_SOURCE_FORMAT[source]
    captured=_timestamp(selected["source_observed_at_utc"],"source_observed_at")
    rows=selected["rows"]
    reasons={"DATASET_LICENSE_OWNER_BINDING_REQUIRED",
             "RESEARCH_L1_NOT_CANONICAL_PIT",
             "PIT_LISTING_READER_NOT_ATTESTED",
             "ORIGINAL_SOURCE_AVAILABILITY_NOT_BAR_CLOCK",
             "CORPORATE_ACTION_PRICE_VOLUME_BASIS_UNVERIFIED"}
    if source=="eod-bars":
        reasons.add("EOD_NOT_TRUE_ONE_MINUTE")
    elif source=="boats-bars":
        reasons.update({"BOATS_NOT_DAYTIME_CONSOLIDATED",
                        "BOATS_SINGLE_ATS_NOT_NBBO",
                        "ZERO_VENDOR_VOLUME_NOT_TRADE_PROOF"})
    elif source=="iex-bars":
        reasons.add("SINGLE_EXCHANGE_NOT_CONSOLIDATED")
    else:
        reasons.update({"CONSOLIDATED_VOLUME_UNIT_UNQUALIFIED",
                        "BETA_INTRADAY_SOURCE_NOT_INSTALLED_OR_ADMITTED"})
    seen=set(); overnight=defaultdict(list); volumecount=zero=0
    for raw in rows:
        if not isinstance(raw,Mapping):
            raise ValueError("owner_research_row_mapping_required")
        if source=="eod-bars":
            # A daily history can be useful to S1, but it is not 1m S2.
            continue
        stamp=_timestamp(raw.get("bar_at_vendor"),"invalid_vendor_minute_clock")
        if stamp.second or stamp.microsecond:
            raise ValueError("invalid_vendor_minute_clock_unaligned")
        # A retained 2026 snapshot cannot become an actual 2024 observation.
        if captured<stamp:
            raise ValueError("source_observed_before_event")
        local=stamp.astimezone(_ET)
        if not(start<=local.date()<=end):
            raise ValueError("bar_outside_original_request")
        if raw.get("ticker_vendor")!=vendor_symbol or any(
            raw.get(field)!=value for field,value in (
              ("source_view_schema","mastermind.tiingo.research_views.v2"),
              ("dataset_source",source),
              ("source_vendor","tiingo"),
              ("source_sha256",selected["source_sha256"]),
              ("source_observed_at_utc",selected["source_observed_at_utc"]),
              ("requested_resample_frequency","1min"),
              ("venue_scope",scope),("venue",venue),
              ("session",session),("volume_unit_vendor",unit),
              ("projection_version","tiingo.additional_history.v1"))):
            raise ValueError("source_row_context_mismatch")
        if not isinstance(raw.get("source_receipt_id"),str) or not _SHA.fullmatch(raw["source_receipt_id"]):
            raise ValueError("source_row_context_mismatch")
        for field in ("source_rights_admitted","pit_backtest_eligible",
                       "dataos_identity_admitted","canonical_price_basis_admitted",
                       "executable_price_proven","is_nbbo"):
            if raw.get(field) is not False:
                raise ValueError("owner_source_admission_spoof")
        minute=(vendor_symbol,stamp)
        if minute in seen:
            raise ValueError("duplicate_vendor_minute")
        seen.add(minute)
        numeric={}
        for k in ("open","high","low","close"):
            numeric[k]=_finite_positive(raw.get("vendor_"+k),"vendor_ohlc")
        if (numeric["low"]>min(numeric["open"],numeric["close"]) or
                numeric["high"]<max(numeric["open"],numeric["close"])):
            raise ValueError("invalid_vendor_ohlc_inconsistent")
        vol=raw.get("vendor_volume")
        if vol is not None and (type(vol) not in (float,int) or
            not math.isfinite(vol) or vol<0):
            raise ValueError("invalid_vendor_volume")
        if raw.get("volume_available") is not (vol is not None):
            raise ValueError("invalid_vendor_volume_availability")
        if vol is None:
            reasons.add("BAR_VOLUME_MISSING")
        else:
            volumecount+=1
            if vol==0:
                zero+=1
        if source=="boats-bars":
            if not (local.hour>=20 or local.hour<4):
                raise ValueError("outside_overnight")
            end_date=local.date()+(timedelta(days=1) if local.hour>=20 else timedelta())
            overnight[end_date.isoformat()].append((stamp,vol))
        elif not(4<=local.hour<20):
            reasons.add("NOT_REGISTERED_DAYTIME_PHASE")
    sess=[]
    for day,items in sorted(overnight.items()):
        expected,left,right=_request_clip(day,start,end)
        observed=len(items)
        if observed>expected:
            raise ValueError("more_bars_than_requested_minute_slots")
        sess.append(OvernightRequestCoverage(
          day,expected,observed,expected-observed,
          sum(v==0 for _,v in items),sum(v is None for _,v in items),left,right))
    if source!="eod-bars" and not rows:
        reasons.add("NO_RETAINED_MINUTE_ROWS_IN_PARTITION")
    if source not in ("boats-bars","eod-bars") and rows:
        reasons.add("SOURCE_CANNOT_ASSERT_CONSOLIDATED_EXECUTION_TRUTH")
    if not rows or vendor_symbol not in pilot or source=="eod-bars":
        # EOD daily observations cannot fill even a single S2 minute slot.
        in_pilot=()
    else:
        in_pilot=(vendor_symbol,)
    absent=tuple(x for x in pilot if x not in in_pilot)
    # This fingerprint binds *all* bounded source row bytes and their chosen
    # content/vintage, not an external entitlement, producer signature or PIT.
    docs=sorted((dict(item) for item in rows),key=lambda x:(
        str(x.get("ticker_vendor","")),str(x.get("bar_at_vendor",""))))
    fingerprint=m.digest({
       "source":source,"sha":selected["source_sha256"],
       "request_path":selected["source_request_path"],
       "observed":selected["source_observed_at_utc"],
       "purpose":selected["purpose"],"rows":docs,
       "expected_pilot_symbols":pilot})
    return TiingoSourceFitness(
        "factor_atlas.tiingo_source_fitness.v1",
        _STATUS[source],source,selected["source_sha256"],
        "RESEARCH_L1_NOT_CANONICAL",selected["source_observed_at_utc"],
        selected["purpose"],"tiingo",venue,scope,pilot,in_pilot,absent,
        (vendor_symbol,) if rows else (),len(rows),volumecount,zero,
        tuple(sess),tuple(sorted(reasons)),False,False,False,False,False,False,
        "RETROSPECTIVE_VENDOR_BAR_COVERAGE_NOT_CAPITAL_PRESSURE",
        fingerprint)


def aggregate_cohort_fitness(reviews: Iterable[TiingoSourceFitness], *,
                             required_symbols: tuple[str,...]=_PILOT) -> TiingoCohortFitness:
    """Aggregates *examined* archive partitions; never asserts fleet-wide absence."""
    pilot=_member_set(required_symbols)
    material=tuple(reviews)
    if not material or any(not isinstance(x,TiingoSourceFitness) for x in material):
        raise ValueError("source_fitness_samples_required")
    raw_hashes={}
    for item in material:
        # Tiingo producer fixed context aliasing; do not reintroduce it here.
        for symbol in item.observed_vendor_symbols:
            prior=raw_hashes.setdefault(item.source_sha256,symbol)
            if prior!=symbol:
                raise ValueError("source_sha_context_alias_collision")
    symbols=tuple(sorted({s for x in material for s in x.observed_vendor_symbols}))
    # Preserve EOD samples in the inventory but NEVER count daily histories
    # toward the registered one-minute Factor Atlas pressure population.
    one_minute_symbols={s for x in material if x.source!="eod-bars"
                        for s in x.observed_vendor_symbols}
    participating=tuple(x for x in pilot if x in one_minute_symbols)
    missing=tuple(x for x in pilot if x not in one_minute_symbols)
    outside=tuple(s for s in symbols if s not in pilot)
    result_hash=m.digest({"pilot":pilot,"audits":[
        (x.source,x.source_sha256,x.evidence_digest) for x in
        sorted(material,key=lambda x:(x.source,x.source_sha256,x.evidence_digest))]})
    return TiingoCohortFitness(
       "factor_atlas.tiingo_cohort_fitness.v1",
       len(material),symbols,pilot,participating,missing,outside,
       True,False,False,False,False,result_hash)

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
class DaytimeClockCoverage:
    """Nominal ET clock-grid accounting; NOT an exchange-calendar admission."""
    date_et: str
    nominal_rth_slots: int
    observed_rth_unique_minutes: int
    nominal_rth_missing_minutes: int
    nominal_rth_grid_complete: bool
    observed_pre_minutes: int
    observed_ah_minutes: int
    observed_before_04_minutes: int
    observed_after_20_minutes: int
    exchange_calendar_attested: bool = False


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
    daytime_clock_coverage: tuple[DaytimeClockCoverage,...]
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
    all_four_nominal_RTH_grids_complete_in_sample: bool
    calendar_and_volume_rights_admitted: bool
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
        # Tiingo's consolidated WebSocket documentation states that reference
        # prices (validated quote mids OR trade prints) create REST OHLC bars.
        # https://www.tiingo.com/documentation/websockets/equity-realtime-stock-data
        # Current documentation is a source-selection warning, NOT an attested
        # historical per-row lineage, adjustment vintage, or legal use grant.
        reasons.update({"CONSOLIDATED_VOLUME_UNIT_UNQUALIFIED",
                        "BETA_INTRADAY_SOURCE_NOT_CANONICALLY_ADMITTED",
                        "CONSOLIDATED_DERIVED_REFERENCE_OHLC_NOT_TRADE_PRICE_BASIS"})
    seen=set(); overnight=defaultdict(list); daytime=defaultdict(Counter)
    volumecount=zero=0
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
        else:
            # Only source-family appropriate one-minute rows enter the nominal
            # daytime grid. Do not fabricate an exchange calendar or source
            # permission from apparent clock completeness.
            minute_of_day=local.hour*60+local.minute
            day_counter=daytime[local.date().isoformat()]
            if minute_of_day<240:
                day_counter["before_04"]+=1
                reasons.add("NOT_REGISTERED_DAYTIME_PHASE")
            elif minute_of_day<570:
                day_counter["pre"]+=1
            elif minute_of_day<960:
                day_counter["rth"]+=1
            elif minute_of_day<1200:
                day_counter["ah"]+=1
            else:
                day_counter["after_20"]+=1
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
    day_report=[]
    if source in ("iex-bars","equity-intraday-bars"):
        for day,clock in sorted(daytime.items()):
            rth=clock["rth"]
            if rth>390:
                raise ValueError("nominal_rth_clock_grid_invalid")
            day_report.append(DaytimeClockCoverage(
                day,390,rth,390-rth,rth==390,
                clock["pre"],clock["ah"],clock["before_04"],
                clock["after_20"],False))
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
        tuple(sess),tuple(day_report),tuple(sorted(reasons)),
        False,False,False,False,False,False,
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
    # Clock-only four-name completeness is useful to prioritize owner
    # qualification, but does not authenticate PIT, venue reach, price/volume
    # adjustment, historic source availability, or redistribution rights.
    # Never cherry-pick competing partitions or dates to claim a full panel.
    consolidated=[x for x in material if x.source=="equity-intraday-bars"]
    single={}
    selected_days=[]
    for item in consolidated:
        if (len(item.observed_vendor_symbols)!=1 or
                len(item.daytime_clock_coverage)!=1):
            continue
        symbol=item.observed_vendor_symbols[0]
        if symbol in single:
            single[symbol]=None  # competing revisions need original owner selection
            continue
        single[symbol]=item
        selected_days.append(item.daytime_clock_coverage[0].date_et)
    complete=(len(consolidated)==len(pilot)
              and all(single.get(x) is not None and
                      single[x].daytime_clock_coverage[0].nominal_rth_grid_complete
                      for x in pilot)
              and len(set(selected_days))==1)
    result_hash=m.digest({"pilot":pilot,"audits":[
        (x.source,x.source_sha256,x.evidence_digest) for x in
        sorted(material,key=lambda x:(x.source,x.source_sha256,x.evidence_digest))]})
    return TiingoCohortFitness(
       "factor_atlas.tiingo_cohort_fitness.v1",
       len(material),symbols,pilot,participating,missing,outside,
       True,complete,False,False,False,False,False,result_hash)


# The original Tiingo Data OS security-search source is RAW_ONLY: there is no
# admitted L1 identity projector. Accept ALREADY-VERIFIED in-memory source
# values only; all selection and canonical alias authority stays with Data OS.
@dataclass(frozen=True)
class TiingoSecuritySearchFitness:
    schema: str
    status: str
    source_type: str
    requested_symbol: str
    original_source_sha256: str
    original_receipt_id: str
    original_source_observed_at_utc: str
    decision_at_utc: str
    total_owner_search_rows: int
    US_exact_matches: int
    nonUS_exact_matches: int
    foreign_country_collision_observed: bool
    us_asset_type: str | None
    candidate_us_vendor_permaticker: str | None
    vendor_composite_figi_present: bool
    source_known_before_decision: bool
    canonical_dataos_ETF_security_id_selected: bool
    us_exchange_mic_verified: bool
    original_owner_pit_alias_binding_admitted: bool
    pit_vendor_alias_admitted: bool
    source_rights_or_trading_basis_admitted: bool
    market_pilot_admitted: bool
    may_rank_or_trade: bool
    customer_publishable: bool
    refusals: tuple[str,...]
    input_digest: str
    authority: tuple[tuple[str,bool],...]=m.AUTHORITY


def inspect_tiingo_security_search(
    owner_raw_receipt: Mapping[str,object],
    owner_verified_search_results: Iterable[Mapping[str,object]], *,
    expected_symbol: str,
    decision_at_utc: str
) -> TiingoSecuritySearchFitness:
    """Negative admission for original RAW_ONLY Tiingo security-search input.

    Does not fetch/retain source bytes, select a Data OS security/listing,
    issue a vendor ID, or grant a PIT source/market trading license.
    """
    if not isinstance(owner_raw_receipt,Mapping):
        raise ValueError("original_security_source_receipt_required")
    source=owner_raw_receipt.get("source")
    if source!="security-search":
        raise ValueError("security_search_source_family_required")
    if (type(expected_symbol) is not str or
            not _SYMBOL.fullmatch(expected_symbol)):
        raise ValueError("expected_vendor_symbol_invalid")
    request=f"/tiingo/utilities/search?query={expected_symbol}"
    if owner_raw_receipt.get("request_path")!=request:
        raise ValueError("source_query_identity_mismatch")
    ssha=owner_raw_receipt.get("raw_sha256")
    receipt_id=owner_raw_receipt.get("receipt_id")
    if (type(ssha) is not str or not _SHA.fullmatch(ssha) or
        type(receipt_id) is not str or not _SHA.fullmatch(receipt_id)):
        raise ValueError("source_receipt_digest_invalid")
    observed=owner_raw_receipt.get("observed_at_utc")
    observed_clock=_timestamp(observed,"search_clock")
    # Original source-receipt known-at is conservatively CEILED when the
    # vendor records fractional nanoseconds beyond Python microseconds.
    # Decision cutoffs remain floored, so late source evidence cannot leak.
    fraction=re.search(r"\.(\d+)(?:Z|[+-]\d{2}:\d{2})$",observed)
    if fraction and any(c!="0" for c in fraction.group(1)[6:]):
        observed_clock+=timedelta(microseconds=1)
    cutoff=_timestamp(decision_at_utc,"search_clock")
    known=observed_clock<=cutoff
    results=tuple(owner_verified_search_results)
    if len(results)>50 or any(not isinstance(x,Mapping) for x in results):
        raise ValueError("bounded_search_rows_required")
    candidates=[r for r in results if r.get("ticker")==expected_symbol]
    us=[r for r in candidates if r.get("countryCode")=="US"]
    foreign=[r for r in candidates if r.get("countryCode")!="US"]
    match=us[0] if len(us)==1 else None
    refusals={
       "DATA_OS_PIT_ALIAS_NOT_SELECTED",
       "VENDOR_SECURITY_ID_NOT_CANONICAL",
       "DATASET_RIGHTS_OR_PRICE_VOLUME_BASIS_NOT_ATTESTED",
    }
    if foreign:
        refusals.add("COUNTRY_DUPLICATE_TICKER")
    if not known:
        refusals.add("SOURCE_FIRST_OBSERVED_AFTER_DECISION")
    expected_asset="ETF" if expected_symbol=="SPY" else "Stock"
    candidate_ref=None
    figi=False
    asset_type=None
    if not us:
        status="NO_US_VENDOR_REFERENCE"
        refusals.add("US_REFERENCE_MISSING")
    elif len(us)!=1:
        status="MULTIPLE_US_VENDOR_REFERENCES"
        refusals.add("AMBIGUOUS_US_REFERENCE")
    else:
        asset_type=match.get("assetType")
        if asset_type!=expected_asset:
            status="EXPECTED_INSTRUMENT_CLASS_MISMATCH"
            refusals.add("ASSET_CLASS_NOT_QUALIFIED")
        elif match.get("isActive") is not True:
            status="INACTIVE_US_VENDOR_REFERENCE"
            refusals.add("REFERENCE_INACTIVE_AT_SOURCE_TIME")
        else:
            perma=match.get("permaTicker")
            figi_string=match.get("openFIGIComposite")
            if (type(perma) is not str or
                not re.fullmatch(r"US[A-Z0-9]{10,20}",perma) or
                type(figi_string) is not str or
                not re.fullmatch(r"[A-Z0-9]{8,20}",figi_string)):
                status="US_VENDOR_IDENTITY_INCOMPLETE"
                refusals.add("US_REFERENCE_MISSING_VENDOR_IDENTITY")
            else:
                candidate_ref=perma
                figi=True
                if not known:
                    status="RETROSPECTIVE_VENDOR_REFERENCE_NOT_PIT"
                else:
                    status="VENDOR_REFERENCE_CANDIDATE_NOT_CANONICAL"

    source_digest=m.digest({
        "source":"security-search","original_raw_sha256":ssha,
        "original_receipt_id":receipt_id,
        "original_request_path":request,
        "source_observed_at":observed,
        "decision_at_utc":cutoff.isoformat(),
        "selected_source_rows":[
           {"ticker":v.get("ticker"),
            "countryCode":v.get("countryCode"),
            "assetType":v.get("assetType"),
            "isActive":v.get("isActive"),
            "permaTicker":v.get("permaTicker"),
            "openFIGIComposite":v.get("openFIGIComposite"),
            "name":v.get("name")}
            for v in sorted(results,key=lambda x:(
                str(x.get("ticker")),str(x.get("countryCode")),
                str(x.get("permaTicker")),str(x.get("openFIGIComposite"))))
        ]
    })
    return TiingoSecuritySearchFitness(
       "factor_atlas.tiingo_security_search_fitness.v1",
       status,"security-search",expected_symbol,ssha,receipt_id,
       observed,cutoff.isoformat(),len(results),len(us),len(foreign),
       bool(foreign),asset_type,candidate_ref,figi,known,
       False,False,False,False,False,False,False,False,
       tuple(sorted(refusals)),source_digest)

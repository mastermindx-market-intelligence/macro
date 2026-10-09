"""TP-1 source-owner RTH soak metrics, WITHOUT creating an acceptance plane.

The same TP-1 incumbent owner supplies authenticated *outside this function*
a bounded cohort's connection seconds, quote-join reason counts, volumes and
grouped-daily comparable reference receipts. This pure diagnostic computes
ratios but never claims those inputs are genuine, never opens a vendor feed,
never admits production, never deploys or approves a signal.

Frozen Massive TP-1 numerics: >=99% connected RTH pilot seconds, >=95% lit
prints classified against a qualified <=5s NBBO, and >=90% eligible symbol
volumes within 2% of a SAME-SCOPE grouped-daily reference. TRF/halts/unknown
venues remain explicitly separate.

Reference: research/MASSIVE_ADVANCED_INTEGRATION_MASTERPLAN_BY_FABLE.md §0.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from engine.tick_plane.minute_projection import SCHEMA as TP1_MINUTE_SCHEMA, MINUTE_NS
from hashlib import sha256
import json
import re

SCHEMA = "equity.tick_plane.pilot_soak_diagnostics/v0"
MAX_PILOT_SYMBOLS = 600
_LIT_FLOOR = Decimal("0.95")
_CONNECTED_FLOOR = Decimal("0.99")
_VOLUME_NAMES_FLOOR = Decimal("0.90")
_VOLUME_DIFF_CEILING = Decimal("0.02")
_TICKER = re.compile(r"^[A-Z][A-Z0-9.\-]{0,19}$")
_SCOPES = frozenset({"RTH", "FULL_DAY"})
_STATES = frozenset({"ELIGIBLE", "HALT_REOPEN_CARVEOUT", "SOURCE_UNQUALIFIED"})
_FIELDS = frozenset({
    "ticker", "state", "session_scope", "reference_scope",
    "lit_eligible_prints", "lit_classified_quote_le5s_prints",
    "lit_classified_quote_gt5s_prints", "lit_unclassified_prints",
    "trf_prints", "unknown_venue_prints", "lit_unknown_reason_counts",
    "source_volume_shares", "reference_volume_shares",
    "carveout_reason", "source_receipt", "reference_receipt",
})


class PilotEvidenceRefusal(ValueError):
    """Invalid source evidence shape, not a failed market performance metric."""


def _int(value, field, *, min_value=0):
    if type(value) is not int or value < min_value:
        raise PilotEvidenceRefusal(f"{field} requires integer >= {min_value}")
    return value


def _str(value, field):
    if not isinstance(value, str) or not value.strip() or len(value) > 512:
        raise PilotEvidenceRefusal(f"{field} requires nonempty bounded string")
    return value


def _shares(value, field, *, optional=False):
    if value is None and optional:
        return None
    if type(value) is not str:
        raise PilotEvidenceRefusal(f"{field} requires an exact decimal string")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise PilotEvidenceRefusal(f"{field} invalid decimal") from exc
    if not number.is_finite() or number < 0:
        raise PilotEvidenceRefusal(f"{field} invalid nonnegative shares")
    return number


def _fmt(value):
    return format(value, "f")


def _gate(ratio, threshold):
    if ratio is None:
        return "NOT_MEASURABLE"
    return "NUMERIC_MET" if ratio >= threshold else "NUMERIC_NOT_MET"


def summarize_tp1_soak_evidence(
    *, session, expected_session_seconds, connected_seconds,
    measurement_cutoff_ns, source_manifest_sha256, source_manifest_known_ns,
    cohort,
):
    """Return bounded, source-unverified numeric diagnostics, not acceptance.

    The caller's claimed original host/market/GHA source receipts are never
    authenticated by this deterministic function. Downstream operators must
    verify actual SIP/market-time source, RTH status, source/condition
    eligibility and grouped-daily scope *independently* before using results.
    """
    _str(session, "session")
    if not session.endswith(":RTH"):
        raise PilotEvidenceRefusal("first TP-1 soak diagnostic is RTH only")
    _int(expected_session_seconds, "expected_session_seconds", min_value=1)
    _int(connected_seconds, "connected_seconds")
    if connected_seconds > expected_session_seconds:
        raise PilotEvidenceRefusal("connected seconds exceed observed session")
    _int(measurement_cutoff_ns, "measurement_cutoff_ns", min_value=1)
    _int(source_manifest_known_ns, "source_manifest_known_ns", min_value=1)
    if source_manifest_known_ns > measurement_cutoff_ns:
        raise PilotEvidenceRefusal("future source snapshot cannot be known at cutoff")
    if (not isinstance(source_manifest_sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", source_manifest_sha256) is None):
        raise PilotEvidenceRefusal("source manifest must have source-bound SHA256")
    if not isinstance(cohort, (list,tuple)) or not 1 <= len(cohort) <= MAX_PILOT_SYMBOLS:
        raise PilotEvidenceRefusal("bounded nonempty frozen pilot cohort required")

    observed = set()
    per_symbol = []
    coverage_lit = 0
    qualified_lit = 0
    n_carveouts = n_unqualified = 0
    volume_names = volume_within = 0
    missing_reference = wrong_scope = zero_reference = 0
    unknown_reasons = {}
    for row in cohort:
        if not isinstance(row,dict) or set(row) != _FIELDS:
            raise PilotEvidenceRefusal("pilot row has unknown or missing fields")
        ticker=row["ticker"]
        if not isinstance(ticker,str) or _TICKER.fullmatch(ticker) is None or ticker in observed:
            raise PilotEvidenceRefusal("invalid or duplicate pilot symbol")
        observed.add(ticker)
        state=row["state"]
        if state not in _STATES:
            raise PilotEvidenceRefusal("invalid source qualification class")
        source_scope=row["session_scope"]
        ref_scope=row["reference_scope"]
        if source_scope not in _SCOPES or ref_scope not in (*_SCOPES,None):
            raise PilotEvidenceRefusal("invalid source or grouped-daily session scope")
        if source_scope != "RTH":
            raise PilotEvidenceRefusal("source scope differs from claimed RTH session")
        counts={}
        for key in ("lit_eligible_prints","lit_classified_quote_le5s_prints",
                    "lit_classified_quote_gt5s_prints","lit_unclassified_prints",
                    "trf_prints","unknown_venue_prints"):
            counts[key]=_int(row[key],key)
        total=counts["lit_eligible_prints"]
        recent=counts["lit_classified_quote_le5s_prints"]
        old=counts["lit_classified_quote_gt5s_prints"]
        unknown=counts["lit_unclassified_prints"]
        if total != recent+old+unknown:
            raise PilotEvidenceRefusal("lit classification denominator inconsistent")
        problems=row["lit_unknown_reason_counts"]
        if not isinstance(problems,dict) or len(problems)>100:
            raise PilotEvidenceRefusal("bounded source unknown-reason accounting required")
        for reason,n in problems.items():
            _str(reason,"unknown reason")
            _int(n,"unknown reason count")
        if sum(problems.values()) != unknown:
            raise PilotEvidenceRefusal("unclassified lit prints missing typed reasons")
        source_volume=_shares(row["source_volume_shares"],"source_volume_shares")
        reference_volume=_shares(row["reference_volume_shares"],
                                 "reference_volume_shares",optional=True)
        source_receipt=_str(row["source_receipt"],"source_receipt")
        reference_receipt=row["reference_receipt"]
        if reference_receipt is not None:
            _str(reference_receipt,"reference_receipt")
        if (reference_volume is None) != (reference_receipt is None):
            raise PilotEvidenceRefusal("grouped reference value and receipt disagree")
        reason=row["carveout_reason"]
        if state=="ELIGIBLE":
            if reason is not None:
                raise PilotEvidenceRefusal("qualified name cannot contain carveout")
            coverage_lit+=total
            qualified_lit+=recent
        else:
            if not isinstance(reason,str) or not reason.strip():
                raise PilotEvidenceRefusal("noneligible name needs typed carveout reason")
            if state=="HALT_REOPEN_CARVEOUT":
                n_carveouts+=1
            else:
                n_unqualified+=1
        for kind,n in problems.items():
            unknown_reasons[kind]=unknown_reasons.get(kind,0)+n
        discrepancy=None
        if state=="ELIGIBLE":
            if reference_volume is None:
                missing_reference+=1
            elif ref_scope!=source_scope:
                wrong_scope+=1
            elif reference_volume==0:
                zero_reference+=1
            else:
                discrepancy=abs(source_volume-reference_volume)/reference_volume
                volume_names+=1
                if discrepancy <= _VOLUME_DIFF_CEILING:
                    volume_within+=1
        per_symbol.append({
            "ticker":ticker, "state":state,
            "lit_eligible_prints":total, "lit_classified_le5s":recent,
            "lit_classified_older_than5s":old,"lit_unknown":unknown,
            "trf_prints":counts["trf_prints"],
            "unknown_venue_prints":counts["unknown_venue_prints"],
            "source_volume_shares":_fmt(source_volume),
            "reference_volume_shares":_fmt(reference_volume) if reference_volume is not None else None,
            "volume_discrepancy":_fmt(discrepancy) if discrepancy is not None else None,
            "source_scope":source_scope, "reference_scope":ref_scope,
            "carveout_reason":reason,
            "reference_comparable":discrepancy is not None,
        })
    eligible_names=sum(x["state"]=="ELIGIBLE" for x in per_symbol)
    connected_ratio=Decimal(connected_seconds)/Decimal(expected_session_seconds)
    lit_ratio=(Decimal(qualified_lit)/Decimal(coverage_lit) if coverage_lit else None)
    volume_ratio=(Decimal(volume_within)/Decimal(volume_names) if volume_names else None)
    unqualified_numerics=(
        n_unqualified>0 or missing_reference>0 or wrong_scope>0
        or zero_reference>0 or eligible_names==0 or coverage_lit==0
    )
    checked={"connected_seconds":_gate(connected_ratio,_CONNECTED_FLOOR),
             "qualified_lit_quote_le5s":_gate(lit_ratio,_LIT_FLOOR),
             "eligible_volume_names_le2pct":_gate(volume_ratio,_VOLUME_NAMES_FLOOR)}
    provisional_numeric_state=(
        "INSUFFICIENT_COMPARABLE_EVIDENCE" if unqualified_numerics
        else "NUMERIC_THRESHOLDS_MET" if all(v=="NUMERIC_MET" for v in checked.values())
        else "NUMERIC_THRESHOLDS_NOT_MET"
    )
    canonical=sorted(per_symbol,key=lambda x:x["ticker"])
    return {
        "schema":SCHEMA, "authority":"UNVERIFIED_SOURCE_DIAGNOSTIC_ONLY",
        "session":session, "source_manifest_sha256":source_manifest_sha256,
        "source_manifest_known_ns":source_manifest_known_ns,
        "measurement_cutoff_ns":measurement_cutoff_ns,
        "n_frozen_symbols":len(cohort),"n_eligible_symbols":eligible_names,
        "n_halt_reopen_carveouts":n_carveouts,
        "n_unqualified_symbols":n_unqualified,
        "source_unknown_reason_totals":dict(sorted(unknown_reasons.items())),
        "connected_session_seconds":connected_seconds,
        "expected_session_seconds":expected_session_seconds,
        "fraction_connected":_fmt(connected_ratio),
        "lit_eligible_prints":coverage_lit,
        "lit_signed_within_5s":qualified_lit,
        "lit_5s_classification_coverage":_fmt(lit_ratio) if lit_ratio is not None else None,
        "n_volume_comparable_symbols":volume_names,
        "n_volume_within_2pct":volume_within,
        "volume_names_within_2pct_fraction":_fmt(volume_ratio) if volume_ratio is not None else None,
        "n_missing_grouped_reference":missing_reference,
        "n_mismatched_reference_scope":wrong_scope,
        "n_zero_reference_denominator":zero_reference,
        "numeric_checks":checked,
        "provisional_numeric_state":provisional_numeric_state,
        "source_quality_receipts_authenticity":"REQUIRES_EXTERNAL_INCUMBENT_SOURCE_PROOF",
        "independent_semantic_review":None,
        "production_source_acceptance":None,
        "enabled_to_trade_or_rank":False,
        "absorption_signal":None,
        "cohort_metrics_sha256":sha256(json.dumps(canonical,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
        "per_symbol_metrics":canonical,
    }



def cohort_row_from_source_minutes(
    *, ticker, session, minute_observations, expected_session_minutes,
    reference_volume_shares, reference_scope, reference_receipt,
    halt_reopen_reason=None,
):
    """Project TP-1 native minute shares/ages into a pilot diagnostic row.

    This is a NON-AUTHENTICATING convenience projection of incumbent TP-1
    evidence, not an RTH clock, receipt validator or independent data source.
    A missing minute, unknown source volume, quote/venue/sale-policy generation
    ambiguity, or incomplete source policy disqualifies numeric acceptance.
    """
    _str(ticker, "ticker")
    if _TICKER.fullmatch(ticker) is None:
        raise PilotEvidenceRefusal("invalid pilot ticker")
    _str(session, "session")
    if not session.endswith(":RTH"):
        raise PilotEvidenceRefusal("pilot input requires RTH scope")
    _int(expected_session_minutes, "expected_session_minutes", min_value=1)
    if expected_session_minutes > 390:
        raise PilotEvidenceRefusal("RTH minute budget exceeds a regular session")
    if not isinstance(minute_observations, (list,tuple)) or not minute_observations:
        raise PilotEvidenceRefusal("at least one source minute required")
    if len(minute_observations)>390:
        raise PilotEvidenceRefusal("unbounded source minute cohort")
    if reference_scope not in (*_SCOPES, None):
        raise PilotEvidenceRefusal("invalid grouped reference scope")
    _shares(reference_volume_shares,"reference_volume_shares",optional=True)
    if (reference_volume_shares is None)!=(reference_receipt is None):
        raise PilotEvidenceRefusal("grouped reference shares and receipt mismatch")
    if reference_receipt is not None:
        _str(reference_receipt,"reference_receipt")
    if halt_reopen_reason is not None:
        _str(halt_reopen_reason,"halt_reopen_reason")

    minutes=sorted(minute_observations,key=lambda m:m.get("start_ns",-1)
                   if isinstance(m,dict) else -1)
    counters={
        "lit_eligible_prints":0,
        "lit_classified_quote_le5s_prints":0,
        "lit_classified_quote_gt5s_prints":0,
        "lit_unclassified_prints":0,
        "trf_prints":0,
        "unknown_venue_prints":0,
    }
    conditions=set()
    exchanges=set()
    quotes=set()
    ages=set()
    source_volume=Decimal(0)
    source_unknown_volume=Decimal(0)
    lit_source_unqualified=0
    reasons={}
    receipts=[]
    first=None
    for minute in minutes:
        if not isinstance(minute,dict) or minute.get("schema")!=TP1_MINUTE_SCHEMA:
            raise PilotEvidenceRefusal("source minute schema not TP-1")
        if (minute.get("state")!="PROVISIONAL_MEASURED_CONTEXT"
                or minute.get("authority")!="OBSERVATIONAL_PROVISIONAL_ONLY"
                or minute.get("correction_status")!="STREAM_PROVISIONAL_UNRECONCILED"
                or minute.get("ticker")!=ticker or minute.get("session")!=session
                or minute.get("source_mode")!="ACTUAL_AS_SEEN_ONLY_WHEN_OWNER_PROVES_RECEIPTS"
                or minute.get("absorption_signal") is not None):
            raise PilotEvidenceRefusal("source minute identity/authority/finality mismatch")
        start=_int(minute.get("start_ns"),"minute.start_ns")
        end=_int(minute.get("end_ns"),"minute.end_ns")
        if end-start!=MINUTE_NS or start%MINUTE_NS:
            raise PilotEvidenceRefusal("unqualified minute event window")
        if first is None:
            first=start
        if start != first + MINUTE_NS*len(receipts):
            raise PilotEvidenceRefusal("missing or duplicate source minute")
        decision=_int(minute.get("decision_ns"),"minute.decision_ns")
        wm=_int(minute.get("watermark_available_ns"),"minute.watermark_available_ns")
        complete=_int(minute.get("source_complete_through_ns"),"minute.source_complete_through_ns")
        if complete < end or wm<complete or wm>decision:
            raise PilotEvidenceRefusal("source minute completeness receipt not matured")
        record_sha=minute.get("source_observation_sha256")
        if not isinstance(record_sha,str) or re.fullmatch("[0-9a-f]{64}",record_sha) is None:
            raise PilotEvidenceRefusal("source minute missing original observation digest")
        receipt=_str(minute.get("source_watermark_receipt"),"source_watermark_receipt")
        for output_name,source_name in (
            ("lit_eligible_prints","n_lit_eligible_prints"),
            ("lit_classified_quote_le5s_prints","n_lit_classified_quote_le5s_prints"),
            ("lit_classified_quote_gt5s_prints","n_lit_classified_quote_gt5s_prints"),
            ("lit_unclassified_prints","n_lit_unclassified_prints"),
            ("trf_prints","n_trf"),
            ("unknown_venue_prints","n_unknown_venue"),
        ):
            counters[output_name]+=_int(minute.get(source_name),source_name)
        lit_source_unqualified+=_int(minute.get("n_lit_source_unqualified_prints"),
                                      "n_lit_source_unqualified_prints")
        n_lit=_int(minute.get("n_lit"),"n_lit")
        n_trf=_int(minute.get("n_trf"),"n_trf")
        n_other=_int(minute.get("n_unknown_venue"),"n_unknown_venue")
        n_sampled=_int(minute.get("n_sampled_prints"),"n_sampled_prints")
        lit_policy_unknown=_int(minute.get("n_lit_source_unqualified_prints"),
                                "n_lit_source_unqualified_prints")
        lit_eligible=_int(minute.get("n_lit_eligible_prints"),"n_lit_eligible_prints")
        if (n_lit+n_trf+n_other!=n_sampled
                or lit_eligible+lit_policy_unknown>n_lit
                or _int(minute.get("n_lit_unclassified_prints"),
                        "n_lit_unclassified_prints")>
                   _int(minute.get("n_unclassified"),"n_unclassified")):
            raise PilotEvidenceRefusal("source minute venue/eligible count denominators inconsistent")
        classified=_int(minute.get("n_buy_proxy"),"n_buy_proxy")+(
            _int(minute.get("n_sell_proxy"),"n_sell_proxy")
            +_int(minute.get("n_midpoint"),"n_midpoint"))
        age_classified=(
            _int(minute.get("n_lit_classified_quote_le5s_prints"),
                 "n_lit_classified_quote_le5s_prints")
            +_int(minute.get("n_lit_classified_quote_gt5s_prints"),
                  "n_lit_classified_quote_gt5s_prints")
        )
        if classified!=age_classified:
            raise PilotEvidenceRefusal("source minute signed-print age bands inconsistent")
        r=minute.get("lit_unknown_reason_counts")
        if not isinstance(r,dict) or len(r)>100:
            raise PilotEvidenceRefusal("source minute unknown lit reasons not tracked")
        for k,v in r.items():
            _str(k,"lit unknown reason")
            reasons[k]=reasons.get(k,0)+_int(v,"lit unknown reason count")
        for group,key in ((conditions,"condition_rules_ref"),
                          (exchanges,"exchange_reference_sha256"),
                          (quotes,"quote_condition_rules_sha256")):
            value=minute.get(key)
            if value is not None:
                if not isinstance(value,str) or re.fullmatch("[0-9a-f]{64}",value) is None:
                    raise PilotEvidenceRefusal("unqualified reference digest")
                group.add(value)
        ages.add(_int(minute.get("max_quote_age_ns"),"minute.max_quote_age_ns"))
        included=_shares(minute.get("source_volume_included_shares"),"source_volume_included_shares")
        unknown=_shares(minute.get("source_volume_unknown_shares"),"source_volume_unknown_shares")
        excluded=_shares(minute.get("source_volume_excluded_shares"),"source_volume_excluded_shares")
        total=_shares(minute.get("source_all_printed_shares"),"source_all_printed_shares")
        if included+unknown+excluded != total:
            raise PilotEvidenceRefusal("source minute native share-volume denominator mismatch")
        volume_counts=[
            _int(minute.get(name),name) for name in (
                "n_source_volume_included_prints",
                "n_source_volume_excluded_prints",
                "n_source_volume_unknown_prints",
            )
        ]
        if sum(volume_counts)!=_int(minute.get("n_sampled_prints"),"n_sampled_prints"):
            raise PilotEvidenceRefusal("source minute share eligibility counts inconsistent")
        if any((amount==0) != (n==0) for amount,n in zip(
            (included,excluded,unknown), volume_counts
        )):
            raise PilotEvidenceRefusal("source share quantities and print counts disagree")
        if (_int(minute.get("max_quote_age_ns"),"max_quote_age_ns") <= 5_000_000_000
                and _int(minute.get("n_lit_classified_quote_gt5s_prints"),
                         "n_lit_classified_quote_gt5s_prints") > 0):
            raise PilotEvidenceRefusal("impossible 5s quote-age bucket from tighter policy")
        source_volume+=included
        source_unknown_volume+=unknown
        receipts.append((start,end,decision,receipt,record_sha))
    if (sum(reasons.values())!=counters["lit_unclassified_prints"]
            or counters["lit_eligible_prints"] != sum(counters[k] for k in (
                "lit_classified_quote_le5s_prints",
                "lit_classified_quote_gt5s_prints",
                "lit_unclassified_prints",
            ))):
        raise PilotEvidenceRefusal("source minute lit classification counters inconsistent")

    bad=[]
    if len(minutes)!=expected_session_minutes:
        bad.append("PARTIAL_MINUTE_COVERAGE")
    if source_unknown_volume:
        bad.append("UNKNOWN_SOURCE_VOLUME_CONDITION")
    if lit_source_unqualified:
        bad.append("LIT_SOURCE_POLICY_UNQUALIFIED")
    if any(len(g)!=1 for g in (conditions,exchanges,quotes,ages)):
        bad.append("MIXED_OR_MISSING_SOURCE_POLICY_GENERATION")
    if halt_reopen_reason is not None:
        state="HALT_REOPEN_CARVEOUT"
        note=halt_reopen_reason
    elif bad:
        state="SOURCE_UNQUALIFIED"
        note=";".join(bad)
    else:
        state="ELIGIBLE"
        note=None
    receipt_digest=sha256(json.dumps({
        "source_minute_receipts":receipts,
        "expected_session_minutes":expected_session_minutes,
        "source_volume_shares":_fmt(source_volume),
        "source_unknown_volume_shares":_fmt(source_unknown_volume),
        "conditions":sorted(conditions),
        "exchanges":sorted(exchanges),
        "quote_policies":sorted(quotes),
        "quote_age_limits":sorted(ages),
    },sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return {
        "ticker":ticker,"state":state,
        "session_scope":"RTH", "reference_scope":reference_scope,
        **counters,
        "lit_unknown_reason_counts":dict(sorted(reasons.items())),
        "source_volume_shares":_fmt(source_volume),
        "reference_volume_shares":reference_volume_shares,
        "carveout_reason":note,
        "source_receipt":"tp1-minute-cohort:"+receipt_digest,
        "reference_receipt":reference_receipt,
    }

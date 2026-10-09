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

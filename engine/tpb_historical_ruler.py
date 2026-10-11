"""TP-B private, source-free off-exchange record and intraday baseline candidates.

Consumes only frozen, source-owner supplied reconciliation snapshots. Does not
fetch Massive/FINRA, hold credentials, assert capture authenticity, reconstruct
native corrections, create R2 storage, serve public consumers, sign trades,
rank investment opportunities or issue alerts. In particular, a TRF print is
not a named ATS or an inferred buyer/seller.

The source owner proves RTH calendar, source watermark, correction chain,
venue/condition rules, grouped denominator, split basis and actual receipt time.
Q03's basis vintage may inform that owner; its research-only module is not
silently promoted or reimplemented here. Q10/Q11 likewise remain research-only.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation, localcontext
from hashlib import sha256
import json
import re
from statistics import median

SCHEMA = "equity.tp_b.historical_ruler/v0"
SNAPSHOT = "equity.tp_b.source_snapshot/v0"
CALIBRATION = "equity.tp_b.history_calibration/v0"
MAX_PRINTS = 20000
MAX_MINUTES = 390
MAX_HISTORY = 1500
MAX_DECIMAL_WIDTH = 128
MINUTE_NS = 60_000_000_000
CLUSTER_NS = 60_000_000_000
_BLOCK_TIERS = (100000, 500000, 1000000)
_SHA = re.compile(r"^[0-9a-f]{64}$")
_SYM = re.compile(r"^[A-Z][A-Z0-9.\-]{0,19}$")
_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}:RTH$")
_ALLOWED = {"ACTIVE", "CANCELLED"}
_PRINT_KEYS = frozenset({
    "native_id", "revision", "action", "sip_ns", "original_available_ns",
    "participant_ns", "trf_report_ns", "price", "shares",
    "venue", "exchange_id", "trf_id",
    "volume_eligible", "source_receipt_sha256",
})
_POINT_KEYS = frozenset({
    "minute_index", "cumulative_oe_shares", "cumulative_consolidated_shares",
    "source_receipt_sha256", "source_available_ns", "prefix_coverage_attested",
})
_SNAPSHOT_KEYS = frozenset({
    "schema", "ticker", "session", "start_ns", "end_ns",
    "asof_ns", "watermark_complete_ns", "watermark_available_ns",
    "source_manifest_sha256", "source_generation_sha256",
    "supersedes_generation_sha256", "calendar_sha256", "volume_policy_sha256",
    "exchange_reference_sha256", "split_basis_id", "split_basis_vintage_sha256",
    "split_segment", "source_owner_assertion", "source_scope",
    "full_rth_covered", "prints", "minutes",
})


class HistoricalRulerRefusal(ValueError):
    """An invalid observation must not turn into neutral or market-zero data."""


def _integer(x, label, *, minimum=0):
    if type(x) is not int or x < minimum or x.bit_length() > 64:
        raise HistoricalRulerRefusal(f"{label} requires a bounded native integer")
    return x


def _text(x, label, max_chars=180):
    if not isinstance(x, str) or not x.strip() or len(x) > max_chars:
        raise HistoricalRulerRefusal(f"{label} requires bounded source text")
    return x


def _sha(x, label):
    if not isinstance(x, str) or not _SHA.fullmatch(x):
        raise HistoricalRulerRefusal(f"{label} requires original SHA256")
    return x


def _amount(x, label, *, zero=False):
    if type(x) is not str or len(x) > MAX_DECIMAL_WIDTH + 16:
        raise HistoricalRulerRefusal(f"{label} requires bounded exact decimal text")
    try:
        d = Decimal(x)
    except InvalidOperation as exc:
        raise HistoricalRulerRefusal(f"{label} malformed decimal") from exc
    if not d.is_finite() or (d < 0 if zero else d <= 0):
        raise HistoricalRulerRefusal(f"{label} invalid nonnegative amount")
    tup = d.as_tuple()
    n, exponent = len(tup.digits), tup.exponent
    left = n + exponent
    width = (n + exponent if exponent >= 0 else
             n + 1 if left > 0 else 2 - left + n) + tup.sign
    if width > MAX_DECIMAL_WIDTH:
        raise HistoricalRulerRefusal(f"{label} unbounded decimal exponent")
    return d


def _fmt(d):
    return format(d, "f")


def _digest(payload):
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=True, allow_nan=False).encode()
    return sha256(raw).hexdigest()


def measure_source_snapshot(snapshot):
    """Build separated measured print/cluster/day objects; never authenticate them.

    One input per *current* native trade identity, with explicit current action
    and revision from the correction owner. This function DOES NOT replay or
    interpret upstream correction chains. Source generations remain immutable;
    a revised/cancelled generation requires an externally held predecessor ref.
    """
    from datetime import date
    if not isinstance(snapshot, dict) or set(snapshot) != _SNAPSHOT_KEYS:
        raise HistoricalRulerRefusal("snapshot must use strict frozen owner contract")
    s = snapshot
    if s["schema"] != SNAPSHOT or s["source_scope"] != "RTH":
        raise HistoricalRulerRefusal("snapshot source/scope mismatch")
    ticker = _text(s["ticker"], "ticker")
    if not _SYM.fullmatch(ticker):
        raise HistoricalRulerRefusal("invalid frozen ticker")
    session = _text(s["session"], "session")
    if not _DAY.fullmatch(session):
        raise HistoricalRulerRefusal("RTH session identity missing")
    try:
        date.fromisoformat(session[:10])
    except ValueError as exc:
        raise HistoricalRulerRefusal("invalid session calendar date") from exc
    start = _integer(s["start_ns"], "start_ns", minimum=1)
    end = _integer(s["end_ns"], "end_ns", minimum=1)
    cutoff = _integer(s["asof_ns"], "asof_ns", minimum=1)
    through = _integer(s["watermark_complete_ns"], "watermark_complete_ns", minimum=1)
    seen = _integer(s["watermark_available_ns"], "watermark_available_ns", minimum=1)
    if (start % MINUTE_NS or end % MINUTE_NS or end <= start
            or end-start > MAX_MINUTES*MINUTE_NS
            or through < start or seen < through or seen > cutoff):
        raise HistoricalRulerRefusal("calendar or original watermark contradictory")
    for key in ("source_manifest_sha256", "source_generation_sha256",
                "calendar_sha256", "volume_policy_sha256",
                "exchange_reference_sha256", "split_basis_vintage_sha256"):
        _sha(s[key], key)
    previous = s["supersedes_generation_sha256"]
    if previous is not None:
        _sha(previous, "supersedes_generation_sha256")
        if previous == s["source_generation_sha256"]:
            raise HistoricalRulerRefusal("self-superseding generation")
    basis = _text(s["split_basis_id"], "split_basis_id")
    segment = _text(s["split_segment"], "split_segment")
    if s["source_owner_assertion"] != "RECONCILED_AT_CUTOFF_UNVERIFIED_EXTERNALLY":
        raise HistoricalRulerRefusal("source owner qualification missing")
    if type(s["full_rth_covered"]) is not bool:
        raise HistoricalRulerRefusal("full RTH assertion must be explicit boolean")
    if s["full_rth_covered"] and through < end:
        raise HistoricalRulerRefusal("full RTH cannot precede session end")
    rows = s["prints"]
    points = s["minutes"]
    if (not isinstance(rows, list) or len(rows) > MAX_PRINTS
            or not isinstance(points, list) or len(points) > MAX_MINUTES):
        raise HistoricalRulerRefusal("bounded frozen prints/minutes required")

    prepared = []
    identities = set()
    cancelled = revised = unknown_policy = 0
    exact_precision = 2 * MAX_DECIMAL_WIDTH + 20
    for row in rows:
        if not isinstance(row, dict) or set(row) != _PRINT_KEYS:
            raise HistoricalRulerRefusal("print source shape not qualified")
        uid = _text(row["native_id"], "native_id")
        if uid in identities:
            raise HistoricalRulerRefusal("duplicate current native identity")
        identities.add(uid)
        revision = _integer(row["revision"], "print.revision")
        action = row["action"]
        if action not in _ALLOWED:
            raise HistoricalRulerRefusal("unresolved native correction action")
        if (revision > 0 or action == "CANCELLED") and previous is None:
            raise HistoricalRulerRefusal("changed/cancelled print missing prior generation")
        if action == "CANCELLED" and revision == 0:
            raise HistoricalRulerRefusal("cancel cannot be original native revision")
        stamp = _integer(row["sip_ns"], "print.sip_ns", minimum=1)
        available = _integer(row["original_available_ns"], "print.available_ns", minimum=1)
        if not start <= stamp < min(end, through) or not stamp <= available <= cutoff:
            raise HistoricalRulerRefusal("print clocks not knowable at source watermark")
        _sha(row["source_receipt_sha256"], "print.source_receipt_sha256")
        for clock_name in ("participant_ns", "trf_report_ns"):
            native_clock = row[clock_name]
            if native_clock is not None:
                _integer(native_clock, "print."+clock_name, minimum=1)
                if native_clock > available:
                    raise HistoricalRulerRefusal("original print clocks exceed source receipt")
        venue = row["venue"]
        if venue not in ("TRF", "LIT", "UNKNOWN"):
            raise HistoricalRulerRefusal("unknown source venue")
        if type(row["exchange_id"]) is not int or row["exchange_id"] < 0:
            raise HistoricalRulerRefusal("native exchange code invalid")
        pipe = row["trf_id"]
        if pipe is not None:
            _integer(pipe, "trf_id")
        if venue == "TRF" and (row["exchange_id"] != 4 or pipe not in (201, 202, 203)):
            raise HistoricalRulerRefusal("TRF pipe/exchange not source qualified")
        eligible = row["volume_eligible"]
        if eligible is not None and type(eligible) is not bool:
            raise HistoricalRulerRefusal("volume policy must be true/false/unknown")
        price = _amount(row["price"], "price")
        shares = _amount(row["shares"], "shares")
        with localcontext() as ctx:
            ctx.prec = exact_precision
            notional = price * shares
        if revision:
            revised += 1
        if action == "CANCELLED":
            cancelled += 1
            continue
        if eligible is None:
            unknown_policy += 1
        if venue != "TRF" or eligible is not True:
            continue
        prepared.append((stamp, uid, pipe, price, shares, notional,
                         row["participant_ns"], row["trf_report_ns"]))

    cumulative = []
    last_index = -1
    last_oe = last_total = Decimal(0)
    for point in points:
        if not isinstance(point, dict) or set(point) != _POINT_KEYS:
            raise HistoricalRulerRefusal("minute point shape not qualified")
        index = _integer(point["minute_index"], "minute_index")
        if index <= last_index or index >= (end-start)//MINUTE_NS:
            raise HistoricalRulerRefusal("minute indices not increasing in source")
        last_index = index
        available = _integer(point["source_available_ns"], "minute.available_ns", minimum=1)
        minute_end = start + (index+1)*MINUTE_NS
        if available > cutoff:
            raise HistoricalRulerRefusal("future minute point not available at cutoff")
        if available < minute_end:
            raise HistoricalRulerRefusal("minute point before its original source minute end")
        if minute_end > through:
            raise HistoricalRulerRefusal("minute prefix exceeds source watermark")
        if type(point["prefix_coverage_attested"]) is not bool:
            raise HistoricalRulerRefusal("minute prefix coverage assertion missing")
        _sha(point["source_receipt_sha256"], "minute.source_receipt")
        oe = _amount(point["cumulative_oe_shares"], "minute.oe", zero=True)
        total = _amount(point["cumulative_consolidated_shares"], "minute.consolidated", zero=True)
        if oe < last_oe or total < last_total or oe > total:
            raise HistoricalRulerRefusal("cumulative source counts or denominator contradict")
        last_oe, last_total = oe, total
        with localcontext() as ctx:
            ctx.prec = exact_precision
            same_minute_share = _fmt(oe / total) if total else None
        cumulative.append({
            "minute_index": index, "oe_shares": _fmt(oe),
            "consolidated_shares": _fmt(total),
            "share": same_minute_share,
            "qualified_prefix": point["prefix_coverage_attested"] and total > 0,
            "source_available_ns": available,
            "source_receipt_sha256": point["source_receipt_sha256"],
        })

    prepared.sort(key=lambda x: (x[0], x[1]))
    with localcontext() as ctx:
        ctx.prec = exact_precision
        total_shares = sum((x[4] for x in prepared), Decimal(0))
        total_notional = sum((x[5] for x in prepared), Decimal(0))
    prints = [x[5] for x in prepared]
    # Partition per exact TRF pipe/price before clustering. Other price
    # levels may interleave and must not split a valid same-level burst.
    by_level = defaultdict(list)
    for item in prepared:
        by_level[(item[2], item[3])].append(item)
    clusters = []
    for level in by_level.values():
        group = [level[0]]
        for item in level[1:]:
            # Anchored 60-second window prevents transitive-chained bursts.
            # SIP for a TRF event is a REPORT-TIME proxy, not fill causality.
            if item[0] - group[0][0] <= CLUSTER_NS:
                group.append(item)
            else:
                if len(group) >= 2:
                    clusters.append(group)
                group = [item]
        if len(group) >= 2:
            clusters.append(group)
    with localcontext() as ctx:
        ctx.prec = exact_precision
        cluster_notionals = [sum((r[5] for r in g), Decimal(0)) for g in clusters]
    tiers = {str(t): sum(n >= t for n in prints) for t in _BLOCK_TIERS}
    with localcontext() as ctx:
        ctx.prec = exact_precision
        tier_rates = {
            str(t): _fmt(Decimal(tiers[str(t)]) / len(prints)) if prints else None
            for t in _BLOCK_TIERS
        }
        tier_notional_shares = {
            str(t): _fmt(sum((n for n in prints if n >= t), Decimal(0)) / total_notional)
                    if total_notional else None
            for t in _BLOCK_TIERS
        }
    report_deltas = [r[0]-r[7] for r in prepared if r[7] is not None]
    state = ("NO_SAMPLED_PRINTS" if not rows else
             "NO_QUALIFIED_OFF_EXCHANGE_OBSERVED" if not prepared else
             "SOURCE_OBSERVATIONS_UNVERIFIED_EXTERNALLY")
    # No native identifiers or original quote/trade payloads in the output.
    return {
        "schema": SCHEMA, "state": state,
        "authority": "RESEARCH_MEASUREMENT_ONLY",
        "ticker": ticker, "session": session,
        "start_ns": start, "end_ns": end, "asof_ns": cutoff,
        "source_scope": "RTH", "full_rth_covered": s["full_rth_covered"],
        "source_manifest_sha256": s["source_manifest_sha256"],
        "source_generation_sha256": s["source_generation_sha256"],
        "snapshot_sha256": _digest(snapshot),
        "supersedes_generation_sha256": previous,
        "calendar_sha256": s["calendar_sha256"],
        "volume_policy_sha256": s["volume_policy_sha256"],
        "exchange_reference_sha256": s["exchange_reference_sha256"],
        "split_basis_id": basis, "split_basis_vintage_sha256": s["split_basis_vintage_sha256"],
        "split_segment": segment,
        "n_source_rows": len(rows), "n_trf_observed": len(prepared),
        "n_revised_rows": revised, "n_cancelled": cancelled,
        "n_unknown_volume_policy": unknown_policy,
        "n_participant_timestamps": sum(r[6] is not None for r in prepared),
        "n_trf_report_timestamps": len(report_deltas),
        "min_sip_minus_trf_report_ns": min(report_deltas) if report_deltas else None,
        "max_sip_minus_trf_report_ns": max(report_deltas) if report_deltas else None,
        "oe_source_shares": _fmt(total_shares) if rows else None,
        "oe_source_notional_usd": _fmt(total_notional) if rows else None,
        "largest_individual_print_usd": _fmt(max(prints)) if prints else None,
        "largest_cluster_usd": _fmt(max(cluster_notionals)) if clusters else None,
        "n_clusters": len(clusters),
        "absolute_block_tier_counts": tiers,
        "absolute_block_tier_rates": tier_rates,
        "absolute_block_tier_notional_fractions": tier_notional_shares,
        "minute_points_private_only": cumulative,
        "cluster_clock": "SIP_REPORT_TIME_PROXY_NOT_EXECUTION_CLOCK",
        "source_receipts_authenticated": False,
        "market_capture_completeness_proven": False,
        "public_delivery_allowed": False,
        "ranking_trading_alert_authority": False,
        "actor_identity": None,
        "signal": None,
    }


def _safe_measurement(record):
    """Permit only the observational output of the TP-B source boundary."""
    return (isinstance(record, dict)
            and record.get("schema") == SCHEMA
            and record.get("authority") == "RESEARCH_MEASUREMENT_ONLY"
            and record.get("source_scope") == "RTH"
            and record.get("public_delivery_allowed") is False
            and record.get("ranking_trading_alert_authority") is False
            and record.get("source_receipts_authenticated") is False
            and record.get("market_capture_completeness_proven") is False
            and record.get("signal") is None
            and record.get("actor_identity") is None
            and isinstance(record.get("snapshot_sha256"), str)
            and _SHA.fullmatch(record["snapshot_sha256"]) is not None
            and isinstance(record.get("minute_points_private_only"), list))


def calibrate_history(*, target, previous, minute_index, evaluation_ns, min_history=20):
    """Rank three distinct measurements and match the SAME minute, outcome blind.

    All historical sessions must be point-in-time available and in the same
    attested split segment. Future/corrected-later rows are not a source of
    retrospective live confidence. Exclusion reasons and sample Ns are explicit.
    """
    _integer(evaluation_ns, "evaluation_ns", minimum=1)
    index = _integer(minute_index, "minute_index")
    minimum = _integer(min_history, "min_history", minimum=2)
    if minimum > MAX_HISTORY:
        raise HistoricalRulerRefusal("history floor exceeds bounded source budget")
    if (not _safe_measurement(target)
            or target.get("state") != "SOURCE_OBSERVATIONS_UNVERIFIED_EXTERNALLY"):
        raise HistoricalRulerRefusal("target source/authority unqualified")
    if (type(target.get("asof_ns")) is not int
            or target["asof_ns"] > evaluation_ns
            or target["asof_ns"] < target.get("start_ns", 0)
            or (target.get("full_rth_covered") is True
                and target["asof_ns"] < target.get("end_ns", 0))):
        raise HistoricalRulerRefusal("target is not an as-of measured candidate")
    if index >= (target["end_ns"]-target["start_ns"])//MINUTE_NS:
        raise HistoricalRulerRefusal("minute index beyond source RTH session")
    if not isinstance(previous, (list, tuple)) or len(previous) > MAX_HISTORY:
        raise HistoricalRulerRefusal("bounded history required")
    names = set()
    eligible = []
    exclusions = Counter()
    for record in previous:
        if not isinstance(record, dict) or record.get("schema") != SCHEMA:
            raise HistoricalRulerRefusal("history row missing source contract")
        marker = record.get("session")
        if not isinstance(marker, str) or not _DAY.fullmatch(marker):
            raise HistoricalRulerRefusal("history row has invalid session identity")
        if marker in names:
            raise HistoricalRulerRefusal("duplicate historical session revisions; reconcile upstream")
        names.add(marker)
        if record.get("ticker") != target["ticker"] or marker >= target["session"]:
            exclusions["TICKER_OR_CAUSAL_DATE_MISMATCH"] += 1
        elif record.get("asof_ns", evaluation_ns+1) > evaluation_ns:
            exclusions["HISTORICAL_REVISION_NOT_AVAILABLE"] += 1
        elif record.get("source_scope") != "RTH":
            exclusions["HISTORICAL_SCOPE_UNQUALIFIED"] += 1
        elif (record.get("split_basis_id") != target["split_basis_id"]
                or record.get("split_basis_vintage_sha256") != target["split_basis_vintage_sha256"]
                or record.get("split_segment") != target["split_segment"]):
            exclusions["SPLIT_BASIS_INCOMPATIBLE"] += 1
        elif not _safe_measurement(record) or record.get("state") != "SOURCE_OBSERVATIONS_UNVERIFIED_EXTERNALLY":
            exclusions["HISTORICAL_SOURCE_UNQUALIFIED"] += 1
        else:
            eligible.append(record)
    eligible.sort(key=lambda x: x["session"])
    daily = {}
    labels = (
        ("SINGLE_PRINT", "largest_individual_print_usd"),
        ("SAME_LEVEL_CLUSTER", "largest_cluster_usd"),
        ("DAILY_TOTAL", "oe_source_notional_usd"),
    )
    for kind, field in labels:
        value = target.get(field)
        vals = [r[field] for r in eligible
                if r.get("full_rth_covered") is True and r.get(field) is not None]
        state = ("NOT_FULL_RTH" if target["full_rth_covered"] is not True else
                 "INSUFFICIENT_COMPARABLE_HISTORY" if len(vals) < minimum else
                 "NO_OBSERVED_OBJECT" if value is None else "OBSERVED_COVERAGE_ONLY")
        if state == "OBSERVED_COVERAGE_ONLY":
            now = _amount(value, field, zero=True)
            hist = [_amount(v, field, zero=True) for v in vals]
            higher = sum(v > now for v in hist)
            equal = sum(v == now for v in hist)
            daily[kind] = {
                "state": state, "rank_desc": higher+1,
                "tie_policy": "COMPETITION_RANK_DESC_WITH_TIES",
                "n_equal_prior": equal,
                "strict_new_record_in_observed_sample": higher == 0 and equal == 0,
                "n_prior": len(hist),
                "coverage_start": min(r["session"] for r in eligible
                                      if r.get("full_rth_covered") and r.get(field) is not None),
                "source_metric": field,
            }
        else:
            daily[kind] = {"state": state, "rank_desc": None,
                           "n_prior": len(vals), "source_metric": field}
    t_points = {x["minute_index"]: x for x in target["minute_points_private_only"]}
    point = t_points.get(index)
    minute_samples = []
    for record in eligible:
        for historical_point in record["minute_points_private_only"]:
            if historical_point["minute_index"] == index and historical_point["qualified_prefix"]:
                if historical_point["share"] is not None:
                    minute_samples.append((_amount(historical_point["share"], "history.share", zero=True),
                                           record["session"]))
                break
    minute = {"conditioning": "EXACT_MINUTE_INDEX_RTH_CUMULATIVE_ONLY",
              "minute_index": index, "n_prior": len(minute_samples),
              "coverage_start": min((x[1] for x in minute_samples), default=None),
              "share": point["share"] if point else None,
              "median": None, "mad": None, "robust_z": None,
              "midrank_percentile": None}
    if point is None or not point["qualified_prefix"] or point["share"] is None:
        minute["state"] = "TARGET_MINUTE_SOURCE_UNQUALIFIED"
    elif len(minute_samples) < minimum:
        minute["state"] = "INSUFFICIENT_MINUTE_MATCHED_HISTORY"
    else:
        with localcontext() as ctx:
            ctx.prec = 2*MAX_DECIMAL_WIDTH+20
            values = sorted(x[0] for x in minute_samples)
            center = median(values)
            dispersion = median(abs(x-center) for x in values)
            now = _amount(point["share"], "target.share", zero=True)
            minute["median"] = _fmt(center)
            minute["mad"] = _fmt(dispersion)
            minute["midrank_percentile"] = _fmt(
                (Decimal(sum(x < now for x in values))
                 +Decimal("0.5")*sum(x == now for x in values))/len(values))
            if dispersion == 0:
                minute["state"] = "NO_ROBUST_DISPERSION"
            else:
                minute["state"] = "OBSERVED_COVERAGE_ONLY"
                minute["robust_z"] = _fmt((now-center)/(dispersion*Decimal("1.4826")))
    return {
        "schema": CALIBRATION,
        "authority": "HISTORICAL_RESEARCH_CALIBRATION_ONLY",
        "target_session": target["session"], "ticker": target["ticker"],
        "target_snapshot_sha256": target["snapshot_sha256"],
        "evaluation_ns": evaluation_ns,
        "basis_id": target["split_basis_id"],
        "basis_vintage_sha256": target["split_basis_vintage_sha256"],
        "split_segment": target["split_segment"],
        "n_candidate_previous": len(previous), "n_comparable_previous": len(eligible),
        "excluded_previous": dict(sorted(exclusions.items())),
        "daily_object_ranks": daily,
        "minute_conditioned_baseline": minute,
        "lineage_source": "AS_OF_SOURCE_OWNER_GENERATIONS_EXTERNAL_PROOF_REQUIRED",
        "named_ats_attribution": None,
        "source_authenticated": False,
        "public_delivery_allowed": False,
        "ranking_trading_alert_authority": False,
        "signal": None,
    }

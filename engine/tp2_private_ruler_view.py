"""TP-2 source-free PRIVATE observational view over TP-B research candidates.

This module does NOT connect to Massive, read or publish R2, change Data OS,
own a source clock or authenticate market data. It selects a bounded view of
the existing TP-B research artifacts for a future authorized private reader.
No EOD/weekly FINRA or Terminal production consumer is replaced here.

TP-B source and calibration schemas remain draft. Every output is a HOLD and
retains source-vintage, original availability and explicitly null live layers.
"""
from __future__ import annotations

import re
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

SCHEMA = "darkpool.tp2_private_offexchange_view/v0"
OBS_SCHEMA = "equity.tp_b.historical_ruler/v0"
CAL_SCHEMA = "equity.tp_b.history_calibration/v0"
_SOURCE = "SOURCE_OBSERVATIONS_UNVERIFIED_EXTERNALLY"
_LIMIT_NS = (1 << 63) - 1
_SHA = re.compile(r"^[0-9a-f]{64}$")
_SYMBOL = re.compile(r"^[A-Z][A-Z0-9.\-]{0,19}$")
_SESSION = re.compile(r"^\d{4}-\d{2}-\d{2}:RTH$")
_DECIMAL_TEXT = re.compile(r"^(?:0|[1-9]\d*)(?:\.\d+)?$")
_KINDS = ("SINGLE_PRINT", "SAME_LEVEL_CLUSTER", "DAILY_TOTAL")
_RANK_SOURCE_METRICS = {
    "SINGLE_PRINT": "largest_individual_print_usd",
    "SAME_LEVEL_CLUSTER": "largest_cluster_usd",
    "DAILY_TOTAL": "oe_source_notional_usd",
}
_SIGNED_DECIMAL_TEXT = re.compile(r"^-?(?:0|[1-9]\d*)(?:\.\d+)?$")
_BLOCKS = ("100000", "500000", "1000000")
_DAILY_STATES = frozenset({
    "OBSERVED_COVERAGE_ONLY", "NOT_FULL_RTH", "NO_OBSERVED_OBJECT",
    "INSUFFICIENT_COMPARABLE_HISTORY",
})
_MINUTE_STATES = frozenset({
    "OBSERVED_COVERAGE_ONLY", "NO_ROBUST_DISPERSION",
    "INSUFFICIENT_MINUTE_MATCHED_HISTORY",
    "TARGET_MINUTE_SOURCE_UNQUALIFIED",
})


class TP2PrivateViewRefusal(ValueError):
    """Research-input contradiction; never replace it with quiet/zero volume."""


def _clock(value, field):
    if type(value) is not int or not 0 < value <= _LIMIT_NS:
        raise TP2PrivateViewRefusal(f"{field}: invalid original nanoseconds")
    return value


def _hex(value, field):
    if type(value) is not str or _SHA.fullmatch(value) is None:
        raise TP2PrivateViewRefusal(f"{field}: original digest missing")
    return value


def _rth_open_ns(session):
    """Cross-check source session against 09:30 New York (DST aware).

    Not a holiday/early-close certificate; the source/calendar owner must
    still attest original market existence and correct session boundaries.
    """
    if type(session) is not str or _SESSION.fullmatch(session) is None:
        return None
    try:
        day = date.fromisoformat(session[:10])
    except ValueError:
        return None
    opening = datetime.combine(
        day, time(9, 30), tzinfo=ZoneInfo("America/New_York"))
    return int(opening.timestamp()) * 1_000_000_000


def _bounded_decimal(value, field, *, allow_zero=False):
    if (type(value) is not str or not 0 < len(value) <= 280
            or _DECIMAL_TEXT.fullmatch(value) is None):
        # A compact 1e+999999999 source token must never be expanded by a
        # later JSON/JS consumer or misread as a qualified measured amount.
        raise TP2PrivateViewRefusal(f"{field}: bounded original decimal missing")
    try:
        d = Decimal(value)
    except InvalidOperation as exc:
        raise TP2PrivateViewRefusal(f"{field}: invalid decimal") from exc
    if not d.is_finite() or d < 0 or (not allow_zero and d == 0):
        raise TP2PrivateViewRefusal(f"{field}: invalid nonnegative amount")
    return value


def _bounded_signed_decimal(value, field):
    """Accept signed, finite, fixed-point research z with finite text width."""
    if (type(value) is not str or not 0 < len(value) <= 1024
            or _SIGNED_DECIMAL_TEXT.fullmatch(value) is None):
        raise TP2PrivateViewRefusal(f"{field}: invalid signed minute statistic")
    try:
        d = Decimal(value)
    except InvalidOperation as exc:
        raise TP2PrivateViewRefusal(f"{field}: malformed minute statistic") from exc
    if not d.is_finite():
        raise TP2PrivateViewRefusal(f"{field}: nonfinite minute statistic")
    return d


def _identity(obj, *, schema, role):
    if not isinstance(obj, dict) or obj.get("schema") != schema:
        raise TP2PrivateViewRefusal(f"{role}: incompatible source schema")
    ticker, session = obj.get("ticker"), obj.get(
        "session" if role == "observation" else "target_session")
    if (not isinstance(ticker, str) or _SYMBOL.fullmatch(ticker) is None
            or not isinstance(session, str) or _SESSION.fullmatch(session) is None):
        raise TP2PrivateViewRefusal(f"{role}: invalid source identity")
    return ticker, session


def _tp1_private_provisional(*, minute, cutoff_ns, expected_ticker=None,
                             expected_session=None, expected_end_ns=None):
    """View the *existing TP1 verified body*, never redo its byte verification.

    The caller first uses TP1's canonical verify_private_minute_bytes. This
    independent consumer checks projection/clock/identity boundaries only; no
    TP1 signer, publisher, R2 client, source custody or auth plane is created.
    Crucially, source provisional TRF counts/notional cannot join TP-B's
    final-vintage or condition-qualified historical observations.
    """
    if (not isinstance(minute, dict)
            or minute.get("schema") != "equity.tick_plane.private_minute_artifact/v0"
            or minute.get("source_schema") != "equity.tick_plane.minute_observation/v0"
            or minute.get("distribution_class") !=
               "PRIVATE_SERVICE_HOLD_PENDING_LICENSE_AND_CONSUMER_REVIEW"
            or minute.get("source_authenticity") !=
               "EXTERNAL_INCUMBENT_PROOF_REQUIRED"
            or minute.get("live_capture_completeness") !=
               "UNVERIFIED_BY_PROJECTION"
            or minute.get("source_mode") !=
               "ACTUAL_AS_SEEN_ONLY_WHEN_OWNER_PROVES_RECEIPTS"
            or minute.get("correction_status") !=
               "STREAM_PROVISIONAL_UNRECONCILED"
            or minute.get("public_delivery_allowed") is not False
            or minute.get("rank_trade_alert_authority") is not False
            or minute.get("absorption_signal") is not None
            or minute.get("price_response_bps") is not None):
        raise TP2PrivateViewRefusal("TP1 source/authority not admitted as provisional")
    ticker, session = _identity(
        minute, schema="equity.tick_plane.private_minute_artifact/v0",
        role="observation")
    if (expected_ticker is not None and ticker != expected_ticker
            or expected_session is not None and session != expected_session):
        raise TP2PrivateViewRefusal("TP1 identity disagrees with TP-B observation")
    start = _clock(minute.get("start_ns"), "TP1.start_ns")
    end = _clock(minute.get("end_ns"), "TP1.end_ns")
    decision = _clock(minute.get("decision_ns"), "TP1.decision_ns")
    watermark = _clock(minute.get("source_watermark_available_ns"),
                       "TP1.watermark_available_ns")
    through = _clock(minute.get("source_complete_through_ns"),
                     "TP1.source_complete_through_ns")
    last_seen = _clock(minute.get("source_latest_print_available_ns"),
                       "TP1.source_latest_print_available_ns")
    open_ns = _rth_open_ns(session)
    if (open_ns is None or start < open_ns
            or start % 60_000_000_000
            or end-start != 60_000_000_000
            or end > open_ns+390*60_000_000_000
            or expected_end_ns is not None and end > expected_end_ns
            or through < end or watermark < through
            or last_seen < start or last_seen > decision
            or watermark > decision or end > decision):
        raise TP2PrivateViewRefusal("TP1 original minute clocks or RTH scope invalid")
    if decision > cutoff_ns:
        # Withhold every source-dependent field. The as-seen reader must not
        # surface even a digest or native original receipt in the past.
        return "TP1_MINUTE_NOT_YET_KNOWABLE", None
    for field in ("source_manifest_sha256", "source_observation_sha256",
                  "source_watermark_receipt_sha256"):
        _hex(minute.get(field), "TP1."+field)
    counts = minute.get("counts")
    if not isinstance(counts, dict):
        raise TP2PrivateViewRefusal("TP1 source counts missing")
    needed = (
        "n_sampled_prints", "n_lit", "n_trf", "n_unknown_venue",
        "n_lit_eligible_prints", "n_lit_classified_quote_le5s_prints",
        "n_lit_unclassified_prints",
    )
    if any(type(counts.get(k)) is not int or not 0 <= counts[k] <= 10_000
           for k in needed):
        raise TP2PrivateViewRefusal("TP1 source counts invalid")
    if (counts["n_sampled_prints"] < 1
            or counts["n_lit"]+counts["n_trf"]+counts["n_unknown_venue"]
               != counts["n_sampled_prints"]
            or counts["n_lit_eligible_prints"] > counts["n_lit"]
            or counts["n_lit_classified_quote_le5s_prints"]
               > counts["n_lit_eligible_prints"]):
        raise TP2PrivateViewRefusal("TP1 source counts contradictory")
    notional = minute.get("notional_usd")
    if not isinstance(notional, dict):
        raise TP2PrivateViewRefusal("TP1 source notional missing")
    def source_amount(key):
        raw = notional.get(key)
        if type(raw) is not str or len(raw) > 160:
            raise TP2PrivateViewRefusal("TP1 source exact amount malformed")
        try:
            value = Decimal(raw)
        except InvalidOperation as exc:
            raise TP2PrivateViewRefusal("TP1 source amount malformed") from exc
        if not value.is_finite() or value < 0:
            raise TP2PrivateViewRefusal("TP1 source amount invalid")
        fixed = format(value, "f") if -130 <= value.adjusted() <= 130 else None
        if fixed is None or len(fixed) > 280:
            raise TP2PrivateViewRefusal("TP1 source exact amount unbounded")
        return value, fixed
    total, _ = source_amount("gross_sampled_notional_usd")
    trf, trf_text = source_amount("trf_gross_notional_usd")
    if trf > total or (counts["n_trf"] == 0 and trf != 0):
        raise TP2PrivateViewRefusal("TP1 sampled TRF count/notional contradiction")
    return "PROVISIONAL_TP1_MINUTE_RESEARCH_HOLD", {
        "source": "TP1_VERIFIED_PRIVATE_BODY_REQUIRES_EXTERNAL_CUSTODY_PROOF",
        "ticker": ticker, "session": session,
        "minute_start_ns_decimal": str(start),
        "minute_end_ns_decimal": str(end),
        "minute_decision_ns_decimal": str(decision),
        "watermark_available_ns_decimal": str(watermark),
        "source_manifest_sha256": minute["source_manifest_sha256"],
        "source_observation_sha256": minute["source_observation_sha256"],
        "sampled_prints": counts["n_sampled_prints"],
        "sampled_lit_prints": counts["n_lit"],
        "sampled_trf_prints": counts["n_trf"],
        "lit_quote_located_le5s_prints": counts["n_lit_classified_quote_le5s_prints"],
        "provisional_trf_any_condition_notional_usd": trf_text,
        "trf_volume_eligibility_proven": False,
        "classification_accuracy_validated": False,
        "join_to_tpb_historical_ranks": False,
        "source_authenticity": "EXTERNAL_INCUMBENT_PROOF_REQUIRED",
    }


def _hold(*, state, observed_at_ns, observation=None, reason=None):
    """One truth-preserving response family, including absent/late source."""
    return {
        "schema": SCHEMA,
        "state": state,
        "reason": reason,
        "authority": "PRIVATE_RESEARCH_VIEW_HOLD_NOT_DELIVERY",
        "observation_asof_ns_decimal": (
            str(observation["asof_ns"]) if observation is not None else None),
        "view_asof_ns_decimal": str(observed_at_ns),
        "ticker": observation["ticker"] if observation is not None else None,
        "session": observation["session"] if observation is not None else None,
        "source_generation_sha256": (
            observation["source_generation_sha256"] if observation is not None else None),
        "source_snapshot_sha256": (
            observation["snapshot_sha256"] if observation is not None else None),
        "source_manifest_sha256": (
            observation["source_manifest_sha256"] if observation is not None else None),
        "observed_source": None,
        "historical_ruler": None,
        # TP1's *separate* provisional minute is never merged with TP-B
        # final-vintage ranks or condition-qualified TRF notional.
        "tp1_minute_state": "TP1_MINUTE_NOT_SUPPLIED",
        "tp1_provisional_minute": None,
        "intraday_minute_baseline": None,
        # Deliberately no reconstructed per-print tape or price shelves in
        # TP-B's aggregate output. The original owner must supply those.
        "live_block_tape": None,
        "repeat_print_price_shelves": None,
        "live_signed_offexchange_flow": None,
        "nbbo_classification_coverage": None,
        # ATS firm attribution is delayed FINRA, NOT the live TRF pipe.
        "named_ats_attribution": None,
        "finra_ats_delayed_context": None,
        "eod_weekly_context": "UNCHANGED_SEPARATE_EXISTING_CONSUMER",
        "source_authenticated": False,
        "market_capture_completeness_proven": False,
        "public_delivery_allowed": False,
        "ranking_trading_alert_authority": False,
        "signal": None,
    }


def build_private_tp2_view(*, observation, calibration=None, view_asof_ns,
                           tp1_private_minute=None):
    """Create a private candidate; no source or authority promotion.

    `observation` must be a TP-B source-free result from the incumbent
    historical ruler. `calibration` is a separately time-qualified TP-B
    history candidate. A matching hash proves only internal lineage between
    supplied dicts, not cryptographic custody of original vendor bytes.
    """
    now = _clock(view_asof_ns, "view_asof_ns")

    def finish(result):
        if tp1_private_minute is None:
            return result
        # Only the incumbent TP1 verifier decodes the original private
        # artifact; the caller passes its already-verified body. We neither
        # read raw bytes nor assert a new source-custody/authenticity receipt.
        tp1_state, tp1_candidate = _tp1_private_provisional(
            minute=tp1_private_minute, cutoff_ns=now,
            expected_ticker=observation.get("ticker")
                            if isinstance(observation, dict) else None,
            expected_session=observation.get("session")
                            if isinstance(observation, dict) else None,
            expected_end_ns=observation.get("end_ns")
                            if isinstance(observation, dict) else None)
        result["tp1_minute_state"] = tp1_state
        result["tp1_provisional_minute"] = tp1_candidate
        return result

    if observation is None:
        if calibration is not None:
            raise TP2PrivateViewRefusal("calibration without an original source")
        return finish(_hold(state="NO_TPB_OBSERVATION_SOURCE", observed_at_ns=now))
    ticker, session = _identity(
        observation, schema=OBS_SCHEMA, role="observation")
    if (observation.get("authority") != "RESEARCH_MEASUREMENT_ONLY"
            or observation.get("source_scope") != "RTH"
            or observation.get("source_receipts_authenticated") is not False
            or observation.get("market_capture_completeness_proven") is not False
            or observation.get("public_delivery_allowed") is not False
            or observation.get("ranking_trading_alert_authority") is not False
            or observation.get("signal") is not None
            or observation.get("actor_identity") is not None):
        raise TP2PrivateViewRefusal("observation: unauthorized source promotion")
    _hex(observation.get("snapshot_sha256"), "source snapshot")
    _hex(observation.get("source_manifest_sha256"), "source manifest")
    _hex(observation.get("source_generation_sha256"), "source generation")
    start = _clock(observation.get("start_ns"), "source.start_ns")
    if start != _rth_open_ns(session):
        raise TP2PrivateViewRefusal("source: RTH session/clock mismatch")
    end = _clock(observation.get("end_ns"), "source.end_ns")
    asof = _clock(observation.get("asof_ns"), "source.asof_ns")
    if end <= start or end-start > 390*60_000_000_000 or asof < start:
        raise TP2PrivateViewRefusal("source: impossible RTH window")
    if asof > now:
        # The caller may hold a future source record in memory, but none of
        # its fields (including source generation/hash and receipt time)
        # existed at this requested decision cutoff. Do not leak them into
        # an as-seen projection, even on a private research interface.
        return finish(_hold(state="SOURCE_NOT_YET_KNOWABLE", observed_at_ns=now))
    state = observation.get("state")
    if state != _SOURCE:
        if state not in ("NO_SAMPLED_PRINTS",
                         "NO_QUALIFIED_OFF_EXCHANGE_OBSERVED"):
            raise TP2PrivateViewRefusal("observation: unknown missingness state")
        return finish(_hold(state="NO_QUALIFIED_TRF_OBSERVATIONS",
                            observed_at_ns=now, observation=observation,
                            reason=state))
    n = observation.get("n_trf_observed")
    if type(n) is not int or not 0 < n <= 20_000:
        raise TP2PrivateViewRefusal("observation: no qualified TRF cohort")
    for field in ("oe_source_shares", "oe_source_notional_usd",
                  "largest_individual_print_usd"):
        _bounded_decimal(observation.get(field), field)
    largest_cluster = observation.get("largest_cluster_usd")
    if largest_cluster is not None:
        _bounded_decimal(largest_cluster, "largest_cluster_usd")
    total_usd = Decimal(observation["oe_source_notional_usd"])
    if (Decimal(observation["largest_individual_print_usd"]) > total_usd
            or (largest_cluster is not None
                and Decimal(largest_cluster) > total_usd)):
        raise TP2PrivateViewRefusal("observation: source total smaller than print/cluster")
    tiers = observation.get("absolute_block_tier_counts")
    if not isinstance(tiers, dict) or set(tiers) != set(_BLOCKS):
        raise TP2PrivateViewRefusal("observation: invalid block-tier source")
    if any(type(v) is not int or not 0 <= v <= n for v in tiers.values()):
        raise TP2PrivateViewRefusal("observation: impossible block-tier counts")
    output = _hold(state="HISTORICAL_CALIBRATION_PENDING",
                   observed_at_ns=now, observation=observation)
    output["observed_source"] = {
        "state": "BOUNDED_SOURCE_OBSERVATION_NOT_AUTHENTICATED",
        "n_trf_observed": n,
        "n_unknown_volume_policy": observation.get("n_unknown_volume_policy"),
        "largest_individual_print_usd": observation["largest_individual_print_usd"],
        "largest_same_level_cluster_usd": largest_cluster,
        "measured_rth_trf_notional_usd": observation["oe_source_notional_usd"],
        "measured_rth_trf_shares": observation["oe_source_shares"],
        "block_tier_counts": {k: tiers[k] for k in _BLOCKS},
        "full_rth_covered_claim_unverified": observation.get("full_rth_covered") is True,
        "cluster_clock": observation.get("cluster_clock"),
    }
    if calibration is None:
        return finish(output)
    cticker, csession = _identity(
        calibration, schema=CAL_SCHEMA, role="calibration")
    if cticker != ticker or csession != session:
        raise TP2PrivateViewRefusal("calibration: mismatched symbol/session")
    if (calibration.get("authority") != "HISTORICAL_RESEARCH_CALIBRATION_ONLY"
            or calibration.get("source_authenticated") is not False
            or calibration.get("public_delivery_allowed") is not False
            or calibration.get("ranking_trading_alert_authority") is not False
            or calibration.get("signal") is not None
            or calibration.get("named_ats_attribution") is not None):
        raise TP2PrivateViewRefusal("calibration: unauthorized data promotion")
    if (calibration.get("basis_id") != observation.get("split_basis_id")
            or calibration.get("basis_vintage_sha256") != observation.get("split_basis_vintage_sha256")
            or calibration.get("split_segment") != observation.get("split_segment")):
        raise TP2PrivateViewRefusal("calibration: incompatible source split basis")
    if calibration.get("target_snapshot_sha256") != observation["snapshot_sha256"]:
        # Revised source generation makes previously calculated ranks stale.
        output["state"] = "CALIBRATION_STALE_SOURCE_GENERATION"
        output["historical_ruler"] = None
        output["intraday_minute_baseline"] = None
        return finish(output)
    evaluation = _clock(calibration.get("evaluation_ns"), "calibration.evaluation_ns")
    if evaluation < asof:
        raise TP2PrivateViewRefusal("calibration: evaluated before source existed")
    if evaluation > now:
        output["state"] = "CALIBRATION_NOT_YET_KNOWABLE"
        return finish(output)
    ranks = calibration.get("daily_object_ranks")
    if not isinstance(ranks, dict) or set(ranks) != set(_KINDS):
        raise TP2PrivateViewRefusal("calibration: incomplete separate object kinds")
    named = {}
    for kind in _KINDS:
        entry = ranks[kind]
        if not isinstance(entry, dict) or entry.get("state") not in _DAILY_STATES:
            raise TP2PrivateViewRefusal("calibration: invalid daily rank state")
        if entry.get("source_metric") != _RANK_SOURCE_METRICS[kind]:
            raise TP2PrivateViewRefusal("calibration: daily rank source metric mismatch")
        status = entry["state"]
        rank = entry.get("rank_desc")
        n_prior = entry.get("n_prior")
        if type(n_prior) is not int or not 0 <= n_prior <= 1500:
            raise TP2PrivateViewRefusal("calibration: invalid rank evidence N")
        if status == "OBSERVED_COVERAGE_ONLY":
            if type(rank) is not int or not 1 <= rank <= n_prior+1:
                raise TP2PrivateViewRefusal("calibration: invalid rank")
        elif rank is not None:
            raise TP2PrivateViewRefusal("calibration: rank without source evidence")
        named[kind] = {
            "state": status,
            "rank_desc_in_observed_sample": rank,
            "n_prior_comparable": entry.get("n_prior"),
            "source_metric": entry.get("source_metric"),
        }
    if observation.get("full_rth_covered") is not True and any(
        x["state"] == "OBSERVED_COVERAGE_ONLY" for x in named.values()
    ):
        raise TP2PrivateViewRefusal("calibration: full-session rank on partial day")
    minute = calibration.get("minute_conditioned_baseline")
    if (not isinstance(minute, dict)
            or minute.get("state") not in _MINUTE_STATES
            or minute.get("conditioning") != "EXACT_MINUTE_INDEX_RTH_CUMULATIVE_ONLY"
            or type(minute.get("minute_index")) is not int
            or not 0 <= minute["minute_index"] < (end-start)//60_000_000_000
            or type(minute.get("n_prior")) is not int
            or not 0 <= minute["n_prior"] <= 1500):
        raise TP2PrivateViewRefusal("calibration: invalid minute-matched baseline")
    share = minute.get("share")
    if share is not None and Decimal(_bounded_decimal(
            share, "calibration.minute.share", allow_zero=True)) > 1:
        raise TP2PrivateViewRefusal("calibration: invalid minute share")
    # The historical candidate is not a substitute for this snapshot's
    # observed cumulative participation. Its source minute, original receipt
    # and qualification status must agree with what this source generation
    # actually supplied. A matching caller-provided snapshot digest alone
    # cannot guarantee internal coherence of mutable Python dictionaries.
    points = observation.get("minute_points_private_only")
    if not isinstance(points, list) or len(points) > 390:
        raise TP2PrivateViewRefusal("calibration: source minute missing/invalid")
    current = [point for point in points if isinstance(point, dict)
               and point.get("minute_index") == minute["minute_index"]]
    if len(current) > 1:
        raise TP2PrivateViewRefusal("calibration: duplicate source minute")
    source_minute = current[0] if current else None
    source_share = source_minute.get("share") if source_minute else None
    if source_share != share:
        raise TP2PrivateViewRefusal("calibration: source minute share disagrees")
    qualified = False
    if source_minute is not None:
        available = source_minute.get("source_available_ns")
        if (type(available) is not int or available < 1
                or available > asof or available > now):
            raise TP2PrivateViewRefusal("calibration: source minute received after cutoff")
        if type(source_minute.get("qualified_prefix")) is not bool:
            raise TP2PrivateViewRefusal("calibration: source minute qualification invalid")
        qualified = source_minute["qualified_prefix"] and source_share is not None
    if minute["state"] == "TARGET_MINUTE_SOURCE_UNQUALIFIED":
        if qualified:
            raise TP2PrivateViewRefusal("calibration: qualified source minute falsely missing")
    elif not qualified:
        raise TP2PrivateViewRefusal("calibration: source minute not qualified")
    # Typed nulls and bounded fractions are part of the upstream estimator's
    # contract. A malformed 120% percentile, negative MAD, or made-up z on
    # thin/missing history must not be forwarded as a research measurement.
    values = {}
    for field in ("median", "mad", "midrank_percentile"):
        raw = minute.get(field)
        values[field] = (
            Decimal(_bounded_decimal(raw, "calibration.minute."+field,
                                     allow_zero=True))
            if raw is not None else None
        )
        if values[field] is not None and values[field] > 1:
            raise TP2PrivateViewRefusal("calibration: minute fraction out of range")
    z_raw = minute.get("robust_z")
    z = (_bounded_signed_decimal(z_raw, "calibration.minute.robust_z")
         if z_raw is not None else None)
    mstate = minute["state"]
    if mstate in ("OBSERVED_COVERAGE_ONLY", "NO_ROBUST_DISPERSION"):
        if (minute["n_prior"] < 2
                or any(values[k] is None for k in values)):
            raise TP2PrivateViewRefusal("calibration: minute distribution incomplete")
        if mstate == "NO_ROBUST_DISPERSION":
            if values["mad"] != 0 or z is not None:
                raise TP2PrivateViewRefusal("calibration: minute dispersion inconsistent")
        elif values["mad"] <= 0 or z is None:
            raise TP2PrivateViewRefusal("calibration: minute robust z incomplete")
    elif any(v is not None for v in values.values()) or z is not None:
        raise TP2PrivateViewRefusal("calibration: minute statistics without history")
    output["state"] = "PRIVATE_TPB_RESEARCH_CONTEXT_ONLY"
    output["historical_ruler"] = named
    output["intraday_minute_baseline"] = {
        "state": minute["state"],
        "conditioning": minute["conditioning"],
        "minute_index": minute["minute_index"],
        "n_prior": minute.get("n_prior"),
        "cumulative_offexchange_share": minute.get("share"),
        "median": minute.get("median"),
        "mad": minute.get("mad"),
        "robust_z": minute.get("robust_z"),
        "midrank_percentile": minute.get("midrank_percentile"),
        "history_coverage_start": minute.get("coverage_start"),
    }
    return finish(output)

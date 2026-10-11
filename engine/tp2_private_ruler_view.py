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
from decimal import Decimal, InvalidOperation

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


def _identity(obj, *, schema, role):
    if not isinstance(obj, dict) or obj.get("schema") != schema:
        raise TP2PrivateViewRefusal(f"{role}: incompatible source schema")
    ticker, session = obj.get("ticker"), obj.get(
        "session" if role == "observation" else "target_session")
    if (not isinstance(ticker, str) or _SYMBOL.fullmatch(ticker) is None
            or not isinstance(session, str) or _SESSION.fullmatch(session) is None):
        raise TP2PrivateViewRefusal(f"{role}: invalid source identity")
    return ticker, session


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


def build_private_tp2_view(*, observation, calibration=None, view_asof_ns):
    """Create a private candidate; no source or authority promotion.

    `observation` must be a TP-B source-free result from the incumbent
    historical ruler. `calibration` is a separately time-qualified TP-B
    history candidate. A matching hash proves only internal lineage between
    supplied dicts, not cryptographic custody of original vendor bytes.
    """
    now = _clock(view_asof_ns, "view_asof_ns")
    if observation is None:
        if calibration is not None:
            raise TP2PrivateViewRefusal("calibration without an original source")
        return _hold(state="NO_TPB_OBSERVATION_SOURCE", observed_at_ns=now)
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
    end = _clock(observation.get("end_ns"), "source.end_ns")
    asof = _clock(observation.get("asof_ns"), "source.asof_ns")
    if end <= start or end-start > 390*60_000_000_000 or asof < start:
        raise TP2PrivateViewRefusal("source: impossible RTH window")
    if asof > now:
        return _hold(state="SOURCE_NOT_YET_KNOWABLE", observed_at_ns=now,
                     observation=observation)
    state = observation.get("state")
    if state != _SOURCE:
        if state not in ("NO_SAMPLED_PRINTS",
                         "NO_QUALIFIED_OFF_EXCHANGE_OBSERVED"):
            raise TP2PrivateViewRefusal("observation: unknown missingness state")
        return _hold(state="NO_QUALIFIED_TRF_OBSERVATIONS",
                     observed_at_ns=now, observation=observation,
                     reason=state)
    n = observation.get("n_trf_observed")
    if type(n) is not int or not 0 < n <= 20_000:
        raise TP2PrivateViewRefusal("observation: no qualified TRF cohort")
    for field in ("oe_source_shares", "oe_source_notional_usd",
                  "largest_individual_print_usd"):
        _bounded_decimal(observation.get(field), field)
    largest_cluster = observation.get("largest_cluster_usd")
    if largest_cluster is not None:
        _bounded_decimal(largest_cluster, "largest_cluster_usd")
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
        return output
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
        return output
    evaluation = _clock(calibration.get("evaluation_ns"), "calibration.evaluation_ns")
    if evaluation < asof:
        raise TP2PrivateViewRefusal("calibration: evaluated before source existed")
    if evaluation > now:
        output["state"] = "CALIBRATION_NOT_YET_KNOWABLE"
        return output
    ranks = calibration.get("daily_object_ranks")
    if not isinstance(ranks, dict) or set(ranks) != set(_KINDS):
        raise TP2PrivateViewRefusal("calibration: incomplete separate object kinds")
    named = {}
    for kind in _KINDS:
        entry = ranks[kind]
        if not isinstance(entry, dict) or entry.get("state") not in _DAILY_STATES:
            raise TP2PrivateViewRefusal("calibration: invalid daily rank state")
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
    return output

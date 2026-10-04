"""China Intelligence transmission bus — hub-display surfaces; digest summary travels to Mastermind.

LEAF · CONTEXT-ONLY · NEVER A SCORE/SIZE. The China sibling of the macro master_brain brief:
it fans the FIVE China intelligence surfaces — News, Central-Bank/Policy, Alternative Data,
Divergence Radar, and the central-intelligence Analysis — into ONE schema-versioned,
machine-readable rollup (`china_intel.briefing.v6`) for hub display. The blocks assembled here
are hub-display surfaces only; they reach the China Mastermind only via the digest summary
line (see `_digest_text`). It DECOUPLES by reading each surface's already-emitted JSON off disk
(build-order is the only dependency); every reader degrades to None and NOTHING here raises
into a build.

v2 carries the upgrade: importance-ranked + ticker-flagged news, conviction-scored cross-
surface reads, flagged tickers, "what changed", staleness per surface, and a synthesis-led
digest. Additive over v1 (legacy keys preserved). See research/CHINA_INTEL_POWERHOUSE.md §5.

v4 (additive over v3): policy_phrase block (communique_diff APPEARED/DROPPED/LEAD_SHIFT
events from site/communique_diff/latest.json) + narrative_divergence block (GDELT onshore/
offshore tone divergence z-score from data/missing_tape/tone_divergence.parquet). Both blocks
degrade cleanly to None when their artifacts are absent. Schema bumped to v4.

v5 (additive over v4): special_situations block reading site/chinaspecialdata/special.json
(unlock overhang, inquiry letters, preannouncements, buybacks, pledge stress, ST watch,
block-trade anomalies). Degrades cleanly when artifact absent. Schema bumped to v5.

v6 (additive over v5): command block reading site/china_intel/command.json (W4 command
apparatus — per-ticker fusion, edge-remaining ranking, discovery lanes). Compact top-10
rows + counts + asof. Degrades cleanly when artifact absent. Schema bumped to v6. CIE-07
adds an additive visit_discovery block under the same backward-compatible v6 schema: it
reads the existing P1 visit owner locally, never changes command/rank authority, and keeps
insufficient coverage / source degradation / visitor identity explicit.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from lib import config
from engine.narrative_crossmarket import context_for_briefing

log = logging.getLogger(__name__)

SCHEMA = "china_intel.briefing.v6"
MAX_STALE_OK = 35

DISCLAIMER = (
    "Context only — not a signal, score or trade. A fan-in of five display/context-only China "
    "intelligence surfaces (news, central-bank & policy, alternative data, divergence radar, "
    "central analysis), bundled for the China Mastermind to read as background. Nothing here "
    "is an input to any score, signal, regime or allocation."
)
DISCLAIMER_ZH = (
    "仅作背景，非信号、评分或交易。这是五个仅供展示／背景的中国情报面板（新闻、央行与政策、"
    "另类数据、背离雷达、中央分析）的汇总，供中国 Mastermind 作为背景读取。其中没有任何内容"
    "会进入任何评分、信号、区制或配置。"
)


def _site_dir() -> Path:
    sd = Path(config.load()["storage"]["site_dir"])
    return sd if sd.is_absolute() else (config.ROOT / sd)


def _read_json(rel: str) -> dict | list | None:
    try:
        p = Path(rel)
        if not p.is_absolute():
            p = _site_dir() / rel
        if not p.exists():
            alt = config.ROOT / rel
            if alt.exists():
                p = alt
            else:
                return None
        return json.loads(p.read_text())
    except Exception as e:  # noqa: BLE001
        log.debug("china_intel_bus: read %s failed (%s)", rel, e)
        return None


# --------------------------------------------------------------------------- #
# cycle-context chip helper (W5)
# --------------------------------------------------------------------------- #
_REGIME_HISTORY_CACHE: dict = {}  # {path_str: DataFrame}


def _regime_chip_for_date(date_str: str) -> dict | None:
    """Look up quad/liquidity/cycle for a given date in regime_history.parquet.

    Returns {quad, quad_name, liquidity, cycle} if found, else None.
    Degrades cleanly: missing parquet or date not in index → None, no exception.
    Neutral/descriptive context only — no directional language.
    """
    try:
        import pandas as pd
        p = config.ROOT / "data" / "china_regime" / "regime_history.parquet"
        pstr = str(p)
        if pstr not in _REGIME_HISTORY_CACHE:
            if not p.exists():
                return None
            _df = pd.read_parquet(p, columns=["quad", "quad_name", "liquidity", "cycle"])
            _df.index = pd.to_datetime(_df.index)
            _REGIME_HISTORY_CACHE[pstr] = _df.sort_index()
        df = _REGIME_HISTORY_CACHE[pstr]
        if df is None or df.empty:
            return None
        # Backward as-of join: latest regime row AT/BEFORE the event date.
        # Exact-match would drop weekend-dated announcements and future-dated
        # unlocks (regime_history is trading-days-only, ends today). PIT-honest:
        # never reads a regime row later than the event date.
        ts = pd.Timestamp(str(date_str)[:10])
        pos = df.index.get_indexer([ts], method="ffill")[0]
        if pos < 0:
            return None  # event predates regime history
        row = df.iloc[pos]
        quad = str(row["quad"])
        quad_name = str(row["quad_name"])
        liquidity = str(row["liquidity"])
        cycle = str(row["cycle"])
        # Skip NaN / "nan" rows
        if any(v in ("nan", "", "None", "none") for v in (quad, quad_name)):
            return None
        return {"quad": quad, "quad_name": quad_name, "liquidity": liquidity, "cycle": cycle}
    except Exception as e:  # noqa: BLE001
        log.debug("china_intel_bus: regime chip lookup failed (%s)", e)
        return None


# --------------------------------------------------------------------------- #
# per-surface compact readers — enriched (v2)
# --------------------------------------------------------------------------- #
def _news_block() -> dict | None:
    """Media-sentiment + importance-ranked, ticker-flagged headlines + basket tags."""
    sent = _read_json("chinanews/sentiment.json")
    feed = _read_json("chinanews/feed.json")
    if not sent and not feed:
        return None
    out: dict = {}
    if isinstance(sent, dict):
        out["sentiment_z"] = sent.get("z")
        out["band"] = sent.get("band")
        out["band_label_en"] = sent.get("label_en")     # fixes the hub zh leak
        out["band_label_zh"] = sent.get("label_zh")
        out["n_events_7d"] = sent.get("n_events_7d")
    if isinstance(feed, dict):
        tl = feed.get("theme_label") or {}
        out["top_themes"] = [{"key": k, "en": (tl.get(k) or [k, k])[0], "zh": (tl.get(k) or [k, k])[1]}
                             for k in (feed.get("top_themes") or [])]
        bb = feed.get("by_basket") or {}
        out["by_basket"] = bb
        bl = feed.get("basket_label") or {}
        out["flagged_baskets"] = [
            {"id": bid, "hits": int(n), "name_en": (bl.get(bid) or [bid, bid])[0],
             "name_zh": (bl.get(bid) or [bid, bid])[1]}
            for bid, n in sorted(bb.items(), key=lambda kv: -kv[1])[:6]]
        out["top_headlines"] = [
            {"title": it.get("title"), "theme_en": it.get("theme_en"), "theme_zh": it.get("theme_zh"),
             "tier": it.get("tier"), "baskets": it.get("baskets") or [], "tickers": it.get("tickers") or [],
             "importance_en": it.get("importance_en"), "importance_zh": it.get("importance_zh"),
             "surprise": it.get("surprise"), "scheduled_ref": it.get("scheduled_ref"), "url": it.get("url")}
            for it in (feed.get("items") or [])[:8]]
        out["scheduled_ahead"] = feed.get("scheduled_ahead") or []
        out["asof"] = feed.get("asof")
    return out or None


def _policy_block() -> dict | None:
    pol = _read_json("data/china_policy/latest.json")
    if not isinstance(pol, dict):
        return None
    block = {
        "pboc_stance": pol.get("stance"),
        "stance_label_en": pol.get("stance_en"), "stance_label_zh": pol.get("stance_zh"),
        "lpr_1y": pol.get("lpr_1y"), "lpr_5y": pol.get("lpr_5y"),
        "rrr": pol.get("rrr"), "fr007": pol.get("fr007"),
        "fx_reserves": pol.get("fx_reserves"), "usd_cny": pol.get("usd_cny"),
        "last_moves": pol.get("last_moves") or [], "predictions": pol.get("predictions") or [],
        "asof": pol.get("asof"), "stale": pol.get("stale"),
    }
    # priced-for-easing reconciliation
    last_moves = pol.get("last_moves") or []
    has_cuts = any(("cut" in str(m).lower()) or ("降" in str(m)) for m in last_moves)
    if pol.get("stance") == "neutral" and has_cuts:
        block["impulse"] = {
            "label_en": "Easing in progress — stance not yet flipped",
            "label_zh": "宽松进行中——立场尚未转向",
            "note_en": "Cumulative RRR/LPR cuts read as easing momentum; the corridor classifier "
                       "stays neutral until a second leg clears its threshold (leading vs coincident).",
            "note_zh": "累计降准/降息体现宽松动能；在第二条腿越过阈值前，走廊分类仍为中性（领先 vs 同步）。",
        }
    return block


def _altdata_block() -> dict | None:
    """Rich convergence rows (name + conviction + reasons), not bare codes. Legacy arrays kept."""
    ad = _read_json("chinaaltdata/mastermind.json")
    if not isinstance(ad, dict):
        return None
    acc = ad.get("convergence_top") or []
    dist = ad.get("convergence_bottom") or []
    # tolerate both rich-dict (v2) and bare-string (v1) shapes
    def codes(rows):
        return [r.get("ticker") if isinstance(r, dict) else r for r in rows]
    crowded = [r for r in acc + dist if isinstance(r, dict) and r.get("flags")]
    return {
        "n_triple": ad.get("n_triple"), "n_universe": ad.get("n_universe"),
        "accumulate": [r for r in acc if isinstance(r, dict)],
        "distribute": [r for r in dist if isinstance(r, dict)],
        "crowded": crowded,
        "convergence_top": codes(acc), "convergence_bottom": codes(dist),   # legacy
        "crowding_flags": ad.get("crowding_flags") or [],
        "asof": ad.get("asof"),
    }


def _radar_block() -> dict | None:
    rad = _read_json("chinaradar/radar.json")
    if not isinstance(rad, dict):
        return None
    ledger = _read_json("chinaradar/ledger.json") or {}
    n_res = ledger.get("n_resolved", 0) if isinstance(ledger, dict) else 0
    grade = "unproven" if (n_res or 0) < 3 else (
        "reliable" if (ledger.get("hit_rate") or 0) >= 0.55 else "weak")
    return {
        "divergences": rad.get("divergences") or [],
        "n_active": rad.get("n_active"),
        "ledger": {"hit_rate": ledger.get("hit_rate"), "n_resolved": int(n_res or 0),
                   "n_total": ledger.get("n_total"), "grade": grade},
        "asof": rad.get("asof"),
    }


def _regime_block() -> dict | None:
    """RORO / risk-appetite overlay from china_regime/latest.json (the conditions consolidation)."""
    c = _read_json("data/china_regime/latest.json")
    if not isinstance(c, dict):
        return None
    fe = c.get("fear_euphoria") or {}
    cond = c.get("conditions") or {}
    roro = fe.get("roro")
    if roro is None:
        roro = (cond.get("roro") or {}).get("roro")
    if roro is None and not fe:
        return None
    rt = 1 if (isinstance(roro, (int, float)) and roro > 0.15) else (-1 if (isinstance(roro, (int, float)) and roro < -0.15) else 0)
    return {"roro": roro, "roro_state": fe.get("roro_state") or (cond.get("roro") or {}).get("roro_state"),
            "fe_score": fe.get("fe_score"), "band_en": fe.get("band"), "band_zh": fe.get("band_zh"),
            "risk_tilt": rt}


def _discovery_block() -> dict | None:
    """Off-desk leading accumulation (china_discovery, in-process). Bounded, context-only."""
    try:
        from engine import china_discovery
        d = china_discovery.build()
        if not isinstance(d, dict):
            return None
        cands = d.get("candidates") or []
        return {"n": d.get("n"), "n_off_desk": d.get("n_off_desk"),
                "sources": d.get("sources"), "top": cands[:12]}
    except Exception as e:  # noqa: BLE001
        log.debug("china_intel_bus: discovery block failed (%s)", e)
        return None



# --------------------------------------------------------------------------- #
# CIE-07: coverage-adjusted institutional-visit metadata discovery
# --------------------------------------------------------------------------- #

_VISIT_DISCOVERY_SCHEMA = "china_visits.discovery_metadata.v1"
_VISIT_DISCOVERY_RECENT_DAYS = 30
_VISIT_DISCOVERY_BASELINE_DAYS = 90
_VISIT_DISCOVERY_STALE_AFTER_DAYS = 4  # mirrors ChinaVisitsAdapter / Hub reader
_VISIT_UNKNOWN_CLASSES = frozenset({"", "not_yet_available", "unresolved", "none", "nan", "<na>"})


def _visit_day(value) -> date | None:
    """Parse an owner clock to a calendar day without inventing precision."""
    try:
        text = str(value or "").strip()
    except Exception:  # noqa: BLE001
        return None
    if not text or text.lower() in {"none", "nan", "nat", "<na>"}:
        return None
    try:
        return date.fromisoformat(text[:10])
    except (TypeError, ValueError):
        return None


def _visit_text(value) -> str:
    try:
        if value is None:
            return ""
        text = str(value).strip()
        return "" if text.lower() in {"none", "nan", "nat", "<na>"} else text
    except Exception:  # noqa: BLE001
        return ""


def _visit_frame_records(frame) -> list[dict] | None:
    """Bounded adapter for tests/lists and the owner DataFrames; None means unreadable."""
    if frame is None:
        return None
    if isinstance(frame, list):
        return [dict(r) for r in frame if isinstance(r, dict)]
    try:
        return [dict(r) for r in frame.to_dict(orient="records")]
    except Exception:  # noqa: BLE001
        return None


def _visit_discovery_snapshot(
    visits: list[dict],
    *,
    health: dict,
    coverage_start: str | None,
    open_scoped_codes: set[str],
    has_unscoped_open: bool,
    kind_labeler,
    recent_days: int = _VISIT_DISCOVERY_RECENT_DAYS,
    baseline_days: int = _VISIT_DISCOVERY_BASELINE_DAYS,
    reference_day: date | None = None,
    stale_after_days: int = _VISIT_DISCOVERY_STALE_AFTER_DAYS,
) -> dict:
    """Descriptive visit-frequency state from the existing P1 tape.

    It never claims a visit is bullish/bearish, never identifies an actor from
    metadata, and never treats unobserved history as quiet.  The default 30d
    recent / preceding 90d baseline is descriptive bookkeeping only; predictive
    interpretation remains gated by CIE-03/CIE-18.
    """
    recent_days = max(int(recent_days), 1)
    baseline_days = max(int(baseline_days), 1)
    health = health if isinstance(health, dict) else {}
    owner_health_status = _visit_text(health.get("status")) or "no_coverage"
    coverage_day = _visit_day(coverage_start)
    last_success_day = _visit_day(health.get("last_success_utc"))
    last_attempt_day = _visit_day(health.get("last_attempt_utc"))
    # Keep the pure helper deterministic when called directly: production's
    # owner reader passes the real current date explicitly below.
    reference_day = reference_day or last_attempt_day or last_success_day or coverage_day or date.today()
    source_status = owner_health_status
    if (
        owner_health_status == "ok"
        and last_success_day is not None
        and (reference_day - last_success_day).days > max(int(stale_after_days), 0)
    ):
        source_status = "stale"

    # Defensive natural-key dedup. The owner already enforces keep-FIRST on
    # announcement_id; this prevents a malformed fixture/consumer from turning
    # one filing into apparent recurrence.
    deduped: list[dict] = []
    seen_ids: set[str] = set()
    for row in visits or []:
        aid = _visit_text(row.get("announcement_id"))
        if aid:
            if aid in seen_ids:
                continue
            seen_ids.add(aid)
        deduped.append(row)

    source_event_days = [
        d for d in (_visit_day(r.get("source_published_at")) for r in deduped)
        if d is not None
    ]
    system_observed_days = [
        d for d in (_visit_day(r.get("system_recorded_at")) for r in deduped)
        if d is not None
    ]
    if last_success_day is not None and owner_health_status == "ok":
        observation_end = last_success_day
    elif last_attempt_day is not None:
        # A degraded/failed attempt is the honest present-tense reference clock.
        # It grants no negative authority, but prevents a quiet event tape from
        # moving the 30d window backward to the date of its last positive filing.
        observation_end = last_attempt_day
    elif system_observed_days:
        observation_end = max(system_observed_days)
    elif source_event_days:
        # Legacy positive evidence with no system clock: source date is a last
        # resort for display-window anchoring only, never first-seen authority.
        observation_end = max(source_event_days)
    else:
        observation_end = last_success_day or coverage_day

    authority = {
        "is_context_only": True,
        "may_rank": False,
        "may_trade": False,
        "may_feed_prophet": False,
        "may_infer_visitor_identity": False,
        "may_claim_predictive_edge": False,
    }
    base = {
        "schema": _VISIT_DISCOVERY_SCHEMA,
        "is_context_only": True,
        "authority": authority,
        "source_status": source_status,
        "owner_health_status": owner_health_status,
        "stale_after_days": max(int(stale_after_days), 0),
        "coverage_start": coverage_day.isoformat() if coverage_day else None,
        "observation_end": observation_end.isoformat() if observation_end else None,
        "asof": observation_end.isoformat() if observation_end else None,
        "recent_window_days": recent_days,
        "baseline_window_days": baseline_days,
        "scientific_state": "descriptive_only_not_alpha_evidence",
        "actor_recurrence_state": "not_evaluated_without_body_stage_receipt",
        "candidate_accounting": health.get("candidate_accounting"),
        "global_negative_authority": (
            source_status == "ok"
            and coverage_day is not None
            and last_success_day is not None
            and not has_unscoped_open
        ),
        "global_negative_authority_blocker": (
            "unscoped_coverage_exception" if has_unscoped_open
            else "source_stale" if source_status == "stale"
            else "source_health_not_ok" if source_status != "ok"
            else "coverage_start_unavailable" if coverage_day is None
            else "last_success_clock_unavailable" if last_success_day is None
            else None
        ),
        "n_rows_observed": len(deduped),
        "n_recent_companies": 0,
        "n_first_observed_recent": 0,
        "n_measured_baselines": 0,
        "n_company_exceptions": len(open_scoped_codes),
        "examples": [],
        "examples_order": "company_key_lexicographic_not_ranked",
        "examples_truncated": False,
    }
    if observation_end is None:
        return base

    recent_start = observation_end - timedelta(days=recent_days - 1)
    baseline_end = recent_start - timedelta(days=1)
    baseline_start = baseline_end - timedelta(days=baseline_days - 1)

    grouped: dict[str, dict] = {}
    for row in deduped:
        code = _visit_text(row.get("sec_code"))
        if not code:
            continue
        exchange = _visit_text(row.get("exchange"))
        key = f"{exchange}:{code}" if exchange else code
        source_day = _visit_day(row.get("source_published_at"))
        if source_day is None:
            continue
        observed_day = _visit_day(row.get("system_recorded_at"))
        bucket = grouped.setdefault(key, {
            "company_key": key,
            "sec_code": code,
            "sec_name": _visit_text(row.get("sec_name")),
            "exchange": exchange,
            "rows": [],
        })
        # Positive source evidence remains visible even when its publication
        # predates our forward-only coverage stamp (the first P1 run uses a
        # bounded lookback). The source day is the event clock; system_recorded_at
        # is the observation/first-seen clock. They must never substitute for
        # each other.
        bucket["rows"].append((source_day, observed_day, row))

    # Company-scoped exceptions deserve an explicit UNKNOWN record even when no
    # canonical visit row could be admitted.
    for code in open_scoped_codes:
        if not code:
            continue
        if not any(v.get("sec_code") == code for v in grouped.values()):
            grouped[code] = {
                "company_key": code,
                "sec_code": code,
                "sec_name": "",
                "exchange": "",
                "rows": [],
            }

    examples: list[dict] = []
    for key in sorted(grouped):
        bucket = grouped[key]
        rows = sorted(bucket["rows"], key=lambda item: (
            item[0], item[1] or date.min, _visit_text(item[2].get("announcement_id"))
        ))
        code = bucket["sec_code"]
        recent = [r for source_day, _observed_day, r in rows
                  if recent_start <= source_day <= observation_end]
        baseline = [r for source_day, _observed_day, r in rows
                    if baseline_start <= source_day <= baseline_end]
        if not recent and code not in open_scoped_codes:
            continue

        company_exception = code in open_scoped_codes
        if has_unscoped_open:
            baseline_state = "blocked_unscoped_coverage_exception"
        elif company_exception:
            baseline_state = "blocked_company_coverage_exception"
        elif source_status == "stale":
            baseline_state = "unavailable_source_stale"
        elif source_status != "ok":
            baseline_state = "unavailable_source_health"
        elif coverage_day is None or coverage_day > baseline_start:
            baseline_state = "insufficient_observed_history"
        else:
            baseline_state = "measured"

        observed_days = [observed_day for _source_day, observed_day, _r in rows
                         if observed_day is not None]
        first_observed_day = min(observed_days) if observed_days else None
        if company_exception:
            first_seen_state = "unknown_due_coverage_exception"
        elif not recent:
            first_seen_state = "no_recent_positive_evidence"
        elif first_observed_day is None:
            first_seen_state = "observation_clock_unavailable"
        elif coverage_day is None or first_observed_day < coverage_day:
            first_seen_state = "previous_observation_not_coverage_qualified"
        elif recent_start <= first_observed_day <= observation_end:
            first_seen_state = "first_observed_since_coverage_start"
        else:
            first_seen_state = "previously_observed_since_coverage_start"

        recent_rate = len(recent) / recent_days if recent else 0.0
        baseline_rate = len(baseline) / baseline_days if baseline_state == "measured" else None
        ratio = None
        comparison = None
        higher = None
        if baseline_state == "measured" and recent:
            if len(baseline) == 0:
                comparison = "recent_activity_after_measured_zero_baseline"
                higher = True
            else:
                ratio = recent_rate / baseline_rate if baseline_rate else None
                higher = recent_rate > baseline_rate
                comparison = (
                    "recent_rate_higher" if higher
                    else "recent_rate_lower" if recent_rate < baseline_rate
                    else "recent_rate_equal"
                )

        kind_counts: dict[str, int] = {}
        classes: set[str] = set()
        for row in recent:
            try:
                kind_en, _kind_zh = kind_labeler(_visit_text(row.get("title")))
            except Exception:  # noqa: BLE001
                kind_en = "investor visit"
            kind_counts[kind_en] = kind_counts.get(kind_en, 0) + 1
            classes.add(_visit_text(row.get("visitor_class")).lower())

        resolved_actor_present = any(c not in _VISIT_UNKNOWN_CLASSES for c in classes)
        examples.append({
            "company_key": key,
            "sec_code": code,
            "sec_name": bucket["sec_name"],
            "exchange": bucket["exchange"],
            "coverage_state": (
                "unknown_company_exception" if company_exception
                else "positive_metadata_observed" if recent
                else "unknown"
            ),
            "first_seen_state": first_seen_state,
            "earliest_source_published_day": rows[0][0].isoformat() if rows else None,
            "first_observed_system_day": (
                first_observed_day.isoformat() if first_observed_day else None
            ),
            "recent_count": len(recent),
            "recent_window_start": recent_start.isoformat(),
            "recent_window_end": observation_end.isoformat(),
            "baseline_state": baseline_state,
            "baseline_count": len(baseline) if baseline_state == "measured" else None,
            "baseline_window_start": baseline_start.isoformat(),
            "baseline_window_end": baseline_end.isoformat(),
            "recent_rate_per_day": recent_rate if recent else 0.0,
            "baseline_rate_per_day": baseline_rate,
            "recent_vs_baseline_rate_ratio": ratio,
            "recent_activity_higher_than_baseline": higher,
            "rate_comparison": comparison,
            "activity_type_counts": kind_counts,
            "visitor_identity_state": (
                "actor_enriched_rows_present"
                if resolved_actor_present
                else "metadata_only_not_yet_available"
            ),
            "actor_recurrence_state": "not_evaluated_without_body_stage_receipt",
            "may_rank": False,
            "may_trade": False,
        })

    base["n_recent_companies"] = sum(1 for r in examples if r["recent_count"] > 0)
    base["n_first_observed_recent"] = sum(
        1 for r in examples if r["first_seen_state"] == "first_observed_since_coverage_start"
    )
    base["n_measured_baselines"] = sum(
        1 for r in examples if r["baseline_state"] == "measured"
    )
    # The briefing stays bounded. These are deterministic examples, not a ranking.
    base["examples"] = examples[:24]
    base["examples_truncated"] = len(examples) > 24
    return base


def _visit_discovery_block() -> dict | None:
    """CIE-07 metadata-only discovery from the existing P1 visit owner."""
    try:
        from collectors import china_visits as cv

        visits = _visit_frame_records(cv.read_visits_strict())
        exceptions = _visit_frame_records(cv.read_coverage_exceptions_strict())
        if visits is None or exceptions is None:
            return {
                "schema": _VISIT_DISCOVERY_SCHEMA,
                "is_context_only": True,
                "authority": {
                    "is_context_only": True, "may_rank": False, "may_trade": False,
                    "may_feed_prophet": False, "may_infer_visitor_identity": False,
                    "may_claim_predictive_edge": False,
                },
                "source_status": "source_failure",
                "coverage_start": None,
                "observation_end": None,
                "asof": None,
                "global_negative_authority": False,
                "global_negative_authority_blocker": "owner_store_unreadable",
                "examples": [],
                "scientific_state": "descriptive_only_not_alpha_evidence",
                "actor_recurrence_state": "not_evaluated_without_body_stage_receipt",
            }

        open_rows = [r for r in exceptions if _visit_text(r.get("status")) == "open"]
        open_scoped_codes: set[str] = set()
        has_unscoped = False
        for row in open_rows:
            code = row.get("sec_code")
            if cv.is_unscoped_sec_code(code):
                has_unscoped = True
            else:
                norm = _visit_text(code)
                if norm:
                    open_scoped_codes.add(norm)

        health = cv.read_health()
        coverage_start = cv.read_coverage_start()
        if (
            not visits
            and not open_rows
            and _visit_text(health.get("status")) == "no_coverage"
            and not coverage_start
        ):
            return None

        return _visit_discovery_snapshot(
            visits,
            health=health,
            coverage_start=coverage_start,
            open_scoped_codes=open_scoped_codes,
            has_unscoped_open=has_unscoped,
            kind_labeler=cv.visit_kind_label,
            reference_day=date.today(),
            stale_after_days=getattr(
                cv.ChinaVisitsAdapter, "stale_after_days", _VISIT_DISCOVERY_STALE_AFTER_DAYS
            ),
        )
    except Exception as e:  # noqa: BLE001
        log.debug("china_intel_bus: visit discovery block failed (%s)", e)
        return None


def _policy_phrase_block() -> dict | None:
    """Policy-phrase shift events from communique_diff (APPEARED/DROPPED/LEAD_SHIFT).

    Reads site/communique_diff/latest.json — built by engine/communique_diff.py.
    Returns None if the file is absent or has no events.  Salience-only context;
    direction=0.  The 14d recency window filters to recent events only.
    """
    try:
        from datetime import date, timedelta
        raw = _read_json("communique_diff/latest.json")
        if not isinstance(raw, dict):
            return None
        asof = raw.get("asof") or ""
        events = raw.get("events") or []
        cold_start_organs = raw.get("cold_start_organs") or []
        # Defensive 14d recency filter — communique_diff stamps all events with the run asof,
        # so in practice all events already share the top-level asof and this filter is a no-op.
        # Kept as a defensive guard in case a future producer emits per-event asof values.
        cutoff = ""
        try:
            cutoff = (date.fromisoformat(str(asof)[:10]) - timedelta(days=14)).isoformat()
        except (ValueError, TypeError):
            pass
        recent = [e for e in events if not cutoff or str(e.get("asof", ""))[:10] >= cutoff]
        if not recent and not asof:
            return None
        # counts by type
        type_counts = {}
        organs_seen = set()
        for e in recent:
            kind = e.get("kind", "")
            type_counts[kind] = type_counts.get(kind, 0) + 1
            org = e.get("organ", "")
            if org:
                organs_seen.add(org)
        # Stamp cycle-context chips onto each event (W5).  Uses the event's own asof
        # date (or the block asof as fallback).  Chips are muted/descriptive context only.
        stamped = []
        for e in recent[:8]:
            ev = dict(e)
            ev_date = str(ev.get("asof") or asof)[:10]
            chip = _regime_chip_for_date(ev_date)
            if chip:
                ev["regime_chip"] = chip
            stamped.append(ev)
        return {
            "asof": asof,  # "last diff run" — communique_diff stamps run day, not corpus freshness
            "n_events_recent": len(recent),
            "n_appeared": type_counts.get("APPEARED", 0),
            "n_dropped": type_counts.get("DROPPED", 0),
            "n_lead_shift": type_counts.get("LEAD_SHIFT", 0),
            "organs_covered": sorted(organs_seen),
            "cold_start_organs": cold_start_organs,
            "recent_events": stamped,   # cap for transport already applied above
            "is_context_only": True,
            "claim_family": "communique_diff",
            "note_en": "Salience-only — direction unproven (accruing)",
            "note_zh": "仅显著性——方向未验证（台账积累中）",
        }
    except Exception as e:  # noqa: BLE001
        log.debug("china_intel_bus: policy_phrase block failed (%s)", e)
        return None


def _narrative_divergence_block() -> dict | None:
    """Onshore/offshore GDELT tone divergence z-score from tone_divergence.parquet.

    Reads data/missing_tape/tone_divergence.parquet.  Degrades cleanly to None
    if parquet is absent or unreadable.  Direction=0 — this is a RISK FLAG only;
    the directionality of the divergence is unproven.
    """
    try:
        import pandas as pd
        p = config.ROOT / "data" / "missing_tape" / "tone_divergence.parquet"
        if not p.exists():
            return None
        df = pd.read_parquet(p)
        if df.empty:
            return None
        df = df.sort_values("date").reset_index(drop=True)
        # latest row
        last = df.iloc[-1]
        latest_z = last.get("spread_expanding_z")
        latest_date = str(last.get("date", ""))[:10]
        # 5d trend: last 5 rows z-score direction
        trend_dir = None
        if len(df) >= 6:
            recent5 = df["spread_expanding_z"].dropna().tail(5)
            if len(recent5) >= 2:
                delta = float(recent5.iloc[-1]) - float(recent5.iloc[0])
                trend_dir = "rising" if delta > 0.1 else ("falling" if delta < -0.1 else "flat")
        import math
        z_val = float(latest_z) if latest_z is not None and not (isinstance(latest_z, float) and math.isnan(latest_z)) else None
        if z_val is None:
            return None
        return {
            "asof": latest_date,
            "divergence_z": round(z_val, 3),
            "trend_5d": trend_dir,
            "risk_flag": z_val > 1.5,  # one-sided: high z = suppression-suspect; negative z is not a flag
            "is_context_only": True,
            "direction_proven": False,
            "note_en": "Risk flag only — direction unproven (direction=0). High z suggests domestic tape quieter than offshore coverage.",
            "note_zh": "仅风险标志——方向未验证（direction=0）。高z值提示境内报道可能较境外更平静。",
        }
    except Exception as e:  # noqa: BLE001
        log.debug("china_intel_bus: narrative_divergence block failed (%s)", e)
        return None


def _analysis_block() -> dict | None:
    a = _read_json("china_intel_analysis/analysis.json")
    if not isinstance(a, dict):
        return None
    out = {k: a.get(k) for k in
           ("conviction", "chains", "cross_refs", "what_matters", "what_changed",
            "flagged_tickers", "asof") if a.get(k) is not None}
    # Carry the llm_synthesis degraded state so the template can render it explicitly
    # per spec §2.4 (brain_usable = present AND not degraded_reason).
    out["llm_synthesis"] = a.get("llm_synthesis")
    out["llm_synthesis_degraded_reason"] = a.get("llm_synthesis_degraded_reason")
    return out


# --------------------------------------------------------------------------- #
# digest — synthesis-led, de-duped, names not codes
# --------------------------------------------------------------------------- #
def _digest_text(b: dict) -> str:
    parts: list[str] = []
    a = b.get("analysis") or {}
    wm = a.get("what_matters") or []
    if wm:
        parts.append("WHAT MATTERS MOST:")
        for w in wm[:3]:
            parts.append(f"  • {w.get('label_en')} — {w.get('detail_en')}")
    wc = a.get("what_changed") or {}
    changed = []
    if wc.get("stance_change"):
        changed.append(f"PBoC stance {wc['stance_change']['from']}→{wc['stance_change']['to']}")
    if wc.get("sentiment_band_change"):
        changed.append(f"news mood {wc['sentiment_band_change']['from']}→{wc['sentiment_band_change']['to']}")
    if wc.get("new_radar_fires"):
        changed.append(f"new radar: {', '.join(wc['new_radar_fires'][:3])}")
    if wc.get("new_accumulation"):
        changed.append(f"new accumulation: {', '.join(wc['new_accumulation'][:3])}")
    if changed:
        parts.append("CHANGED TODAY: " + " · ".join(changed))
    conv = a.get("conviction") or []
    if conv:
        parts.append("STACKED READS:")
        for c in conv[:3]:
            parts.append(f"  • {c.get('sector_en')} ({c.get('radar_sign')}) cc={c.get('context_conviction')} "
                         f"[{'+'.join(c.get('surfaces_confirming', []))}]")
    # per-surface lines
    n = b.get("news")
    if n:
        z = n.get("sentiment_z")
        parts.append(f"News: media sentiment {n.get('band','?')}"
                     + (f" (z {z:+.2f})" if isinstance(z, (int, float)) else "")
                     + (f", {n['n_events_7d']} events/7d" if n.get("n_events_7d") else ""))
        if n.get("flagged_baskets"):
            parts.append("  baskets: " + ", ".join(f"{fb['name_en']}({fb['hits']})"
                                                   for fb in n["flagged_baskets"][:4]))
    p = b.get("policy")
    if p:
        line = (f"PBoC: stance {p.get('pboc_stance','?')}; LPR1Y {p.get('lpr_1y','?')} / "
                f"5Y {p.get('lpr_5y','?')}; RRR {p.get('rrr','?')}")
        if p.get("impulse"):
            line += f" — {p['impulse']['label_en']}"
        parts.append(line)
    ad = b.get("altdata")
    if ad and ad.get("accumulate"):
        parts.append("Alt-data accumulation: "
                     + ", ".join(f"{r.get('name')}({r.get('ticker')})" for r in ad["accumulate"][:4]))
    r = b.get("radar")
    if r and r.get("divergences"):
        seen, lines = set(), []
        for d in r["divergences"]:
            key = f"{d.get('signal_en')}→{d.get('sector')}"
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"{key} {d.get('sign')}")
        parts.append("Radar divergences: " + "; ".join(lines[:5])
                     + f" (ledger: {r.get('ledger',{}).get('grade','?')})")
    pp = b.get("policy_phrase")
    if pp and pp.get("n_events_recent"):
        n_total = pp.get("n_events_recent", 0)
        appeared = pp.get("n_appeared", 0)
        dropped = pp.get("n_dropped", 0)
        lead_shift = pp.get("n_lead_shift", 0)
        organs = ", ".join((pp.get("organs_covered") or [])[:3])
        parts.append(
            f"Policy phrase shifts (14d): {n_total} events"
            + (f" ({appeared} appeared" if appeared else "")
            + (f" / {dropped} dropped" if dropped else "")
            + (f" / {lead_shift} lead-shift" if lead_shift else "")
            + (")" if appeared or dropped or lead_shift else "")
            + (f" — organs: {organs}" if organs else "")
            + " [salience-only, accruing]"
        )
    nd = b.get("narrative_divergence")
    if nd and nd.get("divergence_z") is not None:
        z = nd["divergence_z"]
        risk = " [RISK FLAG]" if nd.get("risk_flag") else ""
        trend = f" trend: {nd.get('trend_5d')}" if nd.get("trend_5d") else ""
        parts.append(f"Onshore/offshore tone divergence z={z:+.2f}{trend}{risk} (direction=0, accruing)")
    # command line: top-2 ranked names for Mastermind transport
    cmd = b.get("command")
    if cmd and cmd.get("top10"):
        top2 = cmd["top10"][:2]
        cmd_line_parts = []
        for row in top2:
            ticker = row.get("ticker") or "?"
            stage = row.get("stage") or "?"
            edge = row.get("edge_remaining")
            edge_str = f" edge={edge:.0%}" if isinstance(edge, float) else ""
            cmd_line_parts.append(f"{ticker} ({stage}{edge_str})")
        parts.append("COMMAND TOP-2: " + " · ".join(cmd_line_parts)
                     + f" (universe={cmd.get('n_universe','?')}, context-only)")
    context = b.get("us_theme_context") or {}
    if context.get("status") == "CURRENT" and context.get("summary"):
        parts.append(context["summary"])
    if not parts:
        return "China intelligence bus: no surfaces built yet."
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# v5: special_situations block
# --------------------------------------------------------------------------- #
def _special_situations_block() -> dict | None:
    """Compact summary of the special-situations desk for the hub card.

    Reads site/chinaspecialdata/special.json and extracts: counts per category,
    top unlock event, newest inquiry letter. Degrades to None when absent.
    """
    data = _read_json("chinaspecialdata/special.json")
    if not data or not isinstance(data, dict):
        return None
    out: dict = {
        # data_asof = worst (oldest) per-input asof from the engine scan; falls back to asof
        "asof": data.get("data_asof") or data.get("asof"),
        "is_context_only": True,
    }
    # counts per category
    for key, cnt_field in (
        ("unlocks",     "n_events_30d"),
        ("inquiry",     "n_letters"),
        ("preannounce", "n_total"),
        ("buyback",     "n_active"),
        ("pledge",      "n_high"),
        ("st",          "count"),
        ("block_trades", "n_names"),
    ):
        blk = data.get(key) or {}
        out[f"n_{key}"] = blk.get(cnt_field) if isinstance(blk, dict) else None

    # top unlock (for hub card)
    unlock_events = (data.get("unlocks") or {}).get("events") or []
    if unlock_events:
        top = unlock_events[0]
        out["top_unlock"] = {
            "ticker":      top.get("ticker"),
            "name":        top.get("name"),
            "unlock_date": top.get("unlock_date"),
            "float_ratio": top.get("float_ratio"),
            "large_flag":  top.get("large_flag"),
        }

    # newest inquiry letter (for hub card)
    inq_letters = (data.get("inquiry") or {}).get("letters") or []
    if inq_letters:
        newest = inq_letters[0]
        out["newest_letter"] = {
            "secCode": newest.get("secCode"),
            "secName": newest.get("secName"),
            "date":    newest.get("date"),
            "has_reply": newest.get("has_reply"),
            # has_reply is a strict positive claim, so it collapses "no reply
            # filed" and "we could not tie a reply to THIS inquiry" into one
            # False. A consumer reading only that boolean would render an
            # undetermined letter as an open regulatory question. Carry the
            # three-valued state so downstream surfaces can tell them apart.
            "reply_state": newest.get("reply_state"),
        }

    return out


# --------------------------------------------------------------------------- #
# v6: command block — compact top-10 from the W4 command apparatus
# --------------------------------------------------------------------------- #
def _command_block() -> dict | None:
    """Compact command summary from site/china_intel/command.json (W4 apparatus).

    Reads the already-built artifact (build order: build_china_intel_hub runs first).
    Returns None when artifact absent — degrade-safe.  Additive over v5 (prefix-match safe).

    Contract: returns {asof, n_universe, counts, top10, discovery_n, is_context_only}.
    Analogs are handled separately via _analogs_block_from_command().
    """
    try:
        data = _read_json("china_intel/command.json")
        if not isinstance(data, dict):
            return None
        command = data.get("command") or []
        return {
            "asof": data.get("as_of"),
            "n_universe": data.get("n_universe"),
            "counts": data.get("counts"),
            "top10": [
                {
                    "ticker": d.get("ticker"),
                    "name": d.get("name"),
                    "stage": d.get("stage"),
                    "opportunity_score": d.get("opportunity_score"),
                    "edge_remaining": d.get("edge_remaining"),
                    "leading_gap": d.get("leading_gap"),
                }
                for d in command[:10]
            ],
            "us_theme_context": context_for_briefing(data.get("us_theme_context"), site=_site_dir()),
            "discovery_n": len(data.get("discovery") or []),
            "is_context_only": True,
        }
    except Exception as e:  # noqa: BLE001
        log.debug("china_intel_bus: command block failed (%s)", e)
        return None


# --------------------------------------------------------------------------- #
# v6: analogs block — reads site/china_intel/analogs.json (separate from command)
# --------------------------------------------------------------------------- #
def _analogs_block() -> dict | None:
    """Read site/china_intel/analogs.json (schema china_intel.analogs.v1).

    Separate from the command block so the template K4 can read b.analogs independently.
    Returns None when artifact absent — NOT added to surfaces_present until non-None
    (the artifact does not exist today; auto-lights when a parallel program ships it).
    """
    try:
        d = _read_json("china_intel/analogs.json")
        if not isinstance(d, dict):
            return None
        if d.get("schema") != "china_intel.analogs.v1":
            log.debug("china_intel_bus: analogs schema mismatch: %s", d.get("schema"))
            return None
        if not d.get("fan") or not d.get("query"):
            return None
        return {
            "as_of": d.get("as_of"),
            "coverage": d.get("coverage"),
            "query": d.get("query"),
            "analogs": (d.get("analogs") or [])[:12],
            "fan": d.get("fan"),
            "method_note": d.get("method_note"),
            "disclaimer_en": d.get("disclaimer_en"),
            "disclaimer_zh": d.get("disclaimer_zh"),
            "n_analogs": len(d.get("analogs") or []),
        }
    except Exception as e:  # noqa: BLE001
        log.debug("china_intel_bus: analogs block failed (%s)", e)
        return None


# --------------------------------------------------------------------------- #
# public
# --------------------------------------------------------------------------- #
def _staleness(b: dict) -> tuple[dict, int]:
    sa, worst = {}, 0
    for k in ("news", "policy", "altdata", "radar", "analysis",
              "policy_phrase", "narrative_divergence", "special_situations", "visit_discovery", "command"):
        d = (b.get(k) or {}).get("asof") if isinstance(b.get(k), dict) else None
        sa[k] = d
        if d:
            try:
                age = (date.today() - date.fromisoformat(str(d)[:10])).days
                worst = max(worst, age)
            except (ValueError, TypeError):
                pass
    return sa, worst


def briefing(asof: date | str | None = None) -> dict:
    """Assemble the context-only `china_intel.briefing.v6`. Always valid; never raises."""
    b = {
        "schema": SCHEMA, "is_context_only": True,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "asof": str(asof) if asof else str(date.today()),
        "news": None, "policy": None, "altdata": None, "radar": None, "analysis": None,
        "regime": None, "discovery": None,
        "policy_phrase": None, "narrative_divergence": None,
        "special_situations": None, "visit_discovery": None, "command": None,
        "analogs": None,   # v6: separate from command; NOT in surfaces_present until non-None
        "disclaimer": DISCLAIMER, "disclaimer_zh": DISCLAIMER_ZH,
    }
    for key, fn in (("news", _news_block), ("policy", _policy_block),
                    ("altdata", _altdata_block), ("radar", _radar_block),
                    ("analysis", _analysis_block), ("regime", _regime_block),
                    ("discovery", _discovery_block),
                    ("policy_phrase", _policy_phrase_block),
                    ("narrative_divergence", _narrative_divergence_block),
                    ("special_situations", _special_situations_block),
                    ("visit_discovery", _visit_discovery_block),
                    ("command", _command_block),
                    ("analogs", _analogs_block)):
        try:
            b[key] = fn()
        except Exception as e:  # noqa: BLE001
            log.debug("china_intel_bus: %s block failed (%s)", key, e)
            b[key] = None
    # Keep foreign/local observations separate from local stock rankings.
    b["us_theme_context"] = (b.get("command") or {}).get("us_theme_context")
    # hoist synthesis to the top level for the hub + bot
    a = b.get("analysis") or {}
    b["conviction"] = a.get("conviction") or []
    b["cross_surface"] = [c for c in (a.get("conviction") or []) if c.get("n_surfaces", 0) >= 2]
    b["flagged_tickers"] = a.get("flagged_tickers") or []
    b["what_changed"] = a.get("what_changed") or {}
    b["salience"] = a.get("what_matters") or []
    # analogs NOT in surfaces_present until the artifact ships (degrade-safe)
    b["surfaces_present"] = [k for k in ("news", "policy", "altdata", "radar", "analysis",
                                        "policy_phrase", "narrative_divergence",
                                        "special_situations", "visit_discovery", "command") if b.get(k)]
    b["surface_asof"], b["max_staleness_days"] = _staleness(b)
    b["digest"] = _digest_text(b)
    return b


def build() -> dict | None:
    """Write site/china_intel/{briefing,digest}.json. Returns the briefing or None."""
    try:
        b = briefing()
        outdir = _site_dir() / "china_intel"
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "briefing.json").write_text(
            json.dumps(b, ensure_ascii=False, separators=(",", ":"), default=str))
        (outdir / "digest.json").write_text(json.dumps(
            {"schema": "china_intel.digest.v2", "is_context_only": True,
             "generated_utc": b["generated_utc"], "asof": b["asof"],
             "surfaces_present": b["surfaces_present"],
             "max_staleness_days": b["max_staleness_days"], "text": b["digest"]},
            ensure_ascii=False, separators=(",", ":"), default=str))
        log.info("china_intel_bus: wrote briefing v5 (%d surfaces, %d conviction)",
                 len(b["surfaces_present"]), len(b["conviction"]))
        return b
    except Exception as e:  # noqa: BLE001
        log.error("china_intel_bus build failed (%s)", e)
        return None

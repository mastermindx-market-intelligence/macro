"""Literal Sector Pulse functions from 7885f75, independent of the extracted core.
Source SHA256: 969a94a79d1f2713e8104fa532b73557e0ab0e2c7492b8773f916f374f94cc9e.
Only acquisition stubs and this import prelude are fixture scaffolding.
"""
from __future__ import annotations
import logging
from datetime import date
log = logging.getLogger(__name__)

def _load_archive_snapshots(region):
    raise AssertionError("Supply captured archive in the independent fixture")

def _heat_calibration():
    raise AssertionError("Supply captured calibration in the independent fixture")

_HEAT_RANK_DELTA = 3


_HEAT_SCORE_DELTA = 6


_COOL_RANK_DELTA = -3


_HOT_LABELS = {"dominant", "emerging"}


_COOL_LABEL = "fading"


_BROKEN_LABEL = "deteriorating"


SCHEMA = 1


def _observation_date(value: object) -> str | None:
    """Accept the producer's ISO session date; never substitute the build clock."""
    if not isinstance(value, str):
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return value if parsed.isoformat() == value else None


def _archive_through_observation(snapshots: list[dict], as_of: str, region: str) -> list[dict]:
    """Anchor deltas to the current theme observation, not the archive tail.

    The archive is keep-FIRST per asof (signal_archive.archive_snapshot). Preserve
    that law, discard malformed/future rows, and count each date once. The current
    theme may be rendered before its archive write; a zero-offset anchor prevents
    that sequencing difference from shifting every comparison back an observation.
    This is observation-date alignment, not a claim of logged-at/PIT replay.
    """
    by_date: dict[str, dict] = {}
    for snap in snapshots:
        if not isinstance(snap, dict):
            continue
        observed = _observation_date(snap.get("asof"))
        rows = snap.get("themes")
        if (observed is None or observed >= as_of
                or not isinstance(rows, list) or not rows):
            continue
        by_date.setdefault(observed, snap)
    # No source is mutated. Offset helpers never consume this anchor's values:
    # the current theme is the measurement, and comparison offsets start at 1.
    anchor = {"asof": as_of, "themes": []}
    if region == "us":
        from lib.nyse_calendar import session_n_back

        reference = date.fromisoformat(as_of)
        if session_n_back(reference, 0) is None:
            return [anchor]
        aligned = []
        for offset in range(20, 0, -1):
            target = session_n_back(reference, offset)
            day = target.isoformat() if target is not None else None
            # An absent session stays an empty slot; it cannot stretch a 5-day
            # window into 6+ sessions or make an older print mean yesterday.
            aligned.append(by_date.get(day, {"asof": day, "themes": []}))
        return aligned + [anchor]
    # Other regions retain their dated archive-observation convention. They do
    # not borrow the US calendar or silently claim session-complete horizons.
    return [by_date[day] for day in sorted(by_date)] + [anchor]


def _rank_map_at(snapshots: list[dict], offset_sessions: int) -> dict[str, int]:
    """Return {theme_id: rank} from `offset_sessions` rows before the last snapshot.

    offset_sessions=5 → use the snapshot that is ≥5 rows back (0-indexed from end).
    Returns {} when there are not enough rows.
    """
    needed = offset_sessions + 1   # need at least this many rows to have an "N ago" row
    if len(snapshots) < needed:
        return {}
    snap = snapshots[-(needed)]
    return {t["id"]: t["rank"] for t in snap.get("themes", []) if t.get("id") and t.get("rank")}


def _score_map_at(snapshots: list[dict], offset_sessions: int) -> dict[str, int | float]:
    """Return {theme_id: score} from `offset_sessions` rows before the last snapshot."""
    needed = offset_sessions + 1
    if len(snapshots) < needed:
        return {}
    snap = snapshots[-(needed)]
    return {t["id"]: t["score"] for t in snap.get("themes", []) if t.get("id") and t.get("score") is not None}


def _heat_tier(rank: int, n_themes: int, label: str,
               rank_delta_5d: int | None, score_delta_5d: float | None) -> str:
    """Classify this theme's current momentum state into one of five descriptive tiers.

    Tiers (mutually exclusive, tested in priority order):
      "broken"  — label is 'deteriorating'; structure breaking down.
      "cooling" — rank dropped ≥3 positions in 5 sessions, OR label is 'fading'.
                  Takes precedence over "hot" so a formerly-hot theme rolling over
                  reads as cooling rather than hot.
      "heating" — rank improved ≥3 positions in 5 sessions (positive rank_delta means
                  better rank, i.e. lower number) OR score rose ≥6 points, AND the
                  label is in the upward-phase set (emerging / dominant).
      "hot"     — rank is in the top quartile (rank ≤ max(1, n_themes // 4)), label is
                  dominant or emerging, and not cooling.
      "idle"    — everything else.

    All tiers are DESCRIPTIVE: they characterise the current rank/score trajectory
    and label state.  They carry no forward-return forecast.  rank_delta_5d and
    score_delta_5d are None when archive history is too short — treated as 0 (no
    signal either way) so new themes default to "idle" until history accrues.
    """
    if label == _BROKEN_LABEL:
        return "broken"

    rd5 = rank_delta_5d if rank_delta_5d is not None else 0
    sd5 = score_delta_5d if score_delta_5d is not None else 0.0

    # rank_delta_5d is defined as (rank_N_sessions_ago − rank_now):
    # positive → rank number DECREASED (i.e. moved up the board) → improvement.
    is_cooling_delta = rd5 <= _COOL_RANK_DELTA   # rank worsened ≥3 positions
    if is_cooling_delta or label == _COOL_LABEL:
        return "cooling"

    top_n = max(1, n_themes // 4)
    is_top_quartile = rank <= top_n
    is_upward_label = label in _HOT_LABELS

    is_heating = (rd5 >= _HEAT_RANK_DELTA or sd5 >= _HEAT_SCORE_DELTA) and is_upward_label
    if is_heating:
        return "heating"

    if is_top_quartile and is_upward_label:
        return "hot"

    return "idle"


def _heat_strength(heat: str | None, cal: dict) -> dict | None:
    """Grade a theme's CURRENT heat tier by what the kill-test measured about it —
    mirrors theme_scoring._signal_strength. Phase-0 verdict (2026-07-03, 27y proxy):
    heating/hot showed NO forward-return edge vs same-day idle, and if anything slightly
    DEEPER forward drawdowns (the inverted tripwire) → 'descriptive'; cooling was NOT
    separately confirmed (the rank-drop leg dilutes the validated fading label) →
    'unconfirmed'; broken precedes measurably deeper drawdowns → 'backtested' risk.
    cal {} → None (payload keeps its existing honest framing); idle carries no claim."""
    if not cal or heat in (None, "idle"):
        return None
    v = cal.get(heat) or {}
    if not v or v.get("verdict") in (None, "baseline"):
        return None
    measured = v.get("verdict") == "measurable_edge"
    inverted = bool(v.get("inverted"))
    common = {"measured": bool(measured), "metric": v.get("claim"),
              "mean_pct": v.get("mean_pct"), "t_hac": v.get("t_hac"),
              "n_days": v.get("n_days")}
    if heat in ("cooling", "broken"):
        return {"grade": "backtested" if measured else "unconfirmed", "kind": "risk",
                **common,
                "en": ("Backtested risk read — on 27y of proxy history this tier precedes "
                       "measurably deeper 21-day drawdowns than same-day idle themes "
                       "(a risk timer, not a return forecast)." if measured else
                       "Risk read — not separately confirmed vs idle on the proxy; the "
                       "fading/deteriorating LABEL grades remain the backtested risk reads."),
                "zh": ("已回测的风险信号 — 在27年代理历史上，该档位领先于比同日闲置主题"
                       "更深的21日回撤（风险计时器，非收益预测）。" if measured else
                       "风险信号 — 代理上未相对闲置档单独验证；已回测的风险读数仍是"
                       "退潮/走弱标签本身。")}
    if heat in ("heating", "hot"):
        if measured:
            return {"grade": "backtested", "kind": "continuation", **common,
                    "en": ("Backtested — this tier preceded measurable forward strength "
                           "vs same-day idle themes on the 27y proxy."),
                    "zh": "已回测 — 在27年代理上该档位领先于相对闲置档的可测前向优势。"}
        caution_en = (" If anything, it drew slightly DEEPER 21-day drawdowns than idle "
                      "— a chase caution, never an entry signal.") if inverted else ""
        caution_zh = ("（若有差异，其21日回撤反而略深于闲置档 — 追高警示，绝非入场信号。）"
                      if inverted else "")
        return {"grade": "descriptive", "kind": "continuation", **common,
                "en": ("Descriptive — the phase-0 kill-test found no forward-return or "
                       "drawdown edge vs same-day idle themes on the 27y proxy."
                       + caution_en),
                "zh": ("描述性 — 阶段0检验在27年代理上未发现相对同日闲置主题的前向收益"
                       "或回撤优势。" + caution_zh)}
    return None


def _build_theme_row(th: dict, n_themes: int,
                     rank_1d: dict[str, int], rank_5d: dict[str, int], rank_20d: dict[str, int],
                     score_5d: dict[str, float], score_20d: dict[str, float],
                     heat_cal: dict | None = None) -> dict:
    """Assemble one pulse row from a full theme_intel theme entry + archive look-ups."""
    tid = th["id"]
    cur_rank = th.get("rank")
    cur_score = th.get("score")

    def _delta(cur, hist_map):
        """rank_delta = rank_N_ago − rank_now; positive means rank improved (number went down)."""
        if cur is None or tid not in hist_map:
            return None
        return hist_map[tid] - cur

    def _score_delta(cur, hist_map):
        if cur is None or tid not in hist_map:
            return None
        return cur - hist_map[tid]   # positive means score improved

    rank_delta_1d = _delta(cur_rank, rank_1d)
    rank_delta_5d = _delta(cur_rank, rank_5d)
    rank_delta_20d = _delta(cur_rank, rank_20d)
    score_delta_5d = _score_delta(cur_score, score_5d)
    score_delta_20d = _score_delta(cur_score, score_20d)

    label = th.get("label", "neutral")
    heat = _heat_tier(cur_rank or 9999, n_themes, label, rank_delta_5d, score_delta_5d)

    perf = th.get("perf") or {}
    breadth = th.get("breadth") or {}
    textures = th.get("textures") or {}
    mtf = th.get("mtf") or {}
    confluence = mtf.get("confluence") or {}
    ce_raw = textures.get("clean_entry") or {}

    return {
        "id": tid,
        "name": th.get("name", tid),
        "name_zh": th.get("name_zh", th.get("name", tid)),
        "category": th.get("category", "Other"),
        "label": label,
        "reco": th.get("reco", "hold"),
        "score": cur_score,
        "rank": cur_rank,
        # Archive-derived rank deltas (None = history accruing)
        "rank_delta_1d": rank_delta_1d,
        "rank_delta_5d": rank_delta_5d,
        "rank_delta_20d": rank_delta_20d,
        # Archive-derived score deltas (None = history accruing)
        "score_delta_5d": score_delta_5d,
        "score_delta_20d": score_delta_20d,
        # 5-day relative return (from the live theme_intel, not the archive)
        "rel_5d": (perf.get("5d") or {}).get("rel"),
        # Breadth
        "net_ad": th.get("net_ad"),
        "pct50": breadth.get("pct50"),
        # Clean-entry composite
        "clean_entry": {
            "flag": ce_raw.get("flag"),
            "quality": ce_raw.get("quality"),
        },
        # Multi-timeframe momentum
        "momentum_score": mtf.get("momentum_score"),
        "long_sign": confluence.get("long_sign"),
        # Descriptive heat tier + its kill-test grade (None = no calibration / no claim)
        "heat": heat,
        "heat_strength": _heat_strength(heat, heat_cal or {}),
    }


def _build_pulse_from_theme_intel(ti: dict, region: str) -> dict | None:
    """Shared Sector Pulse projection for readers, enrichment and publication.

    Returns a dict with schema/as_of/region/n_themes, plus:
      "themes"  — list of pulse rows (one per theme, sorted by rank ascending)
      "heating" — list of theme ids currently in the 'heating' tier
      "cooling" — list of theme ids currently in the 'cooling' tier

    Returns None (never raises) on any failure or when data is unavailable.
    Rank/score deltas are None when the signal archive has fewer sessions than
    the requested look-back ("history accruing" semantics).
    """
    try:
        if not ti:
            return None
        themes_raw = ti.get("themes") or []
        if not themes_raw:
            return None

        as_of = _observation_date(ti.get("as_of"))
        if as_of is None:
            log.warning("sector_pulse: missing/invalid theme observation date for region=%s", region)
            return None
        n = len(themes_raw)

        # The theme observation is the reference clock. A newer archive cannot
        # revise an older tape, and repeated writes are not new observations.
        snapshots = _archive_through_observation(_load_archive_snapshots(region), as_of, region)

        rank_1d = _rank_map_at(snapshots, 1)
        rank_5d = _rank_map_at(snapshots, 5)
        rank_20d = _rank_map_at(snapshots, 20)
        score_5d = _score_map_at(snapshots, 5)
        score_20d = _score_map_at(snapshots, 20)
        heat_cal = _heat_calibration()

        rows: list[dict] = []
        for th in themes_raw:
            try:
                row = _build_theme_row(th, n, rank_1d, rank_5d, rank_20d, score_5d, score_20d,
                                       heat_cal)
                rows.append(row)
            except Exception:  # noqa: BLE001
                log.debug("sector_pulse: skipping theme %s due to error", th.get("id"), exc_info=True)
                continue

        if not rows:
            return None

        rows.sort(key=lambda r: (r["rank"] is None, r["rank"] or 9999))

        heating = [r["id"] for r in rows if r["heat"] == "heating"]
        cooling = [r["id"] for r in rows if r["heat"] == "cooling"]

        return {
            "schema": SCHEMA,
            "as_of": as_of,
            "region": region,
            "n_themes": n,
            # Actual evidence dates and requested dates are separate: a missing
            # US session must stay unknown, not silently use an older print.
            "history": {
                "basis": ("nyse_sessions" if region == "us"
                          else "distinct_dated_archive_observations"),
                "comparison_as_of": {
                    f"{offset}d": (snapshots[-(offset + 1)]["asof"]
                                    if len(snapshots) > offset
                                    and snapshots[-(offset + 1)]["themes"] else None)
                    for offset in (1, 5, 20)
                },
                "expected_comparison_as_of": {
                    f"{offset}d": (snapshots[-(offset + 1)]["asof"]
                                    if len(snapshots) > offset else None)
                    for offset in (1, 5, 20)
                },
            },
            "themes": rows,
            "heating": heating,
            "cooling": cooling,
            # Per-tier kill-test grades (backtested vs descriptive/unconfirmed); {} when
            # the calibration artifact is absent — consumers fall back to descriptive.
            "heat_grades": {t: (_heat_strength(t, heat_cal) or {}).get("grade")
                            for t in ("heating", "hot", "cooling", "broken")} if heat_cal else {},
        }
    except Exception:  # noqa: BLE001
        log.warning("sector_pulse.build_pulse failed for region=%s", region, exc_info=True)
        return None


def merge_pulse_into_theme_intel(ti: dict, region: str) -> None:
    """Merge per-theme velocity/heat keys from the pulse into a freshly-computed theme_intel dict.

    Adds the following keys to each theme row IN PLACE (additive — existing keys are never
    modified, missing keys default to None so JS can degrade safely on pre-W4 payloads):

        pulse_heat          — str: "heating" | "hot" | "cooling" | "broken" | "idle" | None
        pulse_heat_grade    — str | None: "backtested" | "descriptive" | "unconfirmed"
                              (the kill-test grade for the tier; None = no calibration
                              artifact or the tier carries no claim, e.g. idle)
        pulse_rank_delta_1d — int | None   (positive = rank improved, i.e. number went down)
        pulse_rank_delta_5d — int | None
        pulse_rank_delta_20d — int | None
        pulse_score_delta_5d — float | None

    Keys use a `pulse_` prefix to avoid shadowing the existing `rank_5d` / `delta_5d` keys
    that engine.theme_scoring already writes on each theme row.

    Additive and never-fatal: a failure logs a warning and leaves theme_intel untouched.
    """
    try:
        themes_raw = ti.get("themes") or []
        if not themes_raw:
            return

        payload = _build_pulse_from_theme_intel(ti, region)
        if payload is None:
            return
        pulse_by_id = {row["id"]: row for row in payload["themes"] if row.get("id")}
        fields = {
            "pulse_heat": "heat",
            "pulse_rank_delta_1d": "rank_delta_1d",
            "pulse_rank_delta_5d": "rank_delta_5d",
            "pulse_rank_delta_20d": "rank_delta_20d",
            "pulse_score_delta_5d": "score_delta_5d",
        }
        for th in themes_raw:
            if not isinstance(th, dict):
                continue
            row = pulse_by_id.get(th.get("id"))
            if row is None:
                continue
            # Additive only: never alter the source rank, score or recommendation.
            for target, source in fields.items():
                th.setdefault(target, row.get(source))
            th.setdefault("pulse_heat_grade", (row.get("heat_strength") or {}).get("grade"))
    except Exception:  # noqa: BLE001
        log.warning("merge_pulse_into_theme_intel failed for region=%s", region, exc_info=True)

"""engine.chronicle.impact — event-to-asset consequence projection (F05, MO-PAID-017).

Reads chronicle spine events (the ONE canonical event owner — see spine.py's
module docstring) and projects a deterministic, owner-native
consequence/impact view per event: which tickers are implicated, whether the
linkage is direct (the event names the ticker) or second-order (inferred only
via shared theme, never via a ticker the event itself did not name), when the
underlying development happened vs when it became knowable, and a causal
label that is capped by construction to never claim more than the evidence
supports.

Do-not-redo (agentos/handoffs/MARKET-ONTOLOGY-F05-EVENT-IMPACT-CATALYST-FABLE-COO-2026-08-26.md):
no second event ID/database, no headline-count event identity, no LLM fact
extraction authority, no opaque catalyst ranker. This module performs no
scoring, no ranking, and no statistical estimation — it is a pure,
deterministic re-projection of fields already present on the chronicle.event.v1
record produced by spine.py. Calibrated impact magnitude is explicitly gated
on K5 (Evaluation OS / registered model law) and always reports as
``not_yet_knowable`` here rather than being estimated by this module.

Materiality law: "direct" means the ticker appears in the event's own
``tickers`` field (the adapter that produced the event already asserted that
linkage from source data). "second_order" means a ticker is NOT on the event
but shares a *narrow* theme with the event and IS directly implicated by some
OTHER event carrying that theme, dated on-or-before this event (point-in-time
-- no future-event leakage) -- a strictly weaker, labelled-as-such claim,
never silently promoted to direct. Broad co-mention themes (e.g. corpus-wide
"earnings") fail closed rather than fabricating materiality. When more than
``SECOND_ORDER_MAX_PER_EVENT`` candidates remain after the specificity +
support filters, the projection refuses ALL second-order exposures for that
event (fail closed on ambiguity) and prints the candidate/dropped counts --
it never ranks by co-mention count or alphabetical tiebreak to pick winners.

Causal label law: every projection carries ``causal_label`` fixed to
``"uncalibrated_association"``. This module has no identification strategy and
therefore never emits "causal" -- that ceiling is structural, not a runtime
check the caller could accidentally skip.

Bitemporal honesty (no fabricated known-at clock): every adapter today sets
``ts`` to either a genuine source publication timestamp, or (when the source
gives only a calendar date) exactly ``f"{date}T00:00:00Z"`` -- the same
instant as ``event_time``, not a distinct ingestion/discovery clock. Printing
that synthetic midnight stamp as "known_at" would fabricate a bitemporal claim
the ledger explicitly disclaims (correction_behavior: "event spine (chronicle)
-- no bitemporal claim made"). So ``known_at`` is populated ONLY when ``ts``
is genuinely distinct from the synthetic midnight-of-date value; otherwise it
is printed as ``None`` with a typed reason, per the fail-closed / nulls-
printed-not-hidden law -- never silently collapsed into ``event_time`` and
never fabricated.

Correction law: an event's ``kind``/fields never carry a corrected/withdrawn
state today (authoritative retractions are excluded from events.jsonl
entirely by spine.apply_authoritative_retractions before this module ever
sees them). A caller that still holds a retracted or superseded event object
(e.g. re-projecting a stale snapshot) can mark it explicitly via
``retracted=True`` / ``retraction_reason`` on :func:`project_event_impact`;
this module never infers retraction on its own -- that stays spine's call.

Nightly write law: this module never writes a git-tracked data/ artifact.
Consumers call :func:`project_events_impact` / :func:`glance_consequence_surface`
at render or inspect time over a bounded event window.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Iterable

# Fixed by construction: this module performs no causal identification, so it
# can never emit a label stronger than an uncalibrated association regardless
# of event kind, weight_hint, or theme overlap.
CAUSAL_LABEL = "uncalibrated_association"

MATERIALITY_DIRECT = "direct"
MATERIALITY_SECOND_ORDER = "second_order"

# K5 (Evaluation OS / registered model law) is not consumed here -- any
# magnitude/probability estimate is out of scope for this projection and
# always reports this reason code rather than a fabricated number.
CALIBRATED_IMPACT_GATE_REASON = "not_yet_knowable_k5_gated"

# No genuine source clock at all (neither ``date`` nor ``ts`` present).
NO_SOURCE_CLOCK = "no_source_clock"
# ``ts`` exists but is not distinguishable from the synthetic
# midnight-of-``date`` stamp every non-timestamped adapter emits -- printing
# it as a separate "known_at" would fabricate a bitemporal claim.
NO_DISTINCT_SOURCE_CLOCK = "no_distinct_source_clock"

# Second-order eligibility (fail closed on weak materiality / ambiguity).
# MIN_SUPPORT is an eligibility floor, not a ranker. MAX_PER_EVENT is a
# refuse-all ceiling when ambiguity remains after the theme-specificity gate
# -- never a top-N selector. THEME_MAX_SHARE refuses corpus-dominant themes
# (measured: "earnings" alone is ~82% of events.jsonl) where co-theme carries
# no information.
SECOND_ORDER_MIN_SUPPORT = 2
SECOND_ORDER_MAX_PER_EVENT = 5
SECOND_ORDER_THEME_MAX_SHARE = 0.05
# Share gate only applies once a theme's absolute count clears this floor —
# otherwise a 3-event fixture would refuse every theme (3/3 = 100% share)
# while the real corpus still needs the share gate for "earnings" (~82%).
SECOND_ORDER_THEME_BROAD_MIN_COUNT = 40
SECOND_ORDER_AMBIGUOUS_REASON = "second_order_refused_ambiguous_cap"
SECOND_ORDER_THEME_TOO_BROAD_REASON = "second_order_refused_theme_too_broad"
# Kept as an alias so older call-sites/tests that still reference the prior
# truncation reason string keep resolving; new emits use AMBIGUOUS_REASON.
SECOND_ORDER_CAPPED_REASON = SECOND_ORDER_AMBIGUOUS_REASON

# Glance-tier surface bound (News Feed consequence panel). Bounded so render
# never runs the full-corpus projection. A glance row must carry a consequence
# (direct ticker or second-order ticker) AND belong to a public market-event
# family. Every glance row must carry a named exposure — no family is
# exempt. prophet_ledger rows are the product's own trade-plan closes — they
# are not market events and never appear on the anonymous News glance
# (typed exclusion). The window is the last 7 days as-of the newest
# parseable event date in the input — no wall-clock on the render path. If
# that window is empty (undated / unparseable corpus), fall back to the
# newest 200 events. Zero qualifying rows prints a typed empty state;
# one or more qualifying rows render (capped at 8). A regime_flip /
# risk_band series that flips two or more times in the window collapses
# to its latest state plus a plain-word unstable note.
GLANCE_WINDOW_DAYS = 7
GLANCE_FALLBACK_LIMIT = 200
GLANCE_ROW_CAP = 8
GLANCE_MIN_QUALIFYING = 1
# Backward-compatible alias: older callers passed this as the pre-filter cap.
GLANCE_EVENT_LIMIT = GLANCE_ROW_CAP
GLANCE_WINDOW_LAST_7 = "last_7_days"
GLANCE_WINDOW_FALLBACK = "newest_200_fallback"
GLANCE_EXCLUDED_FAMILIES = frozenset({"prophet_ledger"})
GLANCE_ELIGIBLE_FAMILIES = frozenset({
    "earnings",
    "earnings_call",
    "macro_release",
    "regime_flip",
    "risk_band",
    "research_vault",
})
EMPTY_NO_EXPOSURE_EN = "No event with a named market exposure in the last 7 days."
EMPTY_NO_EXPOSURE_ZH = "近7天没有带明确市场敞口的事件。"
WINDOW_FALLBACK_LABEL_EN = "Latest 200 recorded events"
WINDOW_FALLBACK_LABEL_ZH = "最近记录的200个事件"
GLANCE_STANCE_EN = (
    "Recent market events and the names they touch — shown only when an "
    "event maps to a named exposure."
)
GLANCE_STANCE_ZH = "近期市场事件及其涉及的标的——仅在事件对应到明确标的时显示。"
FLIP_UNSTABLE_EN = "changed direction twice this week — unstable"
FLIP_UNSTABLE_ZH = "本周两度转向——尚不稳定"
# Families that can whipsaw inside one window. Two or more flips of the
# same series collapse to the latest state plus the unstable note.
GLANCE_FLIP_FAMILIES = frozenset({"regime_flip", "risk_band"})

_MONTH_EN = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)


def _midnight_of(date: str | None) -> str | None:
    return f"{date}T00:00:00Z" if date else None


def _time_fields(event: dict) -> tuple[str | None, str | None, str | None]:
    """Return (event_time, known_at, known_at_null_reason).

    Never fabricates a known_at that the source data does not actually
    support -- see the bitemporal-honesty note in the module docstring.
    event_time and known_at stay the same granularity family: event_time is
    always a calendar date (YYYY-MM-DD) when knowable; known_at is an ISO
    instant only when genuinely distinct from midnight-of-that-date.
    """
    date = event.get("date") or None
    ts = event.get("ts") or None

    if not date and not ts:
        return None, None, NO_SOURCE_CLOCK

    # When date is absent but ts is present, recover the calendar date from
    # the timestamp so we never print known_at beside a null event_time.
    if not date and isinstance(ts, str) and len(ts) >= 10 and ts[4] == "-" and ts[7] == "-":
        date = ts[:10]

    event_time = date
    if ts and ts != _midnight_of(date):
        return event_time, ts, None
    return event_time, None, NO_DISTINCT_SOURCE_CLOCK


def project_event_impact(
    event: dict,
    *,
    second_order_tickers: Iterable[str] = (),
    second_order_sources: dict[str, list[str]] | None = None,
    retracted: bool = False,
    retraction_reason: str | None = None,
) -> dict:
    """Project one chronicle.event.v1 record into a consequence/impact view.

    ``second_order_tickers`` (optional) lets a caller pass tickers implicated
    only via co-theme propagation from OTHER events -- this function never
    invents them itself. A ticker present in both the event's own ``tickers``
    and ``second_order_tickers`` is reported once, as direct (direct always
    wins; second-order is never used to demote a directly-named ticker).

    ``second_order_sources`` (optional) maps each second-order ticker to the
    originating event id(s) that directly named it under the shared theme --
    K1 evidence for what would otherwise be an unsourced claim.

    ``retracted``/``retraction_reason`` let a caller mark an event whose
    authoritative status has been withdrawn (spine.py's correction plane);
    such an event still carries its evidence fields but its exposures are
    force-emptied and its state is reported explicitly rather than silently
    projecting a live claim for a withdrawn record.
    """
    direct = [t for t in (event.get("tickers") or []) if t]
    direct_set = set(direct)
    second_order = [t for t in dict.fromkeys(second_order_tickers or ()) if t and t not in direct_set]
    second_order_sources = second_order_sources or {}

    event_time, known_at, known_at_reason = _time_fields(event)

    if retracted:
        exposures: list[dict] = []
    else:
        exposures = [
            {"ticker": t, "materiality": MATERIALITY_DIRECT} for t in direct
        ] + [
            {
                "ticker": t,
                "materiality": MATERIALITY_SECOND_ORDER,
                "source_event_ids": sorted(second_order_sources.get(t, [])),
            }
            for t in second_order
        ]

    return {
        "event_id": event.get("id"),
        # Time law: event_time is when the underlying development occurred
        # (spine's ``date``); known_at is when the chronicle store could
        # first know about it, printed ONLY when the source data actually
        # supports a distinct clock -- otherwise None + a typed reason
        # (never fabricated, never silently collapsed into event_time).
        "event_time": event_time,
        "known_at": known_at,
        "known_at_reason": known_at_reason,
        "source": event.get("source"),
        "source_ref": event.get("source_ref"),
        "kind": event.get("kind"),
        "title": event.get("title"),
        "facts": list(event.get("facts") or []),
        "links": event.get("links"),
        "themes": list(event.get("themes") or []),
        "exposures": exposures,
        "causal_label": CAUSAL_LABEL,
        "calibrated_impact": None,
        "calibrated_impact_reason": CALIBRATED_IMPACT_GATE_REASON,
        "state": "retracted" if retracted else "active",
        "retraction_reason": retraction_reason if retracted else None,
    }


def _theme_key(theme: object) -> str:
    """Casefold a theme token so 'McElligott' and 'Mcelligott' share a bucket."""
    return str(theme or "").strip().casefold()


def _co_theme_index(events: list[dict]) -> dict[str, list[tuple[str, list[str], str]]]:
    """theme -> [(date, tickers, event_id), ...] for every event that
    directly names tickers under that theme -- one entry per event so
    callers can apply an as-of cutoff and a support-count eligibility test.

    Theme keys are casefolded. Source events with no id are skipped — a
    None id would later crash ``sorted({None, "cev-…"})`` at render time.
    """
    out: dict[str, list[tuple[str, list[str], str]]] = {}
    for ev in events:
        src_id = ev.get("id")
        if not src_id:
            continue
        tickers = [t for t in (ev.get("tickers") or []) if t]
        date = ev.get("date") or ""
        if not tickers:
            continue
        for theme in (ev.get("themes") or []):
            key = _theme_key(theme)
            if not key:
                continue
            out.setdefault(key, []).append((date, tickers, str(src_id)))
    return out


def _eligible_themes(events: list[dict]) -> set[str]:
    """Themes narrow enough that co-theme overlap can carry materiality.

    A theme is refused only when it is both numerous in absolute terms
    (``SECOND_ORDER_THEME_BROAD_MIN_COUNT``) AND appears on more than
    ``SECOND_ORDER_THEME_MAX_SHARE`` of the event set. Corpus-dominant themes
    like "earnings" (~82% of events.jsonl) fail closed; small fixtures and
    genuinely narrow themes stay eligible. Keys are casefolded so spelling
    variants do not split the support floor.
    """
    if not events:
        return set()
    counts: dict[str, int] = {}
    for ev in events:
        seen: set[str] = set()
        for theme in ev.get("themes") or []:
            key = _theme_key(theme)
            if key:
                seen.add(key)
        for key in seen:
            counts[key] = counts.get(key, 0) + 1
    n = len(events)
    eligible: set[str] = set()
    for theme, count in counts.items():
        if count >= SECOND_ORDER_THEME_BROAD_MIN_COUNT and (count / n) > SECOND_ORDER_THEME_MAX_SHARE:
            continue
        eligible.add(theme)
    return eligible


def project_events_impact(
    events: list[dict], *, eligible_themes: set[str] | None = None,
) -> list[dict]:
    """Project a full event list, resolving second-order (co-theme) exposures.

    Point-in-time: a ticker only propagates to an event via themes from OTHER
    events dated on-or-before that event's own date -- a later event can never
    leak its ticker backward onto an earlier one.

    Fail-closed specificity: only themes at-or-below
    ``SECOND_ORDER_THEME_MAX_SHARE`` of the corpus participate. Broad themes
    are refused with a typed reason, not ranked through.

    Fail-closed ambiguity: a ticker must be directly named by at least
    ``SECOND_ORDER_MIN_SUPPORT`` prior co-theme events; if more than
    ``SECOND_ORDER_MAX_PER_EVENT`` candidates remain, ALL second-order
    exposures for that event are refused and the candidate/dropped counts are
    printed. There is no support-count or alphabetical top-N selector -- that
    would be an opaque catalyst ranker (do_not_redo).

    Deterministic and order-preserving: iterating the same event list twice
    yields byte-identical output, matching spine.py's byte-stable regeneration
    contract. No field outside the event's own schema-allowed data is
    consulted -- no external ranking, no LLM call.

    ``eligible_themes``, when given, overrides the eligibility computed from
    ``events`` alone (MAJOR 1). A windowed caller (e.g.
    :func:`glance_consequence_surface`) must compute eligibility over the
    FULL corpus and pass it here -- a small window can never contain the
    ``SECOND_ORDER_THEME_BROAD_MIN_COUNT`` occurrences needed to refuse a
    corpus-dominant theme like "earnings" on its own.
    """
    eligible = _eligible_themes(events) if eligible_themes is None else {
        _theme_key(t) for t in eligible_themes if _theme_key(t)
    }
    by_theme = {
        theme: rows for theme, rows in _co_theme_index(events).items()
        if theme in eligible
    }
    projections = []
    for ev in events:
        own = set(ev.get("tickers") or [])
        own_date = ev.get("date") or ""
        own_themes = [_theme_key(t) for t in (ev.get("themes") or []) if _theme_key(t)]
        refused_themes = sorted({t for t in own_themes if t not in eligible})

        # ticker -> set of supporting (prior, on-or-before-date) event ids
        support: dict[str, set[str]] = {}
        for theme in own_themes:
            if theme not in eligible:
                continue
            for date, tickers, src_id in by_theme.get(theme, ()):
                if not src_id:
                    continue
                if date > own_date:
                    continue
                if src_id == ev.get("id"):
                    continue
                for t in tickers:
                    if t in own:
                        continue
                    support.setdefault(t, set()).add(src_id)

        candidates = [
            (t, sorted(ids)) for t, ids in support.items()
            if len(ids) >= SECOND_ORDER_MIN_SUPPORT
        ]
        # Deterministic order by ticker name only -- NEVER by support count.
        # Sorting here is for stable output, not selection: when over the
        # ceiling we refuse the whole set rather than taking a prefix.
        candidates.sort(key=lambda pair: pair[0])
        candidate_count = len(candidates)

        if candidate_count > SECOND_ORDER_MAX_PER_EVENT:
            second_order: list[str] = []
            second_order_sources: dict[str, list[str]] = {}
            truncated = True
            truncated_reason = SECOND_ORDER_AMBIGUOUS_REASON
            dropped_count = candidate_count
        else:
            second_order = [t for t, _ in candidates]
            second_order_sources = {t: ids for t, ids in candidates}
            truncated = False
            truncated_reason = None
            dropped_count = 0

        proj = project_event_impact(
            ev, second_order_tickers=second_order,
            second_order_sources=second_order_sources,
        )
        proj["second_order_truncated"] = truncated
        proj["second_order_truncated_reason"] = truncated_reason
        proj["second_order_candidate_count"] = candidate_count
        proj["second_order_dropped_count"] = dropped_count
        if refused_themes:
            proj["second_order_theme_refused"] = refused_themes
            proj["second_order_theme_refused_reason"] = SECOND_ORDER_THEME_TOO_BROAD_REASON
        else:
            proj["second_order_theme_refused"] = []
            proj["second_order_theme_refused_reason"] = None
        projections.append(proj)
    return projections


def project_family_impact(
    events: list[dict], *, eligible_themes: set[str] | None = None,
) -> dict[str, list[dict]]:
    """Group projected impact by event family (``source``) -- the "consequence
    surface per event family" the ledger row's acceptance test names. Grouping
    only; the underlying event identity, dedup and correction lineage remain
    entirely spine.py's -- this never mutates or re-derives an event id.

    ``eligible_themes`` is forwarded to :func:`project_events_impact` so a
    windowed caller can apply corpus-level eligibility (same contract as the
    glance surface). When omitted, eligibility is computed from ``events``.
    """
    families: dict[str, list[dict]] = {}
    for proj in project_events_impact(events, eligible_themes=eligible_themes):
        families.setdefault(proj["source"] or "unknown", []).append(proj)
    return families


# Glance-tier outcome labels (ledger enums never reach the News panel).
# Shared wording with the Prophet closed-outcome map (T1_HIT / EXPIRED / …).
_PROPHET_OUTCOME_PLAIN: dict[str, tuple[str, str]] = {
    "T1_HIT": ("hit first target", "达到首个目标"),
    "T2_HIT": ("hit second target", "达到第二个目标"),
    "T3_HIT": ("hit final target", "达到最终目标"),
    "EXPIRED": ("timed out", "到期未达标"),
    "INVALIDATED": ("stopped out", "止损离场"),
}

_SIDE_PLAIN: dict[str, tuple[str, str]] = {
    "BULL": ("bullish plan", "偏多计划"),
    "BEAR": ("bearish plan", "偏空计划"),
}

# Common regime / risk-band tokens → plain-word EN/ZH glance glosses.
# Identity fallback is forbidden: Goldilocks/Growth-scare must never print as
# machine state names, and 金发女孩 is a meaningless ZH transliteration.
_STATE_PLAIN: dict[str, tuple[str, str]] = {
    "stagflation": ("stagflation", "滞胀"),
    "reflation": ("reflation", "再通胀"),
    "goldilocks": ("mild growth with low inflation", "温和增长、低通胀"),
    "growth-scare": ("a growth scare", "增长担忧"),
    "growth scare": ("a growth scare", "增长担忧"),
    "deflation": ("deflation", "通缩"),
    "calm": ("calm", "平静"),
    "watch": ("watch", "关注"),
    "caution": ("caution", "警惕"),
    "alarm": ("alarm", "警报"),
}

_REGION_PLAIN: dict[str, tuple[str, str]] = {
    "canada": ("Canada", "加拿大"),
    "hk": ("Hong Kong", "香港"),
    "us": ("US", "美国"),
    "usa": ("US", "美国"),
    "china": ("China", "中国"),
}

# Macro-print series → (en_label, zh_label, unit). Unmapped series fall back
# to a family-level sentence — never a raw slug on either locale.
_MACRO_SERIES: dict[str, tuple[str, str, str]] = {
    "claims": ("Weekly jobless claims", "每周初请失业金人数", "k"),
    "cpi_headline": ("Headline CPI", "整体CPI", "%"),
    "cpi_core": ("Core CPI", "核心CPI", "%"),
    "ppi_finaldemand": ("Producer prices (final demand)", "PPI最终需求", "%"),
    "pce_headline": ("Headline PCE", "整体PCE", "%"),
    "pce_core": ("Core PCE", "核心PCE", "%"),
    "nfp": ("Payrolls", "非农就业", "k"),
}

# Research-vault theme tags → glance subject. Unmapped tags are not printed
# as slugs; ticker-less rows without a derivable subject are dropped.
_THEME_GLANCE: dict[str, tuple[str, str]] = {
    "earnings": ("Earnings", "业绩"),
    "china_property": ("China property", "中国房地产"),
    "china property": ("China property", "中国房地产"),
    "ai_capex": ("AI spending", "人工智能开支"),
    "narrow_supply": ("Supply tightness", "供给偏紧"),
}


def _parse_event_date(raw: object) -> date | None:
    """Parse a ledger date (YYYY-MM-DD prefix). None when absent or unparseable."""
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None


def _plain_event_date(raw: object) -> tuple[str | None, str | None]:
    """Glance date pair: EN '7 Sep 2026' / ZH '2026年9月7日'. Never raw ISO."""
    parsed = _parse_event_date(raw)
    if parsed is None:
        return None, None
    en = f"{parsed.day} {_MONTH_EN[parsed.month - 1]} {parsed.year}"
    zh = f"{parsed.year}年{parsed.month}月{parsed.day}日"
    return en, zh


def _as_of_event_date(events: list[dict]) -> date | None:
    """Newest parseable event date in the input — as-of for the 7-day window.

    Render path has no wall-clock; the ledger's own newest date is the as-of.
    """
    dates = [d for ev in events if (d := _parse_event_date(ev.get("date")))]
    return max(dates) if dates else None


def _select_glance_pool(events: list[dict]) -> tuple[list[dict], str]:
    """Events in the last 7 days as-of the newest dated event, else newest 200."""
    as_of = _as_of_event_date(events)
    if as_of is not None:
        cutoff = as_of - timedelta(days=GLANCE_WINDOW_DAYS)
        window = [
            ev for ev in events
            if (d := _parse_event_date(ev.get("date"))) is not None and d >= cutoff
        ]
        if window:
            return window, GLANCE_WINDOW_LAST_7
    newest = sorted(
        events,
        key=lambda e: (e.get("date") or "", e.get("id") or ""),
        reverse=True,
    )
    return newest[:GLANCE_FALLBACK_LIMIT], GLANCE_WINDOW_FALLBACK


def _plain_window_span(start: date, end: date) -> tuple[str, str]:
    """EN 'Events from 31 Aug to 7 Sep 2026' / ZH '2026年8月31日至9月7日的事件'."""
    if start.year == end.year:
        en = (
            f"Events from {start.day} {_MONTH_EN[start.month - 1]} "
            f"to {end.day} {_MONTH_EN[end.month - 1]} {end.year}"
        )
        zh = (
            f"{start.year}年{start.month}月{start.day}日"
            f"至{end.month}月{end.day}日的事件"
        )
    else:
        en = (
            f"Events from {start.day} {_MONTH_EN[start.month - 1]} {start.year} "
            f"to {end.day} {_MONTH_EN[end.month - 1]} {end.year}"
        )
        zh = (
            f"{start.year}年{start.month}月{start.day}日"
            f"至{end.year}年{end.month}月{end.day}日的事件"
        )
    return en, zh


def _glance_window_labels(
    events: list[dict], window_mode: str | None,
) -> tuple[str | None, str | None]:
    """Section header for the glance window. Corpus as-of, never wall-clock."""
    if window_mode == GLANCE_WINDOW_FALLBACK:
        return WINDOW_FALLBACK_LABEL_EN, WINDOW_FALLBACK_LABEL_ZH
    as_of = _as_of_event_date(events)
    if as_of is None:
        if window_mode:
            return WINDOW_FALLBACK_LABEL_EN, WINDOW_FALLBACK_LABEL_ZH
        return None, None
    cutoff = as_of - timedelta(days=GLANCE_WINDOW_DAYS)
    return _plain_window_span(cutoff, as_of)


def _glance_series_key(family: str, raw_title: str, event_id: str) -> str | None:
    """Stable series identity for in-window flip collapse. None = do not collapse."""
    if family == "regime_flip":
        m = _REGIME_FLIP_RE.match(raw_title or "")
        if m:
            return f"regime_flip:{m.group(1).strip().lower()}"
        return f"regime_flip:{event_id or raw_title}"
    if family == "risk_band":
        return "risk_band:radar"
    return None


def _collapse_flip_series(rows: list[dict]) -> list[dict]:
    """Keep one row per regime/risk series; tag 2+ flips as unstable."""
    groups: dict[str, list[dict]] = {}
    passthrough: list[dict] = []
    for row in rows:
        key = _glance_series_key(
            row.get("family") or "",
            row.get("title") or "",
            row.get("event_id") or "",
        )
        if key is None:
            passthrough.append(row)
            continue
        groups.setdefault(key, []).append(row)
    out = list(passthrough)
    for members in groups.values():
        members.sort(
            key=lambda r: (r.get("event_time") or "", r.get("event_id") or ""),
            reverse=True,
        )
        latest = members[0]
        if len(members) >= 2:
            latest = dict(latest)
            latest["note_en"] = FLIP_UNSTABLE_EN
            latest["note_zh"] = FLIP_UNSTABLE_ZH
        out.append(latest)
    return out


def _plain_state(token: str) -> tuple[str, str]:
    key = (token or "").strip().lower()
    mapped = _STATE_PLAIN.get(key)
    if mapped:
        return mapped
    # Unmapped token: typed pair in both locales — never echo English into ZH.
    return ("a named macro state", "某一宏观状态")


def _plain_region(token: str) -> tuple[str, str]:
    raw = (token or "").strip()
    mapped = _REGION_PLAIN.get(raw.lower())
    if mapped:
        return mapped
    titled = raw.title() or "Market"
    return (titled, titled)


def _zh_state(token: str) -> str:
    return _plain_state(token)[1]


def _zh_region(token: str) -> str:
    return _plain_region(token)[1]


def _zh_detail(detail: str | None) -> str:
    """Translate common '+X% in Nd' ledger detail fragments for ZH glance."""
    if not detail:
        return ""
    m = re.match(r"^([+\-]?\d+(?:\.\d+)?%)\s+in\s+(\d+)d$", detail.strip(), re.IGNORECASE)
    if m:
        return f"（{m.group(2)}日内{m.group(1)}）"
    return f"（{detail}）"

# Strip ledger quarter prefixes from regime state tokens for glance copy.
_QUARTER_PREFIX_RE = re.compile(r"^Q[1-4]\s+", re.IGNORECASE)
_ARROW = r"(?:→|->)"
_PROPHET_CLOSE_RE = re.compile(
    rf"^Prophet close:\s*([A-Z0-9.\-]+)\s+(BULL|BEAR)\s*{_ARROW}\s*([A-Z0-9_]+)"
    r"(?:\s*\(([^)]+)\))?\s*$",
    re.IGNORECASE,
)
_REGIME_FLIP_RE = re.compile(
    rf"^([A-Za-z][A-Za-z /-]*)\s+regime:\s*(.+?)\s*{_ARROW}\s*(.+?)\s*$",
    re.IGNORECASE,
)
_RISK_BAND_RE = re.compile(
    rf"^Risk radar:\s*(.+?)\s*{_ARROW}\s*(.+?)\s*$",
    re.IGNORECASE,
)

_EARNINGS_RE = re.compile(r"^Earnings:\s*(\S+)\s+actual vs est\s*$", re.IGNORECASE)
_EARNINGS_CALL_RE = re.compile(
    r"^Earnings call:\s*(\S+)\s+(Q\d\s+FY\d+)\s*\u2014\s*(.+?)\s*$", re.IGNORECASE
)
_MACRO_PRINT_RE = re.compile(
    r"^Macro print:\s*([A-Za-z0-9_.]+)\s*=\s*([+-]?[\d.]+)\s*\(([\d-]+)\)\s*$",
    re.IGNORECASE,
)
_EARNINGS_TONE_ZH = {
    "cautious": "谨慎", "mixed": "中性", "positive": "积极",
    "negative": "偏弱", "upbeat": "乐观", "bearish": "看空",
    "bullish": "看多", "weak": "疲软", "strong": "强劲",
    "neutral": "中性",
    "confident": "有信心", "guarded": "偏谨慎", "steady": "稳健",
    "defensive": "偏防守", "downbeat": "偏弱", "reassuring": "安抚市场",
}
_ENUM_LEAK_RE = re.compile(r"\b(T[123]_HIT|INVALIDATED|EXPIRED|BULL|BEAR)\b")


def _sanitize(en: str, zh: str, *, fallback_en: str, fallback_zh: str) -> tuple[str, str]:
    """Single exit-point guard: no raw ledger enum reaches the glance surface,
    regardless of which family branch produced the strings (MAJOR 2)."""
    if _ENUM_LEAK_RE.search(en or "") or _ENUM_LEAK_RE.search(zh or ""):
        return fallback_en, fallback_zh
    return en, zh


def _strip_quarter_prefix(token: str) -> str:
    return _QUARTER_PREFIX_RE.sub("", (token or "").strip()) or (token or "").strip()


def _research_vault_subject(proj: dict) -> tuple[str, str] | None:
    """Plain-word subject for a ticker-less research note, or None.

    Prefers a mapped theme tag; otherwise the house/analyst prefix already
    on the spine title (``{institution}: {raw_title}``). A raw unmapped
    slug is not a subject — the glance caller drops the card.
    """
    for theme in proj.get("themes") or []:
        key = _theme_key(theme)
        mapped = _THEME_GLANCE.get(key)
        if mapped:
            return mapped
    raw = (proj.get("title") or "").strip()
    if ":" in raw:
        house = raw.split(":", 1)[0].strip()
        if house and len(house) <= 40 and " " not in house[:1]:
            # Proper-name house code (GS, JPM, S&T) is bilingual as-is.
            if house.lower() not in {"untitled", "report", "note"}:
                return (house, house)
    return None


def plain_glance_titles(proj: dict) -> tuple[str, str]:
    """EN/ZH plain-word glance titles for the News consequence panel.

    Spine event titles are ledger-facing (``T1_HIT``, ``Prophet close:``,
    ``Q3 Stagflation``). Glance surfaces may not print those raw forms —
    front-end clarity law. Falls back to a family-level plain label when the
    title cannot be parsed; never invents a market signal.
    """
    raw = (proj.get("title") or "").strip()
    source = (proj.get("source") or "").strip()
    direct = [
        e["ticker"] for e in (proj.get("exposures") or [])
        if e.get("materiality") == MATERIALITY_DIRECT and e.get("ticker")
    ]

    fallback = ("Chronicle event", "大事记事件")

    m = _PROPHET_CLOSE_RE.match(raw)
    if m or source == "prophet_ledger":
        if m:
            ticker, side, outcome, detail = m.group(1), m.group(2).upper(), m.group(3).upper(), m.group(4)
        else:
            ticker = direct[0] if direct else ""
            side, outcome, detail = "", "", None
        side_en, side_zh = _SIDE_PLAIN.get(side, ("plan", "计划"))
        out_en, out_zh = _PROPHET_OUTCOME_PLAIN.get(
            outcome, ("closed", "已结")
        )
        who = ticker or "Named name"
        detail_en = f" ({detail})" if detail else ""
        detail_zh = _zh_detail(detail)
        en = f"{who} {side_en} closed · {out_en}{detail_en}"
        zh = f"{who}{side_zh}已结·{out_zh}{detail_zh}"
        return _sanitize(en, zh, fallback_en=fallback[0], fallback_zh=fallback[1])

    m = _REGIME_FLIP_RE.match(raw)
    if m or source == "regime_flip":
        if not m:
            # Unparsed regime title: typed pair, never English placeholders in ZH.
            return _sanitize(
                "A regional macro backdrop changed",
                "某一地区宏观环境发生变化",
                fallback_en=fallback[0], fallback_zh=fallback[1],
            )
        region, frm, to = m.group(1).strip(), m.group(2), m.group(3)
        frm_p, to_p = _strip_quarter_prefix(frm), _strip_quarter_prefix(to)
        region_en, region_zh = _plain_region(region)
        frm_en, frm_zh = _plain_state(frm_p)
        to_en, to_zh = _plain_state(to_p)
        en = f"{region_en}'s macro backdrop turned from {frm_en} to {to_en}"
        zh = f"{region_zh}宏观环境由{frm_zh}转向{to_zh}"
        return _sanitize(en, zh, fallback_en=fallback[0], fallback_zh=fallback[1])

    m = _RISK_BAND_RE.match(raw)
    if m or source == "risk_band":
        if not m:
            return _sanitize(
                "Risk radar changed \u2014 stay selective",
                "风险雷达已变化——保持谨慎选择",
                fallback_en=fallback[0], fallback_zh=fallback[1],
            )
        frm, to = m.group(1).strip(), m.group(2).strip()
        frm_en, frm_zh = _plain_state(frm)
        to_en, to_zh = _plain_state(to)
        en = f"Risk radar moved from {frm_en} to {to_en} \u2014 stay selective"
        zh = f"风险雷达由{frm_zh}转为{to_zh}——保持谨慎选择"
        return _sanitize(en, zh, fallback_en=fallback[0], fallback_zh=fallback[1])

    if source == "macro_release":
        # Plain-word series label + unit. Unmapped slugs fall back to the
        # family sentence rather than printing `ppi_finaldemand` / `claims`.
        mp = _MACRO_PRINT_RE.match(raw)
        if mp:
            series, value = mp.group(1), mp.group(2)
            mapped = _MACRO_SERIES.get((series or "").strip().lower())
            if mapped:
                label_en, label_zh, unit = mapped
                shown = value if (not unit or str(value).endswith(unit)) else f"{value}{unit}"
                en = f"{label_en} came in at {shown}"
                zh = f"{label_zh}公布为{shown}"
            else:
                en, zh = "Macro data release", "宏观数据发布"
        else:
            en, zh = "Macro data release", "宏观数据发布"
        return _sanitize(
            en, zh,
            fallback_en="Macro data release", fallback_zh="宏观数据发布",
        )

    if source == "earnings":
        # BLOCKER 1(a): never echo `raw` as title_zh — real corpus rows
        # always carry `raw`, so this branch used to render untranslated
        # English on the ZH glance panel for 5,548 of 11,025 events (98.8%
        # combined with earnings_call/research_vault).
        who = direct[0] if direct else "Named name"
        en = f"{who} reported earnings"
        zh = f"{who}公布业绩"
        return _sanitize(
            en, zh,
            fallback_en="Earnings event", fallback_zh="业绩事件",
        )

    if source == "earnings_call":
        # Mapped tones print in both locales. An unmapped adapter token
        # (or a missing tone) emits the tone-free pair — never a ZH 中性
        # default that contradicts the EN surface.
        mc = _EARNINGS_CALL_RE.match(raw)
        ticker = mc.group(1) if mc else (direct[0] if direct else "Named name")
        tone_raw = (mc.group(3) if mc else "").strip().lower()
        tone_zh = _EARNINGS_TONE_ZH.get(tone_raw) if tone_raw else None
        if tone_raw and tone_zh:
            en = f"{ticker} earnings call — {tone_raw} tone"
            zh = f"{ticker}业绩电话会——基调{tone_zh}"
        else:
            en = f"{ticker} earnings call"
            zh = f"{ticker}业绩电话会"
        return _sanitize(
            en, zh,
            fallback_en="Earnings call", fallback_zh="业绩电话会",
        )

    if source == "research_vault":
        who = direct[0] if direct else None
        if who:
            en, zh = f"Research note on {who}", f"关于{who}的研究纪要"
        else:
            subject = _research_vault_subject(proj)
            if subject:
                en, zh = f"Research note — {subject[0]}", f"研究纪要——{subject[1]}"
            else:
                return ("", "")
        return _sanitize(
            en, zh,
            fallback_en="Research note", fallback_zh="研究纪要",
        )

    # Unknown family: typed pair in both locales — never the raw ledger title.
    return _sanitize(
        "Market event", "市场事件",
        fallback_en=fallback[0], fallback_zh=fallback[1],
    )


def glance_consequence_surface(
    events: list[dict],
    *,
    limit: int = GLANCE_ROW_CAP,
) -> dict:
    """Bounded, plain-word consequence surface for the News Feed panel.

    A glance row must belong to a public market-event family (earnings,
    earnings_call, macro_release, regime/risk shifts, or research_vault)
    and carry at least one direct or second-order ticker. There is no
    family exemption — rows without a named exposure never render.
    ``prophet_ledger`` is a typed exclusion — those rows are the product's
    own trade ledger, not market events, and never appear on the anonymous
    News glance.

    Window: events dated within 7 days of the newest parseable event date in
    the input (no wall-clock). If that window is empty — the corpus is undated
    or no event carries a parseable date — fall back to the newest 200
    events. From the chosen pool, keep every qualifying row up to ``limit``
    (default 8). The typed empty state prints only when ZERO rows qualify.

    The section header carries the window's actual dates from the corpus
    as-of (``window_label_en`` / ``window_label_zh``), or the fallback label
    when the newest-200 path fires.

    Calibrated impact stays null + reason. Size is not part of this
    surface — the glance names exposures only. Empty / missing input
    prints an honest null state rather than fabricating rows. Row titles are
    dual-locale plain-word (``title_en`` / ``title_zh``); the raw spine
    ``title`` is kept for diagnostics only and must not be rendered on the
    glance surface. A regime/risk series that flipped twice or more in the
    window collapses to its latest row and carries ``note_en`` / ``note_zh``.
    """
    if not events:
        return {
            "served_as_market_feed": False,
            "market_feed_disposition": "explicitly_does_not_serve_market_feed",
            "stance_en": "Not available yet",
            "stance_zh": "暂不可用",
            "reason_en": "No chronicle events in this window yet.",
            "reason_zh": "此窗口尚无大事记事件。",
            "empty_kind": None,
            "window_mode": None,
            "window_label_en": None,
            "window_label_zh": None,
            "families": {},
            "rows": [],
            "event_count": 0,
        }

    pool, window_mode = _select_glance_pool(events)
    label_en, label_zh = _glance_window_labels(events, window_mode)
    # Chronological order for projection (point-in-time second-order).
    window = sorted(
        pool,
        key=lambda e: (e.get("date") or "", e.get("id") or ""),
    )
    # Eligibility over the FULL corpus; one projection feeds both family
    # counts and glance rows (MINOR 1 — do not re-project the window with
    # a different eligibility set).
    eligible_themes = _eligible_themes(events)
    projections = project_events_impact(window, eligible_themes=eligible_themes)
    rows = []
    for proj in projections:
        family = (proj.get("source") or "").strip()
        if family in GLANCE_EXCLUDED_FAMILIES:
            continue
        if family not in GLANCE_ELIGIBLE_FAMILIES:
            continue
        direct = [e["ticker"] for e in proj["exposures"] if e.get("materiality") == MATERIALITY_DIRECT]
        second = [e["ticker"] for e in proj["exposures"] if e.get("materiality") == MATERIALITY_SECOND_ORDER]
        if not direct and not second:
            continue
        title_en, title_zh = plain_glance_titles(proj)
        if not title_en or not title_zh:
            continue
        time_en, time_zh = _plain_event_date(proj["event_time"])
        rows.append({
            "event_id": proj["event_id"],
            "event_time": proj["event_time"],
            "event_time_en": time_en,
            "event_time_zh": time_zh,
            "known_at": proj["known_at"],
            "family": family or "unknown",
            "title": proj.get("title") or "",  # raw spine title — diagnostics only
            "title_en": title_en,
            "title_zh": title_zh,
            "direct_tickers": direct,
            "second_order_tickers": second,
            "second_order_truncated": bool(proj.get("second_order_truncated")),
            "second_order_candidate_count": proj.get("second_order_candidate_count", 0),
            "second_order_dropped_count": proj.get("second_order_dropped_count", 0),
            "note_en": None,
            "note_zh": None,
            "calibrated_impact": None,
            "calibrated_impact_reason": CALIBRATED_IMPACT_GATE_REASON,
            "causal_label": CAUSAL_LABEL,
        })
    # Collapse a regime/risk series that flipped both ways in this window,
    # then newest-first, cap at the row limit.
    rows = _collapse_flip_series(rows)
    rows.sort(key=lambda r: (r.get("event_time") or "", r.get("event_id") or ""), reverse=True)
    cap = max(1, int(limit))
    rows = rows[:cap]
    families: dict[str, int] = {}
    for row in rows:
        families[row["family"]] = families.get(row["family"], 0) + 1

    if not rows:
        return {
            "served_as_market_feed": False,
            "market_feed_disposition": "explicitly_does_not_serve_market_feed",
            "stance_en": None,
            "stance_zh": None,
            "reason_en": EMPTY_NO_EXPOSURE_EN,
            "reason_zh": EMPTY_NO_EXPOSURE_ZH,
            "empty_kind": "no_named_exposure",
            "window_mode": window_mode,
            "window_label_en": label_en,
            "window_label_zh": label_zh,
            "families": {},
            "rows": [],
            "event_count": len(window),
        }

    return {
        "served_as_market_feed": False,
        "market_feed_disposition": "explicitly_does_not_serve_market_feed",
        "stance_en": GLANCE_STANCE_EN,
        "stance_zh": GLANCE_STANCE_ZH,
        "reason_en": None,
        "reason_zh": None,
        "empty_kind": None,
        "window_mode": window_mode,
        "window_label_en": label_en,
        "window_label_zh": label_zh,
        "families": families,
        "rows": rows,
        "event_count": len(window),
    }

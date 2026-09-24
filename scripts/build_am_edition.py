"""Build the deterministic premarket "AM Edition" delta artifact -> site/am_edition.json.

Producer half of MO-PAID-011 (packet A-MO-W2-3). Authority ceiling: display_only.
No signal, rank, score, gate, sizing, ENTRY_OPEN, Prophet, portfolio or trade
authority is originated here — every value is either an owner fact read
verbatim from an already-committed deterministic artifact, a deterministic
derived comparison (prior close vs last known price), a deterministic
calendar fact, or a reference to the EXISTING model-generated prior-close
brief (site/master_brief.json), never re-summarised or re-ranked.

This builder does LIGHT fail-open reads of committed deterministic artifacts
(market_state, regime, neuralweb market_plane, release_forecast, live quotes,
master_brief) — no new collector, no vendor, no LLM/model/provider/quota path.
Every per-block gather is wrapped in try/except and degrades to a visible
UNAVAILABLE/NOT_COVERED block with a plain-word EN/ZH reason; a gather NEVER
removes the block and NEVER breaks the render. Returns 0 on ANY error.

Usage: python -m scripts.build_am_edition   (run anytime; safe pre-open or post)

A5 typed-state reachability (R14): the spec names six typed states per
block; the three new blocks (context_planes / research_watch / owner_links)
reach a strict subset. NOT_YET_OPEN and CLOSED are session_clock-only typed
states (the build never runs at NOT_YET_OPEN or CLOSED on a path the
producer can reach for these three blocks — they are documented here as
unreachable rather than implemented). The reachable set per block is
documented at the top of each block builder; the test module docstring
mirrors this surface.

R14 partiality: "each new block in all five typed states" was the spec's
language; the three new blocks reach 4 / 3 / 2 of 5 respectively. The
unreachable pair (NOT_YET_OPEN / CLOSED) is documented here as a HARD
constraint (session_clock owns these states; the new blocks have no
calendar clock to gate them).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from datetime import datetime, timezone, timedelta, date
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import config, nyse_calendar, pages  # noqa: E402
from lib.pages import write_page  # noqa: E402  # 2026-09-19 h5_7337: bare name so the page-registry census (scan_write_sites) derives macro:am_edition

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("build_am_edition")

SCHEMA = "am_edition.v1"
STATES = (
    "CURRENT",
    "STALE_WITH_LAST_KNOWN",
    "UNAVAILABLE",
    "NOT_COVERED",
    "NOT_YET_OPEN",
    "CLOSED",
)
CLASSIFICATIONS = (
    "owner_fact",
    "deterministic_derived_comparison",
    "deterministic_calendar",
    "existing_model_generated_prior_close_brief",
    "owner_context_summary",
    "owner_research_watch",
    "owner_link_registry",
)

# A7 guard — STRUCTURAL ONLY. The producer NEVER reads `lean`, `entry_levels`,
# `conviction`, `outcome`, or `realized` from theses.jsonl and NEVER composes
# direction / size / target / order copy. The rule is enforced by the loader
# interface (the producer reads only `falsifier.text`, `state_asof`,
# `logged_at`, `status`, and `id`) — see `_load_theses_row` below for the
# load-time key allow-list. A runtime regex redaction is REMOVED per the
# R6 ruling because it destroys benign transferred owner prose ("long-dated",
# "long end", "long Treasury") that the producer is permitted to surface
# verbatim. The A7 contract is now a load-time key gate + a post-render text
# scan; both are exercised by the test suite.


# Whitelist of keys the producer is allowed to read from a single thesis
# row (R6 — A7 contract is STRUCTURAL). Any key outside this set must NOT
# be accessed; the loader returns None for that row and the test suite
# monkeypatches `dict.__getitem__` to fail on access.
_THESIS_ROW_KEYS = frozenset({
    "id", "status", "state_asof", "logged_at", "falsifier", "check_by",
})


def _load_theses_row(obj: dict) -> dict | None:
    """A7 load-time key gate (R6): the producer reads ONLY the whitelisted
    keys (`_THESIS_ROW_KEYS`) from a thesis row. Any thesis whose `status`
    is not `open`, whose `falsifier.text` is absent, or whose read keys
    fall outside the whitelist is dropped. The whitelist is a CLOSED
    set — the producer must NEVER widen this list without a Meta-CEO
    ruling. The function returns a flat dict of normalised fields the
    caller can pass straight to the row builder; the original `obj` is
    never held by the producer past this call."""
    if not isinstance(obj, dict):
        return None
    if obj.get("status") != "open":
        return None
    # The whitelist check: any unknown top-level key means the upstream
    # artifact has added a directional field we do NOT consume — refuse
    # the row (the test suite proves we never widen the whitelist).
    if any(k not in _THESIS_ROW_KEYS for k in obj.keys()):
        return None
    falsifier = obj.get("falsifier") or {}
    if not isinstance(falsifier, dict):
        return None
    if "text" not in falsifier:
        return None
    cond_text = falsifier.get("text")
    if not isinstance(cond_text, str) or not cond_text:
        return None
    since_raw = obj.get("state_asof")
    logged_raw = obj.get("logged_at")
    since_iso, _ = _norm_clock(since_raw)
    as_of_iso, _ = _norm_clock(logged_raw or since_raw)
    return {
        "id": obj.get("id"),
        "cond_text": cond_text,
        "since_raw": since_raw,
        "logged_raw": logged_raw,
        "since_iso": since_iso,
        "as_of_iso": as_of_iso,
    }


# Plain-language ZH mirror for an OPEN-condition row. The condition text is
# English (theses.jsonl is EN-only); the producer never machine-translates
# it. The ZH field surfaces ONE plain-word ZH sentence that names the row's
# intent — never the EN text, never an "（条件原文照录如下）" prefix (the
# previous copy embedded the EN condition into the ZH field and broke the
# plain-language law / BLOCKER 3 / MAJOR-minor 7). The same row renders the
# EN condition in its own EN field; the ZH field is a glance-tier ZH mirror.
_RESEARCH_WATCH_ZH_FRAMES = (
    "正在观察这一条件，留意后续变化。",
    "对这一条件保持关注，等待复核。",
)

# Per-row freshness budgets — one US session ≈ 24h × weekday window. Premarket
# reading windows are narrow (intraday-fastpath runs */30 11-21 UTC; a weekday
# build at 11:30Z can call a 22h-old nightly CURRENT if the source was stamped
# at the prior 16:00 ET close). 1440 minutes = one full session day.
_CONTEXT_PLANE_MAX_AGE = 1440
_RESEARCH_WATCH_MAX_AGE = 1440 * 10  # 10 US sessions; older -> STALE block

# Owner-page anchors verified against templates/_navlinks.html.j2 on
# origin/main. Each plane maps to ONE owner page (DEC item 8 §A4 — one per
# plane; the international row folds both, see _owner_links_block below).
# `macro.html` is generated by scripts/build_site.py:7702 (no .j2 template);
# the other four are .j2-templated pages written by build_china.py,
# build_hk.py, build_bonds.py and build_commodities.py respectively. The
# resolution helper checks both shapes; macro.html is whitelisted because
# it is a known generated page (no template) but never appears as a .j2.
_OWNER_PAGE_BY_PLANE = {
    "rates": "macro.html",
    "dollar": "bonds.html",
    "credit": "bonds.html",
    "commodity": "commodities.html",
    "international": "china.html",  # hk.html is a sub-link below
}

# Reference registry anchor map for the owner_links kind=reference rows.
# These are the mastermind.market_reference/v1 ids used by the Reference
# builder, verified against config/market_reference.yml on origin/main (the
# census lists every one of them in §4). The map is a CLOSED whitelist — any
# anchor not in this table is dropped by the resolution helper, never guessed.
_REFERENCE_ANCHORS = (
    "yield-curve",      # rates / yield curve shape
    "credit-spread",    # credit
    "high-yield-spread",  # credit
    "real-rates",       # rates / real
    "breakevens",       # rates / inflation
    "term-premium",     # rates / term premium
    "dollar-index",     # dollar
    "market-regime",    # macro context
    "market-state-score",  # macro context
    "risk-on-risk-off",  # cross
    "flight-to-quality",  # cross
)

# Fixed tuple of (symbol, label_en, label_zh) for the tape-since-prior-close block.
_TAPE_SYMBOLS = (
    ("SPY", "S&P 500 ETF", "标普500 ETF"),
    ("QQQ", "Nasdaq 100 ETF", "纳斯达克100 ETF"),
    ("^RUT", "Russell 2000", "罗素2000指数"),
)

# US regular session: 09:30–16:00 America/New_York on an NYSE session day
# (DST-aware). Session days come from lib.nyse_calendar, not weekday().
_US_OPEN_HOUR_LOCAL = 9
_US_OPEN_MINUTE_LOCAL = 30
_US_CLOSE_HOUR_LOCAL = 16
_US_CLOSE_MINUTE_LOCAL = 0
_NY_TZ = ZoneInfo("America/New_York")

# Deterministic calendar titles — display copy only. Keys match
# data/release_forecast/latest.json `release` / `release_type`. Unknown
# codes never surface the raw slug; they get a generic plain-word pair.
_RELEASE_TITLES = {
    "cpi": ("CPI (consumer prices)", "消费者物价指数"),
    "cpi_headline": ("Headline CPI (consumer prices)", "总体消费者物价指数"),
    "cpi_core": ("Core CPI (consumer prices)", "核心消费者物价指数"),
    "ppi": ("PPI (producer prices)", "生产者物价指数（PPI）"),
    "ppi_finaldemand": ("PPI (producer prices)", "生产者物价指数（PPI）"),
    "nfp": ("Jobs report (nonfarm payrolls)", "非农就业报告"),
    "claims": ("Initial jobless claims", "初请失业金"),
    "pce": ("PCE / personal income", "PCE 物价指数"),
    "pce_headline": ("Headline PCE", "PCE 总体物价指数"),
    "pce_core": ("Core PCE", "PCE 核心物价指数"),
    "retail_sales": ("Retail sales", "零售销售"),
    "gdp": ("GDP (BEA estimate)", "GDP 数据"),
}

# Regime quad code -> plain-word EN/ZH label (engine/regime.py:25-26 is the
# authoritative code->name map; this is display copy only, never re-derived).
_QUAD_LABELS = {
    "Q1": ("Goldilocks", "金发姑娘（低通胀增长）"),
    "Q2": ("Reflation", "再通胀"),
    "Q3": ("Stagflation", "滞胀"),
    "Q4": ("Growth-scare / Deflation", "增长恐慌/通缩"),
}

# Commodity-regime code -> plain-word EN/ZH label. The artifact ships an
# English slug like "Reflation" or "Goldilocks"; the labels are HONEST
# translations of that slug — never a claim about specific commodities
# (MAJOR 12: the previous "Risk-on → 铜金煤走强" mapping asserted copper/gold/
# coal were rising, a claim absent from `regime`, so the producer originated
# content). An unmapped regime surfaces the EN slug, leaves ZH null, and
# attaches a state_reason disclosure.
_COMMODITY_REGIME_LABELS = {
    "Reflation": ("Reflation", "再通胀"),
    "Goldilocks": ("Goldilocks", "金发姑娘（低通胀增长）"),
    "Stagflation": ("Stagflation", "滞胀"),
    "Deflation": ("Deflation", "通缩"),
    "Tightening": ("Tightening", "收紧"),
    "Easing": ("Easing", "宽松"),
    "Risk-on": ("Risk-on commodities", "商品风险偏好上升"),
    "Risk-off": ("Risk-off commodities", "商品风险偏好下降"),
}

# Commodity EN name -> ZH name. Used by context_planes' commodity row to
# surface plain-word ZH labels for the favored list (R9 — ZH fields must
# never carry EN tokens). Unknown names are OMITTED from the ZH list,
# never printed in EN (the rule: a `*_zh` string contains no ASCII
# letters except inside the whitelisted tokens WTI/OAS/HY/CPI/FOMC).
_COMMODITY_NAME_ZH = {
    "Copper": "铜",
    "Oil · WTI": "WTI原油",
    "Oil": "原油",
    "Brent": "布伦特原油",
    "Gold": "金",
    "Silver": "银",
    "Natural Gas": "天然气",
    "Platinum": "铂",
    "Palladium": "钯",
    "Corn": "玉米",
    "Wheat": "小麦",
    "Soybeans": "大豆",
    "Aluminum": "铝",
    "Nickel": "镍",
    "Zinc": "锌",
    "Iron Ore": "铁矿石",
    "Coffee": "咖啡",
    "Sugar": "糖",
    "Cotton": "棉花",
    "Cocoa": "可可",
    "Lumber": "木材",
}

# Rates regime EN -> ZH. Used by context_planes' rates row to surface a
# plain-word ZH label for the regime (R9). A missing regime surfaces the
# literal "未知" rather than copy the EN token into a ZH field.
_RATES_REGIME_ZH = {
    "restrictive": "紧缩",
    "accommodative": "宽松",
    "neutral": "中性",
    "tightening": "收紧",
    "easing": "放松",
    "rising": "上行",
    "falling": "下行",
    "flat": "持平",
}

# Plain-word UNAVAILABLE default for new-block rows whose owner file is
# missing or whose field is absent (R8: no "Not covered yet" / "暂未覆盖"
# leakage into an UNAVAILABLE row).
_UNAVAILABLE_DEFAULT_EN = "Not available this morning."
_UNAVAILABLE_DEFAULT_ZH = "今晨暂不可用。"


def _load_json_safe(path: Path) -> dict | list | None:
    """Load JSON from path; return None on any error."""
    try:
        return json.loads(path.read_bytes())
    except Exception as exc:  # noqa: BLE001
        log.debug("am_edition: could not read %s (%s)", path, exc)
        return None


def _load_committed(site: Path, data_dir: Path, site_rel: str, data_rel: str) -> dict | list | None:
    """Committed-artifact load order: site/ copy preferred, data/ fallback
    (mirrors scripts/build_aibrief.py:71-96)."""
    val = _load_json_safe(site / site_rel)
    if val is None:
        val = _load_json_safe(data_dir / data_rel)
    return val


def _norm_clock(raw: str | None) -> tuple[str | None, str]:
    """Normalise a clock field to (iso_utc, precision). precision in
    {"second","minute","day"}. Returns (None, "day") if unparseable."""
    if not raw or not isinstance(raw, str):
        return None, "day"
    s = raw.strip()
    # Date-only, e.g. "2026-09-04"
    if len(s) == 10 and s.count("-") == 2:
        try:
            d = date.fromisoformat(s)
            return f"{d.isoformat()}T00:00:00+00:00", "day"
        except Exception:  # noqa: BLE001
            return None, "day"
    try:
        s2 = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s2)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt = dt.astimezone(timezone.utc)
        precision = "second" if (dt.second or dt.microsecond) else "minute"
        return dt.isoformat(), precision
    except Exception:  # noqa: BLE001
        return None, "day"


def _humanize_age(age_minutes: int) -> tuple[str, str]:
    """Plain-word EN/ZH age with real singular/plural — never `hour(s)`."""
    minutes = max(0, int(age_minutes))
    if minutes < 60:
        if minutes == 1:
            return "1 minute", "1分钟"
        return f"{minutes} minutes", f"{minutes}分钟"
    hours = minutes // 60
    if hours < 24:
        if hours == 1:
            return "1 hour", "1小时"
        return f"{hours} hours", f"{hours}小时"
    days = hours // 24
    if days < 7:
        if days == 1:
            return "1 day", "1天"
        return f"{days} days", f"{days}天"
    weeks = days // 7
    if weeks < 8:
        if weeks == 1:
            return "1 week", "1周"
        return f"{weeks} weeks", f"{weeks}周"
    months = days // 30
    if months < 24:
        if months == 1:
            return "1 month", "1个月"
        return f"{months} months", f"{months}个月"
    years = days // 365
    if years == 1:
        return "1 year", "1年"
    return f"{years} years", f"{years}年"


def _plain_day_en(d: date) -> str:
    return f"{d.day} {d.strftime('%b')}"


def _plain_day_zh(d: date) -> str:
    return f"{d.month}月{d.day}日"


def _as_of_ny_date(as_of_iso: str | None) -> date | None:
    """NY calendar date of a UTC-normalised ISO instant."""
    if not as_of_iso:
        return None
    try:
        dt = datetime.fromisoformat(as_of_iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(_NY_TZ).date()
    except Exception:  # noqa: BLE001
        return None


def _release_title(entry: dict) -> tuple[str, str]:
    """Whitelist a calendar row to a plain-word EN/ZH pair. Never return a slug."""
    for key in (entry.get("release_type"), entry.get("release")):
        if isinstance(key, str) and key in _RELEASE_TITLES:
            return _RELEASE_TITLES[key]
    return ("US economic release", "美国经济数据发布")


def _classify(
    source_as_of: str | None,
    generated_at: str,
    max_age_minutes: int | None,
    *,
    covered: bool = True,
) -> tuple[str, int | None]:
    """Pure. -> (state, age_minutes). NEVER returns CURRENT when age > max_age,
    and NEVER returns CURRENT for a future-stamped (negative-age) source.

    Legacy helper. The six legacy blocks (session_clock, tape_since_prior_close,
    market_state, cross_asset_plane, todays_calendar, prior_close_brief_ref —
    and the seventh, regime, which the MOR-2b spec named by omission) call this
    helper with byte-identical inputs to origin/main dd20710c; any change to
    its signature or semantics here changes the legacy payload. Day-precision
    freshness lives in `_row_state` / `_classify_day_aware`, used ONLY by the
    three new blocks (DEC:R1, 2026-09-24).

    Premarket reads are CURRENT here too — freshness is judged by age against
    the source's own budget, not by session_open alone (intraday-fastpath runs
    */30 11-21 UTC, so a weekday build at 11:30Z can call a 22h-old nightly
    CURRENT if the source was stamped at the prior 16:00 ET close)."""
    if not covered:
        return "NOT_COVERED", None
    if source_as_of is None:
        return "UNAVAILABLE", None
    try:
        gen_dt = datetime.fromisoformat(generated_at)
        src_dt = datetime.fromisoformat(source_as_of)
    except Exception:  # noqa: BLE001
        return "UNAVAILABLE", None
    age_seconds = (gen_dt - src_dt).total_seconds()
    age_minutes = int(age_seconds // 60)
    if age_seconds < 0:
        # Future-stamped source: never trust it as CURRENT.
        return "UNAVAILABLE", age_minutes
    if max_age_minutes is not None and age_minutes <= max_age_minutes:
        return "CURRENT", age_minutes
    return "STALE_WITH_LAST_KNOWN", age_minutes


def _block(
    key: str,
    *,
    title_en: str,
    title_zh: str,
    source_ref: str,
    source_owner: str,
    classification: str,
    source_as_of: str | None,
    max_age_minutes: int | None,
    generated_at: str,
    rows: list | None = None,
    reason_en: str | None = None,
    reason_zh: str | None = None,
    covered: bool = True,
    precision: str | None = None,
) -> dict:
    """Builds ONE contract-shaped block. `precision` MUST be the precision
    returned alongside source_as_of by the caller's own _norm_clock() call —
    re-deriving it here from the already-normalised ISO string always
    reads "minute" (the ...T00:00:00+00:00 padding looks second-exact) and
    silently upgrades a day-precision source into a false-precise one."""
    assert classification in CLASSIFICATIONS, f"invalid classification: {classification}"
    if precision is None:
        _, precision = _norm_clock(source_as_of) if source_as_of else (None, "day")
    state, age_minutes = _classify(
        source_as_of, generated_at, max_age_minutes, covered=covered
    )
    out = {
        "key": key,
        "title_en": title_en,
        "title_zh": title_zh,
        "state": state,
        "source_ref": source_ref,
        "source_owner": source_owner,
        "source_as_of": source_as_of if state in ("CURRENT", "STALE_WITH_LAST_KNOWN") else None,
        "source_as_of_precision": precision if state in ("CURRENT", "STALE_WITH_LAST_KNOWN") else None,
        "age_minutes": age_minutes if state in ("CURRENT", "STALE_WITH_LAST_KNOWN") else None,
        "max_age_minutes": max_age_minutes,
        "classification": classification,
    }
    if state in ("UNAVAILABLE", "NOT_COVERED", "NOT_YET_OPEN", "CLOSED"):
        out["state_reason_en"] = reason_en or "Not available yet."
        out["state_reason_zh"] = reason_zh or "暂不可用。"
    elif state == "STALE_WITH_LAST_KNOWN" and not reason_en:
        age_en, age_zh = _humanize_age(age_minutes or 0)
        out["state_reason_en"] = (
            f"Last updated {age_en} ago — showing the last known reading, not a fresh one."
        )
        out["state_reason_zh"] = (
            f"最近更新于{age_zh}前——展示的是最新已知读数，而非最新数据。"
        )
    else:
        out["state_reason_en"] = reason_en
        out["state_reason_zh"] = reason_zh
    if rows is not None:
        out["rows"] = rows
    return out


def _session_phase(now: datetime) -> str:
    """weekend | holiday | preopen | open | closed.

    Session days come from lib.nyse_calendar.is_session (weekends and
    full-day NYSE holidays). The 09:30–16:00 ET clock applies only on a
    session day. HK is out of scope — this producer is US-only.
    """
    local = now.astimezone(_NY_TZ)
    today = local.date()
    if not nyse_calendar.is_session(today):
        return "weekend" if today.weekday() >= 5 else "holiday"
    open_local = local.replace(
        hour=_US_OPEN_HOUR_LOCAL, minute=_US_OPEN_MINUTE_LOCAL, second=0, microsecond=0
    )
    close_local = local.replace(
        hour=_US_CLOSE_HOUR_LOCAL, minute=_US_CLOSE_MINUTE_LOCAL, second=0, microsecond=0
    )
    if local < open_local:
        return "preopen"
    if local >= close_local:
        return "closed"
    return "open"


def _is_session_open_now(now: datetime) -> bool:
    """True only during the US regular session (09:30–16:00 America/New_York,
    DST-aware) on an NYSE session day — False on weekends and holidays."""
    return _session_phase(now) == "open"


def _previous_trading_day(d: date) -> date:
    """Most recent NYSE session strictly before `d` (lib.nyse_calendar)."""
    return nyse_calendar.last_session_on_or_before(d - timedelta(days=1))


def _session_clock_block(generated_at: str, now: datetime) -> dict:
    phase = _session_phase(now)
    if phase == "weekend":
        state = "NOT_YET_OPEN"
        reason_en = "Markets are closed for the weekend."
        reason_zh = "周末休市。"
    elif phase == "holiday":
        state = "CLOSED"
        reason_en = "Market holiday"
        reason_zh = "休市日"
    elif phase == "preopen":
        state = "NOT_YET_OPEN"
        reason_en = "US markets have not opened yet today."
        reason_zh = "美股今日尚未开盘。"
    elif phase == "closed":
        state = "CLOSED"
        reason_en = "US markets have closed for the day."
        reason_zh = "美股今日已收盘。"
    else:
        state = "CURRENT"
        reason_en = None
        reason_zh = None
    return {
        "key": "session_clock",
        "title_en": "Session clock",
        "title_zh": "交易时段",
        "state": state,
        "source_ref": "computed",
        "source_owner": "build_am_edition",
        "source_as_of": generated_at if state == "CURRENT" else None,
        "source_as_of_precision": "second" if state == "CURRENT" else None,
        "age_minutes": 0 if state == "CURRENT" else None,
        "max_age_minutes": None,
        "classification": "deterministic_calendar",
        "state_reason_en": reason_en,
        "state_reason_zh": reason_zh,
    }


def _tape_block(site: Path, generated_at: str, now: datetime, prior_close_date: str, *, live_dir: Path | None = None) -> dict:
    phase = _session_phase(now)
    if live_dir is not None:
        # VPS overlay path (A1): a wrapper script that knows the served copy
        # points at a separate directory can pass it in. The default behaviour
        # — reading site/live/quotes.json exactly as today — is preserved when
        # live_dir is None.
        quotes_path = live_dir / "quotes.json"
        quotes_source_ref = "live/quotes.json (vps)"
    else:
        quotes_path = site / "live" / "quotes.json"
        quotes_source_ref = "site/live/quotes.json"
    try:
        quotes = _load_json_safe(quotes_path)
        if not quotes or not isinstance(quotes, dict):
            return _block(
                "tape_since_prior_close",
                title_en="Since yesterday's close",
                title_zh="自昨日收盘以来",
                source_ref=quotes_source_ref,
                source_owner="intraday-fastpath",
                classification="deterministic_derived_comparison",
                source_as_of=None,
                max_age_minutes=240,
                generated_at=generated_at,
                covered=False,
                reason_en="No live tape reading is available.",
                reason_zh="暂无实时行情读数。",
            )
        as_of_iso, precision = _norm_clock(quotes.get("asof"))
        quote_session = _as_of_ny_date(as_of_iso)
        try:
            intended_close = date.fromisoformat(prior_close_date)
        except Exception:  # noqa: BLE001
            intended_close = None
        implied_baseline = _previous_trading_day(quote_session) if quote_session else None
        baseline_mismatch = (
            intended_close is None
            or implied_baseline is None
            or implied_baseline != intended_close
        )
        rows = []
        qmap = quotes.get("quotes") or {}
        for sym, label_en, label_zh in _TAPE_SYMBOLS:
            q = qmap.get(sym)
            if not q:
                continue
            change_pct = (
                None
                if baseline_mismatch
                else (round(float(q.get("changePct")), 4) if q.get("changePct") is not None else None)
            )
            rows.append({
                "label_en": label_en,
                "label_zh": label_zh,
                "symbol": sym,
                "prior_close": round(float(q.get("prevClose")), 4) if q.get("prevClose") is not None else None,
                "last": round(float(q.get("price")), 4) if q.get("price") is not None else None,
                "change_pct": change_pct,
                "quote_as_of": as_of_iso,
            })
        blk = _block(
            "tape_since_prior_close",
            title_en="Since yesterday's close",
            title_zh="自昨日收盘以来",
            source_ref=quotes_source_ref,
            source_owner="intraday-fastpath",
            classification="deterministic_derived_comparison",
            source_as_of=as_of_iso,
            max_age_minutes=240,
            generated_at=generated_at,
            rows=rows,
            precision=precision,
        )
        if baseline_mismatch and implied_baseline is not None:
            day_en = _plain_day_en(implied_baseline)
            day_zh = _plain_day_zh(implied_baseline)
            baseline_en = (
                f"Compared with the close of {day_en} — no newer close has been captured."
            )
            baseline_zh = f"对比的是{day_zh}收盘——尚未捕获更新的收盘价。"
            if blk["state"] == "STALE_WITH_LAST_KNOWN" and blk.get("state_reason_en"):
                blk["state_reason_en"] = f"{baseline_en} {blk['state_reason_en']}"
                blk["state_reason_zh"] = f"{baseline_zh}{blk['state_reason_zh']}"
            else:
                blk["state_reason_en"] = baseline_en
                blk["state_reason_zh"] = baseline_zh
        elif blk["state"] == "CURRENT" and phase == "preopen":
            # Premarket is a real reading window (intraday-fastpath runs
            # */30 11-21 UTC) — a fresh reading before the cash open is not
            # stale, but it IS worth disclosing as premarket, not a live tape.
            blk["state_reason_en"] = "Premarket reading — the regular session has not opened yet."
            blk["state_reason_zh"] = "盘前读数——正式交易时段尚未开始。"
        elif blk["state"] == "CURRENT" and phase == "closed":
            blk["state_reason_en"] = "After the close — the regular session has ended."
            blk["state_reason_zh"] = "已收盘——正式交易时段已经结束。"
        return blk
    except Exception as exc:  # noqa: BLE001
        log.debug("am_edition: tape block failed (%s)", exc)
        return _block(
            "tape_since_prior_close",
            title_en="Since yesterday's close",
            title_zh="自昨日收盘以来",
            source_ref=quotes_source_ref,
            source_owner="intraday-fastpath",
            classification="deterministic_derived_comparison",
            source_as_of=None,
            max_age_minutes=240,
            generated_at=generated_at,
            covered=False,
            reason_en="The live tape reading could not be read.",
            reason_zh="无法读取实时行情读数。",
        )


def _owner_state_block(site: Path, data_dir: Path, generated_at: str) -> dict:
    try:
        d = _load_committed(site, data_dir, "market_state.json", "market_state/latest.json")
        if not d:
            return _block(
                "market_state", title_en="Market state", title_zh="市场状态",
                source_ref="data/market_state/latest.json", source_owner="nightly",
                classification="owner_fact", source_as_of=None, max_age_minutes=1440,
                generated_at=generated_at, covered=False,
                reason_en="Market state has not been generated yet.",
                reason_zh="市场状态尚未生成。",
            )
        as_of_iso, precision = _norm_clock(d.get("asof"))
        rows = [{
            "label_en": d.get("label_en"), "label_zh": d.get("label_zh"),
            "posture_en": d.get("posture_en"), "posture_zh": d.get("posture_zh"),
            "headline_en": d.get("headline_en"), "headline_zh": d.get("headline_zh"),
        }]
        return _block(
            "market_state", title_en="Market state", title_zh="市场状态",
            source_ref="data/market_state/latest.json", source_owner="nightly",
            classification="owner_fact", source_as_of=as_of_iso, max_age_minutes=1440,
            generated_at=generated_at, rows=rows, precision=precision,
        )
    except Exception as exc:  # noqa: BLE001
        log.debug("am_edition: market_state block failed (%s)", exc)
        return _block(
            "market_state", title_en="Market state", title_zh="市场状态",
            source_ref="data/market_state/latest.json", source_owner="nightly",
            classification="owner_fact", source_as_of=None, max_age_minutes=1440,
            generated_at=generated_at, covered=False,
            reason_en="Market state could not be read.", reason_zh="无法读取市场状态。",
        )


def _regime_block(site: Path, data_dir: Path, generated_at: str) -> dict:
    try:
        d = _load_committed(site, data_dir, "regime.json", "regime/latest.json")
        if not d:
            return _block(
                "regime", title_en="Regime", title_zh="宏观周期",
                source_ref="data/regime/latest.json", source_owner="nightly",
                classification="owner_fact", source_as_of=None, max_age_minutes=1440,
                generated_at=generated_at, covered=False,
                reason_en="Regime has not been generated yet.", reason_zh="宏观周期尚未生成。",
            )
        as_of_raw = d.get("asof") or d.get("date")
        as_of_iso, precision = _norm_clock(as_of_raw)
        quad_code = d.get("label")  # internal slug e.g. "Q2" — never surfaced raw
        mapped = _QUAD_LABELS.get(quad_code)
        extra_reason_en = None
        extra_reason_zh = None
        if mapped:
            label_en, label_zh = mapped
        else:
            # Never copy English into the ZH field. A missing map is a typed
            # null with a plain-word reason, not a silent EN fallback.
            label_en = d.get("quad_name")
            label_zh = None
            extra_reason_en = (
                "No Chinese label is on file for this regime — "
                "the English name was not copied into the Chinese field."
            )
            extra_reason_zh = "宏观周期名称尚无中文对照，英文名未写入中文栏。"
        rows = [{"quad_name_en": label_en, "quad_name_zh": label_zh}]
        blk = _block(
            "regime", title_en="Regime", title_zh="宏观周期",
            source_ref="data/regime/latest.json", source_owner="nightly",
            classification="owner_fact", source_as_of=as_of_iso, max_age_minutes=1440,
            generated_at=generated_at, rows=rows, precision=precision,
        )
        if extra_reason_zh and not blk.get("state_reason_zh"):
            blk["state_reason_en"] = extra_reason_en
            blk["state_reason_zh"] = extra_reason_zh
        elif extra_reason_zh:
            # Keep freshness/unavailability copy; attach the ZH-null note.
            blk["state_reason_en"] = f"{blk['state_reason_en']} {extra_reason_en}".strip()
            blk["state_reason_zh"] = f"{blk['state_reason_zh']}{extra_reason_zh}"
        return blk
    except Exception as exc:  # noqa: BLE001
        log.debug("am_edition: regime block failed (%s)", exc)
        return _block(
            "regime", title_en="Regime", title_zh="宏观周期",
            source_ref="data/regime/latest.json", source_owner="nightly",
            classification="owner_fact", source_as_of=None, max_age_minutes=1440,
            generated_at=generated_at, covered=False,
            reason_en="Regime could not be read.", reason_zh="无法读取宏观周期。",
        )


def _plane_block(site: Path, data_dir: Path, generated_at: str) -> dict:
    try:
        d = _load_committed(site, data_dir, "neuralweb/market_plane.json", "neuralweb/market_plane.json")
        if not d:
            return _block(
                "cross_asset_plane", title_en="Cross-asset plane", title_zh="跨资产全景",
                source_ref="data/neuralweb/market_plane.json", source_owner="nightly",
                classification="owner_fact", source_as_of=None, max_age_minutes=1440,
                generated_at=generated_at, covered=False,
                reason_en="Cross-asset plane has not been generated yet.",
                reason_zh="跨资产全景尚未生成。",
            )
        as_of_iso, precision = _norm_clock(d.get("asof"))
        verdict_raw = d.get("verdict")
        if isinstance(verdict_raw, dict):
            # Authority-shaped verdict objects (e.g. a `score`/rank field) are
            # NEVER passed through whole — only the plain-word verdict label
            # is display_only; whitelist it field-by-field.
            verdict_val = {
                "verdict": verdict_raw.get("verdict"),
                "label_en": verdict_raw.get("label_en"),
                "label_zh": verdict_raw.get("label_zh"),
            }
        else:
            verdict_val = verdict_raw
        count = d.get("contradiction_count")
        if count is None:
            contradictions_en = contradictions_zh = None
        elif count == 0:
            contradictions_en = "No disagreements across the plane."
            contradictions_zh = "各资产读数一致，无分歧。"
        elif count == 1:
            contradictions_en = "1 disagreement across the plane."
            contradictions_zh = "各资产读数有1处分歧。"
        else:
            contradictions_en = f"{int(count)} disagreements across the plane."
            contradictions_zh = f"各资产读数有{int(count)}处分歧。"
        stale_flag = d.get("stale")
        if stale_flag is True:
            freshness_en = "This plane reading is stale."
            freshness_zh = "该全景读数已过时。"
        elif stale_flag is False:
            freshness_en = "This plane reading is current."
            freshness_zh = "该全景读数是最新的。"
        else:
            freshness_en = freshness_zh = None
        rows = [{
            "verdict": verdict_val,
            "contradictions_en": contradictions_en,
            "contradictions_zh": contradictions_zh,
            "freshness_en": freshness_en,
            "freshness_zh": freshness_zh,
            # Raw contradiction_count / stale / gaps are machine fields —
            # never shipped. gaps also carry internal component slugs.
        }]
        return _block(
            "cross_asset_plane", title_en="Cross-asset plane", title_zh="跨资产全景",
            source_ref="data/neuralweb/market_plane.json", source_owner="nightly",
            classification="owner_fact", source_as_of=as_of_iso, max_age_minutes=1440,
            generated_at=generated_at, rows=rows, precision=precision,
        )
    except Exception as exc:  # noqa: BLE001
        log.debug("am_edition: plane block failed (%s)", exc)
        return _block(
            "cross_asset_plane", title_en="Cross-asset plane", title_zh="跨资产全景",
            source_ref="data/neuralweb/market_plane.json", source_owner="nightly",
            classification="owner_fact", source_as_of=None, max_age_minutes=1440,
            generated_at=generated_at, covered=False,
            reason_en="Cross-asset plane could not be read.", reason_zh="无法读取跨资产全景。",
        )


def _calendar_block(site: Path, data_dir: Path, generated_at: str, session_date: str) -> dict:
    try:
        d = _load_committed(site, data_dir, "release_forecast.json", "release_forecast/latest.json")
        if not d:
            return _block(
                "todays_calendar", title_en="Today's calendar", title_zh="今日日程",
                source_ref="data/release_forecast/latest.json", source_owner="nightly",
                classification="deterministic_calendar", source_as_of=None, max_age_minutes=1440,
                generated_at=generated_at, covered=False,
                reason_en="Today's calendar has not been generated yet.",
                reason_zh="今日日程尚未生成。",
            )
        as_of_iso, precision = _norm_clock(d.get("asof"))
        upcoming = d.get("upcoming") or []
        rows = []
        for u in upcoming:
            if not isinstance(u, dict):
                continue
            # Production upcoming rows carry `release_date`, never `date`.
            if not str(u.get("release_date") or "").startswith(session_date):
                continue
            title_en, title_zh = _release_title(u)
            rows.append({
                "release_date": str(u.get("release_date")),
                "title_en": title_en,
                "title_zh": title_zh,
            })
        empty_reason_en = "No scheduled US releases today." if not rows else None
        empty_reason_zh = "今日无美国经济数据发布。" if not rows else None
        return _block(
            "todays_calendar", title_en="Today's calendar", title_zh="今日日程",
            source_ref="data/release_forecast/latest.json", source_owner="nightly",
            classification="deterministic_calendar", source_as_of=as_of_iso, max_age_minutes=1440,
            generated_at=generated_at, rows=rows, precision=precision,
            reason_en=empty_reason_en, reason_zh=empty_reason_zh,
        )
    except Exception as exc:  # noqa: BLE001
        log.debug("am_edition: calendar block failed (%s)", exc)
        return _block(
            "todays_calendar", title_en="Today's calendar", title_zh="今日日程",
            source_ref="data/release_forecast/latest.json", source_owner="nightly",
            classification="deterministic_calendar", source_as_of=None, max_age_minutes=1440,
            generated_at=generated_at, covered=False,
            reason_en="Today's calendar could not be read.", reason_zh="无法读取今日日程。",
        )


def _prior_brief_ref_block(site: Path, data_dir: Path, generated_at: str) -> dict:
    try:
        d = _load_committed(site, data_dir, "master_brief.json", "regime/master_brief.json")
        if not d:
            return _block(
                "prior_close_brief_ref", title_en="Yesterday's brief", title_zh="昨日简报",
                source_ref="site/master_brief.json", source_owner="master_brain",
                classification="existing_model_generated_prior_close_brief",
                source_as_of=None, max_age_minutes=1440, generated_at=generated_at, covered=False,
                reason_en="No prior-close brief is available yet.", reason_zh="暂无昨日收盘简报。",
            )
        as_of_iso, precision = _norm_clock(d.get("generated_at"))
        rows = [{
            "generated_at": as_of_iso,
            "link": "/aibrief.html",
        }]
        return _block(
            "prior_close_brief_ref", title_en="Yesterday's brief", title_zh="昨日简报",
            source_ref="site/master_brief.json", source_owner="master_brain",
            classification="existing_model_generated_prior_close_brief",
            source_as_of=as_of_iso, max_age_minutes=1440, generated_at=generated_at, rows=rows,
            precision=precision,
        )
    except Exception as exc:  # noqa: BLE001
        log.debug("am_edition: prior brief ref block failed (%s)", exc)
        return _block(
            "prior_close_brief_ref", title_en="Yesterday's brief", title_zh="昨日简报",
            source_ref="site/master_brief.json", source_owner="master_brain",
            classification="existing_model_generated_prior_close_brief",
            source_as_of=None, max_age_minutes=1440, generated_at=generated_at, covered=False,
            reason_en="The prior-close brief could not be read.", reason_zh="无法读取昨日收盘简报。",
        )


# ---------------------------------------------------------------------------
# MOR-2b Lane A new blocks (DEC §3.1 items 3, 6, 8 — context planes, research
# watch, owner links). Every value is either an owner fact read verbatim from
# an already-committed deterministic artifact, a plain-word label surfaced by
# the owner itself, or a reference resolved through the closed registry; no
# signal, rank, score, gate, sizing, ENTRY_OPEN or buy/sell call is originated
# here. Per-row states drive block state (worst row state wins).
# ---------------------------------------------------------------------------


def _row_state(
    source_as_of: str | None,
    generated_at: str,
    *,
    covered: bool = True,
    precision: str | None = None,
    max_age_minutes: int | None = None,
) -> tuple[str, int | None]:
    """One-row state decision: CURRENT/STALE_WITH_LAST_KNOWN/UNAVAILABLE/NOT_COVERED.
    Pure, no legacy coupling. `max_age_minutes` is the budget THIS row/block
    advertises (passed in so the new blocks each set their own — context_planes
    uses _CONTEXT_PLANE_MAX_AGE = 1440, research_watch uses
    _RESEARCH_WATCH_MAX_AGE = 14400 per §A3). When `precision` is "day",
    freshness is judged in whole days (MAJOR 5) so a yesterday-stamped source
    IS CURRENT today.

    R2 (BLOCKER 2, 2026-09-24): `_row_state` previously hardcoded
    _CONTEXT_PLANE_MAX_AGE inside this helper, so research_watch rows were
    aged on a 1440-minute budget while the block advertised 14400 — that
    contradiction meant the block could never read CURRENT on real theses.
    The budget now lives in the parameter and the call sites pass the
    block's own max_age_minutes through."""
    if not covered:
        return "NOT_COVERED", None
    if source_as_of is None:
        return "UNAVAILABLE", None
    try:
        gen_dt = datetime.fromisoformat(generated_at)
        src_dt = datetime.fromisoformat(source_as_of)
    except Exception:  # noqa: BLE001
        return "UNAVAILABLE", None
    age_seconds = (gen_dt - src_dt).total_seconds()
    age_minutes = int(age_seconds // 60)
    if age_seconds < 0:
        return "UNAVAILABLE", age_minutes
    if precision == "day":
        try:
            gen_date = gen_dt.astimezone(timezone.utc).date()
            src_date = src_dt.astimezone(timezone.utc).date()
            age_days = (gen_date - src_date).days
            budget = max_age_minutes if max_age_minutes is not None else _CONTEXT_PLANE_MAX_AGE
            max_age_days = -(-budget // 1440) if budget > 0 else 0
            if age_days <= max_age_days:
                return "CURRENT", age_minutes
            return "STALE_WITH_LAST_KNOWN", age_minutes
        except Exception:  # noqa: BLE001
            pass
    budget = max_age_minutes if max_age_minutes is not None else _CONTEXT_PLANE_MAX_AGE
    if age_minutes <= budget:
        return "CURRENT", age_minutes
    return "STALE_WITH_LAST_KNOWN", age_minutes


def _row_age_phrase_en_zh(age_minutes: int | None) -> tuple[str, str]:
    """Plain-word EN/ZH age disclosure for a stale row."""
    if age_minutes is None:
        return "", ""
    age_en, age_zh = _humanize_age(age_minutes)
    return f"Last updated {age_en} ago.", f"最近更新于{age_zh}前。"


def _safe_zh_mirror(cond_text: str) -> str:
    """Build the ZH mirror of an OPEN-condition row. The condition text is
    English (theses.jsonl is EN-only); the ZH field surfaces a single ZH
    framing sentence that names the row's intent — NEVER the EN text, never
    a prefix that embeds the EN condition into the ZH field (BLOCKER 3 /
    plain-language law). The framing is picked deterministically by the
    hash of the condition string so the same row always reads the same ZH
    frame, but the framing itself is ZH only."""
    if not cond_text:
        return ""
    pick = int(hashlib.sha256(cond_text.encode("utf-8")).hexdigest(), 16) % len(_RESEARCH_WATCH_ZH_FRAMES)
    return _RESEARCH_WATCH_ZH_FRAMES[pick]


def _context_planes_row(
    plane: str,
    label_en: str | None,
    label_zh: str | None,
    read_en: str | None,
    read_zh: str | None,
    as_of: str | None,
    source_ref: str,
    *,
    covered: bool = True,
    not_covered_reason_en: str | None = None,
    not_covered_reason_zh: str | None = None,
    generated_at: str,
    precision: str | None = None,
) -> dict:
    """One context_planes row. State is decided per-row by as_of age.
    `precision` is the caller's _norm_clock result for `as_of` — the row
    function never recomputes precision from the already-normalised string
    (the legacy _block() docstring warns this reads "minute"/"second" because
    the ...T00:00:00+00:00 padding looks second-exact).

    Owner-transferred text is passed through verbatim (R6: the runtime A7
    regex is REMOVED because it destroyed benign owner prose like "long-
    dated" / "long end" / "long Treasury"; the A7 contract is now a
    load-time key gate on theses.jsonl and a post-render text scan)."""
    state, age = _row_state(as_of, generated_at, covered=covered, precision=precision)
    if precision is None:
        _, precision = _norm_clock(as_of) if as_of else (None, "day")
    row_dict = {
        "plane": plane,
        "label_en": label_en,
        "label_zh": label_zh,
        "read_en": read_en,
        "read_zh": read_zh,
        "as_of": as_of if state in ("CURRENT", "STALE_WITH_LAST_KNOWN") else None,
        "source_as_of_precision": precision if state in ("CURRENT", "STALE_WITH_LAST_KNOWN") else None,
        "source_ref": source_ref,
        "state": state,
    }
    if state == "STALE_WITH_LAST_KNOWN":
        row_dict["state_reason_en"], row_dict["state_reason_zh"] = _row_age_phrase_en_zh(age)
    elif state == "NOT_COVERED":
        row_dict["state_reason_en"] = not_covered_reason_en or "Not covered yet."
        row_dict["state_reason_zh"] = not_covered_reason_zh or "暂未覆盖。"
    elif state == "UNAVAILABLE":
        row_dict["state_reason_en"] = not_covered_reason_en or _UNAVAILABLE_DEFAULT_EN
        row_dict["state_reason_zh"] = not_covered_reason_zh or _UNAVAILABLE_DEFAULT_ZH
    return row_dict


def _context_planes_block(site: Path, data_dir: Path, generated_at: str) -> dict:
    """Read the five planes from their deterministic owner artifacts and pack
    them in the order the spec names: rates, dollar, credit, commodity,
    international. Block state = worst row state (ranked)."""
    rows: list[dict] = []
    # All paths verified against the MOR-2a census §2 table on origin/main.
    transmission = _load_committed(site, data_dir, "transmission.json", "transmission/latest.json")
    transmission_source_ref = "data/transmission/latest.json"
    transmission_root_asof = None
    rates_state = dollar_state = credit_state = None
    if isinstance(transmission, dict):
        transmission_root_asof, transmission_root_precision = _norm_clock(transmission.get("asof"))
        # rates
        r = (transmission.get("state") or {}).get("rates") or {}
        rates_label = (r.get("label") or {}) if isinstance(r.get("label"), dict) else {}
        rates_regime_en = r.get("regime")
        rates_direction_en = r.get("direction")
        rates_turn_watch = r.get("turn_watch")
        # yield_curve: read the top-level `yield_curve` block (the spec names
        # this as a sub-input to the rates row). The artifact ships a regime
        # label in {en,zh}; we surface THAT — never the percentile, never the
        # raw slope number (BLOCKER 1: the round-2 producer deleted this
        # entire input; the spec mandates it).
        yc = transmission.get("yield_curve") if isinstance(transmission.get("yield_curve"), dict) else {}
        yc_regime = (yc.get("regime") or {}) if isinstance(yc.get("regime"), dict) else {}
        yc_label_en = yc_regime.get("label") if isinstance(yc_regime, dict) else None
        if not isinstance(yc_label_en, dict):
            yc_label_en = None
        yc_label_en_str = yc_label_en.get("en") if isinstance(yc_label_en, dict) else None
        yc_label_zh_str = yc_label_en.get("zh") if isinstance(yc_label_en, dict) else None
        # Compose a plain-word EN/ZH read from the owner-rendered label (the
        # owner already maps regime + direction to plain words) and append a
        # turn-watch phrase when non-null. We never surface the percentile
        # (real_10y_pctile) — that is a machine field, not a glance-tier read.
        # §A2 forbids the percentile; we do not copy `real_10y_pctile`. The
        # owner label itself may carry extremeness copy ("at a 5y extreme"),
        # which we pass through unchanged (the producer never invents the
        # extremeness phrase — it surfaces the owner's own plain words).
        read_en_parts: list[str] = []
        read_zh_parts: list[str] = []
        if rates_label.get("en"):
            read_en_parts.append(str(rates_label["en"]))
        if rates_label.get("zh"):
            read_zh_parts.append(str(rates_label["zh"]))
        if yc_label_en_str:
            # Owner-rendered plain words; no percentiles, no slope numbers.
            read_en_parts.append(f"Yield curve: {yc_label_en_str}.")
            if yc_label_zh_str:
                read_zh_parts.append(f"收益率曲线：{yc_label_zh_str}。")
            else:
                read_zh_parts.append("收益率曲线：参见英文标注。")
        if rates_turn_watch and rates_turn_watch != "none" and not yc_label_en_str:
            # Plain-word "watch" phrase; never the percentile itself. Only
            # surface when there is NO yield-curve phrase so the row stays
            # at two sentences (R11: no run-on, no stray spaces).
            read_en_parts.append("Under watch — fresh extremes being tracked.")
            read_zh_parts.append("正在观察——正在跟踪新的极值。")
        # R11: rates copy is two sentences max with no run-on. The first
        # sentence carries the owner-rendered label (regime + direction).
        # The second sentence carries the yield-curve phrase OR the
        # turn-watch phrase — never both. Joined with a single space;
        # ZH fields use a full-width 。 separator (no ASCII spaces around
        # clauses; the ZH field is one glance-tier line).
        read_en_str = " ".join(p for p in read_en_parts if p).strip()
        read_zh_str = "".join(p for p in read_zh_parts if p).strip()
        rates_state = _context_planes_row(
            "rates",
            label_en=rates_label.get("en") or rates_regime_en,
            label_zh=rates_label.get("zh") or (rates_regime_en and _RATES_REGIME_ZH.get(rates_regime_en)),
            read_en=read_en_str or None,
            read_zh=read_zh_str or None,
            as_of=transmission_root_asof,
            source_ref=transmission_source_ref,
            generated_at=generated_at,
            covered=bool(transmission_root_asof),
            precision=transmission_root_precision,
        )
        # dollar
        dc = transmission.get("dollar_channel") or {}
        dc_state_obj = dc.get("state") if isinstance(dc, dict) else None
        dc_state_en = dc_state_obj.get("en") if isinstance(dc_state_obj, dict) else None
        dc_state_zh = dc_state_obj.get("zh") if isinstance(dc_state_obj, dict) else None
        dc_asof, dc_precision = _norm_clock(dc.get("asof") if isinstance(dc, dict) else None)
        dc_lean = (dc.get("regime") or {}) if isinstance(dc, dict) else {}
        dc_lean_en = dc_lean.get("en") if isinstance(dc_lean, dict) else None
        dc_lean_zh = dc_lean.get("zh") if isinstance(dc_lean, dict) else None
        # Compose read from dollar regime; never the correlation numbers.
        dollar_state = _context_planes_row(
            "dollar",
            label_en=dc_state_en or dc_lean_en,
            label_zh=dc_state_zh or dc_lean_zh,
            read_en=dc_lean_en,
            read_zh=dc_lean_zh,
            as_of=dc_asof,
            source_ref=transmission_source_ref,
            generated_at=generated_at,
            covered=bool(dc_asof),
            precision=dc_precision,
        )
        # credit — present only if a keyed `state.credit` field exists in the
        # committed artifact. The spec names this gap explicitly: a missing
        # credit field is NOT_COVERED with a plain reason, never guessed.
        credit_obj = (transmission.get("state") or {}).get("credit")
        if isinstance(credit_obj, dict):
            credit_label_obj = credit_obj.get("label") or {}
            credit_label_en = credit_label_obj.get("en") if isinstance(credit_label_obj, dict) else None
            credit_label_zh = credit_label_obj.get("zh") if isinstance(credit_label_obj, dict) else None
            credit_regime = credit_obj.get("regime")
            credit_asof, credit_precision = _norm_clock(credit_obj.get("asof"))
            credit_state = _context_planes_row(
                "credit",
                label_en=credit_label_en or credit_regime,
                label_zh=credit_label_zh or credit_regime,
                read_en=credit_label_en,
                read_zh=credit_label_zh,
                as_of=credit_asof,
                source_ref=transmission_source_ref,
                generated_at=generated_at,
                covered=bool(credit_asof),
                precision=credit_precision,
            )
        else:
            credit_state = _context_planes_row(
                "credit",
                label_en=None,
                label_zh=None,
                read_en=None,
                read_zh=None,
                as_of=None,
                source_ref=transmission_source_ref,
                generated_at=generated_at,
                covered=False,
                not_covered_reason_en="Credit is not projected by the transmission owner yet.",
                not_covered_reason_zh="信用维度尚未由传输主理人覆盖。",
            )
    else:
        # Whole-artifact missing — three rows degrade to UNAVAILABLE. The
        # transmission pipeline exists; the file just isn't there (gate 4
        # separates "missing owner file" from "NOT_COVERED"). UNAVAILABLE is
        # the truthful typed state; NOT_COVERED is reserved for fields the
        # owner has explicitly chosen not to publish (e.g. credit when
        # state.credit is absent from the loaded file). Passing covered=True
        # here lets _row_state resolve UNAVAILABLE via the source_as_of=None
        # branch — passing covered=False would silently downgrade this to
        # NOT_COVERED and conflate the two failure modes (MAJOR 3).
        for plane in ("rates", "dollar", "credit"):
            rows.append(_context_planes_row(
                plane,
                label_en=None, label_zh=None,
                read_en=None, read_zh=None,
                as_of=None,
                source_ref=transmission_source_ref,
                generated_at=generated_at,
                covered=True,
                not_covered_reason_en="Transmission state file is not available yet.",
                not_covered_reason_zh="传输状态文件暂不可用。",
            ))
    if rates_state is not None:
        rows.append(rates_state)
    if dollar_state is not None:
        rows.append(dollar_state)
    if credit_state is not None:
        rows.append(credit_state)

    # commodity — plain-word regime + favored + breadth. No index levels.
    commodity = _load_committed(site, data_dir, "commodity.json", "commodity/latest.json")
    commodity_source_ref = "data/commodity/latest.json"
    if isinstance(commodity, dict):
        c_asof, c_precision = _norm_clock(commodity.get("asof") or commodity.get("date"))
        c_regime = commodity.get("regime")
        c_regime_pair = _COMMODITY_REGIME_LABELS.get(c_regime)
        if c_regime_pair is not None:
            c_label_en, c_label_zh = c_regime_pair
        else:
            # Unmapped regime: surface the EN, leave ZH null with a disclosure.
            c_label_en = c_regime
            c_label_zh = None
        c_favored = commodity.get("favored") or []
        c_breadth = commodity.get("breadth") or {}
        c_breadth_n = c_breadth.get("n_members")
        c_breadth_up = c_breadth.get("n_up_trend")
        breadth_en = None
        breadth_zh = None
        if isinstance(c_breadth_n, int) and isinstance(c_breadth_up, int):
            breadth_en = f"{c_breadth_up}/{c_breadth_n} members trending up."
            breadth_zh = f"{c_breadth_up}/{c_breadth_n} 个品种趋势向上。"
        favored_en_list = [str(x) for x in c_favored if x]
        favored_en = "、".join(favored_en_list) if favored_en_list else None
        # Map EN commodity names to ZH (R9); unknown names are OMITTED from
        # the ZH list (a missing ZH label must NOT copy the EN token into
        # the ZH field).
        favored_zh_list = [
            _COMMODITY_NAME_ZH[n] for n in favored_en_list if n in _COMMODITY_NAME_ZH
        ]
        favored_zh = "、".join(favored_zh_list) if favored_zh_list else None
        read_en = (
            ("Favored: " + favored_en + ". " + breadth_en)
            if favored_en and breadth_en else (favored_en or breadth_en)
        )
        if favored_zh is not None:
            read_zh = (
                ("看好：" + favored_zh + "。" + breadth_zh)
                if favored_zh and breadth_zh else favored_zh
            )
        else:
            read_zh = breadth_zh
        rows.append(_context_planes_row(
            "commodity",
            label_en=c_label_en,
            label_zh=c_label_zh,
            read_en=read_en,
            read_zh=read_zh,
            as_of=c_asof,
            source_ref=commodity_source_ref,
            generated_at=generated_at,
            covered=bool(c_asof),
            precision=c_precision,
        ))
    else:
        # Missing commodity artifact: §0 gate 4 separates "missing owner
        # file" from "NOT_COVERED" — this row is UNAVAILABLE because the
        # commodity pipeline exists but the file is missing. covered=True
        # lets _row_state resolve UNAVAILABLE via the as_of=None branch
        # (MAJOR 3).
        rows.append(_context_planes_row(
            "commodity",
            label_en=None, label_zh=None,
            read_en=None, read_zh=None,
            as_of=None,
            source_ref=commodity_source_ref,
            generated_at=generated_at,
            covered=True,
            not_covered_reason_en="Commodity state file is not available yet.",
            not_covered_reason_zh="商品状态文件暂不可用。",
        ))

    # international — China then HK market_state summaries. Each contributes
    # one row keyed under plane="international" with both markets folded in.
    intl_rows: list[dict] = []
    cn_present = hk_present = False
    for path in ("china_market_state.json", "hk_market_state.json"):
        label = "china" if "china" in path else "hk"
        d = _load_committed(site, data_dir, path, path.replace(".json", "/latest.json"))
        if isinstance(d, dict):
            d_asof, d_precision = _norm_clock(d.get("asof"))
            intl_rows.append({
                "label": label,
                "asof": d_asof,
                "asof_precision": d_precision,
                "label_en": d.get("label_en"),
                "label_zh": d.get("label_zh"),
                "posture_en": d.get("posture_en"),
                "posture_zh": d.get("posture_zh"),
                "headline_en": d.get("headline_en"),
                "headline_zh": d.get("headline_zh"),
            })
            if label == "china":
                cn_present = True
            else:
                hk_present = True
        # NOTE: when BOTH intl files are absent the producer surfaces an
        # UNAVAILABLE row (the intl pipeline exists; both files just aren't
        # there). R5 covers the asymmetric case where ONE file is missing —
        # the row is then built from the PRESENT half only. When zero
        # halves are present we drop the intl_rows list entirely below
        # and emit a UNAVAILABLE row via the same `_context_planes_row` path
        # the other planes use.
    if intl_rows:
        cn = intl_rows[0]
        hk = intl_rows[1] if len(intl_rows) > 1 else {"label": "hk", "asof": None, "asof_precision": "day"}
        # When BOTH intl files are missing the row degrades to UNAVAILABLE
        # directly — the intl pipeline exists; both files just aren't there
        # (matches the transmission/commodity "missing owner file" semantic).
        if not cn_present and not hk_present:
            rows.append(_context_planes_row(
                "international",
                label_en=None, label_zh=None,
                read_en=None, read_zh=None,
                as_of=None,
                source_ref="data/china_market_state/latest.json + data/hk_market_state/latest.json",
                generated_at=generated_at,
                covered=True,
                not_covered_reason_en=_UNAVAILABLE_DEFAULT_EN,
                not_covered_reason_zh=_UNAVAILABLE_DEFAULT_ZH,
            ))
        else:
            # Per-row per-market state (R5): the row is built from whichever
            # owner file is PRESENT. If one file is missing, the row's clock
            # comes from the present file only — never from a phantom as_of the
            # producer invents. State and reasons are decided per-row, NOT via a
            # post-hoc state override that re-writes what `_context_planes_row`
            # already decided.
            cn_state, cn_age = _row_state(cn.get("asof"), generated_at, precision=cn.get("asof_precision"))
            hk_state, hk_age = _row_state(hk.get("asof"), generated_at, precision=hk.get("asof_precision"))
            # Per-market attribution: china then HK, each prefixed with its market
            # name so the reader can tell which sentence is which (BLOCKER 4:
            # the previous code concatenated two byte-identical headlines into
            # one sentence with no attribution — measured the committed artifact
            # ships identical headline_en for both markets).
            cn_phrase_en = (
                f"China — {cn.get('label_en') or '—'}; posture {cn.get('posture_en') or '—'}."
                if cn.get("label_en") else None
            )
            hk_phrase_en = (
                f"Hong Kong — {hk.get('label_en') or '—'}; posture {hk.get('posture_en') or '—'}."
                if hk.get("label_en") else None
            )
            cn_phrase_zh = (
                f"中国——{cn.get('label_zh') or '—'}；姿态 {cn.get('posture_zh') or '—'}。"
                if cn.get("label_zh") else None
            )
            hk_phrase_zh = (
                f"香港——{hk.get('label_zh') or '—'}；姿态 {hk.get('posture_zh') or '—'}。"
                if hk.get("label_zh") else None
            )
            # Headline is the OWNER's full sentence — never the truncated label
            # + posture pair (which duplicated each other in the real artifact:
            # the committed china_market_state ships label = "Risk-off" and
            # posture = "Risk-off" verbatim, making the row redundant). Each
            # market's headline is prefixed with its market name so the reader
            # can attribute the prose (BLOCKER 4).
            cn_headline_en = (
                f"China — {cn.get('headline_en')}" if cn.get("headline_en") else cn_phrase_en
            )
            hk_headline_en = (
                f"Hong Kong — {hk.get('headline_en')}" if hk.get("headline_en") else hk_phrase_en
            )
            cn_headline_zh = (
                f"中国——{cn.get('headline_zh')}" if cn.get("headline_zh") else cn_phrase_zh
            )
            hk_headline_zh = (
                f"香港——{hk.get('headline_zh')}" if hk.get("headline_zh") else hk_phrase_zh
            )
            # R5 missing-owner disclosure: when one of the two files is missing,
            # the missing market's headline slot is REPLACED with a plain-word
            # disclosure naming the absent half — never a phantom sentence
            # borrowing from the present market's clock. The row's overall state
            # is then decided from the present market's clock + the missing
            # half's disclosed UNAVAILABLE copy.
            missing_en = missing_zh = None
            if not cn_present:
                missing_en = "Mainland read not available this morning."
                missing_zh = "今晨暂无A股读数。"
            elif not hk_present:
                missing_en = "Hong Kong read not available this morning."
                missing_zh = "今晨暂无港股读数。"
            if missing_en is not None:
                if cn_present:
                    # HK missing: keep CN sentence, replace HK slot with disclosure.
                    hk_headline_en = missing_en
                    hk_headline_zh = missing_zh
                else:
                    # CN missing: replace CN slot with disclosure, keep HK sentence.
                    cn_headline_en = missing_en
                    cn_headline_zh = missing_zh
            # Two sentences joined with a hard separator; the row carries both
            # markets' attribution, so the reader can tell which is which even
            # when the underlying headlines are byte-identical.
            read_en = " | ".join(p for p in (cn_headline_en, hk_headline_en) if p) or None
            read_zh = " | ".join(p for p in (cn_headline_zh, hk_headline_zh) if p) or None
            # R5 row clock: when one half is missing the row's clock is the
            # PRESENT half's clock (the producer never invents an as_of). The
            # row's state is decided from that clock via _context_planes_row.
            present_iso = cn.get("asof") if cn_present else hk.get("asof")
            present_precision = (
                cn.get("asof_precision") if cn_present else hk.get("asof_precision")
            )
            present_label_en = (
                cn.get("label_en") if cn_present else hk.get("label_en")
            )
            present_label_zh = (
                cn.get("label_zh") if cn_present else hk.get("label_zh")
            )
            intl_row = _context_planes_row(
                "international",
                label_en=present_label_en,
                label_zh=present_label_zh,
                read_en=read_en,
                read_zh=read_zh,
                as_of=present_iso,
                source_ref="data/china_market_state/latest.json + data/hk_market_state/latest.json",
                generated_at=generated_at,
                covered=bool(present_iso),
                precision=present_precision,
            )
            # When one half is missing, the row carries a state_reason_en/zh
            # naming the missing half in plain words (R5) — these keys are
            # required on every non-CURRENT row so the consumer can render
            # the missing-market disclosure alongside the present-market clock.
            if missing_en is not None and intl_row["state"] != "CURRENT":
                intl_row["state_reason_en"] = missing_en
                intl_row["state_reason_zh"] = missing_zh
            rows.append(intl_row)

    # Block state: worst row state across all rows.
    block_state = _WorstOf([r["state"] for r in rows]) if rows else "UNAVAILABLE"
    # R12 block clock = NEWEST as_of among rows that carry one, regardless
    # of the block state. The previous code picked the as_of of the FIRST
    # row matching the block state and broke early; that left the clock null
    # whenever the worst row was NOT_COVERED/UNAVAILABLE even when every
    # other row carried a fresh clock. The truthful disclosure for a
    # multi-owner summary is the NEWEST reading in the block (the block
    # was last touched when this row was committed), with the worst row
    # driving the state.
    newest_as_of = None
    newest_precision = None
    newest_age: int | None = None
    for r in rows:
        if not r.get("as_of"):
            continue
        if newest_as_of is None or r["as_of"] > newest_as_of:
            newest_as_of = r["as_of"]
            newest_precision = r.get("source_as_of_precision") or (
                _norm_clock(r["as_of"])[1] if r["as_of"] else "day"
            )
            try:
                src_dt = datetime.fromisoformat(r["as_of"])
                gen_dt = datetime.fromisoformat(generated_at)
                secs = (gen_dt - src_dt).total_seconds()
                if secs >= 0:
                    newest_age = int(secs // 60)
            except Exception:  # noqa: BLE001
                newest_age = None
    block = {
        "key": "context_planes",
        "title_en": "Context planes",
        "title_zh": "背景面",
        "state": block_state,
        "source_ref": "see per-row source_ref",
        "source_owner": "multi-owner",
        "source_as_of": newest_as_of if block_state in ("CURRENT", "STALE_WITH_LAST_KNOWN") else None,
        "source_as_of_precision": newest_precision if block_state in ("CURRENT", "STALE_WITH_LAST_KNOWN") else None,
        "age_minutes": newest_age if block_state in ("CURRENT", "STALE_WITH_LAST_KNOWN") else None,
        "max_age_minutes": _CONTEXT_PLANE_MAX_AGE,
        "classification": "owner_context_summary",
        "rows": rows,
    }
    if block_state == "STALE_WITH_LAST_KNOWN":
        block["state_reason_en"] = "Some context planes are not fresh — last-known values shown."
        block["state_reason_zh"] = "部分背景面并非最新——展示的是最新已知值。"
    elif block_state == "UNAVAILABLE":
        block["state_reason_en"] = "Context planes are not available this morning."
        block["state_reason_zh"] = "今晨背景面暂不可用。"
    elif block_state == "NOT_COVERED":
        block["state_reason_en"] = "Some context planes are not yet covered."
        block["state_reason_zh"] = "部分背景面尚未覆盖。"
    # CURRENT rows ship no state_reason — the row disclosures themselves
    # are the freshness disclosure (R8: no "within budget" / "budget"
    # jargon in customer-facing copy).
    return block


# A tiny worst-state ranker for a flat list of state strings. Unknown
# states are ranked WORST (after NOT_COVERED) so a typo'd or new state
# string cannot silently win the worst-of as CURRENT (MINOR 2 — the
# previous default 0 mapped to CURRENT and would silently mask an
# unknown state's true freshness).
_STATE_RANK = {
    "CURRENT": 0,
    "STALE_WITH_LAST_KNOWN": 1,
    "NOT_YET_OPEN": 2,
    "CLOSED": 3,
    "UNAVAILABLE": 4,
    "NOT_COVERED": 5,
}
_UNKNOWN_STATE_RANK = 6


def _WorstOf(states):
    """Return the worst state in `states` per the STATE_RANK ordering; ties go
    to the first occurrence (stable). The leading underscore is for the test
    surface — the helper is named to read like a verb in the call sites."""
    if not states:
        return "UNAVAILABLE"
    return max(states, key=lambda s: _STATE_RANK.get(s, _UNKNOWN_STATE_RANK))


def _research_watch_block(site: Path, data_dir: Path, generated_at: str) -> dict:
    """Read the track-record / theses artifacts and surface at most 5 OPEN
    conditions. Words only — no direction, size, order, target or buy/sell.
    If the newest row is older than _RESEARCH_WATCH_MAX_AGE (10 US sessions
    ≈ 14 calendar days = 14400 minutes), the whole block is
    STALE_WITH_LAST_KNOWN with the dated reason
    "Last updated <YYYY-MM-DD> — showing the last known conditions."

    R2 (BLOCKER 2, 2026-09-24): source_as_of comes from the DISPLAYED ROWS
    only. The previous code mixed in `track_record.json`'s top-level `as_of`
    and used that mix as the block clock — with real artifacts that mix
    reads "1 day ago" while the rows are months old. track_record.json is a
    CALIBRATION summary; its `as_of` is no longer a clock here (it may only
    feed `calibration_note` display, which we surface as a plain sentence
    when present). Staleness budget for the BLOCK and its ROWS is
    _RESEARCH_WATCH_MAX_AGE; `_row_state` takes the budget as a parameter
    so the row age and the block budget agree.

    OPEN conditions live in `data/master_brain/theses.jsonl`. The sibling
    `track_record.json` is a CALIBRATION summary — never an open-condition
    list, so we never claim `conditions` / `open_conditions` keys
    (BLOCKER 5 — never invent a key)."""
    rows: list[dict] = []
    source_ref = "data/master_brain/theses.jsonl + data/master_brain/track_record.json"
    newest_asof: str | None = None
    newest_asof_raw: str | None = None  # pre-normalisation so we can derive "day" precision (MAJOR 6)
    theses_path = data_dir / "master_brain" / "theses.jsonl"
    track_path = data_dir / "master_brain" / "track_record.json"
    calibration_note_en: str | None = None
    calibration_note_zh: str | None = None
    try:
        # 1. theses.jsonl — primary OPEN-condition source. The row set
        # drives the block clock (newest_asof is the max of these rows'
        # as_of, NEVER mixed with track_record.json's top-level as_of).
        if theses_path.exists():
            for line in theses_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:  # noqa: BLE001
                    continue
                if not isinstance(obj, dict):
                    continue
                row = _load_theses_row(obj)
                if row is None:
                    continue
                cond_text = row["cond_text"]
                since_iso = row["since_iso"]
                as_of_iso = row["as_of_iso"]
                logged_raw = row["logged_raw"]
                since_raw = row["since_raw"]
                # R6: the producer surfaces the OWNER's words verbatim. The
                # A7 contract is enforced STRUCTURALLY by `_load_theses_row`
                # — only `id`, `status`, `state_asof`, `logged_at`,
                # `falsifier.text`, `check_by` are read; `lean`,
                # `entry_levels`, `conviction`, `outcome`, `realized` are
                # never touched. The runtime regex is removed (R6) so
                # benign owner prose ("long-dated", "long end", "long
                # Treasury") is rendered verbatim.
                rows.append({
                    "condition_en": cond_text,
                    "condition_zh": _safe_zh_mirror(cond_text),
                    "since": since_iso,
                    "as_of": as_of_iso,
                    "source_ref": "data/master_brain/theses.jsonl",
                })
                # Track newest as_of AMONG THE ROWS ONLY (R2).
                if as_of_iso and (newest_asof is None or as_of_iso > newest_asof):
                    newest_asof = as_of_iso
                    newest_asof_raw = logged_raw or since_raw
        # 2. track_record.json — calibration summary. Its `as_of` is NOT a
        # block clock here (R2); we only surface the calibration_note pair
        # as plain display copy when present.
        if track_path.exists():
            try:
                track = json.loads(track_path.read_text(encoding="utf-8"))
                if isinstance(track, dict):
                    note_en = track.get("calibration_note")
                    note_zh = track.get("calibration_note_zh")
                    if isinstance(note_en, str) and note_en:
                        calibration_note_en = note_en
                    if isinstance(note_zh, str) and note_zh:
                        calibration_note_zh = note_zh
            except Exception as exc:  # noqa: BLE001
                log.debug("am_edition: track_record read failed (%s)", exc)
        # Cap at 5 most-recent conditions (newest first).
        rows.sort(key=lambda r: (r.get("as_of") or ""), reverse=True)
        rows = rows[:5]
    except Exception as exc:  # noqa: BLE001
        log.debug("am_edition: research_watch read failed (%s)", exc)
        rows = []
        newest_asof = None
        newest_asof_raw = None
    # Block state.
    if not rows:
        # No rows because the source file is missing (or empty). MAJOR 3:
        # the research_watch pipeline exists; the file just isn't there. That
        # is UNAVAILABLE, NOT NOT_COVERED — NOT_COVERED is reserved for the
        # case where the owner has explicitly chosen not to publish this
        # field. Build the UNAVAILABLE block directly so the typed state
        # matches the missing-file semantic and does not collapse into the
        # NOT_COVERED branch that `_block(covered=False)` would produce.
        return {
            "key": "research_watch",
            "title_en": "Research watch",
            "title_zh": "研究观察",
            "state": "UNAVAILABLE",
            "source_ref": source_ref,
            "source_owner": "master_brain",
            "source_as_of": None,
            "source_as_of_precision": None,
            "age_minutes": None,
            "max_age_minutes": _RESEARCH_WATCH_MAX_AGE,
            "classification": "owner_research_watch",
            "rows": [],
            "state_reason_en": "Not available this morning.",
            "state_reason_zh": "今晨暂不可用。",
        }
    # Decide block-level state via per-row age (R2: budget = research_watch's
    # own budget, not the legacy context-plane budget).
    row_states = []
    for r in rows:
        s, _ = _row_state(
            r.get("as_of"),
            generated_at,
            max_age_minutes=_RESEARCH_WATCH_MAX_AGE,
        )
        row_states.append(s)
    block_state = _WorstOf(row_states) if row_states else "UNAVAILABLE"
    # Spec: if the newest row is older than _RESEARCH_WATCH_MAX_AGE, the
    # whole block is STALE_WITH_LAST_KNOWN with the dated reason.
    newest_precision = (
        "day"
        if (newest_asof_raw and "T" not in str(newest_asof_raw) and ":" not in str(newest_asof_raw))
        else "second"
    )
    newest_state, newest_age = _row_state(
        newest_asof,
        generated_at,
        precision=newest_precision,
        max_age_minutes=_RESEARCH_WATCH_MAX_AGE,
    )
    if newest_age is not None and newest_age > _RESEARCH_WATCH_MAX_AGE:
        block_state = "STALE_WITH_LAST_KNOWN"
    # Plain-word YYYY-MM-DD prefix for the dated reasons. `newest_asof[:10]`
    # is the canonical ISO date — never an age in hours (R2: "Last updated
    # <YYYY-MM-DD>" with a date, not a duration).
    newest_date = newest_asof[:10] if newest_asof else "—"
    block = {
        "key": "research_watch",
        "title_en": "Research watch",
        "title_zh": "研究观察",
        "state": block_state,
        "source_ref": source_ref,
        "source_owner": "master_brain",
        "source_as_of": newest_asof if block_state in ("CURRENT", "STALE_WITH_LAST_KNOWN") else None,
        "source_as_of_precision": newest_precision if block_state in ("CURRENT", "STALE_WITH_LAST_KNOWN") else None,
        "age_minutes": newest_age if block_state in ("CURRENT", "STALE_WITH_LAST_KNOWN") else None,
        "max_age_minutes": _RESEARCH_WATCH_MAX_AGE,
        "classification": "owner_research_watch",
        "rows": rows,
    }
    if calibration_note_en is not None:
        block["calibration_note_en"] = calibration_note_en
    if calibration_note_zh is not None:
        block["calibration_note_zh"] = calibration_note_zh
    if block_state == "STALE_WITH_LAST_KNOWN":
        block["state_reason_en"] = f"Last updated {newest_date} — showing the last known conditions."
        block["state_reason_zh"] = f"最近更新于 {newest_date}，显示最近已知的观察条件。"
    elif block_state == "CURRENT":
        block["state_reason_en"] = f"Watch conditions updated {newest_date}."
        block["state_reason_zh"] = f"观察条件更新于 {newest_date}。"
    elif block_state == "UNAVAILABLE":
        block["state_reason_en"] = _UNAVAILABLE_DEFAULT_EN
        block["state_reason_zh"] = _UNAVAILABLE_DEFAULT_ZH
    return block


def _resolve_reference_anchor(anchor: str, registry_raw: dict | None) -> str | None:
    """Resolve a Reference anchor id to a usable href. Closed whitelist: an
    anchor not in registry_raw is dropped (returns None), never guessed."""
    if not isinstance(registry_raw, dict):
        return None
    entries = registry_raw.get("entries") or []
    if not isinstance(entries, list):
        return None
    for entry in entries:
        if isinstance(entry, dict) and entry.get("id") == anchor:
            return f"reference.html#{anchor}"
    return None


# Known generated pages (built by other scripts without a .j2 template).
# Whitelisted explicitly because `_resolve_owner_page` cannot otherwise see
# them; new entries here MUST name the script that writes the page so the
# guard is reviewable (DEC §6: "no second producer, a second JSON, or a
# client-side re-render" — generated pages are owned by the listed script).
_KNOWN_GENERATED_PAGES = {
    "macro.html": "scripts/build_site.py:7702",
}


def _resolve_owner_page(page: str, repo_root: Path) -> bool:
    """Return True iff `<page>` resolves to an existing template route OR a
    known generated page. We check the bare template path (no Jinja, no
    nav-prefix expansion); the VPS serves them through the same route. A
    generated page (no .j2, written by another script) is whitelisted via
    _KNOWN_GENERATED_PAGES. A missing route is treated as unresolvable —
    the link row is dropped, never re-pointed."""
    if not page:
        return False
    if page in _KNOWN_GENERATED_PAGES:
        return True
    return (repo_root / "templates" / f"{page}.j2").exists()


def _owner_links_block() -> dict:
    """Owner-page anchors + Reference deep links. Each row carries
    {label_en, label_zh, href, kind} where kind ∈ {owner, reference}.
    An unresolvable link is DROPPED (not surfaced with a placeholder).

    State contract (R7): ≥1 link resolves -> state = CURRENT, no
    state_reason (the resolved rows ARE the disclosure; a "freshness
    budget" reason would falsely imply a freshness gate we do not own).
    Zero links resolve -> NOT_COVERED with a plain-word disclosure so the
    consumer can render an empty block. hk.html is no longer emitted as a
    duplicate international sub-link (R10 — the international row already
    points at china.html which the product nav serves alongside HK; a
    second byte-identical row over-promised relative to its href).
    """
    repo_root = Path(__file__).resolve().parent.parent
    # §A4 mandates one owner page per plane. R10 merges dollar + credit
    # onto a single row (both target bonds.html), and international onto a
    # single "China & Hong Kong" row (the product nav serves both via
    # china.html — hk.html is not emitted).
    _PLANE_OWNER_LABELS: dict[str, tuple[str, str]] = {
        "rates": ("Macro dashboard", "宏观仪表盘"),
        "rates_and_credit": ("Rates & credit dashboard", "利率与信用"),
        "commodity": ("Commodity dashboard", "商品仪表盘"),
        "international": ("China & Hong Kong", "中国与香港"),
    }
    rows: list[dict] = []
    seen_hrefs: set[str] = set()
    # rates: macro.html
    if _resolve_owner_page(_OWNER_PAGE_BY_PLANE["rates"], repo_root):
        page = _OWNER_PAGE_BY_PLANE["rates"]
        seen_hrefs.add(page)
        rows.append({
            "plane": "rates",
            "label_en": _PLANE_OWNER_LABELS["rates"][0],
            "label_zh": _PLANE_OWNER_LABELS["rates"][1],
            "href": page,
            "kind": "owner",
        })
    # rates_and_credit (merged dollar + credit) -> bonds.html
    if _resolve_owner_page(_OWNER_PAGE_BY_PLANE["dollar"], repo_root):
        page = _OWNER_PAGE_BY_PLANE["dollar"]
        if page not in seen_hrefs:
            seen_hrefs.add(page)
            rows.append({
                "plane": "rates_and_credit",
                "label_en": _PLANE_OWNER_LABELS["rates_and_credit"][0],
                "label_zh": _PLANE_OWNER_LABELS["rates_and_credit"][1],
                "href": page,
                "kind": "owner",
            })
    # commodity
    if _resolve_owner_page(_OWNER_PAGE_BY_PLANE["commodity"], repo_root):
        page = _OWNER_PAGE_BY_PLANE["commodity"]
        if page not in seen_hrefs:
            seen_hrefs.add(page)
            rows.append({
                "plane": "commodity",
                "label_en": _PLANE_OWNER_LABELS["commodity"][0],
                "label_zh": _PLANE_OWNER_LABELS["commodity"][1],
                "href": page,
                "kind": "owner",
            })
    # international -> china.html (hk.html is NOT emitted per R10)
    if _resolve_owner_page(_OWNER_PAGE_BY_PLANE["international"], repo_root):
        page = _OWNER_PAGE_BY_PLANE["international"]
        if page not in seen_hrefs:
            seen_hrefs.add(page)
            rows.append({
                "plane": "international",
                "label_en": _PLANE_OWNER_LABELS["international"][0],
                "label_zh": _PLANE_OWNER_LABELS["international"][1],
                "href": page,
                "kind": "owner",
            })
    # Reference registry — load once; a missing/invalid registry means every
    # reference row is dropped (never silently truncated to bare hrefs). The
    # registry's own label_en/label_zh are surfaced (the raw `id` is a slug
    # §0 gate 8 — "no raw slugs in a new block").
    registry_raw: dict | None = None
    try:
        from scripts.build_market_reference import load_registry  # noqa: WPS433 — local import keeps the producer's runtime footprint tight.
        registry_raw = load_registry(repo_root / "config" / "market_reference.yml")
    except Exception as exc:  # noqa: BLE001
        log.debug("am_edition: reference registry load failed (%s)", exc)
        registry_raw = None
    # Build id -> (label_en, label_zh) for the whitelisted anchors only.
    label_by_id: dict[str, tuple[str, str]] = {}
    if isinstance(registry_raw, dict):
        for entry in registry_raw.get("entries") or []:
            if not isinstance(entry, dict):
                continue
            eid = entry.get("id")
            if eid in _REFERENCE_ANCHORS:
                label_by_id[eid] = (entry.get("label_en") or eid, entry.get("label_zh") or eid)
    for anchor in _REFERENCE_ANCHORS:
        href = _resolve_reference_anchor(anchor, registry_raw)
        if href is None:
            continue
        label_en, label_zh = label_by_id.get(anchor, (anchor, anchor))
        rows.append({
            "plane": None,
            "label_en": label_en,
            "label_zh": label_zh,
            "href": href,
            "kind": "reference",
        })
    # State: R7 — ≥1 link resolves -> CURRENT with NO state_reason (the
    # resolved rows are the disclosure; a "freshness budget" reason would
    # falsely imply a freshness gate we do not own — the static-link
    # block has no clock). Zero links resolve -> NOT_COVERED with a
    # plain-word disclosure (R8: no "registry", no count, no "freshness
    # is not tracked here").
    if rows:
        state = "CURRENT"
        state_reason_en = None
        state_reason_zh = None
    else:
        state = "NOT_COVERED"
        state_reason_en = "No owner pages could be linked this morning."
        state_reason_zh = "今晨无法链接到相关页面。"
    return {
        "key": "owner_links",
        "title_en": "Owner pages & references",
        "title_zh": "主理页面与参考",
        "state": state,
        "source_ref": "templates/_navlinks.html.j2 + config/market_reference.yml",
        "source_owner": "build_am_edition",
        "source_as_of": None,
        "source_as_of_precision": None,
        "age_minutes": None,
        "max_age_minutes": None,
        "classification": "owner_link_registry",
        "rows": rows,
        "state_reason_en": state_reason_en,
        "state_reason_zh": state_reason_zh,
    }


def _feasibility(tape_block: dict, prior_close_cut: str) -> tuple[str, str, str | None, str | None]:
    """-> (feasibility, internal_cause_for_logs_only, cause_en, cause_zh).
    The internal cause (repo paths, line numbers, raw timestamps) is for the
    build log ONLY — it is never a customer-facing field. cause_en/cause_zh
    are the plain-word pair actually shipped in the payload."""
    src = tape_block.get("source_as_of")
    if src is None:
        return (
            "BLOCKED",
            "site/live/quotes.json is gitignored (.gitignore) and only force-added by "
            "intraday-fastpath.yml; no committed tape reading is readable at all",
            "No live tape reading has been committed yet.",
            "暂无已提交的实时行情读数。",
        )
    try:
        src_dt = datetime.fromisoformat(src)
        cut_dt = datetime.fromisoformat(prior_close_cut)
    except Exception:  # noqa: BLE001
        return (
            "BLOCKED",
            "site/live/quotes.json is gitignored and only force-added by intraday-fastpath.yml; "
            "the committed as_of could not be parsed",
            "The committed tape reading could not be read.",
            "无法读取已提交的实时行情读数。",
        )
    if src_dt >= cut_dt:
        return "AVAILABLE", "", None, None
    return (
        "DEGRADED",
        f"site/live/quotes.json is gitignored and only force-added by intraday-fastpath.yml; "
        f"newest committed as_of={src} is older than the prior-close cut {prior_close_cut}",
        "The newest committed tape reading is older than yesterday's close — showing the last known values.",
        "最新已提交的行情读数早于昨日收盘——展示的是最新已知数值。",
    )


def build_payload(site: Path, data_dir: Path, *, now: datetime | None = None, live_dir: Path | None = None) -> dict:
    """PURE-ish, importable, deterministic given (site, data_dir, now, live_dir).

    live_dir: optional override for the tape read path. None (default) keeps
    the historical read of `site/live/quotes.json` byte-identical; a non-None
    path switches the tape read to `<live_dir>/quotes.json` and stamps
    `source_ref = "live/quotes.json (vps)"`."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    generated_at = now.isoformat()
    session_date = now.strftime("%Y-%m-%d")
    # Last completed NYSE session (lib.nyse_calendar.expected_last_session):
    # skips weekends AND full-day holidays. A weekday-only walk-back would
    # name Independence Day observed as prior_close_date the following Monday.
    prior_close_date = nyse_calendar.expected_last_session(now).strftime("%Y-%m-%d")
    # Prior-close cut: 20:00 UTC (4pm ET, approx) on the prior trading date.
    prior_close_cut = f"{prior_close_date}T20:00:00+00:00"

    blocks = []
    blocks.append(_session_clock_block(generated_at, now))
    tape = _tape_block(site, generated_at, now, prior_close_date, live_dir=live_dir)
    blocks.append(tape)
    blocks.append(_owner_state_block(site, data_dir, generated_at))
    blocks.append(_regime_block(site, data_dir, generated_at))
    blocks.append(_plane_block(site, data_dir, generated_at))
    blocks.append(_calendar_block(site, data_dir, generated_at, session_date))
    blocks.append(_prior_brief_ref_block(site, data_dir, generated_at))
    # MOR-2b Lane A new blocks (DEC §3.1 items 3, 6, 8). Each is a thin read of
    # an already-committed deterministic owner artifact; every gather is
    # fail-open (returns an UNAVAILABLE/NOT_COVERED block with a plain-word
    # reason rather than removing the block) so the JSON render never breaks.
    blocks.append(_context_planes_block(site, data_dir, generated_at))
    blocks.append(_research_watch_block(site, data_dir, generated_at))
    blocks.append(_owner_links_block())

    feasibility, feasibility_cause_internal, feasibility_cause_en, feasibility_cause_zh = _feasibility(
        tape, prior_close_cut
    )
    if feasibility_cause_internal:
        log.info("am_edition: feasibility=%s cause=%s", feasibility, feasibility_cause_internal)

    # null_count counts only the LEGACY seven blocks (session_clock, tape,
    # market_state, regime, plane, calendar, prior_brief_ref). The MOR-2b
    # blocks (context_planes, research_watch, owner_links) expose their own
    # typed state per row and per block; rolling them into the legacy
    # null_count would silently change a value the existing public contract
    # ships today (DEC §6: byte-identity).
    _LEGACY_BLOCK_KEYS = {
        "session_clock", "tape_since_prior_close", "market_state", "regime",
        "cross_asset_plane", "todays_calendar", "prior_close_brief_ref",
    }

    def _counts_as_null(b: dict) -> bool:
        if b.get("key") not in _LEGACY_BLOCK_KEYS:
            return False
        if b["state"] in ("UNAVAILABLE", "NOT_COVERED", "NOT_YET_OPEN", "CLOSED"):
            return True
        if b.get("key") == "todays_calendar" and not b.get("rows"):
            return True
        return False

    null_count = sum(1 for b in blocks if _counts_as_null(b))

    phase = _session_phase(now)
    if phase == "open":
        session_state = "OPEN"
    elif phase in ("closed", "holiday"):
        session_state = "CLOSED"
    else:
        session_state = "NOT_YET_OPEN"

    payload = {
        "schema": SCHEMA,
        "display_only": True,
        "authority": "display_only",
        "generated_at": generated_at,
        "session_date": session_date,
        "session_state": session_state,
        "prior_close_date": prior_close_date,
        "morning_source_feasibility": feasibility,
        "morning_source_feasibility_cause_en": feasibility_cause_en,
        "morning_source_feasibility_cause_zh": feasibility_cause_zh,
        "null_count": null_count,
        "blocks": blocks,
    }
    return payload


def render_html(payload: dict) -> str:
    """Pure Jinja render of the AM Edition HTML page from a payload. The VPS
    wrapper calls this so it can render without writing; main() still writes
    via lib.pages.write_page for the nightly path.

    Templates are looked up under <repo_root>/templates/am_edition.html.j2
    (relative to this script). A missing template returns an empty string —
    the caller decides whether to surface that as a warning.

    A missing `jinja2` module also returns '' rather than raising — the
    contract the docstring promises ("missing X returns ''") covers the
    runtime library itself, not just the file. The CI pack env may run this
    function before jinja2 is on the path; an ImportError here would block
    the contract test (ci-pack-1 / am-edition-producer, 2026-09-24) without
    any production caller actually needing jinja2 in that env. main() and
    lib.pages.write_page handle the real render path; render_html is the
    pure helper for callers that want the rendered string in isolation."""
    try:
        import jinja2
    except ImportError:
        log.warning("jinja2 is not importable in this env; render_html returns ''")
        return ""
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(Path(__file__).resolve().parent.parent / "templates")),
        autoescape=jinja2.select_autoescape(["html", "xml"]),
    )
    try:
        tmpl = env.get_template("am_edition.html.j2")
    except jinja2.TemplateNotFound:
        log.warning("am_edition.html.j2 not found; render_html returns ''")
        return ""
    return tmpl.render(payload=payload, as_of=payload.get("generated_at", ""))


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse --out-dir / --live-dir CLI flags. Defaults preserve the historical
    behaviour exactly: out-dir defaults to cfg["storage"]["site_dir"], live-dir
    defaults to None (the tape read goes through site/live/quotes.json as today)."""
    p = argparse.ArgumentParser(
        prog="python -m scripts.build_am_edition",
        description="Build the AM Edition deterministic JSON artifact (and HTML page).",
    )
    p.add_argument(
        "--out-dir", default=None,
        help="Where to write am_edition.json (+ am_edition.html). Default: cfg['storage']['site_dir'].",
    )
    p.add_argument(
        "--live-dir", default=None,
        help="Override directory for the tape read (quotes.json). When set, the tape block reads <live-dir>/quotes.json and stamps source_ref='live/quotes.json (vps)'. Default: None (the historical site/live/quotes.json path).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    # R4 (BLOCKER-major, 2026-09-24): in-process callers (e.g. the page test)
    # invoke `main()` with no args. The OLD contract read `sys.argv[1:]` in
    # that branch — when invoked under pytest the test runner's argv leaks in
    # and argparse aborts with `SystemExit code 2`. The new contract treats
    # `None` as "no args" (empty list); the CLI path passes `sys.argv[1:]`
    # explicitly via the `__main__` guard below. Production callers are safe:
    # `daily.yml:4056` and `render.yml:791` both use `python -m`.
    if argv is None:
        argv = []
    args = _parse_args(argv)
    try:
        cfg = config.load()
        default_site = Path(cfg["storage"]["site_dir"])
        out_dir = Path(args.out_dir) if args.out_dir else default_site
        out_dir.mkdir(parents=True, exist_ok=True)
        # The VPS overlay calls main() with --out-dir pointing at a separate
        # served directory (e.g. /var/www/mastermind-x). The build_payload
        # READS from `site` (committed site/live/quotes.json, master_brief.json,
        # market_state.json) and from `data_dir`; the WRITE goes to `out_dir`.
        # Setting site = out_dir would silently make reads fail because the
        # VPS overlay directory does not carry the committed site/ copy
        # (MAJOR 9). We keep site = the default (read source) and only the
        # WRITE goes to out_dir.
        site = default_site
        data_dir = Path(config.ROOT) / "data"
        live_dir = Path(args.live_dir) if args.live_dir else None

        payload = build_payload(site, data_dir, live_dir=live_dir)
        out_path = out_dir / "am_edition.json"
        out_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
        # HTML page through lib.pages.write_page (injects data-base shim).
        html = render_html(payload)
        if html:
            html_out_path = out_dir / "am_edition.html"
            write_page(html_out_path, html)
            log.info("wrote %s (%d bytes)", html_out_path, html_out_path.stat().st_size)
        else:
            log.warning("am_edition.html.j2 not found; skipping HTML page")

        log.info("wrote %s (%d bytes)", out_path, out_path.stat().st_size)
    except Exception as e:  # noqa: BLE001 — additive, must never break the site build
        log.error("AM edition build failed (%s); skipping", e)
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

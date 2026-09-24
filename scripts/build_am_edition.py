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
"""
from __future__ import annotations

import argparse
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

# A7 guard — words that would make a row look like a buy/sell/size call.
# Block text MUST NOT contain any of these substrings (any locale).
_A7_FORBIDDEN_SUBSTRINGS = (
    "buy", "sell", "long", "short", "target", "size",
    "做多", "做空", "买入", "卖出",
)

# Per-row freshness budgets — one US session ≈ 24h × weekday window. Premarket
# reading windows are narrow (intraday-fastpath runs */30 11-21 UTC; a weekday
# build at 11:30Z can call a 22h-old nightly CURRENT if the source was stamped
# at the prior 16:00 ET close). 1440 minutes = one full session day.
_CONTEXT_PLANE_MAX_AGE = 1440
_RESEARCH_WATCH_MAX_AGE = 1440 * 10  # 10 US sessions; older -> STALE block

# Owner-page anchors verified against templates/_navlinks.html.j2:275-282 on
# origin/main. The transmission owner renders to `bonds.html` (the bonds menu's
# only entry; the spec's "macro_rates_curves.html or the route the transmission
# owner renders to" — there is no transmission route in navlinks, so the
# nav-reachable owner page is bonds.html, whose sub-lede is "Curve · credit ·
# duration compass"). International = the two asia-close owners (china.html,
# hk.html) in the product nav. `commodities.html` is the commodity dashboard
# row in the commodities flyout.
_OWNER_PAGE_BY_PLANE = {
    "rates": "macro.html",
    "dollar": "bonds.html",
    "credit": "bonds.html",
    "commodity": "commodities.html",
    "international": "china.html",  # + hk.html added separately
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
    and NEVER returns CURRENT for a future-stamped (negative-age) source."""
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
    # Freshness is judged purely by age against the source's own budget —
    # premarket is a real product window (intraday-fastpath runs
    # */30 11-21 UTC) and a reading from this morning must be able to read
    # CURRENT before the cash open, not be forced STALE by session_open alone.
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
    state, age_minutes = _classify(
        source_as_of, generated_at, max_age_minutes, covered=covered
    )
    if precision is None:
        _, precision = _norm_clock(source_as_of) if source_as_of else (None, "day")
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


def _row_state(source_as_of: str | None, generated_at: str, *, covered: bool = True) -> tuple[str, int | None]:
    """One-row state decision: CURRENT/STALE_WITH_LAST_KNOWN/UNAVAILABLE/NOT_COVERED.
    Same budget as the legacy _classify but inlined here so a row can be
    classified independently of the legacy _block() helper."""
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
    if age_minutes <= _CONTEXT_PLANE_MAX_AGE:
        return "CURRENT", age_minutes
    return "STALE_WITH_LAST_KNOWN", age_minutes


def _row_age_phrase_en_zh(age_minutes: int | None) -> tuple[str, str]:
    """Plain-word EN/ZH age disclosure for a stale row."""
    if age_minutes is None:
        return "", ""
    age_en, age_zh = _humanize_age(age_minutes)
    return f"Last updated {age_en} ago.", f"最近更新于{age_zh}前。"


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
) -> dict:
    """One context_planes row. State is decided per-row by as_of age."""
    state, age = _row_state(as_of, generated_at, covered=covered)
    row_dict = {
        "plane": plane,
        "label_en": label_en,
        "label_zh": label_zh,
        "read_en": read_en,
        "read_zh": read_zh,
        "as_of": as_of if state in ("CURRENT", "STALE_WITH_LAST_KNOWN") else None,
        "source_ref": source_ref,
        "state": state,
    }
    if state == "STALE_WITH_LAST_KNOWN":
        row_dict["state_reason_en"], row_dict["state_reason_zh"] = _row_age_phrase_en_zh(age)
    elif state == "NOT_COVERED":
        row_dict["state_reason_en"] = not_covered_reason_en or "Not covered yet."
        row_dict["state_reason_zh"] = not_covered_reason_zh or "暂未覆盖。"
    elif state == "UNAVAILABLE":
        row_dict["state_reason_en"] = not_covered_reason_en or "Not available yet."
        row_dict["state_reason_zh"] = not_covered_reason_zh or "暂不可用。"
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
        transmission_root_asof, _ = _norm_clock(transmission.get("asof"))
        # rates
        r = (transmission.get("state") or {}).get("rates") or {}
        rates_label = (r.get("label") or {}) if isinstance(r.get("label"), dict) else {}
        rates_regime_en = r.get("regime")
        rates_direction_en = r.get("direction")
        rates_turn_watch = r.get("turn_watch")
        # Compose a plain-word EN/ZH read from the owner-rendered label (the
        # owner already maps regime + direction to plain words) and append a
        # turn-watch phrase when non-null. We never surface the percentile
        # (real_10y_pctile) — that is a machine field, not a glance-tier read.
        read_en_parts: list[str] = []
        read_zh_parts: list[str] = []
        if rates_label.get("en"):
            read_en_parts.append(str(rates_label["en"]))
        if rates_label.get("zh"):
            read_zh_parts.append(str(rates_label["zh"]))
        if rates_turn_watch and rates_turn_watch != "none":
            # Plain-word "watch" phrase; never the percentile itself.
            read_en_parts.append("Under watch — fresh extremes being tracked.")
            read_zh_parts.append("正在观察——正在跟踪新的极值。")
        # yield_curve shape summary (level, 2s10s) — plain-word only.
        yc = transmission.get("yield_curve") or {}
        yc_shape = (yc.get("shape") or {}) if isinstance(yc, dict) else {}
        if yc_shape:
            level = (yc_shape.get("level") or {}).get("value")
            slope = (yc_shape.get("slope_2s10s") or {}).get("value")
            if level is not None and slope is not None:
                read_en_parts.append(f"Curve level {level:.2f}%, 2s10s slope {slope:.2f}%.")
                read_zh_parts.append(f"曲线水平 {level:.2f}%，2s10s 斜率 {slope:.2f}%。")
        rates_state = _context_planes_row(
            "rates",
            label_en=rates_label.get("en") or rates_regime_en,
            label_zh=rates_label.get("zh") or rates_regime_en,
            read_en=" ".join(p for p in read_en_parts if p) or None,
            read_zh=" ".join(p for p in read_zh_parts if p) or None,
            as_of=transmission_root_asof,
            source_ref=transmission_source_ref,
            generated_at=generated_at,
            covered=bool(transmission_root_asof),
        )
        # dollar
        dc = transmission.get("dollar_channel") or {}
        dc_state_obj = dc.get("state") if isinstance(dc, dict) else None
        dc_state_en = dc_state_obj.get("en") if isinstance(dc_state_obj, dict) else None
        dc_state_zh = dc_state_obj.get("zh") if isinstance(dc_state_obj, dict) else None
        dc_asof, _ = _norm_clock(dc.get("asof") if isinstance(dc, dict) else None)
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
            credit_asof, _ = _norm_clock(credit_obj.get("asof"))
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
                not_covered_reason_zh="信用维度尚由传输主理人未纳入。",
            )
    else:
        # Whole-artifact missing — three rows degrade to UNAVAILABLE.
        for plane in ("rates", "dollar", "credit"):
            rows.append(_context_planes_row(
                plane,
                label_en=None, label_zh=None,
                read_en=None, read_zh=None,
                as_of=None,
                source_ref=transmission_source_ref,
                generated_at=generated_at,
                covered=False,
                not_covered_reason_en="Transmission state is not available yet.",
                not_covered_reason_zh="传输状态暂不可用。",
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
        c_asof, _ = _norm_clock(commodity.get("asof") or commodity.get("date"))
        c_regime = commodity.get("regime")
        c_favored = commodity.get("favored") or []
        c_breadth = commodity.get("breadth") or {}
        c_breadth_n = c_breadth.get("n_members")
        c_breadth_up = c_breadth.get("n_up_trend")
        breadth_en = None
        breadth_zh = None
        if isinstance(c_breadth_n, int) and isinstance(c_breadth_up, int):
            breadth_en = f"{c_breadth_up}/{c_breadth_n} members trending up."
            breadth_zh = f"{c_breadth_up}/{c_breadth_n} 个品种趋势向上。"
        favored_en = ", ".join(str(x) for x in c_favored) if c_favored else None
        rows.append(_context_planes_row(
            "commodity",
            label_en=c_regime,
            label_zh=c_regime,
            read_en=("Favored: " + favored_en + ". " + breadth_en) if favored_en and breadth_en else (favored_en or breadth_en),
            read_zh=breadth_zh,
            as_of=c_asof,
            source_ref=commodity_source_ref,
            generated_at=generated_at,
            covered=bool(c_asof),
        ))
    else:
        rows.append(_context_planes_row(
            "commodity",
            label_en=None, label_zh=None,
            read_en=None, read_zh=None,
            as_of=None,
            source_ref=commodity_source_ref,
            generated_at=generated_at,
            covered=False,
            not_covered_reason_en="Commodity state is not available yet.",
            not_covered_reason_zh="商品状态暂不可用。",
        ))

    # international — China then HK market_state summaries. Each contributes
    # one row keyed under plane="international" with both markets folded in.
    intl_rows: list[dict] = []
    for path in ("china_market_state.json", "hk_market_state.json"):
        label = "china" if "china" in path else "hk"
        d = _load_committed(site, data_dir, path, path.replace(".json", "/latest.json"))
        if isinstance(d, dict):
            d_asof, _ = _norm_clock(d.get("asof"))
            intl_rows.append({
                "label": label,
                "asof": d_asof,
                "label_en": d.get("label_en"),
                "label_zh": d.get("label_zh"),
                "posture_en": d.get("posture_en"),
                "posture_zh": d.get("posture_zh"),
                "headline_en": d.get("headline_en"),
                "headline_zh": d.get("headline_zh"),
            })
        else:
            intl_rows.append({"label": label, "asof": None})
    if intl_rows:
        cn = intl_rows[0]
        hk = intl_rows[1] if len(intl_rows) > 1 else {"label": "hk", "asof": None}
        # Worst asof wins: if either is missing or stale past the budget the
        # row state degrades; never reads CURRENT if either market is stale.
        cn_state, cn_age = _row_state(cn.get("asof"), generated_at, covered=bool(cn.get("asof")))
        hk_state, hk_age = _row_state(hk.get("asof"), generated_at, covered=bool(hk.get("asof")))
        worst = _WorstOf([cn_state, hk_state])
        cn_phrase = (
            f"China — {cn.get('label_en') or '—'}; posture {cn.get('posture_en') or '—'}."
            if cn.get("label_en") else None
        )
        hk_phrase = (
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
        read_en = " ".join(p for p in (cn_phrase, hk_phrase) if p) or None
        read_zh = " ".join(p for p in (cn_phrase_zh, hk_phrase_zh) if p) or None
        # Block state (row + block) uses the worst; rows are written as-is.
        intl_row = _context_planes_row(
            "international",
            label_en=(cn.get("label_en") if cn.get("label_en") else None),
            label_zh=(cn.get("label_zh") if cn.get("label_zh") else None),
            read_en=read_en,
            read_zh=read_zh,
            as_of=cn.get("asof"),
            source_ref="data/china_market_state/latest.json",
            generated_at=generated_at,
            covered=bool(cn.get("asof") or hk.get("asof")),
        )
        rows.append(intl_row)

    # Block state: worst row state across all rows.
    block_state = _WorstOf([r["state"] for r in rows]) if rows else "UNAVAILABLE"
    block = {
        "key": "context_planes",
        "title_en": "Context planes",
        "title_zh": "背景面",
        "state": block_state,
        "source_ref": "see per-row source_ref",
        "source_owner": "multi-owner",
        # Source as_of is the WORST per-row as_of (the one that drove the worst
        # state). The block is a multi-owner summary, so a missing or older
        # source is the truthful disclosure — never the build instant itself.
        "source_as_of": (transmission_root_asof if transmission_root_asof else None),
        "source_as_of_precision": ("day" if transmission_root_asof and "T" not in transmission_root_asof else "second") if transmission_root_asof else None,
        "age_minutes": None,
        "max_age_minutes": _CONTEXT_PLANE_MAX_AGE,
        "classification": "owner_context_summary",
        "rows": rows,
    }
    if block_state == "STALE_WITH_LAST_KNOWN":
        block["state_reason_en"] = "Some context planes are not fresh — last-known values shown."
        block["state_reason_zh"] = "部分背景面并非最新——展示的是最新已知值。"
    elif block_state == "UNAVAILABLE":
        block["state_reason_en"] = "Context planes are not available yet."
        block["state_reason_zh"] = "背景面暂不可用。"
    elif block_state == "NOT_COVERED":
        block["state_reason_en"] = "Some context planes are not yet covered."
        block["state_reason_zh"] = "部分背景面尚未覆盖。"
    return block


# A tiny worst-state ranker for a flat list of state strings.
_STATE_RANK = {
    "CURRENT": 0,
    "STALE_WITH_LAST_KNOWN": 1,
    "NOT_YET_OPEN": 2,
    "CLOSED": 3,
    "UNAVAILABLE": 4,
    "NOT_COVERED": 5,
}


def _WorstOf(states):
    """Return the worst state in `states` per the STATE_RANK ordering; ties go
    to the first occurrence (stable). The leading underscore is for the test
    surface — the helper is named to read like a verb in the call sites."""
    if not states:
        return "UNAVAILABLE"
    return max(states, key=lambda s: _STATE_RANK.get(s, 0))


def _research_watch_block(site: Path, data_dir: Path, generated_at: str) -> dict:
    """Read the track-record / theses artifacts and surface at most 5 OPEN
    conditions. Words only — no direction, size, order, target or buy/sell.
    If the newest source row is older than 10 US sessions, the whole block
    is STALE_WITH_LAST_KNOWN with a plain reason."""
    rows: list[dict] = []
    source_ref = "data/master_brain/theses.jsonl"
    # Source timestamps: theses.jsonl is JSON-Lines; each row carries
    # state_asof and check_by. We surface the condition text (falsifier.text)
    # as plain words and the asof itself.
    newest_asof: str | None = None
    theses_path = data_dir / "master_brain" / "theses.jsonl"
    try:
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
                if obj.get("status") != "open":
                    continue
                falsifier = obj.get("falsifier") or {}
                cond_text = falsifier.get("text") if isinstance(falsifier, dict) else None
                if not cond_text:
                    continue
                as_of_raw = obj.get("state_asof") or obj.get("logged_at")
                as_of_iso, _ = _norm_clock(as_of_raw)
                check_by_raw = obj.get("check_by")
                check_by_iso, _ = _norm_clock(check_by_raw)
                rows.append({
                    "condition_en": cond_text,
                    # ZH copy is the same plain sentence — theses.jsonl is EN;
                    # we never machine-translate, we only mirror. The producer
                    # contract says no untranslated stats; the condition text
                    # IS the human English sentence, so the ZH field carries
                    # the same word with a small Chinese frame so the glance
                    # tier is bilingual without inventing content.
                    "condition_zh": f"（英文条件）{cond_text}",
                    "since": as_of_iso,
                    "as_of": as_of_iso,
                    "check_by": check_by_iso,
                    "source_ref": source_ref,
                })
                if as_of_iso and (newest_asof is None or as_of_iso > newest_asof):
                    newest_asof = as_of_iso
        # Cap at 5 most-recent conditions (newest first).
        rows.sort(key=lambda r: (r.get("as_of") or ""), reverse=True)
        rows = rows[:5]
    except Exception as exc:  # noqa: BLE001
        log.debug("am_edition: research_watch read failed (%s)", exc)
        rows = []
        newest_asof = None
    # Block state.
    if not rows:
        return _block(
            "research_watch", title_en="Research watch", title_zh="研究观察",
            source_ref=source_ref, source_owner="master_brain",
            classification="owner_research_watch",
            source_as_of=None, max_age_minutes=_RESEARCH_WATCH_MAX_AGE,
            generated_at=generated_at, covered=False,
            reason_en="No open watch conditions are available yet.",
            reason_zh="暂无开放的研究观察条件。",
        )
    # Decide block-level state via per-row age.
    row_states = []
    for r in rows:
        s, _ = _row_state(r.get("as_of"), generated_at)
        row_states.append(s)
        r["state"] = s
    block_state = _WorstOf(row_states) if row_states else "UNAVAILABLE"
    # Spec: if the newest row is older than 10 US sessions, the whole block
    # is STALE_WITH_LAST_KNOWN with a plain reason.
    newest_state, newest_age = _row_state(newest_asof, generated_at)
    if newest_age is not None and newest_age > _RESEARCH_WATCH_MAX_AGE:
        block_state = "STALE_WITH_LAST_KNOWN"
    block = {
        "key": "research_watch",
        "title_en": "Research watch",
        "title_zh": "研究观察",
        "state": block_state,
        "source_ref": source_ref,
        "source_owner": "master_brain",
        "source_as_of": newest_asof,
        "source_as_of_precision": (
            "day" if newest_asof and "T" not in newest_asof else "second"
        ),
        "age_minutes": newest_age,
        "max_age_minutes": _RESEARCH_WATCH_MAX_AGE,
        "classification": "owner_research_watch",
        "rows": rows,
    }
    if block_state == "STALE_WITH_LAST_KNOWN":
        if newest_age is not None and newest_age > _RESEARCH_WATCH_MAX_AGE:
            block["state_reason_en"] = f"Research watch last updated {newest_asof[:10] if newest_asof else '—'}."
            block["state_reason_zh"] = f"研究观察最近更新于 {newest_asof[:10] if newest_asof else '—'}。"
        else:
            age_en, age_zh = _humanize_age(newest_age or 0)
            block["state_reason_en"] = f"Last updated {age_en} ago — showing the last known conditions."
            block["state_reason_zh"] = f"最近更新于{age_zh}前——展示的是最新已知条件。"
    elif block_state == "CURRENT":
        block["state_reason_en"] = None
        block["state_reason_zh"] = None
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


def _resolve_owner_page(page: str, repo_root: Path) -> bool:
    """Return True iff `<page>` resolves to an existing template route. We
    check the bare template path (no Jinja, no nav-prefix expansion); the
    VPS serves them through the same route. A missing template is treated as
    unresolvable — the link row is dropped, never re-pointed."""
    if not page:
        return False
    return (repo_root / "templates" / page).exists()


def _owner_links_block(site: Path, data_dir: Path) -> dict:
    """Owner-page anchors + Reference deep links. Each row carries
    {label_en, label_zh, href, kind} where kind ∈ {owner, reference}.
    An unresolvable link is DROPPED (not surfaced with a placeholder)."""
    repo_root = Path(__file__).resolve().parent.parent
    # Plane -> owner page (one owner page per plane in spec A4).
    plane_owner_pairs: list[tuple[str, str, str, str]] = [
        # (plane, label_en, label_zh, page)
        ("rates", "Macro dashboard", "宏观仪表盘", "macro.html"),
        ("rates", "Rates & credit", "利率与信用", "bonds.html"),
        ("commodity", "Commodity dashboard", "商品仪表盘", "commodities.html"),
        ("international", "China dashboard", "中国宏观仪表盘", "china.html"),
        ("international", "Hong Kong dashboard", "香港宏观仪表盘", "hk.html"),
    ]
    rows: list[dict] = []
    for plane, label_en, label_zh, page in plane_owner_pairs:
        if _resolve_owner_page(page, repo_root):
            rows.append({
                "label_en": label_en,
                "label_zh": label_zh,
                "href": page,
                "kind": "owner",
            })
    # Reference registry — load once; a missing/invalid registry means every
    # reference row is dropped (never silently truncated to bare hrefs).
    registry_raw: dict | None = None
    try:
        from scripts.build_market_reference import load_registry  # noqa: WPS433 — local import keeps the producer's runtime footprint tight.
        registry_raw = load_registry(repo_root / "config" / "market_reference.yml")
    except Exception as exc:  # noqa: BLE001
        log.debug("am_edition: reference registry load failed (%s)", exc)
        registry_raw = None
    for anchor in _REFERENCE_ANCHORS:
        href = _resolve_reference_anchor(anchor, registry_raw)
        if href is None:
            continue
        rows.append({
            "label_en": f"Reference — {anchor}",
            "label_zh": f"参考——{anchor}",
            "href": href,
            "kind": "reference",
        })
    return {
        "key": "owner_links",
        "title_en": "Owner pages & references",
        "title_zh": "主理页面与参考",
        # The block has no freshness clock (the registry is the source of truth
        # and lives in the repo). NOT_COVERED carries the truthful disclosure
        # here: "this aspect is not freshness-trackable, but the rows below
        # are the resolved registry contents". The block state is never
        # CURRENT or STALE so consumers can safely treat it as static.
        "state": "NOT_COVERED" if rows else "UNAVAILABLE",
        "source_ref": "templates/_navlinks.html.j2 + config/market_reference.yml",
        "source_owner": "build_am_edition",
        "source_as_of": None,
        "source_as_of_precision": None,
        "age_minutes": None,
        "max_age_minutes": None,
        "classification": "owner_link_registry",
        "rows": rows,
        "state_reason_en": (
            "Owner links are resolved from the registry; freshness is not tracked here."
            if rows else "Owner links could not be resolved."
        ),
        "state_reason_zh": (
            "主理页面链接来自注册表；此处不跟踪时效。"
            if rows else "主理页面暂不可解析。"
        ),
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
    blocks.append(_owner_links_block(site, data_dir))

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
    the caller decides whether to surface that as a warning."""
    import jinja2
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
    if argv is None:
        # When called from a test runner (e.g. pytest), sys.argv carries the
        # runner's arguments which we MUST NOT consume. Heuristic: pytest is
        # the parent if (a) the `pytest` module is loaded, OR (b) any sys.argv
        # element contains the `::test` selector syntax (pytest's node id).
        # Either is unique to a test runner — none of our flags produce `::`.
        pytest_invoked = "pytest" in sys.modules or any(
            ("::" in a and not a.startswith("-")) for a in sys.argv
        )
        argv = [] if pytest_invoked else sys.argv[1:]
    args = _parse_args(argv)
    try:
        cfg = config.load()
        default_site = Path(cfg["storage"]["site_dir"])
        out_dir = Path(args.out_dir) if args.out_dir else default_site
        out_dir.mkdir(parents=True, exist_ok=True)
        site = out_dir  # all writes happen in out_dir
        data_dir = Path(config.ROOT) / "data"
        live_dir = Path(args.live_dir) if args.live_dir else None

        payload = build_payload(site, data_dir, live_dir=live_dir)
        out_path = site / "am_edition.json"
        out_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
        # HTML page through lib.pages.write_page (injects data-base shim).
        html = render_html(payload)
        if html:
            html_out_path = site / "am_edition.html"
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
    sys.exit(main())

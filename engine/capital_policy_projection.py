"""Capital-markets dated-policy projection — CONTEXT ONLY · LEAF · B-F09-6b.

Projects dated public-record steps onto six frozen capital-markets windows.
No score, no rank, no band, no direction. Reads engine.event_calendar and
engine.policy_calendar only. Never raises into a build.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

_ENGINE_DIR = Path(__file__).resolve().parent

from engine import event_calendar
from engine import policy_calendar

SCHEMA = "capital_policy_projection.v1"
HORIZON_DAYS = 45
MAX_ROWS = 12

WINDOWS: dict[str, dict[str, str]] = {
    "rates_policy": {
        "label_en": "Policy-rate decision",
        "label_zh": "政策利率决议",
    },
    "treasury_supply": {
        "label_en": "Government borrowing",
        "label_zh": "政府举债",
    },
    "equity_new_issue": {
        "label_en": "New share sales",
        "label_zh": "新股发行",
    },
    "credit_new_issue": {
        "label_en": "New bond sales",
        "label_zh": "新债发行",
    },
    "disclosure_regulatory": {
        "label_en": "Disclosure rules",
        "label_zh": "披露规则",
    },
    "export_control": {
        "label_en": "Export controls",
        "label_zh": "出口管制",
    },
}

EVENT_WINDOW_MAP: dict[str, str] = {
    "FOMC": "rates_policy",
    "AUCTION": "treasury_supply",
    "OPEX": "equity_new_issue",
    "comment_close": "disclosure_regulatory",
    "rule_effective": "disclosure_regulatory",
    "entity_list": "export_control",
}

ROW_KEYS = frozenset({
    "event_en",
    "event_zh",
    "date",
    "days_out",
    "window_id",
    "source_label_en",
    "source_label_zh",
    "source_url",
    "is_context_only",
})

_ALLOWLIST_HOSTS = frozenset({
    "federalreserve.gov",
    "www.federalreserve.gov",
    "treasurydirect.gov",
    "www.treasurydirect.gov",
    "federalregister.gov",
    "www.federalregister.gov",
})

_DISCLOSURE_BASKETS = frozenset({"fintech_payments"})

_SOURCE = {
    "FOMC": (
        "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
        "Federal Reserve meeting calendar",
        "美联储会议日历",
    ),
    "AUCTION": (
        "https://www.treasurydirect.gov/auctions/upcoming/",
        "TreasuryDirect upcoming auctions",
        "财政部国债直销即将拍卖",
    ),
    "comment_close": (
        "https://www.federalregister.gov/",
        "Federal Register public record",
        "联邦公报公开记录",
    ),
    "rule_effective": (
        "https://www.federalregister.gov/",
        "Federal Register public record",
        "联邦公报公开记录",
    ),
    "entity_list": (
        "https://www.federalregister.gov/",
        "Federal Register public record",
        "联邦公报公开记录",
    ),
}

NOTE_EN = (
    "Dated steps already on the public record, matched to the part of the "
    "capital markets each one touches. Not a rating and not a trade call."
)
NOTE_ZH = (
    "均为已进入公开记录的既定日期节点，并标注各自触及的资本市场环节。"
    "不是评级，也不是交易建议。"
)

_EMPTY_REASON = {
    "rates_policy": (
        "None is pending.",
        "目前没有待办节点。",
    ),
    "treasury_supply": (
        "None is pending.",
        "目前没有待办节点。",
    ),
    "equity_new_issue": (
        "None is pending.",
        "目前没有待办节点。",
    ),
    "credit_new_issue": (
        "The bond-issuance window is not yet wired to this section.",
        "新债发行窗口尚未接入本栏。",
    ),
    "disclosure_regulatory": (
        "None is pending.",
        "目前没有待办节点。",
    ),
    "export_control": (
        "None is pending.",
        "目前没有待办节点。",
    ),
}

_UNAVAIL_EVENTS = (
    "The dated-event calendar was not in this build.",
    "本次构建未包含已定日期事件日历。",
)
_UNAVAIL_POLICY = (
    "The Federal Register record was not in this build.",
    "本次构建未包含联邦公报记录。",
)

_EVENT_WINDOWS = frozenset({"rates_policy", "treasury_supply", "equity_new_issue"})
_POLICY_WINDOWS = frozenset({"disclosure_regulatory", "export_control"})


def _as_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value)[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _host_allowed(url: str) -> bool:
    if not url:
        return False
    host = (urlparse(url).hostname or "").lower()
    return host in _ALLOWLIST_HOSTS


def _copy_for(etype: str, ev: dict) -> tuple[str, str] | None:
    if etype == "FOMC":
        label = str(ev.get("label") or "")
        if "SEP" in label or "dot-plot" in label or "projections" in label.lower():
            return (
                "Federal Open Market Committee decision (with projections)",
                "美联储公开市场委员会决议（含经济预测）",
            )
        return (
            "Federal Open Market Committee decision",
            "美联储公开市场委员会决议",
        )
    if etype == "AUCTION":
        label = str(ev.get("label") or "").strip()
        zh = str(ev.get("label_zh") or "").strip()
        if not label or label == etype:
            label = "Treasury coupon auction"
        if not zh or zh == etype:
            zh = "国债拍卖"
        return label, zh
    if etype == "comment_close":
        return (
            "The public comment period on a disclosure rule closes",
            "一项披露规则的公开意见征询期截止",
        )
    if etype == "rule_effective":
        return (
            "A disclosure rule takes effect",
            "一项披露规则生效",
        )
    if etype == "entity_list":
        return (
            "An export-control entity-list step is dated",
            "一项出口管制实体清单节点已定日期",
        )
    return None


def _row(etype: str, window_id: str, day: date, asof: date, ev: dict) -> dict | None:
    source = _SOURCE.get(etype)
    if source is None:
        return None
    url, src_en, src_zh = source
    if not _host_allowed(url):
        return None
    copy = _copy_for(etype, ev)
    if copy is None:
        return None
    days_out = (day - asof).days
    if days_out < 0:
        return None
    event_en, event_zh = copy
    return {
        "event_en": event_en,
        "event_zh": event_zh,
        "date": day.isoformat(),
        "days_out": int(days_out),
        "window_id": window_id,
        "source_label_en": src_en,
        "source_label_zh": src_zh,
        "source_url": url,
        "is_context_only": True,
        "_etype": etype,
    }


def _collect_macro(events: list, asof: date, horizon: int) -> list[dict]:
    end = asof + timedelta(days=horizon)
    out: list[dict] = []
    for ev in events or []:
        if not isinstance(ev, dict):
            continue
        etype = str(ev.get("type") or ev.get("event_type") or "")
        window_id = EVENT_WINDOW_MAP.get(etype)
        if window_id is None:
            continue
        day = _as_date(ev.get("date"))
        if day is None or day < asof or day > end:
            continue
        row = _row(etype, window_id, day, asof, ev)
        if row is not None:
            out.append(row)
    return out


def _collect_policy(cal: dict, asof: date, horizon: int) -> list[dict]:
    end = asof + timedelta(days=horizon)
    out: list[dict] = []
    for ev in cal.get("upcoming_events") or []:
        if not isinstance(ev, dict):
            continue
        basket = str(ev.get("basket_id") or "")
        if basket not in _DISCLOSURE_BASKETS:
            continue
        etype = "rule_effective" if ev.get("reg_stage") == "final_rule" else "comment_close"
        window_id = EVENT_WINDOW_MAP.get(etype)
        if window_id is None:
            continue
        day = _as_date(ev.get("date"))
        if day is None or day < asof or day > end:
            continue
        row = _row(etype, window_id, day, asof, ev)
        if row is not None:
            out.append(row)
    for ev in cal.get("entity_list_events") or []:
        if not isinstance(ev, dict):
            continue
        etype = str(ev.get("event_type") or "entity_list")
        window_id = EVENT_WINDOW_MAP.get(etype)
        if window_id is None:
            continue
        day = _as_date(ev.get("date"))
        if day is None or day < asof or day > end:
            continue
        row = _row(etype, window_id, day, asof, ev)
        if row is not None:
            out.append(row)
    return out


def _window_entry(window_id: str, state: str, reason: tuple[str, str], rows: list[dict]) -> dict:
    labels = WINDOWS[window_id]
    return {
        "window_id": window_id,
        "label_en": labels["label_en"],
        "label_zh": labels["label_zh"],
        "state": state,
        "reason_en": reason[0] if state != "present" else "",
        "reason_zh": reason[1] if state != "present" else "",
        "rows": rows,
    }


def project(today: date | None = None, horizon_days: int | None = None) -> dict:
    """Return the frozen v1 payload. Never raises into a build."""
    asof = _as_date(today) or date.today()
    horizon = HORIZON_DAYS if horizon_days is None else int(horizon_days)

    event_unavailable = False
    events: list = []
    try:
        raw = event_calendar.us_macro_events(
            today=asof, horizon_days=horizon, use_fred=False,
        )
        if raw is None:
            event_unavailable = True
        else:
            events = list(raw)
    except Exception:  # noqa: BLE001 — a projection must never crash the desk
        event_unavailable = True

    policy_unavailable = False
    cal: dict | None = None
    try:
        cal = policy_calendar.compute_policy_calendar(today=asof)
        if cal is None:
            policy_unavailable = True
    except Exception:  # noqa: BLE001
        policy_unavailable = True
        cal = None

    collected: list[dict] = []
    if not event_unavailable:
        collected.extend(_collect_macro(events, asof, horizon))
    if not policy_unavailable and cal is not None:
        collected.extend(_collect_policy(cal, asof, horizon))

    collected.sort(key=lambda r: (r["date"], r["_etype"]))
    truncated = len(collected) > MAX_ROWS
    collected = collected[:MAX_ROWS]

    by_window: dict[str, list[dict]] = {wid: [] for wid in WINDOWS}
    for row in collected:
        clean = {k: row[k] for k in ROW_KEYS}
        by_window[row["window_id"]].append(clean)

    windows = []
    for window_id in WINDOWS:
        rows = by_window[window_id]
        if window_id == "credit_new_issue":
            state = "empty"
            reason = _EMPTY_REASON[window_id]
        elif window_id in _EVENT_WINDOWS and event_unavailable:
            state = "unavailable"
            reason = _UNAVAIL_EVENTS
        elif window_id in _POLICY_WINDOWS and policy_unavailable:
            state = "unavailable"
            reason = _UNAVAIL_POLICY
        elif rows:
            state = "present"
            reason = ("", "")
        else:
            state = "empty"
            reason = _EMPTY_REASON[window_id]
        windows.append(_window_entry(window_id, state, reason, rows))

    return {
        "schema": SCHEMA,
        "asof": asof.isoformat(),
        "horizon_days": horizon,
        "is_context_only": True,
        "authority": "context_only",
        "note_en": NOTE_EN,
        "note_zh": NOTE_ZH,
        "windows": windows,
        "truncated": truncated,
        "row_count": sum(len(w["rows"]) for w in windows),
    }

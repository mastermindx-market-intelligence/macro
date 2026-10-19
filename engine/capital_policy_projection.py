"""Capital-markets dated-policy projection — CONTEXT ONLY · LEAF · B-F09-6b.

Places dated public-record steps into six frozen capital-markets windows.
Each row is a step, the day it falls on, the window it touches, and the public
record that dates it — nothing is measured, ordered by importance, or read as
a direction. Reads the cached event-calendar snapshot and
engine.policy_calendar only. Never raises into a build. Never calls the
network.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from urllib.parse import urlparse

from engine import event_calendar
from engine import policy_calendar
from engine.event_calendar import _normalize_term
from lib import config

_LIVE_US_MACRO_EVENTS = event_calendar.us_macro_events

SCHEMA = "capital_policy_projection.v1"
HORIZON_DAYS = 45
MAX_ROWS = 12
SECTION_BUDGET_BYTES = 8192
_AUCTION_CACHE_PREFIX = "upcoming_"

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

# Declared public-record citations. Policy rows join on document_number to
# https://www.federalregister.gov/d/<document_number> — never the homepage.
_FR_RECORD = (
    "https://www.federalregister.gov/d/{document_number}",
    "Federal Register",
    "联邦公报",
)
_FROZEN_SOURCE = {
    "FOMC": (
        "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
        "Fed calendar",
        "美联储日历",
    ),
    "AUCTION": (
        "https://www.treasurydirect.gov/auctions/upcoming/",
        "TreasuryDirect",
        "国债直销",
    ),
    "comment_close": _FR_RECORD,
    "rule_effective": _FR_RECORD,
    "entity_list": _FR_RECORD,
}

_AUCTION_TYPE_ZH = {
    "Bill": "短期国债",
    "Note": "中期国债",
    "Bond": "长期国债",
    "TIPS": "通胀保值国债",
    "FRN": "浮息国债",
}
# Spec 2.4 freezes the auction types this section places: Note, Bond, TIPS and
# FRN. Bill carries its Chinese noun above so the table is complete for a
# reader, but widening the ingested set would place an event type the frozen
# map does not list, so the set is written out rather than read off the table.
_AUCTION_TYPES = frozenset({"Note", "Bond", "TIPS", "FRN"})
_AUCTION_LABEL_RE = re.compile(r"^(\d+)-Year (Note|Bond|TIPS|FRN)$")

# Authority ceiling. The heading already says these are dated steps on the
# public record, so the note carries only the ceiling clause. This string is
# not the merged Policy watch chip's live wording (main ships "Not a rating
# and not a trade call."). The frozen §4 string has a third clause that cannot
# be written anywhere in this packet: §2.3 denylists the EN and the ZH word it
# is built from. The PR body's numbered DEVIATIONS record the drop and the
# contradiction.
NOTE_EN = "Not a rating, not a trade call."
NOTE_ZH = "不是评级，也不是交易建议。"

_EMPTY_REASON = (
    "No dated step is pending right now.",
    "目前没有待办的既定日期节点。",
)
_READ_FAILED_EVENTS = (
    "The dated-event calendar could not be read right now.",
    "目前无法读取已定日期事件日历。",
)
_READ_FAILED_AUCTIONS = (
    "The Treasury auction schedule could not be read right now.",
    "目前无法读取国债拍卖日程。",
)
_READ_FAILED_POLICY = (
    "The Federal Register record could not be read right now.",
    "目前无法读取联邦公报记录。",
)
_NO_RECORD = (
    "Dated steps exist, but none carry a linked public record.",
    "已有既定日期节点，但没有可引用的公开记录。",
)
# One sentence per window, so the reader is told which calendar is absent
# instead of being pointed at an internal referent. Only `equity_new_issue`
# (OPEX carries no citable record) and `credit_new_issue` (no bond-issuance
# source exists in v1) can reach this table in v1; the other four are written
# out so no window can render a state without copy of its own.
_NOT_WIRED: dict[str, tuple[str, str]] = {
    "rates_policy": (
        "The policy-rate calendar is not yet connected to this section.",
        "本栏目暂未收录政策利率日历。",
    ),
    "treasury_supply": (
        "The government-borrowing calendar is not yet connected to this section.",
        "本栏目暂未收录政府举债日历。",
    ),
    "equity_new_issue": (
        "The equity-issuance calendar is not yet connected to this section.",
        "本栏目暂未收录股票发行日历。",
    ),
    "credit_new_issue": (
        "The bond-issuance calendar is not yet connected to this section.",
        "本栏目暂未收录债券发行日历。",
    ),
    "disclosure_regulatory": (
        "The disclosure-rule calendar is not yet connected to this section.",
        "本栏目暂未收录披露规则日历。",
    ),
    "export_control": (
        "The export-control calendar is not yet connected to this section.",
        "本栏目暂未收录出口管制日历。",
    ),
}

_EVENT_WINDOWS = frozenset({"rates_policy", "treasury_supply", "equity_new_issue"})
_POLICY_WINDOWS = frozenset({"disclosure_regulatory", "export_control"})
_AUCTION_WINDOW = "treasury_supply"
_CREDIT_WINDOW = "credit_new_issue"


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


def _url_dates_the_event(url: str) -> bool:
    """True only when the URL is the public record that dates the event.

    Homepages are not that record. Each allowlisted host has its own path rule.
    """
    if not url or not _host_allowed(url):
        return False
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    path = (parsed.path or "").rstrip("/")
    if host.endswith("federalregister.gov"):
        return path.startswith("/documents/") or path.startswith("/d/")
    if host.endswith("federalreserve.gov"):
        return "fomccalendars" in path.lower()
    if host.endswith("treasurydirect.gov"):
        return path.startswith("/auctions/upcoming")
    return False


def _source_for(etype: str, ev: dict) -> tuple[str, str, str] | None:
    frozen = _FROZEN_SOURCE.get(etype)
    if frozen is None:
        return None
    url, src_en, src_zh = frozen
    if "{document_number}" in url:
        doc = str(ev.get("document_number") or "").strip()
        if not doc:
            return None
        url = url.format(document_number=doc)
    if not _url_dates_the_event(url):
        return None
    return url, src_en, src_zh


def _auction_copy(ev: dict) -> tuple[str, str] | None:
    """House copy from structured term + type. Unmappable rows are dropped."""
    typ = str(
        ev.get("security_type") or ev.get("securityType") or ""
    ).strip()
    term = str(ev.get("term") or ev.get("securityTerm") or "").strip()
    if typ not in _AUCTION_TYPES or not term:
        return None
    try:
        label = _normalize_term(typ, term)
    except Exception:  # noqa: BLE001
        return None
    match = _AUCTION_LABEL_RE.match(label)
    if match is None:
        return None
    tenor, kind = match.group(1), match.group(2)
    return (
        f"Treasury auctions {tenor}-Year {kind}",
        f"财政部拍卖{tenor}年期{_AUCTION_TYPE_ZH[kind]}",
    )


def _copy_for(etype: str, ev: dict) -> tuple[str, str] | None:
    if etype == "FOMC":
        label = str(ev.get("label") or "")
        if "SEP" in label or "dot-plot" in label or "projections" in label.lower():
            return (
                "Fed rate decision, with outlook",
                "美联储利率决议，含展望",
            )
        return (
            "Fed rate decision",
            "美联储利率决议",
        )
    if etype == "AUCTION":
        return _auction_copy(ev)
    if etype == "comment_close":
        return (
            "Comment period closes",
            "意见征询期截止",
        )
    if etype == "rule_effective":
        return (
            "A rule takes effect",
            "一项规则生效",
        )
    if etype == "entity_list":
        # Typed by the event's is_upcoming flag (policy_calendar), never by
        # days_out. The matched documents include notices and investigations,
        # so the copy is type-neutral; the window label carries the subject.
        flag = ev.get("is_upcoming")
        if flag is True:
            return (
                "Comment period closes on a Federal Register document",
                "一份联邦公报文件的意见征询期截止",
            )
        if flag is False:
            return (
                "A Federal Register document is published",
                "一份联邦公报文件发布",
            )
        return None
    return None


def _row(etype: str, window_id: str, day: date, asof: date, ev: dict) -> dict | None:
    source = _source_for(etype, ev)
    if source is None:
        return None
    url, src_en, src_zh = source
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


def _ingest(
    events: list, asof: date, horizon: int,
) -> tuple[list[dict], dict[str, int], dict[str, int], dict[str, int]]:
    """Rows plus three per-window counters.

    The counters keep two different causes apart, because they name different
    gaps to the reader (seat ruling R1):

    * `unsourced` — the event type is mapped to this window but has no entry in
      `_FROZEN_SOURCE` at all, so no row of that type could ever carry a
      citation. That is a wiring gap on our side, not a gap in the public
      record. `OPEX` is the standing case: it is computed every third Friday,
      so `equity_new_issue` always has one and can never render it.
    * `dropped` — the type IS wired, but this row's own record could not be
      built (a Federal Register step with no document number) or its copy could
      not be derived from the row's structured fields.
    * `in_horizon` — everything mapped and inside the horizon, whatever happened
      to it afterwards.
    """
    end = asof + timedelta(days=horizon)
    out: list[dict] = []
    in_horizon: dict[str, int] = defaultdict(int)
    dropped: dict[str, int] = defaultdict(int)
    unsourced: dict[str, int] = defaultdict(int)
    for ev in events or []:
        if not isinstance(ev, dict):
            continue
        etype = str(ev.get("event_type") or ev.get("type") or "")
        window_id = EVENT_WINDOW_MAP.get(etype)
        if window_id is None:
            continue
        day = _as_date(ev.get("date"))
        if day is None or day < asof or day > end:
            continue
        in_horizon[window_id] += 1
        if etype not in _FROZEN_SOURCE:
            unsourced[window_id] += 1
            continue
        row = _row(etype, window_id, day, asof, ev)
        if row is None:
            dropped[window_id] += 1
            continue
        out.append(row)
    return out, in_horizon, dropped, unsourced


def _auction_cache_path(asof: date):
    return (
        config.ROOT / "data" / "macro" / "auction_cache"
        / f"{_AUCTION_CACHE_PREFIX}{asof.isoformat()}.json"
    )


def _read_auction_cache(asof: date) -> tuple[str, list]:
    """Return (status, records). Never networks. Never writes.

    The cache file carries the day it covers in its own name, so a cache
    written for another day is not found for this `asof` and the status is
    `missing`. Age is never read from the mtime or the wall clock: §4 requires
    byte-identical output for the same `today` and the same files, and an mtime
    test would flip a window from present to unavailable as a build crosses an
    age boundary.
    """
    path = _auction_cache_path(asof)
    if not path.exists():
        return "missing", []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return "unreadable", []
        return "ok", data
    except Exception:  # noqa: BLE001
        return "unreadable", []


def _auctions_from_records(records: list, asof: date, horizon: int) -> list[dict]:
    end = asof + timedelta(days=horizon)
    out: list[dict] = []
    for rec in records or []:
        if not isinstance(rec, dict):
            continue
        typ = str(rec.get("securityType") or rec.get("security_type") or "").strip()
        if typ not in _AUCTION_TYPES:
            continue
        try:
            day = date.fromisoformat(str(rec.get("auctionDate") or rec.get("date") or "")[:10])
        except ValueError:
            continue
        if day < asof or day > end:
            continue
        out.append({
            "type": "AUCTION",
            "event_type": "AUCTION",
            "date": day.isoformat(),
            "securityType": typ,
            "security_type": typ,
            "securityTerm": str(rec.get("securityTerm") or rec.get("term") or ""),
            "term": str(rec.get("securityTerm") or rec.get("term") or ""),
            "is_context_only": True,
        })
    return out


def _suppress_auction_fetch():
    """Force event_calendar not to call TreasuryDirect during a page build."""
    orig = event_calendar._fetch_upcoming_auctions

    def _closed(today):  # noqa: ARG001
        return []

    event_calendar._fetch_upcoming_auctions = _closed
    return orig


def _more_copy(hidden: int) -> tuple[str, str]:
    if hidden == 1:
        return (
            "1 more dated step is not shown.",
            "另有 1 个既定日期节点未展示。",
        )
    return (
        f"{hidden} more dated steps are not shown.",
        f"另有 {hidden} 个既定日期节点未展示。",
    )


def _collapse_comment_close(rows: list[dict]) -> list[dict]:
    """Same-date comment_close rows that render identically collapse to one.

    Auction and FOMC rows never collapse. The count lives in the copy; the
    frozen §4 object gains no key. The surviving citation is the lowest
    source_url of the group.
    """
    kept: list[dict] = []
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        if row.get("_etype") != "comment_close":
            kept.append(row)
            continue
        key = (row["date"], row["window_id"], row["event_en"], row["event_zh"])
        groups[key].append(row)
    for group in groups.values():
        if len(group) == 1:
            kept.append(group[0])
            continue
        group.sort(key=lambda r: r["source_url"])
        survivor = dict(group[0])
        n = len(group)
        survivor["event_en"] = (
            f"Comment periods close on {n} Federal Register documents"
        )
        survivor["event_zh"] = f"{n} 份联邦公报文件的意见征询期截止"
        kept.append(survivor)
    return kept


def _clip_per_window(collected: list[dict]) -> tuple[dict[str, list[dict]], bool, dict[str, int]]:
    """Keep MAX_ROWS across the section; never clip a window with rows to zero."""
    by_window: dict[str, list[dict]] = {wid: [] for wid in WINDOWS}
    for row in collected:
        by_window[row["window_id"]].append(row)
    for wid in WINDOWS:
        by_window[wid].sort(key=lambda r: (r["date"], r["_etype"], r["source_url"]))

    total = sum(len(rows) for rows in by_window.values())
    hidden = {wid: 0 for wid in WINDOWS}
    if total <= MAX_ROWS:
        return by_window, False, hidden

    occupied = [wid for wid in WINDOWS if by_window[wid]]
    remaining_slots = MAX_ROWS - len(occupied)
    extras: list[dict] = []
    firsts: dict[str, dict] = {}
    for wid in occupied:
        rows = by_window[wid]
        firsts[wid] = rows[0]
        extras.extend(rows[1:])
    extras.sort(key=lambda r: (r["date"], r["_etype"], r["source_url"]))

    kept_extra: dict[str, list[dict]] = {wid: [] for wid in WINDOWS}
    for row in extras:
        if remaining_slots <= 0:
            break
        kept_extra[row["window_id"]].append(row)
        remaining_slots -= 1

    clipped: dict[str, list[dict]] = {wid: [] for wid in WINDOWS}
    for wid in WINDOWS:
        if wid not in firsts:
            continue
        clipped[wid] = [firsts[wid]] + kept_extra[wid]
        hidden[wid] = len(by_window[wid]) - len(clipped[wid])
    return clipped, True, hidden


def _window_entry(
    window_id: str,
    state: str,
    reason: tuple[str, str],
    rows: list[dict],
    more: tuple[str, str] = ("", ""),
) -> dict:
    labels = WINDOWS[window_id]
    return {
        "window_id": window_id,
        "label_en": labels["label_en"],
        "label_zh": labels["label_zh"],
        "state": state,
        "reason_en": reason[0] if state != "present" else "",
        "reason_zh": reason[1] if state != "present" else "",
        "more_en": more[0],
        "more_zh": more[1],
        "rows": rows,
    }


def _clean_rows(rows: list[dict]) -> list[dict]:
    return [{k: row[k] for k in ROW_KEYS} for row in rows]


def typed_unavailable(today: date | None = None) -> dict:
    """Schema-shaped payload used when the leaf cannot be imported."""
    asof = _as_date(today) or date.today()
    windows = []
    for window_id in WINDOWS:
        if window_id == _CREDIT_WINDOW:
            state, reason = "unavailable", _NOT_WIRED[window_id]
        elif window_id in _POLICY_WINDOWS:
            state, reason = "unavailable", _READ_FAILED_POLICY
        elif window_id == _AUCTION_WINDOW:
            state, reason = "unavailable", _READ_FAILED_AUCTIONS
        else:
            state, reason = "unavailable", _READ_FAILED_EVENTS
        windows.append(_window_entry(window_id, state, reason, []))
    return {
        "schema": SCHEMA,
        "asof": asof.isoformat(),
        "horizon_days": HORIZON_DAYS,
        "is_context_only": True,
        "authority": "context_only",
        "note_en": NOTE_EN,
        "note_zh": NOTE_ZH,
        "windows": windows,
        "truncated": False,
        "truncation_en": "",
        "truncation_zh": "",
        "row_count": 0,
    }


def project(today: date | None = None, horizon_days: int | None = None) -> dict:
    """Return the frozen v1 payload. Never raises into a build. Never networks."""
    asof = _as_date(today) or date.today()
    horizon = HORIZON_DAYS if horizon_days is None else int(horizon_days)

    event_unavailable = False
    events: list = []
    orig_fetch = _suppress_auction_fetch()
    try:
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
            events = []
    finally:
        event_calendar._fetch_upcoming_auctions = orig_fetch

    injected_auctions = [
        ev for ev in events
        if isinstance(ev, dict) and str(ev.get("event_type") or ev.get("type") or "") == "AUCTION"
    ]
    events_no_auction = [
        ev for ev in events
        if not (isinstance(ev, dict) and str(ev.get("event_type") or ev.get("type") or "") == "AUCTION")
    ]

    live_macro = event_calendar.us_macro_events is _LIVE_US_MACRO_EVENTS
    auction_status = "ok"
    if live_macro:
        auction_status, records = _read_auction_cache(asof)
        if auction_status == "ok":
            auction_events = _auctions_from_records(records, asof, horizon)
        else:
            auction_events = []
    else:
        auction_events = injected_auctions

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
    in_horizon: dict[str, int] = defaultdict(int)
    dropped: dict[str, int] = defaultdict(int)
    unsourced: dict[str, int] = defaultdict(int)

    def _absorb(source_events: list) -> None:
        rows, h, d, u = _ingest(source_events, asof, horizon)
        collected.extend(rows)
        for wid, n in h.items():
            in_horizon[wid] += n
        for wid, n in d.items():
            dropped[wid] += n
        for wid, n in u.items():
            unsourced[wid] += n

    if not event_unavailable:
        _absorb(events_no_auction)
    _absorb(auction_events)

    if not policy_unavailable and cal is not None:
        _absorb(
            list(cal.get("upcoming_events") or [])
            + list(cal.get("entity_list_events") or [])
        )

    collected = _collapse_comment_close(collected)
    collected.sort(key=lambda r: (r["date"], r["_etype"], r["source_url"]))
    by_window, truncated, hidden = _clip_per_window(collected)

    windows = []
    for window_id in WINDOWS:
        rows = _clean_rows(by_window[window_id])
        more = _more_copy(hidden[window_id]) if hidden[window_id] else ("", "")
        if window_id == _CREDIT_WINDOW:
            state, reason = "unavailable", _NOT_WIRED[window_id]
            rows, more = [], ("", "")
        elif window_id == _AUCTION_WINDOW and auction_status != "ok" and not injected_auctions:
            # The auction schedule is its own cached file. Naming the
            # dated-event calendar here would point the reader at a source the
            # section read successfully one window above.
            state, reason = "unavailable", _READ_FAILED_AUCTIONS
            rows, more = [], ("", "")
        elif window_id in _POLICY_WINDOWS and policy_unavailable:
            state, reason = "unavailable", _READ_FAILED_POLICY
            rows, more = [], ("", "")
        elif rows:
            state, reason = "present", ("", "")
        elif (
            window_id in _EVENT_WINDOWS
            and window_id != _AUCTION_WINDOW
            and event_unavailable
        ):
            state, reason = "unavailable", _READ_FAILED_EVENTS
            rows, more = [], ("", "")
        elif dropped[window_id]:
            state, reason = "unavailable", _NO_RECORD
        elif unsourced[window_id]:
            # Every step this window saw belongs to an event type wired to no
            # citable source. Blaming the public record would be wrong.
            state, reason = "unavailable", _NOT_WIRED[window_id]
        elif in_horizon[window_id]:
            state, reason = "unavailable", _NO_RECORD
        else:
            state, reason = "empty", _EMPTY_REASON
        windows.append(_window_entry(window_id, state, reason, rows, more))

    row_count = sum(len(w["rows"]) for w in windows)
    truncation = (
        (
            f"Showing the next {MAX_ROWS} dated steps; more are scheduled.",
            f"仅显示接下来的 {MAX_ROWS} 个既定日期节点，后续仍有安排。",
        )
        if truncated else ("", "")
    )
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
        "truncation_en": truncation[0],
        "truncation_zh": truncation[1],
        "row_count": row_count,
    }

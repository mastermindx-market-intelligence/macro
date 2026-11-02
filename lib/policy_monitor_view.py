"""Policy Monitor display normalizer — a PURE projection of existing payloads.

The Policy Monitor card and dialog are rendered from ONE normalized view model so
the display layer can never turn an absent reading into a zero, a missing arming
block into "Quiet", a stale election countdown into a live clock, or an
unqualified Fed-vs-market gap into a precise spread.

BOUNDARIES (frozen design packet —
research/policy_monitor/POLICY_MONITOR_UPGRADE_2026-11-01.md):

  * PRESENTATION ONLY. This module never fetches, caches, schedules, scores, or
    mutates a raw payload. It is not a new data owner.
  * Inputs are the existing artifacts and view models:
      - ``site/policy_lever.json``   (producer: scripts/build_policy_lever.py)
      - ``latest.fed_path``           (producer: engine/fed_path.py)
      - ``latest.fed_stance``         (producer: engine/fed_stance.py)
      - the existing flip-confirmation and event-window views
  * Every section degrades INDEPENDENTLY: a malformed rates block leaves the
    conditions state, the recorded-alert counts and the transmission rows intact.
  * Unknown is not zero. A bool is not a numeric reading. NaN/Infinity are not
    readings. Malformed dates, unsafe URLs, over-long text and over-long arrays
    are refused rather than rendered.
  * Comparison discipline: the legacy ``gap`` / ``read_en`` blocks are NOT
    basis-qualified by themselves. A Fed-vs-market comparison is rendered only
    when the existing comparison verdict, source publication dates, measure,
    horizon and values all qualify. Otherwise observations remain separate.

The normalizer never asserts policy intent or timing (DNR:KILL-POLICY-TIMING-
PREDICTOR): it reports recorded conditions, market prices and dated narrative.
"""
from __future__ import annotations

import math
import re
from datetime import date, datetime, timezone
from typing import Any

VIEW_SCHEMA = "policy_monitor_view.v1"

# --- display bounds (the display boundary is where size is clamped) ---------- #
MAX_TEXT = 600
MAX_SHORT_TEXT = 180
MAX_ITEMS = 12
MAX_LEVERS = 12
MAX_DRIVERS = 6
MAX_CONTRACTS = 24

# --- chart geometry (dialog chart + card sparkline share one scale rule) --- #
_CHART = {"width": 720, "height": 264, "pl": 54, "pr": 34, "pt": 22, "pb": 46}
_MOBILE_CHART = {"width": 340, "height": 234, "pl": 48, "pr": 24, "pt": 24, "pb": 44}
_SPARK = {"width": 120, "height": 36, "pl": 2, "pr": 2, "pt": 3, "pb": 3}
_MAX_MONTHS = 12.0

# The producer's own drawdown leg (PS-R9): -15% from the trailing-120d peak.
_DRAWDOWN_LEG_PCT = -15.0

_STATE_VALUES = ("ARMED", "ELEVATED", "QUIET")
_STANCE_LABELS = {
    "hawkish": ("Hawkish", "鹰派"),
    "very-hawkish": ("Very Hawkish", "极鹰派"),
    "dovish": ("Dovish", "鸽派"),
    "very-dovish": ("Very Dovish", "极鸽派"),
    "neutral": ("Neutral / hold", "中性 / 不动"),
}
_GUIDANCE_LABELS = {
    "tightening": ("leaning tighter", "倾向收紧"),
    "easing": ("leaning easier", "倾向宽松"),
    "on_hold": ("on hold", "按兵不动"),
    "mixed": ("mixed signals", "信号混杂"),
}

_ISO_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
_HORIZON_RE = re.compile(r"^m(\d{1,3})$")
_URL_KEYS = ("source_url", "url", "link", "href")


# --------------------------------------------------------------------------- #
# Strict scalar readers — unknown is never coerced into a value.
# --------------------------------------------------------------------------- #

def _mapping(v: Any) -> dict:
    """A mapping, or an empty mapping. Never raises."""
    return v if isinstance(v, dict) else {}


def _num(v: Any) -> float | None:
    """A finite real reading, or None. bool is NOT a number; NaN/inf are NOT
    readings; numeric strings are NOT readings (strict mapping)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(f):
        return None
    return f


def _int(v: Any) -> int | None:
    """A finite integer reading, or None. Keeps a valid zero."""
    f = _num(v)
    if f is None:
        return None
    if float(f).is_integer():
        return int(f)
    return None


def _rate(v: Any) -> float | None:
    """Bound the chart's numeric representation, not the upstream rate model.

    Values outside a million percent cannot be usefully labelled in this
    monitor. Refuse them locally before arithmetic can overflow; other
    independently valid sections remain available.
    """
    n = _num(v)
    return n if n is not None and abs(n) <= 1_000_000 else None


def _text(v: Any, limit: int = MAX_TEXT) -> str | None:
    """A bounded string, or None. Non-strings are refused."""
    if not isinstance(v, str):
        return None
    s = v.strip()
    if not s:
        return None
    return s[:limit]


def _seq(v: Any, limit: int = MAX_ITEMS) -> list:
    """A bounded list. A str/dict is NOT a sequence."""
    if isinstance(v, (str, bytes, dict)) or not isinstance(v, (list, tuple)):
        return []
    return list(v[:limit])


def _safe_url(v: Any) -> str | None:
    """An http(s) URL, or None. javascript:/data:/vbscript: and relatives are
    refused; so is anything without a host."""
    if not isinstance(v, str):
        return None
    s = v.strip()
    if not s or len(s) > 300:
        return None
    low = s.lower()
    if not (low.startswith("http://") or low.startswith("https://")):
        return None
    host = s.split("//", 1)[1].split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    host = host.split("@")[-1].split(":")[0]
    if not host or "." not in host:
        return None
    if any(ch in host for ch in " \t\r\n<>\"'"):
        return None
    return s


def _date(v: Any) -> date | None:
    """An ISO date (or the date part of an ISO timestamp), or None."""
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = v.strip() if isinstance(v, str) else None
    if not s or len(s) > 40:
        return None
    try:
        if len(s) == 10:
            return date.fromisoformat(s)
        if len(s) > 10 and s[10] in ("T", " "):
            return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        return None
    return None


def _date_str(v: Any) -> str | None:
    d = _date(v)
    return d.isoformat() if d else None


def _instant(v: Any) -> datetime | None:
    """A bounded ISO timestamp in UTC, with the producer's naive-UTC convention."""
    if not isinstance(v, str) or len(v.strip()) > 60:
        return None
    s = _text(v, 60)
    if not s or len(s) <= 10 or s[10] not in ("T", " "):
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError):
        return None


def _months_between(d0: date, d1: date) -> float:
    """Signed months from d0 to d1 (calendar months + a day fraction)."""
    months = (d1.year - d0.year) * 12 + (d1.month - d0.month)
    frac = (d1.day - d0.day) / 30.4375
    return months + frac


def _months_label(m: float) -> tuple[str, str]:
    """(EN, ZH) label for a horizon in months."""
    n = int(round(m))
    if n <= 0:
        return ("now", "现在")
    return (f"{n}m", f"{n}个月")


def _find_date_in_text(s: str | None) -> str | None:
    """The first YYYY-MM-DD inside a producer string (the producer states its own
    event date in the copy). Never invents a date."""
    if not s:
        return None
    m = _ISO_DATE_RE.search(s)
    if not m:
        return None
    try:
        return date.fromisoformat(m.group(1)).isoformat()
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
# Chart geometry — elapsed-time x (0/1/3/6/12m), nice y ticks, honest gaps.
# --------------------------------------------------------------------------- #

def _nice_scale(vmin: float, vmax: float, target_ticks: int = 4) -> tuple[float, float, float]:
    """(ymin, ymax, step) on a readable scale. Degenerate spans get a floor."""
    if not math.isfinite(vmin) or not math.isfinite(vmax):
        return (0.0, 1.0, 0.5)
    if vmax - vmin < 1e-9:
        vmin, vmax = vmin - 0.25, vmax + 0.25
    raw = (vmax - vmin) / max(1, target_ticks)
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1.0
    step = math.ceil(raw / mag) * mag
    step = max(step, 0.05)
    lo = math.floor(vmin / step) * step
    hi = math.ceil(vmax / step) * step
    if hi - lo < 1e-9:
        hi = lo + step
    return (round(lo, 6), round(hi, 6), round(step, 6))


def _geometry(points: list[dict], extra_values: list[float], box: dict,
              max_months: float = _MAX_MONTHS,
              scale: tuple[float, float] | None = None) -> dict:
    """Project horizon points onto an elapsed-time x axis.

    ``points`` — [{"months": float, "value": float | None}] in month order. A
    point whose value is None is a GAP: the line breaks there and the point is
    never drawn as a zero.
    ``extra_values`` — other series that share the scale (Fed projections).
    ``scale`` — an explicit (vmin, vmax) so a mini chart can share the scale of
    the main chart instead of rescaling its own.
    """
    w, h = box["width"], box["height"]
    pl, pr, pt, pb = box["pl"], box["pr"], box["pt"], box["pb"]
    x0, x1 = pl, w - pr
    y0, y1 = pt, h - pb

    known = [p for p in points if p.get("value") is not None]
    vals = [p["value"] for p in known] + [v for v in extra_values if math.isfinite(v)]
    if scale is not None:
        vmin, vmax = scale
    elif vals:
        vmin, vmax, _step0 = _nice_scale(min(vals), max(vals))
    else:
        vmin, vmax = 0.0, 1.0
    span = (vmax - vmin) or 1.0

    def x_of(m: float) -> float:
        return round(x0 + (max(0.0, min(m, max_months)) / max_months) * (x1 - x0), 2)

    def y_of(v: float) -> float:
        return round(y1 - (v - vmin) / span * (y1 - y0), 2)

    step = _nice_scale(vmin, vmax)[2]
    ticks = []
    v = vmin
    guard = 0
    while v <= vmax + 1e-9 and guard < 40:
        ticks.append({"value": round(v, 4), "y": y_of(v), "label": f"{v:.2f}%"})
        v = round(v + step, 6)
        guard += 1

    # Contiguous runs only — a missing horizon BREAKS the line (never bridged).
    runs: list[list[list[float]]] = []
    areas: list[str] = []
    run: list[list[float]] = []
    for p in points:
        if p.get("value") is None:
            if len(run) >= 2:
                runs.append(run)
            run = []
            continue
        run.append([x_of(p["months"]), y_of(p["value"])])
    if len(run) >= 2:
        runs.append(run)

    segments: list[dict] = []
    for r in runs:
        d = "M" + " L".join(f"{x},{y}" for x, y in r)
        areas.append(f"{d} L{r[-1][0]},{y1} L{r[0][0]},{y1} Z")
        length = 0.0
        for i in range(1, len(r)):
            length += math.hypot(r[i][0] - r[i - 1][0], r[i][1] - r[i - 1][1])
        segments.append({"points": r, "dash": round(length + 8, 1), "d": d})

    markers = [{
        "x": x_of(p["months"]), "y": y_of(p["value"]), "value": p["value"],
        "months": p["months"], "label_en": p.get("label_en"), "label_zh": p.get("label_zh"),
    } for p in known]
    # Value labels are thinned so two adjacent readings never collide; the
    # values table carries every number regardless.
    last_x = None
    for i, mk in enumerate(markers):
        keep = (i == 0 or i == len(markers) - 1 or last_x is None
                or mk["x"] - last_x >= 44)
        mk["show_label"] = keep
        if keep:
            last_x = mk["x"]

    return {
        "width": w, "height": h,
        "x_min": x0, "x_max": x1, "y_min": vmin, "y_max": vmax,
        "y_top": y0, "y_bottom": y1,
        "y_ticks": ticks,
        "x_ticks": [],
        "segments": segments,
        "areas": areas,
        "markers": markers,
        "gaps": [{"months": p["months"], "x": x_of(p["months"]),
                  "label_en": p.get("label_en"), "label_zh": p.get("label_zh")}
                 for p in points if p.get("value") is None],
        "max_months": max_months,
    }


# --------------------------------------------------------------------------- #
# Section readers
# --------------------------------------------------------------------------- #

def _read_state(pl: dict, conditions: list[dict]) -> dict:
    """Qualify the reported score against its evidence, never replace the score."""
    raw = _text(pl.get("state"), 24)
    reported = raw.upper() if raw and raw.upper() in _STATE_VALUES else None
    values = [c["met"] if c["known"] else None for c in conditions]
    complete = all(v is not None for v in values)
    expected = ("ARMED" if all(values) else "ELEVATED" if any(values) else "QUIET") if complete else None
    contradiction = bool(reported and (
        (complete and reported != expected)
        or (reported == "QUIET" and True in values)
        or (reported == "ARMED" and False in values)))
    partial = reported == "ELEVATED" and True in values and not complete
    known = bool(reported and complete and not contradiction)
    state = reported if known or partial else "UNKNOWN"
    qualification = "confirmed" if known else "inconsistent" if contradiction else "partial" if partial else "unavailable"
    summary = {
        "ARMED": ("Both conditions are met", "两项条件同时成立"),
        "ELEVATED": ("One condition is met", "一项条件成立"),
        "QUIET": ("Neither condition is met", "两项条件均未成立"),
        "UNKNOWN": ("Assessment unavailable", "评估不可用"),
    }[state]
    watch = {
        "ARMED": ("Watch for confirmation in market prices — this is a condition, not a call.",
                  "留意市场价格确认——这是条件，不是交易指令。"),
        "ELEVATED": ("Watch for the second condition — one leg is in place.",
                     "留意第二项条件——目前只有一项成立。"),
        "QUIET": ("Watch for the drawdown or a lever setup to change.",
                  "留意回撤或杠杆技术形态是否变化。"),
        "UNKNOWN": ("The required observations are incomplete or undated.",
                    "所需观测不完整或缺少日期。"),
    }[state]
    stance = {
        "ARMED": ("Watch — conditions met, no call yet",
                  "观察 — 条件成立，但暂无交易结论"),
        "ELEVATED": ("Watch — one condition met",
                     "观察 — 一项条件成立"),
        "QUIET": ("Watch — no condition met",
                  "观察 — 暂无条件成立"),
        "UNKNOWN": ("Assessment unavailable", "评估不可用"),
    }[state]
    if partial:
        summary = ("Elevated condition observed", "已观测到一项风险条件")
        watch = ("Partial evidence · other condition unverified.",
                 "证据不完整 · 另一项条件尚未确认。")
        stance = ("Partial evidence", "证据不完整")
    if contradiction:
        watch = ("The reported state conflicts with the available observations.",
                 "报告状态与现有观测不一致。")
    return {
        "value": state, "known": known, "reported": reported,
        "qualification": qualification,
        "summary_en": summary[0], "summary_zh": summary[1],
        "stance_en": stance[0], "stance_zh": stance[1],
        "watch_en": watch[0], "watch_zh": watch[1],
        "chip_class": {"ARMED": "c-down", "ELEVATED": "c-warn", "QUIET": "c-muted",
                       "UNKNOWN": "c-muted"}[state],
    }


def _read_conditions(pl: dict, transmission: list[dict]) -> list[dict]:
    """The two producer conditions, each with its own known/met pair."""
    fc = _mapping(pl.get("favored_complex"))
    dd = _num(fc.get("drawdown_pct"))
    dd_date = _date_str(fc.get("as_of"))
    dd_known = dd is not None and dd_date is not None and fc.get("basket_incomplete") is not True
    evaluated = _date_str(pl.get("evaluated_at")) or _date_str(pl.get("computed_at"))
    if evaluated and dd_date and dd_date > evaluated:
        dd_known = False
    legs = []
    legs.append({
        "key": "drawdown",
        "label_en": "Semis drawdown ≥15%",
        "label_zh": "半导体组合回撤 ≥15%",
        "value_en": ((f"{dd:+.1f}% from the 120-day peak" + (f" · {dd_date}" if dd_date else " · date unavailable")) if dd is not None
                     else "Drawdown not computed"),
        "value_zh": ((f"较120日高点{dd:+.1f}%" + (f" · {dd_date}" if dd_date else " · 日期不可用")) if dd is not None else "未计算回撤"),
        "known": dd_known,
        "met": (dd <= _DRAWDOWN_LEG_PCT) if dd_known else None,
    })
    eligible = [t for t in transmission if t["asset_known"]]
    observed = [t for t in eligible if t["observed"]["qualified"]]
    armed = [t for t in observed if t["observed"]["state"] == "armed"]
    roster = pl.get("levers")
    roster_complete = (isinstance(roster, list) and 0 < len(roster) <= MAX_LEVERS
                       and all(isinstance(t, dict) and "asset" in t
                               and (t["asset"] is None or _text(t["asset"], 24)) for t in roster))
    arming_known = bool(armed) or bool(roster_complete and eligible and len(observed) == len(eligible))
    legs.append({
        "key": "arming",
        "label_en": "Any technical lever armed",
        "label_zh": "任一政策杠杆技术形态已触发",
        "value_en": (f"{len(armed)}/{len(eligible)} eligible levers armed" if arming_known
                     else "Observation date unavailable" if any(t["observed"]["known"] and not t["observed"]["qualified"] for t in eligible)
                     else "Technical observations unavailable"),
        "value_zh": (f"{len(eligible)}项符合条件的杠杆中{len(armed)}项已触发" if arming_known
                     else "观测日期不可用" if any(t["observed"]["known"] and not t["observed"]["qualified"] for t in eligible)
                     else "技术观测不可用"),
        "known": arming_known,
        "met": bool(armed) if arming_known else None,
    })
    return legs


def _read_transmission(pl: dict) -> list[dict]:
    """Lever rows: observed technical state kept apart from the dated hypothesis."""
    rows = []
    for lv in _seq(pl.get("levers"), MAX_LEVERS):
        lv = _mapping(lv)
        arming = lv.get("arming")
        name_en = _text(lv.get("name"), 120) or "Unnamed lever"
        name_zh = _text(lv.get("name_zh"), 120) or name_en
        asset = _text(lv.get("asset"), 24)
        observed_date = _date_str(_mapping(arming).get("as_of")) or _date_str(lv.get("observed_as_of"))
        evaluated = _date_str(pl.get("evaluated_at")) or _date_str(pl.get("computed_at"))
        observed = {"known": False, "qualified": False, "as_of": observed_date, "state": "unavailable",
                    "label_en": "Not observed", "label_zh": "未观测",
                    "reason_en": "", "reason_zh": "",
                    "gauge": {"known": False, "value": None, "clamped": False}}
        if not isinstance(arming, dict):
            observed["reason_en"] = ("No technical setup is recorded for this lever "
                                     "in the snapshot.")
            observed["reason_zh"] = "本次快照未记录该杠杆的技术形态。"
        elif "armed" not in arming:
            observed["reason_en"] = "The snapshot carries no arming flag for this lever."
            observed["reason_zh"] = "本次快照未携带该杠杆的触发标记。"
        else:
            flag = arming.get("armed")
            if not isinstance(flag, bool):
                observed["reason_en"] = "The arming flag is malformed and was refused."
                observed["reason_zh"] = "触发标记格式异常，已拒绝采用。"
            else:
                observed["known"] = True
                observed["qualified"] = bool(observed_date and (not evaluated or observed_date <= evaluated))
                observed["state"] = "armed" if flag else "quiet"
                observed["label_en"] = "Armed" if flag else "Quiet"
                observed["label_zh"] = "已触发" if flag else "平静"
                observed["reason_en"] = ("Technical setup is armed." if flag
                                         else "Technical setup is not armed.")
                observed["reason_zh"] = ("技术形态已触发。" if flag else "技术形态未触发。")
                if observed["qualified"]:
                    observed["reason_en"] += f" Observed {observed_date}."
                    observed["reason_zh"] += f" 观测于 {observed_date}。"
                else:
                    observed["reason_en"] += " Observation date unqualified; excluded from assessment."
                    observed["reason_zh"] += " 观测日期尚未确认，未纳入评估。"
                k = _num(arming.get("stoch_k"))
                if k is not None:
                    observed["gauge"] = {"known": True,
                                         "value": min(max(k, 0.0), 100.0),
                                         "clamped": k < 0.0 or k > 100.0}
        rows.append({
            "name_en": name_en, "name_zh": name_zh,
            "asset": asset, "asset_known": asset is not None,
            "observed": observed,
            "hypothesis_en": _text(lv.get("watch"), MAX_TEXT) or "",
            "hypothesis_zh": _text(lv.get("watch_zh"), MAX_TEXT)
            or _text(lv.get("watch"), MAX_TEXT) or "",
            "copy_as_of": _date_str(lv.get("copy_as_of")),
            "copy_age_days": _int(lv.get("copy_age_days")),
            "copy_stale": bool(lv.get("copy_stale")) if isinstance(lv.get("copy_stale"), bool) else None,
        })
    return rows


def _read_activity(pl: dict) -> dict:
    """Recorded policy alerts (NOT Fed speeches) — a valid zero stays a zero."""
    jw = _mapping(pl.get("jawboning"))
    n7 = _int(jw.get("n_7d"))
    n30 = _int(jw.get("n_30d"))
    n7 = n7 if n7 is not None and n7 >= 0 else None
    n30 = n30 if n30 is not None and n30 >= 0 else None
    status = _text(jw.get("source_status"), 40)
    refused = "source_status" in jw and status not in ("usable", "partial", "empty")
    if refused or (status == "empty" and (n7 not in (None, 0) or n30 not in (None, 0))):
        n7 = n30 = None
    if n7 is not None and n30 is not None and n7 > n30:
        n7 = n30 = None
    evaluation = _instant(jw.get("evaluated_at"))
    window_end = evaluation.date().isoformat() if evaluation else _date_str(jw.get("evaluated_date"))
    last = _instant(jw.get("last_alert_ts_utc")) or _instant(jw.get("last_alert_ts"))
    ts = last.isoformat().replace("+00:00", "Z") if last else None
    summary_en = _text(jw.get("last_alert_summary"), MAX_SHORT_TEXT)
    summary_zh = _text(jw.get("last_alert_summary_zh"), MAX_SHORT_TEXT)
    if refused or status == "empty" or (last and evaluation and last > evaluation):
        ts = summary_en = summary_zh = None
    coverage_en = "White House alert records. " + (f"7-day and 30-day windows ending {window_end} (UTC). " if window_end
                   else "Window end date unavailable. ") + "Feed coverage is not established."
    coverage_zh = "白宫动态记录。" + (f"7日与30日窗口截止于 {window_end}（UTC）。" if window_end
                   else "窗口截止日期不可用。") + "信息源覆盖范围尚未确认。"
    if status == "partial":
        coverage_en += " Counts include valid records only; unusable or future-dated entries were excluded."
        coverage_zh += "计数仅含有效记录；不可用或日期晚于截止时间的条目已排除。"
    elif refused:
        coverage_en += " The source could not establish usable counts."
        coverage_zh += "来源未能提供可用计数。"
    elif status == "empty":
        coverage_en += " No alerts were present in the recorded source."
        coverage_zh += "记录的来源中没有提醒。"
    return {
        "known_7d": n7 is not None, "n_7d": n7,
        "known_30d": n30 is not None, "n_30d": n30,
        "window_end": window_end, "source_status": status,
        "count_label_en": "recorded policy alerts", "count_label_zh": "记录的政策提醒",
        "coverage_en": coverage_en, "coverage_zh": coverage_zh,
        "last_alert": {
            "known": bool(ts or summary_en),
            "ts": ts, "date": _date_str(ts),
            "summary_en": summary_en or "",
            "summary_zh": summary_zh or summary_en or "",
        },
        "last_alert_label_en": "Last recorded policy alert",
        "last_alert_label_zh": "最近一次政策提醒",
        "fed_communication_label_en": "Fed communication is tracked separately and is not counted here.",
        "fed_communication_label_zh": "美联储沟通单独记录，不计入此处。",
    }


def _read_structure(pl: dict) -> dict:
    fc = _mapping(pl.get("favored_complex"))
    basket = [t for t in (_text(b, 16) for b in _seq(fc.get("basket"), MAX_ITEMS)) if t]
    incomplete = bool(fc.get("basket_incomplete"))
    return {
        "known": _num(fc.get("drawdown_pct")) is not None,
        "basket": basket,
        "drawdown_pct": _num(fc.get("drawdown_pct")),
        "drawdown_z": _num(fc.get("drawdown_z")),
        "basket_incomplete": incomplete,
        "note_en": _text(fc.get("note"), MAX_TEXT) or "",
        "note_zh": _text(fc.get("note_zh"), MAX_TEXT) or _text(fc.get("note"), MAX_TEXT) or "",
        "caveat_en": _text(fc.get("basket_caveat"), MAX_TEXT) or "",
        "caveat_zh": _text(fc.get("basket_caveat_zh"), MAX_TEXT)
        or _text(fc.get("basket_caveat"), MAX_TEXT) or "",
        "as_of": _date_str(fc.get("as_of")),
    }


def _read_stance(latest: dict) -> dict:
    fs = _mapping(_mapping(latest).get("fed_stance"))
    raw = fs.get("stance")
    key = raw if isinstance(raw, str) else ""
    labels = _STANCE_LABELS.get(key)
    known = labels is not None
    return {
        "known": known,
        "kind": key if known else "unknown",
        "label_en": labels[0] if labels else "Stance not reported",
        "label_zh": labels[1] if labels else "未记录立场",
        "as_of": _date_str(fs.get("as_of")) or _date_str(_mapping(latest).get("date")),
    }


def _read_guidance(latest: dict) -> dict:
    fs = _mapping(_mapping(latest).get("fed_stance"))
    raw = fs.get("guidance")
    key = raw if isinstance(raw, str) else ""
    labels = _GUIDANCE_LABELS.get(key)
    known = labels is not None
    return {
        "known": known,
        "label_en": labels[0] if labels else "Guidance unavailable",
        "label_zh": labels[1] if labels else "指引不可用",
    }


def _projection_date(meta: dict, observation: date | None) -> date | None:
    """A source-supported SEP vintage available before the observation day.

    These artifacts carry day precision. Same-day ordering is not established
    by a date alone. The target year-end is never a publication timestamp.
    """
    dots = _mapping(meta.get("dots"))
    released = _date(dots.get("vintage")) or _date(dots.get("first_public_evidence"))
    declared_cutoff = _date(meta.get("cutoff"))
    cutoff = min(declared_cutoff, observation) if declared_cutoff and observation else observation
    if not released or not cutoff or released >= cutoff:
        return None
    if dots.get("value_state") != "present":
        return None
    return released


def _read_gap(meta: dict, gap: dict, observation: date | None) -> dict:
    """The Fed-vs-market comparison — only when the producer's own rule admits it."""
    gap_meta = _mapping(meta.get("gap"))
    status = gap_meta.get("status") if isinstance(gap_meta.get("status"), str) else None
    reason = gap_meta.get("reason") if isinstance(gap_meta.get("reason"), str) else None
    out = {
        "available": False,
        "status": status,
        "reason": reason,
        "reason_en": "", "reason_zh": "",
        "gap_bp": None, "fed_dot": None, "market": None,
        "horizon_label": None, "horizon_months": None,
        "lean_en": None, "lean_zh": None,
        "window_start": None, "window_end": None,
        "rule_id": gap_meta.get("rule_id") if isinstance(gap_meta.get("rule_id"), str) else None,
        "transform": gap_meta.get("transform") if isinstance(gap_meta.get("transform"), str) else None,
        "limitations": [_text(x, MAX_SHORT_TEXT) for x in _seq(gap_meta.get("limitations"), 6)
                        if _text(x, MAX_SHORT_TEXT)],
    }
    selected = _text(meta.get("selected_strip"), 40)
    strip = _mapping(_mapping(meta.get("strips")).get(selected or ""))
    dots = _mapping(meta.get("dots"))
    if not _projection_date(meta, observation):
        out["reason_en"] = "The Fed projection's publication date is unqualified; no numerical comparison is shown."
        out["reason_zh"] = "美联储预测的发布日期尚未确认，暂不显示数值比较。"
        return out
    if (status != "comparable_after_transformation"
            or meta.get("selected_is_effr") is not True
            or strip.get("rate_index") != "EFFR"
            or strip.get("value_state") != "present"
            or gap_meta.get("rule_id") != "sep_vs_market_year_end.v1"
            or gap_meta.get("transform") != "year_end_interval_match"):
        out["reason_en"] = (
            "The market strip and the Fed projection are not on a matched measure, "
            "horizon and date window in this snapshot, so no spread is shown."
        )
        out["reason_zh"] = (
            "本次快照中，市场利率工具与美联储预测在计量口径、期限和日期窗口上不匹配，"
            "因此不显示价差。"
        )
        return out
    gb = _int(gap.get("gap_bp"))
    fed = _rate(gap.get("fed_dot"))
    mkt = _rate(gap.get("market"))
    hm = _int(gap.get("horizon_months"))
    epoch = _date(dots.get("target_epoch"))
    start, end = _date(gap_meta.get("market_reference_start")), _date(gap_meta.get("market_reference_end"))
    strip_date = _date(strip.get("observation_time"))
    supported = bool(epoch and epoch.month == 12 and epoch.day == 31
                     and start and end and start <= epoch.replace(day=1) <= epoch <= end
                     and strip_date and observation and strip_date <= observation
                     and hm is not None and 0 <= hm <= _MAX_MONTHS
                     and _int(gap_meta.get("market_horizon_months")) == hm
                     and fed is not None and mkt is not None and gb is not None
                     and abs(gb - round((mkt - fed) * 100)) <= 1)
    out.update({
        "available": supported,
        "gap_bp": gb if supported else None,
        "fed_dot": fed if supported else None,
        "market": mkt if supported else None,
        "horizon_months": hm if supported else None,
        "horizon_label": f"end-{epoch.year}" if epoch else None,
        "horizon_label_zh": f"{epoch.year}年末" if epoch else None,
        "lean_en": _text(gap.get("lean_en"), MAX_SHORT_TEXT),
        "lean_zh": _text(gap.get("lean_zh"), MAX_SHORT_TEXT),
        "window_start": _date_str(gap_meta.get("market_reference_start")),
        "window_end": _date_str(gap_meta.get("market_reference_end")),
    })
    if not out["available"]:
        out["reason_en"] = "The source dates, matching horizon or comparison values are incomplete; no spread is shown."
        out["reason_zh"] = "来源日期、匹配期限或比较数值不完整，暂不显示价差。"
    return out


def _read_rates(latest: dict, snapshot_date: date | None) -> dict:
    """The rates panel: market-implied path, qualified Fed comparison, dots."""
    fp = _mapping(_mapping(latest).get("fed_path"))
    meta = _mapping(fp.get("implied_source_meta"))
    has_meta = bool(meta)
    implied = _mapping(fp.get("implied"))
    source_en = _text(fp.get("implied_source_en"), MAX_SHORT_TEXT)
    source_zh = _text(fp.get("implied_source_zh"), MAX_SHORT_TEXT)
    selected = _text(meta.get("selected_strip"), 40)
    strip = _mapping(_mapping(meta.get("strips")).get(selected or ""))
    snapshot_date = _date(strip.get("observation_time")) or _date(fp.get("asof"))
    selected_is_effr = meta.get("selected_is_effr")

    points: list[dict] = []
    # The producer emits one key per CONFIGURED horizon; a present-but-None value
    # is a GAP, so the key set (not the value set) defines the axis.
    # The spot policy observation is a separate benchmark, not a futures node.
    # In particular, never join EFFR/target policy into a compounded-SOFR strip.
    for months in range(1, int(_MAX_MONTHS) + 1):
        key = f"m{months}"
        if key not in implied:
            continue
        val = _rate(implied.get(key))
        lab_en, lab_zh = _months_label(months)
        points.append({"key": key, "months": float(months), "value": val,
                       "label_en": lab_en, "label_zh": lab_zh, "known": val is not None})
    points.sort(key=lambda p: p["months"])

    gap = _read_gap(meta, _mapping(fp.get("gap")), snapshot_date)

    # --- Fed dots: only a dot with a KNOWN year-end target epoch can sit on the
    # elapsed-time axis. Everything else is tabulated by year. ---
    dots_meta = _mapping(meta.get("dots"))
    target_epoch = _date_str(dots_meta.get("target_epoch"))
    dots_value_state = dots_meta.get("value_state") if isinstance(dots_meta.get("value_state"), str) else None

    dot_rows: list[dict] = []
    dots_on_axis: list[dict] = []
    for d in _seq(fp.get("dots"), MAX_ITEMS):
        d = _mapping(d)
        year = _int(d.get("year"))
        median = _rate(d.get("median"))
        if year is None or not 1 <= year <= 9999 or median is None:
            continue
        epoch = target_epoch if (target_epoch and int(target_epoch[:4]) == year) else None
        epoch_d = _date(epoch)
        months = _months_between(snapshot_date, epoch_d) if (epoch_d and snapshot_date) else None
        on_axis = bool(
            epoch_d is not None and snapshot_date is not None
            and months is not None and 0.0 <= months <= _MAX_MONTHS
            and dots_value_state == "present"
            and (selected_is_effr is True)
            and _projection_date(meta, snapshot_date) is not None
        )
        row = {
            "year": year, "median": median,
            "target_epoch": epoch, "months": round(months, 2) if months is not None else None,
            "on_axis": on_axis,
            "target_label_en": epoch if epoch else f"end-{year}",
            "target_label_zh": epoch if epoch else f"{year}年末",
            "on_axis_label_en": "On the rate-path axis" if on_axis else "Tabulated by year",
            "on_axis_label_zh": "已在利率路径轴上" if on_axis else "按年份列表",
        }
        dot_rows.append(row)
        if on_axis:
            dots_on_axis.append(row)

    policy_rate = _rate(fp.get("policy_rate"))
    target_mid = _rate(fp.get("target_mid"))
    # The producer uses the effective rate when present, and falls back to
    # the target midpoint only for an absent policy rate. A malformed explicit
    # policy rate cannot establish that its stored spread used the fallback.
    if policy_rate is not None:
        bp_reference = ("effective fed funds", "有效联邦基金利率")
    elif fp.get("policy_rate") is None and target_mid is not None:
        bp_reference = ("target range midpoint", "目标区间中值")
    else:
        bp_reference = (None, None)
    current = target_mid if target_mid is not None else policy_rate
    current_label = ("Target range midpoint", "目标区间中值") if target_mid is not None else ("Effective fed funds rate", "有效联邦基金利率")
    extras = [d["median"] for d in dots_on_axis]
    if current is not None and selected_is_effr is True:
        extras.append(current)
    chart = _geometry(points, extras, _CHART)
    mobile_chart = _geometry(points, extras, _MOBILE_CHART, scale=(chart["y_min"], chart["y_max"]))
    spark = _geometry(points, [], _SPARK,
                      scale=(chart["y_min"], chart["y_max"]))

    # x ticks at the observed horizons (elapsed-time spacing)
    x_ticks = []
    for p in points:
        x_ticks.append({
            "months": p["months"], "x": chart["x_min"] + (p["months"] / _MAX_MONTHS)
            * (chart["x_max"] - chart["x_min"]),
            "label_en": "Now" if p["months"] == 0 else str(int(p["months"])),
            "label_zh": "现在" if p["months"] == 0 else str(int(p["months"])),
        })
    chart["x_ticks"] = [{**t, "x": round(t["x"], 2)} for t in x_ticks]

    # dot markers on the axis
    for d in dots_on_axis:
        m = d["months"]
        x = chart["x_min"] + (m / _MAX_MONTHS) * (chart["x_max"] - chart["x_min"])
        v = d["median"]
        y = chart["y_bottom"] - (v - chart["y_min"]) / ((chart["y_max"] - chart["y_min"]) or 1.0) \
            * (chart["y_bottom"] - chart["y_top"])
        d["x"] = round(x, 2)
        d["y"] = round(y, 2)

    # reference line = current policy rate (target mid / policy rate)
    reference = None
    if current is not None and selected_is_effr is True:
        y = chart["y_bottom"] - (current - chart["y_min"]) / ((chart["y_max"] - chart["y_min"]) or 1.0) \
            * (chart["y_bottom"] - chart["y_top"])
        # The direct label rides the RIGHT end of the rule and flips above or
        # below it, so it never lands on the "now" reading at the left edge.
        mid = (chart["y_top"] + chart["y_bottom"]) / 2
        reference = {"y": round(y, 2), "value": current,
                     "label_en": current_label[0], "label_zh": current_label[1],
                     "label_x": chart["x_max"],
                     "label_y": round(y + 13 if y > mid else y - 7, 2),
                     "label_anchor": "end"}
    chart["reference"] = reference
    chart["dots"] = dots_on_axis
    mobile_chart["x_ticks"] = [
        {**t, "x": round(mobile_chart["x_min"] + t["months"] / _MAX_MONTHS
                         * (mobile_chart["x_max"] - mobile_chart["x_min"]), 2)} for t in chart["x_ticks"]]
    mobile_chart["dots"] = [{**d,
        "x": round(mobile_chart["x_min"] + d["months"] / _MAX_MONTHS * (mobile_chart["x_max"] - mobile_chart["x_min"]), 2),
        "y": round(mobile_chart["y_bottom"] - (d["median"] - mobile_chart["y_min"]) / (mobile_chart["y_max"] - mobile_chart["y_min"]) * (mobile_chart["y_bottom"] - mobile_chart["y_top"]), 2)
    } for d in dots_on_axis]
    mobile_chart["reference"] = None
    if reference:
        mobile_y = round(mobile_chart["y_bottom"] - (current - mobile_chart["y_min"]) / (mobile_chart["y_max"] - mobile_chart["y_min"]) * (mobile_chart["y_bottom"] - mobile_chart["y_top"]), 2)
        mobile_chart["reference"] = {**reference, "y": mobile_y, "label_x": mobile_chart["x_max"],
                                      "label_y": mobile_y + 13 if mobile_y > (mobile_chart["y_top"] + mobile_chart["y_bottom"]) / 2 else mobile_y - 7}

    # table rows — a gap is shown as an explicit "not available", never as zero
    table = []
    for p in points:
        known = p["known"]
        n_m = int(p["months"])
        table.append({
            "key": p["key"],
            "horizon_en": "Now" if n_m == 0 else f"{n_m} month" + ("s" if n_m != 1 else ""),
            "horizon_zh": "现在" if n_m == 0 else f"{n_m}个月",
            "value": (f"{p['value']:.2f}%" if known else "not available"),
            "value_zh": (f"{p['value']:.2f}%" if known else "不可用"),
            "known": known,
            "source_en": source_en or "Source not recorded",
            "source_zh": source_zh or "来源未记录",
        })

    # the supported market horizon for the comparison
    mh = gap.get("horizon_months")
    market_horizon = {
        "known": mh is not None,
        "months": mh,
        "label_en": (f"{mh} months out ({gap.get('horizon_label')})" if mh is not None
                     else "No comparable horizon"),
        "label_zh": (f"{mh}个月后（{gap.get('horizon_label')}）" if mh is not None
                     else "无可比期限"),
        "window_start": gap.get("window_start"),
        "window_end": gap.get("window_end"),
        "observation_date": _date_str(strip.get("observation_time")),
    }

    notes = []
    if not any(p["known"] for p in points):
        notes.append({"en": "No market-implied rate path is present in this snapshot.",
                      "zh": "本次快照没有市场隐含利率路径。"})
    else:
        missing_h = [p for p in points if not p["known"]]
        if missing_h:
            notes.append({
                "en": ("Missing horizons are shown as gaps in the chart and as "
                       + ", ".join(p["label_en"] for p in missing_h)
                       + " in the table — never as zero."),
                "zh": ("缺失的期限在图中显示为缺口，在表中显示为"
                       + "、".join(p["label_zh"] for p in missing_h)
                       + "——绝不按零处理。"),
            })
    if has_meta and selected_is_effr is False:
        notes.append({"en": "The selected market strip is not a fed-funds basis; the "
                            "Fed projection is tabulated separately.",
                      "zh": "所选市场工具并非联邦基金利率口径，美联储预测另行列表呈现。"})
    if not has_meta:
        notes.append({"en": "This snapshot carries no source-basis metadata, so the "
                            "Fed-vs-market comparison is not shown.",
                      "zh": "本次快照没有口径元数据，因此不显示美联储与市场的比较。"})
    missing = [s for s in (_text(m, 60) for m in _seq(meta.get("missing_source"), 6)) if s]
    if missing:
        notes.append({"en": "Missing market inputs: " + ", ".join(missing),
                      "zh": "缺失的市场输入：" + "、".join(missing)})

    available = any(p["known"] for p in points)
    return {
        "available": available,
        "unit": "%",
        "points": points,
        "table": table,
        "chart": chart,
        "mobile_chart": mobile_chart,
        "spark": spark,
        "dots": dot_rows,
        "dots_on_axis": dots_on_axis,
        "reference": reference,
        "gap": gap,
        "market_horizon": market_horizon,
        "current_rate": {
            "known": current is not None,
            "value": current,
            "label_en": current_label[0],
            "label_zh": current_label[1],
            "source_en": "Fed target range" if target_mid is not None else "Effective federal funds observation",
            "source_zh": "美联储目标区间" if target_mid is not None else "有效联邦基金利率观测",
            "as_of": _date_str(fp.get("asof")),
        },
        "source_en": source_en,
        "source_zh": source_zh,
        "as_of": snapshot_date.isoformat() if snapshot_date else None,
        "bp_12m": (_rate(fp.get("implied_bp_12m"))
                   if selected_is_effr is True and bp_reference[0] else None),
        "bp_12m_basis_en": bp_reference[0],
        "bp_12m_basis_zh": bp_reference[1],
        "terminal_rate": _rate(implied.get("m12")),
        "projection_date": (_projection_date(meta, snapshot_date).isoformat()
                            if _projection_date(meta, snapshot_date) else None),
        "axis_en": "Fed funds rate (%)" if selected_is_effr is True else "Futures-implied rate (%)",
        "axis_zh": "联邦基金利率（%）" if selected_is_effr is True else "期货隐含利率（%）",
        "ntfs": _num(fp.get("ntfs")),
        "notes": notes,
        "basis_en": _text(_mapping(meta).get("selected_basis"), MAX_SHORT_TEXT),
    }


def _read_context(pl: dict, latest: dict, evw_snap: Any, flip: Any) -> dict:
    cal = _mapping(pl.get("calendar"))
    cal_note = _text(cal.get("context_note"), MAX_SHORT_TEXT)
    days = _int(cal.get("days_to_midterm"))
    event_date = _date_str(cal.get("event_date")) or _find_date_in_text(cal_note)
    evaluation = _instant(cal.get("evaluated_at"))
    snapshot = (evaluation.date().isoformat() if evaluation else
                _date_str(cal.get("evaluation_date")) or _date_str(cal.get("as_of")))
    explicit_calendar = any(k in cal for k in
                            ("event_date", "event_state", "evaluation_date", "evaluated_at", "days_since_midterm"))

    fc = _mapping(flip)
    last_event = _mapping(fc.get("last_event"))
    flip_known = bool(last_event)

    repricing = pl.get("repricing_components")
    if isinstance(repricing, list):
        channels = []
        for r in _seq(repricing, MAX_ITEMS):
            r = _mapping(r)
            en = _text(r.get("label_en"), 120) or _text(r.get("name"), 120)
            zh = _text(r.get("label_zh"), 120) or _text(r.get("name_zh"), 120) or en
            if en:
                channels.append({"label_en": en, "label_zh": zh})
        repricing_view = {
            "known": bool(channels) or not repricing, "channels": channels,
            "empty_en": "No active repricing channels are recorded in this snapshot.",
            "empty_zh": "本次快照未记录活跃的重定价渠道。",
            "unknown_en": "Recorded channel entries are unusable.", "unknown_zh": "记录的渠道条目不可用。",
        }
    else:
        repricing_view = {
            "known": False, "channels": [],
            "empty_en": "", "empty_zh": "",
            "unknown_en": ("This snapshot does not report repricing channels — that is "
                           "an absent field, not an empty channel list."),
            "unknown_zh": ("本次快照未报告重定价渠道——这是字段缺失，并非渠道列表为空。"),
        }

    evw = _mapping(evw_snap)
    td = _int(evw.get("td_to_fomc")) if evw.get("available") else None

    calendar_view = {
        "known": False,
        "days": days,
        "event_date": event_date,
        "as_of": snapshot,
        "note_en": cal_note or "",
        "note_zh": _text(cal.get("context_note_zh"), MAX_SHORT_TEXT) or cal_note or "",
        "label_en": "Midterm election context",
        "label_zh": "中期选举背景",
        "countdown_en": "",
        "countdown_zh": "",
        "state": "unknown",
        "unknown_en": "Election timing is unavailable in this snapshot.",
        "unknown_zh": "本次快照的选举时间信息不可用。",
    }
    if explicit_calendar:
        event = _date(cal.get("event_date"))
        evaluated_date = _date(snapshot)
        if event and evaluated_date:
            delta = (event - evaluated_date).days
            expected = "upcoming" if delta > 0 else "today" if delta == 0 else "past"
            stated_eval = _date(cal.get("evaluation_date"))
            consistent = (cal.get("event_state") == expected
                          and (not stated_eval or stated_eval == evaluated_date)
                          and (days == delta if delta >= 0 else
                               days is None and _int(cal.get("days_since_midterm")) == -delta))
            if consistent:
                calendar_view["known"] = True
                calendar_view["state"] = expected
                stamp = f" (evaluated {snapshot}, UTC)."
                stamp_zh = f"（按 {snapshot} UTC 计算）。"
                if delta > 0:
                    calendar_view["countdown_en"] = f"Recorded count: {delta} day{'s' if delta != 1 else ''} to {event_date}" + stamp
                    calendar_view["countdown_zh"] = f"记录的计数：距 {event_date} 还有{delta}天" + stamp_zh
                elif delta == 0:
                    calendar_view["countdown_en"] = f"Scheduled election date: {event_date}" + stamp
                    calendar_view["countdown_zh"] = f"预定选举日期：{event_date}" + stamp_zh
                else:
                    calendar_view["countdown_en"] = f"Scheduled date passed: {event_date} · {-delta} day{'s' if delta != -1 else ''} earlier" + stamp
                    calendar_view["countdown_zh"] = f"预定日期已过：{event_date} · {-delta}天前" + stamp_zh
        if not calendar_view["known"] and event_date:
            calendar_view["unknown_en"] = f"Scheduled date: {event_date}; recorded timing is incomplete or inconsistent."
            calendar_view["unknown_zh"] = f"预定日期：{event_date}；记录的时间信息不完整或不一致。"
    elif days is not None and days >= 0:
        calendar_view["known"] = True
        calendar_view["state"] = "legacy"
        when = event_date or "the recorded election date"
        when_zh = event_date or "记录的选举日期"
        stamp = f" (counted on {snapshot})" if snapshot else ""
        stamp_zh = f"（按 {snapshot} 计算）" if snapshot else ""
        calendar_view["countdown_en"] = (
            f"Recorded count: {days} day{'s' if days != 1 else ''} to {when}"
            + (f"{stamp}." if snapshot else "; calculation date unavailable."))
        calendar_view["countdown_zh"] = (
            f"记录的计数：距{when_zh}还有{days}天"
            + (f"{stamp_zh}。" if snapshot else "；计算日期不可用。"))

    flip_view = {
        "known": flip_known,
        "date": _date_str(last_event.get("event_date")),
        "description_en": _text(last_event.get("description"), MAX_TEXT) or "",
        "description_zh": _text(last_event.get("description_zh"), MAX_TEXT)
        or _text(last_event.get("description"), MAX_TEXT) or "",
        "label_en": "Last confirmed flip",
        "label_zh": "最近确认的翻转",
        "value_en": "",
        "value_zh": "",
    }
    if flip_known:
        d = flip_view["date"]
        desc_en = flip_view["description_en"]
        desc_zh = flip_view["description_zh"]
        flip_view["value_en"] = (f"{d} — {desc_en}" if d else desc_en) or "Not recorded"
        flip_view["value_zh"] = (f"{d} — {desc_zh}" if d else desc_zh) or "未记录"

    return {
        "calendar": calendar_view,
        "flip": flip_view,
        "repricing": repricing_view,
        "fomc": {
            "known": td is not None,
            "trading_days": td,
            "label_en": "FOMC in {n} trading days" if td is not None else "",
            "label_zh": "美联储会议还有{n}个交易日" if td is not None else "",
        },
    }


def _read_sources(pl: dict, rates: dict, latest: dict) -> list[dict]:
    """Per-input source / date / basis / quality. Only real, validated fields."""
    rows: list[dict] = []
    snap = _date_str(_mapping(pl.get("favored_complex")).get("as_of"))
    rows.append({
        "label_en": "Semiconductor drawdown", "label_zh": "半导体回撤",
        "value_en": "SMH / SOXX price observations",
        "value_zh": "SMH / SOXX 价格观测",
        "date": snap,
        "basis_en": "Equal-weight composite, trailing 120-day peak",
        "basis_zh": "等权组合，过去120日高点",
        "quality_en": "", "quality_zh": "",
    })
    fp = _mapping(_mapping(latest).get("fed_path"))
    meta = _mapping(fp.get("implied_source_meta"))
    strip_key = _text(meta.get("selected_strip"), 40)
    strip = _mapping(_mapping(meta).get("strips")).get(strip_key or "")
    strip = _mapping(strip)
    rows.append({
        "label_en": "Market-implied rate path", "label_zh": "市场隐含利率路径",
        "value_en": rates.get("source_en") or "Source not recorded",
        "value_zh": rates.get("source_zh") or "来源未记录",
        "date": _date_str(strip.get("observation_time")) or rates.get("as_of"),
        "basis_en": rates.get("basis_en") or "Not recorded",
        "basis_zh": rates.get("basis_en") or "未记录",
        "quality_en": ", ".join(_text(x, 90) for x in _seq(strip.get("limitations"), 4)
                                if _text(x, 90)),
        "quality_zh": ", ".join(_text(x, 90) for x in _seq(strip.get("limitations"), 4)
                                if _text(x, 90)),
    })
    dots_meta = _mapping(meta.get("dots"))
    rows.append({
        "label_en": "Fed projection (dot plot)", "label_zh": "美联储预测（点阵图）",
        "value_en": _text(dots_meta.get("source"), 90) or "FRED FEDTARMD (FOMC SEP median)",
        "value_zh": _text(dots_meta.get("source"), 90) or "FRED FEDTARMD（FOMC SEP 中位数）",
        "date": _date_str(dots_meta.get("vintage")) or _date_str(dots_meta.get("first_public_evidence")),
        "basis_en": _text(dots_meta.get("target"), 90) or "sep_fed_funds_year_end_median",
        "basis_zh": _text(dots_meta.get("target"), 90) or "sep_fed_funds_year_end_median",
        "quality_en": ", ".join(_text(x, 90) for x in _seq(dots_meta.get("limitations"), 4)
                                if _text(x, 90)),
        "quality_zh": ", ".join(_text(x, 90) for x in _seq(dots_meta.get("limitations"), 4)
                                if _text(x, 90)),
    })
    gap_meta = _mapping(meta.get("gap"))
    rows.append({
        "label_en": "Fed-vs-market comparison rule", "label_zh": "美联储与市场比较规则",
        "value_en": _text(gap_meta.get("rule_id"), 90) or "No basis rule recorded",
        "value_zh": _text(gap_meta.get("rule_id"), 90) or "未记录口径规则",
        "date": _date_str(fp.get("asof")),
        "basis_en": (f"verdict: {gap_meta.get('status')}" if gap_meta.get("status")
                     else "verdict: unavailable"),
        "basis_zh": (f"判定：{gap_meta.get('status')}" if gap_meta.get("status")
                     else "判定：不可用"),
        "quality_en": _text(gap_meta.get("transform"), 90) or "",
        "quality_zh": _text(gap_meta.get("transform"), 90) or "",
    })
    # any URL the payload actually carries — validated, never invented
    for key in _URL_KEYS:
        url = _safe_url(_mapping(pl).get(key))
        if url:
            rows.append({
                "label_en": "Source link", "label_zh": "来源链接",
                "value_en": url, "value_zh": url,
                "date": None, "basis_en": "", "basis_zh": "",
                "quality_en": "", "quality_zh": "",
            })
            break
    return rows


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #

def build_view(policy_lever: Any = None, latest: Any = None, *,
               evw_snap: Any = None, flip_confirmation: Any = None) -> dict:
    """Project the existing payloads into the Policy Monitor display model.

    Pure: the inputs are read, never written. A malformed section degrades on its
    own; the rest of the model is still produced.
    """
    pl = _mapping(policy_lever)
    lt = _mapping(latest)

    snapshot = _date(pl.get("as_of"))
    snapshot_str = snapshot.isoformat() if snapshot else None

    transmission = _read_transmission(pl)
    conditions = _read_conditions(pl, transmission)
    state = _read_state(pl, conditions)
    activity = _read_activity(pl)
    structure = _read_structure(pl)
    rates = _read_rates(lt, snapshot)
    stance = _read_stance(lt)
    guidance = _read_guidance(lt)
    context = _read_context(pl, lt, evw_snap, flip_confirmation)
    sources = _read_sources(pl, rates, lt)

    # --- evidence condition (independent of the conditions state) ------------ #
    ev_notes: list[dict] = []
    if not rates["available"]:
        ev_notes.append({"en": "No market-implied rate path in this snapshot.",
                         "zh": "本次快照没有市场隐含利率路径。"})
    if not activity["known_7d"] and not activity["known_30d"]:
        ev_notes.append({"en": "Recorded policy-alert counts are unavailable.",
                         "zh": "记录的政策提醒计数不可用。"})
    if not any(t["observed"]["known"] for t in transmission):
        ev_notes.append({"en": "No lever technical setup is observed in this snapshot.",
                         "zh": "本次快照没有可观测的杠杆技术形态。"})
    for t in transmission:
        if t["copy_stale"] and t["copy_as_of"]:
            age = t["copy_age_days"]
            ev_notes.append({
                "en": (f"“{t['name_en']}” narrative was last reviewed {t['copy_as_of']}"
                       + (f" ({age} days old)." if age is not None else ".")),
                "zh": (f"“{t['name_zh']}”叙述最后复核于 {t['copy_as_of']}"
                       + (f"（已 {age} 天）。" if age is not None else "。")),
            })
    known_sections = sum([
        1 if rates["available"] else 0,
        1 if (activity["known_7d"] or activity["known_30d"]) else 0,
        1 if any(t["observed"]["known"] for t in transmission) else 0,
        1 if structure["known"] else 0,
    ])
    if known_sections == 0:
        level, lbl = "missing", ("No policy evidence in this snapshot",
                                 "本次快照没有政策证据")
    elif known_sections >= 4:
        level, lbl = "complete", ("Core observations available", "主要观测可用")
    else:
        level, lbl = "partial", ("Partial coverage", "覆盖不完整")
    evidence = {
        "level": level,
        "label_en": lbl[0], "label_zh": lbl[1],
        "notes": ev_notes,
        "stale": any(t["copy_stale"] for t in transmission),
    }
    if evidence["stale"]:
        evidence["label_en"], evidence["label_zh"] = "Mixed freshness", "时效不一"
    stale_dates = sorted({t["copy_as_of"] for t in transmission if t["copy_stale"] and t["copy_as_of"]})
    evidence["summary_en"] = (f"Historical commentary · last reviewed {stale_dates[0]}" if stale_dates
                              else "Source dates and availability are listed by section.")
    evidence["summary_zh"] = (f"历史解读 · 最后复核于 {stale_dates[0]}" if stale_dates
                              else "各部分均列出来源日期与可用性。")

    framing_en = _text(pl.get("framing"), MAX_SHORT_TEXT)
    framing_zh = _text(pl.get("framing_zh"), MAX_SHORT_TEXT) or framing_en or ""

    # --- the RELATIVE market-vs-Fed read (only when the producer's own rule
    #     admits the comparison; a market price below a projection is a
    #     relative difference, never an absolute policy stance) -------------- #
    gap = rates["gap"]
    if gap["available"]:
        lean_en = gap["lean_en"] or ""
        lean_zh = gap["lean_zh"] or lean_en
        relative = {
            "known": True,
            "label_en": f"{gap['gap_bp']:+d} bp at {gap['horizon_label']}",
            "label_zh": f"{gap['horizon_label_zh']} {gap['gap_bp']:+d} 基点",
            "sub_en": (f"Market {gap['market']:.2f}% against the Fed's {gap['fed_dot']:.2f}% "
                       f"median dot" + (f" — {lean_en}" if lean_en else "")
                       + ". A relative pricing difference, not a policy stance."),
            "sub_zh": (f"市场 {gap['market']:.2f}% 对比美联储 {gap['fed_dot']:.2f}% 的中位点"
                       + (f"——{lean_zh}" if lean_zh else "")
                       + "。这是定价的相对差异，不是政策立场。"),
        }
    else:
        relative = {
            "known": False,
            "label_en": "Comparison unavailable",
            "label_zh": "比较不可用",
            "sub_en": gap["reason_en"],
            "sub_zh": gap["reason_zh"],
        }

    # --- structural context (the favored complex) -------------------------- #
    basket = structure["basket"]
    basket_label = "/".join(basket) if basket else ""
    dd = structure["drawdown_pct"]
    if dd is not None and basket_label:
        struct_en = (f"{basket_label} equal-weight is {dd:+.1f}% from its trailing-120-day peak"
                     + (f" (as of {structure['as_of']})" if structure["as_of"] else "") + ".")
        struct_zh = (f"{basket_label}等权组合距过去120日高点{dd:+.1f}%"
                     + (f"（截至 {structure['as_of']}）" if structure["as_of"] else "") + "。")
    elif basket_label:
        struct_en = f"{basket_label} — drawdown not computed in this snapshot."
        struct_zh = f"{basket_label}——本次快照未计算回撤。"
    else:
        struct_en = "Structural basket not recorded in this snapshot."
        struct_zh = "本次快照未记录结构性组合。"
    structure_view = {
        "label_en": "Structural context", "label_zh": "结构性背景",
        "value_en": struct_en, "value_zh": struct_zh,
        "caveat_en": structure["caveat_en"], "caveat_zh": structure["caveat_zh"],
    }

    # --- the card/dialog headline reads (no hike counts, no timing claims) --- #
    bp12 = rates.get("bp_12m")
    if bp12 is not None:
        move_en = f"12-month rate vs {rates['bp_12m_basis_en']} {bp12:+.0f} bp"
        move_zh = f"12个月利率相对{rates['bp_12m_basis_zh']} {bp12:+.0f} 基点"
    else:
        move_en = "Rate path change not recorded"
        move_zh = "未记录利率路径变动"

    return {
        "schema": VIEW_SCHEMA,
        "snapshot": {"date": snapshot_str, "known": snapshot is not None},
        "state": state,
        "conditions": conditions,
        "evidence": evidence,
        "rates": rates,
        "stance": stance,
        "guidance": guidance,
        "activity": activity,
        "transmission": transmission,
        "structure": structure,
        "structure_view": structure_view,
        "relative": relative,
        "context": context,
        "sources": sources,
        "framing_en": framing_en or "",
        "framing_zh": framing_zh,
        "move_en": move_en,
        "move_zh": move_zh,
        "methodology_en": (
            "Market-implied rates reflect the selected futures instrument. The spot policy "
            "observation is a separate benchmark, not a futures node. "
            "The Fed projection is the FOMC SEP median for the stated year-end. "
            "A market-vs-Fed spread requires a qualified publication date and an established "
            "comparison with a matched measure, horizon and date window; otherwise the two observations "
            "are listed separately and no spread is computed. Missing points are gaps, "
            "never zeros. Fed dots are placed by their actual year-end date; years "
            "outside the chart horizon are tabulated by year."
        ),
        "methodology_zh": (
            "市场隐含利率来自所选期货工具。即期政策利率是单独的参考值，不是期货曲线节点。美联储预测是FOMC SEP对应年末的中位数。"
            "仅当发布日期已确认，且现有比较规则确认计量口径、期限与日期窗口相匹配时才显示市场与美联储的价差；"
            "否则两项观测分别列出，不计算价差。缺失点为缺口，绝不按零处理。"
            "美联储点阵按实际年末日期定位，超出图表期限的年份按年份列表呈现。"
        ),
        "boundary_en": ("Conditions and market prices only — no administration intent, "
                        "no timing forecast, no trade instruction."),
        "boundary_zh": ("仅呈现条件与市场价格——不含政策意图、时点预测或交易指令。"),
        "footer_en": ("Context only — not a forecast: recorded conditions and market prices, "
                      "no administration intent and no timing call."),
        "footer_zh": ("仅供参考 — 非预测：已记录的条件与市场价格，不含政策意图，也不含时点判断。"),
    }


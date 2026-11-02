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
    when ``implied_source_meta.gap.status == "comparable_after_transformation"``.
    Otherwise the observations are shown separately and the comparison is
    reported as unavailable, with the rule's own reason.

The normalizer never asserts policy intent or timing (DNR:KILL-POLICY-TIMING-
PREDICTOR): it reports recorded conditions, market prices and dated narrative.
"""
from __future__ import annotations

import math
import re
from datetime import date, datetime
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
    s = _text(v, 40)
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(s).date()
    except ValueError:
        return None


def _date_str(v: Any) -> str | None:
    d = _date(v)
    return d.isoformat() if d else None


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
    step = min(max(step, 0.05), 5.0)
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

def _read_state(pl: dict) -> dict:
    raw = pl.get("state")
    state = raw if isinstance(raw, str) and raw.strip().upper() in _STATE_VALUES else None
    known = state is not None
    state = state.upper() if known else "UNKNOWN"
    summary = {
        "ARMED": ("Both conditions are met", "两项条件同时成立"),
        "ELEVATED": ("One condition is met", "一项条件成立"),
        "QUIET": ("Neither condition is met", "两项条件均未成立"),
        "UNKNOWN": ("Condition state not reported", "未记录条件状态"),
    }[state]
    watch = {
        "ARMED": ("Watch for confirmation in market prices — this is a condition, not a call.",
                  "留意市场价格确认——这是条件，不是交易指令。"),
        "ELEVATED": ("Watch for the second condition — one leg is in place.",
                     "留意第二项条件——目前只有一项成立。"),
        "QUIET": ("Watch for the drawdown or a lever setup to change.",
                  "留意回撤或杠杆技术形态是否变化。"),
        "UNKNOWN": ("The snapshot did not report a condition state.",
                    "本次快照未记录条件状态。"),
    }[state]
    stance = {
        "ARMED": ("Watch — conditions met, no call yet",
                  "观察 — 条件成立，但暂无交易结论"),
        "ELEVATED": ("Watch — one condition met",
                     "观察 — 一项条件成立"),
        "QUIET": ("Watch — no condition met",
                  "观察 — 暂无条件成立"),
        "UNKNOWN": ("Watch — state not reported",
                    "观察 — 未报告状态"),
    }[state]
    return {
        "value": state, "known": known,
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
    legs = []
    legs.append({
        "key": "drawdown",
        "label_en": "Semis complex 15%+ below its 120-day peak",
        "label_zh": "半导体组合较120日高点回撤达15%以上",
        "value_en": (f"{dd:+.1f}% from the 120-day peak" if dd is not None
                     else "Drawdown not computed"),
        "value_zh": (f"较120日高点{dd:+.1f}%" if dd is not None else "未计算回撤"),
        "known": dd is not None,
        "met": (dd <= _DRAWDOWN_LEG_PCT) if dd is not None else None,
    })
    observed = [t for t in transmission if t["observed"]["known"]]
    armed = [t for t in observed if t["observed"]["state"] == "armed"]
    legs.append({
        "key": "arming",
        "label_en": "A policy lever's technical setup is armed",
        "label_zh": "某一政策杠杆的技术形态已触发",
        "value_en": (f"{len(armed)} of {len(observed)} observed levers armed"
                     if observed else "No lever setup observed"),
        "value_zh": (f"{len(observed)}项可观测杠杆中{len(armed)}项已触发"
                     if observed else "无可观测的杠杆技术形态"),
        "known": bool(observed),
        "met": bool(armed) if observed else None,
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
        observed = {"known": False, "state": "unavailable",
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
                observed["state"] = "armed" if flag else "quiet"
                observed["label_en"] = "Armed" if flag else "Quiet"
                observed["label_zh"] = "已触发" if flag else "平静"
                observed["reason_en"] = ("Technical setup is armed." if flag
                                         else "Technical setup is not armed.")
                observed["reason_zh"] = ("技术形态已触发。" if flag else "技术形态未触发。")
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
    ts = _text(jw.get("last_alert_ts"), 60)
    note = _text(jw.get("_note"), MAX_SHORT_TEXT)
    summary_en = _text(jw.get("last_alert_summary"), MAX_SHORT_TEXT)
    summary_zh = _text(jw.get("last_alert_summary_zh"), MAX_SHORT_TEXT)
    coverage_en = ("Counts come from the producer's own 7-day and 30-day windows; "
                   "the artifact does not record the window end date.")
    coverage_zh = ("计数来自生产者自身的7日与30日窗口；该产物未记录窗口截止日期。")
    if note:
        coverage_en = f"{coverage_en} Producer note: {note}"
        coverage_zh = f"{coverage_zh} 生产者说明：{note}"
    return {
        "known_7d": n7 is not None, "n_7d": n7,
        "known_30d": n30 is not None, "n_30d": n30,
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


def _read_gap(meta: dict, gap: dict) -> dict:
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
    if status != "comparable_after_transformation":
        out["reason_en"] = (
            "The market strip and the Fed projection are not on a matched measure, "
            "horizon and date window in this snapshot, so no spread is shown."
        )
        out["reason_zh"] = (
            "本次快照中，市场利率工具与美联储预测在计量口径、期限和日期窗口上不匹配，"
            "因此不显示价差。"
        )
        if reason:
            out["reason_en"] += f" (Rule verdict: {reason}.)"
            out["reason_zh"] += f"（规则判定：{reason}。）"
        return out
    gb = _int(gap.get("gap_bp"))
    fed = _num(gap.get("fed_dot"))
    mkt = _num(gap.get("market"))
    hm = _int(gap.get("horizon_months"))
    out.update({
        "available": gb is not None and fed is not None and mkt is not None,
        "gap_bp": gb,
        "fed_dot": fed,
        "market": mkt,
        "horizon_months": hm,
        "horizon_label": _text(gap.get("horizon_label"), 40),
        "lean_en": _text(gap.get("lean_en"), MAX_SHORT_TEXT),
        "lean_zh": _text(gap.get("lean_zh"), MAX_SHORT_TEXT),
        "window_start": _date_str(gap_meta.get("market_reference_start")),
        "window_end": _date_str(gap_meta.get("market_reference_end")),
    })
    if not out["available"]:
        out["reason_en"] = ("The producer's comparison block is incomplete, so no spread "
                            "is shown.")
        out["reason_zh"] = "生产者的比较区块不完整，因此不显示价差。"
    return out


def _read_rates(latest: dict, snapshot_date: date | None) -> dict:
    """The rates panel: market-implied path, qualified Fed comparison, dots."""
    fp = _mapping(_mapping(latest).get("fed_path"))
    meta = _mapping(fp.get("implied_source_meta"))
    has_meta = bool(meta)
    implied = _mapping(fp.get("implied"))
    source_en = _text(fp.get("implied_source_en"), MAX_SHORT_TEXT)
    source_zh = _text(fp.get("implied_source_zh"), MAX_SHORT_TEXT)

    points: list[dict] = []
    # The producer emits one key per CONFIGURED horizon; a present-but-None value
    # is a GAP, so the key set (not the value set) defines the axis.
    if "now" in implied:
        now_v = _num(implied.get("now"))
        points.append({"key": "now", "months": 0.0, "value": now_v,
                       "label_en": "Now", "label_zh": "现在", "known": now_v is not None})
    for key in sorted(implied.keys()):
        m = _HORIZON_RE.match(key) if isinstance(key, str) else None
        if not m:
            continue
        months = int(m.group(1))
        val = _num(implied.get(key))
        lab_en, lab_zh = _months_label(months)
        points.append({"key": key, "months": float(months), "value": val,
                       "label_en": lab_en, "label_zh": lab_zh, "known": val is not None})
    points.sort(key=lambda p: p["months"])

    gap = _read_gap(meta, _mapping(fp.get("gap")))

    # --- Fed dots: only a dot with a KNOWN year-end target epoch can sit on the
    # elapsed-time axis. Everything else is tabulated by year. ---
    dots_meta = _mapping(meta.get("dots"))
    target_epoch = _date_str(dots_meta.get("target_epoch"))
    strip = _mapping(meta.get("strips")).get(_mapping(meta).get("selected_strip") or "")
    strip = _mapping(strip)
    selected_is_effr = _mapping(meta).get("selected_is_effr")
    dots_value_state = dots_meta.get("value_state") if isinstance(dots_meta.get("value_state"), str) else None

    dot_rows: list[dict] = []
    dots_on_axis: list[dict] = []
    for d in _seq(fp.get("dots"), MAX_ITEMS):
        d = _mapping(d)
        year = _int(d.get("year"))
        median = _num(d.get("median"))
        if year is None or median is None:
            continue
        epoch = target_epoch if (target_epoch and int(target_epoch[:4]) == year) else None
        epoch_d = _date(epoch)
        months = _months_between(snapshot_date, epoch_d) if (epoch_d and snapshot_date) else None
        on_axis = bool(
            epoch_d is not None and snapshot_date is not None
            and months is not None and 0.0 <= months <= _MAX_MONTHS
            and dots_value_state == "present"
            and (selected_is_effr is True)
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

    chart = _geometry(points, [d["median"] for d in dots_on_axis], _CHART)
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
    policy_rate = _num(fp.get("policy_rate"))
    target_mid = _num(fp.get("target_mid"))
    current = target_mid if target_mid is not None else policy_rate
    reference = None
    if current is not None:
        y = chart["y_bottom"] - (current - chart["y_min"]) / ((chart["y_max"] - chart["y_min"]) or 1.0) \
            * (chart["y_bottom"] - chart["y_top"])
        # The direct label rides the RIGHT end of the rule and flips above or
        # below it, so it never lands on the "now" reading at the left edge.
        mid = (chart["y_top"] + chart["y_bottom"]) / 2
        reference = {"y": round(y, 2), "value": current,
                     "label_en": "Policy rate today", "label_zh": "今日政策利率",
                     "label_x": chart["x_max"],
                     "label_y": round(y + 13 if y > mid else y - 7, 2),
                     "label_anchor": "end"}

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
    missing = [_text(m, 60) for m in _seq(_mapping(meta).get("missing_source"), 6)]
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
        "spark": spark,
        "dots": dot_rows,
        "dots_on_axis": dots_on_axis,
        "reference": reference,
        "gap": gap,
        "market_horizon": market_horizon,
        "current_rate": {
            "known": current is not None,
            "value": current,
            "label_en": "Policy rate today",
            "label_zh": "今日政策利率",
            "source_en": "Fed target range midpoint",
            "source_zh": "美联储目标区间中值",
            "as_of": _date_str(fp.get("asof")) or _date_str(_mapping(latest).get("date")),
        },
        "source_en": source_en,
        "source_zh": source_zh,
        "as_of": _date_str(fp.get("asof")),
        "bp_12m": _num(fp.get("implied_bp_12m")),
        "ntfs": _num(fp.get("ntfs")),
        "notes": notes,
        "basis_en": _text(_mapping(meta).get("selected_basis"), MAX_SHORT_TEXT),
    }


def _read_context(pl: dict, latest: dict, evw_snap: Any, flip: Any) -> dict:
    cal = _mapping(pl.get("calendar"))
    cal_note = _text(cal.get("context_note"), MAX_SHORT_TEXT)
    days = _int(cal.get("days_to_midterm"))
    event_date = _find_date_in_text(cal_note)
    snapshot = _date_str(pl.get("as_of"))

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
            "known": True, "channels": channels,
            "empty_en": "No active repricing channels are recorded in this snapshot.",
            "empty_zh": "本次快照未记录活跃的重定价渠道。",
            "unknown_en": "", "unknown_zh": "",
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
        "known": days is not None,
        "days": days,
        "event_date": event_date,
        "as_of": snapshot,
        "note_en": cal_note or "",
        "note_zh": _text(cal.get("context_note_zh"), MAX_SHORT_TEXT) or cal_note or "",
        "label_en": "Midterm election countdown",
        "label_zh": "中期选举倒计时",
        "countdown_en": "",
        "countdown_zh": "",
    }
    if days is not None:
        when = event_date or "the recorded election date"
        when_zh = event_date or "记录的选举日期"
        stamp = f" (counted on {snapshot})" if snapshot else ""
        stamp_zh = f"（按 {snapshot} 计算）" if snapshot else ""
        calendar_view["countdown_en"] = (
            f"{days} day{'s' if days != 1 else ''} to {when} — a count taken on the "
            f"snapshot date, not a live clock{stamp}.")
        calendar_view["countdown_zh"] = (
            f"距{when_zh}还有{days}天——按快照日计算，并非实时时钟{stamp_zh}。")

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
    snap = _date_str(pl.get("as_of"))
    rows.append({
        "label_en": "Policy conditions snapshot", "label_zh": "政策条件快照",
        "value_en": "site/policy_lever.json (Policy-Shock W2-F producer)",
        "value_zh": "site/policy_lever.json（Policy-Shock W2-F 生产者）",
        "date": snap,
        "basis_en": "Equal-weight SMH/SOXX composite, technical arming, recorded alerts",
        "basis_zh": "SMH/SOXX 等权组合、技术触发、记录的政策提醒",
        "quality_en": "", "quality_zh": "",
    })
    fp = _mapping(_mapping(latest).get("fed_path"))
    meta = _mapping(fp.get("implied_source_meta"))
    strip_key = _mapping(meta).get("selected_strip")
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
    state = _read_state(pl)
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
        level, lbl = "complete", ("Inputs present", "输入齐备")
    else:
        level, lbl = "partial", ("Partial coverage", "覆盖不完整")
    evidence = {
        "level": level,
        "label_en": lbl[0], "label_zh": lbl[1],
        "notes": ev_notes,
    }

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
            "label_zh": f"{gap['horizon_label']} {gap['gap_bp']:+d} 基点",
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
        move_en = f"12-month priced change {bp12:+.0f} bp"
        move_zh = f"未来12个月定价变动 {bp12:+.0f} 基点"
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
            "Market-implied rates are the futures-implied funds rate, shown as a price. "
            "The Fed projection is the FOMC SEP median for the stated year-end. "
            "A market-vs-Fed spread appears only when the producer's own rule finds a "
            "matched measure, horizon and date window; otherwise the two observations "
            "are listed separately and no spread is computed. Missing points are gaps, "
            "never zeros. Fed dots are placed by their actual year-end date; years "
            "outside the chart horizon are tabulated by year."
        ),
        "methodology_zh": (
            "市场隐含利率是期货隐含的基金利率，属于市场价格。美联储预测是FOMC SEP对应年末的中位数。"
            "仅当生产者自身规则确认计量口径、期限与日期窗口相匹配时才显示市场与美联储的价差；"
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

"""Display-tier descriptive leadership receipt for per-theme detail pages."""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

_THEME_STATE_MAX_AGE_DAYS = 5
_DEAD_BAND = 0.01
_WINDOW_SESSIONS = 20

_AUTHORITY = {
    "display_only": True,
    "may_rank": False,
    "may_size": False,
    "may_gate": False,
    "may_escalate": False,
}

_STANCE = {
    "leading": (
        "Leading its benchmark over the last 20 sessions",
        "近20个交易日跑赢基准",
    ),
    "lagging": (
        "Lagging its benchmark over the last 20 sessions",
        "近20个交易日落后基准",
    ),
    "mixed": (
        "Tracking its benchmark over the last 20 sessions",
        "近20个交易日与基准持平",
    ),
    "unavailable": (
        "No leadership read today",
        "今日无领涨判读",
    ),
}

def _parse_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _rel_hz(basket: dict, hz: str) -> float | None:
    perf = basket.get("perf") or {}
    block = perf.get(hz) or {}
    rel = block.get("rel")
    if rel is None:
        return None
    try:
        return float(rel)
    except (TypeError, ValueError):
        return None


def _roster_changed(basket: dict) -> bool:
    created = _parse_date(basket.get("created"))
    if created is None:
        return False
    for member in basket.get("members") or []:
        if not isinstance(member, dict):
            continue
        added = _parse_date(member.get("curated_added") or member.get("added"))
        if added is not None and added > created:
            return True
    return False


def _load_theme_state_payload(site: Path | None) -> dict | None:
    if site is None:
        return None
    path = site / "neuralwebdata" / "theme_state.json"
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return raw if isinstance(raw, dict) else None


def _theme_state_block(
    basket_id: str,
    region: str,
    theme_intel: dict,
    site: Path | None,
) -> dict[str, Any]:
    if region != "us":
        return {
            "status": "not_published",
            "as_of": None,
            "stale_legs_n": 0,
            "quadrant": None,
        }

    payload = _load_theme_state_payload(site)
    if payload is None:
        return {
            "status": "missing",
            "as_of": None,
            "stale_legs_n": 0,
            "quadrant": None,
        }

    stale_legs = payload.get("stale_legs")
    stale_n = len(stale_legs) if isinstance(stale_legs, list) else 0
    ts_as_of = _parse_date(payload.get("as_of"))
    ti_as_of = _parse_date(theme_intel.get("as_of"))

    quadrant = None
    themes = payload.get("themes")
    if isinstance(themes, list):
        for item in themes:
            if not isinstance(item, dict):
                continue
            basket_ids = item.get("basket_ids")
            if not isinstance(basket_ids, list) or basket_id not in basket_ids:
                continue
            rot = item.get("subsector_rotation") or {}
            if isinstance(rot, dict):
                quadrant = rot.get("rollup_quadrant")
            break
        else:
            return {
                "status": "missing",
                "as_of": ts_as_of.isoformat() if ts_as_of else None,
                "stale_legs_n": stale_n,
                "quadrant": None,
            }
    else:
        return {
            "status": "missing",
            "as_of": ts_as_of.isoformat() if ts_as_of else None,
            "stale_legs_n": stale_n,
            "quadrant": None,
        }

    status = "fresh"
    if ts_as_of is None or ti_as_of is None:
        status = "missing"
    elif (ti_as_of - ts_as_of).days > _THEME_STATE_MAX_AGE_DAYS:
        status = "stale"

    return {
        "status": status,
        "as_of": ts_as_of.isoformat() if ts_as_of else None,
        "stale_legs_n": stale_n,
        "quadrant": quadrant,
    }


def _unavailable_reason(
    rel_20d: float | None,
    obs: dict,
) -> tuple[str, str] | None:
    min_members = int(obs.get("min_members") or 0)
    min_coverage = float(obs.get("min_coverage") or 0)
    coverage = obs.get("coverage")
    try:
        coverage_f = float(coverage) if coverage is not None else None
    except (TypeError, ValueError):
        coverage_f = None

    if rel_20d is None:
        return ("price panel incomplete", "价格面板不完整")
    if obs.get("status") != "complete":
        return ("price panel incomplete", "价格面板不完整")
    if obs.get("aggregate_eligible") is False:
        en = f"fewer than {min_members} members observed"
        zh = f"观察到的成分少于{min_members}个"
        return (en, zh)
    if coverage_f is not None and coverage_f < min_coverage:
        pct = f"{min_coverage:.0%}"
        return (f"coverage below {pct}", f"覆盖率低于{pct}")
    return None


def _state_from_rel(rel_20d: float) -> str:
    if rel_20d >= _DEAD_BAND:
        return "leading"
    if rel_20d <= -_DEAD_BAND:
        return "lagging"
    return "mixed"


def _freshness_row(ts: dict[str, Any]) -> tuple[str, str]:
    status = ts.get("status")
    ts_as_of = ts.get("as_of") or "—"
    stale_n = ts.get("stale_legs_n") or 0
    if status == "fresh":
        en = (
            f"Theme state as of {ts_as_of} — current; "
            f"{stale_n} inputs flagged stale."
        )
        zh = (
            f"主题状态截至{ts_as_of}——当前；{stale_n}项输入标记为陈旧。"
        )
    elif status == "stale":
        en = f"Theme state as of {ts_as_of} — more than 5 days old; read with care."
        zh = f"主题状态截至{ts_as_of}——超过5天；请谨慎阅读。"
    elif status == "not_published":
        en = "Theme state is not published for this market; the read uses prices only."
        zh = "该市场未发布主题状态；本判读仅使用价格。"
    else:
        en = "Theme state not available for this basket today."
        zh = "今日该篮子无可用主题状态。"
    return en, zh


def _build_rows(
    *,
    as_of: str,
    bench_en: str,
    bench_zh: str,
    obs: dict,
    ts: dict[str, Any],
) -> list[dict[str, str]]:
    eff = obs.get("effective_as_of") or as_of
    observed_n = obs.get("observed_n", "—")
    configured_n = obs.get("configured_n", "—")
    try:
        coverage_pct = f"{float(obs.get('coverage')):.0%}"
    except (TypeError, ValueError):
        coverage_pct = "—"

    fresh_en, fresh_zh = _freshness_row(ts)

    return [
        {
            "key": "interval",
            "label_en": "Observation interval",
            "label_zh": "观察区间",
            "text_en": (
                f"Daily close-to-close returns over 5, 20 and 60 sessions, as of {as_of}."
            ),
            "text_zh": f"按日收盘价计算的5、20、60个交易日收益，截至{as_of}。",
        },
        {
            "key": "benchmark",
            "label_en": "Benchmark",
            "label_zh": "基准",
            "text_en": (
                f"{bench_en}, cap-weighted. The basket is equal-weight and rebalanced "
                "monthly, so part of any gap is weighting, not stock selection."
            ),
            "text_zh": (
                f"{bench_zh}，市值加权。篮子为等权、按月再平衡，"
                "因此差距有一部分来自权重而非选股。"
            ),
        },
        {
            "key": "measure",
            "label_en": "Raw, not normalized",
            "label_zh": "原始值，未标准化",
            "text_en": (
                "Raw excess return: basket return minus benchmark return, in percentage "
                "points. Not volatility- or beta-adjusted."
            ),
            "text_zh": (
                "原始超额收益：篮子收益减基准收益，以百分点计。"
                "未按波动率或贝塔调整。"
            ),
        },
        {
            "key": "sample",
            "label_en": "Sample and roster",
            "label_zh": "样本与成分",
            "text_en": (
                f"{observed_n} of {configured_n} members observed (coverage {coverage_pct}) "
                f"at {eff}. Roster is today's; history before a member's curation date is "
                "context, not a track record. Names are never backfilled into past memberships."
            ),
            "text_zh": (
                f"截至{eff}观察到{configured_n}个成分中的{observed_n}个（覆盖率{coverage_pct}）。"
                "成分为当前名单；成分纳入日之前的历史仅作背景，不是业绩记录。"
                "不会把今天的名字回填进过去的成分。"
            ),
        },
        {
            "key": "freshness",
            "label_en": "Freshness and coverage",
            "label_zh": "新鲜度与覆盖",
            "text_en": fresh_en,
            "text_zh": fresh_zh,
        },
        {
            "key": "authority",
            "label_en": "Diagnostic authority",
            "label_zh": "判读权限",
            "text_en": (
                "Display-only context. It never ranks, sizes, gates or escalates, "
                "and it is not a forecast."
            ),
            "text_zh": (
                "仅作展示背景。不排序、不定仓位、不设门槛、不升级，也不是预测。"
            ),
        },
    ]


def _unavailable_receipt(reason_en: str, reason_zh: str) -> dict[str, Any]:
    stance_en, stance_zh = _STANCE["unavailable"]
    return {
        "schema": "mi.leadership_receipt.v1",
        "state": "unavailable",
        "stance_en": stance_en,
        "stance_zh": stance_zh,
        "reason_en": reason_en,
        "reason_zh": reason_zh,
        "window_sessions": _WINDOW_SESSIONS,
        "rel_5d": None,
        "rel_20d": None,
        "rel_60d": None,
        "benchmark": {"label": "—", "label_zh": "—"},
        "as_of": None,
        "sample": {},
        "roster_changed": False,
        "breadth": {"pct50": None, "pct200": None, "n": None, "label": None},
        "leaders": [],
        "split": {"flag": False, "note_en": None, "note_zh": None},
        "theme_state": {
            "status": "missing",
            "as_of": None,
            "stale_legs_n": 0,
            "quadrant": None,
        },
        "authority": dict(_AUTHORITY),
        "rows": [],
    }


def build_receipt(
    basket: dict,
    theme: dict,
    theme_intel: dict,
    region: str,
    site: Path | None,
) -> dict[str, Any]:
    """Pure, fail-soft leadership receipt; never raises."""
    try:
        return _build_receipt_core(basket, theme, theme_intel, region, site)
    except Exception:  # noqa: BLE001 — display tier must not break the page
        return _unavailable_receipt("receipt_error", "收据生成错误")


def _build_receipt_core(
    basket: dict,
    theme: dict,
    theme_intel: dict,
    region: str,
    site: Path | None,
) -> dict[str, Any]:
    obs = basket.get("observation") or {}
    rel_5d = _rel_hz(basket, "5d")
    rel_20d = _rel_hz(basket, "20d")
    rel_60d = _rel_hz(basket, "60d")

    bench_en = theme_intel.get("bench_label") or "S&P 500"
    bench_zh = theme_intel.get("bench_label_zh") or "标普500"
    as_of = obs.get("effective_as_of") or theme_intel.get("as_of")

    ts = _theme_state_block(basket.get("id") or "", region, theme_intel, site)

    reason = _unavailable_reason(rel_20d, obs)
    if reason is not None:
        rec = _unavailable_receipt(reason[0], reason[1])
        rec["rel_5d"] = rel_5d
        rec["rel_20d"] = rel_20d
        rec["rel_60d"] = rel_60d
        rec["benchmark"] = {"label": bench_en, "label_zh": bench_zh}
        rec["as_of"] = as_of
        rec["sample"] = {
            "observed_n": obs.get("observed_n"),
            "configured_n": obs.get("configured_n"),
            "coverage": obs.get("coverage"),
            "status": obs.get("status"),
            "basis": obs.get("basis"),
            "aggregate_eligible": obs.get("aggregate_eligible"),
            "min_members": obs.get("min_members"),
            "min_coverage": obs.get("min_coverage"),
        }
        rec["theme_state"] = ts
        rec["rows"] = _build_rows(
            as_of=str(as_of or "—"),
            bench_en=bench_en,
            bench_zh=bench_zh,
            obs=obs,
            ts=ts,
        )
        return rec

    state = _state_from_rel(rel_20d)  # type: ignore[arg-type]
    stance_en, stance_zh = _STANCE[state]

    breadth_raw = theme.get("breadth") or {}
    leadership = theme.get("leadership") or {}
    leaders_out = []
    for item in (leadership.get("top") or [])[:3]:
        if not isinstance(item, dict):
            continue
        leaders_out.append(
            {"ticker": item.get("ticker"), "ret_20d": item.get("ret_20d")}
        )

    split_flag = bool(theme.get("leadership_split"))
    rows = _build_rows(
        as_of=str(as_of or "—"),
        bench_en=bench_en,
        bench_zh=bench_zh,
        obs=obs,
        ts=ts,
    )

    return {
        "schema": "mi.leadership_receipt.v1",
        "state": state,
        "stance_en": stance_en,
        "stance_zh": stance_zh,
        "reason_en": None,
        "reason_zh": None,
        "window_sessions": _WINDOW_SESSIONS,
        "rel_5d": rel_5d,
        "rel_20d": rel_20d,
        "rel_60d": rel_60d,
        "benchmark": {"label": bench_en, "label_zh": bench_zh},
        "as_of": as_of,
        "sample": {
            "observed_n": obs.get("observed_n"),
            "configured_n": obs.get("configured_n"),
            "coverage": obs.get("coverage"),
            "status": obs.get("status"),
            "basis": obs.get("basis"),
            "aggregate_eligible": obs.get("aggregate_eligible"),
            "min_members": obs.get("min_members"),
            "min_coverage": obs.get("min_coverage"),
        },
        "roster_changed": _roster_changed(basket),
        "breadth": {
            "pct50": breadth_raw.get("pct50"),
            "pct200": breadth_raw.get("pct200"),
            "n": breadth_raw.get("n"),
            "label": leadership.get("breadth"),
        },
        "leaders": leaders_out,
        "split": {
            "flag": split_flag,
            "note_en": theme.get("leadership_split_note_en"),
            "note_zh": theme.get("leadership_split_note_zh"),
        },
        "theme_state": ts,
        "authority": dict(_AUTHORITY),
        "rows": rows,
    }


__all__ = ["build_receipt", "_THEME_STATE_MAX_AGE_DAYS"]

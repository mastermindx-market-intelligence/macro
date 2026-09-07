"""Small homepage projection of the existing Macro & Monetary workspaces.

No data production, score, state classification, forecast or trading authority.
The shared manifest reader validates each input; the shared view supplies owner
state labels and formatting. This module selects only a fixed set of facts and
translates existing contradiction/availability metadata for the glance tier.
"""
from __future__ import annotations
from datetime import date
import math
from pathlib import Path
from typing import Any, Mapping
from lib import macro_suite_labels as labels
from lib import macro_suite_view
from scripts.build_macro_suite_pages import SUITE_PAGES, SnapshotRefused, read_workspace


def _pair(en: str, zh: str) -> dict[str, str]:
    return {"en": en, "zh": zh}


# Editorial selection, not another workspace/state registry. Route and identity
# continue to come from the existing suite page registry below.
_TOPICS = (
    ("growth_real_economy", _pair("Growth", "增长"), (
        ("gdpnow_growth", _pair("GDPNow estimate", "GDPNow 预估"), "pct_saar", _pair("% annualized", "% 年化")),
        ("wei_growth", _pair("Weekly activity", "每周经济活动"), "pct_annualized_equiv", _pair("% annual-equivalent", "% 年化等值")))),
    ("inflation_system", _pair("Inflation", "通胀"), (
        ("headline_cpi_yoy_pct", _pair("Headline CPI", "总体 CPI"), "pct_yoy", _pair("% year-on-year", "% 同比")),
        ("core_cpi_yoy_pct", _pair("Core CPI", "核心 CPI"), "pct_yoy", _pair("% year-on-year", "% 同比")))),
    ("financial_conditions", _pair("Financial conditions", "金融条件"), (
        ("real_10y", _pair("10-year real yield", "10 年期实际收益率"), "pct", _pair("%", "%")),
        ("hy_oas_pct", _pair("High-yield spread", "高收益债利差"), "pct", _pair("percentage points", "个百分点")))),
)
_USABLE = frozenset({"CURRENT", "LATE_WITHIN_TOLERANCE"})
_VALUE_STATUS = frozenset({"PRESENT", "DISAGREEMENT"})


def _period(value: Any) -> str | None:
    """Admit an exact owner-supplied ISO day/month; never substitute build time."""
    if not isinstance(value, str):
        return None
    try:
        if len(value) == 7:
            return value if date.fromisoformat(value + "-01").isoformat()[:7] == value else None
        if len(value) == 10:
            return value if date.fromisoformat(value).isoformat() == value else None
    except ValueError:
        pass
    return None


def _empty(wid: str, title: dict[str, str], href: str, reason: str) -> dict:
    note = (_pair("Older inputs prevent a current read.", "数据较旧，暂不能给出当前读数。")
            if reason == "STALE_SOURCE" else
            _pair("This read could not be verified. Inspect the source details.", "暂无法核实此读数，请查看来源详情。"))
    return {"id": wid, "title": title, "state": _pair("Read unavailable", "暂无法读取"),
            "note": note, "facts": [], "asof": None, "tone": "unavailable", "basis": None,
            "availability": _pair("Source check needed", "需核对来源"), "href": href,
            "link": _pair("Investigate", "查看详情"), "receipt": note,
            "source": {"digest": None, "authority": None, "reason": reason}}


def _fact(raw: Mapping[str, Any] | None, spec: tuple) -> dict:
    mid, title, expected_unit, unit = spec
    value = raw.get("value") if raw else None
    usable = (raw is not None and raw.get("status") in _VALUE_STATUS
              and raw.get("freshness") in _USABLE and raw.get("unit") == expected_unit
              and isinstance(value, (int, float)) and not isinstance(value, bool)
              and math.isfinite(value))
    text = labels.fmt_number(value) if usable else None
    display = (_pair(f"{text}{unit['en']}" if unit['en'].startswith('%') else f"{text} {unit['en']}",
                     f"{text}{unit['zh']}" if unit['zh'].startswith('%') else f"{text} {unit['zh']}")
               if text is not None else _pair("Not provided", "暂未提供"))
    period = _period(raw.get("reference_period")) if usable else None
    return {"metric_id": mid, "label": title, "value": display, "period": period,
            "date_note": _pair("Date unavailable", "日期不明") if usable and period is None else None}


def _includes_estimates(snapshot: Mapping[str, Any]) -> bool:
    """Disclose a present model input without reclassifying the owner's state."""
    for axis in snapshot["axes"]["items"]:
        for component in axis["components"]:
            value, weight = component.get("standardized_value"), component.get("weight")
            if (component.get("freshness") == "SIMULATED"
                    and isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
                    and isinstance(weight, (int, float)) and not isinstance(weight, bool)
                    and math.isfinite(weight) and weight > 0):
                return True
    return False


def _note(snapshot: Mapping[str, Any]) -> dict[str, str]:
    contradiction = snapshot["availability"].get("contradiction") or {}
    if contradiction.get("present") is True:
        if contradiction.get("kind") == "nowcast_vs_hard_data":
            return _pair("Estimates are stronger than the reported activity.", "预估较强，但已公布的经济活动尚未印证。")
        if contradiction.get("kind") == "sticky_led_but_headline_disinflationary":
            return _pair("Headline prices are cooling, but price pressure remains.", "总体价格正在降温，但价格压力依然存在。")
        return _pair("The underlying readings disagree. Inspect the drivers.", "底层读数存在分歧，请查看驱动因素。")
    if snapshot["headline"].get("hysteresis", {}).get("held_prior") is True:
        return _pair("Near a dividing line; inspect the drivers.", "读数接近分界，请查看驱动因素。")
    return _pair("Read the drivers behind this state.", "查看这一状态背后的驱动因素。")


def build_economic_backdrop(data_root: Path, *, page_built_at: str) -> list[dict]:
    """Read three independently dated workspaces without creating a fused read."""
    registered = {p.workspace_id: p for p in SUITE_PAGES}
    cards = []
    for wid, title, selected in _TOPICS:
        page = registered[wid]
        href = "/" + page.output
        try:
            snapshot, artifact = read_workspace(Path(data_root), page)
            availability = snapshot["availability"]
            required = availability.get("required") or []
            health = availability.get("state")
            failed_leg = next((r.get("freshness") if r.get("freshness") not in _USABLE else "SOURCE_FAILED"
                               for r in required if r.get("freshness") not in _USABLE or r.get("status") not in _VALUE_STATUS), None)
            if health not in _USABLE or availability.get("worst_freshness") not in _USABLE or not required or failed_leg:
                cards.append(_empty(wid, title, href, failed_leg or health or "SOURCE_FAILED"))
                continue
            view = macro_suite_view.build_view(snapshot, page_built_at=page_built_at, artifact=artifact)
            headline = view["headline"]
            state = headline.get("state_label")
            asof = _period(snapshot["generation"].get("calculation_as_of"))
            if (headline.get("status") != "PRESENT" or not headline.get("state_id") or asof is None
                    or not isinstance(state, dict) or not all(isinstance(state.get(l), str) and state[l].strip() for l in ("en", "zh"))):
                cards.append(_empty(wid, title, href, "COMPUTATION_REFUSED"))
                continue
            metric_rows = snapshot["metrics"]["items"]
            metric_ids = [item["metric_id"] for item in metric_rows]
            if len(metric_ids) != len(set(metric_ids)):
                cards.append(_empty(wid, title, href, "DISAGREEMENT"))
                continue
            metrics = {item["metric_id"]: item for item in metric_rows}
            note = _note(snapshot)
            has_tension = availability.get("contradiction", {}).get("present") is True
            cards.append({
                "id": wid, "title": title, "state": state, "note": note,
                "facts": [_fact(metrics.get(spec[0]), spec) for spec in selected],
                "asof": asof, "tone": "warn" if has_tension else "neutral",
                "availability": None,
                "basis": _pair("Includes estimates", "含预估") if _includes_estimates(snapshot) else None,
                "href": href, "link": _pair("Investigate", "查看详情"),
                "receipt": _pair(
                    "Dates are supplied by the source. CPI dates label a reference month; other fact dates are the source as-of, not the period of economic activity. Calculated is the workspace calculation cut, not fresh data. A page build does not refresh inputs. Estimates are identified; this read is not a trade instruction.",
                    "日期由来源提供。CPI日期表示参考月份；其他分项日期表示来源截止，并非经济活动的统计期间。计算截止和页面生成不代表数据更新。预估会明确标注，此读数不是交易指令。"),
                "source": {"digest": artifact["sha256"], "authority": snapshot["authority"]["class"],
                           "generation_id": snapshot["generation"]["generation_id"], "availability_state": health, "reason": None},
            })
        except SnapshotRefused as exc:
            cards.append(_empty(wid, title, href, exc.kind))
        except (ValueError, TypeError, KeyError, OSError):
            cards.append(_empty(wid, title, href, "SOURCE_FAILED"))
    return cards

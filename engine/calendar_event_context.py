"""Reference context over the existing calendar; never another event/forecast store.

F05/RIC first non-forecast vertical. The calendar owns event identity and schedule.
This pure projection adds reviewed reading questions and source-supplied auction
terms. It does NOT fetch results, infer consensus, generate an LLM assessment,
assert market exposure, score events, or manufacture an intraday known-at clock.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re
from typing import Any

SCHEMA = "calendar_event_context.v1"
METHOD_VERSION = "reference-playbooks-2026-09-17.1"
TREASURY_URL = "https://www.treasurydirect.gov/auctions/announcements-data-results/"


def _pair(en: str, zh: str) -> dict[str, str]:
    return {"en": en, "zh": zh}


# Editorial reference questions, NOT claims about an event's actual outcome.
# Official source links identify the relevant publisher, not publication receipts.
_PLAYBOOKS = {
    "CPI": ("Separate broad inflation from a few volatile components.", "区分广泛通胀与少数波动较大的分项。",
            "Which core, shelter and energy components explain the change?", "核心、住房与能源分项如何解释变化？", "https://www.bls.gov/cpi/"),
    "PPI": ("Read producer-price components before inferring consumer-price pressure.", "先读生产者价格分项，再判断消费价格压力。",
            "Do goods, services and margins tell the same story?", "商品、服务与利润率是否传递相同信息？", "https://www.bls.gov/ppi/"),
    "NFP": ("Read jobs, wages, participation and earlier revisions together.", "结合就业、工资、参与率及前期修订阅读。",
            "Does hiring breadth agree with wages, hours and the household survey?", "招聘广度是否与工资、工时及家庭调查一致？", "https://www.bls.gov/ces/"),
    "CLAIMS": ("Separate a weekly move from the trend and revisions.", "区分单周波动、趋势及修订。",
               "Do initial claims, continuing claims and the four-week average agree?", "初请、续请与四周均值是否一致？", "https://www.dol.gov/ui/data.pdf"),
    "GDP": ("Separate final demand from inventory and trade contributions.", "区分最终需求、库存与贸易贡献。",
            "Which components changed, and which earlier estimates were revised?", "哪些分项发生变化，哪些前期估计被修订？", "https://www.bea.gov/data/gdp/gross-domestic-product"),
    "PCE": ("Read prices alongside income, spending and revisions.", "结合收入、消费及修订阅读价格变化。",
            "Does real spending support the headline growth and inflation story?", "实际消费是否支持总体增长与通胀解读？", "https://www.bea.gov/data/personal-consumption-expenditures-price-index"),
    "ISM_MFG": ("Compare manufacturing activity with orders, employment and prices.", "结合订单、就业与价格比较制造业活动。",
                "Is the headline move broad or concentrated in one component?", "总体变化是广泛发生还是集中在一个分项？", "https://www.ismworld.org/supply-management-news-and-reports/reports/ism-report-on-business/"),
    "ISM_SVC": ("Compare services activity with orders, employment and prices.", "结合订单、就业与价格比较服务业活动。",
                "Do demand and employment agree, or is the survey mixed?", "需求与就业是否一致，还是调查信号分化？", "https://www.ismworld.org/supply-management-news-and-reports/reports/ism-report-on-business/"),
    "FOMC": ("Keep the decision, statement, projections and press conference distinct.", "区分决议、声明、预测及新闻发布会。",
             "What changed in the official text, and what remains interpretation?", "官方文本改变了什么，哪些仍属于解读？", "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"),
    "OPEX": ("Expiry is market-structure context, not a directional prediction.", "到期属于市场结构背景，不是方向预测。",
             "Which observed exposures and liquidity conditions support a pinning or unwind hypothesis?", "哪些已观测敞口与流动性条件支持钉住或平仓假说？", "https://www.cboe.com/tradable_products/options/options_calendar/"),
    "EIA": ("Compare inventories with production, imports, refinery activity and seasonality.", "结合产量、进口、炼厂活动与季节性比较库存。",
            "Is the stock change explained by flows or a reporting effect?", "库存变化来自实际流量还是报告因素？", "https://www.eia.gov/petroleum/supply/weekly/"),
    "EIA_WPSR": ("Compare inventories with production, imports, refinery activity and seasonality.", "结合产量、进口、炼厂活动与季节性比较库存。",
                 "Is the stock change explained by flows or a reporting effect?", "库存变化来自实际流量还是报告因素？", "https://www.eia.gov/petroleum/supply/weekly/"),
    "OPEC": ("Separate announced targets from implementation and observed supply.", "区分宣布目标、执行情况与实际供应。",
             "What is confirmed, when does it take effect, and what supply evidence could contradict it?", "哪些已确认、何时生效、哪些供应证据可能与之矛盾？", "https://www.opec.org/"),
}


def _source_date(value: Any) -> str | None:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T[0-9:.+Z-]+)?", value):
        return None
    try:
        return date.fromisoformat(value[:10]).isoformat()
    except ValueError:
        return None


def _amount(value: Any) -> str | None:
    # Treasury offeringAmount is dollars. Do not guess units or parse prose.
    if isinstance(value, bool) or value is None:
        return None
    text = str(value).strip()
    if not re.fullmatch(r"[0-9]{1,16}(?:\.[0-9]{1,2})?", text):
        return None
    try:
        number = Decimal(text)
        return format(number, "f") if number.is_finite() and number > 0 else None
    except InvalidOperation:
        return None


def auction_security_type(row: dict) -> str:
    """Treasury's securityType may be Note for both TIPS and FRNs."""
    if row.get("tips") == "Yes" or row.get("type") == "TIPS":
        return "TIPS"
    if row.get("floatingRate") == "Yes" or row.get("type") == "FRN":
        return "FRN"
    return str(row.get("securityType") or "")


def auction_close_time(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    for fmt in ("%I:%M %p", "%H:%M", "%I:%M:%S %p"):
        try:
            return datetime.strptime(value.strip(), fmt).strftime("%H:%M")
        except ValueError:
            continue
    return None


def _fact(key: str, en: str, zh: str, value: Any) -> dict:
    return {"key": key, "label": _pair(en, zh), "value": value,
            "state": "source_supplied" if value is not None else "unavailable"}


def project_event(event: dict, auction: dict | None = None) -> dict:
    """Return a bounded JSON-safe read projection, without mutating either input."""
    family = str(event.get("type") or "UNKNOWN")
    pb = _PLAYBOOKS.get(family)
    if pb:
        summary = _pair(pb[0], pb[1]); questions = [_pair(pb[2], pb[3])]; url = pb[4]
    else:
        summary = _pair("Read the official evidence before forming an interpretation.", "形成解读前先阅读官方证据。")
        questions = [_pair("What changed, what is still unknown, and what would challenge the interpretation?", "改变了什么、哪些仍未知、哪些证据会挑战解读？")]
        url = None
    result = {"schema": SCHEMA, "method_version": METHOD_VERSION,
              "event_type": family, "event_date": event.get("date"),
              "title": _pair(str(event.get("label") or family), str(event.get("label_zh") or family)),
              "coverage": "reference_only", "known_at": None,
              "summary": summary, "questions": questions, "facts": [], "source_url": url,
              "limitations": [_pair("Reference reading guide, not a current assessment or forecast. No release results are supplied here.", "这是阅读指南，不是当前评估或预测；此处未提供发布结果。")],
              "can_rank": False, "can_size": False, "can_trade": False}
    if family != "AUCTION":
        return result
    row = auction or {}
    security_type = auction_security_type(row)
    summaries = {
        "TIPS": _pair("Read real yield and inflation-linked terms; do not compare them directly with nominal Treasury yields.", "阅读实际收益率与通胀挂钩条款，不要直接与名义国债收益率比较。"),
        "FRN": _pair("Read the floating-rate terms and discount margin; a fixed-rate yield comparison is not equivalent.", "阅读浮动利率条款与折现利差；固定利率收益率不可直接等同。"),
    }
    result["summary"] = summaries.get(security_type, _pair("Assess the amount offered, maturity and reopening before reading auction demand.", "判断拍卖需求前，先阅读发行规模、到期日及续发行状态。"))
    cusip = row.get("cusip")
    cusip = cusip if isinstance(cusip, str) and re.fullmatch(r"[A-Z0-9]{9}", cusip) else None
    result["facts"] = [
        _fact("cusip", "Security CUSIP", "证券 CUSIP", cusip),
        _fact("offering_amount_usd", "Offering amount · USD", "发行规模 · 美元", _amount(row.get("offeringAmount"))),
        _fact("announcement_date", "Announcement date", "公告日期", _source_date(row.get("announcementDate"))),
        _fact("issue_date", "Issue / settlement date", "发行／结算日期", _source_date(row.get("issueDate"))),
        _fact("maturity_date", "Maturity date", "到期日期", _source_date(row.get("maturityDate"))),
        _fact("competitive_close_et", "Competitive close · ET", "竞争性投标截止 · 美东", auction_close_time(row.get("closingTimeCompetitive"))),
    ]
    result["source_url"] = TREASURY_URL
    result["coverage"] = ("official_terms" if all(f["value"] is not None for f in result["facts"]) else "partial_terms") if auction else "reference_only"
    result["questions"] = [
        _pair("After the official result, compare demand and allocations with genuinely comparable auctions, not all maturities pooled together.", "官方结果发布后，将需求与分配情况和真正可比的拍卖比较，不要混合所有期限。"),
        _pair("A tail or stop-through needs the correct auction measure and a timestamp-matched when-issued quote. Without that quote, leave the comparison unavailable.", "计算尾差或穿透需正确的拍卖指标及同时间戳的发行前报价；缺少报价时应标记不可用。"),
        _pair("Check the broader rate move before attributing a market reaction to this auction alone.", "将市场反应归因于单次拍卖前，先检查整体利率变化。"),
    ]
    result["limitations"] = [
        _pair("Announcement snapshot only. Auction results, when-issued prices and market reactions are not loaded in this view.", "仅公告快照。此视图未加载拍卖结果、发行前报价或市场反应。"),
        _pair("CUSIP identifies the security, not a unique auction. Reopenings can reuse it; date-only fields do not establish when the facts became known.", "CUSIP 标识证券而非唯一拍卖。续发行可复用；仅日期字段不能证明信息何时已知。"),
    ]
    return result

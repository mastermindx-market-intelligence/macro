"""Inspectable, context-only display projection. No collectors, archive writes or score changes."""
from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
import math
import re
from urllib.parse import urlsplit

SCHEMA = "china_altdata.desk.v1"
SOURCES = (
    ("value", "Valuation", "估值", "Cheapness versus the company's own history, ranked across covered names.", "相对自身历史的估值水平，再于有覆盖的公司间排序。"),
    ("margin", "Margin financing", "融资", "Change in financing balances; leverage is not investor identity.", "融资余额变化；杠杆不能识别投资者身份。"),
    ("flow", "Order flow", "资金流", "Reported large-order flow; absent feed stays unavailable.", "披露的大单资金流；缺失数据不视为零。"),
    ("comment", "Attention", "关注度", "Provider attention and participation composite; a proxy, not ownership.", "供应商关注度与参与度组合；为代理指标，不代表持股。"),
    ("lhb", "Trading disclosures", "龙虎榜", "Exchange trading-list rank. Its existing signed weight may reverse the contribution.", "交易所龙虎榜排名；现有负权重可能反转其贡献方向。"),
    ("block", "Block trades", "大宗交易", "Premium/discount rank with the existing signed weight.", "折溢价排名，沿用现有有符号权重。"),
    ("analyst", "Analyst consensus", "分析师", "Sell-side opinion, not a validated return forecast.", "卖方观点，不是经验证的收益预测。"),
)
REGIMES = {
    "dormant": ("Quiet participation", "参与度偏低"),
    "unclear": ("Mixed participation", "参与度信号混合"),
    "institutional_accumulation": ("Steady activity", "活动平稳"),
    "retail_ignition": ("Activity broadening", "活动扩散"),
    "margin_acceleration": ("Leverage expanding", "杠杆扩张"),
    "broad_mania": ("Elevated activity", "活动高涨"),
    "distribution": ("Conflicting flows", "资金流分歧"),
    "forced_deleveraging": ("Deleveraging pressure", "去杠杆压力"),
}
METRICS = (
    ("turnover_z20", "Trading intensity", "成交强度", "z · 20 sessions", "z · 20个交易日",
     "Zero is the 20-session average; negative means quieter trading.", "零为20日均值；负值表示交易更清淡。", 1),
    ("margin_chg_5d", "Financing balance", "融资余额", "% · 5 sessions", "% · 5个交易日",
     "Change in aggregate margin financing over five trading observations.", "融资总余额在五个交易观察期内的变化。", 1),
    ("zt_breadth", "Limit-up breadth", "触及涨停广度", "% · observed names", "% · 观测股票",
     "Names touching limit-up divided by the observed universe, not all listed shares.", "触及涨停数量除以观测股票数量，分母不是全部上市股票。", 1),
    ("qvix_z", "Implied volatility", "隐含波动率", "z · 60 sessions", "z · 60个交易日",
     "QVIX relative to its own 60-session history. Missing is not calm.", "QVIX相对自身60日历史的位置。缺失不等于平静。", 1),
    ("southbound_net", "Southbound flow", "南向资金", "CNY 100m", "亿元人民币",
     "Mainland investors trading Hong Kong securities; not northbound A-share ownership.", "内地投资者交易香港证券的资金流，不是北向A股持仓。", 0.0001),
    ("broker_rs", "Broker-sector strength", "券商板块相对强度", "% · log-return spread", "% · 对数收益差",
     "20-session cumulative log-return difference of the non-bank financial sector versus CSI 300.", "非银金融板块相对沪深300的20日累计对数收益差。", 100),
)


def number(value):
    if isinstance(value, bool):
        return None
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError, OverflowError):
        return None


def session_date(value):
    if value is None:
        return None
    raw = str(value)[:10]
    try:
        return date.fromisoformat(raw).isoformat() if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw) else None
    except ValueError:
        return None


def instrument_href(ticker):
    return "china_lookup.html#" + ticker if re.fullmatch(r"\d{6}\.(SS|SZ|BJ)", ticker or "") else None


def _health(part, today):
    obs = session_date(part.get("date"))
    latest = session_date(part.get("latest_date")) or obs
    # Old producers expose the latest partial session in their named gap.
    gaps = part.get("data_gaps")
    for gap in gaps if isinstance(gaps, list) else []:
        match = re.search(r"behind tape tail (\d{4}-\d{2}-\d{2})", str(gap))
        if match:
            latest = session_date(match.group(1)) or latest
    available = sum(number(part.get(m[0])) is not None for m in METRICS) if obs and obs <= today else 0
    core = all(number(part.get(k)) is not None for k in ("turnover_z20", "margin_chg_5d"))
    future = bool(obs and obs > today)
    lag = max(0, (date.fromisoformat(latest) - date.fromisoformat(obs)).days) if latest and obs else None
    age = (date.fromisoformat(today) - date.fromisoformat(obs)).days if obs else None
    archival = part.get("projection_kind") != "current_source_recomputation"
    if not obs or available == 0:
        state = "unavailable"
    elif future or not core or available < len(METRICS) or (lag or 0) > 0:
        state = "partial"
    else:
        state = "current"
    if obs and not future and (archival or (age is not None and age > 7)):
        state = "delayed"
    return dict(state=state, observation_date=obs, latest_date=latest,
                lag_calendar_days=lag, age_calendar_days=age, available=available,
                expected=len(METRICS), core_available=core and not future,
                summary_en=f"{available} of {len(METRICS)} readings available for the dated observation.",
                summary_zh=f"该日期的{len(METRICS)}项读数中有{available}项可用。")


def _company_rows(rows, weights, today, flag_labels):
    out = []
    for raw in rows:
        ticker = str(raw.get("ticker") or "")
        conv = number(raw.get("convergence"))
        side = "insufficient" if conv is None else "constructive" if conv > .05 else "cautionary" if conv < -.05 else "mixed"
        sources = []
        for key, *_ in SOURCES:
            value = number(raw.get(key))
            weight = number(weights.get(key))
            contribution = value * weight if value is not None and weight is not None else None
            asof = session_date((raw.get("source_asof") or {}).get(key))
            state = "unavailable" if value is None else "undated" if not asof else "future" if asof > today else "observed"
            direction = ("unavailable" if contribution is None or state == "future" else "neutral" if abs(value) <= .05 or weight == 0
                         else "constructive" if contribution > 0 else "cautionary")
            sources.append(dict(key=key, value=value, contribution=None if contribution is None else round(contribution, 6),
                                direction=direction, asof=asof, state=state,
                                date_kind=(raw.get("source_date_kind") or {}).get(key, "unknown")))
        if any(s["state"] == "future" for s in sources):
            side, conv = "insufficient", None
        available = sum(s["value"] is not None and s["state"] != "future" for s in sources)
        positive = sum(s["direction"] == "constructive" for s in sources)
        negative = sum(s["direction"] == "cautionary" for s in sources)
        agreeing = positive if side == "constructive" else negative if side == "cautionary" else None
        conflicting = negative if side == "constructive" else positive if side == "cautionary" else None
        dated = [s["asof"] for s in sources if s["value"] is not None and s["asof"] and s["asof"] <= today]
        flags = []
        for key in raw.get("flags") or []:
            labels = flag_labels.get(key) or (str(key).replace("_", " "), str(key).replace("_", " "))
            flags.append(dict(key=str(key), label_en=labels[0], label_zh=labels[-1]))
        out.append(dict(ticker=ticker, name=str(raw.get("name") or ticker),
                        name_zh=str(raw.get("name_zh") or raw.get("name") or ticker),
                        side=side, alignment=conv, available=available, agreeing=agreeing, conflicting=conflicting,
                        constructive=positive, cautionary=negative,
                        neutral=sum(s["direction"] == "neutral" for s in sources),
                        asof=min(dated) if dated else None, dated_sources=len(dated),
                        flags=flags, sources=sources, href=instrument_href(ticker)))
    return out


def filing_href(value):
    """Only supplied official exchange/disclosure links; never infer a filing URL."""
    if not isinstance(value, str) or len(value) > 2048 or any(ord(c) < 32 for c in value):
        return None
    try:
        if value.lstrip("/").startswith("finalpage/"):
            from lib.china_filing_urls import cninfo_source_url
            value = cninfo_source_url(value)
            if not value:
                return None
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower()
        official = any(host == domain or host.endswith("." + domain)
                       for domain in ("sse.com.cn", "szse.cn", "bse.cn", "cninfo.com.cn"))
        return value if parsed.scheme == "https" and official and not parsed.username and not parsed.password and parsed.port in (None,443) else None
    except ValueError:
        return None


def event_rows(special, today):
    """Chronological disclosed events, preserving unknown timing and metric scope."""
    events = {}
    specs = (("unlocks", "events", "unlock", "Share unlock", "限售解禁"),
             ("inquiry", "letters", "inquiry", "Exchange inquiry", "交易所问询"),
             ("buyback", "top", "buyback", "Buyback update", "回购进展"),
             ("preannounce", "top_movers", "earnings", "Earnings outlook", "业绩预告"),
             ("pledge", "top", "pledge", "Pledge disclosure", "质押披露"),
             ("st", "top_current", "st", "Special treatment", "特别处理"))
    for block_key, rows_key, kind, label_en, label_zh in specs:
        block = special.get(block_key) or {}
        for raw in block.get(rows_key) or []:
            if not isinstance(raw, dict):
                raw = {"ticker": str(raw)}
            ticker = str(raw.get("ticker") or raw.get("secCode") or "")
            name = str(raw.get("name") or raw.get("name_zh") or raw.get("secName") or ticker)
            dt = session_date(raw.get("unlock_date") if kind == "unlock" else raw.get("date") or raw.get("announce_date"))
            observed = session_date(block.get("asof"))
            en, zh = [], []
            if kind == "unlock":
                value = number(raw.get("float_pct") if raw.get("float_pct") is not None else raw.get("pct_float"))
                if value is not None:
                    en.append(f"{value/100:.1f}× existing free float" if value >= 100 else f"{value:.1f}% of free float")
                    zh.append(f"现有流通量的{value/100:.1f}倍" if value >= 100 else f"占流通量{value:.1f}%")
                en.append("Eligibility to sell; actual selling is unknown.")
                zh.append("股份可流通；实际卖出情况未知。")
            elif kind == "buyback":
                for key, a, z in (("plan_amt_yi", "Planned", "计划"), ("done_amt_yi", "Executed", "已执行")):
                    value = number(raw.get(key))
                    if value is not None:
                        en.append(f"{a}: CNY {value:.2f} × 100m")
                        zh.append(f"{z}：{value:.2f}亿元")
                en.append("Plan and execution are separate; no price floor is implied.")
                zh.append("计划与执行分别列示，不代表股价底部。")
            elif kind == "earnings":
                period = str(raw.get("quarter") or raw.get("report_period") or "")
                typ = str(raw.get("type") or "")
                types = {"预增":"profit up", "略增":"profit slightly up", "续盈":"still profitable",
                         "扭亏":"back to profit", "预减":"profit down", "略减":"profit slightly down",
                         "减亏":"smaller loss", "增亏":"larger loss", "首亏":"first loss",
                         "续亏":"still loss-making", "不确定":"uncertain"}
                en.append(types.get(typ, typ) or "Type not supplied")
                zh.append(typ or "未提供类型")
                en.append("Period: " + (period or "not supplied"))
                zh.append("报告期：" + (period or "未提供"))
                en.append("Metric and comparison base must be checked in the filing.")
                zh.append("请在公告中核对指标及比较基数。")
            elif kind == "inquiry":
                en.append("Regulatory questions are not a finding of wrongdoing.")
                zh.append("监管问询不等于违规结论。")
            elif kind == "pledge":
                value = number(raw.get("pledge_ratio"))
                if value is not None:
                    en.append(f"Disclosed pledge ratio: {value:.1f}%")
                    zh.append(f"披露质押比例：{value:.1f}%")
                en.append("Review the filing's denominator and reporting period.")
                zh.append("请核对公告中的分母与报告期。")
            else:
                en.append("Review the current exchange notice.")
                zh.append("请核对交易所最新公告。")
            detail_en, detail_zh = " · ".join(en), " · ".join(zh)
            identity = json.dumps({"source":block_key, "record":raw}, sort_keys=True,
                                  ensure_ascii=False, separators=(",", ":"), default=str)
            event_id = hashlib.sha256(identity.encode()).hexdigest()[:16]
            horizon = "undated" if not dt else "upcoming" if dt >= today else "recent" if (date.fromisoformat(today)-date.fromisoformat(dt)).days <= 30 else "archive"
            events[event_id] = dict(id=event_id, ticker=ticker, name=name, type=kind, date=dt,
                                    observed_at=observed, horizon=horizon, label_en=label_en, label_zh=label_zh,
                                    detail_en=detail_en, detail_zh=detail_zh, href=instrument_href(ticker),
                                    reported_change=number(raw.get("pct_change", raw.get("p_change"))),
                                    reported_metric=str(raw.get("metric") or raw.get("indicator") or "") or None,
                                    reported_period=str(raw.get("quarter") or raw.get("report_period") or "") or None,
                                    disclosure_title=str(raw.get("title") or "") or None,
                                    filing_href=filing_href(raw.get("pdf_url") or raw.get("filing_url")),
                                    stage=str(raw.get("progress") or raw.get("reply_state") or "") or None)
    order = {"upcoming":0, "recent":1, "undated":2, "archive":3}
    return sorted(events.values(), key=lambda e:(order[e["horizon"]], e["date"] or "9999", e["ticker"], e["id"]))


def build_desk(rows=None, weights=None, participation=None, special=None, flag_labels=None, generated_at=None):
    now = generated_at or datetime.now(timezone.utc).isoformat()
    today = session_date(now) or date.today().isoformat()
    part, weights = participation or {}, weights or {}
    health = _health(part, today)
    obs = health["observation_date"]
    previous = part.get("previous_observation") or {}
    previous_date = session_date(previous.get("date"))
    if not obs or not previous_date or previous_date >= obs or obs > today:
        previous_date = None
    change_units = {"turnover_z20":("z","z"), "margin_chg_5d":("pp","个百分点"),
                    "zt_breadth":("pp","个百分点"), "qvix_z":("z","z"),
                    "southbound_net":("CNY 100m","亿元"), "broker_rs":("pp","个百分点")}
    metrics = []
    for key, en, zh, unit_en, unit_zh, explanation_en, explanation_zh, factor in METRICS:
        value = number(part.get(key))
        valid = value is not None and obs is not None and obs <= today
        prior_value = number(previous.get(key)) if previous_date else None
        change = round((value-prior_value)*factor, 3) if valid and prior_value is not None else None
        metrics.append(dict(key=key, label_en=en, label_zh=zh, value=round(value*factor, 3) if valid else None,
                            unit_en=unit_en, unit_zh=unit_zh, asof=obs if valid else None,
                            state="observed" if valid else "unavailable",
                            change=change, comparison_date=previous_date if change is not None else None,
                            change_unit_en=change_units[key][0], change_unit_zh=change_units[key][1],
                            explanation_en=explanation_en, explanation_zh=explanation_zh))
    regime = REGIMES.get(part.get("regime"), REGIMES["unclear"]) if health["core_available"] else ("Unavailable", "不可用")
    if not health["core_available"]:
        headline = ("Market read incomplete", "市场读数不完整")
    elif health["state"] in ("partial", "delayed"):
        headline = ("Read the dated evidence", "请查看注明日期的证据")
    else:
        headline = regime
    companies = _company_rows(rows or [], weights, today, flag_labels or {})
    catalog = []
    for key, en, zh, de, dz in SOURCES:
        readings = [next(s for s in row["sources"] if s["key"] == key) for row in companies]
        valid = [s for s in readings if s["value"] is not None and s["state"] != "future"]
        dates = [s["asof"] for s in valid if s["asof"] and s["asof"] <= today]
        catalog.append(dict(key=key, label_en=en, label_zh=zh, description_en=de, description_zh=dz,
                            asof=max(dates) if dates else None, oldest_asof=min(dates) if dates else None,
                            date_kind=next(iter({s["date_kind"] for s in valid})) if len({s["date_kind"] for s in valid}) == 1 else "mixed",
                            state="unavailable" if not valid else "observed" if len(dates)==len(valid) else "undated",
                            available=len(valid), dated=len(dates), unit_en="centered rank", unit_zh="中心化排名",
                            weight=number(weights.get(key))))
    events = event_rows(special or {}, today)
    counts = {side:sum(r["side"]==side for r in companies) for side in ("constructive", "cautionary", "mixed", "insufficient")}
    upcoming = sum(e["horizon"]=="upcoming" for e in events)
    detail_en = "Trading intensity and financing describe participation; they do not identify who owns the market."
    detail_zh = "成交强度与融资描述市场参与度，不能识别市场持有者。"
    changes = {m["key"]:m["change"] for m in metrics}
    if changes["turnover_z20"] is not None and changes["margin_chg_5d"] is not None:
        changed_en = (f'Vs {previous_date}: trading intensity {changes["turnover_z20"]:+.2f}z; '
                      f'five-session financing change {changes["margin_chg_5d"]:+.2f} percentage points. Current-source comparison.')
        changed_zh = (f'较{previous_date}：成交强度{changes["turnover_z20"]:+.2f}z；'
                      f'五日融资变化{changes["margin_chg_5d"]:+.2f}个百分点。按当前来源比较。')
    else:
        changed_en = "A comparable prior participation observation is unavailable. Read the dated levels; do not infer a daily change."
        changed_zh = "无可比的上一期参与度观察。请查看注明日期的水平，不推断单日变化。"
    briefing = [
        dict(title_en="Changes since the prior observation", title_zh="较上一期观察的变化",
             detail_en=changed_en, detail_zh=changed_zh, href="#participation"),
        dict(title_en="Compare support and conflict", title_zh="比较支持与冲突",
             detail_en=f'{counts["constructive"]:,} constructive · {counts["cautionary"]:,} cautionary · {counts["mixed"]:,} mixed in the eligible universe.',
             detail_zh=f'合资格范围内：{counts["constructive"]:,}只偏积极 · {counts["cautionary"]:,}只偏谨慎 · {counts["mixed"]:,}只混合。',
             href="#companies"),
        dict(title_en="Check the next disclosure", title_zh="核对后续披露",
             detail_en=f"{upcoming} dated upcoming events in the available feed. Coverage is not a complete market calendar.",
             detail_zh=f"现有数据中有{upcoming}项已注明日期的未来事件；覆盖并非全市场日历。", href="#catalysts")]
    return dict(schema=SCHEMA, generated_at=now, observation_date=obs, data_health=health,
                participation=dict(headline_en=headline[0], headline_zh=headline[1],
                    regime_en=regime[0], regime_zh=regime[1], detail_en=detail_en, detail_zh=detail_zh,
                    metrics=metrics, trend=part.get("trend") or [],
                    projection_kind=part.get("projection_kind") or "first_observed_archive",
                    computed_at=part.get("computed_at"),
                    history_qualification=part.get("history_qualification") or "archival_fallback; current_source_recomputation_unavailable",
                    observed_universe=number(part.get("zt_universe_n"))),
                briefing=briefing, sources=catalog,
                universe=dict(total=len(companies), available=sum(r["available"]>=2 for r in companies),
                    counts=counts, scope_en="Eligible companies with at least two available inputs; not all A-shares.",
                    scope_zh="至少有两项输入的合资格公司，并非全部A股。"),
                rows=companies, events=events,
                event_health=((special or {}).get("hero") or {}).get("freshness") or {})

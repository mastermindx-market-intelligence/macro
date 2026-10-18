"""Country-first International interpretation from existing, dated source facts.

Presentation only: no new trading score, signal, probability, ledger or publisher.
Forecasts retain their original provider, vintage and calendar/fiscal basis.
Market trends never stand in for economic growth or consumer-price evidence.
"""
from __future__ import annotations

from calendar import monthrange
from datetime import date
from math import isfinite
from urllib.parse import urlparse

SCHEMA = "intl_country_assessment.v1"
ORDER = ("JP", "KR", "TW", "IN", "AU", "GB", "EZ")
NAMES = {
    "JP": ("Japan", "日本", "Nikkei 225", "JPY"),
    "KR": ("South Korea", "韩国", "KOSPI", "KRW"),
    "TW": ("Taiwan", "台湾", "TAIEX", "TWD"),
    "IN": ("India", "印度", "Nifty 50", "INR"),
    "AU": ("Australia", "澳大利亚", "ASX 200", "AUD"),
    "GB": ("United Kingdom", "英国", "FTSE 100", "GBP"),
    "EZ": ("Euro Area", "欧元区", "STOXX Europe 600", "EUR"),
}
PROFILES = {
    "JP": {
        "theme": ("Wages, prices, yen", "工资、物价与日元"),
        "driver": ("Wage growth and domestic inflation determine how much room policy has to normalize.",
                   "工资增长与国内通胀决定货币政策正常化的空间。"),
        "transmission": ("A stronger yen improves unhedged dollar translation but can reduce overseas earnings in yen.",
                         "日元升值改善未对冲的美元换算收益，但可能压低海外利润的日元计价。"),
        "upside": ("If real wages improve and inflation settles, household demand could support a broader recovery.",
                   "若实际工资改善且通胀趋稳，家庭需求有望支持更广泛的复苏。"),
        "downside": ("If import costs rise faster than wages, consumption and profit margins could remain squeezed.",
                     "若进口成本涨幅超过工资，消费与利润率可能持续承压。"),
        "watch": ("Wages, household spending and the Bank of Japan outlook.", "工资、家庭支出与日本央行展望。"),
        "route": "japan.html",
        "source": "https://www.boj.or.jp/en/mopo/outlook/",
    },
    "KR": {
        "theme": ("Exports versus demand", "出口与内需"),
        "driver": ("The export cycle and household demand can move in different directions.",
                   "出口周期与家庭需求可能呈现不同方向。"),
        "transmission": ("Export earnings, the won and domestic financing conditions connect the economy to equities.",
                         "出口利润、韩元与国内融资条件将经济变化传导至股市。"),
        "upside": ("If export strength reaches earnings and domestic demand, a price recovery would gain firmer support.",
                   "若出口强势传导至利润与内需，股价复苏将获得更坚实的支撑。"),
        "downside": ("If export demand weakens while stocks remain below trend, the growth outlook could face a tougher test.",
                     "若出口需求走弱且股价持续低于趋势，增长前景将面临更严峻的考验。"),
        "watch": ("Exports, domestic demand and equity trend recovery.", "出口、内需与股市趋势修复。"),
        "route": "south_korea.html",
        "source": "https://www.bok.or.kr/eng/main/main.do",
    },
    "TW": {
        "theme": ("Technology investment", "科技投资"),
        "driver": ("Technology exports and capacity investment are central to the published growth outlook.",
                   "科技出口与产能投资是已发布增长展望的核心。"),
        "transmission": ("Strong technology demand can support export income while energy and currency costs affect margins.",
                         "强劲科技需求支持出口收入，能源与汇率成本则影响利润率。"),
        "upside": ("If technology investment broadens and export demand persists, growth could retain support beyond the leading firms.",
                   "若科技投资扩散且出口需求持续，增长支撑可能延伸至龙头企业之外。"),
        "downside": ("If technology spending slows or energy costs rise, concentrated export exposure could amplify the impact.",
                     "若科技支出放缓或能源成本上升，集中的出口敞口可能放大影响。"),
        "watch": ("Export orders, capital spending and the next GDP release.", "出口订单、资本支出与下一次GDP发布。"),
        "route": None,
        "source": "https://eng.dgbas.gov.tw/News_Content.aspx?n=4438&s=236587",
    },
    "IN": {
        "theme": ("Domestic demand, oil", "内需与石油"),
        "driver": ("Domestic demand supports the growth outlook; imported energy can change the inflation trade-off.",
                   "内需支持增长前景，进口能源则可能改变通胀的权衡。"),
        "transmission": ("Oil costs and the rupee affect import prices, while financing conditions influence domestic investment.",
                         "油价与卢比影响进口价格，融资条件则影响国内投资。"),
        "upside": ("If inflation eases without a demand slowdown, domestic investment could gain breathing room.",
                   "若通胀回落而需求未放缓，国内投资将获得更多空间。"),
        "downside": ("If oil and import costs rise, inflation pressure could constrain support for growth.",
                     "若油价与进口成本上升，通胀压力可能限制对增长的支持。"),
        "watch": ("Inflation, investment activity and the rupee.", "通胀、投资活动与卢比。"),
        "route": "india.html",
        "source": "https://www.rbi.org.in/",
    },
    "AU": {
        "theme": ("Households, commodities", "家庭与大宗商品"),
        "driver": ("Household borrowing costs and commodity demand are distinct channels into activity.",
                   "家庭借贷成本与大宗商品需求通过不同渠道影响经济活动。"),
        "transmission": ("Commodity income supports the external sector; interest rates shape household spending capacity.",
                         "大宗商品收入支持对外部门，利率影响家庭支出能力。"),
        "upside": ("If inflation recedes and household spending improves, domestic growth could become more resilient.",
                   "若通胀回落且家庭支出改善，国内增长可能更具韧性。"),
        "downside": ("If commodity demand softens while borrowing costs stay high, external and domestic growth could weaken together.",
                     "若大宗商品需求转弱且借贷成本维持高位，外部与国内增长可能同时走弱。"),
        "watch": ("Household spending, inflation and commodity demand.", "家庭支出、通胀与大宗商品需求。"),
        "route": None,
        "source": "https://www.rba.gov.au/publications/smp/",
    },
    "GB": {
        "theme": ("Services, rates, sterling", "服务业、利率与英镑"),
        "driver": ("Services inflation and wage growth matter for the pace of monetary easing.",
                   "服务业通胀与工资增长影响货币宽松的节奏。"),
        "transmission": ("Lower financing costs can support domestic demand; sterling also changes overseas earnings translation.",
                         "融资成本下降可支持内需，英镑也会改变海外利润的换算。"),
        "upside": ("If services inflation cools while spending holds, a gradual recovery could gain support.",
                   "若服务业通胀降温且支出保持稳定，渐进复苏可能获得支持。"),
        "downside": ("If inflation stays persistent, prolonged borrowing costs could restrain an already modest growth path.",
                     "若通胀持续，高企的借贷成本可能抑制本已温和的增长路径。"),
        "watch": ("Services prices, wages and household spending.", "服务价格、工资与家庭支出。"),
        "route": "united_kingdom.html",
        "source": "https://www.bankofengland.co.uk/monetary-policy-report",
    },
    "EZ": {
        "theme": ("Energy, credit, demand", "能源、信贷与需求"),
        "driver": ("Energy prices and credit conditions determine how much support weak demand receives.",
                   "能源价格与信贷条件决定疲弱需求能获得多大支持。"),
        "transmission": ("Import costs affect real incomes; bank lending conditions transmit policy into investment and consumption.",
                         "进口成本影响实际收入，银行信贷条件将政策传导至投资与消费。"),
        "upside": ("If energy pressure eases and lending improves, demand could recover without renewed inflation pressure.",
                   "若能源压力缓解且信贷改善，需求可能在不重新推高通胀的情况下复苏。"),
        "downside": ("If energy costs rise while credit remains tight, growth and inflation could move in an unfavorable combination.",
                     "若能源成本上升且信贷持续紧张，增长与通胀可能形成不利组合。"),
        "watch": ("Inflation, bank lending and the ECB outlook.", "通胀、银行信贷与欧洲央行展望。"),
        "route": "euro_area.html",
        "source": "https://www.ecb.europa.eu/pub/projections/html/index.en.html",
    },
}
STATES = {
    "uptrend": ("Uptrend", "上升趋势", "up"),
    "pullback": ("Pullback", "回调", "neutral"),
    "pressure": ("Under pressure", "承压", "down"),
    "rebound": ("Rebound", "反弹", "neutral"),
    "unknown": ("Trend incomplete", "趋势资料不足", "neutral"),
}


def _number(value):
    if type(value) not in (int, float):
        return None
    try:
        return float(value) if isfinite(value) else None
    except (OverflowError, ValueError):
        return None


def _day(value):
    if type(value) is not str:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _period_end(value):
    if type(value) is not str:
        return None
    if len(value) == 7:
        try:
            y, m = (int(x) for x in value.split("-"))
            return date(y, m, monthrange(y, m)[1])
        except (ValueError, TypeError):
            return None
    return _day(value)


def _fresh(period, today, max_age):
    d = _period_end(period)
    return d is not None and 0 <= (today - d).days <= max_age


def _https(value):
    if type(value) is not str:
        return None
    try:
        parsed = urlparse(value)
        return value if parsed.scheme == "https" and parsed.hostname and not parsed.username else None
    except ValueError:
        return None


def _mapping(value):
    return value if type(value) is dict else {}


def _metric(key, record, official, today):
    fields = {
        "inflation": ("cpi_yoy", "cpi_yoy", "Inflation", "通胀", "% y/y", 105),
        "gdp": ("gdp_yoy", "gdp", "GDP growth", "GDP增长", "% y/y", 220),
        "unemployment": ("unemployment", "unemployment", "Unemployment", "失业率", "%", 130),
        "policy": ("policy_rate", "policy_rate", "Policy rate", "政策利率", "%", 45),
    }
    raw_key, date_key, en, zh, unit, limit = fields[key]
    receipt = official.get(key) if type(official) is dict else None
    if type(receipt) is dict:
        value = _number(receipt.get("value"))
        period = receipt.get("period")
        source = receipt.get("provider")
        source_url = _https(receipt.get("source_url"))
        # New official receipts must identify the metric/unit and public observation.
        admitted = (receipt.get("metric") == key and receipt.get("unit") == unit
                    and receipt.get("status") in ("observed", "provisional")
                    and bool(source) and bool(source_url))
        if not admitted:
            value = None
    elif key == "policy":
        # The legacy field can be a 3-month market rate, not a central-bank rate.
        value = period = source = source_url = None
    else:
        value = _number(_mapping(record.get("macro")).get(raw_key))
        period = _mapping(record.get("macro_asof")).get(date_key)
        source = "Existing international macro series"
        source_url = None
    current = value is not None and _fresh(period, today, limit)
    return {
        "key": key, "label_en": en, "label_zh": zh, "value": value,
        "period": period, "unit": unit, "current": current,
        "quality": "current" if current else "dated" if value is not None else "missing",
        "source": source, "source_url": source_url,
        "change_3m_pp": _number(receipt.get("change_3m_pp")) if type(receipt) is dict and current else None,
    }


def _forecast(raw, cc, today):
    if type(raw) is not dict or raw.get("cc") != cc:
        return None
    vintage = _day(raw.get("published"))
    if (vintage is None or not 0 <= (today - vintage).days <= 270
            or raw.get("kind") != "sourced_forecast" or raw.get("unit") != "percent"
            or raw.get("period_basis") not in ("calendar_year", "fiscal_year")
            or not _https(raw.get("source_url")) or not raw.get("provider")):
        return None
    values = raw.get("values")
    if type(values) is not dict:
        return None
    current = _number(values.get(str(today.year)))
    following = _number(values.get(str(today.year + 1)))
    if current is None or following is None or not -100 < current < 100 or not -100 < following < 100:
        return None
    previous = _number(values.get(str(today.year - 1)))
    return {
        "kind": "sourced_forecast", "provider": raw["provider"],
        "source_url": raw["source_url"], "published": raw["published"],
        "period_basis": raw["period_basis"], "year": today.year,
        "next_year": today.year + 1, "current": current, "next": following,
        "previous": previous, "change": round(following - current, 3),
        "revision": _number(raw.get("revision_current_pp")),
        "revision_from": raw.get("revision_from") if _period_end(raw.get("revision_from")) else None,
    }


def _market(record, today):
    equity = _mapping(record.get("equity"))
    # A publication date is not an observation clock. Old envelopes without an
    # instrument clock intentionally do not become current on a fresh page build.
    observed = equity.get("as_of")
    current = _fresh(observed, today, 14)
    fast = equity.get("above_50d") if current else None
    slow = equity.get("above_200d") if current and equity.get("trend_200d_complete") is True else None
    if type(fast) is bool and type(slow) is bool:
        state = {(True, True): "uptrend", (False, True): "pullback",
                 (False, False): "pressure", (True, False): "rebound"}[(fast, slow)]
    else:
        state = "unknown"
    dd = _number(equity.get("off_52w_high"))
    dd = dd if current and dd is not None and -100 <= dd <= 0 else None
    fx_date = _mapping(record.get("macro_asof")).get("fx_strength_3m")
    fx_current = _fresh(fx_date, today, 14)
    fx = _number(_mapping(record.get("macro")).get("fx_strength_3m")) if fx_current else None
    en, zh, tone = STATES[state]
    window = equity.get("high_window_observations")
    window = window if type(window) is int and 60 <= window <= 252 else None
    return {"state": state, "label_en": en, "label_zh": zh, "tone": tone,
            "as_of": observed, "current": current, "above_50d": fast,
            "above_200d": slow, "drawdown": dd, "fx_3m": fx, "fx_as_of": fx_date,
            "high_window_observations": window,
            "high_window_start": equity.get("high_window_start")}


def _path_label(forecast):
    if forecast["next"] < 0:
        return ("Contraction projected", "预计经济收缩")
    if forecast["current"] < 0 < forecast["next"]:
        return ("A return to expansion is projected", "预计恢复扩张")
    if forecast["next"] == 0:
        return ("No growth projected", "预计零增长")
    if forecast["change"] > 0.05:
        return ("Faster growth projected", "预计增长加快")
    if forecast["change"] < -0.05:
        return ("Slower growth projected", "预计增长放缓")
    return ("Broadly steady growth projected", "预计增长大致平稳")


def _headlines(cc, forecast, metrics):
    """Make a specific reading from admitted facts, never infer a price cause."""
    by_key = {m["key"]: m for m in metrics}
    inflation, policy = by_key["inflation"], by_key["policy"]
    rate_change = policy["change_3m_pp"]
    higher_rates = rate_change is not None and rate_change > 0.05
    steady_rates = rate_change is not None and abs(rate_change) <= 0.05
    rising_inflation = inflation["change_3m_pp"] is not None and inflation["change_3m_pp"] > 0.25
    if not forecast:
        if higher_rates:
            title = ("Higher policy rates shape the next phase", "政策利率上升影响下一阶段")
        elif inflation["current"]:
            title = ("Inflation and activity set the policy trade-off", "通胀与经济活动决定政策权衡")
        else:
            title = ("The economic outlook needs fresh evidence", "经济前景有待新数据")
        return (*title, "Follow the dated observations and the conditions affecting demand.",
                "结合带日期的观测，研判影响需求的条件。")
    if forecast["next"] < 0:
        title = ("A contraction is projected", "预计经济收缩")
    elif forecast["current"] > 8 and forecast["change"] < -1:
        title = ("Exceptional growth is forecast to cool", "高速增长预计降温")
    elif forecast["revision"] is not None and forecast["revision"] >= 0.3 and higher_rates:
        title = ("A growth upgrade alongside higher rates", "增长预测上调，政策利率上升")
    elif higher_rates and forecast["change"] < -0.05:
        title = ("Higher rates, a slower growth path", "政策利率上升，增长路径放缓")
    elif higher_rates and forecast["current"] <= 1:
        title = ("Modest growth alongside rising rates", "增长温和，政策利率上升")
    elif rising_inflation and forecast["change"] > 0.05:
        title = ("Faster growth projected as inflation rises", "增长预计加快，通胀同时上升")
    elif steady_rates and forecast["change"] > 0.05:
        title = ("A gradual pickup, with policy rates steady", "预计逐步加快，政策利率稳定")
    else:
        title = _path_label(forecast)
    fy = "FY" if forecast["period_basis"] == "fiscal_year" else ""
    year, following = f'{fy}{forecast["year"]}', f'{fy}{forecast["next_year"]}'
    provider, first, second = forecast["provider"], forecast["current"], forecast["next"]
    revision = forecast["revision"]
    if revision is not None and forecast["revision_from"] and abs(revision) >= 0.05:
        verb, verb_zh = ("raised", "上调") if revision > 0 else ("lowered", "下调")
        read_en = (f'{provider} {verb} its {year} growth forecast by {abs(revision):.1f} percentage points '
                   f'from its {forecast["revision_from"]} edition, to {first:.1f}%; '
                   f'it projects {second:.1f}% for {following}.')
        read_zh = (f'{provider}将{year}年增长预测较{forecast["revision_from"]}版'
                   f'{verb_zh}{abs(revision):.1f}个百分点至{first:.1f}%，预计{following}年为{second:.1f}%。')
    else:
        read_en = f'{provider} projects real GDP growth of {first:.2f}% in {year} and {second:.2f}% in {following}.'
        read_zh = f'{provider}预计{year}年实际GDP增长{first:.2f}%，{following}年为{second:.2f}%。'
    if policy["current"] and rate_change is not None:
        if abs(rate_change) > 0.05:
            direction, direction_zh = ("above", "高于") if rate_change > 0 else ("below", "低于")
            read_en += (f' The {policy["period"]} policy rate was {policy["value"]:.2f}%, '
                        f'{abs(rate_change):.2f} points {direction} three months earlier.')
            read_zh += (f'{policy["period"]}政策利率为{policy["value"]:.2f}%，'
                        f'{direction_zh}三个月前{abs(rate_change):.2f}个百分点。')
        else:
            read_en += f' The {policy["period"]} policy rate was {policy["value"]:.2f}%, unchanged over three months.'
            read_zh += f'{policy["period"]}政策利率为{policy["value"]:.2f}%，较三个月前不变。'
    elif inflation["current"]:
        read_en += f' Inflation was {inflation["value"]:.2f}% year over year in {inflation["period"]}.'
        read_zh += f'{inflation["period"]}通胀同比为{inflation["value"]:.2f}%。'
    return (*title, read_en, read_zh)


def _world_brief(countries):
    eligible = [c for c in countries if c["forecast"]
                and c["forecast"]["period_basis"] == "calendar_year"]
    if not eligible:
        return None
    featured = min(eligible, key=lambda c: c["forecast"]["change"])
    f = featured["forecast"]
    if f["change"] < -1 and f["next"] > 0:
        title = (f'{featured["name_en"]}’s growth is forecast to cool sharply in {f["next_year"]}.', f'{featured["name_zh"]}{f["next_year"]}年增长预计将明显放缓。')
        read = (f'{f["provider"]} projects {f["current"]:.2f}% growth in {f["year"]}, '
                f'moderating to {f["next"]:.2f}% in {f["next_year"]}.',
                f'{f["provider"]}预计{f["year"]}年增长{f["current"]:.2f}%，'
                f'{f["next_year"]}年放缓至{f["next"]:.2f}%。')
    else:
        title = ("The published growth paths", "已发布的增长路径")
        read = (f'{featured["name_en"]}: {f["current"]:.1f}% in {f["year"]}, '
                f'{f["next"]:.1f}% in {f["next_year"]}, according to {f["provider"]}.',
                f'{f["provider"]}预计{featured["name_zh"]}{f["year"]}年增长{f["current"]:.1f}%，'
                f'{f["next_year"]}年增长{f["next"]:.1f}%。')
    return {"title_en": title[0], "title_zh": title[1], "read_en": read[0], "read_zh": read[1],
            "source_url": f["source_url"], "source": f["provider"], "published": f["published"],
            "cc": featured["cc"], "year": f["year"], "next_year": f["next_year"]}


def build_country_assessments(latest, *, today=None, official=None, forecasts=None, commentary=None):
    """Build a deterministic, non-mutating view from a single publication input."""
    today = today or date.today()
    if type(today) is not date or type(latest) is not dict:
        raise ValueError("invalid_country_assessment_input")
    records = latest.get("records")
    if type(records) is not list:
        raise ValueError("invalid_country_records")
    by_cc = {}
    for record in records:
        if type(record) is not dict or record.get("cc") not in ORDER:
            continue
        cc = record["cc"]
        if cc in by_cc:
            raise ValueError("duplicate_country_record")
        by_cc[cc] = record
    official = official if type(official) is dict else {}
    forecasts = forecasts if type(forecasts) is dict else {}
    commentary = _mapping(commentary)
    countries = []
    for cc in ORDER:
        if cc not in by_cc:
            continue
        record = by_cc[cc]
        market = _market(record, today)
        forecast = _forecast(forecasts.get(cc), cc, today)
        metrics = [_metric(key, record, official.get(cc, {}), today)
                   for key in ("gdp", "inflation", "policy", "unemployment")]
        title_en, title_zh, read_en, read_zh = _headlines(cc, forecast, metrics)
        if forecast:
            forecast["path_en"], forecast["path_zh"] = _path_label(forecast)
        name_en, name_zh, index, currency = NAMES[cc]
        profile = dict(PROFILES[cc])
        research = _mapping(commentary.get(cc))
        published = _day(research.get("published"))
        research_ok = (research.get("kind") == "attributed_assessment"
                       and published is not None and 0 <= (today - published).days <= 120
                       and bool(_https(research.get("source_url"))) and bool(research.get("provider")))
        if research_ok:
            for key in ("theme", "driver", "upside", "downside", "watch", "title", "read"):
                pair = research.get(key)
                if not (type(pair) is list and len(pair) == 2 and all(type(x) is str and x for x in pair)):
                    research_ok = False
            if research_ok:
                for key in ("theme", "driver", "upside", "downside", "watch"):
                    profile[key] = research[key][:]
                title_en, title_zh = research["title"]
        research = research if research_ok else None
        countries.append({
            "cc": cc, "name_en": name_en, "name_zh": name_zh,
            "index": index, "currency": currency, "market": market,
            "forecast": forecast, "metrics": metrics,
            "title_en": title_en, "title_zh": title_zh,
            "read_en": read_en, "read_zh": read_zh,
            "profile": profile,
            "research": research,
            "scope_note_en": "Equities use STOXX Europe 600, which includes markets outside the Euro Area." if cc == "EZ" else None,
            "scope_note_zh": "股票采用STOXX欧洲600指数，覆盖范围包含欧元区以外市场。" if cc == "EZ" else None,
            "macro_current_count": sum(m["current"] for m in metrics),
        })
    under_pressure = [x for x in countries if x["market"]["state"] == "pressure"]
    growth_forecasts = [x for x in countries if x["forecast"] and x["forecast"]["current"] > 0]
    uptrends = [x for x in countries if x["market"]["state"] == "uptrend"]
    qualified_market_count = sum(x["market"]["state"] != "unknown" for x in countries)
    focus = min(under_pressure, key=lambda x: x["market"]["drawdown"] if x["market"]["drawdown"] is not None else 0) if under_pressure else (countries[0] if countries else None)
    return {
        "schema": SCHEMA, "evaluated_at": today.isoformat(), "source_as_of": latest.get("date"),
        "countries": countries, "count": len(countries),
        "display_countries": ([focus] + [c for c in countries if c is not focus]) if focus else [],
        "world_brief": _world_brief(countries),
        "expansion_count": len(growth_forecasts), "forecast_count": sum(bool(x["forecast"]) for x in countries),
        "pressure_count": len(under_pressure), "uptrend_count": len(uptrends),
        "qualified_market_count": qualified_market_count,
        "pressure_names_en": ", ".join(x["name_en"] for x in under_pressure),
        "pressure_names_zh": "、".join(x["name_zh"] for x in under_pressure),
        "focus_cc": focus["cc"] if focus else None,
        "focus": focus,
        "basis": "Dated observations, attributed forecasts and conditional interpretation",
    }
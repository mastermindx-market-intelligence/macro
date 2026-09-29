"""Display-only, source-attributed evidence for the four China macro dialogs.

This is an additive projection of the existing parquet owners, NOT a new signal,
policy, collector, or point-in-time store. It never writes to the data store and
never feeds ranking, entry permission, position sizing, or alerts. The same
JSON-safe contract is rendered by the site and published for machine consumers.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from math import isfinite
from typing import Callable
from zoneinfo import ZoneInfo

import pandas as pd

SCHEMA = "mastermind.china_macro_evidence.v1"
Read = Callable[[str, str], pd.DataFrame | None]
# Stored monthly dates often use the FIRST day as a period label. They must not
# become evidence for a completed month before that calendar month has ended.
MONTHLY_SOURCES = {
    "china_credit/tsf", "china_macro/money_supply", "china_macro/fai",
    "china_macro/retail", "china_macro/customs", "china_property/home_price",
    "china_property/climate", "china_property/activity",
}
SOURCES = {
    "credit": ("PBoC · monthly TSF", "https://www.pbc.gov.cn/diaochatongjisi/116219/index.html"),
    "macro": ("NBS / PBoC via Eastmoney", "https://data.eastmoney.com/cjsj/"),
    "property": ("NBS via Eastmoney", "https://www.stats.gov.cn/english/PressRelease/"),
    "futures": ("Sina · continuous main contracts", "https://finance.sina.com.cn/futures/"),
    "curve": ("China government yield curve via Eastmoney", "https://data.eastmoney.com/cjsj/zggzsyl.html"),
    "margin": ("Exchange margin statistics via Eastmoney", "https://data.eastmoney.com/rzrq/"),
    "connect": ("Eastmoney · aggregate Connect history", "https://data.eastmoney.com/hsgt/hsgtV2.html"),
    "limits": ("Eastmoney · limit-price breadth", "https://data.eastmoney.com/ztb/"),
    "activity": ("NBS · national property release", "https://www.stats.gov.cn/sj/zxfb/"),
    "price": ("Canonical China price store · 512200.SS", "https://www.sse.com.cn/"),
}
STATUS = {
    "recent": ("Recent", "近期数据"),
    "stale": ("Older data", "较早数据"),
    "unavailable": ("Unavailable", "暂无数据"),
    "partial": ("Partial coverage", "覆盖不完整"),
    "quality_hold": ("Verification needed", "待核验"),
    "reference": ("Historical reference", "历史参考"),
}


def finite(value) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        v = float(value)
        return v if isfinite(v) else None
    except (ValueError, TypeError):
        return None


def _series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        return pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    return pd.to_numeric(frame[column], errors="coerce").replace([float("inf"), -float("inf")], float("nan"))


def monthly(series: pd.Series) -> pd.Series:
    """Calendar-month continuity, not 12 arbitrary rows. Missing months stay null."""
    if series.empty:
        return series
    s = series.copy()
    s.index = s.index.to_period("M").to_timestamp()
    if s.index.has_duplicates:
        return pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    return s.asfreq("MS")


def rolling_sum(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window, min_periods=window).sum()


def percentile(series: pd.Series, window: int = 252, minimum: int = 60) -> dict:
    sample = series.tail(window).dropna()
    if len(sample) < minimum:
        return {"value": None, "n": len(sample), "window": window, "start": None, "end": None}
    return {"value": round(float((sample <= sample.iloc[-1]).mean() * 100), 1),
            "n": len(sample), "window": window,
            "start": sample.index[0].date().isoformat(), "end": sample.index[-1].date().isoformat()}


def true_credit_impulse(monthly_tsf: pd.Series, nominal_gdp_4q: pd.Series) -> pd.Series:
    """Annual change in trailing-12m TSF / trailing-4q NOMINAL GDP, pp of GDP.

    Both inputs must already be in the same currency/unit. The GDP input must be
    a certified, non-overlapping four-quarter level indexed to quarter-end, NOT
    GDP YoY or year-to-date growth. No interpolating or forward-filling releases.
    It is bound only when the explicit nominal-GDP level column is available.
    Current-vintage diagnostics are not point-in-time trading evidence.
    """
    if monthly_tsf.empty or nominal_gdp_4q.empty:
        return pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    tsf = rolling_sum(monthly(monthly_tsf), 12)
    if tsf.empty:
        return pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    tsf.index = tsf.index.to_period("M").to_timestamp("M")
    gdp = nominal_gdp_4q.copy().sort_index()
    gdp.index = gdp.index.to_period("Q").to_timestamp("Q")
    if gdp.index.has_duplicates:
        return pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    ratio = tsf.reindex(gdp.index).div(gdp.where(gdp > 0)) * 100
    ratio = ratio.asfreq("QE")
    return ratio.diff(4)


def nominal_gdp_four_quarters(ytd: pd.Series) -> pd.Series:
    """De-accumulate nominal calendar-YTD GDP, then sum four complete quarters.

    GDP YoY is never an acceptable input. Missing/duplicate quarters, nonpositive
    standalone quarters and missing within-year predecessors stay unavailable.
    The input/output units are unchanged (the collector's CNY100m).
    """
    if ytd.empty:
        return pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    x = pd.to_numeric(ytd, errors="coerce").copy().sort_index()
    x.index = x.index.to_period("Q").to_timestamp("Q")
    if x.index.has_duplicates:
        return pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    x = x.asfreq("QE")
    standalone = x.diff()
    q1 = x.index.quarter == 1
    standalone.loc[q1] = x.loc[q1]
    standalone = standalone.where(standalone > 0)
    return rolling_sum(standalone, 4)


class Snapshot:
    def __init__(self, read: Read, as_of: date):
        self.read, self.as_of = read, pd.Timestamp(as_of)
        self.cache: dict[str, pd.DataFrame] = {}
        self.errors: dict[str, str] = {}

    def frame(self, group: str, name: str) -> pd.DataFrame:
        key = f"{group}/{name}"
        if key in self.cache:
            return self.cache[key]
        try:
            df = self.read(group, name)
            df = df.copy() if df is not None else pd.DataFrame()
            if not df.empty:
                df.index = pd.to_datetime(df.index, errors="coerce")
                if df.index.isna().any() or df.index.has_duplicates:
                    raise ValueError("invalid_or_duplicate_reference_dates")
                if df.index.tz is not None:
                    df.index = df.index.tz_convert("Asia/Shanghai").tz_localize(None)
                df = df.sort_index().loc[lambda x: x.index.normalize() <= self.as_of]
                if key in MONTHLY_SOURCES:
                    df = df.loc[df.index.to_period("M").end_time.normalize() <= self.as_of]
                elif key == "china_macro/gdp":
                    df = df.loc[df.index.to_period("Q").end_time.normalize() <= self.as_of]
                # This column is a MODELLED date in the existing TSF collector,
                # not an observed publication timestamp. Preserve that distinction.
                if "availability_date" in df:
                    available = pd.to_datetime(df["availability_date"], errors="coerce")
                    df = df.loc[available.notna() & (available <= self.as_of)]
                if "publication_time" in df:
                    published = pd.to_datetime(df["publication_time"], errors="coerce", utc=True)
                    cutoff = (self.as_of.tz_localize("Asia/Shanghai") + pd.Timedelta(days=1)).tz_convert("UTC")
                    df = df.loc[published.notna() & (published < cutoff)]
        except Exception as exc:  # one broken owner must not erase all four dialogs
            self.errors[key] = f"{type(exc).__name__}: {str(exc)[:160]}"
            df = pd.DataFrame()
        self.cache[key] = df
        return df

    def metric(self, ident: str, label: tuple[str, str], series: pd.Series, unit: str,
               source: str, path: str, method: tuple[str, str], *, frequency="daily",
               digits=2, signed=False, status: str | None = None, note=("", ""),
               chart_kind="line", reference=None, primary=False) -> dict:
        series = pd.to_numeric(series, errors="coerce").replace([float("inf"), -float("inf")], float("nan"))
        valid = series.dropna()
        # Do not borrow an earlier value when the latest reported row is null.
        # In particular an incomplete latest rolling window is NOT the old window.
        last = series.index[-1] if not series.empty else None
        value = finite(series.iloc[-1]) if last is not None else None
        observed = last.date().isoformat() if last is not None else None
        period_end = last + pd.offsets.MonthEnd(0) if last is not None and frequency == "monthly" else last
        age = max(0, (self.as_of - period_end.normalize()).days) if period_end is not None else None
        # Calendar age is explicitly NOT exchange-calendar freshness or a release SLA.
        guard = {"monthly": 62, "quarterly": 150}.get(frequency, 7)
        state = status or ("unavailable" if value is None else "stale" if age is not None and age > guard else "recent")
        if value is None and state not in {"quality_hold", "partial"}:
            state = "unavailable"
        delta = finite(series.iloc[-1] - series.iloc[-2]) if len(series) >= 2 else None
        fmt = f"{{:{'+' if signed else ''},.{digits}f}}"
        safe = series.tail(504 if frequency == "daily" else 120)
        # Keep nulls in the contract; the chart adapter never bridges a missing row.
        chart = {"dates": [d.date().isoformat() for d in safe.index],
                 "vals": [finite(v) for v in safe]}
        result = {"id": ident, "label_en": label[0], "label_zh": label[1],
                "value": round(value, digits) if value is not None else None,
                "display": fmt.format(value) if value is not None else "—", "unit": unit,
                "delta_unit": "pp" if unit in {"%", "% YoY"} else unit,
                "reference_label": (last.strftime("%Y-%m") if frequency == "monthly" else
                                    f"{last.year} Q{last.quarter}" if frequency == "quarterly" else observed) if last is not None else None,
                "reference_date": observed, "frequency": frequency, "age_days": age,
                "age_guard_days": guard, "status": state,
                "status_en": STATUS[state][0], "status_zh": STATUS[state][1],
                "delta": round(delta, digits) if delta is not None else None,
                "delta_display": f"{delta:+,.{digits}f}" if delta is not None else None,
                "previous_date": series.index[-2].date().isoformat() if len(series) >= 2 else None,
                "last_valid_date": valid.index[-1].date().isoformat() if not valid.empty else None,
                "n": int(len(valid)), "source": {"name": SOURCES[source][0], "url": SOURCES[source][1],
                "store_path": path, "publication_time": None, "revision_vintage": None},
                "method_en": method[0], "method_zh": method[1], "note_en": note[0], "note_zh": note[1],
                "chart": chart, "chart_kind": chart_kind, "reference": reference, "primary": primary,
                "percentile": (percentile(series) if frequency == "daily" else percentile(series, 60, 24)) if value is not None else None}
        if source == "activity" and last is not None:
            frame = self.frame("china_property", "activity")
            if last in frame.index:
                row = frame.loc[last]
                def text(key):
                    v = row.get(key)
                    return v if isinstance(v, str) and v.strip() else None
                url = text("source_url")
                if isinstance(url, str) and url.startswith("https://www.stats.gov.cn/sj/"):
                    result["source"].update(url=url, publication_time=text("publication_time"),
                        publication_time_verified=bool(text("publication_time")),
                        observed_at=text("observed_at"), source_sha256=text("source_sha256"),
                        revision_vintage=text("vintage_status"))
                result["period_start"] = text("period_start")
                result["period_end"] = text("period_end")
        return result


def build_snapshot(read: Read | None = None, as_of: date | None = None) -> dict:
    if read is None:
        from lib import store
        read = store.read
    as_of = as_of or datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Shanghai")).date()
    ctx = Snapshot(read, as_of)
    metrics: dict[str, dict] = {}

    def add(*args, **kwargs):
        m = ctx.metric(*args, **kwargs)
        metrics[m["id"]] = m
        return m

    # POLICY: preserve the old engines' names/authority; use honest display labels.
    tsf = ctx.frame("china_credit", "tsf")
    total = monthly(_series(tsf, "tsf_total"))
    total12 = rolling_sum(total, 12)
    growth = total12.pct_change(12, fill_method=None).mul(100).replace([float("inf"), -float("inf")], float("nan"))
    add("financing_growth", ("New-financing momentum", "新增融资动能"), growth, "% YoY", "credit", "china_credit/tsf.tsf_total",
        ("Year-over-year growth in the trailing 12-month sum of new TSF. This is NOT GDP-normalized credit impulse. Requires 24 complete calendar months; no missing-month fill. Availability date is the collector's model, not a verified release timestamp.",
         "过去12个月新增社融总和的同比增速，不是GDP标准化信贷脉冲。须有24个完整月份；缺月不填补。可用日期为采集器模型值，并非核验过的发布时间。"),
        frequency="monthly", digits=1, signed=True, chart_kind="bars", reference=0, primary=True)
    add("tsf_month", ("New financing · latest month", "最新月新增社融"), total / 10, "CNY bn", "credit", "china_credit/tsf.tsf_total",
        ("Single-month TSF flow. Source CNY100m is divided by 10 to CNY billions; not a year-to-date total.", "单月新增社融。源单位亿元除以10换算为十亿元人民币，并非年内累计。"), frequency="monthly", digits=1)
    add("tsf_12m", ("New financing · trailing year", "过去12个月新增社融"), total12 / 10000, "CNY tn", "credit", "china_credit/tsf.tsf_total",
        ("Sum of 12 complete calendar months of new financing, not outstanding credit stock.", "12个完整月份新增融资总和，并非融资存量。"), frequency="monthly", digits=2)
    gdp = ctx.frame("china_macro", "gdp")
    gdp4 = nominal_gdp_four_quarters(_series(gdp, "nominal_gdp_ytd_cny100m"))
    impulse = true_credit_impulse(total, gdp4)
    add("financing_gdp_change", ("Financing / GDP · annual change", "融资／GDP·年度变化"), impulse,
        "pp of GDP", "macro", "china_credit/tsf + china_macro/gdp.nominal_gdp_ytd_cny100m",
        ("Quarter-end trailing-12-month new TSF divided by trailing-four-quarter nominal GDP, minus the ratio four quarters earlier. Nominal calendar-YTD GDP is de-accumulated within each year; no interpolation or growth-rate denominator. Current revised data, not a certified point-in-time leading signal.",
         "季末过去12个月新增社融除以过去4个季度名义GDP，再减去一年前的比值。名义年内累计GDP先按同年季度差分；不插值，不用增速作分母。采用当前修订数据，不是经认证的时点领先信号。"),
        frequency="quarterly", digits=2, signed=True, reference=0, chart_kind="bars",
        note=("GDP levels must have been ingested by the updated collector; GDP YoY alone is insufficient.", "须由新版采集器采入名义GDP水平；仅有GDP同比增速时不可计算。"))
    mix = []
    if not tsf.empty:
        row = tsf.iloc[-1]
        for key, en, zh in [("rmb_loans", "RMB loans", "人民币贷款"), ("fx_loans", "FX loans", "外币贷款"),
                            ("govt_bonds", "Government bonds", "政府债券"), ("corp_bonds", "Corporate bonds", "企业债券"),
                            ("entrust", "Entrusted loans", "委托贷款"), ("trust", "Trust loans", "信托贷款"),
                            ("accept_bills", "Undiscounted bills", "未贴现票据"), ("equity", "Equity finance", "股票融资")]:
            v = finite(row.get(key))
            mix.append({"id": key, "label_en": en, "label_zh": zh, "value": round(v / 10, 2) if v is not None else None})
        denom = finite(row.get("tsf_total"))
        known = [r["value"] for r in mix if r["value"] is not None]
        residual = denom / 10 - sum(known) if denom is not None and len(known) == len(mix) else None
        mix.append({"id": "other_residual", "label_en": "Other / reconciliation residual", "label_zh": "其他／对账差额", "value": round(residual, 2) if residual is not None else None})
    govt = monthly(_series(tsf, "govt_bonds"))
    share = govt.div(total.where(total > 0)).mul(100)
    add("government_share", ("Government share of new TSF", "政府债券占新增社融"), share, "%", "credit", "china_credit/tsf.govt_bonds/tsf_total",
        ("Government bond financing / net total TSF, same reference month. Other components may be negative; this share can exceed 100% and is not evidence of private credit demand.", "同一参考月政府债券融资除以新增社融净额。其他分项可为负，占比可能超过100%，不能据此判断私人信贷需求。"), frequency="monthly", digits=1)
    money = ctx.frame("china_macro", "money_supply")
    spread = monthly(_series(money, "m1_yoy") - _series(money, "m2_yoy"))
    # Unverified pre/post-2025 histories must never appear as one comparable line.
    spread = spread.loc[spread.index >= pd.Timestamp("2025-01-01")]
    add("money_spread", ("M1 growth minus M2 growth", "M1与M2增速差"), spread, "pp", "macro", "china_macro/money_supply.m1_yoy,m2_yoy",
        ("Difference of reported year-over-year growth rates; not a money level. PBoC revised M1 in January 2025. Pre-2025 history is excluded here; source rebasing/vintage is not certified.", "两项同比增速之差，并非货币存量。央行于2025年1月调整M1口径；此处不拼接此前历史，源数据回溯版本尚未认证。"), frequency="monthly", digits=1, signed=True, chart_kind="bars", reference=0, primary=True)
    rrr = ctx.frame("china_macro", "rrr")
    add("rrr_record", ("Large-bank RRR · last record", "大型银行存准率·最后记录"), _series(rrr, "rrr_big"), "%", "macro", "china_macro/rrr.rrr_big",
        ("Large-bank series, not the system-wide weighted-average reserve ratio. Event date is the last recorded change; it does not certify today's effective rate or policy stance.", "大型银行序列，不是全系统加权平均存准率。日期是最后记录事件，不能证明今日有效利率或当前政策立场。"), status="reference", digits=2, primary=True)
    events = []
    for idx, row in rrr.tail(8).iloc[::-1].iterrows():
        events.append({"date": idx.date().isoformat(), "change": finite(row.get("rrr_change")), "level": finite(row.get("rrr_big"))})
    tape = []
    for name, column, en, zh in [("fai", "fai_yoy", "Fixed-asset investment · YTD", "固定资产投资·年内累计"),
                                 ("retail", "retail_yoy", "Retail sales · YoY", "社会消费品零售·同比"),
                                 ("customs", "exports_yoy", "Exports · YoY", "出口·同比"),
                                 ("customs", "imports_yoy", "Imports · YoY", "进口·同比")]:
        ident = "macro_" + column
        add(ident, (en, zh), monthly(_series(ctx.frame("china_macro", name), column)), "%", "macro", f"china_macro/{name}.{column}",
            ("Provider-reported growth. Reference period shown separately; YTD and monthly rates are not added or scored together. Customs currency basis must be read from the original release.", "供应方报告的增速，分别标示参考期；累计同比与单月同比不相加、不共同评分。海关币种口径应查原始发布。"), frequency="monthly", digits=1, signed=True)
        tape.append(ident)

    # SENTIMENT: activity, leverage and direction are different observations.
    bal = ctx.frame("china_margin", "balance")
    trade = ctx.frame("china_margin", "daily_trade")
    add("margin_ratio", ("Financing / float market value", "融资余额／流通市值"), _series(bal, "fin_pct_float"), "%", "margin", "china_margin/balance.fin_pct_float",
        ("Financing balance relative to the provider's float-market-value denominator. The percentile uses up to 252 observations and at least 60; high crowding is not a bullish signal.", "融资余额相对供应方流通市值分母。分位基于最多252个观测、至少60个观测；高拥挤度不是看涨信号。"), digits=2, primary=True)
    net_margin = _series(bal, "net_fin_buy")
    add("margin_net20", ("Net financing · 20 sessions", "20个观测交易日融资净买入"), rolling_sum(net_margin, 20) / 10, "CNY bn", "margin", "china_margin/balance.net_fin_buy",
        ("Sum of 20 reported sessions, requiring all 20 non-null values. CNY100m / 10 = CNY billions. Missing sessions are not zero.", "须有20个非空交易日观测才计算总和。亿元除以10换算为十亿元人民币，缺值不是零。"), digits=2, signed=True, reference=0)
    turnover = _series(trade, "margin_trade_amt").div(_series(trade, "trade_amt_ratio").where(lambda x: x > 0)).mul(100).div(10000)
    add("turnover", ("A-share trading activity", "A股成交活跃度"), turnover, "CNY tn", "margin", "china_margin/daily_trade.margin_trade_amt,trade_amt_ratio",
        ("Derived whole-market turnover = margin-trade amount / margin-trade share. This is a derived activity estimate, not directional buying or a directly collected exchange turnover total.", "由两融成交额除以两融成交占比推算全市场成交额；这是活跃度估算，不是方向性买入，也不是直接采集的交易所总成交额。"), digits=2, primary=True)
    add("maintenance", ("Margin maintenance ratio", "平均维持担保比例"), _series(trade, "guarantee_ratio"), "%", "margin", "china_margin/daily_trade.guarantee_ratio",
        ("Aggregate maintenance ratio, not an individual account's liquidation threshold.", "全市场平均维持担保比例，不是个人账户平仓阈值。"), digits=1)
    add("margin_trade_share", ("Margin share of turnover", "两融成交占比"), _series(trade, "trade_amt_ratio"), "%", "margin", "china_margin/daily_trade.trade_amt_ratio",
        ("Margin-related turnover / covered market turnover, as reported by the provider.", "供应方报告的两融成交额占其覆盖市场成交额之比。"), digits=2)
    limits = ctx.frame("china_flows", "limit_breadth")
    ups, downs = _series(limits, "zt"), _series(limits, "dt")
    add("limit_balance", ("Limit-up minus limit-down", "涨停数减跌停数"), ups - downs, "stocks", "limits", "china_flows/limit_breadth.zt,dt",
        ("Signed count, not whole-market advance/decline breadth. Boards have different price-limit rules. Up, down and failed-limit counts use the same stored session.", "有符号计数，不等于全市场涨跌家数；不同板块涨跌停规则不同。涨停、跌停与炸板数来自同一存储交易日。"), digits=0, signed=True, reference=0, chart_kind="bars", primary=True)
    add("seal_rate", ("Limit-up seal rate", "涨停封板率"), _series(limits, "seal_rate"), "%", "limits", "china_flows/limit_breadth.seal_rate",
        ("Provider-reported sealed-limit share; zero and unavailable remain different states.", "供应方报告的封板占比；零与缺失分开处理。"), digits=1)
    limit_counts = {k: finite(limits.iloc[-1].get(k)) if not limits.empty else None for k in ["zt", "dt", "zb"]}

    # CONNECT: source aggregate convention is CNY; stock-level tables are HKD.
    sb = ctx.frame("china_connect", "southbound")
    net = _series(sb, "net")
    for window in (1, 5, 20):
        values = net if window == 1 else rolling_sum(net, window)
        add(f"southbound_{window}", (("Latest net buying" if window == 1 else f"Net buying · {window} sessions"), ("最新交易日净买入" if window == 1 else f"{window}个观测交易日净买入")),
            values / 1000, "CNY bn", "connect", "china_connect/southbound.net",
            (f"Eastmoney aggregate-flow convention: raw million CNY / 1,000 = CNY billions. {window} complete reported session(s). Net executed buying is not quota usage. Not added to HKD stock-level figures.",
             f"东方财富汇总资金口径：原始百万元除以1000为十亿元人民币。须有{window}个完整观测交易日；成交净买入不等于额度使用，不与港元个股数据相加。"),
            digits=2, signed=True, reference=0, chart_kind="bars" if window == 1 else "baseline", primary=True)
    buy_days = net.gt(0).astype(float).where(net.notna()).rolling(20, min_periods=20).sum()
    add("southbound_buy_days", ("Buying days in 20 sessions", "20个观测交易日中净买入天数"), buy_days, "/ 20", "connect", "china_connect/southbound.net",
        ("Positive-net days among 20 complete reported sessions. This is a frequency, NOT a consecutive-day streak.", "20个完整观测交易日中净买入的天数，是频数，不是连续买入天数。"), digits=0)
    hold = _series(sb, "hold_mktcap")
    hold_metric = add("southbound_holdings", ("Southbound holdings · source record", "南向持仓·源记录"), hold / 10000, "source tn", "connect", "china_connect/southbound.hold_mktcap",
        ("Holdings are a stock, not a flow. Store is normalized to 100-million units but its holdings-currency provenance is not certified; do not use it in a currency comparison or a net-flow calculation.", "持仓是存量，不是流量。存储统一为亿单位，但持仓币种溯源尚未认证，不能用于跨币种比较或净流量计算。"), status="quality_hold", digits=2)
    hold_metric["display"] = "—"
    hold_metric["unverified_source_value"] = hold_metric["value"]
    hold_metric["value"] = None
    hold_metric["chart"] = {"dates": [], "vals": []}
    nb = ctx.frame("china_connect", "northbound")
    add("northbound_turnover", ("Northbound gross turnover", "北向成交总额"), _series(nb, "turnover") / 1000, "CNY bn", "connect", "china_connect/northbound.turnover",
        ("Gross turnover, not net capital inflow. Daily northbound net buy/sell disclosure ended in August 2024; no current net-flow figure is reconstructed from turnover.", "成交总额不是净流入。2024年8月北向每日净买卖披露停止，不从成交总额反推当前净流量。"), digits=2)

    # PROPERTY: count coverage, comparable construction legs, and curve shape.
    home = ctx.frame("china_property", "home_price")
    rising, falling, flat, cities = (_series(home, c) for c in ["new_rising", "new_falling", "new_flat", "cities"])
    coherent = ((rising + falling + flat == cities) & (cities > 0) & (cities <= 70)
                & (rising >= 0) & (falling >= 0) & (flat >= 0)
                & (rising.mod(1) == 0) & (falling.mod(1) == 0) & (flat.mod(1) == 0))
    pct = falling.div(cities.where(coherent)).mul(100)
    coverage = finite(cities.iloc[-1]) if not cities.empty else None
    breadth_status = "partial" if coverage is not None and coverage != 70 else None
    add("home_falling", ("Cities with falling new-home prices", "新房价格下跌城市占比"), pct, "%", "property", "china_property/home_price",
        ("Falling / covered cities, month over month. Counts must reconcile to the reported denominator. Coverage below 70 is partial, not a national 70-city result.", "环比下跌城市数除以覆盖城市数；涨跌平家数必须与分母一致。不足70城标为部分覆盖，不冒充完整70城结果。"), frequency="monthly", digits=1, status=breadth_status, primary=True)
    add("home_net", ("New-home price diffusion", "新房价格扩散度"), (rising - falling).where(coherent), "cities", "property", "china_property/home_price.new_rising,new_falling",
        ("Rising cities minus falling cities. A count, not percentage price change. Same cohort and reference month as the distribution.", "上涨城市数减下跌城市数，是家数差而非房价百分比变化；与分布图使用同一城市组和参考月。"), frequency="monthly", digits=0, signed=True, status=breadth_status, reference=0, chart_kind="bars")
    add("second_home", ("Resale-home price diffusion", "二手房价格扩散度"), _series(home, "second_breadth"), "net cities", "property", "china_property/home_price.second_breadth",
        ("Provider's resale rising-minus-falling city count. The legacy store does not record its own valid-city denominator, so a resale percentage is intentionally not invented.", "供应方二手房上涨减下跌城市数。旧存储未记录独立有效城市分母，因此不虚构二手房下跌百分比。"), frequency="monthly", digits=0, signed=True, reference=0, chart_kind="bars", primary=True)
    home_counts = {k: finite(home.iloc[-1].get(k)) if not home.empty else None for k in ["new_rising", "new_falling", "new_flat", "cities"]}
    climate = ctx.frame("china_property", "climate")
    add("climate", ("NBS real-estate climate", "国房景气指数"), _series(climate, "climate"), "index", "property", "china_property/climate.climate",
        ("NBS composite: 95–105 is the moderate band; below 95 is low. The current stored reference period is shown explicitly. An aged print cannot confirm today's property recovery.", "国家统计局综合指数：95至105为适度区间，低于95为偏低。明确展示存储参考期，滞后值不能确认当前房地产复苏。"), frequency="monthly", digits=2, reference=100)
    rebar = _series(ctx.frame("china_property", "rebar"), "close")
    iron = _series(ctx.frame("china_property", "iron_ore"), "close")
    aligned = pd.concat({"rebar": rebar, "iron_ore": iron}, axis=1).dropna()
    construction = aligned.pct_change(63, fill_method=None).mean(axis=1, skipna=False) * 100 if not aligned.empty else pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    add("construction_return", ("Steel + iron ore · 63-session move", "螺纹钢＋铁矿石·63个观测交易日变化"), construction, "%", "futures", "china_property/rebar.close + iron_ore.close",
        ("Equal-weight mean of 63-common-session returns, with both contracts aligned on the same dates. A price-momentum proxy, not measured construction demand. Continuous-contract rolls can affect returns. Headline and chart use the SAME percentage series.", "两合约同日对齐后63个共同观测交易日收益率的等权平均，是价格动量代理而非实际施工需求；连续合约换月可能影响收益。标题和图表使用同一百分比序列。"), digits=1, signed=True, reference=0, primary=True)
    curve = ctx.frame("china_property", "cgb")
    for tenor in (2, 5, 10, 30):
        add(f"cgb_{tenor}", (f"Government yield · {tenor} years", f"{tenor}年期国债收益率"), _series(curve, f"cgb_{tenor}y"), "%", "curve", f"china_property/cgb.cgb_{tenor}y",
            ("Sovereign yield level, not a property-developer credit spread or a fiscal-impulse measure.", "国债收益率水平，不是开发商信用利差或财政脉冲。"), digits=3)
    slope = (_series(curve, "cgb_10y") - _series(curve, "cgb_2y")) * 100
    add("curve_slope", ("10-year minus 2-year yield", "10年减2年国债利差"), slope, "bp", "curve", "china_property/cgb.cgb_10y,cgb_2y",
        ("Same-session yield difference in basis points (one percentage point = 100 bp).", "同一交易日收益率差，单位基点；1个百分点等于100基点。"), digits=1, signed=True, reference=0)
    prices = ctx.frame("china", "512200.SS")
    px = _series(prices, "close").where(lambda x: x > 0)
    jumps = px.pct_change(fill_method=None).abs().gt(.5)
    discontinuities = [d.date().isoformat() for d in jumps.index[jumps]]
    # A screening tripwire, NOT an assertion of corporate action or a silent repair.
    adjusted = prices.attrs.get("adjustment_verified") is True
    held = bool(discontinuities) and not adjusted
    dd = px.div(px.cummax()).sub(1).mul(100)
    m = add("property_drawdown", ("Property ETF · available-history drawdown", "地产ETF·可用历史回撤"), dd, "%", "price", "china/512200.SS.close",
        ("Drawdown from the peak of available history, not a proven all-time high. An unverified >50% single-session price move triggers a basis-review hold; no return is silently stitched or adjusted.", "相对可用历史峰值的回撤，不宣称完整历史最高点。未经核验的单日超过50%价格变化触发口径核验，不暗中拼接或调整收益。"), digits=1, signed=True, status="quality_hold" if held else None)
    m["discontinuities"] = discontinuities
    if held:
        m.update(value=None, display="—", chart={"dates": [], "vals": []}, delta=None, delta_display=None,
                 note_en=f"{len(discontinuities)} large price discontinuities; adjusted-price verification required.",
                 note_zh=f"发现{len(discontinuities)}处价格突变，须核验复权口径。")

    # Origin-published property volumes/funding, kept distinct from price proxies.
    activity = ctx.frame("china_property", "activity")
    activity_ids = []
    activity_fields = [
        ("sales_area", "New-home sales area", "新建商品房销售面积"),
        ("resale_area", "Resale registrations · area", "二手房网签面积"),
        ("investment", "Property development investment", "房地产开发投资"),
        ("starts", "New construction starts · area", "房屋新开工面积"),
        ("completions", "Completed construction · area", "房屋竣工面积"),
        ("sales_value", "New-home sales value", "新建商品房销售额"),
        ("funds", "Developer funding received", "开发商到位资金"),
        ("domestic_loans", "Developer domestic bank loans", "开发商国内贷款"),
        ("mortgages", "Individual mortgage funding", "个人按揭贷款资金"),
        ("deposits", "Deposits and advance receipts", "定金及预收款"),
        ("inventory", "Completed unsold floor area", "已竣工待售面积"),
    ]
    for stem, en, zh in activity_fields:
        stock = stem == "inventory"
        period = "stock" if stock else "ytd"
        ident = "property_" + stem
        col = f"{stem}_{period}_yoy"
        m = add(ident, (en + (" · end-month YoY" if stock else " · YTD YoY"), zh + ("·月末同比" if stock else "·累计同比")),
            _series(activity, col), "%", "activity", "china_property/activity." + col,
            (("End-month completed unsold area stock growth, not months of supply." if stock else
              "Published cumulative year-to-date growth on the official comparable basis, not monthly growth. Do not difference YTD percentages to infer a single month.") +
             " New-home contracts and resale registrations have different reporting universes and must not be mechanically added. Current releases may revise comparatives.",
             ("月末已竣工待售面积存量增速，不是库存去化月数。" if stock else "官方可比口径年内累计同比，不是单月增速；不得对累计增速做差来推算单月。") +
             "新房合同与二手房网签统计范围不同，不能机械相加；当前发布可能修订同比基数。"),
            frequency="monthly", digits=1, signed=True, reference=0,
            primary=stem in {"sales_area", "resale_area"})
        activity_ids.append(ident)
    metrics["rrr_record"]["primary"] = False
    metrics["government_share"]["primary"] = True
    metrics["second_home"]["primary"] = False
    metrics["construction_return"]["primary"] = False

    # Headlines are conservative descriptions, not another scoring engine.
    def usable(ident):
        m = metrics[ident]
        return m["value"] if m["status"] == "recent" else None

    fg = usable("financing_growth")
    policy_head = (("Rolling-year financing is below last year.", "过去一年新增融资低于去年同期。") if fg is not None and fg < 0 else
                   ("Rolling-year financing is above last year.", "过去一年新增融资高于去年同期。") if fg is not None and fg > 0 else
                   ("Credit transmission needs a closer read.", "信贷传导需要进一步核对。"))
    d1, d20 = usable("southbound_1"), usable("southbound_20")
    flows_head = (("Selling in the latest session; 20-session buying remains positive.", "最新交易日净卖出，20日累计仍净买入。") if d1 is not None and d20 is not None and d1 < 0 < d20 else
                  ("Buying in the latest session; 20-session selling remains negative.", "最新交易日净买入，20日累计仍净卖出。") if d1 is not None and d20 is not None and d20 < 0 < d1 else
                  ("Read daily flow and persistent buying separately.", "把单日资金与持续买入力度分开看。"))
    hf = usable("home_falling")
    property_head = (("Home-price weakness is still widespread.", "房价走弱仍较广泛。") if hf is not None and hf > 50 else
                     ("Home-price declines are not a majority of covered cities.", "房价下跌城市未占已覆盖城市的多数。") if hf is not None else
                     ("Property evidence is incomplete or aged.", "房地产证据不完整或已滞后。"))
    new_sales, resales = usable("property_sales_area"), usable("property_resale_area")
    if (new_sales is not None and resales is not None and new_sales < 0 < resales and
            metrics["property_sales_area"]["reference_date"] == metrics["property_resale_area"]["reference_date"]):
        property_head = ("Resale activity is rising; new-home demand and prices need separate checks.",
                         "二手房交易活跃度上升；新房需求与价格仍须分别核对。")
    sentiment_ids = ["margin_ratio", "turnover", "limit_balance"]
    dates = {metrics[i]["reference_date"] for i in sentiment_ids}
    lb = usable("limit_balance")
    sentiment_head = (("Trading activity is not the same as buying conviction.", "成交活跃不等于买盘坚定。") if len(dates) == 1 and None not in dates else
                      ("Different observation dates: assess each leg separately.", "观测日期不同，请逐项判断。"))
    if len(dates) == 1 and None not in dates and lb is not None and lb < 0:
        sentiment_head = ("Limit-downs outnumber limit-ups; activity is not confirmation.", "跌停多于涨停，活跃成交并不构成确认。")
    specs = [
        ("policy", ("Policy & credit", "政策与信贷"), policy_head,
         ("Separate the policy setting, real financing transmission and the macro outcomes. A rate cut alone is not proof of stronger private demand.", "区分政策设置、实际融资传导与宏观结果。降准本身不能证明私人需求转强。"),
         ["financing_growth", "money_spread", "government_share", "tsf_month", "tsf_12m", "financing_gdp_change", "rrr_record"] + tape,
         ("Watch financing momentum and its government/private composition together. The GDP-normalized diagnostic is separate and current-vintage only; it does not validate a leading signal.", "同时观察融资动能与政府／非政府分项。GDP标准化诊断单独展示，仅代表当前版本，不验证领先信号。")),
        ("property", ("Property & fiscal context", "房地产与财政背景"), property_head,
         ("Housing prices, construction-market prices and government yields answer different questions. Aged or broken evidence does not confirm a recovery.", "房价、建筑商品价格与国债收益率回答不同问题；滞后或断裂数据不能确认复苏。"),
         ["home_falling"] + activity_ids + ["second_home", "construction_return", "home_net", "climate", "cgb_2", "cgb_5", "cgb_10", "cgb_30", "curve_slope", "property_drawdown"],
         ("Watch broader city stabilization and repeated improvement in real activity. Bond yields and futures are context, not a fiscal spending impulse or developer credit spread.", "关注更多城市企稳与实际活动持续改善。债券和期货只作背景，不冒充财政支出脉冲或开发商信用利差。")),
        ("flows", ("Connect flows", "互联互通资金"), flows_head,
         ("Mainland-to-Hong-Kong executed flows: daily pressure, persistence and stock-level disclosure are kept separate. This is positioning context, not verified smart-money skill.", "内地至香港成交资金：分开看单日压力、持续性与个股披露。这是持仓背景，不代表已验证的聪明钱能力。"),
         ["southbound_1", "southbound_5", "southbound_20", "southbound_buy_days", "northbound_turnover", "southbound_holdings"],
         ("Look for repeated net buying across complete reported sessions. Top-active stock tables are a partial universe, not a map of every destination of capital.", "观察完整观测交易日中的持续净买入。活跃股榜仅覆盖部分证券，并非全部资金流向图。")),
        ("sentiment", ("Market sentiment", "市场情绪"), sentiment_head,
         ("Read leverage, trading activity and speculative breadth independently. High activity or crowding is not automatically bullish.", "分别阅读杠杆、成交活跃度与投机广度。高成交或高拥挤度并不自动看涨。"),
         sentiment_ids + ["margin_net20", "maintenance", "margin_trade_share", "seal_rate"],
         ("Watch whether financing flows and price-limit breadth improve together on the same session. A sentiment observation does not change the governed entry policy.", "观察同一交易日融资流与涨跌停广度是否同步改善。情绪观测不改变受治理的入场政策。")),
    ]
    panels = {}
    for ident, title, head, desc, ids, watch in specs:
        mm = [metrics[i] for i in ids]
        panels[ident] = {"id": ident, "title_en": title[0], "title_zh": title[1], "headline_en": head[0], "headline_zh": head[1],
                         "description_en": desc[0], "description_zh": desc[1], "watch_en": watch[0], "watch_zh": watch[1],
                         "metrics": mm, "recent": sum(m["status"] == "recent" for m in mm), "total": len(mm)}
    return {"schema": SCHEMA, "observation_cutoff": as_of.isoformat(),
            "generated_at": datetime.now(timezone.utc).isoformat(), "authority": "display_only",
            "replay_eligible": False, "publication_time_verified": False,
            "panels": panels, "tsf_mix": mix, "rrr_events": events, "home_counts": home_counts,
            "limit_counts": limit_counts, "source_errors": ctx.errors,
            "limitations": ["Current stored vintages, not point-in-time replay.",
                            "Age guards are calendar-day disclosure, not exchange-calendar availability guarantees.",
                            "No ranking, sizing, entry permission or alerts are changed."]}

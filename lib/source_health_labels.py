"""Reviewed bilingual display labels for the data-health panel.

``data/run_status.json`` keys every source by its collector id. Those ids are
producer identifiers: they stay exactly as they are in data files, logs and
tests. Several of them carry the name of the commercial provider behind the
collector, and the product law is that a provider is never named on a product
surface. The health panel therefore renders a reviewed ``{"en", "zh"}`` label
per id instead of the id itself.

This module is pure presentation. It never changes a status, a row count or a
date. It fails closed: an id without a reviewed label renders as the generic
label, never as words derived from the id, because a provider token list cannot
know every provider a future collector may be named after. The build lists such
ids through :func:`unreviewed_ids` so they get a reviewed label. :func:`neutral_note`
applies the same law to the free-text note column, which repeats collector ids,
provider names, hosts and URLs out of exception messages.

Bilingual law (house rule): a label is a PAIR. Exactly one language is visible
at a time via the site's ``.l-en`` / ``.l-zh`` toggle; a page never shows both.
"""
from __future__ import annotations

import re
from typing import Iterable


def _pair(en: str, zh: str) -> dict[str, str]:
    return {"en": en, "zh": zh}


# Commercial providers and provider client libraries. Public institutions
# (central banks, regulators, statistics agencies, exchanges) may be named and
# are deliberately absent. Multi-word phrases come first so they match whole.
PROVIDER_TOKENS: tuple[str, ...] = (
    "google trends", "twitter/x",
    "yfinance", "yahoo", "tushare", "polygon", "massive", "quiver", "finnhub",
    "coinbase", "coingecko", "coinmetrics", "deribit", "okx", "stocktwits",
    "ibkr", "farside", "defillama", "kalshi", "huggingface", "github", "google",
    "openfigi", "bgeo", "alpaca", "benzinga", "databento", "thetadata",
    "tiingo", "tencent", "eastmoney", "cninfo", "gdelt", "finviz", "sina",
    "twitter",
)
CLIENT_LIBRARY_TOKENS: tuple[str, ...] = ("yfinance", "pytrends", "akshare")

PROVIDER_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(t) for t in PROVIDER_TOKENS)
    + r")(?![A-Za-z0-9])"
)
_LIBRARY_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(t) for t in CLIENT_LIBRARY_TOKENS)
    + r")(?![A-Za-z0-9])"
)
# Any scheme in any case ("HTTPS://", "ftp://"). Quotes and brackets end a URL
# so the text around it stays intact.
_URL_RE = re.compile(r"(?i)[a-z][a-z0-9+.-]*://[^\s;,|)'\"<>]+")
# host='…', host="…" and host=… as client libraries print them.
_HOST_ARG_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9_])((?:server_)?host(?:name)?)\s*=\s*(?:'[^']*'|\"[^\"]*\"|[^\s,;)'\"]+)"
)
# Case-insensitive, because an error can print a host in capitals. Tickers
# ("0700.HK") and attribute paths ("Ticker.info") stay readable through the
# suffix rules instead: a short country or tech suffix needs two labels in front
# of it, so "0700.HK" and "pandas.io" survive while "API.EXAMPLE.IO" does not.
_DOMAIN_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9@.-])(?:"
    r"(?:[a-z0-9-]+\.)+(?:com|net|org|gov|edu)"
    r"|(?:[a-z0-9-]+\.){2,}(?:io|ai|dev|app|co|cn|hk|ca|uk|jp|space)"
    r")(?![A-Za-z0-9-]|\.[a-z0-9])"
)

GENERIC = _pair("Market data source", "市场数据源")

LABELS: dict[str, dict[str, str]] = {
    "beneficial_ownership": _pair("Beneficial ownership filings", "实益持股申报"),
    "bgeo": _pair("On-chain bitcoin metrics", "比特币链上指标"),
    "bis": _pair("BIS international statistics", "国际清算银行统计"),
    "breadth": _pair("US market breadth", "美股市场广度"),
    "broad_flows": _pair("Broad-market ETF flows", "宽基ETF资金流"),
    "canada_breadth": _pair("Canada market breadth", "加拿大市场广度"),
    "canada_macro": _pair("Canada macro data", "加拿大宏观数据"),
    "canada_prices": _pair("Canada market prices", "加拿大市场价格"),
    "canada_universe": _pair("Canada stock universe", "加拿大股票池"),
    "cboe_cor_vol": _pair("Implied correlation indices", "隐含相关性指数"),
    "cboe_gex": _pair("Options gamma exposure", "期权伽马敞口"),
    "cboe_putcall": _pair("Options put/call ratios", "期权认沽认购比"),
    "cboe_skew": _pair("Tail-risk skew index", "尾部风险偏度指数"),
    "cboe_vix_futures": _pair("Volatility futures curve", "波动率期货曲线"),
    "cboe_vvix": _pair("Volatility-of-volatility index", "波动率的波动率指数"),
    "china_a_valuation": _pair("China A-share valuation", "A股估值"),
    "china_board_breadth": _pair("China board breadth", "A股板块广度"),
    "china_breadth": _pair("China market breadth", "A股市场广度"),
    "china_cb": _pair("China convertible bonds", "中国可转债"),
    "china_cgb_curve": _pair("China government bond curve", "中国国债收益率曲线"),
    "china_connect": _pair("Stock Connect flows", "沪深港通资金流"),
    "china_credit": _pair("China credit data", "中国信贷数据"),
    "china_einteraction": _pair("Shanghai investor Q&A", "上交所投资者问答"),
    "china_filings": _pair("China exchange filings", "A股交易所公告"),
    "china_flows": _pair("China fund flows", "A股资金流向"),
    "china_fund_issuance": _pair("China fund issuance", "中国基金发行"),
    "china_funding": _pair("China money-market funding", "中国货币市场资金"),
    "china_holder_counts": _pair("China shareholder counts", "A股股东户数"),
    "china_irm": _pair("Shenzhen investor Q&A", "深交所投资者问答"),
    "china_lhb": _pair("China top-trader list", "A股龙虎榜"),
    "china_macro": _pair("China macro data", "中国宏观数据"),
    "china_margin": _pair("China margin financing", "A股融资融券"),
    "china_margin_detail": _pair("China margin detail", "A股融资融券明细"),
    "china_news": _pair("China news", "中国新闻"),
    "china_news_wire": _pair("China news wire", "中国新闻快讯"),
    "china_official_corpora": _pair("China official policy texts", "中国官方政策文本"),
    "china_omo": _pair("PBOC open-market operations", "央行公开市场操作"),
    "china_pboc": _pair("PBOC monetary data", "中国人民银行货币数据"),
    "china_prices": _pair("China market prices", "A股市场价格"),
    "china_property": _pair("China property data", "中国房地产数据"),
    "china_qvix": _pair("China options volatility", "中国期权波动率"),
    "china_reports": _pair("China research reports", "A股研究报告"),
    "china_sectors": _pair("China sector data", "A股行业数据"),
    "china_stocks": _pair("China stock prices", "A股个股价格"),
    "china_stocks_raw": _pair("China stock prices (raw)", "A股个股价格（原始）"),
    "china_trade_detail": _pair("China trade detail", "中国贸易明细"),
    "china_tushare": _pair("China market data", "中国市场数据"),
    "china_universe": _pair("China stock universe", "A股股票池"),
    "china_visits": _pair("China institutional visits", "A股机构调研"),
    "china_yield_spread": _pair("China yield spread", "中国收益率利差"),
    "cleveland_nowcast": _pair("Cleveland Fed inflation nowcast", "克利夫兰联储通胀即时预测"),
    "clinicaltrials": _pair("Clinical trial registry", "临床试验登记"),
    "coinbase": _pair("Crypto exchange prices", "加密货币交易所价格"),
    "coingecko": _pair("Crypto market overview", "加密市场概览"),
    "coinmetrics": _pair("Crypto network metrics", "加密网络指标"),
    "corp_bond_holdings": _pair("Corporate bond fund holdings", "公司债基金持仓"),
    "cot": _pair("CFTC positioning (COT)", "CFTC持仓报告"),
    "crypto_universe": _pair("Crypto universe", "加密资产池"),
    "defillama": _pair("Stablecoin supply", "稳定币供应"),
    "deribit": _pair("Crypto options", "加密期权"),
    "edgar_13f": _pair("SEC 13F holdings", "SEC 13F持仓"),
    "edgar_8k": _pair("SEC 8-K filings", "SEC 8-K公告"),
    "edgar_dilution": _pair("SEC dilution filings", "SEC稀释类申报"),
    "edgar_trumpflow": _pair("SEC policy-linked filings", "SEC政策关联申报"),
    "eia": _pair("EIA petroleum data", "EIA石油数据"),
    "etf_holdings": _pair("ETF holdings", "ETF持仓"),
    "farside": _pair("Spot bitcoin ETF flows", "现货比特币ETF资金流"),
    "feargreed": _pair("Crypto sentiment index", "加密情绪指数"),
    "fedboard_ebp": _pair("Excess bond premium", "超额债券溢价"),
    "federal_register": _pair("Federal Register notices", "联邦公报"),
    "finnhub_altdata": _pair("Alternative data", "另类数据"),
    "finnhub_transcripts": _pair("Earnings call transcripts", "业绩电话会纪要"),
    "finra_ats_transparency": _pair("FINRA ATS volume", "FINRA另类交易系统成交"),
    "finra_corp_bonds": _pair("FINRA corporate bond activity", "FINRA公司债交易"),
    "finra_otc_nonats": _pair("FINRA OTC volume", "FINRA场外成交"),
    "finra_short_volume": _pair("FINRA short volume", "FINRA卖空成交"),
    "flow_signals": _pair("Options flow event ledger", "期权资金流事件台账"),
    "frbsf_sentiment": _pair("SF Fed news sentiment", "旧金山联储新闻情绪"),
    "fred": _pair("Fed economic data", "美联储经济数据"),
    "french": _pair("Academic factor returns", "学术因子收益"),
    "fundamentals": _pair("Earnings revision breadth", "盈利修正广度"),
    "gaming_nj": _pair("New Jersey gaming revenue", "新泽西博彩收入"),
    "gaming_nv": _pair("Nevada gaming revenue", "内华达博彩收入"),
    "gaming_ny": _pair("New York gaming revenue", "纽约博彩收入"),
    "gaming_pgcb": _pair("Pennsylvania gaming revenue", "宾夕法尼亚博彩收入"),
    "geo_revenue": _pair("Geographic revenue (10-K)", "地区收入（10-K）"),
    "github_repos": _pair("Open-source developer activity", "开源开发者活跃度"),
    "gold_china_basis": _pair("China gold basis", "中国黄金基差"),
    "google_trends": _pair("Search interest", "搜索热度"),
    "grants_gov": _pair("Federal grants", "联邦拨款"),
    "hk_ah_official": _pair("A/H premium (official)", "A/H溢价（官方）"),
    "hk_ah_panel": _pair("A/H premium panel", "A/H溢价面板"),
    "hk_breadth": _pair("Hong Kong market breadth", "港股市场广度"),
    "hk_cbbc": _pair("HK callable bull/bear contracts", "港股牛熊证"),
    "hk_cbbc_sld": _pair("HK CBBC call prices", "港股牛熊证收回价"),
    "hk_closes_deep": _pair("Hong Kong closing history", "港股收盘历史"),
    "hk_connect_channels": _pair("Southbound Connect channels", "南向通道"),
    "hk_full_breadth": _pair("Hong Kong full-market breadth", "港股全市场广度"),
    "hk_gdelt": _pair("Hong Kong news tone", "港股新闻情绪"),
    "hk_hkexnews": _pair("HK exchange filings", "港交所公告"),
    "hk_indices": _pair("Hong Kong indices", "港股指数"),
    "hk_placements": _pair("HK placements and rights issues", "港股配售与供股"),
    "hk_prices": _pair("Hong Kong market prices", "港股市场价格"),
    "hk_property": _pair("Hong Kong property data", "香港房地产数据"),
    "hk_shorts_positions": _pair("HK short positions", "港股淡仓"),
    "hk_shorts_turnover": _pair("HK short-selling turnover", "港股卖空成交"),
    "hk_southbound_holdings": _pair("Southbound holdings", "南向持股"),
    "hk_stocks": _pair("Hong Kong stock prices", "港股个股价格"),
    "hk_universe": _pair("Hong Kong stock universe", "港股股票池"),
    "hk_valuation": _pair("Hong Kong valuation", "港股估值"),
    "hkma": _pair("HKMA monetary data", "香港金管局货币数据"),
    "holdings": _pair("Thematic ETF holdings", "主题ETF持仓"),
    "huggingface": _pair("AI model activity", "AI模型活跃度"),
    "ibkr_borrow": _pair("Stock borrow rates", "股票借券利率"),
    "imf_weo": _pair("IMF economic outlook", "IMF世界经济展望"),
    "intl_etf": _pair("Country ETF returns", "国家ETF收益"),
    "intl_macro": _pair("International macro data", "国际宏观数据"),
    "intl_prices": _pair("International market prices", "国际市场价格"),
    "intl_universe": _pair("International stock universe", "国际股票池"),
    "intraday_flow_nightly": _pair("Intraday options flow (nightly)", "盘中期权资金流（夜间）"),
    "jodi": _pair("Global oil stocks", "全球石油库存"),
    "kalshi_releases": _pair("Event-market release odds", "事件市场发布预期"),
    "lbnl_queue": _pair("Power interconnection queue", "电力并网排队"),
    "massive_stock_day": _pair("US daily prices", "美股日线价格"),
    "mempool": _pair("Bitcoin mempool", "比特币内存池"),
    "midcap_breadth": _pair("Mid-cap breadth", "中盘股广度"),
    "nyfed": _pair("New York Fed data", "纽约联储数据"),
    "ofac_sdn": _pair("OFAC sanctions list", "OFAC制裁名单"),
    "ofr": _pair("OFR funding monitor", "OFR融资监测"),
    "ofr_fsi": _pair("OFR financial stress index", "OFR金融压力指数"),
    "okx": _pair("Crypto derivatives", "加密衍生品"),
    "openfda": _pair("FDA records", "FDA记录"),
    "openfigi": _pair("Security identifier map", "证券代码映射"),
    "options_flow_creds": _pair("Options flow access", "期权资金流接入"),
    "polygon_gex_accrual": _pair("Options exposure accrual", "期权敞口累积"),
    "polygon_news": _pair("News feed", "新闻流"),
    "prediction_markets": _pair("Prediction markets", "预测市场"),
    "quiver_appratings": _pair("App ratings", "应用评分"),
    "quiver_bills": _pair("Congressional bill summaries", "国会法案摘要"),
    "quiver_cnbc": _pair("TV stock mentions", "电视节目个股提及"),
    "quiver_congress": _pair("Congressional trading", "国会议员交易"),
    "quiver_congressholdings": _pair("Congressional holdings", "国会议员持仓"),
    "quiver_corpdonors": _pair("Corporate political donations", "企业政治捐款"),
    "quiver_flights": _pair("Corporate jet flights", "公司专机航班"),
    "quiver_govcontracts": _pair("Government contracts", "政府合同"),
    "quiver_house": _pair("House trading", "众议院交易"),
    "quiver_insiders": _pair("Insider trading", "内部人交易"),
    "quiver_lobbying": _pair("Lobbying disclosures", "游说披露"),
    "quiver_news": _pair("Alternative news feed", "另类新闻流"),
    "quiver_offexchange": _pair("Off-exchange volume", "场外成交量"),
    "quiver_patents": _pair("Patent filings", "专利申请"),
    "quiver_sec13f": _pair("13F holdings (alternative)", "13F持仓（另类）"),
    "quiver_sec13f_changes": _pair("13F holding changes", "13F持仓变动"),
    "quiver_senate": _pair("Senate trading", "参议院交易"),
    "quiver_spacs": _pair("SPAC tracker", "SPAC追踪"),
    "quiver_trump": _pair("Administration-linked trades", "政府关联交易"),
    "quiver_twitter": _pair("Social follower counts", "社交媒体关注数"),
    "quiver_watchlist": _pair("Alternative data watchlist", "另类数据观察列表"),
    "quiver_wsb": _pair("Retail forum mentions", "散户论坛提及"),
    "rate_futures": _pair("Rate futures policy path", "利率期货政策路径"),
    "russell_breadth": _pair("Broad small-cap breadth", "广义小盘股广度"),
    "sam_gov": _pair("Federal contract notices", "联邦合同公告"),
    "sbir_awards": _pair("SBIR awards", "SBIR资助"),
    "sec_capital_structure": _pair("SEC capital structure", "SEC资本结构"),
    "sec_capital_structure_companyfacts": _pair("SEC capital structure facts", "SEC资本结构事实"),
    "sector_flows": _pair("Sector ETF flows", "行业ETF资金流"),
    "sector_holdings": _pair("Sector ETF holdings", "行业ETF持仓"),
    "sentiment_aaii": _pair("Individual investor survey", "个人投资者调查"),
    "sentiment_naaim": _pair("Active manager exposure survey", "主动管理人仓位调查"),
    "smallcap_breadth": _pair("Small-cap breadth", "小盘股广度"),
    "sovereign": _pair("Sovereign yields", "主权债收益率"),
    "stock_fundamentals": _pair("Stock fundamentals", "个股基本面"),
    "stock_prices": _pair("Sector stock prices", "行业成分股价格"),
    "stocktwits": _pair("Retail social sentiment", "散户社交情绪"),
    "symbol_directory": _pair("Exchange symbol directory", "交易所代码目录"),
    "tape_flow_episodes": _pair("Tape flow episodes", "成交流事件段"),
    "tape_flow_etf-history": _pair("ETF tape flow history", "ETF成交流历史"),
    "tape_flow_forward": _pair("Tape flow forward accrual", "成交流前向累积"),
    "treasury": _pair("Treasury yields", "美债收益率"),
    "treasury_auctions": _pair("Treasury auctions", "美债拍卖"),
    "tsa": _pair("TSA air traveler counts", "TSA航空旅客人数"),
    "uncertainty_indices": _pair("Policy uncertainty indices", "政策不确定性指数"),
    "usaspending": _pair("Federal spending", "联邦支出"),
    "usaspending_awards": _pair("Federal awards", "联邦授予"),
    "usaspending_idv_graph": _pair("Federal contract vehicles", "联邦合同工具"),
    "usaspending_subawards": _pair("Federal subawards", "联邦分包授予"),
    "wiki_pageviews": _pair("Encyclopedia page views", "百科页面浏览量"),
    "wikipedia_btc": _pair("Bitcoin page views", "比特币页面浏览量"),
    "worldbank": _pair("World Bank reserves", "世界银行储备数据"),
    "yahoo": _pair("US quotes", "美股行情"),
}


def label_for(source_id: str) -> dict[str, str]:
    """Return the reviewed ``{"en", "zh"}`` label for a collector id, else :data:`GENERIC`."""
    return LABELS.get(source_id, GENERIC)


def unreviewed_ids(ids: Iterable[str]) -> list[str]:
    """The ids, sorted, that have no reviewed label and so render as :data:`GENERIC`."""
    return sorted(i for i in ids if i not in LABELS)


def _provider_ids(ids: Iterable[str]) -> list[str]:
    named = [i for i in ids if PROVIDER_RE.search(i.replace("_", " ").replace("-", " "))]
    return sorted(named, key=len, reverse=True)


_PROVIDER_ID_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:"
    + "|".join(re.escape(i) for i in _provider_ids(LABELS))
    + r")(?![A-Za-z0-9_])"
)


def neutral_note(text: str) -> str:
    """Strip provider names, hosts and URLs from a health note.

    URLs, ``host=`` arguments and bare domains, in any case, become neutral
    placeholders first, so a provider name inside a host can never leave a
    fragment behind. Then provider-named collector ids become their reviewed
    label, client libraries become "client library" and remaining provider names
    "provider". Callers clip the result, never the raw note, so a clip can't cut
    a host in half before it is scrubbed.
    """
    if not text:
        return ""
    out = _URL_RE.sub("remote file", text)
    out = _HOST_ARG_RE.sub(lambda m: m.group(1) + "=remote", out)
    out = _DOMAIN_RE.sub("remote host", out)
    out = _PROVIDER_ID_RE.sub(lambda m: LABELS[m.group(0)]["en"], out)
    out = _LIBRARY_RE.sub("client library", out)
    out = PROVIDER_RE.sub("provider", out)
    return out

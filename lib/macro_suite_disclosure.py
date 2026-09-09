"""Plain-word composition-law and glance-movement tables for Macro Command.

Every composite on the suite pages must disclose its composition law in
customer words (EN+ZH). Glance movement is a per-axis clause table: a missing
clause is a build defect, never a generic "Moved on".
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from lib.macro_suite_zh_parity import apply_zh_parity

_DIRECTIONS = ("up", "down", "flat")
_ACRONYMS = frozenset({
    "GLT", "US", "CPI", "FRED", "OFR", "NFCI", "HY", "GDP", "ECB", "BOJ",
    "SOFR", "FOMC", "VIX", "HICP", "TIPS", "OECD", "NBER", "BLS", "TGA",
    "USD", "EU", "JP", "CN", "GB", "IG", "NAR", "BEA", "EIA",
})


def _pair(en: str, zh: str) -> dict[str, str]:
    return apply_zh_parity({"en": en, "zh": zh}) or {"en": en, "zh": zh}


# Hand-written glance clauses. Keyed by (axis_id, direction). A missing key
# raises at build time — no "Moved on", no English leaking into ZH.
#
# Authoring rule (one idiom, one casing): every clause is a sentence fragment
# that names its axis; the first word is stored capitalised; clause_case
# lowers a later clause. Do not mix "on X" fragments with bare noun phrases.
# conditions_level / conditions_impulse are internal hysteresis labels in
# financial_conditions.py — they are not published axis_id values and have
# no movement clauses.
AXIS_MOVE_CLAUSES: dict[tuple[str, str], dict[str, str]] = {
    ("funding_pressure", "up"): _pair("Tighter funding pressure", "融资压力上升"),
    ("funding_pressure", "down"): _pair("Easier funding pressure", "融资压力减轻"),
    ("funding_pressure", "flat"): _pair("No change in funding pressure", "融资压力无变化"),
    ("balance_sheet_support", "up"): _pair("Stronger balance-sheet support", "资产负债表支持增强"),
    ("balance_sheet_support", "down"): _pair("Weaker balance-sheet support", "资产负债表支持减弱"),
    ("balance_sheet_support", "flat"): _pair("No change in balance-sheet support", "资产负债表支持无变化"),
    ("financial_conditions_level", "up"): _pair("Tighter funding conditions", "融资条件收紧"),
    ("financial_conditions_level", "down"): _pair("Easier funding conditions", "融资条件放松"),
    ("financial_conditions_level", "flat"): _pair("No change in funding tightness", "融资松紧无变化"),
    ("financial_conditions_impulse", "up"): _pair("Stronger tightening impulse", "收紧脉冲更强"),
    ("financial_conditions_impulse", "down"): _pair("Weaker tightening impulse", "收紧脉冲减弱"),
    ("financial_conditions_impulse", "flat"): _pair("No change in the tightening impulse", "收紧脉冲无变化"),
    ("growth_momentum", "up"): _pair("Stronger growth momentum", "增长动能增强"),
    ("growth_momentum", "down"): _pair("Weaker growth momentum", "增长动能减弱"),
    ("growth_momentum", "flat"): _pair("No change in growth momentum", "增长动能无变化"),
    ("growth_level_breadth", "up"): _pair("Broader breadth", "增长广度扩大"),
    ("growth_level_breadth", "down"): _pair("Narrower breadth", "增长广度收窄"),
    ("growth_level_breadth", "flat"): _pair("No change in growth breadth", "增长广度无变化"),
    ("inflation_impulse", "up"): _pair("Faster price rises", "物价上涨加快"),
    ("inflation_impulse", "down"): _pair("Slower price rises", "物价上涨放缓"),
    ("inflation_impulse", "flat"): _pair("No change in the speed of price rises", "物价上涨速度无变化"),
    ("persistence_breadth", "up"): _pair("Across more categories", "涨价类别增多"),
    ("persistence_breadth", "down"): _pair("Across fewer categories", "涨价类别减少"),
    ("persistence_breadth", "flat"): _pair("No change in how widely prices are rising", "涨价广度无变化"),
    ("labor_demand", "up"): _pair("Stronger employer demand", "用工需求增强"),
    ("labor_demand", "down"): _pair("Weaker employer demand", "用工需求减弱"),
    ("labor_demand", "flat"): _pair("No change in employer demand", "用工需求无变化"),
    ("labor_supply_tightness", "up"): _pair("Tighter job-market conditions", "就业市场更紧"),
    ("labor_supply_tightness", "down"): _pair("Easier job-market conditions", "就业市场更松"),
    ("labor_supply_tightness", "flat"): _pair("No change in job-market tightness", "就业市场松紧无变化"),
    ("cash_flow_momentum", "up"): _pair("Stronger household cash flow", "家庭现金流增强"),
    ("cash_flow_momentum", "down"): _pair("Weaker household cash flow", "家庭现金流减弱"),
    ("cash_flow_momentum", "flat"): _pair("No change in household cash flow", "家庭现金流无变化"),
    ("credit_stress", "up"): _pair("More household credit stress", "家庭信贷压力加大"),
    ("credit_stress", "down"): _pair("Less household credit stress", "家庭信贷压力减轻"),
    ("credit_stress", "flat"): _pair("No change in household credit stress", "家庭信贷压力无变化"),
}

# Composition-law body copy. Keyed by (axis_id, field). Missing raises.
_REVISION_SHARED = _pair(
    "Recomputed each time the source publishes, using only readings that were "
    "already known then. A method change is reported as a break in comparability, "
    "never as a numeric move.",
    "每次数据源发布时用当时已知的读数重算。方法变更会标明为不可比，而不会写成数字位移。",
)

COMPOSITION_LAW: dict[tuple[str, str], dict[str, str]] = {
    ("funding_pressure", "weights_law"): _pair(
        "Weighted average of the parts that are present: Chicago Fed conditions "
        "30%, OFR stress 30%, high-yield spreads 20%, rates-scare 20%. Missing "
        "parts are dropped and the rest are re-weighted.",
        "按到位分项的加权平均：芝加哥联储金融状况 30%、OFR 压力 30%、高收益利差 20%、"
        "利率恐慌 20%。缺项剔除后对其余分项重新加权。",
    ),
    ("funding_pressure", "transformation"): _pair(
        "Percentiles are scaled to 0–100. A z-score is mapped so a 2.5-standard-deviation "
        "move fills half the scale. The rates-scare score is already 0–100 and is used as-is. "
        "Only prior published readings are used.",
        "分位映射到 0–100。z 值按 2.5 个标准差对应半幅刻度。利率恐慌评分已是 0–100，直接采用。"
        "只使用已发布的先验读数。",
    ),
    ("funding_pressure", "frequency_alignment"): _pair(
        "Mixed clocks: Chicago Fed and OFR roughly weekly, high-yield spreads and "
        "rates-scare daily. Each part keeps its own source clock.",
        "时钟不一：芝加哥联储与 OFR 大约每周，高收益利差与利率恐慌为日度。各分项保留自己的来源时钟。",
    ),
    ("balance_sheet_support", "weights_law"): _pair(
        "Weighted average of the parts that are present: support quality 40%, "
        "overlay level 35%, net-liquidity rate of change 25%. Missing parts are "
        "dropped and the rest are re-weighted.",
        "按到位分项的加权平均：支持质量 40%、叠加水平 35%、净流动性变化率 25%。"
        "缺项剔除后对其余分项重新加权。",
    ),
    ("balance_sheet_support", "transformation"): _pair(
        "Quality labels map to support levels from contracting (20) to benign expansion (85). "
        "The net-liquidity rate of change is scaled so a $500bn swing fills half the scale. "
        "An overnight reverse-repo balance at or below $1bn is flagged as an exhausted floor "
        "in the notes; a negative balance is treated as a failed source.",
        "质量标签映射为支持水平，从收缩（20）到良性扩张（85）。净流动性变化率按 5000 亿美元对应半幅刻度。"
        "隔夜逆回购余额不高于 10 亿美元时，在说明中标记为底仓耗尽；负值视为来源失败。",
    ),
    ("balance_sheet_support", "frequency_alignment"): _pair(
        "Weekly Fed balance-sheet cadence (Wednesday data, Thursday release) with a "
        "three-business-day lag. Quality and overlay share that clock.",
        "美联储资产负债表为周度（周三数据、周四发布），并带三个工作日滞后。质量与叠加共用此时钟。",
    ),
    ("financial_conditions_level", "weights_law"): _pair(
        "Weighted average of four channels, re-weighted over those that are present: "
        "rates 30%, credit 30%, dollar funding 20%, equities and volatility 20%. "
        "A fifth declared channel — lending — has no source and carries no weight.",
        "四个渠道的加权平均，按到位渠道重新加权：利率 30%、信贷 30%、美元融资 20%、股票与波动 20%。"
        "第五个已声明渠道（借贷）没有数据源，不计入权重。",
    ),
    ("financial_conditions_level", "transformation"): _pair(
        "Each channel is its own disclosed mix: rates from the 10-year real yield percentile; "
        "credit from high-yield spreads and the Chicago Fed credit slice; dollar funding from "
        "the OFR funding leg; equities from the volatility-regime score and bond-volatility "
        "percentile. Official Chicago Fed and OFR headline indexes are published separately "
        "and are not blended in here. Boundary 50, hold-back band 5 points.",
        "各渠道有各自披露的构成：利率来自 10 年期实际收益率分位；信贷来自高收益利差与芝加哥联储信贷分项；"
        "美元融资来自 OFR 融资分项；股票来自波动体制评分与债券波动分位。官方芝加哥联储与 OFR 综合指数另行发布，"
        "不在此混合。分界 50，滞回带 5 点。",
    ),
    ("financial_conditions_level", "frequency_alignment"): _pair(
        "Mixed clocks: daily real yields and volatility, roughly weekly credit and OFR funding. "
        "Each channel keeps its own source clock.",
        "时钟不一：实际收益率与波动为日度，信贷与 OFR 融资大约每周。各渠道保留自己的来源时钟。",
    ),
    ("financial_conditions_impulse", "weights_law"): _pair(
        "Weighted average of three momentum legs, re-weighted over those that are present: "
        "13-week Chicago Fed change 35%, 13-week OFR change 35%, 63-day real-yield change 30%. "
        "At least two legs must be present.",
        "三个动量分项的加权平均，按到位分项重新加权：芝加哥联储 13 周变化 35%、OFR 13 周变化 35%、"
        "实际收益率 63 日变化 30%。至少两个分项必须到位。",
    ),
    ("financial_conditions_impulse", "transformation"): _pair(
        "Each leg is a rate of change, not a level: Chicago Fed scaled to a 0.5-point half-swing, "
        "OFR to a 1.0-point half-swing, real yields to a 50-basis-point half-swing. A positive "
        "move is a tightening impulse. Boundary 50, hold-back band 5 points.",
        "各分项是变化率而非水平：芝加哥联储按 0.5 点对应半幅，OFR 按 1.0 点，实际收益率按 50 个基点。"
        "正值表示收紧脉冲。分界 50，滞回带 5 点。",
    ),
    ("financial_conditions_impulse", "frequency_alignment"): _pair(
        "13-week windows on the weekly Chicago Fed and OFR prints, and a 63-day window on "
        "the daily real yield.",
        "芝加哥联储与 OFR 的周度读数用 13 周窗口，日度实际收益率用 63 日窗口。",
    ),
    ("growth_momentum", "weights_law"): _pair(
        "Weighted average of the parts that are present: Atlanta Fed nowcast 35%, "
        "weekly economic index 30%, leading-tier momentum 20%, current-activity momentum 15%.",
        "按到位分项的加权平均：亚特兰大联储即时预测 35%、周度经济指数 30%、"
        "领先动能 20%、当前活动动能 15%。",
    ),
    ("growth_momentum", "transformation"): _pair(
        "Nowcast and weekly index are centred (2.0% and 1.5% annualised) and scaled so a "
        "4-point swing fills half the scale. Leading and current-activity momentum are "
        "centred at zero with a 2-point half-swing. Only prior published readings are used.",
        "即时预测与周度指数以年化 2.0% 与 1.5% 为中心，4 个点对应半幅刻度。"
        "领先与当前活动动能以 0 为中心、2 个点为半幅。只使用已发布的先验读数。",
    ),
    ("growth_momentum", "frequency_alignment"): _pair(
        "Mixed clocks: the nowcast updates near-daily inside the quarter, the weekly index "
        "on Fridays, and the activity tiers monthly with each leg's own publication lag.",
        "时钟不一：季内即时预测接近日更，周度指数周五发布，活动分层为月度并带各分项自身的发布滞后。",
    ),
    ("growth_level_breadth", "weights_law"): _pair(
        "Weighted average of the parts that are present: leading diffusion 30%, "
        "current-activity diffusion 35%, current-activity index level 20%, growth score 15%. "
        "The lagging tier is left out on purpose and published separately as confirmation.",
        "按到位分项的加权平均：领先扩散 30%、当前活动扩散 35%、当前活动指数水平 20%、增长评分 15%。"
        "滞后层有意排除，另行作为确认项发布。",
    ),
    ("growth_level_breadth", "transformation"): _pair(
        "Diffusion and the current-activity index are already 0–100 and pass through. "
        "The growth score is centred at zero with a 1-point half-swing.",
        "扩散与当前活动指数已是 0–100，直接采用。增长评分以 0 为中心、1 个点为半幅。",
    ),
    ("growth_level_breadth", "frequency_alignment"): _pair(
        "Monthly activity-tier clocks with each leg's publication lag. The growth score "
        "shares the regime-read cadence.",
        "活动分层为月度，并带各分项发布滞后。增长评分与体制读数同一节奏。",
    ),
    ("inflation_impulse", "weights_law"): _pair(
        "Weighted average of the parts that are present: core CPI, 3-month annualised, "
        "35%; headline CPI, 3-month annualised, 20%; core CPI year over year 20%; "
        "current-month core nowcast, annualised, 25%.",
        "按到位分项的加权平均：核心 CPI 三个月年化 35%、总体 CPI 三个月年化 20%、"
        "核心 CPI 同比 20%、当月核心即时预测（年化）25%。",
    ),
    ("inflation_impulse", "transformation"): _pair(
        "Each percent reading is centred on the Fed 2 percent objective and scaled so a "
        "4-point gap fills half the scale, then clamped to 0–100. The nowcast leg "
        "compounds one monthly point into an annualised rate before the same mapping.",
        "各百分比读数以美联储 2% 目标为中心，4 个点对应半幅刻度，并限制在 0–100。"
        "即时预测分项先把一个月度点折成年化，再做同样映射。",
    ),
    ("inflation_impulse", "frequency_alignment"): _pair(
        "Monthly CPI-family release, one to two months lagged per the source's own "
        "freshness rule. The current-month nowcast is a faster intra-month clock and "
        "is marked simulated, never current.",
        "CPI 族月度发布，按来源自身新鲜度规则滞后一到两个月。当月即时预测是更快的月内时钟，"
        "标记为模拟而非当前。",
    ),
    ("persistence_breadth", "weights_law"): _pair(
        "Weighted average of the parts that are present: sticky-minus-flexible "
        "3-month annualised spread 35%; core 3-month versus 6-month acceleration 25%; "
        "sticky-price 3-month versus 6-month acceleration 20%; core-minus-headline "
        "year-over-year gap 20%.",
        "按到位分项的加权平均：黏性减灵活的三个月年化差 35%、核心三个月相对六个月加速 25%、"
        "黏性价格三个月相对六个月加速 20%、核心减总体的同比缺口 20%。",
    ),
    ("persistence_breadth", "transformation"): _pair(
        "Each spread is the difference of two already-published numbers, mapped onto "
        "0–100 around a zero centre. The sticky-flexible spread uses a 6-point "
        "half-swing; the two acceleration legs use 2 points; the core-headline gap "
        "uses 3 points.",
        "每个差额都是两个已发布数字之差，以 0 为中心映射到 0–100。黏性与灵活之差按 6 个点为半幅；"
        "两个加速分项按 2 个点；核心与总体缺口按 3 个点。",
    ),
    ("persistence_breadth", "frequency_alignment"): _pair(
        "The same monthly CPI-family cadence and publication lag as the impulse axis. "
        "All four legs share the released-state clock.",
        "与冲量轴相同的 CPI 族月度节奏与发布滞后。四个分项共用已发布状态时钟。",
    ),
    ("labor_demand", "weights_law"): _pair(
        "Weighted average of the parts that are present: initial-claims momentum 40%, "
        "job-postings momentum 35%, withheld-tax income-growth proxy 25%.",
        "按到位分项的加权平均：初请动量 40%、职位发布动量 35%、代扣税收入增长代理 25%。",
    ),
    ("labor_demand", "transformation"): _pair(
        "Claims are inverted so elevated claims read as weaker demand. Job-postings "
        "3-month change and withheld-tax year-over-year growth map onto 0–100. Only "
        "prior published readings are used.",
        "初请取反，初请升高表示需求更弱。职位发布三个月变化与代扣税同比映射到 0–100。"
        "只使用已发布的先验读数。",
    ),
    ("labor_demand", "frequency_alignment"): _pair(
        "Mixed clocks: weekly initial claims (Thursday), weekly job-postings, and a "
        "daily-accrual Treasury withheld-tax proxy, all aligned to one shared "
        "calculation date.",
        "时钟不一：周度初请（周四）、周度职位发布，以及按日累计的财政部代扣税代理，"
        "全部对齐到同一个计算日。",
    ),
    ("labor_supply_tightness", "weights_law"): _pair(
        "Weighted average of the parts that are present: Sahm-rule level 55%, "
        "claims-based recession subscore 45%.",
        "按到位分项的加权平均：萨姆规则水平 55%、基于初请的衰退子评分 45%。",
    ),
    ("labor_supply_tightness", "transformation"): _pair(
        "The Sahm rule is inverted against its 0.5-point recession trigger so a "
        "lower Sahm reads as a tighter market. The claims recession subscore is "
        "inverted the same way. Both land on 0–100.",
        "萨姆规则相对 0.5 点衰退触发值取反，萨姆越低表示市场越紧。初请衰退子评分同样取反。两者均落到 0–100。",
    ),
    ("labor_supply_tightness", "frequency_alignment"): _pair(
        "Monthly unemployment (first Friday) for the Sahm rule, and the weekly "
        "claims clock for the recession subscore — two native cadences under one axis.",
        "萨姆规则用月度失业率（第一个周五），衰退子评分用周度初请 — 同一轴下两种原生节奏。",
    ),
    ("cash_flow_momentum", "weights_law"): _pair(
        "Equal weighted average of two required parts: retail sales, year over year, "
        "and real disposable income, year over year. Both must be present.",
        "两个必到分项的等权平均：零售销售同比，以及实际可支配收入同比。两项都必须到位。",
    ),
    ("cash_flow_momentum", "transformation"): _pair(
        "Year-over-year percent changes are mapped onto 0–100 so a faster rise "
        "reads higher. Only prior published prints are used; nothing is estimated "
        "inside this page.",
        "同比百分比变化映射到 0–100，上升越快读数越高。只使用已发布读数，本页不做估算。",
    ),
    ("cash_flow_momentum", "frequency_alignment"): _pair(
        "Both legs are monthly. Retail sales arrive about mid-month for the prior "
        "month; disposable income arrives at month-end.",
        "两个分项均为月度。零售销售约在次月中发布，可支配收入在月末发布。",
    ),
    ("credit_stress", "weights_law"): _pair(
        "Weighted average of the parts that are present (at least two of four): "
        "revolving credit, year over year, 30%; saving rate (inverted) 25%; "
        "credit-card delinquency 25%; mortgage delinquency 20%.",
        "按到位分项的加权平均（四项中至少两项）：循环信贷同比 30%、储蓄率（取反）25%、"
        "信用卡拖欠 25%、房贷拖欠 20%。",
    ),
    ("credit_stress", "transformation"): _pair(
        "Revolving-credit growth maps onto 0–100. The saving rate is inverted around "
        "a disclosed neutral so a lower saving rate reads as more stress. Delinquency "
        "rates map linearly between disclosed floor and ceiling anchors.",
        "循环信贷增长映射到 0–100。储蓄率围绕已披露的中性水平取反，储蓄率越低压力越大。"
        "拖欠率在已披露的上下锚点之间线性映射。",
    ),
    ("credit_stress", "frequency_alignment"): _pair(
        "Mixed clocks: revolving credit about two months lagged, saving rate monthly "
        "at month-end, delinquency quarterly about seventy days after quarter-end.",
        "时钟不一：循环信贷大约滞后两个月，储蓄率为月末月度，拖欠率为季后约七十天的季度数据。",
    ),
}

for _axis_id in {
    "funding_pressure", "balance_sheet_support",
    "financial_conditions_level", "financial_conditions_impulse",
    "growth_momentum", "growth_level_breadth",
    "inflation_impulse", "persistence_breadth",
    "labor_demand", "labor_supply_tightness",
    "cash_flow_momentum", "credit_stress",
}:
    COMPOSITION_LAW[(_axis_id, "revision_behavior")] = dict(_REVISION_SHARED)


FRED_SERIES: dict[str, dict[str, str]] = {
    "BOPGSTB": _pair("US trade balance (FRED)", "美国贸易差额（FRED）"),
    "BOPTEXP": _pair("US exports (FRED)", "美国出口（FRED）"),
    "BOPTIMP": _pair("US imports (FRED)", "美国进口（FRED）"),
    "CSUSHPISA": _pair("National house prices (FRED)", "全国房价（FRED）"),
    "DFII10": _pair("10-year real yield (FRED)", "10年期实际收益率（FRED）"),
    "DFII5": _pair("5-year real yield (FRED)", "5年期实际收益率（FRED）"),
    "DGS1": _pair("1-year Treasury yield (FRED)", "1年期美债收益率（FRED）"),
    "DGS10": _pair("10-year Treasury yield (FRED)", "10年期美债收益率（FRED）"),
    "DGS2": _pair("2-year Treasury yield (FRED)", "2年期美债收益率（FRED）"),
    "DGS20": _pair("20-year Treasury yield (FRED)", "20年期美债收益率（FRED）"),
    "DGS3": _pair("3-year Treasury yield (FRED)", "3年期美债收益率（FRED）"),
    "DGS30": _pair("30-year Treasury yield (FRED)", "30年期美债收益率（FRED）"),
    "DGS3MO": _pair("3-month Treasury yield (FRED)", "3个月美债收益率（FRED）"),
    "DGS5": _pair("5-year Treasury yield (FRED)", "5年期美债收益率（FRED）"),
    "DGS6MO": _pair("6-month Treasury yield (FRED)", "6个月美债收益率（FRED）"),
    "DGS7": _pair("7-year Treasury yield (FRED)", "7年期美债收益率（FRED）"),
    "DRCCLACBS": _pair("Credit-card delinquency (FRED)", "信用卡拖欠（FRED）"),
    "DRSFRMACBS": _pair("Mortgage delinquency (FRED)", "房贷拖欠（FRED）"),
    "DSPIC96": _pair("Real disposable income (FRED)", "实际可支配收入（FRED）"),
    "EFFR": _pair("Effective federal funds rate (FRED)", "有效联邦基金利率（FRED）"),
    "HOUST": _pair("Housing starts (FRED)", "新屋开工（FRED）"),
    "IORB": _pair("Interest on reserves (FRED)", "准备金利息（FRED）"),
    "IQ": _pair("Export price index (FRED)", "出口价格指数（FRED）"),
    "IR": _pair("Import price index (FRED)", "进口价格指数（FRED）"),
    "MORTGAGE30US": _pair("30-year mortgage rate (FRED)", "30年期房贷利率（FRED）"),
    "NONREVSL": _pair("Non-revolving credit (FRED)", "非循环信贷（FRED）"),
    "OBFR": _pair("Overnight bank funding rate (FRED)", "隔夜银行融资利率（FRED）"),
    "PERMIT": _pair("Building permits (FRED)", "营建许可（FRED）"),
    "PSAVERT": _pair("Personal saving rate (FRED)", "个人储蓄率（FRED）"),
    "REVOLSL": _pair("Revolving credit (FRED)", "循环信贷（FRED）"),
    "RSAFS": _pair("US retail sales (FRED)", "美国零售销售（FRED）"),
    "SOFR": _pair("SOFR (FRED)", "SOFR（FRED）"),
    "T10YIE": _pair("10-year inflation break-even (FRED)", "10年期通胀盈亏平衡（FRED）"),
    "T5YIFR": _pair("5-year, 5-year forward inflation (FRED)", "5年后再5年远期通胀（FRED）"),
    "THREEFYTP10": _pair("10-year term premium (FRED)", "10年期期限溢价（FRED）"),
    "TOTALSL": _pair("Total consumer credit (FRED)", "消费者信贷总额（FRED）"),
    "UMCSENT": _pair("Michigan consumer sentiment (FRED)", "密歇根消费者信心（FRED）"),
}

OWNER_DISPLAY: dict[str, dict[str, str]] = {
    "N/A": _pair("Not applicable", "不适用"),
    "engine.axes": _pair("Growth-score desk", "增长评分小组"),
    "engine.business_cycle": _pair("Business-cycle desk", "商业周期小组"),
    "engine.business_cycle (blended; not separately published)": _pair(
        "Business-cycle desk (blended read)", "商业周期小组（混合读数）"),
    "engine.business_cycle (no survey collector)": _pair(
        "Business-cycle desk (no survey feed)", "商业周期小组（无调查接入）"),
    "engine.capital_structure_event_projection": _pair(
        "Capital-structure event desk", "资本结构事件小组"),
    "engine.cb_desk": _pair("Central-bank policy desk", "央行政策小组"),
    "engine.cb_desk[BOJ]": _pair("Bank of Japan desk", "日本银行小组"),
    "engine.cb_desk[ECB]": _pair("European Central Bank desk", "欧洲央行小组"),
    "engine.cb_desk[FED]": _pair("Federal Reserve policy desk", "美联储政策小组"),
    "engine.conditions.financial_conditions": _pair(
        "Financial-conditions desk", "金融条件小组"),
    "engine.conditions.growth_nowcast": _pair("Growth-nowcast desk", "增长即时预测小组"),
    "engine.conditions.labor_nowcast": _pair("Labor-nowcast desk", "劳动力即时预测小组"),
    "engine.conditions.recession": _pair("Recession-nowcast desk", "衰退即时预测小组"),
    "engine.conditions.systemic_stress": _pair("Systemic-stress desk", "系统性压力小组"),
    "engine.global_liquidity_transmission": _pair(
        "Global-liquidity desk", "全球流动性小组"),
    "engine.inflation_intelligence.current_month_proxy_pressure": _pair(
        "Current-month inflation-proxy desk", "当月通胀代理小组"),
    "engine.inflation_intelligence.released_state": _pair(
        "Released inflation-state desk", "已发布通胀状态小组"),
    "engine.inflation_intelligence.released_state.core": _pair(
        "Core inflation-state desk", "核心通胀状态小组"),
    "engine.inflation_intelligence.released_state.headline": _pair(
        "Headline inflation-state desk", "总体通胀状态小组"),
    "engine.inflation_intelligence.released_state.underlying_proxies": _pair(
        "Underlying inflation-proxy desk", "潜在通胀代理小组"),
    "engine.inflation_intelligence.released_state.underlying_proxies.flexible": _pair(
        "Flexible-price inflation desk", "灵活价格通胀小组"),
    "engine.inflation_intelligence.released_state.underlying_proxies.sticky": _pair(
        "Sticky-price inflation desk", "黏性价格通胀小组"),
    "engine.market_os.macro_workspaces.consumer_payments": _pair(
        "Consumer-payments desk", "消费支付小组"),
    "engine.market_os.macro_workspaces.financial_conditions": _pair(
        "Financial-conditions workspace", "金融条件工作区"),
    "engine.market_os.macro_workspaces.growth": _pair(
        "Growth workspace", "增长工作区"),
    "engine.market_os.macro_workspaces.inflation": _pair(
        "Inflation workspace", "通胀工作区"),
    "engine.market_os.macro_workspaces.labor": _pair(
        "Labor-markets workspace", "劳动力市场工作区"),
    "engine.market_os.macro_workspaces.liquidity_regime": _pair(
        "Liquidity-regime workspace", "流动性体制工作区"),
    "engine.rate_inflation_transmission": _pair(
        "Rate-to-inflation desk", "利率到通胀传导小组"),
    "engine.rates_inflation_command": _pair(
        "Rates-and-inflation command desk", "利率与通胀指挥小组"),
    "engine.regime.labor_nowcast": _pair("Labor-nowcast regime desk", "劳动力即时预测体制小组"),
    "engine.regime.liquidity_overlay": _pair("Liquidity-overlay desk", "流动性叠加小组"),
    "engine.regime.liquidity_quality": _pair("Liquidity-quality desk", "流动性质量小组"),
    "engine.regime.recession": _pair("Recession-regime desk", "衰退体制小组"),
    "engine.regime.regime_vector": _pair("Regime-vector desk", "体制向量小组"),
    "engine.risk_state": _pair("Risk-state desk", "风险状态小组"),
    "engine.sector_rate_inflation.rate_inflation_transmission": _pair(
        "Sector rate-to-inflation desk", "行业利率到通胀小组"),
    "engine.vol_regime": _pair("Volatility-regime desk", "波动体制小组"),
    "engine.inflation_intelligence.next_release_forecast": _pair(
        "Next-release inflation forecast desk", "下次通胀发布预测小组"),
    "collectors.treasury_auctions": _pair("Treasury auction collector", "财政部拍卖采集器"),
    "scripts.build_bonds": _pair("Government-bond build", "国债构建"),
    "scripts.collect_redfin_hf": _pair("House-listing collector", "房源采集"),
    "scripts.collect_zori": _pair("National rent collector", "全国租金采集"),
    "data/bonds/latest.json": _pair("Government-bond desk snapshot", "国债交易台快照"),
    "data/bis/us_dsr.parquet": _pair("BIS household debt-service ratio", "国际清算银行家庭偿债比率"),
    "data/bis/us_gap.parquet": _pair("BIS credit-gap reading", "国际清算银行信贷缺口"),
    "data/treasury/net_issuance.parquet": _pair("Treasury net issuance", "财政部净发行"),
    "data/treasury/tga.parquet": _pair("Treasury cash balance", "财政部现金余额"),
    "data/treasury/withheld_taxes.parquet": _pair("Treasury withheld taxes", "财政部代扣税"),
    "data/treasury_auctions/auctions.parquet": _pair("Treasury auction results", "财政部拍卖结果"),
    "data/zori/national.parquet": _pair("National rent index", "全国租金指数"),
    "fred.BOPGSTB - (fred.BOPTEXP - fred.BOPTIMP)": _pair(
        "Trade-balance identity (exports minus imports)", "贸易差额恒等（出口减进口）"),
    "fred.BOPGSTB / (fred.BOPTEXP + fred.BOPTIMP)": _pair(
        "Trade-balance share of total trade", "贸易差额占总贸易比重"),
    "fred.BOPTEXP / fred.BOPTIMP": _pair(
        "Export-to-import coverage", "出口对进口覆盖"),
    "fred.IQ / fred.IR": _pair("Terms-of-trade proxy (export over import prices)", "贸易条件代理（出口/进口价格）"),
}

METHOD_VERSION_NAME: dict[str, dict[str, str]] = {
    "business_activity.compose.v1": _pair("Business-activity method v1", "商业活动方法第1版"),
    "capital_structure.compose.v1": _pair("Capital-structure method v1", "资本结构方法第1版"),
    "consumer_payments.compose.v1": _pair("Consumer-payments method v1", "消费支付方法第1版"),
    "financial_conditions.compose.v1": _pair("Financial-conditions method v1", "金融条件方法第1版"),
    "growth_real_economy.compose.v1": _pair("Growth method v1", "增长方法第1版"),
    "housing_real_estate.compose.v1": _pair("Housing method v1", "住房方法第1版"),
    "inflation_system.compose.v1": _pair("Inflation method v1", "通胀方法第1版"),
    "labor_markets.compose.v1": _pair("Labor-markets method v1", "劳动力市场方法第1版"),
    "liquidity_central_banks.compose.v1": _pair("Central-bank liquidity method v1", "央行流动性方法第1版"),
    "liquidity_regime.compose.v1": _pair("Liquidity-regime method v1", "流动性体制方法第1版"),
    "monetary_policy.compose.v1": _pair("Monetary-policy method v1", "货币政策方法第1版"),
    "national_debt_liabilities.compose.v1": _pair("National-debt method v1", "国债方法第1版"),
    "rates_curves.compose.v1": _pair("Rates-and-curves method v1", "利率与曲线方法第1版"),
    "trade_flows.compose.v1": _pair("Trade-flows method v1", "贸易流动方法第1版"),
}

AUTHORITY_CEILING: dict[str, dict[str, str]] = {
    "DESCRIPTIVE": _pair(
        "Descriptive reading — this page cannot rank, size or trigger a trade",
        "描述性读数 — 本页不能排名、定仓或触发交易",
    ),
}

_FRED_FILE_RE = re.compile(r"data/fred/([A-Z0-9]+)\.parquet$")
_COLLECTOR_FRED_RE = re.compile(r"^collectors\.fred\[([A-Z0-9]+)\]$")
_COLLECTOR_TREASURY_RE = re.compile(r"^collectors\.treasury\[(\w+)\]$")
_COLLECTOR_BIS_RE = re.compile(r"^collectors\.bis\[(\w+)\]$")
_FINGERPRINT_HEAD_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_]*)(?::|$)")
_NONE_RE = re.compile(r"^NONE\b")

_TREASURY_LEGS = {
    "net_issuance": _pair("Treasury net issuance", "财政部净发行"),
    "tga": _pair("Treasury cash balance", "财政部现金余额"),
    "withheld_taxes": _pair("Treasury withheld taxes", "财政部代扣税"),
}
_BIS_LEGS = {
    "us_dsr": _pair("BIS household debt-service ratio", "国际清算银行家庭偿债比率"),
    "us_gap": _pair("BIS credit-gap reading", "国际清算银行信贷缺口"),
}


def owner_display_pair(ref: Any) -> dict[str, str] | None:
    """Owner or source ref as a customer name. Never a path or slug."""
    if ref is None:
        return None
    text = str(ref).strip()
    if not text:
        return None
    found = OWNER_DISPLAY.get(text)
    if found:
        return dict(found)
    if _NONE_RE.match(text) or text == "N/A":
        return _pair("No source is wired for this reading", "该项尚未接入数据源")
    if " + " in text:
        parts = [owner_display_pair(part.strip()) for part in text.split(" + ")]
        parts = [part for part in parts if part]
        if parts:
            return _pair(
                " and ".join(part["en"] for part in parts),
                "与".join(part["zh"] for part in parts),
            )
    match = _FRED_FILE_RE.match(text) or _COLLECTOR_FRED_RE.match(text)
    if match:
        series = FRED_SERIES.get(match.group(1))
        if series:
            return dict(series)
        return _pair(
            f"FRED published series {match.group(1)}",
            f"FRED 已发布序列 {match.group(1)}",
        )
    match = _COLLECTOR_TREASURY_RE.match(text)
    if match and match.group(1) in _TREASURY_LEGS:
        return dict(_TREASURY_LEGS[match.group(1)])
    match = _COLLECTOR_BIS_RE.match(text)
    if match and match.group(1) in _BIS_LEGS:
        return dict(_BIS_LEGS[match.group(1)])
    head = _FINGERPRINT_HEAD_RE.match(text)
    if head:
        from lib.macro_suite_labels import METRIC
        metric = METRIC.get(head.group(1))
        if metric:
            return dict(metric)
    print(
        f"::warning title=macro-suite-unmapped-owner::no customer name for owner_ref {text!r}",
        flush=True,
    )
    return _pair("Source owner not yet named", "数据来源负责人待定")


def composition_law_pair(axis_id: Any, field: str, raw: Any) -> dict[str, str]:
    """Reviewed composition-law sentence. Missing clause raises."""
    key = (str(axis_id or ""), field)
    found = COMPOSITION_LAW.get(key)
    if found is None:
        raise KeyError(
            f"no composition-law clause for axis {axis_id!r} field {field!r}"
        )
    return dict(found)


def definition_version_pair(version: Any, published_iso: Any) -> dict[str, str] | None:
    if version is None or version == "":
        return None
    text = str(version).strip()
    major = text.split(".")[0] if text else text
    if major.isdigit():
        label_en = f"Definition v{major}"
        label_zh = f"定义第{major}版"
    else:
        label_en = f"Definition {text}"
        label_zh = f"定义 {text}"
    from lib.macro_suite_labels import date_display_pair
    dated = date_display_pair(str(published_iso) if published_iso else "")
    if dated:
        return _pair(
            f"{label_en}, published {dated['en']}",
            f"{label_zh}，发布于{dated['zh']}",
        )
    return _pair(label_en, label_zh)


def method_version_pair(token: Any, published_iso: Any) -> dict[str, str] | None:
    if not token:
        return None
    name = METHOD_VERSION_NAME.get(str(token))
    if name is None:
        raise KeyError(f"no dated label for method_version {token!r}")
    from lib.macro_suite_labels import date_display_pair
    dated = date_display_pair(str(published_iso) if published_iso else "")
    if dated:
        return _pair(
            f"{name['en']}, published {dated['en']}",
            f"{name['zh']}，发布于{dated['zh']}",
        )
    return dict(name)


def authority_ceiling_pair(token: Any) -> dict[str, str] | None:
    if token is None or token == "":
        return None
    found = AUTHORITY_CEILING.get(str(token))
    if found is None:
        raise KeyError(f"no customer label for authority_ceiling {token!r}")
    return dict(found)


def coverage_floor_pair(ratio: Any) -> dict[str, str] | None:
    from lib.macro_suite_labels import fmt_ratio_pct
    pct = fmt_ratio_pct(ratio) if not isinstance(ratio, str) else ratio
    if not pct:
        return None
    return _pair(
        f"At least {pct} of the parts must be present",
        f"至少 {pct} 的分项必须到位",
    )


def hysteresis_note_pair(hysteresis: Mapping[str, Any] | None) -> dict[str, str]:
    block = hysteresis or {}
    held = bool(block.get("held_prior"))
    from lib.macro_suite_labels import fmt_number
    raw_band = block.get("band")
    try:
        band_n = float(raw_band) if raw_band is not None else None
    except (TypeError, ValueError):
        band_n = None
    configured = band_n is not None and band_n > 0
    band = fmt_number(raw_band) if configured else None
    note_l = str(block.get("note") or "").lower()
    # Producer "prior quadrant not held … moved beyond the band" means a real flip.
    crossed_beyond = (
        "prior quadrant not held" in note_l
        or "moved beyond" in note_l
        or "transition to the raw quadrant is accepted" in note_l
    )
    if not configured:
        return _pair(
            "No hold-back band is configured on this reading.",
            "本读数未配置滞回带。",
        )
    if held and band:
        return _pair(
            f"A {band}-point hold-back band kept this reading on the prior side of the line.",
            f"{band} 点的滞回带使本读数留在原分界一侧。",
        )
    if crossed_beyond and band:
        return _pair(
            f"A {band}-point hold-back band is in use; this reading did not stay on the prior side of the line.",
            f"已启用 {band} 点滞回带；本读数未留在原分界一侧。",
        )
    # applied=False (no prior) OR applied but not engaged (raw already matched).
    return _pair(
        f"A {band}-point hold-back band is configured but was not needed this reading.",
        f"已配置 {band} 点滞回带，但本读数未用到。",
    )


def changed_sources_pair(fingerprints: Sequence[Any] | None) -> dict[str, str] | None:
    names: list[dict[str, str]] = []
    for item in fingerprints or []:
        pair = owner_display_pair(item)
        if pair:
            names.append(pair)
    if not names:
        return None
    return _pair(
        ", ".join(part["en"] for part in names),
        "、".join(part["zh"] for part in names),
    )


# Producer kinds enumerated from engine/market_os/macro_workspaces/*._corrections.
# Distinguishing fact is the customer-visible phrase that must appear in EN.
# `source_swap` was removed: no producer emits it (verified by
# test_producer_lineage_notes_map_to_real_kinds). Do not re-add without a producer.
LINEAGE_NOTE_KIND_SENTENCES: dict[str, dict[str, str]] = {
    "no_change_republication": _pair(
        "Same reference period as the predecessor print; no source value changed (no-change republication).",
        "与上一期读数同一参考期；源值未变（无变更再发布）。",
    ),
    "value_correction": _pair(
        "Same reference period as the predecessor print; a source value changed, so this print replaces the prior one.",
        "与上一期读数同一参考期；源值已变，本期取代上一期。",
    ),
    "reference_period_change": _pair(
        "This is a new observation for a later reference period, not a revision of the prior print.",
        "这是较晚参考期的新观察，不是对上一期读数的修订。",
    ),
    "first_known": _pair(
        "This is the first published print; no predecessor is on file yet.",
        "这是首次发布的读数；尚无上一期存档。",
    ),
}

LINEAGE_NOTE_KIND_FACTS: dict[str, str] = {
    "no_change_republication": "no-change republication",
    "value_correction": "replaces the prior one",
    "reference_period_change": "later reference period",
    "first_known": "first published print",
}

_LINEAGE_KIND_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("value_correction", (
        "supersedes the prior one as a revision",
        "changed value: this print supersedes",
        "source values changed",
        "metrics changed value",
        "owner-native metrics changed value",
        "source components changed value",
        "tier fields changed value",
    )),
    ("no_change_republication", (
        "no-change republication",
        "no source value changed",
        "no source component changed",
        "no tracked metric changed",
        "no tracked tier field changed",
    )),
    ("reference_period_change", (
        "reference period differs",
        "new observation, not a revision",
    )),
    ("first_known", (
        "first-known snapshot",
        "predecessor recorded when a prior accepted print exists",
    )),
)


def classify_lineage_kind(note: Any) -> str:
    """Map a producer note to a kind. Unknown notes raise (tests pin this)."""
    text = str(note or "").strip().lower()
    if not text:
        raise KeyError("empty lineage note has no kind")
    for kind, markers in _LINEAGE_KIND_MARKERS:
        if any(marker in text for marker in markers):
            return kind
    raise KeyError(f"unknown lineage note kind for {note!r}")


def _period_clause(effective_date: Any, prior_effective_date: Any) -> dict[str, str] | None:
    from lib.macro_suite_labels import date_display_pair
    dated = date_display_pair(str(effective_date) if effective_date else "")
    prior = date_display_pair(str(prior_effective_date) if prior_effective_date else "")
    if dated and prior:
        if dated["en"] == prior["en"] and dated["zh"] == prior["zh"]:
            return _pair(
                f" Both as of {dated['en']}.",
                f"两期均截至{dated['zh']}。",
            )
        return _pair(
            f" This print is as of {dated['en']}; the predecessor is as of {prior['en']}.",
            f"本期截至{dated['zh']}；上一期截至{prior['zh']}。",
        )
    if dated:
        return _pair(
            f" This print is as of {dated['en']}.",
            f"本期截至{dated['zh']}。",
        )
    if prior:
        return _pair(
            f" The predecessor is as of {prior['en']}.",
            f"上一期截至{prior['zh']}。",
        )
    return None


def lineage_note_pair(
    note: Any,
    *,
    effective_date: Any = None,
    prior_effective_date: Any = None,
) -> dict[str, str] | None:
    if not note or not str(note).strip():
        return None
    text = str(note).strip()
    period = _period_clause(effective_date, prior_effective_date)
    try:
        kind = classify_lineage_kind(text)
    except KeyError:
        print(
            f"::warning title=macro-suite-unknown-lineage-kind::unknown lineage note {text!r}",
            flush=True,
        )
        # Typed plain-word fallback: names that classification failed, keeps
        # the note's date/period, never reuses the old "correction on file" constant.
        from lib.macro_suite_labels import date_display_pair
        dated = date_display_pair(str(effective_date) if effective_date else "")
        prior = date_display_pair(str(prior_effective_date) if prior_effective_date else "")
        if dated and prior and dated["en"] == prior["en"]:
            fallback_en = (
                f"This page cannot summarise the correction note yet "
                f"(both as of {dated['en']})."
            )
            fallback_zh = f"本页尚无法概括该更正说明（两期均截至{dated['zh']}）。"
        elif dated:
            fallback_en = (
                f"This page cannot summarise the correction note yet "
                f"(as of {dated['en']})."
            )
            fallback_zh = f"本页尚无法概括该更正说明（截至{dated['zh']}）。"
        else:
            fallback_en = "This page cannot summarise the correction note yet."
            fallback_zh = "本页尚无法概括该更正说明。"
        return _pair(fallback_en, fallback_zh)
    sentence = dict(LINEAGE_NOTE_KIND_SENTENCES[kind])
    if period:
        return _pair(sentence["en"] + period["en"], sentence["zh"] + period["zh"])
    return sentence


def _first_word(text: str) -> str:
    return (text.split() or [""])[0].rstrip(".,;:")


def clause_case(text: str, *, first: bool) -> str:
    """Capitalise the first clause; later clauses start lower unless an acronym."""
    if not text:
        return text
    lead = _first_word(text)
    if lead.upper() in _ACRONYMS:
        return text
    if first:
        return text[0].upper() + text[1:] if text[0].islower() else text
    return text[0].lower() + text[1:] if text[0].isupper() else text


def _direction_token(value: Any) -> str:
    if value is None:
        return "flat"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "flat"
    if number != number:
        return "flat"
    if abs(number) < 1e-12:
        return "flat"
    return "up" if number > 0 else "down"


def axis_move_clause(axis_id: str, direction: str) -> dict[str, str]:
    if direction not in _DIRECTIONS:
        raise KeyError(f"unknown movement direction {direction!r} for axis {axis_id!r}")
    found = AXIS_MOVE_CLAUSES.get((axis_id, direction))
    if found is None:
        raise KeyError(f"no movement clause for axis {axis_id!r} direction {direction!r}")
    return dict(found)


def required_axis_ids() -> tuple[str, ...]:
    return tuple(sorted({axis_id for axis_id, _direction in AXIS_MOVE_CLAUSES}))


def payload_axis_ids(data_root: str | Path) -> frozenset[str]:
    """Axis ids actually emitted on committed workspace payloads."""
    ids: set[str] = set()
    root = Path(data_root)
    for path in sorted(root.glob("workspaces/*/US/latest.json")):
        snap = json.loads(path.read_text(encoding="utf-8"))
        for axis in ((snap.get("axes") or {}).get("items") or []):
            axis_id = axis.get("axis_id")
            if axis_id:
                ids.add(str(axis_id))
    return frozenset(ids)


def resolve_vector_axes(
    axes: Sequence[Mapping[str, Any]],
    vector: Mapping[str, Any] | None,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    """Bind dx/dy to axes by id. Missing ids raise — no positional fallback."""
    items = list(axes or [])
    by_id = {str(axis.get("axis_id")): axis for axis in items if axis.get("axis_id")}
    block = vector or {}
    x_id = block.get("x_axis_id")
    y_id = block.get("y_axis_id")
    if not x_id or not y_id:
        raise KeyError("vector is missing required x_axis_id/y_axis_id")
    if str(x_id) not in by_id or str(y_id) not in by_id:
        raise KeyError(f"vector axis id not in axes: {x_id!r} {y_id!r}")
    return by_id[str(x_id)], by_id[str(y_id)]

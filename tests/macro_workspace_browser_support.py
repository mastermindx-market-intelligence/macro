"""Full dashboard template fixture for the Macro workspace experience.

The view-model is explicitly representative test data, not a market feed.
All layout, nav, styles, inline behavior and dialog markup come from source.
Only external services/live ingestion are stopped for deterministic UI proof.
"""
from __future__ import annotations

import copy
import json
import math
import re
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

import jinja2

from engine import i18n
from engine.macro_news import CHANNEL_LABEL

ROOT = Path(__file__).resolve().parents[1]
EVENT_NAMES = [
    ("Consumer Price Index — headline and core inflation", "居民消费价格指数——整体与核心通胀"),
    ("Initial jobless claims and continuing unemployment claims", "初次申请失业救济与持续申领人数"),
    ("Producer Price Index — final demand", "生产者价格指数——最终需求"),
    ("Federal Reserve policy decision and press conference", "美联储利率决议及新闻发布会"),
    ("Monthly options expiration", "月度期权到期"),
]


def workspace_vm(**overrides):
    vm = json.loads((ROOT / "tests/fixtures/macro_workspace/view_model.json").read_text())
    vm["latest"].update(date="2026-11-06", quad="Q2", quad_name="Reflation",
                        transition_state="TRANSITIONING")
    ms = vm["market_state"]
    ms.update(
        score=36, raw_score=36, color="red", verdict="RISK_OFF",
        label_en="Risk-off", label_zh="避险", asof="2026-11-06",
        headline_en="Risk-off — stress is elevated; defend capital first.",
        headline_zh="避险——压力偏高，优先保护本金。",
        flip_en="Mixed when trend & technicals firms up.",
        flip_zh="趋势与技术面改善后，才可能转向中性。",
        components=[
            dict(key=key, label_en=en, label_zh=zh, score=score, tone=tone,
                 why_en="Representative test observation.", why_zh="代表性测试读数。")
            for key, en, zh, score, tone in [
                ("trend", "Trend & technicals", "趋势与技术面", 28, "bad"),
                ("risk", "Risk appetite", "风险偏好", 34, "warn"),
                ("vol", "Volatility regime", "波动率状态", 33, "warn"),
                ("breadth", "Breadth & participation", "广度与参与度", 30, "bad"),
                ("liquidity", "Liquidity & credit", "流动性与信用", 61, "good"),
                ("stress", "Downturn-risk guard", "下行风险", 30, "bad"),
            ]
        ],
    )
    ms["radar"].update(state="warning", top_score=87,
                       label_en="Risk building", label_zh="风险积聚",
                       do_en="Wait for conditions to stabilize.", do_zh="等待市场环境企稳。")
    start = date(2026, 8, 17)
    days = []
    while len(days) < 60:
        if start.weekday() < 5:
            days.append(start)
        start += timedelta(days=1)
    vm["ms_history"] = [
        dict(asof=day.isoformat(), score=round(73 - i * .62 + math.sin(i * .7) * 4),
             verdict="RISK_ON" if i < 20 else ("MIXED" if i < 47 else "RISK_OFF"))
        for i, day in enumerate(days)
    ]
    vm["ms_history"][-1].update(score=36, verdict="RISK_OFF")
    vm["macro_catalysts"] = [
        dict(date=f"2026-11-{day}", label=en, label_zh=zh, impact=impact)
        for (en, zh), day, impact in zip(EVENT_NAMES, ["10", "12", "13", "18", "20"],
                                        ["high", "med", "high", "high", "med"])
    ]
    vm["fear_greed"] = dict(dial=35, label_en="Fear", label_zh="恐慌",
                            n_legs_qualifying=11, young_tiles=[])
    vm["sector_heat"] = {
        "heating": [dict(name=en, name_zh=zh, rank=rank) for rank, en, zh in
                    [(1, "Energy", "能源"), (2, "Technology", "科技"), (3, "Financials", "金融")]],
        "cooling": [dict(name=en, name_zh=zh, rank=rank) for rank, en, zh in
                    [(9, "Utilities", "公用事业"), (10, "Real Estate", "房地产"), (11, "Health Care", "医疗保健")]],
    }
    vm["alerts"] = [json.loads((ROOT / "tests/fixtures/macro_workspace/alert.json").read_text())]
    vm["macro_news"] = {
        "synthesis": {"high_impact_count": 3, "dominant_channel": "inflation",
                      "dominant_theme": "Inflation", "top_tickers": [{"ticker": "SPY"}, {"ticker": "TLT"}]},
        "headlines": [dict(title=en, title_zh=zh, importance="high", channel="inflation",
                           source_name="Illustrative fixture", url="https://example.com/fixture")
                      for en, zh in [("Illustrative inflation release context", "示例：通胀数据背景"),
                                     ("Illustrative policy meeting context", "示例：政策会议背景"),
                                     ("Illustrative market breadth context", "示例：市场广度背景")]],
    }
    vm["policy_lever"] = dict(schema="policy_lever.v1", state="ELEVATED",
                              repricing_components=[], asof="2026-11-06")
    vm["latest"]["fed_stance"] = dict(stance="hawkish", label_en="Hawkish",
                                       label_zh="鹰派", n_speeches_7d=4)
    vm["rates_command"] = json.loads((ROOT / "tests/fixtures/macro_workspace/rates_command.json").read_text())
    vm.update(copy.deepcopy(overrides))
    return vm


@lru_cache(maxsize=1)
def _workspace_env():
    # The Macro render uses the production loader, i18n globals, zip and filters.
    # Its frozen VM avoids importing the unrelated Stocks build/collector chain.
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(ROOT / "templates")), autoescape=True)
    env.filters["min"] = min
    env.globals.update(td=i18n.td, tr=i18n.tr, zip=zip, CHANNEL_LABEL=CHANNEL_LABEL)
    env.filters["regex_replace"] = lambda value, pattern, repl: re.sub(pattern, repl, value) if isinstance(value, str) else value
    return env


def render_workspace(_template_source=None, **overrides):
    env = _workspace_env()
    template = env.from_string(_template_source) if _template_source else env.get_template("dashboard.html.j2")
    html = template.render(**workspace_vm(**overrides), mode="macro")
    # These owners contact signed-in services, mutate source snapshots or poll live data.
    # Retain canonical nav/theme/illus and all actual inline dashboard controllers.
    stopped = {
        "live_config.js", "auth.js", "auth_gate.js", "auth_gate_loader.js", "live.js", "tape.js",
        "risk_state_live.js", "release_publications_live.js", "master_brief_live.js",
        "stock_notes.js", "assistant.js", "access.js", "tier_preview.js", "chat_widget.js",
    }
    def source_script(match):
        src = match.group(1)
        name = src.split("?")[0].rsplit("/", 1)[-1]
        if name in stopped or src.startswith(("http:", "https:", "//")):
            return ""
        return match.group(0)
    html = re.sub(r'<script[^>]*src="([^"]+)"[^>]*>\s*</script>', source_script, html)
    # Representative hydrated tape; live ingestion is tested by its existing owner.
    quote_text = {
        "ES=F": ("7,455.00", "+0.72%"), "NQ=F": ("27,270.75", "+0.68%"),
        "YM=F": ("51,905.00", "+1.01%"), "RTY=F": ("2,795.40", "+1.26%"),
        "^TNX": ("4.86%", "+0 bps"), "DX-Y.NYB": ("101.84", "−0.45%"),
    }
    def tape_cell(match):
        opening, kind, symbol = match.group(1), match.group(2), match.group(3)
        value = quote_text[symbol][0 if kind == "price" else 1]
        opening = opening.replace(" skel", "").replace('aria-busy="true"', 'aria-busy="false"')
        return opening + value + "</div>"
    html = re.sub(r'(<div class="mx5-mkt-(price|delta)[^>]*data-sym="([^"]+)"[^>]*>)</div>', tape_cell, html)
    return html


def write_preview(directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "macro.html").write_text(render_workspace())
    (directory / "unavailable.html").write_text(render_workspace(
        market_state=None, ms_history=None, macro_catalysts=None,
        fear_greed=None, sector_heat=None, policy_lever=None, rates_command=None,
        macro_news=None, alerts=[]))
    (directory / "macrodata").mkdir(exist_ok=True)
    (directory / "macrodata/release_forecast.json").write_text("{}\n")
    for source in (ROOT / "templates").iterdir():
        if source.is_file() and source.suffix in (".js", ".css"):
            dest = directory / source.name
            if not dest.exists():
                dest.symlink_to(source)
    for name in ("fonts", "assets", "icons"):
        source = ROOT / "templates" / name
        if not source.exists():
            source = ROOT / "site" / name
        dest = directory / name
        if source.exists() and not dest.exists():
            dest.symlink_to(source, target_is_directory=source.is_dir())
    return directory

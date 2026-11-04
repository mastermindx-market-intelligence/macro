"""Evidence-linked economic interpretation for the International country view.

Conclusions are derived from named, dated inputs. A missing dependency suppresses
only its conclusion. Forecasts, observed prices and conditional policy readings
remain distinct; no composite risk score or trading recommendation is produced.
"""
from __future__ import annotations

from datetime import date
from math import ceil, floor

from lib.intl_forecast_vintages import select_publications, publication_view

LABELS = {
    "real_gdp_growth": ("Real GDP growth", "实际GDP增长"),
    "inflation_average": ("Annual inflation", "全年通胀"),
    "current_account": ("Current account", "经常账户"),
    "fiscal_balance": ("Government balance", "政府财政收支"),
    "government_debt": ("Gross government debt", "政府总债务"),
}


COVERAGE_TRANSLATIONS = {
    "General government. Sector and instrument coverage can differ across countries; this is not a sovereign-risk ranking.":
        "政府部门。各经济体的部门与债务工具口径可能不同；这些数据不构成主权风险排名。",
    "General government. Sector and instrument coverage can differ across countries; this is not a sovereign-risk ranking. Japan gross debt is reported on a nonconsolidated basis.":
        "政府部门。各经济体的部门与债务工具口径可能不同；这些数据不构成主权风险排名。日本总债务采用未合并口径。",
    "Euro-area aggregate adjusted for reporting discrepancies in intra-area transactions.":
        "欧元区汇总数据已调整区内交易的报告差异。",
}


def _direction(value):
    return "up" if value > 0.15 else "down" if value < -0.15 else "steady"


def _aligned_views(*views):
    """Combine projections only when their source vintage and intervals match."""
    if not views or any(not v or v.get("next_period") is None for v in views):
        return False
    first = views[0]
    return all(
        all(v.get(k) == first.get(k) for k in ("provider", "family", "edition", "information_cutoff"))
        and all(v[p][k] == first[p][k] for p in ("current_period", "next_period") for k in ("start", "end"))
        for v in views[1:])


def _evidence(view, points=None):
    points = points or [view["current_period"]] + ([view["next_period"]] if view["next_period"] else [])
    return [{"record_id": view["record_id"], "series_id": view["series_id"],
             "period_start": point["start"], "period_end": point["end"],
             "period_label": point["label"], "value": point["value"],
             "published": view["published"], "information_cutoff": view["information_cutoff"]}
            for point in points]


def _proposition(cc, key, en, zh, views, rule, *, kind="conditional_interpretation"):
    return {"id": cc + ":" + key, "classification": kind, "text_en": en, "text_zh": zh,
            "evidence": [item for view in views for item in _evidence(view)],
            "derivation": rule, "dependencies": [view["record_id"] for view in views]}


def _chart(growth):
    points = [p for p in growth["periods"] if growth["year"] - 3 <= p["year"] <= growth["year"] + 1]
    if len(points) < 3 or any(b["year"] != a["year"] + 1 for a, b in zip(points, points[1:])):
        return None
    low = min(0.0, floor(min(p["value"] for p in points)))
    high = max(1.0, ceil(max(p["value"] for p in points)))
    if high == low:
        high = low + 1
    coordinates = []
    for index, p in enumerate(points):
        x = 30 + index * 380 / (len(points) - 1)
        y = 32 + (high - p["value"]) * 72 / (high - low)
        coordinates.append({**p, "x": round(x, 2), "y": round(y, 2),
                            "display_label": p["label"].replace("FY20", "") if p["label"].startswith("FY20") else p["label"],
                            "projected": p["status"] == "projection"})
    first_projection = next((i for i, p in enumerate(coordinates) if p["projected"]), len(coordinates))
    historical = coordinates[:first_projection]
    projected = coordinates[max(0, first_projection - 1):] if first_projection < len(coordinates) else []
    poly = lambda pts: " ".join(f'{p["x"]},{p["y"]}' for p in pts)
    return {"points": coordinates, "historical_line": poly(historical), "projection_line": poly(projected),
            "low": low, "high": high, "zero_y": round(32 + high * 72 / (high - low), 2),
            "description_en": "; ".join(f'{p["label"]}: {p["value"]:.1f}% ({p["status"].replace("_", " ")})' for p in points),
            "description_zh": "；".join(f'{p["label"]}：{p["value"]:.1f}%（{"预测" if p["status"] == "projection" else "机构历史数据"}）' for p in points)}


def build_country_outlook(cc, archive, *, today, growth=None, metrics=(), market=None, operational_as_of=None, policy_decision=None):
    series = {}
    for key in LABELS:
        selected = select_publications(archive, cc, key, today=today, operational_as_of=operational_as_of)
        if selected:
            view = publication_view(selected[0], archive, today=today, operational_as_of=operational_as_of)
            view["label_en"], view["label_zh"] = LABELS[key]
            if not view.get("coverage_note_zh"):
                view["coverage_note_zh"] = COVERAGE_TRANSLATIONS.get(view.get("coverage_note"))
            series[key] = view
    growth = growth or series.get("real_gdp_growth")
    if growth:
        series["real_gdp_growth"] = growth
        growth["label_en"], growth["label_zh"] = LABELS["real_gdp_growth"]
    inflation = series.get("inflation_average")
    propositions, balances = [], []
    title = summary = policy = None
    comparable = _aligned_views(growth, inflation)
    if comparable:
        gd, pi = _direction(growth["change"]), _direction(inflation["change"])
        if growth["next"] < 0:
            title = ("Contraction ahead, with prices shaping policy", "预计经济收缩，物价走势影响政策")
        elif growth["next"] == 0:
            title = ("Zero growth is projected for the next period", "下一期间预计零增长")
        elif growth["current"] < 0 < growth["next"]:
            title = ("A return to growth is projected", "预计恢复经济增长")
        elif growth["current"] > 8 and growth["change"] < -1:
            title = ("Exceptional growth gives way to slower expansion", "高速增长预计转为较缓扩张")
        else:
            titles = {
                ("up", "down"): ("Growth strengthens as inflation eases", "增长走强，通胀回落"),
                ("up", "up"): ("Stronger growth, firmer inflation ahead", "增长加强，通胀趋升"),
                ("up", "steady"): ("Growth strengthens with inflation little changed", "增长走强，通胀变化有限"),
                ("down", "down"): ("Growth cools as inflation eases", "增长放缓，通胀回落"),
                ("down", "up"): ("Slower growth meets rising inflation", "增长放缓，通胀上升"),
                ("down", "steady"): ("Growth slows with little relief on inflation", "增长放缓，通胀改善有限"),
                ("steady", "down"): ("Steady growth, easing price pressure ahead", "增长平稳，物价压力预计缓解"),
                ("steady", "up"): ("Steady growth faces higher inflation", "增长平稳，通胀预计升高"),
                ("steady", "steady"): ("Growth and inflation are broadly steady", "增长与通胀大致平稳"),
            }
            title = titles[(gd, pi)]
        summary = (f'{growth["provider"]} projects {growth["next"]:.1f}% growth and {inflation["next"]:.1f}% annual-average inflation in {growth["next_label"]}.',
                   f'{growth["provider"]}预计{growth["next_label"]}实际GDP增长{growth["next"]:.1f}%，全年平均通胀为{inflation["next"]:.1f}%。')
        propositions.append(_proposition(cc, "growth_prices", *title, [growth, inflation],
                            "Same release and periods; next minus current annual rates. Changes within 0.15 pp are described as broadly steady.",
                            kind="published_projection"))
        if pi == "up":
            policy = ("Persistent domestic inflation could constrain scope for easing, even if growth slows.",
                      "即使增长放缓，国内通胀持续偏高仍可能限制政策宽松的空间。")
        elif pi == "down":
            policy = ("If domestic inflation and expectations ease, the central bank may have more scope to support demand.",
                      "若国内通胀与通胀预期回落，央行可能获得更多支持需求的空间。")
        else:
            policy = ("Domestic price persistence and demand, beyond the annual inflation path, determine the policy trade-off.",
                      "除全年通胀路径外，国内物价持续性与需求共同影响政策权衡。")
        propositions.append(_proposition(cc, "policy_tradeoff", *policy, [growth, inflation],
                                         "Conditional inflation-policy mechanism; no policy-rate path is inferred."))
    monthly = next((m for m in metrics if m["key"] == "inflation" and m["current"]), None)
    tension = None
    if (inflation and inflation["change"] is not None and inflation["change"] < -0.15
            and monthly and monthly["change_3m_pp"] is not None and monthly["change_3m_pp"] > 0.25):
        tension = ("The annual forecast eases, but the latest monthly inflation rate has risen over three months.",
                   "全年通胀预测回落，但最新月度同比通胀较三个月前升高。")
        item = _proposition(cc, "inflation_horizons", *tension, [inflation],
                            "Annual-average forecast direction versus three-calendar-month change in observed monthly year-over-year CPI.",
                            kind="observation_and_projection")
        item["evidence"].append({"series_id": "monthly_cpi_yoy", "period": monthly["period"],
                                 "value": monthly["value"], "change_3m_pp": monthly["change_3m_pp"],
                                 "source_url": monthly["source_url"]})
        propositions.append(item)
    for key in ("current_account", "fiscal_balance", "government_debt"):
        view = series.get(key)
        if not view:
            continue
        first, second, change = view["current"], view["next"], view["change"]
        if second is None:
            reading = ("Only one relevant period is supplied by this release.", "本版仅提供一个相关期间。")
        elif key == "current_account":
            if first < 0 and second < 0:
                reading = ("The baseline retains an external deficit; its financing matters for the currency outlook.",
                           "基准预测仍为经常账户赤字，其融资结构关系到汇率前景。")
            elif first > 0 and second > 0:
                reading = ("The baseline retains an external surplus. Its composition matters more than the sign alone.",
                           "基准预测维持经常账户盈余，其构成比正负号本身更重要。")
            elif second >= 0:
                reading = ("The baseline moves toward an external surplus; this is not a currency-return forecast.",
                           "基准预测转向经常账户盈余；这并非汇率回报预测。")
            else:
                reading = ("The baseline moves into an external deficit; financing and import demand need closer attention.",
                           "基准预测转为经常账户赤字，需进一步关注融资与进口需求。")
        elif key == "fiscal_balance":
            if first < 0 and second < 0:
                reading = (("The projected deficit narrows as a share of GDP; the government remains in deficit." if change > 0.15 else
                            "The projected deficit widens as a share of GDP." if change < -0.15 else
                            "The projected deficit is broadly unchanged as a share of GDP."),
                           ("预测赤字占GDP比率收窄，但财政仍为赤字。" if change > 0.15 else
                            "预测赤字占GDP比率扩大。" if change < -0.15 else
                            "预测赤字占GDP比率大致不变。"))
            elif first < 0 <= second:
                reading = (("The baseline moves from deficit to surplus." if second > 0 else
                            "The baseline moves from deficit to a balanced budget."),
                           ("基准预测由赤字转为盈余。" if second > 0 else "基准预测由赤字转为收支平衡。"))
            elif first >= 0 > second:
                reading = ("The baseline moves into deficit.", "基准预测转为财政赤字。")
            elif first > 0 and second > 0:
                reading = (("The projected surplus widens as a share of GDP." if change > 0.15 else
                            "The projected surplus narrows as a share of GDP." if change < -0.15 else
                            "The projected surplus is broadly unchanged as a share of GDP."),
                           ("预测盈余占GDP比率扩大。" if change > 0.15 else
                            "预测盈余占GDP比率收窄。" if change < -0.15 else
                            "预测盈余占GDP比率大致不变。"))
            else:
                reading = (("The baseline moves into surplus." if second > 0 else
                            "The baseline reaches a balanced budget." if first > 0 else
                            "The baseline remains balanced."),
                           ("基准预测转为财政盈余。" if second > 0 else
                            "基准预测转为收支平衡。" if first > 0 else "基准预测维持收支平衡。"))
        else:
            reading = (("Debt rises relative to GDP in the baseline." if change > 0.15 else
                        "Debt falls relative to GDP in the baseline." if change < -0.15 else
                        "The debt-to-GDP ratio is broadly steady in the baseline."),
                       ("基准预测中债务占GDP比率上升。" if change > 0.15 else
                        "基准预测中债务占GDP比率下降。" if change < -0.15 else
                        "基准预测中债务占GDP比率大致稳定。"))
        view["reading_en"], view["reading_zh"] = reading
        balances.append(view)
        propositions.append(_proposition(cc, key, *reading, [view],
                            "Direction of the same published annual balance or debt ratio; no resilience score or distress probability."))
    # Country conclusions use the actual quantitative path and retain their
    # dependencies. The national mechanism is explained below with its own date.
    if comparable and growth["current"] > 0 and growth["next"] > 0:
        views = [growth, inflation]
        n, cur = growth["next"], growth["current"]
        if cc == "JP" and gd == "steady" and pi == "up":
            title = (f'Growth holds near {n:.1f}%; inflation rises', f'增长维持约{n:.1f}%，通胀上升')
        elif cc == "KR" and gd == "down" and growth.get("revision") is not None and growth["revision"] > 0:
            title = (f'Growth cools to {n:.1f}% after an upward revision', f'预测上调后，增长预计放缓至{n:.1f}%')
        elif cc == "TW" and cur >= 10 and gd == "down":
            title = (f'Double-digit growth gives way to {n:.1f}% expansion', f'两位数增长后，预计保持{n:.1f}%扩张')
        elif cc == "IN" and gd == "steady" and pi == "down":
            title = (f'Growth holds at {n:.1f}%; inflation eases', f'增长维持{n:.1f}%，通胀回落')
        elif cc == "AU" and gd == "down" and pi == "down":
            title = (f'Growth slows to {n:.1f}% as inflation eases', f'通胀回落，增长预计放缓至{n:.1f}%')
        elif cc == "GB":
            fb, debt = series.get("fiscal_balance"), series.get("government_debt")
            if (_aligned_views(growth, inflation, fb, debt)
                    and fb["current"] < fb["next"] < 0 and debt["change"] > 0.15):
                title = ("A smaller deficit, with the debt ratio still rising", "赤字收窄，但债务比率仍上升")
                views.extend([fb, debt])
        elif cc == "EZ" and 0 < growth["change"] <= 0.15:
            fb = series.get("fiscal_balance")
            if _aligned_views(growth, inflation, fb) and fb["next"] < 0:
                title = ("Growth edges up; the fiscal deficit persists", "增长小幅回升，财政赤字持续")
                views.append(fb)
        propositions.append(_proposition(cc, "country_thesis", *title, views,
                            "Country reading of selected published annual paths; exact rules and dependencies retained.",
                            kind="published_projection"))
    if policy_decision and policy_decision.get("current"):
        # The named national decision supplies the visible trade-off in its own
        # sourced section. Do not duplicate a generic inflation-policy inference.
        policy = None
        propositions = [p for p in propositions if p["id"] != cc + ":policy_tradeoff"]
        national_read = (policy_decision["rationale_en"], policy_decision["rationale_zh"])
        propositions.append({
            "id": cc + ":national_policy", "classification": "source_attributed_assessment",
            "text_en": national_read[0], "text_zh": national_read[1],
            "evidence": [{"record_id": policy_decision["record_id"], "source_url": policy_decision["source_url"],
                          "published": policy_decision["published"], "decision_date": policy_decision["decision_date"],
                          "effective_date": policy_decision["effective_date"], "instrument": policy_decision["instrument"],
                          "value": policy_decision["value"], "action": policy_decision["action"]}],
            "derivation": "Latest verified national decision; no predicted rate path or cross-instrument stance comparison.",
            "dependencies": [policy_decision["record_id"]],
        })
    divergence = None
    if growth and growth["current"] > 0 and market and market.get("state") == "pressure":
        divergence = ("The growth forecast remains positive while the equity index is below both trend averages.",
                      "经济增长预测仍为正值，但股指低于两条趋势均线。")
        item = _proposition(cc, "market_divergence", *divergence, [growth],
                            "Separate annual GDP forecast and dated 50/200-observation price trends; no causal or valuation inference.",
                            kind="observation_and_projection")
        item["evidence"].append({"series_id": "equity_trend", "as_of": market["as_of"],
                                 "above_50d": market["above_50d"], "above_200d": market["above_200d"]})
        propositions.append(item)
    alternatives = []
    if growth:
        other = select_publications(archive, cc, today=today, operational_as_of=operational_as_of)
        providers = {growth["provider"]}
        for record in other:
            if record["provider"] in providers:
                continue
            alternative = publication_view(record, archive, today=today, operational_as_of=operational_as_of)
            if alternative:
                alternatives.append(alternative)
                providers.add(record["provider"])
    return {"series": series, "inflation": inflation, "balances": balances,
            "title_en": title[0] if title else None, "title_zh": title[1] if title else None,
            "summary_en": summary[0] if summary else None, "summary_zh": summary[1] if summary else None,
            "policy_en": policy[0] if policy else None, "policy_zh": policy[1] if policy else None,
            "tension_en": tension[0] if tension else None, "tension_zh": tension[1] if tension else None,
            "market_divergence_en": divergence[0] if divergence else None,
            "market_divergence_zh": divergence[1] if divergence else None,
            "chart": _chart(growth) if growth else None, "alternatives": alternatives,
            "propositions": propositions,
            "missing_series": [key for key in LABELS if key not in series]}

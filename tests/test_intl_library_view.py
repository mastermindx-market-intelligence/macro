import copy
import json
from pathlib import Path

import pytest

from lib.intl_library_view import (
    build_intl_library_view,
    resolve_intl_tool,
)


BINDINGS = json.loads(r"""
{
  "schema": "handoff.intl_tool_bindings.v1",
  "purpose": "local presentation bindings, not global tool authority",
  "source_sha": "dd3d218eec55fb2f55526e81877a7ee3134efd8c",
  "groups": [
    {
      "id": "leaders",
      "label_en": "Find the leaders",
      "label_zh": "寻找领涨者",
      "native_node": "3IN-0"
    },
    {
      "id": "recovery",
      "label_en": "Check the recovery",
      "label_zh": "检查修复",
      "native_node": "3JZ-0"
    },
    {
      "id": "policy",
      "label_en": "Follow policy divergence",
      "label_zh": "跟踪政策分化",
      "native_node": "3LB-0"
    },
    {
      "id": "backdrop",
      "label_en": "Understand the backdrop",
      "label_zh": "理解背景",
      "native_node": "3MN-0"
    },
    {
      "id": "pressure",
      "label_en": "Trace the pressure",
      "label_zh": "追踪压力",
      "native_node": "38A-0"
    },
    {
      "id": "challenge",
      "label_en": "Challenge the conclusion",
      "label_zh": "检验结论",
      "native_node": "3NZ-0"
    }
  ],
  "tools": [
    {
      "presentation_key": "performance_currency",
      "group_id": "leaders",
      "order": 0,
      "label_en": "Performance & currency",
      "label_zh": "表现与汇率",
      "question_en": "Find the leaders",
      "question_zh": "寻找领涨者",
      "aliases": [
        "currency",
        "returns",
        "FX",
        "USD",
        "回报",
        "汇率"
      ],
      "source_path": "engine/intl_performance.py",
      "source_symbol": "performance_panel",
      "source_url": "https://github.com/mastermindx-market-intelligence/macro/blob/dd3d218eec55fb2f55526e81877a7ee3134efd8c/engine/intl_performance.py",
      "projection": "perf.leaderboard",
      "page_id": "macro:intl",
      "existing_route": "/intl.html",
      "target_view": "compare",
      "proposed_region_id": "im-tool-performance-currency",
      "region_id_state": "PROPOSED_NOT_EXISTING",
      "analytical_scope": "seven-market"
    },
    {
      "presentation_key": "leadership_rotation",
      "group_id": "leaders",
      "order": 1,
      "label_en": "Leadership rotation",
      "label_zh": "领涨轮动",
      "question_en": "Find the leaders",
      "question_zh": "寻找领涨者",
      "aliases": [
        "rank",
        "momentum",
        "排名",
        "动量",
        "轮动"
      ],
      "source_path": "engine/intl_rotation.py",
      "source_symbol": "rank",
      "source_url": "https://github.com/mastermindx-market-intelligence/macro/blob/dd3d218eec55fb2f55526e81877a7ee3134efd8c/engine/intl_rotation.py",
      "projection": "rotation_ranks",
      "page_id": "macro:intl",
      "existing_route": "/intl.html",
      "target_view": "compare",
      "proposed_region_id": "im-tool-leadership-rotation",
      "region_id_state": "PROPOSED_NOT_EXISTING",
      "analytical_scope": "seven-market; not capital flow"
    },
    {
      "presentation_key": "cross_country",
      "group_id": "leaders",
      "order": 2,
      "label_en": "Cross-country comparison",
      "label_zh": "跨经济体比较",
      "question_en": "Find the leaders",
      "question_zh": "寻找领涨者",
      "aliases": [
        "country",
        "economy",
        "comparison",
        "经济体",
        "比较"
      ],
      "source_path": "engine/intl_compare.py",
      "source_symbol": "rankings",
      "source_url": "https://github.com/mastermindx-market-intelligence/macro/blob/dd3d218eec55fb2f55526e81877a7ee3134efd8c/engine/intl_compare.py",
      "projection": "records; rankings",
      "page_id": "macro:intl",
      "existing_route": "/intl.html",
      "target_view": "macro",
      "proposed_region_id": "im-tool-cross-country",
      "region_id_state": "PROPOSED_NOT_EXISTING",
      "analytical_scope": "seven-market"
    },
    {
      "presentation_key": "market_turns",
      "group_id": "recovery",
      "order": 3,
      "label_en": "Market turns",
      "label_zh": "市场转折",
      "question_en": "Check the recovery",
      "question_zh": "检查修复",
      "aliases": [
        "trend",
        "repair",
        "turns",
        "拐点",
        "趋势",
        "修复"
      ],
      "source_path": "engine/intl_market_state.py",
      "source_symbol": "market_states",
      "source_url": "https://github.com/mastermindx-market-intelligence/macro/blob/dd3d218eec55fb2f55526e81877a7ee3134efd8c/engine/intl_market_state.py",
      "projection": "turn_board; turn_events",
      "page_id": "macro:intl",
      "existing_route": "/intl.html",
      "target_view": "overview",
      "proposed_region_id": "im-tool-market-turns",
      "region_id_state": "PROPOSED_NOT_EXISTING",
      "analytical_scope": "world-context plus core; preserve cohort"
    },
    {
      "presentation_key": "recovery_quality",
      "group_id": "recovery",
      "order": 4,
      "label_en": "Recovery quality",
      "label_zh": "修复质量",
      "question_en": "Check the recovery",
      "question_zh": "检查修复",
      "aliases": [
        "recovery",
        "confirmation",
        "quality",
        "修复",
        "确认"
      ],
      "source_path": "engine/intl_recovery_quality.py",
      "source_symbol": "apply_recovery_naming",
      "source_url": "https://github.com/mastermindx-market-intelligence/macro/blob/dd3d218eec55fb2f55526e81877a7ee3134efd8c/engine/intl_recovery_quality.py",
      "projection": "turn_board recovery_assessment where supplied",
      "page_id": "macro:intl",
      "existing_route": "/intl.html",
      "target_view": "overview",
      "proposed_region_id": "im-tool-recovery-quality",
      "region_id_state": "PROPOSED_NOT_EXISTING",
      "analytical_scope": "owner profile; partial coverage"
    },
    {
      "presentation_key": "participation_concentration",
      "group_id": "recovery",
      "order": 5,
      "label_en": "Participation & concentration",
      "label_zh": "参与度与集中度",
      "question_en": "Check the recovery",
      "question_zh": "检查修复",
      "aliases": [
        "breadth",
        "constituents",
        "广度",
        "成分股",
        "集中度"
      ],
      "source_path": "engine/intl_market_confirmation.py",
      "source_symbol": "breadth_snapshot",
      "source_url": "https://github.com/mastermindx-market-intelligence/macro/blob/dd3d218eec55fb2f55526e81877a7ee3134efd8c/engine/intl_market_confirmation.py",
      "projection": "owner confirmation only; full PIT concentration unbound",
      "page_id": "macro:intl",
      "existing_route": "/intl.html",
      "target_view": "overview",
      "proposed_region_id": "im-tool-participation-concentration",
      "region_id_state": "PROPOSED_NOT_EXISTING",
      "analytical_scope": "owner profile; no invented breadth"
    },
    {
      "presentation_key": "rates_curves_carry",
      "group_id": "policy",
      "order": 6,
      "label_en": "Rates, curves & carry",
      "label_zh": "利率、曲线与息差",
      "question_en": "Follow policy divergence",
      "question_zh": "跟踪政策分化",
      "aliases": [
        "rates",
        "yield",
        "curve",
        "carry",
        "利率",
        "收益率",
        "曲线",
        "息差"
      ],
      "source_path": "engine/intl_rates.py",
      "source_symbol": "rates_desk",
      "source_url": "https://github.com/mastermindx-market-intelligence/macro/blob/dd3d218eec55fb2f55526e81877a7ee3134efd8c/engine/intl_rates.py",
      "projection": "rates",
      "page_id": "macro:intl",
      "existing_route": "/intl.html",
      "target_view": "macro",
      "proposed_region_id": "im-tool-rates-curves-carry",
      "region_id_state": "PROPOSED_NOT_EXISTING",
      "analytical_scope": "seven-market plus US anchor"
    },
    {
      "presentation_key": "central_banks_liquidity",
      "group_id": "policy",
      "order": 7,
      "label_en": "Central banks & liquidity",
      "label_zh": "央行与流动性",
      "question_en": "Follow policy divergence",
      "question_zh": "跟踪政策分化",
      "aliases": [
        "central",
        "banks",
        "policy",
        "liquidity",
        "央行",
        "政策",
        "流动性"
      ],
      "source_path": "engine/cb_desk.py",
      "source_symbol": "snapshot",
      "source_url": "https://github.com/mastermindx-market-intelligence/macro/blob/dd3d218eec55fb2f55526e81877a7ee3134efd8c/engine/cb_desk.py",
      "projection": "risk_desk.cb_desk; rates.liquidity",
      "page_id": "macro:intl",
      "existing_route": "/intl.html",
      "target_view": "macro",
      "proposed_region_id": "im-tool-central-banks-liquidity",
      "region_id_state": "PROPOSED_NOT_EXISTING",
      "analytical_scope": "central-bank roster; proxies labeled"
    },
    {
      "presentation_key": "credit_bonds",
      "group_id": "policy",
      "order": 8,
      "label_en": "Credit & bonds",
      "label_zh": "信用与债券",
      "question_en": "Follow policy divergence",
      "question_zh": "跟踪政策分化",
      "aliases": [
        "credit",
        "bonds",
        "spreads",
        "信用",
        "债券",
        "利差"
      ],
      "source_path": "engine/intl_bonds.py",
      "source_symbol": "inversion_board",
      "source_url": "https://github.com/mastermindx-market-intelligence/macro/blob/dd3d218eec55fb2f55526e81877a7ee3134efd8c/engine/intl_bonds.py",
      "projection": "risk_desk.inversion_board; em_stress; two_tier",
      "page_id": "macro:intl",
      "existing_route": "/intl.html",
      "target_view": "risk",
      "proposed_region_id": "im-tool-credit-bonds",
      "region_id_state": "PROPOSED_NOT_EXISTING",
      "analytical_scope": "sovereign and EM regional; not country-credit substitute"
    },
    {
      "presentation_key": "euro_fragmentation",
      "group_id": "backdrop",
      "order": 9,
      "label_en": "Euro-area fragmentation",
      "label_zh": "欧元区分化",
      "question_en": "Understand the backdrop",
      "question_zh": "理解背景",
      "aliases": [
        "euro",
        "fragmentation",
        "欧元区",
        "分化"
      ],
      "source_path": "engine/intl_compare.py",
      "source_symbol": "periphery_panel",
      "source_url": "https://github.com/mastermindx-market-intelligence/macro/blob/dd3d218eec55fb2f55526e81877a7ee3134efd8c/engine/intl_compare.py",
      "projection": "periphery; rates.periphery",
      "page_id": "macro:intl",
      "existing_route": "/intl.html",
      "target_view": "macro",
      "proposed_region_id": "im-tool-euro-fragmentation",
      "region_id_state": "PROPOSED_NOT_EXISTING",
      "analytical_scope": "EZ regional context; preserve Japan on return"
    },
    {
      "presentation_key": "growth_inflation",
      "group_id": "backdrop",
      "order": 10,
      "label_en": "Growth & inflation",
      "label_zh": "增长与通胀",
      "question_en": "Understand the backdrop",
      "question_zh": "理解背景",
      "aliases": [
        "growth",
        "inflation",
        "cycle",
        "GDP",
        "CPI",
        "增长",
        "通胀",
        "周期"
      ],
      "source_path": "engine/intl_regime.py",
      "source_symbol": "classify",
      "source_url": "https://github.com/mastermindx-market-intelligence/macro/blob/dd3d218eec55fb2f55526e81877a7ee3134efd8c/engine/intl_regime.py",
      "projection": "records; heatmap",
      "page_id": "macro:intl",
      "existing_route": "/intl.html",
      "target_view": "macro",
      "proposed_region_id": "im-tool-growth-inflation",
      "region_id_state": "PROPOSED_NOT_EXISTING",
      "analytical_scope": "qualified core; unclassified visible"
    },
    {
      "presentation_key": "dollar_conditions",
      "group_id": "backdrop",
      "order": 11,
      "label_en": "Dollar conditions",
      "label_zh": "美元环境",
      "question_en": "Understand the backdrop",
      "question_zh": "理解背景",
      "aliases": [
        "dollar",
        "funding",
        "USD",
        "美元",
        "融资"
      ],
      "source_path": "engine/flow_regime.py",
      "source_symbol": "compose (existing producer only)",
      "source_url": "https://github.com/mastermindx-market-intelligence/macro/blob/dd3d218eec55fb2f55526e81877a7ee3134efd8c/engine/flow_regime.py",
      "projection": "risk_desk.smile; existing flow_regime publication",
      "page_id": "macro:intl",
      "existing_route": "/intl.html",
      "target_view": "risk",
      "proposed_region_id": "im-tool-dollar-conditions",
      "region_id_state": "PROPOSED_NOT_EXISTING",
      "analytical_scope": "global context; distinguish source families"
    },
    {
      "presentation_key": "structural_fragility",
      "group_id": "pressure",
      "order": 12,
      "label_en": "Structural fragility",
      "label_zh": "结构性脆弱性",
      "question_en": "Trace the pressure",
      "question_zh": "追踪压力",
      "aliases": [
        "fragility",
        "debt",
        "current",
        "account",
        "脆弱",
        "债务",
        "经常账户"
      ],
      "source_path": "engine/intl_risk.py",
      "source_symbol": "vulnerability_table",
      "source_url": "https://github.com/mastermindx-market-intelligence/macro/blob/dd3d218eec55fb2f55526e81877a7ee3134efd8c/engine/intl_risk.py",
      "projection": "risk_desk.vulnerability",
      "page_id": "macro:intl",
      "existing_route": "/intl.html",
      "target_view": "risk",
      "proposed_region_id": "im-tool-structural-fragility",
      "region_id_state": "PROPOSED_NOT_EXISTING",
      "analytical_scope": "IMF country roster; qualified vintage"
    },
    {
      "presentation_key": "contagion",
      "group_id": "pressure",
      "order": 13,
      "label_en": "Contagion",
      "label_zh": "传导",
      "question_en": "Trace the pressure",
      "question_zh": "追踪压力",
      "aliases": [
        "contagion",
        "spillover",
        "transmission",
        "传导",
        "溢出"
      ],
      "source_path": "engine/contagion.py",
      "source_symbol": "spillover; corr_tightening; two_tier_read",
      "source_url": "https://github.com/mastermindx-market-intelligence/macro/blob/dd3d218eec55fb2f55526e81877a7ee3134efd8c/engine/contagion.py",
      "projection": "risk_desk.spillover; corr_tightening; two_tier",
      "page_id": "macro:intl",
      "existing_route": "/intl.html",
      "target_view": "risk",
      "proposed_region_id": "im-tool-contagion",
      "region_id_state": "PROPOSED_NOT_EXISTING",
      "analytical_scope": "distinct statistical and EM-US methods"
    },
    {
      "presentation_key": "trade_supply_links",
      "group_id": "pressure",
      "order": 14,
      "label_en": "Trade & supply links",
      "label_zh": "贸易与供应链联系",
      "question_en": "Trace the pressure",
      "question_zh": "追踪压力",
      "aliases": [
        "trade",
        "supply",
        "chain",
        "exposure",
        "贸易",
        "供应链",
        "敞口"
      ],
      "source_path": "engine/contagion_links.py",
      "source_symbol": "compute",
      "source_url": "https://github.com/mastermindx-market-intelligence/macro/blob/dd3d218eec55fb2f55526e81877a7ee3134efd8c/engine/contagion_links.py",
      "projection": "CGL static/blended model context; sourced business exposure unbound",
      "page_id": "macro:intl",
      "existing_route": "/intl.html",
      "target_view": "risk",
      "proposed_region_id": "im-tool-trade-supply-links",
      "region_id_state": "PROPOSED_NOT_EXISTING",
      "analytical_scope": "model context is not documented company exposure"
    },
    {
      "presentation_key": "cross_market_correlation",
      "group_id": "challenge",
      "order": 15,
      "label_en": "Cross-market correlation",
      "label_zh": "跨市场相关性",
      "question_en": "Challenge the conclusion",
      "question_zh": "检验结论",
      "aliases": [
        "correlation",
        "diversification",
        "相关性",
        "分散"
      ],
      "source_path": "engine/intl_performance.py",
      "source_symbol": "correlation_matrix",
      "source_url": "https://github.com/mastermindx-market-intelligence/macro/blob/dd3d218eec55fb2f55526e81877a7ee3134efd8c/engine/intl_performance.py",
      "projection": "perf.correlation",
      "page_id": "macro:intl",
      "existing_route": "/intl.html",
      "target_view": "compare",
      "proposed_region_id": "im-tool-cross-market-correlation",
      "region_id_state": "PROPOSED_NOT_EXISTING",
      "analytical_scope": "qualified weekly USD population; not causality"
    },
    {
      "presentation_key": "risk_track_record",
      "group_id": "challenge",
      "order": 16,
      "label_en": "Risk-radar track record",
      "label_zh": "风险雷达记录",
      "question_en": "Challenge the conclusion",
      "question_zh": "检验结论",
      "aliases": [
        "track",
        "record",
        "false",
        "alarms",
        "accuracy",
        "记录",
        "误报",
        "验证"
      ],
      "source_path": "engine/risk_radar_intl_audit.py",
      "source_symbol": "scorecard(log_governance=False)",
      "source_url": "https://github.com/mastermindx-market-intelligence/macro/blob/dd3d218eec55fb2f55526e81877a7ee3134efd8c/engine/risk_radar_intl_audit.py",
      "projection": "records risk_radar.forward_log; existing read-only scorecard",
      "page_id": "macro:intl",
      "existing_route": "/intl.html",
      "target_view": "history",
      "proposed_region_id": "im-tool-risk-track-record",
      "region_id_state": "PROPOSED_NOT_EXISTING",
      "analytical_scope": "market profile; sample and authority gate"
    },
    {
      "presentation_key": "country_sectors_stocks",
      "group_id": "challenge",
      "order": 17,
      "label_en": "Country sectors & stocks",
      "label_zh": "经济体板块与股票",
      "question_en": "Challenge the conclusion",
      "question_zh": "检验结论",
      "aliases": [
        "sectors",
        "stocks",
        "industry",
        "板块",
        "股票",
        "行业"
      ],
      "source_path": "scripts/build_intl_library.py",
      "source_symbol": "main (BUILD ONLY)",
      "source_url": "https://github.com/mastermindx-market-intelligence/macro/blob/dd3d218eec55fb2f55526e81877a7ee3134efd8c/scripts/build_intl_library.py",
      "projection": "sector_board; setups; intl_stocks.html; intl_stock.html",
      "page_id": "macro:intl_stocks",
      "existing_route": "/intl_stocks.html",
      "target_view": "library",
      "proposed_region_id": "im-tool-country-sectors-stocks",
      "region_id_state": "PROPOSED_NOT_EXISTING",
      "analytical_scope": "existing stock universe; no assumed market filter"
    }
  ]
}
""")


def route_bindings(targets=None):
    if targets is None:
        targets = {
            "performance_currency": {
                "page_id": "macro:intl",
                "route": "/intl.html",
                "region_id": "lb-board",
                "verified": True,
            },
            "country_sectors_stocks": {
                "page_id": "macro:intl_stocks",
                "route": "/intl_stocks.html",
                "region_id": None,
                "verified": True,
            },
        }
    return {"bindings": copy.deepcopy(BINDINGS), "targets": copy.deepcopy(targets)}


def family(key="performance_currency", metadata="allowed", metrics=None, source="source-a"):
    return {
        "metadata": metadata,
        "values": "allowed",
        "data_state": "supported",
        "owner_ref": "owner:caller",
        "decision_ref": "decision:caller",
        "source_reference": source,
        "metrics": metrics if metrics is not None else [],
    }


def workspace(families=None, generation="generation-1", source="source-a"):
    return {
        "source_reference": source,
        "catalogue_generation": generation,
        "families": families if families is not None else {},
    }


def context(**changes):
    value = {
        "research_market": "JP",
        "market_ids": ["JP", "EZ", "US"],
        "horizon": "1w",
        "horizons": ["1d", "1w"],
        "currency_basis": "usd_unhedged",
        "return_basis": "price",
        "source_reference": "source-a",
    }
    value.update(changes)
    return value


REAL_KEYS = [tool["presentation_key"] for tool in BINDINGS["tools"]]


def all_permitted(metrics=None):
    families = {key: family(metrics=metrics) for key in REAL_KEYS}
    targets = {
        key: {
            "page_id": "macro:intl_stocks" if key == "country_sectors_stocks" else "macro:intl",
            "route": "/intl_stocks.html" if key == "country_sectors_stocks" else "/intl.html",
            "region_id": "lb-board",
            "verified": True,
        }
        if key != "country_sectors_stocks"
        else {
            "page_id": "macro:intl_stocks",
            "route": "/intl_stocks.html",
            "region_id": None,
            "verified": True,
        }
        for key in REAL_KEYS
    }
    return context(), workspace(families), route_bindings(targets)


def assert_rejected(value, mutation, message):
    changed = copy.deepcopy(value)
    mutation(changed)
    with pytest.raises(ValueError, match=message):
        build_intl_library_view(changed, workspace(), route_bindings())


def test_full_catalogue_shape_groups_search_and_no_extras():
    result = build_intl_library_view(*all_permitted())
    assert result["catalogue_state"] == "available"
    assert result["catalogue_generation"] == "generation-1"
    assert result["context"] == {
        "research_market": "JP",
        "horizon": "1w",
        "currency_basis": "usd_unhedged",
        "return_basis": "price",
        "source_reference": "source-a",
    }
    assert len(result["tools"]) == 18
    assert [tool["order"] for tool in result["tools"]] == list(range(18))
    assert [group["slot"] for group in result["groups"]] == list(range(6))
    assert all(len(group["tool_keys"]) == 3 for group in result["groups"])
    assert result["exclusions"] == []
    assert len(result["search_catalogue"]) == 18
    assert set(result["search_catalogue"][0]) == {
        "presentation_key",
        "group_id",
        "order",
        "label_en",
        "label_zh",
        "question_en",
        "question_zh",
        "aliases",
    }
    assert "source_path" not in result["tools"][0]


def test_missing_family_is_isolated_and_denial_hides_private_payload():
    secret = {
        "metadata": "denied",
        "values": "allowed",
        "data_state": "supported",
        "owner_ref": "secret-owner",
        "decision_ref": "secret decision SECRET-LABEL",
        "source_reference": "source-a",
        "metrics": [
            {
                "key": "secret-metric",
                "value": 9,
                "unit": "ratio",
                "interpretation": "proxy",
                "quality": "qualified",
            }
        ],
    }
    targets = {
        "leadership_rotation": {
            "page_id": "macro:intl",
            "route": "/intl.html",
            "region_id": "lb-board",
            "verified": True,
        }
    }
    initial_secret = copy.deepcopy(secret)
    initial_secret["metadata"] = "unknown"
    families = {"leadership_rotation": initial_secret}
    result = build_intl_library_view(context(), workspace(families), route_bindings(targets))
    assert result["catalogue_state"] == "unavailable"
    assert result["groups"] == [{"slot": slot, "state": "withheld"} for slot in range(6)]
    assert result["tools"] == []
    assert result["search_catalogue"] == []
    assert result["exclusions"] == [
        {"slot": index, "state": "unknown", "reason": "metadata_unknown"} for index in range(18)
    ]
    families["leadership_rotation"]["metadata"] = "denied"
    result = build_intl_library_view(context(), workspace(families), route_bindings(targets))
    assert result["exclusions"][1] == {"slot": 1, "state": "denied", "reason": "metadata_denied"}
    serialized = json.dumps(result)
    assert "secret" not in serialized
    assert "secret-metric" not in serialized


def test_euro_context_proxy_and_stale_rules():
    metrics = [
        {"key": "proxy", "value": 0, "unit": "ratio", "interpretation": "proxy", "quality": "qualified"},
        {"key": "stale", "value": 1.5, "unit": "ratio", "interpretation": "observed", "quality": "stale"},
    ]
    context_value = context()
    workspace_value = workspace({"euro_fragmentation": family(metrics=metrics)})
    result = build_intl_library_view(context_value, workspace_value, route_bindings({}))
    euro = result["tools"][0]
    assert euro["research_market"] == "JP"
    assert euro["analytical_market"] == "EZ"
    assert euro["metrics"][0] == {
        "key": "proxy",
        "value": 0,
        "unit": "ratio",
        "interpretation": "proxy",
        "quality": "qualified",
    }
    assert euro["metrics"][1] == {
        "key": "stale",
        "value": None,
        "unit": "ratio",
        "interpretation": "observed",
        "quality": "stale",
        "reason": "unavailable_value",
    }
    resolved = resolve_intl_tool("euro_fragmentation", context_value, workspace_value, route_bindings({}))
    assert resolved["research_market"] == "JP" and resolved["analytical_market"] == "EZ"
    trade_ws = workspace({"trade_supply_links": family()})
    trade = resolve_intl_tool("trade_supply_links", context(), trade_ws, route_bindings({}))
    assert trade["interpretation_notice"] == "model_context_not_company_exposure"
    stale_ws = workspace({"performance_currency": family(metrics=[metrics[1]])})
    assert resolve_intl_tool("performance_currency", context(), stale_ws, route_bindings())["metrics"] == [
        {
            "key": "stale",
            "value": None,
            "unit": "ratio",
            "interpretation": "observed",
            "quality": "stale",
            "reason": "unavailable_value",
        }
    ]


@pytest.mark.parametrize(
    ("family_changes", "expected_quality"),
    [
        ({"values": "denied"}, "qualified"),
        ({"values": "unknown"}, "qualified"),
        ({"data_state": "not_applicable"}, "qualified"),
        ({"data_state": "missing"}, "qualified"),
        ({"data_state": "denied"}, "qualified"),
        ({"data_state": "failed"}, "qualified"),
        ({"data_state": "unknown"}, "qualified"),
        ({"data_state": "stale"}, "qualified"),
        ({"quality": "stale"}, "stale"),
        ({"quality": "missing"}, "missing"),
        ({"quality": "denied"}, "denied"),
        ({"quality": "failed"}, "failed"),
        ({"quality": "unsupported"}, "unsupported"),
        ({"quality": "unknown"}, "unknown"),
    ],
)
def test_withheld_metric_descriptor_is_preserved(family_changes, expected_quality):
    metric = {
        "key": "sample",
        "value": 0,
        "unit": "percent",
        "interpretation": "proxy",
        "quality": "qualified",
    }
    context_value, workspace_value, bindings_value = all_permitted([metric])
    changed_family = {**workspace_value["families"]["performance_currency"], **family_changes}
    if "quality" in family_changes:
        changed_metric = dict(metric)
        changed_metric["quality"] = family_changes["quality"]
        changed_family["metrics"] = [changed_metric]
        changed_family.pop("quality")
    workspace_value["families"]["performance_currency"] = changed_family

    result = build_intl_library_view(context_value, workspace_value, bindings_value)

    assert result["tools"][0]["metrics"] == [
        {
            "key": "sample",
            "value": None,
            "unit": "percent",
            "interpretation": "proxy",
            "quality": expected_quality,
            "reason": "unavailable_value",
        }
    ]


def test_target_real_anchor_stocks_unverified_and_invalid_routes():
    view_ws = workspace({"performance_currency": family(), "country_sectors_stocks": family()})
    result = build_intl_library_view(context(), view_ws, route_bindings())
    performance = next(tool for tool in result["tools"] if tool["presentation_key"] == "performance_currency")
    stocks = next(tool for tool in result["tools"] if tool["presentation_key"] == "country_sectors_stocks")
    assert performance["target"] == {"page_id": "macro:intl", "route": "/intl.html", "region_id": "lb-board"}
    assert stocks["target"] == {"page_id": "macro:intl_stocks", "route": "/intl_stocks.html", "region_id": None}
    assert stocks["data_state"] == "supported" and stocks["reason"] is None
    missing = dict(route_bindings()["targets"])
    missing["performance_currency"] = {
        "page_id": "macro:intl",
        "route": "/intl.html",
        "region_id": "lb-board",
        "verified": False,
    }
    result = build_intl_library_view(context(), view_ws, route_bindings(missing))
    assert result["tools"][0]["route_state"] == "unavailable"
    assert result["tools"][0]["reason"] == "missing_target"
    invalid = route_bindings()
    invalid["targets"]["performance_currency"] = {
        "page_id": "macro:intl",
        "route": "/intl.html?country=JP",
        "region_id": "lb-board",
        "verified": True,
    }
    with pytest.raises(ValueError, match="invalid_target:binding_pair"):
        build_intl_library_view(context(), view_ws, invalid)


def test_malformed_duplicate_context_workspace_and_tool_errors():
    assert_rejected(context(), lambda x: x["market_ids"].append("JP"), "invalid_context:market_ids")
    assert_rejected(context(), lambda x: x.update(extra=1), "invalid_context:fields")
    with pytest.raises(ValueError, match="invalid_workspace:source"):
        build_intl_library_view(context(), workspace(source="other"), route_bindings())
    bad_workspace = workspace({"performance_currency": {**family(), "extra": True}})
    with pytest.raises(ValueError, match="invalid_workspace:family_fields"):
        build_intl_library_view(context(), bad_workspace, route_bindings())
    bad_metrics = workspace({"performance_currency": family(metrics=[{"key": "x", "value": True, "unit": "ratio", "interpretation": "proxy", "quality": "qualified"}])})
    with pytest.raises(ValueError, match="invalid_workspace:metric_value"):
        build_intl_library_view(context(), bad_metrics, route_bindings())
    duplicate = copy.deepcopy(route_bindings())
    duplicate["bindings"]["tools"][1]["order"] = 0
    with pytest.raises(ValueError, match="invalid_bindings:tool_order"):
        build_intl_library_view(context(), workspace(), duplicate)
    assert route_bindings()["bindings"]["tools"][1]["order"] == 1
    duplicate_group = copy.deepcopy(route_bindings())
    duplicate_group["bindings"]["groups"][1]["id"] = "leaders"
    with pytest.raises(ValueError, match="invalid_bindings:group_id"):
        build_intl_library_view(context(), workspace(), duplicate_group)
    with pytest.raises(ValueError, match="invalid_tool:key"):
        resolve_intl_tool("unknown", context(), workspace(), route_bindings())


def test_declared_order_survives_input_permutation():
    context_value, workspace_value, bindings_value = all_permitted()
    bindings_value["bindings"]["tools"].reverse()

    result = build_intl_library_view(context_value, workspace_value, bindings_value)
    declared_keys = [tool["presentation_key"] for tool in BINDINGS["tools"]]
    group_keys = [
        [tool["presentation_key"] for tool in BINDINGS["tools"] if tool["group_id"] == group["id"]]
        for group in BINDINGS["groups"]
    ]

    assert [tool["order"] for tool in result["tools"]] == list(range(18))
    assert [tool["presentation_key"] for tool in result["tools"]] == declared_keys
    assert [row["presentation_key"] for row in result["search_catalogue"]] == declared_keys
    assert [group["tool_keys"] for group in result["groups"]] == group_keys


def test_closed_type_validation_precedes_membership_and_huge_integers_remain_finite():
    with pytest.raises(ValueError, match="invalid_context:currency_basis"):
        build_intl_library_view(context(currency_basis=[]), workspace(), route_bindings())
    with pytest.raises(ValueError, match="invalid_context:return_basis"):
        build_intl_library_view(context(return_basis=True), workspace(), route_bindings())
    bad_group = route_bindings()
    bad_group["bindings"]["tools"][0]["group_id"] = []
    with pytest.raises(ValueError, match="invalid_bindings:tool_group"):
        build_intl_library_view(context(), workspace(), bad_group)
    bad_page = route_bindings()
    bad_page["bindings"]["tools"][0]["page_id"] = []
    with pytest.raises(ValueError, match="invalid_bindings:tool_target"):
        build_intl_library_view(context(), workspace(), bad_page)
    huge_integer = 10**400
    metrics = [
        {
            "key": "huge",
            "value": huge_integer,
            "unit": "ratio",
            "interpretation": "observed",
            "quality": "qualified",
        }
    ]
    result = resolve_intl_tool(
        "performance_currency", context(), workspace({"performance_currency": family(metrics=metrics)}), route_bindings()
    )
    assert result["metrics"][0]["value"] == huge_integer


def test_unknown_source_receipt_and_all_denied_no_public_labels():
    denied = {key: family(metadata="denied") for key in REAL_KEYS}
    result = build_intl_library_view(context(), workspace(denied), route_bindings())
    assert result["catalogue_state"] == "unavailable"
    assert result["search_catalogue"] == []
    assert result["groups"] == [{"slot": index, "state": "withheld"} for index in range(6)]
    receipt = family(source=None)
    result = build_intl_library_view(context(), workspace({"performance_currency": receipt}), route_bindings())
    assert result["groups"][0]["state"] == "withheld"
    mismatch = family(source="wrong")
    result = build_intl_library_view(context(), workspace({"performance_currency": mismatch}), route_bindings())
    assert result["exclusions"][0]["reason"] == "binding_mismatch"
    denied_mismatch = family(metadata="denied", source="wrong")
    result = build_intl_library_view(context(), workspace({"performance_currency": denied_mismatch}), route_bindings())
    assert result["exclusions"][0] == {"slot": 0, "state": "unknown", "reason": "binding_mismatch"}


def test_inputs_not_mutated_deterministic_and_module_has_no_runtime_io():
    context_value = context()
    workspace_value = workspace({"performance_currency": family()})
    bindings_value = route_bindings()
    before = copy.deepcopy((context_value, workspace_value, bindings_value))
    first = build_intl_library_view(context_value, workspace_value, bindings_value)
    second = build_intl_library_view(context_value, workspace_value, bindings_value)
    assert first == second
    assert (context_value, workspace_value, bindings_value) == before
    source = (Path(__file__).parent.parent / "lib" / "intl_library_view.py").read_text(encoding="utf-8")
    for forbidden in ("open(", "Path(", "import requests", "subprocess", "producer"):
        assert forbidden not in source

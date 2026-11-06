import copy
import hashlib
import json

import pytest

from lib.intl_library_view import (
    build_public_intl_library_view,
    public_intl_library_copy_sha256,
)

BINDINGS_JSON = "{\"schema\":\"handoff.intl_tool_bindings.v1\",\"groups\":[{\"id\":\"leaders\",\"label_en\":\"Find the leaders\",\"label_zh\":\"寻找领涨者\",\"native_node\":\"3IN-0\"},{\"id\":\"recovery\",\"label_en\":\"Check the recovery\",\"label_zh\":\"检查修复\",\"native_node\":\"3JZ-0\"},{\"id\":\"policy\",\"label_en\":\"Follow policy divergence\",\"label_zh\":\"跟踪政策分化\",\"native_node\":\"3LB-0\"},{\"id\":\"backdrop\",\"label_en\":\"Understand the backdrop\",\"label_zh\":\"理解背景\",\"native_node\":\"3MN-0\"},{\"id\":\"pressure\",\"label_en\":\"Trace the pressure\",\"label_zh\":\"追踪压力\",\"native_node\":\"38A-0\"},{\"id\":\"challenge\",\"label_en\":\"Challenge the conclusion\",\"label_zh\":\"检验结论\",\"native_node\":\"3NZ-0\"}],\"tools\":[{\"presentation_key\":\"performance_currency\",\"group_id\":\"leaders\",\"order\":0,\"label_en\":\"Performance & currency\",\"label_zh\":\"表现与汇率\",\"question_en\":\"Find the leaders\",\"question_zh\":\"寻找领涨者\",\"aliases\":[\"currency\",\"returns\",\"FX\",\"USD\",\"回报\",\"汇率\"],\"analytical_scope\":\"seven-market\",\"page_id\":\"macro:intl\",\"existing_route\":\"/intl.html\"},{\"presentation_key\":\"leadership_rotation\",\"group_id\":\"leaders\",\"order\":1,\"label_en\":\"Leadership rotation\",\"label_zh\":\"领涨轮动\",\"question_en\":\"Find the leaders\",\"question_zh\":\"寻找领涨者\",\"aliases\":[\"rank\",\"momentum\",\"排名\",\"动量\",\"轮动\"],\"analytical_scope\":\"seven-market; not capital flow\",\"page_id\":\"macro:intl\",\"existing_route\":\"/intl.html\"},{\"presentation_key\":\"cross_country\",\"group_id\":\"leaders\",\"order\":2,\"label_en\":\"Cross-country comparison\",\"label_zh\":\"跨经济体比较\",\"question_en\":\"Find the leaders\",\"question_zh\":\"寻找领涨者\",\"aliases\":[\"country\",\"economy\",\"comparison\",\"经济体\",\"比较\"],\"analytical_scope\":\"seven-market\",\"page_id\":\"macro:intl\",\"existing_route\":\"/intl.html\"},{\"presentation_key\":\"market_turns\",\"group_id\":\"recovery\",\"order\":3,\"label_en\":\"Market turns\",\"label_zh\":\"市场转折\",\"question_en\":\"Check the recovery\",\"question_zh\":\"检查修复\",\"aliases\":[\"trend\",\"repair\",\"turns\",\"拐点\",\"趋势\",\"修复\"],\"analytical_scope\":\"world-context plus core; preserve cohort\",\"page_id\":\"macro:intl\",\"existing_route\":\"/intl.html\"},{\"presentation_key\":\"recovery_quality\",\"group_id\":\"recovery\",\"order\":4,\"label_en\":\"Recovery quality\",\"label_zh\":\"修复质量\",\"question_en\":\"Check the recovery\",\"question_zh\":\"检查修复\",\"aliases\":[\"recovery\",\"confirmation\",\"quality\",\"修复\",\"确认\"],\"analytical_scope\":\"owner profile; partial coverage\",\"page_id\":\"macro:intl\",\"existing_route\":\"/intl.html\"},{\"presentation_key\":\"participation_concentration\",\"group_id\":\"recovery\",\"order\":5,\"label_en\":\"Participation & concentration\",\"label_zh\":\"参与度与集中度\",\"question_en\":\"Check the recovery\",\"question_zh\":\"检查修复\",\"aliases\":[\"breadth\",\"constituents\",\"广度\",\"成分股\",\"集中度\"],\"analytical_scope\":\"owner profile; no invented breadth\",\"page_id\":\"macro:intl\",\"existing_route\":\"/intl.html\"},{\"presentation_key\":\"rates_curves_carry\",\"group_id\":\"policy\",\"order\":6,\"label_en\":\"Rates, curves & carry\",\"label_zh\":\"利率、曲线与息差\",\"question_en\":\"Follow policy divergence\",\"question_zh\":\"跟踪政策分化\",\"aliases\":[\"rates\",\"yield\",\"curve\",\"carry\",\"利率\",\"收益率\",\"曲线\",\"息差\"],\"analytical_scope\":\"seven-market plus US anchor\",\"page_id\":\"macro:intl\",\"existing_route\":\"/intl.html\"},{\"presentation_key\":\"central_banks_liquidity\",\"group_id\":\"policy\",\"order\":7,\"label_en\":\"Central banks & liquidity\",\"label_zh\":\"央行与流动性\",\"question_en\":\"Follow policy divergence\",\"question_zh\":\"跟踪政策分化\",\"aliases\":[\"central\",\"banks\",\"policy\",\"liquidity\",\"央行\",\"政策\",\"流动性\"],\"analytical_scope\":\"central-bank roster; proxies labeled\",\"page_id\":\"macro:intl\",\"existing_route\":\"/intl.html\"},{\"presentation_key\":\"credit_bonds\",\"group_id\":\"policy\",\"order\":8,\"label_en\":\"Credit & bonds\",\"label_zh\":\"信用与债券\",\"question_en\":\"Follow policy divergence\",\"question_zh\":\"跟踪政策分化\",\"aliases\":[\"credit\",\"bonds\",\"spreads\",\"信用\",\"债券\",\"利差\"],\"analytical_scope\":\"sovereign and EM regional; not country-credit substitute\",\"page_id\":\"macro:intl\",\"existing_route\":\"/intl.html\"},{\"presentation_key\":\"euro_fragmentation\",\"group_id\":\"backdrop\",\"order\":9,\"label_en\":\"Euro-area fragmentation\",\"label_zh\":\"欧元区分化\",\"question_en\":\"Understand the backdrop\",\"question_zh\":\"理解背景\",\"aliases\":[\"euro\",\"fragmentation\",\"欧元区\",\"分化\"],\"analytical_scope\":\"EZ regional context; preserve Japan on return\",\"page_id\":\"macro:intl\",\"existing_route\":\"/intl.html\"},{\"presentation_key\":\"growth_inflation\",\"group_id\":\"backdrop\",\"order\":10,\"label_en\":\"Growth & inflation\",\"label_zh\":\"增长与通胀\",\"question_en\":\"Understand the backdrop\",\"question_zh\":\"理解背景\",\"aliases\":[\"growth\",\"inflation\",\"cycle\",\"GDP\",\"CPI\",\"增长\",\"通胀\",\"周期\"],\"analytical_scope\":\"qualified core; unclassified visible\",\"page_id\":\"macro:intl\",\"existing_route\":\"/intl.html\"},{\"presentation_key\":\"dollar_conditions\",\"group_id\":\"backdrop\",\"order\":11,\"label_en\":\"Dollar conditions\",\"label_zh\":\"美元环境\",\"question_en\":\"Understand the backdrop\",\"question_zh\":\"理解背景\",\"aliases\":[\"dollar\",\"funding\",\"USD\",\"美元\",\"融资\"],\"analytical_scope\":\"global context; distinguish source families\",\"page_id\":\"macro:intl\",\"existing_route\":\"/intl.html\"},{\"presentation_key\":\"structural_fragility\",\"group_id\":\"pressure\",\"order\":12,\"label_en\":\"Structural fragility\",\"label_zh\":\"结构性脆弱性\",\"question_en\":\"Trace the pressure\",\"question_zh\":\"追踪压力\",\"aliases\":[\"fragility\",\"debt\",\"current\",\"account\",\"脆弱\",\"债务\",\"经常账户\"],\"analytical_scope\":\"IMF country roster; qualified vintage\",\"page_id\":\"macro:intl\",\"existing_route\":\"/intl.html\"},{\"presentation_key\":\"contagion\",\"group_id\":\"pressure\",\"order\":13,\"label_en\":\"Contagion\",\"label_zh\":\"传导\",\"question_en\":\"Trace the pressure\",\"question_zh\":\"追踪压力\",\"aliases\":[\"contagion\",\"spillover\",\"transmission\",\"传导\",\"溢出\"],\"analytical_scope\":\"distinct statistical and EM-US methods\",\"page_id\":\"macro:intl\",\"existing_route\":\"/intl.html\"},{\"presentation_key\":\"trade_supply_links\",\"group_id\":\"pressure\",\"order\":14,\"label_en\":\"Trade & supply links\",\"label_zh\":\"贸易与供应链联系\",\"question_en\":\"Trace the pressure\",\"question_zh\":\"追踪压力\",\"aliases\":[\"trade\",\"supply\",\"chain\",\"exposure\",\"贸易\",\"供应链\",\"敞口\"],\"analytical_scope\":\"model context is not documented company exposure\",\"page_id\":\"macro:intl\",\"existing_route\":\"/intl.html\"},{\"presentation_key\":\"cross_market_correlation\",\"group_id\":\"challenge\",\"order\":15,\"label_en\":\"Cross-market correlation\",\"label_zh\":\"跨市场相关性\",\"question_en\":\"Challenge the conclusion\",\"question_zh\":\"检验结论\",\"aliases\":[\"correlation\",\"diversification\",\"相关性\",\"分散\"],\"analytical_scope\":\"qualified weekly USD population; not causality\",\"page_id\":\"macro:intl\",\"existing_route\":\"/intl.html\"},{\"presentation_key\":\"risk_track_record\",\"group_id\":\"challenge\",\"order\":16,\"label_en\":\"Risk-radar track record\",\"label_zh\":\"风险雷达记录\",\"question_en\":\"Challenge the conclusion\",\"question_zh\":\"检验结论\",\"aliases\":[\"track\",\"record\",\"false\",\"alarms\",\"accuracy\",\"记录\",\"误报\",\"验证\"],\"analytical_scope\":\"market profile; sample and authority gate\",\"page_id\":\"macro:intl\",\"existing_route\":\"/intl.html\"},{\"presentation_key\":\"country_sectors_stocks\",\"group_id\":\"challenge\",\"order\":17,\"label_en\":\"Country sectors & stocks\",\"label_zh\":\"经济体板块与股票\",\"question_en\":\"Challenge the conclusion\",\"question_zh\":\"检验结论\",\"aliases\":[\"sectors\",\"stocks\",\"industry\",\"板块\",\"股票\",\"行业\"],\"analytical_scope\":\"existing stock universe; no assumed market filter\",\"page_id\":\"macro:intl_stocks\",\"existing_route\":\"/intl_stocks.html\"}]}"
BINDINGS = json.loads(BINDINGS_JSON)
KEYS = [tool["presentation_key"] for tool in BINDINGS["tools"]]
CONTEXT = {
    "research_market": "JP",
    "market_ids": ["CA", "FR", "DE", "JP", "UK", "US", "EZ"],
    "horizon": "1y",
    "horizons": ["1y", "3y", "5y"],
    "currency_basis": "usd_unhedged",
    "return_basis": "price",
    "source_reference": None,
}


def route_bindings():
    targets = {}
    for tool in BINDINGS["tools"]:
        targets[tool["presentation_key"]] = {
            "page_id": tool["page_id"],
            "route": tool["existing_route"],
            "region_id": "US" if tool["page_id"] != "macro:intl_stocks" else None,
            "verified": True,
        }
    return {"bindings": copy.deepcopy(BINDINGS), "targets": targets}


def decision(keys, **changes):
    value = {
        "scope": "public_product_copy",
        "copy_sha256": public_intl_library_copy_sha256(BINDINGS),
        "approved_tool_keys": list(keys),
        "owner_ref": "catalogue-owner",
        "decision_ref": "decision-17",
    }
    value.update(changes)
    return value


def oracle_digest(bindings):
    fields = (
        "presentation_key", "group_id", "order", "label_en", "label_zh",
        "question_en", "question_zh", "aliases", "analytical_scope",
        "page_id", "existing_route",
    )
    projection = {
        "schema": bindings["schema"],
        "groups": [
            {field: group[field] for field in ("id", "label_en", "label_zh")}
            for group in bindings["groups"]
        ],
        "tools": [
            {field: tool[field] for field in fields}
            for tool in sorted(bindings["tools"], key=lambda item: item["order"])
        ],
    }
    raw = json.dumps(projection, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def test_canonical_digest_matches_raw_fixture():
    assert public_intl_library_copy_sha256(BINDINGS) == oracle_digest(BINDINGS)
    assert len(BINDINGS["groups"]) == 6
    assert len(BINDINGS["tools"]) == 18


def test_copy_digest_is_independent_of_context_and_approval():
    digest = public_intl_library_copy_sha256(BINDINGS)
    first = build_public_intl_library_view(
        CONTEXT, route_bindings=route_bindings(), public_copy_decision=decision(KEYS[:2])
    )
    other_context = copy.deepcopy(CONTEXT)
    other_context.update(research_market="EZ", horizon="3y")
    second = build_public_intl_library_view(
        other_context, route_bindings=route_bindings(), public_copy_decision=decision(KEYS[2:])
    )
    assert first["catalogue_source_reference"] == f"public-copy:sha256:{digest}"
    assert first["catalogue_generation"] == second["catalogue_generation"] == f"public-copy:sha256:{digest}"


@pytest.mark.parametrize("field,value", [
    ("label_zh", "tampered"),
    ("aliases", ["changed"]),
    ("group_id", "policy"),
    ("order", 16),
])
def test_copy_digest_binds_catalogue_fields(field, value):
    copied = copy.deepcopy(BINDINGS)
    if field == "group_id":
        copied["tools"][0]["group_id"] = "recovery"
        copied["tools"][3]["group_id"] = "leaders"
    elif field == "order":
        copied["tools"][0]["order"], copied["tools"][1]["order"] = 1, 0
    else:
        copied["tools"][0][field] = value
    assert public_intl_library_copy_sha256(copied) != public_intl_library_copy_sha256(BINDINGS)


def test_partial_none_and_full_approval_redaction():
    partial = build_public_intl_library_view(
        CONTEXT, route_bindings=route_bindings(), public_copy_decision=decision(["euro_fragmentation"])
    )
    none = build_public_intl_library_view(
        CONTEXT, route_bindings=route_bindings(), public_copy_decision=decision([])
    )
    full = build_public_intl_library_view(
        CONTEXT, route_bindings=route_bindings(), public_copy_decision=decision(KEYS)
    )
    assert [tool["presentation_key"] for tool in partial["tools"]] == ["euro_fragmentation"]
    assert none["tools"] == [] and none["catalogue_state"] == "unavailable"
    assert all(group == {"slot": index, "state": "withheld"} for index, group in enumerate(none["groups"]))
    assert len(full["tools"]) == 18 and full["catalogue_state"] == "available"
    assert all(tool["metrics"] == [] for tool in full["tools"])


def test_original_source_none_and_no_financial_or_rights_projection():
    result = build_public_intl_library_view(
        CONTEXT, route_bindings=route_bindings(), public_copy_decision=decision(KEYS)
    )
    assert result["context"]["source_reference"] is None
    assert result["context"].keys() == {
        "research_market", "horizon", "currency_basis", "return_basis", "source_reference"
    }
    assert not any(key in result for key in ("rights", "source_owner"))


@pytest.mark.parametrize("source", [False, {"source": "hostile"}])
def test_invalid_original_source_rejects_before_publication(source):
    context = copy.deepcopy(CONTEXT)
    context["source_reference"] = source
    with pytest.raises(ValueError):
        build_public_intl_library_view(
            context, route_bindings=route_bindings(), public_copy_decision=decision(KEYS)
        )


def test_extra_decision_metrics_and_duplicate_or_unknown_approvals_reject():
    with pytest.raises(ValueError):
        build_public_intl_library_view(
            CONTEXT, route_bindings=route_bindings(), public_copy_decision=decision(KEYS, metrics=[])
        )
    with pytest.raises(ValueError):
        build_public_intl_library_view(
            CONTEXT, route_bindings=route_bindings(),
            public_copy_decision=decision(["euro_fragmentation", "euro_fragmentation"]),
        )
    with pytest.raises(ValueError):
        build_public_intl_library_view(
            CONTEXT, route_bindings=route_bindings(), public_copy_decision=decision(["unknown"]),
        )


def test_getter_dict_rejects_before_getitem():
    accesses = []

    class GetterDict(dict):
        def __getitem__(self, key):
            accesses.append(key)
            return super().__getitem__(key)

    with pytest.raises(ValueError):
        build_public_intl_library_view(
            GetterDict(copy.deepcopy(CONTEXT)),
            route_bindings=route_bindings(),
            public_copy_decision=decision(KEYS),
        )
    assert accesses == []


def test_inputs_are_not_mutated():
    context = copy.deepcopy(CONTEXT)
    routes = route_bindings()
    chosen = decision(["euro_fragmentation", "country_sectors_stocks"])
    before = copy.deepcopy((context, routes, chosen))
    build_public_intl_library_view(context, route_bindings=routes, public_copy_decision=chosen)
    assert (context, routes, chosen) == before


def test_routes_and_special_context_are_preserved():
    result = build_public_intl_library_view(
        CONTEXT, route_bindings=route_bindings(), public_copy_decision=decision(KEYS)
    )
    tools = {tool["presentation_key"]: tool for tool in result["tools"]}
    assert tools["performance_currency"]["target"]["route"] == "/intl.html"
    assert tools["country_sectors_stocks"]["target"] == {
        "page_id": "macro:intl_stocks", "route": "/intl_stocks.html", "region_id": None
    }
    assert tools["euro_fragmentation"]["analytical_market"] == "EZ"
    assert tools["trade_supply_links"]["interpretation_notice"] == "model_context_not_company_exposure"
    assert tools["performance_currency"]["research_market"] == "JP"


def test_catalogue_identity_tracks_copy_instead_of_receipt_name():
    first = build_public_intl_library_view(
        CONTEXT, route_bindings=route_bindings(), public_copy_decision=decision(KEYS)
    )
    second = build_public_intl_library_view(
        CONTEXT, route_bindings=route_bindings(),
        public_copy_decision=decision(KEYS, decision_ref="a-distinct-review-receipt")
    )
    assert first["catalogue_generation"] == second["catalogue_generation"]
    assert first["catalogue_generation"] == first["catalogue_source_reference"]
    assert first["context"]["source_reference"] is None


def test_plain_json_gate_rejects_non_string_and_subclass_dictionary_keys():
    class Key(str):
        pass
    for key in (1, Key("extra")):
        bindings = copy.deepcopy(BINDINGS)
        bindings[key] = None
        with pytest.raises(ValueError, match="invalid_json:key"):
            public_intl_library_copy_sha256(bindings)


def test_ignored_json_integer_does_not_require_lossy_float_conversion():
    bindings = copy.deepcopy(BINDINGS)
    bindings["source_only_integer"] = 10 ** 4000
    assert public_intl_library_copy_sha256(bindings) == oracle_digest(BINDINGS)

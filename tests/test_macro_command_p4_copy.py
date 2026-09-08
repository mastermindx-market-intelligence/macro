"""Macro Command P4 — seven remaining sections: copy, riders, fail-closed.

Every §2 string is asserted by value (EN and ZH) on the built page or the
view. Riders: METRIC pool, consumer_payments tone, foot-note condition,
one-null-voice on E1, truthful housing/debt/trade stances, Q2 A/C pin.
"""
from __future__ import annotations

import copy
import json
import re
import shutil
from html import unescape
from pathlib import Path

from engine.market_os.macro_workspaces import contract as workspace_contract
from engine.market_os.macro_workspaces.financial_conditions import (
    BOUNDARY,
    _classify,
    _QUADRANTS,
)

import pytest

from lib import macro_suite_labels as L
from scripts import build_macro_suite_pages as builder
from scripts import check_macro_command_copy as guard

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "site" / "macrodata"
BUILT_AT = "2026-09-06T00:00:00Z"
P4_IDS = ("growth", "jobs", "housing", "consumer", "credit", "debt", "trade")
QUADRANTS = ("A", "B", "C", "D")
_CJK = re.compile(r"[\u4e00-\u9fff]")

# Pin §2 — every reviewed string, byte-for-byte.
_PINNED = {
    ("growth", "question"): (
        "Is the economy speeding up or slowing down?",
        "经济是在加快还是放缓？",
    ),
    ("growth", "stance.A"): (
        "Growth is still strong but slowing. Watch the pace, not the level, from here.",
        "增长依然强劲，但正在放缓。从这里开始，要盯的是速度而不是水平。",
    ),
    ("growth", "stance.B"): (
        "Growth is picking up and the pickup is broad. No action needed; watch for it narrowing.",
        "增长正在加快，而且面也广。今天无需行动，留意面是否收窄。",
    ),
    ("growth", "stance.C"): (
        "Growth is weak and still slowing. Read this section closely before anything else today.",
        "增长疲弱且仍在放缓。今天请先仔细读本板块，再看其他。",
    ),
    ("growth", "stance.D"): (
        "Growth is improving, but only in a few places. Watch — narrow pickups usually fade.",
        "增长在改善，但只集中在少数领域。观察为主 — 面窄的回升通常会退去。",
    ),
    ("growth", "primer"): (
        "Growth here means how fast the economy is expanding and how many parts of it are expanding together.",
        "这里的「增长」指经济扩张的速度，以及有多少领域在同步扩张。",
    ),
    ("growth", "caption"): (
        "Each row shows the last two readings. The tabs are not on one scale.",
        "每行显示最近两次读数。两个标签页衡量的不是同一件事。",
    ),
    ("growth", "watch.1"): (
        "If the pace slows while most gauges still rise, the slowdown is not broad yet.",
        "若速度放缓而多数指标仍在上行，说明放缓尚未扩散。",
    ),
    ("growth", "watch.2"): (
        "If company activity weakens before the wider economy does, the turn starts there.",
        "若企业活动先于整体经济走弱，转折就是从那里开始的。",
    ),
    ("jobs", "question"): (
        "How hard is it to hire, and how hard to find work?",
        "招人有多难？找工作又有多难？",
    ),
    ("jobs", "stance.A"): (
        "Jobs are still hard to fill, but hiring demand is cooling. Watch the demand side first.",
        "岗位依然难填，但招聘需求正在降温。请先盯需求这一侧。",
    ),
    ("jobs", "stance.B"): (
        "Employers are hiring hard and workers are scarce. No action needed; watch for demand cooling.",
        "企业招聘强劲，人手依然紧缺。今天无需行动，留意需求是否降温。",
    ),
    ("jobs", "stance.C"): (
        "Hiring demand is weak and workers are easy to find. Read this section closely today.",
        "招聘需求疲弱，人手很好找。今天请仔细读本板块。",
    ),
    ("jobs", "stance.D"): (
        "Hiring is picking up and there is still room to grow. No action needed today.",
        "招聘正在回升，而且仍有余量。今天无需行动。",
    ),
    ("jobs", "primer"): (
        "This section is about how hard it is for companies to hire, and how easily people find work.",
        "本板块讲的是企业招人的难度，以及人们找工作的难易程度。",
    ),
    ("jobs", "caption"): (
        "Each row shows the last two readings. Higher means a tighter job market.",
        "每行显示最近两次读数。数值更高表示就业市场更紧。",
    ),
    ("jobs", "watch.1"): (
        "If hiring demand falls while workers stay scarce, wage pressure lasts longer.",
        "若招聘需求下滑而人手仍然紧缺，薪资压力会持续更久。",
    ),
    ("jobs", "watch.2"): (
        "If both readings fall together, the job market is loosening for real.",
        "若两项读数同时下行，说明就业市场是真的在转松。",
    ),
    ("housing", "question"): (
        "What does it cost to buy, build and own a home?",
        "买房、建房与持有住房的成本是多少？",
    ),
    ("housing", "stance.unavailable"): (
        "No single housing reading is published. Mortgage costs, building activity and prices below are the read.",
        "房地产没有单一综合读数。要看的是下方的房贷成本、建筑活动与房价。",
    ),
    ("housing", "primer"): (
        "This section is about what it costs to borrow for a home, how much is being built, and where prices are.",
        "本板块讲的是买房借贷的成本、建了多少房，以及房价处在什么位置。",
    ),
    ("housing", "caption"): (
        "Each row shows the last two readings. Costs and volumes read differently.",
        "每行显示最近两次读数。成本与建量需分开来看。",
    ),
    ("housing", "watch.1"): (
        "If building permits fall while the mortgage rate holds, builders are stepping back.",
        "若营建许可下滑而房贷利率未动，说明开发商正在收手。",
    ),
    ("housing", "watch.2"): (
        "If prices keep rising while building slows, affordability gets worse, not better.",
        "若房价继续上涨而建设放缓，可负担性只会更差。",
    ),
    ("consumer", "question"): (
        "Are households spending, and can they keep it up?",
        "家庭还在消费吗？还能撑多久？",
    ),
    ("consumer", "stance.A"): (
        "Households are spending and their finances look comfortable. No action needed today.",
        "家庭在消费，财务状况也较为宽裕。今天无需行动。",
    ),
    ("consumer", "stance.B"): (
        "Households are still spending, but debt stress is high. Watch — this pairing rarely holds long.",
        "家庭仍在消费，但债务压力偏高。观察为主 — 这种组合通常撑不久。",
    ),
    ("consumer", "stance.C"): (
        "Spending has slowed, but household finances are still comfortable. Watch the spending side.",
        "消费已经放缓，但家庭财务仍较宽裕。请盯住消费这一侧。",
    ),
    ("consumer", "stance.D"): (
        "Spending has slowed and debt stress is high. Read this section closely before anything else.",
        "消费放缓且债务压力偏高。请先仔细读本板块，再看其他。",
    ),
    ("consumer", "primer"): (
        "This section is about how much households are spending and how comfortably they can carry their debts.",
        "本板块讲的是家庭花了多少钱，以及他们背负债务的轻松程度。",
    ),
    ("consumer", "caption"): (
        "Each row shows the last two readings. Read spending and stress separately.",
        "每行显示最近两次读数。消费与压力需分开来看。",
    ),
    ("consumer", "watch.1"): (
        "If stress keeps rising while spending holds, the spending is being borrowed.",
        "若压力持续上升而消费未减，说明这些消费是借来的。",
    ),
    ("consumer", "watch.2"): (
        "If spending falls first, households are pulling back before the debt bites.",
        "若消费先行下滑，说明家庭在债务咬人之前就已收手。",
    ),
    ("credit", "question"): (
        "How expensive and how hard is it to borrow?",
        "借钱有多贵？又有多难？",
    ),
    ("credit", "stance.A"): (
        "Borrowing is cheap and getting cheaper. No action needed today; watch for the turn.",
        "借钱便宜，而且还在变便宜。今天无需行动，留意何时转向。",
    ),
    ("credit", "stance.B"): (
        "Borrowing is expensive and getting harder. Read this section closely before anything else today.",
        "借钱成本偏高，而且越来越难。今天请先仔细读本板块，再看其他。",
    ),
    ("credit", "stance.C"): (
        "Borrowing is still cheap, but it is getting less so. Watch the direction, not the level.",
        "借钱仍然便宜，但正在变贵。要盯的是方向，而不是水平。",
    ),
    ("credit", "stance.D"): (
        "Borrowing is expensive but easing. Watch whether the easing reaches company funding.",
        "借钱成本仍高，但正在放松。留意这份放松是否传导到企业融资。",
    ),
    ("credit", "primer"): (
        "This section is about how expensive and how hard it is for companies to borrow right now.",
        "本板块讲的是企业当下借钱的成本有多高、难度有多大。",
    ),
    ("credit", "caption"): (
        "Each row shows the last two readings. The tabs are not on one scale.",
        "每行显示最近两次读数。两个标签页衡量的不是同一件事。",
    ),
    ("credit", "watch.1"): (
        "If conditions tighten while companies keep issuing, the pressure has not reached them yet.",
        "若融资条件收紧而企业仍在照常发债，说明压力尚未传导到它们身上。",
    ),
    ("credit", "watch.2"): (
        "If issuing slows first, borrowers are stepping back before the price moves.",
        "若发行先行放缓，说明借款人在价格变动前就已收手。",
    ),
    ("debt", "question"): (
        "How much is the government borrowing, and who is buying?",
        "政府借了多少？又是谁在买？",
    ),
    ("debt", "stance.unavailable"): (
        "No single debt reading is published. Watch the cash balance, new issuance and auction demand below.",
        "政府债务没有单一综合读数。请看下方的现金余额、新发行与拍卖需求。",
    ),
    ("debt", "primer"): (
        "This section is about how much the government is borrowing and how easily that debt finds buyers.",
        "本板块讲的是政府借了多少钱，以及这些债务找到买家的难易程度。",
    ),
    ("debt", "caption"): (
        "Each row shows the last two readings. More issuance is more debt to place.",
        "每行显示最近两次读数。发行越多，需要消化的债务就越多。",
    ),
    ("debt", "watch.1"): (
        "If auction demand falls while issuance rises, buyers are asking for a better price.",
        "若拍卖需求下滑而发行量上升，说明买方在要求更好的价格。",
    ),
    ("debt", "watch.2"): (
        "If the cash balance is rebuilt quickly, that money comes out of the market.",
        "若现金余额被快速补回，这些钱就是从市场里抽走的。",
    ),
    ("trade", "question"): (
        "What is the country buying and selling abroad?",
        "这个国家在海外买什么、卖什么？",
    ),
    ("trade", "stance.unstated"): (
        "No single trade reading is published here. The balance, exports and imports below are the read.",
        "贸易往来此处不发布单一读数。下方的差额、出口与进口就是要看的内容。",
    ),
    ("trade", "primer"): (
        "This section is about what the country sells abroad, what it buys, and the gap between the two.",
        "本板块讲的是这个国家向海外卖了什么、买了什么，以及两者之间的差额。",
    ),
    ("trade", "caption"): (
        "Each row shows the last two readings. Imports above exports is a deficit.",
        "每行显示最近两次读数。进口大于出口即为逆差。",
    ),
    ("trade", "watch.1"): (
        "If imports rise while exports flatten, the gap widens without demand improving.",
        "若进口上升而出口走平，差额会在需求未改善的情况下扩大。",
    ),
    ("trade", "watch.2"): (
        "If both fall together, trade is slowing rather than rebalancing.",
        "若两者同时下滑，说明贸易是在放缓，而不是在再平衡。",
    ),
    ("FOOT", "stale"): (
        "Some inputs are not current today — see details.",
        "今天部分输入并非最新 — 详见细节。",
    ),
    ("FOOT", "disagree"): (
        "Some inputs disagree today — see details.",
        "今天部分输入相互矛盾 — 详见细节。",
    ),
}


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> tuple[str, Path]:
    out = tmp_path_factory.mktemp("macro_command_p4") / "site"
    pages = builder.render(ROOT, data_root=DATA_ROOT, out_dir=out, page_built_at=BUILT_AT)
    hub = [p for p in pages if p.name == builder.HUB_PAGE.output]
    assert hub, "the builder did not write macro_monetary.html"
    return hub[0].read_text(encoding="utf-8"), out


def _panel(html: str, section_id: str) -> str:
    match = re.search(
        r'<section class="mc-panel" id="' + section_id + r'".*?(?=<section class="mc-panel"|</main>)',
        html, re.S)
    assert match, section_id
    return match.group(0)


def _live_entries() -> list[dict]:
    entries = []
    for page in builder.SUITE_PAGES:
        identity = builder._identity(page)
        snapshot, _artifact = builder.read_workspace(DATA_ROOT, page)
        entries.append({
            "workspace_id": page.workspace_id,
            "region": page.region,
            "output": page.output,
            "title": identity["title"],
            "subtitle": identity["subtitle"],
            "snapshot": snapshot,
            "failure": None,
        })
    return entries


def test_copy_ids_is_the_twelve_and_primers_stay_the_first_three() -> None:
    assert builder.COPY_IDS == frozenset({
        "overview", "money", "policy", "rates", "inflation",
        "growth", "jobs", "housing", "consumer", "credit", "debt", "trade",
    })
    assert builder.P3_PRIMER_OPEN == frozenset({"overview", "money", "policy"})
    assert not hasattr(builder, "P3_COPY_IDS")


def test_pinned_copy_tables_are_byte_for_byte() -> None:
    for (section_id, key), (en, zh) in _PINNED.items():
        if section_id == "FOOT":
            pair = L.FOOT[key]
        elif key == "question":
            section = next(s for s in builder.SECTIONS if s.id == section_id)
            assert section.question_en == en
            assert section.question_zh == zh
            continue
        elif key.startswith("stance."):
            pair = L.STANCES[section_id][key.split(".", 1)[1]]
        elif key == "primer":
            pair = L.PRIMERS[section_id]
        elif key == "caption":
            pair = L.CAPTIONS[section_id]
        elif key.startswith("watch."):
            pair = L.WATCHING[section_id][int(key.split(".", 1)[1]) - 1]
        else:
            raise AssertionError(key)
        assert pair["en"] == en, (section_id, key)
        assert pair["zh"] == zh, (section_id, key)


def test_p4_copy_budgets() -> None:
    for section_id in P4_IDS:
        for key, pair in L.STANCES[section_id].items():
            assert len(pair["en"].split()) <= 20, (section_id, key)
            assert len(pair["en"]) <= 110, (section_id, key, len(pair["en"]))
            assert len(_CJK.findall(pair["zh"])) <= 34, (section_id, key)
        caption = L.CAPTIONS[section_id]
        assert len(caption["en"].split()) <= 14, section_id
        assert len(caption["en"]) <= 74, (section_id, len(caption["en"]))
        assert len(_CJK.findall(caption["zh"])) <= 40, section_id
        primer = L.PRIMERS[section_id]
        assert len(primer["en"].split()) <= 45, section_id
        for bullet in L.WATCHING[section_id]:
            assert len(bullet["en"].split()) <= 16, (section_id, bullet["en"])
            assert len(_CJK.findall(bullet["zh"])) <= 40, section_id
        section = next(s for s in builder.SECTIONS if s.id == section_id)
        assert len(section.question_en.split()) <= 14, section_id


def test_quadrant_tables_carry_every_emitted_key() -> None:
    for section_id in ("growth", "jobs", "consumer", "credit"):
        assert set(L.STANCES[section_id]) == set(QUADRANTS) | {"unstated", "unavailable"}
    for section_id in ("housing", "debt"):
        assert set(L.STANCES[section_id]) == {"unstated", "unavailable"}
        assert L.STANCES[section_id]["unavailable"]["en"] != L._UNAVAILABLE["en"]
    assert set(L.STANCES["trade"]) == {"unstated", "unavailable"}
    assert L.STANCES["trade"]["unstated"]["en"] != L._UNSTATED_GENERIC["en"]
    assert L.STANCES["trade"]["unavailable"] is L._UNAVAILABLE


def test_required_metric_pairs_and_rewordings() -> None:
    assert L.METRIC["conditions_level"] == {
        "en": "Tightness of borrowing conditions",
        "zh": "融资条件的紧张程度",
    }
    assert L.METRIC["conditions_impulse"] == {
        "en": "Direction of borrowing conditions",
        "zh": "融资条件的变化方向",
    }
    assert L.METRIC["financial_conditions_level"] == L.METRIC["conditions_level"]
    assert L.METRIC["financial_conditions_impulse"] == L.METRIC["conditions_impulse"]
    assert L.METRIC["growth_level_breadth"] == {
        "en": "Strength and breadth of growth",
        "zh": "增长的强度与广度",
    }
    assert L.METRIC["labor_demand"] == {
        "en": "Employer demand for workers",
        "zh": "企业对劳动力的需求",
    }
    assert L.METRIC["labor_supply_tightness"] == {
        "en": "Tightness of the job market",
        "zh": "就业市场的紧张程度",
    }


def test_consumer_payments_tone_row() -> None:
    assert L.STATE_TONE["consumer_payments"] == {
        "A": "ok", "B": "warn", "C": "warn", "D": "bad",
    }


def test_financial_conditions_a_c_match_composer_quadrants() -> None:
    """Q2 / M5: all four keys, both locales, pinned to the composer's tables."""
    assert _classify(0.0, 0.0) == "A"
    assert _classify(BOUNDARY, BOUNDARY) == "B"
    assert _classify(0.0, BOUNDARY) == "C"
    assert _classify(BOUNDARY, 0.0) == "D"
    expected_word = {
        "A": ("Easy and easing", "宽松且续松"),
        "B": ("Tight and tightening", "偏紧且续紧"),
        "C": ("Easy but tightening", "宽松但转紧"),
        "D": ("Tight but easing", "偏紧但转松"),
    }
    expected_predicate = {
        "A": ("is cheap and getting cheaper", "便宜，而且还在变便宜"),
        "B": ("is expensive and getting harder", "成本偏高，而且越来越难"),
        "C": ("is still cheap but getting less so", "仍然便宜，但正在变贵"),
        "D": ("is expensive but easing", "成本仍高，但正在放松"),
    }
    expected_tone = {"A": "ok", "B": "bad", "C": "warn", "D": "warn"}
    expected_quadrant = {
        "A": ("Easy conditions / Easing impulse", "宽松条件 / 边际放松"),
        "B": ("Tight conditions / Tightening impulse", "紧张条件 / 边际收紧"),
        "C": ("Easy conditions / Tightening impulse", "宽松条件 / 边际收紧"),
        "D": ("Tight conditions / Easing impulse", "紧张条件 / 边际放松"),
    }
    for key in QUADRANTS:
        assert _QUADRANTS[key]["en"] == expected_quadrant[key][0], key
        assert _QUADRANTS[key]["zh"] == expected_quadrant[key][1], key
        assert L.STATE_WORD["financial_conditions"][key]["en"] == expected_word[key][0], key
        assert L.STATE_WORD["financial_conditions"][key]["zh"] == expected_word[key][1], key
        assert L.PREDICATE_FORM["financial_conditions"][key]["en"] == expected_predicate[key][0], key
        assert L.PREDICATE_FORM["financial_conditions"][key]["zh"] == expected_predicate[key][1], key
        assert L.STATE_TONE["financial_conditions"][key] == expected_tone[key], key


def test_live_page_carries_every_emitted_p4_string(built: tuple[str, Path]) -> None:
    html, _ = built
    plain = unescape(html)
    live = {
        "growth": "stance.B",
        "jobs": "stance.B",
        "housing": "stance.unavailable",
        "consumer": "stance.B",
        "credit": "stance.B",
        "debt": "stance.unavailable",
        "trade": "stance.unstated",
    }
    for section_id, stance_key in live.items():
        panel = unescape(_panel(plain, section_id))
        keys = ["question", stance_key, "primer", "watch.1", "watch.2"]
        # I4 drops the caption on current-only figures; the state line lives
        # in the fragment for sub-tabbed sections, so do not require caption
        # on the hub panel. The I4 tests pin the drop.
        if 'class="mc-caption' in panel:
            keys.append("caption")
        for key in keys:
            en, zh = _PINNED[(section_id, key)]
            assert en in panel, (section_id, key, en)
            assert zh in panel, (section_id, key, zh)
        if 'class="mc-caption' not in panel:
            assert "Each row shows the last two readings" not in panel
            assert "compared against the previous publication" not in panel
    assert _PINNED[("FOOT", "disagree")][0] in unescape(_panel(plain, "growth"))
    assert _PINNED[("FOOT", "disagree")][1] in unescape(_panel(plain, "growth"))
    assert _PINNED[("FOOT", "stale")][0] in unescape(_panel(plain, "consumer"))
    assert _PINNED[("FOOT", "stale")][1] in unescape(_panel(plain, "consumer"))
    inflation = unescape(_panel(plain, "inflation"))
    assert _PINNED[("FOOT", "stale")][0] in inflation
    assert _PINNED[("FOOT", "disagree")][0] not in inflation


def test_quadrant_copy_that_is_not_live_today_is_on_the_view() -> None:
    """A/C/D are not today's published states — still asserted on the tables
    and on a fabricated view so a later state cannot ship unpinned."""
    entries = copy.deepcopy(_live_entries())
    for entry in entries:
        if entry["workspace_id"] == "growth_real_economy":
            entry["snapshot"]["headline"]["state_id"] = "C"
    sections = builder._macro_command_sections(entries, page_built_at=BUILT_AT)
    growth = next(s for s in sections if s["id"] == "growth")
    assert growth["stance"]["text"]["en"] == _PINNED[("growth", "stance.C")][0]
    assert growth["stance"]["text"]["zh"] == _PINNED[("growth", "stance.C")][1]
    for section_id in ("growth", "jobs", "consumer", "credit"):
        for letter in QUADRANTS:
            en, zh = _PINNED[(section_id, f"stance.{letter}")]
            assert L.STANCES[section_id][letter]["en"] == en
            assert L.STANCES[section_id][letter]["zh"] == zh


def test_fabricated_stance_key_raises_and_writes_no_page(tmp_path: Path) -> None:
    out = tmp_path / "site"
    out.mkdir()
    entries = []
    for page in builder.SUITE_PAGES:
        snap = None
        if page.workspace_id == "growth_real_economy":
            snap = {
                "workspace": {"id": page.workspace_id},
                "headline": {"status": "PRESENT", "state_id": "Z",
                             "effective_date": "2026-09-04"},
                "changes": {"comparability": "COMPARABLE", "deltas": []},
            }
        entries.append({
            "workspace_id": page.workspace_id, "region": "US",
            "output": page.output,
            "title": {"en": page.workspace_id, "zh": page.workspace_id},
            "subtitle": {"en": "", "zh": ""},
            "snapshot": snap, "failure": None if snap else {"kind": "NOT_COVERED"},
        })
    with pytest.raises(builder.MacroCommandBuildError, match="unknown stance key growth/Z"):
        builder._macro_command_sections(entries, page_built_at=BUILT_AT)
    assert not (out / "macro_monetary.html").exists()


def test_unmapped_metric_still_raises() -> None:
    deltas = [{
        "metric_id": "not_a_reviewed_metric",
        "label": {"en": "Nope", "zh": "Nope"},
        "prior_present": True, "current_present": True, "delta_present": True,
        "prior": "1", "current": "2", "delta": "+1", "sign": "up",
    }]
    with pytest.raises(builder.MacroCommandBuildError, match="unmapped metric_id"):
        builder._move_rows_from_deltas(deltas, href="x.html", show_source=None)


def test_boundary_axis_conditions_impulse_is_in_the_metric_pool() -> None:
    builder._require_metric("conditions_impulse")
    builder._require_metric("conditions_level")


def test_consumer_tone_is_warn_on_live_b(built: tuple[str, Path]) -> None:
    html, _ = built
    consumer = _panel(html, "consumer")
    assert "mq-tone-warn" in consumer
    assert "mq-tone-neutral" not in re.search(
        r'class="mc-stance ([^"]+)"', consumer).group(1)


def test_input_note_stale_wins_over_disagree() -> None:
    view = {"diagnostics": [
        {"tone": "bad", "title": {"en": "Contradictory signals"}},
        {"tone": "warn", "title": {"en": "Required source not current"}},
    ]}
    assert builder._input_note_from_view(view) == "stale"
    assert builder._input_note_from_view(
        {"diagnostics": [{"tone": "bad", "title": {"en": "Contradictory signals"}}]}
    ) == "disagree"
    assert builder._input_note_from_view({"diagnostics": []}) is None
    assert builder._input_note_pair("disagree", "stale") == dict(L.FOOT["stale"])
    assert builder._input_note_pair("disagree") == dict(L.FOOT["disagree"])


def _write_housing_fixture(data_root: Path, *, dated: bool) -> None:
    victim = data_root / "workspaces" / "housing_real_estate" / "US" / "latest.json"
    snap = json.loads(victim.read_text(encoding="utf-8"))
    if not dated:
        snap["headline"]["effective_date"] = None
        snap["headline"]["status"] = "ABSENT"
        snap["headline"]["null_reason"] = "NOT_YET_RELEASED"
    snap["changes"]["deltas"] = []
    snap["changes"]["comparability"] = "NO_PRIOR"
    snap["changes"]["status"] = "ABSENT"
    snap["changes"]["null_reason"] = "INSUFFICIENT_HISTORY"
    sealed = workspace_contract.finalize(snap)
    raw = json.dumps(sealed, ensure_ascii=False).encode("utf-8")
    victim.write_bytes(raw)
    manifest_path = data_root / "workspaces" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = manifest["workspaces"]["housing_real_estate/US"]
    entry["content_sha256"] = sealed["generation"]["content_sha256"]
    entry["bytes"] = len(raw)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


def test_e1_on_housing_uses_the_empty_title_and_drops_caption(tmp_path: Path) -> None:
    data_root = tmp_path / "macrodata"
    shutil.copytree(DATA_ROOT, data_root)
    _write_housing_fixture(data_root, dated=False)
    out = tmp_path / "site"
    builder.render(ROOT, data_root=data_root, out_dir=out, page_built_at=BUILT_AT)
    html = unescape((out / "macro_monetary.html").read_text(encoding="utf-8"))
    housing = _panel(html, "housing")
    frag = unescape((out / "macro" / "fragments" / "housing.html").read_text(encoding="utf-8"))
    assert 'data-mc-empty="e1"' in frag
    assert "We don't have this reading yet" in housing
    assert "No single housing reading is published" not in housing
    assert "Each row shows the last two readings" not in housing
    assert "class=\"mc-caption\"" not in housing


def test_e2_on_housing_uses_the_empty_title(tmp_path: Path) -> None:
    entries = copy.deepcopy(_live_entries())
    for entry in entries:
        if entry["workspace_id"] == "housing_real_estate":
            entry["snapshot"]["availability"]["state"] = "SOURCE_FAILED"
            entry["snapshot"]["headline"]["status"] = "ABSENT"
            entry["snapshot"]["headline"]["state_id"] = None
            entry["snapshot"]["headline"]["effective_date"] = None
            entry["snapshot"]["changes"]["deltas"] = []
    sections = builder._macro_command_sections(entries, page_built_at=BUILT_AT)
    housing = next(s for s in sections if s["id"] == "housing")
    assert housing["empty"]["id"] == "e2"
    assert housing["stance"]["text"]["en"] == L.EMPTY_STATES["e2"]["title"]["en"]
    assert housing["stance"]["tone"] == "neutral"
    assert housing["caption"] is None


def test_subtab_e1_uses_the_stance_tab_empty_title() -> None:
    entries = copy.deepcopy(_live_entries())
    for entry in entries:
        if entry["workspace_id"] == "business_activity":
            entry["snapshot"]["headline"]["status"] = "ABSENT"
            entry["snapshot"]["headline"]["state_id"] = None
        if entry["workspace_id"] == "growth_real_economy":
            entry["snapshot"]["headline"]["effective_date"] = None
            entry["snapshot"]["headline"]["status"] = "ABSENT"
            entry["snapshot"]["headline"]["state_id"] = None
            entry["snapshot"]["headline"]["null_reason"] = "NOT_YET_RELEASED"
            entry["snapshot"]["changes"]["deltas"] = []
            entry["snapshot"]["changes"]["comparability"] = "NO_PRIOR"
    sections = builder._macro_command_sections(entries, page_built_at=BUILT_AT)
    growth = next(s for s in sections if s["id"] == "growth")
    assert growth["empty"] is None
    economy = next(t for t in growth["subtabs"] if t["id"] == "economy")
    assert economy["empty"]["id"] == "e1"
    assert growth["stance"]["text"]["en"] == L.EMPTY_STATES["e1"]["title"]["en"]
    assert growth["stance"]["tone"] == "neutral"
    assert growth["caption"] is None


def test_credit_subtab_e2_uses_the_stance_tab_empty_title() -> None:
    entries = copy.deepcopy(_live_entries())
    for entry in entries:
        if entry["workspace_id"] == "capital_structure":
            entry["snapshot"]["headline"]["status"] = "ABSENT"
            entry["snapshot"]["headline"]["state_id"] = None
        if entry["workspace_id"] == "financial_conditions":
            entry["snapshot"]["availability"]["state"] = "STALE_SOURCE"
            entry["snapshot"]["headline"]["status"] = "ABSENT"
            entry["snapshot"]["headline"]["state_id"] = None
            entry["snapshot"]["headline"]["effective_date"] = None
            entry["snapshot"]["changes"]["deltas"] = []
    sections = builder._macro_command_sections(entries, page_built_at=BUILT_AT)
    credit = next(s for s in sections if s["id"] == "credit")
    borrowing = next(t for t in credit["subtabs"] if t["id"] == "borrowing")
    assert borrowing["empty"]["id"] == "e2"
    assert credit["stance"]["text"]["en"] == L.EMPTY_STATES["e2"]["title"]["en"]
    assert credit["caption"] is None


def test_bilingual_parity_and_no_zh_in_title(built: tuple[str, Path]) -> None:
    html, _ = built
    assert html.count('class="l-en"') == html.count('class="l-zh"')
    for attr in re.findall(r'title="([^"]*)"', html):
        assert not _CJK.search(attr), attr


def test_copy_guard_green_on_built_page(built: tuple[str, Path]) -> None:
    html, _ = built
    assert guard.find_violations(html) == []


def test_not_applicable_trade_is_unstated_not_e1(built: tuple[str, Path]) -> None:
    html, _ = built
    trade = unescape(_panel(html, "trade"))
    assert 'data-mc-empty="e1"' not in trade
    assert _PINNED[("trade", "stance.unstated")][0] in trade
    assert "This desk could not be read today" not in trade


def test_credit_funding_e4_needs_the_capture_fixture_flag() -> None:
    """P3 v5: withheld_command_tabs is fixture-only; credit/funding E4 needs the flag."""
    entries = copy.deepcopy(_live_entries())
    for entry in entries:
        if entry["workspace_id"] == "capital_structure":
            entry["snapshot"]["withheld_command_tabs"] = ["funding"]
    closed = builder._macro_command_sections(entries, page_built_at=BUILT_AT)
    closed_credit = next(s for s in closed if s["id"] == "credit")
    closed_funding = next(t for t in closed_credit["subtabs"] if t["id"] == "funding")
    assert closed_funding["empty"] is None
    open_ = builder._macro_command_sections(
        entries, page_built_at=BUILT_AT, allow_empty_state_fixture=True)
    credit = next(s for s in open_ if s["id"] == "credit")
    funding = next(t for t in credit["subtabs"] if t["id"] == "funding")
    assert funding["empty"]["id"] == "e4"
    assert funding["empty"]["title"]["en"] == L.EMPTY_STATES["e4"]["title"]["en"]
    assert funding["empty"]["title"]["zh"] == L.EMPTY_STATES["e4"]["title"]["zh"]
    assert funding["figure"] is None
    assert credit["caption"] is None


def test_growth_caption_matches_credit_scale_disclaimer() -> None:
    """M4: growth uses the credit pattern — tabs are not on one scale."""
    assert L.CAPTIONS["growth"] == L.CAPTIONS["credit"]
    assert L.CAPTIONS["growth"]["en"] == (
        "Each row shows the last two readings. The tabs are not on one scale.")
    assert L.CAPTIONS["growth"]["zh"] == "每行显示最近两次读数。两个标签页衡量的不是同一件事。"


CURRENT_ONLY_EN = (
    "Only one reading is published so far — nothing earlier to compare yet.")
CURRENT_ONLY_ZH = "目前只有一次读数——暂无更早读数可比。"
MIXED_PAIR_EN = "Some readings have no earlier print to compare yet."
MIXED_PAIR_ZH = "部分读数暂无更早读数可比。"


def _iter_p4_figures(sections: list[dict]) -> list[tuple[str, dict]]:
    found: list[tuple[str, dict]] = []
    for section in sections:
        if section["id"] not in P4_IDS:
            continue
        if section.get("figure"):
            found.append((section["id"], section["figure"]))
        for tab in section.get("subtabs") or []:
            if tab.get("figure"):
                found.append((f"{section['id']}/{tab['id']}", tab["figure"]))
    return found


def test_p4_live_figures_follow_i4_mode_table() -> None:
    """N3/N4: every P4 section figure selects chrome by mode, EN and ZH."""
    sections = builder._macro_command_sections(_live_entries(), page_built_at=BUILT_AT)
    current_en = L.COUNT["same_publication"]["en"]
    current_zh = L.COUNT["same_publication"]["zh"]
    mixed_en = L.COUNT["overview_mixed"]["en"]
    mixed_zh = L.COUNT["overview_mixed"]["zh"]
    assert current_en == CURRENT_ONLY_EN
    assert current_zh == CURRENT_ONLY_ZH
    assert mixed_en == MIXED_PAIR_EN
    assert mixed_zh == MIXED_PAIR_ZH
    seen_current = 0
    figures = _iter_p4_figures(sections)
    assert figures, "P4 sections published no figures"
    for name, figure in figures:
        kinds = {row["kind"] for row in figure["rows"]}
        if kinds == {"current"}:
            seen_current += 1
            assert figure["count_text"] is None, name
            assert figure["state_line"]["en"] == current_en, name
            assert figure["state_line"]["zh"] == current_zh, name
            assert figure["state_line"]["en"] != mixed_en, name
            for row in figure["rows"]:
                assert row["prior"] is None, name
                assert row["delta"] is None, name
                assert row["sign"] is None, name
                assert row["current"], name
        elif kinds == {"movement"}:
            assert figure["state_line"] is None, name
            assert figure["count_text"] is not None, name
            assert current_en not in (figure["count_text"] or {}).get("en", "")
        elif kinds == {"current", "movement"}:
            assert figure["count_text"] is None, name
            assert figure["state_line"]["en"] == mixed_en, name
            assert figure["state_line"]["zh"] == mixed_zh, name
            assert figure["state_line"]["en"] != current_en, name
        else:
            raise AssertionError(f"{name}: unexpected kinds {kinds}")
    assert seen_current >= 1


def test_p4_mixed_section_figure_uses_mixed_pair_not_current_only() -> None:
    """N3: a mixed P4 section figure prints the mixed pair, never the current-only line."""
    sections = builder._macro_command_sections(_live_entries(), page_built_at=BUILT_AT)
    mixed_en = L.COUNT["overview_mixed"]["en"]
    mixed_zh = L.COUNT["overview_mixed"]["zh"]
    current_en = L.COUNT["same_publication"]["en"]
    current_zh = L.COUNT["same_publication"]["zh"]
    seen = 0
    for name, figure in _iter_p4_figures(sections):
        rows = copy.deepcopy(figure["rows"])
        assert rows, name
        kinds = {row["kind"] for row in rows}
        if kinds == {"current"}:
            rows[0]["kind"] = "movement"
            rows[0]["prior"] = rows[0].get("current") or "1.00"
            rows[0]["delta"] = "+0.10"
            rows[0]["sign"] = "up"
        elif kinds == {"movement"}:
            rows[0]["kind"] = "current"
            rows[0]["prior"] = None
            rows[0]["delta"] = None
            rows[0]["sign"] = None
        mixed = builder._figure_block(
            rows, overview=False, shown=len(rows), total=len(rows))
        seen += 1
        assert {row["kind"] for row in mixed["rows"]} == {"current", "movement"}, name
        assert mixed["count_text"] is None, name
        assert mixed["state_line"]["en"] == mixed_en, name
        assert mixed["state_line"]["zh"] == mixed_zh, name
        assert mixed["state_line"]["en"] != current_en, name
        assert current_en not in mixed["state_line"]["en"]
        assert current_zh not in mixed["state_line"]["zh"]
    assert seen >= 1


def test_p4_live_hub_html_prints_the_i4_state_line(built: tuple[str, Path]) -> None:
    html, out = built
    state_en = L.COUNT["same_publication"]["en"]
    state_zh = L.COUNT["same_publication"]["zh"]
    seen = 0
    for section_id in P4_IDS:
        fragment = (out / "macro" / "fragments" / f"{section_id}.html")
        body = unescape(fragment.read_text(encoding="utf-8")
                        if fragment.exists()
                        else _panel(html, section_id))
        if "mc-move-current-only" not in body:
            continue
        seen += 1
        assert state_en in body, section_id
        assert state_zh in body, section_id
        assert "compared against the previous publication" not in body
        assert "与上一次发布相比" not in body
        assert "mc-move-prior" not in body
        assert "mq-delta-flat" not in body
        assert 'class="mc-caption' not in body
    assert seen >= 1


def test_p4_probes_name_panel_ok_and_doc_ok_separately() -> None:
    """M1: the 390 probe flag is not a lie about document overflow."""
    probes = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p4" / "probes.json")
        .read_text(encoding="utf-8"))
    rows = probes["p19"]
    assert len(rows) == 12
    for row in rows:
        assert "ok" not in row, row
        assert isinstance(row["panel_ok"], bool)
        assert isinstance(row["doc_ok"], bool)
        assert row["panel_ok"] is True
        assert row["panel_sw"] <= row["panel_cw"]
        assert row["doc_ok"] is (row["sw"] <= row["cw"])
    mobile = [row for row in rows if row["width"] == 390]
    assert len(mobile) == 4
    for row in mobile:
        assert row["cw"] == 390
        assert row["sw"] >= 390

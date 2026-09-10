"""Macro Command P4 — seven remaining sections: copy, riders, fail-closed.

Every §2 string is asserted by value (EN and ZH) on the built page or the
view. Riders: METRIC pool, consumer_payments tone, foot-note condition,
one-null-voice on E1, truthful housing/debt/trade stances, Q2 A/C pin.
"""
from __future__ import annotations

import copy
import inspect
import json
import re
import shutil
from html import unescape
from html.parser import HTMLParser
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
    assert "We don't have this reading yet" in frag
    assert "We don't have this reading yet" not in housing
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
    assert housing["empty"]["title"]["en"] == L.EMPTY_STATES["e2"]["title"]["en"]
    assert housing["stance"] is None
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
    assert growth["stance"] is None
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
    assert credit["stance"] is None
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


def test_p4_mixed_section_routes_through_macro_command_sections() -> None:
    """N10: a mixed P4 section through the real builder path, not _figure_block."""
    entries = copy.deepcopy(_live_entries())
    mixed_en = L.COUNT["overview_mixed"]["en"]
    mixed_zh = L.COUNT["overview_mixed"]["zh"]
    current_en = L.COUNT["same_publication"]["en"]
    current_zh = L.COUNT["same_publication"]["zh"]
    victim = None
    for entry in entries:
        if entry["workspace_id"] != "labor_markets":
            continue
        snap = entry["snapshot"] or {}
        headline = snap.setdefault("headline", {})
        changes = snap.setdefault("changes", {})
        deltas = list(changes.get("deltas") or [])
        assert len(deltas) >= 2, "labor_markets needs two deltas to mix"
        headline["effective_date"] = "2026-09-04"
        changes["prior_effective_date"] = "2026-08-04"
        first, extra = deltas[0], deltas[1]
        first["prior_value"] = first.get("prior_value") if first.get("prior_value") is not None else 1.0
        first["current_value"] = first.get("current_value") if first.get("current_value") is not None else 1.1
        first["delta"] = first.get("delta") if first.get("delta") is not None else 0.1
        extra["prior_value"] = None
        extra["delta"] = None
        extra["current_value"] = extra.get("current_value") if extra.get("current_value") is not None else 2.0
        changes["deltas"] = [first, extra]
        victim = entry
        break
    assert victim is not None
    sections = builder._macro_command_sections(entries, page_built_at=BUILT_AT)
    jobs = next(section for section in sections if section["id"] == "jobs")
    figure = jobs["figure"]
    assert figure is not None
    kinds = {row["kind"] for row in figure["rows"]}
    assert kinds == {"current", "movement"}
    assert figure["count_text"] is None
    assert figure["state_line"]["en"] == mixed_en
    assert figure["state_line"]["zh"] == mixed_zh
    assert current_en not in figure["state_line"]["en"]
    assert current_zh not in figure["state_line"]["zh"]
    assert current_en not in (jobs.get("stance") or {}).get("text", {}).get("en", "")


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


def test_overview_current_only_emits_no_figure_state_line(built: tuple[str, Path]) -> None:
    """MIN-2: all-current Overview speaks once via overview_current, never the figure line."""
    html, _ = built
    overview = unescape(_panel(html, "overview"))
    assert "mc-move-current-only" in overview
    current_en = L.COUNT["same_publication"]["en"]
    current_zh = L.COUNT["same_publication"]["zh"]
    stance_en = L.COUNT["overview_current"]["en"]
    stance_zh = L.COUNT["overview_current"]["zh"]
    assert current_en not in overview
    assert current_zh not in overview
    assert overview.count(stance_en) == 1
    assert overview.count(stance_zh) == 1
    assert '<p class="mc-move-state">' not in overview


def _e6_slot_texts() -> dict[str, dict[str, str]]:
    spec = L.EMPTY_STATES["e6"]
    texts = {}
    for key in ("title", "stance", "why", "unlock", "cta_label"):
        pair = spec[key]
        texts[key] = {
            "en": pair["en"].replace("{plan}", "Research"),
            "zh": pair["zh"].replace("{plan}", "Research"),
        }
    return texts


def _strip_sentence(text: str) -> str:
    return text.strip().rstrip(".—。")


def _levenshtein(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    prev = list(range(len(right) + 1))
    for i, char_l in enumerate(left, 1):
        curr = [i]
        for j, char_r in enumerate(right, 1):
            curr.append(min(
                prev[j] + 1,
                curr[j - 1] + 1,
                prev[j - 1] + (char_l != char_r),
            ))
        prev = curr
    return prev[-1]


def _shared_char_ratio(left: str, right: str) -> float:
    from collections import Counter
    denom = max(len(left), len(right))
    if denom == 0:
        return 1.0
    shared = sum((Counter(left) & Counter(right)).values())
    return shared / denom


def test_e6_slots_share_no_sentence_or_prefix() -> None:
    """r5 MINOR-1 + r6 MINOR-A: distinct slots; reject twins (Lev≤2 or ≥80% chars)."""
    slots = _e6_slot_texts()
    assert slots["cta_label"]["en"] == "Upgrade to see it"
    assert slots["cta_label"]["zh"] == "查看升级方案"
    for locale in ("en", "zh"):
        items = [(key, _strip_sentence(pair[locale])) for key, pair in slots.items()]
        for i, (key_a, text_a) in enumerate(items):
            for key_b, text_b in items[i + 1:]:
                assert text_a, (locale, key_a)
                assert text_b, (locale, key_b)
                assert text_a != text_b, (locale, key_a, key_b, text_a)
                assert not text_b.startswith(text_a), (locale, key_a, key_b, text_a, text_b)
                assert not text_a.startswith(text_b), (locale, key_a, key_b, text_a, text_b)
                assert _levenshtein(text_a, text_b) > 2, (
                    locale, key_a, key_b, text_a, text_b)
                assert _shared_char_ratio(text_a, text_b) < 0.8, (
                    locale, key_a, key_b, text_a, text_b)


def test_entitlement_walled_section_uses_plan_stance_and_drops_watching() -> None:
    """N-D: a walled section never issues a read-now instruction; WATCHING is off."""
    entries = copy.deepcopy(_live_entries())
    for entry in entries:
        if entry["workspace_id"] == "capital_structure":
            entry["snapshot"]["entitlement"] = "Research"
    sections = builder._macro_command_sections(
        entries, page_built_at=BUILT_AT, allow_empty_state_fixture=True)
    credit = next(section for section in sections if section["id"] == "credit")
    funding = next(tab for tab in credit["subtabs"] if tab["id"] == "funding")
    assert funding["empty"]["id"] == "e6"
    assert credit["stance"] is None
    assert credit["watching"] is None
    assert credit["empty"] is None


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
    for row in rows:
        assert "mmbBootDisplay" in row, row
        if row["width"] <= 768:
            assert row["mmbBootDisplay"] == "none", row


def _runtime_receipt(*, missing_section: str | None = None,
                     fragments: bool = True) -> dict[str, dict]:
    receipt: dict[str, dict] = {}
    for section in ("overview", "growth", "jobs", "housing",
                    "consumer", "credit", "debt", "trade"):
        present = section != "overview" and section != missing_section
        receipt[section] = {
            "templatePresent": present,
            "fragmentTarget": f"macro/fragments/{section}.html",
            "fragments": fragments,
        }
    return receipt


def test_e5_applicability_from_page_evaluates_runtime_js() -> None:
    """r8 MINOR-1: applicability is page.evaluate over the live DOM, not HTML regex."""
    from scripts import capture_macro_command_p4 as capture

    assert "e5_applicability_from_html" not in dir(capture)
    src = Path(capture.__file__).read_text(encoding="utf-8")
    assert "def e5_applicability_from_html" not in src
    assert "def e5_applicability(" not in src
    assert "re.finditer" not in src
    js = capture.E5_APPLICABILITY_JS
    assert "querySelectorAll('[data-mc-panel]')" in js
    assert "template[data-mc-empty-e5]" in js
    assert "#mc-shell" in js
    assert "data-mc-fragments" in js

    seen: dict[str, str] = {}

    class _Page:
        def evaluate(self, code):
            seen["js"] = code
            return _runtime_receipt(missing_section="jobs")

    receipt = capture.e5_applicability_from_page(_Page())
    assert seen["js"] == capture.E5_APPLICABILITY_JS
    assert receipt["growth"]["templatePresent"] is True
    assert receipt["jobs"]["templatePresent"] is False
    assert receipt["growth"]["fragments"] is True


def test_e5_applicability_is_per_hub_section() -> None:
    """r7 SCOPE + r8 MINOR-1: E5 is declared from the runtime receipt."""
    from scripts import capture_macro_command_p4 as capture

    receipt = _runtime_receipt(missing_section="jobs")
    assert capture.empty_ids_for_section(receipt["growth"])[-1] == "e5"
    assert "e5" not in capture.empty_ids_for_section(receipt["jobs"])
    no_fragments = _runtime_receipt()
    no_fragments["growth"]["fragments"] = False
    assert "e5" not in capture.empty_ids_for_section(no_fragments["growth"])
    families = capture.declared_families(
        blast_keys=["growth_real_economy"], applicability=receipt)
    e5 = [cell for cell in families["empty_states"] if cell.startswith("empty-e5-")]
    assert any(cell.startswith("empty-e5-growth-") for cell in e5)
    assert not any(cell.startswith("empty-e5-jobs-") for cell in e5)
    assert len(e5) == 6 * 2 * 4  # six templated sections × 1440/390 × theme × locale


def test_declared_matrix_gaps_are_generated_not_hand_written() -> None:
    """r6 MAJOR: every state is a per-cell matrix; gaps = declared − captured."""
    from scripts import capture_macro_command_p4 as capture

    blast = [f"workspace_{i}" for i in range(9)]
    none_e5 = {
        section: {
            "templatePresent": False,
            "fragmentTarget": f"macro/fragments/{section}.html",
            "fragments": True,
        }
        for section in capture.SECTIONS
    }
    families = capture.declared_families(blast_keys=blast, applicability=none_e5)
    declared = capture.flatten_declared(families)
    assert not any(cell.startswith("empty-e5-") for cell in declared)
    assert len(families["empty_states"]) == 5 * 2 * 4
    assert len(families["sections"]) == 7 * 3 * 4 + 7 * 4  # widths + 1440 full
    assert len(families["states"]) == 4 * 4
    assert len(families["blast"]) == 9 * 2 * 4
    assert len(families["clearance"]) == 7 * 3 * 4
    assert len(families["rail_viewport"]) == 2 * 4
    assert len(families["fab"]) == 4
    assert len(families["rest_views"]) == 3 * 4
    captured = set(declared)
    assert capture.generate_gaps(declared, captured) == []
    missing = capture.generate_gaps(
        declared, captured - {"empty-e1-light-zh-390", "mob-growth-dark-en-390"})
    stems = {gap.split(":", 1)[0] for gap in missing}
    assert stems == {"empty-e1-light-zh-390", "mob-growth-dark-en-390"}
    excluded = capture.generate_excluded(missing)
    assert {row["id"] for row in excluded} == stems


def test_writer_emits_gaps_from_same_computation() -> None:
    """r7 MAJOR-1: the writer emits gaps; key set includes gaps."""
    from scripts import capture_macro_command_p4 as capture

    families = {
        "sections": ["mob-growth-dark-en-390"],
        "empty_states": ["empty-e1-light-zh-390"],
    }
    declared = capture.flatten_declared(families)
    captured = {"mob-growth-dark-en-390"}
    gaps = capture.generate_gaps(declared, captured)
    protocol = {
        "tree_clean_start": True,
        "tree_clean_end": True,
        "head_start": "abc",
        "head_end": "abc",
        "generated_at_start": "2026-09-08T00:00:00Z",
        "generated_at_end": "2026-09-08T00:01:00Z",
        "commit_time_of_capture_sha": "2026-09-08T00:00:00+00:00",
    }
    manifest = capture.build_manifest(
        families=families,
        probe_stems=[],
        excluded=capture.generate_excluded(gaps),
        gaps=gaps,
        states=[],
        protocol=protocol,
    )
    assert "gaps" in manifest
    assert manifest["gaps"] == capture.generate_gaps(declared, captured)
    assert manifest["gaps"] == manifest["pages"][0]["gaps"]
    assert manifest["gaps"] == [
        "empty-e1-light-zh-390: captured:false — declared cell missing from this run"
    ]


def test_state_row_rejects_null_fixture() -> None:
    """r7 MINOR-3: fixture is never null."""
    from scripts import capture_macro_command_p4 as capture

    info = {
        "applied_locale": "en",
        "applied_theme": "dark",
        "bytes": 10,
        "png_height": 10,
        "png_width": 10,
        "sha256": "a" * 64,
        "css_width": 10,
        "css_height": 10,
        "clip": {"x": 0, "y": 0, "width": 10, "height": 10},
        "dpr": 2,
    }
    try:
        capture._state_row(
            "x.png", "dark", "en", "desktop", info,
            fixture=None, verified_how="test")
    except ValueError as exc:
        assert "fixture" in str(exc)
    else:
        raise AssertionError("expected ValueError for fixture=None")
    try:
        capture._state_row(
            "x.png", "dark", "en", "desktop", info,
            fixture="", verified_how="test")
    except ValueError as exc:
        assert "fixture" in str(exc)
    else:
        raise AssertionError("expected ValueError for empty fixture")
    row = capture._state_row(
        "x.png", "dark", "en", "desktop", info,
        fixture="builder-payload", verified_how="test")
    assert row["fixture"] == "builder-payload"


def test_p3_clearance_and_rail_import_contract() -> None:
    """r7 MINOR-2 + r8 MINOR-2: every P3 import is module-level and pinned."""
    import inspect

    from scripts import capture_macro_command_p3 as p3
    from scripts import capture_macro_command_p4 as capture

    assert capture.RAIL_VIEWPORT_JS is p3.RAIL_VIEWPORT_JS
    assert capture._run_clearance is p3._run_clearance
    assert capture._run_synthetic_clearance is p3._run_synthetic_clearance
    assert capture._confirm_rail_fade_visual is p3._confirm_rail_fade_visual
    assert capture._device_px_span is p3._device_px_span
    assert capture._write_element_shot is p3._write_element_shot
    assert capture._assert_shot_geometry is p3._assert_shot_geometry
    assert capture._device_px_span_from_crop_box_doc is p3._device_px_span_from_crop_box_doc

    assert callable(capture._run_clearance)
    assert "getComputedStyle(list, '::after')" in capture.RAIL_VIEWPORT_JS
    assert "capWidth" in capture.RAIL_VIEWPORT_JS
    assert "position === 'sticky'" in capture.RAIL_VIEWPORT_JS
    assert "fadeWidth" in capture.RAIL_VIEWPORT_JS

    span = capture._device_px_span(
        {"x": 10.2, "y": 20.4, "width": 100.3, "height": 50.1}, 2.0)
    assert set(span) == {"x0", "x1", "y0", "y1"}

    shot_src = inspect.getsource(capture._write_element_shot)
    assert 'extra["crop_box_doc"]' in shot_src
    assert 'extra["scroll_y_at_shot"]' in shot_src
    assert 'extra["element_text_head"]' in shot_src
    assert 'extra["device_px_span"] = _device_px_span(box_before, extra["dpr"])' in shot_src
    assert "element box moved" in shot_src

    _run_clearance = capture._run_clearance

    class _Page:
        def evaluate(self, _js, target=None):
            return {
                "ok": True,
                "textCount": 4,
                "maxScrollMatched": True,
                "maxScroll": 200,
                "hits": [],
                "excused": [{
                    "reason": "rail_fully_covered",
                    "docTop": 400,
                    "ovBottom": 80,
                    "exposedAtScrollY": 120,
                    "maxScroll": 200,
                }, {
                    "reason": "chip_partially_covered",
                    "docTop": 100,
                    "ovBottom": 40,
                    "exposedAtScrollY": 60,
                    "maxScroll": 200,
                }],
                "overlays": [],
                "mmbBootInDom": True,
                "mmbBootVisible": False,
            }

    row = _run_clearance(_Page())
    assert set(row["positions"]) == {"0", "50", "max"}
    for pos in row["positions"].values():
        assert pos["maxScrollMatched"] is True
        assert pos["hits"] == []
        assert pos["excused"]
        for item in pos["excused"]:
            assert "docTop" in item
            assert "ovBottom" in item
            assert "exposedAtScrollY" in item
            assert "maxScroll" in item
            reason = item["reason"]
            assert reason.endswith("_fully_covered") or reason.endswith(
                "_partially_covered")


def test_manifest_gaps_recompute_from_declared() -> None:
    """r6 MAJOR: a test recomputes gaps from manifest['declared'] and asserts equality."""
    from scripts import capture_macro_command_p4 as capture

    manifest_path = ROOT / "mockups" / "evidence" / "macro-command-p4" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    declared = manifest.get("declared")
    assert isinstance(declared, dict), "manifest.declared must be the complete family matrix"
    flat = capture.flatten_declared(declared)
    captured = capture.captured_stems(manifest["pages"][0]["states"])
    captured.update(manifest.get("probe_stems") or [])
    assert "gaps" in manifest
    assert capture.generate_gaps(flat, captured) == manifest["gaps"]
    # r8 NIT: captured ⊆ declared and declared ⊆ captured. A silently
    # dropped E5 cell or a stray frame fails this, not just declared − captured.
    assert capture.generate_extras(flat, captured) == []
    assert captured - set(flat) == set()
    assert set(flat) - captured == set(gap.split(":", 1)[0] for gap in manifest["gaps"])


def test_runtime_receipt_agrees_with_declared_e5() -> None:
    """r8 MINOR-1: committed runtime receipt and declared E5 cells agree."""
    from scripts import capture_macro_command_p4 as capture

    probes_path = ROOT / "mockups" / "evidence" / "macro-command-p4" / "probes.json"
    manifest_path = ROOT / "mockups" / "evidence" / "macro-command-p4" / "manifest.json"
    probes = json.loads(probes_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    receipt = probes.get("e5_applicability") or {}
    assert receipt, "probes.e5_applicability missing"
    families = capture.declared_families(
        blast_keys=[
            name.removeprefix("macro_").removesuffix(".html")
            for name in (probes.get("blast_pages") or [])
        ],
        applicability=receipt,
    )
    declared_e5 = {
        cell for cell in families["empty_states"] if cell.startswith("empty-e5-")
    }
    manifest_e5 = {
        cell for cell in manifest["declared"]["empty_states"]
        if cell.startswith("empty-e5-")
    }
    assert declared_e5 == manifest_e5
    captured = capture.captured_stems(manifest["pages"][0]["states"])
    captured_e5 = {stem for stem in captured if stem.startswith("empty-e5-")}
    assert captured_e5 == declared_e5


def test_generate_extras_flags_undeclared_stems() -> None:
    """r8 NIT: captured − declared is a first-class list."""
    from scripts import capture_macro_command_p4 as capture

    declared = ["empty-e1-light-zh-390"]
    captured = {"empty-e1-light-zh-390", "stray-frame"}
    extras = capture.generate_extras(declared, captured)
    assert extras == [
        "stray-frame: undeclared — captured stem not in declared matrix"
    ]
    assert capture.generate_extras(declared, set(declared)) == []


def test_ihdr_3px_wider_than_element_span_raises(tmp_path: Path) -> None:
    """r8 MAJOR-1: PNG 3 px wider than the element-box span raises."""
    from PIL import Image

    from scripts import capture_macro_command_p4 as capture

    dest = tmp_path / "wide.png"
    Image.new("RGB", (103, 50), (0, 0, 0)).save(dest)
    extra = {
        "dpr": 2.0,
        "crop": True,
        "crop_selector": "#x",
        "device_px_span": {"x0": 0, "x1": 100, "y0": 0, "y1": 50},
    }
    with pytest.raises(RuntimeError, match="device_px_span"):
        capture._assert_shot_geometry(dest, extra, 1440, 900)


def test_committed_crops_span_recomputed_from_crop_box_doc() -> None:
    """r8 MAJOR-1: every committed crop span is the element box, not the IHDR."""
    from scripts import capture_macro_command_p4 as capture

    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p4" / "manifest.json")
        .read_text(encoding="utf-8"))
    for state in manifest["pages"][0]["states"]:
        if not state.get("crop"):
            continue
        box = state.get("crop_box_doc")
        assert box, state.get("file")
        recomputed = capture._device_px_span_from_crop_box_doc(
            box, float(state["scroll_y_at_shot"]), float(state["dpr"]))
        assert state["device_px_span"] == recomputed, state.get("file")
        exp_w = recomputed["x1"] - recomputed["x0"]
        exp_h = recomputed["y1"] - recomputed["y0"]
        delta = state.get("ihdr_delta_px") or {
            "w": abs(int(state["width"]) - exp_w),
            "h": abs(int(state["height"]) - exp_h),
        }
        assert delta["w"] <= 1 and delta["h"] <= 1, (state.get("file"), delta)


def _crop_info(**extra):
    info = {
        "applied_locale": "en",
        "applied_theme": "dark",
        "bytes": 10,
        "png_height": 10,
        "png_width": 10,
        "sha256": "a" * 64,
        "css_width": 10,
        "css_height": 10,
        "clip": {"x": 0, "y": 0, "width": 10, "height": 10},
        "dpr": 2,
        "crop_box": {"x": 0, "y": 0, "width": 10, "height": 10},
        "crop_box_doc": {"x": 0, "y": 0, "width": 10, "height": 10},
        "scroll_y_at_shot": 0,
        "element_text_head": "Included in a higher plan. The reading is available on upgrade.",
        "element_text_sha256": "b" * 64,
        "device_px_span": {"x0": 0, "x1": 10, "y0": 0, "y1": 10},
        "ihdr_delta_px": {"w": 0, "h": 0},
    }
    info.update(extra)
    return info


def test_section_from_clip_sel_does_not_eat_credit_c() -> None:
    """MAJOR-E1: prefix-strip, never lstrip character class."""
    from scripts import capture_macro_command_p4 as capture

    assert capture.section_from_clip_sel("section#credit") == "credit"
    assert capture.section_from_clip_sel("section.mc-panel#credit") == "credit"
    assert capture.section_from_clip_sel("section#housing") == "housing"
    with pytest.raises(RuntimeError, match="cannot derive section"):
        capture.section_from_clip_sel("[data-mc-empty='e4']")


def test_state_row_raises_on_section_outside_hub_ids() -> None:
    """MAJOR-E1: writer raises when section is not in the hub id set."""
    from scripts import capture_macro_command_p4 as capture

    with pytest.raises(RuntimeError, match="not in hub id set"):
        capture._state_row(
            "empty-e6-light-zh-1440.png", "light", "zh", "desktop",
            _crop_info(), fixture="builder-payload", verified_how="test",
            section="redit", crop=True)


def test_manifest_section_census_uses_hub_id_set() -> None:
    """MAJOR-E1: every committed section ∈ hub ids; seven P4 family counts."""
    from collections import Counter

    from scripts import capture_macro_command_p4 as capture

    allowed = capture.hub_id_set()
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p4" / "manifest.json")
        .read_text(encoding="utf-8"))
    states = manifest["pages"][0]["states"]
    census = Counter(row.get("section") for row in states if row.get("section"))
    for section in census:
        assert section in allowed, (section, census[section])
    for section in capture.SECTIONS:
        families = capture.expected_p4_section_family_counts(section)
        rows = [row for row in states if row.get("section") == section]
        section_files = [
            row for row in rows
            if re.match(rf"(comp|tab|mob)-{section}-", str(row.get("file") or ""))
        ]
        e5_files = [
            row for row in rows
            if str(row.get("file") or "").startswith(f"empty-e5-{section}-")
        ]
        fixture_files = [
            row for row in rows
            if re.match(r"empty-e[1-46]-", str(row.get("file") or ""))
        ]
        state_files = [
            row for row in rows
            if str(row.get("file") or "").startswith("state-")
        ]
        assert len(section_files) == families["sections"], (section, families)
        assert len(e5_files) == families["empty_e5"], (section, families)
        assert len(fixture_files) == families["empty_fixture"], (section, families)
        assert len(state_files) == families["states"], (section, families)


def test_synthetic_clearance_receipt_asserts_hit() -> None:
    """MAJOR-E2: python synthetic_hit_rule receipt from the committed probes."""
    probes = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p4" / "probes.json")
        .read_text(encoding="utf-8"))
    row = probes["synthetic_clearance"]
    receipts = row.get("synthetic_hit_rule") or {}
    assert set(receipts) >= {"inside zone", "below zone", "under pill"}
    for station in ("0", "50", "max"):
        inside = receipts["inside zone"][station]
        assert inside["verdict"] == "hit", station
        assert inside["reason"] == "sticky-rail-full-cover-unexposable"
        assert float(inside["exposedAtScrollY"]) < 0
    excused = [
        item for item in receipts["below zone"].values()
        if item.get("verdict") == "excused"
    ]
    assert excused and excused[0].get("exposedAtScrollY") is not None
    assert any(
        item.get("verdict") == "hit" for item in receipts["under pill"].values())


def test_synthetic_clearance_runs_shipped_js_in_playwright() -> None:
    """MAJOR-E2: SHIPPED CLEARANCE_AT_JS against the synthetic DOM."""
    from scripts import capture_macro_command_p4 as capture

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("Playwright not installed")
    try:
        playwright_cm = sync_playwright().start()
    except Exception as exc:
        pytest.skip(f"Playwright runtime unavailable: {exc}")
    try:
        try:
            browser = playwright_cm.chromium.launch(headless=True, channel="chrome")
        except Exception:
            try:
                browser = playwright_cm.chromium.launch(headless=True)
            except Exception as exc:
                pytest.skip(f"Chromium unavailable: {exc}")
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            row = capture._run_synthetic_clearance(page)
        finally:
            browser.close()
    finally:
        playwright_cm.stop()
    receipts = row["synthetic_hit_rule"]
    for station in ("0", "50", "max"):
        assert receipts["inside zone"][station]["verdict"] == "hit", station
        assert receipts["inside zone"][station]["reason"] == (
            "sticky-rail-full-cover-unexposable")
        assert float(receipts["inside zone"][station]["exposedAtScrollY"]) < 0
    excused = [
        item for item in receipts["below zone"].values()
        if item.get("verdict") == "excused"
    ]
    assert excused and excused[0].get("exposedAtScrollY") is not None


def test_rail_viewport_records_full_fade_receipt() -> None:
    """MINOR-E1: fade fields present; |fadeOnsetX − fadeLeft| ≤ 4 when applicable."""
    probes = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p4" / "probes.json")
        .read_text(encoding="utf-8"))
    for theme in ("dark", "light"):
        for locale in ("en", "zh"):
            for width in (390, 768):
                key = f"rail_viewport-{theme}-{locale}-{width}"
                row = probes[key]
                assert "fadeOnsetX" in row, key
                assert "fadeHalfDelta" in row or row.get("fadeVisualApplicable") is False, key
                assert "fadeVisualApplicable" in row, key
                assert row.get("maskRaw"), key
                assert row.get("chips"), key
                for chip in row["chips"]:
                    assert chip.get("fullyVisibleAtScrollLeft") is not None, (key, chip)
                if row.get("fadeVisualApplicable"):
                    assert row.get("fadeOnsetX") is not None, key
                    assert abs(float(row["fadeOnsetX"]) - float(row["fadeLeft"])) <= 4, key
                    assert row.get("fadeHalfDelta") is not None, key
                else:
                    assert row.get("fadeVisualReason"), key


def test_element_text_head_is_first_block_not_mid_word() -> None:
    """MINOR-E2: heads are first-block, ≤400, never mid-word; sha256 present."""
    from scripts import capture_macro_command_p4 as capture

    assert capture.first_block_head(
        "Borrowing costs. Read today's overview extra", 20
    ) == "Borrowing costs."
    assert "Borrow" != capture.first_block_head(
        "Borrowing costs sit above the fold today and keep climbing", 20
    )
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p4" / "manifest.json")
        .read_text(encoding="utf-8"))
    for state in manifest["pages"][0]["states"]:
        if not state.get("crop"):
            continue
        head = state.get("element_text_head") or ""
        assert head, state.get("file")
        assert len(head) <= 400, (state.get("file"), len(head))
        assert state.get("element_text_sha256"), state.get("file")
        if head and not head[-1].isspace():
            # never mid-word: last char is punctuation or the block ended cleanly
            assert head[-1].isalnum() or head[-1] in ".。！？!?→", (
                state.get("file"), head[-20:])


_VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
})


class _Visible(HTMLParser):
    """Locale-aware visible text. Void tags inside a skipped subtree must
    not increment skip depth — HTMLParser never emits their end tag."""

    def __init__(self, lang: str) -> None:
        super().__init__()
        self.lang = lang
        self._skip = 0
        self.texts: list[str] = []

    def _skip_start(self, tag: str, attrs) -> None:
        classes = dict(attrs).get("class", "").split()
        if self.lang == "en" and "l-zh" in classes:
            self._skip += 1
        elif self.lang == "zh" and "l-en" in classes:
            self._skip += 1
        elif self._skip and tag not in _VOID_TAGS:
            self._skip += 1

    def handle_starttag(self, tag, attrs):
        self._skip_start(tag, attrs)

    def handle_startendtag(self, tag, attrs):
        if self._skip:
            return
        self._skip_start(tag, attrs)
        if self._skip:
            self._skip -= 1

    def handle_endtag(self, tag):
        if tag in _VOID_TAGS:
            return
        if self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if self._skip:
            return
        text = " ".join(data.split())
        if text:
            self.texts.append(text)


def _visible_blob(html: str, lang: str) -> str:
    parser = _Visible(lang)
    parser.feed(html)
    return " ".join(parser.texts)


def test_rendered_sections_have_no_repeated_visible_sentence() -> None:
    """MINOR-E2: repeated-sentence check on the rendered hub, not the head."""
    html = (ROOT / "site" / "macro_monetary.html").read_text(encoding="utf-8")
    for section in P4_IDS:
        match = re.search(
            r'<section class="mc-panel" id="' + section + r'".*?(?=<section class="mc-panel"|</main>)',
            html, re.S)
        assert match, section
        for lang in ("en", "zh"):
            blob = _visible_blob(match.group(0), lang)
            sentences = [
                part.strip() for part in re.split(r"(?<=[.。！？!?])\s+", blob)
                if part.strip()
            ]
            assert sentences, (section, lang)
            assert len(sentences) == len(set(sentences)), (section, lang, sentences)


def test_visible_parser_does_not_go_blind_on_void_in_skipped_span() -> None:
    """NIT-1: a <br> inside an l-zh span must not swallow the following EN."""
    html = (
        '<section class="mc-panel" id="housing">'
        '<span class="l-zh">跳过<br>仍跳过</span>'
        '<span class="l-en">First sentence. Second sentence.</span>'
        "</section>"
    )
    blob = _visible_blob(html, "en")
    assert "First sentence." in blob
    assert "Second sentence." in blob
    assert "跳过" not in blob
    sentences = [
        part.strip() for part in re.split(r"(?<=[.。！？!?])\s+", blob)
        if part.strip()
    ]
    assert sentences == ["First sentence.", "Second sentence."]


def _p4_workspaces() -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for section in builder.SECTIONS:
        if section.id not in P4_IDS:
            continue
        if section.subtabs:
            mapping[section.id] = [tab.workspace_id for tab in section.subtabs]
        elif section.workspace_id:
            mapping[section.id] = [section.workspace_id]
    return mapping


def _p4_plan(section_id: str) -> str:
    """The entitlement string the fixture path writes; :1073 must pass it."""
    return f"Research-{section_id}"


def _mutate_p4_entries_for_empty(entries: list[dict], empty_id: str) -> None:
    ws_to_section = {
        workspace_id: section_id
        for section_id, workspace_ids in _p4_workspaces().items()
        for workspace_id in workspace_ids
    }
    tab_id_by_workspace: dict[str, str] = {}
    for section in builder.SECTIONS:
        if section.id not in P4_IDS or not section.subtabs:
            continue
        for tab in section.subtabs:
            tab_id_by_workspace[tab.workspace_id] = tab.id
    for entry in entries:
        workspace_id = entry["workspace_id"]
        if workspace_id not in ws_to_section:
            continue
        snap = entry["snapshot"]
        section_id = ws_to_section[workspace_id]
        if empty_id == "e1":
            snap["headline"]["effective_date"] = None
            snap["headline"]["status"] = "ABSENT"
            snap["headline"]["state_id"] = None
            snap["headline"]["null_reason"] = "NOT_YET_RELEASED"
            snap["changes"]["deltas"] = []
            snap["changes"]["comparability"] = "NO_PRIOR"
            snap["changes"]["status"] = "ABSENT"
            snap["changes"]["null_reason"] = "INSUFFICIENT_HISTORY"
        elif empty_id == "e2":
            snap["availability"]["state"] = "SOURCE_FAILED"
            snap["headline"]["status"] = "ABSENT"
            snap["headline"]["state_id"] = None
            snap["headline"]["effective_date"] = None
            snap["changes"]["deltas"] = []
        elif empty_id == "e3":
            if not snap["headline"].get("effective_date"):
                snap["headline"]["effective_date"] = "2026-09-01"
            snap["changes"]["deltas"] = []
            snap["changes"]["comparability"] = "NO_PRIOR"
            snap["changes"]["status"] = "ABSENT"
            snap["changes"]["null_reason"] = "INSUFFICIENT_HISTORY"
        elif empty_id == "e4":
            if workspace_id in tab_id_by_workspace:
                snap["withheld_command_tabs"] = [tab_id_by_workspace[workspace_id]]
        elif empty_id == "e6":
            snap["entitlement"] = _p4_plan(section_id)


def _section_has_empty(section: dict, empty_id: str) -> bool:
    if (section.get("empty") or {}).get("id") == empty_id:
        return True
    return any(
        (tab.get("empty") or {}).get("id") == empty_id
        for tab in section.get("subtabs") or []
    )


def _render_forced_hub(tmp_path: Path, empty_id: str) -> Path:
    """Same force path as capture `_build_memory_hub` / remanifest fixtures."""
    out = tmp_path / f"forced-{empty_id}"
    out.mkdir(parents=True, exist_ok=True)
    entries = copy.deepcopy(_live_entries())
    _mutate_p4_entries_for_empty(entries, empty_id)
    env = builder._environment(ROOT)
    sections = builder._macro_command_sections(
        entries, page_built_at=BUILT_AT, allow_empty_state_fixture=True)
    if empty_id == "e4":
        # E4 only routes through withheld command tabs. Non-subtab P4
        # sections have no writer path; inject the same `_empty_state`
        # the fixture path uses so the rendered fragment still carries E4.
        for section in sections:
            if section["id"] in P4_IDS and not _section_has_empty(section, "e4"):
                section["empty"] = builder._empty_state("e4")
    builder.build_hub(
        entries, out_dir=out, env=env, root=ROOT,
        page_built_at=BUILT_AT, allow_empty_state_fixture=True)
    if empty_id == "e4":
        builder.write_fragments(env, sections, out)
    return out


def _empty_card_html(html: str, empty_id: str) -> str:
    match = re.search(
        r'<div class="mc-empty" role="note" data-mc-empty="'
        + re.escape(empty_id) + r'".*?</div>',
        html, re.S)
    assert match, empty_id
    return match.group(0)


def _normalize_empty_card(card: str, *, plan: str | None = None) -> str:
    text = card
    if plan:
        text = text.replace(plan, "{plan}")
    return text


def _assert_shared_empty_cards(
        cards: dict[str, str], *, plans: dict[str, str] | None = None) -> None:
    normalized = {
        section_id: _normalize_empty_card(
            card, plan=(plans or {}).get(section_id))
        for section_id, card in cards.items()
    }
    first_id, first = next(iter(normalized.items()))
    for section_id, text in normalized.items():
        assert text == first, (first_id, section_id, first[:200], text[:200])


def _assert_empty_vocabulary(card: str, empty_id: str, plan: str | None) -> None:
    spec = L.EMPTY_STATES[empty_id]
    for lang in ("en", "zh"):
        assert spec["title"][lang] == _visible_blob(
            re.search(r'<p class="mc-empty-title">.*?</p>', card, re.S).group(0),
            lang), (empty_id, lang)
        why = spec["why"][lang]
        if empty_id == "e6":
            why = why.format(plan=plan)
        assert why == _visible_blob(
            re.search(r'<p class="mc-empty-why">.*?</p>', card, re.S).group(0),
            lang), (empty_id, lang, plan)
        if spec.get("stance"):
            assert spec["stance"][lang] == _visible_blob(
                re.search(r'<p class="mc-empty-stance">.*?</p>', card, re.S).group(0),
                lang), (empty_id, lang)
        if spec.get("unlock"):
            assert spec["unlock"][lang] == _visible_blob(
                re.search(r'<p class="mc-empty-unlock">.*?</p>', card, re.S).group(0),
                lang), (empty_id, lang)
        if spec.get("next"):
            assert spec["next"][lang] == _visible_blob(
                re.search(r'<p class="mc-empty-next">.*?</p>', card, re.S).group(0),
                lang), (empty_id, lang)
        if spec.get("cta_label"):
            assert spec["cta_label"][lang] == _visible_blob(
                re.search(r'<a class="mc-empty-cta"[^>]*>.*?</a>', card, re.S).group(0),
                lang), (empty_id, lang)


def test_seven_p4_sections_share_e1_e4_e6_vocabulary(tmp_path: Path) -> None:
    """MINOR-E3(b): rendered-page vocabulary on every P4 section × E1–E4/E6."""
    by_section = {section.id: section for section in builder.SECTIONS}
    for empty_id in ("e1", "e2", "e3", "e4", "e6"):
        out = _render_forced_hub(tmp_path, empty_id)
        hub = unescape((out / "macro_monetary.html").read_text(encoding="utf-8"))
        cards: dict[str, str] = {}
        plans = {section_id: _p4_plan(section_id) for section_id in P4_IDS}
        for section_id in P4_IDS:
            panel = _panel(hub, section_id)
            spec_section = by_section[section_id]
            assert spec_section.label_en in panel, section_id
            assert spec_section.label_zh in panel, section_id
            frag = unescape(
                (out / "macro" / "fragments" / f"{section_id}.html")
                .read_text(encoding="utf-8"))
            assert f'data-mc-empty="{empty_id}"' in frag, (section_id, empty_id)
            card = _empty_card_html(frag, empty_id)
            plan = plans[section_id] if empty_id == "e6" else None
            _assert_empty_vocabulary(card, empty_id, plan)
            if empty_id == "e2":
                assert L.EMPTY_STATES["e2"]["title"]["en"] == "No reading arrived today."
                assert L.EMPTY_STATES["e2"]["title"]["zh"] == "今天没有新的读数。"
            if empty_id == "e6":
                assert L.EMPTY_STATES["e6"]["cta_label"]["zh"] == "查看升级方案"
            cards[section_id] = card
        _assert_shared_empty_cards(
            cards, plans=plans if empty_id == "e6" else None)

        if empty_id == "e4":
            bad = dict(cards)
            bad["credit"] = bad["credit"].replace(
                L.EMPTY_STATES["e4"]["title"]["en"], "Only-credit E4 title")
            with pytest.raises(AssertionError):
                _assert_shared_empty_cards(bad)
        if empty_id == "e6":
            credit = cards["credit"]
            with pytest.raises(AssertionError):
                _assert_empty_vocabulary(credit, "e6", "WRONG-PLAN")


def test_tree_completeness_fails_when_committed_frame_missing(tmp_path: Path) -> None:
    """CODE MINOR-1: delete one committed frame in a temp copy → check fails."""
    from scripts import capture_macro_command_p4 as capture

    src = ROOT / "mockups" / "evidence" / "macro-command-p4"
    dest = tmp_path / "macro-command-p4"
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("fixtures"))
    manifest = json.loads((src / "manifest.json").read_text(encoding="utf-8"))
    declared = capture.flatten_declared(manifest["declared"])
    probe_stems = manifest.get("probe_stems") or []
    capture.assert_tree_matches_declared(dest, declared, probe_stems)
    victim = dest / "comp-growth-dark-en-1440.png"
    assert victim.is_file()
    victim.unlink()
    with pytest.raises(RuntimeError, match="declared-on-disk"):
        capture.assert_tree_matches_declared(dest, declared, probe_stems)


def test_copy_chrome_raises_on_stale_asset_name(tmp_path: Path, monkeypatch) -> None:
    """CODE MINOR-2: a stale name in ASSETS raises, naming the asset."""
    from scripts import capture_macro_command_p4 as capture

    monkeypatch.setattr(
        capture, "ASSETS", capture.ASSETS + ("not-a-real-p4-asset.css",))
    with pytest.raises(RuntimeError, match="asset missing: not-a-real-p4-asset.css"):
        capture._copy_chrome(tmp_path)


def _e5_collision_groups(states: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for row in states:
        digest = row.get("sha256")
        if not row.get("captured") or not digest:
            continue
        groups.setdefault(str(digest), []).append(row)
    return {digest: group for digest, group in groups.items() if len(group) > 1}


def _box_key(row: dict) -> str:
    return json.dumps(row.get("crop_box_doc"), sort_keys=True, default=str)


def assert_committed_e5_collision_groups(states: list[dict]) -> None:
    """Committed-manifest collision predicate (r10 CODE MINOR-1 / EVIDENCE MINOR-1).

    For every sha256 group: all rows are empty_e5 crops; all share
    (theme, locale, width); crop_selector values are pairwise distinct
    (one row per section); the set of distinct crop_box_doc is recorded
    and ≤ the number of rows. Identical boxes are not required.
    """
    for digest, group in _e5_collision_groups(states).items():
        files = [row.get("file") for row in group]
        assert all(
            str(row.get("file") or "").startswith("empty-e5-")
            or row.get("force_state") == "e5"
            for row in group
        ), (digest, files)
        assert all(row.get("crop") for row in group), (digest, files)
        axes = {
            (row.get("theme"), row.get("locale"),
             row.get("viewport_width") or row.get("width"))
            for row in group
        }
        assert len(axes) == 1, (digest, files, axes)
        sections = [row.get("section") for row in group]
        assert len(sections) == len(set(sections)), (digest, files, sections)
        selectors = [row.get("crop_selector") for row in group]
        assert None not in selectors, (digest, files)
        assert len(selectors) == len(set(selectors)), (digest, files, selectors)
        boxes = {_box_key(row) for row in group}
        assert 1 <= len(boxes) <= len(group), (digest, files, len(boxes))


def test_sha256_collisions_only_in_ruled_e5_groups() -> None:
    """CODE MINOR-3 / r10 MINOR-1: committed E5 groups; intra-section fails."""
    from scripts import capture_macro_command_p4 as capture

    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p4" / "manifest.json")
        .read_text(encoding="utf-8"))
    states = manifest["pages"][0]["states"]
    capture.assert_sha256_collisions_only_e5(states)
    assert_committed_e5_collision_groups(states)
    clone = copy.deepcopy(states)
    donor = next(row for row in clone if row.get("file") == "empty-e6-dark-en-1440.png")
    victim = next(row for row in clone if row.get("file") == "empty-e6-light-en-1440.png")
    victim["sha256"] = donor["sha256"]
    with pytest.raises(RuntimeError, match="not in ruled E5 group"):
        capture.assert_sha256_collisions_only_e5(clone)
    intra = copy.deepcopy(states)
    light = next(
        row for row in intra
        if row.get("file") == "empty-e5-credit-light-en-1440.png")
    dup = copy.deepcopy(light)
    dup["file"] = "empty-e5-credit-dup-light-en-1440.png"
    dup["crop_selector"] = 'section#credit [data-mc-empty="e5"]-dup'
    intra.append(dup)
    with pytest.raises(AssertionError):
        assert_committed_e5_collision_groups(intra)
    cross = copy.deepcopy(states)
    credit = next(
        row for row in cross
        if row.get("file") == "empty-e5-credit-light-en-1440.png")
    growth = next(
        row for row in cross
        if row.get("file") == "empty-e5-growth-dark-zh-390.png")
    growth["sha256"] = credit["sha256"]
    with pytest.raises(AssertionError):
        assert_committed_e5_collision_groups(cross)


def _p3_producer_crop_keys() -> set[str]:
    from scripts import capture_macro_command_p3 as p3

    keys = set(re.findall(
        r'extra\["(\w+)"\]\s*=', inspect.getsource(p3._write_element_shot)))
    keys.add("element_text_sha256")
    return keys


def _p4_extra_info_boundary_keys() -> set[str]:
    """Keys the extra→info list at :466-478 / :989-999 / :1139-1150 copies."""
    from scripts import capture_macro_command_p4 as capture

    keys: set[str] = set()
    for fn in (
            capture._capture_clip,
            capture._capture_metric_table,
            capture._capture_hub_e5_cell,
    ):
        keys.update(re.findall(r'extra\.get\("(\w+)"\)', inspect.getsource(fn)))
    return keys


def _info_through_p4_extra_boundary(extra: dict) -> dict:
    """Feed producer extra through the real extra.get() key list, then _state_row."""
    info = {
        "applied_locale": "en",
        "applied_theme": "dark",
        "bytes": 10,
        "png_height": 10,
        "png_width": 10,
        "sha256": "a" * 64,
        "css_width": 10,
        "css_height": 10,
        "clip": {"x": 0, "y": 0, "width": 10, "height": 10},
        "dpr": 2,
    }
    for key in _p4_extra_info_boundary_keys():
        if key in extra:
            info[key] = extra[key]
    return info


def test_state_row_forwards_producer_extra_keys() -> None:
    """r10 MINOR-2: written row ⊇ producer keys after the real extra→info list."""
    from scripts import capture_macro_command_p4 as capture

    producer_keys = _p3_producer_crop_keys()
    extra = {key: f"fwd-{key}" for key in producer_keys}
    extra["new_probe"] = "must-not-pass-the-key-list"
    info = _info_through_p4_extra_boundary(extra)
    assert "new_probe" not in info
    assert producer_keys <= set(info), sorted(producer_keys - set(info))
    row = capture._state_row(
        "state-growth-foot-dark-en-1440.png", "dark", "en", "desktop", info,
        fixture="builder-payload", verified_how="test",
        section="growth", crop=True)
    assert producer_keys <= set(row), sorted(producer_keys - set(row))
    assert "new_probe" not in row


def test_e5_request_url_matches_fragment_target() -> None:
    """NIT-2: stalled requestUrl matches the section fragmentTarget."""
    probes = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p4" / "probes.json")
        .read_text(encoding="utf-8"))
    for key, row in probes.items():
        if not str(key).startswith("e5_timeout_"):
            continue
        assert row.get("requestUrl"), key
        assert row["requestUrl"].endswith(row["fragmentTarget"]), key
        assert abs(row["elapsedMs"] - (row["cloneSeenAtMs"] - row["requestSeenAtMs"])) < 1e-6

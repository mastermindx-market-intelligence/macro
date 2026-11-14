"""tests/test_china_act_now.py — Pure-assembler tests for engine/china_act_now.py (W8-R3).

Tests:
  1. Lane mapping per urgency/reco vocab
  2. Baijiu dual-read fixture (reco=avoid + Trough/osc>0 => BOTH lanes with tape chip)
  3. Null-safety: no theme artifact; no forward_log
  4. No BUY-family words in bottoming lane strings
  5. Ordering determinism within lanes
  6. Dual-read (FT-R1): reduce row gets dual_chip set; both lanes retain the row
  7. Sector routing: urgency vocab matches cycles.py literals
  8. Empty inputs yield empty lanes with no crash
"""
from __future__ import annotations

from copy import deepcopy
import re
import sys
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.china_act_now import assemble_act_now  # noqa: E402

# ─────────────────────────────────────── helpers ──────────────────────────────

def _sector(ticker: str, urgency: str, tag: str = "", name: str | None = None,
            dir_: str = "up", tag_zh: str | None = None) -> dict:
    """Minimal sector card mirroring build_china._sector_cards() shape."""
    return {
        "ticker": ticker,
        "name": name or ticker,
        "label": "TEST",
        "state": "TEST",
        "dir": dir_,
        "entry": {"urgency": urgency, "tag": tag, "tag_zh": tag_zh, "days_hi": None},
    }


def _theme_intel(buy: list, pullback: list, reduce: list) -> dict:
    """Minimal theme_intel dict."""
    return {
        "as_of": "2026-07-08",
        "themes": [],
        "act_now": {
            "buy": buy,
            "add_on_pullback": pullback,
            "reduce": reduce,
        },
    }


def _theme_item(id_: str, name: str, name_zh: str, score: int, reco: str,
                reco_en: str, reco_zh: str) -> dict:
    return {
        "id": id_, "name": name, "name_zh": name_zh,
        "score": score,
        "action": reco, "action_en": reco_en, "action_zh": reco_zh,
        "label": "dominant", "entry_quality": 1.0, "clean_entry": True,
        "reasons": [f"20d +10.0% vs CSI 300"],
    }


def _cycle_row(id_: str, name: str, kind: str, phase: str,
               osc_slope: float, pos: float = 0.3,
               rs_63d: float = -10.0, rs_rank: int = 15) -> dict:
    return {
        "date": "2026-07-08",
        "id": id_,
        "kind": kind,
        "name": name,
        "phase": phase,
        "osc_slope": osc_slope,
        "pos": pos,
        "rs_63d": rs_63d,
        "rs_rank": rs_rank,
        "signal": None,
        "above200d": False,
    }


# ─────────────────────────────────────── 1. lane mapping ─────────────────────

class TestLaneMapping:
    """Sector urgency vocab routes to the correct lane."""

    def test_now_sector_to_buy_now(self):
        s = [_sector("A", "now", "BUY NOW")]
        r = assemble_act_now(s, None, None)
        assert [x["id"] for x in r["lanes"]["buy_now"]] == ["A"]
        assert r["lanes"]["wait_pullback"] == []
        assert r["lanes"]["reduce_avoid"] == []

    def test_imminent_sector_to_wait_pullback(self):
        # 'imminent' = cycles.py BUY SOON fall-through: conditional trigger not yet
        # fired.  Routing fix: imminent must NOT land in buy_now; goes to wait_pullback.
        s = [_sector("B", "imminent")]
        r = assemble_act_now(s, None, None)
        assert "B" in [x["id"] for x in r["lanes"]["wait_pullback"]], \
            "imminent must route to wait_pullback (BUY SOON — don't front-run)"
        assert "B" not in [x["id"] for x in r["lanes"]["buy_now"]], \
            "imminent must NOT be in buy_now after routing fix"

    def test_soon_sector_to_wait_pullback(self):
        # 'soon' means "cycle low due in ~N days — watch, don't front-run".
        # Design W8-R3: Buy Now = clean-entry (now/imminent only); soon → wait lane.
        s = [_sector("C", "soon", "WATCH")]
        r = assemble_act_now(s, None, None)
        assert "C" in [x["id"] for x in r["lanes"]["wait_pullback"]]
        assert "C" not in [x["id"] for x in r["lanes"]["buy_now"]]

    def test_caution_take_profits_to_reduce(self):
        # TAKE PROFITS has urgency='caution' in cycles.py (TOP WATCH state).
        # It must land in reduce_avoid, NOT wait_pullback.
        s = [_sector("TP", "caution", "TAKE PROFITS")]
        r = assemble_act_now(s, None, None)
        assert "TP" in [x["id"] for x in r["lanes"]["reduce_avoid"]], \
            "caution+TAKE PROFITS must route to reduce_avoid"
        assert "TP" not in [x["id"] for x in r["lanes"]["wait_pullback"]]

    def test_later_sector_to_wait_pullback(self):
        # 'later' (mid-cycle dip, not yet the cycle low) → wait_pullback
        s = [_sector("L", "later", "WAIT")]
        r = assemble_act_now(s, None, None)
        assert "L" in [x["id"] for x in r["lanes"]["wait_pullback"]]
        assert "L" not in [x["id"] for x in r["lanes"]["buy_now"]]
        assert "L" not in [x["id"] for x in r["lanes"]["reduce_avoid"]]

    def test_caution_dont_chase_to_wait_pullback(self):
        s = [_sector("D", "caution", "DON'T CHASE")]
        r = assemble_act_now(s, None, None)
        assert "D" in [x["id"] for x in r["lanes"]["wait_pullback"]]
        assert "D" not in [x["id"] for x in r["lanes"]["reduce_avoid"]]

    def test_hold_sector_to_wait_pullback(self):
        s = [_sector("E", "hold", "HOLD")]
        r = assemble_act_now(s, None, None)
        assert "E" in [x["id"] for x in r["lanes"]["wait_pullback"]]

    def test_caution_unconfirmed_to_reduce(self):
        # em-dash literal must match — same as cycles.py
        s = [_sector("F", "caution", "UNCONFIRMED — HIGH RISK")]
        r = assemble_act_now(s, None, None)
        assert "F" in [x["id"] for x in r["lanes"]["reduce_avoid"]]
        assert "F" not in [x["id"] for x in r["lanes"]["wait_pullback"]]

    def test_exit_sector_to_reduce(self):
        s = [_sector("G", "exit", "TAKE PROFITS")]
        r = assemble_act_now(s, None, None)
        assert "G" in [x["id"] for x in r["lanes"]["reduce_avoid"]]

    def test_avoid_sector_to_reduce(self):
        s = [_sector("H", "avoid", "AVOID")]
        r = assemble_act_now(s, None, None)
        assert "H" in [x["id"] for x in r["lanes"]["reduce_avoid"]]

    def test_sector_kind_chip(self):
        s = [_sector("X", "now")]
        r = assemble_act_now(s, None, None)
        assert r["lanes"]["buy_now"][0]["kind"] == "SECTOR"

    def test_sector_tag_zh_threaded(self):
        # bilingual parity (DESIGN_DOCTRINE Law 2/§5.5): cycles.py emits tag_zh
        # alongside tag; the LaneRow must carry it so the ZH glance tier doesn't
        # fall back to raw English.
        s = [_sector("Z", "caution", "UNCONFIRMED — HIGH RISK",
                     tag_zh="未确认 — 高风险")]
        r = assemble_act_now(s, None, None)
        row = r["lanes"]["reduce_avoid"][0]
        assert row["tag"] == "UNCONFIRMED — HIGH RISK"
        assert row["tag_zh"] == "未确认 — 高风险"

    def test_sector_tag_zh_absent_is_none(self):
        # entry dicts without a tag_zh twin (older artifacts) must yield None,
        # not KeyError — the template falls back to the EN tag.
        s = [_sector("Y", "avoid", "AVOID")]
        r = assemble_act_now(s, None, None)
        row = r["lanes"]["reduce_avoid"][0]
        assert row["tag_zh"] is None

    def test_blank_row_has_tag_zh_key(self):
        # every LaneRow kind (theme/sector/cycle) shares _blank_row; the key must
        # exist on all of them or the jinja missing-key gotcha bites the template.
        rows = [_cycle_row("801010", "Agriculture", "sector", "Trough", osc_slope=3.9)]
        r = assemble_act_now([], None, rows)
        assert "tag_zh" in r["lanes"]["bottoming_watch"][0]


class TestThemeLaneMapping:
    """Theme act_now items route to the correct lane."""

    def _theme(self, score=60, reco="accumulate"):
        return _theme_item("t1", "Semis", "半导体", score, reco, "ACCUMULATE", "加仓")

    def test_buy_theme_to_buy_now(self):
        ti = _theme_intel(buy=[self._theme(69)], pullback=[], reduce=[])
        r = assemble_act_now([], ti, None)
        assert len(r["lanes"]["buy_now"]) == 1
        assert r["lanes"]["buy_now"][0]["kind"] == "THEME"
        assert r["lanes"]["buy_now"][0]["score"] == 69

    def test_pullback_theme_to_wait_pullback(self):
        ti = _theme_intel(buy=[], pullback=[self._theme(60)], reduce=[])
        r = assemble_act_now([], ti, None)
        assert len(r["lanes"]["wait_pullback"]) == 1

    def test_reduce_theme_to_reduce_avoid(self):
        ti = _theme_intel(buy=[], pullback=[],
                          reduce=[_theme_item("t2","Solar","光伏",25,"avoid","AVOID","回避")])
        r = assemble_act_now([], ti, None)
        assert len(r["lanes"]["reduce_avoid"]) == 1

    def test_buy_sorted_score_desc(self):
        items = [
            _theme_item("a","A","A",40,"accumulate","ACCUM","加仓"),
            _theme_item("b","B","B",70,"accumulate","ACCUM","加仓"),
            _theme_item("c","C","C",55,"accumulate","ACCUM","加仓"),
        ]
        ti = _theme_intel(buy=items, pullback=[], reduce=[])
        r = assemble_act_now([], ti, None)
        scores = [x["score"] for x in r["lanes"]["buy_now"]]
        assert scores == sorted(scores, reverse=True), "buy_now must be score-desc"

    def test_reduce_sorted_score_asc(self):
        items = [
            _theme_item("a","A","A",35,"avoid","AVOID","回避"),
            _theme_item("b","B","B",20,"avoid","AVOID","回避"),
            _theme_item("c","C","C",27,"avoid","AVOID","回避"),
        ]
        ti = _theme_intel(buy=[], pullback=[], reduce=items)
        r = assemble_act_now([], ti, None)
        scores = [x["score"] for x in r["lanes"]["reduce_avoid"]]
        assert scores == sorted(scores), "reduce_avoid must be score-asc"


# ──────────────────────────────── 2. baijiu dual-read fixture ─────────────────

class TestBaijuiDualRead:
    """FT-R1: cn_baijiu in reduce AND bottoming_watch must appear in BOTH."""

    def _setup(self):
        # cn_baijiu in reduce (reco=avoid/trim)
        baijiu_reduce = _theme_item(
            "cn_baijiu", "Baijiu / Liquor", "白酒/白酒", 31,
            "avoid", "AVOID", "回避",
        )
        ti = _theme_intel(buy=[], pullback=[], reduce=[baijiu_reduce])
        # cn_baijiu in forward_log: Trough, osc_slope=+0.1 (R7 evidence)
        cycle = [_cycle_row("b-cn_baijiu", "Baijiu / Liquor", "basket",
                             "Trough", osc_slope=0.1, pos=0.3, rs_63d=-24.1)]
        return ti, cycle

    def test_baijiu_in_reduce_lane(self):
        ti, cycle = self._setup()
        r = assemble_act_now([], ti, cycle)
        ids_reduce = [x["id"] for x in r["lanes"]["reduce_avoid"]]
        assert "cn_baijiu" in ids_reduce

    def test_baijiu_in_bottoming_lane(self):
        ti, cycle = self._setup()
        r = assemble_act_now([], ti, cycle)
        ids_bot = [x["id"] for x in r["lanes"]["bottoming_watch"]]
        assert "b-cn_baijiu" in ids_bot

    def test_baijiu_dual_read_with_prefix_mismatch(self):
        """FT-R1: theme reduce id='cn_baijiu' and basket cycle id='b-cn_baijiu' must trigger dual_read.
        This is the real live scenario: forward_log basket rows use 'b-' prefix, theme ids do not.
        The assembler must strip 'b-' to normalize before intersection."""
        ti, cycle = self._setup()
        r = assemble_act_now([], ti, cycle)
        reduce_rows = {x["id"]: x for x in r["lanes"]["reduce_avoid"]}
        bot_ids = {x["id"] for x in r["lanes"]["bottoming_watch"]}
        # cn_baijiu (theme) must be in reduce
        assert "cn_baijiu" in reduce_rows, "theme reduce row must be present"
        # b-cn_baijiu (basket cycle) must be in bottoming
        assert "b-cn_baijiu" in bot_ids, "basket bottoming row must be present"
        # dual_read must be True on the reduce row (b- stripped for matching)
        row = reduce_rows["cn_baijiu"]
        assert row["dual_read"] is True, \
            "dual_read must fire when cycle id='b-cn_baijiu' matches theme id='cn_baijiu'"
        assert row["dual_chip_en"] is not None
        assert "洗盘" in (row["dual_chip_zh"] or "")

    def test_dual_read_when_ids_match(self):
        """When a reduce item's id appears in cycle rows, dual_read=True and chip is set."""
        reduce_item = _theme_item(
            "cn_test", "Test Basket", "测试", 28, "avoid", "AVOID", "回避",
        )
        ti = _theme_intel(buy=[], pullback=[], reduce=[reduce_item])
        cycle = [_cycle_row("cn_test", "Test Basket", "basket",
                             "Trough", osc_slope=0.5, pos=0.1)]
        r = assemble_act_now([], ti, cycle)
        reduce_rows = {x["id"]: x for x in r["lanes"]["reduce_avoid"]}
        bot_ids = {x["id"] for x in r["lanes"]["bottoming_watch"]}
        assert "cn_test" in reduce_rows, "reduce must contain cn_test"
        assert "cn_test" in bot_ids, "bottoming must contain cn_test"
        row = reduce_rows["cn_test"]
        assert row["dual_read"] is True
        assert row["dual_chip_en"] is not None
        assert row["dual_chip_zh"] is not None
        assert "洗盘" in row["dual_chip_zh"]

    def test_dual_read_not_merged(self):
        """The rows remain in BOTH lanes — never removed from either."""
        reduce_item = _theme_item(
            "cn_test", "Test Basket", "测试", 28, "avoid", "AVOID", "回避",
        )
        ti = _theme_intel(buy=[], pullback=[], reduce=[reduce_item])
        cycle = [_cycle_row("cn_test", "Test Basket", "basket",
                             "Trough", osc_slope=0.5, pos=0.1)]
        r = assemble_act_now([], ti, cycle)
        assert any(x["id"] == "cn_test" for x in r["lanes"]["reduce_avoid"])
        assert any(x["id"] == "cn_test" for x in r["lanes"]["bottoming_watch"])


# ─────────────────────────────── 3. null safety ───────────────────────────────

class TestNullSafety:
    def test_no_theme_intel(self):
        """None theme_intel → themes omitted + note + no crash."""
        r = assemble_act_now([], None, None)
        assert r["lanes"]["buy_now"] == []
        assert r["lanes"]["wait_pullback"] == []
        assert r["lanes"]["reduce_avoid"] == []
        assert any("theme" in n for n in r["notes"])

    def test_no_forward_log(self):
        """None cycle_rows → bottoming lane empty + note."""
        r = assemble_act_now([], None, None)
        assert r["lanes"]["bottoming_watch"] == []
        assert any("forward_log" in n for n in r["notes"])

    def test_empty_forward_log(self):
        """Empty list cycle_rows → bottoming empty, no note."""
        r = assemble_act_now([], None, [])
        assert r["lanes"]["bottoming_watch"] == []

    def test_no_crash_empty_sectors(self):
        r = assemble_act_now([], None, None)
        assert "lanes" in r

    def test_cycle_row_missing_osc_slope(self):
        """Rows with missing osc_slope are skipped (null-safe)."""
        rows = [{"id": "x", "kind": "sector", "name": "X", "phase": "Trough",
                 "osc_slope": None, "pos": 0.0, "rs_63d": 0.0, "rs_rank": 1}]
        r = assemble_act_now([], None, rows)
        assert r["lanes"]["bottoming_watch"] == []

    def test_cycle_row_non_trough_skipped(self):
        """Rows where phase != Trough are skipped."""
        rows = [_cycle_row("y", "Y", "sector", "Peak", osc_slope=5.0)]
        r = assemble_act_now([], None, rows)
        assert r["lanes"]["bottoming_watch"] == []

    def test_cycle_row_negative_slope_skipped(self):
        """Rows where osc_slope <= 0 are skipped (not turning)."""
        rows = [_cycle_row("z", "Z", "sector", "Trough", osc_slope=-1.0)]
        r = assemble_act_now([], None, rows)
        assert r["lanes"]["bottoming_watch"] == []


# ─────────────────── 4. no BUY-family words in bottoming lane ─────────────────

_BUY_RE = re.compile(r"\b(buy|entry|accumulate|enter)\b", re.IGNORECASE)

class TestBottomingLaneCopyLaw:
    """F1 / W8-R3 copy law: bottoming lane row fields must not contain buy-family words."""

    def _all_strings(self, row: dict) -> list[str]:
        """Return all string fields of a bottoming row."""
        fields = ["name", "tag", "reco", "reco_en", "reco_zh",
                  "dual_chip_en", "dual_chip_zh"]
        return [str(row.get(f) or "") for f in fields]

    def test_basket_row_no_buy_words(self):
        rows = [_cycle_row("b-test", "Test Basket", "basket", "Trough", osc_slope=2.0)]
        r = assemble_act_now([], None, rows)
        for row in r["lanes"]["bottoming_watch"]:
            for s in self._all_strings(row):
                assert not _BUY_RE.search(s), \
                    f"BUY-family word found in bottoming row field: {s!r}"

    def test_sector_row_no_buy_words(self):
        rows = [_cycle_row("801010", "Agriculture", "sector", "Trough", osc_slope=3.9)]
        r = assemble_act_now([], None, rows)
        for row in r["lanes"]["bottoming_watch"]:
            for s in self._all_strings(row):
                assert not _BUY_RE.search(s), \
                    f"BUY-family word found in bottoming row field: {s!r}"

    def test_mixed_rows_no_buy_words(self):
        rows = [
            _cycle_row("b-a", "Alpha Basket", "basket", "Trough", osc_slope=1.0),
            _cycle_row("801150", "Pharma", "sector", "Trough", osc_slope=8.3),
        ]
        r = assemble_act_now([], None, rows)
        for row in r["lanes"]["bottoming_watch"]:
            for s in self._all_strings(row):
                assert not _BUY_RE.search(s), \
                    f"BUY-family word found in bottoming row: {s!r}"


# ─────────────────────────────── 5. ordering determinism ─────────────────────

class TestOrdering:
    def test_buy_now_themes_before_sectors(self):
        """Themes appear before sectors in buy_now (themes sorted first, then sectors)."""
        ti = _theme_intel(
            buy=[_theme_item("t1", "Pharma", "医药", 69, "accumulate", "ACCUM", "加仓")],
            pullback=[], reduce=[],
        )
        sectors = [_sector("SEC1", "now")]
        r = assemble_act_now(sectors, ti, None)
        kinds = [x["kind"] for x in r["lanes"]["buy_now"]]
        assert kinds[0] == "THEME", "themes appear before sectors in buy_now"

    def test_bottoming_sorted_osc_desc(self):
        rows = [
            _cycle_row("a", "A", "sector", "Trough", osc_slope=1.0),
            _cycle_row("b", "B", "basket", "Trough", osc_slope=8.6),
            _cycle_row("c", "C", "sector", "Trough", osc_slope=3.5),
        ]
        r = assemble_act_now([], None, rows)
        slopes = [x["osc_slope"] for x in r["lanes"]["bottoming_watch"]]
        assert slopes == sorted(slopes, reverse=True), "bottoming must be osc_slope desc"

    def test_pull_themes_score_desc(self):
        items = [
            _theme_item("a","A","A",40,"accumulate","ACCUM","加仓"),
            _theme_item("b","B","B",74,"accumulate","ACCUM","加仓"),
        ]
        ti = _theme_intel(buy=[], pullback=items, reduce=[])
        r = assemble_act_now([], ti, None)
        scores = [x["score"] for x in r["lanes"]["wait_pullback"]]
        assert scores == sorted(scores, reverse=True)


# ─────────────────────── 6. all lane keys always present ─────────────────────

class TestLaneKeys:
    """All four lane keys are always present, even when empty."""

    def test_all_keys_present_on_empty(self):
        r = assemble_act_now([], None, None)
        assert set(r["lanes"]) == {"buy_now", "wait_pullback", "bottoming_watch", "reduce_avoid"}

    def test_all_keys_present_with_data(self):
        ti = _theme_intel(
            buy=[_theme_item("t1","X","X",60,"accumulate","ACCUM","加仓")],
            pullback=[], reduce=[],
        )
        r = assemble_act_now([_sector("S1","avoid")], ti,
                              [_cycle_row("b1","B1","basket","Trough",osc_slope=1.0)])
        assert set(r["lanes"]) == {"buy_now", "wait_pullback", "bottoming_watch", "reduce_avoid"}


# ──────────────────── 7. bottoming: both kinds accepted ──────────────────────

class TestBottomingKinds:
    def test_sector_kind_classified_sector(self):
        rows = [_cycle_row("801010", "Agriculture", "sector", "Trough", osc_slope=3.9)]
        r = assemble_act_now([], None, rows)
        assert r["lanes"]["bottoming_watch"][0]["kind"] == "SECTOR"

    def test_basket_kind_classified_basket(self):
        rows = [_cycle_row("b-cn_gold", "Gold Miners", "basket", "Trough", osc_slope=1.2)]
        r = assemble_act_now([], None, rows)
        assert r["lanes"]["bottoming_watch"][0]["kind"] == "BASKET"


# ─────────────────────────────── 8. as_of and notes ──────────────────────────

class TestAsOfAndNotes:
    def test_as_of_from_theme_intel(self):
        ti = _theme_intel(buy=[], pullback=[], reduce=[])
        ti["as_of"] = "2026-07-08"
        r = assemble_act_now([], ti, None)
        assert r["as_of"] == "2026-07-08"

    def test_as_of_none_when_no_theme(self):
        r = assemble_act_now([], None, None)
        assert r["as_of"] is None

    def test_note_on_absent_theme(self):
        r = assemble_act_now([], None, None)
        assert any("theme" in n for n in r["notes"])

    def test_note_on_absent_forward_log(self):
        r = assemble_act_now([], None, None)
        assert any("forward_log" in n for n in r["notes"])


# ─────────────────── 9. W8-R7 rider — basket_turn organ chips ───────────────

class TestBasketTurnOrganRider:
    """Basket-turn organ rider (W8-R7): organ chips added to bottoming_watch rows."""

    def _basket_turn(self, states: dict) -> dict:
        """Minimal basket_turn_cn.json artifact dict."""
        return {
            "schema": "basket_turn_cn.v1",
            "as_of": "2026-07-08",
            "baskets": {
                bid: {"state": state, "evidence": []}
                for bid, state in states.items()
            },
        }

    def test_organ_absent_when_basket_turn_none(self):
        """No organ chips when basket_turn=None."""
        rows = [_cycle_row("b-cn_baijiu", "Baijiu", "basket", "Trough", osc_slope=0.5)]
        r = assemble_act_now([], None, rows, basket_turn=None)
        row = r["lanes"]["bottoming_watch"][0]
        assert row["organ_state"] is None
        assert row["organ_chip_en"] is None

    def test_turning_organ_chip_added(self):
        """TURNING state in basket_turn adds organ chip to the bottoming row."""
        rows = [_cycle_row("b-cn_baijiu", "Baijiu", "basket", "Trough", osc_slope=0.5)]
        bt = self._basket_turn({"cn_baijiu": "TURNING"})
        r = assemble_act_now([], None, rows, basket_turn=bt)
        bw = r["lanes"]["bottoming_watch"]
        assert len(bw) >= 1
        baijiu_rows = [row for row in bw if row["id"] == "b-cn_baijiu"]
        assert baijiu_rows, f"b-cn_baijiu not found in bottoming_watch: {[r['id'] for r in bw]}"
        assert baijiu_rows[0]["organ_state"] == "TURNING"
        assert baijiu_rows[0]["organ_chip_en"] == "Turning up"
        assert baijiu_rows[0]["organ_chip_zh"] == "走势转强"

    def test_confirmed_organ_chip_added(self):
        """CONFIRMED state in basket_turn adds organ chip."""
        rows = [_cycle_row("cn_semis", "Semis", "basket", "Trough", osc_slope=1.2)]
        bt = self._basket_turn({"cn_semis": "CONFIRMED"})
        r = assemble_act_now([], None, rows, basket_turn=bt)
        bw = r["lanes"]["bottoming_watch"]
        semis_rows = [row for row in bw if row["id"] == "cn_semis"]
        assert semis_rows
        assert semis_rows[0]["organ_state"] == "CONFIRMED"
        assert semis_rows[0]["organ_chip_en"] == "Trend confirmed"
        assert semis_rows[0]["organ_chip_zh"] == "走势确认"

    def test_organ_adds_not_removes(self):
        """Existing forward_log row stays even when organ state is WASHED_OUT (not TURNING)."""
        rows = [_cycle_row("b-cn_baijiu", "Baijiu", "basket", "Trough", osc_slope=0.5)]
        bt = self._basket_turn({"cn_baijiu": "WASHED_OUT"})
        r = assemble_act_now([], None, rows, basket_turn=bt)
        bw = r["lanes"]["bottoming_watch"]
        # Row should still be in the lane (not removed)
        assert any(row["id"] == "b-cn_baijiu" for row in bw)
        baijiu_rows = [row for row in bw if row["id"] == "b-cn_baijiu"]
        # WASHED_OUT gets organ_state but NOT the chip_en headline
        assert baijiu_rows[0]["organ_state"] == "WASHED_OUT"

    def test_organ_surfaces_new_turning_basket(self):
        """TURNING basket not in forward_log is surfaced as a new bottoming row."""
        # No cycle_rows (forward_log empty)
        bt = self._basket_turn({"cn_pharma": "TURNING"})
        r = assemble_act_now([], None, [], basket_turn=bt)
        bw = r["lanes"]["bottoming_watch"]
        pharma_rows = [row for row in bw if row["id"] == "cn_pharma"]
        assert pharma_rows, "TURNING basket should be surfaced as new bottoming row"
        assert pharma_rows[0]["organ_state"] == "TURNING"
        assert pharma_rows[0]["organ_chip_en"] == "Turning up"
        assert pharma_rows[0]["organ_chip_zh"] == "走势转强"

    def test_organ_no_buy_words_in_chip(self):
        """Organ chips must not contain buy/accumulate/enter words (F1 law)."""
        rows = [_cycle_row("b-cn_baijiu", "Baijiu", "basket", "Trough", osc_slope=0.5)]
        bt = self._basket_turn({"cn_baijiu": "TURNING"})
        r = assemble_act_now([], None, rows, basket_turn=bt)
        bw = r["lanes"]["bottoming_watch"]
        banned = {"buy", "accumulate", "enter"}
        for row in bw:
            for field in ["organ_chip_en", "organ_chip_zh", "name", "reco", "reco_en"]:
                val = (row.get(field) or "").lower()
                for word in banned:
                    assert word not in val, (
                        f"Banned word {word!r} found in {field}: {val!r}"
                    )

    def test_dual_read_unaffected_by_organ(self):
        """Organ rider does not interfere with existing dual-read logic."""
        ti = _theme_intel(
            buy=[], pullback=[],
            reduce=[_theme_item("cn_baijiu", "Baijiu", "白酒", 30, "reduce", "REDUCE", "减仓")],
        )
        rows = [_cycle_row("b-cn_baijiu", "Baijiu", "basket", "Trough", osc_slope=0.5)]
        bt = self._basket_turn({"cn_baijiu": "TURNING"})
        r = assemble_act_now([], ti, rows, basket_turn=bt)
        # dual_read should still be set on the reduce_avoid row (FT-R1)
        ra = r["lanes"]["reduce_avoid"]
        baijiu_ra = [row for row in ra if row["id"] == "cn_baijiu"]
        assert baijiu_ra
        assert baijiu_ra[0]["dual_read"] is True
        # Both lanes should contain the row
        bw = r["lanes"]["bottoming_watch"]
        assert any(row["id"] in ("b-cn_baijiu", "cn_baijiu") for row in bw)


# ─────────────── 10. organ-rider enrichment (Fix 1/2) ────────────────────────

def _minimal_theme_intel_with_theme(tid: str, name: str, name_zh: str,
                                     score: int, rel20: float) -> dict:
    """theme_intel dict containing one theme in themes[], no act_now items."""
    return {
        "as_of": "2026-07-08",
        "themes": [{
            "id": tid, "name": name, "name_zh": name_zh,
            "score": score, "action": "hold", "action_en": "HOLD", "action_zh": "持有",
            "perf": {"20d": {"rel": rel20}},
        }],
        "act_now": {"buy": [], "add_on_pullback": [], "reduce": []},
    }


def _minimal_ths_baskets(bid: str, name: str, name_zh: str, rel20: float) -> dict:
    """ths_baskets {id: basket} dict for a single THS basket."""
    return {bid: {"id": bid, "name": name, "name_zh": name_zh,
                  "perf": {"20d": {"rel": rel20}}}}


class TestOrganRiderEnrichment:
    """Fix 1: organ-rider rows get name/name_zh/score/reco/rel20 from theme_intel or ths_baskets."""

    def _basket_turn(self, states: dict) -> dict:
        return {
            "schema": "basket_turn_cn.v1",
            "as_of": "2026-07-08",
            "baskets": {bid: {"state": st, "evidence": []} for bid, st in states.items()},
        }

    def test_cn_id_enriched_from_theme_intel(self):
        """organ-rider row with a cn_* id present in theme_intel.themes gets name/name_zh/score/rel20."""
        ti = _minimal_theme_intel_with_theme("cn_pharma", "Pharma", "医药", 72, 0.15)
        bt = self._basket_turn({"cn_pharma": "TURNING"})
        r = assemble_act_now([], ti, [], basket_turn=bt, ths_baskets=None)
        bw = r["lanes"]["bottoming_watch"]
        rows = [row for row in bw if row["id"] == "cn_pharma"]
        assert rows, "cn_pharma organ row must be surfaced"
        row = rows[0]
        assert row["name"] == "Pharma", f"expected name='Pharma', got {row['name']!r}"
        assert row["name_zh"] == "医药"
        assert row["score"] == 72
        assert abs((row["rel20"] or 0) - 0.15) < 1e-9
        assert row["organ_chip_en"] is not None

    def test_cn_id_enriched_reco_from_theme_intel(self):
        """organ-rider row gets reco_en/reco_zh when theme_intel has them."""
        ti = _minimal_theme_intel_with_theme("cn_semis", "Semis", "半导体", 65, 0.08)
        bt = self._basket_turn({"cn_semis": "CONFIRMED"})
        r = assemble_act_now([], ti, [], basket_turn=bt)
        bw = r["lanes"]["bottoming_watch"]
        rows = [row for row in bw if row["id"] == "cn_semis"]
        assert rows
        assert rows[0]["reco_en"] == "HOLD"
        assert rows[0]["reco_zh"] == "持有"

    def test_thsc_id_enriched_from_ths_baskets(self):
        """organ-rider row with a thsc* id gets name/name_zh/rel20 from ths_baskets."""
        ths = _minimal_ths_baskets("thsc309128", "Beer", "啤酒", 0.05)
        bt = self._basket_turn({"thsc309128": "TURNING"})
        r = assemble_act_now([], None, [], basket_turn=bt, ths_baskets=ths)
        bw = r["lanes"]["bottoming_watch"]
        rows = [row for row in bw if row["id"] == "thsc309128"]
        assert rows, "thsc309128 organ row must be surfaced"
        row = rows[0]
        assert row["name"] == "Beer"
        assert row["name_zh"] == "啤酒"
        assert abs((row["rel20"] or 0) - 0.05) < 1e-9

    def test_ths_id_enriched_from_ths_baskets(self):
        """ths_* ids also resolved from ths_baskets."""
        ths = _minimal_ths_baskets("ths_baijiu", "Baijiu", "白酒", -0.03)
        bt = self._basket_turn({"ths_baijiu": "CONFIRMED"})
        r = assemble_act_now([], None, [], basket_turn=bt, ths_baskets=ths)
        bw = r["lanes"]["bottoming_watch"]
        rows = [row for row in bw if row["id"] == "ths_baijiu"]
        assert rows
        assert rows[0]["name"] == "Baijiu"
        assert rows[0]["name_zh"] == "白酒"

    def test_unknown_id_falls_back_to_slug(self):
        """Unknown id falls back to slug as name, no crash."""
        bt = self._basket_turn({"unknown_xyz": "TURNING"})
        r = assemble_act_now([], None, [], basket_turn=bt, ths_baskets=None)
        bw = r["lanes"]["bottoming_watch"]
        rows = [row for row in bw if row["id"] == "unknown_xyz"]
        assert rows, "unknown id should still produce a row"
        assert rows[0]["name"] == "unknown_xyz"  # slug fallback

    def test_b_prefix_id_canonical_lookup(self):
        """b-cn_x id resolves name via canonical cn_x key in theme_intel."""
        ti = _minimal_theme_intel_with_theme("cn_gold", "Gold Miners", "黄金", 58, 0.20)
        bt = self._basket_turn({"b-cn_gold": "TURNING"})
        r = assemble_act_now([], ti, [], basket_turn=bt)
        bw = r["lanes"]["bottoming_watch"]
        rows = [row for row in bw if row["id"] == "b-cn_gold"]
        assert rows, "b-cn_gold row must be surfaced"
        assert rows[0]["name"] == "Gold Miners"

    def test_backward_compat_no_ths_baskets_kwarg(self):
        """Calling assemble_act_now without ths_baskets kwarg works (backward-compat)."""
        bt = self._basket_turn({"cn_pharma": "TURNING"})
        # Must not raise
        r = assemble_act_now([], None, [], basket_turn=bt)
        assert "lanes" in r


class TestOrganRiderDedup:
    """Fix 2: dedup hardening — b-/non-b- variants produce at most one row."""

    def _basket_turn(self, states: dict) -> dict:
        return {
            "schema": "basket_turn_cn.v1",
            "as_of": "2026-07-08",
            "baskets": {bid: {"state": st, "evidence": []} for bid, st in states.items()},
        }

    def test_bprefix_and_canonical_produce_one_row(self):
        """organ_state_map has both b-cn_x and cn_x mapped; only one row emitted."""
        # Both keys will be in the map after the canonical registration inside the organ block
        bt = self._basket_turn({"b-cn_x": "TURNING", "cn_x": "TURNING"})
        r = assemble_act_now([], None, [], basket_turn=bt)
        bw = r["lanes"]["bottoming_watch"]
        ids = [row["id"] for row in bw]
        # At most one of b-cn_x or cn_x should appear
        count = ids.count("b-cn_x") + ids.count("cn_x")
        assert count == 1, f"expected 1 row, got {count}: {ids}"

    def test_forward_log_row_and_organ_same_id_no_dup(self):
        """Basket already in forward_log (b-cn_x); organ also fires — no duplicate row."""
        cycle = [_cycle_row("b-cn_x", "X Basket", "basket", "Trough", osc_slope=1.0)]
        bt = self._basket_turn({"cn_x": "TURNING"})  # canonical (non-b) key
        r = assemble_act_now([], None, cycle, basket_turn=bt)
        bw = r["lanes"]["bottoming_watch"]
        ids = [row["id"] for row in bw]
        count = ids.count("b-cn_x") + ids.count("cn_x")
        assert count == 1, f"expected 1 row (forward_log), got {count}: {ids}"

    def test_forward_log_row_takes_precedence(self):
        """When forward_log already has the row, the organ does not add a second row."""
        cycle = [_cycle_row("cn_y", "Y Basket", "basket", "Trough", osc_slope=2.5)]
        bt = self._basket_turn({"b-cn_y": "CONFIRMED"})
        r = assemble_act_now([], None, cycle, basket_turn=bt)
        bw = r["lanes"]["bottoming_watch"]
        ids = [row["id"] for row in bw]
        count = ids.count("cn_y") + ids.count("b-cn_y")
        assert count == 1, f"expected 1 row (forward_log), got {count}: {ids}"


# ─────────────────── 11. routing fix — imminent goes to wait_pullback ─────────

class TestImminentRouting:
    """Bug fix: urgency='imminent' (BUY SOON fall-through) must NOT land in buy_now."""

    def test_imminent_routes_to_wait_pullback(self):
        """(a) imminent sector ends up in wait_pullback, not buy_now."""
        s = [_sector("SEMI", "imminent", "BUY SOON")]
        r = assemble_act_now(s, None, None)
        wp_ids = [x["id"] for x in r["lanes"]["wait_pullback"]]
        bn_ids = [x["id"] for x in r["lanes"]["buy_now"]]
        assert "SEMI" in wp_ids, "imminent must be in wait_pullback"
        assert "SEMI" not in bn_ids, "imminent must NOT be in buy_now"

    def test_now_still_routes_to_buy_now(self):
        """(b) urgency='now' still routes to buy_now after the fix."""
        s = [_sector("ETF", "now", "BUY NOW")]
        r = assemble_act_now(s, None, None)
        bn_ids = [x["id"] for x in r["lanes"]["buy_now"]]
        wp_ids = [x["id"] for x in r["lanes"]["wait_pullback"]]
        assert "ETF" in bn_ids, "now must remain in buy_now"
        assert "ETF" not in wp_ids, "now must NOT be in wait_pullback"

    def test_imminent_and_now_together(self):
        """Both urgencies present: 'now' in buy_now, 'imminent' in wait_pullback."""
        s = [_sector("N", "now"), _sector("I", "imminent")]
        r = assemble_act_now(s, None, None)
        assert "N" in [x["id"] for x in r["lanes"]["buy_now"]]
        assert "I" in [x["id"] for x in r["lanes"]["wait_pullback"]]
        assert "I" not in [x["id"] for x in r["lanes"]["buy_now"]]
        assert "N" not in [x["id"] for x in r["lanes"]["wait_pullback"]]


# ──────────────────────── 12. href convention post-pass ───────────────────────

class TestHrefConvention:
    """(c-e) href field populated correctly by convention; href_exists guard."""

    def _bt(self, states: dict) -> dict:
        return {
            "schema": "basket_turn_cn.v1",
            "as_of": "2026-07-08",
            "baskets": {bid: {"state": st, "evidence": []} for bid, st in states.items()},
        }

    # (c) id shape -> correct href string ----------------------------------------

    def test_theme_cn_id_href(self):
        """THEME id 'cn_x' -> basket_china/cn_x.html"""
        ti = _theme_intel(
            buy=[_theme_item("cn_semis", "Semis", "半导体", 70, "accumulate", "ACCUM", "加仓")],
            pullback=[], reduce=[],
        )
        r = assemble_act_now([], ti, None)
        row = r["lanes"]["buy_now"][0]
        assert row["href"] == "basket_china/cn_semis.html"

    def test_basket_b_prefix_href(self):
        """BASKET id 'b-cn_x' -> basket_china/cn_x.html (b- stripped)."""
        cycle = [_cycle_row("b-cn_baijiu", "Baijiu", "basket", "Trough", osc_slope=1.0)]
        r = assemble_act_now([], None, cycle)
        row = r["lanes"]["bottoming_watch"][0]
        assert row["href"] == "basket_china/cn_baijiu.html"

    def test_basket_ths_prefix_href(self):
        """BASKET id starting with 'ths' -> subsector_china/{cid-with-dashes}.html"""
        cycle = [_cycle_row("ths_baijiu", "Baijiu", "basket", "Trough", osc_slope=1.0)]
        r = assemble_act_now([], None, cycle)
        row = r["lanes"]["bottoming_watch"][0]
        assert row["href"] == "subsector_china/ths-baijiu.html"

    def test_basket_thsc_prefix_href(self):
        """BASKET id 'thsc309128' -> subsector_china/thsc309128.html (no underscore)."""
        cycle = [_cycle_row("thsc309128", "Beer", "basket", "Trough", osc_slope=1.0)]
        r = assemble_act_now([], None, cycle)
        row = r["lanes"]["bottoming_watch"][0]
        assert row["href"] == "subsector_china/thsc309128.html"

    def test_sector_etf_ticker_href(self):
        """SECTOR id with '.' (ETF ticker like 512760.SS) -> sectors/512760.SS.html"""
        s = [_sector("512760.SS", "now", "BUY NOW", name="CN Semis ETF")]
        r = assemble_act_now(s, None, None)
        row = r["lanes"]["buy_now"][0]
        assert row["href"] == "sectors/512760.SS.html"

    def test_sector_sw_code_href(self):
        """SECTOR id without '.' (SW code like 801080) -> sector_cycles_china.html"""
        s = [_sector("801080", "now", "BUY NOW", name="Electronics")]
        r = assemble_act_now(s, None, None)
        row = r["lanes"]["buy_now"][0]
        assert row["href"] == "sector_cycles_china.html"

    # (d) href_exists guard -------------------------------------------------------

    def test_href_exists_false_nulls_all_hrefs(self):
        """(d) href_exists=lambda h: False forces all href fields to None."""
        s = [_sector("512760.SS", "now", "BUY NOW"), _sector("801080", "now")]
        cycle = [_cycle_row("cn_semis", "Semis", "basket", "Trough", osc_slope=1.0)]
        r = assemble_act_now(s, None, cycle, href_exists=lambda h: False)
        all_rows = (
            r["lanes"]["buy_now"]
            + r["lanes"]["wait_pullback"]
            + r["lanes"]["bottoming_watch"]
            + r["lanes"]["reduce_avoid"]
        )
        for row in all_rows:
            assert row["href"] is None, \
                f"href should be None when href_exists=False, got {row['href']!r}"

    def test_href_exists_selective(self):
        """href_exists can allow some hrefs and block others."""
        s = [_sector("512760.SS", "now"), _sector("801080", "hold")]
        allowed = {"sectors/512760.SS.html"}
        r = assemble_act_now(s, None, None, href_exists=lambda h: h in allowed)
        bn = {row["id"]: row["href"] for row in r["lanes"]["buy_now"]}
        wp = {row["id"]: row["href"] for row in r["lanes"]["wait_pullback"]}
        assert bn.get("512760.SS") == "sectors/512760.SS.html"
        assert wp.get("801080") is None

    def test_href_exists_raising_degrades_not_throws(self):
        """A raising href_exists probe (e.g. Path.exists on a path-invalid id)
        must drop only that row's link, never crash the whole board."""
        s = [_sector("512760.SS", "now"), _sector("801080", "now")]
        def _boom(h):
            raise RuntimeError("probe blew up")
        r = assemble_act_now(s, None, None, href_exists=_boom)
        rows = r["lanes"]["buy_now"]
        assert rows, "board must still assemble when href_exists raises"
        for row in rows:
            assert row["href"] is None, \
                f"raising probe must leave href None, got {row['href']!r}"

    # (e) organ-rider-surfaced BASKET rows also get hrefs -------------------------

    def test_organ_rider_basket_gets_href(self):
        """(e) BASKET rows appended to bottoming_watch by the organ rider get hrefs."""
        bt = self._bt({"cn_pharma": "TURNING"})
        r = assemble_act_now([], None, [], basket_turn=bt)
        bw = r["lanes"]["bottoming_watch"]
        pharma = [row for row in bw if row["id"] == "cn_pharma"]
        assert pharma, "cn_pharma organ-rider row must be surfaced"
        assert pharma[0]["href"] == "basket_china/cn_pharma.html"

    def test_organ_rider_b_prefix_basket_gets_href(self):
        """organ-rider BASKET with b- prefix id gets href with b- stripped."""
        bt = self._bt({"b-cn_gold": "CONFIRMED"})
        r = assemble_act_now([], None, [], basket_turn=bt)
        bw = r["lanes"]["bottoming_watch"]
        gold = [row for row in bw if row["id"] == "b-cn_gold"]
        assert gold, "b-cn_gold organ-rider row must be surfaced"
        assert gold[0]["href"] == "basket_china/cn_gold.html"

    def test_empty_id_href_stays_none(self):
        """Row with empty id gets href=None (no crash, no empty-string href)."""
        from engine.china_act_now import _blank_row
        row = _blank_row("BASKET", "", "No-id basket")
        assert row["href"] is None  # default from _blank_row
        # Verify assemble_act_now doesn't crash on empty-id cycle row
        cycle = [{"id": "", "kind": "basket", "name": "X", "phase": "Trough",
                  "osc_slope": 1.0, "pos": 0.1, "rs_63d": 0.0, "rs_rank": 1}]
        r = assemble_act_now([], None, cycle)
        bw = r["lanes"]["bottoming_watch"]
        for row in bw:
            if not row["id"]:
                assert row["href"] is None


# ───────────────────────────── 13. rel5 field ─────────────────────────────────

class TestRel5Field:
    """(f) rel5 populated from theme perf['5d']['rel']; None when absent."""

    def _ti_with_perf(self, tid: str, perf: dict) -> dict:
        """theme_intel with a single theme that has custom perf dict."""
        return {
            "as_of": "2026-07-08",
            "themes": [{"id": tid, "name": "X", "name_zh": "X", "score": 60,
                        "action": "accumulate", "action_en": "ACCUM", "action_zh": "加仓",
                        "perf": perf}],
            "act_now": {"buy": [{"id": tid, "name": "X", "name_zh": "X", "score": 60,
                                  "action": "accumulate", "action_en": "ACCUM",
                                  "action_zh": "加仓", "reasons": []}],
                        "add_on_pullback": [], "reduce": []},
        }

    def test_rel5_populated_from_theme_perf(self):
        """(f) rel5 is set from themes_by_id[tid].perf['5d']['rel']."""
        ti = self._ti_with_perf("cn_x", {"5d": {"rel": 0.034}, "20d": {"rel": 0.12}})
        r = assemble_act_now([], ti, None)
        row = r["lanes"]["buy_now"][0]
        assert abs((row["rel5"] or 0) - 0.034) < 1e-9, \
            f"expected rel5=0.034, got {row['rel5']!r}"

    def test_rel5_none_when_5d_absent(self):
        """rel5 stays None when perf has no '5d' key."""
        ti = self._ti_with_perf("cn_x", {"20d": {"rel": 0.10}})
        r = assemble_act_now([], ti, None)
        row = r["lanes"]["buy_now"][0]
        assert row["rel5"] is None

    def test_rel5_none_for_sector_rows(self):
        """Sector rows always have rel5=None (no perf lookup for sectors)."""
        s = [_sector("ETF", "now")]
        r = assemble_act_now(s, None, None)
        row = r["lanes"]["buy_now"][0]
        assert row["rel5"] is None

    def test_rel5_none_for_bottoming_rows(self):
        """Bottoming watch (cycle_row) rows have rel5=None (no theme perf source)."""
        cycle = [_cycle_row("cn_x", "X", "basket", "Trough", osc_slope=1.0)]
        r = assemble_act_now([], None, cycle)
        row = r["lanes"]["bottoming_watch"][0]
        assert row["rel5"] is None


# Exact-entity display coherence (2026-09-21). Raw evidence remains unchanged.
def _display_fixture(*, primary="add_on_pullback", reco="enter", organ="TURNING", cycle=True):
    item = {"id": "cn_semis", "name": "Semiconductors", "name_zh": "半导体",
            "score": 59, "action": reco, "action_en": reco.upper(), "action_zh": "观察"}
    from datetime import datetime
    intel = {"as_of": "2026-09-18", "themes": [dict(item, reco=reco,
             regime_demoted=False, chase_demoted=False,
             observation={"effective_as_of": "2026-09-18", "aggregate_eligible": True},
             textures={"clean_entry": {"flag": primary == "buy"}})],
             "act_now": {primary: [item]} if primary else {}}
    cycles = [{"id": "b-cn_semis", "name": "Semiconductors", "kind": "basket",
               "phase": "Trough", "osc_slope": 1.2}] if cycle else []
    # Match the accepted basket-turn artifact shape.
    tape = {"baskets": {"cn_semis": {"state": organ}}} if organ else None
    return assemble_act_now([], intel, cycles, basket_turn=tape,
                            observed_at=datetime.fromisoformat("2026-09-18T10:00:00+00:00"))


def display_rows(result):
    return [row for rows in result["display_lanes"].values() for row in rows]


def render(result):
    root = Path(__file__).resolve().parents[1]
    env = Environment(loader=FileSystemLoader(root / "templates"), autoescape=True)
    env.globals.update(t=lambda en, zh: en, tr=lambda text: text,
                       help=lambda *args, **kwargs: "")
    return env.get_template("_china_act_now_board.html.j2").render(act_now_v2=result)


def test_semiconductor_duplicate_becomes_one_card_with_both_reads():
    result = _display_fixture()
    assert len(result["lanes"]["wait_pullback"]) == 1
    assert len(result["lanes"]["bottoming_watch"]) == 1
    assert len(display_rows(result)) == 1
    row = result["display_lanes"]["wait_pullback"][0]
    assert set(row["observed_lanes"]) == {"wait_pullback", "bottoming_watch"}
    assert len(row["source_reads"]) == 2
    assert row["osc_slope"] == 1.2
    assert result["display_lanes"]["bottoming_watch"] == []


@pytest.mark.parametrize("primary,lane", [("buy", "buy_now"),
                                           ("add_on_pullback", "wait_pullback"),
                                           ("reduce", "reduce_avoid")])
def test_turn_evidence_never_overrides_existing_action(primary, lane):
    result = _display_fixture(primary=primary, reco="avoid" if primary == "reduce" else "enter")
    assert len(result["display_lanes"][lane]) == 1
    assert len(display_rows(result)) == 1


def test_projection_is_independent_of_raw_source_objects():
    result = _display_fixture()
    before = deepcopy(result["lanes"])
    display_rows(result)[0]["source_reads"][0]["row"]["name"] = "changed copy"
    display_rows(result)[0]["name"] = "changed copy"
    assert result["lanes"] == before


def test_equal_names_with_different_ids_are_not_falsely_merged():
    sectors = [{"ticker": "512760.SS", "name": "Semiconductors",
                "entry": {"urgency": "now", "tag": "BUY NOW"}}]
    intel = {"act_now": {"add_on_pullback": [{"id": "cn_semis", "name": "Semiconductors"}]}}
    result = assemble_act_now(sectors, intel, [])
    assert len(display_rows(result)) == 2
    assert len({r["canonical_display_id"] for r in display_rows(result)}) == 2


def test_missing_ids_remain_separate():
    intel = {"act_now": {"buy": [{"name": "A"}, {"name": "B"}]}}
    assert len(display_rows(assemble_act_now([], intel, []))) == 2


def test_parent_and_subtheme_remain_distinct():
    intel = {"act_now": {"buy": [{"id": "cn_semis", "name": "Semiconductors"},
                                 {"id": "cn_memory", "name": "Memory"}]}}
    assert len(display_rows(assemble_act_now([], intel, []))) == 2


def test_conflicting_action_sources_are_visible_and_not_promoted():
    # Current qualified conflicting observations stay visible. Missing-session
    # fixtures belong to the unavailable-data tests, not current advice.
    from copy import deepcopy
    ti = _continuation_fixture(clean=True)
    item = deepcopy(ti["act_now"]["buy"][0])
    item.update(action="avoid", action_en="AVOID")
    ti["act_now"]["reduce"] = [item]
    result = _continuation_board(ti, cycles=[])
    assert result["display_lanes"]["buy_now"] == []
    row = result["display_lanes"]["reduce_avoid"][0]
    assert row["action_disagreement"] is True
    assert len(row["source_reads"]) == 2
    assert "Conflicting actions" in render(result)


def test_no_turn_only_buy_promotion():
    result = _display_fixture(primary=None)
    assert result["display_lanes"]["buy_now"] == []
    assert len(result["display_lanes"]["bottoming_watch"]) == 1


def test_render_has_one_semiconductor_card_and_no_false_has_run_claim():
    html = render(_display_fixture())
    assert html.count('class="anv2-name anv2-name-link"') == 1
    assert "Entry pending" in html
    assert "but it has run" not in html
    assert "Still in favour — wait for a dip before adding" not in html


def test_watch_card_does_not_print_enter_badge():
    html = render(_display_fixture(primary=None, cycle=False))
    assert '>ENTER<' not in html


def test_buy_card_keeps_its_enter_badge():
    html = render(_display_fixture(primary="buy"))
    assert '>ENTER<' in html
    assert "Entry pending" not in html


def test_empty_projection():
    result = assemble_act_now([], None, None)
    assert all(not rows for rows in result["display_lanes"].values())


# Continuing leadership is a distinct theme presentation, not stock admission.
def _continuation_fixture(session="2026-09-21", clean=False, final="accumulate"):
    td = {"id": "cn_example", "name": "Example leader", "name_zh": "示例领涨主题",
          "score": 75, "label": "dominant", "reco": final,
          "reco_en": final.upper(), "reco_zh": "增持" if final == "accumulate" else "持有",
          "regime_demoted": False, "chase_demoted": False, "ext_abs": 0.3,
          "textures": {"clean_entry": {"flag": clean}}, "n_members": 12,
          "observation": {"effective_as_of": session, "aggregate_eligible": True}}
    item = {"id": td["id"], "name": td["name"], "name_zh": td["name_zh"],
            "score": 75, "action": "accumulate", "action_en": "ACCUMULATE", "action_zh": "增持"}
    return {"as_of": session, "themes": [td], "act_now": {
        "buy": [item] if clean else [], "add_on_pullback": [] if clean else [item],
        "reduce": [], "conflicted": []}}


def _continuation_board(ti, clock="2026-09-21T10:00:00+00:00", cycles=None):
    from datetime import datetime
    from engine.china_act_now import assemble_act_now
    return assemble_act_now([], ti, cycles, observed_at=datetime.fromisoformat(clock))


def test_continuation_final_accumulate_enters_buy_without_new_bottom():
    ti = _continuation_fixture()
    b = _continuation_board(ti)
    row, = b["display_lanes"]["buy_now"]
    assert row["entry_route"] == "continuation"
    assert "CONTINUATION" in row["reco_en"]
    assert b["display_lanes"]["wait_pullback"] == []


def test_continuation_preserves_raw_lanes_and_exact_source_evidence():
    from copy import deepcopy
    ti = _continuation_fixture()
    original = deepcopy(ti)
    b = _continuation_board(ti)
    assert ti == original
    assert b["lanes"]["buy_now"] == []
    assert len(b["lanes"]["wait_pullback"]) == 1
    row, = b["display_lanes"]["buy_now"]
    assert row["observed_lanes"] == ["wait_pullback"]
    assert row["source_reads"][0]["row"] == b["lanes"]["wait_pullback"][0]
    assert row["theme_decision"]["source_as_of"] == "2026-09-21"
    assert row["theme_decision"]["final_reco"] == "accumulate"


def test_continuation_remains_buyable_across_three_months_of_clean_flag_changes():
    from datetime import date, timedelta
    from lib import cn_calendar
    day, count = date(2026, 6, 22), 0
    while day <= date(2026, 9, 21):
        if cn_calendar.is_session(day):
            ti = _continuation_fixture(day.isoformat(), clean=bool(count % 2))
            b = _continuation_board(ti, day.isoformat() + "T10:00:00+00:00")
            row, = b["display_lanes"]["buy_now"]
            assert row["entry_route"] == "continuation"
            count += 1
        day += timedelta(days=1)
    assert count >= 60


def test_continuation_final_hold_trim_avoid_overrides_stale_affirmative_lane():
    for final in ("hold", "trim", "avoid"):
        for clean in (True, False):
            b = _continuation_board(_continuation_fixture(clean=clean, final=final))
            assert b["display_lanes"]["buy_now"] == []
            lane = "wait_pullback" if final == "hold" else "reduce_avoid"
            row, = b["display_lanes"][lane]
            assert row["reco"] == final
            assert row.get("entry_route") != "continuation"


def test_continuation_same_session_correction_removes_buy_immediately():
    ti = _continuation_fixture()
    assert _continuation_board(ti)["display_lanes"]["buy_now"]
    ti["themes"][0]["reco"] = "hold"
    ti["themes"][0]["chase_demoted"] = True
    assert _continuation_board(ti)["display_lanes"]["buy_now"] == []


def test_continuation_missing_stale_future_and_non_session_fail_closed():
    for session in (None, "bad", "2026-09-18", "2026-09-22", "2026-09-20"):
        b = _continuation_board(_continuation_fixture(session))
        assert b["display_lanes"]["buy_now"] == []
    ti = _continuation_fixture()
    ti["stale"] = True
    assert _continuation_board(ti)["display_lanes"]["buy_now"] == []
    assert _continuation_board(None)["display_lanes"]["buy_now"] == []


def test_continuation_requires_complete_final_non_us_recommendation():
    from copy import deepcopy
    for changes in ({"label": "emerging"}, {"regime_demoted": True},
                    {"chase_demoted": True}, {"ext_abs": None},
                    {"ext_abs": float("nan")}, {"textures": {}}, {"reco": "enter"}):
        ti = _continuation_fixture()
        ti["themes"][0].update(changes)
        assert _continuation_board(ti)["display_lanes"]["buy_now"] == []
    for field in ("regime_demoted", "chase_demoted", "label", "reco"):
        ti = _continuation_fixture()
        del ti["themes"][0][field]
        assert _continuation_board(ti)["display_lanes"]["buy_now"] == []
    ti = _continuation_fixture()
    ti["themes"].append(deepcopy(ti["themes"][0]))
    assert _continuation_board(ti)["display_lanes"]["buy_now"] == []


def test_continuation_never_overrides_source_conflict_or_defensive_read():
    from copy import deepcopy
    for lane in ("conflicted", "reduce"):
        ti = _continuation_fixture()
        item = deepcopy(ti["act_now"]["add_on_pullback"][0])
        item.update(action="avoid", action_en="AVOID", action_zh="回避")
        ti["act_now"][lane] = [item]
        b = _continuation_board(ti)
        assert b["display_lanes"]["buy_now"] == []


def test_continuation_render_names_its_route_not_a_fresh_bottom():
    b = _continuation_board(_continuation_fixture())
    html = render(b)
    assert 'data-entry-route="continuation"' in html
    assert '>CONTINUATION<' in html
    assert 'Theme accumulation remains in favour' in html
    assert 'Fresh setups and continuing leaders' in html
    assert 'A clean entry is open today.' not in html
    assert 'Trend accumulation remains in favour.' in html


def test_stale_clean_buy_has_no_affirmative_card_or_freshness_claim():
    ti = _continuation_fixture("2026-09-18", clean=True)
    b = _continuation_board(ti)
    assert len(b['lanes']['buy_now']) == 1
    assert b['display_lanes']['buy_now'] == []
    html = render(b)
    assert 'DATA UNAVAILABLE' in html
    assert 'Current inputs unavailable' in html
    assert 'Trend intact' not in html
    assert 'A clean entry is open today.' not in html


def test_naive_clock_refuses_continuation_without_breaking_board():
    b = _continuation_board(_continuation_fixture(clean=True), "2026-09-21T10:00:00")
    assert not b['display_lanes']['buy_now']


def test_future_technical_source_cannot_confirm_present_continuation():
    for key in ('mtf', 'tape'):
        ti = _continuation_fixture(clean=True)
        ti['themes'][0][key] = {'as_of': '2026-09-22'}
        b = _continuation_board(ti)
        assert not b['display_lanes']['buy_now']
        assert b['display_lanes']['wait_pullback'][0]['theme_decision']['status'] == 'UNAVAILABLE'


def test_continuation_respects_member_observation_coverage_and_date():
    for observation in ({'effective_as_of': '2026-09-18', 'aggregate_eligible': True},
                        {'effective_as_of': '2026-09-21', 'aggregate_eligible': False}):
        ti = _continuation_fixture()
        ti['themes'][0]['observation'] = observation
        assert not _continuation_board(ti)['display_lanes']['buy_now']


def test_continuation_does_not_reinterpret_stock_or_sector_entry_permission():
    from datetime import datetime
    sector = {'ticker': '512760.SS', 'name': 'Sector example', 'entry': {'urgency': 'soon', 'tag': 'WAIT'}}
    ti = _continuation_fixture()
    b = assemble_act_now([sector], ti, None, observed_at=datetime.fromisoformat('2026-09-21T10:00:00+00:00'))
    assert [r['id'] for r in b['display_lanes']['buy_now']] == ['cn_example']
    assert [r['id'] for r in b['display_lanes']['wait_pullback']] == ['512760.SS']
    assert b['display_lanes']['buy_now'][0]['theme_decision']['stock_entry_permission'] is False


@pytest.mark.parametrize("observation", [None, {}, [], "complete",
    {"effective_as_of": "2026-09-21"},
    {"aggregate_eligible": True},
    {"effective_as_of": "2026-09-21", "aggregate_eligible": "true"},
    {"effective_as_of": "2026-09-21", "aggregate_eligible": 1},
    {"effective_as_of": "2026-09-22", "aggregate_eligible": True}])
@pytest.mark.parametrize("clean", [False, True])
def test_missing_or_malformed_member_evidence_cannot_authorize_a_theme_buy(observation, clean):
    ti = _continuation_fixture(clean=clean)
    ti["themes"][0]["observation"] = observation
    original = deepcopy(ti)
    board = _continuation_board(ti)
    assert not board["display_lanes"]["buy_now"]
    row, = board["display_lanes"]["wait_pullback"]
    assert row["theme_decision"]["status"] == "UNAVAILABLE"
    assert row.get("entry_route") != "continuation"
    assert ti == original
    assert len(board["lanes"]["buy_now" if clean else "wait_pullback"]) == 1


def test_current_eligible_member_evidence_restores_continuation():
    ti = _continuation_fixture()
    ti["themes"][0]["observation"]["aggregate_eligible"] = False
    assert not _continuation_board(ti)["display_lanes"]["buy_now"]
    ti["themes"][0]["observation"]["aggregate_eligible"] = True
    assert _continuation_board(ti)["display_lanes"]["buy_now"][0]["entry_route"] == "continuation"


def test_unavailable_theme_suppresses_unqualified_metrics_but_retains_source_reads():
    ti = _continuation_fixture(clean=True)
    td = ti['themes'][0]
    td.update(perf={'5d': {'rel': 0.137}, '20d': {'rel': 0.215}},
              breadth={'pct50': 0.9}, leadership={'breadth': 'broad', 'top': []})
    ti['act_now']['buy'][0]['reasons'] = ['accelerating']
    td['observation']['aggregate_eligible'] = False
    board = _continuation_board(ti)
    row, = board['display_lanes']['wait_pullback']
    for key in ('score', 'rel5', 'rel20', 'breadth_pct50', 'leadership', 'n_members'):
        assert row[key] is None
    assert row['reasons'] == []
    assert row['source_reads'][0]['row']['score'] == 75
    assert row['source_reads'][0]['row']['rel5'] == 0.137
    html = render(board)
    assert 'Data status' in html
    assert 'accelerating' not in html and '+13.7' not in html and '+21.5' not in html
    assert 'anv2-score-hi' not in html and 'anv2-chip-reco-hold' not in html


def test_unsettled_current_session_is_disclosed_without_inventing_finality():
    ti = _continuation_fixture()
    early = _continuation_board(ti, '2026-09-21T08:00:00+00:00')
    assert not early['display_lanes']['buy_now']
    row, = early['display_lanes']['wait_pullback']
    assert row['theme_decision']['source_status'] == 'UNSETTLED'
    assert 'SESSION SETTLING' in render(early) and 'Session not yet settled' in render(early)
    assert _continuation_board(ti)['display_lanes']['buy_now']


def test_final_producer_owns_translated_recommendation_words():
    ti = _continuation_fixture(final='hold')
    ti['themes'][0].update(reco_en='WAIT FOR ENTRY', reco_zh='等待入场条件')
    row, = _continuation_board(ti)['display_lanes']['wait_pullback']
    assert row['reco_en'] == 'WAIT FOR ENTRY'
    assert row['reco_zh'] == '等待入场条件'


def test_continuations_join_existing_theme_score_order_not_end_of_lane():
    ti = _continuation_fixture()
    second = deepcopy(ti['themes'][0])
    second.update(id='cn_lower', score=60, label='emerging', reco='enter')
    second['textures']['clean_entry']['flag'] = True
    ti['themes'].append(second)
    ti['act_now']['buy'] = [{'id': 'cn_lower', 'name': 'Lower score', 'score': 60,
                              'action': 'enter', 'action_en': 'ENTER'}]
    rows = _continuation_board(ti)['display_lanes']['buy_now']
    assert [row['id'] for row in rows] == ['cn_example', 'cn_lower']
    assert [row['score'] for row in rows] == [75, 60]


@pytest.mark.parametrize('final,lane', [('accumulate', 'add_on_pullback'), ('avoid', 'reduce'), ('trim', 'reduce')])
def test_unavailable_theme_has_neutral_status_in_row_and_hover(final, lane):
    from bs4 import BeautifulSoup
    ti = _continuation_fixture(final=final)
    item = ti['act_now']['add_on_pullback'].pop()
    item.update(action=final, action_en=final.upper())
    ti['act_now'][lane] = [item]
    ti['themes'][0]['observation']['aggregate_eligible'] = False
    board = _continuation_board(ti)
    rows = [row for lane_rows in board['display_lanes'].values() for row in lane_rows]
    row, = rows
    assert row['reco'] is None
    assert row['reco_en'] == 'DATA UNAVAILABLE'
    assert row['source_reads'][0]['row']['reco'] == final
    html = BeautifulSoup(render(board), 'html.parser')
    pop = html.select_one('.row-pop-decision')
    assert pop is not None
    assert 'Theme basket' in pop.get_text() and 'Sector pulse' not in pop.get_text()
    assert 'Data status' in pop.get_text()
    assert 'DATA UNAVAILABLE' in pop.select_one('.row-pop-tag').get_text()
    assert not html.select('.anv2-chip-reco-hold, .anv2-chip-reco-avoid, .anv2-chip-reco-trim')


@pytest.mark.parametrize('final', [None, 'unsupported'])
def test_unknown_final_recommendation_is_unavailable_not_trend_intact(final):
    from bs4 import BeautifulSoup
    ti = _continuation_fixture()
    ti['themes'][0]['reco'] = final
    board = _continuation_board(ti)
    row, = board['display_lanes']['wait_pullback']
    assert row['theme_decision']['status'] == 'UNAVAILABLE'
    pop = BeautifulSoup(render(board), 'html.parser').select_one('.row-pop-decision')
    assert 'Current inputs unavailable' in pop.get_text()
    assert 'Trend intact' not in pop.get_text()


@pytest.mark.parametrize('final', ['accumulate', 'hold', 'trim', 'avoid', None])
def test_settling_copy_does_not_infer_an_unchanged_thesis(final):
    ti = _continuation_fixture()
    ti['themes'][0]['reco'] = final
    html = render(_continuation_board(ti, '2026-09-21T08:00:00+00:00'))
    assert 'Session not yet settled' in html
    assert 'not a change in the theme thesis' not in html
    assert '不表示主题逻辑发生变化' not in html
    assert 'No new entry is confirmed' in html


@pytest.mark.parametrize('clock', ['2026-09-21T08:00:00+00:00', '2026-09-22T10:00:00+00:00'])
def test_unavailable_dual_read_clears_derived_advice_but_keeps_source_evidence(clock):
    from bs4 import BeautifulSoup
    ti = _continuation_fixture(final='avoid')
    item = ti['act_now']['add_on_pullback'].pop()
    item.update(action='avoid', action_en='AVOID')
    ti['act_now']['reduce'] = [item]
    cycles = [{'id': 'b-cn_example', 'kind': 'basket', 'name': 'Example leader',
               'phase': 'Trough', 'osc_slope': 1.2, 'pos': .3, 'rs_63d': .05}]
    board = _continuation_board(ti, clock, cycles)
    row, = board['display_lanes']['reduce_avoid']
    assert row['theme_decision']['status'] == 'UNAVAILABLE'
    assert row['dual_read'] is False
    assert row['dual_chip_en'] is row['dual_chip_zh'] is None
    assert row['action_disagreement'] is False
    assert board['lanes']['reduce_avoid'][0]['dual_read'] is True
    assert any(r['row']['dual_read'] for r in row['source_reads'])
    html = BeautifulSoup(render(board), 'html.parser')
    assert 'may be bottoming' not in html.get_text().lower()
    assert 'longer trend still says reduce' not in str(html)
    assert board['theme_data_note']['en'] in html.get_text()


@pytest.mark.parametrize('clock', ['2026-09-21T08:00:00+00:00', '2026-09-22T10:00:00+00:00'])
def test_all_unavailable_theme_cards_have_one_visible_board_disclosure(clock):
    board = _continuation_board(_continuation_fixture(), clock)
    note = board['theme_data_note']
    assert note and note['en'] and note['zh']
    assert render(board).count(note['en']) == 1
    assert 'theme recommendations' in note['en']
    assert 'lane labels' not in note['en'] and 'cards' not in note['en']


@pytest.mark.parametrize('degraded', [False, True])
def test_data_note_is_partial_without_disqualifying_the_current_theme(degraded):
    from copy import deepcopy
    ti = _continuation_fixture()
    second = deepcopy(ti['themes'][0])
    second['id'] = 'cn_second'
    second['observation']['aggregate_eligible'] = not degraded
    ti['themes'].append(second)
    item = deepcopy(ti['act_now']['add_on_pullback'][0])
    item['id'] = 'cn_second'
    ti['act_now']['add_on_pullback'].append(item)
    board = _continuation_board(ti)
    assert any(row['id'] == 'cn_example' for row in board['display_lanes']['buy_now'])
    if degraded:
        assert board['theme_data_note']['en'].startswith('Some theme inputs')
    else:
        assert board['theme_data_note'] is None
        assert 'data-theme-data-status' not in render(board)


def test_current_defensive_dual_read_is_preserved():
    ti = _continuation_fixture(final='avoid')
    item = ti['act_now']['add_on_pullback'].pop()
    item.update(action='avoid', action_en='AVOID')
    ti['act_now']['reduce'] = [item]
    cycles = [{'id': 'b-cn_example', 'kind': 'basket', 'name': 'Example leader',
               'phase': 'Trough', 'osc_slope': 1.2, 'pos': .3, 'rs_63d': .05}]
    row, = _continuation_board(ti, cycles=cycles)['display_lanes']['reduce_avoid']
    assert row['dual_read'] is True and row['reco'] == 'avoid'
    assert 'may be bottoming' in render(_continuation_board(ti, cycles=cycles)).lower()


# EMERGING/ENTER is a theme-level continuation decision, not stock admission.
def _emerging_enter_fixture(session="2026-09-21", clean=False, final="enter"):
    td = {
        "id": "cn_emerging", "name": "Emerging leader", "name_zh": "新兴领涨主题",
        "score": 68, "label": "emerging", "reco": final,
        "reco_en": final.upper(), "reco_zh": "建仓" if final == "enter" else "持有",
        "regime_demoted": False, "chase_demoted": False, "ext_abs": None,
        "textures": {"clean_entry": {"flag": clean}}, "n_members": 10,
        "observation": {"effective_as_of": session, "aggregate_eligible": True},
    }
    item = {
        "id": td["id"], "name": td["name"], "name_zh": td["name_zh"],
        "score": 68, "action": "enter", "action_en": "ENTER", "action_zh": "建仓",
    }
    return {"as_of": session, "themes": [td], "act_now": {
        "buy": [item] if clean else [],
        "add_on_pullback": [] if clean else [item],
        "reduce": [], "conflicted": [],
    }}


def _emerging_enter_board(ti=None, clock="2026-09-21T10:00:00+00:00"):
    from datetime import datetime
    return assemble_act_now(
        [], ti or _emerging_enter_fixture(), None,
        observed_at=datetime.fromisoformat(clock),
    )


def test_emerging_enter_remains_theme_buy_now_after_clean_entry_closes():
    board = _emerging_enter_board()
    row, = board["display_lanes"]["buy_now"]
    assert row["entry_route"] == "theme_enter"
    assert row["reco"] == "enter"
    assert row["theme_decision"]["stock_entry_permission"] is False
    assert board["display_lanes"]["wait_pullback"] == []


def test_emerging_enter_preserves_raw_wait_lane_and_source_evidence():
    board = _emerging_enter_board()
    assert board["lanes"]["buy_now"] == []
    assert len(board["lanes"]["wait_pullback"]) == 1
    row, = board["display_lanes"]["buy_now"]
    assert row["observed_lanes"] == ["wait_pullback"]
    assert row["source_reads"][0]["row"] == board["lanes"]["wait_pullback"][0]


def test_emerging_enter_does_not_invent_an_extension_gate():
    for extension in (None, float("nan")):
        ti = _emerging_enter_fixture()
        ti["themes"][0]["ext_abs"] = extension
        row, = _emerging_enter_board(ti)["display_lanes"]["buy_now"]
        assert row["entry_route"] == "theme_enter"


@pytest.mark.parametrize("final,lane", [
    ("hold", "wait_pullback"), ("trim", "reduce_avoid"), ("avoid", "reduce_avoid"),
])
def test_emerging_enter_never_overrides_final_defensive_recommendation(final, lane):
    ti = _emerging_enter_fixture(final=final)
    item = ti["act_now"]["add_on_pullback"][0]
    if final in ("trim", "avoid"):
        item.update(action=final, action_en=final.upper())
        ti["act_now"]["add_on_pullback"] = []
        ti["act_now"]["reduce"] = [item]
    board = _emerging_enter_board(ti)
    assert board["display_lanes"]["buy_now"] == []
    out, = board["display_lanes"][lane]
    assert out["reco"] == final


def test_emerging_enter_never_overrides_source_conflict():
    ti = _emerging_enter_fixture()
    conflict = deepcopy(ti["act_now"]["add_on_pullback"][0])
    conflict.update(action="avoid", action_en="AVOID", action_zh="回避")
    ti["act_now"]["conflicted"] = [conflict]
    board = _emerging_enter_board(ti)
    assert board["display_lanes"]["buy_now"] == []
    assert board["display_lanes"]["wait_pullback"][0]["reco"] == "hold"


@pytest.mark.parametrize("session", [None, "bad", "2026-09-18", "2026-09-22", "2026-09-20"])
def test_emerging_enter_missing_stale_future_or_non_session_fails_closed(session):
    assert _emerging_enter_board(_emerging_enter_fixture(session))["display_lanes"]["buy_now"] == []


def test_existing_clean_entry_enter_keeps_clean_entry_route():
    row, = _emerging_enter_board(_emerging_enter_fixture(clean=True))["display_lanes"]["buy_now"]
    assert row["entry_route"] == "clean_entry"


def test_emerging_enter_render_names_theme_scope_not_stock_permission():
    html = render(_emerging_enter_board())
    assert 'data-entry-route="theme_enter"' in html
    assert 'Theme entry remains open' in html
    assert 'Theme-level entry' in html
    assert 'Individual stock timing is separate; no stock entry is implied.' in html
    assert 'A clean entry is open today.' not in html


@pytest.mark.parametrize("changes", [
    {"regime_demoted": True},
    {"chase_demoted": True},
    {"textures": {}},
    {"label": "dominant"},
])
def test_emerging_enter_requires_complete_final_theme_state(changes):
    ti = _emerging_enter_fixture()
    ti["themes"][0].update(changes)
    assert _emerging_enter_board(ti)["display_lanes"]["buy_now"] == []


@pytest.mark.parametrize("field", ["regime_demoted", "chase_demoted", "label", "reco"])
def test_emerging_enter_missing_final_state_field_fails_closed(field):
    ti = _emerging_enter_fixture()
    del ti["themes"][0][field]
    assert _emerging_enter_board(ti)["display_lanes"]["buy_now"] == []


@pytest.mark.parametrize("observation", [
    None,
    {},
    {"effective_as_of": "2026-09-21"},
    {"aggregate_eligible": True},
    {"effective_as_of": "2026-09-18", "aggregate_eligible": True},
    {"effective_as_of": "2026-09-21", "aggregate_eligible": False},
    {"effective_as_of": "2026-09-21", "aggregate_eligible": "true"},
])
def test_emerging_enter_requires_current_eligible_constituent_observation(observation):
    ti = _emerging_enter_fixture()
    ti["themes"][0]["observation"] = observation
    board = _emerging_enter_board(ti)
    assert board["display_lanes"]["buy_now"] == []
    row, = board["display_lanes"]["wait_pullback"]
    assert row["theme_decision"]["status"] == "UNAVAILABLE"


@pytest.mark.parametrize("clean", [None, "false", 0, 1])
def test_emerging_enter_requires_boolean_clean_entry_state(clean):
    ti = _emerging_enter_fixture()
    ti["themes"][0]["textures"]["clean_entry"]["flag"] = clean
    assert _emerging_enter_board(ti)["display_lanes"]["buy_now"] == []

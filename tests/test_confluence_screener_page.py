"""Tests for scripts.build_confluence_screener.

Headless-safe: no network, no site/ writes (tmp_path for any output),
does not depend on real artifact files.

The DOM-leak acceptance test verifies that gated tickers NEVER appear in the
public rendered HTML. They may appear only in the separate server-protected
/premiumdata/ payload returned to entitled sessions.
"""
from __future__ import annotations

import copy
import json
from html.parser import HTMLParser
from pathlib import Path

import pytest

import sys
_HERE = Path(__file__).resolve().parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from scripts.build_confluence_screener import (
    PAYLOAD_URL,
    PAYLOAD_SCHEMA,
    build_context,
    build_premium_payload,
    render_html,
)

# ── Synthetic artifact ───────────────────────────────────────────────────────

# Three legs that combos can reference
_LEGS = [
    {"leg_id": "leg0", "signal_id": "s0", "tf": "D",
     "display_en": "Golden Cross",     "display_zh": "黄金交叉"},
    {"leg_id": "leg1", "signal_id": "s1", "tf": "W",
     "display_en": "Weekly Uptrend",   "display_zh": "周线上升趋势"},
    {"leg_id": "leg2", "signal_id": "s2", "tf": "D",
     "display_en": "RSI Curl",         "display_zh": "RSI上卷"},
]

_H21_VALID = {
    "n": 30,
    "wr_mc_test": 0.70,
    "wr_mc_train": 0.60,
    "n_test": 15,
    "months_test": 12,
    "n_train": 40,
    "months_train": 36,
}

def _make_raw(*, free_active=("FREEAA",), gated2_active=("GATEDBB",),
              gated3_active=("GATEDCC",)):
    """Build a synthetic tech_confluence-shaped artifact with 4 eligible combos
    (rank_score ordering: rank1=0.5, rank2=0.3, rank3=0.2, rank4=0.1) and one
    inactive combo to verify n_active_total counting.
    """
    return {
        "generated_utc": "2026-07-19T04:00:00Z",
        "universe_n": 226,
        "split_date": "2018-01-01",
        "legs": _LEGS,
        "combos": {
            "long": [
                # Rank 1 (highest rank_score, free)
                {
                    "id": "L0001",
                    "name_en": "Golden cross + weekly uptrend",
                    "name_zh": "黄金交叉+周线上升",
                    "legs": [0, 1],
                    "h21": _H21_VALID,
                    "rank_score": 0.5,
                    "active_now": list(free_active),
                    "n_fires": 100,
                    "first_fire": "2005-03-01",
                    "last_fire": "2026-07-15",
                    "fires_per_year": 3.5,
                    "edge_wr_test": 0.20,
                    "edge_wr_train": 0.10,
                    "consistent": True,
                },
                # Rank 2 (gated)
                {
                    "id": "L0002",
                    "name_en": "RSI curl + golden cross",
                    "name_zh": "RSI上卷+黄金交叉",
                    "legs": [2, 0],
                    "h21": _H21_VALID,
                    "rank_score": 0.3,
                    "active_now": list(gated2_active),
                    "n_fires": 80,
                    "first_fire": "2008-01-01",
                    "last_fire": "2026-07-14",
                    "fires_per_year": 2.8,
                    "edge_wr_test": 0.15,
                    "edge_wr_train": -0.02,
                    "consistent": False,
                },
                # Rank 3 (gated)
                {
                    "id": "L0003",
                    "name_en": "Weekly uptrend + RSI curl",
                    "name_zh": "周线上升+RSI上卷",
                    "legs": [1, 2],
                    "h21": _H21_VALID,
                    "rank_score": 0.2,
                    "active_now": list(gated3_active),
                    "n_fires": 60,
                    "first_fire": "2010-06-01",
                    "last_fire": "2026-07-13",
                    "fires_per_year": 2.0,
                    "edge_wr_test": 0.10,
                    "edge_wr_train": 0.08,
                    "consistent": True,
                },
                # Rank 4 — would be rank 4 if there were more
                {
                    "id": "L0004",
                    "name_en": "Fourth combo",
                    "name_zh": "第四组合",
                    "legs": [0],
                    "h21": _H21_VALID,
                    "rank_score": 0.1,
                    "active_now": ["RANKFOUR"],
                    "n_fires": 40,
                    "first_fire": "2012-01-01",
                    "last_fire": "2026-07-12",
                    "fires_per_year": 1.5,
                    "edge_wr_test": 0.05,
                    "edge_wr_train": -0.01,
                    "consistent": False,
                },
                # Inactive combo (should NOT count toward n_active_total)
                {
                    "id": "L0005",
                    "name_en": "Inactive combo",
                    "name_zh": "非活跃组合",
                    "legs": [0],
                    "h21": _H21_VALID,
                    "rank_score": 0.99,  # high score but inactive
                    "active_now": [],    # empty → should be excluded
                    "n_fires": 200,
                    "first_fire": "2000-01-01",
                    "last_fire": "2026-06-01",
                    "fires_per_year": 10.0,
                    "edge_wr_test": 0.30,
                    "consistent": True,
                },
                # Null h21 combo (should be excluded)
                {
                    "id": "L0006",
                    "name_en": "Null h21 combo",
                    "name_zh": "空h21组合",
                    "legs": [0],
                    "h21": {"wr_mc_test": None, "wr_mc_train": 0.55},
                    "rank_score": 0.8,
                    "active_now": ["NULLTST"],
                    "n_fires": 50,
                    "first_fire": "2015-01-01",
                    "last_fire": "2026-07-10",
                    "fires_per_year": 2.0,
                    "edge_wr_test": 0.12,
                    "consistent": True,
                },
            ],
            "short": [],
        },
    }


_ROOT = Path(__file__).resolve().parent.parent


# ── build_context tests ──────────────────────────────────────────────────────

def test_build_context_rank1_has_active_tickers():
    raw = _make_raw()
    ctx = build_context(raw, {})
    combos = ctx["combos"]
    assert len(combos) == 3  # top 3
    rank1 = combos[0]
    assert rank1["rank"] == 1
    assert rank1["is_free"] is True
    tickers = [t["ticker"] for t in rank1["active_tickers"]]
    assert "FREEAA" in tickers


def test_build_context_gated_combos_have_empty_active_tickers():
    raw = _make_raw()
    ctx = build_context(raw, {})
    combos = ctx["combos"]
    for c in combos[1:]:
        assert c["active_tickers"] == [], (
            f"Rank {c['rank']} combo should have empty active_tickers, got: {c['active_tickers']}"
        )


def test_build_context_n_active_total():
    raw = _make_raw()
    ctx = build_context(raw, {})
    # 4 combos have active_now and valid h21 (L0001, L0002, L0003, L0004)
    # L0005 is inactive (empty active_now), L0006 has null wr_mc_test
    assert ctx["n_active_total"] == 4


def test_build_context_sort_by_rank_score():
    raw = _make_raw()
    ctx = build_context(raw, {})
    scores = [c["combo_id"] for c in ctx["combos"]]
    # L0001 has rank_score 0.5, L0002 has 0.3, L0003 has 0.2
    assert scores == ["L0001", "L0002", "L0003"]


def test_build_context_none_raw():
    ctx = build_context(None, {})
    assert ctx["combos"] == []
    assert ctx["n_active_total"] is None
    assert ctx["source_status"] == "unavailable"
    assert ctx["source_generation"] is None
    assert ctx["asof"] is None


def test_build_context_name_map_used():
    name_map = {"FREEAA": "Free Company Alpha"}
    raw = _make_raw()
    ctx = build_context(raw, name_map)
    tickers = ctx["combos"][0]["active_tickers"]
    assert tickers[0]["name"] == "Free Company Alpha"


def test_build_context_win_rate_pct():
    raw = _make_raw()
    ctx = build_context(raw, {})
    c = ctx["combos"][0]
    # wr_mc_test=0.70 → 70.0
    assert abs(c["wr_test_pct"] - 70.0) < 0.01
    # wr_mc_train=0.60 → 60.0
    assert abs(c["wr_train_pct"] - 60.0) < 0.01


def test_build_context_active_count_for_gated():
    """Gated combos must still expose active_count (the integer) — only tickers are hidden."""
    raw = _make_raw(gated2_active=("GATEDBB",), gated3_active=("GATEDCC", "GATEDDD"))
    ctx = build_context(raw, {})
    assert ctx["combos"][1]["active_count"] == 1
    assert ctx["combos"][2]["active_count"] == 2


# ── protected payload tests ─────────────────────────────────────────────────

def test_premium_payload_contains_only_gated_top_three_tickers():
    raw = _make_raw()
    payload = build_premium_payload(raw, {"GATEDBB": "Gated B"})

    assert payload["schema"] == PAYLOAD_SCHEMA
    assert payload["page"] == "confluence_screener"
    assert payload["gated"] is True
    assert payload["required_tier"] == "essential"
    assert payload["built"] == "2026-07-19T04:00:00Z"
    assert [combo["combo_id"] for combo in payload["combos"]] == ["L0002", "L0003"]

    payload_text = repr(payload)
    assert "GATEDBB" in payload_text
    assert "GATEDCC" in payload_text
    assert "Gated B" in payload_text
    assert "FREEAA" not in payload_text
    assert "RANKFOUR" not in payload_text


def test_premium_payload_none_raw_overwrites_with_empty_fail_soft_payload():
    payload = build_premium_payload(None, {})
    assert payload["schema"] == PAYLOAD_SCHEMA
    assert payload["gated"] is True
    assert payload["combos"] == []
    assert payload["built"] == ""


# ── render_html DOM-leak tests ───────────────────────────────────────────────

def _rendered_html():
    raw = _make_raw()
    ctx = build_context(raw, {})
    return render_html(_ROOT, ctx)


def test_render_html_free_ticker_present():
    html = _rendered_html()
    assert "FREEAA" in html


def test_render_html_gated_tickers_absent():
    """Critical: GATEDBB and GATEDCC must NOT appear anywhere in the rendered HTML."""
    html = _rendered_html()
    assert "GATEDBB" not in html, "GATED ticker leaked into rendered HTML!"
    assert "GATEDCC" not in html, "GATED ticker leaked into rendered HTML!"


def test_render_html_has_protected_payload_hydration_contract():
    html = _rendered_html()
    assert PAYLOAD_URL in html
    assert 'data-confluence-combo="L0002"' in html
    assert 'data-confluence-combo="L0003"' in html
    assert "credentials: 'same-origin'" in html
    assert "freshSession" in html
    assert "mdx-auth" in html
    assert PAYLOAD_SCHEMA in html
    assert 'id="confluence-paid-cta"' in html


def test_render_html_og_meta_present():
    html = _rendered_html()
    assert "og/confluence_screener.png" in html
    assert "summary_large_image" in html


def test_render_html_empty_context_no_exception():
    """empty context (raw=None) must render without exception."""
    ctx = build_context(None, {})
    html = render_html(_ROOT, ctx)
    assert html  # non-empty


def test_render_html_no_validated_word():
    """House law: the word 'validated' must not appear in user-facing rendered HTML."""
    html = _rendered_html()
    assert "validated" not in html.lower()


def test_render_html_is_html():
    html = _rendered_html()
    assert "<!DOCTYPE html>" in html or "<!doctype html>" in html.lower()


def test_shipped_shell_and_protected_payload_are_paired():
    """The committed artifact pair must stay deployable between nightly runs."""
    html = (_ROOT / "site" / "confluence_screener.html").read_text(encoding="utf-8")
    payload = json.loads(
        (_ROOT / "site" / "premiumdata" / "confluence_screener.json")
        .read_text(encoding="utf-8")
    )

    assert payload["schema"] == PAYLOAD_SCHEMA
    assert payload["page"] == "confluence_screener"
    assert payload["gated"] is True
    assert payload["required_tier"] == "essential"
    assert PAYLOAD_URL in html
    assert payload["source_status"] == "available"
    assert payload["source_generation"]["sha256"] in html
    assert payload["source_generation"]["generated_utc"] == payload["built"]
    for combo in payload["combos"]:
        assert combo["active_count"] == len(combo["active_tickers"])
        assert f'data-confluence-combo="{combo["combo_id"]}"' in html


# ── LENS Tier-2 inventory + line-590 honesty (H3 frozen spec) ───────────────

# Exact frozen strings. Interpolated receipts are asserted separately against
# the synthetic context so a fixture change cannot silently green a paraphrase.
_TIPS = {
    "T1": (
        "Eligible active signal combinations in this source snapshot, not stocks. The list below shows up to three combinations in source rank order.",
        "此数据快照中符合条件的活跃信号组合数，不是股票数。下方最多展示按源数据排名的前三组。",
    ),
    "T2": (
        "Source ordering uses recent monthly win averages and a small-sample penalty relative to random entry. This ranking heuristic does not establish statistical significance.",
        "源数据按近年月均胜率、样本量惩罚和随机入场基准排序。这是排序方法，不代表统计显著性。",
    ),
    "T3": (
        "A sighting starts when a stock's full signal combination changes from false to true. Consecutive days that stay true do not add sightings. The yearly figure averages sightings over the first-to-last span.",
        "某只股票的完整信号组合由不成立变为成立，计为一次触发。连续成立的日期不重复计数。年均次数按首次至末次的时间跨度计算。",
    ),
    "T6a": (
        "This leg is evaluated on daily bars. The indicator itself may use a longer lookback.",
        "此条件在日线数据上计算；指标本身可能使用更长的回看窗口。",
    ),
    "T6b": (
        "This leg is evaluated on weekly bars. Its indicator lookback and trigger frequency are separate properties.",
        "此条件在周线数据上计算；指标回看窗口和触发频率是不同的属性。",
    ),
    "T10": (
        "Matching large-cap stocks in this source snapshot. Their count is public; names require an entitled response for this same snapshot.",
        "此源数据快照中匹配的大盘股数量。数量公开；名称须来自有权限访问的同一快照。",
    ),
}


def test_render_html_retained_lens_tips_en_zh():
    """Retained tips stay bilingual; rates and baseline method use native disclosure."""
    html = _rendered_html()
    for key, (en, zh) in _TIPS.items():
        assert f'data-tip-en="{en}"' in html, f"{key} EN missing"
        assert f'data-tip-zh="{zh}"' in html, f"{key} ZH missing"
    assert html.count('<details class="lc-method">') == 3
    assert "How these readings are calculated" in html
    assert "这些读数如何计算" in html
    assert "not the fraction of winning months or the pooled win rate" in html
    assert "这不是盈利月份占比，也不是所有触发次数合并后的胜率" in html
    assert "The baseline enters the same stocks on random dates over the same period." in html
    assert "基准是在同一时期对相同股票随机选择日期入场。" in html
    assert "in 10 recently" not in html and 'class="w10' not in html

def test_render_html_receipts_and_visible_samples_carry_context():
    """Population/rank receipts and visible sample counts use source values."""
    raw = _make_raw()
    raw["split_date"] = "2019-06-01"
    ctx = build_context(raw, {})
    html = render_html(_ROOT, ctx)
    c0, split = ctx["combos"][0], ctx["split_date"]
    assert f"≥15 fires and ≥12 distinct months since {split}" in html
    assert f"{split} 起触发 ≥15 次且覆盖 ≥12 个不同月份" in html
    assert "Wilson-based ranking heuristic on the monthly win average" in html
    for half in ("test", "train"):
        assert f'{c0["months_" + half]} months · {c0["n_" + half]} fires' in html
        assert f'{c0["months_" + half]} 个月 · {c0["n_" + half]} 次触发' in html
    assert f"Recent is the test period, with fire dates from {split}" in html
    assert f"近年为测试期，触发日期自 {split} 起" in html
    assert "Older is the training period, before that date" in html
    assert "Random-entry monthly win average · 21 trading days" in html
    assert '<span class="l-en">unavailable</span>' in html
    assert '<span class="l-zh">暂无数据</span>' in html
    assert "No older-era readings for this line-up" not in html

def test_render_html_honesty_promise_and_dynamic_split():
    html = _rendered_html()
    assert "The exact counts sit next to every rate." not in html
    assert "Months and fires are shown beside each rate; open “How these readings are calculated” for definitions." in html
    assert "月份与触发次数列在各读数旁；打开「这些读数如何计算」可查看定义。" in html
    assert "coin-flip" not in html
    assert "Versus random entry · percentage points" in html
    assert "Above baseline only in the recent period" in html
    assert "仅近年高于基准" in html
    src = (_ROOT / "templates" / "confluence_screener.html.j2").read_text(encoding="utf-8")
    assert "Recent (2018+)" not in src and "近年（2018起）" not in src
    assert "split_date[:4]" in src

def test_render_html_split_year_is_derived_not_hardcoded():
    """A non-2018 split_date must appear in the unit label; 2018 must not."""
    raw = _make_raw()
    raw["split_date"] = "2020-06-15"
    html = render_html(_ROOT, build_context(raw, {}))
    assert "Recent (2020+)" in html
    assert "近年（2020起）" in html
    assert "Recent (2018+)" not in html
    assert "近年（2018起）" not in html


def test_render_html_rate_disclosure_and_retained_lens_hosts():
    """Rate definitions have a native summary; leg names gain no invented tips."""
    html = _rendered_html()
    assert 'class="hero-state" tabindex="0"' in html
    assert "lc-rank cs-tipped" in html
    assert 'class="lc-wr-big mono"' in html and 'class="lc-wr-old"' in html
    assert "lc-wr-big mono cs-tipped" not in html
    assert "lc-wr-old cs-tipped" not in html
    assert '<details class="lc-method">' in html and "<summary>" in html
    assert 'class="leg-tf w" tabindex="0"' in html
    assert 'class="leg-tf d" tabindex="0"' in html
    for chunk in html.split('class="leg-txt"')[1:]:
        assert "data-tip-en" not in chunk.split(">", 1)[0]
    assert not any("title=" in tag and "data-tip-en=" in tag
                   for tag in html.split("<") if "data-tip-en=" in tag)

def test_gates_receipt_literals_match_minerconfig_defaults():
    """T1 Gates numbers are literals; they must track MinerConfig defaults."""
    from engine.tech_confluence import MinerConfig

    cfg = MinerConfig()
    src = (_ROOT / "templates" / "confluence_screener.html.j2").read_text(
        encoding="utf-8"
    )
    assert cfg.min_fires == 40
    assert cfg.min_months == 24
    assert cfg.min_tickers == 10
    assert cfg.min_test_fires == 15
    assert cfg.min_test_months == 12
    assert f"≥{cfg.min_fires} fires pooled" in src
    assert f"≥{cfg.min_months} distinct months pooled" in src
    assert f"≥{cfg.min_tickers} tickers" in src
    assert (
        f"≥{cfg.min_test_fires} fires and ≥{cfg.min_test_months} distinct months"
        in src
    )
    assert f"合计触发 ≥{cfg.min_fires} 次" in src
    assert f"合计 ≥{cfg.min_months} 个不同月份" in src
    assert f"≥{cfg.min_tickers} 只股票" in src
    assert (
        f"触发 ≥{cfg.min_test_fires} 次且覆盖 ≥{cfg.min_test_months} 个不同月份"
        in src
    )



def _comparison_cells(card):
    """Read the independently identified recent/older cells from rendered HTML."""
    class Cells(HTMLParser):
        def __init__(self):
            super().__init__()
            self.cells, self.current = {}, None

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == "dd" and attrs.get("data-period") in ("recent", "older"):
                self.current = [attrs["data-period"], attrs["data-state"], []]

        def handle_data(self, text):
            if self.current is not None:
                self.current[2].append(text)

        def handle_endtag(self, tag):
            if tag == "dd" and self.current is not None:
                period, state, parts = self.current
                self.cells[period] = {"state": state, "text": "".join(parts).strip()}
                self.current = None

    parser = Cells()
    parser.feed(card)
    return parser.cells

def test_render_html_measured_comparison_sign_and_period_support():
    html_pos = _rendered_html()
    assert "Above baseline in both periods" in html_pos
    assert "两期均高于基准" in html_pos
    assert "Above baseline only in the recent period" in html_pos
    assert "仅近年高于基准" in html_pos
    assert "Not above baseline recently" not in html_pos
    first = html_pos.split('<div class="lc free">', 1)[1].split('<div class="lc gated">', 1)[0]
    assert _comparison_cells(first) == {
        "recent": {"state": "positive", "text": "+20.0"},
        "older": {"state": "positive", "text": "+10.0"},
    }
    for value, expected in ((-0.02, "-2.0"), (0, "0.0")):
        raw = copy.deepcopy(_make_raw())
        for combo in raw["combos"]["long"]:
            if not combo.get("consistent"):
                combo["edge_wr_test"] = value
        html = render_html(_ROOT, build_context(raw, {}))
        assert "Not above baseline recently" in html
        assert "近年未高于基准" in html
        assert "Above baseline only in the recent period" not in html
        gated = html.split('<div class="lc gated">', 1)[1].split('<div class="lc gated">', 1)[0]
        assert _comparison_cells(gated)["recent"]["text"] == expected
        assert "+-" not in html

def test_eligible_population_is_not_the_display_limit():
    ctx = build_context(_make_raw(), {})
    html = render_html(_ROOT, ctx)
    assert ctx["n_active_total"] == 4
    assert len(ctx["combos"]) == 3
    assert '<span class="n">4</span> active line-ups' in html
    assert "Showing 3 of 4 eligible line-ups." in html
    assert "Two more are lining up behind it" not in html
    assert "12 months · 15 fires" in html
    assert "36 months · 40 fires" in html


@pytest.mark.parametrize("count", [1, 2, 3])
def test_display_scope_and_cta_follow_available_rows(count):
    raw = copy.deepcopy(_make_raw())
    raw["combos"]["long"] = raw["combos"]["long"][:count]
    ctx = build_context(raw, {})
    html = render_html(_ROOT, ctx)
    assert f"Showing {count} of {count} eligible line-ups." in html
    assert ('id="confluence-paid-cta"' in html) == (count > 1)
    assert len(build_premium_payload(raw, {})["combos"]) == count - 1


def test_verified_zero_and_unavailable_are_different_states():
    raw = copy.deepcopy(_make_raw())
    raw["combos"]["long"] = []
    ctx = build_context(raw, {})
    assert ctx["source_status"] == "available"
    assert ctx["n_active_total"] == 0
    html = render_html(_ROOT, ctx)
    assert 'data-source-state="available-empty"' in html
    assert "No eligible line-ups" in html
    missing = render_html(_ROOT, build_context(None, {}))
    assert 'data-source-state="unavailable"' in missing
    assert "number of matching line-ups is unknown" in missing
    assert "No eligible line-ups" not in missing


@pytest.mark.parametrize("mutation", [
    lambda raw: raw.update(generated_utc="2026-07-19"),
    lambda raw: raw.update(generated_utc="not-a-clock"),
    lambda raw: raw.update(universe_n=True),
    lambda raw: raw.update(combos={"long": {}}),
    lambda raw: raw["combos"]["long"].append(None),
    lambda raw: raw["combos"]["long"][0].update(active_now="FREEAA"),
    lambda raw: raw["combos"]["long"][0].update(active_now=["FREEAA", "FREEAA"]),
    lambda raw: raw["combos"]["long"][0].update(active_now=["../private"]),
    lambda raw: raw["combos"]["long"][0].update(h21=[]),
    lambda raw: raw["combos"]["long"][0].update(rank_score=float("nan")),
    lambda raw: raw["combos"]["long"][0]["h21"].update(wr_mc_test=1.1),
    lambda raw: raw["combos"]["long"][0]["h21"].update(months_test=None),
    lambda raw: raw["combos"]["long"][0].update(legs=[999]),
    lambda raw: raw["combos"]["long"][1].update(id="L0001"),
])
def test_malformed_source_cannot_claim_verified_zero(mutation):
    raw = copy.deepcopy(_make_raw())
    mutation(raw)
    ctx = build_context(raw, {})
    paid = build_premium_payload(raw, {})
    assert ctx["source_status"] == paid["source_status"] == "unavailable"
    assert ctx["n_active_total"] is None
    assert ctx["combos"] == paid["combos"] == []
    assert ctx["source_generation"] is paid["source_generation"] is None


def test_both_projections_bind_exact_artifact_content_not_only_its_clock():
    a = _make_raw()
    b = copy.deepcopy(a)
    b["combos"]["long"][1]["active_now"] = ["DIFFERENT"]
    public_a = build_context(a, {})
    paid_a = build_premium_payload(a, {})
    paid_b = build_premium_payload(b, {})
    assert public_a["source_generation"] == paid_a["source_generation"]
    assert paid_a["built"] == paid_b["built"]
    assert paid_a["source_generation"]["sha256"] != paid_b["source_generation"]["sha256"]
    reordered = dict(reversed(list(a.items())))
    assert build_context(reordered, {})["source_generation"] == public_a["source_generation"]
    public_text = render_html(_ROOT, public_a)
    assert "GATEDBB" not in public_text
    assert "GATEDCC" not in public_text
    assert "DIFFERENT" not in public_text


def test_stable_ties_and_all_four_daily_weekly_legs_survive():
    raw = copy.deepcopy(_make_raw())
    raw["legs"].append({"display_en": "Fourth daily condition", "display_zh": "第四个日线条件", "tf": "D"})
    raw["combos"]["long"][0]["legs"] = [0, 1, 2, 3]
    for combo in raw["combos"]["long"][:4]:
        combo["rank_score"] = 0.25
    ctx = build_context(raw, {})
    assert [c["combo_id"] for c in ctx["combos"]] == ["L0001", "L0002", "L0003"]
    assert [leg["tf"] for leg in ctx["combos"][0]["legs"]] == ["D", "W", "D", "D"]
    assert ctx["combos"][0]["is_free"]
    assert not ctx["combos"][1]["active_tickers"]
    assert "Fourth daily condition" in render_html(_ROOT, ctx)


def test_month_mean_is_not_pooled_or_winning_month_incidence():
    import numpy as np
    from engine.tech_confluence import _month_collapsed_wr
    wins = np.array([True, True] + [False] * 8)
    months = np.array([1] + [2] * 9)
    rate, count = _month_collapsed_wr(wins, months)
    assert count == 2
    assert rate == pytest.approx((1 + 1 / 9) / 2)
    assert rate != pytest.approx(wins.mean())
    assert rate != 1
    html = _rendered_html()
    assert "not the fraction of winning months or the pooled win rate" in html
    assert "Older is the training period, before that date" in html
    assert "out-of-sample check" not in html
    assert "Consecutive days that stay true do not add sightings" in html


def test_source_build_clock_is_not_presented_as_market_observation_time():
    html = _rendered_html()
    assert "Source built 2026-07-19T04:00:00Z" in html
    assert "market observation time not supplied" in html
    assert "Data as of 2026-07-19" not in html


def test_baseline_readings_come_from_source_not_derived_edge():
    raw = copy.deepcopy(_make_raw())
    raw["base"] = {"long": {"h21": {"wr_mc_test": 0.5669, "wr_mc_train": 0.5583}}}
    ctx = build_context(raw, {})
    assert ctx["baseline_test_pct"] == pytest.approx(56.69)
    html = render_html(_ROOT, ctx)
    assert "5.7/10" in html and "5.6/10" in html
    assert "随机入场月均胜率 · 21 个交易日" in html


@pytest.mark.parametrize("field,value", [
    ("edge_wr_test", None), ("edge_wr_test", "0.2"), ("edge_wr_test", True),
    ("edge_wr_test", 1.5), ("consistent", None), ("consistent", "false"),
    ("edge_wr_train", None), ("edge_wr_train", "0.1"), ("edge_wr_train", True),
    ("edge_wr_train", 1.5),
    ("n_fires", None), ("n_fires", 0), ("first_fire", None),
    ("first_fire", "2005-02-30"), ("last_fire", None),
    ("fires_per_year", None), ("fires_per_year", -1),
])
def test_optional_evidence_missingness_does_not_erase_valid_rates(field, value):
    raw = copy.deepcopy(_make_raw())
    raw["combos"]["long"][0][field] = value
    ctx = build_context(raw, {})
    first = ctx["combos"][0]
    assert ctx["source_status"] == "available"
    assert ctx["n_active_total"] == 4 and len(ctx["combos"]) == 3
    assert first["wr_test_pct"] == 70 and first["wr_train_pct"] == 60
    html = render_html(_HERE, ctx)
    card = html.split('<div class="lc free">', 1)[1].split('<div class="lc gated">', 1)[0]
    if field == "edge_wr_test":
        assert first["edge_test_pp"] is None
        assert "Recent-period comparison unavailable" in card
        assert "近年时期比较暂无数据" in card
        assert _comparison_cells(card)["older"] == {"state": "positive", "text": "+10.0"}
        assert "Not above baseline recently" not in card
        assert "Above baseline in both periods" not in card
    elif field == "consistent":
        assert first["consistent"] is None
        # Known positive comparisons in both periods remain readable even when
        # the optional producer flag is absent or malformed.
        assert "Above baseline in both periods" in card
        assert "Above baseline only in the recent period" not in card
    elif field == "edge_wr_train":
        assert first["edge_train_pp"] is None
        assert "Older-period comparison unavailable" in card
        assert "Above baseline only in the recent period" not in card
        assert "Above baseline in both periods" not in card
    else:
        assert not first["history_complete"]
        assert "Historical frequency details unavailable" in card
        assert "Seen 0 times" not in card


def test_absent_optional_evidence_is_not_negative_evidence():
    raw = copy.deepcopy(_make_raw())
    for field in ("edge_wr_test", "edge_wr_train", "consistent", "n_fires", "first_fire", "last_fire", "fires_per_year"):
        raw["combos"]["long"][0].pop(field)
    ctx = build_context(raw, {})
    assert ctx["source_status"] == "available"
    first = ctx["combos"][0]
    assert first["edge_test_pp"] is None and first["consistent"] is None
    assert first["n_fires"] is None and not first["history_complete"]
    card = render_html(_HERE, ctx).split('<div class="lc free">', 1)[1].split('<div class="lc gated">', 1)[0]
    assert "Random-entry comparison unavailable" in card
    assert "Historical frequency details unavailable" in card
    assert "Not above baseline recently" not in card


@pytest.mark.parametrize("edge,expected", [
    (0, "0.0"), (-0.001, "-0.1"), (0.001, "+0.1"),
    (-0.00004, "-0.004"), (0.00004, "+0.004"),
    (-1e-12, "-1e-10"), (1e-12, "+1e-10"),
])
def test_measured_zero_and_small_signed_comparison_remain_distinct(edge, expected):
    raw = copy.deepcopy(_make_raw())
    raw["combos"]["long"][0].update(edge_wr_test=edge, consistent=False)
    first = build_context(raw, {})["combos"][0]
    assert first["edge_test_pp"] == edge * 100
    card = render_html(_HERE, build_context(raw, {})).split('<div class="lc free">', 1)[1].split('<div class="lc gated">', 1)[0]
    comparison = _comparison_cells(card)["recent"]
    assert comparison["text"] == expected
    assert comparison["state"] == ("zero" if edge == 0 else "negative" if edge < 0 else "positive")
    assert ("Not above baseline recently" in card) == (edge <= 0)
    assert "Random-entry comparison unavailable" not in card


def test_missing_rank_is_not_silently_ranked_as_zero():
    raw = copy.deepcopy(_make_raw())
    raw["combos"]["long"][0].pop("rank_score")
    assert build_context(raw, {})["source_status"] == "unavailable"


@pytest.mark.parametrize("flag", [True, False])
def test_consistency_flag_cannot_supply_missing_older_comparison(flag):
    raw = copy.deepcopy(_make_raw())
    raw["combos"]["long"][0].update(consistent=flag, edge_wr_train=None)
    ctx = build_context(raw, {})
    assert ctx["combos"][0]["edge_test_pp"] > 0
    card = render_html(_HERE, ctx).split('<div class="lc free">', 1)[1].split('<div class="lc gated">', 1)[0]
    assert "Older-period comparison unavailable" in card
    assert "Above baseline only in the recent period" not in card
    assert "Above baseline in both periods" not in card


@pytest.mark.parametrize("input_kind", [
    "missing", "malformed_json", "non_object", "read_error",
    "missing_collection", "missing_clock", "invalid_clock",
    "mixed_malformed_row", "qualified_zero",
])
def test_actual_render_overwrites_stale_protected_rows(tmp_path, monkeypatch, input_kind):
    """Exercise the real renderer and file writers, not only payload construction.

    Only output-root configuration and its shim cache are isolated. This proves a successful render;
    a failure before the protected write is a separate publication contract.
    """
    import shutil
    from lib import config, pages
    from scripts import build_confluence_screener as builder

    templates = tmp_path / "templates"
    templates.mkdir()
    for name in (
        "confluence_screener.html.j2", "_seo_head.html.j2",
        "_site_nav.html.j2", "_navlinks.html.j2", "data_base.js",
        "shared_shell_bridge.js", "shared_shell.css",
    ):
        shutil.copyfile(_ROOT / "templates" / name, templates / name)
    site = tmp_path / "site"
    source = site / "factordata" / "tech_confluence.json"
    source.parent.mkdir(parents=True)
    protected = site / "premiumdata" / "confluence_screener.json"
    protected.parent.mkdir()
    protected.write_text(json.dumps({
        "schema": PAYLOAD_SCHEMA, "page": "confluence_screener",
        "combos": [{"combo_id": "OLD", "active_tickers": [
            {"ticker": "STALE_PRIVATE", "name": "Old protected fixture"}
        ]}],
    }), encoding="utf-8")
    public = site / "confluence_screener.html"
    public.write_text("OLD_PUBLIC_SHELL", encoding="utf-8")

    raw = copy.deepcopy(_make_raw())
    if input_kind == "read_error":
        source.mkdir()  # An existing non-file produces a real read failure.
    elif input_kind == "malformed_json":
        source.write_text("{bad-json", encoding="utf-8")
    elif input_kind == "non_object":
        source.write_text("[]", encoding="utf-8")
    elif input_kind != "missing":
        if input_kind == "missing_collection":
            del raw["combos"]["long"]
        elif input_kind == "missing_clock":
            del raw["generated_utc"]
        elif input_kind == "invalid_clock":
            raw["generated_utc"] = "not-a-clock"
        elif input_kind == "mixed_malformed_row":
            raw["combos"]["long"].append(None)
        elif input_kind == "qualified_zero":
            raw["combos"]["long"] = []
        source.write_text(json.dumps(raw), encoding="utf-8")

    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setattr(config, "load", lambda: {"storage": {"site_dir": "site"}})
    monkeypatch.setattr(pages, "_shim_checked", False)
    builder.render(tmp_path)

    html = public.read_text(encoding="utf-8")
    payload_text = protected.read_text(encoding="utf-8")
    payload = json.loads(payload_text)
    assert "OLD_PUBLIC_SHELL" not in html
    assert "STALE_PRIVATE" not in html + payload_text
    assert "Old protected fixture" not in html + payload_text
    assert payload["schema"] == PAYLOAD_SCHEMA
    assert payload["page"] == "confluence_screener"
    assert payload["gated"] is True and payload["required_tier"] == "essential"
    assert payload["combos"] == []

    if input_kind == "qualified_zero":
        assert payload["source_status"] == "available"
        assert payload["source_generation"] == build_context(raw, {})["source_generation"]
        assert payload["built"] == raw["generated_utc"]
        assert 'data-source-state="available-empty"' in html
        assert 'data-source-state="unavailable"' not in html
        assert "No eligible line-ups" in html
    else:
        assert payload["source_status"] == "unavailable"
        assert payload["source_generation"] is None and payload["built"] == ""
        assert 'data-source-state="unavailable"' in html
        assert 'data-source-state="available-empty"' not in html
        assert "number of matching line-ups is unknown" in html


@pytest.mark.parametrize("recent,older,expected_recent,expected_older,summary", [
    (0.2, -0.02, "+20.0", "-2.0", "Above baseline only in the recent period"),
    (-0.02, 0.2, "-2.0", "+20.0", "Not above baseline recently"),
    (0, 0, "0.0", "0.0", "Not above baseline recently"),
    (None, 0.1, "Unavailable暂无数据", "+10.0", "Recent-period comparison unavailable"),
    (0.2, None, "+20.0", "Unavailable暂无数据", "Older-period comparison unavailable"),
    (None, None, "Unavailable暂无数据", "Unavailable暂无数据", "Random-entry comparison unavailable"),
])
def test_period_comparisons_remain_independent_of_rates_and_each_other(
    recent, older, expected_recent, expected_older, summary
):
    raw = copy.deepcopy(_make_raw())
    raw["combos"]["long"][0]["id"] = "L 0001"  # Accepted source identity may contain spaces.
    # A higher older headline rate is not evidence of a positive older delta.
    raw["combos"]["long"][0]["h21"] = dict(_H21_VALID, wr_mc_train=0.9)
    raw["combos"]["long"][0].update(edge_wr_test=recent, edge_wr_train=older)
    # Supplied baseline levels must not manufacture an absent supplied delta.
    raw["base"] = {"long": {"h21": {"wr_mc_test": 0.5, "wr_mc_train": 0.4}}}
    ctx = build_context(raw, {})
    assert ctx["combos"][0]["combo_id"] == "L 0001"
    assert ctx["combos"][0]["wr_test_pct"] == 70
    assert ctx["combos"][0]["wr_train_pct"] == 90
    assert ctx["n_active_total"] == 4 and len(ctx["combos"]) == 3
    card = render_html(_HERE, ctx).split('<div class="lc free">', 1)[1].split('<div class="lc gated">', 1)[0]
    cells = _comparison_cells(card)
    assert set(cells) == {"recent", "older"}
    assert cells["recent"]["text"] == expected_recent
    assert cells["older"]["text"] == expected_older
    assert summary in card
    assert "Versus random entry · percentage points" in card
    assert "较随机入场 · 个百分点" in card
    assert 'aria-labelledby="baseline-unit-1"' in card
    assert 'id="baseline-unit-1"' in card
    assert "Recent comparison" in card and "Older comparison" in card
    assert "12 months · 15 fires" in card and "36 months · 40 fires" in card
    assert "in 10 recently" not in card

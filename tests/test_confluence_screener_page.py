"""Tests for scripts.build_confluence_screener.

Headless-safe: no network, no site/ writes (tmp_path for any output),
does not depend on real artifact files.

The DOM-leak acceptance test verifies that gated tickers NEVER appear in the
public rendered HTML. They may appear only in the separate server-protected
/premiumdata/ payload returned to entitled sessions.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import sys
_HERE = Path(__file__).resolve().parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from scripts.build_confluence_screener import (
    PAYLOAD_URL,
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
    assert ctx["n_active_total"] == 0
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

    assert payload["schema"] == "tier_payload.v1"
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
    assert payload["schema"] == "tier_payload.v1"
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
    assert "tier_payload.v1" in html
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

    assert payload["schema"] == "tier_payload.v1"
    assert payload["page"] == "confluence_screener"
    assert payload["gated"] is True
    assert payload["required_tier"] == "essential"
    assert PAYLOAD_URL in html
    for combo in payload["combos"]:
        assert combo["active_count"] == len(combo["active_tickers"])
        assert f'data-confluence-combo="{combo["combo_id"]}"' in html


# ── LENS Tier-2 inventory + line-590 honesty (H3 frozen spec) ───────────────

# Exact frozen strings. Interpolated receipts are asserted separately against
# the synthetic context so a fixture change cannot silently green a paraphrase.
_TIPS = {
    "T1": (
        "How many proven signal line-ups are firing across the large-cap list today. A line-up only appears here if it cleared the history gates below.",
        "今日在大盘股名单中触发的、且已通过历史门槛的信号组合数量。未达门槛的组合不会出现在这里。",
    ),
    "T2": (
        "Ranked by the cautious end of its recent win rate — a line-up with fewer months behind it is pushed down, not up.",
        "按近年胜率的保守下限排序——历史月份越少的组合排名越靠后，而非靠前。",
    ),
    "T3": (
        "Every time all of this line-up's signals were true for a stock on the same day counts as one sighting. The yearly figure is those sightings spread over the span between the first and the last.",
        "该组合的全部信号在同一天对同一只股票同时成立，即计为一次出现。「每年约 N 次」是把这些次数摊到首末两次之间的年数上。",
    ),
    "T4": (
        "Out of the recent months where this line-up fired, the share that ended higher 21 trading days later — about a calendar month. Each month counts once, so a busy month can't inflate it.",
        "在近年触发过的月份中，21 个交易日（约一个自然月）后收高的月份占比。每个月只计一次，密集触发不会虚增。",
    ),
    "T5": (
        "The same reading on the years before the split — the out-of-sample check. A line-up that only works after the split is the one to distrust.",
        "同一读数应用于分割日之前的年份——即样本外检验。只在分割日之后才有效的组合最值得怀疑。",
    ),
    "T6a": (
        "Read on daily bars — this signal has to be true on the day.",
        "按日线读取——该信号须在当日成立。",
    ),
    "T6b": (
        "Read on weekly bars — a slower leg that only changes a few times a year.",
        "按周线读取——变化较慢的一条，一年只切换几次。",
    ),
    "T7": (
        "Ten blocks, one per win in ten. Filled blocks are the recent win rate rounded to the nearest whole win.",
        "十个方块代表十次中的胜负。填充的方块数是近年胜率四舍五入到整数的结果。",
    ),
    "T8": (
        "Against a baseline of entering the same stocks on random dates over the same period. Points are percentage points of win rate, not return.",
        "对照基准为：同期在相同股票上随机选日入场。此处的「个百分点」指胜率的百分点，而非收益率。",
    ),
    "T9a": (
        "It beat random entry in the older years as well as the recent ones. Both halves had to clear the bar, not just the recent one.",
        "在更早年份与近年，它都跑赢了随机入场。两段样本须同时达标，而非只看近年。",
    ),
    "T9b": (
        "It beat random entry recently, but not in the older years — so the recent reading is the only one supporting it.",
        "它近年跑赢了随机入场，但在更早年份没有——因此只有近年读数在支持它。",
    ),
    "T10": (
        "How many of today's large-cap names this line-up matches right now. The names sit behind the trial; the count does not.",
        "该组合当前匹配的大盘股数量。具体名称需试用后查看，数量本身不设限。",
    ),
}


def test_render_html_lens_tips_exact_en_zh():
    """Every frozen T1–T10 pair is present verbatim on the rendered page."""
    html = _rendered_html()
    for key, (en, zh) in _TIPS.items():
        assert f'data-tip-en="{en}"' in html, f"{key} EN missing or paraphrased"
        assert f'data-tip-zh="{zh}"' in html, f"{key} ZH missing or paraphrased"


def test_render_html_lens_receipts_carry_counts_from_context():
    """T1/T2/T4/T5/T8 receipt pairs interpolate live context, not placeholders."""
    raw = _make_raw()
    ctx = build_context(raw, {})
    html = render_html(_ROOT, ctx)
    c0 = ctx["combos"][0]
    split = ctx["split_date"]
    asof = ctx["asof"]

    assert (
        f'data-tip-rc-en="Gates: ≥40 fires pooled · ≥24 distinct months pooled · ≥10 tickers · ≥15 fires and ≥12 distinct months since {split} · horizon 21 trading days"'
        in html
    )
    assert (
        f'data-tip-rc-zh="门槛：合计触发 ≥40 次 · 合计 ≥24 个不同月份 · ≥10 只股票 · {split} 起触发 ≥15 次且覆盖 ≥12 个不同月份 · 持有期 21 个交易日"'
        in html
    )
    assert (
        'data-tip-rc-en="Wilson lower bound on the month-collapsed win rate, minus the random-entry baseline, 21-day horizon, recent half"'
        in html
    )
    assert (
        'data-tip-rc-zh="按月合并胜率的 Wilson 置信下限，减去随机入场基准 · 21 日持有期 · 近期样本"'
        in html
    )
    assert (
        f'data-tip-rc-en="{c0["months_test"]} months · {c0["n_test"]} fires · {split} → {asof} · win = up after 21 trading days"'
        in html
    )
    assert (
        f'data-tip-rc-zh="{c0["months_test"]} 个月 · 触发 {c0["n_test"]} 次 · {split} 至 {asof} · 胜 = 21 个交易日后上涨"'
        in html
    )
    assert (
        f'data-tip-rc-en="{c0["months_train"]} months · {c0["n_train"]} fires · first fire {c0["first_fire"]} → {split}"'
        in html
    )
    assert (
        f'data-tip-rc-zh="{c0["months_train"]} 个月 · 触发 {c0["n_train"]} 次 · 首次触发 {c0["first_fire"]} 至 {split}"'
        in html
    )
    assert (
        f'data-tip-rc-en="Random-entry baseline, month-collapsed win rate, 21-day horizon, {split} → {asof}"'
        in html
    )
    assert (
        f'data-tip-rc-zh="随机入场基准 · 按月合并胜率 · 21 日持有期 · {split} 至 {asof}"'
        in html
    )
    # BMV-4: rendered combos have a real train sample, so the empty-era
    # receipt is not the branch this artifact supports.
    assert "No older-era readings for this line-up" not in html
    assert "该组合没有更早年份的读数" not in html


def test_render_html_honesty_promise_and_hardcoded_2018_gone():
    """Line-590 four-part ruling: healed promise, no coin-flip, no hardcoded 2018."""
    html = _rendered_html()
    assert "The exact counts sit next to every rate." not in html
    assert "具体次数就标在每个胜率旁边。" not in html
    assert "Hover or tap any win rate to see how many months it rests on." in html
    assert "将鼠标移到任一胜率上（手机端点按），即可看到它基于多少个月的读数。" in html
    assert "coin-flip" not in html
    assert "points better than entering at random" in html
    assert "较随机入场高" in html
    assert "recent read only — thinner older record" not in html
    assert "仅近年数据 — 更早记录较薄" not in html
    assert "older years didn't back it up" in html
    assert "更早年份未能印证" in html

    src = (_ROOT / "templates" / "confluence_screener.html.j2").read_text(encoding="utf-8")
    assert "wins recently (2018+)" not in src
    assert "近年胜率 (2018起)" not in src
    assert "split_date[:4]" in src


def test_render_html_split_year_is_derived_not_hardcoded():
    """A non-2018 split_date must appear in the unit label; 2018 must not."""
    raw = _make_raw()
    raw["split_date"] = "2020-06-15"
    html = render_html(_ROOT, build_context(raw, {}))
    assert "wins recently (2020+)" in html
    assert "近年胜率 (2020起)" in html
    assert "wins recently (2018+)" not in html
    assert "近年胜率 (2018起)" not in html


def test_render_html_lens_hosts_and_no_leg_text_tip():
    """Tips sit on the specified hosts; leg display names are not invented into tips."""
    html = _rendered_html()
    assert 'class="hero-state" tabindex="0"' in html
    assert "lc-rank cs-tipped" in html
    assert "lc-wr-big mono cs-tipped" in html
    assert "lc-wr-old cs-tipped" in html
    assert 'class="lc-since" tabindex="0"' in html
    assert "cs-tipped" not in html.split('class="hero-state"', 1)[1].split(">", 1)[0]
    assert "cs-tipped" not in html.split('class="lc-since"', 1)[1].split(">", 1)[0]
    assert 'class="leg-tf w" tabindex="0"' in html
    assert 'class="leg-tf d" tabindex="0"' in html
    # BMV-3: no tip on the leg text span itself.
    assert "leg-txt" in html
    for chunk in html.split('class="leg-txt"')[1:]:
        assert not chunk.lstrip().startswith("data-tip-")
        opening = chunk.split(">", 1)[0]
        assert "data-tip-en" not in opening
    # Tipped hosts must not carry title= (CI-guarded i18n rule).
    assert "data-tip-en=" in html
    assert not any(
        "title=" in tag and "data-tip-en=" in tag
        for tag in html.split("<")
        if "data-tip-en=" in tag
    )


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


def test_render_html_t9b_sign_conditional_and_edge_chip_sign():
    """M1+m1: two-part T9b only when edge_test_pp > 0; edge chip never '+-'."""
    src = (_ROOT / "templates" / "confluence_screener.html.j2").read_text(
        encoding="utf-8"
    )
    assert "+{{ _edge }}" not in src
    assert "+{{" not in src.split("points better than entering at random", 1)[0][-40:]

    html_pos = _rendered_html()
    assert (
        'data-tip-en="It beat random entry recently, but not in the older years — so the recent reading is the only one supporting it."'
        in html_pos
    )
    assert (
        "data-tip-zh=\"它近年跑赢了随机入场，但在更早年份没有——因此只有近年读数在支持它。\""
        in html_pos
    )
    assert "older years didn't back it up" in html_pos
    assert "更早年份未能印证" in html_pos
    assert "Hasn't beaten random entry in the recent half" not in html_pos
    assert "近段未能跑赢随机入场" not in html_pos
    assert "+20 points better than entering at random" in html_pos
    assert "较随机入场高 20 个百分点" in html_pos
    assert "+-" not in html_pos

    raw_neg = _make_raw()
    for combo in raw_neg["combos"]["long"]:
        if not combo.get("consistent"):
            combo["edge_wr_test"] = -0.02
    html_neg = render_html(_ROOT, build_context(raw_neg, {}))
    assert "Hasn't beaten random entry in the recent half" in html_neg
    assert "近段未能跑赢随机入场" in html_neg
    assert (
        "data-tip-en=\"Hasn't beaten random entry in the recent half — so the recent reading is not supporting it.\""
        in html_neg
    )
    assert (
        "data-tip-zh=\"近段未能跑赢随机入场——因此近年读数并不支持它。\""
        in html_neg
    )
    assert "beat random entry recently" not in html_neg
    assert "它近年跑赢了随机入场，但在更早年份没有" not in html_neg
    assert "older years didn't back it up" not in html_neg
    assert "更早年份未能印证" not in html_neg
    assert "-2 points better than entering at random" in html_neg
    assert "较随机入场 -2 个百分点" in html_neg
    assert "+-" not in html_neg
    assert "+-2" not in html_neg

    raw_zero = _make_raw()
    for combo in raw_zero["combos"]["long"]:
        if not combo.get("consistent"):
            combo["edge_wr_test"] = 0
    html_zero = render_html(_ROOT, build_context(raw_zero, {}))
    assert "Hasn't beaten random entry in the recent half" in html_zero
    assert "近段未能跑赢随机入场" in html_zero
    assert "beat random entry recently" not in html_zero
    assert "+-" not in html_zero

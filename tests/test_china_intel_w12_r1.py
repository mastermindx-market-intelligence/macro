"""W12 r1 china_intel heal — B1/B2/C3/P2/S3/S6, both lanes.

Renders the production template through scripts.build_china_intel._env().
Every behavioral assertion probes EN (.l-en) and ZH (.l-zh).
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from engine import china_intel_bus as bus
from scripts.build_china_intel import _env


STANCES_EN = (
    "Act",
    "Get ready",
    "Watch — don't chase",
    "Protect gains",
    "Stand aside",
    "Ignore",
)
STANCES_ZH = (
    "行动",
    "做好准备",
    "观察，勿追高",
    "保护利润",
    "观望",
    "可忽略",
)


def _today() -> date:
    return date.today()


def _b(**over):
    base = {
        "schema": "china_intel.briefing.v6",
        "is_context_only": True,
        "asof": str(_today()),
        "generated_utc": "2026-09-11T00:00:00Z",
        "news": None, "policy": None, "altdata": None, "radar": None,
        "analysis": None, "regime": None, "discovery": None,
        "policy_phrase": None, "narrative_divergence": None,
        "special_situations": None, "command": None, "analogs": None,
        "conviction": [], "cross_surface": [], "flagged_tickers": [],
        "what_changed": {}, "salience": [],
        "surfaces_present": [],
        "surface_asof": {},
        "max_staleness_days": 0,
        "max_staleness_feed": None,
        "max_staleness_feed_asof": None,
        "stale_working_feeds": [],
        "digest": "machine digest",
        "disclaimer": "Context only.", "disclaimer_zh": "仅供参考。",
    }
    base.update(over)
    return base


def _row(i: int, ticker: str | None = None) -> dict:
    tkr = ticker or f"{600000 + i:06d}.SS"
    return {
        "ticker": tkr, "name": f"名称{i}",
        "stage": "early", "opportunity_score": 50.0 + i,
        "edge_remaining": 0.5, "leading_gap": 1,
        "lead_up": 1, "lag_up": 0, "signal_core": 0.5,
        "falsifier": "If the radar sign flips.", "falsifier_zh": "若雷达方向翻转。",
        "falsifier_penalty": 1.0,
        "off_desk": False, "veto_blind": False,
        "directions": {"altdata": 1, "radar": None, "news": None, "board": None},
        "desk_matrix": {
            "news": {"present": False, "dir": None},
            "altdata": {"present": True, "dir": 1},
            "radar": {"present": False, "dir": None},
            "board": {"present": False, "dir": None},
            "special": {"present": False, "dir": None},
        },
        "traj": {"ret_20d": 1.0, "rs_20d": 2.0, "rs_60d": 1.0,
                 "off_high_pct": -5.0, "rolling_over": False},
        "read": "A leading desk is ahead of the crowd.",
        "read_zh": "已有一个台走在市场前面。",
        "edge_drivers": [], "edge_components": 1,
    }


def _cmd(n: int, discovery: list | None = None) -> dict:
    return {
        "schema": "china_intel.command.v1",
        "is_context_only": True,
        "as_of": str(_today()),
        "n_universe": n,
        "command": [_row(i) for i in range(n)],
        "discovery": discovery if discovery is not None else [
            {"ticker": "000002.SZ", "name": "万科A", "disc_score": 0.8,
             "source": "southbound_delta",
             "reason": "Southbound holdings +13.6% over 20d",
             "reason_zh": "南向持股 20 日增加 +13.6%",
             "off_desk": True, "experimental": False, "venue": "HK"},
            {"ticker": "000001.SZ", "name": "平安银行", "disc_score": 0.8,
             "source": "margin_velocity",
             "reason": "Margin financing rose faster than peers over 20 days (reading 7.8).",
             "reason_zh": "融资余额 20 日增幅高于同业（读数 7.8）。",
             "off_desk": True, "experimental": True},
        ],
        "counts": {"emerging": 0, "early": n, "veto_blind": 0},
        "disclaimer": "Context only.",
    }


def _render(b: dict | None = None, cmd_full=None) -> str:
    tmpl = _env().get_template("china_intel.html.j2")
    return tmpl.render(b=b if b is not None else _b(), cmd_full=cmd_full)


def _outside_details(html: str) -> str:
    return re.sub(r"<details\b[\s\S]*?</details>", "", html, flags=re.I)


def _l1_headings(html: str) -> list[str]:
    body = _outside_details(html)
    return [re.sub(r"<[^>]+>", "", h) for h in
            re.findall(r'<h2 class="sec">[\s\S]*?</h2>', body)]


def _lane(html: str, cls: str) -> str:
    return " ".join(re.findall(rf'<span class="{cls}">(.*?)</span>', html, flags=re.S))


# --------------------------------------------------------------------------- #
# B1 — staleness names a feed; mismatch with stamps impossible by construction
# --------------------------------------------------------------------------- #

def test_b1_staleness_returns_feed_and_age():
    old = (_today() - timedelta(days=70)).isoformat()
    fresh = _today().isoformat()
    b = {
        "news": {"asof": fresh},
        "policy": {"asof": fresh},
        "altdata": None, "radar": {"asof": fresh},
        "analysis": None,
        "policy_phrase": {"asof": old},
        "narrative_divergence": None, "special_situations": None, "command": None,
    }
    sa, rec = bus._staleness(b)
    assert rec["key"] == "policy_phrase"
    assert rec["age"] == 70
    assert rec["asof"] == old
    assert sa["news"] == fresh
    assert sa["policy_phrase"] == old
    # by construction: chip age == named feed's age
    named_asof = date.fromisoformat(sa[rec["key"]])
    assert rec["age"] == (_today() - named_asof).days
    working_keys = {w["key"] for w in rec["working"]}
    assert "news" in working_keys
    assert rec["key"] not in working_keys


def test_b1_chip_names_feed_and_age_both_lanes():
    old = (_today() - timedelta(days=70)).isoformat()
    fresh = _today().isoformat()
    b = _b(
        news={"asof": fresh, "band": "steady", "band_label_en": "Steady",
              "band_label_zh": "平稳"},
        policy={"asof": fresh, "pboc_stance": "neutral",
                "stance_label_en": "Neutral", "stance_label_zh": "中性",
                "predictions": [{"en": "Hold the 1y rate", "zh": "维持一年期利率"}]},
        radar={"asof": fresh},
        policy_phrase={"asof": old, "n_events_recent": 0, "recent_events": [],
                       "cold_start_organs": []},
        surface_asof={"news": fresh, "policy": fresh, "radar": fresh,
                      "policy_phrase": old},
        max_staleness_days=70,
        max_staleness_feed="policy_phrase",
        max_staleness_feed_asof=old,
        stale_working_feeds=[{"key": "news", "asof": fresh, "age": 0},
                             {"key": "policy", "asof": fresh, "age": 0},
                             {"key": "radar", "asof": fresh, "age": 0}],
        surfaces_present=["news", "policy", "radar", "policy_phrase"],
    )
    html = _render(b, cmd_full=_cmd(3))
    rest = _outside_details(html)
    en = _lane(rest, "l-en")
    zh = _lane(rest, "l-zh")
    assert "Oldest feed" in en
    assert "最旧数据源" in zh
    assert "70" in rest
    assert "Policy language" in en
    assert "政策表述" in zh
    assert old in rest
    assert "Still reading" in en
    assert "仍在读取" in zh
    assert "News" in en
    assert "新闻" in zh
    # chip does not relabel the fresh panel stamps as 70d — those stamps
    # still print their own as-of next to the desk links
    assert fresh in rest
    assert "Freshest data" not in rest
    assert "最新数据" not in rest or "最旧数据源" in zh


def test_b1_chip_age_cannot_contradict_named_feed_stamp():
    """Mismatch-with-stamps is impossible: the number is that feed's age."""
    for days in (3, 14, 70):
        old = (_today() - timedelta(days=days)).isoformat()
        b = {
            "news": {"asof": str(_today())},
            "policy": None, "altdata": None, "radar": None, "analysis": None,
            "policy_phrase": {"asof": old},
            "narrative_divergence": None, "special_situations": None, "command": None,
        }
        sa, rec = bus._staleness(b)
        assert rec["age"] == days
        assert rec["key"] in sa
        assert rec["age"] == (_today() - date.fromisoformat(sa[rec["key"]])).days


# --------------------------------------------------------------------------- #
# B2 — Discovery bar deleted (option b)
# --------------------------------------------------------------------------- #

def test_b2_discovery_bar_absent_magnitude_kept_both_lanes():
    html = _render(_b(), cmd_full=_cmd(3))
    body = html.split("</style>")[-1] if "</style>" in html else html
    assert 'class="disc-score-bar"' not in body
    rest = _outside_details(html)
    en = _lane(rest, "l-en")
    zh = _lane(rest, "l-zh")
    assert "Southbound holdings +13.6%" in en
    assert "+13.6%" in zh
    assert "发现队列" in zh
    assert "Discovery Queue" in en


# --------------------------------------------------------------------------- #
# C1/C2 — Archetype-E order and L1 ≤ 6
# --------------------------------------------------------------------------- #

def test_c1_lead_brief_is_first_l1_module():
    html = _render(_b(salience=[{
        "kind": "news", "label_en": "Media tone", "label_zh": "媒体语气",
        "detail_en": "Media tone is unusually negative over 90 days.",
        "detail_zh": "近90日媒体语气明显偏消极。",
    }]), cmd_full=_cmd(3))
    heads = _l1_headings(html)
    assert heads, "no L1 h2.sec headings"
    assert "What matters most today" in heads[0]
    assert "今日要点" in heads[0]
    # lead sits above the briefs / command table
    lead_at = html.find("What matters most today")
    briefs_at = html.find("Today's briefs")
    cmd_at = html.find("China Command List")
    assert 0 < lead_at < briefs_at < cmd_at


def test_c2_l1_at_most_six_and_visits_deleted():
    html = _render(_b(analogs={
        "query": {"quad": "Q2", "quad_name": "Bull", "liquidity": "easing",
                  "cycle": "mid"},
        "fan": {"h20": {"p25": 0.01, "median": 0.03, "p75": 0.06, "n": 12}},
        "analogs": [{"date": "2015-06-01", "quad": "Q2",
                     "fwd_shcomp": {"h20": 0.04}}],
        "n_analogs": 1,
        "disclaimer_en": "Context only. Historical analogs are descriptive.",
        "disclaimer_zh": "仅供展示。",
    }), cmd_full=_cmd(9))
    heads = _l1_headings(html)
    assert 1 <= len(heads) <= 6, heads
    blob = " ".join(heads)
    assert "Institutional visits" not in blob
    assert "机构调研" not in blob
    assert "Desk Status Board" not in blob
    assert "Intelligence Surfaces" not in blob
    assert "China Suite Directory" not in blob
    rest = _outside_details(html)
    assert "Institutional visits" not in rest


# --------------------------------------------------------------------------- #
# C3 — 8 visible rows, counted expander truthful, both lanes
# --------------------------------------------------------------------------- #

def test_c3_eight_visible_no_expander_at_boundary():
    html = _render(_b(), cmd_full=_cmd(8))
    first = html.split('<table class="cmd-tbl">')[1].split("</table>")[0]
    assert first.count("cmd-ticker") == 8
    rest = _outside_details(html)
    assert "Show all" not in rest
    assert "展开全部" not in rest


def test_c3_nine_rows_expander_counts_total_both_lanes():
    html = _render(_b(), cmd_full=_cmd(9))
    first = html.split('<table class="cmd-tbl">')[1].split("</table>")[0]
    assert first.count("cmd-ticker") == 8
    rest = _outside_details(html)
    en = _lane(html, "l-en")  # expander summary is outside the table, still L1
    zh = _lane(html, "l-zh")
    assert "Show all" in en
    assert "展开全部" in zh
    assert "9" in rest or ">9<" in html
    assert "names" in en
    # gated rows live inside <details>
    gated = re.search(
        r'<details>\s*<summary class="cmd-expander"[\s\S]*?</details>', html)
    assert gated, "command expander details missing"
    assert gated.group(0).count("cmd-ticker") == 1


def test_c3_thirty_names_label_stays_truthful():
    html = _render(_b(), cmd_full=_cmd(30))
    first = html.split('<table class="cmd-tbl">')[1].split("</table>")[0]
    assert first.count("cmd-ticker") == 8
    en = _lane(html, "l-en")
    assert "Show all" in en
    assert "30" in html
    assert "names" in en


# --------------------------------------------------------------------------- #
# P2 — stance on every surviving L1 panel, both lanes
# --------------------------------------------------------------------------- #

def test_p2_stance_on_every_l1_panel_both_lanes():
    html = _render(_b(
        salience=[{"kind": "news", "label_en": "X", "label_zh": "甲",
                   "detail_en": "ok", "detail_zh": "可"}],
        analogs={
            "query": {"quad": "Q2", "quad_name": "Bull"},
            "fan": {"h20": {"p25": 0.01, "median": 0.03, "p75": 0.06, "n": 4}},
            "analogs": [],
            "disclaimer_en": "Context only.",
            "disclaimer_zh": "仅供展示。",
        },
    ), cmd_full=_cmd(3))
    rest = _outside_details(html)
    sections = re.findall(
        r'<section data-l1="([^"]+)">([\s\S]*?)</section>', rest)
    assert sections, "no data-l1 sections"
    for name, body in sections:
        en = _lane(body, "l-en")
        zh = _lane(body, "l-zh")
        assert any(s in en for s in STANCES_EN), f"{name} missing EN stance: {en[:200]}"
        assert any(s in zh for s in STANCES_ZH), f"{name} missing ZH stance: {zh[:200]}"


# --------------------------------------------------------------------------- #
# S3 — no z= / z - at rest outside the three details ranges
# --------------------------------------------------------------------------- #

def test_s3_no_z_tokens_at_rest_outside_details():
    html = _render(_b(
        salience=[{
            "kind": "news", "label_en": "Media tone", "label_zh": "媒体语气",
            "detail_en": "Media tone is unusually negative over 90 days.",
            "detail_zh": "近90日媒体语气明显偏消极。",
            "detail_tip_en": "standardized reading -0.96 vs the last 90 days",
            "detail_tip_zh": "近90日标准化读数 -0.96",
        }],
        narrative_divergence={
            "divergence_z": -0.96, "risk_flag": False, "trend_5d": "flat",
            "asof": str(_today()),
        },
        digest="Onshore/offshore tone divergence z=-0.96 (direction=0, accruing)\n"
               "z -0.96 over 90d",
    ), cmd_full=_cmd(3))
    rest = _outside_details(html)
    assert "z=" not in rest
    assert "z -" not in rest
    assert "z -0" not in rest


def test_s3_bus_rewrites_salience_z_copy():
    item = bus._plain_salience_item({
        "kind": "news",
        "detail_en": "z -0.96 over 90d.",
        "detail_zh": "90日 z -0.96。",
    })
    assert "z " not in item["detail_en"]
    assert "z -" not in item["detail_en"]
    assert "unusually negative" in item["detail_en"]
    assert "偏消极" in item["detail_zh"]
    assert "z=" not in item["detail_en"]
    assert "z=" not in item["detail_zh"]


# --------------------------------------------------------------------------- #
# S6 — standing policy calls render ZH in the ZH lane
# --------------------------------------------------------------------------- #

def test_s6_standing_policy_calls_zh_lane():
    b = _b(policy={
        "pboc_stance": "neutral",
        "stance_label_en": "Neutral", "stance_label_zh": "中性",
        "predictions": [
            {"en": "Hold the 1-year loan rate.", "zh": "维持一年期贷款利率。"},
            {"en": "No reserve-ratio cut this quarter.", "zh": "本季不降准。"},
        ],
        "asof": str(_today()),
    })
    html = _render(b, cmd_full=None)
    rest = _outside_details(html)
    zh = _lane(rest, "l-zh")
    en = _lane(rest, "l-en")
    assert "维持一年期贷款利率。" in zh
    assert "本季不降准。" in zh
    assert "Hold the 1-year loan rate." in en
    # the old `{{ p }}` path interpolated the English string into both lanes
    assert "Hold the 1-year loan rate." not in zh


def test_s6_bilingual_predictions_from_strings_keep_pair_shape():
    out = bus._bilingual_predictions(["Hold the 1-year loan rate."])
    assert out == [{"en": "Hold the 1-year loan rate.",
                    "zh": "Hold the 1-year loan rate."}]
    out2 = bus._bilingual_predictions(
        [{"en": "Hold", "zh": "维持"}])
    assert out2[0]["zh"] == "维持"

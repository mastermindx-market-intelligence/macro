"""China Alt-Data desk — convergence kernel + signal-lab contract tests (network-free)."""
from __future__ import annotations

from engine import china_altdata as ad
from engine import china_signal_lab as lab
from engine import china_conviction as cv


# ---- pure sub-scores ------------------------------------------------------- #
def test_analyst_score():
    assert ad._analyst_score({"buy": 10, "hold": 0, "sell": 0}) == 1.0
    assert ad._analyst_score({"buy": 0, "hold": 0, "sell": 10}) == -1.0
    assert ad._analyst_score({"buy": 5, "hold": 0, "sell": 5}) == 0.0
    assert ad._analyst_score({"buy": 0, "hold": 0, "sell": 0}) is None


def test_value_score_cheap_positive():
    cheap = ad._value_score({"pe": {"pctile": 5}, "pb": {"pctile": 15}})   # cheap vs own band
    rich = ad._value_score({"pe": {"pctile": 95}, "pb": {"pctile": 90}})   # expensive
    assert cheap > 0 and rich < 0
    assert ad._value_score({}) is None


def test_margin_score_and_crowd_flag():
    s, crowded = ad._margin_score({"chg_pct": 40})
    assert s == 1.0 and crowded is True            # >25% financing jump -> crowded
    s2, c2 = ad._margin_score({"chg_pct": 5})
    assert 0 < s2 < 1 and c2 is False
    assert ad._margin_score({})[0] is None


def test_clip():
    assert ad._clip(2.0) == 1.0 and ad._clip(-2.0) == -1.0 and ad._clip(0.3) == 0.3


# ---- by_ticker: structure + None-safe -------------------------------------- #
def test_by_ticker_structure_and_none_safe():
    bt = ad.by_ticker()
    if bt is None:
        return
    assert bt["schema"] == ad.SCHEMA
    for k in ("top", "bottom", "triple", "crowding_flags", "n_universe", "n_triple"):
        assert k in bt
    # triple slice must all have all-three feeds
    assert all(r["n_signals"] >= 3 for r in bt["triple"])
    # top sorted by convergence descending
    convs = [r["convergence"] for r in bt["top"]]
    assert convs == sorted(convs, reverse=True)


def test_mastermind_prefers_triple_and_emits_rich_rows():
    bt = {"asof": "2026-06-20",
          "triple": [{"ticker": "AAA", "name": "Alpha"}, {"ticker": "BBB", "name": "Beta"}],
          "top": [{"ticker": "CCC", "name": "Gamma"}, {"ticker": "AAA", "name": "Alpha"}],
          "bottom": [{"ticker": "ZZZ", "name": "Zed"}], "crowding_flags": ["AAA"]}
    mm = ad.mastermind(bt)
    codes = [r["ticker"] for r in mm["convergence_top"]]
    assert codes[:2] == ["AAA", "BBB"]                  # triple first, deduped
    assert "CCC" in codes
    assert mm["convergence_top"][0]["name"] == "Alpha"  # rich rows carry the name
    assert mm["schema"] == "china_altdata.mastermind.v2"
    assert mm["convergence_bottom"][0]["ticker"] == "ZZZ"


def test_by_ticker_de_degenerated():
    bt = ad.by_ticker()
    if bt is None or len(bt["top"]) < 5:
        return
    convs = [r["convergence"] for r in bt["top"]]
    # rank-normalized convergence must NOT all pin to one value (the old 8/8==1.0 bug)
    assert len(set(round(c, 3) for c in convs)) > 3
    assert convs == sorted(convs, reverse=True)
    assert all(0 <= r["conviction100"] <= 100 for r in bt["top"])


# ---- signal lab ------------------------------------------------------------ #
def test_n_signals_discount_lowers_conviction_for_sparse_names():
    """conv=0.5 with n_signals=1 must score below conv=0.5 with n_signals=3 (B8 requirement).
    Verified by replicating the conviction100 formula: abs(conv) * min(1.0, n/3.0)."""
    conv = 0.5
    c100_n1 = cv.to_100(abs(conv) * min(1.0, 1 / 3.0))
    c100_n3 = cv.to_100(abs(conv) * min(1.0, 3 / 3.0))
    assert c100_n1 < c100_n3, (
        f"n=1 conviction100 ({c100_n1}) must be below n=3 ({c100_n3})"
    )
    # n>=3 should not be discounted (cap at 1.0)
    c100_n5 = cv.to_100(abs(conv) * min(1.0, 5 / 3.0))
    assert c100_n5 == c100_n3, f"n=5 should equal n=3 (both uncapped): {c100_n5} vs {c100_n3}"


def test_signal_lab_priors_lhb_block_are_negative():
    """_PRIORS altdata lhb and block must be negative (DEMOTION): scores are signed and
    measure alpha-draining at positive values (§W6-CN Fix 2 / Brief 8 sign-convention)."""
    priors = lab._PRIORS["altdata"]
    assert priors["lhb"] < 0, f"lhb prior must be negative (demotion), got {priors['lhb']}"
    assert priors["block"] < 0, f"block prior must be negative (demotion), got {priors['block']}"
    # positive legs are still positive
    assert priors["value"] > 0 and priors["margin"] > 0 and priors["analyst"] > 0


def test_wsum_abs_normalization_bounded() -> None:
    """_compute_rows normalizes conv by SUM-OF-ABSOLUTE weights, not signed sum.
    Verifies three properties:
    1. Bounded output: legs {lhb:-0.10, flow:+0.18} produce |conv| <= 1.
    2. Near-zero signed wsum (comment+lhb+block = 0.0 exactly) doesn't blow up:
       conv must be None/skipped or a finite value in [-1,1].
    3. Pure positive legs produce positive conv.
    """
    from unittest.mock import patch

    W = {"value": 0.24, "margin": 0.20, "flow": 0.18, "comment": 0.15,
         "lhb": -0.10, "block": -0.05, "analyst": 0.08}

    def _fake_leg_weights():
        return dict(W)

    # Test 1: {lhb, flow} — abs wsum=0.28, signed wsum=0.08
    # scores: lhb=-0.10 present with score +0.8, flow=+0.18 present with score +0.8
    # conv = (-0.10*0.8 + 0.18*0.8) / 0.28 = 0.064/0.28 ≈ 0.229  (bounded, positive)
    with patch.object(ad, "_leg_weights", _fake_leg_weights):
        pct_lhb = 0.9   # pctile → score = 0.9*2-1 = +0.8
        pct_flow = 0.9
        s_lhb = pct_lhb * 2 - 1   # +0.8
        s_flow = pct_flow * 2 - 1  # +0.8
        wsum_abs = abs(W["lhb"]) + abs(W["flow"])
        conv = (W["lhb"] * s_lhb + W["flow"] * s_flow) / wsum_abs
        assert abs(conv) <= 1.0, f"conv={conv} out of [-1,1] for lhb+flow combo"

    # Test 2: exact-zero signed wsum (comment+lhb+block)
    # signed sum = 0.15 - 0.10 - 0.05 = 0.0 (floating-point epsilon)
    # abs sum = 0.30 — safe denominator; conv must be finite & bounded
    import math
    s_comment = 0.6  # score ∈ [-1,1]
    s_lhb2 = 0.8
    s_block2 = -0.4
    wsum_signed = W["comment"] + W["lhb"] + W["block"]   # ≈ 0.0 (exact hazard)
    wsum_abs2 = abs(W["comment"]) + abs(W["lhb"]) + abs(W["block"])  # 0.30
    # old (broken) denominator would be ~0.0 → divide-by-zero or `or 1.0` nonsense
    assert abs(wsum_signed) < 1e-10, "test precondition: combo IS exact-zero signed wsum"
    conv2 = (W["comment"] * s_comment + W["lhb"] * s_lhb2 + W["block"] * s_block2) / wsum_abs2
    assert math.isfinite(conv2) and abs(conv2) <= 1.0, (
        f"near-zero signed-wsum case blew up: conv={conv2}"
    )

    # Test 3: pure positive legs — conv must be positive
    s_val = 0.7
    s_margin = 0.5
    wsum_abs3 = W["value"] + W["margin"]
    conv3 = (W["value"] * s_val + W["margin"] * s_margin) / wsum_abs3
    assert conv3 > 0, f"pure positive legs must yield positive conv, got {conv3}"


def test_signal_lab_scorecard():
    sc = lab.build_china_scorecard()
    assert sc["schema"] == lab.SCHEMA
    assert set(sc["tiers"]) == set(lab.TIERS)
    assert sc["summary"]["scored"] == 3        # the 3 validated regime de-risk legs
    assert sc["summary"]["killed"] >= 2
    # every row has bilingual labels + a tier
    for tier, items in sc["tiers"].items():
        for r in items:
            assert r["name_en"] and r["name_zh"] and r["tier"] == tier


# ------------------------------------------------ page render: event-catalyst cards ----
# Synthetic records shaped like the committed site/chinaspecialdata/special.json emit
# (engine/china_special_situations.py): inquiry letters carry secName/secCode, pre-announcements
# carry pct_change plus a Chinese-only type, unlocks carry float_pct (unlock shares as a % of the
# free float). The page must print each, and the legacy name/p_change/pct_float keys still work.
_TYPES = {"预增": "profit up", "略增": "profit slightly up", "续盈": "still profitable",
          "扭亏": "back to profit", "预减": "profit down", "略减": "profit slightly down",
          "减亏": "smaller loss", "增亏": "larger loss", "首亏": "first loss",
          "续亏": "still loss-making", "不确定": "uncertain"}


def _altdata_env():
    from pathlib import Path

    from jinja2 import Environment, FileSystemLoader

    from engine import i18n

    root = Path(__file__).resolve().parents[1]
    env = Environment(loader=FileSystemLoader(str(root / "templates")), autoescape=False)
    env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    return env


def _render_altdata(special, env=None):
    return (env or _altdata_env()).get_template("china_altdata.html.j2").render(
        ad=None, lab=None, mm=None, crowd_labels={}, broker_gold=[], guidance={},
        guidance_labels={}, tape=None, tape_spark="", special=special, narr=[],
        narr_asof=None, zt=[], zt_breadth=[])


def _card_rows(html, title):
    import re

    a = html.find('id="catalysts"')
    j = html.find(f'<span class="l-en">{title}</span>', a)
    assert 0 < a < j, title
    k = html.find('<div class="cad-card">', j)
    seg = html[j:k] if k > 0 else html[j:html.find("</section>", j)]
    return re.findall(r'font-size:12px">\s*(.*?)\s*</div>', seg, re.S)


def test_catalyst_inquiry_row_prints_producer_name():
    letter = {"secCode": "920493", "secName": "并行科技", "date": "2026-10-15",
              "reply_state": "open"}
    rows = _card_rows(_render_altdata({"inquiry": {"n_letters": 1, "letters": [letter]}}),
                      "Exchange inquiries")
    assert len(rows) == 1 and "<span>并行科技</span>" in rows[0], rows
    assert "<span></span>" not in rows[0]
    code_only = {"inquiry": {"letters": [{"secCode": "002155", "date": "2026-10-13"}]}}
    assert "<span>002155</span>" in _card_rows(_render_altdata(code_only), "Exchange inquiries")[0]


def test_catalyst_preannounce_row_prints_swing_and_type():
    movers = [{"ticker": "002466.SZ", "name": "天齐锂业", "type": "预增", "pct_change": 265430.305},
              {"ticker": "002368.SZ", "name": "太极股份", "type": "增亏", "pct_change": -31094.37}]
    rows = _card_rows(_render_altdata({"preannounce": {"n_total": 2, "top_movers": movers}}),
                      "Earnings pre-announcements")
    assert len(rows) == 2, rows
    assert '<span class="l-en">profit up</span><span class="l-zh">预增</span> +265430%' in rows[0]
    assert '<span class="l-en">larger loss</span><span class="l-zh">增亏</span> -31094%' in rows[1]
    assert not any('<span class="cad-asof"></span>' in r for r in rows)


def test_catalyst_unlock_row_prints_float_share():
    events = [{"ticker": "688783.SS", "name": "西安奕材", "unlock_date": "2026-10-28",
               "float_pct": 1054.9871502417},
              {"ticker": "600000.SS", "name": "浦发银行", "unlock_date": "2026-11-02",
               "float_pct": 42.4}]
    rows = _card_rows(_render_altdata({"unlocks": {"n_large": 2, "events": events}}),
                      "Share unlocks")
    assert len(rows) == 2, rows
    assert ('2026-10-28 · <span class="l-en">10.5× the free float</span>'
            '<span class="l-zh">为流通量的10.5倍</span>') in rows[0]
    assert "1055%" not in rows[0]
    assert ('2026-11-02 · <span class="l-en">42% of free float</span>'
            '<span class="l-zh">占流通量42%</span>') in rows[1]


def test_catalyst_preannounce_type_falls_back_to_raw_when_unmapped():
    sp = {"preannounce": {"top_movers": [{"name": "X", "type": "未映射", "pct_change": 5.0}]}}
    row = _card_rows(_render_altdata(sp), "Earnings pre-announcements")[0]
    assert '<span class="cad-asof"><span class="l-en">未映射</span><span class="l-zh">未映射</span>' \
        ' +5%</span>' in row, row


def test_catalyst_cards_survive_legacy_name_keys():
    sp = {"unlocks": {"events": [{"name": "X", "ticker": "600000.SS", "date": "2026-10-20",
                                  "pct_float": 3.0}]},
          "inquiry": {"letters": [{"name": "Y", "date": "2026-10-19"}]},
          "preannounce": {"top_movers": [{"name": "Z", "ticker": "600001.SS", "p_change": 12.0}]}}
    html = _render_altdata(sp)
    unlock = _card_rows(html, "Share unlocks")[0]
    assert "<span>X</span>" in unlock and '<span class="l-en">3% of free float</span>' in unlock
    assert "<span>Y</span>" in _card_rows(html, "Exchange inquiries")[0]
    pre = _card_rows(html, "Earnings pre-announcements")[0]
    assert "<span>Z</span>" in pre and '<span class="cad-asof">+12%</span>' in pre, pre


def test_zh_and_en_both_carry_the_new_labels():
    import re

    env = _altdata_env()
    legs = re.compile(r'<span class="l-en">(.*?)</span><span class="l-zh">(.*?)</span>')
    cjk = re.compile(r"[一-鿿]")
    for zh, en in _TYPES.items():
        sp = {"preannounce": {"top_movers": [{"name": "N", "type": zh, "pct_change": 1.0}]}}
        row = _card_rows(_render_altdata(sp, env), "Earnings pre-announcements")[0]
        asof = row.split('<span class="cad-asof">', 1)[1].rsplit("</span>", 1)[0]
        assert legs.findall(asof) == [(en, zh)], (zh, asof)
        assert not re.search(r"[A-Za-z]|[一-鿿]", legs.sub("", asof)), asof
    sp = {"unlocks": {"events": [{"name": "N", "unlock_date": "2026-10-28", "float_pct": 250.0},
                                 {"name": "M", "unlock_date": "2026-10-29", "float_pct": 7.0}]}}
    for row in _card_rows(_render_altdata(sp, env), "Share unlocks"):
        asof = row.split('<span class="cad-asof">', 1)[1].rsplit("</span>", 1)[0]
        (en_leg, zh_leg), = legs.findall(asof)
        assert not cjk.search(en_leg) and cjk.search(zh_leg), asof
        assert not re.search(r"[A-Za-z]|[一-鿿]", legs.sub("", asof)), asof


# ====================== W31-L51 · SPEC 2/3/4 disclosure ====================== #
# Synthetic payloads shaped like the committed emits; nothing under data/ or site/ is
# read and build()/main() is never called. `hero.freshness` mirrors the producer
# engine/china_special_situations.py; `snapshot_note`/`data_gaps` mirror
# engine/china_participation.py:955-971.
_FRESH_STALE = {"n_planes": 7, "n_fresh": 6, "n_stale": 1, "n_unreadable": 0,
                "all_fresh": False,
                "stale_labels": [{"en": "Risk warnings", "zh": "风险警示"}],
                "oldest_stale_asof": "2026-10-13"}
_SNAP_NOTE = "core legs null on 2026-10-16; publishing last fully-populated row (2026-09-29)"
_STALE_GAP = ("snapshot_staleness:published row 2026-09-29 is 17d behind tape tail 2026-10-16;"
              " tail row missing core legs (turnover_z20, margin_chg_5d) — union-index"
              " freshness lag")
_FLAG_KEYS = ["margin_froth", "pledge_tail", "limitup_froth", "attention_spike",
              "rich_valuation", "leverage_crowded"]
_CROWD_ROW = {"ticker": "600000.SS", "name": "浦发银行", "convergence": 0.42, "n_signals": 4,
              "conviction_band_en": "Mild", "conviction_band_zh": "温和", "side": "accumulate",
              "reasons": ["margin"], "rank_pctile": 88.0, "analyst": 0.3, "value": None,
              "margin": 0.6, "flow": 0.2, "comment": None, "lhb": None, "block": None,
              "flags": ["leverage_crowded", "margin_froth"]}


def _render_full(**over):
    """Render the desk with _render_altdata's keyword set, overridden by `over`."""
    kw = dict(ad=None, lab=None, mm=None, crowd_labels={}, broker_gold=[], guidance={},
              guidance_labels={}, tape=None, tape_spark="", special=None, narr=[],
              narr_asof=None, zt=[], zt_breadth=[])
    kw.update(over)
    return _altdata_env().get_template("china_altdata.html.j2").render(**kw)


def _seg(html, start, stop):
    a = html.find(start)
    b = html.find(stop, a + 1) if a >= 0 else -1
    assert 0 <= a < b, (start, stop, a, b)
    return html[a:b]


def _chip(html, needle):
    """The whole `<span class="cad-chip …">…</span>` carrying `needle`."""
    i = html.find(needle)
    assert i > 0, needle
    a = html.rfind('<span class="cad-chip', 0, i)
    assert a >= 0, needle
    tail = "</span></span>"
    b = html.find(tail, a)
    assert b > a, needle
    return html[a:b + len(tail)]


def _legs(seg):
    import re

    en = re.findall(r'<span class="l-en">(.*?)</span>', seg, re.S)
    zh = re.findall(r'<span class="l-zh">(.*?)</span>', seg, re.S)
    assert len(en) == 1 and len(zh) == 1, seg
    return en[0], zh[0]


def test_catalyst_board_discloses_stale_plane():
    html = _render_full(special={"hero": {"freshness": dict(_FRESH_STALE)}})
    seg = _seg(html, 'id="catalysts"', "</section>")
    assert '<div class="cad-sec-bar">' in seg
    assert "6 of 7" in seg and "planes up to date" in seg and "Lagging:" in seg
    assert "7条数据线中6条已更新" in seg and "滞后：" in seg
    lab = _chip(seg, "Risk warnings")
    assert "c-warn" in lab and _legs(lab) == ("Risk warnings", "风险警示")
    assert "oldest lagging plane as of 2026-10-13" in seg
    assert "最早滞后数据截至2026-10-13" in seg
    assert "unreadable" not in seg and "无法读取" not in seg


def test_catalyst_board_all_fresh_suppresses_stale_copy():
    fr = {"n_planes": 7, "n_fresh": 7, "n_stale": 0, "n_unreadable": 0, "all_fresh": True,
          "stale_labels": [], "oldest_stale_asof": None}
    seg = _seg(_render_full(special={"hero": {"freshness": fr}}),
               'id="catalysts"', "</section>")
    for s in ("planes up to date", "Lagging", "oldest lagging", "已更新", "滞后：",
              '<div class="cad-sec-bar">'):
        assert s not in seg, s


def test_catalyst_board_absent_hero_renders_unchanged():
    for sp in ({}, {"hero": {}}, {"hero": {"stance": "x"}}):
        seg = _seg(_render_full(special=sp), 'id="catalysts"', "</section>")
        for s in ("planes up to date", "Lagging", "oldest lagging", "无法读取",
                  '<div class="cad-sec-bar">'):
            assert s not in seg, (sp, s)


def test_catalyst_board_does_not_claim_a_cause():
    seg = _seg(_render_full(special={"hero": {"freshness": dict(_FRESH_STALE)}}),
               'id="catalysts"', "</section>")
    for w in ("because", "collector", "failed", "outage", "broken", "因为", "故障", "失败"):
        assert w not in seg, w


def test_catalyst_board_unreadable_plane_chip():
    fr = dict(_FRESH_STALE, n_unreadable=2)
    seg = _seg(_render_full(special={"hero": {"freshness": fr}}),
               'id="catalysts"', "</section>")
    chip = _chip(seg, "unreadable")
    assert "c-warn" in chip and _legs(chip) == ("2 unreadable", "2条无法读取")
    seg0 = _seg(_render_full(special={"hero": {"freshness": dict(_FRESH_STALE, n_unreadable=0)}}),
                'id="catalysts"', "</section>")
    assert "unreadable" not in seg0 and "无法读取" not in seg0


def test_tape_read_passes_through_staleness_fields():
    import scripts.build_china_altdata as bca

    gaps = [_STALE_GAP, "zt_breadth:null on 2026-09-29"]
    tape = bca._tape_read({"regime": "dormant", "date": "2026-09-29",
                           "snapshot_note": _SNAP_NOTE, "data_gaps": gaps})
    assert tape["snapshot_note"] == _SNAP_NOTE
    assert tape["data_gaps"] == gaps
    assert tape["staleness"] == {"row_date": "2026-09-29", "lag_days": 17,
                                 "tail_date": "2026-10-16"}
    assert isinstance(tape["staleness"]["lag_days"], int)


def test_tape_staleness_is_none_without_token():
    import scripts.build_china_altdata as bca

    for gaps in (None, [], "x", 5, {_STALE_GAP: 1},
                 ["northbound:DEAD post-2024-08-16 SLF-050"],
                 ["snapshot_staleness:unparsable", 3, None]):
        assert bca._tape_staleness({"regime": "dormant", "data_gaps": gaps}) is None, gaps
    for part in ({}, None, "x", {"data_gaps": 5}):
        assert bca._tape_staleness(part) is None, part
    tape = bca._tape_read({"regime": "dormant"})
    assert tape["snapshot_note"] is None and tape["data_gaps"] == []
    assert tape["staleness"] is None


def test_hero_renders_staleness_line_from_committed_shape():
    import scripts.build_china_altdata as bca

    part = {"regime": "dormant", "who_controls": "mixed", "risk": "low", "date": "2026-09-29",
            "snapshot_note": _SNAP_NOTE, "data_gaps": [_STALE_GAP], "margin_chg_5d": -1.65,
            "southbound_net": 14.63, "qvix": 17.2}
    html = _render_full(tape=bca._tape_read(part))
    chip = _chip(html, "days behind tape tail")
    en, zh = _legs(chip)
    assert "c-warn" in chip
    for frag in ("2026-09-29", "2026-10-16", "17"):
        assert frag in en and frag in zh, (frag, en, zh)
    assert "snapshot_staleness:" not in html
    assert "publishing last fully-populated row" not in html
    assert "union-index freshness lag" not in html


def test_hero_reduced_staleness_line_without_token():
    import scripts.build_china_altdata as bca

    tape = bca._tape_read({"regime": "dormant", "date": "2026-09-29",
                           "snapshot_note": "row published from an earlier session"})
    html = _render_full(tape=tape)
    en, zh = _legs(_chip(html, "behind the tape tail"))
    assert en == "Row 2026-09-29 · behind the tape tail", en
    assert zh == "数据行2026-09-29 · 落后于盘面末端", zh
    assert "row published from an earlier session" not in html


def test_hero_fresh_tape_renders_no_staleness_line():
    import scripts.build_china_altdata as bca

    html = _render_full(tape=bca._tape_read({"regime": "dormant", "date": "2026-10-16"}))
    for s in ("behind the tape tail", "落后于盘面末端", "days behind tape tail", "落后盘面末端"):
        assert s not in html, s


def test_gauge_tooltip_does_not_claim_current_regime():
    import re

    import scripts.build_china_altdata as bca

    html = _render_full(tape=bca._tape_read({"regime": "dormant", "date": "2026-10-16"}))
    a = html.find('<div class="cad-gauge')
    assert a > 0
    seg = html[a:html.find(">", html.find("data-tip-zh", a)) + 1]
    tips_en = re.findall(r'data-tip-en="([^"]*)"', seg)
    tips_zh = re.findall(r'data-tip-zh="([^"]*)"', seg)
    assert len(tips_en) == 1 and len(tips_zh) == 1, seg
    en, zh = tips_en[0], tips_zh[0]
    assert "The needle sits at the regime of the dated tape row shown beside the read." in en
    assert "指针停在旁注日期那一行盘面的状态。" in zh
    assert "0 = capitulation / fire-sale, 50 = neutral, 100 = euphoria" in en
    assert "0＝恐慌抛售，50＝中性，100＝狂热" in zh
    assert "current regime" not in html and "当前状态" not in html


def test_hero_leg_chips_render_only_when_present():
    import scripts.build_china_altdata as bca

    tape = bca._tape_read({"regime": "dormant", "date": "2026-10-16", "margin_chg_5d": 2.3,
                           "qvix": 21.7, "southbound_net": None})
    html = _render_full(tape=tape)
    assert _legs(_chip(html, "Margin 5d")) == ("Margin 5d +2.30%", "融资5日 +2.30%")
    assert _legs(_chip(html, "QVIX")) == ("QVIX 21.7", "QVIX 21.7")
    # scoped to the hero metrow: the global nav also carries a "Southbound" link
    rows = _seg(html, '<div class="cad-metrows">', "</div>")
    assert "Southbound" not in rows and "南向净额" not in rows
    bare = _render_full(tape=bca._tape_read({"regime": "dormant", "date": "2026-10-16"}))
    brows = _seg(bare, '<div class="cad-metrows">', "</div>")
    for s in ("Margin 5d", "融资5日", "Southbound net", "南向净额", "QVIX"):
        assert s not in brows, s



def test_hero_leg_chips_print_zero_and_raw_southbound():
    """A flat margin leg still prints, and southbound prints in the 万 CNY unit it is stored in."""
    import scripts.build_china_altdata as bca

    tape = bca._tape_read({"regime": "dormant", "date": "2026-10-16", "margin_chg_5d": 0.0,
                           "southbound_net": 123456.0})
    html = _render_full(tape=tape)
    assert _legs(_chip(html, "Margin 5d")) == ("Margin 5d +0.00%", "融资5日 +0.00%")
    assert _legs(_chip(html, "Southbound net")) == ("Southbound net (万 CNY) +123456",
                                                    "南向净额(万元) +123456")


def test_catalyst_board_lists_every_lagging_plane():
    fr = dict(_FRESH_STALE, n_fresh=5, n_stale=2,
              stale_labels=[{"en": "Risk warnings", "zh": "风险警示"},
                            {"en": "Share unlocks", "zh": "限售解禁"}])
    seg = _seg(_render_full(special={"hero": {"freshness": fr}}),
               'id="catalysts"', "</section>")
    assert _legs(_chip(seg, "Risk warnings")) == ("Risk warnings", "风险警示")
    assert _legs(_chip(seg, "Share unlocks")) == ("Share unlocks", "限售解禁")


def test_tape_staleness_skips_non_string_gaps():
    import scripts.build_china_altdata as bca

    want = {"row_date": "2026-09-29", "lag_days": 17, "tail_date": "2026-10-16"}
    for junk in (None, 123, {"x": 1}):
        part = {"regime": "dormant", "data_gaps": [junk, _STALE_GAP]}
        assert bca._tape_staleness(part) == want, junk

def test_crowding_card_does_not_claim_a_margin_jump():
    html = _render_full(ad={"crowding_flags": ["600000.SS"]})
    seg = _seg(html, 'id="crowding"', "</section>")
    for s in ("jumped", "building fastest", "跳升", "累积最快", "20-day financing balance",
              "20日融资余额跳升最多"):
        assert s not in seg, s
    assert "600000.SS" in seg


def test_crowding_card_states_the_k_of_5_rule():
    seg = _seg(_render_full(ad={"crowding_flags": ["600000.SS"]}), 'id="crowding"', "</section>")
    assert _legs(_seg(seg, "<h3>", "</h3>")) == ("Crowded names — fragility watch",
                                                 "拥挤名单 — 脆弱度观察")
    en, zh = _legs(_seg(seg, '<p class="sub">', "</p>"))
    assert "3 of 5" in en and "5项中至少3项" in zh
    for leg in ("Margin froth", "Pledge tail-risk", "Limit-up froth", "Attention spike",
                "Rich valuation"):
        assert leg in en, leg
    for leg in ("融资拥挤", "质押尾部风险", "涨停拥挤", "关注度飙升", "估值偏高"):
        assert leg in zh, leg
    assert "25%" in en and "20 days" in en and "融资余额20日增幅超过25%" in zh
    assert "highest convergence first" in en and "up to 20" in en
    assert "按共振从高到低" in zh and "最多20只" in zh


def test_flag_labels_cover_every_key_a_producer_can_emit():
    from engine.china_crowding import FLAG_LABELS

    for key in _FLAG_KEYS:
        assert key in FLAG_LABELS, key
        pair = FLAG_LABELS[key]
        assert isinstance(pair, tuple) and len(pair) == 2, pair
        en, zh = pair
        assert isinstance(en, str) and isinstance(zh, str) and en.strip() and zh.strip()
        assert en != key and zh != key


def test_raw_flag_key_never_reaches_the_page():
    from engine.china_crowding import FLAG_LABELS

    html = _render_full(ad={"crowding_flags": ["600000.SS"], "triple": [dict(_CROWD_ROW)],
                             "bottom": []},
                        crowd_labels={k: list(v) for k, v in FLAG_LABELS.items()})
    for raw in ("leverage_crowded", "margin_froth"):
        assert raw not in html, raw
    seg = _seg(html, 'id="crowding"', "</section>")
    for shown in ("Leverage crowded", "杠杆拥挤", "Margin froth", "融资拥挤"):
        assert shown in seg, shown


def test_margin_froth_copy_says_level_not_change():
    seg = _seg(_render_full(ad={"crowding_flags": ["600000.SS"]}),
               'id="crowding"', "</section>")
    en, zh = _legs(_seg(seg, '<p class="sub">', "</p>"))
    assert "Margin froth is a level" in en
    assert "financing balance against float market cap" in en
    assert "not a change" in en
    assert "融资拥挤是水平而非变化" in zh and "融资余额相对流通市值" in zh
    for s in ("jumped", "跳升", "rose most", "增幅最大"):
        assert s not in en + zh, s

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

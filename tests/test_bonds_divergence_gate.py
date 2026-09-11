"""Bonds Archetype-D round-1 gates: stale-date fail-closed + six-block skeleton.

Frozen spec: spec_bonds_regime_dashboard.md §0 G1/G2/G3, §3.
Run: python3 -m pytest tests/test_bonds_divergence_gate.py -q
"""
from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.build_bonds import (  # noqa: E402
    _agree_band,
    _changed_rows,
    _hero_pack,
    _series_last_obs,
    _watching,
    divergence_card_state,
)

TMPL = ROOT / "templates"


class SilentUndefined:
    """Degrade missing viewmodel fields so a skeleton render still compiles."""

    def __str__(self) -> str:
        return ""

    def __repr__(self) -> str:
        return ""

    def __html__(self) -> str:
        return ""

    def __call__(self, *a, **kw):
        return SilentUndefined()

    def __getattr__(self, name: str) -> "SilentUndefined":
        return SilentUndefined()

    def __getitem__(self, key):
        return SilentUndefined()

    def __iter__(self):
        return iter(())

    def __len__(self) -> int:
        return 0

    def __contains__(self, item) -> bool:
        return False

    def __bool__(self) -> bool:
        return False

    def __float__(self) -> float:
        return 0.0

    def __int__(self) -> int:
        return 0

    def __index__(self) -> int:
        return 0

    def __round__(self, *a):
        return 0

    def __lt__(self, other) -> bool:
        return False

    __le__ = __gt__ = __ge__ = __lt__

    def _op(self, *a, **kw):
        return SilentUndefined()

    __add__ = __radd__ = __sub__ = __rsub__ = _op
    __mul__ = __rmul__ = __truediv__ = __rtruediv__ = _op
    __floordiv__ = __rfloordiv__ = __mod__ = __rmod__ = _op
    __pow__ = __rpow__ = __neg__ = __pos__ = _op

    def get(self, *a, **kw):
        return SilentUndefined()

    def split(self, *a, **kw):
        return [""]


def _base_ctx(**overrides):
    """Minimal context that compiles the template and exercises the card."""
    from jinja2 import Undefined

    u = Undefined(name="u")
    ctx = {
        "C": {
            "blue": "#285FFF", "indigo": "#4559DC", "ink": "#0B1733",
            "text": "#344054", "muted": "#4C5A6C", "faint": "#5F6A7A",
            "red": "#D30B0B", "amber": "#F5AD42", "green": "#1a7f43",
            "grid": "#EAECF0", "card": "#FFFFFF", "bg": "#F7F8FA",
            "gold": "#C8A53B", "teal": "#1F8A70",
        },
        "as_of": "Sep 10, 2026",
        "as_of_zh": "2026年9月10日",
        "as_of_iso": "2026-09-10",
        "built": "2026-09-10 00:00 UTC",
        "span": "2014-01-01..2026-09-10",
        "vm": {
            "health": {
                "score": 88, "label": "healthy", "label_zh": "健康",
                "color": "#15764f", "phase_key": "late",
                "phase_en": "Late-cycle", "phase_zh": "周期晚段",
                "phase_color": "#8a5c00",
                "verdict_en": "ok", "verdict_zh": "ok",
                "recession_risk": 0.0, "drawdown_risk": 7.0,
                "calib": None, "stress_legs": [],
            },
            "curve": {
                "spread_10y3m": 0.88, "spread_2s10s": 0.4,
                "curve_tp_adj": 1.29, "ntfs": 0.75, "nyfed_prob": 13.2,
                "tax_en": "Bear flattener", "tax_zh": "熊市平坦",
                "tax_note_en": "short rates rising faster than long",
                "tax_note_zh": "短端快于长端",
                "tax_color": "#b3252a",
                "inverted": False, "tp_adj_inverted": False,
                "uninversion": False, "bull_steepener_uninversion": False,
            },
            "credit": {
                "hy_oas": 2.67, "ig_oas": 0.9, "hy_ig_ratio": 3.0,
                "baa_aaa": 0.8, "ebp": 0.4, "pctile": 20,
                "band_en": "tight", "band_zh": "偏紧", "band_color": "#15764f",
                "direction": None, "direction_zh": None,
            },
            "real": {
                "real_10y": 2.43, "real_5y": 1.8, "breakeven_10y": 2.3,
                "breakeven_5y5y": 2.2, "term_premium": 0.5, "tp_positive": False,
            },
            "stress": {
                "move": 80, "band_en": "calm", "band_zh": "平静",
                "color": "#15764f", "pctile": 30, "move_leads_vix": False,
                "sofr_iorb_bp": 5, "repo_spike_bp": 2,
                "reserve_scarcity": False, "repo_stress": False,
            },
            "cross": {
                "corr": -0.3, "regime_en": "Diversifying — bonds hedge",
                "regime_zh": "分散化 — 债券对冲", "color": "#15764f",
                "hedge_working": True,
            },
            "sovereign": {
                "euro_frag": 0.8, "bund_10y": 2.5,
                "frag_en": "Calm", "frag_zh": "平静", "frag_color": "#15764f",
                "frag_direction": None, "frag_direction_zh": "",
                "jgb_2s10s": 0.4, "jgb_en": "Flat", "jgb_zh": "平坦",
                "jgb_color": "#4C5A6C",
            },
            "alarms": [],
        },
        "charts": {k: "" for k in (
            "health", "curve_now", "spreads", "credit", "real", "move",
            "corr", "sovereign", "policy_path", "intl_yields", "tp_decomp",
            "xasset_betas")},
        "credit_cycle": None,
        "fed_path": None,
        "treasury_supply": None,
        "usd_link": None,
        "intl": None,
        "compass": None,
        "xasset": None,
        "xasset_vm": None,
        "timeline": [],
        "timeline_days": 120,
        "n_alerts": 0,
        "cc_vm": {
            "as_of": "2026-09-10",
            "hero": {
                "state_en": "Credit stress: low", "state_zh": "信用压力：低",
                "pill_en": "Watch — don't chase", "pill_zh": "观望 · 勿追",
                "pill_css": "stance-amber", "hero_cs": "cs-amber",
                "subtitle_en": "Company-bond stress is low.",
                "subtitle_zh": "整体压力仍低。",
            },
            "gauges": [], "themes": [],
            "watch": {"orcl": None, "fallen_angel_accruing": True,
                      "fallen_angel_candidates": [], "new_issuance_accruing": True},
            "finra": None, "maturity_wall": [],
            "divergence_ready": False,
            "divergence_ready_date": None,
            "divergence_last_obs": None,
        },
        "glance": [],
        "key_levels": [],
        "hero": {
            "word_en": "HEALTHY, LATE-CYCLE", "word_zh": "健康 · 周期晚段",
            "clause_en": "Bonds are healthy and the cycle is late: the curve is normal, credit is calm, rate swings are quiet.",
            "clause_zh": "债市健康、周期处于晚段：曲线正常，信用平静，利率波动温和。",
            "stance_en": "Watch — don't chase", "stance_zh": "观察，勿追",
            "stance_cls": "mx-stance-warn",
            "as_of": "Sep 10, 2026",
            "as_of_zh": "2026年9月10日",
            "caveat_en": ("Read the score with care: the recession-risk input is at the "
                          "bottom of its scale (0.0/100) — a rail, not a fine-grained measurement."),
            "caveat_zh": "读数注意：衰退风险分项已触及量表下限（0.0/100）——这是量表边界，并非精细测量。",
            "rec_band_en": None, "rec_band_zh": None, "rec_rail": True,
            "dd_band_en": "low", "dd_band_zh": "低", "dd_rail": False,
            "rec_score": 0.0, "dd_score": 7.0,
        },
        "changed": [],
        "watching": [],
        "div_card": divergence_card_state(False, None, None, "2026-09-10"),
        "n_tailwind": 6, "n_headwind": 5,
        "agree_en": "factors mostly agree", "agree_zh": "各因子多数一致",
        "active_section": "bonds", "active_page": "bonds",
        "u": u,
    }
    ctx.update(overrides)
    if "watching" not in overrides:
        ctx["watching"] = _watching(ctx.get("vm") or {})
    return ctx


def _render(**overrides) -> str:
    pytest.importorskip("jinja2")
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader(str(TMPL)), autoescape=True)
    tmpl = env.get_template("bonds.html.j2")
    return tmpl.render(**_base_ctx(**overrides))


def _card_html(html: str) -> str:
    m = re.search(
        r'<div class="card[^"]*"[^>]*data-card="stocks-vs-bonds"[\s\S]*?</div>\s*<div class="cc-foot-note"',
        html,
    )
    assert m, "stocks-vs-bonds card not found"
    return m.group(0)


# ---------------------------------------------------------------------------
# G3 — stale-date gate (frozen clock)
# ---------------------------------------------------------------------------

AS_OF = "2026-09-10"


def test_divergence_state_function_fail_closed():
    """Producer helper: only a strictly-future ready_date is BUILDING."""
    assert divergence_card_state(True, "2026-12-01", None, AS_OF)["state"] == "ready"
    b = divergence_card_state(False, "2026-12-01", None, AS_OF)
    assert b["state"] == "building"
    assert b["ready_date"] == "01 Dec 2026"
    d = divergence_card_state(False, "2026-08-14", None, AS_OF)
    assert d["state"] == "delayed"
    assert d["ready_date"] is None
    eq = divergence_card_state(False, AS_OF, None, AS_OF)
    assert eq["state"] == "delayed"
    for bad in (None, "", "not-a-date", "14 Aug 2026"):
        s = divergence_card_state(False, bad, None, AS_OF)
        assert s["state"] == "delayed", bad


def test_g3_future_ready_date_is_building():
    """Case 1: ready_date in the future → BUILDING; date from the variable."""
    dc = divergence_card_state(False, "2026-12-01", None, AS_OF)
    html = _render(div_card=dc, as_of_iso=AS_OF)
    card = _card_html(html)
    assert "History building · read opens 01 Dec 2026" in card
    assert "数据积累中 · 01 Dec 2026 起可查看" in card
    assert "14 Aug 2026" not in card
    assert "check back" not in card


def test_g3_past_ready_date_is_delayed():
    """Case 2: ready_date in the past AND last_obs < as_of → dated DELAYED."""
    dc = divergence_card_state(False, "2026-08-14", "2026-08-01", AS_OF)
    html = _render(div_card=dc, as_of_iso=AS_OF)
    card = _card_html(html)
    assert dc["cause"] == "stale"
    assert "Data delayed since 01 Aug 2026" in card
    assert "building" not in card.lower()
    assert "数据积累中" not in card
    assert "The daily series has not updated" in card
    assert "daily price feed" not in card.lower()
    assert "isn't live yet" not in card


def test_g3_equal_date_is_delayed():
    """Case 3: ready_date == as_of → DELAYED (fail-closed on the boundary)."""
    dc = divergence_card_state(False, AS_OF, None, AS_OF)
    html = _render(div_card=dc, as_of_iso=AS_OF)
    card = _card_html(html)
    assert "Data delayed" in card
    assert "building" not in card.lower()
    assert "数据积累中" not in card


def test_g3_missing_unparseable_does_not_raise():
    """Case 4: ready_date absent / None / unparseable → DELAYED, no raise."""
    for bad in (None, "", "nope", "14 Aug 2026"):
        dc = divergence_card_state(False, bad, None, AS_OF)
        html = _render(div_card=dc, as_of_iso=AS_OF)
        card = _card_html(html)
        assert "Data delayed — awaiting the daily series" in card
        assert "building" not in card.lower()


_DATE_RE = re.compile(
    r"\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+20\d{2}"
    r"|20\d{2}-\d{2}-\d{2}"
    r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+20\d{2})\b",
    re.I,
)


def _parse_date(s: str) -> date:
    from datetime import datetime
    for fmt in ("%d %b %Y", "%Y-%m-%d", "%b %d, %Y", "%d %B %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise AssertionError(f"unparseable date {s!r}")


@pytest.mark.parametrize("ready_date,last_obs", [
    ("2026-12-01", None),
    ("2026-08-14", "2026-08-01"),
    (AS_OF, None),
    (None, None),
    (None, AS_OF),
    ("2026-08-14", AS_OF),
    (None, "2026-09-11"),
])
def test_g3_property_no_past_or_future_leak(ready_date, last_obs):
    """Case 5: DELAYED never prints a date on or after as_of; last_obs==as_of is unbuilt."""
    dc = divergence_card_state(False, ready_date, last_obs, AS_OF)
    html = _render(div_card=dc, as_of_iso=AS_OF)
    card = _card_html(html)
    as_of_d = date(2026, 9, 10)
    building = "History building" in card
    lo = None
    if last_obs:
        try:
            lo = date.fromisoformat(last_obs)
        except ValueError:
            lo = None
    if not building:
        assert "delayed since today" not in card.lower()
        if lo is None or lo >= as_of_d:
            assert "Data delayed since" not in card
        else:
            assert "Data delayed since" in card
            assert dc["cause"] == "stale"
    for raw in _DATE_RE.findall(card):
        d = _parse_date(raw if isinstance(raw, str) else raw[0])
        if building:
            continue
        assert d < as_of_d, f"DELAYED card leaked date {raw} >= as_of {as_of_d}"


# Pre-fix template bytes (origin/main before this packet). Inline so the
# positive control cannot shell out to `git show origin/main` — after squash-
# merge origin/main IS this template, and blobless/offline checkouts have no
# object. Never git-show a live ref from a gate test.
_OLD_TEMPLATE_STOCKS_VS_BONDS = """
  <div class="card cs-card cs-neutral">
    <h2>{{ t('Stocks vs their bonds', '股票与其债券') }}</h2>
    <p class="cc-verdict-lead">
      <span class="l-en">The divergence read builds after ~1 month of daily history — the risk sign is stocks rising while their bonds weaken.</span><span class="l-zh">该背离指标需约1个月的日度数据积累——风险信号为股价上涨而债券走弱。</span>
    </p>
    <span class="faint" style="font-size:12px;display:block;margin-top:8px">
      <span class="l-en">History building · check back 14 Aug 2026</span><span class="l-zh">数据积累中 · 2026年8月14日后可查看</span>
    </span>
  </div>
"""


def test_g3_old_template_had_the_literal():
    """Positive control: the pre-fix template contained the hardcoded date."""
    assert "check back 14 Aug 2026" in _OLD_TEMPLATE_STOCKS_VS_BONDS
    new = (TMPL / "bonds.html.j2").read_text()
    assert "check back 14 Aug 2026" not in new


# ---------------------------------------------------------------------------
# G1 — six L1 blocks in order
# ---------------------------------------------------------------------------

def test_g1_six_l1_blocks_in_order():
    html = _render()
    found = re.findall(r'data-l1="([a-z-]+)"', html)
    assert found == ["hero", "changed", "drivers", "world", "watching", "deeper"], found


def test_g1_driver_panel_count_le_4():
    html = _render()
    m = re.search(r'data-l1="drivers"[\s\S]*?data-l1="world"', html)
    assert m
    n = len(re.findall(r'<div class="panel"', m.group(0)))
    assert n <= 4, n
    assert n == 4


def test_g1_deeper_named_landings():
    html = _render()
    m = re.search(r'data-l1="deeper"[\s\S]*?</section>', html)
    assert m
    block = m.group(0)
    for en in (
        "Corporate bond desk",
        "Rates &amp; curve detail",
        "Fed path &amp; policy",
        "Global rates &amp; sovereign detail",
        "Bonds → each market",
        "Treasury supply &amp; absorption",
        "State changes · last 120 days",
        "How to read this page",
    ):
        assert en in block, en
    assert 'href="transmission.html"' in block
    assert 'href="#corpcredit"' in block
    assert 'href="#rates-curve"' in block
    assert 'href="#fed-path"' in block
    assert 'href="#global-detail"' in block
    assert 'href="#supply"' in block
    assert 'href="#timeline"' in block
    assert 'href="#how-to-read"' in block


# ---------------------------------------------------------------------------
# G2 — copy-tier
# ---------------------------------------------------------------------------

def test_g2_banned_visible_strings():
    html = _render()
    src = (TMPL / "bonds.html.j2").read_text()
    assert "check back 14 Aug 2026" not in html
    assert "check back 14 Aug 2026" not in src
    # Column rename
    assert "vs 1-yr normal" in src
    assert "对比一年常态" in src
    assert re.search(r">1y z<", src) is None
    assert "1年z" not in src
    # Compass acronym gone from labels
    assert "(TSMOM)" not in src
    # Betas glossed
    assert 'class="l-en">Betas' not in html
    assert "These numbers show how much each market typically moves" in src
    # title= conversions
    assert 'title="forward-drawdown' not in src
    assert 'title="Long-Treasury' not in src
    assert re.search(r'title="[^"]*[一-鿿]', src) is None
    # converted hosts use data-tip pair
    assert "data-tip-en=" in src and "data-tip-zh=" in src


def test_g2_no_bare_r_in_transmission_rows():
    html = _render()
    src = (TMPL / "bonds.html.j2").read_text()
    # Spec §2.9: grep -nE '>r *=?[ <]|>ρ' — a loop variable `r.date` is not a coefficient.
    assert re.search(r">r *=?[ <]|>ρ", src) is None
    assert "r&nbsp;" not in src
    assert "co-movement" in src
    assert "联动度" in src
    assert html  # render must succeed with the glossed template


def _intl(*, direction="rising", avg=4.05, premium_direction="rising",
          em_direction="stable"):
    return {
        "global": {"avg_10y": avg, "direction": direction, "avg_10y_chg_63d_bp": 18},
        "us_vs_world": {"us_premium_bp": 42, "premium_direction": premium_direction},
        "em": {"em_oas": 2.9, "pctile": 35, "emb_trend": "down", "direction": em_direction},
        "countries": [],
    }


def _world_en_subtitle(html: str) -> str:
    m = re.search(
        r'data-l1="world"[\s\S]*?<p class="drv-read"><b>([\s\S]*?)</b></p>',
        html,
    )
    assert m, "world subtitle not found"
    en = re.search(r'class="l-en">(.*?)</span>', m.group(1))
    assert en, m.group(1)
    return re.sub(r"<[^>]+>", "", en.group(1))


def _en_word_count(s: str) -> int:
    return len(s.replace("—", " ").split())


def test_g2_subtitle_word_count():
    """Tier-1 world + transmission subtitles are ≤14 EN words on a rendered VM."""
    rising = _world_en_subtitle(_render(intl=_intl(direction="rising")))
    falling = _world_en_subtitle(_render(intl=_intl(direction="falling")))
    stable = _world_en_subtitle(_render(intl=_intl(direction="stable")))
    unread = _world_en_subtitle(_render(intl=_intl(direction=None)))
    assert _en_word_count(rising) <= 14, rising
    assert _en_word_count(falling) <= 14, falling
    assert _en_word_count(stable) <= 14, stable
    assert _en_word_count(unread) <= 14, unread
    src = (TMPL / "bonds.html.j2").read_text()
    assert "a tailwind for" in src
    en6 = "Bonds are a tailwind for 6 markets and a headwind for 5."
    assert _en_word_count(en6) == 12


def test_world_subtitle_follows_global_direction():
    """B1: conclusion words bind to g.direction; a hardcoded tightening fails."""
    src = (TMPL / "bonds.html.j2").read_text()
    assert "the world is tightening" not in src
    assert "且持续上行——全球融资成本在收紧" not in src
    rising = _render(intl=_intl(direction="rising"))
    falling = _render(intl=_intl(direction="falling"))
    stable = _render(intl=_intl(direction="stable"))
    unread = _render(intl=_intl(direction=None))
    assert "the world is tightening" in rising
    assert "全球融资成本在收紧" in rising
    assert "且持续上行" in rising
    assert "the world is easing" in falling
    assert "全球融资成本在放松" in falling
    assert "且持续下行" in falling
    assert "the world is tightening" not in falling
    assert "且持续上行" not in falling
    assert "the world is steady" in stable
    assert "全球融资成本持稳" in stable
    assert "world direction still reading" in unread
    assert "全球方向仍在读数" in unread
    # M1: lens tip binds intl.em.direction / uw.premium_direction
    assert "the gap is widening" in rising
    assert "the gap is narrowing" in _render(
        intl=_intl(direction="falling", premium_direction="falling"))
    assert "(stable)" in rising
    assert "(widening)" in _render(intl=_intl(em_direction="rising"))


def test_g2_watch_foot_and_empty_changed():
    html = _render()
    assert "Windows, not certainties — re-drawn nightly." in html
    assert "是窗口，不是定论——每晚重新校准。" in html
    assert "No state changes in the last 120 days — the bond regime has been steady." in html


def _pack_vm(**overrides) -> dict:
    vm = {
        "health": {
            "score": 88, "label": "healthy", "label_zh": "健康",
            "phase_en": "Late-cycle", "phase_zh": "周期晚段",
            "recession_risk": 7.0, "drawdown_risk": 7.0,
        },
        "curve": {"spread_2s10s": 0.4, "inverted": False, "tp_adj_inverted": False},
        "credit": {"band_en": "tight"},
        "stress": {"band_en": "calm"},
        "alarms": [],
    }
    for k, v in overrides.items():
        if isinstance(v, dict) and isinstance(vm.get(k), dict):
            vm[k] = {**vm[k], **v}
        else:
            vm[k] = v
    return vm


def test_watching_uninverted_stressed_has_no_inverted_or_calm_premise():
    """M2: un-inverted curve + stressed credit must not claim still-inverted / calm."""
    rows = _watching(_pack_vm(
        curve={"inverted": False, "tp_adj_inverted": False},
        credit={"band_en": "distress"},
    ))
    blob = " ".join(
        f"{r['cond_en']} {r['then_en']} {r['cond_zh']} {r['then_zh']}" for r in rows
    ).lower()
    assert "still inverted" not in blob
    assert "un-invert" not in blob
    assert "解除倒挂" not in blob
    assert "credit calm" not in blob
    assert "from calm" not in blob
    assert "从平静" not in blob


def test_watching_unknown_is_cautious():
    rows = _watching({"curve": {}, "credit": {}, "cross": {}})
    blob = " ".join(r["cond_en"].lower() for r in rows)
    assert "un-invert" not in blob
    assert "from calm" not in blob
    assert "not assume" in blob or "leaves its current band" in blob


def test_uninversion_row_is_not_ignore():
    """M3: alarm-grade uninversion must not say Ignore — already reflected."""
    rows = _changed_rows([{
        "day": "2026-09-01",
        "events": [{
            "type": "uninversion",
            "ts": "2026-09-01",
            "headline": "Curve un-inverted",
            "headline_zh": "曲线解除倒挂",
            "label": "Curve",
            "label_zh": "曲线",
        }],
    }])
    assert rows
    assert rows[0]["stance_en"] != "Ignore — already reflected"
    assert rows[0]["stance_en"] == "Protect gains"
    assert rows[0]["stance_zh"] == "保护收益"


def test_rail_caveat_floor_vs_ceiling():
    """M4: 0.0 is the floor; 100.0 is the ceiling with the true value."""
    h0 = _hero_pack(_pack_vm(health={"recession_risk": 0.0}), "Sep 10, 2026", "late")
    assert h0["caveat_en"]
    assert "bottom" in h0["caveat_en"]
    assert "0.0/100" in h0["caveat_en"]
    assert "top" not in h0["caveat_en"]
    assert "下限" in h0["caveat_zh"]
    h100 = _hero_pack(_pack_vm(health={"recession_risk": 100.0}), "Sep 10, 2026", "late")
    assert h100["caveat_en"]
    assert "top" in h100["caveat_en"]
    assert "100.0/100" in h100["caveat_en"]
    assert "bottom" not in h100["caveat_en"]
    assert "上限" in h100["caveat_zh"]
    assert h100["rec_rail"] is True
    assert h100["rec_band_en"] is None


def test_missing_2s10s_is_not_flat():
    """M5: absent 2s10s must not coerce to a 'flat' shape claim."""
    h = _hero_pack(_pack_vm(curve={
        "spread_2s10s": None, "inverted": False, "tp_adj_inverted": False,
    }), "Sep 10, 2026", "late")
    assert "flat" not in h["clause_en"]
    assert "平坦" not in h["clause_zh"]
    assert "unresolved" not in h["clause_en"]
    assert "shape is not readable yet" in h["clause_en"]
    assert "形态尚不可读" in h["clause_zh"]


def test_delayed_card_three_true_causes():
    """R1: DELAYED copy states only the true cause. last_obs==as_of is unbuilt."""
    stale = divergence_card_state(False, None, "2026-08-01", AS_OF)
    assert stale["state"] == "delayed"
    assert stale["cause"] == "stale"
    assert stale["last_obs"] == "01 Aug 2026"
    stale_card = _card_html(_render(div_card=stale, as_of_iso=AS_OF))
    assert "Data delayed since 01 Aug 2026" in stale_card
    assert "数据自 01 Aug 2026 起未更新" in stale_card
    assert "The daily series has not updated" in stale_card
    assert "isn't live yet" not in stale_card
    assert "awaiting the daily series" not in stale_card
    assert "daily price feed" not in stale_card.lower()

    current = divergence_card_state(False, None, AS_OF, AS_OF)
    assert current["state"] == "delayed"
    assert current["cause"] == "unbuilt"
    assert current["last_obs"] is None
    current_card = _card_html(_render(div_card=current, as_of_iso=AS_OF))
    assert "This read isn't live yet — the comparison engine hasn't produced it" in current_card
    assert "该读数尚未上线——比较引擎尚未产出" in current_card
    assert "Data delayed since" not in current_card
    assert "delayed since today" not in current_card.lower()
    assert "has not updated" not in current_card
    assert "daily price feed" not in current_card.lower()
    assert "awaiting the daily series" not in current_card

    ahead = divergence_card_state(False, "2026-08-14", "2026-09-11", AS_OF)
    assert ahead["cause"] == "unbuilt"
    assert ahead["last_obs"] is None
    ahead_card = _card_html(_render(div_card=ahead, as_of_iso=AS_OF))
    assert "This read isn't live yet" in ahead_card
    assert "Data delayed since" not in ahead_card

    missing = divergence_card_state(False, None, None, AS_OF)
    assert missing["state"] == "delayed"
    assert missing["cause"] == "awaiting"
    assert missing["last_obs"] is None
    missing_card = _card_html(_render(div_card=missing, as_of_iso=AS_OF))
    assert "Data delayed — awaiting the daily series" in missing_card
    assert "数据延迟——等待日度序列" in missing_card
    assert "Data delayed since" not in missing_card
    assert "isn't live yet" not in missing_card


def test_base_ctx_watching_follows_producer():
    """r3 minor: fixture watching is _watching(vm), not a leftover inverted premise."""
    ctx = _base_ctx()
    assert ctx["watching"] == _watching(ctx["vm"])
    blob = " ".join(r["cond_en"] for r in ctx["watching"]).lower()
    assert "un-invert" not in blob
    assert "inverts again" in blob


def test_series_last_obs_from_theme_daily(tmp_path):
    """M6: last_obs is the newest as_of on the series the producer already loads."""
    cm = tmp_path / "corp_bonds" / "credit_momentum.json"
    series = cm.parent / "series"
    series.mkdir(parents=True)
    cm.write_text("{}")
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame({
        "as_of": ["2026-07-10", "2026-08-03", "2026-07-20"],
        "theme": ["hyperscaler_credit"] * 3,
        "g_spread_bp_pw": [80.0, 82.0, 81.0],
    })
    df.to_parquet(series / "theme_daily.parquet")
    assert _series_last_obs(cm) == "2026-08-03"
    assert _series_last_obs(None) is None
    missing = tmp_path / "empty" / "credit_momentum.json"
    missing.parent.mkdir()
    missing.write_text("{}")
    assert _series_last_obs(missing) is None


def test_tz_aware_ready_date_does_not_raise():
    """m1: tz-aware ready_date compares; never TypeError."""
    future = divergence_card_state(
        False, "2026-12-01T00:00:00+00:00", None, "2026-09-10")
    assert future["state"] == "building"
    past = divergence_card_state(
        False, "2026-08-01T00:00:00+00:00", None, "2026-09-10")
    assert past["state"] == "delayed"


def test_agree_band_guards_bad_input():
    """m2: unparseable agreement degrades; does not ValueError the build."""
    assert _agree_band(None)[0] == "factors are split"
    assert _agree_band("nope")[0] == "factors are split"
    assert _agree_band(object())[0] == "factors are split"
    assert _agree_band(0.9)[0] == "factors strongly agree"

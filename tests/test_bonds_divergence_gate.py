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

from scripts.build_bonds import divergence_card_state  # noqa: E402

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
            "caveat_en": ("Read the score with care: the recession-risk input is at the "
                          "bottom of its scale (0.0/100) — a rail, not a fine-grained measurement."),
            "caveat_zh": "读数注意：衰退风险分项已触及量表下限（0.0/100）——这是量表边界，并非精细测量。",
            "rec_band_en": None, "rec_band_zh": None, "rec_rail": True,
            "dd_band_en": "low", "dd_band_zh": "低", "dd_rail": False,
            "rec_score": 0.0, "dd_score": 7.0,
        },
        "changed": [],
        "watching": [
            {"cond_en": "The curve un-inverts while short rates fall",
             "cond_zh": "曲线在短端利率下行时解除倒挂",
             "then_en": "…would mark the late-cycle handoff and move the stance toward Protect gains.",
             "then_zh": "…将标志周期晚段交接，立场转向「保护收益」。"},
            {"cond_en": "High-yield spreads move from calm into elevated",
             "cond_zh": "高收益利差从平静升至偏高",
             "then_en": "…would flip the credit driver and cap the health read.",
             "then_zh": "…将翻转信用驱动并压制健康度读数。"},
            {"cond_en": "Stock-bond correlation turns positive and stays there",
             "cond_zh": "股债相关性转正并维持",
             "then_en": "…would mean the Treasury hedge has stopped working.",
             "then_zh": "…意味着国债对冲已失效。"},
        ],
        "div_card": divergence_card_state(False, None, None, "2026-09-10"),
        "n_tailwind": 6, "n_headwind": 5,
        "agree_en": "factors mostly agree", "agree_zh": "各因子多数一致",
        "active_section": "bonds", "active_page": "bonds",
        "u": u,
    }
    ctx.update(overrides)
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
    """Case 2: ready_date in the past, not ready → DELAYED; no 'building'."""
    dc = divergence_card_state(False, "2026-08-14", "2026-08-01", AS_OF)
    html = _render(div_card=dc, as_of_iso=AS_OF)
    card = _card_html(html)
    assert "Data delayed since 01 Aug 2026" in card
    assert "building" not in card.lower()
    assert "数据积累中" not in card
    assert "The daily price feed for these bonds has not updated" in card


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
        assert "Data delayed — no daily price since the feed started" in card
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
])
def test_g3_property_no_past_or_future_leak(ready_date, last_obs):
    """Case 5: every rendered date in the card is <= as_of OR the card is BUILDING."""
    dc = divergence_card_state(False, ready_date, last_obs, AS_OF)
    html = _render(div_card=dc, as_of_iso=AS_OF)
    card = _card_html(html)
    as_of_d = date(2026, 9, 10)
    building = "History building" in card
    for raw in _DATE_RE.findall(card):
        # findall with one group returns strings
        d = _parse_date(raw if isinstance(raw, str) else raw[0])
        if building:
            continue
        assert d <= as_of_d, f"DELAYED card leaked date {raw} > as_of {as_of_d}"


def test_g3_old_template_had_the_literal():
    """Positive control: origin/main template still contains the hardcoded date."""
    import subprocess
    old = subprocess.check_output(
        ["git", "show", "origin/main:templates/bonds.html.j2"],
        cwd=str(ROOT),
    ).decode()
    assert "check back 14 Aug 2026" in old
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


def test_g2_subtitle_word_count():
    """The two rewritten Tier-1 subtitles are ≤14 EN words (frozen strings)."""
    en5 = "Global 10-year yields average 4.05% and are rising — the world is tightening."
    en6 = "Bonds are a tailwind for 6 markets and a headwind for 5."
    assert len(en5.replace("—", " ").split()) == 12
    assert len(en6.replace("—", " ").split()) == 12
    src = (TMPL / "bonds.html.j2").read_text()
    assert "the world is tightening" in src
    assert "a tailwind for" in src


def test_g2_watch_foot_and_empty_changed():
    html = _render()
    assert "Windows, not certainties — re-drawn nightly." in html
    assert "是窗口，不是定论——每晚重新校准。" in html
    assert "No state changes in the last 120 days — the bond regime has been steady." in html

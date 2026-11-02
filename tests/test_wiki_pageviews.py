"""Tests for the DISPLAY-ONLY offshore-attention chip (P2): the wiki_pageviews
collector parse + title map, the abnormal-attention z compute, the display-only
invariant (never scored), and the bilingual discovery chip with the CN/HK caveat.
Synthetic fixtures, no network. See research/WIKI_ATTENTION_CHIP_SPEC.md."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collectors import wiki_pageviews as wp  # noqa: E402
from engine import i18n  # noqa: E402
from scripts import build_site as bs  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"


# ---- 1. collector parse ------------------------------------------------------
def test_parse_shape():
    payload = {"items": [
        {"timestamp": "2026050100", "article": "Apple_Inc.", "views": 6966},
        {"timestamp": "2026050200", "article": "Apple_Inc.", "views": 6327},
    ]}
    df = wp._parse(payload)
    assert list(df.columns) == ["views", "log_views"]     # 2-col -> dodges outlier guard
    assert isinstance(df.index, pd.DatetimeIndex) and df.index.is_monotonic_increasing
    assert pd.api.types.is_numeric_dtype(df["views"])
    assert df["views"].iloc[0] == 6966
    # the adapter's validate() accepts it
    out = wp.WikiPageviewsAdapter().validate("AAPL", df)
    assert not out.empty and "views" in out.columns
    assert wp._parse({"items": []}).empty


# ---- 2. ticker->title map + empty-run guard ----------------------------------
def test_ticker_titles_skips_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(wp.config, "data_dir", lambda: tmp_path)
    pdir = tmp_path / "profile"
    pdir.mkdir()
    # no wiki_title column at all -> empty map, no exception
    pd.DataFrame({"name": ["Apple"]}, index=["AAPL"]).to_parquet(pdir / "profiles.parquet")
    assert wp._ticker_titles() == {}
    # some titles present, some NaN -> only the resolved ones returned
    pd.DataFrame({"wiki_title": ["Apple_Inc.", None, "Nvidia"]},
                 index=["AAPL", "ZZZ", "NVDA"]).to_parquet(pdir / "profiles.parquet")
    assert wp._ticker_titles() == {"AAPL": "Apple_Inc.", "NVDA": "Nvidia"}


def test_fetch_raises_when_no_titles(monkeypatch):
    monkeypatch.setattr(wp, "_ticker_titles", lambda: {})
    with pytest.raises(ValueError):
        wp.WikiPageviewsAdapter().fetch()


# ---- 3. chip compute / shape -------------------------------------------------
def test_attention_z_and_build(tmp_path, monkeypatch):
    monkeypatch.setattr(bs.config, "data_dir", lambda: tmp_path)
    adir = tmp_path / "attention"
    adir.mkdir()
    idx = pd.bdate_range("2025-11-01", periods=120)
    rng = np.random.default_rng(0)
    spike = pd.Series(1000.0 + rng.normal(0, 20, 120), index=idx)
    spike.iloc[-3:] = 5000.0                               # viral -> high z
    quiet = pd.Series(800.0 + rng.normal(0, 15, 120), index=idx)   # no abnormal attention
    for tk, v in (("LOUD", spike), ("QUIET", quiet)):
        pd.DataFrame({"views": v, "log_views": np.log1p(v)}).to_parquet(adir / f"{tk}.parquet")
    # _attention_z is causal + clipped
    z_loud = bs._attention_z(spike)
    z_quiet = bs._attention_z(quiet)
    assert z_loud is not None and 0 <= z_loud <= 6.0       # clip bound
    assert z_loud > 2.0 and abs(z_quiet) < 2.0
    # build_attention_data writes the json with the right shape
    out = bs.build_attention_data(tmp_path / "site")
    assert set(out["LOUD"]) == {"z", "views", "asof"}
    assert out["LOUD"]["z"] == round(z_loud, 2)
    assert isinstance(out["LOUD"]["views"], int)


# ---- 4. display-only invariant (critical guard) ------------------------------
def test_never_scored():
    for f in ("engine/axes.py", "engine/setups.py", "engine/residual_alpha.py",
              "engine/regime.py"):
        src = (ROOT / f).read_text()
        for tok in ("attention", "wiki_pageviews", "attn_z"):
            assert tok not in src, f"{tok} leaked into {f}"


# ---- 5. bilingual discovery chip + CN/HK caveat ------------------------------
# Renders main's actual discovery `conv(r)` macro (the already-merged `.cchip.attn`
# offshore-attention chip that consumes the attention.json this port produces).
def _render_attn_chip(r):
    from jinja2 import Environment, FileSystemLoader
    src = (TEMPLATES / "discovery.html.j2").read_text()
    pre = src[: src.index("<!DOCTYPE")]                    # t()/help()/conv() macros
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=True)
    env.globals.update(td=i18n.td, tr=i18n.tr, LEG_LBL={}, tilt_legs=[], attn_threshold=2.0)
    row = {"legs": {}, "ins_buyers": 0, "val_label": None, **r}
    return env.from_string(pre + "{{ conv(r) }}").render(r=row)


def test_chip_bilingual_us():
    html = _render_attn_chip({"ticker": "AAPL", "attn_z": 2.5})
    assert "l-en" in html and "l-zh" in html              # both language spans emitted
    assert "👁" in html and "+2.5σ" in html
    assert "short-horizon reversal" in html and "短期反转" in html
    assert "cchip attn" in html                           # the display-only caution idiom
    assert "intl only" not in html and "仅境外" not in html  # US ticker -> no CN/HK caveat


def test_chip_cnhk_caveat():
    html = _render_attn_chip({"ticker": "600519.SS", "attn_z": 2.5})
    assert "intl only" in html and "仅境外" in html        # CN/HK -> international-attention-only caveat


def test_chip_absent_below_threshold():
    assert "cchip attn" not in _render_attn_chip({"ticker": "AAPL", "attn_z": 1.2})
    assert "cchip attn" not in _render_attn_chip({"ticker": "AAPL", "attn_z": None})


# ---- 6. W19-F: insider SELL cluster / cross age / alpha-only score note ---------
# Specs 1-3: display wiring for fields the committed artifacts already carry
# (insider_signals.json sellers + net_mn, signal_gate verdict ticks, n_legs).
# Synthetic rows only — no data/ or site/ reads.
_W19F_ROW = {"ticker": "AAPL", "name": "Apple Inc", "sector": "Technology", "price": 100.0,
             "top_score": 1.0, "band": "strong", "alpha": 1.0, "n_legs": 5, "legs": {},
             "entry_en": "In trend", "entry_zh": "趋势中", "entry_css": "", "grade": "na",
             "sig_tier": None, "sig_en": None, "sig_zh": None, "sig_css": "", "sig_ticks": None,
             "sig_btc": None, "sig_prov": False, "sector_rank": None, "sector_n": None,
             "ins_buyers": 0, "ins_bps": None, "ins_sellers": 0, "ins_net_mn": None,
             "attn_z": None, "val_label": None}


def _w19f_render(call, **r):
    from jinja2 import Environment, FileSystemLoader
    src = (TEMPLATES / "discovery.html.j2").read_text()
    pre = src[: src.index("<!DOCTYPE")]        # the t()/conv()/signal()/trow()/srow() macros
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=True)
    env.globals.update(td=i18n.td, tr=i18n.tr, LEG_LBL={}, tilt_legs=[], attn_threshold=2.0)
    return env.from_string(pre + call).render(r={**_W19F_ROW, **r})


def _w19f_t1(**over):
    d = {"sig_tier": "T1", "sig_en": "Buy zone", "sig_zh": "买入区",
         "sig_css": "sg-confirmed", "sig_ticks": 0}
    d.update(over)
    return d


def _w19f_t2(**over):
    d = {"sig_tier": "T2", "sig_en": "early✓", "sig_zh": "早期✓",
         "sig_css": "sg-early-confirmed", "sig_ticks": 2}
    d.update(over)
    return d


# ---- Spec 1: the Form-4 sell cluster ---------------------------------------
def test_w19f_sell_chip_nhc_shape():
    """Committed NHC: buyers 1, bps -24.0, sellers 9, net_mn -8.74 — a SELL cluster."""
    html = _w19f_render("{{ conv(r) }}", ins_buyers=1, ins_bps=-24.0,
                        ins_sellers=9, ins_net_mn=-8.74)
    assert "cchip down" in html                 # reuses the existing down idiom
    assert "9 sellers" in html and "9 名卖出" in html
    assert "-$8.7M" in html
    # the tip repeats the same two facts and never invents a reason
    assert "window, net -$8.7M. Counts and dollars only" in html
    assert "，净卖出 $8.7M。仅统计人数与金额" in html
    assert "$$" not in html
    assert "👤" not in html                     # buyers=1 is not a buy cluster


def test_w19f_sell_chip_etsy_shape():
    """Committed ETSY: buyers 0, bps -89.2, sellers 8, net_mn -68.61."""
    html = _w19f_render("{{ conv(r) }}", ins_buyers=0, ins_bps=-89.2,
                        ins_sellers=8, ins_net_mn=-68.61)
    assert "8 sellers" in html and "8 名卖出" in html
    assert "-$68.6M" in html
    assert "6-month" in html and "6个月" in html
    assert "window, net -$68.6M." in html and "，净卖出 $68.6M。" in html


def test_w19f_sell_chip_absent_cases():
    # (i) committed EFOR is a BUY cluster (12 buyers, bps +11.6): no sell chip, chip intact.
    efor = _w19f_render("{{ conv(r) }}", ins_buyers=12, ins_bps=11.6,
                        ins_sellers=0, ins_net_mn=1.86)
    assert "👤12" in efor and "sellers" not in efor
    # (ii) sellers with a positive bps is not a sell cluster.
    assert "sellers" not in _w19f_render("{{ conv(r) }}", ins_sellers=5, ins_bps=3.0)
    # (iii) one seller is below the >= 2 cluster floor.
    assert "sellers" not in _w19f_render("{{ conv(r) }}", ins_sellers=1, ins_bps=-5.0)
    # (iv) heads without a net figure still print, and no dollars appear.
    nonet = _w19f_render("{{ conv(r) }}", ins_sellers=3, ins_bps=-5.0, ins_net_mn=None)
    assert "3 sellers" in nonet and "$" not in nonet


def test_w19f_row_carries_sell_fields():
    """The chip is dead copy unless _row passes the two committed fields through."""
    import inspect

    from scripts import build_discovery as bd
    src = inspect.getsource(bd.main)
    assert '"ins_sellers": ins.get("sellers")' in src
    assert '"ins_net_mn": _clean(ins.get("net_mn"))' in src


# ---- Spec 2: how many bars ago the confluence cross fired -------------------
def test_w19f_cross_age_t1_just_fired():
    html = _w19f_render("{{ signal(r) }}", **_w19f_t1(sig_ticks=0))
    assert "just fired" in html and "刚刚触发" in html


def test_w19f_cross_age_t2_bars():
    html = _w19f_render("{{ signal(r) }}", **_w19f_t2(sig_ticks=2))
    assert "fired 2 bars ago" in html and "2 根K线前触发" in html
    one = _w19f_render("{{ signal(r) }}", **_w19f_t2(sig_ticks=1))
    assert "fired 1 bar ago" in one and "1 根K线前触发" in one
    assert "fired 1 bars" not in one


def test_w19f_cross_age_absent_cases():
    # (i) no fresh cross -> the muted dash carries no age.
    dash = _w19f_render("{{ signal(r) }}", sig_ticks=0)
    assert "just fired" not in dash and "sg-none" in dash
    # (ii) a T2 verdict with no ticks number prints no age, never "None bars ago".
    noage = _w19f_render("{{ signal(r) }}", **_w19f_t2(sig_ticks=None))
    assert "bars ago" not in noage and "just fired" not in noage
    # (iii) T3 has NOT fired: it keeps the forward ~Nd estimate, never a back-looking age.
    t3 = _w19f_render("{{ signal(r) }}", sig_tier="T3", sig_en="Watch", sig_zh="观察",
                      sig_css="sg-imminent", sig_ticks=1, sig_btc=2)
    assert "~2d" in t3
    assert "bar ago" not in t3 and "bars ago" not in t3 and "just fired" not in t3


# ---- Spec 3: alpha-only disclosure when the confirming legs are missing -----
def test_w19f_alpha_only_note_tph_shape():
    """Committed TPH: n_legs 0 -> MIN_TILT_LEGS zeroes conviction, so +1.38 is alpha alone."""
    row = dict(ticker="TPH", top_score=1.38, alpha=2.3, n_legs=0)
    trow_html = _w19f_render("{{ trow(r, 10) }}", **row)
    assert "+1.38" in trow_html
    assert "α only" in trow_html and "仅阿尔法" in trow_html
    srow_html = _w19f_render("{{ srow(r) }}", **row)
    assert "α only" in srow_html and "仅阿尔法" in srow_html


def test_w19f_alpha_only_note_absent():
    for call in ("{{ trow(r, 10) }}", "{{ srow(r) }}"):
        for n_legs in (2, 5, None):
            assert "α only" not in _w19f_render(call, n_legs=n_legs), (call, n_legs)


def test_w19f_sell_chip_dollars_sign_and_body():
    # The visible chip body carries the signed dollars (distinct from the tip's "net -$8.7M").
    nhc = _w19f_render("{{ conv(r) }}", ins_buyers=0, ins_bps=-24.0,
                       ins_sellers=9, ins_net_mn=-8.7)
    assert "名卖出</span> -$8.7M</span>" in nhc
    # A positive net is not a net sale: heads still print, no dollars and no "net" claim.
    pos = _w19f_render("{{ conv(r) }}", ins_buyers=0, ins_bps=-24.0,
                       ins_sellers=9, ins_net_mn=3.2)
    assert "9 sellers" in pos and "9 名卖出" in pos
    assert "$" not in pos and "net " not in pos and "净卖出" not in pos


def test_w19f_alpha_only_note_one_leg():
    # One leg is still below the two-leg tilt floor, so the note must show.
    for call in ("{{ trow(r, 10) }}", "{{ srow(r) }}"):
        html = _w19f_render(call, n_legs=1)
        assert "α only" in html and "仅阿尔法" in html, call

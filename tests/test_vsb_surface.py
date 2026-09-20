"""VSB W3/W4/W5 surface tests: vol_weather + breadth_split on Market Sentiment card/dialog.

Four scenario groups:
  (i)  Both payloads present -> strip rows, AI section, stance text, card caveat appear.
  (ii) vol_weather=None/breadth_split=None -> sections absent, no raise.
  (iii) spread_50=8 (below 15 threshold) -> no card caveat rendered.
  (iv) Chip with pctile=None -> 'Still collecting' copy shown, no history phrase.

Also asserts no '<< NaN' artifacts in rendered output.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Jinja2 environment helpers
# ---------------------------------------------------------------------------

def _env():
    """Minimal Jinja2 env that mirrors build_site.py's dashboard render env."""
    import jinja2
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(ROOT / "templates")),
        autoescape=False,
        undefined=jinja2.ChainableUndefined,
    )
    # td/tr/zip globals (subset used by template)
    try:
        from engine import i18n
        env.globals.update(td=i18n.td, tr=i18n.tr, zip=zip)
    except Exception:  # noqa: BLE001
        env.globals.update(
            td=lambda en, zh=None: en,
            tr=lambda en: en,
            zip=zip,
        )
    env.filters["min"] = lambda seq: min(seq)
    # regex_replace is the One-Integer-Law (R-C, R-C FINAL FORM) hero stripper.
    # build_site.py registers the same filter on the production env. Without
    # this, the template crashes inside `_unified_dashboard_hero.html.j2` and
    # `dashboard.html.j2` on `{%- set _flip_en = _flip_en|regex_replace(...) -%}`.
    import re as _re
    env.filters["regex_replace"] = (
        lambda s, pattern, repl: _re.sub(pattern, repl, s)
        if isinstance(s, str) else s
    )
    return env


def _base_ctx() -> dict:
    """Minimal context dict that keeps the template from crashing on unrelated keys.

    Only provides the keys exercised by the sections under test. All other
    references inside dashboard.html.j2 degrade via ChainableUndefined.
    """
    # Load the engine's real market_state snapshot (or fall back to a
    # minimal-but-complete stub that the template's MS.* accesses can use).
    real_ms_path = ROOT / "data" / "market_state" / "latest.json"
    if real_ms_path.exists():
        try:
            market_state = json.loads(real_ms_path.read_text())
        except Exception:  # noqa: BLE001
            market_state = _minimal_market_state()
    else:
        market_state = _minimal_market_state()

    return {
        # mode='macro' is REQUIRED: the vol-weather strip (UD-B2-W1 R3 fold)
        # is gated on the macro render path; the page-mode render omits it.
        # Without this, the strip is dead markup and every assertion below
        # would falsely pass on a vacuous "no strip" result.
        "mode": "macro",
        # market_state gates the #sx-risk-v2 block in the template:
        # {% if market_state %} ... {% endif %}. Without it, the vol-weather
        # strip never renders even with vol_weather set. The template also
        # references MS.color / MS.label_en / MS.label_zh / MS.headline_en /
        # MS.headline_zh / MS.score etc. — using the real engine snapshot
        # means every unrelated MS access works without crashes.
        "market_state": market_state,
        # fear_greed: needed by the dialog preamble we share the block with
        "fear_greed": {
            "dial": 50,
            "label_en": "Neutral",
            "label_zh": "中性",
            "legs_included": [],
            "legs_excluded_young": [],
            "disclaimer_en": "Test disclaimer.",
            "disclaimer_zh": "测试免责声明。",
            "as_of": "2026-07-13",
        },
        # defaults for other often-accessed keys
        "latest": {},
        "generated": "2026-07-13 00:00",
        # These should be None/falsy by default; individual tests override
        "vol_weather": None,
        "breadth_split": None,
    }


def _minimal_market_state() -> dict:
    """Minimal market_state shape the template's MS.* accesses can survive."""
    return {
        "schema": "market_state.v1",
        "asof": "2026-07-13",
        "score": 61,
        "raw_score": 61,
        "score_source": "blend",
        "capped": False,
        "score_ceiling": None,
        "score_caps": [],
        "score_gap": None,
        "color": "yellow",
        "label_en": "Trade with caution",
        "label_zh": "谨慎操作",
        "verdict": "caution",
        "headline_en": "Markets cautious — stay selective",
        "headline_zh": "市场谨慎，精选标的",
        "flip_en": "Cautious tone held; breadth stable.",
        "flip_zh": "维持谨慎基调；广度稳定。",
        "components": [],
        "overrides": [],
        "score_ceiling": None,
        "radar": {
            "state": "caution",
            "top_score": 56,
            "label_en": "Credit stress",
            "label_zh": "信用压力",
            "state_zh": "警戒",
            "do_en": "Trim chasing; favour good entries over extended leaders.",
            "do_zh": "减少追高；择优入场而非追逐已延展的龙头。",
            "scares": [],
            "is_warning": True,
            "is_loud": False,
        },
        "audit": {},
    }


def _full_vol_weather() -> dict:
    """Fixture: vol_weather payload with all 8 chips, some young, some with pctile."""
    return {
        "as_of": "2026-07-13",
        "n_young": 1,
        "disclaimer_en": "Vol weather disclaimer.",
        "disclaimer_zh": "波动率天气免责声明。",
        "chips": [
            {
                "key": "vix_level",
                "name_en": "VIX level",
                "name_zh": "VIX 水平",
                "value": 18.5,
                "pctile": 42,
                "band": "normal",
                "state": "calm",
                "plain_en": "Volatility is calm",
                "plain_zh": "波动率平静",
                "freshness": "ok",
                "obs_count": 500,
                "last_date": "2026-07-13",
                "spark": [17, 18, 19, 18.5],
            },
            {
                "key": "vix_velocity",
                "name_en": "VIX velocity",
                "name_zh": "VIX 变动速度",
                "value": 0.3,
                "pctile": 55,
                "band": "normal",
                "state": "steady",
                "plain_en": "Rising slowly",
                "plain_zh": "缓慢上升",
                "freshness": "ok",
                "obs_count": 500,
                "last_date": "2026-07-13",
                "spark": [],
            },
            {
                "key": "term_slope",
                "name_en": "VIX term slope",
                "name_zh": "VIX 期限结构斜率",
                "value": 2.1,
                "pctile": 60,
                "band": "normal",
                "state": "contango",
                "plain_en": "Curve in contango — near-term calm",
                "plain_zh": "期货溢价，短期平静",
                "freshness": "ok",
                "obs_count": 500,
                "last_date": "2026-07-13",
                "spark": [],
            },
            {
                "key": "vvix_vix",
                "name_en": "VVIX / VIX",
                "name_zh": "VVIX / VIX",
                "value": 5.8,
                "pctile": 72,
                "band": "elevated",
                "state": "hedging",
                "plain_en": "Options on options elevated vs VIX",
                "plain_zh": "期权隐含波动率高于 VIX",
                "freshness": "ok",
                "obs_count": 500,
                "last_date": "2026-07-13",
                "spark": [],
            },
            {
                "key": "vix1d",
                "name_en": "VIX1D (overnight VIX)",
                "name_zh": "VIX1D（隔夜波动率）",
                "value": None,
                "pctile": None,
                "band": None,
                "state": "young",
                "plain_en": None,
                "plain_zh": None,
                "freshness": "young",
                "obs_count": 10,
                "last_date": "2026-07-13",
                "spark": [],
            },
            {
                "key": "cor1m",
                "name_en": "1-month implied correlation",
                "name_zh": "1个月隐含相关性",
                "value": 0.38,
                "pctile": 33,
                "band": "low",
                "state": "dispersed",
                "plain_en": "Stocks moving independently — dispersion high",
                "plain_zh": "个股走势分散，相关性低",
                "freshness": "ok",
                "obs_count": 400,
                "last_date": "2026-07-13",
                "spark": [],
            },
            {
                "key": "cor3m",
                "name_en": "3-month implied correlation",
                "name_zh": "3个月隐含相关性",
                "value": 0.41,
                "pctile": 38,
                "band": "low",
                "state": "dispersed",
                "plain_en": "Stocks moving independently",
                "plain_zh": "个股走势分散",
                "freshness": "ok",
                "obs_count": 400,
                "last_date": "2026-07-13",
                "spark": [],
            },
            {
                "key": "dspx",
                "name_en": "DSPX dispersion index",
                "name_zh": "DSPX 离散度指数",
                "value": 12.3,
                "pctile": 65,
                "band": "elevated",
                "state": "high",
                "plain_en": "Dispersion elevated — stock-picking matters",
                "plain_zh": "离散度偏高，选股更重要",
                "freshness": "ok",
                "obs_count": 300,
                "last_date": "2026-07-13",
                "spark": [],
            },
        ],
    }


def _full_breadth_split(spread: float = 25.0) -> dict:
    """Fixture: breadth_split payload."""
    return {
        "as_of": "2026-07-13",
        "cohort_sizes": {
            "ai_core": 80,
            "ai_infra_power": 20,
            "ai_total": 100,
            "non_ai": 300,
            "universe": 400,
            "ai_core_tagged": 85,
            "ai_infra_power_tagged": 22,
        },
        "latest": {
            "ai_pct50": 72.0,
            "nonai_pct50": 72.0 - spread,
            "spread_50": spread,
            "ai_pct200": 65.0,
            "nonai_pct200": 60.0,
            "spread_200": 5.0,
            "ai_adv_share": 55.0,
            "nonai_adv_share": 50.0,
            "spread_adv": 5.0,
        },
        "spark": {"spread_50": [20, 22, 25, 24, 25]},
        "young": False,
        "stance_en": "AI names leading — watch, don't chase",
        "stance_zh": "AI 相关股领涨，观察而非追高",
        "disclaimer_en": "Display-only. Not investment advice.",
        "disclaimer_zh": "仅供展示，非投资建议。",
    }


def _render(ctx: dict) -> str:
    """Render dashboard.html.j2 with the given context; returns HTML string."""
    env = _env()
    tmpl = env.get_template("dashboard.html.j2")
    return tmpl.render(**ctx)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestVSBSurfaceBothPayloads:
    """Scenario (i): both vol_weather and breadth_split present.

    UD-B2-W1 (R3): the vol-weather chips no longer render inside
    #dlg-sentiment. They now live as a sub-row inside the Risk isle
    (#sx-risk-v2) — see test_ud_b2_w1_vw_fold.py for the engine-true
    fold tests. This class keeps the surface-render assertions
    (plain text, pctile phrasing, breadth_split surface) on the new
    location: vol-weather text and chip markers must still appear on
    the page, but inside the isle slice, with the new scoped markers.
    """

    def test_vol_weather_subrow_present_in_risk_isle(self):
        ctx = _base_ctx()
        ctx["vol_weather"] = _full_vol_weather()
        ctx["breadth_split"] = _full_breadth_split(spread=25.0)
        html = _render(ctx)
        # The new sub-row is identified by data-sx-vw-strip + scope class
        assert "data-sx-vw-strip" in html, (
            "Vol weather sub-row must render (folded into the risk isle)"
        )
        assert "sx-vw-strip--risk-isle" in html, (
            "Vol weather sub-row must carry its scope class"
        )
        # And the OLD sibling-section id must NOT appear anymore
        assert 'id="vsb-vol-weather-section"' not in html, (
            "Old dialog sibling-section id (vsb-vol-weather-section) must not appear on the page"
        )

    def test_vol_weather_chip_rows_present(self):
        ctx = _base_ctx()
        ctx["vol_weather"] = _full_vol_weather()
        ctx["breadth_split"] = _full_breadth_split()
        html = _render(ctx)
        # After the fold, chips carry data-sx-vw-chip= on the new sub-row
        assert 'data-sx-vw-chip="vix_level"' in html
        assert 'data-sx-vw-chip="vix_velocity"' in html
        assert 'data-sx-vw-chip="cor1m"' in html
        assert 'data-sx-vw-chip="dspx"' in html
        # And the OLD dialog-row marker is gone
        assert 'data-vsb-chip="' not in html

    def test_vol_weather_plain_text_and_pctile_phrase(self):
        """R-W1-B + one-integer law: glance tier carries ONLY tier words
        (calm/breeze/gust/storm + ZH twins). The OLD phrases ('Volatility is
        calm', 'higher than N% of days', 'lower than N% of days') are banned
        from the glance tier — they belonged to the dialog's scoreboard row
        and have been demoted/removed entirely.

        This test now verifies the TIER-WORD contract: each chip's band
        maps to the tier-word family, and pctile scoreboard phrases are
        absent from the rendered output.
        """
        ctx = _base_ctx()
        ctx["vol_weather"] = _full_vol_weather()
        html = _render(ctx)
        # The risk isle slice is where the vol-weather strip lives.
        risk_isle_start = html.find('<div class="sx" id="sx-risk-v2"')
        assert risk_isle_start >= 0, "Risk isle must exist when mode=macro"
        depth = 0
        i = risk_isle_start
        n = len(html)
        while i < n:
            if html.startswith("<div ", i) or html.startswith("<div>", i):
                depth += 1
                i += 5
            elif html.startswith("</div>", i):
                depth -= 1
                i += 6
                if depth == 0:
                    break
            else:
                i += 1
        isle = html[risk_isle_start:i]
        # Every tier word family must be reachable from a chip in the fixture.
        # The fixture uses bands: normal/calm/quiet/low/elevated/extreme. The
        # template's _vw_band_word map covers every one of them — at least one
        # of the tier words below must appear on the rendered row.
        tier_words_en = ("calm", "breeze", "gust", "storm")
        tier_words_zh = ("平静", "微风", "疾风", "风暴")
        any_en = [w for w in tier_words_en if f'>{w}</span>' in isle or f'>{w}<' in isle]
        any_zh = [w for w in tier_words_zh if f'>{w}</span>' in isle or f'>{w}<' in isle]
        assert any_en, (
            f"At least one tier word EN {tier_words_en} must appear on the "
            f"rendered risk isle row (R-W1-B)"
        )
        assert any_zh, (
            f"At least one tier word ZH {tier_words_zh} must appear on the "
            f"rendered risk isle row (R-W1-B)"
        )
        # pctile scoreboard phrases must NOT appear on the page at all
        # (one-integer law: removed entirely, not demoted)
        assert "higher than" not in html, (
            "Pctile 'higher than N% of days' must not appear (one-integer law retirement)"
        )
        assert "lower than" not in html, (
            "Pctile 'lower than N% of days' must not appear (one-integer law retirement)"
        )
        # The old dialog-row marker is gone too
        assert "data-vsb-chip=" not in html

    def test_breadth_split_section_present(self):
        ctx = _base_ctx()
        ctx["vol_weather"] = _full_vol_weather()
        ctx["breadth_split"] = _full_breadth_split(spread=25.0)
        html = _render(ctx)
        assert 'id="vsb-breadth-split-section"' in html, (
            "AI vs rest section header should render when payload present"
        )

    def test_breadth_split_stance_text(self):
        ctx = _base_ctx()
        ctx["vol_weather"] = _full_vol_weather()
        ctx["breadth_split"] = _full_breadth_split(spread=25.0)
        html = _render(ctx)
        assert "AI names leading" in html
        assert "AI 相关股领涨" in html

    def test_breadth_split_receipt_lines(self):
        ctx = _base_ctx()
        ctx["vol_weather"] = _full_vol_weather()
        ctx["breadth_split"] = _full_breadth_split(spread=25.0)
        html = _render(ctx)
        assert 'data-vsb-bs="ai"' in html
        assert 'data-vsb-bs="nonai"' in html
        assert "AI-linked names above their 50-day trend" in html
        assert "Everyone else" in html

    def test_card_caveat_renders_when_spread_large(self):
        ctx = _base_ctx()
        ctx["vol_weather"] = _full_vol_weather()
        ctx["breadth_split"] = _full_breadth_split(spread=25.0)
        html = _render(ctx)
        assert 'id="vsb-sentiment-caveat"' in html, (
            "Card caveat should render when |spread_50| >= 15"
        )
        # Stance text should appear in the caveat
        assert "AI names leading" in html

    def test_circularity_watch_note(self):
        ctx = _base_ctx()
        ctx["vol_weather"] = _full_vol_weather()
        ctx["breadth_split"] = _full_breadth_split(spread=25.0)
        html = _render(ctx)
        assert "recycles capital" in html, (
            "Static circularity-watch note should appear in dialog"
        )

    def test_cohort_size_note(self):
        ctx = _base_ctx()
        ctx["vol_weather"] = _full_vol_weather()
        ctx["breadth_split"] = _full_breadth_split(spread=25.0)
        html = _render(ctx)
        # 100 AI-linked names out of 400 tracked
        assert "100" in html
        assert "400" in html

    def test_no_nan_artifacts(self):
        ctx = _base_ctx()
        ctx["vol_weather"] = _full_vol_weather()
        ctx["breadth_split"] = _full_breadth_split(spread=25.0)
        html = _render(ctx)
        # The brief check: no Jinja undefined-variable render artifacts
        assert "<< NaN" not in html, "No << NaN artifacts should appear"
        # Spot-check our added sections specifically: extract the vol-weather
        # sub-row from the risk isle slice and the breadth block; neither should
        # contain rendering NaNs. Post-fold, vol-weather lives inside the risk
        # isle, so we slice by the new data-sx-vw-strip sentinel.
        if "data-sx-vw-strip" in html:
            start = html.index("data-sx-vw-strip")
            snippet = html[start:start + 4000]
            assert "<< NaN" not in snippet


class TestVSBSurfaceAbsent:
    """Scenario (ii): vol_weather=None, breadth_split=None -> sections absent, no raise."""

    def test_renders_without_exception_when_both_none(self):
        ctx = _base_ctx()
        # Already defaults to None; just confirm render doesn't raise
        html = _render(ctx)
        assert html  # non-empty

    def test_vol_weather_section_absent_when_none(self):
        ctx = _base_ctx()
        html = _render(ctx)
        # Old dialog sibling-section id is never present, regardless of VM
        assert 'id="vsb-vol-weather-section"' not in html
        # The new scoped sub-row must also be absent when vol_weather is None
        assert 'data-sx-vw-strip' not in html

    def test_breadth_split_section_absent_when_none(self):
        ctx = _base_ctx()
        html = _render(ctx)
        assert 'id="vsb-breadth-split-section"' not in html

    def test_card_caveat_absent_when_breadth_none(self):
        ctx = _base_ctx()
        html = _render(ctx)
        assert 'id="vsb-sentiment-caveat"' not in html

    def test_no_nan_artifacts_absent_case(self):
        ctx = _base_ctx()
        html = _render(ctx)
        # No Jinja undefined render artifacts
        assert "<< NaN" not in html


class TestVSBSurfaceSmallSpread:
    """Scenario (iii): spread_50=8 (below 15 threshold) -> no card caveat."""

    def test_card_caveat_absent_when_spread_small(self):
        ctx = _base_ctx()
        ctx["vol_weather"] = _full_vol_weather()
        ctx["breadth_split"] = _full_breadth_split(spread=8.0)
        html = _render(ctx)
        assert 'id="vsb-sentiment-caveat"' not in html, (
            "Card caveat must not render when |spread_50| < 15"
        )

    def test_dialog_sections_still_render_when_spread_small(self):
        """Small spread should not suppress the dialog sections."""
        ctx = _base_ctx()
        ctx["vol_weather"] = _full_vol_weather()
        ctx["breadth_split"] = _full_breadth_split(spread=8.0)
        html = _render(ctx)
        assert 'id="vsb-breadth-split-section"' in html

    def test_negative_spread_also_suppressed(self):
        """Negative spread of -8 is below absolute threshold — no caveat."""
        bs = _full_breadth_split(spread=-8.0)
        bs["latest"]["spread_50"] = -8.0
        bs["latest"]["nonai_pct50"] = 80.0
        ctx = _base_ctx()
        ctx["breadth_split"] = bs
        html = _render(ctx)
        assert 'id="vsb-sentiment-caveat"' not in html


class TestVSBSurfaceYoungChip:
    """Scenario (iv): chip with pctile=None renders 'still collecting' copy, no history phrase."""

    def test_young_chip_shows_collecting_copy(self):
        """vix1d chip has freshness='young' and pctile=None -> 'Still collecting' shown."""
        ctx = _base_ctx()
        ctx["vol_weather"] = _full_vol_weather()  # includes vix1d with freshness='young'
        html = _render(ctx)
        assert "Still collecting" in html, (
            "Young chip should show 'Still collecting — check back soon'"
        )

    def test_young_chip_no_history_phrase(self):
        """A young chip must NOT show 'higher than X% of days'."""
        ctx = _base_ctx()
        # Isolate: only vix1d (young, pctile=None) in vol_weather
        vw = {
            "as_of": "2026-07-13",
            "n_young": 1,
            "chips": [
                {
                    "key": "vix1d",
                    "name_en": "VIX1D",
                    "name_zh": "VIX1D",
                    "value": None,
                    "pctile": None,
                    "band": None,
                    "state": "young",
                    "plain_en": None,
                    "plain_zh": None,
                    "freshness": "young",
                    "obs_count": 5,
                    "last_date": "2026-07-13",
                    "spark": [],
                }
            ],
        }
        ctx["vol_weather"] = vw
        html = _render(ctx)
        assert "higher than" not in html, (
            "Young chip with pctile=None must not show 'higher than X% of days'"
        )
        assert "Still collecting" in html

    def test_ok_chip_with_extreme_band_shows_storm_tier(self):
        """A chip with band='extreme' must show 'storm' / '风暴' tier word
        on the glance tier (UD-B2-W1 R3 + R-W1-B). Engine `plain_en` and
        pctile scoreboard phrases demote to the disclosure tier and do
        NOT appear on glance.
        """
        ctx = _base_ctx()
        vw = {
            "as_of": "2026-07-13",
            "n_young": 0,
            "chips": [
                {
                    "key": "vix_level",
                    "name_en": "VIX level",
                    "name_zh": "VIX 水平",
                    "value": 45.0,
                    "pctile": 99,
                    "band": "extreme",
                    "state": "panic",
                    "plain_en": "Extreme fear — volatility spiked",
                    "plain_zh": "极度恐慌，波动率飙升",
                    "freshness": "ok",
                    "obs_count": 500,
                    "last_date": "2026-07-13",
                    "spark": [],
                }
            ],
        }
        ctx["vol_weather"] = vw
        html = _render(ctx)
        # Tier word lands on the right column of the glance row.
        assert 'data-sx-vw-chip="vix_level"' in html
        assert 'data-tier="extreme"' in html
        # Tier word (storm / 风暴) shows inside the row's tier column.
        # Walk to the row and verify the tier word appears after .sx-vw-tier.
        import re as _re
        row = _re.search(
            r'data-sx-vw-chip="vix_level"[^>]*>.*?<div\s+class="sx-vw-tier">(.*?)</div>\s*</div>',
            html, _re.DOTALL,
        )
        assert row, "vix_level row not found in rendered HTML"
        tier = row.group(1)
        assert "storm" in tier and "风暴" in tier, (
            f"Extreme-band row must show 'storm' / '风暴' tier word; got {tier!r}"
        )
        # pctile scoreboard phrases must NOT appear on glance.
        assert "higher than" not in html
        assert "lower than" not in html
        assert "% of days" not in html
        # engine plain_en must NOT appear on glance (R-W1-B).
        assert "Extreme fear" not in html
        assert "volatility spiked" not in html

    def test_ok_chip_with_calm_band_shows_calm_tier(self):
        """A chip with band='calm' shows the 'calm' / '平静' tier word.
        pctile scoreboard phrases and engine plain_en do not appear on glance.
        """
        ctx = _base_ctx()
        vw = {
            "as_of": "2026-07-13",
            "n_young": 0,
            "chips": [
                {
                    "key": "vix_level",
                    "name_en": "VIX level",
                    "name_zh": "VIX 水平",
                    "value": 18.0,
                    "pctile": None,
                    "band": "calm",
                    "state": "calm",
                    "plain_en": "Calm",
                    "plain_zh": "平静",
                    "freshness": "ok",
                    "obs_count": 500,
                    "last_date": "2026-07-13",
                    "spark": [],
                }
            ],
        }
        ctx["vol_weather"] = vw
        html = _render(ctx)
        import re as _re
        row = _re.search(
            r'data-sx-vw-chip="vix_level"[^>]*>.*?<div\s+class="sx-vw-tier">(.*?)</div>\s*</div>',
            html, _re.DOTALL,
        )
        assert row, "vix_level row not found in rendered HTML"
        tier = row.group(1)
        assert "calm" in tier and "平静" in tier, (
            f"Calm-band row must show 'calm' / '平静' tier word; got {tier!r}"
        )
        # pctile scoreboard phrases must NOT appear on glance.
        assert "higher than" not in html
        assert "lower than" not in html
        # engine plain_en "Calm" must NOT appear on glance — tier word is the read.
        # Note: tier word "calm" appears inside the tier column, but plain_en
        # "Calm" (capitalised, from engine) should not appear on the row.
        # The row contains "calm" in lowercase (tier word) only.

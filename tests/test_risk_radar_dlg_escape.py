"""Escaping contract for the Risk Radar dialogs' pipeline-sourced strings.

The shared country dialog (templates/_risk_radar_dlg.html.j2) is rendered by
scripts/build_china.py, build_hk.py and build_canada.py, all of which build their
Jinja Environment with ``autoescape=False``. The US dialog lives inside
templates/dashboard.html.j2: the production env in scripts/build_site.py runs with
``autoescape=True``, while the dev fast renderer (scripts/render_macro_fast.py) uses
Jinja's default — autoescape OFF. Tickers, names, as-of dates and caveats in these
dialogs come from the data pipeline, so each one is passed through ``|e`` explicitly
rather than trusting the environment.

Two properties are pinned:

1. A hostile value (``<b>X</b>``) comes out escaped exactly once, under every env the
   template is actually rendered with.
2. Ordinary values (letters, digits, dots, dashes, colons, spaces, CJK) render
   BYTE-IDENTICAL to the pre-escape template. The "pre-escape twin" is derived from the
   current source by stripping every ``|e`` inside ``{{ ... }}`` — the twin is also
   shown to leak the hostile value raw, so the comparison is known to discriminate.
"""
from __future__ import annotations

import functools
import re
from pathlib import Path

import pytest
from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"
DLG = "_risk_radar_dlg.html.j2"

HOSTILE = "<b>X</b>"
HOSTILE_ESC = "&lt;b&gt;X&lt;/b&gt;"
HOSTILE_DOUBLE = "&amp;lt;b&amp;gt;"

_EXPR = re.compile(r"\{\{.*?\}\}", re.S)
_ESC_FILTER = re.compile(r"\s*\|\s*e\b")


def _strip_escape(src: str) -> tuple[str, int]:
    """Remove every ``|e`` filter inside ``{{ }}`` — the pre-escape twin of ``src``."""
    n = 0

    def _one(m: re.Match) -> str:
        nonlocal n
        out, k = _ESC_FILTER.subn("", m.group(0))
        n += k
        return out

    return _EXPR.sub(_one, src), n


# ── Shared country dialog (CN / HK / CA) ─────────────────────────────────────────

_RD = {
    "state": "caution", "top_score": 82, "label_en": "Breadth breakdown",
    "label_zh": "广度破位", "state_zh": "警戒",
    "do_en": "Trim chasing; favour good entries over extended leaders.",
    "do_zh": "减少追高；择优入场而非追逐已延展的龙头。", "gross": 0.8,
    "dd5": 0.06, "dd10": 0.12, "dd21": 0.24, "dd_lift": 1.35,
    "dd_base": {"h5": 0.036, "h10": 0.086, "h21": 0.178},
    "is_loud": True, "scares": [], "forward_log": None, "cycle": None, "counterread": None,
    "amp": 0, "amp_flags_en": [], "amp_flags_zh": [], "recovery": None, "track": None,
}


def _dlg_ctx(v: str, *, asof: str, lag: str, rows: bool = True) -> dict:
    leaders = {"line_en": f"Line {v}", "line_zh": f"线 {v}",
               "absent_en": f"Absent {v}", "absent_zh": f"缺 {v}"}
    if rows:
        leaders["rows"] = [
            {"ticker": v, "name_en": f"Name {v}", "name_zh": f"名 {v}",
             "value": f"#1 {v}", "pct": None, "tone": "muted"},
            {"ticker": "603308.SS", "name_en": "Ordinary Co", "name_zh": "普通股份",
             "value": "#2", "pct": None, "tone": "muted"},
        ]
    return {
        "asof": asof,
        "caveat_en": f"Caveat {v}", "caveat_zh": f"提示 {v}",
        "leaders": leaders,
        # usd_dir makes the currency section render; stale + a different built_date
        # makes the as-of clause carry the lagging-feed date
        "fx": {"usd_dir": "weakening", "stale": True, "built_date": lag},
    }


@functools.lru_cache(maxsize=None)
def _dlg_template(twin: bool):
    fs = FileSystemLoader(str(TEMPLATES))
    loader = fs
    if twin:
        src, n = _strip_escape((TEMPLATES / DLG).read_text(encoding="utf-8"))
        assert n > 0, "no |e filters found to strip — the twin would equal the source"
        loader = ChoiceLoader([DictLoader({DLG: src}), fs])
    # the builders' own setting: autoescape OFF
    env = Environment(loader=loader, autoescape=False)
    return env.from_string(
        '{% import "' + DLG + '" as rrd %}{{ rrd.risk_radar_dlg(mkt, rd, none, ctx) }}'
    )


def _render_dlg(mkt: str, ctx: dict, *, twin: bool = False) -> str:
    return _dlg_template(twin).render(mkt=mkt, rd=_RD, ctx=ctx)


_MKTS = ["cn", "hk", "ca"]


class TestCountryDialogEscapes:
    @pytest.mark.parametrize("mkt", _MKTS)
    def test_leader_row_ticker_is_escaped(self, mkt):
        html = _render_dlg(mkt, _dlg_ctx(HOSTILE, asof="2026-10-13", lag="2026-10-10"))
        assert f'<span class="rrd-ldr-tkr">{HOSTILE_ESC}</span>' in html
        assert HOSTILE not in html
        assert HOSTILE_DOUBLE not in html

    @pytest.mark.parametrize("mkt", _MKTS)
    def test_leader_row_siblings_are_escaped(self, mkt):
        html = _render_dlg(mkt, _dlg_ctx(HOSTILE, asof="2026-10-13", lag="2026-10-10"))
        for frag in (f"Name {HOSTILE_ESC}", f"名 {HOSTILE_ESC}", f"#1 {HOSTILE_ESC}",
                     f"Line {HOSTILE_ESC}", f"线 {HOSTILE_ESC}",
                     f"Caveat {HOSTILE_ESC}", f"提示 {HOSTILE_ESC}"):
            assert frag in html, frag

    @pytest.mark.parametrize("mkt", _MKTS)
    def test_leader_absent_line_is_escaped(self, mkt):
        # no rows and no line → the absence branch
        ctx = _dlg_ctx(HOSTILE, asof="2026-10-13", lag="2026-10-10", rows=False)
        ctx["leaders"].pop("line_en")
        html = _render_dlg(mkt, ctx)
        assert f'<div class="rrd-absent"><span class="l-en">Absent {HOSTILE_ESC}</span>' in html
        assert f"缺 {HOSTILE_ESC}" in html
        assert HOSTILE not in html

    @pytest.mark.parametrize("mkt", _MKTS)
    def test_tone_cannot_break_out_of_the_class_attribute(self, mkt):
        ctx = _dlg_ctx("AAA", asof="2026-10-13", lag="2026-10-10")
        ctx["leaders"]["rows"][0]["tone"] = 'x" onmouseover="alert(1)'
        html = _render_dlg(mkt, ctx)
        assert 'onmouseover="alert(1)' not in html
        assert "tone-x&#34; onmouseover=&#34;alert(1)" in html

    @pytest.mark.parametrize("mkt", _MKTS)
    def test_asof_and_currency_lag_are_escaped_in_both_languages(self, mkt):
        html = _render_dlg(mkt, _dlg_ctx("AAA", asof=HOSTILE, lag="<i>L</i>"))
        assert f"As of {HOSTILE_ESC}, currency readings from &lt;i&gt;L&lt;/i&gt;. " in html
        assert f"数据截至 {HOSTILE_ESC}，汇率读数为 &lt;i&gt;L&lt;/i&gt;。" in html
        assert HOSTILE not in html and "<i>L</i>" not in html


_ORDINARY = [
    "600118.SS",
    "0700.HK",
    "RY.TO",
    "BRK-B",
    "Ratio 1:2 up 3.5",
    "中国卫星",
    "腾讯控股 00700",
]


class TestCountryDialogByteIdentity:
    @pytest.mark.parametrize("value", _ORDINARY)
    @pytest.mark.parametrize("mkt", _MKTS)
    def test_ordinary_values_render_byte_identical_to_pre_escape_twin(self, mkt, value):
        ctx = _dlg_ctx(value, asof="2026-10-13", lag="2026-10-10")
        assert _render_dlg(mkt, ctx) == _render_dlg(mkt, ctx, twin=True)

    @pytest.mark.parametrize("mkt", _MKTS)
    def test_absence_branch_is_byte_identical_too(self, mkt):
        ctx = _dlg_ctx("中国卫星", asof="2026-10-13", lag="2026-10-10", rows=False)
        ctx["leaders"].pop("line_en")
        assert _render_dlg(mkt, ctx) == _render_dlg(mkt, ctx, twin=True)

    def test_exact_ordinary_bytes(self):
        html = _render_dlg("cn", _dlg_ctx("600118.SS", asof="2026-10-13", lag="2026-10-10"))
        assert '<span class="rrd-ldr-tkr">600118.SS</span>' in html
        assert '<span class="rrd-ldr-tkr">603308.SS</span>' in html
        assert ('<span class="l-en">Ordinary Co</span><span class="l-zh">普通股份</span>'
                in html)
        assert "As of 2026-10-13, currency readings from 2026-10-10. " in html
        assert "数据截至 2026-10-13，汇率读数为 2026-10-10。" in html

    def test_twin_discriminates(self):
        """The pre-escape twin leaks the hostile ticker raw — so equality above means
        the escape changed nothing for ordinary input, not that the twin is inert."""
        html = _render_dlg("cn", _dlg_ctx(HOSTILE, asof=HOSTILE, lag="2026-10-10"),
                           twin=True)
        assert f'<span class="rrd-ldr-tkr">{HOSTILE}</span>' in html
        assert f"As of {HOSTILE}" in html


# ── US dashboard Risk Radar dialog (templates/dashboard.html.j2) ─────────────────
# The dashboard needs a full build view-model to render whole, so the two dialog
# fragments are cut from the live template source by stable markers and rendered
# standalone with the template's own `t` macro.

_DASH = (TEMPLATES / "dashboard.html.j2").read_text(encoding="utf-8")


def _slice(src: str, start: str, end: str, *, include_end_line: bool) -> str:
    i = src.index(start)
    j = src.index(end, i)
    if include_end_line:
        j = src.index("\n", j)
    return src[i:j]


def _t_macro(src: str) -> str:
    i = src.index("{% macro t(en, zh='') -%}")
    j = src.index("{%- endmacro %}", i) + len("{%- endmacro %}")
    return src[i:j]


def _dash_fragments(src: str) -> dict[str, str]:
    t = _t_macro(src)
    head = _slice(src, "{% set _rk_asof = ", 'class="riskdlg-asof"', include_end_line=True)
    lead = _slice(src, "{% set _rot = (sector_heat.get('rotation')",
                  "</div>{# /riskdlg-leadership #}", include_end_line=False)
    return {"head": t + "\n" + head, "lead": t + "\n" + lead}


_FRAGS = _dash_fragments(_DASH)
_FRAGS_TWIN = {k: _strip_escape(v)[0] for k, v in _FRAGS.items()}


def _dash_vars(v: str) -> dict:
    return {
        "latest": {"date": v},
        "sector_heat": {
            "as_of": v,
            "rotation": [
                {"id": v, "short_name": f"Theme {v}", "short_name_zh": f"主题 {v}",
                 "rank": 1, "rank_delta_5d": 2},
                {"id": "ai-power", "short_name": "AI Power", "short_name_zh": None,
                 "rank": 2, "rank_delta_5d": 0},
            ],
        },
        "leadership_crack": {
            "state": "BROKEN", "asof": v, "state_since": v,
            "med_dd": -0.31, "high_window_sessions": 63,
            "share10": 0.8, "share30": 0.4, "n_total": 20,
            "index_dd": -0.08, "z_vel": 1.24, "carnage_share_ema": 0.35,
            "worst_members": [{"ticker": v, "dd": -0.52},
                              {"ticker": "SMCI", "dd": -0.47}],
        },
    }


@functools.lru_cache(maxsize=None)
def _dash_template(frag: str, autoescape: bool, twin: bool):
    src = (_FRAGS_TWIN if twin else _FRAGS)[frag]
    return Environment(autoescape=autoescape).from_string(src)


def _render_dash(frag: str, v: str, *, autoescape: bool, twin: bool = False) -> str:
    return _dash_template(frag, autoescape, twin).render(**_dash_vars(v))


_ENVS = pytest.mark.parametrize(
    "autoescape", [True, False], ids=["prod-autoescape-on", "dev-autoescape-off"])


class TestDashboardDialogEscapes:
    def test_fragments_found_and_carry_the_filters(self):
        assert "{{ _rk_asof|e }}" in _FRAGS["head"]
        assert '<div class="rkc-ldr-tkr">{{ wm.ticker|e }}</div>' in _FRAGS["lead"]
        for frag in ("head", "lead"):
            assert _FRAGS_TWIN[frag] != _FRAGS[frag]

    @_ENVS
    def test_riskdlg_asof_is_escaped_once(self, autoescape):
        html = _render_dash("head", HOSTILE, autoescape=autoescape)
        assert f'<span class="riskdlg-asof">{HOSTILE_ESC}</span>' in html
        assert HOSTILE not in html and HOSTILE_DOUBLE not in html

    @_ENVS
    def test_worst_member_ticker_is_escaped_once(self, autoescape):
        html = _render_dash("lead", HOSTILE, autoescape=autoescape)
        assert f'<div class="rkc-ldr-tkr">{HOSTILE_ESC}</div>' in html
        assert '<div class="rkc-ldr-tkr">SMCI</div>' in html
        assert HOSTILE not in html and HOSTILE_DOUBLE not in html

    @_ENVS
    def test_leadership_siblings_are_escaped_once(self, autoescape):
        html = _render_dash("lead", HOSTILE, autoescape=autoescape)
        assert f'href="basket/{HOSTILE_ESC}.html"' in html
        assert f"Theme {HOSTILE_ESC}" in html and f"主题 {HOSTILE_ESC}" in html
        # section header + rotation head (sector_heat.as_of) and cohort kicker (_lc.asof)
        assert html.count(f"</span> {HOSTILE_ESC}</small>") == 3
        # receipt tooltip attributes carry state_since
        assert f'data-tip-en="State since {HOSTILE_ESC}.' in html
        assert f'data-tip-zh="自{HOSTILE_ESC}起。' in html

    @_ENVS
    def test_theme_id_cannot_break_out_of_href(self, autoescape):
        html = _render_dash("lead", 'x" onclick="alert(1)', autoescape=autoescape)
        assert 'onclick="alert(1)' not in html


_DASH_ORDINARY = ["2026-10-13", "NVDA", "BRK.B", "Ratio 1:2 up 3.5", "人工智能电力"]


class TestDashboardDialogByteIdentity:
    @pytest.mark.parametrize("value", _DASH_ORDINARY)
    @pytest.mark.parametrize("frag", ["head", "lead"])
    @_ENVS
    def test_ordinary_values_render_byte_identical_to_pre_escape_twin(
            self, autoescape, frag, value):
        assert (_render_dash(frag, value, autoescape=autoescape)
                == _render_dash(frag, value, autoescape=autoescape, twin=True))

    def test_twin_discriminates_under_the_dev_renderer(self):
        html = _render_dash("lead", HOSTILE, autoescape=False, twin=True)
        assert f'<div class="rkc-ldr-tkr">{HOSTILE}</div>' in html

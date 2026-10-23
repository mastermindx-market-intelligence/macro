"""Contract tests for the shared country Risk Radar dialog (templates/_risk_radar_dlg.html.j2).

The partial's whole promise is "absent-safe by construction": china / hk / canada each
assemble `ctx` from stores that go missing, go stale, or return partial rows, and a
build must NEVER die on a missing payload — the section simply does not render.

The trap this pins (it took down a real China build on 2026-08-11): in Jinja a MISSING
dict key evaluates `is not none` as TRUE, so `{% if f.pct is not none %}` guards nothing
and the arithmetic behind it raises `UndefinedError`. Every optional numeric field in
the macro must be guarded `is defined and is not none`. The sparse case below feeds
dicts whose optional keys are omitted (not set to None) precisely to catch a regression.

Also pins the copy law the dialog ships under (DESIGN_DOCTRINE §5 / CLAUDE.md epistemics):
no falsifier vocabulary, no "validated", no internal jargon at glance tier.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent

# Shape mirrors engine/market_state.py `_radar_to_rd` — which always emits every key.
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

# Every optional key OMITTED rather than set to None — the Undefined-vs-None trap.
_CTX_SPARSE = {
    "leading": {"bench_en": "Shanghai Composite"},
    "overseas": {"level": "high"},
    "track": {},
    "calendar": [{"date": "2026-08-17"}, {"name_en": "LPR fix"}],
    "policy_chips": [{"label_en": "Policy stance", "value_en": "Easing"}],
    "factors": [{"label_en": "Margin balance", "value": "2.7%"}, {"label_en": "Options fear"}],
    "gauges": [{"label_en": "Deep-drawdown gauge"}],
    "leaders": {"rows": [{"ticker": "600118.SS"}, {"ticker": "603308.SS"}]},
    "fx": {"usd_dir": "weakening"},
}
_SCARES_SPARSE = [{"label_en": "Breadth breakdown"}, {"label_en": "US rate shock", "score": 51}]


def _render(mkt="cn", rd=_RD, scares=None, ctx=None, measured_state=None) -> str:
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=False)
    tpl = env.from_string(
        '{% import "_risk_radar_dlg.html.j2" as rrd %}'
        "{{ rrd.risk_radar_dlg(mkt, rd, scares, ctx, measured_state) }}"
    )
    return tpl.render(
        mkt=mkt,
        rd=rd,
        scares=scares,
        ctx=ctx,
        measured_state=measured_state,
    )


class TestAbsentSafe:
    @pytest.mark.parametrize("ctx", [None, {}, _CTX_SPARSE], ids=["none", "empty", "sparse"])
    @pytest.mark.parametrize("mkt", ["cn", "hk", "ca"])
    def test_renders_without_raising(self, mkt, ctx):
        html = _render(mkt=mkt, scares=_SCARES_SPARSE, ctx=ctx)
        assert f'id="{mkt}x-dlg-risk"' in html
        # the headline always renders — the dialog is never an empty shell
        assert "rrd-hd" in html

    def test_no_radar_at_all_still_renders_a_stance(self):
        html = _render(rd=None, scares=None, ctx=None)
        assert "No active risk readings" in html and "暂无活跃风险读数" in html
        assert "Nothing to chase right now" in html
        # a stub radar must NOT drag the .rrx card in (it reads odds fields unguarded)
        assert 'class="rrx' not in html

    def test_stub_radar_does_not_pull_in_the_card(self):
        html = _render(rd={"state": "calm"}, ctx=None)
        assert 'class="rrx' not in html

    def test_full_radar_embeds_the_shared_card(self):
        html = _render(ctx=None)
        assert 'class="rrx' in html

    def test_sections_are_omitted_not_emptied(self):
        """No payload -> no eyebrow. An empty titled section is a defect, not an absence."""
        html = _render(ctx={})
        for eyebrow in ("The local backdrop", "Leaders", "Currency backdrop", "Context"):
            assert eyebrow not in html, eyebrow


class TestShell:
    def test_market_prefix_drives_the_page_dialog_idiom(self):
        html = _render(mkt="hk")
        assert 'class="hkx-dlg"' in html
        assert "hkxCloseDlg()" in html            # backdrop + close button
        assert html.count("hkxCloseDlg()") >= 2

    def test_ctx_can_override_the_shell(self):
        html = _render(ctx={"dlg": {"id": "zz-dlg", "cls": "zz", "close_js": "zzClose()"}})
        assert 'id="zz-dlg"' in html and 'class="zz"' in html and "zzClose()" in html


class TestCopyLaw:
    def test_one_asof_and_one_footnote(self):
        html = _render(ctx={"asof": "2026-08-11", "caveat_en": "Led from outside.",
                            "caveat_zh": "由外部因素引导。", **_CTX_SPARSE})
        assert html.count("As of 2026-08-11") == 1
        assert html.count("数据截至 2026-08-11") == 1
        assert html.count('class="rrd-foot"') == 1

    def test_windows_not_certainties_line_is_always_present(self):
        html = _render(ctx=None)
        assert "windows, not certainties — re-drawn nightly" in html
        assert "是概率窗口而非定论——每晚重算" in html

    @pytest.mark.parametrize("banned", [
        # falsifier vocabulary is never front-facing (operator 2026-07-27, #3821)
        "falsifier", "refuted", "证伪",
        # CI-guarded overclaim
        "validated",
        # internal vocabulary banned at glance tier (DESIGN_DOCTRINE Law 2)
        "display-tier", "gauntlet", "prereg", "z-score", "K-of-N",
    ])
    def test_banned_vocabulary_absent(self, banned):
        html = _render(scares=_SCARES_SPARSE, ctx=_CTX_SPARSE)
        assert banned.lower() not in html.lower(), banned

    def test_severity_colour_uses_only_the_zh_flipping_token_family(self):
        """Risk colour must ride --down/--warn/--up (theme.css swaps them under zh),
        never a literal green/red hex the Asia convention cannot flip."""
        css = (ROOT / "templates" / "_risk_radar_dlg.css.j2").read_text(encoding="utf-8")
        import re
        # any 3/6-digit hex outside a comment is a colour literal
        stripped = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b", stripped), "literal hex colour in rrd- CSS"
        html = (ROOT / "templates" / "_risk_radar_dlg.html.j2").read_text(encoding="utf-8")
        body = html.split("{% macro risk_radar_dlg", 1)[1]
        assert not re.search(r"#[0-9a-fA-F]{3,6}\b(?!;)", body.replace("&#xd7;", "")), \
            "literal hex colour in rrd- markup"

    def test_no_translated_text_in_title_attributes(self):
        """CI-guarded house law: receipts ride data-tip-en/zh, never title=."""
        html = _render(scares=_SCARES_SPARSE, ctx=_CTX_SPARSE)
        assert "title=" not in html



class TestChinaP0Semantics:
    """China must separate tape state, forward hazard, and capital authority."""

    _RD_CN = {
        "state": "risk-off",
        "top_score": 98,
        "label_en": "US rate shock",
        "label_zh": "美债利率冲击",
        "state_zh": "避险",
        "do_en": "Defend capital first.",
        "do_zh": "优先防守。",
        "gross": 0.62,
        "dd5": 0.15,
        "dd10": 0.32,
        "dd21": 0.50,
        "dd_lift": 1.64,
        "dd_base": {"h5": 0.036, "h10": 0.086, "h21": 0.305},
        "is_loud": True,
        "is_warning": True,
        "can_force": False,
        "binding": False,
        "authority": {
            "tier": "advisory",
            "can_force": False,
            "note_en": "Advisory — sizes risk; does not override the measured tape.",
            "note_zh": "提示性信号——仅调整仓位，不覆盖实测盘面。",
        },
        "scares": [
            {"label_en": "US rate shock", "label_zh": "美债利率冲击", "score": 97.1, "band": "risk-off"},
            {"label_en": "Breadth breakdown", "label_zh": "广度破位", "score": 96.2, "band": "risk-off"},
            {"label_en": "Capital outflow / FX", "label_zh": "资本外流／汇率", "score": 62.2, "band": "caution"},
        ],
        # Mirrors the real producer split: forward_log owns matured rows while
        # track owns monitoring, loud-alert outcomes, and awaiting-maturity rows.
        "forward_log": {"n_graded": 16, "can_force": False},
        "track": {
            "monitoring": {"awaiting_maturity": 18, "graded_n": 16, "log_fresh": True},
            "windows": {
                "full": {"alerts": {"n": 5, "tp": 2, "fp": 3, "hit_rate": 0.4}},
                "y1": {"alerts": {"n": 5, "tp": 2, "fp": 3, "hit_rate": 0.4},
                       "watch_caution": {"n": 11, "tp": 7}, "by_scare": {}},
            },
        },
        "cycle": None,
        "counterread": None,
        "amp": 0,
        "amp_flags_en": [],
        "amp_flags_zh": [],
        "recovery": None,
    }
    _MS_CN = {
        "score": 39,
        "raw_score": 39,
        "score_source": "blend",
        "capped": False,
        "verdict": "RISK_OFF",
        "label_en": "Risk-off",
        "label_zh": "避险",
        "components": [
            {"key": "trend", "score": 38},
            {"key": "risk_appetite", "score": 51},
            {"key": "vol_froth", "score": 54},
            {"key": "breadth", "score": 15},
            {"key": "liquidity", "score": 16},
            {"key": "stress", "score": 63},
        ],
    }

    def _html(self) -> str:
        return _render(
            mkt="cn",
            rd=self._RD_CN,
            scares=self._RD_CN["scares"],
            ctx={"title_en": "China Risk Context", "title_zh": "中国风险背景"},
            measured_state=self._MS_CN,
        )

    def test_first_dialog_view_separates_the_three_objects(self):
        html = self._html()
        for phrase in (
            "MEASURED STATE",
            "TRANSITION HAZARD",
            "FORWARD ODDS",
            "EVIDENCE / AUTHORITY",
            "实测状态",
            "转变风险",
            "前瞻概率",
            "证据／权限",
        ):
            assert phrase in html

    def test_measured_state_discloses_boundary_and_actual_weak_legs(self):
        html = self._html()
        assert "near Mixed boundary" in html
        assert "3 points below" in html
        assert "Participation and liquidity are weak; trend remains soft." in html
        assert "参与度与流动性偏弱；趋势仍然疲软。" in html
        assert "stress is elevated" not in html.lower()

    def test_hazard_score_is_a_percentile_not_a_probability(self):
        html = self._html()
        assert "EXTREME" in html and "98th percentile" in html
        assert "极端" in html and "第98百分位" in html
        assert "98/100" not in html and "98</b>/100" not in html

    def test_forward_odds_are_historical_and_reference_bounded(self):
        html = self._html()
        assert "Historical model estimate" in html
        assert "历史模型估计" in html
        assert "50%" in html
        assert "normal historical rate 30.5%" in html
        assert "常态历史率 30.5%" in html
        assert "1.64× reference odds" in html
        assert "1.64× 参考概率" in html

    def test_evidence_and_authority_are_explicit(self):
        html = self._html()
        for phrase in ("16 matured", "5 loud", "2 hits", "18 awaiting maturity"):
            assert phrase in html
        for phrase in ("16 条已成熟", "5 条强警报", "2 次命中", "18 条待成熟"):
            assert phrase in html
        assert "ADVISORY — does not override measured tape" in html
        assert "提示性 — 不覆盖实测盘面" in html

    def test_advisory_sizing_uses_exact_reference_not_round_wording(self):
        html = self._html()
        assert "×0.62" in html
        assert "advisory risk-budget reference" in html
        assert "提示性风险预算参考" in html
        assert "half of normal" not in html
        assert "suggested size" not in html
        assert "约常规一半" not in html
        assert "建议仓位" not in html
        assert "never selects stocks" in html
        assert "不用于选股" in html

    def test_china_template_does_not_reintroduce_banned_copy(self):
        template = (ROOT / "templates" / "china.html.j2").read_text(encoding="utf-8")
        for phrase in ("Transition hazard", "Historical model estimate", "Live forward evidence still accruing"):
            assert phrase in template
        for banned in ("stress is elevated; defend capital first", "half of normal", "suggested size", "98/100"):
            assert banned.lower() not in template.lower()

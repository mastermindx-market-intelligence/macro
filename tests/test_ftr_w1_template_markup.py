"""Render/parse assertions for FTR W1+W2a template additions.

Guards:
- ftr-shock-banner, ftr-lever-chip, ftr-member-sym-registry divs are present
- lever chip reads framing/framing_zh from fetched JSON (d.framing_zh), NOT hardcoded ZH
- allocation.html.j2 carries the FT-R11 horizon label
- basket_detail.html.j2 uses relative paths (../live/...) for shock_state / policy_lever
- sector_central.html.j2 full render with basket_member_syms emits data-sym spans

These are display-tier / de-escalation additions (FT-R2, PS-R3, PS-W2-F, FT-R11).
"""
from __future__ import annotations

import html as html_lib
import re
from pathlib import Path

import pytest

TMPL_DIR = Path(__file__).parent.parent / "templates"


def _src(name: str) -> str:
    return (TMPL_DIR / name).read_text()


def _parse(name: str) -> None:
    from jinja2 import Environment
    src = _src(name)
    Environment(autoescape=False).parse(src)


def _render_baskets(syms: list[str]) -> str:
    from jinja2 import Environment, FileSystemLoader, Undefined
    env = Environment(loader=FileSystemLoader(str(TMPL_DIR)), autoescape=False,
                      undefined=Undefined)
    t = env.get_template("sector_central.html.j2")
    return t.render(basket_member_syms=syms)


# ── Parse (syntax) guards ──────────────────────────────────────────────────

class TestFtrTemplatesParse:
    def test_baskets_parses(self):
        _parse("sector_central.html.j2")

    def test_allocation_parses(self):
        _parse("allocation.html.j2")

    def test_basket_detail_parses(self):
        _parse("basket_detail.html.j2")


# ── Static-source guards (framing + structure) ─────────────────────────────

class TestFtrStaticSource:
    """Check static source strings that can't be overridden by Jinja rendering."""

    @pytest.mark.parametrize("template", [
        "sector_central.html.j2", "allocation.html.j2", "basket_detail.html.j2",
    ])
    def test_shock_banner_div_present(self, template):
        assert "ftr-shock-banner" in _src(template)

    @pytest.mark.parametrize("template", [
        "sector_central.html.j2", "allocation.html.j2", "basket_detail.html.j2",
    ])
    def test_lever_chip_div_present(self, template):
        assert "ftr-lever-chip" in _src(template)

    @pytest.mark.parametrize("template", [
        "sector_central.html.j2", "allocation.html.j2", "basket_detail.html.j2",
    ])
    def test_framing_read_from_json_not_hardcoded(self, template):
        """Lever chip must use d.framing_zh from the fetched JSON, not a hardcoded ZH string."""
        src = _src(template)
        # Must reference framing_zh field from the fetched data
        assert "d.framing_zh" in src, f"{template} must read framing_zh from fetched JSON"
        # Must NOT contain the old hardcoded ZH disclaimer that diverged from policy_lever.json
        assert "更可能出现剧烈隔夜反转的条件" not in src, (
            f"{template}: hardcoded ZH disclaimer removed; use d.framing_zh from JSON"
        )

    def test_basket_detail_uses_relative_paths(self):
        """basket_detail pages live under site/basket/ — must use ../ prefix."""
        src = _src("basket_detail.html.j2")
        assert "../live/shock_state.json" in src
        assert "../policy_lever.json" in src

    def test_allocation_ft_r11_horizon_label(self):
        """FT-R11: allocation page must carry the honest strategic-horizon sub-label.

        The label ships in plain words, not the wording this test was born with.
        #2635 ported the original copy — "Strategic horizon (3–12m): skip-month
        momentum by construction — this view is deliberately slow." — to the
        current sentence under docs/DESIGN_DOCTRINE.md Law 2 (no unexplained
        construction jargon on Tier 1: "skip-month momentum by construction" is
        exactly the banned "comparative construction that needs a manual") and
        Law 3 (a Tier-1 number arrives with its interpretation). The label div
        and its FT-R11 marker comment are untouched by that port — only the
        sentence inside changed — so assert the disclosure, not the retired
        string. Asserting the old wording would pin a Law 2 violation in place.
        """
        src = _src("allocation.html.j2")
        assert "FT-R11 horizon label" in src
        # the horizon stays explicit while the Tier-1 wording remains plain.
        assert "Slow-moving view" in src
        assert "3–12 month trends" in src
        assert "deliberately ignores the most recent month" in src
        # Law 5 — honesty survives translation (the ZH twin carries the same claim).
        assert "慢速视角" in src
        assert "3–12个月趋势" in src
        assert "刻意忽略最近一个月" in src

    def test_basket_detail_nb_chg_spans(self):
        """basket_detail must emit nb-chg spans for member live-price wiring."""
        src = _src("basket_detail.html.j2")
        assert "nb-chg" in src

    def test_baskets_member_sym_registry_div(self):
        """sector_central.html.j2 must have the hidden registry div for live-quotes scrape."""
        assert "ftr-member-sym-registry" in _src("sector_central.html.j2")


# ── Full-render guard for sector_central.html.j2 ─────────────────────────────────

class TestFtrBasketsRender:
    """Full Jinja render of sector_central.html.j2 with basket_member_syms context."""

    def test_member_sym_spans_emitted(self):
        html = _render_baskets(["AAPL", "NVDA", "MSFT"])
        assert 'data-sym="AAPL"' in html
        assert 'data-sym="NVDA"' in html
        assert 'data-sym="MSFT"' in html

    def test_shock_banner_div_in_render(self):
        html = _render_baskets(["SPY"])
        assert "ftr-shock-banner" in html

    def test_lever_chip_div_in_render(self):
        html = _render_baskets(["SPY"])
        assert "ftr-lever-chip" in html

    def test_framing_zh_ref_in_render(self):
        """The rendered JS must reference d.framing_zh, not a static ZH string."""
        html = _render_baskets(["SPY"])
        assert "d.framing_zh" in html

    def test_no_member_spans_when_syms_empty(self):
        """Registry div must NOT be emitted when basket_member_syms is empty."""
        html = _render_baskets([])
        assert "ftr-member-sym-registry" not in html


# Allocation primary-copy and progressive-disclosure contracts.
ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "allocation.html.j2"
SITE = ROOT / "site" / "allocation.html"


def _glance_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"<script\b.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<details\b.*?</details>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(html_lib.unescape(text).split())


def test_template_uses_plain_primary_section_names() -> None:
    src = TEMPLATE.read_text(encoding="utf-8")
    for phrase in (
        "Lower-risk option",
        "What to add or trim",
        "Theme leadership",
        "Leadership handoff",
        "Long-history check",
        "How Mastermind AI uses this page",
        "Emerging themes",
    ):
        assert phrase in src
    for old in (
        "Optional de-risk overlay",
        "Buy & sell entries — the playbook",
        "Narrative lifecycle board",
        "What is actually validated — sector backtest",
        "AI desk guardrails",
        "Candidate themes — discovery radar",
    ):
        assert old not in src


def test_theme_table_keeps_quant_receipts_off_the_glance_columns() -> None:
    src = TEMPLATE.read_text(encoding="utf-8")
    start = src.index("<!-- ============ 02")
    end = src.index("<!-- ============ 03", start)
    board = src[start:end]
    assert ">Hurst<" not in board
    assert "{{ t('Score', '评分') }}" not in board
    assert "zfmt(cr.crowding_z)" in board  # retained only as a tooltip receipt
    assert "t('Crowded','拥挤')" in board
    assert "t('Normal','正常')" in board


def test_long_history_details_keep_machine_statistics_behind_click() -> None:
    src = TEMPLATE.read_text(encoding="utf-8")
    start = src.index("<!-- ============ 04")
    end = src.index("<!-- ============ 05", start)
    history = src[start:end]
    assert '<details class="study-details">' in history
    assert "See long-history evidence" in history
    assert "Test strength" in history
    assert "DSR" in history  # exact receipt still exists inside disclosure
    assert "B.verdict[k]" not in history
    for raw in ("validated_risk_control", "display_only", "modest_or_none", "no_basket_drawdown_edge"):
        assert raw not in history


def test_ai_rules_are_human_copy_not_raw_contract_fields() -> None:
    src = TEMPLATE.read_text(encoding="utf-8")
    start = src.index("<!-- ============ 05")
    end = src.index("<!-- live desk", start)
    ai = src[start:end]
    for raw_expr in ("A.overall_verdict", "A.reader_contract", "A.do_not_conclude", "A.ai_directive"):
        assert raw_expr not in ai
    assert '<details class="panel study-details ai-use">' in ai


def test_committed_allocation_glance_has_no_machine_language() -> None:
    text = _glance_text(SITE)
    for required in (
        "Lower-risk option",
        "Theme leadership",
        "Leadership handoff",
        "Long-history check",
        "Emerging themes",
    ):
        assert required in text
    for banned in (
        "DSR",
        "Hurst",
        "validated_risk_control",
        "display_only",
        "discipline_not_prediction",
        "rank-IC",
        "z 1.91",
        "What is actually validated",
    ):
        assert banned not in text

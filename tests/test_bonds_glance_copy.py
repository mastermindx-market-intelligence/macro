"""Bonds keeps freshness and calibration language truthful and reader-first."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "bonds.html.j2"
SITE = ROOT / "site" / "bonds.html"


def _src() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def test_bonds_hero_uses_snapshot_not_live_badge() -> None:
    src = _src()
    assert "dtp-chip--live" not in src
    assert ">LIVE<" not in src
    assert "Latest bond snapshot" in src
    assert "最新债券快照" in src
    assert "dtp-chip--snapshot" in src


def test_backtest_summary_uses_reader_language() -> None:
    src = _src()
    assert "{{ t('Measured', '已校准') }}" not in src
    assert "{{ t('Backtested', '历史回测') }}" in src
    assert "Recession-IC" not in src
    assert "衰退IC" not in src
    assert "Historical recession ordering" in src
    assert "历史衰退排序" in src
    assert "top-stress readings were followed by a 10%+ S&P drawdown" in src


def test_jargon_heavy_section_titles_are_plain() -> None:
    src = _src()
    for required in (
        "Credit — early stress signal",
        "Stress & funding · the stock-bond hedge",
        "Rates volatility & funding stress",
        "Global credit cycle — leverage risk (BIS)",
    ):
        assert required in src
    for banned in (
        'Credit — the "smart money" canary',
        "Stress & plumbing",
        "Rates volatility & funding plumbing",
        "crisis early-warning",
    ):
        assert banned not in src


def test_supply_and_timeline_use_product_language_not_scoring_internals() -> None:
    src = _src()
    assert "Supply context only; not scored." not in src
    assert "Supply context only; does not affect the bond-health score." in src
    assert "Daily state changes, debounced to reduce whipsaw. Context only." not in src
    assert "Daily state changes with repeat flips filtered out. Context only." in src


def test_calibration_tooltip_is_plain_and_keeps_audit_detail() -> None:
    src = _src()
    start = src.index("Historical recession ordering")
    snippet = src[start:start + 1200]
    assert "rank correlation" not in snippet
    assert "1.0 = perfect ordering" not in snippet
    assert "sample window" in snippet.lower()
    assert "observations" in snippet.lower()


def test_committed_bonds_page_matches_contract() -> None:
    html = SITE.read_text(encoding="utf-8")
    for required in (
        "Latest bond snapshot",
        "Backtested",
        "Historical recession ordering",
        "Credit — early stress signal",
        "Rates volatility &amp; funding stress",
        "Global credit cycle — leverage risk (BIS)",
        "Supply context only; does not affect the bond-health score.",
    ):
        assert required in html
    for banned in (
        ">LIVE<",
        "Recession-IC",
        "Credit — the &#34;smart money&#34; canary",
        "funding plumbing",
        "crisis early-warning",
        "Supply context only; not scored.",
    ):
        assert banned not in html


def test_committed_bonds_stylesheet_is_fingerprinted() -> None:
    import hashlib
    import re

    from jinja2 import Environment, StrictUndefined

    from scripts.build_bonds import C

    blocks = re.findall(r"<style\b[^>]*>(.*?)</style>", _src(), re.IGNORECASE | re.DOTALL)
    source_css = next(block for block in blocks if ".dtp-chip--snapshot" in block)
    rendered_css = Environment(
        autoescape=True,
        keep_trailing_newline=True,
        undefined=StrictUndefined,
    ).from_string(source_css).render(C=C)
    digest = hashlib.sha256(rendered_css.encode("utf-8")).hexdigest()[:8]

    html = SITE.read_text(encoding="utf-8")
    refs = re.findall(r"assets/css/([0-9a-f]{8})\.css\?v=\1", html)
    assert digest in refs
    css = ROOT / "site" / "assets" / "css" / f"{digest}.css"
    assert css.is_file()
    assert hashlib.sha256(css.read_bytes()).hexdigest()[:8] == digest
    text = css.read_text(encoding="utf-8")
    assert text == rendered_css
    assert ".dtp-chip--snapshot" in text
    assert ".dtp-chip--live" not in text

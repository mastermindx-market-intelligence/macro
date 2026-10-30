"""Bonds keeps freshness and calibration language truthful and reader-first."""
from __future__ import annotations

from pathlib import Path

import re
import runpy

import numpy as np
import pandas as pd
import pytest
from jinja2 import Environment, FileSystemLoader

from engine import bonds
from scripts import build_bonds

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


# Producer-to-visible-driver coverage for missing rates and their recovery.
def _pipeline(monkeypatch, rates=None):
    # Store absence is an explicit supported producer condition. Prevent unrelated
    # local calibration/store data from influencing this deterministic fixture.
    monkeypatch.setattr(bonds.store, "read", lambda *args, **kwargs: None)
    frame = pd.DataFrame(
        {"hy_oas": 3.0, "move": 90.0, **(rates or {})},
        index=pd.bdate_range("2024-01-01", periods=600),
    )
    health = bonds.bonds_frame(frame)
    assert not health.empty and "health_score" in health
    snapshot = bonds.bonds_snapshot(frame, health)
    vm = build_bonds._vm(snapshot, health)
    hero = build_bonds._hero_pack(vm, "Oct 9, 2026", snapshot["cycle_phase"])
    glance = build_bonds._glance(vm)
    base_ctx = runpy.run_path(str(ROOT / "tests/test_bonds_divergence_gate.py"))["_base_ctx"]
    ctx = base_ctx(vm=vm, hero=hero, glance=glance)
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True)
    html = env.get_template("bonds.html.j2").render(**ctx)
    driver = re.search(
        r'<div class="panel" id="curve">.*?<p class="drv-read">(.*?)</p>',
        html, re.S,
    )
    assert driver is not None, "The assertion must inspect the actual visible curve driver"
    return snapshot, hero, glance[0], driver.group(1), html


@pytest.mark.parametrize("rates", [{}, {"spread_2s10s": np.nan, "spread_10y3m": np.nan, "curve_tp_adj": np.nan}])
def test_absent_rates_stay_unavailable_in_visible_curve_driver(monkeypatch, rates):
    snapshot, hero, curve, driver, _ = _pipeline(monkeypatch, rates)
    assert snapshot["pillars"]["curve"]["spread_2s10s"] is None
    assert snapshot["pillars"]["curve"]["inverted"] is None
    assert "not readable yet" in hero["clause_en"]
    assert curve["state_en"] == "Unavailable"
    assert curve["state_zh"] == "暂不可用"
    assert curve["sev"] == "gl-mid"
    assert '<span class="l-en">Unavailable</span>' in driver
    assert '<span class="l-zh">暂不可用</span>' in driver
    assert "Flat" not in driver and "平坦" not in driver


@pytest.mark.parametrize("spread, expected_en, expected_zh", [
    (0.0, "Flat", "平坦"), (0.15, "Flat", "平坦"),
    (0.16, "Normal", "正常"), (0.99, "Normal", "正常"),
    (1.0, "Steep", "陡峭"), (1.5, "Steep", "陡峭"),
])
def test_observed_spreads_preserve_existing_thresholds(monkeypatch, spread, expected_en, expected_zh):
    _, _, curve, driver, _ = _pipeline(monkeypatch, {"spread_2s10s": spread})
    assert curve["state_en"] == expected_en
    assert curve["state_zh"] == expected_zh
    assert f'<span class="l-en">{expected_en}</span>' in driver
    assert "Unavailable" not in driver


@pytest.mark.parametrize("rates", [
    {"spread_10y3m": -0.3},
    {"curve_tp_adj": -0.3},
    {"spread_10y3m": -0.3, "spread_2s10s": 1.5},
])
def test_observed_inversion_keeps_precedence(monkeypatch, rates):
    _, hero, curve, driver, _ = _pipeline(monkeypatch, rates)
    assert curve["state_en"] == "Inverted"
    assert curve["state_zh"] == "倒挂"
    assert "inverted" in hero["clause_en"]
    assert '<span class="l-en">Inverted</span>' in driver


def test_recovery_and_loss_do_not_retain_a_prior_curve_state(monkeypatch):
    observed = []
    for rates in ({}, {"spread_2s10s": 0.0}, {}, {"spread_2s10s": 1.5}):
        _, _, curve, _, _ = _pipeline(monkeypatch, rates)
        observed.append(curve["state_en"])
    assert observed == ["Unavailable", "Flat", "Unavailable", "Steep"]

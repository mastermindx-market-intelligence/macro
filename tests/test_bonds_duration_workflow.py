"""Repository-route checks for the Paper R11 duration workflow; no market/data writes."""
from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
PARTIAL = TEMPLATES / "_bonds_duration.html.j2"
SCRIPT = TEMPLATES / "_bonds_duration.mjs.j2"


def _partial() -> str:
    assert PARTIAL.is_file(), "The real Bonds route needs its duration review partial"
    return Environment(loader=FileSystemLoader(TEMPLATES), autoescape=True,
                       undefined=StrictUndefined).get_template(PARTIAL.name).render()


def test_bonds_route_reaches_one_drawer_and_its_controller() -> None:
    source = (TEMPLATES / "bonds.html.j2").read_text()
    assert source.count('{% include "_bonds_duration.html.j2" %}') == 1
    assert source.count('{% include "_bonds_duration.mjs.j2" %}') == 1
    assert 'data-duration-open' in source
    assert source.index('data-duration-open') > source.index('id="real"')
    assert source.index('data-duration-open') < source.index('id="stress"')


def test_no_javascript_means_no_fabricated_result_or_enabled_calculator() -> None:
    html = _partial()
    assert 'data-duration-input' in html and 'disabled' in html
    assert '<noscript>' in html
    assert 'JavaScript' in html and '市场解读不受影响' in html
    assert '−$250' not in html and '−$740' not in html
    assert html.count('data-duration-value') == 2
    assert html.count('data-duration-empty') == 2
    assert 'Not calculated' in html and '未计算' in html


def test_examples_cannot_masquerade_as_sourced_positions() -> None:
    html = _partial()
    assert 'data-duration-origin="illustrative"' in html
    assert html.count('data-position-value="10000"') == 2
    assert 'data-position-id="example-intermediate"' in html
    assert 'data-position-id="example-long"' in html
    assert 'data-modified-duration="5.0"' in html
    assert 'data-modified-duration="14.8"' in html
    assert 'modified duration' in html and '修正久期' in html
    assert 'not live holdings' in html and '并非实际持仓' in html
    assert 'convexity' in html and '凸性' in html
    assert 'not an accuracy guarantee' in html and '不保证估算精度' in html


def test_native_dialog_has_named_controls_and_early_correction_region() -> None:
    html = _partial()
    assert '<dialog ' in html and 'aria-labelledby="duration-title"' in html
    assert 'aria-describedby="duration-scope"' in html
    assert html.count('data-duration-close') == 2
    assert 'data-duration-edit' in html and 'data-duration-reset' in html
    assert 'type="text"' in html and 'inputmode="decimal"' in html
    assert 'type="range"' in html
    assert 'role="status"' in html and 'aria-atomic="true"' in html
    assert html.index('data-duration-error') < html.index('data-duration-row')
    assert 'data-duration-error-en' in html and 'data-duration-error-zh' in html
    assert 'title=' not in html


def test_styling_is_scoped_dual_theme_and_uses_existing_tokens() -> None:
    html = _partial()
    css = re.search(r'<style>(.*?)</style>', html, re.S).group(1)
    assert ':root' not in css
    assert not re.search(r'#[0-9a-fA-F]{3,8}\b', css)
    assert 'style.textContent' not in html
    assert 'data-theme="light"' in css
    assert 'prefers-reduced-motion' in css
    assert 'safe-area-inset-bottom' in css
    assert 'max-height' in css and 'overflow-y' in css
    assert 'var(--font-ui)' in css and 'var(--line)' in css


def test_controller_behavior_on_the_unmodified_production_module() -> None:
    assert SCRIPT.is_file(), "Production duration controller is missing"
    node = shutil.which('node')
    assert node, "Node is required to verify the served duration controller"
    completed = subprocess.run([node, '--test', str(ROOT / 'tests' / 'bonds_duration_workflow.test.mjs')],
                               cwd=ROOT, capture_output=True, text=True, timeout=45)
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_full_bonds_template_renders_with_existing_owner_fixture() -> None:
    assert PARTIAL.is_file(), "Duration include must exist before route verification"
    path = ROOT / 'tests' / 'test_bonds_divergence_gate.py'
    spec = importlib.util.spec_from_file_location('bonds_duration_route_fixture', path)
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    context = fixture._base_ctx()
    before = repr(context['vm'])
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=True)
    html = env.get_template('bonds.html.j2').render(**context)
    assert html.count('id="bonds-duration-dialog"') == 1
    assert 'data-duration-open' in html and 'mountDurationWorkflow' in html
    assert '<script type="module">' in html
    assert repr(context['vm']) == before
    assert 'id="real"' in html and 'id="stress"' in html and 'id="corpcredit"' in html
    assert html.index('data-duration-open') < html.index('id="stress"')


def test_slider_does_not_round_a_valid_fractional_text_shock() -> None:
    # 0.0137 bp is valid in R11. A 0.01 range step would silently round its handle.
    html = _partial()
    slider = re.search(r'<input[^>]+data-duration-slider[^>]*>', html).group(0)
    assert 'step="any"' in slider


def test_existing_page_writer_and_asset_sweep_preserve_the_served_controller(tmp_path, monkeypatch) -> None:
    """Exercise real production rendering/writing/postprocessing against temporary output only."""
    import hashlib
    from lib import pages
    from scripts.externalize_css import externalize

    fixture_path = ROOT / 'tests' / 'test_bonds_divergence_gate.py'
    spec = importlib.util.spec_from_file_location('bonds_duration_pipeline_fixture', fixture_path)
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=True)
    rendered = env.get_template('bonds.html.j2').render(**fixture._base_ctx())
    site = tmp_path / 'site'
    site.mkdir()
    # The existing shim owner is directed to test output, never the sparse production tree.
    monkeypatch.setattr(pages, '_site_root', lambda: site)
    monkeypatch.setattr(pages, '_shim_checked', False)
    output = site / 'bonds.html'
    pages.write_page(output, rendered, encoding='utf-8')
    externalize(site)
    served = output.read_text()
    assert served.count('id="bonds-duration-dialog"') == 1
    module = re.search(r'<script type="module">(.*?)</script>', served, re.S)
    assert module, 'Postprocessing must not drop module semantics or its include'
    assert module.group(1).strip() == SCRIPT.read_text().strip()
    refs = re.findall(r'assets/css/([0-9a-f]{8})\.css\?v=\1', served)
    duration_css = []
    for digest in refs:
        path = site / 'assets' / 'css' / f'{digest}.css'
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest()[:8] == digest
        if b'.bonds-duration-dialog' in raw:
            duration_css.append(raw.decode())
    assert len(duration_css) == 1
    assert 'data-theme="light"' in duration_css[0]
    assert 'prefers-reduced-motion' in duration_css[0]
    assert 'data-duration-input' in served and 'step="any"' in served
    assert f'<script {pages.DBASE_MARKER}' in served

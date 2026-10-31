#!/usr/bin/env python3
"""Render the INTL-GS W2F evidence site: the real intl.html (render_fixture
seam, real attach_surveillance) and the state-matrix fixture page.

CLI:
    python3 tests/intl_gs_fixture_site.py --out <dir> [--stub-coverage]
    python3 tests/intl_gs_fixture_site.py --print-html [--stub-coverage]

``--stub-coverage`` injects a TEST-ONLY builder module + view template (never
committed to lib/ or templates/intl_workspace/) so exactly the coverage tab is
available — the browser proof (tests/intl_gs_foundation_browser.test.cjs) and
pytest 2.6 use it to exercise the mount seam end to end. Importable: render_intl_page /
render_states_page are used by tests/test_intl_gs_foundation.py.
"""
import argparse
import json
import shutil
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader  # noqa: E402

from engine import i18n  # noqa: E402
from engine.intl_workspace_overview import build_workspace_overviews as _workspace_overviews  # noqa: E402
from lib.intl_gs_display import horizon_label, snapshot_display  # noqa: E402
from lib.intl_library_mount import render_international_pages  # noqa: E402
from lib.intl_surveillance_mount import attach_surveillance  # noqa: E402

STUB_MODULE = "lib.intl_gs_coverage_view"
STUB_TEMPLATE = "intl_workspace/coverage.html.j2"

# Test-only stub view: opens with the production gs_panel_root contract so
# panelValid() accepts it, and shows no market number (L10). The market demo
# block sits AFTER the panel root (still inside .intl-gs) so the X6 market
# selection seam stays visible from every view, exactly like the scanner-row
# market links the later lanes ship.
STUB_COVERAGE_HTML = """{% import "intl_workspace/_gs_macros.html.j2" as gs %}
{% call gs.gs_panel_root(view='coverage', panel=gs_panel) %}
{{ gs.gs_bandhead(t('Coverage and data states', '覆盖与数据状态'), qnum=t('Coverage stub', '覆盖占位'), sub=t('Test-only stub for the W2F foundation seam.', 'W2F 基础接缝的测试专用占位视图。'), clock=t('21 Oct 08:00 UTC', '10月21日 08:00 UTC')) }}
{{ gs.gs_specimen_chip() }}
<p class="intl-gs__footnote">{{ t('Stub panel: no production view is shipped by this packet. IM13 lands the real coverage board.', '占位面板：本包不投产任何视图。真实覆盖面板由 IM13 落地。') }}</p>
{% endcall %}
<section class="intl-gs__panel" aria-labelledby="intl-gs-market-selection">
  {{ gs.gs_bandhead(t('Market selection', '市场选择'), sub=t('Foundation seam: select a market, the scope follows.', '基础接缝：选择市场后范围随之切换。'), id='intl-gs-market-selection') }}
  <div class="intl-gs__demorow">
    <div data-gs-market-row="JP">{{ gs.gs_state_cell('qualified', t('Japan', '日本'), 0.42, '%', t('Proxy basis', '代理口径'), t('21 Oct 08:00 UTC', '10月21日 08:00 UTC'), reason=t('Thin session', '成交清淡'), dir='up') }} <a class="intl-gs__chip intl-gs__chip--link" href="?view=coverage&amp;market=JP" data-gs-select-market="JP" data-gs-open="coverage">{{ t('Select Japan', '选择日本') }}</a></div>
    <div data-gs-market-row="KR">{{ gs.gs_state_cell('complete', t('Korea', '韩国'), -0.86, '%', t('USD · Unhedged', '美元 · 未对冲'), t('21 Oct 08:00 UTC', '10月21日 08:00 UTC'), dir='down') }} <a class="intl-gs__chip intl-gs__chip--link" href="?view=coverage&amp;market=KR" data-gs-select-market="KR" data-gs-open="coverage">{{ t('Select Korea', '选择韩国') }}</a></div>
  </div>
  <div data-gs-market-scope>
    <div data-gs-market="JP" data-gs-market-default><p class="intl-gs__footnote">{{ t('Japan scope stub: shows only while JP is selected.', '日本范围占位：仅在选中 JP 时显示。') }}</p></div>
    <div data-gs-market="KR" hidden><p class="intl-gs__footnote">{{ t('Korea scope stub: shows only while KR is selected.', '韩国范围占位：仅在选中 KR 时显示。') }}</p></div>
  </div>
</section>
"""


def _stub_module():
    module = types.ModuleType(STUB_MODULE)
    module.__doc__ = "Test-only coverage builder injected by intl_gs_fixture_site."

    def build_view(*, universe, rights, contexts, workspace, observations=None):
        return [dict(view="coverage", context_id="im-gs-coverage", context={},
                     generation=None, payload={"stub": True})]

    module.build_view = build_view
    return module


def _env(extra=None):
    loader = FileSystemLoader(str(ROOT / "templates"))
    if extra:
        loader = ChoiceLoader([DictLoader(extra), loader])
    env = Environment(loader=loader, autoescape=False)
    env.globals.update(t=i18n.t, tr=i18n.tr, td=i18n.td)
    return env


def _vm():
    summary = {"n": 0, "dominant_quad": "unknown", "recession_watch": 0, "drawdown_watch": 0}
    vm = {"latest": {"date": "fixture", "records": [], "summary": summary},
          "built": "fixture", "records": [], "summary": summary, "rankings": {},
          "heatmap": [], "periphery": None, "sector_board": [], "setups": {},
          "global_regime_html": '<section id="fixture-owner-fragment">Existing research</section>'}
    vm["intl_workspace"] = _workspace_overviews(None)
    return vm


def render_intl_page(*, include_surveillance=True, stub_coverage=False):
    """The real intl.html via the render_fixture seam (no data I/O)."""
    vm = _vm()
    overlay = {}
    injected = False
    if stub_coverage:
        sys.modules[STUB_MODULE] = _stub_module()
        injected = True
        overlay[STUB_TEMPLATE] = STUB_COVERAGE_HTML
    try:
        if include_surveillance:
            vm["intl_workspace"] = attach_surveillance(vm["intl_workspace"])
        catalogue = json.loads((ROOT / "config/intl_library_catalogue.json").read_text(encoding="utf-8"))
        pages = render_international_pages(_env(overlay).get_template("intl.html.j2"), vm, catalogue=catalogue)
        return pages[0]
    finally:
        if injected:
            sys.modules.pop(STUB_MODULE, None)


def _fixture_snapshot_context():
    """FX1/FX5: the fixture's two snapshot variants + the horizon vocabulary,
    composed through the SAME lib.intl_gs_display path the mount uses
    (snapshot_display over the raw clock literals; horizon_label over the
    workspace config horizons). The fixture template holds no hand-typed
    clock display string."""
    raw_populated = {
        basis: {"clocks": {
            "observation": "2026-10-07",
            "source_publication": "2026-10-09T15:00:00+00:00",
            "ingestion": "2026-10-09T15:00:00+00:00",
            "computation": "2026-10-09T20:30:00+00:00"},
            "qualified": 35, "total": 35}
        for basis in ("local", "usd_unhedged")}
    raw_populated["usd_hedged"] = {"clocks": {
        "observation": None, "source_publication": None,
        "ingestion": None, "computation": None}, "qualified": 0, "total": 35}
    no_clocks = {"clocks": {
        "observation": None, "source_publication": None,
        "ingestion": None, "computation": None}, "qualified": 0, "total": 0}
    raw_withheld = {basis: dict(no_clocks) for basis in ("local", "usd_unhedged", "usd_hedged")}
    horizons = _workspace_overviews(None)["config"]["horizons"]
    en, zh = horizon_label("1m")
    return {
        "snapshot_populated": snapshot_display(raw_populated),
        "snapshot_withheld": snapshot_display(raw_withheld),
        "horizon": {"id": "1m", "en": en, "zh": zh},
        "horizon_options": [
            {"value": horizon, "label": i18n.t(*horizon_label(horizon))}
            for horizon in horizons],
    }


def render_states_page():
    """Minimal fixture document: html[data-theme][data-lang] + theme.css +
    intl_workspace.css + intl_workspace_surveillance.css + theme.js, no site
    nav, everything wrapped in one .intl-gs scope (spec §10.8). The wrapper
    carries test-only presentation scaffolding: the fixture page opts out of
    the site-wide ambient aurora backdrop (VF1 — a specimen board reads on a
    plain --bg canvas) and reserves bottom space under the copilot launcher
    (VF13). Production pages never see this style block."""
    template = _env().from_string(
        '<!DOCTYPE html>\n'
        '<html lang="en" data-theme="dark">\n'
        '<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<title>INTL-GS state matrix fixture</title>\n'
        '<link rel="stylesheet" href="theme.css">\n'
        '<link rel="stylesheet" href="intl_workspace.css">\n'
        '<link rel="stylesheet" href="intl_workspace_surveillance.css">\n'
        '<style>/* fixture-only scaffolding (VF1): plain canvas, no aurora */\n'
        'html,body{background:var(--bg);background-image:none;}\n'
        'html body::before{content:none;}\n'
        '</style>\n'
        '<script defer src="theme.js"></script>\n'
        '</head>\n'
        '<body>\n'
        '<div class="intl-gs intl-gs--fixture">\n'
        "{% include 'intl_workspace/_gs_state_fixture.html.j2' %}\n"
        '</div>\n'
        '</body>\n'
        '</html>\n')
    return template.render(**_fixture_snapshot_context())


def write_site(out_dir, *, stub_coverage=False):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "intl.html").write_text(render_intl_page(stub_coverage=stub_coverage), encoding="utf-8")
    (out / "intl-gs-states.html").write_text(render_states_page(), encoding="utf-8")
    copied = 0
    for pattern in ("*.css", "*.js"):
        for asset in (ROOT / "templates").glob(pattern):
            shutil.copy2(asset, out / asset.name)
            copied += 1
    # VF16: the production site build serves the Inter faces and the live
    # config beside the pages; the fixture site must serve them too so both
    # evidence manifests record zero console errors and zero failed requests.
    fonts = out / "fonts"
    fonts.mkdir(exist_ok=True)
    for font in (ROOT / "templates" / "fonts").glob("*.woff2"):
        shutil.copy2(font, fonts / font.name)
        copied += 1
    live_config = ROOT / "templates" / "live_config.js"
    if live_config.is_file():
        shutil.copy2(live_config, out / "live_config.js")
        copied += 1
    else:
        (out / "live_config.js").write_text(
            "/* fixture stub: no live configuration on the evidence site */\n",
            encoding="utf-8")
        copied += 1
    return copied


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", help="write <out>/intl.html, <out>/intl-gs-states.html and templates assets")
    parser.add_argument("--stub-coverage", action="store_true", help="test-only stub coverage view (pytest 2.6 / browser proof)")
    parser.add_argument("--print-html", action="store_true", help="print the rendered intl.html to stdout")
    parser.add_argument("--print-states", action="store_true", help="print the rendered states fixture page to stdout")
    args = parser.parse_args(argv)
    if args.print_html:
        sys.stdout.write(render_intl_page(stub_coverage=args.stub_coverage))
    if args.print_states:
        sys.stdout.write(render_states_page())
    if args.out:
        copied = write_site(args.out, stub_coverage=args.stub_coverage)
        print(f"wrote {args.out}/intl.html, intl-gs-states.html + {copied} assets", file=sys.stderr)
    if not (args.out or args.print_html or args.print_states):
        parser.error("nothing to do: pass --out, --print-html and/or --print-states")


if __name__ == "__main__":
    main()

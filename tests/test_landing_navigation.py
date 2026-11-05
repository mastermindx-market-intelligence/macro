"""Landing information-architecture, brand, and disclosure-nav contracts."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HTML_PATHS = (ROOT / "templates" / "index.html", ROOT / "site" / "index.html")
CSS_PATHS = (
    ROOT / "templates" / "landing.css",
    ROOT / "site" / "landing.css",
)


def _primary_nav(text: str) -> str:
    start = text.index('<nav class="nav"')
    end = text.index("</nav>", start)
    return text[start:end]


@pytest.mark.parametrize("path", HTML_PATHS)
def test_landing_uses_mastermindx_entity_name(path: Path):
    text = path.read_text(encoding="utf-8")
    assert "<title>MastermindX " in text
    assert '<meta property="og:site_name" content="MastermindX">' in text
    assert '"@type":"Organization","name":"MastermindX"' in text
    assert '"@type":"WebSite","name":"MastermindX"' in text
    assert "MASTERMINDX" in _primary_nav(text)


@pytest.mark.parametrize("path", HTML_PATHS)
def test_primary_nav_has_three_accessible_disclosures(path: Path):
    nav = _primary_nav(path.read_text(encoding="utf-8"))
    triggers = re.findall(
        r'<button class="nav-trigger" id="([^"]+)"[^>]+'
        r'aria-expanded="false" aria-controls="([^"]+)"',
        nav,
    )
    assert len(triggers) == 3
    assert len({trigger_id for trigger_id, _ in triggers}) == 3
    assert len({panel_id for _, panel_id in triggers}) == 3
    for trigger_id, panel_id in triggers:
        panel_match = re.search(
            rf'<div class="nav-panel[^"]*" id="{re.escape(panel_id)}" '
            rf'aria-labelledby="{re.escape(trigger_id)}" hidden>.*?</div>\s*</div>',
            nav,
            flags=re.S,
        )
        assert panel_match
        assert 'role="menu"' not in panel_match.group(0)
        assert 'role="menuitem"' not in panel_match.group(0)


@pytest.mark.parametrize("path", HTML_PATHS)
def test_primary_nav_links_only_to_real_destinations(path: Path):
    nav = _primary_nav(path.read_text(encoding="utf-8"))
    for href in (
        "products/index.html",
        "products/market-terminal.html",
        "products/mastermind-ai.html",
        "products/market-dashboards.html",
        "https://www.mastermind-x.com/research_vault.html",
        "stocks/index.html",
        "tools/index.html",
        "learn/index.html",
        "blog/index.html",
        "support.html",
        "plans.html",
    ):
        assert f'href="{href}"' in nav
    assert 'href="#ai"' not in nav
    assert 'href="#pricing"' not in nav


@pytest.mark.parametrize("path", HTML_PATHS)
def test_mobile_toggle_and_existing_account_actions_remain(path: Path):
    nav = _primary_nav(path.read_text(encoding="utf-8"))
    assert (
        'id="nav-toggle" type="button" aria-expanded="false" '
        'aria-controls="primary-navigation"'
    ) in nav
    assert 'id="nav-login"' in nav
    assert 'href="https://app.mastermind-x.com/terminal?signin=1"' in nav
    assert 'id="nav-cta"' in nav
    assert 'href="https://app.mastermind-x.com/terminal?signup=1"' in nav
    assert 'id="gear-btn"' in nav


@pytest.mark.parametrize("path", HTML_PATHS)
def test_navigation_script_supports_keyboard_and_outside_close(path: Path):
    text = path.read_text(encoding="utf-8")
    controller = text[text.index("const MMX_NAV"):text.index("/* ───── nav settings")]
    for behavior in ("ArrowDown", "ArrowUp", "Escape", "pointerdown", "focusout"):
        assert behavior in controller
    assert "aria-expanded" in controller
    assert "panel.hidden" in controller
    assert "matchMedia('(max-width: 900px)')" in controller


def test_landing_plain_copy_pairs_match():
    assert HTML_PATHS[0].read_bytes() == HTML_PATHS[1].read_bytes()
    assert CSS_PATHS[0].read_bytes() == CSS_PATHS[1].read_bytes()


@pytest.mark.parametrize("path", HTML_PATHS)
def test_chinese_hero_uses_optically_centered_authored_lines(path: Path):
    text = path.read_text(encoding="utf-8")
    start = text.index('<h1 data-adtest-slot="hero_headline"')
    hero = text[start:text.index("</h1>", start)]
    data_zh = re.search(r'data-zh="([^"]+)"', hero)
    assert data_zh
    assert data_zh.group(1).count("zh-line-punct") == 2

    cfg_start = text.index('<script type="application/json" id="mm-adtest">')
    cfg_start = text.index(">", cfg_start) + 1
    cfg = json.loads(text[cfg_start:text.index("</script>", cfg_start)])
    for arm in cfg["arms"]:
        zh = arm["copy"]["hero_headline"]["zh"]
        if "。" in zh:
            assert "zh-line-punct" in zh

    css = CSS_PATHS[0].read_text(encoding="utf-8")
    assert 'html[data-lang="zh"] .cov-copy h1 .zh-line{' in css
    assert 'html[data-lang="zh"] .cov-copy h1 .zh-line-punct{' in css
    assert "transform:translateX(.26em)" in css


def test_mobile_navigation_css_is_an_in_flow_accordion():
    css = CSS_PATHS[0].read_text(encoding="utf-8")
    assert "@media (max-width:900px)" in css
    assert ".nav-links.open{display:flex}" in css
    assert ".nav-panel,.nav-panel-research,.nav-panel-resources{position:static" in css
    assert "max-height:calc(100dvh - 76px)" in css


# Pricing click-capture ownership regression (issue #8405).
# Keep with the existing landing navigation suite so CI's established job owns it.
ONBOARD_COPIES = ("templates/onboard.js", "site/onboard.js")

NODE_HARNESS = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const code = JSON.parse(fs.readFileSync(0, 'utf8'));
const signup = 'https://app.mastermind-x.com/terminal?signup=1';
const signin = 'https://app.mastermind-x.com/terminal?signin=1';
const cases = [
  {name:'free', href:signup, expected:1},
  {name:'paid_annual', href:signup+'&plan=pro&period=annual', expected:1},
  {name:'resume', href:signup+'&onboard=resume', expected:1},
  {name:'signin', href:signin, expected:1},
  {name:'already_claimed', href:signup, prevented:true, expected:0},
  {name:'middle_button', href:signup, button:1, expected:0},
  {name:'right_button', href:signup, button:2, expected:0},
  {name:'meta_key', href:signup, metaKey:true, expected:0},
  {name:'ctrl_key', href:signup, ctrlKey:true, expected:0},
  {name:'shift_key', href:signup, shiftKey:true, expected:0},
  {name:'alt_key', href:signup, altKey:true, expected:0},
  {name:'other_link', href:'https://app.mastermind-x.com/terminal?help=1', expected:0}
];
let count = 0;
for (const order of [['theme','onboard'], ['onboard','theme']]) {
 for (const c of cases) {
  const called = [];
  const handlers = [];
  const sandbox = {
    URLSearchParams,
    document: {addEventListener: (type, cb) => {
      if (type === 'click') handlers.push(cb);
    }},
    mmTerminalOn: () => true,
    terminalTarget: a => a && a.href.includes('/terminal?sign')
      ? {ticker:null, url:a.href} : null,
    openTerminal: (ticker, anchor, url) => called.push({kind:'terminal', url}),
    readMeCache: () => null,
    openSheet: (mode, opts) => called.push({kind:'macro', mode, opts}),
    normTier: tier => tier
  };
  vm.runInNewContext(code.intent, sandbox, {timeout:1000});
  for (const name of order) {
    vm.runInNewContext(code[name], sandbox, {timeout:1000});
  }
  assert.equal(handlers.length, 2, 'both shipping listeners were registered');
  for (let round=1; round<=2; round++) {
    const anchor = {href:c.href, getAttribute: key => key==='href'?c.href:null};
    const e = {
      button:c.button || 0,
      defaultPrevented:!!c.prevented,
      metaKey:!!c.metaKey, ctrlKey:!!c.ctrlKey,
      shiftKey:!!c.shiftKey, altKey:!!c.altKey,
      target:{closest: selector => {
        if (selector === 'a[href]') return anchor;
        if (selector.includes('app.mastermind-x.com/terminal?sign') &&
            c.href.includes('app.mastermind-x.com/terminal?sign')) return anchor;
        return null;
      }},
      preventDefault(){this.defaultPrevented=true;},
      stopPropagation(){this.stopped=true;}
    };
    // Same-node stopPropagation does not suppress other capture listeners.
    for (const handler of handlers) handler(e);
    assert.equal(called.length, round*c.expected,
      order.join('->')+' '+c.name+' round '+round);
    assert.equal(e.defaultPrevented, c.expected>0 || !!c.prevented);
    if (c.expected) {
      const call = called[called.length-1];
      assert.equal(call.kind, order[0] === 'theme' ? 'terminal' : 'macro');
      if (call.kind === 'macro') {
        if (c.name === 'paid_annual') {
          assert.equal(call.opts.plan, 'pro');
          assert.equal(call.opts.period, 'annual');
        }
        if (c.name === 'resume') assert.equal(call.opts.resume, true);
        if (c.name === 'signin') assert.equal(call.mode, 'signin');
      } else {
        assert.equal(call.url, c.href);
      }
    }
    count++;
  }
 }
}
console.log('capture event cases passed:', count);
"""


def _listener(src: str, marker: str) -> str:
    at = src.index(marker)
    start = src.rfind("document.addEventListener(", 0, at)
    assert start >= 0, "capture handler missing before marker"
    end = src.index("}, true);", at) + len("}, true);")
    return src[start:end]


@pytest.mark.parametrize("copy", ONBOARD_COPIES)
def test_one_consumer_per_pricing_signup_click(copy: str) -> None:
    if not shutil.which("node"):
        pytest.skip("node not installed")
    onboard = (ROOT / copy).read_text(encoding="utf-8")
    theme = (ROOT / "templates/theme.js").read_text(encoding="utf-8")
    start = onboard.index("function parseIntent(qs)")
    end = onboard.index("\n  // delegated listener:", start)
    payload = {
        "intent": onboard[start:end],
        "onboard": _listener(onboard, "var a = e.target.closest ? e.target.closest("),
        "theme": _listener(theme, "if (!mmTerminalOn() || e.defaultPrevented || e.button"),
    }
    proc = subprocess.run(
        ["node", "-e", NODE_HARNESS],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + "\n" + proc.stdout


def test_onboard_template_and_site_copies_stay_in_sync() -> None:
    assert (ROOT / ONBOARD_COPIES[0]).read_bytes() == (
        ROOT / ONBOARD_COPIES[1]
    ).read_bytes()


def test_pricing_and_landing_load_the_new_onboard_bytes() -> None:
    """Immutable CDN caching must not strand buyers on the old two-dialog script."""
    version = hashlib.sha256((ROOT / "site/onboard.js").read_bytes()).hexdigest()[:8]
    for rel in ("templates/index.html", "site/index.html", "site/plans.html"):
        html = (ROOT / rel).read_text(encoding="utf-8")
        assert f'onboard.js?v={version}' in html, f"stale onboard cache key: {rel}"

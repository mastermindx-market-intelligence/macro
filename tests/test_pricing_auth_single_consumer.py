"""Pricing CTA click ownership regression (issue #8405).

Run the shipping document-capture handlers together in both registration orders.
Unlike a guard-string assertion, this fails if either handler double-opens after
a sibling calls stopPropagation (which does not stop same-node listeners).
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
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

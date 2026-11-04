'use strict';
// Exercise the real Python producer through Chromium's HTML5 script tokenizer.
// This is a local transport fixture, not a served/authenticated product journey.
const {test, before, after} = require('node:test');
const assert = require('node:assert/strict');
const {spawnSync} = require('node:child_process');
const path = require('node:path');
const {chromium} = require('playwright');

const root = path.resolve(__dirname, '..');
const encoderFile = path.join(root, 'lib/intl_library_mount.py');
const python = process.env.PYTHON || 'python3';
const encoderProgram = `
import importlib.util, json, sys
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("_inert_encoder_under_test", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
json.dump([str(module.intl_inert_json(value)) for value in json.load(sys.stdin)], sys.stdout, ensure_ascii=False)
`;

function encode(values) {
  const run = spawnSync(python, ['-B', '-c', encoderProgram, encoderFile], {
    cwd: root, input: JSON.stringify(values), encoding: 'utf8',
    env: {...process.env, PYTHONDONTWRITEBYTECODE: '1'},
    timeout: 30000, maxBuffer: 8 * 1024 * 1024
  });
  assert.equal(run.status, 0, run.stderr || String(run.error || 'producer failed'));
  return JSON.parse(run.stdout);
}

let browser;
before(async () => {
  browser = await chromium.launch({headless: true,
    ...(process.env.PLAYWRIGHT_CHROMIUM_CHANNEL ? {channel: process.env.PLAYWRIGHT_CHROMIUM_CHANNEL} : {})});
});
after(async () => { await browser.close(); });

test('ordinary markup and every decoded character stay exact', () => {
  const value = {schema: 'intl-gs-market.v1', market_id: 'JP', default: true,
    markup: '<article data-source="a&b"><code> a  b\n\tc </code><pre> x  y\n z </pre></article>',
    text: '中文😀\u2028\u2029\u0000\r\n\t & \\"\'  two  spaces', literal: String.raw`\u003c`};
  const [encoded] = encode([value]);
  assert.ok(encoded.includes('<article'), 'non-hazard markup remains inert JSON string data');
  assert.deepEqual(JSON.parse(encoded), value);
});

test('HTML5 tokenizer keeps hostile nested carriers and exact source tuples intact', async () => {
  const hazards = [
    '</script><p id="breakout">bad</p><script>globalThis.__escaped = 1</script>',
    '</ScRiPt><p id="breakout">bad</p>', '</script\t>', '</SCRIPT\n>',
    '<!--<script></script>-->', '<!--<ScRiPt >x</sCrIpT> -->',
    '<!--', '<script', '</script', '<SCRIPTURE>', '</ScRiPture>',
    '<!--<script><!--</script>--></script>',
    '中文😀\u2028\u2029\u0000\r\n\t\\ " \' & <ordinary>'
  ];
  const inner = hazards.map((text, i) => ({schema: 'intl-gs-market.v1', market_id: 'JP', default: true,
    markup: '<article id="ctx-JP" data-gs-market="JP"><code> a  b\n\tc </code><p>' + text + '</p></article>',
    source_ref: 'receipt:exact/' + i, generation: 'generation:exact', text}));
  const encodedInner = encode(inner);
  const outer = encodedInner.map((body) => ({schema: 'intl-gs-deferred.v1', view: 'dossier',
    context_id: 'ctx', horizon: '3m', basis: 'local', generation: 'generation:exact', markets: ['JP'],
    markup: '<section id="ctx-dossier" data-im-panel><script type="application/json" data-im-gs-market-id="JP">' +
      body + '</script></section>'}));
  const encodedOuter = encode(outer);
  const page = await browser.newPage();
  let requests = 0;
  await page.route('**/*', (route) => { requests += 1; return route.abort(); });
  try {
    for (let i = 0; i < hazards.length; i += 1) {
      assert.equal(/<!--|<\/?script/i.test(encodedInner[i]), false);
      assert.equal(/<!--|<\/?script/i.test(encodedOuter[i]), false);
      await page.setContent('<!doctype html><meta charset="utf-8"><main><script id="outer" type="application/json">' +
        encodedOuter[i] + '</script><p id="after">after</p></main>');
      const actual = await page.evaluate(() => {
        const script = document.querySelector('#outer');
        const outerValue = JSON.parse(script.textContent);
        const template = document.createElement('template');
        template.innerHTML = outerValue.markup;
        const nested = template.content.querySelector('script[data-im-gs-market-id]');
        return {outerValue, innerValue: JSON.parse(nested.textContent),
          after: document.querySelector('#after')?.textContent,
          outerScripts: document.querySelectorAll('script').length,
          nestedScripts: template.content.querySelectorAll('script').length,
          breakout: document.querySelectorAll('#breakout').length + template.content.querySelectorAll('#breakout').length,
          executed: globalThis.__escaped || 0};
      });
      assert.deepEqual(actual.outerValue, outer[i], 'outer decoded bytes: case ' + i);
      assert.deepEqual(actual.innerValue, inner[i], 'nested decoded bytes: case ' + i);
      assert.equal(actual.after, 'after');
      assert.equal(actual.outerScripts, 1);
      assert.equal(actual.nestedScripts, 1);
      assert.equal(actual.breakout, 0);
      assert.equal(actual.executed, 0);
    }
    assert.equal(requests, 0, 'the tokenizer fixture performs no network request');
  } finally { await page.close(); }
});

test('negative control detects escaped/double-escaped script-state swallowing', async () => {
  // Closing-tag-only escaping misses entry into script double-escaped state.
  const unsafe = JSON.stringify({markup: '<!--<script>'}).replace(/<\/script/gi, '\\u003c/script');
  const [safe] = encode([{markup: '<!--<script>'}]);
  const page = await browser.newPage();
  try {
    await page.setContent('<script type="application/json">' + unsafe + '</script><p id="after">after</p>');
    assert.equal(await page.locator('#after').count(), 0, 'unsafe control swallows the following element');
    await page.setContent('<script type="application/json">' + safe + '</script><p id="after">after</p>');
    assert.equal(await page.locator('#after').count(), 1, 'the actual producer prevents tokenizer-state entry');
  } finally { await page.close(); }
});

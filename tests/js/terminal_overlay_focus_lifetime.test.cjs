// Reuse the incumbent fake-browser harness; this file owns the new review edge.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const harnessPath = path.resolve(__dirname, 'terminal_overlay_readiness.test.cjs');
const harness = fs.readFileSync(harnessPath, 'utf8').split("test('stalled navigation")[0]
  .replace('focus() {}', 'focus() { document.activeElement = this; }')
  .replace("root: () => document.getElementById('mm-terminal-overlay'),", "document, root: () => document.getElementById('mm-terminal-overlay'),");
const context = {require, __dirname:path.dirname(harnessPath),process,console,URL};
vm.createContext(context);vm.runInContext(harness+'\nthis.browser = browser;',context);
test('prior visual-ready focus cannot cross a close/reopen of the same warm desktop iframe', () => {
  const b = context.browser(), frame = b.open();
  b.message(frame, 'terminal:visual-ready');b.advance(900); // owns a delayed focus transfer
  b.close();const current = b.open('AAPL');assert.equal(current, frame);
  const back = b.root().querySelector('.mmto-back');assert.equal(b.document.activeElement, back);
  b.advance(180);assert.equal(b.document.activeElement, back);
  assert.equal(b.root().classList.contains('is-loading'), true);
});
test('confirmed current visual-ready still focuses its healthy iframe', () => {
  const b = context.browser(), frame = b.open();
  b.message(frame, 'terminal:visual-ready');b.advance(1080);assert.equal(b.document.activeElement, frame);
});

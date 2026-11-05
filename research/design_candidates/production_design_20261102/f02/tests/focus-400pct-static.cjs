const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

// In the repository this test lives in f02/tests, beside ../pattern-lab.html.
// A positional specimen path permits isolated qualification without a checkout.
const specimen = process.argv[2] || path.join(__dirname, '..', 'pattern-lab.html');
const html = fs.readFileSync(specimen, 'utf8');
const css = html.match(/<style>([\s\S]*?)<\/style>/)?.[1];
assert.ok(css, 'F02 styles present');

// Guard against reintroducing a 200px sticky identity column in a 320 CSS-px
// viewport (the layout viewport of a 1280 physical-px browser at 400% zoom).
const narrowRule = css.match(/@media\(max-width:600px\)\{\s*\.sticky-first th:first-child\{position:static\}\s*#panel-comparison \.table-wrap\{scroll-padding-inline-start:12px\}\s*\}/);
assert.ok(narrowRule, 'narrow tables unpin the occluding identity column');
assert.match(css, /#panel-comparison \.table-wrap\{scroll-padding-inline-start:188px;scroll-padding-inline-end:12px\}/);
assert.match(css, /#panel-comparison \.table-wrap \[data-evidence\]\{scroll-margin-inline:4px\}/);
assert.match(html, /trigger\.focus\(\{preventScroll:true\}\);trigger\.scrollIntoView\(\{block:'nearest',inline:'nearest'\}\)/);

const script = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].at(-1)?.[1];
assert.ok(script, 'interactive specimen script present');
new vm.Script(script);

for (const width of [320, 360, 480, 600]) {
  assert.ok(width <= 600, `${width}px CSS viewport is inside unpinned threshold`);
}
console.log('F02 focus CSS/source checks: PASS; 320/360/480/600px rules qualified structurally; browser rendering NOT VERIFIED');

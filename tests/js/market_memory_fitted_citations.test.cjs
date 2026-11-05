'use strict';
// Actual gateway-produced identities arrive on stdin; no hand-invented positive wire.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync('templates/mm_brain.js', 'utf8');
assert.equal(source, fs.readFileSync('site/mm_brain.js', 'utf8'));
const {links, saved_sources, catalogs} = JSON.parse(fs.readFileSync(0, 'utf8'));
assert.ok(links.length > 1);
const begin = source.indexOf('  /* BEGIN retained source citation parser');
const end = source.indexOf('  function showUpgrade(d) {', begin);
const ctx = {ANCHOR: 'top'};
vm.runInNewContext(source.slice(begin, end), ctx);
for (const link of links) {
  assert.equal(ctx.retainedSourceCitation(link), null); // old 9-key protocol is separate
  assert.equal(ctx.savedSourceCitation(link).href, link);
  assert.equal(ctx.citeToPage(link), link);
  const u = new URL(link);
  assert.equal(u.searchParams.get('mm_context'), u.searchParams.get('mm_source_context'));
  for (const bad of [link + '&mm_mode=saved', link + '&mm_method=unexpected',
      link + '#source', link.replace('https:', 'http:'), link.replace('.com/', '.com.evil/'),
      link.replace('.com/', '.com:443/'), link.replace('https://', 'https://user@'),
      link.replace('saved', 'current'), link.replace('mm_cutoff=', 'unknown='),
      link.replace('T11:00:00.000000Z', 'T25:00:00Z'), link + '%20']) {
    assert.equal(ctx.savedSourceCitation(bad), null, bad);
  }
}
const altered = new URL(links[0]);
altered.searchParams.set('mm_source_context', new URL(links[1]).searchParams.get('mm_context'));
assert.equal(ctx.savedSourceCitation(altered.href), null);
const add = source.slice(source.indexOf('  function addCites(bub, cites) {'), begin);
Object.assign(ctx, {
  L: (en, zh) => ctx.zh ? zh : en,
  DOC: {createElement: () => ({children: [], setAttribute(k, v) {this[k] = v;},
    appendChild(node) {this.children.push(node);}})},
  insertBeforeActions: (bubble, node) => bubble.children.push(node), stickAfter() {}
});
vm.runInNewContext(add, ctx);
for (const zh of [false, true]) {
  ctx.zh = zh;
  const bubble = {children: []};
  ctx.addCites(bubble, [...links, 'master_brief.json']);
  const anchors = bubble.children[0].children;
  assert.equal(anchors.length, links.length + 1);
  for (let i = 0; i < links.length; i++) {
    const anchor = anchors[i], parsed = ctx.savedSourceCitation(links[i]);
    assert.equal(anchor.href, parsed.href);
    assert.equal(anchor.textContent, parsed[zh ? 'labelZh' : 'labelEn']);
    assert.equal(anchor.target, '_blank');
    assert.equal(anchor.rel, 'noopener noreferrer');
  }
  assert.equal(anchors.at(-1).href, 'https://www.mastermind-x.com/macro.html');
}
// Unchanged destination page parses the exact saved intent and actual owner envelope.
const page = {};
page.globalThis = page;
page.__MM_RETAINED_TEST_HOOK__ = hooks => {page.hooks = hooks;};
page.URLSearchParams = URLSearchParams;
vm.runInNewContext(fs.readFileSync('templates/market_memory_retained.js', 'utf8'), page);
for (let i = 0; i < links.length; i++) {
  const intent = page.hooks.parseUrlIntent(new URL(links[i]).search);
  assert.equal(intent.ok, true);
  assert.equal(intent.intent.mode, 'saved');
  // The actual browser parses JSON in its own realm; preserve that boundary.
  const nativeSaved = vm.runInNewContext('JSON.parse(' + JSON.stringify(JSON.stringify(saved_sources[i])) + ')', page);
  const catalog = page.hooks.normalizeCatalog(catalogs[i]);
  const entry = catalog.entries.find(e => e.contextId === intent.intent.context);
  assert.ok(entry, 'original exact catalog locates each fitted source with limit=1');
  const playback = page.hooks.normalizePlayback(entry, nativeSaved, '"' + entry.packetSha256 + '"', intent.intent);
  assert.equal(playback.contextId, intent.intent.context);
}
console.log('PASS actual fitted gateway citations -> strict saved renderer EN/ZH -> unchanged exact saved page; original chat retained');

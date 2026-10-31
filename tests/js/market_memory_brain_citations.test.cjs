/**
 * Node tests for citation_bridge.js over the actual-owner fixture values
 * (synthetic; no network, no production claims).
 * Run: node test_citation_bridge.cjs
 */
'use strict';
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../../templates/mm_brain.js'), 'utf8');
const start = source.indexOf('  /* BEGIN retained source citation parser');
const end = source.indexOf('  /* END retained source citation parser', start);
if (start < 0 || end < start) throw new Error('actual Brain parser missing');
const context = {};
vm.runInNewContext(source.slice(start, end) + ';this.review=retainedSourceCitation;', context);
const retainedSourceCitation = context.review;

const Q = 'mmquery_ef8f00ade0de779694fa3933236f1a5de6af33aa7368783fc56877cc202819f7';
const S = 'mmsecurity_5fc37e8db34f74314b654c910ea8bacfa7de8b5d2d067f2e5421c9d5745ceb4c';
const G = 'mmgeneration_855da3bb40a2502e33119854bc6655b07492018e8dde7f66d18a8be4474d528e';
const GS = 'dd599258b44e72749f8dc0d7c788d46e252bf3ff69626634fe8107d216c6d29f';
const M = 'mmretainedmethod_e3a65e7758a98eafd5e82eff478fd5e3c633e3628aa4ab0939d8ea3463c1d980';
const CUTOFF = '2026-08-20T12:00:00Z';
const CTX = 'mmctx_1a2692c8568fce5b63b005e55ef98c17af2906f36e1d072df3a13070d4d2a99b';
const SRC = 'mmctx_4e9dca516e8570896af739dc2ab5cf8a313b7d6736adaff7892a2d8b57815cff';

function link(mode, overrides) {
  const values = { mm_mode: mode, mm_query: Q, mm_subject: S, mm_gen: G,
    mm_gen_sha: GS, mm_cutoff: CUTOFF, mm_method: M, mm_context: CTX,
    mm_source_context: SRC };
  Object.assign(values, overrides || {});
  const keys = Object.keys(values);
  return 'https://www.mastermind-x.com/market_memory.html?' +
    keys.map((k) => k + '=' + values[k]).join('&');
}
const CANONICAL = link('historical');

let passed = 0;
let failed = 0;
function check(name, actual, expected) {
  const ok = actual === expected;
  if (ok) { passed += 1; } else {
    failed += 1;
    process.stdout.write('FAIL ' + name + '\n  actual:   ' + String(actual) +
      '\n  expected: ' + String(expected) + '\n');
  }
}
function rejects(name, candidate) {
  check(name, retainedSourceCitation(candidate), null);
}

// Canonical acceptance and label shape.
const cite = retainedSourceCitation(CANONICAL);
check('accepts canonical link', cite === null, false);
check('href is canonical', cite.href, CANONICAL);
check('labelEn is short', cite.labelEn.length <= 64 && cite.labelEn.indexOf('mmctx_4e9dca51') !== -1, true);
check('labelZh is short', cite.labelZh.length <= 64 && cite.labelZh.indexOf('mmctx_4e9dca51') !== -1, true);
check('label is not the raw URL', cite.labelEn.indexOf('http') === -1, true);
check('current mode accepted', retainedSourceCitation(link('current')).href,
  link('current'));

// Canonical click parsing: exact origin, path and full exact keyset once.
const parsed = new URL(cite.href);
check('scheme', parsed.protocol, 'https:');
check('host', parsed.host, 'www.mastermind-x.com');  // no port, no userinfo
check('path', parsed.pathname, '/market_memory.html');
check('no fragment', parsed.hash, '');
const keys = Array.from(parsed.searchParams.keys()).sort();
check('exact keyset', JSON.stringify(keys), JSON.stringify(
  ['mm_context', 'mm_cutoff', 'mm_gen', 'mm_gen_sha', 'mm_method', 'mm_mode',
   'mm_query', 'mm_source_context', 'mm_subject']));
check('unique keys', new Set(keys).size, keys.length);

// Alternate hosts, schemes, ports, credentials, fragments, extra keys.
rejects('http scheme', CANONICAL.replace('https://', 'http://'));
rejects('alternate host', link('historical').replace('www.mastermind-x.com', 'www.mastermind-x.com.evil.test'));
rejects('lookalike host', link('historical').replace('www.mastermind-x.com', 'evil-mastermind-x.com'));
rejects('explicit port', link('historical').replace('https://www.mastermind-x.com/', 'https://www.mastermind-x.com:443/'));
rejects('userinfo credentials', link('historical').replace('https://', 'https://user:pass@'));
rejects('fragment', CANONICAL + '#frag');
rejects('extra query key', CANONICAL + '&mm_extra=1');
rejects('missing key', CANONICAL.replace('&mm_method=' + M, ''));
rejects('duplicate key', CANONICAL + '&mm_mode=historical');
rejects('wrong path', CANONICAL.replace('market_memory.html', 'macro.html'));

// Bounded strict values and mode.
rejects('unknown mode', link('forward_looking'));
rejects('uppercase mode', link('HISTORICAL'));
rejects('bad query token', link('historical', { mm_query: 'mmquery_' + 'Z'.repeat(64) }));
rejects('short sha', link('historical', { mm_gen_sha: 'abc' }));
rejects('uppercase sha', link('historical', { mm_gen_sha: GS.toUpperCase() }));
rejects('bad context token', link('historical', { mm_source_context: Q }));
rejects('naive cutoff', link('historical', { mm_cutoff: 'yesterday' }));
rejects('impossible date', link('historical', { mm_cutoff: '2026-02-30T12:00:00Z' }));
rejects('offset clock', link('historical', { mm_cutoff: '2026-08-20T12:00:00+00:00' }));

// Encoded confusion and smuggling.
rejects('percent-encoded value', link('historical', { mm_cutoff: '2026-08-20T12%3A00%3A00Z' }));
rejects('percent-encoded suffix', CANONICAL + '%2B');
rejects('embedded space', link('historical', { mm_subject: S + '%20' }));
rejects('raw space', 'https://www.mastermind-x.com/market_memory.html?mm_mode= historical&x');
rejects('parameter smuggle', CANONICAL + '&mm_query=mmquery_' + '0'.repeat(64));
rejects('semicolon pair', CANONICAL + ';mm_mode=current');
rejects('non-string input', null);
rejects('object input', { href: CANONICAL });
rejects('empty query', 'https://www.mastermind-x.com/market_memory.html?');
rejects('bare origin', 'https://www.mastermind-x.com');

process.stdout.write('passed=' + passed + ' failed=' + failed + '\n');
process.exit(failed === 0 ? 0 : 1);

// Exercise the actual widget render and routing functions, including all nine cards.
const addStart = source.indexOf('  function addCites(bub, cites) {');
const addEnd = source.indexOf('  /* BEGIN retained source citation parser', addStart);
const routeStart = source.indexOf('  function citeToPage(c) {');
const routeEnd = source.indexOf('  function showUpgrade(d) {', routeStart);
const renderContext = {retainedSourceCitation, ANCHOR:'top',
  L:(en,zh)=>renderContext.zh?zh:en, stickAfter(){},
  DOC:{createElement:()=>({children:[],setAttribute(k,v){this[k]=v;},appendChild(x){this.children.push(x);}})},
  insertBeforeActions:(bubble,node)=>bubble.children.push(node)};
vm.runInNewContext(source.slice(addStart, addEnd)+source.slice(routeStart,routeEnd)+';this.render=addCites;this.route=citeToPage;',renderContext);
for (const zh of [false,true]) {
  renderContext.zh=zh;
  const citations=Array.from({length:9},(_,i)=>link('historical',{mm_source_context:'mmctx_'+String(i).repeat(64)}));
  const bubble={children:[]};renderContext.render(bubble,citations);
  const anchors=bubble.children[0].children;
  if(anchors.length!==9)throw new Error('query plus eight source links must remain visible');
  anchors.forEach((a,i)=>{if(a.href!==citations[i]||a.target!=='_blank'||a.rel!=='noopener noreferrer')throw new Error('source locator routing mismatch');if(a.textContent!==retainedSourceCitation(citations[i])[zh?'labelZh':'labelEn'])throw new Error('localized source label mismatch');});
}
if(renderContext.route('master_brief.json')!=='https://www.mastermind-x.com/macro.html')throw new Error('incumbent citation routing changed');
console.log('PASS actual Brain render: nine exact citations in EN/ZH and incumbent routing');

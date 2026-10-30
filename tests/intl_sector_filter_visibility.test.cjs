'use strict';
// International-only integration regression: a source-rendered collapsed sector
// board must agree with the inherited tablesort.js visible-result count.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');

const root = path.resolve(__dirname, '..');
const template = fs.readFileSync(path.join(root, 'templates/intl.html.j2'), 'utf8');
const tablesort = fs.readFileSync(path.join(root, 'templates/tablesort.js'), 'utf8');
const ownerScript = /<script>\s*(document\.querySelectorAll\('\.more-btn\[data-more\]'\)[\s\S]*?)<\/script>/;
const snippet = template.match(ownerScript);
assert(snippet, 'International page-owned Show all script must be present');
assert(template.includes("'hidden sbmore' if loop.index > 14"), 'source owns the 14-row collapse');
assert(template.includes('data-more="sbmore"'), 'source owns the Show all affordance');
// Frozen, explicitly synthetic 62-row fixture: eleven India rows are below
// the 14-row default. Do not make CI sensitive to daily market sorting.
const indiaRanks = new Set([22,35,40,41,42,45,46,50,56,57,60]);
const rows = Array.from({length:62}, (_,i) => {
  const rank = i+1, market = indiaRanks.has(rank) ? 'India' : 'Market'+rank;
  return '<tr class="' + (rank>14?'hidden sbmore':'') + '"><td>'+rank+'</td><td>'+market+'</td><td>Sector'+rank+'</td></tr>';
}).join('');
const board = '<table class="sb sortable"><thead><tr><th>#</th><th>Market</th><th>Sector</th></tr></thead><tbody>'+rows+'</tbody></table>';
const showAll = '<button class="more-btn" data-more="sbmore">Show all (62)</button>';
test('published International pages retain the actual page-owned filter integration', () => {
  for (const filename of ['intl.html','intl_stocks.html']) {
    const published = fs.readFileSync(path.join(root,'site',filename),'utf8');
    const compiled = published.match(ownerScript);
    assert(compiled,filename+' missing page-owned script');
    assert.equal(compiled[1].trim(),snippet[1].trim(),filename+' must carry current template handler');
  }
});
let browser;
test.before(async () => { browser = await chromium.launch({headless:true}); });
test.after(async () => { if (browser) await browser.close(); });

async function withBoard(fn) {
  const ctx = await browser.newContext({viewport:{width:1440,height:800}});
  const page = await ctx.newPage();
  try {
    await page.setContent('<!doctype html><html data-lang="en"><head><style>.hidden{display:none}</style></head><body>'
      + board + showAll
      + '<table id="other"><tbody><tr class="hidden sbmore"><td>other owner</td></tr><tr><td>visible</td></tr></tbody></table>'
      + '</body></html>');
    await page.addScriptTag({content:snippet[1]});
    await page.addScriptTag({content:tablesort});
    assert.equal(await page.locator('table.sb tbody tr').count(), 62);
    await fn(page);
  } finally { await ctx.close(); }
}

async function shown(page) {
  return page.locator('table.sb tbody tr').evaluateAll(rows =>
    rows.filter(row => getComputedStyle(row).display !== 'none').length);
}
async function search(page, query, status) {
  const input = page.locator('.tbl-filter input[type="search"]').first();
  await input.fill(query);
  await page.waitForFunction(expected => document.querySelector('.tbl-filter .cnt').textContent === expected, status);
  return input;
}

test('filter reveals collapsed matching source rows then restores the fourteen-row resting view', async () => {
  await withBoard(async page => {
    assert.equal(await shown(page),14);
    const input = await search(page,'India','11 / 62');
    assert.equal(await shown(page),11,'announced India matches must be visibly reachable');
    await page.locator('table.sb thead th').nth(1).click(); // inherited sort still operates on the live rows
    assert.equal(await shown(page),11,'sorting must preserve filtered visibility');
    assert.equal(await page.locator('#other tr.hidden').count(),1,'another table owner remains collapsed');
    await search(page,'','');
    assert.equal(await shown(page),14,'clearing filter preserves default collapse');
    assert.equal(await input.inputValue(),'');
    await page.locator('.more-btn[data-more=sbmore]').click();
    assert.equal(await shown(page),62);
    await search(page,'India','11 / 62');
    assert.equal(await shown(page),11);
    await search(page,'','');
    assert.equal(await shown(page),62,'Show all remains committed after Clear');
  });
});

test('no-match reset and Chinese announcements retain the sector collapse and focus', async () => {
  await withBoard(async page => {
    await page.evaluate(() => {
      document.documentElement.setAttribute('data-lang','zh');
      document.dispatchEvent(new Event('langchange'));
    });
    const input=await search(page,'__no_sector_here__','无匹配行 · 0 / 62');
    assert.equal(await shown(page),0);
    await page.locator('.tbl-filter [data-tablesort-reset]').first().click();
    await page.waitForFunction(() => document.querySelector('.tbl-filter .cnt').textContent === '');
    assert.equal(await shown(page),14,'Reset restores default collapse');
    assert.equal(await input.inputValue(),'');
    assert.equal(await input.evaluate(el => document.activeElement === el),true);
  });
});

// This remains source-browser evidence, not an authenticated served-site claim.
// It exercises the real generated page, real CSS and emitted first-party scripts,
// rather than relying on the synthetic table's simplified layout.
test('generated International Stocks page shows every reported filtered match', async () => {
  const ctx = await browser.newContext({viewport:{width:390,height:850},reducedMotion:'reduce'});
  const page = await ctx.newPage();
  try {
    const siteRoot=path.join(root,'site');
    await page.route('**/*', async route => {
      const u=new URL(route.request().url());
      if (u.hostname!=='intl.test') return route.abort();
      const filename=decodeURIComponent(u.pathname).slice(1)||'intl_stocks.html';
      const target=path.resolve(siteRoot,filename);
      if(!target.startsWith(siteRoot+path.sep)||!fs.existsSync(target)||!fs.statSync(target).isFile())
        return route.fulfill({status:404,body:''});
      const type=target.endsWith('.html')?'text/html':target.endsWith('.css')?'text/css':
        target.endsWith('.js')?'text/javascript':target.endsWith('.svg')?'image/svg+xml':
        target.endsWith('.json')?'application/json':'application/octet-stream';
      return route.fulfill({status:200,contentType:type,body:fs.readFileSync(target)});
    });
    const response=await page.goto('http://intl.test/intl_stocks.html',{waitUntil:'load',timeout:45000});
    assert.equal(response.status(),200);
    await page.waitForFunction(() => {
      const table=document.querySelector('table.sb.sortable');
      return table && table.dataset.tablesort==='1';
    });
    const params=await page.evaluate(() => {
      const table=document.querySelector('table.sb.sortable');
      const anchor=table.parentElement.classList.contains('tbl-scroll')?table.parentElement:table;
      const control=anchor.previousElementSibling;
      if(!control?.classList.contains('tbl-filter')) throw new Error('sector filter missing');
      const input=control.querySelector('input[type=search]');
      input.setAttribute('data-r10-sector-test','1');
      const rows=[...table.tBodies[0].rows];
      const hidden=rows.find(row=>row.classList.contains('sbmore')&&row.classList.contains('hidden'));
      if(!hidden) throw new Error('no collapsed sector row in produced data');
      const needle=hidden.cells[2].textContent.trim();
      if(!needle) throw new Error('collapsed sector has no filterable name');
      return {needle,total:rows.length,matching:rows.filter(r=>r.textContent.toLowerCase().includes(needle.toLowerCase())).length};
    });
    const input=page.locator('[data-r10-sector-test]');
    assert(params.matching>0);
    await input.fill(params.needle);
    const count=page.locator('.tbl-filter').filter({has:input}).locator('.cnt');
    await page.waitForFunction(text => [...document.querySelectorAll('.tbl-filter')].some(c=>c.querySelector('[data-r10-sector-test]')&&c.querySelector('.cnt')?.textContent===text),
      params.matching+' / '+params.total);
    assert.equal(await shown(page),params.matching,
      'real generated sector board must visibly show the number it announces');
    await input.fill('');
    assert.equal(await shown(page),14,'native Clear restores first fourteen rows');
  } finally { await ctx.close(); }
});

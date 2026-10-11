'use strict';
/* Browser tests for templates/tablesort.js (site20 S2-01 numeric grammar,
   S2-03 live-row population). Fixtures are inline HTML + the script source
   injected via addScriptTag: no network, no site/ dependency, so the suite
   works in sparse CI checkouts. Set TABLESORT_SOURCE to point at another
   copy of the source (e.g. origin/main bytes for red runs). */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');

const SOURCE = fs.readFileSync(
  process.env.TABLESORT_SOURCE || path.join(__dirname, '..', '..', 'templates', 'tablesort.js'),
  'utf8');

let browser;
test.before(async () => {
  browser = await chromium.launch({headless: true});
});
test.after(async () => {
  if (browser) await browser.close();
});

function doc(body) {
  return '<!doctype html><html><head><meta charset="utf-8"></head><body>' + body + '</body></html>';
}
function table(headers, rows, attrs) {
  const head = '<thead><tr>' + headers.map(h => '<th>' + h + '</th>').join('') + '</tr></thead>';
  const body = '<tbody>' + rows.map(r => '<tr>' + r.map(c => '<td>' + c + '</td>').join('') + '</tr>').join('') + '</tbody>';
  return '<table' + (attrs ? ' ' + attrs : '') + '>' + head + body + '</table>';
}
function bigTable(n) {
  const rows = [];
  for (let i = 1; i <= n; i++) rows.push(['name' + i, String(i * 10)]);
  return table(['Name', 'Val'], rows);
}

async function withPage(html, fn) {
  const context = await browser.newContext();
  const page = await context.newPage();
  page.setDefaultTimeout(10000);
  try {
    await page.setContent(html);
    await page.addScriptTag({content: SOURCE});
    await fn(page);
  } finally {
    await context.close();
  }
}

// click the header cell ITSELF (never a .help child), like a real user
async function clickHeader(page, tableIdx, colIdx) {
  await page.evaluate(({tableIdx, colIdx}) => {
    const table = document.querySelectorAll('table')[tableIdx];
    const header = (table.tHead && table.tHead.rows[0]) || table.tBodies[0].rows[0];
    header.cells[colIdx].dispatchEvent(new MouseEvent('click', {bubbles: true}));
  }, {tableIdx, colIdx});
}
async function dirOf(page, tableIdx, colIdx) {
  return page.evaluate(({tableIdx, colIdx}) => {
    const table = document.querySelectorAll('table')[tableIdx];
    const header = (table.tHead && table.tHead.rows[0]) || table.tBodies[0].rows[0];
    return header.cells[colIdx].getAttribute('data-dir');
  }, {tableIdx, colIdx});
}
// the column's sort keys in current row order (data-sort wins, like the script's txt())
async function colKeys(page, tableIdx, colIdx) {
  return page.evaluate(({tableIdx, colIdx}) => {
    const table = document.querySelectorAll('table')[tableIdx];
    const rows = Array.prototype.slice.call(table.tBodies[0].rows);
    const dataRows = table.tHead ? rows : rows.slice(1);
    return dataRows.map(r => {
      const c = r.cells[colIdx];
      if (!c) return null;
      if (c.dataset && c.dataset.sort !== undefined) return c.dataset.sort;
      return (c.textContent || '').trim();
    });
  }, {tableIdx, colIdx});
}
async function visibleKeys(page, tableIdx, colIdx) {
  return page.evaluate(({tableIdx, colIdx}) => {
    const table = document.querySelectorAll('table')[tableIdx];
    const rows = Array.prototype.slice.call(table.tBodies[0].rows);
    const dataRows = table.tHead ? rows : rows.slice(1);
    return dataRows.filter(r => r.style.display !== 'none')
      .map(r => (r.cells[colIdx].textContent || '').trim());
  }, {tableIdx, colIdx});
}
// wait briefly for the observer-driven count, then ASSERT it (so a wrong count
// fails as an assertion with the observed text, not as a timeout)
async function settleCount(page, expected) {
  try {
    await page.waitForFunction((e) => {
      const el = document.querySelector('.tbl-filter .cnt');
      return el && el.textContent === e;
    }, expected, {timeout: 2000, polling: 50});
  } catch (err) { /* fall through to the assertion below */ }
  assert.equal(await page.locator('.tbl-filter .cnt').textContent(), expected);
}

/* ---------------- S2-01: strict, anchored numeric grammar ---------------- */

test('S2-01: currency+scale suffixes sort by true magnitude ($1.2B vs $900M vs $45K vs $3.4T)', async () => {
  await withPage(doc(table(['Mkt cap'], [
    ['$900M'], ['$3.4T'], ['$45K'], ['$1.2B'], ['$0'],
  ])), async page => {
    await clickHeader(page, 0, 0);
    assert.equal(await dirOf(page, 0, 0), 'desc');
    assert.deepEqual(await colKeys(page, 0, 0), ['$3.4T', '$1.2B', '$900M', '$45K', '$0']);
    await clickHeader(page, 0, 0); // toggle to asc
    assert.equal(await dirOf(page, 0, 0), 'asc');
    assert.deepEqual(await colKeys(page, 0, 0), ['$0', '$45K', '$900M', '$1.2B', '$3.4T']);
  });
});

test('S2-01: accounting negatives sort below U+2212 negatives; real zero sits between', async () => {
  await withPage(doc(table(['Change'], [
    ['(12.5%)'], ['+4.1%'], ['−3.0%'], ['0.0%'],
  ])), async page => {
    await clickHeader(page, 0, 0);
    assert.equal(await dirOf(page, 0, 0), 'desc');
    assert.deepEqual(await colKeys(page, 0, 0), ['+4.1%', '0.0%', '−3.0%', '(12.5%)']);
    await clickHeader(page, 0, 0); // asc: zero between negatives and positives
    assert.deepEqual(await colKeys(page, 0, 0), ['(12.5%)', '−3.0%', '0.0%', '+4.1%']);
  });
});

test('S2-01: missing tokens go last in BOTH directions on numeric and text columns; 0 is not missing', async () => {
  await withPage(doc(table(['Num', 'Text'], [
    ['5', 'banana'], ['', ''], ['3', 'apple'], ['—', '—'], ['n/a', 'n/a'], ['8', 'cherry'], ['0', 'date'],
  ])), async page => {
    await clickHeader(page, 0, 0); // numeric desc
    assert.equal(await dirOf(page, 0, 0), 'desc');
    assert.deepEqual(await colKeys(page, 0, 0), ['8', '5', '3', '0', '', '—', 'n/a']);
    await clickHeader(page, 0, 0); // asc — missing still last
    assert.deepEqual(await colKeys(page, 0, 0), ['0', '3', '5', '8', '', '—', 'n/a']);

    await clickHeader(page, 0, 1); // text asc
    assert.equal(await dirOf(page, 0, 1), 'asc');
    assert.deepEqual(await colKeys(page, 0, 1), ['apple', 'banana', 'cherry', 'date', '', '—', 'n/a']);
    await clickHeader(page, 0, 1); // text desc — missing still last
    assert.deepEqual(await colKeys(page, 0, 1), ['date', 'cherry', 'banana', 'apple', '', '—', 'n/a']);
  });
});

test('S2-01: equal keys keep their prior relative order (stable sort)', async () => {
  await withPage(doc(table(['Val', 'Tag'], [
    ['2', 'a'], ['1', 'b'], ['2', 'c'], ['1', 'd'], ['3', 'e'], ['2', 'f'],
  ])), async page => {
    await clickHeader(page, 0, 0);
    assert.deepEqual(await colKeys(page, 0, 1), ['e', 'a', 'c', 'f', 'b', 'd']);
    await clickHeader(page, 0, 0); // asc: 1s keep b,d order; 2s keep a,c,f order
    assert.deepEqual(await colKeys(page, 0, 1), ['b', 'd', 'a', 'c', 'f', 'e']);
  });
});

test('S2-01: tickers/codes and ISO dates are text, first activation ascending, dates chronological', async () => {
  await withPage(doc(
    table(['Code', 'Date'], [
      ['0700.HK', '2024-01-05'], ['600519.SH', '2023-12-31'], ['3690.HK', '2024-06-02'], ['9988.HK', '2022-09-30'],
    ]) +
    table(['Ticker'], [['AAPL'], ['0700.HK'], ['9988.HK']])), async page => {
    await clickHeader(page, 0, 0);
    assert.equal(await dirOf(page, 0, 0), 'asc'); // old code called 0700.HK numeric → desc
    assert.deepEqual(await colKeys(page, 0, 0), ['0700.HK', '3690.HK', '9988.HK', '600519.SH']);
    await clickHeader(page, 0, 1);
    assert.equal(await dirOf(page, 0, 1), 'asc'); // old code called 2024-01-05 numeric → desc
    assert.deepEqual(await colKeys(page, 0, 1), ['2022-09-30', '2023-12-31', '2024-01-05', '2024-06-02']);
    assert.deepEqual(await colKeys(page, 0, 0), ['9988.HK', '600519.SH', '0700.HK', '3690.HK']);

    await clickHeader(page, 1, 0); // AAPL among tickers is plain text
    assert.equal(await dirOf(page, 1, 0), 'asc');
    assert.deepEqual(await colKeys(page, 1, 0), ['0700.HK', '9988.HK', 'AAPL']);
  });
});

test('S2-01: no partial guesses — 1.2.3 and 12abc make the column text', async () => {
  await withPage(doc(table(['Mix'], [
    ['1.2.3'], ['5'], ['12abc'], ['7'],
  ])), async page => {
    await clickHeader(page, 0, 0);
    assert.equal(await dirOf(page, 0, 0), 'asc'); // classified text, not numeric-desc
    assert.equal((await colKeys(page, 0, 0)).indexOf('1.2.3') !== -1, true); // all rows still present
  });
});

test('S2-01: explicit data-sort machine keys still win over visible text', async () => {
  const rows = [
    ['<td data-sort="-0.42"><span class="heat">▮▮</span></td>'],
    ['<td data-sort="1.05"><span class="heat">▮▮▮▮</span></td>'],
    ['<td data-sort="0.00"><span class="heat">·</span></td>'],
    ['<td data-sort="-1.20"><span class="heat">▮</span></td>'],
  ];
  await withPage(doc('<table><thead><tr><th>Heat</th></tr></thead><tbody>' +
    rows.map(r => '<tr>' + r[0] + '</tr>').join('') + '</tbody></table>'), async page => {
    await clickHeader(page, 0, 0);
    assert.equal(await dirOf(page, 0, 0), 'desc');
    assert.deepEqual(await colKeys(page, 0, 0), ['1.05', '0.00', '-0.42', '-1.20']);
  });
});

test('S2-01: CJK scale suffixes 万/亿 sort by magnitude (3.2亿 above 9,800万)', async () => {
  await withPage(doc(table(['Cap'], [
    ['9,800万'], ['3.2亿'], ['8.8万'], ['1,250亿'],
  ])), async page => {
    await clickHeader(page, 0, 0);
    assert.equal(await dirOf(page, 0, 0), 'desc');
    assert.deepEqual(await colKeys(page, 0, 0), ['1,250亿', '3.2亿', '9,800万', '8.8万']);
  });
});

/* ---------------- S2-03: filter reads the live population ---------------- */

test('S2-03: rows appended after init are filtered and counted (0 / 14, 1 / 14)', async () => {
  await withPage(doc(bigTable(12)), async page => {
    await page.evaluate(() => {
      const tb = document.querySelector('table').tBodies[0];
      const mk = (name, val) => {
        const tr = document.createElement('tr');
        const a = document.createElement('td'); a.textContent = name;
        const b = document.createElement('td'); b.textContent = val;
        tr.appendChild(a); tr.appendChild(b); tb.appendChild(tr);
      };
      mk('ZZTEST13', '130');
      mk('otherrow14', '140');
    });
    await settleCount(page, ''); // no query yet: 14 live rows, all shown
    const input = page.locator('.tbl-filter input');
    await input.fill('qqqnomatchqqq');
    await settleCount(page, '0 / 14');
    assert.deepEqual(await visibleKeys(page, 0, 0), []);
    await input.fill('ZZTEST13');
    await settleCount(page, '1 / 14');
    assert.deepEqual(await visibleKeys(page, 0, 0), ['ZZTEST13']);
  });
});

test('S2-03: rows appended and removed under an active query — live denominator, detached rows untouched', async () => {
  await withPage(doc(bigTable(14)), async page => {
    const input = page.locator('.tbl-filter input');
    await input.fill('name7');
    await settleCount(page, '1 / 14');
    assert.deepEqual(await visibleKeys(page, 0, 0), ['name7']);

    await page.evaluate(() => { // append a row that does NOT match the query
      const tb = document.querySelector('table').tBodies[0];
      const tr = document.createElement('tr');
      const a = document.createElement('td'); a.textContent = 'name15-extra';
      tr.appendChild(a); tb.appendChild(tr);
    });
    await settleCount(page, '1 / 15');

    // remove two non-matching rows: live denominator drops and the detached
    // elements keep the display they had at removal (never re-styled)
    const before = await page.evaluate(() => {
      const tb = document.querySelector('table').tBodies[0];
      const rows = Array.prototype.slice.call(tb.rows);
      window.__kept = [rows[0], rows[5]].map(r => ({
        node: r, display: r.style.display, text: r.cells[0].textContent}));
      tb.removeChild(rows[0]);
      tb.removeChild(rows[5]);
      return window.__kept.map(k => ({text: k.text, display: k.display}));
    });
    await settleCount(page, '1 / 13');
    const after = await page.evaluate(() =>
      window.__kept.map(k => ({display: k.node.style.display, attached: k.node.isConnected})));
    assert.deepEqual(before, [
      {text: 'name1', display: 'none'},
      {text: 'name6', display: 'none'},
    ]);
    assert.deepEqual(after, [
      {display: 'none', attached: false},
      {display: 'none', attached: false},
    ]);
  });
});

test('S2-03: whole-tbody replacement keeps the active sort and filter', async () => {
  await withPage(doc(bigTable(12)), async page => {
    await clickHeader(page, 0, 1); // numeric col desc
    assert.equal(await dirOf(page, 0, 1), 'desc');
    const input = page.locator('.tbl-filter input');
    await input.fill('name');
    await settleCount(page, '12 / 12');

    await page.evaluate(() => {
      const table = document.querySelector('table');
      const tb = document.createElement('tbody');
      [['nameB', '5'], ['nameA', '50'], ['nameC', '500'], ['nomatchzz', '1']].forEach(r => {
        const tr = document.createElement('tr');
        r.forEach(t => { const td = document.createElement('td'); td.textContent = t; tr.appendChild(td); });
        tb.appendChild(tr);
      });
      table.replaceChild(tb, table.tBodies[0]);
    });
    await settleCount(page, '3 / 4');
    // still sorted desc by value, still filtered to name*
    assert.deepEqual(await visibleKeys(page, 0, 1), ['500', '50', '5']);
    assert.deepEqual(await visibleKeys(page, 0, 0), ['nameC', 'nameA', 'nameB']);
  });
});

test('S2-03: nested .tip table and cell text rewrite are not population changes', async () => {
  const rows = [];
  for (let i = 1; i <= 12; i++) rows.push(['name' + i, String(i)]);
  await withPage(doc('<table><thead><tr><th>Name</th><th>Val</th></tr></thead><tbody>' +
    rows.map((r, i) => '<tr>' +
      (i === 0 ? '<td>name1 <table class="tip"><tbody><tr><td>tip</td></tr></tbody></table></td>' : '<td>' + r[0] + '</td>') +
      '<td>' + r[1] + '</td></tr>').join('') +
    '</tbody></table>'), async page => {
    await clickHeader(page, 0, 1); // sort by Val: first click desc
    await clickHeader(page, 0, 1); // second click asc: name1..name12
    const input = page.locator('.tbl-filter input');
    await input.fill('name');
    await settleCount(page, '12 / 12');

    await page.evaluate(() => {
      // grow the nested tip table inside a cell of the enhanced table
      const tip = document.querySelector('table.tip tbody');
      const tr = document.createElement('tr');
      const td = document.createElement('td'); td.textContent = 'tip2';
      tr.appendChild(td); tip.appendChild(tr);
      // rewrite a cell's textContent (live.js style update)
      const cell = document.querySelector('table:not(.tip) tbody tr td:nth-child(2)');
      cell.textContent = '999';
    });
    await settleCount(page, '12 / 12'); // population unchanged
    // no re-sort happened: the rewritten row is still first despite its 999
    const vals = await colKeys(page, 0, 1);
    assert.equal(vals[0], '999');
    assert.equal(vals[1], '2');
  });
});

test('S2-03: idempotent init — second injection adds nothing and one click sorts once', async () => {
  await withPage(doc(bigTable(12)), async page => {
    await page.addScriptTag({content: SOURCE}); // second injection
    await page.waitForTimeout(30);
    assert.equal(await page.locator('.tbl-filter').count(), 1);
    assert.equal(await page.locator('table thead th .sarrow').count(), 2); // one per header
    await clickHeader(page, 0, 0);
    assert.equal(await dirOf(page, 0, 0), 'asc'); // text col first activation, toggled exactly once
    await clickHeader(page, 0, 1);
    assert.equal(await dirOf(page, 0, 1), 'desc'); // numeric col first activation
  });
});

test('S2-03: .st-table and .sb-table are not enhanced', async () => {
  await withPage(doc(
    table(['A'], [['x'], ['y']], 'class="st-table"') +
    table(['B'], [['x'], ['y']], 'class="sb-table"') +
    table(['C'], [['x'], ['y']])), async page => {
    assert.equal(await page.locator('.st-table .th-sort').count(), 0);
    assert.equal(await page.locator('.sb-table .th-sort').count(), 0);
    assert.equal(await page.locator('.st-table .sarrow').count(), 0);
    assert.equal(await page.locator('.sb-table .sarrow').count(), 0);
    // the plain table next to them IS enhanced
    const plain = page.locator('table:not(.st-table):not(.sb-table)');
    assert.equal(await plain.locator('.sarrow').count(), 1);
  });
});

/* ------- conditional composed-only case: #7502 localization survives ------- */

test('S2-03: composed #7502 filter copy localizes on langchange', async (t) => {
  if (!SOURCE.includes('refreshFilterCopy')) {
    t.skip('source has no refreshFilterCopy (main bytes) — composed-only case');
    return;
  }
  await withPage(doc(bigTable(12)), async page => {
    await page.evaluate(() => {
      document.documentElement.setAttribute('data-lang', 'zh');
      document.dispatchEvent(new CustomEvent('langchange'));
    });
    assert.equal(await page.locator('.tbl-filter input').getAttribute('placeholder'), '筛选…');
  });
});

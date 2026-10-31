'use strict';
// INTL-GS-W2A (IM13) browser proof: the real intl.html through the W2A fixture
// (production observation variant, abstain-all, specimen), in Chromium.
// Mirrors tests/intl_gs_foundation_browser.test.cjs (same route/fixture idiom).
const {test, before} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const {chromium} = require('playwright');
const root = path.resolve(__dirname, '..');

const PAGES = {};

// ORCH-6 browser fixture hardening (W2B fx4 lesson B11): fixtureHtml builds
// each variant with a synchronous execFileSync python render inside
// serveRoute, so the first page.goto's navigation timeout would also cover
// the fixture build. Pre-warm all three variants in a node:test before hook,
// outside any navigation timeout — the same one-line hoist main's
// tests/intl_gs_dossier_browser.test.cjs already carries. No assertion,
// timeout value or fixture content changes.
before(() => {
  fixtureHtml('prod');
  fixtureHtml('abstain');
  fixtureHtml('specimen');
});

function fixtureHtml(which) {
  if (PAGES[which]) return PAGES[which];
  const flag = {prod: '--print-html', abstain: '--print-abstain', specimen: '--print-specimen'}[which];
  const html = execFileSync(process.env.INTL_TEST_PYTHON || 'python3',
    [path.join(__dirname, 'intl_gs_scanner_fixture.py'), flag],
    {cwd: root, env: {...process.env, PYTHONPATH: root}, encoding: 'utf8', maxBuffer: 32 * 1024 * 1024});
  PAGES[which] = html;
  return html;
}

function serveRoute(route, pathname) {
  const types = {'.css': 'text/css', '.js': 'text/javascript', '.woff2': 'font/woff2'};
  if (pathname === '/live_config.js' && !fs.existsSync(path.join(root, 'templates', 'live_config.js'))) {
    return route.fulfill({contentType: 'text/javascript',
      body: '/* fixture stub: no live configuration on the evidence site */\n'});
  }
  if (pathname === '/intl.html') {
    return route.fulfill({contentType: 'text/html; charset=utf-8', body: fixtureHtml('prod')});
  }
  if (pathname === '/intl-abstain.html') {
    return route.fulfill({contentType: 'text/html; charset=utf-8', body: fixtureHtml('abstain')});
  }
  if (pathname === '/intl-gs-scanner-specimen.html') {
    return route.fulfill({contentType: 'text/html; charset=utf-8', body: fixtureHtml('specimen')});
  }
  let file = path.join(root, 'templates', '.' + pathname);
  if (pathname.startsWith('/fonts/')) file = path.join(root, 'templates', pathname.slice(1));
  if (!file.startsWith(path.join(root, 'templates') + path.sep)) return route.abort();
  if (!fs.existsSync(file)) return route.abort();
  return route.fulfill({contentType: types[path.extname(file)] || 'application/octet-stream',
    body: fs.readFileSync(file)});
}

async function withRoutedPage(fn, {page = 'intl.html', viewport = {width: 1440, height: 900}} = {}) {
  const browser = await chromium.launch({headless: true,
    ...(process.env.PLAYWRIGHT_CHROMIUM_CHANNEL ? {channel: process.env.PLAYWRIGHT_CHROMIUM_CHANNEL} : {})});
  try {
    const context = await browser.newContext({viewport});
    const web = await context.newPage();
    web.setDefaultTimeout(8000);
    web.setDefaultNavigationTimeout(30000);
    await web.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (url.hostname === 'cloud.umami.is') return route.fulfill({contentType: 'text/javascript', body: ''});
      if (url.hostname !== 'intl.test') return route.abort();
      serveRoute(route, url.pathname);
    });
    await web.goto('https://intl.test/' + page);
    await fn(web);
  } finally {
    await browser.close();
  }
}

function visiblePanel(web, view) {
  return web.locator(`section.intl-gs__view--${view}:not([hidden])`);
}

test('A11 scanner deep link selects JP with the 1.5px info ring', async () => {
  await withRoutedPage(async web => {
    await web.goto('https://intl.test/intl.html?view=scanner&market=JP');
    const panel = visiblePanel(web, 'scanner');
    await web.waitForSelector('section.intl-gs__view--scanner:not([hidden])');
    const selected = panel.locator('table tr[data-gs-market-row][data-gs-selected]');
    assert.equal(await selected.count(), 1);
    assert.equal(await selected.getAttribute('data-gs-market-row'), 'JP');
    const marks = await panel.locator('[data-gs-market-row][data-gs-selected]').evaluateAll(
      nodes => Array.from(nodes).map(node => node.getAttribute('data-gs-market-row')));
    assert.ok(marks.length >= 1 && marks.every(mark => mark === 'JP'), marks.join(','));
    const link = panel.locator('a[data-gs-select-market="JP"]').first();
    assert.equal(await link.getAttribute('aria-current'), 'true');
    const style = await selected.evaluate(node => {
      const cs = getComputedStyle(node);
      // Chromium reports a computed outline-width of 1.5px as '1px', so the
      // declared ring is read from the CSSOM alongside the computed colour.
      let declared = null;
      for (const sheet of document.styleSheets) {
        for (const rule of sheet.cssRules) {
          if (rule.selectorText && rule.selectorText.includes('[data-gs-market-row][data-gs-selected]')) {
            declared = /outline:\s*1\.5px/.test(rule.cssText) ? '1.5px' : rule.cssText;
          }
        }
      }
      return {width: cs.outlineWidth, style: cs.outlineStyle, color: cs.outlineColor, declared};
    });
    assert.equal(style.style, 'solid');
    // dark theme --info resolves to rgb(91, 155, 240)
    assert.equal(style.color, 'rgb(91, 155, 240)');
    assert.equal(style.declared, '1.5px');
    assert.ok(['1px', '1.5px'].includes(style.width), style.width);
  });
});

test('A11 clicking the KR select link moves both marks', async () => {
  await withRoutedPage(async web => {
    await web.goto('https://intl.test/intl.html?view=scanner&market=JP');
    const panel = visiblePanel(web, 'scanner');
    await web.waitForSelector('section.intl-gs__view--scanner:not([hidden])');
    await panel.locator('a[data-gs-select-market="KR"]').first().click();
    const selected = panel.locator('table tr[data-gs-market-row][data-gs-selected]');
    assert.equal(await selected.count(), 1);
    assert.equal(await selected.getAttribute('data-gs-market-row'), 'KR');
    assert.equal(await panel.locator('a[data-gs-select-market="KR"]').first()
      .getAttribute('aria-current'), 'true');
    assert.equal(await panel.locator('a[data-gs-select-market="JP"]').first()
      .getAttribute('aria-current'), null);
  });
});

test('A11 coverage deep link selects JP and the ring follows', async () => {
  await withRoutedPage(async web => {
    await web.goto('https://intl.test/intl.html?view=coverage&market=JP');
    await web.waitForSelector('section.intl-gs__view--coverage:not([hidden])');
    const panel = visiblePanel(web, 'coverage');
    const selected = panel.locator('[data-gs-market-row][data-gs-selected]');
    assert.equal(await selected.count(), 1);
    assert.equal(await selected.getAttribute('data-gs-market-row'), 'JP');
    const style = await selected.evaluate(node => {
      const cs = getComputedStyle(node);
      let declared = null;
      for (const sheet of document.styleSheets) {
        for (const rule of sheet.cssRules) {
          if (rule.selectorText && rule.selectorText.includes('[data-gs-market-row][data-gs-selected]')) {
            declared = /outline:\s*1\.5px/.test(rule.cssText) ? '1.5px' : rule.cssText;
          }
        }
      }
      return {width: cs.outlineWidth, style: cs.outlineStyle, color: cs.outlineColor, declared};
    });
    assert.equal(style.style, 'solid');
    assert.equal(style.color, 'rgb(91, 155, 240)');
    assert.equal(style.declared, '1.5px');
  });
});

test('A11 no horizontal page scroll at 390 on both views', async () => {
  for (const view of ['scanner', 'coverage']) {
    await withRoutedPage(async web => {
      await web.goto(`https://intl.test/intl.html?view=${view}&market=JP`);
      await web.waitForSelector(`section.intl-gs__view--${view}:not([hidden])`);
      const scrollWidth = await web.evaluate(
        () => document.scrollingElement.scrollWidth);
      assert.ok(scrollWidth <= 390, `${view} scrollWidth ${scrollWidth} > 390`);
    }, {viewport: {width: 390, height: 844}});
  }
});

test('A11 the +N markets and +N more disclosures reveal their rows', async () => {
  await withRoutedPage(async web => {
    await web.goto('https://intl.test/intl.html?view=scanner&market=JP');
    await web.waitForSelector('section.intl-gs__view--scanner:not([hidden])');
    const panel = visiblePanel(web, 'scanner');
    const nodata = panel.locator('details.intl-gs__nodata').first();
    const summary = nodata.locator('summary');
    assert.ok(await summary.isVisible());
    const height = await summary.evaluate(node => node.getBoundingClientRect().height);
    assert.ok(height >= 39, `disclosure summary ${height}px < 40px`);
    let list = nodata.locator('[data-gs-nodata-market]').first();
    assert.equal(await list.isVisible(), false);
    await summary.click();
    assert.equal(await nodata.getAttribute('open'), '');
    assert.ok(await list.isVisible());
    const label = await summary.innerText();
    assert.match(label.replace(/\s+/g, ' '), /\+\d+ ?(markets|个市场)/);
  });
  await withRoutedPage(async web => {
    await web.goto('https://intl.test/intl.html?view=coverage&market=JP');
    await web.waitForSelector('section.intl-gs__view--coverage:not([hidden])');
    const panel = visiblePanel(web, 'coverage');
    const more = panel.locator('details.intl-gs__covmore').first();
    const summary = more.locator('summary');
    assert.ok(await summary.isVisible());
    const hiddenRow = more.locator('[data-gs-cov-row]').first();
    assert.equal(await hiddenRow.isVisible(), false);
    await summary.click();
    assert.equal(await more.getAttribute('open'), '');
    assert.ok(await hiddenRow.isVisible());
    assert.match((await summary.innerText()).replace(/\s+/g, ' '), /\+\d+ ?(more|更多)/);
  });
});

test('A11 Tab focus on a select link is the 2px link outline with offset 3', async () => {
  await withRoutedPage(async web => {
    await web.goto('https://intl.test/intl.html?view=scanner&market=JP');
    await web.waitForSelector('section.intl-gs__view--scanner:not([hidden])');
    const link = visiblePanel(web, 'scanner').locator('a[data-gs-select-market]').first();
    await link.focus();
    const style = await link.evaluate(node => {
      const cs = getComputedStyle(node);
      return {width: cs.outlineWidth, style: cs.outlineStyle, color: cs.outlineColor,
              offset: cs.outlineOffset};
    });
    assert.equal(style.width, '2px');
    assert.equal(style.style, 'solid');
    // dark theme --link resolves to rgb(122, 167, 224)
    assert.equal(style.color, 'rgb(122, 167, 224)');
    assert.equal(style.offset, '3px');
  });
});

test('A15 horizon option labels carry the vocabulary in both languages', async () => {
  // GAP (recorded): intl_workspace.js has no generic data-im-label-* option swap
  // for the set_horizon select (only the scenario/history view-local swaps at
  // intl_workspace.js:1221 and intl_workspace.js:1464), so the option TEXT does
  // not follow a language change; the attributes below carry the vocabulary.
  await withRoutedPage(async web => {
    await web.goto('https://intl.test/intl.html?view=scanner&market=JP');
    const options = await web.evaluate(() => Array.from(
      document.querySelectorAll('select[data-im-action="set_horizon"] option'),
      option => ({value: option.value, en: option.getAttribute('data-im-label-en'),
                  zh: option.getAttribute('data-im-label-zh'), text: option.textContent})));
    assert.ok(options.length >= 5);
    const expected = {en: {'1m': '1M', '3m': '3M', '6m': '6M', '12m': '1Y', 'ytd': 'YTD'},
                      zh: {'1m': '1月', '3m': '3月', '6m': '6个月', '12m': '1年', 'ytd': '年初至今'}};
    for (const option of options) {
      assert.equal(option.en, expected.en[option.value], option.value);
      assert.equal(option.zh, expected.zh[option.value], option.value);
      assert.ok(option.en && option.zh && option.en !== option.value);
    }
  });
});

test('A16 no h2 rail renders: ::before content is none outside and inside .intl-gs', async () => {
  await withRoutedPage(async web => {
    await web.goto('https://intl.test/intl.html?view=scanner&market=JP');
    await web.waitForSelector('section.intl-gs__view--scanner:not([hidden])');
    const legacy = await web.evaluate(() => {
      const heading = Array.from(document.querySelectorAll('h2')).find(
        node => !node.closest('.intl-gs'));
      if (!heading) return null;
      const cs = getComputedStyle(heading, '::before');
      return {content: cs.content, id: heading.id || heading.textContent.trim().slice(0, 30)};
    });
    assert.notEqual(legacy, null, 'fixture renders a legacy h2 outside .intl-gs');
    assert.ok(legacy.content === 'none' || legacy.content === 'normal',
      `legacy h2 ::before content ${legacy.content}`);
    const inside = await web.evaluate(() => {
      const heading = document.querySelector('.intl-gs h2');
      const cs = getComputedStyle(heading, '::before');
      return cs.content;
    });
    assert.ok(inside === 'none' || inside === 'normal', `intl-gs h2 ::before ${inside}`);
  });
});

test('scanner abstain-all page boots with zero console errors', async () => {
  await withRoutedPage(async web => {
    const failures = [];
    web.on('console', message => { if (message.type() === 'error') failures.push(message.text()); });
    web.on('pageerror', error => failures.push(String(error)));
    await web.goto('https://intl.test/intl-abstain.html?view=scanner');
    await web.waitForSelector('section.intl-gs__view--scanner:not([hidden])');
    assert.deepEqual(failures, []);
  });
});

test('specimen page boots, chip visible, specimen rows present', async () => {
  await withRoutedPage(async web => {
    await web.goto('https://intl.test/intl-gs-scanner-specimen.html?view=scanner');
    await web.waitForSelector('section.intl-gs__view--scanner:not([hidden])');
    const chip = web.locator('.intl-gs__chip--specimen').first();
    assert.ok(await chip.isVisible());
    const rows = await web.evaluate(() => Array.from(
      document.querySelectorAll('section.intl-gs__view--scanner:not([hidden]) tr[data-gs-market-row]'),
      node => node.getAttribute('data-gs-market-row')));
    assert.deepEqual(rows, ['BR', 'TW', 'KR', 'MX', 'JP', 'AU', 'IN', 'ZA', 'PL']);
  });
});

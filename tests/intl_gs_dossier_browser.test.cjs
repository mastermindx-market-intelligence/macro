'use strict';
// INTL-GS-W2B (IM14 market dossier) browser proof: the REAL dossier view via
// the fixture site (production + abstain-all + specimen), in Chromium.
// Mirrors tests/intl_gs_foundation_browser.test.cjs (same route/fixture idiom).
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const {execFileSync} = require('node:child_process');
const {chromium} = require('playwright');
const root = path.resolve(__dirname, '..');

const SITE = process.env.INTL_GS_W2B_SITE || path.join(os.tmpdir(), 'intl-gs-w2b-site');
const PY = process.env.INTL_TEST_PYTHON || 'python3';

function buildSite() {
  execFileSync(PY, [path.join(__dirname, 'intl_gs_dossier_fixture.py'), '--out', SITE],
    {cwd: root, env: {...process.env, PYTHONPATH: root}, encoding: 'utf8',
      maxBuffer: 64 * 1024 * 1024});
}

function site() {
  if (!fs.existsSync(path.join(SITE, 'intl.html'))) buildSite();
  return SITE;
}

function serveRoute(route, pathname) {
  const types = {'.css': 'text/css', '.js': 'text/javascript', '.woff2': 'font/woff2'};
  let file = path.join(site(), '.' + pathname);
  if (!file.startsWith(site() + path.sep)) return route.abort();
  if (!fs.existsSync(file)) return route.abort();
  return route.fulfill({contentType: types[path.extname(file)] || 'text/html',
    body: fs.readFileSync(file)});
}

async function withRoutedPage(fn, query) {
  const browser = await chromium.launch({headless: true,
    ...(process.env.PLAYWRIGHT_CHROMIUM_CHANNEL ? {channel: process.env.PLAYWRIGHT_CHROMIUM_CHANNEL} : {})});
  try {
    const context = await browser.newContext({viewport: {width: 1440, height: 900}});
    const web = await context.newPage();
    await web.route('**/*', route => serveRoute(route, new URL(route.request().url()).pathname));
    await web.goto('http://fixture.local/intl.html' + (query || ''), {waitUntil: 'load'});
    await web.waitForTimeout(400); // theme.js flourish settle
    await fn(web);
    await context.close();
  } finally {
    await browser.close();
  }
}

async function panel(page) {
  return page.locator('[data-im-panel][data-view="dossier"][data-horizon="1m"][data-basis="usd_unhedged"]');
}

test('B11 deep link ?view=dossier&market=JP shows only the JP article', async () => {
  await withRoutedPage(async page => {
    await page.evaluate(() => { window.IntlWorkspace && window.IntlWorkspace(); });
    const visible = await page.locator('[data-gs-market-scope] article:not([hidden])').all();
    const shown = [];
    for (const article of visible) shown.push(await article.getAttribute('data-gs-market'));
    assert.deepEqual(shown, ['JP']);
    const current = await page.locator('[data-gs-market-row="JP"][data-gs-selected], a[data-gs-select-market="JP"][aria-current="true"]').count();
    assert.ok(current >= 1, 'JP picker link carries the selection mark');
  }, '?view=dossier&market=JP');
});

test('B11 unknown market QQ falls back to the default article with no issues', async () => {
  await withRoutedPage(async page => {
    const shown = await page.locator('[data-gs-market-scope] article:not([hidden])').all();
    const markets = [];
    for (const article of shown) markets.push(await article.getAttribute('data-gs-market'));
    assert.equal(markets.length, 1);
    assert.equal(await page.locator('[data-gs-market-scope] article[data-gs-market-default]').count(), 1);
    assert.equal(markets[0], await page.locator('[data-gs-market-scope] article[data-gs-market-default]').first().getAttribute('data-gs-market'));
    const issues = await page.locator('[data-im-issues]').first().textContent();
    assert.equal((issues || '').trim(), '');
    assert.ok(!page.url().includes('market=QQ'), 'URL aligned back to the canonical form');
  }, '?view=dossier&market=QQ');
});

test('B11 clicking a peer select link switches article and picker mark', async () => {
  await withRoutedPage(async page => {
    const scope = page.locator('[data-im-panel][data-view="dossier"][data-horizon="1m"][data-basis="usd_unhedged"] [data-gs-market-scope]');
    const before = await scope.locator('article:not([hidden])').first().getAttribute('data-gs-market');
    await page.locator('a[data-gs-select-market="JP"]').first().click();
    await page.waitForTimeout(200);
    const after = await scope.locator('article:not([hidden])').first().getAttribute('data-gs-market');
    assert.equal(after, 'JP');
    assert.notEqual(after, before);
    const marked = await page.locator('[data-gs-market-row="JP"][data-gs-selected]').count();
    assert.ok(marked >= 1, 'picker row marked selected');
  }, '?view=dossier');
});

test('B11 no horizontal scroll at 390 and picker disclosure toggles', async () => {
  const browser = await chromium.launch({headless: true});
  try {
    const context = await browser.newContext({viewport: {width: 390, height: 844}});
    const page = await context.newPage();
    await page.route('**/*', route => serveRoute(route, new URL(route.request().url()).pathname));
    await page.goto('http://fixture.local/intl.html?view=dossier', {waitUntil: 'load'});
    await page.waitForTimeout(400);
    const scrollWidth = await page.evaluate(() => document.scrollingElement.scrollWidth);
    assert.ok(scrollWidth <= 390, `scrollWidth ${scrollWidth} > 390`);
    const box = page.locator('[data-gs-picker-box]').first();
    assert.ok(await box.count(), 'picker disclosure present');
    const openBefore = await box.evaluate(el => el.open);
    assert.equal(openBefore, false, 'collapsed at 390 by default');
    const listHiddenBefore = await box.locator('.intl-gs__pickerlist').evaluate(el => el.getBoundingClientRect().height === 0 || getComputedStyle(el).display === 'none');
    assert.ok(listHiddenBefore, 'picker list collapsed');
    await box.locator('summary').click();
    await page.waitForTimeout(150);
    assert.equal(await box.evaluate(el => el.open), true, 'disclosure opens');
    const linkVisible = await box.locator('a[data-gs-select-market]').first().evaluate(el => el.getBoundingClientRect().height > 0);
    assert.ok(linkVisible, 'picker links visible when open');
    const target = await box.locator('summary').evaluate(el => Math.max(el.getBoundingClientRect().height, el.getBoundingClientRect().width));
    assert.ok(target >= 40, `summary target ${target} < 40`);
    await context.close();
  } finally {
    await browser.close();
  }
});

test('B11 Tab focus on a select link shows the 2px --link outline offset 3', async () => {
  const browser = await chromium.launch({headless: true});
  try {
    for (const theme of ['dark', 'light']) {
      const context = await browser.newContext({viewport: {width: 1440, height: 900}});
      const page = await context.newPage();
      await page.route('**/*', route => serveRoute(route, new URL(route.request().url()).pathname));
      await page.goto('http://fixture.local/intl.html?view=dossier', {waitUntil: 'load'});
      await page.evaluate((mode) => {
        document.documentElement.setAttribute('data-theme', mode);
        document.documentElement.setAttribute('data-lang', 'en');
      }, theme);
      await page.waitForTimeout(300);
      const link = page.locator('a[data-gs-select-market="JP"]').first();
      await link.focus();
      const style = await link.evaluate(el => {
        const cs = getComputedStyle(el);
        return {outline: cs.outlineStyle + ' ' + cs.outlineWidth + ' ' + cs.outlineColor,
          offset: cs.outlineOffset};
      });
      assert.match(style.outline, /solid 2px/, `${theme}: 2px solid outline`);
      assert.equal(style.offset, '3px', `${theme}: offset 3px`);
      await context.close();
    }
  } finally {
    await browser.close();
  }
});

test('B13 correction note separator and clock share ONE line box at 390', async () => {
  const browser = await chromium.launch({headless: true});
  try {
    for (const {lang, theme} of [{lang: 'en', theme: 'dark'}, {lang: 'zh', theme: 'light'}]) {
      const context = await browser.newContext({viewport: {width: 390, height: 844}});
      const page = await context.newPage();
      await page.route('**/*', route => serveRoute(route, new URL(route.request().url()).pathname));
      await page.goto('http://fixture.local/intl-gs-states.html', {waitUntil: 'load'});
      await page.evaluate(({lang, theme}) => {
        document.documentElement.setAttribute('data-lang', lang);
        document.documentElement.setAttribute('data-theme', theme);
      }, {lang, theme});
      await page.waitForTimeout(300);
      const notes = await page.locator('.intl-gs__corr').count();
      assert.ok(notes >= 1, 'correction note present on the states page');
      const spans = await page.locator('.intl-gs__corr-when').count();
      assert.equal(spans, notes, `${lang}: one corr-when span per note`);
      const rects = await page.locator('.intl-gs__corr-when').first()
        .evaluate(el => el.getClientRects().length);
      assert.equal(rects, 1, `${lang}/${theme}: separator and clock share one line box`);
      await context.close();
    }
  } finally {
    await browser.close();
  }
});

test('B13 specimen correction row keeps one line box at 390', async () => {
  const browser = await chromium.launch({headless: true});
  try {
    const context = await browser.newContext({viewport: {width: 390, height: 844}});
    const page = await context.newPage();
    await page.route('**/*', route => serveRoute(route, new URL(route.request().url()).pathname));
    await page.goto('http://fixture.local/intl-gs-dossier-specimen.html', {waitUntil: 'load'});
    await page.waitForTimeout(300);
    const spans = await page.locator('.intl-gs__corr-when').count();
    assert.ok(spans >= 1, 'specimen correction row present');
    const rects = await page.locator('.intl-gs__corr-when').first()
      .evaluate(el => el.getClientRects().length);
    assert.equal(rects, 1, 'specimen correction clock shares one line box');
    await context.close();
  } finally {
    await browser.close();
  }
});

test('abstain-all variant renders no market numeral and no horizontal scroll', async () => {
  const browser = await chromium.launch({headless: true});
  try {
    const context = await browser.newContext({viewport: {width: 390, height: 844}});
    const page = await context.newPage();
    await page.route('**/*', route => serveRoute(route, new URL(route.request().url()).pathname));
    await page.goto('http://fixture.local/intl-abstain.html?view=dossier&market=JP', {waitUntil: 'load'});
    await page.waitForTimeout(400);
    const shown = await page.locator('[data-gs-market-scope] article:not([hidden])').all();
    assert.equal(shown.length, 1);
    assert.equal(await shown[0].getAttribute('data-gs-market'), 'JP');
    const heroNumerals = await page.locator('.intl-gs__hero__num').count();
    assert.equal(heroNumerals, 0, 'no hero numeral in the abstain-all variant');
    const scrollWidth = await page.evaluate(() => document.scrollingElement.scrollWidth);
    assert.ok(scrollWidth <= 390, `abstain 390 scrollWidth ${scrollWidth}`);
    await context.close();
  } finally {
    await browser.close();
  }
});

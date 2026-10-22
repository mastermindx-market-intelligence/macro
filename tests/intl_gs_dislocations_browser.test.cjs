'use strict';
// INTL-GS-W3U browser proof: the dislocation explorer view rendered by the
// real intl.html seam (tests/intl_gs_dislocations_fixture.py, real
// attach_surveillance + the real builder) in Chromium, over the W2F fixture
// route idiom (tests/intl_gs_foundation_browser.test.cjs).
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const {chromium} = require('playwright');
const root = path.resolve(__dirname, '..');

function fixtureHtml(variant, scenario) {
  return execFileSync(process.env.INTL_TEST_PYTHON || 'python3',
    [path.join(__dirname, 'intl_gs_dislocations_fixture.py'),
     '--variant', variant, '--scenario', scenario, '--print-html'],
    {cwd: root, env: {...process.env, PYTHONPATH: root}, encoding: 'utf8',
     maxBuffer: 32 * 1024 * 1024});
}

function serveRoute(route, pathname) {
  const types = {'.css': 'text/css', '.js': 'text/javascript', '.woff2': 'font/woff2'};
  if (pathname === '/live_config.js' && !fs.existsSync(path.join(root, 'templates', 'live_config.js'))) {
    return route.fulfill({contentType: 'text/javascript',
      body: '/* fixture stub: no live configuration on the evidence site */\n'});
  }
  let file = path.join(root, 'templates', '.' + pathname);
  if (pathname.startsWith('/fonts/')) file = path.join(root, 'templates', pathname.slice(1));
  if (!file.startsWith(path.join(root, 'templates') + path.sep)) return route.abort();
  if (!fs.existsSync(file)) return route.abort();
  return route.fulfill({contentType: types[path.extname(file)] || 'application/octet-stream',
    body: fs.readFileSync(file)});
}

async function withRoutedPage(fn, {variant = 'specimen', scenario = 'restricted',
                                   width = 1440, height = 900, theme = 'dark',
                                   lang = 'en', query = '?view=dislocations',
                                   trackFailures = false} = {}) {
  const browser = await chromium.launch({headless: true,
    ...(process.env.PLAYWRIGHT_CHROMIUM_CHANNEL ? {channel: process.env.PLAYWRIGHT_CHROMIUM_CHANNEL} : {})});
  try {
    const html = fixtureHtml(variant, scenario);
    const failures = {console: [], responses: []};
    const context = await browser.newContext({viewport: {width, height}});
    const web = await context.newPage();
    web.setDefaultTimeout(8000);
    web.setDefaultNavigationTimeout(30000);
    if (trackFailures) {
      web.on('console', message => { if (message.type() === 'error') failures.console.push(message.text()); });
      web.on('response', response => { if (response.status() >= 400) failures.responses.push(`${response.status()} ${response.url()}`); });
    }
    await web.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (url.hostname === 'cloud.umami.is') return route.fulfill({contentType: 'text/javascript', body: ''});
      if (url.hostname !== 'intl.test') return route.abort();
      if (url.pathname === '/intl.html') return route.fulfill({contentType: 'text/html', body: html});
      return serveRoute(route, url.pathname);
    });
    await web.goto('https://intl.test/intl.html' + query);
    await web.evaluate(({theme, lang}) => {
      if (window.setTheme) window.setTheme(theme);
      if (window.setLang) window.setLang(lang);
      document.documentElement.setAttribute('data-theme', theme);
      document.documentElement.setAttribute('data-lang', lang);
    }, {theme, lang});
    await web.waitForTimeout(250);
    await fn(web, failures);
  } finally {
    await browser.close();
  }
}

async function tokenColor(page, token) {
  return page.evaluate((name) => {
    const probe = document.createElement('span');
    probe.style.color = `var(${name})`;
    document.body.appendChild(probe);
    const color = getComputedStyle(probe).color;
    probe.remove();
    return color;
  }, token);
}

async function declaredRule(page, needle) {
  return page.evaluate((fragment) => {
    for (const sheet of document.styleSheets) {
      for (const rule of sheet.cssRules) {
        if (rule.selectorText && rule.selectorText.includes(fragment)) return rule.cssText;
      }
    }
    return null;
  }, needle);
}

test('B1: the dislocations tab is enabled and opens the view', async () => {
  await withRoutedPage(async page => {
    const tab = page.locator('.intl-workspace__view-nav button[data-im-view="dislocations"]');
    assert.equal(await tab.getAttribute('disabled'), null, 'dislocations tab must be enabled');
    await tab.click();
    const panel = page.locator('section[data-gs-panel][data-view="dislocations"]');
    await panel.waitFor({state: 'visible'});
    assert.equal(await tab.getAttribute('aria-pressed'), 'true');
    assert.ok(await panel.getAttribute('id'));
  });
});

test('B2: 1440 layout — rail 400 beside the column, ranking widths, head 32, rank-1 ring', async () => {
  await withRoutedPage(async page => {
    const rail = page.locator('.intl-dislocations__rail');
    const main = page.locator('.intl-dislocations__left');
    const railBox = await rail.boundingBox();
    const mainBox = await main.boundingBox();
    assert.ok(Math.abs(railBox.width - 400) <= 1, `rail width ${railBox.width}`);
    assert.ok(railBox.x >= mainBox.x + mainBox.width, 'rail sits beside the left column');
    assert.ok(Math.abs(railBox.y - mainBox.y) <= 1, 'rail tops align');
    const widths = await page.evaluate(() => {
      const cells = document.querySelectorAll('.intl-dislocations__table thead th');
      return Array.from(cells).map(cell => cell.getBoundingClientRect().width);
    });
    const expected = [28, 200, 320, 72, 80, 72, 72, 80, 180];
    for (let i = 0; i < expected.length; i += 1) {
      assert.ok(Math.abs(widths[i] - expected[i]) <= 1, `column ${i}: ${widths[i]} != ${expected[i]}`);
    }
    assert.ok(widths[9] > 0, 'STANCE flex column renders');
    const headHeight = await page.evaluate(() =>
      document.querySelector('.intl-dislocations__table thead th').getBoundingClientRect().height);
    assert.ok(Math.abs(headHeight - 32) <= 1, `head height ${headHeight}`);
    const ring = await page.evaluate(() => {
      const row = document.querySelector('.intl-dislocations__ranking tr[data-i="0"]');
      const style = getComputedStyle(row);
      return {style: style.outlineStyle, color: style.outlineColor,
              rule: null};
    });
    const rule = await declaredRule(page, 'checked ~ .intl-dislocations__ranking tr[data-i="0"]');
    assert.ok(rule && rule.includes('outline: 1.5px solid var(--info)'), rule);
    assert.equal(ring.style, 'solid');
    assert.equal(ring.color, await tokenColor(page, '--info'));
  });
});

test('rail stacks below the column at 1024 (mutant 6)', async () => {
  for (const width of [1440, 1280]) {
    await withRoutedPage(async page => {
      const rail = (await page.locator('.intl-dislocations__rail').boundingBox());
      const main = (await page.locator('.intl-dislocations__left').boundingBox());
      assert.ok(rail.x >= main.x + main.width, `at ${width} the rail is beside the column`);
      assert.ok(Math.abs(rail.width - 400) <= 1, `at ${width} rail width ${rail.width}`);
    }, {width});
  }
  await withRoutedPage(async page => {
    const rail = (await page.locator('.intl-dislocations__rail').boundingBox());
    assert.ok(Math.abs(rail.width - 360) <= 1, `at 1180 rail width ${rail.width} (W2 geometry, R5)`);
  }, {width: 1180});
  for (const width of [1099, 1024]) {
    await withRoutedPage(async page => {
      const rail = (await page.locator('.intl-dislocations__rail').boundingBox());
      const main = (await page.locator('.intl-dislocations__left').boundingBox());
      assert.ok(rail.y >= main.y + main.height, `at ${width} the rail stacks below the column`);
    }, {width});
  }
});

test('B4: keyboard — Tab reaches the radios, arrows move selection, focus ring on the label', async () => {
  await withRoutedPage(async page => {
    const radios = page.locator('input.intl-dislocations__pick');
    assert.equal(await radios.count(), 4);
    await radios.first().focus();
    const focused = await page.evaluate(() =>
      document.activeElement && document.activeElement.classList.contains('intl-dislocations__pick'));
    assert.ok(focused, 'Tab reaches the visually hidden radios');
    const focusRing = await page.evaluate(() => {
      const label = document.querySelector('.intl-dislocations__ranking label[data-i="0"]');
      const style = getComputedStyle(label);
      return {style: style.outlineStyle, width: style.outlineWidth,
              color: style.outlineColor, offset: style.outlineOffset};
    });
    assert.equal(focusRing.style, 'solid');
    assert.equal(focusRing.color, await tokenColor(page, '--link'));
    assert.equal(parseFloat(focusRing.width), 2);
    assert.equal(parseFloat(focusRing.offset), 3);
    await page.keyboard.press('ArrowDown');
    const state = await page.evaluate(() => {
      const checked = document.querySelector('input.intl-dislocations__pick:checked');
      const index = checked ? checked.getAttribute('data-i') : null;
      const visible = selector => {
        const element = document.querySelector(selector);
        return element && getComputedStyle(element).display !== 'none';
      };
      return {
        index,
        insp: visible(`.intl-dislocations__insp[data-i="${index}"]`),
        peers: visible(`.intl-dislocations__peers[data-i="${index}"]`),
        ring: visible(`.intl-dislocations__ring[data-i="${index}"]`),
        rowRing: getComputedStyle(
          document.querySelector(`.intl-dislocations__ranking tr[data-i="${index}"]`)).outlineStyle,
      };
    });
    assert.equal(state.index, '1');
    assert.ok(state.insp, 'inspector follows the selection');
    assert.ok(state.peers, 'peers panel follows the selection');
    assert.ok(state.ring, 'scatter ring follows the selection');
    assert.equal(state.rowRing, 'solid', 'row ring follows the selection');
  });
});

test('B5: ZH — an UP numeral takes the EN DOWN colour (red-up via theme tokens)', async () => {
  await withRoutedPage(async page => {
    const enUp = await page.evaluate(() =>
      getComputedStyle(document.querySelector(
        '.intl-dislocations__table .intl-gs__num--up')).color);
    const enDown = await page.evaluate(() =>
      getComputedStyle(document.querySelector(
        '.intl-dislocations__table .intl-gs__num--down')).color);
    assert.notEqual(enUp, enDown);
    const zhUp = await page.evaluate(() => {
      document.documentElement.setAttribute('data-lang', 'zh');
      const color = getComputedStyle(document.querySelector(
        '.intl-dislocations__table .intl-gs__num--up')).color;
      document.documentElement.setAttribute('data-lang', 'en');
      return color;
    });
    assert.equal(zhUp, enDown, 'ZH up ink equals the EN down ink (red)');
    assert.notEqual(zhUp, enUp, 'ZH up ink differs from the EN up ink (green)');
  });
});

test('B6: 390x844 — no horizontal scroll, cards, hit targets', async () => {
  await withRoutedPage(async page => {
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    assert.ok(scrollWidth <= 390, `scrollWidth ${scrollWidth}`);
    const cardMode = await page.evaluate(() =>
      getComputedStyle(document.querySelector('.intl-dislocations__ranking tbody tr')).display);
    assert.equal(cardMode, 'block');
    const labelHeight = await page.evaluate(() =>
      document.querySelector('label.intl-dislocations__market').getBoundingClientRect().height);
    assert.ok(labelHeight >= 40, `interactive label height ${labelHeight}`);
    const resbarWidth = await page.evaluate(() =>
      document.querySelector('.intl-dislocations__resbar').getBoundingClientRect().width);
    assert.ok(resbarWidth <= 390 - 32, `resbar width ${resbarWidth}`);
  }, {width: 390, height: 844});
});

test('B7: dark and light render with zero console errors', async () => {
  for (const theme of ['dark', 'light']) {
    await withRoutedPage(async (page, failures) => {
      assert.deepEqual(failures.console, [], `console errors (${theme})`);
      assert.deepEqual(failures.responses, [], `failed responses (${theme})`);
      assert.equal(await page.locator('.intl-dislocations__root').count(), 1);
    }, {theme, trackFailures: true});
  }
});

test('B8: no duplicate ids and no script inside the view', async () => {
  await withRoutedPage(async page => {
    const audit = await page.evaluate(() => {
      const panel = document.querySelector('section[data-gs-panel][data-view="dislocations"]');
      const ids = Array.from(panel.querySelectorAll('[id]')).map(node => node.id);
      const duplicates = ids.filter((id, index) => ids.indexOf(id) !== index);
      return {duplicates, scripts: panel.querySelectorAll('script').length};
    });
    assert.deepEqual(audit.duplicates, []);
    assert.equal(audit.scripts, 0);
  });
});

test('B9: production variant — no fragility numeral, scatter Empty note, no specimen chip', async () => {
  await withRoutedPage(async page => {
    const audit = await page.evaluate(() => {
      const panel = document.querySelector('section[data-gs-panel][data-view="dislocations"]');
      const fragilityCells = Array.from(panel.querySelectorAll(
        'td[data-label="FRAGILITY"]')).map(cell => cell.textContent.trim());
      return {
        fragilityCells,
        specimen: panel.querySelectorAll('.intl-gs__chip--specimen').length,
        emptyNote: panel.textContent.includes('No admitted fragility score — nothing to plot')
          || panel.textContent.includes('无已准入的脆弱度评分——暂无可绘制数据'),
        above: panel.textContent.includes('above threshold') || panel.textContent.includes('高于阈值'),
      };
    });
    assert.ok(audit.fragilityCells.length >= 7);
    for (const cell of audit.fragilityCells) {
      assert.ok(cell.includes('—'), cell);
      assert.ok(!/\d/.test(cell), cell);  // no fragility numeral in production
    }
    assert.equal(audit.specimen, 0);
    assert.ok(audit.emptyNote);
    assert.equal(audit.above, false);
  }, {variant: 'production'});
});

test('B10: evidence crops when INTL_GS_W3U_CROPS is set', async () => {
  const crops = process.env.INTL_GS_W3U_CROPS;
  if (!crops) return;
  fs.mkdirSync(path.join(root, crops), {recursive: true});
  const manifest = [];
  await withRoutedPage(async page => {
    await page.screenshot({path: path.join(root, crops, 'dislocations__dark__en__1280.png'), fullPage: true});
    manifest.push({file: 'dislocations__dark__en__1280.png', viewport: '1280x900',
                   theme: 'dark', lang: 'en', variant: 'specimen', what: '1280 desktop: rail 400 beside the column'});
  }, {width: 1280, height: 900});
  await withRoutedPage(async page => {
    await page.screenshot({path: path.join(root, crops, 'dislocations__dark__en__1024-stacked.png'), fullPage: true});
    manifest.push({file: 'dislocations__dark__en__1024-stacked.png', viewport: '1024x900',
                   theme: 'dark', lang: 'en', variant: 'specimen', what: '1024: the inspector rail stacks below the left column (D3, mutant 6)'});
  }, {width: 1024, height: 900});
  await withRoutedPage(async page => {
    const row = page.locator('.intl-dislocations__ranking tr[data-unranked="1"]').first();
    await row.scrollIntoViewIfNeeded();
    await row.screenshot({path: path.join(root, crops, 'abstain-row__dark__en__1440.png')});
    manifest.push({file: 'abstain-row__dark__en__1440.png', viewport: '1440x900',
                   theme: 'dark', lang: 'en', variant: 'production-rows', what: 'Abstain row: dashed muted chip, dash cells, reason line'});
  }, {variant: 'production'});
  await withRoutedPage(async page => {
    const row = page.locator('.intl-dislocations__ranking tr[data-i="1"]');
    await row.scrollIntoViewIfNeeded();
    await row.screenshot({path: path.join(root, crops, 'qualified-row__dark__en__1440.png')});
    manifest.push({file: 'qualified-row__dark__en__1440.png', viewport: '1440x900',
                   theme: 'dark', lang: 'en', variant: 'specimen', what: 'Qualified row: dashed warn residual bar outline, fragility 60 above threshold (D2/D4)'});
  });
  await withRoutedPage(async page => {
    await page.screenshot({path: path.join(root, crops, 'dislocations__dark__en__1440__production.png'), fullPage: true});
    manifest.push({file: 'dislocations__dark__en__1440__production.png', viewport: '1440x900',
                   theme: 'dark', lang: 'en', variant: 'production', what: 'production honesty: no fragility numeral, scatter Empty note, all markets in Not-plotted chips'});
  }, {variant: 'production'});
  fs.writeFileSync(path.join(root, crops, 'crops.json'),
                   JSON.stringify(manifest, null, 1) + '\n');
  assert.equal(manifest.length, 5);
});

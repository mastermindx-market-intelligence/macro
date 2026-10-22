'use strict';
// INTL-GS-W2F browser proof (mission 4.6): the real intl.html via the
// render_fixture seam + the fixture-site stub coverage view, in Chromium.
// Mirrors tests/intl_workspace_page.test.cjs (same route/fixture idiom).
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const {chromium} = require('playwright');
const root = path.resolve(__dirname, '..');

function fixtureHtml(stub) {
  const args = [path.join(__dirname, 'intl_gs_fixture_site.py'), '--print-html'];
  if (stub) args.push('--stub-coverage');
  return execFileSync(process.env.INTL_TEST_PYTHON || 'python3', args,
    {cwd: root, env: {...process.env, PYTHONPATH: root}, encoding: 'utf8', maxBuffer: 16 * 1024 * 1024});
}

function statesHtml() {
  return execFileSync(process.env.INTL_TEST_PYTHON || 'python3',
    [path.join(__dirname, 'intl_gs_fixture_site.py'), '--print-states'],
    {cwd: root, env: {...process.env, PYTHONPATH: root}, encoding: 'utf8', maxBuffer: 16 * 1024 * 1024});
}

function serveRoute(route, pathname) {
  const types = {'.css': 'text/css', '.js': 'text/javascript', '.woff2': 'font/woff2'};
  // The production site build serves live_config.js beside the pages; this
  // branch does not carry a templates/ copy, so the same no-op stub the
  // fixture site writes (tests/intl_gs_fixture_site.py, VF16) serves here too.
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

async function withRoutedPage(fn, {query = '', stub = true, page = 'intl', trackFailures = false} = {}) {
  const browser = await chromium.launch({headless: true,
    ...(process.env.PLAYWRIGHT_CHROMIUM_CHANNEL ? {channel: process.env.PLAYWRIGHT_CHROMIUM_CHANNEL} : {})});
  try {
    const html = page === 'states' ? statesHtml() : fixtureHtml(stub);
    const failures = {console: [], responses: []};
    const context = await browser.newContext({viewport: {width: 1440, height: 900}});
    const web = await context.newPage();
    web.setDefaultTimeout(6000);
    web.setDefaultNavigationTimeout(30000);
    if (trackFailures) {
      web.on('console', message => { if (message.type() === 'error') failures.console.push(message.text()); });
      web.on('response', response => { if (response.status() >= 400) failures.responses.push(`${response.status()} ${response.url()}`); });
    }
    await web.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (url.hostname === 'cloud.umami.is') return route.fulfill({contentType: 'text/javascript', body: ''});
      if (url.hostname !== 'intl.test') return route.abort();
      if (url.pathname === '/intl.html' && page !== 'states') {
        return route.fulfill({contentType: 'text/html', body: html});
      }
      if (url.pathname === '/intl-gs-states.html' && page === 'states') {
        return route.fulfill({contentType: 'text/html', body: html});
      }
      return serveRoute(route, url.pathname);
    });
    const target = page === 'states' ? '/intl-gs-states.html' : '/intl.html';
    await web.goto('https://intl.test' + target + query);
    await fn(web, failures);
  } finally {
    await browser.close();
  }
}

async function withPage(fn, {query = '', stub = true} = {}) {
  await withRoutedPage((web) => fn(web), {query, stub});
}

// Resolved token probe: reads the rgb() form the engine would paint for a
// token, so assertions compare like with like across engines.
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

// Chromium floors the COMPUTED outline width/offset to whole pixels, so the
// 1.5px ring is proven on the declared CSSOM rule plus the computed style and
// colour (a floored 1px solid --info outline is exactly the 1.5px rule painted
// at device-pixel granularity — never an inset or single-side border).
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

test('production page shows seven disabled surveillance tabs', async () => {
  await withPage(async page => {
    const states = await page.evaluate(() => Object.fromEntries(
      Array.from(document.querySelectorAll('.intl-workspace__view-nav button[data-im-action="set_view"]'))
        .map(button => [button.getAttribute('data-im-view'), button.disabled])));
    for (const view of ['scanner', 'dislocations', 'transmission', 'dossier', 'scenario', 'replay', 'coverage']) {
      assert.ok(view in states, `missing tab ${view}`);
      assert.equal(states[view], true, `${view} must be disabled without a builder`);
    }
    for (const view of ['overview']) assert.equal(states[view], false, `${view} must stay enabled`);
  }, {stub: false});
});

test('coverage tab is enabled, clickable, shows its panel and empties issues', async () => {
  await withPage(async page => {
    const issues = page.locator('[data-im-issues]');
    const unavailable = page.locator('[data-im-unavailable]');
    await issues.textContent().then(text => assert.equal(text, '', 'issues must start empty'));
    const coverage = page.locator('.intl-workspace__view-nav button[data-im-view="coverage"]');
    assert.equal(await coverage.isDisabled(), false, 'coverage must be enabled under the stub');
    await coverage.click();
    await page.waitForTimeout(120);
    const panel = page.locator('[data-im-panel][data-view="coverage"]');
    await panel.waitFor({state: 'visible'});
    assert.equal(await panel.getAttribute('data-im-panel') !== null, true);
    const hiddenOthers = await page.evaluate(() =>
      Array.from(document.querySelectorAll('[data-im-panel]:not([data-view="coverage"])'))
        .every(node => node.hidden));
    assert.equal(hiddenOthers, true, 'legacy panels must be hidden while coverage shows');
    assert.equal(await issues.textContent(), '', 'issues stays empty after switching');
    assert.equal(await unavailable.isHidden(), true, 'unavailable banner must stay hidden');
    const gsWrapper = await panel.evaluate(node => Boolean(node.closest('.intl-gs')));
    assert.equal(gsWrapper, true, 'coverage panel must render inside the .intl-gs wrapper');
  });
});

test('?view=scanner without a panel behaves like an unsupported view', async () => {
  await withPage(async page => {
    const issues = await page.locator('[data-im-issues]');
    await issues.waitFor({state: 'visible'});
    const text = await issues.textContent();
    assert.equal(text, 'This view is not available yet');
    assert.equal(await page.locator('[data-im-unavailable]').isVisible(), true,
      'unavailable banner must show, exactly like a legacy view with no panel');
    const visible = await page.evaluate(() =>
      Array.from(document.querySelectorAll('[data-im-panel]')).filter(node => !node.hidden).length);
    assert.equal(visible, 0, 'no panel may be shown for an unbuilt view');
    const scanner = page.locator('.intl-workspace__view-nav button[data-im-view="scanner"]');
    assert.equal(await scanner.isDisabled(), true, 'scanner button stays disabled');
  }, {query: '?view=scanner'});
});

test('legacy views still switch while the surveillance seam exists', async () => {
  await withPage(async page => {
    const overview = page.locator('.intl-workspace__view-nav button[data-im-view="overview"]');
    const coverage = page.locator('.intl-workspace__view-nav button[data-im-view="coverage"]');
    const legacyStates = await page.evaluate(() => Object.fromEntries(
      Array.from(document.querySelectorAll('.intl-workspace__view-nav button[data-im-action="set_view"]'))
        .filter(button => ['overview', 'compare', 'macro', 'risk', 'history', 'library']
          .includes(button.getAttribute('data-im-view')))
        .map(button => [button.getAttribute('data-im-view'), button.disabled])));
    assert.deepEqual(Object.keys(legacyStates),
      ['overview', 'compare', 'macro', 'risk', 'history', 'library']);
    for (let round = 0; round < 2; round++) {
      await coverage.click();
      await page.locator('[data-im-panel][data-view="coverage"]').waitFor({state: 'visible'});
      await overview.click();
      await page.waitForTimeout(120);
      assert.equal(await page.evaluate(() =>
        Array.from(document.querySelectorAll('[data-im-panel][data-view="overview"]'))
          .some(node => !node.hidden)), true, 'overview must come back after coverage');
      assert.equal(await page.evaluate(() =>
        Array.from(document.querySelectorAll('[data-im-panel][data-view="coverage"]'))
          .every(node => node.hidden)), true, 'coverage must hide again');
    }
  });
});

// ---------------------------------------------------------------- X6 market seam

test('X6a: ?view=coverage&market=JP selects JP and scopes to JP only', async () => {
  await withPage(async page => {
    const jp = page.locator('[data-gs-market-scope] > [data-gs-market="JP"]');
    const kr = page.locator('[data-gs-market-scope] > [data-gs-market="KR"]');
    await page.locator('[data-im-panel][data-view="coverage"]').waitFor({state: 'visible'});
    await jp.waitFor({state: 'visible'});
    assert.equal(await kr.isHidden(), true, 'KR must stay hidden while JP is selected');
    assert.equal(await page.evaluate(() => new URLSearchParams(location.search).get('market')), 'JP',
      'the market param must survive the mount serialization');
  }, {query: '?view=coverage&market=JP'});
});

test('X6b: market=zz and unknown ids are ignored with empty issues', async () => {
  for (const bad of ['zz', 'XX', 'JPN']) {
    await withPage(async page => {
      await page.locator('[data-im-panel][data-view="coverage"]').waitFor({state: 'visible'});
      assert.equal(await page.locator('[data-im-issues]').textContent(), '',
        `issues must stay empty for market=${bad}`);
      const visible = await page.evaluate(() =>
        Array.from(document.querySelectorAll('[data-gs-market-scope] > [data-gs-market]'))
          .filter(node => !node.hidden)
          .map(node => node.getAttribute('data-gs-market')));
      assert.deepEqual(visible, ['JP'], `the default market shows for market=${bad}`);
      const marketParam = await page.evaluate(() => new URLSearchParams(location.search).get('market'));
      assert.ok(marketParam === '' || marketParam === null,
        `an ignored market must leave no selection in the URL, saw ${marketParam}`);
    }, {query: `?view=coverage&market=${bad}`});
  }
});

test('X6c: a market select link switches view and updates the URL', async () => {
  await withPage(async page => {
    await page.waitForTimeout(150);
    assert.equal(await page.locator('[data-im-panel][data-view="coverage"]').isHidden(), true,
      'start on overview with the coverage panel hidden');
    await page.click('a[data-gs-select-market="KR"][data-gs-open="coverage"]');
    await page.locator('[data-im-panel][data-view="coverage"]').waitFor({state: 'visible'});
    const params = new URLSearchParams(await page.evaluate(() => location.search));
    assert.equal(params.get('view'), 'coverage');
    assert.equal(params.get('market'), 'KR');
    const visible = await page.evaluate(() =>
      Array.from(document.querySelectorAll('[data-gs-market-scope] > [data-gs-market]'))
        .filter(node => !node.hidden)
        .map(node => node.getAttribute('data-gs-market')));
    assert.deepEqual(visible, ['KR']);
  });
});

test('X6d: back and forward restore both view and market', async () => {
  await withPage(async page => {
    await page.click('a[data-gs-select-market="KR"][data-gs-open="coverage"]');
    await page.locator('[data-im-panel][data-view="coverage"]').waitFor({state: 'visible'});
    await page.click('.intl-workspace__view-nav button[data-im-view="overview"]');
    await page.waitForTimeout(150);
    await page.goBack();
    await page.locator('[data-im-panel][data-view="coverage"]').waitFor({state: 'visible'});
    assert.equal(await page.evaluate(() => new URLSearchParams(location.search).get('market')), 'KR',
      'back must restore the selected market');
    const marks = await page.evaluate(() =>
      Array.from(document.querySelectorAll('[data-gs-market-row][data-gs-selected]'))
        .map(node => node.getAttribute('data-gs-market-row')));
    assert.deepEqual(marks, ['KR'], 'back must restore the selected-market marking');
    await page.goForward();
    await page.waitForTimeout(150);
    assert.equal(await page.evaluate(() =>
      Array.from(document.querySelectorAll('[data-im-panel][data-view="overview"]'))
        .some(node => !node.hidden)), true, 'forward must restore overview');
  });
});

test('X6e: selected market rows carry the 1.5px --info ring and aria-current', async () => {
  await withPage(async page => {
    await page.locator('[data-im-panel][data-view="coverage"]').waitFor({state: 'visible'});
    const initial = await page.evaluate(() => ({
      marked: Array.from(document.querySelectorAll('[data-gs-market-row][data-gs-selected]'))
        .map(node => node.getAttribute('data-gs-market-row')),
      current: Array.from(document.querySelectorAll('a[data-gs-select-market][aria-current="true"]'))
        .map(node => node.getAttribute('data-gs-select-market')),
    }));
    assert.deepEqual(initial.marked, ['JP']);
    assert.deepEqual(initial.current, ['JP']);
    const ring = await page.evaluate(() => {
      const row = document.querySelector('[data-gs-market-row="JP"]');
      const style = getComputedStyle(row);
      return {width: style.outlineWidth, color: style.outlineColor, offset: style.outlineOffset, style: style.outlineStyle};
    });
    assert.match(await declaredRule(page, 'data-gs-market-row'), /outline:\s*1\.5px solid var\(--info\)/);
    assert.match(await declaredRule(page, 'data-gs-market-row'), /outline-offset:\s*-1\.5px/);
    assert.equal(ring.style, 'solid', 'the selected row paints a solid outline');
    assert.equal(ring.color, await tokenColor(page, '--info'), 'ring colour must be --info');
    await page.click('a[data-gs-select-market="KR"]');
    await page.waitForTimeout(150);
    const moved = await page.evaluate(() => ({
      marked: Array.from(document.querySelectorAll('[data-gs-market-row][data-gs-selected]'))
        .map(node => node.getAttribute('data-gs-market-row')),
      current: Array.from(document.querySelectorAll('a[data-gs-select-market][aria-current="true"]'))
        .map(node => node.getAttribute('data-gs-select-market')),
    }));
    assert.deepEqual(moved.marked, ['KR']);
    assert.deepEqual(moved.current, ['KR']);
  }, {query: '?view=coverage&market=JP'});
});

// ---------------------------------------------------------------- visual fixes

test('VF1/VF2/VF5/VF15: fixture page canvas, anatomy, muted values, h2 bar', async () => {
  await withRoutedPage(async (page) => {
    for (const theme of ['dark', 'light']) {
      await page.evaluate((name) => document.documentElement.setAttribute('data-theme', name), theme);
      const bg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
      const expectedBg = await tokenColor(page, '--bg');
      assert.equal(bg, expectedBg, `body background must be --bg in ${theme}`);
      assert.equal(await page.evaluate(() => getComputedStyle(document.body).backgroundImage), 'none',
        `no ambient gradient in ${theme}`);
      const title = await page.evaluate(() =>
        getComputedStyle(document.querySelector('.intl-gs__bandhead__title')).color);
      assert.equal(title, await tokenColor(page, '--text'), `title must be --text in ${theme}`);
    }
    const mainrow = await page.evaluate(() => {
      const cell = document.querySelector('.intl-gs__statecell');
      const row = cell.querySelector('.intl-gs__statecell__mainrow');
      return row ? getComputedStyle(row) : null;
    });
    assert.ok(mainrow, 'the value row must exist');
    assert.equal(mainrow.display, 'flex', 'value + basis must share one flex row');
    for (const state of ['stale', 'closed', 'suspended']) {
      const muted = await page.evaluate(async (name) => {
        document.documentElement.setAttribute('data-theme', 'dark');
        const cell = document.querySelector(`.intl-gs__statecell--${name} .intl-gs__statecell__value`);
        return getComputedStyle(cell).color;
      }, state);
      assert.equal(muted, await tokenColor(page, '--muted'), `${state} value must be --muted`);
      const ink = await page.evaluate((name) =>
        document.querySelector(`.intl-gs__statecell--${name} .intl-gs__statecell__value`).className, state);
      assert.ok(!/intl-gs__num--(up|down)/.test(ink), `${state} must carry no direction ink class`);
    }
    const h2bar = await page.evaluate(() =>
      getComputedStyle(document.querySelector('.intl-gs h2'), '::before').content);
    assert.equal(h2bar, 'none', 'the page-wide h2 gradient bar must be neutralised inside .intl-gs');
  }, {page: 'states'});
});

test('VF7/VF9/VF12: glyph row wraps, selected ring complete, mobile question grid', async () => {
  await withRoutedPage(async (page) => {
    const glyphRow = page.locator('.intl-gs__demorow').filter({has: page.locator('.intl-gs__glyphwrap')});
    for (const width of [1440, 390]) {
      await page.setViewportSize({width, height: width === 1440 ? 900 : 844});
      const overflow = await page.evaluate(() => {
        const rows = Array.from(document.querySelectorAll('.intl-gs__demorow'));
        const row = rows.find(node => node.querySelector('.intl-gs__glyphwrap'));
        return {scroll: row.scrollWidth, client: row.clientWidth};
      });
      assert.ok(overflow.scroll <= overflow.client,
        `glyph row must wrap inside its panel at ${width}: ${overflow.scroll} > ${overflow.client}`);
    }
    await page.setViewportSize({width: 1440, height: 900});
    const ring = await page.evaluate(() => {
      const row = document.querySelector('.intl-gs__table tbody tr.is-selected');
      const style = getComputedStyle(row);
      return {width: style.outlineWidth, color: style.outlineColor, offset: style.outlineOffset, style: style.outlineStyle,
        box: row.getBoundingClientRect()};
    });
    assert.match(await declaredRule(page, 'tr.is-selected'), /outline:\s*1\.5px solid var\(--info\)/);
    assert.match(await declaredRule(page, 'tr.is-selected'), /outline-offset:\s*-1\.5px/);
    assert.equal(ring.style, 'solid');
    assert.equal(ring.color, await tokenColor(page, '--info'));
    // The ring is drawn inside the row box, so the clipped .intl-gs__tablewrap
    // cannot cut it: all four sides render at 1440 (VF9).
    const wrapClip = await page.evaluate(() =>
      getComputedStyle(document.querySelector('.intl-gs__tablewrap')).overflow);
    assert.equal(wrapClip, 'clip');
    await page.setViewportSize({width: 390, height: 844});
    const columns = await page.evaluate(() =>
      getComputedStyle(document.querySelector('.intl-gs__qstrip')).gridTemplateColumns.split(' ').length);
    assert.equal(columns, 2, 'the six-question strip is a 2×3 grid at 390');
    const clipped = await page.evaluate(() =>
      Array.from(document.querySelectorAll('.intl-gs__qcard__title'))
        .filter(node => node.scrollWidth > node.clientWidth + 1).length);
    assert.equal(clipped, 0, 'no question label may be clipped at 390');
  }, {page: 'states'});
});

test('VF11: the KPI tier chip never overlaps the label at 390', async () => {
  await withRoutedPage(async (page) => {
    await page.setViewportSize({width: 390, height: 844});
    const overlaps = await page.evaluate(() => {
      const bad = [];
      for (const card of document.querySelectorAll('.intl-gs__kpi')) {
        const chip = card.querySelector('.intl-gs__kpi__tier .intl-gs__chip').getBoundingClientRect();
        const label = card.querySelector('.intl-gs__kpi__label');
        // The label's padded box may extend under the reserved chip space by
        // design; what must never collide is the label's TEXT (VF11).
        const range = document.createRange();
        range.selectNodeContents(label);
        const lines = Array.from(range.getClientRects());
        const collide = lines.some(rect => rect.right > chip.left + 1
          && rect.bottom > chip.top + 1 && rect.top < chip.bottom - 1 && rect.left < chip.right - 1);
        if (collide) bad.push(label.textContent.trim());
      }
      return bad;
    });
    assert.deepEqual(overlaps, [], 'no KPI label may collide with its tier chip at 390');
  }, {page: 'states'});
});

test('VF13/VF14: fixture reserves copilot space and header chip gap', async () => {
  await withRoutedPage(async (page) => {
    const padding = await page.evaluate(() =>
      parseFloat(getComputedStyle(document.querySelector('.intl-gs--fixture')).paddingBottom));
    assert.ok(padding >= 80, `fixture must reserve copilot space, saw ${padding}px`);
    const chipGap = await page.evaluate(() => {
      const head = document.querySelector('.intl-gs__specimen-head');
      return parseFloat(getComputedStyle(head).marginBottom);
    });
    assert.ok(chipGap >= 12, `specimen chip row must leave >=12px below, saw ${chipGap}px`);
    // The floating copilot launcher pins to the viewport bottom; the reserved
    // bottom space keeps it over empty canvas, never over the last specimen.
    const gap = await page.evaluate(() => {
      const panels = document.querySelectorAll('.intl-gs .intl-gs__panel');
      const last = panels[panels.length - 1].getBoundingClientRect();
      return document.documentElement.scrollHeight - last.bottom;
    });
    assert.ok(gap >= 80, `at least 80px must sit below the last specimen, saw ${gap}px`);
  }, {page: 'states'});
});

test('VF16: both fixture pages load with zero console errors and zero failed requests', async () => {
  await withRoutedPage(async (page, failures) => {
    await page.waitForTimeout(1600);
    assert.deepEqual(failures.console, [], 'console errors on the states page');
    assert.deepEqual(failures.responses, [], 'failed responses on the states page');
  }, {page: 'states', trackFailures: true});
  await withRoutedPage(async (page, failures) => {
    await page.waitForTimeout(1600);
    assert.deepEqual(failures.console, [], 'console errors on the shell page');
    assert.deepEqual(failures.responses, [], 'failed responses on the shell page');
  }, {page: 'intl', stub: true, trackFailures: true});
});

// ---------------------------------------------------------------- FX fix round

// FX3: a chip that is a direct child of a flex-column panel keeps its content
// width (the specimen chip must never stretch to the panel width).
test('FX3: specimen chip keeps intrinsic width in flex-column panels', async () => {
  await withRoutedPage(async page => {
    for (const width of [1440, 390]) {
      await page.setViewportSize({width, height: width === 1440 ? 900 : 844});
      const measure = await page.evaluate(() => {
        const chip = document.querySelector('.intl-gs__panel > .intl-gs__chip--specimen');
        if (!chip) return null;
        const panel = chip.closest('.intl-gs__panel');
        const previous = chip.style.width;
        chip.style.width = 'max-content';
        const maxContent = chip.getBoundingClientRect().width;
        chip.style.width = previous;
        return {width: chip.getBoundingClientRect().width, maxContent,
                panel: panel.getBoundingClientRect().width};
      });
      assert.ok(measure, 'the stub coverage panel must carry a direct specimen chip');
      assert.ok(measure.width <= measure.maxContent + 2,
        `chip stretched at ${width}: ${measure.width} > max-content ${measure.maxContent} + 2`);
      assert.ok(measure.width < measure.panel / 2,
        `chip must stay under half the panel at ${width}: ${measure.width} of ${measure.panel}`);
    }
  }, {page: 'intl', stub: true, query: '?view=coverage&market=JP'});
});

// FX4: at 390 the snapshot labels and read-only pills stay one LINE tall in
// every theme × language (the h40 pill box is design height — the defect is
// the TEXT wrapping, measured as the number of distinct line tops under the
// element's own range), and nothing horizontally scrolls.
test('FX4: snapshot controls never break per character at 390', async () => {
  await withRoutedPage(async page => {
    for (const theme of ['dark', 'light']) {
      for (const lang of ['en', 'zh']) {
        await page.evaluate(({theme, lang}) => {
          document.documentElement.setAttribute('data-theme', theme);
          document.documentElement.setAttribute('data-lang', lang);
        }, {theme, lang});
        await page.setViewportSize({width: 390, height: 844});
        const result = await page.evaluate(() => {
          const multiLine = [];
          const nodes = [
            ...document.querySelectorAll('.intl-gs__snapctl__label'),
            ...document.querySelectorAll('.intl-gs__snapshot .intl-gs__seg__opt'),
          ];
          for (const node of nodes) {
            const style = getComputedStyle(node);
            const lineHeight = style.lineHeight !== 'normal'
              ? parseFloat(style.lineHeight) : 1.5 * parseFloat(style.fontSize);
            const range = document.createRange();
            range.selectNodeContents(node);
            const rects = Array.from(range.getClientRects())
              .filter(rect => rect.width > 0 && rect.height > 0);
            // A one-line label keeps every text rect within half a line of the
            // topmost; per-character wrapping sits a full line lower.
            const spread = Math.max(...rects.map(rect => rect.top))
              - Math.min(...rects.map(rect => rect.top));
            if (rects.length && spread > lineHeight / 2) {
              multiLine.push(`${node.className}: spread ${spread.toFixed(1)}px of ${lineHeight}px`);
            }
          }
          return {multiLine, scrollWidth: document.scrollingElement.scrollWidth};
        });
        assert.deepEqual(result.multiLine, [],
          `one-line labels required at 390 ${theme}/${lang}: ${result.multiLine}`);
        assert.ok(result.scrollWidth <= 390,
          `no horizontal scroll at 390 ${theme}/${lang}: ${result.scrollWidth}`);
      }
    }
  }, {page: 'states'});
});

// F6 (only when fixed): the mobile page-header title computes to the 22px token.
test('F6: pagehead title computes to 22px at 390 through the token', async () => {
  await withRoutedPage(async page => {
    await page.setViewportSize({width: 390, height: 844});
    const fontSize = await page.evaluate(() => {
      const scope = document.querySelector('.intl-gs');
      const probe = document.createElement('h1');
      probe.className = 'intl-gs__pagehead__title';
      probe.textContent = 'probe';
      scope.appendChild(probe);
      const size = getComputedStyle(probe).fontSize;
      probe.remove();
      return size;
    });
    assert.equal(fontSize, '22px', 'the ≤900 override must resolve to the 22px token');
    // The override must be declared inside the ≤900 media block with the
    // existing token — never a px literal, never outside the breakpoint.
    const declared = await page.evaluate(() => {
      const found = [];
      for (const sheet of document.styleSheets) {
        for (const rule of sheet.cssRules) {
          // CSSMediaRule only (@import also carries .media but no cssRules).
          if (rule.conditionText && rule.cssRules) {
            for (const inner of rule.cssRules) {
              if (inner.selectorText === '.intl-gs__pagehead__title') {
                found.push(`${rule.conditionText} ${inner.style.fontSize}`);
              }
            }
          }
        }
      }
      return found;
    });
    assert.ok(declared.some(entry => /max-width:\s*900px/.test(entry)
      && entry.includes('var(--fs-num-lg)')),
    `expected a ≤900 var(--fs-num-lg) override, saw ${declared}`);
  }, {page: 'states'});
});

// F7a: the Loading and Empty state chips carry the --muted border (spec §7).
test('F7a: loading and empty chips carry the muted border in both themes', async () => {
  await withRoutedPage(async page => {
    for (const theme of ['dark', 'light']) {
      await page.evaluate(name => document.documentElement.setAttribute('data-theme', name), theme);
      for (const state of ['loading', 'empty']) {
        const border = await page.evaluate(name =>
          getComputedStyle(document.querySelector(
            `.intl-gs__statecell--${name} .intl-gs__chip`)).borderColor, state);
        assert.equal(border, await tokenColor(page, '--muted'),
          `${state} chip border must be --muted in ${theme}`);
      }
    }
  }, {page: 'states'});
});

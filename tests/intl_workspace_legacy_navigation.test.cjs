'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');
const { test } = require('node:test');
const { chromium } = require('playwright');

const entryPath = path.join(__dirname, '..', 'templates', 'intl_workspace_entry.js');
const unicodeId = 'ünï-目标';
const routedOrigin = 'http://127.0.0.1:45687';

let browser;

test.before(async () => {
  browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHROMIUM_CHANNEL });
});

test.after(async () => {
  if (browser) await browser.close();
});

async function createPage({ initialHash = '', outerLink = true, macroRoot = true, mountMode = 'normal' } = {}) {
  const context = await browser.newContext();
  const page = await context.newPage();
  page.setDefaultTimeout(1500);
  page.setDefaultNavigationTimeout(1500);

  const outer = outerLink ? '<a id="outer-link" href="#intl-legacy-research">Legacy</a>' : '';
  const rootHtml = macroRoot ? `
          <div id="macro" data-im-workspace data-im-mode="macro">
            <script type="application/json" data-im-config>{}</script>
            <button data-im-controls disabled></button>
            <details id="intl-legacy-research">
              <summary>Legacy</summary>
              <details id="legacy-nested">
                <summary>Nested</summary>
                <p id="lb-board">Board</p>
                <p id="${unicodeId}">Unicode target</p>
              </details>
            </details>
            <details id="unrelated"><p id="unrelated-target">Other</p></details>
            ${outer}
            <a id="board-link" href="#lb-board">Board</a>
          </div>` : '<details id="intl-legacy-research"><p id="lb-board">Board</p></details>';
  const html = `<!doctype html><html lang="en"><body>${rootHtml}</body></html>`;

  await context.route(`${routedOrigin}/workspace`, route => route.fulfill({ contentType: 'text/html; charset=utf-8', body: html }));
  const target = new URL(`${routedOrigin}/workspace`);
  target.hash = initialHash;
  await page.goto(target.href);

  await page.evaluate(mode => {
    // Production puts retained research after, outside, the enhanced root.
    const root = document.getElementById('macro');
    if (root) root.after(document.getElementById('intl-legacy-research'));
    window.mountCalls = 0;
    window.destroyCalls = 0;
    window.IntlWorkspace = {
      mountIntlWorkspace() {
        window.mountCalls += 1;
        if (mode === 'throw') throw new Error('mount failed');
        root.setAttribute('data-im-enhanced', '');
        return { destroy() { window.destroyCalls += 1; } };
      },
    };
  }, mountMode);
  await page.addScriptTag({ path: entryPath });
  return { context, page };
}

async function mountCalls(page) {
  return page.evaluate(() => window.mountCalls);
}

async function isOpen(page, selector) {
  return page.evaluate(id => document.getElementById(id).open, selector);
}

test('startup without hash leaves legacy collapsed', async () => {
  const { context, page } = await createPage();
  try {
    assert.equal(await mountCalls(page), 1);
    assert.equal(await page.getAttribute('button[data-im-controls]', 'disabled'), null);
    assert.equal(await isOpen(page, 'intl-legacy-research'), false);
  } finally {
    await context.close();
  }
});

test('startup opens the direct legacy target', async () => {
  const { context, page } = await createPage({ initialHash: '#intl-legacy-research' });
  try {
    assert.equal(await mountCalls(page), 1);
    assert.equal(await isOpen(page, 'intl-legacy-research'), true);
  } finally {
    await context.close();
  }
});

test('startup opens every containing nested disclosure', async () => {
  const { context, page } = await createPage({ initialHash: '#lb-board' });
  try {
    assert.equal(await isOpen(page, 'intl-legacy-research'), true);
    assert.equal(await isOpen(page, 'legacy-nested'), true);
  } finally {
    await context.close();
  }
});

test('startup accepts a percent-encoded Unicode ID', async () => {
  const { context, page } = await createPage({ initialHash: `#${encodeURIComponent(unicodeId)}` });
  try {
    assert.equal(await isOpen(page, 'intl-legacy-research'), true);
    assert.equal(await isOpen(page, 'legacy-nested'), true);
    assert.equal(await page.evaluate(() => document.getElementById(decodeURIComponent(location.hash.slice(1))).textContent), 'Unicode target');
  } finally {
    await context.close();
  }
});

test('hashchange reveals legacy and preserves state for malformed and unknown targets', async () => {
  const { context, page } = await createPage();
  try {
    await page.evaluate(() => {
      document.getElementById('unrelated').open = true;
      location.hash = '#lb-board';
    });
    await page.waitForFunction(() => document.getElementById('legacy-nested').open);
    assert.equal(await isOpen(page, 'intl-legacy-research'), true);
    assert.equal(await isOpen(page, 'unrelated'), true);

    await page.evaluate(() => { location.hash = '#%ZZ'; });
    await page.waitForFunction(() => location.hash === '#%ZZ');
    assert.equal(await isOpen(page, 'intl-legacy-research'), true);
    assert.equal(await isOpen(page, 'legacy-nested'), true);
    assert.equal(await isOpen(page, 'unrelated'), true);

    await page.evaluate(() => { location.hash = '#missing-target'; });
    await page.waitForFunction(() => location.hash === '#missing-target');
    assert.equal(await isOpen(page, 'intl-legacy-research'), true);
    assert.equal(await isOpen(page, 'legacy-nested'), true);
    assert.equal(await isOpen(page, 'unrelated'), true);
  } finally {
    await context.close();
  }
});

test('same-hash activation reopens a manually collapsed target', async () => {
  const { context, page } = await createPage();
  try {
    await page.evaluate(() => { location.hash = '#lb-board'; });
    await page.waitForFunction(() => document.getElementById('legacy-nested').open);
    await page.evaluate(() => {
      document.getElementById('legacy-nested').open = false;
      document.getElementById('intl-legacy-research').open = false;
    });
    await page.click('#board-link');
    await page.waitForFunction(() => document.getElementById('legacy-nested').open);
    assert.equal(await isOpen(page, 'intl-legacy-research'), true);
  } finally {
    await context.close();
  }
});

test('full and relative same-document URL activation reveals nested targets', async () => {
  const { context, page } = await createPage();
  try {
    await page.evaluate(() => {
      const link = document.getElementById('board-link');
      link.href = `${location.origin}${location.pathname}#lb-board`;
    });
    await page.click('#board-link');
    await page.waitForFunction(() => document.getElementById('legacy-nested').open);

    await page.evaluate(unicodeId => {
      document.getElementById('legacy-nested').open = false;
      const link = document.getElementById('board-link');
      link.setAttribute('href', `./workspace#${unicodeId}`);
    }, unicodeId);
    await page.click('#board-link');
    await page.waitForFunction(() => document.getElementById('intl-legacy-research').open && document.getElementById('legacy-nested').open);
  } finally {
    await context.close();
  }
});

test('nonlocal links do not reveal legacy details', async () => {
  const { context, page } = await createPage();
  try {
    await page.evaluate(origin => {
      const external = document.createElement('a');
      external.id = 'external-link';
      external.href = 'https://example.invalid/workspace#lb-board';
      const otherPath = document.createElement('a');
      otherPath.id = 'other-path-link';
      otherPath.href = `${origin}/other?x=1#lb-board`;
      for (const link of [external, otherPath]) {
        link.textContent = link.id;
        link.addEventListener('click', event => event.preventDefault());
        document.body.append(link);
      }
    }, routedOrigin);
    await page.click('#external-link');
    assert.equal(await isOpen(page, 'intl-legacy-research'), false);
    await page.click('#other-path-link');
    assert.equal(await isOpen(page, 'intl-legacy-research'), false);
  } finally {
    await context.close();
  }
});

test('the optional outer jump link can be absent', async () => {
  const { context, page } = await createPage({ initialHash: '#lb-board', outerLink: false });
  try {
    assert.equal(await mountCalls(page), 1);
    assert.equal(await isOpen(page, 'intl-legacy-research'), true);
    assert.equal(await isOpen(page, 'legacy-nested'), true);
  } finally {
    await context.close();
  }
});

test('failed mount enables graceful legacy fallback', async () => {
  const { context, page } = await createPage({ mountMode: 'throw' });
  try {
    assert.equal(await mountCalls(page), 1);
    assert.equal(await page.evaluate(() => window.destroyCalls), 0);
    assert.equal(await page.getAttribute('button[data-im-controls]', 'disabled'), '');
    assert.equal(await isOpen(page, 'intl-legacy-research'), true);
  } finally {
    await context.close();
  }
});

test('no macro root makes no mount call', async () => {
  const { context, page } = await createPage({ macroRoot: false });
  try {
    assert.equal(await mountCalls(page), 0);
    assert.equal(await isOpen(page, 'intl-legacy-research'), false);
  } finally {
    await context.close();
  }
});

for (const initialHash of ['#%ZZ', '#missing-target', '#unrelated-target']) {
  test(`startup with ${initialHash} does not expose retained research`, async () => {
    const {context, page} = await createPage({initialHash});
    try {
      assert.equal(await isOpen(page, 'intl-legacy-research'), false);
      assert.equal(await isOpen(page, 'legacy-nested'), false);
      assert.equal(await mountCalls(page), 1);
    } finally { await context.close(); }
  });
}

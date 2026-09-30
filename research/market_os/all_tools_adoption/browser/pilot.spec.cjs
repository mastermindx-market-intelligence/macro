const { test, expect } = require('@playwright/test');
const fs = require('fs');
const os = require('os');
const path = require('path');

const pages = ['macro.html', 'sector_central.html', 'reports.html'];
const baseOrigin = new URL(process.env.SHARED_SHELL_BASE_URL || 'http://127.0.0.1:8877').origin;
const evidenceDir = process.env.SHARED_SHELL_EVIDENCE_DIR
  || path.join(os.tmpdir(), 'shared-shell-browser-evidence');
fs.mkdirSync(evidenceDir, { recursive: true });

async function openPage(page, route, { width = 1440, height = 1000, theme = 'dark', lang = 'en' } = {}) {
  await page.setViewportSize({ width, height });
  const assetStatuses = new Map();
  page.on('response', (response) => {
    const url = new URL(response.url());
    if (url.origin === baseOrigin
        && /(?:theme|account|nav_market)\.js$|navigation-refresh\.css$/.test(url.pathname)) {
      assetStatuses.set(url.pathname, response.status());
    }
  });
  await page.goto('/' + route, { waitUntil: 'domcontentloaded' });
  await page.evaluate(({ theme, lang }) => {
    document.documentElement.setAttribute('data-theme', theme);
    document.documentElement.setAttribute('data-lang', lang);
    document.dispatchEvent(new CustomEvent('langchange'));
  }, { theme, lang });
  const host = page.locator('[data-mmx-all-tools]');
  await expect(host).toHaveCount(1);
  await expect(host).toHaveAttribute('data-mmx-tools-mounted', 'true');
  const trigger = page.locator('nav.site-nav .nav-ctrls [data-tools-open]');
  await expect(trigger).toHaveCount(1);
  await expect(trigger).toBeVisible();
  await expect(page.locator('[data-mmx-all-tools] dialog')).toHaveCount(1);
  const cssHref = await page.locator('link[rel="stylesheet"][href*="navigation-refresh.css"]').getAttribute('href');
  expect(cssHref).toMatch(/navigation-refresh\.css\?v=[0-9a-f]{8}$/);
  return { host, trigger, assetStatuses };
}

async function openTools(page, trigger) {
  await trigger.click();
  const dialog = page.locator('[data-mmx-all-tools] dialog');
  await expect(dialog).toHaveAttribute('open', '');
  await expect(trigger).toHaveAttribute('aria-expanded', 'true');
  await expect(page.locator('html')).toHaveClass(/mmx-tools-open/);
  await expect(page.locator('[data-tools-results] a[data-tools-href]')).not.toHaveCount(0);
  return dialog;
}

for (const route of pages) {
  test(`${route}: desktop dark EN opens, searches, recovers, and returns focus`, async ({ page }) => {
    const { trigger, assetStatuses } = await openPage(page, route, { theme: 'dark', lang: 'en' });
    await openTools(page, trigger);
    const layout = await page.evaluate(() => {
      const shell = document.querySelector('.mmx-tools-shell').getBoundingClientRect();
      const footer = document.querySelector('.mmx-tools-footer');
      const footerBox = footer.getBoundingClientRect();
      const footerStyle = getComputedStyle(footer);
      return {
        shellWidth: shell.width,
        footerWidth: footerBox.width,
        footerMaxWidth: footerStyle.maxWidth,
        footerMarginTop: footerStyle.marginTop,
      };
    });
    expect(Math.abs(layout.footerWidth - layout.shellWidth)).toBeLessThan(1);
    expect(layout.footerMaxWidth).toBe('none');
    expect(layout.footerMarginTop).toBe('0px');

    const query = page.locator('[data-tools-query]');
    await expect(query).toBeFocused();
    await query.fill('market');
    await expect(page.locator('[data-tools-results] a[data-tools-href]')).not.toHaveCount(0);
    await expect(page.locator('[data-tools-status]')).not.toContainText(/changed|unavailable/i);

    await query.fill('tax-loss planner');
    await expect(page.locator('[data-tools-results]')).toContainText('No matching tools');
    const reset = page.locator('[data-tools-reset]');
    await expect(reset).toBeVisible();
    await reset.click();
    await expect(query).toHaveValue('');
    await expect(page.locator('[data-tools-results] a[data-tools-href]')).not.toHaveCount(0);

    await page.screenshot({ path: path.join(evidenceDir, `${route.replace('.html','')}-desktop-dark-en.png`) });
    await page.keyboard.press('Escape');
    await expect(page.locator('[data-mmx-all-tools] dialog')).not.toHaveAttribute('open', '');
    await expect(trigger).toBeFocused();
    await expect(trigger).toHaveAttribute('aria-expanded', 'false');
    await expect(page.locator('html')).not.toHaveClass(/mmx-tools-open/);

    for (const required of ['/theme.js', '/account.js', '/nav_market.js']) {
      const match = [...assetStatuses.entries()].find(([p]) => p.endsWith(required));
      expect(match, `${required} response observed`).toBeTruthy();
      expect(match[1], `${required} HTTP status`).toBe(200);
    }
  });

  test(`${route}: mobile light ZH opens as a sheet with title focus`, async ({ page }) => {
    const { trigger } = await openPage(page, route, { width: 390, height: 844, theme: 'light', lang: 'zh' });
    await openTools(page, trigger);
    const title = page.locator('[data-tools-title]');
    await expect(title).toBeFocused();
    await expect(title).toHaveText('所有工具');
    await expect(page.locator('[data-tools-query]')).toHaveAttribute('aria-label', '搜索工具，而非股票代码');
    const dialog = page.locator('[data-mmx-all-tools] dialog');
    const box = await dialog.boundingBox();
    expect(box).toBeTruthy();
    expect(box.width).toBeLessThanOrEqual(390.5);
    expect(box.height).toBeLessThanOrEqual(844.5);
    await expect(page.locator('[data-tools-close]')).toBeVisible();
    await page.screenshot({ path: path.join(evidenceDir, `${route.replace('.html','')}-mobile-light-zh.png`) });
  });
}

test('foreign modal blocks All tools without disturbing the existing overlay', async ({ page }) => {
  const { trigger } = await openPage(page, 'macro.html', { theme: 'dark', lang: 'en' });
  await page.evaluate(() => {
    const dialog = document.createElement('dialog');
    dialog.id = 'foreign-proof-dialog';
    dialog.textContent = 'Existing overlay';
    document.body.appendChild(dialog);
    dialog.showModal();
  });
  // The top-layer modal correctly intercepts pointer input. Dispatch activation
  // directly to verify that the controller itself still refuses modal stacking.
  await trigger.evaluate((element) => element.click());
  await expect(page.locator('#foreign-proof-dialog')).toHaveAttribute('open', '');
  await expect(page.locator('[data-mmx-all-tools] dialog')).not.toHaveAttribute('open', '');
  await expect(trigger).toHaveAttribute('aria-expanded', 'false');
  await page.locator('#foreign-proof-dialog').evaluate((dialog) => dialog.close());
  await trigger.click();
  await expect(page.locator('[data-mmx-all-tools] dialog')).toHaveAttribute('open', '');
});

test('live source withdrawal disables the projected destination before navigation', async ({ page }) => {
  const { trigger } = await openPage(page, 'macro.html', { theme: 'dark', lang: 'en' });
  await openTools(page, trigger);
  const projected = page.locator('[data-tools-results] a[data-tools-href]').first();
  const href = await projected.getAttribute('data-tools-href');
  expect(href).toBeTruthy();
  const removed = await page.evaluate((targetHref) => {
    const sources = [...document.querySelectorAll('nav.site-nav .nav-links a[href]')]
      .filter((anchor) => anchor.href === targetHref);
    sources.forEach((source) => source.remove());
    return sources.length;
  }, href);
  expect(removed).toBeGreaterThan(0);
  const projectedForHref = page.locator(`[data-tools-results] a[data-tools-href=${JSON.stringify(href)}]`);
  await expect(projectedForHref).toHaveAttribute('aria-disabled', 'true');
  await expect(projectedForHref).not.toHaveAttribute('href', /.+/);
  await expect(page.locator('[data-tools-status]')).toContainText(/changed|unavailable/i);
});

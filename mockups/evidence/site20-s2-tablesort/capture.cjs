'use strict';
/* Evidence capture for site20 S2 tablesort (S2-02 keyboard sort + aria-sort,
   S2-04 filter status + no-results reset). Serves nothing itself: it drives a
   page that a LOCAL server (python3 -m http.server <port> --bind 127.0.0.1
   --directory site) already exposes, and refuses every non-127.0.0.1 request.

   Usage: node capture.cjs <pagePath> <port> <outDir> [requestsLog]
     pagePath — e.g. /hk.html (the real built page, table index 2 = the
                13-row sector table the round-1 census identified)
     port     — the local server's port
     outDir   — output directory for the PNG crops
     requestsLog — optional r2b request log (appended): every same-origin
                response with status >= 400 plus every aborted external
                host, and one summary line per run. The capture gate is
                stylesheet=0 script=0 — a 404 stylesheet means the page
                rendered without its CSS (the r2 defect this log exists to
                catch ever recurring).

   States × theme(dark|light) × lang(en|zh) × viewport(1440|390) = 32 PNGs
   named <state>--<theme>--<lang>--<vw>.png. Every crop is the union of the
   filter bar and the table's header + first 6 data rows, clipped to the
   viewport width and at most 480 px tall — never a full-page shot.
   With the page stylesheet present (r2b) the table lives inside the
   hkx-dlg-sector modal; each context opens it via window.hkxOpenDlg before
   capturing (display:none until then — the page's own trigger cards do the
   same).

   Synthetic hydration is labelled here and in README.md: two cloned rows with
   tokens ZZTEST13/ZZTEST14 are appended so the "one" state has a deterministic
   single match. Synthetic query/hydration on a real built page; local server;
   not production. */
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');

const [,, PAGE_PATH, PORT, OUT_DIR, REQ_LOG] = process.argv;
if (!PAGE_PATH || !PORT || !OUT_DIR) {
  console.error('usage: node capture.cjs <pagePath> <port> <outDir> [requestsLog]');
  process.exit(2);
}
const BASE = 'http://127.0.0.1:' + PORT;
const TABLE_IDX = 2;   // 13-row sector table (Sector / 20d RS / State) — has the filter
const NUM_COL = 1;     // "20d RS" numeric column
const THEMES = ['dark', 'light'];
const LANGS = ['en', 'zh'];
const VWS = [['1440', [1440, 900]], ['390', [390, 844]]];
const NO_MATCH = {en: 'No matching rows · 0 / ', zh: '无匹配行 · 0 / '};

// crop = union of the filter bar + the table's header + first 6 data rows,
// clipped to the viewport width and at most 480 px tall. Under an active
// filter, hidden rows collapse to zero height, so the union runs over the
// first 6 VISIBLE data rows (a filtered table shows fewer). Non-full-page
// screenshots do not scroll: put the region at the top of the viewport first,
// then hand back VIEWPORT-relative clip coordinates.
// With the page stylesheet present (r2b) the sector table lives inside the
// hkx-dlg-sector modal dialog; .hkx-dlg itself is the scroll container
// (position:fixed; overflow:auto), so the region is raised by scrolling the
// OPEN DIALOG, never window (body is overflow:hidden while a dialog is open).
async function cropRect(page) {
  await page.evaluate(({TABLE_IDX}) => {
    const t = document.querySelectorAll('table')[TABLE_IDX];
    const wrap = document.querySelector('.tbl-filter');
    const header = (t.tHead && t.tHead.rows[0]) || t.tBodies[0].rows[0];
    const top = Math.min(wrap.getBoundingClientRect().top, header.getBoundingClientRect().top);
    const sc = document.querySelector('.hkx-dlg.open') || document.scrollingElement;
    sc.scrollTop = Math.max(0, sc.scrollTop + top - 8);
  }, {TABLE_IDX});
  await page.waitForTimeout(250); // settle (site CSS may animate scrolling)
  return page.evaluate(({TABLE_IDX}) => {
    const t = document.querySelectorAll('table')[TABLE_IDX];
    const wrap = document.querySelector('.tbl-filter');
    const header = (t.tHead && t.tHead.rows[0]) || t.tBodies[0].rows[0];
    const rows = Array.prototype.slice.call(t.tBodies[0].rows);
    const dataRows = t.tHead ? rows : rows.slice(1);
    const vis6 = dataRows.filter(r => r.style.display !== 'none').slice(0, 6);
    const fr = wrap.getBoundingClientRect();
    const hr = header.getBoundingClientRect();
    const vr = vis6.map(r => r.getBoundingClientRect());
    const vw = window.innerWidth;
    const x = Math.max(0, Math.min(fr.left, hr.left));
    const right = Math.max.apply(null, [fr.right, hr.right].concat(vr.map(r => r.right)));
    const y = Math.max(0, Math.min(fr.top, hr.top));
    const bottom = Math.max.apply(null, [fr.bottom, hr.bottom].concat(vr.map(r => r.bottom)));
    return {
      x: x,
      y: y,
      width: Math.max(60, Math.min(right - x, vw - x)),
      height: Math.max(60, Math.min(bottom - y, 480)),
    };
  }, {TABLE_IDX});
}

async function waitStatus(page, expected) {
  await page.waitForFunction((e) => {
    const el = document.querySelector('.tbl-filter .cnt');
    return el && el.textContent === e;
  }, expected, {timeout: 4000, polling: 50});
}

async function main() {
  const browser = await chromium.launch({headless: true});
  let n = 0;
  const badResponses = [];   // {url, status, resourceType} for same-origin >= 400
  const abortedHosts = new Set();
  for (const theme of THEMES) {
    for (const lang of LANGS) {
      for (const [vwName, vp] of VWS) {
        const context = await browser.newContext({viewport: {width: vp[0], height: vp[1]}});
        const page = await context.newPage();
        page.setDefaultTimeout(30000);
        page.on('response', r => {
          if (r.status() >= 400) badResponses.push({url: r.url(), status: r.status(), resourceType: r.request().resourceType()});
        });
        await page.route('**/*', async route => {
          if (new URL(route.request().url()).hostname !== '127.0.0.1') {
            abortedHosts.add(new URL(route.request().url()).hostname);
            return route.abort();
          }
          return route.continue();
        });
        await page.goto(BASE + PAGE_PATH, {waitUntil: 'load'});
        await page.waitForTimeout(1000);
        await page.evaluate(t => window.setTheme(t), theme);
        await page.waitForTimeout(1200); // theme transition
        await page.evaluate(l => window.setLang(l), lang);
        await page.waitForTimeout(300);
        // The complete page keeps the sector table inside the hkx-dlg-sector
        // modal (display:none until opened) — open it like the page's own
        // trigger card does, then let the entrance settle.
        await page.evaluate(() => window.hkxOpenDlg('hkx-dlg-sector'));
        await page.waitForTimeout(400);

        // rest: after load, no query, pristine population
        await page.screenshot({clip: await cropRect(page),
          path: path.join(OUT_DIR, 'rest--' + theme + '--' + lang + '--' + vwName + '.png')});
        n++;

        // keyfocus: numeric header focused BY KEYBOARD (Tab arms keyboard modality,
        // then focus) and sorted with Enter — focus ring should be visible
        const input = page.locator('.tbl-filter input').first();
        await input.click();
        await page.keyboard.press('Tab');
        await page.evaluate(({TABLE_IDX, NUM_COL}) => {
          const t = document.querySelectorAll('table')[TABLE_IDX];
          ((t.tHead && t.tHead.rows[0]) || t.tBodies[0].rows[0]).cells[NUM_COL].focus();
        }, {TABLE_IDX, NUM_COL});
        await page.keyboard.press('Enter');
        await page.waitForTimeout(300);
        await page.screenshot({clip: await cropRect(page),
          path: path.join(OUT_DIR, 'keyfocus--' + theme + '--' + lang + '--' + vwName + '.png')});
        n++;

        // SYNTHETIC hydration: 2 cloned rows, tokens ZZTEST13 / ZZTEST14
        await page.evaluate(({TABLE_IDX}) => {
          const t = document.querySelectorAll('table')[TABLE_IDX];
          const rows = Array.prototype.slice.call(t.tBodies[0].rows);
          const dataRows = t.tHead ? rows : rows.slice(1);
          ['ZZTEST13', 'ZZTEST14'].forEach(tok => {
            const clone = dataRows[0].cloneNode(true);
            clone.cells[0].textContent = tok;
            t.tBodies[0].appendChild(clone);
          });
        }, {TABLE_IDX});
        await page.waitForTimeout(200);

        // one: query matching exactly one row
        await input.click();
        await input.fill('');
        await input.pressSequentially('ZZTEST13', {delay: 15});
        await waitStatus(page, '1 / 15');
        await page.screenshot({clip: await cropRect(page),
          path: path.join(OUT_DIR, 'one--' + theme + '--' + lang + '--' + vwName + '.png')});
        n++;

        // nomatch: status + reset button visible
        await input.fill('');
        await input.pressSequentially('qqqnomatchqqq', {delay: 15});
        await waitStatus(page, NO_MATCH[lang] + '15');
        await page.waitForTimeout(150);
        await page.screenshot({clip: await cropRect(page),
          path: path.join(OUT_DIR, 'nomatch--' + theme + '--' + lang + '--' + vwName + '.png')});
        n++;

        await context.close();
      }
    }
  }
  await browser.close();
  console.log('captured ' + n + ' PNGs into ' + OUT_DIR);
  if (REQ_LOG) {
    const buckets = {stylesheet: 0, script: 0, font: 0, other: 0};
    for (const r of badResponses) {
      if (r.resourceType in buckets) buckets[r.resourceType]++;
      else buckets.other++;
    }
    const out = [];
    out.push('=== capture.cjs run ' + new Date().toISOString() + ' — ' + n + ' PNGs, ' + badResponses.length + ' same-origin >=400 response(s) ===');
    for (const r of badResponses) out.push('  detail: ' + r.status + ' ' + r.resourceType + ' ' + r.url);
    out.push('same-origin 4xx/5xx: stylesheet=' + buckets.stylesheet + ' script=' + buckets.script +
      ' font=' + buckets.font + ' other=' + buckets.other +
      '; aborted external hosts=' + (Array.from(abortedHosts).sort().join(',') || '(none)'));
    fs.appendFileSync(REQ_LOG, out.join('\n') + '\n');
  }
}
main().catch(e => { console.error(e); process.exit(1); });

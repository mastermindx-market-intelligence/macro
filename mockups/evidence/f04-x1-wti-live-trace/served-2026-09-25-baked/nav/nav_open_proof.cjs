// Served nav-reachability proof (anonymous): macro.html -> shared nav -> ontology item -> ontology.html.
// usage: NODE_PATH=<pw modules> node nav_open_proof.cjs <base_url> <out_dir>
const { chromium } = require('playwright');
const crypto = require('crypto'), fs = require('fs'), path = require('path');
const BASE = process.argv[2], OUT = process.argv[3]; fs.mkdirSync(OUT, { recursive: true });
const SEL = 'a.nav-mega-item[href$="ontology.html"], .site-nav a[href$="ontology.html"], nav a[href$="ontology.html"]';
const sha = f => crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
const cells = [];
for (const vp of [['desktop', 1440, 900], ['mobile', 390, 844]]) for (const lang of ['en', 'zh']) for (const theme of ['dark', 'light']) cells.push({ vp, lang, theme });
(async () => {
  const browser = await chromium.launch(); const results = [];
  for (const c of cells) {
    const mobile = c.vp[0] === 'mobile';
    const ctx = await browser.newContext({ viewport: { width: c.vp[1], height: c.vp[2] }, userAgent: 'mastermind-seat-proof/1', deviceScaleFactor: 1, isMobile: mobile, hasTouch: mobile, locale: c.lang === 'zh' ? 'zh-CN' : 'en-US' });
    await ctx.addInitScript(({ theme, lang }) => { try { localStorage.setItem('theme', theme); localStorage.removeItem('themeAuto'); localStorage.setItem('lang', lang); } catch (e) { } }, { theme: c.theme, lang: c.lang });
    const page = await ctx.newPage();
    const r = { viewport: c.vp[0], width: c.vp[1], locale: c.lang, theme: c.theme, route: '/macro.html' };
    try {
      const resp = await page.goto(BASE + '/macro.html', { waitUntil: 'load', timeout: 60000 });
      r.status = resp && resp.status(); await page.waitForTimeout(2500);
      r.applied_theme = await page.evaluate(() => document.documentElement.getAttribute('data-theme'));
      r.applied_lang = await page.evaluate(() => document.documentElement.getAttribute('data-lang'));
      Object.assign(r, await page.evaluate((SEL) => {
        const item = document.querySelector(SEL); if (!item) return { found: false };
        const toggle = document.querySelector('.nav-toggle'); let mobileOpened = false;
        if (toggle && getComputedStyle(toggle).display !== 'none') { toggle.click(); mobileOpened = true; }
        const dd = item.closest('.nav-dd'); const trig = dd ? dd.querySelector(':scope > a') : null; if (trig && mobileOpened) trig.click();
        return { found: true, mobileOpened, trigger: trig ? trig.textContent.replace(/\s+/g, ' ').trim().slice(0, 40) : null, ddOpen: dd ? dd.classList.contains('open') : null };
      }, SEL));
      if (!mobile) { await page.hover('.nav-dd:has(a[href$="ontology.html"]) > a'); r.hovered = 'trigger'; await page.waitForTimeout(700); await page.hover(SEL); r.hovered = 'trigger, then item (auto-scrolled into view, pointer kept inside the open panel)'; }
      await page.waitForTimeout(700);
      r.ddOpen = await page.evaluate(() => { const dd = document.querySelector('.nav-dd:has(a[href$="ontology.html"])'); return dd ? dd.classList.contains('open') : null; });
      r.item = await page.evaluate(([SEL, mobile]) => {
        const item = document.querySelector(SEL); if (!item) return null; if (mobile) item.scrollIntoView({ block: 'center' });
        const b = item.getBoundingClientRect(), cs = getComputedStyle(item);
        return { text: item.textContent.replace(/\s+/g, ' ').trim().slice(0, 60), href: item.getAttribute('href'), box: [b.x, b.y, b.width, b.height].map(Math.round), visible: b.width > 0 && b.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none' && parseFloat(cs.opacity || '1') > 0.5 && b.bottom > 0 && b.top < innerHeight };
      }, [SEL, mobile]);
      await page.waitForTimeout(300);
      const n1 = `nav-open-macro-${c.vp[0]}-${c.lang}-${c.theme}.png`; await page.screenshot({ path: path.join(OUT, n1) }); r.screenshot = n1; r.screenshot_sha256 = sha(path.join(OUT, n1));
      if (r.item && r.item.visible) {
        await Promise.all([page.waitForNavigation({ waitUntil: 'load', timeout: 60000 }).catch(() => null), page.click(SEL)]);
        await page.waitForTimeout(800); r.landed_url = page.url(); r.landed_title = await page.title();
        const n2 = `nav-landed-ontology-${c.vp[0]}-${c.lang}-${c.theme}.png`; await page.screenshot({ path: path.join(OUT, n2) }); r.landed_screenshot = n2; r.landed_sha256 = sha(path.join(OUT, n2));
        r.landed_excerpt = await page.evaluate(() => (document.body.innerText || '').replace(/\s+/g, ' ').slice(0, 240));
      }
      r.captured = !!(r.item && r.item.visible && r.landed_url && /ontology\.html/.test(r.landed_url));
    } catch (e) { r.captured = false; r.error = String(e).slice(0, 300); }
    results.push(r); await ctx.close();
  }
  await browser.close();
  const receipt = { schema: 'mastermind.f04_served_nav_reachability.v1', generated_at: new Date().toISOString().replace(/\.\d+Z$/, 'Z'), base_url: BASE, access: 'anonymous (no credential entered; the landing is the anonymous gate state)', journey: 'macro.html -> shared nav (hamburger on mobile) -> dropdown trigger -> ontology item click -> ontology.html', cells: results, totals: { attempted: results.length, captured: results.filter(x => x.captured).length } };
  fs.writeFileSync(path.join(OUT, 'nav-reachability.json'), JSON.stringify(receipt, null, 2) + '\n');
  console.log(JSON.stringify(receipt.totals));
  for (const x of results) console.log(`${x.viewport}/${x.locale}/${x.theme}: status=${x.status} theme=${x.applied_theme} lang=${x.applied_lang} mobileOpened=${x.mobileOpened} trigger=${JSON.stringify(x.trigger)} ddOpen=${x.ddOpen} visible=${x.item && x.item.visible} text=${JSON.stringify(x.item && x.item.text)} landed=${x.landed_url} ${x.error || ''}`);
})();

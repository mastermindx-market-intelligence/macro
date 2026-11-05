#!/usr/bin/env python3
"""S1 repair round 3 proof: at 390x844 (and 1440x900 for regression), dark/light x EN/ZH,
is the unavailable-state retry the topmost element at its centre, and does a real pointer
click on it re-read the account without a reload?

usage: probe_r3.py [--js <account.js to substitute>] --label <name> [--out <dir>]
Without --js this checkout's site/account.js is served as-is (variant fix).
Local-only and hermetic: reuses browser_s1's mock + routing; no production host is contacted."""
import argparse
import asyncio
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import browser_s1 as H  # noqa: E402
from playwright.async_api import async_playwright  # noqa: E402

HIT = """(sel) => {
  var b = document.querySelector(sel); var p = document.querySelector('.mmacc');
  function r(e){ if(!e) return null; var x=e.getBoundingClientRect(); return [Math.round(x.left),Math.round(x.top),Math.round(x.right),Math.round(x.bottom)]; }
  var hit = null, top = null;
  if (b) { var x=b.getBoundingClientRect(); var el=document.elementFromPoint(x.left+x.width/2, x.top+x.height/2);
           hit = el ? (el===b || b.contains(el)) : null;
           top = el ? (el.tagName + '#' + (el.id||'') + '.' + String(el.className||'').slice(0,40)) : null; }
  var orb = document.querySelector('.mmb-orb');
  return {panel: r(p), target: r(b), orb: r(orb), target_hit: hit, topmost_at_target: top, vw: innerWidth, vh: innerHeight};
}"""
STATE = """() => { var p=document.querySelector('.mmacc'); if(!p) return null;
  var n=p.querySelector('.mmacc-head:not(.mmacc-head-out) .mmacc-name');
  return {open: p.classList.contains('open'), unavailable: !!p.querySelector('[data-acct-state=unavailable]'),
          name: n ? n.textContent.trim() : null, noReload: window.__noReload || null}; }"""


async def one(br, variant, js, theme, lang, vw, vh):
    m = H.Mock(); m.acct_mode = "503"
    ctx, page, errs = await H.new_page(br, m, variant, js, theme=theme, lang=lang, viewport=(vw, vh))
    rec = {"theme": theme, "lang": lang, "viewport": f"{vw}x{vh}"}
    try:
        await H.open_acct(page, wait_name=False)
        await page.wait_for_selector("[data-acct-state=unavailable]", timeout=6000)
        await page.wait_for_timeout(600)
        await page.evaluate("() => { window.__noReload = 'kept'; }")
        rec.update(await page.evaluate(HIT, "[data-act=retry-load]"))
        reads_before = m.acct_reads
        m.acct_mode = "ok"
        try:
            await page.click("[data-act=retry-load]", timeout=3000)  # real pointer click, actionability checked
            await page.wait_for_selector(".mmacc.open .mmacc-head:not(.mmacc-head-out) .mmacc-name", timeout=6000)
            st = await page.evaluate(STATE)
            rec["P3"] = {"ok": bool(st and st["name"] and not st["unavailable"] and st["noReload"] == "kept"
                                    and m.acct_reads > reads_before),
                         "acct_reads_before": reads_before, "acct_reads_after": m.acct_reads, "state": st}
            # regression: the signed-in panel's sign-out-everywhere control stays reachable
            await page.locator("[data-act=signout-all]").scroll_into_view_if_needed()
            so = await page.evaluate(HIT, "[data-act=signout-all]")
            rec["signout_all"] = {k: so.get(k) for k in ("target", "target_hit", "topmost_at_target")}
            # report-only: the last control on the sheet (danger zone) once scrolled into view
            await page.locator("[data-act=show-delete]").scroll_into_view_if_needed()
            de = await page.evaluate(HIT, "[data-act=show-delete]")
            rec["show_delete"] = {k: de.get(k) for k in ("target", "target_hit", "topmost_at_target")}
        except Exception as e:  # noqa: BLE001
            rec["P3"] = {"ok": False, "error": repr(e)[:240]}
        rec["page_errors"] = list(errs)[:5]
    finally:
        await ctx.close()
    return rec


async def run(js_path, label, out_dir):
    js = Path(js_path).read_text(encoding="utf-8") if js_path else ""
    variant = "main" if js_path else "fix"  # "main" = substitute the given bytes for account.js
    served = js.encode() if js_path else (H.TREE_SITE / "account.js").read_bytes()
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(H.PORT), "--bind", "127.0.0.1",
                            "--directory", str(H.TREE_SITE)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    rows = []
    try:
        await asyncio.sleep(1.0)
        async with async_playwright() as pw:
            br = await pw.chromium.launch()
            for vw, vh in ((390, 844), (1440, 900)):
                for theme in ("dark", "light"):
                    for lang in ("en", "zh"):
                        rows.append(await one(br, variant, js, theme, lang, vw, vh))
            await br.close()
    finally:
        srv.terminate()
    out = {"label": label, "account_js_sha256": hashlib.sha256(served).hexdigest(), "rows": rows,
           "all_hit": all(r.get("target_hit") is True for r in rows),
           "all_signout_all_hit": all((r.get("signout_all") or {}).get("target_hit") is True for r in rows),
           "all_P3_ok": all(r.get("P3", {}).get("ok") is True for r in rows),
           "all_show_delete_hit": all((r.get("show_delete") or {}).get("target_hit") is True for r in rows)}
    (Path(out_dir) / f"probe_r3_{label}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    for r in rows:
        print(json.dumps({k: r.get(k) for k in ("viewport", "theme", "lang", "target", "orb", "target_hit", "topmost_at_target")}
                         | {"P3_ok": r.get("P3", {}).get("ok")}, ensure_ascii=False))
    print("ALL_HIT", out["all_hit"], "SIGNOUT_ALL_HIT", out["all_signout_all_hit"], "ALL_P3_OK", out["all_P3_ok"], "SHOW_DELETE_HIT", out["all_show_delete_hit"], "sha256", out["account_js_sha256"][:12])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--js")
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", default=str(HERE))
    a = ap.parse_args()
    asyncio.run(run(a.js, a.label, a.out))

#!/usr/bin/env python3
"""site20 S1 browser acceptance: account and preference continuity (S1-01..S1-04).

Real Chromium against the RENDERED consuming page (site/alerts.html, the Macro
product page whose settings gear carries the real theme segment and language
switch) served from the lane tree by a local http.server.

Local-only by construction: every request whose host is not the local server is
ABORTED (never sent), websockets are closed, and supabase.js is aborted so no
identity SDK runs. /api/account* is answered by an in-process mock with
fictional fixtures (pat.fictional@example.test / b.fictional@example.test).

  --variant fix   serve the tree's site/account.js (the candidate)
  --variant main  substitute origin/main's account.js bytes (red replay)

Writes browser_S1-0k.txt per task (+ shots/ and crops_inventory.json for fix).
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright

TREE_SITE = Path(__file__).resolve().parents[3] / "site"
PORT = 18821
HOST = f"127.0.0.1:{PORT}"
BASE = f"http://{HOST}"
PAGE = "alerts.html"

EN = {
    "unavail_t": "Can’t load your account right now",
    "guest_t": "Access session",
    "so_unknown": "We couldn’t confirm that your other devices were signed out. You’re still signed in here — try again later.",
    "saved": "Saved",
}
ZH = {
    "unavail_t": "暂时无法加载你的账户",
    "so_unknown": "无法确认其他设备已退出登录。你在此设备上仍处于登录状态，请稍后重试。",
}
RL_EN = "Too many requests — try again in a minute."
RL_ZH = "请求过多，请一分钟后再试。"


class Mock:
    """Stateful fictional backend. Pref POSTs apply at RESPONSE time (slow server)."""

    def __init__(self) -> None:
        self.email = "pat.fictional@example.test"
        self.name = "Pat Fictional"
        self.server_prefs = {"theme": "dark", "lang": "en"}
        self.alert = {"alert_email_optin": True, "alert_categories": ["thesis_window"],
                      "tz": "Europe/London", "quiet_hours": None}
        self.unset: list[str] = []
        self.acct_mode = "ok"
        self.acct_queue: list[tuple[str, float]] = []
        self.pref_plan: list[tuple] = []
        self.so_plan: tuple = ("json", 200, {"ok": True})
        self.pref_posts: list[dict] = []
        self.so_posts = 0
        self.acct_reads = 0

    def switch_to_b(self) -> None:
        self.email = "b.fictional@example.test"
        self.name = "Bo Fictional"
        self.server_prefs = {"theme": "dark", "lang": "en"}
        self.alert = {"alert_email_optin": True, "alert_categories": [], "tz": "Asia/Tokyo", "quiet_hours": None}

    def acct_body(self) -> dict:
        return {"authenticated": True, "email": self.email, "email_confirmed": True, "name": self.name,
                "tier": "pro", "plan_label": "Pro", "status": "active", "plans_url": "/plans.html",
                "providers": ["email"], "created_at": "2026-01-02T03:04:05Z",
                "last_sign_in_at": "2026-10-10T00:00:00Z", "prefs": dict(self.server_prefs)}


def make_handler(mock: Mock, variant: str, main_js: str):
    async def handle(route, request):
        u = urlparse(request.url)
        if u.netloc != HOST:
            return await route.abort()
        p = u.path
        if p.endswith("supabase.js"):
            return await route.abort()
        if variant == "main" and p.endswith("/account.js"):
            return await route.fulfill(status=200, content_type="application/javascript", body=main_js)
        if p == "/api/account":
            mock.acct_reads += 1
            mode, delay = mock.acct_queue.pop(0) if mock.acct_queue else (mock.acct_mode, 0.0)
            if delay:
                await asyncio.sleep(delay)
            if mode == "abort":
                return await route.abort()
            if mode == "503":
                return await route.fulfill(status=503, content_type="application/json", body=json.dumps({"detail": "unavailable"}))
            if mode == "401":
                return await route.fulfill(status=401, content_type="application/json", body=json.dumps({"authenticated": False}))
            if mode == "anon":
                return await route.fulfill(status=200, content_type="application/json", body=json.dumps({"authenticated": False}))
            if mode == "malformed":
                return await route.fulfill(status=200, content_type="application/json", body=json.dumps({"hello": "world"}))
            if mode == "nonjson":
                return await route.fulfill(status=200, content_type="text/html", body="<html>gateway</html>")
            return await route.fulfill(status=200, content_type="application/json", body=json.dumps(mock.acct_body()))
        if p == "/api/account/prefs":
            if request.method == "GET":
                return await route.fulfill(status=200, content_type="application/json",
                                           body=json.dumps({"prefs": dict(mock.alert), "unset": list(mock.unset)}))
            body = json.loads(request.post_data or "{}")
            rec = {"body": body, "t0": time.monotonic(), "t1": None, "email": mock.email}
            mock.pref_posts.append(rec)
            status, delay, rbody = mock.pref_plan.pop(0) if mock.pref_plan else (200, 0.0, None)
            if delay:
                await asyncio.sleep(delay)
            rec["t1"] = time.monotonic()
            if status == 0:
                return await route.abort()
            if status == 200:
                for k, v in body.items():
                    if k in ("theme", "lang"):
                        mock.server_prefs[k] = v
                    else:
                        mock.alert[k] = None if (k == "quiet_hours" and v == "off") else v
                rbody = {"ok": True, "prefs": {**mock.server_prefs, **mock.alert}}
            return await route.fulfill(status=status, content_type="application/json", body=json.dumps(rbody or {}))
        if p == "/api/account/signout-everywhere":
            mock.so_posts += 1
            kind, status, rbody = mock.so_plan
            if kind == "abort":
                return await route.abort()
            if kind == "text":
                return await route.fulfill(status=status, content_type="text/plain", body=str(rbody))
            return await route.fulfill(status=status, content_type="application/json", body=json.dumps(rbody))
        return await route.continue_()
    return handle


class Report:
    def __init__(self, name: str) -> None:
        self.name = name
        self.lines: list[str] = []
        self.npass = 0
        self.nfail = 0

    def check(self, cond: bool, label: str, detail: object = "") -> None:
        if cond:
            self.npass += 1
        else:
            self.nfail += 1
        self.lines.append(f"{'PASS' if cond else 'FAIL'} {label} :: {detail}")

    def text(self, variant: str) -> str:
        head = [f"# {self.name} browser acceptance — variant={variant} page=site/{PAGE} (local-only, fictional fixtures)",
                f"# result: {self.npass} pass / {self.nfail} fail"]
        return "\n".join(head + self.lines) + "\n"


async def new_page(browser, mock: Mock, variant: str, main_js: str, *, theme="dark", lang="en",
                   viewport=(1440, 900)):
    ctx = await browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
    seed = (
        "try{if(!sessionStorage.getItem('__s1seed')){localStorage.setItem('theme',%s);"
        "localStorage.setItem('lang',%s);localStorage.removeItem('themeAuto');"
        "sessionStorage.setItem('__s1seed','1');}}catch(e){}; window.MM_API = location.origin;"
    ) % (json.dumps(theme), json.dumps(lang))
    await ctx.add_init_script(seed)
    await ctx.route("**/*", make_handler(mock, variant, main_js))
    try:
        await ctx.route_web_socket(lambda url: True, lambda ws: ws.close())
    except Exception:
        pass
    page = await ctx.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)[:200]))
    await page.goto(f"{BASE}/{PAGE}", wait_until="domcontentloaded")
    await ready(page)
    return ctx, page, errors


async def ready(page) -> None:
    await page.wait_for_function(
        "() => !!(window.MMAccount && window.MDXAuth && document.getElementById('settings-open'))", timeout=20000)
    await page.evaluate(
        "() => { if (window.__soWrapped) return; window.__soWrapped = 1; window.__soCalls = 0;"
        " var o = window.MDXAuth.signOut; window.MDXAuth.signOut = function () { window.__soCalls++;"
        " return o.apply(this, arguments); }; }")


async def open_acct(page, wait_name=True) -> None:
    await page.evaluate("() => window.MMAccount.open()")
    if wait_name:
        await page.wait_for_selector(".mmacc.open .mmacc-name", timeout=6000)


async def attr(page, sel, name):
    return await page.evaluate("([s,n]) => { var e=document.querySelector(s); return e ? e.getAttribute(n) : null; }",
                               [sel, name])


async def txt(page, sel):
    return await page.evaluate("(s) => { var e=document.querySelector(s); return e ? e.textContent.trim() : null; }", sel)


async def is_open(page) -> bool:
    return await page.evaluate("() => { var p=document.querySelector('.mmacc'); return !!(p && p.classList.contains('open')); }")


async def open_gear(page) -> None:
    await page.click("#settings-open")
    await page.wait_for_selector("#settings-pop #set-theme-light", state="visible", timeout=4000)


def bodies(mock: Mock) -> list[dict]:
    return [r["body"] for r in mock.pref_posts]


# ----------------------------------------------------------------- S1-01 -----
async def s1_01(browser, variant, main_js) -> Report:
    R = Report("S1-01 theme/language preference persistence")

    # J1 rapid theme -> lang through the real gear controls (mouse), EN start
    m = Mock()
    ctx, page, errs = await new_page(browser, m, variant, main_js)
    try:
        await open_acct(page); await page.keyboard.press("Escape")
        R.check(not await is_open(page), "J1 Esc closes the account dialog", "")
        await open_gear(page)
        await page.click("#set-theme-light")
        await page.click("#settings-pop .lang-toggle")
        await page.wait_for_timeout(1600)
        R.check(bodies(m) == [{"theme": "light", "lang": "zh"}], "J1 theme then language (EN start) -> ONE POST carrying both", bodies(m))
        R.check(m.server_prefs == {"theme": "light", "lang": "zh"}, "J1 server holds both final values", m.server_prefs)
        st = (await attr(page, ".mmacc", "data-pref-theme"), await attr(page, ".mmacc", "data-pref-lang"))
        R.check(st == ("acked", "acked"), "J1 both fields acknowledged on the account root", st)
        # J7 reload keeps the persisted values (local + server) and does not echo a write
        n0 = len(m.pref_posts)
        await page.reload(wait_until="domcontentloaded"); await ready(page)
        await open_acct(page); await page.wait_for_timeout(1200)
        dl = (await attr(page, "html", "data-theme"), await attr(page, "html", "data-lang"))
        R.check(dl == ("light", "zh"), "J7 reload keeps theme=light lang=zh", dl)
        R.check(len(m.pref_posts) == n0, "J7 reload + account hydration sends no write", len(m.pref_posts) - n0)
        R.check(not errs, "J1/J7 no page errors", errs[:3])
    except Exception as e:  # noqa: BLE001
        R.check(False, "J1/J7 journey completed", repr(e)[:200])
    await ctx.close()

    # J1z reverse order from a ZH/light start: language -> theme
    m = Mock(); m.server_prefs = {"theme": "light", "lang": "zh"}
    ctx, page, errs = await new_page(browser, m, variant, main_js, theme="light", lang="zh")
    try:
        await open_acct(page); await page.keyboard.press("Escape")
        await open_gear(page)
        await page.click("#settings-pop .lang-toggle")
        await page.click("#set-theme-dark")
        await page.wait_for_timeout(1600)
        R.check(bodies(m) == [{"lang": "en", "theme": "dark"}], "J1z language then theme (ZH start) -> ONE POST carrying both", bodies(m))
        R.check(m.server_prefs == {"theme": "dark", "lang": "en"}, "J1z server holds both final values", m.server_prefs)
    except Exception as e:  # noqa: BLE001
        R.check(False, "J1z journey completed", repr(e)[:200])
    await ctx.close()

    # J2 repeated edits to one field keep its last value and the other field
    m = Mock()
    ctx, page, errs = await new_page(browser, m, variant, main_js)
    try:
        await open_acct(page); await page.keyboard.press("Escape")
        await open_gear(page)
        for sel in ("#set-theme-light", "#set-theme-dark", "#settings-pop .lang-toggle", "#set-theme-light"):
            await page.click(sel)
        await page.wait_for_timeout(1600)
        R.check(bodies(m) == [{"theme": "light", "lang": "zh"}], "J2 light,dark,lang,light -> ONE POST {theme:light,lang:zh}", bodies(m))
    except Exception as e:  # noqa: BLE001
        R.check(False, "J2 journey completed", repr(e)[:200])
    await ctx.close()

    # J3 a rejected save is not reported as saved
    m = Mock(); m.pref_plan = [(400, 0.0, {"detail": {"field": "theme", "en": "Theme not accepted", "zh": "主题未被接受"}})]
    ctx, page, errs = await new_page(browser, m, variant, main_js)
    try:
        await open_acct(page); await page.keyboard.press("Escape")
        await open_gear(page); await page.click("#set-theme-light")
        await page.wait_for_timeout(1400)
        st = await attr(page, ".mmacc", "data-pref-theme")
        R.check(st == "failed", "J3 HTTP 400 marks theme failed (not acked)", st)
        R.check(m.server_prefs["theme"] == "dark", "J3 server unchanged", m.server_prefs)
    except Exception as e:  # noqa: BLE001
        R.check(False, "J3 journey completed", repr(e)[:200])
    await ctx.close()

    # J4 an older slow response cannot undo a later edit (single flight)
    m = Mock(); m.pref_plan = [(200, 1.5, None)]
    ctx, page, errs = await new_page(browser, m, variant, main_js)
    try:
        await open_acct(page); await page.keyboard.press("Escape")
        await open_gear(page); await page.click("#set-theme-light")
        await page.wait_for_timeout(750)
        await page.click("#set-theme-dark")
        await page.wait_for_timeout(3200)
        b = bodies(m)
        R.check(b == [{"theme": "light"}, {"theme": "dark"}], "J4 requests carry light then dark", b)
        overlap = len(m.pref_posts) >= 2 and m.pref_posts[1]["t0"] < (m.pref_posts[0]["t1"] or 1e18)
        R.check(len(m.pref_posts) == 2 and not overlap, "J4 second write starts only after the first returns", f"overlap={overlap}")
        R.check(m.server_prefs["theme"] == "dark", "J4 final server theme = last edit (dark)", m.server_prefs)
        st = await attr(page, ".mmacc", "data-pref-theme")
        R.check(st == "acked", "J4 theme acknowledged", st)
    except Exception as e:  # noqa: BLE001
        R.check(False, "J4 journey completed", repr(e)[:200])
    await ctx.close()

    # J5 hydration from server prefs does not echo writes
    m = Mock(); m.server_prefs = {"theme": "light", "lang": "zh"}
    ctx, page, errs = await new_page(browser, m, variant, main_js)
    try:
        await open_acct(page); await page.wait_for_timeout(1400)
        dl = (await attr(page, "html", "data-theme"), await attr(page, "html", "data-lang"))
        R.check(dl == ("light", "zh"), "J5 server prefs hydrate theme+lang", dl)
        R.check(m.pref_posts == [], "J5 hydration sends no write", bodies(m))
    except Exception as e:  # noqa: BLE001
        R.check(False, "J5 journey completed", repr(e)[:200])
    await ctx.close()

    # J6 an account transition drops the previous account's pending prefs
    m = Mock()
    ctx, page, errs = await new_page(browser, m, variant, main_js)
    try:
        await open_acct(page); await page.keyboard.press("Escape")
        await open_gear(page); await page.click("#set-theme-light")
        m.switch_to_b()
        await page.evaluate("() => window.dispatchEvent(new CustomEvent('mdx-auth', {detail: {user: {email: 'b.fictional@example.test'}, event: 'SIGNED_IN'}}))")
        await page.wait_for_timeout(1400)
        R.check(m.pref_posts == [], "J6 pending theme of account A is not sent after switch to B", [(r['email'], r['body']) for r in m.pref_posts])
    except Exception as e:  # noqa: BLE001
        R.check(False, "J6 journey completed", repr(e)[:200])
    await ctx.close()

    # J8 keyboard: gear Enter, theme Enter, language Space
    m = Mock()
    ctx, page, errs = await new_page(browser, m, variant, main_js)
    try:
        await open_acct(page); await page.keyboard.press("Escape")
        await page.focus("#settings-open"); await page.keyboard.press("Enter")
        await page.wait_for_selector("#settings-pop #set-theme-light", state="visible", timeout=4000)
        await page.focus("#set-theme-light"); await page.keyboard.press("Enter")
        await page.focus("#settings-pop .lang-toggle"); await page.keyboard.press(" ")
        await page.wait_for_timeout(1600)
        R.check(bodies(m) == [{"theme": "light", "lang": "zh"}], "J8 keyboard theme(Enter)+language(Space) -> ONE POST with both", bodies(m))
    except Exception as e:  # noqa: BLE001
        R.check(False, "J8 journey completed", repr(e)[:200])
    await ctx.close()
    return R


# ----------------------------------------------------------------- S1-02 -----
async def s1_02(browser, variant, main_js) -> Report:
    R = Report("S1-02 notification-preference acknowledgements")

    async def setup(m, lang="en"):
        ctx, page, errs = await new_page(browser, m, variant, main_js, lang=lang)
        await open_acct(page)
        await page.wait_for_selector("#mmacc-tz", timeout=6000)
        return ctx, page, errs

    # T1 delayed ack stores its OWN submitted value; T2 newer edit survives
    m = Mock(); m.pref_plan = [(200, 1.5, None), (200, 0.8, None)]
    ctx, page, errs = await setup(m)
    try:
        await page.select_option("#mmacc-tz", "America/New_York")
        await page.wait_for_timeout(800)
        await page.select_option("#mmacc-tz", "Asia/Hong_Kong")
        await page.wait_for_timeout(1500)   # first reply landed, second in flight
        mid = await attr(page, "#mmacc-tz", "data-prev")
        R.check(mid == "America/New_York", "T1 first ack records ITS submitted value as acked (data-prev)", mid)
        R.check(await page.input_value("#mmacc-tz") == "Asia/Hong_Kong", "T1 newer selection kept while second write in flight", await page.input_value("#mmacc-tz"))
        await page.wait_for_timeout(1500)
        R.check(bodies(m) == [{"tz": "America/New_York"}, {"tz": "Asia/Hong_Kong"}], "T1 request values = NY then HK", bodies(m))
        fin = (await attr(page, "#mmacc-tz", "data-prev"), await page.input_value("#mmacc-tz"), m.alert["tz"])
        R.check(fin == ("Asia/Hong_Kong",) * 3, "T1 final acked/visible/server = HK", fin)
        R.check(await txt(page, "#mmacc-alert-msg") == EN["saved"], "T1 visible copy 'Saved'", await txt(page, "#mmacc-alert-msg"))
        # reload state
        await page.reload(wait_until="domcontentloaded"); await ready(page); await open_acct(page)
        await page.wait_for_selector("#mmacc-tz", timeout=6000)
        R.check(await page.input_value("#mmacc-tz") == "Asia/Hong_Kong", "T1 reload shows acked HK", await page.input_value("#mmacc-tz"))
    except Exception as e:  # noqa: BLE001
        R.check(False, "T1 journey completed", repr(e)[:200])
    await ctx.close()

    # T2 an OLD failure cannot roll back a newer edit
    m = Mock(); m.pref_plan = [(502, 1.5, {"detail": "bad gateway"}), (200, 0.0, None)]
    ctx, page, errs = await setup(m)
    try:
        await page.select_option("#mmacc-tz", "America/New_York")
        await page.wait_for_timeout(800)
        await page.select_option("#mmacc-tz", "Asia/Hong_Kong")
        await page.wait_for_timeout(1300)
        v = await page.input_value("#mmacc-tz")
        R.check(v == "Asia/Hong_Kong", "T2 old 502 does not revert the newer selection", v)
        await page.wait_for_timeout(1500)
        fin = (await attr(page, "#mmacc-tz", "data-prev"), await page.input_value("#mmacc-tz"), m.alert["tz"])
        R.check(fin == ("Asia/Hong_Kong",) * 3, "T2 newer edit acked after old failure", fin)
    except Exception as e:  # noqa: BLE001
        R.check(False, "T2 journey completed", repr(e)[:200])
    await ctx.close()

    # T3 visible error copy EN + ZH; control returns to the acked value
    for lg, want in (("en", "Unknown time zone"), ("zh", "未知时区")):
        m = Mock(); m.pref_plan = [(400, 0.0, {"detail": {"field": "tz", "en": "Unknown time zone", "zh": "未知时区"}})]
        m.server_prefs = {"theme": "dark", "lang": lg}  # account prefs hydrate lang; seed must agree
        ctx, page, errs = await setup(m, lang=lg)
        try:
            await page.select_option("#mmacc-tz", "America/New_York")
            await page.wait_for_timeout(1300)
            msg = await txt(page, "#mmacc-alert-msg")
            R.check(msg == want, f"T3 400 shows server copy ({lg})", msg)
            R.check(await page.input_value("#mmacc-tz") == "Europe/London", f"T3 control back to acked Europe/London ({lg})", await page.input_value("#mmacc-tz"))
        except Exception as e:  # noqa: BLE001
            R.check(False, f"T3 journey completed ({lg})", repr(e)[:200])
        await ctx.close()

    # T4 opt-in success + failure
    m = Mock(); m.pref_plan = [(200, 0.0, None), (502, 0.0, {"detail": "bad gateway"})]
    ctx, page, errs = await setup(m)
    try:
        await page.click("[data-act=alert-optin]"); await page.wait_for_timeout(1000)
        R.check(bodies(m)[-1:] == [{"alert_email_optin": False}] and await attr(page, "[data-act=alert-optin]", "aria-checked") == "false",
                "T4 opt-in off saved", (bodies(m), await attr(page, "[data-act=alert-optin]", "aria-checked")))
        await page.click("[data-act=alert-optin]"); await page.wait_for_timeout(1000)
        R.check(await attr(page, "[data-act=alert-optin]", "aria-checked") == "false",
                "T4 failed opt-in on reverts to acked off", await attr(page, "[data-act=alert-optin]", "aria-checked"))
    except Exception as e:  # noqa: BLE001
        R.check(False, "T4 journey completed", repr(e)[:200])
    await ctx.close()

    # T5 category + quiet hours
    m = Mock()
    ctx, page, errs = await setup(m)
    try:
        await page.click("[data-act=alert-cat][data-cat=holdings_material_change]"); await page.wait_for_timeout(1000)
        cats = bodies(m)[-1].get("alert_categories") if m.pref_posts else None
        R.check(sorted(cats or []) == ["holdings_material_change", "thesis_window"], "T5 category write carries both categories", cats)
        await page.fill("#mmacc-qh-start", "22:00"); await page.fill("#mmacc-qh-end", "07:00")
        await page.wait_for_timeout(1100)
        R.check(m.alert["quiet_hours"] == {"start": "22:00", "end": "07:00"} and await attr(page, ".mmacc-alerts", "data-quiet") == "true",
                "T5 quiet hours saved + data-quiet=true", (m.alert["quiet_hours"], await attr(page, ".mmacc-alerts", "data-quiet")))
        await page.click("[data-act=alert-qh-clear]"); await page.wait_for_timeout(1100)
        R.check(m.alert["quiet_hours"] is None and await attr(page, ".mmacc-alerts", "data-quiet") == "false",
                "T5 quiet hours cleared", (m.alert["quiet_hours"], await attr(page, ".mmacc-alerts", "data-quiet")))
    except Exception as e:  # noqa: BLE001
        R.check(False, "T5 journey completed", repr(e)[:200])
    await ctx.close()

    # T6 close/reopen: a late ack lands on the re-rendered control of the SAME account
    m = Mock(); m.pref_plan = [(200, 1.2, None)]
    ctx, page, errs = await setup(m)
    try:
        await page.select_option("#mmacc-tz", "America/New_York")
        await page.wait_for_timeout(700)
        await page.keyboard.press("Escape"); await page.evaluate("() => window.MMAccount.open()")
        await page.wait_for_timeout(1500)
        fin = (await attr(page, "#mmacc-tz", "data-prev"), await page.input_value("#mmacc-tz"))
        R.check(fin == ("America/New_York", "America/New_York"), "T6 reopen shows the acked value after the late ack", fin)
    except Exception as e:  # noqa: BLE001
        R.check(False, "T6 journey completed", repr(e)[:200])
    await ctx.close()

    # T7 account switch: account A's late ack cannot mutate account B's controls
    m = Mock(); m.pref_plan = [(200, 1.5, None)]
    ctx, page, errs = await setup(m)
    try:
        await page.select_option("#mmacc-tz", "America/New_York")
        await page.wait_for_timeout(700)
        m.switch_to_b()
        await page.evaluate("() => window.dispatchEvent(new CustomEvent('mdx-auth', {detail: {user: {email: 'b.fictional@example.test'}, event: 'SIGNED_IN'}}))")
        await page.wait_for_selector(".mmacc.open .mmacc-name", timeout=6000)
        await page.wait_for_timeout(1600)
        fin = (await txt(page, ".mmacc-name"), await attr(page, "#mmacc-tz", "data-prev"), await page.input_value("#mmacc-tz"), await txt(page, "#mmacc-alert-msg"))
        R.check(fin == ("Bo Fictional", "Asia/Tokyo", "Asia/Tokyo", ""), "T7 B's tz control untouched by A's late ack", fin)
    except Exception as e:  # noqa: BLE001
        R.check(False, "T7 journey completed", repr(e)[:200])
    await ctx.close()
    return R


# ----------------------------------------------------------------- S1-03 -----
async def s1_03(browser, variant, main_js) -> Report:
    R = Report("S1-03 failed account read vs signed-out")

    async def state_of(page):
        return await page.evaluate(
            "() => { var p=document.querySelector('.mmacc'); if(!p) return null; return {"
            " unavail: !!p.querySelector('[data-acct-state=unavailable]'), name: !!p.querySelector('.mmacc-head:not(.mmacc-head-out) .mmacc-name'),"
            " guest: p.textContent.indexOf('Access session') > -1, text: p.textContent.slice(0, 160)}; }")

    for mode in ("503", "abort", "malformed", "nonjson"):
        m = Mock(); m.acct_mode = mode
        ctx, page, errs = await new_page(browser, m, variant, main_js)
        try:
            await open_acct(page, wait_name=False); await page.wait_for_timeout(1500)
            s = await state_of(page)
            R.check(bool(s) and s["unavail"] and not s["guest"] and not s["name"], f"K {mode} -> unavailable (not guest, not account)", s)
            if mode == "503":
                R.check(EN["unavail_t"] in (s or {}).get("text", ""), "K 503 shows 'Can’t load your account right now'", (s or {}).get("text", "")[:80])
        except Exception as e:  # noqa: BLE001
            R.check(False, f"K {mode} journey completed", repr(e)[:200])
        await ctx.close()

    for mode in ("401", "anon"):
        m = Mock(); m.acct_mode = mode
        ctx, page, errs = await new_page(browser, m, variant, main_js)
        try:
            await open_acct(page, wait_name=False); await page.wait_for_timeout(1500)
            s = await state_of(page)
            R.check(bool(s) and s["guest"] and not s["unavail"], f"K {mode} -> signed-out guest flow", s)
        except Exception as e:  # noqa: BLE001
            R.check(False, f"K {mode} journey completed", repr(e)[:200])
        await ctx.close()

    # ZH unavailable copy
    m = Mock(); m.acct_mode = "503"
    ctx, page, errs = await new_page(browser, m, variant, main_js, lang="zh")
    try:
        await open_acct(page, wait_name=False); await page.wait_for_timeout(1500)
        s = await state_of(page)
        R.check(ZH["unavail_t"] in (s or {}).get("text", ""), "K 503 ZH copy", (s or {}).get("text", "")[:60])
    except Exception as e:  # noqa: BLE001
        R.check(False, "K ZH journey completed", repr(e)[:200])
    await ctx.close()

    # recovery without reload via the retry control; plan/entitlement label unchanged
    m = Mock(); m.acct_mode = "503"
    ctx, page, errs = await new_page(browser, m, variant, main_js)
    try:
        await open_acct(page, wait_name=False); await page.wait_for_timeout(1200)
        await page.evaluate("() => { window.__noReload = 'kept'; }")
        m.acct_mode = "ok"
        await page.click("[data-act=retry-load]")
        await page.wait_for_selector(".mmacc.open .mmacc-name", timeout=6000)
        got = (await txt(page, ".mmacc-name"), await txt(page, ".mmacc-plan-pill"), await page.evaluate("() => window.__noReload"))
        R.check(got == ("Pat Fictional", "Pro", "kept"), "K retry restores account without reload; plan label intact", got)
    except Exception as e:  # noqa: BLE001
        R.check(False, "K retry journey completed", repr(e)[:200])
    await ctx.close()

    # a late read from an older generation cannot replace the newer state
    m = Mock(); m.acct_queue = [("503", 1.6), ("ok", 0.0)]
    ctx, page, errs = await new_page(browser, m, variant, main_js)
    try:
        await open_acct(page, wait_name=False); await page.wait_for_timeout(250)
        await page.keyboard.press("Escape")
        await open_acct(page)
        await page.wait_for_timeout(2200)
        s = await state_of(page)
        R.check(bool(s) and s["name"] and not s["unavail"] and m.acct_reads >= 2, "K late 503 from older load ignored; account stays", (s, m.acct_reads))
    except Exception as e:  # noqa: BLE001
        R.check(False, "K late-read journey completed", repr(e)[:200])
    await ctx.close()
    return R


# ----------------------------------------------------------------- S1-04 -----
async def s1_04(browser, variant, main_js) -> Report:
    R = Report("S1-04 sign-out-everywhere outcome")
    cases = [
        ("500 {}", ("json", 500, {}), "en", EN["so_unknown"]),
        ("500 non-JSON", ("text", 500, "Internal Server Error"), "en", EN["so_unknown"]),
        ("transport abort", ("abort", 0, None), "en", EN["so_unknown"]),
        ("500 {} ZH", ("json", 500, {}), "zh", ZH["so_unknown"]),
        ("429 EN", ("json", 429, {"ok": False, "error": RL_EN, "error_zh": RL_ZH}), "en", RL_EN),
        ("429 ZH", ("json", 429, {"ok": False, "error": RL_EN, "error_zh": RL_ZH}), "zh", RL_ZH),
    ]
    for label, plan, lg, want in cases:
        m = Mock(); m.so_plan = plan
        m.server_prefs = {"theme": "dark", "lang": lg}  # account prefs hydrate lang; seed must agree
        ctx, page, errs = await new_page(browser, m, variant, main_js, lang=lg)
        try:
            await open_acct(page)
            await page.click("[data-act=signout-all]"); await page.wait_for_timeout(900)
            got = (await txt(page, "#mmacc-signout-msg"), await page.evaluate("() => window.__soCalls"), await is_open(page), m.so_posts)
            R.check(got == (want, 0, True, 1), f"M {label}: message shown, NO local sign-out, dialog open, one request", got)
        except Exception as e:  # noqa: BLE001
            R.check(False, f"M {label} journey completed", repr(e)[:200])
        await ctx.close()

    m = Mock(); m.so_plan = ("json", 200, {"ok": True})
    ctx, page, errs = await new_page(browser, m, variant, main_js)
    try:
        await open_acct(page)
        labels = (await txt(page, "[data-act=signout]"), await txt(page, "[data-act=signout-all]"))
        R.check(labels[0] and labels[1] and labels[0] != labels[1], "M local and all-device sign-out are separately labelled", labels)
        await page.click("[data-act=signout-all]"); await page.wait_for_timeout(900)
        got = (await page.evaluate("() => window.__soCalls"), await is_open(page), m.so_posts)
        R.check(got == (1, False, 1), "M 200 {ok:true}: local sign-out follows, dialog closes", got)
    except Exception as e:  # noqa: BLE001
        R.check(False, "M success journey completed", repr(e)[:200])
    await ctx.close()
    return R


# ----------------------------------------------------------------- crops -----
async def crops(browser, variant, main_js, out: Path) -> list[dict]:
    shots = out / "shots"; shots.mkdir(parents=True, exist_ok=True)
    inv = []
    for theme in ("dark", "light"):
        for lg in ("en", "zh"):
            for vw, vh in ((1440, 900), (390, 844)):
                for state in ("unavailable", "signout-unknown"):
                    m = Mock(); m.server_prefs = {"theme": theme, "lang": lg}
                    if state == "unavailable":
                        m.acct_mode = "503"
                    else:
                        m.so_plan = ("json", 500, {})
                    ctx, page, errs = await new_page(browser, m, variant, main_js, theme=theme, lang=lg, viewport=(vw, vh))
                    try:
                        if state == "unavailable":
                            await open_acct(page, wait_name=False); await page.wait_for_timeout(1200)
                            await page.wait_for_selector("[data-acct-state=unavailable]", timeout=4000)
                        else:
                            await open_acct(page)
                            await page.click("[data-act=signout-all]"); await page.wait_for_timeout(1000)
                            await page.locator("#mmacc-signout-msg").scroll_into_view_if_needed()
                        await page.wait_for_timeout(400)
                        name = f"s1_{state}_{theme}_{lg}_{vw}.png"
                        await page.locator(".mmacc").screenshot(path=str(shots / name))
                        data = (shots / name).read_bytes()
                        inv.append({"file": f"shots/{name}", "state": state, "theme": theme, "lang": lg,
                                    "viewport": f"{vw}x{vh}", "bytes": len(data),
                                    "sha256": hashlib.sha256(data).hexdigest(), "page_errors": len(errs)})
                    except Exception as e:  # noqa: BLE001
                        inv.append({"file": None, "state": state, "theme": theme, "lang": lg,
                                    "viewport": f"{vw}x{vh}", "error": repr(e)[:200]})
                    await ctx.close()
    return inv


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=("fix", "main"), required=True)
    ap.add_argument("--main-js", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-crops", action="store_true")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    main_js = Path(a.main_js).read_text(encoding="utf-8") if a.variant == "main" else ""
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1",
                            "--directory", str(TREE_SITE)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        await asyncio.sleep(1.0)
        served = TREE_SITE / "account.js"
        meta = {"variant": a.variant, "page": f"site/{PAGE}",
                "account_js_sha256": hashlib.sha256((main_js.encode() if a.variant == "main" else served.read_bytes())).hexdigest()}
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            total_p = total_f = 0
            for fn, tag in ((s1_03, "S1-03"), (s1_01, "S1-01"), (s1_02, "S1-02"), (s1_04, "S1-04")):
                rep = await fn(browser, a.variant, main_js)
                (out / f"browser_{tag}.txt").write_text(f"# account.js sha256 {meta['account_js_sha256']}\n" + rep.text(a.variant), encoding="utf-8")
                total_p += rep.npass; total_f += rep.nfail
                print(f"{tag}: {rep.npass} pass / {rep.nfail} fail", flush=True)
            if a.variant == "fix" and not a.no_crops:
                inv = await crops(browser, a.variant, main_js, out)
                (out / "crops_inventory.json").write_text(json.dumps({**meta, "crops": inv}, indent=2, ensure_ascii=False), encoding="utf-8")
                print(f"crops: {sum(1 for c in inv if c.get('file'))}/{len(inv)}", flush=True)
            await browser.close()
        print(f"TOTAL {a.variant}: {total_p} pass / {total_f} fail", flush=True)
        return 0 if (a.variant == "main" or total_f == 0) else 1
    finally:
        srv.terminate()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

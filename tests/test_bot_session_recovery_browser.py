"""Real Chromium + shipping theme/GoTrue regression for the Bot renewal lifecycle.

All provider responses are synthetic. No customer account, real refresh token,
or live network is used. The server entitlement decision is covered separately
by test_paywall_pro_gate; reload here proves only a return to that server gate.
"""
from __future__ import annotations

import base64
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlsplit

import pytest

if os.environ.get("MM_REQUIRE_BROWSER") == "1":
    from playwright.sync_api import sync_playwright
else:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SESSION_KEY = "sb-recovery-auth-token"
BOT_URL = "https://bot.mastermind-x.com/desk?view=trades"
AUTH_URL = "https://auth.example.test"
OLD_SESSION = {
    "access_token": "synthetic-expired-access",
    "refresh_token": "synthetic-refresh",
    "expires_at": 100,
    "user": {"id": "synthetic-user"},
}


def cookie_value(session):
    raw = json.dumps(session, separators=(",", ":")).encode()
    return "base64-" + base64.urlsafe_b64encode(raw).decode().rstrip("=")


def session_cookie(session):
    return {"name": SESSION_KEY, "value": cookie_value(session),
            "domain": ".mastermind-x.com", "path": "/", "secure": True, "sameSite": "Lax"}


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        yield b
        b.close()


class Recovery:
    def __init__(self, browser, case="pending", *, ordinary=False, theme_override=None):
        self.context = browser.new_context()
        self.context.add_cookies([session_cookie(OLD_SESSION)])
        if case == "pkce":
            self.context.add_cookies([{
                "name": SESSION_KEY + "-code-verifier", "value": "synthetic-verifier",
                "domain": ".mastermind-x.com", "path": "/", "secure": True,
            }])
        self.page = self.context.new_page()
        self.events = []
        self.held = {}
        self.documents = []
        self.page.expose_function("__record", lambda kind, data=None: self.events.append((kind, data)))
        self.page.add_init_script("""
          window.SUPABASE_CFG = {url:'https://auth.example.test', anonKey:'synthetic-public-key',ref:'recovery'};
          const cookieDescriptor = Object.getOwnPropertyDescriptor(Document.prototype, 'cookie');
          Object.defineProperty(Document.prototype, 'cookie', {
            get(){return cookieDescriptor.get.call(this);},
            set(value){
              if(value.startsWith('sb-recovery-auth-token')) window.__record('cookie-write', value.split('=')[0]);
              if(__CASE__ !== 'blocked_cookie') cookieDescriptor.set.call(this,value);
            }
          });
          const post = BroadcastChannel.prototype.postMessage;
          BroadcastChannel.prototype.postMessage = function(value){
            window.__record('broadcast', value && value.event);
            return post.call(this,value);
          };
          const fetchOriginal = window.fetch.bind(window);
          window.fetch = function(input, init){
            const url = typeof input === 'string' ? input : input.url;
            if(!url.startsWith('https://auth.example.test/')) return fetchOriginal(input,init);
            window.__record('fetch',{url, method:init && init.method});
            if(init && init.signal) init.signal.addEventListener('abort',()=>window.__record('abort'));
            // Deliberately ignore abort settlement: a late provider result must
            // still be unable to write, broadcast success, or reload.
            return new Promise((resolve,reject)=>{
              window.__releaseRefresh = (kind)=>{
                if(kind==='network') {reject(new TypeError('synthetic network failure'));return;}
                let status=kind==='unavailable'?503:kind==='invalid'?400:200;
                let body=status===200 ? {
                  access_token:'synthetic-new-access',refresh_token:'synthetic-rotated-refresh',
                  expires_in:3600,expires_at:Math.floor(Date.now()/1000)+3600,
                  token_type:'bearer',user:{id:'synthetic-user'}
                } : {code:kind==='invalid'?'refresh_token_not_found':'unexpected_failure',message:'synthetic failure'};
                resolve(new Response(JSON.stringify(body),{status,headers:{'Content-Type':'application/json'}}));
              };
            });
          };
          if(__CASE__==='storage_off'){
            const get=Storage.prototype.getItem;
            Storage.prototype.getItem=function(k){if(this===sessionStorage)throw Error('blocked');return get.call(this,k);};
          }
          if(__CASE__==='recent') sessionStorage.setItem('mm.bot.session-renew.v1',String(Date.now()-100));
          if(__CASE__==='late_lock'){
            const request=navigator.locks.request.bind(navigator.locks);
            let held=false;
            navigator.locks.request=function(...args){
              if(!held && String(args[0]).includes('sb-recovery-auth-token')){
                held=true;return new Promise((resolve,reject)=>{
                  window.__releaseLock=()=>request(...args).then(resolve,reject);
                });
              }
              return request(...args);
            };
          }
        """.replace("__CASE__", json.dumps(case)))
        html = (ROOT / "app/paywall_pro_session_refresh.html").read_text()
        if case == "no":
            html = html.replace('name="mm-bot-renew" content="yes"', 'name="mm-bot-renew" content="no"')
        if ordinary:
            html = '<!doctype html><base href="https://www.mastermind-x.com/"><script src="theme.js" defer></script><body>ordinary</body>'
        theme = (ROOT / "site/theme.js").read_text()
        # Only public deployment configuration is substituted. The shipped
        # broker and vendored SDK are executed intact.
        theme, config_slots = re.subn(
            r"var _bakedSupabaseCfg=[^;]+;",
            'var _bakedSupabaseCfg={"url":"https://auth.example.test","anonKey":"synthetic-public-key","ref":"recovery"};',
            theme, count=1,
        )
        assert config_slots == 1
        if theme_override is not None:
            theme = theme_override
        sdk = (ROOT / "templates/supabase.js").read_text() + """
          ;(function(){
            const original=window.supabase.createClient;
            window.supabase.createClient=function(url,key,options){
              window.__record('client',{auto:options.auth.autoRefreshToken,detect:options.auth.detectSessionInUrl});
              return original.apply(this,arguments);
            };
          })();
        """
        if case == "missing_controller":
            theme = "window.__MMBotSessionRecovery=null;\n" + theme

        def route(r):
            path = urlsplit(r.request.url).path
            if r.request.is_navigation_request() and urlsplit(r.request.url).hostname == "bot.mastermind-x.com":
                self.documents.append(r.request.url)
                allow_recovery = len(self.documents) == 1 or (case == "manual_retry" and len(self.documents) == 2)
                r.fulfill(status=200, content_type="text/html", body=html if allow_recovery else "<p>server gate revisited</p>")
            elif path == "/theme.js":
                if case == "late_theme":
                    self.held["theme"] = (r, theme)
                else:
                    r.fulfill(content_type="application/javascript", body=theme)
            elif path == "/supabase.js":
                if case == "late_sdk":
                    self.held["sdk"] = (r, sdk)
                else:
                    r.fulfill(content_type="application/javascript", body=sdk)
            else:
                # All non-fixture network is denied; no request reaches the Internet.
                r.abort()
        self.context.route("**/*", route)
        self.page.clock.install()
        self.url = BOT_URL + ("&code=synthetic-code" if case == "pkce" else "")
        self.page.goto(self.url, wait_until="commit")
        if ordinary:
            self.page.wait_for_function("typeof window.getSupabaseClient==='function'")
        else:
            self.page.wait_for_selector("#mm-bot-renew-status")

    def count(self, kind):
        return sum(k == kind for k, _ in self.events)

    def start(self):
        self.page.wait_for_function("typeof window.__releaseRefresh==='function'")

    def release(self, kind="success"):
        self.page.evaluate("(kind)=>window.__releaseRefresh(kind)", kind)

    def release_script(self, name):
        route, body = self.held.pop(name)
        route.fulfill(content_type="application/javascript", body=body)

    def advance(self, ms):
        self.page.clock.fast_forward(ms)
        self.page.evaluate("Promise.resolve()")

    def unavailable(self):
        self.page.wait_for_function("document.querySelector('#mm-bot-renew-status').textContent.includes('Please sign in again')")

    def value(self):
        return next((c["value"] for c in self.context.cookies() if c["name"] == SESSION_KEY), None)

    def close(self):
        self.context.close()


@pytest.fixture
def recovery(browser):
    opened = []
    def factory(case="pending", **kwargs):
        r = Recovery(browser, case, **kwargs)
        opened.append(r)
        return r
    yield factory
    for r in opened:
        r.close()


@pytest.mark.parametrize("case", ["storage_off", "recent", "no", "missing_controller", "late_theme", "late_sdk", "late_lock"])
def test_closed_admission_cannot_escape_through_theme_or_sdk(recovery, case):
    r = recovery(case)
    if case == "late_theme":
        r.advance(13000)
        r.unavailable()
        r.release_script("theme")
    elif case == "late_sdk":
        r.page.wait_for_function("typeof window.getSupabaseClient==='function'")
        # Process the SDK request before expiring its page.
        r.page.wait_for_event("request", predicate=lambda req: urlsplit(req.url).path == "/supabase.js") if "sdk" not in r.held else None
        r.advance(13000)
        r.release_script("sdk")
    elif case == "late_lock":
        r.page.wait_for_function("typeof window.__releaseLock==='function'")
        r.advance(13000)
        r.page.evaluate("window.__releaseLock()")
    r.advance(35000)
    r.unavailable()
    r.page.evaluate("window.dispatchEvent(new Event('online'));document.dispatchEvent(new Event('visibilitychange'));")
    r.advance(35000)
    assert r.count("fetch") == 0, r.events
    assert r.count("cookie-write") == 0, r.events
    assert r.count("broadcast") == 0, r.events
    assert len(r.documents) == 1
    assert r.value() == cookie_value(OLD_SESSION)
    if case != "late_lock":
        assert r.count("client") == 0, r.events


def test_external_theme_client_request_after_deadline_cannot_restart_auth(recovery):
    """Even an explicit late consumer cannot reopen the shared auth broker."""
    r = recovery("late_theme")
    r.advance(13000)
    r.unavailable()
    r.release_script("theme")
    r.page.wait_for_function("typeof window.getSupabaseClient === 'function'")
    denied = r.page.evaluate("""async () => {
        try { await window.getSupabaseClient(); return 'incorrectly-opened'; }
        catch (error) { return String(error && error.message); }
    }""")
    assert denied in ("auth-disabled", "recovery-closed")
    r.advance(35000)
    assert r.count("client") == 0, r.events
    assert r.count("fetch") == 0, r.events
    assert r.count("cookie-write") == 0, r.events
    assert r.count("broadcast") == 0, r.events
    assert r.value() == cookie_value(OLD_SESSION)
    assert r.documents == [r.url]


@pytest.mark.parametrize("case", ["timeout", "unavailable", "network", "invalid", "other_signin", "other_signout", "blocked_cookie"])
def test_late_or_failed_refresh_has_no_shared_session_effect(recovery, case):
    r = recovery(case)
    r.start()
    expected = cookie_value(OLD_SESSION)
    if case == "timeout":
        r.advance(13000)
        r.unavailable()
        assert r.count("abort") == 1
    elif case == "other_signout":
        r.context.clear_cookies(name=SESSION_KEY)
        expected = None
    elif case == "other_signin":
        newer = dict(OLD_SESSION, access_token="synthetic-other-session", expires_at=int(time.time()) + 7200)
        r.context.add_cookies([session_cookie(newer)])
        expected = cookie_value(newer)
    r.release(case if case in ("unavailable", "network", "invalid") else "success")
    r.advance(1000)
    r.unavailable()
    r.advance(35000)
    assert r.count("fetch") == 1, r.events
    assert r.count("broadcast") == 0, r.events
    assert len(r.documents) == 1
    assert r.value() == expected
    if case != "blocked_cookie":
        assert r.count("cookie-write") == 0, r.events


@pytest.mark.parametrize("case", ["success", "pkce"])
def test_success_commits_canonical_cookie_then_revisits_original_server_gate(recovery, case):
    r = recovery(case)
    r.start()
    r.release()
    r.page.wait_for_selector("text=server gate revisited")
    assert r.documents == [r.url, r.url]
    assert r.count("fetch") == 1, r.events
    assert r.count("cookie-write") > 0
    assert r.count("broadcast") == 0, r.events
    raw = r.value().removeprefix("base64-")
    session = json.loads(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))
    assert session["access_token"] == "synthetic-new-access"
    assert all(data["url"] == AUTH_URL + "/auth/v1/token?grant_type=refresh_token" for kind, data in r.events if kind == "fetch")
    if case == "pkce":
        assert any(c["name"] == SESSION_KEY + "-code-verifier" for c in r.context.cookies())


def test_user_retry_after_failed_renewal_is_not_stopped_by_automatic_replay_fence(recovery):
    r = recovery("manual_retry")
    r.start()
    r.release("invalid")
    r.unavailable()
    assert r.count("fetch") == 1
    assert len(r.documents) == 1
    r.page.get_by_role("button", name="Try Bot again · 重试").click()
    r.page.wait_for_function("window.__MMBotSessionRecovery && window.__MMBotSessionRecovery.isOpen()")
    r.start()
    assert r.count("fetch") == 2, r.events
    r.release("success")
    r.page.wait_for_selector("text=server gate revisited")
    assert r.documents == [r.url, r.url, r.url]


def test_ordinary_page_retains_existing_automatic_auth_contract(recovery):
    r = recovery(ordinary=True)
    r.start()
    options = [data for kind, data in r.events if kind == "client"]
    assert options == [{"auto": True, "detect": True}]
    r.release()
    r.advance(1000)
    assert r.count("cookie-write") > 0
    assert r.value() != cookie_value(OLD_SESSION)
    assert r.count("broadcast") > 0


def test_legacy_theme_config_override_stays_disabled(recovery):
    # The existing config override is the compatibility seam old bundles honor.
    # This probe models their unguarded DCL boot; a full pre-repair shipping
    # bundle is also exercised when validating the release locally.
    old_boot = """
      window.SUPABASE_CFG = window.SUPABASE_CFG ||
        {url:'https://auth.example.test',anonKey:'synthetic-public-key'};
      const enabled=!!(window.SUPABASE_CFG.url && window.SUPABASE_CFG.anonKey);
      document.addEventListener('DOMContentLoaded',function(){
        if(enabled) window.__record('client','unguarded legacy boot');
      });
    """
    r = recovery(theme_override=old_boot)
    r.unavailable()
    r.advance(35000)
    assert r.count("client") == 0
    assert r.count("fetch") == 0
    assert r.count("cookie-write") == 0
    assert r.value() == cookie_value(OLD_SESSION)

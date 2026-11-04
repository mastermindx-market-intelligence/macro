"""Recover the existing landing auth broker after an interrupted SDK download.

The real shipped functions run under Node with a stub script loader; no
production credentials, network requests, or duplicate auth clients.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which('node') is None, reason='node unavailable')
@pytest.mark.parametrize('path', ['templates/onboard.js', 'site/onboard.js'])
def test_failed_lazy_auth_script_can_reload_from_same_page(path: str) -> None:
    source = (ROOT / path).read_text()
    start = source.index('  var _themeLoad = null;')
    end = source.index('  function authEnabled()', start)
    actual = source[start:end]
    harness = r'''
const window = {};
const scripts = [];
const host = {appendChild(script){script.parentNode=this;scripts.push(script);},removeChild(script){script.removed=true;}};
const document = {createElement(name){if(name!=='script')throw Error(name);return {};},head:host,documentElement:host};
function restoreLightOnlyHostTheme(){}
__ACTUAL_SOURCE__
(async()=>{
 const first=ensureAuthBroker();
 if(scripts.length!==1)throw Error('Expected exactly one initial script');
 scripts[0].onerror();
 const empty=await first;
 if(empty!==null)throw Error('First failed download should resolve unavailable');
 const retry=ensureAuthBroker();
 const retried=scripts.length===2;
 if(retried){window.MDXAuth={client:()=>Promise.resolve({auth:{}})};scripts[1].onload();}
 const result=await retry;
 process.stdout.write(JSON.stringify({retried,brokerRecovered:result===window.MDXAuth,removedFailedScript:!!scripts[0].removed}));
})().catch(error=>{console.error(error.stack);process.exit(1)});
'''
    res = subprocess.run(['node', '-e', harness.replace('__ACTUAL_SOURCE__',actual)],capture_output=True,text=True,timeout=10)
    assert res.returncode == 0,res.stderr
    assert json.loads(res.stdout)=={'retried':True,'brokerRecovered':True,'removedFailedScript':True}

@pytest.mark.skipif(shutil.which("node") is None, reason="node unavailable")
def test_dashboard_explicit_logout_survives_auth_service_errors() -> None:
    """Actual shipping signOut method clears both scopes even on error/SDK failure."""
    source = (ROOT / "templates/theme.js").read_text(encoding="utf-8")
    start = source.index("  function _clearLocalAuthCookies()")
    end = source.index("  // Restore a prior session", start)
    script = r"""
const window = {addEventListener() {}};
const _authEnabled = true;
let _explicitSignOut = false, _curUser = {id:'signed-in'}, _authReady=true;
let keys=[], notifications=[], mode='error';
function _storageKey(){return 'sb-test-auth-token';}
function _clearCookieKey(k){keys.push(k);}
function _hasSessionCookie(){return true;}
function _mmOpenOnboard(){}
// Current main added these unrelated broker members; this fixture never invokes them.
function _queuePendingPrefs(){}
function _deliverPendingPrefs(){}
function _onAuth(event){_curUser=null;notifications.push(event);}
function getSupabaseClient(){
  if(mode==='sdk-failure')return Promise.reject(new Error('SDK offline'));
  return Promise.resolve({auth:{signOut:({scope})=>{
    if(scope!=='local')throw Error('Revoked sessions on OTHER devices');
    return Promise.resolve(mode==='error'?{error:{status:503}}:{error:null});
  }}});
}
__AUTH_OBJECT__
(async()=>{
  const rows=[];
  for(const k of ['error','sdk-failure','success']){
    mode=k; _explicitSignOut=false; _curUser={id:'signed-in'}; keys=[]; notifications=[];
    await window.MDXAuth.signOut();
    rows.push({kind:k,keys,notifications,explicit:_explicitSignOut,user:_curUser});
  }
  process.stdout.write(JSON.stringify(rows));
})().catch(e=>{console.error(e.stack);process.exit(1)});
""".replace("__AUTH_OBJECT__", source[start:end])
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    for row in json.loads(result.stdout):
        assert row["explicit"] is True
        assert row["user"] is None
        assert row["keys"] == ["sb-test-auth-token", "sb-test-auth-token-code-verifier"]
        assert row["notifications"] == ["SIGNED_OUT"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node unavailable")
def test_browser_return_retries_but_never_restores_explicitly_signed_out_user() -> None:
    source = (ROOT / "templates/theme.js").read_text(encoding="utf-8")
    begin = source.index("  function _retryRestoreOnReturn()")
    end = source.index("  /* ---- the frosted-glass", begin)
    script = r"""
const window={addEventListener(){}};
const document={hidden:false,addEventListener(){}};
let _explicitSignOut=true, _authBooted=false, _curUser=null, runs=0;
function _hasSessionCookie(){return true;}
function _isAuthReturn(){return false;}
function _authBoot(){_authBooted=true;runs++;}
__AUTH_RETURN__
_retryRestoreOnReturn();
const logoutRuns=runs;
_explicitSignOut=false;
_retryRestoreOnReturn();
_retryRestoreOnReturn();
process.stdout.write(JSON.stringify({logoutRuns,runs}));
""".replace("__AUTH_RETURN__", source[begin:end])
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"logoutRuns": 0, "runs": 1}


def test_every_entry_page_references_current_immutable_auth_assets() -> None:
    """Warm cached HTML must not pin superseded browser auth/logout behavior."""
    import hashlib
    import re

    digests = {
        name: hashlib.sha256((ROOT / "site" / (name + ".js")).read_bytes()).hexdigest()[:8]
        for name in ("theme", "onboard")
    }
    for base in (ROOT / "site", ROOT / "templates"):
        # Nested stock, basket, earnings and research pages share these auth assets.
        pages = [*base.rglob("*.html"), *base.rglob("*.j2")]
        assert pages
        for p in pages:
            text = p.read_text(encoding="utf-8")
            # Match a complete asset basename; ontology-theme.js has its own digest.
            for name, stamp in re.findall(r"(?<![\w.-])(theme|onboard)\.js\?v=([0-9a-f]{8})", text):
                assert stamp == digests[name], f"{p}: stale {name}.js?v={stamp}, current={digests[name]}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node unavailable")
@pytest.mark.parametrize("malformed", [None, {}, {"createClient": True}, {"createClient": "not-callable"}])
def test_dashboard_sdk_without_callable_client_can_retry(malformed) -> None:
    """A script load event without the actual SDK never poisons the cached promise."""
    source = (ROOT / "templates/theme.js").read_text(encoding="utf-8")
    start = source.index("  function _loadSDK()")
    end = source.index("  function getSupabaseClient()", start)
    harness = r"""
const window={supabase:__MALFORMED__}; let _sbLoading=null; const _SDK_URL='supabase.js';
const scripts=[];
const host={appendChild(s){s.parentNode=this;scripts.push(s)},removeChild(s){s.removed=true}};
const document={createElement(){return {}},head:host,documentElement:host};
__SOURCE__
(async()=>{
 const first=_loadSDK();
 if(scripts.length!==1)throw Error('Non-callable SDK was treated as available');
 scripts[0].onload();
 let outcome='resolved';try{await first}catch(e){outcome='rejected'}
 const retry=_loadSDK();
 if(scripts.length===2){window.supabase={createClient(){}};scripts[1].onload()}
 await retry;
 process.stdout.write(JSON.stringify({outcome,loads:scripts.length,removed:!!scripts[0].removed}));
})().catch(e=>{console.error(e.name);process.exit(2)});
""".replace("__MALFORMED__", json.dumps(malformed)).replace("__SOURCE__", source[start:end])
    result = subprocess.run(["node", "-e", harness], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"outcome": "rejected", "loads": 2, "removed": True}


@pytest.mark.parametrize("path", ["templates/theme.js", "site/theme.js"])
def test_dynamic_account_asset_release_key_tracks_local_signout_bytes(path: str) -> None:
    """A year-cached account dependency must not keep the pre-repair global logout."""
    # Account and navigation already share one explicit release key. Keep that
    # owner contract; the existing nav-payload digest independently pins bytes.
    expected = "20261103-auth-session-continuity"
    assert f"account.js?v={expected}" in (ROOT / path).read_text(encoding="utf-8")
    assert f"nav_market.js?v={expected}" in (ROOT / "templates/account.js").read_text()


def test_account_generated_asset_preserves_authored_local_signout() -> None:
    authored = (ROOT / "templates/account.js").read_bytes()
    assert authored == (ROOT / "site/account.js").read_bytes()
    assert b"sb.auth.signOut({ scope: 'local' })" in authored

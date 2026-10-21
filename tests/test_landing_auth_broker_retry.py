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
        pages = [*base.glob("*.html"), *base.glob("*.j2")]
        assert pages
        for p in pages:
            text = p.read_text(encoding="utf-8")
            for name, stamp in re.findall(r"(theme|onboard)\.js\?v=([0-9a-f]{8})", text):
                assert stamp == digests[name], f"{p}: stale {name}.js?v={stamp}, current={digests[name]}"

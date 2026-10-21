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

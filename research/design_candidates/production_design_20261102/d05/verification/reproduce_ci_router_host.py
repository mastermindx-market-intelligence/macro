from pathlib import Path
import ast, hashlib, json, subprocess, textwrap, time
root=Path('/Volumes/Mastermind/agent-workspaces/macro/web/d05-native-source-verification-20261104')
expected={'tests/test_si_workspace_shell.py':'9d40017add0d844de5decc854091f0f370a4b158','templates/si_workspace.js':'ac426abc3a8a49a6d1023cc53b8eedb00a23c57a'}
actual={}
for rel,want in expected.items():
    data=(root/rel).read_bytes()
    actual[rel]=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
    assert actual[rel]==want,(rel,actual[rel],want)
source=(root/'tests/test_si_workspace_shell.py').read_text()
tree=ast.parse(source)
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_replay_router')
function_source=ast.get_source_segment(source,fn)
assert function_source.count("location: { hash: '' },")==1
base={'_textwrap':textwrap,'_subprocess':subprocess,'_json':json,'ROOT':root}
exec(compile(function_source,'<exact-pinned-router-harness>','exec'),base)
results={'source_ref':'0c4493c7025f7c1c0f9e558860d5e4ba33457cd1','source_blobs':actual,'source_files_modified':False,'scope':'isolated in-memory reproduction; incumbent source writer retains ownership','cases':[]}
t=time.time()
try:
    base['_replay_router'](['#si-measured','#overview','#confluence'])
except AssertionError as e:
    s=str(e)
    assert 'ReferenceError: URL is not defined' in s,s
    results['baseline']={'result':'EXPECTED_FAILURE_REPRODUCED','cause':'ReferenceError: URL is not defined','seconds':round(time.time()-t,3)}
else:
    raise AssertionError('Expected unchanged harness to reproduce hosted failure')
patched=function_source.replace("location: { hash: '' },","location: { hash: '', href: 'https://d05-fixture.invalid/sector_central.html' },\n          URL,")
fixed={'_textwrap':textwrap,'_subprocess':subprocess,'_json':json,'ROOT':root}
exec(compile(patched,'<browser-host-completed-router-harness>','exec'),fixed)
cases=[(['#si-measured','#overview','#confluence'],{'#si-measured':['map','si-measured'],'#overview':['overview',None],'#confluence':['confluence',None]}),(['si-heat-section','accumulation-section','actnow-section'],{'si-heat-section':['explore','theme-heat-section'],'accumulation-section':['moving','accumulation-section'],'actnow-section':['overview','actnow-section']})]
for hashes,want in cases:
    t=time.time()
    got=fixed['_replay_router'](hashes)
    assert got==want,(got,want)
    results['cases'].append({'hashes':hashes,'expected':want,'actual':got,'result':'PASS','seconds':round(time.time()-t,3)})
results['repair']='Only provide browser host WHATWG URL plus stable absolute location.href. Original routing assertions and real timers retained. No product code edits, caught exceptions, skips, or auth/source bypass.'
results['result']='HOSTED_FAILURE_REPRODUCED_AND_MINIMAL_HOST_FIX_PROVEN'
out=root/'.pytest_cache/d05-composed-20261104/ci_pack4_harness_reproduction_0c4493.json'
out.write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))

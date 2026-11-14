"""Qualify native ConfigRefresh and the real SSH observation/control pipe.

Only isolated /tmp state and a pre-copied admin fixture are used at the VPS.
Production configuration, credentials, listeners and service definitions are not
loaded or changed. Native upstream calls are closed by MockTransport. Every
explicit control operation is submitted once; an ambiguous result stops proof.
"""
from __future__ import annotations
import argparse
import asyncio
from contextlib import suppress
import hashlib
import importlib
import json
import os
from pathlib import Path
import shlex
import sys
import tempfile
import time
from unittest.mock import patch
import httpx


async def prove(args):
    release=args.release.resolve();sys.path.insert(0,str(release))
    gateway=importlib.import_module('ops.native_fabric.unified_router.gateway')
    observer=importlib.import_module('ops.native_fabric.unified_router.capacity_fabric_observer')
    transactions=importlib.import_module('ops.native_fabric.unified_router.capacity_config_transaction')
    assert str(args.remote_source).startswith('/tmp/capacity-router-11194-')
    assert str(args.remote_state).startswith('/tmp/capacity-router-11194-')
    original_spawn=asyncio.create_subprocess_exec
    remote_python='/opt/macro/.venv/bin/python'
    def remote_command(code):
        return 'cd '+shlex.quote(str(args.remote_source))+' && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/opt/macro '+remote_python+' -c '+shlex.quote(code)
    async def remote(code):
        process=await original_spawn('ssh','-T','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=8',args.ssh_alias,remote_command(code),stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        out,err=await asyncio.wait_for(process.communicate(),30)
        assert process.returncode==0,(process.returncode,err.decode()[-1500:])
        return json.loads(out)
    snapshot=args.remote_state/'snapshot.json'
    setup=await remote('from pathlib import Path; import json,hashlib; p=Path('+repr(str(args.remote_state))+');p.mkdir(mode=0o700); print(json.dumps({"ingress_sha256":hashlib.sha256(Path("admin/capacity_ingest.py").read_bytes()).hexdigest()}))')
    expected=hashlib.sha256((Path(__file__).resolve().parents[1]/'capacity_ingest.py').read_bytes()).hexdigest()
    assert setup['ingress_sha256']==expected,'remote fixture differs from reviewed ingress'
    root=Path(tempfile.mkdtemp(prefix='capacity-control-native-11194-')).resolve()
    config_path=root/'routes.json'
    document={'routes':[{'route_id':'fixture-control','kind':'gateway','base_url':'https://fixture.invalid','wire':'anthropic','models':['model-a'],'priority':10,'weight':1,'gateway_token_env':'UNUSED_FIXTURE_TOKEN'}],'aliases':{'fabric/fast':['model-a']},'observability':{'interval_s':.25}}
    config_path.write_text(json.dumps(document));config_path.chmod(0o600)
    parsed,revision=gateway.read_document(config_path)
    cfg=gateway.Settings(proxy_token='isolated-control-proof-token',state_dir=root/'state',routes=gateway._routes_from_document(parsed),aliases=(('fabric/fast',('model-a',)),),auth_store=root/'NO_PRODUCTION_AUTH',routes_path=config_path,routes_digest=revision,capacity_wait_s=0)
    async def no_provider(request):raise AssertionError('control proof attempted upstream inference')
    app=gateway.create_app(cfg,transport=httpx.MockTransport(no_provider))
    observer.instrument_app(app,gateway)
    writer=root/'isolated-writer.py';writer.write_text('from ops.native_fabric.unified_router.capacity_config_transaction import configuration_writer\n')
    export={'ssh_alias':args.ssh_alias,'controls_enabled':True,'control_writers':[{'path':str(writer),'sha256':hashlib.sha256(writer.read_bytes()).hexdigest()}]}
    pipe_code='from pathlib import Path; import os; from admin.capacity_ingest import main; root=Path('+repr(str(args.remote_state))+');(root/"ingress.pid").write_text(str(os.getpid()));main(root/"snapshot.json")'
    expected_command='cd /opt/macro && exec /opt/macro/.venv/bin/python -m admin.capacity_ingest'
    pipe_count=0
    async def spawn_pipe(*command,**kwargs):
        nonlocal pipe_count
        assert command[0]=='ssh' and command[-1]==expected_command,'unexpected native subprocess'
        pipe_count+=1
        assert pipe_count==1,'transport reconnected unexpectedly; inspect original fixture before another attempt'
        return await original_spawn(*command[:-1],remote_command(pipe_code),**kwargs)
    context=app.router.lifespan_context(app);publisher=None;entered=False
    proof={'schema':'mastermind.capacity_router.control_pipe_qualification.v1','release':str(release),'remote_source_sha256':setup,'native_config_path':str(config_path),'production_effects':False}
    try:
        with transactions.configuration_writer(config_path):
            await asyncio.wait_for(context.__aenter__(),10);entered=True
        proof['native_startup_with_configuration_lock_held']=True
        with patch.object(observer.asyncio,'create_subprocess_exec',side_effect=spawn_pipe):
            publisher=asyncio.create_task(observer.publish_snapshots(app,app.state.capacity_observer,export,gateway=gateway))
            wait_code='''from pathlib import Path
import json,time
from admin import capacity_control_transport as control
path=Path(PATH_VALUE)
end=time.monotonic()+20
while time.monotonic()<end:
    s=control.settings(path=path)
    if s.get('writable'):
        print(json.dumps({k:s.get(k) for k in ['writable','revision','epoch','interval_s']}));break
    time.sleep(.1)
else:raise SystemExit('isolated native owner did not become writable')
'''.replace('PATH_VALUE',repr(str(snapshot)))
            live=await remote(wait_code);assert live['revision']==revision
            receipts=[]
            for action in ['validate','apply']:
                body={'action':action,'expected_revision':revision,'patch':{'interval_s':.5}}
                result=await remote('from pathlib import Path;import json;from admin.capacity_control_transport import submit;r,status=submit('+repr(body)+',path=Path('+repr(str(snapshot))+'),timeout=8);print(json.dumps({"status":status,"receipt":r}))')
                expected_state='VALIDATED' if action=='validate' else 'APPLIED'
                assert result['status']==200 and result['receipt']['state']==expected_state,result
                receipts.append(result['receipt'])
            current,digest=gateway.read_document(config_path)
            assert current['observability']['interval_s']==.5
            assert app.state.config_refresh.digest==digest and digest!=revision
            proof.update(receipts=receipts,native_effective_revision=digest,configuration_writes=1,real_ssh_bidirectional_pipe=True)
            readback_code=wait_code.replace("if s.get('writable'):","if s.get('writable') and s.get('revision') == "+repr(digest)+":")
            readback=await remote(readback_code);assert readback['interval_s']==.5
            proof['vps_effective_readback']=readback
            publisher.cancel()
            with suppress(asyncio.CancelledError):await publisher
            publisher=None
        with transactions.configuration_writer(config_path):
            await asyncio.wait_for(context.__aexit__(None,None,None),10);entered=False
        proof['native_shutdown_with_configuration_lock_held']=True
        cleanup=await remote('''from pathlib import Path
import os,json,time
pid=int((Path(STATE_VALUE)/'ingress.pid').read_text())
end=time.monotonic()+8
while time.monotonic()<end:
    try:os.kill(pid,0)
    except ProcessLookupError:print(json.dumps({'ingress_exited':True}));break
    time.sleep(.1)
else:raise SystemExit('isolated ingress remains active')
'''.replace('STATE_VALUE',repr(str(args.remote_state))))
        proof.update(cleanup=cleanup,result='PASS',pipe_connections=pipe_count)
    except BaseException as exc:
        proof.update(result='FAIL',error=type(exc).__name__+': '+str(exc))
        raise
    finally:
        if publisher:
            publisher.cancel()
            with suppress(asyncio.CancelledError,Exception):await publisher
        if entered:
            with suppress(Exception):await context.__aexit__(None,None,None)
        args.output.write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps(proof,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('release',type=Path)
    parser.add_argument('--ssh-alias',required=True)
    parser.add_argument('--remote-source',type=Path,required=True)
    parser.add_argument('--remote-state',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    asyncio.run(prove(parser.parse_args()))

if __name__=='__main__':main()

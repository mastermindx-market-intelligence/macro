"""Prove serial launchd maintenance on a disposable loopback stream fixture.

No production job, configuration, credentials, provider or transport is used.
The exact installed signal handler and prepared startup guard are exercised.
A stream exceeds the loaded supervisor stop timeout. An operation-bound startup
fence prevents KeepAlive from reopening the retiring release's listener.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import http.client
import json
import os
from pathlib import Path
import plistlib
import re
import signal
import socket
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from admin.deploy.stage_capacity_observer import native_maintenance_candidate


def command(*args, check=True):
    return subprocess.run(args, capture_output=True, text=True, check=check)


def loaded(target):
    r = command('launchctl', 'print', target, check=False)
    match = re.search(r'^\s+pid = (\d+)$', r.stdout, re.M) if r.returncode == 0 else None
    return int(match.group(1)) if match else None, r.stdout


def alive(pid):
    if not pid: return False
    try: os.kill(pid, 0); return True
    except ProcessLookupError: return False


def until(predicate, seconds=20):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        value=predicate()
        if value: return value
        time.sleep(.1)
    raise AssertionError('fixture deadline expired')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--service',type=Path,required=True)
    parser.add_argument('--python',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    assert sys.platform=='darwin','launchd qualification requires macOS'
    source=args.service.read_text()
    node=next(n for n in ast.walk(ast.parse(source)) if isinstance(n,ast.ClassDef) and n.name=='RouterServer')
    handler=textwrap.dedent(''.join(source.splitlines(keepends=True)[node.lineno-1:node.end_lineno]))
    assert 'model_policy.draining = True' in handler and 'super().handle_exit(sig, frame)' in handler
    label='ai.mastermind.capacity-proof-11194-'+str(os.getpid());domain='gui/'+str(os.getuid());target=domain+'/'+label
    assert command('launchctl','print',target,check=False).returncode!=0
    proof={'schema':'mastermind.capacity_router.launchd_qualification.v1','production_effects':False,
           'service_sha256':hashlib.sha256(source.encode()).hexdigest(),
           'signal_handler_sha256':hashlib.sha256(handler.encode()).hexdigest(),'label':label}
    with tempfile.TemporaryDirectory(prefix='capacity-launchd-11194-') as temp:
        root=Path(temp).resolve();fake_home=root/'fixture-home'
        old=root/'releases/old';new=root/'releases/new';package=Path('ops/native_fabric/unified_router')
        (old/package).mkdir(parents=True);(new/package).mkdir(parents=True)
        marker=fake_home/'.local/share/mastermind/fabric-router/state/reload.lock/maintenance.json'
        stdout=root/'stdout.log';stderr=root/'stderr.log'
        sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
        app_source='''import asyncio, os, socket, sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import uvicorn
from fastapi import FastAPI
from starlette.responses import StreamingResponse
'''+f"_fixture_home = patch('pathlib.Path.home', return_value=Path({str(fake_home)!r}))\n_fixture_home.start()\n"+'''
def main():
    app=FastAPI()
    app.state.model_policy=SimpleNamespace(draining=False,changed=asyncio.Event())
    @app.get('/healthz')
    async def health():
        return {'ok':True,'generation':sys.argv[2],'pid':os.getpid(),'xpc_service_name':os.environ.get('XPC_SERVICE_NAME')}
    @app.get('/stream')
    async def stream():
        async def body():
            yield b'BEGIN\\n'
            for part in [b'ONE\\n',b'TWO\\n',b'END\\n']:
                await asyncio.sleep(1.2)
                yield part
        return StreamingResponse(body(),media_type='text/plain')
'''+textwrap.indent(handler,'    ')+'''
    config=uvicorn.Config(app,host='127.0.0.1',port=int(sys.argv[1]),workers=1,access_log=False,timeout_graceful_shutdown=15,limit_concurrency=384)
    server=RouterServer(config)
    sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEPORT,1)
    sock.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
    sock.bind(('127.0.0.1',int(sys.argv[1])));sock.listen(2048)
    server.run(sockets=[sock])

if __name__=='__main__': main()
'''
        fixture=old/package/'service.py';fixture.write_text(app_source)
        gated=native_maintenance_candidate('service.py',app_source,target_label=label)
        candidate=new/package/'service.py';candidate.write_text(gated)
        proof['prepared_startup_guard_sha256']=hashlib.sha256(gated.encode()).hexdigest()
        plist=root/(label+'.plist')
        definition={'Label':label,'ProgramArguments':[str(args.python),str(fixture),str(port),'first'],
                    'WorkingDirectory':str(old),'KeepAlive':{'SuccessfulExit':False},'RunAtLoad':True,
                    'ExitTimeOut':1,'ThrottleInterval':30,'StandardOutPath':str(stdout),'StandardErrorPath':str(stderr)}
        plist.write_bytes(plistlib.dumps(definition))
        def health():
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/healthz',timeout=.5) as r:return json.load(r)
            except (OSError,ValueError):return None
        started=threading.Event();stream_result={};thread=None
        def consume():
            conn=http.client.HTTPConnection('127.0.0.1',port,timeout=15)
            try:
                conn.request('GET','/stream');response=conn.getresponse();stream_result['status']=response.status
                first=response.read(6);stream_result['first']=first.decode();started.set()
                stream_result['body']=(first+response.read()).decode()
            except BaseException as exc:stream_result['error']=type(exc).__name__+': '+str(exc)
            finally:conn.close()
        try:
            command('launchctl','bootstrap',domain,str(plist))
            first=until(health);pid,description=loaded(target)
            assert first['xpc_service_name']==label
            proof['launchd_job_identity_verified']=True
            assert pid==first['pid'] and str(old) in description and 'exit timeout = 1' in description
            proof.update(loaded_original_timeout_s=1,original_pid=pid)
            thread=threading.Thread(target=consume,daemon=True);thread.start();assert started.wait(8)
            marker.parent.mkdir(parents=True,mode=0o700)
            maintenance={'schema':'mastermind.capacity_router.maintenance.v1','operation_id':'closed-launchd-proof','target_job':label,'base_release':str(old),'candidate_release':str(new),'candidate_service_sha256':hashlib.sha256(candidate.read_bytes()).hexdigest(),'phase':'STOPPING_OLD'}
            marker.write_text(json.dumps(maintenance));marker.chmod(0o600)
            prepared=fixture.with_suffix('.next');prepared.write_text(gated);os.replace(prepared,fixture)
            assert alive(pid) and health()['pid']==pid
            signalled=time.monotonic();os.kill(pid,signal.SIGTERM)
            thread.join(17)
            assert not thread.is_alive() and stream_result=={'status':200,'first':'BEGIN\n','body':'BEGIN\nONE\nTWO\nEND\n'},stream_result
            until(lambda:not alive(pid),seconds=5)
            proof['stream_completed_after_signal_s']=round(time.monotonic()-signalled,3)
            assert proof['stream_completed_after_signal_s']>2
            proof['complete_stream_bytes']=True
            print('FIXTURE_STREAM_DRAINED',proof['stream_completed_after_signal_s'],flush=True)
            until(lambda:stdout.exists() and 'capacity_maintenance_startup_held' in stdout.read_text(),seconds=40)
            until(lambda:not loaded(target)[0],seconds=8)
            assert health() is None
            _,description=loaded(target);assert 'last exit code = 0' in description,description
            proof['keepalive_child_fenced_before_listener']=True
            print('FIXTURE_RETIRING_STARTUP_FENCED',flush=True)
            end=time.monotonic()+32
            while time.monotonic()<end:
                current,_=loaded(target);assert not current or not alive(current),'held release restarted'
                time.sleep(.5)
            assert stdout.read_text().count('capacity_maintenance_startup_held')==1
            proof['successful_fence_exit_stops_keepalive']=True
            command('launchctl','bootout',target)
            assert command('launchctl','print',target,check=False).returncode!=0
            maintenance['phase']='STARTING_CANDIDATE';marker.write_text(json.dumps(maintenance))
            definition.update(WorkingDirectory=str(new),ExitTimeOut=19)
            definition['ProgramArguments']=[str(args.python),str(candidate),str(port),'second']
            plist.write_bytes(plistlib.dumps(definition));command('launchctl','bootstrap',domain,str(plist))
            second=until(health);second_pid,description=loaded(target)
            assert second['generation']=='second' and second_pid==second['pid'] and second_pid!=pid and not alive(pid)
            assert 'exit timeout = 19' in description
            proof.update(new_pid=second_pid,loaded_new_timeout_s=19,serial_bootstrap_new_definition=True,result='PASS')
        except BaseException as exc:
            proof.update(result='FAIL',error=type(exc).__name__+': '+str(exc),fixture_stderr=stderr.read_text()[-3000:] if stderr.exists() else '')
            raise
        finally:
            command('launchctl','bootout',target,check=False)
            if thread:thread.join(2)
            end=time.monotonic()+8
            while time.monotonic()<end and command('launchctl','print',target,check=False).returncode==0:time.sleep(.1)
            proof['fixture_job_removed']=command('launchctl','print',target,check=False).returncode!=0
            args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps(proof,indent=2))

if __name__=='__main__':main()

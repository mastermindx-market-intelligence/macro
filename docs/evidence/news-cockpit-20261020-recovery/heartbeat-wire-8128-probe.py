import hashlib,json,os,socket,subprocess,tempfile,time,urllib.request
from pathlib import Path
import httpx
ROOT=Path('/Volumes/Mastermind 2/agent-workspaces/macro/web/news-cockpit-rebuild-20261018-astra-01')
report={'scope':'one real loopback HTTP stream; fixture identity override; not production/auth/capacity proof','api_sha256':hashlib.sha256((ROOT/'app/news_desk.py').read_bytes()).hexdigest(),'events':[]}
with tempfile.TemporaryDirectory(prefix='news9612-wire-') as td:
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
    base=f'http://127.0.0.1:{port}';env=os.environ.copy();env['NEWS_DESK_PREVIEW_DIR']=td
    with open(Path(td)/'server.log','w+') as log:
        process=subprocess.Popen(['/opt/homebrew/bin/uvicorn','scripts.news_desk_preview:app','--host','127.0.0.1','--port',str(port),'--log-level','warning'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            for _ in range(80):
                if process.poll() is not None:raise RuntimeError('preview exited')
                try:
                    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(base+'/news.html',timeout=.7) as r:
                        if r.status==200:break
                except Exception:time.sleep(.15)
            else:raise RuntimeError('preview startup deadline')
            with httpx.Client(timeout=httpx.Timeout(75.0,read=12.0),trust_env=False) as client:
                started=time.monotonic()
                with client.stream('GET',base+'/api/news-desk/stream',headers={'Accept':'text/event-stream'}) as stream:
                    assert stream.status_code==200
                    report['headers']={k:stream.headers.get(k) for k in ['cache-control','content-type','vary']}
                    frame=[]
                    for line in stream.iter_lines():
                        if line:frame.append(line);continue
                        if not frame:continue
                        fields={}
                        for item in frame:
                            key,_,value=item.partition(':');fields.setdefault(key,[]).append(value.lstrip())
                        event=fields.get('event',['message'])[0]
                        data=json.loads('\n'.join(fields.get('data',['{}'])))
                        elapsed=time.monotonic()-started
                        report['events'].append({'event':event,'elapsed_seconds':round(elapsed,3)})
                        if event=='snapshot':
                            report['snapshot_revision']=fields.get('id',[''])[0]
                            report['stories']=len(data.get('stories',[]))
                        elif event=='heartbeat':
                            assert set(data)=={'at'},data
                        elif event=='reconnect':
                            assert data.get('reason')=='refresh_session'
                        else:raise AssertionError('unexpected event '+event)
                        frame=[]
                report['elapsed_seconds']=round(time.monotonic()-started,3)
            assert report['events'][0]['event']=='snapshot'
            assert report['events'][-1]['event']=='reconnect'
            heartbeat=[x for x in report['events'] if x['event']=='heartbeat']
            assert len(heartbeat)>=11,report
            times=[report['events'][0]['elapsed_seconds']]+[x['elapsed_seconds'] for x in heartbeat]
            report['max_heartbeat_gap_seconds']=round(max(b-a for a,b in zip(times,times[1:])),3)
            assert report['max_heartbeat_gap_seconds']<10,report
            assert 59<=report['elapsed_seconds']<=72,report
        finally:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)
            report['fixture_server_stopped']=process.returncode is not None
Path('/tmp/news-9612-live-wire-probe.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)

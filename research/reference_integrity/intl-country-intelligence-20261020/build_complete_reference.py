"""Run the unchanged primary International builder on an isolated copy of existing stores."""
from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import subprocess,json,os,shutil,re,sys,time
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
BUILD=Path('/tmp/intl-country-cockpit-rig-build-20261020/source')
SOURCE_SHA='6ad0c377ed80a8ccf07ecbfb6c7b44530b753cf7'
def main():
    snapshot=json.loads((OUT/'production_input_snapshot.json').read_text())
    assert snapshot['immutable_build_source']==SOURCE_SHA
    for row in snapshot['files']:
        assert sha256((BUILD/row['path']).read_bytes()).hexdigest()==row['sha256'],row['path']
    started=datetime.now(timezone.utc).isoformat()
    tick=time.monotonic()
    command=[sys.executable,'-m','scripts.build_intl']
    env=dict(os.environ)
    env.pop('PYTHONPATH',None)
    with (OUT/'complete_build.log').open('w') as log:
        result=subprocess.run(command,cwd=BUILD,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
    receipt={'schema':'intl.reference_complete_build.v1','source_commit':SOURCE_SHA,
        'input_snapshot':'production_input_snapshot.json',
        'input_snapshot_sha256':sha256((OUT/'production_input_snapshot.json').read_bytes()).hexdigest(),
        'kind':'unchanged ordinary builder, isolated source export and copied existing production inputs',
        'command':command,'started_at':started,'finished_at':datetime.now(timezone.utc).isoformat(),
        'duration_seconds':round(time.monotonic()-tick,2),'exit_code':result.returncode,
        'source_reacquisition':False,'production_mutation':False,'files':[]}
    if result.returncode==0:
        html=BUILD/'site/intl.html'
        assert html.is_file()
        target=OUT/'proposed'
        target.mkdir(exist_ok=True)
        required={'intl.html'}
        required.update(p.name for p in (BUILD/'site').iterdir() if p.is_file() and p.suffix in {'.css','.js'})
        text=html.read_text()
        for item in re.findall(r"""(?:src|href)=["']([^"']+)["']""",text):
            item=item.split('?')[0].split('#')[0].lstrip('/')
            if item and not '://' in item and not item.startswith('data:') and item.endswith(('.css','.js','.woff2','.woff','.json')):
                required.add(item)
        for item in sorted(required):
            src=BUILD/'site'/item
            if not src.is_file(): src=BUILD/'templates'/item
            if not src.is_file():
                receipt.setdefault('missing_optional_assets',[]).append(item)
                continue
            dst=target/item
            dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(src,dst)
            receipt['files'].append({'path':str(dst.relative_to(ROOT)),'source_path':str(src.relative_to(BUILD)),
                'sha256':sha256(dst.read_bytes()).hexdigest(),'bytes':dst.stat().st_size})
        receipt['html_bytes']=html.stat().st_size
        receipt['html_sha256']=sha256(html.read_bytes()).hexdigest()
        receipt['rendered_markers']={name:(name in text) for name in [
            'imc-world','imc-country-JP','intl-analysis-tools','intl-legacy-research',
            'data-view="macro"','data-view="risk"','data-view="history"','intl-growth-inflation']}
    (OUT/'complete_build_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='files'}))
    return result.returncode
if __name__=='__main__':
    raise SystemExit(main())

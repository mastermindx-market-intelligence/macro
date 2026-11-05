"""Read-only release identity probe. Run over the existing SSH path after hold release.
Does not fetch, deploy, restart, call candidate APIs or read raw claims/grades.
"""
import datetime,hashlib,json,os,stat,subprocess
from pathlib import Path
EXPECTED = {'admin/evidence_findings.py': 'd2355370c9c458db54a35e2253903d5b781b5b0193c945b587618706cb3bf909', 'admin/evidence_status.py': '5315e8e95b2a5ee3c5c12b88eac8126c8578db12a773357916aed20bdb459efd', 'admin/intelligence_os.py': '45eceabbee1d04ecf820b1d2ca5b24a5c0b417ec27a6171ed5939f7010e59873', 'admin/server.py': '53e65e1fca02988f7a0838d2b64026b78e3921c7c66a366e4be6c04e1e93a87b', 'admin/static/app.js': '6728183681df41e488494fd2f310c4ee62d990252149af9a118b97cc2a513772', 'admin/static/index.html': '27a1a4e55dee999b435dda94c86730987624621ee3868c7fbea086e308645179', 'admin/static/preferences.js': 'c22da47436d7db34ff2dec4de32cc1924aac756d2f8f15063049b1042a0e760f', 'admin/static/styles.css': '203f9d806f35441e598189654b91b0c97243feecb5319c5943df3617e0cabe60', 'app/deploy/update.sh': 'fc59de0f72c774a6d29287c110cb31fb3e57bedc8f73cd5d0dd9350991f2f322', 'engine/neuralweb/eval/benchmark_eval_os_measurement_v1.json': 'f86677c419e97eb3932024db56e5e147de7b5a88536bb9701af5ea367e8140db', 'engine/neuralweb/response_eval.py': 'b4caa23259a91e78ef4ddbbbce2ec38c6339fa12090f9135018d125d1b320e1d', 'engine/qledger.py': '6473c710806b26bc5ee3da3ad781d07b3ca02f208f9789a723186216819c1e00', 'scripts/build_intelligence_registry.py': '8f224e29d69517cbb5fd1e390ec05f70755d0bf5f89056ff016f2caf9d7381a9', 'scripts/grade_qledger.py': '56d49a99be7105c29f80795c2c2af8d89605f660f6280042fdb28072731155b2', 'admin/theme_tokens.py': '1e27b1decad0273a3a495e7151be8ba22a03e131761ceeb93da065af1693cf46', 'templates/theme.css': '311f121e4d748b917aaa3ce8ca6dae411782a02571fc39f551e3516a4e0a2ab2', 'engine/qledger_desk_adapter.py': '55f7304d9c422992cb5710a95c118c16cfd78999b7bb51095e0951b9018c11c4'}
ROOT=Path('/opt/macro')
def file_digest(path,limit=16*1024*1024):
    try:
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as f:
            before=os.fstat(f.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size>limit:
                return {'state':'rejected_kind_or_bound'}
            b=f.read(limit+1);after=os.fstat(f.fileno())
        if len(b)>limit or (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):
            return {'state':'moving_or_over_bound'}
        return {'state':'observed','bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'mtime_ns':before.st_mtime_ns}
    except (OSError,ValueError) as e:return {'state':'unavailable','error_type':type(e).__name__}
def command(args):
    r=subprocess.run(args,capture_output=True,text=True,timeout=15)
    return {'returncode':r.returncode,'stdout':r.stdout.strip()}
def identity():
    return {'installed_head':command(['git','-C',str(ROOT),'rev-parse','HEAD']),
            'admin':command(['systemctl','show','admin.service','--property=ActiveState,SubState,MainPID,ExecMainStartTimestamp'])}
before_identity=identity()
sources={}
for name,want in EXPECTED.items():
    sources[name]=file_digest(ROOT/name);sources[name]['expected_sha256']=want;sources[name]['matches_candidate']=sources[name].get('sha256')==want
updater=file_digest(Path('/usr/local/bin/macro-update'));updater['matches_candidate']=updater.get('sha256')==EXPECTED['app/deploy/update.sh']
owner_artifacts={name:file_digest(ROOT/name) for name in ['data/qledger/run_status.json','site/qledger/track_record.json']}
resource=command(['systemctl','show','admin.service','--property=MemoryCurrent,MemoryPeak,MemoryMax'])
after_identity=identity()
stable_epoch=before_identity==after_identity and all(v['returncode']==0 for v in before_identity.values())
print(json.dumps({'schema':'eval_os.installed_identity_observation.v2','observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'candidate':'05a75a4131f5e695a1d31616ac9e2ecca6059c67','before_identity':before_identity,'after_identity':after_identity,'stable_observed_epoch':stable_epoch,'sources':sources,'installed_updater':updater,'admin_resources':resource,'owner_artifacts':owner_artifacts,'scope':'Bounded file and process observations. Stable endpoints do not prove atomicity or served assets. Not API/render acceptance, market freshness, release permission or post-release update proof.'},indent=2))

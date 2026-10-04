"""Controlled fixtures for the actual Crypto builder; no published site writes."""
from pathlib import Path
from unittest.mock import patch
import copy
import hashlib
import json
import shutil
import sys

ROOT=Path('/Volumes/Mastermind/worktrees/crypto-vector-r2-20260926-sol-001-sparse').resolve()
sys.path.insert(0,str(ROOT))
from lib import store
from scripts import build_crypto

OUT=Path('/Volumes/Mastermind/research/crypto-vector-r2-20260926-sol-001/crypto_h5_actual')
OUT.mkdir(parents=True,exist_ok=True)
read_original=store.read
SIG=read_original('vector','signals')
if SIG is None or SIG.empty:
    raise SystemExit('vector signals unavailable')
as_of=str(SIG.index[-1].date())
price=float(SIG['close'].iloc[-1]) if 'close' in SIG.columns else None
base={
    'schema':'btc.decision/v1','status':'ok','as_of':as_of,'integrity_ok':True,
    'final_exposure_pct':60,'errors':[],
    'authority_source':'btc.decision/v1.final.exposure_pct',
}
states={
    'happy':base,
    'zero':{**base,'final_exposure_pct':0},
    'unavailable':{**base,'status':'unavailable','integrity_ok':False,'final_exposure_pct':None,
                   'errors':['RAW_FINAL_MISMATCH_WITHOUT_NAMED_OVERRIDE']},
    'stale':{**base,'as_of':str(SIG.index[-2].date())},
    'breakdown':base,
    'zero-gap':{**base,'final_exposure_pct':0},
    'malformed':{**base,'final_exposure_pct':'60'},
}
receipt=[]
for name, projection in states.items():
    decision=copy.deepcopy(projection)
    work=OUT/f'_work_{name}'
    work.mkdir(parents=True,exist_ok=True)
    cockpit={
        'schema':'crypto.cockpit/v1','display_only':True,'as_of':as_of,
        'hero':{'asset':'BTC-USD','price':price,'change_24h_pct':0.0,
                'stance_en':'Controlled fixture','stance_zh':'受控示例',
                'summary_en':'Controlled H5 authority fixture, not a live allocation.',
                'summary_zh':'H5 权威链路受控示例，并非实时配置。',
                'master_score':None,'exposure_pct':decision['final_exposure_pct'],'gate_active':False},
        'decision':decision,'axes':[],
        'authority':{'sizing_source':'btc.decision/v1.final.exposure_pct'},
    }
    (work/'crypto_cockpit.json').write_text(json.dumps(cockpit,ensure_ascii=False,allow_nan=False,indent=2))
    source=SIG.copy(deep=True)
    if name in ('breakdown','zero-gap'):
        source.loc[source.index[-1],'close']=float('nan')
    def fixture_read(group, name, *args, **kwargs):
        if (group,name)==('vector','signals'):
            return source.copy(deep=True)
        return read_original(group,name,*args,**kwargs)
    with patch.object(store,'read',side_effect=fixture_read):
        html=build_crypto.build(work)
    dest=OUT/f'crypto-{name}.html'
    shutil.copy2(html,dest)
    receipt.append({'scenario':name,'decision':decision,'signal_as_of':as_of,
                    'close_missing':name in ('breakdown','zero-gap'),
                    'html_sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})

for asset in ['theme.css','illus.css','illus.js','theme.js','mm_brain.js','navigation-refresh.css','logo_config.js','stock-logos.js','live_config.js','live.js']:
    src=ROOT/'templates'/asset
    if not src.exists(): src=ROOT/'site'/asset
    if src.exists(): shutil.copy2(src,OUT/asset)
(OUT/'scenario_receipts.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False))
print('CONTROLLED_BUILD',OUT,'as_of',as_of,'scenarios',len(receipt))
for record in receipt:
    print(record['scenario'],record['html_sha256'])

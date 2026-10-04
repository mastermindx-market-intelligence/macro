"""Read-only R13 receipt verification; not independent human/science review.

No template build, provider call, CVD composition, live collector or state write.
This checks saved browser measurements and immutable source/input identities.
"""
from pathlib import Path
import hashlib
import itertools
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from lib import config
HERE=Path(__file__).resolve().parent
BASE='6812add52487ccbefc067d0850e8ebd4dcc8b3af'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def original(p):return subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT)

def main():
    prior=json.loads((HERE.parent/'r12/pipeline_proof.json').read_text())
    data=Path(config.data_dir())
    for key in ['inputs','old_live_observation_files']:
        assert all((sha(data/k) if (data/k).exists() else None)==v for k,v in prior[key].items()),key
    assert all(sha(data/k)==v for k,v in prior['gates'].items())
    assert all(sha(ROOT/k)==v for k,v in prior['prior_evidence'].items())
    for path in prior['sources']:
        if path=='scripts/build_vector.py':continue
        assert (ROOT/path).read_bytes()==original(path),path
    assert (ROOT/'templates/_crypto_house_style.html.j2').read_bytes()==original('templates/_crypto_house_style.html.j2')
    # Removing only the added pure projection and its one vm reference restores
    # the exact previous builder, including all existing models and side effects.
    path='scripts/build_vector.py';s=(ROOT/path).read_text()
    a=s.index('def _derivatives_flow_view(regime) -> dict:');b=s.index('def main() -> int:',a)
    restored=(s[:a]+s[b:]).replace('        "derivatives_flow": _derivatives_flow_view(regime),\n','',1)
    assert restored.encode()==original(path),'Existing builder logic changed beyond declared insertion'
    tests=(ROOT/'tests/test_vector_r2_frontdoor.py').read_bytes()
    assert tests.startswith(original('tests/test_vector_r2_frontdoor.py'))
    r=json.loads((HERE/'browser_proof.json').read_text())
    assert all(sha(ROOT/k)==v for k,v in r['source_sha256'].items())
    expected={'current':('available','62.5%'),'stale':('stale','—'),'gap':('coverage_gap','—'),
              'no_activity':('no_activity','—'),'only_24h':('available','62.5%'),
              'zero_share':('available','0.0%'),'unavailable':('unavailable','—')}
    keys={(x['scenario'],x['width'],x['theme'],x['lang']) for x in r['cases']}
    assert len(r['cases'])==112 and keys==set(itertools.product(expected,[320,390,768,1440],['dark','light'],['en','zh']))
    for x in r['cases']:
        assert (x['state'],x['share'])==expected[x['scenario']]
        assert x['http_status']==200 and x['keyboard_disclosure'] and x['touch_height']>=44
        assert not x['page_errors'] and not x['geometry']['pageOverflow'] and not x['geometry']['innerOverflow']
        assert x['geometry']['proseMinimum']>=14
        assert x['font_status']['inter400'] and x['font_status']['inter700']
        h=x['hero_geometry']
        if x['width']<=780:
            assert h['copyWidth']>=h['container']-2 and h['positionTop']>=h['copyBottom']
    assert len(r['screenshots'])==14 and all(sha(ROOT/k)==v for k,v in r['screenshots'].items())
    for weight in [400,500,600,700,800,900]:
        name=f'fonts/Inter-{weight}.woff2'
        assert sha(ROOT/'templates'/name)==r['fixture']['copied_assets'][name]
    old=json.loads((HERE/'before_mobile_repair/hero_geometry.json').read_text())
    assert old['copyWidth']==42 and old['container']==336 and old['viewport']==390
    fixed=next(x['hero_geometry'] for x in r['cases'] if x['scenario']=='current' and x['width']==390 and x['theme']=='light' and x['lang']=='zh')
    assert fixed['copyWidth']>=old['container']-2
    canonical=ROOT/'mockups/evidence/crypto-vector-r13-context'
    m=json.loads((canonical/'manifest.json').read_text());states=m['pages'][0]['states']
    assert m['outcome']=='captured' and len(states)==16
    assert len({(x['viewport'],x['theme'],x['locale'],x['force_state']) for x in states})==16
    for x in states:
        assert x['captured'] and x['applied_theme']==x['theme'] and x['applied_locale']==x['locale']
        p=canonical/x['file'];assert p.stat().st_size==x['bytes'] and sha(p)==x['sha256']
        if x['force_state']:assert x['force_state']=='flow-focus' and x['applied_force_state']=='flow-focus'
    full=(HERE/'verification_final.txt').read_text()
    assert '439 passed' in full and full.count('EXIT 0')==5
    if (HERE/'MANIFEST.json').exists():
        package=json.loads((HERE/'MANIFEST.json').read_text())
        assert all(sha(ROOT/k)==v['sha256'] and (ROOT/k).stat().st_size==v['bytes'] for k,v in package['artifacts'].items())
    print('R13_RECEIPTS_VERIFIED: 112 browser cells, 16 canonical image states, 14 inspected-state snapshots, hero geometry and canonical font identities.')
    print('R13_SOURCE_SCOPE: existing builder restored exactly after removing only added pure projection/vm wiring; old tests are byte-prefix intact; engine/collector/house styles unchanged.')
    print('R13_HISTORY: 57 input identities,18 gates,137 prior artifacts and absent live receipt stores unchanged. 439 regression tests recorded; separate held optional tests are not counted.')
    print('Controlled fixture, initial expanded desk/CSP for canonical capture, remaining resource gaps and no independent-review/deployment claims remain explicit.')

if __name__=='__main__':main()

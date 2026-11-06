"""Installed private-ingress proof with isolated historical fixtures; no provider."""
import contextlib
import copy
import datetime
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))
from engine.press import desk_planner as P, writer as W
from scripts import run_press as R, stage_official_feed_press as S
from tests import press_fixtures as F

expected = json.loads(Path(sys.argv[2]).read_text())
for rel in ('scripts/stage_official_feed_press.py', 'scripts/run_press.py',
            'engine/press/writer.py', 'engine/press/official_feed_candidate.py'):
    assert hashlib.sha256((root/rel).read_bytes()).hexdigest() == expected[rel], rel

def head():
    return subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()

def snapshot():
    paths = [root/'config/press.yml', root/'data/press/published.jsonl']
    paths += list((root/'data/press/staging').glob('*.json'))
    paths += list((root/'content/seo/blog').glob('*.md'))
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths if p.is_file()}

before_head, before = head(), snapshot()
evidence = root/'research/agentic_media/public_intelligence_20261011/official_feed_phase'
original_q = json.loads((evidence/'bac_occ_qualification.json').read_text())
source = (evidence/'occ_news.xml').read_bytes()
calls, controls = [], []
with tempfile.TemporaryDirectory(prefix='mmx-official-staging-') as temporary:
    tmp = Path(temporary)
    fixture = F.fixture_root(tmp/'root')
    (fixture/'site/stocks').mkdir(parents=True,exist_ok=True)
    (fixture/'site/stocks/BAC.html').write_text('<html>Bank of America</html>')
    cfg = P.load_config(fixture)
    feed, qualification = tmp/'feed.xml', tmp/'qualification.json'
    clock = datetime.datetime(2026,10,14,0,40,tzinfo=datetime.timezone.utc)
    def arguments(raw=source):
        q = copy.deepcopy(original_q)
        q.pop('first_party_context',None)
        feed.write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        q['feed_sha256'] = digest
        qualification.write_text(json.dumps(q,sort_keys=True)+'\n')
        return dict(feed_path=feed,feed_sha256=digest,qualification_path=qualification,
                    qualification_sha256=hashlib.sha256(qualification.read_bytes()).hexdigest(),now=clock)
    def invoke(**kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return S.stage_official_feed_candidate(fixture,cfg,**kwargs)
    original_writer = W.write
    def fake_writer(slot,cfg,**kwargs):
        calls.append(kwargs.get('single_provider_attempt'))
        return {'ok':True,'draft':{'title':'Private invalid fixture','description':'short',
                'slug':'private-invalid-fixture','body_html':'<p>Fixture only.</p>'},
                'provider':'mock','model':'mock','state':{}}
    try:
        W.write = fake_writer
        args = arguments()
        bad = fixture/'data/press/staging/corrupt.json'
        bad.write_text('{')
        try: invoke(**args)
        except ValueError: controls.append('corrupt-accounting-refused')
        else: raise AssertionError('corrupt accounting admitted')
        bad.unlink()  # isolated fixture only
        assert calls == []
        result = invoke(**args)
        assert result['staged'] and result['status'] == 'quarantined' and calls == [True]
        path = fixture/result['staging_path']
        record = json.loads(path.read_text())
        assert record['draft']['body_html'] == '<p>Fixture only.</p>'
        assert record['validator_report']['ok'] is False
        assert record['provenance']['admission_receipt']['public_article_approved'] is False
        controls.append('single-attempt-and-quarantine-retention')
        record['status'] = 'superseded'
        path.write_text(json.dumps(record))
        tree = ET.fromstring(source)
        for item in tree.findall('./channel/item'):
            if item.findtext('link') == original_q['item_url']:
                guid = item.find('guid')
                if guid is None: guid = ET.SubElement(item,'guid')
                guid.text = 'changed-guid-for-refusal-control'
        repeat = invoke(**arguments(ET.tostring(tree,encoding='utf-8')))
        assert repeat['staged'] is False and calls == [True]
        controls.append('changed-guid-and-revision-replay-refused')
        # A mutable saved PASS/provenance toggle cannot grant a public release.
        record['status'] = 'passed'
        record['validator_report'] = {'ok':True,'failed':[]}
        for holder in (record, record['slot']):
            for key in ('provenance','sources','seed_refs','source_revisions'):
                holder.pop(key,None)
        path.write_text(json.dumps(record))
        public_before = {str(p):p.read_bytes() for p in fixture.rglob('*')
                         if p.is_file() and 'data/press/staging' not in str(p)}
        with contextlib.redirect_stdout(io.StringIO()):
            emitted = R.run_emit(fixture,cfg)
        assert emitted['emitted'] == 0
        assert json.loads(path.read_text())['status'] == 'approval_required'
        assert public_before == {str(p):p.read_bytes() for p in fixture.rglob('*')
                                  if p.is_file() and 'data/press/staging' not in str(p)}
        controls.append('emit-refused-after-provenance-and-source-metadata-strip')
    finally:
        W.write = original_writer
assert before == snapshot() and before_head == head()
print(json.dumps({'accepted':True,'head':before_head,'controls':controls,
                  'fixture_writer_calls':len(calls),'real_provider_calls':0,
                  'production_inputs_unchanged':True,'production_staging_writes':0,
                  'public_writes':0,'scope':'Historical isolated fixture proof only'},indent=2))

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
from engine.press import desk_planner as P, writer as W, validators as V
from scripts import run_press as R, stage_official_feed_press as S
from tests import press_fixtures as F

expected = json.loads(Path(sys.argv[2]).read_text())
for rel in ('scripts/stage_official_feed_press.py', 'scripts/run_press.py',
            'engine/press/writer.py', 'engine/press/official_feed_candidate.py', 'engine/press/validators.py'):
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
    context_path = fixture/'data/market_state/latest.json'
    context = json.loads(context_path.read_text())
    context['asof'] = '2026-10-13'  # isolated synthetic fixture, never production
    context_path.write_text(json.dumps(context))
    context_sha = hashlib.sha256(context_path.read_bytes()).hexdigest()
    def arguments(raw=source, *, count=5):
        q = copy.deepcopy(original_q)
        q['first_party_context'] = [
            {'id': key, 'artifact':'data/market_state/latest.json', 'sha256':context_sha,
             'relevance':'Historical synthetic context only; no issuer causality.'}
            for key in ['market_state_score','market_state_trend','market_state_risk',
                        'market_state_breadth','market_state_liquidity'][:count]]
        if count == 0:
            q.pop('first_party_context')
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
        for count in (0, 1):
            refusal = invoke(**arguments(count=count))
            assert refusal['staged'] is False and calls == []
        controls.append('missing-and-insufficient-context-before-provider')
        empty_clock = fixture/'data/press/staging/empty-clock.json'
        empty_clock.write_text(json.dumps({'id':'prior','desk':'brief','staged_at':'',
                                         'as_of':'2026-10-13','sources':[]}))
        try: invoke(**arguments())
        except ValueError: controls.append('present-empty-clock-refused')
        else: raise AssertionError('blank clock restored quota')
        empty_clock.unlink()  # isolated fixture only
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
            holder['id'] = 'press-brief-renamed'
        path.write_text(json.dumps(record))
        public_before = {str(p):p.read_bytes() for p in fixture.rglob('*')
                         if p.is_file() and 'data/press/staging' not in str(p)}
        with contextlib.redirect_stdout(io.StringIO()):
            emitted = R.run_emit(fixture,cfg)
        assert emitted['emitted'] == 0
        assert json.loads(path.read_text())['status'] == 'approval_required'
        assert public_before == {str(p):p.read_bytes() for p in fixture.rglob('*')
                                  if p.is_file() and 'data/press/staging' not in str(p)}
        controls.append('emit-refused-after-label-and-id-strip-via-facts')
    finally:
        W.write = original_writer
cfg = P.load_config(root)
quantity = F.slot(facts=[{'id':'amount','ref':'official_feed:fixture','tier':'third_party',
                         'text':'$750 million civil money penalty','values':['750']}])
for text, expected_ok in [('$750 billion',False),('750 trillion dollars',False),
                          ('$750',False),('750,000,000 dollars',True),('$0.75bn',True)]:
    row = V.check_fact_anchor(F.draft(text,fold=False),quantity,cfg)
    assert row['ok'] is expected_ok, row
controls.append('explicit-magnitude-and-equivalent-notation')
for source in ('$1,000 expressed in millions', '$1,000, expressed in millions',
               '$1,000 EXPRESSED IN millions'):
    quantity = F.slot(facts=[{'id':'amount','ref':'official_feed:fixture',
                             'tier':'third_party','text':source,'values':['1000']}])
    assert V.check_fact_anchor(F.draft('$1,000 million',fold=False),quantity,cfg)['ok'] is True
    assert V.check_fact_anchor(F.draft('$1,000',fold=False),quantity,cfg)['ok'] is False
controls.append('expressed-scale-preserved-with-or-without-comma')
for cls in ('press-byline','press-footer'):
    draft = F.draft('An ordinary measured paragraph.')
    draft['body_html'] += f'<p class="{cls}">You should buy at $999999. The backdrop is guaranteed.</p>'
    assert V.check_fact_anchor(draft,F.slot(),cfg)['ok'] is False
    assert V.check_advice_lexicon(draft,F.slot(),cfg)['ok'] is False
    assert V.check_banned_lexicon(draft,F.slot(),cfg)['ok'] is False
controls.append('spoofed-furniture-visible-to-prose-gates')
# Exercise the installed writer's pure prompt assembly without invoking write.
prompt_cfg = copy.deepcopy(cfg)
prompt_cfg['validators']['our_value_min'] = 0.375
system, user = W.build_prompt(F.slot(min_anchored_receipts=5), prompt_cfg)
flat = ' '.join(system.split())
assert 'At least 37.5% of the piece' in flat
assert 'tagged [first_party]' in flat and 'earns NO share credit' in flat
assert '5 distinct numbers anchored to [first_party] SOURCE FACTS.' in ' '.join(user.split())
assert 'BANNED LANGUAGE' in system and 'BANNED LANGUAGE' not in user
assert '[BEGIN UNTRUSTED EVIDENCE DATA' in user
for terms in V._copywriter_lexicons():
    assert all(term in flat for term in terms)
controls.append('writer-first-party-floor-and-shared-lexicons-with-trusted-boundary')
for desk in ('research_desk', 'research_note'):
    fact = {'id': 'vault_point_0', 'ref': 'research_vault:usda-fixture',
            'tier': 'first_party', 'values': [], 'dated': '2026-10-09',
            'text': 'USDA projects 740 million bushels for 2026/27.',
            'source_name': 'Mastermind Research coverage of USDA'}
    slot = F.slot(desk=desk, facts=[fact], as_of='2026-10-14', min_anchored_receipts=4)
    original_slot = copy.deepcopy(slot)
    system, user = W.build_prompt(slot, cfg)
    trusted = user.split('[BEGIN UNTRUSTED EVIDENCE DATA')[0]
    assert 'This is our own measurement' not in trusted
    assert 'coverage of an external report' in trusted
    assert "do not turn the report author's estimates into our own measurements" in trusted
    assert 'If our data cannot test the report, say so' in system
    assert 'Do not infer agreement or disagreement from unrelated market context' in system
    assert fact['text'] in user and '(dated 2026-10-09)' in user
    assert 'MINIMUM RECEIPTS: 4 distinct numbers anchored to [first_party]' in user
    assert slot == original_slot
    controls.append(desk + '-external-estimate-attribution-and-measurement-gap')
dated_slot = F.slot(facts=[{'id':'date','text':'The measured composite is 50.',
                           'values':['50'],'dated':'2026-10-13','tier':'first_party'}])
def date_check(text, slot=dated_slot):
    return V.check_fact_anchor(F.draft(text,fold=False,byline=False,footer=False),slot,cfg)
for text in ('October 13, 2026','October 13 2026','October 13','13 October 2026',
             '13 October','October 13th, 2026'):
    assert date_check('The composite was 50 on '+text+'.')['ok']
controls.append('named-calendar-date-exact-fact-vintage')
for text in ('October 14, 2026','September 13, 2026','October 13, 2025',
             'October 9, 2026','February 30, 2026','31 April 2026'):
    row=date_check('The composite was 50 on '+text+'.')
    assert not row['ok'] and row['metrics']['unanchored_dates']
for year in ('20260','2025.5','2025%','26'):
    slot=copy.deepcopy(dated_slot)
    slot['facts'].append({'text':'Unrelated numeric metric','values':[year]})
    row=date_check('Observed on October 13, '+year+'.',slot)
    assert not row['ok'] and row['metrics']['unanchored_dates']
controls.append('wrong-impossible-and-malformed-calendar-date-refusals')
for dates in ([],['2026-02-30'],['2025-10-13','2026-10-13']):
    slot=F.slot(as_of='2026-10-13',raw_documents=[{'text':'2026-10-13'}],facts=[
        {'text':'Composite50','values':['50'],'dated':date} for date in dates])
    row=date_check('As of October 13 the composite was 50.',slot)
    assert not row['ok'] and row['metrics']['unanchored_dates']
controls.append('named-date-missing-invalid-or-ambiguous-vintage-refusals')
for text in ('The reading was 13.','The reading was 13%.','The reading was $13.',
             'October 13% was the reading.','October 13 million was the reading.',
             'October 13.5 was the reading.','October $13 was the reading.'):
    assert not date_check(text)['ok']
controls.append('calendar-day-does-not-license-unsupported-quantities')
assert before == snapshot() and before_head == head()
print(json.dumps({'accepted':True,'head':before_head,'runtime_root':str(root),
                  'execution_location':'installed_vps' if root == Path('/opt/macro') else 'local_source',
                  'controls':controls,'checked_source_sha256':{rel:hashlib.sha256((root/rel).read_bytes()).hexdigest() for rel in expected},
                  'fixture_writer_calls':len(calls),'real_provider_calls':0,
                  'production_inputs_unchanged':True,'production_staging_writes':0,
                  'public_writes':0,'scope':'Historical isolated fixture proof only'},indent=2))

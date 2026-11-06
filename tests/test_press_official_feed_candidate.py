"""A selected public-agency RSS fact is evidence, never a writer admission."""
import hashlib
import json
from pathlib import Path
import pytest
from tests import press_fixtures as F

EVIDENCE = Path(__file__).resolve().parents[1] / 'research/agentic_media/public_intelligence_20261011/official_feed_phase'
URL = 'https://www.occ.gov/news-issuances/news-releases/2026/nr-occ-2026-89.html'
FEED = 'https://www.occ.treas.gov/rss/occ_news.xml'

def dump(path, value):
    path.write_text(json.dumps(value, sort_keys=True)+'\n')
    return hashlib.sha256(path.read_bytes()).hexdigest()

@pytest.fixture
def inputs(tmp_path):
    root=F.fixture_root(tmp_path/'root');(root/'site/stocks').mkdir(parents=True,exist_ok=True)
    (root/'site/stocks/BAC.html').write_text('<html>Bank of America</html>')
    feed=tmp_path/'source.xml';feed.write_bytes((EVIDENCE/'occ_news.xml').read_bytes())
    q={'kind':'official_feed_editorial_qualification','source_key':'occ_news','feed_url':FEED,
       'feed_sha256':hashlib.sha256(feed.read_bytes()).hexdigest(),'item_url':URL,
       'published_at':'2026-10-13T20:15:00+00:00','event_date':'2026-10-13',
       'observed_at':'2026-10-14T00:19:37+00:00',
       'rights_basis':{'qualification':'government_authored_factual_reporting','scope':'Original factual reporting of the agency assessment; no imagery or endorsement.'},
       'review_result':'accepted_as_editorial_candidate_only',
       'reviewed_claims':[{'literal':'$750 million civil money penalty','quantity_literal':'$750 million'}],
       'reviewed_tickers':{'BAC':'Bank of America'},'allow_stage':False,'allow_emit':False,'publication_approved':False}
    path=tmp_path/'qualification.json'
    return dict(feed_path=feed,feed_sha256=q['feed_sha256'],qualification_path=path,
                qualification_sha256=dump(path,q),root=root,as_of='2026-10-14T00:25:00+00:00')

def change(inputs, fn):
    q=json.loads(inputs['qualification_path'].read_text());fn(q)
    inputs['qualification_sha256']=dump(inputs['qualification_path'],q)

def invoke(inputs):
    from engine.press.official_feed_candidate import plan_official_feed_candidate
    return plan_official_feed_candidate(**inputs)

def test_current_documented_occ_event_keeps_original_source_and_remains_planning_only(inputs):
    before={str(p):p.read_bytes() for p in inputs['root'].rglob('*') if p.is_file()}
    r=invoke(inputs);ctx=r['validation_context']
    assert r['operation']=='planning_only'
    assert r['allow_stage'] is r['allow_emit'] is r['publication_approved'] is False
    assert r['cadence_consumed'] is False and 'id' not in r
    assert r['event_date']=='2026-10-13' and r['published_at']=='2026-10-13T20:15:00+00:00'
    assert ctx['primary_source']=={'kind':'external','name':'Office of the Comptroller of the Currency','url':URL}
    assert ctx['allowed_links']==['https://www.mastermind-x.com/stocks/BAC.html']
    assert ctx['facts'][0]['text']=='$750 million civil money penalty'
    assert ctx['facts'][0]['tier']=='third_party' and ctx['facts'][0]['values']==['750']
    assert ctx['min_anchored_receipts']==5
    assert before=={str(p):p.read_bytes() for p in inputs['root'].rglob('*') if p.is_file()}

@pytest.mark.parametrize('patch',[
 {'source_key':'cnbc_top'},{'feed_url':'https://evil.test/rss'}, {'event_date':'2026-10-08'},
 {'published_at':'2026-10-14T00:00:00+00:00'},{'rights_basis':{'qualification':'unqualified','scope':'anything'}},
 {'allow_stage':True},{'allow_emit':True},{'publication_approved':True},
 {'reviewed_tickers':{'BAC':'NVIDIA'}},{'reviewed_claims':[{'literal':'$1.95 billion total','quantity_literal':'$1.95 billion'}]},
])
def test_mutated_qualification_refuses(inputs,patch):
    change(inputs,lambda q:q.update(patch))
    with pytest.raises(ValueError):invoke(inputs)

def test_modified_feed_refuses_exact_hash_binding(inputs):
    inputs['feed_path'].write_bytes(inputs['feed_path'].read_bytes()+b' ')
    with pytest.raises(ValueError,match='hash'):invoke(inputs)

@pytest.mark.parametrize('clock',['', 'not-a-date', '13 Oct 2026 16:15:00'])
def test_missing_or_naive_publisher_clock_cannot_fall_back_to_poll_time(inputs,clock):
    text=inputs['feed_path'].read_text().replace('13 Oct 2026 16:15:00 -0400',clock)
    inputs['feed_path'].write_text(text);inputs['feed_sha256']=hashlib.sha256(text.encode()).hexdigest()
    change(inputs,lambda q:q.update(feed_sha256=inputs['feed_sha256']))
    with pytest.raises(ValueError,match='publisher clock'):invoke(inputs)

def test_unrelated_and_larger_source_claims_cannot_be_inferred_from_rss_summary(inputs):
    change(inputs,lambda q:q.update(reviewed_claims=[{'literal':'$750 million civil money penalty','quantity_literal':'$750 billion'}]))
    with pytest.raises(ValueError):invoke(inputs)

def test_candidate_without_existing_public_dossier_refuses(inputs):
    (inputs['root']/'site/stocks/BAC.html').unlink()
    with pytest.raises(ValueError,match='dossier'):invoke(inputs)

@pytest.mark.parametrize('atom',['$75', '50', '750', '$750 billion'])
def test_quantity_must_match_a_whole_source_atom(inputs,atom):
    change(inputs,lambda q:q['reviewed_claims'][0].update(quantity_literal=atom))
    with pytest.raises(ValueError,match='source evidence'):invoke(inputs)

@pytest.mark.parametrize('mutation',['duplicate','truncated','entity','lookalike'])
def test_ambiguous_or_incomplete_feed_refuses(inputs,mutation):
    import xml.etree.ElementTree as ET
    import copy
    tree=ET.fromstring(inputs['feed_path'].read_bytes());channel=tree.find('channel');item=channel.find('item')
    if mutation=='duplicate':channel.append(copy.deepcopy(item))
    elif mutation=='truncated':item.find('description').text += ' '+ 'irrelevant filler '*70
    elif mutation=='lookalike':
        url=URL.replace('www.occ.gov','www.occ.gov.evil.test');item.find('link').text=url
        change(inputs,lambda q:q.update(item_url=url))
    raw=ET.tostring(tree,encoding='utf-8')
    if mutation=='entity':raw=b'<!DOCTYPE rss [<!ENTITY payload "test">]>'+raw
    inputs['feed_path'].write_bytes(raw);inputs['feed_sha256']=hashlib.sha256(raw).hexdigest()
    change(inputs,lambda q:q.update(feed_sha256=inputs['feed_sha256']))
    with pytest.raises(ValueError):invoke(inputs)

def test_explicit_selected_context_uses_same_reviewed_measurement_contract(inputs):
    path=inputs['root']/'data/market_state/latest.json';path.parent.mkdir(parents=True,exist_ok=True)
    digest=dump(path,{'asof':'2026-10-13','score':50,'verdict':'MIXED'})
    row={'id':'market_state_score','artifact':'data/market_state/latest.json','sha256':digest,
         'relevance':'Dated broad backdrop only; not an explanation of bank-specific price effects.'}
    change(inputs,lambda q:q.update(first_party_context=[row]));r=invoke(inputs)
    assert r['validation_context']['facts'][-1]['values']==['50']
    assert r['validation_context']['facts'][-1]['tier']=='first_party'
    assert r['source_revisions']['artifact:data/market_state/latest.json']=='sha256:'+digest
    assert r['allow_stage'] is False

def test_existing_stage_blocks_same_source_without_consumer_writes(inputs):
    r=invoke(inputs);stage=inputs['root']/'data/press/staging';stage.mkdir(parents=True,exist_ok=True)
    dump(stage/'existing.json',{'sources':[r['source_ref']],'status':'in_progress'})
    assert invoke(inputs)['blocked_by_existing_coverage'] is True


def test_utf16_doctype_cannot_evade_byte_level_xml_guard(inputs):
    text=inputs['feed_path'].read_text().replace('encoding="Windows-1252"', 'encoding="UTF-16"')
    marker=text.index('?>')+2
    text=text[:marker]+'\n<!DOCTYPE rss [<!ENTITY agency "OCC">]>'+text[marker:]
    raw=text.encode('utf-16')
    inputs['feed_path'].write_bytes(raw);inputs['feed_sha256']=hashlib.sha256(raw).hexdigest()
    change(inputs,lambda q:q.update(feed_sha256=inputs['feed_sha256']))
    with pytest.raises(ValueError,match='entities|DOCTYPE|malformed'):
        invoke(inputs)


@pytest.fixture
def doj_inputs(tmp_path):
    evidence = EVIDENCE.parent / 'doj_source_phase'
    root = F.fixture_root(tmp_path / 'root')
    (root / 'site/stocks').mkdir(parents=True, exist_ok=True)
    (root / 'site/stocks/CVS.html').write_text('<html>CVS Health</html>')
    q = json.loads((evidence / 'cvs_candidate.json').read_text())
    result = {'root': root, 'as_of': '2026-10-14T04:00:00+00:00'}
    for key, name in [('feed_path', 'rss.xml'), ('release_path', 'release.html'),
                      ('policy_path', 'policy.html')]:
        path = tmp_path / name
        path.write_bytes((evidence / name).read_bytes())
        result[key] = path
    result.update(feed_sha256=q['feed_sha256'], qualification_path=tmp_path / 'q.json',
                  qualification_sha256=dump(tmp_path / 'q.json', q))
    return result


def test_doj_release_retains_allegation_limit_and_never_admits_a_writer(doj_inputs):
    before = {str(p): p.read_bytes() for p in doj_inputs['root'].rglob('*') if p.is_file()}
    r = invoke(doj_inputs)
    ctx = r['validation_context']
    assert ctx['primary_source']['name'] == 'U.S. Department of Justice'
    assert ctx['allowed_links'] == ['https://www.mastermind-x.com/stocks/CVS.html']
    assert ctx['facts'][0]['values'] == ['315']
    assert all(f['tier'] == 'third_party' for f in ctx['facts'])
    assert any('no determination of liability' in f['text'] for f in ctx['facts'])
    assert 'no determination of liability' in ctx['raw_documents'][0]['text']
    assert len(r['source_revisions']) == 3  # feed, release and policy bytes
    assert r['allow_stage'] is r['allow_emit'] is r['publication_approved'] is False
    assert r['cadence_consumed'] is False
    assert before == {str(p): p.read_bytes() for p in doj_inputs['root'].rglob('*') if p.is_file()}


@pytest.mark.parametrize('key', ['release_path', 'policy_path'])
def test_doj_requires_retained_full_release_and_policy(doj_inputs, key):
    doj_inputs.pop(key)
    with pytest.raises(ValueError, match='DOJ'):
        invoke(doj_inputs)


@pytest.mark.parametrize('key', ['release_path', 'policy_path'])
def test_doj_changed_document_bytes_refuse(doj_inputs, key):
    doj_inputs[key].write_bytes(doj_inputs[key].read_bytes() + b' ')
    with pytest.raises(ValueError, match='hash'):
        invoke(doj_inputs)


@pytest.mark.parametrize('patch', [
    {'source_qualifiers': []},
    {'source_qualifiers': ['CVS admitted liability.']},
    {'rights_basis': {'qualification': 'government_authored_factual_reporting',
                      'scope': 'anything', 'policy_url': 'https://evil.test/policy'}},
    {'source_key': 'occ_news'},
    {'event_date': '2026-10-08'},
])
def test_doj_changed_qualification_refuses(doj_inputs, patch):
    change(doj_inputs, lambda q: q.update(patch))
    with pytest.raises(ValueError):
        invoke(doj_inputs)


@pytest.mark.parametrize('mutation', ['canonical', 'clock', 'summary', 'duplicate_body'])
def test_doj_rebound_wrong_release_cannot_qualify(doj_inputs, mutation):
    p = doj_inputs['release_path']
    text = p.read_text()
    if mutation == 'canonical':
        text = text.replace('rel="canonical"', 'rel="alternate"')
    elif mutation == 'clock':
        text = text.replace('2026-10-13T12:00:00Z', '2026-10-12T12:00:00Z')
    elif mutation == 'summary':
        text = text.replace('$315 million', '$316 million')
    else:
        text += '<div class="node-body"><div class="field_body">ambiguous</div></div>'
    p.write_text(text)
    change(doj_inputs, lambda q: q.update(release_sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    with pytest.raises(ValueError, match='DOJ'):
        invoke(doj_inputs)


def test_doj_candidate_alone_refuses_before_checkpoint_or_provider(doj_inputs, monkeypatch):
    from datetime import datetime
    from engine.press import desk_planner as P
    from scripts import stage_official_feed_press as S

    def forbidden(*args, **kwargs):
        pytest.fail('a third-party source cannot reach the provider')

    monkeypatch.setattr(S.writer, 'write', forbidden)
    root = doj_inputs['root']
    before = {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    kwargs = {k: v for k, v in doj_inputs.items() if k not in ('root', 'as_of')}
    r = S.stage_official_feed_candidate(root, P.load_config(root),
        now=datetime.fromisoformat(doj_inputs['as_of']), **kwargs)
    assert r['staged'] is False and r['public_article_approved'] is False
    assert 'first-party' in r['reason']
    assert before == {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()}

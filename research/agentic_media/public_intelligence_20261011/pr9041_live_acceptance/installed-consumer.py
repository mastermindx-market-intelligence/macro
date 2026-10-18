"""Installed consumer acceptance using isolated historical fixtures; no publication."""
import copy,datetime,hashlib,json,pathlib,subprocess,sys,tempfile
root=pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0,str(root))
from engine.press import desk_planner as P
from engine.whitehouse_feed import _slug_id
from tests import press_fixtures as F
expected="89a9ae3b591a569e10cfd2146dcfe7d8565728d68369d80ade723c7a1081f197"
assert hashlib.sha256((root/'engine/press/external_candidate.py').read_bytes()).hexdigest()==expected
head=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
def snapshot():
    paths=[root/'config/press.yml',root/'engine/press/external_candidate.py',*sorted((root/'data/press/staging').glob('*.json')),*sorted((root/'content/seo/blog').glob('*.md'))]
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}
before=snapshot();accepted=[];rejected=[]
with tempfile.TemporaryDirectory(prefix='mmx-press-installed-acceptance-') as d:
    tmp=pathlib.Path(d);fixture=F.fixture_root(tmp/'root');(fixture/'site/stocks').mkdir(parents=True,exist_ok=True);(fixture/'site/stocks/NVDA.html').write_text('<html>NVIDIA</html>')
    evidence=root/'research/agentic_media/public_intelligence_20261011'
    original_doc=json.loads((evidence/'sources/whitehouse_science_retained_document.json').read_text())
    original_q=json.loads((evidence/'whitehouse_event_source_receipt.json').read_text())
    policy=tmp/'policy.txt';policy.write_bytes((evidence/'sources/whitehouse_copyright_20261011.txt').read_bytes())
    def invoke(route='fact-sheets',change=None,as_of='2026-10-11T23:00:00Z'):
        doc=copy.deepcopy(original_doc);q=copy.deepcopy(original_q)
        doc['url']=doc['url'].replace('/fact-sheets/', '/'+route+'/');doc['section']='news';doc['id']=_slug_id(doc['url'],doc['published'])
        q['existing_feed_ingress']['candidate'].update({k:doc[k] for k in ('id','guid','title','url','published','section')})
        q['existing_feed_ingress']['url']='https://www.whitehouse.gov/news/feed/';q['external_planning']['feed_url']='https://www.whitehouse.gov/news/feed/'
        if change:change(doc,q)
        dp=tmp/'doc.json';dp.write_text(json.dumps(doc,sort_keys=True)+'\n');dh=hashlib.sha256(dp.read_bytes()).hexdigest();q['external_planning']['document_sha256']=dh
        qp=tmp/'q.json';qp.write_text(json.dumps(q,sort_keys=True)+'\n');qh=hashlib.sha256(qp.read_bytes()).hexdigest()
        return P.plan_external_candidate(document_path=dp,document_sha256=dh,qualification_path=qp,qualification_sha256=qh,policy_path=policy,as_of=as_of,root=fixture)
    for route in ('fact-sheets','research'):
        r=invoke(route)
        assert r['operation']=='planning_only' and r['allow_stage'] is r['allow_emit'] is r['publication_approved'] is False and not r['cadence_consumed']
        assert r['validation_context']['allowed_links']==['https://www.mastermind-x.com/stocks/NVDA.html']
        assert r['validation_context']['facts'][-1]['values']==['62.5']
        accepted.append(route)
    controls=[('unknown-route',dict(route='administration')),('expired-event',dict(as_of='2026-10-12T00:00:00Z')),('rights',dict(change=lambda d,q:q['rights_basis'].update(qualification='unqualified'))),('feed',dict(change=lambda d,q:q['external_planning'].update(feed_url='https://www.whitehouse.gov/fact-sheets/feed/'))),('body',dict(change=lambda d,q:d.update(body=d['body']+' changed')))]
    for name,kwargs in controls:
        try:invoke(**kwargs)
        except ValueError as e:rejected.append({'control':name,'error':str(e)})
        else:raise AssertionError('Negative control accepted: '+name)
    assert not list((fixture/'data/press/staging').glob('*.json'))
after=snapshot();end=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
assert before==after and head==end
print(json.dumps({'schema':'press.aggregate_installed_consumer.v1','observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'head':head,'head_after':end,'source_sha256':expected,'positive_historical_fixture_routes':accepted,'negative_controls':rejected,'runtime_inputs_unchanged':True,'staging_writes':0,'provider_calls':0,'publication_approved':False,'qualification_scope':'Synthetic historical consumer controls only, not admission of a current story','accepted':True},indent=2))

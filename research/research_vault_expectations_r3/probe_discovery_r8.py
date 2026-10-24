"""Research-only characterization of pinned corpus and selected existing route/client.

No acquisition, live application, provider, credentials, source repair or production writes.
Expected product gaps are RECORDED, not fixed or passed as product acceptance.
"""
from __future__ import annotations
import argparse, ast, hashlib, importlib.util, json, logging, platform
import sqlite3, subprocess, tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PIN='e86cf4593d2c2603a695ccab858f98ac4a29abae'
CORPUS_BLOB='0b035b34489a4efd2ae7a3c59d153b3d1977701a'

def git_blob(b: bytes) -> str:
    return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()

def verified_corpus(p: Path):
    raw=p.read_bytes()
    if git_blob(raw)!=CORPUS_BLOB: raise ValueError('Pinned upstream corpus blob mismatch')
    spec=importlib.util.spec_from_file_location('rv_r8_pinned_corpus',p)
    assert spec and spec.loader
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

class FixtureHTTPException(Exception): pass

def route_from_excerpt(path: Path, corpus, conn_factory, admitted, *, pro=True, preview=(), catalog_error=False):
    tree=ast.parse(path.read_text(encoding='utf-8'))
    fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='research_search')
    fn.decorator_list=[]  # No FastAPI mounting. All call arguments are passed explicitly.
    def ids():
        if catalog_error: raise FixtureHTTPException('Fixture catalog unavailable')
        return set(admitted)
    scope={'Any':Any,'Query':lambda value,*a,**kw:value,'Header':lambda default=None,**kw:default,
        '_Q_MAX':512,'_FACET_MAX':200,'_SEARCH_LIMIT_DEFAULT':50,'_SEARCH_LIMIT_MAX':50,
        'HTTPException':FixtureHTTPException,'_catalog_ids':ids,'_corpus_conn':conn_factory,
        'corpus_mod':corpus,'log':logging.getLogger('r8'),
        '_can_view':lambda tier:pro,'_optional_tier':lambda authorization:'fixture',
        '_catalog_preview':lambda catalog:{'items':[{'id':i} for i in preview]},'_load_catalog':lambda:{}}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),str(path),'exec'),scope)
    def call(q,limit=50):
        return scope['research_search'](q=q,institution='',from_='',to='',limit=limit,authorization=None)
    return call

def main() -> int:
    a=argparse.ArgumentParser()
    a.add_argument('--corpus',type=Path)
    a.add_argument('--output-dir',type=Path)
    args=a.parse_args();root=Path(__file__).resolve().parent
    out=args.output_dir or Path(tempfile.mkdtemp(prefix='rv-r8-results-'))
    out.mkdir(parents=True,exist_ok=True)
    corpus_path=args.corpus or (root/'upstream/corpus.py' if (root/'upstream/corpus.py').is_file()
                              else root.parents[1]/'engine/research_vault/corpus.py')
    corpus=verified_corpus(corpus_path)
    route_path=root/'r8_fragments/research_search.py.txt'
    results=[]; responses={}
    def record(i,kind,q,expected,actual,**facts):
        results.append({'id':i,'class':kind,'question':q,'expected':expected,'actual':actual,
                        'requirement_met':expected==actual,**facts})
    def seed(p,rows):
        c=corpus.open_db(p)
        for i,title,body,extras in rows:
            corpus.upsert(c,{'id':i,'title':title,'summary_points':[], 'institution':'Fixture Desk',
                    'side':'sell','published_at':'2026-09-15T00:00:00Z',**extras},body)
        c.close()
    def connect(p):
        c=sqlite3.connect(str(p));c.row_factory=sqlite3.Row;return c
    with tempfile.TemporaryDirectory(prefix='rv-r8-fixture-') as td:
        p=Path(td)/'main.sqlite'
        seed(p,[('metadata-only','Equipment outlook','Order trends stabilized.',{'tickers':['ACMEQ']}),
                ('literal','LITERALQ outlook','Investment discussion.',{}),
                ('body-hit','Business review','BODYQ investment guidance.',{})])
        all_ids={'metadata-only','literal','body-hit'}
        api=route_from_excerpt(route_path,corpus,lambda:connect(p),all_ids)
        responses['metadata_only']=api('ACMEQ')
        record('R8-C1','control','Literal title retrieval works',['literal'],[x['id'] for x in api('LITERALQ')['items']])
        record('R8-C2','control','Literal body retrieval works',['body-hit'],[x['id'] for x in api('BODYQ')['items']])
        responses['healthy_empty']=api('NOHITQ')
        record('R8-C3','control','Healthy no-match is available and empty',{'items':[],'count':0,'available':True},responses['healthy_empty'])
        responses['no_connection']=route_from_excerpt(route_path,corpus,lambda:None,all_ids)('LITERALQ')
        record('R8-C4','control','Missing connection is marked unavailable',False,responses['no_connection']['available'])
        c=connect(p)
        stored=dict(c.execute("SELECT title,summary,body FROM documents WHERE doc_id='metadata-only'").fetchone());c.close()
        record('R8-C8','control','Metadata input does not mutate literal source columns',
               {'title':'Equipment outlook','summary':'','body':'Order trends stabilized.'},stored)
        q=Path(td)/'broken.sqlite';seed(q,[('literal','LITERALQ outlook','',{})])
        c=connect(q);c.execute('DROP TABLE documents_fts');c.commit();c.close()
        broken=route_from_excerpt(route_path,corpus,lambda:connect(q),{'literal'})('LITERALQ')
        responses['broken_fts']=broken
        record('R8-G2','gap','Missing FTS table must not be a valid empty search',False,broken['available'],response=broken)
        q=Path(td)/'limit.sqlite';seed(q,[('ahead-a','ACMEQ ACMEQ ACMEQ','',{}),
            ('ahead-b','ACMEQ ACMEQ','',{}),('allowed-report','Business report','ACMEQ '+('filler '*500),{})])
        c=connect(q);raw=corpus.search(c,'ACMEQ',limit=50);c.close()
        final=route_from_excerpt(route_path,corpus,lambda:connect(q),{'allowed-report'})('ACMEQ',limit=1)
        record('R8-G4','gap','Catalog-eligible match survives final result limit',['allowed-report'],
              [x['id'] for x in final['items']],raw_order=[x['id'] for x in raw],response=final)
        record('R8-C9','control','Non-admitted IDs remain undisclosed',True,
               all(x['id']=='allowed-report' for x in final['items']))
        preview=route_from_excerpt(route_path,corpus,lambda:connect(p),all_ids,pro=False,preview=('literal',))('BODYQ')
        record('R8-C10','control','Controlled non-Pro preview excludes non-preview result',[],preview['items'])
        caterr=route_from_excerpt(route_path,corpus,lambda:connect(p),all_ids,catalog_error=True)('BODYQ')
        record('R8-C11','control','Catalog unavailable refuses search',False,caterr['available'])
    (out/'backend_responses.json').write_text(json.dumps(responses,indent=2)+'\n')
    js=subprocess.run(['node',str(root/'probe_client_r8.js'),str(root/'r8_fragments/search_client.js.txt'),str(out/'backend_responses.json')],
                      capture_output=True,text=True,timeout=10,check=True)
    client=json.loads(js.stdout);results.extend(client['cases']);results.sort(key=lambda x:x['id'])
    receipt={'schema':'research.discovery_boundary_assay.r8','executed_at_utc':datetime.now(timezone.utc).isoformat(),
       'source_commit':PIN,'python':platform.python_version(),'sqlite':sqlite3.sqlite_version,'node':client['runtime'],
       'source_verification':{'corpus_full_git_blob':git_blob(corpus_path.read_bytes()),
           'corpus_full_blob_matches':True,'api_client':'Connector-range copies; whole-file parity NOT claimed',
           'api_expected_full_blob':'bca9b965057df653607765107ef789692c47dcdc',
           'client_expected_full_blob':'1f0b673da6c3d6a44ad3d74b2994f70b9a4311c8'},
       'scope':'Actual pinned corpus on synthetic SQLite/FTS5; selected route/client functions with controlled auth/catalog/network/time/UI; no live service',
       'counts':{'cases':len(results),'controls':sum(x['class']=='control' for x in results),
           'controls_met':sum(x['class']=='control' and x['requirement_met'] for x in results),
           'product_gaps_reproduced':sum(x['class']=='gap' and not x['requirement_met'] for x in results)},
       'cases':results,'production_repairs':0,'real_reports_processed':0,'browser_journeys':0,
       'artifacts':{('pinned_corpus.py' if p==corpus_path else str(p.relative_to(root))):hashlib.sha256(p.read_bytes()).hexdigest() for p in [
           corpus_path,route_path,root/'r8_fragments/search_client.js.txt',root/'probe_client_r8.js',Path(__file__)]}}
    (out/'verification_r8.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'counts':receipt['counts'],'cases':[(x['id'],x['requirement_met']) for x in results],
          'receipt':str(out/'verification_r8.json')},indent=2))
    # Exit 0 means characterization complete, never product acceptance.
    if any(not x['requirement_met'] for x in results if x['class']=='control'): return 2
    if receipt['counts']['product_gaps_reproduced']!=5:return 3
    return 0

if __name__=='__main__':raise SystemExit(main())

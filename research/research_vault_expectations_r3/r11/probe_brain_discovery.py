"""Read-only research diagnostic: selected Brain search semantics versus corpus.

No production modules are patched, no provider/auth/source calls are made, and all
report contents are synthetic. The Brain slice is a disclosed transcription;
the complete corpus dependency is verified by its existing Git blob before import.
"""
from __future__ import annotations
import argparse, datetime, hashlib, importlib.util, json, pathlib, sqlite3, sys, tempfile

ROOT=pathlib.Path(__file__).resolve().parents[1]
CORPUS_BLOB='0b035b34489a4efd2ae7a3c59d153b3d1977701a'
NOW=datetime.datetime(2026,9,16,10,0,tzinfo=datetime.timezone.utc)

def blob(b):
    return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--corpus',type=pathlib.Path,default=ROOT/'upstream/corpus.py')
    ap.add_argument('--output',type=pathlib.Path,required=True)
    args=ap.parse_args()
    b=args.corpus.read_bytes()
    if blob(b)!=CORPUS_BLOB:raise ValueError('Refuse an unqualified corpus revision')
    spec=importlib.util.spec_from_file_location('qualified_corpus_r11',args.corpus)
    corpus=importlib.util.module_from_spec(spec);spec.loader.exec_module(corpus)
    slice_path=ROOT/'r11/brain_search_slice.py.txt';slice_bytes=slice_path.read_bytes()
    ns={'__name__':'selected_brain_search_r11'}
    exec(compile(slice_bytes,str(slice_path),'exec'),ns)
    checks=[]
    with tempfile.TemporaryDirectory(prefix='rv-r11-case-') as tmp:
        root=pathlib.Path(tmp)
        catalog=root/'data/research_vault/catalog.json';catalog.parent.mkdir(parents=True)
        def item(doc_id='one',title='Weekly industry note',points=None,**kw):
            d={'id':doc_id,'title':title,'institution':'Fictional Research House','side':'sell',
               'summary_points':points or ['Industry developments are discussed.'],
               'published_at':'2026-09-15T12:00:00Z','tickers':[],'top_pick':False}
            d.update(kw);return d
        def run(rows,q,body='',corpus_query=None):
            catalog.write_text(json.dumps({'items':rows},ensure_ascii=False),encoding='utf-8')
            result=ns['search_slice'](root,q,now=NOW)
            conn=corpus.open_db(root/'case.sqlite')
            conn.execute('DELETE FROM documents');conn.commit()
            for r in rows:corpus.upsert(conn,r,body)
            hits=corpus.search(conn,corpus_query or q,limit=50);conn.close()
            return result,hits
        def record(key,kind,assertion,**observed):
            if not assertion:raise AssertionError(key)
            checks.append({'id':key,'kind':kind,'observation_confirmed':True,**observed})
        def ids(r):return [x['id'] for x in r['results']]
        def fids(r):return [x['id'] for x in r]
        r,h=run([item(title='Orionquartz covenant update')],'orionquartz covenant')
        record('literal_title','control',ids(r)==['one'],brain_ids=ids(r))
        r,h=run([item()],'orionquartz covenant','The original body discusses the orionquartz covenant.')
        record('body_only_evidence','scope_limit',ids(r)==[] and fids(h)==['one'],brain_ids=ids(r),corpus_ids=fids(h),count_scanned=r['count_scanned'])
        r,h=run([item(tickers=['ACMEQ'])],'ACMEQ')
        record('association_not_discovery','scope_limit',ids(r)==[],brain_ids=ids(r),catalog_association=['ACMEQ'])
        points=['First topic.','Second topic.','Third topic.','Fourth topic.','The orionquartz covenant changed.']
        r,h=run([item(points=points)],'orionquartz covenant')
        shown=json.dumps(r['results'],ensure_ascii=False)
        record('fifth_summary_bullet','projection_limit',ids(r)==['one'] and 'orionquartz' not in shown,brain_ids=ids(r),returned_bullets=len(r['results'][0]['summary_points']),matching_bullet_projected=False)
        long_point='Background information. '*14+'The orionquartz covenant changed.'
        r,h=run([item(points=[long_point])],'orionquartz covenant')
        record('summary_tail','projection_limit',ids(r)==['one'] and 'orionquartz' not in json.dumps(r['results']),brain_ids=ids(r),returned_point_chars=len(r['results'][0]['summary_points'][0]),matching_tail_projected=False)
        r,h=run([item(title='OtherCo margin outlook')],'ACMEQ margin')
        record('query_is_not_subject_filter','scope_limit',ids(r)==['one'],brain_ids=ids(r),missing_subject_token='ACMEQ',matched_shared_word='margin')
        r,h=run([item(title='股票回购政策')],'股票回购')
        record('literal_chinese','control',ids(r)==['one'],brain_ids=ids(r))
        r,h=run([item(title='Share repurchases outlook')],'股票回购')
        record('cross_language_is_not_tokenization','scope_limit',ids(r)==[],brain_ids=ids(r),query_language='Chinese',source_metadata_language='English')
        r,h=run([item(title='Share repurchases outlook')],'share repurchases')
        record('explicit_english_terms','control',ids(r)==['one'],brain_ids=ids(r),translation_automated=False)
        r,h=run([item(title='ACMEQ results')],'ACMEQ')
        record('single_atom_candidate_support','control',ids(r)==['one'],brain_ids=ids(r),candidate_not_deployed=True)
        catalog.unlink();r=ns['search_slice'](root,'orionquartz covenant',now=NOW)
        record('catalog_unavailable','control',r['note']=='research vault unavailable',note=r['note'])
        r,h=run([item()],'orionquartz covenant')
        record('healthy_metadata_no_match','control',r['results']==[] and r['count_scanned']==1 and r['note']!='research vault unavailable',note=r['note'],count_scanned=r['count_scanned'])
        body='padding '*8000+'criticalquartz'
        r,h=run([item()],'criticalquartz',body)
        record('fulltext_prefix_limit','scope_limit',not fids(h) and len(body)>corpus.BODY_MAX_CHARS,corpus_ids=fids(h),input_chars=len(body),stored_cap=corpus.BODY_MAX_CHARS)
        r,h=run([item(doc_id='a'),item(doc_id='b'),item(doc_id='c')],'orionquartz covenant','orionquartz covenant')
        record('count_scanned_scope','scope_limit',r['count_scanned']==3 and not ids(r) and len(h)==3,catalog_rows_scanned=r['count_scanned'],brain_ids=ids(r),corpus_ids=fids(h),pdfs_scanned_by_brain_search=0)
    receipt={
      'schema':'research.brain_discovery_path.r11','executed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'python':sys.version.split()[0],'sqlite':sqlite3.sqlite_version,
      'main_pin':'0d60e2b6a2eb049bcbf00050e689a547e459f3e9',
      'pending_brain_pin':'8271ae320732997be4553957e3e2773d1b9e9f1b',
      'brain_expected_upstream_blob':'376d1045e6187926bea2fd4c83385d140174b817',
      'brain_scope':'Executable transcription of selected search branch/helpers; comments/docstrings omitted, diagnostic function signature; NO full-module byte parity',
      'brain_slice_sha256':hashlib.sha256(slice_bytes).hexdigest(),
      'corpus_full_git_blob':blob(b),'corpus_full_blob_verified':True,
      'scope':'Synthetic locally written metadata and text; actual SQLite/FTS5 and complete pinned corpus; selected Brain search semantics only',
      'checks':checks,'count':len(checks),'control_count':sum(c['kind']=='control' for c in checks),
      'scope_or_projection_limits':sum(c['kind']!='control' for c in checks),
      'product_failures_fixed':0,'full_gateway_executed':False,'real_auth_or_entitlement_executed':False,
      'production_browser_executed':False,'source_pdf_admitted':False,'model_benchmark_executed':False,
      'interpretation':'Completed characterization, not newly passing product features or measured live recall. FTS relevance scores are not investor signals.'}
    if args.output.exists():raise ValueError('Refuse overwrite of existing receipt')
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({k:receipt[k] for k in ('count','control_count','scope_or_projection_limits','executed_at_utc')},indent=2))
if __name__=='__main__':main()

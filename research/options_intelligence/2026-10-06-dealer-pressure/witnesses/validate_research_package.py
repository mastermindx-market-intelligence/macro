"""Validate the delivered research's structure, source links and reproducibility receipt.

This is a package-integrity check. It cannot validate market alpha or source truth.
Run: python3 witnesses/validate_research_package.py
"""
from pathlib import Path
import csv, hashlib, json, re

ROOT=Path(__file__).resolve().parent.parent
def rows(name):
    with (ROOT/name).open(newline='') as f:
        return list(csv.DictReader(f))
def read(name):
    return json.loads((ROOT/name).read_text())

def validate():
    checks=[]
    def require(test,name):
        if not test: raise AssertionError(name)
        checks.append(name)
    reports=sorted(ROOT.glob('[0-9][0-9]_*.md'))
    require([int(x.name[:2]) for x in reports]==list(range(1,21)),'all_20_distinct_commissioned_reports')
    sr=read('SOURCE_REGISTER.json'); ss=sr['sources']; ids={r['id'] for r in ss}
    require(len(ids)==len(ss)==sr['count']==260,'260_unique_source_records')
    require(len({r['url'] for r in ss})==260,'260_distinct_source_URLs')
    for r in ss:
        require(all(str(r.get(k,'')).strip() for k in ['id','title','url','publication_or_version','retrieved_at','evidence_class','access_limit','claim_scope','claim_limit']),'source_fields_'+r['id'])
        require(r['url'].startswith(('https://','http://')),'source_URL_'+r['id'])
    fs=rows('15_FEATURE_HYPOTHESIS_CATALOG.csv')
    require(len(fs)==72 and len(fs[0])==17,'72_features_17_fields')
    require(len({r['feature_id'] for r in fs})==72,'unique_feature_IDs')
    require(fs==read('specs/feature_catalog.json')['features'],'feature_CSV_JSON_equivalence')
    require(len({r['family'] for r in fs})==9,'nine_feature_families')
    data=rows('14_DATA_SOURCE_COST_RIGHTS.csv')
    require(len(data)==37 and len(data[0])==28,'37_data_products_28_fields')
    require(len({r['data_id'] for r in data})==37,'unique_data_IDs')
    cs=rows('CLAIM_EVIDENCE_LEDGER.csv')
    require(len(cs)==168,'168_claim_records')
    require(cs==read('specs/claim_evidence_ledger.json')['claims'],'claim_CSV_JSON_equivalence')
    for name,rr in [('feature',fs),('data',data),('claim',cs)]:
        for n,r in enumerate(rr,1):
            require(all(isinstance(v,str) and v.strip() for v in r.values()),f'{name}_{n}_all_fields_populated')
    for r in cs:
        linked={x.strip() for x in r['source_ids'].split(';')}
        require(bool(linked) and linked<=ids,'claim_sources_'+r['claim_id'])
    for p in ROOT.rglob('*.md'):
        t=p.read_text(); used=set(re.findall(r'\[([A-Z]+\d+)\](?!:)',t)); defs=set(re.findall(r'^\[([A-Z]+\d+)\]:',t,re.M))
        require(used<=ids,'no_unknown_citations_'+p.name)
        require(used<=defs,'all_citations_resolve_'+p.name)
        for dest in re.findall(r'\]\(([^\s)]+)',t):
            if not dest.startswith(('http:','https:','#','mailto:')):
                target=(p.parent/dest.split('#')[0]).resolve()
                require(target.exists() or target.name in {'VALIDATION_RECEIPT.json','FILE_MANIFEST.json'},'relative_link_'+p.name+'_'+dest)
    registration=read('specs/first_slice_registration.template.json')
    require(registration['status']=='PROPOSED_NOT_REGISTERED','registration_is_a_proposal')
    require(not any(registration['authority'].values()),'all_operational_authority_false')
    require(set(registration['required_family_verdicts'])>={'F1','F2','F3'},'three_required_endpoint_verdicts')
    witness=read('witnesses/results.json')
    require(witness['assertion_count']==witness['assertions_passed']==62,'62_synthetic_assertions_recorded_passed')
    require(witness['script_sha256']==hashlib.sha256((ROOT/'witnesses/dealer_pressure_witness.py').read_bytes()).hexdigest(),'synthetic_script_hash_matches_receipt')
    require((ROOT/'witnesses/dealer_pressure_synthetic.png').stat().st_size>100000,'synthetic_figure_present')
    word_count=sum(len(re.findall(r'\S+',re.sub(r'^\[[^\]]+\]:.*$','',p.read_text(),flags=re.M))) for p in reports)
    return {'schema':'mastermind.dealer_pressure.package_validation/v1','status':'PASS','research_date':'2026-10-06','check_count':len(checks),'checks':checks,
            'counts':{'reports':20,'report_words_excluding_reference_definitions':word_count,'features':72,'feature_families':9,'feature_fields':17,'data_products':37,'data_fields':28,'source_records':260,'distinct_source_urls':260,'claim_records':168,'synthetic_assertions':62},
            'source_pins':sr['pins'],'publication_scope':'research/options_intelligence/2026-10-06-dealer-pressure only',
            'market_backtest_executed':False,'empirical_forecast_uplift_established':False,'entitlement_verified':False,'production_or_policy_changed':False,
            'limits':'Checks validate package structure, source-link identity and the existing synthetic receipt; they do not verify external claims, live data or market forecasting performance.'}

if __name__=='__main__':
    result=validate()
    (ROOT/'VALIDATION_RECEIPT.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    manifest=[]
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file() or p.name=='FILE_MANIFEST.json' or '__pycache__' in p.parts: continue
        b=p.read_bytes()
        manifest.append({'path':p.relative_to(ROOT).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob_sha1':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()})
    (ROOT/'FILE_MANIFEST.json').write_text(json.dumps({'schema':'research.file_manifest/v1','self_excluded':True,'files':manifest},indent=2)+'\n')
    print(json.dumps({'status':result['status'],'check_count':result['check_count'],'counts':result['counts'],'manifest_files':len(manifest)},indent=2))

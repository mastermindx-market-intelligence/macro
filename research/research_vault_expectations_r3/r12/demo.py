"""Create and demonstrate the review flow with entirely synthetic originals."""
from pathlib import Path
import argparse, copy, datetime, hashlib, json, sqlite3
from fixtures import load_corpus, make_source, populate, catalog_item
from bridge import discover, read_selected

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output-dir',type=Path,required=True);a=ap.parse_args()
    if a.output_dir.exists():raise ValueError('Refuse existing demo directory')
    root=a.output_dir;root.mkdir(parents=True)
    original=root/'synthetic_original.pdf';corrected=root/'synthetic_corrected.pdf'
    before=make_source(original);after=make_source(corrected,29)
    (root/'extracted_original.txt').write_text(before['body'])
    corpus=load_corpus();item=catalog_item();db=root/'corpus.sqlite'
    populate(corpus,db,item,before)
    scope={'decision':'allowed','generation':'fixture-g1','items':{item['id']:{'catalog':item,
        'pdf_sha256':before['pdf_sha256'],'body_sha256':before['body_sha256']}}}
    source_path=original;meter_calls=[]
    def admit(purpose):return copy.deepcopy(scope)
    def connect():
        c=sqlite3.connect(db);c.row_factory=sqlite3.Row;return c
    def source(rid):return source_path.read_bytes()
    def meter(rid):meter_calls.append(rid);return True
    args={'query':'orionquartz margin','scope':'source_text','corpus':corpus,
          'scope_provider':admit,'connection_factory':connect}
    found=discover(**args);selection=found['items'][0]['selection']
    kwargs={'corpus':corpus,'scope_provider':admit,'connection_factory':connect,'source_reader':source,'meter':meter}
    evidence=read_selected(selection=selection,**kwargs)
    assert evidence['status']=='matched' and evidence['passages'][0]['locator']['page']==2
    assert '31% to 28%' in evidence['passages'][0]['text']
    assert evidence['source_binding']['content_sha256']==hashlib.sha256(original.read_bytes()).hexdigest()
    populate(corpus,db,item,after);source_path=corrected
    scope['generation']='fixture-g2';scope['items'][item['id']].update(pdf_sha256=after['pdf_sha256'],body_sha256=after['body_sha256'])
    stale=read_selected(selection=selection,**kwargs)
    assert stale['status']=='selection_stale' and len(meter_calls)==1
    new=discover(**args);updated=read_selected(selection=new['items'][0]['selection'],**kwargs)
    assert updated['status']=='matched' and '31% to 29%' in updated['passages'][0]['text']
    assert len(meter_calls)==2
    report={'schema':'research.source_discovery_demo.r12','executed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'all_source_material_synthetic':True,'scope_and_accounting_adapters':'controlled fixtures, NOT authentic runtime services',
        'catalog':item,'original_pdf_sha256':before['pdf_sha256'],'extracted_body_sha256':before['body_sha256'],
        'discovery':found,'initial_evidence':evidence,'old_selection_after_change':stale,
        'updated_evidence':updated,'meter_callback_calls':len(meter_calls),
        'real_brain_gateway_executed':False,'real_pdf_extraction_executed':True,
        'incumbent_find_evidence_passages_executed':True,'authenticated_browser_proof':False,
        'correction_publisher':'fixture changed via existing corpus upsert, not real sidecar propagation'}
    (root/'demo_result.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    (root/'ANSWER_PREVIEW.md').write_text(
        '# Synthetic source-discovery demonstration\n\n'
        '**Not real institutional research, an LLM answer, or a deployed Brain feature.**\n\n'
        'Question: What does the captured report say about the Orionquartz margin outlook?\n\n'
        'The catalog title and summary do not contain the queried company or metric. '
        'The proposed source-text discovery returns the report ID without disclosing body text. '
        'The subsequent authorized-fixture read uses the incumbent passage selector and returns this literal source support on page 2:\n\n'
        '> Orionquartz margin outlook for FY2027 is revised from 31% to 28%.\n\n'
        'The selected passage also retains the fictional reason and condition. No investment conclusion is inferred.\n\n'
        f'Original PDF SHA256: `{before["pdf_sha256"]}`\n\n'
        f'Extracted-text SHA256: `{before["body_sha256"]}`\n\n'
        'After the fixture source owner publishes the corrected version, the old selection is refused before accounting. '
        'A fresh discovery reads the new literal value, 29%, from the corrected PDF. '
        'Two successful fixture reads invoke the accounting stand-in twice; the stale attempt does not. '
        'No commercial entitlement, quota policy, automated extraction interpretation, or production release was proven.\n')
    print(json.dumps({'status':'DEMO_PASS','page':2,'old_selection_status':stale['status'],
                      'meter_callback_calls':len(meter_calls),'output_dir':str(root)},indent=2))
if __name__=='__main__':main()

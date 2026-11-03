"""Fault injection against the native single-pass issuer read. No source edits."""
from pathlib import Path
import ast
import hashlib
import json
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from engine.company_intelligence import issuer_disclosure_selection as native_selection
from tests import test_gmi_issuer_economic_context as tests


def main():
    path=ROOT/'engine/company_intelligence/issuer_disclosure_selection.py'
    source=path.read_text();before=hashlib.sha256(path.read_bytes()).hexdigest()
    node=next(x for x in ast.parse(source).body if isinstance(x,ast.FunctionDef)
              and x.name=='read_issuer_disclosure_bundle')
    body='\n'.join(source.splitlines()[node.lineno-1:node.end_lineno])+'\n'
    def single():return tests.issuer_case.__wrapped__(tests.sample.__wrapped__())
    def multi():return tests.multi_case.__wrapped__(single())
    def field_gate():tests.test_later_selected_fact_missing_grant_prevents_all_artifact_io(multi())
    def selection_check():tests.test_selection_change_after_fact_read_withholds_everything(single())
    def admission_check():tests.test_final_last_admission_recheck_withholds_whole_batch(multi())
    def duplicates():
        from pytest import MonkeyPatch
        with MonkeyPatch.context() as monkeypatch:
            tests.test_issuer_reads_each_fact_once_and_matches_legacy_io(single(),monkeypatch)
    mutations=[
      ('missing_pre_io_field_restriction',
       'native._require(required_fields <= admission.allowed_fields, "PROJECTION_FIELDS_NOT_ADMITTED")','pass',field_gate),
      ('missing_final_selection_check',
       'native._require(_resolve(owner, issuer_id, purpose, audience) == snapshot, "SELECTION_CHANGED")','pass',selection_check),
      ('missing_final_admission_check',
       'native._require(native.preflight(authority, req) == admission, "SELECTION_ADMISSION_CHANGED")','pass',admission_check),
      ('duplicate_native_fact_read',
       'completed_reads.append(SelectedDisclosureRead(req, admission, result))',
       'native.read_disclosure(store, authority, req, expected_admission=admission); completed_reads.append(SelectedDisclosureRead(req, admission, result))',duplicates),
    ]
    rows=[]
    for name,old,new,check in mutations:
        check()
        if body.count(old)!=1:raise AssertionError('PREIMAGE_CHANGED:'+name)
        namespace=dict(vars(native_selection))
        exec(compile(body.replace(old,new,1),name,'exec'),namespace)
        with patch.object(native_selection,'read_issuer_disclosure_bundle',namespace['read_issuer_disclosure_bundle']):
            try:check()
            except AssertionError:rows.append({'mutation':name,'control':'passed','fault':'detected'})
            else:raise AssertionError('UNDETECTED:'+name)
    if hashlib.sha256(path.read_bytes()).hexdigest()!=before:raise AssertionError('SOURCE_CHANGED')
    print(json.dumps({'scope':'isolated_in_memory_fault_injection','source_sha256':before,
                     'source_unchanged':True,'results':rows},indent=2))


if __name__=='__main__':main()

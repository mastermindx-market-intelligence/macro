import hashlib
from copy import deepcopy
import pytest
from engine.research_intelligence.schema import SCHEMA
from engine.research_intelligence.projection import compare_grounded_claims


def sha(x):return hashlib.sha256(x.encode()).hexdigest()


def pair(statement='Demand rises.', body=None, report='r', institution='Bank', pdf='a'*64):
    text=body or statement
    doc=dict(id=report,source_type='institutional_research',source_name='Fixture',institution=institution,desk='',title='Fixture',published_at='2026-10-01',content_sha256=sha(text))
    analysis=dict(thesis=dict(summary='Development synthesis about demand conditions.',direction='unclear',mechanism=[],conviction='',support_claim_indices=[0]),
                  assumptions=[],forecasts=[],catalysts=[],falsifiers=[],counterarguments=[],implications=[],uncertainties=[],
                  belief_delta=dict(statement='',support_claim_indices=[]),consensus_relation=dict(statement='',support_claim_indices=[]))
    rio=dict(schema=SCHEMA,document=doc,claims=[dict(statement=statement,evidence=[dict(quote_span=statement)],numbers=[],entities=[],horizon='2027',explicit=True)],analysis=analysis,authority='descriptive_research_only')
    src=dict(report_id=report,source_pdf_sha256=pdf,extracted_text_sha256=sha(text),text=text,family_id='family')
    return rio,src


BASIS=dict(subject='demand',horizon='2027',units='percent',currency='USD',scenario='base')


def compare(a,b,**kw):
    return compare_grounded_claims(a[0],b[0],left_source=a[1],right_source=b[1],left_claim_index=0,right_claim_index=0,left_basis=BASIS,right_basis=kw.pop('right_basis',BASIS),**kw)


def test_two_exact_sources_bound_to_literal_byte_spans():
    a=pair(body='中文 preface. Demand rises.');b=pair('Demand falls.',report='b',institution='Other',pdf='b'*64)
    got=compare(a,b)
    assert got['relation']=='DIFFERING_SOURCE_STATEMENTS'
    assert got['authority']=='descriptive_research_only'
    span=got['left']['evidence'][0]
    assert a[1]['text'].encode()[span['start_byte']:span['end_byte']]==span['text'].encode()
    assert got['revision_relation']=='UNCLASSIFIED'


def test_horizon_unit_currency_scenario_or_subject_mismatch_is_not_conflict():
    a=pair();b=pair('Demand falls.',report='b')
    for axis in ('units','currency','subject','scenario'):
        got=compare(a,b,right_basis={**BASIS,axis:'different'})
        assert got['relation']=='UNQUALIFIED_BASIS' and axis in got['basis_mismatches']
    b[0]['claims'][0]['horizon']='2028'
    got=compare(a,b,right_basis={**BASIS,'horizon':'2028'})
    assert not got['comparable']
    with pytest.raises(ValueError,match='horizon'):compare(a,b)


def test_fabricated_summary_cannot_replace_actual_source_claim():
    a=pair();b=pair('Demand falls.',report='b')
    b[1]['text']='Nothing supports the claim.';b[1]['extracted_text_sha256']=sha(b[1]['text']);b[0]['document']['content_sha256']=b[1]['extracted_text_sha256']
    with pytest.raises(ValueError,match='literal'):compare(a,b)
    a=pair();a[1]['extracted_text_sha256']='f'*64
    with pytest.raises(ValueError,match='identity'):compare(a,pair())


def test_identical_report_and_identical_extraction_are_distinguished():
    assert compare(pair(),pair())['revision_relation']=='SAME_SOURCE_REVISION'
    assert compare(pair(),pair(report='b'))['revision_relation']=='IDENTICAL_REPORT_REISSUE'
    assert compare(pair(),pair(report='b',pdf='b'*64))['revision_relation']=='IDENTICAL_EXTRACTED_TEXT'
    a=pair();b=pair(report='b',institution='Other')
    assert compare(a,b)['revision_relation']=='UNCLASSIFIED'


def test_corrected_error_and_changed_view_require_explicit_grounded_support():
    a=pair()
    correction='Correction: the prior demand estimate was an error.'
    b=pair('Demand falls.',body='Demand falls. '+correction,report='b',pdf='b'*64)
    got=compare(a,b,revision_annotation=dict(kind='CORRECTED_FACTUAL_ERROR',support_quote=correction))
    assert got['revision_relation']=='CORRECTED_FACTUAL_ERROR' and got['revision_support']
    view='We lowered our demand forecast.'
    b=pair('Demand falls.',body='Demand falls. '+view,report='b',pdf='b'*64)
    assert compare(a,b,revision_annotation=dict(kind='CHANGED_VIEW',support_quote=view))['revision_relation']=='CHANGED_VIEW'
    for quote in ('Demand falls.','Correction: fabricated source claim.'):
        with pytest.raises(ValueError):compare(a,b,revision_annotation=dict(kind='CORRECTED_FACTUAL_ERROR',support_quote=quote))

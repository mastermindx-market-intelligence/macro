import copy
import json
import pytest
from review_projection import ReviewProjectionError, project_relationship_review, attach_relationship_review


def row(**change):
    r = dict(id='filing-related', ticker='FIX-B', company='Example related registrant',
             status='defer', category=None, stage=None, llm_category='Going-Private',
             llm_role='none', role='none', date_filed='2026-09-25',
             source_url='https://example.invalid/filing', summary='A parent transaction is discussed.',
             llm_terms={'cash_per_share': '99'}, arb={'spread': .4})
    r.update(change)
    return r


def payload():
    return dict(scored=False, is_context_only=True,
                situations=[dict(id='filing-direct', ticker='FIX-A', category='Going-Private')],
                counts={'Going-Private': 1},
                coverage={'events_total': 3, 'classified': 1, 'deferred_to_text_lane': 2})


def project(records=None, **kw):
    return project_relationship_review([row()] if records is None else records, as_of='2026-09-27', **kw)


def test_related_source_survives():
    assert project()['records'][0]['source_record_id'] == 'filing-related'


def test_source_text_kept_as_text():
    assert project([row(summary='<script>alert(1)</script>')])['records'][0]['source_summary'] == '<script>alert(1)</script>'


def test_no_economic_promotion():
    r=project()['records'][0]
    assert r['direct_target_eligible'] is False and r['affected_relationship_confirmed'] is False
    assert r['can_rank'] is False and r['relation_status']=='unqualified'
    assert not ({'arb','llm_terms','deal_terms','spread','probability','target_price'} & r.keys())


def test_reason_names_relationship_not_text():
    assert project()['records'][0]['reason']=='registrant_target_not_established'


@pytest.mark.parametrize('role', [None, '', ' NONE ', 'issuer', 'buyer', 'unknown'])
def test_non_target_roles_retained(role):
    assert project([row(llm_role=role)])['total_records']==1


@pytest.mark.parametrize('role', ['target', ' TARGET '])
def test_explicit_target_not_in_review(role):
    assert project([row(llm_role=role)])['total_records']==0


@pytest.mark.parametrize('change', [{'status':'skip'}, {'llm_category':'Acquisitions'}, {'llm_category':None}])
def test_other_rows_not_reinterpreted(change):
    assert project([row(**change)])['total_records']==0


def test_copied_role_does_not_override_source_annotation():
    assert project([row(role='target',llm_role='none')])['total_records']==1


def test_bound_count_not_shown_count():
    out=project([row(id='b'),row(id='a')],limit=1)
    assert out['total_records']==2 and out['shown_records']==1 and out['truncated']
    assert out['records'][0]['source_record_id']=='a'


def test_no_ticker_level_collapse():
    assert project([row(id='a'),row(id='b')])['total_records']==2


@pytest.mark.parametrize('url',['javascript:alert(1)','data:text/html,bad','https://user:pass@example.invalid/a','https://example.invalid/\nbad',None])
def test_unusable_source_link_does_not_erase_record(url):
    out=project([row(source_url=url)])
    assert out['total_records']==1 and out['records'][0]['source_url'] is None


def test_json_nulls_for_display_missingness():
    out=project([row(ticker=float('nan'),company=None,summary=float('nan'))])
    assert out['records'][0]['display_ticker'] is None
    assert json.loads(json.dumps(out,allow_nan=False)) == out


def test_future_source_refused():
    with pytest.raises(ReviewProjectionError,match='future_source_date'): project([row(date_filed='2026-09-28')])


def test_unknown_source_date_preserved():
    assert project([row(date_filed=None)])['records'][0]['source_date'] is None


@pytest.mark.parametrize('limit',[0,-1,201,True,1.5])
def test_invalid_limit(limit):
    with pytest.raises(ReviewProjectionError,match='invalid_limit'):project(limit=limit)


def test_missing_source_record_id_is_not_fabricated():
    with pytest.raises(ReviewProjectionError,match='missing_source_record_id'):project([row(id=None)])


def test_originals_unchanged():
    p=payload();rs=[row(),row(id='other',llm_category='Other')];before=copy.deepcopy((p,rs))
    attach_relationship_review(p,rs,as_of='2026-09-27')
    assert (p,rs)==before


def test_coverage_relabel_not_double_count():
    out=attach_relationship_review(payload(),[row(),row(id='other',llm_category='Other')],as_of='2026-09-27')
    assert out['coverage']['deferred_to_text_lane']==1
    assert out['coverage']['relationship_review_records']==1
    assert out['coverage']['events_total']==3 and out['coverage']['classified']==1
    assert out['counts']=={'Going-Private':1} and len(out['situations'])==1


def test_existing_coverage_absence_preserved_for_desk():
    p=payload();p['coverage']={'shown':1,'with_arb':1}
    out=attach_relationship_review(p,[row()],as_of='2026-09-27')
    assert 'deferred_to_text_lane' not in out['coverage']
    assert out['coverage']['shown']==1 and out['coverage']['with_arb']==1


def test_direct_row_leak_refused_not_silently_repaired():
    p=payload();p['situations'].append({'id':'filing-related','category':'Going-Private'})
    with pytest.raises(ReviewProjectionError,match='direct_target_leak'):attach_relationship_review(p,[row()],as_of='2026-09-27')


def test_coverage_underflow_refused():
    p=payload();p['coverage']['deferred_to_text_lane']=0
    with pytest.raises(ReviewProjectionError,match='coverage_mismatch'):attach_relationship_review(p,[row()],as_of='2026-09-27')


@pytest.mark.parametrize('key',['scored','is_context_only'])
def test_authority_boundary(key):
    p=payload();p[key]=not p[key]
    with pytest.raises(ReviewProjectionError,match='context_only_required'):attach_relationship_review(p,[row()],as_of='2026-09-27')


def test_no_stale_append_to_existing_projection():
    p=payload();p['relationship_review']={'records':[{'source_record_id':'stale'}]}
    with pytest.raises(ReviewProjectionError,match='fresh_payload_required'):
        attach_relationship_review(p,[row()],as_of='2026-09-27')


def test_duplicate_record_id_refused_not_double_counted():
    with pytest.raises(ReviewProjectionError,match='duplicate_source_record_id'):
        project([row(),row()])


def test_no_hidden_direct_leak_beyond_display_limit():
    p=payload();p['situations'].append({'id':'z','category':'Going-Private'})
    with pytest.raises(ReviewProjectionError,match='direct_target_leak'):
        attach_relationship_review(p,[row(id='a'),row(id='z')],as_of='2026-09-27',limit=1)


def test_original_unguarded_output_refused():
    with pytest.raises(ReviewProjectionError,match='classification_guard_required'):
        project([row(status='ok',category='Going-Private',stage='live')])


def test_deferred_row_with_direct_fields_refused():
    with pytest.raises(ReviewProjectionError,match='withheld_direct_fields_not_cleared'):
        project([row(category='Going-Private',stage='live')])

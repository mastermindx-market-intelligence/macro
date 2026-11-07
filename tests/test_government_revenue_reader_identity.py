"""P2 reader continuity is bound to actual immutable input and normalized selection."""
import pytest
from fastapi import HTTPException
from app import government_revenue as api


def source(*, version=1, generated_at='2026-10-12T00:00:00Z'):
    return {'schema_version':'government_procurement_workspace.v2', 'bundle_id':'grw2-fixture',
            'as_of':'2026-10-12','known_at':'2026-10-12T00:00:00Z','generated_at':generated_at,
            'events':[{'event_id':'e'+str(i),'record_id':'r'+str(i),'version':version,
                       'kind':'award_change','title_original':'radar', 'primary_ticker':'LMT',
                       'listed_company_impacts':[{'ticker':'LMT'}]} for i in range(3)]}


def test_read_identity_stable_for_assembly_clock_only_and_changes_on_evidence():
    assert api._workspace_read_identity(source()) == api._workspace_read_identity(source(generated_at='2026-10-13T00:00:00Z'))
    assert api._workspace_read_identity(source()) != api._workspace_read_identity(source(version=2))


def test_bound_cursor_is_bounded_and_rejects_cross_input_or_selection():
    binding=api._reader_binding(source(), {'route':'events','q':'radar'})
    cursor=api._encode_bound_workspace_cursor(2,binding=binding)
    assert len(cursor)<=96
    assert api._decode_bound_workspace_cursor(cursor,binding=binding)==2
    for new in [api._reader_binding(source(version=2),{'route':'events','q':'radar'}),api._reader_binding(source(),{'route':'events','q':'missile'})]:
        with pytest.raises(HTTPException) as err:
            api._decode_bound_workspace_cursor(cursor,binding=new)
        assert err.value.status_code==409


def test_workspace_page_returns_immutable_ref_and_refuses_generation_drift(monkeypatch):
    current=[source()]
    monkeypatch.setattr(api,'_load',lambda: {})
    monkeypatch.setattr(api,'_procurement_workspace',lambda _: current[0])
    first=api.workspace(cursor=None,limit=1)
    second=api.workspace(cursor=first['next_cursor'],limit=2)
    assert [e['event_id'] for e in first['events']+second['events']]==['e0','e1','e2']
    assert first['input_refs']==second['input_refs']
    assert first['reader_identity']==second['reader_identity']
    current[0]=source(version=2)
    with pytest.raises(HTTPException) as err:
        api.workspace(cursor=first['next_cursor'],limit=1)
    assert err.value.status_code==409


def test_events_page_query_binding_normalizes_equivalent_inputs(monkeypatch):
    monkeypatch.setattr(api,'_load',lambda: {})
    monkeypatch.setattr(api,'_procurement_workspace',lambda _:source())
    # Direct Python calls must supply FastAPI Query defaults explicitly.
    args=dict(mode='awards',ticker=None,agency_id=None,notice_type=None,evidence_class=None,
              impact=None,deadline='all',scope='all',sort='priority',limit=1)
    first=api.events(q=' RADAR ',cursor=None,**args)
    second=api.events(q='radar',cursor=first['next_cursor'],**args)
    assert second['events'][0]['event_id']=='e1'
    with pytest.raises(HTTPException) as err:
        api.events(q='missile',cursor=first['next_cursor'],**args)
    assert err.value.status_code==409

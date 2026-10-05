"""Controlled publication witnesses; not a natural rights/cohort/UI receipt."""
import ast
import copy
import gzip
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
T = "2026-10-04T09:00:00.123456Z"
OLD = "2026-10-04T08:00:00Z"
LATE = "2026-10-04T10:00:00Z"


def api():
    from engine.theme_graph import selection_cohort_publication as p
    return p


def raw(rows=None, generation="native-process-1"):
    if rows is None:
        rows = [dict(ticker="ROK", featured=True, conviction={"verdict":"owner-late"},
                     entry_signal={"label":"blocked"}, risk_sizing={"units":None}),
                dict(ticker="OTHER", featured=False),
                dict(ticker="LRCX", featured=True, issuer_id="same-issuer",
                     conviction={"verdict":"owner-second"})]
    return json.dumps(dict(buy=rows, as_of="2026-10-03", emit={"pair_id":generation,"at_utc":OLD},
                           w3c_source={"schema":"mastermind.selection_cohort_library_source.v1",
                                       "generation_id":generation,"availability":"VALID","available_at":OLD}),
                      separators=(",", ":"), allow_nan=False).encode()


def controlled_authority(request):
    # An injected controlled OWNER capability; never an actual rights assertion.
    assert request["purpose"] == "selection_cohort_internal_capture"
    assert request["source_sha256"] and request["generation_id"]
    assert request["phase"] in {"capture_write", "pre_read", "read_use"}
    if request["phase"] != "pre_read":
        assert request["ancestry"]
    return True


def publish(tmp_path, data=None, **kwargs):
    return api().publish_us_source(data or raw(), data_dir=tmp_path, finalized_at=T,
                                   authorize_capture=controlled_authority, **kwargs)


def paths(tmp_path, data=None, generation="native-process-1"):
    return api()._paths(tmp_path, "us_today", generation, hashlib.sha256(data or raw()).hexdigest())


def test_existing_owner_finalization_and_both_consumer_seams_are_wired():
    us = (ROOT/"scripts/build_stock_library.py").read_text()
    cn = (ROOT/"scripts/build_china.py").read_text()
    render = (ROOT/"scripts/build_site.py").read_text()
    library = (ROOT/"scripts/build_china_library.py").read_text()
    assert "publish_us_source(" in us, "US has no post-serialization finalization call"
    assert us.index("publish_us_source(") > us.index('wide["emit"] = _PAIR_EMIT_STAMP')
    assert cn.index("publish_cn_source(") > cn.index("stamp_cn_board_since_fail_open(")
    assert cn.index("publish_cn_source(") < cn.index('tmpl = env.get_template("china.html.j2")')
    assert render.count("consume_us_source(") == 2
    assert "_fresh_w3c != vm.get(\"us_selection_cohort_internal\")" in render
    assert library.count("source_handoff(") == 2
    assert "publish_cn_source(" not in library
    for source in (us, cn, render, library):
        ast.parse(source)


def test_full_serialized_order_late_reasons_and_duplicate_issuer_preserved(tmp_path):
    data = raw([dict(ticker="DUP",issuer_id="one",featured=True,conviction={"verdict":"late-replacement"}),
                dict(ticker="DUP",issuer_id="one",featured=True,entry_signal={"label":"blocked"})])
    result = publish(tmp_path, data)
    assert result["status"] == "AVAILABLE"
    selection = result["receipt"]["source_selection"]
    assert [r["original_identity"]["ticker"] for r in selection["rows"]] == ["DUP","DUP"]
    assert selection["rows"][0]["original_reasons"]["conviction"]["verdict"] == "late-replacement"
    assert selection["rows"][1]["original_reasons"]["entry_signal"]["label"] == "blocked"
    assert selection["n_selected"] == 2
    for f in api().FLAGS: assert result[f] is False and result["receipt"][f] is False
    assert result["receipt"]["public_display_allowed"] is False
    assert result["explanation"] is None


def test_current_context_clock_and_retry_do_not_refresh_first_event(tmp_path):
    first=publish(tmp_path)
    later=api().publish_us_source(raw(),data_dir=tmp_path,finalized_at=LATE,authorize_capture=controlled_authority)
    assert later == first
    selection=first["receipt"]["source_selection"]
    assert {selection[k] for k in ["selected_at","effective_at","known_at"]} == {T}
    assert first["receipt"]["source_clocks"]["pair_emitted_at"] == OLD


def test_actual_missing_rights_and_revocation_never_archive_or_promote(tmp_path):
    refused=api().publish_us_source(raw(),data_dir=tmp_path,finalized_at=T)
    assert refused["reason_codes"] == ["CAPTURE_RIGHTS_UNAVAILABLE"]
    assert list(tmp_path.iterdir()) == []
    publish(tmp_path)
    files={p:p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    denied=api().read_finalized_cohort(raw(),market="us_today",generation_id="native-process-1",data_dir=tmp_path,
                                     authorize_capture=lambda request:False)
    assert denied["receipt"] is None and denied["explanation"] is None
    assert {p:p.read_bytes() for p in files} == files


def test_valid_finalized_empty_vs_outage_partial_and_missing(tmp_path):
    empty=publish(tmp_path,raw([],generation="empty"))
    assert empty["status"] == "AVAILABLE" and empty["receipt"]["source_selection"]["n_selected"] == 0
    partial=api().publish_finalized_cohort(raw([],generation="partial"),market="us_today",generation_id="partial",source_ref="fixture://owner",source_schema="fixture/v1",finalized_at=T,data_dir=tmp_path,ancestry=[ancestry()],availability="PARTIAL",authorize_capture=controlled_authority)
    assert partial["receipt"]["source_availability"] == "PARTIAL"
    outage=api().publish_finalized_cohort(raw([]),market="us_today",generation_id="outage",source_ref="fixture://owner",source_schema="fixture/v1",finalized_at=T,data_dir=tmp_path,ancestry=[],availability="OUTAGE",authorize_capture=controlled_authority)
    assert outage["reason_codes"] == ["SOURCE_UNAVAILABLE"]
    missing=api().consume_us_source(b'{}',data_dir=tmp_path)
    assert missing["status"] == "UNAVAILABLE"


@pytest.mark.parametrize('data',[b'{"buy":NaN}',b'{"buy":Infinity}',b'{"buy":[null]}',b'{"buy":"empty"}',b'[]',b'{'])
def test_malformed_and_nonfinite_source_never_writes(tmp_path,data):
    result=api().publish_finalized_cohort(data,market="us_today",generation_id="bad",source_ref="fixture://owner",source_schema="fixture/v1",finalized_at=T,data_dir=tmp_path,ancestry=[ancestry()],authorize_capture=controlled_authority)
    assert result["status"] == "UNAVAILABLE"
    assert not any(tmp_path.rglob('*.v1.json'))


@pytest.mark.parametrize('clock',["2026-10-04","2026-10-04T09:00:00","not-a-clock"])
def test_imprecise_malformed_naive_event_refuses(tmp_path,clock):
    result=api().publish_us_source(raw(),data_dir=tmp_path,finalized_at=clock,authorize_capture=controlled_authority)
    assert result["status"] == "UNAVAILABLE" and list(tmp_path.iterdir()) == []


def ancestry(available_at=OLD):
    return dict(owner="fixture-owner",source_family="fixture-controlled-house",source_ref="fixture://owner",
                sha256="a"*64,generation_id="fixture-owner-native-gen",available_at=available_at)


@pytest.mark.parametrize('clock',[None,LATE,"2026-10-04"])
def test_unknown_future_or_date_only_ancestry_cannot_be_qualified(tmp_path,clock):
    result=api().publish_finalized_cohort(raw(),market="us_today",generation_id="bad",source_ref="fixture://owner",source_schema="fixture/v1",finalized_at=T,data_dir=tmp_path,ancestry=[ancestry(clock)],authorize_capture=controlled_authority)
    assert result["status"] == "UNAVAILABLE" and not any(tmp_path.rglob('*.v1.json'))


@pytest.mark.parametrize('clock',["2026-10-05","2026-10-04T10:00:00Z","2026-10-04T09:00:00"])
def test_future_or_naive_source_clock_is_not_a_query_cutoff(tmp_path,clock):
    result=api().publish_finalized_cohort(raw(),market="us_today",generation_id="future",source_ref="fixture://owner",source_schema="fixture/v1",finalized_at=T,data_dir=tmp_path,ancestry=[ancestry()],source_clocks={"source_at":clock},authorize_capture=controlled_authority)
    assert result["status"] == "UNAVAILABLE"


def test_rok_cat_and_reason_only_generation_collision_preserves_first(tmp_path):
    first=publish(tmp_path)
    sp,rp=paths(tmp_path); original=rp.read_bytes()
    changed=json.loads(raw()); changed['buy'][0]['ticker']='CAT'
    collision=publish(tmp_path,json.dumps(changed).encode())
    assert collision["status"] == "UNAVAILABLE" and rp.read_bytes() == original
    changed=json.loads(raw()); changed['buy'][0]['conviction']['verdict']='same-session-correction'
    assert publish(tmp_path,json.dumps(changed).encode())["status"] == "UNAVAILABLE"
    assert rp.read_bytes() == original
    changed['emit']['pair_id']='actual-new-process'
    changed['w3c_source']['generation_id']='actual-new-process'
    assert publish(tmp_path,json.dumps(changed).encode())["status"] == "AVAILABLE"
    assert first['receipt']['source_selection']['rows'][0]['original_identity']['ticker']=='ROK'


@pytest.mark.parametrize('failure',['missing_source','truncated_source','truncated_receipt','mixed_receipt'])
def test_missing_interrupted_truncated_mixed_pair_is_unavailable(tmp_path,failure):
    publish(tmp_path); sp,rp=paths(tmp_path)
    if failure=='missing_source':sp.unlink()
    elif failure=='truncated_source':sp.write_bytes(sp.read_bytes()[:8])
    elif failure=='truncated_receipt':rp.write_bytes(b'{')
    else:
        receipt=json.loads(rp.read_bytes());receipt['generation_id']='other';rp.write_text(json.dumps(receipt))
    result=api().read_finalized_cohort(raw(),market="us_today",generation_id="native-process-1",data_dir=tmp_path,authorize_capture=controlled_authority)
    assert result['status']=='UNAVAILABLE' and result['explanation'] is None


def test_interrupted_receipt_write_never_claims_success(tmp_path,monkeypatch):
    incumbent=api()._exclusive
    def interrupt(path,data):
        if path.suffix=='.json':raise OSError('controlled receipt interruption')
        incumbent(path,data)
    monkeypatch.setattr(api(),'_exclusive',interrupt)
    result=publish(tmp_path)
    assert result['status']=='UNAVAILABLE'
    assert len(list(tmp_path.rglob('*.json.gz')))==1
    assert not list(tmp_path.rglob('*.v1.json'))


def test_original_projection_is_detached_from_display_mutation(tmp_path):
    result=publish(tmp_path);before=copy.deepcopy(result)
    display=json.loads(raw());display['buy'][0]['conviction']={'display':'attached'}
    assert result==before
    assert api().consume_us_source(raw(),data_dir=tmp_path,authorize_capture=controlled_authority)==result


def cn_documents():
    p=api();handoff=p.source_handoff(generation_id='native-cn-library-1',availability='VALID',available_at=OLD)
    library=dict(buy=[dict(ticker='000001.SZ',conviction={'verdict':'library'}),dict(ticker='000002.SZ')],as_of='2026-10-03',w3c_source=handoff)
    served=copy.deepcopy(library);served['buy'][0]['conviction']={'verdict':'served-per-stock'};served['buy'][0]['board_since']='2026-10-03'
    return json.dumps(library).encode(),json.dumps(served).encode()


def cn_ancestry(served):
    row = json.loads(served)["buy"][0]
    return [{**ancestry(), "row_index": 0,
             "reason_projection_sha256": api().content_sha256({k: row.get(k) for k in api().REASONS})}]


def test_cn_once_after_served_reasons_binds_library_ancestry_and_preserves_order(tmp_path):
    library,served=cn_documents()
    result=api().publish_cn_source(served,library_bytes=library,data_dir=tmp_path,finalized_at=T,reason_ancestry=cn_ancestry(served),authorize_capture=controlled_authority)
    assert result['status']=='AVAILABLE'
    receipt=result['receipt'];rows=receipt['source_selection']['rows']
    assert [r['original_identity']['ticker'] for r in rows]==['000001.SZ','000002.SZ']
    assert rows[0]['original_reasons']['conviction']=={'verdict':'served-per-stock'}
    assert receipt['reason_projection']=='cn-served-reasons/v1'
    assert receipt['ancestry'][0]['sha256']==hashlib.sha256(library).hexdigest()
    assert api().publish_cn_source(served,library_bytes=library,data_dir=tmp_path,finalized_at=LATE,reason_ancestry=[ancestry()],authorize_capture=controlled_authority,fallback=True)==result


def test_cn_fallback_cannot_create_receipt_or_refresh_generation(tmp_path):
    library,served=cn_documents()
    result=api().publish_cn_source(served,library_bytes=library,data_dir=tmp_path,finalized_at=T,reason_ancestry=[ancestry()],authorize_capture=controlled_authority,fallback=True)
    assert result['status']=='UNAVAILABLE' and not list(tmp_path.rglob('*.v1.json'))
    legacy=json.loads(library);legacy.pop('w3c_source')
    assert api().publish_cn_source(served,library_bytes=json.dumps(legacy).encode(),data_dir=tmp_path,finalized_at=T,reason_ancestry=[],authorize_capture=controlled_authority)['status']=='UNAVAILABLE'


def test_cn_mixed_order_outage_and_future_library_are_distinct(tmp_path):
    library,served=cn_documents();doc=json.loads(served);doc['buy'].reverse()
    assert api().publish_cn_source(json.dumps(doc).encode(),library_bytes=library,data_dir=tmp_path,finalized_at=T,reason_ancestry=[],authorize_capture=controlled_authority)['reason_codes']==['SERVED_COHORT_ORDER_MISMATCH']
    for availability,clock in [('OUTAGE',OLD),('VALID',LATE)]:
        lib=json.loads(library);s=json.loads(served)
        h=api().source_handoff(generation_id='bad-cn',availability=availability,available_at=clock)
        lib['w3c_source']=s['w3c_source']=h
        assert api().publish_cn_source(json.dumps(s).encode(),library_bytes=json.dumps(lib).encode(),data_dir=tmp_path,finalized_at=T,reason_ancestry=cn_ancestry(served),authorize_capture=controlled_authority)['status']=='UNAVAILABLE'


def test_qualified_reads_delegate_same_cutoff_coverage_and_neutral_hook(tmp_path):
    # Reuse unchanged incumbent owning fixtures: their qualification rules are NOT copied.
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "w3c_incumbent_fixture_owner", ROOT / "tests/test_theme_graph_selection_cohort.py")
    owner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(owner)
    receipt, member, state = owner.receipt, owner.member, owner.state
    publish(tmp_path)
    def joins(selection):
        ids={};members={}
        for i,row in enumerate(selection['rows']):
            sid=row['selection_id'];base=receipt();base.update(effective_at=T,known_at=T,available_at=OLD)
            binding=dict(selection_id=sid,original_identity_sha256=api().content_sha256(row['original_identity']),selection_sha256=api().content_sha256(selection))
            ids[sid]=dict(**base,**binding,security_id=f'SEC:controlled:{i}',graph_node_ids=[f'co:fixture:{i}'],historical_identity_claim=True)
            ms=[member(i)] if i==0 else []
            members[sid]=dict(**base,**binding,security_id=ids[sid]['security_id'],complete=True,memberships=ms,identity_receipt_ref=ids[sid]['receipt_ref'],identity_receipt_sha256=ids[sid]['receipt_sha256'])
        return dict(identity_reads=ids,membership_reads=members,state_reads={})
    result=api().read_finalized_cohort(raw(),market='us_today',generation_id='native-process-1',data_dir=tmp_path,authorize_capture=controlled_authority,qualified_reads=joins)
    e=result['explanation'];assert e['coverage']['n_selected']==2
    assert len(e['coverage']['no_recorded_membership'])==1 and len(e['coverage']['missing_state'])==1
    assert e['consequence_link']['status']=='UNREGISTERED'
    assert all(e[f] is False for f in api().FLAGS)
    corrected=api().read_finalized_cohort(raw(),market='us_today',generation_id='native-process-1',data_dir=tmp_path,authorize_capture=controlled_authority,qualified_reads=joins,previous_explanation=e)
    assert corrected['explanation']['version']['corrects']==e['explanation_id']
    assert corrected['explanation']['source_selection']==e['source_selection']

def test_capture_strings_registry_labels_and_faults_do_not_authorize(tmp_path):
    for capability in ("ALLOWED", lambda request: "ALLOWED", lambda request: {"allowed": True}):
        result = api().publish_us_source(raw(), data_dir=tmp_path, finalized_at=T,
                                         authorize_capture=capability)
        assert result["status"] == "UNAVAILABLE" and list(tmp_path.iterdir()) == []
    def fault(request):
        raise RuntimeError("controlled incumbent capability outage")
    result = api().publish_us_source(raw(), data_dir=tmp_path, finalized_at=T,
                                     authorize_capture=fault)
    assert result["reason_codes"] == ["CAPTURE_CAPABILITY_UNAVAILABLE"]


def test_cn_missing_or_mismatched_reason_receipt_never_archives(tmp_path):
    library, served = cn_documents()
    for ancestry_rows in ([], [ancestry()], [{**cn_ancestry(served)[0], "reason_projection_sha256": "0"*64}]):
        result = api().publish_cn_source(served, library_bytes=library, data_dir=tmp_path,
            finalized_at=T, reason_ancestry=ancestry_rows, authorize_capture=controlled_authority)
        assert result["status"] == "UNAVAILABLE" and list(tmp_path.iterdir()) == []


def test_cn_fallback_cannot_swap_bound_library_source(tmp_path):
    library, served = cn_documents()
    assert api().publish_cn_source(served, library_bytes=library, data_dir=tmp_path,
        finalized_at=T, reason_ancestry=cn_ancestry(served),
        authorize_capture=controlled_authority)["status"] == "AVAILABLE"
    other = json.loads(library); other["unrelated_actual_source_fact"] = "different"
    result = api().publish_cn_source(served, library_bytes=json.dumps(other).encode(),
        data_dir=tmp_path, finalized_at=LATE, reason_ancestry=[], fallback=True,
        authorize_capture=controlled_authority)
    assert result["reason_codes"] == ["MIXED_LIBRARY_ANCESTRY"]


@pytest.mark.parametrize("field,value", [("source_schema","other-schema"),
    ("market","cn_featured"),("public_display_allowed",True),("can_rank",True)])
def test_fully_rehashed_outer_binding_adversaries_refuse(tmp_path,field,value):
    publish(tmp_path); sp,rp=paths(tmp_path)
    receipt=json.loads(rp.read_bytes());receipt[field]=value
    receipt["receipt_sha256"]=api().content_sha256({k:v for k,v in receipt.items() if k!="receipt_sha256"})
    rp.write_text(json.dumps(receipt))
    result=api().read_finalized_cohort(raw(),market="us_today",generation_id="native-process-1",
        data_dir=tmp_path,authorize_capture=controlled_authority)
    assert result["status"]=="UNAVAILABLE" and result["explanation"] is None


def test_unknown_archive_identity_unreadable_prior_and_source_interruption(tmp_path,monkeypatch):
    result=api().publish_us_source(raw(generation="../foreign"),data_dir=tmp_path,
                                  finalized_at=T,authorize_capture=controlled_authority)
    assert result["status"]=="UNAVAILABLE" and list(tmp_path.iterdir())==[]
    incumbent=api()._exclusive
    def interrupt(path,data):
        if path.suffix==".gz":raise OSError("controlled source interruption")
        incumbent(path,data)
    monkeypatch.setattr(api(),"_exclusive",interrupt)
    assert publish(tmp_path)["status"]=="UNAVAILABLE"
    assert not list(tmp_path.rglob("*.v1.json"))

def test_actual_us_serialize_once_seam_uses_late_rows_and_survives_provenance_failure(tmp_path,monkeypatch):
    import datetime
    from types import SimpleNamespace
    module=ast.parse((ROOT/"scripts/build_stock_library.py").read_text())
    def is_emit(node):
        return isinstance(node,ast.Assign) and ast.unparse(node).startswith("wide['emit'] = _PAIR_EMIT_STAMP")
    def locate(nodes):
        for node in nodes:
            for _,value in ast.iter_fields(node):
                if isinstance(value,list) and value and isinstance(value[0],ast.stmt):
                    for i,child in enumerate(value):
                        if is_emit(child):return value[i:i+5]
                    found=locate(value)
                    if found:return found
        return None
    seam=locate(module.body);assert len(seam)==5
    observed=[]
    def unavailable(raw_bytes,**kw):
        observed.append((raw_bytes,kw))
        raise OSError("controlled GMI provenance outage")
    monkeypatch.setattr(api(),"publish_us_source",unavailable)
    (tmp_path/"factordata").mkdir()
    wide={"buy":[{"ticker":"ROK","featured":True,"conviction":{"verdict":"late-mutated"}}]}
    namespace=dict(wide=wide,_PAIR_EMIT_STAMP={"pair_id":"controlled-native","at_utc":OLD},
        json=json,_json_safe=lambda value:value,site=tmp_path,
        datetime=datetime.datetime,timezone=datetime.timezone,
        config=SimpleNamespace(data_dir=lambda:tmp_path/"internal"),
        log=SimpleNamespace(warning=lambda *args:None,info=lambda *args:None))
    exec(compile(ast.Module(body=seam,type_ignores=[]),"<actual US final write seam>","exec"),namespace)
    actual=(tmp_path/"factordata/us_standouts.json").read_bytes()
    assert len(observed)==1 and observed[0][0]==actual
    assert json.loads(actual)["buy"][0]["conviction"]["verdict"]=="late-mutated"
    assert json.loads(actual)["emit"]["pair_id"]=="controlled-native"
    assert not (tmp_path/"internal").exists()


def test_actual_cn_final_shared_seam_preserves_both_render_vm_and_refuses_no_capability(tmp_path,monkeypatch):
    from types import SimpleNamespace
    module=ast.parse((ROOT/"scripts/build_china.py").read_text())
    target=None
    for node in ast.walk(module):
        if isinstance(node,ast.Try) and any(isinstance(x,ast.ImportFrom) and x.module=="engine.theme_graph.selection_cohort_publication" for x in node.body):
            target=node
    assert target is not None
    library,served=cn_documents()
    (tmp_path/"china_standouts.json").write_bytes(library)
    vm={"setups":json.loads(served),"cn_selection_cohort_internal":None}
    before=copy.deepcopy(vm["setups"]);observed=[]
    incumbent=api().publish_cn_source
    def capture(*args,**kwargs):
        observed.append(kwargs.copy())
        return incumbent(*args,**kwargs)
    monkeypatch.setattr(api(),"publish_cn_source",capture)
    namespace=dict(vm=vm,json=json,factordata=tmp_path,_w3c_cn_fallback=False,
        config=SimpleNamespace(data_dir=lambda:tmp_path/"internal"),
        log=SimpleNamespace(warning=lambda *args:None,info=lambda *args:None))
    exec(compile(ast.Module(body=[target],type_ignores=[]),"<actual CN shared finalization seam>","exec"),namespace)
    assert len(observed)==1 and "authorize_capture" not in observed[0]
    assert vm["setups"]==before and vm["cn_selection_cohort_internal"] is None
    assert not (tmp_path/"internal").exists()

def test_actual_first_and_fresh_us_reader_failures_preserve_board(tmp_path,monkeypatch):
    from types import SimpleNamespace
    module=ast.parse((ROOT/"scripts/build_site.py").read_text())
    def fail(*args,**kwargs):
        raise RuntimeError("controlled missing W3C read capability")
    monkeypatch.setattr(api(),"consume_us_source",fail)
    (tmp_path/"factordata").mkdir()
    (tmp_path/"factordata/us_standouts.json").write_bytes(raw())
    first=None;fresh=None
    for node in ast.walk(module):
        if isinstance(node,ast.If) and ast.unparse(node.test)=="_us.exists()":first=node
        if isinstance(node,ast.Try) and node.body and isinstance(node.body[0],ast.Assign) and ast.unparse(node.body[0]).startswith("_us_path ="):
            fresh=node
    assert first is not None and fresh is not None
    log=SimpleNamespace(warning=lambda *args:None)
    namespace=dict(json=json,site=tmp_path,_us=tmp_path/"factordata/us_standouts.json",
        us_standouts=None,_us_w3c=None,_us_w3c_binding=None,log=log,
        config=SimpleNamespace(data_dir=lambda:tmp_path/"internal"),
        _attach_board_display_chips=lambda site,doc:doc)
    exec(compile(ast.Module(body=[first],type_ignores=[]),"<actual first US source seam>","exec"),namespace)
    assert namespace["us_standouts"]==json.loads(raw()) and namespace["_us_w3c"] is None
    # Narrow actual fresh read/bind/attach prefix, before financial view logic/render.
    prefix=[]
    for node in fresh.body:
        prefix.append(node)
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="_fresh_su" for t in node.targets):break
    exec(compile(ast.Module(body=prefix,type_ignores=[]),"<actual fresh US source seam>","exec"),namespace)
    assert namespace["_fresh_su"]==json.loads(raw()) and namespace["_fresh_w3c"] is None


def test_unreadable_prior_bytes_refuse_without_overwriting(tmp_path,monkeypatch):
    publish(tmp_path);sp,rp=paths(tmp_path);before=rp.read_bytes()
    incumbent=Path.read_bytes
    def read(path):
        if path==rp:raise PermissionError("controlled unreadable prior receipt")
        return incumbent(path)
    monkeypatch.setattr(Path,"read_bytes",read)
    result=publish(tmp_path)
    assert result["status"]=="UNAVAILABLE"
    assert incumbent(rp)==before


@pytest.mark.parametrize('before,after', [(True,1),(False,0),(1,1.0)])
def test_cn_typed_reason_change_requires_exact_row_ancestry(tmp_path,before,after):
    library,served=cn_documents();lib=json.loads(library);doc=copy.deepcopy(lib)
    lib['buy'][0]['risk_sizing']={'units':before};doc['buy'][0]['risk_sizing']={'units':after}
    lb=json.dumps(lib).encode();sb=json.dumps(doc).encode()
    result=api().publish_cn_source(sb,library_bytes=lb,data_dir=tmp_path,finalized_at=T,
        reason_ancestry=[],authorize_capture=controlled_authority)
    assert result['reason_codes']==['REQUIRED_REASON_SOURCE_ANCESTRY_UNAVAILABLE']
    assert not list(tmp_path.rglob('*.json.gz'))
    accepted=api().publish_cn_source(sb,library_bytes=lb,data_dir=tmp_path,finalized_at=T,
        reason_ancestry=cn_ancestry(sb),authorize_capture=controlled_authority)
    assert accepted['status']=='AVAILABLE'
    assert type(accepted['receipt']['source_selection']['rows'][0]['original_reasons']['risk_sizing']['units']) is type(after)


@pytest.mark.parametrize('field', ['security_id','issuer_id'])
def test_cn_complete_native_identity_cannot_change_under_same_ticker(tmp_path,field):
    library,_=cn_documents();lib=json.loads(library);lib['buy'][0].update(security_id='SEC-original',issuer_id='ISS-original')
    served=copy.deepcopy(lib);served['buy'][0][field]='replaced'
    result=api().publish_cn_source(json.dumps(served).encode(),library_bytes=json.dumps(lib).encode(),
        data_dir=tmp_path,finalized_at=T,reason_ancestry=[],authorize_capture=controlled_authority)
    assert result['reason_codes']==['SERVED_COHORT_ORDER_MISMATCH']
    assert list(tmp_path.iterdir())==[]


def test_cn_repeated_native_identity_and_many_security_issuer_order_are_preserved(tmp_path):
    library,_=cn_documents();lib=json.loads(library)
    lib['buy']=[dict(ticker='ONE',security_id='SEC-1',issuer_id='ISS-shared'),
                dict(ticker='TWO',security_id='SEC-2',issuer_id='ISS-shared'),
                dict(ticker='ONE',security_id='SEC-1',issuer_id='ISS-shared')]
    data=json.dumps(lib).encode()
    result=api().publish_cn_source(data,library_bytes=data,data_dir=tmp_path,finalized_at=T,
        reason_ancestry=[],authorize_capture=controlled_authority)
    assert result['status']=='AVAILABLE'
    assert [r['original_identity'] for r in result['receipt']['source_selection']['rows']]==lib['buy']
    assert result['receipt']['source_selection']['n_selected']==3
    lib['buy'].reverse() # exact palindrome remains legitimately unchanged
    assert api().publish_cn_source(json.dumps(lib).encode(),library_bytes=data,data_dir=tmp_path,
        finalized_at=LATE,reason_ancestry=[],authorize_capture=controlled_authority)['status']=='AVAILABLE'


@pytest.mark.parametrize('outcome',['false','fault','unsupported','post_false','post_fault','allowed'])
def test_current_use_authorization_phases_precede_protected_receipt_read(tmp_path,monkeypatch,outcome):
    publish(tmp_path);sp,rp=paths(tmp_path);events=[];read=Path.read_bytes
    def traced(path):
        if path in (rp,sp):events.append('receipt_read' if path==rp else 'source_read')
        return read(path)
    monkeypatch.setattr(Path,'read_bytes',traced)
    def capability(request):
        phase=request.get('phase');events.append(phase)
        if phase=='pre_read':
            assert set(request)=={'market','generation_id','source_ref','source_sha256','purpose','phase'}
            assert request['source_ref']=='data/'+api().SOURCES+'/'+hashlib.sha256(raw()).hexdigest()+'.json.gz'
            if outcome=='fault':raise RuntimeError('revoked owner lookup')
            if outcome=='unsupported':raise KeyError('unsupported request phase')
            if outcome=='false':return False
        elif phase=='read_use':
            assert request['ancestry'] and request['source_schema'] and request['source_ref']=='site/factordata/us_standouts.json'
            if outcome=='post_fault':raise RuntimeError('current use fault')
            if outcome=='post_false':return False
        else:raise AssertionError('no permissive unphased legacy read')
        return True
    result=api().read_finalized_cohort(raw(),market='us_today',generation_id='native-process-1',
        data_dir=tmp_path,authorize_capture=capability)
    assert events[0]=='pre_read'
    if outcome in {'false','fault','unsupported'}:
        assert events==['pre_read'] and result['status']=='UNAVAILABLE'
    elif outcome in {'post_false','post_fault'}:
        assert events==['pre_read','receipt_read','read_use'] and result['status']=='UNAVAILABLE'
    else:
        assert events==['pre_read','receipt_read','read_use','source_read'] and result['status']=='AVAILABLE'


def test_none_and_missing_request_identity_refuse_before_protected_reads(tmp_path,monkeypatch):
    publish(tmp_path);reads=[];original=Path.read_bytes
    def traced(path):reads.append(str(path));return original(path)
    monkeypatch.setattr(Path,'read_bytes',traced)
    for generation,capability in [('native-process-1',None),('',controlled_authority)]:
        result=api().read_finalized_cohort(raw(),market='us_today',generation_id=generation,
            data_dir=tmp_path,authorize_capture=capability)
        assert result['status']=='UNAVAILABLE'
    assert reads==[]


def test_canonical_digest_source_reference_refuses_coherent_echo_rehash(tmp_path):
    publish(tmp_path);sp,rp=paths(tmp_path);receipt=json.loads(rp.read_bytes())
    foreign='data/'+api().SOURCES+'/'+'b'*64+'.json.gz'
    receipt['source_ref']=receipt['source_selection']['source_ref']=foreign
    receipt['receipt_sha256']=api().content_sha256({k:v for k,v in receipt.items() if k!='receipt_sha256'})
    with pytest.raises(ValueError):api().validate_publication(receipt)
    rp.write_text(json.dumps(receipt));before=rp.read_bytes()
    result=api().consume_us_source(raw(),data_dir=tmp_path,authorize_capture=controlled_authority)
    assert result['status']=='UNAVAILABLE' and rp.read_bytes()==before


def test_publication_retry_cannot_accept_coherent_foreign_market_receipt(tmp_path):
    publish(tmp_path);sp,rp=paths(tmp_path);receipt=json.loads(rp.read_bytes())
    receipt.update(market='cn_featured',reason_projection='cn-served-reasons/v1')
    receipt['source_selection'].update(owner='build_china',cohort_scope=api().MARKETS['cn_featured'])
    receipt['receipt_sha256']=api().content_sha256({k:v for k,v in receipt.items() if k!='receipt_sha256'})
    api().validate_publication(receipt);rp.write_text(json.dumps(receipt));before=rp.read_bytes()
    result=api().publish_us_source(raw(),data_dir=tmp_path,finalized_at=LATE,authorize_capture=controlled_authority)
    assert result['reason_codes']==['MIXED_SOURCE_GENERATION']
    assert rp.read_bytes()==before


def test_publication_retry_validates_recomposed_exact_typed_projection(tmp_path):
    publish(tmp_path);sp,rp=paths(tmp_path);receipt=json.loads(rp.read_bytes());selection=receipt['source_selection']
    selection['rows'][0]['source_row']['conviction']={'verdict':'forged'}
    selection['rows'][0]['original_reasons']['conviction']={'verdict':'forged'}
    selection['rows_sha256']=api().content_sha256(selection['rows'])
    selection['ordered_reasons_sha256']=api().content_sha256([r['original_reasons'] for r in selection['rows']])
    receipt['receipt_sha256']=api().content_sha256({k:v for k,v in receipt.items() if k!='receipt_sha256'})
    api().validate_publication(receipt);rp.write_text(json.dumps(receipt));before=rp.read_bytes()
    result=api().publish_us_source(raw(),data_dir=tmp_path,finalized_at=LATE,authorize_capture=controlled_authority)
    assert result['reason_codes']==['SOURCE_PROJECTION_MISMATCH']
    assert rp.read_bytes()==before


def test_same_generation_orphan_retry_never_reassigns_finalization_clock(tmp_path,monkeypatch):
    incumbent=api()._exclusive
    def interrupt(path,data):
        if path.suffix=='.json':raise OSError('first receipt write interrupted')
        incumbent(path,data)
    monkeypatch.setattr(api(),'_exclusive',interrupt)
    first=publish(tmp_path);sp,rp=paths(tmp_path);before=sp.read_bytes()
    assert first['status']=='UNAVAILABLE' and not rp.exists()
    monkeypatch.setattr(api(),'_exclusive',incumbent)
    later=api().publish_us_source(raw(),data_dir=tmp_path,finalized_at=LATE,authorize_capture=controlled_authority)
    assert later['reason_codes']==['UNSEALED_FINALIZATION_EVENT']
    assert later['receipt'] is None and not rp.exists() and sp.read_bytes()==before
    new=raw(generation='actual-distinct-owner-generation')
    assert api().publish_us_source(new,data_dir=tmp_path,finalized_at=LATE,
        authorize_capture=controlled_authority)['status']=='AVAILABLE'

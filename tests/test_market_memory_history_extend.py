"""An append is new evidence, never permission to rewrite an old market day."""
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
import copy
import hashlib
import importlib
import json
import pytest
from engine.neuralweb import market_memory_history_archive as ar
from tests.test_market_memory_history_archive import request


def module():
    assert importlib.util.find_spec('engine.neuralweb.market_memory_history_extend'), 'immutable history extension is not implemented'
    return importlib.import_module('engine.neuralweb.market_memory_history_extend')


def reader(*args, **kwargs):
    count=15 if len(args[2])>1 else 10
    rows=tuple({'market_date':(date(2020,1,1)+timedelta(days=i)).isoformat(),
                'close_raw':float(100+i),'close_tradj':float(50+i/2),'volume_raw':1000} for i in range(count))
    return SimpleNamespace(rows=rows,source_partitions=tuple(tuple(x) for x in args[2]),
        metadata=lambda:{'source':'eod-bars','vendor_symbol':args[1],'pit_backtest_eligible':False})


@pytest.fixture
def case(monkeypatch,tmp_path):
    monkeypatch.setattr(ar,'read_research_history',reader)
    req=request();old=tmp_path/'parent'
    receipt=ar.write_archive(ar.assemble_history(req),old)
    nxt=copy.deepcopy(req);nxt['end']='2020-01-20'
    nxt['symbols'][0]['refs'].append(['2026-10-14','b'*64])
    return SimpleNamespace(root=old,receipt=receipt,next=nxt,destination=tmp_path/'next',request=req)


def extend(case, **kwargs):
    return module().extend_archive(case.root,case.next,case.destination,
        expected_parent_manifest_sha256=case.receipt['manifest_sha256'],**kwargs)


def fingerprint(root):
    return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir() if p.is_file()}


def test_exact_append_preserves_all_old_states_and_separates_matured_outcomes(case):
    before=fingerprint(case.root)
    old=ar.read_day(case.root,'2020-01-09',expected_manifest_sha256=case.receipt['manifest_sha256'],reveal_outcomes=True)
    result=extend(case)
    assert result['status']=='EXTENDED' and result['preserved_state_rows']==10 and result['added_state_rows']==5
    assert result['parent_manifest_sha256']==case.receipt['manifest_sha256']
    new=ar.read_day(case.destination,'2020-01-09',expected_manifest_sha256=result['manifest_sha256'],reveal_outcomes=True)
    assert new['rows']==old['rows']
    assert old['outcomes'][0]['forward_return_5ob_pct'] is None
    assert new['outcomes'][0]['forward_return_5ob_pct'] is not None
    assert fingerprint(case.root)==before
    manifest=ar.read_manifest(case.destination,expected_manifest_sha256=result['manifest_sha256'])
    assert manifest['extension']['parent_artifact_id']==case.receipt['artifact_id']
    assert manifest['extension']['parent_manifest_sha256']==case.receipt['manifest_sha256']


def test_no_actual_new_rows_means_no_output(case):
    case.next['symbols']=copy.deepcopy(case.request['symbols'])
    result=extend(case)
    assert result['status']=='NO_NEW_OBSERVATIONS' and result['added_state_rows']==0
    assert not case.destination.exists()


@pytest.mark.parametrize('field,value', [('basis','raw'),('benchmark','OTHER'),('selection','a different universe'),
    ('start','2020-01-02'),('warmup_start','2019-01-02'),('end','2020-01-11'),
    ('capture_cutoff','2026-10-14T00:00:00Z')])
def test_changed_study_or_regressed_clock_refuses_before_source_read(case,monkeypatch,field,value):
    case.next[field]=value
    monkeypatch.setattr(ar,'read_research_history',lambda *a,**k:pytest.fail('source read before append admission'))
    with pytest.raises(ar.HistoricalExperienceError): extend(case)
    assert not case.destination.exists()


def test_old_reference_cannot_be_dropped(case):
    case.next['symbols'][0]['refs']=case.next['symbols'][0]['refs'][1:]
    with pytest.raises(ar.HistoricalExperienceError):extend(case)
    assert not case.destination.exists()


def test_new_symbol_is_not_an_append(case):
    case.next['symbols'].append({'vendor_symbol':'NEW','refs':[['2026-10-14','c'*64]]})
    with pytest.raises(ar.HistoricalExperienceError):extend(case)
    assert not case.destination.exists()


def test_revised_or_missing_historical_state_is_not_silently_accepted(case,monkeypatch):
    original=ar.assemble_history
    def changed(req):
        packet=original(req)
        packet['states'][0]['close_tradj']=999.0
        return packet
    monkeypatch.setattr(ar,'assemble_history',changed)
    with pytest.raises(ar.HistoricalExperienceError,match='historical state'):extend(case)
    assert not case.destination.exists()


def test_parent_corruption_refuses_before_publication(case):
    file=next(case.root.glob('states-*.parquet'));file.write_bytes(file.read_bytes()+b'corrupt')
    with pytest.raises(ar.HistoricalExperienceError):extend(case)
    assert not case.destination.exists()


def test_parent_digest_mismatch_refuses(case):
    with pytest.raises(ar.HistoricalExperienceError):
        module().extend_archive(case.root,case.next,case.destination,expected_parent_manifest_sha256='0'*64)
    assert not case.destination.exists()


def test_parent_outcomes_are_not_opened(case):
    for p in case.root.glob('outcomes-*.parquet'):p.unlink()
    assert extend(case)['status']=='EXTENDED'


def test_existing_destination_never_overwritten(case):
    case.destination.mkdir();(case.destination/'sentinel').write_text('preserve')
    with pytest.raises(FileExistsError):extend(case)
    assert (case.destination/'sentinel').read_text()=='preserve'


def test_same_parent_path_never_overwritten(case):
    case.destination=case.root;before=fingerprint(case.root)
    with pytest.raises(FileExistsError):extend(case)
    assert fingerprint(case.root)==before


def test_empty_response_does_not_drop_existing_states(case,monkeypatch):
    original=ar.assemble_history
    def changed(req):
        packet=original(req);packet['states']=[];return packet
    monkeypatch.setattr(ar,'assemble_history',changed)
    with pytest.raises(ar.HistoricalExperienceError,match='historical state'):extend(case)
    assert not case.destination.exists()


def test_false_parent_logical_state_digest_refuses(case):
    m=json.loads((case.root/'manifest.json').read_text());m['states_sha256']='0'*64
    m['artifact_id']=ar._semantic_identity(m);raw=ar._bytes(m)
    (case.root/'manifest.json').write_bytes(raw);case.receipt['manifest_sha256']=ar._hash(raw)
    with pytest.raises(ar.HistoricalExperienceError,match='canonical state payload digest'):extend(case)
    assert not case.destination.exists()


def test_old_missing_day_cannot_be_retroactively_inserted(case,monkeypatch):
    original=ar.assemble_history
    def insert(req):
        packet=original(req)
        packet['states'].insert(1,dict(packet['states'][0],vendor_symbol='NEW'))
        return packet
    monkeypatch.setattr(ar,'assemble_history',insert)
    with pytest.raises(ar.HistoricalExperienceError,match='historical state'):extend(case)
    assert not case.destination.exists()


def test_parent_capture_and_state_evidence_cannot_be_changed_during_build(case,monkeypatch):
    original=ar.assemble_history
    def changed(req):
        packet=original(req)
        manifest=case.root/'manifest.json';manifest.write_bytes(manifest.read_bytes()+b' ')
        return packet
    monkeypatch.setattr(ar,'assemble_history',changed)
    with pytest.raises(ar.HistoricalExperienceError,match='manifest digest'):extend(case)
    assert not case.destination.exists()


def test_different_feature_version_is_not_automatically_upgraded(case):
    m=json.loads((case.root/'manifest.json').read_text());m['feature_version']='older.feature.v0'
    m['artifact_id']=ar._semantic_identity(m);raw=ar._bytes(m)
    (case.root/'manifest.json').write_bytes(raw);case.receipt['manifest_sha256']=ar._hash(raw)
    with pytest.raises(ar.HistoricalExperienceError,match='feature version'):extend(case)
    assert not case.destination.exists()


def test_digest_bound_extension_chain_reuses_successful_generation_without_new_write(case):
    first=extend(case);parent=case.destination
    result=module().extend_archive(parent,case.next,parent.parent/'third',expected_parent_manifest_sha256=first['manifest_sha256'])
    assert result['status']=='NO_NEW_OBSERVATIONS' and result['preserved_state_rows']==15
    assert not (parent.parent/'third').exists()


def test_destination_cannot_be_created_inside_the_immutable_parent(case,monkeypatch):
    case.destination=case.root/'nested-generation'
    monkeypatch.setattr(ar,'read_research_history',lambda *a,**k:pytest.fail('nested parent write admitted before source read'))
    with pytest.raises(ar.HistoricalExperienceError,match='inside the parent archive'):extend(case)
    assert not case.destination.exists()


def test_case_insensitive_parent_alias_cannot_bypass_no_nested_write(case,monkeypatch):
    alias=case.root.with_name(case.root.name.swapcase())
    if not alias.exists() or not alias.samefile(case.root):
        pytest.skip('filesystem distinguishes case; actual APFS alias path is not present')
    assert alias.resolve()!=case.root.resolve()
    case.destination=alias/'nested-generation'
    monkeypatch.setattr(ar,'read_research_history',lambda *a,**k:pytest.fail('case alias bypassed immutable-parent preflight'))
    with pytest.raises(ar.HistoricalExperienceError,match='inside the parent archive'):extend(case)
    assert not case.destination.exists()

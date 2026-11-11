"""Synthetic discriminators only. No native data, ledger, R2 or publication."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import pytest

from engine import foresight_divergence as candidate
ROOT = Path(__file__).resolve().parents[1]
GOLDEN = json.loads((ROOT / "tests/fixtures/native_divergence_incumbent_boards.json").read_text())

def incumbent(n):
    return copy.deepcopy(GOLDEN["cases"][str(n)])

@pytest.mark.parametrize("phase",["input","final"])
def test_optional_capture_encoding_failure_preserves_single_board_and_ledger(tmp_path,monkeypatch,phase):
    cascade,activity=cohort();original_rows=incumbent(8)["ledger_calls"];candidate_rows=[];axis_calls=[]
    monkeypatch.setattr(candidate,"_append_divergence_ledger",lambda rows,**kw:candidate_rows.append(rows))
    expected=incumbent(8)["board"]
    native_axis=candidate._axis_raw
    monkeypatch.setattr(candidate,"_axis_raw",lambda args:(axis_calls.append(1),native_axis(args))[1])
    dumps=candidate.json.dumps
    def fail_capture(value,*args,**kwargs):
        if (phase=="input" and type(value) is dict and set(value)=={"cascade","activity"}) or (phase=="final" and type(value) is dict and value.get("schema")=="gmi.divergence_same_run_capture/v1"):
            raise ValueError("synthetic capture-only encoding failure")
        return dumps(value,*args,**kwargs)
    monkeypatch.setattr(candidate.json,"dumps",fail_capture)
    sink={}
    assert candidate.compute_divergence_board(cascade,activity,root=tmp_path,provenance_sink=sink,capture_optional=True)==expected
    assert sink=={} and candidate_rows==original_rows and len(candidate_rows)==1 and len(axis_calls)==16

def cohort(n=8):
    return ({"asof": "2026-10-19", "themes": [
        {"theme": f"theme{i}", "language_accel": float(i+1),
         "revision_breadth": float(n-i), "bottleneck_band": None}
        for i in range(n)]},
        {f"theme{i}": {"fused_obs_z": float(n-i)*2,
                       "sources": [{"name": "news_velocity", "z": float(i)/2}]}
         for i in range(n)})

def compute(cascade, activity, root, **kw):
    return candidate.compute_divergence_board(cascade, activity, root=root, write_ledger=False, **kw)

@pytest.mark.parametrize("n", [1, 5, 6, 8])
def test_default_and_capture_keep_exact_incumbent_board(n, tmp_path):
    cascade, activity = cohort(n)
    expected = incumbent(n)["board"]
    assert compute(cascade, activity, tmp_path) == expected
    sink = {}
    assert compute(cascade, activity, tmp_path, provenance_sink=sink) == expected
    assert sink["board"] == expected
    assert sink["n_input_rows"] == n
    assert len(sink["axis_computations"]) == n
    assert sink["cross_section_positions"] == list(range(n))
    assert sink["source_available_at"] is None
    assert sink["publication_allowed"] is False

def test_complete_attempted_denominator_and_asymmetric_axes(tmp_path):
    cascade, activity = cohort()
    cascade["themes"].extend([{"theme":"narrative_only","language_accel":7.0},
                              {"theme":"money_only","revision_breadth":3.0},
                              {"name":"missing native key"}])
    sink = {}
    board = compute(cascade, activity, tmp_path, provenance_sink=sink)
    assert board["n_total"] == 10 and board["n_cross_section"] == 8
    assert sink["n_input_rows"] == 11 and len(sink["attempted_population"]) == 11
    assert sink["attempted_population"][-1]["status"] == "MISSING_NATIVE_KEY"
    assert sink["identity_status"] == "UNQUALIFIED"
    assert sink["axis_computations"][-2]["money_raw"] is None
    assert sink["axis_computations"][-1]["narrative_raw"] is None
    by_theme = {item["theme"]:item for item in board["items"]}
    assert by_theme["theme0"]["quadrant"] == "hidden-opportunity"
    assert by_theme["theme7"]["quadrant"] == "hype-risk"
    assert sink["axis_computations"][0]["narrative_raw"] != sink["axis_computations"][0]["money_raw"]
    assert "provenance" not in json.dumps(board)

def test_one_axis_execution_and_no_file_writes(monkeypatch,tmp_path):
    cascade, activity = cohort()
    calls = []
    native = candidate._axis_raw
    monkeypatch.setattr(candidate, "_axis_raw", lambda args:(calls.append(tuple(args)),native(args))[1])
    sink={}
    compute(cascade,activity,tmp_path,provenance_sink=sink)
    assert len(calls)==16
    assert not list(tmp_path.rglob("*"))
    assert sink["predecessor_ledger"]["state"]=="ABSENT_AT_CHECK"

def test_actual_predecessor_bytes_and_transition_retained(tmp_path):
    cascade, activity = cohort()
    # Theme7 money becomes maximal too: a real asymmetric hidden->confirmed.
    activity["theme7"]["fused_obs_z"]=1000.
    ledger=tmp_path/"foresight"/"divergence_log.jsonl"
    ledger.parent.mkdir()
    raw=b'{"theme":"theme7","asof":"2026-10-18","quadrant":"hidden-opportunity"}\r\n'
    ledger.write_bytes(raw)
    sink={}
    board=compute(cascade,activity,tmp_path,provenance_sink=sink)
    assert next(r for r in board["items"] if r["theme"]=="theme7")["transition"]=="hidden→confirmed"
    assert sink["predecessor_ledger"]=={"state":"READ","sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw)}
    assert sink["last_quadrants_used"]["theme7"]==("2026-10-18","hidden-opportunity")
    assert ledger.read_bytes()==raw

def test_frozen_input_and_output_hashes_do_not_alias(tmp_path):
    cascade,activity=cohort()
    before=copy.deepcopy({"cascade":cascade,"activity":activity})
    sink={}
    board=compute(cascade,activity,tmp_path,provenance_sink=sink)
    assert sink["input_sha256"]==hashlib.sha256(json.dumps(before,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(",",":")).encode()).hexdigest()
    recorded=copy.deepcopy(sink)
    cascade["themes"][0]["theme"]="mutated"
    activity["theme0"]["fused_obs_z"]=99
    board["items"].clear()
    assert sink==recorded
    payload=dict(sink); digest=payload.pop("capture_sha256")
    assert hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(",",":")).encode()).hexdigest()==digest

@pytest.mark.parametrize("value",[float("nan"),float("inf"),-float("inf")])
def test_nonfinite_input_refuses_without_capture_or_append(value,monkeypatch,tmp_path):
    cascade,activity=cohort();activity["theme0"]["fused_obs_z"]=value
    sink={}; writes=[]
    monkeypatch.setattr(candidate,"_append_divergence_ledger",lambda *a,**k:writes.append(1))
    with pytest.raises(ValueError):
        candidate.compute_divergence_board(cascade,activity,root=tmp_path,provenance_sink=sink)
    assert sink=={} and writes==[]

def test_overflow_refuses_before_optional_ledger_effect(monkeypatch,tmp_path):
    cascade,activity=cohort()
    for row in cascade["themes"]:
        row["revision_breadth"]=1.7e308
        activity[row["theme"]]["fused_obs_z"]=1.7e308
    sink={};writes=[]
    monkeypatch.setattr(candidate,"_append_divergence_ledger",lambda *a,**k:writes.append(1))
    with pytest.raises(ValueError):
        candidate.compute_divergence_board(cascade,activity,root=tmp_path,provenance_sink=sink)
    assert sink=={} and writes==[]

def test_optional_native_append_after_complete_capture(monkeypatch,tmp_path):
    cascade,activity=cohort();sink={};states=[]
    def append(rows,**kw):
        states.append(sink.get("capture_sha256"))
        return len(rows)
    monkeypatch.setattr(candidate,"_append_divergence_ledger",append)
    candidate.compute_divergence_board(cascade,activity,root=tmp_path,provenance_sink=sink)
    assert states==[sink["capture_sha256"]]
    assert "append_succeeded" not in sink

def test_existing_sink_never_overwritten(tmp_path):
    cascade,activity=cohort();sink={"old":"retained"}
    with pytest.raises(ValueError,match="empty dict"):
        compute(cascade,activity,tmp_path,provenance_sink=sink)
    assert sink=={"old":"retained"}

def test_missing_effective_date_is_marked_as_fallback(tmp_path):
    cascade,activity=cohort();cascade.pop("asof");sink={}
    compute(cascade,activity,tmp_path,provenance_sink=sink)
    assert sink["effective_at_declared"] is False
    assert sink["qualification"]=="UNQUALIFIED_NATIVE_COMPUTATION"
    assert sink["producer_revision"] is None
    assert sink["member_identity_receipts"] is None
    assert sink["source_purpose_receipts"] is None

def test_duplicate_native_key_is_explicitly_unqualified(tmp_path):
    cascade,activity=cohort();cascade["themes"].append(copy.deepcopy(cascade["themes"][0]));sink={}
    compute(cascade,activity,tmp_path,provenance_sink=sink)
    assert sink["n_input_rows"]==9 and sink["identity_status"]=="UNQUALIFIED"


def test_source_prose_and_unconsumed_fields_never_retained(tmp_path):
    cascade,activity=cohort()
    cascade["source_body"]="PRIVATE_SOURCE_PROSE_CANARY"
    cascade["themes"][0]["rationale"]="PRIVATE_SOURCE_PROSE_CANARY"
    activity["theme0"]["credentials"]="SECRET_CANARY"
    activity["theme0"]["sources"].append({"name":"unconsumed","z":3.0,"body":"PRIVATE_SOURCE_PROSE_CANARY"})
    activity["unattempted"]={"fused_obs_z":99.0,"body":"UNATTEMPTED_CANARY"}
    expected=incumbent(8)["board"]
    sink={}
    actual=compute(cascade,activity,tmp_path,provenance_sink=sink)
    assert actual==expected
    text=json.dumps(sink)
    assert all(canary not in text for canary in ("PRIVATE_SOURCE_PROSE_CANARY","SECRET_CANARY","UNATTEMPTED_CANARY"))
    assert sink["input_scope"]=="NATIVE_DIVERGENCE_FIELDS_NOT_UPSTREAM_PROVENANCE"


"""Immutable private retention contract tests; no credentials, network or native data."""
import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest
from engine.research_vault import divergence_capture as r
RUN="original-synthetic-run-1"
COMMIT="a"*40

@pytest.fixture
def capture(tmp_path):
    sink={}
    compute(*cohort(),tmp_path,provenance_sink=sink)
    return sink

def rehash(capture):
    capture["input_sha256"]=r.digest(r.canonical(capture["inputs"]))
    payload=dict(capture);payload.pop("capture_sha256",None)
    capture["capture_sha256"]=r.digest(r.canonical(payload))
    return capture

class MemoryStore:
    def __init__(self):
        self.data={};self.puts=[];self.reads=[];self.capability=True
        self.before_read=None;self.write_mode="success"
    def validate_strict_conditional_write_capability(self):
        if not self.capability:
            raise RuntimeError("capability unavailable")
    def get_bytes_strict_bounded(self,key,limit):
        self.reads.append((key,limit))
        if self.before_read:
            self.before_read(self,key)
        return self.data.get(key)
    def put_bytes_strict_conditional(self,key,raw,*,expected_version,content_type):
        self.puts.append((key,raw,expected_version,content_type))
        assert expected_version is None
        if self.write_mode=="lost_absent":
            raise OSError("lost response")
        if self.write_mode=="conflict_different":
            self.data[key]=b"different writer"
            return False
        if self.write_mode=="conflict_absent":
            return False
        self.data[key]=raw
        if self.write_mode=="lost_committed":
            raise OSError("lost response after commit")
        if self.write_mode=="invalid_response":
            return "yes"
        return self.write_mode!="conflict_identical"

def retain(store,capture):
    return r._retain_prepared_store_once(store,capture,native_run_id=RUN,producer_commit=COMMIT,before_write=lambda *args:None)

def test_one_conditional_create_bounded_readback_and_closed_envelope(capture):
    store=MemoryStore();ref=retain(store,capture)
    assert len(store.puts)==1
    key,raw,version,content_type=store.puts[0]
    assert key==r.key_for_run(RUN) and version is None and content_type=="application/json"
    assert store.reads==[(key,r.MAX_BYTES)]*2
    assert ref.state=="COMMITTED_OBSERVED" and ref.publication_allowed is False
    assert ref.payload_sha256==r.digest(raw)
    envelope=json.loads(raw)
    assert set(envelope)=={"schema","native_run_id","declared_producer_commit","capture","purpose","source_authentication","qualification","publication_allowed"}
    assert envelope["purpose"]=="internal_replay" and envelope["source_authentication"]=="NOT_ESTABLISHED"
    assert envelope["declared_producer_commit"]==COMMIT
    assert "current" not in key and RUN not in key

def test_existing_identical_bytes_are_observed_without_put(capture):
    store=MemoryStore();key,raw=r.prepare(capture,native_run_id=RUN,producer_commit=COMMIT)
    store.data[key]=raw
    assert retain(store,capture).state=="COMMITTED_OBSERVED"
    assert store.puts==[]

def test_existing_conflicting_bytes_never_overwritten(capture):
    store=MemoryStore();store.data[r.key_for_run(RUN)]=b"old"
    with pytest.raises(r.CaptureRefused,match="different immutable"):
        retain(store,capture)
    assert store.puts==[] and store.data[r.key_for_run(RUN)]==b"old"

@pytest.mark.parametrize("mode",["success","lost_committed","conflict_identical"])
def test_authoritative_exact_readback_settles_one_write(capture,mode):
    store=MemoryStore();store.write_mode=mode
    assert retain(store,capture).state=="COMMITTED_OBSERVED"
    assert len(store.puts)==1

@pytest.mark.parametrize("mode",["lost_absent","conflict_absent","invalid_response"])
def test_uncertain_return_never_retries_and_retains_original_identity(capture,mode):
    store=MemoryStore();store.write_mode=mode
    with pytest.raises(r.CaptureEffectUnknown) as failure:
        retain(store,capture)
    assert failure.value.key==r.key_for_run(RUN) and len(store.puts)==1
    # Reconciliation is GET-only, even if the original write became visible later.
    key,raw=r.prepare(capture,native_run_id=RUN,producer_commit=COMMIT)
    store.data[key]=raw
    assert r.reconcile(store,native_run_id=RUN,expected_sha256=failure.value.expected_sha256).state=="COMMITTED_OBSERVED"
    assert len(store.puts)==1

def test_conflicting_writer_after_pre_read_never_retries(capture):
    store=MemoryStore();store.write_mode="conflict_different"
    with pytest.raises(r.CaptureRefused,match="different immutable"):
        retain(store,capture)
    assert len(store.puts)==1

def test_read_failure_before_write_is_not_a_write_unknown(capture):
    store=MemoryStore()
    def fail(*args): raise OSError("read unavailable")
    store.before_read=fail
    with pytest.raises(OSError): retain(store,capture)
    assert store.puts==[]

def test_readback_failure_is_unknown_after_one_put(capture):
    store=MemoryStore()
    def fail_second(store,key):
        if store.puts: raise OSError("readback unavailable")
    store.before_read=fail_second
    with pytest.raises(r.CaptureEffectUnknown): retain(store,capture)
    assert len(store.puts)==1

def test_missing_conditional_capability_has_no_reads_or_effects(capture):
    store=MemoryStore();store.capability=False
    with pytest.raises(RuntimeError): retain(store,capture)
    assert store.reads==[] and store.puts==[]

@pytest.mark.parametrize("where",["root","inputs","theme","activity","source","axis","native_values","board","item","predecessor"])
def test_extra_private_field_refused_even_with_recomputed_hashes(capture,where):
    targets={"root":capture,"inputs":capture["inputs"],"theme":capture["inputs"]["cascade"]["themes"][0],
             "activity":capture["inputs"]["activity"]["theme0"],"source":capture["inputs"]["activity"]["theme0"]["sources"][0],
             "axis":capture["axis_computations"][0],"native_values":capture["axis_computations"][0]["narrative_native_values"],
             "board":capture["board"],"item":capture["board"]["items"][0],"predecessor":capture["predecessor_ledger"]}
    targets[where]["source_body"]="PRIVATE_CANARY"
    store=MemoryStore()
    with pytest.raises(r.CaptureRefused): retain(store,rehash(capture))
    assert store.reads==[] and store.puts==[]

def test_nested_prose_in_allowed_scalar_cannot_be_retained(capture):
    capture["inputs"]["cascade"]["themes"][0]["name"]={"source_body":"PRIVATE_CANARY"}
    store=MemoryStore()
    with pytest.raises(r.CaptureRefused): retain(store,rehash(capture))
    assert store.reads==[]

@pytest.mark.parametrize("change",["publication","qualification","receipts","digest","denominator","unattempted","nonfinite"])
def test_tampered_scope_or_content_refused_before_store(capture,change):
    if change=="publication": capture["publication_allowed"]=True
    if change=="qualification": capture["qualification"]="QUALIFIED"
    if change=="receipts": capture["member_identity_receipts"]={"invented":True}
    if change=="denominator": capture["n_input_rows"]-=1
    if change=="unattempted": capture["inputs"]["activity"]["unattempted"]={"fused_obs_z":0,"sources":[]}
    if change=="nonfinite": capture["board"]["items"][0]["divergence"]=float("nan")
    if change not in ("digest","nonfinite"): rehash(capture)
    if change=="digest": capture["capture_sha256"]="0"*64
    store=MemoryStore()
    with pytest.raises((r.CaptureRefused,ValueError)): retain(store,capture)
    assert store.puts==[] and store.reads==[]

def test_byte_budget_refusal_precedes_store(capture,monkeypatch):
    monkeypatch.setattr(r,"MAX_BYTES",100)
    store=MemoryStore()
    with pytest.raises(r.CaptureRefused,match="allocation"): retain(store,capture)
    assert store.reads==[] and store.puts==[]

@pytest.mark.parametrize("run",["",None,False,"bad\nidentity","a"*193])
def test_missing_or_malformed_run_identity_refused(capture,run):
    with pytest.raises(r.CaptureRefused): r.prepare(capture,native_run_id=run,producer_commit=COMMIT)

def test_runtime_factory_requires_private_exact_r2_and_single_attempt(monkeypatch):
    from engine.research_vault import r2_store
    class Qualified(MemoryStore):
        available=True
        _single_attempt_writes=True
    calls=[];chosen=Qualified()
    def build(**kwargs): calls.append(kwargs);return chosen
    monkeypatch.setattr(r2_store,"R2Store",Qualified)
    monkeypatch.setattr(r2_store,"build_store",build)
    assert r.runtime_store() is chosen
    assert calls==[{"single_attempt_writes":True}]
    chosen._single_attempt_writes=False
    with pytest.raises(r.CaptureRefused): r.runtime_store()
    chosen=MemoryStore()
    with pytest.raises(r.CaptureRefused): r.runtime_store()
    chosen=None
    with pytest.raises(r.CaptureRefused): r.runtime_store()

@pytest.fixture
def production_store(monkeypatch):
    from engine.research_vault import r2_store
    class Qualified(MemoryStore):
        available=True
        _single_attempt_writes=True
    chosen=Qualified()
    monkeypatch.setattr(r2_store,"R2Store",Qualified)
    monkeypatch.setattr(r,"runtime_store",lambda:chosen)
    return chosen

def submit(capture,tmp_path):
    tmp_path.chmod(0o700)
    return r.retain_private_capture(capture,native_run_id=RUN,producer_commit=COMMIT,private_run_dir=tmp_path)

def test_production_entry_enforces_guarded_transport_before_journal(capture,tmp_path,production_store):
    production_store._single_attempt_writes=False
    with pytest.raises(r.CaptureRefused): submit(capture,tmp_path)
    assert production_store.puts==[] and not list(tmp_path.glob("*.jsonl"))

def test_original_intent_is_durable_before_put_and_slot_is_not_reusable(capture,tmp_path,production_store):
    from engine.research_vault.generation_evidence import read_evidence,EvidenceUnavailable
    original_put=production_store.put_bytes_strict_conditional
    def checked_put(key,raw,**kwargs):
        path=next(tmp_path.glob("*.jsonl"))
        events=[json.loads(line)["event"] for line in path.read_text().splitlines()]
        assert events[-1]["kind"]=="write_intent"
        assert events[-1]["payload"]["key"]==key
        assert events[-1]["payload"]["sha256"]==r.digest(raw)
        return original_put(key,raw,**kwargs)
    production_store.put_bytes_strict_conditional=checked_put
    result=submit(capture,tmp_path)
    path=next(tmp_path.glob("*.jsonl"));before=path.read_bytes()
    events=read_evidence(path,expected_identity={"source_commit":COMMIT,"run":RUN})
    assert events[-1]["payload"]["state"]==result.state=="COMMITTED_OBSERVED"
    with pytest.raises(EvidenceUnavailable): submit(capture,tmp_path)
    assert len(production_store.puts)==1 and path.read_bytes()==before

def test_unknown_original_operation_can_only_reconcile_without_second_put(capture,tmp_path,production_store):
    from engine.research_vault.generation_evidence import read_evidence,EvidenceUnavailable
    production_store.write_mode="lost_absent"
    with pytest.raises(r.CaptureEffectUnknown): submit(capture,tmp_path)
    path=next(tmp_path.glob("*.jsonl"))
    events=read_evidence(path,expected_identity={"source_commit":COMMIT,"run":RUN})
    intent=next(e["payload"] for e in events if e["kind"]=="write_intent")
    assert events[-1]["payload"]["state"]=="UNRESOLVED"
    with pytest.raises(EvidenceUnavailable): submit(capture,tmp_path)
    with pytest.raises(r.CaptureEffectUnknown):
        r.reconcile(production_store,native_run_id=RUN,expected_sha256=intent["sha256"])
    assert len(production_store.puts)==1
    key,raw=r.prepare(capture,native_run_id=RUN,producer_commit=COMMIT)
    production_store.data[key]=raw
    assert r.reconcile(production_store,native_run_id=RUN,expected_sha256=intent["sha256"]).state=="COMMITTED_OBSERVED"
    assert len(production_store.puts)==1

def test_intent_persistence_failure_prevents_put(capture,tmp_path,production_store,monkeypatch):
    from engine.research_vault.generation_evidence import FileGenerationEvidence,EvidenceUnavailable
    original=FileGenerationEvidence.append
    def fail_intent(self,kind,payload,**kwargs):
        if kind=="write_intent": raise EvidenceUnavailable("synthetic durable sink failure")
        return original(self,kind,payload,**kwargs)
    monkeypatch.setattr(FileGenerationEvidence,"append",fail_intent)
    with pytest.raises(EvidenceUnavailable): submit(capture,tmp_path)
    assert production_store.puts==[]

def test_world_readable_original_artifact_directory_refuses(capture,tmp_path,production_store):
    from engine.research_vault.generation_evidence import EvidenceUnavailable
    tmp_path.chmod(0o755)
    with pytest.raises(EvidenceUnavailable):
        r.retain_private_capture(capture,native_run_id=RUN,producer_commit=COMMIT,private_run_dir=tmp_path)
    assert production_store.puts==[]

@pytest.mark.parametrize("phase,mode",[("terminal","success"),("close","success"),("terminal","lost_absent")])
def test_finalization_failure_keeps_unknown_key_digest_and_exclusive_slot(capture,tmp_path,production_store,monkeypatch,phase,mode):
    from engine.research_vault.generation_evidence import FileGenerationEvidence,EvidenceUnavailable
    production_store.write_mode=mode
    original_append,original_close=FileGenerationEvidence.append,FileGenerationEvidence.close
    def fail_terminal(self,kind,payload,**kwargs):
        if kind=="terminal": raise EvidenceUnavailable("synthetic terminal persistence failure")
        return original_append(self,kind,payload,**kwargs)
    def fail_close(self):
        original_close(self)
        raise EvidenceUnavailable("synthetic close failure")
    if phase=="terminal": monkeypatch.setattr(FileGenerationEvidence,"append",fail_terminal)
    if phase=="close": monkeypatch.setattr(FileGenerationEvidence,"close",fail_close)
    key,raw=r.prepare(capture,native_run_id=RUN,producer_commit=COMMIT)
    with pytest.raises(r.CaptureEffectUnknown) as failure: submit(capture,tmp_path)
    assert failure.value.key==key and failure.value.expected_sha256==r.digest(raw)
    assert len(production_store.puts)==1
    with pytest.raises(EvidenceUnavailable): submit(capture,tmp_path)
    assert len(production_store.puts)==1



"""Ordinary-invocation handoff falsifiers: synthetic bytes, no native execution."""
import json
import os
from pathlib import Path
import pytest
from engine.research_vault import divergence_handoff as h
from engine.research_vault.generation_evidence import EvidenceUnavailable, FileGenerationEvidence

COMMIT="a"*40

def submit_staged(repo,env,staged):
    return h.retain_staged(repo,expected_payload_sha256=staged["payload_sha256"],expected_source_sha256=staged["source_sha256"],original_producer_commit=staged["producer_commit"],environ=env)

@pytest.fixture
def invocation(tmp_path, monkeypatch):
    repo=tmp_path/"checkout";repo.mkdir()
    runner=tmp_path/"runner";runner.mkdir()
    env={"GITHUB_ACTIONS":"true","GITHUB_REPOSITORY":h.REPOSITORY,
         "GITHUB_JOB":"engine","COLLECT_LANE":"nightly",
         "GITHUB_WORKFLOW_REF":h.REPOSITORY+"/.github/workflows/daily.yml@refs/heads/main",
         "GITHUB_RUN_ID":"123","GITHUB_RUN_ATTEMPT":"1","RUNNER_TEMP":str(runner)}
    monkeypatch.setattr(h,"_head",lambda repo:COMMIT)
    monkeypatch.setattr(h,"_source_binding",lambda repo:(h._head(repo),"c"*64))
    return repo,runner,env

@pytest.mark.parametrize("env",[{},{"COLLECT_LANE":"nightly","RENDER_NO_DRIP":"1"}])
def test_render_and_non_nightly_do_nothing_even_without_filesystem(env,monkeypatch):
    monkeypatch.setattr(h,"_head",lambda *a:pytest.fail("source read forbidden"))
    monkeypatch.setattr(h.retention,"retain_private_capture",lambda *a,**k:pytest.fail("store forbidden"))
    assert h.begin("/does-not-exist",environ=env) is None
    assert h.retain_staged("/does-not-exist",expected_payload_sha256=None,expected_source_sha256=None,original_producer_commit=None,environ=env) is None
    assert h.journal_path("/does-not-exist",expected_payload_sha256=None,original_producer_commit=None,environ=env) is None

@pytest.mark.parametrize("key,value",[("GITHUB_ACTIONS","false"),("GITHUB_REPOSITORY","other/repo"),
    ("GITHUB_JOB","render"),("GITHUB_WORKFLOW_REF",h.REPOSITORY+"/.github/workflows/daily.yml@refs/heads/pr"),
    ("GITHUB_RUN_ID","../123"),("GITHUB_RUN_ATTEMPT","0")])
def test_wrong_native_identity_has_no_staged_effect(invocation,key,value):
    repo,runner,env=invocation;env[key]=value
    with pytest.raises(h.retention.CaptureRefused): h.begin(repo,environ=env)
    assert list(runner.iterdir())==[]

def test_capture_directory_is_private_exclusive_and_outside_checkout(invocation):
    repo,runner,env=invocation
    context=h.begin(repo,environ=env)
    assert context.commit==COMMIT and context.directory.parent==runner
    assert context.directory.stat().st_mode&0o777==0o700
    (context.directory/"unknown-partial").write_text("preserve")
    with pytest.raises(FileExistsError): h.begin(repo,environ=env)
    assert (context.directory/"unknown-partial").read_text()=="preserve"
    env["RUNNER_TEMP"]=str(repo)
    with pytest.raises(h.retention.CaptureRefused,match="outside checkout"): h.begin(repo,environ=env)

def test_same_invocation_exact_capture_and_one_retention(invocation,capture,production_store):
    repo,runner,env=invocation;ctx=h.begin(repo,environ=env)
    staged=h.stage(capture,ctx)
    assert (ctx.directory/"capture.json").stat().st_mode&0o777==0o600
    assert staged["payload_sha256"]==h.retention.digest((ctx.directory/"capture.json").read_bytes())
    store=production_store
    ref=submit_staged(repo,env,staged)
    assert ref.state=="COMMITTED_OBSERVED" and len(store.puts)==1
    assert json.loads(store.puts[0][1])["capture"]==json.loads(json.dumps(capture))
    journal=h.journal_path(repo,expected_payload_sha256=staged["payload_sha256"],original_producer_commit=staged["producer_commit"],environ=env)
    assert journal.suffix==".jsonl" and journal.name!="capture.json"
    assert "source_body" not in journal.read_text() and "axis_computations" not in journal.read_text()
    with pytest.raises(EvidenceUnavailable): submit_staged(repo,env,staged)
    assert len(store.puts)==1 and list(repo.iterdir())==[]

def test_source_drift_before_stage_preserves_slot_without_payload(invocation,capture,monkeypatch):
    repo,runner,env=invocation;ctx=h.begin(repo,environ=env)
    monkeypatch.setattr(h,"_head",lambda repo:"b"*40)
    with pytest.raises(h.retention.CaptureRefused,match="source moved"): h.stage(capture,ctx)
    assert list(ctx.directory.iterdir())==[]

def test_source_drift_before_publisher_never_relabels_capture(invocation,capture,monkeypatch):
    repo,runner,env=invocation;ctx=h.begin(repo,environ=env);staged=h.stage(capture,ctx)
    monkeypatch.setattr(h,"_head",lambda repo:"b"*40)
    monkeypatch.setattr(h.retention,"runtime_store",lambda:pytest.fail("no store before source binding"))
    with pytest.raises(h.retention.CaptureRefused,match="source mismatch"): submit_staged(repo,env,staged)

@pytest.mark.parametrize("change",["public_mode","symlink","hardlink","noncanonical","foreign_run"])
def test_changed_staged_carrier_refuses_before_store(invocation,capture,monkeypatch,change):
    repo,runner,env=invocation;ctx=h.begin(repo,environ=env);staged=h.stage(capture,ctx)
    path=ctx.directory/"capture.json"
    if change=="public_mode": path.chmod(0o644)
    if change=="symlink":
        saved=ctx.directory/"saved";path.rename(saved);path.symlink_to(saved)
    if change=="hardlink": os.link(path,ctx.directory/"another")
    if change=="noncanonical": path.write_bytes(path.read_bytes()+b"\n")
    if change=="foreign_run":
        obj=json.loads(path.read_bytes());obj["native_run_id"]="other";path.write_text(json.dumps(obj))
    monkeypatch.setattr(h.retention,"runtime_store",lambda:pytest.fail("no store for changed carrier"))
    with pytest.raises((h.retention.CaptureRefused,OSError)): submit_staged(repo,env,staged)

def test_lost_response_remains_same_run_unknown_without_second_put(invocation,capture,production_store):
    repo,runner,env=invocation;ctx=h.begin(repo,environ=env);staged=h.stage(capture,ctx)
    store=production_store;store.write_mode="lost_absent"
    with pytest.raises(h.retention.CaptureEffectUnknown) as error: submit_staged(repo,env,staged)
    journal=h.journal_path(repo,expected_payload_sha256=staged["payload_sha256"],original_producer_commit=staged["producer_commit"],environ=env)
    assert journal is not None and "write_intent" in journal.read_text()
    assert error.value.key==h.retention.key_for_run(ctx.run_id) and len(store.puts)==1
    with pytest.raises(EvidenceUnavailable): submit_staged(repo,env,staged)
    assert len(store.puts)==1

def test_valid_rehashed_replacement_cannot_replace_original_stage(invocation,capture,monkeypatch):
    repo,runner,env=invocation;ctx=h.begin(repo,environ=env);staged=h.stage(capture,ctx)
    capture["inputs"]["cascade"]["themes"][0]["language_accel"]=999.0
    rehash(capture)
    _,raw=h.retention.prepare(capture,native_run_id=ctx.run_id,producer_commit=ctx.commit)
    (ctx.directory/"capture.json").write_bytes(raw)
    monkeypatch.setattr(h.retention,"runtime_store",lambda:pytest.fail("no store for substituted original bytes"))
    with pytest.raises(h.retention.CaptureRefused,match="original stage digest"): submit_staged(repo,env,staged)

@pytest.mark.parametrize("replacement",["capture","chained_capture_field"])
def test_artifact_path_rejects_payload_or_nested_capture(invocation,capture,replacement):
    repo,runner,env=invocation;ctx=h.begin(repo,environ=env);staged=h.stage(capture,ctx)
    path=ctx.directory/("native-divergence-"+h.retention.digest(ctx.run_id.encode())+".jsonl")
    if replacement=="capture":
        path.write_bytes((ctx.directory/"capture.json").read_bytes());path.chmod(0o600)
    else:
        evidence=FileGenerationEvidence.create(path,{"source_commit":COMMIT,"run":ctx.run_id})
        evidence.append("terminal",{"state":"UNRESOLVED","write_intent_durable":False,
            "key":h.retention.key_for_run(ctx.run_id),"sha256":staged["payload_sha256"],"capture":capture})
        evidence.close()
    with pytest.raises((EvidenceUnavailable,h.retention.CaptureRefused)):
        h.journal_path(repo,expected_payload_sha256=staged["payload_sha256"],original_producer_commit=staged["producer_commit"],environ=env)

def test_committed_source_binding_rejects_dirty_bytes_without_head_change(tmp_path,monkeypatch):
    import subprocess
    repo=tmp_path/"synthetic";repo.mkdir();source=repo/"native.py";source.write_text("value = 1\n")
    def git(*args): return subprocess.run(["git","-C",str(repo),*args],check=True,capture_output=True).stdout
    git("init","-q");git("add","native.py")
    git("-c","user.name=Fixture","-c","user.email=fixture@example.invalid","commit","-qm","synthetic source")
    monkeypatch.setattr(h,"SOURCE_PATHS",("native.py",))
    before=h._source_binding(repo);source.write_text("value = 2\n")
    assert h._head(repo)==before[0]
    with pytest.raises(h.retention.CaptureRefused,match="committed bytes"): h._source_binding(repo)

def test_later_head_drift_blocks_submission_but_preserves_original_journal(invocation,capture,production_store,monkeypatch):
    repo,runner,env=invocation;ctx=h.begin(repo,environ=env);staged=h.stage(capture,ctx)
    assert submit_staged(repo,env,staged).state=="COMMITTED_OBSERVED"
    monkeypatch.setattr(h,"_head",lambda repo:"b"*40)
    with pytest.raises(h.retention.CaptureRefused,match="source mismatch"): submit_staged(repo,env,staged)
    assert h.journal_path(repo,expected_payload_sha256=staged["payload_sha256"],original_producer_commit=COMMIT,environ=env) is not None
    assert len(production_store.puts)==1


"""One-computation composition and existing-workflow boundary tests; synthetic only."""
import copy
import importlib.util
import subprocess
from pathlib import Path
import pytest
import yaml
from scripts import publish_native_divergence_capture as publisher

def computed_board(capture,calls):
    def native(cascade,activity,**kwargs):
        calls.append((cascade,activity,kwargs.copy()))
        sink=kwargs.get("provenance_sink")
        if sink is not None: sink.update(copy.deepcopy(capture))
        return {"same_board":True}
    return native

def stage_outputs(path):
    return dict(line.split("=",1) for line in path.read_text().splitlines())

def test_ordinary_computation_emits_only_original_digests_once(invocation,capture):
    repo,runner,env=invocation;output=runner/"step-output";output.touch();env["GITHUB_OUTPUT"]=str(output)
    calls=[];board=h.compute_with_capture({}, {},repo_root=repo,compute=computed_board(capture,calls),environ=env)
    assert board=={"same_board":True} and len(calls)==1 and calls[0][2]["write_ledger"] is True
    outputs=stage_outputs(output)
    assert set(outputs)=={"native_divergence_payload_sha256","native_divergence_source_sha256","native_divergence_producer_commit"}
    staged=next(runner.glob("native-divergence-*/capture.json"))
    assert h.retention.digest(staged.read_bytes())==outputs["native_divergence_payload_sha256"]
    assert "capture" not in output.read_text() and list(repo.iterdir())==[]

@pytest.mark.parametrize("failure",["before_compute","output_unavailable","render"])
def test_auxiliary_failure_never_recomputes_or_changes_return(invocation,capture,monkeypatch,failure):
    repo,runner,env=invocation;calls=[]
    if failure=="before_compute":
        monkeypatch.setattr(h,"begin",lambda *a,**k:(_ for _ in ()).throw(OSError("sensitive failure")))
    if failure=="render": env["RENDER_NO_DRIP"]="1"
    board=h.compute_with_capture({}, {},repo_root=repo,compute=computed_board(capture,calls),environ=env)
    assert board=={"same_board":True} and len(calls)==1
    if failure!="output_unavailable":
        assert "provenance_sink" not in calls[0][2] and list(runner.iterdir())==[]
    else: assert len(list(runner.glob("native-divergence-*/capture.json")))==1

def test_publish_existing_capture_once_and_retain_only_closed_journal(invocation,capture,production_store,capsys):
    repo,runner,env=invocation;output=runner/"step-output";output.touch();env["GITHUB_OUTPUT"]=str(output)
    h.compute_with_capture({}, {},repo_root=repo,compute=computed_board(capture,[]),environ=env)
    outputs=stage_outputs(output)
    env["NATIVE_DIVERGENCE_PAYLOAD_SHA256"]=outputs["native_divergence_payload_sha256"]
    env["NATIVE_DIVERGENCE_SOURCE_SHA256"]=outputs["native_divergence_source_sha256"]
    env["NATIVE_DIVERGENCE_PRODUCER_COMMIT"]=outputs["native_divergence_producer_commit"]
    production_store.write_mode="lost_absent"
    assert publisher.main(repo_root=repo,environ=env)==1
    assert len(production_store.puts)==1 and "EFFECT_UNKNOWN" in capsys.readouterr().out
    journal=Path(stage_outputs(output)["native_divergence_journal"])
    assert journal.suffix==".jsonl" and journal.stat().st_size<32768
    assert "axis_computations" not in journal.read_text()
    assert publisher.main(repo_root=repo,environ=env)==1
    assert len(production_store.puts)==1

def test_publisher_without_stage_has_no_store_or_native_action(invocation,monkeypatch):
    repo,runner,env=invocation
    monkeypatch.setattr(h,"retain_staged",lambda *a,**k:pytest.fail("no submission without original stage"))
    assert publisher.main(repo_root=repo,environ=env)==0 and list(runner.iterdir())==[]

def workflow():
    return yaml.safe_load((ROOT / ".github/workflows/daily.yml").read_text())

def test_workflow_uses_existing_private_step_and_metadata_artifact():
    current=workflow(); steps=current["jobs"]["engine"]["steps"]
    publish=next(s for s in steps if s.get("id")=="native_private_publish")
    assert publish["name"]=="publish Filing Forensics private state"
    incumbent_keys={"R2_ENDPOINT","R2_ACCESS_KEY_ID","R2_SECRET_ACCESS_KEY",
                    "R2_RESEARCH_ENDPOINT","R2_RESEARCH_ACCESS_KEY_ID",
                    "R2_RESEARCH_SECRET_ACCESS_KEY","R2_RESEARCH_BUCKET"}
    assert {k:v for k,v in publish["env"].items() if not k.startswith("NATIVE_DIVERGENCE_")} == {
        key: "${{ secrets."+key+" }}" for key in incumbent_keys}
    assert {k for k in publish["env"] if k.startswith("NATIVE_DIVERGENCE_")} == {
        "NATIVE_DIVERGENCE_PAYLOAD_SHA256","NATIVE_DIVERGENCE_SOURCE_SHA256","NATIVE_DIVERGENCE_PRODUCER_COMMIT"}
    engine=next(s for s in steps if s.get("id")=="regime_dashboard")
    assert not any(k.startswith("R2_RESEARCH_") for k in engine["env"])
    assert current["jobs"]["engine"]["env"]["COLLECT_LANE"]=="nightly"
    artifacts=[s for s in steps if s.get("name","")=="retain this run's native divergence journal (metadata only)"]
    assert len(artifacts)==1
    artifact=artifacts[0]
    assert artifact["with"]["path"]=="${{ steps.native_private_publish.outputs.native_divergence_journal }}"
    assert artifact["with"]["retention-days"]==14
    assert artifact["uses"]=="actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"
    subprocess.run(["bash","-n"],input=publish["run"],text=True,check=True)

@pytest.mark.parametrize("forensics_rc,capture_rc",[(1,0),(0,1)])
def test_existing_forensics_exit_status_preserved(tmp_path,forensics_rc,capture_rc):
    new=workflow();script=next(s["run"] for s in new["jobs"]["engine"]["steps"] if s.get("id")=="native_private_publish")
    script=script.replace("python -m scripts.build_fundamental_forensics --publish-only",f"(exit {forensics_rc})")
    script=script.replace("python -m scripts.publish_native_divergence_capture",f"(exit {capture_rc})")
    result=subprocess.run(["bash","-e"],input=script,text=True,capture_output=True)
    assert result.returncode==forensics_rc

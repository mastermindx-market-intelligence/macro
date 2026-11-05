"""Controlled S2 owner tests. No production bootstrap, rights or natural claim."""
import json
from pathlib import Path
import pytest
from engine.neuralweb import thematic_state as legacy
from scripts import build_thematic_state as builder

HISTORY = "data/neuralweb/theme_phase_history.jsonl"
PRIMARY = "data/neuralweb/theme_state.json"
MIRROR = "site/neuralwebdata/theme_state.json"

def artifact(date="2026-10-03", stage="WATCH", ids=("a",)):
    return {"schema":"neuralweb.theme_state.v1","as_of":date,"themes":[
        {"theme_id":tid,"foresight":{"stage":stage},"basket_intel":[{"label":None,"crowding":0}],
         "radar":None,"divergence_board":None} for tid in ids]}

def put(root, path, raw):
    target=root/path
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(raw)
    return target

@pytest.fixture(autouse=True)
def nightly(monkeypatch):
    monkeypatch.setenv("COLLECT_LANE","nightly")

@pytest.mark.parametrize("raw",[b"{broken\n",b"null\n",b'{"schema":"foreign","theme_id":"a","as_of":"2026-10-03"}\n'])
def test_prior_history_refusal(raw,tmp_path):
    p=put(tmp_path,HISTORY,raw)
    with pytest.raises(Exception):
        legacy.append_phase_history(tmp_path,artifact())
    assert p.read_bytes()==raw

def test_builder_history_guard_before_primary(tmp_path,monkeypatch):
    put(tmp_path,PRIMARY,b"old-primary")
    put(tmp_path,MIRROR,b"old-mirror")
    p=put(tmp_path,HISTORY,b"{broken\n")
    monkeypatch.setattr(builder,"compose",lambda **kw:artifact())
    assert builder.build(tmp_path)!=0
    assert (tmp_path/PRIMARY).read_bytes()==b"old-primary"
    assert (tmp_path/MIRROR).read_bytes()==b"old-mirror"
    assert p.read_bytes()==b"{broken\n"

def test_duplicate_incoming_ids_refuse(tmp_path):
    with pytest.raises(Exception):
        legacy.append_phase_history(tmp_path,artifact(ids=("a","a")))
    assert not (tmp_path/HISTORY).exists()

def test_nonnightly_has_no_directory_effect(tmp_path,monkeypatch):
    monkeypatch.setenv("COLLECT_LANE","intraday")
    assert legacy.append_phase_history(tmp_path,artifact())==0
    assert list(tmp_path.iterdir())==[]

def test_last_line_without_lf_preserves_prefix(tmp_path):
    legacy.append_phase_history(tmp_path,artifact())
    p=tmp_path/HISTORY
    prefix=p.read_bytes().rstrip(b"\n")
    p.write_bytes(prefix)
    assert legacy.append_phase_history(tmp_path,artifact("2026-10-04","NEW"))==1
    raw=p.read_bytes()
    assert raw.startswith(prefix+b"\n")
    assert len([json.loads(line) for line in raw.splitlines()])==2

def test_controlled_fresh_root_positive(tmp_path):
    assert legacy.append_phase_history(tmp_path,artifact())==1
    assert legacy.append_phase_history(tmp_path,artifact())==0

from engine.neuralweb import theme_state_generation as g
from tests.test_theme_state_production import production_world, compose, EMITTED

class AcceptedFixture(g.ControlledOwnerVerifier):
    def __init__(self): self.revoked=False; self.calls=[]
    def current_action_at(self,plan,*,action):
        # Explicit synthetic action clock, independent of production wall time.
        return plan["activation_at"]
    def resolve(self,plan,*,action):
        self.calls.append(action)
        return g.ControlledDecision(plan["root"],plan["generation_id"],action,plan["activation_at"],
            "REVOKED" if self.revoked else "ACCEPTED","synthetic-existing-owner-action-fixture")

@pytest.fixture
def prepared(production_world):
    bundle,result=compose(production_world)
    entry=g.entry_preflight(production_world,legacy_api=True)
    plan=g.prepare_generation(bundle,root=production_world,generated_at=EMITTED,activation_at=EMITTED,entry=entry)
    return production_world,bundle,plan

def test_actual_s1_delegation_and_distinct_stamp_scopes(prepared):
    root,bundle,plan=prepared
    state=g.validate_generation(plan)
    assert state["bundle_ref"]["sha256"]==bundle.bundle_sha256
    assert state["authority_caps"]["may_publish"] is False
    assert state["materialization_allowed"] is False
    assert plan["publication_status"]=="UNAVAILABLE"
    assert plan["digests"]["projection_unstamped"]!=plan["digests"]["projection_stamped"]
    assert g.read(root,g.CURRENT) is None

@pytest.mark.parametrize("authority",[None,True,"accepted",{},object()])
def test_arbitrary_authority_cannot_publish(prepared,authority):
    root,_,plan=prepared
    before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob("*") if p.is_file()}
    with pytest.raises(g.GenerationUnavailable):
        g.publish_generation(root,plan,controlled_verifier=authority)
    assert before=={str(p.relative_to(root)):p.read_bytes() for p in root.rglob("*") if p.is_file()}

def test_controlled_sealed_generation_ref_last_idempotent(prepared):
    root,_,plan=prepared
    stages=[]
    def observe(stage):
        stages.append(stage)
        if stage!="ref": assert g.read(root,g.CURRENT) is None
    verdict=g.publish_generation(root,plan,controlled_verifier=AcceptedFixture(),fault=observe)
    assert verdict["status"]=="CONTROLLED_ACCEPTED"
    assert stages==["stage","seal","primary","mirror","tail","ref"]
    assert g.read(root,g.PRIMARY)==g.read(root,g.MIRROR)==g.unb64(plan["compatibility_b64"])
    prefix=g.read(root,g.HISTORY)
    assert g.publish_generation(root,plan,controlled_verifier=AcceptedFixture())["status"]=="ALREADY_ACCEPTED"
    assert g.read(root,g.HISTORY)==prefix
    g.entry_preflight(root)

@pytest.mark.parametrize("point",["seal","primary","mirror","tail","ref"])
def test_each_sealed_failure_resumes_original_plan(prepared,point):
    root,_,plan=prepared
    def fault(stage):
        if stage==point: raise RuntimeError("controlled crash:"+point)
    with pytest.raises(RuntimeError):
        g.publish_generation(root,plan,controlled_verifier=AcceptedFixture(),fault=fault)
    sealed=g.read(root,g.GENERATIONS+"/"+plan["generation_id"]+"/plan.json")
    assert sealed==g.canonical(plan)
    assert g.resume_generation(root,plan,controlled_verifier=AcceptedFixture())["status"]=="CONTROLLED_ACCEPTED"
    assert g.read(root,g.HISTORY)==g.unb64(plan["history_b64"])+g.unb64(plan["tail_b64"])
    assert g.read(root,g.GENERATIONS+"/"+plan["generation_id"]+"/plan.json")==sealed

def test_unsealed_stage_orphan_refuses_resume(prepared):
    root,_,plan=prepared
    def fault(stage):
        if stage=="stage": raise RuntimeError("unsealed")
    with pytest.raises(RuntimeError):
        g.publish_generation(root,plan,controlled_verifier=AcceptedFixture(),fault=fault)
    before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob("*") if p.is_file()}
    with pytest.raises(g.GenerationUnavailable,match="ORIGINAL_SEALED_PLAN_UNAVAILABLE"):
        g.resume_generation(root,plan,controlled_verifier=AcceptedFixture())
    assert before=={str(p.relative_to(root)):p.read_bytes() for p in root.rglob("*") if p.is_file()}

@pytest.mark.parametrize("target",["history","primary","mirror","ref","plan"])
def test_resume_foreign_or_partial_bytes_refuse(prepared,target):
    root,_,plan=prepared
    def fault(stage):
        if stage=="seal":raise RuntimeError("pause")
    with pytest.raises(RuntimeError):
        g.publish_generation(root,plan,controlled_verifier=AcceptedFixture(),fault=fault)
    paths={"history":g.HISTORY,"primary":g.PRIMARY,"mirror":g.MIRROR,"ref":g.CURRENT,
           "plan":g.GENERATIONS+"/"+plan["generation_id"]+"/plan.json"}
    p=put(root,paths[target],b"foreign-or-partial")
    before=p.read_bytes()
    with pytest.raises(g.GenerationUnavailable):
        g.resume_generation(root,plan,controlled_verifier=AcceptedFixture())
    assert p.read_bytes()==before

def test_pending_transaction_refuses_direct_appender(prepared):
    root,_,plan=prepared
    def fault(stage):
        if stage=="seal":raise RuntimeError
    with pytest.raises(RuntimeError):
        g.publish_generation(root,plan,controlled_verifier=AcceptedFixture(),fault=fault)
    with pytest.raises(g.GenerationUnavailable,match="PENDING_GENERATION"):
        legacy.append_phase_history(root,artifact())
    assert g.read(root,g.CURRENT) is None

def test_revocation_between_prepare_publish_and_resume(prepared):
    root,_,plan=prepared
    authority=AcceptedFixture();authority.revoked=True
    with pytest.raises(g.GenerationUnavailable,match="REJECTED"):
        g.publish_generation(root,plan,controlled_verifier=authority)
    assert g.read(root,g.PENDING) is None
    authority.revoked=False
    def fault(stage):
        if stage=="seal":raise RuntimeError
    with pytest.raises(RuntimeError):
        g.publish_generation(root,plan,controlled_verifier=authority,fault=fault)
    authority.revoked=True
    with pytest.raises(g.GenerationUnavailable,match="REJECTED"):
        g.resume_generation(root,plan,controlled_verifier=authority)
    assert g.read(root,g.CURRENT) is None

def test_backdated_native_frontier_and_optional_nulls(tmp_path):
    now="2026-10-04T12:00:00Z"
    history=g.preflight_phase_history(b"")
    rows=[]
    for date,stage in [("2026-10-03","A"),("2026-10-05","B"),("2026-10-04","C"),("2026-10-06","D")]:
        tail,_=g.plan_phase_history(artifact(date,stage,("a","b")),history,recorded_at=now)
        history=g.preflight_phase_history(history.raw+tail)
    a=[r for r in history.rows if r["theme_id"]=="a"]
    assert a[1]["prev_hash"]==legacy._row_hash(a[0])
    assert a[2]["prev_hash"]==a[3]["prev_hash"]==legacy._row_hash(a[1])
    assert a[0]["evidence_z"]["crowding"]==0
    # Optional fields participate in native hash without normalization.
    first=a[0]|{"optional":{"native_null":None}}
    second=a[1]|{"prev_hash":legacy._row_hash(first)}
    raw=g.canonical(first)+b"\r\n  "+g.canonical(second)+b"\r\n"
    assert g.preflight_phase_history(raw).raw==raw

@pytest.mark.parametrize("same",[True,False])
def test_identical_and_conflicting_prior_daily_duplicate_refuse(tmp_path,same):
    legacy.append_phase_history(tmp_path,artifact())
    raw=(tmp_path/HISTORY).read_bytes()
    duplicate=json.loads(raw)
    if not same: duplicate["foresight_stage"]="changed"
    raw+=g.canonical(duplicate)+b"\n"
    with pytest.raises(g.GenerationUnavailable,match="DUPLICATE"):
        g.preflight_phase_history(raw)

def test_history_entry_cas_before_effect(tmp_path):
    entry=g.entry_preflight(tmp_path,legacy_api=True)
    put(tmp_path,HISTORY,b"")
    with pytest.raises(g.GenerationUnavailable,match="CAS"):
        g.cas_entry(tmp_path,entry)
    assert not (tmp_path/g.LOCK).exists()

def test_missing_known_prior_and_unavailable_bootstrap(tmp_path):
    put(tmp_path,g.CURRENT,b"prior-reference")
    with pytest.raises(g.GenerationUnavailable,match="HISTORY_MISSING"):
        g.entry_preflight(tmp_path,legacy_api=True)
    other=tmp_path/"new"
    with pytest.raises(g.GenerationUnavailable,match="FIRST_FAMILY_AUTHORITY_UNAVAILABLE"):
        g.entry_preflight(other)
    assert not other.exists()

def test_fixed_path_symlink_preserves_external_sentinel(prepared,tmp_path):
    root,_,plan=prepared
    outside=tmp_path/"outside";outside.mkdir()
    sentinel=outside/"sentinel";sentinel.write_bytes(b"preserve")
    parent=root/"site/neuralwebdata"
    parent.mkdir(parents=True,exist_ok=True)
    parent.rmdir()
    parent.symlink_to(outside,target_is_directory=True)
    with pytest.raises(g.GenerationUnavailable,match="SYMLINK"):
        g.publish_generation(root,plan,controlled_verifier=AcceptedFixture())
    assert sentinel.read_bytes()==b"preserve"
    assert not (outside/"theme_state.json").exists()

def test_real_cross_process_owner_exclusivity(tmp_path):
    import subprocess,sys
    from contextlib import contextmanager
    root=tmp_path/"fixture";root.mkdir()
    with g.family_lock(root):
        code="from pathlib import Path; from engine.neuralweb.theme_state_generation import family_lock;\nwith family_lock(Path("+repr(str(root))+")): pass"
        result=subprocess.run([sys.executable,"-c",code],capture_output=True,text=True)
        assert result.returncode!=0 and "OWNER_BUSY" in result.stderr
    with g.family_lock(root): pass

def test_shadow_zero_family_effect_and_successor_rights_hold(production_world):
    root=production_world
    bundle,_=compose(root)
    before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob("*") if p.is_file()}
    assert builder.build(root,mode="SHADOW",bundle=bundle,generated_at=EMITTED)==0
    assert builder.build(root,mode="SUCCESSOR",bundle=bundle,generated_at=EMITTED)==1
    assert before=={str(p.relative_to(root)):p.read_bytes() for p in root.rglob("*") if p.is_file()}

def test_main_suppresses_optional_on_shadow_and_failure(tmp_path,monkeypatch):
    import sys
    calls=[]
    monkeypatch.setattr(builder,"run_optional_stages",lambda root:calls.append(root))
    monkeypatch.setattr(builder,"build",lambda root,**kw:0)
    monkeypatch.setattr(sys,"argv",["build","--root",str(tmp_path),"--mode","SHADOW"])
    with pytest.raises(SystemExit) as result:builder.main()
    assert result.value.code==0 and calls==[]
    monkeypatch.setattr(builder,"build",lambda root,**kw:1)
    monkeypatch.setattr(sys,"argv",["build","--root",str(tmp_path)])
    with pytest.raises(SystemExit) as result:builder.main()
    assert result.value.code==1 and calls==[]

def reseal(plan):
    plan["generation_id"]="tsg-"+g._plan_digest(plan)
    return plan

def test_same_day_linked_correction_no_counterfeit_tape(prepared):
    root,bundle,first=prepared
    g.publish_generation(root,first,controlled_verifier=AcceptedFixture())
    prefix=g.read(root,g.HISTORY)
    entry=g.entry_preflight(root)
    bundle,_=compose(root)  # new operation captures the actual accepted frontier
    second=g.prepare_generation(bundle,root=root,generated_at="2026-10-04T12:01:00Z",
        activation_at="2026-10-04T12:01:00Z",entry=entry,correction_reason="controlled later-known owner correction")
    state=g.validate_generation(second)
    assert state["correction"]["previous"]["state_sha256"]==g.validate_generation(first)["state_sha256"]
    assert second["history_rows_added"]==0 and g.unb64(second["tail_b64"])==b""
    g.publish_generation(root,second,controlled_verifier=AcceptedFixture())
    assert g.read(root,g.HISTORY)==prefix
    assert first["generation_id"]!=second["generation_id"]

def test_rollback_keeps_current_tape_and_old_emission(prepared):
    root,bundle,first=prepared
    authority=AcceptedFixture()
    g.publish_generation(root,first,controlled_verifier=authority)
    bundle,_=compose(root)  # new operation captures the actual accepted frontier
    second=g.prepare_generation(bundle,root=root,generated_at="2026-10-04T12:01:00Z",
        activation_at="2026-10-04T12:01:00Z",entry=g.entry_preflight(root),correction_reason="controlled correction")
    g.publish_generation(root,second,controlled_verifier=authority)
    tape=g.read(root,g.HISTORY)
    authority.revoked=True
    with pytest.raises(g.GenerationUnavailable,match="REJECTED"):
        g.rollback_generation(root,first["generation_id"],activation_at="2026-10-04T12:02:00Z",controlled_verifier=authority)
    assert g.read(root,g.CURRENT)==g._reference(second)
    authority.revoked=False
    result=g.rollback_generation(root,first["generation_id"],activation_at="2026-10-04T12:02:00Z",controlled_verifier=authority)
    ref=g.parse(g.read(root,g.CURRENT))
    rollback=g._validate_ref(root,ref)
    assert result["generation_id"]==rollback["generation_id"]
    assert g.validate_generation(rollback)["generated_at"]==g.validate_generation(first)["generated_at"]
    assert rollback["rollback_selection"]["history_sha256"]==g.sha(g.unb64(first["history_b64"])+g.unb64(first["tail_b64"]))
    assert g.read(root,g.HISTORY)==tape
    assert g.read(root,g.PRIMARY)==g.unb64(first["compatibility_b64"])
    assert g.read(root,g.GENERATIONS+"/"+first["generation_id"]+"/plan.json")==g.canonical(first)
    # Next normal plan continues from activation, not the selected old frontier.
    bundle,_=compose(root)  # capture current rollback frontier, never reuse stale input
    next_plan=g.prepare_generation(bundle,root=root,generated_at="2026-10-04T12:03:00Z",
        activation_at="2026-10-04T12:03:00Z",entry=g.entry_preflight(root))
    assert next_plan["prior_reference_b64"]==g.b64(g.read(root,g.CURRENT))

@pytest.mark.parametrize("field,value",[
    ("history_rows_added",99),("history_exists",False),("root","/foreign"),
    ("activation_at","2026-10-04T11:59:00Z"),("rollback_of","tsg-"+"f"*64)])
def test_rehashed_plan_relational_tamper(prepared,field,value):
    import copy
    root,_,plan=prepared
    bad=copy.deepcopy(plan)
    if field=="history_exists":
        bad["history_b64"]=g.b64(g.unb64(plan["tail_b64"]))
        bad["digests"]["history_prefix"]=g.sha(g.unb64(bad["history_b64"]))
        bad["tail_b64"]=g.b64(b"")
        bad["digests"]["history_tail"]=g.sha(b"")
        bad["history_rows_added"]=0
    bad[field]=value;reseal(bad)
    with pytest.raises(g.GenerationUnavailable):
        if field=="root":g.publish_generation(root,bad,controlled_verifier=AcceptedFixture())
        else:g.validate_generation(bad)

def test_legacy_frontier_cannot_self_bootstrap_successor(prepared):
    root,bundle,plan=prepared
    put(root,g.HISTORY,g.unb64(plan["tail_b64"]))
    put(root,g.PRIMARY,b"old");put(root,g.MIRROR,b"old")
    entry=g.entry_preflight(root,legacy_api=True)
    with pytest.raises(g.GenerationUnavailable,match="LEGACY_FRONTIER_AUTHORITY_UNAVAILABLE"):
        g.prepare_generation(bundle,root=root,generated_at=EMITTED,activation_at=EMITTED,entry=entry)

def test_orphan_generation_cannot_be_adopted(prepared):
    root,_,plan=prepared
    p=root/g.GENERATIONS/("tsg-"+"f"*64);p.mkdir(parents=True)
    sentinel=p/"unowned";sentinel.write_bytes(b"retain")
    with pytest.raises(g.GenerationUnavailable,match="ORPHAN"):
        g.publish_generation(root,plan,controlled_verifier=AcceptedFixture())
    assert sentinel.read_bytes()==b"retain"
    assert g.read(root,g.PENDING) is None

def test_lost_sealed_plan_never_recaptures(prepared,monkeypatch):
    root,_,plan=prepared
    def fault(stage):
        if stage=="seal":raise RuntimeError
    with pytest.raises(RuntimeError):
        g.publish_generation(root,plan,controlled_verifier=AcceptedFixture(),fault=fault)
    (root/g.GENERATIONS/plan["generation_id"]/"plan.json").unlink()
    from engine.neuralweb import theme_state_adapter
    monkeypatch.setattr(theme_state_adapter,"capture_owner_bundle",lambda *a,**kw:pytest.fail("recapture"))
    with pytest.raises(g.GenerationUnavailable,match="ORIGINAL_SEALED"):
        g.resume_generation(root,plan,controlled_verifier=AcceptedFixture())

def test_unreadable_history_never_makes_lock_or_output(tmp_path,monkeypatch):
    put(tmp_path,HISTORY,b"")
    actual=Path.read_bytes
    def unreadable(path):
        if path==tmp_path/HISTORY:raise PermissionError("controlled unreadable")
        return actual(path)
    monkeypatch.setattr(Path,"read_bytes",unreadable)
    assert builder.build(tmp_path)==1
    assert not (tmp_path/g.LOCK).exists()
    assert not (tmp_path/PRIMARY).exists()

@pytest.mark.parametrize("replacement",[True,float("nan"),"0"])
def test_history_evidence_strict_types_and_nonfinite(tmp_path,replacement):
    legacy.append_phase_history(tmp_path,artifact())
    row=json.loads((tmp_path/HISTORY).read_bytes())
    row["evidence_z"]["crowding"]=replacement
    with pytest.raises(g.GenerationUnavailable):
        g.preflight_phase_history(json.dumps(row).encode()+b"\n")

def test_stamp_once_before_seal_and_no_stamp_on_resume(production_world,monkeypatch):
    from engine.neuralweb import envelope
    actual=envelope.stamp;calls=[]
    def stamp(*args,**kw):
        calls.append(1);return actual(*args,**kw)
    monkeypatch.setattr(envelope,"stamp",stamp)
    bundle,_=compose(production_world)
    plan=g.prepare_generation(bundle,root=production_world,generated_at=EMITTED,activation_at=EMITTED,
        entry=g.entry_preflight(production_world,legacy_api=True))
    assert calls==[1]
    def fault(stage):
        if stage=="seal":raise RuntimeError
    with pytest.raises(RuntimeError):
        g.publish_generation(production_world,plan,controlled_verifier=AcceptedFixture(),fault=fault)
    g.resume_generation(production_world,plan,controlled_verifier=AcceptedFixture())
    assert calls==[1]

def test_pending_race_at_entry_cas_refuses(tmp_path):
    entry=g.entry_preflight(tmp_path,legacy_api=True)
    put(tmp_path,g.PENDING,b"dispatched-other-plan")
    with pytest.raises(g.GenerationUnavailable,match="PENDING"):
        g.cas_entry(tmp_path,entry)
    assert not (tmp_path/PRIMARY).exists()

def test_nonnightly_controlled_publication_refuses_before_effect(prepared,monkeypatch):
    root,_,plan=prepared
    monkeypatch.setenv("COLLECT_LANE","intraday")
    with pytest.raises(g.GenerationUnavailable,match="NIGHTLY"):
        g.publish_generation(root,plan,controlled_verifier=AcceptedFixture())
    assert g.read(root,g.PENDING) is None and g.read(root,g.CURRENT) is None

@pytest.mark.parametrize("bad",["echo","bool","future","wrong_scope","wrong_event","revoked"])
def test_owner_fixture_refusal_distinctions(prepared,bad):
    root,_,plan=prepared
    class Broken(g.ControlledOwnerVerifier):
        def resolve(self,p,*,action):
            if bad=="echo":return p
            if bad=="bool":return True
            return g.ControlledDecision(p["root"],"tsg-"+"f"*64 if bad=="wrong_scope" else p["generation_id"],
                action,"2026-10-04T13:00:00Z" if bad=="future" else p["activation_at"],
                "REVOKED" if bad=="revoked" else "ACCEPTED",True if bad=="wrong_event" else "fixture")
    with pytest.raises(g.GenerationUnavailable):
        g.publish_generation(root,plan,controlled_verifier=Broken())
    assert g.read(root,g.PENDING) is None

def test_two_processes_same_sealed_plan_cannot_both_advance(prepared):
    import subprocess,sys
    root,_,plan=prepared
    children=[]
    def fault(stage):
        if stage!="seal":return
        code="""import json,sys
from pathlib import Path
from engine.neuralweb import theme_state_generation as g
class V(g.ControlledOwnerVerifier):
 def current_action_at(self,p,*,action):return p['activation_at']  # controlled child clock
 def resolve(self,p,*,action):
  return g.ControlledDecision(p['root'],p['generation_id'],action,p['activation_at'],'ACCEPTED','fixture')
p=json.loads(Path(sys.argv[1]).read_text())
g.resume_generation(Path(p['root']),p,controlled_verifier=V())
"""
        child=subprocess.run([sys.executable,"-c",code,str(root/g.GENERATIONS/plan["generation_id"]/"plan.json")],
            capture_output=True,text=True)
        children.append(child)
        assert child.returncode!=0 and "OWNER_BUSY" in child.stderr
    g.publish_generation(root,plan,controlled_verifier=AcceptedFixture(),fault=fault)
    assert len(children)==1
    assert len(g.preflight_phase_history(g.read(root,g.HISTORY)).rows)==plan["history_rows_added"]

def test_rehashed_foreign_tail_cannot_change_native_meaning(prepared):
    import copy
    _,_,plan=prepared
    bad=copy.deepcopy(plan)
    rows=[json.loads(line) for line in g.unb64(bad["tail_b64"]).splitlines()]
    rows[0]["foresight_stage"]="caller changed"
    tail=b"\n".join(g.canonical(row) for row in rows)+b"\n"
    bad["tail_b64"]=g.b64(tail);bad["digests"]["history_tail"]=g.sha(tail);reseal(bad)
    with pytest.raises(g.GenerationUnavailable,match="NATIVE_PLAN"):
        g.validate_generation(bad)

def test_strict_reference_numeric_boolean_and_digest_refuse():
    ref={"schema":"neuralweb.theme_state_current.v1","generation_id":"tsg-"+"a"*64,
         "plan_sha256":"a"*64,"history_sha256":"b"*64,"history_length":False,"activation_at":EMITTED}
    with pytest.raises(g.GenerationUnavailable):
        g._validate_reference_shape(ref)

def test_rollback_after_real_controlled_tape_advance(prepared,monkeypatch):
    root,bundle,first=prepared
    authority=AcceptedFixture()
    g.publish_generation(root,first,controlled_verifier=authority)
    # Controlled native transition is new input, not a changed sealed generation.
    source=root/legacy._FORESIGHT_PATH
    value=json.loads(source.read_text())
    value["themes"][0]["stage"]="RE-RATING"
    value["asof"]="2026-10-05"
    source.write_text(json.dumps(value))
    from engine.neuralweb import theme_state_adapter as adapter
    # Next controlled daily emission, not a claimed natural observation.
    newer=adapter.capture_owner_bundle(root,effective_at="2026-10-05",known_at="2026-10-05T12:03:00Z")
    second=g.prepare_generation(newer,root=root,generated_at="2026-10-05T12:03:00Z",
        activation_at="2026-10-05T12:03:00Z",entry=g.entry_preflight(root))
    assert second["history_rows_added"] > 0
    g.publish_generation(root,second,controlled_verifier=authority)
    tape=g.read(root,g.HISTORY)
    assert tape.startswith(g.unb64(first["tail_b64"])) and len(tape)>len(g.unb64(first["tail_b64"]))
    g.rollback_generation(root,first["generation_id"],activation_at="2026-10-05T12:04:00Z",controlled_verifier=authority)
    plan=g._validate_ref(root,g.parse(g.read(root,g.CURRENT)))
    assert g.read(root,g.HISTORY)==tape
    assert plan["history_b64"]==g.b64(tape)
    assert plan["rollback_selection"]["history_sha256"]==g.sha(g.unb64(first["history_b64"])+g.unb64(first["tail_b64"]))

# Independent review B1-B4 owning regressions. All owner decisions are synthetic.
def test_review_captured_A_entry_B_refuses(production_world):
    from engine.neuralweb import theme_state_adapter as adapter
    root=production_world
    put(root,g.HISTORY,b'')
    old=artifact(ids=('grid',)) | {'owner_extra':'CAPTURED_A'}
    put(root,g.PRIMARY,g.canonical(old))
    bundle,_=compose(root)
    newer=old | {'owner_extra':'ENTRY_B'}
    put(root,g.PRIMARY,g.canonical(newer));put(root,g.MIRROR,g.canonical(newer))
    entry=g.entry_preflight(root,legacy_api=True)
    with pytest.raises(g.GenerationUnavailable,match='CAPTURED_LEGACY_FRONTIER_MISMATCH'):
        g.prepare_generation(bundle,root=root,generated_at=EMITTED,activation_at=EMITTED,entry=entry)
    assert g.read(root,g.PRIMARY)==g.canonical(newer)
    assert g.read(root,g.MIRROR)==g.canonical(newer)
    assert g.read(root,g.PENDING) is None and g.read(root,g.LOCK) is None

def test_review_missing_capture_existing_empty_history_refuses(production_world):
    root=production_world;bundle,_=compose(root)
    assert bundle.snapshot()['sources']['legacy_phase_history']['availability']=='UNAVAILABLE'
    put(root,g.HISTORY,b'')
    with pytest.raises(g.GenerationUnavailable,match='CAPTURED_LEGACY_FRONTIER_MISMATCH'):
        g.prepare_generation(bundle,root=root,generated_at=EMITTED,activation_at=EMITTED,
            entry=g.entry_preflight(root,legacy_api=True))
    assert g.read(root,g.HISTORY)==b'' and g.read(root,g.PENDING) is None

@pytest.mark.parametrize('target',['helper','schema','unchanged'])
def test_review_changed_disposable_version_refuses_same_sealed_plan(prepared,tmp_path,target):
    import importlib.util,sys
    root,_,plan=prepared
    def pause(stage):
        if stage=='seal':raise RuntimeError('pause')
    with pytest.raises(RuntimeError):g.publish_generation(root,plan,controlled_verifier=AcceptedFixture(),fault=pause)
    clone=tmp_path/'disposable';helper=clone/'engine/neuralweb/theme_state_generation.py'
    helper.parent.mkdir(parents=True)
    text=Path(g.__file__).read_text()
    if target=='helper':
        text=text.replace('if tail != expected_tail or plan["history_rows_added"] != expected_count:',
                          'if False:  # controlled material native-tail-policy drift')
    helper.write_text(text)
    schema=clone/'contracts/theme_graph/theme_state_generation.v1.schema.json';schema.parent.mkdir(parents=True)
    value=json.loads(g._SCHEMA_PATH.read_text())
    if target=='schema':value['properties']['publication_status']={'type':'string'}
    if target=='schema':schema.write_text(json.dumps(value))
    else:schema.write_bytes(g._SCHEMA_PATH.read_bytes())
    name='engine.neuralweb._review_disposable_'+target
    spec=importlib.util.spec_from_file_location(name,helper);mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod;spec.loader.exec_module(mod)
    class V(mod.ControlledOwnerVerifier):
        def current_action_at(self,p,*,action):return p['activation_at']
        def resolve(self,p,*,action):return mod.ControlledDecision(p['root'],p['generation_id'],action,p['activation_at'],'ACCEPTED','fixture')
    before=g.read(root,g.PENDING)
    if target=='unchanged':
        assert mod.resume_generation(root,plan,controlled_verifier=V())['status']=='CONTROLLED_ACCEPTED'
        assert g.read(root,g.GENERATIONS+'/'+plan['generation_id']+'/plan.json')==g.canonical(plan)
    else:
        with pytest.raises(mod.GenerationUnavailable,match='PRODUCER'):
            mod.resume_generation(root,plan,controlled_verifier=V())
        assert g.read(root,g.PENDING)==before and g.read(root,g.CURRENT) is None

@pytest.mark.parametrize('field',['parity','parity_flag','omit','bundle','state','projection','population','dispositions','natural','cutover'])
def test_review_rehashed_false_shadow_refuses(prepared,field):
    import copy
    root,_,plan=prepared;bad=copy.deepcopy(plan)
    if field=='parity':bad['shadow']={'parity':True}
    elif field=='parity_flag':bad['shadow']['parity_accepted']=True
    elif field=='omit':bad['shadow'].pop('successor_surface')
    elif field=='bundle':bad['shadow']['same_input_bundle_sha256']='f'*64
    elif field=='state':bad['shadow']['production_state_sha256']='f'*64
    elif field=='projection':bad['shadow']['projection_sha256']='f'*64
    elif field=='population':bad['shadow']['successor_surface']={}
    elif field=='dispositions':bad['shadow']['production_qualification_dispositions']={}
    elif field=='natural':bad['shadow']['natural']=True
    else:bad['shadow']['cutover_allowed']=True
    reseal(bad)
    with pytest.raises(g.GenerationUnavailable):g.publish_generation(root,bad,controlled_verifier=AcceptedFixture())
    assert g.read(root,g.PENDING) is None and g.read(root,g.CURRENT) is None

@pytest.mark.parametrize('kind',['accepted','stale','future','revoked'])
def test_review_current_check_separate_from_original_activation(prepared,kind):
    root,_,plan=prepared
    def pause(stage):
        if stage=='seal':raise RuntimeError('pause')
    with pytest.raises(RuntimeError):g.publish_generation(root,plan,controlled_verifier=AcceptedFixture(),fault=pause)
    sealed=g.read(root,g.GENERATIONS+'/'+plan['generation_id']+'/plan.json')
    class Later(g.ControlledOwnerVerifier):
        def current_action_at(self,p,*,action):return '2026-10-04T13:00:00Z'
        def resolve(self,p,*,action):
            checked=p['activation_at'] if kind=='stale' else '2026-10-04T13:00:01Z' if kind=='future' else '2026-10-04T13:00:00Z'
            return g.ControlledDecision(p['root'],p['generation_id'],action,checked,
                'REVOKED' if kind=='revoked' else 'ACCEPTED','later-synthetic-owner-check')
    if kind=='accepted':
        assert g.resume_generation(root,plan,controlled_verifier=Later())['status']=='CONTROLLED_ACCEPTED'
    else:
        with pytest.raises(g.GenerationUnavailable):g.resume_generation(root,plan,controlled_verifier=Later())
        assert g.read(root,g.CURRENT) is None
    assert g.read(root,g.GENERATIONS+'/'+plan['generation_id']+'/plan.json')==sealed
    assert plan['activation_at']==EMITTED

@pytest.mark.parametrize('action_clock',[None,'not-a-clock','2026-10-04T11:59:00Z'])
def test_review_unbound_or_regressed_current_action_refuses(prepared,action_clock):
    root,_,plan=prepared
    class Unbound(AcceptedFixture):
        def current_action_at(self,p,*,action):return action_clock
    with pytest.raises(g.GenerationUnavailable):
        g.publish_generation(root,plan,controlled_verifier=Unbound())
    assert g.read(root,g.PENDING) is None and g.read(root,g.LOCK) is None

def test_review_exact_existing_empty_capture_is_distinct_positive(production_world):
    root=production_world
    put(root,g.HISTORY,b'')
    bundle,_=compose(root)
    plan=g.prepare_generation(bundle,root=root,generated_at=EMITTED,activation_at=EMITTED,
        entry=g.entry_preflight(root,legacy_api=True))
    assert plan['captured_frontier']['legacy_phase_history']['availability']=='AVAILABLE'
    assert plan['captured_frontier']['legacy_phase_history']['sha256']==g.sha(b'')
    assert plan['history_exists'] is True
    assert g.validate_generation(plan)['bundle_ref']['sha256']==bundle.bundle_sha256

def test_review_later_current_rollback_check_keeps_original_state(prepared):
    root,_,first=prepared
    g.publish_generation(root,first,controlled_verifier=AcceptedFixture())
    bundle,_=compose(root)
    second=g.prepare_generation(bundle,root=root,generated_at='2026-10-04T12:01:00Z',
        activation_at='2026-10-04T12:01:00Z',entry=g.entry_preflight(root),correction_reason='controlled correction')
    g.publish_generation(root,second,controlled_verifier=AcceptedFixture())
    class Later(AcceptedFixture):
        def __init__(self,revoked=False):super().__init__();self.revoked=revoked
        def current_action_at(self,p,*,action):return '2026-10-04T13:00:00Z'
        def resolve(self,p,*,action):
            return g.ControlledDecision(p['root'],p['generation_id'],action,'2026-10-04T13:00:00Z',
                'REVOKED' if self.revoked else 'ACCEPTED','later-controlled-rollback-use')
    tape=g.read(root,g.HISTORY)
    with pytest.raises(g.GenerationUnavailable,match='REJECTED'):
        g.rollback_generation(root,first['generation_id'],activation_at='2026-10-04T12:02:00Z',controlled_verifier=Later(True))
    assert g.read(root,g.CURRENT)==g._reference(second)
    g.rollback_generation(root,first['generation_id'],activation_at='2026-10-04T12:02:00Z',controlled_verifier=Later())
    rollback=g._validate_ref(root,g.parse(g.read(root,g.CURRENT)))
    assert rollback['activation_at']=='2026-10-04T12:02:00Z'
    assert rollback['state_b64']==first['state_b64']
    assert g.read(root,g.HISTORY)==tape

def test_review_disposable_source_drift_during_check_refuses_before_effect(prepared,tmp_path):
    import importlib.util,sys
    root,_,plan=prepared
    clone=tmp_path/'check-race-copy';helper=clone/'engine/neuralweb/theme_state_generation.py'
    helper.parent.mkdir(parents=True);helper.write_bytes(Path(g.__file__).read_bytes())
    schema=clone/'contracts/theme_graph/theme_state_generation.v1.schema.json'
    schema.parent.mkdir(parents=True);schema.write_bytes(g._SCHEMA_PATH.read_bytes())
    name='engine.neuralweb._review_check_race_copy'
    spec=importlib.util.spec_from_file_location(name,helper);mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod;spec.loader.exec_module(mod)
    class Changed(mod.ControlledOwnerVerifier):
        def current_action_at(self,p,*,action):return p['activation_at']
        def resolve(self,p,*,action):
            helper.write_text(helper.read_text()+'\n# controlled disposable source revision after initial validation\n')
            return mod.ControlledDecision(p['root'],p['generation_id'],action,p['activation_at'],'ACCEPTED','fixture')
    with pytest.raises(mod.GenerationUnavailable,match='PRODUCER'):
        mod.publish_generation(root,plan,controlled_verifier=Changed())
    assert g.read(root,g.PENDING) is None and g.read(root,g.LOCK) is None and g.read(root,g.CURRENT) is None

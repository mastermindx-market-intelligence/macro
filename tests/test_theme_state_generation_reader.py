"""S3a controlled actual sealed-owner reads; no production rights/publication."""
import copy
from dataclasses import replace
import json
import pytest
from engine.neuralweb import theme_state_generation as g
from engine.neuralweb import theme_state_generation_reader as reader
from tests.test_theme_state_generation import prepared, AcceptedFixture, put
from tests.test_theme_state_production import production_world, compose, LOCAL, CN, EFFECTIVE, KNOWN

USE = "2026-10-04T13:00:00Z"

class ReadFixture(reader.ControlledReadVerifier):
    def __init__(self, status="ACCEPTED", change=None):
        self.status=status
        self.change=change
    def resolve(self, request):
        decision=reader.ControlledReadDecision(**request, status=self.status,
            owner_event="synthetic-current-use-owner-fixture", accepted_at=request["use_at"])
        return replace(decision, **(self.change or {}))

def files(root):
    return {("F:" if p.is_file() else "D:")+str(p.relative_to(root)):
        p.read_bytes() if p.is_file() else None for p in root.rglob("*")}

def call(root, **kw):
    before=files(root)
    args=dict(effective_at=EFFECTIVE, known_at=KNOWN, purpose="research_internal",
        use_at=USE, controlled_verifier=ReadFixture())
    args.update(kw)
    answer=reader.read_generation(root, **args)
    assert files(root)==before, "read/refusal changed owner bytes"
    witness = None
    if answer["state"] is not None:
        witness = publication_plan(root, answer)
    reader.validate_read_receipt(answer, publication_plan=witness)
    assert files(root)==before, "detached validation changed owner bytes"
    return answer


def publication_plan(root, receipt):
    """Only read the actual immutable plan; never reconstruct one from a receipt."""
    generation_id = receipt["publication"]["generation_id"]
    return g.parse(g.read(root, g.GENERATIONS + "/" + generation_id + "/plan.json"))

@pytest.fixture
def accepted(prepared):
    root,bundle,plan=prepared
    g.publish_generation(root,plan,controlled_verifier=AcceptedFixture())
    return root,plan

def test_actual_sealed_generation_coherent_state_projection_history(accepted):
    root,plan=accepted
    out=call(root)
    assert out["status"]=="DESCRIPTIVE"
    assert out["publication"]["generation_id"]==plan["generation_id"]
    assert out["publication"]["reference_sha256"]==g.sha(g.read(root,g.CURRENT))
    state=g.validate_generation(plan)
    assert out["state"]==state
    assert out["state_identity"]["semantic_sha256"]==state["state_sha256"]
    assert out["state_identity"]["raw_sha256"]==plan["digests"]["state_raw"]
    assert out["compatibility"]["projection"]==g.parse(g.unb64(plan["compatibility_b64"]))
    assert [x["theme_id"] for x in out["compatibility"]["projection"]["themes"]]==["grid","travel"]
    prefix=g.unb64(plan["history_b64"])+g.unb64(plan["tail_b64"])
    assert g.unb64(out["history"]["prefix_b64"])==prefix
    assert out["history"]["length"]==len(prefix)
    assert out["history"]["rows"]==g.preflight_phase_history(prefix).rows
    assert all(value is False for value in out["authority_caps"].values())
    assert out["materialization_allowed"] is False
    assert out["state_identity"]["generated_at"]==state["generated_at"]

@pytest.mark.parametrize("node",["theme:grid","theme:travel",LOCAL,CN])
def test_actual_s1_subjects_native_zero_null_unmapped(accepted,node):
    root,_=accepted
    out=call(root,node_id=node)
    assert out["subject_read"]["status"]=="DESCRIPTIVE"
    subject=out["subject_read"]["subject"]
    assert subject["node_id"]==node and subject["eligibility"]=="NOT_QUALIFIED"
    if node==LOCAL:
        assert subject["canonical_mapping"]["state"]=="UNMAPPED"
        assert subject["legs"]["baskets"]["records"][0]["value"]["score"]==0
    if node=="theme:grid":
        record=subject["legs"]["foresight_cascade"]["records"][0]
        assert record["value"]["score"]==0
        assert record["value"]["bottleneck_band"] is None
        assert record["native_clocks"]["known_at"]["grain"]=="UNAVAILABLE"

def test_missing_subject_is_not_missing_generation(accepted):
    root,_=accepted
    out=call(root,node_id="theme:absent")
    assert out["status"]=="DESCRIPTIVE"
    assert out["subject_read"]["status"]=="UNAVAILABLE"
    assert out["subject_read"]["reason_codes"]==["SUBJECT_UNAVAILABLE"]

@pytest.mark.parametrize("authority",[None,True,"accepted",{},object()])
def test_unwired_current_use_never_granted(accepted,authority):
    root,_=accepted
    out=call(root,controlled_verifier=authority)
    assert out["status"]=="UNAVAILABLE"
    assert out["reason_codes"]==["CURRENT_USE_AUTHORITY_UNAVAILABLE"]
    assert out["state"] is None and out["compatibility"] is None

@pytest.mark.parametrize("status",["REVOKED","REJECTED","UNAVAILABLE"])
def test_current_rights_refusal_distinct(accepted,status):
    root,_=accepted
    out=call(root,controlled_verifier=ReadFixture(status))
    assert out["status"]=="UNAVAILABLE"
    assert out["reason_codes"]==["CURRENT_USE_"+status]

@pytest.mark.parametrize("change",[
    {"generation_id":"tsg-"+"0"*64},{"root":"/wrong"},{"purpose":"public"},
    {"use_at":"2026-10-04T12:00:00Z"},{"reference_sha256":"0"*64},
    {"state_sha256":"0"*64},{"query":{"effective_at":"2026-10-02","known_at":KNOWN}},
    {"accepted_at":"2026-10-04T14:00:00Z"},{"owner_event":""}])
def test_current_use_exact_binding(accepted,change):
    root,_=accepted
    out=call(root,controlled_verifier=ReadFixture(change=change))
    assert out["status"]=="UNAVAILABLE" and out["state"] is None

@pytest.mark.parametrize("purpose",["public","service","trade","CONTROLLED_TEST_ONLY"])
def test_controlled_receipt_cannot_upgrade_s1_purpose(accepted,purpose):
    root,_=accepted
    out=call(root,purpose=purpose)
    assert out["status"]=="UNAVAILABLE"
    assert out["reason_codes"]==["S1_UNMATERIALIZED_CURRENT_SOURCE_PURPOSE_GRANT_REQUIRED"]

def test_missing_ref_never_uses_valid_loose_aliases(accepted):
    root,_=accepted
    (root/g.CURRENT).unlink()
    out=call(root)
    assert out["status"]=="MISSING" and out["state"] is None

@pytest.mark.parametrize("target",["ref","plan","state","legacy","history","tail"])
def test_bad_accepted_family_no_fallback(accepted,target):
    root,plan=accepted
    base=g.GENERATIONS+"/"+plan["generation_id"]+"/"
    paths={"ref":g.CURRENT,"plan":base+"plan.json","state":base+"state.json",
        "legacy":base+"legacy.json","history":g.HISTORY,"tail":g.HISTORY}
    if target=="tail":
        put(root,g.HISTORY,g.read(root,g.HISTORY)+b"\n")
    else: put(root,paths[target],b"foreign")
    out=call(root)
    assert out["status"]=="INVALID" and out["state"] is None

def test_loose_alias_mixture_does_not_control_accepted_read(accepted):
    root,plan=accepted
    put(root,g.PRIMARY,b"pending-primary");put(root,g.MIRROR,b"pending-mirror")
    out=call(root)
    assert out["status"]=="DESCRIPTIVE"
    assert out["compatibility"]["raw_sha256"]==plan["digests"]["compatibility_raw"]

@pytest.mark.parametrize("known,reason",[
    ("2026-10-04T11:00:00Z","STATE_NOT_YET_EMITTED"),
    ("2026-10-04T12:30:00Z","EXACT_CAPTURE_QUERY_REQUIRED")])
def test_query_cutoff_not_restamped(accepted,known,reason):
    root,_=accepted
    out=call(root,known_at=known)
    assert out["status"]=="UNAVAILABLE" and reason in out["reason_codes"]

def test_effective_query_not_reinterpreted(accepted):
    root,_=accepted
    out=call(root,effective_at="2026-10-02")
    assert out["reason_codes"]==["EXACT_CAPTURE_QUERY_REQUIRED"]

@pytest.mark.parametrize("use_at",["not-a-clock","2026-10-04T11:59:59Z"])
def test_use_clock_future_refusal(accepted,use_at):
    root,_=accepted
    out=call(root,use_at=use_at)
    assert out["status"]=="INVALID" or out["status"]=="UNAVAILABLE"
    assert out["state"] is None

def next_plan(root, reason="controlled correction"):
    from engine.neuralweb import theme_state_adapter as adapter
    bundle=adapter.capture_owner_bundle(root,effective_at=EFFECTIVE,known_at="2026-10-04T12:01:00Z")
    return g.prepare_generation(bundle,root=root,generated_at="2026-10-04T12:01:00Z",
        activation_at="2026-10-04T12:01:00Z",entry=g.entry_preflight(root),correction_reason=reason)

@pytest.mark.parametrize("stage",["stage","seal","primary","mirror","tail"])
def test_pending_correction_reads_only_previous_accepted(accepted,stage):
    root,first=accepted
    plan=next_plan(root)
    def crash(point):
        if point==stage:raise RuntimeError("controlled interruption")
    with pytest.raises(RuntimeError):
        g.publish_generation(root,plan,controlled_verifier=AcceptedFixture(),fault=crash)
    out=call(root)
    assert out["status"]=="PENDING"
    assert out["publication"]["generation_id"]==first["generation_id"]
    assert out["publication"]["pending_generation_id"]==plan["generation_id"]
    assert out["state_identity"]["generated_at"]==KNOWN
    assert out["history"]["sha256"]==g.parse(g._reference(first))["history_sha256"]

def test_pending_without_any_accepted_generation(prepared):
    root,_,plan=prepared
    def crash(point):
        if point=="seal":raise RuntimeError("first interruption")
    with pytest.raises(RuntimeError):
        g.publish_generation(root,plan,controlled_verifier=AcceptedFixture(),fault=crash)
    out=call(root)
    assert out["status"]=="PENDING" and out["publication"] is None and out["state"] is None

def test_correction_and_rollback_keep_emission_age_history(accepted):
    root,first=accepted
    second=next_plan(root)
    g.publish_generation(root,second,controlled_verifier=AcceptedFixture())
    late=call(root)
    assert late["status"]=="UNAVAILABLE"
    out=call(root,known_at="2026-10-04T12:01:00Z")
    assert out["publication"]["activation_kind"]=="CORRECTION"
    assert out["state"]["correction"]["previous"]["state_sha256"]==first["digests"]["state_semantic"]
    history=out["history"]
    g.rollback_generation(root,first["generation_id"],activation_at="2026-10-04T12:03:00Z",
        controlled_verifier=AcceptedFixture())
    out=call(root)
    assert out["publication"]["activation_kind"]=="ROLLBACK"
    assert out["publication"]["rollback_selection"]["generation_id"]==first["generation_id"]
    assert out["state_identity"]["generated_at"]==KNOWN
    assert out["state_identity"]["age_seconds_at_use"]==3600
    assert out["history"]==history
    assert call(root,controlled_verifier=ReadFixture("REVOKED"))["state"] is None

def test_reference_switch_during_current_rights_refuses(accepted):
    root,plan=accepted
    class Switch(ReadFixture):
        def resolve(self,request):
            put(root,g.CURRENT,b"changed")
            return super().resolve(request)
    # Intentional fixture-side mutation; reader must detect rather than emit old.
    out=reader.read_generation(root,effective_at=EFFECTIVE,known_at=KNOWN,
        purpose="research_internal",use_at=USE,controlled_verifier=Switch())
    assert out["status"]=="INVALID" and out["reason_codes"]==["REFERENCE_CHANGED_DURING_READ"]
    assert out["state"] is None

def test_read_contract_closed_flags_and_relational_digest(accepted):
    root,_=accepted
    out=call(root)
    for mutate in [
        lambda x:x.update(extra=True),
        lambda x:x["authority_caps"].update(may_publish=True),
        lambda x:x["state_identity"].update(semantic_sha256="0"*64),
        lambda x:x["history"].update(length=True),
        lambda x:x["compatibility"].update(raw_sha256="0"*64)]:
        changed=copy.deepcopy(out);mutate(changed)
        with pytest.raises(ValueError):
            reader.validate_read_receipt(changed, publication_plan=publication_plan(root, out))

def test_reader_schema_owner_defs_exact():
    from engine.theme_graph import theme_state_production as p
    doc=json.loads(reader.SCHEMA_PATH.read_text())
    for key,value in p._SCHEMA_DOC["$defs"].items():
        assert doc["$defs"][key]==value


@pytest.mark.parametrize("mode",["stale","future"])
def test_native_freshness_not_refreshed_by_publication(production_world,mode):
    from engine.neuralweb import theme_state_adapter as adapter, thematic_state as legacy
    source=production_world/legacy._FORESIGHT_PATH
    value=json.loads(source.read_text())
    value["asof"]="2026-09-20" if mode=="stale" else "2026-10-05"
    source.write_text(json.dumps(value))
    bundle,_=compose(production_world)
    plan=g.prepare_generation(bundle,root=production_world,generated_at=KNOWN,
        activation_at=KNOWN,entry=g.entry_preflight(production_world,legacy_api=True))
    g.publish_generation(production_world,plan,controlled_verifier=AcceptedFixture())
    out=call(production_world)
    leg=next(x for x in out["source_clocks"] if x["node_id"]=="theme:grid" and x["source_id"]=="foresight_cascade")
    assert leg["freshness"]==mode.upper()
    record=next(x for x in out["state"]["subjects"] if x["node_id"]=="theme:grid")["legs"]["foresight_cascade"]["records"][0]
    assert record["native_clocks"]["effective_at"]["value"]==value["asof"]
    assert record["native_clocks"]["effective_at"]["grain"]=="DATE"
    assert out["state_identity"]["generated_at"]==KNOWN
    if mode=="future":assert record["usable_at_query"] is False
    else:assert out["status"]=="STALE"

def test_actual_empty_owner_population_is_valid_empty(production_world):
    import pandas as pd
    import yaml
    graph=production_world/"data/theme_graph"
    nodes=pd.read_parquet(graph/"nodes.parquet")
    nodes.iloc[0:0].to_parquet(graph/"nodes.parquet",index=False)
    (production_world/"config/theme_crosswalk.yml").write_text(yaml.safe_dump({"themes":[]}))
    bundle,_=compose(production_world)
    plan=g.prepare_generation(bundle,root=production_world,generated_at=KNOWN,
        activation_at=KNOWN,entry=g.entry_preflight(production_world,legacy_api=True))
    g.publish_generation(production_world,plan,controlled_verifier=AcceptedFixture())
    out=call(production_world)
    assert out["status"]=="VALID_EMPTY"
    assert out["state"]["subjects"]==[]
    assert out["compatibility"]["projection"]["themes"]==[]
    assert out["compatibility"]["projection"]["n_themes"]==0
    assert out["history"]["length"]==0 and out["history"]["rows"]==[]

@pytest.mark.parametrize("target",["plan","state","legacy","history","pending"])
def test_owner_family_change_inside_verifier_is_quarantined(accepted,target):
    root,plan=accepted
    path={"plan":g.GENERATIONS+"/"+plan["generation_id"]+"/plan.json",
        "state":g.GENERATIONS+"/"+plan["generation_id"]+"/state.json",
        "legacy":g.GENERATIONS+"/"+plan["generation_id"]+"/legacy.json",
        "history":g.HISTORY,"pending":g.PENDING}[target]
    class Change(ReadFixture):
        def resolve(self,request):
            put(root,path,b"changed-during-read")
            return super().resolve(request)
    out=reader.read_generation(root,effective_at=EFFECTIVE,known_at=KNOWN,
        purpose="research_internal",use_at=USE,controlled_verifier=Change())
    assert out["status"]=="INVALID"
    assert out["reason_codes"]==["FAMILY_CHANGED_DURING_READ"]
    assert out["state"] is None

def test_unaccepted_orphan_and_forged_pending_refuse(accepted):
    root,plan=accepted
    orphan=root/g.GENERATIONS/("tsg-"+"0"*64)
    orphan.mkdir()
    out=call(root)
    assert out["status"]=="INVALID" and out["reason_codes"]==["ORPHAN_GENERATION_UNAVAILABLE"]
    orphan.rmdir()
    put(root,g.PENDING,b'{"schema":"fake"}')
    out=call(root)
    assert out["status"]=="INVALID" and out["state"] is None

def test_exact_use_publication_boundary(accepted):
    root,_=accepted
    out=call(root,use_at=KNOWN)
    assert out["status"]=="DESCRIPTIVE"
    assert out["state_identity"]["age_seconds_at_use"]==0


def test_real_pending_tail_is_not_part_of_previous_sealed_prefix(accepted,monkeypatch):
    from engine.neuralweb import theme_state_adapter as adapter
    root,first=accepted
    monkeypatch.setenv("COLLECT_LANE","nightly")
    from engine.neuralweb import thematic_state as legacy
    source=root/legacy._FORESIGHT_PATH
    value=json.loads(source.read_text());value["themes"][0]["stage"]="ACTIVE"
    source.write_text(json.dumps(value))
    bundle=adapter.capture_owner_bundle(root,effective_at="2026-10-04",known_at="2026-10-05T12:00:00Z")
    plan=g.prepare_generation(bundle,root=root,generated_at="2026-10-05T12:00:00Z",
        activation_at="2026-10-05T12:00:00Z",entry=g.entry_preflight(root),
        correction_reason="controlled next-date correction")
    assert plan["history_rows_added"]>0 and g.unb64(plan["tail_b64"])
    def crash(stage):
        if stage=="tail":raise RuntimeError("tail before ref")
    with pytest.raises(RuntimeError):
        g.publish_generation(root,plan,controlled_verifier=AcceptedFixture(),fault=crash)
    out=call(root,use_at="2026-10-05T13:00:00Z")
    assert out["status"]=="PENDING"
    old=g.unb64(first["history_b64"])+g.unb64(first["tail_b64"])
    assert g.unb64(out["history"]["prefix_b64"])==old
    assert len(g.read(root,g.HISTORY))>out["history"]["length"]
    g.resume_generation(root,plan,controlled_verifier=AcceptedFixture())
    assert call(root,use_at="2026-10-05T13:00:00Z")["status"]=="UNAVAILABLE"
    new=call(root,effective_at="2026-10-04",known_at="2026-10-05T12:00:00Z",
        use_at="2026-10-05T13:00:00Z")
    assert new["publication"]["activation_kind"]=="CORRECTION"
    assert new["history"]["length"]==len(g.read(root,g.HISTORY))
    g.rollback_generation(root,first["generation_id"],activation_at="2026-10-05T12:30:00Z",
        controlled_verifier=AcceptedFixture())
    restored=call(root,use_at="2026-10-05T13:00:00Z")
    assert restored["state_identity"]["generated_at"]==KNOWN
    assert restored["history"]==new["history"]
    assert restored["publication"]["activation_kind"]=="ROLLBACK"

def test_pending_initial_ref_committed_cleanup_still_pending(prepared):
    root,_,plan=prepared
    def crash(stage):
        if stage=="ref":raise RuntimeError("accepted ref before cleanup")
    with pytest.raises(RuntimeError):
        g.publish_generation(root,plan,controlled_verifier=AcceptedFixture(),fault=crash)
    out=call(root)
    assert out["status"]=="PENDING"
    assert out["publication"]["generation_id"]==plan["generation_id"]
    assert out["publication"]["pending_generation_id"]==plan["generation_id"]

def test_publication_identity_fields_cannot_be_relabelled(accepted):
    root,_=accepted
    out=call(root)
    for update in [
        {"generation_id":"tsg-"+"0"*64},{"activation_at":"2026-10-04T12:01:00Z"},
        {"activation_kind":"ROLLBACK"},{"reference_sha256":"0"*64},
        {"plan_sha256":"0"*64}]:
        changed=copy.deepcopy(out);changed["publication"].update(update)
        with pytest.raises(ValueError):
            reader.validate_read_receipt(changed, publication_plan=publication_plan(root, out))

@pytest.mark.parametrize("field",["effective_at","known_at","purpose","use_at","node_id"])
def test_nonstring_request_refused_without_effects(accepted,field):
    root,_=accepted
    before=files(root)
    kwargs=dict(effective_at=EFFECTIVE,known_at=KNOWN,purpose="research_internal",
        use_at=USE,controlled_verifier=ReadFixture())
    kwargs[field]=True
    with pytest.raises(ValueError):reader.read_generation(root,**kwargs)
    assert files(root)==before


def test_rehashed_foreign_state_cannot_be_sealed_by_ref_echo(accepted):
    from engine.theme_graph import theme_state_production as p
    root,plan=accepted
    forged=copy.deepcopy(plan)
    state=g.parse(g.unb64(forged["state_b64"]))
    state["subjects"][0]["legs"]["foresight_cascade"]["records"][0]["value"]["score"]=99
    state["state_sha256"]=p.state_digest(state)
    state["generation_id"]=p.GENERATION_PREFIX+state["state_sha256"][:20]
    forged["state_b64"]=g.b64(g.canonical(state))
    forged["digests"]["state_raw"]=g.sha(g.canonical(state))
    forged["digests"]["state_semantic"]=state["state_sha256"]
    forged["generation_id"]="tsg-"+g._plan_digest(forged)
    base=g.GENERATIONS+"/"+forged["generation_id"]+"/"
    put(root,base+"plan.json",g.canonical(forged))
    put(root,base+"state.json",g.unb64(forged["state_b64"]))
    put(root,base+"legacy.json",g.unb64(forged["compatibility_b64"]))
    put(root,g.CURRENT,g._reference(forged))
    out=call(root)
    assert out["status"]=="INVALID" and out["state"] is None

def test_missing_history_not_equivalent_to_valid_empty(accepted):
    root,_=accepted
    (root/g.HISTORY).unlink()
    out=call(root)
    assert out["status"]=="INVALID"
    assert out["reason_codes"]==["UNACCEPTED_HISTORY_TAIL"]

def test_symlink_immutable_state_refused_without_alias_fallback(accepted):
    root,plan=accepted
    p=root/g.GENERATIONS/plan["generation_id"]/"state.json"
    p.unlink();p.symlink_to(root/g.PRIMARY)
    out=call(root)
    assert out["status"]=="INVALID" and out["reason_codes"]==["FAMILY_SYMLINK"]


@pytest.mark.parametrize("kind", ["INITIAL", "CORRECTION", "ROLLBACK"])
def test_available_detached_receipt_requires_actual_publication_witness(accepted, kind):
    root, first = accepted
    known = KNOWN
    if kind != "INITIAL":
        second = next_plan(root)
        g.publish_generation(root, second, controlled_verifier=AcceptedFixture())
        known = "2026-10-04T12:01:00Z"
    if kind == "ROLLBACK":
        g.rollback_generation(root, first["generation_id"],
            activation_at="2026-10-04T12:03:00Z", controlled_verifier=AcceptedFixture())
        known = KNOWN
    out = call(root, known_at=known)
    assert out["publication"]["activation_kind"] == kind
    witness = publication_plan(root, out)
    before = files(root)
    with pytest.raises(ValueError, match="publication plan witness required"):
        reader.validate_read_receipt(out)
    assert reader.validate_read_receipt(out, publication_plan=witness) == out
    assert files(root) == before


@pytest.mark.parametrize("section,field", [
    ("rollback_selection", "plan_sha256"),
    ("rollback_selection", "history_sha256"),
    ("rollback_selection", "history_length"),
    ("prior_reference", "plan_sha256"),
    ("prior_reference", "history_sha256"),
    ("prior_reference", "history_length"),
])
def test_actual_witness_rejects_detached_lineage_metadata_changes(accepted, section, field):
    root, first = accepted
    second = next_plan(root)
    g.publish_generation(root, second, controlled_verifier=AcceptedFixture())
    g.rollback_generation(root, first["generation_id"],
        activation_at="2026-10-04T12:03:00Z", controlled_verifier=AcceptedFixture())
    out = call(root)
    witness = publication_plan(root, out)
    changed = copy.deepcopy(out)
    target = changed["publication"][section]
    target[field] = target[field] + 1 if field == "history_length" else "f" * 64
    before = files(root)
    with pytest.raises(ValueError, match="witness mismatch"):
        reader.validate_read_receipt(changed, publication_plan=witness)
    assert files(root) == before


def test_initial_relabelling_cannot_remove_rollback_lineage_obligation(accepted):
    root, first = accepted
    second = next_plan(root)
    g.publish_generation(root, second, controlled_verifier=AcceptedFixture())
    g.rollback_generation(root, first["generation_id"],
        activation_at="2026-10-04T12:03:00Z", controlled_verifier=AcceptedFixture())
    out = call(root)
    changed = copy.deepcopy(out)
    changed["publication"].update(activation_kind="INITIAL", prior_reference=None,
                                   rollback_selection=None)
    with pytest.raises(ValueError, match="witness required"):
        reader.validate_read_receipt(changed)
    with pytest.raises(ValueError, match="witness mismatch"):
        reader.validate_read_receipt(changed, publication_plan=publication_plan(root, out))


def test_foreign_or_modified_owner_plan_is_not_a_receipt_witness(accepted):
    root, first = accepted
    out = call(root)
    changed = copy.deepcopy(first)
    changed["activation_at"] = "2026-10-04T12:02:00Z"
    with pytest.raises(ValueError):
        reader.validate_read_receipt(out, publication_plan=changed)
    second = next_plan(root)
    g.publish_generation(root, second, controlled_verifier=AcceptedFixture())
    corrected = call(root, known_at="2026-10-04T12:01:00Z")
    with pytest.raises(ValueError, match="witness mismatch"):
        reader.validate_read_receipt(corrected, publication_plan=first)
    with pytest.raises(ValueError):
        reader.validate_read_receipt(corrected, publication_plan=True)

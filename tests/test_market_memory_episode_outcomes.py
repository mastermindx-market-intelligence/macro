"""Synthetic real-owner fixtures only; no production prices, grant or admission."""
from dataclasses import replace
from datetime import datetime, timezone
import json

import pytest

from engine.neuralweb import market_memory_episode_outcomes as outcomes
from engine.neuralweb import market_memory_episode_features as features
from engine.neuralweb import market_memory_episode_retrieval as retrieval
from engine.neuralweb import market_memory_technical_store as store
from engine.neuralweb import market_memory_technical_observation as technical
from tests.test_market_memory_episode_features import Policy
from tests.test_market_memory_retained_context_cohort import capture, owner, load
from tests import test_market_memory_technical_store as prices

DEFINITION = outcomes.RetainedArchivedBarOutcomeDefinition(
    "2026-07-01", "2026-08-31", "2026-09-02T00:00:00Z")
CUTOFF = "2026-08-20T12:00:00Z"


def _make_corpus(tmp_path, monkeypatch, *, sessions=("2026-07-13","2026-07-14","2026-07-15")):
    for session, growth in ((sessions[0], 0.0), (sessions[1], .4)):
        capture(tmp_path, monkeypatch, session=session, growth=growth)
    query_capture = capture(tmp_path, monkeypatch, session=sessions[2], growth=.2)
    reader, pin = owner(tmp_path)
    population = load(reader, pin, query_capture, cutoff=CUTOFF)
    query = features.read_episode_feature_capability(reader, pin,
        query_id=query_capture.capture_receipt["query_id"],
        subject_id=query_capture.packet["subject"]["subject_id"], query_cutoff=CUTOFF, policy=Policy())
    selection = retrieval.retrieve_retained_contexts(population, query, policy=Policy(), k=1,
        method=retrieval.RetainedContextMethodSpec(0, 0, "historical_hypothetical"))
    root, _ = prices._capture(tmp_path, monkeypatch)
    technical_pin = store.pin_technical_actual_output_generation(root)
    # Actual publication and read clocks have separate source meanings.
    monkeypatch.setattr(store, "_utc_now", lambda: datetime(2026, 8, 21, tzinfo=timezone.utc))
    return root, technical_pin, selection, reader, pin


@pytest.fixture
def corpus(tmp_path,monkeypatch):
    return _make_corpus(tmp_path,monkeypatch)


def prepare(corpus, *, policy=None, **kwargs):
    root, pin, selection, reader, context_pin = corpus
    return outcomes.prepare_contextual_outcomes(selection, technical_root=root, technical_pin=pin,
        context_reader=reader, context_generation=context_pin,
        definition=kwargs.pop("definition",DEFINITION), e0_registration_sha256="a" * 64,
        lens=kwargs.pop("lens", "later_observed"), outcome_cutoff=kwargs.pop("outcome_cutoff", CUTOFF),
        policy=Policy() if policy is None else policy, **kwargs)


def mark_input(corpus, policy=None):
    root, pin, *_ = corpus
    policy = Policy() if policy is None else policy
    cap = store.read_retained_source_bar_metadata(root, technical_pin=pin,
        source_observation_id=pin.captures[0].source_observation_id, policy=policy)
    return dict(root=root, technical_pin=pin, metadata=cap, anchor_session="2026-07-13",
        target_session="2026-07-20", definition_sha256=DEFINITION.disclosure()["definition_sha256"],
        e0_registration_sha256="a" * 64, visibility_cutoff=CUTOFF,
        observation_deadline=DEFINITION.observation_deadline,policy=policy)


def test_native_marks_exact_source_rows_and_no_publication_claim(corpus):
    cap = store.read_retained_source_bar_marks(**mark_input(corpus))
    value = store.disclose_retained_source_bar_marks(cap, policy=Policy())
    assert value["anchor"]["session"] == "2026-07-13"
    assert value["target"]["session"] == "2026-07-20"
    assert float.fromhex(value["anchor"]["close_binary64_hex"]).as_integer_ratio() == tuple(
        int(value["anchor"]["close_integer_ratio"][key]) for key in ("numerator", "denominator"))
    assert value["marks_read_at"] == "2026-08-21T00:00:00Z"
    assert value["source_first_observed_at"] == "2026-08-10T02:00:00Z"
    assert value["contextual_observation_published"] is False
    assert "published_at" not in value


@pytest.mark.parametrize("action", ["read_registered_contextual_outcome_labels", "read_retained_source_bar_marks"])
def test_label_and_current_source_gates_precede_numerical_decoder(corpus, monkeypatch, action):
    inputs = mark_input(corpus, policy=Policy({action}))
    monkeypatch.setattr(technical, "read_source_bar_marks", lambda *a, **k: pytest.fail("label decoder"))
    with pytest.raises(PermissionError):
        store.read_retained_source_bar_marks(**inputs)


def test_generation_authorization_precedes_owner_io(corpus, monkeypatch):
    monkeypatch.setattr(store, "pin_technical_actual_output_generation", lambda *a, **k: pytest.fail("owner I/O"))
    with pytest.raises(PermissionError):
        prepare(corpus, policy=Policy({"read_retained_source_bar_generation_metadata"}))


def test_future_source_clock_precedes_numerical_decoder(corpus, monkeypatch):
    inputs = mark_input(corpus)
    inputs["visibility_cutoff"] = "2026-08-09T00:00:00Z"
    monkeypatch.setattr(technical, "read_source_bar_marks", lambda *a, **k: pytest.fail("future label"))
    with pytest.raises(store.MarketMemoryTechnicalStoreError, match="not visible"):
        store.read_retained_source_bar_marks(**inputs)


def test_preparation_preserves_all_selected_bytes_and_unreturned_rights(corpus):
    root, pin, selection, *_ = corpus
    original = retrieval.disclose_episode_retrieval(selection, policy=Policy())
    cap = prepare(corpus)
    value = outcomes.disclose_outcome_preparation(cap, policy=Policy())
    assert value["selection_sha256"] == original["selection_sha256"]
    assert value["retrieval_id"] == original["retrieval_id"]
    assert value["denominator"] == original["denominator"]
    assert [row["selected"] for row in value["rows"]] == original["selected"]
    assert value["rows"][0]["rank"] == 1
    row = value["rows"][0]
    assert row["status"] == "proof_pending" and row["value_q18"] is None
    assert row["proposed_value_q18"] is not None
    assert row["reason"] == "contextual_observation_not_published"
    assert value["contextual_observations_published"] is False
    assert value["operational_admission"] is False
    assert value["economic_return"] is False
    assert retrieval.disclose_episode_retrieval(selection, policy=Policy()) == original
    value["rows"].clear()
    assert outcomes.disclose_outcome_preparation(cap, policy=Policy())["rows"]
    with pytest.raises(features.EpisodeFeatureAccessError):
        outcomes.disclose_outcome_preparation(cap, policy=Policy({"compare_retained_macro_feature"}))


def test_cached_preparation_rechecks_source_and_e0_rights(corpus):
    cap = prepare(corpus)
    for action in ("read_registered_contextual_outcome_labels", "disclose_retained_source_bar_marks",
                   "disclose_retained_source_bar_metadata"):
        with pytest.raises(PermissionError):
            outcomes.disclose_outcome_preparation(cap, policy=Policy({action}))


def test_then_known_does_not_decode_or_reveal_unpublished_observation(corpus, monkeypatch):
    monkeypatch.setattr(technical, "read_source_bar_marks", lambda *a, **k: pytest.fail("then-known price"))
    value = outcomes.disclose_outcome_preparation(prepare(corpus, lens="then_known"), policy=Policy())
    for row in value["rows"]:
        assert row["reason"] == "not_visible_at_query"
        assert set(row) == {"rank", "selected", "source_session", "subject", "status", "value_q18", "reason"}


@pytest.mark.parametrize("lens,cutoff", [("nearest", CUTOFF), ("then_known", "2026-08-21T00:00:00Z"),
                                      ("later_observed", "2026-08-19T00:00:00Z")])
def test_lens_and_cutoff_not_coerced(corpus, lens, cutoff):
    with pytest.raises(outcomes.EpisodeOutcomeError):
        prepare(corpus, lens=lens, outcome_cutoff=cutoff)


def test_capabilities_reject_dicts_subclasses_and_changed_body(corpus):
    cap = prepare(corpus)
    with pytest.raises(outcomes.EpisodeOutcomeError):
        outcomes.disclose_outcome_preparation(json.loads(cap._body), policy=Policy())
    with pytest.raises(outcomes.EpisodeOutcomeError):
        outcomes.EpisodeOutcomePreparationCapability(b"{}", corpus[2], (), (), Policy.policy_id)
    bad = object.__new__(outcomes.EpisodeOutcomePreparationCapability)
    for name in cap.__slots__:
        object.__setattr__(bad, name, getattr(cap, name))
    object.__setattr__(bad, "_body", b"{}")
    with pytest.raises(outcomes.EpisodeOutcomeError):
        outcomes.disclose_outcome_preparation(bad, policy=Policy())
    marks = store.read_retained_source_bar_marks(**mark_input(corpus))
    with pytest.raises(PermissionError):
        store.disclose_retained_source_bar_marks(replace(marks, _body=b"{}"), policy=Policy())


@pytest.mark.parametrize("first,last,deadline", [("2026-7-01","2026-08-31","2026-09-02T00:00:00Z"),
    ("2026-08-31","2026-07-01","2026-09-02T00:00:00Z"),
    ("2026-07-01","2026-08-31","2026-08-31T23:59:59Z")])
def test_definition_never_fills_unknown_or_invalid_registration(first,last,deadline):
    with pytest.raises(outcomes.EpisodeOutcomeError):
        outcomes.RetainedArchivedBarOutcomeDefinition(first,last,deadline)


def test_exact_fifth_session_and_no_calendar_day_substitution():
    assert outcomes._target("2026-07-13", DEFINITION) == "2026-07-20"
    with pytest.raises(outcomes.EpisodeOutcomeError):
        outcomes._target("2026-07-12", DEFINITION)
    with pytest.raises(outcomes.EpisodeOutcomeError):
        outcomes._target("2026-08-31", DEFINITION)


def test_ratio_has_single_context_independent_half_even_rounding():
    from decimal import localcontext, ROUND_DOWN
    marks={"anchor":{"close_integer_ratio":{"numerator":"3","denominator":"1"}},
           "target":{"close_integer_ratio":{"numerator":"4","denominator":"1"}}}
    with localcontext() as context:
        context.prec=2;context.rounding=ROUND_DOWN
        assert outcomes._ratio(marks) == "1.333333333333333333"


@pytest.fixture
def published(corpus):
    from engine.neuralweb import market_memory_contextual_observation_store as observations
    root, native, *_ = corpus
    preparation=prepare(corpus)
    reference=observations.append_contextual_observations(root,preparation=preparation,policy=Policy())
    pin=observations.pin_contextual_observation_generation(root,technical_store_id=native.store_id,
        exact_generation_ref=reference,policy=Policy())
    ids=tuple(entry["observation_id"] for entry in json.loads(pin._body)["entries"])
    return reference,pin,ids,preparation


def attach(corpus,published,*,policy=None,lens="later_observed",cutoff="2026-08-22T00:00:00Z",ids=None):
    _,pin,original_ids,_=published
    return outcomes.attach_contextual_outcomes(corpus[2],pin,
        observation_ids=original_ids if ids is None else ids,
        definition_sha256=DEFINITION.disclosure()["definition_sha256"],
        lens=lens,outcome_cutoff=cutoff,policy=Policy() if policy is None else policy)


def test_separate_durable_publication_clock_and_real_attachment(corpus,published):
    cap=attach(corpus,published)
    value=outcomes.disclose_contextual_outcomes(cap,policy=Policy())
    row=value["rows"][0]
    assert row["status"]=="observed" and row["value_q18"] is not None
    assert row["clocks"]=={"observed_at":"2026-08-21T00:00:00Z",
        "published_at":"2026-08-21T00:00:00Z","recorded_at":"2026-08-21T00:00:00Z"}
    original=retrieval.disclose_episode_retrieval(corpus[2],policy=Policy())
    assert value["selection_sha256"]==original["selection_sha256"]
    assert value["rows"][0]["selected"]==original["selected"][0]
    assert value["operational_admission"] is False
    assert value["economic_return"] is False


def test_publishing_is_idempotent_and_never_changes_original_technical_head(corpus,published):
    from engine.neuralweb import market_memory_contextual_observation_store as observations
    root,native,*_=corpus
    head=(root/"HEAD.json").read_bytes()
    before=prices._tree(root)
    reference=observations.append_contextual_observations(root,preparation=published[3],policy=Policy())
    assert reference==published[0]
    assert prices._tree(root)==before
    assert (root/"HEAD.json").read_bytes()==head
    assert store.pin_technical_actual_output_generation(root)==native


def test_then_known_future_and_missing_reference_are_indistinguishable(corpus,published,monkeypatch):
    from engine.neuralweb import market_memory_contextual_observation_store as observations
    monkeypatch.setattr(observations,"_read_observation",lambda *a,**k:pytest.fail("future payload"))
    future=outcomes.disclose_contextual_outcomes(attach(corpus,published,lens="then_known",cutoff=CUTOFF),policy=Policy())
    missing=outcomes.disclose_contextual_outcomes(attach(corpus,published,lens="then_known",cutoff=CUTOFF,
        ids=("mmcontextualobservation_"+"f"*64,)),policy=Policy())
    assert future==missing
    assert future["rows"][0]["reason"]=="not_visible_at_query"
    assert "observation_id" not in future["rows"][0]
    assert "revision_number" not in future["rows"][0]


@pytest.mark.parametrize("action",["read_registered_contextual_outcome_labels",
    "read_retained_contextual_observation","disclose_retained_contextual_observation",
    "read_retained_source_bar_metadata"])
def test_attachment_disclosure_current_source_and_registration_denials(corpus,published,action):
    cap=attach(corpus,published)
    with pytest.raises(PermissionError):
        outcomes.disclose_contextual_outcomes(cap,policy=Policy({action}))


def test_publication_denial_precedes_writes(corpus):
    from engine.neuralweb import market_memory_contextual_observation_store as observations
    preparation=prepare(corpus)
    before=prices._tree(corpus[0])
    with pytest.raises(PermissionError):
        observations.append_contextual_observations(corpus[0],preparation=preparation,
            policy=Policy({"publish_retained_contextual_observations"}))
    assert prices._tree(corpus[0])==before
    assert not (corpus[0]/"contextual_observations_v1").exists()


def test_cached_pin_rejects_removed_object_and_tampered_payload(corpus,published):
    from engine.neuralweb import market_memory_contextual_observation_store as observations
    identity=published[2][0]
    path=corpus[0]/"contextual_observations_v1"/"observations"/(identity+".json")
    body=path.read_bytes()
    path.write_bytes(body.replace(b'"observed"',b'"corrupt!"'))
    with pytest.raises((outcomes.EpisodeOutcomeError,store.MarketMemoryTechnicalStoreError)):
        attach(corpus,published)
    path.write_bytes(body)
    path.unlink()
    with pytest.raises((outcomes.EpisodeOutcomeError,OSError)):
        observations._disclose_pin(published[1],Policy())


def test_partial_publication_cannot_be_pinned(corpus,monkeypatch):
    from engine.neuralweb import market_memory_contextual_observation_store as observations
    preparation=prepare(corpus)
    def fail(*a,**k):raise OSError("synthetic crash before HEAD")
    monkeypatch.setattr(store,"_replace_head",fail)
    with pytest.raises(OSError):
        observations.append_contextual_observations(corpus[0],preparation=preparation,policy=Policy())
    assert not (corpus[0]/"contextual_observations_v1"/"HEAD.json").exists()
    # Immutable prepared objects alone are never advertised as published.
    assert list((corpus[0]/"contextual_observations_v1"/"generations").glob("*.json"))


def test_publication_never_backdates_to_source_capture(corpus,monkeypatch):
    from engine.neuralweb import market_memory_contextual_observation_store as observations
    preparation=prepare(corpus)
    monkeypatch.setattr(store,"_utc_now",lambda:datetime(2026,8,10,tzinfo=timezone.utc))
    with pytest.raises(outcomes.EpisodeOutcomeError,match="precedes_observation"):
        observations.append_contextual_observations(corpus[0],preparation=preparation,policy=Policy())


def test_no_callback_dict_or_policy_flag_can_replace_generation_capability(corpus,published):
    with pytest.raises(outcomes.EpisodeOutcomeError):
        outcomes.attach_contextual_outcomes(corpus[2],json.loads(published[1]._body),
            observation_ids=published[2],definition_sha256=DEFINITION.disclosure()["definition_sha256"],
            lens="later_observed",outcome_cutoff="2026-08-22T00:00:00Z",policy=Policy())


def test_preparation_cannot_drop_native_source_or_mark_authorization_caps(corpus):
    cap=prepare(corpus)
    for field in ("_marks","_metadata"):
        bad=object.__new__(outcomes.EpisodeOutcomePreparationCapability)
        for name in cap.__slots__:
            object.__setattr__(bad,name,getattr(cap,name))
        object.__setattr__(bad,field,())
        with pytest.raises(outcomes.EpisodeOutcomeError):
            outcomes.disclose_outcome_preparation(bad,policy=Policy())


def test_mark_decoder_materializes_only_named_close_scalars(monkeypatch):
    inputs=prices._bundle().pinned_inputs
    seen=[]
    original=technical._open_spy_parquet
    class Audit:
        def __init__(self,inner):self.inner=inner
        def __getattr__(self,name):return getattr(self.inner,name)
        def read(self,*a,**kw):
            seen.append(("read",kw.get("columns")))
            assert kw.get("columns")==["date"]
            return self.inner.read(*a,**kw)
        def read_row_group(self,*a,**kw):
            seen.append(("row_group",kw.get("columns")))
            assert kw.get("columns")==["close"]
            return self.inner.read_row_group(*a,**kw)
    monkeypatch.setattr(technical,"_open_spy_parquet",lambda body:Audit(original(body)))
    monkeypatch.setattr(technical,"_validated_spy_rows",lambda *a,**k:pytest.fail("whole price frame"))
    marks=technical.read_source_bar_marks(inputs,anchor_session="2026-07-13",target_session="2026-07-20")
    assert len([kind for kind,_ in seen if kind=="row_group"])==2
    assert set(marks)=={"schema","source_observation","anchor","target"}


@pytest.mark.parametrize("anchor,target",[(True,"2026-07-20"),("2026-7-13","2026-07-20"),
    ("2026-07-20","2026-07-13"),("2026-07-13","2026-07-13"),("2026-06-01","2026-07-20")])
def test_mark_sessions_strict_and_never_nearest(anchor,target):
    with pytest.raises(technical.MarketMemoryTechnicalObservationError):
        technical.read_source_bar_marks(prices._bundle().pinned_inputs,
            anchor_session=anchor,target_session=target)


def test_metadata_pin_and_payload_read_current_rights_before_price_object(corpus,published,monkeypatch):
    from engine.neuralweb import market_memory_contextual_observation_store as observations
    original=store._read_raw
    def audit(path,*a,**kw):
        if "contextual_observations_v1/observations/" in str(path):pytest.fail("price payload before rights")
        return original(path,*a,**kw)
    monkeypatch.setattr(store,"_read_raw",audit)
    with pytest.raises(PermissionError):
        attach(corpus,published,policy=Policy({"read_retained_contextual_observation"}))
    # Metadata-only pin itself never opens an observation value body.
    observations._disclose_pin(published[1],Policy())


def test_uncounted_selected_reference_cannot_be_dropped(corpus,published):
    with pytest.raises(outcomes.EpisodeOutcomeError,match="complete_exact"):
        attach(corpus,published,ids=())


def test_instrument_mismatch_is_not_joined_by_ticker(corpus,monkeypatch):
    reader=corpus[3]
    original=reader.read_pinned_capture_receipt
    def changed(*a,**kw):
        value=original(*a,**kw)
        value["subject"]={**value["subject"],"instrument_id":"mmsecurity_"+"f"*64}
        return value
    monkeypatch.setattr(reader,"read_pinned_capture_receipt",changed)
    monkeypatch.setattr(technical,"read_source_bar_marks",lambda *a,**k:pytest.fail("wrong instrument label"))
    with pytest.raises(outcomes.EpisodeOutcomeError,match="instrument_mismatch"):
        prepare(corpus)


@pytest.mark.parametrize("reference",[None,{},True,{"generation_id":"latest","sha256":"f"*64,"bytes":1}])
def test_public_pin_requires_exact_ref_before_owner_io(corpus,monkeypatch,reference):
    from engine.neuralweb import market_memory_contextual_observation_store as observations
    monkeypatch.setattr(observations,"_published_chain",lambda *a,**k:pytest.fail("owner I/O"))
    with pytest.raises((outcomes.EpisodeOutcomeError,store.MarketMemoryTechnicalStoreError)):
        observations.pin_contextual_observation_generation(corpus[0],technical_store_id=corpus[1].store_id,
            exact_generation_ref=reference,policy=Policy())


@pytest.mark.parametrize("action",["read_retained_source_bar_marks","disclose_retained_source_bar_marks"])
def test_persisted_observation_rechecks_original_numerical_purpose_before_body(corpus,published,monkeypatch,action):
    cap=attach(corpus,published)
    original=store._read_raw
    def audit(path,*a,**kw):
        if "contextual_observations_v1/observations/" in str(path):pytest.fail("revoked numerical body")
        return original(path,*a,**kw)
    monkeypatch.setattr(store,"_read_raw",audit)
    with pytest.raises(PermissionError):
        outcomes.disclose_contextual_outcomes(cap,policy=Policy({action}))


def test_registered_deadline_censors_late_source_without_value_decode(corpus,monkeypatch):
    definition=outcomes.RetainedArchivedBarOutcomeDefinition("2026-07-01","2026-07-31","2026-08-01T00:00:00Z")
    monkeypatch.setattr(technical,"read_source_bar_marks",lambda *a,**k:pytest.fail("late label"))
    value=outcomes.disclose_outcome_preparation(prepare(corpus,definition=definition),policy=Policy())
    assert value["rows"][0]["status"]=="censored"
    assert value["rows"][0]["reason"]=="source_observation_after_registered_deadline"
    assert "source_marks" not in value["rows"][0]
    inputs=mark_input(corpus)
    inputs["observation_deadline"]=definition.observation_deadline
    with pytest.raises(store.MarketMemoryTechnicalStoreError,match="after registered deadline"):
        store.read_retained_source_bar_marks(**inputs)


def test_then_known_invariant_across_an_added_future_generation(corpus,monkeypatch):
    from engine.neuralweb import market_memory_contextual_observation_store as observations
    root,native,selection,reader,context_pin=corpus
    monkeypatch.setattr(store,"_utc_now",lambda:datetime(2026,8,18,tzinfo=timezone.utc))
    initial=prepare(corpus)
    monkeypatch.setattr(store,"_utc_now",lambda:datetime(2026,8,19,tzinfo=timezone.utc))
    ref1=observations.append_contextual_observations(root,preparation=initial,policy=Policy())
    pin1=observations.pin_contextual_observation_generation(root,technical_store_id=native.store_id,
        exact_generation_ref=ref1,policy=Policy())
    identity=json.loads(pin1._body)["entries"][0]["observation_id"]
    def view(pin):
        cap=outcomes.attach_contextual_outcomes(selection,pin,observation_ids=(identity,),
            definition_sha256=DEFINITION.disclosure()["definition_sha256"],
            lens="then_known",outcome_cutoff=CUTOFF,policy=Policy())
        return outcomes.disclose_contextual_outcomes(cap,policy=Policy())
    before=view(pin1)
    assert before["rows"][0]["status"]=="observed"
    second_selection=retrieval.retrieve_retained_contexts(selection._cohort,selection._query,
        policy=Policy(),k=2,method=retrieval.RetainedContextMethodSpec(0,0,"historical_hypothetical"))
    monkeypatch.setattr(store,"_utc_now",lambda:datetime(2026,8,21,tzinfo=timezone.utc))
    second=prepare((root,native,second_selection,reader,context_pin),outcome_cutoff="2026-08-22T00:00:00Z")
    ref2=observations.append_contextual_observations(root,preparation=second,policy=Policy())
    assert ref2!=ref1
    pin2=observations.pin_contextual_observation_generation(root,technical_store_id=native.store_id,
        exact_generation_ref=ref2,policy=Policy())
    future=[e["observation_id"] for e in json.loads(pin2._body)["entries"] if e["observation_id"]!=identity]
    assert len(future)==1
    original=store._read_raw
    def audit(path,*a,**kw):
        assert not str(path).endswith(future[0]+".json"),"future observation body read"
        return original(path,*a,**kw)
    monkeypatch.setattr(store,"_read_raw",audit)
    assert view(pin2)==before
    assert before["observation_generation_ref"] is None
    assert before["observation_generation_provenance"]=="withheld_in_then_known"


def test_gap_revision_is_append_only_and_original_exact_pin_replays(tmp_path,monkeypatch):
    from datetime import date
    from engine.neuralweb import market_memory_contextual_observation_store as observations
    corpus=_make_corpus(tmp_path,monkeypatch,sessions=("2026-08-03","2026-08-04","2026-08-05"))
    root,native,selection,reader,context_pin=corpus
    first=prepare(corpus)
    assert outcomes.disclose_outcome_preparation(first,policy=Policy())["rows"][0]["status"]=="proof_pending"
    ref1=observations.append_contextual_observations(root,preparation=first,policy=Policy())
    pin1=observations.pin_contextual_observation_generation(root,technical_store_id=native.store_id,
        exact_generation_ref=ref1,policy=Policy())
    old=json.loads(pin1._body)["entries"][0]
    original_manifest=prices._manifest
    def current_manifest(frame):
        value=original_manifest(frame)
        value["store"]["updated_at"]="2026-08-17T01:35:00.000000+00:00"
        return value
    monkeypatch.setattr(prices,"_manifest",current_manifest)
    candidate=prices._bundle(frame=prices._frame(end=date(2026,8,14)),
        manifest_modified="Mon, 17 Aug 2026 01:37:37 GMT",spy_modified="Mon, 17 Aug 2026 01:32:56 GMT")
    prices._capture(tmp_path,monkeypatch,candidate=candidate,observed_at="2026-08-17T02:00:00Z")
    newer=store.pin_technical_actual_output_generation(root)
    monkeypatch.setattr(store,"_utc_now",lambda:datetime(2026,8,22,tzinfo=timezone.utc))
    second=prepare((root,newer,selection,reader,context_pin),outcome_cutoff="2026-08-22T00:00:00Z")
    ref2=observations.append_contextual_observations(root,preparation=second,policy=Policy())
    pin2=observations.pin_contextual_observation_generation(root,technical_store_id=native.store_id,
        exact_generation_ref=ref2,policy=Policy())
    entries=json.loads(pin2._body)["entries"]
    assert entries[0]==old and len(entries)==2
    assert entries[1]["event_id"]==old["event_id"]
    assert entries[1]["revision_number"]==2
    assert entries[1]["previous_observation_id"]==old["observation_id"]
    for pin,identity,status in ((pin1,old["observation_id"],"proof_pending"),
                               (pin2,entries[1]["observation_id"],"observed")):
        cap=outcomes.attach_contextual_outcomes(selection,pin,observation_ids=(identity,),
            definition_sha256=DEFINITION.disclosure()["definition_sha256"],lens="later_observed",
            outcome_cutoff="2026-08-23T00:00:00Z",policy=Policy())
        assert outcomes.disclose_contextual_outcomes(cap,policy=Policy())["rows"][0]["status"]==status


def test_revoked_e0_before_head_refuses_even_gap_only_publication(corpus,monkeypatch):
    from engine.neuralweb import market_memory_contextual_observation_store as observations
    policy=Policy()
    definition=outcomes.RetainedArchivedBarOutcomeDefinition("2026-07-13","2026-07-14","2026-07-16T00:00:00Z")
    preparation=prepare(corpus,definition=definition,policy=policy)
    assert not preparation._marks
    original=store._write_json_create_once
    def revoke(*a,**kw):
        result=original(*a,**kw)
        policy.denied.add("read_registered_contextual_outcome_labels")
        return result
    monkeypatch.setattr(store,"_write_json_create_once",revoke)
    with pytest.raises(PermissionError):
        observations.append_contextual_observations(corpus[0],preparation=preparation,policy=policy)
    assert not (corpus[0]/"contextual_observations_v1"/"HEAD.json").exists()

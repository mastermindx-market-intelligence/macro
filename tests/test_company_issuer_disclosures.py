"""Synthetic owner contracts only; these fixtures cannot admit any real source."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import json

import pytest

from engine.company_intelligence import issuer_disclosures as d


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class SyntheticStore:
    def __init__(self):
        self.objects = {}
        self.reads = self.writes = self.capabilities = 0
        self.failure = None

    def validate_strict_conditional_write_capability(self):
        self.capabilities += 1

    def get_bytes_strict_bounded(self, key, *, expected_byte_length, max_byte_length):
        self.reads += 1
        result = self.objects.get(key)
        assert expected_byte_length <= max_byte_length == d.MAX_OBJECT_BYTES
        return result

    def put_bytes_strict_conditional(self, key, raw, *, expected_version, content_type):
        self.writes += 1
        assert expected_version is None
        assert len(raw) <= d.MAX_OBJECT_BYTES
        if self.failure == "before":
            raise OSError("synthetic lost acknowledgement, outcome unproven")
        if key in self.objects:
            return False
        self.objects[key] = raw
        if self.failure == "after":
            raise OSError("synthetic acknowledgement lost after commit")
        return True

    def get_bytes_strict_bounded_versioned(self, key, maximum_bytes):
        self.reads += 1
        raw=self.objects.get(key)
        assert raw is None or len(raw)<=maximum_bytes
        return d.VersionedBytes(raw, None if raw is None else sha(raw))


class SyntheticSourceReader:
    def __init__(self, body=None, action=None):
        self.body=body
        self.action=action
        self.calls=[]

    def read_source(self, **binding):
        assert set(binding)=={"disclosure_id","edition_reference","source_sha256","expected_byte_length","max_byte_length"}
        assert 0<binding["expected_byte_length"]<=binding["max_byte_length"]==d.MAX_SOURCE_BYTES
        self.calls.append(binding)
        return self.action() if self.action else self.body


class SyntheticAuthority:
    """Only a test fixture; not an installed authority or a C01 permission."""
    def __init__(self, admission):
        self.admission = admission
        self.calls = 0
        self.change_at = None
        self.deny = False

    def resolve(self, request, candidate=None):
        self.calls += 1
        if self.deny:
            return None
        if self.change_at and self.calls >= self.change_at:
            return replace(self.admission, generation="fixture-revoked-generation")
        return self.admission

    def authorize_publication(self, request, candidate):
        value = self.resolve(request)
        return replace(value, operation="publish") if type(value) is d.Admission else value


@pytest.fixture
def sample():
    body = b"Synthetic Alpha plans to integrate synthetic memory into Beta platform."
    did = d.disclosure_id("cik:0000000001", "fixture-release-1")
    edition = dict(schema=d.EDITION_SCHEMA, disclosure_id=did, issuer_id="cik:0000000001",
                   source_key="fixture-release-1", revision=1, previous=None,
                   source_sha256=sha(body), source_byte_length=len(body), published_date="2026-01-02",
                   published_at=None, publication_precision="date", known_at="2026-01-03T10:00:00Z")
    eref = d.validate_edition(edition)
    fid = d.fact_id(did, "fixture-planned-integration")
    fact = dict(schema=d.FACT_SCHEMA, fact_id=fid, claim_key="fixture-planned-integration",
                disclosure_id=did, edition=eref.payload(), revision=1, previous=None,
                review_revision="1"*64, subject_id="cik:0000000001", object_id="cik:0000000002",
                subject_identity="2"*64, object_identity="3"*64, kind="product_integration",
                lifecycle="planned", product="Synthetic memory", platform="Synthetic Beta",
                amount=None, economic_share=None, span=dict(start_byte=0,end_byte=len(body),text_sha256=sha(body)),
                known_at="2026-01-03T10:01:00Z")
    req = d.Request(fid,"private_ci","fixture-authorized-audience")
    admission = d.Admission(req,d.validate_fact(fact),eref,"fixture-generation-1","fixture:disclosures",
                            "fixture:profile","4"*64,"5"*64,"6"*64,"7"*64,"8"*64,
                            fact["known_at"],"date","current",frozenset({"fact_id","kind","lifecycle","product","platform"}))
    return body,edition,fact,req,SyntheticAuthority(admission),SyntheticStore()


def publish(sample):
    body,edition,fact,req,authority,store=sample
    return d.publish_disclosure(store,authority,req,edition=edition,fact=fact,source_reader=SyntheticSourceReader(body))


def test_positive_private_native_contract_and_repeat_zero_writes(sample):
    body,edition,fact,req,authority,store=sample
    result=publish(sample)
    assert result["status"]=="COMMITTED_OBSERVED" and result["conditional_objects_observed"]==4
    frozen=dict(store.objects); before=store.writes
    repeat=publish(sample)
    assert repeat["status"]=="REPEATED" and store.writes==before
    result=d.read_disclosure(store,authority,req)
    assert result["fact"]=={k:fact[k] for k in authority.admission.allowed_fields}
    assert result["authority"]=="context_only"
    assert store.objects==frozen and store.writes==before
    encoded=json.dumps(result)
    assert body.decode() not in encoded and "text_sha256" not in encoded and "review_revision" not in encoded


@pytest.mark.parametrize("change",["deny","dict","purpose","audience","reference","edition","future","identity","date_history","fields","missing_digest"])
def test_metadata_refusal_before_any_private_io(sample,change):
    body,edition,fact,req,authority,store=sample
    a=authority.admission
    if change=="deny": authority.deny=True
    elif change=="dict": authority.admission={"allow":True}
    elif change=="purpose": authority.admission=replace(a,request=replace(req,purpose="other"))
    elif change=="audience": authority.admission=replace(a,request=replace(req,audience="other"))
    elif change=="reference": authority.admission=replace(a,reference=d.Reference(d.EDITION_SCHEMA,"0"*64,8))
    elif change=="edition": authority.admission=replace(a,edition=d.Reference(d.FACT_SCHEMA,"0"*64,8))
    elif change=="future": authority.admission=replace(a,known_at=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat())
    elif change in {"identity","date_history"}:
        req=replace(req,mode="historical",as_of="2026-01-04T00:00:00Z")
        authority.admission=replace(a,request=req,identity_mode="current" if change=="identity" else "historical",
                                    publication_precision="instant" if change=="identity" else "date")
    elif change=="fields": authority.admission=replace(a,allowed_fields=frozenset({"source_text"}))
    else: authority.admission=replace(a,purpose_revision="")
    with pytest.raises(d.DisclosureError): d.read_disclosure(store,authority,req)
    assert store.reads==store.writes==store.capabilities==0


def test_producer_absent_purpose_does_not_invoke_source_reader(sample):
    body,edition,fact,req,authority,store=sample; authority.deny=True
    with pytest.raises(d.DisclosureError,match="SOURCE_NOT_ADMITTED"):
        d.publish_disclosure(store,authority,req,edition=edition,fact=fact,
                             source_reader=SyntheticSourceReader(action=lambda:pytest.fail("private source read before admission")))
    assert store.reads==store.writes==store.capabilities==0


def test_revoked_generation_after_private_read_never_serializes(sample):
    publish(sample)
    body,edition,fact,req,authority,store=sample
    authority.calls=0;authority.change_at=2
    with pytest.raises(d.DisclosureError,match="ADMISSION_CHANGED"):
        d.read_disclosure(store,authority,req)


def test_revocation_during_source_read_does_not_write(sample):
    body,edition,fact,req,authority,store=sample;authority.change_at=2
    with pytest.raises(d.DisclosureError,match="ADMISSION_CHANGED"): publish(sample)
    assert store.writes==0


def test_lost_write_acknowledgement_reconciles_exact_bytes_without_retry(sample):
    sample[-1].failure="after"
    assert publish(sample)["status"]=="COMMITTED_OBSERVED"
    assert sample[-1].writes==4


def test_unknown_write_effect_is_not_retried(sample):
    sample[-1].failure="before"
    with pytest.raises(d.DisclosureError) as error: publish(sample)
    assert error.value.effect_unknown and error.value.code=="WRITE_EFFECT_UNKNOWN"
    assert sample[-1].writes==1


@pytest.mark.parametrize("time",["2026-01-03","2026-01-03T10:00:00","2026-01-03T10:00:00.0000001Z","2026-01-03T10:00:00.9999999Z"])
def test_temporal_precision_is_not_coerced(sample,time):
    sample[1]["known_at"]=time
    with pytest.raises(d.DisclosureError,match="INSTANT_PRECISION_INVALID"): d.validate_edition(sample[1])


def test_microsecond_precision_preserved_and_date_not_promoted(sample):
    edition=sample[1]; edition["known_at"]="2026-01-03T10:00:00.123456+00:00"
    d.validate_edition(edition)
    assert edition["published_at"] is None
    edition["published_at"]="2026-01-02T00:00:00Z"
    with pytest.raises(d.DisclosureError,match="DATE_IS_NOT_INSTANT"): d.validate_edition(edition)


@pytest.mark.parametrize("field,value",[("revision",True),("kind","corporate_action"),("lifecycle","completed"),("amount",100),("economic_share",0.5),("review_revision",""),("product","X"*257),("subject_id","bad id")])
def test_fact_rejects_coercion_or_unreviewed_promotions(sample,field,value):
    sample[2][field]=value
    with pytest.raises(d.DisclosureError): d.validate_fact(sample[2])


@pytest.mark.parametrize("mutate",["source","span","edition","fact_identity"])
def test_wrong_source_bindings_do_not_write(sample,mutate):
    body,edition,fact,req,authority,store=sample
    if mutate=="source": body=b"wrong bytes"
    elif mutate=="span":
        fact["span"]["text_sha256"]="0"*64;authority.admission=replace(authority.admission,reference=d.validate_fact(fact))
    elif mutate=="edition": fact["edition"]["sha256"]="0"*64
    else: fact["fact_id"]="integration:wrong"
    with pytest.raises(d.DisclosureError):
        d.publish_disclosure(store,authority,req,edition=edition,fact=fact,source_reader=SyntheticSourceReader(body))
    assert store.writes==0


def test_judgment_correction_does_not_create_source_edition(sample):
    publish(sample)
    body,edition,fact,req,authority,store=sample
    first=dict(store.objects); prior=d.validate_fact(fact)
    fact.update(revision=2,previous=prior.payload(),review_revision="9"*64,known_at="2026-01-03T11:00:00Z")
    authority.admission=replace(authority.admission,reference=d.validate_fact(fact),known_at=fact["known_at"],generation="fixture-generation-2")
    result=publish(sample)
    assert result["conditional_objects_observed"]==2
    assert all(store.objects[k]==v for k,v in first.items())
    assert len(store.objects)==6


def test_source_correction_preserves_stable_identity_and_prior_edition(sample):
    publish(sample)
    body,edition,fact,req,authority,store=sample
    olde=d.validate_edition(edition);oldf=d.validate_fact(fact);did=edition["disclosure_id"]
    body+=b" Synthetic correction."
    edition.update(revision=2,previous=olde.payload(),source_sha256=sha(body),source_byte_length=len(body),known_at="2026-01-03T11:00:00Z")
    eref=d.validate_edition(edition)
    fact.update(revision=2,previous=oldf.payload(),edition=eref.payload(),known_at="2026-01-03T11:01:00Z")
    authority.admission=replace(authority.admission,reference=d.validate_fact(fact),edition=eref,known_at=fact["known_at"],generation="fixture-generation-2")
    result=d.publish_disclosure(store,authority,req,edition=edition,fact=fact,source_reader=SyntheticSourceReader(body))
    assert result["conditional_objects_observed"]==4 and edition["disclosure_id"]==did
    assert len(store.objects)==8


def test_wrong_correction_chain_refuses_before_source_retrieval(sample):
    publish(sample)
    body,edition,fact,req,authority,store=sample
    prior=d.validate_fact(fact);fact.update(revision=3,previous=prior.payload())
    authority.admission=replace(authority.admission,reference=d.validate_fact(fact))
    before=store.writes
    with pytest.raises(d.DisclosureError,match="CORRECTION_CHAIN_MISMATCH"):
        d.publish_disclosure(store,authority,req,edition=edition,fact=fact,
                             source_reader=SyntheticSourceReader(action=lambda:pytest.fail("invalid chain must stop first")))
    assert store.writes==before


def test_caller_mutation_during_resolution_cannot_rebind_snapshot(sample):
    body,edition,fact,req,authority,store=sample
    original=authority.resolve
    def mutate(*args):
        result=original(*args);fact["product"]="tampered";return result
    authority.resolve=mutate
    publish(sample)
    result=d.read_disclosure(store,authority,req)
    assert result["fact"]["product"]=="Synthetic memory"


def test_read_authority_does_not_authorize_publication(sample):
    body,edition,fact,req,authority,store=sample
    authority.authorize_publication=lambda request,candidate:authority.admission
    with pytest.raises(d.DisclosureError,match="ADMISSION_OPERATION_MISMATCH"): publish(sample)
    assert store.reads==store.writes==store.capabilities==0


def test_current_query_cannot_borrow_historical_cutoff(sample):
    with pytest.raises(d.DisclosureError,match="CURRENT_CUTOFF_NOT_ALLOWED"):
        replace(sample[3],as_of="2026-01-04T00:00:00Z")


def test_source_instant_preserves_its_original_calendar_day(sample):
    edition=sample[1]
    edition.update(published_at="2026-01-02T23:30:00-05:00",publication_precision="instant")
    d.validate_edition(edition)


def test_sibling_fact_revision_cannot_publish_two_native_values(sample):
    publish(sample)
    body,edition,fact,req,authority,store=sample
    prior=d.validate_fact(fact)
    fact.update(revision=2,previous=prior.payload(),review_revision="9"*64)
    authority.admission=replace(authority.admission,reference=d.validate_fact(fact))
    publish(sample)
    fact["product"]="Conflicting sibling at same native revision"
    authority.admission=replace(authority.admission,reference=d.validate_fact(fact))
    with pytest.raises(d.DisclosureError,match="REVISION_CONFLICT"): publish(sample)


def test_losing_revision_blob_is_not_readable_even_with_selected_reference(sample):
    publish(sample)
    body,edition,fact,req,authority,store=sample
    prior=d.validate_fact(fact)
    fact.update(revision=2,previous=prior.payload(),review_revision="9"*64)
    authority.admission=replace(authority.admission,reference=d.validate_fact(fact))
    publish(sample)
    winner=authority.admission
    fact["product"]="Losing immutable blob"
    loser=d.validate_fact(fact)
    authority.admission=replace(winner,reference=loser)
    with pytest.raises(d.DisclosureError,match="REVISION_CONFLICT"): publish(sample)
    # The content write can precede a failed revision reservation. Its mere
    # existence, or even erroneous owner selection, must not make it readable.
    assert f"company_intelligence/issuer_disclosures/v1/facts/{loser.sha256}.json" in store.objects
    before=store.writes
    with pytest.raises(d.DisclosureError,match="REVISION_CONFLICT"):
        d.read_disclosure(store,authority,req)
    authority.admission=winner
    assert d.read_disclosure(store,authority,req)["fact"]["product"]=="Synthetic memory"
    assert store.writes==before


def test_private_reader_refuses_missing_predecessor(sample):
    publish(sample)
    body,edition,fact,req,authority,store=sample
    prior=d.validate_fact(fact)
    fact.update(revision=2,previous=prior.payload(),review_revision="9"*64)
    authority.admission=replace(authority.admission,reference=d.validate_fact(fact))
    publish(sample)
    del store.objects[f"company_intelligence/issuer_disclosures/v1/facts/{prior.sha256}.json"]
    with pytest.raises(d.DisclosureError,match="PRIVATE_OBJECT_ABSENT"):
        d.read_disclosure(store,authority,req)


@pytest.mark.parametrize("lost_ack",[False,True])
def test_incumbent_localstore_publish_read_repeat(sample,tmp_path,lost_ack):
    from engine.research_vault.r2_store import LocalStore
    body,edition,fact,req,authority,_=sample
    store=LocalStore(tmp_path / "synthetic-native-disclosures")
    original=store.put_bytes_strict_conditional
    calls=[]
    def put(*args,**kwargs):
        calls.append(args[0]); result=original(*args,**kwargs)
        if lost_ack: raise OSError("synthetic lost ack after actual LocalStore put")
        return result
    store.put_bytes_strict_conditional=put
    actual=(body,edition,fact,req,authority,store)
    assert publish(actual)["conditional_objects_observed"]==4
    before=len(calls)
    assert publish(actual)["status"]=="REPEATED"
    assert d.read_disclosure(store,authority,req)["fact"]["product"]==fact["product"]
    assert len(calls)==before==4


def test_actual_localstore_concurrent_siblings_have_one_native_revision(sample,tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from engine.research_vault.r2_store import LocalStore
    body,edition,fact,req,authority,_=sample
    store=LocalStore(tmp_path / "synthetic-concurrent-revisions")
    publish((body,edition,fact,req,authority,store))
    prior=d.validate_fact(fact)
    def sibling(name):
        f=deepcopy(fact);f.update(revision=2,previous=prior.payload(),product=name)
        a=SyntheticAuthority(replace(authority.admission,reference=d.validate_fact(f)))
        try: return publish((body,edition,f,req,a,store))["status"]
        except d.DisclosureError as error: return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(sibling,["Synthetic sibling A","Synthetic sibling B"]))
    assert sorted(results)==["COMMITTED_OBSERVED","REVISION_CONFLICT"]


def test_source_reader_receives_exact_owner_reference_and_prebuffer_bounds(sample):
    body,edition,fact,req,authority,store=sample
    reader=SyntheticSourceReader(body)
    d.publish_disclosure(store,authority,req,edition=edition,fact=fact,source_reader=reader)
    assert reader.calls==[dict(disclosure_id=edition["disclosure_id"],edition_reference=d.validate_edition(edition),
                              source_sha256=sha(body),expected_byte_length=len(body),max_byte_length=d.MAX_SOURCE_BYTES)]


def test_historical_read_requires_and_preserves_real_instant_and_pit_identity(sample):
    body,edition,fact,req,authority,store=sample
    edition.update(published_at="2026-01-02T08:00:00Z",publication_precision="instant")
    eref=d.validate_edition(edition);fact["edition"]=eref.payload()
    req=replace(req,mode="historical",as_of="2026-01-03T10:01:00Z")
    authority.admission=replace(authority.admission,request=req,reference=d.validate_fact(fact),edition=eref,
                                publication_precision="instant",identity_mode="historical")
    actual=(body,edition,fact,req,authority,store)
    publish(actual)
    assert d.read_disclosure(store,authority,req)["fact"]["lifecycle"]=="planned"
    too_early=replace(req,as_of="2026-01-03T10:00:59.999999Z")
    authority.admission=replace(authority.admission,request=too_early)
    before=store.reads
    with pytest.raises(d.DisclosureError,match="FUTURE_KNOWLEDGE"):
        d.read_disclosure(store,authority,too_early)
    assert store.reads==before

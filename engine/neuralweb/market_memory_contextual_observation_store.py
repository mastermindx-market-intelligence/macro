"""Dormant contextual-observation sidecar of the original technical owner.

Uses that owner's private root, writer lock, durable immutable-object writes
and atomic HEAD discipline. Never changes its original capture HEAD/manifest.
No API/CLI calls this module. E0 and publication actions require a trusted
owner policy; the installed metadata-only policy grants neither. Tests use
synthetic stores and explicit policy doubles, not production authorization.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import fcntl
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import stat

from engine.neuralweb import market_memory_technical_store as store
from engine.neuralweb import market_memory_episode_outcomes as outcomes

_NAMESPACE = "contextual_observations_v1"
_MAX_ENTRIES = 256
_MAX_BYTES = 2 * 1024 * 1024
_MAX_OBJECT = 128 * 1024
_TOKEN = object()
_KEY = secrets.token_bytes(32)
_ID = re.compile(r"mmcontextual(?:generation|observation)_[a-f0-9]{64}\Z")


def _canonical(value):
    return store._canonical_bytes(value)


def _identity(prefix, value):
    return prefix + sha256(_canonical(value)).hexdigest()


def _check_id(value, prefix):
    if type(value) is not str or not value.startswith(prefix) or not _ID.fullmatch(value):
        raise outcomes.EpisodeOutcomeError("exact_contextual_owner_identity_required")
    return value


def _resource(store_id):
    return {"profile": store.STORE_PROFILE, "store_id": store_id, "namespace": _NAMESPACE}


def _authorize(policy, action, resource):
    store._authorize_retained_metadata(policy, action, resource)


def _authorize_publication(policy,resource):
    _authorize(policy,"read_registered_contextual_outcome_labels",resource)
    _authorize(policy,"publish_retained_contextual_observations",resource)


def _path(root, category, identity):
    _check_id(identity, "mmcontextualgeneration_" if category == "generations" else "mmcontextualobservation_")
    return store._safe_path(root, _NAMESPACE, category, identity + ".json")


def _validate_reference(reference):
    if type(reference) is not dict or set(reference) != {"generation_id", "sha256", "bytes"}:
        raise outcomes.EpisodeOutcomeError("exact_contextual_generation_ref_required")
    identity = _check_id(reference["generation_id"], "mmcontextualgeneration_")
    store._require_digest(reference["sha256"], field="contextual generation")
    store._require_int(reference["bytes"], field="contextual generation bytes", maximum=_MAX_BYTES)
    return identity


def _manifest(root, reference):
    identity=_validate_reference(reference)
    body = store._read_raw(_path(root, "generations", identity), digest=reference["sha256"],
        expected_bytes=reference["bytes"], limit=_MAX_BYTES, label="contextual observation generation")
    value = json.loads(body)
    if (set(value) != {"schema", "store_id", "generation_id", "previous_generation_ref", "entries"}
            or value["schema"] != "market_memory.contextual_observation_generation.v1"
            or identity != _identity("mmcontextualgeneration_", {k:v for k,v in value.items() if k != "generation_id"})
            or type(value["entries"]) is not list or not 1 <= len(value["entries"]) <= _MAX_ENTRIES
            or body != _canonical(value)):
        raise outcomes.EpisodeOutcomeError("contextual_generation_integrity_required")
    seen = set()
    revisions = {}
    for entry in value["entries"]:
        if (type(entry) is not dict or set(entry) != {"observation_id", "sha256", "bytes",
                "event_id", "revision_number", "previous_observation_id", "published_at",
                "source_resource", "mark_use_resource", "context_ref", "definition_sha256", "e0_registration_sha256"}
                or entry["observation_id"] in seen):
            raise outcomes.EpisodeOutcomeError("contextual_generation_entries_invalid")
        _check_id(entry["observation_id"], "mmcontextualobservation_")
        store._require_digest(entry["sha256"], field="contextual observation")
        store._require_digest(entry["event_id"], field="contextual event")
        store._require_int(entry["bytes"], field="contextual observation bytes", maximum=_MAX_OBJECT)
        store._require_int(entry["revision_number"], field="contextual revision", maximum=_MAX_ENTRIES)
        outcomes._clock(entry["published_at"])
        for key in ("definition_sha256","e0_registration_sha256"):
            store._require_digest(entry[key],field="contextual "+key)
        context=entry["context_ref"]
        if (type(context)is not dict or set(context)!={"context_id","capture_id","packet_sha256",
                "source_session","subject_id","instrument_id","currency"}
                or any(type(v)is not str for v in context.values())):
            raise outcomes.EpisodeOutcomeError("exact_contextual_identity_required")
        outcomes._date(context["source_session"])
        store._require_digest(context["packet_sha256"],field="contextual packet")
        if entry["event_id"]!=sha256(_canonical({"context":context,
                "definition_sha256":entry["definition_sha256"]})).hexdigest():
            raise outcomes.EpisodeOutcomeError("contextual_event_identity_invalid")
        prior=revisions.get(entry["event_id"])
        if (entry["revision_number"]!=(1 if prior is None else prior["revision_number"]+1)
                or entry["previous_observation_id"]!=(None if prior is None else prior["observation_id"])
                or prior is not None and outcomes._clock(entry["published_at"])<outcomes._clock(prior["published_at"])):
            raise outcomes.EpisodeOutcomeError("contextual_observation_revision_chain_invalid")
        revisions[entry["event_id"]]=entry
        if entry["source_resource"] is not None:
            if (type(entry["source_resource"]) is not dict
                    or set(entry["source_resource"]) != set(store._RESOURCE_MARK_FIELDS)
                    or entry["source_resource"]["profile"] != store.STORE_PROFILE):
                raise outcomes.EpisodeOutcomeError("contextual_source_resource_invalid")
            store._require_digest(entry["source_resource"]["generation_sha256"], field="technical source generation")
            mark_use=entry["mark_use_resource"]
            expected=set(store._RESOURCE_MARK_FIELDS)|{"anchor_session","target_session","definition_sha256",
                "e0_registration_sha256","visibility_cutoff","observation_deadline"}
            if (type(mark_use)is not dict or set(mark_use)!=expected
                    or any(mark_use[key]!=v for key,v in entry["source_resource"].items())
                    or any(mark_use[key]!=entry[key] for key in ("definition_sha256","e0_registration_sha256"))):
                raise outcomes.EpisodeOutcomeError("original_numerical_mark_resource_required")
            outcomes._date(mark_use["anchor_session"])
            outcomes._date(mark_use["target_session"])
            outcomes._clock(mark_use["visibility_cutoff"])
            outcomes._clock(mark_use["observation_deadline"])
        elif entry["mark_use_resource"] is not None:
            raise outcomes.EpisodeOutcomeError("unexpected_numerical_mark_resource")
        seen.add(entry["observation_id"])
    return value, body


def _published_chain(root, store_id, exact_ref=None):
    head, _ = store._read_json(store._safe_path(root, _NAMESPACE, "HEAD.json"),
        limit=16 * 1024, label="contextual observation HEAD")
    if set(head) != {"schema", "store_id", "generation_ref"} or head["store_id"] != store_id:
        raise outcomes.EpisodeOutcomeError("contextual_owner_head_invalid")
    if head["schema"] != "market_memory.contextual_observation_head.v1":
        raise outcomes.EpisodeOutcomeError("contextual_owner_head_invalid")
    reference = head["generation_ref"]
    selected = None
    newer = None
    visited = set()
    total_bytes = 0
    for _ in range(_MAX_ENTRIES):
        value, body = _manifest(root, reference)
        total_bytes+=len(body)
        if total_bytes>64*1024*1024:
            raise outcomes.EpisodeOutcomeError("contextual_ancestry_byte_limit")
        if value["store_id"] != store_id or value["generation_id"] in visited:
            raise outcomes.EpisodeOutcomeError("contextual_owner_ancestry_invalid")
        visited.add(value["generation_id"])
        if newer is not None and (len(newer["entries"]) <= len(value["entries"])
                or newer["entries"][:len(value["entries"])] != value["entries"]):
            raise outcomes.EpisodeOutcomeError("contextual_owner_ancestry_prefix_invalid")
        if (exact_ref is None and selected is None) or reference == exact_ref:
            selected = (value, body, reference)
        previous = value["previous_generation_ref"]
        if previous is None:
            if selected is None:
                raise outcomes.EpisodeOutcomeError("contextual_generation_not_published")
            return selected
        newer, reference = value, previous
    raise outcomes.EpisodeOutcomeError("contextual_owner_ancestry_limit")


def _context(row, preparation):
    return {**{key:row["selected"]["candidate"][key] for key in ("context_id", "capture_id", "packet_sha256")},
            "source_session": row["source_session"],
            **{key:row["subject"][key] for key in ("subject_id", "instrument_id", "currency")}}


def _core(row):
    # Rank and distance belong to the immutable selection, not event identity.
    return {k:v for k,v in row.items() if k not in ("rank", "selected")}


def append_contextual_observations(technical_root, *, preparation, policy):
    """Explicit original-owner publication; never called by source preparation.

    Idempotence preserves already-published clocks. A changed event appends an
    immutable revision. The original capture publisher and exporter are not
    invoked, restarted, adopted or modified by this sidecar operation.
    """
    value = outcomes.disclose_outcome_preparation(preparation, policy=policy)
    if value["lens"] != "later_observed" or not value["rows"]:
        raise outcomes.EpisodeOutcomeError("nonempty_later_observation_preparation_required")
    resource = {**_resource(value["technical_generation"]["store_id"]),
        "definition_sha256": value["definition"]["definition_sha256"],
        "e0_registration_sha256": value["e0_registration_sha256"]}
    _authorize_publication(policy,resource)
    root = store.validate_technical_actual_output_store_root(technical_root)
    actual = store.pin_technical_actual_output_generation(root,
        generation_id=value["technical_generation"]["generation_id"], maximum_capture_count=256)
    if any(getattr(actual,k) != v for k,v in value["technical_generation"].items()):
        raise outcomes.EpisodeOutcomeError("contextual_publication_technical_owner_mismatch")
    flags = os.O_RDONLY | getattr(os,"O_DIRECTORY",0) | getattr(os,"O_NOFOLLOW",0)
    descriptor = os.open(root, flags)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        outcomes.disclose_outcome_preparation(preparation, policy=policy)
        head_path = store._safe_path(root, _NAMESPACE, "HEAD.json")
        if os.path.lexists(head_path):
            previous, _, previous_ref = _published_chain(root, actual.store_id)
            entries = list(previous["entries"])
        else:
            entries, previous_ref = [], None
        now = store._sample_first_observed_at()  # Actual separate publication clock.
        additions = []
        for row in value["rows"]:
            context = _context(row, preparation)
            core = _core(row)
            # Read-at is not event identity and a repeated read is not a correction.
            if "source_marks" in core:
                core = json.loads(_canonical(core))
                core["source_marks"].pop("marks_read_at")
                core["source_marks"].pop("visibility_cutoff")
                core.update(status="observed",value_q18=core.pop("proposed_value_q18"),
                            reason="exact_retained_source_marks")
            event_id = sha256(_canonical({"context":context,
                "definition_sha256":resource["definition_sha256"]})).hexdigest()
            prior = [entry for entry in entries if entry["event_id"] == event_id]
            old = None
            if prior:
                latest = prior[-1]
                prior_pin=ContextualObservationGenerationCapability(root,_canonical(previous),
                    previous_ref,policy.policy_id,_key=_TOKEN)
                old=_read_observation(prior_pin,latest,cutoff=now,policy=policy)
                if old is None:
                    raise outcomes.EpisodeOutcomeError("publication_clock_precedes_existing_revision")
                if old["core"] == core:
                    continue
            observed_at = row.get("source_marks",{}).get("marks_read_at",now)
            if outcomes._clock(observed_at) > outcomes._clock(now):
                raise outcomes.EpisodeOutcomeError("contextual_publication_clock_precedes_observation")
            observation = {"schema":"market_memory.contextual_observation.v1", "event_id":event_id,
                "context_ref":context, "definition_sha256":resource["definition_sha256"],
                "definition":value["definition"],
                "e0_registration_sha256":resource["e0_registration_sha256"], "core":core,
                "revision_number":len(prior)+1,
                "previous_observation_id":prior[-1]["observation_id"] if prior else None,
                "revision_reason":"source_or_observation_revision" if prior else "initial_observation",
                "clocks":{"observed_at":observed_at,"published_at":now,"recorded_at":now}}
            identity = _identity("mmcontextualobservation_",observation)
            observation["observation_id"] = identity
            body = _canonical(observation)
            if len(body)>_MAX_OBJECT:
                raise outcomes.EpisodeOutcomeError("contextual_observation_byte_limit")
            entry={key:observation[key] for key in ("event_id","revision_number","previous_observation_id",
                "context_ref","definition_sha256","e0_registration_sha256")}
            entry.update(observation_id=identity,sha256=sha256(body).hexdigest(),bytes=len(body),
                published_at=now,source_resource=None if "source_marks" not in row else {
                    key:row["source_marks"][key] for key in store._RESOURCE_MARK_FIELDS},
                mark_use_resource=None if "source_marks" not in row else {
                    key:row["source_marks"][key] for key in (*store._RESOURCE_MARK_FIELDS,"anchor_session",
                        "target_session","definition_sha256","e0_registration_sha256","visibility_cutoff",
                        "observation_deadline")})
            additions.append((entry,body))
        if not additions:
            return previous_ref
        if len(entries)+len(additions)>_MAX_ENTRIES:
            raise outcomes.EpisodeOutcomeError("contextual_observation_entry_limit")
        entries += [entry for entry,_ in additions]
        generation={"schema":"market_memory.contextual_observation_generation.v1","store_id":actual.store_id,
            "previous_generation_ref":previous_ref,"entries":entries}
        generation["generation_id"]=_identity("mmcontextualgeneration_",generation)
        body=_canonical(generation)
        if len(body)>_MAX_BYTES:
            raise outcomes.EpisodeOutcomeError("contextual_generation_byte_limit")
        _authorize_publication(policy,resource)
        for entry,object_body in additions:
            store._write_json_create_once(root,_path(root,"observations",entry["observation_id"]),
                object_body,label="contextual observation",limit=_MAX_OBJECT)
        store._write_json_create_once(root,_path(root,"generations",generation["generation_id"]),
            body,label="contextual observation generation",limit=_MAX_BYTES)
        reference={"generation_id":generation["generation_id"],"sha256":sha256(body).hexdigest(),"bytes":len(body)}
        outcomes.disclose_outcome_preparation(preparation,policy=policy)
        _authorize_publication(policy,resource)
        sidecar=store._safe_path(root,_NAMESPACE)
        store.market_memory_pit._ensure_store_directory_chain(root,sidecar)
        store._replace_head(sidecar,{"schema":"market_memory.contextual_observation_head.v1",
            "store_id":actual.store_id,"generation_ref":reference})
        return reference
    finally:
        fcntl.flock(descriptor,fcntl.LOCK_UN)
        os.close(descriptor)


@dataclass(frozen=True,slots=True,init=False)
class ContextualObservationGenerationCapability:
    _root: Path
    _body: bytes
    _reference: bytes
    _policy_id: str
    _seal: bytes

    def __init__(self,root,body,reference,policy_id,*,_key=None):
        if _key is not _TOKEN:
            raise outcomes.EpisodeOutcomeError("owner_verified_observation_generation_required")
        for key,value in (("_root",root),("_body",body),("_reference",_canonical(reference)),("_policy_id",policy_id)):
            object.__setattr__(self,key,value)
        object.__setattr__(self,"_seal",hmac.digest(_KEY,os.fsencode(root)+body+_canonical(reference)+policy_id.encode(),"sha256"))


def pin_contextual_observation_generation(technical_root, *, technical_store_id, exact_generation_ref, policy):
    # None means current HEAD only for the internal publisher. A public pin
    # cannot silently substitute the latest generation for an absent exact ref.
    _validate_reference(exact_generation_ref)
    resource=_resource(technical_store_id)
    _authorize(policy,"read_retained_contextual_observation_metadata",resource)
    root=store.validate_technical_actual_output_store_root(technical_root)
    value,body,reference=_published_chain(root,technical_store_id,exact_generation_ref)
    # Stat every referenced object before claiming complete manifest membership;
    # price bodies are intentionally NOT opened by this metadata-only pin.
    for entry in value["entries"]:
        path=_path(root,"observations",entry["observation_id"])
        metadata=path.lstat()
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_mode & 0o077
                or metadata.st_uid!=os.geteuid() or metadata.st_size!=entry["bytes"]):
            raise outcomes.EpisodeOutcomeError("contextual_generation_object_missing_or_unsafe")
    _authorize(policy,"read_retained_contextual_observation_metadata",resource)
    return ContextualObservationGenerationCapability(root,body,reference,policy.policy_id,_key=_TOKEN)


def _disclose_pin(capability,policy):
    if (type(capability) is not ContextualObservationGenerationCapability
            or type(capability._body) is not bytes or len(capability._body)>_MAX_BYTES
            or capability._policy_id!=getattr(policy,"policy_id",None)
            or type(capability._seal) is not bytes
            or not hmac.compare_digest(capability._seal,hmac.digest(_KEY,
                os.fsencode(capability._root)+capability._body+capability._reference+capability._policy_id.encode(),"sha256"))):
        raise outcomes.EpisodeOutcomeError("owner_verified_observation_generation_required")
    manifest=json.loads(capability._body)
    reference=json.loads(capability._reference)
    fresh=pin_contextual_observation_generation(capability._root,technical_store_id=manifest["store_id"],
        exact_generation_ref=reference,policy=policy)
    if fresh._body!=capability._body:
        raise outcomes.EpisodeOutcomeError("contextual_generation_changed")
    return manifest


def _read_observation(capability, entry, *, cutoff, policy):
    """Authorize metadata before any visible observation/label body is read."""
    if outcomes._clock(entry["published_at"]) > outcomes._clock(cutoff):
        return None
    resource={**_resource(json.loads(capability._body)["store_id"]),
        "definition_sha256":entry["definition_sha256"],
        "e0_registration_sha256":entry["e0_registration_sha256"],
        "observation_id":entry["observation_id"],"context_ref":entry["context_ref"]}
    _authorize(policy,"read_registered_contextual_outcome_labels",resource)
    _authorize(policy,"read_retained_contextual_observation",resource)
    source=entry["source_resource"]
    if source is not None:
        store._marks_authorization(policy,entry["mark_use_resource"])
        store._marks_authorization(policy,entry["mark_use_resource"],disclose=True)
        _authorize(policy,"read_retained_source_bar_generation_metadata",{
            key:value for key,value in source.items() if key!="source_observation_id"})
        native=store.pin_technical_actual_output_generation(capability._root,
            generation_id=source["generation_id"],maximum_capture_count=256)
        if native.store_id!=source["store_id"] or native.generation_sha256!=source["generation_sha256"]:
            raise outcomes.EpisodeOutcomeError("published_observation_source_pin_mismatch")
        # Original source-choice metadata rights remain current for all sources
        # that influenced the choice, including unreturned source observations.
        for identity in sorted({item.source_observation_id for item in native.captures}):
            metadata=store.read_retained_source_bar_metadata(capability._root,
                technical_pin=native,source_observation_id=identity,policy=policy)
            store.disclose_retained_source_bar_metadata(metadata,policy=policy)
    body=store._read_raw(_path(capability._root,"observations",entry["observation_id"]),
        digest=entry["sha256"],expected_bytes=entry["bytes"],limit=_MAX_OBJECT,
        label="exact published contextual observation")
    value=json.loads(body)
    if (set(value)!={"schema","event_id","context_ref","definition_sha256","definition","e0_registration_sha256",
            "core","revision_number","previous_observation_id","revision_reason","clocks","observation_id"}
            or value["schema"]!="market_memory.contextual_observation.v1"
            or value["observation_id"]!=_identity("mmcontextualobservation_",{
                k:v for k,v in value.items() if k!="observation_id"}) or body!=_canonical(value)
            or any(value[key]!=entry[key] for key in ("observation_id","event_id","context_ref",
                "definition_sha256","e0_registration_sha256","revision_number","previous_observation_id"))
            or value["clocks"]["published_at"]!=entry["published_at"]):
        raise outcomes.EpisodeOutcomeError("published_observation_integrity_required")
    declared=value["definition"]
    definition=outcomes.RetainedArchivedBarOutcomeDefinition(declared["first_session"],
        declared["last_session"],declared["observation_deadline"])
    if definition.disclosure()!=declared or declared["definition_sha256"]!=value["definition_sha256"]:
        raise outcomes.EpisodeOutcomeError("published_observation_definition_mismatch")
    times=value["clocks"]
    if (set(times)!={"observed_at","published_at","recorded_at"}
            or outcomes._clock(times["observed_at"])>outcomes._clock(times["published_at"])
            or outcomes._clock(times["published_at"])>outcomes._clock(times["recorded_at"])):
        raise outcomes.EpisodeOutcomeError("published_observation_clock_order_invalid")
    if any(outcomes._clock(time)>outcomes._clock(cutoff) for time in times.values()):
        return None
    marks=value["core"].get("source_marks")
    if source is not None:
        if (type(marks)is not dict or any(marks[key]!=value for key,value in source.items())
                or any(marks[key]!=v for key,v in entry["mark_use_resource"].items() if key!="visibility_cutoff")
                or marks["anchor_session"]!=value["context_ref"]["source_session"]
                or marks["target_session"]!=outcomes._target(value["context_ref"]["source_session"],definition)
                or outcomes._clock(marks["source_first_observed_at"])>outcomes._clock(definition.observation_deadline)
                or any(outcomes._clock(marks[key])>outcomes._clock(cutoff)
                       for key in ("source_available_at","source_first_observed_at"))
                or value["core"]["value_q18"]!=outcomes._ratio(marks)
                or value["core"]["status"]!="observed"):
            raise outcomes.EpisodeOutcomeError("published_mark_source_or_value_mismatch")
        store._marks_authorization(policy,entry["mark_use_resource"])
        store._marks_authorization(policy,entry["mark_use_resource"],disclose=True)
    elif marks is not None or value["core"]["value_q18"] is not None:
        raise outcomes.EpisodeOutcomeError("unqualified_contextual_mark_value")
    _authorize(policy,"read_registered_contextual_outcome_labels",resource)
    _authorize(policy,"disclose_retained_contextual_observation",resource)
    return value

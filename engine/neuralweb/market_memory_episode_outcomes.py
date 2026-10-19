"""Selection-immutable L0 preparation over the original technical source owner.

All production effects are dormant: no installed policy grants these actions,
no API mounts this module, and no metadata object admits an E0 study. Pure
synthetic tests are not actual label access, publication or research acceptance.
A source mark read is NOT contextual-observation publication. Preparation keeps
those clocks separate and may only become a product attachment through a
separately published, exactly pinned observation generation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from fractions import Fraction
from hashlib import sha256
import hmac
import json
import secrets

from engine.neuralweb import market_memory_episode_retrieval as retrieval
from engine.neuralweb import market_memory_episode_features as features
from engine.neuralweb import market_memory_retained_context_cohort as cohort
from engine.neuralweb import market_memory_technical_store as store
from engine.neuralweb import market_memory_technical_observation as technical
from engine.neuralweb import market_memory_trusted as trusted

_MAX_BYTES = 2 * 1024 * 1024
_TOKEN = object()
_KEY = secrets.token_bytes(32)
PROFILE = "spy_retained_source_observation_unadjusted_daily_close_ratio_5_xnys_sessions.v1"


class EpisodeOutcomeError(ValueError):
    """A source, clock, capability or exact selection join was refused."""


def _clock(value):
    try:
        return cohort.utc_instant(value)
    except (TypeError, ValueError) as exc:
        raise EpisodeOutcomeError("exact_outcome_clock_required") from exc


def _date(value):
    if type(value) is not str:
        raise EpisodeOutcomeError("exact_outcome_session_required")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise EpisodeOutcomeError("exact_outcome_session_required") from exc
    if parsed.isoformat() != value:
        raise EpisodeOutcomeError("exact_outcome_session_required")
    return parsed


@dataclass(frozen=True, slots=True)
class RetainedArchivedBarOutcomeDefinition:
    """Explicit prelabel definition metadata, never source or study authority.

    Window/deadline are required actual registration inputs. This constructor
    never fills unknown original metadata or silently converts the separately
    frozen same-session-capture outcome profile into this archive profile.
    """
    first_session: str
    last_session: str
    observation_deadline: str

    def __post_init__(self):
        first, last = _date(self.first_session), _date(self.last_session)
        if first > last or first.year < 1962 or last.year > 2100:
            raise EpisodeOutcomeError("supported_outcome_window_required")
        if _clock(self.observation_deadline).date() <= last:
            raise EpisodeOutcomeError("explicit_post_window_observation_deadline_required")

    def disclosure(self):
        value = {"schema": "market_memory.retained_archived_bar_outcome_definition.v1",
                 "profile": PROFILE, "source_profile": store.STORE_PROFILE,
                 "calendar_sha256": technical._CALENDAR_SHA256_V1,
                 "price_subject": technical._canary_config_v1()["subject"],
                 "price_basis": technical._PRICE_BASIS,
                 "horizon_xnys_sessions": 5, "anchor_rule": "original_house_source_session",
                 "source_choice": "coverage_then_earliest_first_observed_at_then_source_id",
                 "metric": "target_close_divided_by_anchor_close",
                 "numeric_convention": "exact_integer_ratio_to_q18_half_even_once",
                 "first_session": self.first_session, "last_session": self.last_session,
                 "observation_deadline": self.observation_deadline,
                 "economic_return": False, "RTH_close_authenticated": False,
                 "corporate_action_adjusted": False}
        # Detach the native source basis object; no caller can mutate its owner.
        value = json.loads(cohort.canonical(value))
        return {**value, "definition_sha256": sha256(cohort.canonical(value)).hexdigest()}


def _target(anchor, definition):
    session = _date(anchor)
    if not definition.first_session <= anchor <= definition.last_session:
        raise EpisodeOutcomeError("anchor_outside_registered_window")
    if not technical.is_frozen_v1_xnys_session(session):
        raise EpisodeOutcomeError("anchor_not_registered_xnys_session")
    count = 0
    for _ in range(32):
        session += timedelta(days=1)
        if session.year > 2100:
            raise EpisodeOutcomeError("outcome_calendar_unavailable")
        if technical.is_frozen_v1_xnys_session(session):
            count += 1
            if count == 5:
                if session.isoformat() > definition.last_session:
                    raise EpisodeOutcomeError("target_outside_registered_window")
                return session.isoformat()
    raise EpisodeOutcomeError("outcome_calendar_unavailable")


def _ratio(marks):
    def number(row):
        ratio = row["close_integer_ratio"]
        return Fraction(int(ratio["numerator"]), int(ratio["denominator"]))
    value = number(marks["target"]) / number(marks["anchor"])
    numerator = value.numerator * 10**18
    integer, remainder = divmod(numerator, value.denominator)
    if remainder * 2 > value.denominator or (remainder * 2 == value.denominator and integer % 2):
        integer += 1
    return f"{integer // 10**18}.{integer % 10**18:018d}"


def _seal(body, policy_id):
    return hmac.digest(_KEY, body + policy_id.encode("utf-8"), "sha256")


@dataclass(frozen=True, slots=True, init=False)
class EpisodeOutcomePreparationCapability:
    _body: bytes
    _selection: retrieval.EpisodeRetrievalCapability
    _metadata: tuple
    _marks: tuple
    _policy_id: str
    _seal: bytes

    def __init__(self, body, selection, metadata, marks, policy_id, *, _key=None):
        if _key is not _TOKEN:
            raise EpisodeOutcomeError("owner_verified_outcome_preparation_required")
        object.__setattr__(self, "_body", body)
        object.__setattr__(self, "_selection", selection)
        object.__setattr__(self, "_metadata", tuple(metadata))
        object.__setattr__(self, "_marks", tuple(marks))
        object.__setattr__(self, "_policy_id", policy_id)
        object.__setattr__(self, "_seal", _seal(body, policy_id))


def prepare_contextual_outcomes(selection, *, technical_root, technical_pin,
        context_reader, context_generation,
        definition: RetainedArchivedBarOutcomeDefinition, e0_registration_sha256: str,
        lens: str, outcome_cutoff: str, policy: object):
    """Prepare exact original-owner observations AFTER immutable selection.

    ``policy`` is supplied by trusted owner construction, never an API argument.
    Registration hashes merely select the admission that policy must actually
    authenticate. The current metadata-only CLI policy cannot authorize labels.
    No source absence, maturity or publication is inferred from a missing row.
    """
    selected = retrieval.disclose_episode_retrieval(selection, policy=policy)
    if (type(context_reader) is not trusted.TrustedFileAsKnownAtReader
            or type(context_generation) is not store.market_memory_pit.PinnedGenerationSnapshot
            or any(getattr(context_generation, key) != selected["query_owner"][key]
                   for key in ("store_id", "generation_id", "generation_sha256"))):
        raise EpisodeOutcomeError("exact_selected_context_owner_required")
    if type(definition) is not RetainedArchivedBarOutcomeDefinition:
        raise EpisodeOutcomeError("registered_archived_bar_definition_required")
    store._require_digest(e0_registration_sha256, field="E0 registration")
    if lens not in ("then_known", "later_observed"):
        raise EpisodeOutcomeError("explicit_outcome_lens_required")
    query_cutoff = selected["query_owner"]["query_cutoff"]
    cutoff, original = _clock(outcome_cutoff), _clock(query_cutoff)
    if (lens == "then_known" and cutoff != original) or (lens == "later_observed" and cutoff < original):
        raise EpisodeOutcomeError("outcome_lens_cutoff_mismatch")
    if type(technical_pin) is not store.PinnedTechnicalGenerationSnapshot:
        raise EpisodeOutcomeError("exact_original_technical_pin_required")
    declared = definition.disclosure()
    metadata_caps, metadata_values, mark_caps = [], [], []
    # The owner authenticates a complete exact generation; callers cannot pass
    # a convenient partial source list or choose a source using price quality.
    with store.market_memory_pit.bounded_owner_reads(maximum_bytes=64 * 1024 * 1024):
        store._authorize_retained_metadata(policy, "read_retained_source_bar_generation_metadata",
            {"profile": store.STORE_PROFILE, **{key: getattr(technical_pin, key)
                for key in ("store_id", "generation_id", "generation_sha256")}})
        fresh = store.pin_technical_actual_output_generation(technical_root,
            generation_id=technical_pin.generation_id, maximum_capture_count=256)
        if fresh != technical_pin:
            raise EpisodeOutcomeError("exact_technical_generation_mismatch")
        for source_id in sorted({entry.source_observation_id for entry in technical_pin.captures}):
            cap = store.read_retained_source_bar_metadata(technical_root,
                technical_pin=technical_pin, source_observation_id=source_id, policy=policy)
            metadata_caps.append(cap)
            metadata_values.append(store.disclose_retained_source_bar_metadata(cap, policy=policy))
        feature_values = {}
        for cap in selection._compared:
            value = features.disclose_episode_features(cap, policy=policy, for_comparison=True)
            feature_values[value["context_id"]] = value
        rows = []
        for rank, comparison in enumerate(selected["selected"], 1):
            candidate = comparison["candidate"]
            projection = feature_values[candidate["context_id"]]
            if any(projection[key] != candidate[key] for key in
                   ("context_id", "capture_id", "packet_sha256")):
                raise EpisodeOutcomeError("selected_context_projection_mismatch")
            anchor = projection["measurement_period"]["value"]
            resource = {**projection["owner"]}
            features._policy(policy, "read_retained_macro_capture_metadata", {
                key:value for key,value in resource.items() if key != "subject_id"}
                | {"requested_subject_id": resource["subject_id"]})
            receipt = context_reader.read_pinned_capture_receipt(context_generation,
                query_id=resource["query_id"])
            if any(receipt[key] != candidate[key] for key in ("context_id", "capture_id", "packet_sha256")):
                raise EpisodeOutcomeError("selected_context_identity_receipt_mismatch")
            subject = receipt["subject"]
            if any(subject.get(key) != declared["price_subject"][key]
                   for key in ("subject_id", "instrument_id")):
                raise EpisodeOutcomeError("registered_price_subject_instrument_mismatch")
            # House receipts retain opaque subject/instrument IDs, not a
            # currency field. Currency comes from the registered price owner's
            # authenticated identity bound to that exact instrument ID.
            subject = {**subject, "currency": declared["price_subject"]["currency"],
                       "currency_basis": "registered_price_owner_identity"}
            row = {"rank": rank, "selected": comparison, "source_session": anchor,
                   "subject": subject,
                   "status": "proof_pending", "value_q18": None,
                   "reason": "source_or_observation_proof_pending"}
            if lens == "then_known":
                # A retained source predating the query is not proof that a
                # contextual observation had been published then. Only the
                # separate exact observation-generation reader can establish
                # that. Preparation must not decode labels for this lens.
                row.update(reason="not_visible_at_query")
                rows.append(row)
                continue
            try:
                target = _target(anchor, definition)
            except EpisodeOutcomeError as exc:
                row.update(status="censored", reason=str(exc))
                rows.append(row)
                continue
            eligible = [(value, cap) for value, cap in zip(metadata_values, metadata_caps, strict=True)
                if all(value["subject"].get(key) == subject.get(key) and subject.get(key) is not None
                       for key in ("subject_id", "instrument_id", "currency"))
                and anchor in value["bar_sessions"] and target in value["bar_sessions"]]
            eligible.sort(key=lambda pair: (_clock(pair[0]["first_observed_at"]), pair[0]["source_observation_id"]))
            if not eligible:
                if lens == "then_known":
                    row.update(reason="not_visible_at_query")
                rows.append(row)
                continue
            if len(eligible) > 1 and (_clock(eligible[0][0]["first_observed_at"])
                                     == _clock(eligible[1][0]["first_observed_at"])):
                row.update(status="censored", reason="ambiguous_source_observation_clock")
                rows.append(row)
                continue
            metadata, cap = eligible[0]
            # Future existence/status/source IDs are withheld, not just values.
            if any(_clock(metadata[key]) > cutoff for key in ("first_observed_at", "available_at")):
                row.update(reason="not_visible_at_query" if lens == "then_known" else "not_visible_at_cutoff")
                rows.append(row)
                continue
            if any(_clock(metadata[key]) > _clock(definition.observation_deadline)
                   for key in ("first_observed_at", "available_at")):
                row.update(status="censored", reason="source_observation_after_registered_deadline")
                rows.append(row)
                continue
            marks_cap = store.read_retained_source_bar_marks(technical_root,
                technical_pin=technical_pin, metadata=cap, anchor_session=anchor, target_session=target,
                definition_sha256=declared["definition_sha256"],
                e0_registration_sha256=e0_registration_sha256, visibility_cutoff=outcome_cutoff,
                observation_deadline=definition.observation_deadline, policy=policy)
            mark_caps.append(marks_cap)
            marks = store.disclose_retained_source_bar_marks(marks_cap, policy=policy)
            row.update(reason="contextual_observation_not_published", target_session=target,
                       proposed_value_q18=_ratio(marks), source_marks=marks)
            rows.append(row)
        value = {"schema": "market_memory.episode_outcome_preparation.v1",
            "retrieval_id": selected["retrieval_id"], "selection_sha256": selected["selection_sha256"],
            "query_cutoff": query_cutoff, "outcome_cutoff": outcome_cutoff, "lens": lens,
            "definition": declared, "e0_registration_sha256": e0_registration_sha256,
            "technical_generation": {key: getattr(technical_pin, key) for key in
                ("store_id", "generation_id", "generation_sha256")},
            "source_metadata_refs": [{"source_observation_id": item["source_observation_id"],
                "body_sha256": sha256(cap._body).hexdigest()}
                for item,cap in zip(metadata_values,metadata_caps,strict=True)],
            "rows": rows, "denominator": selected["denominator"],
            "operational_admission": False, "contextual_observations_published": False,
            "effective_n": "not_estimated", "economic_return": False,
            "corporate_action_adjusted": False, "RTH_close_authenticated": False}
        body = cohort.canonical(value)
        if len(body) > _MAX_BYTES:
            raise EpisodeOutcomeError("outcome_preparation_byte_limit")
        cap = EpisodeOutcomePreparationCapability(body, selection, metadata_caps, mark_caps,
            policy.policy_id, _key=_TOKEN)
        disclose_outcome_preparation(cap, policy=policy)
        return cap


def disclose_outcome_preparation(capability, *, policy: object):
    """Internal owner preparation only; NOT the retained product API response."""
    if (type(capability) is not EpisodeOutcomePreparationCapability
            or type(capability._body) is not bytes or len(capability._body) > _MAX_BYTES
            or capability._policy_id != getattr(policy, "policy_id", None)
            or type(capability._seal) is not bytes
            or not hmac.compare_digest(capability._seal, _seal(capability._body, capability._policy_id))):
        raise EpisodeOutcomeError("owner_verified_outcome_preparation_required")
    selection = retrieval.disclose_episode_retrieval(capability._selection, policy=policy)
    value = json.loads(capability._body)
    references=[]
    for cap in capability._metadata:
        item=store.disclose_retained_source_bar_metadata(cap, policy=policy)
        references.append({"source_observation_id":item["source_observation_id"],
                           "body_sha256":sha256(cap._body).hexdigest()})
    if references!=value["source_metadata_refs"]:
        raise EpisodeOutcomeError("complete_original_source_metadata_capabilities_required")
    expected=[row["source_marks"] for row in value["rows"] if "source_marks" in row]
    if len(expected)!=len(capability._marks):
        raise EpisodeOutcomeError("complete_original_mark_capabilities_required")
    for wanted,cap in zip(expected,capability._marks,strict=True):
        if store.disclose_retained_source_bar_marks(cap,policy=policy)!=wanted:
            raise EpisodeOutcomeError("original_mark_capability_changed")
    if (value["selection_sha256"] != selection["selection_sha256"]
            or value["retrieval_id"] != selection["retrieval_id"]
            or [row["selected"] for row in value["rows"]] != selection["selected"]):
        raise EpisodeOutcomeError("original_outcome_selection_changed")
    retrieval.disclose_episode_retrieval(capability._selection, policy=policy)
    return value


@dataclass(frozen=True, slots=True, init=False)
class EpisodeOutcomeAttachmentCapability:
    _body: bytes
    _selection: retrieval.EpisodeRetrievalCapability
    _observation_pin: object
    _ids: tuple
    _definition: str
    _lens: str
    _cutoff: str
    _policy_id: str
    _seal: bytes

    def __init__(self,body,selection,pin,ids,definition,lens,cutoff,policy_id,*,_key=None):
        if _key is not _TOKEN:
            raise EpisodeOutcomeError("owner_verified_outcome_attachment_required")
        for name,value in (("_body",body),("_selection",selection),("_observation_pin",pin),
                ("_ids",ids),("_definition",definition),("_lens",lens),("_cutoff",cutoff),("_policy_id",policy_id)):
            object.__setattr__(self,name,value)
        object.__setattr__(self,"_seal",_seal(body,policy_id))


def _attachment_value(selection,pin,ids,definition,lens,cutoff,policy):
    from engine.neuralweb import market_memory_contextual_observation_store as observations
    original=retrieval.disclose_episode_retrieval(selection,policy=policy)
    store._require_digest(definition,field="outcome definition")
    query_cutoff=original["query_owner"]["query_cutoff"]
    if (lens not in ("then_known","later_observed")
            or lens=="then_known" and _clock(cutoff)!=_clock(query_cutoff)
            or lens=="later_observed" and _clock(cutoff)<_clock(query_cutoff)):
        raise EpisodeOutcomeError("outcome_lens_cutoff_mismatch")
    if type(ids)is not tuple or len(ids)!=len(original["selected"]):
        raise EpisodeOutcomeError("complete_exact_observation_reference_tuple_required")
    manifest=observations._disclose_pin(pin,policy)
    by_id={row["observation_id"]:row for row in manifest["entries"]}
    rows=[]
    with store.market_memory_pit.bounded_owner_reads(maximum_bytes=64*1024*1024):
        for rank,(comparison,identity) in enumerate(zip(original["selected"],ids,strict=True),1):
            if identity is not None:
                observations._check_id(identity,"mmcontextualobservation_")
            row={"rank":rank,"selected":comparison,"status":"proof_pending","value_q18":None,
                 "reason":"not_visible_at_query" if lens=="then_known" else "not_visible_at_cutoff"}
            entry=by_id.get(identity)
            # The same public shape covers absent and future records. No count,
            # ID, revision/status or source payload from a later object leaks.
            if entry is None or _clock(entry["published_at"])>_clock(cutoff):
                rows.append(row)
                continue
            if entry["definition_sha256"]!=definition or any(
                    entry["context_ref"][key]!=comparison["candidate"][key]
                    for key in ("context_id","capture_id","packet_sha256")):
                raise EpisodeOutcomeError("exact_selected_outcome_reference_mismatch")
            if entry["context_ref"]["subject_id"]!=original["query_owner"]["subject_id"]:
                raise EpisodeOutcomeError("exact_selected_outcome_subject_mismatch")
            observed=observations._read_observation(pin,entry,cutoff=cutoff,policy=policy)
            if observed is not None:
                row.update(status=observed["core"]["status"],value_q18=observed["core"]["value_q18"],
                    reason=observed["core"]["reason"],observation_id=observed["observation_id"],
                    observation_sha256=entry["sha256"],clocks=observed["clocks"],
                    revision_number=observed["revision_number"],
                    previous_observation_id=observed["previous_observation_id"])
            rows.append(row)
        value={"schema":"market_memory.episode_outcome_attachment.v1",
            "retrieval_id":original["retrieval_id"],"selection_sha256":original["selection_sha256"],
            "query_cutoff":query_cutoff,"outcome_cutoff":cutoff,"lens":lens,
            "definition_sha256":definition,
            # A later-built generation can organize older observations. Its
            # identity/entry count must not become a then-known side channel.
            "observation_generation_ref":None if lens=="then_known" else json.loads(pin._reference),
            "observation_generation_provenance":"withheld_in_then_known" if lens=="then_known"
                else "explicit_current_read_pin_not_historical_query_proof",
            "rows":rows,"denominator":original["denominator"],"operational_admission":False,
            "effective_n":"not_estimated","economic_return":False,
            "corporate_action_adjusted":False,"RTH_close_authenticated":False}
        if len(cohort.canonical(value))>_MAX_BYTES:
            raise EpisodeOutcomeError("outcome_attachment_byte_limit")
        retrieval.disclose_episode_retrieval(selection,policy=policy)
        observations._disclose_pin(pin,policy)
        return value


def attach_contextual_outcomes(selection,observation_pin,*,observation_ids:tuple,
        definition_sha256:str,lens:str,outcome_cutoff:str,policy:object):
    """Attach exact published observations; never retrieve, rerank or write.

    The observation-generation capability can be obtained only through its
    current original-owner metadata read. IDs select exact revisions; there
    is no current-head, nearest, newest-correction or alternate-source fallback.
    """
    value=_attachment_value(selection,observation_pin,observation_ids,definition_sha256,
        lens,outcome_cutoff,policy)
    return EpisodeOutcomeAttachmentCapability(cohort.canonical(value),selection,observation_pin,
        observation_ids,definition_sha256,lens,outcome_cutoff,policy.policy_id,_key=_TOKEN)


def disclose_contextual_outcomes(capability,*,policy:object):
    if (type(capability)is not EpisodeOutcomeAttachmentCapability
            or type(capability._body)is not bytes or len(capability._body)>_MAX_BYTES
            or capability._policy_id!=getattr(policy,"policy_id",None)
            or type(capability._seal)is not bytes
            or not hmac.compare_digest(capability._seal,_seal(capability._body,capability._policy_id))):
        raise EpisodeOutcomeError("owner_verified_outcome_attachment_required")
    value=_attachment_value(capability._selection,capability._observation_pin,capability._ids,
        capability._definition,capability._lens,capability._cutoff,policy)
    if cohort.canonical(value)!=capability._body:
        raise EpisodeOutcomeError("original_outcome_attachment_changed")
    return value

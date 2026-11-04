"""Existing site entitlement plus the Chairman's bounded house-output grant.

This adapter owns no users, tokens, rights database or capture lifecycle. The
server supplies the authenticated user identity; current entitlement and the
installed source-purpose record are checked on every use and final disclosure.
"""
from __future__ import annotations

import json
import re
from hashlib import sha256
from pathlib import Path

from engine.neuralweb import market_memory_episode_features as features
from engine.neuralweb import market_memory_retained_context_cohort as cohort
from engine.neuralweb import market_memory_trusted as trusted

REGISTRATION = "config/market_memory_retained_use.v1.json"
AUTHORITY_RECORD = "research/licenses/MARKET_MEMORY_HOUSE_MACRO_REUSE_2026-10-13.md"
PROFILE = "retained_original_house_macro_output.v1"
FIELDS = ("growth_score", "inflation_score", "quad", "liquidity_overlay", "cycle_tag")
_ACTIONS = frozenset({
    "read_retained_generation_metadata", "read_retained_macro_cohort",
    "disclose_retained_macro_cohort", "read_retained_macro_capture_metadata",
    "read_retained_macro_capture", "disclose_retained_macro_capture",
    "read_retained_macro_feature", "disclose_retained_macro_feature",
    "compare_retained_macro_feature", "verify_retained_macro_retention",
    "use_retained_house_output_cohort_for_contextual_comparison",
    "read_real_synthesis_generation_metadata", "read_real_synthesis_capture_metadata",
    "read_real_synthesis_source", "disclose_real_synthesis_source",
    "use_retained_house_output_for_evidence_synthesis",
})
_RICH_ACTIONS = frozenset({
    "read_retained_macro_capture", "disclose_retained_macro_capture",
    "disclose_retained_macro_feature", "compare_retained_macro_feature",
    "read_real_synthesis_source", "disclose_real_synthesis_source",
    "use_retained_house_output_for_evidence_synthesis",
})


class RetainedUseError(PermissionError):
    """Current entitlement, exact resource or named house use is not admitted."""


def _bounded_file(path: Path) -> bytes:
    with path.open("rb") as stream:
        body = stream.read(64 * 1024 + 1)
    if len(body) > 64 * 1024:
        raise RetainedUseError("source_use_record_exceeds_bound")
    return body


def _enforce_current_site_user(user_id: str) -> None:
    from app.paywall import enforce_site_full

    value = enforce_site_full({"id": user_id}, always=True)
    if value.get("id") != user_id:
        raise RetainedUseError("current_site_entitlement_required")


def load_registration(root: Path) -> tuple[dict, str]:
    """Read installed administrative admission; no caller flags grant use."""
    try:
        body = _bounded_file(root / REGISTRATION)
        value = json.loads(body)
        authority = value["source_authority"]
        if (value["schema"] != "market_memory.retained_house_use.v1"
                or value["enabled"] is not True
                or value["policy_id"] != "market_memory.retained_house_contextual_use.v1"
                or value["profile"] != PROFILE
                or value["store_profile"] != trusted.TRUSTED_STORE_PROFILE
                or value["source_id"] != "market_regime_store"
                or type(value["store_id"]) is not str
                or not re.fullmatch(r"mmstore_[a-f0-9]{64}", value["store_id"])
                or value["fields"] != list(FIELDS)
                or value["purposes"] != ["retention", "reuse", "customer_comparisons", "cited_evidence"]
                or value["modes"] != ["historical_hypothetical", "current_contextual_support"]
                or authority["record"] != AUTHORITY_RECORD
                or authority["basis"] != "direct_chairman_confirmation"
                or sha256(_bounded_file(root / AUTHORITY_RECORD)).hexdigest() != authority["sha256"]
                or any(value[key] is not False for key in
                       ("fit_eligible", "training_eligible", "promotion_eligible"))):
            raise RetainedUseError("exact_house_source_use_record_required")
        method = value["method"]
        if (method["registration_id"] != "retained_house_fixed_l1_contextual_5d_20261013.v1"
                or method["descriptor_id"] != features.fixed_comparison_descriptor()["descriptor_id"]
                or type(method["purge_calendar_days"]) is not int or method["purge_calendar_days"] != 5
                or type(method["embargo_calendar_days"]) is not int or method["embargo_calendar_days"] != 5
                or method["label_interval_coverage"] != "not_established"
                or method["effective_n"] != "not_estimated"):
            raise RetainedUseError("registered_contextual_method_required")
        for key, prefix in (("allowed_subject_ids", "mmsecurity_"),
                            ("revoked_capture_ids", "mmcapture_"),
                            ("revoked_source_receipt_ids", "mmsrc_")):
            rows = value[key]
            if (type(rows) is not list or len(rows) > 1024
                    or any(type(x) is not str or not re.fullmatch(prefix + r"[a-f0-9]{64}", x) for x in rows)
                    or len(set(rows)) != len(rows)):
                raise RetainedUseError("bounded_source_scope_required")
        if not value["allowed_subject_ids"]:
            raise RetainedUseError("admitted_subject_required")
        return value, sha256(body).hexdigest()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise RetainedUseError("source_use_registration_unavailable") from exc


class RetainedHouseUsePolicy:
    """Request-local exact generation binding, using current existing owners."""

    def __init__(self, root: Path, *, user_id: str, store_id: str,
                 generation_id: str, generation_sha256: str, subject_id: str,
                 query_cutoff: str, mode: str):
        if type(user_id) is not str or not 1 <= len(user_id) <= 256:
            raise RetainedUseError("server_authenticated_user_required")
        self.root, self.user_id = Path(root), user_id
        self._bind_source_scope(store_id=store_id, generation_id=generation_id,
            generation_sha256=generation_sha256, subject_id=subject_id,
            query_cutoff=query_cutoff, mode=mode)

    def _read_retained_context_cohort(self, reader, generation, *, subject_id,
                                     query_cutoff, method):
        """Trusted owner composition; inherited policies retain native issuance.

        The generic composer depends only on this optional owner protocol. Site
        authorization imports and bounded reuse remain in this concrete owner;
        no request value selects a reader or grants reuse rights.
        """
        if type(self) is not RetainedHouseUsePolicy:
            return cohort.read_retained_context_cohort(
                reader, generation, subject_id=subject_id,
                query_cutoff=query_cutoff, policy=self)
        from engine.neuralweb import market_memory_retained_cohort_reuse as reuse
        return reuse.read_exact_retained_cohort(
            reader, generation, subject_id=subject_id,
            query_cutoff=query_cutoff, policy=self, method=method)

    def _enforce_current_principal(self):
        _enforce_current_site_user(self.user_id)

    def _bind_source_scope(self, *, store_id, generation_id, generation_sha256,
                           subject_id, query_cutoff, mode):
        self._enforce_current_principal()
        value, digest = load_registration(self.root)
        self.registration, self.registration_sha256 = value, digest
        self.policy_id = value["policy_id"] + ":" + digest
        self.mode = mode
        if (mode not in value["modes"] or subject_id not in value["allowed_subject_ids"]
                or store_id != value["store_id"]):
            raise RetainedUseError("registered_subject_and_mode_required")
        for item, pattern in ((store_id, r"mmstore_[a-f0-9]{64}"),
                              (generation_id, r"mmgeneration_[a-f0-9]{64}"),
                              (generation_sha256, r"[a-f0-9]{64}")):
            if type(item) is not str or not re.fullmatch(pattern, item):
                raise RetainedUseError("exact_generation_identity_required")
        cohort.utc_instant(query_cutoff)
        self.expected = {"store_id": store_id, "generation_id": generation_id,
                         "generation_sha256": generation_sha256,
                         "subject_id": subject_id, "query_cutoff": query_cutoff}

    def check(self, action: str, resource: dict) -> None:
        # Rechecking the existing entitlement owner retains its established cache
        # and revocation semantics, rather than minting a second user authority.
        self._enforce_current_principal()
        value, digest = load_registration(self.root)
        if digest != self.registration_sha256:
            raise RetainedUseError("source_use_registration_changed")
        if action not in _ACTIONS or type(resource) is not dict:
            raise RetainedUseError("named_house_use_required")
        for key in ("store_id", "generation_id", "generation_sha256", "query_cutoff"):
            if resource.get(key) != self.expected[key]:
                raise RetainedUseError("request_resource_binding_mismatch")
        subjects = [resource[key] for key in ("subject_id", "requested_subject_id") if key in resource]
        if not subjects or any(x != self.expected["subject_id"] for x in subjects):
            raise RetainedUseError("actual_or_requested_subject_not_admitted")
        if resource.get("capture_id") in value["revoked_capture_ids"]:
            raise RetainedUseError("capture_use_revoked")
        metadata_only = action in {
            "read_retained_generation_metadata", "read_retained_macro_capture_metadata",
            "read_real_synthesis_generation_metadata", "read_real_synthesis_capture_metadata"}
        rich = action in _RICH_ACTIONS or (not metadata_only
                    and "subject_id" in resource and "source_receipt_ids" in resource)
        if rich:
            for key, prefix in (("capture_id", "mmcapture_"), ("context_id", "mmctx_")):
                if type(resource.get(key)) is not str or not re.fullmatch(prefix + r"[a-f0-9]{64}", resource[key]):
                    raise RetainedUseError("authenticated_capture_resource_required")
            if (resource.get("subject_id") != self.expected["subject_id"]
                    or type(resource.get("packet_sha256")) is not str
                    or not re.fullmatch(r"[a-f0-9]{64}", resource["packet_sha256"])):
                raise RetainedUseError("authenticated_capture_resource_required")
        if rich or "source_receipt_ids" in resource:
            sources = resource.get("source_receipt_ids")
            if (type(sources) is not list or not 1 <= len(sources) <= 64
                    or any(type(x) is not str or not re.fullmatch(r"mmsrc_[a-f0-9]{64}", x) for x in sources)
                    or set(sources) & set(value["revoked_source_receipt_ids"])):
                raise RetainedUseError("original_source_use_not_admitted")
        if action in {"read_real_synthesis_source", "disclose_real_synthesis_source",
                       "use_retained_house_output_for_evidence_synthesis"}:
            if (type(resource.get("feature_sha256")) is not str
                    or not re.fullmatch(r"[a-f0-9]{64}", resource["feature_sha256"])):
                raise RetainedUseError("original_feature_identity_required")

    def disclosure(self) -> dict:
        self.check("read_retained_generation_metadata", self.expected)
        return {"status": "ADMITTED_FOR_NAMED_PURPOSES", "profile": PROFILE, "policy_id": self.policy_id,
                "registration_sha256": self.registration_sha256,
                "authority_record": AUTHORITY_RECORD,
                "authority_sha256": self.registration["source_authority"]["sha256"],
                "purposes": list(self.registration["purposes"]),
                "mode": self.mode, "method": dict(self.registration["method"])}

FACTORY_CONSUMER = "research_factory.contextual_evidence.v1"
FACTORY_BINDINGS = "config/market_memory_factory_bindings.v1.json"


def _factory_binding(root: Path, binding_id: str) -> tuple[dict, str]:
    """Resolve one installed current registration before any private owner I/O."""
    try:
        registration, _ = load_registration(root)
        service = registration["service_consumers"][FACTORY_CONSUMER]
        body = _bounded_file(root / FACTORY_BINDINGS)
        if (service["enabled"] is not True or service["binding_registry"] != FACTORY_BINDINGS
                or service["binding_registry_sha256"] != sha256(body).hexdigest()
                or service["purpose"] != "contextual_cited_evidence"):
            raise RetainedUseError("current_factory_service_admission_required")
        registry = json.loads(body)
        if (set(registry) != {"schema", "bindings"}
                or registry["schema"] != "market_memory.factory_contextual_bindings.v1"
                or type(registry["bindings"]) is not list or len(registry["bindings"]) > 1):
            raise RetainedUseError("bounded_factory_binding_registry_required")
        matches = [v for v in registry["bindings"] if type(v) is dict and v.get("binding_id") == binding_id]
        if len(matches) != 1:
            raise RetainedUseError("exact_current_factory_binding_required")
        value = matches[0]
        fields = {"schema", "binding_id", "origin", "registered_at", "trial_registration_id",
                  "trial_registration_sha256", "trial_record", "store_id", "query_id", "context_id",
                  "capture_id", "subject_id", "generation_id", "generation_sha256", "query_cutoff",
                  "method_spec_id", "mode", "limit", "consumer"}
        core = {k: v for k, v in value.items() if k != "binding_id"}
        if (set(value) != fields or value["schema"] != "market_memory.factory_contextual_binding.v1"
                or value["consumer"] != FACTORY_CONSUMER
                or value["origin"] != "current_owner_registered_contextual_attachment"
                or value["binding_id"] != "mmrfbinding_" + sha256(cohort.canonical(core)).hexdigest()
                or value["store_id"] != registration["store_id"]
                or value["subject_id"] not in registration["allowed_subject_ids"]
                or value["mode"] not in registration["modes"]
                or type(value["limit"]) is not int or not 1 <= value["limit"] <= 8):
            raise RetainedUseError("exact_factory_contextual_binding_required")
        for key, prefix in (("query_id", "mmquery_"), ("context_id", "mmctx_"),
                            ("capture_id", "mmcapture_"), ("generation_id", "mmgeneration_"),
                            ("trial_registration_id", "mmtrial_"), ("method_spec_id", "mmretainedmethod_"),
                            ("generation_sha256", ""), ("trial_registration_sha256", "")):
            if type(value[key]) is not str or not re.fullmatch(prefix + r"[a-f0-9]{64}", value[key]):
                raise RetainedUseError("exact_factory_identity_required")
        if value["trial_record"] != "research/market_memory/trials/" + value["trial_registration_sha256"] + ".json":
            raise RetainedUseError("exact_factory_trial_record_required")
        if cohort.utc_instant(value["registered_at"]) < cohort.utc_instant(value["query_cutoff"]):
            raise RetainedUseError("current_contextual_registration_clock_required")
        from engine.neuralweb import market_memory_episode_retrieval as retrieval
        registered_method = retrieval.RetainedContextMethodSpec(
            registration["method"]["purge_calendar_days"],
            registration["method"]["embargo_calendar_days"], value["mode"])
        if registered_method.disclosure()["method_spec_id"] != value["method_spec_id"]:
            raise RetainedUseError("registered_factory_method_required")
        return value, sha256(body).hexdigest()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise RetainedUseError("current_factory_binding_unavailable") from exc


class RetainedFactoryUsePolicy(RetainedHouseUsePolicy):
    """Trusted internal Factory consumer; never substitutes a website user."""

    def __init__(self, root: Path, *, binding_id: str):
        self.root, self.binding_id = Path(root), binding_id
        binding, self.binding_registry_sha256 = _factory_binding(self.root, binding_id)
        self.binding = binding
        self._bind_source_scope(**{k: binding[k] for k in
            ("store_id", "generation_id", "generation_sha256", "subject_id", "query_cutoff", "mode")})

    def _enforce_current_principal(self):
        binding, digest = _factory_binding(self.root, self.binding_id)
        if (digest != self.binding_registry_sha256 or binding != self.binding):
            raise RetainedUseError("factory_binding_changed")

    def disclose_binding(self) -> dict:
        self.check("read_retained_generation_metadata", self.expected)
        return {**self.binding, "registry_sha256": self.binding_registry_sha256,
                "trial_original_query_provenance": "not_established"}

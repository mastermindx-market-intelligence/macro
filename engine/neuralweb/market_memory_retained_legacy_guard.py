"""Current house-source admission for the three original operational PIT routes.

Use ``with guard_trusted_legacy_reader(composite, root=root, user_id=user) as g``
for the entire request, then ``g.final_authorize()`` before disclosure. Only the
request-local Composite.trusted reader is wrapped. W1A keeps its original owner,
bytes and exact-miss behavior. A trusted denial is PermissionError, never a miss.
The proxy exposes packets and receipts; full feature projection is not public.
"""
from __future__ import annotations

import json
from hashlib import sha256
from datetime import datetime, timezone
from pathlib import Path

from engine.neuralweb import market_memory_pit as pit
from engine.neuralweb import market_memory_trusted as trusted
from engine.neuralweb import market_memory_retained_use as use
from engine.neuralweb import market_memory_retained_context_cohort as cohort


class LegacyTrustedGuard:
    def __init__(self, reader, *, root: Path, user_id: str):
        if not isinstance(reader, (trusted.CompositeAsKnownAtReader, pit.FileAsKnownAtReader)):
            raise use.RetainedUseError("original_operational_reader_required")
        self.reader, self.root, self.user_id = reader, Path(root), user_id
        self._active = False
        self._owner = reader.trusted if isinstance(reader, trusted.CompositeAsKnownAtReader) else None
        if self._owner is not None and type(self._owner) is not trusted.TrustedFileAsKnownAtReader:
            raise use.RetainedUseError("original_trusted_owner_required")
        self._owner_root = self._owner.root if self._owner is not None else None
        self._proxy = _TrustedPacketReader(self) if self._owner is not None else None
        self._resources = {}
        self._policies = {}
        self._registration_sha = None

    def __enter__(self):
        if self._active:
            raise use.RetainedUseError("request_guard_already_active")
        use._enforce_current_site_user(self.user_id)
        self.cutoff = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        self._budget = pit.bounded_owner_reads(maximum_bytes=cohort.MAX_OWNER_BYTES)
        self._budget.__enter__()
        self._active = True
        if self._proxy is not None:
            self.reader.trusted = self._proxy
        return self

    def __exit__(self, *args):
        self._active = False
        if self._owner is not None:
            self.reader.trusted = self._owner
        return self._budget.__exit__(*args)

    def _check(self):
        if not self._active:
            raise use.RetainedUseError("active_request_guard_required")
        use._enforce_current_site_user(self.user_id)
        if self._owner is not None and (self.reader.trusted is not self._proxy
                or self._owner.root != self._owner_root):
            raise use.RetainedUseError("request_owner_identity_changed")

    def _policy(self, pin):
        self._check()
        registration, digest = use.load_registration(self.root)
        if self._registration_sha is not None and digest != self._registration_sha:
            raise use.RetainedUseError("source_use_registration_changed")
        self._registration_sha = digest
        if len(registration["allowed_subject_ids"]) != 1:
            raise use.RetainedUseError("single_registered_legacy_subject_required")
        key = (pin.generation_id, pin.generation_sha256)
        if key not in self._policies:
            self._policies[key] = use.RetainedHouseUsePolicy(self.root,
                user_id=self.user_id, store_id=pin.store_id,
                generation_id=pin.generation_id, generation_sha256=pin.generation_sha256,
                subject_id=registration["allowed_subject_ids"][0],
                query_cutoff=self.cutoff, mode="current_contextual_support")
        return self._policies[key]

    def _receipt(self, pin, query_id):
        self._check()
        pin = self._owner._authenticate_pinned_snapshot(pin)
        entries = [entry for entry in pin.captures if entry.query_id == query_id]
        if len(entries) != 1:
            raise pit.MarketMemoryContextNotFound("exact query absent from trusted generation")
        entry = entries[0]
        policy = self._policy(pin)
        resource = {**policy.expected, "query_id":entry.query_id,
                    "context_id":entry.context_id,"capture_id":entry.capture_id}
        metadata = {k:v for k,v in resource.items() if k != "subject_id"}
        metadata["requested_subject_id"] = policy.expected["subject_id"]
        policy.check("read_retained_macro_capture_metadata", metadata)
        receipt = self._owner.read_pinned_capture_receipt(pin, query_id=query_id)
        resource.update(subject_id=receipt["subject"]["subject_id"],
                        source_receipt_ids=list(receipt["source_receipt_ids"]),
                        packet_sha256=receipt["packet_sha256"])
        self._authorize(policy, resource)
        # Retain independent immutable resource bytes, never a returned dict.
        self._resources[(pin.generation_id, query_id)] = (policy, cohort.canonical(resource))
        return receipt

    @staticmethod
    def _authorize(policy, resource):
        for action in ("read_retained_macro_capture", "verify_retained_macro_retention",
                       "disclose_retained_macro_capture"):
            policy.check(action, resource)

    def final_authorize(self):
        self._check()
        for policy, body in self._resources.values():
            self._authorize(policy, json.loads(body))


class _TrustedPacketReader:
    """Narrow interface consumed by Composite and the operational catalog."""
    def __init__(self, guard):
        self._guard = guard
        self.mode = guard._owner.mode

    def read_pinned_generation(self, *, generation_id=None, maximum_capture_count=None):
        g = self._guard; g._check()
        maximum = cohort.MAX_CAPTURES
        if maximum_capture_count is not None:
            if type(maximum_capture_count) is not int or maximum_capture_count < 0:
                raise pit.MarketMemoryQueryError("bounded capture count required")
            maximum = min(maximum, maximum_capture_count)
        g._owner.observe_generation_head(maximum_capture_count=maximum)
        return g._owner.read_pinned_generation(generation_id=generation_id,
                                               maximum_capture_count=maximum)

    def _authenticate_pinned_snapshot(self, generation):
        g = self._guard; g._check()
        g._owner.observe_generation_head(maximum_capture_count=cohort.MAX_CAPTURES)
        pin = g._owner._authenticate_pinned_snapshot(generation)
        if len(pin.captures) > cohort.MAX_CAPTURES:
            raise pit.MarketMemoryStoreError("trusted generation exceeds request bound")
        return pin

    def read_pinned_capture_receipt(self, generation, *, query_id):
        pin = self._authenticate_pinned_snapshot(generation)
        return self._guard._receipt(pin, query_id)

    def read_stored_from_pinned_generation(self, generation, *, query_id):
        pin = self._authenticate_pinned_snapshot(generation)
        receipt = self._guard._receipt(pin, query_id)
        stored = self._guard._owner.read_stored_from_pinned_generation(pin, query_id=query_id)
        if (stored.packet["context_id"] != receipt["context_id"]
                or sha256(cohort.canonical(stored.packet)).hexdigest() != receipt["packet_sha256"]):
            raise pit.MarketMemoryStoreError("original packet differs from admitted receipt")
        self._guard.final_authorize()
        return stored

    def read_stored_context_id(self, context_id):
        pit._context_path(self._guard._owner.root, context_id)
        pin = self.read_pinned_generation()
        rows = [e for e in pin.captures if e.context_id == context_id]
        if not rows:
            raise pit.MarketMemoryContextNotFound("exact context absent from trusted generation")
        if len(rows) != 1:
            raise pit.MarketMemoryStoreError("trusted context membership ambiguous")
        return self.read_stored_from_pinned_generation(pin, query_id=rows[0].query_id)

    def read_stored_as_known_at(self, *, subject, event_time, as_known_at):
        query, _, _ = pit._normalize_query(subject=subject,event_time=event_time,
            as_known_at=as_known_at,mode=self.mode,reject_future_cutoff=True)
        return self.read_stored_from_pinned_generation(self.read_pinned_generation(),
                                                       query_id=pit._query_id(query))

    def read_as_known_at(self, **query):
        return self.read_stored_as_known_at(**query).packet

    def read_pinned_capture_projections(self, *args, **kwargs):
        raise use.RetainedUseError("legacy_route_exposes_original_packets_only")

    def read_macro_feature_from_pinned_generation(self, *args, **kwargs):
        raise use.RetainedUseError("legacy_route_exposes_original_packets_only")


def guard_trusted_legacy_reader(composite, *, root: Path, user_id: str) -> LegacyTrustedGuard:
    return LegacyTrustedGuard(composite, root=root, user_id=user_id)

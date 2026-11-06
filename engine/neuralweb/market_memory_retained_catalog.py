"""Bounded authenticated discovery of exact original retained macro captures.

Discovery pins one actual trusted generation. It is not an opportunity census or
historical reconstruction. Rich metadata and totals are disclosed only after
current rights have admitted every capture in that exact generation.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import re
import time

from engine.neuralweb import market_memory_pit as pit
from engine.neuralweb import market_memory_trusted as trusted
from engine.neuralweb import market_memory_retained_use as use
from engine.neuralweb import market_memory_retained_context_cohort as cohort
from engine.neuralweb import market_memory_episode_retrieval as retrieval

SCHEMA = "market_memory.retained_context_catalog.v1"
MAX_RESPONSE_BYTES = 128 * 1024


@contextmanager
def _observe_catalog_stage(observer, stage):
    """Optional timing only; neither clocks nor observers may affect a read."""
    started = None
    if observer is not None:
        try:
            started = (time.monotonic(), time.thread_time())
        except Exception:
            pass
    try:
        yield
    finally:
        if started is not None:
            try:
                observer(stage, max(0.0, (time.monotonic() - started[0]) * 1000),
                         max(0.0, (time.thread_time() - started[1]) * 1000))
            except Exception:
                pass


class CatalogDiscoveryAuthority:
    """Only installed source scope and a current real user authorize enumeration."""

    def __init__(self, root: Path, user_id: str, mode: str):
        if type(user_id) is not str or not 1 <= len(user_id) <= 256:
            raise use.RetainedUseError("server_authenticated_user_required")
        self.root, self.user_id, self.mode = Path(root), user_id, mode
        use._enforce_current_site_user(user_id)
        self.registration, self.digest = use.load_registration(self.root)
        if mode not in self.registration["modes"]:
            raise use.RetainedUseError("registered_catalog_mode_required")
        # This delivery is the one already registered SPY reference. A later
        # multi-subject catalog must define explicit independent scope semantics.
        if len(self.registration["allowed_subject_ids"]) != 1:
            raise use.RetainedUseError("single_registered_catalog_subject_required")

    def authorize_metadata(self) -> None:
        use._enforce_current_site_user(self.user_id)
        _value, digest = use.load_registration(self.root)
        if digest != self.digest:
            raise use.RetainedUseError("source_use_registration_changed")


def read_catalog(root: Path, *, user_id: str, mode: str, offset: int, limit: int,
                 generation_id: str | None = None,
                 generation_sha256: str | None = None,
                 query_id: str | None = None, context_id: str | None = None,
                 stage_observer=None) -> dict:
    if (type(offset) is not int or not 0 <= offset <= 255
            or type(limit) is not int or not 1 <= limit <= 20
            or bool(generation_id) != bool(generation_sha256)
            or (offset and not generation_id)):
        raise pit.MarketMemoryQueryError("bounded_exact_catalog_request_required")
    locate = query_id is not None or context_id is not None
    if locate and (not generation_id or offset != 0
            or type(query_id) is not str or not re.fullmatch(r"mmquery_[a-f0-9]{64}", query_id)
            or type(context_id) is not str or not re.fullmatch(r"mmctx_[a-f0-9]{64}", context_id)):
        raise pit.MarketMemoryQueryError("exact_pinned_catalog_locator_required")
    with _observe_catalog_stage(stage_observer, "authorization"):
        authority = CatalogDiscoveryAuthority(root, user_id, mode)
        registered = authority.registration
        subject_id = registered["allowed_subject_ids"][0]
        cutoff = datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    # Includes failed/nested reads; an ancestry cache cannot remove byte billing.
    with pit.bounded_owner_reads(maximum_bytes=cohort.MAX_OWNER_BYTES):
        with _observe_catalog_stage(stage_observer, "authorization"):
            authority.authorize_metadata()
        with _observe_catalog_stage(stage_observer, "generation_pin"):
            reader = trusted.TrustedFileAsKnownAtReader(trusted.default_trusted_store_root(root))
            observed = reader.observe_generation_head(maximum_capture_count=cohort.MAX_CAPTURES)
            if observed.store_id != registered["store_id"]:
                raise pit.MarketMemoryStoreError("registered_catalog_store_required")
            pin = reader.read_pinned_generation(generation_id=generation_id,
                                                maximum_capture_count=cohort.MAX_CAPTURES)
            if (pin.store_id != registered["store_id"]
                    or (generation_sha256 is not None and pin.generation_sha256 != generation_sha256)):
                raise pit.MarketMemoryStoreError("exact_catalog_generation_required")
            if locate and sum(entry.query_id == query_id and entry.context_id == context_id
                              for entry in pin.captures) != 1:
                raise pit.MarketMemoryContextNotFound("exact_catalog_capture_not_found")
        with _observe_catalog_stage(stage_observer, "receipt_authorization"):
            policy = use.RetainedHouseUsePolicy(root, user_id=user_id, store_id=pin.store_id,
                generation_id=pin.generation_id, generation_sha256=pin.generation_sha256,
                subject_id=subject_id, query_cutoff=cutoff, mode=mode)
            resources = []
            declared_bytes = 0
            for entry in pin.captures:
                metadata = {**policy.expected, "capture_id": entry.capture_id,
                            "context_id": entry.context_id, "query_id": entry.query_id,
                            "requested_subject_id": subject_id}
                del metadata["subject_id"]
                policy.check("read_retained_macro_capture_metadata", metadata)
                receipt = reader.read_pinned_capture_receipt(pin, query_id=entry.query_id)
                actual = {**metadata, "subject_id": receipt["subject"]["subject_id"],
                          "source_receipt_ids": list(receipt["source_receipt_ids"]),
                          "packet_sha256": receipt["packet_sha256"]}
                policy.check("read_retained_macro_capture", actual)
                policy.check("verify_retained_macro_retention", actual)
                declared_bytes += (len(cohort.canonical(receipt)) + receipt["packet_bytes"]
                                   + receipt["feature_snapshot"]["content_bytes"])
                if declared_bytes > cohort.MAX_OWNER_BYTES:
                    raise pit.OwnerReadBudgetError("catalog_payload_budget_exceeded")
                resources.append(actual)
        with _observe_catalog_stage(stage_observer, "projections"):
            originals = reader.read_pinned_capture_projections(pin)
            if len(originals) != len(pin.captures):
                raise pit.MarketMemoryStoreError("complete_catalog_generation_required")
        with _observe_catalog_stage(stage_observer, "response_projection"):
            entries = []
            instrument_ids = set()
            for original, resource in zip(originals, resources):
                receipt, packet, feature = original.receipt, original.stored.packet, original.feature
                if (receipt["capture_id"] != resource["capture_id"]
                        or receipt["query_id"] != resource["query_id"]):
                    raise pit.MarketMemoryStoreError("catalog_owner_order_mismatch")
                policy.check("disclose_retained_macro_capture", resource)
                clocks = {"captured_at": receipt["captured_at"],
                          "raw_source_observed_at": receipt["source_evidence"]["raw_source_observed_at"],
                          "raw_source_built_at": receipt["source_evidence"]["raw_source_built_at"],
                          "feature_as_of": feature["as_of"], **packet["clocks"]}
                # A measurement date or original event cutoff does not stand in for
                # later collection/build/feature clocks. Preserve the actual maximum.
                supported = max(clocks.values(), key=cohort.utc_instant)
                instrument_ids.add(receipt["subject"]["instrument_id"])
                entries.append({
                    "query_id": receipt["query_id"], "context_id": receipt["context_id"],
                    "capture_id": receipt["capture_id"], "packet_sha256": receipt["packet_sha256"],
                    "subject_id": receipt["subject"]["subject_id"],
                    "instrument_id": receipt["subject"]["instrument_id"],
                    "event_time": packet["clocks"]["event_time"],
                    "as_known_at": packet["clocks"]["as_known_at"],
                    "captured_at": receipt["captured_at"],
                    "earliest_supported_cutoff": supported,
                    "source_session": feature.get("source_artifact", {}).get("source_asof"),
                    "clocks": clocks,
                    "field_status": {name: "observed" if feature["state"].get(name) is not None
                                     and feature["state"].get(name) != "unknown" else "unavailable"
                                     for name in use.FIELDS},
                    "saved_output": {"path": "/api/market-memory/v1/macro/retained/saved",
                                     "packet_sha256": receipt["packet_sha256"]},
                })
            entries.sort(key=lambda x: (cohort.utc_instant(x["as_known_at"]),
                cohort.utc_instant(x["event_time"]), x["query_id"]), reverse=True)
            if locate:
                # Locate only inside the already pinned, fully authorized population.
                # Return its ordinary page; never choose another capture or cutoff.
                index = next(i for i, row in enumerate(entries)
                             if row["query_id"] == query_id and row["context_id"] == context_id)
                offset = (index // limit) * limit
            methods = [retrieval.RetainedContextMethodSpec(
                registered["method"]["purge_calendar_days"],
                registered["method"]["embargo_calendar_days"], value).disclosure()
                for value in registered["modes"]]
            end = min(offset + limit, len(entries))
            continuation = ({"mode": mode, "offset": end, "limit": limit,
                             "generation_id": pin.generation_id,
                             "generation_sha256": pin.generation_sha256} if end < len(entries) else None)
            value = {"schema": SCHEMA, "mode": mode,
                "subject": {"subject_id": subject_id, "instrument_ids": sorted(instrument_ids),
                            "association": "house_macro_reference_context"},
                "generation": {"store_id": pin.store_id, "profile": pin.profile,
                               "generation_id": pin.generation_id, "generation_sha256": pin.generation_sha256},
                "methods": methods, "entries": entries[offset:end],
                "selection": {"basis": "exact_generation_saved_captures_not_opportunity_census",
                              "total": len(entries), "offset": offset, "limit": limit,
                              "returned": len(entries[offset:end]), "continuation": continuation},
                "server_reference_cutoff": cutoff, "request_clock_origin": "runtime_request_clock",
                "source_use": policy.disclosure(),
                "outcomes": {"status": "NOT_ATTACHED", "selection_independent": True}}
            if len(cohort.canonical(value)) > MAX_RESPONSE_BYTES:
                raise pit.MarketMemoryStoreError("catalog_response_budget_exceeded")
        # Total/continuation depend on all records, so reauthorize all originals,
        # including pages/captures that were not returned.
        with _observe_catalog_stage(stage_observer, "final_authorization"):
            for resource in resources:
                policy.check("disclose_retained_macro_capture", resource)
                policy.check("verify_retained_macro_retention", resource)
            authority.authorize_metadata()
            policy.disclosure()
        return value

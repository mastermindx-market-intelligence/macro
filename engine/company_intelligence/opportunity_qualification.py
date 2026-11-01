"""K5 qualification of existing Earnings revisions for one existing LER episode.

No source I/O, detector, B1 episode conversion, identity allocation or store. The
caller supplies the existing verified Earnings revision chain and observation-
bound Data OS read. A vendor is an explicit source query, never inferred from a
bare ticker. This establishes episode-symbol CONTEXT, not the identity of the
instrument that supplied LER's quotes (the current LER row does not carry it).
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from hashlib import sha256
import json
import math
import re

from engine.company_intelligence.documents import FilingKey, SourceDocument, SourceSpan
from engine.company_intelligence.event_workspace import validate_event_workspace
from engine.entry_radar.live_ledger import LiveEpisode
from engine.entry_radar.replay.identity_observation_snapshot import IdentitySnapshotRead
from engine.prophet_lab.intelligence_vector import _safe_object_id, _validate_owner_workspace_binding
from lib import evidence_foundation as ef
from lib.dataos.identity import IssuerMaster, validate_reference_snapshot

SCHEMA = "earnings.opportunity_qualification.v1"
MAX_REVISIONS = 32
MAX_BYTES = 1024 * 1024


class EarningsQualificationError(ValueError):
    """Bounded refusal token; no owner bodies or arbitrary input in errors."""


def _require(ok: bool, code: str) -> None:
    if not ok:
        raise EarningsQualificationError(code)


def _copy(value):
    try:
        raw = json.dumps(value, allow_nan=False, sort_keys=True, separators=(",", ":"))
        _require(len(raw.encode()) <= MAX_BYTES, "qualification_input_bound")
        return json.loads(raw)
    except EarningsQualificationError:
        raise
    except (TypeError, ValueError, RecursionError):
        raise EarningsQualificationError("qualification_input_invalid") from None


def _instant(value) -> datetime:
    _require(type(value) is str and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})", value) is not None,
             "qualification_clock_unknown")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        raise EarningsQualificationError("qualification_clock_unknown") from None


def _digest(value) -> str:
    return sha256(ef.canonical_json_bytes(value)).hexdigest()


def _identity(episode: LiveEpisode, read: IdentitySnapshotRead, vendor: str) -> dict:
    _require(type(read) is IdentitySnapshotRead and type(vendor) is str and 0 < len(vendor) <= 32,
             "identity_observation_required")
    try:
        snap = read.snapshot
        checked = validate_reference_snapshot(snap.receipt_bytes, dict(snap.artifact_bytes), snap.receipt_bytes,
            alias_records=json.loads(snap.alias_json), master_records=json.loads(snap.master_json))
        _require(checked == snap, "identity_snapshot_mismatch")
        answer = read.alias_table().resolve_binding(vendor, episode.ticker,
            _instant(episode.candidate_at).date(), decision_at=episode.candidate_at,
            snapshot_receipts=(read.receipt,))
        _require(answer.status == "BOUND", "candidate_alias_not_bound_by_cutoff")
        master = IssuerMaster.from_records(json.loads(snap.master_json))
        issuer = master.issuer_of_security(answer.security_id)
        cik = master.cik_of_issuer(issuer) if issuer else None
        _require(issuer is not None and cik is not None, "candidate_issuer_unresolved")
        return {"vendor": vendor, "vendor_symbol": episode.ticker, "security_id": answer.security_id,
                "issuer_id": issuer, "cik": cik, "alias_revision_id": answer.alias_revision_id,
                "alias_known_at_utc_ns": answer.known_at_utc_ns,
                "identity_read_receipt": read.receipt.as_record(),
                "identity_snapshot_sha256": answer.receipt_sha256,
                "identity_scope": "as_known_in_observation_bound_snapshot"}
    except EarningsQualificationError:
        raise
    except Exception:
        raise EarningsQualificationError("identity_observation_invalid") from None


def _source_fact(workspace: dict, cutoff: datetime) -> dict:
    """One exact native reported revenue fact; no SUE/consensus substitution."""
    facts = [f for f in workspace["facts"] if isinstance(f, dict) and f.get("metric") == "revenue"]
    _require(len(facts) == 1, "workspace_revenue_ambiguous_or_absent")
    fact = facts[0]
    value = fact.get("value")
    # The native Earnings revenue units are USD / usd_millions. Keep the
    # source value; no inferred conversion or consensus/surprise calculation.
    _require(type(value) in (int, float) and 0 <= value <= 10**15
             and math.isfinite(value) and type(fact.get("basis")) is str
             and fact["basis"] in {"reported", "gaap"} and type(fact.get("unit")) is str
             and fact["unit"] in {"USD", "usd_millions"}, "workspace_fact_unqualified")
    span = fact.get("source_span")
    _require(isinstance(span, dict) and type(span.get("document_id")) is str, "workspace_fact_source_missing")
    sources = [s for s in workspace["sources"] if isinstance(s, dict) and s.get("document_id") == span["document_id"]]
    _require(len(sources) == 1, "workspace_fact_source_ambiguous")
    source = sources[0]
    # Release facts already carry the owner's byte-replay receipt and public-
    # primary profile. Do not require a new source_document export (the native
    # release row does not publish one), or pretend to replay private bytes here.
    try:
        _require(span.get("schema") == "source_span.v1" and span.get("authority") == "context_only"
                 and span.get("rights_profile") == "rp_public_primary_v1"
                 and span.get("receipt_state") == "byte_replayed"
                 and source.get("receipt_state") == "byte_replayed", "workspace_derived_rights_unqualified")
        native_span = SourceSpan(**{k: v for k, v in span.items() if k not in {"schema", "authority"}})
        receipt = native_span.receipt
        _require(_safe_object_id(native_span.document_id) == native_span.document_id
                 and re.fullmatch(r"span_[a-f0-9]{20}", native_span.span_id) is not None
                 and type(source.get("source_sha256")) is str
                 and re.fullmatch(r"[a-f0-9]{64}", source["source_sha256"]) is not None
                 and type(native_span.document_version) is int and native_span.document_version > 0
                 and receipt["source_sha256"] == source.get("source_sha256")
                 and type(receipt["span_start_byte"]) is int and type(receipt["span_end_byte"]) is int
                 and type(receipt["segment_bytes"]) is int
                 and 0 <= receipt["span_start_byte"] < receipt["span_end_byte"] <= receipt["segment_bytes"]
                 and native_span.locator.get("span_start_byte") == receipt["span_start_byte"]
                 and native_span.locator.get("span_end_byte") == receipt["span_end_byte"]
                 and native_span.locator.get("segment_index") == receipt["segment_index"],
                 "workspace_fact_lineage_invalid")
        if source.get("kind") == "issuer_release":
            filing = FilingKey(**source["filing_key"])
            _require(filing.cik == workspace["issuer"]["company_id"][4:]
                     and source.get("form") in {"8-K", "8-K/A"}, "workspace_release_identity_invalid")
        elif source.get("kind") == "issuer_supplement":
            # Reuse the currently installed owner profile/availability rules.
            # A new profile is admitted there, never guessed by this consumer.
            from engine.company_intelligence.issuer_supplements import validate_supplement_source
            observed, available = validate_supplement_source(source, event_id=workspace["event_id"])
            _require(available <= observed <= cutoff, "workspace_document_after_candidate")
        else:
            raise EarningsQualificationError("workspace_source_kind_unqualified")
    except EarningsQualificationError:
        raise
    except Exception:
        raise EarningsQualificationError("workspace_fact_lineage_invalid") from None
    doc = source.get("source_document")
    if doc is not None:
        _require(isinstance(doc, dict) and doc.get("schema") == "source_document.v1"
                 and doc.get("authority") == "context_only"
                 and doc.get("source_class") in {"issuer_release", "primary_filing"}
                 and doc.get("rights_state") == "public_primary"
                 and doc.get("rights_profile") == native_span.rights_profile
                 and doc.get("event_id") == workspace["event_id"]
                 and doc.get("document_id") == native_span.document_id
                 and doc.get("content_sha256") == source.get("source_sha256")
                 and doc.get("holds_bytes") is True
                 and doc.get("filing_key") == source.get("filing_key"), "workspace_derived_rights_unqualified")
        try:
            data = {k: v for k, v in doc.items() if k not in {"schema", "authority", "filing_key"}}
            data["filing_key"] = FilingKey(**doc["filing_key"]) if doc.get("filing_key") else None
            SourceDocument(**data)
        except Exception:
            raise EarningsQualificationError("workspace_source_document_invalid") from None
        _require(_instant(doc.get("available_at")) <= _instant(doc.get("fetched_at")) <= min(cutoff, _instant(workspace["generated_at"])),
                 "workspace_document_after_candidate")
    _require(fact.get("schema") == "event_fact.v1" and fact.get("event_id") == workspace["event_id"]
             and type(fact.get("period")) is str and 0 < len(fact["period"]) <= 64,
             "workspace_fact_identity_invalid")
    try:
        from engine.company_intelligence.events import FiscalPeriod
        period = workspace["fiscal_period"]
        _require(type(period.get("year")) is int
                 and (period.get("quarter") is None or type(period["quarter"]) is int),
                 "workspace_fact_period_mismatch")
        fiscal = FiscalPeriod(**period)
        expected_event = "evt_cik" + workspace["issuer"]["company_id"][4:] + "_" + fiscal.token + "_"
        _require(workspace["event_id"].startswith(expected_event), "workspace_fact_period_mismatch")
        label = f"{fiscal.year}Q{fiscal.quarter}" if fiscal.quarter else f"{fiscal.year}FY"
        _require(fact["period"] == label or fiscal.calendar_end is not None
                 and fact["period"] == fiscal.calendar_end.isoformat(), "workspace_fact_period_mismatch")
    except EarningsQualificationError:
        raise
    except (TypeError, ValueError, KeyError):
        raise EarningsQualificationError("workspace_fact_period_mismatch") from None
    return {"value": fact["value"], "unit": fact["unit"], "basis": fact["basis"], "period": fact["period"],
            "document_id": native_span.document_id, "source_sha256": source["source_sha256"],
            "rights_profile": native_span.rights_profile, "span_id": native_span.span_id,
            "text_sha256": native_span.text_sha256, "lineage_state": "owner_byte_replay_receipt",
            "locally_replayed": False, "field_path": f"facts[{workspace['facts'].index(fact)}]"}


def qualify_candidate_workspace(*, episode: dict, event_id: str, revisions: list[dict],
                                identity_read: IdentitySnapshotRead, vendor: str) -> dict:
    """Qualify native context; never manufacture an eligible LER case.

    `event_id` is an explicit native owner event key, never guessed from a
    ticker. `revisions` is the existing read_event_source_revisions output. Its receipt
    is owner-verified upstream; this pure function rechecks semantic/hash links,
    not transport authenticity. `vendor` MUST be the caller's actual native
    namespace. Until LER carries the quote/listing identity provenance, the
    output intentionally does not assert a candidate quote-security join.
    """
    _require(type(event_id) is str and re.fullmatch(r"evt_cik[0-9]{10}_[A-Za-z0-9_.:-]{1,110}", event_id) is not None,
             "workspace_event_identity_required")
    raw_episode = _copy(episode)
    try:
        candidate = LiveEpisode.from_dict(raw_episode)
    except Exception:
        raise EarningsQualificationError("candidate_contract_invalid") from None
    _require(candidate.state == "CANDIDATE" and not candidate.terminal and candidate.candidate_at is not None,
             "candidate_required")
    from engine.entry_radar import detectors
    from engine.entry_radar.live_ledger import compute_episode_id
    try:
        spec = detectors.get_spec(candidate.detector_id)
    except Exception:
        raise EarningsQualificationError("candidate_identity_mismatch") from None
    _require(candidate.detector_version == spec.version and candidate.detector_spec_hash == spec.spec_hash
             and candidate.episode_id == compute_episode_id(ticker=candidate.ticker, detector_id=candidate.detector_id,
                 variant=candidate.variant, first_armed_at=candidate.first_armed_at), "candidate_identity_mismatch")
    cutoff = _instant(candidate.candidate_at)
    _require(_instant(candidate.first_armed_at) <= cutoff, "candidate_clock_order_invalid")
    identity = _identity(candidate, identity_read, vendor)
    rows = _copy(revisions)
    _require(type(rows) is list and 0 < len(rows) <= MAX_REVISIONS, "workspace_revision_bound")
    accepted = []
    for revision in rows:
        try:
            _require(type(revision) is dict and type(revision.get("workspace")) is dict, "workspace_revision_invalid")
            workspace = revision["workspace"]
            validate_event_workspace(workspace)
            _validate_owner_workspace_binding(revision, event_id=event_id,
                                               earnings_company_id="cik:" + identity["cik"])
            clocks = [workspace["lifecycle"]["source_available_at"], workspace["lifecycle"]["observed_at"], workspace["generated_at"]]
            parsed = [_instant(v) for v in clocks]
            _require(parsed[0] <= parsed[1] <= parsed[2], "workspace_clock_order_invalid")
        except EarningsQualificationError:
            raise
        except Exception:
            raise EarningsQualificationError("workspace_owner_binding_invalid") from None
        if all(t <= cutoff for t in parsed):
            accepted.append((parsed[0], parsed[1], workspace, revision))
    _require(bool(accepted), "workspace_not_known_at_candidate")
    newest = max((r[0], r[1]) for r in accepted)
    selected = [r for r in accepted if (r[0], r[1]) == newest]
    _require(len(selected) == 1, "workspace_revision_clock_tie")
    _, _, workspace, revision = selected[0]
    fact = _source_fact(workspace, cutoff)
    evidence = _evidence(workspace, revision, candidate.candidate_at)
    binding = {"schema": "earnings.ler_context_binding.v1", "episode_id": candidate.episode_id,
               "episode_canonical_sha256": sha256(candidate.canonical.encode()).hexdigest(),
               "candidate_at": candidate.candidate_at, "ticker": candidate.ticker,
               "identity": identity,
               "workspace_native_identity": {"event_id": event_id, "generation_id": workspace["generation_id"]},
               "workspace_reference_id": next(iter(evidence["references"])),
               "workspace_semantic_sha256": _digest(workspace),
               "scope": "episode_symbol_context", "candidate_quote_security_join": "not_established"}
    binding["sha256"] = _digest(binding)
    return {"schema": SCHEMA, "state": "qualified_context", "candidate_binding": binding,
            "evidence": evidence, "observation": fact,
            "authority": dict(ef.ALL_FALSE_AUTHORITY),
            "permitted_consumer": "opportunity_case.research.v1",
            "purpose_scope": {"class": "context_only", "source_body_embedded": False,
                              "whole_workspace_rights": "unknown", "publication_permission": "not_asserted"},
            "live_projection_eligible": False,
            "remaining_input": "native_candidate_quote_listing_identity_provenance"}


def _evidence(workspace: dict, revision: dict, cutoff: str) -> dict:
    """A new K5-purpose recipe; no security_state recipe or owner payload copy."""
    native = {k: workspace[k] for k in ("generation_id", "event_id")}
    owner = ef.load_vocabulary()["owner_stores"]["earnings.workspace_generation"]
    clocks = [{"class": kind, "field": field, "value_state": "known", "value": value, "grain": "datetime"}
              for kind, field, value in [
                  ("knowable", "lifecycle.source_available_at", workspace["lifecycle"]["source_available_at"]),
                  ("observed", "lifecycle.observed_at", workspace["lifecycle"]["observed_at"]),
                  ("belief_or_build", "generated_at", workspace["generated_at"])]]
    subject = {"key_type": "cik", "key": workspace["event_id"][7:17]}
    authority = dict(ef.ALL_FALSE_AUTHORITY)
    reference = {"schema": ef.SCHEMA, "version": ef.VERSION, "object_class": "derived_view",
        "owner_store": "earnings.workspace_generation", "native_identity": native,
        "native_schema": "event_workspace.v1", "native_digest": {"state": "known", "sha256": revision["workspace_receipt"]["sha256"]},
        "coverage_class": "immutable_generation", "freshness": {"state": "unknown", "clock_field": None, "policy_id": None},
        "rights": {"state": "unknown", "policy_id": None}, "authority_class": "deterministic",
        "subject": subject, "secondary_subjects": [], "clocks": clocks,
        "provenance": {"pointer_only": True, "body_embedded": False, "owner_reader": owner["reader"],
            "owner_reader_kind": owner["reader_kind"], "pointer": ef.render_owner_pointer(owner, native)},
        "relations": [], "missingness": {"state": "present", "reason": None, "zero_substituted": False},
        "correction": {"kind": "none", "predecessor_reference_ids": [], "clock_field": None, "chronology_state": "not_applicable", "append_only": True, "mutates_predecessor": False},
        "replay": {"mode": "live", "cutoffs": {c: {"state": "known", "value": cutoff, "grain": "datetime"}
            for c in ef.load_vocabulary()["clock_classes"]}, "code_revision": None,
            "input_digest": revision["workspace_receipt"]["sha256"], "vintage_state": "owner_native"}, "authority": authority}
    reference["reference_id"] = ef.compute_reference_id(reference)
    reference = ef.validate_reference(reference)
    rid = reference["reference_id"]
    consumer = {"workstream": "WS:ALPHA-INTELLIGENCE-INTEGRATION", "job": "qualified earnings context for an existing candidate",
                "output_contract": "opportunity_case.research.v1"}
    block = {"schema": ef.BLOCK_SCHEMA, "version": ef.VERSION, "block_key": "earnings_workspace_context", "consumer": consumer,
        "supported_claim": {"kind": "claim", "state": "partial", "text": "One qualified native Earnings generation; canonical candidate quote identity remains unestablished."},
        "reference_ids": [rid], "owner_stores": ["earnings.workspace_generation"], "object_classes": ["derived_view"],
        "evidence_class": "deterministic", "clock_summary": {"collapsed": False, "entries": [{"reference_id": rid, **c} for c in clocks]},
        "coverage": {"state": "unknown", "total": 1, "included": 1, "excluded": 0, "missing": 0, "stale": 0,
            "rights_blocked": 0, "fallback": 0, "basis": "one native source; freshness policy unknown", "reconciliation_state": "reconciled"},
        "uncertainty": {"state": "none", "probability": None, "derivation_ref": None, "calibration_ref": None},
        "dependence": {"state": "independent", "independent_evidence_count": 1, "groups": []},
        "conflict_correction": {"state": "none", "reference_ids": []},
        "next_observable": {"state": "unknown", "description": None, "owner_clock_field": None},
        "permitted_consumers": [consumer["output_contract"]], "lineage": {"state": "original", "predecessor_block_ids": [], "invalidated_by_reference_ids": []}, "authority": authority}
    block["evidence_block_id"] = ef.compute_block_id(block)
    block = ef.validate_block(block, references={rid: reference})
    recipe = {"schema": ef.RECIPE_SCHEMA, "version": ef.VERSION, "recipe_name": "earnings_workspace_k5.v1", "consumer": consumer,
        "subject_instance": subject, "subject_key_types": ["cik"], "identity_joins": [],
        "block_specs": [{"order": 1, "block_key": block["block_key"], "requirement": "required",
            "allowed_owner_stores": ["earnings.workspace_generation"], "allowed_object_classes": ["derived_view"],
            "evidence_class": "deterministic", "minimum_references": 1, "maximum_references": 1,
            "on_absent": "refuse", "output_fields": ["company_context"]}],
        "refusal_degradation_rules": [{"code": code, "condition": condition, "effect": effect} for code, condition, effect in [
            ("REQUIRED_BLOCK_ABSENT", "required native workspace absent", "refuse"), ("OPTIONAL_BLOCK_ABSENT", "optional context absent", "degrade"),
            ("IDENTITY_UNRESOLVED", "native CIK unresolved", "refuse"), ("RIGHTS_BLOCKED", "native derived rights unqualified", "refuse"),
            ("CONFLICTED_REQUIRED_BLOCK", "workspace revision conflicted", "abstain")]],
        "dedup_dependence_rules": {"automatic_relation_types": [], "nonautomatic_relation_types": ["exact_duplicate", "same_fact", "same_event", "corroborates", "contradicts", "shares_upstream", "corrects", "supersedes", "projects"], "reference_count_implies_independence": False},
        "output_mappings": [{"output_field": "company_context", "block_key": block["block_key"], "when_unavailable": "refuse"}],
        "integrity": {"denominator_receipt_required": True, "dominant_degradation_required": True, "partial_may_look_complete": False,
            "confidence_requires_receipt": True, "correction_recompilation_required": True, "owner_payload_copy_allowed": False}, "authority": authority}
    recipe["recipe_id"] = ef.compute_recipe_id(recipe)
    recipe = ef.validate_recipe(recipe)
    ef.compile_recipe(recipe, blocks=[block], references={rid: reference})
    return {"recipe": recipe, "blocks": [block], "references": {rid: reference}}

"""Synthetic native-owner tests; no live-source or production acceptance claim."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import importlib
import importlib.util
import json

import pytest

from engine.company_intelligence.documents import SourceDocument, text_span
from engine.company_intelligence.contracts import canonical_json_bytes, canonical_json_sha256, company_filename
from engine.company_intelligence.events import CompanyEvent, FiscalPeriod
from engine.company_intelligence.identity import IssuerIdentity, IssuerRegistry, ListingAlias
from engine.company_intelligence.views import build_bundle as company_bundle
from engine.company_theme_exposure.views import build_bundle as exposure_bundle
from engine.earnings_narrative.contracts import sha256_bytes

UTC = timezone.utc
CUTOFF = datetime(2026, 10, 9, 10, tzinfo=UTC)
STAMP = CUTOFF - timedelta(hours=2)
TEXT = "The issuer reports additional capacity; no revenue outcome is yet known."


def subject():
    name = "engine.company_theme_exposure.factor_evidence"
    assert importlib.util.find_spec(name) is not None, "native F04 evidence reader is missing"
    return importlib.import_module(name)


def inputs(*, text=TEXT, document_id="doc-1", stance="support"):
    mod = subject()
    generated = "2026-10-09T09:00:00Z"
    contexts, company_manifest = company_bundle(
        [{"document_ticker": "AAPL", "fiscal_year": 2026, "fiscal_quarter": 3,
          "call_date": "2026-10-08", "updated_at": generated,
          "summary": "Synthetic context, not evidence.",
          "raw_source_url": "https://issuer.example/synthetic"}],
        tx_index={"schema": "mastermind.tx-index/v1", "documents": []},
        generated_at=generated, as_of="2026-10-09")
    # In-memory fixture of the native writer's file receipts, not a relaxed contract.
    company_manifest["files"] = {company_filename(ticker): {
        "sha256": canonical_json_sha256(context), "bytes": len(canonical_json_bytes(context))}
        for ticker, context in contexts.items()}
    membership = {"version": "synthetic", "baskets": {"basket": {"members": [
        {"ticker": "AAPL", "added": "2026-01-01", "removed": None}]}}}
    crosswalk = {"version": 1, "themes": [{"id": "theme", "foresight_id": "theme",
        "name_en": "Synthetic Theme", "name_zh": "Synthetic", "basket_ids": ["basket"]}],
        "unmapped_baskets": []}
    state = {"schema": "neuralweb.theme_state.v1", "as_of": "2026-10-09",
        "stale_legs": [], "n_themes": 1, "themes": [{"theme_id": "theme"}],
        "authority": {"is_context_only": True}}
    exposures, exposure_manifest = exposure_bundle(contexts,
        company_manifest=company_manifest, membership=membership, crosswalk=crosswalk,
        theme_state=state, as_of=date(2026, 10, 9))
    registry = IssuerRegistry([IssuerIdentity(company_id="320193", display_name="Synthetic",
        fiscal_year_end_month=9, reporting_currency="USD",
        listings=(ListingAlias(ticker="AAPL", mic="XNAS", share_class="common",
            trading_currency="USD", is_primary=True, valid_from=date(2020, 1, 1)),))])
    event = CompanyEvent.create(company_id="320193", fiscal_period=FiscalPeriod(2026, 3),
        security_ids=("xnas:AAPL",), state="complete", source_available_at=STAMP,
        observed_at=STAMP + timedelta(minutes=1), document_ids=(document_id,))
    body = text.encode("utf-8")
    document = SourceDocument(document_id=document_id, event_id=event.event_id,
        document_kind="release", source_class="issuer_release",
        content_sha256=sha256_bytes(body), content_bytes=len(body),
        published_at=STAMP, available_at=STAMP, fetched_at=STAMP + timedelta(minutes=1),
        rights_profile="rp_public_primary_v1", rights_state="public_primary")
    span = text_span(document_id=document_id, document_version=1,
        body_sha256=document.content_sha256, segment_index=0, segment_text=text,
        start_byte=0, end_byte=len(body), text=text, rights_profile=document.rights_profile)
    row = mod.NativeEvidence(event=event, document=document, span=span,
        body=body, stance=stance)
    return dict(cutoff=CUTOFF, company_contexts=contexts, company_manifest=company_manifest,
        exposures=exposures, exposure_manifest=exposure_manifest, registry=registry,
        evidence=[row], source_use=lambda **kwargs: True)


def render(args):
    return subject().compile_factor_evidence("theme", **args)


def refused(args, reason):
    result = render(args)
    assert result["supporting"] == []
    assert reason in {r["reason"] for r in result["refused"]}
    assert TEXT not in json.dumps(result)
    return result


def test_native_reader_exists():
    subject()


def test_native_f04_source_join_and_exact_excerpt():
    result = render(inputs())
    assert result["status"] == "EVIDENCE_AVAILABLE"
    assert result["supporting"][0]["text"] == TEXT
    assert result["supporting"][0]["link_meaning"] == "basket_membership_only"
    assert result["causal_attribution"] == "UNPROVEN"
    assert result["independent_confirmation_count"] is None
    assert result["observed_movement"] is None
    assert all(value is False for value in result["authority"].values())


def test_use_permission_is_not_inferred_from_public_primary_label():
    args = inputs(); args["source_use"] = None
    refused(args, "source_use_unavailable")


def test_use_callback_is_bound_to_native_objects_and_exact_purpose():
    args = inputs(); calls = []
    def source_use(**kw):
        calls.append(kw)
        return True
    args["source_use"] = source_use
    assert render(args)["supporting"]
    assert len(calls) == 1
    assert calls[0] == {"document": args["evidence"][0].document,
        "span": args["evidence"][0].span, "purpose": "internal_research", "cutoff": CUTOFF}


@pytest.mark.parametrize("value", [False, 1, "ALLOWED", None])
def test_permission_requires_literal_true(value):
    args = inputs(); args["source_use"] = lambda **kw: value
    refused(args, "source_use_unavailable")


@pytest.mark.parametrize("field,value,reason", [
    ("published_at", None, "source_clock_missing"),
    ("available_at", CUTOFF + timedelta(seconds=1), "source_from_future"),
    ("fetched_at", None, "source_clock_missing"),
    ("fetched_at", STAMP - timedelta(seconds=1), "source_clock_order"),
    ("published_at", STAMP - timedelta(days=7), "source_stale"),
    ("superseded_by_document_id", "newer-document", "source_not_current"),
    ("document_kind", "release_duplicate", "source_not_current"),
    ("event_id", "different-event", "event_document_join"),
    ("content_sha256", "0" * 64, "body_digest_mismatch"),
    ("content_bytes", 1, "body_length_mismatch"),
])
def test_document_fail_closed(field, value, reason):
    args = inputs(); row = args["evidence"][0]
    args["evidence"] = [replace(row, document=replace(row.document, **{field: value}))]
    refused(args, reason)


@pytest.mark.parametrize("field,value,reason", [
    ("observed_at", CUTOFF + timedelta(seconds=1), "source_from_future"),
    ("source_available_at", None, "source_clock_missing"),
    ("state", "cancelled", "event_not_current"),
    ("document_ids", (), "event_document_join"),
    ("security_ids", ("xnas:MSFT",), "issuer_security_join"),
])
def test_event_fail_closed(field, value, reason):
    args = inputs(); row = args["evidence"][0]
    args["evidence"] = [replace(row, event=replace(row.event, **{field: value}))]
    refused(args, reason)


@pytest.mark.parametrize("field,value,reason", [
    ("document_id", "foreign-doc", "document_span_join"),
    ("document_version", 2, "document_span_join"),
    ("rights_profile", "different-profile", "document_span_join"),
])
def test_span_binding_fail_closed(field, value, reason):
    args = inputs(); row = args["evidence"][0]
    args["evidence"] = [replace(row, span=replace(row.span, **{field: value}))]
    refused(args, reason)


def test_display_excerpt_is_never_rendered_as_evidence():
    args = inputs(); row = args["evidence"][0]
    args["evidence"] = [replace(row, span=replace(row.span, display_excerpt="BUY NOW 99/100"))]
    result = render(args)
    assert result["supporting"][0]["text"] == TEXT
    assert "BUY NOW" not in json.dumps(result)


def test_forged_locator_and_tampered_body_are_refused():
    args = inputs(); row = args["evidence"][0]
    locator = dict(row.span.locator); locator["span_start_byte"] = 1
    args["evidence"] = [replace(row, span=replace(row.span, locator=locator))]
    refused(args, "span_locator_mismatch")
    args["evidence"] = [replace(row, body=row.body + b" changed")]
    refused(args, "body_digest_mismatch")


def test_utf8_replay_preserves_exact_native_bytes():
    text = "Café revenue discussion — capacity remains constrained."
    assert render(inputs(text=text))["supporting"][0]["text"] == text


def test_mutated_f04_or_company_context_cannot_forge_a_join():
    args = inputs(); args["exposures"]["AAPL"]["exposures"][0]["theme_id"] = "forged"
    result = render(args)
    assert result["supporting"] == []
    assert "owner_snapshot_invalid" in result["unknowns"]
    args = inputs(); args["company_contexts"]["AAPL"]["company"]["display_name"] = "altered"
    assert "owner_snapshot_invalid" in render(args)["unknowns"]


def test_missing_or_stale_owner_snapshot_is_not_positive():
    args = inputs(); args["company_contexts"] = {}
    assert "owner_snapshot_invalid" in render(args)["unknowns"]
    args = inputs(); args["cutoff"] = CUTOFF + timedelta(days=3)
    assert "owner_snapshot_stale" in render(args)["unknowns"]


def test_same_event_syndication_does_not_multiply_confirmation():
    args = inputs(); row = args["evidence"][0]
    event = replace(row.event, document_ids=("doc-1", "doc-2"))
    first = replace(row, event=event)
    second_args = inputs(document_id="doc-2")
    second = replace(second_args["evidence"][0], event=event)
    args["evidence"] = [second, first, first]
    result = render(args)
    assert len(result["supporting"]) == 1
    assert result["distinct_event_count"] == 1
    assert result["independent_confirmation_count"] is None
    reverse = dict(args, evidence=list(reversed(args["evidence"])))
    assert result == render(reverse)


def test_contradiction_is_preserved_even_when_source_text_is_identical():
    args = inputs(); row = args["evidence"][0]
    args["evidence"] = [row, replace(row, stance="contradict")]
    result = render(args)
    assert result["status"] == "CONFLICTING_EVIDENCE"
    assert result["supporting"] and result["contradictory"]
    assert result["causal_attribution"] == "UNPROVEN"


def test_same_document_identity_with_different_bytes_is_quarantined():
    args = inputs(); row = args["evidence"][0]
    other = inputs(text="Different content for the same document version.")["evidence"][0]
    args["evidence"] = [row, other]
    result = render(args)
    assert result["status"] == "CONFLICTING_EVIDENCE"
    assert result["supporting"] == []
    assert result["conflicts"][0]["reason"] == "document_version_conflict"


def test_invalid_cutoff_and_unbounded_evidence_are_rejected():
    args = inputs(); args["cutoff"] = datetime(2026, 10, 9)
    with pytest.raises(ValueError): render(args)
    args = inputs(); args["evidence"] *= 1001
    with pytest.raises(ValueError): render(args)


def test_source_use_failure_is_closed_without_exception_text_leakage():
    args = inputs()
    def failing(**kw): raise OSError("private backend detail")
    args["source_use"] = failing
    result = refused(args, "source_use_unavailable")
    assert "private backend" not in json.dumps(result)


def test_company_manifest_receipt_must_match_actual_native_context():
    from engine.company_theme_exposure.views import derive_generation_id
    args = inputs()
    args["company_manifest"]["files"]["companies/AAPL.json"]["sha256"] = "0" * 64
    # Re-seal the downstream F04 view using its real owner. The actual parent
    # receipt still disagrees with the held parent bytes and must be checked.
    manifest = args["exposure_manifest"]
    manifest["source"]["company_intelligence"]["sha256"] = canonical_json_sha256(args["company_manifest"])
    generation = derive_generation_id(args["exposures"], manifest)
    manifest["generation_id"] = generation
    for exposure in args["exposures"].values(): exposure["generation_id"] = generation
    result = render(args)
    assert result["supporting"] == []
    assert "owner_snapshot_invalid" in result["unknowns"]


def test_boolean_locator_is_not_integer_zero():
    args = inputs(); row = args["evidence"][0]
    locator = dict(row.span.locator); locator["segment_index"] = False
    args["evidence"] = [replace(row, span=replace(row.span, locator=locator))]
    refused(args, "span_locator_mismatch")


def test_reobserved_copy_has_permutation_invariant_presentation():
    args = inputs(); row = args["evidence"][0]
    later = replace(row, document=replace(row.document, fetched_at=STAMP + timedelta(minutes=10)))
    args["evidence"] = [later, row]
    assert render(args) == render(dict(args, evidence=[row, later]))


def test_unresolved_correction_selection_cannot_display_old_and_new_as_current():
    args = inputs(); old = args["evidence"][0]
    new = inputs(text="A corrected capacity statement.", document_id="doc-2")["evidence"][0]
    event = replace(old.event, document_ids=("doc-1", "doc-2"))
    new = replace(new, event=event,
        document=replace(new.document, revision=2, supersedes_document_id="doc-1"),
        span=replace(new.span, document_version=2))
    args["evidence"] = [replace(old, event=event), new]
    result = render(args)
    assert result["supporting"] == []
    assert result["status"] == "CONFLICTING_EVIDENCE"
    assert "correction_selection_required" in {row["reason"] for row in result["conflicts"]}


def test_unknown_theme_and_missing_native_identity_never_create_membership():
    args = inputs()
    result = subject().compile_factor_evidence("unmapped-theme", **args)
    assert result["supporting"] == []
    args["registry"] = IssuerRegistry()
    refused(args, "issuer_security_join")


def test_context_only_labels_cannot_become_support_or_predictions():
    args = inputs(stance="context")
    result = render(args)
    assert result["context"] and result["supporting"] == []
    assert result["status"] == "ATTRIBUTION_UNKNOWN"
    assert "prediction" not in result and "score" not in result


def test_reader_does_not_mutate_owner_snapshots():
    args = inputs()
    snapshots = {k: args[k] for k in ("company_contexts", "company_manifest", "exposures", "exposure_manifest")}
    before = canonical_json_bytes(snapshots)
    render(args)
    assert canonical_json_bytes(snapshots) == before

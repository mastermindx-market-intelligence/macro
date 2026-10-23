"""Controlled v2 contract proof, not market, rights or production evidence.

§0/§9: retain accepted v1/waiver, one registry and facts-only authority; this
fixture neither starts a composer/publisher nor proves a natural consumer.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess

import pytest

from engine.sector_intelligence import contracts as owner
from engine.sector_intelligence.contracts import (
    ContractValidationError,
    canonical_json_sha256,
    validate_contract,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data/sector_intelligence/fixtures/sector_dossier_read_model.v2.valid.json"


def document():
    return json.loads(FIXTURE.read_text())


def seal(doc):
    packet = doc["governance"]["packet"]
    packet.pop("packet_hash", None)
    packet["packet_hash"] = canonical_json_sha256(packet)
    doc["governance"]["lobe_run"]["output_artifacts"][0]["content_sha256"] = packet["packet_hash"]
    doc.pop("dossier_hash", None)
    doc["dossier_hash"] = canonical_json_sha256(doc)


def synchronize(doc):
    """Rebind exact provenance after a controlled receipt change, not production."""
    rows = doc["input_receipts"]
    for watermark in doc["governance"]["lobe_run"]["source_watermarks"]:
        watermark["input_receipt"] = copy.deepcopy(next(
            row for row in rows if row["source_id"] == watermark["input_receipt"]["source_id"]
        ))
    doc["governance"]["lobe_run"]["input_hashes"] = sorted({
        row["sha256"] for row in rows if row["sha256"] is not None
    })


def fail(doc, code=None):
    seal(doc)
    with pytest.raises(ContractValidationError) as raised:
        validate_contract("sector_dossier_read_model.v2", doc)
    if code is not None:
        assert any(issue.code == code or f"[{code}]" in issue.message for issue in raised.value.issues), str(raised.value)


def old_document():
    return json.loads(subprocess.check_output(
        ["git", "show", "HEAD:data/sector_intelligence/fixtures/sector_dossier_read_model.v1.valid.json"],
        cwd=ROOT, text=True,
    ))


def test_v1_positive_and_static_refusal_are_preserved():
    old = old_document()
    validate_contract("sector_dossier_read_model.v1", old)
    old["input_receipts"].append(copy.deepcopy(next(
        r for r in document()["input_receipts"] if r["source_id"] == "theme-crosswalk"
    )))
    old.pop("dossier_hash")
    old["dossier_hash"] = canonical_json_sha256(old)
    with pytest.raises(ContractValidationError):
        validate_contract("sector_dossier_read_model.v1", old)


def test_v2_golden_and_each_exact_nested_contract():
    doc = document()
    validate_contract("sector_dossier_read_model.v2", doc)
    for key in ("packet", "lobe_run", "authority_manifest"):
        nested = doc["governance"][key]
        validate_contract(nested["contract_id"], nested)
    assert canonical_json_sha256({k: v for k, v in doc.items() if k != "dossier_hash"}) == doc["dossier_hash"]


def test_static_unknown_clock_and_missing_optional_are_truthful():
    doc = document()
    static = next(r for r in doc["input_receipts"] if r["source_id"] == "theme-crosswalk")
    assert static["as_of"] is None and static["observed_at"] is None
    assert static["null_reasons"] == {
        "as_of": "NOT_APPLICABLE", "observed_at": "OWNER_CLOCK_UNAVAILABLE"
    }
    absent = next(r for r in doc["input_receipts"] if not r["required"])
    assert absent["clock_grain"] == "session"
    assert absent["sha256"] is absent["as_of"] is absent["observed_at"] is None
    validate_contract("sector_dossier_read_model.v2", doc)


def test_packet_v2_missing_financial_denials_rejected_after_rehash():
    packet = copy.deepcopy(document()["governance"]["packet"])
    packet["authority_caps"]["forbidden_actions"] = ["originate_signal"]
    packet.pop("packet_hash")
    packet["packet_hash"] = canonical_json_sha256(packet)
    with pytest.raises(ContractValidationError, match="authority"):
        validate_contract("sector_intelligence_packet.v2", packet)


def test_v2_explicitly_invokes_incumbent_packet_authority_guard(monkeypatch):
    calls = []
    original = owner._packet_authority_issues

    def observe(packet):
        calls.append(packet["contract_id"])
        return original(packet)

    monkeypatch.setattr(owner, "_packet_authority_issues", observe)
    validate_contract("sector_intelligence_packet.v2", document()["governance"]["packet"])
    assert calls == ["sector_intelligence_packet.v2"]


@pytest.mark.parametrize("kind,native,family,node", [
    ("canonical_theme", "ai_semiconductors", None, "theme:ai_semiconductors"),
    ("local_theme", "301096", "ths", "ltheme:ths:301096"),
    ("local_theme", "semiconductors", "finviz", "ltheme:finviz:semiconductors"),
])
def test_typed_theme_contract_without_fake_security(kind, native, family, node):
    doc = document()
    subject = {"kind": kind, "native_id": native, "source_family": family, "node_id": node}
    doc["identity"]["subject"] = subject
    for part in doc["governance"].values():
        part["subject"] = copy.deepcopy(subject)
    for name in ("tradable_binding", "benchmark_binding"):
        doc["identity"][name] = {
            "applicability": "not_applicable", "value": None,
            "reason": "NOT_APPLICABLE", "source_refs": ["config/theme_crosswalk.yml"]
        }
    doc["governance"]["packet"]["entity_refs"] = [node]
    doc["governance"]["packet"]["security_refs"] = []
    token = canonical_json_sha256({
        "subject": subject, "common_as_of": doc["common_as_of"],
        "code_version": doc["governance"]["packet"]["producer"]["code_version"],
        "source_identity": sorted((r["source_id"], r["sha256"]) for r in doc["input_receipts"] if r["sha256"]),
    })[:24]
    previous = doc["dossier_id"]
    doc["dossier_id"] = f"dossier:{kind}:{token}"
    packet = doc["governance"]["packet"]
    run = doc["governance"]["lobe_run"]
    manifest = doc["governance"]["authority_manifest"]
    packet["packet_id"] = f"packet:{kind}:{token}"
    run["run_id"] = f"run:sector-federation:{kind}:{token}"
    manifest["manifest_id"] = f"authority:sector-dossier:{kind}:{token}"
    packet["current_fact_refs"] = [x.replace(previous, doc["dossier_id"]) for x in packet["current_fact_refs"]]
    packet["material_change_event_refs"] = [x.replace(previous, doc["dossier_id"]) for x in packet["material_change_event_refs"]]
    packet["lobe_run_ref"] = run["run_id"]
    packet["authority_manifest_ref"] = run["authority_manifest_ref"] = manifest["manifest_id"]
    manifest["artifact_ref"] = run["output_artifacts"][0]["artifact_ref"] = packet["packet_id"]
    seal(doc)
    validate_contract("sector_dossier_read_model.v2", doc)


@pytest.mark.parametrize("part", ["packet", "lobe_run", "authority_manifest"])
def test_subject_mismatch_rejected_after_real_rehash(part):
    doc = document()
    doc["governance"][part]["subject"]["native_id"] = "xlf"
    doc["governance"][part]["subject"]["node_id"] = "sector:xlf"
    fail(doc)


@pytest.mark.parametrize("part", ["packet", "lobe_run", "authority_manifest"])
def test_mixed_nested_versions_rejected(part):
    doc = document()
    doc["governance"][part]["contract_id"] = doc["governance"][part]["contract_id"].replace(".v2", ".v1")
    doc["governance"][part]["schema_version"] = "1.0.0"
    fail(doc)


@pytest.mark.parametrize("mutation", ["namespace", "native", "family", "whitespace", "unknown_family"])
def test_subject_identity_cannot_be_relabelled(mutation):
    doc = document()
    subject = doc["identity"]["subject"]
    if mutation == "namespace": subject["node_id"] = "theme:xlk"
    if mutation == "native": subject["native_id"] = "xlf"
    if mutation == "family": subject["source_family"] = "ths"
    if mutation == "whitespace": subject["native_id"] = " xlk "
    if mutation == "unknown_family":
        subject.update(kind="local_theme", node_id="ltheme:other:xlk", source_family="other")
    fail(doc)


@pytest.mark.parametrize("mutation", [
    "unknown_source", "foreign_path", "wrong_grain", "missing_required",
    "duplicate", "missing_null_reason", "invented_null_reason",
    "static_market_date", "static_fresh", "missing_market_clock",
    "future_date", "future_time", "naive_time",
])
def test_receipt_policy_adversaries(mutation):
    doc = document()
    market = next(r for r in doc["input_receipts"] if r["source_id"] == "site-subsector-confluence")
    static = next(r for r in doc["input_receipts"] if r["source_id"] == "theme-crosswalk")
    if mutation == "unknown_source": market["source_id"] = "unknown-owner"
    if mutation == "foreign_path": market["path"] = "site/foreign.json"
    if mutation == "wrong_grain": market["clock_grain"] = "static"
    if mutation == "missing_required": doc["input_receipts"].remove(market)
    if mutation == "duplicate": doc["input_receipts"].append(copy.deepcopy(market))
    if mutation == "missing_null_reason": static["null_reasons"].pop("as_of")
    if mutation == "invented_null_reason": market["null_reasons"]["sha256"] = "SOURCE_MISSING"
    if mutation == "static_market_date": static["as_of"] = doc["common_as_of"]
    if mutation == "static_fresh": static["freshness_state"] = "fresh"
    if mutation == "missing_market_clock":
        market["observed_at"] = None
        market["null_reasons"]["observed_at"] = "OWNER_CLOCK_UNAVAILABLE"
    if mutation == "future_date": market["as_of"] = "2026-09-19"
    if mutation == "future_time": market["observed_at"] = "2026-09-18T21:00:00Z"
    if mutation == "naive_time": market["observed_at"] = "2026-09-18T19:55:00"
    codes = {"unknown_source": "receipt.owner", "foreign_path": "receipt.policy", "wrong_grain": "receipt.policy", "missing_required": "receipt.required", "duplicate": "receipt.duplicate", "missing_null_reason": "receipt.null_reasons", "invented_null_reason": "receipt.null_reasons", "static_market_date": "receipt.static", "static_fresh": "receipt.static", "missing_market_clock": "receipt.required_clock", "future_date": "receipt.future", "future_time": "receipt.future", "naive_time": "receipt.clock"}
    fail(doc, codes[mutation])


@pytest.mark.parametrize("mutation", ["substitution", "duplicate", "foreign", "hash_set", "static_current", "missing_current"])
def test_lobe_exact_embedded_receipt_and_hash_set(mutation):
    doc = document()
    run = doc["governance"]["lobe_run"]
    if mutation == "substitution": run["source_watermarks"][0]["input_receipt"]["sha256"] = "f" * 64
    if mutation == "duplicate": run["source_watermarks"].append(copy.deepcopy(run["source_watermarks"][0]))
    if mutation == "foreign": run["source_watermarks"][0]["input_receipt"]["source_id"] = "foreign-owner"
    if mutation == "hash_set": run["input_hashes"] = ["f" * 64]
    if mutation == "static_current":
        next(w for w in run["source_watermarks"] if w["input_receipt"]["source_id"] == "theme-crosswalk")["state"] = "current"
    if mutation == "missing_current":
        next(w for w in run["source_watermarks"] if not w["input_receipt"]["required"])["state"] = "current"
    fail(doc)


@pytest.mark.parametrize("mutation", ["packet_ref", "output_id", "output_hash", "manifest_ref", "generation", "unadmitted_source", "financial_manifest"])
def test_governance_adversaries_after_valid_rehash(mutation):
    doc = document()
    packet = doc["governance"]["packet"]
    run = doc["governance"]["lobe_run"]
    manifest = doc["governance"]["authority_manifest"]
    if mutation == "packet_ref": packet["lobe_run_ref"] = "run:sector-federation:sector:" + "a" * 24
    if mutation == "output_id": run["output_artifacts"][0]["artifact_ref"] = "packet:sector:" + "a" * 24
    if mutation == "output_hash":
        seal(doc)
        run["output_artifacts"][0]["content_sha256"] = "f" * 64
        doc.pop("dossier_hash")
        doc["dossier_hash"] = canonical_json_sha256(doc)
        with pytest.raises(ContractValidationError): validate_contract(doc)
        return
    if mutation == "manifest_ref": manifest["artifact_ref"] = "packet:sector:" + "a" * 24
    if mutation == "generation": doc["dossier_id"] = "dossier:sector:" + "a" * 24
    if mutation == "unadmitted_source": doc["conflicts"][0]["source_refs"] = ["fixture#/opaque"]
    if mutation == "financial_manifest": manifest["allowed_actions"] = ["attend"]
    fail(doc)


def test_wrong_benchmark_null_reason_refuses():
    doc = document()
    doc["identity"]["benchmark_binding"]["reason"] = None
    fail(doc)


def test_nonfinite_values_refuse_without_false_rehash():
    doc = document()
    doc["dimensions"][0]["value"] = float("nan")
    with pytest.raises(ContractValidationError):
        validate_contract(doc)


def test_required_unavailable_is_not_a_successful_dossier():
    doc = document()
    row = next(r for r in doc["input_receipts"] if r["source_id"] == "site-theme-state")
    row.update(state="unavailable", sha256=None, as_of=None, observed_at=None, freshness_state="unknown",
               null_reasons={k: "SOURCE_MISSING" for k in ("sha256", "as_of", "observed_at")})
    fail(doc)


@pytest.mark.parametrize("freshness_state,expected", [("fresh", "degraded"), ("stale", "stale"), ("unknown", "unknown")])
def test_older_required_market_is_disclosed_without_rewriting_owner_state(freshness_state, expected):
    doc = document()
    row = next(r for r in doc["input_receipts"] if r["source_id"] == "site-subsector-confluence")
    row.update(as_of="2026-09-17", observed_at="2026-09-17T19:55:00Z", freshness_state=freshness_state)
    synchronize(doc)
    ids = {"stale_source_ids": [], "unknown_source_ids": [], "degraded_source_ids": ["site-subsector-confluence"]}
    if freshness_state == "stale": ids["stale_source_ids"] = ["site-subsector-confluence"]
    if freshness_state == "unknown": ids["unknown_source_ids"] = ["site-subsector-confluence"]
    doc["freshness"].update(state=expected, oldest_required_source_at=row["observed_at"], **ids)
    packet_freshness = doc["governance"]["packet"]["freshness"]
    packet_freshness.update(state=expected, oldest_required_source_at=row["observed_at"],
                            stale_source_ids=ids["stale_source_ids"], unknown_source_ids=ids["unknown_source_ids"])
    seal(doc)
    validate_contract(doc)
    assert row["freshness_state"] == freshness_state


def test_static_known_clock_does_not_enter_market_age_minimum():
    doc = document()
    row = next(r for r in doc["input_receipts"] if r["source_id"] == "theme-crosswalk")
    row["observed_at"] = "2020-01-01T00:00:00Z"
    row["null_reasons"].pop("observed_at")
    synchronize(doc)
    seal(doc)
    validate_contract(doc)
    assert doc["freshness"]["oldest_required_source_at"] == "2026-09-18T19:55:00Z"


@pytest.mark.parametrize("field", ["generated_at", "knowledge_cutoff"])
def test_generation_and_knowledge_cutoff_binding(field):
    doc = document()
    doc["governance"]["packet"][field] = "2026-09-18T19:59:00Z"
    fail(doc, "governance.clock_binding")


def test_missing_required_cannot_pass_by_lowering_completeness():
    doc = document()
    row = next(r for r in doc["input_receipts"] if r["source_id"] == "site-theme-state")
    row.update(state="unavailable", sha256=None, as_of=None, observed_at=None, freshness_state="unknown",
               null_reasons={k: "SOURCE_MISSING" for k in ("sha256", "as_of", "observed_at")})
    synchronize(doc)
    doc["quality"]["required_completeness"] = doc["governance"]["packet"]["quality"]["completeness"] = 7 / 8
    doc["governance"]["lobe_run"]["completeness"] = 7 / 8
    fail(doc, "receipt.required")


def test_v2_zero_duration_logical_interval_is_valid_but_v1_remains_strict():
    doc = document()
    run = doc["governance"]["lobe_run"]
    assert run["started_at"] == run["finished_at"] == doc["generated_at"]
    validate_contract(run)
    validate_contract(doc)
    old = old_document()
    old_run = old["governance"]["lobe_run"]
    old_run["finished_at"] = old_run["started_at"]
    with pytest.raises(ContractValidationError) as exc:
        validate_contract(old_run)
    assert any(issue.code == "interval.run" for issue in exc.value.issues)


@pytest.mark.parametrize("finished", ["2026-09-18T19:59:00Z", "2026-09-18T20:00:00", "not-a-clock"])
def test_v2_logical_interval_rejects_reversed_naive_and_malformed_clocks(finished):
    doc = document()
    doc["governance"]["lobe_run"]["finished_at"] = finished
    run = doc["governance"]["lobe_run"]
    with pytest.raises(ContractValidationError) as exc:
        validate_contract(run)
    assert any(issue.code in {"interval.run", "schema"} for issue in exc.value.issues)
    fail(doc)


def test_v1_nested_lobe_cannot_borrow_v2_zero_duration_semantics():
    doc = document()
    doc["governance"]["lobe_run"]["contract_id"] = "lobe_run.v1"
    fail(doc, "governance.lobe_run_contract")


def test_present_unusable_optional_retains_known_hash_in_lobe_provenance():
    run = copy.deepcopy(document()["governance"]["lobe_run"])
    row = next(w["input_receipt"] for w in run["source_watermarks"] if not w["input_receipt"]["required"])
    row["sha256"] = "9" * 64
    row["null_reasons"] = {"as_of": "SOURCE_UNAVAILABLE", "observed_at": "OWNER_CLOCK_UNAVAILABLE"}
    run["input_hashes"] = sorted(set(run["input_hashes"] + [row["sha256"]]))
    validate_contract(run)
    assert row["sha256"] in run["input_hashes"]
    run["input_hashes"].remove(row["sha256"])
    with pytest.raises(ContractValidationError, match="provenance.hash_set"):
        validate_contract(run)


def test_available_optional_cannot_turn_unknown_owner_clocks_into_available_facts():
    run = copy.deepcopy(document()["governance"]["lobe_run"])
    watermark = next(w for w in run["source_watermarks"] if not w["input_receipt"]["required"])
    row = watermark["input_receipt"]
    row.update(state="available", sha256="9" * 64, freshness_state="fresh")
    row["null_reasons"] = {"as_of": "SOURCE_UNAVAILABLE", "observed_at": "OWNER_CLOCK_UNAVAILABLE"}
    watermark["state"] = "current"
    run["input_hashes"] = sorted(set(run["input_hashes"] + [row["sha256"]]))
    with pytest.raises(ContractValidationError, match="receipt.available_clock"):
        validate_contract(run)


def test_v2_retains_owner_nulls_and_counts_without_zero_imputation():
    doc = document()
    doc["concentration"]["value"] = None
    doc["concentration"]["state"] = "unavailable"
    child = doc["children"][0]
    child.update(n_priced=None, n_members=None, entry_tier=None, regime_state=None)
    seal(doc)
    validate_contract(doc)
    assert child["n_priced"] is child["n_members"] is None


def test_structural_child_cannot_be_relabelled_as_a_theme():
    doc = document()
    doc["children"][0]["child_id"] = "theme:semiconductors"
    doc["children"][0]["relationship_basis"] = "local_theme"
    fail(doc, "schema")


def rebind_generation(doc):
    """Apply the published generation/hash bindings to a controlled adversary."""
    subject = doc["identity"]["subject"]
    packet, run, manifest = (doc["governance"][key] for key in ("packet", "lobe_run", "authority_manifest"))
    token = canonical_json_sha256({
        "subject": subject, "common_as_of": doc["common_as_of"],
        "code_version": packet["producer"]["code_version"],
        "source_identity": sorted((r["source_id"], r["sha256"]) for r in doc["input_receipts"] if r["sha256"] is not None),
    })[:24]
    previous = doc["dossier_id"]
    kind = subject["kind"]
    doc["dossier_id"] = f"dossier:{kind}:{token}"
    packet["packet_id"] = f"packet:{kind}:{token}"
    run["run_id"] = f"run:sector-federation:{kind}:{token}"
    manifest["manifest_id"] = f"authority:sector-dossier:{kind}:{token}"
    packet["lobe_run_ref"] = run["run_id"]
    packet["authority_manifest_ref"] = run["authority_manifest_ref"] = manifest["manifest_id"]
    manifest["artifact_ref"] = run["output_artifacts"][0]["artifact_ref"] = packet["packet_id"]
    for field in ("current_fact_refs", "material_change_event_refs"):
        packet[field] = [value.replace(previous, doc["dossier_id"]) for value in packet[field]]
    synchronize(doc)
    seal(doc)


def test_standalone_lobe_future_market_dates_refuse_without_hash_or_clock_changes():
    run = copy.deepcopy(document()["governance"]["lobe_run"])
    for watermark in run["source_watermarks"]:
        row = watermark["input_receipt"]
        if row["freshness_role"] == "market_observation":
            row["as_of"] = "2030-01-02"
    with pytest.raises(ContractValidationError) as exc:
        validate_contract(run)
    assert any(issue.code == "receipt.future_date" and issue.path.endswith(".input_receipt.as_of") and "site-baskets" in issue.message for issue in exc.value.issues)


def test_coordinated_future_dates_refuse_after_full_generation_rebinding_and_rehash():
    doc = document()
    for row in doc["input_receipts"]:
        if row["freshness_role"] == "market_observation":
            row["as_of"] = "2030-01-02"
    doc["common_as_of"] = doc["freshness"]["common_as_of"] = "2030-01-02"
    rebind_generation(doc)
    assert canonical_json_sha256({k: v for k, v in doc.items() if k != "dossier_hash"}) == doc["dossier_hash"]
    with pytest.raises(ContractValidationError) as exc:
        validate_contract(doc)
    assert any(issue.code == "receipt.future_date" for issue in exc.value.issues)
    assert any(issue.code == "dossier.future_common_date" and issue.path == "$.common_as_of" for issue in exc.value.issues)


@pytest.mark.parametrize("available", [False, True])
def test_present_optional_future_date_is_still_a_future_fact(available):
    run = copy.deepcopy(document()["governance"]["lobe_run"])
    row = next(w["input_receipt"] for w in run["source_watermarks"] if not w["input_receipt"]["required"])
    row.update(sha256="9" * 64, as_of="2030-01-02", observed_at="2026-09-18T19:55:00Z", null_reasons={})
    if available:
        row.update(state="available", freshness_state="fresh")
        next(w for w in run["source_watermarks"] if w["input_receipt"] is row)["state"] = "current"
    run["input_hashes"] = sorted(set(run["input_hashes"] + [row["sha256"]]))
    with pytest.raises(ContractValidationError) as exc:
        validate_contract(run)
    assert any(issue.code == "receipt.future_date" for issue in exc.value.issues)


@pytest.mark.parametrize("cutoff,observed,accepted", [
    ("2026-09-18T01:00:00+02:00", "2026-09-17T12:00:00Z", False),
    ("2026-09-17T23:00:00-02:00", "2026-09-18T00:30:00Z", True),
])
def test_market_date_bound_uses_cutoff_utc_date_not_literal_offset_date(cutoff, observed, accepted):
    run = copy.deepcopy(document()["governance"]["lobe_run"])
    run["knowledge_cutoff"] = cutoff
    for watermark in run["source_watermarks"]:
        row = watermark["input_receipt"]
        if row["freshness_role"] == "market_observation":
            row["observed_at"] = observed
    if accepted:
        validate_contract(run)
    else:
        with pytest.raises(ContractValidationError) as exc:
            validate_contract(run)
        assert any(issue.code == "receipt.future_date" for issue in exc.value.issues)


def test_common_date_bound_uses_utc_date_independently_of_receipt_common_binding():
    doc = document()
    cutoff = "2026-09-18T01:00:00+02:00"  # September17 in UTC.
    doc["knowledge_cutoff"] = cutoff
    doc["governance"]["packet"]["knowledge_cutoff"] = cutoff
    doc["governance"]["lobe_run"]["knowledge_cutoff"] = cutoff
    for row in doc["input_receipts"]:
        if row["freshness_role"] == "market_observation":
            row["observed_at"] = "2026-09-17T12:00:00Z"
    doc["freshness"]["oldest_required_source_at"] = "2026-09-17T12:00:00Z"
    doc["governance"]["packet"]["freshness"]["oldest_required_source_at"] = "2026-09-17T12:00:00Z"
    rebind_generation(doc)
    with pytest.raises(ContractValidationError) as exc:
        validate_contract(doc)
    assert any(issue.code == "dossier.future_common_date" for issue in exc.value.issues)


def test_coordinated_common_date_may_equal_utc_cutoff_date_despite_earlier_literal_date():
    doc = document()
    cutoff = "2026-09-17T23:00:00-02:00"  # September18 in UTC.
    doc["knowledge_cutoff"] = cutoff
    doc["governance"]["packet"]["knowledge_cutoff"] = cutoff
    doc["governance"]["lobe_run"]["knowledge_cutoff"] = cutoff
    for row in doc["input_receipts"]:
        if row["freshness_role"] == "market_observation":
            row["observed_at"] = "2026-09-18T00:30:00Z"
    doc["freshness"]["oldest_required_source_at"] = "2026-09-18T00:30:00Z"
    doc["governance"]["packet"]["freshness"]["oldest_required_source_at"] = "2026-09-18T00:30:00Z"
    rebind_generation(doc)
    validate_contract(doc)
    assert doc["common_as_of"] == "2026-09-18"

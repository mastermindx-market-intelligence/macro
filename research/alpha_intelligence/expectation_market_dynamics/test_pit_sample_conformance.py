from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "pit_sample_conformance.py"
SPEC = importlib.util.spec_from_file_location("k3e_pit_sample_conformance", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)

classify_transition = mod.classify_transition
replay_as_of = mod.replay_as_of
validate_sample = mod.validate_sample

CUTOFF = datetime(2025, 1, 10, 16, 0, tzinfo=timezone.utc)


def row(
    oid: str = "obs-1",
    *,
    known_at: str = "2025-01-10T15:00:00Z",
    value: float | None = 1.25,
    period_end: str = "2025-03-31",
    contributor: str | None = "analyst-1",
) -> dict:
    known_dt = datetime.fromisoformat(known_at.replace("Z", "+00:00"))
    ingested_at = (known_dt + timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
    return {
        "observation_id": oid,
        "provider_record_id": f"provider-{oid}",
        "provider": "SYNTHETIC_VENDOR",
        "issuer_ref": "issuer:synthetic",
        "security_ref": "SEC:US-XNAS-SYNTH",
        "provider_company_id": "vendor-company-1",
        "metric_native": "EPS",
        "metric_canonical": "EPS_DILUTED",
        "fiscal_period_end": period_end,
        "periodicity": "quarter",
        "fiscal_year": 2025,
        "horizon_label_raw": "Q1",
        "contributor_id": contributor,
        "broker_id": "broker-1" if contributor else None,
        "analyst_id": contributor,
        "value": value,
        "currency": "USD",
        "unit": "per_share",
        "scale": "1",
        "basis": "reported_diluted",
        "normalization_class": "provider_native",
        "source_published_at": None,
        "vendor_received_at": None,
        "vendor_activated_at": None,
        "provider_snapshot_at": "2025-01-10T14:55:00Z",
        "mastermind_observed_at": known_at,
        "known_at": known_at,
        "ingested_at": ingested_at,
        "effective_from": known_at,
        "effective_to": None,
        "correction_generation": 0,
        "supersedes_observation_id": None,
        "withdrawal_state": "active",
        "rights_class": "UNKNOWN",
        "source_receipt": {"receipt_id": f"receipt-{oid}"},
    }


def correction(parent: dict, oid: str, *, known_at: str, value: float) -> dict:
    out = deepcopy(parent)
    out.update(
        {
            "observation_id": oid,
            "provider_record_id": f"provider-{oid}",
            "value": value,
            "mastermind_observed_at": known_at,
            "known_at": known_at,
            "ingested_at": known_at,
            "effective_from": known_at,
            "correction_generation": parent["correction_generation"] + 1,
            "supersedes_observation_id": parent["observation_id"],
            "source_receipt": {"receipt_id": f"receipt-{oid}"},
        }
    )
    return out


def finding_codes(receipt: dict) -> set[str]:
    return {item["code"] for item in receipt["findings"]}


def test_valid_row_is_structurally_pass_but_never_grants_rights_or_production():
    receipt = validate_sample([row()], cutoff=CUTOFF)
    assert receipt["summary"]["structural_pass"] is True
    assert receipt["summary"]["rights_ready"] is False
    assert receipt["summary"]["production_ready"] is False
    assert receipt["authority"] == {
        "class": "research_diagnostic_only",
        "canonical_source_owner_changed": False,
        "rights_granted": False,
        "model_use_granted": False,
        "redistribution_granted": False,
        "financial_influence": False,
    }
    assert receipt["invariants"]["T3_NO_TIMESTAMP_INVENTION"]["status"] == "PARTIAL"
    assert receipt["invariants"]["T6_RIGHTS"]["status"] == "PARTIAL"
    assert receipt["invariants"]["T7_INTRADAY_HONESTY"]["status"] == "UNKNOWN"
    assert receipt["invariants"]["T9_CORPORATE_ACTION_LINEAGE"]["status"] == "UNKNOWN"


def test_future_known_row_is_hidden_from_replay_without_becoming_missing_or_zero():
    future = row("future", known_at="2025-01-10T17:00:00Z", value=2.0)
    receipt = validate_sample([row(), future], cutoff=CUTOFF)
    assert receipt["summary"]["structural_pass"] is True
    assert receipt["replay"]["visible_observation_ids"] == ["obs-1"]
    assert receipt["invariants"]["T1_KNOWLEDGE_CUTOFF"]["hidden_future_rows"] == 1


def test_later_correction_cannot_rewrite_earlier_replay():
    first = row()
    later = correction(first, "obs-2", known_at="2025-01-10T17:00:00Z", value=1.5)
    before = replay_as_of([first, later], CUTOFF)
    after = replay_as_of(
        [first, later],
        datetime(2025, 1, 10, 18, 0, tzinfo=timezone.utc),
    )
    assert [x["observation_id"] for x in before] == ["obs-1"]
    assert [x["observation_id"] for x in after] == ["obs-2"]
    assert before[0]["value"] == 1.25
    assert after[0]["value"] == 1.5


def test_correction_must_increment_generation_exactly():
    first = row()
    bad = correction(first, "obs-2", known_at="2025-01-10T17:00:00Z", value=1.5)
    bad["correction_generation"] = 3
    receipt = validate_sample([first, bad], cutoff=CUTOFF)
    assert "CORRECTION_GENERATION_GAP" in finding_codes(receipt)
    assert receipt["summary"]["structural_pass"] is False


def test_correction_cannot_change_immutable_period_or_basis():
    first = row()
    bad = correction(first, "obs-2", known_at="2025-01-10T17:00:00Z", value=1.5)
    bad["basis"] = "adjusted"
    receipt = validate_sample([first, bad], cutoff=CUTOFF)
    assert "CORRECTION_GRAIN_CHANGED" in finding_codes(receipt)


def test_fiscal_roll_is_not_value_revision():
    previous = row()
    current = deepcopy(previous)
    current["observation_id"] = "obs-2"
    current["fiscal_period_end"] = "2025-06-30"
    current["value"] = 2.0
    assert classify_transition(previous, current) == "FISCAL_ROLL"


def test_contributor_change_without_value_change_is_composition_only():
    previous = row()
    current = deepcopy(previous)
    current["observation_id"] = "obs-2"
    current["contributor_id"] = "analyst-2"
    current["analyst_id"] = "analyst-2"
    current["broker_id"] = "broker-2"
    assert classify_transition(previous, current) == "COMPOSITION_ONLY"


def test_value_change_on_same_period_and_basis_is_value_revision():
    previous = row()
    current = deepcopy(previous)
    current["observation_id"] = "obs-2"
    current["value"] = 1.35
    assert classify_transition(previous, current) == "VALUE_REVISION"


def test_withdrawal_is_not_value_revision():
    previous = row()
    current = deepcopy(previous)
    current["observation_id"] = "obs-2"
    current["withdrawal_state"] = "withdrawn"
    current["value"] = None
    assert classify_transition(previous, current) == "WITHDRAWAL_OR_STALENESS"


def test_absent_required_clock_field_is_not_silently_synthesized():
    bad = row()
    del bad["source_published_at"]
    receipt = validate_sample([bad], cutoff=CUTOFF)
    assert "REQUIRED_FIELD_ABSENT" in finding_codes(receipt)
    assert receipt["summary"]["structural_pass"] is False


def test_explicit_null_source_clock_is_allowed_and_preserved_as_partial_evidence():
    sample = row()
    sample["source_published_at"] = None
    receipt = validate_sample([sample], cutoff=CUTOFF)
    assert "INVALID_CLOCK" not in finding_codes(receipt)
    assert receipt["invariants"]["T3_NO_TIMESTAMP_INVENTION"]["explicit_null_clock_fields"] >= 1


def test_naive_timestamp_refuses():
    bad = row()
    bad["known_at"] = "2025-01-10T15:00:00"
    receipt = validate_sample([bad], cutoff=CUTOFF)
    assert "INVALID_CLOCK" in finding_codes(receipt)


def test_boolean_value_never_becomes_numeric_estimate():
    bad = row(value=True)
    receipt = validate_sample([bad], cutoff=CUTOFF)
    assert "INVALID_VALUE" in finding_codes(receipt)


def test_rights_class_string_never_grants_rights():
    sample = row()
    sample["rights_class"] = "LICENSED_INTERNAL_MODEL_USE"
    receipt = validate_sample([sample], cutoff=CUTOFF)
    assert receipt["summary"]["rights_ready"] is False
    assert receipt["authority"]["model_use_granted"] is False
    assert receipt["invariants"]["T6_RIGHTS"]["status"] == "PARTIAL"


def test_corporate_action_lineage_is_only_pass_when_explicit_in_receipt():
    sample = row()
    sample["source_receipt"] = {
        "receipt_id": "r1",
        "corporate_action_lineage": {
            "basis": "as_reported",
            "split_adjustment": "none",
        },
    }
    receipt = validate_sample([sample], cutoff=CUTOFF)
    assert receipt["invariants"]["T9_CORPORATE_ACTION_LINEAGE"]["status"] == "PASS"


def test_receipt_is_deterministic_for_same_explicit_input():
    rows = [row()]
    a = validate_sample(rows, cutoff=CUTOFF)
    b = validate_sample(deepcopy(rows), cutoff=CUTOFF)
    assert a["receipt_sha256"] == b["receipt_sha256"]
    assert a["replay"]["canonical_sha256"] == b["replay"]["canonical_sha256"]


def test_cli_reads_only_explicit_local_json_and_returns_deterministic_receipt(tmp_path: Path):
    sample_path = tmp_path / "sample.json"
    output_path = tmp_path / "receipt.json"
    sample_path.write_text(json.dumps({"observations": [row()]}), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(MODULE_PATH),
            str(sample_path),
            "--cutoff",
            "2025-01-10T16:00:00Z",
            "--output",
            str(output_path),
        ],
        cwd=HERE.parents[2],
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )
    assert proc.returncode == 0, proc.stderr
    receipt = json.loads(output_path.read_text(encoding="utf-8"))
    assert receipt["schema"] == "commission2.pit_expectation_sample_conformance/v1"
    assert receipt["input"]["row_count"] == 1
    assert receipt["authority"]["financial_influence"] is False

def test_invalid_fiscal_period_end_refuses():
    bad = row()
    bad["fiscal_period_end"] = "FY1-ish"
    receipt = validate_sample([bad], cutoff=CUTOFF)
    assert "INVALID_FISCAL_PERIOD_END" in finding_codes(receipt)


def test_boolean_fiscal_year_refuses():
    bad = row()
    bad["fiscal_year"] = True
    receipt = validate_sample([bad], cutoff=CUTOFF)
    assert "INVALID_FISCAL_YEAR" in finding_codes(receipt)


def test_non_reference_source_receipt_refuses():
    bad = row()
    bad["source_receipt"] = 123
    receipt = validate_sample([bad], cutoff=CUTOFF)
    assert "INVALID_SOURCE_RECEIPT" in finding_codes(receipt)


def test_source_clock_after_known_at_refuses():
    bad = row()
    bad["source_published_at"] = "2025-01-10T15:30:00Z"
    receipt = validate_sample([bad], cutoff=CUTOFF)
    assert "SOURCE_CLOCK_AFTER_KNOWN" in finding_codes(receipt)
    assert receipt["invariants"]["T1_KNOWLEDGE_CUTOFF"]["status"] == "FAIL"


def test_correction_cannot_change_contributor_identity():
    first = row()
    bad = correction(first, "obs-2", known_at="2025-01-10T17:00:00Z", value=1.5)
    bad["contributor_id"] = "analyst-2"
    bad["analyst_id"] = "analyst-2"
    receipt = validate_sample([first, bad], cutoff=CUTOFF)
    assert "CORRECTION_GRAIN_CHANGED" in finding_codes(receipt)


def test_correction_fork_refuses():
    first = row()
    a = correction(first, "obs-2", known_at="2025-01-10T17:00:00Z", value=1.5)
    b = correction(first, "obs-3", known_at="2025-01-10T18:00:00Z", value=1.6)
    receipt = validate_sample([first, a, b], cutoff=CUTOFF)
    assert "SUPERSESSION_FORK" in finding_codes(receipt)


def test_correction_cycle_refuses():
    a = row("obs-1")
    b = row("obs-2", known_at="2025-01-10T16:00:00Z")
    a["correction_generation"] = 1
    a["supersedes_observation_id"] = "obs-2"
    b["correction_generation"] = 2
    b["supersedes_observation_id"] = "obs-1"
    receipt = validate_sample([a, b], cutoff=CUTOFF)
    assert "SUPERSESSION_CYCLE" in finding_codes(receipt)

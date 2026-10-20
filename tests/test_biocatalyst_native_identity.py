"""Bio consumption of native DataOS file reads; isolated synthetic identity data."""
from datetime import date
import json
import pytest
from engine.entry_radar.replay import identity_observation_snapshot as adapter
from lib.dataos.identity import IdentityError
from tests import test_dataos_identity as f
from tests.test_entry_radar_identity_observation_snapshot import END, generation, prepared


def bio_snapshot_args(read):
    from tests.test_biocatalyst_what_matters_next import _event, _wmn_inputs
    event = _event()
    declared = _wmn_inputs(event, {}, cutoff="2026-10-07T23:59:59Z")
    completed = f._obs_iso(END)
    for member in declared["input_cut"]["members"]:
        artifact = {"dataos_issuer_master.current": "security_master.parquet",
                    "dataos_vendor_aliases.current": "vendor_aliases.parquet"}.get(member["contract_id"])
        if artifact:
            member.update(sha256=dict(read.receipt.artifact_sha256)[artifact],
                          observed_at=completed, accepted_at=completed)
    return dict(events=[event], input_cut=declared["input_cut"], identity_read=read,
                identity_cut_date=date(2026, 10, 7), coverage=declared["coverage"])


def test_bio_composition_binds_actual_native_reader_without_inventing_issuer(prepared):
    from engine.biocatalyst.company_event_adapter import compose_wmn_snapshot_inputs
    read = adapter.read_identity_snapshot(prepared)
    result = compose_wmn_snapshot_inputs(**bio_snapshot_args(read))
    identity = next(iter(result["identity_projection"].values()))
    assert identity["state"] == "unresolved"  # Fixture proves MU, not this Bio issuer.
    assert identity["issuers"] == []
    assert identity["identity_observed_at"] == "2026-10-07T10:46:50Z"
    assert result["input_cut"]["members"][1]["sha256"] in dict(read.receipt.artifact_sha256).values()


@pytest.mark.parametrize("defect", ["wrong_digest", "old_receipt", "future_read", "backdated_member", "duplicate_security"])
def test_bio_snapshot_composition_rejects_unbound_or_future_native_evidence(prepared, defect):
    from dataclasses import replace
    from engine.biocatalyst.company_event_adapter import compose_wmn_snapshot_inputs
    from engine.company_intelligence.contracts import ContractError
    read = adapter.read_identity_snapshot(prepared)
    args = bio_snapshot_args(read)
    if defect == "wrong_digest":
        args["input_cut"]["members"][1]["sha256"] = "0" * 64
    elif defect == "old_receipt":
        args["identity_read"] = replace(read, receipt=replace(read.receipt, receipt_sha256="0" * 64))
    elif defect == "future_read":
        args["input_cut"]["cutoff"] = f._obs_iso(END - 1_000)
    elif defect == "backdated_member":
        args["input_cut"]["members"][1]["observed_at"] = f._obs_iso(END - 1_000)
    else:
        records = json.loads(read.snapshot.master_json)
        records.append(records[0])
        args["identity_read"] = replace(read, snapshot=replace(read.snapshot, master_json=f._obs_json(records)))
    with pytest.raises((ContractError, IdentityError)):
        compose_wmn_snapshot_inputs(**args)


def test_bio_native_read_submicrosecond_clock_is_never_rounded_backward(prepared):
    from dataclasses import replace
    from engine.biocatalyst.company_event_adapter import compose_wmn_snapshot_inputs
    from engine.company_intelligence.contracts import ContractError
    read = adapter.read_identity_snapshot(prepared)
    read = replace(read, receipt=replace(read.receipt, read_completed_at_utc_ns=str(END + 1)))
    args = bio_snapshot_args(read)
    with pytest.raises(ContractError, match="precedes actual read"):
        compose_wmn_snapshot_inputs(**args)
    for member in args["input_cut"]["members"][1:]:
        member.update(observed_at=f._obs_iso(END + 1_000_000_000), accepted_at=f._obs_iso(END + 1_000_000_000))
    result = compose_wmn_snapshot_inputs(**args)
    assert next(iter(result["identity_projection"].values()))["identity_observed_at"] == "2026-10-07T10:46:51Z"


def test_bio_snapshot_current_issuer_and_missing_store_symbol(prepared):
    from engine.biocatalyst.company_event_adapter import compose_wmn_snapshot_inputs
    original, history, aliases, master = f._obs_base()
    master[0].update(issuer_id="ISS:TEST-BIO", issuer_cik="0001365916", issuer_state="RESOLVED")
    generation(prepared, original=original, history=history, rows=aliases, master=master)
    read = adapter.read_identity_snapshot(prepared)
    result = compose_wmn_snapshot_inputs(**bio_snapshot_args(read))
    identity = next(iter(result["identity_projection"].values()))
    assert identity["state"] == "resolved"
    assert identity["issuers"][0]["issuer_id"] == "ISS:TEST-BIO"
    assert identity["issuers"][0]["securities"][0]["display_symbol"] is None


def test_bio_native_cut_rejects_submicrosecond_truncation(prepared):
    from engine.biocatalyst.company_event_adapter import compose_wmn_snapshot_inputs
    from engine.company_intelligence.contracts import ContractError
    args = bio_snapshot_args(adapter.read_identity_snapshot(prepared))
    args["input_cut"]["cutoff"] = "2026-10-07T23:59:59.000000001Z"
    with pytest.raises(ContractError, match="whole seconds"):
        compose_wmn_snapshot_inputs(**args)

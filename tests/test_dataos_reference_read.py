"""I02 acceptance suite — reference-snapshot GENERATION reading (Data OS §D2).

Lane I02-TEST-1.  The reader under test is the adopted reference-snapshot reader
in ``lib/dataos/identity.py`` (``VendorAliasTable.from_records`` with
``observation_history``, ``resolve_binding`` / ``symbol_binding_for``,
``AliasResolution``, ``ReferenceReadReceipt``, ``ReferenceSnapshot``,
``validate_reference_snapshot``).  These tests index masterplan rows
I02.01-I02.04 plus the CONSUMER half of I02.05; they add discriminating pins on
top of ``tests/test_dataos_identity.py`` without duplicating it.

Pure unit tests: stdlib + pytest only (the CI dataos lane installs only pytest
and pyyaml), no ``data/`` read anywhere.  Expected results are hand-stated
(security ids, statuses, refusal fragments); the ``_obs_*`` fixture builders are
imported, never re-derived, and no product call computes an expectation.

ACCEPTANCE MAP (row -> pre-existing coverage census -> new tests here):

I02.01  one complete generation, same view both lookup directions
  pre-existing: test_observation_original_v1_is_unchanged_and_not_consumer_custody
                test_observation_read_clock_is_separate_and_ns_boundary_is_exact
                test_observation_complete_three_name_chain_uses_same_security_and_preserves_earlier_view
                test_observation_both_directions_reject_selected_cross_family_collisions
  new:          test_i02_01_both_directions_resolve_one_generation_with_one_receipt
                test_i02_01_table_built_from_snapshot_a_refuses_a_foreign_receipt

I02.02  receipt-only refusals cannot disappear while Parquet bytes are unchanged
  pre-existing: test_observation_latest_refusal_survives_removed_master_without_poisoning_old_bound
                test_observation_bound_refused_bound_preserves_all_attempts_and_does_not_fallback
                test_observation_same_prefix_equivalent_generation_uses_earliest_actual_receipt
  new:          test_i02_02_receipt_only_refusal_on_byte_identical_artifacts_does_not_fallback

I02.03  old snapshots cannot borrow newer master/issuer bytes
  pre-existing: test_observation_old_receipt_does_not_authorize_new_master_bytes (semantic, at read)
                test_observation_snapshot_requires_exact_bytes_records_and_consumer_seals (byte level)
  new:          test_i02_03_old_receipt_refuses_newer_master_bytes
                test_i02_03_old_receipt_refuses_newer_alias_bytes
                test_i02_03_refusal_message_names_the_swapped_artifact  (passes: refusals
                                                                        now name the artifact)

I02.04  receipt A/B equality is not "globally latest" and not ABA-proof
  pre-existing: test_observation_same_prefix_equivalent_generation_uses_earliest_actual_receipt
                test_observation_snapshot_requires_exact_bytes_records_and_consumer_seals
                test_observation_public_context_values_cannot_hide_duplicate_vectors
  new:          test_i02_04_no_latest_or_current_claim_on_read_values
                test_i02_04_generation_a_revalidates_after_b_as_generation_a_not_latest
                test_i02_04_receipt_before_and_after_disagreeing_is_refused

I02.05  CONSUMER half only: interrupted publication is refused at read time
  pre-existing: test_observation_snapshot_requires_exact_bytes_records_and_consumer_seals
  new:          test_i02_05_zero_byte_artifact_refused_under_predecessor_receipt
                test_i02_05_truncated_artifacts_refused_under_predecessor_receipt
                test_i02_05_receipt_change_mid_read_simulating_interrupted_publication_is_refused
  GAP:          the PUBLISHER half of I02.05 (preimage preservation during an
                interrupted write, empty scratch output is not the predecessor)
                is owned by scripts/build_security_master.py / PR #7299 and is
                deliberately NOT tested or claimed here.

Run: python3 -m pytest tests/test_dataos_reference_read.py tests/test_dataos_identity.py -q -p no:cacheprovider
"""

from __future__ import annotations

import hashlib
import json
from datetime import date

import pytest

from lib.dataos.identity import (
    AliasResolution,
    IdentityError,
    ReferenceReadReceipt,
    ReferenceSnapshot,
    validate_reference_snapshot,
)
from tests.test_dataos_identity import (
    _OBS_T0,
    _obs_append,
    _obs_base,
    _obs_iso,
    _obs_query,
    _obs_snapshot,
    _obs_table,
)

_MU = "SEC:US-XNAS-MU"
_DECISION = _obs_iso(_OBS_T0 + 100_000)  # the _obs_query default cutoff


def _second_generation(original, history, rows, master):
    """Generation B = generation A plus one REFUSED native attempt (no new rows)."""
    history_b, rows_b = _obs_append(original, history, rows, status="REFUSED")
    snap_b, read_b = _obs_snapshot(original, history_b, rows_b, master)
    return history_b, rows_b, snap_b, read_b


# ── I02.01 ────────────────────────────────────────────────────────────────────

def test_i02_01_both_directions_resolve_one_generation_with_one_receipt():
    original, history, rows, master = _obs_base()
    snap, read = _obs_snapshot(original, history, rows, master)
    table = _obs_table(original, history, rows, snap)
    forward = _obs_query(table, read)
    reverse = table.symbol_binding_for("polygon", _MU, date(2026, 10, 7),
                                       decision_at=_DECISION, snapshot_receipts=(read,))
    for result in (forward, reverse):
        assert result.status == "BOUND"
        assert result.vendor_symbol == "MU"
        assert result.security_id == _MU
        # One generation = one receipt: both lookup directions cite the SAME read.
        assert result.receipt_sha256 == read.receipt_sha256
        assert result.attempt_id == history["anchor"]["anchor_id"]
        assert result.alias_revision_id == history["anchor"]["anchor_id"] + "/polygon:MU"
        assert result.known_at_utc_ns == str(_OBS_T0)
    assert forward == reverse


def test_i02_01_table_built_from_snapshot_a_refuses_a_foreign_receipt():
    original, history, rows, master = _obs_base()
    snap_a, read_a = _obs_snapshot(original, history, rows, master)
    _history_b, _rows_b, snap_b, read_b = _second_generation(original, history, rows, master)
    assert read_b.receipt_sha256 != read_a.receipt_sha256
    table = _obs_table(original, history, rows, snap_a)  # enrolled view = snapshot A only
    with pytest.raises(IdentityError, match="no exact snapshot"):
        _obs_query(table, read_b)
    assert _obs_query(table, read_a).status == "BOUND"


# ── I02.02 ────────────────────────────────────────────────────────────────────

def test_i02_02_receipt_only_refusal_on_byte_identical_artifacts_does_not_fallback():
    original, history, rows, master = _obs_base()
    snap_a, read_a = _obs_snapshot(original, history, rows, master)
    history_b, rows_b, snap_b, read_b = _second_generation(original, history, rows, master)
    # The point of the row: generation B differs ONLY by its receipt — the alias
    # rows did not move (a REFUSED attempt adds none) and the artifact bytes and
    # their sha256s are byte-identical across the two generations.
    assert rows_b == rows
    assert dict(snap_a.artifact_bytes) == dict(snap_b.artifact_bytes)
    for name, raw in snap_a.artifact_bytes:
        assert hashlib.sha256(raw).hexdigest() == hashlib.sha256(dict(snap_b.artifact_bytes)[name]).hexdigest()
    table = _obs_table(original, history_b, rows_b, snap_a, snap_b)
    later = _obs_query(table, read_b)
    assert later.status == "REFUSED"
    assert later.reason == "source_unavailable"
    assert later.attempt_id == "attempt-1"
    assert later.receipt_sha256 == read_b.receipt_sha256
    earlier = _obs_query(table, read_a)
    assert earlier.status == "BOUND"
    assert earlier.security_id == _MU
    assert earlier.receipt_sha256 == read_a.receipt_sha256
    both = _obs_query(table, read_a, read_b)
    assert both.status == "REFUSED"  # no fallback to the earlier BOUND


# ── I02.03 ────────────────────────────────────────────────────────────────────

def test_i02_03_old_receipt_refuses_newer_master_bytes():
    original, history, rows, master = _obs_base()
    snap, read = _obs_snapshot(original, history, rows, master)
    artifacts = dict(snap.artifact_bytes)
    # Same length, different content: only the byte seal can catch a newer
    # serialization borrowing an older generation's receipt.
    artifacts["security_master.parquet"] = b"newer" + artifacts["security_master.parquet"][5:]
    with pytest.raises(IdentityError, match="artifact byte seal"):
        validate_reference_snapshot(snap.receipt_bytes, artifacts, snap.receipt_bytes,
                                    alias_records=rows, master_records=master)
    assert _obs_query(_obs_table(original, history, rows, snap), read).status == "BOUND"


def test_i02_03_old_receipt_refuses_newer_alias_bytes():
    original, history, rows, master = _obs_base()
    snap, read = _obs_snapshot(original, history, rows, master)
    artifacts = dict(snap.artifact_bytes)
    artifacts["vendor_aliases.parquet"] = artifacts["vendor_aliases.parquet"] + b"(newer generation)"
    with pytest.raises(IdentityError, match="artifact byte"):
        validate_reference_snapshot(snap.receipt_bytes, artifacts, snap.receipt_bytes,
                                    alias_records=rows, master_records=master)
    assert _obs_query(_obs_table(original, history, rows, snap), read).status == "BOUND"


def test_i02_03_refusal_message_names_the_swapped_artifact():
    original, history, rows, master = _obs_base()
    snap, _read = _obs_snapshot(original, history, rows, master)
    artifacts = dict(snap.artifact_bytes)
    artifacts["security_master.parquet"] = b"newer" + artifacts["security_master.parquet"][5:]
    with pytest.raises(IdentityError, match="security_master"):
        validate_reference_snapshot(snap.receipt_bytes, artifacts, snap.receipt_bytes,
                                    alias_records=rows, master_records=master)


def test_i02_03_refusal_message_names_the_swapped_alias_artifact():
    original, history, rows, master = _obs_base()
    snap, _read = _obs_snapshot(original, history, rows, master)
    artifacts = dict(snap.artifact_bytes)
    # Same length, different content: only the byte seal can catch the swap, so
    # the refusal itself must name WHICH artifact was swapped.
    artifacts["vendor_aliases.parquet"] = b"newer" + artifacts["vendor_aliases.parquet"][5:]
    with pytest.raises(IdentityError, match="vendor_aliases"):
        validate_reference_snapshot(snap.receipt_bytes, artifacts, snap.receipt_bytes,
                                    alias_records=rows, master_records=master)


# ── I02.04 ────────────────────────────────────────────────────────────────────

def test_i02_04_no_latest_or_current_claim_on_read_values():
    # Hand-stated full field surfaces: a successful validation exposes no
    # latest/current claim on any read-side value.
    assert set(ReferenceReadReceipt.__slots__) == {
        "receipt_sha256", "generation_id", "artifact_sha256", "history_prefix_sha256",
        "read_started_at_utc_ns", "read_completed_at_utc_ns"}
    assert set(ReferenceSnapshot.__slots__) == {
        "receipt_bytes", "artifact_bytes", "alias_json", "master_json"}
    assert set(AliasResolution.__slots__) == {
        "status", "vendor", "vendor_symbol", "security_id", "attempt_id",
        "alias_revision_id", "known_at_utc_ns", "receipt_sha256", "reason"}
    for cls in (ReferenceReadReceipt, ReferenceSnapshot, AliasResolution):
        for name in cls.__slots__:
            assert "latest" not in name and "current" not in name


def test_i02_04_generation_a_revalidates_after_b_as_generation_a_not_latest():
    """A -> B -> A: re-presenting generation A's EXACT bytes validates as A.

    This pins ONLY that the read ends on a consistent generation A — the same
    sealed receipt and the same alias/master records at both ends of the read.
    It does NOT prove that nothing changed during the read (the before/after
    receipt equality is what refuses that), and it does NOT prove that A is the
    latest generation (B existed between the two reads and stays the current
    view for B's own receipt).
    """
    original, history, rows, master = _obs_base()
    snap_a, read_a = _obs_snapshot(original, history, rows, master)
    history_b, rows_b, snap_b, read_b = _second_generation(original, history, rows, master)
    assert snap_b.receipt_bytes != snap_a.receipt_bytes
    round_trip = validate_reference_snapshot(
        snap_a.receipt_bytes, dict(snap_a.artifact_bytes), snap_a.receipt_bytes,
        alias_records=rows, master_records=master)
    assert round_trip.receipt_bytes == snap_a.receipt_bytes
    assert json.loads(round_trip.receipt_bytes)["publication"]["generation_id"] == \
        json.loads(snap_a.receipt_bytes)["publication"]["generation_id"]
    canonical = lambda records: sorted(json.dumps(r, sort_keys=True) for r in records)
    assert canonical(json.loads(round_trip.alias_json)) == canonical(rows)
    assert canonical(json.loads(round_trip.master_json)) == canonical(master)
    # B still exists and each receipt still routes to its own generation view.
    table = _obs_table(original, history_b, rows_b, snap_a, snap_b)
    assert _obs_query(table, read_b).status == "REFUSED"
    assert _obs_query(table, read_a).status == "BOUND"
    assert _obs_query(table, read_a).receipt_sha256 == read_a.receipt_sha256


def test_i02_04_receipt_before_and_after_disagreeing_is_refused():
    original, history, rows, master = _obs_base()
    snap_a, _read_a = _obs_snapshot(original, history, rows, master)
    _history_b, _rows_b, snap_b, _read_b = _second_generation(original, history, rows, master)
    # Two individually valid generation receipts at the two ends of one read.
    with pytest.raises(IdentityError, match="receipt changed during read"):
        validate_reference_snapshot(snap_a.receipt_bytes, dict(snap_a.artifact_bytes),
                                    snap_b.receipt_bytes, alias_records=rows, master_records=master)
    # Any drift at all — here one flipped byte in an otherwise identical copy —
    # is refused by the same equality, before the after-receipt is even parsed.
    drifted = snap_a.receipt_bytes[:-1] + bytes([snap_a.receipt_bytes[-1] ^ 0x20])
    with pytest.raises(IdentityError, match="receipt changed during read"):
        validate_reference_snapshot(snap_a.receipt_bytes, dict(snap_a.artifact_bytes), drifted,
                                    alias_records=rows, master_records=master)


# ── I02.05 (consumer half only — publisher half is GAPS, see module docstring) ─

def test_i02_05_zero_byte_artifact_refused_under_predecessor_receipt():
    original, history, rows, master = _obs_base()
    snap, _read = _obs_snapshot(original, history, rows, master)
    for name in ("security_master.parquet", "vendor_aliases.parquet"):
        artifacts = dict(snap.artifact_bytes)
        artifacts[name] = b""  # empty scratch output is not the predecessor
        with pytest.raises(IdentityError, match="artifact byte count"):
            validate_reference_snapshot(snap.receipt_bytes, artifacts, snap.receipt_bytes,
                                        alias_records=rows, master_records=master)


def test_i02_05_truncated_artifacts_refused_under_predecessor_receipt():
    original, history, rows, master = _obs_base()
    snap, _read = _obs_snapshot(original, history, rows, master)
    for name in ("security_master.parquet", "vendor_aliases.parquet"):
        artifacts = dict(snap.artifact_bytes)
        artifacts[name] = artifacts[name][:-8]
        with pytest.raises(IdentityError, match="artifact byte count"):
            validate_reference_snapshot(snap.receipt_bytes, artifacts, snap.receipt_bytes,
                                        alias_records=rows, master_records=master)


def test_i02_05_receipt_change_mid_read_simulating_interrupted_publication_is_refused():
    """Interrupted publication: the consumer captured generation A before the
    write and generation B after it; the pair is refused, never reconciled by
    guessing which half was intended.  Publisher-side preimage preservation is
    NOT claimed here (GAPS: scripts/build_security_master.py / PR #7299)."""
    original, history, rows, master = _obs_base()
    snap_a, _read_a = _obs_snapshot(original, history, rows, master)
    _history_b, _rows_b, snap_b, _read_b = _second_generation(original, history, rows, master)
    with pytest.raises(IdentityError, match="receipt changed during read"):
        validate_reference_snapshot(snap_a.receipt_bytes, dict(snap_b.artifact_bytes),
                                    snap_b.receipt_bytes, alias_records=rows, master_records=master)

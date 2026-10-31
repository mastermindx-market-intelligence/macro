"""Discriminating tests for the V4-A2 issuer-side source qualification preflight.

Each test mutates exactly one evidence leg and proves the typed NOT_SETTLED
refusal fires for that leg and ONLY that leg — and that no accepted bundle
identity is ever produced on incomplete evidence.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from pathlib import Path

import pytest

from engine.neuralweb import theme_state_generation as g
from tests.test_theme_state_production import production_world  # noqa: F401 — pytest fixture
from scripts.prophet_output_inventory import (
    INDEX_REL,
    candidate_store_entries,
    snapshot,
    store_sha256,
)
from scripts.prophet_settlement_preflight import (
    InfrastructureError,
    STATUS_QUALIFIED,
    STATUS_REFUSED,
    write_receipt,
    run_preflight,
    write_receipt,
)

BOARD_REL = "site/factordata/us_standouts.json"
COMPUTED_AT = "2026-10-31T02:15:00Z"
# Accepted-generation clocks reusing the incumbent use-reader fixture family:
# emission precedes activation precedes the declared use observation.
EMISSION = "2026-10-05T12:00:00Z"
ACTIVATION = "2026-10-06T12:00:00Z"
USE = "2026-10-06T13:00:00Z"
# Later correction clocks: knowledge precedes the corrected emission instant.
CORR_KNOWN = "2026-10-05T12:30:00Z"
CORR_EMITTED = "2026-10-05T13:00:00Z"
CORR_ACTIVATION = "2026-10-06T15:00:00Z"


def _board_bytes(as_of: str = "2026-10-30") -> bytes:
    doc = {
        "as_of": as_of,
        "gate_go": True,
        "buy": [],
        "staleness": {
            "price_through": as_of,
            "delayed": False,
            "unknown": False,
            "basis": "panel_majority",
            "inputs": {"panel": {"mixed_vintage": False}},
        },
    }
    return json.dumps(doc, sort_keys=True).encode("utf-8") + b"\n"


def _index_bytes(board_sha: str, snapshot_rel: str, computed_at=COMPUTED_AT) -> bytes:
    doc = {
        "schema": "prophet.index/v1",
        "asof": "2026-10-30",
        "source_board_sha256": board_sha,
        "source_board_snapshot_path": snapshot_rel,
        "source_board_snapshot_encoding": "gzip",
        "computed_at": computed_at,
    }
    return (json.dumps(doc, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _populate_prophet(root: Path, *, plans: int = 3, computed_at=COMPUTED_AT) -> tuple[str, str]:
    """Populate the build-owned artifact set; returns (board_sha, snapshot_rel)."""
    board = _board_bytes()
    (root / "site/factordata").mkdir(parents=True, exist_ok=True)
    (root / BOARD_REL).write_bytes(board)
    board_sha = hashlib.sha256(board).hexdigest()
    snapshot_rel = f"data/prophet/origination_sources/{board_sha}.json.gz"
    snapshot_dir = root / "data/prophet/origination_sources"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    (root / snapshot_rel).write_bytes(gzip.compress(board, compresslevel=9, mtime=0))
    plans_dir = root / "site/prophet/plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    for index in range(plans):
        (plans_dir / f"PLAN-{index}-BULL-20261030.json").write_text(
            json.dumps({"id": f"PLAN-{index}"}) + "\n", encoding="utf-8"
        )
    (root / "site/prophet/states").mkdir(parents=True, exist_ok=True)
    (root / "site/prophet/states/PLAN-0.json").write_text('{"id":"PLAN-0"}\n', encoding="utf-8")
    (root / "site/prophet/index.json").write_bytes(_index_bytes(board_sha, snapshot_rel, computed_at))
    ledger_dir = root / "data/prophet"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    (ledger_dir / "ledger.jsonl").write_text('{"id":"existing"}\n', encoding="utf-8")
    return board_sha, snapshot_rel


def _freeze_evidence(tmp_path: Path, root: Path) -> tuple[Path, Path, Path, Path]:
    """Persist the nightly evidence files exactly as the extended step would."""
    board = (root / BOARD_REL).read_bytes()
    board_sha = hashlib.sha256(board).hexdigest()
    inventory = tmp_path / "inventory.json"
    inventory.write_text(json.dumps(snapshot(root), sort_keys=True), encoding="utf-8")
    source_snapshot = tmp_path / "source.json"
    source_snapshot.write_text(
        json.dumps(
            {
                "schema": "prophet.origination_source_snapshot/v1",
                "source": {
                    "path": BOARD_REL,
                    "sha256": board_sha,
                    "size_bytes": len(board),
                    "snapshot_path": f"data/prophet/origination_sources/{board_sha}.json.gz",
                    "snapshot_encoding": "gzip",
                    "board_asof": "2026-10-30",
                    "price_through": "2026-10-30",
                    "staleness": {"price_through": "2026-10-30"},
                },
                "admitted_count": 0,
                "admitted_candidates": [],
            }
        ),
        encoding="utf-8",
    )
    blob = tmp_path / "board.blob.json"
    blob.write_bytes(board)
    delta = tmp_path / "delta.tsv"
    delta.write_text("", encoding="utf-8")
    return inventory, source_snapshot, blob, delta


def _preflight(root: Path, evidence: tuple[Path, Path, Path, Path], **kw) -> dict:
    inventory, source_snapshot, blob, delta = evidence
    return run_preflight(
        root,
        inventory_path=inventory,
        source_snapshot_path=source_snapshot,
        source_blob_path=blob,
        delta_path=delta,
        **kw,
    )


def _tree(root: Path, prefixes=("site/", "data/")) -> dict[str, bytes]:
    """Every byte under the publication roots — the preflight must not touch them."""
    files = {}
    for prefix in prefixes:
        base = root / prefix
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and not path.is_symlink():
                files[path.relative_to(root).as_posix()] = path.read_bytes()
    return files


# ---------------------------------------------------------------------------
# Full population inventory
# ---------------------------------------------------------------------------


def test_full_population_is_bound_and_a_post_inventory_addition_is_refused(tmp_path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    board_sha, snapshot_rel = _populate_prophet(root)
    evidence = _freeze_evidence(tmp_path, root)

    receipt = _preflight(root, evidence)

    # Every non-GMI leg binds; the ONLY refusal is the unqualified GMI leg,
    # because the incumbent owner still stamps D2E_NOT_QUALIFIED.
    assert receipt["status"] == STATUS_REFUSED
    assert receipt["reason_codes"] == ["GMI_ACCEPTED_REFERENCE_MISSING"]
    persisted = json.loads(evidence[0].read_text(encoding="utf-8"))
    assert receipt["artifact_hashes"]["candidate_store"] == store_sha256(
        candidate_store_entries(persisted)
    )
    assert receipt["artifact_hashes"]["board"] == board_sha
    assert receipt["artifact_hashes"]["index"] == hashlib.sha256(
        (root / "site/prophet/index.json").read_bytes()
    ).hexdigest()
    assert receipt["artifact_hashes"]["theme_state"] is None
    assert receipt["candidate_count"] == 3
    assert receipt["artifact_inventory_file_count"] == len(persisted)
    assert receipt["board_definition"] == "us_prophet_v4"

    # The discriminator a changed-only delta TSV can never catch: a plan file
    # ADDED after the inventory is in no TSV row, yet the full-population
    # binding refuses it.
    (root / "site/prophet/plans/PLAN-LATE-BULL-20261030.json").write_text(
        '{"id":"PLAN-LATE"}\n', encoding="utf-8"
    )
    late = _preflight(root, evidence)
    assert "INVENTORY_POPULATION_CHANGED" in late["reason_codes"]
    assert late["leg_detail"]["inventory"]["detail"]["added"] == [
        "site/prophet/plans/PLAN-LATE-BULL-20261030.json"
    ]
    assert late["bundle_id"] is None and late["accepted"] is False


def test_candidate_store_digest_binds_the_whole_population_not_the_delta(tmp_path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _populate_prophet(root, plans=2)
    evidence = _freeze_evidence(tmp_path, root)
    receipt = _preflight(root, evidence)
    persisted = json.loads(evidence[0].read_text(encoding="utf-8"))
    entries = candidate_store_entries(persisted)
    assert set(entries) == {
        "site/prophet/plans/PLAN-0-BULL-20261030.json",
        "site/prophet/plans/PLAN-1-BULL-20261030.json",
    }
    assert receipt["candidate_count"] == 2
    # The store digest is a hash over path + RAW-BYTE sha256 pairs, so it is
    # reproducible from the incumbent fingerprints without a second registry.
    raw = {path: fingerprint.split(":", 1)[1] for path, fingerprint in entries.items()}
    assert receipt["artifact_hashes"]["candidate_store"] == hashlib.sha256(
        json.dumps(raw, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


# ---------------------------------------------------------------------------
# Frozen board
# ---------------------------------------------------------------------------


def test_frozen_board_swap_after_freeze_is_refused(tmp_path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    board_sha, snapshot_rel = _populate_prophet(root)
    evidence = _freeze_evidence(tmp_path, root)
    # The live board mutates after the freeze — the snapshot/bundle/live
    # triple equality must refuse, exactly like the nightly receipt step.
    (root / BOARD_REL).write_bytes(_board_bytes(as_of="2026-10-31"))

    receipt = _preflight(root, evidence)

    assert "SOURCE_CHANGED_AFTER_FREEZE" in receipt["reason_codes"]
    assert receipt["artifact_hashes"]["board"] is None
    # The index still embeds the ORIGINAL frozen board sha, so its binding to
    # the now-frozen source is intact; only the source leg refuses here.
    assert "INDEX_BOARD_BINDING_MISMATCH" not in receipt["reason_codes"]
    assert receipt["bundle_id"] is None


def test_missing_frozen_blob_is_refused(tmp_path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _populate_prophet(root)
    evidence = _freeze_evidence(tmp_path, root)
    evidence[2].unlink()

    receipt = _preflight(root, evidence)

    assert "SOURCE_CHANGED_AFTER_FREEZE" in receipt["reason_codes"]
    assert "DURABLE_SOURCE_SNAPSHOT_MISSING" in receipt["reason_codes"]
    assert receipt["artifact_hashes"]["board"] is None
    assert receipt["bundle_id"] is None


def test_corrupt_durable_gzip_body_is_a_typed_loss_not_a_crash(tmp_path) -> None:
    """round-2 N1: a gzip header over a corrupt deflate body raises zlib.error, not OSError."""
    root = tmp_path / "repo"
    root.mkdir()
    board_sha, snapshot_rel = _populate_prophet(root)
    evidence = _freeze_evidence(tmp_path, root)
    good = (root / snapshot_rel).read_bytes()
    (root / snapshot_rel).write_bytes(good[:10] + b"\xff\xff\xff\xff" + good[14:])
    with pytest.raises(Exception) as caught:
        gzip.decompress((root / snapshot_rel).read_bytes())
    assert not isinstance(caught.value, (OSError, EOFError)), type(caught.value)

    receipt = _preflight(root, evidence)

    assert receipt["status"] == STATUS_REFUSED
    assert "DURABLE_SOURCE_SNAPSHOT_MISSING" in receipt["reason_codes"]
    assert receipt["artifact_hashes"]["board"] is None


def test_durable_source_snapshot_loss_is_refused(tmp_path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    board_sha, snapshot_rel = _populate_prophet(root)
    evidence = _freeze_evidence(tmp_path, root)
    (root / snapshot_rel).write_bytes(gzip.compress(b'{"tampered":true}\n', compresslevel=9, mtime=0))

    receipt = _preflight(root, evidence)

    assert "DURABLE_SOURCE_SNAPSHOT_MISSING" in receipt["reason_codes"]
    assert receipt["artifact_hashes"]["board"] is None


def test_unqualified_source_clock_is_refused(tmp_path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _populate_prophet(root)
    evidence = _freeze_evidence(tmp_path, root)
    source_doc = json.loads(evidence[1].read_text(encoding="utf-8"))
    source_doc["source"]["price_through"] = None
    evidence[1].write_text(json.dumps(source_doc), encoding="utf-8")

    receipt = _preflight(root, evidence)

    assert "SOURCE_CLOCK_UNQUALIFIED" in receipt["reason_codes"]
    assert receipt["artifact_hashes"]["board"] is None


# ---------------------------------------------------------------------------
# Index raw bytes and clocks
# ---------------------------------------------------------------------------


def _rebind_index(root: Path, board_sha: str, snapshot_rel: str, computed_at) -> None:
    """Rewrite the index first, then freeze evidence so only the clock moves."""
    (root / "site/prophet/index.json").write_bytes(
        _index_bytes(board_sha, snapshot_rel, computed_at)
    )


def test_missing_index_clock_is_refused(tmp_path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    board_sha, snapshot_rel = _populate_prophet(root, computed_at=None)
    evidence = _freeze_evidence(tmp_path, root)

    receipt = _preflight(root, evidence)

    assert "INDEX_CLOCK_MISSING" in receipt["reason_codes"]
    assert receipt["artifact_hashes"]["index"] is None
    assert "GMI_ACCEPTED_REFERENCE_MISSING" in receipt["reason_codes"]


def test_malformed_index_clock_is_refused(tmp_path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    board_sha, snapshot_rel = _populate_prophet(root)
    _rebind_index(root, board_sha, snapshot_rel, "2026-10-31 02:15:00")
    evidence = _freeze_evidence(tmp_path, root)

    receipt = _preflight(root, evidence)

    assert "INDEX_CLOCK_UNQUALIFIED" in receipt["reason_codes"]
    assert receipt["artifact_hashes"]["index"] is None


def test_index_board_binding_mismatch_is_refused(tmp_path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    board_sha, snapshot_rel = _populate_prophet(root)
    _rebind_index(root, "0" * 64, snapshot_rel, COMPUTED_AT)
    evidence = _freeze_evidence(tmp_path, root)

    receipt = _preflight(root, evidence)

    assert "INDEX_BOARD_BINDING_MISMATCH" in receipt["reason_codes"]
    assert receipt["artifact_hashes"]["index"] is None


def test_split_checkpoint_tsv_index_mismatch_is_refused(tmp_path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _populate_prophet(root)
    evidence = _freeze_evidence(tmp_path, root)
    stale_after = "0400:" + "1" * 64
    evidence[3].write_text(
        f"site/prophet/index.json\tMISSING\t{stale_after}\n", encoding="utf-8"
    )

    receipt = _preflight(root, evidence)

    assert "SPLIT_CHECKPOINT_INDEX_MISMATCH" in receipt["reason_codes"]
    assert receipt["artifact_hashes"]["index"] is None


def test_split_checkpoint_tsv_stale_row_is_refused(tmp_path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    board_sha, snapshot_rel = _populate_prophet(root)
    evidence = _freeze_evidence(tmp_path, root)
    persisted = json.loads(evidence[0].read_text(encoding="utf-8"))
    plan_rel = "site/prophet/states/PLAN-0.json"
    wrong_after = "0400:" + "2" * 64
    assert persisted[plan_rel] != wrong_after
    evidence[3].write_text(f"{plan_rel}\tMISSING\t{wrong_after}\n", encoding="utf-8")

    receipt = _preflight(root, evidence)

    assert "SPLIT_CHECKPOINT_TSV_STALE" in receipt["reason_codes"]
    assert receipt["artifact_hashes"]["index"] is None


def test_delta_tsv_path_not_normalized_is_refused(tmp_path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _populate_prophet(root)
    evidence = _freeze_evidence(tmp_path, root)
    evidence[3].write_text(
        "site/prophet/../prophet/index.json\tMISSING\t0400:" + "3" * 64 + "\n",
        encoding="utf-8",
    )

    receipt = _preflight(root, evidence)

    assert "PATH_NOT_NORMALIZED" in receipt["reason_codes"]


def test_missing_delta_manifest_is_refused(tmp_path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _populate_prophet(root)
    evidence = _freeze_evidence(tmp_path, root)
    evidence[3].unlink()

    receipt = _preflight(root, evidence)

    assert "DELTA_MANIFEST_MISSING" in receipt["reason_codes"]


def test_missing_inventory_is_refused(tmp_path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _populate_prophet(root)
    evidence = _freeze_evidence(tmp_path, root)
    evidence[0].unlink()

    receipt = _preflight(root, evidence)

    assert "INVENTORY_MISSING" in receipt["reason_codes"]
    assert receipt["artifact_hashes"]["candidate_store"] is None
    assert receipt["candidate_count"] is None
    assert receipt["bundle_id"] is None


def test_symlinked_store_entry_is_refused(tmp_path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _populate_prophet(root)
    evidence = _freeze_evidence(tmp_path, root)
    target = root / "site/prophet/plans/PLAN-0-BULL-20261030.json"
    target.unlink()
    target.symlink_to(root / "site/prophet/states/PLAN-0.json")

    receipt = _preflight(root, evidence)

    assert "SYMLINK_REFUSED" in receipt["reason_codes"]
    assert receipt["bundle_id"] is None


# ---------------------------------------------------------------------------
# GMI ThemeState qualification
# ---------------------------------------------------------------------------


def test_descriptive_shadow_is_never_a_theme_state_qualification(tmp_path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _populate_prophet(root)
    # A plausible descriptive shadow at the incumbent alias path must NOT
    # satisfy the gate: only the accepted generation family can.
    neuralweb = root / "data/neuralweb"
    neuralweb.mkdir(parents=True)
    (neuralweb / "theme_state.json").write_text(
        json.dumps({"schema": "neuralweb.theme_state.v1", "themes": [{"theme_id": "grid"}]}),
        encoding="utf-8",
    )
    evidence = _freeze_evidence(tmp_path, root)

    receipt = _preflight(root, evidence)

    assert receipt["reason_codes"] == ["GMI_ACCEPTED_REFERENCE_MISSING"]
    assert receipt["artifact_hashes"]["theme_state"] is None
    assert receipt["leg_detail"]["gmi_theme_state"]["detail"]["receipt_status"] is None


def test_accepted_family_without_a_supplied_receipt_is_refused(
    tmp_path, production_world
) -> None:
    from tests.test_theme_state_generation import AcceptedFixture
    from tests.test_theme_state_production import compose

    root = production_world
    _populate_prophet(root)
    bundle, _ = compose(root)
    entry = g.entry_preflight(root, legacy_api=True)
    plan = g.prepare_generation(
        bundle, root=root, generated_at=EMISSION, activation_at=ACTIVATION, entry=entry
    )
    g.publish_generation(root, plan, controlled_verifier=AcceptedFixture())
    evidence = _freeze_evidence(tmp_path, root)

    receipt = _preflight(root, evidence)

    # The immutable accepted generation exists and validates, but no
    # owner-issued production read receipt exists to verify against it
    # (current-use rights owner unwired, W3B in progress). Typed, never
    # guessed around.
    assert receipt["reason_codes"] == ["GMI_RECEIPT_NOT_SUPPLIED"]
    assert receipt["leg_detail"]["gmi_theme_state"]["detail"]["generation_id"] == (
        plan["generation_id"]
    )
    assert receipt["artifact_hashes"]["theme_state"] is None
    assert receipt["bundle_id"] is None


def test_unreadable_or_invalid_gmi_receipt_is_refused(tmp_path, production_world) -> None:
    from tests.test_theme_state_generation import AcceptedFixture
    from tests.test_theme_state_production import compose

    root = production_world
    _populate_prophet(root)
    bundle, _ = compose(root)
    entry = g.entry_preflight(root, legacy_api=True)
    plan = g.prepare_generation(
        bundle, root=root, generated_at=EMISSION, activation_at=ACTIVATION, entry=entry
    )
    g.publish_generation(root, plan, controlled_verifier=AcceptedFixture())
    evidence = _freeze_evidence(tmp_path, root)

    garbage = tmp_path / "receipt-garbage.json"
    garbage.write_text("{not json", encoding="utf-8")
    unreadable = _preflight(root, evidence, gmi_receipt_path=garbage)
    assert unreadable["reason_codes"] == ["GMI_RECEIPT_UNREADABLE"]

    fabricated = tmp_path / "receipt-fabricated.json"
    fabricated.write_text(json.dumps({"schema": "gmi", "status": "DESCRIPTIVE"}), encoding="utf-8")
    invalid = _preflight(root, evidence, gmi_receipt_path=fabricated)
    assert invalid["reason_codes"] == ["GMI_RECEIPT_INVALID"]

    # round-2 N2: an invalid receipt's content is never echoed — a NaN status and a non-list
    # reason_codes must not reach the writer (allow_nan=False) and must leave the typed fields unset.
    odd = tmp_path / "receipt-odd.json"
    odd.write_text('{"schema": "gmi", "status": NaN, "reason_codes": {"x": NaN}}', encoding="utf-8")
    weird = _preflight(root, evidence, gmi_receipt_path=odd)
    assert weird["reason_codes"] == ["GMI_RECEIPT_INVALID"]
    gmi_detail = weird["leg_detail"]["gmi_theme_state"]["detail"]
    assert gmi_detail["receipt_status"] is None and gmi_detail["receipt_reason_codes"] is None
    out = tmp_path / "runner" / "odd-receipt.json"
    out.parent.mkdir()
    write_receipt(weird, out)
    assert json.loads(out.read_text(encoding="utf-8"))["reason_codes"] == ["GMI_RECEIPT_INVALID"]
    assert invalid["artifact_hashes"]["theme_state"] is None


def test_current_generation_receipt_with_owner_ceiling_is_not_qualified(
    tmp_path, production_world
) -> None:
    from engine.neuralweb import theme_state_generation_reader as reader
    from tests.test_theme_state_generation import AcceptedFixture
    from tests.test_theme_state_generation_reader import ReadFixture
    from tests.test_theme_state_production import compose, EFFECTIVE, KNOWN

    root = production_world
    _populate_prophet(root)
    bundle, _ = compose(root)
    entry = g.entry_preflight(root, legacy_api=True)
    plan = g.prepare_generation(
        bundle, root=root, generated_at=EMISSION, activation_at=ACTIVATION, entry=entry
    )
    g.publish_generation(root, plan, controlled_verifier=AcceptedFixture())
    evidence = _freeze_evidence(tmp_path, root)

    # Without a receipt the leg refuses first.
    assert _preflight(root, evidence)["reason_codes"] == ["GMI_RECEIPT_NOT_SUPPLIED"]

    # The incumbent owner's own read in its own lawful verifier context:
    # DESCRIPTIVE, immutable, current — and stamped with its production
    # qualification ceiling. The preflight must refuse on exactly that owner
    # verdict when the receipt is supplied for detached verification.
    owner_receipt = reader.read_generation_at_use(
        root, effective_at=EFFECTIVE, known_at=KNOWN,
        purpose="research_internal", use_at=USE, controlled_verifier=ReadFixture(),
    )
    assert owner_receipt["status"] == "DESCRIPTIVE"
    assert owner_receipt["reason_codes"] == ["CONTROLLED_TEST_ONLY", "D2E_NOT_QUALIFIED"]
    receipt_path = tmp_path / "owner-receipt.json"
    receipt_path.write_text(json.dumps(owner_receipt), encoding="utf-8")

    settled = _preflight(root, evidence, gmi_receipt_path=receipt_path)

    gmi = settled["leg_detail"]["gmi_theme_state"]
    assert gmi["detail"]["receipt_status"] == "DESCRIPTIVE"
    assert gmi["detail"]["receipt_reason_codes"] == [
        "CONTROLLED_TEST_ONLY",
        "D2E_NOT_QUALIFIED",
    ]
    assert settled["reason_codes"] == ["GMI_THEME_STATE_NOT_QUALIFIED"]
    assert settled["artifact_hashes"]["theme_state"] is None
    assert settled["bundle_id"] is None
    # Everything else bound: the four-asset bundle is withheld ONLY by GMI.
    assert settled["artifact_hashes"]["board"] is not None
    assert settled["artifact_hashes"]["index"] is not None
    assert settled["artifact_hashes"]["candidate_store"] is not None


def test_receipt_for_a_superseded_generation_is_refused(tmp_path, production_world) -> None:
    from engine.neuralweb import theme_state_adapter as adapter
    from engine.neuralweb import theme_state_generation_reader as reader
    from tests.test_theme_state_generation import AcceptedFixture
    from tests.test_theme_state_generation_reader import ReadFixture
    from tests.test_theme_state_production import compose, EFFECTIVE, KNOWN

    root = production_world
    _populate_prophet(root)
    bundle, _ = compose(root)
    first = g.prepare_generation(
        bundle, root=root, generated_at=EMISSION, activation_at=ACTIVATION,
        entry=g.entry_preflight(root, legacy_api=True),
    )
    g.publish_generation(root, first, controlled_verifier=AcceptedFixture())
    evidence = _freeze_evidence(tmp_path, root)
    first_receipt = reader.read_generation_at_use(
        root, effective_at=EFFECTIVE, known_at=KNOWN,
        purpose="research_internal", use_at=USE, controlled_verifier=ReadFixture(),
    )
    assert first_receipt["status"] == "DESCRIPTIVE"
    receipt_path = tmp_path / "first-receipt.json"
    receipt_path.write_text(json.dumps(first_receipt), encoding="utf-8")

    # Advance the family to a second accepted generation so the supplied
    # receipt no longer names the CURRENT one.
    corr_bundle = adapter.capture_owner_bundle(root, effective_at=EFFECTIVE, known_at=CORR_KNOWN)
    second = g.prepare_generation(
        corr_bundle, root=root, generated_at=CORR_EMITTED, activation_at=CORR_ACTIVATION,
        entry=g.entry_preflight(root),
        correction_reason="controlled later-known owner correction",
    )
    g.publish_generation(root, second, controlled_verifier=AcceptedFixture())

    receipt = _preflight(root, evidence, gmi_receipt_path=receipt_path)

    # The owner's own detached validator refuses a receipt whose accepted
    # reference names a generation other than the exact plan witness it is
    # verified against; a stale receipt can never pass as current.
    assert receipt["reason_codes"] == ["GMI_RECEIPT_INVALID"]
    assert receipt["artifact_hashes"]["theme_state"] is None
    assert receipt["bundle_id"] is None


def test_pending_generation_supersession_is_refused(tmp_path, production_world) -> None:
    from tests.test_theme_state_generation import AcceptedFixture
    from tests.test_theme_state_production import compose, EFFECTIVE

    root = production_world
    _populate_prophet(root)
    bundle, _ = compose(root)
    entry = g.entry_preflight(root, legacy_api=True)
    plan = g.prepare_generation(
        bundle, root=root, generated_at=EMISSION, activation_at=ACTIVATION, entry=entry
    )
    g.publish_generation(root, plan, controlled_verifier=AcceptedFixture())
    from engine.neuralweb import theme_state_adapter as adapter
    corr_bundle = adapter.capture_owner_bundle(root, effective_at=EFFECTIVE, known_at=CORR_KNOWN)
    pending = g.prepare_generation(
        corr_bundle, root=root, generated_at=CORR_EMITTED, activation_at=CORR_ACTIVATION,
        entry=g.entry_preflight(root, allow_pending=True),
        correction_reason="controlled later-known owner correction",
    )
    (root / g.PENDING).write_bytes(g.canonical(pending))
    evidence = _freeze_evidence(tmp_path, root)

    receipt = _preflight(root, evidence)

    assert receipt["reason_codes"] == ["GMI_PENDING_GENERATION_OWNS_PREFIX"]
    assert receipt["artifact_hashes"]["theme_state"] is None


# ---------------------------------------------------------------------------
# No accepted bundle on incomplete evidence
# ---------------------------------------------------------------------------


def test_preflight_never_writes_into_the_publication_tree_or_accepts(tmp_path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _populate_prophet(root)
    evidence = _freeze_evidence(tmp_path, root)
    before = _tree(root)
    receipt_path = tmp_path / "receipt.json"

    receipt = _preflight(root, evidence)
    write_receipt(receipt, receipt_path, root)
    first = receipt_path.read_bytes()
    write_receipt(_preflight(root, evidence), receipt_path, root)
    second = receipt_path.read_bytes()

    assert first == second, "receipt bytes must be deterministic"
    assert _tree(root) == before, "preflight mutated the publication tree"
    assert receipt["bundle_id"] is None
    assert receipt["accepted"] is False
    assert receipt["reader_proof"] is None
    assert receipt["publish"] is None
    assert set(receipt["authority_caps"].values()) == {False}
    assert receipt["status"] == STATUS_REFUSED

    # The receipt itself can never be parked inside the publication tree.
    with pytest.raises(InfrastructureError):
        write_receipt(receipt, root / "site/prophet/preflight.json", root)
    with pytest.raises(InfrastructureError):
        write_receipt(receipt, root / "data/prophet/preflight.json", root)


def test_self_check_refuses_a_bundled_identity(tmp_path) -> None:
    from scripts.prophet_settlement_preflight import _self_check

    tampered = {
        "status": STATUS_QUALIFIED,
        "bundle_id": "bundle-xyz",
        "accepted": False,
        "reason_codes": [],
        "artifact_hashes": {"board": "a", "candidate_store": "b", "index": "c",
                            "theme_state": "d"},
        "authority_caps": {key: False for key in (
            "ranking", "gating", "sizing", "insertion", "origination", "escalation",
            "trade", "predictive", "may_publish")},
    }
    with pytest.raises(InfrastructureError):
        _self_check(tampered)
    tampered["bundle_id"] = None
    tampered["accepted"] = True
    with pytest.raises(InfrastructureError):
        _self_check(tampered)
    tampered["accepted"] = False
    tampered["artifact_hashes"]["theme_state"] = None
    with pytest.raises(InfrastructureError):
        _self_check(tampered)


# ---------------------------------------------------------------------------
# Nightly wiring contract
# ---------------------------------------------------------------------------


def _nightly_source() -> str:
    return (Path(__file__).resolve().parents[1] / "scripts/ci/daily_engine_prophet_nightly.sh").read_text(
        encoding="utf-8"
    )


def _python_heredocs(source: str) -> list[str]:
    blocks, current = [], None
    for line in source.splitlines():
        if current is None and "<<'PY'" in line and "python" in line:
            current = []
        elif current is not None and line == "PY":
            blocks.append("\n".join(current) + "\n")
            current = None
        elif current is not None:
            current.append(line)
    assert current is None, "unterminated Python heredoc"
    return blocks


def test_nightly_step_wiring_stays_pinned_and_nonfatal() -> None:
    source = _nightly_source()

    # The extracted-verbatim pins survive untouched.
    assert len(_python_heredocs(source)) == 3
    import re as _re

    exact_blocks = _re.findall(r"exact = \{(.*?)\n\}", source, flags=_re.S)
    assert len(exact_blocks) == 2
    assert source.count('"data/prophet/origination_sources": "*.json.gz"') == 2
    assert source.count('"data/prophet/legacy_shadow": "*/*.parquet"') == 2

    # Full-population persistence lives in the delta heredoc only.
    persistence = source.count('inventory_target = os.environ.get("PROPHET_INVENTORY")')
    assert persistence == 1
    heredocs = _python_heredocs(source)
    assert "inventory_target" in heredocs[2]
    compile(heredocs[2], "nightly-delta-heredoc", "exec")

    # The preflight runs ONLY after the checkpoint outputs exist, captures its
    # rc, and never flips the checkpoint contract.
    delta_out = source.index('echo "delta_manifest=$PROPHET_DELTA" >> "$GITHUB_OUTPUT"')
    invocation = source.index("python3 -m scripts.prophet_settlement_preflight")
    final_exit = source.index("exit 0\n", invocation)
    assert delta_out < invocation < final_exit
    assert "preflight_rc=$?" in source
    assert source.count("succeeded=false") == 4  # unchanged failure contract
    assert "PROPHET_PREFLIGHT_RECEIPT" in source
    # The nightly neither invents a use clock nor fabricates a GMI receipt.
    assert "--gmi-use-at" not in source
    assert "--gmi-receipt" not in source


def test_dag_declares_the_preflight_after_build_prophet() -> None:
    import yaml

    dag = yaml.safe_load(
        (Path(__file__).resolve().parents[1] / "config/dag.yml").read_text(encoding="utf-8")
    )
    modules = [
        step.get("module")
        for lane in dag.get("lanes") or []
        for step in (lane.get("steps") or [])
        if isinstance(step, dict)
    ]
    build_i = modules.index("scripts.build_prophet")
    preflight_i = modules.index("scripts.prophet_settlement_preflight")
    acceptance_i = modules.index("scripts.prophet_board_acceptance")
    assert build_i < preflight_i < acceptance_i


def test_module_invocation_shape_matches_dag_extraction() -> None:
    from scripts.check_dag_conformance import _extract_modules_from_run

    nightly = Path(__file__).resolve().parents[1] / "scripts/ci/daily_engine_prophet_nightly.sh"
    modules = _extract_modules_from_run(nightly.read_text(encoding="utf-8"))
    assert modules == ["scripts.build_prophet", "scripts.prophet_settlement_preflight"]


def test_cli_writes_the_typed_receipt_runner_locally(tmp_path) -> None:
    import os
    import subprocess
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    root = tmp_path / "repo"
    root.mkdir()
    _populate_prophet(root)
    evidence = _freeze_evidence(tmp_path, root)
    receipt_path = tmp_path / "receipt.json"
    env = os.environ.copy()
    env.update(
        {
            "GITHUB_WORKSPACE": str(root),
            "PROPHET_INVENTORY": str(evidence[0]),
            "PROPHET_SOURCE_SNAPSHOT": str(evidence[1]),
            "PROPHET_SOURCE_BLOB": str(evidence[2]),
            "PROPHET_DELTA": str(evidence[3]),
            "PROPHET_PREFLIGHT_RECEIPT": str(receipt_path),
            "PYTHONPATH": str(repo_root),
        }
    )

    result = subprocess.run(
        [sys.executable, "-m", "scripts.prophet_settlement_preflight"],
        cwd=repo_root, env=env, capture_output=True, text=True, check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    # NOT_SETTLED is an alarm (warning), never a quiet notice.
    assert "::warning title=prophet accepted-source preflight::status=NOT_SETTLED" in result.stdout
    assert "::notice title=prophet accepted-source preflight" not in result.stdout
    assert "bundle_id=null" in result.stdout
    doc = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert doc["schema"] == "prophet.accepted_source_preflight/v1"
    assert doc["status"] == "NOT_SETTLED"
    assert doc["reason_codes"] == ["GMI_ACCEPTED_REFERENCE_MISSING"]
    assert doc["bundle_id"] is None and doc["accepted"] is False

    # Missing evidence paths are an infrastructure refusal (rc 2), never a
    # silently green run.
    env.pop("PROPHET_INVENTORY")
    failed = subprocess.run(
        [sys.executable, "-m", "scripts.prophet_settlement_preflight"],
        cwd=repo_root, env=env, capture_output=True, text=True, check=False,
    )
    assert failed.returncode == 2
    assert "::error title=prophet accepted-source preflight::missing required evidence paths" in (
        failed.stdout
    )


# --- round-2 repairs (review of #10289: M1-M4, m1-m6) -------------------------------------------


def _accepted_world(tmp_path, production_world):
    """An immutable accepted generation + frozen evidence, as the owner publishes it."""
    from tests.test_theme_state_generation import AcceptedFixture
    from tests.test_theme_state_production import compose

    root = production_world
    _populate_prophet(root)
    bundle, _ = compose(root)
    entry = g.entry_preflight(root, legacy_api=True)
    plan = g.prepare_generation(
        bundle, root=root, generated_at=EMISSION, activation_at=ACTIVATION, entry=entry
    )
    g.publish_generation(root, plan, controlled_verifier=AcceptedFixture())
    return root, plan, _freeze_evidence(tmp_path, root)


def _owner_receipt(root, tmp_path) -> tuple[Path, dict]:
    from engine.neuralweb import theme_state_generation_reader as reader
    from tests.test_theme_state_generation_reader import ReadFixture
    from tests.test_theme_state_production import EFFECTIVE, KNOWN

    owner_receipt = reader.read_generation_at_use(
        root, effective_at=EFFECTIVE, known_at=KNOWN,
        purpose="research_internal", use_at=USE, controlled_verifier=ReadFixture(),
    )
    path = tmp_path / "owner-receipt.json"
    path.write_text(json.dumps(owner_receipt), encoding="utf-8")
    return path, owner_receipt


def test_owner_receipt_identity_binds_raw_to_raw_and_semantic_to_semantic(
    tmp_path, production_world
) -> None:
    """M1: the preflight's two state digests equal the owner's two, not each other."""
    root, _plan, evidence = _accepted_world(tmp_path, production_world)
    receipt_path, owner_receipt = _owner_receipt(root, tmp_path)

    settled = _preflight(root, evidence, gmi_receipt_path=receipt_path)
    detail = settled["leg_detail"]["gmi_theme_state"]["detail"]
    identity = owner_receipt["state_identity"]
    assert detail["state_raw_sha256"] == identity["raw_sha256"]
    assert detail["state_semantic_sha256"] == identity["semantic_sha256"]
    assert detail["state_raw_sha256"] != detail["state_semantic_sha256"]
    # The owner's production ceiling is the ONLY thing refusing this receipt.
    assert settled["reason_codes"] == ["GMI_THEME_STATE_NOT_QUALIFIED"]
    assert "GMI_STATE_IDENTITY_MISMATCH" not in settled["reason_codes"]


def test_pass_through_is_reachable_once_the_owner_ceiling_lifts_and_every_leg_flips_back(
    tmp_path, production_world, monkeypatch
) -> None:
    """M2: QUALIFIED_SOURCE_PREFLIGHT is produced by run_preflight with real evidence.

    The owner reader today stamps every receipt with its production ceiling
    (``CONTROLLED_TEST_ONLY``, ``D2E_NOT_QUALIFIED``) and its validator binds
    exactly those codes, so no genuine receipt can clear the ceiling yet. The
    monkeypatch lifts the preflight's ceiling list and nothing else: the
    receipt, generation, hashes and validators are the owner's own.
    """
    import scripts.prophet_settlement_preflight as module

    root, plan, evidence = _accepted_world(tmp_path, production_world)
    receipt_path, owner_receipt = _owner_receipt(root, tmp_path)
    monkeypatch.setattr(module, "GMI_UNQUALIFIED_CODES", ())

    qualified = _preflight(root, evidence, gmi_receipt_path=receipt_path)
    assert qualified["status"] == STATUS_QUALIFIED
    assert qualified["reason_codes"] == []
    assert all(qualified["artifact_hashes"].values())
    assert qualified["artifact_hashes"]["theme_state"] == owner_receipt["state_identity"]["raw_sha256"]
    assert qualified["leg_detail"]["gmi_theme_state"]["detail"]["generation_id"] == plan["generation_id"]
    # Even the pass-through never settles, accepts or mints a bundle.
    assert qualified["accepted"] is False
    assert qualified["bundle_id"] is None
    assert qualified["reader_proof"] is None and qualified["publish"] is None
    assert set(qualified["authority_caps"].values()) == {False}

    # Flip one leg at a time; each flips the whole receipt back to NOT_SETTLED.
    assert _preflight(root, evidence)["reason_codes"] == ["GMI_RECEIPT_NOT_SUPPLIED"]

    inventory, source_snapshot, blob, delta = evidence
    broken_blob = tmp_path / "board.other.json"
    broken_blob.write_bytes(_board_bytes("2026-10-29"))
    flipped = _preflight(root, (inventory, source_snapshot, broken_blob, delta),
                         gmi_receipt_path=receipt_path)
    assert flipped["status"] == STATUS_REFUSED
    assert "SOURCE_CHANGED_AFTER_FREEZE" in flipped["reason_codes"]
    assert flipped["artifact_hashes"]["board"] is None

    (root / "site/prophet/plans/PLAN-99-BULL-20261030.json").write_text("{}\n", encoding="utf-8")
    flipped = _preflight(root, evidence, gmi_receipt_path=receipt_path)
    assert flipped["status"] == STATUS_REFUSED
    assert "INVENTORY_POPULATION_CHANGED" in flipped["reason_codes"]
    (root / "site/prophet/plans/PLAN-99-BULL-20261030.json").unlink()

    missing_inventory = tmp_path / "no-inventory.json"
    flipped = _preflight(root, (missing_inventory, source_snapshot, blob, delta),
                         gmi_receipt_path=receipt_path)
    assert flipped["status"] == STATUS_REFUSED
    assert "INVENTORY_MISSING" in flipped["reason_codes"]

    monkeypatch.setattr(module, "GMI_UNQUALIFIED_CODES", ("D2E_NOT_QUALIFIED", "CONTROLLED_TEST_ONLY"))
    assert _preflight(root, evidence, gmi_receipt_path=receipt_path)["reason_codes"] == [
        "GMI_THEME_STATE_NOT_QUALIFIED"
    ]


def test_missing_or_unbound_source_snapshot_leaves_a_typed_receipt(tmp_path) -> None:
    """M3: a settlement that cannot be proven still leaves NOT_SETTLED, never a missing run."""
    root = tmp_path / "repo"
    root.mkdir()
    _populate_prophet(root)
    inventory, source_snapshot, blob, delta = _freeze_evidence(tmp_path, root)

    gone = tmp_path / "source-gone.json"
    receipt = _preflight(root, (inventory, gone, blob, delta))
    assert receipt["status"] == STATUS_REFUSED
    assert "SOURCE_SNAPSHOT_MISSING" in receipt["reason_codes"]
    assert "INDEX_BOARD_BINDING_MISMATCH" in receipt["reason_codes"]
    assert receipt["artifact_hashes"]["board"] is None
    assert receipt["artifact_hashes"]["index"] is None

    unbound = tmp_path / "source-unbound.json"
    unbound.write_text(json.dumps({"schema": "x", "source": {"path": BOARD_REL}}), encoding="utf-8")
    receipt = _preflight(root, (inventory, unbound, blob, delta))
    assert "SOURCE_SNAPSHOT_UNBOUND" in receipt["reason_codes"]
    assert receipt["bundle_id"] is None

    # The CLI keeps rc 0 and writes the receipt for this case.
    import os
    import subprocess
    import sys

    receipt_path = tmp_path / "receipt-m3.json"
    env = os.environ.copy()
    env.update({
        "GITHUB_WORKSPACE": str(root), "PROPHET_INVENTORY": str(inventory),
        "PROPHET_SOURCE_SNAPSHOT": str(gone), "PROPHET_SOURCE_BLOB": str(blob),
        "PROPHET_DELTA": str(delta), "PROPHET_PREFLIGHT_RECEIPT": str(receipt_path),
        "PYTHONPATH": str(Path(__file__).resolve().parents[1]),
    })
    result = subprocess.run(
        [sys.executable, "-m", "scripts.prophet_settlement_preflight"],
        cwd=Path(__file__).resolve().parents[1], env=env, capture_output=True, text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "::warning title=prophet accepted-source preflight::status=NOT_SETTLED" in result.stdout
    doc = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert "SOURCE_SNAPSHOT_MISSING" in doc["reason_codes"]


def test_symlinked_index_and_malformed_inventory_are_typed_not_crashes(tmp_path) -> None:
    """m1: no traceback paths — symlinked index, non-string / colon-less inventory values."""
    root = tmp_path / "repo"
    root.mkdir()
    _populate_prophet(root)
    inventory, source_snapshot, blob, delta = _freeze_evidence(tmp_path, root)

    index = root / INDEX_REL
    real = tmp_path / "index-real.json"
    real.write_bytes(index.read_bytes())
    index.unlink()
    index.symlink_to(real)
    receipt = _preflight(root, (inventory, source_snapshot, blob, delta))
    assert receipt["status"] == STATUS_REFUSED
    assert receipt["leg_detail"]["index"]["reason_codes"] == ["SYMLINK_REFUSED"]
    assert receipt["artifact_hashes"]["index"] is None
    index.unlink()
    index.write_bytes(real.read_bytes())

    for bad in ({"site/prophet/index.json": 7}, {"site/prophet/index.json": "no-colon"},
                {"site/prophet/index.json": "0644:short"}):
        malformed = tmp_path / "inventory-malformed.json"
        malformed.write_text(json.dumps(bad), encoding="utf-8")
        receipt = _preflight(root, (malformed, source_snapshot, blob, delta))
        assert receipt["status"] == STATUS_REFUSED
        assert receipt["leg_detail"]["inventory"]["reason_codes"] == ["INVENTORY_MALFORMED"]
        assert receipt["leg_detail"]["candidate_store"]["reason_codes"] == ["INVENTORY_MISSING"]


def test_empty_candidate_store_is_a_typed_refusal(tmp_path) -> None:
    """m3: zero plans never qualify as a bound population."""
    root = tmp_path / "repo"
    root.mkdir()
    _populate_prophet(root, plans=0)
    evidence = _freeze_evidence(tmp_path, root)
    receipt = _preflight(root, evidence)
    store = receipt["leg_detail"]["candidate_store"]
    assert store["reason_codes"] == ["CANDIDATE_STORE_EMPTY"]
    assert store["sha256"] is None and store["file_count"] == 0
    assert receipt["candidate_count"] == 0
    assert receipt["artifact_hashes"]["candidate_store"] is None


def test_snapshot_path_outside_the_allowlist_is_refused(tmp_path) -> None:
    """m4: the durable copy must be a normalized path inside the snapshot dir and the inventory."""
    root = tmp_path / "repo"
    root.mkdir()
    board_sha, snapshot_rel = _populate_prophet(root)
    inventory, source_snapshot, blob, delta = _freeze_evidence(tmp_path, root)
    doc = json.loads(source_snapshot.read_text(encoding="utf-8"))
    outside = tmp_path / "outside.json.gz"
    outside.write_bytes((root / snapshot_rel).read_bytes())
    for bad in ("../outside.json.gz", str(outside), "site/prophet/index.json",
                "data/prophet/origination_sources/not-in-inventory.json.gz"):
        doc["source"]["snapshot_path"] = bad
        tampered = tmp_path / "source-tampered.json"
        tampered.write_text(json.dumps(doc), encoding="utf-8")
        receipt = _preflight(root, (inventory, tampered, blob, delta))
        board = receipt["leg_detail"]["board"]
        assert "SNAPSHOT_PATH_UNQUALIFIED" in board["reason_codes"], bad
        assert "DURABLE_SOURCE_SNAPSHOT_MISSING" in board["reason_codes"], bad
        assert receipt["artifact_hashes"]["board"] is None


def test_nightly_allowlists_match_the_importable_inventory_module() -> None:
    """m5: both heredoc allowlists and the module constants are the same sets."""
    import ast
    import re as _re

    from scripts.prophet_output_inventory import DIRECTORY_GLOBS, EXACT_PATHS

    source = _nightly_source()
    exact_blocks = _re.findall(r"exact = (\{.*?\n\})", source, flags=_re.S)
    glob_blocks = _re.findall(r"globs = (\{.*?\n\})", source, flags=_re.S)
    assert len(exact_blocks) == 2 and len(glob_blocks) == 2
    for block in exact_blocks:
        assert ast.literal_eval(block) == set(EXACT_PATHS)
    for block in glob_blocks:
        assert ast.literal_eval(block) == dict(DIRECTORY_GLOBS)


def test_receipt_is_refused_anywhere_inside_the_repository(tmp_path) -> None:
    """m6: runner-local means outside the checkout, not merely outside site/ and data/."""
    root = tmp_path / "repo"
    root.mkdir()
    _populate_prophet(root)
    receipt = _preflight(root, _freeze_evidence(tmp_path, root))
    with pytest.raises(InfrastructureError):
        write_receipt(receipt, root / "preflight.json", root)
    with pytest.raises(InfrastructureError):
        write_receipt(receipt, root / "research/preflight.json", root)
    write_receipt(receipt, tmp_path / "outside.json", root)
    assert (tmp_path / "outside.json").is_file()


def test_nightly_inventory_write_failure_never_flips_the_checkpoint(tmp_path, monkeypatch) -> None:
    """M4: the alarm-only inventory write is wrapped; manifest_rc cannot come from it."""
    source = _nightly_source()
    heredoc = _python_heredocs(source)[2]
    start = heredoc.index('inventory_target = os.environ.get("PROPHET_INVENTORY")')
    tail = heredoc[start:]
    assert "try:" in tail and "except OSError" in tail
    assert "::warning title=prophet full-population inventory" in tail
    assert "sys.exit" not in tail and "raise" not in tail
    # round-2 N5: run the extracted block itself against an unwritable target — it must print the
    # warning and return normally (the shell's manifest_rc then stays 0).
    import io, contextlib
    blocker = tmp_path / "not-a-dir"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setenv("PROPHET_INVENTORY", str(blocker / "inventory.json"))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(compile(tail, "nightly-inventory-block", "exec"), {"os": os, "json": json, "Path": Path, "after": {"k": 1}})
    assert "::warning title=prophet full-population inventory" in out.getvalue()
    assert not (blocker / "inventory.json").exists()

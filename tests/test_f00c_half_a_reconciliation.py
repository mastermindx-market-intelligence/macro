"""Pin packet A-REC-W4-1: the F00C ledger reconciled against the merged half-A wave.

Nine ledger rows were re-read against seven merged Macro pull requests. Every claim
this suite checks is read from a CHECKED-IN manifest — never by shelling out to git
or `gh` at test time. The manifest is the record; the ledger CSV is the surface;
this suite asserts the two agree.

RED before the packet: the nine rows still read SPEC_ONLY or PARTIAL with
`state_delta` UNCHANGED (or an UNVERIFIED/REFRESHED note that did not name the
merged half-A builds), so Charter §2's DONE test under-counted the program's own
progress by these nine rows.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]

MANIFEST = _ROOT / "tests/fixtures/f00c_half_a_reconciliation_manifest.json"
LEDGER = _ROOT / (
    "research/market_intelligence_productization/"
    "MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv"
)
RECORDS_DOC = _ROOT / (
    "research/market_intelligence_productization/"
    "MARKET_ONTOLOGY_A_REC_W4_1_HALF_A_LEDGER_RECONCILIATION_2026-09-09.md"
)
WAIVERS = _ROOT / "config/unrun_test_waivers.yml"

ROWS = (
    "MO-DELTA-032",
    "MO-PAID-007",
    "MO-PAID-023",
    "MO-PAID-034",
    "MO-DELTA-001",
    "MO-DELTA-004",
    "MO-DELTA-015",
    "MO-PAID-003",
    "MO-PAID-004",
)

LEDGER_COLUMNS = (
    "id", "family", "granular_disposition", "capability_state_c2", "state_delta",
    "current_owner", "real_producer", "real_consumer", "missing_contract_or_proof",
    "correction_behavior", "next_bounded_child", "acceptance_test", "source_rights",
    "authority_ceiling", "adjudication_notes",
)


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _manifest_rows() -> dict[str, dict]:
    return {row["id"]: row for row in _manifest()["rows"]}


def _ledger_rows() -> dict[str, dict]:
    with LEDGER.open(newline="", encoding="utf-8") as fh:
        return {row["id"]: row for row in csv.DictReader(fh)}


def _stacked_absent() -> set[str]:
    return set(_manifest().get("stacked_head_absent_producer_paths") or ())


def test_manifest_exists_and_covers_the_nine_rows_once_each() -> None:
    assert MANIFEST.exists(), f"missing reconciliation manifest: {MANIFEST}"
    ids = [row["id"] for row in _manifest()["rows"]]
    assert len(ids) == len(set(ids)), "a row is listed twice in the manifest"
    assert set(ids) == set(ROWS), (
        f"manifest rows {sorted(set(ids))} != packet rows {sorted(ROWS)}"
    )


def test_each_manifest_entry_has_the_named_fields() -> None:
    for row in _manifest()["rows"]:
        for key in ("id", "pr", "merge_sha", "producer_paths", "acceptance_test"):
            assert key in row, f"{row.get('id')}: missing manifest field {key}"
        assert row["producer_paths"], f"{row['id']}: no producer path recorded"
        assert len(row["merge_sha"]) == 40, f"{row['id']}: merge_sha is not 40 hex chars"


@pytest.mark.parametrize("row_id", ROWS)
def test_ledger_row_is_unique(row_id: str) -> None:
    text = LEDGER.read_text(encoding="utf-8")
    count = text.count(f"\n{row_id},") + int(text.startswith(f"{row_id},"))
    assert count == 1, f"{row_id}: expected exactly one ledger row, found {count}"


@pytest.mark.parametrize("row_id", ROWS)
def test_capability_state_is_built_not_proven(row_id: str) -> None:
    ledger = _ledger_rows()[row_id]
    assert ledger["capability_state_c2"] == "BUILT_NOT_PROVEN", (
        f"{row_id}: ledger says {ledger['capability_state_c2']!r}"
    )


@pytest.mark.parametrize("row_id", ROWS)
def test_real_producer_names_the_manifest_pr_and_merge_sha(row_id: str) -> None:
    ledger = _ledger_rows()[row_id]
    manifest = _manifest_rows()[row_id]
    producer = ledger["real_producer"]
    pr = str(manifest["pr"])
    sha = manifest["merge_sha"]
    assert f"macro#{pr}" in producer, (
        f"{row_id}: real_producer does not name macro#{pr}: {producer!r}"
    )
    assert sha[:10] in producer, (
        f"{row_id}: real_producer does not name merge sha {sha[:10]}: {producer!r}"
    )


@pytest.mark.parametrize("row_id", ROWS)
def test_producer_paths_exist_on_disk(row_id: str) -> None:
    """Path.exists() only. No git, no gh, no network.

    Three producer paths landed on origin/main in merges that are not ancestors
    of this stacked HEAD (#6928 uk_policy_brain, #6929 market_ontology). Those
    paths are recorded in the manifest and named in real_producer; requiring
    them on disk here would force this PR to import files the named-files bound
    forbids. If a later rebase makes them appear, Path.exists() still holds.
    """
    absent = _stacked_absent()
    for path in _manifest_rows()[row_id]["producer_paths"]:
        on_disk = (_ROOT / path).exists()
        if path in absent and not on_disk:
            continue
        assert on_disk, f"{row_id}: producer path {path} is missing from this worktree"


@pytest.mark.parametrize("row_id", ROWS)
def test_next_bounded_child_is_empty(row_id: str) -> None:
    ledger = _ledger_rows()[row_id]
    assert ledger["next_bounded_child"] == "", (
        f"{row_id}: next_bounded_child should be empty, got "
        f"{ledger['next_bounded_child']!r}"
    )


@pytest.mark.parametrize("row_id", ROWS)
def test_manifest_quotes_the_ledger_acceptance_sentence_verbatim(row_id: str) -> None:
    assert _manifest_rows()[row_id]["acceptance_test"] == _ledger_rows()[row_id]["acceptance_test"], (
        f"{row_id}: the manifest must judge the ledger's own acceptance sentence"
    )


def test_no_row_in_this_packet_claims_a_production_readback() -> None:
    for row_id, row in _ledger_rows().items():
        if row_id not in ROWS:
            continue
        assert row["capability_state_c2"] != "PROVEN_LIVE", (
            f"{row_id}: PROVEN_LIVE needs a production readback this packet does not have"
        )


def test_ledger_shape_is_unchanged() -> None:
    with LEDGER.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    assert tuple(rows[0]) == LEDGER_COLUMNS, "the ledger's column order moved"
    assert len(rows) == 131, f"the ledger gained or lost rows: {len(rows)} records incl. header"
    assert all(len(r) == len(LEDGER_COLUMNS) for r in rows), "a ledger row has the wrong width"


def test_records_doc_exists_and_names_every_row_and_both_caveats() -> None:
    assert RECORDS_DOC.exists(), f"missing records document: {RECORDS_DOC}"
    text = RECORDS_DOC.read_text(encoding="utf-8")
    for row_id in ROWS:
        assert row_id in text, f"records document does not mention {row_id}"
    assert "data tier only" in text, "records document dropped the MO-DELTA-004 caveat"
    assert "A-F04-W2-2 owns the rendered surface" in text
    assert "#6957" in text, "records document dropped the MO-PAID-004 collision flag"
    assert "BUILT_NOT_PROVEN" in text
    assert "PROVEN_LIVE" in text


def test_this_suite_is_not_waived() -> None:
    assert WAIVERS.exists(), f"missing waivers file: {WAIVERS}"
    text = WAIVERS.read_text(encoding="utf-8")
    assert "test_f00c_half_a_reconciliation" not in text, (
        "this suite must run; do not add it to config/unrun_test_waivers.yml"
    )

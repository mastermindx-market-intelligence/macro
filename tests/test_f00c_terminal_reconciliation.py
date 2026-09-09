"""Pin packet B-REC-B5-1: the F00C ledger reconciled against the merged half-B
Terminal wave.

Twelve ledger rows were re-read against ten merged Terminal pull requests. Every
claim this suite checks is read from a CHECKED-IN manifest — never by shelling to
the other checkout at test time, which would make the suite depend on a working
tree this repository does not own and cannot pin. The manifest is the record; the
ledger CSV is the surface; this suite asserts the two agree and that neither
invents a state.

RED before the packet: the manifest did not exist and all twelve rows still read
NOT_BUILT, SPEC_ONLY or PARTIAL with `state_delta` UNCHANGED, so Charter §2's DONE
test under-counted the program's own progress by these twelve rows.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]

MANIFEST = _ROOT / (
    "research/market_intelligence_productization/"
    "F00C_TERMINAL_WAVE_RECONCILIATION_MANIFEST_2026-09-09.json"
)
LEDGER = _ROOT / (
    "research/market_intelligence_productization/"
    "MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv"
)
RECORDS_DOC = _ROOT / (
    "research/market_intelligence_productization/"
    "MARKET_ONTOLOGY_F00C_TERMINAL_WAVE_RECONCILIATION_2026-09-09.md"
)

ROWS = (
    "MO-PAID-028", "MO-PAID-036", "MO-PAID-046", "MO-PAID-051",
    "MO-PAID-053", "MO-PAID-081", "MO-PAID-082", "MO-PAID-083",
    "MO-PAID-086", "MO-PAID-087", "MO-DELTA-014", "MO-DELTA-042",
)

# The vocabulary the column already carries. A packet may move a row inside this
# set; it may never widen the set.
CAPABILITY_STATES = {"NOT_BUILT", "SPEC_ONLY", "PARTIAL", "BUILT_NOT_PROVEN", "PROVEN_LIVE"}
CLOSED_STATES = {"BUILT_NOT_PROVEN", "PROVEN_LIVE"}
DISPOSITIONS = {"SATISFIED", "NOT_SATISFIED"}

LEDGER_COLUMNS = (
    "id", "family", "granular_disposition", "capability_state_c2", "state_delta",
    "current_owner", "real_producer", "real_consumer", "missing_contract_or_proof",
    "correction_behavior", "next_bounded_child", "acceptance_test", "source_rights",
    "authority_ceiling", "adjudication_notes",
)

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _manifest_rows() -> dict[str, dict]:
    return {row["id"]: row for row in _manifest()["rows"]}


def _ledger_rows() -> dict[str, dict]:
    with LEDGER.open(newline="", encoding="utf-8") as fh:
        return {row["id"]: row for row in csv.DictReader(fh)}


# ------------------------------------------------------------ the manifest


def test_manifest_exists_and_covers_the_twelve_rows_once_each() -> None:
    assert MANIFEST.exists(), f"missing reconciliation manifest: {MANIFEST}"
    ids = [row["id"] for row in _manifest()["rows"]]
    assert len(ids) == len(set(ids)), "a row is listed twice in the manifest"
    assert set(ids) == set(ROWS), (
        f"manifest rows {sorted(set(ids))} != packet rows {sorted(ROWS)}"
    )


def test_manifest_pins_the_terminal_master_it_was_read_at() -> None:
    data = _manifest()
    assert data["terminal_repo"].endswith("/mastermind-terminal")
    assert _SHA_RE.match(data["terminal_master_sha"]), (
        "the manifest must pin the Terminal master commit it was verified against"
    )


def test_every_named_terminal_pr_records_a_merge_commit() -> None:
    prs = _manifest()["terminal_prs"]
    # The ten merged pull requests the packet was commissioned against.
    assert set(prs) == {"513", "514", "515", "517", "520", "522", "524", "526", "527", "529"}
    for number, pr in prs.items():
        assert pr["state"] == "MERGED", f"terminal#{number} is not recorded as merged"
        assert _SHA_RE.match(pr["merge_sha"]), f"terminal#{number}: bad merge sha"
        assert pr["title"].strip(), f"terminal#{number}: no title recorded"


@pytest.mark.parametrize("row_id", ROWS)
def test_every_row_names_a_merged_terminal_pr(row_id: str) -> None:
    row = _manifest_rows()[row_id]
    prs = _manifest()["terminal_prs"]
    number = str(row["terminal_pr"])
    assert number in prs, f"{row_id}: names terminal#{number}, which the manifest does not list"
    assert row["merge_sha"] == prs[number]["merge_sha"], (
        f"{row_id}: merge sha disagrees with the pull request it names"
    )


@pytest.mark.parametrize("row_id", ROWS)
def test_every_row_names_producer_paths_that_exist_on_terminal_master(row_id: str) -> None:
    data = _manifest()
    on_master = data["producer_paths_on_master"]
    paths = _manifest_rows()[row_id]["producer_paths"]
    assert paths, f"{row_id}: no producer path recorded"
    for path in paths:
        assert on_master.get(path) is True, (
            f"{row_id}: producer path {path!r} is not recorded as present on "
            f"Terminal master {data['terminal_master_sha'][:8]}"
        )


def test_no_producer_path_is_recorded_as_absent() -> None:
    """The manifest is a record of what WAS found, not a wish list."""
    for path, present in _manifest()["producer_paths_on_master"].items():
        assert present is True, f"{path}: recorded as absent from Terminal master"


# ------------------------------------------------- dispositions and residuals


@pytest.mark.parametrize("row_id", ROWS)
def test_disposition_and_state_agree(row_id: str) -> None:
    row = _manifest_rows()[row_id]
    assert row["disposition"] in DISPOSITIONS, f"{row_id}: unknown disposition"
    assert row["capability_state_c2"] in CAPABILITY_STATES, (
        f"{row_id}: {row['capability_state_c2']!r} is not in the column's vocabulary"
    )
    if row["disposition"] == "SATISFIED":
        assert row["capability_state_c2"] in CLOSED_STATES, (
            f"{row_id}: a satisfied acceptance sentence moves the row"
        )
    else:
        assert row["capability_state_c2"] not in CLOSED_STATES, (
            f"{row_id}: the acceptance sentence is not satisfied, so the row stays open"
        )


@pytest.mark.parametrize("row_id", ROWS)
def test_an_open_row_names_its_residual(row_id: str) -> None:
    row = _manifest_rows()[row_id]
    if row["disposition"] == "NOT_SATISFIED":
        assert row.get("residual"), f"{row_id}: an open row must name what is missing"


def test_no_row_in_this_packet_claims_a_production_readback() -> None:
    """The 0014/0015/0016 receipts prove the DDL applied, not that a user did
    anything with it. Nothing in the seat's records is a two-user production
    proof, so no row may read PROVEN_LIVE off this wave."""
    for row_id, row in _manifest_rows().items():
        assert row["capability_state_c2"] != "PROVEN_LIVE", (
            f"{row_id}: PROVEN_LIVE needs a production readback this packet does not have"
        )


# ------------------------------------------------------- manifest vs ledger


@pytest.mark.parametrize("row_id", ROWS)
def test_ledger_row_is_unique_and_matches_the_manifest_state(row_id: str) -> None:
    text = LEDGER.read_text(encoding="utf-8")
    assert text.count(f"\n{row_id},") + text.startswith(f"{row_id},") == 1, (
        f"{row_id}: expected exactly one ledger row"
    )
    ledger = _ledger_rows()[row_id]
    manifest = _manifest_rows()[row_id]
    assert ledger["capability_state_c2"] == manifest["capability_state_c2"], (
        f"{row_id}: ledger says {ledger['capability_state_c2']!r}, manifest says "
        f"{manifest['capability_state_c2']!r}"
    )


@pytest.mark.parametrize("row_id", ROWS)
def test_manifest_quotes_the_ledger_acceptance_sentence_verbatim(row_id: str) -> None:
    assert _manifest_rows()[row_id]["acceptance_test"] == _ledger_rows()[row_id]["acceptance_test"], (
        f"{row_id}: the manifest must judge the ledger's own acceptance sentence"
    )


@pytest.mark.parametrize("row_id", ROWS)
def test_a_moved_row_records_its_producer_and_empties_its_next_child(row_id: str) -> None:
    manifest = _manifest_rows()[row_id]
    if manifest["disposition"] != "SATISFIED":
        return
    ledger = _ledger_rows()[row_id]
    assert ledger["next_bounded_child"] == "", (
        f"{row_id}: a satisfied row carries no next bounded child"
    )
    assert manifest["merge_sha"][:8] in ledger["real_producer"], (
        f"{row_id}: real_producer must carry the merge commit that produced it"
    )
    assert any(p in ledger["real_producer"] for p in manifest["producer_paths"]), (
        f"{row_id}: real_producer must name at least one producer path"
    )
    assert ledger["state_delta"] not in ("", "UNCHANGED"), (
        f"{row_id}: state_delta must say what changed"
    )


@pytest.mark.parametrize("row_id", ROWS)
def test_an_open_row_keeps_a_next_child_and_names_the_residual_in_the_ledger(row_id: str) -> None:
    manifest = _manifest_rows()[row_id]
    if manifest["disposition"] != "NOT_SATISFIED":
        return
    ledger = _ledger_rows()[row_id]
    assert ledger["next_bounded_child"].strip(), (
        f"{row_id}: an open row keeps a next bounded child"
    )
    assert ledger["adjudication_notes"].strip(), (
        f"{row_id}: an open row names its residual in adjudication_notes"
    )


def test_ledger_shape_is_unchanged() -> None:
    with LEDGER.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    assert tuple(rows[0]) == LEDGER_COLUMNS, "the ledger's column order moved"
    assert len(rows) == 131, f"the ledger gained or lost rows: {len(rows)} records incl. header"
    assert all(len(r) == len(LEDGER_COLUMNS) for r in rows), "a ledger row has the wrong width"


# ------------------------------------------------------------ records doc


def test_records_doc_exists_and_names_every_row_and_pull_request() -> None:
    assert RECORDS_DOC.exists(), f"missing records document: {RECORDS_DOC}"
    text = RECORDS_DOC.read_text(encoding="utf-8")
    for row_id in ROWS:
        assert row_id in text, f"records document does not mention {row_id}"
    for number in _manifest()["terminal_prs"]:
        assert f"#{number}" in text, f"records document does not mention terminal#{number}"


def test_records_doc_states_what_built_not_proven_means() -> None:
    text = RECORDS_DOC.read_text(encoding="utf-8")
    assert "BUILT_NOT_PROVEN" in text
    assert "two" in text.lower(), (
        "the document must say the rows are merged but not yet proven by two users "
        "in production"
    )

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

def _current_manifest_rows() -> dict[str, dict]:
    """Current canonical mirror; the original rows array remains historical evidence."""
    block = _manifest()["current_terminal_rows_2026_09_19"]
    assert block["row_count"] == len(ROWS)
    rows = block["rows"]
    assert set(rows) == set(ROWS)
    return rows


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


def test_every_named_pull_request_is_accounted_for_exactly_once() -> None:
    """Ten pull requests were named. Each one either moves a row in this packet or is
    listed with the reason it moves none. A pull request that appears in neither list is
    an accounting hole: the reader cannot tell whether it was judged and found irrelevant
    or simply never read."""
    data = _manifest()
    named = set(data["terminal_prs"])
    moves_a_row = {str(row["terminal_pr"]) for row in data["rows"]}
    moves_nothing = set(data["prs_that_move_no_row_in_this_packet"])
    assert not (moves_a_row & moves_nothing), (
        "a pull request cannot both move a row and be listed as moving none: "
        f"{sorted(moves_a_row & moves_nothing)}"
    )
    assert named == moves_a_row | moves_nothing, (
        f"unaccounted for: {sorted(named - (moves_a_row | moves_nothing))}; "
        f"accounted for but never named: {sorted((moves_a_row | moves_nothing) - named)}"
    )
    for number, reason in data["prs_that_move_no_row_in_this_packet"].items():
        assert reason.strip(), f"terminal#{number}: listed as moving no row with no reason"


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
def test_every_row_names_producer_paths_recorded_present_per_the_checked_in_manifest(
    row_id: str,
) -> None:
    """Reads the manifest's own `producer_paths_on_master` booleans and nothing else.

    This is NOT live cross-repository verification. The manifest pins Terminal master
    `db69d072` and records what was found there once, by hand, at packet time; the
    `how_verified` field says how. If that repository drifts, this suite cannot see it.
    """
    data = _manifest()
    assert data["how_verified"].strip(), (
        "the manifest must say how its producer paths were checked, since the suite "
        "only re-reads the answer"
    )
    on_master = data["producer_paths_on_master"]
    paths = _manifest_rows()[row_id]["producer_paths"]
    assert paths, f"{row_id}: no producer path recorded"
    for path in paths:
        assert on_master.get(path) is True, (
            f"{row_id}: producer path {path!r} is not recorded as present on "
            f"Terminal master {data['terminal_master_sha'][:8]}"
        )


def test_no_producer_path_is_recorded_as_absent_per_the_checked_in_manifest() -> None:
    """The manifest is a record of what WAS found, not a wish list.

    Again a re-read of the checked-in booleans, not a live check of the Terminal tree.
    The pinned commit and the method are asserted here so that no reader can take a green
    run as evidence about the state of that repository today.
    """
    data = _manifest()
    assert _SHA_RE.match(data["terminal_master_sha"] or ""), (
        "the manifest must pin the Terminal master commit these booleans were read at"
    )
    assert data["how_verified"].strip(), "the manifest must record how they were read"
    for path, present in data["producer_paths_on_master"].items():
        assert present is True, (
            f"{path}: recorded as absent from Terminal master "
            f"{data['terminal_master_sha'][:8]}"
        )


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
def test_ledger_row_is_unique_and_matches_the_current_manifest_state(row_id: str) -> None:
    text = LEDGER.read_text(encoding="utf-8")
    assert text.count(f"\n{row_id},") + text.startswith(f"{row_id},") == 1, (
        f"{row_id}: expected exactly one ledger row"
    )
    ledger = _ledger_rows()[row_id]
    current = _current_manifest_rows()[row_id]
    assert ledger["capability_state_c2"] == current["capability_state_c2"], (
        f"{row_id}: ledger says {ledger['capability_state_c2']!r}, current manifest says "
        f"{current['capability_state_c2']!r}"
    )


@pytest.mark.parametrize("row_id", ROWS)
def test_current_manifest_quotes_the_ledger_acceptance_sentence_verbatim(row_id: str) -> None:
    assert _current_manifest_rows()[row_id]["acceptance_test"] == _ledger_rows()[row_id][
        "acceptance_test"
    ], f"{row_id}: the current manifest must judge the ledger's own acceptance sentence"


@pytest.mark.parametrize("row_id", ROWS)
def test_current_manifest_mirrors_load_bearing_closure_fields(row_id: str) -> None:
    """Later accepted evidence may supersede the 2026-09-09 packet without rewriting it."""
    ledger = _ledger_rows()[row_id]
    current = _current_manifest_rows()[row_id]
    for field in (
        "capability_state_c2",
        "acceptance_test",
        "real_producer",
        "missing_contract_or_proof",
        "next_bounded_child",
        "adjudication_notes",
    ):
        assert current[field] == ledger[field], (
            f"{row_id}: current manifest field {field!r} drifted from the canonical ledger"
        )
    if current["capability_state_c2"] == "BUILT_NOT_PROVEN":
        assert current["missing_contract_or_proof"].strip(), (
            f"{row_id}: BUILT_NOT_PROVEN must name the remaining proof or residual"
        )


@pytest.mark.parametrize("row_id", ROWS)
def test_historical_open_rows_keep_their_original_residual_receipt(row_id: str) -> None:
    """The historical packet stays auditable even when later waves close part of its gap."""
    row = _manifest_rows()[row_id]
    if row["disposition"] == "NOT_SATISFIED":
        assert row.get("residual"), f"{row_id}: historical open row lost its residual receipt"
        assert row["next_bounded_child"].strip(), (
            f"{row_id}: historical open row lost the child recorded by that packet"
        )


@pytest.mark.parametrize("row_id", ROWS)
def test_current_manifest_mirrors_the_ledger_next_bounded_child(row_id: str) -> None:
    """Current child ownership is a canonical fact; historical rows remain immutable evidence."""
    assert _current_manifest_rows()[row_id]["next_bounded_child"] == _ledger_rows()[row_id][
        "next_bounded_child"
    ], f"{row_id}: current manifest and ledger disagree about the next bounded child"


def test_the_event_object_invalidation_build_is_not_recommissioned() -> None:
    """#576 shipped invalidation; neither paired row may ask to build it again."""
    ledger = _ledger_rows()
    paid = ledger["MO-PAID-028"]["next_bounded_child"]
    delta = ledger["MO-DELTA-042"]["next_bounded_child"]
    assert "add the F08 §9 invalidation" not in paid
    assert "add the F08 §9 invalidation" not in delta
    assert "invalidation are already shipped" in delta
    assert "signed-in" in paid
    assert "signed-in" in delta


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


# The definitional sentence the records document must carry, verbatim once whitespace
# is collapsed. It is the whole content of BUILT_NOT_PROVEN: merged, migration applied,
# and nobody observed using it. A reader who only sees the state word must be able to
# find out here what would move the row again.
_BUILT_NOT_PROVEN_MEANING = "It does not mean anyone has used it."
_WHAT_WOULD_MOVE_IT = (
    "When two people have exercised one of these surfaces in production and that is "
    "recorded, the row can move again"
)


def _state_word_section() -> str:
    text = RECORDS_DOC.read_text(encoding="utf-8")
    _, _, rest = text.partition("## What the state words mean here")
    assert rest, "the records document has no section defining its state words"
    section, _, _ = rest.partition("\n## ")
    return " ".join(section.split())


def test_records_doc_states_what_built_not_proven_means() -> None:
    section = _state_word_section()
    assert "BUILT_NOT_PROVEN" in section, (
        "the state-word section must define BUILT_NOT_PROVEN, the word ten rows now carry"
    )
    assert _BUILT_NOT_PROVEN_MEANING in section, (
        "the section must say in one sentence that the word does not mean anyone has "
        f"used the capability; expected {_BUILT_NOT_PROVEN_MEANING!r}"
    )
    assert _WHAT_WOULD_MOVE_IT in section, (
        "the section must name the threshold that would move a row past "
        f"BUILT_NOT_PROVEN; expected {_WHAT_WOULD_MOVE_IT!r}"
    )

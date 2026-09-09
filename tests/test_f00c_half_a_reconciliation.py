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
import yaml

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

# The ONLY producer paths this packet may excuse from the on-disk check. They landed on
# origin/main in merges (#6928, #6929) that are not ancestors of this stacked head, so
# importing them here would breach the packet's named-files bound. Pinned in code, not
# read from the fixture, so the fixture cannot widen the exemption: the skip below is
# intersected with this set, and the fixture is asserted equal to it.
STACKED_HEAD_ABSENT_PRODUCER_PATHS = frozenset(
    {
        "engine/uk_policy_brain.py",
        "engine/market_ontology/exposure_map.py",
        "engine/market_ontology/__init__.py",
    }
)


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _manifest_rows() -> dict[str, dict]:
    return {row["id"]: row for row in _manifest()["rows"]}


def _ledger_rows() -> dict[str, dict]:
    with LEDGER.open(newline="", encoding="utf-8") as fh:
        return {row["id"]: row for row in csv.DictReader(fh)}


def _declared_absent() -> set[str]:
    """What the fixture claims is absent at this stacked head."""
    return set(_manifest().get("stacked_head_absent_producer_paths") or ())


def _stacked_absent() -> set[str]:
    """The exemption actually honoured — never wider than the pinned set."""
    return _declared_absent() & set(STACKED_HEAD_ABSENT_PRODUCER_PATHS)


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


def test_the_absent_producer_path_exemption_is_pinned_and_cannot_widen() -> None:
    """The escape hatch is a closed set of three paths, and only the seat may move it.

    Without this, `stacked_head_absent_producer_paths` is read from the same fixture the
    suite polices, so the list could grow to cover every producer path and
    `test_producer_paths_exist_on_disk` would assert nothing, silently.
    """
    declared = _declared_absent()
    widened = sorted(declared - set(STACKED_HEAD_ABSENT_PRODUCER_PATHS))
    assert not widened, (
        "the stacked-head exemption may not widen; these paths are not in the pinned "
        f"set and must exist on disk: {widened}"
    )
    assert declared == set(STACKED_HEAD_ABSENT_PRODUCER_PATHS), (
        "the fixture must declare exactly the pinned exemption, got "
        f"{sorted(declared)} != {sorted(STACKED_HEAD_ABSENT_PRODUCER_PATHS)}"
    )


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
    """Column order and row width are durable; a whole-file row count is not.

    This packet sits on unmerged stacked work, so a sibling records packet that adds a
    ledger row must not red this suite for a reason unrelated to the nine rows it exists
    to pin. What this packet owns is those nine rows, asserted by id below; the file may
    only grow, never shrink.
    """
    with LEDGER.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    assert tuple(rows[0]) == LEDGER_COLUMNS, "the ledger's column order moved"
    assert all(len(r) == len(LEDGER_COLUMNS) for r in rows), "a ledger row has the wrong width"
    assert len(rows) >= 131, (
        f"the ledger lost rows: {len(rows)} records incl. header, expected at least 131"
    )
    ids = [r[0] for r in rows[1:]]
    for row_id in ROWS:
        assert ids.count(row_id) == 1, (
            f"{row_id}: expected exactly one ledger row, found {ids.count(row_id)}"
        )
    ledger = _ledger_rows()
    for row_id in ROWS:
        row = ledger[row_id]
        assert row["capability_state_c2"] == "BUILT_NOT_PROVEN", (
            f"{row_id}: capability_state_c2 is {row['capability_state_c2']!r}"
        )
        assert row["state_delta"].strip(), f"{row_id}: state_delta was emptied"
        assert row["real_producer"].strip(), f"{row_id}: real_producer was emptied"
        assert row["next_bounded_child"] == "", (
            f"{row_id}: next_bounded_child should be empty, got "
            f"{row['next_bounded_child']!r}"
        )


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


def test_the_6957_collision_is_recorded_as_file_level_not_row_level() -> None:
    """macro#6957's live hunk is +1/-1 on MO-DELTA-008 only — it does not touch this row.

    The first cut of this packet read #6957's file list rather than its hunk and recorded
    a row-level collision on MO-PAID-004. That reading is withdrawn; the collision is real
    but file-level. Pinned on both surfaces so it cannot drift back.
    """
    cell = _ledger_rows()["MO-PAID-004"]["state_delta"]
    assert "#6957" in cell, "MO-PAID-004 must still flag the open packet on this file"
    assert "MO-DELTA-008" in cell, "the CAUTION must name the row #6957 actually edits"
    assert "edits this exact CSV row" not in cell, (
        "withdrawn claim: #6957 does not edit the MO-PAID-004 row"
    )
    assert "file-level" in cell, "the CAUTION must say the collision is file-level"
    doc = RECORDS_DOC.read_text(encoding="utf-8")
    assert "MO-DELTA-008" in doc and "file-level" in doc, (
        "the records document must carry the corrected #6957 hunk fact"
    )
    # Round-3 MAJOR: the body of that section withdrew the row-level reading, but
    # the section HEADING still restated it, so the guard above passed green over a
    # false sentence on the committed surface. The heading is now pinned too.
    assert "this row is also being edited by an open PR" not in doc, (
        "withdrawn claim: no heading or line in the records document may say #6957 "
        "edits the MO-PAID-004 row; the collision is file-level"
    )
    assert "a file-level collision with open #6957, not a row edit" in doc, (
        "the MO-PAID-004 caveat heading must state the file-level truth it withdrew to"
    )


def test_this_suite_is_not_waived() -> None:
    assert WAIVERS.exists(), f"missing waivers file: {WAIVERS}"
    text = WAIVERS.read_text(encoding="utf-8")
    assert "test_f00c_half_a_reconciliation" not in text, (
        "this suite must run; do not add it to config/unrun_test_waivers.yml"
    )


# ------------------------------------------ CI scope closure (round-3 MAJOR 2)

_LEGACY_JOBS = _ROOT / ".github" / "ci" / "legacy-jobs.yml"

# Every artifact THIS suite reads from disk and pins. `self-mod-fence` is the only
# merge-gate (`gate: code`) job that runs this suite (see the last `run:` step of
# its definition in .github/ci/legacy-jobs.yml); `engine-render-guards`
# (`gate: data`) also runs it, off the gate. So an edit touching ONLY one of these
# paths must be able to select the merge-gate job on its own — otherwise the pin
# fires post-merge on main instead of pre-merge on the PR. Round-3 MAJOR: the
# manifest fixture was read at line 23 and named in no job's `paths:`; `tests` is
# absent from LITERAL_DIRS in scripts/ci_scope_dependencies.py, so scope inference
# could not reach it either, and a fixture-only break would have merged green. Modelled on
# tests/test_b_rec3_wave_boundary_records.py's `_PINNED_RECORD_PATHS`. Declaring a
# path inference already covers costs nothing: infer_job_scopes() unions declared
# with inferred, so a declaration only ever widens a job's scope.
_PINNED_RECORD_PATHS = tuple(
    str(path.relative_to(_ROOT))
    for path in (
        Path(__file__).resolve(),
        LEDGER,
        RECORDS_DOC,
        MANIFEST,
    )
)


def _self_mod_fence_paths() -> set[str]:
    manifest = yaml.safe_load(_LEGACY_JOBS.read_text(encoding="utf-8"))
    return set(manifest["jobs"]["self-mod-fence"].get("paths") or ())


@pytest.mark.parametrize("record_path", _PINNED_RECORD_PATHS)
def test_self_mod_fence_paths_cover_every_artifact_this_suite_pins(
    record_path: str,
) -> None:
    """Every pinned artifact is declared on the merge-gate job's `paths:` list.

    Declaration ownership is split across this stack: this PR declares three of the
    four entries itself (this suite file, its manifest fixture and its records
    document) and inherits the fourth, the F00C ledger CSV, from the base branch
    `claude/mo-b-rec-b5-1-ledger-reconciliation` (#7003), so that one parameter
    passes on the parent packet's declaration rather than on one this PR owns.
    """
    declared = _self_mod_fence_paths()
    assert record_path in declared, (
        f"{record_path!r} is read by this suite, which self-mod-fence is the only "
        "merge-gate (`gate: code`) job to run — engine-render-guards (`gate: data`) "
        "also runs it, off the gate — but it is missing from self-mod-fence's "
        "`paths:` list in .github/ci/legacy-jobs.yml — an edit touching only this "
        "file would select no merge-gate job that runs the suite, so the pin would "
        "fire post-merge on main instead of pre-merge on a PR"
    )

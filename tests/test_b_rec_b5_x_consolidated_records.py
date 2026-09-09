"""Pin packet B-REC-B5-X: consolidated half-B records.

Five census packets ride one pull request because the F00C ledger CSV is a
single-appender resource. Every claim this suite checks is read from a
CHECKED-IN manifest — never by shelling to git or gh, and never by reading a
terminal/ tree this repository does not contain.

RED before the packet: the seven edited rows still carry their pre-packet
cells, the consolidated document and the F08 matrix do not exist, and the
two agentos records are absent.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]

MANIFEST = REPO / "tests/fixtures/b_rec_b5_x_consolidated_manifest.json"
LEDGER = REPO / (
    "research/market_intelligence_productization/"
    "MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv"
)
RECORDS_DOC = REPO / (
    "research/market_intelligence_productization/"
    "MARKET_ONTOLOGY_B_REC_B5_X_CONSOLIDATED_RECORDS_2026-09-09.md"
)
F08_MATRIX = REPO / "research/MARKET_ONTOLOGY_F08_METRIC_ADOPTION_MATRIX_2026-09-09.md"
F08_FREEZE = REPO / "research/MARKET_ONTOLOGY_F08_ARCHITECTURE_FREEZE_2026-09-05.md"
DEC_F08 = REPO / "agentos/decisions/DEC-F08-METRIC-ADOPTION-MATRIX-2026-09-09.md"
DEC_F13 = REPO / "agentos/decisions/DEC-F13-TIER-REFRESH-ACCEPTANCE-CONFLICT-2026-09-09.md"
DSC = REPO / (
    "agentos/discoveries/"
    "DSC-CENSUS-PACKET-29-F12-RULING-IS-NOT-IN-THE-CONSOLIDATION.md"
)
WAIVERS = REPO / "config/unrun_test_waivers.yml"

CAPABILITY_STATES = {
    "NOT_BUILT",
    "PARTIAL",
    "SPEC_ONLY",
    "BUILT_NOT_PROVEN",
    "PROVEN_LIVE",
}

SECTION_HEADINGS = (
    "## 1. F07 consensus-source verified negative",
    "## 2. Enterprise-deployment-planner rejection",
    "## 3. F09 rows after the merged coverage matrix",
    "## 4. F12 public-API refusal chain — recorded, not edited",
    "## 5. F08 metric adoption matrix",
    "## 6. What this packet deliberately did not do",
)

EDIT_TABLE_HEADING = "## Rows this packet edited"

F08_DEC_REQUIRED = (
    "key",
    "type",
    "status",
    "workstream",
    "question",
    "answer",
    "rationale",
    "alternatives",
    "evidence",
    "affects",
    "confidence",
    "reversibility",
    "decided_by",
    "decided_at",
)

DSC_REQUIRED = ("key", "claim", "falsifier", "so_what", "scope", "confidence")

FREEZE_SENTENCE = (
    "a builder may neither fork nor invent a formula before the matrix is ratified"
)

# The spec's BLOCKER 5 vocabulary. MO-DELTA-014 stays open, so none of these
# words may sit beside the row id in either document.
CLOSURE_WORDS = ("closed", "satisfied", "absorbed", "finished", "a closure")

# Column order of the F08 metric adoption matrix table.
MATRIX_COLUMNS = (
    "metric",
    "owning_module",
    "definition",
    "benchmark",
    "horizon",
    "annualization",
    "version",
    "may_not_be_used_for",
)


def _norm(s: str) -> str:
    s = (s or "").replace("`", "")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _edited() -> list[dict]:
    return _manifest()["edited"]


def _edited_ids() -> tuple[str, ...]:
    return tuple(row["id"] for row in _edited())


def _recorded() -> list[dict]:
    return _manifest()["recorded_not_edited"]


def _recorded_ids() -> tuple[str, ...]:
    return tuple(row["id"] for row in _recorded())


def _ledger() -> dict[str, dict]:
    with LEDGER.open(newline="", encoding="utf-8") as fh:
        return {row["id"]: row for row in csv.DictReader(fh)}


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    parts = text.split("---")
    assert len(parts) >= 3, f"{path}: expected YAML frontmatter between --- fences"
    data = yaml.safe_load(parts[1])
    assert isinstance(data, dict), f"{path}: frontmatter did not parse as a mapping"
    return data


def _matrix_rows(text: str) -> dict[str, list[str]]:
    """Parse the F08 matrix table into {first cell -> list of cells}.

    Row-anchored so an assertion about one metric cannot be satisfied by a
    different metric's row somewhere else in the file.
    """
    rows: dict[str, list[str]] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|") or not line.endswith("|"):
            continue
        cells = [_norm(c) for c in line.strip("|").split("|")]
        if len(cells) != len(MATRIX_COLUMNS):
            continue
        head = cells[0]
        if not head or head.lower() == "metric" or set(head) <= set("-: "):
            continue
        assert head not in rows, f"matrix lists metric {head!r} on two rows"
        rows[head] = cells
    return rows


def _matrix_row(text: str, metric: str) -> dict[str, str]:
    rows = _matrix_rows(text)
    assert metric in rows, (
        f"the F08 matrix has no table row whose first cell is {metric!r}; "
        f"rows present: {sorted(rows)}"
    )
    return dict(zip(MATRIX_COLUMNS, rows[metric]))


def _edit_table(text: str) -> str:
    start = text.find(EDIT_TABLE_HEADING)
    assert start >= 0, "consolidated document is missing the edit table heading"
    rest = text[start:]
    nxt = re.search(r"\n## ", rest[len(EDIT_TABLE_HEADING):])
    end = start + len(EDIT_TABLE_HEADING) + nxt.start() if nxt else len(text)
    return text[start:end]


# ------------------------------------------------------------ manifest shape


def test_manifest_exists_and_lists_seven_edited_rows_once_each() -> None:
    assert MANIFEST.exists(), f"missing consolidated-records manifest: {MANIFEST}"
    ids = [row["id"] for row in _edited()]
    assert len(ids) == len(set(ids)), "an edited row is listed twice in the manifest"
    assert set(ids) == {
        "MO-DELTA-017",
        "MO-PAID-035",
        "MO-PAID-037",
        "MO-DELTA-040",
        "MO-DELTA-029",
        "MO-PAID-067",
        "MO-PAID-057",
    }


def test_manifest_lists_eight_recorded_not_edited_rows() -> None:
    ids = [row["id"] for row in _recorded()]
    assert len(ids) == 8, f"expected 8 recorded-not-edited rows, got {len(ids)}"
    assert len(ids) == len(set(ids))
    assert set(ids) == {
        "MO-DELTA-036",
        "MO-DELTA-037",
        "MO-DELTA-038",
        "MO-DELTA-039",
        "MO-PAID-055",
        "MO-PAID-084",
        "MO-PAID-036",
        "MO-DELTA-014",
    }


def test_terminal_pin_discloses_that_macro_has_no_terminal_tree() -> None:
    pin = _manifest()["terminal_pin"]
    assert pin["repo"] == "terminal"
    assert pin["pr"] == 524
    assert pin["merge"].startswith("efcd98aa")
    assert len(pin["commit"]) == 40
    assert "invisible" in pin["disclosure"].lower() or "does not contain" in pin["disclosure"].lower() or "no terminal" in pin["disclosure"].lower()


# ------------------------------------------------------------ edited rows


@pytest.mark.parametrize("row_id", _edited_ids())
def test_each_edited_row_exists_once_and_matches_manifest_state(row_id: str) -> None:
    text = LEDGER.read_text(encoding="utf-8")
    count = text.count(f"\n{row_id},") + int(text.startswith(f"{row_id},"))
    assert count == 1, f"{row_id}: expected exactly one ledger row, found {count}"
    spec = next(r for r in _edited() if r["id"] == row_id)
    row = _ledger()[row_id]
    assert row["granular_disposition"] == spec["new_granular_disposition"], (
        f"{row_id}: granular_disposition={row['granular_disposition']!r}, "
        f"manifest wants {spec['new_granular_disposition']!r}"
    )
    assert row["capability_state_c2"] == spec["new_capability_state_c2"], (
        f"{row_id}: capability_state_c2={row['capability_state_c2']!r}, "
        f"manifest wants {spec['new_capability_state_c2']!r}"
    )
    delta = row["state_delta"]
    notes = row["adjudication_notes"]
    for needle in spec["state_delta_must_contain"]:
        assert needle in delta, f"{row_id}: state_delta missing {needle!r}"
    for needle in spec["adjudication_must_contain"]:
        assert needle in notes, f"{row_id}: adjudication_notes missing {needle!r}"


@pytest.mark.parametrize("row_id", ("MO-PAID-035", "MO-PAID-037"))
def test_docket_prefix_and_anchor_survive_on_035_and_037(row_id: str) -> None:
    row = _ledger()[row_id]
    assert row["next_bounded_child"].startswith("DOCKETED_TERMINAL_HALF_B;"), (
        f"{row_id}: next_bounded_child lost the #6997 docket prefix: "
        f"{row['next_bounded_child']!r}"
    )
    assert "MARKET_ONTOLOGY_HALF_B_RIGHTS_AND_UPSTREAM_GATE_DOCKET_2026-09-06.md#mo-paid-" in row["adjudication_notes"], (
        f"{row_id}: adjudication_notes lost the #6997 docket anchor"
    )


def test_mo_delta_040_keeps_the_post_tenancy_revisit_clause() -> None:
    child = _ledger()["MO-DELTA-040"]["next_bounded_child"]
    assert "post-F12-tenancy revisit clause" in child, (
        f"MO-DELTA-040: revisit clause missing from next_bounded_child={child!r}"
    )


def test_mo_paid_057_rewrites_only_next_bounded_child() -> None:
    spec = next(r for r in _edited() if r["id"] == "MO-PAID-057")
    row = _ledger()["MO-PAID-057"]
    assert row["next_bounded_child"] == spec["next_bounded_child_must_equal"], (
        f"MO-PAID-057: next_bounded_child={row['next_bounded_child']!r}"
    )
    assert row["state_delta"] == spec["state_delta_must_contain"][0]
    assert row["adjudication_notes"] == spec["adjudication_must_contain"][0]
    assert row["granular_disposition"] == "UPGRADE_EXISTING_OWNER"
    assert row["capability_state_c2"] == "PARTIAL"


@pytest.mark.parametrize("row_id", _edited_ids())
def test_next_bounded_child_matches_manifest_needles(row_id: str) -> None:
    spec = next(r for r in _edited() if r["id"] == row_id)
    child = _ledger()[row_id]["next_bounded_child"]
    if spec.get("next_bounded_child_must_equal"):
        assert child == spec["next_bounded_child_must_equal"], row_id
        return
    for needle in spec.get("next_bounded_child_must_contain") or []:
        assert needle in child, f"{row_id}: next_bounded_child missing {needle!r}"


# ------------------------------------------------------------ recorded not edited


@pytest.mark.parametrize("row_id", _recorded_ids())
def test_recorded_not_edited_rows_are_absent_from_the_edit_table(row_id: str) -> None:
    text = RECORDS_DOC.read_text(encoding="utf-8")
    table = _edit_table(text)
    assert row_id not in table, (
        f"{row_id}: appears in the edit table; this packet must not claim to have edited it"
    )
    spec = next(r for r in _recorded() if r["id"] == row_id)
    assert str(spec["owner_pr"]) in text, (
        f"{row_id}: owner_pr #{spec['owner_pr']} is not named in the consolidated document"
    )
    assert row_id in text, f"{row_id}: not named in the recorded-not-edited prose"


def test_mo_delta_014_is_not_described_as_closed() -> None:
    """BLOCKER 5. The row is open; no document here may say otherwise.

    Normalised through the module's own _norm(), which strips the backticks the
    documents wrap the row id in, and matched as a regex within one sentence on
    either side of the id, so `MO-DELTA-014` is absorbed is caught as readily as
    the bare form.
    """
    alternation = "|".join(re.escape(word) for word in CLOSURE_WORDS)
    gap = r"[^.!?]{0,90}"
    patterns = (
        re.compile(rf"mo-delta-014{gap}\b(?:{alternation})\b", re.IGNORECASE),
        re.compile(rf"\b(?:{alternation})\b{gap}mo-delta-014", re.IGNORECASE),
    )
    for path, label in (
        (RECORDS_DOC, "consolidated document"),
        (F08_MATRIX, "F08 matrix"),
    ):
        blob = _norm(path.read_text(encoding="utf-8"))
        for pattern in patterns:
            hit = pattern.search(blob)
            assert hit is None, (
                f"{label} places a closure word beside MO-DELTA-014, which is open: "
                f"{hit.group(0)!r}"
            )


# ------------------------------------------------------------ vocabulary


def test_blocked_rights_never_appears_in_capability_state_c2() -> None:
    for row_id, row in _ledger().items():
        assert row["capability_state_c2"] != "BLOCKED_RIGHTS", (
            f"{row_id}: BLOCKED_RIGHTS is a granular_disposition value, "
            "never a capability_state_c2 value"
        )


def test_fourteen_original_rows_use_the_closed_state_vocabulary() -> None:
    ids = list(_edited_ids()) + list(_recorded_ids())
    # 057 is extra (R9); the original fourteen are the six-plus-eight without 057,
    # plus 057 itself is still in the closed vocabulary.
    ledger = _ledger()
    for row_id in ids:
        state = ledger[row_id]["capability_state_c2"]
        assert state in CAPABILITY_STATES, (
            f"{row_id}: {state!r} is not in the closed capability_state_c2 vocabulary"
        )


def test_no_row_in_this_packet_claims_proven_live() -> None:
    for spec in _edited():
        assert spec["new_capability_state_c2"] != "PROVEN_LIVE", spec["id"]
    # Hard ban: do not claim any of the seven moved to PROVEN_LIVE.
    for row_id in _edited_ids():
        assert _ledger()[row_id]["capability_state_c2"] != "PROVEN_LIVE", row_id


# ------------------------------------------------------------ documents


def test_consolidated_document_exists_with_six_section_headings() -> None:
    assert RECORDS_DOC.exists(), f"missing consolidated records document: {RECORDS_DOC}"
    text = RECORDS_DOC.read_text(encoding="utf-8")
    assert len(text) > 4000, "consolidated document looks too small to be substantive"
    for heading in SECTION_HEADINGS:
        assert heading in text, f"missing section heading {heading!r}"
    assert "validated" not in text.lower(), "consolidated document uses the banned claim word validated"


def test_edit_table_names_exactly_the_seven_edited_rows() -> None:
    text = RECORDS_DOC.read_text(encoding="utf-8")
    table = _edit_table(text)
    for row_id in _edited_ids():
        assert row_id in table, f"{row_id}: missing from the edit table"
    for row_id in _recorded_ids():
        assert row_id not in table


def test_f08_matrix_document_exists_and_covers_every_manifest_metric() -> None:
    assert F08_MATRIX.exists(), f"missing F08 metric adoption matrix: {F08_MATRIX}"
    text = F08_MATRIX.read_text(encoding="utf-8")
    assert "decision_support_only" in text
    assert "engine/portfolio.py" in text and "HOUSE-only" in text
    assert "research-proposal-only" in text or "research proposal" in text.lower()
    for entry in _manifest()["f08_metrics"]:
        metric = entry["metric"]
        cells = _matrix_row(text, metric)
        if entry["owning_module"] == "NO-OWNER":
            assert cells["owning_module"] == "NO-OWNER", (
                f"{metric}: the owner cell on its own matrix row reads "
                f"{cells['owning_module']!r}, not the literal token NO-OWNER"
            )
            assert entry["may_not_be_used_for"], f"{metric}: empty may_not_be_used_for"
        else:
            assert cells["owning_module"] == _norm(entry["owning_module"]), (
                f"{metric}: the owner cell on its own matrix row reads "
                f"{cells['owning_module']!r}, manifest wants "
                f"{_norm(entry['owning_module'])!r}"
            )
            for attr in ("definition", "benchmark", "horizon", "annualization", "version"):
                assert entry[attr] and entry[attr] != "NO-OWNER", (
                    f"{metric}: owned metric missing {attr}"
                )
                assert cells[attr] == _norm(entry[attr]), (
                    f"{metric}: the {attr} cell on its own matrix row reads "
                    f"{cells[attr]!r}, manifest wants {_norm(entry[attr])!r}"
                )
    for name in ("Sharpe", "Sortino", "beta"):
        # Row-anchored: NO-OWNER must stand in every attribute cell of THIS
        # metric's own row, not merely somewhere else in the file.
        cells = _matrix_row(text, name)
        for column in MATRIX_COLUMNS[1:-1]:
            assert cells[column] == "NO-OWNER", (
                f"{name}: the {column} cell on its own matrix row reads "
                f"{cells[column]!r}, not NO-OWNER — an owner was invented for a "
                "metric the freeze leaves unowned"
            )
        assert cells["may_not_be_used_for"], f"{name}: empty may-not-be-used-for cell"
    assert "validated" not in text.lower()


def test_f08_architecture_freeze_still_carries_the_no_fork_sentence() -> None:
    assert F08_FREEZE.exists(), f"missing F08 freeze: {F08_FREEZE}"
    text = F08_FREEZE.read_text(encoding="utf-8")
    assert FREEZE_SENTENCE in text, (
        "F08 freeze lost the sentence forbidding a builder to fork or invent a formula"
    )


def test_f08_dec_frontmatter_round_trips_and_names_the_matrix() -> None:
    assert DEC_F08.exists(), f"missing F08 DEC: {DEC_F08}"
    fm = _frontmatter(DEC_F08)
    assert fm["key"] == "F08-METRIC-ADOPTION-MATRIX-2026-09-09"
    assert DEC_F08.stem == f"DEC-{fm['key']}"
    for field in F08_DEC_REQUIRED:
        assert field in fm and fm[field], f"F08 DEC missing required field {field}"
    alts = fm["alternatives"]
    assert isinstance(alts, list) and len(alts) >= 1
    for alt in alts:
        assert alt.get("option"), "alternatives entry missing option"
        assert alt.get("why_not"), "alternatives entry missing why_not"
    body = DEC_F08.read_text(encoding="utf-8")
    assert "MARKET_ONTOLOGY_F08_METRIC_ADOPTION_MATRIX_2026-09-09.md" in body


def test_f13_dec_records_the_tier_refresh_acceptance_conflict() -> None:
    assert DEC_F13.exists(), f"missing F13 DEC: {DEC_F13}"
    fm = _frontmatter(DEC_F13)
    assert fm["key"] == "F13-TIER-REFRESH-ACCEPTANCE-CONFLICT-2026-09-09"
    assert DEC_F13.stem == f"DEC-{fm['key']}"
    for field in ("key", "question", "answer", "rationale", "alternatives", "evidence"):
        assert field in fm and fm[field], f"F13 DEC missing {field}"
    body = DEC_F13.read_text(encoding="utf-8")
    assert "The tier-differentiated refresh in the ledger row is REFUSED." in body
    assert "MO-PAID-057" in body
    assert "#6919" in body


def test_discovery_frontmatter_carries_the_census_correction() -> None:
    assert DSC.exists(), f"missing discovery: {DSC}"
    fm = _frontmatter(DSC)
    assert fm["key"] == "CENSUS-PACKET-29-F12-RULING-IS-NOT-IN-THE-CONSOLIDATION"
    for field in DSC_REQUIRED:
        assert field in fm and fm[field], f"discovery missing required field {field}"
    assert "6925" in str(fm["claim"]) or "6925" in str(fm["falsifier"])
    assert "6997" in str(fm["claim"])


def test_this_packet_adds_no_waiver_row() -> None:
    if not WAIVERS.exists():
        return
    text = WAIVERS.read_text(encoding="utf-8")
    assert "test_b_rec_b5_x_consolidated_records" not in text

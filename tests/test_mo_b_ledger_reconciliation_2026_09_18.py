"""Single-writer regression for MarketOntology F00C convergence (2026-09-19).

This is the existing #7335 records test widened to cover the one canonical
80-row integration.  It intentionally does not create a second ledger/control
plane: the CSV remains the source of truth and this file only pins its accepted
state/closure boundaries.
"""

import csv
import hashlib
import json
from pathlib import Path

CSV_PATH = Path("research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv")
MANIFEST_PATH = Path("research/market_intelligence_productization/F00C_TERMINAL_WAVE_RECONCILIATION_MANIFEST_2026-09-09.json")
INTEGRATION_BASE_SHA = "5332d876e75837c158c6f42a2862734451bb7158"
OUTSIDE_UNION_SHA256 = "b2e30e3b42b932d62c0a2781a87c6a527bdce05ed9e9003171add0f36b3abb7d"
CAPABILITY_STATES = {"NOT_BUILT", "SPEC_ONLY", "PARTIAL", "BUILT_NOT_PROVEN", "PROVEN_LIVE"}

UNION_ROWS = set([
  "MO-DELTA-001",
  "MO-DELTA-002",
  "MO-DELTA-003",
  "MO-DELTA-004",
  "MO-DELTA-005",
  "MO-DELTA-006",
  "MO-DELTA-007",
  "MO-DELTA-008",
  "MO-DELTA-009",
  "MO-DELTA-010",
  "MO-DELTA-011",
  "MO-DELTA-012",
  "MO-DELTA-014",
  "MO-DELTA-015",
  "MO-DELTA-016",
  "MO-DELTA-017",
  "MO-DELTA-019",
  "MO-DELTA-021",
  "MO-DELTA-023",
  "MO-DELTA-026",
  "MO-DELTA-029",
  "MO-DELTA-031",
  "MO-DELTA-032",
  "MO-DELTA-033",
  "MO-DELTA-034",
  "MO-DELTA-035",
  "MO-DELTA-040",
  "MO-DELTA-042",
  "MO-PAID-001",
  "MO-PAID-002",
  "MO-PAID-003",
  "MO-PAID-004",
  "MO-PAID-005",
  "MO-PAID-006",
  "MO-PAID-007",
  "MO-PAID-008",
  "MO-PAID-010",
  "MO-PAID-012",
  "MO-PAID-013",
  "MO-PAID-014",
  "MO-PAID-015",
  "MO-PAID-016",
  "MO-PAID-017",
  "MO-PAID-019",
  "MO-PAID-020",
  "MO-PAID-021",
  "MO-PAID-023",
  "MO-PAID-025",
  "MO-PAID-027",
  "MO-PAID-028",
  "MO-PAID-032",
  "MO-PAID-034",
  "MO-PAID-035",
  "MO-PAID-036",
  "MO-PAID-037",
  "MO-PAID-039",
  "MO-PAID-046",
  "MO-PAID-047",
  "MO-PAID-051",
  "MO-PAID-053",
  "MO-PAID-054",
  "MO-PAID-057",
  "MO-PAID-058",
  "MO-PAID-059",
  "MO-PAID-060",
  "MO-PAID-064",
  "MO-PAID-067",
  "MO-PAID-069",
  "MO-PAID-070",
  "MO-PAID-073",
  "MO-PAID-074",
  "MO-PAID-075",
  "MO-PAID-076",
  "MO-PAID-077",
  "MO-PAID-078",
  "MO-PAID-082",
  "MO-PAID-083",
  "MO-PAID-085",
  "MO-PAID-086",
  "MO-PAID-088"
])
EXPECTED = {
  "MO-DELTA-008": [
    "UPGRADE_EXISTING_OWNER",
    "PARTIAL"
  ],
  "MO-DELTA-010": [
    "EXACT_EQUIVALENT",
    "PROVEN_LIVE"
  ],
  "MO-DELTA-012": [
    "UPGRADE_EXISTING_OWNER",
    "PARTIAL"
  ],
  "MO-PAID-001": [
    "UPGRADE_EXISTING_OWNER",
    "PARTIAL"
  ],
  "MO-PAID-002": [
    "UPGRADE_EXISTING_OWNER",
    "PARTIAL"
  ],
  "MO-PAID-003": [
    "UPGRADE_EXISTING_OWNER",
    "PARTIAL"
  ],
  "MO-PAID-004": [
    "UPGRADE_EXISTING_OWNER",
    "PARTIAL"
  ],
  "MO-PAID-005": [
    "UPGRADE_EXISTING_OWNER",
    "PARTIAL"
  ],
  "MO-PAID-025": [
    "NEW_BOUNDED_BUILD",
    "NOT_BUILT"
  ],
  "MO-DELTA-031": [
    "NEW_BOUNDED_BUILD",
    "PROVEN_LIVE"
  ],
  "MO-DELTA-032": [
    "NEW_BOUNDED_BUILD",
    "PROVEN_LIVE"
  ],
  "MO-PAID-006": [
    "UPGRADE_EXISTING_OWNER",
    "PARTIAL"
  ],
  "MO-PAID-007": [
    "UPGRADE_EXISTING_OWNER",
    "PROVEN_LIVE"
  ],
  "MO-PAID-008": [
    "NEW_BOUNDED_BUILD",
    "PARTIAL"
  ],
  "MO-PAID-023": [
    "UPGRADE_EXISTING_OWNER",
    "BUILT_NOT_PROVEN"
  ],
  "MO-PAID-034": [
    "UPGRADE_EXISTING_OWNER",
    "PROVEN_LIVE"
  ],
  "MO-DELTA-033": [
    "NEW_BOUNDED_BUILD",
    "SPEC_ONLY"
  ],
  "MO-DELTA-034": [
    "NEW_BOUNDED_BUILD",
    "BUILT_NOT_PROVEN"
  ],
  "MO-DELTA-035": [
    "UPGRADE_EXISTING_OWNER",
    "BUILT_NOT_PROVEN"
  ],
  "MO-PAID-010": [
    "UPGRADE_EXISTING_OWNER",
    "PROVEN_LIVE"
  ],
  "MO-PAID-012": [
    "UPGRADE_EXISTING_OWNER",
    "PARTIAL"
  ],
  "MO-PAID-013": [
    "UPGRADE_EXISTING_OWNER",
    "PARTIAL"
  ],
  "MO-PAID-014": [
    "UPGRADE_EXISTING_OWNER",
    "PARTIAL"
  ],
  "MO-PAID-015": [
    "UPGRADE_EXISTING_OWNER",
    "BUILT_NOT_PROVEN"
  ],
  "MO-PAID-070": [
    "NEW_BOUNDED_BUILD",
    "SPEC_ONLY"
  ],
  "MO-PAID-073": [
    "EXACT_EQUIVALENT",
    "PARTIAL"
  ],
  "MO-PAID-074": [
    "UPGRADE_EXISTING_OWNER",
    "PARTIAL"
  ],
  "MO-PAID-075": [
    "UPGRADE_EXISTING_OWNER",
    "BUILT_NOT_PROVEN"
  ],
  "MO-PAID-076": [
    "NEW_BOUNDED_BUILD",
    "NOT_BUILT"
  ],
  "MO-PAID-077": [
    "NEW_BOUNDED_BUILD",
    "PARTIAL"
  ],
  "MO-DELTA-004": [
    "PROJECTION_ONLY",
    "PARTIAL"
  ],
  "MO-DELTA-005": [
    "CONTEXT_ONLY",
    "SPEC_ONLY"
  ],
  "MO-DELTA-006": [
    "PROJECTION_ONLY",
    "PROVEN_LIVE"
  ],
  "MO-DELTA-009": [
    "PROJECTION_ONLY",
    "PARTIAL"
  ],
  "MO-PAID-016": [
    "UPGRADE_EXISTING_OWNER",
    "PARTIAL"
  ],
  "MO-DELTA-001": [
    "PROJECTION_ONLY",
    "PROVEN_LIVE"
  ],
  "MO-PAID-017": [
    "UPGRADE_EXISTING_OWNER",
    "PARTIAL"
  ],
  "MO-DELTA-002": [
    "NEW_BOUNDED_BUILD",
    "NOT_BUILT"
  ],
  "MO-PAID-020": [
    "UPGRADE_EXISTING_OWNER",
    "PROVEN_LIVE"
  ],
  "MO-PAID-021": [
    "UPGRADE_EXISTING_OWNER",
    "PROVEN_LIVE"
  ],
  "MO-DELTA-017": [
    "NEW_BOUNDED_BUILD",
    "NOT_BUILT"
  ],
  "MO-PAID-035": [
    "BLOCKED_RIGHTS",
    "NOT_BUILT"
  ],
  "MO-PAID-037": [
    "BLOCKED_RIGHTS",
    "NOT_BUILT"
  ],
  "MO-DELTA-003": [
    "CONTEXT_ONLY",
    "PARTIAL"
  ],
  "MO-DELTA-014": [
    "PROJECTION_ONLY",
    "BUILT_NOT_PROVEN"
  ],
  "MO-DELTA-042": [
    "PROJECTION_ONLY",
    "BUILT_NOT_PROVEN"
  ],
  "MO-PAID-027": [
    "UPGRADE_EXISTING_OWNER",
    "PARTIAL"
  ],
  "MO-PAID-028": [
    "PROJECTION_ONLY",
    "BUILT_NOT_PROVEN"
  ],
  "MO-PAID-036": [
    "PROJECTION_ONLY",
    "BUILT_NOT_PROVEN"
  ],
  "MO-PAID-085": [
    "UPGRADE_EXISTING_OWNER",
    "PARTIAL"
  ],
  "MO-DELTA-019": [
    "UPGRADE_EXISTING_OWNER",
    "PROVEN_LIVE"
  ],
  "MO-DELTA-021": [
    "NEW_BOUNDED_BUILD",
    "PARTIAL"
  ],
  "MO-DELTA-023": [
    "NEW_BOUNDED_BUILD",
    "BUILT_NOT_PROVEN"
  ],
  "MO-DELTA-026": [
    "PROJECTION_ONLY",
    "NOT_BUILT"
  ],
  "MO-DELTA-029": [
    "NEW_BOUNDED_BUILD",
    "PROVEN_LIVE"
  ],
  "MO-PAID-019": [
    "UPGRADE_EXISTING_OWNER",
    "PARTIAL"
  ],
  "MO-PAID-059": [
    "NEW_BOUNDED_BUILD",
    "PARTIAL"
  ],
  "MO-PAID-060": [
    "UPGRADE_EXISTING_OWNER",
    "PROVEN_LIVE"
  ],
  "MO-PAID-064": [
    "NEW_BOUNDED_BUILD",
    "BUILT_NOT_PROVEN"
  ],
  "MO-PAID-067": [
    "PROJECTION_ONLY",
    "PROVEN_LIVE"
  ],
  "MO-PAID-069": [
    "PROJECTION_ONLY",
    "NOT_BUILT"
  ],
  "MO-DELTA-015": [
    "CONTEXT_ONLY",
    "PARTIAL"
  ],
  "MO-DELTA-016": [
    "CONTEXT_ONLY",
    "BUILT_NOT_PROVEN"
  ],
  "MO-PAID-039": [
    "CONTEXT_ONLY",
    "BUILT_NOT_PROVEN"
  ],
  "MO-PAID-032": [
    "NEW_BOUNDED_BUILD",
    "PARTIAL"
  ],
  "MO-PAID-046": [
    "NEW_BOUNDED_BUILD",
    "BUILT_NOT_PROVEN"
  ],
  "MO-PAID-047": [
    "PROJECTION_ONLY",
    "BUILT_NOT_PROVEN"
  ],
  "MO-PAID-053": [
    "NEW_BOUNDED_BUILD",
    "BUILT_NOT_PROVEN"
  ],
  "MO-PAID-054": [
    "UPGRADE_EXISTING_OWNER",
    "PARTIAL"
  ],
  "MO-PAID-051": [
    "NEW_BOUNDED_BUILD",
    "BUILT_NOT_PROVEN"
  ],
  "MO-PAID-078": [
    "UPGRADE_EXISTING_OWNER",
    "PARTIAL"
  ],
  "MO-PAID-082": [
    "NEW_BOUNDED_BUILD",
    "BUILT_NOT_PROVEN"
  ],
  "MO-PAID-083": [
    "NEW_BOUNDED_BUILD",
    "BUILT_NOT_PROVEN"
  ],
  "MO-PAID-086": [
    "UPGRADE_EXISTING_OWNER",
    "BUILT_NOT_PROVEN"
  ],
  "MO-DELTA-007": [
    "PROJECTION_ONLY",
    "PARTIAL"
  ],
  "MO-DELTA-011": [
    "PROJECTION_ONLY",
    "PROVEN_LIVE"
  ],
  "MO-DELTA-040": [
    "REJECTED_BY_DESIGN",
    "NOT_BUILT"
  ],
  "MO-PAID-057": [
    "UPGRADE_EXISTING_OWNER",
    "PARTIAL"
  ],
  "MO-PAID-058": [
    "UPGRADE_EXISTING_OWNER",
    "BUILT_NOT_PROVEN"
  ],
  "MO-PAID-088": [
    "UPGRADE_EXISTING_OWNER",
    "PROVEN_LIVE"
  ]
}
SOURCE_HEADS = {
  "7011": "89a1be5fc111f703472820d47973ba6840b9ddea",
  "7014": "9c2950d2bcd16dc790b47d655d43842e5ef69d92",
  "7335": "074670d9789fc41b399f18ad5c35199afee12cc9",
  "7340": "89eea5595fc7fd1e96a8bf052f041437585d83fe",
  "7343": "a7b9f945e34c1de460874c47282370edefcfff37",
  "7348": "d26cfaa41f15d81679b05fa9faa624c045d6f298",
  "7349": "879ccef3c85f537955d177cb2ea1917437d1a7d8",
  "7353": "4b7f7aa2ccd993bd71ccc4a4815ab34a94f46c6b"
}


def _rows():
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {r["id"]: r for r in rows}


def _outside_digest():
    raw = CSV_PATH.read_bytes().decode("utf-8").splitlines()
    kept = []
    for line in raw[1:]:
        if not line:
            continue
        row_id = line.split(",", 1)[0]
        if row_id not in UNION_ROWS:
            kept.append(line)
    return hashlib.sha256("\n".join(kept).encode("utf-8")).hexdigest()


def test_row_shape_vocabulary_and_union_size():
    rows = _rows()
    assert len(rows) == 130
    assert len(UNION_ROWS) == 80
    assert set(rows) >= UNION_ROWS
    assert all(r["capability_state_c2"] in CAPABILITY_STATES for r in rows.values())
    assert all(r["capability_state_c2"] != "DONE" for r in rows.values())
    assert all(r["capability_state_c2"] != "BLOCKED_RIGHTS" for r in rows.values())


def test_all_80_integration_rows_pin_disposition_and_capability():
    rows = _rows()
    assert set(EXPECTED) == UNION_ROWS
    for row_id, (disp, cap) in EXPECTED.items():
        r = rows[row_id]
        assert r["granular_disposition"] == disp, (row_id, r["granular_disposition"], disp)
        assert r["capability_state_c2"] == cap, (row_id, r["capability_state_c2"], cap)


def test_other_50_rows_are_byte_identical_to_integration_baseline():
    assert _outside_digest() == OUTSIDE_UNION_SHA256


def test_sol_adjudicated_closure_fields_are_not_stale():
    r = _rows()

    uk = r["MO-PAID-023"]
    assert uk["capability_state_c2"] == "BUILT_NOT_PROVEN"
    assert "gate_off" in (uk["state_delta"] + uk["missing_contract_or_proof"])
    assert "#7351" in uk["missing_contract_or_proof"]

    eu = r["MO-PAID-034"]
    assert eu["capability_state_c2"] == "PROVEN_LIVE"
    assert "qbus/items.parquet" in eu["real_consumer"]
    assert "second event bus" in eu["next_bounded_child"]

    matrix = r["MO-DELTA-029"]
    assert matrix["capability_state_c2"] == "PROVEN_LIVE"
    assert "matrix acceptance" in matrix["missing_contract_or_proof"]
    assert "per-family" in matrix["next_bounded_child"]

    support = r["MO-PAID-058"]
    assert support["capability_state_c2"] == "BUILT_NOT_PROVEN"
    assert "signed-in PRO" in support["missing_contract_or_proof"]
    assert "second support" in support["next_bounded_child"]

    glossary = r["MO-DELTA-011"]
    assert glossary["capability_state_c2"] == "PROVEN_LIVE"
    assert "superseded by 2026-09-19 live proof" in glossary["state_delta"]
    assert glossary["missing_contract_or_proof"].startswith("none")

    risk = r["MO-DELTA-014"]
    assert risk["capability_state_c2"] == "BUILT_NOT_PROVEN"
    assert "#578" in (risk["state_delta"] + risk["real_producer"])
    assert "computed nowhere" not in risk["state_delta"]
    assert "liquidity belongs to MO-PAID-036" in risk["next_bounded_child"]

    thesis = r["MO-PAID-046"]
    assert "previous_version" in thesis["acceptance_test"]
    assert "amended_from" not in thesis["acceptance_test"]
    assert "Do not add or restore amended_from" in thesis["adjudication_notes"]

    alias = r["MO-DELTA-001"]
    assert alias["capability_state_c2"] == "PROVEN_LIVE"
    assert "out of sparse scope" not in alias["state_delta"]
    assert "NOT_SERVED" in alias["state_delta"]

    catalog = r["MO-DELTA-010"]
    assert catalog["capability_state_c2"] == "PROVEN_LIVE"
    assert "glossary" in catalog["real_consumer"].lower()
    assert catalog["missing_contract_or_proof"].startswith("none")
    assert "second indicators-catalog" in catalog["next_bounded_child"]

    sanctions = r["MO-DELTA-031"]
    assert sanctions["capability_state_c2"] == "PROVEN_LIVE"
    assert sanctions["missing_contract_or_proof"].startswith("none for the accepted")
    assert "NEW_BOUNDED_BUILD scoped to base map" not in sanctions["next_bounded_child"]

    lifecycle = r["MO-DELTA-032"]
    assert lifecycle["capability_state_c2"] == "PROVEN_LIVE"
    joined = " ".join(lifecycle[k] for k in ("state_delta", "missing_contract_or_proof", "next_bounded_child"))
    assert "SPEC_ONLY stands" not in joined
    assert "still unexecuted" not in joined
    assert "second tracker/store" in lifecycle["next_bounded_child"]

    liquidity = r["MO-PAID-036"]
    assert liquidity["capability_state_c2"] == "BUILT_NOT_PROVEN"
    assert "wider metric suite named by MO-DELTA-014 is not shipped" not in liquidity["adjudication_notes"]
    assert "liquidity thickness" in liquidity["missing_contract_or_proof"]

    projection = r["MO-PAID-067"]
    assert projection["capability_state_c2"] == "PROVEN_LIVE"
    assert "capital_policy_projection.py" in projection["real_producer"]
    assert "foresight_cascade not used" in projection["real_producer"]

    help_row = r["MO-PAID-088"]
    assert help_row["capability_state_c2"] == "PROVEN_LIVE"
    assert help_row["missing_contract_or_proof"].startswith("none")

    for row_id in ("MO-DELTA-019", "MO-PAID-060"):
        assert r[row_id]["capability_state_c2"] == "PROVEN_LIVE"
        assert "credit_window.py" in r[row_id]["real_producer"]

    briefs = r["MO-PAID-032"]
    assert briefs["capability_state_c2"] == "PARTIAL"
    assert "subscription intake only" in briefs["real_producer"]
    assert "cadence producer" in briefs["missing_contract_or_proof"]

    f07 = r["MO-DELTA-017"]
    assert f07["capability_state_c2"] == "NOT_BUILT"
    assert "consensus half" in f07["state_delta"]
    assert "BLOCKED_RIGHTS" in f07["state_delta"]
    assert "FIF half" in f07["state_delta"]

    for row_id in ("MO-PAID-007", "MO-PAID-020", "MO-PAID-021"):
        assert r[row_id]["capability_state_c2"] == "PROVEN_LIVE"

    theme_map = r["MO-DELTA-004"]
    assert theme_map["capability_state_c2"] == "PARTIAL"
    missing = theme_map["missing_contract_or_proof"].lower()
    assert "consumer surface" in missing
    assert "shock->theme->company" in missing
    assert "no product surface" in theme_map["real_consumer"].lower()

    research_mode = r["MO-PAID-031"]
    assert research_mode["capability_state_c2"] == "SPEC_ONLY"

    lifecycle_owner = r["MO-PAID-007"]
    assert lifecycle_owner["capability_state_c2"] == "PROVEN_LIVE"
    assert "still SPEC_ONLY" not in lifecycle_owner["next_bounded_child"]
    assert "MO-DELTA-032" in lifecycle_owner["next_bounded_child"]

    event_schema = r["MO-DELTA-042"]
    assert event_schema["capability_state_c2"] == "BUILT_NOT_PROVEN"
    assert "terminal#576" in event_schema["real_producer"]
    assert "EventImpactPanel" in event_schema["real_consumer"]
    assert "signed-in production" in event_schema["missing_contract_or_proof"]
    assert "add the F08" not in event_schema["next_bounded_child"]

    event_positions = r["MO-PAID-028"]
    assert event_positions["capability_state_c2"] == "BUILT_NOT_PROVEN"
    assert "EventImpactPanel" in event_positions["real_consumer"]
    assert "signed-in production" in event_positions["missing_contract_or_proof"]
    assert "mapping is already shipped" in event_positions["next_bounded_child"]

    rms = r["MO-PAID-053"]
    assert rms["capability_state_c2"] == "BUILT_NOT_PROVEN"
    assert "ThesisWorkspace" in rms["real_consumer"]
    assert "signed-in production" in rms["missing_contract_or_proof"]
    assert "not-yet-built Thesis identities" not in rms["missing_contract_or_proof"]

    tenancy = r["MO-PAID-051"]
    assert tenancy["capability_state_c2"] == "BUILT_NOT_PROVEN"
    assert "/api/teams" in tenancy["real_consumer"]
    assert "signed-in production" in tenancy["missing_contract_or_proof"]
    assert "entire multi-seat team/tenant model" not in tenancy["missing_contract_or_proof"]

    roles = r["MO-PAID-082"]
    assert roles["capability_state_c2"] == "BUILT_NOT_PROVEN"
    assert "members/route.ts" in roles["real_consumer"]
    assert "signed-in production" in roles["missing_contract_or_proof"]
    assert "role/permission model" not in roles["missing_contract_or_proof"]

    workspace_settings = r["MO-PAID-083"]
    assert workspace_settings["capability_state_c2"] == "BUILT_NOT_PROVEN"
    assert "terminal#584 merged dd7c6dec" in workspace_settings["real_producer"]
    assert "SectionTeam" in workspace_settings["real_consumer"]
    assert "signed-in production" in workspace_settings["missing_contract_or_proof"]
    assert "#584 OPEN" not in (workspace_settings["missing_contract_or_proof"] + workspace_settings["next_bounded_child"] + workspace_settings["adjudication_notes"])

    export = r["MO-PAID-086"]
    assert export["capability_state_c2"] == "BUILT_NOT_PROVEN"
    assert "SectionAccount" in export["real_consumer"]
    assert "/api/account/export" in export["real_consumer"]
    assert "signed-in production" in export["missing_contract_or_proof"]
    assert "no /export route" not in export["missing_contract_or_proof"]

    implication = r["MO-PAID-039"]
    assert implication["capability_state_c2"] == "BUILT_NOT_PROVEN"
    assert "admin.mastermind-x.com" in implication["real_consumer"]
    assert "Intelligence Hub" in implication["real_consumer"]
    assert "@never_site" in implication["missing_contract_or_proof"]
    assert "retarget/remove" in implication["next_bounded_child"]
    assert "single existing measurement builder" in implication["next_bounded_child"]
    assert "scripts.build_measurement" in implication["adjudication_notes"]
    assert "not a missing builder step" in implication["adjudication_notes"]


def test_manifest_names_the_single_writer_sources_and_union():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    receipt = data["single_writer_convergence_2026_09_19"]
    assert receipt["operation"] == "marketontology-f00c-single-writer-convergence-20260919-sol-001"
    assert receipt["integration_base_sha"] == INTEGRATION_BASE_SHA
    assert receipt["union_row_count"] == 80
    assert set(receipt["union_row_ids"]) == UNION_ROWS
    assert receipt["source_pr_heads"] == SOURCE_HEADS
    assert receipt["outside_union_sha256"] == OUTSIDE_UNION_SHA256
    assert receipt["csv_commit"] == "e6ea08107305a95b4eda41782c304206b1cb8439"

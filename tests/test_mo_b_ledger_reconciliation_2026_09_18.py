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
# Re-pinned 2026-10-02 by the single lawful F00C writer (CEO A seat ruling D7 over
# F00A_CENSUS_R1 @ main 32d22a9b; CEO B verifies, never writes). The only outside-union
# row D7 touched is MO-PAID-072 (restamped `state_delta`, state unchanged). Prior digest:
# a4fdb5812267ae203faa009ea97dd8c9da3e203c3676d8b4abd33fd95b6355ab.
# 2026-10-02 wave 2 (same writer, D15 as F01 owner): MO-PAID-001 PARTIAL->BUILT_NOT_PROVEN
# (the two-axis regime read is built but its only include is dead, dashboard.html.j2:15538);
# MO-PAID-073 and MO-PAID-057 restamped (state unchanged). All three are union rows, so the
# outside-union digest is unchanged; CEO B's F06-F13 census (#8264) confirmed 78/79 cells.
# 2026-10-02 wave 3 (same writer, D17 as F03 owner): MO-PAID-073 PARTIAL->PROVEN_LIVE (freshness = designed T+1 cadence);
# MO-PAID-077/008 carry served receipts (states unchanged); MO-PAID-006 child text corrected. All four are union rows,
# so the outside-union digest is unchanged.
# 2026-10-02 wave 5 (same writer, D21 as F01 owner): MO-PAID-001 BUILT_NOT_PROVEN->PROVEN_LIVE (render 36998130756 + served
# us_stocks.html == main with id=regime-read); MO-PAID-008 RETRACTS the 07:5xZ 'no pin layer' receipt (layer live since #7377, D26),
# MO-DELTA-009 (#6958 closed), MO-PAID-011 (natural run observed), MO-PAID-023 (#8267 merged) MO-PAID-006 (plane merged #8276) restamped, states
# unchanged. All are union rows, so the outside-union digest is unchanged.
# 2026-10-02 wave 6 (same writer, D27/D28 as F02 owner): MO-PAID-008 BUILT_NOT_PROVEN->PROVEN_LIVE (#8278 c88f7b288b36, 16 cells viewed,
# served == main) and MO-PAID-023 PARTIAL->PROVEN_LIVE (whitehouse-sentinel 37007365383 state=no_new + served policy_watch.html == main);
# MO-PAID-011 (DEC §6 proof satisfied by #8280, D29) and MO-PAID-017 (#8265 merged 36d83f1330ff, D30) restamped, states unchanged.
# All four are union rows, so the outside-union digest is unchanged.
# 2026-10-02 wave 7 (same writer): MO-PAID-017 restamped PRODUCTION_PROOF (D49, served news.html == main),
# MO-PAID-011 (O26 minors merged #8283 + receipt #8289, D36/D47) and MO-PAID-008 (O21 family landed, D46/D48)
# restamped — states unchanged, all three are union rows, outside-union digest unchanged.
# Re-pinned 2026-10-04 by the same single writer (CEO A ruling D87 over CEO B 5978166980,
# A-verified on terminal #549 / the 0018 DDL receipt / live routes): the only outside-union rows
# touched are MO-PAID-056 and MO-DELTA-038 (NOT_BUILT -> BUILT_NOT_PROVEN). Prior digest:
# 3b8a93ce1ee08f64b3536df5a95e18861fc14fba4087cb436fd38c559a1df2a8.
# Re-pinned again 2026-10-04 (same writer, ruling D88 over CEO B 5978248217, A-verified on terminal
# #581/#548/#555/#526/#588/#550/#557 + live 401 probes): outside-union rows MO-PAID-055 and
# MO-PAID-084 NOT_BUILT -> BUILT_NOT_PROVEN, MO-PAID-052 NOT_BUILT -> PARTIAL, MO-DELTA-039 and
# MO-PAID-081 notes only. Prior digest: 83e3ab7a6270691b87a87f68b6ba3838f8cb8e97dcc0d3855a6b4ff6d1bd7951.
OUTSIDE_UNION_SHA256 = "a5f263439ac32778504c887db876ad5391961eb86ec41de533e81628424ba3ea"
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
  "MO-PAID-011",
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
    "PROVEN_LIVE"
  ],  # D21 2026-10-02: BUILT_NOT_PROVEN->PROVEN_LIVE (render + served proof)
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
    "PROVEN_LIVE"
  ],  # D7 2026-10-02: PARTIAL->PROVEN_LIVE
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
    "PROVEN_LIVE"
  ],
  "MO-PAID-007": [
    "UPGRADE_EXISTING_OWNER",
    "PROVEN_LIVE"
  ],
  "MO-PAID-008": [
    "NEW_BOUNDED_BUILD",
    "PROVEN_LIVE"
  ],  # D27 2026-10-02: BUILT_NOT_PROVEN->PROVEN_LIVE (#8278 c88f7b288b36, 16 cells viewed); D7: PARTIAL->BUILT_NOT_PROVEN
  "MO-PAID-023": [
    "UPGRADE_EXISTING_OWNER",
    "PROVEN_LIVE"
  ],  # D28 2026-10-02: PARTIAL->PROVEN_LIVE (sentinel 37007365383 + served no_new); D7: PROVEN_LIVE->PARTIAL
  "MO-PAID-034": [
    "UPGRADE_EXISTING_OWNER",
    "PROVEN_LIVE"
  ],
  "MO-DELTA-033": [
    "NEW_BOUNDED_BUILD",
    "PARTIAL"
  ],  # D7 2026-10-02: SPEC_ONLY->PARTIAL
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
    "PROVEN_LIVE"
  ],
  "MO-PAID-014": [
    "UPGRADE_EXISTING_OWNER",
    "PARTIAL"
  ],
  "MO-PAID-015": [
    "UPGRADE_EXISTING_OWNER",
    "BUILT_NOT_PROVEN"
  ],
  "MO-PAID-011": [
    "PROJECTION_ONLY",
    "PARTIAL"
  ],
  "MO-PAID-070": [
    "NEW_BOUNDED_BUILD",
    "PARTIAL"
  ],  # D7 2026-10-02: SPEC_ONLY->PARTIAL
  "MO-PAID-073": [
    "EXACT_EQUIVALENT",
    "PROVEN_LIVE"
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
    "BUILT_NOT_PROVEN"
  ],  # D7 2026-10-02: PARTIAL->BUILT_NOT_PROVEN
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
    "PROVEN_LIVE"
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
    "PROVEN_LIVE"
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
    "BUILT_NOT_PROVEN"
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
    assert len(UNION_ROWS) == 81
    assert set(rows) >= UNION_ROWS
    assert all(r["capability_state_c2"] in CAPABILITY_STATES for r in rows.values())
    assert all(r["capability_state_c2"] != "DONE" for r in rows.values())
    assert all(r["capability_state_c2"] != "BLOCKED_RIGHTS" for r in rows.values())


def test_all_81_integration_rows_pin_disposition_and_capability():
    rows = _rows()
    assert set(EXPECTED) == UNION_ROWS
    for row_id, (disp, cap) in EXPECTED.items():
        r = rows[row_id]
        assert r["granular_disposition"] == disp, (row_id, r["granular_disposition"], disp)
        assert r["capability_state_c2"] == cap, (row_id, r["capability_state_c2"], cap)


def test_other_49_rows_are_byte_identical_to_integration_baseline():
    assert _outside_digest() == OUTSIDE_UNION_SHA256


def test_sol_adjudicated_closure_fields_are_not_stale():
    r = _rows()

    uk = r["MO-PAID-023"]
    # D7 (2026-10-02): PROVEN_LIVE->PARTIAL — the served policy_watch.html read
    # model_unavailable (MO-PAID-023_UK_DIAG_R1: placement fault + latent fallback defect).
    # D28 (2026-10-02): PARTIAL->PROVEN_LIVE after the #8267 cure — sentinel run 37007365383
    # (state=no_new) and the served page == main with data-uk-state="no_new". Sol's #7351
    # closure receipt stays pinned below.
    assert uk["capability_state_c2"] == "PROVEN_LIVE"
    assert "no_new" in (uk["state_delta"] + uk["missing_contract_or_proof"])
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
    assert "NOT_BUILT" not in glossary["state_delta"]
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
    # W12 D89 (2026-10-04) aligned the state word to BUILT_NOT_PROVEN on the same facts Sol ruled
    # in W8 (implementation present / activation + natural delivery proof missing); the PARTIAL pin
    # below was D63's own word, superseded — the gap/activation assertions that follow are unchanged.
    assert briefs["capability_state_c2"] == "BUILT_NOT_PROVEN"
    assert "subscription intake only" in briefs["real_producer"]
    assert "cadence producer" in briefs["missing_contract_or_proof"]
    # W8 (2026-10-03, D63): the producer exists but is DORMANT in production; the gap is
    # activation authority + one natural delivery proof, never BUILD_NEW.
    assert "DORMANT" in briefs["missing_contract_or_proof"]
    assert "RECURRING_BRIEFS_ENABLE" in briefs["missing_contract_or_proof"]
    assert "build_recurring_briefs.py" in briefs["real_producer"]
    assert briefs["next_bounded_child"].startswith("ACTIVATION, not BUILD_NEW")
    # W11 (D83): the 2026-10-03 natural weekly run was read once and was DORMANT; state unchanged.
    assert "2026-10-03 CEO A D83" in briefs["adjudication_notes"]
    assert "37141524333" in briefs["adjudication_notes"]
    assert "DORMANT (RECURRING_BRIEFS_ENABLE unset)" in briefs["adjudication_notes"]

    # W8 D61/D62/D64 (Sol 5966652470 rows 1-4): stale NOT_BUILT / "still open" premises removed.
    screener = r["MO-DELTA-002"]
    assert screener["capability_state_c2"] == "PROVEN_LIVE"
    assert "research_screener.py" in screener["real_producer"]
    assert "never a trade ranker" in screener["acceptance_test"]
    for row_id in ("MO-DELTA-018", "MO-PAID-059"):
        assert r[row_id]["capability_state_c2"] == "PROVEN_LIVE"
        assert "stocks/AAPL.html" in r[row_id]["real_consumer"]
        assert "SEPARATE capability" in r[row_id]["missing_contract_or_proof"]
    thesis = r["MO-PAID-054"]
    assert thesis["capability_state_c2"] == "PARTIAL"
    assert "#577 is MERGED" in thesis["state_delta"]
    assert "#577 OPEN" not in thesis["missing_contract_or_proof"]
    # W12 D86 (CEO B 5978004918 / 5978053351; A re-verified 2026-10-04): cadence receipts + MO-DELTA-021 reason correction.
    assert "2026-10-04 CEO A D86" in r["MO-PAID-059"]["adjudication_notes"]
    assert "debt-maturity-drip.yml" in r["MO-PAID-059"]["adjudication_notes"]
    assert "natural cadence READ (D86)" in screener["missing_contract_or_proof"]
    assert "has not been read by A" not in screener["missing_contract_or_proof"]
    assert "#7100" in thesis["next_bounded_child"]
    headroom = r["MO-DELTA-021"]
    assert headroom["capability_state_c2"] == "PARTIAL"
    assert "PAGE BUILDER NOT WIRED" in headroom["state_delta"]
    assert "both CLOSED unmerged" in headroom["state_delta"]
    # W12 D87 (CEO B 5978166980): F12 outbound webhooks built in terminal #549, not proven.
    for rid in ("MO-PAID-056", "MO-DELTA-038"):
        assert r[rid]["capability_state_c2"] == "BUILT_NOT_PROVEN", rid
        assert "#549" in r[rid]["real_producer"], rid
    assert "worker cron" in r["MO-PAID-056"]["missing_contract_or_proof"]
    assert "#582" in r["MO-PAID-056"]["missing_contract_or_proof"]
    # W12 D88 (CEO B 5978248217): public API v1 + api keys (terminal #581) built, not proven; sharing half-built.
    for rid in ("MO-PAID-055", "MO-PAID-084"):
        assert r[rid]["capability_state_c2"] == "BUILT_NOT_PROVEN", rid
        assert "#581" in r[rid]["state_delta"], rid
    assert "failed_readback" in r["MO-PAID-084"]["real_producer"]
    sharing = r["MO-PAID-052"]
    assert sharing["capability_state_c2"] == "PARTIAL"
    assert "#548" in sharing["state_delta"] and "#555" in sharing["state_delta"]
    assert r["MO-DELTA-039"]["capability_state_c2"] == "NOT_BUILT"

    # W12 D89 (CEO B 5978485628 items 3-6): MO-PAID-032's state word aligned to BUILT_NOT_PROVEN on
    # unchanged facts (Sol 5966291701/5966652470: 'implementation present / activation + natural
    # delivery proof missing', state word never named); F11/F08 evidence widened on union rows only,
    # so OUTSIDE_UNION_SHA256 is unchanged by this ruling.
    briefs = r["MO-PAID-032"]
    assert briefs["capability_state_c2"] == "BUILT_NOT_PROVEN"
    assert "D89" in briefs["state_delta"] and "PARTIAL -> BUILT_NOT_PROVEN" in briefs["state_delta"]
    assert "RECURRING_BRIEFS_ENABLE" in briefs["missing_contract_or_proof"]
    assert "Do NOT build another producer" in briefs["next_bounded_child"]
    for rid in ("MO-PAID-046", "MO-PAID-053"):
        assert r[rid]["capability_state_c2"] == "BUILT_NOT_PROVEN", rid
        assert "#744" in r[rid]["adjudication_notes"], rid
    assert r["MO-PAID-047"]["capability_state_c2"] == "BUILT_NOT_PROVEN"
    assert "#762" in r["MO-PAID-047"]["adjudication_notes"]
    assert r["MO-PAID-054"]["capability_state_c2"] == "PARTIAL"
    assert "#798" in r["MO-PAID-054"]["adjudication_notes"]
    assert "#513" in r["MO-PAID-027"]["adjudication_notes"]
    assert "#586" in r["MO-DELTA-003"]["adjudication_notes"]
    for rid in ("MO-DELTA-003", "MO-PAID-027", "MO-PAID-085"):
        assert r[rid]["capability_state_c2"] == "PARTIAL", rid

    # W8b D66-D71 (CEO B 5966674775; Sol 5966690034/5966717632/5966734154/5966757712/5966757713/5966776979/5966790439).
    covenant = r["MO-PAID-062"]
    assert covenant["capability_state_c2"] == "BUILT_NOT_PROVEN"
    assert "covenant_terms.py" in covenant["real_producer"]
    assert "observations 0" in covenant["state_delta"]
    assert "never a second covenant-text producer" in covenant["next_bounded_child"]
    scenario = r["MO-PAID-026"]
    assert scenario["capability_state_c2"] == "PROVEN_LIVE"
    assert "valuation_scenario.py" in scenario["real_producer"]
    assert "Cautious $98.23 / Base $140.57 / Upbeat $188.43" in scenario["state_delta"]
    assert "MO-PAID-022/035" in scenario["missing_contract_or_proof"]
    analog = r["MO-PAID-045"]
    assert analog["capability_state_c2"] == "PARTIAL"
    assert "analog_pit.py" in analog["real_producer"]
    assert analog["next_bounded_child"].startswith("WAITING_DEPENDENCY")
    assert "#7755" in r["MO-PAID-039"]["real_consumer"]
    assert r["MO-PAID-039"]["missing_contract_or_proof"].startswith("PROOF-ONLY")
    accuracy = r["MO-DELTA-007"]
    assert accuracy["capability_state_c2"] == "PARTIAL"
    assert "#554 7e15e50" in accuracy["state_delta"]
    assert accuracy["missing_contract_or_proof"].startswith("ADVANCEMENT PATH + REAL-USER PROOF")
    constructor = r["MO-DELTA-003"]
    assert constructor["capability_state_c2"] == "PARTIAL"
    assert "0023_portfolio_targets.sql" in constructor["real_producer"]
    assert constructor["missing_contract_or_proof"].startswith("ROLE dimension only")

    # W9 stage 1 D73-D74 (O32 natural-run publication proof; Sol 5966828357 scheduler owner).
    am_edition = r["MO-PAID-011"]
    assert am_edition["capability_state_c2"] == "PARTIAL"
    assert am_edition["state_delta"].startswith("UPDATED 2026-10-03 D73")
    assert "96db8a19f9f5" in am_edition["state_delta"]
    assert "NOT a weekday premarket producer-build proof" in am_edition["state_delta"]
    assert "natural-run PUBLICATION proof READ 2026-10-03 08:12:01Z" in am_edition["next_bounded_child"]
    assert "natural-run live proof owed" not in am_edition["next_bounded_child"]
    accuracy_sched = r["MO-DELTA-007"]
    assert accuracy_sched["capability_state_c2"] == "PARTIAL"
    assert "REUSE the existing `ops/terminal-data` nightly" in accuracy_sched["next_bounded_child"]
    assert "never a second cron" in accuracy_sched["next_bounded_child"]
    assert "Build owner = CEO B (F13" in accuracy_sched["next_bounded_child"]
    # W11 (D84): F13 receipts from CEO B — wiring merged live, hydration fix merged, deploy owned by Terminal #793; still PARTIAL.
    assert "2026-10-03 CEO A D84" in accuracy_sched["adjudication_notes"]
    assert "#790" in accuracy_sched["adjudication_notes"]
    assert "#793" in accuracy_sched["adjudication_notes"]

    # W9 stage 2 D76-D77 (served .com proofs after render 37105009906).
    dossier = r["MO-PAID-006"]
    assert dossier["capability_state_c2"] == "PROVEN_LIVE"
    assert dossier["state_delta"].startswith("PARTIAL->PROVEN_LIVE 2026-10-03 (CEO A D76")
    assert "served_proof_8300.sh (rc=0)" in dossier["state_delta"]
    assert dossier["next_bounded_child"].startswith("NONE for the page")
    # W10 (D79): the finalize-only guard is recorded on the row; the receipt itself is unchanged.
    assert "2026-10-03 CEO A D79: evidence tool hardened" in dossier["adjudication_notes"]
    assert "refuse (rc 2, no write)" in dossier["adjudication_notes"]
    sanctions = r["MO-PAID-008"]
    assert sanctions["capability_state_c2"] == "PROVEN_LIVE"
    assert sanctions["state_delta"].startswith("PRODUCTION_PROOF 2026-10-03 (CEO A D77)")
    assert "stroke-dasharray:none" in sanctions["state_delta"]
    catalyst = r["MO-PAID-077"]
    assert catalyst["capability_state_c2"] == "BUILT_NOT_PROVEN"
    assert catalyst["next_bounded_child"].startswith("W3-1b consumer ruling NOT RIPE 2026-10-03")
    assert "session_date 2026-09-25" in catalyst["next_bounded_child"]

    f07 = r["MO-DELTA-017"]
    assert f07["capability_state_c2"] == "NOT_BUILT"
    assert "consensus half" in f07["state_delta"]
    assert "BLOCKED_RIGHTS" in f07["state_delta"]
    assert "FIF half" in f07["state_delta"]

    for row_id in ("MO-PAID-007", "MO-PAID-020", "MO-PAID-021"):
        assert r[row_id]["capability_state_c2"] == "PROVEN_LIVE"

    theme_map = r["MO-DELTA-004"]
    assert theme_map["capability_state_c2"] == "PARTIAL"
    assert "no product surface" in theme_map["missing_contract_or_proof"].lower()

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
    assert "templates/intelligence_hub.html.j2" in implication["real_consumer"]
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
    # MO-PAID-011 was moved INTO the union by the A seat in 2026-09-24 pass B;
    # the 2026-09-19 Sol convergence receipt freezes the pre-pass-B 80-row union
    # (historical block — per spec, "never edit older blocks" in the manifest).
    historical_union_ids = set(receipt["union_row_ids"])
    assert historical_union_ids == UNION_ROWS - {"MO-PAID-011"}
    assert receipt["union_row_count"] == 80  # pre-pass-B
    # The historical receipt's outside_union_sha256 was computed over the
    # pre-pass-B outside set (CSV line `MO-PAID-011,...` excluded by spec ruling).
    HISTORICAL_OUTSIDE_UNION_SHA256 = "b2e30e3b42b932d62c0a2781a87c6a527bdce05ed9e9003171add0f36b3abb7d"
    assert receipt["outside_union_sha256"] == HISTORICAL_OUTSIDE_UNION_SHA256
    assert receipt["source_pr_heads"] == SOURCE_HEADS
    assert receipt["csv_commit"] == "e6ea08107305a95b4eda41782c304206b1cb8439"

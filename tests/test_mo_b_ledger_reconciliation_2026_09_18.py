"""
test_mo_b_ledger_reconciliation_2026_09_18

Pin test: RED against origin/main CSV, GREEN after this PR.
Run against HEAD (workspace CSV) to verify post-state.
Run against git show origin/main:<csv> to confirm RED on main.

Acceptance gate:
  python3 -m pytest tests/test_mo_b_ledger_reconciliation_2026_09_18.py -q -p no:cacheprovider
"""

import csv
import os
import pytest

CSV_PATH = os.environ.get(
    "CSV_PATH",
    "research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv",
)
ORIGIN_MAIN_SHA = "0dbc87292d2728e891c4a72288ff5f58f02149fe"


def _read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _row_by_id(rows, id_):
    for r in rows:
        if r["id"] == id_:
            return r
    raise KeyError(id_)


# ---------------------------------------------------------------------------
# F07 — #7014
# ---------------------------------------------------------------------------

def test_mo_paid_035_BLOCKED_RIGHTS():
    """MO-PAID-035 granular_disposition -> BLOCKED_RIGHTS per #7014."""
    rows = _read_csv(CSV_PATH)
    r = _row_by_id(rows, "MO-PAID-035")
    assert r["granular_disposition"] == "BLOCKED_RIGHTS", (
        f"expected BLOCKED_RIGHTS, got {r['granular_disposition']}"
    )
    assert r["capability_state_c2"] == "NOT_BUILT"
    assert "BLOCKED_RIGHTS on a verified negative" in r["adjudication_notes"]
    assert "macro#6905" in r["adjudication_notes"]


def test_mo_paid_037_BLOCKED_RIGHTS():
    """MO-PAID-037 granular_disposition -> BLOCKED_RIGHTS per #7014."""
    rows = _read_csv(CSV_PATH)
    r = _row_by_id(rows, "MO-PAID-037")
    assert r["granular_disposition"] == "BLOCKED_RIGHTS"
    assert r["capability_state_c2"] == "NOT_BUILT"
    assert "inherits MO-PAID-035 BLOCKED_RIGHTS" in r["adjudication_notes"]


def test_mo_delta_040_text_unchanged():
    """MO-DELTA-040: disposition/capability unchanged REJECTED_BY_DESIGN/NOT_BUILT per #7014; next_bounded_child has measured state."""
    rows = _read_csv(CSV_PATH)
    r = _row_by_id(rows, "MO-DELTA-040")
    assert r["granular_disposition"] == "REJECTED_BY_DESIGN"
    assert r["capability_state_c2"] == "NOT_BUILT"
    # next_bounded_child must contain measured #6905/#6925 states per #7014 correction
    nbc = r["next_bounded_child"]
    assert "#6905 MERGED" in nbc, f"expected #6905 MERGED in next_bounded_child, got: {nbc[:80]}"
    assert "#6925 CLOSED" in nbc, f"expected #6925 CLOSED in next_bounded_child, got: {nbc[:80]}"


def test_mo_paid_057_next_bounded_child():
    """MO-PAID-057: next_bounded_child updated with #6905/#6925 measured states per #7014 correction."""
    rows = _read_csv(CSV_PATH)
    r = _row_by_id(rows, "MO-PAID-057")
    # disposition and capability unchanged
    assert r["granular_disposition"] == "UPGRADE_EXISTING_OWNER"
    assert r["capability_state_c2"] == "PARTIAL"
    # next_bounded_child must contain measured #6905/#6925 states per #7014 correction
    nbc = r["next_bounded_child"]
    assert "#6905 MERGED" in nbc, f"expected #6905 MERGED in next_bounded_child, got: {nbc[:80]}"
    assert "#6925 CLOSED" in nbc, f"expected #6925 CLOSED in next_bounded_child, got: {nbc[:80]}"


# ---------------------------------------------------------------------------
# F06 — #7137
# ---------------------------------------------------------------------------

def test_mo_paid_020_BUILT_NOT_PROVEN():
    """MO-PAID-020 capability -> BUILT_NOT_PROVEN per #7137; cites #7122 (OPEN/draft)."""
    rows = _read_csv(CSV_PATH)
    r = _row_by_id(rows, "MO-PAID-020")
    assert r["capability_state_c2"] == "BUILT_NOT_PROVEN", (
        f"expected BUILT_NOT_PROVEN, got {r['capability_state_c2']}"
    )
    assert "9c5445b9" in r["next_bounded_child"], "expected #7122 head in next_bounded_child"


def test_mo_paid_021_BUILT_NOT_PROVEN():
    """MO-PAID-021 capability -> BUILT_NOT_PROVEN per #7137."""
    rows = _read_csv(CSV_PATH)
    r = _row_by_id(rows, "MO-PAID-021")
    assert r["capability_state_c2"] == "BUILT_NOT_PROVEN"


def test_mo_delta_002_cites_7122():
    """MO-DELTA-002 cites #7122 (OPEN/draft) in state_delta per #7137."""
    rows = _read_csv(CSV_PATH)
    r = _row_by_id(rows, "MO-DELTA-002")
    assert "9c5445b9" in r["state_delta"], "expected #7122 head citation in state_delta"
    assert r["capability_state_c2"] == "NOT_BUILT"


# ---------------------------------------------------------------------------
# F08 — #7138
# ---------------------------------------------------------------------------

def test_mo_delta_003_PARTIAL():
    """MO-DELTA-003 capability_state_c2 -> PARTIAL per #7138 §LEDGER_MOVES #7 (role half absent)."""
    rows = _read_csv(CSV_PATH)
    r = _row_by_id(rows, "MO-DELTA-003")
    assert r["capability_state_c2"] == "PARTIAL", (
        f"expected PARTIAL, got {r['capability_state_c2']}"
    )
    assert r["granular_disposition"] == "CONTEXT_ONLY"


def test_mo_delta_042_retains_invalidation_token():
    """MO-DELTA-042 next_bounded_child retains literal token 'invalidation' per #7138."""
    rows = _read_csv(CSV_PATH)
    r = _row_by_id(rows, "MO-DELTA-042")
    assert "invalidation" in r["next_bounded_child"], (
        "literal token 'invalidation' must be retained in next_bounded_child"
    )


def test_mo_paid_027_refreshed_6906_merged():
    """MO-PAID-027 state_delta notes #6906 MERGED; stays PARTIAL per #7138."""
    rows = _read_csv(CSV_PATH)
    r = _row_by_id(rows, "MO-PAID-027")
    assert r["capability_state_c2"] == "PARTIAL", "MO-PAID-027 must stay PARTIAL"
    assert "6906" in r["state_delta"] or "MERGED" in r["state_delta"]


def test_mo_paid_085_capability_partial_with_715acf5f():
    """MO-PAID-085 capability moves to PARTIAL; co-text cites #6907 and 715acf5f."""
    rows = _read_csv(CSV_PATH)
    r = _row_by_id(rows, "MO-PAID-085")
    assert r["granular_disposition"] == "UPGRADE_EXISTING_OWNER"
    assert r["capability_state_c2"] == "PARTIAL", (
        f"expected PARTIAL, got {r['capability_state_c2']}"
    )
    assert "715acf5f" in r["state_delta"], (
        "expected commit 715acf5f in state_delta"
    )
    assert "6907" in r["state_delta"] or "MERGED" in r["state_delta"]


# ---------------------------------------------------------------------------
# F13 — #7147
# ---------------------------------------------------------------------------

def test_mo_delta_007_SPEC_ONLY():
    """MO-DELTA-007 capability_state_c2 -> SPEC_ONLY per #7147 §LEDGER_MOVES #32 (spec present; UserClaim absent)."""
    rows = _read_csv(CSV_PATH)
    r = _row_by_id(rows, "MO-DELTA-007")
    assert r["capability_state_c2"] == "SPEC_ONLY", (
        f"expected SPEC_ONLY, got {r['capability_state_c2']}"
    )
    assert r["granular_disposition"] == "PROJECTION_ONLY"


def test_mo_delta_011_BUILT_NOT_PROVEN():
    """MO-DELTA-011 capability_state_c2 -> BUILT_NOT_PROVEN per #7147 §LEDGER_MOVES #33 (glossary on main, not live)."""
    rows = _read_csv(CSV_PATH)
    r = _row_by_id(rows, "MO-DELTA-011")
    assert r["capability_state_c2"] == "BUILT_NOT_PROVEN", (
        f"expected BUILT_NOT_PROVEN, got {r['capability_state_c2']}"
    )
    assert r["granular_disposition"] == "PROJECTION_ONLY"


def test_mo_paid_088_cites_7133():
    """MO-PAID-088 next_bounded_child cites #7133 OPEN per #7147 §LEDGER_MOVES #35."""
    rows = _read_csv(CSV_PATH)
    r = _row_by_id(rows, "MO-PAID-088")
    assert "7133" in r["next_bounded_child"], (
        "expected #7133 citation in next_bounded_child"
    )


# ---------------------------------------------------------------------------
# HOLD rows — pre-state preserved (verified against origin/main)
# ---------------------------------------------------------------------------

HOLD_ROWS = [
    # origin/main values confirmed via git show origin/main:<csv>
    ("MO-DELTA-017", "NEW_BOUNDED_BUILD", "NOT_BUILT"),
    ("MO-DELTA-029", "NEW_BOUNDED_BUILD", "PARTIAL"),
    ("MO-PAID-067", "PROJECTION_ONLY", "PARTIAL"),
    ("MO-PAID-022", "NEW_BOUNDED_BUILD", "NOT_BUILT"),
    ("MO-PAID-026", "NEW_BOUNDED_BUILD", "NOT_BUILT"),
    ("MO-PAID-058", "UPGRADE_EXISTING_OWNER", "PARTIAL"),
    ("MO-PAID-031", "NEW_BOUNDED_BUILD", "SPEC_ONLY"),
    ("MO-PAID-032", "NEW_BOUNDED_BUILD", "SPEC_ONLY"),
    ("MO-PAID-047", "PROJECTION_ONLY", "PARTIAL"),
    ("MO-PAID-053", "NEW_BOUNDED_BUILD", "BUILT_NOT_PROVEN"),
    ("MO-PAID-054", "UPGRADE_EXISTING_OWNER", "PARTIAL"),
]


@pytest.mark.parametrize("row_id,expected_disp,expected_cap", HOLD_ROWS)
def test_hold_rows_preserved(row_id, expected_disp, expected_cap):
    """HOLD rows must retain their pre-state (disposition + capability)."""
    rows = _read_csv(CSV_PATH)
    r = _row_by_id(rows, row_id)
    assert r["granular_disposition"] == expected_disp, (
        f"{row_id}: expected disp {expected_disp}, got {r['granular_disposition']}"
    )
    assert r["capability_state_c2"] == expected_cap, (
        f"{row_id}: expected cap {expected_cap}, got {r['capability_state_c2']}"
    )


# ---------------------------------------------------------------------------
# Row count unchanged
# ---------------------------------------------------------------------------

def test_row_count_130():
    """Ledger must have exactly 130 data rows (header excluded)."""
    rows = _read_csv(CSV_PATH)
    assert len(rows) == 130, f"expected 130 rows, got {len(rows)}"


# ---------------------------------------------------------------------------
# No changed row promoted to DONE or PROVEN_LIVE
# (origin/main already has PROVEN_LIVE in unchanged rows — check transitions)
# ---------------------------------------------------------------------------

def test_no_changed_row_to_done_or_proven_live():
    """No row modified by THIS PR may have capability_state_c2 = DONE or PROVEN_LIVE."""
    # Rows actually changed by this PR (from git diff origin/main HEAD -- <csv>)
    changed_ids = {
        "MO-PAID-035", "MO-PAID-037", "MO-DELTA-040", "MO-PAID-057",
        "MO-PAID-020", "MO-PAID-021", "MO-DELTA-002",
        "MO-DELTA-003", "MO-DELTA-042", "MO-PAID-027", "MO-PAID-085",
        "MO-DELTA-007", "MO-DELTA-011", "MO-PAID-088",
    }
    rows = _read_csv(CSV_PATH)
    bad = [
        r["id"] for r in rows
        if r["id"] in changed_ids and r["capability_state_c2"] in ("DONE", "PROVEN_LIVE")
    ]
    assert not bad, f"Changed rows promoted to DONE/PROVEN_LIVE: {bad}"


def test_blocked_rights_not_in_capability():
    """BLOCKED_RIGHTS is a granular_disposition value only; never a capability_state_c2."""
    rows = _read_csv(CSV_PATH)
    bad = [
        r["id"] for r in rows
        if r["capability_state_c2"] == "BLOCKED_RIGHTS"
    ]
    assert not bad, f"Rows with BLOCKED_RIGHTS as capability: {bad}"

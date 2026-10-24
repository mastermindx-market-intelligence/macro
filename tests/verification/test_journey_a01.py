"""A01-1 — the collected vertical acceptance journey (programme DATA-OS-COMPLETION).

One module-scoped fixture builds the frozen synthetic corpus and runs the journey
ONCE (``journey_a01.run_journey``); every test calls a named assertion from
``journey_a01`` or inspects the receipt directly.  No float tolerance and no
``pytest.approx`` anywhere: every value comparison is exact, through ``Fraction``.

Zero skips by design: ``SKIPPED_ROOT_HOST`` is a recorded receipt VALUE (asserted
as one of two lawful outcomes), never a pytest skip.
"""
from __future__ import annotations

import json
import sys
from fractions import Fraction
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.verification import journey_a01 as journey  # noqa: E402
from tests.verification.journey_a01 import (  # noqa: E402
    DIV_CASH, DIV_FACTOR, GEN_A, PENDING_LEGS, REGISTRY_DATASET, SEC_ABC,
    SEC_ABC_2, SEC_MMC, SPLIT_DAY_INDEX, DIV_DAY_INDEX, VIEW_A_ID,
)

EXPECTED_RIGHTS = {"purchase_access": "unverified",
                   "internal_computation": "unverified",
                   "redistribution": "not_granted"}


@pytest.fixture(scope="module")
def receipt(tmp_path_factory) -> dict:
    """Build the corpus and run S1–S8 exactly once for this module."""
    base = tmp_path_factory.mktemp("a01_journey")
    return journey.run_journey(base)


# ── A01.01 — known answer, three consumers, CURRENT/REPLAY ────────────────────

def test_s1_view_a_served_for_three_tickers(receipt):
    """A01.01 — view A is served to all three price consumers without refusal"""
    s1 = receipt["s1_view_a"]
    for ticker in ("PLAINCO", "SPLITCO", "DIVCO"):
        assert s1["seam"][ticker]["ok"], ticker
        assert s1["seam"][ticker]["refusal"] is None
        assert s1["seam"][ticker]["coverage"].startswith("2026-01-02")
        assert len(s1["seam"][ticker]["values"]) == 60
        assert s1["inspector"][ticker]["rows"]
    assert s1["read_contract_current"]["rows"] == 60
    assert s1["read_contract_current"]["label"] == "current"


def test_known_answer_three_consumers(receipt):
    """A01.01 — assert_a01_01_known_answer_three_consumers"""
    journey.assert_a01_01_known_answer_three_consumers(receipt)


def test_known_answer_splitco_exact_two_for_one(receipt):
    """A01.01 — SPLITCO's stored tradj series carries the exact 2-for-1 relation"""
    values = receipt["s1_view_a"]["seam"]["SPLITCO"]["values"]
    dates = sorted(values)
    pre = [Fraction(values[d]) for d in dates[:SPLIT_DAY_INDEX]]
    post = [Fraction(values[d]) for d in dates[SPLIT_DAY_INDEX:]]
    assert set(pre) == {Fraction(50)} and set(post) == {Fraction(100)}
    assert post[0] == pre[-1] * Fraction(2, 1)


def test_known_answer_divco_exact_distribution(receipt):
    """A01.01 — DIVCO's declared distribution relation holds exactly on day 20

    The source series the registry names for this store is the total-return
    adjusted close (``schema.close.basis: tradj`` on ``equity.bars.daily.stocks``):
    the store back-adjusts every bar BEFORE the ex-date by the total-return factor
    ``1 + D/P_post`` — a multiplicative rebase of the pre-ex tail, the post-ex
    bars untouched.  With D = 25.00 and P_post = 100.00 the factor is exactly
    5/4 and the stored pre-ex tail is exactly 80.00.
    """
    values = receipt["s1_view_a"]["seam"]["DIVCO"]["values"]
    dates = sorted(values)
    pre_day, post_day = dates[DIV_DAY_INDEX - 1], dates[DIV_DAY_INDEX]
    assert DIV_FACTOR == 1 + DIV_CASH / Fraction(100)
    assert Fraction(values[pre_day]) * DIV_FACTOR == Fraction(values[post_day])
    assert Fraction(values[pre_day]) == Fraction(80)
    assert Fraction(values[post_day]) == Fraction(100)


def test_known_answer_plainco_control_identical(receipt):
    """A01.01 — the no-action control is identical across every consumer"""
    s1 = receipt["s1_view_a"]
    seam = s1["seam"]["PLAINCO"]["values"]
    inspector = {day: value for day, value in s1["inspector"]["PLAINCO"]["rows"]}
    assert seam == inspector
    assert s1["retained_a"]["payload_plainco_day10"] == seam[
        receipt["s2_generation_b"]["day"]]
    days = sorted(seam)
    assert seam[days[0]] == "100" and seam[days[-1]] == "159"
    assert seam[receipt["s2_generation_b"]["day"]] == receipt[
        "s2_generation_b"]["a_value"]


def test_current_returns_b(receipt):
    """A01.01 — assert_a01_01_current_returns_b"""
    journey.assert_a01_01_current_returns_b(receipt)


def test_replay_returns_exact_a(receipt):
    """A01.01 — assert_a01_01_replay_returns_exact_a"""
    journey.assert_a01_01_replay_returns_exact_a(receipt)


def test_stale_generation_proof(receipt):
    """A01.01 — CURRENT evidence naming GEN_A refuses STALE_GENERATION after B"""
    s3 = receipt["s3_current_after_b"]
    assert s3["stale_generation_code"] == "STALE_GENERATION"
    assert s3["read_contract"]["generation"] != GEN_A


def test_registry_rights_row_real_corpus_unfinished(receipt):
    """A01.01 — the real retained corpus leg stays UNFINISHED on the quoted rights

    The registry row ``equity.bars.daily.stocks`` states
    ``rights.internal_computation: unverified`` and ``rights.redistribution:
    not_granted`` (all three values asserted exactly, via both the Registry
    object and the raw YAML file), so a rights-allowed retained corpus cannot be
    established on this repo's evidence and the leg cannot silently flip to
    "passed" when rights change.
    """
    assert PENDING_LEGS["real_retained_corpus"] in receipt["pending_legs"].values()
    from lib.dataos.registry import load_registry
    row = load_registry().get(REGISTRY_DATASET)
    assert row is not None and row.rights == EXPECTED_RIGHTS
    raw = yaml.safe_load((ROOT / "config" / "dataset_registry.yml").read_text(
        encoding="utf-8"))
    entry = next(e for e in raw["datasets"]
                 if e.get("dataset_id") == REGISTRY_DATASET)
    assert entry["rights"] == EXPECTED_RIGHTS


# ── A01.02 — a passing call is not workflow acceptance ────────────────────────

def test_inspectable_explanation(receipt):
    """A01.02 — assert_a01_02_inspectable_explanation"""
    journey.assert_a01_02_inspectable_explanation(receipt)


def test_a_passing_call_is_not_workflow_acceptance(receipt):
    """A01.02 — the receipt names the browser/production workflow as not covered"""
    assert receipt["pending_legs"] == PENDING_LEGS
    assert receipt["pending_legs"]["terminal_json_evidence"].startswith("UNFINISHED")
    assert "#996" in receipt["citations"]["terminal_ui"]
    assert "fdc7c7f9" in receipt["citations"]["terminal_ui"]
    assert receipt["citations"]["terminal_ui"].count("R02/R03") == 1
    for ticker in ("PLAINCO", "SPLITCO", "DIVCO"):
        assert receipt["s1_view_a"]["inspector"][ticker][
            "production_qualification"] == "NOT_ESTABLISHED_BY_THIS_ADAPTER"


# ── A01.03 — controls the happy path cannot mask ──────────────────────────────

def test_rename_boundary_exact(receipt):
    """A01.03 — assert_a01_03_rename_owner_evidenced_only"""
    journey.assert_a01_03_rename_owner_evidenced_only(receipt)


def test_rename_row_omitted_no_continuity(receipt):
    """A01.03 — with the MRSH alias row omitted nothing resolves after the rename"""
    rename = receipt["s6_identity"]["rename"]
    assert rename["row_omitted_mrsh_on"] is None
    assert rename["mrsh_on"] == SEC_MMC == rename["mmc_before"]


@pytest.mark.xfail(strict=True, reason=(
    "FINDING A01-F1: VendorAliasTable binds rename continuity from an alias row "
    "that carries NO evidence digest — evidence_sha256 is optional for non-polygon "
    "vendors, so owner evidence is not enforced at bind time.  Correct behaviour: "
    "a rename row without owner evidence must not yield continuity.  Reproducer: "
    "VendorAliasTable([AliasRow('yahoo','MMC',SEC_MMC,None,date(2026,1,14)), "
    "AliasRow('yahoo','MRSH',SEC_MMC,date(2026,1,14),None)]).resolve("
    "'yahoo','MRSH',date(2026,1,14)) returns SEC_MMC instead of None"))
def test_rename_without_evidence_is_a_finding(receipt):
    """A01.03 — rename continuity must not be granted without owner evidence"""
    assert receipt["s6_identity"]["rename"]["no_evidence_mrsh_on"] is None


def test_reused_ticker_two_securities(receipt):
    """A01.03 — assert_a01_03_reused_ticker_does_not_join"""
    journey.assert_a01_03_reused_ticker_does_not_join(receipt)


def test_reused_ticker_boundary_ids(receipt):
    """A01.03 — the reused ticker resolves to two distinct ids either side of reuse"""
    reuse = receipt["s6_identity"]["reuse"]
    assert reuse["before"] == SEC_ABC
    assert reuse["on_or_after"] == SEC_ABC_2
    assert reuse["before"] != reuse["on_or_after"]


def test_reused_ticker_overlap_refused(receipt):
    """A01.03 — an overlapping-interval alias table refuses at construction"""
    assert receipt["s6_identity"]["reuse"]["overlap_refused_at_construction"] is True


def test_reused_ticker_join_unfinished_not_passed(receipt):
    """A01.03 — the ticker-key join is recorded UNFINISHED, never passed"""
    join = receipt["s6_identity"]["reuse_join"]
    assert join["note"].startswith("UNFINISHED: awaiting U03/U04 LANDED")
    assert join["seam_ok"] and join["seam_rows_served"] == 60
    assert "resolve_close_canonical" in join["note"]


def test_incompatible_refuses_compatible_serves(receipt):
    """A01.03 — assert_a01_03_incompatible_refuses_compatible_succeeds"""
    journey.assert_a01_03_incompatible_refuses_compatible_succeeds(receipt)


# ── A01.04 — nothing hidden or silently filled ────────────────────────────────

def test_missing_member_stays_in_account(receipt):
    """A01.04 — assert_a01_04_missing_member_stays_in_account"""
    journey.assert_a01_04_missing_member_stays_in_account(receipt)


def test_coverage_denominator_before_and_after_b(receipt):
    """A01.04 — the account denominator is the frozen population, both sides of B"""
    before = receipt["s1_view_a"]["account"]
    after = receipt["s8_coverage_after_b"]
    for account in (before, after):
        assert account["requested"] == 4
        assert Fraction(account["qualified_fraction"]) == Fraction(3, 4)
        assert account["summary"]["dispositions"]["MISSING"] == 1
        assert account["summary"]["dispositions"]["SERVED"] == 3
        assert "US-XNYS-GONECO" not in account["qualified"]
    assert before["summary"] == after["summary"]


def test_revocation_typed_never_b_under_a(receipt):
    """A01.04 — assert_a01_04_revocation_typed_never_b_under_a"""
    journey.assert_a01_04_revocation_typed_never_b_under_a(receipt)


def test_revocation_root_binding_removed(receipt):
    """A01.04 — a removed root binding refuses ROOT_NOT_BOUND"""
    case = receipt["s5_revocations"]["root_binding_removed"]
    assert case == {"code": "ROOT_NOT_BOUND", "values_present": False}


def test_revocation_source_file_deleted(receipt):
    """A01.04 — a deleted source refuses SOURCE_NOT_FOUND"""
    case = receipt["s5_revocations"]["source_file_deleted"]
    assert case == {"code": "SOURCE_NOT_FOUND", "values_present": False}


def test_revocation_source_unreadable(receipt):
    """A01.04 — an unreadable source refuses SOURCE_INACCESSIBLE (or root-host skip)"""
    case = receipt["s5_revocations"]["source_unreadable"]
    if case["code"] == "SKIPPED_ROOT_HOST":
        assert case["values_present"] is True
    else:
        assert case == {"code": "SOURCE_INACCESSIBLE", "values_present": False}


def test_revocation_version_pin(receipt):
    """A01.04 — a read pinned to A's version after B refuses SOURCE_VERSION_MISMATCH"""
    case = receipt["s5_revocations"]["expected_version_pinned_to_a"]
    assert case == {"code": "SOURCE_VERSION_MISMATCH", "values_present": False}
    assert receipt["s1_view_a"]["plainco_version_a"]


def test_revocation_reconstruct_required_missing(receipt):
    """A01.04 — reconstruct with a required dependency missing refuses UNBOUND_DEPENDENCY"""
    case = receipt["s5_revocations"]["reconstruct_required_missing"]
    assert case == {"code": "UNBOUND_DEPENDENCY", "values_present": False}


def test_revocation_replay_payload_removed(receipt):
    """A01.04 — replay with the retained payload removed refuses NO_RETAINED_OUTPUT"""
    case = receipt["s5_revocations"]["replay_retained_payload_removed"]
    assert case == {"code": "NO_RETAINED_OUTPUT", "values_present": False}


# ── receipt shape ──────────────────────────────────────────────────────────────

def test_pending_legs_receipt(receipt):
    """the receipt lists PENDING_LEGS verbatim — assert_receipt_lists_pending_legs"""
    journey.assert_receipt_lists_pending_legs(receipt)


def test_receipt_json_serialisable(receipt):
    """the whole journey receipt is JSON-serialisable (Fractions as n/d strings)"""
    text = json.dumps(receipt, sort_keys=True)
    loaded = json.loads(text)
    assert loaded["view_a_id"] == VIEW_A_ID
    assert loaded["s3_current_after_b"]["seam_day10"] == "999"

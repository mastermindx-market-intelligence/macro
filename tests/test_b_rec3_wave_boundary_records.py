"""Pin the B-REC-3 wave-boundary records absorbed into packet B-REC-B5-1.

Mirrors tests/test_b_rec2_wave_boundary_records.py: repo-root ``_ROOT``, no
network, no subprocess, no read of any other checkout.

RED on the pre-packet head (macro #6997 head ecaf8f8e merged with #6981's
479f9725): receipts 0014/0015/0016 were not in the repo, the migration-namespace
DEC recorded evidence only through 0013, neither wave-boundary discovery existed,
the Half-A K-chain docket never said whose acceptance its opener denotes, and the
five F12 ledger rows still read NOT_BUILT or PARTIAL.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import pytest
import yaml

_ROOT = Path(__file__).resolve().parents[1]

_RECEIPTS = _ROOT / "research/market_intelligence_productization/receipts"
RECEIPT_0014 = _RECEIPTS / "supabase_receipt_0014_tenancy_foundation_2026-09-08.json"
RECEIPT_0015 = _RECEIPTS / "supabase_receipt_0015_team_roles_invitations_2026-09-08.json"
RECEIPT_0016 = _RECEIPTS / "supabase_receipt_0016_account_lifecycle_requests_2026-09-09.json"

DEC = _ROOT / (
    "agentos/decisions/"
    "DEC-SUPABASE-MIGRATION-NAMESPACE-TERMINAL-LEDGER-2026-09-06.md"
)
DSC_THREADS = _ROOT / (
    "agentos/discoveries/DSC-TERMINAL-MASTER-REQUIRES-RESOLVED-THREADS-SO-AN"
    "-ADVISORY-CODEQL-THREAD-BLOCKS-A-GREEN-HEAD.md"
)
DSC_OVERLAP = _ROOT / (
    "agentos/discoveries/DSC-SEAT-TRANSFER-OVERLAP-DUPLICATES-IRREVERSIBLE-ACTS.md"
)
DOCKET = _ROOT / (
    "research/market_intelligence_productization/"
    "MARKET_ONTOLOGY_HALF_A_K_CHAIN_GATE_DOCKET_2026-09-06.md"
)
LEDGER = _ROOT / (
    "research/market_intelligence_productization/"
    "MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv"
)

ALL_RECEIPTS = (RECEIPT_0014, RECEIPT_0015, RECEIPT_0016)

# A Supabase project reference is a 20-character run of lowercase letters. The
# receipts of record carry the literal placeholder instead; this is the guard that
# keeps a real one from ever being committed by a later edit.
_PROJECT_REF_SHAPE = re.compile(r"[a-z]{20}")


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path.name}: no YAML frontmatter"
    return yaml.safe_load(text.split("---", 2)[1])


def _ledger_rows() -> dict[str, dict]:
    with LEDGER.open(newline="", encoding="utf-8") as fh:
        return {row["id"]: row for row in csv.DictReader(fh)}


# ---------------------------------------------------------------- receipts


@pytest.mark.parametrize("path", ALL_RECEIPTS, ids=lambda p: p.stem)
def test_receipt_exists_and_parses(path: Path) -> None:
    assert path.exists(), f"missing receipt: {path}"
    json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", ALL_RECEIPTS, ids=lambda p: p.stem)
def test_receipt_project_ref_is_the_placeholder(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data.get("project_ref") == "{ref}"


@pytest.mark.parametrize("path", ALL_RECEIPTS, ids=lambda p: p.stem)
def test_receipt_records_a_successful_application(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data.get("apply_result") == "ok"


@pytest.mark.parametrize("path", ALL_RECEIPTS, ids=lambda p: p.stem)
def test_receipt_never_carries_a_project_reference(path: Path) -> None:
    hit = _PROJECT_REF_SHAPE.search(path.read_text(encoding="utf-8"))
    assert hit is None, f"{path.name}: a project-reference-shaped token is present"


def test_0015_was_applied_after_0014_and_0016_after_0015() -> None:
    r15 = json.loads(RECEIPT_0015.read_text(encoding="utf-8"))
    r16 = json.loads(RECEIPT_0016.read_text(encoding="utf-8"))
    assert "0014" in str(r15.get("applied_after", "")), (
        "0015's receipt must name 0014 as the migration it followed"
    )
    assert "0015" in str(r16.get("applied_after", "")), (
        "0016's receipt must name 0015 as the migration it followed"
    )
    r14 = json.loads(RECEIPT_0014.read_text(encoding="utf-8"))
    assert r14["applied_at"] < r15["applied_at"] < r16["applied_at"], (
        "the three receipts must record ledger-number order in wall-clock time"
    )


# ------------------------------------------------- migration-namespace DEC


def test_dec_records_the_0014_0015_0016_applications() -> None:
    text = DEC.read_text(encoding="utf-8")
    for token in (
        "2026-09-08T22:24:14Z",   # 0014
        "2026-09-08T22:24:42Z",   # 0015
        "2026-09-09T01:11:07Z",   # 0016
        "cff58ee8",               # terminal#514 merge
        "83424c63",               # terminal#526 squash onto #514's branch
        "68bbe8ea",               # terminal#527 merge
    ):
        assert token in text, f"DEC missing wave-boundary evidence token {token!r}"


def test_dec_names_the_three_new_receipts_as_evidence() -> None:
    text = DEC.read_text(encoding="utf-8")
    for path in ALL_RECEIPTS:
        assert path.name in text, f"DEC does not cite receipt {path.name}"


def test_dec_records_the_duplicate_application_as_idempotent_and_superseded() -> None:
    text = DEC.read_text(encoding="utf-8")
    assert "SEAT-TRANSFER-OVERLAP-DUPLICATES-IRREVERSIBLE-ACTS" in text, (
        "the duplicate application must cite the seat-transfer discovery"
    )
    assert "5592751149" in text, "the supersession comment id must be recorded"


# ------------------------------------------------------- the two discoveries


@pytest.mark.parametrize("path", (DSC_THREADS, DSC_OVERLAP), ids=lambda p: p.stem)
def test_discovery_exists_with_a_complete_frontmatter(path: Path) -> None:
    assert path.exists(), f"missing discovery: {path}"
    fm = _frontmatter(path)
    for field in (
        "key", "claim", "falsifier", "so_what", "kind",
        "verified_at", "verified_by", "scope", "confidence",
    ):
        assert fm.get(field), f"{path.name}: missing or empty field {field!r}"
    assert path.stem == f"DSC-{fm['key']}", (
        f"{path.name}: filename must be DSC-<key>.md"
    )
    assert fm["kind"] == "landmine"
    assert fm["confidence"] == "verified"


def test_threads_discovery_names_the_protection_flag_and_the_blocked_pr() -> None:
    text = DSC_THREADS.read_text(encoding="utf-8")
    assert "required_conversation_resolution" in text
    assert "terminal#514" in text
    assert "cff58ee8" in text
    assert "1d5956ec" in text, (
        "B-REC-3 item 14: the least-privilege follow-up terminal#537 merged as "
        "1d5956ec and its sha belongs in this discovery's so_what"
    )


def test_overlap_discovery_orders_the_seat_transfer_protocol() -> None:
    text = DSC_OVERLAP.read_text(encoding="utf-8")
    assert "7cd4fae1" in text, "the predecessor session id must be named"
    assert "d640f3ef" in text, "the successor session id must be named"
    assert "5592751149" in text, "the disclosure comment must be cited"


# ------------------------------------------------------- K-chain docket note


def test_docket_says_whose_acceptance_the_opener_denotes() -> None:
    text = DOCKET.read_text(encoding="utf-8")
    assert "CHAIRMAN-OVERRIDE-CLAUDE-META-CEO-REGIME-2026-09-06" in text
    assert "#6961" in text
    assert "5563643365" in text


def test_docket_note_does_not_disturb_the_quoted_openers() -> None:
    text = DOCKET.read_text(encoding="utf-8")
    assert text.count("- **Opener:** Sol acceptance") == 5, (
        "the five quoted 'Sol acceptance' openers are a ratified record and must "
        "not be rewritten by the note"
    )


# ---------------------------------------------------- F12 ledger rows (item 3)


@pytest.mark.parametrize(
    "row_id",
    ("MO-PAID-081", "MO-PAID-082", "MO-PAID-083", "MO-PAID-086", "MO-PAID-087"),
)
def test_f12_rows_moved_to_built_not_proven(row_id: str) -> None:
    row = _ledger_rows()[row_id]
    assert row["capability_state_c2"] == "BUILT_NOT_PROVEN", (
        f"{row_id}: the merged Terminal wave satisfies its acceptance sentence"
    )
    assert row["state_delta"] != "UNCHANGED", f"{row_id}: state_delta still says UNCHANGED"


# Round-2 FIX-3: byte-identical to the base branch (ecaf8f8e), not merely an
# open capability_state_c2 word — every other column of these rows could have
# been rewritten and the prior assertion would still have passed.
#
# 2026-09-19 seat records pass (Meta-CEO B 026851bd): MO-PAID-085 and MO-PAID-088
# were moved by Sol's single-writer F00C integration #7335 (merge af617506;
# ruling = #7335 comment 5739279644: 085 PARTIAL per #7138 §LEDGER_MOVES #10,
# 088 PROVEN_LIVE from the #7353 live Help receipt). The B-REC-3 wave still owns
# neither row, so the fence stays — re-pinned to the integration head's lines.
# MO-PAID-084 is unchanged since ecaf8f8e.
_UNTOUCHED_F12_ROWS_AT_BASE: dict[str, str] = {
    'MO-PAID-084': 'MO-PAID-084,F12-TEAM-API-PLATFORM,NEW_BOUNDED_BUILD,NOT_BUILT,UNCHANGED,WS:MARKET-OS (F12 lane) — canonical auth/secrets owner + API projection,NONE (api_key hits = server-side secrets only),NONE,API key issuance/management,n/a,DEFER — dependency MO-PAID-055 public API,an issued key authenticates one request and is revocable,n/a,access_control_only,',
    'MO-PAID-085': 'MO-PAID-085,F08-PORTFOLIO-ALERTS,UPGRADE_EXISTING_OWNER,PARTIAL,"REFRESHED per #7138 §LEDGER_MOVES #10: preferences half MERGED (#6907 squash 715acf5f 2026-09-18T22:49:38Z; live /api/health commit 715acf5f3c; GET /api/account/prefs -> 401 auth-gated); live /account.js carries prefs UI. Send path (engine/portfolio_digest.py ""SEND PATH IS NOT WIRED"") still unwired; #7131 OPEN. NOT DONE.",WS:MARKET-OS (F08 lane) — Market OS alerts + app/account_prefs.py (prefs sink),"app/account_prefs.py (no alert prefs) + engine/portfolio_digest.py (\'SEND PATH IS NOT WIRED, DELIBERATELY\')",NONE,alert/notification preference UI/API + mailer wiring,n/a,F08 delivery-path child includes prefs + app/mailer.py wiring (not rights-blocked). | #7131 OPEN: send path unwired; prefs UI live but alert send not wired.,a set preference causes an actual send on the next matching alert,"email via existing app/mailer.py (unwired, not rights-blocked)",notification_only,"2026-09-19 seat: prefs half built via macro #6907 (MERGED 2026-09-18T22:49:38Z, squash 715acf5f3ce5: app/account_prefs.py GET/POST /api/account/prefs, templates/account.js prefs UI, tests/test_alert_prefs.py); live /api/health reported commit 715acf5f3c and anonymous GET /api/account/prefs -> 401 (route live, auth-gated); DONE still needs the signed-in save journey (Chairman-only); delivery-path half (app/mailer.py wiring) remains NOT_BUILT"',
    'MO-PAID-088': 'MO-PAID-088,F13-OPS-LEARNING,UPGRADE_EXISTING_OWNER,PROVEN_LIVE,EVIDENCE-REFINED: /learn SEO hub (templates/seo_learn_index.html.j2 via build_free_content.py:1201) and an economic-release calendar widget exist but are NOT in-product help/FAQ/changelog; state unchanged,WS:MARKET-OS (F13 lane) — F13 lane + Market OS product/help owners,lib/help_directory.py:606 + templates/help.html.j2:238-254 (#6959) + app/support.py + methodology/seo_learn_index,public help.html (FAQs + dated changelog) + support mailbox,none — live-proven 2026-09-19: GET help.html 200 52137 changelog published 2026-09-05 #6828 and 14 FAQ answers,ticket ids stable; no ticket-update path,Help+changelog live. No second /help child.,an authenticated user reaches /help FAQs and a dated product changelog,Market OS product/help + release/receipt owners,operations_and_explanation_only,Public /help serves FAQs and a dated changelog. Authenticated-only was the old bar; anonymous 200 exceeds it.',
}


def test_the_untouched_f12_rows_keep_an_open_state_word() -> None:
    """B-REC-3 item 3: no half-B PR ships 084, 085 or 088.

    2026-09-19: Sol's F00C integration #7335 (comment 5739279644) moved 088 to
    PROVEN_LIVE on the #7353 live Help receipt — a later single-writer ruling,
    not a half-B PR — so 088 is pinned to that word; 084/085 stay open.
    """
    rows = _ledger_rows()
    for row_id in ("MO-PAID-084", "MO-PAID-085"):
        assert rows[row_id]["capability_state_c2"] in {"NOT_BUILT", "SPEC_ONLY", "PARTIAL"}, (
            f"{row_id}: nothing in this wave ships it, so it cannot read as built"
        )
    assert rows["MO-PAID-088"]["capability_state_c2"] == "PROVEN_LIVE", (
        "MO-PAID-088: Sol ruled PROVEN_LIVE (#7335 comment 5739279644, #7353 receipt)"
    )


def test_the_untouched_f12_rows_are_byte_identical_to_base() -> None:
    """B-REC-3 item 3, strengthened: 084/085/088 are not owned by this wave,
    so their raw CSV line must match the base branch (ecaf8f8e) exactly —
    not just keep an open capability_state_c2 word."""
    raw_by_id = {
        line.split(",", 1)[0]: line
        for line in LEDGER.read_text(encoding="utf-8").splitlines()
    }
    for row_id, base_line in _UNTOUCHED_F12_ROWS_AT_BASE.items():
        assert raw_by_id[row_id] == base_line, (
            f"{row_id}: this wave does not own this row — its raw CSV line "
            "must stay byte-identical to the base branch"
        )


# --------------------------------------------- CI scope closure (FIX-1, MAJOR)

_LEGACY_JOBS = _ROOT / ".github" / "ci" / "legacy-jobs.yml"

from tests.test_f00c_terminal_reconciliation import MANIFEST as _F00C_MANIFEST  # noqa: E402
from tests.test_f00c_terminal_reconciliation import RECORDS_DOC as _F00C_RECORDS_DOC  # noqa: E402
from tests.test_b_rec2_wave_boundary_records import HANDOFF as _B_REC2_HANDOFF  # noqa: E402
from tests.test_b_rec2_wave_boundary_records import RECEIPT_0012 as _B_REC2_RECEIPT_0012  # noqa: E402

# Every record read from disk by ALL THREE suites self-mod-fence runs — this
# file, test_f00c_terminal_reconciliation.py, and the sibling
# test_b_rec2_wave_boundary_records.py — not just this packet's own two. That
# job is the only one that runs any of them (see the run step at the bottom of
# its definition), so an edit that touches ONLY one of these paths must alone be
# able to select it — otherwise the pin these suites enforce fires post-merge on
# main instead of pre-merge on a PR. Round-4 MAJOR: the b_rec2 handoff was read
# by a suite this job runs and named nowhere in the job's `paths:` list, and
# `agentos` is outside LITERAL_DIRS, so nothing could select the job for it.
_PINNED_RECORD_PATHS = tuple(
    str(path.relative_to(_ROOT))
    for path in (
        RECEIPT_0014,
        RECEIPT_0015,
        RECEIPT_0016,
        DEC,
        DSC_THREADS,
        DSC_OVERLAP,
        DOCKET,
        LEDGER,
        _F00C_MANIFEST,
        _F00C_RECORDS_DOC,
        _B_REC2_HANDOFF,
        _B_REC2_RECEIPT_0012,
    )
)


def _self_mod_fence_paths() -> set[str]:
    manifest = yaml.safe_load(_LEGACY_JOBS.read_text(encoding="utf-8"))
    return set(manifest["jobs"]["self-mod-fence"].get("paths") or ())


@pytest.mark.parametrize("record_path", _PINNED_RECORD_PATHS)
def test_self_mod_fence_paths_cover_every_record_the_jobs_suites_pin(
    record_path: str,
) -> None:
    declared = _self_mod_fence_paths()
    assert record_path in declared, (
        f"{record_path!r} is read by a suite self-mod-fence runs but is missing "
        "from that job's `paths:` list in .github/ci/legacy-jobs.yml — an "
        "edit that touches only this file would never select the job that "
        "pins it, so the pin would fire post-merge on main instead of "
        "pre-merge on a PR"
    )

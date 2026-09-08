"""Pins the F01 FX/commodity rights record against the citations it claims.

Each assertion is a value check (exact posture string, cited file:line contents),
not an existence tautology. Findings: PR #6908 Opus review BLOCKER-1/2, MAJOR-1/2,
MINOR-2/3.
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

DSC_KEY = "COMMODITY-AND-FX-PRICE-SPINE-YAHOO-VENDOR-TERMS-ARE-RECORDED-ADVERSE"
DSC_PATH = REPO / "agentos" / "discoveries" / f"DSC-{DSC_KEY}.md"
OLD_DSC_PATH = (
    REPO
    / "agentos"
    / "discoveries"
    / "DSC-COMMODITY-AND-FX-PRICE-SPINE-IS-AN-UNRULED-YAHOO-STORE.md"
)
F01 = (
    REPO
    / "research"
    / "market_intelligence_productization"
    / "F01_FX_COMMODITY_SOURCE_RIGHTS_AND_DEPTH_2026-09.md"
)
CHARTER = (
    REPO
    / "research"
    / "market_intelligence_productization"
    / "F01_FX_DISLOCATION_CHARTER_2026-09.md"
)
DEC_OVERRIDE = (
    REPO
    / "agentos"
    / "decisions"
    / "DEC-CHAIRMAN-OVERRIDE-CLAUDE-META-CEO-REGIME-2026-09-06.md"
)
REGISTRY = REPO / "config" / "dataset_registry.yml"
CONTRACTS = REPO / "research" / "MASTERMIND_DATA_CONTRACTS.md"
IMCE = REPO / "research" / "IMCE_ROUND3_ARCHITECTURE_FREEZE_BY_FABLE.md"
FOREX_INPUTS = REPO / "engine" / "forex_inputs.py"
COLLECT = REPO / "scripts" / "collect.py"
BUILD_SPR = REPO / "scripts" / "build_spr.py"
DISLOCATION = REPO / "engine" / "dislocation.py"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _line(path: Path, n: int) -> str:
    lines = _text(path).splitlines()
    assert n >= 1, f"{path} line {n} is not 1-indexed"
    assert n <= len(lines), f"{path} has {len(lines)} lines; cannot read :{n}"
    return lines[n - 1]


# ---------------------------------------------------------------------------
# BLOCKER-1 — DSC claim is recorded-and-adverse, not UNRULED
# ---------------------------------------------------------------------------


def test_old_unruled_dsc_filename_is_gone() -> None:
    assert not OLD_DSC_PATH.exists(), (
        f"{OLD_DSC_PATH.name} still exists — the UNRULED title was the falsified claim"
    )


def test_dsc_key_and_h1_drop_unruled() -> None:
    text = _text(DSC_PATH)
    assert f"key: {DSC_KEY}" in text
    assert "UNRULED" not in text
    assert "unruled" not in text
    first_h1 = next(line for line in text.splitlines() if line.startswith("# "))
    assert first_h1 == (
        "# Commodity and FX price spine Yahoo vendor terms are recorded and adverse"
    )


def test_dsc_claim_is_recorded_adverse_personal_use() -> None:
    text = _text(DSC_PATH)
    claim_block = text.split("falsifier:", 1)[0]
    assert "vendor_terms_personal_use" in claim_block
    assert "recorded and adverse" in claim_block
    assert "never cleared" in claim_block
    assert "no rights ruling" not in claim_block
    assert "unrecorded, not cleared" not in claim_block


def test_dsc_falsifier_covers_config_and_research() -> None:
    text = _text(DSC_PATH)
    falsifier = text.split("falsifier:", 1)[1].split("so_what:", 1)[0]
    assert "config/" in falsifier
    assert "research/" in falsifier
    assert "vendor_terms_personal_use" in falsifier


def test_dsc_verified_by_cites_the_two_research_records() -> None:
    text = _text(DSC_PATH)
    verified = text.split("verified_by:", 1)[1].split("scope:", 1)[0]
    assert "research/MASTERMIND_DATA_CONTRACTS.md:103" in verified
    assert "research/IMCE_ROUND3_ARCHITECTURE_FREEZE_BY_FABLE.md:189" in verified
    assert "config/dataset_registry.yml:63" in verified


def test_dsc_so_what_forbids_typing_the_spine_unknown() -> None:
    text = _text(DSC_PATH)
    so_what = text.split("so_what:", 1)[1].split("kind:", 1)[0]
    assert "must not type the spine `unknown`" in so_what
    assert "recorded-and-adverse (vendor_terms_personal_use)" in so_what


def test_yahoo_registry_row_is_personal_use_vendor_terms() -> None:
    """Ground the DSC in the live registry, not in a self-citation."""
    assert _line(REGISTRY, 59).strip() == "vendor: yahoo"
    assert _line(REGISTRY, 63).strip() == "licensing: vendor_terms_personal_use"
    assert _line(REGISTRY, 104).strip() == "licensing: vendor_terms_personal_use"


def test_data_contracts_record_paid_republication_of_yfinance() -> None:
    line = _line(CONTRACTS, 103)
    assert "yfinance-sourced and republished to a paid product" in line
    assert "licensing: vendor_terms_personal_use" in line


def test_imce_canonical_price_tape_documents_yfinance_exposure() -> None:
    line = _line(IMCE, 189)
    assert "CANONICAL_PRICE_TAPE (REUSE; yfinance exposure documented in-repo)" in line


# ---------------------------------------------------------------------------
# BLOCKER-2 — FRED legs are rights_blocked by clause (q), not unknown
# ---------------------------------------------------------------------------


def test_imce_fred_clause_q_is_do_not_ingest() -> None:
    line_111 = _line(IMCE, 111)
    assert "FRED = DO_NOT_INGEST" in line_111
    assert "Prohibition (q)" in line_111
    assert "storing/caching/archiving FRED content" in line_111
    line_189 = _line(IMCE, 189)
    assert (
        "DO_NOT_INGEST — FRED_API_SITE (clause (q): no store/cache/archive/database "
        "incorporation; binds all use classes)"
    ) in line_189


def test_fred_legs_are_stored_fred_content() -> None:
    line_45 = _line(FOREX_INPUTS, 45)
    assert "fx_rates_short" in line_45
    assert "fx_rates_long" in line_45
    assert "fx_reer" in line_45
    line_150 = _line(COLLECT, 150)
    assert '("fred", "collectors.fred", "FredAdapter")' in line_150


def test_f01_fred_rows_are_rights_blocked_clause_q() -> None:
    text = _text(F01)
    blocked = "rights_blocked (FRED clause (q); IMCE Round-3 freeze :189)"
    assert text.count(blocked) >= 5
    assert "IMCE binds" in text or "IMCE freeze binds" in text
    assert "unreconciled practice" in text
    # The three FRED-group inventory rows must not reuse the forbidden unknown typing.
    inventory = text.split("## 3.")[0]
    for needle in (
        "| policy/short rates |",
        "| long rates |",
        "| REER |",
    ):
        row = next(line for line in inventory.splitlines() if line.startswith(needle))
        assert blocked in row, f"{needle} is not typed rights_blocked: {row}"
        assert "unknown (rights-posture-unrecorded)" not in row


def test_f01_v2_cites_imce_111_and_189() -> None:
    text = _text(F01)
    v2 = text.split("**V-2 basis", 1)[1].split("**V-3", 1)[0]
    assert "IMCE_ROUND3_ARCHITECTURE_FREEZE_BY_FABLE.md:111" in v2
    assert ":189" in v2
    assert "DO_NOT_INGEST" in v2
    assert "clause (q)" in v2
    assert "scripts/collect.py:150" in v2


def test_f01_section7_does_not_certify_fred_as_unknown() -> None:
    closure = _text(F01).split("## 7. Ledger closure statement", 1)[1]
    assert "rights_blocked (FRED clause (q); IMCE Round-3 freeze :189)" in closure
    assert "the IMCE freeze binds the rights reading" in closure
    # Yahoo is no longer lumped into the unknown bucket either.
    assert "Yahoo typed `recorded-and-adverse (vendor_terms_personal_use)`" in closure
    assert (
        "every vendor (Yahoo, CFTC, EIA) typed `unknown (rights-posture-unrecorded)`"
        not in closure
    )


# ---------------------------------------------------------------------------
# MAJOR-1 — negative-search scope includes research/ and config/
# ---------------------------------------------------------------------------


def test_f01_v_rows_state_widened_search_scope_and_date() -> None:
    text = _text(F01)
    for marker in ("**V-1 ", "**V-2a ", "**V-3 ", "**V-4 "):
        section = text.split(marker, 1)[1].split("\n- **V-", 1)[0]
        assert "research/" in section, f"{marker} omitted research/ from the search"
        assert "config/" in section, f"{marker} omitted config/ from the search"
        assert "2026-09-07" in section, f"{marker} still carries the old 2026-09-05 scope date"


def test_f01_headline_does_not_claim_yahoo_is_unrecorded() -> None:
    headline = _text(F01).split("## 2.")[0]
    assert "no rights ruling" not in headline
    assert "vendor_terms_personal_use" in headline
    assert "recorded and adverse, never cleared" in headline


# ---------------------------------------------------------------------------
# MAJOR-2 — authorizing DEC is on this tree (PR #6894 merged)
# ---------------------------------------------------------------------------


def test_authorizing_dec_is_present_on_this_tree() -> None:
    text = _text(DEC_OVERRIDE)
    assert "key: CHAIRMAN-OVERRIDE-CLAUDE-META-CEO-REGIME-2026-09-06" in text
    assert "HOLD-FOR-SOL is no longer a lawful terminal state" in text
    f01 = _text(F01)
    assert "DEC-CHAIRMAN-OVERRIDE-CLAUDE-META-CEO-REGIME-2026-09-06" in f01
    assert "PR #6894" in f01
    assert "discharged 2026-09-07" in f01


# ---------------------------------------------------------------------------
# MINOR-2 — SPR store group is eia, not a filesystem path
# ---------------------------------------------------------------------------


def test_spr_store_group_is_eia() -> None:
    row = next(
        line
        for line in _text(F01).splitlines()
        if line.startswith("| US SPR weekly stocks |")
    )
    assert "| `eia` |" in row
    assert "data/eia/spr_stocks" not in row.split("|")[2]
    assert 'store.read("eia", "spr_stocks")' in _line(BUILD_SPR, 214)


# ---------------------------------------------------------------------------
# MINOR-3 — charter names master_switch_frame, not Gate-1
# ---------------------------------------------------------------------------


def test_charter_names_master_switch_frame() -> None:
    text = _text(CHARTER)
    acceptance = text.split("## 2. The one-line distinction", 1)[1].split("## 3.", 1)[0]
    assert "FED-PUT MASTER SWITCH" in acceptance
    assert "master_switch_frame" in acceptance
    assert "Gate-1 switch" not in acceptance
    assert _line(DISLOCATION, 260).startswith("def master_switch_frame(")
    assert "FED-PUT MASTER SWITCH:" in "\n".join(
        _line(DISLOCATION, n) for n in range(29, 35)
    )

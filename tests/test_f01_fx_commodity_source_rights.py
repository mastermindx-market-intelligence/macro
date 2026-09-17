"""Pins the F01 FX/commodity rights record against the citations it claims.

Each assertion is a value check (exact posture string, cited contents),
not an existence tautology. Cross-file assertions are content-anchored:
they search the cited file for a string, then — when the record cites
file:N — check that the RECORD's own N resolves to a line containing
that string. A drift fails with a message naming the record line to
update, never by equal-comparing an absolute line number of a file
outside this PR.
"""
from __future__ import annotations

import re
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

YAHOO_BLOCKED = (
    "rights_blocked (basis: vendor_terms_personal_use, config/dataset_registry.yml)"
)
FRED_BLOCKED = "rights_blocked (FRED clause (q); IMCE Round-3 freeze :189)"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _linelist(path: Path) -> list[str]:
    return _text(path).splitlines()


def _first_lineno(path: Path, needle: str) -> int:
    for i, line in enumerate(_linelist(path), 1):
        if needle in line:
            return i
    raise AssertionError(f"{path} has no line containing {needle!r}")


def _assert_present(path: Path, needle: str) -> int:
    n = _first_lineno(path, needle)
    assert needle in _linelist(path)[n - 1]
    return n


def _assert_record_citation_resolves(
    record: Path,
    cited: Path,
    path_token: str,
    needle: str,
) -> None:
    """Parse path_token:N citations from the record. At least one must
    resolve to a line of `cited` containing `needle`. Failure names the
    record line(s) to update, not the pack."""
    pattern = re.compile(rf"{re.escape(path_token)}:(\d+)")
    matches: list[tuple[int, int]] = []
    for i, line in enumerate(_linelist(record), 1):
        for m in pattern.finditer(line):
            matches.append((i, int(m.group(1))))
    assert matches, f"{record.name} does not cite {path_token}:N"
    lines = _linelist(cited)
    for rec_n, cited_n in matches:
        if 1 <= cited_n <= len(lines) and needle in lines[cited_n - 1]:
            return
    details = []
    for rec_n, cited_n in matches:
        loc = f"{record.name}:{rec_n}"
        if not (1 <= cited_n <= len(lines)):
            details.append(
                f"{loc} cites {path_token}:{cited_n} but {cited.name} has "
                f"{len(lines)} lines"
            )
            continue
        details.append(
            f"{loc} cites {path_token}:{cited_n} = {lines[cited_n - 1]!r}"
        )
    raise AssertionError(
        f"no {record.name} citation of {path_token}:N contains {needle!r} — "
        f"update {'; '.join(details)}"
    )


def _assert_and_continuation_resolves(
    record: Path,
    cited: Path,
    after_token: str,
    needle: str,
) -> None:
    """Parse `after_token:N and :M` and require cited:M contain needle."""
    pattern = re.compile(
        rf"{re.escape(after_token)}:(\d+)\s+and\s+:(\d+)"
    )
    for i, line in enumerate(_linelist(record), 1):
        m = pattern.search(line)
        if m is None:
            continue
        cited_n = int(m.group(2))
        lines = _linelist(cited)
        loc = f"{record.name}:{i}"
        assert 1 <= cited_n <= len(lines), (
            f"{loc} cites and :{cited_n} but {cited.name} has "
            f"{len(lines)} lines — update {loc}"
        )
        assert needle in lines[cited_n - 1], (
            f"{loc} cites and :{cited_n} but that line is "
            f"{lines[cited_n - 1]!r}, expected {needle!r} — update {loc}"
        )
        return
    raise AssertionError(
        f"{record.name} has no '{after_token}:N and :M' continuation citation"
    )


# ---------------------------------------------------------------------------
# BLOCKER-1 — DSC claim is recorded-adverse prose, not UNRULED
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
    assert "research/MASTERMIND_DATA_CONTRACTS.md:" in verified
    assert "research/IMCE_ROUND3_ARCHITECTURE_FREEZE_BY_FABLE.md:" in verified
    assert "config/dataset_registry.yml:" in verified
    _assert_record_citation_resolves(
        DSC_PATH,
        CONTRACTS,
        "research/MASTERMIND_DATA_CONTRACTS.md",
        "yfinance-sourced and republished to a paid product",
    )
    _assert_record_citation_resolves(
        DSC_PATH,
        IMCE,
        "research/IMCE_ROUND3_ARCHITECTURE_FREEZE_BY_FABLE.md",
        "CANONICAL_PRICE_TAPE (REUSE; yfinance exposure documented in-repo)",
    )
    _assert_record_citation_resolves(
        DSC_PATH,
        REGISTRY,
        "config/dataset_registry.yml",
        "licensing: vendor_terms_personal_use",
    )


def test_dsc_so_what_types_spine_rights_blocked() -> None:
    text = _text(DSC_PATH)
    so_what = text.split("so_what:", 1)[1].split("kind:", 1)[0]
    assert "rights_blocked" in so_what
    assert "recorded basis" in so_what
    assert "`unknown`" in so_what
    assert "unrecorded" in so_what
    assert "recorded-and-adverse" not in so_what
    assert "underlying Yahoo vendor terms text was not read" in so_what


def test_dsc_confidence_is_probable() -> None:
    text = _text(DSC_PATH)
    conf = next(
        line for line in text.splitlines() if line.startswith("confidence:")
    )
    assert conf.strip() == "confidence: probable"


def test_yahoo_registry_row_is_personal_use_vendor_terms() -> None:
    """Ground the DSC in the live registry, not in a self-citation."""
    _assert_present(REGISTRY, "vendor: yahoo")
    _assert_present(REGISTRY, "licensing: vendor_terms_personal_use")
    _assert_record_citation_resolves(
        DSC_PATH,
        REGISTRY,
        "config/dataset_registry.yml",
        "licensing: vendor_terms_personal_use",
    )
    _assert_and_continuation_resolves(
        DSC_PATH,
        REGISTRY,
        "config/dataset_registry.yml",
        "licensing: vendor_terms_personal_use",
    )


def test_data_contracts_record_paid_republication_of_yfinance() -> None:
    _assert_present(CONTRACTS, "yfinance-sourced and republished to a paid product")
    _assert_present(CONTRACTS, "licensing: vendor_terms_personal_use")
    _assert_record_citation_resolves(
        DSC_PATH,
        CONTRACTS,
        "research/MASTERMIND_DATA_CONTRACTS.md",
        "yfinance-sourced and republished to a paid product",
    )
    _assert_record_citation_resolves(
        DSC_PATH,
        CONTRACTS,
        "research/MASTERMIND_DATA_CONTRACTS.md",
        "licensing: vendor_terms_personal_use",
    )


def test_imce_canonical_price_tape_documents_yfinance_exposure() -> None:
    needle = "CANONICAL_PRICE_TAPE (REUSE; yfinance exposure documented in-repo)"
    _assert_present(IMCE, needle)
    _assert_record_citation_resolves(
        DSC_PATH,
        IMCE,
        "research/IMCE_ROUND3_ARCHITECTURE_FREEZE_BY_FABLE.md",
        needle,
    )


# ---------------------------------------------------------------------------
# BLOCKER-2 — FRED legs are rights_blocked by clause (q), not unknown
# ---------------------------------------------------------------------------


def test_imce_fred_clause_q_is_do_not_ingest() -> None:
    _assert_present(IMCE, "FRED = DO_NOT_INGEST")
    _assert_present(IMCE, "Prohibition (q)")
    _assert_present(IMCE, "storing/caching/archiving FRED content")
    clause_q = (
        "DO_NOT_INGEST — FRED_API_SITE (clause (q): no store/cache/archive/database "
        "incorporation; binds all use classes)"
    )
    _assert_present(IMCE, clause_q)
    _assert_record_citation_resolves(
        F01,
        IMCE,
        "IMCE_ROUND3_ARCHITECTURE_FREEZE_BY_FABLE.md",
        "FRED = DO_NOT_INGEST",
    )
    _assert_record_citation_resolves(
        F01,
        IMCE,
        "IMCE_ROUND3_ARCHITECTURE_FREEZE_BY_FABLE.md",
        clause_q,
    )


def test_fred_legs_are_stored_fred_content() -> None:
    _assert_present(FOREX_INPUTS, "fx_rates_short")
    _assert_present(FOREX_INPUTS, "fx_rates_long")
    _assert_present(FOREX_INPUTS, "fx_reer")
    fred_adapter = '("fred", "collectors.fred", "FredAdapter")'
    _assert_present(COLLECT, fred_adapter)
    _assert_record_citation_resolves(
        F01,
        FOREX_INPUTS,
        "engine/forex_inputs.py",
        "fx_rates_short",
    )
    _assert_record_citation_resolves(
        F01,
        COLLECT,
        "scripts/collect.py",
        fred_adapter,
    )


def test_f01_fred_rows_are_rights_blocked_clause_q() -> None:
    text = _text(F01)
    assert text.count(FRED_BLOCKED) >= 5
    assert "IMCE binds" in text or "IMCE freeze binds" in text
    assert "unreconciled practice" in text
    inventory = text.split("## 3.")[0]
    for needle in (
        "| policy/short rates |",
        "| long rates |",
        "| REER |",
    ):
        row = next(line for line in inventory.splitlines() if line.startswith(needle))
        assert FRED_BLOCKED in row, f"{needle} is not typed rights_blocked: {row}"
        assert "unknown (rights-posture-unrecorded)" not in row


def test_f01_v2_cites_imce_111_and_189() -> None:
    text = _text(F01)
    v2 = text.split("**V-2 basis", 1)[1].split("**V-3", 1)[0]
    assert "IMCE_ROUND3_ARCHITECTURE_FREEZE_BY_FABLE.md:" in v2
    assert "DO_NOT_INGEST" in v2
    assert "clause (q)" in v2
    assert "scripts/collect.py:" in v2
    assert "underlying FRED terms text has not been re-read" in v2
    _assert_record_citation_resolves(
        F01,
        COLLECT,
        "scripts/collect.py",
        '("fred", "collectors.fred", "FredAdapter")',
    )


def test_f01_section7_does_not_certify_fred_as_unknown() -> None:
    closure = _text(F01).split("## 7. Ledger closure statement", 1)[1]
    assert FRED_BLOCKED in closure
    assert "the IMCE freeze binds the rights reading" in closure
    assert f"Yahoo typed `{YAHOO_BLOCKED}`" in closure
    assert "recorded-and-adverse" not in closure
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


def test_f01_headline_types_yahoo_rights_blocked_on_registry_basis() -> None:
    headline = _text(F01).split("## 2.")[0]
    assert "no rights ruling" not in headline
    assert "vendor_terms_personal_use" in headline
    assert YAHOO_BLOCKED in headline
    assert "the registry row is the ruling" not in headline
    assert "underlying Yahoo vendor terms text was not read" in headline
    assert "recorded-and-adverse" not in headline


def test_f01_section0_has_no_seventh_taxonomy_state() -> None:
    section0 = _text(F01).split("## 1.")[0]
    assert "| `recorded-and-adverse` |" not in section0
    for state in (
        "`unknown`",
        "`not_yet_available`",
        "`stale`",
        "`source_failed`",
        "`rights_blocked`",
        "`measured-zero`",
    ):
        assert state in section0
    assert section0.count("| `") == 6


def test_f01_yahoo_inventory_rows_use_existing_taxonomy() -> None:
    text = _text(F01)
    inventory = text.split("## 4.")[0]
    for needle in (
        "| FX spot & DXY",
        "| commodity futures/spot closes |",
    ):
        row = next(line for line in inventory.splitlines() if line.startswith(needle))
        assert YAHOO_BLOCKED in row, f"{needle} is not typed rights_blocked: {row}"
        assert "recorded-and-adverse" not in row


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
    spr_read = 'store.read("eia", "spr_stocks")'
    _assert_present(BUILD_SPR, spr_read)
    _assert_record_citation_resolves(
        F01,
        BUILD_SPR,
        "scripts/build_spr.py",
        spr_read,
    )


# ---------------------------------------------------------------------------
# MINOR-3 — charter names master_switch_frame, not Gate-1
# ---------------------------------------------------------------------------


def test_charter_names_master_switch_frame() -> None:
    text = _text(CHARTER)
    acceptance = text.split("## 2. The one-line distinction", 1)[1].split("## 3.", 1)[0]
    assert "FED-PUT MASTER SWITCH" in acceptance
    assert "master_switch_frame" in acceptance
    assert "Gate-1 switch" not in acceptance
    _assert_present(DISLOCATION, "def master_switch_frame(")
    _assert_present(DISLOCATION, "FED-PUT MASTER SWITCH:")
    _assert_record_citation_resolves(
        CHARTER,
        DISLOCATION,
        "engine/dislocation.py",
        "def master_switch_frame(",
    )
    assert "recorded-and-adverse" not in text

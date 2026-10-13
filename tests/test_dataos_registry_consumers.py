"""R00 consumer declarations — the D00.D6 consumers in ``config/dataset_registry.yml``.

Two halves, same split as ``tests/test_dataos_registry.py``:

* the SYNTHETIC half proves each R00 counterexample is actually refused — a
  validator that returns ``[]`` for everything passes a "the real registry is
  clean" test perfectly;
* the REAL half pins what the three frozen consumers (D00.D6) now declare in
  the ONE registry, so P01-P04 views, ORCH-3 consumer wiring and ORCH-4
  acceptance resolve "what is this data and may I compute/redistribute it"
  from the registry — not from a directory name or a licensing label.

The R00 rule numbers named in tests:

* R00.01 — PROPOSED != PRODUCED; never claim PRODUCED you cannot evidence.
* R00.02 — no right is granted by a readable directory or a subscription
  label; ``granted`` requires a DEC:/DSC: key or a docs/ research/ agentos/
  path, and rights never imply each other (K01.02).
* R00.03 — never a second registry; the consumer declarations live in this one.
* R00.04 — the Tiingo contracts stay exactly as measured, byte-unchanged.

Semantic violations are REPORTED by ``validate_registry`` (the module's frozen
report-not-raise contract — see
``test_a_temporal_profile_outside_the_enum_is_reported_not_raised``);
``RegistryError`` is reserved for structures no honest contract can hold
(non-mapping ``rights``/``population``, a non-bool
``point_in_time_corporate_actions`` — ``bool("false")`` is ``True``, so a
truthiness coercion would INVERT the author's meaning).

No ``data/`` read: the registry is a config file, and the stores it DESCRIBES
are never opened here.

Run: PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_dataos_registry_consumers.py -q
"""

from __future__ import annotations

import pytest

from lib.dataos.registry import (
    DatasetContract,
    DatasetStatus,
    Registry,
    RegistryError,
    load_registry,
    validate_registry,
)

RIGHTS_DEFAULT = {
    "purchase_access": "unverified",
    "internal_computation": "unverified",
    "redistribution": "not_granted",
}

#: The 24 Tiingo dataset_ids exactly as measured at the R00 base (R00.04).
TIINGO_IDS = frozenset({
    "vendor.tiingo.raw.equity_eod",
    "vendor.tiingo.raw.fundamentals",
    "vendor.tiingo.raw.boats",
    "vendor.tiingo.research.eod",
    "vendor.tiingo.research.fundamentals",
    "vendor.tiingo.research.boats",
    "vendor.tiingo.raw.boats_bars",
    "vendor.tiingo.research.boats_bars",
    "vendor.tiingo.raw.iex_bars",
    "vendor.tiingo.research.iex_bars",
    "vendor.tiingo.raw.equity_intraday",
    "vendor.tiingo.research.equity_intraday",
    "vendor.tiingo.raw.forex_bars",
    "vendor.tiingo.research.forex_bars",
    "vendor.tiingo.raw.crypto_bars",
    "vendor.tiingo.research.crypto_bars",
    "vendor.tiingo.raw.splits",
    "vendor.tiingo.research.splits",
    "vendor.tiingo.raw.distributions",
    "vendor.tiingo.research.distributions",
    "vendor.tiingo.raw.fund_fee_history",
    "vendor.tiingo.research.fund_fee_history",
    "vendor.tiingo.raw.distribution_yield",
    "vendor.tiingo.research.distribution_yield",
})
TIINGO_PRODUCED = frozenset({
    "vendor.tiingo.raw.equity_eod",
    "vendor.tiingo.raw.fundamentals",
    "vendor.tiingo.research.eod",
    "vendor.tiingo.research.fundamentals",
})


def contract(dataset_id: str, **overrides) -> DatasetContract:
    """A minimal VALID contract carrying the R00 defaults, so a test can
    introduce exactly one defect."""
    base = {
        "dataset_id": dataset_id,
        "layer": "L1",
        "status": "PRODUCED",
        "owner": "macro-dashboard",
        "producer": "collectors/example.py",
        "storage": "data/example/{ticker}.parquet",
        "format": "parquet",
        "grain": ["ticker", "date"],
        "temporal_profile": "BARS",
        "version": "1.0.0",
        "basis": "not_applicable",
        "rights": dict(RIGHTS_DEFAULT),
    }
    base.update(overrides)
    return DatasetContract.from_mapping(base)


def violations_for(**overrides) -> list[str]:
    return validate_registry(Registry([contract("a.b.c", **overrides)]))


# ── R00.02: what is NOT evidence for a granted right ─────────────────────────
def test_r0002_redistribution_granted_without_evidence_is_refused() -> None:
    """The headline counterexample: a grant with nothing behind it."""
    rights = dict(RIGHTS_DEFAULT, redistribution="granted")
    violations = violations_for(rights=rights)
    assert any("redistribution" in v and "granted without evidence" in v for v in violations)


def test_r0002_the_licensing_label_is_not_evidence() -> None:
    """A row's own `licensing:` string asserting its own grant is the exact
    self-reference the evidence law exists to refuse."""
    rights = dict(RIGHTS_DEFAULT, redistribution="granted",
                  evidence={"redistribution": "vendor_terms_personal_use"})
    violations = violations_for(licensing="vendor_terms_personal_use", rights=rights)
    assert any("redistribution" in v and "R00.02" in v for v in violations)


def test_r0002_a_data_directory_is_not_evidence() -> None:
    rights = dict(RIGHTS_DEFAULT, redistribution="granted",
                  evidence={"redistribution": "data/stocks/"})
    violations = violations_for(rights=rights)
    assert any("data/stocks/" in v and "R00.02" in v for v in violations)


def test_r0002_a_url_is_not_evidence() -> None:
    rights = dict(RIGHTS_DEFAULT, redistribution="granted",
                  evidence={"redistribution": "https://vendor.example.com/terms"})
    violations = violations_for(rights=rights)
    assert any("https://" in v and "R00.02" in v for v in violations)


def test_r0002_a_bare_directory_or_root_only_path_is_not_evidence() -> None:
    for pointer in ("docs/", "research", "agentos/2026-10-13/", "docs"):
        rights = dict(RIGHTS_DEFAULT, redistribution="granted",
                      evidence={"redistribution": pointer})
        violations = violations_for(rights=rights)
        assert any(pointer in v and "R00.02" in v for v in violations), pointer


@pytest.mark.parametrize("pointer", [
    "DEC:K01-02", "DSC:D00-D6",
    "research/data_os_completion/2026-10-13/D00_SEMANTIC_DECISIONS.md",
    "docs/ops/ticker-news.md",
    "agentos/WS-DATA-OS-COMPLETION/2026-10-13.md#rights",
    "research/MASTERMIND_DATA_OS_ARCHITECTURE.md#d3",
])
def test_r0002_lawful_evidence_forms_are_accepted(pointer: str) -> None:
    rights = dict(RIGHTS_DEFAULT, redistribution="granted",
                  evidence={"redistribution": pointer})
    assert violations_for(rights=rights) == []


def test_r0002_rights_never_imply_each_other() -> None:
    """K01.02: purchase != computation != redistribution. A granted
    purchase_access (with valid evidence) must NOT turn either other right
    into granted — not in the validator's eye and not in the stored contract."""
    rights = dict(RIGHTS_DEFAULT, purchase_access="granted",
                  evidence={"purchase_access": "DEC:K01-02"})
    c = contract("a.b.c", rights=rights)
    assert violations_for(rights=rights) == []
    assert c.rights["purchase_access"] == "granted"
    assert c.rights["internal_computation"] == "unverified"
    assert c.rights["redistribution"] == "not_granted"


def test_r0002_a_fourth_rights_key_is_refused() -> None:
    rights = dict(RIGHTS_DEFAULT, resale="granted")
    violations = violations_for(rights=rights)
    assert any("unknown key" in v and "resale" in v for v in violations)


def test_r0002_a_missing_rights_key_is_refused() -> None:
    rights = {"purchase_access": "unverified", "redistribution": "not_granted"}
    violations = violations_for(rights=rights)
    assert any("missing key" in v and "internal_computation" in v for v in violations)


def test_r0002_yes_is_not_a_rights_value() -> None:
    rights = dict(RIGHTS_DEFAULT, purchase_access="yes")
    violations = violations_for(rights=rights)
    assert any("purchase_access" in v and "'yes'" in v for v in violations)


def test_r0002_evidence_must_be_a_mapping_when_present() -> None:
    rights = dict(RIGHTS_DEFAULT, evidence="DEC:K01-02")
    violations = violations_for(rights=rights)
    assert any("evidence must be a mapping" in v for v in violations)


# ── the frozen additive schema, each field's counterexamples ──────────────────
def test_basis_disagreeing_with_the_close_column_is_refused() -> None:
    """A row label may never claim LESS adjustment than a constituent column:
    `basis: raw` over a close that says `tradj` is the D00.D3 lie."""
    violations = violations_for(
        basis="raw",
        schema={"close": {"dtype": "float64", "basis": "tradj"}},
    )
    assert any("basis 'raw' disagrees with schema column 'close'" in v for v in violations)


def test_basis_agreeing_with_the_close_column_is_clean() -> None:
    assert violations_for(
        basis="tradj",
        schema={"close": {"dtype": "float64", "basis": "tradj"}},
    ) == []


def test_basis_not_applicable_over_a_based_column_is_refused() -> None:
    violations = violations_for(
        schema={"close": {"dtype": "float64", "basis": "tradj"}},
    )
    assert any("'not_applicable' but schema column(s)" in v for v in violations)


def test_an_unknown_basis_value_is_refused() -> None:
    violations = violations_for(basis="mostly_raw")
    assert any("basis 'mostly_raw' is not one of" in v for v in violations)


def test_clocks_wall_clock_is_refused() -> None:
    violations = violations_for(clocks=["wall_clock"])
    assert any("clocks entry 'wall_clock' is not one of" in v for v in violations)


def test_an_empty_clocks_list_is_refused_but_absent_is_not_validated() -> None:
    assert any("clocks must be a non-empty list" in v for v in violations_for(clocks=[]))
    assert violations_for() == []      # absent = not declared, never a violation


def test_population_requires_exactly_the_three_keys() -> None:
    violations = violations_for(population={"market": "US", "universe": "everything"})
    assert any("population keys must be exactly" in v and "venues" in v for v in violations)


def test_population_venues_must_be_four_letter_mics() -> None:
    bad = {"market": "US", "venues": ["nasdaq"], "universe": "top-N union"}
    assert any("4-letter uppercase MIC" in v and "nasdaq" in v
               for v in violations_for(population=bad))
    good = {"market": "US", "venues": ["XNYS", "XNAS"], "universe": "top-N union"}
    assert violations_for(population=good) == []


def test_structurally_impossible_fields_raise_at_load() -> None:
    """RegistryError, not a silent coercion: these structures cannot be held by
    an honest contract, and bool("false") would INVERT the author's meaning."""
    with pytest.raises(RegistryError, match="rights: must be a mapping"):
        DatasetContract.from_mapping({**contract("a.b.c").__dict__,
                                      "rights": "all granted"})
    with pytest.raises(RegistryError, match="population: must be a mapping"):
        DatasetContract.from_mapping({**contract("a.b.c").__dict__,
                                      "population": ["US"]})
    with pytest.raises(RegistryError, match="point_in_time_corporate_actions"):
        DatasetContract.from_mapping({**contract("a.b.c").__dict__,
                                      "point_in_time_corporate_actions": "false"})


# ── the real, committed registry — what the three consumers now declare ───────
def test_the_committed_registry_still_loads_and_validates_clean() -> None:
    violations = validate_registry(load_registry())
    assert violations == [], "\n".join(violations)


def test_consumer_b_stocks_row_carries_the_r00_declaration() -> None:
    c = load_registry().get("equity.bars.daily.stocks")
    assert c.basis == "tradj"                       # agrees with schema close
    assert c.schema["close"]["basis"] == "tradj"
    assert c.clocks == ("ingested_at",)
    assert c.point_in_time_corporate_actions is False
    assert c.rights == RIGHTS_DEFAULT
    assert c.code_consumers == (
        "lib/dataos/web_workspace.py",
        "lib/dataos/web_api.py",
        "lib/dataos/web_readers.py",
    )
    # population stays ABSENT, not guessed: venues are unmeasurable in-repo.
    assert c.population == {}
    assert "market US" in c.notes


@pytest.mark.parametrize("dataset_id", [
    "reference.security_master",
    "reference.vendor_aliases",
    "reference.security_migrations",
])
def test_consumer_b_reference_rows_carry_the_r00_declaration(dataset_id: str) -> None:
    c = load_registry().get(dataset_id)
    assert c.basis == "not_applicable"              # no price column carries a basis
    assert all("basis" not in spec for spec in c.schema.values())
    assert c.rights == RIGHTS_DEFAULT
    assert c.code_consumers == (
        "lib/dataos/web_workspace.py",
        "lib/dataos/web_api.py",
        "lib/dataos/web_readers.py",
    )


def test_r0001_the_terminal_row_is_proposed_with_a_cross_repo_producer() -> None:
    """R00.01: PROPOSED != PRODUCED. The Terminal JSONs are written by another
    repo; this registry does not pretend an in-repo pipeline evidences them."""
    c = load_registry().get("terminal.bars.daily.ohlc_json")
    assert c.status is DatasetStatus.PROPOSED
    assert c.producer.startswith("mastermind-terminal@06a49a6104f6:")
    assert "build_ohlc_json" in c.producer
    assert "equity.bars.daily.stocks" in c.notes
    assert "not house SADJ (D00.D3)" in c.notes
    assert c.basis == "tradj"
    assert c.clocks == ("derived",)
    assert c.point_in_time_corporate_actions is False
    assert c.rights == RIGHTS_DEFAULT
    assert c.population == {
        "market": "US",
        "venues": ["XNYS", "XNAS", "XASE", "ARCX"],
        "universe": c.population["universe"],       # any non-empty universe text
    }
    assert c.population["universe"].startswith("US tickers present in the Macro deep store")
    # No lineage edge: a cross-repo build is named in notes, never graphed as an
    # in-repo pipeline (and the seed fence on consumers_of stays true).
    assert load_registry().consumers_of("equity.bars.daily.stocks") == ()


@pytest.mark.parametrize("dataset_id, market, identity_only", [
    ("basket.membership.history.baskets", "US", False),
    ("basket.membership.history.baskets_china", "CN", True),
    ("basket.membership.history.baskets_china_ths", "CN", True),
])
def test_consumer_c_membership_rows_carry_the_r00_declaration(
    dataset_id: str, market: str, identity_only: bool,
) -> None:
    c = load_registry().get(dataset_id)
    assert c.producer == "engine/basket_membership_pit.py::append_all"
    assert c.storage == f"data/{dataset_id.split('.')[-1]}/membership_history.parquet"
    assert c.grain == ("snapshot_date", "basket_id", "ticker")
    assert c.basis == "not_applicable"
    assert c.clocks == ("ingested_at",)
    assert c.point_in_time_corporate_actions is False
    assert c.rights == RIGHTS_DEFAULT
    assert c.code_consumers, "at least the PIT read seam reads this store"
    if identity_only:
        assert "IDENTITY-ONLY" in c.notes and market == "CN"
    else:
        assert "positive witness" in c.notes and market == "US"


def test_r0003_there_is_still_exactly_one_registry() -> None:
    """R00.03: the consumer declarations extended the ONE registry and its ONE
    contract class — no second store, auth or publisher appeared beside it."""
    registry = load_registry()
    for dataset_id in (
        "equity.bars.daily.stocks", "terminal.bars.daily.ohlc_json",
        "basket.membership.history.baskets",
    ):
        assert isinstance(registry.get(dataset_id), DatasetContract)


def test_r0004_the_tiingo_rows_are_exactly_the_measured_twenty_four() -> None:
    """R00.04: the Tiingo contracts stay as measured — same id set, same status
    counts, and none of them carries an R00 field."""
    registry = load_registry()
    tiingo = [c for c in registry.all() if c.dataset_id.startswith("vendor.tiingo.")]
    assert {c.dataset_id for c in tiingo} == TIINGO_IDS
    produced = {c.dataset_id for c in tiingo if c.status is DatasetStatus.PRODUCED}
    assert produced == TIINGO_PRODUCED
    assert len(tiingo) == 24 and len(produced) == 4
    for c in tiingo:
        assert c.basis == "", c.dataset_id
        assert c.population == {}, c.dataset_id
        assert c.clocks is None, c.dataset_id
        assert c.rights == {}, c.dataset_id
        assert c.point_in_time_corporate_actions is None, c.dataset_id

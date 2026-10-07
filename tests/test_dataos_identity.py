"""Identity spine contracts (Data OS §D2) — ``lib/dataos/identity.py``.

The regression this suite exists for is the MMC->MRSH rename recorded in
``lib/ticker_aliases.py``: a timeless two-entry alias dict living in one collector
and not its sibling left ``data/baskets/ohlcv/MMC.parquet`` nonexistent for seven
months, and the `insurance` basket rendered 18/19 members with nothing going red.
``test_alias_table_answers_differently_either_side_of_the_mmc_rename`` is that
incident, pinned.

Pure unit tests: no ``data/`` read anywhere, so the suite is identical on a full
checkout and in a thin CI lane.

Run: .venv/bin/python -m pytest tests/test_dataos_identity.py -q
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from lib.dataos.identity import (
    BATS,
    XASE,
    XBSE,
    XHKG,
    XNAS,
    XNYS,
    XSHE,
    XSHG,
    XTSE,
    XTSX,
    AliasRow,
    CNBoard,
    IdentityError,
    IssuerMaster,
    KNOWN_MICS,
    ARCX,
    ListingKey,
    SecurityIssuerRow,
    VendorAliasTable,
    cn_board,
    fx_id,
    future_id,
    index_id,
    issuer_id,
    listing_id,
    normalize_cn_symbol,
    normalize_hk_symbol,
    option_contract_id,
    parse_fx_id,
    parse_future_id,
    parse_id,
    parse_index_id,
    parse_listing_key,
    parse_option_contract_id,
    security_id,
)

MMC = ListingKey("US", XNYS, "MMC")
AAPL = ListingKey("US", XNAS, "AAPL")
MAOTAI = ListingKey("CN", XSHG, "600519")
TENCENT = ListingKey("HK", XHKG, "00700")


# ── listing keys ─────────────────────────────────────────────────────────────
def test_the_admitted_venues_are_all_known() -> None:
    assert KNOWN_MICS == {BATS, XNYS, XNAS, XASE, ARCX, XSHG, XSHE, XBSE, XHKG, XTSE, XTSX}
    assert ListingKey("US", BATS, "CBOE").render() == "US-BATS-CBOE"


@pytest.mark.parametrize(
    "key, rendered",
    [
        (MMC, "US-XNYS-MMC"),
        (ListingKey("US", XNYS, "MMC", 2), "US-XNYS-MMC.2"),
        (MAOTAI, "CN-XSHG-600519"),
        (ListingKey("CN", XSHE, "000001"), "CN-XSHE-000001"),
        (ListingKey("CN", XBSE, "920163"), "CN-XBSE-920163"),
        (TENCENT, "HK-XHKG-00700"),
        (ListingKey("US", XNYS, "BRK-B"), "US-XNYS-BRK-B"),
        (ListingKey("US", XNYS, "BRK.B"), "US-XNYS-BRK.B"),
    ],
)
def test_listing_key_round_trips_through_its_rendered_form(key: ListingKey, rendered: str) -> None:
    assert key.render() == rendered
    assert parse_listing_key(rendered) == key


def test_a_dotted_class_suffix_is_not_read_as_a_disambiguator() -> None:
    """``BRK.B`` is a share class; only a ``.<digits>`` tail is the collision suffix."""
    assert parse_listing_key("US-XNYS-BRK.B").code == "BRK.B"
    assert parse_listing_key("US-XNYS-BRK.B").disambiguator is None
    assert parse_listing_key("US-XNYS-MMC.2").disambiguator == 2


@pytest.mark.parametrize(
    "bad",
    ["", "MMC", "US-MMC", "US-XNYS-", "-XNYS-MMC", "USA-XNYS-MMC", "us-XXXX-MMC"],
)
def test_malformed_listing_keys_raise_rather_than_degrade(bad: str) -> None:
    with pytest.raises(IdentityError):
        parse_listing_key(bad)


def test_disambiguator_one_is_refused_as_a_second_spelling_of_the_first_listing() -> None:
    with pytest.raises(IdentityError):
        ListingKey("US", XNYS, "MMC", 1)


def test_an_unknown_mic_is_refused_because_the_venue_list_is_closed() -> None:
    with pytest.raises(IdentityError):
        ListingKey("US", "XXXX", "MMC")


# ── issuer / security / listing ids ──────────────────────────────────────────
def test_the_three_id_forms_round_trip_and_carry_a_visible_kind() -> None:
    assert security_id(MMC) == "SEC:US-XNYS-MMC"
    assert issuer_id(MMC) == "ISS:US-XNYS-MMC"
    assert listing_id(MMC) == "US-XNYS-MMC"
    assert parse_id("SEC:US-XNYS-MMC") == ("security", MMC)
    assert parse_id("ISS:US-XNYS-MMC") == ("issuer", MMC)
    assert parse_id("US-XNYS-MMC") == ("listing", MMC)


def test_ids_accept_a_rendered_key_as_well_as_the_object() -> None:
    assert security_id("CN-XSHG-600519") == security_id(MAOTAI)


def test_parse_id_refuses_an_instrument_class_id_instead_of_half_answering() -> None:
    """``OPT:``/``FUT:``/``IDX:``/``FX:`` are not listing keys; a half-truth here is
    how a concept confusion reaches a store."""
    for other in ("OPT:US-XNAS-AAPL:20260918:C:00250000", "FUT:XCBF:VX:202609",
                  "IDX:SPDJI-SPX", "FX:USDCNH"):
        with pytest.raises(IdentityError):
            parse_id(other)


def test_the_id_survives_the_rename_that_motivates_the_project() -> None:
    """MMC->MRSH changed the symbol, not the listing: the id is the INCEPTION code."""
    assert security_id(MMC) == "SEC:US-XNYS-MMC"
    assert security_id(ListingKey("US", XNAS, "FISV")) == "SEC:US-XNAS-FISV"


# ── option contract ids ──────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "strike, encoded",
    [
        ("250", "00250000"),
        ("250.50", "00250500"),      # fractional strike — the float-corruption case
        (Decimal("250.50"), "00250500"),
        ("4000", "04000000"),        # high strike
        ("0.125", "00000125"),       # sub-dollar, tenth-of-a-cent
        ("99999.999", "99999999"),   # the top of the 8-digit field
    ],
)
def test_option_contract_id_scales_the_strike_by_1000_into_eight_digits(
    strike, encoded: str
) -> None:
    oid = option_contract_id(AAPL, date(2026, 9, 18), "C", strike)
    assert oid == f"OPT:US-XNAS-AAPL:20260918:C:{encoded}"
    underlying, expiry, right, parsed_strike = parse_option_contract_id(oid)
    assert (underlying, expiry, right) == (AAPL, date(2026, 9, 18), "C")
    assert parsed_strike == Decimal(str(strike))


def test_option_contract_id_matches_the_spec_example() -> None:
    assert option_contract_id(AAPL, date(2026, 9, 18), "C", "250") == \
        "OPT:US-XNAS-AAPL:20260918:C:00250000"


def test_a_put_round_trips_too() -> None:
    oid = option_contract_id(AAPL, date(2026, 1, 16), "P", "175.25")
    assert oid == "OPT:US-XNAS-AAPL:20260116:P:00175250"
    assert parse_option_contract_id(oid)[2] == "P"


def test_a_float_strike_is_refused_because_binary_float_silently_mints_another_contract() -> None:
    with pytest.raises(IdentityError, match="never float"):
        option_contract_id(AAPL, date(2026, 9, 18), "C", 250.10)


def test_a_strike_finer_than_a_tenth_of_a_cent_raises_instead_of_rounding() -> None:
    with pytest.raises(IdentityError):
        option_contract_id(AAPL, date(2026, 9, 18), "C", "250.0001")


@pytest.mark.parametrize(
    "bad",
    [
        "OPT:US-XNAS-AAPL:20260918:X:00250000",   # not a right
        "OPT:US-XNAS-AAPL:2026918:C:00250000",    # short date
        "OPT:US-XNAS-AAPL:20260918:C:250000",     # unpadded strike
        "OPT:US-XNAS-AAPL:20261332:C:00250000",   # impossible month/day
        "US-XNAS-AAPL:20260918:C:00250000",       # no OPT prefix
    ],
)
def test_malformed_option_ids_raise(bad: str) -> None:
    with pytest.raises(IdentityError):
        parse_option_contract_id(bad)


# ── other instrument classes ─────────────────────────────────────────────────
def test_future_index_and_fx_ids_round_trip() -> None:
    assert future_id("XCBF", "VX", "202609") == "FUT:XCBF:VX:202609"
    assert parse_future_id("FUT:XCBF:VX:202609") == ("XCBF", "VX", "202609")
    assert future_id("XCBF", "vx", date(2026, 9, 16)) == "FUT:XCBF:VX:202609"

    assert index_id("SPDJI", "SPX") == "IDX:SPDJI-SPX"
    assert parse_index_id("IDX:SPDJI-SPX") == ("SPDJI", "SPX")

    assert fx_id("USD", "CNH") == "FX:USDCNH"
    assert parse_fx_id("FX:USDCNH") == ("USD", "CNH")


def test_fx_refuses_a_pair_of_one_currency_and_futures_refuse_a_thirteenth_month() -> None:
    with pytest.raises(IdentityError):
        fx_id("USD", "USD")
    with pytest.raises(IdentityError):
        future_id("XCBF", "VX", "202613")


# ── China A-share normalization ──────────────────────────────────────────────
def test_the_measured_tushare_vs_repository_divergence_normalizes_to_one_key() -> None:
    """TuShare emits ``600519.SH``; the repository ticker is ``600519.SS``."""
    keys = {
        normalize_cn_symbol("600519.SH"),
        normalize_cn_symbol("600519.SS"),
        normalize_cn_symbol("600519"),
        normalize_cn_symbol(" 600519.ss "),
        normalize_cn_symbol("SH600519"),
    }
    assert keys == {MAOTAI}
    assert MAOTAI.render() == "CN-XSHG-600519"


@pytest.mark.parametrize(
    "symbol, mic, board",
    [
        ("920163", XBSE, CNBoard.BSE),          # BSE — spine contract's canonical 920xxx
        ("920163.BJ", XBSE, CNBoard.BSE),
        ("688981", XSHG, CNBoard.STAR),         # STAR on Shanghai
        ("689009.SH", XSHG, CNBoard.STAR),
        ("300750", XSHE, CNBoard.CHINEXT),      # ChiNext on Shenzhen
        ("309999.SZ", XSHE, CNBoard.CHINEXT),   # top of the official 300000-309999 range
        ("600519", XSHG, CNBoard.MAIN),
        ("000001.SZ", XSHE, CNBoard.MAIN),
        ("002594", XSHE, CNBoard.MAIN),
    ],
)
def test_board_and_venue_follow_the_cn_spine_contract_ranges(
    symbol: str, mic: str, board: CNBoard
) -> None:
    key = normalize_cn_symbol(symbol)
    assert key.country == "CN"
    assert key.mic == mic
    assert cn_board(key.code) is board


def test_a_declared_venue_that_contradicts_the_code_range_raises() -> None:
    """``600519.SZ`` is two facts that cannot both be true — refuse to pick one."""
    with pytest.raises(IdentityError, match="refusing to guess"):
        normalize_cn_symbol("600519.SZ")


# ── old BJ codes are ALIASES, and this module cannot resolve them ────────────
#: The spine contract, twice: "Old BJ codes remain aliases. Every canonical BSE
#: mapping target must be ``920xxx``" and "other admitted A code families are main
#: board" (research/CN_TUSHARE_FULL_A_SPINE_CONTRACT_2026-08-08.md:89-92).
LEGACY_BJ_CODES = ["430047", "833819", "871981", "838275", "400001", "420001"]


@pytest.mark.parametrize("code", LEGACY_BJ_CODES)
def test_an_old_bj_alias_code_is_refused_rather_than_minted_as_a_canonical_key(
    code: str,
) -> None:
    """THE DUPLICATE-IDENTITY BUG THIS MODULE EXISTS TO END, produced by the module.

    ``430047`` is a historical ALIAS of a BSE security whose canonical code is
    ``920163``. Minting ``CN-XBSE-430047`` from it gives that one security two
    identities — ``SEC:CN-XBSE-920163`` from the canonical feed and
    ``SEC:CN-XBSE-430047`` from a legacy TuShare pull — which join as two different
    securities in the security master and are never reconciled, because neither side
    is wrong on its face.

    This module carries NO ``bse_mapping`` table, so it has no authority to resolve
    an alias to its canonical code. Refusing is the fail-closed behaviour the rest of
    the file already uses; the resolution belongs to the alias table.
    """
    with pytest.raises(IdentityError, match="920"):
        normalize_cn_symbol(code)
    with pytest.raises(IdentityError, match="920"):
        cn_board(code)


@pytest.mark.parametrize("code", LEGACY_BJ_CODES)
def test_an_explicit_bj_suffix_does_not_buy_an_alias_code_a_canonical_key(
    code: str,
) -> None:
    """The declared-venue escape hatch must NOT reach here.

    ``normalize_cn_symbol`` trusts an explicit suffix when the code family is unknown
    (``inferred = declared``). That is right for an unrecognised family and WRONG
    here: the venue was never the doubt. ``430047.BJ`` says "this is on the BSE",
    which is true and does not make ``430047`` a canonical key.
    """
    with pytest.raises(IdentityError, match="920"):
        normalize_cn_symbol(f"{code}.BJ")
    with pytest.raises(IdentityError, match="920"):
        normalize_cn_symbol(f"BJ{code}")


def test_the_canonical_bse_code_family_still_normalizes() -> None:
    """The refusal above is scoped to the alias families; 920xxx is unaffected."""
    key = normalize_cn_symbol("920163")
    assert key.render() == "CN-XBSE-920163"
    assert cn_board("920163") is CNBoard.BSE
    assert normalize_cn_symbol("920163.BJ") == key


def test_the_cdr_range_stays_chinext_on_shenzhen() -> None:
    """The other half of the contract sentence, which was already right: the official
    SZ 300000-309999 allocation is ChiNext INCLUDING the 309800-309999 CDR range."""
    for code in ("309800", "309999"):
        assert normalize_cn_symbol(code).render() == f"CN-XSHE-{code}"
        assert cn_board(code) is CNBoard.CHINEXT


@pytest.mark.parametrize("bad", ["", "60051", "6005199", "ABCDEF", "600519.XX", "600519.HK"])
def test_unusable_cn_symbols_raise(bad: str) -> None:
    with pytest.raises(IdentityError):
        normalize_cn_symbol(bad)


# ── Hong Kong ────────────────────────────────────────────────────────────────
def test_every_hk_spelling_pads_to_the_exchanges_five_digit_code() -> None:
    assert normalize_hk_symbol("700") == normalize_hk_symbol("0700.HK")
    assert normalize_hk_symbol("700") == TENCENT
    assert {normalize_hk_symbol(s) for s in ("700", "0700", "00700", "0700.HK", "700.hk")} == {
        TENCENT
    }
    assert TENCENT.render() == "HK-XHKG-00700"


@pytest.mark.parametrize("bad", ["", "007000", "70A", "0700.SS"])
def test_unusable_hk_symbols_raise(bad: str) -> None:
    with pytest.raises(IdentityError):
        normalize_hk_symbol(bad)


# ── the vendor alias table — the MMC/MRSH regression ─────────────────────────
RENAME = date(2026, 1, 14)

#: The incident, as rows.  ``valid_to`` is EXCLUSIVE, which is what makes the
#: changeover day itself unambiguous.
MMC_ALIASES = [
    {"vendor": "yahoo", "vendor_symbol": "MMC", "security_id": "SEC:US-XNYS-MMC",
     "valid_from": None, "valid_to": "2026-01-14"},
    {"vendor": "yahoo", "vendor_symbol": "MRSH", "security_id": "SEC:US-XNYS-MMC",
     "valid_from": "2026-01-14", "valid_to": None},
    # Fiserv: the vendor LAGS the rename — Yahoo still serves the pre-rename symbol.
    {"vendor": "yahoo", "vendor_symbol": "FISV", "security_id": "SEC:US-XNAS-FISV",
     "valid_from": None, "valid_to": None},
]


def test_alias_table_answers_differently_either_side_of_the_mmc_rename() -> None:
    """THE regression test for the seven-month silent production loss.

    ``lib/ticker_aliases.py`` is timeless, so it can say "MMC means MRSH" but cannot
    say "MMC meant MMC before 2026-01-14".  A backfill reading history through a
    timeless map re-labels the past and nothing downstream can see it.
    """
    table = VendorAliasTable.from_records(MMC_ALIASES)
    day_before, day_of = date(2026, 1, 13), RENAME

    # forward: vendor symbol -> security
    assert table.resolve("yahoo", "MMC", day_before) == "SEC:US-XNYS-MMC"
    assert table.resolve("yahoo", "MMC", day_of) is None
    assert table.resolve("yahoo", "MRSH", day_before) is None
    assert table.resolve("yahoo", "MRSH", day_of) == "SEC:US-XNYS-MMC"

    # reverse: security -> what the vendor called it that day
    assert table.vendor_symbol_for("yahoo", "SEC:US-XNYS-MMC", day_before) == "MMC"
    assert table.vendor_symbol_for("yahoo", "SEC:US-XNYS-MMC", day_of) == "MRSH"
    assert table.vendor_symbol_for("yahoo", "SEC:US-XNYS-MMC", date(2026, 8, 12)) == "MRSH"


def test_the_lagging_rename_direction_is_the_same_table() -> None:
    """Fiserv renamed FISV->FI in 2023 and Yahoo still serves the OLD symbol."""
    table = VendorAliasTable.from_records(MMC_ALIASES)
    assert table.vendor_symbol_for("yahoo", "SEC:US-XNAS-FISV", date(2026, 8, 12)) == "FISV"


def test_an_unmapped_symbol_returns_none_rather_than_guessing_identity() -> None:
    table = VendorAliasTable.from_records(MMC_ALIASES)
    assert table.resolve("yahoo", "NVDA", RENAME) is None
    assert table.resolve("tushare", "MMC", date(2020, 1, 1)) is None


def test_an_overlapping_pair_of_rows_is_refused_at_construction() -> None:
    """A translation layer that can return either of two answers is not one."""
    with pytest.raises(IdentityError, match="ambiguous alias table"):
        VendorAliasTable.from_records([
            {"vendor": "yahoo", "vendor_symbol": "MMC", "security_id": "SEC:US-XNYS-MMC",
             "valid_from": None, "valid_to": "2026-02-01"},
            {"vendor": "yahoo", "vendor_symbol": "MMC", "security_id": "SEC:US-XNYS-OTHER",
             "valid_from": "2026-01-14", "valid_to": None},
        ])


def test_alias_rows_carry_half_open_intervals() -> None:
    row = AliasRow("yahoo", "MMC", "SEC:US-XNYS-MMC", None, RENAME)
    assert row.covers(date(2026, 1, 13))
    assert not row.covers(RENAME)          # valid_to is EXCLUSIVE
    assert row.covers(date(1990, 1, 1))    # open lower bound


def test_a_record_missing_a_required_column_raises_with_the_column_named() -> None:
    with pytest.raises(IdentityError, match="security_id"):
        VendorAliasTable.from_records([{"vendor": "yahoo", "vendor_symbol": "MMC"}])


# ── the issuer master reader — V4-D2B1 (§3 Reader API) ─────────────────────────
def test_issuer_master_finds_securities_of_a_shared_issuer() -> None:
    """The §9.7 canonical query, pure over a hand-built record set — GOOG/GOOGL."""
    im = IssuerMaster.from_records([
        {"security_id": "SEC:US-XNAS-GOOG", "issuer_id": "ISS:US-XNAS-GOOG",
         "issuer_state": "RESOLVED", "listing_key": "US-XNAS-GOOG"},
        {"security_id": "SEC:US-XNAS-GOOGL", "issuer_id": "ISS:US-XNAS-GOOG",
         "issuer_state": "RESOLVED", "listing_key": "US-XNAS-GOOGL"},
        {"security_id": "SEC:US-XNYS-MMC", "issuer_id": "ISS:US-XNYS-MMC",
         "issuer_state": "RESOLVED", "listing_key": "US-XNYS-MMC"},
    ])
    assert im.securities_of_issuer("ISS:US-XNAS-GOOG") == (
        "SEC:US-XNAS-GOOG", "SEC:US-XNAS-GOOGL",
    )
    assert im.securities_of_issuer("ISS:US-XNYS-MMC") == ("SEC:US-XNYS-MMC",)
    assert im.issuer_of_security("SEC:US-XNAS-GOOGL") == "ISS:US-XNAS-GOOG"
    assert im.issuer_of_security("SEC:US-XNAS-GOOG") == "ISS:US-XNAS-GOOG"


def test_issuer_master_answers_none_never_a_guess() -> None:
    im = IssuerMaster.from_records([
        {"security_id": "SEC:US-XNAS-AEP", "issuer_id": None,
         "issuer_state": "NO_ISSUER_EVIDENCE", "listing_key": "US-XNAS-AEP"},
    ])
    assert im.issuer_of_security("SEC:US-XNAS-AEP") is None
    assert im.issuer_of_security("SEC:UNKNOWN") is None
    assert im.securities_of_issuer("ISS:UNKNOWN") == ()
    # A null-issuer row is never indexed under any issuer_id.
    assert im.securities_of_issuer(None) == ()  # type: ignore[arg-type]


def test_issuer_master_from_records_is_nan_safe_without_pandas() -> None:
    """V4-D2B1 FIX 3 (M1): a ``pandas`` ``to_dict("records")`` round-trip can hand
    back a genuine ``float('nan')`` — never ``None`` — for a null cell in a nullable
    string column that also carries real strings.  ``lib/dataos/identity.py`` is
    stdlib-only (module docstring) and must catch this WITHOUT importing pandas; a
    NaN ``issuer_id`` must index as NO issuer, never the literal string ``'nan'``.
    """
    nan = float("nan")
    im = IssuerMaster.from_records([
        {"security_id": "SEC:US-XNAS-AEP", "issuer_id": nan,
         "issuer_state": nan, "listing_key": nan},
        {"security_id": "SEC:US-XNAS-GOOG", "issuer_id": "ISS:US-XNAS-GOOG",
         "issuer_state": "RESOLVED", "listing_key": "US-XNAS-GOOG"},
    ])
    assert im.issuer_of_security("SEC:US-XNAS-AEP") is None
    # The literal string 'nan' must never appear as a key or a matchable issuer id.
    assert im.securities_of_issuer("nan") == ()
    assert "nan" not in im._by_issuer  # noqa: SLF001 — pinning the index directly
    assert im.issuer_of_security("SEC:US-XNAS-GOOG") == "ISS:US-XNAS-GOOG"


def test_issuer_master_from_records_requires_security_id() -> None:
    with pytest.raises(IdentityError, match="security_id"):
        IssuerMaster.from_records([{"issuer_id": "ISS:US-XNYS-MMC"}])


def test_security_issuer_row_is_a_frozen_pure_value() -> None:
    row = SecurityIssuerRow(security_id="SEC:US-XNYS-MMC", issuer_id="ISS:US-XNYS-MMC",
                            issuer_state="RESOLVED", listing_key="US-XNYS-MMC")
    with pytest.raises(Exception):  # noqa: BLE001 — frozen dataclass raises FrozenInstanceError
        row.security_id = "SEC:US-XNYS-OTHER"  # type: ignore[misc]


# ── current issuer -> CIK seam — D5 prerequisite ─────────────────────────────
def test_issuer_master_issuer_cik_normalizes_to_the_exact_ten_digit_value() -> None:
    """The current Data OS reader exposes the master-backed CIK, not a new reader."""
    im = IssuerMaster.from_records([
        {"security_id": "SEC:US-XNAS-AAPL", "issuer_id": "ISS:US-XNAS-AAPL",
         "issuer_state": "RESOLVED", "issuer_cik": "320193", "listing_key": "US-XNAS-AAPL"},
    ])

    assert im.cik_of_issuer("ISS:US-XNAS-AAPL") == "0000320193"


def test_issuer_master_issuer_cik_accepts_repeated_current_rows_for_one_issuer() -> None:
    """Dual-class rows with the same evidenced CIK are one current issuer fact."""
    im = IssuerMaster.from_records([
        {"security_id": "SEC:US-XNAS-GOOG", "issuer_id": "ISS:US-XNAS-GOOG",
         "issuer_state": "RESOLVED", "issuer_cik": "0001652044", "listing_key": "US-XNAS-GOOG"},
        {"security_id": "SEC:US-XNAS-GOOGL", "issuer_id": "ISS:US-XNAS-GOOG",
         "issuer_state": "RESOLVED", "issuer_cik": "1652044", "listing_key": "US-XNAS-GOOGL"},
    ])

    assert im.cik_of_issuer("ISS:US-XNAS-GOOG") == "0001652044"


def test_issuer_master_issuer_cik_returns_none_for_absent_or_nan_observation() -> None:
    """Missing current CIK evidence is an unresolved bridge, never a guessed CIK."""
    nan = float("nan")
    im = IssuerMaster.from_records([
        {"security_id": "SEC:US-XNAS-AEP", "issuer_id": "ISS:US-XNAS-AEP",
         "issuer_state": "NO_ISSUER_EVIDENCE", "issuer_cik": None, "listing_key": "US-XNAS-AEP"},
        {"security_id": "SEC:US-XNAS-IBM", "issuer_id": "ISS:US-XNAS-IBM",
         "issuer_state": "NO_ISSUER_EVIDENCE", "issuer_cik": nan, "listing_key": "US-XNAS-IBM"},
    ])

    assert im.cik_of_issuer("ISS:US-XNAS-AEP") is None
    assert im.cik_of_issuer("ISS:US-XNAS-IBM") is None
    assert im.cik_of_issuer("ISS:UNKNOWN") is None


def test_issuer_master_issuer_cik_refuses_conflicting_current_observations() -> None:
    """An issuer mapping to two non-null current CIKs cannot lawfully pick either."""
    im = IssuerMaster.from_records([
        {"security_id": "SEC:US-XNAS-ONE", "issuer_id": "ISS:US-XNAS-ONE",
         "issuer_state": "RESOLVED", "issuer_cik": "0000320193", "listing_key": "US-XNAS-ONE"},
        {"security_id": "SEC:US-XNAS-TWO", "issuer_id": "ISS:US-XNAS-ONE",
         "issuer_state": "RESOLVED", "issuer_cik": "0000789019", "listing_key": "US-XNAS-TWO"},
    ])

    with pytest.raises(IdentityError, match="conflicting.*CIK"):
        im.cik_of_issuer("ISS:US-XNAS-ONE")


@pytest.mark.parametrize("bad_cik", ["", "cik:0000320193", "0000000000320193"])
def test_issuer_master_issuer_cik_refuses_malformed_source_evidence(bad_cik: str) -> None:
    """The source field is decimal CIK evidence, never an Earnings company id."""
    with pytest.raises(IdentityError, match="issuer CIK"):
        IssuerMaster.from_records([
            {"security_id": "SEC:US-XNAS-AAPL", "issuer_id": "ISS:US-XNAS-AAPL",
             "issuer_state": "RESOLVED", "issuer_cik": bad_cik,
             "listing_key": "US-XNAS-AAPL"},
        ])


def test_issuer_master_issuer_cik_direct_rows_normalize_before_lookup() -> None:
    """The public direct-row constructor has the same canonical output contract."""
    im = IssuerMaster([
        SecurityIssuerRow(
            security_id="SEC:US-XNAS-AAPL",
            issuer_id="ISS:US-XNAS-AAPL",
            issuer_state="RESOLVED",
            listing_key="US-XNAS-AAPL",
            issuer_cik="320193",
        ),
    ])

    assert im.rows[0].issuer_cik == "0000320193"
    assert im.cik_of_issuer("ISS:US-XNAS-AAPL") == "0000320193"


@pytest.mark.parametrize("bad_cik", ["", "cik:0000320193", "0000000000320193"])
def test_issuer_master_issuer_cik_direct_rows_refuse_malformed_evidence(bad_cik: str) -> None:
    row = SecurityIssuerRow(
        security_id="SEC:US-XNAS-AAPL",
        issuer_id="ISS:US-XNAS-AAPL",
        issuer_state="RESOLVED",
        listing_key="US-XNAS-AAPL",
        issuer_cik=bad_cik,
    )

    with pytest.raises(IdentityError, match="issuer CIK"):
        IssuerMaster([row])


def test_security_issuer_row_legacy_positional_optional_fields_remain_in_place() -> None:
    """Appending the CIK seam cannot reinterpret legacy security-axis arguments."""
    row = SecurityIssuerRow(
        "SEC:US-XNYS-VMRK",
        "ISS:US-XNYS-EQR",
        "RESOLVED",
        "US-XNYS-VMRK",
        "SUPERSEDED_DUPLICATE_MINT",
        "SEC:US-XNYS-EQR",
    )

    assert row.security_state == "SUPERSEDED_DUPLICATE_MINT"
    assert row.superseded_by == "SEC:US-XNYS-EQR"
    assert row.issuer_cik is None


# ── the security axis — V4-D2B1-R1 (§3.6 reader API) ───────────────────────────
def test_security_state_is_null_by_default_and_excluded_rows_never_aggregate() -> None:
    """A security-axis-superseded row (a tombstone) is excluded from
    ``securities_of_issuer`` by construction, even when hand-fed the SAME
    ``issuer_id`` as an active member — the exclusion is on ``security_state``, not
    on the issuer axis at all."""
    im = IssuerMaster.from_records([
        {"security_id": "SEC:US-XNYS-EQR", "issuer_id": "ISS:US-XNYS-EQR",
         "issuer_state": "RESOLVED", "listing_key": "US-XNYS-EQR",
         "security_state": None, "superseded_by": None},
        {"security_id": "SEC:US-XNYS-VMRK", "issuer_id": "ISS:US-XNYS-EQR",
         "issuer_state": "RESOLVED", "listing_key": "US-XNYS-VMRK",
         "security_state": "SUPERSEDED_DUPLICATE_MINT",
         "superseded_by": "SEC:US-XNYS-EQR"},
    ])
    assert im.securities_of_issuer("ISS:US-XNYS-EQR") == ("SEC:US-XNYS-EQR",)
    assert im.security_state_of("SEC:US-XNYS-VMRK") == "SUPERSEDED_DUPLICATE_MINT"
    assert im.superseded_by_of("SEC:US-XNYS-VMRK") == "SEC:US-XNYS-EQR"
    assert im.security_state_of("SEC:US-XNYS-EQR") is None
    assert im.superseded_by_of("SEC:US-XNYS-EQR") is None
    # Unknown security_id: both accessors answer None, never a raise or a guess.
    assert im.security_state_of("SEC:UNKNOWN") is None
    assert im.superseded_by_of("SEC:UNKNOWN") is None


def test_security_axis_absent_columns_default_to_active_era_seam() -> None:
    """A pre-V4-D2B1-R1 record (no security_state/superseded_by keys at all) reads as
    an ACTIVE row — the era seam, same law as the issuer axis's own pre-D2B1
    behaviour: an old record shape is 'not yet migrated', never a schema error."""
    im = IssuerMaster.from_records([
        {"security_id": "SEC:US-XNYS-AAPL", "issuer_id": "ISS:US-XNYS-AAPL",
         "issuer_state": "RESOLVED", "listing_key": "US-XNYS-AAPL"},
    ])
    assert im.security_state_of("SEC:US-XNYS-AAPL") is None
    assert im.superseded_by_of("SEC:US-XNYS-AAPL") is None
    assert im.securities_of_issuer("ISS:US-XNYS-AAPL") == ("SEC:US-XNYS-AAPL",)


def test_security_axis_from_records_is_nan_safe_without_pandas() -> None:
    """Same NaN-is-not-None trap as the issuer axis (FIX 3/M1) — a pandas
    ``to_dict('records')`` round-trip can hand back a genuine ``float('nan')`` for a
    null ``security_state``/``superseded_by`` cell, never the literal string 'nan'."""
    nan = float("nan")
    im = IssuerMaster.from_records([
        {"security_id": "SEC:US-XNYS-EQR", "issuer_id": "ISS:US-XNYS-EQR",
         "issuer_state": "RESOLVED", "listing_key": "US-XNYS-EQR",
         "security_state": nan, "superseded_by": nan},
    ])
    assert im.security_state_of("SEC:US-XNYS-EQR") is None
    assert im.superseded_by_of("SEC:US-XNYS-EQR") is None
    assert im.securities_of_issuer("ISS:US-XNYS-EQR") == ("SEC:US-XNYS-EQR",), (
        "a NaN security_state must read as active, never truthy"
    )


def test_security_issuer_row_carries_the_security_axis_and_stays_frozen() -> None:
    row = SecurityIssuerRow(security_id="SEC:US-XNYS-VMRK", issuer_id=None,
                            issuer_state="NO_ISSUER_EVIDENCE", listing_key="US-XNYS-VMRK",
                            security_state="SUPERSEDED_DUPLICATE_MINT",
                            superseded_by="SEC:US-XNYS-EQR")
    assert row.security_state == "SUPERSEDED_DUPLICATE_MINT"
    assert row.superseded_by == "SEC:US-XNYS-EQR"
    with pytest.raises(Exception):  # noqa: BLE001 — frozen dataclass raises FrozenInstanceError
        row.security_state = "ACTIVE"  # type: ignore[misc]
    # Default construction (no security-axis kwargs) is active — matches the era seam.
    active = SecurityIssuerRow(security_id="SEC:US-XNYS-EQR", issuer_id="ISS:US-XNYS-EQR",
                               issuer_state="RESOLVED", listing_key="US-XNYS-EQR")
    assert active.security_state is None
    assert active.superseded_by is None


def test_issuer_id_and_parse_id_are_unchanged_by_the_issuer_axis() -> None:
    """Spec §2: grammar unchanged — ``issuer_id()``/``parse_id()`` stay pure
    renderers; WHICH listing key the builder passes to ``issuer_id()`` is what
    changed, not the function itself."""
    assert issuer_id(MMC) == "ISS:US-XNYS-MMC"
    assert parse_id("ISS:US-XNAS-GOOG") == ("issuer", ListingKey("US", XNAS, "GOOG"))


# ── current security -> listing key seam — B-F06-1 prerequisite ─────────────
def test_issuer_master_listing_key_of_security_returns_the_master_value() -> None:
    im = IssuerMaster.from_records([
        {"security_id": "SEC:US-XNAS-MSFT", "issuer_id": "ISS:US-XNAS-MSFT",
         "issuer_state": "RESOLVED", "issuer_cik": "789019", "listing_key": "US-XNAS-MSFT"},
    ])

    assert im.listing_key_of_security("SEC:US-XNAS-MSFT") == "US-XNAS-MSFT"


def test_issuer_master_listing_key_of_security_returns_none_for_absent_security() -> None:
    im = IssuerMaster.from_records([
        {"security_id": "SEC:US-XNAS-MSFT", "issuer_id": "ISS:US-XNAS-MSFT",
         "issuer_state": "RESOLVED", "issuer_cik": "789019", "listing_key": "US-XNAS-MSFT"},
    ])

    assert im.listing_key_of_security("SEC:UNKNOWN") is None


def test_issuer_master_listing_key_of_security_refuses_conflicting_rows() -> None:
    im = IssuerMaster([
        SecurityIssuerRow(security_id="SEC:US-XNAS-DUP", issuer_id="ISS:US-XNAS-DUP",
                          issuer_state="RESOLVED", listing_key="US-XNAS-DUP"),
        SecurityIssuerRow(security_id="SEC:US-XNAS-DUP", issuer_id="ISS:US-XNAS-DUP",
                          issuer_state="RESOLVED", listing_key="US-XNAS-DUPTWO"),
    ])

    with pytest.raises(IdentityError, match="conflicting.*listing key"):
        im.listing_key_of_security("SEC:US-XNAS-DUP")


def test_issuer_master_listing_key_round_trips_to_the_security_id() -> None:
    im = IssuerMaster.from_records([
        {"security_id": "SEC:US-XNAS-MSFT", "issuer_id": "ISS:US-XNAS-MSFT",
         "issuer_state": "RESOLVED", "issuer_cik": "789019", "listing_key": "US-XNAS-MSFT"},
    ])
    listing_key = im.listing_key_of_security("SEC:US-XNAS-MSFT")
    assert security_id(parse_listing_key(listing_key)) == "SEC:US-XNAS-MSFT"


def test_issuer_master_listing_key_of_security_excludes_a_tombstoned_duplicate() -> None:
    """MAJOR fix (B-F06-1 review): a security-axis-superseded row (a
    tombstone) sharing a security_id with the live row must never
    contribute its stale listing_key to `listing_key_of_security` --
    mirroring the exclusion `securities_of_issuer` already enforces."""
    im = IssuerMaster([
        SecurityIssuerRow(security_id="SEC:US-XNAS-DUP", issuer_id="ISS:US-XNAS-DUP",
                          issuer_state="RESOLVED", listing_key="US-XNAS-DUP",
                          security_state=None, superseded_by=None),
        SecurityIssuerRow(security_id="SEC:US-XNAS-DUP", issuer_id="ISS:US-XNAS-DUP",
                          issuer_state="RESOLVED", listing_key="US-XNAS-DUPSTALE",
                          security_state="superseded", superseded_by="SEC:US-XNAS-DUP"),
    ])

    assert im.listing_key_of_security("SEC:US-XNAS-DUP") == "US-XNAS-DUP"


def test_issuer_master_listing_key_of_security_is_none_for_a_tombstone_only_security() -> None:
    """A security whose only row is superseded must never return the stale
    key as if it were current."""
    im = IssuerMaster([
        SecurityIssuerRow(security_id="SEC:US-XNAS-OLD", issuer_id="ISS:US-XNAS-OLD",
                          issuer_state="RESOLVED", listing_key="US-XNAS-OLD",
                          security_state="superseded", superseded_by="SEC:US-XNAS-NEW"),
    ])

    assert im.listing_key_of_security("SEC:US-XNAS-OLD") is None


# ── Observation reader: pure synthetic records, no writer or file adapter ──────
import copy
import hashlib
import json
from datetime import datetime, timezone

from lib.dataos.identity import (
    AliasResolution, ReferenceReadReceipt, alias_binding_sha256,
    validate_reference_snapshot,
)

_OBS_NAMES = (
    "security_master.parquet", "vendor_aliases.parquet", "issuer_master.parquet",
    "issuer_migrations.parquet", "security_migrations.parquet",
)
_OBS_T0 = 1791370000000000000  # synthetic fixture, not an actual read receipt
_OBS_PROBES = {"MU": ("XNAS", "CS"), "SPY": ("ARCX", "ETF"),
               "QQQ": ("XNAS", "ETF"), "SMH": ("XNAS", "ETF")}


def _obs_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode()


def _obs_hash(value):
    return hashlib.sha256(_obs_json(value)).hexdigest()


def _obs_rows_hash(rows):
    return _obs_hash(sorted(rows, key=_obs_json))


def _obs_iso(ns):
    return datetime.fromtimestamp(ns // 10**9, timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S") + f".{ns % 10**9:09d}Z"


def _obs_seal(record, field):
    record[field] = _obs_hash({k: v for k, v in record.items() if k != field})
    return record


def _obs_base():
    rows = [{"vendor": "store", "vendor_symbol": "DOMO", "security_id": "SEC:US-XNAS-DOMO",
             "valid_from": None, "valid_to": None, "ingested_at": "2026-10-01T00:00:00",
             "known_at": None, "evidence_sha256": None, "binding_sha256": None}]
    probes = {}
    master = []
    for symbol, (mic, kind) in _OBS_PROBES.items():
        sec = f"SEC:US-{mic}-{symbol}"
        master.append({"security_id": sec, "listing_key": f"US-{mic}-{symbol}",
                       "country": "US", "mic": mic, "inception_code": symbol,
                       "security_state": None, "issuer_id": None})
        probe = {"symbol": symbol, "status": "BOUND" if symbol == "MU" else "REFUSED",
                 "code": None if symbol == "MU" else "canonical_identity_refused",
                 "known_at": _obs_iso(_OBS_T0), "evidence_sha256": _obs_hash({"probe": symbol}),
                 "native_identity": {"ticker": symbol, "primary_exchange": mic, "type": kind}}
        if symbol == "MU":
            seal = alias_binding_sha256("polygon", symbol, sec, date(2026, 10, 7), None,
                                        probe["known_at"], probe["evidence_sha256"])
            probe.update(security_id=sec, binding_sha256=seal)
            rows.append({"vendor": "polygon", "vendor_symbol": symbol, "security_id": sec,
                         "valid_from": "2026-10-07", "valid_to": None,
                         "ingested_at": "2026-10-07T00:00:00",
                         "known_at": probe["known_at"], "evidence_sha256": probe["evidence_sha256"],
                         "binding_sha256": seal})
        probes[symbol] = probe
    for symbol in ("DOMO", "YYGH"):
        master.append({"security_id": f"SEC:US-XNAS-{symbol}", "listing_key": f"US-XNAS-{symbol}",
                       "country": "US", "mic": "XNAS", "inception_code": symbol,
                       "security_state": None, "issuer_id": None})
    original = {"schema": "mastermind.prospective_reference.v1",
                "source_read_completed_at_utc_ns": _OBS_T0, "probes": probes}
    digest = _obs_hash(original)
    anchor = _obs_seal({"schema": "mastermind.identity_anchor.v1",
                       "anchor_id": "anchor:" + digest, "original_reference_sha256": digest,
                       "original_native_rows_sha256": _obs_rows_hash([r for r in rows if r["vendor"] == "polygon"]),
                       "owner_read_completed_at_utc_ns": str(_OBS_T0)}, "anchor_sha256")
    history = {"schema": "mastermind.identity_observations.v1", "anchor": anchor, "attempts": []}
    return original, history, rows, master


def _obs_append(original, history, rows, *, status="BOUND", listing=False, boundary="2026-09-24"):
    history, rows = copy.deepcopy(history), copy.deepcopy(rows)
    sequence = len(history["attempts"]) + 1
    aid = f"attempt-{sequence}"
    ns = _OBS_T0 + sequence * 1000
    specs = ({"listing:domo": ("DOMO", "HUCK", "COMMON_CLASS_B"),
              "listing:yygh": ("YYGH", "YFOR", "ORDINARY_CLASS_A")} if listing else
             {f"polygon:{symbol}": (symbol, mic, kind)
              for symbol, (mic, kind) in _OBS_PROBES.items()})
    acquisition, families = {}, []
    evidence = {name: _obs_hash(name) for name in
                ("listing_snapshot", "listing_receipt", "cik_mapping", "mic_evidence", "identity_seams")}
    deps = {"source_commit": "1" * 40,
            "source_blobs": {name: "4" * 40 for name in ("scripts/build_security_master.py",
                "lib/dataos/identity.py", "config/identity_seams.yml")},
            "prior_receipt_sha256": "2" * 64,
            "artifact_sha256": {name: _obs_hash(name) for name in _OBS_NAMES},
            "evidence_sha256": evidence}
    for fid, spec in specs.items():
        symbol = spec[0]
        vendor = "listing" if listing else "polygon"
        mic, klass = ("XNAS", spec[2]) if listing else (spec[1], spec[2])
        symbols = list(spec[:2]) if listing else [symbol]
        sec = f"SEC:US-{mic}-{symbol}"
        disposition = status if symbol in ("MU", "DOMO") else ("BOUND" if listing else "REFUSED")
        prior = history["anchor"]["anchor_id"] + "/" + fid if not listing else None
        for previous in history["attempts"]:
            for family in previous["payload"]["families"]:
                if family["family_id"] == fid:
                    prior = family["alias_revision_id"]
        revision = aid + "/" + fid
        esha = _obs_hash({"family": fid, "sequence": sequence})
        acquisition[fid] = {
            "started_at_utc_ns": str(ns - 200), "completed_at_utc_ns": str(ns - 100),
            "outcome": "SUCCESS", "representation": "decoded_json",
            "response_sha256": _obs_hash({"response": sequence, "family": fid}),
            "source_published_at": None, "published_date": None,
        }
        members = []
        if disposition == "BOUND":
            bounds = [(symbol, "2026-10-07", None)] if not listing else [
                (symbol, None, boundary), (spec[1], boundary, None)]
            for token, lo, hi in bounds:
                row = {"vendor": vendor, "vendor_symbol": token, "security_id": sec,
                       "valid_from": lo, "valid_to": hi, "ingested_at": "2026-10-07T00:00:00",
                       "known_at": _obs_iso(ns), "evidence_sha256": esha,
                       "attempt_id": aid, "alias_family_id": fid, "alias_revision_id": revision}
                row["binding_sha256"] = _obs_hash(
                    {"schema": "mastermind.identity_alias_revision.v1", **row})
                rows.append(row)
                members.append(_obs_hash(row))
        family = {"family_id": fid, "alias_revision_id": revision,
                  "predecessor_revision_id": prior, "vendor": vendor, "symbols": symbols,
                  "security_id": sec if (disposition == "BOUND" or symbol == "MU") else None,
                  "country": "US", "mic": mic, "security_class": klass,
                  "status": disposition, "reason": None if disposition == "BOUND" else "source_unavailable",
                  "evidence_sha256": esha, "row_sha256": members}
        families.append(_obs_seal(family, "family_sha256"))
    for fid in specs:
        role = "continuity_evidence" if listing else "native_response"
        evidence[fid + "/" + role] = acquisition[fid]["response_sha256"]
        evidence[fid + "/owner_fences"] = _obs_hash({"fences": fid})
        if listing:
            evidence[fid + "/listing_binding_spec"] = _obs_hash({"spec": fid})
    previous = history["attempts"][-1] if history["attempts"] else history["anchor"]
    attempt = {"schema": "mastermind.identity_attempt_envelope.v1",
               "attempt_id": aid, "sequence": sequence,
               "predecessor_attempt_id": previous.get("attempt_id", previous.get("anchor_id")),
               "predecessor_sha256": previous.get("attempt_sha256", previous.get("anchor_sha256")),
               "kind": "SAME_VENUE_RENAME" if listing else "NATIVE_REFERENCE",
               "scope": list(specs), "input_file_sha256": _obs_hash({"input": sequence}),
               "input_sha256": _obs_hash({"decoded": sequence}),
               "dependencies_sha256": _obs_hash(deps), "acquisition_sha256": _obs_hash(acquisition),
               "owner_read_completed_at_utc_ns": str(ns),
               "row_membership": {f["family_id"]: list(f["row_sha256"]) for f in families},
               "payload": {"schema": "mastermind.identity_attempt_payload.v1",
                           "dependencies": deps, "acquisition": acquisition, "families": families}}
    _obs_refresh_attempt(attempt, rows)
    history["attempts"].append(attempt)
    return history, rows



def _obs_refresh_attempt(attempt, rows):
    """Independently reseal synthetic evidence; never calls implementation helpers."""
    payload = attempt["payload"]
    attempt["dependencies_sha256"] = _obs_hash(payload["dependencies"])
    attempt["acquisition_sha256"] = _obs_hash(payload["acquisition"])
    for family in payload["families"]:
        fid = family["family_id"]
        evidence = _obs_hash({"schema": "mastermind.identity_family_evidence.v1",
            "family_id": fid, "input_file_sha256": attempt["input_file_sha256"],
            "input_sha256": attempt["input_sha256"],
            "dependencies_sha256": attempt["dependencies_sha256"],
            "acquisition": payload["acquisition"][fid]})
        family["evidence_sha256"] = evidence
        own = [r for r in rows if r.get("attempt_id") == attempt["attempt_id"]
               and r.get("alias_family_id") == fid]
        own.sort(key=lambda r: family["symbols"].index(r["vendor_symbol"])
                 if r["vendor_symbol"] in family["symbols"] else -1)
        members = []
        for row in own:
            row["evidence_sha256"] = evidence
            row["binding_sha256"] = _obs_hash({"schema": "mastermind.identity_alias_revision.v1",
                **{k: v for k, v in row.items() if k != "binding_sha256"}})
            members.append(_obs_hash(row))
        family["row_sha256"] = members
        _obs_seal(family, "family_sha256")
    attempt["row_membership"] = {f["family_id"]: list(f["row_sha256"]) for f in payload["families"]}
    _obs_seal(attempt, "attempt_sha256")


def _obs_snapshot(original, history, rows, master, *, read_ns=None, receipt_overrides=None):
    artifacts = {name: b"synthetic serialization:" + name.encode() for name in _OBS_NAMES}
    semantic = {"vendor_aliases.parquet": _obs_rows_hash(rows),
                "security_master.parquet": _obs_rows_hash(master)}
    manifest = {name: {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                      "semantic_sha256": semantic.get(name)} for name, raw in artifacts.items()}
    publication = _obs_seal({"schema": "mastermind.identity_publication.v1",
                            "predecessor_receipt_sha256": None, "code_version": "3" * 40,
                            "artifacts": manifest, "history_sha256": _obs_hash(history)}, "generation_id")
    receipt = {"prospective_reference": original, "identity_observations": history,
               "publication": publication}
    if receipt_overrides:
        receipt.update(receipt_overrides)
    raw = _obs_json(receipt)
    snapshot = validate_reference_snapshot(raw, artifacts, raw, alias_records=rows, master_records=master)
    end = read_ns if read_ns is not None else _OBS_T0 + 10_000 + len(history["attempts"]) * 1000
    rr = ReferenceReadReceipt.from_record({
        "schema": "mastermind.identity_read_receipt.v1", "receipt_sha256": hashlib.sha256(raw).hexdigest(),
        "generation_id": publication["generation_id"],
        "artifact_sha256": {name: manifest[name]["sha256"] for name in _OBS_NAMES},
        "history_prefix_sha256": _obs_hash(history),
        "read_started_at_utc_ns": str(end - 1), "read_completed_at_utc_ns": str(end)})
    return snapshot, rr


def _obs_table(original, history, rows, *snapshots):
    return VendorAliasTable.from_records(rows, observation_history=history,
                                         original_reference=original, snapshot_contexts=snapshots)


def _obs_query(table, *reads, cutoff=None, vendor="polygon", symbol="MU", on=date(2026, 10, 7)):
    return table.resolve_binding(vendor, symbol, on, decision_at=_obs_iso(
        _OBS_T0 + 100_000 if cutoff is None else cutoff), snapshot_receipts=reads)


def test_observation_original_v1_is_unchanged_and_not_consumer_custody():
    original, history, rows, master = _obs_base()
    before = copy.deepcopy((original, history, rows, master))
    v1 = VendorAliasTable.from_records(rows)
    assert v1.resolve("polygon", "MU", date(2026, 10, 7), decision_at=_obs_iso(_OBS_T0)) == "SEC:US-XNAS-MU"
    assert _obs_query(v1).status == "UNAVAILABLE"
    snap, read = _obs_snapshot(original, history, rows, master)
    table = _obs_table(original, history, rows, snap)
    result = _obs_query(table, read)
    assert result.status == "BOUND" and result.security_id == "SEC:US-XNAS-MU"
    assert result.known_at_utc_ns == str(_OBS_T0)
    assert table.resolve("store", "DOMO", date(2000, 1, 1)) == "SEC:US-XNAS-DOMO"
    assert (original, history, rows, master) == before
    with pytest.raises(IdentityError, match="eligible view"):
        _ = table.rows


@pytest.mark.parametrize("decision", [None, "2026-10-07", datetime(2026, 10, 7), "2026-10-07X00:00:00Z"])
@pytest.mark.parametrize("vendor", ["polygon", "listing"])
def test_observation_empty_unknown_queries_still_require_explicit_clock(decision, vendor):
    with pytest.raises(IdentityError):
        VendorAliasTable().resolve_binding(vendor, "UNKNOWN", date(2026, 10, 7), decision_at=decision)
    with pytest.raises(IdentityError):
        VendorAliasTable().resolve(vendor, "UNKNOWN", date(2026, 10, 7), decision_at=decision)


def test_observation_read_clock_is_separate_and_ns_boundary_is_exact():
    original, history, rows, master = _obs_base()
    read_ns = _OBS_T0 + 999
    snap, read = _obs_snapshot(original, history, rows, master, read_ns=read_ns)
    table = _obs_table(original, history, rows, snap)
    assert _obs_query(table, read, cutoff=read_ns - 1).reason == "NO_ENROLLED_SNAPSHOT_BY_CUTOFF"
    assert _obs_query(table, read, cutoff=read_ns).status == "BOUND"
    assert _obs_query(table).status == "UNAVAILABLE"
    assert table.symbol_binding_for("polygon", "SEC:US-XNAS-MU", date(2026, 10, 7),
                                   decision_at=_obs_iso(read_ns), snapshot_receipts=(read,)).vendor_symbol == "MU"


def test_observation_bound_refused_bound_preserves_all_attempts_and_does_not_fallback():
    original, history, rows, master = _obs_base()
    snapshots, reads, views = [], [], []
    for status in ("BOUND", "REFUSED", "BOUND"):
        history, rows = _obs_append(original, history, rows, status=status)
        snap, read = _obs_snapshot(original, history, rows, master)
        snapshots.append(snap); reads.append(read); views.append(copy.deepcopy((history, rows)))
    table = _obs_table(original, history, rows, *snapshots)
    for i, expected in enumerate(("BOUND", "REFUSED", "BOUND")):
        result = _obs_query(table, *reads, cutoff=int(reads[i].read_completed_at_utc_ns))
        assert result.status == expected
        assert result.attempt_id == f"attempt-{i + 1}"
        reverse = table.symbol_binding_for("polygon", "SEC:US-XNAS-MU", date(2026, 10, 7),
                                           decision_at=_obs_iso(int(reads[i].read_completed_at_utc_ns)),
                                           snapshot_receipts=tuple(reads))
        assert reverse.status == expected
    assert len(history["attempts"]) == 3
    assert views[0][0]["attempts"] == history["attempts"][:1]
    assert views[1][1] == views[0][1]  # REFUSED adds no alias row
    assert all(row in rows for row in views[0][1])


def test_observation_listing_half_open_a_b_a_correction_preserves_old_view():
    original, history, rows, master = _obs_base()
    snapshots, reads = [], []
    for boundary in ("2026-09-24", "2026-09-25", "2026-09-24"):
        history, rows = _obs_append(original, history, rows, listing=True, boundary=boundary)
        snap, read = _obs_snapshot(original, history, rows, master)
        snapshots.append(snap); reads.append(read)
    table = _obs_table(original, history, rows, *snapshots)
    for i, symbol in enumerate(("HUCK", "DOMO", "HUCK")):
        result = table.symbol_binding_for("listing", "SEC:US-XNAS-DOMO", date(2026, 9, 24),
            decision_at=_obs_iso(int(reads[i].read_completed_at_utc_ns)), snapshot_receipts=tuple(reads))
        assert result.vendor_symbol == symbol
        assert table.resolve("listing", symbol, date(2026, 9, 24),
            decision_at=_obs_iso(int(reads[i].read_completed_at_utc_ns)), snapshot_receipts=tuple(reads)) == result.security_id
    assert _obs_query(table, reads[0], vendor="listing", symbol="HUCK", on=date(2026, 9, 23)).status == "UNAVAILABLE"
    assert _obs_query(table, reads[0], vendor="listing", symbol="DOMO", on=date(2026, 9, 23)).status == "BOUND"


@pytest.mark.parametrize("future_schema", ["future.v999", None, [], {}])
def test_observation_sealed_future_payload_cannot_poison_genuine_old_prefix(future_schema):
    original, history, rows, master = _obs_base()
    old_snap, old_read = _obs_snapshot(original, history, rows, master, read_ns=_OBS_T0 + 500)
    old_table = _obs_table(original, history, rows, old_snap)
    expected = _obs_query(old_table, old_read, cutoff=_OBS_T0 + 500)
    future, future_rows = _obs_append(original, history, rows, status="REFUSED")
    future["attempts"][0]["payload"]["schema"] = future_schema
    _obs_seal(future["attempts"][0], "attempt_sha256")
    new_snap, new_read = _obs_snapshot(original, future, future_rows, master)
    table = _obs_table(original, future, future_rows, old_snap, new_snap)
    assert _obs_query(table, old_read, new_read, cutoff=_OBS_T0 + 500) == expected
    assert _obs_query(table, old_read) == expected  # late cutoff does not enroll future data
    with pytest.raises(IdentityError, match="schema unsupported"):
        _obs_query(table, new_read)


def test_observation_old_receipt_does_not_authorize_new_master_bytes():
    original, history, rows, master = _obs_base()
    old_snap, old_read = _obs_snapshot(original, history, rows, master, read_ns=_OBS_T0 + 500)
    changed_master = copy.deepcopy(master)
    changed_master[0].update(mic="XNYS", listing_key="US-XNYS-MU")
    new_snap, new_read = _obs_snapshot(original, history, rows, changed_master)
    table = _obs_table(original, history, rows, old_snap, new_snap)
    assert _obs_query(table, old_read).status == "BOUND"
    with pytest.raises(IdentityError, match="master"):
        _obs_query(table, new_read)
    with pytest.raises(IdentityError, match="ambiguous same-prefix"):
        _obs_query(table, old_read, new_read)


def test_observation_same_prefix_equivalent_generation_uses_earliest_actual_receipt():
    original, history, rows, master = _obs_base()
    snap_a, read_a = _obs_snapshot(original, history, rows, master, read_ns=_OBS_T0 + 500)
    snap_b, read_b = _obs_snapshot(original, history, rows, master, read_ns=_OBS_T0 + 600,
                                  receipt_overrides={"diagnostic": "later generation"})
    table = _obs_table(original, history, rows, snap_a, snap_b)
    assert _obs_query(table, read_b, read_a).receipt_sha256 == read_a.receipt_sha256


@pytest.mark.parametrize("field,value", [("sequence", True), ("attempt_id", 7),
    ("owner_read_completed_at_utc_ns", True), ("owner_read_completed_at_utc_ns", "01791370000000000001"),
    ("owner_read_completed_at_utc_ns", "1e18"), ("owner_read_completed_at_utc_ns", str(_OBS_T0)),
    ("predecessor_sha256", "0" * 64)])
def test_observation_outer_failures_refuse_even_before_future_visibility(field, value):
    original, history, rows, master = _obs_base()
    history, rows = _obs_append(original, history, rows)
    history["attempts"][0][field] = value
    _obs_seal(history["attempts"][0], "attempt_sha256")
    with pytest.raises(IdentityError):
        _obs_snapshot(original, history, rows, master)


def test_observation_row_integrity_is_immediate_and_orphans_cannot_hide():
    original, history, rows, master = _obs_base()
    history, rows = _obs_append(original, history, rows)
    bad = copy.deepcopy(rows)
    bad[-1]["vendor_symbol"] = "OTHER"
    with pytest.raises(IdentityError, match="row binding seal"):
        _obs_snapshot(original, history, bad, master)
    with pytest.raises(IdentityError, match="missing/duplicate row membership"):
        _obs_snapshot(original, history, rows[:-1], master)
    truncated = copy.deepcopy(history); truncated["attempts"] = []
    with pytest.raises(IdentityError, match="orphan"):
        _obs_snapshot(original, truncated, rows, master)


def test_observation_changed_old_prefix_and_duplicate_attempt_are_rejected():
    original, history, rows, master = _obs_base()
    history, rows = _obs_append(original, history, rows)
    snap, _read = _obs_snapshot(original, history, rows, master)
    changed = copy.deepcopy(history)
    changed["attempts"][0]["input_sha256"] = "f" * 64
    _obs_seal(changed["attempts"][0], "attempt_sha256")
    new_snap, _ = _obs_snapshot(original, changed, rows, master)
    with pytest.raises(IdentityError, match="prefix"):
        _obs_table(original, changed, rows, snap, new_snap)
    duplicate = copy.deepcopy(history)
    duplicate["attempts"].append(copy.deepcopy(duplicate["attempts"][0]))
    with pytest.raises(IdentityError, match="duplicate attempt"):
        _obs_snapshot(original, duplicate, rows, master)


def test_observation_projection_never_relabels_clocked_namespaces():
    original, history, rows, master = _obs_base()
    history, rows = _obs_append(original, history, rows, listing=True)
    projected = VendorAliasTable.legacy_only_records(rows)
    assert projected == [rows[0]]
    assert VendorAliasTable.from_records(projected).resolve("store", "DOMO", date(1990, 1, 1)) == "SEC:US-XNAS-DOMO"
    with pytest.raises(IdentityError, match="requires observation"):
        VendorAliasTable.from_records(rows)
    with pytest.raises(IdentityError, match="requires observation"):
        AliasRow("listing", "HUCK", "SEC:US-XNAS-DOMO")
    corrupted = dict(rows[0], attempt_id="attempt-1")
    with pytest.raises(IdentityError, match="revision metadata"):
        VendorAliasTable.legacy_only_records([corrupted])


@pytest.mark.parametrize("field,value", [("vendor_symbol", True), ("security_id", 3), ("vendor", 7)])
def test_observation_numeric_identity_cannot_be_coerced_to_a_binding(field, value):
    original, history, rows, master = _obs_base()
    history, rows = _obs_append(original, history, rows)
    row = rows[-1]
    row[field] = value
    row["binding_sha256"] = _obs_hash({"schema": "mastermind.identity_alias_revision.v1",
                                     **{k: v for k, v in row.items() if k != "binding_sha256"}})
    family = history["attempts"][0]["payload"]["families"][0]
    family["row_sha256"] = [_obs_hash(row)]
    _obs_seal(family, "family_sha256")
    _obs_seal(history["attempts"][0], "attempt_sha256")
    with pytest.raises(IdentityError, match="string"):
        _obs_snapshot(original, history, rows, master)


def test_observation_bound_cannot_claim_failed_acquisition_or_missing_dependency():
    original, history, rows, master = _obs_base()
    history, rows = _obs_append(original, history, rows)
    for failure in ("failed", "missing"):
        bad = copy.deepcopy(history); changed_rows = copy.deepcopy(rows)
        attempt = bad["attempts"][0]
        if failure == "failed":
            attempt["payload"]["acquisition"]["polygon:MU"]["outcome"] = "FAILED"
            attempt["acquisition_sha256"] = _obs_hash(attempt["payload"]["acquisition"])
        else:
            attempt["payload"]["dependencies"]["evidence_sha256"]["listing_snapshot"] = None
            attempt["dependencies_sha256"] = _obs_hash(attempt["payload"]["dependencies"])
        _obs_refresh_attempt(attempt, changed_rows)
        snap, read = _obs_snapshot(original, bad, changed_rows, master)
        table = _obs_table(original, bad, changed_rows, snap)
        with pytest.raises(IdentityError, match="bound dependencies"):
            _obs_query(table, read)


def test_observation_snapshot_requires_exact_bytes_records_and_consumer_seals():
    original, history, rows, master = _obs_base()
    snap, read = _obs_snapshot(original, history, rows, master)
    with pytest.raises(IdentityError, match="semantic record seal"):
        validate_reference_snapshot(snap.receipt_bytes, dict(snap.artifact_bytes), snap.receipt_bytes,
                                    alias_records=rows[:-1], master_records=master)
    with pytest.raises(IdentityError, match="receipt changed"):
        validate_reference_snapshot(snap.receipt_bytes, dict(snap.artifact_bytes), snap.receipt_bytes+b" ",
                                    alias_records=rows, master_records=master)
    artifacts = dict(snap.artifact_bytes); artifacts["security_master.parquet"] += b"x"
    with pytest.raises(IdentityError, match="byte count"):
        validate_reference_snapshot(snap.receipt_bytes, artifacts, snap.receipt_bytes,
                                    alias_records=rows, master_records=master)
    bad_read = read.as_record(); bad_read["artifact_sha256"]["security_master.parquet"] = "f" * 64
    table = _obs_table(original, history, rows, snap)
    with pytest.raises(IdentityError, match="snapshot mismatch"):
        _obs_query(table, ReferenceReadReceipt.from_record(bad_read))


def test_observation_capacity_64_attempts_is_inclusive_65_refuses_without_truncation():
    original, history, rows, master = _obs_base()
    for _ in range(64):
        history, rows = _obs_append(original, history, rows, status="REFUSED")
    snap, read = _obs_snapshot(original, history, rows, master)
    table = _obs_table(original, history, rows, snap)
    assert _obs_query(table, read).status == "REFUSED"
    more, more_rows = _obs_append(original, history, rows, status="REFUSED")
    with pytest.raises(IdentityError, match="attempt count"):
        _obs_snapshot(original, more, more_rows, master)
    assert len(history["attempts"]) == 64


def test_observation_deep_or_non_json_objects_refuse_boundedly():
    original, history, rows, master = _obs_base()
    nested = "leaf"
    for _ in range(18):
        nested = [nested]
    bad = copy.deepcopy(history); bad["extra"] = nested
    with pytest.raises(IdentityError):
        _obs_table(original, bad, rows)
    with pytest.raises(IdentityError, match="JSON primitive"):
        _obs_table(original, history, [*rows, {"vendor": object()}])


def test_observation_legacy_changes_do_not_rewrite_native_anchor_or_old_clocked_view():
    original, history, rows, master = _obs_base()
    old_snapshot, old_read = _obs_snapshot(original, history, rows, master)
    expected = _obs_query(_obs_table(original, history, rows, old_snapshot), old_read)
    changed = copy.deepcopy(rows)
    changed[0]["valid_to"] = "2026-10-01"
    changed.append(dict(changed[0], vendor_symbol="HUCK", valid_from="2026-10-01", valid_to=None))
    # Null new columns are the only allowed native anchor projection normalization.
    for row in changed:
        row.update(attempt_id=None, alias_family_id=None, alias_revision_id=None)
    current_snapshot, _ = _obs_snapshot(original, history, changed, master)
    table = _obs_table(original, history, changed, old_snapshot, current_snapshot)
    assert _obs_query(table, old_read) == expected
    assert table.resolve("store", "DOMO", date(2026, 9, 30)) == "SEC:US-XNAS-DOMO"
    assert table.resolve("store", "HUCK", date(2026, 10, 7)) == "SEC:US-XNAS-DOMO"
    assert table.resolve("store", "DOMO", date(2026, 10, 7)) is None
    bad = copy.deepcopy(changed)
    bad[1]["ingested_at"] = "changed"
    with pytest.raises(IdentityError, match="native prefix changed"):
        _obs_snapshot(original, history, bad, master)


def test_observation_latest_refusal_survives_removed_master_without_poisoning_old_bound():
    original, history, rows, master = _obs_base()
    history, rows = _obs_append(original, history, rows)
    old_snapshot, old_read = _obs_snapshot(original, history, rows, master)
    history, rows = _obs_append(original, history, rows, status="REFUSED")
    missing_master = [r for r in master if r["security_id"] != "SEC:US-XNAS-MU"]
    new_snapshot, new_read = _obs_snapshot(original, history, rows, missing_master)
    table = _obs_table(original, history, rows, old_snapshot, new_snapshot)
    assert _obs_query(table, old_read).status == "BOUND"
    refusal = _obs_query(table, new_read)
    assert refusal.status == "REFUSED" and refusal.attempt_id == "attempt-2"
    assert table.resolve("polygon", "MU", date(2026, 10, 7),
        decision_at=_obs_iso(_OBS_T0 + 100_000), snapshot_receipts=(new_read,)) is None


@pytest.mark.parametrize("future_payload", [None, [], {"alien": {"members": "unsupported"}}])
def test_observation_future_whole_layout_with_physical_rows_is_semantically_isolated(future_payload):
    original, history, rows, master = _obs_base()
    old_snapshot, old_read = _obs_snapshot(original, history, rows, master, read_ns=_OBS_T0+500)
    expected = _obs_query(_obs_table(original, history, rows, old_snapshot), old_read)
    future, future_rows = _obs_append(original, history, rows)
    future["attempts"][0]["payload"] = future_payload
    _obs_seal(future["attempts"][0], "attempt_sha256")
    new_snapshot, new_read = _obs_snapshot(original, future, future_rows, master)
    table = _obs_table(original, future, future_rows, old_snapshot, new_snapshot)
    assert _obs_query(table, old_read) == expected
    assert _obs_query(table, old_read, new_read, cutoff=_OBS_T0+500) == expected
    with pytest.raises(IdentityError, match="visible payload"):
        _obs_query(table, new_read)
    bad_rows = copy.deepcopy(future_rows)
    bad_rows[-1]["known_at"] = _obs_iso(_OBS_T0 + 999)
    row = bad_rows[-1]
    row["binding_sha256"] = _obs_hash({"schema": "mastermind.identity_alias_revision.v1",
        **{k: v for k, v in row.items() if k != "binding_sha256"}})
    future["attempts"][0]["row_membership"]["polygon:MU"] = [_obs_hash(row)]
    _obs_seal(future["attempts"][0], "attempt_sha256")
    with pytest.raises(IdentityError, match="row evidence clock"):
        _obs_snapshot(original, future, bad_rows, master)


def _obs_three_name_chain():
    original, history, rows, master = _obs_base()
    history, rows = _obs_append(original, history, rows, listing=True)
    old_snapshot, old_read = _obs_snapshot(original, history, rows, master)
    history, rows = _obs_append(original, history, rows, listing=True)
    attempt = history["attempts"][-1]
    family = attempt["payload"]["families"][0]
    family["symbols"].append("NEXT")
    own = [r for r in rows if r.get("attempt_id") == attempt["attempt_id"]
           and r.get("alias_family_id") == "listing:domo"]
    own[0]["valid_from"] = "2026-01-01"
    own[1]["valid_to"] = "2026-10-01"
    rows.append(dict(own[1], vendor_symbol="NEXT", valid_from="2026-10-01", valid_to=None))
    _obs_refresh_attempt(attempt, rows)
    return original, history, rows, master, old_snapshot, old_read


def test_observation_complete_three_name_chain_uses_same_security_and_preserves_earlier_view():
    original, history, rows, master, old_snapshot, old_read = _obs_three_name_chain()
    new_snapshot, new_read = _obs_snapshot(original, history, rows, master)
    table = _obs_table(original, history, rows, old_snapshot, new_snapshot)
    for on, expected in ((date(2026, 9, 23), "DOMO"), (date(2026, 9, 24), "HUCK"),
                         (date(2026, 10, 1), "NEXT")):
        answer = table.symbol_binding_for("listing", "SEC:US-XNAS-DOMO", on,
            decision_at=_obs_iso(_OBS_T0+100_000), snapshot_receipts=(new_read,))
        assert answer.status == "BOUND" and answer.vendor_symbol == expected
        assert _obs_query(table, new_read, vendor="listing", symbol=expected, on=on).security_id == "SEC:US-XNAS-DOMO"
    assert _obs_query(table, old_read, vendor="listing", symbol="HUCK").status == "BOUND"
    assert _obs_query(table, new_read, vendor="listing", symbol="NEXT", on=date(2025, 12, 31)).status == "UNAVAILABLE"


@pytest.mark.parametrize("defect", ["cycle", "branch", "gap", "overlap", "zero_width", "order"])
def test_observation_chain_cycles_branches_and_interval_conflicts_refuse(defect):
    original, history, rows, master, old_snapshot, _ = _obs_three_name_chain()
    attempt = history["attempts"][-1]
    family = attempt["payload"]["families"][0]
    own = [r for r in rows if r.get("attempt_id") == attempt["attempt_id"]
           and r.get("alias_family_id") == "listing:domo"]
    if defect == "cycle":
        family["symbols"][-1] = "DOMO"; own[-1]["vendor_symbol"] = "DOMO"
    elif defect == "branch":
        family["symbols"][1] = "BRANCH"; own[1]["vendor_symbol"] = "BRANCH"
    elif defect == "gap":
        own[1]["valid_from"] = "2026-09-25"
    elif defect == "overlap":
        own[1]["valid_from"] = "2026-09-23"
    elif defect == "zero_width":
        own[1]["valid_to"] = own[1]["valid_from"]
    _obs_refresh_attempt(attempt, rows)
    if defect == "order":
        family["row_sha256"].reverse()
        attempt["row_membership"][family["family_id"]] = list(family["row_sha256"])
        _obs_seal(family, "family_sha256"); _obs_seal(attempt, "attempt_sha256")
    if defect == "zero_width":
        with pytest.raises(IdentityError, match="event interval width"):
            _obs_snapshot(original, history, rows, master)
        return
    snapshot, read = _obs_snapshot(original, history, rows, master)
    table = _obs_table(original, history, rows, old_snapshot, snapshot)
    with pytest.raises(IdentityError):
        _obs_query(table, read, vendor="listing", symbol="NEXT")


@pytest.mark.parametrize("collision", ["vendor_symbol", "security_id"])
def test_observation_both_directions_reject_selected_cross_family_collisions(collision):
    original, history, rows, master = _obs_base()
    history, rows = _obs_append(original, history, rows, listing=True)
    attempt = history["attempts"][0]; family = attempt["payload"]["families"][1]
    own = [r for r in rows if r.get("alias_family_id") == "listing:yygh"]
    if collision == "vendor_symbol":
        family["symbols"][1] = "HUCK"; own[1]["vendor_symbol"] = "HUCK"
    else:
        family["security_id"] = "SEC:US-XNAS-DOMO"
        for row in own:
            row["security_id"] = family["security_id"]
    _obs_refresh_attempt(attempt, rows)
    snapshot, read = _obs_snapshot(original, history, rows, master)
    table = _obs_table(original, history, rows, snapshot)
    with pytest.raises(IdentityError, match="ambiguous selected alias"):
        _obs_query(table, read, vendor="listing", symbol="HUCK")
    with pytest.raises(IdentityError, match="ambiguous selected alias"):
        table.symbol_binding_for("listing", "SEC:US-XNAS-DOMO", date(2026, 10, 7),
            decision_at=_obs_iso(_OBS_T0+100_000), snapshot_receipts=(read,))


@pytest.mark.parametrize("defect", ["missing", "extra", "source_path", "source_blob", "response", "evidence"])
def test_observation_closed_dependency_and_family_evidence_binding(defect):
    original, history, rows, master = _obs_base()
    history, rows = _obs_append(original, history, rows)
    attempt = history["attempts"][0]; deps = attempt["payload"]["dependencies"]
    if defect == "missing":
        del deps["evidence_sha256"]["mic_evidence"]
    elif defect == "extra":
        deps["evidence_sha256"]["unrecognized"] = "f"*64
    elif defect == "source_path":
        del deps["source_blobs"]["lib/dataos/identity.py"]
    elif defect == "source_blob":
        deps["source_blobs"]["lib/dataos/identity.py"] = True
    elif defect == "response":
        deps["evidence_sha256"]["polygon:MU/native_response"] = "f"*64
    _obs_refresh_attempt(attempt, rows)
    if defect == "evidence":
        attempt["payload"]["families"][0]["evidence_sha256"] = "f"*64
        _obs_seal(attempt["payload"]["families"][0], "family_sha256")
        _obs_seal(attempt, "attempt_sha256")
    snapshot, read = _obs_snapshot(original, history, rows, master)
    table = _obs_table(original, history, rows, snapshot)
    with pytest.raises(IdentityError):
        _obs_query(table, read)


def test_observation_other_family_missing_source_keeps_independent_bound_and_real_refusal():
    original, history, rows, master = _obs_base()
    history, rows = _obs_append(original, history, rows)
    attempt = history["attempts"][0]; payload = attempt["payload"]
    payload["acquisition"]["polygon:SPY"].update(
        outcome="FAILED", representation=None, response_sha256=None)
    payload["dependencies"]["evidence_sha256"]["polygon:SPY/native_response"] = None
    payload["dependencies"]["evidence_sha256"]["polygon:SPY/owner_fences"] = None
    _obs_refresh_attempt(attempt, rows)
    snapshot, read = _obs_snapshot(original, history, rows, master)
    table = _obs_table(original, history, rows, snapshot)
    assert _obs_query(table, read).status == "BOUND"
    refused = _obs_query(table, read, symbol="SPY")
    assert refused.status == "REFUSED" and refused.reason == "source_unavailable"
    assert refused.security_id is None


@pytest.mark.parametrize("field,value", [
    ("read_started_at_utc_ns", True), ("read_completed_at_utc_ns", "01791370000000000000"),
    ("read_completed_at_utc_ns", "1791370000000000000.0"),
    ("read_completed_at_utc_ns", "-1"), ("read_completed_at_utc_ns", "9223372036854775808"),
])
def test_observation_actual_read_clock_grammar_refuses_coercion(field, value):
    original, history, rows, master = _obs_base()
    _, read = _obs_snapshot(original, history, rows, master)
    record = read.as_record(); record[field] = value
    with pytest.raises(IdentityError):
        ReferenceReadReceipt.from_record(record)


def test_observation_receipts_and_contexts_have_inclusive_bounds():
    original, history, rows, master = _obs_base()
    snapshot, read = _obs_snapshot(original, history, rows, master)
    table = _obs_table(original, history, rows, *([snapshot]*65))
    assert _obs_query(table, *([read]*256)).status == "BOUND"
    with pytest.raises(IdentityError, match="context count"):
        _obs_table(original, history, rows, *([snapshot]*66))
    with pytest.raises(IdentityError, match="receipt sequence bound"):
        _obs_query(table, *([read]*257))


def test_observation_record_set_budget_is_checked_before_whole_list_encoding(monkeypatch):
    # Shrink only this byte unit to exercise the real cumulative guard cheaply.
    # Both per-record objects fit; their complete canonical list does not.
    from lib.dataos import identity as owner
    monkeypatch.setattr(owner, "_MIB", 1)
    assert owner._ob_records([{"x": "a"*25}, {"x": "b"*20}]) == _obs_json(
        [{"x": "a"*25}, {"x": "b"*20}])
    with pytest.raises(IdentityError, match="record-set byte bound"):
        owner._ob_records([{"x": "a"*25}, {"x": "b"*25}])
    # Large aggregate record sets must not inherit a 100,000-node whole-list cap.
    monkeypatch.setattr(owner, "_MIB", 1024*1024)
    records = [{"i": i} for i in range(100_000)]
    assert len(json.loads(owner._ob_records(records))) == 100_000
    with pytest.raises(IdentityError, match="record sequence"):
        owner._ob_records(records + [{"i": 100_000}])


@pytest.mark.parametrize("defect", ["clock", "missing", "duplicate", "scope"])
def test_observation_outer_membership_immediate_controls_survive_unknown_payload(defect):
    original, history, rows, master = _obs_base()
    history, rows = _obs_append(original, history, rows)
    attempt = history["attempts"][0]
    attempt["payload"] = {"schema": "future.v999"}
    if defect == "clock":
        rows[-1]["known_at"] = _obs_iso(_OBS_T0 + 999)
        rows[-1]["binding_sha256"] = _obs_hash({"schema": "mastermind.identity_alias_revision.v1",
            **{k: v for k, v in rows[-1].items() if k != "binding_sha256"}})
        attempt["row_membership"]["polygon:MU"] = [_obs_hash(rows[-1])]
    elif defect == "missing":
        attempt["row_membership"]["polygon:MU"] = []
    elif defect == "duplicate":
        attempt["row_membership"]["polygon:MU"] *= 2
    else:
        attempt["row_membership"]["extra"] = []
    _obs_seal(attempt, "attempt_sha256")
    with pytest.raises(IdentityError):
        _obs_snapshot(original, history, rows, master)


def test_observation_chain_row_bound_is_inclusive_and_not_truncated():
    from datetime import timedelta
    original, history, rows, master = _obs_base()
    history, rows = _obs_append(original, history, rows, listing=True)
    attempt = history["attempts"][0]
    family = attempt["payload"]["families"][0]
    symbols = ["DOMO", "HUCK"] + [f"NAME{i}" for i in range(63)]
    template = next(r for r in rows if r.get("alias_family_id") == "listing:domo")
    rows = [r for r in rows if r.get("alias_family_id") != "listing:domo"]
    family["symbols"] = symbols
    for index, symbol in enumerate(symbols):
        lo = (date(2026, 1, 1) + timedelta(days=index)).isoformat()
        hi = None if index == 64 else (date(2026, 1, 2) + timedelta(days=index)).isoformat()
        rows.append(dict(template, vendor_symbol=symbol, valid_from=lo, valid_to=hi))
    _obs_refresh_attempt(attempt, rows)
    snapshot, read = _obs_snapshot(original, history, rows, master)
    table = _obs_table(original, history, rows, snapshot)
    assert _obs_query(table, read, vendor="listing", symbol=symbols[-1]).status == "BOUND"
    assert len(attempt["row_membership"]["listing:domo"]) == 65
    family["symbols"].append("OVERFLOW")
    rows[-1]["valid_to"] = "2026-10-01"
    rows.append(dict(template, vendor_symbol="OVERFLOW", valid_from="2026-10-01", valid_to=None))
    _obs_refresh_attempt(attempt, rows)
    with pytest.raises(IdentityError, match="row membership bound"):
        _obs_snapshot(original, history, rows, master)


@pytest.mark.parametrize("defect", ["mic", "class", "security"])
def test_observation_revisions_cannot_change_established_family_identity(defect):
    original, history, rows, master, old_snapshot, _ = _obs_three_name_chain()
    attempt = history["attempts"][-1]; family = attempt["payload"]["families"][0]
    if defect == "mic":
        family["mic"] = "XNYS"
    elif defect == "class":
        family["security_class"] = "ORDINARY_CLASS_A"
    else:
        family["security_id"] = "SEC:US-XNAS-YYGH"
        for row in rows:
            if row.get("attempt_id") == attempt["attempt_id"] and row.get("alias_family_id") == family["family_id"]:
                row["security_id"] = family["security_id"]
    _obs_refresh_attempt(attempt, rows)
    snapshot, read = _obs_snapshot(original, history, rows, master)
    table = _obs_table(original, history, rows, old_snapshot, snapshot)
    with pytest.raises(IdentityError):
        _obs_query(table, read, vendor="listing", symbol="NEXT")


def test_observation_public_context_values_cannot_hide_duplicate_vectors():
    from dataclasses import replace
    original, history, rows, master = _obs_base()
    snapshot, read = _obs_snapshot(original, history, rows, master)
    table = _obs_table(original, history, rows, snapshot)
    duplicate_read = replace(read, artifact_sha256=(read.artifact_sha256[0],)*5)
    with pytest.raises(IdentityError, match="duplicate read artifact"):
        _obs_query(table, duplicate_read)
    duplicate_snapshot = replace(snapshot, artifact_bytes=(snapshot.artifact_bytes[0],)*5)
    with pytest.raises(IdentityError, match="duplicate snapshot artifact"):
        _obs_table(original, history, rows, duplicate_snapshot)
    with pytest.raises(IdentityError, match="read clock order"):
        record = read.as_record()
        record["read_started_at_utc_ns"] = str(int(record["read_completed_at_utc_ns"])+1)
        ReferenceReadReceipt.from_record(record)
    before_owner = replace(read, read_started_at_utc_ns=str(_OBS_T0-2),
                           read_completed_at_utc_ns=str(_OBS_T0-1))
    with pytest.raises(IdentityError, match="consumer read precedes"):
        _obs_query(table, before_owner)


def test_observation_json_wire_refuses_duplicate_keys_and_nonfinite_values():
    original, history, rows, master = _obs_base()
    snapshot, _ = _obs_snapshot(original, history, rows, master)
    for wire in (b'{"publication":{},"publication":{}}', b'{"invalid":NaN}', b'\xff'):
        with pytest.raises(IdentityError):
            validate_reference_snapshot(wire, dict(snapshot.artifact_bytes), wire,
                                        alias_records=rows, master_records=master)


def test_observation_acquisition_clock_order_is_visible_semantics_not_future_leakage():
    original, history, rows, master = _obs_base()
    old_snapshot, old_read = _obs_snapshot(original, history, rows, master, read_ns=_OBS_T0+500)
    expected = _obs_query(_obs_table(original, history, rows, old_snapshot), old_read)
    history, rows = _obs_append(original, history, rows)
    attempt = history["attempts"][0]
    attempt["payload"]["acquisition"]["polygon:MU"]["completed_at_utc_ns"] = str(_OBS_T0+1001)
    _obs_refresh_attempt(attempt, rows)
    new_snapshot, new_read = _obs_snapshot(original, history, rows, master)
    table = _obs_table(original, history, rows, old_snapshot, new_snapshot)
    assert _obs_query(table, old_read) == expected
    with pytest.raises(IdentityError, match="acquisition clock order"):
        _obs_query(table, new_read)


@pytest.mark.parametrize("upper", ["2026-10-07", "2026-10-06"])
def test_observation_repair_future_physical_interval_width_is_immediate(upper):
    original, history, rows, master = _obs_base()
    old_snapshot, old_read = _obs_snapshot(original, history, rows, master, read_ns=_OBS_T0+500)
    expected = _obs_query(_obs_table(original, history, rows, old_snapshot), old_read)
    future, future_rows = _obs_append(original, history, rows)
    # An intact unknown future layout is allowed for an older enrolled view,
    # including its valid physical rows and complete outer membership.
    valid_future = copy.deepcopy(future)
    valid_future["attempts"][0]["payload"] = {"schema": "future.v999"}
    _obs_seal(valid_future["attempts"][0], "attempt_sha256")
    valid_snapshot, valid_read = _obs_snapshot(original, valid_future, future_rows, master)
    valid_table = _obs_table(original, valid_future, future_rows, old_snapshot, valid_snapshot)
    assert _obs_query(valid_table, old_read, valid_read, cutoff=_OBS_T0+500) == expected

    # Recompute every affected seal before replacing the future payload.
    # Invalid width is intrinsic to the fixed physical row, not its payload.
    future_rows[-1]["valid_to"] = upper
    _obs_refresh_attempt(future["attempts"][0], future_rows)
    future["attempts"][0]["payload"] = {"schema": "future.v999"}
    _obs_seal(future["attempts"][0], "attempt_sha256")
    with pytest.raises(IdentityError, match="event interval width"):
        _obs_snapshot(original, future, future_rows, master)


@pytest.mark.parametrize("offset", ["+00:99", "-00:99", "+00:60", "-00:60", "+24:00", "-24:00"])
def test_observation_repair_empty_lookup_refuses_invalid_numeric_timezone_components(offset):
    with pytest.raises(IdentityError):
        VendorAliasTable().resolve_binding("polygon", "UNKNOWN", date(2026, 10, 7),
            decision_at="2026-10-07T08:00:00.123456789" + offset)


@pytest.mark.parametrize("direction", [-1, 1])
def test_observation_repair_valid_numeric_offsets_keep_exact_nine_digit_boundary(direction):
    from datetime import timedelta
    original, history, rows, master = _obs_base()
    read_ns = _OBS_T0 + 999
    snapshot, read = _obs_snapshot(original, history, rows, master, read_ns=read_ns)
    table = _obs_table(original, history, rows, snapshot)
    local = datetime.fromtimestamp(read_ns // 10**9, timezone.utc) + timedelta(minutes=direction*99)
    offset = "+01:39" if direction == 1 else "-01:39"
    before = local.strftime("%Y-%m-%dT%H:%M:%S") + ".000000998" + offset
    exact = local.strftime("%Y-%m-%dT%H:%M:%S") + ".000000999" + offset
    assert table.resolve_binding("polygon", "MU", date(2026, 10, 7),
        decision_at=before, snapshot_receipts=(read,)).reason == "NO_ENROLLED_SNAPSHOT_BY_CUTOFF"
    answer = table.resolve_binding("polygon", "MU", date(2026, 10, 7),
        decision_at=exact, snapshot_receipts=(read,))
    assert answer == _obs_query(table, read, cutoff=read_ns)
    assert answer.status == "BOUND"

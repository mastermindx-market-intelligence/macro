"""M01: the prospectively frozen market support matrix, pinned to the code.

Every claim in ``research/data_os_completion/2026-10-13/M01_SUPPORT_MATRIX.md`` is
proven here against the existing owners and the committed stores. New file only:
no calendar, identity, adapter, registry or price-view change is made or assumed.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lib.dataos.identity import (
    IdentityError,
    normalize_cn_symbol,
    normalize_hk_symbol,
    venue_currency,
    venue_timezone,
)
from lib.dataos.price import KNOWN_STORE_BASES, STORES_WITHOUT_OPEN, AdjustmentBasis
from lib.dataos.price_views import (
    SUPPORTED_FAMILIES,
    UNSUPPORTED_FAMILIES,
    RefusalReason,
    ViewRefusal,
    raw_view,
)
from lib.dataos.registry import load_registry
from lib.dataos.web_readers import inspect_file

REPO = Path(__file__).resolve().parents[1]
RECORD = REPO / "research/data_os_completion/2026-10-13/M01_SUPPORT_MATRIX.md"
D = "2024-01-02"

_NON_US_STORE_PREFIXES = (
    "data/hk_stocks",
    "data/china_stocks_raw",
    "data/canada_stocks",
    "data/hk_connect_roster",
)


@pytest.fixture(scope="module")
def registry():
    return load_registry(REPO / "config/dataset_registry.yml")


def _reason(rows, mic):
    with pytest.raises(ViewRefusal) as excinfo:
        raw_view(rows, mic=mic)
    return excinfo.value.reason


# ── M01.01 — every enrolled market keeps a real positive permitted read ──────


def test_m01_us_registry_row_is_produced_tradj_on_the_new_york_clock(registry):
    row = registry.get("equity.bars.daily.stocks")
    assert row is not None
    assert row.status.name == "PRODUCED"
    assert row.timezone == "America/New_York"
    assert str(getattr(row.basis, "value", row.basis)).lower() == "tradj"
    assert row.schema["close"]["basis"] == "tradj"
    assert row.schema["close"]["renames_to"] == "close_tradj"
    assert str(row.storage) == "data/stocks/{ticker}.parquet"
    assert KNOWN_STORE_BASES["data/stocks:close"] is AdjustmentBasis.TRADJ


@pytest.mark.parametrize("mic", ["XNAS", "XNYS", "ARCX"])
def test_m01_us_venues_keep_the_registry_clock_and_usd(registry, mic):
    row = registry.get("equity.bars.daily.stocks")
    assert venue_timezone(mic).key == row.timezone
    assert venue_currency(mic) == "USD"


@pytest.mark.needs_full_checkout("data")
def test_m01_us_store_has_a_real_positive_read():
    pq = pytest.importorskip("pyarrow.parquet")
    path = REPO / "data/stocks/NVDA.parquet"
    with path.open("rb") as fh:
        meta = inspect_file(fh, ".parquet", file_bytes=path.stat().st_size)
    assert {"close", "Date"} <= set(meta["columns"])
    assert "open" not in meta["columns"]
    assert "data/stocks" in STORES_WITHOUT_OPEN
    assert meta["row_count"] > 0


@pytest.mark.needs_full_checkout("data")
def test_m01_hk_roster_identities_agree_on_xhkg():
    pq = pytest.importorskip("pyarrow.parquet")
    rows = pq.read_table(
        REPO / "data/hk_connect_roster/roster.parquet", columns=["code5", "ticker"]
    ).to_pylist()
    populated = [r for r in rows if r["code5"] and r["ticker"]]
    assert len(populated) >= 700
    assert len({r["code5"] for r in populated}) >= 500
    failures = []
    for r in populated:
        from_code5 = normalize_hk_symbol(r["code5"])
        from_ticker = normalize_hk_symbol(r["ticker"])
        if not (
            from_code5.mic == from_ticker.mic == "XHKG"
            and from_code5.code == from_ticker.code
            and from_code5.code == r["code5"].zfill(5)
        ):
            failures.append((r["code5"], r["ticker"]))
    assert not failures, f"roster identities disagree: first 5 {failures[:5]}"


@pytest.mark.needs_full_checkout("data")
def test_m01_hk_store_stems_normalize_to_xhkg():
    pytest.importorskip("pyarrow.parquet")
    stems = [p.stem for p in sorted((REPO / "data/hk_stocks").glob("*.parquet"))]
    assert len(stems) >= 140
    failures = [s for s in stems if normalize_hk_symbol(s).mic != "XHKG"]
    assert not failures, f"stems refused or off-venue: first 5 {failures[:5]}"


@pytest.mark.needs_full_checkout("data")
def test_m01_cn_store_stems_normalize_to_their_exchange():
    pytest.importorskip("pyarrow.parquet")
    stems = [p.stem for p in sorted((REPO / "data/china_stocks_raw").glob("*.parquet"))]
    assert len(stems) >= 1700
    suffixes = {Path(s).suffix for s in stems}
    assert suffixes <= {".SS", ".SZ"}
    wanted = {".SS": "XSHG", ".SZ": "XSHE"}
    failures = [
        s for s in stems if normalize_cn_symbol(s).mic != wanted[Path(s).suffix]
    ]
    assert not failures, f"stems refused or off-venue: first 5 {failures[:5]}"


@pytest.mark.parametrize(
    "mic,tz,ccy",
    [
        ("XHKG", "Asia/Hong_Kong", "HKD"),
        ("XSHG", "Asia/Shanghai", "CNY"),
        ("XSHE", "Asia/Shanghai", "CNY"),
        ("XTSE", "America/Toronto", "CAD"),
    ],
)
def test_m01_non_us_venues_keep_their_local_clock_and_currency(mic, tz, ccy):
    assert venue_timezone(mic).key == tz
    assert venue_currency(mic) == ccy
    assert raw_view([{"date": D, "close_raw": "1"}], mic=mic).currency == ccy


# ── M01.02 — US assumptions cannot be copied silently to other markets ───────


@pytest.mark.parametrize("mic", ["XHKG", "XSHG", "XSHE"])
def test_m01_non_us_clocks_are_not_the_us_registry_clock(registry, mic):
    us_clock = registry.get("equity.bars.daily.stocks").timezone
    assert venue_timezone(mic).key != us_clock


@pytest.mark.parametrize(
    "mic,currency",
    [("XHKG", "USD"), ("XSHE", "USD"), ("XNAS", "HKD"), ("XSHG", "HKD")],
)
def test_m01_a_foreign_currency_column_is_refused(mic, currency):
    assert _reason(
        [{"date": D, "close_raw": "1", "currency": currency}], mic
    ) is RefusalReason.CURRENCY_MISMATCH


def test_m01_an_unenrolled_venue_has_no_clock():
    assert _reason([{"date": D, "close_raw": "1"}], "XLON") is (
        RefusalReason.VENUE_CLOCK_UNKNOWN
    )
    with pytest.raises(IdentityError):
        venue_timezone("XLON")


def test_m01_no_venue_means_no_currency_default():
    view = raw_view([{"date": D, "close_raw": "1"}])
    assert view.currency is None


@pytest.mark.parametrize(
    "market,symbol",
    [("hk", "NVDA"), ("cn", "NVDA"), ("cn", "0700.HK"), ("hk", "600519.SS")],
)
def test_m01_listing_symbols_do_not_cross_markets(market, symbol):
    normalizer = {"hk": normalize_hk_symbol, "cn": normalize_cn_symbol}[market]
    with pytest.raises(IdentityError):
        normalizer(symbol)


def test_m01_bare_volume_is_never_promoted_to_raw_volume():
    view = raw_view([{"date": D, "close_raw": "1", "volume": "5"}], mic="XNAS")
    assert view.rows[0]["volume"] == "5"
    assert "volume_raw" not in view.rows[0]


@pytest.mark.xfail(
    strict=True,
    reason="M01 limitation: raw_view does not police volume_sadj; "
    "a split-adjusted volume can ride a RAW view",
)
def test_m01_adjusted_volume_is_refused_by_the_raw_view():
    with pytest.raises(ViewRefusal):
        raw_view([{"date": D, "close_raw": "1", "volume_sadj": "5"}], mic="XNAS")


# ── M01.03 — no adjusted price ever answers an exchange-rule question ────────


@pytest.mark.parametrize("mic", ["XSHG", "XSHE", "XHKG", "XNAS"])
def test_m01_total_return_tape_is_refused_as_raw(mic):
    assert _reason([{"date": D, "close_tradj": "1"}], mic) is (
        RefusalReason.NON_RAW_INPUT
    )


@pytest.mark.parametrize("mic", ["XHKG", "XSHG"])
def test_m01_split_adjusted_tape_is_refused_as_raw(mic):
    assert _reason([{"date": D, "close_sadj": "1"}], mic) is (
        RefusalReason.DOUBLE_ADJUST_RISK
    )


def test_m01_tradj_is_unlawful_for_exchange_rule_work():
    assert "limit" in " ".join(AdjustmentBasis.TRADJ.unlawful_for)
    assert "DNR:KILL-CN-ADJUSTED-TAPE-LEGAL-LIMIT" in " ".join(
        AdjustmentBasis.TRADJ.unlawful_for
    )
    assert "exchange-rule tests" in " ".join(AdjustmentBasis.RAW.lawful_for)


@pytest.mark.needs_full_checkout("data")
@pytest.mark.parametrize(
    "store,mic",
    [
        ("data/hk_stocks/0700.HK.parquet", "XHKG"),
        ("data/china_stocks_raw/600519.SS.parquet", "XSHG"),
        ("data/stocks/NVDA.parquet", "XNAS"),
    ],
)
def test_m01_store_columns_without_a_basis_are_ambiguous(store, mic):
    pq = pytest.importorskip("pyarrow.parquet")
    table = pq.read_table(REPO / store, columns=["Date", "close"])
    rows = [
        {"date": str(r["Date"])[:10], "close": str(r["close"])}
        for r in table.slice(0, 3).to_pylist()
    ]
    assert _reason(rows, mic) is RefusalReason.AMBIGUOUS_BASIS


# ── M01.04 — scoped limitations, never a global PIT or whole-market claim ────


def test_m01_us_contract_claims_no_pit_and_no_population(registry):
    row = registry.get("equity.bars.daily.stocks")
    assert row.point_in_time_corporate_actions is False
    assert row.population == {}


def test_m01_non_us_stores_have_no_registry_contract(registry):
    hits = [
        c.dataset_id
        for c in registry.all()
        if str(c.storage).startswith(_NON_US_STORE_PREFIXES)
    ]
    assert hits == []


@pytest.mark.parametrize("symbol", ["430047.BJ", "830799.BJ"])
def test_m01_beijing_listings_are_not_enrolled(symbol):
    with pytest.raises(IdentityError):
        normalize_cn_symbol(symbol)
    assert venue_timezone("XBSE").key == "Asia/Shanghai"


@pytest.mark.needs_full_checkout("data")
def test_m01_canada_has_no_price_store():
    pytest.importorskip("pyarrow.parquet")
    canada = REPO / "data/canada_stocks"
    assert canada.is_dir()
    assert list(canada.glob("*.parquet")) == []


def test_m01_supported_action_families_are_exactly_three():
    assert sorted(f.value for f in SUPPORTED_FAMILIES) == [
        "cash_dividend",
        "forward_split",
        "reverse_split",
    ]
    assert sorted(f.value for f in UNSUPPORTED_FAMILIES) == [
        "merger",
        "return_of_capital",
        "rights_issue",
        "scrip",
        "spin_off",
        "stock_dividend",
    ]


def test_m01_terminal_view_is_proposed_not_enrolled(registry):
    row = registry.get("terminal.bars.daily.ohlc_json")
    assert row is not None
    assert row.status.name == "PROPOSED"


def test_m01_record_matches_the_code():
    lines = RECORD.read_text(encoding="utf-8").splitlines()
    statuses: dict[str, str] = {}
    for line in lines:
        if line.startswith("M01-STATUS "):
            parts = line.split()
            market, status = parts[1], parts[2]
            assert market not in statuses, f"{market} stated twice"
            statuses[market] = status
    assert statuses == {
        "US": "ENROLLED-POSITIVE",
        "HK": "IDENTITY-ONLY",
        "CN": "IDENTITY-ONLY",
        "CN-BSE": "NOT-ENROLLED",
        "CA": "NOT-ENROLLED",
    }
    supported = [ln for ln in lines if ln.startswith("M01-ACTIONS-SUPPORTED ")]
    assert len(supported) == 1
    assert supported[0].split()[1:] == sorted(f.value for f in SUPPORTED_FAMILIES)
    unsupported = [ln for ln in lines if ln.startswith("M01-ACTIONS-UNSUPPORTED ")]
    assert len(unsupported) == 1
    assert unsupported[0].split()[1:] == sorted(f.value for f in UNSUPPORTED_FAMILIES)
    text = RECORD.read_text(encoding="utf-8").lower()
    assert "no global pit claim" in text
    assert "terminal.bars.daily.ohlc_json" in text
    assert "validated" not in text

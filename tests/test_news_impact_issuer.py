"""Hermetic tests for engine/news_impact/issuer.py (lane B4_issuer).

Stdlib + pytest + jsonschema only.  No network, no repo data files unless
they are absent-safe (the real-ledger test skips with a reason when the file
is missing — the lane clone has an empty working tree).  Every fixture
registry/ledger is built in-memory here.
"""
import os
from collections.abc import Mapping
from datetime import date, datetime
from pathlib import Path

import pytest

from engine.company_intelligence.identity import (
    IssuerIdentity,
    IssuerRegistry,
    ListingAlias,
)
from engine.news_impact import issuer

try:
    from jsonschema import Draft202012Validator
    HAVE_JSONSCHEMA = True
except ImportError:  # pragma: no cover - host-dependent
    HAVE_JSONSCHEMA = False

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "contracts" / "news_impact" / "news_impact_event.v1.schema.json"

ASOF = date(2026, 10, 11)


# ---------------------------------------------------------------- fixtures
def _alias(ticker, mic, share_class, valid_from, valid_to=None, primary=False):
    return ListingAlias(
        ticker=ticker,
        mic=mic,
        share_class=share_class,
        trading_currency="USD",
        is_primary=primary,
        valid_from=valid_from,
        valid_to=valid_to,
    )


def make_registry() -> IssuerRegistry:
    acme = IssuerIdentity(
        company_id="cik:0000001750",
        display_name="ACME Corp",
        fiscal_year_end_month=12,
        reporting_currency="USD",
        listings=(
            _alias("ACME", "XNAS", "A", date(2020, 1, 1), primary=True),
            _alias("ACMEB", "XNAS", "B", date(2020, 1, 1)),
        ),
    )
    berkshire = IssuerIdentity(
        company_id="cik:0001067983",
        display_name="Berkshire Hathaway Inc",
        fiscal_year_end_month=12,
        reporting_currency="USD",
        listings=(
            _alias("BRK-B", "XNYS", "B", date(1996, 5, 9), primary=True),
            _alias("BRK-A", "XNYS", "A", date(1970, 1, 1)),
        ),
    )
    # A ticker that changed hands: the half-open window means no overlap.
    oldco = IssuerIdentity(
        company_id="cik:0000009999",
        display_name="Old Wave Inc",
        fiscal_year_end_month=12,
        reporting_currency="USD",
        listings=(_alias("WAVE", "XNAS", "A", date(2000, 1, 1), date(2015, 6, 1)),),
    )
    newco = IssuerIdentity(
        company_id="cik:0000008888",
        display_name="New Wave Inc",
        fiscal_year_end_month=12,
        reporting_currency="USD",
        listings=(_alias("WAVE", "XNAS", "A", date(2015, 6, 1)),),
    )
    return IssuerRegistry([acme, berkshire, oldco, newco])


def make_ledger():
    return {
        "AAPL": [("cik:0000320193", None, None)],
        "MSFT": [("cik:0000789019", None, None)],
        "TSLA": [("cik:0001318605", None, None)],
        "GONE": [("cik:0000005555", date(1999, 1, 1), date(2001, 1, 1))],
        "DUAL": [
            ("cik:0000000001", date(1990, 1, 1), None),
            ("cik:0000000002", date(1990, 1, 1), None),
        ],
    }


def mention(**kwargs):
    defaults = dict(text="", ticker=None, cik=None, exchange_mic=None, asof=ASOF)
    defaults.update(kwargs)
    return issuer.Mention(**defaults)


def rungs_of(resolution):
    return resolution.receipt["rungs"]


# ---------------------------------------------------------------- constants
def test_constants_are_closed():
    assert issuer.RESOLVER_VERSION == "ni-issuer-1"
    assert issuer.RUNGS == ("explicit_cik", "registry", "ledger", "absent")
    assert issuer.ABSENCE_REASONS == (
        "unknown_ticker",
        "ambiguous_ticker",
        "not_listed_at_asof",
        "name_only_mention",
        "malformed_identifier",
        "no_mention",
    )


def test_canonical_ticker_one_documented_rule():
    assert issuer.canonical_ticker("$TSLA") == "TSLA"
    assert issuer.canonical_ticker(" brk.b ") == "BRK-B"  # . -> - share class
    assert issuer.canonical_ticker("BF-B") == "BF-B"
    assert issuer.canonical_ticker("$$X") == "$X"  # one leading $ only
    assert issuer.canonical_ticker("") is None
    assert issuer.canonical_ticker(None) is None


def test_mention_rejects_non_date_asof():
    with pytest.raises(ValueError) as exc:
        mention(asof="2026-01-01")
    assert str(exc.value) == "Mention.asof must be a datetime.date: '2026-01-01'"


def test_mention_normalises_datetime_to_date():
    assert mention(asof=datetime(2026, 10, 11, 15, 30)).asof == ASOF


# ---------------------------------------------------------------- rung 1
def test_explicit_cik_resolves():
    res = issuer.resolve_mention(mention(cik="320193"), registry=None, ledger=None)
    assert (res.company_id, res.rung) == ("cik:0000320193", "explicit_cik")
    assert res.candidates == ("cik:0000320193",)
    assert [r["rung"] for r in rungs_of(res)] == ["explicit_cik"]
    assert rungs_of(res)[0]["outcome"] == "resolved"


def test_explicit_cik_wins_over_conflicting_ticker():
    res = issuer.resolve_mention(
        mention(cik="320193", ticker="MSFT"),
        registry=make_registry(),
        ledger=make_ledger(),
    )
    assert (res.company_id, res.rung) == ("cik:0000320193", "explicit_cik")
    # Both identifiers are on the record; the ticker rungs never ran.
    rung = rungs_of(res)[0]
    assert rung["input"] == {"cik": "320193", "ticker": "MSFT", "asof": ASOF.isoformat()}
    assert rung["note"] == "ticker not consulted (explicit identifier wins)"
    assert [r["rung"] for r in rungs_of(res)] == ["explicit_cik"]


def test_malformed_cik_is_terminal_never_a_guess():
    res = issuer.resolve_mention(
        mention(cik="12x40", ticker="AAPL"),
        registry=make_registry(),
        ledger=make_ledger(),
    )
    assert res.company_id is None
    assert res.rung == "absent"
    assert res.absence_reason == "malformed_identifier"
    assert res.candidates == ()
    rung = rungs_of(res)[0]
    assert rung["outcome"] == "malformed"
    assert rung["note"] == "malformed cik; ticker not consulted (never a guess)"
    assert rungs_of(res)[1] == {
        "rung": "absent",
        "input": {"ticker": "AAPL", "cik": "12x40", "asof": ASOF.isoformat()},
        "outcome": "malformed_identifier",
    }


# ---------------------------------------------------------------- rung 2
def test_registry_rung_resolves_with_sibling_security_ids():
    res = issuer.resolve_mention(
        mention(text="ACME wins contract", ticker="ACME"),
        registry=make_registry(),
        ledger=make_ledger(),
    )
    assert (res.company_id, res.rung) == ("cik:0000001750", "registry")
    assert res.sibling_security_ids == ("xnas:ACMEB",)
    assert res.receipt["sibling_tickers"] == ("ACME", "ACMEB")


def test_registry_is_point_in_time_on_a_handoff_ticker():
    reg = make_registry()
    early = issuer.resolve_mention(mention(ticker="WAVE", asof=date(2010, 1, 1)), registry=reg, ledger=None)
    late = issuer.resolve_mention(mention(ticker="WAVE", asof=date(2020, 1, 1)), registry=reg, ledger=None)
    assert early.company_id == "cik:0000009999"
    assert late.company_id == "cik:0000008888"


def test_registry_miss_falls_through_to_ledger():
    res = issuer.resolve_mention(
        mention(ticker="AAPL"), registry=make_registry(), ledger=make_ledger()
    )
    assert (res.company_id, res.rung) == ("cik:0000320193", "ledger")
    assert [(r["rung"], r["outcome"]) for r in rungs_of(res)] == [
        ("registry", "not_found"),
        ("ledger", "resolved"),
    ]


# ---------------------------------------------------------------- rung 3
def test_ambiguous_ticker_lists_every_candidate():
    res = issuer.resolve_mention(
        mention(ticker="DUAL"), registry=None, ledger=make_ledger()
    )
    assert res.company_id is None
    assert res.absence_reason == "ambiguous_ticker"
    assert res.candidates == ("cik:0000000001", "cik:0000000002")


def test_delisted_at_asof_is_not_listed_at_asof():
    res = issuer.resolve_mention(
        mention(ticker="GONE"), registry=None, ledger=make_ledger()
    )
    assert res.company_id is None
    assert res.absence_reason == "not_listed_at_asof"
    assert res.candidates == ("cik:0000005555",)


def test_ledger_without_dates_says_so_in_the_receipt():
    res = issuer.resolve_mention(
        mention(ticker="AAPL"), registry=None, ledger=make_ledger()
    )
    ledger_rung = rungs_of(res)[0]
    assert ledger_rung["note"] == issuer.NO_VALIDITY_DATES_NOTE
    assert ledger_rung["note"] == "ledger has no validity dates"


def test_dollar_prefixed_ticker_normalises():
    res = issuer.resolve_mention(
        mention(text="$tsla rallies", ticker="$tsla"), registry=None, ledger=make_ledger()
    )
    assert (res.company_id, res.rung) == ("cik:0001318605", "ledger")


def test_share_class_dot_variant_resolves_registry_rung():
    res = issuer.resolve_mention(
        mention(ticker="BRK.B"), registry=make_registry(), ledger=make_ledger()
    )
    assert (res.company_id, res.rung) == ("cik:0001067983", "registry")
    assert res.sibling_security_ids == ("xnys:BRK-A",)


# ---------------------------------------------------------------- rung 4
def test_unknown_ticker():
    res = issuer.resolve_mention(
        mention(text="rally", ticker="ZZZZ"), registry=make_registry(), ledger=make_ledger()
    )
    assert res.absence_reason == "unknown_ticker"
    assert [r["outcome"] for r in rungs_of(res)] == ["not_found", "not_found", "unknown_ticker"]


def test_name_only_mention_is_typed_absence():
    res = issuer.resolve_mention(mention(text="Big Tech Inc"), registry=None, ledger=None)
    assert res.absence_reason == "name_only_mention"
    assert [r["rung"] for r in rungs_of(res)] == ["absent"]


def test_no_mention():
    res = issuer.resolve_mention(mention(text="   "), registry=None, ledger=None)
    assert res.absence_reason == "no_mention"


# ---------------------------------------------------------------- payload
def _absence_fixture_mentions():
    return {
        "unknown_ticker": mention(text="rally", ticker="ZZZZ"),
        "ambiguous_ticker": mention(ticker="DUAL"),
        "not_listed_at_asof": mention(ticker="GONE"),
        "name_only_mention": mention(text="Big Tech Inc"),
        "malformed_identifier": mention(cik="x1"),
        "no_mention": mention(text=""),
    }


def test_absence_payload_targets_owner_typed_absence_v1():
    if not HAVE_JSONSCHEMA:
        pytest.skip("jsonschema not installed on this host")
    if not SCHEMA_PATH.exists():
        pytest.skip("frozen schema not present next to src/")
    import json

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(
        {"$ref": "#/$defs/owner_typed_absence_v1", "$defs": schema["$defs"]}
    )
    for reason, m in sorted(_absence_fixture_mentions().items()):
        res = issuer.resolve_mention(m, registry=make_registry(), ledger=make_ledger())
        assert res.absence_reason == reason
        payload = issuer.absence_payload(res)
        assert payload["reason"] == "unjoinable_filing_identity"
        assert reason in payload["detail"]
        errors = list(validator.iter_errors(payload))
        assert not errors, f"{reason}: {errors}"


def test_absence_payload_raises_for_resolved():
    res = issuer.resolve_mention(mention(cik="320193"), registry=None, ledger=None)
    with pytest.raises(ValueError) as exc:
        issuer.absence_payload(res)
    assert str(exc.value) == "resolution is not an absence: cik:0000320193"


# ---------------------------------------------------------------- batch
def test_resolve_batch_counts_every_rung_and_reason_key():
    ms = list(_absence_fixture_mentions().values()) + [
        mention(cik="320193"),
        mention(ticker="ACME"),
        mention(ticker="AAPL"),
    ]
    resolutions, counts = issuer.resolve_batch(
        ms, registry=make_registry(), ledger=make_ledger()
    )
    assert len(resolutions) == len(ms)
    assert counts["by_rung"] == {
        "explicit_cik": 1,
        "registry": 1,
        "ledger": 1,
        "absent": 6,
    }
    assert counts["by_absence_reason"] == {
        "unknown_ticker": 1,
        "ambiguous_ticker": 1,
        "not_listed_at_asof": 1,
        "name_only_mention": 1,
        "malformed_identifier": 1,
        "no_mention": 1,
    }


def test_resolve_batch_zero_keys_present():
    _, counts = issuer.resolve_batch([], registry=None, ledger=None)
    assert counts["by_rung"] == {r: 0 for r in issuer.RUNGS}
    assert counts["by_absence_reason"] == {r: 0 for r in issuer.ABSENCE_REASONS}


def test_determinism_same_inputs_same_output():
    ms = list(_absence_fixture_mentions().values()) + [mention(cik="320193"), mention(ticker="BRK.B")]
    first, _ = issuer.resolve_batch(ms, registry=make_registry(), ledger=make_ledger())
    second, _ = issuer.resolve_batch(ms, registry=make_registry(), ledger=make_ledger())
    assert first == second
    assert repr(first) == repr(second)


# ---------------------------------------------------------------- ledger io
def test_load_ledger_estate_shape(tmp_path):
    p = tmp_path / "ledger.json"
    p.write_text(
        '{"note": "accreting map", "tickers": {"MSFT": 789019, "AAPL": "320193"}}',
        encoding="utf-8",
    )
    led = issuer.load_ledger(p)
    assert isinstance(led, Mapping)
    assert len(led) == 2
    assert led["AAPL"] == (("cik:0000320193", None, None),)
    assert led["MSFT"] == (("cik:0000789019", None, None),)
    assert led.has_validity_dates is False
    assert list(led) == ["AAPL", "MSFT"]  # sorted iteration
    with pytest.raises(TypeError):
        led["AAPL"] = ()


def test_load_ledger_dated_shapes(tmp_path):
    p = tmp_path / "dated.json"
    p.write_text(
        '{"tickers": {'
        ' "WAVE": [{"cik": "8888", "valid_from": "2015-06-01"},'
        '          {"cik": "9999", "valid_from": "2000-01-01", "valid_to": "2015-06-01"}],'
        ' "A": ["123", "1990-01-01", null]}}',
        encoding="utf-8",
    )
    led = issuer.load_ledger(p)
    assert led.has_validity_dates is True
    assert led["WAVE"] == (
        ("cik:0000008888", date(2015, 6, 1), None),
        ("cik:0000009999", date(2000, 1, 1), date(2015, 6, 1)),
    )
    assert led["A"] == (("cik:0000000123", date(1990, 1, 1), None),)


def test_load_ledger_error_paths(tmp_path):
    missing = tmp_path / "absent.json"
    with pytest.raises(issuer.LedgerError, match="^ledger unreadable: "):
        issuer.load_ledger(missing)
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(issuer.LedgerError, match="^ledger unreadable: "):
        issuer.load_ledger(bad)
    arr = tmp_path / "arr.json"
    arr.write_text("[]", encoding="utf-8")
    with pytest.raises(issuer.LedgerError) as exc:
        issuer.load_ledger(arr)
    assert str(exc.value) == f"ledger not a JSON object: {arr}"
    nokey = tmp_path / "nokey.json"
    nokey.write_text('{"note": "x"}', encoding="utf-8")
    with pytest.raises(issuer.LedgerError) as exc:
        issuer.load_ledger(nokey)
    assert str(exc.value) == f"ledger missing 'tickers' mapping: {nokey}"
    badcik = tmp_path / "badcik.json"
    badcik.write_text('{"tickers": {"AAPL": {"cik": "ab"}}}', encoding="utf-8")
    with pytest.raises(issuer.LedgerError) as exc:
        issuer.load_ledger(badcik)
    assert str(exc.value) == f"ledger entry not a CIK: AAPL='ab' in {badcik}"
    nocik = tmp_path / "nocik.json"
    nocik.write_text('{"tickers": {"AAPL": {"valid_from": "2000-01-01"}}}', encoding="utf-8")
    with pytest.raises(issuer.LedgerError) as exc:
        issuer.load_ledger(nocik)
    assert str(exc.value) == f"ledger entry missing 'cik': AAPL in {nocik}"
    baddate = tmp_path / "baddate.json"
    baddate.write_text('{"tickers": {"AAPL": {"cik": "320193", "valid_from": "01/02/2000"}}}', encoding="utf-8")
    with pytest.raises(issuer.LedgerError) as exc:
        issuer.load_ledger(baddate)
    assert str(exc.value) == (
        f"ledger entry date not ISO: AAPL.valid_from='01/02/2000' in {baddate}"
    )
    emptywin = tmp_path / "emptywin.json"
    emptywin.write_text(
        '{"tickers": {"AAPL": {"cik": "320193", "valid_from": "2001-01-01", "valid_to": "2001-01-01"}}}',
        encoding="utf-8",
    )
    with pytest.raises(issuer.LedgerError) as exc:
        issuer.load_ledger(emptywin)
    assert str(exc.value) == (
        f"ledger entry window empty: AAPL=[2001-01-01,2001-01-01] in {emptywin}"
    )
    malformed = tmp_path / "malformed.json"
    malformed.write_text('{"tickers": {"AAPL": {"cik": "320193"}, "X": 1.5}}', encoding="utf-8")
    with pytest.raises(issuer.LedgerError) as exc:
        issuer.load_ledger(malformed)
    assert str(exc.value) == f"ledger entry malformed: X=1.5 in {malformed}"


# ---------------------------------------------------------------- real data
REAL_LEDGER_CANDIDATES = [
    Path(os.environ.get("NI_REAL_LEDGER", "/nonexistent")),
    Path(__file__).resolve().parents[1] / "data" / "edgar" / "ticker_cik_ledger.json",
]
REAL_LEDGER = next((p for p in REAL_LEDGER_CANDIDATES if p.exists()), None)


@pytest.mark.skipif(REAL_LEDGER is None, reason="data/edgar/ticker_cik_ledger.json not checked out (sparse worktree)")
def test_real_ledger_resolves_three_tickers():
    led = issuer.load_ledger(REAL_LEDGER)
    assert len(led) > 1000
    assert led.has_validity_dates is False
    for ticker, expected in (
        ("AAPL", "cik:0000320193"),
        ("MSFT", "cik:0000789019"),
        ("BRK-B", "cik:0001067983"),
    ):
        res = issuer.resolve_mention(mention(ticker=ticker), registry=None, ledger=led)
        assert (res.company_id, res.rung) == (expected, "ledger")
        assert res.receipt["rungs"][0]["note"] == "ledger has no validity dates"

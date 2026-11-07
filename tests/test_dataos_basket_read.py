"""Mode-bound basket composition reads (U04) — ``lib/dataos/basket_read.py``.

Synthetic fixtures only: an injected membership reader and resolver, price rows
built through the REAL read-contract owner, no ``data/`` files, no network, no
wall clock.

Run: python3 -m pytest tests/test_dataos_basket_read.py -q
"""

from __future__ import annotations

import dataclasses
import json
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from lib.dataos.basket_read import (
    BasketRead,
    BasketReadRefusal,
    BasketRefusalCode,
    EvidenceMode,
    PopulationKind,
    population_delta,
    read_basket,
)
from lib.dataos.identity import IdentityError
from lib.dataos.nulls import MissingReason
from lib.dataos.read_contract import (
    CurrentEvidence,
    Dependency,
    Disposition,
    MemberDisposition,
    ReadContractError,
    ReadMode,
    ReadRefusal,
    ReadRequest,
    RefusalCode,
    SourceSegment,
    ViewContract,
    account_coverage,
    current,
    reconstruct,
)
from lib.dataos.temporal import TemporalProfile

REPO_ROOT = Path(__file__).resolve().parents[1]
CODE_VERSION = "a1" * 20
CUTOFF = "2026-01-05T10:00:00+00:00"
DAY = date(2026, 1, 4)
TICKERS = ("600036", "600519")
LISTINGS = {"600036": "CN-XSHG-600036", "600519": "CN-XSHG-600519"}
_UNSET = object()


def _contract(**over) -> ViewContract:
    fields = dict(
        purpose="unit-test view pinning the U04 mode-bound basket read",
        identity={"security_id": "BASKET-AI", "listing_id": "BASKET-AI"},
        field_units={"close": "CNY/share"},
        adjustment_reference={"basis": "raw"},
        coverage="synthetic U04 basket local to this suite",
    )
    fields.update(over)
    return ViewContract(**fields)


def _evidence(**over) -> CurrentEvidence:
    fields = dict(
        receipt_sha256s=("ab" * 32,),
        identity_generation_id="ident-gen-7",
        action_revision_set_id="revset-3",
        code_version=CODE_VERSION,
    )
    fields.update(over)
    return CurrentEvidence(**fields)


def _row(listing="CN-XSHG-600519", source="primary", basis="raw") -> dict:
    return {"listing_id": listing, "source": source, "basis": basis,
            "close": "1700.00", "ingested_at": "2026-01-04T08:00:00+00:00",
            "published_at": "2026-01-04T06:00:00+00:00"}


ROWS = (_row("CN-XSHG-600519"), _row("CN-XSHG-600036"))


def _membership(**over) -> dict:
    fields = dict(
        basket_id="BK1", suite="baskets_china_ths", asof="2026-01-04",
        members=list(TICKERS), pit=True, basis="pit_snapshot",
        snapshot_date="2026-01-04", source_shape="membership", note="",
    )
    fields.update(over)
    return fields


class _Reader:
    """Injected membership reader that records every call and replays a payload."""

    def __init__(self, payload: dict):
        self.payload = payload
        self.calls: list[tuple] = []

    def __call__(self, basket_id, day_iso, *, suite):
        self.calls.append((basket_id, day_iso, suite))
        return dict(self.payload)


class _Resolver:
    """Injected ticker -> listing id lookup that records every call."""

    def __init__(self, mapping=None):
        self.mapping = dict(LISTINGS if mapping is None else mapping)
        self.calls: list[tuple] = []

    def __call__(self, ticker, day):
        self.calls.append((ticker, day))
        return self.mapping.get(ticker)


def _reconstruct_read(*, cutoff=CUTOFF, clock="ingested_at", rows=None, dep="prices"):
    rows = ROWS if rows is None else rows
    request = ReadRequest(ReadMode.RECONSTRUCT, _contract(), cutoff=cutoff, clock=clock)
    return reconstruct(
        request, {dep: Dependency(name=dep, profile=TemporalProfile.BARS, rows=rows)},
        required=(dep,), code_version=CODE_VERSION)


def _current_read(rows=None, dep="prices"):
    rows = ROWS if rows is None else rows
    request = ReadRequest(ReadMode.CURRENT, _contract())
    return current(
        request, {dep: Dependency(name=dep, profile=TemporalProfile.BARS, rows=rows)},
        evidence=_evidence())


def _read(*, mode="RECONSTRUCT", cutoff=CUTOFF, basket_id="BK1",
          suite="baskets_china_ths", membership=None,
          expected=PopulationKind.CURATED_CAPPED, session_day=_UNSET,
          fallback_sources=(), price_read=None, reader=None, resolver=None):
    """Run read_basket through the real owner with synthetic fakes injected."""
    if price_read is None:
        price_read = (_reconstruct_read(cutoff=cutoff) if mode == "RECONSTRUCT"
                      else _current_read())
    if session_day is _UNSET:
        session_day = None if mode == "RECONSTRUCT" else DAY
    payload = _membership() if membership is None else _membership(**membership)
    if reader is None:
        reader = _Reader(payload)
    if resolver is None:
        resolver = _Resolver()
    if mode == "RECONSTRUCT":
        request = ReadRequest(ReadMode.RECONSTRUCT, _contract(), cutoff=cutoff,
                              clock="ingested_at")
    else:
        request = ReadRequest(ReadMode.CURRENT, _contract())
    return read_basket(request, basket_id=basket_id, suite=suite,
                       price_read=price_read, resolve=resolver,
                       expected_population=expected, session_day=session_day,
                       membership_reader=reader, fallback_sources=fallback_sources)


def test_u04_reconstruct_binds_membership_identity_and_price_to_one_request() -> None:
    reader, resolver = _Reader(_membership()), _Resolver()
    got = _read(reader=reader, resolver=resolver)
    assert reader.calls == [("BK1", "2026-01-04", "baskets_china_ths")]
    assert [ticker for ticker, _ in resolver.calls] == sorted(TICKERS)
    assert {d for _, d in resolver.calls} == {DAY}
    assert got.result.label == "reconstruction"
    assert got.result.mode is ReadMode.RECONSTRUCT
    assert got.coverage.population == got.member_keys
    assert got.member_keys == ("CN-XSHG-600036", "CN-XSHG-600519")
    assert all(got.coverage.disposition_of(k).disposition is Disposition.SERVED
               for k in got.member_keys)
    assert got.result.evidence["basket"]["evidence_mode"] == "PIT_SNAPSHOT"
    assert got.result.evidence["cutoff"] == CUTOFF


def test_u04_current_read_is_labelled_current_and_marks_current_membership() -> None:
    got = _read(mode="CURRENT", membership=dict(
        pit=False, basis="current_membership", source_shape=None,
        snapshot_date=None))
    assert got.result.label == "current"
    assert got.evidence_mode is EvidenceMode.CURRENT_MEMBERSHIP
    assert got.population_kind is PopulationKind.CURATED_CAPPED
    block = got.result.evidence["basket"]
    assert block["basis"] == "current_membership"
    assert block["pit"] is False


def test_u04_lookahead_membership_never_funds_a_reconstruction() -> None:
    with pytest.raises(BasketReadRefusal) as exc:
        _read(membership=dict(pit=False, basis="current_membership",
                              source_shape=None, snapshot_date=None))
    assert exc.value.code is BasketRefusalCode.LOOKAHEAD_MEMBERSHIP


def test_u04_replay_is_refused() -> None:
    request = ReadRequest(ReadMode.REPLAY, _contract(), output_id="out-1")
    with pytest.raises(BasketReadRefusal) as exc:
        read_basket(request, basket_id="BK1", suite="baskets_china_ths",
                    price_read=_reconstruct_read(), resolve=_Resolver(),
                    expected_population=PopulationKind.CURATED_CAPPED)
    assert exc.value.code is BasketRefusalCode.MODE_UNSUPPORTED


def test_u04_price_read_in_another_mode_is_refused() -> None:
    with pytest.raises(BasketReadRefusal) as exc:
        _read(price_read=_current_read())
    assert exc.value.code is BasketRefusalCode.MODE_MISMATCH


def test_u04_price_read_under_another_contract_is_refused() -> None:
    request = ReadRequest(ReadMode.RECONSTRUCT, _contract(purpose="a different view"),
                          cutoff=CUTOFF, clock="ingested_at")
    with pytest.raises(BasketReadRefusal) as exc:
        read_basket(request, basket_id="BK1", suite="baskets_china_ths",
                    price_read=_reconstruct_read(), resolve=_Resolver(),
                    expected_population=PopulationKind.CURATED_CAPPED)
    assert exc.value.code is BasketRefusalCode.CONTRACT_MISMATCH


@pytest.mark.parametrize(
    "kwargs", [{"cutoff": "2026-01-06T10:00:00+00:00"}, {"clock": "published_at"}],
    ids=["other-cutoff", "clock-published-at"])
def test_u04_price_read_at_another_cutoff_or_clock_is_refused(kwargs) -> None:
    with pytest.raises(BasketReadRefusal) as exc:
        _read(price_read=_reconstruct_read(**kwargs))
    assert exc.value.code is BasketRefusalCode.CUTOFF_MISMATCH


def test_u04_accounted_price_read_is_refused() -> None:
    base = _reconstruct_read()
    accounted = dataclasses.replace(base, coverage=account_coverage(
        _contract(), ("CN-XSHG-600519",),
        (MemberDisposition("CN-XSHG-600519", Disposition.SERVED,
                           segments=(SourceSegment("primary", "raw",
                                                   "CN-XSHG-600519"),)),)))
    with pytest.raises(BasketReadRefusal) as exc:
        _read(price_read=accounted)
    assert exc.value.code is BasketRefusalCode.ALREADY_ACCOUNTED


def test_u04_unbound_prices_dependency_is_refused() -> None:
    with pytest.raises(BasketReadRefusal) as exc:
        _read(price_read=_reconstruct_read(dep="closes"))
    assert exc.value.code is BasketRefusalCode.PRICES_UNBOUND


def test_u04_reconstruct_refuses_a_caller_session_day() -> None:
    with pytest.raises(BasketReadRefusal) as exc:
        _read(session_day=DAY)
    assert exc.value.code is BasketRefusalCode.DAY_CONFLICT


@pytest.mark.parametrize(
    "session_day", [None, datetime(2026, 1, 4, tzinfo=timezone.utc), "2026-01-04"])
def test_u04_current_requires_a_calendar_date(session_day) -> None:
    with pytest.raises(BasketReadRefusal) as exc:
        _read(mode="CURRENT", session_day=session_day)
    assert exc.value.code is BasketRefusalCode.DAY_CONFLICT


def test_u04_unknown_suite_is_refused() -> None:
    with pytest.raises(BasketReadRefusal) as exc:
        _read(suite="baskets_mars")
    assert exc.value.code is BasketRefusalCode.UNKNOWN_SUITE


@pytest.mark.parametrize(
    "over", [{"basket_id": "BK2"}, {"suite": "baskets"}, {"asof": "2026-01-03"}])
def test_u04_reader_echo_mismatch_is_refused(over) -> None:
    with pytest.raises(BasketReadRefusal) as exc:
        _read(membership=over)
    assert exc.value.code is BasketRefusalCode.MEMBERSHIP_ECHO_MISMATCH


@pytest.mark.parametrize(
    "pair", [(True, "current_membership"), (False, "pit_snapshot"),
             (1, "pit_snapshot"), (True, "something_else"),
             (True, "membership_unreadable")])
def test_u04_unlawful_pit_basis_pairs_are_malformed(pair) -> None:
    with pytest.raises(BasketReadRefusal) as exc:
        _read(membership=dict(pit=pair[0], basis=pair[1]))
    assert exc.value.code is BasketRefusalCode.MALFORMED_MEMBERSHIP


@pytest.mark.parametrize(
    "members", [None, ["600519", ""], ["600519", "600519"]])
def test_u04_malformed_member_lists_are_refused(members) -> None:
    with pytest.raises(BasketReadRefusal) as exc:
        _read(membership=dict(members=members))
    assert exc.value.code is BasketRefusalCode.MALFORMED_MEMBERSHIP


def test_u04_unknown_basket_is_refused() -> None:
    with pytest.raises(BasketReadRefusal) as exc:
        _read(membership=dict(pit=False, basis="unknown_basket", snapshot_date=None,
                              source_shape=None))
    assert exc.value.code is BasketRefusalCode.UNKNOWN_BASKET


def test_u04_empty_membership_is_refused() -> None:
    with pytest.raises(BasketReadRefusal) as exc:
        _read(membership=dict(members=[]))
    assert exc.value.code is BasketRefusalCode.EMPTY_MEMBERSHIP


def test_u04_snapshot_dated_after_the_membership_day_is_refused() -> None:
    with pytest.raises(BasketReadRefusal) as exc:
        _read(membership=dict(snapshot_date="2026-01-05"))
    assert exc.value.code is BasketRefusalCode.SNAPSHOT_AFTER_DAY


@pytest.mark.parametrize(
    "over,kind,mode",
    [
        (dict(pit=True, basis="pit_snapshot", source_shape="membership"),
         PopulationKind.CURATED_CAPPED, "RECONSTRUCT"),
        (dict(pit=True, basis="pit_snapshot", source_shape="ths_concept_dump"),
         PopulationKind.VENDOR_UNIVERSE, "RECONSTRUCT"),
        (dict(pit=False, basis="current_membership", source_shape=None,
              snapshot_date=None),
         PopulationKind.CURATED_CAPPED, "CURRENT"),
    ])
def test_u04_population_kind_follows_the_source_shape(over, kind, mode) -> None:
    got = _read(mode=mode, membership=over, expected=kind)
    assert got.population_kind is kind


def test_u04_unknown_source_shape_is_refused() -> None:
    with pytest.raises(BasketReadRefusal) as exc:
        _read(membership=dict(source_shape="board_dump_v9"))
    assert exc.value.code is BasketRefusalCode.UNKNOWN_POPULATION


def test_u04_population_kind_mismatch_is_refused() -> None:
    with pytest.raises(BasketReadRefusal) as exc:
        _read(membership=dict(source_shape="ths_concept_dump"))
    assert exc.value.code is BasketRefusalCode.POPULATION_KIND_MISMATCH


def test_u04_vendor_universe_read_carries_the_current_concept_mapping_caveat() -> None:
    got = _read(membership=dict(source_shape="ths_concept_dump"),
                expected=PopulationKind.VENDOR_UNIVERSE)
    assert got.result.evidence["basket"]["concept_mapping"] == "current"


def test_u04_unresolved_ticker_is_never_inspected_not_dropped() -> None:
    got = _read(resolver=_Resolver({"600036": "CN-XSHG-600036"}))
    assert len(got.coverage.population) == len(TICKERS) == 2
    key = "unresolved:600519"
    assert key in got.coverage.population
    entry = got.coverage.disposition_of(key)
    assert entry.disposition is Disposition.NEVER_INSPECTED
    assert got.coverage.qualified_fraction < 1


@pytest.mark.parametrize("resolved", ["600519", "CN-XSHG-abc", 42])
def test_u04_malformed_resolved_identity_is_refused(resolved) -> None:
    resolver = _Resolver({"600519": resolved, "600036": "CN-XSHG-600036"})
    with pytest.raises(BasketReadRefusal) as exc:
        _read(resolver=resolver)
    assert exc.value.code is BasketRefusalCode.MALFORMED_IDENTITY
    assert "600519" in str(exc.value)


def test_u04_resolver_identity_error_is_refused_not_unresolved() -> None:
    """A resolver that RAISES is MALFORMED_IDENTITY (chained), never a quiet NEVER_INSPECTED."""

    class _Raising(_Resolver):
        def __call__(self, ticker, day):
            if ticker == "600519":
                raise IdentityError("ticker '600519' is not a lawful identity")
            return super().__call__(ticker, day)

    with pytest.raises(BasketReadRefusal) as exc:
        _read(resolver=_Raising())
    assert exc.value.code is BasketRefusalCode.MALFORMED_IDENTITY
    assert "600519" in str(exc.value)
    assert isinstance(exc.value.__cause__, IdentityError)


def test_u04_member_without_price_rows_is_missing_no_coverage() -> None:
    got = _read(price_read=_reconstruct_read(rows=(_row("CN-XSHG-600519"),)))
    entry = got.coverage.disposition_of("CN-XSHG-600036")
    assert entry.disposition is Disposition.MISSING
    assert entry.missing_reason is MissingReason.NO_COVERAGE


def test_u04_declared_fallback_source_is_context_not_served() -> None:
    rows = (_row("CN-XSHG-600519", source="vendor_deep"),
            _row("CN-XSHG-600036", source="vendor_deep"))
    got = _read(price_read=_reconstruct_read(rows=rows),
                fallback_sources=("vendor_deep",))
    for key in got.member_keys:
        entry = got.coverage.disposition_of(key)
        assert entry.disposition is Disposition.FALLBACK
        assert key in got.coverage.displayable
        assert key not in got.coverage.qualified


def test_u04_mixed_primary_and_fallback_rows_are_fallback() -> None:
    rows = (_row("CN-XSHG-600519", source="vendor_deep"),
            _row("CN-XSHG-600519"),
            _row("CN-XSHG-600036"))
    got = _read(price_read=_reconstruct_read(rows=rows),
                fallback_sources=("vendor_deep",))
    entry = got.coverage.disposition_of("CN-XSHG-600519")
    assert entry.disposition is Disposition.FALLBACK
    assert entry.disposition is not Disposition.REFUSED
    assert "CN-XSHG-600519" not in got.coverage.qualified
    assert {segment.source for segment in entry.segments} == {"vendor_deep"}
    assert "vendor_deep" in entry.detail and "primary" in entry.detail


@pytest.mark.parametrize("drop", ["listing_id", "source", "basis"])
def test_u04_price_row_without_listing_source_or_basis_is_refused(drop) -> None:
    row = _row()
    row.pop(drop)
    rows = (row, _row("CN-XSHG-600036"))
    with pytest.raises(BasketReadRefusal) as exc:
        _read(price_read=_reconstruct_read(rows=rows))
    assert exc.value.code is BasketRefusalCode.MALFORMED_PRICE_ROW


def test_u04_basis_drift_demotes_the_member_to_refused() -> None:
    rows = (_row("CN-XSHG-600519", basis="tradj"), _row("CN-XSHG-600036"))
    got = _read(price_read=_reconstruct_read(rows=rows))
    entry = got.coverage.disposition_of("CN-XSHG-600519")
    assert entry.disposition is Disposition.REFUSED
    assert entry.refusal is RefusalCode.BASIS_CHANGED


def test_u04_two_tickers_on_one_listing_refuse_duplicate_member() -> None:
    resolver = _Resolver({"600036": "CN-XSHG-600519", "600519": "CN-XSHG-600519"})
    with pytest.raises(ReadRefusal) as exc:
        _read(resolver=resolver)
    assert exc.value.code is RefusalCode.DUPLICATE_MEMBER


def test_u04_rows_outside_the_population_are_counted_not_refused() -> None:
    rows = (*ROWS, _row("CN-XSHG-688981"))
    got = _read(price_read=_reconstruct_read(rows=rows))
    assert got.result.evidence["basket"]["rows_outside_population"] == 1
    assert got.result.evidence["basket"]["identity"]["600036"] == "CN-XSHG-600036"


def _basket_read(**over) -> BasketRead:
    fields = dict(
        result=_reconstruct_read(), basket_id="BK1", suite="baskets_china_ths",
        membership_day=DAY, evidence_mode=EvidenceMode.PIT_SNAPSHOT,
        population_kind=PopulationKind.CURATED_CAPPED,
        tickers=TICKERS, member_keys=("CN-XSHG-600036", "CN-XSHG-600519"))
    fields.update(over)
    return BasketRead(**fields)


def test_u04_population_delta_reports_added_and_removed() -> None:
    a = _read()
    b = _read(cutoff="2026-01-06T10:00:00+00:00",
              membership=dict(asof="2026-01-05", snapshot_date="2026-01-05",
                              members=["600036"]))
    assert population_delta(a, b) == {
        "from_day": "2026-01-04", "to_day": "2026-01-05",
        "added": (), "removed": ("600519",)}


@pytest.mark.parametrize(
    "over,code",
    [
        (dict(basket_id="BK2"), BasketRefusalCode.BASKET_MISMATCH),
        (dict(result=_current_read(), evidence_mode=EvidenceMode.CURRENT_MEMBERSHIP),
         BasketRefusalCode.MODE_MISMATCH),
        (dict(population_kind=PopulationKind.VENDOR_UNIVERSE),
         BasketRefusalCode.POPULATION_KIND_MISMATCH),
        (dict(evidence_mode=EvidenceMode.CURRENT_MEMBERSHIP),
         BasketRefusalCode.EVIDENCE_MODE_MISMATCH),
    ])
def test_u04_population_delta_refuses_across_boundaries(over, code) -> None:
    a = _basket_read()
    with pytest.raises(BasketReadRefusal) as exc:
        population_delta(a, _basket_read(**over))
    assert exc.value.code is code


def test_u04_refusal_vocabulary_is_closed() -> None:
    assert len(BasketRefusalCode) == 21
    assert all(code.value == code.name for code in BasketRefusalCode)
    assert issubclass(BasketReadRefusal, ReadContractError)
    exc = BasketReadRefusal(BasketRefusalCode.UNKNOWN_SUITE, "declined")
    assert str(exc).startswith("UNKNOWN_SUITE")


def test_u04_the_price_read_is_never_mutated() -> None:
    price_read = _reconstruct_read()
    got = _read(price_read=price_read)
    assert got is not None
    assert price_read.coverage is None
    assert "basket" not in price_read.evidence


def test_u04_engine_vocabulary_is_pinned() -> None:
    pytest.importorskip("pandas")
    from engine import basket_membership_pit as pit
    import lib.dataos.basket_read as basket_read
    assert pit.SUITE_US == "baskets"
    assert pit.SUITE_CURATED == "baskets_china"
    assert pit.SUITE_THS == "baskets_china_ths"
    assert pit.SHAPE_MEMBERSHIP == "membership"
    assert pit.SHAPE_CONCEPT_DUMP == "ths_concept_dump"
    assert pit._BASIS_PIT == "pit_snapshot"
    assert pit._BASIS_CURRENT == "current_membership"
    assert pit._BASIS_UNKNOWN == "unknown_basket"
    assert pit._BASIS_UNREADABLE == "membership_unreadable"
    assert basket_read._BASIS_UNREADABLE == pit._BASIS_UNREADABLE
    assert set(basket_read._SUITE_TZ_MIC) == {
        pit.SUITE_US, pit.SUITE_CURATED, pit.SUITE_THS}


def test_u04_default_reader_is_members_asof(monkeypatch) -> None:
    pytest.importorskip("pandas")
    from engine import basket_membership_pit as pit
    calls = []

    def fake(basket_id, day_iso, *, suite):
        calls.append((basket_id, day_iso, suite))
        return _membership()

    monkeypatch.setattr(pit, "members_asof", fake)
    # No membership_reader injected: the module's default reader must be the
    # engine's own members_asof.
    request = ReadRequest(ReadMode.RECONSTRUCT, _contract(), cutoff=CUTOFF,
                          clock="ingested_at")
    read_basket(request, basket_id="BK1", suite="baskets_china_ths",
                price_read=_reconstruct_read(), resolve=_Resolver(),
                expected_population=PopulationKind.CURATED_CAPPED)
    assert calls == [("BK1", "2026-01-04", "baskets_china_ths")]


@pytest.mark.parametrize("mode", ["RECONSTRUCT", "CURRENT"])
def test_u04_unreadable_store_is_refused_through_the_default_reader(mode, tmp_path, monkeypatch) -> None:
    """Q02-F1: corrupt PIT bytes reach read_basket via the DEFAULT reader and are
    refused MEMBERSHIP_UNREADABLE in every mode — corruption is never measured as
    absence or as current membership."""
    pytest.importorskip("pandas")
    from engine import basket_membership_pit as pit
    from lib import config
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    suite = "baskets_china_ths"
    history = tmp_path / suite / "membership_history.parquet"
    history.parent.mkdir(parents=True, exist_ok=True)
    history.write_bytes(b"broken")
    assert pit.history_path(suite) == history  # binds the file the reader reads
    if mode == "RECONSTRUCT":
        request = ReadRequest(ReadMode.RECONSTRUCT, _contract(), cutoff=CUTOFF,
                              clock="ingested_at")
        price_read, session_day = _reconstruct_read(), None
    else:
        request = ReadRequest(ReadMode.CURRENT, _contract())
        price_read, session_day = _current_read(), DAY
    # No membership_reader injected: the module default (the real members_asof)
    # must be the one that answers, and its unreadable answer must refuse here.
    with pytest.raises(BasketReadRefusal) as exc:
        read_basket(request, basket_id="BK1", suite=suite,
                    price_read=price_read, resolve=_Resolver(),
                    expected_population=PopulationKind.CURATED_CAPPED,
                    session_day=session_day)
    assert exc.value.code is BasketRefusalCode.MEMBERSHIP_UNREADABLE


def test_u04_absent_store_keeps_the_flagged_current_fallback(tmp_path, monkeypatch) -> None:
    """Control (Q02-F1): an ABSENT store keeps its unchanged fallback — current
    membership applied backward, pit=False — which a RECONSTRUCT refuses as
    LOOKAHEAD_MEMBERSHIP, never as MEMBERSHIP_UNREADABLE."""
    pytest.importorskip("pandas")
    from lib import config
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    suite = "baskets_china_ths"
    assert not (tmp_path / suite / "membership_history.parquet").exists()
    membership = tmp_path / suite / "membership.json"
    membership.parent.mkdir(parents=True, exist_ok=True)
    membership.write_text(json.dumps({
        "version": 1, "seed_date": "2021-06-15", "curated": False,
        "baskets": {"BK1": {"name": "BK1", "name_zh": "BK1", "category": "theme",
                            "members": [{"ticker": "600036", "added": "2021-06-15",
                                         "removed": None, "name_zh": "zh-600036",
                                         "rationale": "u04"}]}},
    }), encoding="utf-8")
    request = ReadRequest(ReadMode.RECONSTRUCT, _contract(), cutoff=CUTOFF,
                          clock="ingested_at")
    with pytest.raises(BasketReadRefusal) as exc:
        read_basket(request, basket_id="BK1", suite=suite,
                    price_read=_reconstruct_read(), resolve=_Resolver(),
                    expected_population=PopulationKind.CURATED_CAPPED)
    assert exc.value.code is BasketRefusalCode.LOOKAHEAD_MEMBERSHIP
    assert exc.value.code is not BasketRefusalCode.MEMBERSHIP_UNREADABLE


@pytest.mark.parametrize("mode", ["RECONSTRUCT", "CURRENT"])
def test_u04_injected_unreadable_membership_is_refused_in_every_mode(mode) -> None:
    """An injected reader answering membership_unreadable (with NO members) is
    refused MEMBERSHIP_UNREADABLE in BOTH modes; members=[] discriminates the
    ordering — after the empty check this would say EMPTY_MEMBERSHIP instead."""
    with pytest.raises(BasketReadRefusal) as exc:
        _read(mode=mode, membership=dict(pit=False, basis="membership_unreadable",
                                         members=[], snapshot_date=None,
                                         source_shape=None))
    assert exc.value.code is BasketRefusalCode.MEMBERSHIP_UNREADABLE


def test_u04_import_is_stdlib_only() -> None:
    proc = subprocess.run(
        [sys.executable, "-c",
         "import sys, lib.dataos.basket_read; "
         "print('pandas' in sys.modules, "
         "any(m.startswith('engine') for m in sys.modules))"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    assert proc.stdout.strip() == "False False"


def test_u04_no_wall_clock_or_io_in_the_module() -> None:
    source = (REPO_ROOT / "lib" / "dataos" / "basket_read.py").read_text(
        encoding="utf-8")
    for token in ("datetime.now", "date.today", "time.time", "open(",
                  "os.environ", "getenv", "random", "print(", "logging"):
        assert token not in source, token

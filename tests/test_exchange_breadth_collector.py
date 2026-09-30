from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from collectors.exchange_breadth import (
    CollectionRefused,
    MassiveReferenceClient,
    _completed_session_from_store,
    collect_exchange_breadth,
)

SESSION = date(2026, 1, 9)
NOW_AFTER_CLOSE = datetime(2026, 1, 9, 23, 0, tzinfo=timezone.utc)


def _roster_row(
    ticker: str,
    *,
    exchange: str = "XNYS",
    ticker_type: str = "CS",
    active: bool = True,
    share_class_figi: str | None = None,
) -> dict:
    return {
        "ticker": ticker,
        "name": f"{ticker} Corp",
        "market": "stocks",
        "locale": "us",
        "primary_exchange": exchange,
        "type": ticker_type,
        "active": active,
        "currency_name": "usd",
        "share_class_figi": share_class_figi,
        "composite_figi": None,
    }


def _split_row(
    ticker: str,
    *,
    execution_date: str = "2025-08-15",
    split_from: float = 1.0,
    split_to: float = 2.0,
    adjustment_type: str = "forward_split",
    split_id: str | None = None,
) -> dict:
    return {
        "id": split_id or f"{ticker}-{execution_date}-{split_from}-{split_to}",
        "ticker": ticker,
        "execution_date": execution_date,
        "split_from": split_from,
        "split_to": split_to,
        "adjustment_type": adjustment_type,
    }


def _ok(
    rows: list[dict], *, next_url: str | None = None, request_id: str = "req"
) -> dict:
    payload = {
        "status": "OK",
        "request_id": request_id,
        "count": len(rows),
        "results": rows,
    }
    if next_url is not None:
        payload["next_url"] = next_url
    return payload


def _write_store(
    root: Path,
    *,
    latest: date = SESSION,
    files: int = 2,
    anchor_last: date | None = None,
) -> None:
    store = root / "massive_stock_day"
    store.mkdir(parents=True, exist_ok=True)
    for i in range(files):
        pd.DataFrame(
            {"close": [100.0 + i]},
            index=pd.DatetimeIndex([pd.Timestamp(latest)], name="date"),
        ).to_parquet(store / f"T{i}.parquet")
    manifest = {
        "store": "massive_stock_day",
        "latest_date": latest.isoformat(),
        "n_tickers": files,
        "anchor": {
            "ticker": "SPY",
            "last": (anchor_last or latest).isoformat(),
            "n_rows": 1,
        },
    }
    (store / "_manifest.json").write_text(json.dumps(manifest))


def _write_aliases(root: Path) -> None:
    reference = root / "reference"
    reference.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "vendor": "massive",
                "vendor_symbol": "AAA",
                "security_id": "SEC:US-XNYS-AAA",
                "valid_from": None,
                "valid_to": None,
            },
            {
                "vendor": "massive",
                "vendor_symbol": "BBB",
                "security_id": "SEC:US-XNYS-BBB",
                "valid_from": None,
                "valid_to": None,
            },
        ]
    ).to_parquet(reference / "vendor_aliases.parquet", index=False)


def _price_loader(ticker: str) -> pd.DataFrame:
    if ticker not in {"AAA", "BBB"}:
        return pd.DataFrame()
    return pd.DataFrame(
        {"close": [100.0 if ticker == "AAA" else 50.0]},
        index=pd.DatetimeIndex([pd.Timestamp(SESSION)], name="date"),
    )


def test_roster_request_has_exact_point_in_time_filters() -> None:
    calls: list[tuple[str, dict]] = []

    def request_json(url: str, params: dict) -> dict:
        calls.append((url, dict(params)))
        return _ok([_roster_row("AAA"), _roster_row("BBB")])

    client = MassiveReferenceClient(
        api_key="secret-key",
        base_url="https://api.example.test",
        request_json=request_json,
    )
    bundle = client.fetch_roster(SESSION, min_rows=2)

    assert len(bundle.rows) == 2
    assert calls == [
        (
            "https://api.example.test/v3/reference/tickers",
            {
                "market": "stocks",
                "exchange": "XNYS",
                "date": "2026-01-09",
                "active": "true",
                "limit": 1000,
                "sort": "ticker",
                "order": "asc",
                "apiKey": "secret-key",
            },
        )
    ]


def test_split_request_is_bounded_and_keeps_stock_dividend_type() -> None:
    calls: list[tuple[str, dict]] = []

    def request_json(url: str, params: dict) -> dict:
        calls.append((url, dict(params)))
        return _ok([_split_row("AAA", adjustment_type="stock_dividend")])

    client = MassiveReferenceClient(
        api_key="secret-key",
        base_url="https://api.example.test",
        request_json=request_json,
    )
    bundle = client.fetch_splits(date(2025, 1, 1), SESSION)

    assert bundle.rows[0]["adjustment_type"] == "stock_dividend"
    assert calls[0][0].endswith("/stocks/v1/splits")
    assert calls[0][1]["execution_date.gte"] == "2025-01-01"
    assert calls[0][1]["execution_date.lte"] == "2026-01-09"
    assert "adjustment_type" not in calls[0][1]
    assert calls[0][1]["limit"] == 1000


def test_pagination_propagates_key_and_receipt_never_contains_it() -> None:
    calls: list[tuple[str, dict]] = []
    pages = [
        _ok(
            [_roster_row("AAA")],
            next_url="https://api.example.test/v3/reference/tickers?cursor=abc",
            request_id="r1",
        ),
        _ok([_roster_row("BBB")], request_id="r2"),
    ]

    def request_json(url: str, params: dict) -> dict:
        calls.append((url, dict(params)))
        return pages.pop(0)

    client = MassiveReferenceClient(
        api_key="secret-key",
        base_url="https://api.example.test",
        request_json=request_json,
    )
    bundle = client.fetch_roster(SESSION, min_rows=2)

    assert calls[0][1]["apiKey"] == "secret-key"
    assert calls[1][1] == {"apiKey": "secret-key"}
    serialized = json.dumps(bundle.receipt)
    assert "secret-key" not in serialized
    assert bundle.receipt["pages"] == 2
    assert bundle.receipt["request_ids"] == ["r1", "r2"]


def test_request_error_redacts_api_key() -> None:
    def request_json(url: str, params: dict) -> dict:
        raise RuntimeError(f"GET {url}?apiKey={params['apiKey']}&cursor=abc failed")

    client = MassiveReferenceClient(
        api_key="top-secret",
        base_url="https://api.example.test",
        request_json=request_json,
    )
    with pytest.raises(CollectionRefused) as exc:
        client.fetch_roster(SESSION, min_rows=1)
    assert "top-secret" not in str(exc.value)
    assert "REDACTED" in str(exc.value)


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        ({"status": "ERROR", "results": [_roster_row("AAA")]}, "non-OK"),
        (_ok([]), "empty"),
        (_ok([_roster_row("AAA"), _roster_row("AAA")]), "duplicate"),
        (_ok([_roster_row("AAA", exchange="XASE")]), "wrong exchange"),
        (
            _ok(
                [_roster_row("AAA")],
                next_url=None,
            )
            | {"count": 1000},
            "truncated",
        ),
    ],
)
def test_roster_refuses_invalid_source_shapes(payload: dict, match: str) -> None:
    client = MassiveReferenceClient(
        api_key="k",
        base_url="https://api.example.test",
        request_json=lambda _url, _params: payload,
    )
    with pytest.raises(CollectionRefused, match=match):
        client.fetch_roster(SESSION, min_rows=1)


def test_roster_refuses_low_row_floor() -> None:
    client = MassiveReferenceClient(
        api_key="k",
        base_url="https://api.example.test",
        request_json=lambda _url, _params: _ok([_roster_row("AAA")]),
    )
    with pytest.raises(CollectionRefused, match="row floor"):
        client.fetch_roster(SESSION, min_rows=2)


@pytest.mark.parametrize(
    "row",
    [
        _split_row("AAA", split_from=0),
        _split_row("AAA", split_to=-1),
        _split_row("AAA", split_from=float("nan")),
    ],
)
def test_splits_refuse_invalid_ratios(row: dict) -> None:
    client = MassiveReferenceClient(
        api_key="k",
        base_url="https://api.example.test",
        request_json=lambda _url, _params: _ok([row]),
    )
    with pytest.raises(CollectionRefused, match="ratio"):
        client.fetch_splits(date(2025, 1, 1), SESSION)


def test_splits_refuse_duplicate_and_page_cap() -> None:
    duplicate = _split_row("AAA", split_id="same")
    client = MassiveReferenceClient(
        api_key="k",
        base_url="https://api.example.test",
        request_json=lambda _url, _params: _ok([duplicate, dict(duplicate)]),
    )
    with pytest.raises(CollectionRefused, match="duplicate"):
        client.fetch_splits(date(2025, 1, 1), SESSION)

    capped = MassiveReferenceClient(
        api_key="k",
        base_url="https://api.example.test",
        max_pages=1,
        request_json=lambda _url, _params: _ok(
            [_split_row("AAA")],
            next_url="https://api.example.test/stocks/v1/splits?cursor=more",
        ),
    )
    with pytest.raises(CollectionRefused, match="page cap"):
        capped.fetch_splits(date(2025, 1, 1), SESSION)


def test_completed_session_comes_from_manifest_and_calendar(tmp_path: Path) -> None:
    _write_store(tmp_path, latest=SESSION, files=2)
    assert (
        _completed_session_from_store(tmp_path, now=NOW_AFTER_CLOSE, min_store_files=2)
        == SESSION
    )

    stale_now = datetime(2026, 1, 12, 23, 0, tzinfo=timezone.utc)
    with pytest.raises(CollectionRefused, match="stale"):
        _completed_session_from_store(tmp_path, now=stale_now, min_store_files=2)


def test_partial_store_refuses_before_source_fetch(tmp_path: Path) -> None:
    _write_store(tmp_path, files=1)
    calls = 0

    def request_json(_url: str, _params: dict) -> dict:
        nonlocal calls
        calls += 1
        return _ok([_roster_row("AAA")])

    client = MassiveReferenceClient("k", request_json=request_json)
    with pytest.raises(CollectionRefused, match="partial"):
        collect_exchange_breadth(
            client=client,
            data_root=tmp_path,
            now=NOW_AFTER_CLOSE,
            min_store_files=2,
            min_roster_rows=1,
            min_operating_rows=1,
            min_identity_coverage=0.0,
            min_price_coverage=0.0,
            price_loader=_price_loader,
        )
    assert calls == 0


def test_source_failure_preserves_prior_accepted_files_byte_for_byte(
    tmp_path: Path,
) -> None:
    _write_store(tmp_path, files=2)
    _write_aliases(tmp_path)
    out = tmp_path / "exchange_breadth"
    out.mkdir()
    prior = {
        "universe_intervals.parquet": b"old-intervals",
        "source_splits.parquet": b"old-splits",
        "nyse_operating.parquet": b"old-operating",
        "nyse_all_issues.parquet": b"old-all",
        "_state.json": b'{"old": true}',
        "_receipt.json": b'{"old": true}',
    }
    for name, payload in prior.items():
        (out / name).write_bytes(payload)

    client = MassiveReferenceClient(
        "k",
        request_json=lambda _url, _params: (_ for _ in ()).throw(
            RuntimeError("upstream unavailable")
        ),
    )
    with pytest.raises(CollectionRefused):
        collect_exchange_breadth(
            client=client,
            data_root=tmp_path,
            now=NOW_AFTER_CLOSE,
            min_store_files=2,
            min_roster_rows=1,
            min_operating_rows=1,
            min_identity_coverage=0.0,
            min_price_coverage=0.0,
            price_loader=_price_loader,
        )

    assert {name: (out / name).read_bytes() for name in prior} == prior


def test_accepted_collection_writes_both_universes_and_receipt(tmp_path: Path) -> None:
    _write_store(tmp_path, files=2)
    _write_aliases(tmp_path)
    pages = [
        _ok(
            [
                _roster_row("AAA"),
                _roster_row("BBB", ticker_type="ADRC"),
                _roster_row("CCC"),
            ],
            request_id="roster-r1",
        ),
        _ok(
            [
                _split_row(
                    "AAA",
                    adjustment_type="stock_dividend",
                    execution_date="2026-01-09",
                )
            ],
            request_id="split-r1",
        ),
    ]

    def request_json(_url: str, _params: dict) -> dict:
        return pages.pop(0)

    client = MassiveReferenceClient(
        api_key="secret-key",
        base_url="https://api.example.test",
        request_json=request_json,
    )
    result = collect_exchange_breadth(
        client=client,
        data_root=tmp_path,
        now=NOW_AFTER_CLOSE,
        min_store_files=2,
        min_roster_rows=3,
        min_operating_rows=3,
        min_identity_coverage=0.60,
        min_price_coverage=0.60,
        price_loader=_price_loader,
        split_lookback_days=500,
    )

    assert set(result.frames) == {"nyse_operating", "nyse_all_issues"}
    assert not result.frames["nyse_operating"].empty
    assert not result.frames["nyse_all_issues"].empty

    out = tmp_path / "exchange_breadth"
    expected = {
        "universe_intervals.parquet",
        "source_splits.parquet",
        "nyse_operating.parquet",
        "nyse_all_issues.parquet",
        "_state.json",
        "_receipt.json",
    }
    assert expected.issubset({p.name for p in out.iterdir()})

    intervals = pd.read_parquet(out / "universe_intervals.parquet")
    assert set(intervals["universe_key"]) == {"nyse_operating", "nyse_all_issues"}
    assert set(intervals["entity_key"]) == {
        "SEC:US-XNYS-AAA",
        "SEC:US-XNYS-BBB",
    }

    splits = pd.read_parquet(out / "source_splits.parquet")
    assert splits.loc[0, "adjustment_type"] == "stock_dividend"

    receipt = json.loads((out / "_receipt.json").read_text())
    assert receipt["accepted_session"] == "2026-01-09"
    assert receipt["source_rules_version"] == "exchange_breadth.xnys.v1"
    assert receipt["price_basis"] == "massive_stock_day.raw_daily_aggregate+pit_splits"
    assert receipt["universes"]["nyse_operating"]["listed_n"] == 3
    assert receipt["universes"]["nyse_operating"]["resolved_identity_n"] == 2
    assert receipt["unresolved_identity_examples"] == ["CCC"]
    assert receipt["roster"]["request_ids"] == ["roster-r1"]
    assert receipt["splits"]["request_ids"] == ["split-r1"]
    assert "secret-key" not in json.dumps(receipt)
    assert receipt["source_clock"]

    state = json.loads((out / "_state.json").read_text())
    assert state["last_observed_session"] == "2026-01-09"
    assert state["accepted_sessions"] == ["2026-01-09"]


def test_registry_order_is_after_massive_stock_day() -> None:
    root = Path(__file__).resolve().parents[1]
    collect_text = (root / "scripts" / "collect.py").read_text()
    assert collect_text.index('("massive_stock_day"') < collect_text.index(
        '("exchange_breadth"'
    )

    registry = (root / "config" / "dataset_registry.yml").read_text()
    assert "breadth.exchange.xnys.operating" in registry
    assert "breadth.exchange.xnys.all_issues" in registry


def test_managed_persistence_adapter_is_not_upserted_twice(monkeypatch) -> None:
    from collectors import base
    from collectors.base import Adapter, run_adapter

    class ManagedAdapter(Adapter):
        name = "managed_test"
        group = "managed_test"
        manages_persistence = True

        def fetch(self, full_history: bool = False) -> dict[str, pd.DataFrame]:
            return {
                "accepted": pd.DataFrame(
                    {"value": [1.0]},
                    index=pd.DatetimeIndex([pd.Timestamp("2026-01-09")], name="date"),
                )
            }

    monkeypatch.setattr(base, "_breaker_state", lambda: {})
    monkeypatch.setattr(base, "_probe_state", lambda: {})
    monkeypatch.setattr(base, "detect_stale_series", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(base, "_emit_dark_columns", lambda _entries: [])

    def duplicate_write(*_args, **_kwargs):
        raise AssertionError(
            "generic store.upsert must not rewrite managed persistence"
        )

    monkeypatch.setattr(base.store, "upsert", duplicate_write)
    result = run_adapter(ManagedAdapter(), stale_after_days=1000)

    assert result.status == "ok"
    assert result.rows == 1
    assert result.last_date == "2026-01-09"


def test_splits_accept_a_legitimate_quiet_window() -> None:
    client = MassiveReferenceClient(
        api_key="k",
        base_url="https://api.example.test",
        request_json=lambda _url, _params: {
            "status": "OK",
            "request_id": "quiet",
            "count": 0,
            "results": [],
        },
    )

    bundle = client.fetch_splits(date(2025, 1, 1), SESSION)

    assert bundle.rows == ()
    assert bundle.receipt["row_count"] == 0
    assert bundle.receipt["request_ids"] == ["quiet"]


def test_roster_preserves_case_distinct_massive_ticker_identities() -> None:
    client = MassiveReferenceClient(
        api_key="k",
        base_url="https://api.example.test",
        request_json=lambda _url, _params: _ok(
            [
                _roster_row("TPC", ticker_type="CS"),
                _roster_row("TpC", ticker_type="PFD"),
            ]
        ),
    )

    bundle = client.fetch_roster(SESSION, min_rows=2)

    assert [row["ticker"] for row in bundle.rows] == ["TPC", "TpC"]


def test_split_preserves_case_exact_massive_ticker_identity() -> None:
    client = MassiveReferenceClient(
        api_key="k",
        base_url="https://api.example.test",
        request_json=lambda _url, _params: _ok([_split_row("TpC")]),
    )

    bundle = client.fetch_splits(date(2025, 1, 1), SESSION)

    assert bundle.rows[0]["ticker"] == "TpC"


def test_partial_all_issues_comparator_does_not_block_primary_generation(
    tmp_path: Path,
) -> None:
    _write_store(tmp_path, files=2)
    _write_aliases(tmp_path)
    pages = [
        _ok(
            [
                _roster_row("AAA", ticker_type="CS"),
                _roster_row("BBB", ticker_type="ADRC"),
                _roster_row("PREF", ticker_type="PFD"),
                _roster_row("FUND", ticker_type="FUND"),
            ],
            request_id="roster-partial-comparator",
        ),
        _ok([], request_id="splits-quiet"),
    ]
    client = MassiveReferenceClient(
        api_key="secret-key",
        base_url="https://api.example.test",
        request_json=lambda _url, _params: pages.pop(0),
    )

    result = collect_exchange_breadth(
        client=client,
        data_root=tmp_path,
        now=NOW_AFTER_CLOSE,
        min_store_files=2,
        min_roster_rows=4,
        min_operating_rows=2,
        min_identity_coverage=0.90,
        min_price_coverage=0.90,
        price_loader=_price_loader,
    )

    operating = result.receipt["universes"]["nyse_operating"]
    comparator = result.receipt["universes"]["nyse_all_issues"]
    assert operating["status"] == "accepted"
    assert operating["required"] is True
    assert operating["usable"] is True
    assert operating["listed_n"] == 2
    assert operating["resolved_identity_n"] == 2
    assert operating["priced_n"] == 2

    assert comparator["status"] == "partial"
    assert comparator["required"] is False
    assert comparator["usable"] is False
    assert comparator["confirmation_eligible"] is False
    assert comparator["listed_n"] == 4
    assert comparator["resolved_identity_n"] == 2
    assert comparator["priced_n"] == 2
    assert comparator["coverage_reasons"] == [
        "identity_coverage_below_floor",
        "price_coverage_below_floor",
    ]
    latest = result.frames["nyse_all_issues"].loc[pd.Timestamp(SESSION)]
    assert int(latest["listed_n"]) == 4
    assert int(latest["priced_n"]) == 2


def test_primary_identity_coverage_still_fails_closed(tmp_path: Path) -> None:
    _write_store(tmp_path, files=2)
    _write_aliases(tmp_path)
    pages = [
        _ok(
            [
                _roster_row("AAA", ticker_type="CS"),
                _roster_row("MISSING", ticker_type="CS"),
            ],
            request_id="roster-primary-low-identity",
        ),
        _ok([], request_id="splits-quiet"),
    ]
    client = MassiveReferenceClient(
        api_key="secret-key",
        base_url="https://api.example.test",
        request_json=lambda _url, _params: pages.pop(0),
    )

    with pytest.raises(CollectionRefused, match="nyse_operating identity coverage"):
        collect_exchange_breadth(
            client=client,
            data_root=tmp_path,
            now=NOW_AFTER_CLOSE,
            min_store_files=2,
            min_roster_rows=2,
            min_operating_rows=2,
            min_identity_coverage=0.90,
            min_price_coverage=0.90,
            price_loader=_price_loader,
        )

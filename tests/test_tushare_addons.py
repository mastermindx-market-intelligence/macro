from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import pyarrow.parquet as pq
import pytest

from collectors import tushare_addons as addons
from scripts import collect_tushare_addons as cli

ROOT = Path(__file__).resolve().parents[1]
SHANGHAI = ZoneInfo("Asia/Shanghai")
HISTORICAL_NOW = datetime(2026, 8, 9, 12, tzinfo=timezone.utc)
# Each entry states something the data itself cannot support, regardless of who
# ordered the collection.
EPISTEMIC_NONCLAIMS = [
    "context_only_not_signal_authority",
    "no_fillability_or_execution_claim",
    "no_complete_historical_backfill_claim",
    "post_close_rows_are_unclassified_not_a_completeness_claim",
    "no_level2_order_book_or_queue_position",
]
ACCESS_NONCLAIMS = [
    "not_proof_of_future_access",
    "not_a_completeness_claim_for_the_session",
]


@pytest.fixture(autouse=True)
def configured_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """A configured TUSHARE_TOKEN is the only execution prerequisite."""
    monkeypatch.setenv("TUSHARE_TOKEN", "synthetic-test-token")


def minute_frame(*, high: float = 10.2, trade_date: str = "2026-08-07") -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ts_code": "600519.SH",
                "trade_time": f"{trade_date} 09:31:00",
                "open": 10.0,
                "close": 10.1,
                "high": high,
                "low": 9.9,
                "vol": 1_000,
                "amount": 10_050,
            },
            {
                "ts_code": "600519.SH",
                "trade_time": f"{trade_date} 09:32:00",
                "open": 10.1,
                "close": 10.15,
                "high": 10.2,
                "low": 10.0,
                "vol": 800,
                "amount": 8_100,
            },
        ]
    )


def minute_clock_frame(clock: str) -> pd.DataFrame:
    frame = minute_frame().iloc[[0]].copy()
    frame.loc[:, "trade_time"] = f"2026-08-07 {clock}"
    return frame


def premarket_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "trade_date": "20260807",
                "ts_code": "000001.SZ",
                "total_share": 19_405_918.20,
                "float_share": 19_405_755.61,
                "pre_close": 10.0,
                "up_limit": 11.0,
                "down_limit": 9.0,
            }
        ]
    )


def auction_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ts_code": "000001.SZ",
                "trade_date": "20260810",
                "vol": 10_000,
                "price": 10.1,
                "amount": 101_000,
                "pre_close": 10.0,
                "turnover_rate": 0.02,
                "volume_ratio": 1.2,
                "float_share": 19_405_755.61,
            }
        ]
    )


def auction_oc_frame(*, trade_date: str = "20260807") -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ts_code": "000001.SZ",
                "trade_date": trade_date,
                "close": 10.1,
                "open": 10.0,
                "high": 10.15,
                "low": 9.95,
                "vol": 10_000,
                "amount": 100_500,
                "vwap": 10.05,
            }
        ]
    )


class FakeQuery:
    def __init__(
        self,
        endpoint: str,
        frame: pd.DataFrame,
        *,
        open_by_exchange: dict[str, int] | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.frame = frame
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.open_by_exchange = open_by_exchange or {"SSE": 1, "SZSE": 1}

    def __call__(self, api_name: str, **kwargs: object) -> pd.DataFrame | None:
        self.calls.append((api_name, dict(kwargs)))
        if api_name == "trade_cal":
            exchange = str(kwargs["exchange"])
            requested = str(kwargs["start_date"])
            prior = pd.Timestamp(requested) - pd.Timedelta(days=1)
            return pd.DataFrame(
                [
                    {
                        "exchange": exchange,
                        "cal_date": requested,
                        "is_open": self.open_by_exchange[exchange],
                        "pretrade_date": prior.strftime("%Y%m%d"),
                    }
                ]
            )
        assert api_name == self.endpoint
        return self.frame.copy()


class SequenceClock:
    def __init__(self, *observations: datetime) -> None:
        self.observations = iter(observations)

    def __call__(self) -> datetime:
        return next(self.observations)


def minute_request() -> addons.PilotRequest:
    return addons.PilotRequest(
        endpoint="stk_mins",
        trade_date="2026-08-07",
        ticker="600519.SH",
        frequency="1min",
    )


def test_plan_is_no_network_no_write_and_names_the_operative_authority(
    tmp_path: Path,
) -> None:
    output = tmp_path / "store"
    plan = addons.pilot_plan(minute_request(), output_root=output)
    assert plan["status"] == "planned_no_network_no_write"
    assert plan["maximum_vendor_calls"] == 3
    assert plan["range_or_bulk_mode"] is False
    assert plan["request"]["ticker"] == "600519.SS"
    assert plan["collection_provenance"] == {
        "basis": "operator_ordered_wiring",
        "reference": "research/TUSHARE_WIRING_TAKEOVER_2026-08-09.md",
    }
    assert plan["execute_requirements"]["tushare_token_configured"] is True
    assert plan["execute_requirements"]["technical_fences"] == [
        "two_exchange_trade_cal_session_agreement",
        "per_endpoint_collection_clock",
        "documented_row_cap",
        "exact_session_and_ticker_containment",
        "schema_and_domain_validation",
        "keep_first_immutability",
    ]
    assert not output.exists()


def test_no_endpoint_is_blocked_unconfirmed_after_the_auction_oc_admission(
    tmp_path: Path,
) -> None:
    """The o/c hold is released; the receipt key stays so readers see the state."""
    assert dict(addons.BLOCKED_UNCONFIRMED_ENDPOINTS) == {}
    output = tmp_path / "store"
    for endpoint in ("stk_auction_o", "stk_auction_c"):
        plan = addons.pilot_plan(
            addons.PilotRequest(
                endpoint=endpoint, trade_date="2026-08-07", ticker="000001.SZ"
            ),
            output_root=output,
        )
        assert plan["blocked_unconfirmed_endpoints"] == {}
        assert plan["declared_access_context"] == (
            "operator_attested_2026-08-09_takeover_doc"
        )
    assert not output.exists()


def test_admitted_auction_oc_contracts_pin_their_official_documents() -> None:
    documents = {"stk_auction_o": 353, "stk_auction_c": 354}
    for endpoint, document_id in documents.items():
        contract = addons.ENDPOINTS[endpoint]
        assert contract.document_id == document_id
        assert contract.document_url.endswith(f"doc_id={document_id}")
        assert contract.contract_source == "official_doc_page"
        # Docs 353/354 publish this exact output field list, in this order.
        assert contract.vendor_fields == (
            "ts_code",
            "trade_date",
            "close",
            "open",
            "high",
            "low",
            "vol",
            "amount",
            "vwap",
        )
        assert contract.max_rows == 10_000
        units = {field.name: field.unit for field in contract.output_schema}
        # Neither doc states a unit for 成交量/成交额, so the schema must disclose
        # the gap rather than assert shares/CNY the minute contract can assert.
        assert "no unit" in str(units["volume"])
        assert "no unit" in str(units["amount"])
        assert units["close"] == "CNY/share"


def test_default_output_root_is_gitignored() -> None:
    expected = ROOT / "data/tushare_addons"
    assert Path(addons.DEFAULT_OUTPUT_ROOT).resolve() == expected.resolve()
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "data/tushare_addons/probe/part.parquet"],
        cwd=ROOT,
        check=False,
    )
    assert ignored.returncode == 0


def test_minute_pilot_writes_provenance_receipt_without_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = "distinctive-secret-token-never-persist"
    monkeypatch.setenv("TUSHARE_TOKEN", secret)
    query = FakeQuery("stk_mins", minute_frame())

    result = addons.collect_pilot(
        minute_request(), output_root=tmp_path, query_fn=query, now=HISTORICAL_NOW
    )

    destination = Path(result.partition_path)
    assert result.status == "written"
    assert destination.relative_to(tmp_path).as_posix() == (
        "stk_mins/by_frequency=1min/by_trade_date=2026-08-07/by_scope=ticker-600519.SS"
    )
    assert {path.name for path in destination.iterdir()} == {
        "part.parquet",
        "receipt.json",
    }
    assert [call[0] for call in query.calls] == ["trade_cal", "trade_cal", "stk_mins"]
    endpoint_params = query.calls[-1][1]
    assert endpoint_params["ts_code"] == "600519.SH"
    assert endpoint_params["freq"] == "1min"
    assert "token" not in endpoint_params

    receipt_bytes = (destination / "receipt.json").read_bytes()
    assert secret.encode() not in receipt_bytes
    receipt = json.loads(receipt_bytes)
    assert receipt["authority"] == "context_display_only"
    access = receipt["access_observation_receipt"]
    assert access["observation"] == "access_observed_at_request_time"
    assert (
        access["observation_basis"] == "valid_nonempty_rows_returned_for_this_request"
    )
    assert access["nonclaims"] == ACCESS_NONCLAIMS
    assert receipt["collection_provenance"] == {
        "basis": "operator_ordered_wiring",
        "reference": "research/TUSHARE_WIRING_TAKEOVER_2026-08-09.md",
    }
    assert receipt["nonclaims"] == EPISTEMIC_NONCLAIMS
    assert receipt["request"]["maximum_vendor_calls"] == 3
    assert receipt["request"]["range_or_bulk_mode"] is False
    assert receipt["request"]["vendor_request_without_token"]["transport"] == "HTTPS"
    assert "token" not in receipt["request"]["vendor_request_without_token"]
    assert (
        "tushare_daily_and_stk_limit"
        in receipt["join_basis_contract"]["required_nominal_history"]
    )
    assert (
        "yahoo_split_adjusted"
        in receipt["join_basis_contract"]["forbidden_nominal_history"]
    )
    assert receipt["exact_session_receipt"]["required_exchanges"] == ["SSE", "SZSE"]
    assert receipt["request_clock"]["observation_point"] == (
        "after_trade_cal_immediately_before_addon_endpoint_request"
    )
    assert (
        access["observed_at_asia_shanghai"]
        == receipt["request_clock"]["observed_at_asia_shanghai"]
    )
    assert receipt["runtime_receipt"]["collector_source_sha256"]
    assert receipt["data_receipt"]["row_count"] == 2
    assert (
        addons.canonical_hash(
            {key: value for key, value in receipt.items() if key != "receipt_sha256"}
        )
        == receipt["receipt_sha256"]
    )

    table = pq.read_table(destination / "part.parquet")
    assert table.schema.metadata[b"endpoint"] == b"stk_mins"
    assert table.column("ticker").to_pylist() == ["600519.SS", "600519.SS"]
    assert table.column("session_segment").to_pylist() == [
        "regular_trading_window",
        "regular_trading_window",
    ]


def test_identical_rerun_is_noop_and_revision_is_keep_first_contradiction(
    tmp_path: Path,
) -> None:
    first_query = FakeQuery("stk_mins", minute_frame())
    first = addons.collect_pilot(
        minute_request(), output_root=tmp_path, query_fn=first_query, now=HISTORICAL_NOW
    )
    destination = Path(first.partition_path)
    before = {
        path.name: path.read_bytes() for path in destination.iterdir() if path.is_file()
    }

    second = addons.collect_pilot(
        minute_request(),
        output_root=tmp_path,
        query_fn=FakeQuery("stk_mins", minute_frame()),
        now=HISTORICAL_NOW,
    )
    after = {
        path.name: path.read_bytes() for path in destination.iterdir() if path.is_file()
    }
    assert second.status == "unchanged"
    assert before == after

    with pytest.raises(addons.CollectorIntegrityError, match="keep-first"):
        addons.collect_pilot(
            minute_request(),
            output_root=tmp_path,
            query_fn=FakeQuery("stk_mins", minute_frame(high=10.3)),
            now=HISTORICAL_NOW,
        )
    assert before == {
        path.name: path.read_bytes() for path in destination.iterdir() if path.is_file()
    }


def test_rehashed_authority_tamper_is_still_rejected(tmp_path: Path) -> None:
    result = addons.collect_pilot(
        minute_request(),
        output_root=tmp_path,
        query_fn=FakeQuery("stk_mins", minute_frame()),
        now=HISTORICAL_NOW,
    )
    receipt_path = Path(result.partition_path) / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["authority"] = "signal_authority"
    receipt.pop("receipt_sha256")
    receipt["receipt_sha256"] = addons.canonical_hash(receipt)
    receipt_path.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")

    with pytest.raises(addons.CollectorIntegrityError, match="authority"):
        addons.collect_pilot(
            minute_request(),
            output_root=tmp_path,
            query_fn=FakeQuery("stk_mins", minute_frame()),
            now=HISTORICAL_NOW,
        )


def test_execution_requires_a_configured_token_and_makes_no_call_without_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Token presence is the only execution prerequisite -- and it fails closed."""
    monkeypatch.delenv("TUSHARE_TOKEN", raising=False)

    with pytest.raises(addons.CollectionHeld, match="TUSHARE_TOKEN_absent"):
        addons.collect_pilot(minute_request(), output_root=tmp_path, now=HISTORICAL_NOW)

    assert not tmp_path.exists() or list(tmp_path.iterdir()) == []


def test_no_authorization_env_var_gates_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No env var may gate this collector: only the technical fences bind.

    The pilot foundation once carried a separate authorization gate. It was
    removed by operator ruling (2026-08-09), so a run with a configured token and
    a hostile environment must still collect normally.
    """
    for stale in (
        "TUSHARE_VENDOR_LICENSE_AUTHORITY",
        "TUSHARE_VENDOR_LICENSE_AUTHORITY_SHA256",
    ):
        monkeypatch.setenv(stale, "definitely-not-a-valid-value")

    result = addons.collect_pilot(
        minute_request(),
        output_root=tmp_path,
        query_fn=FakeQuery("stk_mins", minute_frame()),
        now=HISTORICAL_NOW,
    )

    assert result.status == "written"
    source = (ROOT / "collectors/tushare_addons.py").read_text(encoding="utf-8")
    assert "TUSHARE_VENDOR_LICENSE_AUTHORITY" not in source
    assert "allowlist" not in source.lower()


def test_receipt_records_plain_provenance_and_epistemic_nonclaims_only(
    tmp_path: Path,
) -> None:
    result = addons.collect_pilot(
        minute_request(),
        output_root=tmp_path,
        query_fn=FakeQuery("stk_mins", minute_frame()),
        now=HISTORICAL_NOW,
    )
    receipt = json.loads(
        (Path(result.partition_path) / "receipt.json").read_text(encoding="utf-8")
    )

    assert receipt["collection_provenance"] == {
        "basis": "operator_ordered_wiring",
        "reference": "research/TUSHARE_WIRING_TAKEOVER_2026-08-09.md",
    }
    assert receipt["nonclaims"] == EPISTEMIC_NONCLAIMS
    access = receipt["access_observation_receipt"]
    assert access["observation"] == "access_observed_at_request_time"
    assert access["nonclaims"] == ACCESS_NONCLAIMS
    # No licensing conclusion is asserted in either direction.
    blob = json.dumps(receipt, ensure_ascii=False).lower()
    assert "license" not in blob
    assert "attestation" not in blob


def test_altered_provenance_is_a_keep_first_contradiction(tmp_path: Path) -> None:
    result = addons.collect_pilot(
        minute_request(),
        output_root=tmp_path,
        query_fn=FakeQuery("stk_mins", minute_frame()),
        now=HISTORICAL_NOW,
    )
    receipt_path = Path(result.partition_path) / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["collection_provenance"] = {"basis": "self_authorized", "reference": "x"}
    receipt.pop("receipt_sha256")
    receipt["receipt_sha256"] = addons.canonical_hash(receipt)
    receipt_path.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")

    with pytest.raises(addons.CollectorIntegrityError, match="provenance"):
        addons.collect_pilot(
            minute_request(),
            output_root=tmp_path,
            query_fn=FakeQuery("stk_mins", minute_frame()),
            now=HISTORICAL_NOW,
        )


@pytest.mark.parametrize(
    ("endpoint", "frequency"),
    [
        ("stk_auction_o", "opening_call_auction"),
        ("stk_auction_c", "closing_call_auction"),
    ],
)
def test_auction_oc_pilots_write_partitions_and_preserve_a_no_trade_auction(
    tmp_path: Path, endpoint: str, frequency: str
) -> None:
    query = FakeQuery(endpoint, auction_oc_frame())
    result = addons.collect_pilot(
        addons.PilotRequest(
            endpoint=endpoint, trade_date="2026-08-07", ticker="000001.SZ"
        ),
        output_root=tmp_path / endpoint,
        query_fn=query,
        now=HISTORICAL_NOW,
    )

    assert result.status == "written"
    assert f"by_frequency={frequency}" in result.partition_path
    assert [call[0] for call in query.calls] == ["trade_cal", "trade_cal", endpoint]
    endpoint_params = query.calls[-1][1]
    assert endpoint_params["trade_date"] == "20260807"
    assert endpoint_params["ts_code"] == "000001.SZ"
    # ts_type is a stk_auction (doc 369) parameter and must not leak to o/c.
    assert "ts_type" not in endpoint_params

    table = pq.read_table(Path(result.partition_path) / "part.parquet")
    assert table.schema.metadata[b"endpoint"] == endpoint.encode()
    assert table.column("vwap").to_pylist() == [10.05]
    assert table.column("volume").to_pylist() == [10_000.0]

    # A session that draws no matched order is preserved as null prices, never
    # fabricated and never rejected as an integrity failure.
    empty = auction_oc_frame()
    for column in ("open", "high", "low", "close", "vwap"):
        empty.loc[:, column] = float("nan")
    empty.loc[:, "vol"] = 0
    empty.loc[:, "amount"] = 0
    quiet = addons.collect_pilot(
        addons.PilotRequest(
            endpoint=endpoint, trade_date="2026-08-07", ticker="000001.SZ"
        ),
        output_root=tmp_path / f"{endpoint}-quiet",
        query_fn=FakeQuery(endpoint, empty),
        now=HISTORICAL_NOW,
    )
    quiet_table = pq.read_table(Path(quiet.partition_path) / "part.parquet")
    assert quiet_table.column("close").to_pylist() == [None]
    assert quiet_table.column("volume").to_pylist() == [0.0]


@pytest.mark.parametrize("endpoint", ["stk_auction_o", "stk_auction_c"])
def test_auction_oc_rejects_incoherent_ohlc_without_writing(
    tmp_path: Path, endpoint: str
) -> None:
    frame = auction_oc_frame()
    frame.loc[:, "low"] = 99.0
    query = FakeQuery(endpoint, frame)

    with pytest.raises(addons.CollectorIntegrityError, match="OHLC"):
        addons.collect_pilot(
            addons.PilotRequest(
                endpoint=endpoint, trade_date="2026-08-07", ticker="000001.SZ"
            ),
            output_root=tmp_path,
            query_fn=query,
            now=HISTORICAL_NOW,
        )
    assert not tmp_path.exists() or list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("endpoint", ["stk_auction_o", "stk_auction_c"])
def test_auction_oc_has_no_hold_on_history_but_holds_an_unpublished_session(
    tmp_path: Path, endpoint: str
) -> None:
    """Docs 353/354 say 每天盘后更新, so only the CURRENT session is held."""
    request = addons.PilotRequest(
        endpoint=endpoint, trade_date="2026-08-10", ticker="000001.SZ"
    )
    query = FakeQuery(endpoint, auction_oc_frame(trade_date="20260810"))

    with pytest.raises(addons.CollectionHeld, match="not_yet_published"):
        addons.collect_pilot(
            request,
            output_root=tmp_path,
            query_fn=query,
            now=datetime(2026, 8, 10, 16, 29, tzinfo=SHANGHAI),
        )
    assert query.calls == []

    published = addons.collect_pilot(
        request,
        output_root=tmp_path,
        query_fn=FakeQuery(endpoint, auction_oc_frame(trade_date="20260810")),
        now=datetime(2026, 8, 10, 16, 30, tzinfo=SHANGHAI),
    )
    assert published.status == "written"

    # A deep-history session is admitted with no clock objection at all.
    historical = addons.collect_pilot(
        addons.PilotRequest(
            endpoint=endpoint, trade_date="2023-03-01", ticker="000001.SZ"
        ),
        output_root=tmp_path,
        query_fn=FakeQuery(endpoint, auction_oc_frame(trade_date="20230301")),
        now=datetime(2026, 8, 10, 0, 1, tzinfo=SHANGHAI),
    )
    assert "by_trade_date=2023-03-01" in historical.partition_path


def test_bse_pilots_fail_before_vendor_call_or_partition(tmp_path: Path) -> None:
    query = FakeQuery("stk_mins", minute_frame())
    request = addons.PilotRequest(
        endpoint="stk_mins",
        trade_date="2026-08-07",
        ticker="430047.BJ",
        frequency="1min",
    )

    with pytest.raises(addons.CollectionHeld, match="BSE_pilots_blocked"):
        addons.collect_pilot(
            request, output_root=tmp_path, query_fn=query, now=HISTORICAL_NOW
        )

    assert query.calls == []
    assert not tmp_path.exists() or list(tmp_path.iterdir()) == []


def test_vendor_response_bse_row_fails_without_partition(tmp_path: Path) -> None:
    frame = premarket_frame()
    frame.loc[:, "ts_code"] = "430047.BJ"
    query = FakeQuery("stk_premarket", frame)

    with pytest.raises(addons.CollectionHeld, match="BSE_rows_blocked"):
        addons.collect_pilot(
            addons.PilotRequest(
                endpoint="stk_premarket",
                trade_date="2026-08-07",
                ticker="000001.SZ",
            ),
            output_root=tmp_path,
            query_fn=query,
            now=HISTORICAL_NOW,
        )

    assert [call[0] for call in query.calls] == [
        "trade_cal",
        "trade_cal",
        "stk_premarket",
    ]
    assert not tmp_path.exists() or list(tmp_path.iterdir()) == []


def test_calendar_and_exact_session_fail_before_partition_mutation(
    tmp_path: Path,
) -> None:
    closed = FakeQuery(
        "stk_mins",
        minute_frame(),
        open_by_exchange={"SSE": 0, "SZSE": 0},
    )
    with pytest.raises(addons.CollectionHeld, match="not_an_open"):
        addons.collect_pilot(
            minute_request(), output_root=tmp_path, query_fn=closed, now=HISTORICAL_NOW
        )
    assert [call[0] for call in closed.calls] == ["trade_cal", "trade_cal"]
    assert list(tmp_path.iterdir()) == []

    wrong_day = FakeQuery("stk_mins", minute_frame(trade_date="2026-08-06"))
    with pytest.raises(addons.CollectorIntegrityError, match="exact session"):
        addons.collect_pilot(
            minute_request(),
            output_root=tmp_path,
            query_fn=wrong_day,
            now=HISTORICAL_NOW,
        )
    assert len(wrong_day.calls) == 3
    assert list(tmp_path.iterdir()) == []


def test_clock_guards_make_no_vendor_call_or_partition(tmp_path: Path) -> None:
    auction_query = FakeQuery("stk_auction", auction_frame())
    with pytest.raises(addons.CollectionHeld, match="outside_documented"):
        addons.collect_pilot(
            addons.PilotRequest(
                endpoint="stk_auction", trade_date="2026-08-10", ticker="000001.SZ"
            ),
            output_root=tmp_path,
            query_fn=auction_query,
            now=datetime(2026, 8, 10, 9, 31, tzinfo=SHANGHAI),
        )
    assert auction_query.calls == []

    minute_query = FakeQuery("stk_mins", minute_frame())
    with pytest.raises(addons.CollectionHeld, match="not_finalized"):
        addons.collect_pilot(
            addons.PilotRequest(
                endpoint="stk_mins",
                trade_date="2026-08-10",
                ticker="600519.SS",
                frequency="1min",
            ),
            output_root=tmp_path,
            query_fn=minute_query,
            now=datetime(2026, 8, 10, 20, 59, tzinfo=SHANGHAI),
        )
    assert minute_query.calls == []
    assert list(tmp_path.iterdir()) == []


def test_auction_rechecks_clock_after_calendars_and_blocks_0930_crossing(
    tmp_path: Path,
) -> None:
    query = FakeQuery("stk_auction", auction_frame())
    clock = SequenceClock(
        datetime(2026, 8, 10, 9, 29, 59, tzinfo=SHANGHAI),
        datetime(2026, 8, 10, 9, 30, 0, tzinfo=SHANGHAI),
    )

    with pytest.raises(addons.CollectionHeld, match="outside_documented"):
        addons.collect_pilot(
            addons.PilotRequest(
                endpoint="stk_auction", trade_date="2026-08-10", ticker="000001.SZ"
            ),
            output_root=tmp_path,
            query_fn=query,
            clock_fn=clock,
        )

    assert [call[0] for call in query.calls] == ["trade_cal", "trade_cal"]
    assert not tmp_path.exists() or list(tmp_path.iterdir()) == []


def test_auction_receipt_binds_final_pre_request_clock(tmp_path: Path) -> None:
    query = FakeQuery("stk_auction", auction_frame())
    final_clock = datetime(2026, 8, 10, 9, 27, 8, tzinfo=SHANGHAI)
    result = addons.collect_pilot(
        addons.PilotRequest(
            endpoint="stk_auction", trade_date="2026-08-10", ticker="000001.SZ"
        ),
        output_root=tmp_path,
        query_fn=query,
        clock_fn=SequenceClock(
            datetime(2026, 8, 10, 9, 27, 0, tzinfo=SHANGHAI),
            final_clock,
        ),
    )
    receipt = json.loads(
        (Path(result.partition_path) / "receipt.json").read_text(encoding="utf-8")
    )

    assert (
        receipt["request_clock"]["observed_at_asia_shanghai"] == final_clock.isoformat()
    )
    assert (
        receipt["access_observation_receipt"]["observed_at_asia_shanghai"]
        == final_clock.isoformat()
    )


@pytest.mark.parametrize("clock", ["15:05:00", "15:30:00"])
def test_minute_validator_preserves_post_close_boundary_rows(
    tmp_path: Path, clock: str
) -> None:
    result = addons.collect_pilot(
        minute_request(),
        output_root=tmp_path / clock.replace(":", ""),
        query_fn=FakeQuery("stk_mins", minute_clock_frame(clock)),
        now=HISTORICAL_NOW,
    )
    table = pq.read_table(Path(result.partition_path) / "part.parquet")

    assert table.column("session_segment").to_pylist() == ["unclassified_post_close"]


def test_minute_validator_rejects_clock_after_admitted_post_close_window(
    tmp_path: Path,
) -> None:
    query = FakeQuery("stk_mins", minute_clock_frame("15:31:00"))
    with pytest.raises(addons.CollectorIntegrityError, match="admitted A-share clocks"):
        addons.collect_pilot(
            minute_request(),
            output_root=tmp_path,
            query_fn=query,
            now=HISTORICAL_NOW,
        )
    assert [call[0] for call in query.calls] == [
        "trade_cal",
        "trade_cal",
        "stk_mins",
    ]
    assert not tmp_path.exists() or list(tmp_path.iterdir()) == []


def test_premarket_and_auction_single_ticker_partitions(tmp_path: Path) -> None:
    premarket = addons.collect_pilot(
        addons.PilotRequest(
            endpoint="stk_premarket", trade_date="20260807", ticker="000001.SZ"
        ),
        output_root=tmp_path,
        query_fn=FakeQuery("stk_premarket", premarket_frame()),
        now=HISTORICAL_NOW,
    )
    assert "by_frequency=daily_premarket" in premarket.partition_path

    auction = addons.collect_pilot(
        addons.PilotRequest(
            endpoint="stk_auction", trade_date="2026-08-10", ticker="000001.SZ"
        ),
        output_root=tmp_path,
        query_fn=FakeQuery("stk_auction", auction_frame()),
        now=datetime(2026, 8, 10, 9, 27, tzinfo=SHANGHAI),
    )
    assert "by_frequency=opening_auction" in auction.partition_path
    assert pq.read_table(Path(auction.partition_path) / "part.parquet").num_rows == 1


@pytest.mark.parametrize("endpoint", sorted(addons.ENDPOINTS))
def test_all_library_pilots_require_one_ticker_before_vendor_call(
    tmp_path: Path, endpoint: str
) -> None:
    query = FakeQuery(endpoint, minute_frame())
    with pytest.raises(addons.CollectionHeld, match="require_one_ticker"):
        addons.collect_pilot(
            addons.PilotRequest(
                endpoint=endpoint,
                trade_date="2026-08-07",
                frequency="1min" if endpoint == "stk_mins" else None,
            ),
            output_root=tmp_path,
            query_fn=query,
            now=HISTORICAL_NOW,
        )
    assert query.calls == []
    assert not tmp_path.exists() or list(tmp_path.iterdir()) == []


def test_partial_bundle_fails_closed(tmp_path: Path) -> None:

    normalized = addons.normalize_request(minute_request())
    partial = addons.partition_path(tmp_path, normalized)
    partial.mkdir(parents=True)
    (partial / "part.parquet").write_bytes(b"not a parquet")
    with pytest.raises(addons.CollectorIntegrityError, match="partial"):
        addons.collect_pilot(
            minute_request(),
            output_root=tmp_path,
            query_fn=FakeQuery("stk_mins", minute_frame()),
            now=HISTORICAL_NOW,
        )


def test_https_query_keeps_token_out_of_url(monkeypatch: pytest.MonkeyPatch) -> None:
    observed: dict[str, object] = {}

    class Response:
        status_code = 200
        is_redirect = False
        is_permanent_redirect = False

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"code": 0, "data": {"fields": ["value"], "items": [[1]]}}

    def fake_post(url: str, **kwargs: object) -> Response:
        observed["url"] = url
        observed.update(kwargs)
        return Response()

    monkeypatch.setenv("TUSHARE_TOKEN", "paid-secret")
    monkeypatch.setattr(addons.requests, "post", fake_post)
    frame = addons._query_tushare_https(
        "trade_cal", fields="exchange,cal_date", exchange="SSE"
    )
    assert frame is not None and frame.to_dict(orient="records") == [{"value": 1}]
    assert observed["url"] == "https://api.tushare.pro"
    assert "paid-secret" not in str(observed["url"])
    assert observed["json"]["token"] == "paid-secret"
    assert observed["json"]["fields"] == "exchange,cal_date"
    assert observed["json"]["params"] == {"exchange": "SSE"}
    assert observed["timeout"] == 30
    assert observed["allow_redirects"] is False


def test_https_query_rejects_redirect_without_reading_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class RedirectResponse:
        status_code = 307
        is_redirect = True
        is_permanent_redirect = True

        def raise_for_status(self) -> None:
            raise AssertionError("redirect must be rejected before status parsing")

        def json(self) -> dict[str, object]:
            raise AssertionError("redirect body must never be parsed")

    observed: dict[str, object] = {}

    def fake_post(url: str, **kwargs: object) -> RedirectResponse:
        observed["url"] = url
        observed.update(kwargs)
        return RedirectResponse()

    monkeypatch.setenv("TUSHARE_TOKEN", " paid-secret-with-space ")
    monkeypatch.setattr(addons.requests, "post", fake_post)

    assert addons._query_tushare_https("trade_cal", exchange="SSE") is None
    assert observed["url"] == "https://api.tushare.pro"
    assert observed["allow_redirects"] is False


def test_cli_defaults_to_plan_and_has_no_range_or_backfill_surface(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    parser = cli.build_parser()
    option_strings = {
        option for action in parser._actions for option in action.option_strings
    }
    for subparser_action in parser._subparsers._actions:
        for subparser in (getattr(subparser_action, "choices", None) or {}).values():
            option_strings.update(
                option
                for action in subparser._actions
                for option in action.option_strings
            )
    assert "--start-date" not in option_strings
    assert "--end-date" not in option_strings
    assert "--backfill" not in option_strings
    endpoint_parsers = next(
        action.choices for action in parser._actions if getattr(action, "choices", None)
    )
    # Every admitted library contract must be reachable from the CLI, and the CLI
    # must not offer an endpoint the library has no contract for.
    assert set(endpoint_parsers) == set(addons.ENDPOINTS)
    for endpoint_parser in endpoint_parsers.values():
        ticker_action = next(
            action for action in endpoint_parser._actions if action.dest == "ticker"
        )
        assert ticker_action.required is True

    rc = cli.main(
        [
            "stk_mins",
            "--trade-date",
            "2026-08-07",
            "--ticker",
            "600519.SS",
            "--frequency",
            "1min",
            "--output-root",
            str(tmp_path / "planned"),
        ]
    )
    assert rc == 0
    assert (
        json.loads(capsys.readouterr().out)["status"] == "planned_no_network_no_write"
    )
    assert not (tmp_path / "planned").exists()


def test_cli_execute_requires_explicit_output_root_before_collection(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args: object, **kwargs: object) -> addons.PilotResult:
        raise AssertionError("collector must not run without explicit output root")

    monkeypatch.setattr(cli, "collect_pilot", forbidden)
    rc = cli.main(
        [
            "stk_mins",
            "--trade-date",
            "2026-08-07",
            "--ticker",
            "600519.SS",
            "--frequency",
            "1min",
            "--execute",
        ]
    )

    assert rc == 2
    assert json.loads(capsys.readouterr().out)["reason_code"] == (
        "execute_requires_explicit_output_root"
    )


def test_cli_failure_receipt_does_not_echo_exception_or_secret(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "vendor-exception-contained-this-secret"

    def fail(*args: object, **kwargs: object) -> addons.PilotResult:
        raise RuntimeError(secret)

    monkeypatch.setattr(cli, "collect_pilot", fail)
    rc = cli.main(
        [
            "stk_mins",
            "--trade-date",
            "2026-08-07",
            "--ticker",
            "600519.SS",
            "--frequency",
            "1min",
            "--output-root",
            str(tmp_path),
            "--execute",
        ]
    )
    payload = capsys.readouterr().out
    assert rc == 4
    assert secret not in payload
    assert json.loads(payload) == {
        "authority": "context_display_only",
        "endpoint": "stk_mins",
        "reason_code": "unexpected_collector_failure",
        "status": "unexpected_failure_fail_closed",
    }


def test_reverted_manual_pilot_infrastructure_stays_retired() -> None:
    """The recovered collector must not resurrect #5098's retired runner lane."""
    workflow_path = ROOT / ".github/workflows/tushare-addons-pilot.yml"
    lock_path = ROOT / "requirements/tushare-addons-pilot-macos-arm64-py312.lock"
    dag_text = (ROOT / "config/dag.yml").read_text(encoding="utf-8")

    assert not workflow_path.exists()
    assert not lock_path.exists()
    assert "tushare-addons-pilot.yml" not in dag_text
    assert "scripts.collect_tushare_addons" not in dag_text


# China physical-gold close-basis source seam (stacked source slice).

class _GoldBasisResp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def _gold_basis_ms(ts: str) -> int:
    return int(pd.Timestamp(ts).timestamp() * 1000)


def test_sge_au9999_frame_filters_contract_and_stamps_shanghai_close():
    from collectors import china_gold_basis as cgb

    raw = pd.DataFrame(
        [
            {"ts_code": "Au99.95", "trade_date": "20260917", "close": 816.0},
            {"ts_code": "Au99.99", "trade_date": "20260917", "close": 817.25},
            {"ts_code": "Au99.99", "trade_date": "20260918", "close": 820.50},
        ]
    )

    out = cgb._sge_au9999_frame(raw)

    assert list(out.columns) == ["rmb_per_g"]
    assert list(out["rmb_per_g"]) == [817.25, 820.50]
    assert list(out.index) == [
        pd.Timestamp("2026-09-17T07:30:00"),
        pd.Timestamp("2026-09-18T07:30:00"),
    ]


def test_massive_xaucny_frame_selects_nearest_bar_to_shanghai_close():
    from collectors import china_gold_basis as cgb

    payload = {
        "results": [
            {"t": _gold_basis_ms("2026-09-18T07:27:00Z"), "c": 30900.0},
            {"t": _gold_basis_ms("2026-09-18T07:29:00Z"), "c": 30950.0},
            {"t": _gold_basis_ms("2026-09-18T07:30:00Z"), "c": 30960.0},
            {"t": _gold_basis_ms("2026-09-18T07:31:00Z"), "c": 30970.0},
        ]
    }

    out = cgb._massive_xaucny_frame(payload, tolerance_minutes=2)

    assert list(out.columns) == ["cny_per_oz"]
    assert len(out) == 1
    assert out.index[0] == pd.Timestamp("2026-09-18T07:30:00")
    assert out.iloc[0]["cny_per_oz"] == pytest.approx(30960.0)


def test_massive_xaucny_frame_drops_days_without_close_aligned_bar():
    from collectors import china_gold_basis as cgb

    payload = {
        "results": [
            {"t": _gold_basis_ms("2026-09-18T07:20:00Z"), "c": 30900.0},
            {"t": _gold_basis_ms("2026-09-18T07:40:00Z"), "c": 31000.0},
        ]
    }

    out = cgb._massive_xaucny_frame(payload, tolerance_minutes=2)

    assert out.empty


def test_adapter_fetch_uses_existing_tushare_client_and_massive_currency_key(monkeypatch):
    from collectors import china_gold_basis as cgb

    raw_sge = pd.DataFrame(
        [
            {"ts_code": "Au99.99", "trade_date": "20260917", "close": 817.25},
            {"ts_code": "Au99.99", "trade_date": "20260918", "close": 820.50},
        ]
    )
    calls = []

    monkeypatch.setattr(cgb.tushare_client, "enabled", lambda: True)
    monkeypatch.setattr(
        cgb.tushare_client,
        "query",
        lambda api_name, **kwargs: raw_sge.copy()
        if api_name == "sge_daily"
        else (_ for _ in ()).throw(AssertionError(api_name)),
    )
    monkeypatch.setattr(cgb.config, "secret", lambda name: "massive-key" if name in {"POLYGON_API_KEY", "MASSIVE_API_KEY"} else None)

    adapter = cgb.ChinaGoldBasisAdapter()

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return _GoldBasisResp(
            {
                "results": [
                    {"t": _gold_basis_ms("2026-09-17T07:30:00Z"), "c": 30750.0},
                    {"t": _gold_basis_ms("2026-09-18T07:30:00Z"), "c": 30960.0},
                ]
            }
        )

    monkeypatch.setattr(adapter, "http_get", fake_get)

    frames = adapter.fetch(full_history=False)

    assert set(frames) == {"sge_au9999", "xaucny_spot"}
    assert list(frames["sge_au9999"]["rmb_per_g"]) == [817.25, 820.50]
    assert list(frames["xaucny_spot"]["cny_per_oz"]) == [30750.0, 30960.0]
    assert calls
    url, kwargs = calls[0]
    assert "C:XAUUSD" not in url
    assert "C:XAUCNY" in url
    assert kwargs["headers"]["Authorization"] == "Bearer massive-key"
    assert "apiKey" not in kwargs.get("params", {})


def test_adapter_without_either_credential_is_known_blocked(monkeypatch):
    from collectors import china_gold_basis as cgb

    monkeypatch.setattr(cgb.tushare_client, "enabled", lambda: False)
    monkeypatch.setattr(cgb.config, "secret", lambda name: None)

    adapter = cgb.ChinaGoldBasisAdapter()

    assert adapter.expected_failure
    with pytest.raises(RuntimeError, match="credentials"):
        adapter.fetch()


def test_production_config_wires_close_proxy_to_source_store_without_vendor_branding():
    from lib import config

    cfg = config.load()["commodities"]["china_gold_premium"]
    proxy = cfg["close_proxy"]

    assert proxy["sge"] == {
        "group": "gold_china_basis",
        "name": "sge_au9999",
        "column": "rmb_per_g",
        "source_label": "Shanghai Gold Exchange Au99.99",
        "entitled": True,
    }
    assert proxy["global"] == {
        "group": "gold_china_basis",
        "name": "xaucny_spot",
        "column": "cny_per_oz",
        "source_label": "Global XAU/CNY spot",
        "entitled": True,
    }
    assert proxy["max_skew_minutes"] == 2
    assert proxy["max_age_days"] == 4
    public_labels = " ".join((proxy["sge"]["source_label"], proxy["global"]["source_label"]))
    assert "Tushare" not in public_labels
    assert "Massive" not in public_labels
    assert "Polygon" not in public_labels


def test_collector_registry_places_gold_basis_on_existing_us_nightly_shard():
    from scripts import collect

    registry = collect.all_adapters()

    assert "gold_china_basis" in registry
    assert registry["gold_china_basis"].__name__ == "ChinaGoldBasisAdapter"
    assert "gold_china_basis" in collect.group_members("us", registry)
    assert "gold_china_basis" not in collect.group_members("asia", registry)


def test_daily_nightly_already_supplies_both_gold_basis_credentials():
    from pathlib import Path

    repo = Path(__file__).resolve().parents[1]
    text = (repo / ".github" / "workflows" / "daily.yml").read_text()

    assert "TUSHARE_TOKEN: ${{ secrets.TUSHARE_TOKEN }}" in text
    assert "POLYGON_API_KEY: ${{ secrets.POLYGON_API_KEY }}" in text
    assert "MASSIVE_API_KEY: ${{ secrets.MASSIVE_API_KEY }}" in text
    assert "python -m scripts.collect --exclude-group asia" in text


def test_massive_history_chunks_never_exceed_fourteen_calendar_days():
    from datetime import date
    from collectors import china_gold_basis as cgb

    chunks = list(cgb._date_chunks(date(2026, 7, 1), date(2026, 8, 9), max_days=14))

    assert chunks[0] == (date(2026, 7, 1), date(2026, 7, 14))
    assert chunks[-1][1] == date(2026, 8, 9)
    for start, end in chunks:
        assert (end - start).days <= 13
    for left, right in zip(chunks, chunks[1:]):
        assert right[0] == left[1] + pd.Timedelta(days=1)


def test_adapter_filters_tushare_request_to_au9999(monkeypatch):
    from collectors import china_gold_basis as cgb

    seen = {}
    monkeypatch.setattr(cgb.tushare_client, "enabled", lambda: True)
    monkeypatch.setattr(cgb.config, "secret", lambda name: "massive-key")
    raw_sge = pd.DataFrame(
        [{"ts_code": "Au99.99", "trade_date": "20260918", "close": 820.5}]
    )

    def fake_query(api_name, **kwargs):
        seen.update(kwargs)
        return raw_sge

    monkeypatch.setattr(cgb.tushare_client, "query", fake_query)
    adapter = cgb.ChinaGoldBasisAdapter()
    monkeypatch.setattr(
        adapter,
        "http_get",
        lambda *args, **kwargs: _GoldBasisResp(
            {"results": [{"t": _gold_basis_ms("2026-09-18T07:30:00Z"), "c": 30960.0}]}
        ),
    )

    adapter.fetch()

    assert seen["ts_code"] == "Au99.99"


def test_collector_store_is_consumed_by_engine_and_audited_render_without_translation(tmp_path, monkeypatch):
    import copy
    import json

    from collectors import china_gold_basis as cgb
    from collectors.base import run_adapter
    from engine import china_gold_premium as cgp
    from lib import config, store
    from scripts import audit_china_gold_premium as audit

    cfg = copy.deepcopy(config.load())
    cfg["storage"]["site_dir"] = "site"
    data_root = tmp_path / "data"
    site_root = tmp_path / "site"
    site_root.mkdir(parents=True)

    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setattr(config, "data_dir", lambda: data_root)
    monkeypatch.setattr(config, "load", lambda: cfg)
    monkeypatch.setattr(cgb.tushare_client, "enabled", lambda: True)
    monkeypatch.setattr(cgb.config, "secret", lambda name: "fixture-key")
    adapter = cgb.ChinaGoldBasisAdapter()

    now = pd.Timestamp.now(tz="UTC")
    latest = (now.normalize() - pd.Timedelta(days=1) + pd.Timedelta(hours=7, minutes=30)).tz_convert(None)
    idx = pd.DatetimeIndex([latest - pd.Timedelta(days=1), latest])
    frames = {
        "sge_au9999": pd.DataFrame({"rmb_per_g": [817.0, 820.5]}, index=idx),
        "xaucny_spot": pd.DataFrame({"cny_per_oz": [25380.0, 25490.0]}, index=idx),
    }
    monkeypatch.setattr(
        adapter,
        "fetch",
        lambda full_history=False: {name: frame.copy() for name, frame in frames.items()},
    )

    result = run_adapter(adapter)

    assert result.status == "ok"
    stored_sge = store.read("gold_china_basis", "sge_au9999")
    assert stored_sge is not None
    assert stored_sge.index[-1] == latest

    vm = cgp.build_view_model(
        cfg["commodities"]["china_gold_premium"],
        now=now,
    )
    assert vm["available"] is True
    assert vm["current_method"] == "close_proxy"
    expected_asof = latest.tz_localize("UTC").isoformat()
    assert vm["close_proxy"]["asof"] == expected_asof

    site_root.joinpath("commodities.html").write_text(
        '<section id="gold-china-premium" '
        f'data-cgp-state="{vm["state"]}" '
        f'data-cgp-display-source="{vm["chart"]["display_source"]}" '
        f'data-cgp-currency="{vm["price_currency"]}" '
        f'data-cgp-source-asof="{vm["close_proxy"]["asof"]}" '
        f'data-cgp-premium="{vm["premium_pct"]:.6f}"></section>'
    )
    # The builder's compact projection is pinned independently in
    # tests/test_china_gold_premium.py. Keep this source-plane test hermetic to
    # the china-native-collectors CI job, which intentionally does not install
    # heavy page-render dependencies such as Plotly.
    machine = {
        "available": bool(vm.get("available")),
        "method": vm.get("current_method"),
        "state": vm.get("state"),
        "premium_pct": vm.get("premium_pct"),
        "price_currency": vm.get("price_currency"),
        "source_asof": vm["close_proxy"].get("asof"),
        "source_fresh": bool(vm["close_proxy"].get("fresh")),
        "avg_5_pct": vm["stats"].get("avg_5"),
        "range_30_pct": vm["stats"].get("range_30"),
        "official_canonical_available": bool(vm["canonical"].get("available")),
        "context_only": True,
    }
    commodity_dir = data_root / "commodity"
    commodity_dir.mkdir(parents=True)
    commodity_dir.joinpath("latest.json").write_text(
        json.dumps({"gold_context": {"china_physical_premium": machine}})
    )

    rc = audit.run(strict_render=True)
    persisted = json.loads(
        (data_root / "quality" / "china_gold_premium.json").read_text()
    )
    assert rc == 0
    assert persisted["status"] == "available_fresh"
    assert persisted["headline_method"] == "close_proxy"
    assert persisted["render_consistent"] is True
    assert persisted["machine_projection_consistent"] is True
    assert persisted["source_asof"] == expected_asof
    assert persisted["official_canonical_available"] is False


def test_gold_premium_quality_audit_runs_immediately_after_commodity_builder():
    from pathlib import Path

    repo = Path(__file__).resolve().parents[1]
    text = (repo / "scripts" / "ci" / "daily_engine_regional_desk_builders.sh").read_text()

    build = 'brun commodities  "build commodity vector (build_commodities)"         scripts.build_commodities'
    audit = 'brun commodities_gold_premium_audit "audit China gold premium live path" scripts.audit_china_gold_premium --strict-render'
    assert build in text
    assert audit in text
    assert text.index(build) < text.index(audit) < text.index('brun spr')

    order_line = next(
        line for line in text.splitlines() if line.startswith('ORDER="')
    )
    order = order_line.split('"', 2)[1].split()
    assert order.index("commodities") < order.index("commodities_gold_premium_audit") < order.index("spr")


def test_gold_basis_store_namespace_survives_us_nightly_china_reset():
    from fnmatch import fnmatch
    from collectors.china_gold_basis import ChinaGoldBasisAdapter
    from lib import config

    adapter = ChinaGoldBasisAdapter()
    assert adapter.name == "gold_china_basis"
    assert adapter.group == "gold_china_basis"

    proxy = config.load()["commodities"]["china_gold_premium"]["close_proxy"]
    assert proxy["sge"]["group"] == "gold_china_basis"
    assert proxy["global"]["group"] == "gold_china_basis"

    # daily.yml's US-nightly commit deliberately unstages data/china_* because
    # that namespace belongs to asia-close. This source is US-nightly-owned, so
    # its store namespace must never match that reset pattern.
    assert not fnmatch(f"data/{adapter.group}", "data/china_*")


def test_gold_basis_cold_start_seeds_enough_history_for_30_session_stats(monkeypatch):
    from collectors import china_gold_basis as cgb

    monkeypatch.setattr(cgb.tushare_client, "enabled", lambda: True)
    monkeypatch.setattr(cgb.config, "secret", lambda name: "fixture-key")
    adapter = cgb.ChinaGoldBasisAdapter()

    from datetime import date

    monkeypatch.setattr(cgb.store, "last_date", lambda group, name: None)
    assert adapter._fetch_window_days(
        full_history=False,
        today=date(2026, 9, 18),
    ) >= 90

    monkeypatch.setattr(
        cgb.store,
        "last_date",
        lambda group, name: date(2026, 9, 18),
    )
    deep_idx = pd.date_range("2026-08-01 07:30:00", periods=35, freq="D")
    monkeypatch.setattr(
        cgb.store,
        "read",
        lambda group, name: pd.DataFrame({"v": range(35)}, index=deep_idx),
    )
    assert adapter._fetch_window_days(
        full_history=False,
        today=date(2026, 9, 18),
    ) == cgb._REFRESH_DAYS
    assert adapter._fetch_window_days(
        full_history=True,
        today=date(2026, 9, 18),
    ) == 370


def test_gold_basis_refresh_recovers_a_long_store_gap(monkeypatch):
    from datetime import date
    from collectors import china_gold_basis as cgb

    monkeypatch.setattr(cgb.tushare_client, "enabled", lambda: True)
    monkeypatch.setattr(cgb.config, "secret", lambda name: "fixture-key")
    adapter = cgb.ChinaGoldBasisAdapter()

    monkeypatch.setattr(
        cgb.store,
        "last_date",
        lambda group, name: date(2026, 7, 1),
    )

    days = adapter._fetch_window_days(
        full_history=False,
        today=date(2026, 9, 18),
    )

    assert days >= 90
    assert days >= (date(2026, 9, 18) - date(2026, 7, 1)).days + 14


def test_gold_basis_refresh_stays_bounded_when_store_is_current(monkeypatch):
    from datetime import date
    from collectors import china_gold_basis as cgb

    monkeypatch.setattr(cgb.tushare_client, "enabled", lambda: True)
    monkeypatch.setattr(cgb.config, "secret", lambda name: "fixture-key")
    adapter = cgb.ChinaGoldBasisAdapter()

    latest = {
        "sge_au9999": date(2026, 9, 17),
        "xaucny_spot": date(2026, 9, 18),
    }
    monkeypatch.setattr(
        cgb.store,
        "last_date",
        lambda group, name: latest[name],
    )
    deep_idx = pd.date_range("2026-08-01 07:30:00", periods=35, freq="D")
    monkeypatch.setattr(
        cgb.store,
        "read",
        lambda group, name: pd.DataFrame({"v": range(35)}, index=deep_idx),
    )

    assert adapter._fetch_window_days(
        full_history=False,
        today=date(2026, 9, 18),
    ) == cgb._REFRESH_DAYS


def test_gold_premium_quality_audit_rechecks_post_normalization_tree_before_stage():
    from pathlib import Path

    repo = Path(__file__).resolve().parents[1]
    text = (repo / "scripts" / "ci" / "daily_engine_commit_outputs.sh").read_text()

    optimize = 'python -m scripts.optimize_assets'
    audit = 'python -m scripts.audit_china_gold_premium --strict-render'
    stage = 'git add data/ site/ reports/'

    assert optimize in text
    assert audit in text
    assert stage in text
    strip = 'strip_conflict_markers.sh'
    assert text.index(optimize) < text.index(strip) < text.index(audit) < text.index(stage)
    assert 'China gold premium final render audit' in text


def test_gold_basis_exact_massive_endpoint_probe_is_code_gated():
    from scripts import massive_entitlement_probe as mep

    class Resp:
        status_code = 200

        def json(self):
            return {
                "resultsCount": 1,
                "results": [{"t": 1, "c": 30000.0}],
            }

    class Session:
        def __init__(self):
            self.headers = {}
            self.calls = []

        def get(self, url, params=None, timeout=None):
            self.calls.append({"url": url, "params": params, "timeout": timeout})
            return Resp()

    session = Session()
    prober = mep.RestProber(
        "fixture-key",
        base_url="https://api.massive.example",
        session=session,
    )
    results = mep.run_rest_battery(prober, probe_day="2026-09-18")

    exact = results["fx_gold_cny_minute"]
    assert exact["verdict"] == "entitled"
    calls = [
        call for call in session.calls
        if "C:XAUCNY/range/1/minute/2026-09-18/2026-09-18" in call["url"]
    ]
    assert len(calls) == 1
    assert calls[0]["params"]["limit"] == 5


def test_gold_basis_cold_start_prioritizes_current_chunk_and_keeps_recent_data_when_old_history_fails(monkeypatch):
    from datetime import datetime, timezone
    from collectors import china_gold_basis as cgb

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            value = cls(2026, 9, 18, 12, 0, tzinfo=timezone.utc)
            return value if tz is None else value.astimezone(tz)

    raw_sge = pd.DataFrame(
        [
            {"ts_code": "Au99.99", "trade_date": "20260917", "close": 817.25},
            {"ts_code": "Au99.99", "trade_date": "20260918", "close": 820.50},
        ]
    )

    monkeypatch.setattr(cgb, "datetime", FixedDateTime)
    monkeypatch.setattr(cgb.tushare_client, "enabled", lambda: True)
    monkeypatch.setattr(cgb.config, "secret", lambda name: "fixture-key")
    monkeypatch.setattr(cgb.store, "last_date", lambda group, name: None)
    monkeypatch.setattr(cgb.tushare_client, "query", lambda api_name, **kwargs: raw_sge.copy())

    adapter = cgb.ChinaGoldBasisAdapter()
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        # The newest chunk must be attempted first. It succeeds with current data;
        # older-history entitlement/network failures may reduce depth but must not
        # black out the current product reading.
        if url.endswith("/2026-09-05/2026-09-18"):
            return _GoldBasisResp(
                {
                    "results": [
                        {"t": _gold_basis_ms("2026-09-17T07:30:00Z"), "c": 30750.0},
                        {"t": _gold_basis_ms("2026-09-18T07:30:00Z"), "c": 30960.0},
                    ]
                }
            )
        raise RuntimeError("older minute history unavailable")

    monkeypatch.setattr(adapter, "http_get", fake_get)

    frames = adapter.fetch(full_history=False)

    assert calls[0].endswith("/2026-09-05/2026-09-18")
    assert list(frames["xaucny_spot"].index) == [
        pd.Timestamp("2026-09-17T07:30:00"),
        pd.Timestamp("2026-09-18T07:30:00"),
    ]
    assert list(frames["sge_au9999"]["rmb_per_g"]) == [817.25, 820.50]


def test_gold_basis_refresh_keeps_backfilling_until_thirty_aligned_sessions(monkeypatch):
    from datetime import date
    from collectors import china_gold_basis as cgb

    monkeypatch.setattr(cgb.tushare_client, "enabled", lambda: True)
    monkeypatch.setattr(cgb.config, "secret", lambda name: "fixture-key")
    adapter = cgb.ChinaGoldBasisAdapter()

    idx = pd.date_range("2026-09-08 07:30:00", periods=10, freq="D")
    frames = {
        "sge_au9999": pd.DataFrame({"rmb_per_g": range(10)}, index=idx),
        "xaucny_spot": pd.DataFrame({"cny_per_oz": range(10)}, index=idx),
    }
    monkeypatch.setattr(
        cgb.store,
        "read",
        lambda group, name: frames[name].copy(),
    )
    monkeypatch.setattr(
        cgb.store,
        "last_date",
        lambda group, name: date(2026, 9, 17),
    )

    assert adapter._fetch_window_days(
        full_history=False,
        today=date(2026, 9, 18),
    ) >= cgb._COLD_START_DAYS

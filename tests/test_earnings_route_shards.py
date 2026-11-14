"""Redaction, deterministic bucketing and fail-closed route-shard regression."""
from __future__ import annotations

from copy import deepcopy
import json

import pytest

from scripts.earnings_route_shards import (
    CATALOG_SCHEMA,
    SHARD_COUNT,
    SHARD_SCHEMA,
    EarningsRouteShardError,
    build_route_shards,
    shard_filename,
    shard_index,
)


def _row(slug: str, period: str = "Q4 FY2026", transcript: str = "2026Q4") -> dict:
    return {
        "href": slug,
        "period": period,
        "transcript_id": transcript,
        "date": "2026-11-02",
        "dossier_available": False,
    }


def _catalog() -> dict:
    apple = _row("aapl-2026q4-call-record.html")
    berkshire = _row("brk-b-2026q4-call-record.html")
    return {
        "schema": CATALOG_SCHEMA,
        "source_generation_id": "generation-123",
        "verified_at": "2026-11-12T00:00:00Z",
        "source_manifest_sha256": "SECRET_MUST_NOT_LEAK",
        "deferred_packet_keys": ["SECRET_DEFERRED"],
        "forward_selection_floor_date": "2026-07-29",
        "routes": {
            "AAPL": {
                "company_name": "Apple Inc.",
                "latest": apple,
                "events": {"2026Q4": apple},
            },
            "BRK.B": {
                "company_name": "Berkshire Hathaway",
                "latest": berkshire,
                "events": {"2026Q4": berkshire},
            },
        },
    }


def _project(payload: dict) -> dict[str, bytes]:
    return build_route_shards(json.dumps(payload).encode("utf-8"))


def test_shard_index_is_fixed_ascii_browser_contract() -> None:
    assert shard_filename("AAPL") == "part-1c.json"
    assert shard_filename("MSFT") == "part-34.json"
    assert shard_filename("BRK.B") == "part-0f.json"
    assert shard_filename("TSLA") == "part-34.json"
    assert shard_index("A") == 1
    assert SHARD_COUNT == 64


def test_shards_preserve_only_exact_route_lookup_fields() -> None:
    catalog = _catalog()
    shards = _project(catalog)
    assert len(shards) == SHARD_COUNT
    assert set(shards) == {f"part-{index:02x}.json" for index in range(SHARD_COUNT)}
    combined: dict = {}
    empty = 0
    for index in range(SHARD_COUNT):
        filename = f"part-{index:02x}.json"
        raw = shards[filename]
        assert raw.endswith(b"\n")
        assert b"SECRET" not in raw
        assert b"company_name" not in raw
        assert b"dossier_available" not in raw
        assert b"source_manifest_sha256" not in raw
        assert b"forward_selection_floor_date" not in raw
        shard = json.loads(raw)
        assert set(shard) == {"schema", "shard", "routes"}
        assert shard["schema"] == SHARD_SCHEMA
        assert shard["shard"] == f"{index:02x}"
        if not shard["routes"]:
            empty += 1
        for ticker, record in shard["routes"].items():
            assert shard_filename(ticker) == filename
            assert set(record) == {"events", "latest"}
            assert set(record["latest"]) == {"href", "period", "transcript_id"}
            assert set(record["events"]["2026Q4"]) == {"href", "period", "transcript_id"}
            assert record["latest"]["href"] == catalog["routes"][ticker]["latest"]["href"]
            combined[ticker] = record
    assert empty == 62
    assert set(combined) == set(catalog["routes"])


def test_shards_are_deterministic_regardless_of_input_object_order() -> None:
    catalog = _catalog()
    expected = _project(catalog)
    catalog["routes"] = dict(reversed(list(catalog["routes"].items())))
    assert _project(catalog) == expected


def test_unchanged_routes_do_not_change_when_source_clock_advances() -> None:
    catalog = _catalog()
    expected = _project(catalog)
    catalog["verified_at"] = "2026-11-13T00:47:00Z"
    catalog["source_generation_id"] = "new-source-generation"
    catalog["source_manifest_sha256"] = "another-original-source-receipt"
    assert _project(catalog) == expected


def test_only_affected_ticker_bucket_changes() -> None:
    catalog = _catalog()
    before = _project(catalog)
    catalog["routes"]["AAPL"]["events"]["2026Q4"]["href"] = "aapl-2026q4-corrected-call-record.html"
    after = _project(catalog)
    assert [key for key in sorted(before) if before[key] != after[key]] == [shard_filename("AAPL")]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda c: c.update(schema="earnings.public_wire_routes/v1"),
        lambda c: c.update(source_generation_id=None),
        lambda c: c["routes"].update({"../escape": c["routes"].pop("AAPL")}),
        lambda c: c["routes"]["AAPL"].update(events=[]),
        lambda c: c["routes"]["AAPL"]["latest"].update(href="../private.json"),
        lambda c: c["routes"]["AAPL"]["latest"].update(period=42),
        lambda c: c["routes"]["AAPL"]["events"].update({"bad": None}),
    ],
)
def test_bad_canonical_inputs_fail_closed_without_shards(mutation) -> None:
    catalog = deepcopy(_catalog())
    mutation(catalog)
    with pytest.raises(EarningsRouteShardError):
        _project(catalog)


def test_invalid_json_fails_closed() -> None:
    with pytest.raises(EarningsRouteShardError):
        build_route_shards(b"{bad")


@pytest.mark.parametrize("ticker", ["AAPL", "BRK.B", "BRK.", "-BRK", "BRK-", ".", "1" * 16])
@pytest.mark.parametrize("transcript", [
    "2026Q4", "2026_Q4", "2026.Q4", "2026-Q4", "Q4_v2.1",
    "_Q4", ".Q4", "2026..Q4", "T" * 80,
])
def test_canonical_wire_identities_round_trip(ticker: str, transcript: str) -> None:
    """The derived projector must accept the real producer's filename grammar."""
    from engine.earnings_narrative.public_wire import wire_slug

    row = _row(f"{wire_slug(ticker, transcript)}.html", transcript=transcript)
    catalog = _catalog()
    catalog["routes"] = {ticker: {"latest": row, "events": {transcript: row}}}
    shards = _project(catalog)
    projected = json.loads(shards[shard_filename(ticker)])["routes"][ticker]
    expected = {key: row[key] for key in ("href", "period", "transcript_id")}
    assert projected == {"latest": expected, "events": {transcript: expected}}
    assert len(shards) == SHARD_COUNT


@pytest.mark.parametrize("href", [
    "../a.html", "a/b.html", "a\\b.html", "https://example.com/a.html",
    "//host/a.html", "a%2fb.html", "a?b.html", "a#b.html", "a b.html",
    "a\nb.html", "a\x00b.html", "é.html", "<a>.html", ".hidden.html", "A.html",
])
def test_unsafe_or_noncanonical_href_is_rejected(href: str) -> None:
    catalog = _catalog()
    catalog["routes"]["AAPL"]["latest"]["href"] = href
    with pytest.raises(EarningsRouteShardError, match="unsafe.*href"):
        _project(catalog)


@pytest.mark.parametrize("ticker", [
    None, "", "A" * 17, "aapl", "A/B", "A\\B", "A B", "A%", "Ä", "A\n",
])
def test_invalid_ticker_is_rejected(ticker) -> None:
    with pytest.raises(EarningsRouteShardError, match="invalid.*ticker"):
        shard_index(ticker)

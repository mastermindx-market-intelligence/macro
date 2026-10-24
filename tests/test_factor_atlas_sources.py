"""Incumbent-owner adapter integration. Stores and rights in this file are synthetic."""
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import date
import hashlib
import importlib
import importlib.util
import json

import pandas as pd
import pytest

from engine import basket_membership_pit as pit
from engine import price_ladder
from lib import config
from lib.dataos.identity import AliasRow, ListingKey, VendorAliasTable, security_id

DAYS = ["2026-01-28", "2026-01-29", "2026-01-30"]
SIDS = [security_id(ListingKey("US", "XNYS", t)) for t in ("AAA", "BBB", "CCC")]


def module():
    assert importlib.util.find_spec("engine.factor_atlas_sources") is not None, "native owner bridge is missing"
    return importlib.import_module("engine.factor_atlas_sources")


def receipt(doc, day):
    generation = pit.collection_generation_sha(doc)
    slots = pit._members_from_membership(doc)
    value = dict(schema="basket_membership_collection/v2", suite=pit.SUITE_US,
                 basket_id="mag7", source_ref="data/baskets/membership.json",
                 generation_id=generation[:16], generation_sha256=generation,
                 collection_state="COMPLETE", source_clock_grain="instant",
                 observed_at=day + "T08:00:00Z", known_at=day + "T09:00:00Z",
                 members_sha=pit._sha_of(slots), member_count=len(slots),
                 authority_caps=dict(may_rank=False, may_size=False, may_gate=False, may_escalate=False))
    value["collection_id"] = pit.collection_id(value)
    return value


@pytest.fixture
def owners(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    doc = {"baskets": {"mag7": {"members": [
        {"ticker": t, "added": "2026-01-01", "removed": None} for t in ("AAA", "BBB", "CCC")]}}}
    target = tmp_path / "baskets" / "membership.json"
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(doc))
    stamped = pit.append_snapshot(pit.SUITE_US, asof="2026-01-27", lane="nightly",
                                  collection_receipts=[receipt(doc, "2026-01-27")])
    assert stamped["written"]
    for t in ("AAA", "BBB", "CCC"):
        p = tmp_path / "baskets" / "ohlcv" / f"{t}.parquet"
        p.parent.mkdir(exist_ok=True)
        pd.DataFrame({"close": [100., 110., 121.] if t == "AAA" else [100., 100., 100.]},
                     index=pd.to_datetime(DAYS)).to_parquet(p)
    aliases = VendorAliasTable([
        AliasRow(vendor=space, vendor_symbol=t, security_id=sid,
                 valid_from=date(2026, 1, 1), known_at="2026-01-01T00:00:00Z")
        for t, sid in zip(("AAA", "BBB", "CCC"), SIDS)
        for space in ("membership", "store")])
    request = dict(basket_id="mag7", history_mode="PIT_AS_KNOWN", start=DAYS[0], end=DAYS[-1],
                   measurement_cutoff="2026-02-12T00:00:00Z", purpose="internal_research",
                   weighting="equal", rebalance="monthly")
    calls = []
    def membership(day):
        calls.append(day)
        raw = pit.members_asof("mag7", day, suite=pit.SUITE_US)
        return {"value": raw, "snapshot_ref": "fixture:membership-history",
                "source_sha256": hashlib.sha256(pit.history_path(pit.SUITE_US).read_bytes()).hexdigest()}
    def price(ticker):
        return price_ladder.resolve_close(ticker, data_dir=str(tmp_path),
                                         allow_unadjusted=False, capture_evidence=True,
                                         start=DAYS[0], asof=DAYS[-1])
    options = dict(membership_reader=membership, aliases=aliases,
                   construction={"inception": DAYS[0], "owner_ref": "fixture:method/v1"},
                   alias_snapshot_ref="fixture:vendor-aliases", price_reader=price,
                   code_ref="fixture:code/v1", input_revision="fixture:owner-input/v1",
                   evidence_kind="SYNTHETIC_FIXTURE",
                   decision_cutoffs={DAYS[0]: DAYS[0] + "T20:59:00Z"},
                   currency_by_security={sid: "USD" for sid in SIDS},
                   rights={"status": "QUALIFIED", "purpose": "internal_research", "owner_ref": "fixture:rights"})
    return request, options, tmp_path, calls


def qualify_price_reader(options):
    old = options["price_reader"]
    def qualified(ticker):
        result = old(ticker)
        result.evidence = replace(result.evidence, adjustment_asof="2026-02-11T22:00:00Z",
                                  observed_at="2026-02-11T22:00:00Z",
                                  session="regular", venue_scope="consolidated")
        return result
    options["price_reader"] = qualified
    options["corporate_action_refs"] = {sid: "fixture:actions/v1" for sid in SIDS}


def test_native_owner_reads_expose_unattested_price_metadata(owners):
    request, options, _, _ = owners
    result = module().build_from_owners(request, **options)
    assert result["binding_status"] == "BOUND"
    assert result["read"]["status"] == "UNAVAILABLE"
    assert "ADJUSTMENT_VINTAGE_UNAVAILABLE" in result["read"]["reasons"]
    assert all(v["content_sha256"] for v in result["read"]["source_refs"]["prices"].values())
    assert result["read"]["release_state"] == "CANDIDATE_NOT_ADMITTED"


def test_real_native_readers_compute_when_fixture_evidence_is_qualified(owners):
    request, options, _, calls = owners
    qualify_price_reader(options)
    result = module().build_from_owners(request, **options)
    assert calls == [DAYS[0]]
    assert result["read"]["analytics"]["window_return"] == pytest.approx(0.07)
    assert result["read"]["history_mode"] == "PIT_AS_KNOWN"
    assert result["read"]["evidence_kind"] == "SYNTHETIC_FIXTURE"


def test_current_mode_does_not_call_historical_dates(owners):
    request, options, _, calls = owners
    qualify_price_reader(options)
    request["history_mode"] = "CURRENT_ROSTER"
    options["current_roster_asof"] = "2026-01-30"
    result = module().build_from_owners(request, **options)
    assert calls == ["2026-01-30"]
    assert result["read"]["status"] == "READY"
    assert result["read"]["history_mode"] == "CURRENT_ROSTER"


def test_unmapped_symbol_does_not_shrink_the_denominator(owners):
    request, options, _, _ = owners
    options["aliases"] = VendorAliasTable([row for row in options["aliases"].rows if row.security_id != SIDS[0]])
    result = module().build_from_owners(request, **options)
    assert result["read"] is None
    assert result["binding_status"] == "UNAVAILABLE"
    assert result["unresolved_symbols"] == ["AAA"]
    assert result["requested_member_count"] == 3
    assert "UNRESOLVED_SECURITY_IDENTITY" in result["reasons"]


def test_dated_membership_symbol_is_not_used_as_price_store_key(owners):
    request, options, root, _ = owners
    (root / "baskets/ohlcv/RENAMED.parquet").write_bytes((root / "baskets/ohlcv/AAA.parquet").read_bytes())
    qualify_price_reader(options)
    rows = list(options["aliases"].rows)
    rows = [replace(row, vendor_symbol="RENAMED") if row.vendor == "store" and row.security_id == SIDS[0] else row for row in rows]
    options["aliases"] = VendorAliasTable(rows)
    old, seen = options["price_reader"], []
    def price(ticker):
        seen.append(ticker)
        return old(ticker)
    options["price_reader"] = price
    result = module().build_from_owners(request, **options)
    assert "RENAMED" in seen and "AAA" not in seen
    assert result["read"]["status"] == "READY"


def test_binding_preserves_owner_bytes_and_makes_no_network_calls(owners, monkeypatch):
    request, options, root, _ = owners
    import socket
    before = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}
    def refused(*args, **kwargs):
        raise AssertionError("owner adapter attempted network")
    monkeypatch.setattr(socket, "socket", refused)
    module().build_from_owners(request, **options)
    after = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}
    assert before == after


def test_price_index_duplicates_are_not_silently_averaged(owners):
    request, options, _, _ = owners
    old = options["price_reader"]
    def broken(ticker):
        result = old(ticker)
        result.series = pd.concat([result.series, result.series.iloc[-1:]])
        return result
    options["price_reader"] = broken
    with pytest.raises(ValueError, match="duplicate"):
        module().build_from_owners(request, **options)


def test_native_calendar_rejects_omitted_holidays_and_resolves_early_close():
    cal = module().owner_calendar("2026-11-25", "2026-11-30", code_ref="fixture:code")
    assert [row["date"] for row in cal["sessions"]] == ["2026-11-25", "2026-11-27", "2026-11-30"]
    assert cal["sessions"][1]["close_at"] == "2026-11-27T18:00:00Z"
    assert cal["rebalance_dates"] == ["2026-11-25"]


def test_alias_clock_is_not_filled_with_current_read_time(owners):
    request, options, _, _ = owners
    qualify_price_reader(options)
    options["aliases"] = VendorAliasTable([replace(row, known_at=None) for row in options["aliases"].rows])
    result = module().build_from_owners(request, **options)
    assert result["read"]["status"] == "UNAVAILABLE"
    assert "IDENTITY_RECEIPT_UNAVAILABLE" in result["read"]["reasons"]

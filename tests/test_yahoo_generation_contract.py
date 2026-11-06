"""Private generation publication/read/binding over controlled real acquisition.

No provider requests, production writes or runtime transfer are performed.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
from io import BytesIO
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from collectors.yahoo import YahooAdapter
from engine import basket_index, inputs
from lib import config, market_session, store
from lib import yahoo_generation_contract as contract
from lib.yahoo_runtime_profile import (
    SECTOR_CLOSE_TICKERS, YahooRuntimeProfile, bind_snapshot, bound_snapshot_for,
)
from scripts import vps_live_orchestrator as publisher

NOW = datetime(2026, 11, 3, 23, tzinfo=timezone.utc)
PREPARED = NOW + timedelta(seconds=1)
PUBLISHED = NOW + timedelta(seconds=2)
REVISION = "a" * 40
SYMBOLS = SECTOR_CLOSE_TICKERS
MEMBERS = contract.YAHOO_GENERATION_MEMBERS


def _acquire(frames, *, order=SYMBOLS, priors=None, period="1mo"):
    adapter = YahooAdapter(yahoo_config={"batch_size": 20, "retries": 2,
        "backoff_base_s": 0, "upsert_basis_tol": .001})
    calls = []
    def download(batch, requested_period, *, request_settings):
        calls.append((tuple(batch), requested_period))
        return pd.concat({ticker: (frames[ticker] if requested_period == "max" else frames[ticker].iloc[-25:])
            .rename(columns={"close": "Adj Close", "close_price": "Close", "volume": "Volume"})
            for ticker in batch}, axis=1)
    adapter._download = download
    result = adapter.acquire_cycle_benchmarks(order, prior_frames=frames if priors is None else priors,
        evaluation_instant=NOW, period=period)
    assert result.accepted, result.failure_reasons
    return result, calls


@pytest.fixture(scope="module")
def acquired():
    dates = pd.bdate_range(end="2026-11-03", periods=1300)
    dates = dates[[market_session.is_session_date("US", day.date()) for day in dates]][-1100:]
    assert len(dates) == 1100
    frames = {ticker: pd.DataFrame({"close": 100 + n + np.arange(len(dates)) / 100,
        "close_price": 110 + n + np.arange(len(dates)) / 100,
        "volume": np.full(len(dates), 1000.0)}, index=dates) for n, ticker in enumerate(SYMBOLS)}
    result, calls = _acquire(frames)
    assert calls == [(SYMBOLS, "1mo")]
    raw = {ticker: contract.encode_history(frame, source_session="2026-11-03")
           for ticker, frame in frames.items()}
    prior = {"kind": "bootstrap", "source_ref": "fixture-quiesced-capture-v1", "content_id": None,
        "captured_at": (NOW - timedelta(seconds=1)).isoformat(),
        "domain": contract.YAHOO_GENERATION_DOMAIN, "source_revision": "b" * 40,
        "member_sha256": {ticker: hashlib.sha256(data).hexdigest() for ticker, data in raw.items()},
        "member_bytes": {ticker: len(data) for ticker, data in raw.items()}}
    return result, prior


@pytest.fixture(scope="module")
def original_encoded(acquired):
    acquisition, prior = acquired
    return contract.encode_yahoo_acquisition(acquisition, prior_identity=prior,
        prepared_at=PREPARED, source_revision=REVISION)


@pytest.fixture
def encoded(original_encoded):
    return contract.EncodedYahooInputs(dict(original_encoded.members),
        deepcopy(dict(original_encoded.input_identity)))


def _orchestrator(tmp_path, *, now=PUBLISHED):
    return publisher.Orchestrator(live_dir=tmp_path / "public/live",
        state_dir=tmp_path / "private/state", data_dir=tmp_path / "legacy-data", now=now)


def _publish(tmp_path, encoded, *, generation_id="input-g1", expected=None, now=PUBLISHED):
    owner = _orchestrator(tmp_path, now=now)
    result = owner.publish_yahoo_inputs(encoded, generation_id=generation_id,
        source_revision=REVISION, expected_current_content_id=expected)
    return owner, result


def _validate(encoded, *, published=PUBLISHED, now=PUBLISHED, require_current=False):
    return contract.validate_yahoo_bundle(member_bytes=encoded.members,
        input_identity=encoded.input_identity, published_at=published.isoformat(), now=now,
        source_revision=REVISION, computed_at=PREPARED.isoformat(), require_current=require_current)


def forbidden(*args, **kwargs):
    raise AssertionError("Ambient checkout/config/provider access reached")


def test_real_publisher_verified_reader_and_whole_calculation_binding(tmp_path, encoded, monkeypatch):
    owner, published = _publish(tmp_path, encoded)
    assert published.status == "published", published.detail
    root = owner.state_dir / "generations"
    verified = contract.read_verified_yahoo_cohort(generations_root=root, now=PUBLISHED)
    assert verified.snapshot.content_id == published.content_id
    assert verified.snapshot.published_at == PUBLISHED.isoformat()
    assert verified.cohort.source_session == "2026-11-03"
    assert set(verified.cohort.frames) == set(SYMBOLS)
    before = {str(path.relative_to(root)): (path.read_bytes(), path.stat().st_mtime_ns)
              for path in root.rglob("*") if path.is_file()}
    with monkeypatch.context() as scoped:
        scoped.setattr(config, "load", forbidden)
        scoped.setattr(config, "data_dir", forbidden)
        scoped.setattr(pd, "read_parquet", forbidden)
        scoped.setattr(YahooAdapter, "_download", forbidden)
        scoped.setattr(store, "_path", forbidden)
        with bind_snapshot(YahooRuntimeProfile(mode="shadow", declared=True), verified.cohort):
            tr, price = inputs._yahoo_close("SPY"), inputs._yahoo_close("SPY", basis="price")
            assert tr.attrs["price_basis"] == "tr" and price.attrs["price_basis"] == "price"
            assert np.allclose(price - tr, 10)
            candle = basket_index._load_member_ohlcv("SPY")
            assert candle is not None and candle["close"].iloc[-1] == tr.iloc[-1]
            tr.iloc[-1] = -999
            assert store.read("yahoo", "SPY")["close"].iloc[-1] > 0
    assert bound_snapshot_for(group="yahoo", symbol="SPY") is None
    assert {str(path.relative_to(root)): (path.read_bytes(), path.stat().st_mtime_ns)
            for path in root.rglob("*") if path.is_file()} == before
    assert not list(owner.state_dir.glob(".yahoo-input-*"))
    assert not owner.live_dir.exists() and not owner.data_dir.exists()


def test_stale_private_generation_remains_a_truthful_prior(tmp_path, encoded):
    owner, published = _publish(tmp_path, encoded)
    later = PUBLISHED + timedelta(days=3)
    verified = contract.read_verified_yahoo_cohort(generations_root=owner.state_dir / "generations", now=later)
    prior = verified.prior_identity(captured_at=later)
    assert verified.snapshot.published_at == PUBLISHED.isoformat()
    assert verified.cohort.source_session == "2026-11-03"
    assert prior["content_id"] == published.content_id and prior["source_ref"] == "input-g1"
    assert set(prior["member_sha256"]) == set(SYMBOLS)
    for ticker, name in zip(SYMBOLS, MEMBERS):
        assert prior["member_sha256"][ticker] == hashlib.sha256(encoded.members[name]).hexdigest()
        assert prior["member_bytes"][ticker] == len(encoded.members[name])
    with pytest.raises(contract.YahooGenerationContractError, match="source_not_current_target"):
        _validate(encoded, now=later, require_current=True)


def test_normal_publication_clock_is_sampled_after_orchestrator_construction(tmp_path, encoded, monkeypatch):
    clock = [NOW]
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return clock[0]
    monkeypatch.setattr(publisher, "datetime", Clock)
    owner = _orchestrator(tmp_path, now=None)
    assert owner.now == NOW
    clock[0] = PUBLISHED
    result = owner.publish_yahoo_inputs(encoded, generation_id="clock-g1",
        source_revision=REVISION, expected_current_content_id=None)
    assert result.status == "published", result.detail
    assert result.published_at == PUBLISHED.isoformat()


@pytest.mark.parametrize("published,now", [
    (NOW, PUBLISHED), (PUBLISHED, NOW),
    (PUBLISHED + timedelta(days=1), PUBLISHED + timedelta(days=1)),
])
def test_backdated_future_or_cross_target_publication_is_refused(encoded, published, now):
    with pytest.raises(contract.YahooGenerationContractError):
        _validate(encoded, published=published, now=now, require_current=True)


def test_retained_reuse_uses_original_metadata_and_never_refreshes_age(tmp_path, encoded):
    owner, first = _publish(tmp_path, encoded)
    original = (owner.state_dir / "generations" / contract.YAHOO_GENERATION_DOMAIN / "input-g1/manifest.json").read_bytes()
    _, reused = _publish(tmp_path, encoded, expected=first.content_id, now=PUBLISHED + timedelta(seconds=30))
    assert reused.status == "unchanged" and reused.published_at == first.published_at
    assert (owner.state_dir / "generations" / contract.YAHOO_GENERATION_DOMAIN / "input-g1/manifest.json").read_bytes() == original
    _, refused = _publish(tmp_path, encoded, expected=first.content_id, now=PUBLISHED + timedelta(days=2))
    assert refused.status == "rejected"
    assert contract.read_verified_yahoo_cohort(generations_root=owner.state_dir / "generations",
        now=PUBLISHED + timedelta(days=2)).snapshot.content_id == first.content_id


@pytest.mark.parametrize("field,value", [("computed_at", "2026-11-03T23:30:00+00:00"),
                                         ("source_revision", "b" * 40)])
def test_factory_request_metadata_cannot_change_during_admission(tmp_path, encoded, field, value):
    sources = {}
    for name, raw in encoded.members.items():
        path = tmp_path / "source" / name
        path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw); sources[name] = path
    request = contract.prepare_yahoo_generation_request(sources=sources,
        input_identity=encoded.input_identity, generation_id="metadata-g1", source_revision=REVISION, lane="snapshot")
    request = replace(request, **{field: value})
    result = _orchestrator(tmp_path).publish_generation(request, expected_current_content_id=None)
    assert result.status == "rejected" and "yahoo_identity_changed" in result.detail


@pytest.mark.parametrize("change,code", [
    (lambda x: x["acquisition"].update(accepted=1), "invalid_acquisition_evidence"),
    (lambda x: x["acquisition"].update(returned=list(reversed(SYMBOLS))), "invalid_acquisition_evidence"),
    (lambda x: x["acquisition"].update(notes=["unqualified"]), "invalid_acquisition_evidence"),
    (lambda x: x["acquisition"].update(unexpected=1), "invalid_acquisition_evidence"),
    (lambda x: x["clocks"]["known"].update(retries=True), "invalid_acquisition_policy"),
    (lambda x: x["clocks"]["known"].update(basis_tolerance=float("inf")), "invalid_acquisition_policy"),
    (lambda x: x["clocks"]["known"].update(extra="hidden"), "invalid_acquisition_clock"),
    (lambda x: x["clocks"]["unknown"].update(provider_available_at="known now"), "invalid_acquisition_clock"),
    (lambda x: x["prior"]["member_sha256"].update(SPY=None), "invalid_prior_identity"),
    (lambda x: x["prior"]["member_bytes"].update(SPY=True), "invalid_prior_identity"),
    (lambda x: x["members"]["SPY"]["lineage"].update(rows=True), "history_lineage_mismatch"),
    (lambda x: x["members"]["SPY"]["lineage"].update(extra="hidden"), "invalid_yahoo_lineage"),
    (lambda x: x["members"]["SPY"]["lineage"].update(vendor_symbol="QQQ", alias_applied=True), "invalid_yahoo_lineage"),
    (lambda x: x["members"]["SPY"]["lineage"].update(prior="absent"), "prior_identity_mismatch"),
    (lambda x: x["members"]["SPY"]["lineage"].update(basis_comparison={"close": "shifted", "close_price": "aligned"}), "unqualified_window_merge"),
    (lambda x: x["members"]["SPY"].update(sha256="0" * 64), "member_identity_mismatch"),
])
def test_closed_evidence_rejects_contradictions(encoded, change, code):
    change(encoded.input_identity["yahoo_cohort"])
    with pytest.raises(contract.YahooGenerationContractError, match=f"^{code}$"):
        _validate(encoded)


def test_actual_max_recovery_retains_shifted_basis_evidence(acquired):
    acquisition, prior = acquired
    corrected = {ticker: frame.copy(deep=True) for ticker, frame in acquisition.frames.items()}
    corrected["SPY"]["close"] *= 1.02
    recovered, calls = _acquire(corrected, priors=acquisition.frames)
    assert calls[-1] == (("SPY",), "max")
    assert recovered.lineage["SPY"]["basis_comparison"]["close"] == "shifted"
    encoded = contract.encode_yahoo_acquisition(recovered, prior_identity=prior,
        prepared_at=PREPARED, source_revision=REVISION)
    decoded = _validate(encoded)
    np.testing.assert_array_equal(decoded["SPY"]["close"], corrected["SPY"]["close"])


def test_request_order_is_evidence_not_an_artifact_order_constraint(acquired):
    acquisition, prior = acquired
    reversed_acquisition, _ = _acquire(acquisition.frames, order=tuple(reversed(SYMBOLS)))
    encoded = contract.encode_yahoo_acquisition(reversed_acquisition, prior_identity=prior,
        prepared_at=PREPARED, source_revision=REVISION)
    assert encoded.input_identity["yahoo_cohort"]["acquisition"]["requested"] == list(reversed(SYMBOLS))
    assert tuple(encoded.members) == MEMBERS


def test_partial_or_failed_acquisition_cannot_create_inputs(acquired):
    acquisition, prior = acquired
    for invalid in (replace(acquisition, accepted=False), replace(acquisition, frames={}),
                    replace(acquisition, failed=("SPY",))):
        with pytest.raises(contract.YahooGenerationContractError, match="acquisition_not_accepted"):
            contract.encode_yahoo_acquisition(invalid, prior_identity=prior,
                prepared_at=PREPARED, source_revision=REVISION)


def test_optional_volume_and_null_observations_survive_without_zero_fill(acquired):
    frame = acquired[0].frames["SPY"].copy(deep=True)
    frame.loc[frame.index[0], "volume"] = np.nan
    raw = contract.encode_history(frame, source_session="2026-11-03")
    read = contract.decode_history(raw, source_session="2026-11-03")
    assert pd.isna(read["volume"].iloc[0]) and read["volume"].iloc[1] == 1000
    raw = contract.encode_history(frame.drop(columns="volume"), source_session="2026-11-03")
    assert "volume" not in contract.decode_history(raw, source_session="2026-11-03")


@pytest.mark.parametrize("kind", ["extra", "object", "infinite_volume", "negative_volume", "too_many_rows"])
def test_encoding_refuses_unbounded_or_nonprimitive_extra_history(acquired, kind):
    frame = acquired[0].frames["SPY"].copy(deep=True)
    if kind == "extra": frame["private_object"] = 1
    elif kind == "object": frame["volume"] = "not numeric"
    elif kind == "infinite_volume": frame.loc[frame.index[0], "volume"] = float("inf")
    elif kind == "negative_volume": frame.loc[frame.index[0], "volume"] = -1
    else:
        # Encoder bounds are independently checked before serializing the frame.
        with pytest.MonkeyPatch.context() as m:
            m.setattr(contract, "MAX_HISTORY_ROWS", 1000)
            with pytest.raises(contract.YahooGenerationContractError, match="history_shape_invalid"):
                contract.encode_history(frame, source_session="2026-11-03")
        return
    with pytest.raises(contract.YahooGenerationContractError):
        contract.encode_history(frame, source_session="2026-11-03")


def test_noncanonical_parquet_metadata_and_nested_payloads_are_refused(acquired):
    frame = acquired[0].frames["SPY"]
    for table in (pa.Table.from_pandas(frame),
                  pa.table({"session": frame.index.to_numpy(), "close": [[1.0]] * len(frame),
                            "close_price": [110.0] * len(frame)})):
        output = BytesIO(); pq.write_table(table, output)
        with pytest.raises(contract.YahooGenerationContractError):
            contract.decode_history(output.getvalue(), source_session="2026-11-03")


def test_declared_decoded_size_and_footer_are_bounded_before_read(encoded, monkeypatch):
    raw = encoded.members[MEMBERS[0]]
    with monkeypatch.context() as m:
        m.setattr(contract, "MAX_HISTORY_ROWS", 1000)
        with pytest.raises(contract.YahooGenerationContractError, match="history_shape_invalid"):
            contract.decode_history(raw, source_session="2026-11-03")
    with monkeypatch.context() as m:
        m.setattr(contract, "MAX_PARQUET_DECODE_BYTES", 1)
        with pytest.raises(contract.YahooGenerationContractError, match="history_decode_bound"):
            contract.decode_history(raw, source_session="2026-11-03")
    forged = raw[:-8] + (contract.MAX_PARQUET_FOOTER_BYTES + 1).to_bytes(4, "little") + b"PAR1"
    with pytest.raises(contract.YahooGenerationContractError, match="history_footer_invalid"):
        contract.decode_history(forged, source_session="2026-11-03")


def test_invalid_member_never_replaces_previous_selection(tmp_path, encoded):
    owner, first = _publish(tmp_path, encoded)
    pointer = owner.state_dir / "generations" / contract.YAHOO_GENERATION_DOMAIN / "current.json"
    before = pointer.read_bytes()
    encoded.members[MEMBERS[0]] = b"corrupted"
    _, rejected = _publish(tmp_path, encoded, generation_id="input-g2", expected=first.content_id)
    assert rejected.status == "rejected" and pointer.read_bytes() == before
    assert not (pointer.parent / "input-g2").exists()


def test_read_is_one_verified_snapshot_even_when_selection_changes(tmp_path, encoded, acquired):
    owner, first = _publish(tmp_path, encoded)
    corrected = {ticker: frame.copy(deep=True) for ticker, frame in acquired[0].frames.items()}
    corrected["SPY"]["close"] *= 1.02
    acquisition, _ = _acquire(corrected, priors=acquired[0].frames)
    replacement = contract.encode_yahoo_acquisition(acquisition, prior_identity=acquired[1],
        prepared_at=PREPARED, source_revision=REVISION)
    calls = []
    def capture_then_move(**kwargs):
        calls.append(kwargs)
        captured = publisher.read_selected_generation(**kwargs)
        second = owner.publish_yahoo_inputs(replacement, generation_id="input-g2",
            source_revision=REVISION, expected_current_content_id=first.content_id)
        assert second.status == "published", second.detail
        return captured
    captured = contract.read_verified_yahoo_cohort(generations_root=owner.state_dir / "generations",
        now=PUBLISHED, snapshot_reader=capture_then_move)
    latest = contract.read_verified_yahoo_cohort(generations_root=owner.state_dir / "generations", now=PUBLISHED)
    assert len(calls) == 1 and captured.cohort.generation_id == "input-g1"
    assert latest.cohort.generation_id == "input-g2"
    assert latest.cohort.frames["SPY"]["close"].iloc[-1] != captured.cohort.frames["SPY"]["close"].iloc[-1]


def test_corruption_is_unavailable_and_absence_creates_nothing(tmp_path, encoded):
    absent = tmp_path / "missing-generations"
    with pytest.raises(publisher.SelectedGenerationUnavailable):
        contract.read_verified_yahoo_cohort(generations_root=absent, now=PUBLISHED)
    assert not absent.exists()
    owner, _ = _publish(tmp_path, encoded)
    member = owner.state_dir / "generations" / contract.YAHOO_GENERATION_DOMAIN / "input-g1" / MEMBERS[0]
    member.write_bytes(b"corrupt")
    with pytest.raises(publisher.SelectedGenerationUnavailable):
        contract.read_verified_yahoo_cohort(generations_root=owner.state_dir / "generations", now=PUBLISHED)


@pytest.mark.parametrize("location", ["checkout", "served", "symlink", "relative"])
def test_private_staging_refuses_source_public_symlink_and_relative_roots(tmp_path, encoded, location, monkeypatch):
    root = tmp_path / "checkout"
    monkeypatch.setattr(publisher, "ROOT", root)
    owner = _orchestrator(tmp_path)
    if location == "checkout": owner.state_dir = root / "state"
    elif location == "served": owner.state_dir = tmp_path / "public/state"
    elif location == "relative": owner.state_dir = Path("relative")
    else:
        target = tmp_path / "elsewhere"; target.mkdir()
        owner.state_dir = tmp_path / "linked"; owner.state_dir.symlink_to(target, target_is_directory=True)
    with pytest.raises(contract.YahooGenerationContractError):
        owner.publish_yahoo_inputs(encoded, generation_id="unsafe-g1", source_revision=REVISION,
            expected_current_content_id=None)


def test_explicit_absent_bootstrap_requires_actual_max_recovery(acquired):
    acquisition, prior = acquired
    bootstrap = deepcopy(prior)
    bootstrap["member_sha256"] = {ticker: None for ticker in SYMBOLS}
    bootstrap["member_bytes"] = {ticker: None for ticker in SYMBOLS}
    recovered, calls = _acquire(acquisition.frames, priors={ticker: None for ticker in SYMBOLS})
    assert calls == [(SYMBOLS, "1mo"), (SYMBOLS, "max")]
    encoded = contract.encode_yahoo_acquisition(recovered, prior_identity=bootstrap,
        prepared_at=PREPARED, source_revision=REVISION)
    assert all(row["lineage"]["prior"] == "absent"
               for row in encoded.input_identity["yahoo_cohort"]["members"].values())
    assert set(_validate(encoded)) == set(SYMBOLS)


def test_full_history_request_uses_empty_basis_comparison(acquired):
    acquisition, prior = acquired
    recovered, calls = _acquire(acquisition.frames, period="max")
    assert calls == [(SYMBOLS, "max")]
    encoded = contract.encode_yahoo_acquisition(recovered, prior_identity=prior,
        prepared_at=PREPARED, source_revision=REVISION)
    assert all(row["lineage"]["basis_comparison"] == {}
               for row in encoded.input_identity["yahoo_cohort"]["members"].values())
    assert set(_validate(encoded)) == set(SYMBOLS)


def test_retained_computation_clock_tamper_refuses_read_and_reuse(tmp_path, encoded):
    owner, first = _publish(tmp_path, encoded)
    domain = owner.state_dir / "generations" / contract.YAHOO_GENERATION_DOMAIN
    path = domain / "input-g1/manifest.json"
    manifest = json.loads(path.read_bytes())
    manifest["computed_at"] = "2026-11-03T23:00:00+00:00"
    path.write_text(json.dumps(manifest))
    pointer = (domain / "current.json").read_bytes()
    with pytest.raises(contract.YahooGenerationContractError, match="invalid_yahoo_identity"):
        contract.read_verified_yahoo_cohort(generations_root=owner.state_dir / "generations", now=PUBLISHED)
    _, refused = _publish(tmp_path, encoded, expected=first.content_id)
    assert refused.status == "rejected" and "yahoo_identity_changed" in refused.detail
    assert (domain / "current.json").read_bytes() == pointer


def test_throwing_calculation_restores_snapshot_context(tmp_path, encoded):
    owner, _ = _publish(tmp_path, encoded)
    verified = contract.read_verified_yahoo_cohort(generations_root=owner.state_dir / "generations", now=PUBLISHED)
    with pytest.raises(RuntimeError, match="calculation failed"):
        with bind_snapshot(YahooRuntimeProfile(mode="shadow"), verified.cohort):
            assert bound_snapshot_for(group="yahoo", symbol="SPY") is not None
            raise RuntimeError("calculation failed")
    assert bound_snapshot_for(group="yahoo", symbol="SPY") is None


@pytest.mark.parametrize("generation_id", ["input@g1", "input:g1"])
def test_private_publisher_identity_round_trips_into_next_acquisition(tmp_path, encoded, acquired, generation_id):
    owner, published = _publish(tmp_path, encoded, generation_id=generation_id)
    assert published.status == "published", published.detail
    verified = contract.read_verified_yahoo_cohort(generations_root=owner.state_dir / "generations", now=PUBLISHED)
    prior = verified.prior_identity(captured_at=PUBLISHED)
    assert prior["source_ref"] == generation_id
    acquisition = acquired[0]
    clocks = deepcopy(dict(acquisition.clocks))
    clocks["known"]["evaluation_instant"] = (PUBLISHED + timedelta(seconds=1)).isoformat()
    next_inputs = contract.encode_yahoo_acquisition(replace(acquisition, clocks=clocks),
        prior_identity=prior, prepared_at=PUBLISHED + timedelta(seconds=2), source_revision=REVISION)
    assert next_inputs.input_identity["yahoo_cohort"]["prior"]["content_id"] == published.content_id


@pytest.mark.parametrize("kind", ["extra", "oversized", "mutable_bytes", "bad_identity", "bad_id"])
def test_invalid_prepared_inputs_are_rejected_before_staging_effects(tmp_path, encoded, kind):
    owner = _orchestrator(tmp_path)
    generation_id = "guard-g1"
    if kind == "extra": encoded.members["extra.parquet"] = b"extra"
    elif kind == "oversized": encoded.members[MEMBERS[0]] = b"x" * (contract.MAX_YAHOO_MEMBER_BYTES + 1)
    elif kind == "mutable_bytes": encoded.members[MEMBERS[0]] = bytearray(encoded.members[MEMBERS[0]])
    elif kind == "bad_identity": encoded.input_identity["yahoo_cohort"]["source_session"] = "not-a-date"
    else: generation_id = "trailing-newline\n"
    with pytest.raises(contract.YahooGenerationContractError):
        owner.publish_yahoo_inputs(encoded, generation_id=generation_id,
            source_revision=REVISION, expected_current_content_id=None)
    assert not owner.state_dir.exists()

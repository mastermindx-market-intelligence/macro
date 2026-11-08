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


# Producer qualification uses the actual acquisition and publisher over fixture
# bytes. Provider calls and legacy-file writes are never part of these tests.
def _legacy_bytes(frame, transform=None):
    copied = frame.copy(deep=True)
    copied.index.name = "Date"
    table = pa.Table.from_pandas(copied, preserve_index=True)
    table = table.set_column(table.schema.get_field_index("Date"), "Date",
        pa.array(copied.index.to_numpy(dtype="datetime64[ms]"), type=pa.timestamp("ms")))
    if transform is not None:
        table = transform(table)
    stream = BytesIO()
    pq.write_table(table, stream)
    return stream.getvalue()


def _bootstrap(acquired, *, absent=()):
    return contract.YahooBootstrapCapture(
        {ticker: None if ticker in absent else _legacy_bytes(frame)
         for ticker, frame in acquired[0].frames.items()},
        "fixture-capture@v1", "b" * 40, NOW - timedelta(seconds=1))


def _controlled_adapter(frames, calls, on_acquire=None):
    adapter = YahooAdapter(yahoo_config={"batch_size": 20, "retries": 2,
        "backoff_base_s": 0, "upsert_basis_tol": .001})
    def download(batch, requested_period, *, request_settings):
        calls.append(("download", tuple(batch), requested_period))
        return pd.concat({ticker: (frames[ticker] if requested_period == "max" else frames[ticker].iloc[-25:])
            .rename(columns={"close": "Adj Close", "close_price": "Close", "volume": "Volume"})
            for ticker in batch}, axis=1)
    adapter._download = download
    original = adapter.acquire_cycle_benchmarks
    def acquire(*args, **kwargs):
        calls.append(("acquire", kwargs))
        if on_acquire is not None:
            on_acquire(kwargs)
        return original(*args, **kwargs)
    adapter.acquire_cycle_benchmarks = acquire
    return adapter


def _clock(*values):
    iterator = iter(values)
    return lambda: next(iterator)


def test_bootstrap_primitive_decode_preserves_original_bytes_and_absence(acquired):
    capture = _bootstrap(acquired, absent=(SYMBOLS[-1],))
    frames, prior = contract.decode_bootstrap_capture(capture)
    for ticker in SYMBOLS[:-1]:
        pd.testing.assert_frame_equal(frames[ticker], acquired[0].frames[ticker],
            check_names=False, check_freq=False, check_index_type=False)
        assert prior["member_sha256"][ticker] == hashlib.sha256(capture.members[ticker]).hexdigest()
        assert prior["member_bytes"][ticker] == len(capture.members[ticker])
    assert frames[SYMBOLS[-1]] is None
    assert prior["member_sha256"][SYMBOLS[-1]] is prior["member_bytes"][SYMBOLS[-1]] is None
    assert prior["source_ref"] == capture.source_ref and prior["kind"] == "bootstrap"
    # The explicit bootstrap decoder does not relax canonical admission.
    with pytest.raises(contract.YahooGenerationContractError, match="history_shape_invalid"):
        contract.decode_history(capture.members["SPY"], source_session="2026-11-03")


def test_shallow_bootstrap_is_a_prior_but_not_a_verified_calculation(acquired):
    raw = _legacy_bytes(acquired[0].frames["SPY"].iloc[-3:])
    prior = contract.decode_legacy_bootstrap_history(raw)
    assert len(prior) == 3
    with pytest.raises(Exception, match="YAHOO_RUNTIME_HISTORY_INSUFFICIENT"):
        contract.encode_history(prior, source_session="2026-11-03")


@pytest.mark.parametrize("kind", ["metadata_absent", "range_index", "two_indices", "duplicate_metadata",
    "timezone", "nested", "bool", "extra", "reversed", "duplicate_date"])
def test_legacy_bootstrap_malformed_archive_is_not_repaired(acquired, kind):
    frame = acquired[0].frames["SPY"].copy()
    if kind == "reversed": frame = frame.iloc[::-1]
    if kind == "duplicate_date": frame.index = pd.DatetimeIndex([frame.index[0], *frame.index[:-1]])
    def transform(table):
        if kind == "metadata_absent": return table.replace_schema_metadata(None)
        if kind in {"range_index", "two_indices", "duplicate_metadata"}:
            metadata = dict(table.schema.metadata)
            pandas = json.loads(metadata[b"pandas"])
            if kind == "duplicate_metadata":
                metadata[b"pandas"] = b'{"index_columns":["Date"],"index_columns":["Date"]}'
            else:
                pandas["index_columns"] = [{"kind": "range", "start": 0, "stop": len(frame), "step": 1}] if kind == "range_index" else ["Date", "Date"]
                metadata[b"pandas"] = json.dumps(pandas).encode()
            return table.replace_schema_metadata(metadata)
        if kind == "timezone":
            return table.set_column(table.schema.get_field_index("Date"), "Date",
                pa.array(frame.index, type=pa.timestamp("ms", tz="UTC")))
        if kind in {"nested", "bool"}:
            values = [[1.0]] * len(frame) if kind == "nested" else [True] * len(frame)
            return table.set_column(table.schema.get_field_index("volume"), "volume", pa.array(values))
        if kind == "extra": return table.append_column("ignored", pa.array([1] * len(frame)))
        return table
    raw = _legacy_bytes(frame, transform)
    with pytest.raises(contract.YahooGenerationContractError):
        contract.decode_legacy_bootstrap_history(raw)


def test_legacy_bounds_apply_before_materialization(acquired, monkeypatch):
    raw = _legacy_bytes(acquired[0].frames["SPY"])
    monkeypatch.setattr(contract, "MAX_PARQUET_DECODE_BYTES", 1)
    with pytest.raises(contract.YahooGenerationContractError, match="history_decode_bound"):
        contract.decode_legacy_bootstrap_history(raw)


def test_capture_reads_each_explicit_file_once_and_retains_no_path(tmp_path, acquired, monkeypatch):
    owner = _orchestrator(tmp_path)
    raw = _bootstrap(acquired)
    paths = {}
    for ticker in SYMBOLS:
        path = tmp_path / (ticker + ".parquet")
        path.write_bytes(raw.members[ticker]); paths[ticker] = path
    original = publisher._read_source_bytes
    reads = []
    def read(path, *, limit):
        reads.append(path)
        return original(path, limit=limit)
    monkeypatch.setattr(publisher, "_read_source_bytes", read)
    capture = owner.capture_yahoo_bootstrap(sources=paths, source_ref=raw.source_ref,
        source_revision=raw.source_revision, clock=lambda: NOW)
    assert reads == list(paths.values()) and capture.captured_at == NOW
    assert dict(capture.members) == dict(raw.members)
    paths["SPY"].write_bytes(b"now corrupt")
    frames, prior = contract.decode_bootstrap_capture(capture)
    assert frames["SPY"].iloc[-1]["close"] > 0
    assert prior["member_sha256"]["SPY"] == hashlib.sha256(raw.members["SPY"]).hexdigest()
    assert not owner.state_dir.exists()


@pytest.mark.parametrize("kind", ["missing", "symlink", "corrupt", "relative", "missing_key"])
def test_bad_bootstrap_file_is_not_implicit_absence(tmp_path, acquired, kind):
    owner = _orchestrator(tmp_path)
    path = tmp_path / "source.parquet"
    path.write_bytes(_legacy_bytes(acquired[0].frames["SPY"]))
    paths = {ticker: path for ticker in SYMBOLS}
    if kind == "missing": paths["SPY"] = tmp_path / "absent.parquet"
    elif kind == "symlink":
        link = tmp_path / "linked.parquet"; link.symlink_to(path); paths["SPY"] = link
    elif kind == "corrupt": path.write_bytes(b"invalid")
    elif kind == "relative": paths["SPY"] = Path("relative.parquet")
    else: paths.pop("SPY")
    with pytest.raises((contract.YahooGenerationContractError, publisher.GenerationRejected)):
        owner.capture_yahoo_bootstrap(sources=paths, source_ref="capture", source_revision=REVISION)
    assert not owner.state_dir.exists()



def test_bootstrap_symlinked_ancestor_is_rejected_before_file_read(tmp_path, acquired, monkeypatch):
    owner = _orchestrator(tmp_path)
    target = tmp_path / "target"; target.mkdir()
    path = target / "SPY.parquet"; path.write_bytes(_legacy_bytes(acquired[0].frames["SPY"]))
    link = tmp_path / "alias"; link.symlink_to(target, target_is_directory=True)
    monkeypatch.setattr(publisher, "_read_source_bytes", forbidden)
    with pytest.raises(contract.YahooGenerationContractError, match="bootstrap_source_ancestor_symlink"):
        owner.capture_yahoo_bootstrap(sources={ticker: link / "SPY.parquet" for ticker in SYMBOLS},
            source_ref="capture", source_revision=REVISION)
    assert not owner.state_dir.exists()


def test_refresh_explicit_bootstrap_publishes_then_binds_one_process(tmp_path, acquired, monkeypatch):
    owner = _orchestrator(tmp_path)
    calls = []
    adapter = _controlled_adapter(acquired[0].frames, calls)
    result = owner.refresh_yahoo_inputs(adapter=adapter, generation_id="boot@g1", source_revision=REVISION,
        bootstrap=_bootstrap(acquired), clock=_clock(NOW, PREPARED))
    assert result.status == "published", result.detail
    assert [c[0] for c in calls] == ["acquire", "download"]
    assert calls[0][1]["evaluation_instant"] == NOW
    assert calls[0][1]["completed_sessions_only"] is True
    reader = contract.read_verified_yahoo_cohort
    reads = []
    def read(**kwargs):
        reads.append(kwargs)
        return reader(**kwargs)
    monkeypatch.setattr(contract, "read_verified_yahoo_cohort", read)
    with owner.yahoo_calculation_scope(profile=YahooRuntimeProfile(mode="shadow"),
                                       expected_content_id=result.content_id) as selected:
        assert selected.cohort.generation_id == "boot@g1"
        with monkeypatch.context() as scoped:
            scoped.setattr(store, "_path", forbidden)
            scoped.setattr(config, "load", forbidden)
            scoped.setattr(config, "data_dir", forbidden)
            pd.testing.assert_series_equal(inputs._yahoo_close("SPY"),
                selected.cohort.frames["SPY"]["close"], check_names=False, check_freq=False)
    assert len(reads) == 1
    assert bound_snapshot_for(group="yahoo", symbol="SPY") is None
    assert not owner.data_dir.exists() and not owner.live_dir.exists()


@pytest.mark.parametrize("kind", ["absent", "corrupt", "symlink", "unreadable"])
def test_refresh_never_implicitly_bootstraps_or_contacts_provider(tmp_path, acquired, monkeypatch, kind):
    owner = _orchestrator(tmp_path)
    domain = owner.state_dir / "generations" / contract.YAHOO_GENERATION_DOMAIN
    pointer = domain / "current.json"
    if kind != "absent":
        domain.mkdir(parents=True)
        if kind == "corrupt": pointer.write_bytes(b"invalid")
        elif kind == "symlink": pointer.symlink_to(tmp_path / "absent")
        else:
            original = publisher._read_json_state
            monkeypatch.setattr(publisher, "_read_json_state",
                lambda path: ("unreadable", None) if path == pointer else original(path))
    calls = []
    adapter = _controlled_adapter(acquired[0].frames, calls)
    with pytest.raises(publisher.SelectedGenerationUnavailable):
        owner.refresh_yahoo_inputs(adapter=adapter, generation_id="must-not-publish", source_revision=REVISION)
    assert not calls
    if kind == "absent": assert not owner.state_dir.exists()
    else:
        with pytest.raises(contract.YahooGenerationContractError, match="bootstrap_selection_not_absent"):
            owner.refresh_yahoo_inputs(adapter=adapter, generation_id="must-not-bootstrap", source_revision=REVISION,
                bootstrap=_bootstrap(acquired))
        assert not calls


def test_explicit_bootstrap_cannot_overwrite_established_generation(tmp_path, encoded, acquired):
    owner, published = _publish(tmp_path, encoded)
    calls = []
    with pytest.raises(contract.YahooGenerationContractError, match="bootstrap_selection_not_absent"):
        owner.refresh_yahoo_inputs(adapter=_controlled_adapter(acquired[0].frames, calls),
            generation_id="bad-bootstrap", source_revision=REVISION, bootstrap=_bootstrap(acquired))
    assert not calls
    selected = contract.read_verified_yahoo_cohort(generations_root=owner.state_dir / "generations", now=PUBLISHED)
    assert selected.snapshot.content_id == published.content_id


def test_old_verified_prior_advances_with_fresh_acquisition_clock(tmp_path, encoded, acquired):
    owner, first = _publish(tmp_path, encoded)
    later = NOW + timedelta(days=1)
    fresh = {}
    for ticker, frame in acquired[0].frames.items():
        last = frame.iloc[[-1]].copy(); last.index = pd.DatetimeIndex(["2026-11-04"])
        last["close"] += 1; last["close_price"] += 1
        fresh[ticker] = pd.concat([frame, last])
    calls = []
    # The constructor's task clock remains old. Publication has its independent
    # current clock override; acquisition receives fresh samples, never self.now.
    owner._publication_now = later + timedelta(seconds=5)
    assert owner.now == PUBLISHED
    result = owner.refresh_yahoo_inputs(adapter=_controlled_adapter(fresh, calls), generation_id="next-session",
        source_revision=REVISION, clock=_clock(later, later + timedelta(seconds=1),
            later + timedelta(seconds=2), later + timedelta(seconds=3)))
    assert result.status == "published", result.detail
    selected = contract.read_verified_yahoo_cohort(generations_root=owner.state_dir / "generations",
        now=owner._publication_now)
    evidence = selected.snapshot.manifest["input_identity"]["yahoo_cohort"]
    assert selected.cohort.source_session == "2026-11-04"
    assert evidence["prior"]["content_id"] == first.content_id
    assert evidence["prior"]["captured_at"] == (later + timedelta(seconds=1)).isoformat()
    assert evidence["clocks"]["known"]["evaluation_instant"] == (later + timedelta(seconds=2)).isoformat()
    assert evidence["prepared_at"] == (later + timedelta(seconds=3)).isoformat()
    assert len(selected.cohort.frames["SPY"]) == len(acquired[0].frames["SPY"]) + 1
    assert len([call for call in calls if call[0] == "acquire"]) == 1


@pytest.mark.parametrize("kind", ["provider_rejected", "clock_backwards", "session_boundary"])
def test_refresh_failure_preserves_prior_and_makes_no_publication(tmp_path, encoded, acquired, monkeypatch, kind):
    owner, _ = _publish(tmp_path, encoded)
    pointer = owner.state_dir / "generations" / contract.YAHOO_GENERATION_DOMAIN / "current.json"
    before = pointer.read_bytes()
    calls = []
    adapter = _controlled_adapter(acquired[0].frames, calls)
    monkeypatch.setattr(owner, "publish_yahoo_inputs", forbidden)
    if kind == "provider_rejected":
        adapter.acquire_cycle_benchmarks = lambda *a, **k: replace(acquired[0], accepted=False, reason="fixture failure")
        result = owner.refresh_yahoo_inputs(adapter=adapter, generation_id="rejected", source_revision=REVISION,
            clock=_clock(PUBLISHED, PUBLISHED, PUBLISHED, PUBLISHED))
        assert result.status == "rejected"
    elif kind == "clock_backwards":
        with pytest.raises(contract.YahooGenerationContractError, match="evaluation_before_prior_capture"):
            owner.refresh_yahoo_inputs(adapter=adapter, generation_id="backwards", source_revision=REVISION,
                clock=_clock(PUBLISHED, PUBLISHED, NOW))
        assert not calls
    else:
        with pytest.raises(contract.YahooGenerationContractError, match="source_not_completed_target"):
            owner.refresh_yahoo_inputs(adapter=adapter, generation_id="boundary", source_revision=REVISION,
                clock=_clock(PUBLISHED, PUBLISHED, PUBLISHED, PUBLISHED + timedelta(days=1)))
    assert pointer.read_bytes() == before


def test_uncertain_publication_result_is_returned_unchanged_once(tmp_path, acquired, monkeypatch):
    owner = _orchestrator(tmp_path)
    calls = []
    uncertain = publisher.GenerationPublishResult(status="uncertain", generation_id="candidate",
        detail="fixture pointer uncertainty", durability="unconfirmed")
    publications = []
    def publish(value, **kwargs):
        publications.append((value, kwargs)); return uncertain
    monkeypatch.setattr(owner, "publish_yahoo_inputs", publish)
    result = owner.refresh_yahoo_inputs(adapter=_controlled_adapter(acquired[0].frames, calls),
        generation_id="candidate", source_revision=REVISION, bootstrap=_bootstrap(acquired),
        clock=_clock(NOW, PREPARED))
    assert result is uncertain and len(publications) == 1
    assert publications[0][1]["expected_current_content_id"] is None
    assert len([call for call in calls if call[0] == "acquire"]) == 1
    assert not owner.state_dir.exists()



def test_concurrent_refresh_keeps_original_captured_prior_and_cas(tmp_path, encoded, acquired, monkeypatch):
    owner, first = _publish(tmp_path, encoded)
    root = owner.state_dir / "generations"
    original_read = contract.read_verified_yahoo_cohort
    reads = []
    def reader(**kwargs):
        reads.append(kwargs); return original_read(**kwargs)
    monkeypatch.setattr(contract, "read_verified_yahoo_cohort", reader)
    corrected = {ticker: frame.copy(deep=True) for ticker, frame in acquired[0].frames.items()}
    corrected["SPY"]["close"] *= 1.02
    second_acquisition, _ = _acquire(corrected, priors=acquired[0].frames)
    replacement = contract.encode_yahoo_acquisition(second_acquisition, prior_identity=acquired[1],
        prepared_at=PREPARED, source_revision=REVISION)
    owner._publication_now = PUBLISHED + timedelta(seconds=10)
    pointer = root / contract.YAHOO_GENERATION_DOMAIN / "current.json"
    second = {}
    def concurrent(kwargs):
        expected_prior = acquired[0].frames["SPY"].copy(deep=True)
        expected_prior.index = expected_prior.index.as_unit("ns")
        pd.testing.assert_frame_equal(kwargs["prior_frames"]["SPY"], expected_prior, check_freq=False)
        second["result"] = owner.publish_yahoo_inputs(replacement, generation_id="competing-g2",
            source_revision=REVISION, expected_current_content_id=first.content_id)
        assert second["result"].status == "published"
        second["pointer"] = pointer.read_bytes()
    calls = []
    original_publish = owner.publish_yahoo_inputs
    candidate = []
    def publish(value, **kwargs):
        if kwargs["generation_id"] == "stale-writer-g2": candidate.append((value, kwargs))
        return original_publish(value, **kwargs)
    monkeypatch.setattr(owner, "publish_yahoo_inputs", publish)
    result = owner.refresh_yahoo_inputs(adapter=_controlled_adapter(acquired[0].frames, calls, concurrent),
        generation_id="stale-writer-g2", source_revision=REVISION,
        clock=_clock(PUBLISHED, PUBLISHED + timedelta(seconds=1),
            PUBLISHED + timedelta(seconds=2), PUBLISHED + timedelta(seconds=3)))
    assert result.status == "rejected", result.detail
    assert len(reads) == len(candidate) == 1
    assert candidate[0][1]["expected_current_content_id"] == first.content_id
    prior = candidate[0][0].input_identity["yahoo_cohort"]["prior"]
    assert prior["content_id"] == first.content_id
    for ticker, name in zip(SYMBOLS, MEMBERS):
        assert prior["member_sha256"][ticker] == hashlib.sha256(encoded.members[name]).hexdigest()
        assert prior["member_bytes"][ticker] == len(encoded.members[name])
    assert len([call for call in calls if call[0] == "acquire"]) == 1
    assert pointer.read_bytes() == second["pointer"]
    latest = original_read(generations_root=root, now=owner._publication_now)
    assert latest.snapshot.content_id == second["result"].content_id
    assert latest.cohort.frames["SPY"]["close"].iloc[-1] == corrected["SPY"]["close"].iloc[-1]


def test_bootstrap_racing_first_publication_keeps_original_none_fence(tmp_path, encoded, acquired, monkeypatch):
    owner = _orchestrator(tmp_path)
    winner = {}
    def concurrent(kwargs):
        winner["result"] = owner.publish_yahoo_inputs(encoded, generation_id="winner",
            source_revision=REVISION, expected_current_content_id=None)
        assert winner["result"].status == "published"
        pointer = owner.state_dir / "generations" / contract.YAHOO_GENERATION_DOMAIN / "current.json"
        winner["pointer"] = pointer.read_bytes()
    calls = []
    publications = []
    original = owner.publish_yahoo_inputs
    def publish(value, **kwargs):
        publications.append(kwargs); return original(value, **kwargs)
    monkeypatch.setattr(owner, "publish_yahoo_inputs", publish)
    result = owner.refresh_yahoo_inputs(adapter=_controlled_adapter(acquired[0].frames, calls, concurrent),
        generation_id="losing-bootstrap", source_revision=REVISION, bootstrap=_bootstrap(acquired),
        clock=_clock(NOW, PREPARED))
    assert result.status == "rejected", result.detail
    assert [p["expected_current_content_id"] for p in publications] == [None, None]
    assert len([call for call in calls if call[0] == "acquire"]) == 1
    pointer = owner.state_dir / "generations" / contract.YAHOO_GENERATION_DOMAIN / "current.json"
    assert pointer.read_bytes() == winner["pointer"]


def test_calculation_scope_refuses_different_child_generation_and_restores_on_failure(tmp_path, encoded, monkeypatch):
    owner, first = _publish(tmp_path, encoded)
    profile = YahooRuntimeProfile(mode="shadow")
    ran = []
    with pytest.raises(contract.YahooGenerationContractError, match="yahoo_calculation_generation_changed"):
        with owner.yahoo_calculation_scope(profile=profile, expected_content_id="c" * 64):
            ran.append(True)
    assert not ran and bound_snapshot_for(group="yahoo", symbol="SPY") is None
    with pytest.raises(RuntimeError, match="fixture calculation"):
        with owner.yahoo_calculation_scope(profile=profile, expected_content_id=first.content_id):
            assert bound_snapshot_for(group="yahoo", symbol="SPY") is not None
            raise RuntimeError("fixture calculation")
    assert bound_snapshot_for(group="yahoo", symbol="SPY") is None
    monkeypatch.setattr(contract, "read_verified_yahoo_cohort", forbidden)
    for invalid in (None, "", "c" * 63, "c" * 64 + "\n"):
        with pytest.raises(contract.YahooGenerationContractError, match="expected_yahoo_content_id_required"):
            with owner.yahoo_calculation_scope(profile=profile, expected_content_id=invalid):
                ran.append(True)
    assert not ran


def test_refresh_invalid_private_destination_refuses_before_provider(tmp_path, acquired):
    owner = _orchestrator(tmp_path)
    owner.state_dir = Path("relative")
    calls = []
    with pytest.raises(contract.YahooGenerationContractError, match="absolute_private_root_required"):
        owner.refresh_yahoo_inputs(adapter=_controlled_adapter(acquired[0].frames, calls),
            generation_id="invalid", source_revision=REVISION, bootstrap=_bootstrap(acquired))
    assert not calls

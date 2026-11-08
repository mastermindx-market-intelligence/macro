"""Input qualification bridge — ``engine/systematic_inputs.py`` (Macro #10089).

Every fixture below is SYNTHETIC and labelled as such.  No captured market data
is copied into this file: the numbers are invented so the assertions pin the
*rule*, not the sample.  The one real thing this suite reads is the repository's
own dataset registry, because the qualification is defined against it.

The discriminating claims:

* a missing session is DETECTED against the shared published calendar, not
  compressed away by comparing counts;
* a newer receipt cannot authenticate a stale local file;
* a size, digest or mid-read mutation is refused, not warned about;
* a raw price jump is a SUSPECTED reason and never a split confirmation or a
  factor, and the ABSENCE of a jump is not evidence that there was no action;
* a PROPOSED action source stays held, and a qualified owner view qualifies only
  through the existing registry law — a caller cannot assert its way past it;
* unknown rights deny dependent use; ``null`` is not ``0``;
* the output is deterministic and reaches no network, account or ledger.

Run: python -m pytest tests/test_systematic_inputs.py -q
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from engine.systematic_inputs import (
    SCHEMA,
    CaptureError,
    CaptureManifest,
    CaptureObject,
    QualificationInputs,
    _discontinuity_observation,
    loads_strict,
    parse_manifest,
    qualify_systematic_inputs,
    read_object_bytes,
    resolve_capture_path,
)
from engine.systematic_inputs import Code
from lib.dataos.registry import DatasetContract, Registry, load_registry
from lib import us_cash_calendar as cal

REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_PRICE_DATASET = "equity.bars.daily.massive"
REAL_ACTION_DATASET = "reference.corporate_actions.massive_split_evidence"
UTC = timezone.utc
AS_OF = datetime(2026, 10, 22, 19, 5, 0, tzinfo=UTC)
RECEIVED_AT = datetime(2026, 10, 22, 19, 1, 23, tzinfo=UTC)
EXPECTED_SESSION = date(2026, 10, 21)


# ── Synthetic fixture builders (labelled; no real data) ─────────────────────

def synthetic_frame(sessions, closes=None, *, volume=None, high=None, low=None, open_=None):
    """A SYNTHETIC daily frame over calendar-verified session labels."""
    n = len(sessions)
    closes = list(closes) if closes is not None else [10.0] * n
    return pd.DataFrame(
        {
            "open": list(open_) if open_ is not None else list(closes),
            "high": list(high) if high is not None else [c + 0.5 for c in closes],
            "low": list(low) if low is not None else [c - 0.5 for c in closes],
            "close": closes,
            "volume": list(volume) if volume is not None else [1_000_000] * n,
        },
        index=pd.Index(pd.to_datetime(sessions), name="date"),
    )


def synthetic_manifest(objects, *, scope="existing_store_read_only", proven=False,
                       corporate_actions_qualified=False, proof=None, exclusions=()):
    """A SYNTHETIC receipt manifest mirroring the capture receipt's field shape."""
    return CaptureManifest(
        receipt_sha256="a" * 64,
        scope=scope,
        historical_original_availability_proven=proven,
        corporate_actions_qualified=corporate_actions_qualified,
        objects=tuple(objects),
        exclusions=tuple(exclusions),
        owner_availability_proof=proof,
    )


def synthetic_object(symbol="SYN", *, rows=None, last_session="2026-10-21",
                     first_session="2026-10-19", received_at=RECEIVED_AT,
                     object_key=None):
    return CaptureObject(
        object_key=object_key or f"massive_stock_day/{symbol}.csv",
        bytes=1,
        sha256="b" * 64,
        received_at=received_at,
        rows=rows,
        columns=("open", "high", "low", "close", "volume"),
        first_session=first_session,
        last_session=last_session,
    )


def real_registry():
    return load_registry(REPO_ROOT / "config" / "dataset_registry.yml")


def contract(**overrides):
    """A synthetic DatasetContract built through the real loader."""
    payload = {
        "dataset_id": "synthetic.price.bars",
        "layer": "L1",
        "owner": "test",
        "producer": "test",
        "storage": "test",
        "format": "csv",
        "grain": ["ticker", "date"],
        "temporal_profile": "BARS",
        "version": "1.0.0",
        "status": "PRODUCED",
        "basis": "sadj",
        "point_in_time_corporate_actions": True,
        "rights": {
            "purchase_access": "granted",
            "internal_computation": "granted",
            "redistribution": "granted",
            "evidence": {
                "purchase_access": "research/licenses/SYNTHETIC.md",
                "internal_computation": "research/licenses/SYNTHETIC.md",
                "redistribution": "research/licenses/SYNTHETIC.md",
            },
        },
    }
    payload.update(overrides)
    return DatasetContract.from_mapping(payload)


def qualified_owner_registry(*, status="PRODUCED"):
    """A registry whose action source is PRODUCED — the owner's qualified path.

    SYNTHETIC ids only.  It exists to prove the bridge reaches economics through
    the existing :func:`qualify_action_input` law rather than a local shortcut.
    """
    price = contract()
    action = contract(
        dataset_id="synthetic.actions.splits",
        layer="L0",
        format="json",
        grain=["id"],
        temporal_profile="SNAPSHOT_SERIES",
        basis="not_applicable",
        status=status,
        point_in_time_corporate_actions=None,
    )
    return Registry([price, action]), price, action


def confirmed_observation(dataset_id="synthetic.actions.splits"):
    return {
        "dataset_id": dataset_id,
        "endpoint": "synthetic://action-snapshot",
        "field_convention": "as_observed_split_ratio",
        "receipt": "synthetic-receipt-digest",
        "origin": "source_record",
        "response": "events",
        "rights_limited": False,
    }


def qualify(frames, universe, *, manifest=None, price_contract=None, registry=None,
            action_dataset_id=REAL_ACTION_DATASET, action_evidence=None,
            economic_evidence=None, expected_session=EXPECTED_SESSION, mode="current",
            volume_requires_positive=False, as_of=AS_OF):
    registry = registry or real_registry()
    price_contract = price_contract or registry.get(REAL_PRICE_DATASET)
    manifest = manifest or synthetic_manifest([synthetic_object()])
    return qualify_systematic_inputs(
        QualificationInputs(
            manifest=manifest,
            frames=frames,
            declared_universe=universe,
            as_of=as_of,
            expected_session=expected_session,
            price_contract=price_contract,
            action_dataset_id=action_dataset_id,
            action_evidence=action_evidence,
            economic_evidence=economic_evidence,
            registry=registry,
            mode=mode,
            volume_requires_positive=volume_requires_positive,
        )
    )


def instrument(document, symbol):
    return next(i for i in document["instruments"] if i["symbol"] == symbol)


# ── The contract as the live registry actually states it ───────────────────

class TestLiveRegistryContract:
    """Pins the facts the bridge depends on, read from the real registry."""

    def test_price_dataset_is_produced_raw_with_granted_rights(self):
        contract_row = real_registry().get(REAL_PRICE_DATASET)
        assert contract_row.status.value == "PRODUCED"
        assert contract_row.basis == "raw"
        assert contract_row.rights["internal_computation"] == "granted"
        # PIT corporate actions are NOT declared on this row (None, not False).
        assert contract_row.point_in_time_corporate_actions is None

    def test_action_dataset_is_proposed_and_declares_no_basis(self):
        contract_row = real_registry().get(REAL_ACTION_DATASET)
        assert contract_row.status.value == "PROPOSED"
        assert contract_row.basis not in ("raw", "sadj", "tradj")

    def test_raw_basis_is_unlawful_for_return_math_per_the_enum(self):
        from lib.dataos.price import AdjustmentBasis

        assert AdjustmentBasis.RAW.unlawful_for
        assert any("return math" in entry for entry in AdjustmentBasis.RAW.unlawful_for)


# ── Structural qualification ───────────────────────────────────────────────

class TestStructure:
    def test_clean_synthetic_frame_is_structurally_ready(self):
        sessions = ["2026-10-19", "2026-10-20", "2026-10-21"]
        doc = qualify({"SYN": synthetic_frame(sessions)}, ("SYN",))
        row = instrument(doc, "SYN")
        assert row["blockers"] == []
        assert row["structural_ready"] is True
        assert doc["current_data_ready"] is True

    def test_missing_session_is_detected_not_compressed(self):
        # 2026-08-18 is a real published session; dropping it from a range whose
        # endpoints are sessions is a gap, and counting alone would hide it.
        assert cal.is_session(date(2026, 8, 18))
        doc = qualify({"SYN": synthetic_frame(["2026-08-17", "2026-08-19"])}, ("SYN",),
                      expected_session=date(2026, 8, 19))
        row = instrument(doc, "SYN")
        assert Code.CALENDAR_GAP in row["blockers"]
        assert row["findings"]["missing_sessions"] == ["2026-08-18"]
        assert row["findings"]["expected_sessions_in_range"] == 3
        assert row["findings"]["present_sessions_in_range"] == 2
        assert row["structural_ready"] is False

    def test_holiday_span_is_not_reported_as_a_gap(self):
        # Independence Day 2026-07-03 is not a session, so spanning it is clean.
        assert not cal.is_session(date(2026, 7, 3))
        doc = qualify({"SYN": synthetic_frame(["2026-07-02", "2026-07-06"])}, ("SYN",),
                      expected_session=date(2026, 7, 6))
        assert Code.CALENDAR_GAP not in instrument(doc, "SYN")["blockers"]

    def test_duplicate_session_label_is_refused(self):
        sessions = ["2026-10-20", "2026-10-20", "2026-10-21"]
        doc = qualify({"SYN": synthetic_frame(sessions)}, ("SYN",))
        assert Code.SESSION_LABEL_DUPLICATE in instrument(doc, "SYN")["blockers"]

    def test_non_chronological_order_is_refused(self):
        sessions = ["2026-10-21", "2026-10-20"]
        doc = qualify({"SYN": synthetic_frame(sessions)}, ("SYN",))
        assert Code.SESSION_LABEL_NOT_CHRONOLOGICAL in instrument(doc, "SYN")["blockers"]

    def test_label_that_is_not_a_session_is_refused(self):
        assert not cal.is_session(date(2026, 7, 4))
        doc = qualify({"SYN": synthetic_frame(["2026-07-03", "2026-07-06"])}, ("SYN",),
                      expected_session=date(2026, 7, 6))
        assert Code.SESSION_LABEL_NOT_A_SESSION in instrument(doc, "SYN")["blockers"]

    def test_aware_datetime_index_is_refused_not_coerced(self):
        frame = synthetic_frame(["2026-10-19", "2026-10-20", "2026-10-21"])
        frame.index = pd.DatetimeIndex(frame.index, tz="UTC", name="date")
        doc = qualify({"SYN": frame}, ("SYN",))
        assert Code.SESSION_INDEX_IS_AWARE in instrument(doc, "SYN")["blockers"]

    @pytest.mark.parametrize(
        "kwargs,expected",
        [
            ({"closes": [float("nan"), 10.0, 10.0]}, Code.PRICE_NON_FINITE),
            ({"closes": [float("inf"), 10.0, 10.0]}, Code.PRICE_NON_FINITE),
            ({"closes": [-1.0, 10.0, 10.0]}, Code.PRICE_NOT_POSITIVE),
            ({"closes": [0.0, 10.0, 10.0]}, Code.PRICE_NOT_POSITIVE),
        ],
    )
    def test_price_must_be_finite_and_positive(self, kwargs, expected):
        closes = kwargs["closes"]
        frame = synthetic_frame(
            ["2026-10-19", "2026-10-20", "2026-10-21"], closes,
            open_=closes, high=[c + 0.5 for c in closes], low=[c - 0.5 for c in closes],
        )
        doc = qualify({"SYN": frame}, ("SYN",))
        assert expected in instrument(doc, "SYN")["blockers"]

    def test_low_high_inequality_is_refused(self):
        frame = synthetic_frame(
            ["2026-10-19", "2026-10-20", "2026-10-21"],
            closes=[10.0, 10.0, 10.0], high=[9.0, 11.0, 11.0],
        )
        doc = qualify({"SYN": frame}, ("SYN",))
        assert Code.PRICE_INEQUALITY_VIOLATION in instrument(doc, "SYN")["blockers"]

    def test_close_above_high_is_refused(self):
        frame = synthetic_frame(
            ["2026-10-19", "2026-10-20", "2026-10-21"],
            closes=[10.0, 10.0, 20.0], open_=[10.0, 10.0, 10.0],
        )
        doc = qualify({"SYN": frame}, ("SYN",))
        assert Code.PRICE_INEQUALITY_VIOLATION in instrument(doc, "SYN")["blockers"]


# ── null is not 0, and volume rules ────────────────────────────────────────

class TestVolume:
    def test_null_volume_is_reported_as_null_and_not_coerced_to_zero(self):
        frame = synthetic_frame(
            ["2026-10-19", "2026-10-20", "2026-10-21"], volume=[1_000_000, None, 1_000_000],
        )
        row = instrument(qualify({"SYN": frame}, ("SYN",)), "SYN")
        assert Code.VOLUME_NULL in row["blockers"]
        assert row["findings"]["price"]["null_volume_rows"] == 1

    def test_zero_volume_is_suspected_erased_missingness_only_when_required(self):
        frame = synthetic_frame(["2026-10-19", "2026-10-20", "2026-10-21"], volume=[1_000_000, 0, 1_000_000])
        lenient = instrument(qualify({"SYN": frame}, ("SYN",)), "SYN")
        assert Code.VOLUME_NULL not in lenient["blockers"]
        assert lenient["findings"]["price"]["zero_volume_sessions"] == 1
        strict = instrument(
            qualify({"SYN": frame}, ("SYN",), volume_requires_positive=True), "SYN"
        )
        assert Code.VOLUME_ZERO_SUSPECTED_MISSINGNESS in strict["blockers"]

    def test_negative_volume_is_refused(self):
        frame = synthetic_frame(["2026-10-19", "2026-10-20", "2026-10-21"], volume=[1000, -5, 1000])
        assert Code.VOLUME_NEGATIVE in instrument(qualify({"SYN": frame}, ("SYN",)), "SYN")["blockers"]

    def test_null_and_zero_are_distinguishable(self):
        base = ["2026-10-19", "2026-10-20", "2026-10-21"]
        nulls = instrument(
            qualify({"SYN": synthetic_frame(base, volume=[1000, None, 1000])}, ("SYN",)), "SYN"
        )["findings"]["price"]
        zeros = instrument(
            qualify({"SYN": synthetic_frame(base, volume=[1000, 0, 1000])}, ("SYN",)), "SYN"
        )["findings"]["price"]
        assert nulls["null_volume_rows"] == 1 and nulls["zero_volume_sessions"] == 0
        assert zeros["null_volume_rows"] == 0 and zeros["zero_volume_sessions"] == 1


# ── Freshness: a new receipt cannot authenticate stale bytes ───────────────

class TestFreshness:
    def test_newer_receipt_cannot_authenticate_a_stale_object(self):
        stale = synthetic_frame(["2026-07-01", "2026-07-02"])
        manifest = synthetic_manifest([
            synthetic_object(rows=2, first_session="2026-07-01", last_session="2026-10-21")
        ])
        doc = qualify({"SYN": stale}, ("SYN",), manifest=manifest)
        row = instrument(doc, "SYN")
        assert row["freshness"]["actual_last_session"] == "2026-07-02"
        assert row["freshness"]["manifest_last_session"] == "2026-10-21"
        assert row["freshness"]["manifest_claim_matches_actual"] is False
        assert Code.LAST_SESSION_STALE in row["blockers"]
        assert row["structural_ready"] is False
        assert doc["current_data_ready"] is False

    def test_fresh_object_at_the_expected_session_is_current(self):
        sessions = ["2026-10-19", "2026-10-20", "2026-10-21"]
        manifest = synthetic_manifest([synthetic_object()])
        doc = qualify({"SYN": synthetic_frame(sessions)}, ("SYN",), manifest=manifest)
        row = instrument(doc, "SYN")
        assert row["freshness"]["status"] == "fresh"
        assert row["freshness"]["manifest_claim_matches_actual"] is True
        assert doc["current_data_ready"] is True

    def test_object_older_than_expected_session_is_stale(self):
        sessions = ["2026-10-19", "2026-10-20"]
        doc = qualify({"SYN": synthetic_frame(sessions)}, ("SYN",),
                      expected_session=date(2026, 10, 21))
        assert Code.LAST_SESSION_STALE in instrument(doc, "SYN")["blockers"]

    def test_object_ahead_of_expected_session_is_refused(self):
        sessions = ["2026-10-20", "2026-10-22"]
        doc = qualify({"SYN": synthetic_frame(sessions)}, ("SYN",),
                      expected_session=date(2026, 10, 21))
        assert Code.LAST_SESSION_IN_FUTURE in instrument(doc, "SYN")["blockers"]

    def test_without_an_expected_session_freshness_is_not_evaluated(self):
        doc = qualify({"SYN": synthetic_frame(["2026-07-02"])}, ("SYN",), expected_session=None)
        row = instrument(doc, "SYN")
        assert row["freshness"]["blockers"] == [Code.EXPECTED_SESSION_NOT_SUPPLIED]
        assert doc["current_data_ready"] is False


class TestModes:
    def test_historical_reconstruction_is_never_marked_current(self):
        sessions = ["2026-07-01", "2026-07-02"]
        doc = qualify({"SYN": synthetic_frame(sessions)}, ("SYN",),
                      expected_session=date(2026, 7, 2), mode="historical_reconstruction")
        assert doc["requested_mode"] == "historical_reconstruction"
        assert doc["current_data_ready"] is False
        assert Code.MODE_HISTORICAL_NOT_CURRENT in doc["mode_blockers"]

    def test_mode_is_still_research_only_in_every_mode(self):
        for mode in ("current", "historical_reconstruction"):
            doc = qualify({"SYN": synthetic_frame(["2026-10-21"])}, ("SYN",), mode=mode)
            assert doc["mode"] == "RESEARCH_ONLY"
            assert doc["capital_eligible"] is False
            assert doc["live_orders_enabled"] is False


# ── Timestamps ─────────────────────────────────────────────────────────────

class TestTimestamps:
    def test_naive_received_at_is_refused_at_parse(self):
        raw = json.dumps(
            {"objects": [{
                "object_key": "massive_stock_day/SYN.csv", "bytes": 1, "sha256": "b" * 64,
                "received_at": "2026-10-22T19:01:23",
            }]}
        )
        with pytest.raises(CaptureError, match=Code.RECEIPT_TIMESTAMP_NAIVE):
            parse_manifest(raw)

    def test_naive_as_of_is_refused(self):
        with pytest.raises(CaptureError, match=Code.RECEIPT_TIMESTAMP_NAIVE):
            qualify({"SYN": synthetic_frame(["2026-10-21"])}, ("SYN",),
                    as_of=datetime(2026, 10, 22, 19, 5, 0))

    def test_received_after_as_of_is_blocked(self):
        future = datetime(2026, 10, 23, 9, 0, 0, tzinfo=UTC)
        manifest = synthetic_manifest([synthetic_object(received_at=future)])
        doc = qualify({"SYN": synthetic_frame(["2026-10-19", "2026-10-20", "2026-10-21"])},
                      ("SYN",), manifest=manifest)
        assert Code.RECEIPT_TIMESTAMP_AFTER_AS_OF in instrument(doc, "SYN")["blockers"]

    def test_missing_received_at_is_blocked(self):
        manifest = synthetic_manifest([synthetic_object(received_at=None)])
        doc = qualify({"SYN": synthetic_frame(["2026-10-19", "2026-10-20", "2026-10-21"])},
                      ("SYN",), manifest=manifest)
        assert Code.RECEIPT_TIMESTAMP_MISSING in instrument(doc, "SYN")["blockers"]

    def test_aware_received_at_at_or_before_as_of_is_accepted(self):
        assert RECEIVED_AT <= AS_OF
        manifest = synthetic_manifest([synthetic_object()])
        doc = qualify({"SYN": synthetic_frame(["2026-10-19", "2026-10-20", "2026-10-21"])},
                      ("SYN",), manifest=manifest)
        assert Code.RECEIPT_TIMESTAMP_AFTER_AS_OF not in instrument(doc, "SYN")["blockers"]


# ── Receipt parsing: strict, duplicate-safe, bounded ───────────────────────

class TestReceiptParsing:
    def test_malformed_json_is_refused(self):
        with pytest.raises(CaptureError, match=Code.RECEIPT_JSON_INVALID):
            parse_manifest('{"objects": [')

    def test_duplicate_top_level_key_is_refused(self):
        raw = '{"objects": [], "objects": []}'
        with pytest.raises(CaptureError, match=Code.RECEIPT_DUPLICATE_KEY):
            parse_manifest(raw)

    def test_duplicate_nested_key_is_refused(self):
        raw = '{"objects": [{"object_key": "massive_stock_day/A.csv", "bytes": 1, ' \
              '"bytes": 2, "sha256": "' + "b" * 64 + '"}]}'
        with pytest.raises(CaptureError, match=Code.RECEIPT_DUPLICATE_KEY):
            parse_manifest(raw)

    def test_nan_constant_is_refused(self):
        with pytest.raises(CaptureError, match=Code.RECEIPT_JSON_INVALID):
            loads_strict('{"bytes": NaN}')

    def test_infinity_constant_is_refused(self):
        with pytest.raises(CaptureError, match=Code.RECEIPT_JSON_INVALID):
            loads_strict('{"bytes": Infinity}')

    def test_non_object_root_is_refused(self):
        with pytest.raises(CaptureError, match=Code.RECEIPT_NOT_OBJECT):
            parse_manifest("[]")

    def test_duplicate_object_key_is_refused(self):
        entry = lambda: {  # noqa: E731
            "object_key": "massive_stock_day/SYN.csv", "bytes": 1, "sha256": "b" * 64,
        }
        with pytest.raises(CaptureError, match=Code.DUPLICATE_OBJECT_KEY):
            parse_manifest(json.dumps({"objects": [entry(), entry()]}))

    def test_malformed_digest_is_refused(self):
        raw = json.dumps({"objects": [{
            "object_key": "massive_stock_day/SYN.csv", "bytes": 1, "sha256": "nothex",
        }]})
        with pytest.raises(CaptureError, match=Code.RECEIPT_JSON_INVALID):
            parse_manifest(raw)

    def test_wrong_digest_length_is_refused(self):
        raw = json.dumps({"objects": [{
            "object_key": "massive_stock_day/SYN.csv", "bytes": 1, "sha256": "ab",
        }]})
        with pytest.raises(CaptureError, match=Code.RECEIPT_JSON_INVALID):
            parse_manifest(raw)

    def test_missing_objects_list_is_refused(self):
        with pytest.raises(CaptureError, match=Code.RECEIPT_JSON_INVALID):
            parse_manifest('{"scope": "existing_store_read_only"}')


# ── Object integrity and path safety ───────────────────────────────────────

class TestObjectIntegrity:
    def test_hash_mismatch_is_refused(self, tmp_path):
        path = tmp_path / "SYN.csv"
        path.write_text("date,open\n2026-10-21,1\n")
        with pytest.raises(CaptureError, match=Code.OBJECT_HASH_MISMATCH):
            read_object_bytes(path, expected_bytes=len(path.read_bytes()), expected_sha256="c" * 64)

    def test_size_mismatch_is_refused(self, tmp_path):
        path = tmp_path / "SYN.csv"
        payload = b"date,open\n2026-10-21,1\n"
        path.write_bytes(payload)
        with pytest.raises(CaptureError, match=Code.OBJECT_SIZE_MISMATCH):
            read_object_bytes(path, expected_bytes=len(payload) + 1, expected_sha256=hashlib.sha256(payload).hexdigest())

    def test_matching_size_and_hash_is_accepted(self, tmp_path):
        path = tmp_path / "SYN.csv"
        payload = b"date,open\n2026-10-21,1\n"
        path.write_bytes(payload)
        got = read_object_bytes(path, expected_bytes=len(payload),
                                expected_sha256=hashlib.sha256(payload).hexdigest())
        assert got == payload

    def test_size_bound_is_enforced(self, tmp_path):
        path = tmp_path / "SYN.csv"
        payload = b"x" * 32
        path.write_bytes(payload)
        with pytest.raises(CaptureError, match=Code.OBJECT_TOO_LARGE):
            read_object_bytes(path, expected_bytes=32, expected_sha256=hashlib.sha256(payload).hexdigest(),
                              max_bytes=16)

    def test_change_during_read_is_refused(self, tmp_path, monkeypatch):
        """The object must be one stable file across the whole observation."""
        path = tmp_path / "SYN.csv"
        payload = b"date,open\n2026-10-21,1\n"
        path.write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        original = Path.read_bytes

        def mutating(self):
            data = original(self)
            if self == path:
                self.write_bytes(data + b"appended,1\n")
            return data

        monkeypatch.setattr(Path, "read_bytes", mutating)
        with pytest.raises(CaptureError, match=Code.OBJECT_CHANGED_DURING_READ):
            read_object_bytes(path, expected_bytes=len(payload), expected_sha256=digest)


class TestPathSafety:
    @pytest.mark.parametrize("name", [
        "../outside.csv", "sub/evil.csv", "/etc/passwd", "..", "", "   ",
    ])
    def test_traversal_and_absolute_names_are_refused(self, tmp_path, name):
        with pytest.raises(CaptureError):
            resolve_capture_path(tmp_path, name)

    def test_symlink_escape_is_refused(self, tmp_path):
        root = tmp_path / "root"
        root.mkdir()
        outside = tmp_path / "outside.csv"
        outside.write_text("date,open\n2026-10-21,1\n")
        (root / "SYN.csv").symlink_to(outside)
        with pytest.raises(CaptureError, match=Code.PATH_SYMLINK):
            resolve_capture_path(root, "SYN.csv")

    def test_plain_basename_resolves_under_root(self, tmp_path):
        (tmp_path / "SYN.csv").write_text("date,open\n2026-10-21,1\n")
        assert resolve_capture_path(tmp_path, "SYN.csv").parent == tmp_path.resolve()

    def test_receipt_local_file_absolute_path_is_never_trusted(self, tmp_path):
        """A hostile local_file in the receipt cannot redirect the read.

        ``local_file`` is not part of the parsed manifest at all; the opened
        name comes only from the declared object's basename.
        """
        (tmp_path / "SYN.csv").write_text("date,open\n2026-10-21,1\n")
        hostile = json.dumps({
            "scope": "existing_store_read_only",
            "objects": [{
                "object_key": "massive_stock_day/SYN.csv",
                "local_file": "/etc/passwd",
                "bytes": 1, "sha256": "b" * 64,
                "received_at": "2026-10-22T19:01:23Z",
            }],
        })
        manifest = parse_manifest(hostile)
        assert not hasattr(manifest.objects[0], "local_file")
        assert manifest.objects[0].basename == "SYN.csv"
        resolved = resolve_capture_path(tmp_path, manifest.objects[0].basename)
        assert resolved == (tmp_path / "SYN.csv").resolve()

    def test_traversal_in_the_key_prefix_is_refused_at_the_source_check(self, tmp_path):
        """A key with ../ cannot escape (only its basename is opened) and is
        additionally refused because it is not under the declared prefix."""
        frame = synthetic_frame(["2026-10-19", "2026-10-20", "2026-10-21"])
        manifest = synthetic_manifest([
            synthetic_object(object_key="../../massive_stock_day/SYN.csv")
        ])
        doc = qualify({"SYN": frame}, ("SYN",), manifest=manifest)
        assert Code.SOURCE_KEY_PREFIX_MISMATCH in instrument(doc, "SYN")["blockers"]

    def test_missing_root_is_refused(self, tmp_path):
        with pytest.raises(CaptureError, match=Code.OBJECT_NOT_FOUND):
            resolve_capture_path(tmp_path / "absent", "SYN.csv")

    def test_missing_object_is_refused(self, tmp_path):
        with pytest.raises(CaptureError, match=Code.OBJECT_NOT_FOUND):
            resolve_capture_path(tmp_path, "absent.csv")


# ── The universe is never silently narrowed ────────────────────────────────

class TestUniverse:
    def test_a_missing_frame_blocks_that_instrument_without_dropping_it(self):
        good = synthetic_frame(["2026-10-19", "2026-10-20", "2026-10-21"])
        doc = qualify({"SYN": good}, ("SYN", "GONE"))
        assert [i["symbol"] for i in doc["instruments"]] == ["SYN", "GONE"]
        missing = instrument(doc, "GONE")
        assert missing["blockers"] == [Code.FRAME_NOT_SUPPLIED]
        assert missing["structural_ready"] is False
        assert doc["current_data_ready"] is False

    def test_excluded_symbol_is_retained_with_an_explicit_blocked_state(self):
        good = synthetic_frame(["2026-10-19", "2026-10-20", "2026-10-21"])
        manifest = synthetic_manifest(
            [synthetic_object()],
            exclusions=[{"object_key": "massive_stock_day/SYN.csv", "reason": "issuer delisting"}],
        )
        doc = qualify({"SYN": good}, ("SYN",), manifest=manifest)
        row = instrument(doc, "SYN")
        assert row["excluded"] is True
        assert row["exclusion_reason"] == "issuer delisting"
        assert Code.SYMBOL_EXCLUDED in row["blockers"]
        assert doc["capture"]["excluded_symbols"] == ["SYN"]

    def test_one_gapped_symbol_does_not_make_the_complete_ones_look_broken(self):
        # The honest shape: two complete symbols and one incomplete, all three
        # reported, global readiness false.
        sessions = ["2026-10-19", "2026-10-20", "2026-10-21"]
        manifest = synthetic_manifest(
            [synthetic_object("AAA"), synthetic_object("BBB"), synthetic_object("GAP")]
        )
        doc = qualify(
            {"AAA": synthetic_frame(sessions), "BBB": synthetic_frame(sessions),
             "GAP": synthetic_frame(["2026-08-17", "2026-08-19"])},
            ("AAA", "BBB", "GAP"), manifest=manifest, expected_session=date(2026, 10, 21),
        )
        assert instrument(doc, "AAA")["structural_ready"] is True
        assert instrument(doc, "BBB")["structural_ready"] is True
        assert instrument(doc, "GAP")["structural_ready"] is False
        assert doc["current_data_ready"] is False
        assert Code.CALENDAR_GAP in instrument(doc, "GAP")["blockers"]

    def test_declared_row_count_is_checked_against_the_decoded_frame(self):
        frame = synthetic_frame(["2026-10-19", "2026-10-20", "2026-10-21"])
        manifest = synthetic_manifest([synthetic_object(rows=3)])
        clean = qualify({"SYN": frame}, ("SYN",), manifest=manifest)
        assert instrument(clean, "SYN")["source"]["actual_rows"] == 3
        assert Code.OBJECT_ROWS_MISMATCH not in instrument(clean, "SYN")["blockers"]

        lying = synthetic_manifest([synthetic_object(rows=99)])
        caught = qualify({"SYN": frame}, ("SYN",), manifest=lying)
        row = instrument(caught, "SYN")
        assert Code.OBJECT_ROWS_MISMATCH in row["blockers"]
        assert row["source"]["actual_rows"] == 3
        assert row["structural_ready"] is False

    def test_suspected_action_is_reported_separately_from_structural_blockers(self):
        """A suspected jump is an ACTION finding, not a structural defect."""
        frame = synthetic_frame(["2025-12-04", "2025-12-05"], closes=[100.0, 50.0])
        manifest = synthetic_manifest([synthetic_object(rows=2, last_session="2025-12-05",
                                                       first_session="2025-12-04")])
        row = instrument(
            qualify({"SYN": frame}, ("SYN",), manifest=manifest,
                    expected_session=date(2025, 12, 5)), "SYN"
        )
        assert Code.SUSPECTED_ACTION_DISCONTINUITY in row["action_blockers"]
        assert row["blockers"] == []
        assert row["structural_ready"] is True

    def test_clean_instrument_has_no_action_blockers(self):
        row = instrument(qualify({"SYN": synthetic_frame(["2026-10-21"])}, ("SYN",)), "SYN")
        assert row["action_blockers"] == []

    def test_scope_other_than_read_only_is_reported(self):
        manifest = synthetic_manifest([synthetic_object()], scope="live_store_mutable")
        doc = qualify({"SYN": synthetic_frame(["2026-10-21"])}, ("SYN",), manifest=manifest)
        assert Code.RECEIPT_SCOPE_NOT_READ_ONLY in doc["source"]["blockers"]
        assert doc["current_data_ready"] is False


# ── Corporate actions: the existing law, never a shortcut ──────────────────

class TestCorporateActions:
    def test_raw_price_jump_is_suspected_and_never_a_factor(self):
        frame = synthetic_frame(["2026-10-20", "2026-10-21"], closes=[100.0, 50.0])
        doc = qualify({"SYN": frame}, ("SYN",))
        suspects = instrument(doc, "SYN")["findings"]["suspected_actions"]
        assert len(suspects) == 1
        assert suspects[0]["action_status"] == ActionInputStatus_SUSPECTED()
        assert suspects[0]["origin"] == "price_discontinuity"
        assert suspects[0]["factor_applied"] is False
        # The word SUSPECTED and its reason come from the existing gate.
        assert doc["actions"]["price_path_verdict"] == "SUSPECTED"
        assert doc["actions"]["price_path_reason"] == "DISCONTINUITY_INFERRED"
        assert doc["actions"]["factor_applied"] is False
        assert doc["economic_inputs_ready"] is False

    def test_a_split_that_lands_just_under_exactly_half_is_still_suspected(self):
        """Regression: a threshold sitting exactly at 0.50 misses a real 2:1.

        A 2:1 split prints as ~0.4999 of the prior close, not exactly 0.5000, so
        a ``>= 0.5`` default would step straight over the most common real
        event this check exists to catch.
        """
        from engine.systematic_inputs import DEFAULT_JUMP_FRACTION

        assert DEFAULT_JUMP_FRACTION < 0.5
        frame = synthetic_frame(["2025-12-04", "2025-12-05"], closes=[69.9504, 34.9998])
        row = instrument(qualify({"SYN": frame}, ("SYN",)), "SYN")
        suspects = row["findings"]["suspected_actions"]
        assert len(suspects) == 1
        assert suspects[0]["session"] == "2025-12-05"
        assert suspects[0]["action_status"] == "SUSPECTED"
        assert suspects[0]["factor_applied"] is False

    def test_ordinary_daily_moves_are_not_flagged(self):
        frame = synthetic_frame(
            ["2025-12-03", "2025-12-04", "2025-12-05"], closes=[70.0, 70.5, 69.8]
        )
        row = instrument(
            qualify({"SYN": frame}, ("SYN",), expected_session=date(2025, 12, 5)), "SYN"
        )
        assert row["findings"]["suspected_actions"] == []
        assert row["structural_ready"] is True

    def test_no_jump_still_does_not_qualify_economics(self):
        frame = synthetic_frame(["2026-10-20", "2026-10-21"], closes=[100.0, 100.5])
        doc = qualify({"SYN": frame}, ("SYN",))
        assert instrument(doc, "SYN")["findings"]["suspected_actions"] == []
        assert Code.ACTION_EVIDENCE_MISSING in doc["economics_blockers"]
        assert doc["economic_inputs_ready"] is False

    def test_discontinuity_observation_always_routes_to_suspected(self):
        registry, _, action = qualified_owner_registry()
        from lib.dataos.registry import qualify_action_input

        verdict = qualify_action_input(
            _discontinuity_observation(action.dataset_id), registry=registry
        )
        assert verdict.status.value == "SUSPECTED"
        assert verdict.reason == "DISCONTINUITY_INFERRED"

    def test_proposed_action_source_stays_held(self):
        """The live PROPOSED registry row cannot witness an event."""
        sessions = ["2026-10-19", "2026-10-20", "2026-10-21"]
        observation = confirmed_observation(REAL_ACTION_DATASET)
        doc = qualify({"SYN": synthetic_frame(sessions)}, ("SYN",), action_evidence=observation)
        assert doc["actions"]["evidence_verdict"] == "UNQUALIFIED"
        assert doc["actions"]["evidence_reason"] == "SOURCE_NOT_PRODUCED"
        assert Code.ACTION_SOURCE_NOT_PRODUCED in doc["economics_blockers"]
        assert doc["economic_inputs_ready"] is False

    def test_proposed_flag_in_the_receipt_alone_qualifies_nothing(self):
        manifest = synthetic_manifest([synthetic_object()], corporate_actions_qualified=True)
        doc = qualify({"SYN": synthetic_frame(["2026-10-21"])}, ("SYN",), manifest=manifest)
        assert doc["actions"]["manifest_corporate_actions_qualified"] is True
        assert doc["economic_inputs_ready"] is False

    def test_qualified_owner_view_reaches_economics_through_the_existing_law(self):
        registry, price, action = qualified_owner_registry(status="PRODUCED")
        doc = qualify(
            {"SYN": synthetic_frame(["2026-10-19", "2026-10-20", "2026-10-21"])},
            ("SYN",),
            registry=registry,
            price_contract=price,
            action_dataset_id=action.dataset_id,
            action_evidence=confirmed_observation(action.dataset_id),
            economic_evidence={"adjustment_basis": "sadj"},
        )
        assert doc["actions"]["evidence_verdict"] == "CONFIRMED"
        assert doc["actions"]["confirmed_event_source"] == action.dataset_id
        assert doc["economic_inputs_ready"] is True
        # Still research-only, never capital.
        assert doc["capital_eligible"] is False
        assert doc["live_orders_enabled"] is False

    def test_qualified_economics_still_cannot_be_marked_current_in_a_reconstruction(self):
        registry, price, action = qualified_owner_registry()
        doc = qualify(
            {"SYN": synthetic_frame(["2026-10-19", "2026-10-20", "2026-10-21"])},
            ("SYN",), registry=registry, price_contract=price,
            action_dataset_id=action.dataset_id,
            action_evidence=confirmed_observation(action.dataset_id),
            economic_evidence={"adjustment_basis": "sadj"},
            mode="historical_reconstruction",
        )
        assert doc["economic_inputs_ready"] is True
        assert doc["current_data_ready"] is False
        assert doc["allowed_use"] == "descriptive_reconstruction"

    def test_qualified_economics_in_current_mode_stay_inspect_only(self):
        registry, price, action = qualified_owner_registry()
        doc = qualify(
            {"SYN": synthetic_frame(["2026-10-19", "2026-10-20", "2026-10-21"])},
            ("SYN",), registry=registry, price_contract=price,
            action_dataset_id=action.dataset_id,
            action_evidence=confirmed_observation(action.dataset_id),
            economic_evidence={"adjustment_basis": "sadj"},
            mode="current",
        )
        assert doc["economic_inputs_ready"] is True
        assert doc["allowed_use"] == "inspect_only"

    def test_raw_basis_is_blocked_for_economics_on_the_real_contract(self):
        doc = qualify({"SYN": synthetic_frame(["2026-10-21"])}, ("SYN",))
        assert Code.BASIS_RAW_UNLAWFUL_FOR_ECONOMICS in doc["economics_blockers"]
        assert doc["source"]["basis_unlawful_for"]

    def test_declaring_raw_as_the_economic_basis_is_refused(self):
        registry, price, action = qualified_owner_registry()
        doc = qualify(
            {"SYN": synthetic_frame(["2026-10-19", "2026-10-20", "2026-10-21"])},
            ("SYN",), registry=registry, price_contract=price,
            action_dataset_id=action.dataset_id,
            action_evidence=confirmed_observation(action.dataset_id),
            economic_evidence={"adjustment_basis": "raw"},
        )
        assert Code.BASIS_RAW_UNLAWFUL_FOR_ECONOMICS in doc["economics_blockers"]
        assert doc["economic_inputs_ready"] is False

    def test_not_producing_price_source_blocks_everything(self):
        registry = Registry([contract(dataset_id="synthetic.price.bars", status="PROPOSED")])
        doc = qualify({"SYN": synthetic_frame(["2026-10-21"])}, ("SYN",),
                      registry=registry, price_contract=registry.get("synthetic.price.bars"))
        assert Code.SOURCE_NOT_PRODUCED in doc["economics_blockers"]

    def test_malformed_action_evidence_is_refused_not_coerced(self):
        doc = qualify({"SYN": synthetic_frame(["2026-10-21"])}, ("SYN",),
                      action_evidence={"dataset_id": "x", "origin": "not_a_real_origin",
                                       "endpoint": None, "field_convention": None,
                                       "receipt": None, "response": None,
                                       "rights_limited": False})
        assert Code.ACTION_EVIDENCE_MALFORMED in doc["economics_blockers"]
        assert doc["economic_inputs_ready"] is False

    def test_undeclared_basis_is_reported(self):
        registry = Registry([contract(basis="")])
        doc = qualify({"SYN": synthetic_frame(["2026-10-21"])}, ("SYN",),
                      registry=registry, price_contract=registry.get("synthetic.price.bars"))
        assert Code.BASIS_NOT_DECLARED in doc["source"]["blockers"]

    def test_pit_corporate_actions_not_declared_blocks_economics(self):
        registry, price, action = qualified_owner_registry()
        undeclared = contract(point_in_time_corporate_actions=None)
        registry = Registry([undeclared, action])
        doc = qualify(
            {"SYN": synthetic_frame(["2026-10-19", "2026-10-20", "2026-10-21"])},
            ("SYN",), registry=registry, price_contract=undeclared,
            action_dataset_id=action.dataset_id,
            action_evidence=confirmed_observation(action.dataset_id),
            economic_evidence={"adjustment_basis": "sadj"},
        )
        assert Code.PIT_CORPORATE_ACTIONS_NOT_DECLARED in doc["economics_blockers"]
        assert doc["economic_inputs_ready"] is False


# ── Rights ─────────────────────────────────────────────────────────────────

class TestRights:
    def test_undeclared_rights_deny_dependent_use(self):
        registry = Registry([contract(rights={})])
        doc = qualify({"SYN": synthetic_frame(["2026-10-21"])}, ("SYN",),
                      registry=registry, price_contract=registry.get("synthetic.price.bars"))
        assert Code.RIGHTS_UNDECLARED in doc["source"]["blockers"]
        assert Code.RIGHTS_UNDECLARED in doc["economics_blockers"]

    def test_unverified_right_does_not_grant_dependent_use(self):
        registry = Registry([contract(rights={"purchase_access": "unverified",
                                              "internal_computation": "unverified",
                                              "redistribution": "unverified"})])
        doc = qualify({"SYN": synthetic_frame(["2026-10-21"])}, ("SYN",),
                      registry=registry, price_contract=registry.get("synthetic.price.bars"))
        assert doc["economic_inputs_ready"] is False

    def test_explicit_denial_is_reported(self):
        registry = Registry([contract(rights={"purchase_access": "not_granted",
                                              "internal_computation": "not_granted",
                                              "redistribution": "not_granted"})])
        doc = qualify({"SYN": synthetic_frame(["2026-10-21"])}, ("SYN",),
                      registry=registry, price_contract=registry.get("synthetic.price.bars"))
        assert Code.RIGHTS_NOT_GRANTED in doc["economics_blockers"]

    def test_granted_right_with_unlawful_evidence_pointer_blocks_dependent_use(self):
        """R00.02: a label asserting its own grant is not evidence."""
        registry = Registry([contract(rights={
            "purchase_access": "granted", "internal_computation": "granted",
            "redistribution": "granted",
            "evidence": {"purchase_access": "https://example.invalid/licence",
                         "internal_computation": "research/licenses/SYNTHETIC.md",
                         "redistribution": "research/licenses/SYNTHETIC.md"},
        })])
        doc = qualify({"SYN": synthetic_frame(["2026-10-21"])}, ("SYN",),
                      registry=registry, price_contract=registry.get("synthetic.price.bars"))
        assert Code.RIGHTS_EVIDENCE_UNLAWFUL in doc["source"]["blockers"]
        assert doc["economic_inputs_ready"] is False

    def test_rights_are_independent_not_inferred(self):
        registry = Registry([contract(rights={
            "purchase_access": "granted", "internal_computation": "not_granted",
            "redistribution": "granted",
            "evidence": {"purchase_access": "research/licenses/SYNTHETIC.md",
                         "redistribution": "research/licenses/SYNTHETIC.md"},
        })])
        doc = qualify({"SYN": synthetic_frame(["2026-10-21"])}, ("SYN",),
                      registry=registry, price_contract=registry.get("synthetic.price.bars"))
        assert Code.RIGHTS_NOT_GRANTED in doc["economics_blockers"]
        assert doc["economic_inputs_ready"] is False


# ── Historical availability ────────────────────────────────────────────────

class TestHistoricalAvailability:
    def test_bare_caller_true_is_downgraded(self):
        manifest = synthetic_manifest([synthetic_object()], proven=True)
        doc = qualify({"SYN": synthetic_frame(["2026-10-21"])}, ("SYN",), manifest=manifest)
        assert doc["historical_original_availability_proven"] is False
        assert Code.HISTORICAL_AVAILABILITY_NOT_PROVEN in doc["source"]["blockers"]

    def test_qualification_does_not_flip_the_field_on_its_own(self):
        """Economic readiness must never imply historical knowability."""
        registry, price, action = qualified_owner_registry()
        doc = qualify(
            {"SYN": synthetic_frame(["2026-10-19", "2026-10-20", "2026-10-21"])},
            ("SYN",), registry=registry, price_contract=price,
            action_dataset_id=action.dataset_id,
            action_evidence=confirmed_observation(action.dataset_id),
            economic_evidence={"adjustment_basis": "sadj"},
        )
        assert doc["economic_inputs_ready"] is True
        assert doc["historical_original_availability_proven"] is False

    def test_default_sample_never_claims_provenance(self):
        doc = qualify({"SYN": synthetic_frame(["2026-10-21"])}, ("SYN",))
        assert doc["historical_original_availability_proven"] is False


# ── Output shape and determinism ───────────────────────────────────────────

class TestOutputDocument:
    def test_schema_and_mode_are_fixed(self):
        doc = qualify({"SYN": synthetic_frame(["2026-10-21"])}, ("SYN",))
        assert doc["schema"] == SCHEMA == "systematic_input_qualification.v1"
        assert doc["mode"] == "RESEARCH_ONLY"

    def test_current_and_economic_readiness_are_distinct_fields(self):
        doc = qualify({"SYN": synthetic_frame(["2026-10-21"])}, ("SYN",))
        assert doc["current_data_ready"] is True
        assert doc["economic_inputs_ready"] is False
        assert doc["current_data_ready"] is not doc["economic_inputs_ready"]

    def test_no_returns_or_recommendations_are_emitted(self):
        """Structural check: the document carries no advice-shaped key.

        Substring matching over the whole payload would trip on honest prose
        ("chronological order"), so the assertion is made on key names, which
        is where a recommendation would actually have to live.
        """
        doc = qualify({"SYN": synthetic_frame(["2026-10-20", "2026-10-21"], closes=[100.0, 50.0])},
                      ("SYN",))
        keys: set[str] = set()

        def walk(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    keys.add(key.lower())
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(doc)
        forbidden = {"recommendation", "recommendations", "expected_return", "sharpe",
                     "position_size", "orders", "signal", "target_price", "returns",
                     "forecast", "alpha", "weight"}
        assert not (keys & forbidden), sorted(keys & forbidden)

    def test_capital_and_live_flags_are_present_and_false(self):
        doc = qualify({"SYN": synthetic_frame(["2026-10-21"])}, ("SYN",))
        assert doc["capital_eligible"] is False
        assert doc["live_orders_enabled"] is False
        assert doc["allowed_use"] in {"inspect_only", "descriptive_reconstruction"}

    def test_reconstruction_limitation_is_stated(self):
        doc = qualify({"SYN": synthetic_frame(["2026-10-21"])}, ("SYN",))
        assert "not proof of what was knowable" in doc["reconstruction_note"]

    def test_output_is_strict_json_serialisable(self):
        doc = qualify({"SYN": synthetic_frame(["2026-10-20", "2026-10-21"], closes=[100.0, 50.0])},
                      ("SYN",))
        payload = json.dumps(doc, sort_keys=True, allow_nan=False, ensure_ascii=False)
        assert json.loads(payload)["schema"] == SCHEMA

    def test_two_runs_are_byte_identical(self):
        frame = synthetic_frame(["2026-10-19", "2026-10-20", "2026-10-21"])
        first = json.dumps(qualify({"SYN": frame}, ("SYN",)), sort_keys=True, default=str)
        second = json.dumps(qualify({"SYN": frame}, ("SYN",)), sort_keys=True, default=str)
        assert first == second

    def test_blocker_codes_are_sorted_and_stable(self):
        frame = synthetic_frame(["2026-08-17", "2026-08-19"])
        doc = qualify({"SYN": frame}, ("SYN",), expected_session=date(2026, 8, 19))
        blockers = instrument(doc, "SYN")["blockers"]
        assert blockers == sorted(blockers)
        assert blockers == sorted(set(blockers))


def ActionInputStatus_SUSPECTED():
    from lib.dataos.registry import ActionInputStatus

    return ActionInputStatus.SUSPECTED.value


# ── No network, account or ledger is reached ───────────────────────────────

class TestNoExternalEffect:
    FORBIDDEN_IMPORTS = (
        "socket", "requests", "urllib.request", "httpx", "aiohttp", "boto3",
        "botocore", "paramiko", "psycopg2", "sqlalchemy", "qledger", "ledger",
    )

    @pytest.mark.parametrize("module", ["engine/systematic_inputs.py",
                                        "scripts/qualify_systematic_inputs.py"])
    def test_module_imports_no_network_or_ledger_client(self, module):
        source = (REPO_ROOT / module).read_text(encoding="utf-8")
        for name in self.FORBIDDEN_IMPORTS:
            assert f"import {name}" not in source, f"{module} must not import {name}"

    def test_qualification_runs_with_sockets_disabled(self, monkeypatch):
        import socket

        def refuse(*args, **kwargs):
            raise AssertionError("qualification must not open a socket")

        monkeypatch.setattr(socket, "socket", refuse)
        monkeypatch.setattr(socket, "create_connection", refuse)
        doc = qualify({"SYN": synthetic_frame(["2026-10-19", "2026-10-20", "2026-10-21"])}, ("SYN",))
        assert doc["schema"] == SCHEMA


# ── The CLI: read-only capture in, one explicit document out ───────────────

def write_capture(root: Path, symbol: str, sessions, *, closes=None):
    """Write one SYNTHETIC object plus its true size and digest into *root*."""
    frame = synthetic_frame(sessions, closes).reset_index()
    path = root / f"{symbol}.csv"
    payload = frame.to_csv(index=False).encode("utf-8")
    path.write_bytes(payload)
    return path, len(payload), hashlib.sha256(payload).hexdigest(), len(frame)


def write_receipt(root: Path, entries, *, scope="existing_store_read_only", **extra):
    receipt = {"scope": scope, "objects": entries, **extra}
    payload = json.dumps(receipt).encode("utf-8")
    (root / "receipt.json").write_bytes(payload)
    return payload


def entry(symbol, size, digest, rows, *, last_session="2026-10-21", key=None):
    return {
        "object_key": key or f"massive_stock_day/{symbol}.csv",
        "bytes": size, "sha256": digest,
        "received_at": "2026-10-22T19:01:23.660073Z",
        "object_last_modified": "2026-10-22T19:01:25.406573Z",
        "rows": rows,
        "columns": ["date", "open", "high", "low", "close", "volume"],
        "first_session": "2026-10-19", "last_session": last_session,
        "timezone": "America/New_York",
    }


class TestCommandLine:
    """The CLI is the only thing that touches the filesystem."""

    def test_end_to_end_writes_one_explicit_document(self, tmp_path):
        from scripts.qualify_systematic_inputs import main

        capture = tmp_path / "capture"
        capture.mkdir()
        _, size, digest, rows = write_capture(
            capture, "SYN", ["2026-10-19", "2026-10-20", "2026-10-21"]
        )
        write_receipt(capture, [entry("SYN", size, digest, rows)])
        out = tmp_path / "qualification.json"
        code = main([
            "--capture-root", str(capture), "--output", str(out),
            "--as-of", "2026-10-22T19:05:00Z", "--expected-session", "2026-10-21",
        ])
        assert code == 0
        document = json.loads(out.read_text())
        assert document["schema"] == SCHEMA
        assert document["mode"] == "RESEARCH_ONLY"
        assert document["current_data_ready"] is True
        assert document["economic_inputs_ready"] is False
        assert document["capital_eligible"] is False
        assert document["capture"]["objects_verified"][0]["verified"] is True

    def test_second_identical_run_does_not_rewrite_the_output(self, tmp_path):
        from scripts.qualify_systematic_inputs import main

        capture = tmp_path / "capture"
        capture.mkdir()
        _, size, digest, rows = write_capture(capture, "SYN", ["2026-10-19", "2026-10-21"])
        write_receipt(capture, [entry("SYN", size, digest, rows, last_session="2026-10-21")])
        out = tmp_path / "qualification.json"
        args = ["--capture-root", str(capture), "--output", str(out),
                "--as-of", "2026-10-22T19:05:00Z", "--expected-session", "2026-10-21"]
        assert main(args) == 0
        first = out.stat().st_mtime_ns
        before = out.read_bytes()
        assert main(args) == 0
        assert out.read_bytes() == before
        assert out.stat().st_mtime_ns == first

    def test_hash_mismatch_refuses_and_writes_nothing(self, tmp_path):
        from scripts.qualify_systematic_inputs import main

        capture = tmp_path / "capture"
        capture.mkdir()
        _, size, _, rows = write_capture(capture, "SYN", ["2026-10-19", "2026-10-21"])
        write_receipt(capture, [entry("SYN", size, "c" * 64, rows)])
        out = tmp_path / "qualification.json"
        code = main(["--capture-root", str(capture), "--output", str(out),
                     "--as-of", "2026-10-22T19:05:00Z"])
        assert code == 3
        assert not out.exists()

    def test_receipt_digest_fence_is_enforced(self, tmp_path):
        from scripts.qualify_systematic_inputs import main

        capture = tmp_path / "capture"
        capture.mkdir()
        _, size, digest, rows = write_capture(capture, "SYN", ["2026-10-19", "2026-10-21"])
        payload = write_receipt(capture, [entry("SYN", size, digest, rows)])
        out = tmp_path / "qualification.json"
        wrong = main(["--capture-root", str(capture), "--output", str(out),
                      "--as-of", "2026-10-22T19:05:00Z",
                      "--expect-receipt-sha256", "d" * 64])
        assert wrong == 3
        right = main(["--capture-root", str(capture), "--output", str(out),
                      "--as-of", "2026-10-22T19:05:00Z",
                      "--expect-receipt-sha256", hashlib.sha256(payload).hexdigest()])
        assert right == 0

    def test_gap_is_detected_end_to_end(self, tmp_path):
        from scripts.qualify_systematic_inputs import main

        capture = tmp_path / "capture"
        capture.mkdir()
        _, size, digest, rows = write_capture(capture, "SYN", ["2026-08-17", "2026-08-19"])
        write_receipt(capture, [entry("SYN", size, digest, rows, last_session="2026-08-19")])
        out = tmp_path / "qualification.json"
        assert main(["--capture-root", str(capture), "--output", str(out),
                     "--as-of", "2026-10-22T19:05:00Z",
                     "--expected-session", "2026-08-19"]) == 0
        document = json.loads(out.read_text())
        row = document["instruments"][0]
        assert Code.CALENDAR_GAP in row["blockers"]
        assert row["findings"]["missing_sessions"] == ["2026-08-18"]
        assert document["current_data_ready"] is False

    def test_new_manifest_with_a_stale_object_is_blocked(self, tmp_path):
        from scripts.qualify_systematic_inputs import main

        capture = tmp_path / "capture"
        capture.mkdir()
        # The bytes stop in July; the receipt claims October. The frame wins.
        _, size, digest, rows = write_capture(capture, "SYN", ["2026-07-01", "2026-07-02"])
        write_receipt(capture, [entry("SYN", size, digest, rows,
                                      last_session="2026-10-21")])
        out = tmp_path / "qualification.json"
        assert main(["--capture-root", str(capture), "--output", str(out),
                     "--as-of", "2026-10-22T19:05:00Z",
                     "--expected-session", "2026-10-21"]) == 0
        row = json.loads(out.read_text())["instruments"][0]
        assert row["freshness"]["actual_last_session"] == "2026-07-02"
        assert row["freshness"]["manifest_claim_matches_actual"] is False
        assert Code.LAST_SESSION_STALE in row["blockers"]

    def test_symlink_in_the_capture_root_is_refused(self, tmp_path):
        from scripts.qualify_systematic_inputs import main

        capture = tmp_path / "capture"
        capture.mkdir()
        outside = tmp_path / "outside.csv"
        outside.write_bytes(b"date,open,high,low,close,volume\n2026-10-21,1,1,1,1,1\n")
        payload = outside.read_bytes()
        (capture / "SYN.csv").symlink_to(outside)
        write_receipt(capture, [entry("SYN", len(payload),
                                      hashlib.sha256(payload).hexdigest(), 1)])
        code = main(["--capture-root", str(capture),
                     "--output", str(tmp_path / "q.json"),
                     "--as-of", "2026-10-22T19:05:00Z"])
        assert code == 3

    def test_cli_runs_with_sockets_disabled(self, tmp_path, monkeypatch):
        import socket

        from scripts.qualify_systematic_inputs import main

        def refuse(*args, **kwargs):
            raise AssertionError("the CLI must not open a socket")

        monkeypatch.setattr(socket, "socket", refuse)
        monkeypatch.setattr(socket, "create_connection", refuse)
        capture = tmp_path / "capture"
        capture.mkdir()
        _, size, digest, rows = write_capture(capture, "SYN", ["2026-10-19", "2026-10-21"])
        write_receipt(capture, [entry("SYN", size, digest, rows)])
        out = tmp_path / "qualification.json"
        assert main(["--capture-root", str(capture), "--output", str(out),
                     "--as-of", "2026-10-22T19:05:00Z"]) == 0
        assert out.exists()

    def test_output_is_required_there_is_no_default_path(self):
        from scripts.qualify_systematic_inputs import build_parser

        with pytest.raises(SystemExit):
            build_parser().parse_args(["--capture-root", "/tmp", "--as-of",
                                        "2026-10-22T19:05:00Z"])

    def test_fail_on_blocked_gates_on_economics(self, tmp_path):
        from scripts.qualify_systematic_inputs import main

        capture = tmp_path / "capture"
        capture.mkdir()
        _, size, digest, rows = write_capture(capture, "SYN", ["2026-10-19", "2026-10-21"])
        write_receipt(capture, [entry("SYN", size, digest, rows)])
        out = tmp_path / "qualification.json"
        code = main(["--capture-root", str(capture), "--output", str(out),
                     "--as-of", "2026-10-22T19:05:00Z", "--expected-session", "2026-10-21",
                     "--fail-on-blocked"])
        assert code == 3
        # The document is still produced: recording evidence while blocked is useful.
        assert json.loads(out.read_text())["economic_inputs_ready"] is False
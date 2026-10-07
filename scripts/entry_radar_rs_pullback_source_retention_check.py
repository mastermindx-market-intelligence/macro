#!/usr/bin/env python3
"""Cross-repository SYNTHETIC_CONFORMANCE proof for retained minute observations.

Runs the existing Terminal producer against an injected HTTP transport and
temporary store, then reads those actual atomic files through the Macro bridge
and existing Phase-1 selector. It makes no provider calls and reads no market
outcomes. All source and reader clocks in the scenarios are synthetic.

Run from any directory:
  python scripts/entry_radar_rs_pullback_source_retention_check.py \
    --terminal-source /absolute/path/to/mastermind-terminal

The Terminal source must contain the supported capture implementation. Source
file digests in the output bind the exact code exercised, including dirty trees.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import hashlib
import importlib.util
import io
import itertools
import json
import os
from pathlib import Path
import sys
import tempfile
import urllib.error
import urllib.parse
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.entry_radar.replay.rs_pullback_launch_data import (  # noqa: E402
    build_input_panel,
)
from engine.entry_radar.replay.terminal_minute_observations import (  # noqa: E402
    decode_terminal_minute_observations,
    read_terminal_minute_snapshot,
)

READER = "SYNTHETIC_CONFORMANCE:radar-reader"
DUMMY_KEY = "SYNTHETIC_CONFORMANCE_NO_VENDOR"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load source: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Response:
    """Bounded byte reads, matching the real urllib response seam."""

    def __init__(self, body: dict):
        self.stream = io.BytesIO(json.dumps(body, allow_nan=False).encode())

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.stream.close()

    def read(self, limit: int = -1):
        return self.stream.read(limit)


def run(terminal_source: Path) -> dict:
    terminal_source = terminal_source.resolve(strict=True)
    producer_path = terminal_source / "ingest/backfill_intraday.py"
    capture_path = terminal_source / "ingest/intraday_capture.py"
    if not producer_path.is_file() or not capture_path.is_file():
        raise ValueError("Terminal source lacks the minute capture implementation")
    fixture = load_module(
        "rs_capture_conformance_fixture",
        ROOT / "tests/test_entry_radar_rs_pullback_phase1.py",
    )
    with patch.dict(os.environ, {"POLYGON_API_KEY": DUMMY_KEY}):
        producer = load_module("terminal_capture_producer_under_test", producer_path)

    admission_path = ROOT / (
        "research/live_entry_radar/rs_pullback_launch/"
        "PHASE1_ADMISSION_2026-10-07.json"
    )
    admission_before = digest(admission_path)
    start_ms = int(fixture.clock("2026-10-06T13:30:00Z").timestamp()) * 1000
    base_rows = [
        {
            "t": start_ms + index * 60000,
            "o": 100 + index / 100,
            "h": 100.5 + index / 100,
            "l": 99.5 + index / 100,
            "c": 100.1 + index / 100,
            "v": 17.25,
        }
        for index in range(30)
    ]
    clocks = [
        "2026-10-06T14:17:00Z",
        "2026-10-06T14:18:00Z",
        "2026-10-06T14:19:00Z",
    ]
    decisions = [value.replace(":00Z", ":01Z") for value in clocks]
    receipts = []
    snapshots = []
    exit_codes = []
    frames = []
    logs = []

    def decoded(snapshot, owner_receipts, decision, reader=READER):
        metadata = fixture.fixture()["streams"]["stock"]
        return decode_terminal_minute_observations(
            snapshot,
            owner_receipts,
            reader_identity=reader,
            symbol="SPY",
            stream="stock",
            stream_metadata=metadata,
            cutoff=decision,
        )

    def panel_frame(rows, decision, owner_receipts):
        bundle = fixture.fixture([fixture.candidate(decision=decision)])
        bundle["minutes"] = [
            row for row in bundle["minutes"] if row["stream"] != "stock"
        ] + rows
        # These are owner input receipts, not a separate persistent ledger.
        bundle["terminal_read_receipts"] = copy.deepcopy(owner_receipts)
        return build_input_panel(bundle)["frames"][0]

    def capture_and_read(store, rows, clock, *, partial=False):
        base_ns = int(fixture.clock(clock).timestamp()) * 1_000_000_000
        ticks = itertools.count(base_ns, 1000)
        calls = 0

        def transport(_request, **_kwargs):
            nonlocal calls
            calls += 1
            if partial and calls > 1:
                raise urllib.error.HTTPError(
                    "https://api.polygon.io/synthetic-next",
                    503,
                    "synthetic transport failure",
                    {},
                    None,
                )
            body = {"status": "OK", "results": rows}
            if partial:
                request_url = urllib.parse.urlsplit(_request.full_url)
                body["next_url"] = urllib.parse.urlunsplit((
                    request_url.scheme, request_url.netloc, request_url.path,
                    "cursor=fixture", "",
                ))
            return Response(body)

        output = io.StringIO()
        with (
            patch.object(producer, "INTRADAY", store),
            patch.object(producer.urllib.request, "urlopen", side_effect=transport),
            patch.object(producer.time, "time", return_value=base_ns / 1_000_000_000),
            patch.object(producer.time, "time_ns", side_effect=lambda: next(ticks)),
            patch.object(producer.time, "sleep", return_value=None),
            contextlib.redirect_stdout(output),
        ):
            result = producer.main([
                "--capture-minutes", "--symbols", "SPY", "--tf", "1m",
                "--update", "--workers", "1",
            ])
            snapshot = read_terminal_minute_snapshot(
                store / "SPY.1m.json", reader_identity=READER
            )
        logs.append(output.getvalue())
        exit_codes.append(result)
        assert result == (producer.EXIT_STORE_FAILURES if partial else producer.EXIT_OK), (
            result, output.getvalue()[-1800:]
        )
        assert calls > 1 if partial else calls == 1
        assert DUMMY_KEY.encode() not in snapshot.raw_bytes
        return snapshot

    with tempfile.TemporaryDirectory(prefix="rs-retention-conformance-") as tmp:
        store = Path(tmp) / "intraday"
        for index, clock in enumerate(clocks):
            rows = copy.deepcopy(base_rows)
            if index == 1:
                rows[-1]["c"] += 0.05
            snapshot = capture_and_read(store, rows, clock)
            snapshots.append(snapshot)
            receipts.append(snapshot.receipt)
            bridge = decoded(snapshot, receipts, decisions[index])
            frame = panel_frame(bridge["minutes"], decisions[index], receipts)
            frames.append(frame)

        latest_bridge = decoded(snapshots[-1], receipts, decisions[-1])
        earlier_bridge = decoded(snapshots[-1], receipts, decisions[0])
        earlier_again = panel_frame(earlier_bridge["minutes"], decisions[0], receipts)
        assert fixture.frame_bytes(frames[0]) == fixture.frame_bytes(earlier_again)
        closes = [item["bars"]["stock"]["30"]["ohlcv"]["close"] for item in frames]
        assert closes[0] == closes[2] and closes[1] != closes[0], closes
        for frame in frames:
            assert frame["bars"]["stock"]["30"]["availability"] == "available"
            assert frame["bars"]["stock"]["15"]["availability"] == "unavailable"
            assert frame["availability"] == "unavailable"
            assert frame["condition_met"] is None
            assert not any(frame["authority"].values())
        assert frames[0]["bars"]["stock"]["30"]["ohlcv"]["volume"] == 517.5
        final_document = json.loads(snapshots[-1].raw_bytes)
        assert sum(row[5] for row in final_document["bars"]) == 510
        captures = final_document["minute_capture"]["captures"]
        assert len(captures) == 3
        retained = [
            observation
            for capture in captures
            for observation in capture["payload"]["observations"]
        ]
        assert len(retained) == 32, len(retained)
        source_clocks = [
            page["response_received_at_utc_ns"]
            for capture in captures
            for page in capture["payload"]["pages"]
        ]
        assert len(source_clocks) == 3
        assert all(
            capture["payload"]["finality_lag_s"] == 900 for capture in captures
        )

        # A distinct reader sees the three historical versions for the first
        # time together. Source ordering may not invent its knowledge order.
        late_reader = "SYNTHETIC_CONFORMANCE:late-reader"
        late_ns = int(fixture.clock("2026-10-06T14:20:00Z").timestamp()) * 1_000_000_000
        with patch.object(producer.time, "time_ns", return_value=late_ns):
            late = read_terminal_minute_snapshot(
                store / "SPY.1m.json", reader_identity=late_reader
            )
        late_rows = decoded(
            late, [late.receipt], "2026-10-06T14:20:01Z", reader=late_reader
        )["minutes"]
        late_frame = panel_frame(late_rows, "2026-10-06T14:20:01Z", [late.receipt])
        late_bar = late_frame["bars"]["stock"]["30"]
        assert late_bar["availability"] == "unavailable"
        assert "CONFLICTING_MINUTE_REVISION" in late_bar["refusals"]
        assert late_bar["ohlcv"] is None
        assert late_frame["condition_met"] is None

        # An incomplete response can retain safe source evidence, but cannot
        # replace the chart projection or promote partial rows to RS inputs.
        projection_before = copy.deepcopy(final_document["bars"])
        partial_rows = copy.deepcopy(base_rows)
        partial_rows[-1]["c"] += 0.1
        partial_snapshot = capture_and_read(
            store, partial_rows, "2026-10-06T14:21:00Z", partial=True
        )
        partial_document = json.loads(partial_snapshot.raw_bytes)
        partial_capture = partial_document["minute_capture"]["captures"][-1]
        assert partial_capture["payload"]["status"] == "partial"
        assert partial_capture["payload"]["failure_kind"] == "transport_exhausted"
        assert partial_document["bars"] == projection_before
        partial_receipts = receipts + [partial_snapshot.receipt]
        partial_bridge = decoded(
            partial_snapshot, partial_receipts, "2026-10-06T14:21:01Z"
        )
        assert partial_bridge["minutes"] == latest_bridge["minutes"]
        partial_earlier_bridge = decoded(
            partial_snapshot, partial_receipts, decisions[0]
        )
        partial_earlier = panel_frame(
            partial_earlier_bridge["minutes"], decisions[0], partial_receipts
        )
        assert fixture.frame_bytes(partial_earlier) == fixture.frame_bytes(frames[0])
        retained_count = len(retained)

        # Adversarial, well-sealed synthetic append. The producer would reject
        # this malformed value; this tests the reader's candidate boundary.
        # It is written only to a separate temporary fixture, never a source.
        mutation = copy.deepcopy(partial_document)
        records = mutation["minute_capture"]["captures"]
        future_payload = copy.deepcopy(captures[-1]["payload"])
        mutation_ns = int(fixture.clock("2026-10-06T14:22:00Z").timestamp()) * 1_000_000_000
        future_payload["started_at_utc_ns"] = mutation_ns
        future_payload["finality_reference_utc_ns"] = mutation_ns
        future_payload["completed_at_utc_ns"] = mutation_ns + 3000
        for page in future_payload["pages"]:
            page["request_started_at_utc_ns"] = mutation_ns + 1000
            page["response_received_at_utc_ns"] = mutation_ns + 2000
        future_payload["observations"][0]["event_start_utc_ms"] = "malformed-future-start"

        def seal(value):
            raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True, allow_nan=False).encode()
            return hashlib.sha256(raw).hexdigest()

        used_ids = {record["capture_id"] for record in records}
        counter = 1
        while f"{counter:032x}" in used_ids:
            counter += 1
        future_record = {
            "sequence": len(records) + 1,
            "capture_id": f"{counter:032x}",
            "previous_capture_sha256": mutation["minute_capture"]["prefix_sha256"],
            "payload_sha256": seal(future_payload),
            "payload": future_payload,
        }
        future_record["capture_sha256"] = seal(future_record)
        records.append(future_record)
        mutation["minute_capture"]["prefix_sha256"] = future_record["capture_sha256"]
        mutation_path = Path(tmp) / "future-mutation.json"
        mutation_path.write_text(json.dumps(mutation, allow_nan=False))
        with patch.object(producer.time, "time_ns", return_value=mutation_ns + 4000):
            mutation_snapshot = read_terminal_minute_snapshot(
                mutation_path, reader_identity=READER
            )
        mutation_receipts = partial_receipts + [mutation_snapshot.receipt]
        mutation_earlier = decoded(mutation_snapshot, mutation_receipts, decisions[0])
        mutation_frame = panel_frame(
            mutation_earlier["minutes"], decisions[0], mutation_receipts
        )
        assert fixture.frame_bytes(mutation_frame) == fixture.frame_bytes(frames[0])
        try:
            decoded(mutation_snapshot, mutation_receipts, "2026-10-06T14:22:01Z")
        except ValueError as error:
            assert "event start" in str(error)
        else:
            raise AssertionError("Visible malformed event start must be refused")

    assert digest(admission_path) == admission_before
    return {
        "schema": "mastermind.rs_pullback_launch.source_retention_conformance.v1",
        "input_kind": "SYNTHETIC_CONFORMANCE",
        "clock_basis": "injected source and reader clocks; no market availability claim",
        "result": "PASS",
        "transport": "injected urllib; no provider request",
        "checks": {
            "producer_atomic_store_reader_selector": True,
            "a_b_a_revision_sequence": True,
            "earlier_complete_frame_byte_invariance": True,
            "fractional_volume_preserved": True,
            "future_semantic_mutation_isolated": True,
            "future_invalid_semantics_refused_when_visible": True,
            "late_first_read_conflict_preserved": True,
            "partial_failure_not_promoted": True,
            "partial_failure_preserves_chart_projection": True,
            "credentials_excluded_from_store": True,
            "latest_15m_remains_unavailable": True,
            "phase1_admission_file_unchanged": True,
        },
        "complete_captures": 3,
        "retained_complete_observation_episodes": retained_count,
        "synthetic_30m_closes": closes,
        "synthetic_30m_volume": 517.5,
        "producer_exit_codes": exit_codes,
        "phase1_admission_sha256": admission_before,
        "authority": frames[0]["authority"],
        "source_sha256": {
            "terminal:ingest/backfill_intraday.py": digest(producer_path),
            "terminal:ingest/intraday_capture.py": digest(capture_path),
            "macro:engine/entry_radar/replay/terminal_minute_observations.py": digest(
                ROOT / "engine/entry_radar/replay/terminal_minute_observations.py"
            ),
            "macro:engine/entry_radar/replay/rs_pullback_launch_data.py": digest(
                ROOT / "engine/entry_radar/replay/rs_pullback_launch_data.py"
            ),
            "macro:scripts/entry_radar_rs_pullback_source_retention_check.py": digest(
                Path(__file__)
            ),
            "macro:tests/test_entry_radar_rs_pullback_phase1.py": digest(
                ROOT / "tests/test_entry_radar_rs_pullback_phase1.py"
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--terminal-source", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.terminal_source), sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

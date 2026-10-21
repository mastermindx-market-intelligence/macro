"""Capture-only nightly decision-time stamps for the B4 same-read entry point.

These tests pin the FROZEN SPEC (seat ruling F22) of
``scripts/capture_prophet_b4_same_read.py`` against the REAL owner chain: the
real candidates store, the real W3 board-as-of resolver, the real HEAD-backed
episode snapshot, and the real same-read evaluator.  World fixtures are
imported from the existing suites (``tests/test_prophet_strategy_definition.py``
reader world; ``tests/test_prophet_b4_same_read.py`` clock pins and the
future-owner interposition) — the only new fixture material is the durable
candidates-store parquet part and the committed standouts file the capture
script itself reads.

At BASE the alias seam is unbound (``resolve_alias_table() -> None``) and the
entry-geometry/metric owners do not exist, so every capture row is honestly
``UNAVAILABLE_DATA`` with the owners' typed reasons — that census is the
deliverable, and these tests assert it byte for byte.
"""
import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

import pandas as pd
import pytest

import scripts.capture_prophet_b4_same_read as capture
from engine import us_context_vector as ucv
from engine.prophet_b4_same_read import evaluate_same_read_entry_availability
from engine.prophet_entry_availability import AVAILABILITY_STATES
from engine.prophet_strategy_definition import (
    build_early_leadership_sector_rotation_definition,
)
from engine.us_candidate_episode import canonical_json
from tests.test_prophet_b4_same_read import (
    _SR_ANCHOR_AT,
    _SR_STORE_RECORDED_AT,
    _inject_future_geometry_metric_owners,
    _pin_clocks,
)
from tests.test_prophet_strategy_definition import (
    _B4Aliases,
    _QUALIFIED_SOURCE_KNOWN_AT,
    _b4_reader_observation,
    _b4_reader_world,
)

_SESSION = "2026-09-17"
_CAPTURE_REL = Path("data") / "us_prophet_rank" / "b4_capture"
_FIRST_CAPTURED_AT = datetime(2026, 9, 17, 20, 5, 0, tzinfo=timezone.utc)
_SECOND_CAPTURED_AT = datetime(2026, 9, 17, 21, 40, 0, tzinfo=timezone.utc)


def _stamp_native_rows(root):
    rows, _receipts = ucv.read_today_candidate_source_rows(root)
    return [row for row in rows if str(row.get("stamp_date")) == _SESSION]


def _write_candidates_part(root, tickers):
    """The durable ``us_prophet_rank.candidates/v1`` store part for the stamp."""
    part = root / "data" / "us_prophet_rank" / "candidates"
    part.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "stamp_date": _SESSION,
            "ticker": ticker,
            "board_definition": "gap_continuation",
            "tier": "curated",
        }
        for ticker in tickers
    ]
    pd.DataFrame(rows).to_parquet(part / f"{_SESSION[:7]}.parquet", index=False)


def _world(tmp_path, *, tickers=("UNIT",), session=_SESSION):
    """One complete capture world: candidates store, episode store, live owners.

    Built ON the imported reader-world fixture; the only additions are the two
    committed artifacts the capture script itself reads — the candidates store
    part and the board standouts file.  Each observation's source receipt is
    DERIVED from the actual durable store row exactly as production intake
    derives it, so the script's builder-identical derivation resolves the very
    event the episode store carries.
    """
    _write_candidates_part(tmp_path, tickers)
    native = {row["ticker"]: row for row in _stamp_native_rows(tmp_path)}
    observations = []
    for ticker in tickers:
        receipt = (
            "sha256:" + sha256(canonical_json(native[ticker]).encode("utf-8")).hexdigest()
        )
        observations.append(
            _b4_reader_observation(
                day=session,
                ticker=ticker,
                security_id="SEC:US-XNAS-AAPL" if ticker == "UNIT"
                else f"SEC:US-XNAS-{ticker}",
                company_id="ISS:US-XNAS-AAPL" if ticker == "UNIT"
                else f"ISS:US-XNAS-{ticker}",
                known_at=_QUALIFIED_SOURCE_KNOWN_AT,
                anchor_time=_SR_ANCHOR_AT,
                source_event_id=f"candidate:{session}:{ticker}:gap_continuation",
                source_receipt=receipt,
            )
        )
    world = _b4_reader_world(
        tmp_path,
        observations=observations,
        candidate_inputs=len(tickers),
        source_known_at=_QUALIFIED_SOURCE_KNOWN_AT,
        store_recorded_at=_SR_STORE_RECORDED_AT,
    )
    standouts = tmp_path / "site" / "factordata" / "us_standouts.json"
    standouts.parent.mkdir(parents=True, exist_ok=True)
    standouts.write_text(json.dumps({"as_of": session}), encoding="utf-8")
    return world


def _run(monkeypatch, tmp_path, world, *flags, now=_FIRST_CAPTURED_AT, lane="nightly"):
    if lane is None:
        monkeypatch.delenv("COLLECT_LANE", raising=False)
        monkeypatch.delenv("US_LANE", raising=False)
    else:
        monkeypatch.setenv("COLLECT_LANE", lane)
    monkeypatch.setattr(capture, "_now", lambda: now)
    monkeypatch.setattr(capture, "NATIVE_LIVE_ROOT", world["live_root"])
    _pin_clocks(monkeypatch)
    return capture.main(["--root", str(tmp_path), *flags])


def _capture_file(tmp_path, session=_SESSION):
    return tmp_path / _CAPTURE_REL / session[:7] / f"{session}.jsonl"


def _read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _direct_envelope(tmp_path, world, ticker="UNIT", alias_table=None):
    native = {row["ticker"]: row for row in _stamp_native_rows(tmp_path)}[ticker]
    return evaluate_same_read_entry_availability(
        tmp_path,
        world["snapshot"],
        candidate_source_event_id=f"candidate:{_SESSION}:{ticker}:gap_continuation",
        candidate_source_receipt=(
            "sha256:" + sha256(canonical_json(native).encode("utf-8")).hexdigest()
        ),
        native_live_root=world["live_root"],
        alias_table=alias_table,
        strategy_definition=build_early_leadership_sector_rotation_definition(),
    )


# ── Spec 2/7: report mode, and the lane gate before any read ─────────────────


def test_report_mode_writes_nothing_and_prints_the_run_document(
        tmp_path, monkeypatch, capsys):
    world = _world(tmp_path)

    code = _run(
        monkeypatch, tmp_path, world,
        "--live-root", str(world["live_root"]), lane=None,
    )

    assert code == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["mode"] == "report"
    assert doc["stamp_date"] == _SESSION
    assert doc["snapshot_generation_id"] == world["generation_id"]
    assert doc["rows"] == doc["candidates"] * doc["strategies"] == 1
    assert doc["counts_by_state"] == {"UNAVAILABLE_DATA": 1}
    assert doc["counts_by_reason"] == {"IDENTITY_ALIAS_UNRESOLVED": 1}
    assert doc["rows_written"] == 0
    assert doc["target"] is None
    assert doc["captured_at"] == "2026-09-17T20:05:00Z"
    assert not (tmp_path / _CAPTURE_REL).exists()


def test_durable_mode_refuses_outside_the_nightly_lane_before_any_read(
        tmp_path, monkeypatch, capsys):
    world = _world(tmp_path)
    calls = []

    def no_read(name, *args, **kwargs):  # pragma: no cover - the fence itself
        calls.append(name)
        raise AssertionError(f"{name} was called before the lane gate")

    monkeypatch.setattr(capture, "resolve_board_as_of", lambda *a, **k: no_read("board"))
    monkeypatch.setattr(
        capture, "read_today_candidate_source_rows", lambda *a, **k: no_read("candidates")
    )
    monkeypatch.setattr(
        capture, "load_candidate_episode_store_snapshot", lambda *a, **k: no_read("snapshot")
    )
    monkeypatch.setattr(capture, "NATIVE_LIVE_ROOT", world["live_root"])

    code = _run(monkeypatch, tmp_path, world, "--nightly", lane=None)

    assert code == 3
    assert calls == []
    refusal = json.loads(capsys.readouterr().out)
    assert refusal["refused"] == "NIGHTLY_LANE_NOT_ARMED"
    assert not (tmp_path / _CAPTURE_REL).exists()


def test_durable_mode_refuses_without_a_committed_board_as_of(
        tmp_path, monkeypatch, capsys):
    world = _world(tmp_path)
    (tmp_path / "site" / "factordata" / "us_standouts.json").unlink()

    code = _run(monkeypatch, tmp_path, world, "--nightly")

    assert code == 3
    refusal = json.loads(capsys.readouterr().out)
    assert refusal["refused"] == "COMMITTED_BOARD_AS_OF_MISSING"
    assert not (tmp_path / _CAPTURE_REL).exists()


def test_durable_mode_refuses_an_absent_candidates_stamp(
        tmp_path, monkeypatch, capsys):
    world = _world(tmp_path, session="2026-09-18")

    code = _run(monkeypatch, tmp_path, world, "--nightly")

    assert code == 3
    refusal = json.loads(capsys.readouterr().out)
    assert refusal["refused"] == "CANDIDATES_STAMP_ABSENT"
    assert not (tmp_path / _CAPTURE_REL).exists()


# ── Spec 3/4/6: the durable census, the closed row, the D11 fence ────────────


def test_durable_run_writes_one_row_per_candidate_x_strategy_with_typed_unavailable_reasons(
        tmp_path, monkeypatch, capsys):
    world = _world(tmp_path, tickers=("UNIT", "UNIT2"))
    loads = []
    real_load = capture.load_candidate_episode_store_snapshot

    def counting_load(*args, **kwargs):
        loads.append(args)
        return real_load(*args, **kwargs)

    monkeypatch.setattr(capture, "load_candidate_episode_store_snapshot", counting_load)

    code = _run(monkeypatch, tmp_path, world, "--nightly")

    assert code == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["mode"] == "nightly"
    assert doc["rows"] == doc["candidates"] * doc["strategies"] == 2
    assert doc["rows_written"] == 2
    assert doc["counts_by_state"] == {"UNAVAILABLE_DATA": 2}
    # ONE HEAD-backed snapshot for the whole run — never a second read per
    # candidate.
    assert len(loads) == 1

    rows = _read_rows(_capture_file(tmp_path))
    assert len(rows) == 2
    by_ticker = {row["ticker"]: row for row in rows}
    assert set(by_ticker) == {"UNIT", "UNIT2"}
    for ticker, row in by_ticker.items():
        envelope = _direct_envelope(tmp_path, world, ticker)
        assert row["state"] == "UNAVAILABLE_DATA"
        assert row["unavailable_reasons"] == envelope["unavailable_reasons"]
        assert row["facts"] is None
        assert row["same_read_schema"] == envelope["schema"]
        assert row["nbbo_quality"] == envelope["nbbo_quality"] == "MISSING"
        assert row["episode_id"] == envelope["episode_id"]
        assert row["b3_projection_id"] == envelope["b3_projection_id"]
        assert row["candidate_generation_id"] == world["generation_id"]
        assert row["security_id"].startswith("SEC:US-XNAS-")
        assert row["strategy_definition_id"].startswith("psd:")


def test_row_key_set_is_closed_and_no_state_token_is_ever_persisted(
        tmp_path, monkeypatch):
    world = _world(tmp_path, tickers=("UNIT", "UNIT2"))
    assert _run(monkeypatch, tmp_path, world, "--nightly") == 0

    for row in _read_rows(_capture_file(tmp_path)):
        assert set(row) == set(capture.ROW_KEYS)
        assert row["schema"] == capture.ROW_SCHEMA
        # The row-level state is the SAME-READ vocabulary, never a verdict.
        assert row["state"] in capture.SAME_READ_STATES
        # Every other written scalar, anywhere in the row, is checked against
        # the evaluator's own state tokens.
        for key, value in row.items():
            if key == "state":
                continue
            stack = [value]
            while stack:
                item = stack.pop()
                if isinstance(item, dict):
                    stack.extend(item.values())
                elif isinstance(item, (list, tuple)):
                    stack.extend(item)
                elif isinstance(item, str):
                    assert item not in AVAILABILITY_STATES, (key, item)
        # No verdict field survives in facts (None at BASE).
        assert row["facts"] is None


# ── Spec 3: EVALUATED rows persist facts only, and the verdict round-trips ───


def test_evaluated_row_persists_facts_only_and_round_trips_the_verdict(
        tmp_path, monkeypatch):
    world = _world(tmp_path)
    monkeypatch.setattr(capture, "resolve_alias_table", lambda: _B4Aliases("UNIT"))
    _inject_future_geometry_metric_owners(monkeypatch)

    assert _run(monkeypatch, tmp_path, world, "--nightly") == 0
    row = _read_rows(_capture_file(tmp_path))[0]
    assert row["state"] == "EVALUATED"
    assert isinstance(row["facts"], dict)
    assert not set(row["facts"]) & set(capture.VERDICT_FIELDS)

    # The verdict is re-derived: re-evaluating the same world reproduces every
    # persisted fact byte for byte, and the ONLY keys the fresh evaluation adds
    # are exactly the removed verdict fields.
    fresh = _direct_envelope(tmp_path, world, alias_table=_B4Aliases("UNIT"))
    assert fresh["state"] == "EVALUATED"
    availability = fresh["availability"]
    assert {key: availability[key] for key in row["facts"]} == row["facts"]
    assert set(availability) - set(row["facts"]) == set(capture.VERDICT_FIELDS)
    # The D11 fence held on the evaluated row too: no availability state token
    # was persisted anywhere in it.
    stack = [row["facts"], row["binding"], row["receipts"]]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            stack.extend(item.values())
        elif isinstance(item, (list, tuple)):
            stack.extend(item)
        elif isinstance(item, str):
            assert item not in AVAILABILITY_STATES


# ── Spec 6: idempotence and the typed conflict ───────────────────────────────


def test_second_durable_run_is_idempotent_and_keeps_committed_captured_at(
        tmp_path, monkeypatch, capsys):
    world = _world(tmp_path)

    assert _run(monkeypatch, tmp_path, world, "--nightly", now=_FIRST_CAPTURED_AT) == 0
    capsys.readouterr()
    first_bytes = _capture_file(tmp_path).read_bytes()
    first_rows = _read_rows(_capture_file(tmp_path))

    code = _run(monkeypatch, tmp_path, world, "--nightly", now=_SECOND_CAPTURED_AT)

    assert code == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["rows_written"] == 0
    assert _capture_file(tmp_path).read_bytes() == first_bytes
    for row in _read_rows(_capture_file(tmp_path)):
        assert row["captured_at"] == "2026-09-17T20:05:00Z"
    assert first_rows[0]["captured_at"] == "2026-09-17T20:05:00Z"


def test_changed_row_body_under_an_existing_key_is_a_typed_conflict_and_writes_nothing(
        tmp_path, monkeypatch, capsys):
    world = _world(tmp_path)
    assert _run(monkeypatch, tmp_path, world, "--nightly") == 0
    capsys.readouterr()
    target = _capture_file(tmp_path)
    committed = target.read_bytes()

    tampered = _read_rows(target)
    tampered[0]["unavailable_reasons"] = ["SOMETHING_ELSE"]
    target.write_text(
        "".join(
            json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
            for row in tampered
        ),
        encoding="utf-8",
    )
    tampered_bytes = target.read_bytes()

    code = _run(
        monkeypatch, tmp_path, world, "--nightly", now=_SECOND_CAPTURED_AT
    )

    assert code == 2
    conflict = json.loads(capsys.readouterr().out)
    assert conflict["conflict"][0] == _SESSION
    # NOTHING was written: the tampered file is byte-identical, and no merge
    # rewrote it.
    assert target.read_bytes() == tampered_bytes != committed


# ── Spec 4/5: the builder-identical derivation and the owner-input seams ─────


def test_source_key_and_receipt_match_the_builder_derivation(tmp_path, monkeypatch):
    world = _world(tmp_path)
    assert _run(monkeypatch, tmp_path, world, "--nightly") == 0
    row = _read_rows(_capture_file(tmp_path))[0]

    native = _stamp_native_rows(tmp_path)[0]
    expected_key = "candidate:{stamp_date}:{ticker}:{board_definition}".format(**native)
    expected_receipt = (
        "sha256:" + sha256(canonical_json(native).encode("utf-8")).hexdigest()
    )
    assert row["candidate_source_event_id"] == expected_key == world["source_event_id"]
    assert row["candidate_source_receipt"] == expected_receipt

    definition = build_early_leadership_sector_rotation_definition()
    assert row["strategy_definition_id"] == definition["strategy_definition_id"]
    assert row["strategy_definition_receipt"] == (
        "sha256:" + sha256(canonical_json(definition).encode("utf-8")).hexdigest()
    )


def test_live_root_override_is_report_only(tmp_path, monkeypatch, capsys):
    world = _world(tmp_path)

    code = _run(
        monkeypatch, tmp_path, world,
        "--nightly", "--live-root", str(world["live_root"]),
    )

    assert code == 3
    refusal = json.loads(capsys.readouterr().out)
    assert refusal["refused"] == "LIVE_ROOT_OVERRIDE_FORBIDDEN_IN_NIGHTLY_MODE"
    assert not (tmp_path / _CAPTURE_REL).exists()

    # The same override is lawful inspection in report mode.
    code = _run(
        monkeypatch, tmp_path, world,
        "--live-root", str(world["live_root"]), lane=None,
    )
    assert code == 0
    assert json.loads(capsys.readouterr().out)["mode"] == "report"


def test_alias_seam_is_unbound_at_base_and_the_gap_is_typed_not_guessed(
        tmp_path, monkeypatch):
    world = _world(tmp_path)

    assert capture.resolve_alias_table() is None
    assert _run(monkeypatch, tmp_path, world, "--nightly") == 0
    row = _read_rows(_capture_file(tmp_path))[0]
    assert row["state"] == "UNAVAILABLE_DATA"
    # The adapter's own refusal is the captured reason — never a guessed alias.
    assert row["unavailable_reasons"] == ["IDENTITY_ALIAS_UNRESOLVED"]


# ── Spec 8: ZERO AUTHORITY — no product builder or template reads the stream ─


def test_no_product_builder_or_template_reads_the_capture_stream():
    fences = sorted(Path("scripts").glob("build_*.py")) + [
        Path("engine/prophet_bridge.py"),
        Path("engine/prophet_opportunity_presentation.py"),
        Path("engine/prophet_candidate_state.py"),
    ] + sorted(Path("templates").rglob("*"))
    needles = ("b4_capture", "capture_prophet_b4_same_read")
    assert fences
    for path in fences:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for needle in needles:
            assert needle not in text, f"{path} mentions {needle}"


def test_docstring_pins_zero_authority_and_capture_only():
    text = capture.__doc__
    assert "ZERO AUTHORITY" in text
    assert "first run is" in text
    assert "capture-only" in text.split("first run is")[1][:60]
    assert "ENTRY_OPEN" in text

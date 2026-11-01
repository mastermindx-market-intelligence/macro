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

Without the committed Data OS reference the alias seam is unbound (``None``) and the
entry-geometry/metric owners do not exist, so every capture row is honestly
``UNAVAILABLE_DATA`` with the owners' typed reasons — that census is the
deliverable, and these tests assert it byte for byte.
"""
import json
import subprocess
from datetime import date, datetime, timezone
from hashlib import sha256
from pathlib import Path

import pandas as pd
import pytest

import scripts.capture_prophet_b4_same_read as capture
from engine import us_context_vector as ucv
from engine.prophet_b4_same_read import evaluate_same_read_entry_availability
from engine.prophet_entry_availability import AVAILABILITY_STATES
from engine.prophet_entry_availability_sources import RuntimeOwnerFactError
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

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SESSION = "2026-09-17"
_CAPTURE_REL = Path("data") / "us_prophet_rank" / "b4_capture"
_FIRST_CAPTURED_AT = datetime(2026, 9, 17, 20, 5, 0, tzinfo=timezone.utc)
_SECOND_CAPTURED_AT = datetime(2026, 9, 17, 21, 40, 0, tzinfo=timezone.utc)
#: The VPS pass for stamp 2026-09-17 happens inside the NEXT session (Fri 09-18).
_PASS_AT = datetime(2026, 9, 18, 15, 6, 30, tzinfo=timezone.utc)
_PASS_ISO = "2026-09-18T15:06:30Z"
_PASS_OBJ = "20260918T150630Z.json"


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


def _world(tmp_path, *, tickers=("UNIT",), session=_SESSION, alias_reference=True):
    """One complete capture world: candidates store, episode store, live owners.

    Built ON the imported reader-world fixture; the only additions are the
    committed artifacts the capture script itself reads — the candidates store
    part, the board standouts file and (by default) an EMPTY but lawful Data OS
    alias reference, so the durable nightly path has its tracked file while the
    seam still resolves nothing and the adapter's own typed refusal stays the
    row reason.  Each observation's source receipt is DERIVED from the actual
    durable store row exactly as production intake derives it, so the script's
    builder-identical derivation resolves the very event the episode store
    carries.
    """
    _write_candidates_part(tmp_path, tickers)
    if alias_reference:
        _write_alias_reference(tmp_path, [])
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
    assert doc["dry_run"] is False
    # F3: the run document names the root it wrote under and whether --root
    # overrode the repository default, so a night's receipt is auditable.
    assert doc["root_override"] is True
    assert doc["data_root"] == str(tmp_path.resolve())
    assert Path(doc["data_root"]) / _CAPTURE_REL == _capture_file(tmp_path).parent.parent
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
    monkeypatch.setattr(capture, "resolve_alias_table", lambda *_, **__: _B4Aliases("UNIT"))
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


def test_alias_seam_is_unbound_without_the_reference_in_dry_run_and_the_gap_is_typed_not_guessed(
        tmp_path, monkeypatch, capsys):
    """Report / dry-run: no reference -> unbound seam, the adapter's own typed
    refusal is the row reason, nothing durable is written."""
    world = _world(tmp_path, alias_reference=False)

    assert not (tmp_path / "data" / "reference" / "vendor_aliases.parquet").exists()
    assert capture.resolve_alias_table(tmp_path) is None
    assert _run(monkeypatch, tmp_path, world, "--nightly", "--dry-run") == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["alias_table"] == {"bound": False, "receipt": None}
    assert doc["counts_by_state"] == {"UNAVAILABLE_DATA": len(capture.STRATEGY_DEFINITIONS)}
    # The adapter's own refusal is the reported reason — never a guessed alias.
    assert set(doc["counts_by_reason"]) == {"IDENTITY_ALIAS_UNRESOLVED"}
    assert not (tmp_path / _CAPTURE_REL).exists()


@pytest.mark.parametrize("shape", ["absent", "directory"])
def test_a_durable_nightly_capture_refuses_an_absent_reference_instead_of_degrading_rows(
        tmp_path, monkeypatch, capsys, shape):
    """The reference is a tracked file: its absence is an incomplete checkout,
    not a lawful "no alias" state.  A durable row written against the unbound
    seam could never be told apart from a security with no store alias, nor
    corrected later (the day file keeps the first row under each key), so the
    nightly write is a typed refusal with nothing persisted."""
    world = _world(tmp_path, alias_reference=False)
    path = tmp_path / "data" / "reference" / "vendor_aliases.parquet"
    if shape == "directory":
        path.mkdir(parents=True)
    assert capture.resolve_alias_table(tmp_path) is None
    with pytest.raises(capture.TypedRefusal) as refusal:
        capture.resolve_alias_table(tmp_path, required=True)
    assert refusal.value.token == "ALIAS_REFERENCE_MISSING"

    assert _run(monkeypatch, tmp_path, world, "--nightly") == 3
    assert json.loads(capsys.readouterr().out)["refused"] == "ALIAS_REFERENCE_MISSING"
    assert not (tmp_path / _CAPTURE_REL).exists()


def _write_alias_reference(root, rows):
    path = root / "data" / "reference" / "vendor_aliases.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows, columns=[
        "vendor", "vendor_symbol", "security_id", "valid_from", "valid_to",
        "ingested_at", "known_at", "evidence_sha256", "binding_sha256", "alias_kind",
    ])
    frame.to_parquet(path, index=False)
    return path


def test_alias_seam_binds_the_committed_data_os_reference_and_the_row_evaluates(
        tmp_path, monkeypatch, capsys):
    """The bound seam resolves the candidate's canonical security_id to its
    ``store`` symbol through the ONE identity reader; the same world that was
    IDENTITY_ALIAS_UNRESOLVED without the reference now EVALUATES, and the run
    document names the exact reference bytes (sha256) it resolved against."""
    world = _world(tmp_path)
    path = _write_alias_reference(tmp_path, [
        {"vendor": "store", "vendor_symbol": "UNIT", "security_id": "SEC:US-XNAS-AAPL"},
        {"vendor": "yahoo", "vendor_symbol": "AAPL", "security_id": "SEC:US-XNAS-AAPL"},
    ])
    _inject_future_geometry_metric_owners(monkeypatch)

    table = capture.resolve_alias_table(tmp_path)
    assert table is not None
    assert table.vendor_symbol_for("store", "SEC:US-XNAS-AAPL", date(2026, 9, 17)) == "UNIT"
    assert table.resolve("store", "UNIT", date(2026, 9, 17)) == "SEC:US-XNAS-AAPL"
    assert table.receipt == {
        "path": str(path),
        "sha256": "sha256:" + sha256(path.read_bytes()).hexdigest(),
    }

    assert _run(monkeypatch, tmp_path, world, "--nightly") == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["alias_table"] == {"bound": True, "receipt": table.receipt}
    assert doc["counts_by_state"] == {"EVALUATED": 1}
    assert doc["counts_by_reason"] == {}
    row = _read_rows(_capture_file(tmp_path))[0]
    assert row["state"] == "EVALUATED"
    assert row["unavailable_reasons"] == []
    assert not set(row["facts"]) & set(capture.VERDICT_FIELDS)


def test_a_present_but_unlawful_alias_reference_is_a_typed_refusal_not_a_silent_unbind(
        tmp_path, monkeypatch, capsys):
    world = _world(tmp_path)
    # two timeless rows claim the same store symbol: an ambiguous translation layer
    _write_alias_reference(tmp_path, [
        {"vendor": "store", "vendor_symbol": "UNIT", "security_id": "SEC:US-XNAS-AAPL"},
        {"vendor": "store", "vendor_symbol": "UNIT", "security_id": "SEC:US-XNAS-OTHER"},
    ])
    with pytest.raises(capture.TypedRefusal) as info:
        capture.resolve_alias_table(tmp_path)
    assert info.value.token == "ALIAS_TABLE_MALFORMED"

    assert _run(monkeypatch, tmp_path, world, "--nightly") == 3
    assert json.loads(capsys.readouterr().out)["refused"] == "ALIAS_TABLE_MALFORMED"
    assert not (tmp_path / _CAPTURE_REL).exists()


def _reference_is_sparse_omitted(relative: Path) -> bool:
    """True when the tracked reference is skip-worktree (sparse session tree)."""
    proc = subprocess.run(
        ["git", "ls-files", "-v", "--", str(relative)],
        cwd=_REPO_ROOT, capture_output=True, text=True, check=False)
    return proc.returncode == 0 and proc.stdout[:1] == "S"


def test_the_production_reference_binds_and_resolves_a_store_symbol():
    """The committed estate reference loads through the seam as production will
    read it: a currently valid ``store`` alias round-trips both ways.  A sparse
    session worktree that omits ``data/`` skips; a tracked-but-missing file in
    a full checkout fails, exactly as the durable nightly write would refuse."""
    relative = Path(*capture.ALIAS_REFERENCE_PARTS)
    if not (_REPO_ROOT / relative).is_file():
        if _reference_is_sparse_omitted(relative):
            pytest.skip("sparse worktree omits data/reference (skip-worktree)")
        pytest.fail(f"{relative} is tracked but missing from this checkout")
    table = capture.resolve_alias_table(_REPO_ROOT, required=True)
    assert table.receipt["sha256"].startswith("sha256:")
    frame = pd.read_parquet(_REPO_ROOT / relative)
    on = date(2026, 10, 30)
    store = frame[(frame["vendor"] == "store") & frame["valid_to"].isna()
                  & (frame["valid_from"].isna() | (pd.to_datetime(frame["valid_from"]).dt.date <= on))]
    assert not store.empty, "the production reference carries at least one store alias open on the probe date"
    probe = store.iloc[0]
    symbol = table.vendor_symbol_for("store", str(probe["security_id"]), on)
    assert symbol == str(probe["vendor_symbol"])
    assert table.resolve("store", symbol, on) == str(probe["security_id"])


# ── Spec 8: ZERO AUTHORITY — no product builder or template reads the stream ─


_FENCE_NEEDLES = ("b4_capture", "capture_prophet_b4_same_read")


def _capture_stream_consumers(root: Path) -> list[tuple[str, str]]:
    """Every (file, needle) under ``root`` where a product builder, a presentation
    engine module or a template names the capture stream.  Anchored on the
    root passed in — never the process cwd — so the scan reads the repository
    the script under test lives in."""
    fences = sorted((root / "scripts").glob("build_*.py")) + [
        root / "engine" / "prophet_bridge.py",
        root / "engine" / "prophet_opportunity_presentation.py",
        root / "engine" / "prophet_candidate_state.py",
    ] + sorted((root / "templates").rglob("*"))
    assert fences
    hits = []
    for path in fences:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        hits.extend(
            (path.relative_to(root).as_posix(), needle)
            for needle in _FENCE_NEEDLES
            if needle in text
        )
    return hits


def test_no_product_builder_or_template_reads_the_capture_stream(tmp_path):
    repo_root = Path(capture.__file__).resolve().parents[1]
    assert (repo_root / "scripts" / "capture_prophet_b4_same_read.py").is_file()
    assert _capture_stream_consumers(repo_root) == []

    # Positive control: a planted consumer IS reported, so the empty result
    # above means the fence held — not that the scan looked at nothing.
    planted = tmp_path / "scripts" / "build_planted_consumer.py"
    planted.parent.mkdir(parents=True)
    planted.write_text("ROWS = load('data/us_prophet_rank/b4_capture')\n", encoding="utf-8")
    (tmp_path / "templates").mkdir()
    assert _capture_stream_consumers(tmp_path) == [
        ("scripts/build_planted_consumer.py", "b4_capture"),
    ]


# ── Review repairs F1 / F2 / F4 / F12 (seat ruling F27) ──────────────────────


def _synthetic_evaluated_envelope(**availability_extra):
    availability = {
        "state": "VERDICT_TOKEN_NEVER_PERSISTED",
        "entry_open": False,
        "chase_state": "VERDICT_CHASE",
        "availability_id": "sha256:" + "0" * 64,
        "blockers": ["NBBO_QUALITY_MISSING"],
        "reasons": ["QUOTE_STALE"],
        "quote_age_seconds": 12.5,
        "gate_inputs": {"nbbo": "MISSING", "lifecycle": "OPEN"},
    }
    availability.update(availability_extra)
    return {
        "schema": "prophet.b4.same_read/v1",
        "state": "EVALUATED",
        "availability": availability,
        "b3_projection_id": None,
        "episode_id": None,
        "binding": None,
        "owner_read_schema": None,
        "nbbo_quality": "MISSING",
        "unavailable_reasons": [],
        "receipts": [],
    }


def _build_row(world, envelope):
    return capture._capture_row(
        stamp_date=_SESSION,
        captured_at=capture._now_iso(_FIRST_CAPTURED_AT),
        ticker="UNIT",
        source_event_id=f"candidate:{_SESSION}:UNIT:gap_continuation",
        source_receipt="sha256:" + "a" * 64,
        definition=build_early_leadership_sector_rotation_definition(),
        definition_receipt="sha256:" + "b" * 64,
        envelope=envelope,
        snapshot=world["snapshot"],
    )


def test_row_builder_strips_the_verdict_trace_blockers_and_reasons(tmp_path):
    """F1: ``blockers`` / ``reasons`` are the state-decision branch's verdict
    trace — an encoded verdict — so the row builder strips them with the other
    verdict fields; only the evaluator's INPUT facts survive."""
    world = _world(tmp_path)
    row = _build_row(world, _synthetic_evaluated_envelope())

    assert {"blockers", "reasons"} <= set(capture.VERDICT_FIELDS)
    assert row["facts"] == {
        "quote_age_seconds": 12.5,
        "gate_inputs": {"nbbo": "MISSING", "lifecycle": "OPEN"},
    }
    assert "blockers" not in row and "reasons" not in row
    # No mapping anywhere in the row — facts, binding, receipts — carries a
    # verdict-trace key (``unavailable_reasons`` is the same-read envelope's
    # own typed-reason list, a different field).
    for mapping in capture._walk_mappings(row):
        assert not ({"blockers", "reasons"} & set(mapping)), mapping


def test_write_fence_refuses_a_smuggled_verdict_trace_anywhere_in_facts(tmp_path):
    world = _world(tmp_path)
    lawful = _build_row(world, _synthetic_evaluated_envelope())
    capture._assert_row_is_lawful(lawful)  # the control row passes

    top_level = dict(lawful)
    top_level["reasons"] = ["QUOTE_STALE"]
    with pytest.raises(capture.TypedRefusal) as refused:
        capture._assert_row_is_lawful(top_level)
    assert refused.value.token == "CAPTURE_ROW_PERSISTS_A_VERDICT_TRACE"

    in_facts = dict(lawful)
    in_facts["facts"] = dict(lawful["facts"], reasons=["QUOTE_STALE"])
    with pytest.raises(capture.TypedRefusal) as refused:
        capture._assert_row_is_lawful(in_facts)
    assert refused.value.token == "CAPTURE_ROW_PERSISTS_A_VERDICT_TRACE"

    nested = dict(lawful)
    nested["facts"] = {"gate_inputs": {"trace": [{"blockers": []}]}}
    with pytest.raises(capture.TypedRefusal) as refused:
        capture._assert_row_is_lawful(nested)
    assert refused.value.token == "CAPTURE_ROW_PERSISTS_A_VERDICT_TRACE"


def test_capture_key_is_the_candidate_source_event_so_unbound_candidates_never_collide(
        tmp_path, monkeypatch, capsys):
    """F2: two bound + two UNBOUND candidates (owner fact absent → the typed
    ``UNAVAILABLE_DATA`` fallback envelope, ``security_id`` None) are FOUR rows
    under four keys; keying on ``security_id`` collapsed the unbound pair onto
    one ``None`` key and refused the night as a false conflict."""
    world = _world(tmp_path, tickers=("UNIT", "UNIT2", "LONE", "ORPH"))
    real_evaluate = capture.evaluate_same_read_entry_availability

    def evaluate_with_two_unbound(root, snapshot, **kwargs):
        event = kwargs["candidate_source_event_id"]
        if event.split(":")[2] in {"LONE", "ORPH"}:
            raise RuntimeOwnerFactError(f"owner fact absent for {event}")
        return real_evaluate(root, snapshot, **kwargs)

    monkeypatch.setattr(
        capture, "evaluate_same_read_entry_availability", evaluate_with_two_unbound
    )

    assert _run(monkeypatch, tmp_path, world, "--nightly") == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["rows"] == doc["rows_written"] == 4
    rows = _read_rows(_capture_file(tmp_path))
    by_ticker = {row["ticker"]: row for row in rows}
    assert set(by_ticker) == {"UNIT", "UNIT2", "LONE", "ORPH"}
    assert by_ticker["LONE"]["security_id"] is None
    assert by_ticker["ORPH"]["security_id"] is None
    assert by_ticker["UNIT"]["security_id"] == "SEC:US-XNAS-AAPL"
    for ticker in ("LONE", "ORPH"):
        assert by_ticker[ticker]["state"] == "UNAVAILABLE_DATA"
        assert by_ticker[ticker]["unavailable_reasons"] == [
            f"RuntimeOwnerFactError: owner fact absent for candidate:{_SESSION}:{ticker}:gap_continuation"
        ]
    keys = [capture._row_key_of(row) for row in rows]
    assert len(set(keys)) == 4
    assert {key[1] for key in keys} == {row["candidate_source_event_id"] for row in rows}

    # The second night is idempotent: nothing appended, captured_at kept.
    assert _run(monkeypatch, tmp_path, world, "--nightly", now=_SECOND_CAPTURED_AT) == 0
    assert json.loads(capsys.readouterr().out)["rows_written"] == 0
    assert {row["ticker"]: row["captured_at"] for row in _read_rows(_capture_file(tmp_path))} == {
        ticker: "2026-09-17T20:05:00Z" for ticker in ("UNIT", "UNIT2", "LONE", "ORPH")
    }


def test_conflict_reports_body_digests_never_bodies(tmp_path, monkeypatch, capsys):
    world = _world(tmp_path)
    assert _run(monkeypatch, tmp_path, world, "--nightly") == 0
    capsys.readouterr()
    target = _capture_file(tmp_path)
    tampered = _read_rows(target)
    tampered[0]["unavailable_reasons"] = ["SOMETHING_ELSE"]
    target.write_text(
        json.dumps(tampered[0], sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    assert _run(monkeypatch, tmp_path, world, "--nightly", now=_SECOND_CAPTURED_AT) == 2
    conflict = json.loads(capsys.readouterr().out)
    assert conflict["conflict"][1] == f"candidate:{_SESSION}:UNIT:gap_continuation"
    for digest in (conflict["committed"], conflict["incoming"]):
        assert digest.startswith("sha256:") and len(digest) == len("sha256:") + 64
    assert conflict["committed"] != conflict["incoming"]
    assert "SOMETHING_ELSE" not in json.dumps(conflict)


def test_dry_run_is_not_lane_gated_builds_every_row_and_writes_nothing(
        tmp_path, monkeypatch, capsys):
    """F4: ``--nightly --dry-run`` is the no-write preview of the nightly
    shape — unarmed it still runs, prints the run document and leaves no file
    and no directory behind."""
    world = _world(tmp_path, tickers=("UNIT", "UNIT2"))
    code = _run(monkeypatch, tmp_path, world, "--nightly", "--dry-run", lane=None)
    assert code == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["mode"] == "dry-run"
    assert doc["dry_run"] is True
    assert doc["rows"] == doc["candidates"] * doc["strategies"] == 2
    assert doc["rows_written"] == 0
    assert doc["target"] == str(_capture_file(tmp_path))
    assert not _capture_file(tmp_path).exists()
    assert not (tmp_path / _CAPTURE_REL).exists()
    # The armed, non-dry nightly on the same world is unchanged by the preview.
    assert _run(monkeypatch, tmp_path, world, "--nightly") == 0
    assert json.loads(capsys.readouterr().out)["rows_written"] == 2


def test_malformed_committed_day_file_is_a_typed_error_exit_2_and_writes_nothing(
        tmp_path, monkeypatch, capsys):
    """F12: a day file the merge cannot read is a typed ``CaptureDayFileError``
    document with exit code 2 — never a traceback — and the file is untouched."""
    world = _world(tmp_path)
    target = _capture_file(tmp_path)
    target.parent.mkdir(parents=True)
    target.write_text("this is not a capture row\n", encoding="utf-8")
    before = target.read_bytes()

    code = _run(monkeypatch, tmp_path, world, "--nightly")

    assert code == 2
    doc = json.loads(capsys.readouterr().out)
    assert set(doc) == {"error"}
    assert doc["error"]["type"] == "CaptureDayFileError"
    assert doc["error"]["detail"]
    assert target.read_bytes() == before
    assert [entry.name for entry in target.parent.iterdir()] == [target.name]


def test_docstring_pins_zero_authority_and_capture_only():
    text = capture.__doc__
    assert "ZERO AUTHORITY" in text
    assert "first run is" in text
    assert "capture-only" in text.split("first run is")[1][:60]
    assert "ENTRY_OPEN" in text


# ── Two hosts, one stream: the VPS spool pass and the nightly spool ingest ───
#
# The capture's facts live on two machines (committed tree + native live plane) and
# the live-plane host writes nothing under data/, so ``--spool`` publishes one object
# per pass and ``--nightly --from-spool`` is the sole durable advancer.  The fake R2
# below is a dict; r2io's own suite covers the wire.


class _FakeS3:
    """The two boto3 calls the ingest's STRICT listing makes, paginated in pages of 2
    so a single-page fake cannot hide a lost continuation."""

    def __init__(self, spool):
        self.spool = spool

    def list_objects_v2(self, *, Bucket, Prefix, ContinuationToken=None):
        if self.spool.list_fail:
            raise RuntimeError("R2 LIST failed (fake transport)")
        if ContinuationToken is None:
            self.spool.lists.append(Prefix)
        keys = sorted(k for k in self.spool.objects if k.startswith(Prefix))
        start = int(ContinuationToken or 0)
        page = keys[start:start + 2]
        more = start + 2 < len(keys)
        out = {"Contents": [{"Key": k} for k in page], "IsTruncated": more}
        if more:
            out["NextContinuationToken"] = str(start + 2)
        return out


class _FakeSpool:
    """Dict-backed stand-in for the r2io functions the capture calls."""

    def __init__(self, *, publish=True, client=True, list_fail=False):
        self.objects: dict[str, object] = {}
        self.puts: list[str] = []
        self.lists: list[str] = []
        self.publish = publish
        self.client_available = client
        self.list_fail = list_fail

    def install(self, monkeypatch):
        r2 = capture.r2io
        monkeypatch.setattr(r2, "client", lambda: _FakeS3(self) if self.client_available else None)

        def put_json(key, payload, *, s3=None):
            self.puts.append(key)
            if not self.publish:
                return False
            # Round-trip through JSON exactly as the wire would.
            self.objects[key] = json.loads(json.dumps(payload))
            return True

        def list_keys(prefix, *, s3=None):  # the lenient lister: the ingest must NOT use it
            raise AssertionError("ingest must list strictly via s3.list_objects_v2, not r2io.list_keys")

        def get_json(key, *, s3=None, allow_public=True):
            assert allow_public is False, "the ingest must never fall back to the public mirror"
            return self.objects.get(key)

        monkeypatch.setattr(r2, "put_json", put_json)
        monkeypatch.setattr(r2, "list_keys", list_keys)
        monkeypatch.setattr(r2, "get_json", get_json)
        return self


def _ingest(monkeypatch, root, *flags, now=_SECOND_CAPTURED_AT, lane="nightly"):
    """A nightly ingest on a host with NO live plane (the Mac runner)."""
    if lane is None:
        monkeypatch.delenv("COLLECT_LANE", raising=False)
        monkeypatch.delenv("US_LANE", raising=False)
    else:
        monkeypatch.setenv("COLLECT_LANE", lane)
    monkeypatch.setattr(capture, "_now", lambda: now)
    monkeypatch.setattr(capture, "NATIVE_LIVE_ROOT", root / "no-such-live-plane")
    _pin_clocks(monkeypatch)
    return capture.main(["--root", str(root), "--nightly", "--from-spool", *flags])


def test_spool_pass_publishes_one_object_with_the_rows_the_nightly_would_write(
        tmp_path, monkeypatch, capsys):
    world = _world(tmp_path, tickers=("UNIT", "UNIT2"))
    spool = _FakeSpool().install(monkeypatch)

    code = _run(monkeypatch, tmp_path, world, "--spool", lane=None, now=_PASS_AT)

    assert code == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["mode"] == "spool" and doc["source"] == "native_live_root"
    assert doc["rows"] == 2 and doc["rows_written"] == 0 and doc["target"] is None
    assert doc["alias_table"]["bound"] is True
    key = doc["spool"]["key"]
    assert spool.puts == [key]
    assert key == f"{capture.SPOOL_PREFIX}/{_SESSION}/{_PASS_OBJ}"
    # Nothing under data/ on the live-plane host: the spool IS the pass's output.
    assert not (tmp_path / _CAPTURE_REL).exists()
    obj = spool.objects[key]
    assert obj["schema"] == capture.SPOOL_SCHEMA
    assert obj["producer"] == capture.SPOOL_PRODUCER
    assert obj["stamp_date"] == _SESSION and obj["captured_at"] == _PASS_ISO
    assert obj["pass_date"] == "2026-09-18"  # the guard's Eastern date rides with the pass
    assert doc["spool"]["session_guard"] == {
        "pass_date": "2026-09-18", "stamp_date": _SESSION, "prior_session": _SESSION}
    assert obj["counts_by_state"] == {"UNAVAILABLE_DATA": 2}
    for row in obj["rows"]:
        assert set(row) == set(capture.ROW_KEYS)
        capture._assert_row_is_lawful(row)

    # The same world, same clock, captured DIRECTLY by a nightly host that has both
    # the tree and the live plane: the committed rows are byte-identical to the spool.
    assert _run(monkeypatch, tmp_path, world, "--nightly", now=_PASS_AT) == 0
    capsys.readouterr()
    direct = _read_rows(_capture_file(tmp_path))
    # The day file is key-sorted by the merge; the spool keeps build order.
    srt = lambda rows: sorted(rows, key=lambda r: capture._sort_key(capture._row_key_of(r)))
    assert [capture._row_body(r) for r in srt(direct)] == [capture._row_body(r) for r in srt(obj["rows"])]
    assert {r["captured_at"] for r in direct} == {r["captured_at"] for r in obj["rows"]}


def test_spool_pass_that_does_not_publish_is_a_typed_refusal_not_a_silent_zero(
        tmp_path, monkeypatch, capsys):
    world = _world(tmp_path)
    spool = _FakeSpool(publish=False).install(monkeypatch)

    code = _run(monkeypatch, tmp_path, world, "--spool", now=_PASS_AT)

    assert code == 3
    refusal = json.loads(capsys.readouterr().out)
    assert refusal["refused"] == "SPOOL_NOT_PUBLISHED"
    assert len(spool.puts) == 1
    assert not (tmp_path / _CAPTURE_REL).exists()


@pytest.mark.parametrize("flags,token", [
    (("--spool", "--nightly"), "SPOOL_MODE_IS_NOT_NIGHTLY"),
    (("--spool", "--dry-run"), "SPOOL_MODE_IS_NOT_NIGHTLY"),
    (("--spool", "--from-spool"), "SPOOL_MODE_IS_NOT_NIGHTLY"),
    (("--from-spool",), "FROM_SPOOL_REQUIRES_NIGHTLY"),
])
def test_spool_flag_combinations_that_blur_the_two_hosts_are_refused_before_any_read(
        tmp_path, monkeypatch, capsys, flags, token):
    world = _world(tmp_path)
    spool = _FakeSpool().install(monkeypatch)
    monkeypatch.setattr(capture, "resolve_board_as_of",
                        lambda *a, **k: pytest.fail("read before the mode check"))

    code = _run(monkeypatch, tmp_path, world, *flags)

    assert code == 3
    assert json.loads(capsys.readouterr().out)["refused"] == token
    assert spool.puts == [] and spool.lists == []
    assert not (tmp_path / _CAPTURE_REL).exists()


def test_spool_pass_refuses_a_live_root_override(tmp_path, monkeypatch, capsys):
    world = _world(tmp_path)
    spool = _FakeSpool().install(monkeypatch)
    code = _run(monkeypatch, tmp_path, world, "--spool", "--live-root", str(world["live_root"]))
    assert code == 3
    assert json.loads(capsys.readouterr().out)["refused"] == "LIVE_ROOT_OVERRIDE_FORBIDDEN_IN_SPOOL_MODE"
    assert spool.puts == []


def _spooled_world(tmp_path, monkeypatch, capsys, *, tickers=("UNIT", "UNIT2"), now=_PASS_AT):
    """A VPS-side pass into a fake spool; returns (spool, published object)."""
    world = _world(tmp_path / "vps", tickers=tickers)
    spool = _FakeSpool().install(monkeypatch)
    assert _run(monkeypatch, tmp_path / "vps", world, "--spool", now=now, lane=None) == 0
    key = json.loads(capsys.readouterr().out)["spool"]["key"]
    return spool, spool.objects[key]


def test_nightly_from_spool_is_the_sole_durable_advancer_and_is_idempotent(
        tmp_path, monkeypatch, capsys):
    spool, obj = _spooled_world(tmp_path, monkeypatch, capsys)
    mac = tmp_path / "mac"
    mac.mkdir()

    code = _ingest(monkeypatch, mac)

    assert code == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["mode"] == "nightly" and doc["source"] == "spool"
    assert doc["rows"] == doc["rows_written"] == 2
    assert doc["spool"]["objects"] == 1
    assert doc["spool"]["sessions"][_SESSION]["rows_written"] == 2
    assert spool.lists == [capture.SPOOL_PREFIX + "/"]
    target = _capture_file(mac)
    committed = _read_rows(target)
    # The committed rows are the VPS rows verbatim — the VPS pass clock is the
    # observation instant, never the nightly's.
    srt = lambda rows: sorted(rows, key=lambda r: capture._sort_key(capture._row_key_of(r)))
    assert [capture._row_body(r) for r in srt(committed)] == [capture._row_body(r) for r in srt(obj["rows"])]
    assert {r["captured_at"] for r in committed} == {_PASS_ISO}
    first_bytes = target.read_bytes()

    # Second nightly (a later clock, the same spool): keep-first, nothing rewritten.
    assert _ingest(monkeypatch, mac, now=_SECOND_CAPTURED_AT) == 0
    assert json.loads(capsys.readouterr().out)["rows_written"] == 0
    assert target.read_bytes() == first_bytes


def test_from_spool_refuses_a_malformed_or_smuggled_object_before_any_write(
        tmp_path, monkeypatch, capsys):
    spool, obj = _spooled_world(tmp_path, monkeypatch, capsys)
    good_key = next(iter(spool.objects))
    mac = tmp_path / "mac"
    mac.mkdir()

    def bad(label, mutate):
        clone = json.loads(json.dumps(obj))
        mutate(clone)
        spool.objects[f"{capture.SPOOL_PREFIX}/{_SESSION}/20260918T153000Z.json"] = clone
        code = _ingest(monkeypatch, mac)
        assert code == 3, label
        refusal = json.loads(capsys.readouterr().out)
        assert refusal["refused"] == "SPOOL_OBJECT_MALFORMED", label
        # The GOOD object in the same prefix was not written either: validation of
        # every object precedes the first write.
        assert not (mac / _CAPTURE_REL).exists(), label

    bad("wrong schema", lambda o: o.update(schema="prophet.b4.capture_spool/v0"))
    bad("foreign producer", lambda o: o.update(producer="someone_else.py"))
    bad("stamp mismatch", lambda o: o.update(stamp_date="2026-09-18"))
    bad("row without the closed key set", lambda o: o["rows"][0].pop("facts"))
    bad("row clock not the pass clock", lambda o: o["rows"][0].update(captured_at="2026-09-18T15:30:00Z"))
    bad("no pass date", lambda o: o.pop("pass_date"))
    bad("pass on a Saturday", lambda o: o.update(pass_date="2026-09-19"))
    bad("pass two sessions after the stamp", lambda o: o.update(pass_date="2026-09-21"))
    bad("pass before the stamp", lambda o: o.update(pass_date="2026-09-16"))
    bad("pass on the stamp day itself", lambda o: o.update(pass_date=_SESSION))

    def declared_date_not_the_clock(o):
        # A producer declaring the lawful pass_date while its instant is another day.
        o["captured_at"] = "2026-09-21T15:06:30Z"
        for row in o["rows"]:
            row["captured_at"] = o["captured_at"]
    bad("pass_date disagrees with captured_at", declared_date_not_the_clock)
    bad("captured_at without a zone", lambda o: o.update(captured_at="2026-09-18T15:06:30"))

    def smuggle(o):
        o["rows"][0]["facts"] = {"availability_state": "ENTRY_OPEN", "x": 1}
    bad("smuggled verdict in facts", smuggle)
    bad("not an object", lambda o: o.clear())
    assert good_key in spool.objects  # the fake never lost the good object


def test_from_spool_changed_body_under_a_committed_key_is_a_conflict_exit_2(
        tmp_path, monkeypatch, capsys):
    spool, obj = _spooled_world(tmp_path, monkeypatch, capsys, tickers=("UNIT",))
    mac = tmp_path / "mac"
    mac.mkdir()
    assert _ingest(monkeypatch, mac) == 0
    capsys.readouterr()
    target = _capture_file(mac)
    committed = target.read_bytes()

    # A later VPS pass (new object, same key, DIFFERENT body — a stale re-read, a
    # re-fired timer) is a SUPERSEDED observation: validated, recorded, never merged.
    # The stamp's observation is its EARLIEST pass, so the second pass can neither
    # win keep-first nor conflict with the first.
    later_key = f"{capture.SPOOL_PREFIX}/{_SESSION}/20260918T154000Z.json"
    later = json.loads(json.dumps(obj))
    later["captured_at"] = "2026-09-18T15:40:00Z"
    for row in later["rows"]:
        row["captured_at"] = later["captured_at"]
        row["unavailable_reasons"] = ["SOMETHING_ELSE"]
    spool.objects[later_key] = later

    assert _ingest(monkeypatch, mac) == 0
    doc = json.loads(capsys.readouterr().out)
    sess = doc["spool"]["sessions"][_SESSION]
    assert sess["objects"] == 2 and sess["superseded"] == [later_key]
    assert sess["observation"].endswith("/" + _PASS_OBJ)
    assert doc["rows_written"] == 0 and target.read_bytes() == committed

    # The committed day file disagreeing with the stamp's observation IS a conflict
    # (tampered or foreign-written history): exit 2, nothing rewritten.
    first_key = sess["observation"]
    tampered = json.loads(json.dumps(spool.objects[first_key]))
    for row in tampered["rows"]:
        row["unavailable_reasons"] = ["SOMETHING_ELSE"]
    spool.objects[first_key] = tampered

    code = _ingest(monkeypatch, mac)

    assert code == 2
    conflict = json.loads(capsys.readouterr().out)
    assert conflict["conflict"][0] == _SESSION
    assert target.read_bytes() == committed


def test_from_spool_plans_every_stamp_before_the_first_write(tmp_path, monkeypatch, capsys):
    """A conflict on the SECOND stamp leaves the first stamp unwritten: a nightly is
    all-or-nothing across day files, never a partial night."""
    spool, obj = _spooled_world(tmp_path, monkeypatch, capsys, tickers=("UNIT",))
    mac = tmp_path / "mac"
    mac.mkdir()
    assert _ingest(monkeypatch, mac) == 0
    capsys.readouterr()
    committed = _capture_file(mac).read_bytes()
    first_key = next(iter(spool.objects))
    tampered = json.loads(json.dumps(obj))
    for row in tampered["rows"]:
        row["unavailable_reasons"] = ["SOMETHING_ELSE"]
    spool.objects[first_key] = tampered
    older = json.loads(json.dumps(obj))
    older["stamp_date"] = "2026-09-16"
    older["pass_date"], older["captured_at"] = "2026-09-17", "2026-09-17T15:06:30Z"
    for row in older["rows"]:
        row["stamp_date"], row["captured_at"] = "2026-09-16", older["captured_at"]
    spool.objects[f"{capture.SPOOL_PREFIX}/2026-09-16/20260916T200500Z.json"] = older

    code = _ingest(monkeypatch, mac)

    assert code == 2
    assert json.loads(capsys.readouterr().out)["conflict"][0] == _SESSION
    assert not _capture_file(mac, "2026-09-16").exists()
    assert _capture_file(mac).read_bytes() == committed


def test_from_spool_refuses_when_the_listing_fails_instead_of_reporting_an_empty_spool(
        tmp_path, monkeypatch, capsys):
    spool = _FakeSpool(list_fail=True).install(monkeypatch)
    mac = tmp_path / "mac"
    mac.mkdir()

    code = _ingest(monkeypatch, mac)

    assert code == 3
    refusal = json.loads(capsys.readouterr().out)
    assert refusal["refused"] == "SPOOL_LIST_FAILED"
    assert not (mac / _CAPTURE_REL).exists()
    assert spool.puts == []


def test_from_spool_without_r2_credentials_is_a_typed_refusal(tmp_path, monkeypatch, capsys):
    spool = _FakeSpool(client=False).install(monkeypatch)
    mac = tmp_path / "mac"
    mac.mkdir()
    code = _ingest(monkeypatch, mac)
    assert code == 3
    assert json.loads(capsys.readouterr().out)["refused"] == "SPOOL_CLIENT_UNAVAILABLE"
    assert spool.lists == []
    assert not (mac / _CAPTURE_REL).exists()


def test_from_spool_with_an_empty_spool_is_a_valid_state_exit_0_and_writes_nothing(
        tmp_path, monkeypatch, capsys):
    _FakeSpool().install(monkeypatch)
    mac = tmp_path / "mac"
    mac.mkdir()
    code = _ingest(monkeypatch, mac)
    assert code == 0
    captured = capsys.readouterr()
    assert "capture spool is empty" in captured.err
    doc = json.loads(captured.out)
    assert doc["rows"] == doc["rows_written"] == 0 and doc["spool"]["objects"] == 0
    assert not (mac / _CAPTURE_REL).exists()


def test_from_spool_is_lane_gated_and_lists_nothing_when_unarmed(tmp_path, monkeypatch, capsys):
    spool = _FakeSpool().install(monkeypatch)
    mac = tmp_path / "mac"
    mac.mkdir()
    code = _ingest(monkeypatch, mac, lane=None)
    assert code == 3
    assert json.loads(capsys.readouterr().out)["refused"] == "NIGHTLY_LANE_NOT_ARMED"
    assert spool.lists == []


def test_from_spool_dry_run_reads_everything_and_writes_nothing(tmp_path, monkeypatch, capsys):
    _spooled_world(tmp_path, monkeypatch, capsys)
    mac = tmp_path / "mac"
    mac.mkdir()
    code = _ingest(monkeypatch, mac, "--dry-run", lane=None)
    assert code == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["mode"] == "dry-run" and doc["rows"] == 2 and doc["rows_written"] == 0
    assert not (mac / _CAPTURE_REL).exists()


def test_from_spool_bounds_the_sessions_read_and_ignores_foreign_keys(
        tmp_path, monkeypatch, capsys):
    spool, obj = _spooled_world(tmp_path, monkeypatch, capsys, tickers=("UNIT",))
    # An older session's object, and junk under the prefix that is not a pass object.
    older = json.loads(json.dumps(obj))
    older["stamp_date"] = "2026-09-16"
    older["pass_date"], older["captured_at"] = "2026-09-17", "2026-09-17T15:06:30Z"
    for row in older["rows"]:
        row["stamp_date"], row["captured_at"] = "2026-09-16", older["captured_at"]
    spool.objects[f"{capture.SPOOL_PREFIX}/2026-09-16/20260916T200500Z.json"] = older
    spool.objects[f"{capture.SPOOL_PREFIX}/README.txt"] = "not a pass"
    spool.objects[f"{capture.SPOOL_PREFIX}/2026-09-16/nested/x.json"] = {}
    # Prefixes that are not calendar stamps are never path components nor sessions:
    # a traversal, a date-shaped-but-invalid prefix, a late sort-order prefix.
    spool.objects[f"{capture.SPOOL_PREFIX}/../x.json"] = older
    spool.objects[f"{capture.SPOOL_PREFIX}/2026-13-40/x.json"] = older
    spool.objects[f"{capture.SPOOL_PREFIX}/zzzz-latest/x.json"] = older
    mac = tmp_path / "mac"
    mac.mkdir()

    # Window of ONE session, but 2026-09-16 has no committed day file: a backlog is
    # ingested, never aged out unread.  Foreign prefixes are counted and ignored.
    assert _ingest(monkeypatch, mac, "--spool-sessions", "1") == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["spool"]["stamps_seen"] == ["2026-09-16", _SESSION]
    assert doc["spool"]["stamps_selected"] == ["2026-09-16", _SESSION]
    assert doc["spool"]["stamps_aged_out"] == [] and doc["spool"]["foreign_keys"] == 5
    assert _capture_file(mac, "2026-09-16").exists() and _capture_file(mac).exists()
    # Nothing escaped the capture directory and nothing landed under a foreign prefix.
    written = sorted(p.relative_to(mac / _CAPTURE_REL).as_posix()
                     for p in (mac / _CAPTURE_REL).rglob("*") if p.is_file())
    assert written == [_capture_file(mac, "2026-09-16").relative_to(mac / _CAPTURE_REL).as_posix(),
                       _capture_file(mac).relative_to(mac / _CAPTURE_REL).as_posix()]
    assert not (mac / "x.json").exists() and not (mac / "data" / "us_prophet_rank" / "x.json").exists()

    # Now 2026-09-16 is landed: with a window of one it is aged out of the READ (a
    # later pass under it would be superseded anyway) and only 09-17 is re-checked.
    assert _ingest(monkeypatch, mac, "--spool-sessions", "1") == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["spool"]["stamps_selected"] == [_SESSION]
    assert doc["spool"]["stamps_aged_out"] == ["2026-09-16"]
    assert doc["rows_written"] == 0

    # Window 0 = every stamp.
    assert _ingest(monkeypatch, mac, "--spool-sessions", "0") == 0
    doc = json.loads(capsys.readouterr().out)
    assert list(doc["spool"]["sessions"]) == ["2026-09-16", _SESSION]


def test_spool_pass_refuses_a_holiday_and_a_stale_board_before_any_live_read(
        tmp_path, monkeypatch, capsys):
    world = _world(tmp_path, tickers=("UNIT",))
    spool = _FakeSpool().install(monkeypatch)

    # Thanksgiving 2026 is a Thursday: the timer fires, the pass refuses.
    code = _run(monkeypatch, tmp_path, world, "--spool", lane=None,
                now=datetime(2026, 11, 26, 15, 6, 30, tzinfo=timezone.utc))
    assert code == 3
    assert json.loads(capsys.readouterr().out)["refused"] == "NOT_A_SESSION"

    # Monday 2026-09-21 with a board still stamped Thu 09-17 (Fri 09-18's nightly
    # never landed here): two sessions old, refused.
    code = _run(monkeypatch, tmp_path, world, "--spool", lane=None,
                now=datetime(2026, 9, 21, 15, 6, 30, tzinfo=timezone.utc))
    assert code == 3
    refusal = json.loads(capsys.readouterr().out)
    assert refusal["refused"] == "STALE_BOARD_STAMP"
    assert "2026-09-18" in refusal["message"]

    # The stamp day itself, mid-session: a board stamped D while D is open can only
    # be an anomalous render; it must not become D's observation and sort first.
    code = _run(monkeypatch, tmp_path, world, "--spool", lane=None, now=_FIRST_CAPTURED_AT)
    assert code == 3
    assert json.loads(capsys.readouterr().out)["refused"] == "STALE_BOARD_STAMP"
    assert spool.puts == [] and not (tmp_path / _CAPTURE_REL).exists()


def test_spool_pass_reads_the_board_once_so_a_mid_pass_rerender_cannot_split_it(
        tmp_path, monkeypatch, capsys):
    world = _world(tmp_path, tickers=("UNIT",))
    spool = _FakeSpool().install(monkeypatch)
    real = capture.resolve_board_as_of
    reads = []

    def counting_board(root):
        reads.append(1)
        return real(root)
    monkeypatch.setattr(capture, "resolve_board_as_of", counting_board)

    assert _run(monkeypatch, tmp_path, world, "--spool", lane=None, now=_PASS_AT) == 0
    assert len(reads) == 1
    obj = next(iter(spool.objects.values()))
    assert obj["stamp_date"] == _SESSION and json.loads(capsys.readouterr().out)["spool"]["published"]


def test_spool_pass_reads_the_clock_once(tmp_path, monkeypatch, capsys):
    world = _world(tmp_path, tickers=("UNIT",))
    spool = _FakeSpool().install(monkeypatch)
    calls = []

    def ticking():
        calls.append(1)
        return _PASS_AT
    monkeypatch.delenv("COLLECT_LANE", raising=False)
    monkeypatch.delenv("US_LANE", raising=False)
    monkeypatch.setattr(capture, "_now", ticking)
    monkeypatch.setattr(capture, "NATIVE_LIVE_ROOT", world["live_root"])
    _pin_clocks(monkeypatch)

    assert capture.main(["--root", str(tmp_path), "--spool"]) == 0
    assert len(calls) == 1
    obj = next(iter(spool.objects.values()))
    assert obj["pass_date"] == "2026-09-18" and obj["captured_at"] == _PASS_ISO


def test_spool_session_rule_admits_the_stamp_session_and_the_next_session_only():
    thu, fri, mon = date(2026, 9, 17), date(2026, 9, 18), date(2026, 9, 21)
    assert not capture._stamp_is_lawful_for_pass(thu, thu)      # same day: the nightly runs AFTER the close
    assert capture._stamp_is_lawful_for_pass(thu, fri)          # the next session (the only lawful case)
    assert not capture._stamp_is_lawful_for_pass(thu, mon)      # two sessions old
    assert not capture._stamp_is_lawful_for_pass(fri, thu)      # board ahead of the clock
    assert not capture._stamp_is_lawful_for_pass(thu, date(2026, 9, 19))   # Saturday
    assert not capture._stamp_is_lawful_for_pass(date(2026, 11, 25), date(2026, 11, 26))  # holiday
    assert capture._stamp_is_lawful_for_pass(date(2026, 11, 25), date(2026, 11, 27))      # over the holiday


def test_docstring_names_the_two_host_design_and_both_entrypoints():
    text = capture.__doc__
    assert "TWO HOSTS, ONE STREAM" in text
    assert "--spool" in text and "--nightly --from-spool" in text
    assert "writes NOTHING under" in text

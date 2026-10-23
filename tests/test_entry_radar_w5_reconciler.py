"""W5 §8/§17 — the nightly reconciler's write discipline.

EVERY test here runs against a ``tmp_path`` root.  The reconciler's whole job is
writing durable evidence, so a suite that let it touch the real
``data/entry_radar/`` or ``data/qledger/`` would be writing production claims
from CI — the exact single-writer violation the script exists to prevent.

WHAT IS BEING PINNED, in order of how badly it would hurt to lose it:

  1. **The gate refuses ALWAYS and writes NOTHING.**  Not "writes the safe
     subset" — a partial artifact from a lane error is worse than none, because
     it is indistinguishable from a healthy pass to every instrument we own.
  2. **No spool ⇒ WAITING_FOR_LIVE_SOURCE and zero rows.**  The failure mode
     this forecloses is a reconciler that, finding no live stream, quietly
     replays nightly artifacts into plausible "observations".
  3. **No epoch ⇒ recorded but never registered.**  §8 forbids relabelling a
     row's live-forward status afterwards, so registering early is irreversible.
  4. **Re-runs are idempotent.**  Append-only means the second pass adds nothing
     and moves nothing.
"""
from __future__ import annotations

import json

import pytest

from engine.entry_radar.replay import prereg
from scripts import reconcile_entry_radar as rec


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _event(ticker: str = "ABCD", detector: str = "C2_1D_TURN@1", *,
           session: str = "2026-08-14",
           observed_at: str = "2026-08-14T20:05:00+00:00",
           event_id: str | None = None) -> dict:
    return {
        "schema": rec.SPOOL_EVENT_SCHEMA,
        "record": {
            "event_id": event_id or f"{ticker}-{detector}-{session}",
            "producer": "entry_radar",
            "detector_id": detector,
            "ticker": ticker,
            "family": "radar_turn",
            "subtype": "c2_turn",
            "context": {"market_session": session},
            "signal_ts": f"{session}T19:55:00+00:00",
            "signal_known_ts": f"{session}T20:00:00+00:00",
            "observed_at": observed_at,
            "bar_state": "confirmed",
            "final": True,
            "source_identity": {"detector_spec_hash":
                                prereg.EXPECTED_SPEC_HASHES[detector]},
        },
    }


def _write_spool(directory, events) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "2026-08-14.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")


def _state(root):
    path = root / "data" / "entry_radar" / rec.LEDGER_STATE_NAME
    return json.loads(path.read_text(encoding="utf-8"))


def _entry_radar_files(root) -> set[str]:
    out = root / "data" / "entry_radar"
    if not out.is_dir():
        return set()
    return {p.name for p in out.iterdir() if not p.name.startswith(".")}


@pytest.fixture()
def nightly(monkeypatch):
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    monkeypatch.delenv(rec.SPOOL_DIR_ENV, raising=False)


@pytest.fixture()
def lane_down(monkeypatch):
    monkeypatch.delenv("COLLECT_LANE", raising=False)
    monkeypatch.delenv("US_LANE", raising=False)
    monkeypatch.delenv(rec.SPOOL_DIR_ENV, raising=False)


# =========================================================================== #
# 1 — the hard gate
# =========================================================================== #
def test_nightly_outside_the_lane_exits_2_and_writes_nothing(tmp_path, lane_down):
    rc = rec.main(["--root", str(tmp_path), "--nightly"])
    assert rc == 2
    assert not (tmp_path / "data").exists(), (
        "a refused nightly must not create even the output directory")


def test_gate_refusal_precedes_intake(tmp_path, lane_down, monkeypatch, capsys):
    """The refusal cannot depend on what the spool happened to contain tonight.

    MUTATION CONTROL: move the gate below ``read_spool_events`` and this passes
    only by accident — so the assertion is on the ANNOTATION, which names the
    lane, not on the (also-empty) output.
    """
    spool = tmp_path / "spool"
    _write_spool(spool, [_event()])
    monkeypatch.setenv(rec.SPOOL_DIR_ENV, str(spool))
    assert rec.main(["--root", str(tmp_path), "--nightly"]) == 2
    out = capsys.readouterr().out
    assert "::warning title=entry-radar-reconcile::" in out
    assert "COLLECT_LANE!=nightly" in out and "NOTHING written" in out
    assert not (tmp_path / "data").exists()


def test_every_annotation_starts_the_line_and_is_a_bare_print(tmp_path, lane_down,
                                                              capsys):
    """House law: a ``::warning`` emitted through a logger is silently dropped."""
    rec.main(["--root", str(tmp_path), "--nightly"])
    for line in capsys.readouterr().out.splitlines():
        if "::warning" in line or "::error" in line or "::notice" in line:
            assert line.startswith("::"), f"annotation not at line start: {line!r}"


# =========================================================================== #
# 2 — no spool ⇒ WAITING_FOR_LIVE_SOURCE
# =========================================================================== #
def test_no_spool_writes_only_the_waiting_state(tmp_path, nightly):
    assert rec.main(["--root", str(tmp_path), "--nightly", "--verbose"]) == 0
    state = _state(tmp_path)
    assert state["schema"] == rec.LEDGER_STATE_SCHEMA
    assert state["state"] == prereg.WAITING_FOR_LIVE_SOURCE
    assert state["live_forward_start"] is None
    assert state["observed_spool_events"] == 0
    assert state["session"] and state["updated_at"]
    # No forward rows, and above all no claims: nothing was observed, so nothing
    # may be asserted about anything.
    assert rec.FORWARD_NAME not in _entry_radar_files(tmp_path)
    assert not (tmp_path / "data" / "qledger").exists()


def test_no_spool_writes_nothing_outside_DURABLE_WRITES(tmp_path, nightly):
    """The declared list is the complete list, not a sample of it."""
    rec.main(["--root", str(tmp_path), "--nightly"])
    declared = {p.rsplit("/", 1)[-1] for p in rec.DURABLE_WRITES}
    assert _entry_radar_files(tmp_path) <= declared


def test_session_stamp_is_a_real_session_not_the_wall_clock(tmp_path, nightly):
    """A date the market never opened is a join key no outcome can attach to."""
    from datetime import date as _date

    from lib.nyse_calendar import is_session

    rec.main(["--root", str(tmp_path), "--nightly"])
    session = _state(tmp_path)["session"]
    assert is_session(_date.fromisoformat(session)), \
        f"{session} is not an NYSE session"


# =========================================================================== #
# 3 — idempotency
# =========================================================================== #
def test_rerun_is_idempotent_with_no_spool(tmp_path, nightly):
    rec.main(["--root", str(tmp_path), "--nightly"])
    first = _state(tmp_path)
    rec.main(["--root", str(tmp_path), "--nightly"])
    second = _state(tmp_path)
    # `updated_at` is excluded ON PURPOSE: it stamps WHEN the pass ran, and is
    # the one field that must move. Every field that makes a CLAIM about the
    # evidence is compared, and none of them may move on a re-run.
    assert {k: v for k, v in first.items() if k != "updated_at"} == \
           {k: v for k, v in second.items() if k != "updated_at"}


def test_rerun_appends_no_duplicate_forward_rows(tmp_path, nightly, monkeypatch):
    spool = tmp_path / "spool"
    _write_spool(spool, [_event("AAA"), _event("BBB")])
    monkeypatch.setenv(rec.SPOOL_DIR_ENV, str(spool))

    rec.main(["--root", str(tmp_path), "--nightly"])
    forward = tmp_path / "data" / "entry_radar" / rec.FORWARD_NAME
    first_bytes = forward.read_bytes()
    assert _state(tmp_path)["forward_rows_total"] == 2

    rec.main(["--root", str(tmp_path), "--nightly"])
    assert _state(tmp_path)["forward_rows_total"] == 2
    assert _state(tmp_path)["forward_rows_appended"] == 0
    # Nothing new ⇒ the file is not rewritten at all, so the stored rows are
    # byte-identical rather than merely value-identical.
    assert forward.read_bytes() == first_bytes


def test_a_new_event_appends_without_disturbing_the_stored_rows(tmp_path, nightly,
                                                                monkeypatch):
    import pandas as pd

    spool = tmp_path / "spool"
    _write_spool(spool, [_event("AAA")])
    monkeypatch.setenv(rec.SPOOL_DIR_ENV, str(spool))
    rec.main(["--root", str(tmp_path), "--nightly"])
    forward = tmp_path / "data" / "entry_radar" / rec.FORWARD_NAME
    before = pd.read_parquet(forward)

    _write_spool(spool, [_event("AAA"), _event("BBB")])
    rec.main(["--root", str(tmp_path), "--nightly"])
    after = pd.read_parquet(forward)

    assert len(after) == 2 and _state(tmp_path)["forward_rows_appended"] == 1
    # Keep-first: the original row's VALUES survive the append untouched.
    pd.testing.assert_frame_equal(after.iloc[:1].reset_index(drop=True),
                                  before.reset_index(drop=True))


# =========================================================================== #
# 4 — spool present, epoch unset  (the state PR-5b inherits)
# =========================================================================== #
def test_events_are_recorded_but_never_registered_while_the_epoch_is_unset(
        tmp_path, nightly, monkeypatch):
    # The live module is stamped (epoch = the merged PR-5a instant); the
    # pre-stamp None state is reconstructed here because its BEHAVIOR — record
    # everything, register nothing — must stay pinned forever.
    monkeypatch.setattr(rec, "LIVE_FORWARD_EPOCH", None)
    spool = tmp_path / "spool"
    _write_spool(spool, [_event("AAA"), _event("BBB", "G0_GREY_DOT@1")])
    monkeypatch.setenv(rec.SPOOL_DIR_ENV, str(spool))

    assert rec.main(["--root", str(tmp_path), "--nightly"]) == 0
    state = _state(tmp_path)
    assert state["observed_spool_events"] == 2
    assert state["forward_rows_total"] == 2
    # RECORDED (nothing is lost) ...
    assert state["state"] == prereg.WAITING_FOR_LIVE_SOURCE
    assert state["live_forward_start"] is None
    assert state["live_forward_rows"] == 0
    # ... and REGISTERED NOWHERE: an early registration is irreversible.
    assert not (tmp_path / "data" / "qledger").exists()
    assert rec.REGISTRATION_LOG_NAME not in _entry_radar_files(tmp_path)


def test_rows_recorded_under_an_unset_epoch_carry_the_waiting_state(tmp_path,
                                                                    nightly,
                                                                    monkeypatch):
    import pandas as pd

    spool = tmp_path / "spool"
    _write_spool(spool, [_event("AAA")])
    monkeypatch.setenv(rec.SPOOL_DIR_ENV, str(spool))
    rec.main(["--root", str(tmp_path), "--nightly"])
    frame = pd.read_parquet(tmp_path / "data" / "entry_radar" / rec.FORWARD_NAME)
    assert set(frame["state"]) == {rec.STATE_WAITING}
    assert frame["observed_at_basis"].iloc[0] == "spool_envelope"


def test_live_forward_eligible_is_false_for_every_row_without_an_epoch():
    row = {"observed_at": "2030-01-01T00:00:00+00:00"}
    assert rec.live_forward_eligible(row, epoch=None) is False
    # CONTROL: with an epoch, the same row IS eligible — the None answer above
    # is the epoch's doing, not a function that always says no.
    assert rec.live_forward_eligible(row, epoch="2026-01-01T00:00:00+00:00") is True


def test_an_event_at_or_before_the_epoch_is_never_live_forward():
    epoch = "2026-08-14T12:00:00+00:00"
    assert rec.live_forward_eligible({"observed_at": epoch}, epoch=epoch) is False
    assert rec.live_forward_eligible(
        {"observed_at": "2026-08-14T11:59:59+00:00"}, epoch=epoch) is False
    assert rec.live_forward_eligible(
        {"observed_at": "2026-08-14T12:00:01+00:00"}, epoch=epoch) is True


# =========================================================================== #
# 5 — dry-run and report-only
# =========================================================================== #
def test_dry_run_writes_nothing(tmp_path, nightly, monkeypatch):
    spool = tmp_path / "spool"
    _write_spool(spool, [_event()])
    monkeypatch.setenv(rec.SPOOL_DIR_ENV, str(spool))
    assert rec.main(["--root", str(tmp_path), "--nightly", "--dry-run"]) == 0
    assert not (tmp_path / "data").exists()


def test_without_nightly_nothing_is_written_even_inside_the_lane(tmp_path, nightly,
                                                                 monkeypatch):
    """The single-advancer law has no 'just the state file' exception."""
    spool = tmp_path / "spool"
    _write_spool(spool, [_event()])
    monkeypatch.setenv(rec.SPOOL_DIR_ENV, str(spool))
    assert rec.main(["--root", str(tmp_path)]) == 0
    assert not (tmp_path / "data").exists()


# =========================================================================== #
# 6 — registration, once an epoch exists (§17)
# =========================================================================== #
def test_live_forward_rows_register_into_the_injected_root(tmp_path, nightly,
                                                           monkeypatch):
    """CONTROL for the 'never registered' tests above — with a lawful epoch the
    same machinery DOES register, so those assertions are about the epoch."""
    monkeypatch.setattr(rec, "LIVE_FORWARD_EPOCH", "2026-01-01T00:00:00+00:00")
    spool = tmp_path / "spool"
    _write_spool(spool, [_event("AAA")])
    monkeypatch.setenv(rec.SPOOL_DIR_ENV, str(spool))

    assert rec.main(["--root", str(tmp_path), "--nightly"]) == 0
    state = _state(tmp_path)
    assert state["state"] == "LIVE_FORWARD_ACCRUING"
    assert state["live_forward_rows"] == 1
    assert state["live_forward_start"] == "2026-08-14"
    assert state["qledger"]["registered"] == 1

    claims = (tmp_path / "data" / "qledger" / "claims.jsonl")
    assert claims.exists(), "registration must land in the INJECTED root only"
    rows = [json.loads(x) for x in claims.read_text().splitlines() if x.strip()]
    assert len(rows) == 1
    claim = rows[0]
    assert claim["horizon_d"] == prereg.QLEDGER_HORIZON_D == 21
    assert claim["horizon_unit"] == "trading_days"
    assert claim["claim_family"] == "entry_radar_C2_1D_TURN@1"
    assert claim["desk"] == prereg.QLEDGER_DESK
    assert claim["authority"] == prereg.AUTHORITY
    assert claim["registration_note"] == prereg.REGISTRATION_NOTE
    assert "DNR:KILL-WASHOUT-TURN" in str(claim["falsifier"])


def test_registration_is_keep_first_across_reruns(tmp_path, nightly, monkeypatch):
    monkeypatch.setattr(rec, "LIVE_FORWARD_EPOCH", "2026-01-01T00:00:00+00:00")
    spool = tmp_path / "spool"
    _write_spool(spool, [_event("AAA")])
    monkeypatch.setenv(rec.SPOOL_DIR_ENV, str(spool))
    rec.main(["--root", str(tmp_path), "--nightly"])
    rec.main(["--root", str(tmp_path), "--nightly"])

    log = (tmp_path / "data" / "entry_radar" / rec.REGISTRATION_LOG_NAME)
    entries = [json.loads(x) for x in log.read_text().splitlines() if x.strip()]
    assert len(entries) == 1, "a second pass must not re-log a latched episode"
    claims = (tmp_path / "data" / "qledger" / "claims.jsonl")
    assert len([x for x in claims.read_text().splitlines() if x.strip()]) == 1


def test_c4_is_recorded_but_never_registered(tmp_path, nightly, monkeypatch):
    """§17: C4 is stratification-only, so a directional claim for it would be
    fabricated symmetry.  It still gets a forward row — recording is not
    endorsement."""
    import pandas as pd

    monkeypatch.setattr(rec, "LIVE_FORWARD_EPOCH", "2026-01-01T00:00:00+00:00")
    spool = tmp_path / "spool"
    _write_spool(spool, [_event("AAA", "C4_MTF_TURN@1")])
    monkeypatch.setenv(rec.SPOOL_DIR_ENV, str(spool))

    assert rec.main(["--root", str(tmp_path), "--nightly"]) == 0
    frame = pd.read_parquet(tmp_path / "data" / "entry_radar" / rec.FORWARD_NAME)
    assert len(frame) == 1 and frame["detector_id"].iloc[0] == "C4_MTF_TURN@1"
    assert not (tmp_path / "data" / "qledger").exists()
    assert _state(tmp_path)["live_forward_rows"] == 0


def test_build_claims_refuses_a_non_live_forward_row(tmp_path):
    """The separation is enforced where the claim is BUILT, not only where the
    caller filters — one filter is one place to forget."""
    row = {"state": rec.STATE_WAITING, "detector_id": "C2_1D_TURN@1",
           "ticker": "AAA", "decision_session": "2026-08-14",
           "episode_address": "x"}
    with pytest.raises(AssertionError, match="LIVE-FORWARD"):
        rec.build_claims([row], root=tmp_path)


def test_build_claims_refuses_a_never_register_detector(tmp_path):
    row = {"state": rec.STATE_LIVE_FORWARD, "detector_id": "F1_FUSION",
           "ticker": "AAA", "decision_session": "2026-08-14",
           "episode_address": "x"}
    with pytest.raises(AssertionError, match="never be registered"):
        rec.build_claims([row], root=tmp_path)


def test_registration_outcome_is_fail_closed():
    """A slot that persisted nothing must never be logged as registered."""
    assert rec._registration_outcome(None) == rec._OUTCOME_FAILED
    assert rec._registration_outcome({"status": "error", "error": "x"}) == \
        rec._OUTCOME_FAILED
    assert rec._registration_outcome({"status": "open"}) == rec._OUTCOME_FAILED
    assert rec._registration_outcome({"status": "rejected", "claim_id": "z"}) == \
        rec._OUTCOME_REJECTED
    assert rec._registration_outcome({"status": "open", "claim_id": "z"}) == \
        rec._OUTCOME_REGISTERED


# =========================================================================== #
# 7 — intake hygiene
# =========================================================================== #
def test_off_schema_and_torn_records_are_skipped_never_repaired(tmp_path, nightly,
                                                                monkeypatch, capsys):
    spool = tmp_path / "spool"
    spool.mkdir(parents=True)
    (spool / "mixed.jsonl").write_text(
        json.dumps(_event("AAA")) + "\n"
        + json.dumps({"schema": "something.else/v1", "record": {"ticker": "ZZZ"}}) + "\n"
        + '{"schema": "mastermind.entry_ev\n', encoding="utf-8")
    monkeypatch.setenv(rec.SPOOL_DIR_ENV, str(spool))

    rec.main(["--root", str(tmp_path), "--nightly"])
    assert _state(tmp_path)["observed_spool_events"] == 1
    assert "were SKIPPED" in capsys.readouterr().out


def test_episode_address_is_stable_across_passes():
    """The join key may never contain a wall-clock field, or every re-run
    appends a 'new' episode and the ledger grows without bound."""
    ev = _event("AAA")["record"]
    assert rec.episode_address(ev) == rec.episode_address(dict(ev))
    no_id = {k: v for k, v in ev.items() if k != "event_id"}
    assert rec.episode_address(no_id) == "AAA|C2_1D_TURN@1|2026-08-14"

# =========================================================================== #
# Phase22 DFII10 prospective PIT receipt — Rates owner -> existing W5 consumer
# =========================================================================== #
import copy
import json
from pathlib import Path

import pandas as pd
import pytest

from engine.rate_inflation_receipt import (
    DFII10_BUNDLE_SCHEMA,
    DFII10_CONTEXT_SCHEMA,
    DFII10_RECEIPT_SCHEMA,
    MEASUREMENT_ONLY_AUTHORITY,
    bind_dfii10_context,
    build_dfii10_five_session_receipt,
    build_dfii10_owner_bundle,
    build_dfii10_receipt_bundle,
    capture_dfii10_receipt,
    flatten_dfii10_context,
    load_dfii10_bundle,
    select_dfii10_series,
)


def sessions(*days: str):
    return [pd.Timestamp(day).date() for day in days]


LABOR_DAY_WINDOW = sessions(
    "2026-08-31", "2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04",
    "2026-09-08",  # 09-07 Labor Day is not a completed NYSE session.
)


def series(values: dict[str, float]) -> pd.Series:
    return pd.Series(values, dtype=float).rename_axis("date")


def qualified_receipt(*, captured="2026-09-08T22:00:00Z", sha="a" * 64,
                      previous=None):
    return build_dfii10_five_session_receipt(
        series({
            "2026-08-31": 1.90,
            "2026-09-01": 1.89,
            "2026-09-02": 1.88,
            "2026-09-03": 1.87,
            "2026-09-04": 1.86,
            "2026-09-08": 1.84,
        }),
        completed_sessions=LABOR_DAY_WINDOW,
        captured_at=captured,
        source_content_sha256=sha,
        source_column="DFII10",
        previous_receipt=previous,
    )


def test_exact_five_completed_sessions_skip_holiday_and_have_zero_authority():
    receipt = qualified_receipt()
    assert receipt["schema"] == DFII10_RECEIPT_SCHEMA
    assert receipt["status"] == "QUALIFIED"
    assert receipt["latest"] == {"observation_date": "2026-09-08", "value_pct": 1.84}
    assert receipt["prior_five_sessions"] == {
        "observation_date": "2026-08-31", "value_pct": 1.90}
    assert receipt["bound_session_window"] == [day.isoformat() for day in LABOR_DAY_WINDOW]
    assert receipt["delta_bp"] == -6.0
    assert receipt["stale_state"] == "CURRENT_AT_CAPTURE"
    assert receipt["measurement_only"] is True
    assert receipt["authority"] == MEASUREMENT_ONLY_AUTHORITY
    assert not any(receipt["authority"].values())


def test_exact_prior_endpoint_is_never_filled_or_inferred():
    receipt = build_dfii10_five_session_receipt(
        series({
            "2026-09-01": 1.89,
            "2026-09-02": 1.88,
            "2026-09-03": 1.87,
            "2026-09-04": 1.86,
            "2026-09-08": 1.84,
        }),
        completed_sessions=LABOR_DAY_WINDOW,
        captured_at="2026-09-08T22:00:00Z",
        source_content_sha256="b" * 64,
    )
    assert receipt["status"] == "MISSING"
    assert receipt["missing_state"] == "EXACT_PRIOR_ENDPOINT_MISSING"
    assert receipt["prior_five_sessions"] is None
    assert receipt["delta_bp"] is None


def test_stale_source_is_explicit_and_not_promoted_to_qualified():
    completed = sessions("2026-08-28") + LABOR_DAY_WINDOW
    receipt = build_dfii10_five_session_receipt(
        series({
            "2026-08-28": 1.91,
            "2026-08-31": 1.90,
            "2026-09-01": 1.89,
            "2026-09-02": 1.88,
            "2026-09-03": 1.87,
            "2026-09-04": 1.86,
        }),
        completed_sessions=completed,
        captured_at="2026-09-08T22:00:00Z",
        source_content_sha256="c" * 64,
    )
    assert receipt["status"] == "STALE"
    assert receipt["completed_session_lag"] == 1
    assert receipt["stale_state"] == "STALE_AT_CAPTURE"


def test_exact_retry_preserves_earliest_conservative_first_known_time():
    first = qualified_receipt(captured="2026-09-08T22:00:00Z")
    replay = qualified_receipt(
        captured="2026-09-09T01:00:00Z", previous=first)
    assert replay["source_snapshot_hash"] == first["source_snapshot_hash"]
    assert replay["capture"]["captured_at"] == "2026-09-09T01:00:00Z"
    assert replay["capture"]["first_known_at"] == "2026-09-08T22:00:00Z"


def test_endpoint_revision_is_bound_as_a_correction_not_hidden():
    first = qualified_receipt()
    corrected = build_dfii10_five_session_receipt(
        series({
            "2026-08-31": 1.91,
            "2026-09-01": 1.89,
            "2026-09-02": 1.88,
            "2026-09-03": 1.87,
            "2026-09-04": 1.86,
            "2026-09-08": 1.84,
        }),
        completed_sessions=LABOR_DAY_WINDOW,
        captured_at="2026-09-09T02:00:00Z",
        source_content_sha256="d" * 64,
        previous_receipt=first,
    )
    assert corrected["correction"]["state"] == "BOUND_ENDPOINT_CORRECTION_DETECTED"
    assert corrected["correction"]["corrected_endpoints"] == [{
        "endpoint": "prior_five_sessions",
        "observation_date": "2026-08-31",
        "previous_value_pct": 1.9,
        "current_value_pct": 1.91,
    }]
    assert corrected["delta_bp"] == -7.0


def test_bundle_keeps_current_plus_exactly_one_prior_qualified_receipt():
    old = qualified_receipt(captured="2026-09-08T22:00:00Z", sha="a" * 64)
    old_bundle = build_dfii10_receipt_bundle(old)
    through_sep9 = LABOR_DAY_WINDOW + sessions("2026-09-09")
    new = build_dfii10_five_session_receipt(
        series({
            "2026-08-31": 1.90, "2026-09-01": 1.89, "2026-09-02": 1.88,
            "2026-09-03": 1.87, "2026-09-04": 1.86, "2026-09-08": 1.84,
            "2026-09-09": 1.82,
        }),
        completed_sessions=through_sep9,
        captured_at="2026-09-09T22:00:00Z",
        source_content_sha256="e" * 64,
    )
    bundle = build_dfii10_receipt_bundle(new, old_bundle)
    assert bundle["schema"] == DFII10_BUNDLE_SCHEMA
    assert bundle["current"]["source_snapshot_hash"] == new["source_snapshot_hash"]
    assert bundle["previous_qualified"]["source_snapshot_hash"] == \
        old["source_snapshot_hash"]
    assert bundle["history_policy"] == "current_plus_one_prior_qualified_no_backfill"
    assert not any(bundle["authority"].values())


def test_consumer_uses_prior_receipt_known_at_intraday_decision_cut():
    prior = qualified_receipt(captured="2026-09-08T22:00:00Z")
    through_sep9 = LABOR_DAY_WINDOW + sessions("2026-09-09")
    current = build_dfii10_five_session_receipt(
        series({
            "2026-08-31": 1.90,
            "2026-09-01": 1.89,
            "2026-09-02": 1.88,
            "2026-09-03": 1.87,
            "2026-09-04": 1.86,
            "2026-09-08": 1.84,
            "2026-09-09": 1.82,
        }),
        completed_sessions=through_sep9,
        captured_at="2026-09-09T22:00:00Z",
        source_content_sha256="e" * 64,
        source_column="DFII10",
        previous_receipt=prior,
    )
    bundle = build_dfii10_receipt_bundle(
        current, build_dfii10_receipt_bundle(prior)
    )
    context = bind_dfii10_context(
        bundle,
        decision_known_at="2026-09-09T19:30:00Z",
        decision_session="2026-09-09",
        completed_sessions=LABOR_DAY_WINDOW + sessions("2026-09-09"),
    )
    assert context["schema"] == DFII10_CONTEXT_SCHEMA
    assert context["status"] == "QUALIFIED"
    assert context["source_snapshot_hash"] == prior["source_snapshot_hash"]
    assert context["receipt_age_completed_sessions"] == 1
    assert context["delta_bp"] == -6.0
    assert not any(context["authority"].values())


def test_consumer_refuses_not_yet_known_and_too_stale_receipts():
    current = qualified_receipt(captured="2026-09-09T22:00:00Z")
    context = bind_dfii10_context(
        build_dfii10_receipt_bundle(current),
        decision_known_at="2026-09-09T19:30:00Z",
        decision_session="2026-09-09",
        completed_sessions=LABOR_DAY_WINDOW + sessions("2026-09-09"),
    )
    assert context["status"] == "UNAVAILABLE"
    assert context["reason"] == "NO_QUALIFIED_RECEIPT_AT_DECISION"
    assert "NOT_KNOWN_AT_DECISION" in context["load_state"]

    prior = qualified_receipt(captured="2026-09-08T22:00:00Z")
    context = bind_dfii10_context(
        build_dfii10_receipt_bundle(prior),
        decision_known_at="2026-09-10T19:30:00Z",
        decision_session="2026-09-10",
        completed_sessions=LABOR_DAY_WINDOW + sessions("2026-09-09", "2026-09-10"),
    )
    assert context["status"] == "UNAVAILABLE"
    assert "STALE_AT_DECISION_2" in context["load_state"]


def test_consumer_recomputes_hash_delta_and_canonical_window_fail_closed():
    receipt = qualified_receipt()

    tampered = copy.deepcopy(receipt)
    tampered["delta_bp"] = 999.0
    context = bind_dfii10_context(
        build_dfii10_receipt_bundle(tampered),
        decision_known_at="2026-09-09T19:30:00Z",
        decision_session="2026-09-09",
        completed_sessions=LABOR_DAY_WINDOW + sessions("2026-09-09"),
    )
    assert context["status"] == "UNAVAILABLE"
    assert "SOURCE_SNAPSHOT_HASH_MISMATCH" in context["load_state"]

    tampered = copy.deepcopy(receipt)
    tampered["bound_session_window"] = tampered["bound_session_window"][:-1]
    context = bind_dfii10_context(
        build_dfii10_receipt_bundle(tampered),
        decision_known_at="2026-09-09T19:30:00Z",
        decision_session="2026-09-09",
        completed_sessions=LABOR_DAY_WINDOW + sessions("2026-09-09"),
    )
    assert context["status"] == "UNAVAILABLE"
    assert "SOURCE_SNAPSHOT_HASH_MISMATCH" in context["load_state"]


def test_flatten_persists_both_endpoints_and_full_context_without_authority():
    context = bind_dfii10_context(
        build_dfii10_receipt_bundle(qualified_receipt()),
        decision_known_at="2026-09-09T19:30:00Z",
        decision_session="2026-09-09",
        completed_sessions=LABOR_DAY_WINDOW + sessions("2026-09-09"),
    )
    row = flatten_dfii10_context(context)
    assert row["dfii10_latest_observation_date"] == "2026-09-08"
    assert row["dfii10_prior_observation_date"] == "2026-08-31"
    assert row["dfii10_delta_bp"] == -6.0
    persisted = json.loads(row["dfii10_context_json"])
    assert persisted["status"] == "QUALIFIED"
    assert not any(persisted["authority"].values())


def test_load_bundle_is_explicit_and_fail_closed(tmp_path: Path):
    bundle, state = load_dfii10_bundle(tmp_path)
    assert bundle is None and state == "TRANSMISSION_CONTRACT_MISSING"
    path = tmp_path / "data" / "transmission" / "latest.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"real_yield_5session": {"schema": "wrong"}}))
    bundle, state = load_dfii10_bundle(tmp_path)
    assert bundle is None and state == "DFII10_BUNDLE_SCHEMA_MISMATCH"


def test_capture_hashes_exact_bytes_and_selects_the_only_numeric_column(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "DFII10.parquet"
    raw = b"exact-parquet-byte-fixture"
    path.write_bytes(raw)
    frame = pd.DataFrame(
        {"DFII10": [1.90, 1.89, 1.88, 1.87, 1.86, 1.84]},
        index=pd.to_datetime([day.isoformat() for day in LABOR_DAY_WINDOW]),
    )

    def fake_read_parquet(handle):
        assert handle.read() == raw
        return frame

    monkeypatch.setattr(pd, "read_parquet", fake_read_parquet)
    receipt = capture_dfii10_receipt(
        path,
        captured_at="2026-09-08T22:00:00Z",
        completed_sessions=LABOR_DAY_WINDOW,
    )
    import hashlib

    assert receipt["status"] == "QUALIFIED"
    assert receipt["source"]["content_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert receipt["source"]["column"] == "DFII10"

    with pytest.raises(ValueError, match="ambiguous numeric columns"):
        select_dfii10_series(pd.DataFrame({"a": [1.0], "b": [2.0]}))


def test_capture_failure_emits_explicit_missing_receipt(tmp_path: Path):
    receipt = capture_dfii10_receipt(
        tmp_path / "missing.parquet",
        captured_at="2026-09-08T22:00:00Z",
        completed_sessions=LABOR_DAY_WINDOW,
    )
    assert receipt["status"] == "MISSING"
    assert receipt["missing_state"] == "SOURCE_FILE_MISSING"
    assert receipt["source_snapshot_hash"]
    assert not any(receipt["authority"].values())


def test_consumer_refuses_malformed_or_fabricated_authority_and_clocks():
    receipt = qualified_receipt()

    malformed_bundle = build_dfii10_receipt_bundle(receipt)
    malformed_bundle["authority"] = "all-false"
    context = bind_dfii10_context(
        malformed_bundle,
        decision_known_at="2026-09-09T19:30:00Z",
        decision_session="2026-09-09",
        completed_sessions=LABOR_DAY_WINDOW + sessions("2026-09-09"),
    )
    assert context["status"] == "UNAVAILABLE"
    assert context["reason"] == "DFII10_BUNDLE_AUTHORITY_INVALID"

    fabricated = copy.deepcopy(receipt)
    fabricated["capture"]["provider_release_time_inferred"] = True
    context = bind_dfii10_context(
        build_dfii10_receipt_bundle(fabricated),
        decision_known_at="2026-09-09T19:30:00Z",
        decision_session="2026-09-09",
        completed_sessions=LABOR_DAY_WINDOW + sessions("2026-09-09"),
    )
    assert context["status"] == "UNAVAILABLE"
    assert "CAPTURE_BASIS_INVALID" in context["load_state"]

    wrong_path = copy.deepcopy(receipt)
    wrong_path["source"]["path"] = "data/other/DFII10.parquet"
    context = bind_dfii10_context(
        build_dfii10_receipt_bundle(wrong_path),
        decision_known_at="2026-09-09T19:30:00Z",
        decision_session="2026-09-09",
        completed_sessions=LABOR_DAY_WINDOW + sessions("2026-09-09"),
    )
    assert context["status"] == "UNAVAILABLE"
    assert "SOURCE_IDENTITY_INVALID" in context["load_state"]


def test_owner_bundle_uses_existing_transmission_contract_and_no_new_store(tmp_path: Path):
    prior = qualified_receipt()
    previous_bundle = build_dfii10_receipt_bundle(prior)
    bundle = build_dfii10_owner_bundle(
        tmp_path / "data",
        captured_at="2026-09-09T22:00:00Z",
        previous_bundle=previous_bundle,
        completed_sessions=LABOR_DAY_WINDOW + sessions("2026-09-09"),
    )
    assert bundle["schema"] == DFII10_BUNDLE_SCHEMA
    assert bundle["current"]["status"] == "MISSING"
    assert bundle["current"]["missing_state"] == "SOURCE_FILE_MISSING"
    assert bundle["previous_qualified"]["source_snapshot_hash"] == \
        prior["source_snapshot_hash"]
    assert list(tmp_path.rglob("*")) == [], "owner helper must not create a second store"


def test_reconciler_binds_measurement_context_without_changing_event_identity():
    from scripts import reconcile_entry_radar as rec

    prior = qualified_receipt(captured="2026-09-08T22:00:00Z")
    bundle = build_dfii10_receipt_bundle(prior)
    record = {
        "event_id": "AAA-C2-2026-09-09",
        "ticker": "AAA",
        "detector_id": "C2_1D_TURN@1",
        "family": "radar_turn",
        "subtype": "c2_turn",
        "context": {"market_session": "2026-09-09"},
        "signal_ts": "2026-09-09T19:25:00Z",
        "signal_known_ts": "2026-09-09T19:30:00Z",
        "observed_at": "2026-09-09T19:31:00Z",
        "bar_state": "confirmed",
        "final": True,
        "source_identity": {"detector_spec_hash": "detector-hash"},
    }
    row = rec._event_row(
        record,
        session="2026-09-09",
        state=rec.STATE_WAITING,
        dfii10_bundle=bundle,
        dfii10_load_state="LOADED",
    )
    assert row["episode_address"] == "AAA-C2-2026-09-09"
    assert row["detector_id"] == "C2_1D_TURN@1"
    assert row["state"] == rec.STATE_WAITING
    assert row["dfii10_context_status"] == "QUALIFIED"
    assert row["dfii10_latest_observation_date"] == "2026-09-08"
    assert row["dfii10_prior_observation_date"] == "2026-08-31"
    assert row["dfii10_delta_bp"] == -6.0
    assert not any(json.loads(row["dfii10_context_json"])["authority"].values())


def test_reconciler_persists_unavailable_context_instead_of_defaulting_to_zero():
    from scripts import reconcile_entry_radar as rec

    record = {
        "event_id": "AAA-C2-2026-09-09",
        "ticker": "AAA",
        "detector_id": "C2_1D_TURN@1",
        "context": {"market_session": "2026-09-09"},
        "signal_known_ts": "2026-09-09T19:30:00Z",
        "observed_at": "2026-09-09T19:31:00Z",
    }
    row = rec._event_row(
        record,
        session="2026-09-09",
        state=rec.STATE_WAITING,
        dfii10_bundle=None,
        dfii10_load_state="TRANSMISSION_CONTRACT_MISSING",
    )
    assert row["dfii10_context_status"] == "UNAVAILABLE"
    assert row["dfii10_delta_bp"] is None
    assert row["dfii10_context_load_state"] == "TRANSMISSION_CONTRACT_MISSING"


def test_builder_wires_receipt_before_the_incumbent_contract_write():
    source = (Path(__file__).resolve().parents[1] / "scripts" /
              "build_transmission.py").read_text(encoding="utf-8")
    owner_call = source.index('contract["real_yield_5session"]')
    contract_write = source.index('(outdir / "latest.json").write_text')
    assert "build_dfii10_owner_bundle" in source
    assert owner_call < contract_write
    assert 'data/transmission/dfii10' not in source


def test_bundle_preserves_pre_session_receipt_across_multiple_same_night_source_changes():
    sep8 = qualified_receipt(captured="2026-09-08T22:00:00Z", sha="a" * 64)
    bundle = build_dfii10_receipt_bundle(sep8)

    through_sep9 = LABOR_DAY_WINDOW + sessions("2026-09-09")
    sep9_first = build_dfii10_five_session_receipt(
        series({
            "2026-08-31": 1.90, "2026-09-01": 1.89, "2026-09-02": 1.88,
            "2026-09-03": 1.87, "2026-09-04": 1.86, "2026-09-08": 1.84,
            "2026-09-09": 1.82,
        }),
        completed_sessions=through_sep9,
        captured_at="2026-09-09T21:00:00Z",
        source_content_sha256="b" * 64,
    )
    bundle = build_dfii10_receipt_bundle(sep9_first, bundle)
    assert bundle["previous_qualified"]["source_snapshot_hash"] == \
        sep8["source_snapshot_hash"]

    sep9_corrected = build_dfii10_five_session_receipt(
        series({
            "2026-08-31": 1.90, "2026-09-01": 1.89, "2026-09-02": 1.88,
            "2026-09-03": 1.87, "2026-09-04": 1.86, "2026-09-08": 1.84,
            "2026-09-09": 1.81,
        }),
        completed_sessions=through_sep9,
        captured_at="2026-09-09T22:00:00Z",
        source_content_sha256="c" * 64,
        previous_receipt=sep9_first,
    )
    bundle = build_dfii10_receipt_bundle(sep9_corrected, bundle)
    assert bundle["previous_qualified"]["source_snapshot_hash"] == \
        sep8["source_snapshot_hash"], "same-night rebuild must not evict the pre-session receipt"

    through_sep10 = through_sep9 + sessions("2026-09-10")
    sep10 = build_dfii10_five_session_receipt(
        series({
            "2026-08-31": 1.90, "2026-09-01": 1.89, "2026-09-02": 1.88,
            "2026-09-03": 1.87, "2026-09-04": 1.86, "2026-09-08": 1.84,
            "2026-09-09": 1.81, "2026-09-10": 1.80,
        }),
        completed_sessions=through_sep10,
        captured_at="2026-09-10T22:00:00Z",
        source_content_sha256="d" * 64,
        previous_receipt=sep9_corrected,
    )
    rolled = build_dfii10_receipt_bundle(sep10, bundle)
    assert rolled["previous_qualified"]["source_snapshot_hash"] == \
        sep9_corrected["source_snapshot_hash"], "next session should roll to latest prior receipt"


def test_nonfinite_source_values_are_not_bound_as_measurements():
    receipt = build_dfii10_five_session_receipt(
        series({
            "2026-08-31": 1.90, "2026-09-01": 1.89, "2026-09-02": 1.88,
            "2026-09-03": 1.87, "2026-09-04": 1.86, "2026-09-08": float("inf"),
        }),
        completed_sessions=LABOR_DAY_WINDOW,
        captured_at="2026-09-08T22:00:00Z",
        source_content_sha256="f" * 64,
    )
    assert receipt["status"] != "QUALIFIED"
    assert receipt["latest"]["observation_date"] == "2026-09-04"
    assert receipt["stale_state"] == "STALE_AT_CAPTURE"


def test_consumer_rejects_nonfinite_or_incomplete_source_identity_without_throwing():
    receipt = qualified_receipt()
    nonfinite = copy.deepcopy(receipt)
    nonfinite["latest"]["value_pct"] = float("nan")
    context = bind_dfii10_context(
        build_dfii10_receipt_bundle(nonfinite),
        decision_known_at="2026-09-09T19:30:00Z",
        decision_session="2026-09-09",
        completed_sessions=LABOR_DAY_WINDOW + sessions("2026-09-09"),
    )
    assert context["status"] == "UNAVAILABLE"
    assert "RECEIPT_NUMERIC_INVALID" in context["load_state"] or \
        "SOURCE_SNAPSHOT_HASH_INVALID" in context["load_state"]

    no_column = copy.deepcopy(receipt)
    no_column["source"]["column"] = None
    context = bind_dfii10_context(
        build_dfii10_receipt_bundle(no_column),
        decision_known_at="2026-09-09T19:30:00Z",
        decision_session="2026-09-09",
        completed_sessions=LABOR_DAY_WINDOW + sessions("2026-09-09"),
    )
    assert context["status"] == "UNAVAILABLE"
    assert "SOURCE_IDENTITY_INVALID" in context["load_state"]


def test_unqualified_current_preserves_last_valid_same_session_receipt():
    through_sep9 = LABOR_DAY_WINDOW + sessions("2026-09-09")
    sep9_valid = build_dfii10_five_session_receipt(
        series({
            "2026-08-31": 1.90, "2026-09-01": 1.89, "2026-09-02": 1.88,
            "2026-09-03": 1.87, "2026-09-04": 1.86, "2026-09-08": 1.84,
            "2026-09-09": 1.82,
        }),
        completed_sessions=through_sep9,
        captured_at="2026-09-09T21:00:00Z",
        source_content_sha256="1" * 64,
        source_column="DFII10",
    )
    previous = build_dfii10_receipt_bundle(sep9_valid)
    missing = build_dfii10_five_session_receipt(
        None,
        completed_sessions=through_sep9,
        captured_at="2026-09-09T22:00:00Z",
        source_content_sha256=None,
        source_column=None,
        previous_receipt=sep9_valid,
    )
    bundle = build_dfii10_receipt_bundle(missing, previous)
    assert bundle["current"]["status"] == "MISSING"
    assert bundle["previous_qualified"]["source_snapshot_hash"] == \
        sep9_valid["source_snapshot_hash"]


def test_numeric_source_index_is_refused_instead_of_becoming_epoch_dates():
    receipt = build_dfii10_five_session_receipt(
        pd.Series([1.90, 1.89, 1.88, 1.87, 1.86, 1.84]),
        completed_sessions=LABOR_DAY_WINDOW,
        captured_at="2026-09-08T22:00:00Z",
        source_content_sha256="2" * 64,
        source_column="DFII10",
    )
    assert receipt["status"] == "MISSING"
    assert receipt["missing_state"] == "SOURCE_INDEX_INVALID"
    assert receipt["latest"] is None


def test_owner_calendar_waits_for_settle_before_admitting_same_session_source(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "DFII10.parquet"
    raw = b"calendar-settle-fixture"
    path.write_bytes(raw)
    dates = [
        "2026-08-28", "2026-08-31", "2026-09-01", "2026-09-02",
        "2026-09-03", "2026-09-04", "2026-09-08",
    ]
    frame = pd.DataFrame(
        {"DFII10": [1.91, 1.90, 1.89, 1.88, 1.87, 1.86, 1.84]},
        index=pd.to_datetime(dates),
    )

    def fake_read_parquet(handle):
        assert handle.read() == raw
        return frame

    monkeypatch.setattr(pd, "read_parquet", fake_read_parquet)
    before_settle = capture_dfii10_receipt(
        path,
        captured_at="2026-09-08T20:30:00Z",  # 16:30 ET, before 17:00 settle.
    )
    assert before_settle["eligible_session"] == "2026-09-04"
    assert before_settle["latest"]["observation_date"] == "2026-09-04"
    assert before_settle["prior_five_sessions"]["observation_date"] == "2026-08-28"

    after_settle = capture_dfii10_receipt(
        path,
        captured_at="2026-09-08T22:00:00Z",  # 18:00 ET, after settle.
    )
    assert after_settle["eligible_session"] == "2026-09-08"
    assert after_settle["latest"]["observation_date"] == "2026-09-08"
    assert after_settle["prior_five_sessions"]["observation_date"] == "2026-08-31"

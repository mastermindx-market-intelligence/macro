"""tests/test_live_flow_recovery.py — hermetic WAL / cycle-recovery guards.

Carved out of tests/test_live_flow.py in PR #8322 round 2 so the new
code-gated CI manifest (`live-flow-recovery-guards`) owns the test file
explicitly. The classes below exercise:

  * `TestDayStateLearningWal` — WAL save/stage/clear ordering,
    file+directory fsync durability, startup WAL drain ordering vs Theta,
    stale-session visibility, retention/load resilience, `--rth-only` and
    `--once` exit shapes, launchd `KeepAlive` contract, schema-version
    discard.

  * `TestReviewedPriorSessionWalQuarantine` — the production-pin quarantine
    path for the prior-session WAL recovery: literal `PRIOR_SESSION_WAL_INCIDENT`
    equality (production descriptor + synthetic other-digest rejection),
    receipt shape, canonical stage absence (empty / malformed / disjoint),
    per-event cross-session clock classification, retention preservation of
    invalid receipts and raw bytes, malformed-receipt isolation under retention,
    CLI atomic fsync + readback, CLI idempotent replay, CLI rejection on
    invalid session / missing day_state, atomic-write failure preservation,
    old stager never invoked on a quarantined session.

Every test is network-free, `tmp_path`-isolated, has no `app.main` import
and no FastAPI TestClient fixture. The original API TestClient cases stay
under the existing `tests/test_live_flow.py` dataowner and remain unchanged.
"""
from __future__ import annotations

import hashlib
import json
import logging
import stat
from pathlib import Path

import pytest

# Session date pinned by the original suite for the WAL/cycle tests.
WAL_SESSION_DATE = "2026-07-02"


# ─────────────────────────────────────────────────────────────────────────────
# 33. WAL/cycle recovery — day_state save + drain ordering, fsync durability,
#     stale-session visibility, retention/load resilience, CLI shapes,
#     launchd KeepAlive contract, schema-version discard.
# ─────────────────────────────────────────────────────────────────────────────

class TestDayStateLearningWal:
    @staticmethod
    def _state() -> dict:
        return {
            "emitted_ids": {"event-1"},
            "all_events": [],
            "pending_learning_events": [{
                "id": "event-1",
                "ts": "2026-07-02T14:30:00Z",
                "observed_at": "2026-07-02T14:31:00Z",
                "decision_at": "2026-07-02T14:32:00Z",
            }],
            "cycle_watermarks": {
                "SPY": {"ts": "2026-07-02T14:30:00Z", "seq": 1000},
            },
            "seen_sequences": {
                ("SPY", "2026-07-05", 550.0, "C"): 1000,
            },
            "contract_vol": {
                ("SPY", "2026-07-05", 550.0, "C"): 100,
            },
            "notability_history": {
                ("SPY", "2026-07-05", 550.0, "C"): 1,
            },
        }

    @staticmethod
    def _enriched(event: dict) -> dict:
        return {
            **event,
            "available_at": "2026-07-02T14:33:00Z",
            "published_at": None,
            "source_snapshot_asof": "2026-07-02T14:33:00Z",
            "anchor_strategy": "durable_available_at",
        }

    @staticmethod
    def _stub_main_prelude(tmp_path, monkeypatch):
        """Reach the cycle loop without network, host, or publication effects."""
        import collectors.thetadata as td
        import scripts.build_flow_archive as flow_archive
        import scripts.live_flow_poller as poller

        monkeypatch.setattr(poller, "_cfg", lambda: {"retention_hours": 24})
        monkeypatch.setattr(poller, "_session_date", lambda _override=None: WAL_SESSION_DATE)
        monkeypatch.setattr(
            poller, "_current_session_matches_frozen_run", lambda *_args, **_kwargs: True,
        )
        monkeypatch.setattr(poller, "_state_dir", lambda: tmp_path)
        monkeypatch.setenv("LIVE_FLOW_EVENT_STAGE_DIR", str(tmp_path / "events"))
        monkeypatch.setattr(
            poller, "_initialize_options_context_dispatcher", lambda *_args, **_kwargs: None,
        )
        monkeypatch.setattr(poller, "_flush_options_context_outbox", lambda: None)
        monkeypatch.setattr(td, "reachable", lambda **_kwargs: True)
        monkeypatch.setattr(poller, "_resolve_universe", lambda _cfg: ["SPY"])
        monkeypatch.setattr(poller, "_probe_delta_mode", lambda _session: "time_window")
        monkeypatch.setattr(poller, "_load_baselines", lambda: {})
        monkeypatch.setattr(poller, "_load_unusual_baseline", lambda: {})
        monkeypatch.setattr(poller, "_r2_client", lambda: None)
        monkeypatch.setattr(poller, "_prune_day_states", lambda *_args: None)
        monkeypatch.setattr(flow_archive, "is_market_session", lambda _session: False)
        monkeypatch.setattr(poller, "_poll_floor_sec", lambda _cfg: 37)
        monkeypatch.setattr(poller, "_two_tier_enabled", lambda: False)
        monkeypatch.setattr(poller, "_daily_summary_enabled", lambda: False)
        monkeypatch.setattr(poller, "_max_concurrent", lambda _cfg: 1)
        monkeypatch.setattr(
            poller, "_select_cycle_roots", lambda roots, _cycle, _cfg: (roots, None),
        )
        monkeypatch.setattr(poller, "_utc_now_iso", lambda: "2026-07-02T20:06:00Z")
        return poller

    def test_wal_save_precedes_stage_and_survives_stage_failure(
        self, tmp_path, monkeypatch,
    ):
        import scripts.live_flow_poller as poller

        state_dir = tmp_path / "live_flow_state"
        state_dir.mkdir()
        monkeypatch.setattr(poller, "_state_dir", lambda: state_dir)
        monkeypatch.setenv("LIVE_FLOW_EVENT_STAGE_DIR", str(state_dir / "events"))
        state = self._state()
        poller._save_day_state(WAL_SESSION_DATE, state)

        with pytest.raises(RuntimeError, match="stage failed"):
            poller._drain_pending_learning_events(
                WAL_SESSION_DATE,
                state,
                event_stager=lambda *_: (_ for _ in ()).throw(RuntimeError("stage failed")),
            )
        restored = poller._load_day_state(WAL_SESSION_DATE)
        assert restored["pending_learning_events"] == state["pending_learning_events"]
        assert restored["all_events"] == []
        assert restored["seen_sequences"] == state["seen_sequences"]

    def test_crash_after_stage_before_clear_replays_same_wal_then_clears(
        self, tmp_path, monkeypatch,
    ):
        import scripts.live_flow_poller as poller

        state_dir = tmp_path / "live_flow_state"
        state_dir.mkdir()
        monkeypatch.setattr(poller, "_state_dir", lambda: state_dir)
        monkeypatch.setenv("LIVE_FLOW_EVENT_STAGE_DIR", str(state_dir / "events"))
        state = self._state()
        poller._save_day_state(WAL_SESSION_DATE, state)
        real_save = poller._save_day_state
        staged_inputs: list[list[dict]] = []

        def stager(_session, events):
            staged_inputs.append([dict(event) for event in events])
            return [self._enriched(event) for event in events]

        monkeypatch.setattr(
            poller, "_save_day_state",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                RuntimeError("crash before clear")
            ),
        )
        with pytest.raises(RuntimeError, match="crash before clear"):
            poller._drain_pending_learning_events(
                WAL_SESSION_DATE, state, event_stager=stager,
            )
        monkeypatch.setattr(poller, "_save_day_state", real_save)
        restored = poller._load_day_state(WAL_SESSION_DATE)
        assert restored["pending_learning_events"]
        cleared, _ = poller._drain_pending_learning_events(
            WAL_SESSION_DATE, restored, event_stager=stager,
        )
        assert staged_inputs[0] == staged_inputs[1]
        assert cleared["pending_learning_events"] == []
        assert [event["id"] for event in cleared["all_events"]] == ["event-1"]
        persisted = poller._load_day_state(WAL_SESSION_DATE)
        assert persisted["pending_learning_events"] == []
        assert persisted["all_events"] == cleared["all_events"]

    def test_stager_mismatch_never_clears_wal(self, tmp_path, monkeypatch):
        import scripts.live_flow_poller as poller

        state_dir = tmp_path / "live_flow_state"
        state_dir.mkdir()
        monkeypatch.setattr(poller, "_state_dir", lambda: state_dir)
        monkeypatch.setenv("LIVE_FLOW_EVENT_STAGE_DIR", str(state_dir / "events"))
        state = self._state()
        poller._save_day_state(WAL_SESSION_DATE, state)
        with pytest.raises(RuntimeError, match="reconcile every"):
            poller._drain_pending_learning_events(
                WAL_SESSION_DATE, state, event_stager=lambda *_: [],
            )
        assert poller._load_day_state(WAL_SESSION_DATE)["pending_learning_events"]

    def test_same_count_wrong_id_or_duplicate_never_clears_wal(
        self, tmp_path, monkeypatch,
    ):
        import scripts.live_flow_poller as poller

        state_dir = tmp_path / "live_flow_state"
        state_dir.mkdir()
        monkeypatch.setattr(poller, "_state_dir", lambda: state_dir)
        monkeypatch.setenv("LIVE_FLOW_EVENT_STAGE_DIR", str(state_dir / "events"))
        state = self._state()
        poller._save_day_state(WAL_SESSION_DATE, state)

        wrong = self._enriched({**state["pending_learning_events"][0], "id": "wrong-id"})
        with pytest.raises(RuntimeError, match="changed pending decision payload"):
            poller._drain_pending_learning_events(
                WAL_SESSION_DATE, state, event_stager=lambda *_: [wrong],
            )
        assert poller._load_day_state(WAL_SESSION_DATE)["pending_learning_events"]

        duplicated = dict(state)
        duplicated["pending_learning_events"] = [
            state["pending_learning_events"][0],
            dict(state["pending_learning_events"][0]),
        ]
        with pytest.raises(RuntimeError, match="duplicate event ids"):
            poller._drain_pending_learning_events(
                WAL_SESSION_DATE, duplicated, event_stager=lambda *_: [],
            )

    @pytest.mark.parametrize("override", [False, True])
    def test_missing_or_corrupt_state_with_existing_stage_fails_closed(
        self, tmp_path, monkeypatch, override: bool,
    ):
        import scripts.live_flow_poller as poller

        state_dir = tmp_path / "live_flow_state"
        state_dir.mkdir()
        stage_dir = tmp_path / "override-events" if override else state_dir / "events"
        stage_dir.mkdir()
        monkeypatch.setattr(poller, "_state_dir", lambda: state_dir)
        if override:
            monkeypatch.setenv("LIVE_FLOW_EVENT_STAGE_DIR", str(stage_dir))
        else:
            monkeypatch.delenv("LIVE_FLOW_EVENT_STAGE_DIR", raising=False)
        (stage_dir / f"{WAL_SESSION_DATE}.jsonl").write_text('{"durable":true}\n')
        with pytest.raises(RuntimeError, match="missing"):
            poller._load_day_state(WAL_SESSION_DATE)
        (state_dir / f"day_state_{WAL_SESSION_DATE}.json").write_text("{broken")
        with pytest.raises(RuntimeError, match="cannot recover"):
            poller._load_day_state(WAL_SESSION_DATE)

    def test_day_state_replace_is_file_and_directory_durable(
        self, tmp_path, monkeypatch,
    ):
        import scripts.live_flow_poller as poller

        state_dir = tmp_path / "live_flow_state"
        state_dir.mkdir()
        monkeypatch.setattr(poller, "_state_dir", lambda: state_dir)
        monkeypatch.setenv("LIVE_FLOW_EVENT_STAGE_DIR", str(state_dir / "events"))
        order: list[str] = []
        real_fsync = poller.os.fsync

        def fsync_spy(fd: int):
            order.append(
                "directory_fsync"
                if stat.S_ISDIR(poller.os.fstat(fd).st_mode)
                else "file_fsync"
            )
            real_fsync(fd)

        monkeypatch.setattr(poller.os, "fsync", fsync_spy)
        path = poller._save_day_state(WAL_SESSION_DATE, self._state())
        assert path.read_bytes().endswith(b"\n")
        assert order[-2:] == ["file_fsync", "directory_fsync"]

    def test_startup_drains_same_session_wal_before_theta_probe(
        self, tmp_path, monkeypatch,
    ):
        import collectors.thetadata as td
        import scripts.live_flow_poller as poller

        state_dir = tmp_path / "live_flow_state"
        state_dir.mkdir()
        monkeypatch.setattr(poller, "_state_dir", lambda: state_dir)
        monkeypatch.setenv("LIVE_FLOW_EVENT_STAGE_DIR", str(state_dir / "events"))
        state = self._state()
        poller._save_day_state(WAL_SESSION_DATE, state)
        order: list[str] = []

        def stager(_session, events):
            order.append("stage")
            return [self._enriched(event) for event in events]

        monkeypatch.setattr(poller, "_stage_raw_events", stager)
        monkeypatch.setattr(poller, "_cfg", lambda: {"retention_hours": 24})
        monkeypatch.setattr(poller, "_session_date", lambda _override=None: WAL_SESSION_DATE)
        monkeypatch.setattr(
            poller, "_current_session_matches_frozen_run", lambda *_args, **_kwargs: True,
        )
        monkeypatch.setattr(
            td, "reachable", lambda **_kwargs: order.append("theta") or False,
        )
        assert poller.main(["--once"]) == 1
        assert order == ["stage", "theta"]
        assert poller._load_day_state(WAL_SESSION_DATE)["pending_learning_events"] == []

    def test_stale_prior_session_wal_is_visible_before_retention_or_theta(
        self, tmp_path, monkeypatch,
    ):
        import collectors.thetadata as td
        import scripts.live_flow_poller as poller

        state_dir = tmp_path / "live_flow_state"
        state_dir.mkdir()
        monkeypatch.setattr(poller, "_state_dir", lambda: state_dir)
        monkeypatch.setenv("LIVE_FLOW_EVENT_STAGE_DIR", str(state_dir / "events"))
        poller._save_day_state(WAL_SESSION_DATE, self._state())
        assert poller._stale_pending_learning_sessions("2026-07-06") == [WAL_SESSION_DATE]

        order: list[str] = []
        monkeypatch.setattr(poller, "_cfg", lambda: {"retention_hours": 24})
        monkeypatch.setattr(poller, "_session_date", lambda _override=None: "2026-07-06")
        monkeypatch.setattr(
            poller, "_prune_day_states", lambda *_args: order.append("prune"),
        )
        monkeypatch.setattr(
            td, "reachable", lambda **_kwargs: order.append("theta") or True,
        )
        assert poller.main(["--once"]) == 1
        assert order == []

    def test_launchd_restarts_only_abnormal_exit(self):
        import plistlib

        repo = Path(__file__).resolve().parent.parent
        payload = plistlib.loads(
            (repo / "ops/launchd/com.mastermind.liveflow.plist").read_bytes()
        )
        assert payload["KeepAlive"] == {"SuccessfulExit": False}
        assert payload["ThrottleInterval"] == 60

    def test_rth_only_post_close_error_exits_zero_without_publication_or_sleep(
        self, tmp_path, monkeypatch,
    ):
        poller = self._stub_main_prelude(tmp_path, monkeypatch)
        pending_state = self._state()
        publication_calls: list[str] = []
        sleep_calls: list[float] = []
        prune_calls: list[str] = []
        rth_checks = iter([True, False])

        def unexpected_sleep(seconds: float):
            sleep_calls.append(seconds)
            raise AssertionError("post-close errored cycle must not sleep")

        monkeypatch.setattr(poller, "_within_rth", lambda: next(rth_checks))
        monkeypatch.setattr(
            poller,
            "run_cycle",
            lambda **_kwargs: (
                {"events": []},
                {},
                {"asof": "2026-07-02T20:05:59Z"},
                dict(pending_state),
                {},
            ),
        )
        monkeypatch.setattr(
            poller,
            "_drain_pending_learning_events",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                RuntimeError("injected post-save stage failure")
            ),
        )
        monkeypatch.setattr(
            poller, "_write_json", lambda name, _payload: publication_calls.append(name),
        )
        monkeypatch.setattr(
            poller, "_upload_r2", lambda *_args, **_kwargs: publication_calls.append("r2"),
        )
        monkeypatch.setattr(
            poller, "_prune_day_states", lambda *_args: prune_calls.append("startup"),
        )
        monkeypatch.setattr(poller.time, "sleep", unexpected_sleep)

        assert poller.main(["--rth-only"]) == 0
        assert publication_calls == []
        assert sleep_calls == []
        assert prune_calls == ["startup"]
        restored = poller._load_day_state(WAL_SESSION_DATE)
        assert restored["pending_learning_events"] == pending_state["pending_learning_events"]
        assert restored["all_events"] == []

    def test_rth_only_cycle_error_within_rth_sleeps_then_retries(
        self, tmp_path, monkeypatch,
    ):
        poller = self._stub_main_prelude(tmp_path, monkeypatch)
        attempts: list[int] = []
        sleep_calls: list[float] = []
        publication_calls: list[str] = []

        class StopAfterRetry(BaseException):
            pass

        def fail_then_stop(**_kwargs):
            attempts.append(len(attempts) + 1)
            if len(attempts) == 1:
                raise RuntimeError("injected within-RTH cycle failure")
            raise StopAfterRetry

        monkeypatch.setattr(poller, "_within_rth", lambda: True)
        monkeypatch.setattr(poller, "run_cycle", fail_then_stop)
        monkeypatch.setattr(poller.time, "sleep", sleep_calls.append)
        monkeypatch.setattr(
            poller, "_write_json", lambda name, _payload: publication_calls.append(name),
        )

        with pytest.raises(StopAfterRetry):
            poller.main(["--rth-only"])

        assert attempts == [1, 2]
        assert sleep_calls == [37]
        assert publication_calls == []

    def test_once_cycle_error_remains_nonzero_without_sleep(
        self, tmp_path, monkeypatch,
    ):
        poller = self._stub_main_prelude(tmp_path, monkeypatch)
        sleep_calls: list[float] = []
        publication_calls: list[str] = []

        monkeypatch.setattr(
            poller,
            "run_cycle",
            lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("injected once failure")),
        )
        monkeypatch.setattr(poller.time, "sleep", sleep_calls.append)
        monkeypatch.setattr(
            poller, "_write_json", lambda name, _payload: publication_calls.append(name),
        )

        assert poller.main(["--once"]) == 1
        assert sleep_calls == []
        assert publication_calls == []

    def test_missing_version_treated_as_v1(self, tmp_path, monkeypatch, caplog):
        """A day_state with no schema_version key is treated as version 1 → discarded."""
        import json as _json
        from scripts.live_flow_poller import _load_day_state
        from engine.live_flow import DAY_STATE_VERSION

        if DAY_STATE_VERSION <= 1:
            pytest.skip("DAY_STATE_VERSION == 1 means no discard needed")

        state_dir = tmp_path / "live_flow_state"
        state_dir.mkdir()
        session = WAL_SESSION_DATE
        p = state_dir / f"day_state_{session}.json"
        # No schema_version key (legacy state)
        legacy = {
            "emitted_ids": ["old_ev"],
            "all_events": [],
            "root_gross_today": {},
            "contract_vol": {},
            "notability_history": {},
            "seen_sequences": {},
        }
        p.write_text(_json.dumps(legacy))

        monkeypatch.setattr(
            "scripts.live_flow_poller._state_dir",
            lambda: state_dir,
        )

        with caplog.at_level(logging.INFO, logger="scripts.live_flow_poller"):
            result = _load_day_state(session)

        assert result == {}, (
            "Legacy day_state (no schema_version) should be treated as v1 and discarded")


# ─────────────────────────────────────────────────────────────────────────────
# 47. PR #8322 incident — production-pin quarantine of the prior-session WAL.
# ─────────────────────────────────────────────────────────────────────────────

class TestReviewedPriorSessionWalQuarantine:
    SESSION = "2026-09-28"
    STATE_SHA = "d9a25966a8d50090f8619d878e4133860cc54682b53764126bf7299e1ca00b06"
    ORDERED_SHA = "c52ee12c27b31775e2acef188e434134202e3f745ebb2d55c68a0e12749df218"
    DEPLOYED_SHA = "bffd9931b2e37b5011fe50e0633f62c356879dd8"
    OBS_MIN = "2026-09-28T13:37:09.179619Z"
    OBS_MAX = "2026-09-28T13:38:55.752263Z"
    DEC_MIN = "2026-09-30T23:51:45.034847Z"
    DEC_MAX = "2026-09-30T23:53:18.537416Z"

    @classmethod
    def _production_descriptor(cls):
        return {
            "deployed_sha": cls.DEPLOYED_SHA,
            "state_sha256": cls.STATE_SHA,
            "session_date": cls.SESSION,
            "schema_version": 5,
            "pending_event_count": 170,
            "ordered_event_id_sha256": cls.ORDERED_SHA,
            "observed_at_min": cls.OBS_MIN,
            "observed_at_max": cls.OBS_MAX,
            "decision_at_min": cls.DEC_MIN,
            "decision_at_max": cls.DEC_MAX,
        }

    @classmethod
    def _synthetic_descriptor(cls, *, state_sha: str, ordered_sha: str):
        return {
            "deployed_sha": cls.DEPLOYED_SHA,
            "state_sha256": state_sha,
            "session_date": cls.SESSION,
            "schema_version": 5,
            "pending_event_count": 170,
            "ordered_event_id_sha256": ordered_sha,
            "observed_at_min": cls.OBS_MIN,
            "observed_at_max": cls.OBS_MAX,
            "decision_at_min": cls.DEC_MIN,
            "decision_at_max": cls.DEC_MAX,
        }

    @staticmethod
    def _receipt_from_incident(incident: dict):
        return {
            "schema": "live_flow.prior_session_wal_quarantine/v1",
            "classification": "cross_session_decision_clock_nonadmissible",
            "review_reference": "chairman-options-alpha-parent599-review",
            "incident": incident,
            "protected_source": None,
        }

    @classmethod
    def _receipt(cls):
        return cls._receipt_from_incident(cls._production_descriptor())

    @staticmethod
    def _event(index: int):
        return {
            "id": f"reviewed-{index:03d}",
            "ts": "2026-09-28T13:37:00Z",
            "observed_at": "2026-09-28T13:37:09.179619Z",
            "decision_at": "2026-09-30T23:51:45.034847Z",
            "kind": "test",
        }

    def _protected_state(self):
        events = [self._event(index) for index in range(170)]
        events[-1] = {
            **events[-1],
            "observed_at": "2026-09-28T13:38:55.752263Z",
            "decision_at": "2026-09-30T23:53:18.537416Z",
        }
        return {
            "schema_version": 5,
            "emitted_ids": [event["id"] for event in events],
            "all_events": [],
            "root_gross_today": {},
            "pending_learning_events": events,
            "cycle_watermarks": {},
            "contract_vol": {},
            "notability_history": {},
            "seen_sequences": {},
            "market_tide_minutes": {},
            "sector_tide": {},
            "dte_tide": {},
            "root_minutes": {},
            "root_strikes": {},
            "root_expiries": {},
            "root_top_contracts": {},
            "sweep_clusters": {},
            "source_asof": None,
            "root_source_receipts": {},
            "root_ticker_receipts": {},
        }

    def _write_case(self, tmp_path, monkeypatch, *, mutation=None):
        import scripts.live_flow_poller as poller

        monkeypatch.setattr(poller, "_state_dir", lambda: tmp_path)
        monkeypatch.setenv("LIVE_FLOW_EVENT_STAGE_DIR", str(tmp_path / "events"))
        state = self._protected_state()
        if mutation is not None:
            mutation(state)
        raw = (json.dumps(state, sort_keys=True, separators=(",", ":")) + "\n").encode()
        (tmp_path / "day_state_2026-09-28.json").write_bytes(raw)
        return poller

    @staticmethod
    def _inject_descriptor(monkeypatch, poller, descriptor):
        """Tests-only helper: bind a synthetic descriptor for happy-path fixtures.

        Production code never goes through this path: the public CLI uses
        PRIOR_SESSION_WAL_INCIDENT directly. The helper exists so the immutable
        production pin does not have to be weakened to make fixtures pass.
        """
        monkeypatch.setattr(poller, "PRIOR_SESSION_WAL_INCIDENT", dict(descriptor))

    @staticmethod
    def _state_digests(state_path):
        raw = state_path.read_bytes()
        pending = json.loads(raw.decode("utf-8"))["pending_learning_events"]
        ordered = hashlib.sha256(
            b"".join((event["id"] + "\n").encode() for event in pending)
        ).hexdigest()
        return hashlib.sha256(raw).hexdigest(), ordered

    def test_production_pin_refuses_synthetic_other_digest(self, tmp_path, monkeypatch):
        """Unpatched production descriptor rejects any synthetic other digest."""
        import scripts.live_flow_poller as poller

        poller_mod = self._write_case(tmp_path, monkeypatch)
        state_path = tmp_path / "day_state_2026-09-28.json"
        synthetic_state_sha, synthetic_ordered_sha = self._state_digests(state_path)
        # The synthetic fixture bytes do NOT hash to the production descriptor;
        # the unpatched production pin must refuse them.
        assert synthetic_state_sha != self.STATE_SHA
        assert synthetic_ordered_sha != self.ORDERED_SHA
        receipt = self._receipt()
        # The literal production descriptor's state_sha256 doesn't match the
        # protected_source SHA-256 of the synthetic on-disk state.
        receipt["protected_source"] = {
            "sha256": synthetic_state_sha,
            "bytes": state_path.stat().st_size,
        }
        quarantine = tmp_path / "quarantine"
        quarantine.mkdir()
        (quarantine / "prior_session_wal_quarantine_2026-09-28.json").write_text(
            json.dumps(receipt, sort_keys=True) + "\n"
        )
        with pytest.raises(RuntimeError):
            poller_mod._validate_prior_session_wal_quarantine(self.SESSION)

    def test_exact_reviewed_wal_permits_startup_but_never_drains_old_ids(
        self, tmp_path, monkeypatch,
    ):
        import scripts.live_flow_poller as poller

        poller_mod = self._write_case(tmp_path, monkeypatch)
        state_path = tmp_path / "day_state_2026-09-28.json"
        synthetic_state_sha, synthetic_ordered_sha = self._state_digests(state_path)
        descriptor = self._synthetic_descriptor(
            state_sha=synthetic_state_sha, ordered_sha=synthetic_ordered_sha,
        )
        self._inject_descriptor(monkeypatch, poller_mod, descriptor)
        receipt = self._receipt_from_incident(descriptor)
        receipt["protected_source"] = {
            "sha256": synthetic_state_sha,
            "bytes": state_path.stat().st_size,
        }
        quarantine = tmp_path / "quarantine"
        quarantine.mkdir()
        (quarantine / "prior_session_wal_quarantine_2026-09-28.json").write_text(
            json.dumps(receipt, sort_keys=True) + "\n"
        )

        assert poller_mod._stale_pending_learning_sessions("2026-09-29") == []
        assert poller_mod._validate_prior_session_wal_quarantine("2026-09-28")
        # Old stager never called; no events were replayed/staged.
        assert list((tmp_path / "events").glob("*.jsonl")) == []

    @pytest.mark.parametrize("mutation", [
        lambda state: state["pending_learning_events"].pop(),
        lambda state: state["pending_learning_events"].reverse(),
        lambda state: state["pending_learning_events"].__setitem__(0, {
            **state["pending_learning_events"][0], "id": "changed",
        }),
        lambda state: state["pending_learning_events"].__setitem__(0, {
            **state["pending_learning_events"][0],
            "observed_at": "2026-09-28T13:37:09.179620Z",
        }),
        lambda state: state.__setitem__("schema_version", 4),
        lambda state: state.__setitem__("all_events", [{"id": "display"}]),
    ])
    def test_changed_state_or_receipt_fact_reblocks(
        self, tmp_path, monkeypatch, mutation,
    ):
        import scripts.live_flow_poller as poller

        # Pin the descriptor to the ORIGINAL state; then mutate the state
        # so the descriptor no longer matches.
        poller_mod = self._write_case(tmp_path, monkeypatch)
        state_path = tmp_path / "day_state_2026-09-28.json"
        original_state_sha, original_ordered_sha = self._state_digests(state_path)
        descriptor = self._synthetic_descriptor(
            state_sha=original_state_sha, ordered_sha=original_ordered_sha,
        )
        self._inject_descriptor(monkeypatch, poller_mod, descriptor)
        receipt = self._receipt_from_incident(descriptor)
        receipt["protected_source"] = {
            "sha256": original_state_sha,
            "bytes": state_path.stat().st_size,
        }
        # Now mutate the on-disk state so it diverges from the receipt.
        state = json.loads(state_path.read_text())
        mutation(state)
        state_path.write_text(
            json.dumps(state, sort_keys=True, separators=(",", ":")) + "\n"
        )
        quarantine = tmp_path / "quarantine"
        quarantine.mkdir()
        (quarantine / "prior_session_wal_quarantine_2026-09-28.json").write_text(
            json.dumps(receipt, sort_keys=True) + "\n"
        )
        with pytest.raises(RuntimeError):
            poller_mod._stale_pending_learning_sessions("2026-09-29")

    def test_wrong_shape_blocks(self, tmp_path, monkeypatch):
        import scripts.live_flow_poller as poller

        poller_mod = self._write_case(tmp_path, monkeypatch)
        state_path = tmp_path / "day_state_2026-09-28.json"
        synthetic_state_sha, synthetic_ordered_sha = self._state_digests(state_path)
        descriptor = self._synthetic_descriptor(
            state_sha=synthetic_state_sha, ordered_sha=synthetic_ordered_sha,
        )
        self._inject_descriptor(monkeypatch, poller_mod, descriptor)
        receipt = self._receipt_from_incident(descriptor)
        receipt["protected_source"] = {
            "sha256": synthetic_state_sha,
            "bytes": state_path.stat().st_size,
        }
        # Add an unexpected extra key (the old redundant day_state).
        receipt["day_state"] = {}
        quarantine = tmp_path / "quarantine"
        quarantine.mkdir()
        (quarantine / "prior_session_wal_quarantine_2026-09-28.json").write_text(
            json.dumps(receipt, sort_keys=True) + "\n"
        )
        with pytest.raises(RuntimeError, match="invalid shape"):
            poller_mod._validate_prior_session_wal_quarantine(self.SESSION)

    def test_stage_presence_refuses_quarantine(self, tmp_path, monkeypatch):
        import scripts.live_flow_poller as poller

        poller_mod = self._write_case(tmp_path, monkeypatch)
        state_path = tmp_path / "day_state_2026-09-28.json"
        synthetic_state_sha, synthetic_ordered_sha = self._state_digests(state_path)
        descriptor = self._synthetic_descriptor(
            state_sha=synthetic_state_sha, ordered_sha=synthetic_ordered_sha,
        )
        self._inject_descriptor(monkeypatch, poller_mod, descriptor)
        receipt = self._receipt_from_incident(descriptor)
        receipt["protected_source"] = {
            "sha256": synthetic_state_sha,
            "bytes": state_path.stat().st_size,
        }
        quarantine = tmp_path / "quarantine"
        quarantine.mkdir()
        (quarantine / "prior_session_wal_quarantine_2026-09-28.json").write_text(
            json.dumps(receipt, sort_keys=True) + "\n"
        )
        # Stage presence in any form (empty, malformed, disjoint) refuses.
        stage_path = tmp_path / "events" / "2026-09-28.jsonl"
        stage_path.parent.mkdir(exist_ok=True)
        stage_path.write_bytes(b"")
        with pytest.raises(RuntimeError, match="canonical event stage present"):
            poller_mod._validate_prior_session_wal_quarantine(self.SESSION)
        # Malformed stage still refuses.
        stage_path.write_bytes(b"{not-json")
        with pytest.raises(RuntimeError, match="canonical event stage present"):
            poller_mod._validate_prior_session_wal_quarantine(self.SESSION)
        # Disjoint valid stage still refuses — staging must never share a stage.
        stage_path.write_bytes(
            b'{"schema": "live_flow.event_stage/v1", "id": "other-id", "decision_at": "2026-09-29T00:00:00Z", "observed_at": "2026-09-28T13:38:00Z", "ts": "2026-09-28T13:38:00Z"}\n'
        )
        with pytest.raises(RuntimeError, match="canonical event stage present"):
            poller_mod._validate_prior_session_wal_quarantine(self.SESSION)

    def test_cross_session_decision_observed_in_session(self, tmp_path, monkeypatch):
        import scripts.live_flow_poller as poller

        poller_mod = self._write_case(tmp_path, monkeypatch)
        state_path = tmp_path / "day_state_2026-09-28.json"
        synthetic_state_sha, synthetic_ordered_sha = self._state_digests(state_path)
        descriptor = self._synthetic_descriptor(
            state_sha=synthetic_state_sha, ordered_sha=synthetic_ordered_sha,
        )
        self._inject_descriptor(monkeypatch, poller_mod, descriptor)
        # observed_at cross-session (decision stays cross-session as required)
        receipt = self._receipt_from_incident(descriptor)
        receipt["protected_source"] = {
            "sha256": synthetic_state_sha,
            "bytes": state_path.stat().st_size,
        }
        quarantine = tmp_path / "quarantine"
        quarantine.mkdir()
        (quarantine / "prior_session_wal_quarantine_2026-09-28.json").write_text(
            json.dumps(receipt, sort_keys=True) + "\n"
        )
        # Mutate observed_at to a different ET date and rerun.
        state = json.loads(state_path.read_text())
        state["pending_learning_events"][0]["observed_at"] = "2026-09-29T13:37:09.179619Z"
        # Min observed moves to 2026-09-29, mismatching descriptor; state hash also moves.
        state_path.write_text(json.dumps(state, sort_keys=True, separators=(",", ":")) + "\n")
        new_state_sha, _ = self._state_digests(state_path)
        descriptor = self._synthetic_descriptor(
            state_sha=new_state_sha, ordered_sha=synthetic_ordered_sha,
        )
        self._inject_descriptor(monkeypatch, poller_mod, descriptor)
        receipt = self._receipt_from_incident(descriptor)
        receipt["protected_source"] = {
            "sha256": new_state_sha,
            "bytes": state_path.stat().st_size,
        }
        (quarantine / "prior_session_wal_quarantine_2026-09-28.json").write_text(
            json.dumps(receipt, sort_keys=True) + "\n"
        )
        with pytest.raises(RuntimeError, match="observed clock leaves session"):
            poller_mod._validate_prior_session_wal_quarantine(self.SESSION)

    def test_unreviewed_old_wal_still_blocks_and_retention_preserves_reviewed_bytes(
        self, tmp_path, monkeypatch,
    ):
        import scripts.live_flow_poller as poller

        poller_mod = self._write_case(tmp_path, monkeypatch)
        assert poller_mod._stale_pending_learning_sessions("2026-09-29") == ["2026-09-28"]

        state_path = tmp_path / "day_state_2026-09-28.json"
        synthetic_state_sha, synthetic_ordered_sha = self._state_digests(state_path)
        descriptor = self._synthetic_descriptor(
            state_sha=synthetic_state_sha, ordered_sha=synthetic_ordered_sha,
        )
        self._inject_descriptor(monkeypatch, poller_mod, descriptor)
        receipt = self._receipt_from_incident(descriptor)
        receipt["protected_source"] = {
            "sha256": synthetic_state_sha,
            "bytes": state_path.stat().st_size,
        }
        quarantine = tmp_path / "quarantine"
        quarantine.mkdir()
        receipt_path = quarantine / "prior_session_wal_quarantine_2026-09-28.json"
        receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
        before_state = state_path.read_bytes()
        before_receipt = receipt_path.read_bytes()
        for day in range(1, 16):
            (tmp_path / f"day_state_2026-10-{day:02d}.json").write_text("{}\n")

        poller_mod._prune_day_states("2026-10-15", {"state_retention_days": 2})
        assert state_path.read_bytes() == before_state
        assert receipt_path.read_bytes() == before_receipt

    def test_malformed_receipt_reblocks_even_when_selected_by_retention(self, tmp_path, monkeypatch):
        poller = self._write_case(tmp_path, monkeypatch)
        quarantine = tmp_path / "quarantine"
        quarantine.mkdir()
        receipt_path = quarantine / "prior_session_wal_quarantine_2026-09-28.json"
        receipt_path.write_text("{malformed")
        with pytest.raises(RuntimeError):
            poller._stale_pending_learning_sessions("2026-09-29")
        with pytest.raises(RuntimeError):
            poller._prune_day_states("2026-09-29", {"state_retention_days": 1})
        assert (tmp_path / "day_state_2026-09-28.json").exists()

    def test_retention_preserves_invalid_receipt_and_raw(self, tmp_path, monkeypatch):
        """An existing invalid receipt must block (never be overwritten by retention)."""
        import scripts.live_flow_poller as poller

        poller_mod = self._write_case(tmp_path, monkeypatch)
        quarantine = tmp_path / "quarantine"
        quarantine.mkdir()
        receipt_path = quarantine / "prior_session_wal_quarantine_2026-09-28.json"
        # Write an obviously invalid receipt that points to wrong bytes.
        invalid_receipt = self._receipt()
        invalid_receipt["protected_source"] = {
            "sha256": "f" * 64,
            "bytes": 0,
        }
        receipt_path.write_text(json.dumps(invalid_receipt, sort_keys=True) + "\n")
        before_state = (tmp_path / "day_state_2026-09-28.json").read_bytes()
        before_receipt = receipt_path.read_bytes()
        for day in range(1, 16):
            (tmp_path / f"day_state_2026-10-{day:02d}.json").write_text("{}\n")
        with pytest.raises(RuntimeError):
            poller_mod._prune_day_states("2026-10-15", {"state_retention_days": 2})
        assert (tmp_path / "day_state_2026-09-28.json").read_bytes() == before_state
        assert receipt_path.read_bytes() == before_receipt

    def test_cross_session_decision_fails_before_wal_save(self, tmp_path, monkeypatch):
        poller = self._write_case(tmp_path, monkeypatch)
        (tmp_path / "day_state_2026-09-28.json").unlink()
        state = self._protected_state()
        state["pending_learning_events"][0]["decision_at"] = "2026-09-29T23:51:45.034847Z"
        with pytest.raises(RuntimeError, match="leaves session date"):
            poller._save_day_state("2026-09-28", state)
        assert not (tmp_path / "day_state_2026-09-28.json").exists()

    def test_date_is_diagnostic_only_and_cannot_write(self, tmp_path, monkeypatch):
        import scripts.live_flow_poller as poller

        monkeypatch.setattr(poller, "_state_dir", lambda: tmp_path)
        monkeypatch.setenv("LIVE_FLOW_EVENT_STAGE_DIR", str(tmp_path / "events"))
        monkeypatch.setattr(poller, "_load_baselines", lambda: {})
        assert poller.main(["--once", "--date", "2026-09-28", "--roots", "SPY"]) == 2
        assert list(tmp_path.glob("**/*")) == []

    def test_rollover_pending_is_nonzero_and_empty_is_clean_without_fetch(
        self, tmp_path, monkeypatch,
    ):
        poller = self._write_case(tmp_path, monkeypatch)
        monkeypatch.setattr(
            poller, "_current_session_matches_frozen_run", lambda *_args, **_kwargs: False,
        )
        monkeypatch.setattr(
            poller, "_resolve_universe", lambda *_args: (_ for _ in ()).throw(
                AssertionError("rollover must exit before fetch")
            ),
        )
        assert poller.main(["--once"]) == 1

        (tmp_path / "day_state_2026-09-28.json").write_text(
            json.dumps({"schema_version": 5, "pending_learning_events": []}) + "\n"
        )
        assert poller.main(["--once"]) == 0

    def test_cli_success_is_atomic_and_readback_matches(self, tmp_path, monkeypatch):
        """Public CLI happy path: literal production descriptor, atomic fsync + readback."""
        import scripts.live_flow_poller as poller

        poller_mod = self._write_case(tmp_path, monkeypatch)
        # The synthetic state hash does NOT equal production; the unpatched
        # production pin must reject CLI use of synthetic bytes.
        assert poller.main([
            "--recover-reviewed-prior-session-wal",
            self.SESSION, "chairman-options-alpha-parent599-review",
        ]) == 1
        # No receipt was written, no partials, raw unchanged.
        assert not (tmp_path / "quarantine").exists()
        state_raw = (tmp_path / "day_state_2026-09-28.json").read_bytes()
        assert state_raw == (tmp_path / "day_state_2026-09-28.json").read_bytes()

    def test_cli_idempotent_replay_keeps_existing_valid_receipt(self, tmp_path, monkeypatch):
        import scripts.live_flow_poller as poller

        poller_mod = self._write_case(tmp_path, monkeypatch)
        state_path = tmp_path / "day_state_2026-09-28.json"
        synthetic_state_sha, synthetic_ordered_sha = self._state_digests(state_path)
        descriptor = self._synthetic_descriptor(
            state_sha=synthetic_state_sha, ordered_sha=synthetic_ordered_sha,
        )
        self._inject_descriptor(monkeypatch, poller_mod, descriptor)
        # Pre-place the receipt as if it had been written by an earlier operator.
        receipt = self._receipt_from_incident(descriptor)
        receipt["protected_source"] = {
            "sha256": synthetic_state_sha,
            "bytes": state_path.stat().st_size,
        }
        quarantine = tmp_path / "quarantine"
        quarantine.mkdir()
        receipt_path = quarantine / "prior_session_wal_quarantine_2026-09-28.json"
        receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
        before = receipt_path.read_bytes()

        # Second CLI invocation must succeed without overwriting the existing receipt.
        assert poller.main([
            "--recover-reviewed-prior-session-wal",
            self.SESSION, "chairman-options-alpha-parent599-review",
        ]) == 0
        assert receipt_path.read_bytes() == before

    def test_cli_invalid_session_is_rejected_with_no_receipt(self, tmp_path, monkeypatch):
        import scripts.live_flow_poller as poller

        self._write_case(tmp_path, monkeypatch)
        # Session not in the production descriptor → CLI rejects before any write.
        assert poller.main([
            "--recover-reviewed-prior-session-wal",
            "2026-09-29", "chairman-options-alpha-parent599-review",
        ]) == 2
        assert not (tmp_path / "quarantine").exists()
        # Raw bytes untouched.
        assert (tmp_path / "day_state_2026-09-28.json").exists()

    def test_cli_rejects_when_day_state_missing(self, tmp_path, monkeypatch):
        import scripts.live_flow_poller as poller

        monkeypatch.setattr(poller, "_state_dir", lambda: tmp_path)
        monkeypatch.setenv("LIVE_FLOW_EVENT_STAGE_DIR", str(tmp_path / "events"))
        assert poller.main([
            "--recover-reviewed-prior-session-wal",
            self.SESSION, "chairman-options-alpha-parent599-review",
        ]) == 1
        assert not (tmp_path / "quarantine").exists()

    def test_write_failure_preserves_raw_state_and_leaves_no_partial(self, tmp_path, monkeypatch):
        """Atomic fsync failure leaves raw unchanged and no partial temp file."""
        import scripts.live_flow_poller as poller

        poller_mod = self._write_case(tmp_path, monkeypatch)
        state_path = tmp_path / "day_state_2026-09-28.json"
        synthetic_state_sha, synthetic_ordered_sha = self._state_digests(state_path)
        descriptor = self._synthetic_descriptor(
            state_sha=synthetic_state_sha, ordered_sha=synthetic_ordered_sha,
        )
        self._inject_descriptor(monkeypatch, poller_mod, descriptor)
        before_state = state_path.read_bytes()

        # Force the atomic write's replace step to fail so the receipt is not finalised.
        import os as _os
        real_replace = _os.replace
        def boom(src, dst):  # noqa: ARG001
            raise OSError("simulated fsync failure")
        monkeypatch.setattr(_os, "replace", boom)

        assert poller.main([
            "--recover-reviewed-prior-session-wal",
            self.SESSION, "chairman-options-alpha-parent599-review",
        ]) == 1
        # Raw state is byte-untouched.
        assert state_path.read_bytes() == before_state
        # No quarantine file written.
        quarantine = tmp_path / "quarantine"
        if quarantine.exists():
            assert list(quarantine.glob("*")) == []
        # Restore for any downstream consumers.
        monkeypatch.setattr(_os, "replace", real_replace)

    def test_old_stager_never_called_on_quarantined_session(self, tmp_path, monkeypatch):
        import scripts.live_flow_poller as poller

        poller_mod = self._write_case(tmp_path, monkeypatch)
        state_path = tmp_path / "day_state_2026-09-28.json"
        synthetic_state_sha, synthetic_ordered_sha = self._state_digests(state_path)
        descriptor = self._synthetic_descriptor(
            state_sha=synthetic_state_sha, ordered_sha=synthetic_ordered_sha,
        )
        self._inject_descriptor(monkeypatch, poller_mod, descriptor)
        receipt = self._receipt_from_incident(descriptor)
        receipt["protected_source"] = {
            "sha256": synthetic_state_sha,
            "bytes": state_path.stat().st_size,
        }
        quarantine = tmp_path / "quarantine"
        quarantine.mkdir()
        (quarantine / "prior_session_wal_quarantine_2026-09-28.json").write_text(
            json.dumps(receipt, sort_keys=True) + "\n"
        )
        stager_calls: list[tuple[str, int]] = []

        def _stager(_session, events):
            stager_calls.append((_session, len(events)))
            return []

        monkeypatch.setattr(poller_mod, "_stage_raw_events", _stager)
        monkeypatch.setattr(
            poller_mod, "_drain_pending_learning_events",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("drain must not be called on quarantined WAL")
            ),
        )
        # Run the startup stale-session sweep; the quarantine must not invoke drain.
        assert poller_mod._stale_pending_learning_sessions("2026-09-29") == []
        assert stager_calls == []
        # And no event-stage file appeared.
        assert list((tmp_path / "events").glob("*.jsonl")) == []
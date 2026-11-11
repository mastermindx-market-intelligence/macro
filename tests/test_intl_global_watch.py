"""IM18 contract checks: the GS-local watch-condition lifecycle (IM18 engine half).

The evaluator is pure over recorded evidence rows: every fixture here is either a
real ``build_observation`` / ``dislocation_own_history`` output or a minimal
cut-down of one (only where the real builder cannot omit a required field, e.g. a
missing ingestion clock). Fixture helpers are copied from
``tests/test_intl_global_observation.py`` / ``tests/test_intl_global_dislocation.py``
per the lane commission, never imported from them.
"""
from __future__ import annotations

import ast
import hashlib
import subprocess
import sys
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path

import pytest

from engine.intl_global_dislocation import (
    KINDS as DISLOCATION_KINDS,
    dislocation_own_history,
)
from engine.intl_global_observation import build_observation
from engine.intl_global_watch import (
    CONDITION_KINDS,
    CONTRACT_VERSION,
    DECLARED_NOT_IMPLEMENTED,
    INTERPRETATION_LIMITS,
    ROW_KEYS,
    STATES,
    TRANSITIONS,
    WatchError,
    evaluate_watch,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

RIGHTS = {"decision_ref": "chairman:2026-10-09:user-facing-redistribution-confirmed",
          "scope": "intl-index-fx-eod-user-facing-v1"}
INCUMBENT = {"quality": "qualified", "reason": None,
             "decision_ref": "derived-evaluation:sha256:abc"}
EVIDENCE = "saved-parquet:sha256:one|saved-parquet:sha256:two"
COMPUTED_AT = "2026-10-09T20:30:00+00:00"
BASE_END = date(2026, 10, 7)

# Language ceilings copied from the IM17 contract (engine/intl_transmission_evidence.py);
# the watch module may not import that module, so the scans are copied here.
FORBIDDEN_OUTPUT_KEY_PARTS = ("score", "centrality", "percentile",
                              "connectedness", "country_exposure",
                              "total_exposure", "exposure_pct", "composite")
CAUSAL_TERMS_EN = ("caused", "causes", "causing", "cause of", "drove", "drives",
                   "driven by", "triggered", "triggers", "led to",
                   "spilled over", "contagion from")
CAUSAL_TERMS_ZH = ("导致", "引发", "造成", "传染")
FORBIDDEN_WORDS = {"cheap", "expensive", "bottom", "entry", "buy", "sell",
                   "oversold", "overbought", "undervalued", "overvalued",
                   "bargain", "opportunity"}


# ---------------------------------------------------------------------------
# Observation fixtures (copied pattern from tests/test_intl_global_observation.py)
# ---------------------------------------------------------------------------

def _obs_identity(tag: str, window, horizon="1m", currency_basis="usd_unhedged"):
    return {
        "universe_id": "JP", "market_id": "JP", "index_id": "^N225",
        "fx_id": "USDJPY=X", "horizon": horizon,
        "currency_basis": currency_basis, "return_basis": "price",
        "window_start": window[0], "window_end": window[1],
        "source_content_sha256": hashlib.sha256(tag.encode()).hexdigest(),
    }


def _obs(*, tag="obs-a", window=("2026-09-08T00:00:00", "2026-10-07T00:00:00"),
         ingestion_at="2026-10-09T15:00:00+00:00",
         ingestion_precision="exact", rights="default", horizon="1m",
         currency_basis="usd_unhedged", local_pct=5.0, fx_pct=-10.0):
    usd_pct = ((1.0 + local_pct / 100.0) * (1.0 + fx_pct / 100.0) - 1.0) * 100.0
    clocks = {
        "observation": {"at": f"{window[1][:10]}T00:00:00", "precision": "session_date"},
        "source_publication": {"at": ingestion_at, "precision": "exact"},
        "ingestion": {"at": ingestion_at, "precision": ingestion_precision},
        "computation": {"at": ingestion_at, "precision": "exact"},
    }
    return build_observation(
        identity=_obs_identity(tag, window, horizon, currency_basis),
        clocks=clocks,
        values={"local_pct": local_pct, "usd_pct": usd_pct, "fx_pct": fx_pct},
        rights=dict(RIGHTS) if rights == "default" else rights,
        incumbent=dict(INCUMBENT), evidence_ref=EVIDENCE)


def _flat_obs(k: int, local_pct: float):
    """Local-basis monthly observation copied from the IM15 fixture pattern."""
    total = BASE_END.year * 12 + BASE_END.month - 1 - k
    end = date(total // 12, total % 12 + 1, BASE_END.day)
    total -= 1
    start = date(total // 12, total % 12 + 1, BASE_END.day)
    stamp = f"{end + timedelta(days=2)}T15:00:00+00:00"
    identity = _obs_identity(f"flat:{k}", (f"{start}T00:00:00", f"{end}T00:00:00"),
                             currency_basis="local")
    return build_observation(
        identity=identity,
        clocks={
            "observation": {"at": f"{end}T00:00:00", "precision": "session_date"},
            "source_publication": {"at": stamp, "precision": "exact"},
            "ingestion": {"at": stamp, "precision": "exact"},
            "computation": {"at": stamp, "precision": "exact"},
        },
        values={"local_pct": local_pct, "usd_pct": None, "fx_pct": None},
        rights=dict(RIGHTS), incumbent=dict(INCUMBENT), evidence_ref=EVIDENCE)


def _flat_references(count: int = 24) -> list[dict]:
    return [_flat_obs(k, 3.2 if k % 2 else -3.2) for k in range(1, count + 1)]


# ---------------------------------------------------------------------------
# Dislocation fixtures: minimal cut-down receipts of dislocation_own_history
# output (the fields the watch evaluator reads), for precise lifecycle control.
# ---------------------------------------------------------------------------

def _disl(*, evidence_id="disl:sha256:1", kind="own_history_return",
          window=("2026-09-08T00:00:00", "2026-10-07T00:00:00"),
          computation_at="2026-10-09T20:30:00Z", ingestion_at=None,
          state="qualified", abstain_reasons=(),
          attention="outside_reference_range", direction="above",
          universe_id="JP", horizon="1m", currency_basis="usd_unhedged"):
    clocks = {
        "observation": {"at": f"{window[1][:10]}T00:00:00", "precision": "session_date"},
        "source_publication": {"at": computation_at, "precision": "exact"},
        "computation": {"at": computation_at, "precision": "exact"},
    }
    if ingestion_at is not None:
        clocks["ingestion"] = {"at": ingestion_at, "precision": "exact"}
    return {
        "contract_version": "intl-global-dislocation-v1",
        "dislocation_id": evidence_id,
        "kind": kind,
        "comparison_mode": "own_history",
        "peer_rule": None,
        "subject": {
            "observation_id": "obs:sha256:subject",
            "universe_id": universe_id, "market_id": universe_id,
            "horizon": horizon, "currency_basis": currency_basis,
            "return_basis": "price",
            "window_start": window[0], "window_end": window[1],
            "state": state, "abstain_reasons": list(abstain_reasons),
            "decomposition": None,
        },
        "clocks": clocks,
        "state": state,
        "abstain_reasons": list(abstain_reasons),
        "evidence": {
            "statistic": "modified_z", "subject_value": 4.0, "center": 0.0,
            "mad": 1.0, "modified_z": 2.6979999999999997,
            "attention": attention, "direction": direction, "rank": None,
        },
    }


def _watch(**overrides):
    watch = {
        "watch_id": "watch-jp-1m-usd-001",
        "condition": {"kind": "dislocation_attention",
                      "dislocation_kind": "own_history_return",
                      "attention": "outside_reference_range",
                      "direction": "any"},
        "scope": {"universe_id": "JP", "horizon": "1m",
                  "currency_basis": "usd_unhedged"},
        "created_at": "2026-09-01T00:00:00Z",
        "expires_at": None,
        "evidence_due_at": None,
        "max_evidence_age_days": 35,
    }
    watch.update(overrides)
    return watch


def _eval(watch, evidence, at, previous=None):
    return evaluate_watch(watch, evidence, evaluated_at=at, previous=previous)


# ---------------------------------------------------------------------------
# 0 vocabulary and row shape
# ---------------------------------------------------------------------------

def test_module_vocabularies_are_frozen():
    assert CONTRACT_VERSION == "intl-global-watch-v1"
    assert CONDITION_KINDS == ("dislocation_attention", "observation_qualified")
    assert DECLARED_NOT_IMPLEMENTED == ("transmission_status",
                                        "dollar_credit_state",
                                        "scenario_threshold")
    assert STATES == ("pending", "armed", "triggered", "withheld",
                      "corrected", "expired")
    assert TRANSITIONS == ("pending", "withheld", "paused", "first_observation",
                           "qualified", "persisted", "resolved", "revised",
                           "expired", "none")
    assert INTERPRETATION_LIMITS == (
        "A watch reports whether recorded evidence meets a stated condition; "
        "it is not a forecast.",
        "Escalation and acknowledgement are owned by the incumbent "
        "investigation workflow.")


def test_row_keys_and_declared_fields():
    row = _eval(_watch(), [], "2026-10-31T12:00:00Z")
    assert set(row) == set(ROW_KEYS)
    assert row["contract_version"] == CONTRACT_VERSION
    assert row["watch_id"] == "watch-jp-1m-usd-001"
    assert row["state"] == "pending"
    assert row["evaluated_at"] == "2026-10-31T12:00:00Z"
    assert row["condition"] == _watch()["condition"]
    assert row["scope"] == _watch()["scope"]
    assert row["evaluation_id"].startswith("watch:sha256:")
    assert len(row["evaluation_id"]) == len("watch:sha256:") + 64
    int(row["evaluation_id"].split(":", 2)[2], 16)  # 64 hex chars
    assert row["dependency_id"] == row["evaluation_id"]
    assert row["caveats"] == ["track_record_unavailable"]
    assert row["track_record"] is None
    assert row["last_check"] == {"at": "2026-10-31T12:00:00Z",
                                 "evidence_offered": 0,
                                 "evidence_considered": 0}
    assert row["consumes"] == []
    assert row["evidence_ref"] is None
    assert row["evidence_age_days"] is None
    assert row["prior_state"] is None
    assert row["supersedes"] is None
    assert row["previous"] is None


def test_instant_normalisation_accepts_z_offset_and_naive():
    row = _eval(_watch(), [], "2026-10-31T13:00:00+00:00")
    assert row["evaluated_at"] == "2026-10-31T13:00:00Z"
    row = _eval(_watch(created_at="2026-09-01T09:00:00"), [], "2026-10-31T12:00:00Z")
    assert row["evaluated_at"] == "2026-10-31T12:00:00Z"
    row = _eval(_watch(), [], "2026-10-31T21:00:00+09:00")
    assert row["evaluated_at"] == "2026-10-31T12:00:00Z"


# ---------------------------------------------------------------------------
# 1 lifecycle chain
# ---------------------------------------------------------------------------

def test_lifecycle_chain_first_observation_qualified_persisted_paused_persisted_resolved():
    watch = _watch()
    e1 = _disl(evidence_id="disl:sha256:e1",
               window=("2026-08-08T00:00:00", "2026-09-07T00:00:00"),
               computation_at="2026-09-08T20:30:00Z",
               attention="within_reference_range", direction="at_center")
    r1 = _eval(watch, [e1], "2026-09-10T12:00:00Z")
    assert r1["state"] == "armed"
    assert r1["outcome"] == "not_met"
    assert r1["transition"] == "first_observation"
    assert r1["active_trigger"] is False
    assert r1["consecutive_triggered"] == 0
    assert r1["seen_qualified"] is True
    assert r1["first_triggered_at"] is None
    assert r1["evidence_ref"]["evidence_id"] == "disl:sha256:e1"
    assert r1["evidence_age_days"] == 3
    assert r1["consumes"] == ["disl:sha256:e1"]

    e2 = _disl(evidence_id="disl:sha256:e2",
               window=("2026-09-08T00:00:00", "2026-10-07T00:00:00"),
               computation_at="2026-10-08T20:30:00Z")
    r2 = _eval(watch, [e2], "2026-10-10T12:00:00Z", previous=r1)
    assert r2["prior_state"] == "armed"
    assert r2["state"] == "triggered"
    assert r2["outcome"] == "met"
    assert r2["transition"] == "qualified"
    assert r2["active_trigger"] is True
    assert r2["consecutive_triggered"] == 1
    assert r2["first_triggered_at"] == "2026-10-10T12:00:00Z"

    e3 = _disl(evidence_id="disl:sha256:e3",
               window=("2026-10-08T00:00:00", "2026-11-07T00:00:00"),
               computation_at="2026-11-08T20:30:00Z")
    r3 = _eval(watch, [e3], "2026-11-10T12:00:00Z", previous=r2)
    assert r3["transition"] == "persisted"
    assert r3["consecutive_triggered"] == 2
    assert r3["first_triggered_at"] == "2026-10-10T12:00:00Z"

    r4 = _eval(watch, [], "2026-11-20T12:00:00Z", previous=r3)
    assert r4["state"] == "withheld"
    assert r4["outcome"] is None
    assert r4["transition"] == "paused"
    assert r4["reasons"] == ["evidence_missing"]
    assert r4["active_trigger"] is True
    assert r4["consecutive_triggered"] == 2
    assert r4["first_triggered_at"] == "2026-10-10T12:00:00Z"
    assert r4["evidence_ref"] is None
    assert r4["evidence_age_days"] is None
    assert r4["consumes"] == []

    e5 = _disl(evidence_id="disl:sha256:e5",
               window=("2026-11-08T00:00:00", "2026-12-07T00:00:00"),
               computation_at="2026-12-08T20:30:00Z")
    r5 = _eval(watch, [e5], "2026-12-10T12:00:00Z", previous=r4)
    assert r5["transition"] == "persisted"
    assert r5["consecutive_triggered"] == 3
    assert r5["prior_state"] == "withheld"

    e6 = _disl(evidence_id="disl:sha256:e6",
               window=("2026-12-08T00:00:00", "2027-01-07T00:00:00"),
               computation_at="2027-01-08T20:30:00Z",
               attention="within_reference_range", direction="at_center")
    r6 = _eval(watch, [e6], "2027-01-10T12:00:00Z", previous=r5)
    assert r6["state"] == "armed"
    assert r6["outcome"] == "not_met"
    assert r6["transition"] == "resolved"
    assert r6["active_trigger"] is False
    assert r6["consecutive_triggered"] == 0
    assert r6["first_triggered_at"] == "2026-10-10T12:00:00Z"
    assert [r["transition"] for r in (r1, r2, r3, r4, r5, r6)] == [
        "first_observation", "qualified", "persisted", "paused",
        "persisted", "resolved"]


def test_first_observation_on_a_met_condition_sets_the_trigger_fields():
    watch = _watch()
    met = _disl(evidence_id="disl:sha256:first",
                window=("2026-09-08T00:00:00", "2026-10-07T00:00:00"),
                computation_at="2026-10-08T20:30:00Z")
    row = _eval(watch, [met], "2026-10-10T12:00:00Z")
    assert row["transition"] == "first_observation"
    assert row["state"] == "triggered"
    assert row["outcome"] == "met"
    assert row["active_trigger"] is True
    assert row["consecutive_triggered"] == 1
    assert row["first_triggered_at"] == "2026-10-10T12:00:00Z"
    assert row["seen_qualified"] is True


def test_missing_data_after_trigger_never_resolves():
    watch = _watch()
    triggered = _disl(evidence_id="disl:sha256:t",
                      window=("2026-09-08T00:00:00", "2026-10-07T00:00:00"),
                      computation_at="2026-10-08T20:30:00Z")
    base = _eval(watch, [triggered], "2026-10-10T12:00:00Z")
    assert base["active_trigger"] is True
    for at in ("2026-10-20T12:00:00Z", "2026-11-20T12:00:00Z",
               "2027-06-20T12:00:00Z"):
        row = _eval(watch, [], at, previous=base)
        assert row["state"] == "withheld"
        assert row["transition"] == "paused"
        assert row["reasons"] == ["evidence_missing"]
        assert row["outcome"] is None
        assert row["active_trigger"] is True
        assert row["consecutive_triggered"] == 1
        assert row["first_triggered_at"] == base["first_triggered_at"]


# ---------------------------------------------------------------------------
# 2 precedence: abstain > stale > corrected > qualified
# ---------------------------------------------------------------------------

def _triggered_previous(watch, at="2026-10-10T12:00:00Z"):
    met = _disl(evidence_id="disl:sha256:x",
                window=("2026-09-08T00:00:00", "2026-10-07T00:00:00"),
                computation_at="2026-10-08T20:30:00Z")
    return _eval(watch, [met], at)


def test_abstain_beats_stale():
    watch = _watch()
    previous = _triggered_previous(watch)
    # A dislocation receipt that abstains AND whose window is far too old.
    abstain_old = _disl(evidence_id="disl:sha256:ab",
                        window=("2026-07-08T00:00:00", "2026-08-31T00:00:00"),
                        computation_at="2026-09-02T20:30:00Z",
                        state="abstain",
                        abstain_reasons=["insufficient_reference_history"])
    row = _eval(watch, [abstain_old], "2026-10-31T12:00:00Z", previous=previous)
    assert row["state"] == "withheld"
    assert row["reasons"] == ["insufficient_reference_history"]  # verbatim
    assert "evidence_stale" not in row["reasons"]
    assert row["transition"] == "paused"
    assert row["outcome"] is None
    assert row["active_trigger"] is True
    assert row["evidence_ref"]["state"] == "abstain"
    assert row["consumes"] == ["disl:sha256:ab"]

    # Same precedence with a real abstaining observation (rights unconfirmed)
    # whose window is equally stale, on an observation_qualified watch.
    obs_watch = _watch(condition={"kind": "observation_qualified"})
    obs_previous = _eval(
        obs_watch,
        [_obs(tag="obs-prev",
              window=("2026-09-08T00:00:00", "2026-10-07T00:00:00"),
              ingestion_at="2026-10-09T15:00:00+00:00")],
        "2026-10-10T12:00:00Z")
    assert obs_previous["state"] == "triggered"
    abstain_obs = _obs(tag="obs-abstain",
                       window=("2026-08-01T00:00:00", "2026-08-31T00:00:00"),
                       ingestion_at="2026-09-02T15:00:00+00:00",
                       rights=None)
    assert abstain_obs["state"] == "abstain"
    assert abstain_obs["abstain_reasons"] == ["rights_unconfirmed"]
    row = _eval(obs_watch, [abstain_obs], "2026-10-31T12:00:00Z",
                previous=obs_previous)
    assert row["state"] == "withheld"
    assert row["reasons"] == ["rights_unconfirmed"]
    assert "evidence_stale" not in row["reasons"]
    assert row["transition"] == "paused"
    # Without an active trigger the same abstain withholds, it does not pause.
    fresh = _eval(watch, [abstain_old], "2026-10-31T12:00:00Z")
    assert fresh["state"] == "withheld"
    assert fresh["transition"] == "withheld"
    assert fresh["reasons"] == ["insufficient_reference_history"]


def test_stale_beats_corrected():
    watch = _watch()
    previous = _triggered_previous(watch)
    # Same window as the previous evidence, a different id, but evaluated so
    # late that the window is beyond max_evidence_age_days.
    revision = _disl(evidence_id="disl:sha256:y",
                     window=("2026-09-08T00:00:00", "2026-10-07T00:00:00"),
                     computation_at="2026-10-11T20:30:00Z")
    row = _eval(watch, [revision], "2026-11-30T12:00:00Z", previous=previous)
    assert row["state"] == "withheld"
    assert row["reasons"] == ["evidence_stale"]
    assert row["transition"] == "paused"
    assert row["state"] != "corrected"
    assert row["supersedes"] is None
    assert row["outcome"] is None
    assert row["evidence_age_days"] == 54
    assert row["active_trigger"] is True


def test_corrected_beats_qualified_with_previous_verbatim():
    watch = _watch()
    e1 = _disl(evidence_id="disl:sha256:m1",
               window=("2026-08-08T00:00:00", "2026-09-07T00:00:00"),
               computation_at="2026-09-08T20:30:00Z")
    r1 = _eval(watch, [e1], "2026-09-10T12:00:00Z")
    e2 = _disl(evidence_id="disl:sha256:m2",
               window=("2026-09-08T00:00:00", "2026-10-07T00:00:00"),
               computation_at="2026-10-08T20:30:00Z")
    r2 = _eval(watch, [e2], "2026-10-10T12:00:00Z", previous=r1)
    # e1 already set the trigger (first_observation with met), so the next
    # met evidence on a new id persists rather than re-qualifying.
    assert r2["transition"] == "persisted"
    assert r2["consecutive_triggered"] == 2
    # A revision of the SAME window under a NEW id: corrected beats qualified.
    e3 = _disl(evidence_id="disl:sha256:m3",
               window=("2026-09-08T00:00:00", "2026-10-07T00:00:00"),
               computation_at="2026-10-11T20:30:00Z")
    r3 = _eval(watch, [e3], "2026-10-12T12:00:00Z", previous=r2)
    assert r3["state"] == "corrected"
    assert r3["transition"] == "revised"
    assert r3["supersedes"] == "disl:sha256:m2"
    assert r3["outcome"] == "met"
    assert r3["active_trigger"] is True
    assert r3["consecutive_triggered"] == 2  # max(1, previous count)
    assert r3["seen_qualified"] is True
    assert r3["evidence_ref"]["evidence_id"] == "disl:sha256:m3"
    # The previous row is embedded verbatim with its own previous stripped.
    assert r3["previous"] == {**r2, "previous": None}
    assert r3["previous"]["previous"] is None
    assert r3["previous"]["evaluation_id"] == r2["evaluation_id"]

    # A revision that lands not_met clears the trigger and the count.
    e4 = _disl(evidence_id="disl:sha256:m4",
               window=("2026-09-08T00:00:00", "2026-10-07T00:00:00"),
               computation_at="2026-10-13T20:30:00Z",
               attention="within_reference_range", direction="at_center")
    r4 = _eval(watch, [e4], "2026-10-14T12:00:00Z", previous=r3)
    assert r4["state"] == "corrected"
    assert r4["transition"] == "revised"
    assert r4["supersedes"] == "disl:sha256:m3"
    assert r4["outcome"] == "not_met"
    assert r4["active_trigger"] is False
    assert r4["consecutive_triggered"] == 0


def test_corrected_observation_revision_uses_observation_id():
    watch = _watch(condition={"kind": "observation_qualified"})
    first = _obs(tag="obs-v1",
                 window=("2026-09-08T00:00:00", "2026-10-07T00:00:00"),
                 ingestion_at="2026-10-09T15:00:00+00:00")
    r1 = _eval(watch, [first], "2026-10-10T12:00:00Z")
    assert r1["evidence_ref"]["kind"] == "observation"
    assert r1["evidence_ref"]["evidence_id"] == first["observation_id"]
    second = _obs(tag="obs-v2",
                  window=("2026-09-08T00:00:00", "2026-10-07T00:00:00"),
                  ingestion_at="2026-10-11T15:00:00+00:00")
    assert second["observation_id"] != first["observation_id"]
    r2 = _eval(watch, [second], "2026-10-12T12:00:00Z", previous=r1)
    assert r2["state"] == "corrected"
    assert r2["transition"] == "revised"
    assert r2["supersedes"] == first["observation_id"]
    assert r2["outcome"] == "met"


# ---------------------------------------------------------------------------
# 3 point-in-time visibility
# ---------------------------------------------------------------------------

def test_future_evidence_is_ignored():
    watch = _watch()
    visible = dict(window=("2026-09-08T00:00:00", "2026-10-07T00:00:00"),
                   computation_at="2026-10-08T20:30:00Z")
    at = "2026-10-31T12:00:00Z"
    # Computation clock after evaluated_at.
    row = _eval(watch, [_disl(evidence_id="disl:sha256:fc",
                              **{**visible,
                                 "computation_at": "2026-11-01T00:00:00Z"})], at)
    assert row["state"] == "pending"
    assert row["reasons"] == ["awaiting_first_evidence"]
    assert row["evidence_ref"] is None
    assert row["last_check"]["evidence_considered"] == 0
    assert row["last_check"]["evidence_offered"] == 1
    # Ingestion clock after evaluated_at even though computation is not.
    row = _eval(watch, [_disl(evidence_id="disl:sha256:fi",
                              ingestion_at="2026-11-01T00:00:00Z",
                              **visible)], at)
    assert row["state"] == "pending"
    # Observation with an exact ingestion instant after evaluated_at.
    obs_watch = _watch(condition={"kind": "observation_qualified"})
    row = _eval(obs_watch, [_obs(ingestion_at="2026-11-15T15:00:00+00:00")], at)
    assert row["state"] == "pending"
    # Observation ingested on a session_date becomes visible only from the
    # next day 00:00Z.
    late_same_day = _obs(ingestion_at="2026-10-31T00:00:00",
                         ingestion_precision="session_date")
    row = _eval(obs_watch, [late_same_day], "2026-10-31T23:59:00Z")
    assert row["state"] == "pending"
    row = _eval(obs_watch, [late_same_day], "2026-11-01T00:00:00Z")
    assert row["state"] == "triggered"
    assert row["transition"] == "first_observation"
    # An observation output without an ingestion clock is never visible; the
    # real builder cannot omit one (it would abstain clock_missing), so this
    # is a minimal cut-down row carrying the observation-v1 output shape.
    no_ingestion = {
        "contract_version": "intl-global-observation-v1",
        "observation_id": "obs:sha256:noing",
        "identity": _obs_identity("noing", ("2026-09-08T00:00:00",
                                            "2026-10-07T00:00:00")),
        "clocks": {
            "observation": {"at": "2026-10-07T00:00:00",
                            "precision": "session_date"},
            "source_publication": {"at": "2026-10-08T15:00:00+00:00",
                                   "precision": "exact"},
            "computation": {"at": "2026-10-08T20:30:00+00:00",
                            "precision": "exact"},
        },
        "state": "qualified",
        "abstain_reasons": [],
    }
    row = _eval(obs_watch, [no_ingestion], at)
    assert row["state"] == "pending"
    assert row["last_check"]["evidence_considered"] == 0


def test_dislocation_with_present_but_unparseable_ingestion_never_becomes_visible():
    # A dislocation record whose ingestion clock is CARRIED but unreadable
    # cannot establish when it became visible: the watch must evaluate to the
    # contract's pending/withheld states, never silently fall back to the
    # computation clock and drive (or resolve) the lifecycle.
    watch = _watch()
    at = "2026-10-31T12:00:00Z"
    carried = _disl(evidence_id="disl:sha256:unreadable",
                    window=("2026-09-08T00:00:00", "2026-10-07T00:00:00"),
                    computation_at="2026-10-09T20:30:00Z",
                    ingestion_at="not-a-timestamp")
    assert "ingestion" in carried["clocks"]  # present, not absent
    row = _eval(watch, [carried], at)
    assert row["state"] == "pending"
    assert row["transition"] == "pending"
    assert row["reasons"] == ["awaiting_first_evidence"]
    assert row["evidence_ref"] is None
    assert row["consumes"] == []
    assert row["last_check"] == {"at": at, "evidence_offered": 1,
                                 "evidence_considered": 0}
    # With an active trigger the same unreadable record pauses the watch —
    # it never re-triggers, resolves or upgrades on unreadable visibility.
    previous = _triggered_previous(watch)
    row = _eval(watch, [carried], at, previous=previous)
    assert row["state"] == "withheld"
    assert row["transition"] == "paused"
    assert row["reasons"] == ["evidence_missing"]
    assert row["active_trigger"] is True
    assert row["consecutive_triggered"] == 1


# ---------------------------------------------------------------------------
# 4 expiry
# ---------------------------------------------------------------------------

def test_expiry_short_circuits_and_repeats_as_none():
    watch = _watch(expires_at="2026-10-15T00:00:00Z")
    previous = _triggered_previous(watch)  # active trigger, state triggered
    row = _eval(watch, [_disl()], "2026-10-15T00:00:00Z", previous=previous)
    assert row["state"] == "expired"
    assert row["outcome"] is None
    assert row["transition"] == "expired"
    assert row["prior_state"] == "triggered"
    assert row["reasons"] == []
    assert row["evidence_ref"] is None
    assert row["evidence_age_days"] is None
    assert row["consumes"] == []
    # The trigger history is carried, not resolved, by expiry.
    assert row["active_trigger"] is True
    assert row["first_triggered_at"] == previous["first_triggered_at"]
    # A later evaluation of the same expired watch stays expired with none.
    again = _eval(watch, [_disl()], "2026-11-01T00:00:00Z", previous=row)
    assert again["state"] == "expired"
    assert again["transition"] == "none"
    assert again["prior_state"] == "expired"
    # One second before expiry the watch still evaluates normally.
    before = _eval(_watch(expires_at="2026-10-15T00:00:00Z"), [],
                   "2026-10-14T23:59:59Z")
    assert before["state"] == "pending"


# ---------------------------------------------------------------------------
# 5 pending vs evidence_missing around evidence_due_at
# ---------------------------------------------------------------------------

def test_pending_vs_evidence_missing_around_evidence_due_at():
    watch = _watch(evidence_due_at="2026-10-20T00:00:00Z")
    row = _eval(watch, [], "2026-10-19T23:59:59Z")
    assert row["state"] == "pending"
    assert row["reasons"] == ["awaiting_first_evidence"]
    assert row["transition"] == "pending"
    assert row["seen_qualified"] is False
    row = _eval(watch, [], "2026-10-20T00:00:00Z")
    assert row["state"] == "withheld"
    assert row["reasons"] == ["evidence_missing"]
    assert row["transition"] == "withheld"
    assert row["outcome"] is None
    # Repeating the same branch keeps reporting the state-named transition.
    row = _eval(watch, [], "2026-10-21T00:00:00Z", previous=row)
    assert row["state"] == "withheld"
    assert row["transition"] == "withheld"
    # No due date at all: the watch stays pending indefinitely.
    open_watch = _watch()
    row = _eval(open_watch, [], "2027-01-01T00:00:00Z")
    assert row["state"] == "pending"
    assert row["reasons"] == ["awaiting_first_evidence"]


# ---------------------------------------------------------------------------
# 6 idempotent re-evaluation of the same evidence
# ---------------------------------------------------------------------------

def test_same_evidence_reevaluation_is_idempotent():
    watch = _watch()
    quiet = _disl(evidence_id="disl:sha256:quiet",
                  window=("2026-09-08T00:00:00", "2026-10-07T00:00:00"),
                  computation_at="2026-10-08T20:30:00Z",
                  attention="within_reference_range", direction="at_center")
    first = _eval(watch, [quiet], "2026-10-10T12:00:00Z")
    assert first["state"] == "armed"
    assert first["evidence_age_days"] == 3
    # A later replay of the same evidence with the same (empty) prior state
    # must land the identical evaluation identity: evaluated_at, last_check,
    # evidence_age_days and transition are excluded from the hash.
    replay = _eval(watch, [quiet], "2026-10-20T12:00:00Z")
    assert replay["state"] == "armed"
    assert replay["evidence_age_days"] == 13  # only the excluded fields moved
    assert replay["evaluation_id"] == first["evaluation_id"]
    # Feeding the row back in as previous: the same evidence changes nothing.
    later = _eval(watch, [quiet], "2026-10-20T12:00:00Z", previous=first)
    assert later["state"] == "armed"
    assert later["transition"] == "none"
    assert later["consecutive_triggered"] == 0  # no count change
    assert later["active_trigger"] is False
    assert later["evidence_age_days"] == 13     # age advances
    assert later["last_check"]["at"] == "2026-10-20T12:00:00Z"
    # The same holds on an active trigger: the count never moves on a repeat.
    met = _disl(evidence_id="disl:sha256:same",
                window=("2026-09-08T00:00:00", "2026-10-07T00:00:00"),
                computation_at="2026-10-08T20:30:00Z")
    r1 = _eval(watch, [met], "2026-10-10T12:00:00Z")
    assert r1["transition"] == "first_observation"
    assert r1["consecutive_triggered"] == 1
    r2 = _eval(watch, [met], "2026-10-20T12:00:00Z", previous=r1)
    assert r2["transition"] == "none"
    assert r2["consecutive_triggered"] == 1
    assert r2["active_trigger"] is True
    assert r2["first_triggered_at"] == r1["first_triggered_at"]


# ---------------------------------------------------------------------------
# 7 condition semantics
# ---------------------------------------------------------------------------

def test_direction_semantics():
    watch = _watch()
    at = "2026-10-10T12:00:00Z"
    base = dict(window=("2026-09-08T00:00:00", "2026-10-07T00:00:00"),
                computation_at="2026-10-08T20:30:00Z")
    def row_for(direction, evidence_direction, attention="outside_reference_range"):
        return _eval(_watch(condition={"kind": "dislocation_attention",
                                       "dislocation_kind": "own_history_return",
                                       "attention": "outside_reference_range",
                                       "direction": direction}),
                     [_disl(direction=evidence_direction, attention=attention,
                            **base)], at)
    assert row_for("above", "above")["outcome"] == "met"
    assert row_for("above", "below")["outcome"] == "not_met"
    assert row_for("below", "below")["outcome"] == "met"
    assert row_for("below", "above")["outcome"] == "not_met"
    # "any" must not collapse to "above": a below-direction dislocation meets it.
    assert row_for("any", "below")["outcome"] == "met"
    assert row_for("any", "above")["outcome"] == "met"
    # Attention outside the reference range is required even for "any".
    assert row_for("any", "below", attention="within_reference_range")["outcome"] == "not_met"


def test_relevance_requires_matching_family_kind_scope_and_contract():
    watch = _watch()
    at = "2026-10-10T12:00:00Z"
    good = dict(window=("2026-09-08T00:00:00", "2026-10-07T00:00:00"),
                computation_at="2026-10-08T20:30:00Z")
    wrong_kind = _disl(kind="own_history_fx", **good)
    assert _eval(watch, [wrong_kind], at)["state"] == "pending"
    wrong_universe = _disl(universe_id="KR", **good)
    assert _eval(watch, [wrong_universe], at)["state"] == "pending"
    wrong_horizon = _disl(horizon="3m", **good)
    assert _eval(watch, [wrong_horizon], at)["state"] == "pending"
    wrong_basis = _disl(currency_basis="local", **good)
    assert _eval(watch, [wrong_basis], at)["state"] == "pending"
    wrong_family = _obs()
    assert _eval(watch, [wrong_family], at)["state"] == "pending"
    assert _eval(watch, [wrong_family], at)["last_check"]["evidence_considered"] == 0


def test_real_receipts_drive_the_lifecycle():
    watch = _watch(condition={"kind": "dislocation_attention",
                              "dislocation_kind": "own_history_return",
                              "attention": "outside_reference_range",
                              "direction": "any"},
                   scope={"universe_id": "JP", "horizon": "1m",
                          "currency_basis": "local"})
    references = _flat_references(24)
    ordinary = dislocation_own_history(
        _flat_obs(0, 15.0), references, kind="own_history_return",
        computed_at=COMPUTED_AT)
    assert ordinary["state"] == "qualified"
    assert ordinary["evidence"]["attention"] == "within_reference_range"
    row = _eval(watch, [ordinary], "2026-10-20T12:00:00Z")
    assert row["state"] == "armed"
    assert row["outcome"] == "not_met"
    assert row["transition"] == "first_observation"
    assert row["evidence_ref"]["evidence_id"] == ordinary["dislocation_id"]
    assert row["evidence_age_days"] == 13

    extreme = dislocation_own_history(
        _flat_obs(0, 44.8), references, kind="own_history_return",
        computed_at=COMPUTED_AT)
    assert extreme["state"] == "qualified"
    assert extreme["evidence"]["attention"] == "outside_reference_range"
    assert extreme["evidence"]["direction"] == "above"
    row = _eval(watch, [extreme], "2026-10-20T12:00:00Z", previous=row)
    assert row["state"] == "triggered"
    assert row["transition"] == "qualified"

    abstained = dislocation_own_history(
        _flat_obs(0, 15.0), _flat_references(19), kind="own_history_return",
        computed_at=COMPUTED_AT)
    assert abstained["state"] == "abstain"
    assert "insufficient_reference_history" in abstained["abstain_reasons"]
    row = _eval(watch, [abstained], "2026-10-20T12:00:00Z", previous=row)
    assert row["state"] == "withheld"
    assert row["reasons"] == abstained["abstain_reasons"]  # verbatim carry
    assert row["transition"] == "paused"
    assert row["active_trigger"] is True


def test_observation_qualified_semantics():
    watch = _watch(condition={"kind": "observation_qualified"})
    qualified = _obs(tag="obs-q",
                     window=("2026-09-08T00:00:00", "2026-10-07T00:00:00"),
                     ingestion_at="2026-10-09T15:00:00+00:00")
    assert qualified["state"] == "qualified"
    row = _eval(watch, [qualified], "2026-10-10T12:00:00Z")
    assert row["outcome"] == "met"
    assert row["state"] == "triggered"
    assert row["transition"] == "first_observation"
    assert row["evidence_ref"]["state"] == "qualified"
    assert row["evidence_ref"]["window_start"] == "2026-09-08T00:00:00"
    assert row["evidence_ref"]["window_end"] == "2026-10-07T00:00:00"


# ---------------------------------------------------------------------------
# 8 latest-evidence selection
# ---------------------------------------------------------------------------

def test_latest_selection_tiebreaks():
    watch = _watch()
    at = "2026-10-31T12:00:00Z"
    older_window_newer_clock = _disl(
        evidence_id="disl:sha256:old-win",
        window=("2026-09-08T00:00:00", "2026-10-07T00:00:00"),
        computation_at="2026-10-09T20:30:00Z",
        attention="within_reference_range", direction="at_center")
    newer_window_older_clock = _disl(
        evidence_id="disl:sha256:new-win",
        window=("2026-10-08T00:00:00", "2026-10-14T00:00:00"),
        computation_at="2026-10-08T20:30:00Z")
    row = _eval(watch, [older_window_newer_clock, newer_window_older_clock], at)
    # Greatest window_end wins even when its visibility instant is older.
    assert row["evidence_ref"]["evidence_id"] == "disl:sha256:new-win"
    assert row["last_check"]["evidence_offered"] == 2
    assert row["last_check"]["evidence_considered"] == 2

    same_window = ("2026-09-08T00:00:00", "2026-10-07T00:00:00")
    early = _disl(evidence_id="disl:sha256:early", window=same_window,
                  computation_at="2026-10-08T20:30:00Z")
    late = _disl(evidence_id="disl:sha256:late", window=same_window,
                 computation_at="2026-10-09T20:30:00Z")
    row = _eval(watch, [early, late], at)
    # Equal window_end: the latest visibility instant wins.
    assert row["evidence_ref"]["evidence_id"] == "disl:sha256:late"

    tied_low = _disl(evidence_id="disl:sha256:b", window=same_window,
                     computation_at="2026-10-09T20:30:00Z")
    tied_high = _disl(evidence_id="disl:sha256:c", window=same_window,
                      computation_at="2026-10-09T20:30:00Z")
    row = _eval(watch, [tied_high, tied_low], at)
    # Full tie: ascending evidence id is the final deterministic tiebreak.
    assert row["evidence_ref"]["evidence_id"] == "disl:sha256:b"


def test_evidence_age_boundary_is_strictly_above_max():
    watch = _watch()  # max_evidence_age_days = 35
    at = "2026-10-31T12:00:00Z"
    exactly_max = _disl(window=("2026-08-09T00:00:00", "2026-09-26T00:00:00"),
                        computation_at="2026-09-27T20:30:00Z")
    row = _eval(watch, [exactly_max], at)
    assert row["evidence_age_days"] == 35
    assert row["state"] == "triggered"  # age == max is NOT stale
    just_over = _disl(window=("2026-08-08T00:00:00", "2026-09-25T00:00:00"),
                      computation_at="2026-09-26T20:30:00Z")
    row = _eval(watch, [just_over], at)
    assert row["evidence_age_days"] == 36
    assert row["state"] == "withheld"
    assert row["reasons"] == ["evidence_stale"]
    assert row["transition"] == "withheld"  # no active trigger yet


# ---------------------------------------------------------------------------
# 9 validation
# ---------------------------------------------------------------------------

def test_declared_and_unknown_condition_kinds_raise():
    for kind in DECLARED_NOT_IMPLEMENTED:
        with pytest.raises(WatchError, match=f"condition_not_implemented:{kind}"):
            _eval(_watch(condition={"kind": kind}), [], "2026-10-31T12:00:00Z")
    with pytest.raises(WatchError, match="condition_unknown"):
        _eval(_watch(condition={"kind": "momentum_breakout"}), [],
              "2026-10-31T12:00:00Z")
    with pytest.raises(WatchError, match="condition_unknown"):
        _eval(_watch(condition={"kind": "peer_divergence_volatility"}), [],
              "2026-10-31T12:00:00Z")


def test_watch_shape_and_field_validation():
    at = "2026-10-31T12:00:00Z"
    with pytest.raises(WatchError, match="watch_fields"):
        _eval(_watch(bogus=True), [], at)
    with pytest.raises(WatchError, match="watch_fields"):
        broken = _watch()
        del broken["expires_at"]
        _eval(broken, [], at)
    with pytest.raises(WatchError, match="watch_id"):
        _eval(_watch(watch_id=""), [], at)
    with pytest.raises(WatchError, match="scope"):
        _eval(_watch(scope={"universe_id": "JP"}), [], at)
    with pytest.raises(WatchError, match="scope"):
        _eval(_watch(scope={"universe_id": "JP", "horizon": "1m",
                            "currency_basis": "gold_bars"}), [], at)
    with pytest.raises(WatchError, match="created_at"):
        _eval(_watch(created_at="not-a-date"), [], at)
    with pytest.raises(WatchError, match="expires_at"):
        _eval(_watch(expires_at="yesterday"), [], at)
    with pytest.raises(WatchError, match="evidence_due_at"):
        _eval(_watch(evidence_due_at="soon"), [], at)
    with pytest.raises(WatchError, match="evaluated_at"):
        evaluate_watch(_watch(), [], evaluated_at="later")
    with pytest.raises(WatchError, match="evidence_must_be_a_list"):
        _eval(_watch(), _disl(), at)
    with pytest.raises(WatchError, match="max_evidence_age_days"):
        _eval(_watch(max_evidence_age_days=0), [], at)
    with pytest.raises(WatchError, match="max_evidence_age_days"):
        _eval(_watch(max_evidence_age_days=True), [], at)
    with pytest.raises(WatchError, match="max_evidence_age_days"):
        _eval(_watch(max_evidence_age_days="35"), [], at)
    with pytest.raises(WatchError, match="evaluated_before_created"):
        _eval(_watch(), [], "2026-08-31T12:00:00Z")
    with pytest.raises(WatchError, match="condition_dislocation_kind"):
        _eval(_watch(condition={"kind": "dislocation_attention",
                                "dislocation_kind": "factor_residual",
                                "attention": "outside_reference_range",
                                "direction": "any"}), [], at)
    with pytest.raises(WatchError, match="condition_attention"):
        _eval(_watch(condition={"kind": "dislocation_attention",
                                "dislocation_kind": "own_history_return",
                                "attention": "top_decile",
                                "direction": "any"}), [], at)
    with pytest.raises(WatchError, match="condition_direction"):
        _eval(_watch(condition={"kind": "dislocation_attention",
                                "dislocation_kind": "own_history_return",
                                "attention": "outside_reference_range",
                                "direction": "sideways"}), [], at)
    with pytest.raises(WatchError, match="condition_fields"):
        _eval(_watch(condition={"kind": "observation_qualified",
                                "horizon": "1m"}), [], at)
    with pytest.raises(WatchError, match="previous_watch_mismatch"):
        other = _triggered_previous(_watch())
        _eval(_watch(watch_id="watch-jp-1m-usd-002"), [], at, previous=other)


# ---------------------------------------------------------------------------
# 10 purity and language ceilings
# ---------------------------------------------------------------------------

def test_inputs_are_never_mutated():
    watch = _watch()
    previous = _triggered_previous(watch)
    revision = _disl(evidence_id="disl:sha256:mut",
                     window=("2026-09-08T00:00:00", "2026-10-07T00:00:00"),
                     computation_at="2026-10-11T20:30:00Z",
                     abstain_reasons=[])
    watch_before, evidence_before, previous_before = (
        deepcopy(watch), deepcopy([revision]), deepcopy(previous))
    _eval(watch, [revision], "2026-10-12T12:00:00Z", previous=previous)
    assert watch == watch_before
    assert [revision] == evidence_before
    assert previous == previous_before
    # The abstain_reasons list is copied, not aliased, into the row.
    abstain = _disl(state="abstain", abstain_reasons=["rights_unconfirmed"])
    row = _eval(watch, [abstain], "2026-10-12T12:00:00Z")
    assert row["reasons"] == ["rights_unconfirmed"]
    row["reasons"].append("mutated_by_test")
    assert abstain["abstain_reasons"] == ["rights_unconfirmed"]


def test_row_is_scan_clean():
    row = _eval(_watch(), [], "2026-10-31T12:00:00Z")
    triggered = _triggered_previous(_watch())
    revised = _eval(_watch(), [_disl(evidence_id="disl:sha256:scan",
                                     window=("2026-09-08T00:00:00",
                                             "2026-10-07T00:00:00"),
                                     computation_at="2026-10-11T20:30:00Z")],
                    "2026-10-12T12:00:00Z", previous=triggered)
    for doc in (row, triggered, revised):
        assert _forbidden_keys(doc) == []
        for sentence in doc["interpretation_limits"]:
            low = sentence.lower()
            assert not any(term in low for term in CAUSAL_TERMS_EN)
            assert not any(term in sentence for term in CAUSAL_TERMS_ZH)
        assert not any(word in " ".join(doc["reasons"] + doc["caveats"]).lower()
                       for word in CAUSAL_TERMS_EN)
    source = Path("engine/intl_global_watch.py").read_text(encoding="utf-8")
    assert not any(word in source.lower() for word in FORBIDDEN_WORDS)


def _forbidden_keys(doc):
    hits = []

    def walk(node, prefix=""):
        if isinstance(node, dict):
            for key, val in node.items():
                path = f"{prefix}.{key}" if prefix else str(key)
                if any(part in str(key).lower()
                       for part in FORBIDDEN_OUTPUT_KEY_PARTS):
                    hits.append(path)
                walk(val, path)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, f"{prefix}.{i}" if prefix else str(i))

    walk(doc)
    return hits


def test_module_imports_stay_closed():
    source = Path("engine/intl_global_watch.py").read_text(encoding="utf-8")
    allowed = {"__future__", "hashlib", "json", "copy", "datetime",
               "engine.intl_global_observation", "engine.intl_global_dislocation"}
    imported = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert imported <= allowed, imported - allowed
    # Dynamically: importing the module must never load engine.alerts, any
    # lib view, a notification client or a preferences module.
    code = (
        "import sys; import engine.intl_global_watch as w; "
        "bad = [m for m in sys.modules if m == 'engine.alerts' "
        "or m.startswith('engine.alerts.') or m == 'lib' "
        "or m.startswith('lib.') or 'user_prefs' in m or 'notif' in m]; "
        "print('DIRTY:' + ','.join(bad) if bad else 'CLEAN'); "
        "sys.exit(1 if bad else 0)"
    )
    result = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT,
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "CLEAN"

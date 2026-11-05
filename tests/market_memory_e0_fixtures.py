"""Bounded real retained-owner fixtures for E0 condition tests.

The fixture builders preserve the existing trusted-owner test inputs without
importing unrelated API, Options and application test modules into this suite.
"""
import copy
import json
from datetime import date, datetime, timedelta, timezone
from engine.neuralweb import market_memory_identity as identity
from engine.neuralweb import market_memory_projection as projection
from engine.neuralweb import market_memory_trusted as trusted
from engine.neuralweb import market_memory_retained_context_cohort as cohort

DEPLOYED_COMMIT = "a" * 40
CUTOFF = "2026-08-20T12:00:00Z"

def _raw_regime(*, growth_score: float = 0.133) -> dict:
    return {
        "schema_version": 1,
        "asof": "2026-08-10",
        "date": "2026-08-10",
        "quad": "Q2",
        "quad_name": "forbidden human label",
        "label": "must never enter trusted public objects",
        "raw_quad": "Q2",
        "pending_quad": None,
        "pending_days": 0,
        "pending_need": 7,
        "growth_score": growth_score,
        "inflation_score": 0.4,
        "growth_confidence": 0.1,
        "inflation_confidence": 0.3,
        "confidence": 0.2,
        "liquidity_overlay": "contracting",
        "cycle_tag": "late",
        "transition_state": "TRANSITIONING",
        "transition_state_raw": "WEAKENING",
        "transition_ratcheted": True,
        "transition_dwell_remaining": 5,
        "transition_flags": {
            "flag_breadth_price": False,
            "flag_credit_equity": False,
            "flag_ratio_inflection": False,
            "flag_inflation_basket": False,
            "flag_confidence_decay": True,
            "flag_gex": False,
            "flag_rotation_persistence": True,
        },
        "options": {
            "signal_episode": "forbidden",
            "H+60": {"outcome": 0.9},
            "U-CHAIN": {"rank": 1},
        },
        "Prophet": {"candidate": True, "gate": True, "size": 1.0},
        "freshness": {
            "asof": "2026-08-10",
            "built_at": "2026-08-10T09:55:00Z",
            "age_days": 0,
            "age_sessions": 0,
            "max_age_sessions": 1,
            "stale": False,
        },
    }

class Policy:
    policy_id = "test.authenticated_application_policy.v1"

    def __init__(self, denied=()):
        self.denied = set(denied)
        self.calls = []

    def check(self, action, resource):
        self.calls.append((action, copy.deepcopy(resource)))
        if action in self.denied:
            raise PermissionError("denied")

def capture(tmp_path, monkeypatch, *, session="2026-08-10", growth=0.133,
            seconds=0, liquidity="contracting", cycle="late"):
    built = datetime.combine(date.fromisoformat(session), datetime.min.time(),
                             tzinfo=timezone.utc) + timedelta(hours=10, seconds=seconds)
    raw = _raw_regime(growth_score=growth)
    raw.update({"date": session, "asof": session, "liquidity_overlay": liquidity, "cycle_tag": cycle})
    raw["freshness"].update({"asof": session, "built_at": built.isoformat().replace("+00:00", "Z")})
    body = (json.dumps(raw, sort_keys=True) + "\n").encode()
    source = tmp_path / "fixture-house-output.json"
    source.write_bytes(body)
    monkeypatch.setattr(projection, "_utc_now", lambda: built + timedelta(seconds=1))
    snapshot = projection.build_macro_regime_snapshot(source)
    monkeypatch.setattr(identity, "_utc_now", lambda: built + timedelta(seconds=2))
    evidence = identity.build_current_spy_identity()
    monkeypatch.setattr(trusted, "_utc_now", lambda: built + timedelta(seconds=3))
    return trusted.capture_trusted_regime_context(
        tmp_path / "public" / "trusted-v1", tmp_path / "private",
        snapshot=snapshot, identity_evidence=evidence,
        raw_source_body=body, deployed_commit=DEPLOYED_COMMIT,
    )

def owner(tmp_path):
    reader = trusted.TrustedFileAsKnownAtReader(tmp_path / "public" / "trusted-v1")
    return reader, reader.read_pinned_generation()

def load(reader, pin, stored, *, cutoff=CUTOFF, policy=None):
    return cohort.read_retained_context_cohort(
        reader, pin, subject_id=stored.packet["subject"]["subject_id"],
        query_cutoff=cutoff, policy=Policy() if policy is None else policy,
    )


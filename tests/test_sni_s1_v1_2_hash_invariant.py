"""S1 v1.2 code-level pin: hashed holdout_retired config ignores retired_scope.

A future edit that moves retired_scope (or any other non-v1 field) into the
hashed config dict of log_retirement must turn these tests red. The committed
v1.1 run artifacts already pin the v1 hashes; this file pins the invariant at
the function under test with synthetic fixtures only.

SNI-local DRAFT contract tests. They consume owner-supplied TrialLedger hashing
and caller-supplied opaque protocol ids. They do not feed a ranker, gate, sizer,
signal, escalation, or trade path.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "research/single_name_intelligence/residual"))

import run_s1  # noqa: E402
from engine.trial_ledger import TrialLedger  # noqa: E402

FAMILY = "sni.s1_residual.P01"
PID = "P01"
COUNTER = "BABA"
FIXED_SHA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
SCOPE_B = "P01+P02+P03"
V1_CONFIG_KEYS = {
    "event",
    "protocol_id",
    "version",
    "split",
    "membership_sha256",
    "contamination_class",
    "detected_at",
    "evidence",
}


def _rebuilt(membership_sha256: str) -> dict:
    rebuilt = {}
    for h in run_s1.HORIZONS:
        rebuilt[(PID, COUNTER, h)] = {
            "digests": {"TUNE": {"membership_sha256": membership_sha256}},
        }
    return rebuilt


def _leak() -> dict:
    return {
        "BABA": {"detection": None, "steps_total": 0},
        "SPY": {"detection": None, "steps_total": 0},
        "KWEB": {"detection": None, "steps_total": 0},
    }


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line.strip()]


def _log(path: Path, *, retired_scope, rebuilt=None) -> TrialLedger:
    ledger = TrialLedger(path=path)
    run_s1.log_retirement(
        ledger,
        FAMILY,
        PID,
        COUNTER,
        rebuilt if rebuilt is not None else _rebuilt(FIXED_SHA),
        _leak(),
        retired_scope=retired_scope,
    )
    return ledger


def test_h3_01_retired_scope_not_in_hashed_config(tmp_path):
    path_a = tmp_path / "ledger_a.jsonl"
    path_b = tmp_path / "ledger_b.jsonl"
    rebuilt = _rebuilt(FIXED_SHA)
    _log(path_a, retired_scope=None, rebuilt=rebuilt)
    _log(path_b, retired_scope=SCOPE_B, rebuilt=rebuilt)
    row_a = _rows(path_a)[0]
    row_b = _rows(path_b)[0]
    assert row_a["config_hash"] == row_b["config_hash"]
    for row in (row_a, row_b):
        cfg = row["config"]
        assert all("scope" not in key for key in cfg)


def test_h3_02_retired_scope_recorded_on_note(tmp_path):
    path_a = tmp_path / "ledger_a.jsonl"
    path_b = tmp_path / "ledger_b.jsonl"
    rebuilt = _rebuilt(FIXED_SHA)
    _log(path_a, retired_scope=None, rebuilt=rebuilt)
    _log(path_b, retired_scope=SCOPE_B, rebuilt=rebuilt)
    note_a = _rows(path_a)[0]["note"]
    note_b = _rows(path_b)[0]["note"]
    assert note_a.endswith(f"retired_scope={PID}")
    assert note_b.endswith(f"retired_scope={SCOPE_B}")


def test_h3_03_config_keys_frozen(tmp_path):
    path = tmp_path / "ledger.jsonl"
    _log(path, retired_scope=SCOPE_B)
    cfg = _rows(path)[0]["config"]
    assert set(cfg) == V1_CONFIG_KEYS


def test_h3_04_hash_changes_on_config_change(tmp_path):
    sha_a = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    sha_b = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    path_a = tmp_path / "ledger_a.jsonl"
    path_b = tmp_path / "ledger_b.jsonl"
    _log(path_a, retired_scope=None, rebuilt=_rebuilt(sha_a))
    _log(path_b, retired_scope=None, rebuilt=_rebuilt(sha_b))
    hash_a = _rows(path_a)[0]["config_hash"]
    hash_b = _rows(path_b)[0]["config_hash"]
    assert hash_a != hash_b

"""Deterministic contract replay, not a financial backtest or historical claim.

Compare original and corrected source adapters on the real producers' closed
vocabularies. Frozen dates and measured score; no network, clocks, runtime data,
forecast fitting, trades or ledger advancement. Default stdout only.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

BASE = "9e8f22ec1fc03c046bc1f38b3f397d5f6c9965ef"
SESSION = "2026-08-18"
STAMP = "2026-08-19T00:00:00Z"


def main() -> int:
    from engine.risk_envelope import compose_envelope
    from scripts import build_risk_envelope as candidate

    path = "scripts/build_risk_envelope.py"
    original_bytes = subprocess.check_output(["git", "-C", str(ROOT), "show", BASE + ":" + path])
    original = types.ModuleType("original_risk_envelope_adapter")
    original.__file__ = str(ROOT / path)
    exec(compile(original_bytes, BASE + ":" + path, "exec"), original.__dict__)

    rows = []
    for lead in ("INTACT", "CRACKING", "BROKEN"):
        for radar in ("calm", "watch", "caution", "elevated", "risk-off"):
            measured = {"asof": SESSION, "verdict": "MIXED", "score": 50,
                        "radar": {"state": radar, "top_score": 74}}
            leadership = {"asof": SESSION, "state": lead,
                          "cohort_role": "tracked_ai_hardware_damage_monitor"}
            expected = "NONE" if lead == "INTACT" and radar in ("calm", "watch") else "FRAGILE"
            stages = {}
            for label, adapter in (("original", original), ("candidate", candidate)):
                out = compose_envelope(
                    sources=adapter.build_sources(measured, leadership, SESSION), market="US",
                    source_session=SESSION, observed_at=STAMP, produced_at=STAMP, as_of=SESSION,
                )
                assert out["measured_state"]["score"] == 50
                assert out["measured_state"]["verdict"] == "MIXED"
                assert out["authority"]["envelope_may_gate"] is False
                assert out["authority"]["envelope_may_size"] is False
                stages[label] = out["hazard_summary"]["stage"]
            rows.append({"leadership_state": lead, "radar_state": radar,
                         "expected_descriptive_stage": expected, **stages,
                         "original_matches": stages["original"] == expected,
                         "candidate_matches": stages["candidate"] == expected})
    result = {
        "kind": "synthetic_native_contract_replay", "base": BASE,
        "original_adapter_sha256": hashlib.sha256(original_bytes).hexdigest(),
        "candidate_adapter_sha256": hashlib.sha256((ROOT / path).read_bytes()).hexdigest(),
        "n_cases": len(rows),
        "original_matches": sum(row["original_matches"] for row in rows),
        "candidate_matches": sum(row["candidate_matches"] for row in rows),
        "measured_score_verdict_and_authority_unchanged": True,
        "historical_backtest": False, "production_verification": False,
        "cases": rows,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if all(row["candidate_matches"] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER = (
    ROOT
    / "research/prophet_v4/r6_program/wave3"
    / "verify_q06_sec_comparable_revenue_source_contract.py"
)


def test_q06_gate_s_source_contract_is_reproducible_and_non_authoritative():
    namespace = runpy.run_path(str(CHECKER))
    result = namespace["verify"]()
    assert result["schema"] == "prophet.q06.sec_comparable_revenue_source_contract.v0.2"
    assert result["feature_value_pct"] == 16.356501765281383
    assert result["historical_envelope_identities"] == 10
    assert result["gate_s"] == "REPAIRED_PENDING_PARENT_ACCEPTANCE"
    assert result["gate_e"] == "NOT_REGISTERED_PREPARATORY_ONLY"
    assert result["authority_all_false"] is True

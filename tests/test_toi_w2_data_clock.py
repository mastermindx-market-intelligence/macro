import json
from pathlib import Path

import pytest

from scripts.research.validate_toi_w2_store_contracts import ContractError, combined_gate, validate
from scripts.research.run_toi_w2_terminal_parity import validate_parity

ROOT = Path(__file__).resolve().parents[1]


def test_real_contracts_validate_and_hold():
    rows = validate(ROOT / "research/technical_opportunity/w2_store_contracts.json")
    required = {"massive_stock_day", "terminal_intraday_history", "dataos_security_master", "massive_rights"}
    assert combined_gate(rows, required) == "HOLD"


def test_allowed_right_requires_receipt(tmp_path):
    rows = json.loads((ROOT / "research/technical_opportunity/w2_store_contracts.json").read_text())
    rows[0]["source_rights_ref"] = None
    path = tmp_path / "contracts.json"
    path.write_text(json.dumps(rows))
    with pytest.raises(ContractError, match="source_rights_ref"):
        validate(path)


def test_partial_plane_cannot_be_admit(tmp_path):
    rows = json.loads((ROOT / "research/technical_opportunity/w2_store_contracts.json").read_text())
    rows[0]["w3_admission"] = "ADMIT"
    path = tmp_path / "contracts.json"
    path.write_text(json.dumps(rows))
    with pytest.raises(ContractError, match="PROVEN_LIVE"):
        validate(path)


def test_terminal_parity_receipt_proves_blocker():
    got = validate_parity(ROOT / "research/technical_opportunity/w2_terminal_parity_receipts.json")
    assert got == {"status": "valid", "cases": 20, "pass": 15, "fail": 5}

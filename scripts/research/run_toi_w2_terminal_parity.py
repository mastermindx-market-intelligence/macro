from __future__ import annotations

import json
from pathlib import Path


def validate_parity(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    summary = payload["summary"]
    assert summary["strict_4h_parity_cases"] >= 20
    assert summary["pass"] + summary["fail"] == summary["strict_4h_parity_cases"]
    assert summary["fail"] > 0
    assert payload["w3_admission"] == "HOLD"
    return {"status": "valid", "cases": summary["strict_4h_parity_cases"], "pass": summary["pass"], "fail": summary["fail"]}


if __name__ == "__main__":
    print(json.dumps(validate_parity(Path("research/technical_opportunity/w2_terminal_parity_receipts.json")), sort_keys=True))

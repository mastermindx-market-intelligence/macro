from __future__ import annotations

import json
from pathlib import Path


def validate_coverage(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["planes"]["massive_stock_day"]["manifest_tickers"] >= 20000
    assert payload["combined_panel"]["w3_admission"] == "HOLD"
    return {"status": "valid", "combined_gate": "HOLD"}


if __name__ == "__main__":
    print(json.dumps(validate_coverage(Path("research/technical_opportunity/w2_coverage_receipts.json")), sort_keys=True))

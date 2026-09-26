from __future__ import annotations

import json
from pathlib import Path


def validate_clock_matrix(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    four = payload["registered_constructions"]["4H-CLOCK"]
    half = payload["registered_constructions"]["195M-RTH"]
    assert four["anchor"] == "09:30 ET"
    assert "actual_close" in four["bucket2"]
    assert "actual exchange close" in four["early_close"]
    assert half["identity"] == "independent method/trial identity"
    return {"status": "valid", "n_clocks": len(payload["clocks"])}


if __name__ == "__main__":
    print(json.dumps(validate_clock_matrix(Path("research/technical_opportunity/w2_clock_matrix.json")), sort_keys=True))

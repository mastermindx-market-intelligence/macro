"""Write the RD-signed joint row rr-typed-read-flags-001 BEFORE any typed read. Append-only.

Usage: python3 ledger_row_typed_001.py <trials.jsonl> <type_history_v1.parquet> <catalogue/adapter.py> <catalogue/bm_ref.py>
Refuses on any pin mismatch or if the id exists.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROW_ID = "rr-typed-read-flags-001"
PINS = {"types": "d6e77b7cce550f9b295009decdb9f2c5f22637af4b64565d8c323812113bddc5",
        "adapter": "504257977843e0894a97ed53415475eab76d8fc91fa9fc9cb0bbdcb9d24929c1",
        "bm_ref": "f7350e6e3f5a022a80aa2e9907f0b37cfc256fa8249960557798f50873467c76"}
AUTHOR = "risk-radar-lead/claude-opus-5-5 (Macro fable/risk-radar-masterplan-20261112)"


def _fsha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit(__doc__)
    ledger, types, adapter, bm = (Path(a) for a in sys.argv[1:])
    for p, k in ((types, "types"), (adapter, "adapter"), (bm, "bm_ref")):
        if _fsha(p) != PINS[k]:
            raise SystemExit(f"{k} sha differs from the pin; refusing")
    if f'"id": "{ROW_ID}"' in ledger.read_text():
        raise SystemExit(f"{ROW_ID} already exists; append-only")
    spec = json.loads((HERE / "JOINT_ROW_SIGNED_001.json").read_text())
    spec.pop("id")
    spec["harness_sha256_at_write"] = _fsha(HERE / "typed_read.py")
    spec["adapter_sha256"], spec["bm_ref_sha256"] = PINS["adapter"], PINS["bm_ref"]
    stamp = subprocess.run(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], capture_output=True, text=True,
                           check=True).stdout.strip()
    spec_sha = hashlib.sha256(json.dumps(spec, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    row = {"id": ROW_ID, "card": spec["card"], "author": AUTHOR, "family": "R-off", "role": "description",
           "typed_read_joint": True, "approved_by_rd": True, "nomination_possible": False,
           "counts_in_chance_account": True, "utc": stamp, "primary_spec": spec, "spec_sha256": spec_sha}
    with ledger.open("a") as fh:
        fh.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
    print(ROW_ID, spec_sha, stamp)


if __name__ == "__main__":
    main()

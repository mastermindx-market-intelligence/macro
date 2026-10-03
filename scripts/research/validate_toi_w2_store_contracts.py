from __future__ import annotations

import json
import sys
from pathlib import Path

CAPABILITY = {
    "PROVEN_LIVE", "BUILT_NOT_PROVEN", "PARTIAL", "DARK_OR_DISCONNECTED",
    "BROKEN", "SPEC_ONLY", "NOT_BUILT", "REJECTED_BY_DESIGN",
}
GATES = {"ADMIT", "HOLD", "REJECT"}


class ContractError(ValueError):
    pass


def validate(path: Path) -> list[dict]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ContractError("contracts must be a non-empty list")
    seen: set[str] = set()
    for row in rows:
        sid = row.get("store_id")
        if not sid or sid in seen:
            raise ContractError(f"duplicate/missing store_id: {sid}")
        seen.add(sid)
        if row.get("capability_state") not in CAPABILITY:
            raise ContractError(f"bad capability_state: {sid}")
        if row.get("w3_admission") not in GATES:
            raise ContractError(f"bad w3_admission: {sid}")
        rights = row.get("rights") or {}
        if any(v == "allowed" for v in rights.values()) and not row.get("source_rights_ref"):
            raise ContractError(f"allowed rights without source_rights_ref: {sid}")
        if row["w3_admission"] == "ADMIT":
            if row.get("capability_state") != "PROVEN_LIVE":
                raise ContractError(f"ADMIT requires PROVEN_LIVE: {sid}")
            if row.get("point_in_time_status") != "proven":
                raise ContractError(f"ADMIT requires proven PIT: {sid}")
    return rows


def combined_gate(rows: list[dict], load_bearing: set[str]) -> str:
    by_id = {row["store_id"]: row for row in rows}
    if not load_bearing <= set(by_id):
        return "HOLD"
    gates = {by_id[sid]["w3_admission"] for sid in load_bearing}
    if "REJECT" in gates:
        return "REJECT"
    return "ADMIT" if gates == {"ADMIT"} else "HOLD"


if __name__ == "__main__":
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "research/technical_opportunity/w2_store_contracts.json")
    rows = validate(path)
    required = {"massive_stock_day", "terminal_intraday_history", "dataos_security_master", "massive_rights"}
    print(json.dumps({"status": "valid", "combined_gate": combined_gate(rows, required), "n": len(rows)}, sort_keys=True))

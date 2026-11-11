"""Freeze Rotation Core protocol v2 in ONE commit. Run by (or on the instruction of) the parent only.

  python scripts/freeze_rotation_core_v2.py            # dry run: prints what would change, writes nothing
  python scripts/freeze_rotation_core_v2.py --apply    # writes files and stages them; the caller commits once

Steps: DRAFT json -> protocol_header_v2.json with status FROZEN (the JSON governs); DRAFT md -> PROTOCOL_HEADER_v2.md
with the sha256 line; DRAFT files removed; trial-ledger rows appended to data/trial_ledger.jsonl (sparse-safe: built
from the HEAD blob and staged with update-index); HOLDOUT_RELEASE_v2.TEMPLATE.json left untouched (the parent writes
HOLDOUT_RELEASE_v2.json later). Refuses if a frozen header already exists or the tree is dirty.
"""
from __future__ import annotations

import argparse, hashlib, json, subprocess, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RC = ROOT / "research/rotation_core"
DRAFT_J, DRAFT_M = RC / "protocol_header_v2.DRAFT.json", RC / "PROTOCOL_HEADER_v2.DRAFT.md"
FROZEN_J, FROZEN_M = RC / "protocol_header_v2.json", RC / "PROTOCOL_HEADER_v2.md"
LEDGER_ROWS = [
    ("rotation_core_v2", 9, "Rotation Core protocol v2 (own trials): H1 grid 4, H2 1, H3 1, cash ablation 1, tradable "
                            "version 1, named mapping 1; header sha256 {sha}; declared at freeze before any v2 outcome"),
    ("rotation_core_v2_pro_run_b_consumed", 10, "Pro run B (Macro 2afbd280fe): ten rules on Ken French 49 industries "
                            "1926-2019, results negative; consumed trials of this programme, counted at the v2 freeze; "
                            "header sha256 {sha}"),
]
CARRIED = {"rotation_core_v1": 36}


def git(*a, inp=None):
    return subprocess.run(["git", "-C", str(ROOT), *a], input=inp, capture_output=True, check=True).stdout


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--apply", action="store_true"); a = ap.parse_args()
    if FROZEN_J.exists():
        raise SystemExit("refused: protocol_header_v2.json already exists")
    if git("status", "--porcelain", "--", "research/rotation_core", "engine", "scripts").strip():
        raise SystemExit("refused: tree dirty")
    hdr = json.loads(DRAFT_J.read_text())
    hdr["status"] = ("FROZEN " + datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ") + " by the Prophet programme "
                     "CEO. No v2 outcome computed before this commit. Where the Markdown differs, this JSON governs.")
    hdr["trial_ledger_at_freeze"]["declared_rows"] = [r[0] for r in LEDGER_ROWS]
    hdr["trial_ledger_at_freeze"]["dsr_effective_n_families"] = ["rotation_core_v1", "rotation_core_v2",
                                                                 "rotation_core_v2_pro_run_b_consumed"]
    raw = (json.dumps(hdr, indent=2) + "\n").encode()
    sha = hashlib.sha256(raw).hexdigest()
    md = DRAFT_M.read_text().replace("(DRAFT revision 3, NOT FROZEN)", "(FROZEN)")
    md = (f"**Frozen header:** `protocol_header_v2.json`, sha256 `{sha}`. The runner refuses any other bytes.\n\n" + md)
    print("sha256", sha)
    print("ledger rows:", [(f, n) for f, n, _ in LEDGER_ROWS], "carried:", CARRIED, "DSR n =", 9 + 10 + 36)
    if not a.apply:
        print("dry run: nothing written"); return 0
    sys.path.insert(0, str(ROOT))
    from engine.trial_ledger import TrialLedger
    tmp = Path(tempfile.mkdtemp()) / "trial_ledger.jsonl"
    tmp.write_bytes(git("show", "HEAD:data/trial_ledger.jsonl"))
    led = TrialLedger(path=str(tmp))
    for fam, n, reason in LEDGER_ROWS:
        led.log_declared_budget(n, family=fam, reason=reason.format(sha=sha))
    blob = git("hash-object", "-w", str(tmp)).decode().strip()
    git("update-index", "--cacheinfo", f"100644,{blob},data/trial_ledger.jsonl")
    FROZEN_J.write_bytes(raw); FROZEN_M.write_text(md)
    git("add", str(FROZEN_J), str(FROZEN_M)); git("rm", "-q", str(DRAFT_J), str(DRAFT_M))
    print("staged; commit once with: research(rotation-core): freeze protocol header v2 (sha256 %s)" % sha)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

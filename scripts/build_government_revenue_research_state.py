"""Prepare initial GRV research state before the publisher's final sealed proof.

This entrypoint does not activate or append to the grader issuance log. It must
run only inside the existing serialized GovRev publisher staging generation.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Sequence

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.government_revenue.candidate_grader import GRV_FA1, ISSUANCE_LOG_FILENAME, canonical_bytes
from engine.government_revenue.research_state import build_not_started_state
from scripts.build_government_revenue_candidates import (
    CandidateProjectionError, _atomic_write_bytes, verify_candidate_artifacts,
)

INPUT_PATHS = (
    "data/government_revenue/latest.json", "data/government_revenue/workspace.json",
    "data/government_revenue/recipient_entity_graph.json", "data/government_revenue/candidate_queue.json",
    "data/government_revenue/candidate_ledger.jsonl", "data/government_revenue/candidate_projection_state.json",
    "data/government_revenue/candidate_projection_status.json",
)


def project_research_state(root: Path, *, generated_at: str) -> dict:
    """Source verification is read-only; output state appends zero issuances."""
    root = root.resolve()
    source = verify_candidate_artifacts(root, mirror_public=False,
        require_historical_suppression_manifest=True)
    if source.get("status") != "ok":
        raise CandidateProjectionError("research state requires a verified candidate generation")
    source_bytes = {p: (root/p).read_bytes() for p in INPUT_PATHS}
    queue = json.loads(source_bytes["data/government_revenue/candidate_queue.json"])
    log = root / "data/government_revenue" / ISSUANCE_LOG_FILENAME
    prior_raw = log.read_bytes() if log.exists() else b""
    payload = build_not_started_state(queue=queue, prereg_path=root/GRV_FA1.document,
        generated_at=generated_at, source_digests={p:sha256(raw).hexdigest() for p,raw in source_bytes.items()},
        prior_issuance_raw=prior_raw)
    # Do not certify one generation while projecting concurrently changed bytes.
    if any((root/p).read_bytes() != raw for p,raw in source_bytes.items()):
        raise CandidateProjectionError("research state source generation changed during preparation")
    verified_again = verify_candidate_artifacts(root, mirror_public=False,
        require_historical_suppression_manifest=True)
    if verified_again != source:
        raise CandidateProjectionError("research state candidate proof changed during preparation")
    canonical = root/"data/government_revenue/candidate_research_state.json"
    public = root/"site/government-revenue-data/research-state.json"
    raw = canonical_bytes(payload) + b"\n"
    _atomic_write_bytes(canonical, raw)
    _atomic_write_bytes(public, raw)
    if canonical.read_bytes() != public.read_bytes():
        raise CandidateProjectionError("research state twins differ after preparation")
    # The canonical log must still be absent/unchanged; no empty file activation.
    if (log.read_bytes() if log.exists() else b"") != prior_raw:
        raise CandidateProjectionError("research state preparation cannot mutate issuance")
    return {"status":"ok", "state":"not_started", "content_id":payload["content_id"],
        "issuance_append_count":0, "requires_new_final_generation_proof":True}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,required=True)
    parser.add_argument("--generated-at",required=True,help="actual staging clock; not durable issuance time")
    args = parser.parse_args(argv)
    print(json.dumps(project_research_state(args.root,generated_at=args.generated_at),sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

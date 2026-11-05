---
key: FIF-HELD-OUT-BYTES-ARE-STAGED-NOT-COMMITTED
question: >
  Where do the A37 held-out filing bytes for the non-AAPL issuers live, and who
  may write the held-out labels that the Q1 evaluation scores against?
answer: >
  Filing bytes are STAGED, never committed: the capture lane writes them once to
  the seat-owned stage root `~/lanes/stage/fif-heldout/<cik10>/<accession>/members/`
  on a fabric host (read-only afterwards; a byte-identical replica on a second host
  is permitted when the first is admission-hot). Git carries only digest-only
  `package_manifest.json` files, a per-issuer `capture_index.json`, the
  `request_log.jsonl` and `held_out_contract.json` under
  `tests/fixtures/fundamental_forensics_held_out/`. Labels and their `_SEALED`
  markers under `packs/PKxx/labels/` are written only by independent labeler lanes
  (`fif-heldout-lab-<x>`), never by a pack lane, a build lane or the integrating
  seat; the seat merges them unchanged and records the admitted run id in the PR.
rationale: >
  Non-AAPL SEC filing bytes never enter git (rights and size law of the FIF
  programme); the isolation test
  (`tests/test_fundamental_forensics_held_out_isolation.py`) enforces that no
  extractor test module names the held-out root and that a seal sits beside every
  label file. Digests in the manifests make a staged package verifiable without
  copying it. Independence of the labeler is what gives Q1 its evidential value:
  a label written by the seat or by a lane that read the producers would measure
  the authors, not the packs.
alternatives:
  - option: Commit the held-out filing bytes as fixtures
    why_not: Breaks the standing rule that non-AAPL SEC bytes never enter git and would make the held-out set readable by every pack lane.
  - option: Let the seat or the pack lanes author labels when no labeler is admitted
    why_not: Destroys independence; the A37 qualified abstain exists precisely so that the seat does not author Q1.
  - option: Fetch from EDGAR inside each labeler lane instead of staging once
    why_not: Multiplies SEC requests, breaks the capture receipt and the request budget owner recorded in held_out_contract.json.
evidence:
  - "PR #9908 (A37 held-out capture) merged aa76b1e7a46b18edaf3886f8050ac426f4c62e90"
  - "PR #9915 (lab-a labels PK01/PK06/PK09/PK11, 107 records) merged 24ae12d64a91aee63edbb2b1be49e4c73078caca"
  - "tests/fixtures/fundamental_forensics_held_out/README.md (Labels section)"
  - "tests/test_fundamental_forensics_held_out_isolation.py (seal-beside-every-label and root-literal scans)"
  - "stage census 2026-10-31: 135 files / 140M on mmx-ubuntu1, replica on mmx-ubuntu2 with equal counts"
affects:
  - WS:FINANCIAL-INTELLIGENCE-FABRIC
  - agentos/workstreams/WS-FINANCIAL-INTELLIGENCE-FABRIC.md
  - tests/fixtures/fundamental_forensics_held_out/
confidence: high
reversibility: costly
decided_by: FIF Meta-CEO seat 96dc937a (Fable) under the Chairman's FIF commission
decided_at: 2026-10-20
---

The A37 placement ruling, recorded durably after the seat's 2026-10-20 scratch
record was lost with the session. Packages are digests; bytes are staged; labels
come from an independent labeler and are merged unchanged.

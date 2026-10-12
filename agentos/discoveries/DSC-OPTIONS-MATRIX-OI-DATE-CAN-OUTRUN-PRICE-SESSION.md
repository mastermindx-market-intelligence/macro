---
key: OPTIONS-MATRIX-OI-DATE-CAN-OUTRUN-PRICE-SESSION
claim: >
  The nightly per-root matrix selected the newest OI publication date even when
  same-date EOD and Greeks were absent. The Sep-23 M1 job uploaded zero-cell
  matrices for all ten configured roots and exited zero. The real MU store
  reproduced zero cells on automatic selection; a same-session candidate
  returned 755 cells for Sep-22, exactly matching the incumbent explicit-date
  calculation without changing exposure formulas or using Sep-23 OI.
falsifier: >
  Run `python -m pytest tests/test_options_matrix.py -k matrix_auto_uses_complete_same_session_not_newer_oi`
  and reconcile the exact real-store receipt in #7861. Reconcile source generation and code hashes. The claim is
  refuted if the recorded incumbent automatic MU result contains cells, if
  candidate cells differ from the incumbent explicit Sep-22 result, or if any
  candidate input uses the later Sep-23 OI publication under the older date.
so_what: >
  Resolve a coherent per-root OI/EOD/underlying-price session before computing
  a matrix. Keep explicit date requests exact and disclose each source date.
  Missing underlying prices must not fall back to option premiums. A source
  failure must not overwrite a dated valid artifact with a newly built empty
  matrix or make the publication job report success. A cross-sectional breadth
  resolver is a different job and must not replace this per-root input join.
kind: architecture
verified_at: 2026-09-24
verified_by: >
  Macro PR 7861; research/evidence/options-matrix-session-repair-20260924/
  mu-source-qualification.json; tests/test_options_matrix.py;
  nonpublishing exact-source evaluation against the canonical M1 MU store.
scope:
  - macro
  - engine/options_matrix.py
  - scripts/build_options_matrix.py
  - terminal-options
confidence: verified
---

## Exact observed boundary

M1 is the existing source host. Its `theta-ops-wt/data/thetadata_eod` symlink
resolves to `flow-ops-wt/data/thetadata_eod`. At 2026-09-24T00:48:49Z, the
SPY/NVDA/AMD/MU/ARM OI shards reached Sep-23 while their EOD and Greeks shards
reached Sep-22. INTC stopped Aug-21 and is not claimed current. MU and ARM
were absent from the existing ten-root publisher despite having source data.

Candidate `268d53cae74de5f6e5f165e4c85ec784e7017ab7` returned MU spot1096.16,
session2026-09-22 and755 cells. All755 cells equal the incumbent explicit-date
calculation; the input OI publication is Sep-22 and its comparison is Sep-21.
The evaluation used the real store but did not publish or modify installed
source. The installed engine hash remained
`11146402f340c559673357b5b747918c89575eb572a057eb32bab1fa49e2883a`.

The actual Terminal route also consumed this matrix through an explicitly
intercepted local API. Its selected Sep-25/1100 cell displayed41.753106 million
from source41,753,106 dollars, showed5917 OI contracts, and pinned1100 without
recreating the chart. This is real-input local integration, not live release.

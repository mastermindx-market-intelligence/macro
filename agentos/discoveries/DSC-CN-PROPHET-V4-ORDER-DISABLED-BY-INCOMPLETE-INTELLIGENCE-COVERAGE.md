---
key: CN-PROPHET-V4-ORDER-DISABLED-BY-INCOMPLETE-INTELLIGENCE-COVERAGE
claim: >
  The 2026-09-07 cn_prophet_v4 output uses v3_coverage_fallback because four
  raw-ineligible stocks have no_edge_evidence: 600038.SS, 600606.SS, 000069.SZ
  and 603899.SS. The builder raw universe includes a breadth-cache source that
  the Intelligence search/deep trajectory readers do not consume; these four
  are absent from the latter two sources at the inspected immutable pin.
falsifier: >
  Read the board and candidate ledger at Macro
  19cad7eaa11ffeeb73c081ff3de84696ae2ee4e6. Filter stamp_date=2026-09-07 and
  board_definition=cn_prophet_v4; a different missing set, eligible status, or
  source availability disproves the pinned diagnosis. A later natural generation
  with genuine complete input coverage and intel_order_active=true clears live
  degradation, but neither a synthetic fixture nor a source merge proves that.
so_what: >
  Adopt source repair PR6992 and China recovery issue6866 instead of diagnosing
  the four names again or building a new ranker. Preserve real zero versus
  unavailable, reader precedence, raw-input provenance, current-session freshness
  and the global coverage rule. Input restoration can activate a different global
  ordering, so review and explicit serving activation remain separate from code.
kind: data
verified_at: 2026-09-08
verified_by: >
  Read-only git show at Macro19cad7eaa11ffeeb73c081ff3de84696ae2ee4e6;
  pandas filter of data/china_prophet_rank/candidates.parquet
  (blob32485ef806c8de4c7af1ece2a4cf0e34287fd482) returned the four rows, each
  raw_eligible=false, lane=not_raw_eligible, intel_basis=fallback_v3 and
  intel_unavailable_reason=no_edge_evidence. PyArrow schema and member-index
  reads found no search columns/rows; git ls-tree found no per-name deep files.
  Source comparison of builder universe(), CII _trajectories and hub price
  readers proves the source-universe mismatch. Current source/artifact paths
  were byte-identical at 3d0703aa0bb473f8a198e8ed579aebf3b08bafa9.
scope:
  - macro
  - WS:CHINA-ALPHA-INTELLIGENCE
  - WS:PROPHET-US-V4-RECOVERY
  - engine/china_intel_interest.py
  - scripts/build_china_library.py
  - data/china_prophet_rank/candidates.parquet
  - site/factordata/china_standouts.json
confidence: verified
---

# Resolved diagnosis and bounded implementation

The initial assessment at eb9e91961ddc4f3043d0dad358602525e66eccda correctly
identified four gaps but did not establish their identities. This continuation
resolves that specific uncertainty; it does not erase the first investigation's
failed optional probe or claim that blocked work was executed.

The same four missing names occur on 12 persisted sessions from August 20 through
September 7. They have leading-desk evidence (altdata), a measured signal core
of 0.0, and no remaining-edge input. The current board therefore falls back over
all 1,620 ranked records despite 1,616 measured records; none of the four is raw
eligible. Their candidate records contain computed price/technical fields, but
that is not a substitute for original raw price-vintage evidence.

The original breadth-cache bytes were not available in the committed source
or the inspected primary data directory. Do not manufacture historical prices,
write guessed zero scores, drop four names, or quietly change the coverage
population. The measured-zero value after a genuine price repair must come from
the unchanged scorer, not imputation.

## Source repair exists, not live acceptance

PR6992, operation prophet-cn-interest-input-parity-20260908-sol-001, stages an
optional, validated raw-universe price fallback in CII and the real builder
input wiring. First source head2afdd2290fc1bb49fcbbdb295ef1799e4ea8da97:
three files, baseline21 passes, pre-fix21 new failures/21 passes, post-fix42
CII passes and159 across five relevant suites. It remains Draft/HOLD. Always
read its current head, subsequent review and test evidence; this historical
first-head receipt is not later release authority.

Existing covered trajectories, score formulas, coverage floors and entry gates
are unchanged. Restoring a missing input MAY globally activate intelligence
ordering. An unchanged formula therefore does not imply unchanged production
behavior. No production activation, improved return or natural four-row repair
proof is claimed.

## Existing recovery boundary recovered

China recovery #6866 and sticky R0 #6871 already exist. R0's replay was rejected
for false-proof/chronology/denominator issues and remains with its exact native
writer. Its R4 tripwire is a warning/proposal plus explicit serving adjudication,
not an automatic ranker-revert actuator. Do not accept R0 from this data repair.

The separate chronology repair #6567 is already merged as
c968530b5e0e03632fd8d4e06611b3acddb0ece9. Do not rebuild it from stale issue
prose. Other component owners and the current four-market cockpit/Entry Truth
programs remain intact.

Exact next source action: consume PR6992's independent review, repair only real
introduced blockers, and verify current-base/hosted tests. Exact release action:
reconcile #6866's safety facts and original/current source-price basis, issue a
controlled-activation ruling, then require the natural producer and entitled
served-order/browser proof. A source merge is not that proof.

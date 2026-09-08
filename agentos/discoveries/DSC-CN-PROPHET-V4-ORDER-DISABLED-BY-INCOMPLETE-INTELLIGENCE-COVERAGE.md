---
key: CN-PROPHET-V4-ORDER-DISABLED-BY-INCOMPLETE-INTELLIGENCE-COVERAGE
claim: >
  The 2026-09-07 cn_prophet_v4 output uses v3_coverage_fallback because four
  raw-ineligible stocks have no_edge_evidence: 600038.SS, 600606.SS, 000069.SZ
  and 603899.SS. The builder raw universe includes a breadth-cache source that
  the Intelligence search/deep trajectory readers do not consume; these four
  are absent from the latter two sources at the inspected immutable pin.
falsifier: >
  Run git show 19cad7eaa11ffeeb73c081ff3de84696ae2ee4e6:site/factordata/china_standouts.json
  and inspect ranking.ordering plus ranking.input_coverage.intel_interest.
  Read the candidate ledger at that same immutable commit with Python/pandas.
  Filter stamp_date=2026-09-07 and
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

## September 8 review-repair continuation (supersedes the next source action above)

Current source is PR #6992 head a51bae222eedd4c53f4101998f3a3c4bc103f554,
tree 037627b311e54ae1cb50cb047f6aba720ff3e2df, a forward repair of the first
candidate. Same branch/worktree/operation; no replacement source carrier.
The first review identified Boolean-to-price coercion and one bad raw input
wiping a healthy stock's trajectory. Full build_interest_map tests reproduced
four intended failures with 48 controls passing. The repaired five existing
CII/rank/V3/V4/shadow suites passed 169 cases, zero skips; CII contains 52 cases.
Only CII and its existing test module changed in the repair; the original
builder-wiring blob 29d16200267b262c7a49c3fa0a432d2d07972107 is unchanged.

The exact same native reviewer returned semantic PASS on this head, with both
findings closed and no new blocker/major. Its review was static. The 169 tests
are author execution, not independent reviewer execution; the read-only reviewer
could not create pytest capture temporaries. The completed finite reviewer had
no watcher. Its later terminal STOP delivery was platform-blocked and was not
retried; terminal consumption is unverified. Failed out-of-scope child/memory
attempts appeared in its runtime output, with no successful effect shown;
do not infer an exhaustive external-effect census or resume/clone that reviewer.

Actual protected Source Continuity verification returned exit 2 with
REMOTE_CENSUS_INCOMPLETE: the adapter's 100-open-PR ceiling did not cover the
156-PR field. The separate complete source census and byte-identical material
dependencies through main 53142fff7c29230e753699a162c98336211506fb do not replace
that refused receipt. Keep the existing dependency with Mastermind issue #346;
no new checkpoint implementation, exception, writer transfer or release follows.
Current hosted checks remain unverified after a platform-blocked inspection.
No retry, cancellation, Ready, arming, merge, deployment or ranking activation.

The earlier Chairman-facing report's alternate ticker set (001309.SZ,
301078.SZ, 601022.SS, 603325.SS), all-null adj_close diagnosis, unpublished-patch
claim and unverified sandbox review package are withdrawn. A new pinned read
reproduced the four correct names in the claim above, all raw-ineligible and
with intel_signal_core=0.0. PR #6992, not that package, is source truth.

Exact continuation: retain this reviewed semantic head; resolve the existing
formal continuity and allowed current-candidate integration evidence, then
adjudicate controlled activation under #6866 and prove a natural producer plus
entitled served-order/browser result. Original historical breadth bytes remain
unavailable. The four-region integration/Entry Truth/continuing-instruction
outcome is not complete. No source algorithm work or original diagnosis needs
to be repeated merely because the chat or base moved.

---
key: GLOBAL-LIQUIDITY-TRANSMISSION
title: Global Liquidity Transmission perception lobe
objective: >
  Build the governed measurement plane for global liquidity transmission without
  acquiring trading authority. Done means the state producer, its sole downstream
  reader, the causal transmission lab and the accepted product surface each pass
  their separately commissioned gates, with explicit point-in-time and quality
  receipts and a natural (not simulated) source-to-user update.
status: active
program: policy-transmission-intelligence
repos: [macro, mastermind]
owner: claude-fable-seat-10c41bc9
class: build
blast_radius: reversible
ambiguity: scoped
owns_paths:
  - config/global_liquidity_transmission_v1.yml
  - engine/global_liquidity_transmission.py
  - scripts/build_global_liquidity_transmission.py
  - data/global_liquidity_transmission/**
  - site/liquiditydata/global_liquidity_transmission.json
  - research/GLOBAL_LIQUIDITY_*.md
  - tests/test_global_liquidity_transmission*.py
decisions:
  - DEC:GLT-SCOPE-CUSTODY-2026-10-13
discoveries:
  - DSC:BOJ-ASSETS-REQUIRE-MONTH-END-ANCHOR
artifacts:
  - research/GLOBAL_LIQUIDITY_DATA_CENSUS_2026-08-22.md
  - research/GLOBAL_LIQUIDITY_TRANSMISSION_STATE_METHODOLOGY_2026-08-22.md
  - research/GLOBAL_LIQUIDITY_TRANSMISSION_LIVENESS_2026-10-13.md
  - data/global_liquidity_transmission/state_history.parquet
  - data/global_liquidity_transmission/factor_comparison_btc_4w.json
  - site/liquiditydata/global_liquidity_transmission.json
  - tests/test_global_liquidity_transmission_liveness_v2.py
waves:
  - id: W-LIQ.0
    title: Architecture and orchestration freeze in Mastermind issues 117 and 123
    status: done
    next_action: >
      Historical. Mastermind PR #117 (the architecture masterplan) CLOSED UNMERGED
      on 2026-09-24 at draft head 140b90112f25. It is background architecture, never
      merged or protected law (DEC:GLT-SCOPE-CUSTODY-2026-10-13).
  - id: W-LIQ.1
    title: Macro data census and state-quality-freshness producer
    status: done
    pr: 6296
    next_action: >
      Source accepted in #6296 comment 5539622225 and merged 2026-09-04 as
      38fd57a676de. v1 semantics are frozen. The producer had NO production caller
      until W-LIQ.7 task T06 wired it into the nightly engine job; source merge was
      never a fresh production run.
  - id: W-LIQ.2
    title: Mastermind reader and Market View shadow plane
    status: done
    depends_on: [W-LIQ.1]
    next_action: >
      Mastermind PR #914 merged 2026-09-22 as 08597860fbce: the sole reader
      (brain/liquidity_transmission.py, 10-day evidence_available_at freshness law)
      plus an inert Market View plane. Source merge only; that the reader consumes a
      current artifact in production is W-LIQ.7 tasks T06/T23, not proven here.
  - id: W-LIQ.3
    title: Shock registry and causal transmission lab
    status: in_progress
    depends_on: [W-LIQ.2]
    next_action: >
      Mastermind PR #124 (OPEN DRAFT, codex/mas120-wliq3-20260822, head 23f97360131d)
      shows 1,239 paths only because of a stale base; its owned delta is 19
      brain/liquidity_lab paths. W-LIQ.7 task T02 carved exactly those 19 paths onto
      fresh Mastermind master and merged them as Mastermind #1412 (squash
      5bcc656bbe04, byte-identical). #124 stays open and untouched by GLT. Lab scope
      continues inside W-LIQ.7.
  - id: W-LIQ.4
    title: Repricing gap engine
    status: todo
    depends_on: [W-LIQ.3]
    next_action: Scope carried by W-LIQ.7 tasks T16/T18 (response curves, path residual vs remaining repricing); do not start a separate wave.
  - id: W-LIQ.5
    title: Product and chart surface
    status: todo
    depends_on: [W-LIQ.4]
    next_action: Scope carried by W-LIQ.7 tasks T21/T22/T27 inside the existing financial-liquidity surface; do not start a separate wave.
  - id: W-LIQ.6
    title: Learning, calibration, and promotion governance
    status: todo
    depends_on: [W-LIQ.3]
    next_action: Scope carried by W-LIQ.7 tasks T20/T24/T26 (calibration audit, independent adjudication, prospective ledgers); do not start a separate wave.
  - id: W-LIQ.7
    title: Completion DAG T01-T28 (Chairman masterplan 2026-10-13)
    status: in_progress
    depends_on: [W-LIQ.1, W-LIQ.2]
    next_action: >
      As of 2026-10-19, T01-T16 and T21/T23 are merged in both repos (table under
      "Current result (2026-10-19)"). T17 (Mastermind #1641) and T18+T19 (Mastermind
      #1639) are green and in the Mastermind merge queue. Next: T22 after #1639
      lands; the read-only T20/T24 audit after #1639 and #1641 land; the T25
      exact-head review after T22; then T26 (prospective issue or a qualified
      durable wait), T27 (browser-observed production journey) and T28 (scoped
      closure). Handoff: agentos/handoffs/GLOBAL-LIQUIDITY-TRANSMISSION-2026-10-19.md.
landmines:
  - "The existing engine/global_liquidity.py uses JPNASSETS provider labels directly; do not reuse its monthly timestamp kernel for causal work."
  - "Availability lag is not a vintage archive: ECB and BoJ historical revisions remain a declared limitation."
  - "A null global credit impulse is the correct result until comparable release-stamped coverage exists; never coerce US C&I and China TSF into one scalar."
  - "Current liquidity measurement, future-liquidity forecasting, and asset-response estimation are separate capabilities. PR #124 supplies no future-liquidity forecast."
  - "Readers age evidence_available_at (Mastermind consumer: stale beyond 10 days; macro workspace reader: CURRENT to 7 days, tolerance to 11). A regenerated generated_at, a new wrapper or a source merge never certifies freshness."
  - "/liquiditydata/* is outside the Caddyfile public-boundary allowlist, and the VPS clone is shallow: prove publication by site.served bytes and the artifact's own clocks, never by git ancestry."
  - "Macro PR #7191 (OPEN, labels merge-on-green + merge-blocked, head c8088b8a73a9) edits this same record from a 2026-09-16 base. Its facts are absorbed here with attribution; it must not be merged over this record. Its disposition is a seat act."
do_not_redo:
  - "Do not add a second global-liquidity collector before re-running the committed census against existing stores."
  - "Do not revive discontinued EZ/JP/KR/GB M2 parquets or admit China M2/NFCI/ANFCI into the causal state without a governed vintage solution."
  - "Do not build W-LIQ.2 or later waves from this Macro producer PR; issue #123 gives Sol cross-repo sequencing and acceptance authority. (Historical scope note for #6296; current sequencing is the W-LIQ.7 DAG under DEC:GLT-SCOPE-CUSTODY-2026-10-13.)"
  - "Do not rebuild or re-specify the #6296 producer (merged 2026-09-04 as 38fd57a676de). Its v1 semantics, thresholds, hashes and the meta/state/quality/freshness contract are frozen; any extension goes in a versioned namespace."
  - "Do not rebuild the Mastermind #914 sole reader (merged 2026-09-22 as 08597860fbce) or add a second reader or Market View plane."
  - "Do not rebuild the brain/liquidity_lab modules (adapter, contracts, estimator, eventization, ledger, validation). They exist at #124 head 23f97360131d and as the 19-path carve-out at 8e906193a15e. Never merge or replay #124's stale 1,239-path tree: 304 master-carried paths would revert."
  - "Do not cite Mastermind #117 as merged or protected law: it closed unmerged on 2026-09-24 and is historical architecture only."
  - "Do not rebuild accepted #6296, replace #124, weaken Executive security checks to green a native fixture, or call CI/merge a production outcome. (Carried from macro #7191.)"
next_action: >
  After Mastermind #1639 (T18+T19) lands, prove its blobs on master and commission
  T22 (the accepted product surface, macro). After #1639 and #1641 (T17) both land,
  commission the read-only T20/T24 audit against the two pinned heads. Open the T25
  exact-head review once T22 merges. The handoff dated 2026-10-19 holds the ordered
  steps.
---

## Boundary

The Global Liquidity Transmission system is a perception lobe with zero trading
authority. Display tier only (`validated=False`). Observed state, the future-liquidity
outlook and asset responses are separate capabilities with separate clocks; none
infers authority from the presence of another's artifact.

## Current result (2026-10-19)

Each merge below was checked against its repository's default-branch history on
2026-10-19. A merge is a source fact. It does not prove production behaviour, which
is T27's job.

| Tasks | Carrier | Squash on default branch |
|---|---|---|
| T01 + T02 + T06 | macro #9145 | `5a47995fd05d` |
| T02 carve-out (19 lab paths) | Mastermind #1412 | `5bcc656bbe04` |
| T03 + T04 + T05 | macro #9157 | `eb57d3db6448` |
| T07 + T12 | Mastermind #1444 | `3a265caa9b0f` |
| T08 | macro #9532 | `919711cb463b` |
| T10 | macro #9647 | `41428a110bb8` |
| T11 + T13 | Mastermind #1578 | `5a58243ac` |
| T14 | Mastermind #1633 | `2d7021dd8` |
| T21 + T23 | macro #9657 | `1390debab5e7` |
| T15 + T16 | Mastermind #1635 | `0c8cb6b46` |
| T09 | macro #9729 | `0221d6e17175` |

In flight on 2026-10-19:

- **T18 + T19:** Mastermind #1639, head `9355319c7208`, is green and in the merge
  queue. The first independent review found F1 (an issued percent could sit over a
  zero-straddling interval). The repair binds the interval to the sealed
  qualification, refuses a straddle, and HMAC-seals the decided percent. A second,
  non-author delta review passed every attack.
- **T17:** Mastermind #1641, head `fa6b57e2e9d7`, is green and in the merge queue.
  The identification card was frozen before the first fit. The real cell returns
  NOT_IDENTIFIED, because no rights-proven point-in-time policy-surprise tape exists,
  so no causal label is issued. The independent review passed with six minor gaps,
  which are routed to the T20/T24 audit.
- **Not started:** T20, T22, T24, T25, T26, T27, T28.

Scientific state: T09 issues zero forecast cells (measurement only). T17 is
NOT_IDENTIFIED. T18 abstains with no issued forward forecast. No GLT surface may
therefore make a positive forward-performance claim.

## Result as of 2026-10-13 (historical)

- **Producer (W-LIQ.1):** macro #6296 merged 2026-09-04 as `38fd57a676de`. The earlier
  "not merged" body was stale. No workflow ran the producer, so the tracked artifact
  stayed at `evidence_available_at` 2026-08-28 (first known 2026-09-04). W-LIQ.7 task
  T06 wires it into the nightly engine job, non-fatally; see
  `research/GLOBAL_LIQUIDITY_TRANSMISSION_LIVENESS_2026-10-13.md`. Production proof
  is still owed: a natural nightly commit with a later evidence clock, then the
  served bytes, then the consumer copy.
- **Reader (W-LIQ.2):** Mastermind #914 merged 2026-09-22 as `08597860fbce`. That is
  a source merge, not a production attestation.
- **Lab (W-LIQ.3):** Mastermind #124 is still OPEN DRAFT at `23f97360131d`; its
  hosted runs failed (recorded by #7191). Task T02 qualified the 19-path owned delta
  onto fresh master. 175 lab and reader tests pass under Python 3.12; there is no
  admitted study.
- **Architecture:** Mastermind #117 closed unmerged; it is historical only.

## W-LIQ.7 — 28-task DAG and train mapping

The task bodies live in the Chairman masterplan package (`TASKS.json`,
`OPERATOR_TASK_PACKETS.md`, `DEPENDENCIES.md`, 2026-10-13). `TASKS.json` carries no
train field. The mapping below was derived from masterplan section 6 by GLT W1
ORCH-A, and the seat may override it.

| Train | Purpose | Tasks |
|---|---|---|
| A | Measured truth and real consumption | T01 T02 T03 T04 T05 T06 T07 T21 |
| B | Component outlook | T08 T09 T10 |
| C | Transmission and repricing science | T11 T12 T13 T14 T15 T16 T17 T18 T19 T20 T24 |
| D | Accepted user journey and prospective proof | T22 T23 T25 T26 T27 T28 |

**Dependency spine:**
- T01 → T02 and T03.
- T03 → T04 and T05.
- T04 + T05 → T06.
- T02 + T04 + T05 → T07.
- T07 → T11, and T11 + T12 + T13 → T14.
- T14 → T15, then T16, T17 and T18; T16 + T10 → T19.
- T09 + T16 + T17 + T18 + T19 → T20 → T24.
- T06 + T12 → T21; T21 + T09 + T18 → T22; T06 + T07 → T23.
- T22 + T23 → T25.
- T24 + T25 → T26; T25 → T27.
- T24 + T26 + T27 → T28.

**Wave 1 (2026-10-13):**

| Task | State |
|---|---|
| T01 | Custody records in this PR |
| T02 | Mastermind carve-out branch pushed; PR not yet opened |
| T06 | Source wiring in this PR; production proof owed |
| T03/T04/T05 | On the sibling orchestrator |

T06 was wired ahead of its T04/T05 dependencies. The wiring runs the frozen v1
producer unchanged, so it does not depend on their qualification. T06's acceptance
still does.

## Custody dispositions (read 2026-10-13)

| Carrier | State | Disposition |
|---|---|---|
| macro #6296 | MERGED `38fd57a676de` | Frozen producer; never rebuilt |
| Mastermind #914 | MERGED `08597860fbce` | Sole reader; never duplicated |
| Mastermind #117 | CLOSED unmerged | Historical architecture only |
| Mastermind #124 | OPEN DRAFT `23f97360131d` | Original carrier; T02 carve-out supersedes its tree for delivery. Never pushed to by GLT. |
| macro #7191 | OPEN, merge-on-green + merge-blocked, `c8088b8a73a9` | Continuity facts absorbed here. Its handoff `agentos/handoffs/GLOBAL-LIQUIDITY-TRANSMISSION-2026-09-16-aion-recovery.md` exists only on its branch. Closing it is a seat act. |
| macro #7245 | OPEN DRAFT `6fd11eb40630` (sol branch) | Unknown-asof repair in `engine/neuralweb/liquidity_plumbing.py`; not GLT-owned; untouched |
| macro #9102 | MERGED 2026-10-13, head `a2767be332e5`, squash `a49e7d419ecf` | Copy-law test only. The masterplan's "DRAFT" is wrong. Avoid parallel edits to `tests/test_macro_command_copy_law.py`. |

Continuation: `agentos/handoffs/GLOBAL-LIQUIDITY-TRANSMISSION-2026-10-13.md`.
Runtime liveness is not inferred from this authored record.

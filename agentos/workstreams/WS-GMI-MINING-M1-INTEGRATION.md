---
key: GMI-MINING-M1-INTEGRATION
title: "GMI Mining — M1 integration: Freeport copper (W-C) and MP Materials rare-earth (W-R) economic dossiers (Fable Meta-CEO program)"
objective: >
  Deliver the first bounded Mining release inside the existing GMI Themes experience on the
  Semiconductor-led shared foundation: an investor can explain a copper operating change
  (Freeport, theme:copper_steel_electrify) and a rare-earth processing/economic change
  (MP Materials, theme:rare_earth_critical_min) from real permitted sources, correctly bound
  companies, useful signed economics and an explicit counter-thesis. Done means both real-source
  journeys W-C and W-R pass with all forty MGD obligations executed on the integrated candidate,
  independent review, exact-head CI and the authorized release path - never a merged slice alone.
  M1 acceptance is recorded separately from the full Mining sector mission.
status: active
program: gmi-theme-graph
repos: [macro]
owner: fable-meta-ceo
class: build
blast_radius: user_facing
ambiguity: specified
owns_paths:
  - engine/company_intelligence/mining_issuer_profiles.py
  - engine/market_ontology/mining_theme_research.py
  - contracts/market_ontology/mining_theme_research.v1.schema.json
  - tests/mining_casebook.py
  - tests/test_mining_*.py
  - tests/fixtures/mining_economic_dossier/**
  - research/mining/m1_integration_program/**
depends_on:
  - WS:GMI-THEME-GRAPH
  - WS:EARNINGS-INTELLIGENCE-OS
decisions:
  - DEC:CHAIRMAN-INDUSTRY-INTELLIGENCE-META-CEO-CONSOLIDATION-2026-10-11
waves:
  - id: MIN-W1
    title: "T01' consumption harness: synthetic casebook, dependency-binding validator, typed route_unbound client, gate:code job mining-economic-dossier"
    status: done
    next_action: "DONE 2026-09-24 12:52Z — PR #7932 merged at ee908cb8f0b5 after the Opus R1 red-team (REJECT -> probes frozen RED -> seat repair, R-MIN-29/30); 67 tests verified on origin/main."
  - id: MIN-W2
    title: "T02 FCX/MP native profile factories + byte receipts (after CDV-1 #7905 merges) || T04a closed Mining definitions, own schema, synthetic composition"
    status: in_progress
    next_action: "T04a is DONE and at PRODUCTION_PROOF 2026-09-27: PR #7950 merged aff8b76cba6afa6ed03298a1814b059e317070a0 at 03:33:28Z on CONCLUDED green (run 36288053731 completed/success at head c05368b31a6; 26 checks, 0 pending, sole red the sanctioned ci-authority/codex/merge-queue-pilot), the merge is an ancestor of origin/main, and Audit B's frozen GREEN gate re-run against main's own bytes gives 53 passed. mining_theme_research.py, its v1 schema, mining_casebook.py and test_mining_composition.py resolve on main; mining_issuer_profiles.py correctly does NOT (T02 mints it). Three fabric rounds were consumed by freeze-then-repair (R1 REJECT 3B/6M; R2 REJECT 1B/5M letter-gaming - leg values synthesised from period_kind; R2 probes + the R-MIN-31 truth table frozen RED at a848ad54 before round 3 ran). Round 3 delivered real numeric legs and derived polarity and the letter-gaming class is verified dead. ROUND-3 REVIEW TACTIC CHANGED (R-MIN-33e): two Opus red-team spawns returned NO verdict, each exhausting its turn budget on discovery, so the SEAT ran the adversarial battery itself and delegated only scoping/severity to a READ_ONLY auditor with the code excerpt and measured outputs INLINE - 0 tool calls, 65k tokens, complete rulings, three seat severities upgraded and two defects the seat had missed. Four defects fixed under R-MIN-33/33a/33b/33c: duplicate pair names published contradictory rows; a source-declared range shipped as a point estimate the schema pins const false; unit/perimeter/period were carried and never read, so 1700 Mlbs vs 1680 kt published an INVERTED polarity; NaN passed the numeric gate. Receipt: reviews/OPUS_T04A_PR_REVIEW_R3_2026-09-26.md. THE WAVE IS NOT DONE: T02 is still ahead of it and still gated on #7905, which another seat holds DRAFT under its own R7 audit - do not poll it and do not arm a watcher on it. T02 dispatch is SYNTHETIC-ONLY; its packet excludes plan §4 bullet 1 (Audit A F1's unauthorized source-acquisition act), which cannot be deleted at source because the plan is reachable only from carrier #7795."
    depends_on: [MIN-W1]
  - id: MIN-W3
    title: "T03 definition-safe economic inputs (signed blocks, missing_derivation, IR-01/IR-02 consumer rules) -> T04b integrated positive witnesses"
    status: todo
    depends_on: [MIN-W2]
  - id: MIN-W4
    title: "T07 corrections, replay, version identity and unchanged-incumbent proofs"
    status: todo
    depends_on: [MIN-W3]
  - id: MIN-W5
    title: "T05 private route registration, T06 real theme entry + company workflow, T08 two real-source acceptance runs and release"
    status: todo
    depends_on: [MIN-W4]
    next_action: "Wait for Semiconductor B's shared route/client/mount on main and the incumbent-intake G2 source admission; never build against #7870's branch."
next_action: >
  2026-10-11 CONSOLIDATION (DEC:CHAIRMAN-INDUSTRY-INTELLIGENCE-META-CEO-CONSOLIDATION-2026-10-11): the T02 gate is OPEN.
  CDV-1 #7905 MERGED 2026-09-30T01:42Z as cdce3023fbba, so the "waits on #7905 reaching main"
  condition below is satisfied and no longer binds. T02 dispatch stays SYNTHETIC-ONLY per the
  existing ruling; it shares the issuer_profiles.py seam with Industrials #8250 and CDV-1. Packet P-MIN-1.
  .
  MIN-W2 IS PARTLY DELIVERED AND STILL OPEN. T04a is at PRODUCTION_PROOF (#7950 merged
  aff8b76cba6, 53 passed against origin/main). The wave's other half, T02, has not started.
  DISPATCH POSITION, stated explicitly because two successive handoffs got it wrong in opposite
  directions: #7950's merge unblocks NO plan TASK. R-MIN-05 orders
  T01' -> (T02 || T04a) -> T03 -> T04b -> T07, so T03 needs BOTH #7950 merged AND T02 delivered,
  and T04b comes after T03. T02 itself waits on CDV-1 #7905 reaching main - another seat's DRAFT,
  never polled, never watched. What #7950's merge actually unblocked was this program's records
  lane, deferred only because tabling a ruling required a push to #7950 while its proof was in
  flight.
  CHECK THE T02 GATE AGAINST MAIN, NEVER AGAINST #7905: if `fiscal_scope` does not appear in
  engine/company_intelligence/issuer_profiles.py, #7905 has not landed and T02 is not
  dispatchable. Measured 2026-09-27 - it occurs ZERO times, and profile_for_ticker at :1293 has
  no private/public branch and cannot raise, so T02's own truth table describes the POST-#7905
  shape. A T02 lane must NOT build that split itself; it is #7905's hunk in a shared file its
  incumbent owns.
  The next four tasks have SEAT-AUTHORED freeze packets committed beside the rulings
  (T02/T03/T04b/T07 _FREEZE_PACKET.md), so no lane needs to re-derive a spec. T04b's packet is
  seat-authored of necessity: neither audit ever froze a T04b spec, because Audit B wrote ONE
  spec for all of T04 and the a/b split is R-MIN-05's. T02's packet is SYNTHETIC-ONLY and
  deletes the plan's unauthorized live-fetch checkbox from the build packet; real-byte
  acquisition stays held behind G2 + IR-05 as an owner/intake act.
  Per R-MIN-33e every commission carries its binding evidence INLINE rather than naming an
  artifact by path, or the worker spends its whole budget on discovery and returns no verdict
  (measured twice, 166k and 150k tokens, zero verdicts).
  Per R-MIN-33g a watcher's expected check set is the ci.yml RUN's own job list for the exact
  head sha and completion is that run's status == completed - never a constant pack floor, and
  zero ci-pack-* in the rollup is NOT proof that no packs will come, because ci-plan computes
  the set and takes about four minutes to publish it. Your own push invalidates your own
  evidence.
  MGD_EXECUTION_STATUS.json is the program's execution record against the forty obligations and
  is the thing a wave UPDATES, not a thing a wave re-derives. Status is never inferred from a
  test name. CORRECTED 2026-09-27: when T04b lands it owes the two-armed MGD-10 pin ONLY,
  because T04b carries `period` onto native blocks and that is exactly what makes MGD-10
  falsifiable. **MGD-08 clause 2 is CLOSED and is not T04b's to write** - it is
  COVERED_SUITE_GREEN, so the ledger's UNPINNED count is 0 of 40. Closing it required a
  BEHAVIOUR change and not merely a test, which R-MIN-34 had ruled unnecessary on a
  copper-only measurement: on the rare-earth slice a wholly empty economic path reported
  `ready` over an empty panel, because that slice's vocabulary mints
  `stream_threshold_unknown` on every payload and the readiness clause fired on it before
  the native-block channel was consulted. R-MIN-35 records the amendment, R-MIN-34 carries
  an AMENDED BY marker, and T08 acceptance item 3 is amended so a lane cannot revert
  MGD-08 to UNPINNED to satisfy it. Do NOT re-open it.
  WAVE 6 (2026-09-27, same day): the coverage record itself was re-audited BY SUBJECT and six
  rows were mis-statused. 30 rows read `NOT_RUN` because their note said 'owning task <T> has
  not landed on main' - a TASK-level verdict on an obligation-level question. MGD-15/16/17/21/22
  are now PARTIAL_BY_CONSTRUCTION and MGD-20 SATISFIED_BY_ABSENCE_OF_CAPABILITY, because their
  subjects are the MERGED T04a composer (the comparison channel at `:802`, the always-empty
  `derived` list, the `const: false` consensus flags), not unlanded T03 code. `NOT_RUN` 30 -> 24;
  `UNPINNED` stays 0 of 40. T08 SS5's closing sentence, which told a lane that reconciling any
  T03 row 'would be fiction', is WITHDRAWN at source - it sat in the acceptance task's own
  packet. R-MIN-36 records it. One new pin shipped
  (`test_mgd17_refused_comparison_does_not_delete_the_supported_facts`, 175 passed), which was
  the only MGD coverage work available while both #7870 and #7905 are closed. Reconcile by
  SUBJECT, clause by clause, never by owning task.
  WAVE 7 (same day) CLOSED that audit: the 14 rows wave 6 had left, plus the 8 it read without
  writing their evidence onto the rows, were all measured. Six more moved on delivered, green,
  CONTROLLED pins - MGD-05/24/27/28/29/30 - so twelve of forty moved in total, and `NOT_RUN` is
  now 18. **All 40 rows carry a subject-level measurement and NO row explains its status by
  whether a task has landed.** The 18 remaining each state one of three measured reasons:
  subject-absent (own vocabulary at zero occurrences across module, binding, schema and all
  seven suites), G2-gated (the unit is a real-source demonstration no test may satisfy), or
  operative-clause-blocked (a later clause is unviolatable while the FIRST needs T02's unlanded
  vocabulary). Counts 6/1/18/12/3 = 40, UNPINNED 0. Two NON-moves are deliberate and recorded
  on their rows - MGD-35 (absent wiring is not a guarantee about future wiring; the row's value
  is that it is owed) and MGD-38 (half a demonstration is none). R-MIN-37 records the closure.
  Waves 5+6 MERGED as #8100 -> `ce0065d89732` and verified on origin/main; wave 7 is #8110.
  THIRD PART of the same wave delivered the one row the closed audit had identified as
  PAYLOAD-PINNABLE TODAY: MGD-19 clause 2 now has a payload pin - the elimination must reach
  `native_blocks` with `-120` and `sign == '-'`, against a one-block-fewer control and an
  unperturbed-neighbour control - so the row moved to `PARTIAL_BY_CONSTRUCTION` and `NOT_RUN` is
  17. Counts 6/1/17/13/3 = 40, UNPINNED 0, 176 passed. **An audit that ends in a note where a pin
  was available has not finished.** Clause 1 still needs T03's definition vocabulary and is not
  claimed. Do NOT credit `test_internal_transfer_keeps_elimination_sign` to MGD-19: it asserts
  through a helper, and a helper pin is not a pin on the composed payload.

  WAVE 9 (records only; no code, no status, no count changed) closed the program's last
  UNRECEIPTED claims. Three classes, each a different failure of evidence rather than of fact.
  (1) Two rows asserted an ABSENCE in prose - falsifiable, but with no record that anyone probed.
  Both now carry a whole-payload recursive walk with an ENUMERATED positive control, written that
  way because the first version of the probe read two keys that do not exist and answered NONE
  vacuously: a negative result produced by looking in the wrong place is indistinguishable from a
  real absence, and only a control that lists what the probe DID reach separates them.
  (2) The program's CORE reuse row carried the one note in 40 unfalsifiable by inspection; it now
  states the mechanism (the shared contract is a lazy string import, REFUSED when incomplete, never
  reimplemented) and the four conditions that would break it.
  (3) Four record sites justified measurements by naming scratchpad scripts that no longer exist,
  and the ledger header quoted numbers from a head that no longer exists. Both are the same defect
  the program already names as `green proof against a stale base`, appearing INSIDE the evidence
  rather than in CI - so the repair scripts were written SELF-MEASURING, computing every figure at
  run time, because a repair that pasted today's numbers as literals would rebuild the defect one
  head later. The stale header vindicated its own rule on re-measurement: 38 false gaps then, 38
  false gaps now, so the clause was DATED rather than deleted.
  One correction rides along, recorded because it was mine: a sentence written from a five-site grep
  claimed `identity_results` is never constructed in the module. There are ELEVEN sites and four
  assemble the field. The accurate claim is stronger - no identity row's CONTENT originates there -
  and all eleven are now enumerated in T03 section 6. A claim quantified over every site must list
  them.

  WAVE 10 (records only; no code, no status, no count changed) is the wave 9 receipt turned on
  ITSELF. Wave 9 shipped a citation-integrity check reporting 27 pin refs and ZERO dead, and that
  check cannot see the defect that was actually present: it asks whether a ref RESOLVES, which a
  pin aimed at an unrelated green test satisfies completely. Resolution is not relevance. A screen
  comparing each row's NAMED symbols against its cited test's body flagged two rows -- MGD-01 at
  0 of 9 and MGD-22 at 1 of 4 -- and hand-reading both confirmed it: each cited a green test that
  asserts something adjacent to, but not, the mechanism the row's reason turns on. Coverage was
  never the problem, so nothing moved status; the citations were wrong, which is worse than it
  sounds, because a pin's whole purpose is to send a reader to the assertion.
  Two things generalise. FIRST, the family: an integrity check that passes tells you only that the
  thing it measured is fine. Presence is not uniqueness, a misdirected probe answers NONE
  vacuously, and a resolving pin need not assert -- three instances in three waves, each one a
  clean instrument result that WAS the bug. Ship a positive control with every such check and state
  what it cannot see. SECOND, and less obvious: MGD-01's mismatch was created by IMPROVING the row.
  Its previous note was vague enough that no screen could flag it, and the weak pin looked fine
  beside vague prose; replacing it with a real mechanism is what made the mismatch visible. A note
  and its pin are one artifact, so a rewritten justification owes a re-checked citation in the same
  commit. The screen is deliberately kept a SCREEN and not a gate -- a pin may assert a mechanism
  in different words, so a zero score orders a READING, never a verdict.

  WAVE 11 audited the rows the instruments CANNOT REACH, and the defect was there. Wave 10's
  pin-relevance screen scores a row's note against its cited test body, so a note naming no
  backticked symbol scores 0 of 0 and is excluded -- five rows sat in that exclusion, and all five
  justified their status by the delivered test's NAME plus a suite-wide pass count, which is the
  one thing this ledger's own authority block forbids. The count had been stale for two waves.
  Measured by SUBJECT against the obligation statements read from the carrier trace: three confirmed
  (two of them stronger than the row claimed -- MGD-09 is two-armed because its fixture supplies a
  complete economics block and omits only the issuer, and MGD-34 holds over all 11 payloads against
  an oracle literal with a falsy-but-not-False negative control); two had a clause NO delivered test
  reached and both were PINNED in this wave with control arms and mutation probes; one moved status.
  MGD-12 -> PARTIAL_BY_CONSTRUCTION, and T08 §5's mechanism for it is withdrawn as WRONG: it
  recorded a 'dedup path' and there is none -- two rows sharing one subject id go in and two come
  out, as that test itself asserts. The obligation's operative verb has no construct on main to
  violate, enumerated over all 11 cases with a positive control on the walk.
  Three things generalise. FIRST: a rule a file states about its own method is not a rule its rows
  obey -- audit the stated rule against the rows EXEMPT from your instruments, never the rows they
  score. SECOND: report a screen's REACH beside its score. 'pin_relevance 14 of 14' was true and
  invited exactly the wrong conclusion; the honest line is 14 of 40 rows scored, and wave 11 moved
  it to 19 of 40 by making five vague notes specific. THIRD: a screen that names its own blind spot
  tells you where to look next -- this one named 'a stale count in a sibling record', and two
  do_not_redo entries asserting a two-wave-old pass count in the present tense were found by grep
  minutes later. Both are now dated rather than rewritten, as is MGD-08's closure receipt, which
  the stale-count screen flagged as a FALSE POSITIVE of its own making (174 was the seven-suite
  total; the screen compared it to the single-suite figure).
  WAVE 8 (records only) fixed a gate that could not execute. T02's §5 sibling-regression gate
  required `tests/test_issuer_profiles.py` and `tests/test_event_workspace_build.py` green and
  NEITHER FILE EXISTS; the suites it means are `tests/test_issuer_profiles_a5a.py`,
  `tests/test_refresh_event_workspaces.py` and
  `tests/test_company_intelligence_event_workspace.py`, measured green together (123 passed).
  That gate is the packet's ONLY protection against T02's edit to the shared
  `issuer_profiles.py` regressing its incumbent owner, and it fails QUIETLY - a missing path
  exits 4, a pattern run prints "no tests ran". All five packets were then swept
  token-by-token: ZERO undeclared absent symbols, and no sibling repeats the class, so the
  sweep is recorded do_not_redo. Also recorded: a gate named after a PR or a package is not
  falsifiable by inspection - `engine/theme_graph/` has nine PRE-EXISTING modules on main while
  #7870's `curation_assertion` and route/client/mount seam are absent, so state a gate as the
  absent SYMBOL plus its probe.
  T05/T06 stay held for #7870's route/client/mount on main plus the answer to comment
  5811889498; T08 is last; G2 real-source admission remains an incumbent/operator act.
  Standing operator items: mini2 has no WAN (a bridge0 default route shadows the real gateway;
  the fix needs mini2 sudo and is an OPERATOR act), mini2 MiniMax provisioning, mini2 keychain
  unlock for cursor-agent. Never copy the fleet token to another host.

artifacts:
  - agentos/handoffs/GMI-MINING-2026-09-24-m1-integration.md
  - agentos/handoffs/GMI-MINING-2026-09-26-m1-integration.md
  - agentos/handoffs/GMI-MINING-2026-09-27-m1-integration.md
  - research/mining/m1_integration_program/MGD_EXECUTION_STATUS.json
  - research/mining/m1_integration_program/T02_FREEZE_PACKET.md
  - research/mining/m1_integration_program/T03_FREEZE_PACKET.md
  - research/mining/m1_integration_program/T04B_FREEZE_PACKET.md
  - research/mining/m1_integration_program/T07_FREEZE_PACKET.md
  - research/mining/m1_integration_program/T08_FREEZE_PACKET.md
  - research/mining/m1_integration_program/reviews/OPUS_T04A_PR_REVIEW_R3_2026-09-26.md
  - research/mining/m1_integration_program/rulings/R-MIN-2026-09-24-wave1.md
carrier:
  operation: gmi-mining-fable-ceo-m1-integration-20260924-chairman-001
  research_pr: 7795
do_not_redo:
  - "The eight research passes, design (blob 33d94481), plan (a2fca1c5), addendum (053a59e2), witness qualification and forty-row trace on #7795 @ eb6f05c0 are frozen - never re-research Mining or recreate the packet."
  - "Shared requests 5809132661 / 5809893850 and the accepted R4/R12 architecture answers on #7870 are consumed - never repeat them; an acknowledgment is not interface delivery."
  - "Original plan T01 (generic kernel extraction) is a shared-owner proposal, not Mining work; never create or copy engine/market_ontology/theme_research.py, a generic response schema, route, publisher, client or page shell."
  - "Canonical P05 blob is 42c90b46; the excluded local blob 587ee020 is never republished. Healthcare #7787 stays settled and separate."
  - "T04a is spent: #7950 is merged and proven green on main (53 passed AS MEASURED AT THAT MERGE - a receipt of that head, not a current gate; the same suite passes 61 today). Three fabric rounds and three Opus reviews are consumed and R-MIN-31/32/33/33a-33g are tabled - never re-spec or re-review it."
  - "Never re-derive the MGD partition by grepping test names. Planned names resolve 0/40 on main and 2/40 at #7950, so a name audit reports 38 false gaps. MGD_EXECUTION_STATUS.json is keyed by obligation id for exactly that reason."
landmines:
  - "Shared files (issuer_profiles.py, event_workspace_build.py, receipts.py, legacy-jobs.yml, test_ci_pack.py, config/theme_sources.yml, the shared theme-research client/mount) stay owned by their incumbents and are touched only at named seams."
  - "Sparse worktrees truncate data/ and site/ on write."
  - "A new test wired into a gate:code run line without its paths: entry reds contract-delta fleet-wide."
  - "The sec_edgar public-domain rationale is not blanket clearance to republish issuer-authored bodies (addendum IR-05)."
  - "No live Freeport/MP figure may become a fixture or a native receipt before G2; a wrong-host 404 is not a privacy proof."
  - "An --admin merge on a docs-only diff is NOT sanctioned by a rollup showing zero packs. ci-plan computes the pack set and takes minutes; a docs diff gets a REDUCED set, not an empty one. This seat merged #8060 mid-flight over three in-flight checks on exactly that mistake (R-MIN-33g)."
  - "The T02/T04b packets are seat-authored, not audit-frozen. Audit B wrote ONE spec for all of T04 and the a/b split is R-MIN-05's, so a lane told to find 'the T04b spec' in the audits will find nothing and invent one."
---

# GMI Mining — M1 integration

Seat program record. Continuity lives in the handoff above; rulings in
`research/mining/m1_integration_program/rulings/`. Modified shared files are owned by their
incumbent workstreams (`WS:GMI-THEME-GRAPH`, `WS:EARNINGS-INTELLIGENCE-OS`) and are touched only
at named seams. All rank/gate/size/originate/entry authority stays literal false.

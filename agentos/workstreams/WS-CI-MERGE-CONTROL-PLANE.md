---
key: CI-MERGE-CONTROL-PLANE
title: CI + merge control-plane recovery (the 2026-08 traffic jam)
objective: >
  A PR loop where ordinary changes validate quickly, structural mistakes red
  in minutes, armed PRs merge without babysitting, and a fast-moving producer
  main cannot re-prove the universe — with no transport in the pipeline that
  an unbounded changed-file list can kill.
status: active
program: project-active-build-control
repos: [macro]
owner: coo-fable
class: build
blast_radius: reversible
ambiguity: open
decisions:
  - "DEC:CI-EXECUTION-PROFILE-V2"
discoveries:
  - "DSC:CI-CHANGED-FILES-ENV-HAS-AN-EXECVE-CEILING"
  - "DSC:GITHUB-CONCURRENCY-SUPERSEDES-PENDING"
  - "DSC:PR-EVENT-DELIVERY-IS-NOT-CANDIDATE-IDENTITY"
  - "DSC:CI-SELF-MOD-FENCE-ARGV-BYPASSES-BOUNDED-TRANSPORT"
  - "DSC:REUSABLE-WORKFLOW-CALL-AND-HOST-HOOK-USE-DIFFERENT-REF-SHAPES"
  - "DSC:SEALED-PC-CI-REPLAY-AND-PORTABILITY-NEED-EXPLICIT-RUNTIME-BINDINGS"
  - "DSC:CI-PROMISOR-OBJECT-FETCH-TRUNCATION"
waves:
  - id: W-TRANSPORT
    title: Bounded changed-files transport across CI and self-mod fences
    status: done
    pr: [5608, 6223]
    note: >
      PR #5608 landed bounded planner-to-pack changed-file transport. PR #6223
      merged as bc0a9cd896401fae7ec19a208b3a5017cc8d13a6 and moved both
      same-repository and fork self-mod populations into files while
      preserving exact ancestry/range proof. The original #5898 fences run
      32546500471 failed before Python started with E2BIG. The authorized
      tree-preserving #5898 refresh kept the reviewed tree, and fences run
      32602516677 invoked the live checker through bounded file handles,
      emitted the actual PASS policy verdict, and showed no E2BIG or exit 126.
      #5898 then merged as 21f51a1ecfed778a738b048bd7e5efd30b1d9336;
      current main contains both repairs. No policy weakening, parallel
      transport, or separate runner path was introduced. W-TRANSPORT is done.
  - id: W-REWRITE
    title: Structural rewrite of planner/merge control plane
    status: in_progress
    note: >
      Two lineages collided 2026-08-14: PR 5585 (claude — API diff, plan
      consumption, wake diet) was closed in a reconciliation naming PR 5591
      (codex — authority plan artifact, committed scope index, evidence
      chain) canonical. PR 5591 was closed unmerged on 2026-08-15 and is now
      historical archaeology only; it carried the E2BIG defects this
      workstream's W-TRANSPORT fixed on main. Any successor must preserve the
      bounded transport — the wiring pins enforce it.
  - id: W-SEMANTIC-PROOF
    title: Semantic CI proof identity and ancestry-valid healing
    status: done
    note: >
      CEO V2 semantic proof landed through PR 5750 as
      064ebd53a9de3cd0fcc3eb813e634f30106eed03 on 2026-08-15. Current main
      b2938ee302e16654de2858e820877cad096f2446 is a verified descendant. Main
      semantic-producer run 31890203055 on descendant
      719b13774da34e518da57591f2cf940cbe9c856c emitted
      ci.semantic_evidence.v1 with status=clear for 194 jobs and no
      infrastructure findings; merge-on-green consumer run 31892639093 then
      completed successfully on that same merged head. Downstream merged-head
      consumer fixes PR 5756 / 0e84abd736d0 and PR 5757 / 5c253e21b4f7 also
      passed their exact-head semantic CI runs 31894942765 and 31896763803.
      Execution packs remain transport only; shared semantic identity,
      exact-base causality, complete accounting, infrastructure refusal,
      ancestry-valid monotone healing, authority self-excuse refusal, and
      ProofFreshness remain the governing contract. PR 5591 remains historical
      W-REWRITE archaeology only; completing this wave does not commission or
      complete W-REWRITE or any CI-speed/scoping wave.
  - id: W-PR-EVENT-CAUSALITY
    title: Candidate authority and lifecycle-event causality closure
    status: done
    pr: 6252
    note: >
      PR #6252 closed both causality races and merged as
      27711c21665788bb9804b05b03a2587860679646. Candidate authority no
      longer treats mutable same-ref live-base equality as candidate identity,
      while semantic CI remains the sole exact synthetic-merge/base proof;
      `closed` no longer enters the PR proof trigger or concurrency slot, so
      only opened, synchronize, and reopened produce proof. Exact-head evidence
      is semantic CI 32593286806, fences 32593286723, and ci-authority
      32593286769, all successful on subject 004452e517ca277596008ab3623beca3f707fa33.
      Current main contains the merge. No replacement cancellation service,
      semantic-proof weakening, or Fundamental Forensics change was introduced.
      Evidence: DSC:PR-EVENT-DELIVERY-IS-NOT-CANDIDATE-IDENTITY.
  - id: W-GATE-SPLIT
    title: Merge gate tests code against fixtures; data receipts post-nightly
    status: in_progress
    note: >
      Root cause DSC:MERGE-GATE-IS-GATED-ON-MOVING-DATA (main green 44%
      because 130-by-heuristic / 74-by-judgment of 194 merge-gate jobs assert
      on the nightly-rewritten tree). W1 merged 2026-08-19 as PR 5954: every
      legacy job declares gate: code | data (120/74; judgment pass over every
      named suite; decisive discriminator = git authorship of the asserted
      file). W2 MERGED 2026-08-19 10:58Z as PR 5969: ci.yml plans/packs --gate code everywhere
      (baselines prove exactly what the gate runs; the planner fallback is
      gated too), gate: data jobs run in .github/workflows/data-health.yml
      after a SUCCESSFUL nightly, failure feeds one standing data-health
      issue; W4 reachability + no-empty-pack guards ship with it. Opus
      pre-PR review fixed 2 blockers + 4 majors in the lane (repo resolution,
      label ensure, needs-result-not-artifact-presence, literal concurrency
      group, nightly-conclusion gate, fail-closed lookup).
  - id: W-CONTRACT-DELTA
    title: Differential pre-merge contract gate (post-merge jam class closed)
    status: awaiting_ci
    note: >
      2026-08-19 afternoon jam: merges 5872/5932 grew two curated-exclusive
      import closures without widening paths; the closure contract test runs
      only POST-merge (integration-baseline on main pushes; path-scoped PR
      packs never reach it), so the culprits merged green, main went red
      ~12:00Z, the breaker latched, and 21 armed PRs sat baseline-blocked
      ~6h. Heal = PR 6002 (paths widened, merged 18:19Z as main-red-repair;
      integration-baseline 32291151787 green 19:06Z; note the 6002 merge
      push itself SCHEDULED NO integration-baseline run - silent-no-run
      class - recovered via workflow_dispatch). Permanent = PR 6005 (merged
      19:27Z on green main): always-on contract-delta job in ci.yml, PR
      events only, feeding ci-gate needs; scripts/check_contract_delta.py
      fails ONLY on findings the PR's tree introduces vs its base (closure
      misses by (job,path); unwired suites by path) - inherited reds print
      as notices, so a red main can never re-jam the fleet at PR level.
      Finding computation is factored into run_ci_pack.py /
      audit_unrun_tests.py and shared with the absolute tests (no drift
      copy). Proven both directions pre-merge (0-introduced exit 0 against
      the then-red main; simulated introduced defect exit 1 naming the fix).
      Five suites remain unwired on main (analyzer_i18n_percentile,
      check_stock_dossier_integrity, china_special_situations_truth_wave1,
      dossier_identity_end_to_end, dossier_numeric_contract) - they red only
      the data-gated workflow-yaml job (data-health lane); owners' follow-up,
      deliberately not absorbed.
  - id: W3-PLANNER-CONTAINMENT
    title: ci-plan working-tree containment on the sole ci.yml carrier
    status: done
    pr: 6286
    note: >
      PR #6286 merged 2026-08-25T22:36:54Z as
      fafe8d7ee775f8b60a0229c085fb7aee6d4349e7 on exact head
      a8842dd5c6db23753c916aa27005aa7cab0c88ab under Sol's corrected W3
      acceptance law (review 5023367453) and the Chairman release recorded
      on the carrier. The corrected gate replaced the sub-60s ci-plan timing
      metric (hosted ref-fetch latency is not W3's capability) with one
      truthful terminal same-head binding graph: run 32893976114 attempt 2
      concluded SUCCESS at 22:19:30Z after attempt 1's ci-pack-6 died inside
      actions/checkout for ~64 minutes with zero tests executed — a
      checkout-only infrastructure failure recorded as issue #6351 evidence,
      healed by the one permitted same-head targeted retry. W3 deliberately
      fixed ci-plan only: the planner runs in a sparse tracked-paths
      checkout (--tracked-paths-file, scripts/ci_scope_dependencies) while
      ci-pack materialization remains the old hosted blob:none full-tree
      path, now explicitly owned by the #6351 trusted self-hosted promotion.
  - id: W-SELFHOSTED-BRIDGE
    title: P0R diagnostic bridge — canary reconciled to the current semantic contract
    status: in_progress
    note: >
      Issue #6351 is the sole coordination/evidence carrier for trusted
      self-hosted CI promotion (Sol CEO incident command 2026-08-25T19:52Z;
      Fable COO is the single principal owner bridge through P4). The bridge
      implements Sol's frozen design: one narrowly admitted diagnostic plan
      pair (pr_head/workflow_dispatch, valid ONLY for workflow
      infrastructure-selfhosted-ci-canary) in build_plan and
      load_authoritative_plan; ci_semantic_proof byte-unchanged and
      hostile-tested closed; canary pinned to Python 3.12.13 and gate code;
      hosted and self-hosted canary consumers consume ONE frozen plan via
      --plan-json with strict semantic-fragment parity; portable Linux
      execution profile v2 per DEC:CI-EXECUTION-PROFILE-V2. P0R/current-main
      closure is green through merge baseline 32942786458. P1 run 32945782277
      then failed before PC pickup because the canary resolver treated the PR
      API's stale base.sha as the synthetic merge ref's authoritative first
      parent (the observed API base lagged that exact parent by 23 commits).
      Production ci.yml already derives tested_base_sha from merge parent 1;
      #6351's bounded resolver correction merged through PR #6467 as
      b6b2307d34110052eaedd1a3779353b1779c3308. P1 run 32957250432 then
      proved exact hosted/self-hosted pack-0 semantic parity, missing-cache
      refusal, different-tree contamination isolation, and one PC CI slot at
      220.080s versus hosted 799.132s (3.63x). P2 run 32960314514 proved
      three distinct sealed PC slots concurrently at 174.986-254.000s,
      byte-stable shared cache, load-1m peak 4.053 on 16 CPUs, at least
      42.77GB memory available, and an independently routable render slot
      while pc-render-1 executed real production render work. Exact trusted
      manual comparison of the uploaded pack 0/1/9 receipts returned parity
      true for all three. The run wrapper concluded cancelled only because
      pack-9's receipt-only hosted compare job spent its full ten-minute
      budget materializing a redundant full repository checkout. The bounded
      P2R repair now publishes a runtime-complete, package-shaped
      main-defined comparator artifact before candidate checkout or any
      candidate-authored execution, and removes that compare-only checkout;
      executable tests lock both bundle imports and upload ordering. It does
      not change production routing or semantic authority. Sequence after P2R:
      P3A inert trusted executor, P3B production route with hosted ci-pack-N
      anchors, then P4 three natural PR proofs. P2 is now accepted from the
      combined receipts: run 32960314514 proved three concurrent PC CI slots and
      an independently acquired pc-render-4 reservation; run 32964925696 made
      checkoutless parity green for packs 0/1/9 on one exact tree and plan. PC
      wall time was 164.689-216.668s versus hosted 680.467-2050.9s, all semantic
      fragments were byte-identical, cache bytes were unchanged and the resource
      envelope stayed safe. P3A merged through PR #6481 as
      7dc0b0ddcd6dd7323a0bf9d45b4ebf6ebc785531. The exact main-pinned workflow
      was added as the fifth selected workflow in the existing organization runner
      group, and the merged root admission was deployed with identical hash
      e4ff74a96e9949a0ce4707e3fdb58cfffc251057d5e8c69a7309fe2871e11202;
      direct main admission passed and a hostile PR ref remained refused. First
      dispatch 33024021850 then failed closed before PC pickup: after exact resolver
      and candidate checkout success, hosted planning invoked the older candidate
      scripts/run_ci_pack.py, which does not admit the trusted executor event pair,
      so no plan artifact existed. P3A-R on the same #6351 program froze and
      transported the complete main-owned planner/semantic/control bundle while
      retaining the exact candidate tree and manifest. It merged through PR
      #6487 as ac3f8a888e2ece7a15f37180c19dc247227a3098. Direct main proof run
      33030976647 then passed on pc-ci-3 against PR #6390 with exact
      main/control SHA ac3f8a888e2ece7a15f37180c19dc247227a3098, tested merge
      078bdb7d212a3bcabea9df6ba06a6ef7bcf5ee07, plan
      1ad0b428cac9e81481545358f9e30b151c3fdffe88d28ed7bc99be8d5ac7e720,
      matching fragment/control/receipt identity, stable 66,228,371,240-byte
      root-owned cache, 60.03% peak CPU, 38.55GB memory-available floor and
      218.947s wall time. P3B-A then merged through PR #6496 as
      904863dabc490ee95ac50153048c25dee048d90b. Its exact-head hosted run
      33035115527 passed one planner, contract delta, all twelve packs and the
      semantic gate; those packs consumed about 180.7 hosted minutes and the
      slowest pack ran 38m22s. P3B-B is the separate active carrier: call the
      exact main-owned executor only for same-repository PRs, preserve hosted
      planner/ci-pack-N anchors/ci-gate and the complete hosted fork path, and
      prove the route on its own exact PR tree before P4 natural traffic. PR
      #6505 run 33039532309 reached all twelve real PC jobs but the root hook
      refused them before steps because job `env` is unavailable pre-job;
      contract-delta also caught the new route suite unwired. The same carrier
      now uses GitHub's event payload, forwards it in the root-owned wrapper and
      wires the suite. Post-restart PC hashes are Python 69faac248f755829a39f6821f17015382788056991f6d1ff9046b1842e86a002
      and wrapper d55f046e6a6a758f55e311ed73b921e007c8570cc0aba11e0cafdc31cef06dee;
      run 33043922465 then executed the complete twelve-pack matrix: packs
      0/1/2/3/4/7/8/10/11 passed and packs 5/6/9 exposed the complete sealed-host
      portability set. The same carrier now derives replay's loader directory
      from the selected interpreter while stripping credentials, scopes the
      set-ID fixture to exact descriptor metadata, preserves Git-config refusal
      across client behavior, and projects the caller's PR branch identity into
      the detached trusted executor. Repaired exact execution/parity/gate proof
      remains owed.
  - id: W-THROUGHPUT-20261019
    title: Measured CI throughput and bounded planner/weight trials
    status: in_progress
    note: >
      Chairman's October 19 commission is assigned to Codex session
      01a153e8-3c85-7bb2-af63-7f477b570512. The 40-run baseline retains 22
      noncancelled first attempts, 17 cancellations and one separate rerun.
      Successful first-attempt run-to-gate p50/p95 is 3196/4074 seconds.
      Initial trial removes duplicate named-suite closure traversal within one
      planner command; twelve packs and all semantic/gate contracts remain.
      Existing PR 8126 is already delivered and PR 8094 remains separate.
      Research and limitations: research/ci_pack_throughput_20261019/README.md.
      Current continuation: agentos/handoffs/WS-CI-MERGE-CONTROL-PLANE-2026-10-19-THROUGHPUT.md.
      PR 9722 merged as 7736fd72895fc24e55bf2d4bbc7b1f4e94203414 with full
      hosted proof. First broad trial took 78.1 minutes, including 825 seconds
      of post-pack queueing; packing-contract group 740.414 seconds versus a
      historical 847.738-second median is descriptive, not a causal gain.
      Natural cohort has 37 verified first-attempt completions, two selected-set
      matches but zero execution-proof matches and nine pending; no causal gain.
      A twelve-pack replay of all 255 measured job costs supports a bounded
      FIF/earnings weight calibration: modeled maximum command time
      2085.4 to 1532.3 seconds, excluding install/checkout/queue effects.
      Trial PR9763 incorporated landed Defense heal PR9758. The next run
      passed Defense but found a missing schema identifier from PR9765 on
      both candidate and base. A one-field schema registry repair reproduces
      three failures before and passes181 affected tests after. PR9763 merged as
      38d2dac36faabfff04f8efe5ee28e5c8dfa1c5ae after all257 jobs and active checks
      passed in run39298424658. Source landing verified; observer50933 consumed.
      Weighted full trial48.82min/371.70 summed job minutes, versus78.08/337.38
      earlier with different work; no causal gain or cost neutrality established.
      Exact-run command replay2694.53 to2266.33sec supports retaining two weights,
      not additional expansion. Collect a separate post18:49:48Z natural cohort;
      Report PR9780 merged576e21dc2e46bea739465c84a33ffbdf2135cd78, source verified.
      Weighted20:48 cohort32runs/19verified completions/9pending/4cancelled;
      scoped-success N13 p50/p95 2106/3941sec, summed wall215.68/399.37min.
      No exact baseline proof matches; nine completions select neither calibrated
      job. One exploratory adjacent-window exact pair is unexposed and has
      different failure/success outcomes, so cannot estimate the weights' benefit.
      Successful tail has3205sec execution wrapper with two exact-ancestry
      depth8->32 waits691/726sec. Next bounded trial rechecks existing ancestry
      before fetching, preventing a later consumer from re-shallowing complete
      history. Real shallow-Git regression fails before, nine recovery tests pass
      after;199 authority tests plus repaired mock pass, manifest validates.
      PR9791 merged c3c67487f42e1c54986b2e95dca327946fdc5ed0 at21:52:31Z;
      run39324251115 passed258 jobs/554proof units and all active checks.
      All eight source/test/report blobs verified. One real ruling-graph reuse
      notice, five necessary deepening paths; no cache, proof relaxation or shards.
      Trial42.12min/362.57 summed wall min; FIF commands2120.20sec critical.
      Reuse was noncritical; no causal target or cost-neutrality claim.
      Collect a separate post21:52:31Z cohort under blob
      f92be10fc37455fd427829f0f964c5ef581b3a80 and exact merge ancestry.
      At23:56Z29runs:12verified successes,13pending,4cancelled. ScopedN11
      p50/p951981/2863sec, wall196.25/278.23min. No original/weighted full
      proof matches; one original selected-set match has two changed definitions.
      Natural39330880213 confirms reuse in noncritical pack8. Two other runs
      have potential reuse on critical packs; inspect before attributing savings.
      Report9801 merged368c4c3a660215a0bf4809c9b8ff5e65098f413a;6blobs verified.
      Fixed00:55 snapshot45runs/31eligible completions(29success,2failure),
      7pending/7cancelled. ScopedN27 p50/p951966/2863sec, wall186.47/278.23min;
      zero original/weighted proof matches. Both targeted critical-pack logs show
      reuse, without counterfactual saved seconds. FIF alone critical9times and
      control-plane alone8times; no outer-shard expansion justified.
      PR9479/9797 failures are candidate-specific with passing isolated bases;
      preserve their carriers. Hold the cohort fixed. Six slowest scoped successes
      are FIF-alone critical. Exact-source72tests pass403.73sec; focused profile
      identifies repeated ASCII and direct-text scans in the SEC parser.
      Fourth trial replaces the byte loop with isascii and uses the existing
      event index before the unchanged owner filter; no semantic/proof/shard change.
      Parser214tests pass, new scan regression fails before, two complete filing
      outputs match. Alternating local CPU0.8960 to0.6836sec is descriptive only.
      Same72tests pass335.45sec vs403.73before. PR9813 merged9c7df3786fc3856fbb692da301584b4b443ab66d
      at2026-10-20T04:57:13Z; seven blobs verified. Final39364786931 passes
      96jobs/299proof units/zero infrastructure findings and all active checks.
      Three green trial FIF commands1581.75/2093.14/1573.07sec show variation.
      Next: separate natural parser cohort with exact parser plus planner blobs
      and merge ancestry; earlier00:55 cohort remains fixed.
      Fixed parser05:54 cohort16runs has5qualified completions(3success2failure),
      11pending/0cancelled/0reruns. Success p50/p951860/2218sec,wall228.50/252.18min;
      failure first-step-completion950.5/1002sec. Zero original-baseline proof matches.
      Exact secondary pairs differ in outcome; one artifact-upload failure and one
      AgentOS candidate/base-signature mismatch, with existing repair carriers retained.
      No causal fleet30percent or cost-neutrality claim.
      Report9850 merged6793c010048996193d3d98876b486910c7982e3c;75selected jobs,
      active gates and6authored blobs verified. Fixed07:54 parser snapshot57runs:
      36qualified completions(29success7failure),18pending3cancelled. ScopedN24
      success p50/p951895/2553sec,wall177.675/253.95min;zero baseline proof matches.
      Three103job successful treatments share ONE old-parser control. Gate times
      2066/2581/2553sec versus2007control; summed wall lower, no causal claim.
      Treated FIF commands1594.096/2151.041/2089.544sec versus1329.857control;
      treated2681passes versus2680control. Primary command dominates; image and
      Python labels agree among treatments but physical performance is uncontrolled.
      Retain12packs/two weights/parser source. Next source slice requires qualified
      residual profiling and current FIF carrier custody; no speculative shards.
  - id: W-ACCELERATION-20261104
    title: Cross-repo minute-level CI plan and runner assessment (Mastermind #917)
    status: in_progress
    note: >
      Fable CEO receiver session 6e051448 adjudicated the measured CI speed
      options for Mastermind, Macro and Terminal on 2026-11-04. All three
      repositories are public; Macro PR CI is hosted; the sweeper is bounded
      by MAX_IN_FLIGHT_PR_PROOFS after a check-definition commit stales every
      armed green, not by its cron. First packet delivered as Mastermind
      PR 2044 (six-shard re-pin). Macro-side next actions X1 (scoped
      staleness rule), X2 (adaptive in-flight cap) and X3 (native queue
      premise re-test) are sequenced after PR 10652 and PR 10682.
      Current continuation: agentos/handoffs/WS-CI-MERGE-CONTROL-PLANE-2026-11-04-ACCELERATION.md.
      Chairman recommissioned end-to-end acceleration on2026-11-07. Mission
      remains all three repositories at lightning speed with original journeys,
      selected coverage, failure behavior and release authority preserved.
      Verified compatible source-law pin66780ab7e3e9fdbfd40713bb5791fb1888529f7c
      is retained. Existing Phase4 and this wave own the programme; no new
      planner, queue, watcher, runtime, identity store, acceptance owner or root.
      Current master architecture is published in original Mastermind PR2191:
      https://github.com/mastermindx-market-intelligence/Mastermind/blob/980429a1ffdc30fac79c36f87e7d766539967ee0/docs/CI_LIGHTNING_ARCHITECTURE.md.
      Exact document blob 958ed1e1c829fb9ce4946c17a90477951cdeab40 is read back.
      Its current plan gives300s full-verdict,180s ordinary-PR and90s
      trusted-docs p95 targets, per-repository critical-path budgets, integration
      order, source/collision map, original holds, rollback and natural-cohort
      acceptance. Targets remain unachieved. Complete earlier research/receipts
      remain linked at immutable8b549d74; do not repeat accepted work.
      Accepted continuity10825 remains efdf3577;10827 is now accepted at
      0c02daa5c4e6a986b6fc2553d1c3b7a5cd495002. Do not update/reopen that carrier.
      Its historical full record is preserved at that merge's version of this file.
      This fresh follow-up uses operation
      ci-lightning-continuity-20261107-c2-frontier, based on inspected main
      8e2cdcb007ec1c48f39106431b448b11e41a772e, changing only this wave's note.
      Mastermind2065 publishes d26440aac2c45b960d7175836121b885d94f9301.
      Protected107-file manifest/accepted inverse-chain composition is qualified
      by587 complete-file passes. Observer capture and pytest9.2 lock alignment
      are composed; DO_NOT_REDO. Current required42394477066 failed in17m40s:
      shard2's selected pytest phase never ran after its H1 prerequisite failed.
      Serial RWE42394477042 passed in34m41s, with2334 complete unique module
      companions/70693 collected-invoked-finished cases and zero evidence errors.
      Five required shards match1979 modules/60268 cases;355 modules/10425
      cases remain without parallel evidence. Dependency profiles differ, so
      those timings are not a matched speed proof.
      Controlled serial RWE 42398700247 is SUCCESS, all eight jobs complete.
      All six receipts match CPython3.12.16, environment58de61f3d39fc214,
      78 packages/freeze185d3127c6dabf1a98442541ddcf9732ea3d0551ac4e2973bd9717d7b8f5b247
      and exact vendor; all70693 case companions are complete. Longest gate
      1934.55s; final aggregate waited370s then ran2s. The processes4 half was
      dispatched exactly once and reconciled as run42402970898, initially QUEUED
      from18:46:50. Keep remote d264 frozen until this pair is fully consumed.
      RWE does not invoke the held positive H1 Docker prefix.
      Original-workspace fixture commit2c433be85c03db48b92b779b1e26f512fd5533d5
      remains unpublished while remote d264 is frozen. Trend44
      unchanged cases/assertions and independent references pass; per-test
      seed/deepcopies reduce holdout construction10-to3 and local phase time
      85.131132-to76.740074s. Capacity18 unchanged crash cases plus one real
      helper isolation case pass; independent full Git copies reduce phase
      155.057522-to145.788483s before2.081032s isolation cost. No global ACL,
      TMPDIR or guard changes. Native required capacity68.532505s is below the
      90s unit target; Trend208.098650s remains the stronger granularity target.
      Diagnostic commitdc4f4aa699a3bb1d285073d34a9652fe445dcbec is locally qualified:
      96 synthetic contracts pass, zero skips/failures/errors,1.704s controller.
      Only rc75/non-timeout/exact refusal can emit11 allowed reason codes and
      seven bounded numeric facts; private stale labels and raw output are
      discarded. Helper blob6646f958ba88383861018c9a14c10c9ab4978304;
      companion4fdd26e65d53657ae494eb3bddef83ce09886f75. No positive fixture,
      admission threshold, settlement logic, workflow or observer was changed.
      This cannot recover the discarded native snapshot or establish its cause.
      Trend partition commite888d046d3dbe6d0d2fa566a06b2ffbf897acaf3 is locally
      qualified and unpushed. All42 test-function and support ASTs are unchanged
      from the fixture candidate. Separate17/16/11-case invocations pass, plus
      138 selector checks;17 node IDs stay unchanged and27 change only module
      prefix. Module controller times31.563/27.060/24.585s are local evidence,
      not native limits. The existing selector puts the three groups at3/0,
      3/1 and4/0, adds two modules and moves no unrelated module. Complete
      44-case mapping/proof is source-linked beside the current architecture as
      docs/CI_TREND_PARTITION_PROOF_20261107.json, blob4fab18b110d20eff4bda9b15fd436f20a9084181.
      New-source required qualification after the pair is independent only while
      the original private-container/tmpfs/exclusive-home/settlement contract
      stays intact. Parent verified unchanged workflow6e16bcf6, Docker69bf590e
      and provider fixturea80cf451 at local e888. This neither resumes original
      ATT-1 nor infers its cleanup; old H1 and release holds remain.
      Reserved Mastermind1714 head47164aef owns the SDK/runtime lane and
      overlaps pyproject/both RWE locks; regenerate combined-input provenance
      at composition. Reservation alone is not a live-writer/global fence.
      Macro10752 publishes5e23be9cd4f73bfb298206ddd79886ef9d9e168e;476 tests+
      10 subtests pass with two existing sparse skips. Native42397007951 is
      incomplete at the milestone: ten packs succeeded, packs0/10 still executed.
      Current aggregate and a natural narrowed consumer are owed.
      Macro10658 publishes9f3fe48a28c5d3fe45494ad111a63742efbc1737, composed
      with86fdcd66. Original stale merge is reconciled; publication is clean.
      Its120 ordered FIF targets and other391 logical jobs are preserved.
      One fresh interpreter/file, at most two concurrent files, isolates Python
      state only. All80 focused tests and392-job/394-fragment check pass.
      Sparse source lacks the sealed sector-cycles renderer/manifest: native
      full-source proof of accepted c4844c22 remains owed. Run42400346906 owns
      that qualification; its final result is not yet consumed. Authority/fences
      passed. Existing MOG refusal/labels are unchanged.
      Later compose with10788's44/37/39 split using each sibling's own list;
      add helper to all three closures1139-to1140 and preserve B's extra work.
      Failed10738 shared-xdist remains evidence, not a fallback.
      Macro10788 publishes4281c1886f52a93913f6eec85f9f4407fd738fb6.
      Predecessor eb307 native42385192083 passed61m59s. Current42390957332
      failed75m52s with320 jobs/692 steps:682 passed/10 unknown. International
      exhausted one20-minute deadline; IM14browser had86.05s left and no full
      terminal summary. Pack4 passed, but FIF-C command1213.133s and dislocation
      groups600.282s show that timeout repair alone cannot meet five minutes.
      Source granularity/rendering plan is in2191; do not replay uncertain work.
      Macro10755/10770/10766 are accepted;10656/main admission remain OFF.
      Terminal1297 and1334 are accepted DO_NOT_REDO; original context/link
      journeys and bilingual evidence remain. Terminal1306 publishes
      418f44dd8302954892ff194b4dc12477288699c9 after scoped-CI composition;
      264 focused passes. Native42397250070 is now SUCCESS: all19 jobs/all12
      browser jobs and required aggregate passed on hosted ubuntu-latest.
      Longest browser job55m29s; unit/typecheck20m08s; aggregate queued242s;
      full observed path59m57s. Actual event checkout9798d310ea90c3805a8d973dfb8ed2f8bd025ae6
      binds all browser/unit logs. Browser summaries account for4693 cases:
      3693 passed,999 skipped,one flaky mobile J1,zero final failures. Its context
      repair remains owned by1338; broad skip reasons are not all audited.
      Unit20394 passed/50 skipped/3 todo. No optional fleet was activated or qualified.
      Restricted trust/isolation, ephemeral cleanup, capacity/rollback remain.
      Terminal1338 publishes92c5b806b4168f1cd011d25044e3355aa32011e9.
      Prior2a996 native42387278303 cancelled78m04s: desktop5 had16 failed
      cases/32 retry records. First screenshot shows Prophet data-read failure;
      two trace requests lacked completion. No429 or root server cause proved.
      Existing warmup now checks fixture provenance/status/complete JSON/schema
      under one25s deadline. All15 unit contracts and16 original desktop cases
      pass locally, one worker/zero retry/flakes. Local Node26.5/warm build differ
      from native20.20.2; no hosted causal-speed claim. Native42399940917 is
      RUNNING; source-bound capture/evidence composition remains required.
      Preserve exact held effects in2191: H1 run42394477066/job128468846887,
      ATT-1 receipt absent/rc75/admission refused, settlement unknown; discarded
      Docker/tmpfs state is not recovery proof. Historical initializer custody,
      actuator cause and Gateway HOLD6704040875 remain. Local ACL bracket
      proof does not release them. Macro International run42390957332/
      job128458803087 lacks whole-tree settlement/disposal; attempted SIGKILL
      and generic Actions cleanup are insufficient. No restoration/base replay.
      Macro10674 operation26751 remains EFFECT_UNKNOWN before10745-to10735.
      Terminal1223 original create-commit remains EFFECT_UNKNOWN under operation
      mastermind-queue-clearance-20261104-c1, tree8a95165da4779cbbee961f6fc903de02afd1e27f;
      full actor/parents and exhausted bounded diagnosis are pinned in2191.
      Do not replay/rehome or duplicate its topology/trace/timing/Node work.
      Holds are lane-local. Macro/Terminal protection-read403s are unavailable
      rule visibility, not inferred blanket admin gates. Preserve the separately
      denied Terminal administrative action and2065 comment write; no carrier/
      account replay. Source/PR-body publication remains permitted. Formal
      non-author approval only where actually mandatory; no self-approval/merge.
      Fabric roots remain consumed/blocked; existing parent direct-integration
      exception applies, with no new roots. Native C3 is read-only judgment.
      C3 Trend/H1/native/composition judgments are completed; no child editing,
      testing or execution. No external messages or daemon claim.
      Current state MORE_WORK_EXISTS. Next consume42402970898 against fully
      qualified42398700247 and reconcile10752/10658/1338 native outcomes.
      Publish the committed local2065 slices only after the pair's source boundary
      and verified independence. Prepare original10788 main/FIF composition
      without invoking its held International command. Continue measured long-unit
      work while exact held effects await their required receipts. Full acceptance
      still needs original journeys, complete selected evidence/current required
      paths, trust/isolation and natural latency cohorts; green CI alone is not it.
next_action: >
  W-TRANSPORT and W-PR-EVENT-CAUSALITY are closed. Do not reopen either for a
  new CI-speed, runner, branch-protection, or cancellation-system proposal.
  Continue W-GATE-SPLIT and W-CONTRACT-DELTA only under their existing evidence
  gates; W-REWRITE remains separately commissioned. Verify contract-delta
  appears and behaves on the next few ordinary PRs
  (inherited-immune, catches introduced closure/unwired defects); confirm
  the armed backlog fully drains post-breaker-open (21 -> 17 within an hour
  of the 19:06Z green). Then W3 at >=72h from the W2 merge (~08-22):
  trailing-100 green rate above 90% via
  scripts/ci_gate_reliability_report.py plus two consecutive ordinary PRs
  merged with no main-red-repair. W-SEMANTIC-PROOF remains stopped; W-REWRITE
  remains separately commissioned.
  W3-PLANNER-CONTAINMENT is closed; W-SELFHOSTED-BRIDGE (issue #6351, Fable
  COO principal) owns the permanent ci-pack materialization repair — hosted
  packs still run the blob:none full-tree checkout that produced the #6406
  and #6286 attempt-1 checkout-only failures; do not absorb pack-checkout
  repairs into product PRs or reopen them here outside the #6351 sequence.
  P3A-R and its repaired direct-main dispatch are accepted; run 33024021850 is
  a closed diagnostic receipt, not a retry candidate. P3B-A is accepted on main.
  Complete the separate P3B-B carrier: make the exact protected-main zero-input
  call for same-repository PRs, retain the hosted fork implementation and hosted
  planner/anchors/ci-gate, and prove the new route on its own exact PR tree before
  P4 natural traffic.
owns_paths:
  - ".github/workflows/ci.yml"
  - ".github/workflows/merge-on-green.yml"
  - ".github/workflows/fences.yml"
  - "scripts/ci_authority.py"
  - "scripts/run_ci_pack.py"
  - "scripts/merge_on_green.py"
  - "scripts/check_self_mod_fence.py"
  - ".github/workflows/trusted-ci-executor.yml"
---

The E2BIG incident model and receipts live in
DSC:CI-CHANGED-FILES-ENV-HAS-AN-EXECVE-CEILING and the session handoff
CI-MERGE-CONTROL-PLANE-2026-08-14-e2big.md. The competing rewrite lineages'
own documentation lives in their PRs (5585 and 5591 both closed unmerged).
The mandatory pre-build semantic-step census is committed as
`DSC-CI-SEMANTIC-PROOF-MANIFEST-CENSUS.v1.json`.

## W-SEMANTIC-PROOF engineering receipts

- The pinned pre-build census records 193 logical jobs, 614 semantic steps,
  185 dependency-install steps, zero unnamed executable steps, and one
  two-step duplicate-name group. Only those two SBIR/STTR steps received
  explicit `proof_id` values. After fresh-main reconciliation the validated
  manifest has 194 logical jobs and 623 semantic units; no new ambiguity was
  introduced.
- `ci.pack_plan.v2` binds workflow/run/event role, tested merge tree, subject
  head, exact base, changed-file digest, semantic inventory, execution digests,
  and transport partition. `ci.semantic_fragment.v1` carries raw bounded pack
  observations. `ci.semantic_evidence.v1` is written once by `ci-gate`, including
  on planner failure, and is the only semantic-era causality verdict.
- Exact-base replay creates one independently pinned checkout, uses the base
  checkout's runner and manifest, and runs at most one serial child per failed
  logical job under one 900-second deadline. It does not create a replay matrix.
- The hostile mutation battery killed 14/14 required mutations. It exposed and
  closed a real missing-ancestry regression fixture before reaching zero
  survivors. Fresh review also closed main infrastructure bypass, job-level
  infrastructure healing, inactive pilot-authority context handling, and a
  production Unicode plan-digest mismatch.
- Local performance at the pre-release carrier: semantic inventory median
  6.316 ms (p95 9.010 ms), full plan median 9.233 ms, bounded failure capture
  over 1,001 representative lines median 0.444 ms (p95 0.702 ms), and full
  194-job/622-unit reconciliation median 12.106 ms (p95 18.490 ms). Exact-base
  checkout became ready in 129.346 s and checkout plus bounded cleanup took
  160.354 s, inside the shared 900-second red-only budget. These are overhead
  measurements, not a claim that the CI suite itself is faster.
- Green consumer paths make zero semantic artifact calls. A linked red PR lookup
  is bounded to three JSON calls plus one artifact download; descendant history
  is capped at 12 candidates. Main semantic dispatch is exact-SHA-bound and costs
  at most three calls when a red breaker lacks current evidence.
- Bootstrap remains deliberately unresolved in this file: this authority-changing
  branch must earn the old required checks without using its new inherited-red
  reasoning. Status stays `in_progress` until merged-main verification.

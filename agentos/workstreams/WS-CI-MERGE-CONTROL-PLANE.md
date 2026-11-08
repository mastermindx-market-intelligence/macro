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
      Chairman recommissioned all-three-repository acceleration on 2026-11-07.
      Preserve truthful source/input bindings, all selected coverage, original
      product journeys and release authority. Current lifecycle MORE_WORK_EXISTS;
      no five-minute p95 or completed production upgrade is claimed. This
      2026-11-08 00:03 UTC milestone supersedes the current snapshot at2127c6cf;
      historical failed trials and uncertain effects remain historical.

      Governing pin66780ab7e3e9fdbfd40713bb5791fb1888529f7c remains compatible.
      Complete20e17-to-f4f8 census10commits/32paths and f4f8-to-1890f608
      census4commits/28paths contain no governing guide change. Mastermind
      delivery guide19a13a3b was reread atf4f8. Macro AGENTS3d18585b and
      delivery220d23a9 remain unchanged. Terminal root AGENTS08c5a252 at
      ec21ec04 was read in full: native queue24411653 requires ordinary
      exact-head admission without delete-branch; nested older wording does
      not override it. Existing Phase4/this wave/#6351 own the work. No new
      scheduler, queue, retry/identity owner, watcher or runtime authority.
      Fabric roots remain exhausted/blocked; the recorded attended-parent
      exception continues; native children provide bounded C3 judgment only.

      Master architecture2191 is protected-merged as
      accb4a6bcc1f721b93b10f43881cda67eca104ea. Follow-up2251 publishes
      fdb5c952344cfdda85223759b4ab7a7b2970e518; its original native entry
      MQE_lQDOTotz3c8AAAABNlLAWs4ABAiKzgPO398 is AWAITING_CHECKS position1
      at00:02UTC, enqueued23:07:20 by the assigned delivery root. Preserve it.
      GitHub refused the queued-ref update; fdb5 remains unchanged. Prepared
      evidence commit57b19290fa53767a0a4e3f89e2a4907aa4c6e32f and
      architecture blob6d9c3e4277b32531ab5465fbc2dc92d110302eb5 are immutable
      objects NOT attached to that branch or accepted main; later evidence
      below supersedes parts of that prepared text. Do not dequeue or bypass.
      Reconcile actual queue outcome before an ordinary document continuation.
      Targets: docs p95<=90s, ordinary<=180s, full<=300s, interim full<=600s,
      at least30 successive natural eligible observations per populated class.
      Account for queue, plan, checkout, readiness, useful execution and fan-in;
      no isolated fast observation substitutes for end-to-end cohort acceptance.

      Mastermind2065 original head e6737ba03a254310e5eddb28dbe0839713b72694
      has required42419148121 and RWE42419148128 SUCCESS on exact merge
      9c73e295dc2f659db899d4d5dda11734994980c2,
      treee0363dfd2aa864d6719a79533f763df188749c20, parents20e17+e673.
      Both complete2374modules/72084collected=invoked=finished with identical
      per-module identity/outcome hashes; zero evidence errors/deselection/
      incomplete modules, all24children exit0, six RWE ZIPs verified. Counts
      mean completed cases, not72084ordinaryPASS. Required25m05 versus
      RWE34m43 use different dependency profiles, not controlled speedup.
      Required limiting shard waits427s after scope then runs1048s; final
      dependency-to-aggregate14s. Limiting child service840.89s; accepted
      Trend split is not its tail. Native correctness does not release
      H1/Gateway/initializer holds. Preserve old d264/ce38 failures and the
      exact older local800/271/791/137 cohorts; no habitual reruns.

      Mastermind2256 completes the next safe market-view fixture slice.
      Original operationci-lightning-mm-market-fixture-20261107-c2 publishes
      f308d737924d002d23f5fc7e4a1ae90f6e149f54, parentf4f8ddc.
      Only tests/test_market_view.py changes fae0f27b to
      24efb2c8cb58e6898e8132a005de0b0e101800d0. Genuine doctrine is loaded
      once lazily and deep-copied on EVERY read; real view/adapters/builds/
      values/native calendar behavior remains. All15definitions,130assertions
      and54case identities survive; direct nested-mutation/restoration proof
      passes. Same locked local Python3.12.13 profile54PASS before/after:
      76.3377s/1088YAMLcalls becomes4.6946s/onecall. This is local attribution,
      not matched hosted latency or p95. Native CI42426020447 SUCCESS in89s
      tests merge5b1997bbd239b810d58bfb5a1a8b72aff1050ddb,
      tree043870640b78c271d48a3a0dc2613362869585c7, parents1890f608+f308,
      with the exact new fixture blob and actual Macro256c757b engine/lib.
      Trusted STANDARD smoke executes pytest-policy plus market-view:147pass
      indicators, no failure/skip/xfail, six-second step/61sjob. Full shards
      intentionally skip;2368discovered is plan-only, not execution. No native
      node/per-module timing artifact exists. CodeQL42426018219 also succeeds.
      A protection-detail GET returned403 and remains ended. Distinct permitted
      PR/queue metadata plus current protected delivery law qualified ordinary
      admission; no formal review was mandatory and no denial was replayed.
      One exact-head native request returned0 at00:02:24; independent readback
      verifies MQE_lQDOTotz3c8AAAABNlqymM4ABAiKzgPPAKE, position4 QUEUED,
      unchanged f308 OPEN/Ready. No repeat admission or merge claim.

      Macro10764 now publishes796305a624e711c5cfacf2904334f2b9d6bfe21c,
      parentd39ef2f0, tree062f2596e7ae0db00159e98236e0791f5e8a20bd.
      The prior725PASS schema repair remains: actual semantic loader and
      jobs[].logical_job_id, exact source/role/base provenance, complete
      failed/inherited/not-run/infra inventory, clear-zero versus empty-failure
      distinction, cache/rate-limit safety; all440other definitions unchanged.
      d39 native42422937641 contract-delta exposed exactly one introduced
      closure miss: tests/__init__.py. The one-line catalog repair widens only
      ci-control-plane-contracts;392real jobs validate,130owned closure paths,
      sole miss becomes zero with all other commands/definitions unchanged.
      Catalog a5aa98d8 becomes94f7d97a87cbdf8b731961ac2bfdb9a18772b9c1.
      New natural42426026681 runs on actual merge
      84376a74698026dca80152ea1bea34494c20da0f, treef38bdfde526e5ff0fb268a956b6b6afb143f827c,
      parents1d4708473a4207ea6045fd869990dd3cf5b02ddc+796. At00:02:58,
      contract-delta/ci-plan/packs1and2 SUCCESS,10other packs executing and
      no final ci-gate yet.319planned jobs are not completed semantic evidence.
      ArmLast MOG remains removed; merge-blocked preserved. No source repair
      is justified by this running snapshot. Qualify exact final evidence,
      current freshness and actual holds before rearming.

      Macro10788 at5e7a585fee0650ee53f6727b229322a9f015c5d6 retains
      complete42412023592 SUCCESS63m22:321jobs/694passedsteps, zero infra,
      evidencef83861a98d792b630016c986ad49df4c7fb1130dc5d956b525931598778c5dca.
      All120FIF modules execute once in44/37/39siblings: A1368PASS629.906s,
      B1169PASS820.212s, C1716PASS/1SKIP765.374s. Module launches are not exact
      collected-case parity. Keep unarmed until10764protected merge under
      comments6674602501/6682993935. New International10PASS does not settle
      old timed-out descendants. Macro10658 controller has refreshed dc90 to
      aec6664a07f2ec5b0a80f0a4485f5317e84b37d0 with MOG and
      merge-refresh-in-flight; preserve that live lease. Its prior dc90 proof
      42408989367 SUCCESS47m11/97jobs290steps is historical, not current-head
      proof. Macro10752 keeps existing MOG; prior319jobs691steps89m20 remain
      evidence. No manual refresh, cap change, bulk arm or speed claim.

      Macro8094 at372935854f3ec3db858af6e655441937b5db7fc6 has
      native42415102365 SUCCESS319jobs692passedsteps, noUNKNOWN/inherited/
      infra, authority_changed=true and clear, merge52fa11da6011ba3c91a25f884a43c7cc47cc5b42,
      base60dbeffbc7100752863572f4e426316cead7e3d6,
      evidence87f1dc6a6f32d9aeaa0ec82a45f399699bb0b0a0ca868279c89f5aeea925baa3.
      Historical3UNKNOWN/data-health assertions are not retrocleared. Main's
      catalog changed after its tested base; incumbent freshness remains owed.
      Automatic approval review REJECTED the attempted source-release/
      merge-admission hold disposition, explicitly requiring exact end-user
      authorization because the proposed comment would release a consequential
      hold and enable Ready/MOG. Readback found no release among9comments.
      Keep Draft, original6698103282hold and unarmed. No body/Ready/label,
      carrier/account or wording workaround. Exact human request when needed:
      authorize this8094hold release, then ordinary freshness/CI/MOG if qualified.
      Long benchmark/Fabric denial6596581286 remains fenced.

      W4/#6351 Macro10843 now publishes
      d7715d018400b74c30b4d4cf0e7f30d66a4d3b71, parentf0f9315f,
      original operationci-lightning-macro-execution-input-identity-20261107-c2.
      Identity source81828c66126d34eef3cd5a85fd8b60cd6d106ae6 remains.
      Runner2a2cc2973e15c000dc84695271f43ca13d352672 adds real common-loader
      validation: absent materialization remains implicit full; only exact
      version1 integer/mode full is accepted. Null/bool/float/string versions,
      extra keys, unsupported modes and inactive/data-only invalid jobs fail.
      No catalog declaration, plan key, checkout, selected population or
      execution caller changes.117other production and218incumbent test/helper
      definitions survive.61focused contracts PASS/0skip/fail13.0377s; log
      ecda7cb31f23b359efba020f2436442fb1629161db6c16c8b9ce1b8a3821a95f,
      XMLc4765ba908abf6adde2ab58a7fc3f611ed5626143b8092facd11c44724a2e308.
      New-fixture-only failures57/61 then60/61 were repaired and retained;
      they do not alter the final consumer implementation or erase failures.
      Natural42426766918 runs on actual merge242552f7b5309be1e4ab0373dec63b9214d49d1f,
      treef4ad850ce68e0646c5fe9977ea0ba2bd4698ae2f,
      parentsd492ab036efb9baa570abce06f8fcf30361afe85+d771. At00:02:58,
      contract-delta andci-plan succeed,12packs execute; no final gate.
      320planned jobs are not completed evidence. Fences42426766880 and
      authority42426764589/42426826582 SUCCESS. Ready/unarmed, no enrollment.
      Identity is not complete closure, local blob availability or eligibility.
      The consumer remains full-only. Protected main/control_sha/bundle adoption
      is owed before explicit producer declarations; old consumers reject keys.
      Next safe source phase may inventory exact execution seeds/pytest implicit
      inputs in the existing dependency owner, preserving selector semantics.
      Earnings dossier28modules require conftest optional-import behavior,
      eager package initializers, configuration/plugins and exact11-file
      pg_envelope membership/computed reads. Unresolved obligations force full.
      No non-full activation before complete closure, authoritative plan and
      execution-profile binding, local availability/materialization/modes,
      full pack-union fallback/cleanup, independently pinned full base replay,
      exact case/multiplicity/outcome/skip parity. Historical2740PASS176SKIP
      is insufficient. Preserve10803finite-history holds.6505/P3B-B is merged.

      Terminal1338 remains accepted69c3893169a991b15fe7934b53122d55fd4eaaec.
      Terminal1341d71c569a64c5346419494afc3ca988bd06a56a73 now has
      natural42422916742 SUCCESS19/19jobs, tested merge222d33310cb0d718a0b10f37e535ee389ee898e6,
      tree9eeeec067225de53d77af3b6929ffdf7c9f0de77, parentsec21ec04+d71.
      All13execution jobs check out that merge. Drawing blob01e2398309b3bd20cf47e5bcf12ee1765e5aa05e
      and capture producercb619e04b180748d2e4fb328946937e60469f25c match.
      Corrected tablet1 completes505selected=371PASS134SKIP with no failures
      or reported flakes. Whole browser4699selected=3699PASS999SKIP1FLAKY,
      zero final failures. The one retry-pass is unchanged drawing-before-pane-
      GET tool activation, not the repaired superseded-replay journey.
      Unit20424PASS50SKIP3TODO/1158filesPASS6SKIP; planner capture=true
      full-pr-proof and current-run records composition precede actual consumers.
      Required aggregate128567995931 confirms full native success. Earlier
      42414479074 remains FAILED; original trace proves recovery GET463.988ms
      after failed poll, not product loss. Local6PASS/0retry repair proof and
      original capture48contracts/5consumer proofs remain. Existing native
      lifecycle now reads queueMQE_lQDOTOzwKM8AAAABNksf384ABTs-zgPO_Eg,
      enqueued23:55:04, position1 AWAITING_CHECKS at00:02; MOG retained.
      No second enrollment. Correct old-unit timing: npmci15.907s, tsc78.478s,
      browser22.726s, capture650.299s, npmtest307.309s INCLUDINGVitest305.95.
      Do not misattribute307s to npmci or double-count Vitest.

      Terminal1344head78047d04b20dbd2bf0366ddf9252411e8a7cff4e,
      tickerblob2a927447d9b91fb8d993eb4a8de1baaee01b9604, has natural
      42422373914 SUCCESS19/19jobs58m03, tested mergebb428b35e9785f772332ed5044f49c39365a8066,
      tree1862faf372d15ba01aaedaba4152bcae6562aefa, parentsd839705+780.
      Browser4699selected=3698PASS999SKIP2FLAKY0finalFAIL;14invocations
      use one worker. Desktop1 remains57m28. Unit20424PASS50SKIP3TODO.
      Retry-passes are TabletK1keyboard accessibility andMobile symbol-wheel
      drawer detent, held1223surfaces; do not duplicate their repair.
      Prior full local proof21same identities/14PASS7sameSKIP0retry and
      actual navigation74to57 preserves78otherexpectations/policies/helpers.
      Local497.216to448.966s is one ordered sample, not native causal gain.
      Another assigned root already admitted the original PR: comment6714703797,
      MOG23:56:32, native23:56:34. Independent00:02readback confirms
      MQE_lQDOTOzwKM8AAAABNlX8rs4ABTs-zgPO_Sc position2 AWAITING_CHECKS.
      Preserve that entry, no re-enrollment/relabel or replacement carrier.

      Terminal unit/evidence import-barrier source phase is planned but UNEDITED.
      Operationci-lightning-terminal-unit-evidence-barrier-20261107-c2 requested
      ec21ec04; original acquire returned NOT_APPLIED REPOSITORY_SOURCE_UNAVAILABLE.
      One canonical census then succeeded55.91s, source existed at
      /Users/chriswong/Documents/Cluade/charting-app head ec1e45ec, no registered
      operation. One same-operation retry after that observed recovery returned
      the same NOT_APPLIED error. Stop unchanged diagnostics/acquire retries;
      this is a technical lane block, not permission denial or EFFECT_UNKNOWN.
      Next requires material canonical-source/binding recovery. Do not rehome.
      Planned exact3consumer files must be partitioned BEFORE Vitest import.
      Default discovery stays identical; explicit ordinary excludes3; evidence
      includes3 only after successful incumbent plan. Capture=true requires
      producer success/current records selector before import; only successful
      merge-group capture=false authorizes legacy17cases. Failed/malformed
      planning cannot become legacy. No second planner or receipt/traversal.
      Real import-barrier proof remains owed. Workflow activation overlaps held
      1223Node-discovery tail and is fenced; capture650s alone exceeds300s.

      This AgentOS carrier10841 previously published2127c6cf4d3908d8fbccb58a82eda9a3030259ac
      and native42425541269 SUCCESS with all required planner/contract/packs/
      gate jobs; its older bd04delivery comment is historical, not a new owner
      approval requirement. Source update stays on the original registered
      carrier. MOG is absent before this necessary note-only publication.
      Qualify the new exact head before ordinary ArmLast; no native Macro auto.
      Preserve every live controller lease and original uncertain effect.

      Other holds remain: H1run42394477066 missingATT1/processsettlement;
      Gateway6704040875/initializer-actuator cause; International42390957332
      whole-descendant settlement; Macro10674 originalC4PID26751/unbound
      publisher/installed-recovery interface; Terminal1223 uncertain createcommit
      tree8a95165da4779cbbee961f6fc903de02afd1e27f original effect. Closed
      bounded searches are not repeated. Prior protection/admin403s,2065comment
      denial and8094hold-release denial remain action-scoped. No old-author
      handback, denied replay/alternate publisher, extra Fabric root, generic
      kill/cleanup, Slack/email or daemon claim.

      Next: consume original queue outcomes2251/2256/1341/1344 and exact final
      Macro10764/10843 evidence at material boundaries; no idle polling or bulk
      arming. Publish current master architecture through a legitimate post-queue
      boundary. Continue full-only W4 execution-input analysis/adoption and
      Terminal import isolation only after actual carrier recovery and overlap
      gates. Reduce long indivisible tasks, preserve failures/coverage/journeys,
      then prove capacity and natural latency cohorts. Running CI alone is not
      durable autonomous execution.


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
  P3B-B is already merged through #6505 as
  4b9c9ece8593a2483997432e25f233bfe7af8779; do not repeat it.
  Continue W4 under #6351: exact input identity, complete execution closures,
  compatible full-default planning/execution and verified protected-consumer
  adoption before enrollment, then original-case parity and natural traffic.
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

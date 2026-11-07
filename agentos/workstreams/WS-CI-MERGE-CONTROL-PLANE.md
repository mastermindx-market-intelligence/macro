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
      Chairman recommissioned end-to-end acceleration on 2026-11-07. The mission
      remains all three repositories at lightning speed with truthful inputs, full
      selected coverage, original journeys and release authority preserved.
      Latest source-linked frontier: 2026-11-07 21:36 UTC. This supersedes the
      earlier current snapshots retained at69a46209 and the architecture commits;
      it does not erase their failed trials or unsettled effects.

      Compatible law pin66780ab7e3e9fdbfd40713bb5791fb1888529f7c remains usable.
      Complete66780-to-5abd delta15commits/131files and5abd-to-24263 delta3/14
      had no material law changes; new24263-to-0d68434 delta4/41 likewise has
      no AGENTS/sol_skills/law/workflow change. Existing Phase4 and this wave
      own acceleration; #6351 remains the incumbent pack-materialization owner.
      No new scheduler, queue, watcher, identity, retry or runtime authority.

      Master architecture remains original Mastermind PR2191 at
      https://github.com/mastermindx-market-intelligence/Mastermind/blob/c727c97c715f4916ef588e56c2f8b17993d53b6b/docs/CI_LIGHTNING_ARCHITECTURE.md.
      Its exact c727 native PR CI42409545529 passed. Native queue
      MQE_lQDOTotz3c8AAAABNdzYLM4ABAiKzgPOg34 was enqueued20:40:07,
      now position1/AWAITING_CHECKS; no merge is claimed and no rearm is owed.
      Document136c4e521af42919b9bab1c22e385550bbcffea2 and controlled-pair
      artifactd66a4328f204141b0abc55ec4eb4448d67d4f359 have exact readbacks.
      Targets remain p95docs90s/ordinary180s/full300s, interim full600s,
      with at least30 successive eligible observations per populated class.
      None is accepted. New measurements require the next document revision:
      three explicit Mastermind qualification lanes and12-job proof contract;
      Macro independent767s contract command and actual267s full checkout;
      Terminal capture698s and Vitest408s each need material reduction.

      Mastermind2065 original branch now publishes
      2b36c2877d9609ea398bbb75fe1d4aad4e49eb66,
      treea757f0a16b3ddc19719c2002993acd506d687c6a.
      It includes original ce38 plus protected24263 composition837d, followed
      by the six-file cold compiler repair. Pure capability helpers moved
      verbatim/AST-identically to existing executive_mcp_entry; updater
      imports/re-exports them, preserving both CLI bootstraps/security joins.
      Control Room canonical default-root resolution moved into its existing
      gather branch. Three fresh-child compiler cases and two root-selection
      regressions now pass. Whole qualification:801collected/800PASS/0fail/error,
      one unchanged actual-root credential skip. Direct -I -S -B updater CLI
      from unrelated private cwd returns expected usage64. No privilege change.
      Receipt:/tmp/ci-lightning-mm2065-cold-compile-repair-adjudication-receipt.json.
      Original commit/push APPLIED; exact PR body and source refs read back.

      ce38 required42410396607 failed in15m58; RWE42410396564 passed33m15.
      Both completed2358 unique modules and71571collected=invoked=finished
      cases with matching identity/count inventories;2357 outcome hashes agree,
      only cold os_gateway_publication differs. Not a controlled speedup.
      Six RWE environments/locks/plans/exit0/pipchecks were verified.
      Aggregate waited158s after its last shard and executed4s.
      All old d264 and9e36 trials are consumed; do not rerun them.

      Current2b36 full CI did not start: native PR is dirty against newer main,
      with only dynamic CodeQL42415930017 observed. Native ref/master is
      0d68434c37692507f9f1a77152c32b1e11bb4388; API PR base field still24263.
      Original workspace remains clean except preserved mastermind.egg-info/.
      Fetch and merge-tree diagnosis completed without HEAD/index/worktree edit:
      seven conflicts, tree983650d82cdffafc01f4e769fa445527cbadec33,
      receipt:/tmp/ci-lightning-mm2065-0d68434-merge-diagnostic.json.
      Accepted2224 introduces exact Broker quiescence and sparse-advice source
      successors; compose its actual-capture checks with both exact2065 observer
      histories. Do not select one old manifest hash or widen a guard.
      The derived combined107 manifest is28e4c5049a99f28cbb43459ad07e9b2b5bad8a28a3ff0228c15a84360fc16d1f;
      it differs from24263 only in observer/Broker/executor members.
      This is composition planning, not completed qualification or publication.

      Next2065 source phase, after that composition, splits existing qualification
      into explicit composition/Fabric/native jobs. Preserve the nine-step
      bootstrap, all original command objects, private native-root trap and
      375-case unittest prelude source closure. Workflow ci.yml, strict
      scripts/ci_parallel_shard.py and ci_postmerge_proof.py must advance
      together: six shards+three qualification jobs+scope+fast+test=12.
      Stable required test must require all3success on full and all3skipped on
      eligible fast routes; missing/canceled/unknown fails. Six contract owners,
      the pure initializer workflow-shape selector and two upload compatibility
      selectors qualify this change. Both H1 execution blocks remain unchanged.
      The prior800passes do not qualify the later DAG. No new worker pool.

      Macro10658 dc90e19d8b2764a8a5592cf5f2d0f15849403cb8 passed
      42408989367 in47m11:97of319 selected logical jobs,290/290 semantic
      proofsteps, no infrastructure findings. Actual testedmerge9842603411317571aa2ec81fb3eb9c05f17533cf,
      base35f6c48f361894d360505b7223260195bd073814,
      evidenceae341eae79e684145ff1afbb4a9082b6263cffd16d5fdb86feac55d290824d90.
      Pack0 took40m01;120-file FIF group33m40.853,4253pass/1skip.
      Existing MOG owner remains; no rearm, dispatch or speed-target claim.

      Macro10788 original source5e7a585fee0650ee53f6727b229322a9f015c5d6,
      tree12ee576b0d0ff04dd4479369f2816eb98dc3eac6, is now published APPLIED,
      not local-only. It composes the incumbent120-file fresh-interpreter helper
      with three siblings44/37/39 and preserves other390 catalog definitions.
      Corrected66 affected contracts pass with zero skips/failures after the
      earlier570pass/1closurefailure/2existing skips plus10subtests.
      Native42412023592 runs321/321 logical jobs,12packs; testedmerge
      1aadfe404d99f456a8adae2b0541541231f68b07,
      base74873cdaf3c8a3f305ddcac732975f815a7e87fa,
      plan26926098d468f3ed59b0cce9a5d8086f21131e394ad51830fa0d89b9ca05e3ab.
      At21:21 planner/contractdelta/packs2,3,11 passed, nine packs executing.
      All12 actual runner receipts are GitHub Actions/ubuntu-latest/direct.
      International full chain passed including IM14 browser10/10,0skip,70.078s.
      This new source-bound hosted proof does not settle old timed-out descendants.
      FIF3 aggregate completion and native final semantic closure remain owed.

      10788 completed pack3 checkout took267s:173.013s fetch plus93.552s
      full working-tree materialization,147038 paths. It already uses depth1,
      no filter/tags/LFS/submodules, and no checkout error/retry was observed.
      Pack0/1 checkout metadata reports22m11/15m42, internal attribution pending
      their terminal logs. Do not claim depth1 as new or infer network/CPU cause.
      Restore_workspace also restores full exact tree between logical jobs.
      #6351/W-SELFHOSTED-BRIDGE owns this permanent boundary, not productPRs.
      Current linked10803 source1c7ed6e4b8cc0f93c1f4e8697591cacde3c67192
      owns finite provided-actions history; its original686pass/3semanticUNKNOWN
      delivery gap remains. Do not duplicate that helper or reopen closedW3.
      A depth2 planner has an existing positive ancestry regression, but current
      workflow/test still pins full history; it is a distinct future owner slice.

      Macro8094 original carrier is now source-composed and published
      372935854f3ec3db858af6e655441937b5db7fc6 over acceptedbddf192c,
      treeba6652f0191e93740594106d5b143c37aacfaa45.
      Exactly2files+113/-2; authored runnercad2a724/tests000a0067 are unchanged.
      Full manifest validation precedes curated-only inference. Ordinary
      planning/otherfive census classes remain; unused ordinary exceptions are
      not promised equivalent. Natural42415102365 running; fences/authoritypass.
      Draft/unarmed, no long benchmark, local substitute, rerun or dispatch.
      Original benchmark/Fabric explicit refusals6596581286 stay fenced.
      Old42299098545 semantic3UNKNOWN6698103282 not retrocleared.
      Accepted shared code-owner blocks match10752qualified64807eeb and include
      10834commodity repair; retained data_gate assertions require their distinct
      data-health evidence and are not proved by a green code gate.
      Actual10658 contractdelta14m43 includes767.4s command, with closure band
      478/439s already head/base concurrent.8094 removes only part of that work.
      No measured live speedup; natural postmerge consumer still owed.

      Macro10752 head5e23be9cd4f73bfb298206ddd79886ef9d9e168e remains
      under its existing MOG enrollment. Full319/691 native42397007951 passed
      89m20; selected-consumer benefit remains owed. Earlier sweeps explicitly
      cap-deferred it; later42411350309 logs truncated deferred IDs, so no new
      per-PR classification is inferred. No cap change/manualrefresh/rearm.

      Terminal1338 MERGED20:05:38 as69c3893169a991b15fe7934b53122d55fd4eaaec,
      exact qualifiedtree69c7ae0e0a160fdb4401e0bbac8dda5a0701a3b3.
      Integrated42407566693 succeeded:6pass/2intentionaldedupskip.
      Unit21m37 includes capture11m38,Vitest408.45,20420pass/50skip/3todo.
      Prior full browser4693selected=3690pass/999skip/4flaky/0finalfailure.
      No reopen/rearm; production deployment and product acceptance are distinct.

      Terminal1341 new independent original source05a567b8b79df517ff1c6ff87e6247badad75e07
      reuses writeComposition's already complete validated return, removing one
      immediate redundant producer read. Only capture_ci_evidence.cjs and its
      test changed; writer/security/readers/workflow/held1223 surfaces untouched.
      48Node contracts pass. Actual local PL6capture24 andVIcapture30 complete;
      selected50 composition and all5 downstream Vitest consumer cases pass.
      Canonical compositionf2585e78e62d8985ca3496c028bfc33c2c8f1e153196768e66e0303e0f35a8e1.
      Read-only redundant traversal12.933s is one local observation, not hosted
      saving/p95. LocalNode26.5/M2 differs from hostedNode20/Linux.
      Native42414479074 running with no observed failure at21:28.
      MOGlabel+full-head nativeauto reconciled once21:28:13, no queueentry yet;
      do not reenroll. Persistent postwriter changes still fail downstream;
      producer-alone earlier mutation detection and atomicity are not claimed.
      Owned122 capture/generated files retained with byte inventory and archive
      508fff059b5960a8e2e52b4193d1095e05764a104bdeb994091749e02b605cd8,
      source workspace clean. Temporary EXDEV move failed before any file moved;
      verified copy+unlink completed on the same owned artifacts.

      Original holds remain: H1run42394477066 missingATT1/processsettlement,
      Gateway6704040875 and initializer/actuator cause; Macro International
      42390957332 unknown descendants; Macro10674 originalC4PID26751 binding
      unresolved after closed bounded search; Terminal1223 createcommit
      unknown tree8a95165da4779cbbee961f6fc903de02afd1e27f under original
      mastermind-queue-clearance-20261104-c1. No alternate carrier, lookup loop,
      generic kill/cleanup, originalheldworkspace access or reviewer replacement.
      Prior protection403s,Terminaladmin denial,2065comment denial stay scoped.
      Fabric roots consumed/blocked; recorded parent integration exception applies.
      Native agents provide C3 judgment only. Source/PR-body writes are permitted.
      No external messages, extra roots, backgroundrunner or daemon claim.

      MORE_WORK_EXISTS. Exact next work: compose0d security-source histories in
      original2065, run bounded complete owner proofs and publish once; implement
      and qualify three-lane/12-job DAG; consume current native1341/10788/8094
      results at meaningful milestones; let2191/10752 existing controllers work.
      Advance capture/Vitest/browser and Macro contract/materialization through
      their existing owners, prove whole critical paths under admitted capacity,
      then collect the natural cohort. All original journeys and failure behavior
      remain part of completion, not just green infrastructure.


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

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
      no five-minute p95 or completed production upgrade is claimed.
      This milestone supersedes the 21:36 current snapshot retained at528eb8e;
      historical failed trials and uncertain effects are not erased.

      Governing pin66780ab7e3e9fdbfd40713bb5791fb1888529f7c remains compatible.
      The latest complete20e17-to-f4f8ddc552866d2ab4bb2c7f229b0f2be283485c
      census covers10commits/32paths with no governing guide change. Macro
      AGENTS3d18585b and delivery guide220d23a9 are unchanged atabab066 versus
      ca9277. Existing Phase4/this wave and #6351 own the work; no new scheduler,
      queue, retry/identity owner, watcher or runtime authority is commissioned.
      Fabric roots remain exhausted/blocked; recorded attended-parent execution
      continues. Native children perform bounded C3 read-only judgment only.

      Master architecture2191 is protected-merged as
      accb4a6bcc1f721b93b10f43881cda67eca104ea. Follow-up2251 publishes
      fdb5c952344cfdda85223759b4ab7a7b2970e518 and has entered native merge queue.
      GitHub refused an update while queued; original ref remains exactlyfdb5.
      Latest prepared evidence revision is immutable commit
      57b19290fa53767a0a4e3f89e2a4907aa4c6e32f,
      docs/CI_LIGHTNING_ARCHITECTURE.md blob6d9c3e4277b32531ab5465fbc2dc92d110302eb5.
      That object is NOT attached to the queued branch or accepted into main.
      Preserve queue custody; reconcile its actual outcome before the next
      ordinary document continuation. Do not dequeue or bypass the queue guard.
      Targets remain docs p95<=90s, ordinary<=180s, full<=300s, interim full<=600s,
      over at least30 successive natural eligible observations per populated class.

      Mastermind2065 original branch publishes
      e6737ba03a254310e5eddb28dbe0839713b72694. Required42419148121 and
      RWE42419148128 both SUCCESS, testing exact merge
      9c73e295dc2f659db899d4d5dda11734994980c2,
      treee0363dfd2aa864d6719a79533f763df188749c20, parents20e17 plus e673.
      Both complete2374modules/72084collected=invoked=finished cases with
      identical per-module identity/outcome hashes, zero evidence errors,
      deselection or incomplete modules. Required24children return0 with valid
      completion; six RWE receipt ZIPs match published digests, exit0, match
      plan, pass pip-check and have no degraded entries. Native cold guard passes.
      Required exact12-job DAG: scopePASS, fastSKIP, sixpytestPASS,
      threequalificationPASS, aggregatePASS. Core/Fabric/native203/254/219s.
      Whole required25m05 versus RWE34m43 are different dependency profiles,
      not a controlled process-count speedup. Required limiting shard waits427s
      after scope then runs1048s; last-dependency-to-final-aggregate14s.
      Shard3's limiting child accumulates840.89s reported service; the accepted
      Trend split is not on that final child. Market-view fixture105.34s is
      the next safe attribution candidate, preserving all54cases/real calendars.
      Native correctness does not release H1/Gateway/initializer holds.
      Earlier local800/271/791/137 cohorts remain tied to their exact source;
      prior d264 and ce38 failures are retained, never relabeled or rerun by habit.

      Macro10764 now publishes original-carrier
      d39ef2f0fba5a620f1cf855c30ce3e78b193460a,
      tree45d62b686099b9297f3338d7db5d32e1632c7ef1, parents99c6f46e+ca9277.
      It fixes the nonexistent embedded-plan/nonproduction-mode reader using
      the real public semantic loader and complete jobs[].logical_job_id.
      Exact head/role/workflow/event, sealed-base provenance, cache isolation,
      clear-no-work versus empty-failure and quota deferral remain.
      All725complete controller/semantic/canary tests pass, including21actual
      schema boundary cases; all440other test/helper definitions are preserved.
      Natural42422937641 runs. ArmLast MOG was removed before the source push,
      merge-blocked retained; qualify new native proof/holds before rearming.
      Do not claim old Business data assertions passed; accepted10781 preserves
      their assertion bodies in the data gate.

      Macro10788 at5e7a585fee0650ee53f6727b229322a9f015c5d6 has complete
      native42412023592 SUCCESS in63m22:321jobs/694passedsteps, zeroinfra,
      evidencef83861a98d792b630016c986ad49df4c7fb1130dc5d956b525931598778c5dca.
      All120FIF modules execute once across44/37/39siblings:
      A1368PASS/629.906s; B1169PASS/820.212s; C1716PASS/1SKIP/765.374s.
      Exact module launches, not a collected-node parity claim.
      Keep unarmed until10764protected merge per existing6674602501/6682993935.
      New International10PASS does not settle its older timed-out descendants.
      Macro10658dc90 native42408989367 remains SUCCESS47m11,97jobs/290steps;
      Macro10752 prior319jobs/691steps succeeds89m20. Both retain existing MOG.
      No manual refresh, bulk rearm, cap change or speed-target claim.

      Macro8094 head372935854f3ec3db858af6e655441937b5db7fc6 now has
      native42415102365 SUCCESS:319jobs/692passedsteps, noUNKNOWN/inherited
      excuses/infra, authority_changed=true and clear. Testedmerge
      52fa11da6011ba3c91a25f884a43c7cc47cc5b42, base60dbeffbc7100752863572f4e426316cead7e3d6,
      evidence87f1dc6a6f32d9aeaa0ec82a45f399699bb0b0a0ca868279c89f5aeea925baa3.
      Current shared code journeys pass; historical3UNKNOWN and data-health
      assertions are not retrocleared. Current main changes CI catalog since
      the tested base, so the incumbent freshness owner still owes current proof.
      Automatic approval review REJECTED the attempted scoped source-release/
      merge-admission hold disposition, explicitly requiring user authorization.
      Canonical readback remains9comments with no release posted. Keep Draft,
      original6698103282hold and unarmed state. Do not rephrase, move the release
      into a body, switch carrier or mark Ready/arm to bypass the refusal.
      Long benchmark/Fabric denial6596581286 remains fenced; no replay/substitute.

      W4/#6351 first input-identity slice publishes Macro10843 at
      f0f9315f9d69d50f3635ae216c37afbbb1d3918d, parentabab066981e46860b1be51dcb05883aed1a6b5b0.
      Original operationci-lightning-macro-execution-input-identity-20261107-c2.
      Source81828c66126d34eef3cd5a85fd8b60cd6d106ae6/testd542cc9f8a5bc51027c1b6564f68449c61cd8f96.
      33focused contracts PASS, no skips/failures,10.824s; log
      72a762fcff7dd67d5e6b3ff23dd07c1b9bb3c28a48edfe5f8d8aa7c6259ca3a0.
      Every old source byte is preserved. This has no production caller and
      enrolls no job: it binds explicit path/mode/type/OID, exact commit/root tree
      and digest, with independent expected commit+path validation and no lazy
      acquisition/replacement overrides. Identity is NOT complete closure,
      materialized-blob availability, execution eligibility or speed proof.
      Future work: complete closure compiler, full-default producer/consumer
      compatibility, actual protected executor/control-bundle adoption, then
      earnings-economic-dossier enrollment with exact case/outcome/skip parity,
      cleanup and full independently pinned base replay. Candidate combined
      producer/consumer code alone cannot establish protected adoption.
      Preserve10803's finite history helper and holds;6505/P3B-B is already merged.

      Terminal1338 remains accepted as69c3893169a991b15fe7934b53122d55fd4eaaec.
      Original1341 native42414479074 unitPASS20424/50SKIP/3TODO,48Node contracts,
      1158filesPASS/6SKIP, records-mode PL6/VI/Options consumersPASS.
      Eleven browser jobs pass; tablet1fails one superseded-drawing fixture
      among505selected=370PASS/134SKIP/1FAIL. Verified artifact13592533058
      SHA038b94fd295a49eacb9d4ead012e32f26f1ce39620465521dd686c67c42f7ff6
      proves automatic recovery GET arrived463.988ms after poll failure.
      Original2GET/1PUT and expected Review state appear; later user choice had
      not run. No product-loss conclusion or causal runtime claim is inferred.

      Terminal1341 now publishes d71c569a64c5346419494afc3ca988bd06a56a73.
      Exact event handshakes replace the premature poll, preserving timeout,
      request counts, route failures and Review/cloud-count/Use-cloud/outbox path.
      Repaired+adjacent casesPASS6 across all3projects, zero retries/skips/failures;
      JSON3e36c252f18684fe8d872c05eab1bcb5b20a741f192937b729126533432c2253.
      Both capture blobs unchanged. New natural42422916742 runs. Existing
      nativeauto/MOG remains; no reenrollment or manual diagnostic-label clear.

      Terminal1344 publishes78047d04b20dbd2bf0366ddf9252411e8a7cff4e,
      tickerblob2a927447d9b91fb8d993eb4a8de1baaee01b9604.
      Full before/after browser proof matches21case/project identities,
      14PASS/seven identical expectedSKIP/zeroRETRY. All78otherexpectations,
      skip/timeout/appearance policies, helper bodies and test titles preserved.
      Actual network documents and navigation actions both prove74to57:
      matrix13to12, unavailable6to4, recovery15to12, grouped2to1, held2to1,
      editorial3to3, CN/HK33to24. Local497.216to448.966s is one ordered sample,
      not native causal speedup/p95. Comparison99e3785a198023464ac215779bb5a121fe9d20dd688a21d478152bf6feabae71.
      Natural42422373914 runs; original1344unarmed. Preserve1223held topology.
      Further unit partition must delay capture-dependent imports only on the
      capture=true route; legitimate planner-authorized merge-group legacy
      remains separate. Failed/unknown planning cannot become legacy success.

      Original holds remain: H1run42394477066 missingATT1/processsettlement;
      Gateway6704040875/initializer-actuator cause; International42390957332
      whole-descendant settlement; Macro10674 originalC4PID26751 unbound
      publisher/installed-recovery interface; Terminal1223 original createcommit
      tree8a95165da4779cbbee961f6fc903de02afd1e27f, unknown original effect.
      Closed bounded searches are not repeated. Prior protection/admin403s,
      #2065comment denial and now #8094hold-release denial stay scoped.
      No old-author handback, denied-action replay, alternate publisher,
      extra Fabric root, generic kill/cleanup, Slack/email or daemon claim.

      Next: consume current exact native10764/1341/1344/10843 results at material
      boundaries; complete original permitted delivery without bulk arming.
      Reconcile2251queue outcome and publish the retained evidence revision
      through a legitimate subsequent source boundary. Advance W4's complete
      closure/compatible consumer and Terminal unit/capture isolation; attribute
      the market-view fixture before a source change. Preserve all original
      journeys and failure behavior, then qualify total capacity and natural
      delivery cohorts. CI running alone is not durable autonomous execution.


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

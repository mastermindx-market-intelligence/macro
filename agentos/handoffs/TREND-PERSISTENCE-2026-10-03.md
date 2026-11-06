---
workstream: WS:TREND-PERSISTENCE
session: claude/trend-persistence-orchestration-430aef
model: fable
ended_because: complete
decisions: [DEC:TREND-PERSISTENCE-STOPS-AT-WAVE-B]
discoveries: [DSC:IC-GATES-AFTER-RANK-LINEAR-CONTROLS-DO-NOT-SEPARATE-PATH-FEATURES-FROM-VOLATILITY]
mission: >
  Lead the Mastermind Trend Persistence mission end to end: decide under pre-registration
  whether price-path shape features say anything about forward return or forward drawdown
  beyond momentum, volatility and beta, and build an advisory profile only if they do.
state_before: >
  Mastermind PR 1155 was a draft holding the path features and a first experiment whose
  forward-return test was null. No holdout had been read, no review had attacked the
  instrument, and there was no volatility benchmark and no walk-forward comparison.
changed:
  - path: "Mastermind brain/trend_persistence.py"
    what: The path features as pure functions with strict as-of slicing. Nothing in brain/ reads them.
  - path: "Mastermind research/trend_persistence_{substrate,panel,experiment,null,walkforward}.py"
    what: Universe and price substrate, panel and tests, V1/V2 experiments, the volatility-only simulated market, and the B2 walk-forward comparison with its pins and one-run guard.
  - path: "Mastermind research/TREND_PERSISTENCE_PREREG_{V1,V2,B2}.md"
    what: Three pre-registrations. V2 and B2 are pinned by hash in the code that runs them.
  - path: "Mastermind research/TREND_PERSISTENCE_READOUT.md"
    what: The full account - results, eight independent reviews with every finding and disposition, deviations, limits, and how to reproduce.
  - path: "Mastermind research/data/trend_persistence_*.json"
    what: Every result the readout quotes, the simulated reference, and the record of the one B2 run.
  - path: research/DO_NOT_REBUILD.md
    what: One kill row, DNR:KILL-TREND-PERSISTENCE-PATH-FEATURE-PROFILE, with the regenerated compiled blocklists.
verified:
  - claim: The B2 run returned the null on model value and the family stops at Wave B.
    command: "python3 -c \"import json;d=json.load(open('research/data/trend_persistence_b2_result.json'));print(d['decision'])\"  (Mastermind, at 1c5bc0c3a978)"
    result: "{'outcome': 'no_model_value', 'horizons': [], 'kind': {}, 'advances': False, 'family_stops_at_wave_b': True}"
  - claim: The committed result was produced once, under the pinned pre-registration, code and reference.
    command: "PYTHONPATH=.:vendor/macro_src python3 -m pytest tests/test_trend_persistence_panel.py tests/test_trend_persistence.py tests/test_trend_persistence_experiment.py tests/test_trend_persistence_null.py tests/test_trend_persistence_walkforward.py -q  (Mastermind)"
    result: 96 passed at head 7e836892, including test_the_committed_result_was_produced_once_under_the_pinned_files
  - claim: The write-up's numbers, gates and decision match the committed result.
    command: Seventh independent read-only review (Opus reviewer), recorded in the readout section 4
    result: PASS_WITH_FIXES - no number, gate or decision differed; wording findings applied in 703a9363
  - claim: The simulated reference was re-serialized after the run with every value unchanged, and the result and code hash are untouched.
    command: Eighth independent read-only review (Opus reviewer) of Mastermind commit 84ee9590, recorded in the readout section 4; the pin test re-minifies the committed file and compares its sha256 with the one the run recorded
    result: PASS_WITH_FIXES - 72,217 numbers compare exactly, re-minified bytes hash to e2caf7e8...20f3, code hash 5c976ce8...fca6 unchanged; one readout fix applied in 7e836892
  - claim: The Mastermind pull request is merged.
    command: "gh pr view 1155 --repo mastermindx-market-intelligence/Mastermind --json state,mergeCommit"
    result: "MERGED 2026-10-03T15:05:00Z through the merge queue, mergeCommit 1c5bc0c3a9784e0bf4d9fd67c59afd87f93e9920; all 24 paths byte-identical between the reviewed head 7e836892 and origin/master"
unverified:
  - claim: The merged commit is running in production.
    what_would_verify: "It is not deployed, on purpose. Production was at a0779abe (deployed 2026-09-24), 158 commits behind Mastermind master, when this merged; a deploy ships every program's unreleased changes and is a release owner's decision, and this change adds nothing that runs. After a deploy: /opt/mastermind/.deployed_git_sha equals the deployed master sha and /health returns 200."
unresolved:
  - The orchestration handoff issue named in the assignment was never found. Mastermind number 1157 is an unrelated Executive pull request and was not touched; the mission was run from PR 1155 and its thread.
  - There is no point-in-time sector history for former index members (the current map covers 3 of 1,083), so sector, size and group persistence were not attempted.
  - The B2 one-run guard in the code depends on a local file. The public attempt record on PR 1155 (comment 5969307706) is what makes the run single. To be fixed if the design is ever frozen again.
  - Mastermind issue 1188. The Executive identity-literal check judges JSON data files one line at a time - it flagged two counts in the one-line reference file, and it misses identity numbers in an indented file. Reported to its owner; the check was not changed from this seat.
next_actions:
  - None for this family. A reopening needs a new pre-registration, new constructions or group persistence, and formation dates after 2026-06-02.
do_not_redo:
  - Do not run the V2 holdout or the B2 walk-forward comparison on real data again. Each was run exactly once on 2026-10-03.
  - Do not score formation dates 2022-07-06 to 2026-06-02 for a third claim about these features.
  - Do not edit the V2 or B2 pre-registrations, the four pinned modules, or the committed result and attempt files, and do not change any value in the reference file. The reference was re-serialized once, values unchanged (readout section 7); its on-disk sha256 is 6225eabb...8d81 and its one-line sha256 is e2caf7e8...20f3, the one the run recorded.
  - Do not build a calibrated profile, shadow snapshot or advisory field from these 29 tests.
danger_areas:
  - Rebuilding the simulated reference with --out pointed at the committed file overwrites it with the one-line form, which no longer matches the pin and fails the repository identity check again. Rebuild to a scratch path and compare sha256 with e2caf7e8...20f3.
  - Deleting research/data/trend_persistence_b2_attempt.json or running from another checkout lets the B2 code run a second time with no trace.
  - The pin test fails if the pre-registration, the pinned code or the reference drifts from the committed result; a refactor of the four pinned modules will trip it by design.
  - The readout's "beyond simulated volatility" label on three distance-from-high tests is relative to two simulated markets and carries no promotion.
---

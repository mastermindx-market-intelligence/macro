---
workstream: WS:PROPHET-CONDITIONAL-FUSION
session: claude/ssd-prophet-w3-guardrail-20261002-5167b974f63e6828
model: local
ended_because: complete
mission: >
  Preserve HK/CA K6 shadow-store isolation while classifying the new
  read-only US W3 reader's unrelated field-name collisions, then publish
  the corrected existing DRAFT PR 8271. Source reader/helper/test blobs
  stay byte-identical to 783ba597. Draft PR only. No scientific read.
state_before: >
  Assigned workspace dirty with six owned files (reader, synthetic suite,
  validation helper extensions, per-stamp paired loader, scorecard primitive
  tests, exclusive gate:code job) on branch
  claude/ssd-prophet-w3-guardrail-20261002-5167b974f63e6828 at capture base
  dc4fd0766709188cba8d16a9fc16479c0e9c110f. Prior native Grok cleanup was
  normal; OCfree continuation timed out; PIDs 31360/31368 absent and lease
  released. Root 01a0fb5d-06e2-75e2-bb5c-6beadf0bec4e. Sol required one
  lexical-scan closure fix before gates: _assert_accrual_only must copy the
  payload without the free-text refusal field. Live sessions metadata snapshot
  (read-only, no outcomes): 36 sessions, 1 paired_accrued, 23 unmatured,
  12 degraded, latest 2026-09-30 — 1/20, not ready.
changed:
  - path: scripts/report_us_prophet_w3_guardrail.py
    what: >
      Already-built read-only W3 guardrail reader. This continuation's only
      production-source repair is _assert_accrual_only: serialize a copy of the
      payload without the free-text refusal field so a non-numeric diagnostic
      such as "HAC estimator undefined on the ΔIC series" returns REFUSED
      instead of an uncaught second GuardrailReadError. Structured
      comparison-bearing fields remain scanned. No exception-hierarchy or
      statistic-math change.
  - path: tests/test_us_prophet_w3_guardrail.py
    what: >
      Synthetic suite plus one new regression: lawful synthetic-20 fixture,
      inject GuardrailReadError from hac_t_interval, assert returned REFUSED
      (not uncaught), no primary/secondary/per_stamp stats, investigation
      closed. Accrual-only helper now inspects a copy without refusal.
  - path: engine/validation.py
    what: >
      Backward-compatible rank_ic min_names keyword (default 10) and
      newey_west_tstat unrounded keyword (default False). Existing callers
      keep historical bytes.
  - path: engine/us_prophet_w3.py
    what: >
      Narrow public load_paired_stamp. Capture and status semantics unchanged.
  - path: tests/test_scorecard_primitives.py
    what: >
      Byte-compatibility tests for rank_ic min_names and newey_west unrounded
      defaults.
  - path: .github/ci/legacy-jobs.yml
    what: >
      Exclusive gate:code job prophet-w3-guardrail, now 50 declared paths:
      reader plus scorecard primitive tests plus the four site/ literal
      dependencies the hosted contract-delta job named on 2026-10-02
      (site/basketdata/fear_greed.json, site/factordata/basket_washout_state.json,
      site/factordata/stock_personality.json, site/factordata/us_standouts.json).
      Capture/status owner stays on its existing data-gated job.
  - path: research/prophet_fusion/W3_GUARDRAIL_READER.md
    what: >
      Operator-facing reader contract: required --root, stdout JSON/no writes,
      FLOOR_UNMET exit 0 vs REFUSED exit 2, first-load session metadata only,
      N=20, frozen SPY capture, primary HAC-t, secondary cannot OR/cancel,
      unique ordinal ranks, software release separate from scientific read,
      1/20 snapshot, cold-resume next steps.
  - path: agentos/handoffs/PROPHET-CONDITIONAL-FUSION-2026-10-02-GUARDRAIL.md
    what: "This cold-resume handoff for the source-delivery wave, updated for the K6 reviewed-US-field classification and mutation."
  - path: tests/test_board_shadow.py
    what: >
      Third K6 map _K6_REVIEWED_UNRELATED_US_FIELD_FILES classifying only
      scripts/report_us_prophet_w3_guardrail.py onto prefixed_identifier
      (US persisted keys prophet_shadow_definition/score/score_rank; no
      engine.board_shadow import; no HK/CA data/prophet_shadow read). Merged
      into _K6_ALL_ALLOWLISTED_FILES. Not filed in the pre-existing map or
      _K6_REVIEWED_READER_FILES. One mutation: declared forms accept
      frame["prophet_shadow_score_rank"] and reject
      pd.read_parquet(config.data_dir() / "prophet_shadow" / "hk_lane_a.parquet")
      via _k6_unclassified_occurrences.
verified:
  - claim: "HISTORICAL source-delivery receipt, predating this K6 classification: required pytest suites pass at 112 after the HAC-undefined regression. Not re-run for the K6 fence or the four-path CI repair."
    command: "python3 -m pytest tests/test_us_prophet_w3_guardrail.py tests/test_scorecard_primitives.py tests/test_us_prophet_w3.py tests/test_validation.py -q"
    result: "112 passed, 4 warnings in 22.65s; PYTEST_RC=0"
  - claim: "Working tree has no whitespace errors on the owned diff (K6 classification wave)"
    command: "git diff --check"
    result: "DIFFCHECK_RC=0; empty stdout"
  - claim: "legacy-jobs.yml loads as a valid exclusive-aware pack manifest"
    command: "python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --validate-only"
    result: "Validated 241 legacy jobs; VALIDATE_ONLY_RC=0"
  - claim: "HISTORICAL receipt, predating the 2026-10-02 four-dependency repair: at source-delivery time the local narrow gate read prophet-w3-guardrail as a 46-path exclusive gate:code job with no closure misses (sparse local inference; site/ excluded — re-running this command now prints 50)"
    command: "python3 -c 'from pathlib import Path; from scripts.run_ci_pack import inferred_as_if_not_exclusive, curated_exclusive_closure_findings, load_legacy_jobs; m=Path(\".github/ci/legacy-jobs.yml\"); j={x.job_id:x for x in load_legacy_jobs(m)}[\"prophet-w3-guardrail\"]; f=curated_exclusive_closure_findings(m); print(j.gate, j.exclusive, len(j.paths), f.get(\"prophet-w3-guardrail\", ()))'"
    result: "code True 46 (); n_misses=0; inferred_n_paths=46; FINDINGS_FOR_JOB_OK True"
  - claim: "After the four-dependency repair the manifest declares 50 sorted paths; gate:code, exclusive=True, curated_exclusive_closure_findings empty on this tree"
    command: "python3 -c 'from pathlib import Path; from scripts.run_ci_pack import curated_exclusive_closure_findings, load_legacy_jobs; m=Path(\".github/ci/legacy-jobs.yml\"); j={x.job_id:x for x in load_legacy_jobs(m)}[\"prophet-w3-guardrail\"]; print(j.gate, j.exclusive, len(j.paths), j.paths==tuple(sorted(j.paths)), curated_exclusive_closure_findings(m).get(\"prophet-w3-guardrail\", ()))'"
    result: "code True 50 True (); local inferred closure still cannot see site/ (this tree is sparse — missing dirs data, mockups, site, verify_shots), so local 46 vs declared 50 is a superset disclosure, not full hosted parity"
  - claim: "AgentOS store including this handoff is schema-valid after the K6 classification edit"
    command: "python3 scripts/agentos.py validate"
    result: "1430 records (76 workstreams, 384 decisions, 419 discoveries, 551 handoffs) — 0 error(s), 117 warning(s); AGENTOS_RC=0"
  - claim: "board-shadow K6 fence plus mutation: 65 passed (hosted pack9 was 1 failed / 63 passed = 64 tests; this wave adds one mutation)"
    command: "python3 -m pytest tests/test_board_shadow.py -q"
    result: "65 passed in 4.08s; PYTEST_RC=0"
  - claim: "prophet-w3-guardrail exclusive closure empty; 50 declared sorted paths, gate:code, exclusive=True. Local on-disk presence is 46 because sparse omits site/ (the four declared site literals are index blobs, not checked out)."
    command: "python3 -c 'from pathlib import Path; from scripts.run_ci_pack import curated_exclusive_closure_findings, load_legacy_jobs; m=Path(\".github/ci/legacy-jobs.yml\"); j={x.job_id:x for x in load_legacy_jobs(m)}[\"prophet-w3-guardrail\"]; present=sum(1 for p in j.paths if Path(p).exists()); print(j.gate, j.exclusive, len(j.paths), j.paths==tuple(sorted(j.paths)), present, curated_exclusive_closure_findings(m).get(\"prophet-w3-guardrail\", ()))'"
    result: "code True 50 True 46 (); CLOSURE_MISSES=(); ON_DISK=46; DECLARED=50"
  - claim: "board-shadow-substrate stays unscoped (0 declared paths, exclusive=False); inferred closure already includes scripts/report_us_prophet_w3_guardrail.py so the job was not widened."
    command: "python3 -c 'from pathlib import Path; from scripts.run_ci_pack import curated_exclusive_closure_findings, inferred_as_if_not_exclusive, load_legacy_jobs; m=Path(\".github/ci/legacy-jobs.yml\"); j={x.job_id:x for x in load_legacy_jobs(m)}[\"board-shadow-substrate\"]; inf=inferred_as_if_not_exclusive(m)[\"board-shadow-substrate\"]; print(j.gate, j.exclusive, len(j.paths), \"scripts/report_us_prophet_w3_guardrail.py\" in inf.paths, curated_exclusive_closure_findings(m).get(\"board-shadow-substrate\", ()))'"
    result: "code False 0 True (); unscoped always-on; report file already in inferred closure; no path widen"
  - claim: "Six reader/helper/code blobs remain byte-identical to 783ba597"
    command: "for f in scripts/report_us_prophet_w3_guardrail.py tests/test_us_prophet_w3_guardrail.py engine/validation.py engine/us_prophet_w3.py tests/test_scorecard_primitives.py research/prophet_fusion/W3_GUARDRAIL_READER.md; do echo $f $(git rev-parse 783ba597:$f) $(git hash-object $f); done"
    result: "all six hashes match 783ba597 (618dff5b / 0175da89 / 6e57ee4b / edbbbc90 / 592b5457 / b36161de)"
unverified:
  - claim: "Independent root review of these exact persisted source bytes"
    what_would_verify: "Root 01a0fb5d-06e2-75e2-bb5c-6beadf0bec4e reviews the draft PR head after this return. Not performed in this session."
  - claim: "Required GitHub Actions exclusive job prophet-w3-guardrail and unscoped board-shadow-substrate conclude green on the draft PR after this K6 classification push"
    what_would_verify: "Hosted rerun of those two jobs on the new head. First pack9 at f598728d failed only tests/test_board_shadow.py::test_k6_prophet_shadow_literal_is_confined_to_its_own_module_and_tests with offender scripts/report_us_prophet_w3_guardrail.py. Not waited in this session."
unresolved:
  - "Live sessions metadata is 1 matured paired_accrued of 20 required. No lawful comparison read exists."
  - "Held PRs #8091 / #8192 / #8240 and H1 incumbents remain held. Existing owners handle integration. This wave did not touch them."
  - "Independent root review of source is pending after this return."
  - "Hosted rerun of prophet-w3-guardrail and board-shadow-substrate is pending on the K6-classified head."
next_actions:
  - "Independent code review of the owned paths on this branch, including the K6 third-map classification."
  - "Hosted rerun pending: prophet-w3-guardrail (50 declared paths) and board-shadow-substrate (unscoped K6 fence, now 65 tests). First pack9 failed only the K6 literal confinement test on scripts/report_us_prophet_w3_guardrail.py. Native local on-disk presence of the exclusive job is 46 of 50 because this tree is sparse and excludes site/; declared 50 includes the four site literals. Do not claim hosted parity until those jobs conclude."
  - "Source-only release of the reader. Do not treat software release as a scientific read."
  - "Wait for 20 distinct matured H=10 paired sessions in sessions metadata before any lawful comparison read."
  - "Existing owners handle held H1 integration. Do not take that ownership from this wave."
do_not_redo:
  - "Do not restart the W3 guardrail reader implementation. The six dirty files plus this closure repair are the source. The six reader/helper/code blobs stay byte-identical to 783ba597."
  - "Do not re-file scripts/report_us_prophet_w3_guardrail.py into _K6_PREEXISTING_UNRELATED_FILES or _K6_REVIEWED_READER_FILES. It is a reviewed US field-name collision on prefixed_identifier only."
  - "Do not reconstruct candidate or grade writer calls. Exact persisted source and benchmark; grain fingerprint bound to BOTH live and session paired fingerprints."
  - "Do not change exception hierarchy or HAC / rank-IC / Student-t math."
  - "Do not invent a raw-score tie policy. Production rankers assign unique ordinal ranks after (stage_rank, -score, ticker)."
  - "Do not read production paired/candidate/grade outcomes from this source-delivery wave."
  - "Do not change held PRs #8091 / #8192 / #8240. H1 incumbents remain held."
  - "Do not mint a new DEC, invent WS strategy or priority, or create a control plane / blanket permission."
  - "Do not mark-ready, auto-merge, merge, or deploy this draft PR. Root reviews source after return."
  - "Do not treat capture base dc4fd0766709188cba8d16a9fc16479c0e9c110f or status SHA 53ab89afd507734189dd3dc2639e4377da11873e7b37165d490c602e7297a34d as current authority; they are snapshots."
  - "Do not count 1/20 metadata as a winner, promotion, fit, C2 trigger, reversion, or AgentOS automated write."
danger_areas:
  - "Scanning JSON including the free-text refusal field re-raises on lawful non-numeric diagnostics that name HAC or ΔIC. Keep the copy-without-refusal scan."
  - "Below N=20 the comparison surface must stay sealed. First call is sessions_by_stamp; loaders run only after the floor."
  - "A sparse tree must not run the full pytest suite. Use the named files and the exclusive job."
  - "Chairman share https://chatgpt.com/s/t_6abf52c40940819186605acc3689fc54 is assignment context, not a runtime or source grant."
  - "Software release of this reader is not permission to print a C1-vs-shadow comparison against live outcomes."
---

## §0 State — what is true right now

The W3 post-floor statistical guardrail reader remains source-delivered on
branch `claude/ssd-prophet-w3-guardrail-20261002-5167b974f63e6828`. The six
reader/helper/code blobs
(`scripts/report_us_prophet_w3_guardrail.py`,
`tests/test_us_prophet_w3_guardrail.py`, `engine/validation.py`,
`engine/us_prophet_w3.py`, `tests/test_scorecard_primitives.py`,
`research/prophet_fusion/W3_GUARDRAIL_READER.md`) are byte-identical to
`783ba597`. This wave did not edit reader or statistics.

Hosted first pack9 at `f598728d` failed only
`tests/test_board_shadow.py::test_k6_prophet_shadow_literal_is_confined_to_its_own_module_and_tests`
with offender `scripts/report_us_prophet_w3_guardrail.py` (1 failed, 63
passed = 64 tests then). Independent Astra review: every occurrence in that
file is a US persisted key `prophet_shadow_definition` /
`prophet_shadow_score` / `prophet_shadow_score_rank`, matching existing
`prefixed_identifier`. The file does not import `engine.board_shadow` and
does not read HK/CA `data/prophet_shadow` storage. Classification is a new
third map `_K6_REVIEWED_UNRELATED_US_FIELD_FILES` merged into
`_K6_ALL_ALLOWLISTED_FILES`, plus one mutation that accepts
`frame["prophet_shadow_score_rank"]` and rejects
`pd.read_parquet(config.data_dir() / "prophet_shadow" / "hk_lane_a.parquet")`.
Local board-shadow gate: 65 passed in 4.08s.

HISTORICAL source-delivery receipt stays 112 passed (not re-run). `git diff
--check` 0; legacy-jobs validate-only 0. Exclusive job
`prophet-w3-guardrail` declares 50 sorted paths, gate:code, exclusive, 0
closure misses. Local on-disk presence is 46 of those 50 because this
worktree is sparse and excludes `site/` (missing dirs: data, mockups, site,
verify_shots). The four declared site literals —
`site/basketdata/fear_greed.json`, `site/factordata/basket_washout_state.json`,
`site/factordata/stock_personality.json`, `site/factordata/us_standouts.json`
— are index blobs, not checked out. `board-shadow-substrate` stays unscoped
(always-on); inferred closure already includes the report file, so that job
was not widened. Hosted rerun of both jobs is pending. Live metadata remains
1 of 20 matured H=10 paired sessions. Independent root review is pending.
This is not a scientific read and not a merge.

## §1 What is LEFT — in order

1. Independent root review of the exact persisted source on the draft PR.
2. Hosted rerun of exclusive job `prophet-w3-guardrail` and unscoped
   `board-shadow-substrate` on the K6-classified head. Source-only release
   after review; do not merge or deploy from this wave.
3. Accrue sessions metadata to 20 distinct matured H=10 paired sessions
   before any lawful comparison read.
4. Existing owners handle held H1 integration (`#8091` / `#8192` / `#8240`).

## §2 What will bite you

If `_assert_accrual_only` serializes `refusal`, a `GuardrailReadError` whose
message names `HAC` or `ΔIC` is caught, stuffed into `refusal`, then raised
again as an uncaught error. The regression
`test_hac_undefined_from_interval_returns_refused_not_uncaught` pins that.
Do not "fix" it by stripping statistics from refusal prose or by changing
the exception hierarchy.

`--root` has no live default. Running the CLI against the production tree
before N=20 must remain `FLOOR_UNMET` exit 0 with no stats. A `REFUSED`
payload is exit 2.

Inclusive-of-cutoff top-30 is a published-rank rule. Equal raw scores already
receive unique ordinal ranks in production. Adding a raw-score tie policy
here would be a new ranking law.

## §3 What was decided and found

No new `DEC` or `DSC` minted. Binding law remains
`research/prophet_fusion/W3_RACE_PREREG.md` plus
`DEC:PROPHET-FUSION-IS-THE-CANONICAL-US-RANKER`,
`DEC:PROPHET-SHADOW-GRAIN-IS-A-PAIRED-ROW`,
`DEC:W3-FIRST-DURABLE-COMPLETE-OBSERVATION-WINS`,
`DEC:W3-PROSPECTIVE-SAMPLE-IGNORES-GENERIC-BACKFILL`.
Sol required the refusal-field lexical exclusion as the sole in-scope
output-closure fix; core current source hashes were reviewed by Sol before
that repair.

## §4 Not in scope — do not adopt

No outcome read. No winner, promotion, fit, C2, reversion, or AgentOS
automated write. No strategy rewrite. No ownership transfer of H1
incumbents. No new checkout, child delegation, direct provider, main push,
or production action. No reconstructed candidate/grade writer. Capture base
and earlier status SHA are snapshots, not current authority.

---
workstream: WS:PROPHET-CONDITIONAL-FUSION
session: claude/ssd-prophet-w3-guardrail-20261002-5167b974f63e6828
model: local
ended_because: complete
mission: >
  Complete documented SOURCE delivery of the already-built W3 post-floor
  statistical guardrail reader from the existing custody workspace. One
  in-scope output-closure repair plus two required documents. Draft PR only.
  Independent root review follows this return. No scientific read.
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
    what: "This cold-resume handoff for the source-delivery wave."
verified:
  - claim: "Required pytest suites pass at 112 after the HAC-undefined regression"
    command: "python3 -m pytest tests/test_us_prophet_w3_guardrail.py tests/test_scorecard_primitives.py tests/test_us_prophet_w3.py tests/test_validation.py -q"
    result: "112 passed, 4 warnings in 22.65s; PYTEST_RC=0"
  - claim: "Working tree has no whitespace errors on the owned diff"
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
  - claim: "AgentOS store including this handoff is schema-valid"
    command: "python3 scripts/agentos.py validate"
    result: "1430 records (76 workstreams, 384 decisions, 419 discoveries, 551 handoffs) — 0 error(s), 117 warning(s); AGENTOS_RC=0"
unverified:
  - claim: "Independent root review of these exact persisted source bytes"
    what_would_verify: "Root 01a0fb5d-06e2-75e2-bb5c-6beadf0bec4e reviews the draft PR head after this return. Not performed in this session."
  - claim: "Required GitHub Actions exclusive job concludes green on the draft PR"
    what_would_verify: "Watch the prophet-w3-guardrail check on the draft PR after push. Not waited in this session."
unresolved:
  - "Live sessions metadata is 1 matured paired_accrued of 20 required. No lawful comparison read exists."
  - "Held PRs #8091 / #8192 / #8240 and H1 incumbents remain held. Existing owners handle integration. This wave did not touch them."
  - "Independent root review of source is pending after this return."
next_actions:
  - "Independent code review of the eight owned paths on this branch; required exclusive CI job prophet-w3-guardrail."
  - "Hosted contract-delta rerun pending on the 50-path manifest. Its first run failed on four missing literal dependencies; the repair declares them. Native local initial inference read 46 because this tree is sparse and excludes site/, so local 46 is an incomplete inference under a declared-50 superset, not host parity — do not report local 50 and do not claim full hosted parity until the hosted job concludes."
  - "Source-only release of the reader. Do not treat software release as a scientific read."
  - "Wait for 20 distinct matured H=10 paired sessions in sessions metadata before any lawful comparison read."
  - "Existing owners handle held H1 integration. Do not take that ownership from this wave."
do_not_redo:
  - "Do not restart the W3 guardrail reader implementation. The six dirty files plus this closure repair are the source."
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

The W3 post-floor statistical guardrail reader is source-delivered from the
existing custody workspace on branch
`claude/ssd-prophet-w3-guardrail-20261002-5167b974f63e6828`. The only new
production-source edit in this continuation is the lexical accrual-only scan
excluding the free-text `refusal` field. Required local gates on this tree:
112 passed (source-delivery receipt; the suites were not re-run for the
manifest-only repair below); `git diff --check` 0; legacy-jobs validate-only
0; exclusive job `prophet-w3-guardrail` now declares 50 sorted paths with
gate:code, exclusive, and 0 closure misses under the local narrow gate.

Why 46 became 50: the native local initial inference read 46 declared paths
because this worktree is sparse and excludes `site/` (missing dirs: data,
mockups, site, verify_shots), so the four literal dependencies that live
under `site/` were invisible to it. The hosted contract-delta job (full
checkout) named exactly four missing literal dependencies —
`site/basketdata/fear_greed.json`, `site/factordata/basket_washout_state.json`,
`site/factordata/stock_personality.json`, `site/factordata/us_standouts.json`
— and this repair declares them in sorted order. Local inference therefore
still cannot reproduce the hosted walk (46 locally vs 50 declared, a
superset disclosure); hosted contract-delta rerun on the 50-path manifest is
pending and is the parity check. Live metadata remains 1 of
20 matured H=10 paired sessions. Independent root review is pending. This is
not a scientific read and not a merge.

## §1 What is LEFT — in order

1. Independent root review of the exact persisted source on the draft PR.
2. Required exclusive CI job `prophet-w3-guardrail` on that PR. Source-only
   release after review; do not merge or deploy from this wave.
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

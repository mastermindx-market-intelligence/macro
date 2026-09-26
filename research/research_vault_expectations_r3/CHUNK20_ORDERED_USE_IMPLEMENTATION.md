# Research Vault — R20: an implemented ordered-activation consumer

**17 September 2026. Parent institutional-intelligence upgrade: SPEC_ONLY. Measurement leaf: BUILT_NOT_PROVEN in draft PR #7258.** This phase changes the existing reporting script and its existing tests, rather than adding another standalone research implementation. It does not prove actual use, revenue, source rights or the real Brain journey.

## Outcome and scope

Before: independent event-stage counts could imply progression even when different sessions supplied the stages or events occurred in reverse order. R19 characterized this boundary.

After: the existing CLI has an explicit --ordered report that shows supported ordered prefixes alongside independent activity, preserving the original default JSON and Markdown. An operator can distinguish these measures using permitted recorded data. No real Supabase rows were obtained here.

Existing owner: Commercial Activation, source records #6835@babe056724ef17f555ebbb773f3d4908d8203668. Its CA1A implementation #6838 is merged; the records' old TODO projection is not implementation truth. The records branch was not edited. Bounded open-PR searches found no other exact-script implementation, not a universal collision-free census.

Implementation carrier: #7258, sol/activation-ordered-funnel-r20-20260917, commit9872bbe611a3a2ce532f03e28ab15735371f38ef, tree803fc3cb4e46b220bcee555781bd0772a691fbb4, parent983625f5336ad6d6a581cbfe1e81536166deadc1. Exactly scripts/activation_funnel_report.py and tests/test_activation_funnel_report.py changed. Readback confirms script blobd6194e95b5cf3e6f03f1a32e01c4a791e0010065 and test blobb0fae0b37dcfd528afa8a42b2d316cfa93b54783 match tested local bytes. Open/Draft/unmerged; later mergeable=true is not review/CI/release acceptance.

No new event collector, schema, database, credentials, identity resolution, analytics service, network read path, customer UI, CI policy, financial calculator or source owner. Brain and Research Vault runtime code are unchanged. This report is continuity on #7182; it does not duplicate #7258's source files.

## Selected metric contract

`--ordered` emits activation_funnel_report.ordered.v2. Default v1 remains unchanged, including its historical interpretation limits; no existing dashboard is silently switched.

The same ingestion-time cutoff and bot/internal exclusions apply first. Report unit is the recorded(site,session_id), not a person or stitched cross-device visit. Equal session strings on different sites and equal visitors across different sessions do not join. Missing session IDs do not create a shared bucket. Visit means presence of any admitted record with a valid session, not a verified separate visit event.

Action order: intelligence.viewed -> personal.act -> watchlist.saved. Explicit-timezone client_ts supplies the clock; missing/invalid/naive timestamps remain activity only, never arrival-time substitution. Client clocks are not independently verified. Stage times must strictly increase. Same-time stages cannot advance multiple steps, and UUID/list order is not occurrence evidence. Later repeated actions can complete a valid subsequence after an earlier out-of-order attempt. Repeated records do not inflate session counts.

Saved-stage count must be an actual integer>=3 in the opt-in mode, not coerced bool/float/string. Legacy input handling remains unchanged. Occurrence after until is activity-only with a diagnostic; an older occurrence received within the ingestion window remains older rather than being called new conversion. This is admitted-record coverage, not a full occurrence cohort or late-arrival reconstruction.

The report includes independent activity, ordered prefixes, nested ratios, null missing denominators, timing/count/session diagnostics and the actual measurement definitions. It describes missing observed next steps, not permanent churn. Raw session/user/visitor/path values are not projected and source rows are not mutated. No causal, paid or retention claim.

## Actual user-machine demonstration

The existing CLI processed six fictional sessions: forward, reverse, equal-time, view-only, action/save-only and unqualified action time. Legacy stage totals6/5/5/5 yield action/view1.0; ordered totals6/5/1/1 yield0.2. This is a synthetic distinction, NOT a measured100%-to20% customer conversion decline. Tied and missing clocks are unsupported order, not proof a human failed to act.

The actual generated JSON and Markdown display both counts and limitations. A downstream chart must not hide the unit/time/coverage qualifications or call this revenue conversion.

## Executed verification

Full baseline script/test content was recovered via connector and Git-blob verified locally:86801a212365f8f21e4b0ab24ea336709e74983b /51b2148d667c7bc3d253206f3bee158bc6a107f4. A network copy failed DNS; exact connector bytes are the qualified input, not a partial transcription.

- Original8 tests passed.
- Four new real-CLI requirements failed before --ordered existed.
- Final41 passed, zero failures/errors/skips:8 retained +33 new tests in the existing suite.
- One oracle test compares150 generated event sets against independent exhaustive subsequence enumeration. Not150 additional user/model evaluations.
-200 generated datasets preserve default v1 JSON AND Markdown byte-for-byte against the exact baseline.
- Six direct local deliberate regressions rejected: cross-site joining, tied-stage advancement, reverse ordering, arrival fallback, future-clock admission and saved-count coercion. Not independent external review or extra tests in41.
- Final local receipt2026-09-17T08:55:20.018055+00:00, Python3.13.5. External pytest plugin autoload disabled; whole-repository/hosted CI not run.

An initial full-subprocess mutation challenge timed out without a final result; no pass is claimed for it. The completed bounded direct challenge is separately retained. One uploaded-script blank-line difference was isolated, local bytes aligned, and the full41-case suite/direct review rerun afterward. Source readback matches those final bytes.

A fresh extracted delivery package reproduced41 passes,200 compatibility comparisons,six rejected mutations,and byte-identical ordered example JSON/Markdown. This is replay of the same tests, not another independent sample. Original archive CRC and all20 content-manifest hashes passed before replay. The package includes exact complete code/tests, baseline, successful direct harness, receipts and fictional inputs, not private data or institutional originals.

## Business interpretation and first-party access

Use the existing owners to keep supported answer completion, recorded progression, return use and commercial outcomes distinct. An answer-delivered event is not correctness; a citation click is inspection behavior, not necessary proof of value; progression is not retention or causality. Convenient intelligence may help users without making them open every source, but evidence must remain inspectable and sound.

The acquisition pilot still freezes questions and windows, crosses baseline/expanded corpus with existing/improved processing, and separates acquisition/extraction/discovery/support/interpretation/access gaps. This code makes the behavioral measurement less misleading. It does not measure the marginal usefulness of another MarketDesk subscription.

Supabase remains unconnected. No event rows, auth service, credentials or private histories were read; no manual setup workaround. No new source licence, customer count, current price, margin or ROI was established. No account, vendor message, market-data download, model/provider call, Job/worker/watch, native host call, CI dispatch, merge or deployment.

## Owner delivery and next action

Review material delivered to existing Commercial Activation PR#6835, comment5711784778, identifies #7258 and the metric/acceptance limits. Delivery is not acknowledgment, assignment or accepted architecture.

Existing analytics owner reviews/adopts the opt-in contract after applicable current-head/current-base checks. Then one authorized fixed-window real-data report must establish actual schema, filters, timestamp coverage and scoped results. Do not execute the inherited Supabase service-role reader merely because its code exists. Default v1 consumers remain untouched until explicit adoption.

Parent first-source journey remains existing Brain -> single-debit reader -> useful answer -> matching original inspection. R14 review, R16 qualification and R17 code-publication holds remain; none was retried or imported here. #7045's merged hygiene and #6838's event spine are do-not-redo. Current #7079 adoption has no new acknowledgment in the bounded read.

## Procedure and continuity

Protected Mastermind@b14982837cc8146e3dc49e5862558ee399a1aa3d; compatible1.0.1/bootstrap1; INDEX/COLD_START/ACTIVE_EXECUTION/WEB_CEO_DELEGATION/CLOSEOUT loaded at one pin. Live Chairman continuation supplies bounded intent, not a runtime or source-use waiver. Direct reasons PRINCIPAL_JUDGMENT/LOWER_TOTAL_OVERHEAD. Operation commercial-activation-ordered-report-20260917-sol-001 is a source-carrier label, not an invented Executive Job.

Parent research carrier begins d0ff4bb42d2085448fcff5968b3569609570dcf6 on #7182. New code lives ONLY on #7258. The compact canonical report differs from expanded conversation REPORT.md; no identical-serialization claim. Receipt r20/verification_r20.json and existing Agent OS handoff preserve the precise next action.

Primary next step: review/adopt #7258 and obtain one permitted fixed-window report after connection. Independent parent path: resolve the already-recorded Brain/source adoption decision and real-source proof. Do not substitute another synthetic example for either gate.

Sources: https://github.com/mastermindx-market-intelligence/macro/pull/7258 ; https://github.com/mastermindx-market-intelligence/macro/pull/6835 ; https://github.com/mastermindx-market-intelligence/macro/pull/6838 ; https://github.com/mastermindx-market-intelligence/macro/pull/7182 .

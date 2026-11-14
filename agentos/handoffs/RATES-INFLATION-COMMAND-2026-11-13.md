---
workstream: WS:RATES-INFLATION-COMMAND
session: sol/web-macro-surprise-confirmation-20261113-sol
model: sol
ended_because: ci_handoff
mission: >
  Implement the Chairman-assigned Macro Surprise and Confirmation Intelligence extension of MRI,
  with point-in-time data qualification, original-clock research, forward capture and bounded
  consumer integration. This is a source-phase checkpoint; the principal continues release and
  consumer verification. It does not declare the parent mission, broader RIC programme, or active
  session complete.
state_before: >
  Macro main f3a162741e2d6e57be19febf2e7e9799e39be6d8 already contained MRI v2, first-print
  receipts, event calendars, research statistics, TrialLedger and Prophet/Sector readers.
  The inspected economist-consensus owner explicitly reported no_admitted_street_economist_survey_source.
  Legacy macro_surprise priors/revised history were not a qualified point-in-time poll archive.
changed:
  - path: engine/release_surprise_confirmation.py
    what: Typed immutable poll snapshots, canonical first-print join, continuous and lag-normalized surprises, paired clocks, rights and explicit missingness.
  - path: engine/release_surprise_study.py
    what: Exact-session outcomes, shared monthly block resampling, declared-family testing, purged train-only forecasts and qualified-capture evaluation.
  - path: scripts/build_release_forecast.py
    what: Existing MRI producer publishes evidence; original forward writer adds inode-bound locking and separate local capture/readback receipts without a new store.
  - path: scripts/ingest_release_consensus.py
    what: Authorized local poll ingestion with actual capture timestamps, idempotency and interrupted-write reconciliation fences.
  - path: scripts/research_release_surprise.py
    what: Reproducible research and explicit current shadow capture through incumbent TrialLedger/MRI owners; synthetic input cannot activate capture.
  - path: app/prophet_daily_brief.py
    what: Authenticated optional include_macro_context query; legacy query/response defaults and source pins remain unchanged.
  - path: templates/_release_surprise_confirmation.html.j2
    what: Bilingual accessible Release Radar component, using the existing fetch and canonical disclosure anatomy.
  - path: docs/RELEASE_SURPRISE_CONFIRMATION.md
    what: Architecture, source/rights contract, fixed protocol, operational examples and scientific acceptance boundaries.
verified:
  - claim: New contracts and affected MRI, Prophet and Sector Central suites passed at the source candidate.
    command: python3 -m pytest -q tests/test_release_surprise_confirmation.py tests/test_release_surprise_study.py tests/test_release_surprise_pipeline.py tests/test_release_surprise_ui.py tests/test_release_surprise_capture.py tests/test_release_forecast_producer.py tests/test_prophet_today_provenance.py tests/test_prophet_daily_brief_api.py tests/test_sector_central_publication.py
    result: 300 passed, 7 skipped, 5 warnings; skipped legacy Claims integration cases require sparse-excluded committed vintages.parquet. Warnings are existing FastAPI/multipart deprecations.
  - claim: Actual component/renderer works on desktop/mobile in both languages/themes, with keyboard and failure-state checks.
    command: python3 -m tests.test_release_surprise_ui --outdir research/release_forecast/msc_evidence_20261113
    result: 12 checks, 8 screenshots, zero page errors, network blocked; synthetic component proof, not full production-page proof.
  - claim: The changed canonical CI job manifest is structurally valid.
    command: python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --validate-only
    result: 401 legacy jobs validated; this was manifest validation, not execution of all jobs.
  - claim: MRI fixture producer writes byte-identical latest/site evidence, readers preserve digest/authority and native Prophet candidates remain identical.
    command: python3 -m pytest -q tests/test_release_surprise_pipeline.py
    result: Executed as part of the 300-test run; fixture roots only, no production data writes.
unverified:
  - claim: This exact source candidate has merged, deployed and reached the real authenticated/native production consumer.
    what_would_verify: Exact-head binding GitHub evidence, permitted merge controller and covering deploy/render plus actual live consumer readback.
  - claim: A qualified historical economist-consensus archive reproduces Alphatica's complete sample and constitutes usable predictive evidence.
    what_would_verify: Existing data-owner admission, rights/vintage proof, original event universe and independently replayed historical observations; not available from the supplied infographic.
  - claim: The model improves a live or prospective trading strategy.
    what_would_verify: Genuine locally captured pre-entry forecasts, later outcomes, declared incremental-value/risk tests and existing owner's promotion decision; never inferred from synthetic tests.
unresolved:
  - Current source owner reports no admitted economist-survey source; no provider purchase, permission change or historical-vintage exception was made.
  - Core PPI has no canonical first-print target in the current actual owner and remains unsupported.
  - Source phase must still finish the actual repository CI/release/user-consumer lane; an artifact or green local tests is not that result.
next_actions:
  - Qualify the exact source head and use the existing permitted merge-on-green route once; preserve all release holds and unrelated live writers.
  - Verify the covering production render and real MRI/Prophet/Sector consumer states, preserving truthful missing-data behavior.
  - Qualify an already authorized consensus source/archive and its original capture or independently verifiable vintage evidence; do not substitute forecasts/priors or backdate imported observations.
  - Replay the declared protocol through existing TrialLedger, then collect actual current pre-entry shadow captures; promote only through the existing research owner with genuine future results.
do_not_redo:
  - Reuse the original managed operation macro-surprise-confirmation-20261113-sol and its reconciled workspace; no reacquisition or alternate writer.
  - Do not reconstruct another release/calendar/forecast registry, price source, research ledger, scheduler, retry loop or promotion authority.
  - Preserve RIC F0, accepted M0/X0 work and all unrelated wave states; do not rerun accepted historical programme work.
  - The image reports QQQ +0.62 percent in CPI-cold/PPI-hot; its inferred other disagreement cell is approximately +1.05 percent, not the prior assistant's erroneous +3.60 percent.
  - Never turn absent consensus into zero surprise, a neutral observation, no edge, or a buy recommendation.
danger_areas:
  - Protected Mastermind source pin fc91f33ccce3e8f18c78546f03c955c2ced0c704 controls this mission; source work has no power to change Executive or model admission.
  - Held PRs 7909, 7521, 7923, 7940, 7965 and GRI 8317 remain untouched; regime_outlook is unchanged.
  - Capture evidence is original-publisher local fsync/readback, not independent timestamp attestation or accepted model validity. Missing observation receipts stay unqualified after interruption.
  - Default Prophet response shape is closed; only explicit include_macro_context enables the additive context. Do not modify candidate scoring, sorting or source guards.
  - Shared render/daily lanes cannot be cancelled or redispatched merely to accelerate this source release.
---

## Continuity

The implementation task tree and corrections are in `research/release_forecast/MACRO_SURPRISE_CONFIRMATION_MASTERPLAN_2026-11-13.md`; the operational/statistical contract is `docs/RELEASE_SURPRISE_CONFIRMATION.md`. Source commits already published before this phase are `ca697bfa8ffe106eee4666ddcd994f9e8164faa1` and `71c1fd515f0967003e116ee5f1057a8f8378bf11`. The next source commit adds the completed forward-capture path, browser evidence, hardening, CI registration and these knowledge links. Resolve the exact PR from this unique branch instead of conducting an estate census.

No worker, daemon, watcher, live capture schedule, trading rule, external data purchase or independent reviewer was launched. Principal self-checks apply under the Web review waiver; actual repository protections and non-author approval requirements, when present, remain binding. A saved handoff is not the stop condition: continue the highest-value safe authorized release/data phase until the parent outcome is proven or its real remaining boundaries are recorded.


## Recovery and integration hardening - 2026-11-13

The assigned session recovered original PR #11226 at `f25ef6754b86ca63eb7fdcdb854f76c7d4952205`
and its existing managed workspace. No second worker, source branch, data provider
or uncertain write replay was created. Retained the six unpublished UI/root-binding
repairs and the existing screenshot delta; original custody/status was read back.

Source hardening now protects the private consensus archive from Git publication,
requires full input/dataset derived-data rights for public forward-ledger captures,
preflights batches before append, registers the input with existing DAG/Synapse
owners, and expands 31 existing CI scopes for 76 newly reached dependencies.
The incumbent MRI job is explicitly curated against its complete concrete import
closure so an unrelated free-content edit does not select its opaque fallback.
No required test, threshold, CI guard or permission is weakened.

Focused post-recovery contracts: **92 passed in 7.82 seconds** (synthetic/temporary
roots). The real committed-data dry run previously returned zero eligible matched
events, missing economist history and explicit actual-source defects; it wrote no
tracked data/site bytes. Those are honest unavailable states, not evidence of alpha.

The dated organizational handoff is now compiler-visible at
`agentos/handoffs/RATES-INFLATION-COMMAND-2026-11-13.md`; its former suffixed path
was not a canonical latest-handoff name. Wider RIC wave status is unchanged.

Related PR #11232 is an intentionally stacked, separately owned chart/visible
Events-dialog extension of #11226. Preserve that original writer/branch. Its
existence is not merged or live consumer proof. Current release acceptance still
requires CI contract/packing repair, fresh visual receipts, exact-head qualified
source release, a covering production render and real consumer readback.


### Current recovery verification

- Focused CI closure/packing assertions: 2 passed, 302 deselected in 162.78s.
- Affected MRI/Prophet/Sector/Radar regressions: 357 passed, 6 skipped, 5 warnings
  in 38.50s. Skips remain explicit sparse-data-dependent tests, not passes.
- Registry: 652 artifacts, zero violations; factor boundary guard clean.
- Agent OS: 2330 records, zero errors; 164 pre-existing advisory warnings.
- The unique comparison component now lives inside `#dlg-events`, not the hidden
  grid data host. DOM-ready rendering consumes the existing MRI snapshot without
  another fetch/timer. Full-page anonymous browser diagnostic returned the existing
  sign-in sheet, no JavaScript errors and exactly one MRI fetch. This is correct
  access enforcement, not authenticated production proof. A synthetic signed-in
  browser case and exact-source visual recapture remain to run.


### Visible native Events integration proof

The actual dashboard template was rendered in an isolated fake origin and opened
through its native Events card. Three browser cases passed with zero JavaScript
errors: anonymous retains sign-in; synthetic allowed-user desktop (1280) and
mobile (390) show the unique comparison, use the original MRI fetch once, and
open its disclosure with Enter. The probe waits for actual native opacity and
uses stable screenshots, avoiding blank mid-transition captures. Both native
screenshots were visually inspected. No live authentication was changed or
claimed. Receipts and source SHA-256 bindings are in
`research/release_forecast/msc_evidence_20261113/native-dialog-proof.json`.

The legacy P4 source-equivalence visual guard still needs genuine recapture at
the committed current render source. The native proof above does not waive it.


## Integrated source qualification milestone

Source fixes committed as `c1bd700db69107273f3435a6f22c0feaccf271c3`.
The exact current main `3534fad62bb2cbfba1e44a89c92fa717c9c54c52` was integrated
without conflicts at `3fa0404a7dec46621ffd93a67f4f25b801db52b3`. The only overlapping
owned path was the CI manifest; other sessions' changes were retained. A broad
inherited-generated-file whitespace check was noisy, so the actual owned delta
was separately checked against that protected base and passed; no unrelated
upstream SVG/data was reformatted.

The existing P4 probe genuinely recaptured **68 cases** at the integrated source,
bound all **31** render/fixture inputs, and its **164 tests passed**. Only its
receipt changed; the recaptured images were byte-identical to retained evidence.
The merged MRI + consumer regression returned **701 passed, 7 skipped, 5 warnings**
in 81.12s; overlapping earlier runs are not additive unique-test totals.

A read-only head census ran the incumbent closure/suite/control-plane checks
without invoking host-wide stale-worktree cleanup. Unrun suites, skip-only and
trigger-gap findings were empty. All three fixed packing probes met unchanged
10-pack/weight/count ceilings. Its sole closure finding was the native host test's
`tests/test_release_radar_render.py` input; that exact edge is now included in the
existing MRI scope. Hosted exact-head/base-delta CI remains authoritative.

Before: no source-bound macro-surprise comparison reached the real visible Events
host. After: tested original MRI producer/readers and native dialog integration,
with private poll storage and strict public derived-rights gates. Capability
state remains **BUILT_NOT_PROVEN** until permitted source release and covering
production/render/readback. Historical economist archives still need explicit
source qualification; no ingest path may backdate system possession. A provider's
historical market-availability proof must not be confused with our live capture
clock. Genuine historical reproduction and forward predictive validity are not
claimed by any test or screenshot in this work.

Next: publish this original candidate and consume exact-head CI; repair only
introduced failures, then use the existing qualified release controller and
verify actual consumers. The original active assigned session retains recovery;
no old-chat acknowledgment, duplicate worker, new watcher or new branch is owed.


Final local closure recheck after declaring the native-host test dependency:
**1 passed, 303 deselected in 138.89s**. The remaining code/visual candidate is
ready for publication to original PR #11226 and its binding hosted CI. Release
is not armed, and this source checkpoint does not end the mission.


## Final API serving dependency hardening

Post-publication adversarial consumer inspection found a genuine lifecycle gap:
`app/prophet_daily_brief.py` -> the incumbent stock-library projection -> the new
MRI reader imports three modules into the long-running API process. The existing
updater restart predicate matched none of `engine/release_surprise_confirmation.py`,
`engine/release_actuals.py`, or `engine/rates_command_basis.py`. An initial app change
would restart correctly, but a later reader-only fix could remain import-cached.

The original API restart regex now includes exactly those three source modules.
All updater bytes outside its existing API restart region are unchanged; no
Caddy, TLS, journal, CAS, source-install or runtime admission logic was modified.
Positive dependency tests and negative data/research/lookalike-path tests were
added to the incumbent suite. Affected updater/API/MRI tests: **509 passed,
5 existing warnings in 47.54s**. Bash syntax and diff hygiene passed. The two
visual receipts still match every unchanged input byte, so no recapture was repeated.

Current natural CI for predecessor `25d829af62f788a6014852893cc3aac676176353`
is run `43538595652`; necessary source movement will supersede that candidate,
not reuse its incomplete checks as proof of the final head. There is one attended
observer (PID88427), no duplicate workflow dispatch and no release opt-in.

Production preflight is durably recorded in #11226 comment6869127968 and the
existing TLS lane #10900 comment6869128615. The normal updater refuses a
non-route/TLS/global configuration mismatch; served MRI remains dated2026-10-16.
Source engineering and later permitted merge do not clear this actual deployment
gate. The separate TLS/held Caddy lanes and their current writers/holds remain
untouched. No service, credential, active config, producer ledger or data source
was changed on production. The source lane remains active on this original branch.


## Statistical-default falsification and final source proof

A bounded scientific self-check exposed a real finite-resampling limitation before
release: 2 pairs x 3 ETFs x 4 horizons x 7 conditions =168 hypotheses. The former
800-draw plus-one p-value cannot yield a first-step Holm result below168/801
(0.20974), regardless of an injected effect. This was a computation-resolution
limit, not evidence that the underlying relationship has no edge.

The fixed, predeclared default is now9999 shared draws; the family, correction and
nominal0.05 diagnostic threshold are unchanged. The first-step resolution floor
is0.0168. A bounded-chunk masked implementation is numerically equivalent to the
prior literal resampled mean-gap estimand; missing months remain absent. Reports
expose valid-draw floors and within-/cross-run resolution limitations. More logged
configurations may require more than the retained10000-draw bound; those cases
explicitly cannot justify a no-effect conclusion. This does not promote a signal.

The deterministic synthetic positive control, low-budget negative control, missing
calendar masks, exact chunk equivalence, cross-run floor and no-data controls all
passed. Source-hashed receipt:
`research/release_forecast/msc_evidence_20261113/bootstrap-resolution-proof.json`.
The control uses no real market data and claims no predictive or prospective alpha.
It records the uncommitted candidate by source SHA256, not falsely by its predecessor.

Final affected MRI/Prophet/Sector/Radar regression: **706 passed,7 skipped,
5 existing warnings in76.70s**. The separate updater/API restart suite remains
**509 passed,5 existing warnings**; these overlapping counts are not additive.
The actual PR merge-base remains3534; the new main1db19999c87f80b5ac750251b8ab49bb6526be94
has **zero overlapping owned paths**. A first broad diagnostic mistakenly counted
already-merged upstream data as owned; the corrected comparison uses the actual
PR merge-base and42owned paths. No upstream generated data was changed.

Both native/P4 visual source bindings remain valid because their input bytes did
not change. The25d829a CI observer ended after that candidate was superseded; its
cancelled contract/semantic result is not a source failure or current-head proof.
The e722890 predecessor CI43539531798 was running with no concluded failing job at
last read. Necessary scientific source movement supersedes it too. Publish the
completed candidate once, bind to its own natural CI, then qualify the original
release controller only when its required checks actually conclude clean.

Production and historical-data gates from #11226 comment6869127968 remain unchanged.
No TLS/controller bypass, actual-ledger append, provider purchase, service restart,
new worker/watcher, trade decision or claimed live acceptance occurred.


## Hosted design-evidence registration repair

Exact-head CI43540305502 at88ebf64 surfaced a real missing receipt in
`design-governance`: the new material template had browser screenshots under
research evidence, but no owning canonical `mockups/.../EVIDENCE.yml`. Existing
1280px desktop captures were not mislabeled as the required1440px matrix.

An original-registry receipt and reproducible local-fixture capture were added at
`mockups/evidence/mri-surprise-confirmation-20261113/`. The existing canonical
capture tool actually generated16cells: en/zh x dark/light x desktop1440/mobile390
rest captures plus real keyboard-focus captures. All byte/hash and applicable
receipt/matrix/interaction validations pass. Two representative states were
visually inspected. Focused validator/component tests:75passed,2skipped,9.99s.
No engine, UI component, authority, rights, deployment, threshold or check definition
changed; only evidence registration and cumulative documentation changed.

Local full-census CLI refused sparse-checkout scope; this was a configuration
boundary, not silently treated as success. No broad hydration, guard override,
second evidence schema or production screenshot claim. Hosted full-checkout CI
must close this gate on the new published source. The original88ebf64 run and its
remaining pack conclusions remain predecessor evidence, not proof of the next head.

The scientific adverse results and source/runtime dependencies are preserved in
PR comments6869171163,6869231916,6869270587,6869264815 and cumulative6869868647.
All score/rank/gate/size/trade authority remains false. Production remains blocked
by existing Caddy/TLS source/adoption qualification; economist-history admission
and genuine prospective validation remain separate obligations.


### Original-carrier recovery and complete visual qualification

The first managed commit attempt returned the gateway's legacy generic
`TYPED_GIT_PRECHECK_REFUSED`. Original publication/head/index readback and a
non-mutating staging diagnostic showed no commit or index change and identified
the concrete cause: new evidence was outside the workspace's sparse-checkout
include set. This was a Git checkout-configuration failure, not an observed
permission denial. No alternate Git carrier or force/sparse staging bypass was used.

After reading the existing sparse profile, storage admission returnedREADY with
~1.219TB free versus171.8GB minimum; original source/index locks were absent.
The existing `worktree_sparse.py add mockups` owner materialized only that allowed
reference directory (3.711GB committed). It completed successfully and preserved
all26 pre-existing modified/evidence file hashes and exact source head. No full
checkout, source-controller patch, live config change or data-provider admission.

The **full unmodified visual-evidence CLI guard now exits0**, and the focused
validator/component suite reports **77passed,0skipped in11.13s**, including both
formerly omitted reference tests. The original dry-run staging now succeeds;
only the owned25 source/evidence paths are candidates. This materially repaired
precondition qualifies another attempt through the same original managed publisher.
Hosted exact-new-head CI remains required before release; no green predecessor,
source publication or screenshot is being treated as production acceptance.

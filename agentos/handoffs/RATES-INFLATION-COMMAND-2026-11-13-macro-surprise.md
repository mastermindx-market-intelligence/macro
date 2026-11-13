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

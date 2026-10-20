---
workstream: "WS:BIOCATALYST-CORE-PRODUCT"
session: "sol/web-catalyst-company-evidence-r2-20261019"
model: codex
ended_because: blocked
mission: >
  Adopt BioCatalyst V3 through its existing native owners and prove the entitled
  What Matters Next to Decision Desk journey. This is a continuing source
  checkpoint, not production acceptance or a transfer of an existing operation.
state_before: >
  Original PR 9662 was Draft/Hold at a5931959da7337b179eff4a6760a484035b1877c,
  based on the original Bio branch. R9/R10 were accepted source work. Native
  Company/DataOS admission, entitled serving and release were unproven.
changed:
  - path: .github/ci/legacy-jobs.yml
    what: Added 21 exact dependency-path declarations across seven existing exclusive jobs after integrated import-closure verification found missing scopes.
  - path: engine/biocatalyst/company_event_adapter.py
    what: >
      Added a pure owner-cut composition entrypoint using canonical identity
      readers and the existing WMN v2 validator. It neither attests upstream
      admission nor publishes or creates acceptance clocks.
  - path: tests/test_biocatalyst_what_matters_next.py
    what: Added focused composition, correction, missing-symbol and invalid-cut witnesses.
  - path: tests/test_biocatalyst_wmn_publication.py
    what: Routed synthetic owner fixtures through the composition entrypoint before the existing service/publisher transaction.
verified:
  - claim: Integrated exclusive CI scopes cover the actual import closure.
    command: >
      python3.12 -m pytest -q tests/test_ci_pack.py::test_the_curated_exclusive_set_is_actually_declared
      tests/test_ci_pack.py::test_curated_exclusive_scopes_cover_their_own_import_closure
    result: >
      2 passed in 192.25s after adding the three actual Bio dependency paths to
      seven existing job declarations. Commands, enabled states and gates are unchanged.
  - claim: The original source carrier was preserved and supported-base adoption was authorized.
    command: "git log --format='%H %P %s' -2 c9eb64b5047cc8c4857a4daafa8fce4457fd66b5"
    result: >
      Composition commit ef2a68e86258a4f7a5ef70ca739cc030fcf09924 follows the original
      R10 head. Merge c9eb64b5047cc8c4857a4daafa8fce4457fd66b5 incorporates observed
      main 68da9a798428ad425ceda592551719d0c649a1d8 without conflict or rewritten history.
      Chris confirmed this chat owns the checkout; the delegated portfolio ruling
      permits this same-PR base adoption and retargeting, while retaining release HOLD.
  - claim: Focused new composition checks passed before main adoption.
    command: "python3.12 -m pytest -q tests/test_company_intelligence_catalyst_event.py tests/test_biocatalyst_what_matters_next.py"
    result: "69 passed; separate publication suite 23 passed. Workspace-owned basetemp was used."
  - claim: Integrated Company/WMN/native snapshot checks passed; sparse-fixture failures were diagnosed and repaired without changing source data.
    command: >
      python3.12 -m pytest -q --tb=short --basetemp=.pytest_cache/native_integrated_01a158fd
      tests/test_company_intelligence_catalyst_event.py tests/test_biocatalyst_what_matters_next.py
      tests/test_biocatalyst_wmn_publication.py tests/test_biocatalyst_wmn_api.py
      tests/test_entry_radar_identity_observation_snapshot.py
    result: >
      139 passed and 15 collection-dependent failures after the merge omitted sparse
      fixtures. Restored the five ClinicalTrials and three history fixtures
      byte-for-byte from the index. The affected publication/API rerun passed
      all 43 tests in 48.10s. No fixture or production guard was rewritten.
  - claim: The new composition delta received an independent bounded source review.
    command: "fabric_task.py result bio-native-01a158fd-composition-review"
    result: >
      Scoped PASS, no concrete introduced bug; MiniMax on Ubuntu2, authored source
      was local Codex. Reviewer did not execute tests. Parent accepted the review
      through the same run with --by reviewer. Native admission and real input
      binding are explicitly outside this pure helper's claim.
  - claim: The available local reference data cannot supply a native snapshot.
    command: >
      read_identity_snapshot('/Users/chriswong/Documents/Cluade/macro-main/data/reference')
      using the integrated engine.entry_radar.replay.identity_observation_snapshot owner
    result: >
      REFUSED: identity observations: snapshot owner context missing.
      The local receipt has no publication or identity_observations fields.
      /var/lib/macro-biocatalyst/owner-inputs/what_matters_next_inputs.json is absent locally.
      This is local evidence, not a statement about deployed VPS data.
unverified:
  - claim: Actual Company and DataOS native input admission for BioCatalyst.
    what_would_verify: >
      Existing owners supply a qualified current reference snapshot and an admitted
      Bio event/document/span cut, with real rights, clocks, revisions and unavailable coverage.
  - claim: Entitled deployed WMN and Decision Desk acceptance.
    what_would_verify: >
      Separate release authorization, reader-before-writer rollout, actual shared
      admission/pointer/lock state, and authenticated account/route/correction browser proof.
unresolved:
  - "PR 9662 must remain Draft/HOLD, without auto-merge or merge-on-green; no merge-to-main, deployment or activation is authorized."
  - "Exact-head hosted CI and final base/description publication must be consumed from the same PR; local tests are not hosted acceptance."
  - "Main's native Company disclosure owner is constrained to C01-micron-planned-product-integration and private_company_intelligence_context; its rights are not Bio rights."
  - "Studio fleet status returned FLEET_STATUS_OWNER_RESULT_INVALID; no VPS runtime proof was obtained."
  - "Fabric census bio-native-01a158fd-owner-census was refused before launch with FABRIC_NEW_MACRO_WORKTREE_SCOPE_REFUSED. It was not retried or replaced."
next_actions:
  - "Finish same-PR publication/retargeting and consume exact-head CI through the existing carrier; preserve all holds."
  - "Resolve the native input dependency already sent to portfolio chat 01a14c38-2baf-76c2-9475-b1f0a370ab17, through existing Company/DataOS producers. Do not mint a receipt from this local snapshot."
  - "Bind the qualified native records to compose_wmn_owner_inputs and the existing fixed handoff/publication transaction; the helper is composition, not independent admission."
  - "Adopt existing Decision Desk PR 9611 through qualified source custody, then obtain entitled production proof after release authorization."
do_not_redo:
  - "Do not repeat accepted R9/R10 work or create a replacement PR, publisher, identity allocator, admission store or source owner."
  - "Reuse the independent source review until the reviewed delta or relevant semantics change; it is not a whole-program release review."
  - "Do not treat 376 historical tests, current local checks, a source merge or this checkpoint as production acceptance."
danger_areas:
  - "Original workspace: /Volumes/Mastermind 2/agent-workspaces/macro/web/catalyst-company-evidence-r2-20261019."
  - "Native DataOS ReferenceSnapshot, ReferenceReadReceipt and observation-aware alias semantics survive the merge; do not replace the owner with an older copy."
  - "The pure helper relies on upstream custody to bind in-memory readers to declared DataOS digests. That binding must be proven before native activation."
prs: [9662, 6712, 9611]
---

The active local receiver is Codex chat `01a158fd-eaba-7342-8b59-081a483f2fc2`.
The managed source operation remains `catalyst-company-evidence-r2-20261019`.
The public input contract, publication pointer and correction lock remain their
existing owners. No new runtime or transport authority is established here.

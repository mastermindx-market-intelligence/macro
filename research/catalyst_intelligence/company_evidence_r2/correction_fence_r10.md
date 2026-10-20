# BioCatalyst correction fence R10

**Status: DRAFT / HOLD. Source gap closed; native adoption and release remain separate gates.**

This continues the recovered **Redesign BioCatalyst User First** project on the existing Company evidence carrier, PR [#9662](https://github.com/mastermindx-market-intelligence/macro/pull/9662), managed operation `catalyst-company-evidence-r2-20261019`. Verification was completed on 2026-10-20 through Studio Direct C2 Personal in the existing registered M2 Studio workspace.

## Outcome and source lineage

Company evidence head `430234957531693b6b13f026a161e28542086a82` and the original Bio repair R9 head `76f5a28d5d8e8200fbb9c36882f158541809ec3e` were integrated as the real two-parent merge `7ac8fae13e7a9e7164064c58595985ea5ee5d902`. The integration passed 152 focused tests and two curated CI scope checks; [its evidence is recorded separately](r9_integration.md).

R10 is a single-parent source change over that merge. Its exact delivery commit is the Git commit containing this document; the six verified source/test hashes below identify the tested implementation without a self-referential commit hash.

The remaining correction problem was causal: an older build could finish after a newer owner-input cut had been accepted, or an older pointer could be restored after a newer build failed. R10 makes acceptance a durable local transaction and requires both publication and current WMN serving to match that transaction.

## Behavior

1. The service initializes the local admission store and captures its current ticket **before** opening and reading the owner handoff. It validates the complete current WMN v2 payload and compare-and-swap admits that cut **before** attempting the coarse worker lock.
2. A successful admission records a positive sequence, a unique admission ID and the hash of the complete normalized payload. An expected-ticket mismatch is checked before identical-payload idempotence. A late file read cannot acquire authority by matching a digest, and an E1 → E2 → E1 payload sequence does not reuse the first E1 ticket.
3. Direct worker calls must supply an already admitted ticket. Preparation retains the consumed ticket. Promotion revalidates the installed immutable generation, recomputes the payload digest and compares the entire ticket with durable current state under the publication lock.
4. Pointer replacement and exact-byte rollback remain under the same lock. A pointer-write failure can restore pointer bytes; it cannot roll back a newer accepted admission.
5. WMN list and detail handlers check the actual publisher before composition and again after JSON response encoding. Superseded, missing or corrupt admission state makes current WMN unavailable. A changed pointer at the same admission is rejected as a generation change.
6. Historical trial reads remain independent of current WMN admission. They can still read the retained historical artifact when current WMN is unavailable.

A real service-path race witness covers an E1 candidate paused while holding the coarse worker lock, E2 admission before its worker attempt returns locked, a failed E2 build, refusal of E1 promotion, restart preservation of E2, unavailable WMN list/detail alongside a successful historical trial read, successful later E2 publication and continued refusal of E1.

### Durable state and compatibility

The closed `biocatalyst_wmn_admission.v1` schema 1.0.0 is stored in `wmn_admission.json`. The stable `wmn_publication.lock` inode carries a durable initialization marker. Writers take an exclusive flock; servers open the existing lock read-only and take a shared flock. The implementation rejects symlinks, invalid file identity and malformed state. The lock is never replaced or unlinked by the publisher.

Initialization records an explicit null-ticket state and then durably marks the lock inode. This distinguishes a fresh store from loss of admission state even before the first pointer was ever published. State loss cannot silently reset a sequence.

The pointer contract retains exact schema dispatch: historical `biocatalyst_current_pointer.v1` schema 1.0.0 stays unchanged; current fenced WMN publication uses schema 1.1.0 with the consumed ticket. A valid v2 owner artifact behind a historical pointer remains trial-readable but needs fenced republication to qualify as current WMN. No artifact or old pointer bytes are rewritten in place.

**Rollout dependency:** compatible readers must be present before writers begin emitting pointer schema 1.1.0. Older binaries accept only the historical pointer shape. This source delivery performs no rollout.

### Digest recipe

The admission digest binds the **entire validated and normalized WMN v2 payload**, including distinct issuer-master and vendor-alias members, Company event cuts and versioned public source context. A source-context-only correction at the same Company event revision changes this digest.

Sector/Bio canonical payload encoding uses sorted JSON keys, compact separators, UTF-8 and `ensure_ascii=False`, with **no trailing newline**. Publisher artifact bytes and the separate Company `canonical_json_bytes` helper append a newline. The admission hash is therefore intentionally different from the artifact byte hash. Tests state and exercise both recipes rather than conflating them.

## Verification

| Check | Result |
| --- | --- |
| Final eight product suites | **376 passed**, 10 warnings, 281.66 seconds; exit 0 |
| Curated CI declaration and import-closure checks | **2 passed**, 2 warnings, 187.42 seconds; exit 0 |
| Integration before R10 | 152 focused tests and 2 curated checks passed |
| Source diff hygiene | `git diff --check` passed |
| Source snapshot | All six file hashes matched after the final run |
| C3 architecture/source review | Concurrence; no required production fix remains |

The product command, run from the registered repository with the equivalent absolute basetemp path, was:

```bash
python3.12 -m pytest -q --tb=short \
  --basetemp=.pytest_cache/wmn_fence_7ac8fae1_r10_verification \
  tests/test_company_catalyst_public_evidence.py \
  tests/test_company_intelligence_catalyst_event.py \
  tests/test_biocatalyst_research_priority.py \
  tests/test_biocatalyst_what_matters_next.py \
  tests/test_biocatalyst_wmn_api.py \
  tests/test_biocatalyst_wmn_publication.py \
  tests/test_biocatalyst_worker.py \
  tests/test_biocatalyst_api.py
```

The curated checks were `test_the_curated_exclusive_set_is_actually_declared` and `test_curated_exclusive_scopes_cover_their_own_import_closure` in `tests/test_ci_pack.py`. API tests remain in their existing API suite and Company source-context tests remain in their owner suite, preserving the existing worker import scope without a new CI registration.

Additional witnesses cover stale and ABA tickets, a late handoff read, direct-worker refusal without admission, state loss before first publication, post-replacement admission failure without rollback, pointer rollback without admission rollback, source-context-only corrections, missing/corrupt state, historical pointer migration and corrections during response composition. The lock-exclusion witness uses a separate OS process.

### Execution diagnostic and resolved development failures

The first broad run under the macOS default temporary root produced 205 passes, 66 failures and 105 errors. The first worker failure was `BIOCATALYST_R2_ACTIVATION_GATE_INVALID`, before collection or publication; generic API fixture errors cascaded from it. A focused diagnostic showed the activation verifier and its fixture were unchanged from integration head `7ac8fae1`. The fixture expected uid 501 / gid 20; the default temporary root produced gid 0. The required directory and file modes, uid and canonical path were correct.

The identical suites were rerun in a new directory below the workspace-owned pytest cache after checking that its parent group matched the process group. No activation verifier, fixture, system directory permissions or activation guard was changed. The final 376-test result is the corrected-environment result, not a waiver of the first run.

Earlier red tests established missing admission and the ability of a direct worker to publish without a consumed ticket. During expanded verification, one late-read fixture needed the existing runtime-layout preparation and one expected digest used the wrong canonical JSON namespace. Both were repaired before the final run. The final test-source cleanup changed blank lines only and was checked to preserve the Python AST.

Eight sparse-checkout omissions—five ClinicalTrials and three history fixtures—were materialized byte-for-byte from the existing Git index. Generated fixture data was not substituted. Final product warnings concern existing Starlette/FastAPI deprecations and duplicate OpenAPI operation IDs. The two CI-check warnings concern cleanup of a pre-existing unrelated Chromium pytest temporary tree.

### Review and test attribution

C3 independently inspected the three production files at the hashes below and concurred with admission ordering, installed-artifact binding, stable initialization, exact pointer dispatch, pointer-only rollback and the final response gate. **Root executed the tests; C3 did not.** Those two kinds of evidence remain separate.

The new disk-backed API witnesses exercise the real publisher, installed bundle, composer and final gate, with synthetic authentication and runtime-import seams. The existing pure API harness also stubs the new recheck gate, so it remains handler/composer proof and is not presented as native admission or final-gate evidence. No test establishes an actual entitled user session or deployed serving path.

## Exact verified files

| File | SHA-256 |
| --- | --- |
| `engine/biocatalyst/publication.py` | `60e62aabd5bf2ac19cb56e237e9e6e67acdd5edefe0df52cb2ce4dfba7c02fdc` |
| `scripts/biocatalyst_worker.py` | `076f4091f8c4957539625250d651e5289743daf158991546ff8693f1bf105e7c` |
| `app/biocatalyst.py` | `e6833f4b73930eac850c8f9a8d5e26f8ffed008ddcf72454450f7f4a5a2f2986` |
| `tests/test_biocatalyst_wmn_publication.py` | `12730a751d342b092c0c7a1b2573f73b19c4cdb8e213d9d8535894b336a1f25e` |
| `tests/test_biocatalyst_wmn_api.py` | `bd34b9194b6b5709c1afa2ad9af38699dd1d08fd0195c9ccf163404405f6547c` |
| `tests/test_company_catalyst_public_evidence.py` | `c7430ef4c265c80b4701422aa40b65a4074afa7460fcde1c22c0a7c713b6091c` |

The structured receipt is [correction_fence_r10_verification.json](correction_fence_r10_verification.json).

## Remaining owner and release gates

The ticket means **local publisher admission**. It does not independently attest native DataOS or Company admission, upstream artifact custody or source rights. An independent owner handoff-file replacement is not itself the durable local acceptance transaction.

The final serving check defines request-time eligibility. It cannot retract an HTTP response already in flight or invalidate an already displayed browser view.

The next gate is adoption by the existing BioCatalyst native publisher and serving owner behind [#6712](https://github.com/mastermindx-market-intelligence/macro/pull/6712), through reconciled source custody. That requires an owner-authorized real WMN v2 handoff with independently established Company-event and DataOS issuer-master/vendor-alias admission. Publisher acceptance and the serving process must use the same durable state and pointer. Compatible readers must precede schema 1.1.0 writers.

After that owner/runtime gate, the composed list/detail API needs proof through an actual entitled session, and the existing [#9611 Decision Desk adapter](https://github.com/mastermindx-market-intelligence/macro/pull/9611) must be adopted on that serving path. Another synthetic consumer does not substitute for this source-to-user proof.

The original repair checkout remains preserved and Fable remains terminal. R9 source repairs were adopted by the integration merge; the old statement that #9662 has not adopted those repairs is obsolete. Stock-context and NewsImpact work remain on their existing carriers.

The historical CI `unsupported_base_ref` and Vercel packaging failure at Company head `43023495` are retained historical observations, not current-head CI results. This source delivery does not change allowed-base policy, widen a gate or establish hosted CI acceptance. Supported release-base adoption, current-head CI, serving packaging, native activation, scientific/trading qualification and release approval remain separate.

**DRAFT / HOLD remains in force.**

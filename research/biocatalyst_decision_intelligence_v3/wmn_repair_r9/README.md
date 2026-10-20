# BioCatalyst WMN repair R9 — resumed user-first project

Date: 2026-10-20  
Source carrier: [Macro PR #6712](https://github.com/mastermindx-market-intelligence/macro/pull/6712)  
Original branch: `sol/biocatalyst-v3-r0-fable-principal-20260901`  
Pickup commit: `ec5c2e2544576f20348c6eadf834fe3cefae8039`  
Managed continuation: `biocatalyst-wmn-repair-r9-20261020`

This continuation repairs the retained What Matters Next (WMN) dependency of the
user-first Catalyst program. It preserves the original PR and Draft/HOLD posture.
The company assessment continuation remains on
[PR #9616](https://github.com/mastermindx-market-intelligence/macro/pull/9616);
the Decision Desk and company-evidence slices retain their existing carriers.

## Outcome and authority

Current WMN research rows now use their actual timing/revision fields for sorting,
require an alias-bound input cut, reject future-dated identity lookup, distinguish
optional unavailable estimates from real coverage gaps, and report stored owner
contract failures as server unavailability.

No source collector, identity allocator, event store, publication owner, scheduler,
model or trade authority is added. The existing public-generation publisher and
API routes remain the owners. This source repair does not establish native DataOS
admission, decision-time availability, production activation, deployment, merger
acceptance or predictive usefulness.

Protected procedure was loaded at
`Mastermind@a7553e0a18339c910eef9687c730b06605dd710e`, Skillpack 1.0.1,
bootstrap major 1. The subsequent protected head
`2b3429d9aca0d539e7ac2b097a199fb86de2d329` has the same INDEX blob
`339c3d810f8c74ec157a793b143fde9aeb1e4fec` and does not change the loaded
procedure files. Its desktop-account guard change does not affect this source-only
continuation. No provider GUI, paid worker or Executive runtime was started.

## Retained work and source custody

The retained October 4 recovery checkout was found at the exact pickup commit.
Its four dirty test files were copied byte-for-byte into the clean managed
continuation before editing. The original checkout and test bytes remain intact.

| Original retained test | SHA-256 before adoption |
| --- | --- |
| `tests/test_biocatalyst_what_matters_next.py` | `4082ce7443df8540d66a567353d381e59e06382189b844c71e9b34c8b14bc6cf` |
| `tests/test_biocatalyst_wmn_api.py` | `7a6f47ab4a73e31c45d644dc5f9bf552358f9327875395232762933407286565` |
| `tests/test_biocatalyst_wmn_publication.py` | `e7cdbff9f08acbd85e981b5a9712d621fdd9228bf0a3e1527d9d6c7d2c92a2b3` |
| `tests/test_company_intelligence_catalyst_event.py` | `dff90c35f3b3855b4b883ab8b1062a52d6144a0c631116ef090cba7077848c43` |

The retained discriminators reproduced five failures against the pickup source:
nested ordering, missing alias binding, optional-estimate handling, future alias
lookup and the detail route's error mapping. Duplicate event identity was already
rejected correctly and was not reimplemented.

Managed test fixtures were then advanced explicitly to the new v2 wire. One
retained optional-estimate test also declared an unrelated unbuilt registry
family; that unrelated gap was removed from this isolated test case. Separate
matrix cases prove that actual source/family/required-owner gaps still force
partial coverage. The original retained test bytes were not rewritten.

## Versioned artifact compatibility

| Input contract | Artifact integrity/read | New publication and current WMN |
| --- | --- | --- |
| `biocatalyst_wmn_inputs.v1` / `1.0.0` | Original validation and canonical normalization preserved | Refused; alias-bound input is required |
| `biocatalyst_wmn_inputs.v2` / `2.0.0` | Closed v2 validation | Admitted only after v2 validation |
| Unknown or mismatched contract/version | Refused | Refused |

V2 requires exactly one `dataos_issuer_master.current` and exactly one
`dataos_vendor_aliases.current` member, alongside the existing exact hashed
Company event members. All members retain the existing digest-format,
availability and cutoff-clock constraints. V2 also validates the resolved nested
issuer/security shape and a real canonical civil identity date no later than the
generation cutoff's UTC date.

The consumer receives owner projections and declared dependency hashes. It does
not possess the raw DataOS artifacts and cannot prove that arbitrary supplied
hash text attests those projections. V2 therefore establishes complete declared
dependency binding at this boundary. Native owner admission and faithful
projection provenance remain the existing owners' obligations. An alias digest
must not be invented from the projection or copied from the issuer-master digest.

`validate_wmn_inputs` dispatches by stored version for historical artifact
integrity. `validate_current_wmn_inputs` is the shared current-use gate used by
composition, publication preparation and the service handoff. A failed v2
validation never falls back to v1.

This split is required because the publisher materializes every artifact while
reading a selected generation. Tightening v1 in place would invalidate unrelated
CT.gov facts. With an old selected v1 generation, the factual trial API still
works; current WMN list and detail return 503 `OWNER_INPUT_UNAVAILABLE`.
No old artifact, manifest hash, pointer or generation identity is silently changed.

The existing artifact filename and public-generation inventory are unchanged.
The self-describing embedded input version advances; the external WMN list/detail
response contracts remain v1.

## Other repairs

- Research Priority preserves its original flat normative inputs and reads WMN's
  nested `timing` and `revision_summary` fields when sorting composed rows.
- The DataOS current-identity adapter rejects an identity date after the generation
  cutoff before performing alias lookup. Precomputed v2 inputs cannot bypass it.
- Missing probability, materiality, historical-response or incorporation owners
  remain explicitly reported as `NOT_ESTIMABLE` with null values. Their absence
  alone does not make otherwise supported research facts partial.
- Unknown required-owner gaps, source problems and unsupported event families
  continue to determine partial/stale/empty/ready behavior.
- The detail route handles `ContractError` before its `ValueError` superclass,
  preserving caller-error handling while returning the correct owner-failure 503.
- Published JS/CSS are synchronized with their template sources. The authority
  copy is translated into plain EN/ZH product language; authority fields are
  unchanged.
- The old D0b whole-file prediction-word ban is scoped to the Trial workspace and
  retains its exact negative WMN unavailability declaration. The actual shipped
  WMN validator is executed to prove that numeric estimates, missing estimate
  slots and elevated trade authority are refused. No replacement validator is
  used in that proof.

## Existing CI owners and STSI reconciliation

The original October 4 worker commission excluded shared CI changes while STSI
held a separate subregion. This current root continuation reconciled the exact
source before adding the six missing Bio registrations.

Fresh source inspection of #8404 at
`9a4495c0f44372c4e8e7285cbf2bb18e74216a3d` confirms two separately appended
STSI steps in `biocatalyst-contracts`, and the distinct
`engine/theme_graph/identity.py` worker path. Their accepted subregions are
recorded in #6712 comments 5976147456, 5976649086 and 5976841111.

This continuation changes only:

| Existing code-gated job | Additive registration |
| --- | --- |
| `biocatalyst-serving` | Publication-test dependency and exact historical fixture path |
| `biocatalyst-worker` | Exact Company contracts/events/identity and DataOS identity modules; exact historical fixture path |
| `biocatalyst-contracts` | Company catalyst-event test in the existing Bio command |

All prior fields, steps, paths, gates, budgets and jobs are preserved. There are
no new jobs, scope wildcards, exceptions, planner changes or test waivers.
STSI's appended steps and its distinct worker dependency are not edited or
imported into this branch. Actual later composition must retain both projects'
registrations. The first proposed registration batch failed its pre-write
assertion and made no CI change; the revised exact batch was applied and checked
structurally. The fixture's exact path is also registered in its two consumer jobs.

Two typed commit requests were refused before any commit. Read-only Git dry runs
identified the new fixture and the paired site files as outside this checkout's
sparse definition. The fixture's unchanged bytes were moved to the normal test
fixture directory and its test and exact CI dependencies were updated. The
repository's canonical `worktree_sparse.py add site` helper then materialized the
required site directory while preserving the edited JS/CSS bytes. Normal Git dry
run staging includes all eighteen intended files. The same typed publication
path is retained; no publisher, permission or source gate was altered.

## Actual verification

| Check | Observed result |
| --- | --- |
| Owner, identity, Research Priority, WMN composition, API and publication suites | **101 passed after R9a review fix** |
| Page, D0b UI and hydration suites, including the real WMN envelope validator | **74 passed** |
| Curated exclusive dependency closure and declaration checks | **2 passed** |
| Python compilation and diff hygiene | Passed |
| Template/site JS and CSS equality | Exact byte equality |
| Source-copy gate | 38 remaining findings after site materialization; all reproduced against unchanged pickup blobs; zero BioCatalyst findings |

After the fixture relocation, the combined core and UI command passed all **168
tests** in 22.44 seconds. The two CI closure/declaration checks then passed in
278.65 seconds. Subsequent site materialization preserved the exact tested core,
test and paired asset bytes. The source-copy scan was refreshed on that expanded
inventory: all 38 findings reproduce against unchanged pickup blobs. The earlier
sparse checkpoint had 22 findings. Its unchanged allowlist was restored from the
exact pickup Git object after materialization omitted it.

The core command was:

```sh
python -m pytest -q tests/test_biocatalyst_research_priority.py tests/test_biocatalyst_what_matters_next.py tests/test_biocatalyst_wmn_api.py tests/test_biocatalyst_wmn_publication.py tests/test_company_intelligence_catalyst_event.py
```

The UI command was:

```sh
python -m pytest -q tests/test_biocatalyst_page.py tests/test_biocatalyst_d0b_ui.py tests/test_biocatalyst_hydration.py
```

Sparse-omitted test dependencies and twelve old reference plates were restored
from exact pickup Git objects. Those existing images are historical references,
not fresh screenshots of this repair. No Paper or visual-design board was edited.

`tests/fixtures/biocatalyst_wmn/legacy_v1_generation_ec5.json` was generated by
the original ec5 source with the existing offline fake collector and fixed clock.
It contains twelve original public files. Its SHA-256 is
`eb1dd51c9be94103feb0b7eea39e306c385fd03d70f1ecdc57a6a9c653865ed8`.
The captured generation is `ctgov_run_20260801T150000000000Z_e1064ea5a0be`,
with manifest hash
`c990c8db86d92df47e103b8954b5bbb965b12ba6b694d484520481bb7353f4d5`.
These are synthetic compatibility fixtures, not native source qualification.

The original-generation test checks unchanged artifact bytes, selected pointer,
manifest identity and CT.gov trial content. Additional cases refuse tampering,
old inputs at preparation/service/current composition, version mismatches,
missing/duplicate alias members, invalid/future civil identity dates and
precomputed invalid security projections.

The worker's existing public error-code allowlist maps a preparation failure to
`COLLECTION_FAILED`. The new refusal test observes the real
`WMN_OWNER_INPUT_INVALID` exception from `prepare_generation`, verifies that
the worker keeps its existing external mapping, and proves no pointer or private
object publication occurs. That distinction is not a changed production error
contract.

See [source_claim_baseline.json](source_claim_baseline.json) for the exact remaining
source-copy findings. The checker and allowlist are unchanged. Every remaining
finding was rerun through the original checker against its exact pickup Git blob;
none comes from a changed Bio file. The broad gate is still red and is not waived.

Inherited local warnings concern pytest cleanup and the installed
Starlette/httpx interface. They do not represent test failures.

## Review and remaining gates

The independent C3 architectural review accepted the version/current-use split.
The first implementation attempt returned INCOMPLETE because its workspace read
supplied no source. A subsequent bounded read obtained the full six-file diff,
reconstructed all six files against ec5, and independently matched every supplied
whole-file hash. That review found a nested alias-observation date inconsistency.

The R9a follow-up binds every admitted security's `symbol_observed_on` to the
already checked canonical `identity_cut_date`, solely within the v2 branch. Five
new malformed/mismatched date cases reproduced the original defect before the
production edit; matching v2 and historical v1 cases already passed. After the
repair, all **101 core tests passed** in 11.90 seconds, including the authentic
old-generation materialization cases. An intermediate run's six failures were
caused by site materialization removing five unchanged clinicaltrials fixtures;
restoring their exact ec5 Git bytes resolved them without test or source waivers.

The reviewer independently reconstructed the final WMN file from the inspected
source and the exact small replacement, matched SHA-256
`8c9a98050ced7aa673cd904e56ffba55ee106bda122fcfef98ffc0cf0a0b580c`,
and issued **bounded source acceptance for the six-file R9 core**, with the other
five production files unchanged. The tests remain root's execution evidence.
The changed production file also passed the unchanged source-copy scanner;
the 38 inherited full-inventory findings remain recorded separately.

Initial R9 was published as
`76f5a28d5d8e8200fbb9c36882f158541809ec3e`, tree
`b7b4d6b6f414ab94499bdb2babd2ae7f46422c6e`, sole parent ec5.
The first push response was uncertain. Typed publication status and independent
GitHub branch readback both proved the exact commit applied before the original
#6712 branch was fast-forwarded without force. This follow-up retains that same
carrier and hold.

Source acceptance does not release merge, production or native-owner
qualification holds. The 74 UI checks and two CI dependency checks belong to the
initial R9 execution; their asset, import and CI registration sources are
unchanged by the small follow-up. No fresh combined 175-test run is claimed.

Fresh hosted CI on the published #6712 continuation remains required, including
any inherited whole-branch gates. Source acceptance does not release the existing
production, entitlement, owner qualification, native observation, model, trading
or deployment holds.

The next program dependency is the existing publisher's correction-admission
fence: a consumed owner revision must still be current at promotion, and admission
of a correction must immediately make stale WMN current-use unavailable without
erasing historical trial evidence. That implementation and its deterministic
race proof are not part of this repair.

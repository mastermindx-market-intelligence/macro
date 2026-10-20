# SPY current Yahoo catalog intake

## Purpose and scope

Returns needs a defensible SPY benchmark identity before it can qualify the
benchmark's directly fetched daily history. The existing SPY security is
SEC:US-ARCX-SPY. This intake adds one current yahoo_fetch/SPY relation to that
existing record through scripts/build_security_master.py.

It does not mint or revive a security, assign an issuer, add an ETF to the
common-stock seed population, create a Macro stock-store alias, reuse a Theta
option root, or qualify an adjusted price history. It grants no historical
identity, model, forecast, trading, or source-use entitlement.

The Yahoo-to-issuer association is a closed, source-specific inference. Yahoo's
captured response supplies no CUSIP or ISIN. The issuer's identifiers remain
issuer evidence; they are not relabeled as Yahoo identifiers.

## Required inputs

The explicit local manifest uses schema mastermind.spy_yahoo_catalog_input.v1
and has only schema and sources at its top level.

| Source member | Input |
| --- | --- |
| yahoo | body sibling filename and capture object |
| issuer | body sibling filename and capture object |
| listing_body | Original collector Parquet sibling filename |
| listing_receipt_body | Original collector completion-receipt sibling filename |

Each HTTP capture has exactly url, final_url, status, bytes, sha256,
request_started_at and read_completed_at. The supported original and final URLs
are fixed by this profile:

- https://query1.finance.yahoo.com/v8/finance/chart/SPY?interval=1d&range=1d
- https://www.ssga.com/us/en/intermediary/etfs/state-street-spdr-sp-500-etf-trust-spy

Files must be bounded, regular sibling files. Symlinks, traversal, missing
files, duplicate JSON keys, nonfinite numbers, failed responses and mismatched
byte digests refuse. The CLI does no network access or automatic recollection.

Source capture provenance is the caller's responsibility. A digest detects
different bytes; it does not authenticate the sender or authorize reuse.

## Source and canonical checks

The single successful Yahoo chart result must identify SPY, ETF, USD, PCX,
NYSEArca, America/New_York and the exact supported fund name. No general
PCX-to-ARCX translation rule is introduced.

The issuer parser requires one visible fund heading and one complete listing
table under its dated Listing Information heading. The row must identify SPY,
NYSE ARCA, USD, CUSIP 78462F103 and ISIN US78462F1030. Scattered page text,
metadata alone, another fund's table, duplicate rows and conflicting identities
cannot be assembled into a match. Duplicate attributes and unmatched end tags
refuse. An actual element stack preserves inherited hidden state; the dated
heading and table must share their actual section, and every intervening heading
ends the association. Registered-mark removal and whitespace normalization are
explicit; there is no fuzzy name matcher.

The issuer's 1993-01-22 listing date and Yahoo's firstTradeDate are distinct
provider fields. Neither establishes measured price coverage or the validity
start of this new relation.

The listing snapshot must validate against the existing collector's original
completion receipt, be eligible for listing identity, contain one supported
SPY ETF listing, and match the existing owner's current snapshot byte for byte.
The incumbent scoped listing resolver must establish US-ARCX-SPY.

The canonical target must already exist exactly once, be active and
unsuperseded, and have the exact US/ARCX/SPY listing fields and lawful stored
clocks. Its issuer fields and every other canonical field remain unchanged.

## Clocks and prospective meaning

This fresh-intake profile deliberately requires the Yahoo observation, issuer
observation, issuer listing heading and collector observation to share the
admission's UTC date. This is the selected profile's rule, not a claim that all
Data OS CURRENT queries universally require same-day observations.

An October 15 receipt is a dated continuity fact. It cannot be relabeled as an
October 19 receipt or satisfy this profile alongside October 19 public captures.
The original collector must produce any new qualifying snapshot and receipt.

| Receipt field | Meaning |
| --- | --- |
| source_available_at | Latest required original HTTP/collector completion |
| reference_read_completed_at | Conservative completion bound after reading the actual canonical inputs |
| admitted_at / decision_at | The explicit owner identity decision, following required knowledge |
| known_at | The same decision bound sealed into this relation |
| valid_from | Admission's UTC date, never a historical listing or bar date |
| valid_to | Open prospectively; no copied option-root next-day expiry |
| canonical_reference_preimage | Exact sizes and digests of the pre-intake five tables and receipt |

A dry run returns the proposed decision without publishing it. An actual
publication requires the owner to finish writing the reviewed output and the
ordinary repository delivery chain.

The legacy builder's generated_at and alias ingested_at are not completed
publication clocks. Its sequential table/receipt writer does not attest an
atomic generation. This increment introduces no such claim.

Generic Yahoo AliasRow resolution does not enforce known_at, including when
decision_at is supplied. Therefore this alias alone must not qualify SPY's
history. A separate closed materializer must consume and validate the retained
receipt, its sealed relation, the current target, exact reference bytes and an
actual later materialization cutoff. That cutoff must be no earlier than the
price observation, source availability, admission and completed reference read.
A previously captured price response may be assessed later under CURRENT;
price observed_at must not be misused as the admission/publication clock.

The current ordinary stock materializer still requires both store and
yahoo_fetch to identify the same listing. This intake creates no store relation
and does not activate the SPY exception in that consumer.

## Whole-builder preservation and operation

The ordinary builder and its existing native-history refusal remain in control.
The explicit intake cannot be combined with the other reference intakes or
--nightly. It follows the normal current-rail validation and strict bounded-delta
checks, with exactly one Yahoo relation as its permitted delta.

Every prior alias and all four other reference tables must be preserved.
Existing prospective-reference, direct-registrant and option-root evidence stays
retained. A replay, missing retained evidence, altered binding, conflicting
existing Yahoo relation or canonical input changing during preparation/before
publication refuses. A shared pure semantic check runs during construction,
completed-preimage preparation and ordinary retention. It checks all required
source facts and clocks, the exact six-file preimage grammar and the current
unique active target before the evidence/alias seal comparison. Recomputing a
seal does not make incomplete or contradictory evidence valid. A changed or
retired target requires explicit curation of both retained SPY relation families;
this intake introduces no retirement mechanism.

Unrelated ordinary rail changes must be reconciled through the existing
ordinary writer before this bounded intake can proceed. They are not filtered
away to force the one-alias result. The pre-write checks are not an atomic
cross-process lock; the caller retains exclusive ownership of its output scope.

Review in an admitted isolated workspace with the actual data inputs present:

    python3 scripts/build_security_master.py --out data/reference \
      --spy-yahoo-catalog-evidence PATH/spy-yahoo-input.json --dry-run --report

Only after inspecting that exact result should the same explicit owner write
the reviewed output in its isolated scope. Do not run a subset Terminal data
producer against the production full-universe manifest.

## Verification and actual evidence frontier

The hardened combined run passed **406 tests** across the new SPY catalog
intake, existing direct-registrant intake and prospective-reference suite
(39.24 seconds; process exit 0). These use synthetic captures and original
receipt-owner generation in isolated test directories; they are not market
evidence.

Native C3 supplied-source review initially found two essential corrections:
resealed incomplete evidence passed retention, and ambiguous hidden/section
markup could be accepted. The corrected source was independently re-reviewed
using actual source excerpts measured by root as complete builder SHA-256
1a684ee86d0ee102f237ba4d55b4611f336113a97af2227873f1f1a25278f118.
Both source-level findings were closed. The reviewer did not independently
retrieve/hash the entire source or execute tests. The new adversarial tests
recompute both evidence and alias seals, rebind mutated HTTP bytes, and require
refusal before writes. They also test missing, duplicated, retired and changed
current targets.

The original October 19 issuer HTML passed the tightened parser. The actual
real-input CLI dry run completed successfully from 11:23:47.136186 to
11:23:55.092085 UTC, with all six canonical reference files byte-for-byte
unchanged. That proposed result is not an actual admission clock.

Captured Yahoo response: 1,304 bytes,
SHA-256 582f530ce2fb6fcf2e76901d60e9e5d275b404838c901d26062c8eca2f1fe82b.
Captured issuer response: 237,722 bytes,
SHA-256 dc4629144270ddc31b93e05dd0a3e772b89998c6a05828559eebf47074b75b38.

The unmodified SymbolDirectoryAdapter completed the actual October 19 listing
collection at 2026-10-19T08:27:52.695357Z. Its original eligible completion
receipt binds 13,304 rows and 364,452 bytes; snapshot SHA-256:
36f549fc68cb28186602fb26b2c5d78ce56db9bf572c8d55fd2d39e63574e0e1.
Original receipt SHA-256:
d1a87f086e7884f1c2717ab5be5a17b5bd94bd706ffa4eaaf623d9b3e4e1b4f1.
The collector also emitted its ordinary current CIK map and receipt. No old
receipt was relabeled and no collector code was changed.

The first real bounded dry run refused an unrelated ordinary issuer-table
difference. An isolated whole-builder proposal identified exactly one field
change: ISS:US-XNAS-QRVO legal_name changes from Qorvo, Inc. to null because
the current SEC map does not supply that name. This is a nullable current name
absence, not evidence of delisting, migration or another security-state change.

The reviewed ordinary refresh was then actually applied through the existing
whole builder in the owned worktree. It started at 10:54:31.605051 UTC and its
completed writes were observed at 10:54:33.930459 UTC. All five tables matched
the reviewed proposal exactly. Security rows, aliases and both migration tables
were unchanged; prior prospective-reference, direct-registrant and option-root
evidence was preserved. issuer_master.parquet changed from SHA-256
b6a49be4a256b0a62ed0406c36030ca7cf341b56f89610735cf0844fd0782746 to
2b7a6dcf213be446483cd4803e312926e363b62f2db0695a1452a6f334e508e6.
This is a local ordinary refresh, not SPY admission or production publication;
the legacy writer supplies no atomic-generation attestation.

A broader reference/stock run after that refresh passed 280 tests and failed
four. The two earlier mixed-generation failures were resolved. Two retained
failures assert an old SPY refusal as permanent absence and treat a logical
private company-intelligence store as a repository filesystem path. Two other
legacy assertions cap unresolved coverage at 16; the actual refreshed report
contains 17. An exact unchanged a380 builder control reproduced all four on
the same refreshed inputs (41.81 seconds). Its source SHA-256 was
c54e71371e80e5eb7d62ab4f9ed67e72494e916050ff266e78c01f3f867ee824.
No existing assertion was weakened, skipped or removed. The 406 passing intake
tests do not replace these broader gate obligations.

## Actual bounded admission — 2026-10-19

The reviewed implementation and ordinary inputs were committed first at
cd67e7d2025ceae95583505063eaa8f905c3952b. The existing owner then admitted the
one Yahoo relation with that exact code_version:

| Fact | Actual value |
| --- | --- |
| Relation | yahoo_fetch/SPY to SEC:US-ARCX-SPY |
| Current relation valid_from | 2026-10-19 |
| Required sources available | 2026-10-19T08:27:52.695357+00:00 |
| Admission reference read complete | 2026-10-19T11:39:12.998214+00:00 |
| Decision / admission / known_at | 2026-10-19T11:39:12.998232+00:00 |
| Alias rows before / after | 8,926 / 8,927 |
| Evidence SHA-256 | 2a1570ec0e11663b5e3d4e4da0138c660603815d69a7e31640cc99ec9ccbf7de |
| Alias binding SHA-256 | efe9aa30a8c4a781cc411f796cd9f16dd3397ab094a82ae3c1e2e3e72ccf3f35 |

Every prior alias was preserved and all four other reference tables stayed
byte-identical. The original prospective-reference, direct-registrant and
option-root evidence also remained unchanged. No stock-store alias was added.

Actual output vendor_aliases.parquet is 71,186 bytes, SHA-256
d240db4fb7c49d21d389f02ed7d395be83f3b7bd46ac28cbfec16c03ff32d3f8.
Actual output _receipt.json is 42,916 bytes, SHA-256
263728d5ba2cddd21b5d3a267f8ed4a4d14924f2c4781ff8d286744204805135.

The owner command returned successfully. A post-write evidence wrapper then
assumed a nested receipt field and failed after its exact-delta assertions.
A same-carrier read-only reconciliation validated the actual flat receipt,
alias seal and all preserved tables; the owner write was not repeated.
The log written after the successful command supplies a conservative completion
upper bound of 11:39:24.196095 UTC, not an atomic publication clock.
A subsequent ordinary dry run passed and left all six files unchanged,
observed at 11:45:08.197101 UTC.

This admission is local to the owned delivery branch. Repository acceptance,
installed-owner activation and the separate closed SPY price consumer remain
required. It does not qualify adjusted history by itself. No production data
was changed, and the frozen Returns predictive candidate remains withheld.


## Named Terminal consumer and shared validation — 2026-10-20

The admission artifacts are published on this delivery branch at
`dfe18ee874dc259deb08ec01d86bd43283dd75de`. This is repository-branch
publication; protected-branch acceptance and installed-owner activation remain
separate. The original evidence bytes, alias seal and admission clocks above
are unchanged.

`lib/dataos/_spy_yahoo_catalog.py` now owns the pure retained-catalog grammar,
canonical evidence encoding and six-file admission preimage checks. The
builder re-exports its existing constants and preserves its callable wrappers;
its three ordinary Parquet normalization/read functions are AST-identical.
Source acquisition and the explicit write-capable admission entry point remain
in the existing builder. The shared module performs no I/O.

The shared grammar also refuses canonical target timestamps with precision
finer than a microsecond. Two resealed counterexamples showed that Python's
normal timestamp parsing could otherwise truncate one nanosecond across the
original reference-read cutoff or across effective/ingested ordering. Existing
whole-second and exact microsecond forms remain supported. This does not alter
the already admitted target or its evidence digest.

The new `bind_terminal_spy_yahoo_materialization` leaf has its own schema,
`dataos.terminal_spy_yahoo_materialization.v1`. It requires positive retained
catalog evidence, the real canonical Yahoo alias and seal, and the current
master/aliases/receipt triplet. It keeps the original six-file admission
preimage separate from this later consumer read. Its owner source profile adds
the shared helper's actual hash; the ordinary stock profile remains the
existing two-file profile and its complete golden output is unchanged.

Price observation and current qualification are independent clocks. The last
bar must be valid at its original observation in New York session time. The
current reference read must occur at or after catalog admission. Materialization
must follow observation, source availability, admission and that current read.
The catalog date is evaluated in UTC even when a materialization timestamp uses
a western offset. Unsupported clock precision refuses; it is never rounded
into availability.

SPY cannot qualify through the stock leaf by forging a store alias or by
relabelling a request/output symbol, resolved security ID, listing key or
inception code. A missing or invalid named SPY qualification cannot fall back
to ordinary stock qualification. The new contract remains CURRENT, with
historical availability, adjustment vintage and atomic reference generation
unattested. It supplies no predictive admission.

Actual pytest execution in the owned M2 repository passed **522 tests** across
`test_dataos_spy_yahoo_catalog.py`, `test_dataos_direct_registrant.py`,
`test_dataos_prospective_reference.py`, `test_emit_view_contract.py` and the new
`test_terminal_spy_yahoo_materialization.py` (40.94 seconds, exit 0). This includes
44 new closed-consumer cases using synthetic facts and the real canonical
identity reader and seal. Two pytest cleanup warnings concern an unrelated
retained browser-fixture directory; no assertion failed.

The extracted builder's actual ordinary CLI dry run also passed (exit 0).
All six canonical file SHA-256 values before and after were identical, including
the original `2a1570ec...7de` evidence and `efe9aa30...f35` alias seal already
bound by the receipt. The source builder SHA-256 for this run was
`4d2fc311ca2beabc6e95dc53f93443aecba114eb4c3169097c5a869f54b3fbac`.

The new catalog suite is enrolled in the existing prospective-reference CI job;
the named consumer suite is enrolled in the existing C04 identity-seams job.
The previously documented four broader reference/stock failures remain distinct
obligations. These focused passing tests do not classify them as waived.

The proposed Terminal adapter and browser/API reader activation are separate
consumer delivery work. This section does not assert their production use or
that an adjusted historical series has acquired point-in-time provenance.


### 2026-10-20 recovery: retained reference-read precision

Recovery review reproduced an additional precision hole in the shared retained
catalog validator at `d24ee29c2c6c0582514b602245993122ebcb4a93`. A resealed
`reference_read_completed_at` one nanosecond after admission was accepted when
Python truncated the clock to microseconds. Both dot and comma fractional
forms reproduced the failure. The named Terminal SPY materializer already
refused these inputs with `MATERIALIZATION_CLOCK_INVALID`; this finding does
not establish an incorrectly qualified live price artifact.

The repair reuses the existing strict capture-clock grammar for the retained
reference-read clock. It does not change the general clock parser or the
ordinary stock materializer. Two negative regression cases failed before the
repair, while the exact microsecond admission/read boundary passed. After the
repair, the original five-file selection above plus the three new regressions
passed **525 tests** in an actual owned-workspace run (160.88 seconds, exit 0;
`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q
 tests/test_dataos_spy_yahoo_catalog.py tests/test_dataos_direct_registrant.py
 tests/test_dataos_prospective_reference.py tests/test_emit_view_contract.py
 tests/test_terminal_spy_yahoo_materialization.py -p no:cacheprovider
 --basetemp=/tmp/returns-spy-clock-recovery-20261020-pytest`).

The named consumer now reports `MATERIALIZATION_SPY_CATALOG_INVALID` for these
malformed retained clocks because shared catalog validation refuses them before
the materializer's separate publication-clock checks. The refusal outcome is
preserved; the two negative regressions now assert that exact code as well as
shared-validator rejection. An actual focused run of those two cases and the
valid boundary passed **3 tests** (5.63 seconds, exit 0).

### 2026-10-20 recovery: independent review and CI registration

The bounded independent review `returns-intelligence-20261018-spy-contract-review-d24-clock-20261020-v1`
reproduced the helper patch from the published d24 source and matched SHA-256
`6e635a475bb480428e88ea6bbc70a87adb087cf3ac08737bc6ca6833df7b2c80`.
Its separate scratch execution passed all **47** named materialization tests;
it did not rerun the parent's 525-test selection. The parent accepted its
scoped semantic review with response SHA-256
`409097f935bddc8db4885d69859a26a716f89e34429c3c6c9c46975a5b2c9b4e`.
The refusal-code finding above is addressed. The review is not approval of the
later CI manifest repair, a future integrated head, or production release.

Hosted d24 run `39375204727` exposed 15 import-closure omissions and a
three-unit packing increase: the new pytest invocation contributed one command
unit and its explicit test path contributed two units. The manifest now names
the shared helper in the 14 affected exclusive jobs and the dataset registry in
`gmi-classification-axes`. Every existing declared path remains.

The six contiguous pytest invocations in `dataos-identity-seams` use identical
dependencies, environment and flags. They now share one invocation with all six
test paths explicit and in their original order. No tests, jobs, thresholds,
timeouts or dependency settings were removed or relaxed. This removes five
interpreter starts; the estimator retains all six test-path contributions.
Its C04 weight changes from 19 to 14 (run commands 7 to 2, six explicit paths,
command-length contribution zero on both sides). This is estimator accounting,
not a claim of five measured seconds saved.

Actual owned-workspace verification:

- The complete combined six-suite invocation passed **249 tests**, with one
  existing strict expected failure, in 7.85 seconds, exit 0. That expected
  failure is `test_m01_adjusted_volume_is_refused_by_the_raw_view`, documenting
  the existing RAW-view volume limitation.
- `test_curated_exclusive_scopes_cover_their_own_import_closure` and
  `test_exclusive_curation_narrows_ordinary_code_prs` both passed: **2 tests**
  in 246.66 seconds, exit 0.
- The later refusal-code assertion change passed the focused three-case run
  above and did not change helper or materializer code.

The stock owner PR #9619 merged at
`ed72c2dc83997bea51e64efd9014f30b882b8a76`. The SPY branch still needs explicit
integration with current protected main, including the materializer add/add
resolution, followed by review and hosted checks on that integrated source.
These local results do not establish current-base or hosted CI success.

The four broader failures remain in `tests/test_dataos_security_master.py`:
`test_receipt_carries_the_security_axis_block`,
`test_every_produced_row_names_a_real_store_and_a_real_producer`,
`test_us_coverage_scope_holds_through_lawful_admissions`, and
`test_gmi_us_regression_bands_cn_hk_and_legacy_us`.
The precision and CI registration repairs do not waive them or raise a ceiling.

Draft PR #9835 remains held for protected-base integration, review and hosted
checks on that source, publication of the closed Terminal consumer, and
installed-owner/live proof. The original admission clocks, evidence and scope
remain authoritative, and predictive probabilities remain withheld.


### 2026-10-20 recovery: integration with main ef9bcbb6

The original SPY branch integrated exact main
`ef9bcbb6aec7defb5044a1110e442c91f0e4408f`, which contains the stock-owner merge.
The materializer add/add was resolved only after comparing the incoming
`b2815a4700583ef697e9190ac08a90eedd96cf9c` stock-owner blob with the reviewed SPY
extension. The resolved materializer is unchanged from the reviewed SPY source
(SHA-256 `7cc89bcf499e69fff9eaa88783b4f2a4593d373997ad7e3219e48f2fd5bb050b`).
The shared helper and its precision fix are unchanged.

The CI conflict preserved the incoming `jsonschema` dependency and all five
new SEC identity suites as their original separate invocation. It also preserved
the six explicit Returns/identity suites in the consolidated invocation. Every
named main test remains registered, all C04 paths from both parents survive,
and the two new SPY suites remain registered. The resolved manifest SHA-256 is
`1d12bd060f9807a1176ef567ffa35c23357567113755b029c2c34d5525db23d8`.
The registry merged to the exact incoming main blob
`2c17ab49dc1c972bb2fa8e9b80b6ae5b77db8159`; the stock golden and emitter tests
retain blobs `f82b11c1ef5fa49bc4d16a2e81a3515f20d7c3d1` and
`de463ff90a0cd033805f10fa562b203ef84995e5`.

Actual integrated-source execution in the original workspace:

- Incoming SEC identity group: **140 tests and 14 subtests passed**, 10.24 seconds.
- Consolidated C04 group: **255 passed, one existing strict expected failure**,
  8.13 seconds. The additional six passes are incoming main coverage.
- Shared SPY catalog, direct registrant and prospective-reference group:
  **406 passed**, 44.47 seconds.
- The two import-closure/packing tests: **2 passed**, 201.92 seconds.
- Candidate diff/whitespace check against incoming main: exit 0. A first check
  against the old branch parent also encountered existing incoming-main
  whitespace in unrelated generated/site files; those bytes were preserved.

The four named broader security-master assertions were rerun on this integrated
source and still failed (21.65 seconds). The findings are a retained historical
SPY refusal being interpreted as a permanent current-identity prohibition, a
`private:company-intelligence/...` storage address being treated as a checkout
path, and the same unresolved count of 17 exceeding two existing ceilings of 16.
No gate was waived, no ceiling raised, and no reference artifact was rewritten
to force a pass. Corrective owner evidence and review remain required.

This integration preserves real merge ancestry. Hosted CI and independent
review must evaluate the resulting published source before the draft release
hold can be reconsidered; these local results are not production proof.


### 2026-10-20 recovery: identity integration with main 3dc26674

The original branch integrated exact main
`3dc26674901a53bc03ac209906fbc49a42567308` into published parent
`8716552c3020e9cb71efef02e3c1e99a1fc22674`. Main now includes #9649
(`877702bfd078a9d40f0dc3ea408726302278c442`): TXSE, paired KHC/ET venue
transfers, attributed DOMO/HUCK and YYGH/YFOR renames, acquisition exits, and
the correction that distinguishes retained historical refusals from later
BOUND direct-registrant evidence. The source and CI manifest merged normally.

#### Reference history reconciliation

The committed parent records were compared before resolving the three generated
file conflicts. All 3,105 prior security rows survive exactly in main's 3,106-row
master; main's only additional identity is `SEC:US-TXSE-TCBI`, admitted at
`2026-10-19T06:10:18`. The issuer and security migration records match exactly.
The aliases shared by both parents match on every field. Main contributes
exactly four TCBI aliases; the SPY parent contributes exactly one sealed
`yahoo_fetch/SPY` relation.

Those already-committed, nonconflicting alias records were deduplicated on
the declared grain, checked for exact equality on every shared key, and passed
through the incumbent `merge_alias_rows` with no fresh admissions. The canonical
builder then performed one complete build using those predecessor records,
main's canonical master/migrations, the retained SPY receipt and the current
2026-10-19 directory/CIK inputs. No source observation was replayed or resealed.

The rebuild preserves every parent alias field and timestamp, every canonical
security field, both migration histories, and the complete retained
`prospective_reference`, `direct_registrant_intake`, `spy_option_root` and
`spy_yahoo_catalog` documents. SPY evidence remains
`2a1570ec0e11663b5e3d4e4da0138c660603815d69a7e31640cc99ec9ccbf7de`,
with binding
`efe9aa30a8c4a781cc411f796cd9f16dd3397ab094a82ae3c1e2e3e72ccf3f35`.

No new security was minted by the combined build. The current CECO and IBOC
venue changes remain explicit pending-transition refusals; the builder did not
invent transfers. Coverage is **1,624 resolved / 1,636 total / 12 unresolved**.
Both existing unresolved ceilings remain 16. The output has 3,106 securities,
1,932 issuers, 8,931 aliases, three issuer migrations and one security migration.

The resolved receipt, issuer master and aliases are whole-builder outputs.
The semantically unchanged security master and migration files retain exact
main bytes. An initial byte-level comparison of regenerated migration Parquets
failed; comparison through the canonical reader proved every field and
timestamp unchanged, so those existing main artifacts were preserved.

| Integrated file | SHA-256 |
| --- | --- |
| `scripts/build_security_master.py` | `f57cb5687495b9fcd9fd93e171ca3518df3d9d7d1336c4590500b7dab7e21d0b` |
| `.github/ci/legacy-jobs.yml` | `14704614244ef3a3891451e9c01a77fd91d618e69149f0bc238749e2919ebe5a` |
| `tests/test_dataos_security_master.py` | `95685b7fe34b6fed1b8db067a728635b04130e2ccbfa669d332a50272dc84322` |
| `data/reference/_receipt.json` | `c7ea9058c1ecd1bc6148d6ce8254c15e3b6476a386576486a6b78c6bfa20602d` |
| `data/reference/issuer_master.parquet` | `f5d669926e166f258e5a81c12565f6860bf516a2c0fe2db88e071a1f4c7739b0` |
| `data/reference/vendor_aliases.parquet` | `208493872db9485f75a6fa4e797afa1e6c92896553479ceb011aa4154e472e41` |

The reviewed SPY helper remains SHA-256
`6e635a475bb480428e88ea6bbc70a87adb087cf3ac08737bc6ca6833df7b2c80`;
the materializer remains
`7cc89bcf499e69fff9eaa88783b4f2a4593d373997ad7e3219e48f2fd5bb050b`.

#### Actual verification and the remaining global-test failure

The combined fifteen-suite owner run completed with **1,008 passed, two failed,
one existing strict expected failure, and 14 subtests passed** in 189.32 seconds.
It included the complete security-master suite, the three SPY/direct/prospective
suites, six C04 suites and five SEC identity suites. This was not an all-green run.

The receipt failure now arose from a distinct integration mismatch: `lost_rows`
contains immutable security IDs whose inception codes remain DOMO and YYGH,
while the documented continuity census uses current symbols HUCK and YFOR.
The comparison now resolves those rows through the owner's current-symbol
function and still requires exact set equality, real active identities, distinct
lost rows, typed refusals and unminted refused listing keys. The existing
historical-refusal / later-BOUND test correction from main remains intact.
That corrected test and both coverage tests then passed: **3 passed** in
3.92 seconds. No coverage assertion was relaxed.

The two actual import-closure and packing tests passed: **2 passed** in
210.42 seconds. The named suite paths and dependency closure are retained;
no packing ceiling, job condition, timeout or threshold was relaxed.

`test_every_produced_row_names_a_real_store_and_a_real_producer` remains a
reported failure. Its function and the company-intelligence registry row are
unchanged from main 3dc26674. The test interprets the closed
`private:company-intelligence/state/generations/{sha256}.json` address as a
path below this checkout. The registry instead records a real, source-owner
accepted STAGE generation, with separate serving/adoption requirements.
The exact retained operation, outcome, manifest and parent acceptance were
read and their hashes and bindings checked against
`research/theme_graph/issuer_disclosures_20261011/real_stage_20261012/README.md`.
They agree on generation
`05811e172eda94d6d07e63ad151284317d68af3781c6635150a586dfedbb22d0`,
status `MEMBERS_OBSERVED_NOT_ADOPTED`, manifest written, no current pointer
written, and no production acceptance. This is evidence of that accepted stage;
it does not establish present private-store availability.

The only legacy invocation of this global suite is `house-law-registry`, whose
`if: ${{ false }}` condition is identical in main and this branch. This inherited
cross-host path assumption is recorded for its test owner; it is not an active
SPY release gate and no assertion, dataset status or producer was changed to
hide it. The ordinary hosted gates, independent integration review and actual
installed-owner/consumer qualification remain required.

PR #9835 remains draft at this checkpoint. The independent 8716552 integration
review is still outstanding; its result must be reconciled with this later main
integration. Terminal #1043 retains its separately recorded UNKNOWN original
push and has not been republished. Forecast probabilities remain withheld.

# BEA GVC — GMI current-descriptive consumer candidate

**Status: CODED / SYNTHETICALLY TESTED / SOURCE NOT ADMITTED / PUBLIC ROUTE NOT INSTALLED.**

Dependencies: Macro PR #9433 is the scoped first-party BEA source-purpose decision and proposed L0/L1 registry contract. Macro PR #9444 supplies offline original-byte candidates and full 138-view staging/index comparators. Their DRAFT/HOLD, rights and source-access gates are not bypassed by this leaf.

## Consumer contract

The read-only `engine/market_ontology/bea_gvc_current.py` projection uses the EXISTING `lib.dataos.registry.Registry` as source and rights owner. It requires exact BEA L0 and L1 IDs, L1→L0 dependency, owner, layer, PRODUCED status, scoped license, separately granted rights and decision references. A missing or PROPOSED source is refused before opening or parsing supplied bytes.

A caller then supplies an exact industry JSONL buffer and independently expected SHA-256, owner generation, native UTC ingestion instant and revision. These caller inputs are NOT an authenticated Data OS receipt; a claimed digest or positive row flags do not establish source custody, rights, native clocks or publication authority. The actual Data OS owner must independently qualify and bind its original L0, retained corrections and L1 transaction before the app uses any such read.

The projection verifies eight accounting years (2017–2024), 139 unique commodities per year, exact source codes, consistent order, **all nine exact BEA original-response table digests and corresponding capture-receipt digests per accounting year**, unchanging source-lineage/producer identity, signed dollar-million regional accounting, May 21 2026 edition DAY precision, missing historical first-known clocks, aligned generations/native observation and non-ranking/non-trading/non-company flags. It retains negative geographic adjustments and unresolved 5241X-vs-5241XX identity. It emits yearly descriptive aggregates sorted by accounting year, never magnitude. These digest strings cannot themselves authenticate original files: the Data OS owner must do that.

Every result is typed UNAVAILABLE or CANDIDATE_NOT_PUBLISHED with authority ceiling internal_descriptive_candidate_only and may_publish=false. Canonical packet bytes are deterministic for a prospective human/machine adapter but remain nonpublic. The consumer does not authenticate a subscriber, install an HTTP route, create a graph node/edge, use market prices or generate trade signals. Market Ontology exposure-map graph/rights owners are untouched.

## Verification and CI

`tests/test_bea_gvc_current_descriptive.py` uses synthetic fixtures exclusively, including a hypothetical PRODUCED registry (not an actual source receipt). Refusal tests include missing/proposed status before byte touch, contract/rights failures, mixed generation, missing PIT, invalid UTC clock, forged publication, unsigned amounts, duplicate/incomplete/drifting commodity rows, and untrusted source hashes. This file neither reads real BEA original responses nor validates their private source axes.

The existing CI manifest will run these tests as a scoped code-gate job rather than adding an independent workflow. Test discovery and packing constraints are validated explicitly. No previously denied original Use-axis/read-workbook operation, local registry-validation operation, private research view or rights inquiry is replayed.

## Verified local boundaries (October 15 continuation)

- On initial published PR #9494 head `2d66ce52589b7d47d54a8b9a9126aa4f4d86597f`, nine hermetic consumer tests passed, exercising all eight yearly aggregates, non-admitted packet serialization, invalid-status/rights/identity/provenance/clock/grain/rounding refusals, and original nine-table/capture receipt lineage consistency. This is all SYNTHETIC source data.
- The GMI consumer suite is discoverable by the incumbent CI inventory once staged in Git. The new additive code job was inferred as scoped to 23 source/test paths with eight conservative fallback paths; it was selected by all three relevant source/test/library probes and excluded from unrelated homepage, content-builder and Prophet probes (unchanged totals 136/134/129).
- Four focused incumbent CI packing/curated-closure regressions passed, and manifest fragment validation passed with 320 logical jobs / 322 fragments. None of these checks supplies missing native source, formal independent review, public runtime or browser acceptance. This new branch still requires exact-head hosted CI.

## Retrospective accounting and quality amendment — October 16

The source-row aggregator now carries the publisher's **signed rounding residual**
into annual totals, counts per-year commodities with nonpositive world imports,
negative regional adjustments and nonzero residuals, and verifies that each
row's exact `quality_flags` matches the signed amounts. It computes signed
year-over-year differences from the **same retrospective May-2026 edition**,
leaving 2017's unavailable comparison as null. The declared comparison basis is
`RETROSPECTIVE_2026_VINTAGE_NOT_ORIGINAL_HISTORICAL_KNOWLEDGE`, not historical
point-in-time eligibility or an entry/ranking signal. No ratios/shares are
manufactured from nonpositive signed denominators.

Raw amounts, annual sums and interyear differences must fit the exact integer
range safe for JSON/JavaScript consumers (±2^53−1); out-of-range values yield
typed unavailability, rather than silently rounding browser values. Initial
new tests failed before implementation, then the amended hermetic suite passed
13/13. The resulting private packet continues to carry `may_publish=false`,
and retains all existing nine-table source/capture lineage and owner-receipt
authentication caveats. Neither Data OS native installation nor real-browser
delivery was attempted.

## Cross-branch synthetic compatibility — October 16

A read-only, no-file-write local probe loaded **only hermetic fixtures and code**
from native candidate branch `22f86b841389b6c7b7fc336cdd43ce066b615421`.
It generated the full synthetic 72-response, 2017–2024 candidate and its 1,112-row
`5241X` native exporter JSONL. In memory only, a hypothetical PRODUCED
registry plus current UTC ingest/revision and row admission flags were injected
to test **schema interoperability** with this GMI candidate. The consumer
confirmed eight accounting years, world imports +3 and Canada -2 (USD millions)
in the first synthetic year, 138 nonpositive-world commodity rows, consistent
digests/generation and zero region rounding. It still returned
`CANDIDATE_NOT_PUBLISHED`, `may_publish=false` and
`historical_pit_eligible=false`.

This is **NOT** a real native promotion, original-source read, accepted registry
snapshot, authenticated owner receipt, licensed production delivery, or historical
known-at evidence. The synthetic admission fields and claimed byte digest are
caller-created test inputs; they cannot authenticate the source. The consumer
does not import the unmerged native code and remains independently scoped to
existing Data OS interfaces.

## Exact source-purpose rights admission hardening — October 16

Independent hypothetical `PRODUCED` test contracts now qualify the BEA family
only when all **three independent rights** (purchase/access, internal computation,
redistribution) are granted under the exact decision
`DEC:GMI-BEA-GVC-SCOPED-SOURCE-PURPOSE-20261014` on both L0 and L1. Merely
presenting an unrelated `DEC:`-prefixed evidence key or a missing/denied
purchase-access right is a typed refusal **before source bytes are read**.
This does not override owner source custody or elevate a proposed dataset.

A dedicated adversarial rights test initially failed against the former loose
reference check and then passed after the exact-decision fix; the **14-test**
consumer suite passed. No previously refused `PLANNED_NOT_INSTALLED` producer
edit was retried or substituted, and no real source files, website or entitlement
systems were touched. Fresh hosted CI and independent review of the revised
consumer head remain separate from local tests.

## Publisher industry labels without silent crosswalk — October 16

The current-descriptive leaf now verifies nonempty, bounded, no-control-character
publisher `industry_name` strings within each accounting year. It retains exact
`industry_names_by_accounting_year` across 2017–2024; when all eight years
share the same label, `industry_display_name` is that original publisher label
with state `EXACT_SOURCE_LABEL_STABLE`. If names vary between years, the
single display label is **null**, state
`SOURCE_LABELS_VARY_ACROSS_YEARS`, and the original year-specific names
remain visible for an eventual authorized human view. Divergent names **within
one accounting year** fail closed instead of silently choosing a synonym.

The exact code namespace is unchanged, and no implicit `5241X`/`5241XX`
concordance or company relationship was minted. A new hermetic test failed
before the source change and passed afterward; the amended local suite
completed **15 tests**. Product/admission status remains
`CANDIDATE_NOT_PUBLISHED` under the same source gate and rights decision.

## Authenticated application availability boundary — October 17

The incumbent Macro FastAPI application now includes an additive
`GET /api/gmi/bea/industry/{industry_code}` endpoint. It reuses only the
existing `require_site_full_user` dependency (which uses the existing
Supabase `require_user` identity resolution and `enforce_site_full` site
entitlement), plus `lib.dataos.registry.load_registry`; it does **not**
create a second auth, rights, source-state or cache plane. The handler checks
canonical registry contracts and rights but intentionally has no
native original-byte reader binding. Its only data result is a **503 typed
UNAVAILABLE packet**, with `private, no-store`. If the canonical registry
cannot be loaded it responds 503 with a coarsened source error; unsafe source
code is 422; unauthenticated requests 401; users refused by the existing
paid gate 403. It refuses unsafe exact source codes **before the registry
read**. It never returns annual rows, even with a synthetic test that bypasses
the registry status gate: owner-bound original bytes are still absent.
The route is source
code on an unmerged draft branch; no deployed browser/session proof exists.

The `candidate_packet_bytes` helper now validates two **closed** output
shapes. A typed unavailability cannot carry source rows, a generation, native
clock or hidden additional fields, and must use the closed source refusal
vocabulary. A candidate must remain `CANDIDATE_NOT_PUBLISHED`, preserve
non-trading/non-ranking and historic-known-at limits, exact-source labels,
per-year signed aggregate accounting and year-over-year values, and all
retained source hash/metadata fields. Forged `DESCRIPTIVE`, `may_rank`,
`may_trade`, `historical_pit_eligible`, hidden secrets, private file paths,
altered annual values and label/availability leakage fail closed.
This is **structural integrity, NOT cryptographic source authentication**.
It does not convert a source-candidate digest into a production entitlement.

Test-first verification: the new machine serialization tests initially
failed on the old helper; four initial API tests failed with 404 because the
route did not exist, and a later unsafe-code test first returned 503 rather
than the required 422. After correction the combined source/HTTP/paywall/cache
contract suites passed **35 tests** locally, including tests for canonical
payload bytes, paid-site rejection, simulated source-status promotion still
returning no data, coarsened filesystem errors, and invalid codes rejected
before any registry read. Shared application/CI packing and exact-head hosted
CI remain separate gates. No original private BEA response was opened,
previously denied access/producer-string edit replayed, source installed,
PR merged or deployment attempted.

## Current-only API request fence — October 17

The authenticated `GET /api/gmi/bea/industry/{industry_code}` now rejects
**every query parameter** before reading the canonical registry. This is
deliberate: `?year=2019`, `?as_of=2018-01-01`, `?known_at=...` or an
unrecognized `?format=` must never silently receive the May-2026 current
vintage under a false point-in-time expectation. There is no historical
temporal mode or approved crosswalk in this endpoint. The source code is
validated first and entitlement still uses the existing Supabase/site-full
dependency; 422 responses inherit `private,no-store`.

The adversarial regression initially reproduced 503/registry access for
`?known_at=2018-01-01` and then passed when the current-only fence was
implemented. The combined GMI, API-paywall and cache suite passed **36 tests**.
This is a product/query truthfulness improvement, not a native source
read, publication authorization or live browser proof.

## Fabric C3 security review repairs — October 17

Independent, **paid M2 Fabric review** `gmi-bea-20261017-c3-fabric-review-001`
returned a terminal, evidence-backed **REQUEST_CHANGES** verdict against
source head `17e466e3a1a7fb333d34ce657079f11f72f4ab39`. It independently
executed 28 GMI/paywall tests, reproduced the ten curated CI import-closure
defects on that exact head, and independently tested that widening those ten
job path lists resolves the blocking failure. The fix was already published
on this original branch at `8a7d8dbf85c80d837a12242da08db6755f028ded`
and validated locally against the existing two focused CI contract tests.
This is C3 labor evidence, **not formal GitHub approval**.

The reviewer also reproduced defense-in-depth issues. The current source
branch now reuses `enforce_site_full(user, always=True)` on the GMI route,
so an actual free-tier session is refused 403 even when
`PAYWALL_ENABLED=0`. No second entitlement plane exists; test fixtures
use the incumbent `_store_entitlement` source and exercise both paid and
free states. Host-side source/candidate failures are separately coarsened to
503 with a bounded exception **type-only** log entry, never 422 blaming the
client or exposing private source paths. Name and packet validation refuses
lone Unicode surrogates, bidi overrides, zero-width format controls and C0
characters; JSON serialization escapes non-ASCII safely. Machine packet
validation additionally checks that the absolute signed **annual** rounding
residual cannot exceed 3 per commodity with a rounding flag and pins the
May-2026 source commodity-axis expectation as `COMMODITIES_PER_YEAR=139`.
No token aliasing, historical PIT, rights or trade authorizations were
weakened. New adversarial tests first failed on the old implementation,
then passed after fixing the root defects.

The combined GMI leaf, API-paywall and API-no-store suites passed
**40 tests** locally. The remaining nonblocking performance issue
(an uncached canonical registry YAML read on paid GMI availability requests)
is not treated as an alternate source/status owner; optimizations must
preserve timely native revocation and owner decision evidence. The
original-source axes denied by platform safety were **not** re-read.
An exact-head hosted CI and current-head independent review remain distinct
release gates.

## Paid human inspection surface — October 17

The existing Macro API now has a **source-free, light-first human view** for
`GET /api/gmi/bea/industry/{industry_code}/view` and its fixed browser asset
`GET /api/gmi/bea/assets/view.js`. Both reuse the same existing Supabase
identity and `enforce_site_full(user, always=True)` entitlement as the
underlying industry-data endpoint. They carry `private,no-store`;
the HTML uses a same-origin-script/connect CSP, disabled framing, no
external imagery/fonts and no user interpolated source string. There is
no new auth or data service, no browser-local copy of provider bytes, and
no generated public static mirror of the BEA source.

The new view is built for **one exact source industry code** (strict syntax
on both URL and form), has an eight-year accounting selector, world/Canada/YoY
summary slots, seven signed regional bars, and a retrospective timeline
that refuses to misrepresent negative world values as upward bars. All UI
strings are inserted through `textContent`, never HTML fragments from source
rows. Normal default state is **Not yet available** and no KPI, region or
history is rendered while native L0/L1 is unproduced. The browser only
consumes the same canonical API endpoint; it never reads retained BEA files.

For a future owner-qualified data response, the browser contract requires
an explicit server-minted `PUBLISHED_CURRENT_DESCRIPTIVE` status with
`may_publish=true`, `dataos_native_admitted=true`, matching exact source
code, source generation, 2026-05-21 edition, retrospective method, no trading
authority and eight complete JSON-safe accounting years. **No such status
exists or is returned by the current source-guarded endpoint.** This
browser-side shape check is *not* authorization or an alternate publication
control plane; native Data OS and GMI app owners must implement and accept
server-side qualification separately before any real values can be served.

**Verification:** five new TestClient tests cover paid HTML/JS delivery,
CSP/no-store, 401 unauthenticated /403 free-tier, 422 invalid code or
historical query, a source-free human shell even if the registry reader
is hostile, and typed 503/no path leakage when the fixed asset is absent.
The combined GMI/paywall/no-store suite passed **45 tests**. Source scripts
passed `node --check` and a stdlib HTML parser verified 14 unique element
IDs and one same-origin external JS asset. The source is tracked in Git and
the two focused CI curated import-closure/packing regressions passed (2/2);
the inherited manifest remains **320 logical jobs / 322 fragments**. The
two focused macro-api deploy-restart self-heal tests also passed.

Local **physical Chromium via Playwright**, with all HTTP requests
intercepted by hermetic test fixtures, passed four cases across two smoke
sessions: a 503 `SOURCE_NOT_PRODUCED` response left all figures hidden;
a clearly **synthetic future-publication-shaped** packet rendered seven
regional bars, eight retrospective history columns, publisher's exact
year-specific label, year switching and the verified generation display.
Saved Mastermind light preference overrode OS dark, and saved dark
preference overrode OS light, with actual computed browser background
colours checked. No real BEA original responses, site deployment,
live Supabase session, production browser or live API data values
were used.

The preview is an **implementation candidate** only, not installed or linked
from production navigation. It leaves existing parent adoption #9433,
native source #9444, original-axis permission holds, 5241X/5241XX
uncertainty, native timestamp/revision admission and final actual
browser+machine parity acceptance untouched.

## Production remains HELD

Real acceptance still requires lawful original 72-response L0 validation, source industry axis resolution, accepted 5241X/5241XX mapping or explicit unresolved handling, installed L0/L1 UTC ingest/revision/correction chain and registry PRODUCED promotion by the current Data OS owner. Existing app authentication and entitlement then must be proven alongside same-generation browser/API descriptive results. This candidate is not a release, approval, producer or new control plane.

## Current audit update — October 17 Pro design/architecture pass

The historical milestones above are retained as evidence, not current implementation status. See [the Pro design and architecture audit](BEA_GVC_PRO_DESIGN_ARCHITECTURE_AUDIT_20261017.md) for the present architecture and [the visual verification folder](verification/BEA_GVC_PRO_AUDIT_20261017/README.md) for before/after screenshots.

The current implementation removes the speculative published-status browser branch, uses the real nonpublic contract for isolated research-component tests, redesigns the source-safe workspace and signed charts, and moves actual HTTP/browser tests into required PR CI. **85 runtime, contract and browser tests** and **four canonical CI scope/packing/ancestor tests** passed locally. All 26 source refusal reasons have meaningful explanations, zero and negative chart values have truthful geometry, and the existing real cookie parser is exercised with explicitly mocked identity verification. No real account credentials or original BEA source files were used.

The original source-admission and production-proof obligations remain unchanged. No placeholder chart, synthetic screenshot, passing test or feature-branch merge is a native Data OS admission, protected-main merge, deployment or production acceptance.

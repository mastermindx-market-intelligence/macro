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

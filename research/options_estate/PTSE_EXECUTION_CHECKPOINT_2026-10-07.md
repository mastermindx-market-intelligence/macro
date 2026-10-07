# PTSE execution checkpoint — 2026-10-07

**Parent #7925 remains open. MISSION_COMPLETE:false / BUILT_NOT_PROVEN.**
This is a continuation of `market-tide-research-20260924-sol-001` on the existing
implementation PR #8364, from source head
`22e217a3f5ce0c27a8ad0ea0a2a9a2c9f8074ffb`. Architecture custody remains #8325;
the seven-file launch package remains pinned at
`16dcd567edebc1d1a796c3089db44a1027604425`.

## Completed source changes

Independent adversarial review demonstrated that structural hashes alone did
not stop a re-sealed shadow row from carrying contradictory fields. A directly
constructed enrollment could also bind a candidate to a different market
session or bypass the existing prospective-expiry test. These defects matter
because the row is the join boundary into the existing shared grader.

`ptse_shadow_enrollment.py` now validates actual canonical dates, typed identity
and content-address fields, the deterministic candidate source key, literal
false authority values, and the closed context-presence/status/reason matrix.
The builder requires the context session to equal the candidate stamp and calls
the existing `qualify_prospective_observation` validator before enrollment.
It does not create a second readiness rule or authenticate external source
ownership from a self-hash.

`ptse_shadow_outcome.py` now rejects malformed grade collections, malformed source
keys and noninteger/unregistered source horizons before interpreting missing
matches as PENDING. Oversized numeric grades produce a typed refusal. An honest
UNAVAILABLE-context row can still receive a matured incumbent shared grade;
missing optional context must not erase the population denominator. Shared H10,
H21, H42 and H63 outcomes do not become PTSE H5 protected research outcomes.

## Complete-stamp publication preflight

The new `ptse_w3_publication.py` is a pure, in-memory preparation boundary for
the existing publication owner. It performs no I/O and grants no write authority.

The caller supplies one complete candidate stamp, a pinned B1 snapshot returned
by the incumbent validated source reader, an external receipt manifest and its
independent digest pin, and actual canonical context bytes where available.
The candidate receipt binds the exact sorted rows supplied to the function;
if the caller uses the incumbent three-column projection, that projection must
be declared in the source receipt. It must not be presented as a raw-file digest.

Every supplied candidate receives exactly one row:

| Source condition | Packet representation |
| --- | --- |
| Exact B1 relation and admitted prospective context | ENROLLED with exact content identities |
| Exact B1 relation and missing optional context | ENROLLED with explicit UNAVAILABLE / CONTEXT_MISSING |
| Missing or ambiguous B1 relation | RELATION_REFUSED, with no fabricated B1 identity |
| Malformed source metadata, mismatched receipt or invalid enrolled context | Typed refusal of the attempted packet |

The invariant is `attempted = enrolled + relation_refused`. Any relation refusal
keeps the packet in RELATION_REFUSED status. A structurally valid retained
context on a refused relation is held evidence; it is not prospective enrollment.
All nine assessment authority bits and publication authority remain false.

The packet contains canonical immutable bytes, exact population and B1 material
digests, context content addresses, denominators and external receipt references.
Context bytes are returned separately as an immutable tuple, avoiding a second
raw candidate or B1 store. Source receipt authenticity remains the caller's
custody responsibility; a dataclass, owner name or self-consistent hash cannot
prove that an owner issued or admitted the material.

`validate_publication_packet` reconstructs every row from independently supplied
original source inputs and compares canonical bytes. `preflight_publication`
returns FIRST_PACKET for a new stamp and IDENTICAL_REPLAY for identical material.
Changed content or population returns REVISION_REFUSED with explicit lineage,
preserving the first packet bytes. Added, omitted and entirely empty replacement
populations cannot silently backfill or erase the first cohort.

## Verification

The cumulative candidate contains 16 PTSE modules and 17 PTSE test files.
**286 tests pass**: the original 255, 12 new integrity tests and 19 publication
tests. All candidate Python source compiles. The isolated environment uses
Python 3.12.14, pandas 2.2.3, NumPy 2.3.5 and pyarrow 25.0.1; no source stubs were
used and no frozen C1 module was imported or tested.

All 30 incumbent dependency files were independently fetched at frozen current
main `bb7847a33c5fcaa3d2963e3c6be18d3628493966` and Git-blob verified. They are
unchanged from the PR dependency closure. The complete 286-test suite also passes
against that equivalent current-source snapshot. This is a scoped dependency
proof, not a full repository merge-ref run.

A separate nonauthor technical reviewer ran 59 focused tests and 15 additional
forgery, denominator, source-binding, replay and mutation probes against the
exact source blobs recorded in `PTSE_W3_CONFORMANCE_2026-10-07.json`. There are no
blocking findings within this source-only scope. That review is not a formal
GitHub approval and does not approve a physical writer, private endpoint or
scientific protocol.

The previous head's CI run 37292207526 and fences run 37292206948 succeeded.
Hosted checks must be observed again on the published candidate; old green
checks are not new-head proof.

## Actual incumbent-source proof

The five PTSE modules needed by the preflight were fetched as exact GitHub blobs
from published source commit `7359e29812c57722fd729ecd7af6863155b7ec9d`, verified
by Git blob and SHA256, and executed in memory on the authorized Studio host.
No host source file, W3 store, grader or production caller was changed.

The incumbent candidate loader observed 139,038 rows across 40 stamps. Its full
three-column projection for 2026-10-05 contained 2,933 candidate rows. The
incumbent validated B1 reader returned generation
`peg:7473e0087a7a47de5b0feffe9ff6637457d6f6f0a16513e853819f3e2ec45151`
with 1,060 episodes. This is a read-only observation at installed source commit
`007e0cccbd06f089605ba122efc658f406043dd3`, not a claim about the latest deployed
production source or natural first-seen issuance.

| Outcome in the complete observed stamp | Count |
| --- | ---: |
| Attempted candidate rows | 2,933 |
| Exact B1 relation; UNAVAILABLE / CONTEXT_MISSING enrollment | 937 |
| Explicit CANDIDATE_B1_RELATION_UNAVAILABLE rows | 1,996 |
| Fabricated context artifacts or ambiguous relations | 0 |

The immutable B1 generation's reconciliation receipt independently records the
same 2,933 candidate inputs, 937 mapped and 1,996 suppressed. Its same-stamp
suppression records contain 1,893 IDENTITY_UNRESOLVED and 103
MISSING_STRUCTURAL_ANCHOR source IDs, with no duplicate IDs. All 1,996 belong to
`us_prophet_v3`. The generation manifest and receipt digests were checked against
the HEAD manifest pin. A separate identity census verified exact set equality
between the 1,996 missing-relation source IDs and the 1,996 canonical suppression
IDs: zero missing, extra, ambiguous, duplicate or outside-population IDs. The
snapshot's validated receipt equals the immutable generation receipt. These are
canonical suppression decisions, not evidence
that same-stamp B1 reconciliation was absent or that unsupported boards caused
the difference. PTSE must not invent episode links for those rows.

The complete packet remains **RELATION_REFUSED**. That is the expected refusal
behavior for the observed source material; it is not publication acceptance.
Reversing the input order returned IDENTICAL_REPLAY. Replacing the population
with an empty input returned REVISION_REFUSED / CANDIDATES_OMITTED and preserved
the first packet bytes. Source HEAD, B1 HEAD and revalidated B1 material were
unchanged. Every authority value remained literal false. The process exited 0.

`PTSE_W3_ACTUAL_COHORT_2026-10-07.json` contains the exact source and material
digests, observation time, denominator counts, canonical suppression binding
and replay checks. Its manifest digests are observer-produced verification
receipts over actual incumbent-reader material; they are not owner-issued live
admission receipts. No grade, protected B0 outcome or frozen C1 source was read.

## Existing-owner integration ruling still required

Physical W3 storage belongs to `engine/us_prophet_w3.py` and
`scripts/accrue_us_prophet_w3.py` under `data/us_prophet_rank/w3`. PR #8271 has
overlapping incumbent custody. Its paired, family and coverage grains are closed;
the new module neither edits those files nor calls their private append helpers.
The existing owner must explicitly accept a separate PTSE sub-grain and retain
first-observation, unavailable-row, content-address and revision semantics.

The old broad claim that the first PTSE write necessarily refuses after legacy
W3 completion is incorrect: the private helper accepts an empty prior frame
before checking `refuse_new_keys`. The actual incompatibilities are that
completion belongs to the three legacy grains, empty replay omissions are not
recorded, and its fingerprint/canonical-artifact handling is not the PTSE
immutable-byte contract. This preflight defines PTSE completeness independently;
it is not permission to use those private helpers.

The nightly candidate/B1 stage is schedule-only, while W3 can run under
`if: always()`. A future owner implementation must require successful same-stamp
B1 reconciliation, not merely a `lane=nightly` label. The existing W3 commit lane
can stage the accepted grain; no additional publisher, scheduler or commit
service is needed.

The product path remains the separate optional private/authenticated context
surface described on #8325: existing Macro API ownership, a Terminal same-origin
authenticated BFF, the W2 optional guard and a read-only UI. Existing auth,
entitlements, kill switch and no-store controls remain authoritative. Exact
API/BFF custody has not been accepted. The raw internal plan-book route,
management-score `macro_stance`, public R2 and closed D5 decision vectors are
not substitutes for that owner acceptance.

## Source and science frontier

Current-source inspection supersedes two stale dependency claims: #8183 and
#7584 are merged. That does not establish B0 qualification. The #8183 installed
source receipt explicitly records a blocked runtime SPY reader probe with no
effect; this continuation does not repeat it. #7734 and private-quote provenance
#8458 remain Draft/unmerged, and #8458 has no formal independent release review.
The B4 adapter still lacks an admitted production caller and leaves missing
risk/fillability/gap evidence UNKNOWN. Quote provenance alone cannot close B4.

**B0 remains NON_EVALUABLE: SOURCE_NOT_QUALIFIED + PROTOCOL_NOT_RATIFIED.**
The current price ladder leaves adjustment vintage, session, venue and observed-at
provenance absent. Licensed raw bars do not supply the missing canonical
split/dividend factor-vintage owner. Two numeric price bases do not prove
point-in-time corporate-action lineage or qualified structural and total-return
series. The proposed corporate-actions owner has not supplied that contract.

Before opening protected outcomes, the incumbent Data OS/source owner must
qualify the raw and corporate-action lineage, known-at/vintage clocks,
session/calendar and rights/source manifest. The ex-ante B0 protocol must then
be ratified with source identity and prior exposure recorded. A scientific
NON_EVALUABLE or null result may be valid, but it is not a timing edge or automatic
acceptance of the parent mission.

All six action names have an existing composition surface. NEW_ENTRY and
PULLBACK_BUY require their distinct B3/B4 and geometry receipts. CONTINUATION,
ADD, DERISK and REENTRY remain UNKNOWN without canonical position, budget,
geometry or prior-exit lineage. Exact plan-to-B1 relations for a supported subset
do not establish position or exit ownership.

## Next executable gates and acceptance

1. Source publication to existing #8364 used exact-head compare-and-swap and
   exact content readback. The real read-only cohort proof is bound to that
   published code. Observe the final current-head hosted CI separately; neither
   local verification nor an earlier green run replaces that gate.
2. Obtain the incumbent W3 sub-grain and Macro/Terminal consumer-custody ruling,
   then implement through those owners and normal repository release controls.
   Formal independent source/science review remains separate from internal
   technical probes.
3. Demonstrate real qualified owner source -> immutable context -> accepted
   persistence -> private API/BFF -> read-only consumer, including missing,
   stale, refusal, replay and kill-switch behavior.
4. Observe natural first issuance and the existing maturity/outcome path. Do not
   backdate evidence, force off-schedule ledger advancement or relabel historical
   reconstruction as prospective.
5. Qualify B0 source and ratify protocol before protected research, or obtain
   mission-owner acceptance of a concrete NON_EVALUABLE terminal/re-scope result.
   Forecast or decision authority needs its own earned evidence and owner ruling.

Frozen C1 #7929 stays at `e1a6524ecfcdfee0f0cad251e0d502f2660c32a7`. Its prior
refusals and parked unknown effect are not replayed. No competing source store,
grader, lifecycle or publisher has been introduced. No merge, deployment,
production issuance or user-visible completion is asserted by this checkpoint.

# EXP-1 v1 — declared-capture cutoff inspector

Owner context: existing WS:ALPHA-INTELLIGENCE-INTEGRATION / K3E; historical
Fable program ownership remains. Operation:
`information-to-price-exp1-20261003-sol-001`.
Parent intent/evidence: [Information→Price #8309](https://github.com/mastermindx-market-intelligence/macro/issues/8309).

## Bounded outcome and current gates

This increment prepares an internal read-only research query over the existing
SRC-A1 observation and attempt artifacts. It answers, for one explicit immutable
source revision, provider-native ticker, metric, raw horizon and UTC cutoff:

- the latest coherent captured snapshot, including typed absence or partiality;
- the last unambiguous structurally supported captured snapshot;
- the latest collection attempt and its separate degradation;
- exact capture age, native period, raw correction/supersession lineage and
  explicit record/snapshot/attempt populations;
- why a normalized numeric baseline is withheld.

The broader EXP-1 normalized surface remains **PARTIAL**, not fully built.
This is a source-view capability, not financial comparability or model admission.
There is no runtime, release, publication, merge or capital authority in this tool.

Sol independently accepted the native SRC-A1 physical proof at
`63fe5e92d305e34ba8bdd6578ccb56e97076d740` and recorded conditional separate EXP-1
source-preparation admission in #8309 at 2026-10-03 09:10:46 UTC.
SRC-A1 durable acceptance records remain publication-pending in draft PR #8312;
the conditional admission permits this separate bounded preparation. Neither
that admission nor this handoff claims those records are on main or releases
publication. Program-CEO retains independent review and publication decisions.

The relevant contract owners remain `EXPECTATION_MODEL_SPEC.md`,
`DATA_CLOCK_RIGHTS_MATRIX.md`, `BUILD_SEQUENCE.md` and `handoffs/SRC_A1.md`.
The implementation does not rewrite the source acceptance or those owners.

## Entry point and paired source proof

`engine/k3e_expectation_surface.py` provides the stateless
`inspect_expectation_surface` function over explicit observation/attempt mappings.
The pure function does not mutate its input. It requires a paired source
provenance envelope but does not itself attest caller-supplied provenance.

The real consumer entry point is:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/query_k3e_expectation_surface.py \
  --repository /absolute/path/to/macro \
  --source-revision ff420e6841a2468e4b718340cff240abbef114f1 \
  --ticker V --metric EPS --horizon '+1q' \
  --as-of 2026-10-02T11:49:00Z
```

The CLI requires a full lower-case 40-hex commit. It reads exactly
`data/revisions/expectation_observations.parquet` and
`data/revisions/expectation_attempts.parquet` from that same commit via
argument-array Git reads. Both actual byte SHA-256 hashes and Git blob IDs,
the full source commit and all query dimensions/cutoff bind query identity.
Git transports and lazy fetching are disabled. Objects must already be present.
There is no default moving revision, file-path alternative, fetch, provider call,
network request, writer, default output file, installation or watcher.

JSON goes to stdout. Malformed CLI/query/envelope/parquet input produces typed
`REFUSED` JSON on stderr and exit 2. Legitimate absence, unsupported coverage,
ties and degradation produce successful JSON and exit 0. Pandas/parquet support
is needed only at the CLI source-read boundary; the engine uses standard library.

## Declared clocks and historical limit

The replay basis is `declared_capture_at_frozen_source_revision`.
`historical_public_availability_verified=false` and
`historical_repository_visibility_verified=false` are always emitted.
Declared clocks in current committed bytes cannot prove that those bytes or
that provider response were publicly/repository available at the claimed time.

Capture availability is named explicitly:
`max(system_observed_at, provider_observed_at, linked_attempt_completed_at)`.
It is not an alias for `known_at`. Source effective, source published, provider
observed, system observed, attempted and completed clocks stay separate.
Required clocks are explicit UTC/timezone-aware ISO clocks; naive, malformed or
missing capture clocks exclude support. Publication after capture, capture
before attempt, backwards attempt completion and backwards system/provider
capture ordering are invalid. A future economic effective date or native fiscal
period alone does not imply future knowledge.

The full temporal availability boundary precedes observation identity, value,
missingness, rights, field multiplicity, selection, lineage and denominators.
Future-starting attempts never enter historical adjudication and cannot alter
source-clock-anchored missing-receipt observation diagnostics, even when their
attempt IDs match those observations. Future-capture observations and observations
linked to explicitly unfinished or later-completing attempts do not enter any
historical observation population, including diagnostic counts. If any started
receipt under a reused attempt ID is pending, that binding is temporally
ambiguous: all observation facts under that ID are withheld, including facts
claiming the completed receipt. Start-visible duplicate-attempt diagnostics
remain; choosing the completed receipt cannot restore strict support.
Historically locatable missing/malformed receipts retain exclusion diagnostics.
An attempt started by cutoff but completing later, or with null completion,
exposes only its start identity and derived
`INCOMPLETE_AT_CUTOFF` query state. Final status, completion time, HTTP/error,
latency, payload and count are withheld. Invalid or absent final status labels
cannot change that pending classification. Malformed completion strings and
backwards completion clocks remain distinct invalid receipts. This derived
query state does not extend SRC-A1's canonical attempt-status enum.

A malformed/unlocatable row with no valid capture/start anchor cannot belong to
a historical population. Full input totals are confined to `input_provenance`
outside the semantic payload. Changing the explicitly frozen vintage still
changes query identity through its exact source bytes; this is intentional.

In particular, frozen `ff420e6841a2468e4b718340cff240abbef114f1` has 8,583
attempt records. The later source vintage adds four null attempt rows carrying
earlier 06:06 clocks (8,587 attempts; observation bytes unchanged at 473,200 rows).
These are different vintages, even for the same cutoff. A timestamp is not proof
of historical repository visibility.

## Coherent snapshots and structural support

Snapshot identity keeps session, attempt, provider, provider record class,
provider payload hash, input ticker, metric and raw horizon together.
Each field is unique inside that group. All historically available identifiable
members, including scalar-invalid rows, participate in field multiplicity and
period/capture coherence before scalar filtering. An invalid duplicate average
or count, or an invalid member carrying a contradictory period/capture clock,
therefore degrades the entire group. Each excluded member is counted once even
when scalar and group faults overlap. Duplicate observation/attempt identities,
field collisions and inconsistent period/capture clocks exclude or degrade
evidence. Equal latest capture clocks with conflicting groups are
`UNESTIMABLE`; the engine never selects an economically arbitrary candidate by
lexical identity.

The selected raw estimate field is explicitly `average`. Structural support
requires a successful completed unique linked attempt, a finite average with
null missingness, and a positive finite integral
`covering_analyst_count` companion in that exact group. A genuine zero covering
count is retained as a count fact but supports no estimate. A genuine zero
average with positive covering count is supported. Revisers or other count
columns are not substitutes. No historical IDs/dates are hardcoded.

Latest capture and last supported capture are separate. Later partial, null,
error or missing evidence does not erase prior support. Its age and native
period remain exact, while the latest attempt retains its own state. Missing
period anchors are `ANCHOR_UNAVAILABLE`; changed native periods print
`NATIVE_PERIOD_CHANGED_NO_REVISION_INFERENCE`. No fiscal year is derived.
Correction state and raw `supersedes_observation_id` are preserved; missingness
is determined from value plus `missingness_reason`, not correction state.

Raw captured values are marked `RAW_CAPTURE_INSPECTION_ONLY`. They are source
inspection evidence, not normalized or financially comparable claims.

## Null baseline, rights and populations

`normalized_baseline.value` is always null. Status is `UNAVAILABLE` for absent
observation evidence, `UNESTIMABLE` for insufficient/unadmitted evidence or
`RIGHTS_BLOCKED` for an explicit known blocked right. Reasons name ungranted
consumer admission, unknown source-use rights and missing canonical identity,
unit, currency, basis or native period where applicable. Caller rights labels
and IDs cannot grant financial admission. There is no allow-unknown flag.
UNKNOWN permits neither financial use nor an inference that raw inspection is
prohibited.

Denominators name their populations: the retained
`capture_clock_bounded_relevant_records` key now covers fully temporally
available observations plus historically locatable missing/malformed receipts;
it excludes explicitly pending linked captures before any diagnostic or rights
adjudication. Other populations are valid captured records, structurally
supported estimate-field records, true
missing records, invalid/inconsistent excluded records, distinct coherent
snapshots, supported snapshots and started/completed attempts. Attempts are
provider/ticker populations because native receipts are not metric-specific.
The covering count is provider-reported and printed per snapshot. Reason counts
are nonexclusive diagnostics, not additive partitions. True missing may overlap
invalid/excluded evidence. Full-input totals are not historical denominators.

Composition time remains outside the deterministic semantic payload/digest.
Exact age is reported in seconds. `freshness_policy` stays `UNAVAILABLE`.

## Acceptance and held non-goals

Focused synthetic tests discriminate future leakage (including later outcome,
value, missingness, rights, ID and payload changes), mixed completed/pending
receipts under a duplicated attempt ID, future-start receipt append/removal and
mutation with unchanged historical diagnostics, pending attempts with null
completion or invalid/absent final statuses, invalid duplicate average/count
members and invalid members carrying period/capture contradictions, incomplete receipts, malformed/naive clocks, publication contradictions
versus future effective dates, missing/duplicate receipts, frozen-vintage
identity, deterministic repeated semantic payload, cross-session coverage,
zero/null/count-zero, partial/null/error after good, period rollover/missing
anchors, conflicting ties, unknown/caller rights and IDs, absent ticker and
non-mutation. A local Git fixture proves paired-blob CLI use and moving-ref
refusal. Root owns independent native consumer receipts and review; synthetic
tests are not natural-run proof.

Expected native inspection examples, subject to independent receipts: V EPS
`+1q` captures 3.6281 at the earlier 2026-10-02 11:49 UTC cutoff and 3.62739 by
13:00 UTC with explicit source supersession; UVV retains 1.75 with a new capture.
JBGS revenue `0q` is typed missing/zero coverage and partial, with no earlier
structurally supported average for that node. Synthetic tests establish
partial-after-good retention rather than misrepresenting JBGS as that witness.

Allowed implementation paths are exactly this handoff, the engine, CLI and
`tests/test_k3e_expectation_surface.py`. Source collector/legacy revision lanes,
`engine/expectation_state.py` (LT-2c EDGAR/SUE), CI enrollment, Agent OS and
publication records retain their existing owners.

No identity map, guessed issuer/security join, fiscal mapping, source rewrite,
new store/policy plane, market/residual/relationship/outcome join, normalized
consensus, age weighting, freshness threshold/share, contributor dispersion or
median synthesis, revision delta/cluster/score, model, ranker, capital action,
vendor procurement, cadence or universe change is built here.

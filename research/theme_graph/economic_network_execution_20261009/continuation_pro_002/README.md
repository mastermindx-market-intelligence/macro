# Economic network execution — retained reader and frozen review sets

Operation: `gmi-economic-network-native-reader-20261009-pro-002`  
Principal: the current Chairman-commissioned research and execution session  
Source integration: Macro `41c1516fa803504c30ca2d5d067a71899fca3e8d`, 2026-10-09 UTC

## Capability delivered by this change

An analyst can submit an explicit, bounded set of source documents and relationship
candidates to the existing Company Intelligence inspector, receive every case's
complete inspection or refusal, and reproduce the review's canonical content
identity. The retained SEC reader can perform its existing read without importing
the SEC acquisition collector or initializing its networking libraries.

These capabilities advance the source-review and diagnostic stages of the
[economic network masterplan](../../economic_network_20261008/IMPLEMENTATION_MASTERPLAN.md).
They retain the existing separation between source inspection, economic relationship
admission, thematic similarity, and market dependence. Passing a source inspection
does not establish an economic edge, its magnitude, or a predictive effect.

This file records the source-freeze boundary. Native test results below are actual
results. The prepared real-source harnesses require separate execution receipts;
their presence in Git is not a claim that they ran. The implementing PR and its
principal release receipts carry the later frozen-candidate and accepted-source
execution outcomes, hosted CI identity, merge result, and accepted-byte proof.

## Research and accepted implementation preserved

The complete nine-report research package was published in
[PR #8661](https://github.com/mastermindx-market-intelligence/macro/pull/8661).
Its reviewed head is `2015e427ed4690f5a2778f63a825c2cdec4d8ac0`; GitHub reports
merge `219b47ea5a5384ab7299e260dd3eecb7437310de` at 2026-10-09T08:57:03Z.
The principal compared all 29 published files across the reviewed commit, accepted
merge and current main `41c1516…`: every byte matched. The complete upstream delta
since this operation's initial `7abc73…` base contained 4,024 paths, all in the
research package or generated/data outputs. No code, CI, or procedure delta was
hidden behind the GitHub compare API's first 300 filenames.

The research merge is a publication fact. It is not independent proof that every
D01–D10 recommendation was adopted or that a production contract was admitted.
The named commissioning attachment was not recovered; attachment-specific
conformance remains unverified. The completed research and its acceptance matrix
remain intact rather than being replaced with another proposal.

The first implementation was accepted in
[PR #8667](https://github.com/mastermindx-market-intelligence/macro/pull/8667),
squash `094097a5a7a4e2719daf10a464aeaffb262ea149`. This continuation extends its
actual modules and existing CI owner. It preserves all previous refusals and the
original strict NVIDIA failures in
[the retained diagnostic receipt](https://github.com/mastermindx-market-intelligence/macro/pull/8667#issuecomment-6074733760).

## Using the review consumer

The Python API is:

```python
from engine.company_intelligence.relationship_candidates import inspect_review_set

review = inspect_review_set(
    {
        "schema": "company_intelligence.relationship_review_set/v1",
        "review_set_id": "analyst-review-001",
        "cases": [
            {"case_id": "case-001", "candidate": candidate, "source": source_text}
        ],
    },
    as_of=None,
    registry=None,
    include_support_text=False,
)
```

`candidate` is an actual existing single-case candidate payload, not a supplied
inspection result. The consumer calls `inspect_candidate` for each usable case.
The existing candidate schema and refusal rules remain authoritative.

For explicit files, create a manifest using the closed file schema:

```json
{
  "schema": "company_intelligence.relationship_review_files/v1",
  "review_set_id": "analyst-review-001",
  "cases": [
    {
      "case_id": "case-001",
      "candidate_file": "/physical/authorized/path/candidate.json",
      "source_file": "/physical/authorized/path/source.txt"
    }
  ]
}
```

Run the existing module:

```sh
python -B -m engine.company_intelligence.relationship_candidates --review-set review.json
```

`--as-of`, `--registry` and `--include-support-text` retain their existing purposes.
`--review-set` is mutually exclusive with `--candidate`, and it rejects `--source`.
The original single-case API and valid single-case CLI remain available.

Use physical authorized regular-file paths. Symlinks in any component, parent
traversal, FIFOs and other nonregular files are refused. Descriptor-relative
no-follow traversal and nonblocking final open prevent a substituted FIFO from
turning a file read into an indefinite wait. These checks validate the supplied
file inputs; they are not a filesystem sandbox or a source-rights grant.

The CLI returns 2 for a whole-request refusal or any per-case `REFUSED` or
`UNAVAILABLE` result. It returns 0 otherwise; that includes `NOT_KNOWN_AS_OF`, so
consumers must read the statuses rather than equating process success with usable
evidence. A failed file stays in the requested case set and its denominator.

## Output contract and practical limits

Output schema: `company_intelligence.relationship_review/v1`.

| Property | Actual behavior |
| --- | --- |
| Case order | Canonical order by unique opaque ASCII case ID |
| Individual result | Complete output from the existing inspector, or explicit input refusal |
| Missing or invalid inputs | Visible case outcomes; not silently dropped |
| Canonical identity | Options, canonical case order, input bindings and results |
| Raw provenance | Candidate-file and manifest-byte witnesses remain separate from canonical identities |
| Repeated inputs | Reported as repeated references; not counted as independent corroboration |
| Same ID, different payload | Unresolved conflict annotation; no selected winner |
| Explicit correction/contradiction | Target absence, ambiguity or presence is reported; reference remains unresolved |
| Temporal exclusion | Excluded raw candidate semantics cannot establish a reconciliation target |
| Admission | `NOT_ADMITTED`, Graph1 null, rank/gate/size/trade/prediction false |

The counts describe the supplied review: requested cases, cases with supplied
source bytes, unique supplied-source byte digests, inspectable cases, refusals,
unavailable cases and not-known-as-of cases. They do not measure issuer-universe
coverage, relationship recall, precision, legal counterparties, or independent
economic support. Invalid outer or over-budget requests withhold case results and
semantic reconciliation while retaining honest nonsemantic processing counters.

| Resource | Bound |
| --- | ---: |
| Cases | 64 |
| Manifest or individual candidate | 256 KiB |
| Individual UTF-8 source | 4 MiB |
| Aggregate candidates | 8 MiB |
| Aggregate sources | 64 MiB |
| Serialized aggregate output | 8 MiB |

Candidate encoding stops when an encoder chunk crosses the byte cap, avoiding
full materialization of an amplified shared-object payload. One transient escaped
chunk can exceed the cap; the limit is not a promise about total process memory.
Existing depth, node, scalar and finite-number limits also remain in force.

Default output omits the dedicated support-text field. Existing manually supplied
annotations may still contain source prose. Neither mode establishes quote-free,
public-safe, training-eligible, redistribution-authorized, or commercially licensed
content. Registry input also remains caller-supplied within the native loader and
inspector checks; this consumer creates no `PRODUCED` registry row.

## Pure-reader repair

Twelve existing receipt/key/decoder/decompression definitions move unchanged into
the existing Fundamental Forensics engine source spine. The collector re-exports
the identical live objects. Persisted JSON, IDs, storage keys, byte caps, strict
store checks and error behavior remain unchanged. The candidate adapter, native
archive reader and filing-attestation manifest-key lookup use that same pure
closure.

The old strict run exposed an attempted `socket.__new__` during urllib3's IPv6
capability probe. Its exception was caught, and all five outputs could still match,
but the guard had observed a forbidden attempt. Both original runs therefore remain
failed. Warming the acquisition libraries or weakening the guard would not repair
that defect. The new cold regression is red both on original source and on a
manifest-key-only partial correction, and green on the full relocation.

This repair does not claim that every Fundamental Forensics operation is free of
acquisition imports. Filing-package materialization remains outside its scope.
The defining Python module of moved objects changes; the bounded usage census
found no pickle/module-name consumer, but no external pickle-compatibility promise
is made.

## Verification at the source-freeze boundary

| Evidence | Observed result | Scope |
| --- | --- | --- |
| Pure-reader original and partial implementations | Both fail the new cold-process regression | Demonstrates the actual defect and incomplete alternative |
| Pure-reader correction stage | 213 passed | Earlier overlapping manual/pinned/spine/attestation run |
| Final manual and review-set suites | 171 passed, 3.50 s | Existing 107 manual tests plus 64 new review-set tests |
| Final pinned-adapter suite | 44 passed, 2.06 s | Actual downstream compatibility after the consumer extension |
| Independent source review | PASS on final v4 | Both reported blockers corrected before installation |
| Real CI manifest ownership checks | 3 passed, 146.06 s | Command coverage, existing exclusive owner and transitive import closure |
| Existing packing/determinism checks | 2 passed, 110.57 s | Actual baseline-plan determinism and existing packing ceilings; not a current-PR hosted plan |
| Populated AgentOS record validation | 1,590 records, 0 errors | Includes the new decision; 143 warnings concern existing records |

The 213-test earlier run overlaps the later runs; it must not be added to 215 and
presented as a distinct-test total. The first consumer precheck stopped before
pytest because it compared one extra terminal blank line. The original failure is
retained, the preservation assertion was corrected, and no source correction was
needed. No local `run_ci_pack --execute` was run.

The existing exclusive CI job `company-relationship-candidates` now declares 69
literal paths and runs the new review-set suite alongside its two existing suites.
No job, inventory entry, packing ceiling or workflow authority was added. The
principal source receipt extends that dependency union with the two native
spine/attestation tests, producing 71 pinned dependencies.

Read the detailed [pure-reader implementation](NATIVE_READER_PURE_BOUNDARY_IMPLEMENTATION.md),
[independent reader review](NATIVE_READER_FROZEN_SOURCE_REVIEW_20261009.md),
[original consumer findings](REVIEW_SET_INDEPENDENT_SOURCE_REVIEW_V1.md),
[corrective consumer review](REVIEW_SET_INDEPENDENT_SOURCE_REVIEW_V4.md),
[native consumer receipt](REVIEW_SET_NATIVE_IMPLEMENTATION_20261009.md), and
[native log export](review_set_native_receipts.json).

## Real-source proof and source custody

The two prepared harnesses serve different acceptance claims:

- `replay_nvda_repaired_reader_prepared.py` reuses the five exact retained NVIDIA
  pinned-adapter cases, with original store/input identities, complete expected
  outputs, zero prohibited import/side-effect attempts, unchanged retained state
  and no latest-pointer creation. It does not reacquire the filing.
- `replay_micron_nvda_review_set_prepared.py` checks the real Micron and NVIDIA
  inputs in the new batch consumer, including a missing source and invalid
  candidate, current/reordered/historical views and literal CLI compatibility.

Both require a fresh principal source-verification receipt. The separate
`verify_execution_source.py` reads actual Git/workspace bytes and, for accepted
source, actual GitHub PR/main metadata. It verifies clean source, exact frozen
implementation hashes and the whole owned/dependency census. It does not create
admission, deployment, runtime custody, or historical eligibility.

The old acquisition receipt's source revisions remain historical provenance.
The executing source revision is bound separately. A new 2026 capture cannot
establish earlier system possession merely because its filing was public earlier.
The retained NVIDIA SEC index/raw length difference of 115 bytes remains explicit.
The Micron fetch receipt's exploratory coordinates remain unchanged; the saved
source-case and original replay harness carry the actual selected span contract.

One old Studio Direct evidence-copy call timed out without a process identifier.
Its reserved `reader_builder_evidence` target was absent in subsequent same-host
readbacks; the original dispatch/completion remains unverified. That target was
not retried, replaced or written through another carrier. The exact frozen repair
was separately saved and verified in
[GitHub checkpoint 6078102865](https://github.com/mastermindx-market-intelligence/macro/pull/8667#issuecomment-6078102865).
The active native connection was independently reconciled to the same physical
m2studio host, canonical workspace, common Git and source bytes before further
independent work. No application-source effect was part of the unknown copy.

## Parent mission and ownership

The owner-preserving decision is
[`DEC-GMI-ECONOMIC-NETWORK-READER-AND-REVIEW-CONTINUATION`](../../../../agentos/decisions/DEC-GMI-ECONOMIC-NETWORK-READER-AND-REVIEW-CONTINUATION.md).
Fundamental Forensics owns retained SEC source contracts; Company Intelligence owns
this inspector and review consumer. Data OS retains identity, source-purpose and
temporal law; GMI owns semantics and ThemeState; K3-D/Alpha owns propagation
composition; F04 owns downstream product composition. No new truth store or owner
registry is introduced.

The full first production milestone still needs an adopted native relationship
observation species, real producer and temporal grain, purpose-specific source
policy, legal-party identity behavior, an incumbent served consumer, and matching
positive/correction/refusal production evidence. This utility does not complete
that milestone or the planned 120-issuer/30-difficult-case diagnostic. Economic
precision, operating-outcome transmission, useful incremental product behavior
and predictive promotion each need their own evidence and falsifiers.

The [current readiness census](NATIVE_READER_CURRENT_READINESS_20261009.md) and
[native adoption frontier](NATIVE_ADOPTION_FRONTIER_20261009.md) identify the exact
incumbent seams and missing gates. The bounded census found no overlapping active
repair paths; it is not a universal runtime lease census. Historical owner names
are not proof of an active worker. This change releases no preserved hold on shared
Theme Research, private publication, Technology economic change, K3-D, D2E, W-C7,
or Terminal #796.

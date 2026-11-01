# P1.T5 selected SEC publication evidence

This extends the existing Company Intelligence publication workflow. It adds no
source-use, principal, purpose, or action permission and changes no acquisition,
immutable-object, compare-and-swap, or retry contract. This source-only change must
not be exercised by dispatching a publication run as validation.

## Audience and retained content

The repository is PUBLIC. Any future Actions artifact inherits its existing
repository artifact audience; it is not private operational storage. Retention is
seven days, with no ACL change or new public serving endpoint. The allowlist is
therefore restricted to selected public-SEC provenance metadata already represented
by the selected issuer-release source contract. Repository visibility is not an
independent disclosure or source-rights grant.

The artifact contains one closed JSON envelope: repository, actual checkout SHA,
run ID/attempt, ordered publication candidates, and a separate final local-selection
and refresh-return disposition. No actor/account, environment, exception text,
response-header object, root Company output, transcript, quote, claim, or raw
workspace/source body is retained.

Each candidate binds the exact original immutable-manifest SHA256 and byte length
and a closed projection of its schema/generation/cutoff/source-clock metadata plus
selected SEC wire entries. The original manifest is validated locally but its
arbitrary alias/warning strings, mixed entries, and raw bytes are NOT exported.
This projection is not asserted to be the original manifest wire representation.
Each selected entry binds canonical company/event/generation/document/filing IDs,
source URL/hash, and the exact workspace path/hash/length from that manifest. The
complete local workspace bytes must match that receipt before selecting fields.
Only the issuer-release source projection is exported. Missing old-row acquisition
metadata stays explicitly absent; no receipt is minted or backfilled.

An existing acquisition receipt is retained exactly only after closed-schema,
SEC requested/final/redirect, digest/length, source/filing/URL, and cutoff checks.
Declared MIME/encoding/charset fields are permitted only under a narrow known-value
allowlist. Unknown metadata makes evidence unavailable rather than being redacted
into a different purported exact receipt. Body replay already performed upstream
is not re-claimed here: this export verifies wire/hash/metadata binding, not a new
acquisition, raw-wire capture, or independently replayed source body. Acquired_at
remains the original validated fact, including on an unchanged-source no-op.

## Outcomes and failure

Candidate outcomes are recorded at existing publisher decision sites, separately
from integer return codes: unavailable client, already-current marker, dry-run,
payload failure with partial effects possible, CAS conflict, marker-put failure
with effect UNKNOWN, and API-acknowledged marker put. Acknowledgment does not prove
a new immutable CREATE or independently observed serving. No-op before dry-run
keeps its actual already-current disposition. No network behavior changes.

Every chained candidate retains its own generation and outcome. Final local
selection is separately validated even when the closing write is skipped. A later
refresh failure cannot relabel an earlier candidate as final successful promotion.
Invalid candidate metadata/body binding is never retained; safe prior candidates
may be reported as partial with a closed unavailable reason and no successful
final selection. Missing output has an explicit safe absence. An invalid envelope
produces no artifact. Retention failure never supplies publication retry authority.

The workflow uploads only after this attempt successfully serializes the closed
evidence and emits a fresh step-output readiness flag (initialized false). A stale
file or failed initialization/serialization cannot authorize upload. It retains
only the evidence JSON, never an output-directory
wildcard, logs, temporary files, or credentials. Synthetic offline fixtures prove
source behavior only. Runtime acceptance still requires an independently admitted
normal run and consumption of its exact same-run artifact; digest/projection alone
does not supply missing original wire bytes or a rights/principal decision.

## Receiving consumer boundary

IW2 PR804 treats this as conditionally useful metadata only. Existing eventWorkspace
requires original generation-manifest bytes and the exact workspace wire, full
normalization, manifest file hash/length, exact manifest/container fingerprint,
all dependencies/qualifications/clocks/rights and original chain bytes. Existing
issuerRelease additionally requires a unique byte-replayed issuer release and the
current authenticated principal's decision. This artifact supplies none of those
missing preimages or decisions and creates no substitute store, fingerprint or
consumer grant. Their separate permitted owner/wire-access boundary remains.

## Versioned field boundary

`sec_publication_evidence.v1` has only schema, context, audience, retention_days,
scope, candidates, refresh_outcome, final_local_selection, unavailable and
retention_status. Context has only repository, actual 40-hex checkout, numeric
run_id and run_attempt. Candidates have sequence, snapshot and publish_outcome.
A snapshot has schema `sec_publication_snapshot.v1`, manifest and selected.
Manifest is a projection containing only original schema/SHA256/byte length,
generation_id/generated_at/source_clock. Selected entries have only event_id,
company_id, generation_id, generated_at, wire and source. Wire contains only
path/SHA256/bytes. Source contains only kind, document_id, filing_key,
source_sha256, url, receipt_state, receipt_status and acquisition_receipt.

The source key retains the existing closed `earnings_release.sec_acquisition.v1`
receipt verbatim or null with receipt_status=absent. This is a producer report
bound to the validated local wire hash, not independent verification of absent
source/entity/wire preimages. Retention_status is unavailable, partial or
metadata_complete; the last means metadata construction only. Refresh outcomes
are incomplete/returned_success/returned_conflict/failed. Neither field grants
source access or means a fresh acquisition, immutable CREATE or serving proof.
`final_local_selection` is null on refresh failure, otherwise a validated snapshot
with a matching candidate_sequence or explicit null when publication was not
observed. Candidate outcomes are closed in scripts/company_intelligence_publication_evidence.py at actual
publisher decision sites, including partial/effect-UNKNOWN distinctions.

Selected denotes the issuer-release/SEC metadata subset, not a document-purpose
authorization. Document IDs are the exact canonical-shaped values in the hashed
wire; missing original filing/body preimages are not reconstructed to claim an
independent document-identity replay. No omitted dependency or chain is treated
as verified by this metadata artifact.

The helper stays beside the existing publication scripts. This metadata-only
change does not modify engine/** or the accepted SEC producer, and therefore
does not add an engine-render push trigger. The existing publication checkout
explicitly includes the new script in its sparse source list.

Output is bound outside the lexical and resolved publication source directory
before any evidence write or cleanup. Constructor/context rejection performs no
file deletion; source inputs and unrelated stale files are not an upload gate.
Every write/replacement/cleanup rechecks the destination boundary. Latin-1
fallback metadata must satisfy entity_length < source_utf8_length <= 2*entity_length;
both declared lengths must be positive JavaScript-safe integers. These are
structural impossibility checks, not invented missing-preimage verification.

Readiness uses the same source-directory guard and cannot alias the evidence
file. It appends only after final safe serialization, through an existing
non-symlink regular singly-linked file owned by the current process user (the
normal GITHUB_OUTPUT sink). It never creates a missing sink. Symlink and hardlink
aliases to source inputs, and the artifact itself, are refused without mutation.

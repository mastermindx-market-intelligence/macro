# Exact plan-adoption edit recipes

`scripts/agentos_plan_adoption.py` prepares source bytes through the existing Agent
OS workstream/decision validator and stdout-only decision author. It never writes
records, executes Git, opens a PR, admits a Runtime Job, or grants adoption authority.
Every result says `PREVIEW_ONLY`. This is a compiler input to the existing qualified
source publisher, not a public arbitrary-path writer or a new operation controller.
The supplied canonical owner may perform its existing read-only reference-warning
checks; this module itself performs no source acquisition or publication.

The publisher must supply captured owner code and exact already-qualified Git
snapshots. The closed snapshot includes the selected canonical WS, scoped DEC
records, an artifact-associated typed proposal, its exact base bytes, and explicit
candidate/DEC target membership or absence at the snapshot commit. Hash equality
checks bind bytes; they do not prove repository membership, ancestry, permission,
or protected default-branch publication. Those checks remain with the incumbent
sealed collector and publisher. No record can authorize a network or filesystem
fetch. Only the fixed Macro repository and derived target paths are writable.

`compile_candidate_recipe(request=..., snapshot=..., actor=..., owner=...)` accepts
one original `mmos-project-adopt-<40 lowercase hex>` request, current selected WS,
expected captured commit and predecessor, exact proposal/base SourceRefs and
candidate SHA256. Actor facts are the qualified principal, decision author, date
and rationale; client-authored actor facts are never authority. The deterministic
fingerprint binds request, actor, exact source/preimage basis and target proofs.
The candidate must be a fully valid canonical workstream with the same key.
Prose-only content is refused rather than substituted for the WS.

Phase one creates only a deterministic sibling proposal artifact with the exact
candidate bytes. It leaves the canonical WS, all decisions and Runtime unchanged.
If those exact bytes already exist in the qualified immutable candidate member,
the recipe can skip phase-one publication. A conflicting target refuses.

`compile_adoption_recipe(request=..., initial_snapshot=..., current_snapshot=...,
actor=..., candidate_publication=..., owner=...)` recomputes that same fingerprint.
Its private publication input must come from the incumbent publisher's actual
verified default-source readback of the candidate member for this exact operation.
A queued PR, local branch, timeout, absent result or unknown publication cannot be
represented as `VERIFIED_DEFAULT`. This string is an internal interface predicate,
not evidence that a caller holding a dict performed such verification.

Phase two refuses a changed original fingerprint, proposal/base/WS preimage,
current decision or predecessor. Unrelated source commits may advance, but every
relevant current member is recaptured at the new commit and checked. The fixed
recipe updates the selected canonical WS to the exact candidate bytes, authors
one real DEC referencing the immutable candidate source, and updates the exact
predecessor DEC reciprocally while preserving its raw record body. Each update
carries its exact preimage SHA256; new paths require absence. The publisher must
CAS the complete edit set against the declared current commit.

A distinct scoped `ADOPT_PLAN` permission and binding digest must authorize the
exact multi-stage recipe and all reserved scope, DONE_WHEN, release and spending
boundaries. CREATE_PROJECT, READ, direction acceptance, pause/resume and a small or
identical diff do not grant this permission. The compiler's changed-field preview
helps review; it cannot classify a request as authorized or scope-preserving.

Both phases retain the same original operation/request ID and fingerprint. The
incumbent publisher persists stage identities and reconciles unknown outcomes
through that operation only. Recompiling is not permission to resend. A crash
between phases leaves candidate content only: the prior adopted baseline remains
effective. The client may say adopted/current only after actual protected default
DEC readback and a matching canonical capture, never from a recipe, local branch,
PR, merge-queue entry or candidate receipt. No CLI invocation here performs adoption.

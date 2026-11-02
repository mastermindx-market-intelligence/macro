# Fabric implementation and pre-implementation audit

Root: `prophet-a2-board-index-epoch-divergence-20261101-sol01`.

These are commissioned leaf results and parent adjudication. They are not the
final independent PR review and do not authorize merge or deployment.

## Original runs

| Task | Run | Observed route | Original controller | Result |
| --- | --- | --- | ---: | --- |
| Helper implementation | `prophet-epoch-helper-20261102-01` | AUTO → minimax pool | 96833 | TERMINAL, rc=0, root verified |
| Read-only contract audit | `prophet-epoch-audit-20261102-01` | AUTO → glm pool | 98322 | TERMINAL, rc=0, root verified |

Both results were recovered through the original Fabric facade. Earlier
ACTIVE_OR_WAITING / null-root observations were incomplete controller observations,
not proof that execution was absent. No retry, alternate carrier, cancellation,
remote observation or duplicate labor occurred.

The controller retained process/provider outcomes; usage receipts were unavailable.
This record does not infer token cost or a provider START timestamp from polling.
Successful terminal execution, retained results and parent acceptance are distinct
from the final independent review.

## Helper result

Exact complete adapter response SHA-256:
`c2f56c32957c946bb9ce3f18cbb070f83a094ff9783b42211e2e18b97da5fe57`.

The helper returned two complete source files without changing a repository,
pushing, opening a PR or accessing raw datasets. Reported 68 tests passed.
Root verified both delivered file digests before integration:

- engine/prophet_source_epochs.py:
  `d1d1676620c6f4f765c6d547f0a0f12176e487d99f62a489579fc4139eba69ff`.
- tests/test_prophet_source_epochs.py:
  `3f41f02416d6889c063b5a6d71fe7af6ec00fd17a2700a18d131d3ffc48ec6e1`.

Root's first integrated test run passed 75 tests, including the helper's 68 and
seven actual reader/refresh/hydration tests. The helper is accepted as useful
commissioned work, with the parent-owned corrections below; the original returned
implementation is not asserted to be the final reviewed source.

## Audit result and adjudication

Exact complete adapter response SHA-256:
`e5210ca6d2a8ca1d66f4795afd7a74e26e0d546742bef1dc858e4ff8dc2ac09d`.

The auditor read exact source commit
`6343a18748e4ce2bed5a34b2e015acdb39a5d7a7` without changing a branch, PR or
workflow. It independently reproduced the committed board/snapshot sizes, hashes
and same-session date.

| Finding | Disposition and evidence |
| --- | --- |
| F1: nightly can update index after HTML render | Adopted. The disclosure identifies the index used by this page, including its exact raw hash, source/publication dates and the existing render clock. Regression advances the index path after initial capture and proves the fresh page retains the captured book/hash. |
| F2: same-read index binding | Adopted. One read_bytes call admits the displayed book and captures its identity; the fresh pass receives only that capture. A path-advancement regression checks this directly. |
| F3: canonical path and symlinks | Adopted and strengthened. Derive the filename from the validated hash, string-compare the declared path, then use descriptor-relative no-follow traversal. Gzip probe and decompression share one open file. Regressions reject both escaping and in-tree symlinks and replace a path after opening it. |
| F4: allow SAME_SOURCE even with a corrupt snapshot | Declined. The commissioned relation explicitly requires a verified immutable origination snapshot. A declared digest is not a verified source. Missing/corrupt evidence remains UNAVAILABLE/PENDING, while raw observed hashes remain available for diagnosis. |
| F5: preserve loading UX and clarify PENDING | Adopted in part. Missing/rejected books retain their existing ladder loading/error surface; the new disclosure is shown only with an admitted book. A valid book with unavailable source evidence explicitly reports PENDING. No automatic resolution or settlement promise is made. |
| F6: disclosure follows displayed board generation | Adopted. It consumes the existing first/fresh raw captures and updates inside the same branch that replaces the displayed board and Today binding. |
| F7: safe DOM placement; avoid a hydration fence | Placement adopted: adjacent to the plan clock, outside replaceable grids/Today, with no ticker or pg-more selectors. The advice to leave hydration unfenced was declined: hydrate() appends separately fetched plan/candidate rows and panels. Matching metadata must be checked before those mutations, or a preserved label can describe different displayed rows. |
| F8: source availability across lanes | Verified both express checkout paths retain the full tree; missing snapshot remains typed unavailable. The real immutable pickup artifacts were fed through the new projector and returned SEPARATE_EPOCHS/PENDING with a verified snapshot. |
| F9: encoding drift | Adopted. Explicit UTF-8 decoding preserves the incumbent reader's admission behavior; UTF-16/32 and BOM cases fail closed. |
| F10: explicit CI registration | Adopted in the existing unscoped board owner in .github/ci/legacy-jobs.yml. No new workflow or held-PR rerun was introduced. |

The final reviewer must independently inspect the completed candidate head,
regressions, candidate browser receipts and these adjudications. The pre-audit's
recommendations are evidence to assess, not unqualified approval of code that did
not yet exist when it ran.

# Portfolio OHLC origin delivery — verification packet

## Candidate and scope

The source candidate was rebased normally onto protected Macro main
`8c23f6b26a36ce20f5842590e41bb9d78bff1bac`, producing local commit
`93b5c78c153b81d948cf5e15c70008a49dd64d5c`. Subsequent changes repair CI
ownership and add this evidence packet. The final publication identity belongs
in the PR and release receipt; the content hashes in `validation.json` bind the
reviewed source without creating a self-referential commit hash.

The existing daily US chart producer writes ignored files under `site/ohlc`.
The ordinary Git/site deployment cannot carry those files to the authenticated
origin used by Portfolio. This change adds a sealed-generation delivery leg
using the existing retained inputs, daily workflow, deployment key, pinned host,
updater lock, and site origin.

No provider request, alternative source, new credential, Caddy/authentication
change, production payload, or positive Portfolio metric acceptance is part of
this local validation.

## Executed validation

All local commands used native Python 3.14. Hosted CI uses its declared Python
3.12 environment and remains required.

| Gate | Actual result | Receipt in validation.json |
|---|---|---|
| Complete new producer/receiver suite and unchanged chart suite | 78 passed in 3.04s | core |
| Rebased updater shell, rsync preservation, no-op and failure propagation | 9 passed, 315 deselected | post_rebase.results[0] |
| Rebased daily workflow and temporary-key shell behavior | 4 passed, 122 deselected | integration.results[0] |
| Unchanged OHLC authentication guards | 3 passed, 15 deselected | integration.results[1] |
| DAG conformance | 27 lanes checked, exit 0; two inherited drifts still reported | integration.results[2] |
| Curated CI registry, import closure, packing, and ancestor checks before final ancestor declarations | 31 passed, 1 failed, 172 deselected | ci_closure |
| Remaining ancestor ratchet after exact nine-path repair | 1 passed in 6.85s | ci_ancestor_final |

The final CI change after the 31 passing cases only adds the empty
`app/__init__.py` literal to nine existing exclusive scopes. It cannot remove
dependency coverage or change selection for the measured packing-probe paths.
The remaining failed ratchet was rerun against that final manifest and passed.
This is qualified evidence from two executions, not a claim of one all-green
32-case run. No packing, ancestor, or substantive-initializer ceiling changed.

The sparse worktree originally omitted the unchanged `site/chart.js` fixture
needed by two pre-existing chart tests. Only that exact source blob was
materialized; the complete focused pair was then rerun successfully. No generated
site data was fetched. The source blob SHA-256 was
`a31b8e5aa13fafc13605047c05fc0bfb3656f70a9a56dc0e5b2f0bfa78858099`.

### Failures that caused real corrections

The initial placement in the data-gated render job increased packing cost
without providing ordinary PR coverage, because authoritative PR CI selects
`gate: code`. It was replaced by the focused exclusive
`ohlc-origin-delivery` code job. Existing test commands were preserved.

The import-closure guard then identified exactly 25 missing literal dependency
paths across 13 existing exclusive jobs. Those scopes now declare the helper
and/or checked-in host pin as required. The initializer census subsequently
identified nine new `app/__init__.py` rows caused by the literal pin path. Those
nine declarations restore the census to its existing limit. The checker walks
ancestor directories for every literal path; this is a declaration requirement,
not a claim that reading a host-pin file imports the app package.

An earlier updater test fixture gave “old” and “new” rsync inputs the same size
and timestamp, so rsync correctly used its quick check. The fixture now has
distinguishable content lengths. Production rsync semantics were not weakened.

## Adversarial coverage and review

The synthetic suite blocks socket connections. It exercises oversized GNU/PAX
extension declarations with a stream that permits only one 512-byte header read,
USTAR prefix traversal, maximum admitted filename length, truncated and
concatenated archives, census/digest mismatch, and preservation of the current
generation on refusal.

It also checks unlocked upload staging, a competing selection before promotion,
digest-bound repeat acknowledgments, missing ordering fences before and after
rollback, retained predecessors, foreign paths, borrowed-lock custody, generic
post-intent failures, one mutating receive across retries, and producer
completion-receipt invalidation/rollback.

Independent source review and exact hash qualifications are recorded in
`review.md`. The full helper and new regression file received independent
read-only review; updater/workflow integration and final CI declaration deltas
received a separate independent review. These are native reviewer dispositions,
not fabricated GitHub formal approvals.

## Release sequence and remaining proof

The full protected PR CI and semantic evidence must conclude before merge.
After ordinary merge, confirm the incumbent updater has installed the reviewed
helper and successor updater before any first payload publication. The running
predecessor updater does not acquire new behavior simply by installing its
successor.

The existing trusted daily producer must create a new eligible completion
receipt. An old output directory or receipt cannot be promoted by a new workflow
attempt. Do not dispatch a broad collector merely to obtain delivery. Verify the
selected generation and serving links through metadata; this proves delivery,
not price-window coverage or Treasury freshness.

Authenticated Portfolio acceptance remains a separate final step through the
approved browser/session and existing same-box transport. Do not replay the
already completed live fixture mutations or infer positive acceptance from file
counts, mtimes, an empty portfolio, or unavailable metrics.

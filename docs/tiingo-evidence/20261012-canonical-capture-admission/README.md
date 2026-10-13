# Canonical finite capture source and closed history scope

PR #9018 merged as `f5d1cec6e56b4f8e07e4ea9038293a3072f4b1dd` after all twelve
original CI packs, contract delta, final gate, active authority and protected
fences passed at `85914b39d9e9b0c40554f226080390ab934ade6f`. The independently
reviewed callback module and regression tests match their exact canonical bytes.
The canonical CI file includes three unrelated peer job changes, while the
entire owned Tiingo job is semantically identical. Both CI-file hashes and the
owned-job projection hash are retained; original tested evidence was not
restamped. This qualifies the exact module and its gate, not all later main code.

A local verification first tried an implicit Git promisor fetch and hit a DNS
failure. The owned read was interrupted; capture workers were untouched. After
normal canonical checkout on the existing Git carrier, local verification used
`--no-lazy-fetch` and ten-second deadlines. The intervening full-file CI hash
mismatch and actual unrelated peer additions remain recorded. No Git/network
security setting changed and no protected provider or workflow approval was
retried. See `canonical-read-reconciliation.json`.

Original wave10 fully settled with 5000 successful requests, zero failures,
4970 nonempty histories, 30 empty responses and 12699484 bars. Six accepted
completed-response snapshots verified every raw checksum, requested window,
disjoint economic date and nonempty reader lineage. Its closure reused those
proofs without API calls or rebuilding. The resulting catalogue census has
23216 nonempty histories, 51173037 bars, 68 empty responses and 24405 uncaptured
desired windows. Those are bounded catalogue facts, not complete vendor history
or historical identity/PIT admission.

Wave11 started at 2026-10-12T16:00:35.796631Z on the original accepted method.
The earlier rolling candidate for that operation was never launched. A disjoint
wave12 selection and rolling integration are prepared only. Its actual launch
still requires successful prior settlement, fresh company quota, source/collision
and storage checks, exact module/plan/method binding and normal Python assertions.
The existing immutable Data & Lab consumer release remains `0b204cde`; no consumer
reinstall, live quote publisher or scheduler is caused by this source acceptance.
The Tiingo/BOATS programme continues through its remaining real delivery gates.

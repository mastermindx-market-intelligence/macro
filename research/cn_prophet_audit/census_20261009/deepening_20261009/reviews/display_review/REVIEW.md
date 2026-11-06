# Independent display review — one remaining blocker

**Do not accept the original candidate's absolute 30-second request-lifetime claim yet.** Candidate SHA-256 `595b83e907eabfb9e0df4ba3df4a2c3aad0f606c993ac345e4fccfd47d2176bc`, sealed by subject manifest `5bb6c5b3b76d1f2739bd5f362b042c11b3d4e17d5f57fa4552c38ad83864b549`, passes the producer's 28 controls and 27 of this review's 29 additional controls. The two failures are variants of one deadline-consumption defect.

All source and candidate files remain unchanged. The exact copied producer harness produces byte-identical `results.json`, including its 28 controls and 12 native comparative failures. The additional harness is independently written and separately defers response headers, JSON body, wall-clock advancement and queued timer callbacks. It executes the exact native and candidate IIFEs, with no browser or network.

## D1 — A delayed timeout callback can be canceled by an overdue response

The candidate uses `setTimeout(..., FLOOR)` to establish its 30-second request lifetime, but its response-consumption branches only check request sequence identity. They do not check the current instant against the request's deadline. A response can therefore complete after the deadline and cancel the overdue callback before that callback runs.

The retained reproducer uses this exact schedule:

1. The request starts at `2026-10-09T02:00:00.000Z`.
2. The synthetic wall clock advances by 30,001 ms without executing queued timers.
3. Either the response headers arrive, or a previously started JSON-body promise resolves. The response contains an otherwise valid fresh artifact.
4. The promise chain paints `Forming / 正在形成`, clears the deadline timer and releases `_fetching`.
5. Running the queued timers afterward leaves the chip visible and the request un-aborted.

Both the header-completion and body-completion variants reproduce this behavior. They are saved with complete before/after snapshots in `REVIEW_RESULTS.json`. In both, the candidate has one request, its abort flag remains false, the current clock is `02:00:30.001Z`, and the live chip remains visible after queued timers are allowed to run. The native source also paints in this schedule; the point is that the proposed deadline repair has not closed it.

This experiment supplies a deterministic asynchronous ordering that the repair does not guard. It does not claim to have measured a browser's task-source scheduling or an observed production incident. The candidate's own stated suspended-tab limitation already distinguishes elapsed time from timer execution. A callback deadline alone cannot establish the claimed absolute admission rule when callback execution is delayed.

### Smallest correction

Retain the request's absolute deadline instant and check it when consuming headers and again after JSON resolves, before applying the artifact. Use the same deadline-invalidation behavior to prevent an overdue current request from painting or holding `_fetching`. Preserve the request-sequence guard so a deadline or response from an obsolete request cannot erase a newer accepted chip. Keep the independent artifact-age expiry and polling cadence unchanged. Do not weaken the existing source-age, authentication or schema refusals.

Acceptance for the separate repaired candidate should rerun both delayed-timer variants, exact 30-second boundaries, a JSON-body completion spanning the deadline, the existing producer controls and the independent obsolete-response/timeout/SSR controls. Actual browser/API acceptance remains a separate implementation gate.

## Behavior that passed independently

The review confirmed that obsolete header errors, body errors and late JSON completion cannot override a newer state or authentication refusal. An obsolete timer cannot remove a newer chip. Executed timeout callbacks make late responses obsolete even without AbortController, and polling recovers after both header and body stalls.

The candidate accepts the final millisecond below MAXAGE, rejects the inclusive age boundary, accepts exactly the 60-second future-clock tolerance, and refuses one millisecond beyond it. A near-expiry artifact tears down at its own boundary. Visibility resumption removes an expired chip before a fresh response arrives.

404, 429, 500 and 503 remove the optional live layer. In each case the original server-rendered card order, ranks and text remain byte-for-byte equivalent in the fixture, and live tooltip attributes are removed. A current JSON failure clears the old chip; a subsequent valid response restores both `Forming` and `正在形成`. A page without the existing stocks header does not start requests. The entire bilingual STATE/STATUS table is byte-identical to the pinned source.

## Preexisting vocabulary qualification

The unchanged `pair()` fallback echoes an unrecognized state token. Both native and candidate display a synthetic wire state of `confirmed` literally. This is retained as a preexisting scope note, not counted as a new deadline-repair blocker. It means that byte equality of the vocabulary table is not, by itself, validation of arbitrary incoming enum values. The current review does not broaden the agreed repair into a new wire-schema policy.

## Exact evidence and reproduction

| Item | SHA-256 |
|---|---|
| Reviewed candidate | `595b83e907eabfb9e0df4ba3df4a2c3aad0f606c993ac345e4fccfd47d2176bc` |
| Reviewed subject manifest | `5bb6c5b3b76d1f2739bd5f362b042c11b3d4e17d5f57fa4552c38ad83864b549` |
| Independent executable, `review_display.mjs` | `41cd321eeb6de5b2d1641f2bd0f5d840e99054daa7f2b7de4e0bff90bb994792` |
| Independent results, `REVIEW_RESULTS.json` | `0dbfe553c22bb60d6e5fb05b6b92739eb96c0013b0dbd24d1c8d8e1ea03acb72` |
| Byte-identical producer replay results | `bf41dee7453600d9b6008f8653a74852c453a669bafaa975e6e49a33d63c4dfa` |

Run `node review_display.mjs` from this review directory to reproduce the 27 passing controls and two deadline counterexamples. Its process exits successfully when the review completes; the JSON review status remains `BLOCKED`. Run `node producer_replay/verify.mjs` for the unchanged producer control set. Both commands write only review-owned result files. After sealing, use a copied review directory for another run if the retained artifacts must remain immutable.

The initial development run exposed an unattached rejected body promise in the independent harness's obsolete-body-error setup. The setup was corrected to begin JSON consumption before superseding the request, and the final exact-version run exits 0. That harness setup error is not counted as a subject finding. The original and repaired display candidates must remain separate immutable artifacts.

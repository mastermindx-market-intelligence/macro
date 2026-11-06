# M2 Fabric backend review r2: receipt and bounded repair

Original root/parent: rotation-intraday-session-research-20261013; Macro PR #9196. Original child rotation9196-semantic-review-r2 is TERMINAL/rc0/signalok. Its exact text-only return is 7625 bytes, SHA256 9e617bf7a2689b915d7147ace365e1d375e2ab9f8fe3923198739e2e93547bff. Reviewed source was 460af1ea68880543d880801b0838d970643e5a75; verdict CHANGE_REQUIRED. No tools or source effects were claimed by this reviewer. The result is useful review delivery, not subject approval.

## Accepted findings and repairs

1. Closing measurements were erased by a subsequent successful identical settled recompute. This confused a measurement with a newly issued event. Repeated identical qualified closing data now retains the previous observed closing interval with unchanged reference/source timestamps and numbers, delivery_state=retained and is_new_observation=false. A genuinely new interval carries new/true. The same last-good file remains the sole transient baseline; no history store or detector is added.

Retention requires the existing same-session/schema/baseline checks, a byte-equivalent normalized benchmark, identical economic membership, and unchanged normalized member points. It does not carry a correction, missing member, rewound benchmark, changed membership, or a different source/basis. The current consumer applies its existing 45-minute limit regardless of retained delivery. Grounding names a retained observation. A correct measurement can remain visible without issuing another event or refreshing its clock.

2. A caller-provided naive evaluation clock could reach source reads and erase the reference through a None baseline. build() now rejects non-aware clocks BEFORE any source read/write. Tests assert the old sidecar bytes survive untouched. Default now remains an aware UTC clock. The review's alternative post-session live-mode counterexample is unreachable under the existing mode selector, which routes post/closed directly to last_rth; no broad None-means-preserve rule was introduced because intentional session resets must still work.

## Proof

New discriminating controls first fail on the predecessor. The combined eleven-module suite now passes 632 tests. Controls cover repeated retained closings at 21/26 minutes, expiry beyond 45 minutes, corrections, membership changes, older benchmark and missing-member abstention, naive-clock no-read/no-write, and contradictory delivery metadata. The earlier two closing tests now distinguish retained observed values from new observations instead of enforcing the old erase-on-repeat mistake.

closing_retention_replay.json executes the real producer and grounding modules with synthetic source files; it carries exact source hashes. Repeat statuses remain observed while repeat_is_new_observation is false for both groups. No live market behavior, financial predictability or production deployment is established.

UI source remains frozen at its independently reviewed 3b53a64 candidate; only its capture harness was strengthened to verify no extra fetch on Show all, expansion persistence, and overview behavior after denial. Template hash and screenshot identities remain bound in ui_proof/browser_report.json. The current UI already shows original source intervals; retained-delivery rendering in the machine consumer is explicit.

## Next

Obtain a bounded review of this exact retention/clock-validation delta, consume the disjoint UI review, qualify the final head in hosted CI, then normal source release and authorized live proof. r2 completion is not code approval. The previous r1 task remains unaccepted because of its recorded scope deviation. Current capability is BUILT_NOT_PROVEN, with no Executive plugin, source swap, credential change, live alert or trade.

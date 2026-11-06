# Final regular-session rotation observations: source-qualified closing path

Same operation and Macro PR #9196. Predecessor source 046b3705ec3f042be03bf2333a7131e04acb660a is published but not released. This increment does not implement full overnight trading or admit a financial signal.

## Real retained-source finding

The single retained full quote snapshot at live-data commit 99f656615250e527aec8bcc2389a08b2e658ea90 contains 700 of 702 active member quote objects. Applying the predecessor's strict regular-session point boundary admits only 88. The other dispositions are 610 stamped after the regular close, two before the relevant session, and two absent. All 610 later-stamped observations carry price basis regular. Exact source binding: quotes.json SHA256 ef51fdd92bccd72e721af7452f2379e107cb1131e677b9626319d6d3550b772b. No prices are copied into these evidence documents.

The 610 late source timestamps divide into 419 within two seconds after the bell, 104 more than two but at most five seconds, six more than five but at most sixty seconds, three more than sixty but at most ninety seconds, and 78 more than ninety seconds. Source engine/live_quotes.py::parse_yahoo_spark takes regularMarketPrice and regularMarketTime from the same vendor metadata and marks basis regular; it does not substitute postMarketPrice. These facts support a separate, explicit settlement observation path, not a broad relaxation of intraday timestamp limits or a claim that arbitrary late trades occurred during regular hours.

The predecessor also evaluated intraday comparisons only while the build wall clock was in regular hours. Delayed closing evidence arriving after the bell went through the existing settled daily recompute without a final observation comparison. This can lose the final regular-session handoff even though the daily settle is retained.

## Bounded implementation

The existing successful US settled-close builder can now attach the final matched-member comparison. It reuses the same transient last-good baseline and the existing 90-second settlement tolerance. Only source-designated regular/day prices from one minute before through ninety seconds after the actual close qualify for this explicit closing endpoint; trade/minute after-hours bases remain excluded from this new path. Source stamps are retained exactly, never clamped or backdated to the bell. Normal intraday comparisons retain their strict regular-session source bounds.

The observation is tagged settled_regular. Its build mode remains last_rth/settled_close, and the actual Market State Packet consumer renders regular-session close beside the measured interval. The consumer requires explicit settlement metadata and applies the same bounded v1 envelope, existing freshness budget, arithmetic checks and source-skew checks. Repeated snapshots do not emit another measured interval. Same-day membership, benchmark, price-source/basis/reference and monotonic-baseline rules remain.

US wall-clock session classification and settled-close lookup now reuse the existing actual-close owner, including early closes. No holiday rule is copied; HK behavior is unchanged. The earlier half-day negative test now asserts the correctly classified post-close path still refuses observations 29 minutes after the early close and retains the prior pre-close baseline.

## Evidence and limitations

- Test-first closing slice: 13 failures and 4 passes on the predecessor.
- Eight-module integrated functional run after the change: 525 passed.
- Full-day and half-day synthetic tests execute the real builder and grounding consumer with late-arriving, one-second-after-close source stamps. Final daily changes are zero while the earlier observation-to-close returns remain -1.960784% and +1.010101%. Grounding explicitly calls these regular-session-close observations.
- A repeat closing snapshot yields no new observed comparison. Regular/day points within the bounded settlement window pass; 91-second-late points, generic trade/minute bases, and stale/future/malformed consumer inputs remain excluded.
- Applying only point eligibility to the same real retained snapshot now admits 617 member observations; 614 are aligned within the existing upper 60-second SPY tolerance. All 49 inspected groups reach at least 50 percent one-point alignment. The 78 source stamps beyond ninety seconds are not admitted. All accepted timestamps equal their original source timestamps.

That last witness is ONE observed closing snapshot, not two endpoints, a live production rotation, regular-session feed freshness, a historical performance result, or an account-rights attestation. The additional 532 near-close source stamps are admitted by explicit settlement provenance, not invented or forward-filled. The fixed existing 90-second tolerance is not fitted to future returns. No complete overnight path is inferred from a close-to-open gap.

## Exact remaining acceptance

Independent review of predecessor d5e076c remains unresolved under original child rotation9196-semantic-review-r1; it cannot approve this later source. Consume that original child before replacing/recommissioning it. Required checks must qualify the final published source and current-base integration. Production/private source-to-consumer and actual user-interface proof remain unperformed. No new source feed, history store, notification, trade, credential or production deployment was created by this increment.

## Provider transition remains a real qualification boundary

Current engine/live_quotes.py routes post-close US snapshots toward Yahoo regular-session fields, while the regular-hours path may use Polygon. This does not prove a particular deployed source switch, but it makes provider/basis continuity a necessary real-path check. An additional regression explicitly refuses Polygon/minute -> Yahoo/regular stitching as benchmark_basis_changed. The new closing path works only when both endpoint source conventions qualify; it does not claim production cross-provider normalization or relax the source-signature fence to improve apparent coverage. A single closing snapshot cannot establish this paired condition.

# China flow-window diagnosis — no product repair

Operation: china-participation-context-20260921-sol-001; original PR7622 and locked Studio carrier.
Pickup: d47697f9b825013319640e5c266e2f99ada65612.
Protected Skillpack: Mastermind@f1c070d733c4683b20bbbd9af8fae6c30dc38d84; v1.0.1/bootstrap1.
Authority: current Chairman continuation; exceptional review waiver and deferred CI/release retained.

## Reproduced data-integrity problem

The existing engine/china_internals.py:southbound_flow drops missing net observations before
selecting its trailing20 entries. The calculation can pull an older flow into a period still
labelled20-day cumulative. The latest valid row also silently substitutes for a missing tail.

A synthetic21-row example has +200 in the oldest row and -5 in every later row.
The complete latest20 sum to -100. Replacing one of those20 values with a null makes the current
reader reach back to +200 and report +105. Replacing the latest row with null has the same
sum effect and still reports an undated latest net of -5 from the preceding observation.
A one-observation history emits a20-day total of -5 and a nonfinite net_z (NaN).
These are synthetic units, not observed Chinese flows, return percentages or qualified currency.

Four scenarios were executed twice, including through the committed reproducer. This is diagnosis,
not four passing acceptance tests. Source and fixture inputs were unchanged. The JSON receipt
encodes the nonfinite value as null and separately records its exact field; it does not hide it.
Reproducer: research/grey_deer/probe_china_flow_window.py <evidence-json>.
Source SHA256: 44bd35e2a4d0ae53cc93f04bf739df8dc13c7e4a0dfe6e730aa03c83a59c5640.

## Why no repair is claimed

A fresh source-owner/current-main qualification command was explicitly blocked by OpenAI before
execution: "we couldn't determine the safety status of the request." No PID or source effect was
returned. That specific compound read was not repeated, split up, delegated or sent through another
connector. The independent synthetic probe reads the already-known parent function; it does not
supply the denied ownership/current-main evidence. No engine or registered test was edited.

The original device's non-mutating get_config succeeded. The worktree is inside its allowed
filesystem roots; this is not evidence of an offline Studio or a missing sudo permission. The
backend configuration is not permission to override the separate platform refusal. It was unchanged.

P0 PR7875 remains cd0bcb0f257fc92e7f42b1fb8c90c7307475d0b6 at pickup. Its latest message is the
existing recovery request5814095625; no newer committed correction or pickup receipt was returned.
The earlier observed dirty P0 source must be preserved. A read of Executive hot-state code showed a
read-only aggregate projector, not a callable operation-specific writer-recovery action. No runtime
state was queried through that module and no inactivity or lease expiry is inferred. No duplicate
worker or recovery request was created. A bounded P3 operation search returned no matching PR;
that is not proof that the research does not exist or its worker stopped.

## Current release frontier

P0 requires its original writer/custody reconciliation and an exact source/test/browser return.
NBS29, weight16, render-write54 and episode-feed18 cases retain their original action-specific holds.
The existing China normalization/browser hold and source-identity read hold have not recovered.
Current-main composition and live acceptance remain owed; CI/release are deferred, not waived.
Known risk/participation/P2/Signal Lab repairs remain DO_NOT_REDO at their existing proof hashes.

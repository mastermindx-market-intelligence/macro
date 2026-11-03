# Intraday Flow R3 — source-details implementation and proof

Recorded 2026-11-03T07:16:18.623052+00:00. Original PR10498 remains Draft/HOLD.
This is candidate/source and isolated-browser evidence, not independent acceptance.
Predecessor published head:5ad690329824a470529a235474d1f8eae3a18585.
Verified upstream integration:d992e30aac5f012f0f7aa70428e49dd0758f8e59
(main19a896b97ae20f2c12475a0207678f92dc4f335b). Frozen R3 plan:16c375b8966ad36786b60d26d8a365cd9930bbf3.
Material source identity is the commit containing this record (no self-referential hash).
Generated page SHA256:`c47d76bb22886c74dbf65f9d0a885a1d88359ad5261f3a213a24a237d4b45b96`.

## Capability

A native source-details disclosure now sits beside the existing Refresh action. It
shows price, volume/VWAP and options independently, with source clocks, limited
coverage and producer-marked-stale state rather than inventing a current signal.
The existing brief LENS explanation remains unchanged. A static panel header and
controls survive feed refresh; only changed source rows are updated. The native
popover owns opening/closing/Escape and focus return. Refresh delegates to the existing
handler, without a new fetch/poll/retry plane. Scan filters and selection are preserved.

Light and dark treatments use canonical tokens in the paired page stylesheet; the
light panel uses institutional paper/shadow and the dark panel uses graphite/luminance
depth. Mobile actions have44px targets and avoid the floating assistant column.
English/Chinese names, scope, statuses, source clocks and actions are explicit.

## Red-first and verification

- New template/site source contracts:28failed before implementation, then28passed.
- Combined scoped suite:`python3 -m pytest tests/test_intraday_flow*.py tests/test_workflow_file_size.py -q --disable-warnings --tb=short` →329passed,12warnings,19.44s.
- Existing browser regression:515/515passed (`browser_verification_r3.json`).
- Source disclosure matrix:201/201passed,8screenshots,1440/390×light/dark×EN/ZH
  plus limited/missing transport cases. Native opening/labels/initial focus,44px
  geometry, observed zero, independent sources, missing clocks, Escape/Close/Back
  return, refresh-focus retention, live language changes and filter preservation tested.
- R2 recovery compatibility:244/244passed with16screenshots saved separately in
  `recovery-r3-compat/`; historical R2 files were not overwritten.
- All24 current state-specific screenshot digests verified against their reports.
-15protected model functions and5fetch/polling functions are byte-identical to5ad.
- Paired CSS equal; three executable inline scripts pass Node syntax checks.
- Added-diff design-system ratchet:0newblockingfindings; inherited estate25157
  findings remain nonblocking historical debt. Runtime style budget passed:146JS
  files,44injecting,88hits within existing allowance. Scoped whitespace passed.

Two integration test issues were investigated without weakening assertions:
1. An old isolated clock fixture returned the same mock element for every ID. It
   now resolves only `ift-source-times`; the new panel correctly returns when absent.
2. An HTTP200 empty legacy options object is treated by the existing off-hours
   status rule as delivered; that was not an unavailable-transport fixture. The
   new browser test now uses the same explicit503 unavailable response as the
   existing harness and waits for the terminal state. The underlying model was
   not modified. This demonstrates why status is not current confirmation.

Transport cases are explicitly SYNTHETIC TEST FIXTURES, including a deliberate zero
price and absent clocks. They are intercepted in the anonymous browser only, never
written to feeds or treated as real market observations.503fixture responses are
intentional failure inputs, not claimed clean production network evidence.
Full-repository pytest is not represented by the scoped suite; hosted CI remains owed.

## Paper design and implementation mapping

Exact file01M2WGNCX9475G79JRKJTCM08P/pagep-26-1. This turn added and inspected
light/English source-details board6ZVB-0 and dark/Chinese counterpart6ZYE-0. Both
are390×844, illustrative/not-market-observation labeled, editable JSX verified,
computed styles verified and working indicators released. There are8boards total.
The product uses the existing native-popover pattern rather than introducing a new
route/overlay control plane; the source meanings and controls follow those specimens.
The native platform Close and Escape are tested on actual candidate code.
Other Paper state/locale coverage and qualified independent visual taste remain open.
The prior platform-refused dark-Chinese ticker-row batch was not replayed.

## Recovery/integration provenance

The original C2 gateway returned502 during an attempted local integration. A separate
read-only gateway diagnosis through the authorized M2 device changed/restarted no
service and accessed no source worktree. Later exactgateway tools/call200 evidence
enabled original-carrier reconciliation PID97008: clean5ad, noMERGE_HEAD, staged
changes, unmerged paths, log or activeoperation. The source lane was then resumed
under fresh expected-head guards. Main integration and page regeneration passed
301prior scoped tests and515browserchecks before R3 implementation. Details are
in MAIN_INTEGRATION.md; no outstanding uncertain source effect is carried forward.

## Release boundary

No independent R3 source or human/Opus visual approval is claimed. The existing
R2 review request remains REQUEST_REFUSED_BEFORE_LAUNCH/EXECUTION_NOT_ELIGIBLE,
retryfalse; its original owner must diagnose actual eligibility, not reroute/replay.
Desktop shared-navigation displacement and production current-feed proof remain
separate obligations. Latest-head hostedCI, complete visual acceptance and lawful
served release are required. No Ready/un-draft/enqueue/merge/deploy occurred.

## Fresh canonical verification — 2026-11-03 continuation

The assigned successor recovered the original clean M2 workspace at published
`dcda26d6d58bce0cbbe798d659eb7cdb8f755f9c`, with no merge/index lock, unmerged
paths or competing worktree process observed. Product blobs match material R3.
The existing canonical driver then captured24/24 states; all24 SHA256 digests
verified, with zero console errors/failed responses/horizontal overflow. Principal
visually inspected all eight resting layouts and the two existing Paper R3 boards.
See `mockups/refs/intraday-flow-upgrade/source-r3-canonical/verification.json`.
No source-detail rebuild, main reintegration or denied-effect replay occurred.

Resting lab CLS is desktop0.67893–0.88082 and phone0.00994–0.02440; no performance
acceptance. Actual committed base snapshot is76f8f28816e347866a59b90e3d8c2ee1654786e9dbec13eddcdc750e0bf3fe18,
brought by the already-existing main integration. Historical R2 snapshot references
are superseded only for current R3 evidence. Existing329pytest/515browser/244recovery/
201source-detail results remain explicitly historical executions; this continuation
reuses product-identical evidence instead of claiming reruns.

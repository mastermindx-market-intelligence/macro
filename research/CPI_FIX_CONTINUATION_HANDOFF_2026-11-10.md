# CPI release repair — active continuity (2026-11-10)

## Mission and delivery carrier

Fix the user's CPI incident end to end: one correctly dated current release, immediate verified monthly figures and explanation, no indefinitely extracting historical card, and coherent event-related dashboard updates.

Carrier: [Macro PR #10930](https://github.com/mastermindx-market-intelligence/macro/pull/10930), branch `claude/ssd-t3-4a5c5a78-4511ebb22558e9b4`.
Original accepted repair head: `0cdbec5f81eddf3274b6de5c55889f67526fe803`.
Current session owns source repair and recovery under [incident takeover / HOLD](https://github.com/mastermindx-market-intelligence/macro/pull/10930#issuecomment-6769151750).
The historical pre-release handoff and its proposed all-four-values acceptance are superseded by this actual-release diagnosis.
Protected Mastermind procedure pin: `d8dc1873077867f8ddd281c9f98a63bb0b3258df` (bootstrap major 1).

At this source checkpoint the PR remains disarmed (`merge-blocked`, no `merge-on-green`).
The first incident successor was `aead22099dde9a88a6d08b82b19e2cd73da67779`, integrating original candidate and main `0267bf8fffc083cd048504bdb5c8e775025d6396`.
This substantive successor integrates that exact candidate with actually healed main `ecd19ef130b4405df2e72c12787cb59382702c10`, including accepted admin PR #10897 at `165d4b20953a347dea439c4fb92bcb1d0c84794c`.
Its tree starts from the new main. The six parser/watcher/client/test preimages remain byte-identical to the prior receiving main; all seven owned code/test/fixture postimages are unchanged. Current generated pages are preserved with only the live-client hash stamp changed.
The accepted current CI definitions, navigation placement, receipt contracts and other main changes remain untouched. Do not use a stale GitHub test-merge tree.

### Resolved CI dependency

Natural run [42833316319](https://github.com/mastermindx-market-intelligence/macro/actions/runs/42833316319) for `aead220` completed failure at 15:28:11 UTC: ten packs passed; pack 7 failed the inherited admin navigation inventory guard, and pack 2 failed absolute-parent path pruning. The semantic gate also refused self-excusal because the candidate changes the protected `scripts/` surface. That protection remains in force; an all-pass successor can qualify without an exemption.

Both required repairs are now accepted on main through #10897, whose commit explicitly adopts the previously reviewed source correction. Exact main blobs: `tests/test_admin_navigation_ux.py=c658d3630135dcad868c3e2664be2ddd652c9e54`; `admin/deploy/stage_capacity_observer.py=7918254d593080a7f9a8ab0cc3bd03b96aaf4ae5`. These match the two-file repair also carried by #10958. Main additionally includes the analytics suite registration in `.github/ci/legacy-jobs.yml`; it is preserved unchanged.

Controller run [42841815989](https://github.com/mastermindx-market-intelligence/macro/actions/runs/42841815989) had deferred #10958's stale-proof refresh for capacity after #10897 merged. A fresh exact-file main read resolved the dependency: #10958 itself need not merge again. No competing heal, controller override, manual refresh, new priority or second carrier was created. The next valid action is qualification of this substantive integration on the original CPI PR.

## Proven incident causes

1. The apparent pre-release or double detection combines two event IDs. `cpi:2026-10-14` was detected at `2026-10-14T12:31:17.596439Z` (08:31 ET) and remained unparsed. The old client retained it indefinitely and showed only the time. It was not a premature detection of November CPI.
2. The October parser failed after BLS changed the annual sentence order. Original PR fixes those phrases and prevents borrowing an energy/shelter annual number as core CPI.
3. Today's distinct `cpi:2026-11-10` was detected at `2026-11-10T13:30:39.365933Z` (08:30 ET). BLS published monthly headline 0.4% and core 0.3% for October 2026 but explicitly did not publish these two annual comparisons because the corresponding October 2025 survey data are unavailable. The old parser required all four values and rejected this valid release.
4. The CPI feed contains both monthly readings but omits the missingness notice and Table A. A parser-only change would still fail in production. Existing CPI configuration did not follow its selected entry to the full release.
5. The Fed dialog's date-bound `Next CPI · 1d` schedule row was not a client update target and would retain its old prospective sentence and tooltip.

## Official-source evidence

- Archive: https://www.bls.gov/news.release/archives/cpi_11102026.htm
- Feed: https://www.bls.gov/feed/cpi.rss
- Selected entry: `cpi-2026_11_10__07_55_47`.
- Observed feed SHA256: `d643c50862942c7de2997367c28d681cedad74f629ec67c9dd203d9b5e6ea43a`.
- Selected entry-body SHA256: `db2a91273f0fd0692f407107a3b0102e7d26cd48fa31903846a626460f626293`; matches the live unparsed row.
- Full archive: HTTP 200 through the existing production collector, 1,366,766 bytes, SHA256 `7041541ddfc6fc155e33eab0d191e6dff6ba44c1b847921f1926cf9425126c18`.
- The committed reduced fixture preserves the opening PRE and Table A verbatim; navigation, later tables and notes are omitted.
- Table A binds headline/core current monthly 0.4/0.3, previous monthly 0.6/0.3, and annual cells `-`. Other series have valid annual values; the general notice alone is not adequate series-specific evidence.

## Successor behavior

- Complete CPI feeds retain their existing fast path with no extra request.
- Incomplete CPI entries reuse the existing detail reader/cache/304 recovery. Exact BLS dated archive URL, embargo-header release date and title reference period must all match the selected event. A stale document's mention of the next release cannot satisfy identity.
- Both monthly readings remain mandatory. Annual missingness is accepted only when the current-period official notice and the individual Table A cells prove it, with monthly table/prose agreement. Missing, malformed, contradictory or mismatched evidence remains unparsed.
- Unavailable annual scalars remain null and are absent from numeric `metrics`; additive `unavailable_metrics` explains the official reason. No zero, annual estimate or borrowed series is invented.
- The bilingual summary states the monthly readings and annual unavailability. Same-table monthly comparison states headline eased 0.6% to 0.4%, core held at 0.3%. This is a source-backed comparison, not a consensus-surprise or trading claim.
- Parser contract remains `cpi` v1. The existing normalizer produces exactly the two valid monthly receipts; no canonical ledger is manually edited.
- Original detection time and event identity are retained across recovery/replay.
- The paired client retains the original seven-day unresolved display boundary and dated old stamps. The exact-date CPI schedule row now transitions through verifying/detected/released, replacing stale prose and tooltip without changing separate Fed model numbers. Other scheduled dates are untouched.
- Existing collector and client clocks remain approximately 60 seconds each. The client updates an already-open event modal on its next poll. No new polling owner, publisher, queue, daemon or automation is introduced.

## Verification completed before publication

`python -m pytest tests/test_official_release_parsers.py tests/test_release_publications_live_client.py tests/test_release_actuals.py -q`: **91 passed** with one unrelated installed-anyio/pytest deprecation warning.

The focused checks cover the observed official November fixture, legacy and October phrasings, per-series missingness, wrong table/notice/date/archive evidence, neighboring-series contamination, genuine zero, unchanged complete-feed request count, detail 304 recovery, preembargo suppression, one-event replay, original detection time, exact document hash, both monthly receipt integrity, paired client/stamp consistency, and date-bound bilingual CPI schedule updates.

The initial local extra-client-file staging newline and absent committed ledger fixtures were corrected by materializing exact source inputs; they were test-fixture setup issues, not product regressions. Prior handoff's unverified PCE-failure claims are not the current result: the complete 25-test receipt suite is green in this checkpoint.
A standalone local headless-browser launch is unavailable in this container because the process singleton socket syscall is denied. No launch flags or alternate process carrier were used to evade it. Live browser UI acceptance remains outstanding; do not claim a browser pass from these unit tests.

The candidate parser was also replayed in memory against the complete official archive using the existing production collector: HTTP 200, 1,366,766 bytes, expected SHA256 `7041541ddfc6fc155e33eab0d191e6dff6ba44c1b847921f1926cf9425126c18`, exact document identity true, correct monthly/annual-missing packet and bilingual summary. Diagnostic process 5641 exited 0. No production file or service was changed by this proof.

The unchanged candidate was also replayed read-only through the real production state and existing collector. Diagnostic process 28331 exited 0: the existing November event advanced in memory from unparsed to ready, preserved detection time `2026-11-10T13:30:39.365933+00:00`, recovered the full official archive through feed-304/detail handling, and produced exactly the two monthly receipts with no integrity errors. No state, ledger, service or deployed source was changed.

Authenticated Chrome confirmed the production baseline: two extracting cards point to distinct October/November archives. Production preflight at 15:05 UTC confirmed the timer/service is healthy and normal main pickup works, but November remains unparsed and the deployed client is still the old `d9a19340` asset. Live acceptance is not yet proven.

## Remaining acceptance and next safe actions

1. Read back the substantive successor commit, exact branch head/parents/diff, then consume its natural CI and fences. Do not reuse the old candidate's green checks.
2. If the owned repair HOLD conditions are satisfied, record `HOLD-RELEASED` for that exact head and add `merge-on-green` once. The incumbent controller owns merge and its `merge-blocked` disposition; no self-merge, fabricated priority, noop push or CI bypass.
3. Verify actual merge, VPS `/opt/macro` install via the existing pull cron, and the existing fast watcher. Read the public sidecar: today's CPI must be `published`/`data_ready=true`, with the correct monthly figures, explicit unavailable annual values, original detection time and full-document evidence.
4. Verify the real dashboard: one current CPI card, explicit explanation, OUT calendar state, existing open-modal update, no historical October extracting card, and resolved matching CPI schedule row. Observe replay without duplicate insertion.
5. Save final receipt/URLs and readback in the same PR. Do not end merely because a commit, PR or CI phase completed.

## Boundaries and DO_NOT_REDO

- The historical October row exceeds the watcher's seven-day retry horizon. The client hides it; this change does not manufacture its historical ledger repair. Status health may still mention that historical unresolved record.
- No full AI Brief regeneration, forecast model rebake or canonical scoring advance is claimed by the publication sidecar. Those retain their existing owners. The verified event summary is available immediately through the existing live consumer.
- Original October parser/client fixes and accepted CI pins are retained; do not redo independent review as ceremony.
- Native children were bounded read-only contract/release reasoning, accepted and stopped. No paid-worker operation, background watcher, review approval or external notification was created by this recovery.
- Root completion still requires production payload and UI evidence, or a precisely evidenced execution boundary.

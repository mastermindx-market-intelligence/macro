# Quiet live-news heartbeat repair — 20 October 2026

Owner operation: `news-stream-heartbeat-20261020-c3`.
The only runtime change is the quiet SSE heartbeat from 15 seconds to 5 seconds.
The immediate flush, cursor, fresh permission checks, shared reads, 0.1-second
polling interval, data frames, cancellation and error handling are unchanged.

## Observed problem and bounded diagnosis

A controlled authenticated Terminal reload at 18:15:37 UTC still produced
repeated stream reconnects. The retained origin diagnostic window was requested
through 18:22 but was read at 18:21:13, so its actual coverage ends at that read.
It contains 17 Caddy warnings for HTTP/1.1 `/api/news/stream`, all
`aborting with incomplete response` / `reading: context canceled`.
Examples of API HTTP 200 start to Caddy close are:

| API start UTC | Caddy close UTC | Approximate elapsed |
| --- | --- | --- |
| 18:15:47.401955 | 18:16:02.867088 | 15.47 seconds |
| 18:16:08.244017 | 18:16:23.822132 | 15.58 seconds |
| 18:17:06.472882 | 18:17:21.583779 | 15.11 seconds |
| 18:18:38.849147 | 18:18:53.963961 | 15.11 seconds |

These are timestamp associations, not a cross-service request-ID trace.
Caddy's logged `duration` is upstream response-header latency; it is not used
as stream lifetime. The installed Caddy version is v2.11.4. API news requests
in this window returned HTTP 200, with no captured exception signals.

At 18:25 the actual app hostname returned `Server: TencentEdgeOne`,
`Via: 1.1 Caddy`, `EO-Cache-Status: MISS` and private/no-store cache headers;
its CNAME is `app.mastermind-x.com.eo.dnse3.com.`.
[EdgeOne's official origin response timeout documentation](https://edgeone.ai/document/63618)
describes a default 15-second HTTP/1 origin idle deadline, including gaps after
partial-body delivery. The existing 15-second heartbeat has no timing margin.
Five seconds provides margin without changing the reader's work.

This is a strongly supported edge-idle diagnosis. The site's configured CDN
rule was not read. Deployment and sustained real browser behavior must establish
the after-repair result; source review and a successful snapshot cannot do that.

## Alternative checks and deployed provenance

The canonical read-only store-open sampler ran from 18:18:36 to 18:20:06 while
cancellations continued: 180/180 opens passed; the slowest was 4.465 ms.
It used the actual API process's database binding and effective principal.
It read no articles, used no user token, and performed no network call or database
mutation. This narrows the current storage-open hypothesis; it is not route,
SSE or user authorization proof and cannot exclude a historical failure.

At 19:03 the Terminal generation was independently reconciled:
`.deployment-id`, compiled Next `config.deploymentId`, and canonical
`.gitsrc` HEAD all identify `bbc07037aae3e98597945e23448781a091d15281`.
The service was active since 17:56:50. The constant `.next/BUILD_ID` is not
treated as a commit identifier. Neither upstream URL key was in the initial
process environment; Next dotenv resolution remains unproven.

## Regression and independent review

The deterministic regression exercises the actual async generator and proves
an immediate heartbeat, at least five comment frames in 20 simulated seconds,
and no gap above 5.1 seconds. All 201 read cycles retain cursor 7, a fresh
permission check and the existing 0.1-second sleep. It creates no database.

The old 15-second implementation failed this regression: only two frames
at simulated times 100 and 115. The repair then passed 132 tests across eight
existing API, identity/receipt, shared-reader, end-to-end and private-error suites.
Warnings are retained in the test receipt. The independent source/test ruling
is APPROVE and seals both changed source hashes. It independently read the
official EdgeOne documentation, but did not rerun the parent's tests or claim
a live fix. Published-head binding and hosted CI are subsequent release gates.

## Project checkpoint at 19:05 UTC

- Primary integration #9846 is merged, installed and the three licensed additional
  publishers were activated once. The 17:26 census proved 201 Zacks, 123 Motley
  Fool and 96 GlobeNewswire reports. Do not replay the activation.
- Private Press #9888 merged at 18:58:31 as
  `e98d4e53265d2fb6d893c3286ddd6ca55df736d2`, after both independent approvals
  and all 12 hosted CI packs plus ci-gate passed. At 19:03:18 production main
  contained that merge; all four product/test hashes matched the reviewed
  candidate and the opt-in CLI flag was present.
- The fresh 19:03 ordinary planner census still had Brief 0 / Research Desk 1.
  Its sole original current-day slot has 21 first-party facts and no ticker.
  No provider or staging operation was run. A real private draft needs a genuine
  original current-day slot with exactly one qualified ticker, or a complete
  provenance-preserving original staging record; do not manufacture either.
- The installed three grant hashes and four audiences were unchanged. Their
  operational revalidation deadline is 2026-11-19T13:41:32.940484Z; that timestamp
  is not asserted to be a contractual term.
- Existing shared render 39439974736 is still running its page-render step.
  The generated stock panel is not yet accepted live. No duplicate render was
  dispatched and the other owners' queues or branches were not changed.

Next: publish and qualify this exact heartbeat head; merge through normal gates
and deploy through the incumbent updater; then observe a real browser stream
over multiple former 15-second boundaries, the covering stock render, and the
licensed publishers' natural acquisition window. Dashboard #9612, Terminal
sidebar #1081, sector holds and the unrelated frozen W2C lane retain their owners.

## Receipt map

- `heartbeat-regression-before.json`: expected old-code failure.
- `heartbeat-focused-after.json`: 132 passing tests and exact file hashes.
- `base-integration.json`: fast-forward to merged private release without changing
  either reviewed heartbeat source hash.
- `independent-heartbeat-review.md/json`: independent bounded source ruling.
- `news-stream-window-181537.json`: metadata-only pre-repair Caddy/API window.
- `readonly-open-sampler-live.json`: actual-principal canonical open sample.
- `terminal-provenance.json`: selected deployed generation metadata.
- `private-installed.json`, `offline-press-rights-census.json`: installed private
  release and fresh original-input/rights census.
- `independent-private-consumer-ci-review.md/json`: final private CI scope ruling,
  also retained in the merged PR body.

# Independent display repair acceptance

**Accepted for the bounded offline research contract.** Subject manifest `c7448f6c4a873a2d4f6cba2e21e153583800d249bc758587186b9416642b5fd7` binds candidate JavaScript `89a9ca53f61db675128ffc31220d278e0f0b29cf7149c4f03888f829690eda49`. All 38 independent acceptance controls pass. An exact copied producer harness also passes all 30 of its controls and produces byte-identical results. These are separate, partly overlapping suites; they are not claimed as 68 unique behaviors.

The original candidate, its blocked review and this repaired candidate remain separate immutable artifacts. The original review manifest is `059222c1a1c258d11572e331b0a1ff50ae171fa88d2742e59c9886245a6e4776`. The accepted repair addresses its D1 family without weakening request identity or artifact-age checks.

## Why the original blocker is closed

The candidate now captures `deadlineAt` when a request starts. `currentBeforeDeadline()` checks sequence identity first, then enforces the absolute deadline. Both header consumption and post-JSON application pass through that check. An expired current request is invalidated, optionally aborted, releases `_fetching` and removes the live layer. An obsolete request cannot use its deadline to remove a newer result.

The original counterexamples now refuse: response headers or JSON body completing at 30,001 ms cannot paint a fresh-looking artifact even when the timer callback has not run. Running queued timers afterward cannot restore that response. The admission rule is evaluated at consumption; it no longer depends on timeout-callback ordering.

Independent boundary controls accept 29,999 ms and refuse 30,000 ms for both headers and body completion. A header accepted at 29,999 ms with JSON finishing one millisecond later is refused. An expired obsolete header or body completion cannot erase a newer accepted state. Following an absolute-deadline refusal, the scheduled poll recovers with and without AbortController.

## Preserved behavior

The full earlier independent suite also passes. It covers obsolete header/body errors and completions, an obsolete deadline after a newer response, late JSON after an executed timeout, recovery from stalls, exact artifact-age and future-skew boundaries, expiry between polls, and visibility resumption before a new response.

404, 429, 500 and 503 remove live chips while preserving exact server-rendered card order, ranks and text. Live tooltips are removed on teardown. Malformed current JSON removes old live content; a later valid response restores both language spans. A missing stocks header prevents runtime requests. The complete bilingual STATE/STATUS source block remains unchanged from the exact pinned native source.

The 30-second request deadline and 60-second future-clock tolerance remain explicit research settings for the incumbent owner to ratify. The native poll cadence and 15-minute artifact MAXAGE remain unchanged. No score, rank, card owner or page-level telemetry surface was added.

## Evidence and reproduction

`REVIEW_RESULTS.json` has SHA-256 `d355145533a8344be1b82782f96894c1aa4f164ac7f2730a4af480f8ddc6374e`. Its 38 controls include the two originally failing schedules and nine further boundary/compatibility checks. `producer_replay/results.json` exactly matches the repaired producer result `5c87aa6acb631c8ef5fe695293e5c05001824ee09baaaf026f8c0b60c77eead2`. `PRESERVATION.json` verifies every payload in the original display package, original blocked review, repaired display package and sealed integration repair.

Run `node accept_display.mjs` in a copy of this review directory, and run `node producer_replay/verify.mjs` for the unchanged producer suite. The scripts write only review-owned result files. Source/candidate hashes are checked before execution and rechecked afterward. The review manifest binds the exact executable, results, source copies and receipts.

## Acceptance limits

This is deterministic Node execution of the exact IIFE, with independent DOM, fetch, timer and clock adapters. It establishes the tested control flow and observable chip state; it does not establish deployed source identity, browser layout, actual task scheduling, authentication, device-clock accuracy or API behavior. No browser, network, vendor, deployment or operational writes occurred.

The preexisting unknown-enum fallback remains explicitly outside this repair scope: both native and repaired scripts can echo an unrecognized wire state token. Equality of the static vocabulary table is not a general wire-schema validation proof. This was not introduced by the deadline repair and is retained as the same scope note from the original review.

Before release, the existing owner still needs to bind the paired deployed script bytes to the accepted candidate and exercise the natural browser/API path, including a stalled body, visibility resumption, recovery and unchanged server-rendered card order. There is no remaining blocker in the expiry, request-admission, sequence, recovery, SSR-preservation and bilingual-copy seams reviewed here.

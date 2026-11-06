# Existing live-chip failure semantics — bounded experiment

The first census established source control flow that can leave live chips painted after non-authentication HTTP errors. This laboratory will execute the exact pinned JavaScript in a Node VM with a small deterministic DOM/fetch/timer harness. It is not a browser, deployed-page, authentication or layout test. There are no network requests or production writes.

Frozen questions: (1) Does a successful paint survive repeated 500/404/429/204 responses or a hanging request beyond the actual 15-minute MAXAGE? (2) Can a forced overlapping older response restore content after a newer error or successful observation? (3) Can a minimal existing-script repair remove stale live claims while preserving the server-rendered card order and observational vocabulary?

The candidate keeps the existing polling and maximum-age constants. Every non-OK or unparseable response tears down the optional live layer. A successfully accepted artifact arms an independent expiry at its own absolute timestamp plus MAXAGE; visibility resumption rechecks expiry. Request sequence identity prevents an obsolete outstanding response from restoring content after a newer observation or refusal. Its teardown does not alter server-rendered cards. Real browser timers can be suspended; expiry is required on resume and does not claim wall-clock execution while a tab is frozen.

Future artifact clocks, if the original accepts them, will be recorded as a separate source-time boundary. Any proposed skew tolerance must be explicit and is not a proof of a user's correct device clock. Source/session authority and actual deployment identity remain existing-owner integration obligations.

The executed candidate uses an explicit 60-second future-clock allowance and an inclusive expiry boundary. It also bounds every request, including obsolete requests, to the existing 30-second FLOOR duration, aborts when supported, invalidates its sequence and frees later polling after timeout. This repairs hanging-request recovery without increasing the existing 120-second poll cadence. Those two tolerance choices are research settings for owner ratification; they are not measured production latency or clock distributions.

The exact template/site paired-copy identity will be checked. No score, order, cap, card vocabulary, polling frequency or runtime owner is changed. All source copies and candidate diffs remain research artifacts under this directory. Acceptance is a bounded correctness result, not a release or investment result.

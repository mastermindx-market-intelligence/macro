# Live-chip failure semantics — executable assessment

The exact pinned `templates/cn_prophet_live.js` and `site/cn_prophet_live.js` are byte-identical at Git blob `5a4d08eab3ee4eebb587d19cbbd085322fb47a73`; the retained 6,651 bytes have SHA-256 `e4bfdad0781eda00f8c940047e637a6f4ac691b057b703f9eba25d9930665147`. The native IIFE and candidate execute in a deterministic Node VM with small DOM, fetch and timer adapters. There is no network access, real browser, authentication, deployed-script proof or layout inspection in this experiment.

## Findings

The candidate passes **28 controls**. The native source is directly exercised on the comparative cases and fails the candidate's required behavior in **12 individual cases**. These cases group into five practical failure families; they are not twelve observed production incidents. Candidate-only controls explicitly use `native_observed: null` rather than claiming an unperformed native observation. [Evidence: results.json; verify.mjs.]

| Failure family | Native executable witness | Candidate behavior |
| --- | --- | --- |
| Non-OK HTTP response | A previously painted chip survives 500, 503, 404 and 429 | Tear down on every non-OK response. |
| Last accepted observation expires | It remains painted at its absolute age boundary between polls, during a hanging request, or after suspended-tab time advances and visibility resumes | Arm expiry from the accepted artifact's timestamp; check expiry before polling guards and on visibility resumption. |
| Forced overlapping requests | An older response can repaint after a newer authentication refusal or overwrite the newer state | Use request sequence identity; obsolete responses cannot repaint or reset current request state. |
| Hanging request never releases polling | The current outstanding request can keep `_fetching` set, and late responses have no deadline identity | Bound all requests to 30 seconds, abort when supported, mark their sequence obsolete and allow the next normal poll. |
| Future/edge artifact clock | A one-day future artifact and an artifact exactly at MAXAGE are accepted | Reject more than 60 seconds of future skew and expire inclusively at MAXAGE. |

The existing 401/403, network exception, invalid JSON, empty 204 JSON, schema, old-session, stale-payload, dark-state and malformed-clock refusals remain effective. A subsequent valid response restores the same bilingual observational chip text. Teardown preserves the exact server-rendered card order/content and clears live tooltip attributes. A page without the existing stocks header does not start this runtime. Poll cadence remains 120 seconds; MAXAGE remains **900,000 ms, or 15 minutes**. The source's 45-minute header was inconsistent with that constant; the candidate corrects the comment. The STATE and STATUS vocabulary blocks are unchanged.

The future skew and request deadline are explicit proposed settings, not estimates from real clock or latency telemetry. At a 30-second future offset the candidate still accepts the artifact under its 60-second allowance. The actual owner's release should ratify those values, prove its source clock, and measure response behavior. A suspended browser cannot be made to execute timers while frozen; the tested promise is expiry on resume before a new response, plus normal foreground timer expiry.

## Smallest implementation change

Apply the reviewed candidate behavior to the existing paired template/site script through its current owner. `candidate.diff` shows the source change precisely. Retain the current optional live-chip surface, score/rank-free rendering and polling frequency. Register these failure fixtures with the existing surface suite; do not create a new page-level telemetry or ranking owner.

The experiment does not address the separate server-side fallback-age defect. The existing renderer must recompute its stale/unknown badge from its actual current calendar at render time, not reuse a stored `delayed:false` value. Missing or invalid anchors remain unknown; historical source identity and old board data are not made fresh by a render. That source finding remains documented in the first-pass mechanism census and belongs in the same existing-owner implementation wave.

Before release, bind actual deployed paired bytes to the reviewed source and exercise the real browser/API path: valid paint, one forced non-OK response, stalled response expiry, visibility resumption, recovery and exact unchanged card order. These natural/deployed checks remain outstanding. The offline PASS count is research evidence for the chosen semantics, not a substitute for those checks.

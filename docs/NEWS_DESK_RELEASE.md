# News desk release record

Mission: `news-cockpit-rebuild-20261018-astra-01`  
Protected law pin: `ebe2de8f0d94310241362874ec9262ba572a63d2`  
Original Macro base: `a1fe765f08975c786ae74119dce1f04859502105`

## Status

This record captures completed implementation and local design acceptance before publication. The release pull request for this mission carries the final exact-head CI, merge, render and production receipt. No live deployment is claimed by the specimens below.

## Verification

- Relevant pytest suite: **185 passed**, 2 environment warnings, 14.04 seconds. Receipt in `evidence/news-cockpit-20261018/verification.json`.
- Pure JavaScript: 15 query/normalization assertions and 4 company protocol assertions, also called by the two pytest wrapper cases.
- Mounted JavaScript: 14 aggregate and 12 company lifecycle cases; 26 passed against the canonical generated `site/news.html`.
- Canonical full build: **completed, exit 0** (5,002.41 seconds). The first local attempt lacked pinned minifier dependencies; rjsmin 1.2.5 and rcssmin 1.2.2 were installed into an isolated build-only directory before the successful run. The existing public-page builder then completed, exit 0, including the ECB news notice.
- Official-source intake: **36 accepted revisions**, 8 due sources, 5.602 seconds. All seven enabled official feeds were successfully checked; ECB and UK trade had no eligible new item. GDELT worldwide failed within its boundary and remains degraded; the second query was not selected for that turn. The receipt excludes article text and is an isolated collector test, not production proof.
- Loopback HTTP wire: **401 without authentication**, private/no-store responses, initial frame 2.31 ms, atomic amendment 1,003.11 ms, removal 1,002.97 ms, full snapshot on reconnect. The local server was stopped. These are artifact-to-wire observations, not publisher-to-screen production latency.
- Browser: 1440×900 and 390×844, dark/light, English/Chinese controls; no horizontal overflow in measured desktop/mobile states. Story and company modal behavior checked separately from automated DOM tests.

## Paper handoff

[News Intelligence page](https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-3-1)

Current task-owned boards:

| Board | ID | Purpose |
| --- | --- | --- |
| 30 · NEWS DESK · Dark · Current build | `6FXR-0` | Desktop feed and story workspace |
| 31 · NEWS DESK · Light · Current build | `6GMY-0` | Light desktop |
| 32 · MOBILE · Dark feed · Current build | `6GUZ-0` | Compact mobile feed |
| 33 · MOBILE · Light feed · Current build | `6H8F-0` | Light mobile feed |
| 35 · COMPANY NEWS · Dark · Current build | `6ITC-0` | Company reporting and activity workspace |

Working indicators for these five boards were released with an observed applied response. Earlier boards and other pages were preserved. Paper uses its existing shared theme tokens; the implementation uses the site's corresponding shared tokens. The browser is the acceptance reference for runtime geometry, localization, focus, state transitions and actual availability.

## Evidence interpretation

Browser and Paper images contain illustrative reporting and must not be cited as live news, licensed feed availability, source health or production latency evidence. The UI truthfully fell back to 10-second refresh through the temporary preview tunnel. Protocol tests and the loopback wire receipt are distinct from production transport proof.

Two Fabric commissions remain unresolved and were not retried: `news-desk-read-delivery-01` and `news-cockpit-protocol-audit-20261018-01`. Their NOT_FOUND observations did not prove execution absence and conveyed no retry authority. They supply no acceptance evidence. A lost Paper create response for the separate mobile-story board was checked against the News page; the target was absent and the mutation was not replayed. The five observed current boards above are the design handoff.

## Publication and production fields

The release pull request records its final head, successful required exact-head checks, merge SHA, covering render run, deployed checkout, API process commit, API/collector process starts, served artifact identity, authenticated route outcome and real source-health clocks. This prepublication record remains the reproducible local acceptance baseline; failures and unproven production outcomes must remain explicit in that release receipt.

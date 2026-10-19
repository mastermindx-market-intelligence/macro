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

## Final acceptance corrections — 19 October 2026

The release remains unmerged at this checkpoint. These corrections are part of the News implementation, not a production deployment receipt.

- The shared design-system scan found and corrected 31 findings in the new News stylesheet. Page-local aliases now cover both the main desk and native News dialogs, use approved shared colors/radii/shadows, and use the existing positive-status token for a connected company stream. The corrected stylesheet has zero findings in the exact repository scanner.
- Full-shell browser testing found CSS-hidden shared dialogs suppressing News keyboard shortcuts and the mobile focus trap. The dialog-visibility predicate now respects hidden and ARIA-hidden state, display, and visibility while retaining visible dialogs during opacity transitions.
- Language changes now immediately repaint the current connection message in both desktop/mobile headers and the open Coverage view. The fix retains the active channel, specific failure wording, and the original polling deadline.
- The canonical generated page was updated by replacing each uniquely matched Jinja-emitted CSS or JavaScript include. Each replacement preserved all surrounding bytes; the CSS replacement also preserved all scripts. This narrow artifact update did not require repeating the previously successful full build.
- Mounted verification after the final corrections: **29 passed, 0 failed**, 1,993.517 ms (17 News desk and 12 company cases). New assertions cover hidden shared dialogs, mobile focus ownership, immediate language changes, an unchanged active stream, and the original polling deadline.
- The new committed visual evidence package is `mockups/evidence/news-cockpit-20261019/`. It contains the full eight-cell desktop/mobile × English/Chinese × dark/light matrix, four real desktop hover/focus captures, and two additional mobile states: a connected company feed with a buffered new group and an expanded two-source group, plus a streamed story amendment with its visible warning. All fourteen accepted captures have observed state, file hashes and PNG dimensions; they are labelled illustrative previews.

### Artifact identities

| Artifact | SHA-256 |
| --- | --- |
| `templates/news_desk.css` | `a1bf8c533e154ed4b2baf19005022e2572c12247cc6c7d5b5aa6017e60481f68` |
| `templates/news_desk.js` | `fc345ae6fc8a6cfd1b06da26ff5fa953ec7aa1c1ff1e3abd4e961c7f98b5849c` |
| `site/news.html` | `def133b1e649631b414fe21da8d4e0d573bc6592e8cf6aaf46fd3d1be13a22d5` |
| Mounted News test | `98934744183db0689e60ae54f2982d08baee6c30f1b3f28311c487b95a121e13` |

### Preview transport and evidence limits

Cloudflare's temporary Quick Tunnel buffers SSE and [does not support that transport](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/). The accepted final capture set uses a separate temporary localtunnel connection, which delivered the actual preview streams. The company snapshot and grouped-source requests occasionally took 8–10 seconds through that connection and crossed the client's existing ten-second timeout. Those failed desktop company capture attempts are not accepted evidence. The UI cleared the unavailable reporting as designed; the client deadline was not relaxed for the preview.

The accepted mobile company capture proves the real stream-triggered snapshot and buffered-arrival behavior using controlled source fixtures. It precedes only the final aggregate-label translation correction; company JavaScript and CSS are unchanged. The other thirteen accepted captures use the final aggregate JavaScript. Browser screenshots were returned as JPEG bytes despite the tool MIME label; they were decoded and re-encoded as PNG with identical decoded pixels. Native-byte hashes and the conversion disclosure are retained. Neither capture fixture nor tunnel measurements establish publisher-to-screen production latency, production company entitlements, complete global coverage, or MarketOntology parity.

### CI and shared release dependency

The earlier PR run [39179400064](https://github.com/mastermindx-market-intelligence/macro/actions/runs/39179400064) completed. Its News/API/intake tests passed (68 tests), as did the then-current 26 mounted cases. The owned failures were the design findings above and seven curated CI import-closure omissions for `app/news_desk.py`; those seven paths are corrected. The new head requires its own complete CI receipt.

The inherited reference-integrity failure concerns these existing Sector Central packets:

- `research/migration_packets/MP-20261018-sector-central.md`
- `research/migration_packets/MP-20261018-sector-central-capability-crosswalk.md`
- `research/migration_packets/MP-20261018-sector-central-paper-and-acceptance.md`

At the latest independent GitHub check (19 October, 01:54 UTC), the three packet blobs and reference-integrity inventory remained unchanged on main `3d20939a6a5aa0a2e8fb5c4a11c33f1186476a48`. They lack a matching approved October reference receipt. The August approval does not cover the new October design. Recovery remains with the existing [Sector Central owner lane, issue 7646](https://github.com/mastermindx-market-intelligence/macro/issues/7646#issuecomment-6249516830). This News task does not manufacture that approval, bypass the gate, or claim a production release while it is unresolved.

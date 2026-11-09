# Scenario cards: date window, recorded progress and next checks

## Implemented behavior

Overview, Bitcoin and Scenarios now qualify each supplied case before inspection. The card exposes the observation and expiry dates, separates visit-time expiry from original progress, and labels retained instructions as recorded when their current use cannot be established.

The expiry day is inclusive in UTC. A supplied expiry of `2026-10-24` remains within its window through that UTC day and becomes expired on `2026-10-25`. An open window does not establish fresh evidence, validation, probability advantage or monitoring.

| Supplied window / evidence | Primary treatment | Progress and next check |
|---|---|---|
| Strict, coherent dates; cutoff no later than the sampled UTC day; expiry on/after that day | Supplied localized progress remains primary; no Live/Current badge | Ordinary Next check when progress is usable and evidence is not explicitly insufficient |
| Same valid dates; expiry before the sampled UTC day | Expired · historical context only / 已到期 · 仅供历史参考 | Supplied progress under At cutoff / 原始时点; Recorded next check / 当时的下一步检查 |
| Missing, impossible or reversed date interval | Expiry status unavailable / 到期状态暂无 | Recorded status and recorded next check; no inferred replacement date |
| Coherent dates with a future cutoff | Future-dated observation / 观测日期超前 | Recorded wording; no claim that the case is current or scheduled |
| Explicit `state=insufficient` or `progress_state=unavailable` | Date qualification remains independent | Price evidence unavailable / 价格证据暂无 overrides contradictory met/pending prose; any supplied instruction is recorded |
| Selected-locale progress missing, blank or nonstring | Date qualification remains independent | Recorded status unavailable / 记录状态暂无; no other-locale substitution or reconstruction from price levels |
| Next-check text missing, blank or nonstring | Other qualifications remain intact | Not supplied / 未提供 |

A genuinely expired case can also have unavailable original evidence. Expiry does not mean its condition failed, and a missing translation does not establish insufficient price history.

## Existing owners and exact integration

The implementation changes three existing presentation files:

- [Template](../../../templates/crypto_intelligence_r4.html.j2): `scenario_text`, `scenario_dates` and `scenario_status` produce typed, time-neutral fallback content for both compact buttons and full articles. Existing empty branches, titles, case order and Inspect controls remain.
- [Enhancement](../../../templates/crypto_intelligence_r4.js): pure `scenarioCardState(s, today, language)` reads supplied fields. It reuses strict `savedDay()` calendar validation and typed `savedText()`; it does not read the clock, DOM, URL, storage or global language. `renderScenarioCards()` updates only the card’s text hooks and presentation attributes.
- [Styles](../../../templates/crypto_intelligence_r4.css): the existing type scales and colors provide a compact date row, strong window qualification and muted recorded progress. Dates wrap without truncation; no smaller body type or warning panel is introduced.

Each repeated instance resolves its source through **the enclosing `data-case-horizon` plus scenario ID**. The selected 7D case cannot borrow a 30D expiry or progress value. Both repeated compact instances and the full Scenarios article update.

The existing `apply()` pass supplies one sampled UTC day and its captured language to the card renderer. Existing route and language application refresh the cards. There is no timer, midnight scheduler, cache or additional lifecycle owner; an idle page is not promised an unattended midnight refresh.

The renderer retains the original card/button and its text-hook elements. It changes text content rather than replacing the card subtree, preserving a focused opener through language refresh. Inspection continues through the existing case/horizon handler.

## Static reading and preserved authority

Without JavaScript, both forms show observation/expiry fields, **Recorded status** and **Recorded next check**. Typed string checks prevent object values from appearing as display text. The static fallback makes no present-time expiry assessment and uses no separate server clock.

The source producer normally emits no cases when the required cutoff or prior range is unusable. That genuine empty branch remains empty. Invalid-window and localized-text fixtures exercise defensive presentation; they do not authorize a new data producer.

Shared `expired()`, `progressStatus()`, `status()`, Save eligibility, current/saved drawer order, model projection, original evidence and route/history/storage owners remain unchanged. Card qualification does not replace those owners or claim that every malformed-input drawer path has been redesigned.

The retained source JSON is byte-identical. Both generated pages preserve all bytes outside their fourteen scenario-card blocks, apart from two asset-version references and three additional leading template newlines. Case identity and order remain exact. Template/served JS and CSS match.

## Executed proof

[Publication receipt](card-lifecycle/PUBLICATION_RECEIPT.json) binds the exact inputs, source metadata, case identities, observations and captures.

| Run | Result | Native process / elapsed |
|---|---|---|
| Parent reproduction and 21-file snapshot | Both retained pages, JS, CSS and JSON reproduce exactly | PID58363, exit0, 0.24s |
| Parent baseline | 40 failed / 5 passed | PID71236; 29.11s pytest, 29.535s subprocess |
| Initial candidate | 40 passed / 5 failed | PID91280; 25.49s pytest, 25.764s subprocess |
| Corrected affected checks | 5 passed | PID16003; 6.05s pytest, 6.410s subprocess |
| Publication/conservation readback | 8 changed paths / 13 unchanged inputs | PID31255, exit0, 0.09s |

**45 unique affected cases have passing coverage across the initial and corrected runs. This is not a single 45-pass run or a complete browser-suite rerun.** The correction run contains exactly the initial candidate’s five failed case identities. Runtime assets remain unchanged during correction.

Three test-harness corrections account for those five failures: one enhanced-copy assertion now reads semantic text rather than CSS-transformed uppercase; two screenshot cases now specify their horizon; two static English cases expect the existing uppercase label presentation. Initial output, JUnit, source receipts, test additions and reversible corrections are preserved.

All runs used Chrome157.0.8103.39. Baseline and initial candidate each used45 contexts/pages; the correction used5. Every run records zero page errors, outside requests and WebSocket traffic.

Affected proof covers before/on/after the UTC expiry boundary in both languages; 7D expired beside 30D open; all repeated instances; missing/impossible/reversed/future dates; missing/blank/object localized text; explicit evidence insufficiency; four no-JS states; genuine empty inputs; retained focused elements; original case/horizon inspection; current-drawer reading order; and frozen-case expiry/progress separation. Opaque saved storage and the full embedded view remain exact.

Six selected narrow captures were inspected: full and compact expired cards in EN390/ZH320, future observation in EN390, and missing expiry in ZH320. The initial EN full-group crop is also retained and inspected because its bytes differ from the corrected capture; the compact EN capture is byte-identical. Full-group crops retain the existing fixed shared launcher. [Capture references](card-lifecycle/CAPTURE_REFERENCES.json) identify each exact file and native origin.

## Editable design and next work

The corresponding references are in [Paper interaction pages](https://app.paper.design/file/01M6Y3F0NXNDPAKJMJGCAD759Z/p-1-0): Overview `1-0`, Bitcoin `4B-0`, Scenarios `BB-0` and Build scorecard `QI-0`. Exact applied Paper changes, before/after identities and finished captures are recorded separately in the programme audit.

Next: provide a same-case return from a valid current historical review through the existing drawer/history owner. Whole-drawer Close, missing-case recovery and saved-case return behavior remain distinct.

This is still a dependent Draft candidate. H5/model, alerts, paired receipts, qualified historical results, hosted/independent visual acceptance, public-route cutover and admission/release holds remain. Historical/synthetic local proof does not establish current-market freshness or production acceptance.

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

## Recovered source expansion — 20 October 2026 (not a release receipt)

The original `news-cockpit-rebuild-20261018-astra-01` workspace was recovered without replacing its branch or discarding its pending source. The incremental candidate adds the incumbent history-backed search path, bounded source/region/latency coverage diagnostics, report comparison, named investigations and quiet in-app monitoring. Historical results retain their own bounded retention and availability semantics; this is not universal publisher history, account-synchronized memory, or real-time alert delivery. The historical search and availability displays must not imply completeness when retained artifacts or source rights are missing.

Focused repair of the recovered candidate makes the publication-clock fallback select the first *parseable* source publication alias without rewriting raw clocks; confines mobile story Tab and reverse-Tab traversal to eligible sequential controls; and retains the Company News automatic HTTP 429 wait across visibility and BFCache suspension without overriding explicit Retry. The same exact corrections were propagated into the generated `site/news.html`. Discriminating pure-client and mounted regressions were added.

Verified in the recovered original workspace: **194 passed** Python API/intake/intelligence/JS-wrapper tests (3 environment warnings), **86 passed** Node pure-client and mounted tests, JavaScript syntax checks and `git diff --check`. The isolated mounted harness used the existing `tests/news-desk/node_modules` jsdom dependency and the current generated `site/news.html`. These are source/fixture observations, not a new hosted CI, independent review or authenticated production proof.

The inherited Sector proposal was subsequently de-admitted from the main migration-packet inventory through the existing Sector carrier (#7100 and #9637). This supersedes the older *News must await Sector design approval* assumption only. It does not approve the Sector design, clear any current News CI checks, prove merge compatibility with later `main`, or authorize production deployment. Retain exact-head/current-base hosted qualification, source review, controlled merge, installation, served-artifact identification and authenticated production/browser proof as separate gates.

Outstanding north-star scope remains cross-publisher entity/event reconciliation, exposure and portfolio consequences, automated durable alert delivery, worldwide push/newswire entitlements, complete translation rights and production publisher-to-paint latency distributions. Existing source-rights, entitlement, no-retry and effect-uncertainty holds remain in force.

## Resumed review repair — 20 October 2026

This is a verified source milestone in the original mission, not a release or final
acceptance. The continuing assigned session retains the next recovery action on the
same M2 workspace and PR #9612; no replacement branch or workstream was created.

The completed hosted run `39387694502` on `e4503c4242e908fc446ebf43dd9dac423b3f79bc`
passed contract-delta and eleven packs. Its only failed logical job was
`biocatalyst-deploy-integration`: `test_api_load_time_import_closure_is_covered_by_restart_regex`
found the newly imported `engine/marketing/intelligence_history.py` missing from the
API restart trigger. The exact existing trigger now includes that module; it does not
restart unrelated nightly modules or alter deployment authority.

The original independent Fabric review returned and was accepted as a diagnostic report,
not source approval. Its cached coverage-payload/revision race is repaired with the
existing re-entrant owner lock; a deterministic lock-observation regression discriminates
against the old behavior. Its no-op reporting issue is repaired by separating successful
acknowledgements from actual changed identities. Validator loss, duplicate replay,
superseded revision and failed-publication recovery retain their original source clocks.
Four guards now bind the committed News page to its exact canonical JS/CSS includes. A
stale publication-alias mutation failed that guard; the original generated bytes were
restored and their SHA-256 reverified.

Access-policy adjudication preserves the existing owner, rather than quietly repricing
or widening a surface: all four aggregate desk APIs require canonical identity and use
`enforce_site_full` under the incumbent `PAYWALL_ENABLED` launch switch. Registered
access while the switch is off is intentional; when armed, a non-entitled account is
refused before artifact access. Sixteen tests exercise the real policy across all four
routes and switch/entitlement states. Licensed Company News retains its distinct
always-on entitlement and source-rights policy. Public source inputs are not a general
free-access grant. Actual production switch state still needs deployment-path proof.

Source verification: **555 Python tests passed** (three environment warnings) across
API, intake, owner receipts, canonical page, deployment and JS wrappers; **86 Node tests
passed** with zero failures. Initial broad deployment checks exposed omitted sparse
checkout fixtures; the existing `contracts` and `collectors` paths were materialized,
then the full suites passed without weakening tests. See
`docs/evidence/news-cockpit-20261020-recovery/verification.json` for commands, source
hashes, mutation/repair evidence and child identities, and
`DSC:NEWS-COCKPIT-ACKNOWLEDGEMENT-IS-NOT-CHANGE` for the durable data-quality lesson.

A separate read-only repair-proposal request, `news-9612-diagnostic-repair-20261020-01`,
was refused before launch (controller exit 75). It returned no worker result and was
not replayed. Source repair continued directly in the already-authorized original
workspace. This does not establish an outage of every Fabric route or permission to
retry that operation.

### Ordered continuation and protected boundaries

Mission incomplete. Publish the source/evidence together, inspect actual current-main
composition, resolve only real source conflicts, and obtain required exact-head hosted
checks plus a review of changed semantics. Reuse unchanged frontend/browser evidence
only at its original fixture scope. Keep merge held until the existing protected release
controller admits the exact candidate; then verify merge-tree inclusion, natural
render/update, API/collector restart, served page identity, authenticated desk/history,
rights revocation and actual source freshness. Neither a controller-created receipt,
green local tests, source publication, merge nor fixture Chrome behavior is production
acceptance. Preserve original NOT_FOUND/no-retry and Paper effect restrictions; do not
retry them or reassign the separate NewsImpact/Terminal projects.

## Current-main recovery composition — 20 October 2026

The repaired source was committed as `23ef4907d1b380460ab3431db13a5409851f7f60`
in the original workspace. Its first typed commit attempt returned NOT_APPLIED:
the saved Agent OS discovery was outside the sparse checkout. An index-preserving
`git add --dry-run` identified that exact input error; normal inclusion of
`agentos/discoveries` made the dry run succeed, and the same typed publisher then
committed successfully. No permission bypass, alternate source carrier, replacement
workspace, or replay of uncertain effects occurred.

The candidate now composes with accepted Macro main
`902c107227006802bde8312ffd78b4685d0f7949`. Four actual conflicts were resolved:
keep all main API restart dependencies plus the exact News history module; retain
the News cockpit with main's current event rows; retain main's versioned/deferred
shared theme script on both News and Plans; preserve both sides' CI explanations
and fund only measured packing differences. All other News source/test blobs were
unchanged by this integration.

Fresh integration verification: **555 Python tests passed** (three environment
warnings), **86 Node tests passed**, and the actual packing-probe test passed.
The unchanged measurement implementation observed 135 jobs / 5,832 weight / 10 packs
for index, 134 / 5,707 / 10 for free-content, and 128 / 5,581 / 10 for plan-book.
Only the first two weight ceilings increased by the measured ten-unit excess;
job counts, selectors, suites, the plan-book ceiling and ten-pack bound remain.

Real Chrome loaded the exact generated `site/news.html` bytes with controlled
loopback API fixtures, rather than a separately rendered template. Desktop 1440x900
and mobile 390x844 had no horizontal overflow or page errors, unique workspace
roots, working retained-report search including the archive-only example, and
forward/reverse mobile Tab wrapping. The temporary server was stopped. Public
edition rows coexist intentionally with live fixture rows; this is not a production
news or authentication receipt.

See `docs/evidence/news-cockpit-20261020-recovery/integration-main-902c.json` for
exact source hashes, test evidence, packing measurements and browser observations.
Original earlier evidence retains its original source scope. The parent mission
remains incomplete: this composed head still needs hosted checks, independent
review of repaired semantics, the protected release process, actual installed
reader/collector identity, signed-in desk/history and rights/freshness proof.

## Pro recovery: canonical assets and transport margin — 20 October 2026

The original three dirty Labor files were preserved in separate commit
`f3f079c203eec49e65c40342990d6cb734704082`, with their hashes and the Shared Shell
comparison recorded. Main `8128e4085d8aa346c969de186f05694afbbe6274` already contains
an accepted equivalent repair; the final Labor files are exactly that main version.
No original bytes were lost, no broad stash/reset occurred, and no unrelated Shell
navigation was imported. The News branch stays on its original operation and PR.

Actual conflicts were resolved in the API restart trigger, generated News page,
Labor page and packing tests. All 341 main CI jobs and the seven explicit News
history registrations remain. Canonical measurements require only the existing
News ten-unit weight addition: index 135 jobs / 5,832 / 10 packs; free-content
135 / 5,805 / 10; plan-book 128 / 5,581 / 10. Main's job limits and all selectors,
suites, plan-book weight and pack ceiling are preserved.

Both P1 findings from the independent 8d76 review are addressed. The canonical
externalizer and asset optimizer processed News and Plans; their actual linked
CSS/JS files are present, version-stamped and follow the owner's defer rules.
No hand-authored-page exemption was introduced. The old inline-only CSS guard
failed on real externalization before repair. Its replacement verifies the exact
canonical CSS once inline or in stylesheets actually linked by the page, with
HTML parsing, same-site path containment, query handling and strict duplicate,
stale, missing, unlinked, pseudo-attribute/comment and unsafe-reference cases.
The three JavaScript source checks are unchanged. The paid leaf repair proposal
was accepted as an implementation input, not as independent approval of this head.

Aggregate heartbeat timing now matches the accepted company-stream margin in
Macro #9893: five seconds, preserving one-second reads and 60-second renewal.
The old default failed the new real-generator regression with only four heartbeats.
A real loopback HTTP stream subsequently delivered twelve heartbeat frames with
maximum observed gap 5.014 seconds and explicit reconnect at 60.109 seconds.
Those measurements use a fixture identity and do not establish production latency,
capacity, entitlement, authentication or CDN behavior.

Verification on this composition: **582 Python tests**, **87 Node tests**, clean
inline JavaScript parsing, and canonical contract-delta **0 introduced / 0 inherited**.
The local audit initially encountered omitted sparse code and a pre-existing ignored
AAPL render cache absent from its base checkout. Code was materialized normally;
that one cache was temporarily held for a source-equivalent audit and restored with
its exact original SHA-256. No checker was weakened and no fictitious AAPL source
trigger was retained. All original rights/access boundaries remain unchanged.

The generated News page passed eight real Chrome states (desktop/mobile touch,
dark/light, English/Chinese); Plans passed four viewport/language states with its
source notices and loaded, stamped assets. History search and mobile forward/reverse
Tab wrapping were exercised. The preview used the ordinary synthetic sign-in event
and fixture backend identity; this is not a real account login. Temporary servers
stopped, and both selected screenshots were inspected. Evidence, exact source
hashes and executable probes are in `docs/evidence/news-cockpit-20261020-recovery/`
(`integration-main-8128.json`, `browser-assets-8128.json`, `heartbeat-wire-8128.json`).

Release is still held for fresh exact-head hosted CI, an accepted independent
review of this repaired candidate, protected merge and actual deployed News
verification. The independent direct SSH-origin inspection refusal is not bypassed.
Shared Company News and its normal deploy remain separate owners; the rendered
News consumer, live source-health clocks and signed-in retained-history behavior
must be verified after the normal release path, not inferred from these fixtures.


## 2026-10-21 current-main integration

The original News source `3a663ae70ecbd8a4130de9c95dbb6d940d181e04` was
composed with Macro main `2ebe9b7d52665ce4b37dbdb5845f4ce5cea879b1` on the
original managed branch. The measured conflicts were `tests/test_ci_pack.py`
and a routine old-template render of `site/news.html`.

The merged manifest preserves the exact union of 344 jobs, including all seven
`engine/marketing/intelligence_history.py` registrations. Canonical packing
measurements are 5,835 / 5,808 / 5,584 estimator units for index / build-free /
plan-book. Every probe remains at ten packs. Only the first two weight ceilings
are updated to their measured composition; selectors, job ceilings and the
plan-book ceiling remain unchanged. These are planning weights, not runtime.

Main did not change the five canonical News template/controller/style sources.
The generated News conflict therefore retains the previously qualified cockpit
artifact (SHA-256 `0718c4c61139cd5d7a6882f06da0322b73e350be0308cfe4e69efeaed7235e17`)
rather than adopting the old page's render. This is not a fresh source/provider
snapshot or production proof; the normal canonical render and installed API/press
worker verification remain release obligations. Prior browser evidence is retained
for its unchanged source scope only. New-head CI and applicable independent review
are required; the original failed reviewer packet remains immutable.


### Current-main integration validation

The affected packing, contract-delta, News page-render and News JavaScript
modules completed with 363 passing tests and three failures. Two failures
required the committed P0B receipt tree omitted by this sparse checkout; after
the existing sparse-checkout helper materialized mockups, both exact tests
passed. No assertions or source evidence were weakened.

The remaining closure audit finds the pre-existing ignored
`site/stockdata/AAPL.json` cache. That file is absent from both the prior News
commit and the imported main commit, and its presence is the same filesystem
sensitivity already documented above for the original News qualification.
The existing ticker test names this optional data path, so the physical cache
widens the local scanner's inferred closure. It was preserved; no fictitious
AAPL trigger was added and no local cache was staged. A clean hosted exact-head
run remains required. The complete local run is not represented as green.

The combined native repair now continues as the single composed release on
Mastermind PR #1674, incorporating the implementation carried by #1665 and the
protected physical-root and canonical slot changes. The original #1661 head
merged separately. Neither that landing nor this News integration reconciles
original failed reviewer
`news-9612-exact-3a663-release-review-20261021`. Its retained packet continues to
refer to original News source `3a663ae70ecb` and must not be rewritten as this
new integration candidate. Independent applicable review and actual signed-in
production News acceptance remain outstanding.


### 2026-10-21 integration through c694 and publication-boundary census

The original workspace composed protected main
`c694272be0f9b8690c18835897603d57affbdada` with News head
`81df0f97de259457a6a93f90e726240a98d20b82`. The sole textual conflict
was generated `site/news.html`; its resolution preserves the already qualified
News artifact, SHA-256
`0718c4c61139cd5d7a6882f06da0322b73e350be0308cfe4e69efeaed7235e17`.
The five canonical News template/controller/style sources remain unchanged.
The 345 CI job IDs are the exact three-way union, with no job payload changed
on both sides and every one-sided payload preserved. All seven canonical
`engine/marketing/intelligence_history.py` registrations remain present.

A fresh canonical `check_contract_delta.run(c694)` diagnostic, using the
existing tracked-path inventory and canonical base-tree helper, measured:

| Probe | Composed jobs / weight / packs | Base jobs / weight / packs | Existing jobs / weight ceilings |
| --- | --- | --- | --- |
| `templates/index.html` | 135 / 5,835 / 10 | 135 / 5,825 / 10 | 136 / 5,835 |
| `scripts/build_free_content.py` | 135 / 5,808 / 10 | 135 / 5,798 / 10 | 135 / 5,808 |
| `engine/prophet/plan_book.py` | 128 / 5,584 / 10 | 128 / 5,574 / 10 | 130 / 5,600 |

The job sets are identical between the two canonical measurements. Their
ten-unit weight difference is exactly the existing News
`collector-registry` payload, 17 to 27: two additional command blocks and
four explicit test paths. These are deterministic estimator units, not
measured runtime. No packing ceiling, ten-pack limit, selector, job coverage,
or command timeout was changed.

A preceding direct measurement without the tracked-path inventory selected
141/142/135 jobs and had 11 unscoped jobs, compared with two in the canonical
measurement. Its extra selected IDs were `board-contradictions`,
`calculator-input-integrity`, `crypto-shelves`, `nav-gap`, `nav-mega`,
and `site20-s4-chart-brief-js`, plus `title-i18n` for the latter two probes.
That materialization-sensitive diagnostic is not represented as a canonical
packing regression.

The canonical differential completed in 835.471 seconds with return 1:
zero packing breaches, one introduced closure finding for
`unrun-picks-boards -> site/stockdata/AAPL.json`. The preserved physical
cache is a regular 140,579-byte file, SHA-256
`bc155d9112cc1504230efb103d8fe08a4f0601130eb7d023f6851c9cf94caf00`,
ignored by `.gitignore`'s `site/stockdata` rule and absent from the index,
News HEAD and protected c694 Git trees. The tracked-path oracle supplements
physical existence and does not exclude this cache. This matches the prior
disclosed local finding; it is not a green whole-gate result or proof of a
new committed News dependency. The file was not deleted, staged or rewritten.

This was explicitly an uncommitted-composition diagnostic: HEAD remained
81df, MERGE_HEAD c694, and the unchanged staged tree was
`2780a4f203c7b84bf52d90ad80bad11dbe92ea03`. The oracle still anchored
its inventory at HEAD. A fresh canonical measurement and required CI on the
frozen integrated head remain the qualification boundary.

The separate News render/artifact guard passed all 77 tests
(`tests/test_news_page_render.py`, 40.091 seconds command wall time).
Six pytest cleanup warnings concerned pre-existing temporary browser trees;
the test result was 77 passed, with no assertion or cleanup rule changed.

At the publication boundary, protected main advanced five commits to
`566bf7b89cb0ac0e5e8dc081c7bc1598c9b1a30f`: 19 paths, with only
`.github/ci/legacy-jobs.yml` overlapping News-owned paths. The registry
retains 345 jobs; only the protected `flow-surface` payload changes, adding
ThetaData paths and its test to an existing command. It remains exclusive,
matches none of these probes, and retains its fixed weight of 267. The
integration must preserve that exact payload alongside the News
`collector-registry` additions. This bounded source census does not replace
the frozen-head measurement, required independent News review, protected
release, or actual signed-in production acceptance.

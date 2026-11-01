# Shared news intelligence: canonical ownership and activation

Status at the implementation boundary: **BUILT_NOT_PROVEN**.
This document records the implementation contract and local evidence, not a production release receipt.

## Ownership and consumers

Macro's existing qbus news store owns observations, report revisions, ticker identity,
story grouping, correction state, and current projections. The existing
`macro-ticker-news.service` remains the only writer. Terminal's BFF, Macro's
News Intelligence company view, and the new stock/ticker dossier panel consume
the same authenticated `/api/ticker-news` contract. They do not ingest feeds.

The existing press Intelligence Desk remains its own derived editorial consumer.
A generated `intelligence.desk/v1` snapshot is not an upstream article feed:
it does not currently carry the per-source receipt, original receive clock and
report revision needed for admission. Do not import it as Benzinga or substitute
its generation time for article arrival.

The API process keeps read-only access and no provider credentials. Research,
briefs and editorial consumers can use `engine.qbus_news_context.news_evidence_bundle`
with an explicit audience and fresh derivative-processing grant. This is a
read adapter, not a second store, generator, job queue, cache or publisher.
No model call or automatic publication is introduced.

## Source identity and additional coverage

The incumbent primary feed remains Benzinga, delivered directly or through Alpaca.
A transport change is not an additional publisher.

The optional adapter reads Massive's general `/v2/reference/news` endpoint.
Each accepted report has source `massive:<publisher-domain>`, transport
`massive_news_v2`, vendor report ID and the original publication clock.
Each publisher requires its own qualified receipt with `provider: massive`.
There is no provider-wide wildcard or union of one source's display fields into
another source's grant.

The adapter admits only title, article URL, description, tickers and keywords.
It does not collect article bodies, images or provider AI insights. A repeated
payload has the same revision identity. Massive's general response supplies a
publication clock, not an authoritative update/removal clock: different payloads
at the same clock remain recorded conflicts rather than arbitrary last-arrival
corrections. There is no invented removal capability.

The runner polls once per minute by default with a 24-hour overlap. Polling
cadence does not establish upstream publication delay or real-time availability.
Its health reports the last completed refresh, errors and polled delivery. The
panel describes that observed refresh state without claiming an hourly upstream
schedule. Qualifying upstream recency requires source-clock observations for the
actual admitted feed.

Publisher admission occurs before report normalization, and again on the owner
thread before commit. Revocation during a pending request prevents its writes.
The HTTP client uses one bounded network worker, streamed response-size bounds,
an explicit pagination host/path allow-list and no redirects. Credentials stay
in an Authorization header. Incomplete page budgets persist an exact continuation
and never advance the completed coverage checkpoint past unread pages.

### Configuration after an actual source grant exists

Use the existing operator activation owner and [ticker-news runbook](ticker-news.md).
No new credentials or receipts were installed during implementation.

The writer's root-only `/etc/macro-ticker-news.env` can receive:

```text
MM_TICKER_NEWS_MASSIVE_ENABLED=1
MM_TICKER_NEWS_ADDITIONAL_RIGHTS='["/etc/<actual-approved-publisher-receipt>.json"]'
POLYGON_API_KEY=<existing qualified provider credential>
```

The file is a systemd EnvironmentFile, not a shell script. Use the operator's
existing credential-delivery procedure; never put the credential in Git or the
API environment. `--massive-token-env` selects a different existing token variable
when the invocation owner requires it.

Set the same path-only `MM_TICKER_NEWS_ADDITIONAL_RIGHTS` JSON list in
`/etc/macro-api.env` so the serving process can qualify those sources too.
The maximum is 64 explicit receipt paths. The API must not receive the provider key.
Keep receipt files root-owned and readable within the existing serving namespace.

A receipt uses `qbus.news_rights_receipt.v1`, an actual owner reference and current
effective/expiry times. It must establish internal ingestion, retention and
headline display. Link, teaser and derivative permissions remain explicit.
Do not copy example booleans or invent an approval from possession of an API key.
Duplicate declarations of the same source, including a revoked duplicate,
deny that source. Malformed or expired receipts cannot borrow another source's grant.

Run the existing network-dark activation check after the reviewed source is
deployed. With the optional flag set, preflight requires both a token and at least
one applicable Massive publisher receipt. Configure both reader and writer scopes
before restarting under the existing release owner. Confirm separate health,
current publisher counts, cursor progress and authenticated readback before
claiming additional coverage.

At the October 20 implementation observation, the running service had the approved
Alpaca/Benzinga receipt, no additional receipt paths, no optional Massive flag and
no Massive token in that service's environment. These are presence-only observations,
not a claim that the organization has no other agreement or credential.

### Editorial acceptance for ticker-feed coverage

Before counting a publisher activation as additional or improved ticker-feed
coverage, record editorial acceptance in the existing activation evidence
alongside the independent rights and delivery checks. The current
[ticker editorial policy and view contract](ticker-news-editorial-quality.md)
governs this assessment; a licensed, stored report is not itself served coverage.

- Record the exact publisher's disposition under `engine/qkernel.py`, separately
  from its transport and rights receipt. Excluded or unknown publishers cannot
  count as eligible ticker-feed coverage, even when their permitted observations
  are retained internally.
- Review a representative, rights-permitted sample across the intended tickers
  and an explicit observation window, including thinner-coverage tickers. Reuse
  the shared article screening in `engine/news_common.py` and the current view
  rules in `engine/qbus_news_editorial.py`. Record accepted and rejected formats,
  ticker relevance and observed freshness; state the sample's limits. A provider
  ticker tag or Company mentions match alone does not prove that the company is
  the primary subject.
- Verify the ordinary authenticated served feed and source controls in News &
  announcements, Company mentions and Broader coverage. Preserve actual publisher
  attribution and press-release labels. Excluded publishers must stay excluded
  in every view, and sparse results must not fall back to excluded sources. Use
  existing contract/fixture evidence for transitions absent from the observed
  live sample, explicitly retaining that live-proof limit.
- Report licensed/stored observations, editorially eligible served reports and
  story groups separately, with their audience, ticker/view, observation window
  and pagination scope. Explain why the observed content meets the intended
  editorial standard and record remaining coverage gaps; publisher counts and
  successful ingestion alone do not establish a quality improvement.

This acceptance concerns ticker-feed coverage claims and does not broaden source
permissions or replace the canonical policy, single writer, or release owner.
Historical activation receipts below retain their original scope and dates.

## Duplicate groups and quality

Clustering is conservative. The derived character-bigram index restricts posting
reads to the same security and immutable anchor-time window, then uses bounded
frequency-selected probes and fingerprint scoring before the existing pure matcher.
The default budgets are 1,024 examined posting rows and 128 fingerprint candidates.
The reproduced unrelated-burst miss is repaired, but saturated budgets can still
leave duplicates separate; `retrieval_truncated` records that limitation. Existing
source/item identity is resolved before fuzzy retrieval. Subject unions are retained
when a cluster gains a report tagged to another ticker.

Existing number, period, rating-direction, negation and actor guards remain.
HTML entities are decoded for matching and presentation without modifying raw
source revisions. Previously stored clusters are not silently rewritten.

A cluster has one current display representative selected from the audience's
permitted reports using the existing source-tier/quality policy. A newer syndication
does not automatically replace better reporting. Fields denied by a receipt are
masked before ranking. Snapshot, grouped detail and change events use the same
current representative. Benzinga over multiple transports counts as one publisher;
the separate source grants remain intact.

The UI's High signal view excludes narrowly identified routine Benzinga
whale-alert/peer-profile templates. All reporting preserves those reports.
The additional flag does not broaden ingestion drops. All underlying eligible
reports remain expandable and attributed. Conservative matching can leave
duplicates separate; it does not promise semantic perfection.

## Delivery and evidence semantics

Periodic primary REST acquisition now runs outside the WebSocket receive loop.
Only the incumbent runner thread validates admission, routes subjects, and writes.
REST coverage advances only when its captured cursor is still current; WebSocket
observations cannot claim REST coverage. A periodic REST failure does not tear
down a healthy stream. Startup recovery remains conservative.

SSE defaults to a 100 ms poll and performs SQLite reads off the event loop.
Equal database/security/cursor/effective-rights requests share a bounded in-flight
read (50 ms cache, 128 keys, eight concurrent reads). Backlogs drain without an
extra poll delay. Rights are checked after in-flight reads and before each
delivered row; any changed effective scope ends the stream and asks clients to
clear their old scope.

Change events carry the current authorized story projection; they are not a
historical reconstruction of every intermediate report. Journal pages are coalesced
by story in one read transaction. `sequence` consumes the delivery journal while
`projection_sequence` orders the current group. Snapshot `change_sequence` is the
global journal watermark from the same SQLite read transaction as its rows. A removal
is emitted when no report remains eligible for the requested ticker and audience.

Evidence bundles use the same current grouping and field projection. They include
exact report revision IDs, clocks, receipt references and a content digest, with
bounded excerpts, report counts and truncation flags. `site_full`,
`internal_research`, `blog_draft` and `marketing_draft` are separate audiences.
A site display grant does not authorize another audience. The returned
`publication_authorized` remains false; existing editorial/publication owners
still decide whether and where to publish.

The evidence digest is an exact audit identity. It is not a semantic regeneration
key, and must not be used to justify one model call for each arriving headline.

## Macro dossier presentation

The static stock page and dynamic ticker dossier include a full-width company-news
section. It loads authenticated live data, uses the same security mapping as
Terminal, and contains no licensed headlines in the static build.

The panel provides High signal / All reporting, source and freshness labels,
expandable original reports, earlier coverage, back to latest, and links to
Terminal and News Intelligence. New arrivals are held behind a small notice while
the reader is interacting with a story. Corrections and removals still apply.
Ticker/auth changes cancel older reads and clear old content. Provider text is
rendered as text, and external links are restricted to HTTP(S).
English and Chinese labels use the existing language/theme owners.

The existing Terminal UI carrier (#1081) and Macro cockpit carrier (#9612) remain
separate active work. This change does not claim that their held releases are
merged. The company-view client in the cockpit carrier already consumes the
same ticker-news API; no second feed is introduced here.

## Verification evidence

Local artifacts under
`artifacts/news-shared-integration-20261020-c3/` contain controlled synthetic
fixtures only, not licensed provider payloads or credentials.

- `ui/verification.json`: actual shipped JS/CSS/partial hashes, eight interaction
  checks, zero page errors; desktop dark, phone light, Chinese and restricted
  screenshots were inspected. Includes keyboard grouped-report access,
  ticker switching, access denial and provider-text escaping.
- `latency.json`: 32 subscribers, 24 reports, 768 observations in each arm.
  Both arms use the current projection/authorization code. Control is 1 s polling
  without shared reads; candidate is 100 ms polling with shared reads.

| Local receive-before-commit to SSE | Control | Candidate |
| --- | ---: | ---: |
| p50 | 1,254.91 ms | 94.60 ms |
| p95 | 1,501.70 ms | 156.91 ms |
| p99 | 1,567.46 ms | 177.34 ms |
| maximum | 1,625.60 ms | 193.75 ms |
| actual database reads | 64 | 26 |
| subscriber read requests | 64 | 376 |

This is a controlled local SQLite-to-SSE comparison, not production end-to-end
latency. It excludes provider delivery, WAN, Terminal BFF and browser paint.
The candidate's commit p95 was 61.34 ms versus the control's 16.56 ms; faster
fanout does not establish lower commit cost. Do not extrapolate an absolute SLA
or an extreme-speed claim from this short fixture.

Run the reproducible checks with:

```sh
python3 scripts/verify_ticker_news_ui.py --evidence-dir /tmp/shared-news-ui
python3 scripts/benchmark_ticker_news.py --output /tmp/shared-news-latency.json
python3 -m pytest tests/test_shared_news_intelligence.py tests/test_massive_news.py tests/test_qbus_news_intake.py tests/test_ticker_news_api.py -q
node --check templates/ticker_news.js
```

The backend regression set also covers source clocks, grouping guards, same-clock
conflicts, receipts, field isolation, revocation after cached reads, cursor coverage,
quiet-primary intake, blocked REST alongside WebSocket delivery, correction,
removal and evidence audience restrictions. Tuesday/Thursday RFC timestamps have
a regression test for the corrected ISO-prefix detection.

## Release and remaining proof

Merge, production source identity, generated dossier pages and authenticated
browser checks are separate gates. The local benchmark and fixture UI do not
satisfy the existing natural-market observation requirement or authorize a held
Terminal/cockpit release. Preserve those carriers' current ownership and review gates.

After a qualified release, verify:
1. deployed Macro SHA and active API/writer processes;
2. primary store/cursor continuity and absence of a second writer;
3. authenticated snapshot, grouped detail, SSE and stock dossier in the real path;
4. negative rights/health states against controlled fixtures, never by revoking a
   live license just to test the page;
5. per-source availability and actual admitted publisher counts if additional
   sources are explicitly activated;
6. real source-to-receipt, receive-to-API and browser-visible timing separately.

Rollback uses the existing Git-gated release and service owner. The added index is
additive; do not delete or rebuild the durable news store during rollback.
No held Tiingo/financial-news cache work is modified or recreated by this change.


## Continuation after session handoff — 20 October 2026

The Chairman confirmed that the sister session had stopped and authorized takeover
of this same operation and branch. Its final implementation commit
`af58eb070dc752d04978cf004f51fb6e9987e545` and main-merge checkpoint
`0a31325c07762ea683fda9ee73e126824d1e68fa` were recovered with a clean working tree.
No replacement source carrier was created.

The continuation fixes two reproduced correctness defects:

- Quality selects the representative only within materially compatible current
  reporting. If eligible current reports differ on the existing fact
  discriminators, the current journal order keeps an accepted update visible.
  Both current reports remain in the same stable group; recency does not establish
  truth or imply that one publisher corrected another.
- Live streams revalidate source/field and derivative-processing scope on every
  cycle and after a shared read, immediately before each frame. A changed scope
  emits `restricted` and closes, including a quiet stream with no new revision.
  Consumers must purge previously delivered rows, annotations and expanded reports.

Snapshot, detail and live projection now carry the same report counts and display
clocks. Upsert events include `source_count`, `item_count`, `published_at`,
`updated_at` and `received_at`, so a consumer can apply a validated live row
without a second snapshot request. Older or incomplete events still require
authoritative reconciliation. The journal sequence remains the stream cursor;
these events describe the current projection, not an intermediate-history replay.

The additive `reporting_state` distinguishes `reports_differ`,
`no_material_difference`, `comparison_limited` and `not_compared`. Comparisons
use only eligible current titles and stop at 32 distinct titles. Displaying this
derived state requires derivative permission for every compared source.
Internal comparison-source metadata is removed from HTTP payloads. Evidence bundles
include the comparison state alongside exact current report revisions and retain
their separate audience/publication restrictions.

A focused local run passed **83 tests** across shared-news integration, ticker-news
API, store, clustering and annotation, with `git diff --check` clean. This includes
an idle receipt expiry without file changes, derivative revocation with and without
another report, permission change while awaiting a shared read, material correction
visibility across all projections, restricted comparison isolation, and complete
live-row display fields. These are controlled tests, not production acceptance.

A read-only production check at approximately **07:20 UTC** found both the existing
API and sole news writer active, with a live health receipt and no unresolved gap.
The configured receipt covers Benzinga through Alpaca for `site_full`, including
teasers and derivative processing, through 11 October 2027. Additional publisher
receipts and the optional Massive flag were not configured in the news services.
This establishes current deployment configuration, not the organization's entire
commercial entitlement inventory. No receipt, credential or production
configuration was changed.

The indexed retrieval repair for the reproduced same-security burst miss and the
browser delivery repair have returned bounded patch artifacts under this root.
Both artifacts were recovered from the declared source carrier and their retained
bytes matched the worker-return SHA-256 values. The indexed-retrieval task's final
execution receipt is ineligible (`rc=1`); its plausible patch and test narrative do
not constitute an accepted worker outcome. No replay or provider retargeting is
authorized by that receipt. Source inspection and independent qualification remain
required before any candidate is accepted.

Final integration must preserve this continuation's projection and comparison
presentation, qualify the saturation case, cold/warm writer opening and the real
browser permission lifecycle, then follow the existing review, CI, merge and
release owners. The stream's consumed journal cursor must remain separate from
the projected group's ordering value. A live consumer must replace a complete
authorized display projection or reconcile through an authoritative snapshot;
it must not retain omitted grant-dependent fields from an older row.


### Qualification and consumer preparation — 20 October 2026, 08:38 UTC

The expanded local news and deployment qualification passed **1,010 tests**.
CI's discovered import-closure violations were repaired by adding 27 explicit
paths to the 12 existing exclusive job scopes and registering the three new
news suites in the existing ticker-news job. No check was waived or narrowed.
The local contract-delta check against `13e098071ab2799c41a170d21ad522f751dfb15a`
reported **zero introduced and zero inherited violations**. Deployment restart
coverage now includes the shared `news_common` dependency for both API and writer,
and the optional Massive adapter for the writer.

Macro's English and Chinese display exposes `reports_differ` and
`comparison_limited` without labeling a report verified or treating arrival order
as truth. Expanded reports retain their own publisher attribution and differing
figures. Missing comparison evidence has no agreement badge. The real Chromium
fixture harness passed **11 interaction checks**, with zero page errors and five
retained desktop, phone, language and access-state screenshots. The final refresh
wording change also passed all nine intake tests, JavaScript and deployment-shell
syntax checks, and paired template/site asset equality. These screenshots exercise
shipped component bytes with fictional reports; they do not establish the full
production stock page, actual source availability or end-to-end market latency.

Terminal PR [#1088](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1088)
at `683ad84501c5188c4fea4f6d16a87f891952ba7c` preserves the comparison enum and
optional complete-projection fields through its JSON proxy and mounted feed.
Old API payloads default to `not_compared`; missing projection fields stay absent.
Malformed present enums, unsafe integer cursors and inconsistent counts fail
closed. A read-only independent review at that exact head passed: 137 focused
tests, 140 adjacent news tests, five reviewer probes and full TypeScript checking.
The parent accepted that semantic review, with binding CI and normal release
still required. This is contract preparation: visible Terminal comparison labels
and direct event application remain separate integration work. It does not
release the held Terminal sidebar PR #1081 or Macro cockpit PR #9612.

The audience-qualified research/blog/marketing evidence adapter is prepared;
production callers and their explicit audience/source grants remain to be
qualified. Additional-publisher activation and actual publisher coverage remain
open. Existing source receipts, the canonical writer and publication authority
are unchanged by these local proofs.

### Retrieval and direct browser delivery qualification — 20 October 2026, 10:35 UTC

The continuation independently repaired the returned index source and qualified it
on the original integration branch. Posting keys include the immutable anchor's UTC
microsecond clock, so out-of-window history cannot consume the current-window raw
row budget. Retained-subject expansion preserves that clock. A reverse cluster index
bounds repair work; missing or outdated fingerprints rebuild with consistent document
frequencies in the writer transaction. Candidate and posting saturation stay explicit.
The original builder's ineligible execution receipt remains unaccepted.

The existing registered news job passed **757 tests** on the combined candidate,
including atomic snapshot/read concurrency and distinct delivery/projection cursors.
All **nine recovered reproduction cases** pass without modifying the tested source.
New retrieval files are registered through 13 existing exclusive CI scopes; no scope
ceiling, test or gate was waived. The final differential CI contract check and hosted
CI remain separate release gates.

The shipped browser applies complete authorized upsert/remove projections directly.
It replaces the whole row, uses the projection clock for order and the journal clock
for delivery, and reconciles incomplete or older contracts through a snapshot.
Every refresh aborts and fences the prior stream before accepting the snapshot and
reconnecting from its atomic watermark. Restriction, sign-out and ticker changes
purge prior content and pending callbacks. The 40-row cap uses the last retained
row as the exclusive pagination cursor, keeping the first dropped report reachable.

The real local SSE fixture passed **49 checks**, with zero scenario failures and zero
browser errors. The rendered desktop/phone/Chinese fixture passed **11 checks** with
zero browser errors. Recorded fictional-fixture delivery timings were 22.7 ms for
an upsert, 25.6 ms for a correction and 5.0 ms for a removal. These measure local
server-to-DOM behavior only; they are not provider-to-screen production latency.

Reproducible same-host fixtures compare the 4d5f baseline with the repaired source:
at 2,048 distinct same-security noise reports, ten duplicate full commits had median
11.56 ms before and 1.44 ms after. The whole initial ingestion rose from 4.49 s to
10.57 s; the largest 256-item commit in that fixture rose from 0.61 s to 1.43 s.
These are deliberately repetitive adversarial titles, with truthful saturation
counts, not a sampled production traffic distribution. The index trades additional
writer work and storage for bounded retrieval and recovery of the missed duplicate.

A 6,000-cluster fixture, sized against a read-only observation of 5,993 production
clusters, rebuilt the derived index on first writer open in 1.14 s; warm opens had
median 5.67 ms and maximum 6.83 ms. It preserved all canonical clusters and rebuilt
6,000 fingerprints, 139,202 postings and 154 frequency rows. Main database size was
45.0 MB, with a 16.8 MB WAL after rebuilding, versus a 22.0 MB baseline fixture.
This qualifies current-size local startup cost, not unlimited-history scaling.

Evidence and its exact source digests are in
`artifacts/news-shared-integration-20261020-c3/retrieval/`,
`stream-ui/` and `ui/`. The benchmark harness is
`scripts/benchmark_qbus_news_retrieval.py`; the live browser harness is
`scripts/verify_ticker_news_stream_ui.py`.

Terminal #1088 passed independent review and binding CI and merged through the
normal protected-branch API as `8b8b217fdf799713f8b4a906bc0d4564d8aa20a2`.
Its exact-target normal production build is underway after a CLEAN source preflight.
No completed Terminal deployment or Macro production rollout is claimed here.
Additional-publisher grants and actual research/editorial caller admission remain
open qualifications; the separately held sidebar and cockpit PRs keep their owners.

### Terminal release readback — 20 October 2026, 10:40 UTC

The normal exact-target owner completed successfully. Terminal's source checkout,
deployment marker, localhost HTTP and public application HTTP all identify
`8b8b217fdf799713f8b4a906bc0d4564d8aa20a2`; both readbacks returned 200 and the
service was active. `terminal-release.json` records this generation proof.
This establishes deployment of the qualified compatibility code, not activation
of additional upstream publishers or completion of the held sidebar UI.

The final local differential CI contract check also completed successfully against
`13e098071ab2799c41a170d21ad522f751dfb15a`: zero introduced and zero inherited
violations. The expanded manifest stays within all existing job/weight/pack ceilings.


### Review repairs checkpoint — 20 October 2026, 13:30 UTC

This is the same integration operation and source branch at published parent
`111753b278ae9fd2275a7c222f0a11db8999a97c`. Macro PR #9846 remains draft.
The Chairman reaffirmed project ownership after interrupted message streams.
The refreshed GitHub and handoff census preserves the active dashboard owner on
Macro #9612 (`8d76db52`) and sidebar owner on Terminal #1081 (`a10657ee`).
Terminal #1088's previously verified deployed generation remains accepted.

The independent backend and delivery reviews returned terminal successful execution
receipts, but identified source findings; those reports are not implementation
approval for the repaired candidate. The current continuation addresses:

- Publication-time grouping: known publication clocks must also fit the six-hour
  fuzzy window. The receipt-time retrieval bound stays intact. Anchor publication
  comes only from the exact first accepted journal/revision binding, through the
  existing item index with one-row lookup, never a mutable correction or an
  unbounded history scan. Unbound legacy publication stays unknown. Existing
  source/item identity and immutable anchors are preserved; old groups are not
  rewritten. New decisions identify `qbus_news_cluster.v3`.
- Polling clocks: the query's preflight coverage bound remains separate from each
  page's actual arrival clock.
- Comparison: fewer than two eligible visible reports says `not_compared`;
  identical titles from two reports may still be compared.
- Permitted keywords survive normalization and participate in content identity.
- Health no longer asserts an unmeasured hourly cadence. Valid configured publisher
  domains and `accepted_reports_since_start` are explicitly scoped diagnostics,
  not claims of distinct observed live publishers.
- SSE permission and initial universe file reads run through an eight-task bounded
  pool per event loop. Every cycle/frame still reads fresh scope; permissions are not cached.
  Cancelling a stream does not free capacity until its actual read finishes.
  The unused rights-generation helper was removed.
- Three browser checks now assert the observed condition explicitly after their
  existing throwing waits.

The publication regression baseline reproduced three failures; all **125** focused
Massive, clustering, store, retrieval and provenance tests now pass. A separate
event-loop regression failed on the original blocking read; the repaired delivery,
API and receipt suites pass **81** tests, including quiet expiry, mid-read
revocation, cancellation/backpressure and complete live projections.

The current latency artifact was rerun at **13:28 UTC**, after one excluded
one-event warmup resolved lazy imports. It records all **25** loaded repository
Python source digests and rejects source changes during measurement. The table above
now describes that run. It remains synthetic local delivery evidence.

Current main has a real conflict with this branch in
`.github/ci/legacy-jobs.yml`; a read-only merge calculation identified no other
conflicted path. The next integration preserves both owners' job coverage and
requalifies the differential contract. Hosted binding CI has not yet run for these
unpublished repairs; independent delta review, merge and Macro deployment remain
open. Source rights and provider availability are distinct from those release gates:
the standing operator-confirmed enterprise record covers the qualified metadata
use, and a prior bounded credential probe observed the three configured candidate
publishers. Runtime receipts and additional-source activation are not yet installed.

Next three steps:
1. Publish the repaired source after combined qualification and the actual CI
   manifest conflict repair; obtain binding hosted CI and independent delta review.
2. Follow the normal Macro release/render owner and verify deployed identity,
   authenticated snapshot/detail/stream/dossier behavior and the sole writer.
3. Install the narrowly scoped publisher receipts under the standing entitlement,
   activate the existing optional adapter, and prove admitted live publisher counts
   and separate publication/receipt/delivery clocks; then qualify downstream callers.

No human permission or login is currently blocking source work. The active release
gates are exact-source review, binding CI and normal production proof. Keep the
dashboard/sidebar carriers and existing sector holds with their owners.


### Combined qualification and publisher preparation — 20 October 2026, 13:40 UTC

The complete registered news job passed **770 tests across 45 suites**. The refreshed
real Chromium stream harness completed successfully with the same shipped JS/CSS
digests. The paired historical-baseline versus current-candidate retrieval artifacts are `retrieval/review-baseline.json`
and `retrieval/review-candidate.json`: at 2,048 noise reports, duplicate full-commit
median was **8.79 ms versus 1.34 ms**; distinct-report ingestion was **3.26 s versus
14.63 s**, and the largest candidate 256-item commit was **2.19 s**. The current
6,000-cluster fixture rebuilt the derived index in **1.13 s**, with warm opens
**4.15–4.51 ms**. These measurements retain the additional writer-work tradeoff;
older numeric checkpoints describe their own earlier source and host observations.

Three exact-publisher receipt projections are prepared under `activation/` for
`massive:zacks.com`, `massive:fool.com` and `massive:globenewswire.com`, each qualified
for `site_full`, `internal_research`, `blog_draft` and `marketing_draft`. They derive
only from the pinned operator-confirmed enterprise record, permit delivered title,
link, description, retention and derivative processing, and deny body/image use.
Their actual issuance clocks and SHA-256 values are retained. The thirty-day expiry
is an operational revalidation deadline, not a contractual term. They have not
been installed in production. No credential is stored in these artifacts, and
existing publication owners retain publication decisions.


### Published integration and CI repair — 20 October 2026

The interrupted managed push was reconciled, never replayed. It completed at
14:08 UTC with `APPLIED`, action reference
`24830c5448fbdd791a16e9ece6565b646978a03e4180735bd196bf41aadc6649`.
GitHub PR #9846 and the original branch now identify
`c73fa2c3d08e777221fe1ee73f3b87dd479f1fb8`, whose parents are repair
`9eb6198c06d4e15bb516b60b150dfccadd4caa5d` and integrated main
`d59b99b9afbe99ef528ce80db0ff66f0d9846abc`. Both conflicting manifest
path lists were preserved. No news feature bytes changed in that merge, and all
25 latency artifact source digests still match.

At that exact integrated head, the 45 registered news suites passed **770 tests**,
and the deployment suite passed **289 tests**. The differential CI contract against
`d59b99b9` passed with **zero introduced and zero inherited violations**.
Logs are retained under `/tmp/news-integration-recovery-20261020/` as
`c73fa2-news-45.log`, `c73fa2-news-deploy.log`, and `c73fa2-contract.log`.

Hosted fences run `39436558379` passed. Binding CI run `39436558201` found one
concrete import-entry defect in `scripts/benchmark_qbus_news_retrieval.py`:
the existing `test_unpinned_entry_scripts_only_shrink` guard rejected its missing
repository-root pin. The repair pins the checkout before repository imports,
then preserves explicit `--tree` precedence. A bounded independent review found
that an incomplete comparison tree could otherwise fall back to this checkout;
the harness now verifies actual imported store/contract/cluster/retrieval module
origins before measurement and refuses a mismatch. An empty-tree subprocess
failed before creating an artifact. The unchanged **11-test import guard** and
both valid 128-report candidate/baseline smoke runs pass. The independent source
review accepted this bounded harness repair; it did not claim to run those tests
or re-review the product implementation. No CI guard, baseline or ceiling was
weakened. The larger performance artifacts retain their original fixture/source
scope, rather than relabeling these smoke timings as new performance evidence.

Fresh Fabric backend and delivery reviews were commissioned for `c73fa2c` as
`news-shared-integration-20261020-c3-backend-review-c73fa2-r1` and
`news-shared-integration-20261020-c3-delivery-review-c73fa2-r1`, controllers
49013 and 50618. Their last observation was controller polling with worker state
unverified; neither is approval. The old b644 review reports were accepted only
as useful diagnostic returns with the finding dispositions recorded. Their hashes
are `410250828c102a28b6a0016dfc50672a488d47b4ba68f73b8b0f2e15faa8cddc`
and `1cd69b88001797f4cfb9d880a73698ad41b769ecc8cdb781f6fb5a29a294a8c5`.
The original indexed builder remains ineligible, with no retry or retargeting.

The 14:39 UTC production readback found Macro source
`3b49d6a5c8a6330652a926a8e5061e0dbb3d0387`, the existing API and sole news
writer active, 6,507 active Benzinga states and 6,504 canonical groups. Health was
live with no catch-up failure or unresolved gap. These observations describe the
incumbent release, not this candidate. The normal release owner is the existing
`/usr/local/bin/macro-update` invoked by the three-minute root cron and serialized
through `/var/lock/macro-update.lock`; there is no macro-update systemd service.
The writer uses `QBUS_NEWS_PROVIDER` and the existing Alpaca credential pair.
The qualified additional-provider credential exists in `/etc/macro-live.env`;
only its presence was reported. Additional-source flags, path lists and receipts
remain uninstalled. Existing live generated files and other owners' local files
were observed and preserved.

Current gate and next three actions:
1. Publish the entry-point and component-token CI repairs on the same branch,
   bind hosted checks to its exact head, and reconcile the pending product reviews
   plus bounded repair reviews without treating controller polling as approval.
2. After review and CI clearance, merge normally and follow the incumbent Macro
   update/render owner; verify deployed source, API/writer restart, authenticated
   snapshot/detail/SSE and generated dossier behavior.
3. Install the three prepared metadata-only publisher receipts, perform the
   network-dark activation check, activate the existing optional adapter, and
   prove actual admitted publisher counts and clocks; integrate qualified private
   research/editorial callers on a separate follow-up carrier.

No additional human permission is needed for the current source repairs. Release
and live publisher activation remain gated by the exact-source reviews and CI.
Sibling Macro #9612, Terminal #1081 and the existing sector holds keep their owners.


### Component token qualification — 20 October 2026, 14:59 UTC

The concluded `c73fa2c` CI run also identified a design-guard failure in the new
news component stylesheet. Both template/site copies now use the existing theme
color variables and sanctioned radius-token fallback values. Warning text uses
the theme's contrast-adjusted warning ink. The live-health dot uses the freshness
color rather than the language-dependent market-direction palette. No shared theme,
JavaScript, API, grouping or writer source was changed for this repair.

The unchanged forward-only design guard passes with **zero blocking findings**.
The refreshed browser evidence passes **11 rendered interaction checks** and
**49 real SSE checks**, with zero scenario failures or page errors. Current paired
CSS digest is `0183d5f23e0c92507f420b904188114d07e7347842df6adba494957a5d6b5d59`;
JS remains `fe8322cda6e282e08633bee34185200a26905a01fd068aec8b80b6001359fa56`.

An additional Chromium proof loads the actual shared theme and this component
stylesheet with static fictional markup. All four dark/light and English/Chinese
states resolve a visible six-pixel live dot, the twelve-pixel card and eight-pixel
control radius defaults, and warning ink. Health color remains identical across
language changes. `ui/theme-tokens.json` binds both CSS hashes and the actual
computed values. External assets were blocked; this is bounded theme/component
proof, not authenticated production or live-source proof. The larger browser
fixtures retain their clearly labeled fictional-data scope.


### Review return and canonical visual evidence — 20 October 2026, 15:57 UTC

Both independent Fabric reviews completed for published `c73fa2c` and found no
blocking source defect. Each independently reproduced all 770 registered news
tests. The backend review additionally reproduced the 125/81 focused counts and
89 adversarial assertions; the delivery review exercised cancellation, bounded
admission, per-frame revocation and quiet expiry. Exact unmodified reports are
retained under `reviews/backend-c73fa2.txt` and `reviews/delivery-c73fa2.txt`, with
SHA-256 `88dfa3e92d91b0a6fa842f53ba2baf3ede0fae790b9f0b51fd700a27472b8674`
and `c04643968b1252dce0c1f9a7df9dabe6b5dc3b19fc7348719f0671cdb162e7e4`.
These source verdicts describe c73fa2 product bytes; later CSS and benchmark-harness
repairs require their own bounded review. No review is production proof.

Hosted run 39436558201 concluded with only the two known failures: import-entry
hygiene and component design governance. Both repairs now pass their unchanged
local guards. The visual-evidence guard also passes after restoring tracked
mockups through the sparse-worktree owner and producing a canonical receipt.
The unchanged real-browser capturer generated 32 successful states: all eight
required rest cells plus actual link hover, button hover and button focus in each.
The committed fixture is anonymous and fictional, frozen from the actual consumer
DOM in both languages, and uses actual shared theme/component CSS. Its source
hashes, 32 PNGs, manifest, scope and reproducible fixture builder are under
`mockups/evidence/news-shared-integration-20261020-c3/`. This component matrix does
not establish authenticated production, provider delivery or a full stock page.
Parent inspected desktop dark and Chinese mobile light screenshots. Existing
11 UI / 49 SSE checks and the four-state actual-theme token probe remain valid.

All 25 Python hashes in the latency artifact still match candidate product source.
The retrieval wording now explicitly distinguishes historical baseline from current
candidate; the pair does not isolate the v3 publication guard from retrieval cost.
Older indexed/recovery artifacts retain their original earlier-source scope.

The private consumer trace verified the existing Press writer boundary, but its
ordinary staging directory feeds `run_emit`. A separate follow-up carrier will
reuse that writer with fresh blog-draft rights, canonical security binding, private
staging and an explicit durable emit refusal. No ordinary Press staging or public
briefing has been enriched, and no provider activation or production write occurred.

Next: publish this qualified CI repair; bind hosted CI and bounded repair review
to the resulting head; then normal merge/update/render and three-publisher live
activation. Sibling dashboard/sidebar branches and sector holds remain untouched.


### Release, publisher activation and private consumer — 20 October 2026, 17:45 UTC

This dated checkpoint supersedes the earlier release and activation status above.
The historical observations, bounded evidence scopes and ownership rules remain.

Macro PR [#9846](https://github.com/mastermindx-market-intelligence/macro/pull/9846)
merged at 17:06 UTC as
`1298ed4281362329c682a1f7c038b932e4ccbb64`. Its binding
[CI run 39453623427](https://github.com/mastermindx-market-intelligence/macro/actions/runs/39453623427)
completed successfully for `b82af8dae3b05e7eaea198cfe49d61fb9b8ce595`.
The incumbent normal updater deployed the integration. The retained activation
readback includes the 31-pin deployment check; it does not substitute for the
separate generated-page and continuous browser-delivery proof.

The three qualified publishers are now activated through the existing optional
adapter and sole news writer. At 17:26 UTC the live readback counted 420 accepted
additional-publisher reports: Zacks 201, The Motley Fool 123 and GlobeNewswire 96.
These are observations at that time, not a forecast of coverage or a count of
independent underlying events. The installed grants retain their metadata-only
field scope, explicit audience/derivative permissions and body/image denial.
The retained release and activation receipts are under
`artifacts/news-qbus-private-draft-20261020-c3/`:
`primary-integration-landed.json`, `publisher-activation-live.json`,
`activation-operation-review.json` and `activation-parser-repair.json`.

Generated-page qualification remains pending. The render for the merge,
[39463170560](https://github.com/mastermindx-market-intelligence/macro/actions/runs/39463170560),
was cancelled by queue replacement. Its covering successor
[39466358269](https://github.com/mastermindx-market-intelligence/macro/actions/runs/39466358269)
is pending for `67638926282eb17c6c5a5ab631fce06527004914`, which contains the
integration. The parent observed fresh live UI content at 17:30 UTC, followed by
the reappearance of a live UI banner at 17:43 UTC. That behavior is under diagnosis.
Continuous live SSE/browser acceptance is not complete; neither the source pins
nor the publisher counts close that question.

The separate private Press candidate is
`e6f78cfc7362538a66b4ff4f0e4d35b783acf127`. It reuses the existing writer with
fresh `blog_draft` admission at the actual request boundary, canonical ticker
identity, dedicated private staging, durable qbus provenance and an explicit
generic-emit refusal. The focused four-suite qualification passed 252 tests with
one existing skip. At 17:43:16 UTC the complete 47-suite news/Press run passed
981 tests with one existing skip and 20 warnings. The retained
`managed-pytest.json` and `independent-private-consumer-review.md` bind the
focused qualification and independent source review. Hosted publication/CI,
private runtime qualification and public release authority remain distinct.

A real private-draft generation is still unproven: the observed original ordinary
Press slot has no ticker. Do not add a guessed ticker, relabel a historical slot
as current, borrow a held ingress or fabricate a candidate to clear this gate.
An eligible original slot must have a current UTC `as_of` and one unambiguous
ticker supplied by its actual producer. The existing
`engine.press.desk_planner._plan_brief` already copies the Chronicle event's
tickers into `slot.story.tickers`; a bounded census of genuine existing inputs
can establish whether an eligible, non-held slot exists.

Next work:
1. Finish the private carrier's binding qualification and follow the covering
   render; resolve the observed live banner through the incumbent delivery path
   before recording continuous SSE/browser acceptance.
2. Locate a genuine eligible original Press slot, then qualify one private draft
   on the actual database, universe, current receipts and private destination.
   If none exists, retain the exact input gap without altering source identity.
3. Observe the activated publishers over a natural acquisition window, separating
   publication-to-receipt age, polling/coverage progress, API delivery and browser
   visibility. Retain aggregate counts and lag/gap evidence without treating
   overlap/backfill age or the configured polling cadence as upstream latency.

Macro dashboard #9612 and Terminal sidebar #1081 retain their separate owners and
release gates. The Terminal Shared Brief assessment, held sector work and held
Tiingo/financial-news cache work are not reassigned. No private draft, research
bundle or `internal_research` evidence is authorized for automatic publication
or export to `site/intelligence/briefing.json`.


### Private release and bounded heartbeat repair — 20 October 2026, 19:05 UTC

Private Press [#9888](https://github.com/mastermindx-market-intelligence/macro/pull/9888)
merged at 18:58:31 as `e98d4e53265d2fb6d893c3286ddd6ca55df736d2`.
Its exact head `f9270eadd1013a1c1cf69dc6bdf3f04e3c46c74e` had both
independent APPROVE rulings, all 12 hosted packs and ci-gate successful in
[39471764135](https://github.com/mastermindx-market-intelligence/macro/actions/runs/39471764135),
and a clean real merge-tree against then-current main. At 19:03:18 the normal
updater had installed a descendant of the merge and all four qualified source
hashes matched. The opt-in private CLI is present. No live draft was generated.

A fresh read-only ordinary planner census at 19:03 used the incumbent
configuration and current UTC date. It returned Brief 0 / Research Desk 1;
`press-research_desk-2026-10-20-ecbcd172a7b6` has 21 first-party facts and an
empty ticker list. A real private draft still needs a genuine current-day
ordinary slot with exactly one explicitly supplied qualified ticker, or its
complete provenance-preserving original staging record. Do not guess a ticker
or alter cadence, source identity or held ingress. All three installed grant
hashes and four audiences remain current; their operational revalidation
deadline is 19 November 2026 13:41:32 UTC, not an asserted contractual expiry.

The live banner investigation found repeated HTTP/1.1 stream cancellations
about 15.1–15.6 seconds after API HTTP 200 responses. The app is served through
Tencent EdgeOne, whose documented default HTTP/1 origin idle deadline is
15 seconds. The actual site rule was not inspected. The existing 15-second
heartbeat lacks margin; a narrow 5-second repair is prepared in operation
`news-stream-heartbeat-20261020-c3`. Its actual-generator regression fails on
old source and passes on the repair; 132 focused tests pass and independent
source review is APPROVE. Permission checks, shared reads, polling and all
data/error semantics are unchanged. This is a strong edge-idle diagnosis;
sustained authenticated browser proof still requires deployment.

The actual-principal read-only store sampler passed all 180 opens while those
cancellations occurred, with a maximum 4.465 ms. This is not user/SSE proof.
Terminal marker, compiled deploymentId and canonical source all identify
`bbc07037aae3e98597945e23448781a091d15281`, active since 17:56:50.
Evidence and bounded limitations are retained under
`artifacts/news-stream-heartbeat-20261020-c3/`.

Next three steps:
1. Publish the reviewed heartbeat source, bind hosted CI/review, merge and use
   the normal updater; then verify the real stream across repeated former
   15-second boundaries.
2. Accept the generated stock panel only after existing covering render
   39439974736 publishes and the actual page is checked. Keep observing the
   licensed publishers' natural acquisition progress and actual API/browser
   visibility without equating backfill age with delivery latency.
3. When a genuine eligible original company slot exists, qualify one private
   draft through current identity/rights admission and the dedicated private
   destination. The present blocker is the missing original single-ticker input.

The primary activation is already applied; do not replay it. Dashboard #9612,
Terminal sidebar #1081, sector holds, held Tiingo work and frozen W2C retain
their separate owners and release conditions. No news draft is authorized for
automatic public export.

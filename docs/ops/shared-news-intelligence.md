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
| p50 | 1,101.58 ms | 80.99 ms |
| p95 | 1,459.86 ms | 136.03 ms |
| p99 | 1,523.03 ms | 154.40 ms |
| maximum | 1,581.15 ms | 162.57 ms |
| actual database reads | 64 | 23 |
| subscriber read requests | 64 | 331 |

This is a controlled local SQLite-to-SSE comparison, not production end-to-end
latency. It excludes provider delivery, WAN, Terminal BFF and browser paint.
The candidate's commit p95 was 25.32 ms versus the control's 10.87 ms; faster
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

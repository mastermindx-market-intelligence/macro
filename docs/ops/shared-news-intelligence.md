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

Massive documents hourly upstream recency for this endpoint. The runner polls
once per minute with a 24-hour overlap; this does not make upstream data real-time.
Its health is presented separately as polled/hourly. The existing streaming lane
remains the low-latency source.

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

Clustering is conservative. Candidate lookup first restricts to the same security
and immutable anchor-time window, then applies the candidate cap. Unrelated bursts
can no longer evict relevant candidates before matching. Subject unions are retained
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

Change events invalidate current story projection; they are not a historical
reconstruction of every intermediate report. Journal pages are coalesced by story
in one read transaction. A removal is emitted when no report remains eligible
for the requested ticker and audience.

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
browser delivery repair remain in separate bounded Fabric runs under this root.
Their requests and local controller observations do not constitute accepted
worker returns. Final integration must preserve this continuation's projection
changes, qualify the saturation case and the real browser permission lifecycle,
then follow the existing review, CI, merge and release owners.

# Tiingo News → Mastermind News Intelligence: bounded source integration

**Status:** source candidate on feature branch, **BUILT_NOT_PROVEN / DARK BY DEFAULT**.
The enabled flag is absent by default. No production feed, public use or historical
backfill is established by this source change. Source rights, live supervision,
storage placement and deployment each require their incumbent owner.

## User/machine value

Use Tiingo's ticker-tagged news to supplement the existing
`engine/financial_news.py` → `scripts/build_news.py` →
`site/news/financial.json` + `site/news/by_ticker.json` delivery path.
The existing News Intelligence page and stock pages remain consumers of the
existing artifacts. No parallel database, watchlist, identity resolver,
publication system, or signal engine is introduced.

The first source slice makes one global bounded `/tiingo/news` crawl
(`sortBy=crawlDate`, up to 250 rows), never 500 ticker-specific pollers.
It preserves the provider source/ID, published and crawled clocks, our
received clock and explicit observation-time basis. Only ticker-tagged,
allowlisted publisher stories enter the existing display feed. The shared
`news_common` scorer, clickbait exclusions, qbus keep-FIRST history, ticker
validation and news section/ticker routing remain in control. Tiingo data
are **context only**, not a licensed alpha score or entry instruction.

### Rights / activation

The Chairman confirmed commercial business/public-display/redistribution permission
on 2026-10-12 and explicitly ruled the Tiingo News commercial-rights issue
**finalized on 2026-10-24**. The leadership decision is accepted: no license
renegotiation or second commercial approval is required for technical work.
The existing source-rights owner still maps the finalized agreement to an actual
private qbus.news_rights_receipt.v1 with truthful product, licensed publisher
domains, audience, field-level capabilities, and effective/expiry values.
A model/operator must not fabricate those typed values from a vendor token,
ChatGPT memory or a generic entitlement statement. The feature stays OFF
until the source-rights owner supplies its ordinary machine-readable receipt.

The provider branch reuses the incumbent
`engine/qbus_news_receipts.py` format. It requires a receipt from the
source-rights owner, not a developer-manufactured approval. For Tiingo
this consumer requires these explicit capabilities:

- `internal_ingestion=true`
- `historical_retention=true`
- `headline_display=true`
- `derivative_processing=true`

It enforces `source_link_display` and `teaser_display` independently,
both default-deny. Body or image use is **not implemented**. Rights
are re-read at each feed build and an invalid, expired, wrong source,
wrong audience or revoked receipt denies Tiingo ingestion.

Example **shape only** (the bracketed values do **not** establish permission):

```json
{
  "schema": "qbus.news_rights_receipt.v1",
  "status": "approved",
  "receipt_id": "<owner-approved-unique-id>",
  "owner_ref": "<verified-commercial-news-addendum>",
  "source": "tiingo",
  "product_id": "<exact-entitled-news-product>",
  "audiences": ["site_full"],
  "effective_at": "<ISO8601-UTC-contract-start>",
  "expires_at": "<ISO8601-UTC-contract-or-review-expiry>",
  "capabilities": {
    "internal_ingestion": true,
    "historical_retention": true,
    "headline_display": true,
    "source_link_display": false,
    "teaser_display": false,
    "body_display": false,
    "image_display": false,
    "derivative_processing": true
  }
}
```

The `true` booleans are illustrative *required technical shape*, **not a
finding that Tiingo licensed those uses**. The source-rights owner must
replace each value with the contract's verified truth; if unproven, leave
Tiingo disabled. Do **not** check receipts, tokens, or commercial PDFs into Git.

For an authorized isolated integration run, the existing runtime/build owner
sets all three secrets independently through its approved mechanism:

```text
TIINGO_NEWS_ENABLED=1
TIINGO_API_KEY=<read-only Tiingo API token, secret>
TIINGO_NEWS_RIGHTS_FILE=<absolute path to validated private receipt>
```

No one should take these steps based solely on the sample API result.
Do not reuse the Benzinga root-only key file or expand its product scope.
The explicit Tiingo source switch preserves the incumbent Benzinga and
qualified Massive publisher receipt rules and their independent rights. If not all gates pass, existing Polygon, Finnhub,
RSS, Quiver and GDELT feeds continue to operate normally.

### Quality probe: 2026-10-09

One authorized fresh-crawl API sample of **100 consecutive newest rows**,
not an independent random sample or service-level measurement:

| Measure | Observed |
|---|---:|
| Token/API | HTTP 200 |
| Valid sample returned | 100 |
| Distinct article IDs | 100 |
| Distinct exact lowercase titles | 100 |
| Ticker-tagged | 52/100 |
| Nonempty descriptions | 92/100 |
| HTTPS links | 97/100 |
| Source domains | 12 |
| Publication → Tiingo crawl median | 10.7 min |
| Publication → Tiingo crawl p90 | 25.3 min |
| Top three domains' share | 80/100 |

The source concentration came from Yahoo Finance (43), AOL (21),
Kalkine Media (16). This is a **low-diversity snapshot**. It says
nothing definitive about individual publishers' editorial accuracy,
source attribution veracity, ticker-tag precision, coverage across a
full market day, recall vs Reuters/Benzinga, or the SLA over time.
No raw licensed article data or token was saved with this audit.

The first-source policy therefore uses **publisher allowlist and hard
blocklist, low-value-format suppression, pre-existing cross-provider
deduplication, and no model-derived sentiment signal**. The derivative
rights gate prevents unlicensed downstream processing. When an
authorized broader QA run exists, add stratified session/week/ticker/
publisher sampling, original-publisher URL checks, correction testing
and human-labeled entity precision. Compare different upstream
sources by *independent stories*, not raw article counts.

### PIT and storage honesty

- `published_at` = publisher timestamp **or Tiingo discovery fallback**, not
  independently proven publisher time and **not first access**. Both normalization
  and the qbus batch therefore use `CRAWL_BOUNDED`.
- `provider_crawled_at` = Tiingo's capture time; **not first access by Mastermind**.
- `received_at` / `observation_received_at` = the current response receipt.
  It does not prove first-ever observation. Existing v1 qbus keeps the first
  successfully persisted observation; subsequent observations do not rewrite it.
- `first_available_at=max(received_at,provider_crawled_at)` =
  conservative machine availability for this ingestion; not a claim
  that Tiingo had retrospective coverage at that time.
- `historical_backfill=true` when source crawl was >1 hour before
  Mastermind receipt, for attribution/analysis.
- The active v1 qbus emits one batch of **headline observations**,
  keyed keep-FIRST. v1 has no per-provider correction history, no
  separate Tiingo archival authority and does not preserve the complete
  Tiingo raw response; this source change **does not claim that it does**.
- Historical PIT backtests must use Mastermind's actual first receipt
  or an independently qualified historical availability record.
  Backfilled articles cannot be retrospectively counted as live
  observations. No unvalidated event-to-trade/sizing use is enabled.

### Before production activation (still outstanding)

1. Bind the accepted commercial permission to authentic owner-issued runtime
   receipt values for this exact product, fields, audience and effective/expiry
   window. Do not manufacture missing values or reopen the accepted business decision.
2. Qualify the exact host and authorized storage path (especially the
   requested external 4 TB data volume); configure key/receipt via the
   existing secret and source-rights owners. No token in repo/CI logs.
3. Verify full source integration tests, existing financial-news/feed,
   build contract and receipt tests. Current main was merged on 2026-10-22,
   preserving newer Massive receipt qualification and inventory behavior.
4. Exercise a private shadow build and confirm Tiingo health/reason
   fields, source diversity and 100% legacy-provider compatibility.
   Verify stable provider IDs and article updates across several runs.
5. Gate any live/scheduled fetch through the existing feed scheduler,
   inspect deployed location and data retention, and prove end-to-end
   page rendering, ticker drilldown, source attribution and revocation.
6. Only then consider provider pagination and full-history archiving in
   the incumbent qbus revision owner, with verified licensed time span,
   corrections and historical receipt identity. A single 250-article
   crawl is **not** historical ingestion completeness.

No new CI secrets, production flags, authorization paths or retention
services are created by the feature branch.


### Withdrawal and durability repair — 2026-10-22

The collector re-reads the enable flag, configured receipt path and complete
qualified grant after fetch, before persistence and before returning rows.
Equality includes nested field permissions, product, audience, owner, validity
window and derivative permission; a receipt ID alone is insufficient. Current
field capabilities govern displayed URLs and teasers.

A successful nonempty collector result requires the existing qbus append owner
to return a non-None result. None or an exception yields no display rows,
zero eligible articles and an explicit persistence-failed state. A grant change
during an already completed append withholds display; it does not rewrite or
undo the qbus owner's history.

Financial snapshots carry a versioned opaque digest of the complete qualified
grant. The live receipt loader remains the permission authority. A fresh cache
with a changed grant is a cache miss. Unbound Tiingo-era snapshots are rebuilt,
including snapshots whose only licensed text is in an old rejected-title log.
The whole snapshot is invalidated because capped/deduplicated display rows
cannot reconstruct pre-ranking raw and tagged counts.

The static builder qualifies both candidate and retained financial artifacts
before applying its 36-hour coverage preference, rechecks after enrichment and
before publication, and uses one selected snapshot for HTML, financial JSON,
compact ticker output and ledger/rejection inputs. If no safe financial
snapshot exists, it publishes empty sections and truthful zero counts.
Required withdrawal writes for financial.json, by_ticker.json and rejected.json
must succeed; failures fail the build. Compact and rejection outputs are cleared
before financial.json is replaced, preserving the unsafe snapshot as the retry
trigger after a partial failure. Missing financial snapshots with surviving
financial projections also require withdrawal; ordinary macro/RSS-only reject
logs do not. These are build/read boundaries, not a claim of instantaneous
revocation on already deployed static files.

Tiingo rejected titles do not enter the shared rejection log; quality refusals
remain aggregate counts. Ticker tags use the existing display universe's unique
case-folded/dot-hyphen matches. Unknown or ambiguous tags do not create or
select securities. This routing is not a dated DataOS identity grant.

### Premium evidence and Terminal scope — 2026-10-22

The source-filter repair in Macro PR #10027 merged as
`9f643105ec260da4c0b59864c98061061718f41b`. New archive requests use HTTP
`source` singular, while historical receipt/plan queries retain their original
bytes. This does not broaden source admission.

A bounded Bloomberg/CNBC query observed 77 valid unique metadata records
(17 Bloomberg, 60 CNBC). The newest-250 global feed had largely hidden that
cohort. In the common 24-hour comparison, vendor-tag candidates were present
for MSFT, AAPL, NVDA, MU and JPM; no selected candidate was observed for DE,
NEE or WST. These counts are neither complete coverage nor direct relevance.

A later latest-per-ticker/domain metadata selection contained six unique
articles covering seven ticker/domain slots. Two Bloomberg headlines were
plausible direct-company candidates; four CNBC items indicated other-company
news, a market preview or portfolio commentary. Public publisher pages were
inaccessible, so zero original reports were independently verified. This
small recency-biased selection is not a provider precision estimate.

The original #8697 draft targeted legacy Macro financial_news/qbus-v1. Its
published successor #10136 adds Tiingo's publisher-scoped SQLite contract and
rights-gated authenticated API. The single writer's actual Tiingo acquisition
is implemented separately in the held successor's next engineering slice below;
it is not yet accepted, released or activated. The draft stays held until
hosted CI, independent review and real signed-in user-path proof complete.


### Existing canonical SQLite writer — source-only implementation (2026-10-24)

The existing engine/qbus_news_intake.py now exposes a bounded
TiingoSupplementalIntake alongside the pre-existing Massive supplement.
Its only background future performs one Tiingo REST request (max 250 tagged
articles, min interval 60 seconds). The **existing** NewsIngestRunner thread
does rights revalidation, original-publisher editorial admission, dated ticker
routing, and the durable NewsStore.commit_observations transaction. No second
SQLite writer, daemon, release service, feed database, or scheduler was added.
The separate, previously refused engine/qbus_news_tiingo_intake.py file was
not created. The BOATS historical archive remains separately scoped; a single
bounded REST sample does **not** establish historical completeness.

The source is OFF by default. To qualify the **private preflight only**, the
installed runtime owner provides the existing primary Benzinga/Alpaca
prerequisites and sets TIINGO_NEWS_ENABLED=1, TIINGO_API_KEY and
TIINGO_NEWS_RIGHTS_FILE through its authorized host secret/receipt mechanism,
then runs the existing scripts/run_qbus_news.py --check-activation --tiingo-news
with its normal universe, primary rights and health inputs.
--tiingo-news is an explicit opt-in, not a new background worker. Missing
token, feature flag, private owner receipt, derivative grant, or at least one
exact licensed original-publisher domain yields
activation_tiingo_rights_unqualified *before network use or state writes*.
--run --tiingo-news is **not** approved by this source note alone.

Each completed HTTP response is untrusted until the source owner grants the
same current rights again; revocation before SQLite commit denies the batch.
Current rights are checked again on every authenticated API read, including
pagination/cluster/detail projection. Retained first-observation journal
history is never reinterpreted as a currently displayable entitlement.
The incumbent primary delta cursor remains untouched by a supplemental Tiingo
observation. A disabled, denied or broken Tiingo feed leaves the primary
Benzinga/Alpaca/Massive user paths operational.

### Protected production owner path (source-only readiness)

The canonical ticker-news setup script has a single optional Tiingo source
switch in the **existing** root-owned /etc/macro-ticker-news.env:

- MM_TICKER_NEWS_TIINGO_ENABLED=1
- TIINGO_NEWS_ENABLED=1
- TIINGO_API_KEY=(actual provider credential; never commit or print)
- TIINGO_NEWS_RIGHTS_FILE=/etc/macro-ticker-news-tiingo-rights.json

The setup script requires exactly one of each line when opted in and a regular
root-owned mode 0400/0600 Tiingo receipt at the fixed path. The existing
--check validates this with no provider fetch or SQLite writes; --install
remains disabled, and only the approved incumbent --arm action may start
the same macro-ticker-news.service. Without the optional switch, the primary
service behaves as before.

The Macro API never receives TIINGO_API_KEY. Its existing service unit
declares only the read-only receipt path and denies access to the writer
credentials. The serving operator separately enables
TIINGO_NEWS_ENABLED=1 in /etc/macro-api.env after accepting the actual
source-owner receipt. If unset or withdrawn, API Tiingo reads remain dark.
This note supplies release mechanics, not deployment or license-field proof.

Verification before acceptance: run the network-dark
tests/test_qbus_news_intake.py and tests/test_tiingo_sqlite_bridge.py,
the corresponding primary provider/health tests and full CI-pack/contract
gates on the published current head. Then obtain an independent reviewer,
deployed service/feature identity, and **real authenticated** Terminal
News/Company/Broader/detail/flow plus revocation readbacks. All source-only
unit tests can pass while production remains DARK/Built-not-Proven.

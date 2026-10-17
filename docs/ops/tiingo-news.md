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
received clock and conservative first availability. Only ticker-tagged,
allowlisted publisher stories enter the existing display feed. The shared
`news_common` scorer, clickbait exclusions, qbus keep-FIRST history, ticker
validation and news section/ticker routing remain in control. Tiingo data
are **context only**, not a licensed alpha score or entry instruction.

### Rights / activation

A working API token and plan description **do not**, alone, qualify news display.
The owning commercial document/order and current valid product schedule must
explicitly establish *Tiingo News*, licensed audience(s), retention duration,
historical downloads, publisher content/source-link/description display,
derivative processing (quality/entity tagging/cluster formation), and whether
redistribution sublicenses the original publisher's content. Provider terms
and underlying publisher rights can differ. An account-level "full redistribution"
description cannot by itself prove each of these news-specific rights.

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
The explicit source switch preserves the Benzinga default and its
independent rights. If not all gates pass, existing Polygon, Finnhub,
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

- `published_at` = publisher's statement; historical, **not first access**.
- `provider_crawled_at` = Tiingo's capture time; **not first access by Mastermind**.
- `received_at` = Mastermind's first local observation in this batch.
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

1. Obtain an owner-backed News-specific Tiingo redistribution/storage/
   derivative/audience grant with start/expiry, and establish whether
   individual publisher content requires separate agreements.
2. Qualify the exact host and authorized storage path (especially the
   requested external 4 TB data volume); configure key/receipt via the
   existing secret and source-rights owners. No token in repo/CI logs.
3. Verify full source integration tests, existing financial-news/feed,
   build contract and receipt tests. Reconcile concurrent
   `engine/financial_news.py` PR #7982; no blind overwrite.
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

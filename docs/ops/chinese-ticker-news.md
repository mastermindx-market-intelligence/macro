# Original Chinese news for CN/HK single-ticker Terminal

Updated: 2026-10-22. Operation: `terminal-cn-hk-news-20261021`.
Companion Terminal operation: `terminal-cn-hk-news-ui-20261021`.

## Outcome and release boundary

This change adds a disabled-by-default Finlight Chinese transport to the existing
ticker-news runner, store, API and Terminal rail. It preserves original Chinese
headlines and publisher attribution. It does not create another scheduler,
security master, entitlement owner, news database, quote universe or English
translation path.

**Source integration and fixture proof are not live feed acceptance.** The
production observation on 2026-10-22 found 503 US news securities, zero CN/HK
news securities, no Finlight credential in the ticker-news environment and no
Finlight publisher receipts. The active primary and Massive feeds were healthy.
No Chinese feed was activated and no commercial permission was fabricated.
A read-only build from the pinned canonical Git owner parquets qualified 1,669
news securities: the existing 503 plus 1,166 CN/HK listings. This is current
identity-selection proof, not observed news coverage. A mutable local primary
checkout failed the incumbent S&P alias check; the canonical source inputs were
used for acceptance without repairing or weakening that owner gate.

## Source decision

| Input | Intended role | Decision and qualification |
| --- | --- | --- |
| 财联社、第一财经 | Mainland market/company breaking news | First-choice editorial inputs. Finlight documents these Chinese sources and original `zh` results; require source-specific display permission and empirical coverage checks. |
| 证券时报/e公司、中国证券网、中证网 | Mainland listed-company reporting | Reviewed publisher identities in the existing editorial policy. Do not infer Finlight availability merely from that policy. |
| 东方财富财经/股票、新浪财经、同花顺新闻 | Breadth and company follow-through | Use editorial domains only. 东方财富股吧 and user posts are not admitted by this change. |
| 财新、华尔街见闻、新华财经 | Deeper financial reporting/context | Useful supplementary inputs; paywalls, source availability and permitted fields remain publisher-specific. |
| 經濟通 ETNet | Dedicated Hong Kong Chinese company/market coverage | Preferred commercial HK feed discussion: ETNet documents raw-content delivery for client products. No undocumented endpoint or mock live adapter is introduced. |
| 阿思達克、信報、香港經濟日報、智通財經 | Further HK editorial breadth | Reviewed display identities, not a claim that a licensed delivery contract has been connected. Validate actual inventory and entitlement before enabling each. |
| HKEX/CNInfo announcements | Official company disclosures | Complementary source class, not a replacement for independent journalism; retain the incumbent disclosure owners. |
| Tiingo | Existing licensed commercial vendor | Chairman-confirmed special business/display/redistribution permission remains valid. Existing #8697/#8698 technical holds and ownership remain intact. Original-Chinese HK delivery is not established by a generic A-share coverage claim. |
| GDELT / public RSS / open-source scrapers | Discovery/research only | Do not substitute indexing or a scraper for publisher rights, exact listing identity or reliable ticker-news delivery. ETNet's free RSS terms exclude the commercial use needed here. |

**Implementation choice:** Finlight has a documented `POST /v2/articles` API,
Chinese language selection, company entities and exchange/MIC filters. It can
deliver mainland and HK-listed company reports from any actually available,
qualified publisher. A publisher's location is not the listing's exchange.

**Commercial boundary:** Finlight's standard terms distinguish its metadata/API
service from the underlying publishers' redistribution rights. A Finlight API key
alone is insufficient for Terminal display. Each enabled publisher needs an
authentic owner-approved receipt referencing the applicable grant. ETNet's
commercial feed is a separate procurement/technical route; its free RSS is not
the commercial route.

## Implementation contract

- One existing qbus writer; Finlight acquisition uses its bounded supplemental
  network future and commits on the incumbent runner thread.
- Fixed HTTPS API origin, header credential, no redirect following, five-second
  request timeout, four-MiB response ceiling, 100 items/page and three pages/pump.
- Query uses `language=zh`, direct company entities and XSHG/XSHE/XBSE/XHKG
  exchange filters. Outbound domains come only from currently qualified,
  editorially admitted source receipts. Returned publisher domains are checked
  again before normalization; rights are checked again before commit and read.
- Retained fields are original title, source link, original publisher, source
  clocks, minimal direct ticker/MIC association and normal routing provenance.
  Provider summaries, article bodies, images, sentiment and alternate listings
  do not enter the normalized revision.
- Minimal `finlight_entity:` revision tags preserve raw ticker/MIC plus normalized
  alias. The existing routed observation retains canonical security IDs and the
  universe revision. This is the existing provenance path, not a second store.
- Identity comes from the incumbent security master and current
  `theme_graph_native` aliases. The news selection can include current CN/HK
  identities, without changing quote membership or allocating new security IDs.
- HK aliases retain `.HK` and support existing padded/unpadded spellings.
  Shanghai `.SH`/`.SS` converge through the incumbent identity grammar;
  Shenzhen and Beijing retain `.SZ`/`.BJ`. Bare numeric codes never become
  aliases. Unsupported legacy Beijing symbols remain unbound.
- No issuer-name guessing, ADR association or A/H fan-out. Both listings attach
  only when both direct company entities are explicitly present.
- English event/sentiment annotation is suppressed for Finlight Chinese rows.
  Chinese company-reference matching uses current names/symbols. Different
  Chinese headlines do not fuzzy-cluster; exact titles still require the
  incumbent compatible security and time conditions.
- Publication windows overlap by 24 hours. The page cap retains a continuation
  and does not advance a complete-through checkpoint. This is not an archive,
  correction/removal SLA or complete-history guarantee.
- Finlight has its own source key/cursor inside the existing SQLite database.
  Western primary/supplemental cursors remain independent.

## Health semantics

A fresh US wire does not establish Chinese coverage. CN/HK snapshots use their
eligible Chinese source health. Western ticker health does not inherit a Chinese
transport failure.

The existing supplemental health record includes a bounded `last_batch` diagnostic:
fetched, accepted into the current universe, rights-rejected, language-rejected,
invalid entities, unattributed, outside the universe and truncated.

| Observation | Result |
| --- | --- |
| Complete query genuinely returns no articles | Available acquisition; ticker can be quiet. |
| Correctly identified listing is outside the current news universe | Counted outside universe; no invented identity. |
| Direct entities missing from an entitled response | Transport/plan failure; cannot look healthy. |
| Empty/unusable company associations, invalid candidate mapping or rejected publisher/language | Degraded coverage; valid accepted rows remain available. |
| Page cap reached | Degraded partial coverage; continuation retained. |
| Permissions revoked/expired | Ingestion restricted and cached display withheld. |

These counts describe one acquisition batch, not unique story counts or a claim
of market-wide coverage.

## Activation prerequisites

The existing source-rights owner must supply authentic grant facts. Required
receipt fields remain `qbus.news_rights_receipt.v1`, source
`finlight:<normalized-publisher-domain>`, provider `finlight`, owner/receipt
reference, product, audience, effective/expiry or review boundary, and existing
field-level capabilities. Finlight also requires a nonempty
`publisher_rights_ref` and source-link permission. The reference is an evidence
pointer; a made-up string is not a grant.

Required capabilities are internal ingestion, historical retention, headline
display and source-link display for the actual audience. Do not grant
teaser/body/image/derivative rights by copying an example. No approved production
receipt template is committed here.

1. Put the entity-capable Finlight credential in the incumbent root-owned
   `/etc/macro-ticker-news.env` as `FINLIGHT_KEY`. No key belongs in the API
   reader, Terminal build environment, Git, logs or PR.
2. Add authenticated per-publisher receipt paths to the existing
   `MM_TICKER_NEWS_ADDITIONAL_RIGHTS` JSON array for **both writer and API
   reader**. Preserve existing western-source entries.
3. Add `MM_TICKER_NEWS_FINLIGHT_ENABLED=1` to the writer environment. The same
   flag includes CN/HK in the derived news universe during systemd's
   `ExecStartPre`. The CLI also exposes `--include-cn-hk` and
   `--finlight-news` for explicit checks.
4. Use the existing operator setup check on the released source:
   `sudo /opt/macro/app/deploy/ticker-news-setup.sh --check`.
   It parses the supported supplemental settings literally, never sources the
   credential file, qualifies both market selections and opens no provider
   connection. The runner's `--check-activation` itself performs no state writes;
   the setup check intentionally rebuilds the derived universe.
5. Read the actual provider source inventory and verify `includeEntities`
   entitlement and both mainland/HK samples before enabling public display.
   A configured publisher label is not measured availability.
6. Use the existing reviewed deployment/operator lifecycle to reconcile the
   already installed service and restart the writer/API after their settings
   change. `macro-update` continues to preserve inactive-service arming state.
   No new service or credential-delivery mechanism is needed.
7. Verify exact deployed source SHAs, service health, a real CN article and a real
   HK article through the authenticated Terminal path. Retain aggregate proof
   and minimal identity provenance, not licensed raw payloads.

Do not activate from fixture success. If the credential, grant or qualified
universe is absent, preflight exits 2 with sanitized readiness counts and the
Chinese lane stays off.

## Acceptance and rollback

The regression tests cover original Chinese text, header-only credentials,
publisher links/rights, exchange collisions and HK padding, direct A/H entities,
source clocks, bounded pagination, primary cursor independence, receipt expiry,
current-owner universe extension, degraded mapping health, Chinese clustering
and adapter → real SQLite → FastAPI composition.

The companion Terminal test renders synthetic Simplified and Traditional
Chinese fixtures at 1440×900, 820×1180 and 390×844, in EN/ZH interfaces.
Dark captures are the shipped palette; light captures are the existing approved
light **specimen**, not a claim of a live light-mode product. Neither the crops
nor synthetic source receipts establish live publisher coverage.

For source rollback, remove/disable the Finlight flag and the affected publisher
receipts under the existing operator lifecycle, then restart the already-owned
writer/API as required. Verify immediate read-side withholding and continued
western feed health. Preserve the existing store under applicable retention
rules. Do not disarm the entire western news service merely to disable Finlight.

## Primary research sources

Checked 2026-10-21/22:

- [Finlight Chinese financial news](https://finlight.me/chinese-financial-news-api):
  original Chinese and described publisher examples.
- [Finlight REST v2](https://docs.finlight.me/en/v2/rest-endpoints/):
  article request/response, paging, source inventory and entity fields.
- [Finlight advanced query grammar](https://docs.finlight.me/en/v2/advanced-query-building/):
  language, company and exchange/MIC filters.
- [Finlight terms](https://finlight.me/terms-of-use):
  API/metadata service versus original-publisher rights.
- [ETNet commercial content services](https://www.etnet.com.hk/www/tc/product/ci_fdata_info.php):
  raw content and client-product delivery.
- [ETNet RSS terms](https://www.etnet.com.hk/www/tc/news/rss_detail.php):
  limits of the free RSS route.
- [Tiingo News product](https://www.tiingo.com/products/news-api):
  advertised global/A-share coverage; not proof of original Chinese HK records.
- [GDELT DOC 2.0](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/):
  multilingual discovery/indexing.
- [Incumbent Tiingo carrier](https://github.com/mastermindx-market-intelligence/macro/pull/8697):
  confirmed commercial permission and preserved technical holds.

The recommendation is an engineering/source-quality judgment from these primary
materials and the observed repository/runtime boundaries. Actual publisher
availability, ticker association precision and delay require entitled live samples.

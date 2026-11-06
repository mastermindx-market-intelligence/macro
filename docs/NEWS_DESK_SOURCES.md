# News desk: source research and scope

Reviewed 18 October 2026. Source documentation establishes a possible integration and its conditions; it does not establish this product's commercial entitlement, complete coverage or measured latency.

## Configured added intake

All source definitions live in `config/press_sources.yml#research_rss`. The same press daemon collects them. No browser-side feed fetch or article scraper is introduced.

| Source | Added coverage | Configured interval | Display boundary |
| --- | --- | --- | --- |
| Federal Reserve press releases | US central-bank, banking and regulatory announcements | 120s | Attributed feed excerpt and original link |
| Federal Reserve speeches | Official monetary-policy statements | 180s | Attributed feed excerpt and original link |
| ECB institutional releases | Euro-area policy/releases, Governing Council decisions and accounts | 120s | Positive institutional path boundary; authored publications excluded; attribution and free-source notices |
| UK FCDO | Diplomacy, conflicts, sanctions and official international statements | 120s | Attributed GOV.UK excerpt; official perspective, not independent corroboration |
| UK Ministry of Defence | Official defence and conflict statements | 180s | Attributed GOV.UK excerpt and original link |
| HM Treasury | Fiscal and economic announcements | 180s | Attributed GOV.UK excerpt and original link |
| UK Department for Business and Trade | Trade, industry and international commercial policy | 180s | Attributed GOV.UK excerpt and original link |
| GDELT worldwide query | War, ceasefires, sanctions, diplomacy, humanitarian developments | 300s | Headline/link metadata; configured tier filter; no article body |
| GDELT economy query | Inflation, economy, exports, tariffs and energy | 300s | Headline/link metadata; configured tier filter; no article body |
| BBC World | Candidate wider reporting feed | Disabled | Business display permission not established |

The intervals are eligibility settings. They are not publisher SLAs; the existing roughly 75-second daemon turn and source/network backoff govern actual intake. The two GDELT queries share one due opportunity per turn and the incumbent global throttle. The UI filters a finite retained projection (600 aggregate items), not the whole upstream archive.

## Primary references and decisions

### Federal Reserve

The [official RSS directory](https://www.federalreserve.gov/feeds/feeds.htm) lists press, speech, testimony and statistical announcement feeds and describes RSS use by aggregators. This release selects the press and speeches channels. It preserves original source clocks and links, and treats official statements as attributed statements.

### European Central Bank

The [ECB copyright conditions](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html) require accurate attribution and free-availability notice before payment and on access. They distinguish authored publications that need prior authorization. Accordingly, the intake admits `/press/pr/`, `/press/govcdec/` and `/press/accounts/` paths on the configured ECB hosts; a similarly named query parameter or foreign-host path cannot satisfy the boundary. Authored speech/blog/interview/research channels are outside this added intake. The existing pricing-page source notice is extended to ECB news, and each story carries attribution and a source-terms link.

### GOV.UK

The [GOV.UK terms](https://www.gov.uk/help/terms-conditions) describe feed reuse and the Open Government Licence coverage, with exceptions for third-party content. The selected organization feeds use canonical GOV.UK news-and-communications URLs and carry Crown copyright/OGL attribution. A government statement about a conflict remains that government's statement. Presence in a feed is not a verified account of every claim.

### GDELT

[GDELT's published terms](https://www.gdeltproject.org/about.html) allow dataset use and redistribution with attribution. This is not permission to republish each linked publisher's article body. The added integration retains headline/link metadata, credits GDELT, and uses the existing source-tier filter. Provider indexing time remains distinct from publication time. Documentation's broad project coverage cannot be used as the coverage count of these two configured queries.

The isolated live receipt observed a bounded GDELT failure rather than successful discovery. Its health is degraded/unknown until a successful actual attempt establishes otherwise. No active global coverage or tick-latency claim follows from the integration's existence.

### BBC and other commercial publishers

BBC business-use permission was not established from the [business content guidance](https://www.bbc.co.uk/usingthebbc/terms/can-i-use-bbc-content-for-my-business/). The catalog entry stays disabled. No Reuters, Bloomberg, AP, Dow Jones or other paid wire subscription is purchased or activated by this change. Branded rows in the design specimen are illustrative; they do not constitute coverage proof or an entitlement grant.

World Bank material was researched but not enabled under an assumed commercial right. Existing ticker-news source rights and holds remain authoritative. In particular, #8697, #7982 and #8057 are unchanged.

## Tick delivery research

[Alpaca's official news-stream documentation](https://docs.alpaca.markets/us/docs/streaming-real-time-news) specifies a WebSocket feed, article IDs, creation/update clocks, source and symbol associations. This demonstrates an available push protocol; it does not establish this product's licensed redistribution rights or live credentials. The existing company-news owner is the integration point for an entitled push source, and the rebuilt company workspace can consume its changes without relaxing access.

To activate another wire, the source owner needs a concrete rights/field/retention contract, credential binding, correction/delete and replay behavior, and live measurements. Any subscription or redistribution agreement needs its own authorization; the rebuild does not silently accept one.

## Market Ontology comparison

The [public Market Ontology product description](https://marketontology.com/) connects observed developments and evidence to transmission, affected assets, scenarios, portfolio review and retained research. It is a useful functional benchmark. Public marketing is not a measured coverage or latency comparison.

| Benchmark dimension | This release | Remaining parity work |
| --- | --- | --- |
| Observe a changing development | Source clocks, full-snapshot updates, amendments/removals, source health | Publisher-level completeness and latency measurements |
| Inspect reporting | Brief, source evidence, timeline, original links, related reading | Validated cross-publisher event/entity resolution across the entire source set |
| Follow company exposure | Mentioned tickers, company news, grouping, owner-supplied activity; existing Event impact integration | Consistent direct/indirect exposure graph and scenario validation |
| Return to the investigation | Browser-local saved stories/views and Following | Account-synchronized research memory and alert delivery |
| Work calmly at useful density | Full-width desktop, mobile dialogs, two densities, stable ordering, keyboard controls | Long-session user evaluation and assistive-technology audit |

These differences are release boundaries, not grounds to label the current work full Market Ontology parity. The next investment should be measured source coverage and entitled push delivery, followed by validated cross-asset event resolution; additional decorative widgets would not resolve those gaps.

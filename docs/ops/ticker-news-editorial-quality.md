# Ticker news: editorial quality and provider audit

## Finding

The Terminal's shared ticker-news API admitted articles using display-rights receipts. It ranked representatives inside a story group, but did not apply the Macro newsroom's publisher and low-value filters to the population it served. The Terminal's All sources control only filtered the articles already received. It was not an editorial admission control.

The additional-provider activation was deliberate: the [shared integration release record](shared-news-intelligence.md#release-publisher-activation-and-private-consumer--20-october-2026-1745-utc) records Zacks, The Motley Fool and GlobeNewswire being enabled through Massive, with 201, 123 and 96 reports respectively at its 20 October 17:26 UTC check. The transport provider and the underlying publisher were conflated in the UI label, for example `Massive:fool.com`.

A read-only production audit on 21 October 2026 at approximately 02:59 UTC found:

| Publisher source | Active retained reports | Curated treatment |
| --- | ---: | --- |
| benzinga | 6,955 | Reporting, subject to article filters |
| massive:fool.com | 175 | Excluded |
| massive:zacks.com | 416 | Excluded |
| massive:globenewswire.com | 134 | Press releases, subject to article filters |

These are retained reports, not independent events or daily arrivals. The audit used `SELECT source,status,COUNT(*) FROM news_states GROUP BY source,status` over a `mode=ro`, query-only connection. The production source revision was `e5dd30c6344e4b62a0beba054ac4da97e00bab36`; the writer and API services were active. A subsequent ordinary authenticated Terminal read showed 13 Fool, 6 Zacks and 1 Benzinga article in Apple's first 20 rows. No content or credentials were exported as audit evidence.

The live Macro News Intelligence page was also inspected. It offers ranked stories, High impact/Confirmed controls, a topic-filtered full tape, and newsroom diagnostics. Its editorial feed visibly includes CNBC and Bloomberg. That derived newsroom feed has different provenance and acquisition paths from the ticker qbus. Its publisher list is not evidence that the ticker feed has a licensed, active Reuters/Bloomberg/FT integration.

Massive's [publisher explanation](https://massive.com/knowledge-base/article/where-does-massive-source-ticker-news-from) independently describes this endpoint as aggregation and explains that a ticker tag can mean an incidental mention. The transport subscription alone is not a source-quality policy.

## Serving policy

`engine/qkernel.py` remains the canonical publisher-policy owner. Fool and Zacks join the excluded set. The ticker reader uses normalized domain-boundary matching against the existing tier-one/tier-two publisher tables, with named Benzinga/The Fly wire exceptions and a separate press-release category. Bare source mnemonics cannot accidentally confer a tier on an unrelated hostname. Unknown and excluded publishers are not admitted. The display-rights receipt remains an independent requirement; this policy cannot grant or broaden rights.

`engine/news_common.py::ticker_editorial_reason` reuses the newsroom's recognized promotional, stock-pick, advertorial and routine template rules. It retains factual dividend and company-release headlines that are useful for a ticker. Press-release solicitation alerts are excluded. This is deterministic screening of recognized formats, not a claim that every accepted report is independently verified.

The curated view applies before grouping/page limits in `engine/qbus_news_store.py`. The same accepted population governs snapshots, grouped members, direct story retrieval, current-state change projections, and news-flow counts. A correction into a rejected headline removes the visible report and advances delivery progress; a later qualifying correction can restore it. Sparse coverage never falls back to excluded publishers. Raw licensed ingestion/history and the single writer are preserved for internal auditing.

The public API opens only the curated view and announces `editorial_policy: ticker_news.curated.v1`. Rows carry `content_kind: reporting | press_release`. Health is scoped to readable, eligible publishers; raw ingestion counts are not presented as curated counts. The underlying writer health receipt stays intact.

The Terminal preserves these additive fields. It shows actual publisher names, marks releases in rows and expanded reports, and labels its default filter All curated sources only after receiving this policy marker. Older API responses do not gain a curation claim. Existing review-state filters continue to operate on the admitted population.

## Coverage boundary and release

This repair does not activate any new publisher or alter a rights receipt. At the measured production state, the remaining sources are filtered Benzinga reporting and separately identified GlobeNewswire announcements. Reuters, Bloomberg and FT remain a coverage gap for this ticker feed. Admission-table membership, Macro RSS configuration and synthetic test examples must not be presented as active premium coverage.

A premium-source addition must bind the actual upstream endpoint, exact publisher identity, permitted fields/audience, ticker relevance, observed delivery/freshness and deduplication to the existing writer. Do not import an already-derived intelligence snapshot as if it were original publisher evidence, or issue a receipt merely because a credential or public URL exists.

Release through the ordinary Macro and Terminal source/CI/deployment lanes. The Macro reader change can deploy first: the old Terminal parser tolerates additive metadata and already benefits from the filtered API. The Terminal change then supplies the source and release labels. Check an ordinary authenticated ticker page, source choices, grouped detail, stream refresh, and returned flow counts after deployment. A merged commit, local build, or configured publisher alone is not live proof.

## Signed-in acceptance and article-class follow-up — 21 October 2026

Macro [#9942](https://github.com/mastermindx-market-intelligence/macro/pull/9942) and Terminal [#1094](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1094) completed their ordinary merge/deploy lanes. The backend merge was `526ce826f0898d8724e79acf3a884f9cec6f3096`; the Terminal merge was `d9ec4d2b86e9e9e0129d7fcd4c646f25f7670c49`, served by build `build-TfctsWXpff2fKS`. Their PRs retain CI and deployment receipts.

The ordinary signed-in News panel was checked after reload at approximately 09:42 UTC. AAPL's first 20 rows were Benzinga, with no Fool/Zacks or raw transport labels. MSFT offered All curated sources, Benzinga and GlobeNewswire; selecting GlobeNewswire showed three reports, each labelled Press release. Reload returned to the ordinary all-source view with 20 rows, including three releases. No review-state action was taken. The sample contained no expandable multi-report control, so it does not establish live grouped-detail or correction delivery proof.

That same live check exposed residual Benzinga article classes: numbered analyst forecasts/downgrades, the “with industry competitors” peer-comparison template, sector whale-alert roundups, and explicit Opinion/personal-finance URLs. Publisher admission alone did not remove these formats. The follow-up extends the shared headline patterns narrowly and classifies only the exact first URL path segments `opinion` and `personal-finance` on a valid Benzinga host. Factual single-company rating changes, earnings, regulatory actions and disclosed investments remain eligible.

URL-based classification must use the current reader's permitted URL. The common SQL predicate projects a denied URL to an empty string before classification. A hidden URL therefore cannot change visible membership, grouped counts, details or flow. A URL-permitted correction into an excluded section removes the report; a later qualifying correction restores it. Raw writer history remains intact. The existing `ticker_news.curated.v1` contract is retained; this is a recognition repair, with no new publisher, entitlement or client contract.

The follow-up is a candidate until its own concluded checks, ordinary backend rollout and fresh signed-in readback are recorded on its PR. Authentication has been resolved; article-class acceptance is the remaining release gate.

## Verification

Editorial regressions are co-located in `tests/test_shared_news_intelligence.py`, already enrolled in the existing ticker-news-qbus CI job alongside its source-diversity, rights and live-consistency tests. It covers the user's screenshot headlines, aliases and lookalike hosts, before-pagination rejection, mixed story members, corrections/removals/restoration, title permissions, real API reads, release classification and scoped health. Existing qbus/ticker/financial-news suites check the shared-policy integration.

Terminal contract and rendered-consumer tests cover additive compatibility, bilingual attribution and the absence of false curation claims. Its existing responsive ticker-news test exercises publisher filtering at 1440×900, 820×1180 and 390×844 in EN/ZH. Dark views use the shipped theme; light views are explicitly approved-palette specimens under the existing D-W1 ruling. This fixture proof is distinct from production/authentication/delivery evidence.

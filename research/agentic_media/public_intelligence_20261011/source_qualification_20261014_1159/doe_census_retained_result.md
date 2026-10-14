# DOE Intake / Provenance Census — Compact Result

Operation: `mmx-public-intelligence-delivery-20261011-local-ceo-001` — Read-only, 5 of 12 request budget used.

## (a) Documented RSS endpoint evidence

| # | Feed endpoint (exact) | Publisher page | Covers target articles? |
|---|---|---|---|
| 1 | `http://energy.gov/fe/techlines?view=rss` | energy.gov/hgeo/fossil-energy-rss-feeds | No (Office of Fossil Energy scope) |
| 2 | `http://energy.gov/fe/clean-coal-news?view=rss` | same | No |
| 3 | `http://energy.gov/fe/carbon-capture-storage-news?view=rss` | same | No |
| 4 | `http://energy.gov/fe/oil-natural-gas-news?view=rss` | same | No |
| 5 | `http://energy.gov/fe/petroleum-reserves-news?view=rss` | same | No |
| 6 | `http://energy.gov/fe/blog?view=rss` | same | No |

**Finding:** All 6 listed feeds are scoped to Office of Fossil Energy (`/fe/...`). No feed endpoint on the supplied RSS page covers the `/ceser` (Order 202-26-50) or `/articles` (Press Release) sections where the three target documents live. No general `energy.gov` master feed was found in scope. **No safe inspection path found that proves the target articles are exposed via any supplied feed.**

## (b) Publication vs effective/order dates

| Document | Publication date | Order/Effective date | Application date |
|---|---|---|---|
| Mid-Atlantic grid press release | 2026-10-12 | n/a (press release) | n/a |
| DOE Order 202-26-50 (PJM) | 2026-10-12 (issued) | 2026-10-13 through 2026-10-16 | 2026-10-11 (PJM) |
| Eight-state grid expansion press release | 2026-10-13 | n/a (press release) | n/a |

## (c) Explicitly named companies (agency/utility vs inferred ticker)

| Document | Agency | Grid op / utility | Inferred public ticker? |
|---|---|---|---|
| Mid-Atlantic press release | DOE; Secretary Chris Wright | PJM Interconnection, L.L.C. ("PJM") | None inferred (PJM is a private LLC; not publicly traded) |
| DOE Order 202-26-50 | DOE | PJM Interconnection, L.L.C. ("PJM"); "Transmission Owners and Electric Distribution Companies" referenced but not named | None inferred |
| Eight-state grid expansion | DOE; Office of Electricity (OE); Deputy Sec. James P. Danly; Asst. Sec. Katie Jereza | Tennessee Valley Authority (TVA); states: Tennessee, Alabama, North Carolina (3 of the cited 8 named) | None inferred (TVA is a federal corporate entity; not a publicly traded company) |

**Distinction kept:** No government-authored text on these pages asserts a public-stock association for PJM or TVA. "PJM" is a private grid operator per the order text. "TVA" is a federal utility. No third-party supplied documents/images with separate rights holders were credited on the target pages (only DOE-hosted headshots and DOE logo).

## (d) Official government-text reuse terms (energy.gov/web-policies)

- **Public domain:** "Government information at DOE websites is in the public domain." "Public domain information may be freely distributed and copied, but it is requested that in any subsequent use the Department of Energy be given appropriate acknowledgement."
- **Beyond fair use:** "requires the written permission of the copyright owners."
- **Third-party / private content exception (exact):** "When using DOE websites, you may encounter documents, illustrations, photographs or other information resources contributed or licensed by private individuals, companies or organizations that may be protected by U.S. and foreign copyright laws." "Permission to use these images should be obtained directly from those organizations."
- **Outbound link disclaimer:** "Once you access another site through a link that we provide, you are subject to the copyright and licensing restrictions of the new site."
- **RSS / feed reuse:** **No content** on the Web Policies page addresses RSS/feed reuse. UNKNOWN.
- **Effective date of Web Policies page:** not shown. UNKNOWN.
- **Reporting note (not a rights receipt):** These are the published terms as quoted. They are not a legal approval.

## Limitations / negative findings preserved

- 403/access-denial policy: not triggered; all 5 input URLs returned content.
- No supplied RSS feed proved to expose the three target articles.
- DOE Web Policies page does not state an RSS-specific reuse rule.
- The eight-state press release names only 3 of the 8 cited states on-page; the other 5 are UNKNOWN from the read.
- No PDF URLs were returned for the PJM order documents; only relative document paths.
- No "supplied by" / external photographer credits appeared on the three target pages; all images observed are DOE-hosted.

**No code, repo, production, provider, staging, publication, feed-poller, or ingestion actions taken. No delegation. No downloaded private content retained beyond cited excerpts.**

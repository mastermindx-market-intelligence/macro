# FIF P0 — Analyst journeys and view contract freeze

## 0. Freeze identity

Frozen at commit `5267c66846e7733bc1eb30edc1524daff51598ca` against the built Filing Forensics surface. Companion machine contract: `research/financial_intelligence_fabric/FIF_P0_VIEW_CONTRACT.json` (`schema` `fundamental_forensics.p0_view_contract/v1`). Pinning test: `tests/test_fundamental_forensics_p0_view_contract.py`. Surface files: `templates/fundamental_forensics.html.j2`, `templates/fundamental_forensics.js`, `templates/fundamental_forensics.css`, `app/forensics.py`. **No UI change in P0.** P2 may change the surface only by editing the JSON and its test in the same PR, bumping `/v1` when a key is removed or renamed. Journey names come from `~/lanes/fif_plan/MASTERPLAN.md:108-113`.

## 1. Journeys

| ID | Status | What the seat gets today | Gap | P2 question |
|---|---|---|---|---|
| **J1** Open a new filing and inspect its largest supported changes / 打开一份新财报并查看其中最大的受支持变化 | exists | Company picker loads the latest pair (`templates/fundamental_forensics.js:833`); overview leads with the first high/watch finding (`js:979`); radar lists findings ordered by `payload.ranked_findings` (`js:1100`); disclosures list wording changes (`js:1334`). Ranking is high-priority first, then latest `latest_filed` desc (`scripts/build_fundamental_forensics.py:731`). Findings are `display_only` with authority `review_priority_only` (`tests/test_fundamental_forensics_page.py:85`). | "Largest" is review-priority then recency, not magnitude. Supported changes are the built detector set (`detect_quarterly` `scripts/build_fundamental_forensics.py:270`) plus the nine `METRICS` keys (`js:54`). | Rank by magnitude, or keep review-priority then recency? |
| **J2** Open a displayed metric to its exact source occurrence or permitted document span and basis / 从展示的指标打开到精确来源出现位置或允许的文档区间及其依据 | partial | Disclosure `evidence_receipts` carry accession, `source_url`, `source_excerpt`, `display_excerpt`, `block_id`, `section_id` (`engine/fundamental_forensics/disclosure_projection.py:369`; rendered `js:2522`). Numeric findings render `finding.evidence` URLs (`js:2690`) produced as company-level EDGAR browse + companyfacts JSON (`scripts/build_fundamental_forensics.py:183`). Formula/threshold/limitations sit in the evidence drawer (`js:2711`). | Statements/compare paint plain `<td>` values (`js:1474`). Radar numeric URLs are issuer-level, not occurrence-anchored. Char-span is provenance on the projection (`disclosure_projection.py:379`); the page does not jump to it. | Should statements/compare cells open an occurrence-level span? |
| **J3** Rewind the query cutoff to a historical answer or absence / 将查询截止日回拨到历史答案或缺失 | partial | `POST /api/forensics/v1/financial/query` is registered (`app/forensics.py:841`) and admits `policy` with `source_snapshot_at` / `recorded_at` (`engine/fundamental_forensics/query_service.py:322`). Metric support is cutoff-visible governance (`query_service.py:519`). Attested-history snapshots are addressable (`app/forensics.py:627`, `:637`, `:673`). | The page reads only `/latest` (`js:2171`). State `as_of` is display-only (`js:916`). No as-of input exists in the template. The page does not call the financial POST APIs. | Where does the cutoff control live, and how does the page show a historical absence? |
| **J4** Compare a valid peer cohort, see excluded peers, recover the saved comparison / 对比有效同业组、查看被排除同业并恢复已保存的对比 | missing | The only shareable page state is `?symbol=` via `pushState` (`js:862`) and `popstate` (`js:3275`). | Zero `peer` / `cohort` / `localStorage` / `sessionStorage` identifiers in `templates/fundamental_forensics.js`. No cohort picker, exclusion reasons, or saved-comparison store. | Who owns peer-cohort membership, exclusion reasons, and saved-comparison persistence? |
| **J5** Export and refresh the same values, policies, and source refs via API and Excel / 通过 API 和 Excel 导出并刷新相同的数值、策略和来源引用 | partial | Page fetches `GET /api/forensics/state` (`js:9`, `app/forensics.py:128`) and `GET /api/forensics/health` (`js:10`, `app/forensics.py:147`) with `cache:'no-store'` (`js:765`). Attested-history GETs are composed from `ATTESTED_HISTORY_URL` (`js:11`, `js:2096`). Financial POST routes exist (`app/forensics.py:841`, `:888`, `:939`, `:990`). Gate copy says data is being refreshed (`js:643`). | No export/CSV/JSON/Excel control on the page. No explicit refresh button; reload is the refresh. Financial POSTs are unused by the page. | Where is the export entry point, and does it cover API, Excel, or both? |

## 2. Panels in DOM order

Site nav is an include (`templates/fundamental_forensics.html.j2:21`) whose Filing Forensics entry lives at `templates/_navlinks.html.j2:273`. The hero (`html.j2:25`) and tab bar (`html.j2:271`) have no `id=` of their own. Frozen panels below are the regions that do.

| DOM order | panel_id | dom_id | Data source | Journeys |
|---|---|---|---|---|
| 1 | run_meta | `ff-run-meta` (`html.j2:52`) | `GET /api/forensics/health` (`js:10`, `js:890`) plus `as_of` / `generated_at` / `source` (`js:915`) | J1, J3 |
| 2 | company_context | `ff-company-search` (`html.j2:78`) | `payload.companies` search (`js:2826`) | J1 |
| 3 | data_notice | `ff-data-notice` (`html.j2:105`) | `renderNotice` (`js:1043`) | J5 |
| 4 | access_gate | `ff-gate` (`html.j2:114`) | gate states (`js:664`) plus template `state_summary` preview | — |
| 5 | overview | `ff-overview` (`html.j2:212`) | `renderOverview` (`js:979`) | J1 |
| 6 | radar | `ff-panel-radar` (`html.j2:316`) | `orderedFindings` (`js:351`) / `renderFindings` (`js:1100`) | J1 |
| 7 | statements | `ff-panel-statements` (`html.j2:351`) | `renderStatements` (`js:1464`) | J2 |
| 8 | disclosures | `ff-panel-disclosures` (`html.j2:362`) | `renderDisclosureFeed` (`js:1334`) | J1, J2 |
| 9 | redlines | `ff-panel-redlines` (`html.j2:383`) | `renderRedlines` (`js:1390`) | J2 |
| 10 | timeline | `ff-panel-timeline` (`html.j2:395`) | `renderTimeline` (`js:1443`) | J2 |
| 11 | compare | `ff-panel-compare` (`html.j2:406`) | `renderCompare` (`js:1509`) | J2 |
| 12 | trace | `ff-panel-trace` (`html.j2:428`) | source map `renderTrace` (`js:1564`); run record attested-history (`js:2171`, `js:2204`, `js:2255`) | J2, J3, J5 |
| 13 | evidence | `ff-evidence` (`html.j2:455`) | `renderEvidence` (`js:2673`) / `renderDisclosureEvidence` (`js:2580`) | J2 |
| 14 | receipt_inspector | `ff-receipt-inspector` (`html.j2:474`) | `renderReceiptInspector` (`js:2420`) | J2, J3 |

Seven tabs in three groups (`html.j2:271-308`) are pinned by `tests/test_fundamental_forensics_ui.py:29`. Unique `id=` values are pinned by `tests/test_fundamental_forensics_ui.py:105`.

## 3. Receipts

Numeric findings (radar / evidence drawer): `finding.evidence[]` items are `{url, label_en/zh, basis, date}`. URLs are the EDGAR company browse page and the companyfacts JSON (`scripts/build_fundamental_forensics.py:183`; rendered `js:2690`). Company-level; no document anchor.

Disclosure receipts: `_bounded_receipt` emits `accession`, `form`, `source_url`, `source_sha256`, `source_span`, `source_excerpt`, `display_excerpt`, `block_id`, `section_id`, `cell_id` (`engine/fundamental_forensics/disclosure_projection.py:369`). `_bounded_finding` adds `filing_role` via the balanced-receipt helper and keeps `display_only` / `review_priority_only` (`disclosure_projection.py:460`). The page renders accession + excerpt + "Open SEC filing" (`js:2522`); it reads `display_excerpt` / `source_excerpt` / `filing_role` / `block_id` (`js:2526`, `js:2562`) and does not read `source_sha256` or `source_span` as identifiers. Links open the document URL; the char-span is provenance metadata, not a `#` jump.

Run record: identity keys `snapshot_id`, `base_snapshot_id`, `query_hash`, `published_at` (`js:1797`); latest payload exact keys at `js:1870`; paginated roots (`js:2204`); per-root waterfall (`js:2255`). CIK-gated to the selected company (`js:2113`).

## 4. Data contract

Machine list: `FIF_P0_VIEW_CONTRACT.json` `payload_contract`. Keys listed there are identifiers the JS actually contains.

**State** (`GET /api/forensics/state`, `js:9`; entitled gzip, `app/forensics.py:128`): `companies`, `ranked_findings`, `default_symbol`, `as_of`, `generated_at`, `source`, `detectors` (`js:343`, `js:353`, `js:837`, `js:915`, `js:1549`). Loopback QA reads `/data/fundamental_forensics/private/state.json.gz` (`js:7`).

**Company / period / finding / disclosure finding / health** keys are the `payload_contract` lists. Nine period metric keys are `METRICS` (`js:54`). Finding `title`/`summary`/`formula`/`threshold` are read through `fieldPair` (`js:204`, `js:2681`, `js:2726`).

**Attested-history latest** exact keys (`js:1870`): `snapshot_id`, `base_snapshot_id`, `query_hash`, `published_at`, `policy`, `clocks`, `coverage_summary`, `companyfacts_conversion_receipt`, `authority`. Any rename of those keys breaks the run-record tab. `coverage_summary` is required by that exact-key list even though shorter plan notes omitted it.

**Financial APIs not called by this page:** `POST /api/forensics/v1/financial/{query,revisions,packet,statements}` (`app/forensics.py:841`, `:888`, `:939`, `:990`). P2 must amend the JSON and this test in the same PR to start calling them.

## 5. First viewport (inference, unmeasured)

`first_viewport.measured` is false. No browser was run.

Desktop 1440 (`min-width: 1100px`, `templates/fundamental_forensics.css:1890`): body padding 26px (`css:1891`); workspace `min(100%, 1480px)` (`css:51`); evidence sticky on radar/disclosures/redlines/trace-receipt (`css:1893`); hero visual 300×210 (`css:2611`); run-meta four columns (`css:96`); context card three columns (`css:156`); overview `1.42fr` / 300px (`css:2661`); sticky tab bar (`css:409`). Stacked above the fold: nav, hero (`html.j2:25`), run-meta, company card, overview. Ranked findings (`ff-panel-radar`, `html.j2:316`) start at or just below the fold. The page leads with narrative (hero promise `html.j2:31`, overview quick-signal `html.j2:223`) rather than a metrics grid, matching `MASTERPLAN.md:105`.

Mobile 390 (`max-width: 700px`, `css:2023` and `css:2822`): hero visual `display:none` (`css:2827`); run-meta 2×2 (`css:2031`); evidence/receipt inspectors become sheets (`tests/test_fundamental_forensics_ui.py:253`). First viewport is nav + hero headline + deck + promise chips; picker and quick-signal sit further down.

## 6. EN / ZH

Mechanism: template macro `t(en, zh)` (`html.j2:1`) emits `.l-en` / `.l-zh`; JS `pair` (`js:185`) and `fieldPair` (`js:204`); placeholder/aria-label swap (`js:3028`). Counted now: 105 `{{ t(` call sites in the template; 204 `pair(` call sites in the JS. `i18n.template_title_attributes` is 0 — the template has zero `title=` attributes. JS has four `title=` marks wrapping technical IDs (`js:2348` and siblings).

## 7. Open P2 decisions

1. Cutoff control for J3: wire an as-of selector to `financial/query` or to non-latest snapshots, and show historical absence.
2. J4 peer cohort + saved comparison: persistence owner, exclusion reasons, permalink.
3. J5 export entry point: API, Excel, or both; whether a refresh control is added beside reload.
4. J1 ranking: magnitude versus today's review-priority then recency (`scripts/build_fundamental_forensics.py:731`).
5. Forensics site-semantics page: `docs/site_semantics/` currently holds `china.md`, `china_stocks.md`, `etfs.md`, `macro.md`, `stretch_oracles.md`, `us_stocks.md` only.

## 8. GAPS

- First-viewport fold position is inferred from markup/CSS (`css:1890`, `css:2822`); `measured` stays false.
- Sparse tree has no `data/`; live company/finding counts were not observed.
- Hero (`html.j2:25`) and tab bar (`html.j2:271`) have no `id=`; they are described here and omitted from `panels[].dom_id`.
- Projection fields `source_sha256`, `source_span`, `cell_id` (`disclosure_projection.py:377`) are not JS identifiers, so they are omitted from `payload_contract.evidence_receipt_keys`.
- `payload.summary` is produced by the builder and unused as a JS identifier; omitted from `state_keys`.
- Finding `display_only` is set in the builder (`scripts/build_fundamental_forensics.py:265`) and checked by `tests/test_fundamental_forensics_page.py:85`; the JS does not read that identifier.
- GET catchall `app/forensics.py:705` is not a page fetch.
- `query_service.py:517` helper name is not copied here.
- No screenshots, no UI edits, no journey implementation in this freeze.

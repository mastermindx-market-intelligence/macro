# Sovereign auction context — bounded consumer integration contract

**Status: source-only display implementation handoff accepted by the program owner; no product code changed, no tests run, no deployment or live availability claimed.** Prepared 2026-10-08. Root accepted the Mastermind served sibling and Terminal proxy/strip seams, will acquire the official workspaces and reconcile actual writer state separately, and has explicitly scoped the next builder to source-only work without deployment. Root remains the canonical writer and chooses display enablement. This brief does not create a new research commission or revise the prior null/KILL findings.

**W1 pin supplied by root:** stable lifecycle module under `w1_patch`, SHA256 `3db6b0d390c488134ae466a8a929f6c02e73a44e508436b4d7ab77ae28351781`. The consumer builder should bind its exact fixture to that module and the final feed wrapper. This task inspected the consumer sources; the W1 digest is an owner-supplied receipt, not an independent hash recomputation here.

## 1. Decision

Use the one Macro artifact, `site/feeds/event_calendar.json`, and the exact nested key `sovereign_auction_context`. Deliver the first Mastermind integration through the existing **served Market View** and the first Terminal integration through the existing **authenticated display-feed proxy and macro context strip**.

The Mastermind response adds a display-only sibling after loading the existing artifact. It does not populate the stored `event_calendar` plane yet. That distinction has an observable purpose: stored plane availability affects coverage and data-quality summaries that already reach AI seats. An advisory label alone does not establish byte-identical decision inputs.

The Terminal displays an independent auction context chip beside the existing Neural Web strip. It does not use `market_risk.json`, the Oracle decision panel, the copilot, or a historical replay rail. These either have active source overlap or are the wrong semantic surface.

The next builder can implement this bounded consumer vertical against the stable W1 module and a pinned fixture in root's official workspace. Macro publication-path verification is a separate integration acceptance check and does not block fixture-based source implementation. No new upstream fetch from Treasury, auction research engine, per-name score, portfolio rule, shared credential, worker, or scheduled job is required.

## 2. Exact current-source evidence

Source pins:

| Repository | Inspected commit |
|---|---|
| Mastermind | `c7e47c859eb2925c5626931fd511800773ba09ac` |
| mastermind-terminal | `d660d98b1ebc0bdf0d1b16d66202b1760f6cc94a` |

`SOURCE_RECEIPTS.json` contains immutable URLs, Git blob IDs, local paths and SHA256 digests for 35 fetched files. All 35 local copies were checked against their actual Git blob IDs after removing only an extra scratch serialization newline. This is source verification, not application verification. Existing census copies of `brain/anticipation.py`, `brain/treasury_context.py`, and `ingest/pull_macro_risk.py` supply the additional boundary evidence already returned by the implementation/null census.

### Mastermind call paths

1. `data_layer/macro_refresh.py` uses `vendor/macro` / `vendor/macro_src`; `_SPARSE_PATHS` already includes `site`. Its current production note says the VPS uses `vendor/macro -> /opt/macro`; this is a source statement, not a fresh host-symlink receipt. The R2 mirror only includes `stockdata`, so **an R2-only calendar cannot be assumed to materialize on a non-symlink host**. Do not add `feeds` blindly to the per-ticker manifest downloader. Verify the owner's actual publication/copy path.
2. `config/contracts.yml` already declares `feeds-plane`: `path: site/feeds/`, owner `macro_engine`, allowed effect `display-only`, degradation `ADVISORY`, consumer list currently empty. Extend that existing declaration with the actual new reader.
3. `brain/market_view.py` already reserves `event_calendar` in `PLANE_ORDER`; `view()` currently constructs an absent H4 handoff record. Its validated set is exactly `risk_radar`, `mtf_signals`, and `cycles`.
4. `bot/phase2.py` assembles and persists the Market View before position decisions, then persists `brain/decision_context.py` output. `decision_context.assemble()` reads every plane, counts availability, and passes data quality through `prompt_summary()`. `brain/pm_conviction.py::_market_view_enrichment` only includes directional plane summaries, but data-quality and other context still reach prompts. Therefore populating an advisory plane in the stored view is a separately reviewable change.
5. `app/web.py::api_market_view` reads `data/market_view/latest.json`, calls `_enrich_rotation_pairs` on the served copy, and returns it with no-cache headers. `app/static/market_view.html` fetches `/api/market_view` and renders the one view. This is the smallest existing display composition seam.
6. `brain/treasury_context.py` is a different, single-reader Treasury Watch bridge. Its `MASTERMIND_TREASURY_CONTEXT` flag is default OFF and registered at A4 in `config/authority_map.yml` / `control_plane/flags.py`. When enabled it changes `brain/strategist.py::_strategist_input` and `brain/pm_conviction.py::_build_prompt`. Do not widen that flag by silently inserting auction fields.

Immutable primary code:
- [Market View assembler](https://github.com/mastermindx-market-intelligence/Mastermind/blob/c7e47c859eb2925c5626931fd511800773ba09ac/brain/market_view.py)
- [Typed decision context](https://github.com/mastermindx-market-intelligence/Mastermind/blob/c7e47c859eb2925c5626931fd511800773ba09ac/brain/decision_context.py)
- [Existing web response enrichment](https://github.com/mastermindx-market-intelligence/Mastermind/blob/c7e47c859eb2925c5626931fd511800773ba09ac/app/web.py)
- [Feeds contract](https://github.com/mastermindx-market-intelligence/Mastermind/blob/c7e47c859eb2925c5626931fd511800773ba09ac/config/contracts.yml)
- [Vendoring owner](https://github.com/mastermindx-market-intelligence/Mastermind/blob/c7e47c859eb2925c5626931fd511800773ba09ac/data_layer/macro_refresh.py)

### Terminal call paths

1. `terminal/app/api/nw/route.ts` already owns an allowlisted same-origin display proxy. Its current feeds are `market_plane` and `selection_cohort_us`.
2. Its October 6 entitlement contract is load-bearing: relay only the caller's `sb-*-auth-token` cookie, no service credential, no cache shared between callers, `Cache-Control: private, no-store`, `Vary: Cookie`, `redirect: manual`, four-second timeout; 401 remains sign-in-required, 402/403 become not-entitled, other upstream errors become unavailable. Current `NW_FIXTURE` mode is an existing development seam.
3. `terminal/lib/upstreams.ts` owns endpoint configuration. `NW_BASE` defaults to `https://www.mastermind-x.com/neuralwebdata`. Do not import this server-only configuration into a client bundle.
4. `terminal/components/NeuralWebStrip.tsx` polls `/api/nw?f=market_plane` every five minutes and renders macro display context. It currently returns null without the market plane. An auction sibling must remain independent of that condition; one upstream's absence must not hide another source's valid evidence.
5. `OracleDash.tsx::MarketRiskChip` and `copilotTools.ts::curateMarketRisk` expect nested `built` / `display.verdict`, whereas pinned `pull_macro_risk.py` emits flat `market_risk/v1`. The contemporaneous held repair PR #852 independently records that mismatch. This is a known source mismatch; live rendering was not tested here.
6. `terminal/lib/replayEngine.ts` explicitly records that the existing Macro event calendar was forward-only and could not truthfully serve past-session replay markers. A current auction lifecycle context is not a historical replay dataset.
7. `ingest/terminal-refresh.sh` is an aborting stub, not an ingestion owner. Its two-copies narrative is stale: current `ops/terminal-data` records the August 10 resolution in favor of itself and says Macro's installer now installs that exact wrapper. This vertical can use the existing HTTP proxy, avoiding a nightly wrapper change entirely.

Immutable primary code:
- [Authenticated proxy](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d660d98b1ebc0bdf0d1b16d66202b1760f6cc94a/terminal/app/api/nw/route.ts)
- [Proxy entitlement tests](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d660d98b1ebc0bdf0d1b16d66202b1760f6cc94a/terminal/lib/__tests__/nwRoute.test.ts)
- [Macro display strip](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d660d98b1ebc0bdf0d1b16d66202b1760f6cc94a/terminal/components/NeuralWebStrip.tsx)
- [Endpoint owner](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d660d98b1ebc0bdf0d1b16d66202b1760f6cc94a/terminal/lib/upstreams.ts)
- [Actual nightly owner](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d660d98b1ebc0bdf0d1b16d66202b1760f6cc94a/ops/terminal-data)

## 3. W1 boundary to consume

The builder provided the following contract in this session and root subsequently supplied the stable W1 module digest above. This is not an observed production payload. Bind one exact fixture and the feed wrapper to that producer pin for the source-only consumer build.

| Field | Required interpretation |
|---|---|
| `schema_version` | Exact `sovereign_auction_context_v1`; unsupported schema is unavailable, not permissive passthrough |
| `is_context_only` | Exact boolean true |
| `forecast_authority` | Exact `RESEARCH_ONLY` |
| `probabilities` | Null; no default probability or percentage |
| `importance` | `NOT_SCORED` in W1; never cast to a risk score, band, or rank |
| `decision_cutoff_utc` | Producer's as-of decision clock, not event time |
| `source_observed_at` / `asof` | Maximum valid eligible receipt / its UTC date; not proof that every source is current |
| Per-source `source_health` | Preserve source URL, latest attempt/status, last valid observation, body receipt, failure reasons and age separately |
| `stale_after_seconds` | Null in W1. No consumer-invented five-day/48-hour freshness certification |
| Row `known_at` | Conservative producer observation clock; later-known evidence cannot be joined into an earlier decision |
| `competitive_deadline_utc`, `date`, `time_et` | Scheduled calendar clocks. A future auction is allowed; a future evidence receipt is not |
| `result` / `result_evidence_fields` | Null absent actual result evidence. Deadline passed does not mean result observed |
| `source_state`, `physical_state`, `issue_calendar_state` | Separate producer state vocabularies, copied rather than recomputed |
| `offering_amount_usd` | Dollar amount with unit; never gross issuance relabeled as reserve drain |
| `null_reasons` | Retain reasons; missing is not zero, calm, safe, no auction, or settled |

Rows additionally carry `type=AUCTION`, `label`, `source`, `impact=null`, `assets=['bonds']`, `episode_id`, `normalized_class`, announced/issued CUSIPs and announcement/auction/issue dates.

The consumer should use a strict allowlist and pure, clock-injectable validation. It must not reuse generic market-risk or event-impact coercion. Preserve supplied identifiers, clocks and exact source URLs. Validate finite numeric values; null remains null. Reject source observations after the producer cutoff or after the injected current clock. Do not compare a scheduled future deadline to now as if it were a data error. Do not use filesystem mtime, HTTP delivery time, another feed's date, or the wrapper's latest receipt as a substitute for a row's knowledge clock.

A producer lookup failure may be displayed as a failure with the last valid observation's date, where W1 actually retained it. It cannot be called live/current merely because HTTP returned 200. In W1 the correct freshness label is observation/age plus **freshness unassessed**, unless the final producer contract supplies a stronger explicit policy.

## 4. Bounded Mastermind builder contract

### Allowed source targets

| Path | Bounded edit |
|---|---|
| `brain/sovereign_auction_context.py` (new) | Sole local reader of `vendor/macro/site/feeds/event_calendar.json`; extract and validate only the nested context; pure validator/projection plus fail-soft reader |
| `app/web.py` | One response-only helper/call in `api_market_view`, modeled on existing display enrichment; append `sovereign_auction_context` sibling to the served dictionary |
| `app/static/market_view.html` | Small current auction section using escaped text and source links; show observation/unknown/result states truthfully |
| `config/contracts.yml` | Add the new reader to existing `feeds-plane.consumer_modules`; keep display-only/ADVISORY |
| `tests/test_sovereign_auction_context.py` (new) | Pure validator and PIT/null/authority tests |
| `tests/test_web.py` or a focused new API test file | Response composition and nonmutation test with temporary source and stored Market View fixtures |

No `bot/phase2.py`, `brain/market_view.py`, `brain/decision_context.py`, PM/strategist, `brain/anticipation.py`, risk/exit engine, or portfolio configuration edit is needed for this first display vertical. The source snapshot is the Macro writer's responsibility, not something a page request should generate.

Use a fresh read per request or a cache keyed by exact file identity and observation/cutoff, with an explicit reset path. Do not inherit the Treasury Watch reader's process-lifetime cache. When the stored Market View is unavailable, preserve its existing endpoint status; do not fabricate a Market View merely to show auction data.

The existing `event_calendar` plane remains the eventual canonical perception slot. Populating it later requires a separate narrowly scoped review of coverage, decision-context availability, prompt inputs and any flag registration. This brief does not authorize its enrollment in validated contributors.

### Display wording

Show “Sovereign auctions — observed context”, the producer cutoff/observation, an explicit “Not scored” importance label, episode/class and scheduled auction/issue date, with null deadlines shown as unknown. Use “Results not observed” when `result` is null. Do not produce an instruction to hedge, reduce risk, raise cash, or alter a holding.

The auction section is a sibling to the Market View's existing planes and tilt panels; its label must make clear that its observations are outside the displayed decision-plane coverage calculation.

## 5. Bounded Terminal builder contract

### Allowed source targets

| Path | Bounded edit |
|---|---|
| `terminal/lib/sovereignAuctionContext.ts` (new) | Pure typed validator/presentation model for exact W1 nested object; no fetch, score, cache, or signal import |
| `terminal/app/api/nw/route.ts` | Add one fixed allowlisted request `f=sovereign_auction_context`; fetch the existing Macro event-calendar path and extract the exact nested context |
| `terminal/lib/upstreams.ts` (only if needed) | Centralize the exact official Macro event-calendar endpoint; do not introduce arbitrary client-provided URLs |
| `terminal/components/SovereignAuctionContext.tsx` (new) | Independent display component with deterministic rows, observed clocks, source links, and unavailable states |
| `terminal/components/NeuralWebStrip.tsx` | Compose the new sibling next to the existing strip; avoid nesting links and avoid making the sibling contingent on `market_plane.verdict` |
| `terminal/lib/i18n.tsx` | Exact EN/ZH LEX tuples for new static copy |
| `terminal/lib/__tests__/sovereignAuctionContext.test.ts` (new) | Pure validation/presentation tests |
| `terminal/lib/__tests__/nwRoute.test.ts` | One new-feed matrix preserving every existing entitlement test |
| Focused component/e2e test in existing test tree | Current/unavailable/result-not-observed plus responsive and localization proof |

The fixed proposed upstream is the existing Macro website's `/feeds/event_calendar.json` on the same canonical origin as `NW_BASE`. **Actual serving and entitlement are unverified here.** Root must verify that exact publication path under the existing Macro owner; if it is unavailable, report unavailable and finish the producer publication step. Do not substitute public R2, another origin, a service credential, or a second API to get around a denial.

Preserve the existing proxy's per-caller cookie relay and no-cache behavior in full. Keep old `market_plane` and `selection_cohort_us` response paths byte-compatible. Never accept `url`, path traversal, or an arbitrary source string from query parameters. The new route selects a fixed path; it returns a curated nested context, not the entire event calendar and not a protected upstream envelope.

The new component can reuse `nw-strip` / `nw-chip` tokens without a chart, modal or new navigation system. Use a separate sibling element because the existing strip is an anchor. Keep any rendered list bounded in producer order and identify truncated display counts. Never sort by synthetic severity or imply that an unscored episode has high/low probability.

A network/auth failure must clear the auction-specific current state; it must not retain previous entitled data on a sign-out, new session or 403. Polling cadence may reuse the existing five-minute display cadence, but this is a refresh attempt cadence, not a data-freshness guarantee.

## 6. Existing flags and risk authority

There is no current sovereign-auction display flag in the inspected consumer files. Root owns the W1 display-OFF decision. Default-OFF should gate the consumer display/request at the chosen existing deployment setting or producer publication boundary; it must not be implemented by reusing a forecast or risk flag.

If the owner chooses to add a Mastermind `MASTERMIND_*` flag, use its existing flag registry and authority-map mechanism with an explicitly display-only effect. Do not repurpose `MASTERMIND_TREASURY_CONTEXT`, `MASTERMIND_GLT_MODE`, stale-freeze controls or risk flags. No display setting may arm prediction or decision authority.

Critical hazard: `brain/anticipation.py::_crash_auction_leg` looks up `auction_stress` OR `treasury_auctions`, then accepts `stressed` or a generic `band` such as high/elevated. It does not inspect a context-only flag first. **Neither alias may receive this context anywhere, even when the importance algorithm is later scored.** “Advisory” is not a substitute for the separate key.

The existing Terminal KILL on market-regime modulation of per-name ARM/CONFIRM exits remains in force. This vertical must not suppress, escalate, delay, recolor, re-rank or regenerate those warnings. The prior Macro auction-absorption NO-GO and D2 auction-concession FAIL remain unchanged.

## 7. Ownership and overlap census

`PR_COLLISION_RECEIPTS.json` records all open PR metadata observed: 293 Mastermind and 100 Terminal PRs, with selected relevant file lists. This is not a lease/worker census and not proof that any open branch is currently being modified. Root must perform the existing source-custody check before editing an already owned file.

| Candidate | Verified relevance / disposition |
|---|---|
| Terminal #849, head `2ae82269a6e655b444ce2c13febcc4080dfa7c9e` | Edits `ingest/pull_macro_risk.py` plus a new truth test. Separate risk-staleness owner; no auction changes there |
| Terminal #852, head `b9431005331f4e1655ceaa5419fdc82bdbce9c76` | Held copilot schema repair, published helper and patch; existing copilot file deliberately restored. Do not implement that held repair as part of this task |
| Terminal #833, head `0a99c8ec28ba5218c0aaa1e3daecde70004f2006` | Edits `copilotTools.ts` and copilot tests; another reason to omit copilot wiring in W1 |
| Terminal #614, head `14f567a144e43c94f73d936ffa4aed37601932ee` | Stock Intelligence redesign edits `OracleDash.tsx`, signal button and responsive tests |
| Terminal #620, head `79efa2c34a861dfcc968a251817ad51022b3da95` | Risk context in Stock Intelligence also edits `OracleDash.tsx`; use the independent macro strip for this vertical |
| Terminal #619, head `a92516e5ceb82d9fa5ddcbb78cc80bba3f752f85` | Related launcher identity and shared responsive tests |
| Mastermind #565, head `d85b8df2220b7dd0ae7e456e63a747f6346f7f8d` | **Different meaning of auction:** crypto/volume-profile auction theory prototype under research only, no Treasury collector or product seam. Do not treat as prior sovereign implementation |
| Mastermind #124, head `23f97360131d05123acc440da15780b0bb200e82` | Liquidity quant-foundation branch with very broad historical diff; not an auction reader. Its file list is not a safe merge plan |
| Mastermind #789, head `d48be1f9c5a514b13bad1265cca7fb55ba144614` | `brain/bot_mcp.py` evidence-truth work; no need to touch that path |

PR metadata and source trees can change after these receipts. A current base pin must be rechecked before any concrete source edit. Older source instructions about checkout creation must not override Mastermind's current custody launcher or the root's accepted workspace assignment. No checkout was created here.

## 8. Required verification for the first consumer vertical

These are **tests to implement/run**, not passed results:

1. **Identical authority-bearing outputs:** read a fixed stored Market View and call the enriched API with auction absent, valid, malformed, future-known and mixed result states. Existing `planes`, `coverage`, `coherence`, `net_posture_tilt`, `label_vs_planes`, `posture_floor_defense`, `assembly`, `budget_ref`, `brief` remain exact. Stored bytes before/after API calls remain exact. A compiled/hash read of the same stored `decision_context`, PM and strategist fixture payloads must be unchanged.
2. **Crash-auction isolation:** on a fixed calm and stressed regime fixture, add any valid new nested context, including hostile extra `band=critical` / `stressed=true` inside it. `anticipation.crash_risk` remains exact and its incumbent `auction_stress` leg remains absent unless the original regime fixture had a separate original leg. Prove that no adapter writes either forbidden alias.
3. **PIT boundary:** future scheduled auction accepted; future observation rejected; result published after cutoff withheld; deadline passed without observed result stays null; source max receipt cannot rescue an older/failing row; invalid date/offset, NaN/Infinity, booleans-as-numbers and mixed-class identities cannot become known values.
4. **Null and freshness honesty:** missing object, unsupported schema, authority widened, malformed list, all results null and explicit source failure are distinct from a valid empty event set. A 200 body with unknown refresh policy never gets a live/fresh badge. Clock-injected tests prove these states after elapsed wall time.
5. **Entitlement isolation:** extend the existing `nwRoute.test.ts` matrix to the new feed: no cookie/no fetch; only approved cookies forwarded; 401/402/403 propagated; redirects refused; timeout/malformed body unavailable; no entitled bytes sent to later anonymous caller; no shared stale cache. Fixture mode cannot leak into production or reach the live source.
6. **Exit/entry invariance:** fixture equality for existing Oracle verdict and ARM/CONFIRM warning sequence with the auction response toggled on/off; no new imports from auction display into `signalVerdict`, `signal_layer` or portfolio modules. If those modules are untouched, use targeted dependency/static plus end-to-end displayed-warning evidence instead of rerunning a market study.
7. **Real composition proof:** one exact producer fixture passes through the actual Mastermind API reader/page and Terminal route/component. The same episode ID, cutoff, observed clock, amount unit and null-result reason appear in both. A fresh incognito EN/ZH light/dark responsive pass at 1440×900, 820×1180 and 390×844 records no reload workaround, nested anchor, clipped important state or horizontal overflow.
8. **Release truth:** compile/typecheck focused new code, run existing relevant Market View/web/anticipation and NW route tests, then required CI/review under the real owner. Live publication/entitlement and exact deployed SHA are separate receipts, never inferred from scratch tests.

## 9. Remaining concrete gates

- Bind the exact W1 fixture/feed wrapper to the stable owner-supplied module digest above; record source health vocabulary and producer enablement.
- Verify Macro's actual canonical website serving path and Mastermind local publication path. Publication on R2 alone is insufficient evidence for either proposed authenticated/locally vendored consumer.
- Decide the display-OFF setting and exact activation procedure in the existing owner, without a prediction switch.
- Reconcile exact source custody for `app/web.py`, `market_view.html`, `/api/nw`, `NeuralWebStrip` and shared i18n/tests before modification.
- Execute the bounded source changes and meaningful tests above under root's source-only assignment. Deployment is excluded from the next builder scope; no empirical forecast or risk promotion is needed for this vertical.

The research brief and H1–H5 preregistration candidate already returned remain the independent research lane. This consumer contract does not convert those unrun experiments into a pass.


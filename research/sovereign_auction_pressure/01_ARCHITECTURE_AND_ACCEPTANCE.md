# Sovereign Auction and Funding Pressure Intelligence — implementation architecture

**Version:** `sovereign-auction-program.context.v1`, 2026-10-08. **Program owner:** the current Chairman-assigned CEO session, under Macro #6819 and `WS:RATES-INFLATION-COMMAND`. **Delivery posture:** source-only, Draft/HOLD; the attached commission excludes deployment, paid data acquisition and changes to trading, sizing or exit authority. This is an adopted implementation architecture, not an empirical signal verdict.

## 1. The first executable vertical

The Macro Treasury data owner retains immutable official-response observations. A pure lifecycle projection reads eligible observations and supplies `sovereign_auction_context` inside the existing `site/feeds/event_calendar.json`. Mastermind and Terminal read that one produced object through their existing display transports. Research and economic primitives remain separate from display importance and from risk decisions.

| Responsibility | Existing owner / implementation seam | Contract |
|---|---|---|
| Official source acquisition | Macro Treasury auction data; `scripts/capture_treasury_auction_observations.py` | Bounded attended capture; fixed official HTTPS sources; no scheduler or new collector registry |
| Immutable evidence | `<existing data root>/treasury_auctions/observations/*.json` | Exact response bytes and digest, source URL/schema, request/body/parse clocks; failures retained separately |
| Lifecycle projection | `engine/treasury_auction_lifecycle.py` | Pure clock-injectable snapshot; six classes, exact deadlines, identity aliases, corrections and visible coverage limits |
| Economic primitives | `engine/treasury_auction_primitives.py` | Externally qualified inputs, exact units, explicit missingness; no market-data acquisition or predictive model |
| Publication | `scripts/build_feeds.py`, existing `event_calendar.json` | Additive nested context; preserve existing 21-day calendar arrays; new context has its own 30-day horizon and source clocks |
| Mastermind display | Existing `/api/market_view` response enrichment and Market View page | Served sibling only. Stored planes, coverage, decision-context, PM and strategist inputs remain unchanged |
| Terminal display | Existing authenticated `/api/nw` allowlist and active `TerminalShell` detail area | Fixed calendar path, caller entitlement, private/no-store response, independent context component |
| Research evidence / continuity | This Macro research directory and existing Macro Agent OS | One evidence owner; no duplicate Agent OS, job controller, notifier, calendar or data warehouse |

### Existing delivery path, corrected source order

`event_calendar.json` is the sole Git exception in `site/feeds/`; other feeds remain R2-only. The existing daily feed-build step moves immediately before its existing engine-output commit, followed by the existing R2 publisher. There is no additional scheduled invocation. Existing Macro Git refresh/`site.served` rsync and Mastermind's `site` sparse cone can therefore receive the same produced bytes. Authentication remains Macro's existing registration and staged `site_full` paywall policy. No direct public-R2 fallback or new Terminal tier predicate is introduced.

The first data directory is seeded with four exact immutable official responses captured on October 8. Acquisition remains attended-only. Daily reprojection can advance the query cutoff and lifecycle window; it never changes the original source observation clock. Collector cadence, immutable archive selection beyond the v1 read bounds, a freshness SLA and production activation remain explicit readiness work. A local byte-copy/reader proof is not a deployed or entitled HTTP acceptance claim.

Terminal's previously proposed `NeuralWebStrip` is dormant in the current product. The accepted leaf is mounted directly after the existing actions in `TerminalShell.tsx`; it does not activate that strip or its old risk fetch. Its shared-file PR census is recorded with the consumer evidence.

The source-only code is useful without a predictive result. Default production exposure remains the existing producer-publication boundary: unmerged/undeployed candidates create no live product change, and an absent nested producer object is unavailable. No forecast or risk flag is repurposed as a display setting.

## 2. Source and clock contract

The first adapter supports inspected TreasuryDirect current JSON, the quarterly tentative schedule XML and PendingAuctions v4 XML. The October 5 migration specification is evidence for a future adapter; it is not permission to guess unobserved fields. Unknown or migrated shapes become unsupported/degraded, never a valid empty calendar. Original announcement/result XML amount conversion is documented in the casebook but is outside this first parser. PDFs remain source evidence, not silently parsed structured fields.

The seven clocks remain distinct:

| Clock | Meaning and implementation |
|---|---|
| Physical event | Auction competitive deadline, issue date, scheduled announcement date |
| Official source publication | Only an independently supported release clock; otherwise null. A date or raw minute without timezone is preserved with its precision limitation |
| Source update / revision | Raw API update timestamp and source digest; neither backdates publication nor system availability |
| Request/body receipt | Literal capture start and complete-body arrival; HTTP Date and Last-Modified are separate metadata |
| System availability | Conservative parse-completion bound in a forward capture; older research captures use their explicitly qualified verified-availability upper bound |
| Decision cutoff | `decision_cutoff_utc` / `as_of`; eligibility requires receipt knowledge no later than this cutoff |
| Build/render | Publication or rendering activity; cannot freshen an underlying observation |

`source_observed_at` is the maximum valid eligible observation, with its UTC date in `asof`. It does not certify that every source is current. `source_health` retains every origin's latest attempt, latest failure, actual body receipt, last valid observation and age. The body receipt is read only from qualified literal capture metadata; missing legacy body clocks remain null. Parse completion is the conservative availability bound, not body arrival. Aggregate last-body and last-valid clocks are independent: parsing can finish later, and a later malformed body can follow an older valid observation. Consumers display the observation and **freshness unassessed** because v1 has no accepted source-age policy. They reject evidence from after the producer cutoff or their injected current clock; future scheduled deadlines remain valid calendar facts.

Capture validates the exact official HTTPS host before following redirects and on the final response. It persists complete receipts using a no-overwrite publication operation. Malformed bodies remain evidence but produce a non-success semantic status and CLI exit; missing bodies are failure receipts. This is an application no-overwrite property, not a claim of WORM storage or crash-proof disk durability.

Directory snapshots select a bounded recent file set by local write time, then independently validate content digests and aware receipt clocks. File mtime only selects candidates. More than 128 files/envelopes, the input byte bounds, or a row limit produces explicit truncation and null counts. A historical replay exceeding these limits supplies an explicitly selected eligible envelope set; this reader is not a historical warehouse.

## 3. Identity, instrument and phase rules

An announced auction episode uses the announced CUSIP plus auction date, with issued-CUSIP and original-CUSIP aliases retained. Ordinary reopenings on different dates remain different episodes. The documented February 25, 2025 unscheduled reopening proves the issued CUSIP can change; no CUSIP-only deduplication is permitted.

A pre-CUSIP schedule has its own slot and edition. Merge only a unique exact class/official term/auction date/issue date match. Normal coupon/FRN reopenings can use the explicitly supplied original-security term; Bills keep the current offered term. A nominal nearest-tenor guess cannot merge an event. Ambiguous matches remain visible conflicts. Current-source revisions never overwrite older observation bytes or backdate an amended deadline.

| Class | Economic distinction |
|---|---|
| Bill / CMB | Short duration and potentially large financing/refinancing throughput; CMB is a Bill legal form with a separate official class/flag |
| Note / Bond | Fixed nominal yield-duration exposure; remaining maturity and original auction cohort are distinct fields |
| TIPS | Real-yield duration on appropriately indexed market value; separate axis from nominal DV01 |
| FRN | Supplied effective-rate duration and reset/discount-margin convention; nominal two-year maturity is not a fixed-rate duration estimate |

Source stage is inferred from actual evidence, not endpoint names. The captured `/announced` list includes completed results. Future result-bearing contradictions are quarantined. Passing a deadline without a result creates `AWAITING_RESULT`, retained into subsequent days within the recent horizon. Later stale tentative/announcement snapshots cannot regress an observed result. Passing issue date creates `ISSUE_DATE_PASSED`; it does not assert purchaser payment or confirmed reserve settlement. Cancellation/postponement completeness and arbitrary auction-date changes need notice-backed reconciliation and remain an explicit extension gate.

## 4. Economic quantities and deterministic importance

The implemented provided-duration approximation is:

`DV01_USD_per_bp = qualified_market_value_USD × qualified_duration × 0.0001`.

The quantity is a first-order sensitivity, not a pricing model. Coupon cashflows, convexity, licensed ex-ante prices, TIPS index acquisition and FRN reset modeling are not inferred. Input source, valuation clock, availability clock, units, method and role are required. Unknown inputs produce null quantities. Nominal, real and effective-rate axes cannot be blindly added.

Private settlement cash is separately calculated as:

`private_cash_proceeds_excluding_SOMA − private_marketable_redemptions − funded_buyback_cash_outlays`.

Every category needs a qualified component or a sourced explicit zero and an upstream completeness certification. Cohort/date/currency must agree; duplicate component IDs are rejected. Gross face and SOMA context are not silently subtracted from already private proceeds. Negative net financing can be a valid result of correctly signed nonnegative cash components. Reserve pressure remains null because accounting does not identify purchaser funding channels or subsequent Treasury expenditure.

The optional deterministic magnitude percentile compares distinct earlier events with the same class, official tenor, sensitivity axis and measurement basis. The method requires at least 20 eligible comparators, excludes current/future/result-role contamination, defines ties by midrank and versions its 75/90 attention thresholds. These are product relevance choices. They are not calibrated risk probabilities. W1 does not yet supply qualified market inputs or a PIT comparable history, so its actual feed remains `NOT_SCORED`, with no fabricated fallback tier.

The actual October 6 DTS case further limits implementation: TIPS principal indexation and bill discount adjustments separate debt face accounting from cash accounting. Aggregate Treasury cash changes, total public-debt cash transactions and privately financed auction cohorts are different universes. See the independent outcome-blind funding audit for exact original table reconciliation.

## 5. Consumer isolation and existing holds

Mastermind currently accepts generic `stressed`/`band` values under legacy `auction_stress` or `treasury_auctions` in `_crash_auction_leg`. The new context is never aliased to either key. A strict display allowlist drops hostile extra risk fields and consumes no numerical forecast. Even inserting an advisory stored Market View plane would change coverage reaching AI prompts, so this first consumer enriches only the served response, after the canonical artifact is loaded.

Terminal retains the existing caller-cookie relay, private/no-store and Vary:Cookie behavior, redirect refusal, timeout and entitlement statuses. Neither public R2 nor a service credential bypasses a denial. Session/sign-out transitions clear context and invalidate in-flight responses. The independent auction component does not depend on a market-plane verdict and does not touch Oracle, copilot, replay, ARM/CONFIRM or exit policy.

| Existing work | Reconciliation |
|---|---|
| Macro #7273 | Held actual-clock/calendar/Brain-grounding candidate preserved; no edits to its branch or owned dashboard paths |
| Macro #7320 | Held competitive-allocation denominator repair preserved; current results collector and treasury_supply remain outside this branch |
| Macro #8241 | Held Bonds R11 actually edits build_bonds.py; both builder and template ownership preserved |
| Macro #7022 / #7949 | Existing Alert Center and shared shell preserved; no second notifier or shell |
| Terminal #849 / #852 / #833 | Existing market-risk stale/schema/copilot work preserved; the new display does not reuse that drifted bridge |
| Terminal #614 / #620 | Existing OracleDash writers avoided through a direct, independent leaf after the existing detail actions |
| Mastermind #565 | Crypto/volume-profile auction theory, not sovereign auction implementation |

Open PR state alone is not a live lease. Root acquired the installed canonical operation workspaces, verified exact base/preimages and checked current target-path movement. The new operations do not take over older branches, clear their holds or replay their earlier refused effects.

## 6. Research and authority gates

The attached research questions are separated into H1 announcement news, H2 pre-auction burden × fragility, H3 settlement funding, H4 post-result information and H5 equity downside. Existing SLF-006 NO-GO, D2 auction-cycle FAIL and Terminal exit-modulation KILL remain beside every future verdict. The strongest first additional empirical experiment is H3, but a public descriptive study is not an own-system PIT forecast.

The canonical design adoption record fixes the hypotheses, clocks, baselines, placebos, family-wise testing and promotion requirements before new fitting. Model implementation, eligible-data manifests, entitled inputs and exact statistical registration are still required before opening challenge outcomes or starting a prospective log. No training run, numerical client probability, prospective clock, timer or background collector is implied by these documents.

| Gate | Required evidence / current meaning |
|---|---|
| G0 source custody | Exact refs, existing owners, scoped branches, no unresolved mutation; source census and operation receipts |
| G1 source integrity | Representative real six-class casebook and current bounded capture; full historical amendment/cancellation coverage and migrated schema remain incomplete |
| G2 economic correctness | Independently checked provided-input arithmetic; live qualified prices, complete private cash inventory and bidder-share held repair remain separate |
| G3 Macro product | Actual overview/Bonds UI and full responsive/localization proof; held incumbent integration remains pending |
| G4 research integrity | Adopted design plus executable eligibility/accounting audit; no fitted model or completed statistical experiment |
| G5 predictive increment | Untouched eligible evaluation versus actual baseline, calibration/placebos/costs; not passed or claimed |
| G6 production / consumers | Source tests and fixture composition precede exact deployed path/entitlement/source-age proof; source completion is not deployment acceptance |
| G7 decision use | Separate existing decision-owner authority and demonstrated incremental value; OFF |

The final verification receipt records exact commits, commands, test counts, original source capture failures, and which integration evidence actually ran. International extension remains behind the U.S. acceptance gates. No universal cross-asset bearish direction or cash-first instruction is introduced.

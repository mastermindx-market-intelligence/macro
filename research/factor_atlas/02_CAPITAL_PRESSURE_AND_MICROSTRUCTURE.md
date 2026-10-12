# Factor Atlas — Capital Pressure and Microstructure

Session 2 research, mathematical reconstruction, implementation contract and native pilot plan.

**Status:** original deterministic reference implemented and tested on controlled fixtures; **licensed-market pilot NOT_ADMITTED; customer publication NOT_AUTHORIZED; mission incomplete**. This is not a claim of exact LIQN numerical parity, current full-market capture, improved forecasting or institutional buyer identification.

## 1. Decision and product outcome

Build a measurement product, not an institutional-money detector. A sufficiently covered factor should show four separate answers: how much eligible activity occurred; which side appears to have initiated it; whether activity or pressure is unusual at this clock; and which constituents account for it. Holdings and fund creation/redemption information remain separate evidence panels.

The recommended first useful product is **activity magnitude plus clearly labeled estimated pressure**, with coverage, method and source age beside the number. Quote-based classification should become the stronger measurement where a synchronized, rights-qualified tape actually exists. Do not assume that a theoretical subscription capability means that tape is retained or production-ready.

The public LIQN explanation was recovered during this continuation. Its outlined mechanics can be reconstructed, but its undisclosed numerical policies prevent exact reproduction certification. The existing prototype has therefore gained a separate disclosed-core profile while retaining its deliberately conservative research alternative. The distinction is versioned rather than hidden in an implementation detail.

The differentiation should be defensibility: truthful source clocks, explicit uncertainty, gross-versus-net accounting, overlap disclosure, concentration, parallel estimators and falsifiable empirical results. A more complicated score without additional information is not a superior product.

## 2. Source identity, recovery and authority

Protected procedure: Mastermind `732cf7be88e7159b4995a8885fbd381cd1484e3e`, Skillpack 1.0.1 / bootstrap 1. INDEX, ACTIVE_EXECUTION, SESSION_RELIABILITY, COLD_START, WEB_CEO_DELEGATION and CLOSEOUT were loaded from that revision. The protected branch was reread unchanged at recovery.

Analysis source pins:

| Surface | Immutable analysis source |
|---|---|
| Macro | `cdbcd143dcfa419ab0637bc11dd4c80368143e2e` |
| Terminal | `bacda5dcc30682f9327e037a2d4425bd9714ac3a` |
| Recovered Session 2 candidate | `809ab2e2c9e712445b9d28e65e16faa783b0d65c` |
| Native disclosed-core milestone | `80231c289e284f702e2aba5e69394829c784c1e1` |

Original branch: `claude/factor-atlas-capital-pressure-20261008`. Operation label: `factor-atlas-capital-pressure-20261008-c1-001`, not an invented Executive Job. The explicit Chairman commission supplies research and bounded implementation intent, not production, procurement, source-custody displacement or signal promotion.

After the prior generation failed, the original remote head was read back before any new effect. Its committed source was fetched into a fresh isolated M2 research worktree; the missing conversation scratch files were not treated as surviving evidence. No prior write was replayed. GitHub remains the source/evidence owner; Executive owns worker admission; existing source and data owners retain their custody. No duplicate factor graph, calendar, warehouse, publisher, queue or event-replay authority is introduced.

A separate previous platform denial affected reads of four mandatory Macro files: `research/MASSIVE_ADVANCED_INTEGRATION_MASTERPLAN_BY_FABLE.md`, `research/LIVE_DATA_POLYGON.md`, `scripts/build_polygon_intraday.py`, and `collectors/massive_flatfiles.py`. These exact reads were not retried through another tool. Consequently, the mandatory source census is **partial**, not complete. This is an action-scoped access boundary, not evidence that all tools or all feeds are unavailable. A subsequent attempted benchmark-metadata/test repair was also denied before a process receipt; that edit is not part of the delivered implementation.

## 3. LIQN primary-source findings

[P1] is a public LIQN support reply by **Jared, labeled Team**, dated September 14, on the question “flow calc.” It supplies a methodology outline, not source code or a reference-output fixture.

| Item | Publicly disclosed outline |
|---|---|
| Input | One-minute close-to-close **price changes** |
| Scale | Last 60 minutes, same session; neutral before 20 minutes of history |
| Classification | Student-t CDF, degrees of freedom 0.25 |
| Dollars | Volume multiplied by close |
| Aggregation | Plain constituent sums, not factor-weight scaling |
| Accumulation | From 04:00 ET |
| Historical comparison | Matched-clock median and scaled MAD; current constituents |
| Z display | Regular hours; excludes half-days/poor coverage; withholding rules apply |

The selected baseline windows include 5D, 1M, 3M, YTD and 1Y. Exact usable-sample thresholds, variance denominator, inclusion of the current change, sparse-minute treatment, zero-MAD policy and corporate-action conventions are not specified. The first-five-minute withholding statement should not be silently extended into an undocumented premarket Z product. [P1]

**Correction to reconnaissance:** “one-minute returns” is not an exact transcription of the disclosure. Percentage returns and dollar price changes are distinct inputs. Resetting volatility separately at 09:30 and 16:00 is also not established by the same-session description. A current-cohort historical comparison is not point-in-time factor performance.

## 4. Independent mathematical reconstruction

For security i and eligible minute t, define unadjusted price P, eligible volume V and the price change d_t = P_t - P_(t-1). Let H_t contain valid adjacent one-minute changes ending in the preceding 60 wall-clock minutes, excluding the current change. The reconstruction uses n >= 20 and sample standard deviation:

    mean_d = sum(d_j for j in H_t) / n
    sigma_t = sqrt(sum((d_j - mean_d)^2 for j in H_t) / (n - 1))
    z_t = d_t / sigma_t
    f_t = T_(0.25)(z_t)
    gross_t = V_t * P_t
    buy_t = f_t * gross_t
    sell_t = gross_t - buy_t
    net_t = buy_t - sell_t = (2*f_t - 1) * gross_t

The numerator is the current change, **not** that change minus the historical mean. Centering occurs in the standard-deviation estimator. Using a centered numerator would define another estimator.

For any 0 <= f <= 1, buy and sell are nonnegative, buy + sell = gross, and |net| <= gross. Summing these inequalities over the same eligible observation set preserves the bound. Every transaction has a buyer and seller; this classification partitions each counted transaction once by inferred aggressor side. It does not measure a literal imbalance in the existence of buyers and sellers, and gross is not twice the traded notional.

A standard Student-t with df 0.25 has a valid CDF but no finite mean or variance. Therefore sigma here is an empirical scale of observed changes, not the theoretical standard deviation of a t(0.25) random variable. The normal-consistency MAD multiplier does not turn the resulting score into a Gaussian tail probability. Neither f nor a displayed Z is a calibrated institutional-buying probability.

### Explicit reconstruction choices

The implementation keeps uncertainty visible rather than attributing these choices to LIQN:

| Condition | Implemented research behavior |
|---|---|
| First eligible bar of session/basis | f=0.5; net=0; marked neutral, not directionally usable |
| Fewer than 20 valid prior changes | Disclosed-core profile: neutral; conservative profile: unavailable |
| Current change | Excluded from its own volatility history |
| Denominator | ddof=1; alternatives require a separate estimator identity |
| Zero empirical volatility | Default neutral with a quality flag |
| Analytic zero-scale sensitivity | Separate option: positive change -> f=1; negative -> f=0; zero -> 0.5 |
| Sparse interval / missing predecessor | No multi-minute jump disguised as a one-minute change; neutral and flagged |
| Explicit zero volume | gross=net=0; does not create a price-change observation |
| Basis or session change | Reset history; never sign an overnight or split gap as flow |
| Premarket -> regular / regular -> after-hours | Disclosed-core shares same-day history; conservative profile resets by segment |
| Invalid/nonfinite price, volume or clock | Reject; do not repair with fabricated zero |

The first valid directional observation under lagged 20-change warmup requires 20 prior adjacent changes plus a current change: an off-by-one choice must be fixed in a vendor parity exercise. “20 minutes” alone does not settle it.

### Monetary basis

Three amounts must remain named differently:

    exact eligible-print notional = sum(price_k * decimal_size_k)
    bar VWAP notional estimate = volume * reported_bar_vwap
    close-based notional proxy = volume * close

The second equals the first only when VWAP and volume cover the identical corrected trade universe with sufficient precision. Typical price, such as (high+low+close)/3, is neither a true VWAP nor the disclosed close basis; it would be another proxy. Never multiply split-adjusted prices by incompatible unadjusted volume. For monetary pressure, prefer retained unadjusted observations; an adjusted family needs reconstructable price/volume factor conventions bound to the exact source vintage.

The native API is `bvc_series(bars, config, cutoff_utc_s=..., mode=...)`. `disclosed_core_config()` selects price changes, close notional, same-session history and neutral warmup. Plain `BVCConfig()` preserves the conservative return/segment/unavailable-warmup profile. Both share the deterministic implementation, CDF and accounting checks. [I3]

## 5. What alternative estimators can and cannot measure

| Estimator | Information and advantage | Principal error / required comparison |
|---|---|---|
| Disclosed-core BVC | Cheap nonlinear price-volume pressure description | Cannot recover unique aggressor identities from bars; current scale and granularity matter |
| Normal-CDF BVC | Transparent standard comparator using Phi(change/scale) | Different compression; not independent source information |
| Close-to-close sign times dollars | Simple, auditable baseline | Allocates an entire bar to one side; bounce and zero-tick conventions dominate |
| VWAP/deviation or close-location pressure | Describes where price trades relative to a reference | VWAP drift, trend and endogeneity; not observed fund allocation |
| Prints at prevailing bid/ask | Uses transaction and quote evidence rather than bars alone | Stale/late/locked/crossed quotes; inside-spread and auction ambiguity |
| Midpoint plus tick fallback | Higher classification coverage with explicit fallback | Quote sequencing and tick carry can be wrong; midpoint is not universal ground truth |
| Hierarchical measurement | Uses the best admissible evidence with quality states | Selection bias and double counting if quote coverage and bar fallback overlap |
| Off-exchange / TRF context | Observed reporting venue and activity segmentation | Does not reveal a hedge fund, beneficial owner or dark-pool intention |
| ETF creations/redemptions and holdings | Primary-market shares or disclosed positions | Different clocks, units and economic objects; never splice into intraday BVC dollars |

The literature does not support one universal accuracy percentage. Easley, Lopez de Prado and O'Hara find useful links between BVC and information proxies; Chakrabarty, Pascual and Shkilko find conventional classification more accurate in their equity samples; Panayides, Shohfi and Smith distinguish aggressor recovery from information detection. Market, sampling rule, benchmark and target all matter. [P2-P4]

A valid benchmark hierarchy is: true exchange-scoped aggressor flags with documented semantics; then synchronized quote-based classifications; then weaker print/tick comparisons. NBBO classification is an **inferred reference**, not perfect tape truth. A book-derived flag for one venue cannot be assumed to cover off-exchange trading.

BVC is a deterministic function of the supplied price/volume history. Conditional on that entire history, it adds no new source information. It can still be useful as a representation in a finite model. The appropriate forecasting test is therefore against comparably flexible return/volatility/turnover controls, not merely a weak linear baseline that makes a nonlinear transform look like a new information source.

## 6. Quote-based reference and explicit fallback states

The proposed quote study consumes an **already-owned** eligible trade/quote slice. It does not start a collector. Normalize source identity, participant time, SIP time, receipt time, revision/cancel status, conditions, listing and reporting venue first. Massive's public stock schemas expose these clocks and trade corrections; quote and trade sequence numbers are not a shared global order. Preserve nanosecond integers without routing them through lossy JavaScript floating-point values. [P5-P7]

For each eligible continuous-session trade:

1. Select the latest valid NBBO that precedes the trade on the declared clock, with quote availability no later than the measurement cutoff. Never use the nearest quote on either side of the trade, because that admits future information.
2. Require positive bid/ask, bid < ask, valid quoted sizes and an eligible condition set. Locked, crossed, one-sided or absent quotes are separate states, not automatically neutral trades.
3. Apply the registered quote-age limit. Start with 1 second as a **research assumption**, with 100 ms and 5 second sensitivity reports; no age is a vendor-guaranteed truth threshold.
4. At or above an admissible ask classify buyer-initiated; at or below bid classify seller-initiated. Separately report outside-quote prices. For trades inside the spread compare with midpoint; exact midpoint may use the prior nonzero tick only within the same eligible security/session chain.
5. Otherwise emit UNKNOWN, with excluded dollars, count and reason. Never silently remove unknown trades from the headline denominator.

Participant-clock reconstruction and SIP/receipt-clock operational reconstruction are different experiments. Late TRF reports must not be aligned against a quote from their later reporting instant and presented as execution-time truth. Auctions, corrections, cancels, out-of-sequence reports, average-price transactions and other special conditions require their own source-owner rules. A live stream lacking later correction information is provisional; final REST/archive reconciliation must remain with its incumbent ingestion owner. [P5-P8]

For classified tape dollars B and S and unknown eligible dollars U:

    covered_net = B - S
    classified_gross = B + S
    gross_eligible = B + S + U
    signed_dollar_coverage = (B + S) / gross_eligible
    possible_full_net_interval = [covered_net - U, covered_net + U]

This interval is an accounting bound within the observed eligible tape, not a statistical confidence interval or a bound on entirely missing prints. It makes a large uncertain remainder visible even when the classified subset looks decisive.

V1 should show quote-covered pressure and BVC as **parallel labeled measurements**. Selecting a quote method when coverage qualifies, otherwise BVC, is acceptable only with an explicit method/state change. Never add quote-signed dollars to BVC over the same bar. A residual-dollar hybrid is a later experiment requiring exact reconciliation of trade conditions, corrections, clocks and notional universes, plus proof that the unclassified remainder is not systematically different.

Suggested states: QUOTE_REFERENCE, QUOTE_PARTIAL, MIDPOINT_TICK_FALLBACK, BVC_ESTIMATE, NO_DIRECTION, SOURCE_UNAVAILABLE. Include a method mix rather than a single unexplained confidence score. No state identifies the beneficial owner.

FINRA reporting-venue data and short-sale data remain distinct: weekly ATS/non-ATS summaries have publication delays, and short-sale volume is not outstanding short interest. Preserve each dataset's actual initial-publication and revision clocks. ETF share creation/redemption can change shares outstanding without a one-for-one public-market purchase of its holdings; secondary-market ETF volume is not fund inflow. Quarterly Form 13F positions have their own filing clock and omit short positions. [P9-P12]

An issuer-based ETF estimate can use split-consistent change in shares outstanding times aligned NAV. Call it estimated net issuance, not intraday trading pressure. A holdings change needs quantity/corporate-action normalization, not a difference in market values. Both belong beside, not inside, the BVC aggregate.

## 7. Matched-clock abnormality and session policy

Use America/New_York to define market wall time and true UTC for event/receipt comparisons. Consume the incumbent exchange calendar; do not create a weekday-only replacement. The source must provide the actual regular close and any qualified extended-hours policy.

| Window | Comparison key and handling |
|---|---|
| Premarket | 04:00 through regular open, same completed minute and phase |
| Regular | Actual open through actual close; normal and early-close classes separate |
| After-hours | Actual close through 20:00 only where the owner qualifies that interval |
| Session-to-date | Same declared start anchor, end clock, membership and accumulation definition |
| First hour / lunch | Fixed pre-registered elapsed/wall-clock windows, not windows chosen after price moves |
| Closing auction | Condition-aware auction observation separated from continuous bars |
| Special event | Source-known event category and scheduled window; no retrospectively chosen “event” label |
| Halt / thin interval | Explicit excluded or unknown interval; no invented zero volume or carried price |

On an early close, 13:00 is an endpoint, not permission to include a bar beginning at 13:00 in RTH. The current Terminal qualifier explicitly leaves some early-close post-market observations unqualified; that remains a data-admission constraint, not a permission to guess. Holidays have no regular observation. Daylight saving changes UTC offsets but must not change the matched ET clock. [I4-I6]

For target metric X_(d,m), first select prior scheduled sessions D whose sources were actually available by the permitted cutoff. Exclude the current session, later corrections not yet known and future sessions. Then compute:

    center_m = median(X_(h,m) for h in D)
    MAD_m = median(abs(X_(h,m) - center_m) for h in D)
    base_scale_m = 1.482602218505602 * MAD_m
    floor_m = max(absolute_floor, relative_floor * median(prior_gross_(h,m)))
    scale_m = max(base_scale_m, floor_m)
    robust_z = (X_(d,m) - center_m) / scale_m

Use independent reference distributions for signed minute dollars, gross minute dollars, cumulative signed dollars, cumulative gross dollars, turnover and dimensionless imbalance. Do not divide today's minute flow by a cumulative-flow baseline, or treat the return Z and flow Z as interchangeable.

Prototype defaults are a 60-session maximum, 20 usable observations and 80% scheduled-session coverage. These are engineering research defaults, **not LIQN's undisclosed minimums or statistically validated universal cutoffs**. A 5D request cannot satisfy a 20-session floor and should return insufficient history unless a separately registered profile explicitly accepts a smaller sample. Full/early-close classifications and matching calendar windows form part of the denominator; the reference cannot improve its reported coverage by dropping inconvenient scheduled days.

Zero MAD with no positive floor returns ZERO_SCALE and null Z. A positive floor is explicit and changes the interpretation to FLOORED_SCALE; the output includes the floor and reference gross. Never substitute an arbitrarily tiny epsilon that manufactures enormous significance. For a known identical target and zero-scale history, an empirical tie percentile remains meaningful while a standardized score remains undefined.

Keep raw Z and display-clipped Z separate. The prototype clips display at +/-12 but retains the raw value. Primary references are not winsorized: median/MAD already provide robustness. Sensitivities may test training-only 1%/99% winsorization, 20/60/126/252-session windows and instrument-relative floors; every choice counts in the research search budget. Events and true outliers are not removed merely because they hurt performance. Inconsistent/stale data may be excluded under independently defined quality rules.

Native `matched_baseline()` verifies prior dates, ET clock, completion, availability, duplicate revisions, method and membership identity. It consumes caller-qualified observations. A supplied identity string, `complete=true`, or timestamp is not independent proof of custody or rights. Availability qualification must come from the actual source/reader owners.

## 8. Multi-basket joins, concentration and overlap

Use one unique security-minute measurement and a sparse incidence map A_(f,i,v), where v is the exact membership version. Compute raw factor dollars as A times the security-dollar vector. Process observations once, then update affected factors through an inverted security-to-factor join. This costs approximately O(observations + membership edges) per step rather than repeatedly reading the same tape for each factor.

Maintain two distinct membership modes:

- **point_in_time:** membership and weights genuinely available at the historical decision;
- **current_cohort:** today's explicitly selected roster measured over past data, labeled with its selection time and survivorship limitation.

Never let current-cohort backfills enter a purported point-in-time forecasting experiment. Rebalancing changes the reference identity; do not splice old-roster baselines into new-roster targets. Use independently qualified house baskets and canonical security identities, not restricted third-party membership copied into public product outputs.

For a factor with admitted constituent set S:

    gross_f = sum(gross_i)
    estimated_net_f = sum(net_i) on a disclosed common coverage set
    pressure_ratio_f = estimated_net_f / classified_gross_f
    gross_share_i = gross_i / gross_f
    effective_number = 1 / sum(gross_share_i**2)

Report expected/observed members, prior-ADV-weighted coverage, observed gross, classified gross, top-1/top-5 gross share, effective number, positive/negative participation and constituent contributions. Percent contribution to **net** becomes unstable near zero; prefer dollar contribution and share of absolute signed activity instead. A few headline names may genuinely dominate raw-dollar pressure; that is an observation to expose, not a defect to hide with weights.

Market-cap weighting belongs to a separately named dimensionless indicator, for example sum(w_i * net_i/gross_i) with predecision weights and explicit missingness. It is not dollars flowing into the basket. Equal weighting and capped weighting are sensitivity views. Cap/ADV normalizers must carry their own as-of times; missing weights are not renormalized without a visible partial-state rule.

Overlapping baskets intentionally reuse constituent observations. The union count includes each security once; sum-of-factor totals counts some securities multiple times. Emit both only to show duplication:

    duplicated_gross = sum_factor_gross - unique_union_gross

Never label sum_factor_gross “total market capital flow.” ETF shares and their underlying constituents also represent different instruments and can double-count economic exposure even when their security IDs differ.

Unique pressure is the activity of S_f minus a specified comparison union; show the excluded membership and remaining coverage. Residual pressure instead estimates a historical conditional expectation given market/sector return, volatility, turnover and other groups, then subtracts it. Fit only on past data. Call the result residual estimated pressure, not newly observed dollars or an independent capital flow. Collinear overlapping factors need regularization or a fixed orthogonal basis selected outside the test interval; do not reverse-engineer a residual after inspecting desired outcomes.

## 9. Exact proposed consumer read contract

The future consumer schema is `factor_atlas.capital_pressure.read.v1`; it is a read model, not a new source authority. Production validation and adapters are not implemented by the research prototype.

| Field family | Required semantics |
|---|---|
| Identity | factor_ref, security_refs, membership_version, membership_basis, membership_selected_at; existing canonical IDs |
| Measurement | estimator_id, full config digest, change_basis, notional_basis, currency, granularity, session anchor, phase, window start/end |
| Observations | gross_observed_usd, inferred_buy_usd, inferred_sell_usd, net_covered_usd, full_net_usd nullable; quote_unknown_usd and its accounting interval when available |
| Coverage | expected/observed members and slots; classified gross share; missing/neutral/excluded counts; quote-age quantiles and reasons |
| Baseline | measure/key/version, prior-session window, n, scheduled denominator, median, MAD, scale/floor, percentile, raw/display Z, excluded-session reasons |
| Contributions | security reference, signed/unsigned amount, source age, method, state; deterministic ordering |
| Overlap | intersecting factor refs, duplicated inclusion, unique-union scope; never an additive market total |
| Clocks | event_start/end, source_as_of, received_at, owner_read_at, available_at, computed_at, expires_at; each distinct |
| Provenance | source response/page/revision refs, input digest, calendar ref, basis/corporate-action ref, source-quality and rights receipt refs |
| Authority | descriptive_only=true; may_rank/may_alert/may_size/may_trade=false; publication false until consumer acceptance |

Use UTC epoch milliseconds where JavaScript can represent them exactly; serialize nanosecond clocks as decimal strings. All monetary numbers must be finite. Null means unavailable; numeric zero means measured or explicitly policy-neutral zero with the state retained. A partial covered sum is not presented as the complete factor total.

`source_as_of` comes from input observations, never from build time. Earliest eligible use is bounded by event completion, required finality and actual source/downstream receipt. A later historical download may be used in corrected-history analysis but cannot receive a fabricated historical first-seen clock. Prior immutable reader receipts retain their original capture-prefix identity through later corrections. Unsupported versions, basis conflicts and same-availability revision conflicts fail closed through existing selectors.

The producer freezes estimator and membership versions for each materialized result. The consumer rejects inconsistent units, wrong-factor data, mismatched windows, future clocks, impossible gross/net accounting and stale artifacts. It distinguishes unavailable, insufficient-history, zero-scale, warmup, partial-coverage, rights-withheld and stale states. Last-good data may remain visible only with its actual age and stale designation, never relabeled as current. `confidence` remains null until an explicitly named calibrated target earns it.

## 10. Entitlement, archive and current-capture census

The enterprise entitlement record is an operator-confirmed engineering authority for broad delivered equity data, non-display factor research, derived materials and archival retention. It is not the underlying confidential agreement; no contractual commercial terms were retrieved or republished. Do not reopen its closed global licensing gate merely because this is a new study. Bind the relevant use to that record, then check any dataset-specific designation, restriction or actual technical refusal. Raw NBBO redistribution can have additional conditions; Factor Atlas does not acquire permission by accepting a string called `rights_ref`. [I1]

| Data family | Evidence actually inspected | What remains unproved |
|---|---|---|
| Equity minute aggregates | August 8 manifest: successful nonempty request, 836 rows | Current coverage by ticker/date/phase; uninterrupted capture; full archived window |
| Equity second aggregates | Same manifest: successful nonempty request, 50 rows | Retained second history, practical throughput, current capture |
| Equity trades | Manifest records real-time permission evidence and deep historical probe | Full tape completeness, same-condition notional, actual current latency and cancellation retention |
| Equity NBBO | Manifest records NBBO/recent-quote access | Quote-age distribution, synchronized signing coverage and archive cost |
| Broad license | Existing enterprise record supports research/derived use | Exact selected source family and any separately designated exchange/feed conditions |
| Terminal 5m/1h store | October 2 historical inventory and current implementation read | Fresh whole-estate inventory; no retrospective per-row availability implied |
| Terminal retained 1m observations | Existing producer/reader/selector code and retained-reader contract | Installed cohort, admitted raw monetary basis and sufficient captured sessions |
| Off-exchange context | Public trade schema includes TRF identity/time | Current licensed retained TRF population; beneficial-owner identity remains unobservable |
| ETF issuance / holdings | External issuer/regulatory concepts are observable | An installed exact source/rights/availability owner for this consumer was not established |

The August probe is dated **2026-08-08T11:47:39Z**. Its `tick_history_depth` is a probe-derived estimate, not proof of every ticker-minute since that depth. Public vendor documentation describes broader historical capabilities; it cannot certify Mastermind's current account, collector or archive. A successful listing or HEAD is not a successful full dataset GET. [I2, P5-P8]

### Mandatory implementation findings

`engine/group_flow.py` computes a daily thematic fingerprint from relative-strength acceleration, breadth, cohesion and persistence. It is not a minute-dollar BVC engine and does not observe institutional allocation. Reuse its basket/context boundary, not its word “flow” as evidence of tape measurement.

`engine/flow_signing.py` already contains pure quote/tick rules and calibration primitives. Its opening entitlement statement is scoped by the options-flow history and is stale if generalized to equity NBBO access. The August equity manifest is positive evidence against that generalization. Its quote method also needs an equity source adapter to enforce quote validity, age, conditions and source ordering; a midpoint comparison alone is not a complete production signing policy. [I2-I3]

`research/OPTIONS_FLOW_DATA.md` preserves negative options-signing evidence: its June calibration reports 0.41 minute net-sign recovery and rejects delta adjustment on tested samples. These are historical options results, not this session's reproduced measurements and not estimates of equity BVC accuracy. They demonstrate why direction and magnitude must be assessed independently. Even unsigned magnitude requires complete, valid inputs; a blanket code flag cannot certify source coverage. [I3]

`research/INTRADAY_LARGE_CAP_TECH_LEADER_PREREG.md` gives an existing IFT-owned current-universe study and a 09:30/09:45 availability boundary. It is useful ownership and research discipline, not permission to inspect held outcomes or retrofit this study into a new historical universe. [I7]

Four explicitly requested source reads remain blocked as recorded in section 2. Their unread implementation details, ingestion cadence and exact publication responsibilities are therefore **unqualified**, not inferred from filenames.

### Terminal storage and source clocks

The October 2 inventory documented 680 five-minute files, 4,108 hourly files, 21,113,724 five-minute bars, 960,613,373 five-minute bytes and roughly 2.7 GB total intraday storage. Files differed substantially in start/end dates and freshness. These are historical inventory results, not a fresh census performed by this continuation. [I4]

The current inspected producer supports a 40-day 1m request window, 400-day 5m requests and a 60,000-row store cap. The cap is row-based, not a uniform number of trading days. A one-minute capability does not imply an installed one-minute archive. The serving store chooses 5m or 1h history and does not fabricate historical 1m data. Its chart epochs encode ET wall time as UTC; the existing qualifier must invert that encoding before research. [I5-I6]

One default M2 directory was checked and absent in the earlier phase. This observation does not establish that the production VPS or private estate has no data. The current whole-estate ticker/session/timestamp denominator remains **NOT_PROVEN**.

The retained-minute producer uses the existing per-symbol store; the Macro bridge takes an actual downstream read receipt. Source response time, reader completion and event time remain separate. The inspected reader deliberately returns basis-null Terminal rows and refuses to treat caller metadata as adjustment evidence. Its documented finality lag is 900 seconds. Therefore this path cannot be advertised as instantaneous live pressure merely because equity streaming permission exists. [I8]

Existing bounds include 1–16 explicit capture symbols, 4,096 capture attempts per file, 16 pages per capture, 8 MiB per response and 32 MiB per file. These are capacity limits, not a guaranteed study horizon. Retention, installed source, raw-basis qualification and scientific admission are separate gates. Terminal #844 and Macro #8623 remain independent source-delivery dependencies, not branches to overwrite or assume accepted.

### Exact receipt needed to close the census

For each selected source object, the existing owner must return: canonical security ID; requested interval; actual first/last event and observed/expected slots by phase; adjustment/volume conventions and action evidence; request/page/response identities; correction/cancel handling; actual first-seen and downstream-read clocks; file size/hash and immutable revision; rights reference/use classification; installed producer/release identity; latest successful capture and current failure state. Quote samples additionally require age quantiles, classified/unknown dollars and venue/condition breakdown.

This receipt may conclude no usable pilot exists. It must not silently refresh data, buy a feed, start a daemon or mark an absent observation zero. It should be generated by the existing data qualifier and reader, not a second Factor Atlas warehouse inventory service.

## 11. Incumbent storage, publication and data-quality architecture

The smallest architecture is:

    incumbent equity source/capture + canonical identity/basis/calendar
      -> existing input qualification and revision selection
      -> pure security-minute measurement
      -> sparse factor projection using approved membership version
      -> incumbent private object publication and authenticated consumer

The older R2 delivery census identifies separate public facts, premium products, private operations, raw vendor material and unresolved families. Its dated observations are not proof of today's deployed ACLs. The current inspected Research Vault store provides private, dedicated-credential storage and strict bounded reads that distinguish authoritative absence from unavailable/unauthorized responses. Reuse the approved private-store and delivery owners; do not repoint a public bucket or create an alternate bypass origin. [I9-I10]

Full pressure/history should stay private until the existing product gateway authorizes the requested tier and source rights. A public preview must be a separate allowlisted projection, not the complete paid object hidden by CSS. No new `/api/factor-flow` implementation is authorized by merely naming it in this report; the product integrator should route through its existing authenticated read surface after exact owner/interface review.

Keep source-quality status load-bearing: invalid clocks, duplicated revisions, incompatible basis, low coverage, stale capture and partial publication should withhold affected measurements without erasing valid independent magnitude observations. Preserve last-good artifacts by immutable identity. A publisher timeout must not overwrite a valid dated object with an empty “current” object or invent a successful release.

The first periodic path should consume an already-written source generation after its actual finality delay. A five-minute refresh is a proposed owner-scheduled consumer cadence, not a new daemon and not a guarantee of five-minute-old data. A one-minute or event-driven view comes later through the incumbent streaming owner when receipt latency, correction behavior and cost are proven. Whole-market flat files arrive later and are baseline/backfill material, not an intraday live source; the public quickstart describes approximately 11:00 ET next-day availability. [P8]

No customer signal, public R2 object, scheduled service, provider purchase, market-data authority or live trading state was created by this work.

## 12. Resource and incremental-cost architecture

No current per-contract incremental vendor fee was established. The engineering record supports broad licensed use, but it does not publish confidential volume caps, overage schedules or exchange-specific charges. **Do not write “$0 incremental feed cost” as a verified commercial fact.** This session made no new feed purchase and performed no live provider-data acquisition.

Use measured bytes and event rates from the qualified cohort before production sizing. The following is an explicit **planning scenario**, not a fleet benchmark: 960 possible one-minute slots per full 04:00–20:00 session and 96 stored bytes per row after shared metadata conventions. Sparse trading may create fewer rows; source receipts and replicas may create more bytes.

| Universe | Dense rows/session | Storage/session at 96 B | 60 sessions | 252 sessions |
|---|---:|---:|---:|---:|
| 30 names | 28,800 | 2.765 MB | 0.166 GB | 0.697 GB |
| 3,000 names | 2,880,000 | 276.480 MB | 16.589 GB | 69.673 GB |
| 5,000 names | 4,800,000 | 460.800 MB | 27.648 GB | 116.122 GB |

These decimal-unit numbers scale linearly with bytes/row, retention and physical replica count. They do not include quotes, trades, raw response custody, corporate-action tables, object metadata, indexes, application caches or parallel estimator outputs.

Current public R2 Standard pricing is $0.015 per GB-month, $4.50 per million Class A operations and $0.36 per million Class B operations, with rounding and free-tier conditions. A retained 3,000-name dense one-year bar set in this scenario is approximately $1.05/month of storage before other data, shared-account effects or contractual differences. Three such copies are roughly $3.15/month. Those low bar-storage amounts say nothing about full quote-tape feasibility. [P13]

For tape, use:

    daily_bytes = N_trades * bytes_per_trade + N_quotes * bytes_per_quote
    retained_bytes = daily_bytes * retained_sessions * replica_count

As a hypothetical scale example, 1 million trades plus 20 million quotes at 64 bytes each is 1.344 GB per session before additional envelope/index overhead. It is not a measurement of these names. Compression ratios must be measured; the earlier synthetic compact-row gzip ratio is not a vendor-tape compression estimate.

Avoid a remote object operation per trade or per factor-constituent. Bundle deltas through the existing partition/publisher owner. At 3,000 names, 192 five-minute steps and 21 sessions, writing one object per name per step produces 12,096,000 writes; a single bounded cross-factor generation per step produces 4,032. Choose partition sizes for recovery and query patterns, not merely the smallest request count. Billing rounds and the shared free tier make fractional arithmetic different from an invoice.

The kernel retains at most 60 prior valid changes per active security: 180,000 float64 values for 3,000 names is 1.44 MB before Python/object/identity overhead. A dense 150-factor, 960-clock, 60-session baseline cube is 8.64 million values, about 69.12 MB per float64 measure before masks and provenance. The prototype materializes results and is not a production memory benchmark; a production implementation should use bounded batches and incumbent columnar stores.

The older committed synthetic Linux receipt describes 28,800 rows and approximately 2.34 seconds of kernel work on its exact historical source. It excludes feed I/O, publication and concurrent fleet load. It was not reproduced on the current source in this continuation. The native proof is the 79-test run, not a production throughput or RAM promise. An attempted native benchmark-unit repair was blocked and remains unapplied; do not relabel the historical Linux receipt as a Mac benchmark.

## 13. Historical validation, leakage controls and falsifiers

Separate three experiments: **measurement fidelity**, **descriptive utility** and **forward predictive value**. Success in one does not imply success in the others.

### Measurement fidelity

Start with the disclosed-core BVC, conservative return BVC, normal-CDF counterpart, close-sign baseline, VWAP/deviation baseline, quote reference and tick fallback. Fix method/config identities before outcomes. Build the same eligible print/bar notional universe for every comparison, retaining unknown and excluded mass. Compare buyer-dollar fractions, normalized signed-dollar error, minute/window net-sign recovery, total-activity reconstruction and classification coverage. Report near-zero-reference intervals separately so meaningless sign flips do not dominate.

Use actual exchange flags only where their meaning and venue coverage are proven; otherwise call the result agreement with a quote-based reference. Break results down by name, dollar-volume/liquidity stratum, spread, phase, quote age, event day, halt/reopen, auction and direction. A liquid three-name pilot cannot support a whole-universe claim.

### Descriptive and economic tests

Test whether pressure remains informative after conditioning on contemporaneous returns, volatility, total turnover, market/sector movement and past pressure. Use flexible controls with comparable model capacity. A visually attractive flow panel may remain valuable even if the predictive coefficient is zero.

A later predictive study may pre-register next-30-minute residual return as its primary endpoint, with 10-minute and remaining-session endpoints as secondary. Entry/reference times must follow completed and available inputs; bar-close knowledge cannot justify a fill earlier in that bar. Spread, slippage, turnover, costs and capacity belong in any trading-value claim. No such market outcome was computed here.

A practical staged sample is five source-qualified sessions for engineering replay, then a larger source-qualified sequence with at least 20 baseline sessions, 20 development sessions and 20 untouched evaluation sessions. This is a proposed minimum pilot design, not evidence that the current 40-day capture window can supply it. If the source cannot support the sample, return INSUFFICIENT_DATA instead of shortening the holdout after viewing results.

Split chronologically by session. Purge overlapping labels and apply an embargo covering the maximum tested horizon. Fit volatility controls, beta/residualization, winsorization, missing-data rules and tuning only on permitted past data. Bootstrap contiguous day/week blocks, not independent trade rows. Preserve clustered days, overlapping baskets and repeated names in uncertainty estimates. Report all tested model/profile/floor/window choices through the existing TrialLedger/Evaluation OS owner; Session 6 controls independent quantitative acceptance, not a new ledger created here.

Do not select membership from future winners, calculate a “same-minute” reference from today's observation, interpret a later corrected file as a historically available one, choose quote lags after inspecting desired classification, or tune against the untouched evaluation set. Re-run immutable prefixes after appending future observations and revisions; earlier admissible outputs must be unchanged.

### Falsifiers that must survive publication

1. The disclosed formula is reconstructed but signs actual trades poorly.
2. BVC adds no explanatory or predictive information beyond return/volatility/turnover controls.
3. Useful minute statistics are confined to liquid names or regular hours.
4. Quote signing has inadequate coverage or unacceptable processing/retention cost at broad scale.
5. Estimated pressure is useful descriptively but has no stable forward edge.
6. Current-cohort baselines look compelling but point-in-time memberships fail to reproduce them.
7. Apparent factor pressure is mostly one or two large constituents or overlapping groups.

Publish these conclusions with denominators and confidence intervals where appropriate. Neither a negative result nor a data shortage should be hidden behind a newly tuned score. Promotion requires an independently reviewed exact experiment and the relevant consumer authority; a fixture PASS is never sufficient.

## 14. Staged native implementation packets

These packets are bounded implementation specifications, not worker dispatch receipts or new owners. Source/rights and scientific gates apply to the affected packet only. Session 1 owns factor identity/membership interfaces, Session 5 owns product presentation and Session 6 owns independent quantitative acceptance; Session 2 does not recreate those lanes.

### S2-P0 — deterministic measurement reference: implemented, not accepted production

**Source boundary:** only `research/factor_atlas/session2/prototype/{pressure.py,test_pressure.py,test_disclosed_profile.py,witnesses.py,test_witnesses.py,mutation_check.py}` and research evidence. Native milestone `80231c289e284f702e2aba5e69394829c784c1e1` adds the disclosed-core profile without changing ingestion or consumers.

**Interfaces:** immutable `Bar`, `Segment`, `BVCConfig`, `PressurePoint`, `MatchKey`, `Reference`, `BaselineConfig`, `Membership`; `bvc_series`, `buy_fraction`, `disclosed_core_config`, `matched_baseline`, `aggregate_factors`. No network, credentials, database writes, calendar generation or publication in the core.

**Proof:** 67 recovered tests passed, then the 12-test reconstruction extension first produced 11 expected failures / 1 pass. The complete prototype suite passed **79 tests** after implementation. Source SHA-256: `34cf424cdb33ac7edc2b1af83334f2117692b8b3569de93b6c632c6729a75edb`. Runtime: native M2 Python 3.14.7, scipy 1.18.0, numpy 2.5.2, pytest 9.1.1. This is scoped native fixture proof, not the entire Macro test suite or hosted CI.

Coverage includes first-bar neutrality, explicit warmup, previous-60-wall-minute history, lagged sample scale, zero-volatility alternatives, gap/phase/day/basis reset, source availability, future-prefix isolation, zero-MAD/floor distinction, current-observation exclusion, clock matching across DST, overlap transparency, contribution accounting and deterministic input ordering.

The synthetic witness constructs identical trade prices/sizes and bars with different preceding quote environments, giving opposite quote-reference signs. This demonstrates non-identifiability from bars alone; it does not estimate real-market classification accuracy. The six-mutant harness is present, but this continuation does **not** claim a fresh native mutation-run result. Its literal `python` interpreter and the benchmark's Linux-specific memory-unit label remain portability limitations after the later repair was denied.

**Withhold:** market pilot, exact LIQN numerical certification, claims of trade-signing accuracy, new production imports, customer signal and ranking/alert/sizing use. Unit-level reference completion is not source-owner integration.

### S2-P1 — source qualification and bounded intake: blocked on exact source evidence

**Owners/paths:** Terminal `ingest/backfill_intraday.py`, `ingest/intraday_capture.py`, `ingest/intraday_qualification.py`, `scripts/qualify_intraday_research.py`; Macro `engine/entry_radar/replay/terminal_minute_observations.py` and its incumbent revision/basis owners. Preserve Terminal #844 / Macro #8623 custody and delivery gates.

**Input:** start with explicitly selected AAPL, MSFT, NVDA and SPY as a benchmark, a current-house-cohort label, exact existing source paths and declared sessions. These are a proposed bounded cohort, not an admitted dataset. Do not reuse a restricted vendor thematic roster.

**Action:** inventory existing files and retained receipts without refresh; run the incumbent qualifier with explicit files, calendar and cutoff. Bind the enterprise entitlement record and selected use. Verify unadjusted monetary basis or reconstructable compatible price/volume factors, not merely `adjusted=false` in a request. Establish source and downstream availability. A real provider probe may occur only through the permitted incumbent client after its source, custody, current permission and any dataset conditions are qualified.

**Acceptance:** complete metadata receipt from section 10, exact local/private object hashes, unchanged inputs, known/unknown coverage denominators and an explicit admission decision. Begin engineering replay only for admitted observations. Missing current capture, basis or history returns NOT_ADMITTED rather than simulated market data.

**Boundary:** the earlier denied four source reads cannot be delegated or repeated as a workaround; they require actual platform-permitted recovery. No new feed, credentials, raw-data publication, persistent daemon or unowned backfill. A denied batch is not permission to alter the existing source-owner path.

### S2-P2 — native licensed replay adapter: specified, not run

**Proposed added file:** `scripts/research/factor_atlas_capital_pressure_pilot.py`, a bounded offline consumer, with `tests/test_factor_atlas_capital_pressure_pilot.py`. Before implementation, recheck exact path custody. Reuse the qualified canonical input selector; do not parse arbitrary chart JSON into newly “trusted” observations.

**Interface:** consume an existing owner-resolved input bundle plus factor membership reference, estimator config and explicit as-of cutoff; emit an in-memory/read-only research result and a caller-selected private evidence artifact. The adapter must not accept an API key, purchase option, daemon mode, publisher switch or permission override.

**Sequence:** record all input hashes; decode the source's true clock; refuse unproven monetary basis; select eligible revisions through the existing owner; run both BVC profiles and the normal/sign baselines; aggregate deterministic constituent contributions; construct separate minute and cumulative series only across declared coverage; build past-only matched-clock references; emit full exclusions and source age.

**Acceptance:** five admitted engineering sessions including available extended-hour evidence; identical repeated replay and earlier-prefix digests; no writes to input stores; no one-minute interpolation from 5m history; no current-data self-normalization; all authority false. This pilot may produce insufficient-history Z results. It does not earn statistical or predictive promotion.

**Rollback:** remove the optional consumer invocation; preserve immutable source/evidence references. Do not delete or rewrite incumbent data to make results cleaner.

### S2-P3 — quote-reference horse race: specified, source/cost gated

**Owners/paths:** reuse `engine/flow_signing.py` primitives and the existing calibration ownership. Add equity-specific tests and a bounded research consumer in the Session 2 pilot, not another options engine or a replacement options signing gate.

**Input:** source-owner-admitted prints and prior quotes with corrected conditions, decimal size, timestamps and price basis. Record event counts and bytes before expansion. Choose quote-age/condition policies before evaluating recovery.

**Acceptance:** gross eligible reconciliation; no future quote match; visible unclassified dollars; split reporting for midpoint/tick fallbacks, TRF, auctions and corrections; day-clustered comparison against bar estimators; measurements at the same windows. A reference-side flag is not a hedge-fund label.

**Ceiling:** never overwrite `data/options_flow/signing_gate.json` with an equity result, reassert rejected options conclusions, purchase tape or admit a quote stream merely because it exists in a catalog. A too-expensive/incomplete broad tape is an acceptable negative result.

### S2-P4 — reusable factor projection and source-quality gate: specified

**Owners/paths:** Session 1's accepted factor/membership read contract; existing `engine/group_flow.py` basket/context owner; canonical Data OS identity and quality ownership. Any later extraction of pure measurement into production must preserve the options and daily-RS contracts and route through their exact current owners.

**Implementation boundary:** build a sparse security-to-factor join and versioned pressure projection, not a second graph, factor registry or intraday store. Add unique-union and duplicate-inclusion disclosure, missing-member state, contribution ranking and concentration. Keep raw dollars separate from market-cap-weighted/dimensionless summaries.

**Acceptance:** many overlapping synthetic baskets yield the same union as a unique-security reference; no duplicate security-minute within a factor; PIT/current-cohort modes cannot mix; membership changes invalidate only the relevant projection/baseline; common source clocks and deterministic corrections remain load-bearing. A missing constituent cannot silently become zero or disappear from coverage.

**Withhold:** an aggregate “market flow” made from overlapping baskets, inference that residual pressure is new capital, and score/rank changes to Prophet or group_flow's existing daily signal semantics.

### S2-P5 — private read consumer and product proof: specified, owner integration gated

**Proposed bounded parser files:** Terminal `terminal/lib/factorAtlasPressure.ts` and its corresponding unit tests, after Session 0/5 freezes the actual authenticated transport. This is a payload parser/formatter, not a new endpoint, publisher or cache authority. Do not squeeze factor analytics into `/api/intraday`, which owns chart bars.

**Inputs:** the exact versioned read contract, entitled private payload and current canonical factor reference. Existing gateway/store owners classify any new artifact family before publication. The actual route/publisher binding is still unresolved and must be selected by those owners, not guessed here.

**Acceptance:** valid/partial/stale/rights-withheld/zero-scale/insufficient-history states; correct factor switching and late-response races; no hidden paid/raw remainder in public previews; method disclosure; signed versus gross labels; visible member/quote coverage. Session 5 owns real authenticated browser journeys, desktop/mobile and design-language compliance.

**Release:** exact-head review and required checks, then normal incumbent deployment and real served-source proof. No production publication from this research PR. Rollback is through the existing feature/route disable mechanism and last-good generation, not a parallel gateway.

### S2-P6 — independent scientific and product acceptance: not delegated

**Owner:** Session 6 and the existing TrialLedger/Evaluation OS; Session 0 integrates the cross-system decision. Supply the immutable report, config, source hashes, all tried profiles, excluded sessions and untouched-evaluation boundary. No new research ledger or worker lifecycle.

Require distinct rulings for formula fidelity, source/capture quality, aggressor-reference accuracy, descriptive usefulness, broad-universe feasibility and forward economic value. Reject unsupported predictive promotion even if the interface is excellent. A qualified descriptive release may be appropriate after source/consumer gates without granting trading authority.

No worker was submitted or STARTed in this session. The observed Executive interface was read-only; no alternate provider launch or unowned process was used. Direct work was retained for principal methodology judgment and the small source-bound reference repair, not represented as delegated execution.

## 15. Delivery evidence, remaining gates and exact next action

**Delivered capability:** original deterministic BVC, robust matched-clock baselines and transparent multi-factor accounting, with a distinct public-outline reconstruction profile and native controlled-fixture proof. The source and receipt at milestone 80231c289e28 are durable. The report specifies the stronger quote/reference architecture, consumer contract, validation program and native packets without rebuilding source owners.

**Not delivered:** a licensed-market measurement run; fresh universe-wide archive/current-capture census; exact LIQN vendor-output parity; quote accuracy results; empirical forward edge; a customer-facing view; source activation, production deployment, or final independent acceptance.

**Unresolved constraints:** four required source reads remain platform-blocked; a raw monetary-basis/receipt-qualified 1m cohort has not been established; the source capture/revision/basis dependencies are not accepted by this report; native benchmark portability repair was denied and is unapplied; hosted checks and independent review do not follow from author tests. The original Linux benchmark belongs to its exact old source only.

**Next useful dependency:** S2-P1's existing-owner source qualification, followed by the bounded offline replay adapter S2-P2. The specific unlock is a real admitted one-minute input bundle with lawful rights, correct price/volume basis, original clocks, coverage and immutable receipts—not another general instruction to start building. Preserve the previously denied effects until actual platform-permitted recovery; do not ask a worker or another account to perform them instead.

The partial mandatory census and unadmitted licensed pilot mean this commission must **not** be marked fully complete. Source-only prototype, report, hosted CI, merge, installed capture, scientific admission and customer acceptance are separate milestones. No timer, watcher, live service, purchase, production publication, rank, alert, sizing or trading authority was created.

## 16. Source register

External primary sources below were accessed during the resumed October 8–9 research window. Source dates are their own dates, not acquisition or market clocks. Public documentation is evidence of vendor/regulatory descriptions, not account-specific permission or actual installed capture. No proprietary LIQN code or restricted membership dataset was used.

### Public methodology and market-data sources

- **P1 — LIQN team disclosure:** https://feedback.liqn.ai/p/flow-calc ; team reply by Jared, September 14. Public mathematical outline and limitations; undisclosed implementation details remain unknown.
- **P2 — Easley, Lopez de Prado and O'Hara (2016):** *Discerning information from trade data*, Journal of Financial Economics 120(2), 269–285. https://www.sciencedirect.com/science/article/pii/S0304405X16000246 ; DOI 10.1016/j.jfineco.2016.01.018.
- **P3 — Chakrabarty, Pascual and Shkilko (2015):** *Evaluating trade classification algorithms: Bulk volume classification versus the tick rule and the Lee-Ready algorithm*, Journal of Financial Markets 25, 52–79. https://www.sciencedirect.com/science/article/pii/S1386418115000415 ; DOI 10.1016/j.finmar.2015.06.001. Equity evidence and benchmark limitations.
- **P4 — Panayides, Shohfi and Smith (2019):** *Bulk Volume Classification and Information Detection*, Journal of Banking & Finance 103, 113–129; author-posted paper/abstract https://papers.ssrn.com/abstract=2503628 . Distinguishes aggressor accuracy from information proxies.
- **P5 — Massive stock trades schema:** https://www.massive.com/docs/rest/stocks/trades-quotes/trades . Trade/venue identity, corrections, decimal size and participant/SIP/TRF timestamps.
- **P6 — Massive stock NBBO schema:** https://www.massive.com/docs/rest/stocks/trades-quotes/quotes . Prior-quote fields, timestamps and sequence semantics.
- **P7 — Massive stock aggregates:** https://www.massive.com/docs/rest/stocks/aggregates/custom-bars . Eligible-trade construction, missing intervals, start timestamps, split declaration, volume and VWAP fields.
- **P8 — Massive capture/availability descriptions:** https://massive.com/knowledge-base/article/market-data-outside-of-normal-hours ; https://massive.com/docs/flat-files/quickstart ; https://massive.com/knowledge-base/categories/trades . Extended-hours coverage, approximate next-day flat-file availability, corrections and fractional-size caveats.
- **P9 — FINRA developer documentation:** https://developer.finra.org/docs . Weekly OTC/ATS publication fields and two-/four-week delay descriptions; dataset versions and actual publication fields control use.
- **P10 — FINRA:** *Short Interest — What It Is, What It Is Not.* https://syndication.finra.org/content/short-interest-what-it-what-it-not . Short-sale trading volume is not a position count.
- **P11 — iShares/BlackRock:** https://www.ishares.com/us/investor-education/etf-education/etf-premiums-and-discounts and https://www.blackrock.com/au/insights/ishares/authorised-participants-and-market-makers . Primary/secondary-market distinction and in-kind creation/redemption mechanics.
- **P12 — SEC Form 13F FAQ:** https://www.sec.gov/rules-regulations/staff-guidance/division-investment-management-frequently-asked-questions/frequently-asked-questions-about-form-13f . Quarter/filing timing and excluded short positions; staff guidance, not a substitute for the rules.
- **P13 — Cloudflare R2 pricing:** https://developers.cloudflare.com/r2/pricing/ , page updated October 1, 2026. Public Standard storage/operation rates, billing rounding and free-tier limits; not Mastermind's bill.

### Immutable incumbent implementation evidence

For I1–I3 and I7–I10, Macro paths resolve at `cdbcd143dcfa419ab0637bc11dd4c80368143e2e`, except the explicitly named new Session 2 source milestone. For I4–I6, Terminal paths resolve at `bacda5dcc30682f9327e037a2d4425bd9714ac3a`.

- **I1:** `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md`; Git blob `3969a9aae918141b51baffbb0e17d8a2ec2485a0`.
- **I2:** `data/massive/capability_manifest.json`; Git blob `921efe6d6e4b8cdc76e88fdde4183fa2a06729fe`.
- **I3:** `engine/flow_signing.py` blob `bc012baeeeedda73d90d15521c63df3853202f11`; `engine/group_flow.py` blob `af0d5f671edded697c03a827976d207bb2b7e7a3`; `research/OPTIONS_FLOW_DATA.md` blob `4b3d00f90360d0c8d4f1d07032db9b0e79131dda`. New reference: `research/factor_atlas/session2/prototype/pressure.py` at milestone `80231c289e284f702e2aba5e69394829c784c1e1`.
- **I4:** `docs/research/INTRADAY_DISLOCATION_R0_DATA_CENSUS_2026-10-02.md`; Git blob `2cadc099a151bebb47e785544ac5908d69ad6132`.
- **I5:** `ingest/backfill_intraday.py` blob `867871829867784a20ed4e760e7f160c1317fd4b`; `terminal/lib/intradayStore.ts` blob `23f5de371899bb761b09d2b0707db775878591eb`.
- **I6:** `ingest/intraday_qualification.py` blob `b66a99027e8d24b4fbb1b81dd1aeb4682030aa6b`; `scripts/qualify_intraday_research.py` blob `df57e08869e848985aa190f40aa16fa4051f378c`.
- **I7:** `research/INTRADAY_LARGE_CAP_TECH_LEADER_PREREG.md`; Git blob `5578c1a351ab0ee7207e8d5cee930d8b138a94bd`.
- **I8:** `research/live_entry_radar/rs_pullback_launch/SOURCE_RETENTION_READER_CONTRACT_2026-10-07.md`; Git blob `4b8e07baf5150759871a4d53e912e01f68bbecc1`. Related source-delivery carriers: Terminal #844 and Macro #8623; this report does not accept their current delivery state.
- **I9:** `research/R2_AND_DELIVERY_PLANE_TRUTH_CENSUS_2026-08.md` and `config/r2_delivery_plane_classification.v1.json`. Their historical deployment observations remain dated evidence, not current ACL proof.
- **I10:** `engine/research_vault/r2_store.py`; Git blob `8aec6ca9ce727146e970f055692edd993c5f3245`. Strict bounded private reads and dedicated configuration boundary.

## 17. Requirement-to-evidence ruler

| Commission requirement | Delivered evidence or exact unresolved boundary |
|---|---|
| Original public LIQN source | P1 recovered; disclosed versus unspecified choices separated |
| Mathematical reconstruction | Section 4 and shared-kernel disclosed-core profile; vendor-output parity unproved |
| Alternative measurements | Sections 5–6; quote source and empirical accuracy not yet admitted |
| Time-of-day abnormality | Section 7 and native baseline fixtures; real historical study not run |
| Factor overlap/contributions | Section 8 and native aggregation fixtures; Session 1 membership admission still required |
| Entitlement/archive/current capture census | Section 10: positive existing rights/probe evidence, dated archive evidence, four denied reads and current-capture unknowns explicit |
| Source clocks and read contract | Sections 7–9; production adapters and consumer are specified, not installed |
| Storage/cadence/cost architecture | Sections 11–12: incumbent owners, transparent assumptions and unverified commercial/capture quantities |
| Leakage-controlled validation | Section 13; nulls preserved, no held market outcomes read |
| Native deterministic first slice | Section 14 S2-P0, 79 native fixture tests; no licensed-market pilot claim |
| First small licensed cohort | S2-P1/S2-P2 blocked until actual basis/clock/coverage-qualified input exists |
| Native packets and continuation | S2-P0–P6 with exact boundaries; no fabricated worker or unattended execution |

## 18. Native cumulative-window continuation

The next safe dependency was executable despite the licensed-source gates: the original reference had minute results and an independently callable baseline, but no cumulative window connecting them. `session2/prototype/window_pressure.py` now computes the existing BVC once at an explicit cutoff and projects many caller-supplied memberships onto an exact supplied-calendar window. No existing pressure formula, ingestion, calendar, registry, source reader, benchmark script or production consumer is changed.

The reducer distinguishes observed gross, full-window gross, estimated net on observed rows, full-window estimated net, directionally usable gross, policy-neutral gross and unestimated gross. Complete numerical estimates may include explicit first-bar/warmup neutrality; that does not turn neutral dollars into classified tape. Missing cells remain missing and withhold full-window totals/baseline references. Known magnitude remains visible when direction is unavailable. Entirely missing input is not complete zero; explicit zero-volume input is distinct.

The existing MatchKey/Reference and matched_baseline implementation remain the normalization path. The join binds actual sorted membership, monetary basis, mode, estimator, calendar version and ET window anchor/phase shape. It conservatively carries availability of contributing pre-window history rather than using build time. Corrected-history mode creates no as-observed baseline reference. A caller-supplied calendar, rights label or timestamp still requires independent owner qualification.

Native test-first evidence: 24 missing-implementation failures, followed by 103 combined passes; composition/witness development then reached **116 passing prototype tests**. The finite full-window witness exercises 21,105 fabricated security-minutes over twenty explicit prior-session fixtures and one target, from 04:00 through 09:35 ET. Gross abnormality matches an independent scale calculation; reversed replay and appended future rows/revisions leave the earlier result identical. Tests also cover DST, early close, true roster changes despite unchanged version labels, source availability, one BVC evaluation for overlapping factors and independent partial-factor behavior.

Five deliberate faults in the new reducer were all rejected: treating missing cells as complete, admitting partial windows to a baseline, hiding overlap, dropping actual roster membership from identity, and replacing source availability with build cutoff. This is a new-window-only mutation proof; it neither edits nor reruns the previously blocked benchmark/interpreter repair. The original pressure source and all three denied-edit paths remain byte-identical.

Proof: `session2/evidence/native_window_tests.json`, `window_pipeline.json` and `window_mutations.json`; detailed contract: `session2/CUMULATIVE_WINDOW_CONTRACT.md`. This strengthens S2-P0 and proves the synthetic calculation path required by S2-P2; it is **not** a licensed S2-P2 market replay, current-capture qualification, independent review, hosted-suite result or customer release. The existing source, rights, custody, blocked-action and consumer gates remain unchanged.

## 19. Native S2-P3 quote-reference estimator — bounded independent continuation

**Status:** original pure trade/quote reference prototype and controlled-fixture tests exist in `session2/prototype/quote_reference.py` and `test_quote_reference.py`. This is a source-independent research reference, not the canonical equity market-data adapter, an exchange aggressor flag, actual institutional allocation flow, qualified market-data coverage, or a customer-facing measure. The incumbent production signing/calibration owner remains `engine/flow_signing.py`; no code was changed there.

The prototype takes owner-supplied print and NBBO observations with unadjusted monetary basis, declared condition/revision/rights identity, SIP event timestamps and actual source-availability timestamps in **integer UTC nanoseconds**. Before admitting a quote reference it requires the same security, session, phase and basis, a valid positive uncrossed two-sided NBBO, a strictly earlier quote source clock, arrival by the research information cutoff and a research-policy maximum quote age. An equal-SIP-timestamp quote is **ambiguous** and blocks fallback to an older quote; the latest invalid or stale quote cannot be replaced by an older valid quote. Missing/late quotes remain unknown. Midpoint ties are unknown by default; a separately labeled explicit tick fallback requires a strictly earlier eligible print and a nonzero price change, without carried zero-tick signs. Quote and trade source sequence numbers are never conflated.

The default **one-second quote age is an experimental policy**, not a validated cutoff. A 0.1-second/5-second sensitivity and conditions/venue/auction stratification remain prerequisites for any actual comparison. TRF trades remain eligible but unsigned unless the incumbent source owner proves suitable execution-versus-reporting clock alignment; no public-print source identifies beneficial owners. Excluded conditions and canceled/unresolved print revisions remain separate diagnostic gross, never automatically counted as eligible activity.

For eligible observed prints, the prototype accounts for inferred quote-buyer dollars B, inferred quote-seller dollars S and unsigned eligible dollars U:

    eligible_gross = B + S + U
    covered_signed_net = B - S
    quote_classified_share = (B + S) / eligible_gross  [nullable when zero]
    accounting_interval_on_observed_eligible_tape = [B - S - U, B - S + U]

This interval is only an **accounting bound on observed, policy-eligible prints**. It does not bound missing tape, source exclusions, unseen participants, true institutional holdings or trading profit. `observed_gross` includes separately marked excluded/unqualified prints for diagnostics, and is not a publishable eligible-turnover denominator. `corrected_history` never manufactures a historical first-observed clock; `as_observed` uses the latest actual eligible trade/quote receipt as each classified row's known-at clock.

The initial test-first slice deliberately failed before implementation and then passed the full scoped prototype suite after source implementation. A second adversarial test-first pass caught silent loss of high-precision fractional notional, incorrect high-precision midpoint signing and uncontrolled exponent handling; the corrected kernel uses a **local**, not process-global, 256-digit decimal context with bounded input exponents. It was followed by **164 passing native scoped tests** including existing BVC/cumulative/baseline fixtures, six ordinary-quote comparisons against the incumbent `engine.flow_signing.quote_rule_sign` primitive, source cutoff, stale/invalid/equal-time quotes, TRF, corrections, unknown gross and replay order. Neither author tests nor parity on ordinary prices establish empirical trade-signing accuracy or production rights.

The next independently actionable experiment is a **same-population BVC-versus-quote comparison** with observable denominators and declared sampling boundaries; it must report quote coverage and matched eligible print/bar notional before computing classification disagreement. Its construction may be fixture-tested without accessing a real feed, but actual market calibration remains **NOT_ADMITTED** until S2-P1 supplies an exact lawful source/reader/basis bundle. The most relevant external schema fields are documented by Massive's stock trades, quotes and correction documentation (https://www.massive.com/docs/rest/stocks/trades-quotes/trades ; https://www.massive.com/docs/rest/stocks/trades-quotes/quotes ; https://massive.com/knowledge-base/categories/trades ). These public descriptions are not evidence of installed acquisition or per-feed permissions.

## 20. Native S2-P3 same-minute quote/BVC comparison — Extra High continuation

**Research-only software capability added:** `session2/prototype/quote_calibration.py` consumes an existing BVC `PressurePoint` and the new finite `TapeResult` using the same declared source mode, security identity, ET session/phase, complete true-UTC minute, exact monetary-basis version and explicit cutoff. The quote reference carries actual source/quote known-at receipts from its own finite source-supplied input. It never independently authenticates a source string, licenses data or selects a correction vintage.

For eligible matched prints, the comparison retains inferred buy/sell/unknown dollars separately. It measures quote-covered signed fraction `(B-S)/(B+S)` only on the actually classified subset and compares it with BVC's normalized estimated `net/gross` ratio. A ratio disagreement is returned only if the quote-classified share meets the selected research floor (default 90%), the close-based bar-notional diagnostic is within the selected tolerance (default 5%) and BVC direction is usable. The method is labeled **proxy disagreement, not tape aggressor accuracy**. Partially classified or mismatched samples return explicit withheld statuses. The signed unknown-dollar range is only an accounting bound within observed eligible prints; no hedge-fund, allocation, holdings, trade or forward-prediction claim is admitted.

The previously published quote reference now carries immutable **monetary basis, print rights and quote rights reference fields** to each classified or unknown print rather than discarding them. This closes a discovered cross-source mismatch: an unadjusted action-v2 sample must never silently be compared with an incompatible BVC basis. Rights references are still evidence strings, not independent authorization.

A second discovered replay defect was corrected: an unrelated later print previously changed the comparison's input digest, even though the matched earlier minute was unchanged. The digest now binds the matched minute only, plus its BVC record, registered policy, method and decision cutoff. Earlier valid results are therefore invariant to unrelated later prints in the supplied tape, while contradictory source accounting is still refused. All customer, publication and trading authority remains false.

The implementation was developed test-first: original missing-comparator failure; a fixture module identity correction and deliberate numeric-source precision repair; two explicit monetary-basis/source-rights failures; an original future-input-digest failure. The current native scoped prototype suite passes **184 tests** on controlled fixtures, including the preceding BVC/cumulative/quote modules. This is not a source-admitted tape run, empirical signing result, full Macro regression, independent review or production acceptance.

A material public-source finding sharpens the validation gate: Massive's stock aggregate volume and OHLC eligibility rules depend on sale conditions and can differ within one trade. Matching close×volume dollars approximately to exact print notional therefore cannot certify identical eligible transaction populations. Its September 22, 2026 Tape B historical metadata correction also complicates older SPY/IWM venue/tape labels. The source owner must qualify the raw condition map, corrected source vintage and relevant tape identifiers before any market-comparison claim. See `session2/QUOTE_CALIBRATION_PROTOCOL.md` and https://www.massive.com/blog/understanding-trade-eligibility ; https://www.massive.com/changelog .

The first real cohort remains S2-P1 **NOT_ADMITTED**. The optional and independently testable S2-P3 research comparator now exists, but no provider fetch, flat-file backfill, separate market-data authority, calibrated accuracy assertion or public release was performed. The authorized next data action remains an incumbent-owner AAPL/MSFT/NVDA + SPY minute/trade/quote source-quality receipt; earlier platform denials and independent Terminal/Macro source-delivery holds have not been bypassed.


## 21. Native S2-P1 source-evidence preflight — bounded independent implementation

**The actual licensed-market pilot remains NOT_ADMITTED.** The incumbent retained-minute source reader describes precise native source/reader clocks and capture role but deliberately returns `basis_id=null`, with `TERMINAL_BASIS_UNPROVEN`. A v3 `research_unadjusted` capture request, response page declaration `FALSE`, sealed hashes and an owner-read receipt are necessary provenance, **not sufficient evidence** of stable raw/unadjusted price × volume basis or corporate-action vintage. Existing Terminal #844 / Macro #8623 remain Draft and separately owned. No live provider call, new feed, 5m-to-1m interpolation, source store edit or basis override has been performed.

The research-only `session2/prototype/source_preflight.py` now implements the bounded S2-P1 *metadata census* for the proposed explicit AAPL/MSFT/NVDA + SPY pilot. It accepts an owner-supplied calendar (no generated exceptional session), one-minute slot claims and the actual selected source/reader/rights/basis/correction **evidence references**. Each source candidate records source response nanoseconds, source object/prefix hash, exact read-completion nanoseconds, owner revision-selection receipt, acquisition role, request and response adjustment declarations, monetary basis plus canonical action-vintage and volume-unit receipts, rights/dataset-use reference and explicit present/zero/missing state. It checks slot identity, temporal ordering, cutoff causality, SHA-256 shape, duplicate selected revisions, cross-minute listing/basis identity stability and full expected-versus-represented-versus-unknown denominators. Contradictory receipts and mismatched owner calendars are refused; future out-of-scope appended rows do not affect an earlier census.

**The interface is intentionally incapable of admitting a market dataset.** Even when all 12 of 12 invented metadata slots are complete, `status='NOT_ADMITTED'`, `external_owner_admission_required=True`, `may_execute_market_pilot=False`, and all rank/alert/size/trade/publish permissions stay false. Each self-supplied hash or rights/basis reference is unauthenticated input, not source-owner approval, a cryptographic signature, proof of actual retained bytes, or release authority. The existing owner must independently qualify actual custody, source revision selection, corporate actions, calendar, rights and intended research use.

Test-first evidence: absent implementation explicitly failed; the initial preflight was green for 35 tests. Two new version-drift falsifiers then failed as expected; after adding per-security listing/basis consistency checks, a conservative reader-nanosecond-to-microsecond cutoff falsifier also failed and was repaired; the full scoped prototype suite reached **226/226 native passing synthetic tests**. The independent fixed-data witness returns `NOT_ADMITTED` even for complete declared metadata and separately exposes 12 missing source slots, missing monetary basis and after-cutoff reader receipts. This is **software/metadata coverage proof only**, not a market-data census, source installation proof, trade-signing result or empirical return study.

Artifacts: `session2/SOURCE_INTAKE_PREFLIGHT.md`, `prototype/source_preflight.py`, `prototype/test_source_preflight.py`, `evidence/source_intake_witness.json`. The report's existing S2-P2 gate remains unchanged: only the incumbent source owner may certify a truly admissible AAPL/MSFT/NVDA + SPY input bundle; the Factor Atlas research code is not a substitute source admission plane. Earlier platform-denied source reads, benchmark repair and current-base comparison remain untouched.


**Bounded current local source census:** The observed M2 Studio Terminal `charting-app` checkout `81221cb15345118d0796fabaa7c47476350dc614` declares default `terminal/public/data` and, at that path, the four AAPL/MSFT/NVDA/SPY 1m, 5m and 1h candidate files and the containing intraday directory were absent. Its existing manifest (SHA-256 `b66f89a606ac5a374d993e2ced21f5332d9312ee069d40ed8ce4f55b73ecb6e3`, `as_of: 2026-06-26`) listed those tickers but **not admitted minute capture**. Evidence: `session2/evidence/local_terminal_default_path_census.json`. This is expressly **not a production/fleet-wide absence finding**: service `TERMINAL_DATA_DIR` overrides, other hosts and other data stores were not established. No owner-owned files or feed were changed; S2-P1 remains NOT_ADMITTED.


## 22. Hosted-CI ownership gap and focused research-test registration

**Current exact tested research source at decision boundary:** `c7b28ff2bead20487dcb6f90a6d20f89086be9d2`, [Draft/HOLD PR #8677](https://github.com/mastermindx-market-intelligence/macro/pull/8677). Its `fences` workflow `37887224633` concluded SUCCESS. Full CI `37887224764` concluded FAILURE. In CI, 11 of 12 `ci-pack-*` jobs succeeded; `contract-delta` job `113680066249` and `ci-pack-0` job `113680332943` identified the same concrete missing suite-run ownership. The contract-delta log reported **eight introduced, zero inherited** uncovered pytest suites relative to its recorded base `7bd0a9830735`. Its three named job-budget probes all equaled their base results, within their existing limits. No new scientific calculation failure was established by those logs.

The eight unrun suites are `test_pressure.py`, `test_disclosed_profile.py`, `test_witnesses.py`, `test_window_pressure.py`, `test_window_pipeline.py`, `test_quote_reference.py`, `test_quote_calibration.py` and `test_source_preflight.py`, all under `research/factor_atlas/session2/prototype/`. The local 226-pass result had not satisfied the established rule requiring actual GitHub Actions `run:` coverage.

**Chosen repair:** register the exact eight test paths in `.github/workflows/factor-atlas-reference.yml`, an additive narrow `pull_request` GitHub Actions job triggered by `research/factor_atlas/**` or its own workflow file. It uses `contents: read`, Python 3.12, the existing version-locked research requirements plus pandas (the incumbent signing primitive imports pandas), and no secrets, source provider, cache, historical input, upload, publisher, extra runner, service or external platform. There is no new CI control plane; GitHub Actions continues as the existing code/validation owner. The pre-existing operations-only `factor_ops.yml` backfill job, global `.github/ci/legacy-jobs.yml`, `.github/workflows/ci.yml`, waivers and unrun baseline remain unchanged; there is **no waiver** of the eight previously dark suites.

Before publication the workflow was locally parsed by PyYAML and its eight explicitly named run-step paths were checked exactly against the eight test files tracked at the PR head; **8/8 matched**. Its exact test command passed **226/226 native tests** on local M2 Python **3.12** (pytest 9.1.1, scipy 1.18.0, numpy 2.5.1, pandas 3.0.5). Hosted GitHub uses the pinned requirements versions; this local test does **not** establish hosted execution, hosted green, current-base semantic compatibility, deployment, source admission or production acceptance. The new workflow must be observed after the source push and any actual failure must be diagnosed at its exact head; one cannot infer all green from YAML syntax or a local author run.

CI registration is critical engineering infrastructure for the **named Factor Atlas scientific reference**, not a release gate bypass. Source S2-P1 remains `NOT_ADMITTED`, and the specific previously denied source reads, benchmark repair and current-main fetch/target comparison are still not retried. The original PR stays **Draft/HOLD** until real current-head check results, exact-head independent review and permitted release admission. Evidence is in `session2/evidence/ci_registration_preflight.json` and the original GitHub Actions job logs.

**CI trigger closure:** A targeted static import census found that `test_quote_reference.py`
imports `engine.flow_signing.quote_rule_sign` for six incumbent-method
parity tests. The new Factor Atlas research-workflow `pull_request.paths`
therefore includes **`engine/flow_signing.py`** in addition to its own
workflow and `research/factor_atlas/**`. A change to the shared primitive
alone can no longer leave those reference regression tests untriggered.
No existing production signing code, global CI job, test waiver or
provider source was modified. The trigger/case paths were parsed locally
and match exactly eight tracked suites; the same Python 3.12 226-pass
recipe remains the local reference. Hosted checks are still distinct.

## 23. Exact hosted CI outcomes and narrowed trigger closure

Previous PR head `a8b79bd03cd839bbc9b330542c4b932d31dcbad5` completed its
[dedicated native regression workflow](https://github.com/mastermindx-market-intelligence/macro/actions/runs/37902125741)
**SUCCESS with 226 tests passing in hosted Python 3.12** and
[fences](https://github.com/mastermindx-market-intelligence/macro/actions/runs/37902125680)
SUCCESS. Full [CI](https://github.com/mastermindx-market-intelligence/macro/actions/runs/37902126432)
failed on two *introduced trigger-path coverage* gaps, not any of
those 226 native tests. The repo's trigger-closure rule detected literal
reader and entitlement-contract dependencies of
`test_source_preflight.py` that could not independently trigger its
own research workflow.

The additive, narrow `.github/workflows/factor-atlas-reference.yml`
now includes exact trigger paths
`engine/entry_radar/replay/terminal_minute_observations.py` and
`research/licenses/MASSIVE_ENTITLEMENT_RECORD.md` in addition to
the previously installed Factor Atlas and `engine/flow_signing.py`
trigger paths. All eight suites are still executed together under a
read-only checkout; no CI waiver or global workflow edit was needed.
The hosted fixture result belongs to its earlier exact head;
**this source-patch revision needs its own GitHub check result**.

Other full-CI failures include ticker-news QBUS's
`tests/test_build_qbus_news_universe.py` and Intelligence Hub's
`tests/test_intelligence_hub_glance_copy.py`. Neither is part of the
Factor Atlas source edits. Their base/inheritance status was not
verified and must be handled by their current owners rather than
loosening Factor Atlas's science or release gates. Prior explicitly
denied source-read, benchmark repair and current-base comparison
remain untouched. A local connector termination was reconciled
against the original file before any next source effect.

The licensed equity minute/trade/quote cohort is still
**NOT_ADMITTED**, regardless of the fixture green results. This
phase only closes a tested hosted CI integration dependency.


## 24. S2-P4 research-only factor read contract — bounded independent continuation

The source-independent portion of S2-P4 now has an executable, strictly bounded **structural research candidate**. The JSON Schema at `session2/contracts/capital_pressure_read_v1_candidate.schema.json`, an explicit fabricated specimen at `session2/evidence/capital_pressure_read_synthetic.json`, and a deterministic adversarial test suite define an exchange format for factor pressure, coverage, warmup, unusual matched-clock activity, contribution concentration, roster identity and cross-factor overlap. This is *not* a new factor registry, data store, API contract authority, product endpoint, or authentication system: Session 1's factor and identity owners and Session 5's accepted private consumer transport remain the owners of those decisions.

The schema encodes the previously proposed `factor_atlas.capital_pressure.read.v1` identity with structural validation that is deliberately **incapable of positive source admission or customer publication**. Its source class is `MODEL_INFERRED_BAR_PROXY`, `source_quality` is always `NOT_ADMITTED`, all five rank/alert/size/trade/publish flags are FALSE, market admission and customer publication are FALSE, `confidence` and `predicted_return` remain null, and sum-of-overlapping-factors can never be labeled additive market flow. Partial windows have null full gross, full net, full inferred buy/sell and full ratio; numeric zero retains its distinct explicit state. Historical baseline status preserves insufficient sample, low coverage, zero-scale and neutral/partial withholding rather than manufacturing finite Z. Monetary and coverage ranges, fixed schema key sets and resource identities are enforced structurally.

On an M2 local Python 3.12 runtime, the candidate schema validated **one** synthetic snapshot and rejected **15** independently altered invalid snapshots. A separately committed-only-schema test suite adds **24** tests (including twenty-one invalid payload cases, nonfinite JSON refusal and negative authority assertions). Its exact nine-suite invocation, comprising the 226 accepted BVC/window/quote/source tests plus the 24 schema cases, passed **250/250** locally and is registered in the existing `factor-atlas-reference` GitHub Actions workflow. The requirements file now pins `jsonschema==4.26.0`; no new workflow lifecycle or release override is created. The new head needs its *own* hosted result; local Python 3.12 tests do not establish GitHub/production acceptance.

**Critical distinction:** a separate uncommitted read-model calculation experiment exposed four unresolved integrity failures despite its initial successful simple fixtures. They concern constituent neutral/classified gross reconciliation, factor aggregate-to-contribution reconciliation, stale-roster membership-key binding and impossible pre-close source-known timestamps. An attempt to patch those specific functions was explicitly stopped by platform safety checks before dispatch, and the same original file was read back unchanged. Neither the experimental module nor its failing tests is in this PR's publish set or advertised as accepted functionality. The validated schema is a **shape-only candidate**; it cannot prove arithmetic, data rights, true source observation time, point-in-time membership, calibration or institutional ownership. The denied code edit was not retried via a different tool/account/carrier.

The source/right/basis/clock-qualified real one-minute cohort is still **NOT_ADMITTED**. The next consumer action, only with its original owner and positive admission, is to bind the accepted factor identity, hardened native integrity calculation and retained-source receipts into the authenticated private read model. No source order, production ranking/alert, market-pilot execution, customer publication or deployment was performed. Details: `session2/READ_CONTRACT_CANDIDATE.md`, `session2/evidence/capital_pressure_contract_validation.json`, and the narrowed GitHub workflow.


## 25. S2-P3 day-clustered quote/BVC falsifier — independently executable research slice

A new **source-independent day-clustered study** at `session2/prototype/quote_study.py` composes the already accepted, per-minute `quote_calibration.MinuteComparison` reference without claiming that either BVC or midpoint-signing is observed institutional trading truth. The caller supplies an explicit set of security/minute/session/phase slots from its incumbent calendar and population owner; missing slots remain missing and are not represented as executed zero-volume prints. Every observed result must match a specified slot, cutoff, research mode, policy identity and roster identity; duplicate observations and incompatible sessions/cohort policies refuse rather than silently pooling measurements.

The study distinguishes eligible quote notional, classified quote notional and unknown eligible dollars; keeps incompleteness and directional unavailability separate; and emits an absolute ratio discrepancy only for a prior comparator state that was actually comparable. It refuses negative/nonfinite notionals, a quote classified+unknown accounting mismatch, inconsistent signed-pressure ratios and any input attempting to grant customer/trading authority. It requires at least **three distinct comparable session clusters**, so hundreds of correlated minutes from one day cannot make the day-level mean appear independently measured. When enough days exist, the reported descriptive result is the equal-weight average of daily mean proxy discrepancies. A simple leave-one-day-out minimum/maximum shows **sample sensitivity**, not a confidence interval, calibrated expected return or significance test.

Test-first evidence: one missing-implementation failure, then a module-constant correction and one test fixture's cutoff-order repair, followed by **25 passing tests** and **9 further adversarial cases**, for **34/34 native study tests**. The ten-suite focused test invocation including the preceding 250 BVC/window/quote/source/read-schema tests passed **284/284 locally** on M2 Python 3.12. The same GitHub Actions research workflow now explicitly names ten suites; the new head must receive an independent hosted conclusion. A finite fabricated three-day versus empty-slot witness is recorded at `session2/evidence/quote_day_cluster_synthetic.json`; test/source/log identities are bound in `session2/evidence/native_quote_study_tests.json`.

**Scientific limits:** these fixtures are synthetic, not actual market prints, genuine signed trade truth, future-return outcomes or an independent institutional activity label. The study deliberately returns `source_receipts_verified=false`, `rights_verified=false`, `is_statistical_accuracy_study=false`, `is_confidence_interval=false`, `market_pilot_admitted=false`, `customer_publishable=false` and all authority flags false. No separate factor registry, options platform, data collector, publisher or experimental results database was introduced. The old explicitly denied four source reads, benchmark patch and fresh-main comparison, and the newer blocked read-model integrity patch remain untouched. The actual AAPL/MSFT/NVDA + SPY source-admission gate and the existing Terminal/Macro source custody still block licensed empirical S2-P2/S2-P3 evaluation. Exact protocol: `session2/QUOTE_STUDY_PROTOCOL.md`.


## 26. Paired OOS pressure-vs-price-controls falsifier — research-only S2-P6 prerequisite

The next safe, independently testable requirement is **not** a new flow score: it is a causal way to test whether pressure adds forecasting value beyond its own price/volume inputs. The existing report correctly states that BVC is a deterministic transform of historical bar prices and volume, and a favorable comparison against a weak linear close predictor is not new information. The executable `session2/prototype/pressure_oos.py` now assesses *externally supplied, allegedly pre-frozen* model-pair forecasts for a **pre-registered next-30-minute residual-return target in basis points**, without selecting a model, downloading observations, rebuilding data or producing any trade.

The `EvaluationPlan` freezes factor, point-in-time roster and population, 30-minute target, model/feature-basis references, training end, holdout start/end and an embargo at least as long as the outcome horizon. A study must retain **at least twenty independently dated holdout sessions** and **80% available mature outcome labels** before even reporting the descriptive paired loss. Each `PairedForecast` is paired against an explicit factor/day/decision clock. Required feature and both forecast receipts must be known at or before the decision and the predictions cannot predate their declared feature input. Outcome event end must be decision+1800s, with a real outcome-known-at time later than that end. Missing or late outcomes remain unavailable, never imputed with zero or backdated. Same-minute duplicates, unexpected or out-of-holdout slots, non-PIT roster changes, inconsistent source basis, mixed target identities, nonfinite predictions and missing outcome receipt contradictions fail closed.

For matched mature rows, the method records squared forecast loss in bps² for both control and pressure-augmented model. It first averages **within each session**, then equally weights sessions, so a day with hundreds of overlapping 30-minute horizons cannot masquerade as hundreds of independent samples. The primary descriptive difference is `MSE_control - MSE_pressure`; *negative* results remain visible. A zero-MSE control produces a null relative improvement instead of an undefined/infinite one. A leave-one-day-out range is **not** a statistical confidence interval, forecasting significance estimate or trading-value score. Authenticating equal-capacity nonlinear price/turnover controls, model freeze, initial features, residualization, outcome labels, point-in-time roster and embargo history is the obligation of the incumbent source/model/outcome owners and independent scientific review. Mere source/reference strings or a dataset entitlement do not prove these facts.

The test-first run initially failed on a missing implementation, then caught input-known-before-feature and absent-label inconsistencies and enforced a fail-closed finite forecast contract. The new OOS suite passes **41 native tests**. The combined eleven-suite research regression (BVC/cumulative/quote reference/study/source-preflight/strict schema/OOS study) passes **325/325 locally** on M2 Python 3.12. Its finite witness deliberately fabricates twenty sessions with both a favorable and unfavorable model-pair outcome, plus insufficient-history and late-label outcomes. Those fabricated numbers are **not actual market predictions, hedge-fund flows or evidence of gain**. All source, rights, statistical accuracy, customer publication, ranking, alert, sizing and trading authority remains FALSE. The prior explicitly denied four source reads, benchmark repair, fresh-main target compare and separate read-model integrity patch are untouched; the read-model experiment with four red integrity checks remains uncommitted and excluded from accepted evidence.

Artifacts: `session2/OOS_PRESSURE_INCREMENTAL_TEST_PROTOCOL.md`, `prototype/pressure_oos.py`, `prototype/test_pressure_oos.py`, `evidence/pressure_oos_synthetic_trial.json` and the native exact-source receipt. The existing narrow GitHub Actions workflow now names eleven suites; its hosted run and current-source compatibility remain *separate* from the author's test results. The **source-qualified AAPL/MSFT/NVDA + SPY** actual minute/trade/quote and outcome population remains S2-P1 **NOT_ADMITTED**, so an empirical OOS claim cannot begin.


## 27. Native source-shaped S2-P2 bridge — only synthetic preview, never source admission

The previously absent step between **source-owner 1m intake metadata** and the independent cumulative BVC/window reducer is now an executable research-only `session2/prototype/intake_bridge.py` module. It joins incumbent `source_preflight.MinuteClaim`, exact four-name expected source-clock/calendar/selected-revision accounting, and accepted `pressure.Bar` and `window_pressure.measure_windows` geometry. This is not a second source reader, broker/quote collector, corporate-action selector, PIT roster authority, market-rights check, API or publishing pipeline. The only permitted computed preview uses the explicit `SYNTHETIC_FIXTURE` input class; the `OWNER_UNVERIFIED` class returns a no-calculation `OWNER_ADMISSION_REQUIRED` status even when every claimant-controlled hash, rights and monetary-basis label is structurally populated.

Availability is conservatively converted from actual purported source+reader nanosecond receipts to the next whole UTC second before passing bars to the existing BVC kernel. A cutoff after the raw nanosecond receipt but before the conservatively ceiled second becomes `CUTOFF_PRECISION_WITHHELD`, not an artificial earlier observation. A missing minute, source/reader receipt, real monetary basis, action vintage, listing, dataset-use reference or explicitly selected revision withholds the whole preview; its exact preflight exceptions and denominator remain available for source-owner diagnosis. Explicit zero-volume rows stay distinct from absent volume; an in-scope unselected revision collision is refused. A later out-of-scope suffix does not alter earlier evidence or simulated calculations.

The research fixture contains three fabricated minute slots for each of AAPL/MSFT/NVDA/SPY under one unverified test calendar and two source-independent static factors. It deterministically returns synthetic full-gross activity **$3,030 (ETF)** and **$9,090 (three-name tech basket)** with all authority false. These amounts are **invented for software tests**, not actual four-stock capital movement, estimated hedge-fund flow, new market facts or trading signals. The independent controlled witness contrasts this with a completely missing 12-slot grid, a complete but unverified input class that is deliberately uncomputed, and a subsecond information-cutoff that withholds future-rounded source receipts. It produces `status=NOT_ADMITTED` and `market_pilot_admitted=false` in every case. No input parameter can turn a claimant-supplied hash, listing or rights label into source/permission admission.

TDD first showed missing implementation, then passed 20 core cases plus 12 source-rights/clock/conflict/zero/future falsifiers for **32/32 source-bridge tests**. The full **12-suite research test command passed 357/357 locally** on M2 Python 3.12, with the source bridge registered in the existing read-only dedicated GitHub Actions workflow. The exact executable source, fixture, proof receipt, expected conditions and limits are documented at `session2/SOURCE_BRIDGE_PROTOCOL.md` and `evidence/source_bridge_synthetic_witness.json`. This validates internal software geometry only. The *real* S2-P1/2 cohort remains NOT_ADMITTED until the original Terminal/Macro source/basis/revision owners produce and admit genuine selected retained one-minute input, source and reader clocks, source-corrected volume/basis and dataset-specific rights. There was no provider API, raw market capture, release action or production consumer use. The original platform-denied source reads, benchmark/compatibility edits and later blocked S2-P4 read-model integrity patch are unaffected and not retried.

The hosted CI status at the previous accepted head `cb622ddaad4005113285990321373271fb0e8ac7` is: dedicated Factor Atlas research workflow and repository fences SUCCESS; full Macro CI FAILURE from the unrelated `washout-turn-organ` live-quote display-board tests (`test_build_live_quotes.py`, 320/320 board cap and uncovered eight tickers). The current source owner of that surface must repair it independently. The new source-bridge head needs its *own* verified hosted checks, and neither that isolated red CI nor this new synthetic preview provides authority to merge, activate, publish or trade.


## 28. Exact held-reader interoperability and source-basis refusal — owner-led integration frontier

The Factor Atlas S2-P2 bridge now includes **source-attributed compatibility evidence** against the existing, separately held Macro [PR #8623](https://github.com/mastermindx-market-intelligence/macro/pull/8623) retained-minute decoder, head `6cff6ef8aba28dc7ee6f7779a81ef18856d9b3b6`, file blob `95b53bba32eb2ebd6e7804052c31271bf1b65eed`. That reader's public `decode_terminal_minute_observations` returns a per-minute event start/end, original capture/page/row source digest, explicitly enrolled owner reader-completion and first-seen clock, decoded price/optional volume, capture role, source revision identity and self-consistent row checksum. It **deliberately sets `basis_id:null` and `TERMINAL_BASIS_UNPROVEN` on every row**; it also neither selects competing revisions nor grants market or trading admission. This exact source-owner negative contract is load-bearing, not a workaround to fetch an unproven live dataset.

The new pure `session2/prototype/owner_reader_abi.py` interprets the **held reader's already-decoded owner-shaped mapping**, never raw source bytes or provider traffic. It validates the expected v1 decoder schema, closed authority, source response and actual read-completion nanosecond stamps, reader's *ceil-to-microsecond* `known_at` convention, true UTC 1m event identity under a caller-supplied calendar, capture SHA/page/row reference and self-consistent canonical row checksum, explicit zero versus missing/null volume and selected source revision label. It passes the constrained candidate into the existing `source_preflight` logic **without inventing missing proofs**: PIT listing identity, monetary basis/action-vintage, selected revision receipt, dataset-specific rights and original source owner admission remain NULL. Every realistic v1 candidate returns `OWNER_BASIS_UNPROVEN` or `OWNER_READER_UNAVAILABLE`, `status=NOT_ADMITTED`, all publication/trading flags FALSE and **no calculated WindowPressure or observed capital flow**. A syntactically correct checksum is not cryptographic source custody, actual exchange entitlement or a verified source vintage.

The exact ABI test suite comprises **27 fabricated/negative conformance cases**, including all 12 expected minute rows still basis-unproven, unavailable and missing volume, explicit zero, late source-read cutoff, contradictory reader/source order, forged source identity, adjusted capture roles, malformed checksum/UTC clocks, duplicate selected revisions and authority-claim refusals. The focused **13-suite research regression passes 384/384 tests locally** on M2 Python 3.12; the same existing read-only GitHub Actions fixture workflow now names all thirteen tests. Its own new-head hosted CI remains to be observed separately. The synthetic owner-shaped witness has 12/12 rows but `metadata_complete=false`, no admitted data and no source/rights/roster proof; evidence: `session2/evidence/owner_reader_abi_synthetic_witness.json`, full contract `session2/OWNER_READER_ABI_CONFORMANCE.md`.

This interoperability phase is independent of the earlier platform-denied four source reads, benchmark update and main-base comparison, and does not repair, clone or route around the separately denied downstream S2-P4 read-model integrity edit. Those denials and the two four-red uncommitted WIP files remain held/excluded. The original Terminal #844 and Macro #8623 source PRs remain Draft/unmerged. The source-owner admission gate has a *precise* remaining condition: present a genuine selected minute bundle with binding corporate-action/volume basis, canonical PIT identity, correction/revision choice, original source and reader receipts and effective rights for AAPL/MSFT/NVDA+SPY, then proceed through the original owner to an independently accepted live/offline consumer. No self-issued research permit or UI publication is available from the ABI check.


## 29. Held-reader ABI fingerprint and structural OHLC integrity hardening — accepted research lane

A current-head adversarial replay of the accepted `owner_reader_abi.py` demonstrated an **actual evidence-fingerprint failure**, independent of any prior denied operation. A candidate decoded `close` or positive `volume` could change with a correspondingly recomputed self-consistent row SHA-256 while the factor ABI `evidence_digest` remained identical, because the earlier fingerprint reflected only metadata-preflight receipts and not the decoded row's content binding. A second defect let an impossible high/low/open/close combination pass the ABI's structural checks. Neither defect was a signal-quality claim, actual market measurement or source-authority grant; both affected the correctness and detectability of the future reader/consumer integration seam.

The source ABI now verifies finite positive OHLC and the invariant `low <= min(open,close) <= max(open,close) <= high`. It also includes an **order-independent sequence of exact canonical decoded row receipt hashes** alongside the existing source preflight identity in its own `evidence_digest`. Thus a source-like row with changed quote basis, price/volume or included provenance cannot silently share the earlier ABI evidence identity, while reordering identical observations does not change the result. These SHA receipts detect local inconsistency only; they do not authenticate the actual provider, source capture, terms, entitlement or beneficial ownership. The source's original `TERMINAL_BASIS_UNPROVEN`, null `basis_id`, missing selected-revision/rights/PIT proof, `OWNER_BASIS_UNPROVEN` outcome and all no-trade/no-publish authority flags are preserved exactly.

Test-first proof: **eight failing integrity cases** initially reproduced fingerprint collisions and invalid OHLC acceptance, followed by 35/35 ABI tests passing and **392/392** total local 13-suite tests passing on M2 Python 3.12. A new [bounded synthetic evidence witness](session2/evidence/owner_reader_abi_integrity_witness.json) records three changed-row identity cases and four malformed OHLC refusals; no source was fetched. Existing [Terminal #844](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/844#issuecomment-6107460659) and [Macro #8623](https://github.com/mastermindx-market-intelligence/macro/pull/8623#issuecomment-6107464007) original owner PRs now contain scoped Factor Atlas source-admission requests, but remain independently DRAFT/unmerged. Executive OS remains `readonly` and exposes no addressable session target, so no Fabric worker or source-write custody transfer was claimed. The prior explicitly denied four source-file reads, benchmark edit, current-main source comparison, and the separate blocked read-model integrity patch were not retried or replicated.

This hardening improves reproducibility of the source-facing reference without unlocking the actual S2-P1/S2-P2 AAPL/MSFT/NVDA+SPY licensed market pilot. Held source owners must still bind actual PIT listing, source/reader first-seen, selected revision, correct corporate-action/volume basis, rights and population coverage. Hosted checks, source admission, independent model review and customer release remain distinct gates.


## 30. S2-P3 coverage-qualified day-cluster comparison — R2 selection-bias guard

An adversarial audit of the accepted BVC-versus-quote day-cluster calculation found a consequential **sampling-selection weakness**: as few as three comparable minutes out of 300 expected slots could produce an aggregate day-equal discrepancy if each minute came from a different session. Three dates alone are not evidence of usable market coverage; this implementation remained non-publishable but could still overstate the meaningfulness of its research statistics.

The separate accepted `session2/prototype/quote_study.py` now requires a registered **minimum 80% comparable security-minute coverage** both across the full owner-supplied expected slot population and **within each expected session** before returning an aggregate discrepancy or leave-one-day-out stability range. Both the overall fraction and sorted deficient-session IDs are carried in the result; source missing, quote ineligibility, bar mismatch and unclassified statuses are retained as unavailable rather than filled with zeros. When fewer than three comparable day clusters exist, the original `INSUFFICIENT_SESSION_CLUSTERS` remains. For three or more days where population/sample coverage is inadequate, the explicit `INSUFFICIENT_COMPARABLE_COVERAGE` state withholds all aggregate values. Quote *notional* classified percentage is not a substitute for source **minute-slot** coverage; one can be 100% while the other is 1%.

Ten deliberately failing targeted assertions (eleven additional test cases including the numeric policy sweep) established the defect and new refusal behavior. The corrected quote-study suite passes **45/45** and the complete registered **13-suite local native regression passes 403/403** on M2 Python 3.12. The exact synthetic low-coverage witness and receipts are versioned with this phase. This is a test of research information completeness and selection bias, not a newly calibrated confidence interval, real-market aggressor truth or institutional buying. All source/rights/auth, predictor, customer and trading authorities remain FALSE; S2-P1/2 actual four-name minute/trade/NBBO data remain NOT_ADMITTED. Previously denied source reads, benchmark, current-base comparison and separate red S2-P4 read-model patch were not attempted.


## 31. S2-P6 OOS session-label coverage and loss-weighting integrity — independent R2 fix

The newly accepted S2-P3 coverage guard prompted an independent adversarial audit of the **paired forecast OOS** assessor. A genuine analogue was confirmed: with 20 registered sessions and ten outcome labels due per day, **19 complete dates plus one date with only 1/10 known labels** yielded global matured-label coverage **95.5%**, satisfying the original 80% global threshold, and returned a day-equal mean loss improvement. The thin date was overweighted on equal calendar-day footing despite a 90% within-day missing-label rate, potentially distorting comparisons against price/volatility/turnover-only controls.

The corrected `session2/prototype/pressure_oos.py` now applies the **same registered minimum mature-label fraction to each expected holdout session**, not merely the pooled twenty-day sample, with explicit `low_coverage_sessions` in its result. If dates are too few, the original `INSUFFICIENT_HOLDOUT_SESSIONS` applies; if global coverage is below policy, the original `INSUFFICIENT_OUTCOME_COVERAGE` applies; otherwise deficient individual days produce **`INSUFFICIENT_DAY_OUTCOME_COVERAGE`**, withholding control/pressure MSE, improvement and leave-one-day-out sensitivity. A date with exactly 80% paired outcomes remains eligible. This preserves the pre-registered OOS target and loss estimand without relabeling future, missing or late outcomes.

Five deliberately failing first-pass adversarial cases established the omission; after repair, **46/46** OOS and **408/408 full 13-suite local tests passed** (previous accepted head: 392). The exact timestamped fabricated label-grid outcomes are retained as synthetic evidence, never claims of genuinely frozen model performance or predicted trading alpha. No source/membership/outcome system, trading stack, CI owner, authentication or data feed was created. Real AAPL/MSFT/NVDA/SPY one-minute/quote/print/data rights remain S2-P1 NOT_ADMITTED, and the previously explicitly denied source reads, benchmark/current-main comparisons and blocked downstream S2-P4 read-model patch remain untouched.


## 32. Window-reducer source digest reuse — byte-identical mathematical speedup

The intraday factor read-model **geometry** must be responsive across many overlapping constituent cohorts before any private consumer can be considered production-ready. A bounded synthetic performance audit of the already accepted `window_pressure.measure_windows` identified **repeated dataclass deep serialization** as a material avoidable bottleneck rather than BVC mathematical calculations. A 100-security/60-minute/6-factor profile spent 1.339 seconds cumulatively inside 37,988 `asdict` calls versus 2.326 seconds for the full profiled reducer.

The source now serializes each source-qualified computed `PressurePoint` **once per evaluation cutoff** and reuses the immutable in-memory representation for every factor that references it and the union source digest. It does not change the BVC buy fraction, expected/observed counters, neutral/unknown dollar classification, source/reader availability, overlap accounting, roster identity, actual input digest or baseline reference keys. Five **pre-captured full canonical WindowPressure SHA-256 output goldens** (complete, corrected history, partial coverage, explicit zero and multiple phases) remained byte-identical, and **413/413 full native tests passed** on M2 Python 3.12.

A single synthetic M2 comparison on 24,000 security-minutes (200 securities, 120 minutes, eight overlapping factors) observed 4.719s before and 3.649s after (~22.7% reduction), with an observed higher process RSS maximum (~242 MB versus ~260 MB). This is a **bounded one-run engineering measurement, not an empirically calibrated production latency guarantee**. See `session2/evidence/window_history_cache_performance.json`, `session2/prototype/test_window_pressure.py` and updated `session2/CUMULATIVE_WINDOW_CONTRACT.md`.

This optimization is in the approved upstream research window reducer, **not** the separately denied downstream `factor_read_model.py` integrity patch or previously denied benchmark interpreter/mutation script. The immutable source/source-reader basis, runtime admission, consumer ownership and customer publication gates remain unchanged, with the real four-stock qualified minute/trade/NBBO corpus still **NOT_ADMITTED**.


## 33. OOS outcome-known-at prefix isolation — independent causality bugfix

The S2-P6 offline validation code had a separate source-causality problem: although it **withheld** eventual outcomes with reader receipt timestamps after the requested evaluation cutoff, it **validated their future values too early**. A later correction or corruption in a label (non-finite, extreme, nonnumeric, boolean) could make an otherwise valid earlier report fail even though the source value did not yet exist in the reader's information set. This violates point-in-time reproducibility and artificially entangles historical evaluation availability with retrospective source quality.

The new bounded `pressure_oos.py` correction checks the numeric outcome **only if its `realized_known_at_utc_s` is at/before the evaluation cutoff**; all static source-clock/event ordering, model/roster identity, feature-known-at and label-known-after-event validation remains intact. Once the future receipt has genuinely matured, the same invalid values are **rejected**; no late label is filled with zero or reclassified as early. The existing day-equal paired loss, global and per-day coverage floor, minimum day count and NULL insufficiency behaviors are preserved.

Six targeted synthetic future-later-label mutations initially failed the as-of-prefix invariant. All now match the unchanged earlier status and exact input digest, and all fail closed once their original receipt time enters the evaluation window. The OOS suite now passes **53/53**, and the full 13-suite native regression passes **420/420 locally**. An independent fabricated metadata-only witness `session2/evidence/oos_future_label_prefix_witness.json` binds the six cases without publishing any hypothetical return values. This is a pure research-causality fix, not an actual historical market study, admissible label feed or live trading outcome. Previously denied source reads, benchmark/compatibility comparison and the separate four-red S2-P4 read-model patch are not touched; all customer authority remains FALSE.


## 34. Session 1 PIT history versus Session 2 traded-notional boundary — native contract conformance

The first genuinely usable integration seam to the active Factor Atlas program was recovered from sibling held [Macro Session 1 PR #8680](https://github.com/mastermindx-market-intelligence/macro/pull/8680), exact head `ddf1f07f2059caebb4bfa6b1db6c4008dd97859c`, and the already accepted Session 2 cumulative bar-pressure model. The S1 `factor_atlas_read.v1` native candidate is a USD **TRADJ total-return** equal/monthly/drifting long-only basket index; S2 requires a genuinely original-source-qualified **unadjusted/USD true-one-minute price × traded share volume** estimator, neutral/unknown flow separation and selected PIT factor roster. These quantities share at most source-qualified identity and economic concept; treating total-return index units or portfolio index weights as traded-dollar notional would be a serious monetary basis error.

An independent read-only interoperability function at `session2/prototype/cross_session_contract.py` now audits the candidate S1 `result_digest` using its **own published canonical UTF-8 JSON convention**, checks the S1 schema, fixed all-false authority, current-versus-PIT declaration, named source factor, same-session reduced cohort, duplicate member IDs, sorted member-set equality and S2 factor/mode/PIT basis. It does NOT infer historical membership from the S1 `source_refs.cohorts[]` summary, because that published shape contains only `effective_close,members,snapshot_ref` without the required original member-selection `known_at` receipt, effective interval, alias/identity knowledge epoch and source corrections. Likewise S2's `WindowPressure` cannot authenticate raw monetary basis from its reduced projected reference keys; the output calls `unadjusted/USD` a **required source basis**, not a verified fact. Even matching synthetic PIT member lists report `HOLD_SEPARATE_READ_MODELS`, `pit_roster_verified=false`, `source_receipts_authenticated=false`, no combined arithmetic and no market/publication/trading authorization.

**Native proof:** 29 new contract tests pass, covering tampered S1 result digests, current roster PIT overclaim, different and duplicated member IDs, stale/missing monthly candidate roster, unsupported price basis, claimed entitlement/rights and S2 corrected-history/partial overlap. The exact original S1 published synthetic example at head `ddf1...`, Git blob `3590dc40e3116834b79ae17628b399d4be01a18f`, was read only into an ignored local reproduction: SHA-256 `6860786ee663c394e0d33b18e241592879501a6bc5335a09faed6d66b0b42626`. Its own `result_digest` validates, and the S1/S2 checker correctly reports `CURRENT_ROSTER_NOT_PIT`, `FACTOR_ID_MISMATCH`, missing current-window selected cohort and absent original source rights. No S1 source implementation or output was copied into accepted S2 source. The complete existing read-only GitHub Actions research fixture command with **14 named suites passes 449/449 locally** on M2 Python 3.12.

The synthetic schema witness, source/test checks and hash-bound receipt reside at `session2/evidence/s1_s2_native_boundary_synthetic.json` and `session2/evidence/native_cross_session_contract_tests.json`; detailed exact source-owner integration rules are at `session2/S1_S2_METHOD_BOUNDARY.md`. The new contract is a **negative source-compatibility diagnostic**, not an independent factor registry, live source reader, source/use authorization, multi-factor customer endpoint or acceptance of S6 forecasting claims. S1/Macro #8680, S2/Macro #8677, S6/Macro #8696 and Terminal #928 stay held at their original owners. Source-admitted PIT membership and actual one-minute / trade/NBBO / split-adjusted volume/basis/rights/first-seen clocks remain needed for empirical S2-P2 and private consumer completion. Previously denied S2-P4 and S2-P6 source patches, earlier source reads and current-main compatibility requests are untouched; their red local WIP remains outside this PR.


## 35. Tiingo source qualification integrated directly into the existing Factor Atlas research lane

A new live-data opportunity materially changes the original no-capture assumption but **does not automatically qualify the desired S2 capital-pressure corpus**. Existing [Macro Tiingo Data OS PR #8698](https://github.com/mastermindx-market-intelligence/macro/pull/8698) at observed head `6eccb5aa3d3f640b8aea8dc61653bc0b4b5e9bde` reports genuine 1,552 nonempty equity EOD histories and 3,151,249 daily bars, plus 1,407 retained BOATS historical one-minute venue bars (AAPL/AMD). The incumbent Data OS reader `lib/dataos/tiingo_reader.py` blob `73c100cc9ab91f443210a1063c28f7390416f020` and L1 projector `lib/dataos/tiingo_views.py` blob `22d6058648bc111313dd0de5e4a679897b7c25e7` remain the original owners for source content, immutable receipts, reader purpose and rights/identity selection.

The original Tiingo source already registers separate producer routes for `eod-bars`, `boats-bars`, `iex-bars`, and `equity-intraday-bars`. We executed the **original Data OS read-only research reader** on the bounded, physically mounted AAPL and AMD BOATS historical L1 partitions, with explicit `RETROSPECTIVE_EXPLORATORY` purpose and hindsight acknowledgment; the genuine existing raw source/Parquet hash and row lineage checks passed. These are **historical BOATS single ATS venue** observations around 20:00–04:00 ET, not the 04:00–20:00 U.S. consolidated-minute population; the source reader returned `pit_backtest_eligible=false` and `redistribution_admitted=false`. Existing original sanitized owner proof remains at [Tiingo BOATS historic qualification](https://github.com/mastermindx-market-intelligence/macro/blob/6eccb5aa3d3f640b8aea8dc61653bc0b4b5e9bde/docs/tiingo-evidence/20261011-live-qualification/boats-history-qualification.json). A subsequent command to package that actual read into a reusable published artifact was explicitly blocked by the platform **before dispatch**, and was not retried, delegated or routed through a different account/tool. No such live-research-output file is claimed. This accepted source phase includes **only a synthetic, data-free reproducible witness**, not licensed price rows or a live market-pressure study.

The user-facing product needs a different Tiingo family: the existing `equity-intraday-bars` fixed-origin endpoint supports historical **consolidated equity intraday OHLCV with minute resampling** in Tiingo's documented beta offering; the mounted M2 Tiingo archive examined on October 11 had **no `raw/equity-intraday-bars` or `raw/iex-bars` family directory** at that exact root. BOATS minute bars cannot be relabeled as consolidated daytime activity, while IEX bars are single exchange and the current consolidated L1 projector explicitly states `vendor_equity_reference`, `volume_unit_vendor=unqualified`, `canonical_price_basis_admitted=false`. Source response, accepted actual monetary/corporate-action/volume basis, data-use/entitlement, canonical PIT listing, original first-known/revision selection, complete phase/calendar and statistically sufficient quote/trade labels still need the incumbent original Data OS owners, not a new Factor Atlas collector.

We implemented an **executable, source-owner-independent `prototype/tiingo_source_fitness.py`**, which consumes the incumbent `TiingoView` object shape (without importing unmerged original Tiingo source code into S2) and returns a strict **read-only negative-admission source-fitness read model**. It detects all four source-family types, validates fixed-origin original 1min unfilled OHLCV request identity and content/receipt source metadata, rejects source/rights/PIT/price/volume/venue overclaims, separates missing volume from a vendor reported zero, checks one-minute event clocks against the original later source capture, and records request-clipped overnight BOATS minute denominators. It has a distinct bounded **examined-partitions-only** four-name cohort verdict (AAPL/MSFT/NVDA/SPY), never an asserted complete source census. The BOATS request beginning at 00:00 ET is explicitly 240 possible requested slots for that partial overnight period, **not 480**, and a vendor reported zero is not independently verified no-trade. A coincident SHA across different vendor symbol contexts is refused.

The real output type permanently denies `source_admitted`, `pit_backtest_eligible`, `redistribution_admitted`, `may_compute_daytime_pressure`, `customer_publishable` and all five rank/alert/size/trade/publish permissions—even for a synthetically complete four-stock 1m input. Test-first missing implementation and duplicate query/source-context probes were red before fixes; **32/32** focused Tiingo S2 source-fitness conformance tests and all **481/481** locally selected **15-suite** research tests passed on M2 Python 3.12. The original hosted GitHub Actions `factor-atlas-reference` workflow adds that fifteenth suite and triggers on the incumbent Tiingo reader/projector/collector/registry paths without replacing their CI owner. The explicit synthetic witness, source and test hashes, no-admission results and sampling limits are at `session2/TIINGO_SOURCE_FIT_CONTRACT.md`, `session2/evidence/tiingo_source_fitness_synthetic.json`, `session2/evidence/native_tiingo_source_fitness_tests.json`.

**Next direct product-capability requirement:** the original Tiingo Data OS producer/reader must supply an actual **selected, rights-qualified four-name consolidated `equity-intraday-bars` one-minute** sample with exact original requested window, `columns=open,high,low,close,volume`, non-filled chart controls, 04:00–20:00 ET phase semantics, source/reader clocks, selected correction, original raw/adjusted and share-volume basis and issuer/identity/calendar ownership. Once the genuine source owner and the pre-existing S2 `source_preflight` agree, run the existing BVC/window replay privately and test it against real licensed quote/print evidence, independently from BOATS and IEX single-venue comparisons. **Neither Tiingo BOATS nor EOD unlocks that daytime pilot by itself.** The existing Source/PIT/Evaluation OS and two platform-blocked calculation corrections remain mandatory independent acceptance gates; do not claim customer or trading publication from this research code.


## 36. Actual Tiingo consolidated 1-minute four-name input secured — source-fitness phase R2

The Chairman's Tiingo installation now supplies an **authentic retained four-symbol intraday source sample** through the already merged native Tiingo Data OS carrier. On October 11, 2026, we directly executed the original bounded `scripts.tiingo_ingest.collect` for one October 9 `equity-intraday-bars` day for each of **AAPL, MSFT, NVDA, SPY**, with explicit `resampleFreq=1min`, `columns=open,high,low,close,volume`, `afterHours=true` and `forceFill=false`; 4/4 vendor requests succeeded with 438,057 raw response bytes and four independently selected source contexts. The original `tiingo_materialize` yielded four research L1 partitions, and the original `read_research_view` verified exact raw receipt/L1 lineage. This operation reused the **existing original Tiingo collector**, physical archive, Data OS reader and provisioned key; no new vendor client or duplicate data-plane/system was created. Its actual source receipts and first-received clocks have been durably recorded under the original [Tiingo #8698](https://github.com/mastermindx-market-intelligence/macro/pull/8698#issuecomment-6115007538) carrier without copying licensed vendor prices into Git.

Actual existing retained minute observations totaled **4,063** on October 9 ET: AAPL 1,010, MSFT 842, NVDA 1,146 and SPY 1,065. Each contained **390/390 regular-session timestamp slots**, making the original **nominal 1,560-slot** four-name RTH time grid complete. This is a substantial reversal of the earlier missing-source condition; full-calendar, original historical PIT, quote/trade, volume basis and rights qualifications are still separate. Specifically, 939 vendor rows occurred **00:00–04:00 ET** and are not the 04:00–20:00 S2 daytime model phase; outside RTH, observed bar density differs strongly across symbols. The existing L1 still calls interval volume units **unqualified**, does not establish adjusted monetary basis or admitted source rights, and the source capture was performed October 11, two days after the market events. It **must not** be relabeled an October 9 as-observed trading-information set. A historically downloaded bar cannot be assumed to reveal the actual exchange buying/selling side, full national volume or a verified institutional account.

The existing source-only `tiingo_source_fitness.py` was independently improved to disclose nominal ET `DaytimeClockCoverage` separately from true rights, issuer, corporate action and market-calendar admission. It records 04:00–09:30, 09:30–16:00, 16:00–20:00, and out-of-time bars by declared vendor timestamp; the four-name RTH clock-grid indicator requires exactly the same date and one unambiguous consolidated partition per name. Missing minute, duplicate revision and unknown-volume cases cannot self-admit a source. The original default `BETA_INTRADAY_SOURCE_NOT_INSTALLED` refusal now correctly identifies data as **retained but not canonically admitted**. No BVC pressure calculation ran on this unadmitted real dataset.

Ten additional test-first and adversarial Tiingo source-fitness cases bring the scoped suite to **43/43** and the complete **15-suite local regression to 492/492** on M2 Python 3.12. The admitted S2 research package remains **synthetic fixture plus code + protocol**; no raw or L1 market prices are in the git manifest. Exact source method and negative/positive observational distinctions are in `session2/TIINGO_SOURCE_FIT_CONTRACT.md`, and the existing [source-owner PR receipt](https://github.com/mastermindx-market-intelligence/macro/pull/8698#issuecomment-6115007538) binds the four real immutable capture SHA-256 IDs. The critical next named product step is to resolve the original Data OS/rights/issuer/calendar **source-admission contract**, then run a bounded empirical S2-P2 private replay with legally usable, correct time-vintage/consolidated-volume evidence; independent S6 validation, source-correct customer read integration and release remain held.


## 37. Tiingo PIT selected-alias admission boundary — original Data OS semantics, no new identity plane

The four retained Tiingo `equity-intraday-bars` source partitions now have a complete nominal 390-minute regular-session clock grid for AAPL, MSFT, NVDA and SPY, but **source content is not the same as historically knowable canonical security identity**. To move beyond an indefinite source owner status report, we inspected the original `lib/dataos/identity.py::VendorAliasTable` at current merged Tiingo producer head `2a08250fe61aa59ad3e1581149f0b93e9d5a17cf`, original source Git blob `ea8485596e57fd1e686bfdb9d75708a3a3845fda`. The incumbent reference `data/reference/_receipt.json` is dated 2026-10-09 05:05:32 and binds a 6,046-row vendor-alias table. Exactly **zero `vendor='tiingo'` alias rows** are selected for the four pilot names; the actual original `VendorAliasTable.from_records`/ `resolve('tiingo', ...)` returned NULL for all four. Other-vendor AAPL/MSFT/NVDA records do **not** establish Tiingo PIT aliases; SPY is additionally absent from the examined equity-only security-master reference. No new ETF security ID, alias selection, rights or source timestamp was minted.

The original Data OS alias resolver's `covers()` contract answers **historical symbol naming**, not automatically the full decision-known-at test for arbitrary vendors. An independent synthetic trial proved that an invented Tiingo alias first known October 11 can be resolved as a named security for October 9 using the original generic resolver, even though it could **not** have been known at an October 9 market decision. The new pure, bounded `prototype/tiingo_pit_alias.py` **does not duplicate that resolver**: it consumes only *already owner-selected* alias mappings, checks their canonical source-self-consistency SHA-256, inclusive/exclusive date intervals, original source-known-at UTC cutoff and duplicate/refusal conditions, and returns explicit negative admission reasons. In particular it does not adopt another vendor's ID for Tiingo and never selects between competing revisions. Its `alias_known_at` conservatively rounds any nonzero nanosecond tail **up** to the native Data OS microsecond receipt clock; decision cutoff never rounds forward, preventing future source evidence from entering an earlier information vintage.

All outputs are explicitly research-only, including an artificial four-name set that passes those structural and temporal checks: **`pit_vendor_aliases_admitted=false`**, `original_owner_identity_authenticated=false`, `source_rights_or_monetary_basis_admitted=false`, `market_pilot_admitted=false`, `customer_publishable=false` and all five authority flags FALSE. A matching hash or name does not prove original Data OS or Tiingo custody. This is a consumer-side **fail-closed source-contract test**, not an invented second issuer/identity table or a new Data OS source writer.

Test-first implementation originally failed for the missing module. A later targeted nanosecond known-at falsifier failed before the conservative rounding fix. The new suite now passes **25/25**, and the full existing **16-suite Factor Atlas native regression passes 517/517 locally** (previous accepted head 492). The existing read-only GitHub Actions workflow now covers changes to the original `lib/dataos/identity.py` and `scripts/build_security_master.py` paths, without replacing their source CI. Direct read-only original Data OS semantic alias-binding hashes agreed for four invented candidates, and the current original owner reference was inspected only through a sanitized negative-state summary, not copied into S2 Git. Artifacts: `session2/TIINGO_PIT_ALIAS_BOUNDARY.md`, `prototype/test_tiingo_pit_alias.py`, `evidence/tiingo_pit_alias_synthetic.json` and the immutable native source/test receipt.

**Completion gate narrowed:** the existing Data OS identity/ETF/listing owner must supply first-known, effective-dated, selected **Tiingo** vendor bindings for all four, especially a genuine SPY ETF/security listing identity, and its source/permissions receipt. Even then, the source-side Tiingo one-minute vendor `volume_unit_vendor=unqualified`, corporate-action/volume money basis, selected corrections, original October 11 receipt (not the October 9 event-known clock), rights/use and independent quote/science validation remain separately withheld. This project can continue directly with original Data OS source work when qualified, but must not turn selected foreign-vendor IDs or retrospective history into a backdated market signal. No previously platform-blocked S2-P4/S2-P6 edits, denied source reads, benchmark/main-comparison actions, or blocked BOATS packaging were replayed.


## 38. Direct Tiingo security search validates ETF SPY and detects cross-country ticker collisions

After acquiring the authentic four-stock October 9 consolidated one-minute vendor source, we advanced the **actual Data OS issuer/identity source evidence** directly rather than assuming matching display tickers were stable canonical identifiers. The original merged Tiingo Data OS `security-search` registered endpoint `/tiingo/utilities/search?query={ticker}` was used through its incumbent collector for four bounded requests, one each for **SPY, AAPL, MSFT and NVDA**. Original `verified_raw` confirmed exact content/receipt SHA-256 for all four, retained in the existing external archive. The original source metadata, hashes, capture clocks and honest limits are recorded on [Tiingo PR #8698](https://github.com/mastermindx-market-intelligence/macro/pull/8698#issuecomment-6115302530), not copied as vendor result rows in S2 Git.

This observation matters for historical PIT source admission: **each of AAPL, MSFT and NVDA has two ticker-exact Tiingo matches, one Canadian and one U.S.**; choosing the first match would be economically wrong. SPY has one U.S. ETF result identifying **SPDR S&P 500 ETF Trust**, with original vendor permaTicker and composite OpenFIGI present, but the existing Data OS security master/ETF owner has **not** selected an ETF security identity or source-effective Tiingo alias. The real vendor search was first captured on October 11 and cannot be presented as the October 9 known-at decision vintage. Correctly separating U.S. and Canadian source identity is a prerequisite to safely joining this vendor data to our factor PIT/monetary and historical OOS calculations.

An independent, pure `inspect_tiingo_security_search` function was added to the accepted `session2/prototype/tiingo_source_fitness.py`, consuming already-verified original Tiingo RAW_ONLY search data and original receipt metadata in memory. It requires a bounded fixed request, vendor source ID and raw/receipt hashes, U.S. exact match with expected stock/ETF class, active U.S. vendor candidate with a stable permaTicker/composite FIGI, and first-observed receipt not later than the requested decision to qualify even a **structural candidate**. It refuses multiple U.S. candidates, missing identifiers, inconsistent source query, inactive or wrong-class results, and future-known metadata. The returned U.S. vendor candidate is **not a Data OS canonical security**, exchange-MIC attestation, positive PIT alias selection, source-use-rights release, quote aggressor truth or trading authorization. Every authority bit remains FALSE.

The new test-first suite confirms U.S./Canadian exact-ticker collisions, SPY ETF class, no-US and multiple-US refusals, source/receipt identity integrity, original search row permutation, known-after-decision and nanosecond-known-at truncation, and the difference between prospective reference and PIT authentication. **19 new tests** bring focused Tiingo source-fitness tests to **62/62**, and the complete **16-suite native regression to 536/536 PASS** locally on M2 Python3.12, with zero unrun test suites. The expanded synthetic-only witness and native receipt remain under `session2/evidence/`; no original vendor rows or sensitive API credentials were copied to GitHub. The earlier four-stock minute source remains intact on the original Tiingo owner carrier; rights, price×share-volume adjustment, PIT source revision and full S6 validation are separate gates before a customer Factor Atlas capital-pressure product can be accepted.


## 38. Actual retained Tiingo four-name minutes through incumbent S2 source preflight — native integration

An **actual research-only source cohort** is available in the original merged Tiingo Data OS archive: 4,063 retained October 9 `equity-intraday-bars` one-minute vendor rows for AAPL/MSFT/NVDA/SPY, of which **1,560/1,560 nominal RTH security-minute timestamps** are present. Original source response/reader known-at was October 11; the original L1 labels interval volume unit and canonical price/split basis **unqualified**, and its identity/right flags remain false. Prior Session 2 had independent Tiingo source-fitness and PIT alias readers but no executable composition into the **existing canonical S2 `source_preflight` expected-calendar/availability/rights checks**. We added a pure, standalone `session2/prototype/tiingo_preflight_bridge.py` that accepts the original Data OS `TiingoView` value objects, a caller-supplied **unverified** calendar/time window and explicit evaluation cutoff, reuses the already accepted Tiingo fitness/context alias check, and populates the original `MinuteClaim` metadata while leaving all unavailable owner proof **NULL**.

The existing `source_preflight.preflight` remains the **single** true grid/refusal reducer; no second source/data/entitlement/revision/identity authority, archive, market calendar, trading algorithm or publisher was created. Source raw-content SHA and true capture receipt are retained as metadata, but original Data OS PIT identity/ETF listing, legal use rights, reader completion, sealed historical source prefix, selected correction, unadjusted price×volume basis, corporate action and volume convention are not assumed. Even a vendor-reported zero volume remains `UNKNOWN` for executable S2 measurement until the original volume/venue owner qualifies it; separately counted zero rows are not asserted as independent no-trade tape evidence. Each result always reports `SOURCE_METADATA_NOT_ADMITTED`, all source/customer/trading authority FALSE, with no BVC estimator evaluation.

**Direct real-data preflight proof:** The original `read_research_view(... RETROSPECTIVE_EXPLORATORY, acknowledge_hindsight=True)` was invoked **read-only** on the four existing authentic original Tiingo L1 partitions, without new network/API requests, archive writes, copied OHLC prices or new source planes. The source-fitness bridge consumed those four objects in memory under a caller-provided **nominal** October 9 09:30–16:00 ET scope and Oct 9 20:00 UTC cutoff. The incumbent S2 preflight reported **1,560 expected / 1,560 represented / zero missing** minute cells but **all 1,560 unknown/unqualified**. It additionally counted **2,503 retained source rows outside the RTH scope** and recorded `SOURCE_AFTER_CUTOFF` on all 1,560 in-scope cells, since original acquisition happened October 11. The native reason ledger showed 1,560 each of `LISTING_IDENTITY_UNPROVEN`, `MONETARY_BASIS_UNPROVEN`, `READER_RECEIPT_MISSING`, `REVISION_SELECTION_UNPROVEN`, `DATASET_RIGHTS_UNPROVEN` and related raw-source/PIT refusals. These are real **source fitness** measurements, not actual signed dollar activity, the true national tape, or predictive/trading outcomes.

**Test-first and source integrity:** Missing implementation failed first; two-vendor-context reuse of one alleged source SHA failed under a later adversarial test and was corrected by calling the already accepted `aggregate_cohort_fitness`, not duplicating source ownership. The new source-bridge suite passes **21/21** synthetic tests, including complete 390×4 nominal clocks, zero-vs-null vendor observations, late capture timestamps, context collisions, absent reader/basis/PIT/rights, source input permutation, future cutoff and nanosecond-precision known-at refusals. The existing Factor Atlas read-only GitHub Actions job now registers **17 focused suites**; all **557/557 native local Python3.12 tests pass** and the repository unrun-suite auditor found zero dark tests. Synthetic source/census fingerprints are retained at `session2/evidence/tiingo_preflight_synthetic.json`, source/test/log SHA-256 at `session2/evidence/native_tiingo_preflight_tests.json`, and owner-relative limitations in `session2/TIINGO_PREFLIGHT_BRIDGE.md`. None of the genuine licensed minute price rows appears in this accepted research manifest.

**Next authorized product gate:** The available vendor-source-coverage blocker is resolved; the original Data OS issuer/listing/ETF selection, historical PIT `known_at`, source reader/correction selection, canonical interval share-volume and split/action basis, provider rights for derived/non-display/display use and independent S6 quote-side scientific acceptance remain unresolved. The already documented S2-P4 read-model and S2-P6 future-decision source edits were explicitly platform denied and have not been retried by this distinct input metadata bridge. No customer release, ranking, alerts, sizing, trading, merge or deployment follows from a 1,560-slot complete **but entirely unqualified** source grid.

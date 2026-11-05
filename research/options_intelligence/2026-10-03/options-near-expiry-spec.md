# 0DTE and near-expiry analytical specification

**Status:** proposed research and engineering contract, 2026-10-03. This extends [MASTER_PLAN.md](MASTER_PLAN.md) and [CONTRACTS.md](CONTRACTS.md); it installs no schema, autonomous engine, store, loop, subscription, alert or runtime change. Numeric cadences, windows, budgets and thresholds below are proposed defaults for qualification, **not validated optima or proven available capacity**.

## 1. Purpose, cohorts and incumbent ownership

Answer three questions separately: what activity and uncertainty are observable now; how would an explicitly assumed option book's hedge change; and does a qualified feature improve a specified intraday forecast? A useful analytical surface does not earn a five-day directional weight. Current 0DTE research studies expiration availability, fresh trading and accumulated inventory with different identification designs; average dampening and conditional amplification need not conflict. The merged 2026 paper is not independent replication of its predecessor manuscripts. [Literature L13–L16](options-literature.md)

Record calendar DTE, remaining trading sessions and economic time to payoff fixing separately. The active 0DTE cohort consists of contracts expiring on the local product date that remain tradable at decision time. Near-expiry research uses the next one through five trading sessions, retaining individual tenors. AM-settled contracts awaiting fixing are a separate nontradable state. Freeze the initial root panel and contract-selection rule before outcomes; separate SPX/SPXW, ETF and single-name cohorts.

Reuse the four existing owners: `WS:ADVANCED-DATA-OPTIONS` for admission, reference data and storage routes; `WS:INTRADAY-FLOW-P0-RECOVERY` for capture, signing and publication; `WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY` for candidates, monitoring and expression outcomes; and `WS:OPTIONS-CONTEXT-AUDIT-PREREG-V2` for registered studies. Coordinate consumers through [Terminal #599](https://github.com/mastermindx-market-intelligence/mastermind-terminal/issues/599), [#603](https://github.com/mastermindx-market-intelligence/mastermind-terminal/issues/603) and the existing [#723 integration](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/723). Reconcile current contributions rather than commissioning duplicate producers. [Terminal census](options-terminal-census.md)

## 2. Data requests, minimums and separate budgets

The [Theta audit](options-thetadata.md) establishes advertised capabilities, not purchased entitlement, licensing, installed behavior, natural-session completeness or measured latency. Tick streams, sparse minute files and snapshots are different observation processes. A Pro full-trade stream includes nearby quotes but is not a full-market quote stream; the documented sparse quote file supplies minute observations rather than all NBBO updates. No capacity or final-five-minute claim follows from either description alone.

| Lane | Minimum for its stated research use | Requested qualification target |
|---|---|---|
| Broad trade observation | Individual prints with identity, conditions, correction linkage and eligible preceding NBBO for signing; aggregate-only history supports narrower descriptive work | Event-driven capture through the incumbent stream; retain events and publish 5-second aggregates, with 60-second research summaries |
| Selected live contract quotes | One-second observations for bounded quote-state research; this is insufficient to reconstruct every quote event | Event-driven NBBO for exact monitored contracts and a frozen surface-selection rule; initial ceiling 500 simultaneous selected contracts, subject to actual shared quota |
| Underlying/index reference | Timestamped, eligible prior observations; delayed or mismatched inputs cannot qualify live Greeks | Event-driven or one-second updates, with measured source and collector latency |
| IV, Greeks and scenarios | One-minute snapshots for minute-level historical analysis | Recompute selected contracts every five seconds, every second in the last 15 tradable minutes, only if resource and quote qualification pass |
| OI and reference state | Most recent revision actually available, with effective session | Accept source updates when available; reconcile before session and on reference changes; do not invent intraday OI from repeated polling |
| Consumer delivery | Preserve exact artifact identity and clocks at existing cadence | Seek ten-second qualified updates in existing surfaces; measure actual delivery age before claiming that service level |

Trade throughput/storage and quote-subscription count/bandwidth receive separate admission receipts and resource estimates. Allocate quote slots first to exact monitored contracts, then registered near-forward strikes and skew brackets; record selection and removal times. A selected quote universe cannot claim market-wide surface coverage. Broad trade coverage requires its own denominator and gap accounting. Backfill cannot erase an original live gap.

Proposed quote-state freshness gates are option age ≤5 seconds and underlying age ≤2 seconds; in the last 15 minutes, ≤2 and ≤1 second respectively. These are initial research eligibility rules, not signing-accuracy guarantees. Record age distributions and excluded coverage; signing requires its own sequencing rule. A 15-minute-delayed underlying cannot pass. Existing caches, SSE and polling must be qualified end to end; connection health or a recent build timestamp does not refresh market evidence. [Theta audit](options-thetadata.md) [Terminal census](options-terminal-census.md)

The proposed ten-second panel cadence is for analytical summaries. It does not certify an executable final-five-minute quote; exact-expression review requires a newly qualified quote through the existing owner, with age visible at the review decision.

## 3. Feature families and explicit windows

At decision time `t`, calculate trailing `(t−h,t]` windows for **h=5, 15, 30 and 60 trading minutes**, only from available revisions. Separately register last-**60**, last-**15** and last-**5**-minute analyses relative to the product's last-tradable boundary. These nested terminal periods are distinct research strata, not interchangeable labels or independent replications. Fixing-relative studies are separate where the economic fixing rule permits them. Forward outcome windows must end within the registered session/state; do not silently extend them overnight.

| Family | Exact proposed quantities | Interpretation and constraints |
|---|---|---|
| Observation quality | Received/eligible/valid counts, premium coverage, quote-age quantiles, gap duration, spread and best-size summaries in each trailing window | Describe coverage of the evidenced universe; empty, unknown and observed zero differ |
| Activity and inferred exposure | Gross premium; call/put premium separately; classified signed dollar delta `Σa·q·m·Δ·S`; signed vega per vol point `.01Σa·q·m·Vega`; unclassified premium | Compute separately for 0DTE and each near-expiry tenor; initiator inference is not customer, opening or dealer identity |
| Flow persistence | Fraction of qualified constituent five-minute bins whose signed dollar-delta flow shares the whole-window sign; contract/expiry premium concentration; sign reversal versus the preceding equal-length window | Zero whole-window flow yields no persistence sign; preserve package ambiguity and corrections; overlapping windows are correlated observations |
| Surface state | Forward-ATM IV and total variance `w=σ²T`; 25-delta risk reversal `IVcall−IVput`; butterfly `.5(IVcall+IVput)−IVATM`; tenor diagnostic `(w_next−w_0)/(T_next−T_0)` | Declare forward, delta convention and interpolation brackets; missing wings remain missing; validate comparable clocks/carry before interpreting forward variance |
| Conditional mechanics | Whole-book delta change under spot, IV and time scenarios; net Gamma at actual spot; qualified roots and crossing orientations; local-approximation error | Explicit inventory and surface dynamics; no strike-cumsum travel interpretation |
| Intraday response | Subsequent log return; sum of squared one-minute log returns; high/low range and thesis-signed adverse excursion; registered continuation/reversion labels and quote markouts | Report raw horizon variance before explicit annualization; outcomes or separately lagged features; future quotes never enter earlier formation |

Normalize activity against prior qualified sessions matched on time of day, product and expiry cohort. Preserve event-day indicators known at formation. Proposed primary attention diagnostics use the catalogue RZ convention: the preceding 60 eligible training sessions with at least 40 qualified observations and `z=(x−median)/(1.4826·MAD)`; insufficient history or zero dispersion yields an unavailable normalization. This is a robust scale diagnostic, not a probability. Register one primary family/horizon test and treat remaining windows as declared diagnostics. Shared catalogue feature IDs use their exact versioned definition; alternative persistence/window constructions in this near-expiry exploration require a separately named variant. [CONTRACTS.md](CONTRACTS.md) [Literature](options-literature.md)

## 4. Joint IV, Greeks, clocks and contract economics

Retain exchange, received, effective, available, computed and consumer-decision clocks; a historical event timestamp does not prove original receipt. Each model row carries option quote time/mark, underlying source/time, model/version, solver status, rate/dividend inputs, IV convention, day count and exact contract economics. Midpoint IV, trade-price IV and a vendor-supplied Greek are separately named observations or calculations. Failed inversion is null, with reason. [CONTRACTS.md](CONTRACTS.md)

Maintain `last_tradable_at`, `payoff_fixing_at_or_rule/status`, exercise cutoff, settlement payment date, exercise style, deliverable and multiplier. Settlement payment is not model expiry. Standard AM-SPX's special opening quotation depends on constituent opens and is **not one universally exact instant**; show rule and uncertainty instead of substituting 09:30. Half days, holidays, ex-dividend exercise and adjusted contracts require product-specific fixtures. [Theta audit, official Cboe/OCC references](options-thetadata.md)

Use a suitable European or American model with documented carry and exercise assumptions. Calculate exact remaining model time only where the economic clock supports it; preserve explicit expired/indeterminate states. Qualify price, IV inversion and Greeks jointly. The documented one-hour vendor floor does not justify a universal Gamma multiplier: refitting IV to the same price changes the comparison. Test fixed-IV and refitted-IV cases at 3,601/3,600/3,599/1,800/900/300/60/1 seconds, including ATM/wings, calls/puts and American/dividend cases. [Theta audit and TTE witness](options-thetadata.md)

Canonical IV/rates are decimals; vega/vanna per percentage point multiply the decimal derivative by .01. Theta/charm specify advancing-time sign and canonical per-calendar-year derivatives; per-second or per-day output divides by the declared year length explicitly. Show numerical/model uncertainty separately from quote quality. Annualized near-expiry IV can be unstable while total variance remains interpretable; neither should conceal an unsuitable input mark.

## 5. Assumed inventory and hedge repricing

Keep prior-session unsigned OI, assumed beginning inventory, fresh classified flow and known participant inventory in separate evidence classes. Call-positive/put-negative OI is one scenario. Public aggressor signs do not identify the opposing party or accumulated dealer holdings. Compare multiple predeclared allocations without presenting their range as a calibrated probability interval. [Literature L14–L16](options-literature.md)

For signed option positions `n_i` and suitable multipliers `m_i`, define underlying hedge shares `B=−Σn_i m_i Δ_i`. Reprice the entire assumed book at the target state:

\[
H=S_*[B(S_*,\sigma_*,t_*)-B(S_0,\sigma_0,t_0)].
\]

**Positive H means underlying buy notional; cash-balance change from this endpoint trade is −H.** This excludes continuous trading cash, funding and previous rebalancing. State sticky-strike/sticky-delta assumptions, inventory changes and expiries crossed. Proposed diagnostic shocks are spot ±0.25/0.5/1%, IV ±1/3 percentage points, and advancing time 1/5/15 minutes; crossed boundaries require proper expiry treatment, not positive-time clipping. [Mechanics witness](options-mechanics-witness.md)

Report all qualified Gamma crossings with orientation, current Gamma sign and a numerical near-zero band. The nearest crossing does not imply long-above/short-below. Show whole-book coverage and approximation error. Snapshot cumulative Gamma by contract strike may remain a sensitivity display, but cannot be relabeled as spot-path hedge demand. [Mechanics witness](options-mechanics-witness.md)

## 6. Alerts, uncertainty and failure states

Route proposed alerts through existing identities, deduplication and monitoring; keep them inactive until incumbent acceptance. Separate these classes:

- **Quality:** stale input, stream gap, correction, incomplete surface or clock/reference conflict. Withdraw the affected observation; do not create bearish evidence.
- **Activity:** unusual eligible flow, persistence or reversal. Proposed research attention trigger: absolute robust z≥3 with ≥90% valid received-premium coverage; retain sample count and unknown market coverage.
- **Surface:** qualified IV/variance/skew change or liquidity deterioration, with baseline and horizon visible.
- **Scenario:** sign/size change in a stated inventory's repriced hedge requirement; label mechanical and assumption-dependent.
- **Expression/candidate:** impending last-trade/exercise boundary, expired contract, unsuitable quote or source-linked support/counterevidence change. Expiration can invalidate an expression without invalidating its underlying thesis.

Proposed persistence requires two qualified observations at least 30 seconds apart; proposed repeat cooldown is five minutes. These are tunable research controls, not calibrated error rates, trading instructions or new activation authority. Last-five-minute expiry notices use their own event identity rather than waiting for an activity-persistence rule.

Expose three independent dimensions: **source quality** (coverage/clocks), **inference uncertainty** (signing/package/inventory/model assumptions), and **predictive uncertainty** (out-of-time calibration). Do not multiply them into a pseudo-probability. Predictive fields and support scores remain null until admitted.

Explicit fail states include unavailable entitlement, unknown universe, stale/delayed underlying, disconnection/gap, ambiguous sequencing, invalid/one-sided/locked/crossed quote, incomplete window, failed IV, unknown fixing, expired/nontradable contract, missing deliverable, partial inventory and correction supersession. Retained stale observations carry their original clock; missing values never become zero. [CONTRACTS.md](CONTRACTS.md)

## 7. Existing surfaces and decision roles

| Surface | Question it should answer |
|---|---|
| Flow Desk / Tape / Tide / 0DTE | What changed, across which contracts and windows, with how much eligible and unclassified activity? |
| Exposure / GEX / Positioning | Under which inventory and price/IV/time assumptions does the whole-book hedge change, and what is Gamma's actual current sign? |
| Structure / OI | Which prior-session state is known, and what remains unknown about today's positions? |
| Volatility / observed Surface | What uncertainty is priced, with which synchronized marks, model, tenor coverage and missing cells? |
| Surface Replay / chart companion | What evidence was available then, including revisions, irregular intervals and gaps? |
| Prophet / Options Alpha / Issue Desk | Does this qualified evidence alter investigation, intraday risk or expression feasibility for this exact candidate revision and horizon? |
| Payoff Lab / Plan | Is the exact expression tradable and liquid, and how do pre-expiry marks, expiry payoff and exercise differ? |

Broad-market evidence describes aggregate activity, liquidity and conditional volatility state. Candidate evidence must join exact existing candidate/evidence identities and compare with the frozen admission snapshot. Ticker coincidence is insufficient. A five-day candidate may display intraday options risk context without changing rank, direction, gate or size. Preserve current false authority flags and owner-reviewed schema compatibility. Workbench prototypes and draft integrations are not assumed shipped. [Terminal census](options-terminal-census.md) [CONTRACTS.md](CONTRACTS.md)

## 8. Replay, backtest and acceptance

Replay through existing artifacts and revision custody using information available at each decision. Distinguish captured PIT from reconstructed history with assumed latency. Preserve cancellations and later revisions; post-trade quotes belong to subsequent markouts. Divide cumulative changes by actual elapsed time; require a qualified open anchor for since-open views. Unknown surface cells remain unknown.

Freeze selection, feature variants, primary endpoints, latency assumptions and exclusions before evaluation. Compare actual incumbent B1 with B2 adding one options family on identical eligible populations; the audited options-free B0 comparator remains separate. Every training, tuning and calibration label must mature before the test-model freeze, as specified in RESEARCH_PROTOCOL.md. Evaluate the four trailing horizons and three terminal strata with declared multiplicity, purged overlapping labels and date-aware uncertainty. Keep event, liquidity, product and volatility regimes visible. Reuse completed historical studies; add only a registered unresolved question. Underlying returns, option marks and executable option economics remain separate outcomes, with spread, fees, missing exits and exercise accounted for. [Literature](options-literature.md) [MASTER_PLAN.md](MASTER_PLAN.md)

Acceptance requires: an incumbent entitlement/resource receipt; natural-session source and consumer age/coverage evidence; contract/clock and correction fixtures; independent price/Greek/repricing tests including accepted witnesses; correct stale/missing/replay identity behavior; and exact owner compatibility. Observation-only delivery can graduate after those gates. Predictive alerts or candidate-policy changes additionally require out-of-time incremental calibration, decision-loss/false-alert analysis and separate authority. No analytical correctness result substitutes for predictive validation or production permission.

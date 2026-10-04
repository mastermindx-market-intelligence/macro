# Prospective Cross-Session Transfer Protocol — V1.1 Challenger Amendment

Date: 2026-09-26
State: PROSPECTIVE_CHALLENGER_FROZEN / RESEARCH_ONLY / PRODUCTION_INERT / NO TRADING AUTHORITY
Operation: geopolitical-relief-event-study-20260924-sol-001
Carrier: Macro PR #8012 / `sol/geopolitical-relief-event-study-20260924`
Parent protocol: `research/CROSS_SESSION_TRANSFER_PROSPECTIVE_PROTOCOL_2026-09-26.md`
Parent protocol commit: `0f9d4d88cf78b06ab9985d32be9df5c2bc929fd2`
Protected Mastermind pin: `a31f49f4056943124cc0e7e42349e46feee444c7`

## 1. Supersession boundary

This amendment does **not** rewrite or replace the original prospective protocol.

The V1 primary remains:
- `SMH minus QQQ` return from +5 to +35 minutes after the exact admitted event clock.

This V1.1 amendment adds exactly one development-selected challenger:
- `QQQ minus SPY` return over the identical +5 to +35 minute geometry.

The challenger prospective clock begins at the Git commit timestamp that first adds this file.
Any event whose `available_at` is at or before that timestamp is development/history for the
challenger, even if it is prospective under the earlier V1 protocol.

If an event is later discovered between the V1 protocol clock and this amendment clock:
- it may remain prospective for the original V1 primary if otherwise eligible;
- it is **not** prospective evidence for the V1.1 challenger.

## 2. Why the challenger exists

A post-outcome specificity audit over the already-open development sample found that the apparent
cross-session relationship was not uniquely semiconductor-relative.

Development observations:

| Construction | All events | Clean-primary events |
|---|---:|---:|
| SPY absolute sign agreement | 7/12 = 58.3% | 5/7 = 71.4% |
| QQQ absolute sign agreement | 8/12 = 66.7% | 6/7 = 85.7% |
| QQQ minus SPY sign agreement | **10/12 = 83.3%** | **6/7 = 85.7%** |
| SMH minus QQQ sign agreement | 9/12 = 75.0% | 5/7 = 71.4% |

For QQQ-minus-SPY, clean-event Pearson/Spearman versus the next HSI open were
+0.681 / +0.893. The corresponding same-clock clean-parent controls were
9/14 = 64.3% sign agreement with Pearson/Spearman -0.561 / -0.347.

These values were seen **before** this amendment and are therefore development-selection evidence
only. They cannot be counted toward prospective validation.

## 3. Frozen candidate family count

From this amendment onward, the prospective comparison contains exactly two candidate families:

1. **PRIMARY_V1** — `SMH - QQQ`, +5 -> +35 minute return in basis points.
2. **CHALLENGER_V1_1** — `QQQ - SPY`, +5 -> +35 minute return in basis points.

The following may be recorded as nuisance diagnostics but are not promotion families:
- SPY absolute +5 -> +35;
- QQQ absolute +5 -> +35;
- SMH absolute +5 -> +35.

No third predictor, thresholded variant, optimized session bucket, fitted combination or
asset substitution may be added after future outcomes are observed. A future candidate requires
a new versioned preregistration **before** its eligible outcomes exist.

## 4. Shared event and clock law

The challenger inherits the V1 protocol without modification for:

- event-family admission;
- exact source `available_at` clock;
- SOURCE_RESOLVED / SOURCE_CONFOUNDED / SOURCE_UNRESOLVED handling;
- minute-close-known-at semantics;
- +5 and +35 targets and the existing 2-minute tolerance;
- no re-anchoring when bars are missing;
- DATA_GAP treatment;
- HSI next-cash-open endpoint;
- matched-control date selection;
- exact-clock reuse for prior/next controls;
- failure publication;
- V2 holdout isolation;
- no trading/product authority.

Primary and challenger must be measured on the **same admitted event population** and same clocks.
A missing leg stays missing; no family-specific event selection is allowed.

## 5. Prospective comparison law

For each qualifying post-amendment event, before the HSI target outcome is used for any amendment:

- record PRIMARY_V1;
- record CHALLENGER_V1_1;
- record nuisance baselines if available;
- record prior/next same-clock controls for each candidate;
- retain source/conflict/causal/data-gap state;
- publish wrong-sign and missing observations as faithfully as positive ones.

Before 10 qualifying post-amendment events:
- event-by-event evidence only;
- no pooled performance or winner claim.

At n >= 10:
- descriptive per-family sign agreement, correlations, missingness and matched-control deltas;
- report parent-event-collapsed control comparisons;
- no model/threshold tuning and no promotion.

At n >= 20:
- first clustered formal review is permitted;
- compare each candidate against its own matched controls;
- compare challenger versus primary on the same prospective events;
- explicitly account for the challenger having been selected on development outcomes;
- require cross-family/event-family concentration disclosure.

The challenger cannot inherit the V1 historical sample as validation evidence.

## 6. Current scientific interpretation

The development record no longer supports a semiconductor-specific transfer claim.

The live research question is broader:

> does event-conditioned U.S. growth/technology repricing relative to the broad market carry
> reproducible information into the next Hong Kong cash open beyond ordinary same-clock moves?

This remains a research hypothesis, not a forecast, probability, alert, score, rank, trade, sizing,
portfolio or execution state.

## 7. Existing-owner law

No new event rail, minute store, analogue engine, scorecard, scheduler, QLedger substitute or
product state is created by this amendment.

- live source facts remain with the existing press-wire / Brain event reader;
- specialized measurement remains on the bounded research carrier;
- historical analogues remain with the existing Brain/Oracle analogue owner;
- QLedger may be used only after a compatible governed claim-family contract is explicitly accepted;
- Chronicle remains its own deterministic/nightly event owner and is not advanced intraday here.

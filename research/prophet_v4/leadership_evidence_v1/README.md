# Prophet Leadership / Sector Rotation Evidence v1

**Date:** 2026-09-29
**Base:** `610c4865a8c207a81278c8ac7901e275eaa586fb`
**Protected procedure:** Mastermind `1405c634d8a0b0d3b05305fdd8d62e7b0b520e93`, Skillpack 1.0.1/bootstrap1.
**Status:** BUILT_NOT_PROVEN / DISPLAY_AND_RESEARCH_ONLY. No live rank, entry, policy, sizing, execution or trade authority.

## Problem this slice solves

The current US C1 ranker has no active F3 Theme/Peer family on the inspected board. Existing Group Flow has useful descriptive group structure, but a stock can create part of its own group evidence and current breadth does not identify whether the same leaders persisted.

This change adds two pure observations to the existing `engine/group_flow.py` owner instead of creating a new peer engine or second ThemeState:

1. `independent_peer_observation` — fixed-roster, leave-issuer-out peer values;
2. `independent_peer_continuity` — who remained, entered, exited or became unknowable between two fixed-roster observations.

## Identity and denominator law

The focal ticker and every known alternate listing of the same issuer are excluded from independent peer support.

A peer with unknown issuer identity is **not dropped**. It remains in the denominator and becomes uncertainty, so incomplete identity cannot increase the lower bound. Missing market observations likewise remain in the denominator.

The output therefore exposes lower/upper breadth bounds instead of survivor-renormalizing to whichever members happen to have data.

If focal identity is unavailable, the observation may still show conservative bounds but `independence_status=UNAVAILABLE`; no independent-peer claim is made.

## Why continuity is different from another breadth label

Prior breadth and current breadth are marginal counts. They cannot tell whether the same leaders survived.

Example on four peers:

- prior leaders A/B, current leaders A/B: prior breadth=.50, current breadth=.50, retained full-roster=.50;
- prior leaders A/B, current leaders C/D: prior breadth=.50, current breadth=.50, retained full-roster=0.

That joint transition information is not algebraically recoverable from the two marginals.

### Exact retention versus bounded continuity

`known_prior_leader_retention` is an exact complete-transition statistic only when the independent
peer roster is identity-qualified and every **known prior leader** has a current Boolean state.
A known prior leader whose current observation is missing is never dropped from the denominator to
make retention look stronger: the exact scalar becomes null with
`retention_measurement_state=UNAVAILABLE_PRIOR_LEADER_TRANSITION`, while the existing fixed-roster
lower/upper bounds widen.

Missing current state for a known prior nonleader does not invalidate the exact prior-leader
retention rate, because it cannot change whether a prior leader was retained. Unknown prior state
also does not retroactively enlarge the known-prior-leader denominator. If peer identity itself is
unresolved, the exact retention scalar is withheld as `UNAVAILABLE_IDENTITY`. If there were no
known prior leaders, the scalar is null with `NO_KNOWN_PRIOR_LEADERS`, never a favorable zero.

This distinction prevents missing data from manufacturing apparent persistence without collapsing
the useful full-roster continuity bounds or changing the upstream leader definition.

## Do-not-redo / negative-study boundary

This is **not** PSS-SR2 or PSS-SR3. Those frozen constructions conditioned on recovery after systemic fresh lows and used peer diffusion / synchronized short-horizon positive participation as a directional recovery label. They were rejected on the inspected history and remain closed.

The new functions contain no systemic-low anchor, tested-low/rebound condition, 0.50 treatment threshold, sign-reversal of killed labels, buy/sell stage, flow/accumulation claim, market outcome or fitted coefficient.

They provide descriptive bounded evidence only. A later B10/H1-compatible experiment must establish whether continuity improves selection on a common eligible population before any score authority.

## Current-data boundary

Curated thematic baskets still have a historical-membership limitation where their past aggregation can use a current tree. That limitation is not repaired by this source slice. PIT sector membership is a stronger existing owner path. A research consumer must bind the exact dated roster/source before describing a historical theme feature.

Ticker strings are also not sufficient issuer identity for production independence. The new functions accept an explicit `issuer_by_ticker` mapping; the future consumer must obtain it from the existing identity owner.

## Verification

Local exact-base affected suites:

- original reviewed head: `tests/test_group_flow.py` **55 passed**; the author's broader group/theme/basket run reported **269 passed**;
- current repair head: `tests/test_group_flow.py` **63 passed**;
- current directly imported group/theme set (group flow, regional flow, group pulse, downside RS, catalyst binder): **213 passed** after adding the retention regressions.

The repair tests prove the B=False versus B=None discriminator, identity-qualified withholding,
prior-nonleader missingness, no-known-prior-leader typing, same-marginal/different-continuity
discrimination, focal issuer exclusion, missing/identity bounds, roster-drift refusal, immutable
inputs and zero authority. Four deliberate source mutations of the new retention law are caught.

Green software tests are not predictive validation.

## Next capability

Bind one dated source roster plus existing identity mapping and group observations to a real Prophet candidate dossier. Compare:

- incumbent C1;
- transparent company residual momentum;
- group-only state;
- company + independent peer continuity.

Keep eligible population, clocks, entry policy and evaluation endpoint identical. The group-only comparator is mandatory so sector timing cannot be misreported as stock-selection skill.

Macro regime remains a permission / interaction axis, not an additive constant family. Entry geometry remains a separate B12 decision.

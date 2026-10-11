# RS Leader deep recovery: research and implemented contract

## Outcome and status

The existing Leader Radar now has an implemented, source-dated recovery descriptor and producer integration staged for this branch. The code preserves former-leader history through deep corrections, records failed repair attempts, and separates improving structure, price recovery, restored relative leadership, and entry extension. It does not create a second event, portfolio, trading, identity, calendar, or publication owner.

Parent: Macro PR #8750, branch `sol/rs-leader-daily-weekly-high-watch-20261010-c1`. Current Chairman instruction explicitly includes research, planning, and implementation. Protected procedure: Mastermind `326c8469a21d7f50fc9ecb1848196bf1c6e66685`, Sol skillpack 1.0.1. Live Entry Radar #8649 and Leadership Lab #8586 remain separate incumbent source work. The existing shallow 5-20% above-200-day-average pullback construction is unchanged.

This is **descriptive source implementation, not a validated trading signal or production acceptance**. Fundamental-thesis classification is deliberately UNKNOWN when a source-dated fundamental owner has not supplied qualified evidence. The local price evidence ends October 8, 2026; this package does not attest the prior conversation's externally reported October 9 ATH or analyst catalysts.

## Research basis and implications

1. George and Hwang, *The 52-Week High and Momentum Investing*, Journal of Finance (2004), DOI 10.1111/j.1540-6261.2004.00695.x: high-price reference research motivates explicit reference levels, not a claim that a price/RS high identifies an executable entry. Paper-level metadata/abstract was consulted; no copied proprietary indicator implementation.
2. Daniel and Moskowitz, *Momentum Crashes*, NBER WP 20439, https://www.nber.org/papers/w20439 : abstract-level evidence warns that sharp rebounds and momentum crashes depend on market conditions. A rebound alone cannot certify durable leadership.
3. Novy-Marx, *Fundamentally, Momentum is Fundamental Momentum*, NBER WP 20984, https://www.nber.org/papers/w20984 : earnings-related information motivates a separate fundamental evidence axis; it does not justify inferring healthy fundamentals from a recovered stock price.
4. Palantir's Q2 2026 issuer letter, https://www.palantir.com/q2-2026-letter/en/ : later earnings information is an example of a potential evidence update. It must not be inserted into a June decision. No assertion is made that the letter causally explains a particular price move.

These sources do not validate this implementation's cutoffs. All numerical definitions below are **unfitted engineering priors**, selected with the PLTR case already known. Neither this report nor an after-the-fact timestamp is a prospective preregistration.

## Implemented behavior

`engine/leader_recovery.py` is pure. It consumes completed daily close series and the incumbent exchange calendar. A prior leader is explicitly a PRICE_RS_PROXY: a strict RS high versus the preceding 252 sessions, positive 252-session absolute performance, and price above its 200-day average. This is not an invented historical recommendation or an impersonation of the older lifecycle's events.

A correction opens 10% below a previously observed leader peak. The original episode reference and pre-correction RS target stay fixed; an independently recorded price high-water can advance. The maximum drawdown's own peak and trough prices/dates remain paired, so a later higher peak cannot be combined with an earlier trough to fabricate a drawdown.

Repair requires a 15% rebound and three completed observations above the 50-day average with positive 21-session compounded relative performance. REIGNITING also requires three observations above the 200-day average. A failed repair is a close below the floor frozen when that repair began. It invalidates that attempt, not the company forever. Repeated failure counts remain visible. REPAIR_PAUSED describes a previously repairing name still above the long trend but lacking current confirmation; an old maximum drawdown alone must not make current structure 'damaged'. Full restored leadership requires both price and the pre-correction relative reference, with confirmation.

Entry context is independent: EXTENDED, REPAIR_OBSERVATION, or WAIT. It does not issue orders, size positions, rank candidates, change Prophet admission, or manufacture a probability. All authority flags remain false.

Missing source dates are not forward-filled. A gap resets indicator windows and confirmations; a gapped episode cannot be declared fully observed/recovered. Short histories are UNAVAILABLE, not proof of no leadership. Future values and duplicates after the requested cut cannot alter an earlier prefix. Duplicate past sessions and ambiguous timezone labels are refused. Current-vintage source fingerprints and definition hashes distinguish a reconstruction from original first-seen evidence.

## Product integration

`scripts/build_leader_radar.py` attaches `display_chips.leader_recovery` only after incumbent states, fires, and ordering are fixed. It publishes `recovery_roster` through the existing `site/leaderradar/radar.json` writer. Optional recovery failure does not remove the original ticker row. No independent data/ history or scheduler is added. The original lifecycle, shallow pullback, weekly high lens, and old UI continue unchanged.

The new recovery-specific UI partial has **not** been created: its direct host write was explicitly refused (`Command not allowed`); exact readback confirmed the target absent. It was not retried or moved to another carrier. An uncommitted include of the absent file was removed. Do not report the new recovery panel as implemented or browser-proven. The backend, tests, and empirical work are independent of that blocked UI effect.

## Executed validation and actual findings

- 333 focused tests passed on the connected Mac with the branch's staged source over a read-only host dependency checkout. This comprises new recovery/outcome/producer tests and legacy lifecycle/builder suites. Eight existing pytest temporary-directory cleanup warnings were non-failing. This is not exact-head hosted CI.
- A three-name real producer fixture showed complete incumbent payload equality after removing only the two new recovery projections and pre-existing volatile build timestamps. The express build did not modify any fixture data-store bytes. The optional-failure test retains all original ticker rows.
- Six deliberately introduced temporal/state defects were each caught by the core regression suite; the mutation method and result are preserved separately. This is adversarial author verification, not independent acceptance.
- The actual source census covers 173 incumbent members plus explicit non-recovery examples, 176 unique names, through October 8. It produced 1,756 horizon-label rows from observations starting January 2024. Current membership is survivorship-biased and is not a point-in-time historical population.
- PLTR's maximum close drawdown is approximately 48.22% from the November 3, 2025 close high of 207.18 to the June 25, 2026 close of 107.27. Its first reconstructed 2026 re-ignition is August 6. At the October 8 cut it is REIGNITING and EXTENDED, not a certified entry or a retrospectively certain June-bottom call.
- PYPL, DOCU, PTON, UPST, and INTC are included as counterexamples, not excluded for disappointing returns. A failed attempt may rebound later. 'No recovery by horizon' and right-censoring are distinct from permanent failure.
- In the corrected all-decision return sample, REIGNITING observations have median SPY-excess returns about -0.15 percentage points at 21 sessions and -2.50 points at 63 sessions. REBUILDING is about +0.11 and -2.03 points. These descriptive stage groups are not matched causal comparisons. The broad result does **not** establish an alpha edge.
- The first diagnostic accidentally restricted forward returns to unresolved barrier intervals, excluding already-failed attempts. The implementation now separates return-sample completeness from event risk-set eligibility. The initial diagnostic remains preserved, and the corrected cohort keeps losing and non-firing cases.

See `CENSUS_SUMMARY.json`, `test_receipt.json`, and `producer_parity.json` for actual identities and denominators. The full event rows are reproducible with `python -m scripts.research.leader_recovery_census --out /tmp/recovery.json` against the identified source vintages; a later provider correction may require the original source owner to recover those vintages.

## Remaining empirical and acceptance work

The next exploratory comparison uses one shared endpoint per correction and keeps no-entry cases in the denominator: immediate correction entry versus fixed waits, a simple moving-average reclaim, and the richer repair/re-ignition condition. Execution must occur after observation, and cost sensitivity and exposure time must be disclosed. This tests whether the extra conditions add timing value rather than rewarding a longer horizon or quietly removing failures.

Predictive promotion additionally requires actual historical universe membership including delistings, first-seen/revision-consistent source vintages, matched market/sector regimes, clustered uncertainty, a declared untouched/prospective evaluation, and realistic spreads/slippage. Source implementation is not evidence that these requirements are already met. Fundamental thesis health requires issuer- and publication-time-qualified data from its existing owner, not a price-only guess.

Source release still requires current candidate CI and the applicable independent review. Deployment and natural publisher/API/browser proof remain separate. No production configuration has changed.

## Continuity and held effects

An independent READ-ONLY audit was submitted exactly once through Executive session_summon using operation `rs-leader-deep-recovery-independent-audit-20261010`. It returned EFFECT_UNKNOWN. Original-operation reply lookup returned unavailable; there is no dispatch/start/return proof and no resubmission or alternate worker. This unresolved audit effect is fenced and does not authorize another audit. The implementation and empirical work above do not depend on it.

DO_NOT_REDO: the incumbent RS-high feature, old shallow-pullback engine, completed failure/repair source tests, and the original refused UI write. Continue with source publication/readback, exact-head verification, and the finite-endpoint research comparison. Do not replace current source custody or declare 'live' from these files.

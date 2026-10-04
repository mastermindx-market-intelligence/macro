# Options intelligence: reference quotes, delivery value and model acceptance

Date: 2026-09-11 UTC. Parent: WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY. Same research carrier #7027. Records only; no production source, registry, collector, deployment, model or trading authority changed.

## Result and source identity

This continuation recovers an existing private same-basis exact-option comparison system and establishes that its frozen trigger-reference price convention is not automatically a price available when a user receives an alert. Preserve that ruler; a delivery-conditioned comparison requires a separately reviewed basis under the same owner, not a silent change to the existing function.

Protected Skillpack: Mastermind `068dcc1533776672844b36ffcde30fad68a4317f`, INDEX/COLD_START/RECONCILE_STATE/CLOSEOUT, v1.0.1/bootstrap1 compatible. Analytical Macro: `4b1f8fddcc4eb6f36133fca4d42018678b74d30b`. Research-carrier pickup: `99afc564a649cf217eb47de25d749bdb039af33d`, open/draft, eleven records. Earlier census, installed-source, host/store, publication and prefix-integrity findings remain historical evidence, not tasks to repeat.

Primary own-source references at the analytical pin:

| File | Git blob | Relevant purpose |
|---|---|---|
| docs/runbooks/OPTIONS_NBBO_COHORT.md | 410fd67dcfb3253f96ae7afc832119059a4c2ad1 | Frozen reference, private unarmed adapters, capture eligibility |
| engine/options_nbbo_cohort.py | b84426de82c9d55caa26e9dd95092460be6dda1b | effective_boundary around298–305; build_observation around1626–1770 |
| engine/options_mastermindx_capture.py | b56a171e6e3f0cab15ce85df037e22ed82d2925b | Capture-only helper, not source examination or successful capture |
| scripts/live_flow_poller.py | 4f7280d1f96e76cfcaf9382eec124ea13aa9d6d1 | Fetch barrier, sequential processing and final durable stage |

The cohort source is141673bytes, SHA256 `55ebf34be6ae56565eab36a4b4568a6f63331bc7d7c3c962285d87173ad4fb78`. The poller blob matches the earlier deployed source as well as this analytical pin. Source references establish behavior, not runtime activation.

## 1. Reuse the existing exact-option owner

The runbook governs a MastermindX versus MomoEdge comparison. Entry is the first qualified OPRA ask at/after the immutable trigger; exit is the first qualified bid at/after the fixed terminal. Expiry has a fixed final-session15:55ET terminal. The one-contract and $0.65-per-side assumptions are a declared reference basis, not universal fees or recommended sizing.

Event and successful-capture producers are intentionally unarmed. Exact producer/rule/source/auth/evidence validators must be admitted before enrollment or positive capture. An environment value or first-seen digest cannot arm them. The MastermindX capture helper explicitly has not examined candidate sources. Its existence is not signal production or successful coverage.

A qualified Studio file read found the existing optionsnbbocohort plist. A private HEAD read refers to an August12 in-progress snapshot with25unavailable attempts per system, zero enrollments and zero eligible outcomes. Declared snapshot SHA256 `b6cb0a7986fb5e441f6889b4333c61a0d458adbca5614224e559c2f6bae66d2e`,3366bytes. This old stored snapshot is not a current full-corpus or scheduler census. Raw private rows and quotes were not exported.

Nightglass is not silently admitted as another comparison system. No new competitor/member collection, subscription, provider request, successful capture, enrollment or registry activation occurred. Rights and producer admission remain separate gates.

## 2. The reference boundary is intentional, but not a client-fill boundary

`effective_boundary(event)` returns event_at. The observation builder gates request start on available_at, selects the first qualified quote at/after the original trigger, and checks quote-event-to-actual-response-completion lag against600seconds. The600-second fence is not a time-to-first-quote limit. A passing timing check does not waive source authentication, capture, enrollment or quote-quality conditions.

One native test on the existing hash-verified Git object extracted only NbboCohortError, _utc and effective_boundary. With synthetic event_at14:00Z and available_at14:05Z, the returned boundary was14:00Z. No production module or side-effectful function was imported or run. The own Mini PID23211 exited0.

Exact native aggregate receipt SHA256 `9f99e1759a373a7196fa375cdb5a18b2d1877935b6a74a10373482ebe9dcaa68`; recorded_at2026-09-11T05:10:57.616394+00:00. The local packet reconstructs its768bytes exactly after checking the source-returned digest. An initial reconstruction using an incorrect copied timestamp failed and was not accepted; the closed process output was reread, not the experiment rerun.

The useful distinction is between trigger, system observation, evidence availability, service publication, client receipt, decision/transmission and actual fill. A response received after availability can legitimately describe an earlier reference quote. It cannot prove that earlier price was obtainable after user delivery.

A first observed quote update after a decision is also a convention, not necessarily the prevailing quote at that exact instant or a fill. Theta's primary quote-history documentation distinguishes tick observations from interval samples, which represent the last quote at their sample timestamp: https://docs.thetadata.us/operations/option_history_quote.html . Do not change the quote convention to obtain convenient values.

## 3. Synthetic economics establish why this distinction matters

All examples below are original stipulated arithmetic, not vendor calls, market backtests or current performance.

A long standard-multiplier contract entering at a reference ask3.00 and exiting at bid4.00 produces +$98.70 / +32.90% after1.30fees. If the delivered-entry ask is5.00 with the same terminal, it produces -$101.30 / -20.26%. A second hypothetical strategy with entry2.00, delivered-entry2.10 and exit2.40 yields +19.35% / +13.67%; their relative ranking reverses between rulers.

For matched quantity q, multiplier m and equal fees:

`PnL_delivery - PnL_reference = mq * [(bid_delivery-bid_reference) - (ask_delivery-ask_reference)]`.

The first example loses200dollars of quoted value through a2dollar entry difference. Delay can improve a price as well; no monotonic claim about real market delay is made. The identity does not estimate market impact, fills or all causal consequences of a faster service.

Keep candidate, exact contract, terminal policy, quantity and costs fixed for a paired timing comparison. Recalculating targets/stops, changing the option or filtering late candidates is a different full-policy experiment. Preserve its rejections and no-entry population rather than calling the result pure latency improvement.

For stipulated future terminal bid B, multiplier m, fee per side f and desired return r on initial premium, a continuous scenario entry ceiling is `(B-2f/m)/(1+r)` when positive. B4,f0.65,m100,r20% gives3.3225. This is algebra, not a forecast of B or an admitted anti-chase gate. A realized future bid cannot become an earlier model input. Tick rounding, capital and execution require their own policy.

One-contract normalization is not equal-risk normalization. Two synthetic trades1→2 and100→90 have mean individual return+44.34%, but total cash P&L-$902.60 and premium-weighted return-8.94%. Neither arithmetic mean nor that cash ratio alone is a time-feasible portfolio result.

## 4. Coverage and unknowns must not disappear from the result

The existing reference runbook correctly uses intersection coverage for both authenticated systems, maximum gaps and exact observed-call enrollment reconciliation. In78slots,75successful slots per system each means96.15%individual coverage, but different missing slots can yield only72common slots/92.31%. Replacing the intersection with individual uptime is wrong.

Even75common slots does not bound all-call recall without an independently known call population. Failures can coincide with busy periods. Eligible-session reference results and whole-service opportunity availability answer different questions; keep both visible rather than rewriting the frozen cohort rule.

With a stipulated known100-call population,80observed calls totaling+$800 and20missing outcomes bounded within[-200,+200]dollars, the full mean lies in[-32,+48], not the observed-only+10. This is an identified sample range, not a confidence interval. Its missing count and finite bounds are assumptions, not consequences of slot coverage or generic option risk limits.

Unknown client timing can imply a set of feasible quote prices. With entry3–5 and terminal4, the synthetic net-return range is[-20.26%,+32.90%]. Do not replace an unidentified sign by a midpoint or the original alert price. Missing quotes, no entry, expiry, withdrawal, still-pending outcomes and unavailable capture are separate dispositions.

## 5. Source processing has two barriers; faster computation is not automatically faster delivery

The pinned `_fetch_all` completes the concurrent fetch batch before returning the dictionary. `run_cycle` processes roots sequentially, accumulates pending learning events with immediate stage callbacks disabled, saves the completed state, and drains the durable stage. This order preserves the existing WAL/dedup/replay contract.

In an abstract schedule with fetch-ready times1and100seconds, processing1second each and durable cost1second, decisions occur101/102 and availability103. Overlapping the fast root's processing can move its decision to2seconds, while final availability remains102if the same cycle barrier is preserved. A99second earlier intermediate decision yields only1second earlier exposure.

This is a deterministic scheduling counterexample, not an observed phase profile or a proposed durability bypass. Measure per-root completion, computation, durable stage, publication and client consumption before selecting a concurrency repair. Never improve reported latency by stamping availability before durable evidence or weakening the WAL transaction.

## 6. Model and product direction

M1 must expose supported measurement/association, uncertainty and coverage. M2 must predict declared outcomes using information available at its actual decision boundary and account for target/stop/deadline plus enter/wait/decline economics. M3 must evaluate the exact instrument, quote/IV/time/quantity/management policy and its denominator. These remain unadmitted research models; missing input cannot be renamed neutral evidence or a profitable option target.

A useful first candidate can display measured activity, source-backed interpretation, original availability, legitimate plan geometry and an expired/unavailable-entry state before any probability model is promoted. The old shadow parser must not be loosened to manufacture picks. The current candidate/event/Issue Desk owners remain controlling.

Existing PR#6867 owns a separate descriptive Intraday Flow timing/precursor and chase_above repair. Fresh metadata head during this study was1ba8321db28c7ff8458ac2931bd5bcf9bde66809; body prose contains an older head. It remains open/draft, with no new semantic review or custody transfer performed here. Snapshot consistency is not persistent trigger memory; do not build a parallel lifetime or anti-chase store.

## 7. Prepared delivery-basis study — not admitted or executed

Mission: produce unchanged reference and separately named delivery-conditioned quote results for the same governed opportunity under the existing evidence owner. The full user packet contains `proposals/DELIVERY_BASIS_EXPERIMENT_DRAFT.md`.

Before acquisition or fitting, source-owner review must fix:

1. Exact unit/population, source/contract eligibility, immutable revision and baseline rules before outcome inspection.
2. Trusted event/availability/publication/client/decision clocks and bounded synchronization uncertainty. No mtime, polling-clock or date-only substitution.
3. First-update-after versus prevailing-quote convention, maximum wait, session/terminal policy, quantity, fees and quote-validity/rights requirements. Quote benchmark and fill remain separate.
4. Paired measurement comparison with unchanged contract/terminal, separate from a full-policy change that rejects late entries or changes targets.
5. Complete accounting of matched, missing, withdrawn, expired and no-entry opportunities, plus conditional eligible-session results and independently supported service-availability denominators.
6. Chronological evaluation with campaign/session dependence, recorded model-search trials, supported-domain reporting and a locked forward cohort before calibration claims.
7. Existing owner/interface reuse, original reference preservation, no private-row export and no new collector, control plane, ledger, model gate or trading permission.

Acceptance begins with one lawful natural evidence pair and negative tests for clock inversion, earlier-quote substitution, unsupported schemas, missing-pair coercion, fee/unit errors, coverage substitution, revisions and prematurely claimed fills. Browser/machine-consumer proof is separate from an offline calculation. Stop at unresolved rights, writer custody, required source evidence or DNR scope; do not route around an unavailable gate.

## Verification and continuation

Standalone original lab:70tests pass,13deliberately wrong variants detected by assertion with zero mutation errors. It covers exact clock arithmetic, quote-boundary examples, cash/percentage denominator distinctions, coverage and missingness, paired identities, uncertainty bounds, two-barrier schedules and scenario entry budgets. Full cohort admission, production tests, real fills, market profitability and forecast calibration were not tested.

No new competitor data, paid account, provider request, enrollment, source/repository implementation, host mount/link, launchd writer, checkpoint, model, ranking/sizing, workflow rerun or trade was changed. The own native Mini analysis process exited0. A read-only Studio process inventory did not establish a complete current source-host/licensed-writer qualification; no foreign process was acted on. Earlier blocked historical and JS studies were not retried or bypassed.

**Next research action:** existing evidence-owner review of the prepared delivery-basis contract before any acquisition, append or fitting. This is not a prerequisite for disjoint lawful OA-1T NBBO observation. Independently, the existing deployment/source owner continues the current permitted host/store/writer qualification and adoption of the already-accepted measured source, with natural-session proof. OI recovery, AD-1T2, OA-1C, OA-3/4/5, DNR, Issue Desk and the unresolved publication/prefix holds retain their separate gates.

Repository-wide Agent OS validation, independent release review, hosted CI success and production acceptance are not claimed. Keep this carrier draft. The value is a better-defined and tested measurement target, not a shipped trading engine.

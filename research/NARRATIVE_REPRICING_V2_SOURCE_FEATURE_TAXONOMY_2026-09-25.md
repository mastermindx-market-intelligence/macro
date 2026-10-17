# Narrative Repricing V2 — Source-Side Feature Taxonomy

Date: 2026-09-25
State: TRAINING_FEATURE_FREEZE / RESEARCH_ONLY / PRODUCTION_INERT
Operation: geopolitical-relief-event-study-20260924-sol-001
Carrier: Macro PR #8012 / sol/geopolitical-relief-event-study-20260924

## 1. Purpose

Wave 1 falsified the idea that an oil reversal alone is sufficient for positive
semiconductor continuation. This taxonomy freezes source-side explanatory attributes before
they are used to fit thresholds or inspect the prospective holdout.

The taxonomy is descriptive. It does not assign a trade score, rank events, create an
alert, or change portfolio/execution authority.

## 2. Assignment law

Every attribute must be assigned from source text, provenance, and information available at
the event clock. Post-event returns may not be used to choose a label.

If an attribute cannot be established from the source record, use unknown. Do not infer a
stronger category from subsequent market reaction.

Materially identical claims inside the six-hour event-cluster window remain one cluster.
A later item can become a separate event only when it adds material new information rather
than merely repeating or translating an existing claim.

## 3. Origin authority

Record the claim origin separately from the dissemination channel.

Allowed origin_authority values:

- direct_government_action — signed text, formal government/agency action, official order.
- named_principal_quote — attributed statement by a named decision-maker or authorized official.
- official_anonymous — unnamed official(s) speaking through a recognized reporter/wire.
- bilateral_or_mediator — statement by a named mediator/counterparty about the negotiation.
- wire_named_sources — wire report with identified non-government sources.
- wire_anonymous_sources — wire/report based on unnamed sources.
- secondary_media_sources — report relayed from another outlet or local/state media.
- social_primary — first-party social post by a principal.
- unknown.

This is not a numerical credibility score.

## 4. Dissemination channel

Allowed dissemination_channel values:

- official_release
- reuters_wire
- newsquawk_live
- named_reporter_live
- market_feed_relay
- republisher
- social
- other

The market-availability clock belongs to the dissemination record actually observed, not a
later article page, video upload, recap, or clip.

## 5. Novelty role

Allowed novelty_role values:

- first_material_disclosure — first recoverable public disclosure of the material fact.
- material_confirmation — confirms an earlier report and adds decision-relevant certainty.
- implementation_detail — adds timing, operational terms, enforcement, or physical-flow detail.
- negotiation_progress — materially changes the stage of talks without a concluded agreement.
- proposal_or_intent — proposal, desire, or willingness without acceptance.
- repeated_confirmation — substantively repeats already-public information.
- contradiction_or_denial — conflicts with or denies a prior material claim.
- ambiguous_or_unknown.

Repeated confirmation cannot be upgraded to first disclosure because its market move was large.

## 6. Resolution stage

Allowed resolution_stage values:

- rhetoric
- mediation_attempt
- proposal
- framework
- agreement_reported_unconfirmed
- agreement_confirmed
- signed_or_formalized
- implementation_scheduled
- physical_implementation
- breakdown_or_reversal
- unknown

This axis measures where the real-world process stands, not whether the market liked it.

## 7. Physical-channel specificity

Allowed physical_channel values:

- none_generic_diplomacy — no direct shipping, blockade, sanctions, mine, route, or flow term.
- navigation_intent — stated intent to reopen/close or protect navigation.
- operational_terms — route, toll, blockade, sanction, mine-clearing, escort, or enforcement terms.
- scheduled_flow_change — specific implementation timing expected to alter physical transit.
- observed_physical_change — verified vessel passage, mine clearing, blockade action, strike, seizure, or physical disruption.
- unknown.

For escalation events, the same categories apply symmetrically: a verified vessel strike is
observed_physical_change; a threat to close the Strait is navigation_intent.

## 8. Corroboration state

Allowed corroboration_state values:

- single_unconfirmed
- single_official
- multi_source_same_origin
- cross_party
- implemented_or_observed
- conflicted
- unknown

A widely repeated single-source rumor remains single_unconfirmed.

## 9. Event role

Allowed event_role values:

- primary_relief
- primary_escalation
- official_confirmation
- implementation_update
- weak_rumor_control
- denial_control
- mixed_conflict_control
- scheduled_macro_confounder
- data_gap_context

Event role is for stratification; it does not decide inclusion by itself.

## 10. Confounder fields

Each event should preserve source-side confounders where knowable before returns:

- scheduled_us_macro_within_10m
- scheduled_oil_release_within_10m
- major_semiconductor_catalyst_same_window
- major_china_trade_catalyst_same_window
- exchange_open_close_window
- market_closed_or_sparse_response_tape
- competing_geopolitical_headline
- source_clock_conflict

Unknown is distinct from false.

## 11. Session-handoff fields

Record mechanically from the event clock:

- us_session: premarket | regular | after_hours | closed
- europe_cash: open | closed
- asia_cash: open | closed_or_mostly_closed
- after_asia_cash_close: true | false | unknown

This tests timing mechanics without asserting intent to target a region's investors.

## 12. Training-only feature engineering rule

These categories may be explored on training data. Development permits one bounded
selection pass under the existing V2 evaluation split. Prospective holdout labels and
outcomes remain untouched until the feature family is frozen.

No category may be renamed, merged, or split because a holdout event performs badly.

## 13. Current hypothesis implications

Wave 1 already shows that these facts are not sufficient by themselves:

- relief-direction oil move;
- pre-event oil strength;
- a large five-minute oil reversal.

The next question is whether continuation concentrates in source-side states with higher
resolution/physical specificity and broad first-impulse confirmation, or whether Sep 24
remains an idiosyncratic semiconductor session after those controls.

A negative answer is an acceptable research outcome.

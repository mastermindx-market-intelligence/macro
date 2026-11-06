---
key: NEWS-IMPACT-W1C-DESIGN-RULINGS
question: >
  Integrating the nine W3 leaf modules exposed seven places where a module and its frozen
  A-design disagree: C5 cascade, X4 observation, M2 mechanisms, E3 eval receipt, T1 thesis,
  P7 prophet adapter and L6 agreement. For each one, does the code move to match the design,
  or does a seat ruling amend the design to match the code?
answer: >
  Three defects are code repairs and four are design amendments.
  CODE (wave w1c lanes).
  C5 audit reserve: n_audit_target = ceil(rate * review_capacity), computed exactly with
  Fraction(str(rate)) so that 0.14 * 50 is 7 and not 8. The starvation and leftover-slot
  clamps are unchanged.
  X4 matched window: the matched window is counted in trading sessions of the injected
  TradingCalendar, never in calendar days. The anchor is the session containing the
  information cutoff (inclusive), or the next session when the cutoff is outside regular
  hours. Both outcome endpoints are shifted back by the same whole number of sessions so that
  the matched end lands in the k-th session strictly before the anchor (default k = 1, an int
  in [1, 10]; anything else raises the new code BAD_MATCHED_WINDOW_SESSIONS). Each endpoint
  keeps its ET wall-clock time on the shifted session date, so a DST change is absorbed. A
  candidate counts only if both endpoints fall inside their shifted sessions and its UTC
  duration equals the outcome's. Otherwise the search steps one session further back (this
  covers early closes and DST-spanning windows). After 10 candidates it raises the new code
  MATCHED_WINDOW_NO_SESSION. matched_window_end <= information_cutoff follows by
  construction, and WindowGeometry keeps MATCHED_WINDOW_AFTER_CUTOFF as a defensive check.
  X4 outcome end (found at integration): when a landmark cutoff falls outside regular hours,
  for example 16:00 ET on an early-close day, the outcome ends at the close of the session
  containing outcome_start, not at the session after it. Before the fix, 2026-11-27 (close
  13:00 ET) produced an outcome from 2026-11-30T14:31Z to the 2026-12-01 close.
  L6 minimum-agreement gate: a template is usable only if every critical field was actually
  compared. A field with n_compared == 0 makes usable false, with the distinct reason
  not_evaluable. A null kappa at n_both_present >= 20 stays fail-closed, with the distinct
  reason kappa_undefined_single_category.
  DESIGN AMENDMENTS (recorded in phase1_designs/AMENDMENTS_W1C.md; the frozen packets are not
  edited).
  C5: the section 4.4 escalation table puts disputed_high_consequence_fact before
  material_issuer_relative_change. The W4 worked example binds to the 9.9998 usage
  snapshot. stop_not_material_delta stays in the closed enum but is documented as
  unreachable in v1.
  X4: section 4.7(h) follows its fixture: the coincident interval is
  [first_admissible_feed_receipt, outcome_end], inclusive at both ends.
  M2: Case C evaluates rules in the library's ascending priority order. T2-BRIDGE,
  T2-OPTION-CEIL and T2-AWARD are retired names: the bridge is a post-sweep step, an option
  ceiling never feeds a term, and T2-AWARD-POLICY is the library rule. Library gaps stay
  strategic_review and are v2 candidates. form=range maps to interval.
  E3: the committed schema wins in v1. Five design-versus-schema conflicts are disclosed as
  v2 candidates: dependence_dispute, two_way_cgm_interval, success_on_subset mapping to
  null, net_return_horizon pooling, and null_reason in display_text. In grading case 3 the
  pseudocode wins over the prose: a TAM routing miss is graded wrong_absence.
  T1: canonical JSON keeps ruling W3-R2 (sort_keys, compact separators, ensure_ascii=False,
  no trailing newline) inside engine/news_impact. The A1 citation (line 248) of
  engine/company_intelligence/contracts.py:127-140 is amended to "the same parameters minus
  the trailing newline". The live identity of a fact is (fact_key, polarity); the live-set
  rule at A1 line 233 and the Case 4 prose are amended to say so. The Case 1 sha values are placeholders. The
  next observation index is the furthest observed plus one, per the fixture.
  P7: WATCH is matched as a whole, case-sensitive token. channel_source is deferred to
  prophet_evidence.v2 with the enum [channel_hint, template_default, channel_mapping].
  L6 (design half): kappa_note at n = 0 lists the full enum. span_only_divergence, and
  abstentions recorded as metadata, are accepted as built.
rationale: >
  The rule is that physics and observable contracts beat prose.
  The C5 reserve is a sampling floor whose job is to never under-audit. The design itself
  is inconsistent: section 4.5 says floor, but its own section 7 Q6 default gives "12% of 24
  = 3", which floor(2.88) = 2 cannot produce. ceil reproduces Q6, and it guarantees at least
  one audit slot whenever the rate and capacity are positive. round() is ruled out because
  it uses banker's rounding on .5. Float ceil is ruled out because 0.14 * 50 evaluates to
  7.000000000000001, so ceil would give 8; 0.14 is inside the design's 10-15% band.
  The X4 matched window is a control for time of day. Three calendar days back can land on
  a Saturday, where there is no tape, and line 275 of the A4 design asks for the same
  session type. Counting back in trading sessions is the only construction that honours
  both conditions. The anchor is the cutoff's session, not the outcome's, because the
  outcome of a 16:00 landmark sits in the next session. Counting back from the outcome's
  session would land the matched window on the cutoff session itself, which is after the
  cutoff. The cutoff's own session is excluded because it can already carry the news
  reaction the window is meant to control for. k = 1 is therefore the nearest session that
  is both fully known at decision time and free of the event.
  The frozen case file W_obs_1600_landmark.json is not edited. Its superseded matched-window
  values move to the machine-readable overlay phase1_designs/AMENDMENTS_W1C.cases.json, which
  the observation tests load fail-closed.
  For L6, the design says exact agreement must be >= 0.90 on EVERY critical field. A field
  that was never compared has not met that bar, so treating it as passing would let an
  empty field mark a template usable. The usable flag therefore fails closed.
  For the four amendment-only defects, the code already does the physically coherent thing.
  For C5, the design's disputed row contains the material-change predicate, so under
  first-match the disputed row could never fire.
  For T1, nothing outside news_impact compares these hashes; the dislocation scripts'
  log_sha256 is an unrelated quantity. Changing the bytes would only invalidate the
  accepted W3 fixtures for no consumer.
  For E3, the committed schema is the contract that CI validates.
alternatives:
  - option: Re-open the frozen A-design packets and edit them in place.
    why_not: >
      The packets were accepted and integrated as frozen artifacts with byte-identical
      contract copies. An amendments file keeps the original reasoning auditable and makes
      every change a named, dated ruling.
  - option: Keep floor() for the C5 audit reserve, as section 4.5 literally says.
    why_not: >
      floor contradicts the design's own Q6 default (3 of 24) and drops the audit to zero at
      small capacities, which removes the reject-audit miss-rate endpoint exactly when the
      labelled set is small.
  - option: Keep the calendar-day matched-window offset and skip weekends with a rule.
    why_not: >
      A weekend rule still lands on holidays, and it ignores early closes. The injected
      TradingCalendar already models every one of those cases, so session counting is the
      simpler rule as well as the correct one.
  - option: Let L6 treat an uncompared critical field as passing (status quo).
    why_not: >
      A template with an empty critical field would be marked usable, so the agreement
      gate would pass a field nobody labelled.
evidence:
  - "research/prophet_v4/news_to_business_impact_20261006/phase1_designs/A5_cost/A5_cost.md:248 (floor) vs :584 (Q6 '12% of 24 = 3'); :230 first-match order; :234 disputed row embeds the material-change predicate."
  - "python3: math.ceil(0.14*50) == 8 while Fraction('0.14')*50 == 7; across capacities 1-600, rate 0.14 diverges at 10 capacities and 0.10-0.13 and 0.15 at none."
  - "phase1_designs/A4_transfer_obs/A4_transfer_obs.md:275 same duration and session-type; worked values 2026-09-26T13:30:00Z (a Saturday) at :907."
  - "engine/news_impact/observation.py:154 MATCHED_WINDOW_OFFSET_DEFAULT = timedelta(days=3); :626-627 calendar subtraction; :608 upcoming_session(outcome_start) overshoots when outcome_start is inside a session (python3 probe, early-close 2026-11-27 calendar)."
  - "tests/test_news_impact_observation.py test_dst_fall_back_week needs an injected 4-day offset to avoid MATCHED_WINDOW_AFTER_CUTOFF on a Friday landmark, which shows the calendar offset is wrong for ordinary weeks."
  - "phase1_designs/A6_labeler/agreement_spec.md sections 2-4: exact >= 0.90 on EVERY critical field; kappa >= 0.80 at n_both_present >= 20."
  - "engine/company_intelligence/contracts.py:127-141 canonical_json_bytes appends a trailing newline; engine/news_impact/thesis.py:259-268 does not (W3-R2); no cross-module hash comparison exists (grep log_sha256/owners_sha256 outside engine/news_impact)."
  - "PR #9067 W3 integration (commit 0980ee37); lane returns for C5, X4 observation, M2, E3 receipt, T1, P7 and L6 list each deviation."
affects:
  - "WS:PROPHET-NEWS-IMPACT"
  - "engine/news_impact/cascade.py"
  - "engine/news_impact/observation.py"
  - "engine/news_impact/agreement.py"
  - "tests/test_news_impact_cascade.py"
  - "tests/test_news_impact_observation.py"
  - "tests/test_news_impact_agreement.py"
  - "research/prophet_v4/news_to_business_impact_20261006/phase1_designs/AMENDMENTS_W1C.md"
  - "research/prophet_v4/news_to_business_impact_20261006/phase1_designs/AMENDMENTS_W1C.cases.json"
  - "research/prophet_v4/news_to_business_impact_20261006/phase1_designs/A4_transfer_obs/cases/*"
confidence: high
reversibility: easy
decided_by: fable-meta-ceo-seat-0e739467 (recovered fork 959095da) under the Chairman delegation of 2026-10-10
decided_at: 2026-10-13
---

## Do not redo

Do not edit the frozen A-design packets; amend them in AMENDMENTS_W1C.md. Do not reintroduce
round() or float ceil in the audit reserve. Do not offset the matched window in calendar
days, and do not anchor it on the outcome's session. Do not let a field with n_compared == 0
count toward usable. The frozen
news_impact_event.v1 contract (sha256 prefix 3edc7139) is untouched by every ruling here.

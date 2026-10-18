---
key: PROPHET-NESTED-PLAN-LINK-DUPLICATES
claim: Nesting the newer-plan anchor inside the clickable US plan-card anchor makes Chromium create duplicate
  card elements and ids despite one source row per plan.
falsifier: Render the exact pre-article templates and input identities in docs/pr-crops/prophet-plan-record-trust-20260916/nested-link-before.json
  with the actual episode map; show that Chromium produces 400 cards rather than the observed 420, or
  that nulling only newer links does not remove duplicates.
so_what: Before changing counts or deleting data to repair a plan-book pagination discrepancy, count actual
  DOM cards and unique ids. Use separate native anchors inside the opt-in record article and retain the
  real shared-pager browser proof.
kind: landmine
verified_at: '2026-09-16'
verified_by: Native process 91729; nested-link-before.json; process 34629 and browser-receipt.json after
  repair; existing structural regression test_record_navigation_has_no_nested_anchors_and_preserves_both_destinations.
scope:
- macro/templates/_prophet_card.html.j2
- macro/templates/_us_prophet_plan_cards.html.j2
- macro/templates/theme.js
confidence: verified
---

# Scope of the finding

The exact control holds all 400 real plan rows constant and changes only the ten newer-link fields. Source totals and publication drift are separate issues. The result does not assign the exact older screenshot count of 422 to this mechanism. After the opt-in article repair, the real browser and unchanged pager both count 400, with both navigation destinations preserved. Historical records are not deleted to make arithmetic agree.

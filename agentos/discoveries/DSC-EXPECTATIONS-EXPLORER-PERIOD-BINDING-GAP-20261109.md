---
key: EXPECTATIONS-EXPLORER-PERIOD-BINDING-GAP-20261109
claim: >
  At Macro b5674d8ef898e503d6164922654f5ff89be9981c, the breadth builder enforces known equal fiscal-period ends while the explorer prior-value, history and mover path do not establish the same complete period-and-snapshot binding.
falsifier: >
  Inspect scripts/build_expectation_surface.py and templates/expectation_surface.html.j2 at the same pin or a later qualified repair, then exercise period rollover, unknown period, exact mover selection and obsolete-response cases through the real explorer.
so_what: >
  Extend the incumbent explorer and loader with the existing comparable-pair rule and exact selection context before adding data-transition motion or treating a cross-period percentage as an estimate revision.
kind: landmine
verified_at: 2026-11-09
verified_by: >
  Exact-pin builder/template reads and Paper file 01M5EX8RTPR7YEZD2A144XED2S source mapping 47W-0/480-0; source ruling R1 and final readback in research/design_candidates/paper_audit_20261108/followup/.
scope:
  - scripts/build_expectation_surface.py
  - templates/expectation_surface.html.j2
confidence: verified
---

# Carry the comparable-period rule into the explorer

The breadth source's _comparable_pairs rule is reusable. Require equal known period_end for the same security, metric and raw horizon, and preserve prior_at, latest_at and source identity. A zero prior can count in breadth without providing a valid percentage denominator.

The explorer must either remain within the selected fiscal period or label and break each intentionally retained period segment. A new header above an unlabeled old-period series remains misleading even if a gap is drawn.

Selection and refresh have different behavior. Security, metric, period or explicitly selected snapshot changes retire the old result. A refresh of the same security/metric/period may retain dated last values while a newer snapshot loads; a changed period invokes the context-change rule. Commit labels and data together and ignore obsolete responses through the existing loader.

The four-capture streak was consistent with the producer's 1.2× leading-class threshold. The simpler latest-capture headline does not change that classification.

Paper references now document these requirements and show synthetic EN/ZH rollover states. This finding is source-level, not a live-browser incident or a shipped runtime fix. See [results](../../research/design_candidates/paper_audit_20261108/followup/RESULTS.md), [source rulings](../../research/design_candidates/paper_audit_20261108/followup/SOURCE_RULINGS.md) and build slices F01/F02.

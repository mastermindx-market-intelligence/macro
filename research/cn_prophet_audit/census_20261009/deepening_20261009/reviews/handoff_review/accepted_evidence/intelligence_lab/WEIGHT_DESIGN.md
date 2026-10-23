# Adaptive-weight evidence audit — frozen before execution

This is a bounded audit of the incumbent native `leg_weights_for` function, not a proposed new model or weight search. It uses the immutable October 9 scorecard and extracted source. It neither computes new returns nor changes production features or ranks.

Questions: (1) Are any current alt-data weights actually earned or zeroed? (2) Can a late scorecard alter a past calculation without a cutoff? (3) Does the validation family describe the feature being weighted? (4) Can a dense but weakly independent, unproven wrong-sign result zero a leg? (5) Do nonfinite values or non-Boolean verdicts cross the native evidence boundary?

The source maps the per-issuer margin-financing change feature to the validation family's whole-market financing/float timer. The experiment will distinguish a source-level estimand mismatch from an actually changed current weight. Counterfactual scorecards are synthetic and will be labeled individually. Current unchanged priors, if found, are a negative result to preserve.

The implementation implication is an evidence contract at the existing calibration reader: feature/target/horizon identity, matured-label cutoff, artifact and availability identity, strict numerical/verdict validation, and the same effective-evidence gate for positive and negative weight actions. This experiment does not choose a challenger, optimize weights, or establish that enforcing the contract improves returns.

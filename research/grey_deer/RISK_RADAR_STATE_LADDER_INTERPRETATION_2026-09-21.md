# Risk Radar State-Ladder Interpretation — Corrected Replay

Rerun protocol: `e9ff3d234df1f50137bfa38a50995a70f06c1164`.
Parity fix: PR #7632 / `7c6e35163c9f67087ffe174a7ab3810f47ce6a45`.

The pre-parity #7611 interpretation is superseded. Its most important error was not statistical technique; it graded state buckets produced by a replay that did not implement the shipped armed+confirm/Tier-B transition rules.

## What the corrected reconstruction supports

The five labels remain useful as a **plain-language progression**, but they are not five equally precise probability bins.

- **Calm / watch:** low-risk states with weak adjacent separation over longer history. Their configured state-only probabilities should not be read as evidence that they are statistically distinct buckets.
- **Caution:** still behaves like “risk building.” Modern H21 realized rate is **16.5%** against a 17.6% unconditional base and configured state-only 16%.
- **Elevated:** corrected modern H21 is **30.3% (n=33)**, not the stale replay's 11.1% (n=36). H5/H10/H21 point estimates are all above caution after parity repair. The cell remains below the preregistered n=100 evidence-depth floor; its 90% interval is wide, so 30.3% is descriptive rather than a high-confidence calibrated probability.
- **Risk-off:** remains the robust high-risk tier. Modern H21 is **43.8% (n=224)** versus configured state-only 33%.

Modern point estimates are monotonic at H5, H10, and H21 after parity repair. Full-history and 2006+ point estimates are not strictly monotonic at every adjacent step because calm/watch are close and elevated/risk-off can be nearly tied. That supports coarse zones, not five finely separated buckets.

## Product consequence

Preserve the existing user hierarchy:
- watch = early attention;
- caution = risk building;
- elevated = materially higher risk / confirmation developing;
- risk-off = strongest high-risk state.

Do not add a new persistence badge as if it were a separate risk tier. If evidence quality is surfaced, show **sample depth / calibration status**, especially for modern elevated, rather than another color or alarm.

## Calibration consequence

The corrected replay removes the strongest reason from the stale #7611 result to distrust elevated's direction: the modern elevated point estimate is now ordered correctly. It does **not** license a numeric retune.

The complete probability shown to users combines the state-only surface with the existing hot-scare conjunction bump. That combined displayed surface has not yet been evaluated under the corrected replay in this wave. Any probability change needs a separately frozen candidate and promotion evidence; issued/prospective forecasts remain a distinct, higher-authority evidence class.

## Authority

No live probability, band, score, weight, gate, gross, policy, sizing, ranking, ledger, or capital authority changes are made by this interpretation.

# Homepage mobile reflow — approved redesign, first bounded delivery

Operation: homepage-revamp-20260909-sol-001 / mobile-reflow.
Chairman approved the homepage audit and end-to-end implementation in the current conversation.
Skillpack: Mastermind@f3f2d9155796876009f2d427bfdecc7ee7b63e74.
Source base: macro@61cb600c966a7762fcfbe9ea77bfcf48ce017e5c.

## Outcome and scope
A visitor can read the homepage and reach all footer destinations on a narrow phone without unintended page-level horizontal scrolling. This is a layout repair, not a new homepage, entitlement change, analytics plane, or signal authority.

The live audit found footer overflow at 390px. A two-column footer probe fixed 360/390 but left another 320px overflow. Reproduce and identify that second cause before editing. Preserve every link and the existing shared public navigation family. Do not conceal the defect with global overflow suppression.

## Art direction
Light: retain the deliberately light public header and cool research canvas, with existing white cards. Dark preference: retain the same public acquisition art direction; the closing band/footer remains its existing dark contrast. This repair changes layout only, not material, palette, state semantics, or motion. EN/ZH must remain equally readable.

## Implementation order
1. Capture failing 320/360/390 widths and identify actual overflow after ancestor clipping.
2. Add a failing regression against the affected existing mobile rules.
3. Repair intrinsic sizing and footer reflow in the paired landing stylesheets; synchronize/cache-stamp through existing tools.
4. Run targeted existing tests and an actual browser matrix at 320/360/390/430/768/1440, EN/ZH and both preference settings.
5. Inspect screenshots, retain evidence and a durable handoff, then request independent review on one draft PR. Production acceptance requires a separate deployed browser check.

## Acceptance and stop
No unintended horizontal overflow; no missing destinations, clipped billing controls, duplicate chrome, global clipping patch, or change in pricing/entitlements. Existing reduced-motion behavior and template/site parity survive. A remaining narrow-screen defect is a failure, not a waived green result.

Held: acquisition-truth PR #6842, logo PR #6988 and the separately existing connected-research worktree remain in their owners' custody. Do not merge, rebase, or overwrite them as part of this branch.

# R32 tool and implementation scorecard

This is the build inventory for the eight-route design. **Native coverage** means editable tool/state specimens and contracts exist. **Reference coverage** means the specified local behavior runs in the delivered offline HTML. Production still reuses the existing component and service owners.

| ID | Tool and entry | Native coverage | Working reference | Production requirement |
| --- | --- | --- | --- | --- |
| I01 | Value details — hover, focus or tap | Value, source and freshness specimens | Hover/focus tooltip, Escape, Enter/tap sheet and source details | Typed observation receipt, entitlement and current/delayed/stale/error mapping |
| I02 | Calculation and curve shape — Curve or Scenario | Formula, node shocks, unavailable inputs and missing corporate vector | Parallel/spread arithmetic, four-node edits, invalid clearing, apply/undo and corporate withholding | Exact compatible instrument sensitivities, repricer ownership and full chart access |
| I03 | Mechanism evidence — Transmission or outlook | Consistent/countervailing/missing evidence, unranked paths and source overlap | Explanation selection, shared-input inspection, typed attachment and alternate outlook | Qualified observations and lineage; no support-count probability |
| I04 | Conditions — next test | Composer plus waiting, paused, match, invalidation, expiry and later-review states | Eleven deterministic fixture previews; frozen custom rule and correction review | Extend existing Alerts for the complete conjunction and evaluation clock; activation unavailable |
| I05 | Financing and cash timing — Credit | Reported annual buckets, missing dates, cash events, facility eligibility and late draw | Source inspection; declared Parent A cash/receipt timing; rejected wrong-borrower attachment | Current obligation roll-forward, legal cash pools and contractual settlement constraints |
| I06 | FX hedge inspector — Capital | Buyer mandate, duration, currency, tenor and missing quote states | Current annualized hedge edit and linked eligible USD comparison results | Entitled forwards, annualization and transaction costs; rolling hedge is not a guaranteed return |
| I07 | CDS conventions — Credit quote | Entity, seniority, clause, tenor, side and coverage | Inspectable native quote-convention drawer | Licensed instrument observations and a compatible cash-bond comparison |
| I08 | Issuer currency funding — Capital | Same borrower/tenor/base-obligation comparison | Editable issue yield and swap adjustment | Matched swap terms, collateral, fees and execution; no proxy substitution |
| I09 | Episode selection — Replay | Match criteria, contrary examples, valid-empty and unavailable states | Local filters distinguish references, zero eligible matches and absent history | Point-in-time registry and qualified matching; no future-outcome leakage |
| I10 | Next checks — desks or calendar | Schedule certainty, hypothesis and expected observation | Attach a typed next check while preserving unknown dates | Official schedules and publication/cancellation clocks |
| I11 | Model evidence — Scenario or Replay | Target, horizon, version, calibration and abstention | Qualification-inspection specimen with likelihood withheld | Approved model/evaluation owner and reproducible out-of-time evidence |
| I12 | Outcome fingerprint — record then reveal | Hidden/revealed, common horizons and unqualified cohort | Frozen hypothesis, step/reveal guard and synthetic response table | Admitted histories, complete outcome windows and dependence-aware evaluation |
| I13 | Market structure — Curve or evidence | Yield history, horizon conflict, curve participation, rule settings and unavailable distance | Prior-only volatility, authored levels, typed apply, mismatch preservation and exact source inspection | Aligned series/return basis, source clocks and production chart interactions |
| I14 | Buyer flows and funding — Capital or evidence | Transaction/revaluation reconciliation, missing funding origin and repo pipes | Buyer-flow attachment without duplication; funding counterpath | Matched holder, asset, currency, period and transaction provenance |
| I15 | Draft, save and compare — case or Saved | Typed additions, partial save, conflict, uncertainty, exact-read failure and frozen/latest columns | Apply/remove/undo; question-only demo receipt; original-operation recovery; conflict-form preservation | Extend existing Investigation v2 admission and resolvers; real retention is not enabled here |

## Shared acceptance decisions

| Situation | Required result |
| --- | --- |
| Tool returns an addition | Show its type, source, period, affected result and Inspect/Remove actions in the receiving draft. |
| Same addition is applied twice | Update the stable item; do not duplicate it. |
| Borrower, instrument or horizon conflicts | Preserve both the draft and unapplied fields; show the actual conflict and return to the source tool. |
| Main-page input is edited but not applied | Preserve it across navigation and distinguish it from the applied calculation. |
| Curve shape is replaced by parallel assumptions | Replace the shape item and recompute supported outputs together. |
| A known fresh invalidator coexists with missing evidence | Invalidation wins. Missing confirmation input does not suppress a known invalidator. |
| The fifth eligible close can match | Evaluate the close first, then expire if it does not completely match. |
| A later move reverses a matched path | Preserve the event, add a later continuation interpretation and keep causal attribution unresolved. |
| Question-only save succeeds | Reopen only the retained payload; list scenario, chart and rule exclusions. |
| A save result is uncertain | Recover the original operation receipt. Do not mint another operation to conceal uncertainty. |
| Exact saved revision cannot be read | Preserve identity and retry that revision; never substitute latest. |
| Concurrent save conflicts | Keep the custom question, next check and all local additions; no automatic overwrite or merge. |
| Phone screen or keyboard-only use | Keep navigation cancel, modal close, focus boundaries, visible units and reachable actions. |

## Verification scope

The final suites contain **65 rendered journeys** and **39 deterministic analytical checks**. They exercise desktop/tablet/phone routes, all fifteen tool entry families, critical edit and recovery paths, source-scope rejection, conditional-event semantics and modal keyboard return. The harness observed no page errors or HTTP(S) requests.

This scorecard does not treat unbound live sources, historical models, entitlement paths, server persistence, automated monitoring, or every production chart interaction as implemented. Those dependencies are recorded beside the corresponding tool so the implementer can make the exact feature available only when its owner supports it.

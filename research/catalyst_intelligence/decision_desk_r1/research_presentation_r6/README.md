# Company research presentation — R6

This increment continues original Macro PR #9611. It makes the existing v3 company research output readable through a pure frontend component and a separate synthetic preview. Draft/HOLD, R10/Company, Codex native adoption and DataOS ownership remain intact.

## Contract and source custody

The consumer accepts only `catalyst.stock_research_assessment.v3`. Its source owner is PR #9616 at `13b528d07e52680570a837f27571b64eb8176ca8`. Two original CLI outputs and their capture receipt are retained byte-for-byte under the adjacent `fixtures/stock_assessment_r8/` directory. The builder pins all three SHA256 values before producing output. It neither calls that owner nor recaptures accepted R4 evidence.

These are historical synthetic contract examples, including an invented peer cohort and prices. They are not current NVIDIA findings, licensed market observations or independently admitted owner state. The original R8 example predates the separate NewsImpact magnitude repair; this presentation does not derive or display a reduction claim from its weakening-condition flags.

## User capability

The view separates current company evidence from an unavailable or unrequested historical comparison; shows supplied peer returns with the observed/eligible cohort and window; preserves the entry owner's research state, strategy and horizon; and keeps unavailable advanced estimates explicit. It does not fuse facets into a score or infer economic direction, causal spillover, predicted leadership, a best entry or a clinical probability. NewsImpact-generated display wording remains exact and is labeled as an owner summary in both UI languages; it is not labeled as a verbatim primary-source quotation.

Primary copy asks the reader to review the evidence. Technical identity, source revisions and the distinct information/materialization/receipt/composition clocks belong in expandable detail. Numbers describe the supplied example and carry their comparison basis.

## Design and interaction contract

Archetype: research detail, using the existing Decision Desk shell, cards, fields and disclosure components. No new palette, token root, decorative edge, navigation family or runtime stylesheet is introduced.

**Dark treatment:** reuse the established graphite canvas, panel luminance and neutral hairlines. **Light treatment:** reuse white research panels, the cooler canvas and the existing light-specific card shadow. Both retain the same information order and missing-state meaning. EN/ZH controls and all UI-owned copy have parity; owner summary wording is labeled rather than silently machine-translated.

The preview's controls choose one of the two retained examples, language and theme. Replacing a packet is synchronous. Invalid replacement must remove the old content. Untrusted evidence enters only text nodes. The component performs no fetch, storage, authentication, navigation or publication operation. The standalone preview also disables network access through its content policy.

## Native integration boundary

A v3 packet contains a security/company and identity epoch, but no WMN generation or event revision binding. The current WMN contract cannot establish that relationship by matching a ticker or company alone. Therefore the live BioCatalyst host does not load or attach this preview. The build emits a paired reusable asset only; it does not add a production endpoint or script hookup.

The native/serving owners must supply an admitted revision/identity/source/entitlement mapping and correction-safe publication before live attachment. Source hashes are integrity references, not admission or rights receipts. Current/prior cut reconstruction is not proof of actual decision-time availability.

## Verification and retained proof

The existing Decision Desk CI job runs the new Node contracts through its pytest wrapper. New literal consumer, preview and test inputs are included in the same exclusive selection scope. Its four-minute budget, Python3.12/Node20 runtime, checks and all packing ceilings remain unchanged.

`build_preview.py` validates the exact captures before output and refuses to replace a different retained file. `verify_preview.py` exercises only the new research presentation, with no native source, authentication seam or external network. Its receipt separates exact owner examples from mutated security/negative witnesses. Actual test, review, browser and CI outcomes are recorded after execution in this directory and the existing PR checkpoint; these requirements alone are not proof.

Accepted R4 fixtures, captures, browser matrices and historical evidence are unchanged. Do not rerun the legacy default capture or write the previously denied legacy documentation.

## Contract review repairs

Read-only independent review identified and the parent repaired three consumer issues: lawful reduced peer timestamps were falsely rejected; generated NewsImpact summaries were labeled as original source text; and contradictory open-entry blockers or retrospective cohort formation could pass structural checks. Peer-only normalization now follows the producer's reduced/basic/week ISO forms and microsecond truncation, while assessment/envelope/entry timestamps retain their strict v3 grammar. Cohorts must form before the return window, retain supplied-research purpose and a positive age bound; an open entry state cannot carry blockers. These are presentation consistency checks, not digest authenticity or independent source admission. Mutated unit/browser cases are negative or compatibility witnesses, never retained owner captures.

## Observed local verification

The repaired source is covered by **26 Node contracts**, executed through the
existing pytest job with explicit TAP output. Local Python3.12 verification
completed with **19 passed in3.86s** (the Decision Desk wrapper suite plus the
actual shell/asset-emission test). These totals overlap; they are not added.

The six existing CI declaration, dependency closure, fallback-tier, packing,
ancestor-initializer and Decision Desk selection checks passed in255.43s.
Structural comparison against parent549aaee4 proves 869 -> 876 paths for the same
job, exactly seven additions, unchanged execution and every other job, and
unchanged PACKING_PROBES/PACKING_PROBE_MAX_PACKS. The original live host and R4
artifact paths are unchanged.

Current retained browser proof is **evidence_review_repaired/verification.json**,
SHA256 2be24676a02a625f9a587dfa7fed20c07a391803659fa4db1140247094010671.
Installed Python3.14/Playwright, Chromium151.0.7922.34 executed **9 behavior
checks,16 layout states,8 Chinese-font checks**, with no browser errors or
external network requests. The two hash-pinned captures are exercised in both
languages/themes at1440/390 widths, with expanded source details. Added mutated
cases test legacy peer timestamps and refusal of contradictory owner states.
The parent visually inspected the repaired dark/English desktop and
light/Chinese mobile PNGs. The older evidence/ directory remains historical
proof of the first implementation and is superseded for current-source claims.

Read-only independent architecture/contract review returned PASS_WITH_LIMITS
after the documented repairs. It did not run tests or grant formal approval.
Design-system enforce-added reported0 blocking findings; runtime style injection
and source-claim guards passed. The UI material-style detector found no new
governed style surface; these screenshots prove the component's rendering, not
a new design-system or native-runtime approval.

Full local contract-delta against parent549aaee4 passed with0introduced and
0inherited findings in509.31s; all three packing probes matched the parent.
Its log SHA256 is ed6ab79b19435e6063e35334b6f59c4d432638fef48d9fbd6da2d7d196d90d49.
AgentOS checked1911records with0errors and156warnings. The existing handoff
records those receipts. Hosted current-head results belong in canonical PR
checkpoint6291000963; local counts and advisory review do not substitute for
hosted Node20 acceptance.

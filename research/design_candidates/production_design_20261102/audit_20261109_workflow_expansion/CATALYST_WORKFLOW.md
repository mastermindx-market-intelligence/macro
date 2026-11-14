# Catalyst R3 workflow expansion

## Status and scope

Twelve native boards on three new pages extend the existing Catalyst file. This is a design candidate and a source-matched build contract, not a deployed feature or browser acceptance.

Native file: https://app.paper.design/file/01M6Y2VTQBVC9NA39HNG1DYWFH/p-6-0

Product source pin: `cf07e7a73334c646a09c043647c43e43ee6e4060`.
Procedure pin: `494d095813dad415938800fa0e4d2719497738fa`.
Owned source carrier: Macro PR10894, branch `design/paper-breadth-navigation-20261109-c2`.

## Delivered design

| Page | Board | Purpose |
|---|---|---|
| p-6-0 | 1K9-0 | Dark desktop: four-case ledger beside selected case |
| p-6-0 | 1NN-0 | Light desktop with readable semantic text inks |
| p-6-0 | 1R1-0 | 390px phone: all four cases in the first screen |
| p-7-0 | 22G-0 | Aster trial, company economics and price review |
| p-7-0 | 23C-0 | Morrow timing and regulatory-event review |
| p-7-0 | 248-0 | Kestrel financing, net cash and dilution review |
| p-7-0 | 254-0 | Lumen population, endpoint and safety comparison |
| p-7-0 | 260-0 | Sources and unresolved company-to-trial connection |
| p-7-0 | 26W-0 | Source changed, earlier payload unavailable |
| p-7-0 | 27S-0 | 390px English case view |
| p-7-0 | 29R-0 | 320px Chinese source-version recovery |
| p-8-0 | 2JD-0 | Native builder contract and three-stage motion storyboard |

## Behavior and destination contract

A row selection updates only the selected case; Review case opens its exact companion above. Return restores selected case, filter, view mode, scroll and invoker focus. The existing filtered-out selection, absent-requested-case and copy-failure states on p-3-0 remain authoritative. A source detail returns to its actual originating case; Aster is the pictured specimen, not a hard-coded return target.

The four companies, events and prices are fictional fixtures retained from the existing design. Save is unavailable with “Trial link needed” because the current ClinicalTrials.gov consumer does not prove an issuer-to-NCT join. The designer must not create NCT identity from company name or ticker. Open trial research uses the existing BioCatalyst destination with no invented selected NCT.

Eligible real trial records reuse R2 board 171-0 on p-4-0, the existing request controller, currentSubject, ownerKeyFor, ownerStorage and MDXAuth. Preserve NCT, mode, exact row key and publication_ref independently from the local note ID. No new account, storage, queue, monitoring or alert owner is introduced.

Saving is manual. Positive finite price validation and explicit currency, when applicable, remain R2 concerns. Confirm only after a matching readback. Failed/unavailable/corrupt reads are not empty storage. An unverified write may have succeeded; reconcile the original target before any retry.

## Changed-source state

Match authenticated owner, NCT, mode and exact row before comparing publication references. A changed publication_ref supports “Source version changed”; it does not prove changed clinical outcomes.

The delivered recovery specimen intentionally shows the earlier payload unavailable. Keep its exact saved reference and original condition, state why a diff cannot be displayed, and permit opening current evidence. Review condition opens existing R2 Edit with the saved basis intact. Do not silently rebase, create a reviewed flag, notify, or modify the record merely by viewing.

When both permitted versions are available, a future field comparison must preserve source null, missing, restricted and degraded states; absence is not deletion. The same owner and exact identity are required before any changed-field claim.

## Case-specific requirements

- Aster: sponsor endpoint assertion, pending full safety results, US rights, ex-US economics and financing remain separate. Values retained: example close $42.80, reference $41.20, DAILY close below $39.60 for manual review, estimated 11-month runway, expected full results 22 October (example date).
- Morrow: the 29 October company target is not a guaranteed event time. Earlier decisions, trading halts and price gaps can bypass a planned exit level.
- Kestrel: gross proceeds, net cash, dilution and runway are distinct. Do not invent unavailable financing values or clocks.
- Lumen: compare population, endpoint, study design, follow-up and safety. Competitor results do not establish this company's outcome.

## Visual and motion decisions

The workbench replaces repeated long reports with a four-row ledger and one selected-case reading surface. Detailed reasoning lives in named case/source destinations. All original boards remain.

Existing Inter typography, neutral panels and theme tokens are reused. Light status text was corrected from chart/status inks to --mx-light-ink-up and --mx-light-ink-warn. Measured green text contrast on the selected light panel improves from approximately 3.80:1 to 5.56:1; the general chart inks remain available for graphical marks.

The original example series and values are retained. Production display illustrations reuse lib/illus.py plus templates/illus.css and templates/illus.js. Existing ilx reveal draws once, settles to a static endpoint and immediately shows its final state under reduced motion. A proposed panel entrance uses 180ms opacity and an 8px translation. The native storyboard is a specification, not proof of runtime animation.

## Build order and acceptance

1. Bind the actual existing route and source identity; refuse an inferred issuer join.
2. Implement the compact workbench and exact context return without a new persistence owner.
3. Extend the existing publication-reference/comparison path.
4. Route eligible saves into R2; exercise readback and uncertain-write recovery.
5. Verify both themes, EN390 and ZH320, keyboard/back behavior, unjoined issuer, filtered selection, missing old revision, restricted field, account change and failed readback.

Native screenshots and JSX were read back for all twelve boards. The phone case and Chinese 320px recovery were visually inspected with readable wrapping and visible actions; desktop light/dark, source and comparison views were also inspected. Native Paper is not a browser execution environment. Real browser, account and production acceptance remain owed to the implementation.

## Retention

Original pages p-1-0 through p-4-0 still contain 10, 5, 8 and 1 boards respectively (24 total). The other writer's p-5-0 AGENT README was not edited. Existing R2 save and selected-case recovery were reused, not reimplemented. No original resource was archived or deleted. Archive/delete and style/token operations held by the adapter were not invoked.

## Continuation

Catalyst design phase saved; the subsequent Intraday, shared-state and bounded AI/Comparison phases are included in the final README and verification packet. The broader implementation programme remains open.


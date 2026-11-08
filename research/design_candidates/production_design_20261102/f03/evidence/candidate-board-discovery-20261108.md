# Exact candidate-board discovery — 8 November 2026

## User task and source

A builder following an audit's exact board ID should be able to find the corresponding design and understand its status. The D05 page-pointer correction made the proposed p6 page discoverable, but searching **GPL-0** or its full file/page/board tuple still could not find that proposed board.

This bounded follow-on extends the existing F03 returned-observation model and page-keyed view. Its source baseline is `4981fe2dab3912666769c0ef275249f73894b6b9`; governing Mastermind procedure remains `5c3d3885234358aefb97ecdbc59be0864df14f8b`. The same [immutable D05 observation](https://github.com/mastermindx-market-intelligence/macro/blob/235d60d912589e630988b67eee6ba63be37c5712/research/design_candidates/production_design_20261102/f03/evidence/d05-sector-reference-observation-20261108.md) and [native readback](https://github.com/mastermindx-market-intelligence/macro/blob/235d60d912589e630988b67eee6ba63be37c5712/research/design_candidates/production_design_20261102/f03/evidence/d05-sector-reference-readback-20261108.json) establish the parent-bound locator. Their original source head and observation time are retained.

## Resulting behavior

The optional `return_observation.candidate_board_id` is **GPL-0** for D05:

| Role | Exact identity |
| --- | --- |
| Bounded proposed candidate | `01M6FAXA774QT1VRDMAG7DFQ2W / p-6-0 / GPL-0` |
| Provisional Readme | `01M6FAXA774QT1VRDMAG7DFQ2W / p-3-0 / BML-0` |
| Retained original reference | `01M6FAXA774QT1VRDMAG7DFQ2W / p-1-0` |

Assignments and Paper references accept the bare candidate board ID or the slash-delimited full tuple. Assignment cards explain the match with an **Observed candidate board** label. HTML detail and generated D05 Markdown show the complete identity. English and Chinese reference/detail copy explains that the action opens the **containing Paper page**, where the user selects the displayed board ID. A direct board URL or automatic selection is not claimed.

The existing query, owner and originating view are retained through assignment detail and Back. Returned locators do not enter the inventory's board-focus route: no `board=GPL-0` or nonexistent board DOM target is generated. Distinct candidate and Readme claims may share a page without duplicating the page result. Equal short board IDs in different compound identities remain distinct.

## Validation and compatibility

Missing and explicit-null `candidate_board_id` have the same legacy page-only behavior, including search text, rendered identity and claims. A non-null locator must be a string matching the existing board grammar `[A-Za-z0-9]+-[A-Za-z0-9]+` and have its own exact canonical candidate URL/file/page. Whitespace, terminal newlines, URL/path/fragment characters, markup, backticks and non-string values are rejected. The JavaScript projection additionally checks exact canonical URL equality, preventing end-of-line regex normalization.

The Python builder validates all rows before applying any, retaining atomic rejection. The read-only JavaScript projection suppresses a malformed candidate claim while preserving independent Readme and retained-reference claims. Syntax checks alone do not establish Paper membership; populating this field requires the exact immutable observation above.

The outer evidence-field allowlist, strict immutable Macro source URL rule, draft RIG state and null approval receipt remain intact. No source-store, registry, page census, artboard census, canonical route, ownership field or native-operation record was added.

## Actual verification

[Detailed verification output](candidate-board-discovery-verification-20261108.json) records the commands and results:

- **129** return/identity checks passed.
- **69** directory source-logic probes passed.
- **26** structural-evidence checks passed.
- All nine frozen artifact digests and all 36 retained assignment-field digests passed.
- The source diff changes only D05's `candidate_board_id` within assignment data. The provenance JSON, original eight observations, native ledger, historical root manifest, 348 routes, nine noncanonical deltas and all 301 NOT_DISPATCHED actions are unchanged.
- The two curation mirrors have identical bytes. Generated source views use the same observation.
- A source whitespace inspection emitted no diagnostics.

The tests cover exact/incorrect compound tuples, equal short IDs in separate files, same-page distinct roles, absent/null compatibility, malformed values and candidate URLs, atomic rejection, English/Chinese identity labels, retained query/owner/Back context, and the absence of invented board-focus or board-URL targets. These are source-logic checks, not a real browser or screen-reader simulation.

## Browser proof and release boundary

A real-browser attempt used the selected Chrome extension and an owned temporary loopback server for this exact generated directory. The browser reported **net::ERR_CONNECTION_REFUSED**. Read-only device discovery returned multiple online hosts without an established binding to that browser; no device was guessed or used for remote execution. The owned preview process and the temporary browser error tab were closed. No alternate browser/control path, hosting deployment, credential inspection or access change was attempted.

Consequently, actual rendering, responsive layout, keyboard/focus behavior and accessibility remain **UNVERIFIED**. The existing CSS wraps code identities and provides minimum 44px assignment-result link targets, but source inspection is not visual acceptance. Hosted CI and deployment were not claimed.

F03's warned Paper original remains **READ ONLY / NO MODIFY**. The existing recorded Draft/HOLD and stacked CI restrictions remain. The original candidate observation remains provisional, and no whole D05 build acceptance, RIG approval, runtime admission, native clone/move/archive, PR control change or production release follows from this search feature.

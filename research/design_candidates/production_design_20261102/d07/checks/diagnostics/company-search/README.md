# Company search context diagnostics

Observed on 4 November 2026. This is a narrow dependency read of Terminal `2ded360882b9c721e690907ff363b553781fb920`. Other D07 route, financial and Earnings source pins retain their stated epochs. The probe imports unchanged `companySearchContext.ts` and `analysisSymbol.ts` with native TypeScript stripping, after verifying Git blob, SHA-256 and byte length. [Exact inputs](sources.json)

## Reproduce

```sh
node probe.mjs > results.actual.json
cmp results.json results.actual.json
```

Node 24 reproduces **35 cases, 41 functional assertions and 6 integrity checks**. Browser and history-restoration assertions in this script are zero. [Saved result](results.json)

| Contract | Reproduced behavior and boundary |
| --- | --- |
| Typed query | Outer whitespace is trimmed before validation. Interior controls are rejected. The length limit is 160 JavaScript UTF-16 code units, so 80 emoji fit and 81 exceed the bound. Preserve CJK and correctly encode `&` and `#`. |
| Selected listing | Canonical listing identity must match the strict shape. A padded/lowercase identity, missing query, array or extra authority field is rejected by the selection decoder. A query remains descriptive context. |
| URL context | Preserve the existing distinction between absent, empty and repeated query parameters. Use the existing URL builder and exact `symbol` identity. |
| Trading currency | Accept an exact matching fund ticker and a valid uppercase three-letter `quote_currency`. Statement currency cannot substitute for trading currency. |
| Venue | Use the listing's qualified equity market field. Wrong-listing and missing/malformed metadata remain unavailable. SV07 deliberately reproduces the current acceptance of a whitespace-only market string. This requires a usable-venue qualification by the existing owner. |

The separately inspected `ShellSearch` lifecycle stores `mmxCompanySearch` on the existing browser history entry, preserving the entry's other state. Restoration requires a valid selection and an exact matching stored href. Cancelling the dialog clears that marker. Committing opens the chosen Analysis listing with `company_query`. Those lifecycle claims come from source inspection and the separate served-browser sequence. This script proves the context helpers. [Live preview, commit, Back and cancel observations](../../../baseline/continuation-20261104/README.md) · [Return-owner contract](../../../JOURNEY_RETURN.md)

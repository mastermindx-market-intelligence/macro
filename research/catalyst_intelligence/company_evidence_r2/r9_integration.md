# BioCatalyst R9 and Company evidence integration

Date: 2026-10-20

Carrier: [Macro draft PR #9662](https://github.com/mastermindx-market-intelligence/macro/pull/9662)

## Source composition

The original Company evidence head `430234957531693b6b13f026a161e28542086a82` is combined by a real two-parent merge with the published BioCatalyst R9 repair `76f5a28d5d8e8200fbb9c36882f158541809ec3e` from draft #6712. The read-only merge preflight and applied merge had no conflicts. The staged merge tree before the integration fixture update was `bbc1d7a1499a047f26cea1fdee87b3fc39d2a2ce`.

R9 remains the source of the adopted identity-cut, timing, estimate-coverage, historical-read, error-classification and template/site repairs. Its managed continuation already adopted the four preserved test changes. This integration does not edit or claim custody of the retired Fable checkout.

The one additional integration change gives the existing synthetic Company evidence API fixture a distinct vendor-alias cut member, hashed from its explicit synthetic alias records. Company event 1.1.0 source context and microsecond preservation remain intact; the composed input uses the closed WMN v2 owner envelope. The external WMN response and historical v1 artifact bytes remain unchanged.

## Executed checks

The first combined run reported 144 passed and eight failures: two synthetic API fixtures omitted R9's required alias member, and six API/worker cases lacked exact fixture bytes excluded by the sparse checkout. Five small existing ClinicalTrials.gov fixtures were restored byte-for-byte from the Git index. They are repository fixtures, not generated owner evidence.

After the fixture update and exact restoration, the six focused suites passed: **152 tests**, exit 0, 12.49 seconds. Command:

```sh
python -m pytest -q --tb=short tests/test_company_catalyst_public_evidence.py tests/test_company_intelligence_catalyst_event.py tests/test_biocatalyst_research_priority.py tests/test_biocatalyst_what_matters_next.py tests/test_biocatalyst_wmn_api.py tests/test_biocatalyst_wmn_publication.py
```

The two curated CI declaration and import-closure checks also passed, exit 0, 191.63 seconds:

```sh
python -m pytest -q --tb=short tests/test_ci_pack.py::test_the_curated_exclusive_set_is_actually_declared tests/test_ci_pack.py::test_curated_exclusive_scopes_cover_their_own_import_closure
```

The new integration test diff has no whitespace errors. A full diff against the pre-R9 Company head reports four inherited Markdown hard-break lines in R9's README; the adopted source report is preserved. Runtime warnings concern the installed Starlette/httpx compatibility path and cleanup of an unrelated old pytest Chromium directory.

## Boundary and next implementation

**DRAFT / HOLD.** This checkpoint establishes composed local source behavior. It adds no native admission receipt, entitled deployment proof, source-rights qualification, scientific validity or trading authority. The existing unsupported-base hosted CI and prior preview packaging boundary must be reconciled at supported release adoption; this integration does not waive or alter those gates.

The next implementation stays in the existing Bio publication owner: durably invalidate current WMN eligibility when a corrected owner cut is accepted, prevent an earlier candidate from later promoting, and preserve readable historical trial facts. A failed corrected build must leave list/detail unavailable across restart. That correction fence is not implemented by this merge checkpoint.

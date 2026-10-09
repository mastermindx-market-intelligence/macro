# Private settlement cohort and released financing input contract

This local Codex continuation implements the first executable H3 data gate specified in the adopted H1–H5 design. It reuses `engine/treasury_auction_primitives.py` for exact private cash arithmetic. It introduces no source certifier, authority owner, pricing model, liquidity engine, collector, dataset freeze or research execution registration. Independent source/accounting/PIT acceptance is still owed.

`engine/treasury_settlement_ledger.py` accepts normalized cash claims supplied by the existing qualified source owner. Each claim identifies the settlement day and cohort, Bill/CMB or coupon channel, private marketable investor scope, cash USD basis, source digest and extraction locator, and the actual economic payment keys. CUSIP or row ID alone is not an economic payment identity.

An imported upstream inventory must bind every exact claim, value, basis, source, clock and scope through a canonical SHA-256, name the complete expected component set, preserve the independent acceptance reference and certify the complete private universe and buyback/redemption non-overlap. Its availability cannot precede its claims or exceed the decision cutoff. The module checks those declarations; a constructor, boolean or reference string never proves that external acceptance actually occurred.

For each channel separately, the supplying owner must enumerate private proceeds already excluding SOMA, private cash redemptions and funded buyback payments not already included in redemptions. Every missing category is unknown. A category-wide zero requires a qualified source observation and cannot coexist with nonzero/detail rows. Different component IDs carrying the same payment key fail the gate, including a buyback included in redemptions. Gross offered face, par debt accounting, all-holder quantities and subtracting SOMA again fail the private-cash contract. Synthetic and auction-result-role inputs cannot be admitted as prior-known cash features.

Only a fully satisfied imported contract invokes the existing exact math. The output separates `BILL_CMB` and `COUPON` net cash, retains negative net financing when legitimate, keeps combined cash null so opposing channels cannot be hidden, and always retains null reserve pressure and probabilities. `SOURCE_CONTRACT_SATISFIED` is a structural result, not actual independent qualification or a prediction verdict.

## Financing vintages

The pure selector keeps the effective date, exact vintage identity/digest, source/method, actual body receipt and knowledge upper bound separate. A source owner may supply a verified exact publication timestamp or explicitly use a qualified official body-availability upper bound. The latter preserves `release_at = null`; it cannot invent publication time. Release/availability, body, economic and knowledge clocks must all be eligible and causally compatible.

The selector retains the latest eligible economic date and qualified release/availability vintage. Re-fetching an immutable vintage preserves its earliest eligible availability; it cannot replace a genuine later revision or freshen its first receipt. Later revisions remain excluded before their availability. Contradictory same-release vintages are withheld. Weekly interpolation, missing clocks, result-role/synthetic input and future effective dates are ineligible. The selector supplies released TGCR/SOFR/IORB and explicitly qualified reserve/ON-RRP/dealer/MMF vintages; it does not replace the canonical liquidity baseline or imply an entitlement to MMF data.

## Actual original-source replay

`funding_audit/qualify_funding_casebook.py` verifies the original twelve source hashes and causal receipt clocks through the accepted funding audit, binds the immutable original casebook hash and executes the new gate. It imports no unsupported private cash claim and reads no funding outcome value. At the adopted illustrative `2026-10-05T16:00:00-04:00` cutoff, zero original receipts are eligible, no complete private inventory is accepted and no required baseline vintage is qualified. The generated `verification/local_codex_20261008/H3_INPUT_COVERAGE.json` remains `INSUFFICIENT_PIT` with all predictive outputs null. Its freeze and prospective start remain unadmitted.

Reproduce from the repository root:

```sh
python3 research/sovereign_auction_pressure/funding_audit/outcome_blind_funding_audit.py --check
python3 research/sovereign_auction_pressure/funding_audit/qualify_funding_casebook.py --check
python3 -m pytest -q --tb=short tests/test_treasury_settlement_ledger.py tests/test_treasury_auction_primitives.py
```

Golden accounting tests are explicitly fixtures. They show exact opposite-signed bill/coupon cash and reject double counting, missing inventories/zeros, altered digests, future clocks, improper SOMA/par scope, unaccepted certificates, late IORB releases and same-clock conflicting rate revisions. They are not real data acceptance, empirical performance or a production dataset.

Actual complete cash claims, source-independent acceptance, canonical liquidity and eligible released baseline acquisition remain critical data dependencies. SLF-006 NO-GO, D2 FAIL and Terminal KILL remain unchanged. No new challenge outcomes, model fit, calibration, prospective timer, live risk integration or release occurred.

# CLNN — ATM / prospectus supplement, registration + instruments + cash_funding

Dossier A0-0 (SPEC_A0 §2). Expectations are fixed here BEFORE the lineage
harness runs; the source-supported answer is stated from the reference pack
and the retained source plane only, and every mismatch with the served state
is recorded under `## Findings` verbatim. This dossier fixes acceptance inputs only.

```yaml
schema: capital_structure.reference_dossier.v1
ticker: CLNN
issuer_id: sec:cik:0001822791
cik: "0001822791"
registry_name: Clene Inc.
binding_status: qualified
verdict_hint: accept
gap_ids: []
j5_cutoff: "2026-10-17"
expectations:
  - path_id: clnn:atm_programme_remaining
    family: registration
    rule_id: form_s3.I.B.6
    rule_example_id: cdi_116_22_capacity_measured_against_amount_offered
    rule_class: staff_interpretation
    unit: usd
    expected: null
    gap: >
      neither the ATM programme's authorized amount nor its cumulative sales is
      served by the generation at the dossier cutoff, and the retained 424B5
      takedown texts carry no admissible-grade extraction of those amounts, so
      the dollar value cannot be asserted from permitted evidence
    arithmetic: authorized_programme_amount_usd - cumulative_atm_sales_usd
    operands:
      - name: cumulative_atm_sales_usd
        ref: manifest:cs:6999cfd4d14be160fe96e8aebe660a26b1d01ba3bab92c5a3a6265aaf4d5dd48/root:45e530a93ed6bf0e12faa5a8cebf271b0f6ee4f324e0c041944016e75f98835d
        text_sha256: 45e530a93ed6bf0e12faa5a8cebf271b0f6ee4f324e0c041944016e75f98835d
        note: >
          424B5 accession 0001437749-26-014935 (filed 2026-05-05), complete
          submission root span; one takedown of the ATM programme
      - name: cumulative_atm_sales_usd_later_takedown
        ref: manifest:cs:0004ec0800f69e4d173ef474ebc1fd06657ad54e3140441b9f9c54a80a420ed8/root:a85b163d0b70319cb582c57985c29e7849d20929bcd5758242b00dfb896fbecb
        text_sha256: a85b163d0b70319cb582c57985c29e7849d20929bcd5758242b00dfb896fbecb
        note: >
          424B5 accession 0001437749-26-030521 (filed 2026-09-16), complete
          submission root span; a later takedown of the same programme
negatives:
  - name: programme_usage_not_established
    expect: "detail:Registration observed; programme usage not established"
    reason: >
      standing phrase: when registration is observed but no ledger establishes
      programme usage, the aggregate renders this phrase and no sum is
      computed from partial inputs
  - name: issuer_outside_coverage_is_refused
    expect: "detail:issuer not covered"
    reason: >
      the state API refuses an uncovered issuer with _private_error 404 detail
      "issuer not covered" before any evaluation, so an uncovered issuer can
      never render a value
```

## Identity

`identity_for(pack, "CLNN")`: ticker CLNN, CIK 0001822791, issuer_id
sec:cik:0001822791, registry name `Clene Inc.` (submissions name identical),
Nasdaq, ticker as of 2026-10-13, label_drift false, case_supply supplied,
qualification `qualified`.

## Source packet

ATM takedown filings, retained bytes (source ledger at the dossier cutoff):

- form 424B5, accession `0001437749-26-014935`, filed 2026-05-05,
  document `complete-submission.txt` sequence `0`, byte_length 805003,
  manifest_id `manifest:cs:6999cfd4d14be160fe96e8aebe660a26b1d01ba3bab92c5a3a6265aaf4d5dd48`,
  span_id `root:45e530a93ed6bf0e12faa5a8cebf271b0f6ee4f324e0c041944016e75f98835d`,
  text_sha256 `45e530a93ed6bf0e12faa5a8cebf271b0f6ee4f324e0c041944016e75f98835d`
- form 424B5, accession `0001437749-26-014937`, filed 2026-05-05,
  manifest_id `manifest:cs:a459451d65db9038527b3689441343e8c72b2933c5d72b71e6571991cef13773`,
  span_id `root:2c8e70586395ed8f180f42b96fecf8c11131fddc97df776075d20e141cde0c5f`,
  text_sha256 `2c8e70586395ed8f180f42b96fecf8c11131fddc97df776075d20e141cde0c5f`
- form 424B5, accession `0001437749-26-030521`, filed 2026-09-16,
  manifest_id `manifest:cs:0004ec0800f69e4d173ef474ebc1fd06657ad54e3140441b9f9c54a80a420ed8`,
  span_id `root:a85b163d0b70319cb582c57985c29e7849d20929bcd5758242b00dfb896fbecb`,
  text_sha256 `a85b163d0b70319cb582c57985c29e7849d20929bcd5758242b00dfb896fbecb`

Rule source (reference pack source `sec_cdi_securities_act_forms`,
staff_interpretation, qualified): spans `cdi_securities_act_forms_q116_22`
(interpretation date 2010-08-11) and `cdi_securities_act_forms_q116_26`
(interpretation date 2026-03-19, authority_kind `staff_position_not_rule`)
for the ATM-supplement-continuation boundary.

## Mandatory numerical path

`clnn:atm_programme_remaining` — ATM programme remaining = authorized
programme amount − cumulative sales (ledger). The scenario half of this
archetype (one ATM action producing a supply row and a cash row as distinct
records, `funding_gap_coverage` scenario-only) is exercised by the A0-1
harness against `compose_scenario`; the dossier fixes the ledger-side
operands above. The dollar value is NOT asserted here: see the gap on the
expectation row and `## Findings`.

## Negatives

1. `programme_usage_not_established` — the standing phrase
   "Registration observed; programme usage not established" renders and no
   sum is computed when usage is not established.
2. `issuer_outside_coverage_is_refused` — 404 detail `issuer not covered`.

The SPEC's third negative for this archetype (evaluate with inputs
unavailable → 409 with components) belongs to the scenario evaluate endpoint
that lands with U1B-2; it is recorded here as pending that landing, not as a
failed expectation.

## J5 cutoff

`2026-10-17` — the served state generation's as_of instant is
2026-10-17T14:45:44.820502Z; the then-known view at that cutoff and the
"came after" disclosure for the 2026-09-16 takedown if a J5 date before it
is picked.

## Findings

- Served generation `state_bundle:cs:2be6a6164f1d6fd9a5bd5c89375d21b6`
  (as_of 2026-10-17T14:45:44.820502Z) publishes NO registration path records
  for CLNN (`records` empty, provenance support `partial`, support limit
  `lifecycle_coverage_unavailable`) and `registered_amount_remaining` /
  `remaining_offering_dollars` / `instrument_terms` are in the family's
  unavailable list. The instruments and cash_funding families are absent for
  CLNN entirely, so the supply-row/cash-row separation has no served
  counterpart yet.
- `path_evidence` for CLNN is empty and the bundle's evidence_index holds
  zero entries for sec:cik:0001822791: the three 424B5 locators above are
  ledger-retained but not yet served evidence.

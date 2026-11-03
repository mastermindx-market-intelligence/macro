# AIR — automatic shelf (WKSI), registration archetype

Dossier A0-0 (SPEC_A0 §2). Expectations are fixed here BEFORE the lineage
harness runs; the source-supported answer is stated from the reference pack
and the retained source plane only, and every mismatch with the served state
is recorded under `## Findings` verbatim. This dossier fixes acceptance inputs only.

```yaml
schema: capital_structure.reference_dossier.v1
ticker: AIR
issuer_id: sec:cik:0000001750
cik: "0000001750"
registry_name: AAR CORP
binding_status: qualified
verdict_hint: accept
gap_ids: []
j5_cutoff: "2026-10-17"
expectations:
  - path_id: air:remaining_registered_capacity
    family: registration
    rule_id: form_s3.I.B.6
    rule_example_id: cdi_116_22_capacity_measured_against_amount_offered
    rule_class: staff_interpretation
    unit: usd
    expected: null
    gap: >
      no admissible registered-amount operand: the served generation publishes
      no registration path record for AIR and the C2x usage ledger is absent
      from the tracked tree at the dossier cutoff, so the dollar amount cannot
      be asserted from permitted evidence
    arithmetic: registered_amount_usd - securities_actually_sold_usd
    operands:
      - name: registered_amount_usd
        ref: manifest:cs:c9d7f0471af1678dba042210115585ddcf3838f361171e31f190f1536b31f79a/root:9fa035712b8175fd1f787f4ed5e9e55cba29ca794a90f442f73f96c3e5734ca0
        text_sha256: 9fa035712b8175fd1f787f4ed5e9e55cba29ca794a90f442f73f96c3e5734ca0
        note: >
          S-3ASR accession 0001104659-26-085644 (filed 2026-07-22), complete
          submission root span; the fee-table amount inside it is not served at
          an admissible grade by the generation at the dossier cutoff
negatives:
  - name: baby_shelf_supplement_exceeding_remaining_capacity
    expect: ineligible
    state: ROUTE_STATUSES
    rule_id: form_s3.I.B.6
    reason: >
      reference-pack negative example cdi_116_22_capacity_measured_against_amount_offered:
      a prospectus supplement whose amount exceeds the remaining one-third
      capacity is not permitted; the measured quantity is the amount offered in
      the supplement, measured immediately prior to the takedown, and
      securities actually sold count against later takedowns
  - name: f3_route_has_no_rule_pack_witness_for_a_us_domestic_issuer
    expect: unknown
    state: ROUTE_STATUSES
    rule_id: form_f3.I.B.5
    reason: >
      the reference pack records gap foreign_issuer_f3_witness (no qualified
      foreign-issuer F-3 case); AIR is a NYSE domestic registrant, so no F-3
      witness exists for it and the F-3 route must render unknown, never
      eligible
```

## Identity

`identity_for(pack, "AIR")`: ticker AIR, CIK 0000001750, issuer_id
sec:cik:0000001750, registry name `AAR CORP` (submissions name identical),
NYSE, ticker as of 2026-10-13, label_drift false, case_supply supplied,
qualification `qualified` — "company_tickers.json and the submissions index
agree on CIK and registrant name".

## Source packet

Automatic-shelf filing, retained bytes (source ledger at the dossier cutoff):

- form S-3ASR, accession `0001104659-26-085644`, filed 2026-07-22
- document: `complete-submission.txt`, sequence `0`, byte_length 1794697
- manifest_id `manifest:cs:c9d7f0471af1678dba042210115585ddcf3838f361171e31f190f1536b31f79a`
- span_id `root:9fa035712b8175fd1f787f4ed5e9e55cba29ca794a90f442f73f96c3e5734ca0`
- text_sha256 `9fa035712b8175fd1f787f4ed5e9e55cba29ca794a90f442f73f96c3e5734ca0`
- canonical_url `https://www.sec.gov/Archives/edgar/data/1750/0001104659-26-085644.txt`

Rule source (reference pack source `sec_cdi_securities_act_forms`,
staff_interpretation, qualified): span `cdi_securities_act_forms_q116_22`,
interpretation date 2010-08-11.

## Mandatory numerical path

`air:remaining_registered_capacity` — remaining registered capacity on the
automatic shelf = registered amount − ledger usage (C2x), with the fee-table
operand span of the S-3ASR above. Rule: Form S-3 I.B.6 arithmetic as fixed by
the pack example `cdi_116_22_capacity_measured_against_amount_offered`
(securities actually sold count against later takedowns; measured quantity is
the amount offered). The dollar operands are NOT asserted here: see the gap on
the expectation row and `## Findings`.

## Negatives

1. `baby_shelf_supplement_exceeding_remaining_capacity` — route
   `ineligible` (ROUTE_STATUSES) when a supplement's amount exceeds the
   remaining one-third capacity (pack negative example cdi_116_22).
2. `f3_route_has_no_rule_pack_witness_for_a_us_domestic_issuer` — route
   `unknown` (ROUTE_STATUSES), never `eligible`, for the witnessless F-3
   route (pack gap `foreign_issuer_f3_witness`).

## J5 cutoff

`2026-10-17` — the served state generation's as_of instant is
2026-10-17T14:45:44.820502Z; J5 (mode bar, On a date) uses the then-known view
at that cutoff and the "came after" disclosure for anything observed later.

## Findings

- Served generation `state_bundle:cs:2be6a6164f1d6fd9a5bd5c89375d21b6`
  (as_of 2026-10-17T14:45:44.820502Z) publishes NO registration path records
  for AIR: the registration family's `records` list is empty and
  `registered_amount_remaining`, `remaining_offering_dollars`,
  `active_or_executable_offering_capacity` and `wksi_eligibility` are all in
  the family's unavailable list (provenance support `partial`, support limits
  include `lifecycle_coverage_partial` and `offering_role_unknown`). The
  source-supported path above therefore has no served counterpart yet.
- `path_evidence` for AIR is empty and the bundle's evidence_index holds zero
  entries for sec:cik:0000001750, so the S-3ASR operand locator above is
  ledger-retained but not yet served evidence.
- The C2x usage ledger (transaction observations) is absent from the tracked
  tree at this commit, so the usage operand cannot be cited at all.

# QNCX — small-float (baby shelf) rule, registration archetype

Dossier A0-0 (SPEC_A0 §2). Expectations are fixed here BEFORE the lineage
harness runs; the arithmetic below reproduces the reference pack's
$10M / $2.5M / $7.5M / $5M rule example exactly. Every mismatch with the
served state is recorded under `## Findings` verbatim. This dossier fixes acceptance inputs only.

```yaml
schema: capital_structure.reference_dossier.v1
ticker: QNCX
issuer_id: sec:cik:0001662774
cik: "0001662774"
registry_name: IRulya Therapeutics Inc.
binding_status: qualified
verdict_hint: accept
gap_ids: []
j5_cutoff: "2026-10-17"
expectations:
  - path_id: qncx:baby_shelf_offerable_total
    family: registration
    rule_id: sec_cdi.116.23
    rule_example_id: cdi_116_23_concurrent_continuous_offerings
    rule_class: staff_interpretation
    unit: usd
    expected: "7500000"
    gap: null
    arithmetic: one_third_limit_usd - sold_to_date_usd
    operands:
      - name: one_third_limit_usd
        pack_span: cdi_securities_act_forms_q116_23
        text_sha256: a85fb5d9d3a8132b7782e84e59c8906d2cefda0fcff357e34137218940b28cdb
      - name: sold_to_date_usd
        pack_span: cdi_securities_act_forms_q116_23
        text_sha256: a85fb5d9d3a8132b7782e84e59c8906d2cefda0fcff357e34137218940b28cdb
  - path_id: qncx:baby_shelf_max_new_supplement
    family: registration
    rule_id: sec_cdi.116.23
    rule_example_id: cdi_116_23_concurrent_continuous_offerings
    rule_class: staff_interpretation
    unit: usd
    expected: "5000000"
    gap: null
    arithmetic: offerable_total_usd - still_offered_under_june_7_supplement_usd
    operands:
      - name: offerable_total_usd
        pack_span: cdi_securities_act_forms_q116_23
        text_sha256: a85fb5d9d3a8132b7782e84e59c8906d2cefda0fcff357e34137218940b28cdb
      - name: still_offered_under_june_7_supplement_usd
        pack_span: cdi_securities_act_forms_q116_23
        text_sha256: a85fb5d9d3a8132b7782e84e59c8906d2cefda0fcff357e34137218940b28cdb
negatives:
  - name: public_float_basis_conflict
    expect: contradicted
    state: QUANTITY_STATUSES
    reason: >
      when two qualified sources disagree on the public-float basis the
      quantity renders contradicted: "Sources disagree", both values shown,
      no pick between them
  - name: cap_operand_unknown
    expect: unknown
    state: QUANTITY_STATUSES
    reason: >
      a cap operand that no qualified source establishes keeps the cap
      unknown and the aggregate names exactly what is missing; it never
      renders a computed value
```

## Identity

`identity_for(pack, "QNCX")`: ticker QNCX, CIK 0001662774, issuer_id
sec:cik:0001662774, registry name `IRulya Therapeutics Inc.` (submissions
name identical), Nasdaq, ticker as of 2026-10-13, label_drift true,
case_supply supplied, qualification `qualified`. Reference pack 1.1.0
(G0-S requalification) records the registrant rename: `Quince Therapeutics,
Inc.` is a former name to 2026-10-09, the primary ticker is now IRLA and
QNCX is retained. The in-policy anchors were re-derived unchanged, so the
expectations below are unaffected.

## Source packet

Issuer registration filings, retained bytes (source ledger at the dossier
cutoff):

- form S-3, accession `0001193125-26-328769`, filed 2026-07-31,
  document `complete-submission.txt` sequence `0`, byte_length 719098,
  manifest_id `manifest:cs:8d483ca65e28aa529ca58916e21e3f9d2f4e19b4870f1f3cab57b2a79dc27582`,
  span_id `root:5ab78046ba30282993bd29d895b183059419e90e10001967b464c1f677358bce`,
  text_sha256 `5ab78046ba30282993bd29d895b183059419e90e10001967b464c1f677358bce`
- form S-3/A, accession `0001193125-26-333764`, filed 2026-08-05,
  document `complete-submission.txt` sequence `0`, byte_length 78438,
  manifest_id `manifest:cs:22a84e14d8bfbda4133a14cece277c09f755fe077d8f1ef60868a8e15f25c748`,
  span_id `root:902cef4062672206db07e62352b0a5937a187b3fc70a59c81d199db031f644bd`,
  text_sha256 `902cef4062672206db07e62352b0a5937a187b3fc70a59c81d199db031f644bd`

Rule source (reference pack source `sec_cdi_securities_act_forms`,
staff_interpretation, qualified): span `cdi_securities_act_forms_q116_23`,
interpretation date 2010-08-11, sha256
`a85fb5d9d3a8132b7782e84e59c8906d2cefda0fcff357e34137218940b28cdb` — the
span text itself states the example operands: a company able to sell up to
$10 million under General Instruction I.B.6 has sold $2.5 million to date
with $2.5 million still offered under the June 7 supplement, and asks the
maximum for the June 14 supplement.

## Mandatory numerical path

`qncx:baby_shelf_offerable_total` — one-third-of-public-float cap on the
pack's example operands:
`min(remaining_shelf, public_float/3 − trailing-12m usage)`, whose example
arithmetic is `one_third_limit_usd − sold_to_date_usd` = 10,000,000 − 2,500,000
= **7,500,000 USD** offerable as of June 14 (expected value `"7500000"`), and
`qncx:baby_shelf_max_new_supplement` = `offerable_total_usd −
still_offered_under_june_7_supplement_usd` = 7,500,000 − 2,500,000 =
**5,000,000 USD** maximum June 14 supplement (expected value `"5000000"`).
Rule: `sec_cdi.116.23` / pack example
`cdi_116_23_concurrent_continuous_offerings` — concurrent continuous
offerings count against the limit. The issuer's own public float is NOT
asserted here; the issuer filings above anchor the registration identity and
the rule example anchors the arithmetic.

## Negatives

1. `public_float_basis_conflict` — float basis `contradicted`
   (QUANTITY_STATUSES): "Sources disagree", two values, no pick.
2. `cap_operand_unknown` — cap operand `unknown` (QUANTITY_STATUSES); the
   aggregate says what is missing and never renders a computed value.

## J5 cutoff

`2026-10-17` — the served state generation's as_of instant is
2026-10-17T14:45:44.820502Z; the then-known view at that cutoff and the
"came after" disclosure for anything observed later.

## Findings

- Served generation `state_bundle:cs:2be6a6164f1d6fd9a5bd5c89375d21b6`
  (as_of 2026-10-17T14:45:44.820502Z) publishes NO registration path records
  for QNCX (`records` empty, provenance support `partial` with
  `lifecycle_coverage_partial` and `offering_role_unknown`) and lists
  `registered_amount_remaining` and `remaining_offering_dollars` in the
  family's unavailable list. The rule-example arithmetic above is
  pack-provable and traces to the reference-pack span; the issuer-specific
  cap application (public float/3 − trailing-12m usage for QNCX's own float)
  has no served counterpart yet.
- `path_evidence` for QNCX is empty and the bundle's evidence_index holds
  zero entries for sec:cik:0001662774: the two issuer filing locators above
  are ledger-retained but not yet served evidence.

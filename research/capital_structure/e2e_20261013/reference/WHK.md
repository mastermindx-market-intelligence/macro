# WHK — exhibit-rich instrument, instruments archetype (WITHHELD)

Dossier A0-0 (SPEC_A0 §2). WHK is withheld by construction: the reference
pack records gap `whk_replacement_issuer` ("WHK no longer supplies an
S-3-family case; old witness preserved, replacement not guessed") and owes
the replacement to G0. The honest-state proof IS the test: no number, no
zero, no blank. Every mismatch with the served state is recorded under
`## Findings` verbatim. This dossier fixes acceptance inputs only.

```yaml
schema: capital_structure.reference_dossier.v1
ticker: WHK
issuer_id: sec:cik:0001921603
cik: "0001921603"
registry_name: WhiteHawk Minerals Corp.
binding_status: qualified
verdict_hint: withheld
gap_ids:
  - whk_replacement_issuer
j5_cutoff: "2026-10-17"
expectations:
  - path_id: whk:instruments_family_honest_state
    family: instruments
    rule_id: null
    rule_example_id: null
    rule_class: null
    unit: null
    expected: null
    gap: >
      withheld by construction (E0 gap whk_replacement_issuer): the family is
      recorded withheld and the API must return not_built/unavailable
      honestly for it; asserting no number is the expectation
    arithmetic: none - the withheld family renders no quantity
    operands:
      - name: historical_registration_witness
        ref: manifest:cs:30b89244c08a0dc11f16068119c045d74c165a1a52df2b8c174cabafe2245d02/root:ede1360ff1531c54f5eb1098e52942d04adb6d6aa0cd2e80c8bd89e584b3527a
        text_sha256: ede1360ff1531c54f5eb1098e52942d04adb6d6aa0cd2e80c8bd89e584b3527a
        note: >
          S-1 accession 0001193125-26-215605 (filed 2026-05-11), document
          d86452ds1.htm sequence "1" — served evidence, historical witness only
      - name: historical_registration_witness_current
        ref: manifest:cs:6d80220c2356366c9ae551e0f45876fa56ef3d461d8e4eedd5d246b59b0515e6/root:f9fd3f48d750916c954d19ccd41589fba1e7345cafd1d5756dee76a29131791c
        text_sha256: f9fd3f48d750916c954d19ccd41589fba1e7345cafd1d5756dee76a29131791c
        note: >
          S-1 accession 0001193125-26-424097 (filed 2026-10-16), document
          whk-20261016.htm sequence "1" — served evidence, witness only
      - name: historical_effect_notice
        ref: manifest:cs:ab39fdd19c68ed564980554d063c2269b5b11b02d7709716c8fe57281371f90c/root:47930aea828f6bf5a8a8b388c9510716be15158dd59a79ee213764596ca2234d
        text_sha256: 47930aea828f6bf5a8a8b388c9510716be15158dd59a79ee213764596ca2234d
        note: >
          EFFECT accession 9999999995-26-001919 (filed 2026-06-08) — served
          evidence, witness only
negatives:
  - name: instruments_family_not_built
    expect: not_built
    state: SUPPORT_STATES
    reason: >
      the instruments family for WHK renders not_built (or the typed partial/
      unknown honest state) — never a number, never a zero, never a blank
  - name: any_whk_instrument_quantity
    expect: withheld
    state: QUANTITY_STATUSES
    reason: >
      a quantity for the withheld family renders as withheld (the sign-out
      view's "Not shown on your plan" semantics), never as a value
```

## Identity

`identity_for(pack, "WHK")`: ticker WHK, CIK 0001921603, issuer_id
sec:cik:0001921603, registry name `WhiteHawk Minerals Corp.` (submissions
name identical), NYSE, ticker as of 2026-10-13, label_drift TRUE — the prior
label `WhiteHawk Income Corp` is the registrant's FORMER name (renamed per
formerNames) and is retained as a historical witness only; case_supply
`unsupplied`, replacement_owed TRUE, qualification `qualified`. Binding
status is qualified as an identity while the CASE is unsupplied: the pack
owes G0 a replacement issuer and did not guess one.

## Source packet

The served state bundle publishes exactly three evidence entries for WHK,
all `public_source_link` grade, retained as the historical witness:

- S-1 accession `0001193125-26-215605` (filed 2026-05-11), document
  `d86452ds1.htm` sequence `1`,
  evidence key `manifest:cs:30b89244c08a0dc11f16068119c045d74c165a1a52df2b8c174cabafe2245d02/root:ede1360ff1531c54f5eb1098e52942d04adb6d6aa0cd2e80c8bd89e584b3527a`
- S-1 accession `0001193125-26-424097` (filed 2026-10-16), document
  `whk-20261016.htm` sequence `1`,
  evidence key `manifest:cs:6d80220c2356366c9ae551e0f45876fa56ef3d461d8e4eedd5d246b59b0515e6/root:f9fd3f48d750916c954d19ccd41589fba1e7345cafd1d5756dee76a29131791c`
- EFFECT accession `9999999995-26-001919` (filed 2026-06-08),
  evidence key `manifest:cs:ab39fdd19c68ed564980554d063c2269b5b11b02d7709716c8fe57281371f90c/root:47930aea828f6bf5a8a8b388c9510716be15158dd59a79ee213764596ca2234d`

No rule source is bound: the archetype's rule would belong to the replacement
issuer's qualification (E0 gap `whk_replacement_issuer`, owed to G0).

## Mandatory numerical path

NONE. WHK is `withheld` by construction: the family is recorded withheld and
the API returns `not_built`/`unavailable` honestly for it. Asserting no
number is the expectation — the honest-state proof IS the test (no number,
no 0, no blank).

## Negatives

1. `instruments_family_not_built` — support `not_built` (SUPPORT_STATES).
2. `any_whk_instrument_quantity` — quantity `withheld` (QUANTITY_STATUSES).

## J5 cutoff

`2026-10-17` — the served state generation's as_of instant is
2026-10-17T14:45:44.820502Z. J5 at any cutoff must still render the
withheld family's honest state, never a value.

## Findings

- Served generation `state_bundle:cs:2be6a6164f1d6fd9a5bd5c89375d21b6`
  (as_of 2026-10-17T14:45:44.820502Z): WHK is the ONLY reference issuer with
  served evidence entries (the three above), and its registration family
  carries amendment-chain records (S-1 → S-1/A → 424B4 → EFFECT) with
  `offering_role_unknown`, `replacement_not_extracted` support limits.
- The instruments family is absent for WHK in the bundle — consistent with
  the withheld verdict; the not_built honest state is what the API must
  render, not a served family record.
- The identity's label drift (WhiteHawk Income Corp → WhiteHawk Minerals
  Corp.) is bound by the pack; any UI or dossier surfacing the prior label as
  current would be a finding against A07.

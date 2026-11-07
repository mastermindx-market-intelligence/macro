# LPTH — repeated EFFECT / amendment, registration + change_events archetype

Dossier A0-0 (SPEC_A0 §2). Expectations are fixed here BEFORE the lineage
harness runs; the correction lineage (prior value stamped, current value
solid, each with its own evidence ref and available_at) is fixed from the
retained packets, and every mismatch with the served state is recorded under
`## Findings` verbatim. This dossier fixes acceptance inputs only.

```yaml
schema: capital_structure.reference_dossier.v1
ticker: LPTH
issuer_id: sec:cik:0000889971
cik: "0000889971"
registry_name: LIGHTPATH TECHNOLOGIES INC
binding_status: qualified
verdict_hint: accept
gap_ids: []
j5_cutoff: "2026-10-17"
expectations:
  - path_id: lpth:post_amendment_registered_amount
    family: registration
    rule_id: cfr.17.230.462.e
    rule_example_id: null
    rule_class: binding_rule
    unit: usd
    expected: null
    gap: >
      the post-amendment registered amount is not served by the generation at
      the dossier cutoff and the retained POS AM / EFFECT packets carry no
      admissible-grade extraction of the amount, so the dollar value cannot
      be asserted from permitted evidence
    arithmetic: >
      current_registered_amount_usd (solid) with prior_registered_amount_usd
      (stamped) carried alongside, each with its own evidence ref and
      available_at
    operands:
      - name: current_registered_amount_usd
        ref: manifest:cs:6c5b3fc1e7577c55006f3a9b9ed9985465c1f9b103dc1357a87a15870e15f3d8/root:f218e547a9b6e517933d1463f6ac7142dc044dcbc8645e83517a022a4047bb8d
        text_sha256: f218e547a9b6e517933d1463f6ac7142dc044dcbc8645e83517a022a4047bb8d
        note: >
          POS AM accession 0001437749-26-024147 (filed 2026-07-22), complete
          submission root span — the post-effective amendment carrying the
          current registered amount
      - name: effect_notice
        ref: manifest:cs:aa3bbe772ea17765e90e3625a2b3786205d914ddda5f4beed38e4bd81a7b8bbc/root:e3ad4085552b9699f88ad17939042e58fbc6de082f15e93b72907b9f371426cc
        text_sha256: e3ad4085552b9699f88ad17939042e58fbc6de082f15e93b72907b9f371426cc
        note: >
          EFFECT accession 9999999995-26-002397 (filed 2026-07-23), complete
          submission root span — the notice that the amendment went effective
negatives:
  - name: then_known_before_the_amendment
    expect: "detail:unknown_at_date"
    reason: >
      at a then-known cutoff before the POS AM (2026-07-22) the current path
      had not happened yet and renders as unknown_at_date (state_bundle
      not_yet_observed: absence of an observation is not a fact about the
      registration) — the prior value only, never the current value
  - name: evidence_hash_mismatch
    expect: "detail:evidence hash mismatch"
    reason: >
      evidence requested with a digest that does not match the retained span
      is refused with _private_error 409 detail "evidence hash mismatch"
      (app/capital_structure.py) — never a best-effort value
```

## Identity

`identity_for(pack, "LPTH")`: ticker LPTH, CIK 0000889971, issuer_id
sec:cik:0000889971, registry name `LIGHTPATH TECHNOLOGIES INC` (submissions
name identical), Nasdaq, ticker as of 2026-10-13, label_drift false,
case_supply supplied, qualification `qualified`.

## Source packet

Amendment lineage filings, retained bytes (source ledger at the dossier
cutoff):

- form POS AM, accession `0001437749-26-024147`, filed 2026-07-22,
  document `complete-submission.txt` sequence `0`, byte_length 47946,
  manifest_id `manifest:cs:6c5b3fc1e7577c55006f3a9b9ed9985465c1f9b103dc1357a87a15870e15f3d8`,
  span_id `root:f218e547a9b6e517933d1463f6ac7142dc044dcbc8645e83517a022a4047bb8d`,
  text_sha256 `f218e547a9b6e517933d1463f6ac7142dc044dcbc8645e83517a022a4047bb8d`
- form EFFECT, accession `9999999995-26-002397`, filed 2026-07-23,
  document `complete-submission.txt` sequence `0`, byte_length 1788,
  manifest_id `manifest:cs:aa3bbe772ea17765e90e3625a2b3786205d914ddda5f4beed38e4bd81a7b8bbc`,
  span_id `root:e3ad4085552b9699f88ad17939042e58fbc6de082f15e93b72907b9f371426cc`,
  text_sha256 `e3ad4085552b9699f88ad17939042e58fbc6de082f15e93b72907b9f371426cc`

The ledger also retains the sibling POS AM accessions
0001437749-26-024148 through -026176 and EFFECT notices 9999999995-26-002398
through -002407 (the repeated-EFFECT pattern this archetype names); they are
witnesses to the pattern, not operands of this path.

Rule source: `cfr.17.230.462.e` (Rule 462(e) — post-effective amendment
effectiveness) from the active rule-applicability pack
`capital_structure.rule_applicability.L0`.

## Mandatory numerical path

`lpth:post_amendment_registered_amount` — the post-amendment registered
amount with the correction lineage: the prior value rendered stamped with its
own evidence ref and available_at, the current value rendered solid with its
own evidence ref and available_at. The dollar value is NOT asserted here:
see the gap on the expectation row and `## Findings`.

## Negatives

1. `then_known_before_the_amendment` — at a cutoff before 2026-07-22 the
   current path renders `unknown_at_date` (prior value only, "Not yet
   observed on {date}"), never the current value.
2. `evidence_hash_mismatch` — 409 detail `evidence hash mismatch`.

## J5 cutoff

`2026-10-17` — the served state generation's as_of instant is
2026-10-17T14:45:44.820502Z. The archetype's then-known probe date is
2026-07-21 (before the POS AM), where only the pre-amendment state is
allowed to render.

## Findings

- Served generation `state_bundle:cs:2be6a6164f1d6fd9a5bd5c89375d21b6`
  (as_of 2026-10-17T14:45:44.820502Z) publishes NO registration path records
  for LPTH (`records` empty, provenance support `partial` with
  `lifecycle_coverage_partial`) although the ledger retains the full POS AM
  and EFFECT chain — the amendment lineage above has no served counterpart
  yet, and `registered_amount_remaining` is in the family's unavailable list.
- `path_evidence` for LPTH is empty and the bundle's evidence_index holds
  zero entries for sec:cik:0000889971: the two locators above are
  ledger-retained but not yet served evidence.
- The change_events family is absent for LPTH in the bundle, so the
  stamped/solid correction lineage has no served counterpart either.

# EDBL — proxy / corporate action, share_basis + transactions archetype

Dossier A0-0 (SPEC_A0 §2). Expectations are fixed here BEFORE the lineage
harness runs; the post-split share basis and the §7a authorized-headroom
disclosure are fixed from the retained packets and the S0 contract, and every
mismatch with the served state is recorded under `## Findings` verbatim.
This dossier fixes acceptance inputs only; it states no evaluation of the issuer.

```yaml
schema: capital_structure.reference_dossier.v1
ticker: EDBL
issuer_id: sec:cik:0001809750
cik: "0001809750"
registry_name: Edible Garden AG Inc
binding_status: qualified
verdict_hint: accept
gap_ids: []
j5_cutoff: "2026-10-17"
expectations:
  - path_id: edbl:post_split_share_basis
    family: share_basis
    rule_id: null
    rule_example_id: null
    rule_class: null
    unit: null
    expected: null
    gap: >
      the share_basis family is not served for EDBL by the generation at the
      dossier cutoff and the active packs carry no split rule example, so the
      post-split share count cannot be asserted from permitted evidence
    arithmetic: pre_split_share_count split_ratio = post_split_share_count
    operands:
      - name: corporate_action_notice
        ref: manifest:cs:16cb4096227904dda47a2b8b5c4336636c857f4f0d20a5cf9e6c396a305c9b4d/root:a3d4b6b08dd9ccd5fc36e6316636f75110a62f508122297cd7608dd531b57c6c
        text_sha256: a3d4b6b08dd9ccd5fc36e6316636f75110a62f508122297cd7608dd531b57c6c
        note: >
          8-K accession 0001477932-26-005129 (filed 2026-08-17), document
          edbl_8k.htm sequence "1" — the corporate-action notice packet
      - name: proxy_action_basis
        ref: manifest:cs:5da5d525ec4d67fe1547a70ba3d71b79db319eb6b7dee40944968484c6f644a9/root:3f234d2b9970ea59e3755fd32a2a843fb4339cca4b3a9c7e060b97bcb66b8bfa
        text_sha256: 3f234d2b9970ea59e3755fd32a2a843fb4339cca4b3a9c7e060b97bcb66b8bfa
        note: >
          DEF 14A accession 0001140361-26-022336 (filed 2026-05-21), document
          edge20069957x1_def14a.htm sequence "1" — the proxy packet
      - name: registration_effect_notice
        ref: manifest:cs:1652302a6e2b852b59d6b79e7fb12989fb3ae8ac16dfd3e423fb13122a352295/root:71e1910ef1f35f195ef05ca8e943be0c639385085a1d0f565080a7f719c568b9
        text_sha256: 71e1910ef1f35f195ef05ca8e943be0c639385085a1d0f565080a7f719c568b9
        note: >
          EFFECT accession 9999999995-26-002592 (filed 2026-08-07), document
          primary_doc.xml sequence "1" — the registration effect notice
  - path_id: edbl:authorized_headroom_disclosure
    family: share_basis
    rule_id: null
    rule_example_id: null
    rule_class: null
    unit: null
    expected: null
    gap: >
      capacity carries no authorized-share input for EDBL at the dossier
      cutoff, so the S0 §7a disclosure renders its unknown code rather than a
      headroom quantity
    arithmetic: authorized_shares - issued_shares - reserved_shares
    operands:
      - name: corporate_action_notice
        ref: manifest:cs:16cb4096227904dda47a2b8b5c4336636c857f4f0d20a5cf9e6c396a305c9b4d/root:a3d4b6b08dd9ccd5fc36e6316636f75110a62f508122297cd7608dd531b57c6c
        text_sha256: a3d4b6b08dd9ccd5fc36e6316636f75110a62f508122297cd7608dd531b57c6c
negatives:
  - name: pre_effective_date_view
    expect: conditional
    state: FLOW_CERTAINTIES
    reason: >
      viewed at a cutoff before the split's effective date the split renders
      conditional — witnessed but not applied; the share basis stays
      pre-split until the effective moment is observed
  - name: authorized_shares_not_established
    expect: unknown
    state: QUANTITY_STATUSES
    reason: >
      with no established authorized-share quantity the S0 §7a disclosure
      renders the unknown code
      authorized_headroom_not_evaluated:charter_limit_unchecked with note
      "charter share limit not evaluated by capacity; requested share
      issuance is not checked against authorized shares", and the page copy
      says the figure cannot be computed — no digit on screen
```

## Identity

`identity_for(pack, "EDBL")`: ticker EDBL, CIK 0001809750, issuer_id
sec:cik:0001809750, registry name `Edible Garden AG Inc`, Nasdaq, ticker as
of 2026-10-13, label_drift false, case_supply supplied, qualification
`qualified`.

## Source packet

Corporate-action filings, retained bytes (source ledger at the dossier
cutoff):

- form DEF 14A, accession `0001140361-26-022336`, filed 2026-05-21,
  document `edge20069957x1_def14a.htm` sequence `1`, byte_length 492669,
  manifest_id `manifest:cs:5da5d525ec4d67fe1547a70ba3d71b79db319eb6b7dee40944968484c6f644a9`,
  span_id `root:3f234d2b9970ea59e3755fd32a2a843fb4339cca4b3a9c7e060b97bcb66b8bfa`,
  text_sha256 `3f234d2b9970ea59e3755fd32a2a843fb4339cca4b3a9c7e060b97bcb66b8bfa`
- form 8-K, accession `0001477932-26-005129`, filed 2026-08-17,
  document `edbl_8k.htm` sequence `1`, byte_length 27893,
  manifest_id `manifest:cs:16cb4096227904dda47a2b8b5c4336636c857f4f0d20a5cf9e6c396a305c9b4d`,
  span_id `root:a3d4b6b08dd9ccd5fc36e6316636f75110a62f508122297cd7608dd531b57c6c`,
  text_sha256 `a3d4b6b08dd9ccd5fc36e6316636f75110a62f508122297cd7608dd531b57c6c`
- form EFFECT, accession `9999999995-26-002592`, filed 2026-08-07,
  document `primary_doc.xml` sequence `1`, byte_length 670,
  manifest_id `manifest:cs:1652302a6e2b852b59d6b79e7fb12989fb3ae8ac16dfd3e423fb13122a352295`,
  span_id `root:71e1910ef1f35f195ef05ca8e943be0c639385085a1d0f565080a7f719c568b9`,
  text_sha256 `71e1910ef1f35f195ef05ca8e943be0c639385085a1d0f565080a7f719c568b9`
- form S-3, accession `0001477932-26-004651`, filed 2026-07-31 (document
  `edbl_s3.htm` sequence `1`, manifest_id
  `manifest:cs:54b5bcee35665f82ad8e07ad806fcf629911e4c18868abd560112841c0812ae1`,
  span_id `root:4eff8692aef35e6cee05e08bfb528b437d4e4eb1e3992bf5b49177f5f33c5306`)
  anchors the registration identity for the same window.

No rule source is bound: the active packs carry no split rule example, and
the §7a headroom disclosure is an S0 capacity contract, not a rule-pack rule.

## Mandatory numerical path

`edbl:post_split_share_basis` — the post-split share basis with the split
applied exactly once at its observed effective moment, read from the served
share_basis family, plus `edbl:authorized_headroom_disclosure` (S0 §7a) read
from capacity — never derived. Both are gap rows here: see the expectation
rows and `## Findings`.

## Negatives

1. `pre_effective_date_view` — split `conditional` (FLOW_CERTAINTIES),
   not applied, at a cutoff before the effective date.
2. `authorized_shares_not_established` — `unknown` (QUANTITY_STATUSES) with
   the S0 §7a unknown code `authorized_headroom_not_evaluated:charter_limit_unchecked`;
   the page copy states the figure cannot be computed (no digit).

## J5 cutoff

`2026-10-17` — the served state generation's as_of instant is
2026-10-17T14:45:44.820502Z. The archetype's pre-effective probe date is
2026-08-06 (the day before the EFFECT notice above), where the split must
render conditional.

## Findings

- Served generation `state_bundle:cs:2be6a6164f1d6fd9a5bd5c89375d21b6`
  (as_of 2026-10-17T14:45:44.820502Z) publishes NO registration path records
  for EDBL (`records` empty, provenance support `partial`) and NO share_basis
  or transactions family at all, so the post-split basis and the §7a
  disclosure have no served counterpart yet.
- `path_evidence` for EDBL is empty and the bundle's evidence_index holds
  zero entries for sec:cik:0001809750: the four locators above are
  ledger-retained but not yet served evidence.
- The active reference and rule-applicability packs carry no split rule
  example; this dossier asserts no number and names no rule id rather than
  guessing one — the rule example is owed by a later qualification wave.

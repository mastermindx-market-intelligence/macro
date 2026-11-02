# FIF Q1 held-out pack quality index (A34/A37)

- protocol: fif-q0-quality-protocol/v1; report schema fundamental_forensics.pack_quality_report/v1; evaluator role independent_q1
- head_commit: af6d63be102326f5019df8d95484454d79302e6e
- evaluated_at: 2026-10-31T16:37:04Z
- precision floor (predeclared seat ruling 2026-10-31, before any held-out result was observed): extraction-precision Wilson lower bound 0.80 for every pack and cell
- split root: tests/fixtures/fundamental_forensics_held_out (sealed labels; this lane is their only reader; pack builders never read them)
- staged bytes (read-only): /home/ubuntu2/lanes/stage/fif-heldout
- every rate is numerator/denominator with Wilson 95% bounds [lower, upper]; a bare numerator/denominator holds where the report carries no interval
- quality vocabulary is the Q0 set only: held_out_measured, underpowered, unavailable_research_only, blocked_pack

| pack | name | labels | quality_label | cells | precision | recall | abstention | FP rate | failed families | disposition | package unavailable |
|---|---|---|---|---|---|---|---|---|---|---|---|
| PK01 | Debt, liquidity, covenants and maturities | 28 | underpowered | 9 | 17/17 [0.8157, 1.0000] | 17/26 [0.4622, 0.8059] | 11/28 [0.2357, 0.5759] | 0/2 [0.0000, 0.6576] | covenant_text(precision_below_floor+underpowered); debt_outstanding(precision_below_floor); liquidity(precision_below_floor); maturity_schedule(precision_below_floor) | unavailable_research_only | - |
| PK02 | Stock compensation and dilution | 46 | underpowered | 17 | 24/34 [0.5383, 0.8317] | 24/43 [0.4111, 0.6957] | 6/46 [0.0612, 0.2567] | 0/3 [0.0000, 0.5615] | eps(precision_below_floor); sbc(precision_below_floor+underpowered); share_counts(precision_below_floor); share_repurchase(precision_below_floor+underpowered) | unavailable_research_only | - |
| PK03 | Segments and geographic/product dimensions | 20 | underpowered | 4 | 1/1 [0.2065, 1.0000] | 1/19 [0.0094, 0.2464] | 13/20 [0.4329, 0.8188] | 0/1 [0.0000, 0.7935] | segments(precision_below_floor) | unavailable_research_only | - |
| PK04 | Revenue recognition and contract balances | 28 | underpowered | 12 | 19/21 [0.7109, 0.9735] | 19/26 [0.5392, 0.8630] | 5/28 [0.0788, 0.3559] | 1/2 [0.0945, 0.9055] | contract_liability(fp_on_negative+invented_extraction+precision_below_floor+underpowered); revenue(precision_below_floor+underpowered); rpo(precision_below_floor+underpowered) | unavailable_research_only | - |
| PK05 | Tax and uncertain tax positions | 51 | underpowered | 9 | 32/41 [0.6329, 0.8800] | 32/49 [0.5131, 0.7708] | 8/51 [0.0817, 0.2801] | 0/2 [0.0000, 0.6576] | income_tax(precision_below_floor); utp(precision_below_floor) | unavailable_research_only | - |
| PK06 | Leases and off-balance commitments | 16 | underpowered | 5 | 14/14 [0.7847, 1.0000] | 14/14 [0.7847, 1.0000] | 2/16 [0.0350, 0.3602] | 0/2 [0.0000, 0.6576] | lease_liability(precision_below_floor) | unavailable_research_only | - |
| PK07 | M&A, goodwill, intangibles and impairments | 28 | underpowered | 16 | 13/13 [0.7719, 1.0000] | 13/24 [0.3507, 0.7211] | 14/28 [0.3263, 0.6737] | 1/4 [0.0456, 0.6994] | business_combination(precision_below_floor); goodwill_intangibles(precision_below_floor); goodwill_rollforward(precision_below_floor+underpowered); impairment_testing(fp_on_negative+invented_extraction+precision_below_floor+underpowered) | unavailable_research_only | - |
| PK08 | Legal contingencies | 28 | underpowered | 12 | 2/8 [0.0715, 0.5907] | 2/22 [0.0253, 0.2782] | 20/28 [0.5294, 0.8475] | 0/6 [0.0000, 0.3903] | commitments_note(precision_below_floor); legal_proceedings(precision_below_floor); loss_contingency(precision_below_floor+underpowered) | unavailable_research_only | - |
| PK09 | Controls, auditor and going concern | 26 | underpowered | 10 | 13/13 [0.7719, 1.0000] | 13/22 [0.3873, 0.7674] | 13/26 [0.3206, 0.6794] | 0/4 [0.0000, 0.4899] | auditor_opinion(precision_below_floor); going_concern_wording(precision_below_floor+underpowered); icfr_opinion(precision_below_floor) | unavailable_research_only | - |
| PK10 | Proxy compensation and governance | no_held_out_labels | unavailable_research_only | 0 | - | - | - | - | - | unavailable_research_only | - |
| PK11 | Financial-institution credit/capital/liquidity | 37 | underpowered | 15 | 8/12 [0.3906, 0.8619] | 8/27 [0.1585, 0.4848] | 25/37 [0.5146, 0.8037] | 0/10 [0.0000, 0.2775] | cet1_or_stated_ratio(precision_below_floor); credit_loss(precision_below_floor); lcr_or_stated_liq(precision_below_floor+underpowered) | unavailable_research_only | - |
| PK12 | Biotech cash/R&D/financing disclosures | 28 | underpowered | 14 | 0/0 | 0/25 [0.0000, 0.1332] | 28/28 [0.8794, 1.0000] | 0/3 [0.0000, 0.5615] | cash_flow(precision_below_floor); cash_investments(precision_below_floor); liquidity(precision_below_floor+underpowered); rd_expense(precision_below_floor+underpowered) | unavailable_research_only | - |

## Failed-family detail (frozen scoring core)

- PK01 covenant_text: reasons precision_below_floor+underpowered; disposition unavailable_research_only; blocks ['PK01']; precision None, recall 0/3, abstention 3/3, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK01 debt_outstanding: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK01']; precision 2/2, recall 2/8, abstention 8/10, fp 0/2; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK01 liquidity: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK01']; precision 10/10, recall 10/10, abstention 0/10, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK01 maturity_schedule: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK01']; precision 5/5, recall 5/5, abstention 0/5, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK02 eps: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK02']; precision 12/20, recall 12/20, abstention 0/20, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK02 sbc: reasons precision_below_floor+underpowered; disposition unavailable_research_only; blocks ['PK02']; precision 3/5, recall 3/11, abstention 5/13, fp 0/2; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK02 share_counts: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK02']; precision 7/7, recall 7/10, abstention 1/11, fp 0/1; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK02 share_repurchase: reasons precision_below_floor+underpowered; disposition unavailable_research_only; blocks ['PK02']; precision 2/2, recall 2/2, abstention 0/2, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK03 segments: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK03']; precision 1/1, recall 1/19, abstention 13/20, fp 0/1; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK04 contract_liability: reasons fp_on_negative+invented_extraction+precision_below_floor+underpowered; disposition unavailable_research_only; blocks ['PK04']; precision 9/9, recall 9/9, abstention 1/11, fp 1/2; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK04 revenue: reasons precision_below_floor+underpowered; disposition unavailable_research_only; blocks ['PK04']; precision 3/5, recall 3/7, abstention 1/7, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK04 rpo: reasons precision_below_floor+underpowered; disposition unavailable_research_only; blocks ['PK04']; precision 7/7, recall 7/10, abstention 3/10, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK05 income_tax: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK05']; precision 17/18, recall 17/26, abstention 7/27, fp 0/1; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK05 utp: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK05']; precision 15/23, recall 15/23, abstention 1/24, fp 0/1; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK06 lease_liability: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK06']; precision 14/14, recall 14/14, abstention 2/16, fp 0/2; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK07 business_combination: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK07']; precision None, recall 0/5, abstention 5/5, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK07 goodwill_intangibles: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK07']; precision 10/10, recall 10/10, abstention 0/10, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK07 goodwill_rollforward: reasons precision_below_floor+underpowered; disposition unavailable_research_only; blocks ['PK07']; precision 2/2, recall 2/5, abstention 4/6, fp 0/1; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK07 impairment_testing: reasons fp_on_negative+invented_extraction+precision_below_floor+underpowered; disposition unavailable_research_only; blocks ['PK07']; precision 1/1, recall 1/4, abstention 5/7, fp 1/3; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK08 commitments_note: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK08']; precision 2/3, recall 2/4, abstention 1/4, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK08 legal_proceedings: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK08']; precision 0/4, recall 0/10, abstention 6/10, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK08 loss_contingency: reasons precision_below_floor+underpowered; disposition unavailable_research_only; blocks ['PK08']; precision 0/1, recall 0/8, abstention 13/14, fp 0/6; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK09 auditor_opinion: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK09']; precision 3/3, recall 3/6, abstention 7/10, fp 0/4; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK09 going_concern_wording: reasons precision_below_floor+underpowered; disposition unavailable_research_only; blocks ['PK09']; precision 2/2, recall 2/2, abstention 0/2, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK09 icfr_opinion: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK09']; precision 8/8, recall 8/14, abstention 6/14, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK11 cet1_or_stated_ratio: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK11']; precision None, recall 0/9, abstention 15/15, fp 0/6; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK11 credit_loss: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK11']; precision 5/9, recall 5/15, abstention 6/15, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK11 lcr_or_stated_liq: reasons precision_below_floor+underpowered; disposition unavailable_research_only; blocks ['PK11']; precision 3/3, recall 3/3, abstention 4/7, fp 0/4; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK12 cash_flow: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK12']; precision None, recall 0/11, abstention 12/12, fp 0/1; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK12 cash_investments: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK12']; precision None, recall 0/8, abstention 8/8, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK12 liquidity: reasons precision_below_floor+underpowered; disposition unavailable_research_only; blocks ['PK12']; precision None, recall 0/2, abstention 2/2, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK12 rd_expense: reasons precision_below_floor+underpowered; disposition unavailable_research_only; blocks ['PK12']; precision None, recall 0/4, abstention 4/4, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision

## Per-accession admission and production outcomes

- PK01 0000018230-23-000011: ADMITTED; 12 labels, 12 predictions; applicability applicable (applicability_rule_satisfied)
- PK01 0000018230-23-000047: ADMITTED; 5 labels, 5 predictions; applicability applicable (applicability_rule_satisfied)
- PK01 0000018230-23-000056: ADMITTED; 5 labels, 5 predictions; applicability applicable (applicability_rule_satisfied)
- PK01 0000070858-23-000092: ADMITTED; 2 labels, 2 predictions; applicability applicable (applicability_rule_satisfied)
- PK01 0000070858-23-000176: ADMITTED; 2 labels, 2 predictions; applicability applicable (applicability_rule_satisfied)
- PK01 0000070858-23-000272: ADMITTED; 2 labels, 2 predictions; applicability applicable (applicability_rule_satisfied)
- PK02 0000018230-23-000011: ADMITTED; 9 labels, 9 predictions; applicability applicable (applicability_rule_satisfied)
- PK02 0000320193-24-000123: ADMITTED; 9 labels, 9 predictions; applicability applicable (applicability_rule_satisfied)
- PK02 0001640147-23-000030: ADMITTED; 9 labels, 7 predictions; applicability applicable (applicability_rule_satisfied)
- PK02 0001640147-23-000199: ADMITTED; 10 labels, 8 predictions; applicability applicable (applicability_rule_satisfied)
- PK02 0001640147-23-000260: ADMITTED; 9 labels, 7 predictions; applicability applicable (applicability_rule_satisfied)
- PK03 0000018230-23-000011: ADMITTED; 6 labels, 5 predictions; applicability applicable (applicability_rule_satisfied)
- PK03 0000320193-24-000123: ADMITTED; 6 labels, 4 predictions; applicability applicable (applicability_rule_satisfied)
- PK03 0001652044-23-000016: ADMITTED; 8 labels, 5 predictions; applicability applicable (applicability_rule_satisfied)
- PK04 0000320193-24-000123: ADMITTED; 4 labels, 4 predictions; applicability applicable (applicability_rule_satisfied)
- PK04 0001640147-23-000030: ADMITTED; 8 labels, 8 predictions; applicability applicable (applicability_rule_satisfied)
- PK04 0001640147-23-000199: ADMITTED; 6 labels, 6 predictions; applicability applicable (applicability_rule_satisfied)
- PK04 0001640147-23-000260: ADMITTED; 6 labels, 6 predictions; applicability applicable (applicability_rule_satisfied)
- PK04 0001652044-23-000016: ADMITTED; 4 labels, 3 predictions; applicability applicable (applicability_rule_satisfied)
- PK05 0000018230-23-000011: ADMITTED; 16 labels, 15 predictions; applicability applicable (applicability_rule_satisfied)
- PK05 0000320193-24-000069: ADMITTED; 4 labels, 4 predictions; applicability not_applicable (form_outside_pack_forms)
- PK05 0000320193-24-000123: ADMITTED; 16 labels, 15 predictions; applicability applicable (applicability_rule_satisfied)
- PK05 0001652044-23-000016: ADMITTED; 15 labels, 15 predictions; applicability applicable (applicability_rule_satisfied)
- PK06 0000018230-23-000011: ADMITTED; 9 labels, 9 predictions; applicability applicable (applicability_rule_satisfied)
- PK06 0000070858-23-000092: ADMITTED; 2 labels, 2 predictions; applicability applicable (applicability_rule_satisfied)
- PK06 0000070858-23-000176: ADMITTED; 2 labels, 2 predictions; applicability applicable (applicability_rule_satisfied)
- PK06 0000070858-23-000272: ADMITTED; 3 labels, 3 predictions; applicability applicable (applicability_rule_satisfied)
- PK07 0000018230-23-000011: ADMITTED; 7 labels, 7 predictions; applicability applicable (applicability_rule_satisfied)
- PK07 0000070858-23-000092: ADMITTED; 4 labels, 4 predictions; applicability applicable (applicability_rule_satisfied)
- PK07 0001640147-23-000030: ADMITTED; 7 labels, 7 predictions; applicability applicable (applicability_rule_satisfied)
- PK07 0001652044-23-000016: ADMITTED; 10 labels, 10 predictions; applicability applicable (applicability_rule_satisfied)
- PK08 0000070858-23-000092: ADMITTED; 6 labels, 6 predictions; applicability applicable (applicability_rule_satisfied)
- PK08 0000320193-24-000069: ADMITTED; 8 labels, 8 predictions; applicability applicable (applicability_rule_satisfied)
- PK08 0000320193-24-000123: ADMITTED; 9 labels, 9 predictions; applicability applicable (applicability_rule_satisfied)
- PK08 0001652044-23-000016: ADMITTED; 5 labels, 5 predictions; applicability applicable (applicability_rule_satisfied)
- PK09 0000018230-23-000011: ADMITTED; 7 labels, 7 predictions; applicability applicable (applicability_rule_satisfied)
- PK09 0000018230-23-000047: ADMITTED; 3 labels, 3 predictions; applicability applicable (applicability_rule_satisfied)
- PK09 0000018230-23-000056: ADMITTED; 3 labels, 3 predictions; applicability applicable (applicability_rule_satisfied)
- PK09 0000070858-23-000092: ADMITTED; 7 labels, 7 predictions; applicability applicable (applicability_rule_satisfied)
- PK09 0000070858-23-000176: ADMITTED; 3 labels, 3 predictions; applicability applicable (applicability_rule_satisfied)
- PK09 0000070858-23-000272: ADMITTED; 3 labels, 3 predictions; applicability applicable (applicability_rule_satisfied)
- PK11 0000018230-23-000011: ADMITTED; 2 labels, 2 predictions; applicability not_applicable (issuer_class_not_bank)
- PK11 0000070858-23-000092: ADMITTED; 9 labels, 9 predictions; applicability applicable (applicability_rule_satisfied)
- PK11 0000070858-23-000176: ADMITTED; 9 labels, 9 predictions; applicability applicable (applicability_rule_satisfied)
- PK11 0000070858-23-000272: ADMITTED; 9 labels, 9 predictions; applicability applicable (applicability_rule_satisfied)
- PK11 0000320193-24-000123: ADMITTED; 2 labels, 2 predictions; applicability not_applicable (issuer_class_not_bank)
- PK11 0001640147-23-000030: ADMITTED; 2 labels, 2 predictions; applicability not_applicable (issuer_class_not_bank)
- PK11 0001652044-23-000016: ADMITTED; 2 labels, 2 predictions; applicability not_applicable (issuer_class_not_bank)
- PK11 0001652044-23-000070: ADMITTED; 1 labels, 1 predictions; applicability not_applicable (issuer_class_not_bank)
- PK11 0001652044-23-000094: ADMITTED; 1 labels, 1 predictions; applicability not_applicable (issuer_class_not_bank)
- PK12 0001640147-23-000030: ADMITTED; 8 labels, 8 predictions; applicability not_applicable (sic_outside_biotech_codes)
- PK12 0001640147-23-000199: ADMITTED; 6 labels, 6 predictions; applicability not_applicable (form_outside_pack_forms)
- PK12 0001640147-23-000260: ADMITTED; 6 labels, 6 predictions; applicability not_applicable (form_outside_pack_forms)
- PK12 0001652044-23-000016: ADMITTED; 7 labels, 7 predictions; applicability not_applicable (sic_outside_biotech_codes)
- PK12 0001652044-23-000070: ADMITTED; 1 labels, 1 predictions; applicability not_applicable (form_outside_pack_forms)

## Notes

- PK10 has no labels/ directory under the held-out root: reported unavailable_research_only with reason no_held_out_labels; its report was produced over an empty label set (the frozen core labels that report underpowered over zero labels); no label was invented
- power checks come from the protocol minimum_n rows; every labelled pack carries ixbrl_inline labels only in this label generation, so the format-generalization minimum (one non-inline label per pack) is unmet and the frozen core assigns the underpowered quality label pack-wide

## Generation note

This is generation two under DEC:FIF-Q1-SECOND-GENERATION-SCOPE-20261031: the same sealed labels, the same staged bytes and the same predeclared 0.80 precision floor were re-measured after three merged repairs on the evaluation path — the contract-first issuer-SIC binding with visible duplicate-target exclusion (DEC:FIF-Q1-EVALUATOR-BINDS-SIC-FROM-HELD-OUT-CONTRACT-20261031), the SEC-parser repair that tolerates inert attributes on nil numeric facts, and the envelope sic_source production-resolver vocabulary repair (DEC:FIF-Q1-EVALUATOR-ENVELOPE-SIC-SOURCE-FOLLOWS-PRODUCTION-RESOLVER-20261031, PR #10316). The BAC 0000070858-23-000092 label trials that generation one excluded wholesale — 30 of 30 (PK01 2, PK06 2, PK07 4, PK08 6, PK09 7, PK11 9) — are now scored with none still excluded, and the packs that emitted nothing while issuer SIC was unbound now emit PK04 22, PK11 12, PK12 0 (every PK12 trial remains a typed_absence abstention under its biotech applicability rule). Every generation-one failed family keeps its generation-one disposition — unavailable_research_only, reopen_requires fresh held-out labels under a new Q0 split decision — and nothing in this generation reopened, relabelled, dropped or re-scored a family by hand.


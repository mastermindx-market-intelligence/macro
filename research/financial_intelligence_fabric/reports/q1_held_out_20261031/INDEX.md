# FIF Q1 held-out pack quality index (A34/A37)

- protocol: fif-q0-quality-protocol/v1; report schema fundamental_forensics.pack_quality_report/v1; evaluator role independent_q1
- head_commit: 761e814eda8460d09ad6c53adc8ee495b4283cf1
- evaluated_at: 2026-10-31T10:32:45Z
- precision floor (predeclared seat ruling 2026-10-31, before any held-out result was observed): extraction-precision Wilson lower bound 0.80 for every pack and cell
- split root: tests/fixtures/fundamental_forensics_held_out (sealed labels; this lane is their only reader; pack builders never read them)
- staged bytes (read-only): /home/ubuntu2/lanes/stage/fif-heldout
- every rate is numerator/denominator with Wilson 95% bounds [lower, upper]; a bare numerator/denominator holds where the report carries no interval
- quality vocabulary is the Q0 set only: held_out_measured, underpowered, unavailable_research_only, blocked_pack

| pack | name | labels | quality_label | cells | precision | recall | abstention | FP rate | failed families | disposition | package unavailable |
|---|---|---|---|---|---|---|---|---|---|---|---|
| PK01 | Debt, liquidity, covenants and maturities | 28 | underpowered | 9 | 17/17 [0.8157, 1.0000] | 17/26 [0.4622, 0.8059] | 9/28 [0.1793, 0.5066] | 0/2 [0.0000, 0.6576] | covenant_text(precision_below_floor+underpowered); debt_outstanding(precision_below_floor); liquidity(precision_below_floor); maturity_schedule(precision_below_floor) | unavailable_research_only | - |
| PK02 | Stock compensation and dilution | 46 | underpowered | 17 | 24/38 [0.4728, 0.7662] | 24/43 [0.4111, 0.6957] | 8/46 [0.0909, 0.3072] | 0/3 [0.0000, 0.5615] | eps(precision_below_floor); sbc(precision_below_floor+underpowered); share_counts(precision_below_floor); share_repurchase(precision_below_floor+underpowered) | unavailable_research_only | - |
| PK03 | Segments and geographic/product dimensions | 20 | underpowered | 4 | 1/6 [0.0301, 0.5635] | 1/19 [0.0094, 0.2464] | 14/20 [0.4810, 0.8545] | 0/1 [0.0000, 0.7935] | segments(precision_below_floor) | unavailable_research_only | - |
| PK04 | Revenue recognition and contract balances | 28 | underpowered | 12 | 0/0 | 0/26 [0.0000, 0.1287] | 28/28 [0.8794, 1.0000] | 0/2 [0.0000, 0.6576] | contract_liability(precision_below_floor+underpowered); revenue(precision_below_floor+underpowered); rpo(precision_below_floor+underpowered) | unavailable_research_only | - |
| PK05 | Tax and uncertain tax positions | 51 | underpowered | 9 | 32/43 [0.5976, 0.8507] | 32/49 [0.5131, 0.7708] | 8/51 [0.0817, 0.2801] | 0/2 [0.0000, 0.6576] | income_tax(precision_below_floor); utp(precision_below_floor) | unavailable_research_only | - |
| PK06 | Leases and off-balance commitments | 16 | underpowered | 5 | 12/12 [0.7575, 1.0000] | 12/14 [0.6006, 0.9599] | 2/16 [0.0350, 0.3602] | 0/2 [0.0000, 0.6576] | lease_liability(precision_below_floor) | unavailable_research_only | - |
| PK07 | M&A, goodwill, intangibles and impairments | 28 | underpowered | 16 | 11/11 [0.7412, 1.0000] | 11/24 [0.2789, 0.6493] | 12/28 [0.2651, 0.6093] | 1/4 [0.0456, 0.6994] | business_combination(precision_below_floor); goodwill_intangibles(precision_below_floor); goodwill_rollforward(precision_below_floor+underpowered); impairment_testing(fp_on_negative+invented_extraction+precision_below_floor+underpowered) | unavailable_research_only | - |
| PK08 | Legal contingencies | 28 | underpowered | 12 | 2/7 [0.0822, 0.6411] | 2/22 [0.0253, 0.2782] | 15/28 [0.3581, 0.7047] | 0/6 [0.0000, 0.3903] | commitments_note(precision_below_floor); legal_proceedings(precision_below_floor); loss_contingency(precision_below_floor+underpowered) | unavailable_research_only | - |
| PK09 | Controls, auditor and going concern | 26 | underpowered | 10 | 9/9 [0.7008, 1.0000] | 9/22 [0.2326, 0.6127] | 10/26 [0.2243, 0.5747] | 0/4 [0.0000, 0.4899] | auditor_opinion(precision_below_floor); going_concern_wording(precision_below_floor+underpowered); icfr_opinion(precision_below_floor) | unavailable_research_only | - |
| PK10 | Proxy compensation and governance | no_held_out_labels | unavailable_research_only | 0 | - | - | - | - | - | unavailable_research_only | - |
| PK11 | Financial-institution credit/capital/liquidity | 37 | underpowered | 15 | 0/0 | 0/27 [0.0000, 0.1246] | 28/37 [0.5988, 0.8664] | 0/10 [0.0000, 0.2775] | cet1_or_stated_ratio(precision_below_floor); credit_loss(precision_below_floor); lcr_or_stated_liq(precision_below_floor+underpowered) | unavailable_research_only | - |
| PK12 | Biotech cash/R&D/financing disclosures | 28 | underpowered | 14 | 0/0 | 0/25 [0.0000, 0.1332] | 28/28 [0.8794, 1.0000] | 0/3 [0.0000, 0.5615] | cash_flow(precision_below_floor); cash_investments(precision_below_floor); liquidity(precision_below_floor+underpowered); rd_expense(precision_below_floor+underpowered) | unavailable_research_only | - |

## Failed-family detail (frozen scoring core)

- PK01 covenant_text: reasons precision_below_floor+underpowered; disposition unavailable_research_only; blocks ['PK01']; precision None, recall 0/3, abstention 3/3, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK01 debt_outstanding: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK01']; precision 2/2, recall 2/8, abstention 6/10, fp 0/2; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK01 liquidity: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK01']; precision 10/10, recall 10/10, abstention 0/10, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK01 maturity_schedule: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK01']; precision 5/5, recall 5/5, abstention 0/5, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK02 eps: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK02']; precision 12/20, recall 12/20, abstention 0/20, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK02 sbc: reasons precision_below_floor+underpowered; disposition unavailable_research_only; blocks ['PK02']; precision 3/6, recall 3/11, abstention 7/13, fp 0/2; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK02 share_counts: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK02']; precision 7/10, recall 7/10, abstention 1/11, fp 0/1; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK02 share_repurchase: reasons precision_below_floor+underpowered; disposition unavailable_research_only; blocks ['PK02']; precision 2/2, recall 2/2, abstention 0/2, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK03 segments: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK03']; precision 1/6, recall 1/19, abstention 14/20, fp 0/1; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK04 contract_liability: reasons precision_below_floor+underpowered; disposition unavailable_research_only; blocks ['PK04']; precision None, recall 0/9, abstention 11/11, fp 0/2; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK04 revenue: reasons precision_below_floor+underpowered; disposition unavailable_research_only; blocks ['PK04']; precision None, recall 0/7, abstention 7/7, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK04 rpo: reasons precision_below_floor+underpowered; disposition unavailable_research_only; blocks ['PK04']; precision None, recall 0/10, abstention 10/10, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK05 income_tax: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK05']; precision 17/20, recall 17/26, abstention 7/27, fp 0/1; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK05 utp: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK05']; precision 15/23, recall 15/23, abstention 1/24, fp 0/1; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK06 lease_liability: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK06']; precision 12/12, recall 12/14, abstention 2/16, fp 0/2; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK07 business_combination: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK07']; precision None, recall 0/5, abstention 5/5, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK07 goodwill_intangibles: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK07']; precision 8/8, recall 8/10, abstention 0/10, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK07 goodwill_rollforward: reasons precision_below_floor+underpowered; disposition unavailable_research_only; blocks ['PK07']; precision 2/2, recall 2/5, abstention 4/6, fp 0/1; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK07 impairment_testing: reasons fp_on_negative+invented_extraction+precision_below_floor+underpowered; disposition unavailable_research_only; blocks ['PK07']; precision 1/1, recall 1/4, abstention 3/7, fp 1/3; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK08 commitments_note: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK08']; precision 2/3, recall 2/4, abstention 1/4, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK08 legal_proceedings: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK08']; precision 0/4, recall 0/10, abstention 4/10, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK08 loss_contingency: reasons precision_below_floor+underpowered; disposition unavailable_research_only; blocks ['PK08']; precision None, recall 0/8, abstention 10/14, fp 0/6; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK09 auditor_opinion: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK09']; precision 2/2, recall 2/6, abstention 5/10, fp 0/4; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK09 going_concern_wording: reasons precision_below_floor+underpowered; disposition unavailable_research_only; blocks ['PK09']; precision 1/1, recall 1/2, abstention 0/2, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK09 icfr_opinion: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK09']; precision 6/6, recall 6/14, abstention 5/14, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK11 cet1_or_stated_ratio: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK11']; precision None, recall 0/9, abstention 12/15, fp 0/6; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK11 credit_loss: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK11']; precision None, recall 0/15, abstention 10/15, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK11 lcr_or_stated_liq: reasons precision_below_floor+underpowered; disposition unavailable_research_only; blocks ['PK11']; precision None, recall 0/3, abstention 6/7, fp 0/4; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK12 cash_flow: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK12']; precision None, recall 0/11, abstention 12/12, fp 0/1; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK12 cash_investments: reasons precision_below_floor; disposition unavailable_research_only; blocks ['PK12']; precision None, recall 0/8, abstention 8/8, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK12 liquidity: reasons precision_below_floor+underpowered; disposition unavailable_research_only; blocks ['PK12']; precision None, recall 0/2, abstention 2/2, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision
- PK12 rd_expense: reasons precision_below_floor+underpowered; disposition unavailable_research_only; blocks ['PK12']; precision None, recall 0/4, abstention 4/4, fp None; relabelling is forbidden and reopening requires a fresh Q0 split decision

## Per-accession admission and production outcomes

- PK01 0000018230-23-000011: ADMITTED; 12 labels, 12 predictions; applicability applicable (applicability_rule_satisfied)
- PK01 0000018230-23-000047: ADMITTED; 5 labels, 5 predictions; applicability applicable (applicability_rule_satisfied)
- PK01 0000018230-23-000056: ADMITTED; 5 labels, 5 predictions; applicability applicable (applicability_rule_satisfied)
- PK01 0000070858-23-000092: package_admission_refused (primary_unparseable); 2 labels, 0 predictions
- PK01 0000070858-23-000176: ADMITTED; 2 labels, 2 predictions; applicability applicable (applicability_rule_satisfied)
- PK01 0000070858-23-000272: ADMITTED; 2 labels, 2 predictions; applicability applicable (applicability_rule_satisfied)
- PK02 0000018230-23-000011: ADMITTED; 9 labels, 9 predictions; applicability applicable (applicability_rule_satisfied)
- PK02 0000320193-24-000123: ADMITTED; 9 labels, 9 predictions; applicability applicable (applicability_rule_satisfied)
- PK02 0001640147-23-000030: ADMITTED; 9 labels, 9 predictions; applicability applicable (applicability_rule_satisfied)
- PK02 0001640147-23-000199: ADMITTED; 10 labels, 10 predictions; applicability applicable (applicability_rule_satisfied)
- PK02 0001640147-23-000260: ADMITTED; 9 labels, 9 predictions; applicability applicable (applicability_rule_satisfied)
- PK03 0000018230-23-000011: ADMITTED; 6 labels, 6 predictions; applicability applicable (applicability_rule_satisfied)
- PK03 0000320193-24-000123: ADMITTED; 6 labels, 6 predictions; applicability applicable (applicability_rule_satisfied)
- PK03 0001652044-23-000016: ADMITTED; 8 labels, 8 predictions; applicability applicable (applicability_rule_satisfied)
- PK04 0000320193-24-000123: ADMITTED; 4 labels, 4 predictions; applicability not_evaluable (issuer_class_unknown)
- PK04 0001640147-23-000030: ADMITTED; 8 labels, 8 predictions; applicability not_evaluable (issuer_class_unknown)
- PK04 0001640147-23-000199: ADMITTED; 6 labels, 6 predictions; applicability not_evaluable (issuer_class_unknown)
- PK04 0001640147-23-000260: ADMITTED; 6 labels, 6 predictions; applicability not_evaluable (issuer_class_unknown)
- PK04 0001652044-23-000016: ADMITTED; 4 labels, 4 predictions; applicability not_evaluable (issuer_class_unknown)
- PK05 0000018230-23-000011: ADMITTED; 16 labels, 16 predictions; applicability applicable (applicability_rule_satisfied)
- PK05 0000320193-24-000069: ADMITTED; 4 labels, 4 predictions; applicability not_applicable (form_outside_pack_forms)
- PK05 0000320193-24-000123: ADMITTED; 16 labels, 16 predictions; applicability applicable (applicability_rule_satisfied)
- PK05 0001652044-23-000016: ADMITTED; 15 labels, 15 predictions; applicability applicable (applicability_rule_satisfied)
- PK06 0000018230-23-000011: ADMITTED; 9 labels, 9 predictions; applicability applicable (applicability_rule_satisfied)
- PK06 0000070858-23-000092: package_admission_refused (primary_unparseable); 2 labels, 0 predictions
- PK06 0000070858-23-000176: ADMITTED; 2 labels, 2 predictions; applicability applicable (applicability_rule_satisfied)
- PK06 0000070858-23-000272: ADMITTED; 3 labels, 3 predictions; applicability applicable (applicability_rule_satisfied)
- PK07 0000018230-23-000011: ADMITTED; 7 labels, 7 predictions; applicability applicable (applicability_rule_satisfied)
- PK07 0000070858-23-000092: package_admission_refused (primary_unparseable); 4 labels, 0 predictions
- PK07 0001640147-23-000030: ADMITTED; 7 labels, 7 predictions; applicability applicable (applicability_rule_satisfied)
- PK07 0001652044-23-000016: ADMITTED; 10 labels, 10 predictions; applicability applicable (applicability_rule_satisfied)
- PK08 0000070858-23-000092: package_admission_refused (primary_unparseable); 6 labels, 0 predictions
- PK08 0000320193-24-000069: ADMITTED; 8 labels, 8 predictions; applicability applicable (applicability_rule_satisfied)
- PK08 0000320193-24-000123: ADMITTED; 9 labels, 9 predictions; applicability applicable (applicability_rule_satisfied)
- PK08 0001652044-23-000016: ADMITTED; 5 labels, 5 predictions; applicability applicable (applicability_rule_satisfied)
- PK09 0000018230-23-000011: ADMITTED; 7 labels, 7 predictions; applicability applicable (applicability_rule_satisfied)
- PK09 0000018230-23-000047: ADMITTED; 3 labels, 3 predictions; applicability applicable (applicability_rule_satisfied)
- PK09 0000018230-23-000056: ADMITTED; 3 labels, 3 predictions; applicability applicable (applicability_rule_satisfied)
- PK09 0000070858-23-000092: package_admission_refused (primary_unparseable); 7 labels, 0 predictions
- PK09 0000070858-23-000176: ADMITTED; 3 labels, 3 predictions; applicability applicable (applicability_rule_satisfied)
- PK09 0000070858-23-000272: ADMITTED; 3 labels, 3 predictions; applicability applicable (applicability_rule_satisfied)
- PK11 0000018230-23-000011: ADMITTED; 2 labels, 2 predictions; applicability not_applicable (issuer_class_unknown)
- PK11 0000070858-23-000092: package_admission_refused (primary_unparseable); 9 labels, 0 predictions
- PK11 0000070858-23-000176: ADMITTED; 9 labels, 9 predictions; applicability not_applicable (issuer_class_unknown)
- PK11 0000070858-23-000272: ADMITTED; 9 labels, 9 predictions; applicability not_applicable (issuer_class_unknown)
- PK11 0000320193-24-000123: ADMITTED; 2 labels, 2 predictions; applicability not_applicable (issuer_class_unknown)
- PK11 0001640147-23-000030: ADMITTED; 2 labels, 2 predictions; applicability not_applicable (issuer_class_unknown)
- PK11 0001652044-23-000016: ADMITTED; 2 labels, 2 predictions; applicability not_applicable (issuer_class_unknown)
- PK11 0001652044-23-000070: ADMITTED; 1 labels, 1 predictions; applicability not_applicable (issuer_class_unknown)
- PK11 0001652044-23-000094: ADMITTED; 1 labels, 1 predictions; applicability not_applicable (issuer_class_unknown)
- PK12 0001640147-23-000030: ADMITTED; 8 labels, 8 predictions; applicability not_applicable (sic_outside_biotech_codes)
- PK12 0001640147-23-000199: ADMITTED; 6 labels, 6 predictions; applicability not_applicable (form_outside_pack_forms)
- PK12 0001640147-23-000260: ADMITTED; 6 labels, 6 predictions; applicability not_applicable (form_outside_pack_forms)
- PK12 0001652044-23-000016: ADMITTED; 7 labels, 7 predictions; applicability not_applicable (sic_outside_biotech_codes)
- PK12 0001652044-23-000070: ADMITTED; 1 labels, 1 predictions; applicability not_applicable (form_outside_pack_forms)

## Notes

- PK10 has no labels/ directory under the held-out root: reported unavailable_research_only with reason no_held_out_labels; its report was produced over an empty label set (the frozen core labels that report underpowered over zero labels); no label was invented
- power checks come from the protocol minimum_n rows; every labelled pack carries ixbrl_inline labels only in this label generation, so the format-generalization minimum (one non-inline label per pack) is unmet and the frozen core assigns the underpowered quality label pack-wide


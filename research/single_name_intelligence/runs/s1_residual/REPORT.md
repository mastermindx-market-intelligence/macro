> HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; nothing here is a forecast, a signal, or authority
> vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1)
> identity = RETROSPECTIVE JOIN (A07), identity_resolved_as_of = security_master ingested_at

# SNI S1 residual baseline — P01/P02/P03 (historical-descriptive)

BASE: 5ef7a7f39f99232bf9b574c7603da1011ee3af66  
branch: claude/sni-s1-residual-20261011  
seal: research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json (prereg digest c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab)  
prior looks: none for v1  

## P01 — sni.s1_residual.P01

### P01|adr_baba|h=5|TRAIN|always_long|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 347
4. cluster_n: 347
5. literal_rows: 464
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 170, 'n': 347, 'hit_rate': 0.489914}, 'p_value': 0.6661759028156388, 'wilson_ci_95': (0.438, 0.542)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': -0.000121, 'ci95': [-0.0061, 0.0064]}
9. trial_accounting: {'family': 'sni.s1_residual.P01', 'literal_n': 7, 'effective_n': 7, 'declared_budget': 6}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'a74a632314b78a5051ddac6e622f0f74be9d9bd49fa4d4ec1598cd5e3719a097'}}

### P01|adr_baba|h=5|TRAIN|always_long|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 347
4. cluster_n: 347
5. literal_rows: 464
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 170, 'neg': 177, 'zeros_excluded': 0}, 'p_value': 0.7474320683398622}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': -0.000121, 'ci95': [-0.0061, 0.0064]}
9. trial_accounting: {'family': 'sni.s1_residual.P01', 'literal_n': 7, 'effective_n': 7, 'declared_budget': 6}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'a74a632314b78a5051ddac6e622f0f74be9d9bd49fa4d4ec1598cd5e3719a097'}}

### P01|adr_baba|h=5|TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))|always_long|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))
3. honest_n: 114
4. cluster_n: 114
5. literal_rows: 464
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 50, 'n': 114, 'hit_rate': 0.438596}, 'p_value': 0.9201192461074909, 'wilson_ci_95': (0.351, 0.53)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 8.8e-05, 'ci95': [-0.0094, 0.011]}
9. trial_accounting: {'family': 'sni.s1_residual.P01', 'literal_n': 7, 'effective_n': 7, 'declared_budget': 6}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '9bc90c4d68c2a964cd38e756dd249564d221a13f4035600f333bfc94c7f56da5', 'retirement_note': 'NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)'}}

### P01|adr_baba|h=5|TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))|always_long|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))
3. honest_n: 114
4. cluster_n: 114
5. literal_rows: 464
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 50, 'neg': 64, 'zeros_excluded': 0}, 'p_value': 0.2232303624555456}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 8.8e-05, 'ci95': [-0.0094, 0.011]}
9. trial_accounting: {'family': 'sni.s1_residual.P01', 'literal_n': 7, 'effective_n': 7, 'declared_budget': 6}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '9bc90c4d68c2a964cd38e756dd249564d221a13f4035600f333bfc94c7f56da5', 'retirement_note': 'NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)'}}

### P01|adr_baba|h=5|TRAIN|trail63|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 347
4. cluster_n: 347
5. literal_rows: 464
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 182, 'n': 347, 'hit_rate': 0.524496}, 'p_value': 0.19520610073617778, 'wilson_ci_95': (0.472, 0.576)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': -0.000121, 'ci95': [-0.0061, 0.0064]}
9. trial_accounting: {'family': 'sni.s1_residual.P01', 'literal_n': 7, 'effective_n': 7, 'declared_budget': 6}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'a74a632314b78a5051ddac6e622f0f74be9d9bd49fa4d4ec1598cd5e3719a097'}}

### P01|adr_baba|h=5|TRAIN|trail63|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 347
4. cluster_n: 347
5. literal_rows: 464
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 170, 'neg': 177, 'zeros_excluded': 0}, 'p_value': 0.7474320683398622}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': -0.000121, 'ci95': [-0.0061, 0.0064]}
9. trial_accounting: {'family': 'sni.s1_residual.P01', 'literal_n': 7, 'effective_n': 7, 'declared_budget': 6}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'a74a632314b78a5051ddac6e622f0f74be9d9bd49fa4d4ec1598cd5e3719a097'}}

### P01|adr_baba|h=5|TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))|trail63|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))
3. honest_n: 114
4. cluster_n: 114
5. literal_rows: 464
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 57, 'n': 114, 'hit_rate': 0.5}, 'p_value': 0.5372825193716376, 'wilson_ci_95': (0.41, 0.59)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 8.8e-05, 'ci95': [-0.0094, 0.011]}
9. trial_accounting: {'family': 'sni.s1_residual.P01', 'literal_n': 7, 'effective_n': 7, 'declared_budget': 6}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '9bc90c4d68c2a964cd38e756dd249564d221a13f4035600f333bfc94c7f56da5', 'retirement_note': 'NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)'}}

### P01|adr_baba|h=5|TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))|trail63|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))
3. honest_n: 114
4. cluster_n: 114
5. literal_rows: 464
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 50, 'neg': 64, 'zeros_excluded': 0}, 'p_value': 0.2232303624555456}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 8.8e-05, 'ci95': [-0.0094, 0.011]}
9. trial_accounting: {'family': 'sni.s1_residual.P01', 'literal_n': 7, 'effective_n': 7, 'declared_budget': 6}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '9bc90c4d68c2a964cd38e756dd249564d221a13f4035600f333bfc94c7f56da5', 'retirement_note': 'NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)'}}

### P01|adr_baba|h=21|TRAIN|always_long|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 94
4. cluster_n: 94
5. literal_rows: 127
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 46, 'n': 94, 'hit_rate': 0.489362}, 'p_value': 0.6214054629287974, 'wilson_ci_95': (0.391, 0.589)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': -0.004505, 'ci95': [-0.0269, 0.0155]}
9. trial_accounting: {'family': 'sni.s1_residual.P01', 'literal_n': 7, 'effective_n': 7, 'declared_budget': 6}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '8fe185843216059986f5e475ca287c7ce920421f32c60d432485a8c8cb91ba17'}}

### P01|adr_baba|h=21|TRAIN|always_long|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 94
4. cluster_n: 94
5. literal_rows: 127
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 46, 'neg': 48, 'zeros_excluded': 0}, 'p_value': 0.9179230673157426}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': -0.004505, 'ci95': [-0.0269, 0.0155]}
9. trial_accounting: {'family': 'sni.s1_residual.P01', 'literal_n': 7, 'effective_n': 7, 'declared_budget': 6}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '8fe185843216059986f5e475ca287c7ce920421f32c60d432485a8c8cb91ba17'}}

### P01|adr_baba|h=21|TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))|always_long|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))
3. honest_n: 31
4. cluster_n: 31
5. literal_rows: 127
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 15, 'n': 31, 'hit_rate': 0.483871}, 'p_value': 0.639949934091419, 'wilson_ci_95': (0.32, 0.652)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': -0.001093, 'ci95': [-0.0433, 0.0396]}
9. trial_accounting: {'family': 'sni.s1_residual.P01', 'literal_n': 7, 'effective_n': 7, 'declared_budget': 6}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '06c2446afa46cb68821f5afe928bf7792360de38529698fb6d1aad77e7bda510', 'retirement_note': 'NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)'}}

### P01|adr_baba|h=21|TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))|always_long|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))
3. honest_n: 31
4. cluster_n: 31
5. literal_rows: 127
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 15, 'neg': 16, 'zeros_excluded': 0}, 'p_value': 1.0}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': -0.001093, 'ci95': [-0.0433, 0.0396]}
9. trial_accounting: {'family': 'sni.s1_residual.P01', 'literal_n': 7, 'effective_n': 7, 'declared_budget': 6}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '06c2446afa46cb68821f5afe928bf7792360de38529698fb6d1aad77e7bda510', 'retirement_note': 'NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)'}}

### P01|adr_baba|h=21|TRAIN|trail63|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 94
4. cluster_n: 94
5. literal_rows: 127
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 53, 'n': 94, 'hit_rate': 0.56383}, 'p_value': 0.12822117446648462, 'wilson_ci_95': (0.463, 0.66)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': -0.004505, 'ci95': [-0.0269, 0.0155]}
9. trial_accounting: {'family': 'sni.s1_residual.P01', 'literal_n': 7, 'effective_n': 7, 'declared_budget': 6}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '8fe185843216059986f5e475ca287c7ce920421f32c60d432485a8c8cb91ba17'}}

### P01|adr_baba|h=21|TRAIN|trail63|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 94
4. cluster_n: 94
5. literal_rows: 127
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 46, 'neg': 48, 'zeros_excluded': 0}, 'p_value': 0.9179230673157426}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': -0.004505, 'ci95': [-0.0269, 0.0155]}
9. trial_accounting: {'family': 'sni.s1_residual.P01', 'literal_n': 7, 'effective_n': 7, 'declared_budget': 6}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '8fe185843216059986f5e475ca287c7ce920421f32c60d432485a8c8cb91ba17'}}

### P01|adr_baba|h=21|TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))|trail63|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))
3. honest_n: 31
4. cluster_n: 31
5. literal_rows: 127
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 14, 'n': 31, 'hit_rate': 0.451613}, 'p_value': 0.7634351700544357, 'wilson_ci_95': (0.292, 0.622)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': -0.001093, 'ci95': [-0.0433, 0.0396]}
9. trial_accounting: {'family': 'sni.s1_residual.P01', 'literal_n': 7, 'effective_n': 7, 'declared_budget': 6}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '06c2446afa46cb68821f5afe928bf7792360de38529698fb6d1aad77e7bda510', 'retirement_note': 'NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)'}}

### P01|adr_baba|h=21|TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))|trail63|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))
3. honest_n: 31
4. cluster_n: 31
5. literal_rows: 127
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 15, 'neg': 16, 'zeros_excluded': 0}, 'p_value': 1.0}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': -0.001093, 'ci95': [-0.0433, 0.0396]}
9. trial_accounting: {'family': 'sni.s1_residual.P01', 'literal_n': 7, 'effective_n': 7, 'declared_budget': 6}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '06c2446afa46cb68821f5afe928bf7792360de38529698fb6d1aad77e7bda510', 'retirement_note': 'NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)'}}

### P01|adr_baba|h=63|TRAIN|always_long|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 32
4. cluster_n: 32
5. literal_rows: 44
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 14, 'n': 32, 'hit_rate': 0.4375}, 'p_value': 0.8114572062622756, 'wilson_ci_95': (0.282, 0.607)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': -0.002808, 'ci95': [-0.0776, 0.07]}
9. trial_accounting: {'family': 'sni.s1_residual.P01', 'literal_n': 7, 'effective_n': 7, 'declared_budget': 6}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '53f07e57dc5145a79c2e92051e2f4426f759b92571603d111dd58dfa9076e4c3'}}

### P01|adr_baba|h=63|TRAIN|always_long|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 32
4. cluster_n: 32
5. literal_rows: 44
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 14, 'neg': 18, 'zeros_excluded': 0}, 'p_value': 0.5966148958541453}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': -0.002808, 'ci95': [-0.0776, 0.07]}
9. trial_accounting: {'family': 'sni.s1_residual.P01', 'literal_n': 7, 'effective_n': 7, 'declared_budget': 6}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '53f07e57dc5145a79c2e92051e2f4426f759b92571603d111dd58dfa9076e4c3'}}

### P01|adr_baba|h=63|TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))|always_long|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))
3. honest_n: 10
4. cluster_n: 10
5. literal_rows: 44
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 4, 'n': 10, 'hit_rate': 0.4}, 'p_value': 0.828125, 'wilson_ci_95': (0.168, 0.687)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.013709, 'ci95': [-0.0963, 0.1193]}
9. trial_accounting: {'family': 'sni.s1_residual.P01', 'literal_n': 7, 'effective_n': 7, 'declared_budget': 6}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'ab7323ec976800473cb14e11bdd64a5535201a88a9edf6fbbe35b9850470526e', 'retirement_note': 'NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)'}}

### P01|adr_baba|h=63|TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))|always_long|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))
3. honest_n: 10
4. cluster_n: 10
5. literal_rows: 44
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 4, 'neg': 6, 'zeros_excluded': 0}, 'p_value': 0.75390625}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.013709, 'ci95': [-0.0963, 0.1193]}
9. trial_accounting: {'family': 'sni.s1_residual.P01', 'literal_n': 7, 'effective_n': 7, 'declared_budget': 6}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'ab7323ec976800473cb14e11bdd64a5535201a88a9edf6fbbe35b9850470526e', 'retirement_note': 'NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)'}}

### P01|adr_baba|h=63|TRAIN|trail63|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 32
4. cluster_n: 32
5. literal_rows: 44
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 16, 'n': 32, 'hit_rate': 0.5}, 'p_value': 0.5699749670457095, 'wilson_ci_95': (0.336, 0.664)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': -0.002808, 'ci95': [-0.0776, 0.07]}
9. trial_accounting: {'family': 'sni.s1_residual.P01', 'literal_n': 7, 'effective_n': 7, 'declared_budget': 6}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '53f07e57dc5145a79c2e92051e2f4426f759b92571603d111dd58dfa9076e4c3'}}

### P01|adr_baba|h=63|TRAIN|trail63|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 32
4. cluster_n: 32
5. literal_rows: 44
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 14, 'neg': 18, 'zeros_excluded': 0}, 'p_value': 0.5966148958541453}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': -0.002808, 'ci95': [-0.0776, 0.07]}
9. trial_accounting: {'family': 'sni.s1_residual.P01', 'literal_n': 7, 'effective_n': 7, 'declared_budget': 6}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '53f07e57dc5145a79c2e92051e2f4426f759b92571603d111dd58dfa9076e4c3'}}

### P01|adr_baba|h=63|TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))|trail63|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))
3. honest_n: 10
4. cluster_n: 10
5. literal_rows: 44
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 4, 'n': 10, 'hit_rate': 0.4}, 'p_value': 0.828125, 'wilson_ci_95': (0.168, 0.687)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.013709, 'ci95': [-0.0963, 0.1193]}
9. trial_accounting: {'family': 'sni.s1_residual.P01', 'literal_n': 7, 'effective_n': 7, 'declared_budget': 6}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'ab7323ec976800473cb14e11bdd64a5535201a88a9edf6fbbe35b9850470526e', 'retirement_note': 'NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)'}}

### P01|adr_baba|h=63|TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))|trail63|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))
3. honest_n: 10
4. cluster_n: 10
5. literal_rows: 44
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 4, 'neg': 6, 'zeros_excluded': 0}, 'p_value': 0.75390625}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.013709, 'ci95': [-0.0963, 0.1193]}
9. trial_accounting: {'family': 'sni.s1_residual.P01', 'literal_n': 7, 'effective_n': 7, 'declared_budget': 6}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'ab7323ec976800473cb14e11bdd64a5535201a88a9edf6fbbe35b9850470526e', 'retirement_note': 'NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)'}}

## P02 — sni.s1_residual.P02

### P02|hkd_9988|h=5|TRAIN|always_long|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 121
4. cluster_n: 121
5. literal_rows: 239
6. exclusions: {'excluded_listed': 4, 'confounded': 0, 'absorbed': 0, 'purged': 1, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 4, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 49, 'n': 121, 'hit_rate': 0.404959}, 'p_value': 0.9856484004131315, 'wilson_ci_95': (0.322, 0.494)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': -0.003117, 'ci95': [-0.0117, 0.0063]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'd6813de5b6b4c86490a940d285710593ec579c4f6f18e328a50452627fda7f51'}}

### P02|hkd_9988|h=5|TRAIN|always_long|H0_2

1. null: median excess departs from zero (descriptive, non-confirmatory)
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 121
4. cluster_n: 121
5. literal_rows: 239
6. exclusions: {'excluded_listed': 4, 'confounded': 0, 'absorbed': 0, 'purged': 1, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 4, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 49, 'neg': 72, 'zeros_excluded': 0}, 'p_value': 0.045051739725735895}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': -0.003117, 'ci95': [-0.0117, 0.0063]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'd6813de5b6b4c86490a940d285710593ec579c4f6f18e328a50452627fda7f51'}}

### P02|hkd_9988|h=5|TUNE|always_long|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE
3. honest_n: 111
4. cluster_n: 111
5. literal_rows: 239
6. exclusions: {'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 1, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 53, 'n': 111, 'hit_rate': 0.477477}, 'p_value': 0.7153898860982126, 'wilson_ci_95': (0.387, 0.57)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.001611, 'ci95': [-0.0059, 0.0099]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '9995b84bb3577243ccb8a33f84613fba4d5b1c9fdfb63d672fcd221bf2f41150'}}

### P02|hkd_9988|h=5|TUNE|always_long|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE
3. honest_n: 111
4. cluster_n: 111
5. literal_rows: 239
6. exclusions: {'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 1, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 53, 'neg': 58, 'zeros_excluded': 0}, 'p_value': 0.7043793154248914}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.001611, 'ci95': [-0.0059, 0.0099]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '9995b84bb3577243ccb8a33f84613fba4d5b1c9fdfb63d672fcd221bf2f41150'}}

### P02|hkd_9988|h=5|TRAIN|trail63|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 119
4. cluster_n: 119
5. literal_rows: 239
6. exclusions: {'excluded_listed': 4, 'confounded': 0, 'absorbed': 0, 'purged': 1, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 4, 'direction_0_abstain': 2, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 64, 'n': 119, 'hit_rate': 0.537815}, 'p_value': 0.23174408831138207, 'wilson_ci_95': (0.448, 0.625)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': -0.003593, 'ci95': [-0.0128, 0.0064]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'd6813de5b6b4c86490a940d285710593ec579c4f6f18e328a50452627fda7f51'}}

### P02|hkd_9988|h=5|TRAIN|trail63|H0_2

1. null: median excess departs from zero (descriptive, non-confirmatory)
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 119
4. cluster_n: 119
5. literal_rows: 239
6. exclusions: {'excluded_listed': 4, 'confounded': 0, 'absorbed': 0, 'purged': 1, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 4, 'direction_0_abstain': 2, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 47, 'neg': 72, 'zeros_excluded': 0}, 'p_value': 0.027379102500930414}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': -0.003593, 'ci95': [-0.0128, 0.0064]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'd6813de5b6b4c86490a940d285710593ec579c4f6f18e328a50452627fda7f51'}}

### P02|hkd_9988|h=5|TUNE|trail63|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE
3. honest_n: 111
4. cluster_n: 111
5. literal_rows: 239
6. exclusions: {'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 1, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 54, 'n': 111, 'hit_rate': 0.486486}, 'p_value': 0.6478103422875543, 'wilson_ci_95': (0.396, 0.578)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.001611, 'ci95': [-0.0059, 0.0099]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '9995b84bb3577243ccb8a33f84613fba4d5b1c9fdfb63d672fcd221bf2f41150'}}

### P02|hkd_9988|h=5|TUNE|trail63|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE
3. honest_n: 111
4. cluster_n: 111
5. literal_rows: 239
6. exclusions: {'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 1, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 53, 'neg': 58, 'zeros_excluded': 0}, 'p_value': 0.7043793154248914}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.001611, 'ci95': [-0.0059, 0.0099]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '9995b84bb3577243ccb8a33f84613fba4d5b1c9fdfb63d672fcd221bf2f41150'}}

### P02|hkd_9988|h=21|TRAIN|always_long|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 33
4. cluster_n: 33
5. literal_rows: 66
6. exclusions: {'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 14, 'n': 33, 'hit_rate': 0.424242}, 'p_value': 0.8518968157004565, 'wilson_ci_95': (0.272, 0.592)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': -0.020065, 'ci95': [-0.0504, 0.0138]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '09e867fee8dbda33d41af876d1715f7b0bcb195434d9766b9eb482ef019f2889'}}

### P02|hkd_9988|h=21|TRAIN|always_long|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 33
4. cluster_n: 33
5. literal_rows: 66
6. exclusions: {'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 14, 'neg': 19, 'zeros_excluded': 0}, 'p_value': 0.48685024166479707}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': -0.020065, 'ci95': [-0.0504, 0.0138]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '09e867fee8dbda33d41af876d1715f7b0bcb195434d9766b9eb482ef019f2889'}}

### P02|hkd_9988|h=21|TUNE|always_long|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE
3. honest_n: 28
4. cluster_n: 28
5. literal_rows: 66
6. exclusions: {'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 11, 'n': 28, 'hit_rate': 0.392857}, 'p_value': 0.9075333289802074, 'wilson_ci_95': (0.236, 0.576)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.008362, 'ci95': [-0.0319, 0.0557]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '36fbfb97f368e64e9790096395accd141a70500cc88c3c3d79e8bf7324e61765'}}

### P02|hkd_9988|h=21|TUNE|always_long|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE
3. honest_n: 28
4. cluster_n: 28
5. literal_rows: 66
6. exclusions: {'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 11, 'neg': 17, 'zeros_excluded': 0}, 'p_value': 0.34492845088243484}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.008362, 'ci95': [-0.0319, 0.0557]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '36fbfb97f368e64e9790096395accd141a70500cc88c3c3d79e8bf7324e61765'}}

### P02|hkd_9988|h=21|TRAIN|trail63|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 33
4. cluster_n: 33
5. literal_rows: 66
6. exclusions: {'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 12, 'n': 33, 'hit_rate': 0.363636}, 'p_value': 0.9599283437710255, 'wilson_ci_95': (0.222, 0.534)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': -0.020065, 'ci95': [-0.0504, 0.0138]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '09e867fee8dbda33d41af876d1715f7b0bcb195434d9766b9eb482ef019f2889'}}

### P02|hkd_9988|h=21|TRAIN|trail63|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 33
4. cluster_n: 33
5. literal_rows: 66
6. exclusions: {'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 14, 'neg': 19, 'zeros_excluded': 0}, 'p_value': 0.48685024166479707}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': -0.020065, 'ci95': [-0.0504, 0.0138]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '09e867fee8dbda33d41af876d1715f7b0bcb195434d9766b9eb482ef019f2889'}}

### P02|hkd_9988|h=21|TUNE|trail63|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE
3. honest_n: 27
4. cluster_n: 27
5. literal_rows: 66
6. exclusions: {'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 1, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 12, 'n': 27, 'hit_rate': 0.444444}, 'p_value': 0.7789658308029175, 'wilson_ci_95': (0.276, 0.627)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.012873, 'ci95': [-0.0261, 0.0583]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '36fbfb97f368e64e9790096395accd141a70500cc88c3c3d79e8bf7324e61765'}}

### P02|hkd_9988|h=21|TUNE|trail63|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE
3. honest_n: 27
4. cluster_n: 27
5. literal_rows: 66
6. exclusions: {'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 1, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 11, 'neg': 16, 'zeros_excluded': 0}, 'p_value': 0.44206833839416504}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.012873, 'ci95': [-0.0261, 0.0583]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '36fbfb97f368e64e9790096395accd141a70500cc88c3c3d79e8bf7324e61765'}}

### P02|hkd_9988|h=63|TRAIN|always_long|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 11
4. cluster_n: 11
5. literal_rows: 23
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 2, 'n': 11, 'hit_rate': 0.181818}, 'p_value': 0.994140625, 'wilson_ci_95': (0.051, 0.477)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': -0.070169, 'ci95': [-0.1097, -0.0269]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '5c21991c0971cef2da0faf7798e69eba1bf1518f8466e6e8630b7ec695850b4f'}}

### P02|hkd_9988|h=63|TRAIN|always_long|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 11
4. cluster_n: 11
5. literal_rows: 23
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 2, 'neg': 9, 'zeros_excluded': 0}, 'p_value': 0.0654296875}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': -0.070169, 'ci95': [-0.1097, -0.0269]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '5c21991c0971cef2da0faf7798e69eba1bf1518f8466e6e8630b7ec695850b4f'}}

### P02|hkd_9988|h=63|TUNE|always_long|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE
3. honest_n: 10
4. cluster_n: 10
5. literal_rows: 23
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 5, 'n': 10, 'hit_rate': 0.5}, 'p_value': 0.623046875, 'wilson_ci_95': (0.237, 0.763)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.00506, 'ci95': [-0.0598, 0.0779]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'e2695c6bbb7ecdcf80c14ddc7a13031818a93c83b0116386bb48baf095b52163'}}

### P02|hkd_9988|h=63|TUNE|always_long|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE
3. honest_n: 10
4. cluster_n: 10
5. literal_rows: 23
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 5, 'neg': 5, 'zeros_excluded': 0}, 'p_value': 1.0}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.00506, 'ci95': [-0.0598, 0.0779]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'e2695c6bbb7ecdcf80c14ddc7a13031818a93c83b0116386bb48baf095b52163'}}

### P02|hkd_9988|h=63|TRAIN|trail63|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 11
4. cluster_n: 11
5. literal_rows: 23
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 7, 'n': 11, 'hit_rate': 0.636364}, 'p_value': 0.2744140625, 'wilson_ci_95': (0.354, 0.848)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': -0.070169, 'ci95': [-0.1097, -0.0269]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '5c21991c0971cef2da0faf7798e69eba1bf1518f8466e6e8630b7ec695850b4f'}}

### P02|hkd_9988|h=63|TRAIN|trail63|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 11
4. cluster_n: 11
5. literal_rows: 23
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 2, 'neg': 9, 'zeros_excluded': 0}, 'p_value': 0.0654296875}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': -0.070169, 'ci95': [-0.1097, -0.0269]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '5c21991c0971cef2da0faf7798e69eba1bf1518f8466e6e8630b7ec695850b4f'}}

### P02|hkd_9988|h=63|TUNE|trail63|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE
3. honest_n: 10
4. cluster_n: 10
5. literal_rows: 23
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 6, 'n': 10, 'hit_rate': 0.6}, 'p_value': 0.376953125, 'wilson_ci_95': (0.313, 0.832)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.00506, 'ci95': [-0.0598, 0.0779]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'e2695c6bbb7ecdcf80c14ddc7a13031818a93c83b0116386bb48baf095b52163'}}

### P02|hkd_9988|h=63|TUNE|trail63|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE
3. honest_n: 10
4. cluster_n: 10
5. literal_rows: 23
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 5, 'neg': 5, 'zeros_excluded': 0}, 'p_value': 1.0}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.00506, 'ci95': [-0.0598, 0.0779]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'e2695c6bbb7ecdcf80c14ddc7a13031818a93c83b0116386bb48baf095b52163'}}

### P02|hkd_0700|h=5|TRAIN|always_long|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 404
4. cluster_n: 404
5. literal_rows: 881
6. exclusions: {'excluded_listed': 363, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 360, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 3, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 200, 'n': 404, 'hit_rate': 0.49505}, 'p_value': 0.5982078220201428, 'wilson_ci_95': (0.447, 0.544)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.00231, 'ci95': [-0.0006, 0.0054]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '15e08b13690a345d6a92fdc5bd4dceffd1bc54693bf40607150be1c8bcee5e3e'}}

### P02|hkd_0700|h=5|TRAIN|always_long|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 404
4. cluster_n: 404
5. literal_rows: 881
6. exclusions: {'excluded_listed': 363, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 360, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 3, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 200, 'neg': 204, 'zeros_excluded': 0}, 'p_value': 0.8813758029467572}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.00231, 'ci95': [-0.0006, 0.0054]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '15e08b13690a345d6a92fdc5bd4dceffd1bc54693bf40607150be1c8bcee5e3e'}}

### P02|hkd_0700|h=5|TUNE|always_long|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE
3. honest_n: 109
4. cluster_n: 109
5. literal_rows: 881
6. exclusions: {'excluded_listed': 2, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 2, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 60, 'n': 109, 'hit_rate': 0.550459}, 'p_value': 0.16909270609833058, 'wilson_ci_95': (0.457, 0.641)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.00037, 'ci95': [-0.0051, 0.0055]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '85cdf5454f187e53d8c495be313c25b004c33569b93d2d1688065ca413eaa5aa'}}

### P02|hkd_0700|h=5|TUNE|always_long|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE
3. honest_n: 109
4. cluster_n: 109
5. literal_rows: 881
6. exclusions: {'excluded_listed': 2, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 2, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 60, 'neg': 49, 'zeros_excluded': 0}, 'p_value': 0.33818541219666115}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.00037, 'ci95': [-0.0051, 0.0055]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '85cdf5454f187e53d8c495be313c25b004c33569b93d2d1688065ca413eaa5aa'}}

### P02|hkd_0700|h=5|TRAIN|trail63|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 400
4. cluster_n: 400
5. literal_rows: 881
6. exclusions: {'excluded_listed': 363, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 360, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 3, 'direction_0_abstain': 4, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 190, 'n': 400, 'hit_rate': 0.475}, 'p_value': 0.853145940919109, 'wilson_ci_95': (0.427, 0.524)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.002081, 'ci95': [-0.0009, 0.0051]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '15e08b13690a345d6a92fdc5bd4dceffd1bc54693bf40607150be1c8bcee5e3e'}}

### P02|hkd_0700|h=5|TRAIN|trail63|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 400
4. cluster_n: 400
5. literal_rows: 881
6. exclusions: {'excluded_listed': 363, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 360, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 3, 'direction_0_abstain': 4, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 196, 'neg': 204, 'zeros_excluded': 0}, 'p_value': 0.7263869151831212}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.002081, 'ci95': [-0.0009, 0.0051]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '15e08b13690a345d6a92fdc5bd4dceffd1bc54693bf40607150be1c8bcee5e3e'}}

### P02|hkd_0700|h=5|TUNE|trail63|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE
3. honest_n: 104
4. cluster_n: 104
5. literal_rows: 881
6. exclusions: {'excluded_listed': 2, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 2, 'direction_0_abstain': 5, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 53, 'n': 104, 'hit_rate': 0.509615}, 'p_value': 0.46097441381321547, 'wilson_ci_95': (0.415, 0.604)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.001801, 'ci95': [-0.0037, 0.0068]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '85cdf5454f187e53d8c495be313c25b004c33569b93d2d1688065ca413eaa5aa'}}

### P02|hkd_0700|h=5|TUNE|trail63|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE
3. honest_n: 104
4. cluster_n: 104
5. literal_rows: 881
6. exclusions: {'excluded_listed': 2, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 2, 'direction_0_abstain': 5, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 59, 'neg': 45, 'zeros_excluded': 0}, 'p_value': 0.20217310609617567}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.001801, 'ci95': [-0.0037, 0.0068]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '85cdf5454f187e53d8c495be313c25b004c33569b93d2d1688065ca413eaa5aa'}}

### P02|hkd_0700|h=21|TRAIN|always_long|H0_1

1. null: direction at horizon h; the hit rate departs from 0.50 (descriptive, non-confirmatory)
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 109
4. cluster_n: 109
5. literal_rows: 241
6. exclusions: {'excluded_listed': 100, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 98, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 2, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 67, 'n': 109, 'hit_rate': 0.614679}, 'p_value': 0.010543202856568812, 'wilson_ci_95': (0.521, 0.701)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.016449, 'ci95': [0.0042, 0.0294]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'ea98de67378588d71e43233ece716fe5f1c91f8581899755a55a5bc70a3ebea6'}}

### P02|hkd_0700|h=21|TRAIN|always_long|H0_2

1. null: median excess departs from zero (descriptive, non-confirmatory)
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 109
4. cluster_n: 109
5. literal_rows: 241
6. exclusions: {'excluded_listed': 100, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 98, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 2, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 67, 'neg': 42, 'zeros_excluded': 0}, 'p_value': 0.021086405713137624}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.016449, 'ci95': [0.0042, 0.0294]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'ea98de67378588d71e43233ece716fe5f1c91f8581899755a55a5bc70a3ebea6'}}

### P02|hkd_0700|h=21|TUNE|always_long|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE
3. honest_n: 28
4. cluster_n: 28
5. literal_rows: 241
6. exclusions: {'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 14, 'n': 28, 'hit_rate': 0.5}, 'p_value': 0.5747229903936386, 'wilson_ci_95': (0.326, 0.674)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.005602, 'ci95': [-0.0138, 0.0242]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'f34cb11f8b1604082ed66d973497c5382864d89b77a37d38afde3fdd50f1a422'}}

### P02|hkd_0700|h=21|TUNE|always_long|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE
3. honest_n: 28
4. cluster_n: 28
5. literal_rows: 241
6. exclusions: {'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 14, 'neg': 14, 'zeros_excluded': 0}, 'p_value': 1.0}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.005602, 'ci95': [-0.0138, 0.0242]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'f34cb11f8b1604082ed66d973497c5382864d89b77a37d38afde3fdd50f1a422'}}

### P02|hkd_0700|h=21|TRAIN|trail63|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 107
4. cluster_n: 107
5. literal_rows: 241
6. exclusions: {'excluded_listed': 100, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 98, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 2, 'direction_0_abstain': 2, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 58, 'n': 107, 'hit_rate': 0.542056}, 'p_value': 0.21972005088954139, 'wilson_ci_95': (0.448, 0.633)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.016209, 'ci95': [0.0041, 0.0301]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'ea98de67378588d71e43233ece716fe5f1c91f8581899755a55a5bc70a3ebea6'}}

### P02|hkd_0700|h=21|TRAIN|trail63|H0_2

1. null: median excess departs from zero (descriptive, non-confirmatory)
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 107
4. cluster_n: 107
5. literal_rows: 241
6. exclusions: {'excluded_listed': 100, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 98, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 2, 'direction_0_abstain': 2, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 65, 'neg': 42, 'zeros_excluded': 0}, 'p_value': 0.03294666029982694}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.016209, 'ci95': [0.0041, 0.0301]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'ea98de67378588d71e43233ece716fe5f1c91f8581899755a55a5bc70a3ebea6'}}

### P02|hkd_0700|h=21|TUNE|trail63|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE
3. honest_n: 27
4. cluster_n: 27
5. literal_rows: 241
6. exclusions: {'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 1, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 14, 'n': 27, 'hit_rate': 0.518519}, 'p_value': 0.5, 'wilson_ci_95': (0.34, 0.693)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.004787, 'ci95': [-0.015, 0.0244]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'f34cb11f8b1604082ed66d973497c5382864d89b77a37d38afde3fdd50f1a422'}}

### P02|hkd_0700|h=21|TUNE|trail63|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE
3. honest_n: 27
4. cluster_n: 27
5. literal_rows: 241
6. exclusions: {'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 1, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 13, 'neg': 14, 'zeros_excluded': 0}, 'p_value': 1.0}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.004787, 'ci95': [-0.015, 0.0244]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'f34cb11f8b1604082ed66d973497c5382864d89b77a37d38afde3fdd50f1a422'}}

### P02|hkd_0700|h=63|TRAIN|always_long|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 37
4. cluster_n: 37
5. literal_rows: 83
6. exclusions: {'excluded_listed': 34, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 34, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 22, 'n': 37, 'hit_rate': 0.594595}, 'p_value': 0.1620043000439182, 'wilson_ci_95': (0.435, 0.737)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.040692, 'ci95': [0.0061, 0.074]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '3f49baee54ff008220872bf37be99f9be9394e976bdd0d635d8d0dd7cf235334'}}

### P02|hkd_0700|h=63|TRAIN|always_long|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 37
4. cluster_n: 37
5. literal_rows: 83
6. exclusions: {'excluded_listed': 34, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 34, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 22, 'neg': 15, 'zeros_excluded': 0}, 'p_value': 0.3240086000878364}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.040692, 'ci95': [0.0061, 0.074]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '3f49baee54ff008220872bf37be99f9be9394e976bdd0d635d8d0dd7cf235334'}}

### P02|hkd_0700|h=63|TUNE|always_long|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE
3. honest_n: 10
4. cluster_n: 10
5. literal_rows: 83
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 5, 'n': 10, 'hit_rate': 0.5}, 'p_value': 0.623046875, 'wilson_ci_95': (0.237, 0.763)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.000881, 'ci95': [-0.0598, 0.0551]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '41221dbbdae80eb3b0721521f438635a78679f26f8c9977eebdf086c61c286c2'}}

### P02|hkd_0700|h=63|TUNE|always_long|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE
3. honest_n: 10
4. cluster_n: 10
5. literal_rows: 83
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 5, 'neg': 5, 'zeros_excluded': 0}, 'p_value': 1.0}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.000881, 'ci95': [-0.0598, 0.0551]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '41221dbbdae80eb3b0721521f438635a78679f26f8c9977eebdf086c61c286c2'}}

### P02|hkd_0700|h=63|TRAIN|trail63|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 37
4. cluster_n: 37
5. literal_rows: 83
6. exclusions: {'excluded_listed': 34, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 34, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 20, 'n': 37, 'hit_rate': 0.540541}, 'p_value': 0.3714146793645341, 'wilson_ci_95': (0.384, 0.69)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.040692, 'ci95': [0.0061, 0.074]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '3f49baee54ff008220872bf37be99f9be9394e976bdd0d635d8d0dd7cf235334'}}

### P02|hkd_0700|h=63|TRAIN|trail63|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 37
4. cluster_n: 37
5. literal_rows: 83
6. exclusions: {'excluded_listed': 34, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 34, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 22, 'neg': 15, 'zeros_excluded': 0}, 'p_value': 0.3240086000878364}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.040692, 'ci95': [0.0061, 0.074]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '3f49baee54ff008220872bf37be99f9be9394e976bdd0d635d8d0dd7cf235334'}}

### P02|hkd_0700|h=63|TUNE|trail63|H0_1

1. null: direction at horizon h; accuracy indistinguishable from a coin flip at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE
3. honest_n: 10
4. cluster_n: 10
5. literal_rows: 83
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact binomial (math.comb), one-sided greater', 'sidedness': 'one-sided (greater)', 'alpha': 0.05, 'statistic': {'hits': 7, 'n': 10, 'hit_rate': 0.7}, 'p_value': 0.171875, 'wilson_ci_95': (0.397, 0.892)}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.000881, 'ci95': [-0.0598, 0.0551]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '41221dbbdae80eb3b0721521f438635a78679f26f8c9977eebdf086c61c286c2'}}

### P02|hkd_0700|h=63|TUNE|trail63|H0_2

1. null: median excess indistinguishable from zero at the 0.05 level
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE
3. honest_n: 10
4. cluster_n: 10
5. literal_rows: 83
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}
7. test: {'name': 'exact sign test on excess', 'sidedness': 'two-sided', 'alpha': 0.05, 'statistic': {'pos': 5, 'neg': 5, 'zeros_excluded': 0}, 'p_value': 1.0}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean': 0.000881, 'ci95': [-0.0598, 0.0551]}
9. trial_accounting: {'family': 'sni.s1_residual.P02', 'literal_n': 12, 'effective_n': 12, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '41221dbbdae80eb3b0721521f438635a78679f26f8c9977eebdf086c61c286c2'}}

## P03 — sni.s1_residual.P03

### P03|adr_baba|h=5|TRAIN|M1_vs_M0

1. null: incremental explanation of M1 over M0 is zero on this split; the pre-registered S0 criterion is met (descriptive, non-confirmatory)
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 347
4. cluster_n: 347
5. literal_rows: 1383
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.18408397, 'paired_units': 347}, 'verdict': 'M1 beats M0 on this split (S0 criterion met; descriptive, non-confirmatory)'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.000664765609, 'ci95': [0.0003, 0.001], 'delta_R2': 0.18408397}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '47e030d3f9012137e5faf8753331343f759ea1e2bf9e94d42c3dda1b8d6cd899'}}

### P03|adr_baba|h=5|TUNE|M1_vs_M0

1. null: incremental explanation of M1 over M0 is zero on this split; the pre-registered S0 criterion is met (descriptive, non-confirmatory)
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE; NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)
3. honest_n: 114
4. cluster_n: 114
5. literal_rows: 1383
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.10975489, 'paired_units': 114}, 'verdict': 'M1 beats M0 on this split (S0 criterion met; descriptive, non-confirmatory)'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.000395661009, 'ci95': [0.0001, 0.0007], 'delta_R2': 0.10975489}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'a2fbca39f96b83d6b413cc22e182d07566dc078041420857620592db7edbe78a'}}

### P03|adr_baba|h=5|TRAIN|M2_vs_M1

1. null: incremental explanation of M2 over M1 is zero on this split; the pre-registered S0 criterion is met (descriptive, non-confirmatory)
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 347
4. cluster_n: 347
5. literal_rows: 1383
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.52577345, 'paired_units': 347}, 'verdict': 'M2 beats M1 on this split (S0 criterion met; descriptive, non-confirmatory)'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.00189867755, 'ci95': [0.0012, 0.0028], 'delta_R2': 0.52577345}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '47e030d3f9012137e5faf8753331343f759ea1e2bf9e94d42c3dda1b8d6cd899'}}

### P03|adr_baba|h=5|TUNE|M2_vs_M1

1. null: incremental explanation of M2 over M1 is zero on this split; the pre-registered S0 criterion is met (descriptive, non-confirmatory)
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE; NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)
3. honest_n: 114
4. cluster_n: 114
5. literal_rows: 1383
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.54676282, 'paired_units': 114}, 'verdict': 'M2 beats M1 on this split (S0 criterion met; descriptive, non-confirmatory)'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.001971053276, 'ci95': [0.0011, 0.003], 'delta_R2': 0.54676282}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'a2fbca39f96b83d6b413cc22e182d07566dc078041420857620592db7edbe78a'}}

### P03|adr_baba|h=5|TRAIN|IPCA_vs_M1

1. null: incremental explanation of IPCA over M1 is zero on this split; the pre-registered S0 criterion is not met
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN; IN-SAMPLE for Gamma
3. honest_n: 346
4. cluster_n: 346
5. literal_rows: 1383
6. exclusions: {'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 1, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.01351695, 'paired_units': 346}, 'verdict': 'KILL/HOLD-AS-RESEARCH — IPCA shows no incremental explanation over M1 on this split'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 4.8502577e-05, 'ci95': [-0.0, 0.0002], 'delta_R2': 0.01351695}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '47e030d3f9012137e5faf8753331343f759ea1e2bf9e94d42c3dda1b8d6cd899'}}

### P03|adr_baba|h=5|TUNE|IPCA_vs_M1

1. null: incremental explanation of IPCA over M1 is zero on this split; the pre-registered S0 criterion is not met
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE; NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)
3. honest_n: 114
4. cluster_n: 114
5. literal_rows: 1383
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': -0.00290051, 'paired_units': 114}, 'verdict': 'KILL/HOLD-AS-RESEARCH — IPCA shows no incremental explanation over M1 on this split'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': -1.0456181e-05, 'ci95': [-0.0001, 0.0001], 'delta_R2': -0.00290051}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'a2fbca39f96b83d6b413cc22e182d07566dc078041420857620592db7edbe78a'}}

### P03|adr_baba|h=21|TRAIN|M1_vs_M0

1. null: incremental explanation of M1 over M0 is zero on this split; the pre-registered S0 criterion is not met
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 94
4. cluster_n: 94
5. literal_rows: 375
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.10403221, 'paired_units': 94}, 'verdict': 'KILL/HOLD-AS-RESEARCH — M1 shows no incremental explanation over M0 on this split'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.001250761185, 'ci95': [-0.0006, 0.0034], 'delta_R2': 0.10403221}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '5ca9bc324eea822c9e311fe1298873cecd2b39666b2552476bdceb179657ef41'}}

### P03|adr_baba|h=21|TUNE|M1_vs_M0

1. null: incremental explanation of M1 over M0 is zero on this split; the pre-registered S0 criterion is not met
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE; NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)
3. honest_n: 31
4. cluster_n: 31
5. literal_rows: 375
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.05614115, 'paired_units': 31}, 'verdict': 'KILL/HOLD-AS-RESEARCH — M1 shows no incremental explanation over M0 on this split'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.000803848792, 'ci95': [-0.0014, 0.0031], 'delta_R2': 0.05614115}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '2ac08b749e64a0d1a4cbaf70ab15b7a8bc0728ac574a7f30550a5968b3304006'}}

### P03|adr_baba|h=21|TRAIN|M2_vs_M1

1. null: incremental explanation of M2 over M1 is zero on this split; the pre-registered S0 criterion is met (descriptive, non-confirmatory)
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 94
4. cluster_n: 94
5. literal_rows: 375
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.53929845, 'paired_units': 94}, 'verdict': 'M2 beats M1 on this split (S0 criterion met; descriptive, non-confirmatory)'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.006483891618, 'ci95': [0.0039, 0.0098], 'delta_R2': 0.53929845}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '5ca9bc324eea822c9e311fe1298873cecd2b39666b2552476bdceb179657ef41'}}

### P03|adr_baba|h=21|TUNE|M2_vs_M1

1. null: incremental explanation of M2 over M1 is zero on this split; the pre-registered S0 criterion is met (descriptive, non-confirmatory)
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE; NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)
3. honest_n: 31
4. cluster_n: 31
5. literal_rows: 375
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.53901104, 'paired_units': 31}, 'verdict': 'M2 beats M1 on this split (S0 criterion met; descriptive, non-confirmatory)'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.007717749731, 'ci95': [0.0027, 0.0132], 'delta_R2': 0.53901104}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '2ac08b749e64a0d1a4cbaf70ab15b7a8bc0728ac574a7f30550a5968b3304006'}}

### P03|adr_baba|h=21|TRAIN|IPCA_vs_M1

1. null: incremental explanation of IPCA over M1 is zero on this split; the pre-registered S0 criterion is not met
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN; IN-SAMPLE for Gamma
3. honest_n: 93
4. cluster_n: 93
5. literal_rows: 375
6. exclusions: {'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 1, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.00864227, 'paired_units': 93}, 'verdict': 'KILL/HOLD-AS-RESEARCH — IPCA shows no incremental explanation over M1 on this split'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.000103762152, 'ci95': [-0.0004, 0.0007], 'delta_R2': 0.00864227}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '5ca9bc324eea822c9e311fe1298873cecd2b39666b2552476bdceb179657ef41'}}

### P03|adr_baba|h=21|TUNE|IPCA_vs_M1

1. null: incremental explanation of IPCA over M1 is zero on this split; the pre-registered S0 criterion is not met
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE; NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)
3. honest_n: 31
4. cluster_n: 31
5. literal_rows: 375
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': -0.01964421, 'paired_units': 31}, 'verdict': 'KILL/HOLD-AS-RESEARCH — IPCA shows no incremental explanation over M1 on this split'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': -0.000281272726, 'ci95': [-0.0011, 0.0005], 'delta_R2': -0.01964421}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '2ac08b749e64a0d1a4cbaf70ab15b7a8bc0728ac574a7f30550a5968b3304006'}}

### P03|adr_baba|h=63|TRAIN|M1_vs_M0

1. null: incremental explanation of M1 over M0 is zero on this split; the pre-registered S0 criterion is not met
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 32
4. cluster_n: 32
5. literal_rows: 126
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.16935998, 'paired_units': 32}, 'verdict': 'KILL/HOLD-AS-RESEARCH — M1 shows no incremental explanation over M0 on this split'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.007540195838, 'ci95': [-0.0017, 0.018], 'delta_R2': 0.16935998}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '18565a2f40ad814ed29b01f65067fd4766077ca7eefb8fa5ea7e96c0fa282b04'}}

### P03|adr_baba|h=63|TUNE|M1_vs_M0

1. null: incremental explanation of M1 over M0 is zero on this split; the pre-registered S0 criterion is not met
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE; NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)
3. honest_n: 10
4. cluster_n: 10
5. literal_rows: 126
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.03191235, 'paired_units': 10}, 'verdict': 'KILL/HOLD-AS-RESEARCH — M1 shows no incremental explanation over M0 on this split'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.000764568972, 'ci95': [-0.0095, 0.0078], 'delta_R2': 0.03191235}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'e22a8bdf6e2d7b255b6d9c372ffcb03c44d7fb602a546dea09f803e59c7fbc6e'}}

### P03|adr_baba|h=63|TRAIN|M2_vs_M1

1. null: incremental explanation of M2 over M1 is zero on this split; the pre-registered S0 criterion is met (descriptive, non-confirmatory)
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN
3. honest_n: 32
4. cluster_n: 32
5. literal_rows: 126
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.5935294, 'paired_units': 32}, 'verdict': 'M2 beats M1 on this split (S0 criterion met; descriptive, non-confirmatory)'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.026424943915, 'ci95': [0.0133, 0.0412], 'delta_R2': 0.5935294}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '18565a2f40ad814ed29b01f65067fd4766077ca7eefb8fa5ea7e96c0fa282b04'}}

### P03|adr_baba|h=63|TUNE|M2_vs_M1

1. null: incremental explanation of M2 over M1 is zero on this split; the pre-registered S0 criterion is not met
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE; NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)
3. honest_n: 10
4. cluster_n: 10
5. literal_rows: 126
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.30317151, 'paired_units': 10}, 'verdict': 'KILL/HOLD-AS-RESEARCH — M2 shows no incremental explanation over M1 on this split'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.007263505317, 'ci95': [-0.0079, 0.026], 'delta_R2': 0.30317151}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'e22a8bdf6e2d7b255b6d9c372ffcb03c44d7fb602a546dea09f803e59c7fbc6e'}}

### P03|adr_baba|h=63|TRAIN|IPCA_vs_M1

1. null: incremental explanation of IPCA over M1 is zero on this split; the pre-registered S0 criterion is not met
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN; IN-SAMPLE for Gamma
3. honest_n: 31
4. cluster_n: 31
5. literal_rows: 126
6. exclusions: {'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 1, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.00358868, 'paired_units': 31}, 'verdict': 'KILL/HOLD-AS-RESEARCH — IPCA shows no incremental explanation over M1 on this split'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.000157264382, 'ci95': [-0.0022, 0.0028], 'delta_R2': 0.00358868}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '18565a2f40ad814ed29b01f65067fd4766077ca7eefb8fa5ea7e96c0fa282b04'}}

### P03|adr_baba|h=63|TUNE|IPCA_vs_M1

1. null: incremental explanation of IPCA over M1 is zero on this split; the pre-registered S0 criterion is not met
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE; NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)
3. honest_n: 10
4. cluster_n: 10
5. literal_rows: 126
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': -0.02005018, 'paired_units': 10}, 'verdict': 'KILL/HOLD-AS-RESEARCH — IPCA shows no incremental explanation over M1 on this split'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': -0.000480370327, 'ci95': [-0.004, 0.0028], 'delta_R2': -0.02005018}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'e22a8bdf6e2d7b255b6d9c372ffcb03c44d7fb602a546dea09f803e59c7fbc6e'}}

### P03|hkd_9988|h=5|TRAIN|M1_vs_M0

1. null: incremental explanation of M1 over M0 is zero on this split; the pre-registered S0 criterion is met (descriptive, non-confirmatory)
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN; DESCRIPTIVE — outside the P03 cohort (V0 row 14 / X7)
3. honest_n: 121
4. cluster_n: 121
5. literal_rows: 711
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.67209468, 'paired_units': 121}, 'verdict': 'M1 beats M0 on this split (S0 criterion met; descriptive, non-confirmatory)'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.004090251881, 'ci95': [0.0025, 0.006], 'delta_R2': 0.67209468}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'cddb0e4962176ac2883c15839d68d564d3adefc7d4fab32285e08290a6f1ebc4'}}

### P03|hkd_9988|h=5|TUNE|M1_vs_M0

1. null: incremental explanation of M1 over M0 is zero on this split; the pre-registered S0 criterion is met (descriptive, non-confirmatory)
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE; DESCRIPTIVE — outside the P03 cohort (V0 row 14 / X7); NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)
3. honest_n: 111
4. cluster_n: 111
5. literal_rows: 711
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.64736264, 'paired_units': 111}, 'verdict': 'M1 beats M0 on this split (S0 criterion met; descriptive, non-confirmatory)'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.002319872489, 'ci95': [0.0016, 0.0031], 'delta_R2': 0.64736264}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '925dbcd38a54c93ac1178d6d50534ed471f025a71e976d9b754128b92ff510d8'}}

### P03|hkd_9988|h=5|TRAIN|M2_vs_M1

1. null: incremental explanation of M2 over M1 is zero on this split; the pre-registered S0 criterion is not met
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN; DESCRIPTIVE — outside the P03 cohort (V0 row 14 / X7)
3. honest_n: 99
4. cluster_n: 99
5. literal_rows: 711
6. exclusions: {'excluded_listed': 22, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 22, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.02143186, 'paired_units': 99}, 'verdict': 'KILL/HOLD-AS-RESEARCH — M2 shows no incremental explanation over M1 on this split'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.000149699868, 'ci95': [-0.0002, 0.0005], 'delta_R2': 0.02143186}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'cddb0e4962176ac2883c15839d68d564d3adefc7d4fab32285e08290a6f1ebc4'}}

### P03|hkd_9988|h=5|TUNE|M2_vs_M1

1. null: incremental explanation of M2 over M1 is zero on this split; the pre-registered S0 criterion is not met
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE; DESCRIPTIVE — outside the P03 cohort (V0 row 14 / X7); NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)
3. honest_n: 111
4. cluster_n: 111
5. literal_rows: 711
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.00279343, 'paired_units': 111}, 'verdict': 'KILL/HOLD-AS-RESEARCH — M2 shows no incremental explanation over M1 on this split'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 1.0010458e-05, 'ci95': [-0.0001, 0.0001], 'delta_R2': 0.00279343}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '925dbcd38a54c93ac1178d6d50534ed471f025a71e976d9b754128b92ff510d8'}}

### P03|hkd_9988|h=21|TRAIN|M1_vs_M0

1. null: incremental explanation of M1 over M0 is zero on this split; the pre-registered S0 criterion is met (descriptive, non-confirmatory)
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN; DESCRIPTIVE — outside the P03 cohort (V0 row 14 / X7)
3. honest_n: 33
4. cluster_n: 33
5. literal_rows: 189
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.54944911, 'paired_units': 33}, 'verdict': 'M1 beats M0 on this split (S0 criterion met; descriptive, non-confirmatory)'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.010846047212, 'ci95': [0.005, 0.0166], 'delta_R2': 0.54944911}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '676ce51fcef5a93bf02bfffbdb44814dd95fd87e52b4a8f4522a4268235fdf03'}}

### P03|hkd_9988|h=21|TUNE|M1_vs_M0

1. null: incremental explanation of M1 over M0 is zero on this split; the pre-registered S0 criterion is met (descriptive, non-confirmatory)
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE; DESCRIPTIVE — outside the P03 cohort (V0 row 14 / X7); NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)
3. honest_n: 28
4. cluster_n: 28
5. literal_rows: 189
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.67827296, 'paired_units': 28}, 'verdict': 'M1 beats M0 on this split (S0 criterion met; descriptive, non-confirmatory)'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.015609778988, 'ci95': [0.0054, 0.0285], 'delta_R2': 0.67827296}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'bced7731f7d0b36d7be8886ac74ebcbfe4b1a19843925b89537ca365422cff42'}}

### P03|hkd_9988|h=21|TRAIN|M2_vs_M1

1. null: incremental explanation of M2 over M1 is zero on this split; the pre-registered S0 criterion is not met
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN; DESCRIPTIVE — outside the P03 cohort (V0 row 14 / X7)
3. honest_n: 26
4. cluster_n: 26
5. literal_rows: 189
6. exclusions: {'excluded_listed': 7, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 7, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.08160776, 'paired_units': 26}, 'verdict': 'KILL/HOLD-AS-RESEARCH — M2 shows no incremental explanation over M1 on this split'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.001818635255, 'ci95': [-0.0006, 0.0042], 'delta_R2': 0.08160776}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '676ce51fcef5a93bf02bfffbdb44814dd95fd87e52b4a8f4522a4268235fdf03'}}

### P03|hkd_9988|h=21|TUNE|M2_vs_M1

1. null: incremental explanation of M2 over M1 is zero on this split; the pre-registered S0 criterion is not met
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE; DESCRIPTIVE — outside the P03 cohort (V0 row 14 / X7); NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)
3. honest_n: 28
4. cluster_n: 28
5. literal_rows: 189
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.02128548, 'paired_units': 28}, 'verdict': 'KILL/HOLD-AS-RESEARCH — M2 shows no incremental explanation over M1 on this split'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.000489864293, 'ci95': [-0.0007, 0.0017], 'delta_R2': 0.02128548}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'bced7731f7d0b36d7be8886ac74ebcbfe4b1a19843925b89537ca365422cff42'}}

### P03|hkd_9988|h=63|TRAIN|M1_vs_M0

1. null: incremental explanation of M1 over M0 is zero on this split; the pre-registered S0 criterion is met (descriptive, non-confirmatory)
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN; DESCRIPTIVE — outside the P03 cohort (V0 row 14 / X7)
3. honest_n: 11
4. cluster_n: 11
5. literal_rows: 63
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.64629226, 'paired_units': 11}, 'verdict': 'M1 beats M0 on this split (S0 criterion met; descriptive, non-confirmatory)'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.019446392496, 'ci95': [0.0047, 0.0377], 'delta_R2': 0.64629226}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '38c0dd45d952fe3f77936675b4969be8ae50db5180725a824be7155f966e4c5d'}}

### P03|hkd_9988|h=63|TUNE|M1_vs_M0

1. null: incremental explanation of M1 over M0 is zero on this split; the pre-registered S0 criterion is not met
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE; DESCRIPTIVE — outside the P03 cohort (V0 row 14 / X7); NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)
3. honest_n: 10
4. cluster_n: 10
5. literal_rows: 63
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.40734683, 'paired_units': 10}, 'verdict': 'KILL/HOLD-AS-RESEARCH — M1 shows no incremental explanation over M0 on this split'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.008031250878, 'ci95': [-0.0017, 0.0192], 'delta_R2': 0.40734683}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '065f491fcc505e4470dea5ad8d55e618d5403e1810650c94aef99f33bab9f899'}}

### P03|hkd_9988|h=63|TRAIN|M2_vs_M1

1. null: incremental explanation of M2 over M1 is zero on this split; the pre-registered S0 criterion is not met
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN; DESCRIPTIVE — outside the P03 cohort (V0 row 14 / X7)
3. honest_n: 8
4. cluster_n: 8
5. literal_rows: 63
6. exclusions: {'excluded_listed': 3, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 3, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': -0.03529472, 'paired_units': 8}, 'verdict': 'KILL/HOLD-AS-RESEARCH — M2 shows no incremental explanation over M1 on this split'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': -0.001077774246, 'ci95': [-0.0074, 0.0039], 'delta_R2': -0.03529472}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '38c0dd45d952fe3f77936675b4969be8ae50db5180725a824be7155f966e4c5d'}}

### P03|hkd_9988|h=63|TUNE|M2_vs_M1

1. null: incremental explanation of M2 over M1 is zero on this split; the pre-registered S0 criterion is not met
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE; DESCRIPTIVE — outside the P03 cohort (V0 row 14 / X7); NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)
3. honest_n: 10
4. cluster_n: 10
5. literal_rows: 63
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.06248689, 'paired_units': 10}, 'verdict': 'KILL/HOLD-AS-RESEARCH — M2 shows no incremental explanation over M1 on this split'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.001231991695, 'ci95': [-0.0027, 0.0054], 'delta_R2': 0.06248689}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '065f491fcc505e4470dea5ad8d55e618d5403e1810650c94aef99f33bab9f899'}}

### P03|hkd_0700|h=5|TRAIN|M1_vs_M0

1. null: incremental explanation of M1 over M0 is zero on this split; the pre-registered S0 criterion is met (descriptive, non-confirmatory)
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN; DESCRIPTIVE — outside the P03 cohort (V0 row 14 / X7)
3. honest_n: 404
4. cluster_n: 404
5. literal_rows: 1554
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.57576813, 'paired_units': 404}, 'verdict': 'M1 beats M0 on this split (S0 criterion met; descriptive, non-confirmatory)'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.001313030965, 'ci95': [0.001, 0.0017], 'delta_R2': 0.57576813}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'b6e53b540553fb303c082919556f41a8ea8a74c35ad948bec15fd699db775266'}}

### P03|hkd_0700|h=5|TUNE|M1_vs_M0

1. null: incremental explanation of M1 over M0 is zero on this split; the pre-registered S0 criterion is met (descriptive, non-confirmatory)
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE; DESCRIPTIVE — outside the P03 cohort (V0 row 14 / X7); NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)
3. honest_n: 109
4. cluster_n: 109
5. literal_rows: 1554
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.63124453, 'paired_units': 109}, 'verdict': 'M1 beats M0 on this split (S0 criterion met; descriptive, non-confirmatory)'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.001288428259, 'ci95': [0.0008, 0.0019], 'delta_R2': 0.63124453}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '2b0e8c1580380f9d17f1be8a6db959359b42e83ab5579f81e6af38177bc91d3c'}}

### P03|hkd_0700|h=5|TRAIN|M2_vs_M1

1. null: incremental explanation of M2 over M1 is zero on this split; the pre-registered S0 criterion is not met
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN; DESCRIPTIVE — outside the P03 cohort (V0 row 14 / X7)
3. honest_n: 101
4. cluster_n: 101
5. literal_rows: 1554
6. exclusions: {'excluded_listed': 303, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 303, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.06291382, 'paired_units': 101}, 'verdict': 'KILL/HOLD-AS-RESEARCH — M2 shows no incremental explanation over M1 on this split'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.000204909167, 'ci95': [0.0, 0.0004], 'delta_R2': 0.06291382}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': 'b6e53b540553fb303c082919556f41a8ea8a74c35ad948bec15fd699db775266'}}

### P03|hkd_0700|h=5|TUNE|M2_vs_M1

1. null: incremental explanation of M2 over M1 is zero on this split; the pre-registered S0 criterion is not met
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE; DESCRIPTIVE — outside the P03 cohort (V0 row 14 / X7); NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)
3. honest_n: 109
4. cluster_n: 109
5. literal_rows: 1554
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.0050775, 'paired_units': 109}, 'verdict': 'KILL/HOLD-AS-RESEARCH — M2 shows no incremental explanation over M1 on this split'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 1.0363648e-05, 'ci95': [-0.0001, 0.0001], 'delta_R2': 0.0050775}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '2b0e8c1580380f9d17f1be8a6db959359b42e83ab5579f81e6af38177bc91d3c'}}

### P03|hkd_0700|h=21|TRAIN|M1_vs_M0

1. null: incremental explanation of M1 over M0 is zero on this split; the pre-registered S0 criterion is met (descriptive, non-confirmatory)
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN; DESCRIPTIVE — outside the P03 cohort (V0 row 14 / X7)
3. honest_n: 109
4. cluster_n: 109
5. literal_rows: 420
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.61073409, 'paired_units': 109}, 'verdict': 'M1 beats M0 on this split (S0 criterion met; descriptive, non-confirmatory)'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.006218180699, 'ci95': [0.0038, 0.0095], 'delta_R2': 0.61073409}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '9504143aabf74a2406ae596e7032c6515e8b0b98991c0be41f7947a7fab50f4e'}}

### P03|hkd_0700|h=21|TUNE|M1_vs_M0

1. null: incremental explanation of M1 over M0 is zero on this split; the pre-registered S0 criterion is met (descriptive, non-confirmatory)
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE; DESCRIPTIVE — outside the P03 cohort (V0 row 14 / X7); NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)
3. honest_n: 28
4. cluster_n: 28
5. literal_rows: 420
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.6226734, 'paired_units': 28}, 'verdict': 'M1 beats M0 on this split (S0 criterion met; descriptive, non-confirmatory)'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.004878139409, 'ci95': [0.001, 0.0092], 'delta_R2': 0.6226734}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '77633dfcfb05bfb3e5be05d0030357481c8439d95ff697365dae290c393c4729'}}

### P03|hkd_0700|h=21|TRAIN|M2_vs_M1

1. null: incremental explanation of M2 over M1 is zero on this split; the pre-registered S0 criterion is not met
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN; DESCRIPTIVE — outside the P03 cohort (V0 row 14 / X7)
3. honest_n: 26
4. cluster_n: 26
5. literal_rows: 420
6. exclusions: {'excluded_listed': 83, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 83, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.03396839, 'paired_units': 26}, 'verdict': 'KILL/HOLD-AS-RESEARCH — M2 shows no incremental explanation over M1 on this split'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.000543977916, 'ci95': [-0.0008, 0.0021], 'delta_R2': 0.03396839}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '9504143aabf74a2406ae596e7032c6515e8b0b98991c0be41f7947a7fab50f4e'}}

### P03|hkd_0700|h=21|TUNE|M2_vs_M1

1. null: incremental explanation of M2 over M1 is zero on this split; the pre-registered S0 criterion is not met
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE; DESCRIPTIVE — outside the P03 cohort (V0 row 14 / X7); NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)
3. honest_n: 28
4. cluster_n: 28
5. literal_rows: 420
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': -0.00576019, 'paired_units': 28}, 'verdict': 'KILL/HOLD-AS-RESEARCH — M2 shows no incremental explanation over M1 on this split'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': -4.5126428e-05, 'ci95': [-0.0004, 0.0004], 'delta_R2': -0.00576019}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '77633dfcfb05bfb3e5be05d0030357481c8439d95ff697365dae290c393c4729'}}

### P03|hkd_0700|h=63|TRAIN|M1_vs_M0

1. null: incremental explanation of M1 over M0 is zero on this split; the pre-registered S0 criterion is met (descriptive, non-confirmatory)
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN; DESCRIPTIVE — outside the P03 cohort (V0 row 14 / X7)
3. honest_n: 37
4. cluster_n: 37
5. literal_rows: 141
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.61631175, 'paired_units': 37}, 'verdict': 'M1 beats M0 on this split (S0 criterion met; descriptive, non-confirmatory)'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.016420041568, 'ci95': [0.0092, 0.0237], 'delta_R2': 0.61631175}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '7968ab0b5ec69d20cc4a1ae13087fd0313ccb39585f94bf4a958b883426cef0a'}}

### P03|hkd_0700|h=63|TUNE|M1_vs_M0

1. null: incremental explanation of M1 over M0 is zero on this split; the pre-registered S0 criterion is met (descriptive, non-confirmatory)
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE; DESCRIPTIVE — outside the P03 cohort (V0 row 14 / X7); NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)
3. honest_n: 10
4. cluster_n: 10
5. literal_rows: 141
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': 0.62180687, 'paired_units': 10}, 'verdict': 'M1 beats M0 on this split (S0 criterion met; descriptive, non-confirmatory)'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': 0.014370428207, 'ci95': [0.0068, 0.0226], 'delta_R2': 0.62180687}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '0fe9b117e8b35d5e49194c9df90dfdd1cc286900b5cf847cbc89cc33fd73a942'}}

### P03|hkd_0700|h=63|TRAIN|M2_vs_M1

1. null: incremental explanation of M2 over M1 is zero on this split; the pre-registered S0 criterion is not met
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TRAIN; DESCRIPTIVE — outside the P03 cohort (V0 row 14 / X7)
3. honest_n: 8
4. cluster_n: 8
5. literal_rows: 141
6. exclusions: {'excluded_listed': 29, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 29, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': -0.13727726, 'paired_units': 8}, 'verdict': 'KILL/HOLD-AS-RESEARCH — M2 shows no incremental explanation over M1 on this split'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': -0.003178016489, 'ci95': [-0.0068, -0.0], 'delta_R2': -0.13727726}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '7968ab0b5ec69d20cc4a1ae13087fd0313ccb39585f94bf4a958b883426cef0a'}}

### P03|hkd_0700|h=63|TUNE|M2_vs_M1

1. null: incremental explanation of M2 over M1 is zero on this split; the pre-registered S0 criterion is not met
2. analysis_set: PRIMARY = SENS-A = SENS-B (no event bundling for rolling anchors, IL §4); split=TUNE; DESCRIPTIVE — outside the P03 cohort (V0 row 14 / X7); NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)
3. honest_n: 10
4. cluster_n: 10
5. literal_rows: 141
6. exclusions: {'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}
7. test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (approximately one-sided alpha 0.025)', 'alpha': 0.025, 'statistic': {'delta_R2': -0.01802509, 'paired_units': 10}, 'verdict': 'KILL/HOLD-AS-RESEARCH — M2 shows no incremental explanation over M1 on this split'}
8. ci: {'method': 'mirror-trick block_bootstrap_ci (grading_stats L121, default draws 800 seed 7) on mean(d)', 'block': 'one non-overlapping anchor unit (h+1 sessions >= h)', 'cluster_variable': 'trade date of the anchor s', 'mean_d': -0.000416573564, 'ci95': [-0.0028, 0.0019], 'delta_R2': -0.01802509}
9. trial_accounting: {'family': 'sni.s1_residual.P03', 'literal_n': 22, 'effective_n': 22, 'declared_budget': 4}
10. receipt: {'code_tree_sha': '44377b14c8d3880d13fe2c25edcf153b0bf8605c', 'base': '5ef7a7f39f99232bf9b574c7603da1011ee3af66', 'prereg_digest_sha256': 'c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab', 'ledger_path': 'research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl', 'prior_looks': 'none for v1', 'seal_row': {'path': 'research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json', 'membership_sha256': '0fe9b117e8b35d5e49194c9df90dfdd1cc286900b5cf847cbc89cc33fd73a942'}}


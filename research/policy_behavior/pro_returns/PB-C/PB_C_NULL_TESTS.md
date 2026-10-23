# PB-C — Complete null-test inventory

This is an exploratory selected-panel analysis. No probability below is a coordination probability, population hazard estimate, corrected confirmatory test, or return forecast. The exact JSON contains tail counts, Monte Carlo SE, status, excluded roots, reference ranges and input hashes. No case was selected for publication because its probability was small.

## Frozen reference model

Each root is independently reassigned with replacement to trading dates in its observed month and weekday. Root IDs receive stable SHA256-derived seeds from master seed 20261007; NumPy 2.3.5 uses PCG64. Scheduled roots remain fixed except in the explicitly separate calendar diagnostic. Dates on weekends/holidays and unverified publication dates are excluded from this sampler. Exact source time does not certify earliest public disclosure.

There are 10,000 simulations per case, using the upper tail with ties and the plus-one convention. Simulated reference ranges are not confidence intervals for an economic effect. Multiple case/horizon/issuer/program variants are correlated exploratory diagnostics; no familywise confirmation is claimed.

## All 23 proximity cases

Primary uses disjoint observed issuer sets. Relaxed requires only different primary tickers. Shared-program filtering uses direct memberships, without transitive closure. Each cell is observed pairs followed by the upper-tail probability.

| Case | Eligible/input roots | Primary 3 sessions: obs (p) | Primary 5 sessions: obs (p) | Relaxed 3 sessions: obs (p) | Direct-program-filtered 3: obs (p) |
|---|---:|---|---|---|---|
| `calendar_first_results_schedule_type` | 35/35 | 119 (0.000300) | 208 (0.000100) | 119 (0.000300) | 119 (0.000300) |
| `calendar_prior_notice_certified` | 31/31 | 95 (0.000600) | 171 (0.000100) | 95 (0.000600) | 95 (0.000600) |
| `strict_freely_timed_positive` | 0/0 | — (—) | — (—) | — (—) | — (—) |
| `broad_unscheduled_candidate` | 46/47 | 22 (0.482852) | 42 (0.413159) | 25 (0.318468) | 16 (0.896610) |
| `broad_positive_content_only` | 15/15 | 3 (0.346865) | 4 (0.579042) | 4 (0.199280) | 2 (0.610539) |
| `broad_ex_NVDA` | 41/42 | 15 (0.873613) | 33 (0.600040) | 17 (0.753925) | 12 (0.973703) |
| `broad_ex_NVDA_AMD_ORCL` | 36/37 | 10 (0.961404) | 23 (0.790221) | 12 (0.885211) | 9 (0.983302) |
| `broad_exact_source_clock` | 5/5 | 0 (—) | 0 (—) | 0 (—) | 0 (—) |
| `broad_HPE_document_date_assumed` | 47/47 | 22 (0.684932) | 42 (0.626537) | 25 (0.515348) | 16 (0.966903) |
| `broad_TSM_Taiwan_source_date` | 46/47 | 22 (0.494051) | 41 (0.504950) | 25 (0.325267) | 16 (0.903810) |
| `broad_ex_species_ACQUISITION` | 44/45 | 20 (0.457054) | 38 (0.439456) | 23 (0.288771) | 14 (0.895410) |
| `broad_ex_species_AI_COMMITMENT` | 40/41 | 16 (0.663034) | 31 (0.587741) | 18 (0.501450) | 13 (0.885711) |
| `broad_ex_species_BUSINESS_EXIT` | 45/46 | 22 (0.482852) | 42 (0.408659) | 25 (0.318468) | 16 (0.896610) |
| `broad_ex_species_BUYBACK` | 44/45 | 19 (0.615538) | 37 (0.518548) | 22 (0.434957) | 13 (0.962704) |
| `broad_ex_species_CAPEX_CAPACITY` | 35/36 | 17 (0.050295) | 30 (0.045395) | 20 (0.017798) | 11 (0.413159) |
| `broad_ex_species_DIVESTITURE` | 43/44 | 20 (0.354265) | 34 (0.549045) | 23 (0.212679) | 14 (0.838716) |
| `broad_ex_species_FINANCING` | 43/44 | 20 (0.332867) | 37 (0.383162) | 22 (0.252175) | 14 (0.820018) |
| `broad_ex_species_GOVERNMENT_CONTRACT` | 45/46 | 20 (0.603440) | 40 (0.473253) | 23 (0.425357) | 14 (0.953505) |
| `broad_ex_species_OFFICIAL_GOVERNMENT_AGREEMENT` | 45/46 | 21 (0.433157) | 41 (0.334967) | 24 (0.269673) | 15 (0.877512) |
| `broad_ex_species_REGULATORY_APPROVAL` | 46/46 | 22 (0.482852) | 42 (0.413159) | 25 (0.318468) | 16 (0.896610) |
| `broad_ex_species_STRATEGIC_PARTNERSHIP` | 31/32 | 7 (0.908409) | 16 (0.698730) | 7 (0.932407) | 7 (0.908409) |
| `broad_ex_species_SUBSIDY_FLOOR_OFFTAKE` | 45/46 | 22 (0.369863) | 42 (0.289971) | 24 (0.274773) | 16 (0.829117) |
| `broad_first_program_family` | 38/39 | 12 (—) | 24 (—) | 12 (—) | 12 (—) |

## All rate-alignment cases

All four columns are separate Treasury sensitivity instruments/horizons, not the missing primary Nasdaq exposure. Each cell is observed captured roots followed by the upper-tail probability. These are counts among selected roots, not issuer-day hazard rates.

| Case | Nominal 2y prior 5: obs (p) | Nominal 2y prior 10: obs (p) | Real 10y prior 5: obs (p) | Real 10y prior 10: obs (p) |
|---|---|---|---|---|
| `calendar_first_results_schedule_type` | 0 (—) | 0 (—) | 0 (—) | 0 (1.000000) |
| `calendar_prior_notice_certified` | 0 (—) | 0 (—) | 0 (—) | 0 (1.000000) |
| `strict_freely_timed_positive` | — (—) | — (—) | — (—) | — (—) |
| `broad_unscheduled_candidate` | 3 (0.757724) | 4 (0.939906) | 2 (0.677032) | 4 (0.404760) |
| `broad_positive_content_only` | 0 (1.000000) | 0 (1.000000) | 0 (1.000000) | 0 (1.000000) |
| `broad_ex_NVDA` | 2 (0.839516) | 3 (0.936606) | 1 (0.871813) | 3 (0.506249) |
| `broad_ex_NVDA_AMD_ORCL` | 1 (0.924808) | 2 (0.947305) | 1 (0.871813) | 3 (0.506249) |
| `broad_exact_source_clock` | 1 (0.626237) | 1 (0.833417) | 0 (—) | 0 (—) |
| `broad_HPE_document_date_assumed` | 3 (0.757724) | 4 (0.939906) | 2 (0.677032) | 4 (0.404760) |
| `broad_TSM_Taiwan_source_date` | 3 (0.757724) | 4 (0.939906) | 2 (0.677032) | 4 (0.404760) |
| `broad_ex_species_ACQUISITION` | 3 (0.757724) | 4 (0.939906) | 2 (0.677032) | 4 (0.404760) |
| `broad_ex_species_AI_COMMITMENT` | 3 (0.709829) | 4 (0.902110) | 2 (0.677032) | 4 (0.404760) |
| `broad_ex_species_BUSINESS_EXIT` | 3 (0.757724) | 4 (0.939906) | 2 (0.677032) | 4 (0.404760) |
| `broad_ex_species_BUYBACK` | 3 (0.580242) | 4 (0.788421) | 2 (0.495050) | 4 (0.081492) |
| `broad_ex_species_CAPEX_CAPACITY` | 2 (0.792521) | 2 (0.983502) | 1 (0.747325) | 1 (0.934107) |
| `broad_ex_species_DIVESTITURE` | 1 (0.967803) | 2 (0.993301) | 1 (0.865313) | 3 (0.505449) |
| `broad_ex_species_FINANCING` | 3 (0.757724) | 4 (0.939906) | 2 (0.677032) | 4 (0.404760) |
| `broad_ex_species_GOVERNMENT_CONTRACT` | 3 (0.757724) | 4 (0.939906) | 2 (0.677032) | 4 (0.404760) |
| `broad_ex_species_OFFICIAL_GOVERNMENT_AGREEMENT` | 3 (0.757724) | 4 (0.939906) | 2 (0.677032) | 4 (0.404760) |
| `broad_ex_species_REGULATORY_APPROVAL` | 3 (0.757724) | 4 (0.939906) | 2 (0.677032) | 4 (0.404760) |
| `broad_ex_species_STRATEGIC_PARTNERSHIP` | 3 (0.588541) | 4 (0.760624) | 2 (0.677032) | 4 (0.404760) |
| `broad_ex_species_SUBSIDY_FLOOR_OFFTAKE` | 3 (0.757724) | 4 (0.939906) | 2 (0.677032) | 4 (0.404760) |
| `broad_first_program_family` | 3 (—) | 4 (—) | 2 (—) | 4 (—) |

## Interpretation of the strongest null and strongest hint

The broad primary sample has 46 roots,22 close pairs and p 0.482852. Removing NVDA, or NVDA+AMD+ORCL, does not reveal an excess. Ordinary first-results calendar releases with prior notices yield95 pairs among 31 roots, compared with reference mean 57.1754 and p 0.000600. That is evidence that the month/weekday reference model underrepresents ordinary earnings clustering; a small probability alone is therefore not specific to strategic support.

The capex-excluded variant must remain visible: primary disjoint-set 3-session p 0.050295; disjoint-set 5-session p 0.045395; relaxed primary-issuer 3-session p 0.017798. At the same 3-session primary definition, filtering directly shared programs changes 17 pairs to 11 and p 0.050295 to0.413159. A filtered 5-session result was not computed. The isolated hint is definition-sensitive, amid many correlated analyses, and is not a validated discovery.

## Uninformative and non-inferential cells

An em dash does not mean a zero probability. The strict freely timed positive sample is empty. The five-root exact-source-clock subset has no simulated proximity variation. Calendar roots mostly lack any possible rate-exposure contrast within their date strata. Such cells retain explicit NOT_ESTIMABLE/constant/no-contrast statuses in JSON and suppress probabilities. A non-null p1 in a variable model is the upper-tail diagnostic, not proof that an effect is exactly absent.

The first-program-family analysis chooses first captured representatives before resampling and before nontrading-date exclusions. It is descriptive only; all probabilities and Monte Carlo SE are suppressed, even though mechanical reference summaries are retained. It does not implement a program-level randomization with reselected minima in every draw.

## Required controls: executed versus unavailable

| Control | State | Evidence/limit |
|---|---|---|
| Frozen universe/species/stress menu | EXECUTED | Original protocol and disclosed amendments precede event tests. |
| Source-family/root dedup | EXECUTED | Apple–MP mirror merged; joint roots retain all captured issuer roles. |
| Known earnings calendar | EXECUTED | 35 scheduled-type first-results roots;31 with prior notices. |
| Conditional date-permutation null | EXECUTED | 10,000 draws per23 cases; complete output above. |
| Leave NVDA/famous issuers/species | EXECUTED | Every declared case disclosed, including capex hint. |
| Same species outside measured stress | DESCRIPTIVE | Per-species exposed/unexposed captured-root counts in PB_C_DESCRIPTIVE_AUDIT.json. |
| Stress windows with no source-frame items | NARROW AUDIT | Four Apple Newsroom dates in fixed week; no global no-support certification. |
| Matched no-support stress windows | UNAVAILABLE | Complete common source frame and matched risk set missing. |
| Size/sector-balanced weak-linkage controls | UNAVAILABLE | Frozen strata have not demonstrated matching/common support. |
| Complete conference/product/policy-calendar null | UNAVAILABLE | Known contexts and direct program memberships retained; no complete fitted calendar model. |
| Pre-period recurrence | NOT_MEASURED | Historical 2001 example is contextual, not a pre-period frequency panel. |
| Primary equity/issuer stress and H1/H5/H21 returns | NOT_MEASURED | Source admission, adjustment/corporate-action and timestamp gates not passed. |

The insufficient-data route is used explicitly. PB-G disposition remains PROSPECTIVE_ONLY.

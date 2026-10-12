# SNI acceptance evidence matrix

Census of acceptance cases A01-A40 against artifacts on origin/main and the S2 lane.
This is an SNI-local draft contract. It consumes owner-supplied identity, event,
market, evaluation, and publication values. It does not mint identifiers and it
does not feed a ranker, gate, sizer, signal, escalation, or trade path.

As of `2026-10-12T04:52:16Z`. Census `7906ef1cd646`. Main `99b8a6e107d8`. S2 `2aa9f7603996`.

Counts: DONE 4, PARTIAL 25, GATED 11, NOT_STARTED 0.

All six authority flags are false: rank, gate, size, signal, escalation, trade.

| id | status | owner task | evidence paths | gap |
|---|---|---|---|---|
| A01 | PARTIAL | C1 | census:research/single_name_intelligence/e2e_20261011/CENSUS_AND_ACCEPTANCE.md; main:research/single_name_intelligence/SNI_E0_ISSUER_EVIDENCE_QUALIFICATION_2026-10-11.md; main:research/single_name_intelligence/SNI_M0_MARKET_DATA_QUALIFICATION_2026-10-11.md | C1/C4 ratio contract untested; no source-proven ADS interval test. |
| A02 | PARTIAL | C1 | census:research/single_name_intelligence/e2e_20261011/CENSUS_AND_ACCEPTANCE.md; main:research/single_name_intelligence/SNI_E0_ISSUER_EVIDENCE_QUALIFICATION_2026-10-11.md; main:tests/test_single_name_coverage_profiles.py; main:research/single_name_intelligence/evidence/Tencent/E2_EVIDENCE_PACK_2026-10-11.md | C1 relationship contract not on main; no permutation-safe dual-counter test. |
| A03 | PARTIAL | C1 | census:research/single_name_intelligence/e2e_20261011/CENSUS_AND_ACCEPTANCE.md; main:research/single_name_intelligence/evidence/Tencent/E2_EVIDENCE_PACK_2026-10-11.md; main:research/single_name_intelligence/SNI_E0_ISSUER_EVIDENCE_QUALIFICATION_2026-10-11.md | Missing test that ID-dependent SNI operations refuse on null issuer. |
| A04 | PARTIAL | C1 | census:research/single_name_intelligence/e2e_20261011/CENSUS_AND_ACCEPTANCE.md; main:research/single_name_intelligence/SNI_U0_COMPANY_INTELLIGENCE_REUSE_MAP.md; main:research/single_name_intelligence/SNI_E0_ISSUER_EVIDENCE_QUALIFICATION_2026-10-11.md | No C1/C4 test that padding, alias, or currency mismatch cannot bind. |
| A05 | GATED | C1 | census:research/single_name_intelligence/e2e_20261011/TASK_GRAPH.json | Identity receipt versioning not started; C1/C2 wait on R1. |
| A06 | GATED | C1 | census:research/single_name_intelligence/e2e_20261011/TASK_GRAPH.json | No relationship-record ID stability test; C1 waits on R1. |
| A07 | PARTIAL | E1 | census:research/single_name_intelligence/e2e_20261011/CENSUS_AND_ACCEPTANCE.md; main:research/single_name_intelligence/evidence/Alibaba/E1_ADVERSARIAL_CASES_2026-10-11.md; main:research/single_name_intelligence/evidence/Tencent/E2_ADVERSARIAL_CASES_2026-10-11.md; s2:research/single_name_intelligence/runs/s2_event_response/REPORT.md | No then-known compiler test excluding post-cutoff filings or retrieval. |
| A08 | PARTIAL | V1 | census:research/single_name_intelligence/e2e_20261011/CENSUS_AND_ACCEPTANCE.md; main:research/single_name_intelligence/SNI_V0_EVALUATION_SUPPORT_MATRIX.md | SNI three-clock view unbuilt; V1/C2 wait on R1. |
| A09 | PARTIAL | E1 | census:research/single_name_intelligence/e2e_20261011/CENSUS_AND_ACCEPTANCE.md; main:research/single_name_intelligence/evidence/Alibaba/E1_ADVERSARIAL_CASES_2026-10-11.md; main:research/single_name_intelligence/evidence/Tencent/E2_ADVERSARIAL_CASES_2026-10-11.md | Probes document silent join; no automated refusal of mismatched joins. |
| A10 | PARTIAL | E1 | census:research/single_name_intelligence/e2e_20261011/CENSUS_AND_ACCEPTANCE.md; main:research/single_name_intelligence/SNI_E0_ISSUER_EVIDENCE_QUALIFICATION_2026-10-11.md; main:research/single_name_intelligence/evidence/Alibaba/E1_EVIDENCE_PACK_2026-10-11.md | C3 compiler not on main; no test that missing KPI stays non-zero. |
| A11 | PARTIAL | E1 | census:research/single_name_intelligence/e2e_20261011/CENSUS_AND_ACCEPTANCE.md; main:research/single_name_intelligence/evidence/Alibaba/E1_ADVERSARIAL_CASES_2026-10-11.md; main:research/single_name_intelligence/evidence/Tencent/E2_ADVERSARIAL_CASES_2026-10-11.md | Packs refuse; no C4 test binding share count to capital versions. |
| A12 | PARTIAL | M0 | census:research/single_name_intelligence/e2e_20261011/CENSUS_AND_ACCEPTANCE.md; main:research/single_name_intelligence/SNI_M0_MARKET_DATA_QUALIFICATION_2026-10-11.md; main:config/single_name_intelligence/coverage_profiles/alibaba.yml | No SNI test of lunch, halt, or DST declared session state. |
| A13 | PARTIAL | C4 | census:research/single_name_intelligence/e2e_20261011/CENSUS_AND_ACCEPTANCE.md; main:research/single_name_intelligence/SNI_M0_MARKET_DATA_QUALIFICATION_2026-10-11.md; main:research/single_name_intelligence/SNI_V0_EVALUATION_SUPPORT_MATRIX.md; main:research/single_name_intelligence/SNI_U0_COMPANY_INTELLIGENCE_REUSE_MAP.md | C4 comparison guard unbuilt; no stale-FX or proxy-stays-proxy test. |
| A14 | PARTIAL | C3 | census:research/single_name_intelligence/e2e_20261011/CENSUS_AND_ACCEPTANCE.md; main:research/single_name_intelligence/SNI_M0_MARKET_DATA_QUALIFICATION_2026-10-11.md; main:research/single_name_intelligence/evidence/Alibaba/E1_EVIDENCE_PACK_2026-10-11.md | No product-copy test forbidding live-flow or intent labels. |
| A15 | GATED | C2 | census:research/single_name_intelligence/e2e_20261011/TASK_GRAPH.json | Reference twin not started; C2 waits on R1. |
| A16 | PARTIAL | V1 | census:research/single_name_intelligence/e2e_20261011/CENSUS_AND_ACCEPTANCE.md; main:research/single_name_intelligence/SNI_V0_EVALUATION_SUPPORT_MATRIX.md; main:research/single_name_intelligence/evidence/Alibaba/E1_ADVERSARIAL_CASES_2026-10-11.md | SNI generation/manifest not implemented; V1 waits on R1. |
| A17 | GATED | P0 | census:research/single_name_intelligence/e2e_20261011/TASK_GRAPH.json | No EFFECT_UNKNOWN write path; P0/V1 wait on R1. |
| A18 | PARTIAL | P0 | census:research/single_name_intelligence/e2e_20261011/CENSUS_AND_ACCEPTANCE.md; main:research/single_name_intelligence/SNI_E0_ISSUER_EVIDENCE_QUALIFICATION_2026-10-11.md; main:research/single_name_intelligence/evidence/Alibaba/E1_EVIDENCE_PACK_2026-10-11.md | P0 entitlement gate unbuilt; no pre-access denial test. |
| A19 | GATED | P0 | census:research/single_name_intelligence/e2e_20261011/TASK_GRAPH.json | No cache, URL, or log isolation test; P0/P1 wait on R1. |
| A20 | PARTIAL | E1 | census:research/single_name_intelligence/e2e_20261011/CENSUS_AND_ACCEPTANCE.md; main:research/single_name_intelligence/evidence/Alibaba/E1_ADVERSARIAL_CASES_2026-10-11.md; main:research/single_name_intelligence/evidence/Tencent/E2_ADVERSARIAL_CASES_2026-10-11.md | No automated test that injected instructions cannot change tool use. |
| A21 | GATED | C3 | census:research/single_name_intelligence/e2e_20261011/TASK_GRAPH.json | No stale-last-good compiler path; C3/P0 wait on R1. |
| A22 | DONE | S2 | s2:tests/test_sni_s2_collapse.py; main:research/single_name_intelligence/protocols/S0_INDEPENDENCE_LAW.md; main:research/single_name_intelligence/protocols/S0_PROTOCOL_REGISTER.md |  |
| A23 | DONE | S1 | main:tests/test_sni_s1_info_leak.py; main:tests/test_sni_s1_seal_integrity.py; main:research/single_name_intelligence/runs/s1_residual/SEAL_AND_BUDGET.json; s2:tests/test_sni_s2_info_leak.py; s2:tests/test_sni_s2_seal_integrity.py |  |
| A24 | DONE | S1 | main:tests/test_sni_s1_language.py; s2:tests/test_sni_s2_language.py; main:research/single_name_intelligence/runs/s1_residual/REPORT.md |  |
| A25 | DONE | S2 | s2:tests/test_sni_s2_abstain.py; s2:research/single_name_intelligence/runs/s2_event_response/REPORT.md |  |
| A26 | PARTIAL | V1 | census:research/single_name_intelligence/e2e_20261011/CENSUS_AND_ACCEPTANCE.md; main:research/single_name_intelligence/SNI_V0_EVALUATION_SUPPORT_MATRIX.md | sni_belief.v1 salt and family gate not landed; V1 waits on R1. |
| A27 | PARTIAL | V1 | census:research/single_name_intelligence/e2e_20261011/CENSUS_AND_ACCEPTANCE.md; main:research/single_name_intelligence/SNI_V0_EVALUATION_SUPPORT_MATRIX.md | No SNI belief publication hash-chain; V1/P2 wait on R1. |
| A28 | PARTIAL | V1 | census:research/single_name_intelligence/e2e_20261011/CENSUS_AND_ACCEPTANCE.md; main:research/single_name_intelligence/SNI_V0_EVALUATION_SUPPORT_MATRIX.md | SNI censoring_state extension unlanded; V1/V2 wait on R1. |
| A29 | PARTIAL | A1 | census:research/single_name_intelligence/e2e_20261011/CENSUS_AND_ACCEPTANCE.md; main:tests/test_sni_s1_stats.py; s2:research/single_name_intelligence/runs/s2_event_response/REPORT.md | A1 independent proper-score reproduction not started; waits on R1. |
| A30 | PARTIAL | A1 | census:research/single_name_intelligence/e2e_20261011/CENSUS_AND_ACCEPTANCE.md; main:research/single_name_intelligence/protocols/S0_PROTOCOL_REGISTER.md; main:research/single_name_intelligence/runs/s1_residual/REPORT.md | No UI/authority copy test; A1/P2 wait on R1. |
| A31 | PARTIAL | P1 | census:research/single_name_intelligence/e2e_20261011/CENSUS_AND_ACCEPTANCE.md; main:research/single_name_intelligence/SNI_U0_REFERENCE_JOURNEY_AND_WIRE_CONTRACT_DRAFT.md | No EN/ZH or viewport persistence test; P1/A0 wait on R1. |
| A32 | PARTIAL | P1 | census:research/single_name_intelligence/e2e_20261011/CENSUS_AND_ACCEPTANCE.md; main:research/single_name_intelligence/SNI_U0_REFERENCE_JOURNEY_AND_WIRE_CONTRACT_DRAFT.md | No keyboard, focus, or source-click test; P1/A0 wait on R1. |
| A33 | PARTIAL | E1 | census:research/single_name_intelligence/e2e_20261011/CENSUS_AND_ACCEPTANCE.md; main:research/single_name_intelligence/evidence/Alibaba/E1_EVIDENCE_PACK_2026-10-11.md; main:research/single_name_intelligence/evidence/Tencent/E2_EVIDENCE_PACK_2026-10-11.md; main:research/single_name_intelligence/evidence/Alibaba/E1_COVERAGE_REPORT_2026-10-11.json | No A0 test that an all-absence or synthetic-fixture page fails release. |
| A34 | GATED | P0 | census:research/single_name_intelligence/e2e_20261011/TASK_GRAPH.json | No SLO, isolation, or fan-out test; P0/A0 wait on R1. |
| A35 | GATED | L0 | census:research/single_name_intelligence/e2e_20261011/TASK_GRAPH.json | Installed real-path release not started; L0 waits on R1. |
| A36 | PARTIAL | U1 | census:research/single_name_intelligence/e2e_20261011/CENSUS_AND_ACCEPTANCE.md; main:research/single_name_intelligence/SNI_U0_COMPANY_INTELLIGENCE_REUSE_MAP.md; main:research/single_name_intelligence/SNI_U0_COMPOSITION_SEAM_DECISION.md | U1-U4 US/Mag-7 packs unbuilt; they wait on L0/R1. |
| A37 | GATED | X0 | census:research/single_name_intelligence/e2e_20261011/TASK_GRAPH.json | Held-out onboarding not started; X0 waits on R1. |
| A38 | GATED | X1 | census:research/single_name_intelligence/e2e_20261011/TASK_GRAPH.json | Coverage-tier economics not started; X1 waits on R1. |
| A39 | PARTIAL | R0 | census:research/single_name_intelligence/e2e_20261011/CENSUS_AND_ACCEPTANCE.md; main:research/single_name_intelligence/e2e_20261011/SNI_PROGRAM_CONTINUATION_2026-10-11.md | Admission, start, and result receipts are incomplete across delegated tasks. |
| A40 | GATED | X2 | census:research/single_name_intelligence/e2e_20261011/TASK_GRAPH.json | SNI-8 closeout not started; X2 waits on R1. |

## Closest to DONE

Three PARTIAL cases nearest a DONE flip, each with the single missing test:

- **A03** (Null HK issuer stays null; ID operations refuse). Add a pytest that ID-dependent SNI operations raise when the HK issuer is null.
- **A07** (Post-cutoff facts cannot enter a then-known view). Add a then-known view test that a filing after as-of cannot enter the view.
- **A11** (Valuation denominators bind canonical capital versions). Add a test that share-count and valuation joins require a canonical capital version.

## Gated on R1

These cases have no implementation artifact yet, and their owning task cannot start before the Chairman's R1 ruling:

A05, A06, A15, A17, A19, A21, A34, A35, A37, A38, A40.

# PB-C strategic announcement research return

**Research disposition: PROSPECTIVE_ONLY.** The completed 2025 retrospective pilot does not validate post-stress announcement orchestration. It returns source-grounded event semantics, actual conditional timing diagnostics, important negative results, an isolated sensitive subgroup hint, and the gates needed for a prospective study.

## Read first

1. `PB_C_RESULTS.md` — substantive conclusions, scope, counts, C1–C5 ratings, stress and economic interpretation.
2. `PB_C_NULL_TESTS.md` — every declared case and null result, including failures and uninformative cases.
3. `PB_C_ACCEPTANCE_CHECKLIST.md` — completed requirements versus unmeasured population-level gates.
4. `PB_G_HANDOFF.md` — carrier/custody and permitted downstream interpretation.
5. `PB_C_PROSPECTIVE_ACCEPTANCE_CONTRACT.md` — build-ready design with explicit unresolved inputs and owner binding.

## Data and evidence

`PB_C_EVENT_PANEL.json` is the authoritative 94-root panel: 91 research roots and 3 separately selected archive items. `PB_C_EVENT_INDEX.md` is a readable source-linked index. `PB_C_ROOT_RESOLUTION.json` records dedup, program membership and original extraction hashes. `PB_C_SOURCE_AND_COVERAGE_MANIFEST.json` records all 36 issuer coverage states and 143 source URLs. `PB_C_NEGATIVE_WINDOW_AUDIT.json` preserves the fixed Apple/Adobe week without invented zero days.

`PB_C_ANALYSIS_RESULTS.json` contains all 23 cases and exact numerical outputs. `PB_C_DESCRIPTIVE_AUDIT.json` contains root exposure membership, observed close pairs, adverse exposure cases and same-species exposed/unexposed counts. `PB_C_CLAIM_EVIDENCE_LEDGER.json` binds conclusions to evidence and gaps.

`PB_C_STRESS_WINDOWS.json` wraps the derived Treasury flags used by the analysis. `rates_sensitivity_stress_calendar.json` preserves the independent derivation's original serialized output; rows are semantically identical. `treasury_stress_manifest.json`, `treasury_stress_spec.json`, `treasury_derivation_checks.json`, and `nyse_calendar_2025.csv` preserve source/calendar identity and arithmetic checks. Raw Treasury XML and unrelated scratch diagnostics are excluded from the delivery.

The original protocol and amendments remain separate. `PB_C_PUBLICATION_CORRECTIONS.md` documents restoration of an extra terminal newline to the canonical protocol, with all numerical results unchanged. `PB_C_PANEL_FREEZE.md` records the accepted inputs before the first actual event test. The earlier execution checkpoint is historical, not the final completion state. Root/program, methods, internal-code and numerical-interpretation reviews are included; they are not PB-F independent program review.

## Offline reproduction of the frozen calculations

Tested with Python 3.12.14 and NumPy 2.3.5 (PCG64). Install the pinned NumPy dependency if needed, then from this directory:

```bash
python3 reproduce_pilot.py --directory . --simulations 10000
python3 reproduce_descriptive_audit.py
```

These commands read only the included frozen panel, derived flags, calendar and code/protocol bytes. They do not download market data or alter production. They overwrite the two corresponding result JSON files in this local directory. With the same input/code bytes and tested runtime, the generated results match the delivery receipts. JSON provenance intentionally changes if an input is edited.

To verify file integrity without recomputing:

```bash
python3 verify_package.py
```

## Optional independent Treasury rederivation

Run into a **new directory** so the accepted historical receipts are preserved:

```bash
python3 derive_treasury_stress.py --out ../pbc_rates_recheck --protocol ./PB_C_ANNOUNCEMENT_STUDY_PREREG.md
python3 package_stress_windows.py --directory ../pbc_rates_recheck
```

This explicitly downloads only the documented Treasury 2024/2025 nominal and real XML feeds if no matching local cache exists. It does not fetch FRED/Nasdaq/Cboe/issuer prices. Compare the JSON row values and original-source hashes to the accepted receipt. New retrieval/computation timestamps and wrapper formatting need not be byte-identical; a changed source vintage must be reviewed, not silently substituted into the accepted study. No assertion of original intraday availability follows from rederiving dates.

## Repository carrier and scope

Draft PR: https://github.com/mastermindx-market-intelligence/macro/pull/8565  
Branch: `research/pb-c-announcement-study-20261007`  
Base: `309f88c6c209bdc9fb611de0018fb619d9351b37`  
Original protocol: `22a6ab802791848b496ac895ec3335d8ffe34d4d`  
Panel/code freeze: `f856691e4578db7029646bba1c5e90949e009de5`

All Git changes are confined to `research/policy_behavior/pro_returns/PB-C/`. The PR body and the downloadable package's publication receipt report the final exact head. No source-owner rewrite, event-store fork, production collector, merge, deployment, message to people, trading rank or after-turn continuation is claimed.

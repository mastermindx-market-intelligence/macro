# A33 reference-evidence check (2026-10-13)

SNI-local DRAFT review of the committed Alibaba E1 and Tencent E2 coverage
reports. This note consumes owner-supplied cell statuses, owner paths, and
A33 class summaries. It does not re-implement Data OS identity, Company
Event/Earnings, FIF, Capital Structure, Stock Identity, Options, Research
Vault, or qledger/Evaluation. Identity ids stay caller-supplied opaque
strings. Every authority flag on the reports and in the checker stays
literal false. Nothing here feeds a ranker, gate, sizer, signal,
escalation, or trade path.

## Summary

The checker loaded `research/single_name_intelligence/evidence/Alibaba/E1_COVERAGE_REPORT_2026-10-11.json` and `research/single_name_intelligence/evidence/Tencent/E2_COVERAGE_REPORT_2026-10-11.json` (schema `sni_evidence_coverage.v0`, as_of 2026-10-11). Both reports are structurally sound and both have real current owner-backed evidence (Alibaba 26 real cells, Tencent 16 real cells). No `behavioral_pilot.*` cell counts. Alibaba meets the six-class reference floor: identity_listing is OWNER_NATIVE and the other five classes are PARTIAL with their best_cell inside real_cells. Tencent does not meet the floor: identity_listing is REFUSED (`issuer_subject`) and corporate_actions_adjustment is ABSENT; the other four classes are PARTIAL and inside real_cells. That is the honest current answer. Both companies having some real evidence is not the same as both companies clearing the per-company floor.

## Rules

Verbatim from `research/single_name_intelligence/acceptance/a33_reference_evidence_check.py`.

Real cell (`real_cells`):

```
Return the cells that count as real current evidence.

A real cell has status in LIVE_STATUSES, evidence_rows > 0, a key that
does not start with PILOT_PREFIX, and a non-empty owner list. Every
owner path, after stripping the suffix, must qualify under
owner_path_error (no tests/, no fixture/synthetic/mock/fake, known
prefix, in-repo code path exists). An unknown prefix is an error and
drops the cell; it is not guessed to exist.
```

Owner path (`owner_path_error`):

```
Every owner path, after stripping the suffix:
- must not sit under `tests/`;
- must not contain `fixture`, `synthetic`, `mock` or `fake` (case-insensitive);
- if it starts with `engine/`, `scripts/`, `config/`, `lib/` or `research/`
  (and `collectors/`, the remaining in-repo owner tree cited by E1/E2),
  must exist under repo_root;
- if it starts with `data/`, is NOT checked for existence (data/ is absent
  from sparse and CI checkouts), but its prefix is still checked;
- any other prefix is an error. Keep this rule; surface the error instead
  of guessing.
```

Structural errors (`structural_errors`):

```
Return structural errors on a loaded coverage report.

Each of the following is an error:
- wrong schema;
- any authority flag not literal False (`is False`, not falsy);
- a missing authority flag;
- `counts` disagreeing with a recount of `metrics` statuses, total included;
- any A33 class missing;
- an A33 `best_cell` that is non-null but absent from `metrics`;
- an A33 `best_status` disagreeing with `metrics[best_cell]["status"]`;
- an `owner_native_cell` that is non-null while its cell's status is not OWNER_NATIVE.
```

Reference floor (`reference_floor`):

```
True iff real_evidence_present holds AND every A33 class clears the floor.

Every A33 class must have best_status in LIVE_STATUSES with its
best_cell inside real_cells. reasons names each failing class with
its best_status and blocking_missing_descriptors, e.g.
`identity_listing: REFUSED (issuer_subject)`.
```

`real_evidence_present` is true iff `structural_errors` is empty and `real_cells` is non-empty. Constants: `LIVE_STATUSES = ("OWNER_NATIVE", "PARTIAL")`, `PILOT_PREFIX = "behavioral_pilot."`, `A33_CLASSES` in order identity_listing, filings_announcements, financials, company_events_earnings_calendar, corporate_actions_adjustment, market_data_daily.

## Per-company table

Filled from `a33_class_table` (the same helper the tests call) at the committed reports.

### Alibaba E1

| class | best_cell | best_status | in real_cells | blocking descriptors |
| --- | --- | --- | --- | --- |
| identity_listing | identity_listing.adr_baba | OWNER_NATIVE | yes | (none) |
| filings_announcements | filings_announcements.hkd_9988 | PARTIAL | yes | issuer_subject, reporting_period, definition_version, correction_refusal_state |
| financials | financials.hkd_9988 | PARTIAL | yes | issuer_subject, known_at_evidence, unit_currency, accounting_basis, source_span, definition_version, correction_refusal_state |
| company_events_earnings_calendar | company_events_earnings_calendar.adr_baba | PARTIAL | yes | definition_version |
| corporate_actions_adjustment | corporate_actions_adjustment.adr_baba | PARTIAL | yes | known_at_evidence, definition_version |
| market_data_daily | market_data_daily.adr_baba | PARTIAL | yes | known_at_evidence, unit_currency, definition_version, correction_refusal_state |

reference_floor(E1) = (True, []).

### Tencent E2

| class | best_cell | best_status | in real_cells | blocking descriptors |
| --- | --- | --- | --- | --- |
| identity_listing | identity_listing.hkd_0700 | REFUSED | no | issuer_subject |
| filings_announcements | filings_announcements.hkd_0700 | PARTIAL | yes | issuer_subject, reporting_period, definition_version, correction_refusal_state |
| financials | financials.hkd_0700 | PARTIAL | yes | issuer_subject, known_at_evidence, unit_currency, accounting_basis, source_span, definition_version, correction_refusal_state |
| company_events_earnings_calendar | company_events_earnings_calendar.hkd_0700 | PARTIAL | yes | issuer_subject, reporting_period, definition_version, correction_refusal_state |
| corporate_actions_adjustment | corporate_actions_adjustment.hkd_0700 | ABSENT | no | issuer_subject, reporting_period, known_at_evidence, unit_currency, dimensions, accounting_basis, source_span, definition_version, correction_refusal_state |
| market_data_daily | market_data_daily.hkd_0700 | PARTIAL | yes | known_at_evidence, unit_currency, definition_version, correction_refusal_state |

reference_floor(E2) = False, reasons exactly:

- `identity_listing: REFUSED (issuer_subject)`
- `corporate_actions_adjustment: ABSENT (issuer_subject, reporting_period, known_at_evidence, unit_currency, dimensions, accounting_basis, source_span, definition_version, correction_refusal_state)`

## Mutant table

Observed values are from `tests/test_sni_a33_reference_evidence.py` (python3.12).

| mutant | expected | observed |
| --- | --- | --- |
| all_absence | real_evidence_present False | False |
| synthetic_owners | real_evidence_present False | False |
| pilot_only | real_evidence_present False | False |
| authority_flipped | structural_errors non-empty; True grant raises | non-empty; ValueError |
| authority_truthy_not_false | structural_errors non-empty (literal-False rule) | non-empty |
| counts_mismatch | structural_errors non-empty | non-empty |
| best_status_self_upgrade (E2) | structural_errors non-empty | non-empty |
| owner_native_cell_forged (E2) | structural_errors non-empty | non-empty |
| missing_owner_path | mutated cell drops out of real_cells | dropped |
| floor summary edit (test 06) | structural_errors non-empty and reference_floor False | non-empty; False |

## What this proves and does not prove

It proves the committed reports are internally consistent and owner-backed, and that the listed degenerate pages are refused: an all-absence page, a page whose live cells point only at synthetic fixture owners, a page whose only live cells are the frozen August behavioral pilot, a page with any authority flag not literal false, a page whose counts disagree with its metrics, and a page that self-upgrades A33 `best_status` or forges `owner_native_cell` without changing the cell.

It does not prove:

- that the data is fresh today (the as_of is 2026-10-11);
- that values are correct;
- that a rendered product page reads these reports — the product page lives in the charting-app repo and is not covered.

This check is not a validation, not a registration, and not a release of a rank, gate, size, signal, escalation, or trade.

## Owner follow-ons

Tencent identity_listing → the Data OS issuer owner named in the report's `would_be_owner`:

> Data OS issuer axis: scripts/build_security_master.py (apply_issuer_correction) under a new issuer-evidence era declared in config/identity_seams.yml, read via lib/dataos/identity.py

Tencent corporate_actions_adjustment → its named owner:

> an explicit HK corporate-action ledger owner (engine/capital_structure is SEC-only; share count carried by no owner)

When either owner closes the named gap, `test_a33_04_tencent_floor_gap_is_exactly_named` and the A33 matrix row must be updated together.

## Gaps

- Tencent identity_listing remains REFUSED because the issuer-subject descriptor is missing in the Data OS identity owner.
- Tencent corporate_actions_adjustment remains ABSENT; no HK corporate-action ledger owner is recorded for that class.
- `data/` owner paths are prefix-checked only; existence is not verified in sparse or CI checkouts.
- Owner trees under `collectors/` are existence-checked the same way as `engine/`, `scripts/`, `config/`, `lib/`, and `research/`, because E1/E2 cite them as first-party owners. Any other prefix is still an error and drops the cell.
- The checker reads the committed JSON as of 2026-10-11 and does not refresh owner stores.
- Authority flags stay literal false everywhere this lane wrote them.

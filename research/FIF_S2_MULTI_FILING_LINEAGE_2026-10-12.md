# FIF S2 — versioned multi-filing (3+ accession) confirmation lineage

Lane `fif-s2-multi-filing-lineage`, 2026-10-12, base `735d63b0` (post E1 #8985).
Acceptance: A03 (nontransitive exact/consistent/inconsistent), A04 (confirmation
is not revision), A05 (version the multi-filing law, preserve the v1 refusal),
A12 (later filing/rule excluded under each clock), A53 (cutoff-valid rule, no
newest-rule hindsight). Code: `engine/fundamental_forensics/lineage_evidence.py`
(v2 additive), `engine/fundamental_forensics/query.py`
(`_admit_lineage_evidence` + `_effective_roots` only). Tests:
`tests/test_fundamental_forensics_multi_filing_lineage.py`.

## v1 vs v2 rule table

| | v1 (`CONFIRMATION_RULE_VERSION = 1`) | v2 chain (`CONFIRMATION_CHAIN_RULE_VERSION = 2`) |
|---|---|---|
| Accession count of one logical key | exactly 2 | 3 or more (2 stays v1-exclusive, never double-minted) |
| Edges minted | 1 (the unique parent/child pair) | n-1, one per ADJACENT pair of the strict accepted_at order; never A~C |
| Rule clock floor | `CONFIRMATION_RULE_AVAILABLE_AT` = 2026-08-25Z | `CONFIRMATION_CHAIN_RULE_AVAILABLE_AT` = 2026-10-12Z (the v2 rule did not exist before this lane) |
| Mint floor | max(rule clock, both groups' recorded_at) | max(chain rule clock, EVERY occurrence's recorded_at in the chain) |
| Minting state filter | `evaluate_confirmation(...) is None` for the pair | whole-chain `classify_filing_chain` == `repeated` (every adjacent edge exact) |
| Admission shape | receipts touch ≤ 2 accessions, else the incumbent `spans more than two filings` raise (preserved verbatim) | L = every ledger accession of the key (via `_event_by_occurrence_id`); len(L) ≥ 3, exactly len(L)-1 receipts, strict representative accepted_at order, edges == adjacent pairs of that order — else the `one strictly ordered path` raise |
| Root unification (`_effective_roots`) | union-find, then drop any component with > 2 members | union-find unchanged; every component kept (an admitted path's still-proving subset is contiguous sub-paths, so no rounded or skip link can join) |
| Envelope (`receipt_envelope_refusal`) | exactly the pre-S2 checks | rule-id, then `< chain rule clock` → `receipt_system_availability_backdated`, then the chain per-edge floor, then the same source_known_at check; versions 3/0/bool → `receipt_rule_mismatch` |

Receipt ids differ across versions by the existing derivation (the payload
includes `evidence_rule_version`); no derivation changed. Mixed versions on one
key raise `lineage evidence mixes confirmation rule versions for one logical key`.

## Chain-state precedence (first match wins; only `repeated` mints)

1. `revised` — any occurrence `event_type is not FILED` or `revision_of` set.
   Example: FY2023 revenue FILED 1050, then a RESTATEMENT 1060 with
   `revision_of` in the third filing.
2. `ambiguous` — a group with >1 distinct accepted_at or a None accepted_at;
   two groups with equal accepted_at (no strict order); or an adjacent edge
   refusal `ambiguous_duplicate_group` / `multiple_possible_parent`. Example:
   10-K and 10-Q accepted at the same instant; or two same-report spans in one
   filing whose rounding intervals are disjoint (guard 7 `_duplicates_agree`).
   Accessions fall back to lexicographic order, `edge_refusals` is empty.
3. `contradictory` — an adjacent edge refusal `changed_value` /
   `nil_state_difference`. Example: A=B=90,678M exact, C=400,000M.
4. `rounded_consistent` — an adjacent edge refusal
   `precision_consistent_unconfirmed`. Example: A=90,678M/-6 vs B=90,700M/-8
   (intervals overlap, tokens differ), B=C exact. No transitivity: B~C never
   rescues the rounded A~B link (A03).
5. `unproven` — any other non-None adjacent edge refusal (taxonomy URI absent
   or unapproved, custom taxonomy, dimensional scope, unit/context, ...).
6. `repeated` — every adjacent edge `evaluate_confirmation(...) is None`.

Only ADJACENT pairs are evaluated — never A-vs-C (A03/A05).

## Clocks and A12/A53 outcomes

| Clock | Gate | Outcome when the clock excludes |
|---|---|---|
| `source_snapshot_at` (source accepted) | `_event_temporally_eligible`; receipt `source_known_at` | filing invisible = absent; with snapshot between B and C, latest_known resolves through B and the B->C receipt is inert (A12) |
| `recorded_at` (system) | `_event_temporally_eligible`; receipt `system_available_at` | a recorded_at before 2026-10-12 hides every v2 receipt — the cell keeps the `unlinked source vintages...` refusal, no hindsight (A53) |
| rule availability | mint floor + version-aware envelope | v2 mint below 2026-10-12 raises `precedes the accepted lineage clock floor`; a hand-built v2 envelope below it is `receipt_system_availability_backdated`; version 3 is `receipt_rule_mismatch` |

A04 unchanged: a chain unifies FILED vintages only — `latest_restated` stays
missing with `no eligible explicitly typed reported revision vintage`, and
`as_reported` still selects the earliest root.

## Deliberately out of this lane

- Production minting wiring: `ixbrl_raw_ledger.py:538` still calls only
  `derive_confirmation_receipts` (v1); no caller feeds
  `derive_chain_confirmation_receipts` yet.
- Typed chain state in any response body: `FilingChainClassification` is a
  diagnostic; `applied_lineage_evidence` and the response-lineage attachment
  region are untouched (owned by a later lane).
- A request-level policy-cutoff field in `query_service.py`: A53 continues to
  ride `recorded_at` (registry projection + envelope clocks).
- `_duplicates_agree` remains duplicated in `query.py` / `raw_ledger.py`
  (census §7): untouched here by order.

## Incumbent test re-scoped (orchestrator amendment)

`tests/test_fundamental_forensics_cross_filing_lineage.py::test_envelope_rule_version_mismatch_is_refused_at_both_gates`
pinned version 2 as "a version the current rule never minted" ->
`receipt_rule_mismatch`. Under the S2 law version 2 IS admitted, and that
golden twin's 2026-08-25 availability is below the chain rule clock, so both
gates now refuse it `receipt_system_availability_backdated` (still fail-closed;
only the named reason changed). The orchestrator re-parametrized the case in the
same PR: version 2 -> `REFUSAL_RECEIPT_SYSTEM_AVAILABILITY_BACKDATED`; versions 3
and `True` (never minted by any admitted rule) -> `REFUSAL_RECEIPT_RULE_MISMATCH`,
each asserted at both gates.

## Follow-ons

1. Wire `derive_chain_confirmation_receipts` into a production provider path
   (the S2 mint is engine-tested only).
2. Surface the typed chain state (with per-edge refusals) as a Calibration-Lab
   tier diagnostic, never user-facing vocabulary.
3. (Done in this PR: the T1b version-mismatch case now covers versions 2, 3 and `True`.)
4. Revisit `_effective_roots` caching if per-key version heterogeneity is ever
   admitted (today admission enforces homogeneity).
5. Extend `applied_lineage_evidence`/response lineage for multi-receipt chains
   (currently generic but untested end-to-end through the HTTP body).

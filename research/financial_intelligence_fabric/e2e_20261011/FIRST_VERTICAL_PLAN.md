# First vertical: repair evidence binding, then serve a real filing

**Scope:** actionable specification for R0/T1/T2/D0–D3/S0/S1/P1/P2/A0. Not an implementation release. The definitive dependency and acceptance references are [TASK_GRAPH.json](TASK_GRAPH.json) and [ACCEPTANCE_MATRIX.json](ACCEPTANCE_MATRIX.json).

## 1. What was executed during assessment

The author materialized an isolated snapshot of Macro `44a45369617dbbd0afdcf161682679640352a554`, including the existing golden filing packages, reference identity data, parser, query services and required contracts. The source checkout and production were untouched. Python 3.12 parsed the genuine committed package data and called the existing pure/domain query service; this was not a synthetic replacement ledger. [S12–S14, S28]

The run produced **1,722 raw ledger events and 130 genuine confirmation receipts**. The query used issuer `ISS:US-XNAS-AAPL`, metric `total_assets`, instant `2025-09-27`, selection `latest_known_as_of`, and source/system cutoffs `2026-09-20T00:00:00Z`. Its fixture result was the decimal string `359241000000`. These are test-corpus values, not a claim about today's company finances.

For each trial, one `positive_evidence` field was changed and a new `LineageEvidenceReceipt` was constructed with a recomputed ID and digest. The same query then consumed the modified receipt in memory. Nine mutations still returned the valid amount and disclosed the altered evidence: parent/child document IDs; parent/child source occurrence keys; dimensions-known; parent/child acceptance clocks; parent/child recorded clocks. Five already-checked controls—concept, value, decimals, taxonomy URI and accession—were refused or became not evaluable.

The original diagnostic JSON hash is `7f8043dda147551e103ad87340ba08c7d2a389addd291728ce65169c4e066bb7`. [PROBE_RESULTS.json](PROBE_RESULTS.json) is an explicitly labeled summary, not a byte-identical copy of the raw run.

### Repair hypothesis was also tested, without a source patch

A process-local wrapper first ran the existing proof function, then reconstructed the complete expected payload through `_positive_evidence_payload` and required exact semantic equality. No repository or snapshot source file was edited. All **14** mutated inputs were rejected or became not evaluable. The four genuine latest/as-reported/latest-restated/pre-lineage responses retained identical response hashes before and after the wrapper. The run completed successfully; no full pytest suite or production API was exercised.

| Policy case | State / fixture value | Response SHA256 preserved by diagnostic wrapper |
|---|---|---|
| Latest known | value / `359241000000` | `74e134907d44731555b9a2db07a2cab42998d63d4f5c6d4bfcd6c2b6efae84a5` |
| As reported | value / `359241000000` | `2dbcc0d66b13ed0c8d7c54a00551ccb335086816859957d2ac3bde8e60870b5d` |
| Latest restated | missing / null | `a291e19152579d2daf2a64c5fab3c8c7b5880bd13a83bdbcbac031bd0d46883d` |
| Pre-lineage cutoff | not_evaluable / null | `aa6f82dc415e2d3449118c627deb339f98814f0a1be6dff61e88f8819495bb21` |

Hypothesis raw-report SHA256: `2ea142fdedb20e3cf39f57ccaa1315a6e746ecf6dc4ecd6c3cb00f7f91761305`. This supports the proposed repair seam; it does not replace formal implementation review, exhaustive field tests or current-head CI. [S29]

## 2. T1 implementation contract

### Before writing

R0 reconciles the current FIF owner, original #7518 follow-up, pending repair work and changed paths. #7518 is merged; do not reopen it or overwrite its branch. Create the next bounded repair carrier through the incumbent owner only if no active conflicting writer exists. This planning branch grants no takeover or deployment permission.

Current inspected query blob: `529d9e7df8e6183848fea0a37280e938c0bd9238`; lineage blob: `2aaac83a73121e55e38f07c1a7b8228691875149`. Refresh those specific inputs if they change. If an equivalent repair already lands, consume its evidence rather than reimplementing it. [S04–S07]

### Owned changes

- Modify `engine/fundamental_forensics/query.py`, narrowly around `_receipt_still_proves_confirmation`.
- Modify `engine/fundamental_forensics/lineage_evidence.py` only if a reviewed public helper is needed for the existing canonical builder.
- Extend `tests/test_fundamental_forensics_cross_filing_lineage.py`.
- Preserve `raw_ledger.py`, the metric registry, original occurrence IDs and frozen golden fixtures unless a separately justified owner change is required. Do not adjust expected hashes to hide regressions.

The query's existing group reconstruction, source/system cutoffs, occurrence IDs and approved original namespace checks remain. Then compute expected positive evidence using the **same** mint-time semantic builder. Require `dict(receipt.positive_evidence or {}) == expected`; refuse otherwise. A small shared public helper is preferable to maintaining eighteen parallel comparisons. Do not derive namespace URIs from a ledger that does not retain the original source URI.

### Formal tests, in order

- [ ] Add a parameterized failing regression that mutates each of the **18 required fields**, recomputes the receipt ID/digest, and asserts query/admission refusal or not_evaluable with no false source-reference disclosure.
- [ ] Confirm the existing nine omitted-field cases fail on the unmodified current source for the intended semantic reason. Rehashed controls must not merely hit a stale-hash validator.
- [ ] Implement one-builder equality without weakening the existing checks or changing the golden provider.
- [ ] Re-run the 18-field matrix and four valid policy cases; prove no-lineage behavior, original packet revisions, temporal/authority flags and immutable occurrence identities remain correct.
- [ ] Run the existing focused financial query, packet and statement/API regression suites selected by the owning repository's CI map. Keep its data/module guards enabled; environment problems are not grounds to waive a semantic test.
- [ ] Obtain independent current-head review, required CI and the authorized release decision. Only then may the existing downstream trust consumer accept the repaired source reference.

A bounded starting command, subject to current repo setup, is:

```bash
python -m pytest -q \
  tests/test_fundamental_forensics_cross_filing_lineage.py \
  tests/test_fundamental_forensics_financial_query_service.py \
  tests/test_fundamental_forensics_financial_query_api.py \
  tests/test_fundamental_forensics_financial_intelligence_packet.py
```

These tests were not run as a suite in the authoring task. The command is an implementation instruction, not a pass receipt.

## 3. Production provider contract—not a widened demo

Direct source inspection shows:

- `_financial_query_provider()` constructs `GoldenAaplFinancialQueryProvider`.
- `_financial_statement_provider()` constructs `GoldenAaplStatementProvider`.
- `_financial_revision_provider()` and `_financial_packet_provider()` construct `UnavailableFinancialPacketProvider`.
- The POST query endpoint uses `Depends(require_site_full_user)`, admits request bytes, then opens the provider and returns a private serialized result. Preserve that order. [S08]

The existing interface is:

```text
execute_financial_query(*, body: bytes,
                       provider: FinancialQueryProvider) -> FinancialQueryResult
FinancialQueryResult = {body: bytes, sha256: str, envelope: dict}
FinancialQueryProvider.resolve(entity_id: str) -> FinancialQueryDataset
```

The dataset already carries canonical binding, occurrence ledger, filing metadata, registry, delivery and optional lineage evidence. Packet and statement providers have their own existing contracts; inspect their exact current signatures before implementation. Do not invent one universal untyped provider or put a second financial representation behind the same endpoint.

### D0–D3 deliverables

D0 freezes the eligible source forms, exact first production accession, comparison periods, required package resources, identity evidence, temporal modes and authority/rights labels. Start with a **newly admitted real AAPL source package**, not the two committed golden accessions relabeled as production. Preserve those goldens as regression controls.

D1 retains and validates the package through the incumbent SEC/source owner. It must distinguish unchanged source, new filing, correction, partial capture and failed observation. D2 reconciles the existing attestation/historical admission path; its old credential or environment references are evidence to inspect, not standing instructions to read secrets, change permissions or dispatch a workflow. Truly human-only controls remain explicit.

D3 implements a production provider on the existing dataset interfaces. Proposed responsibility: resolve the requested canonical issuer to an admitted immutable source-generation manifest, open only verified components, preserve the accepted temporal/semantic policy and return typed unavailability on missing admission. The owning implementer freezes the exact class/file name after current collision checks. It must not fetch SEC data, run extraction or call a model on the HTTP request path.

Required provider tests include unknown issuer, missing/damaged manifest, disallowed source/rights, wrong cutoff, failed attestation, stale optional input, correction supersession and partial publication. A valid provider object with no valid dataset is not production coverage. Golden and production delivery types must never be selected by an undocumented fallback.

## 4. Source-to-product vertical

S0 preserves original statement presentation. S1 supplies only the mappings qualified for the selected package. P1 binds real query, statement, packet and revision readers through `app/forensics.py`; a genuinely absent revision returns the contract's explicit absence, not a fabricated revision or blanket 503 caused by an unwired service.

P2 extends the existing `fundamental_forensics.html` route and its templates. It must show a supported material change, the relevant statement cell, source drilldown and cutoff comparison. `financial_lineage.html` remains a diagnostic/demo surface unless its owner explicitly changes that role; it is not a substitute for the analyst product.

Before A0 acceptance, capture a chain binding actual source accession/digest and clocks → qualified dataset/provider → authorized API response → installed application/browser → evidence-source navigation. Include a source correction and a forbidden/future-cutoff case in a safe test environment, plus the required natural ingestion/publication witness. Browser proof must include EN/ZH desktop and mobile where promised. A screenshot alone does not prove temporal correctness.

A0 is accepted only after independent review and current release gates. It is a product milestone, not the whole FIF program. G1–G4 and the remaining safe tasks start after their prerequisites; the receiving principal does not stop at the first green AAPL journey.

## 5. Reproduction without changing source

The accompanying [probe script](probe_lineage_evidence.py) reconstructs the fourteen-trial diagnostic in a separately materialized, trusted snapshot of the exact census revision. It prints JSON, blocks outgoing network connections during the experiment and writes no product data. Its optional hypothesis mode installs the temporary validator wrapper only in that process and restores it afterward.

```bash
python3.12 probe_lineage_evidence.py --repo /path/to/isolated/pinned-snapshot
python3.12 probe_lineage_evidence.py --repo /path/to/isolated/pinned-snapshot --hypothesis
```

Use a source snapshot with its `ASSESSMENT_PIN.txt` or an exact clean Git checkout and the original package/identity/contract inputs. Never point the experiment at production. The script is packaged for reproducibility; the source experiment and wrapper were executed independently during this assessment. Formal repaired-source acceptance uses T1/T2, not an in-memory wrapper or a single positive probe.

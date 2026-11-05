---
key: FIF-D3-DATASET-MODE-SELECTOR
question: >
  How should the FIF API select between the committed golden corpus and the
  real immutable production datasets — and what may it fall back to when the
  selector is absent or wrong?
answer: >
  Production immutable datasets are served ONLY when
  `FIF_FINANCIAL_DATASET_MODE=production` is set explicitly. Unset/empty (or
  `golden`) is exactly the pre-D3 wiring, byte for byte. Any other value is a
  configuration error: names-only log, typed
  `ProductionDatasetModeError`, private 503 — an invalid mode must never
  degrade into an undocumented selection. The dataset store itself is built
  only from an explicit local dir, `FIF_PRODUCTION_DATASET_LOCAL_STORE`, or
  the dedicated private research-store family; generic `R2_*` variables are
  NEVER a fallback.
rationale: >
  Mode selection is a trust boundary, not a convenience. Credential presence
  is not intent: any host that happens to hold broad research-vault `R2_*`
  variables would silently start serving "production" financial data without
  anyone declaring it, and default-production would flip every existing
  deployment's corpus the moment the providers exist. Deny-by-default with a
  typed refusal keeps the corpus the request actually served auditable from
  configuration alone, and keeps an unset variable meaning exactly the
  pre-D3 golden behavior so D3 could land with zero behavior change.
alternatives:
  - option: auto-detect from credentials present (if R2/production env vars exist, serve production)
    why_not: >
      Credential presence is not declaration — a host carrying generic
      research-vault variables would silently relabel golden answers as
      production service; the mode becomes unauditable from configuration.
  - option: default-production once providers exist (flip the default at cutover)
    why_not: >
      Changes the served corpus of every deployment by omission; a missed
      env var on a host becomes a silent corpus swap instead of a typed
      configuration error, and the golden corpus (the regression control for
      T1/T2 byte-identity) stops being the default anywhere.
evidence:
  - "app/forensics.py:37-58 (branch claude/fif-d3-production-provider-20261012, head de6ee6a2dd3c) — FIF_FINANCIAL_DATASET_MODE_ENV, _LAWFUL_FINANCIAL_DATASET_MODES = (\"golden\", \"production\"), _financial_dataset_mode(): unset/empty→golden, unlawful value→names-only log + ProductionDatasetModeError"
  - "app/forensics.py:23-35 — header comment: 'deny-by-default … NO fallback to the golden corpus' in production mode; invalid mode 'must never degrade into an undocumented selection'"
  - "engine/fundamental_forensics/production_datasets.py:138-158 — build_production_dataset_store(): explicit local dir, then FIF_PRODUCTION_DATASET_LOCAL_STORE, then the dedicated private research-store family; 'Generic ``R2_*`` values are never a fallback'"
  - "engine/fundamental_forensics/production_datasets.py:110-111 — ProductionDatasetModeError typed refusal"
  - "tests/test_fundamental_forensics_production_provider.py + tests/test_fundamental_forensics_production_dataset_store.py — selector and store coverage (9 + 8 test functions)"
affects:
  - WS:FINANCIAL-INTELLIGENCE-FABRIC
  - app/forensics.py
  - engine/fundamental_forensics/production_datasets.py
  - engine/fundamental_forensics/production_provider.py
confidence: high
reversibility: easy
decided_by: coo-fable (FIF e2e seat; branch claude/fif-d3-production-provider-20261012, head de6ee6a2dd3c)
decided_at: 2026-10-12
---

# FIF D3 — dataset mode is an explicit declaration, never detected

D3 added production providers over an immutable, content-addressed dataset
store (objects/manifests/latest keys under a dedicated prefix) plus additive
seams in the query/revision/statement/packet services. The load-bearing
choice is the selector's failure posture: two lawful modes
(`golden` default, `production` explicit), everything else a typed refusal,
and no path on which generic `R2_*` research-vault credentials select a
corpus. A future session adding a third mode must keep the same shape —
extend `_LAWFUL_FINANCIAL_DATASET_MODES` and refuse everything unnamed —
rather than adding a heuristic.

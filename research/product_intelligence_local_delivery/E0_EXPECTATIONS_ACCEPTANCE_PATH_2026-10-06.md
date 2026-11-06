# E0 — Expectations / evidence acceptance path (read-only reconciliation)

**MAIN_PIN:** `892157418ec6b8664d3a0d4ead12011826fc82b4` (`git rev-parse origin/main` after `git fetch origin main`).  
**Mastermind package pin:** `d1a8e672464d9a90dfe5b3608e071f8a730f3c95` (`research/product_intelligence_local_delivery_20261005/`).  
**Lane:** read-only; no collector/engine/provider runs; `yfinance → yahoo` not applied.

---

## C0 — Canonical publication path

**Answer:** Program-level **accepted publication** for Front E expectation/evidence dossier **does not exist on MAIN_PIN yet**. The **physical capture write path** that persists SRC-A1 expectation evidence today is on main (unchanged at PR #8312 head `69d8c407e7033b9aa1e2fb4699398b454d7864c2`):

| Item | Location |
|------|----------|
| Module / function | `collectors/equity_revisions.py:425` `accrue_expectation_observations` |
| Parquet artifacts | `data/revisions/expectation_observations.parquet`, `data/revisions/expectation_attempts.parquet` via `_write_parquet` at `545:548` (`out_dir` default `config.data_dir() / "revisions"` at `439:447`) |
| Orchestration | `collectors/equity_revisions.py:729` `fetch_revisions` calls accrual at `757:759` |

PR #8337 head `13910854fbd652dcdf975301bdc8c6728c2e4767` adds **read-only** inspection (`engine/k3e_expectation_surface.py:117` `inspect_expectation_surface`, CLI `scripts/query_k3e_expectation_surface.py`) — it does **not** write served product artifacts.

**Gates holding canonical publication (quoted):**

1. **#8337 PR body:** “**Canonical publication still depends on source acceptance PR #8312** and current integrated proof for this reviewed consumer.”
2. **Sol CONTINUE on #8312, comment id `5988970684`:** “Until those conditions are met, this is **reserved dependency only / no manifest effect**” (shared CI-manifest / dependent carrier enrollment, including #8463).

No `site/` or `templates/` renderer for a K3E expectation/evidence dossier exists on MAIN_PIN (see Q5).

---

## Q1 — Acceptance ledger

| Component | State | Head sha | Comment id | Who accepted / holding text (excerpt) |
|-----------|-------|----------|------------|----------------------------------------|
| SRC-A1 integrated source review | ACCEPTED | `69d8c407e7033b9aa1e2fb4699398b454d7864c2` | `IC_kwDOS4LjIs8AAAABZCLoFw` | mastermindx-3 — “Current integrated source review accepted — 2026-10-04” |
| SRC-A1 hosted CI proof run 37165245295 | ACCEPTED | `69d8c407…` | `IC_kwDOS4LjIs8AAAABZCftBw` | mastermindx-3 — “PASS for the exact tested integration: source 69d8 + base …” |
| Integrated CI evidence (Astra) | ACCEPTED | `69d8c407…` | `IC_kwDOS4LjIs8AAAABZAOaFw` | MastermindX1 — acceptance of previously pending integrated CI evidence |
| Information-to-price audit + `test_equity_revisions_src_a1_acceptance` | ACCEPTED | `69d8c407…` | (PR #8312 files) | Evidence in PR; native proof scope per PR body |
| SRC-A1 **merge / release** | HELD | `69d8c407…` | `IC_kwDOS4LjIs8AAAABZCh7tw` | mastermindx-3 — “release held, 2026-10-04” |
| Shared CI-manifest enrollment (MKT-1 / A10) | HELD | `69d8c407…` | `5988970684` | MastermindX1 — “reserved dependency only / no manifest effect” until repaired #8463 + lawful #8312 composition |
| EXP-1 consumer merge / publication | HELD | `13910854fbd652dcdf975301bdc8c6728c2e4767` | (#8337 body) | “Draft / held … **Canonical publication still depends on source acceptance PR #8312**” |
| EXP-1 review + hosted code-gate CI37117324489 | ACCEPTED | `13910854…` | (#8337 body) | Independent R2 PASS; 75-case suite; intelligence-registry pack8 |
| Normalized expectation baseline | HELD / PARTIAL | `13910854…` | (#8337 body + code) | “`normalized_baseline.value` always remains null”; `engine/k3e_expectation_surface.py:389` |
| A10 K3E 13F projection (#8463) | HELD | `3d422d752dd4a51b2a288762bdb87f5913fb0598` | `5988961617` | REQUEST_REPAIR — CI contract-delta + `PublishedCatalogGeneration` provenance |
| A10 repaired head qualification | HELD | `014ffa8350d623917701fbb34da1a6233e7c4182` | `IC_kwDOS4LjIs8AAAABZhkLVQ` | MastermindX1 — “independent review + CI enrollment still required” |
| `tests/test_institutional_census_k3e_projection.py` enrollment | HELD | `3d422d75…` | `5988961617` | “**tests/test_institutional_census_k3e_projection.py is a new pytest suite named by no run: step in any workflow**” — CI-manifest owner **#8312**; “Do **not** edit `.github/ci/legacy-jobs.yml` from this carrier” |
| #8309 program continuation | ACCEPTED | MAIN_PIN | `IC_kwDOS4LjIs8AAAABY6z8Jg` | CHECKPOINTED_CONTINUATION — `information-to-price-20261003-sol-001` |
| Yahoo/yfinance as external product source | HELD | MAIN_PIN | `IC_kwDOS4LjIs8AAAABZMiR8Q` | #8309 — expectations remain **internal diagnostic only** |

---

## Q2 — Diff inventory and occupancy

### PR #8312 (`69d8c407…`)

`git diff --stat $(git merge-base origin/main 69d8c407e7033b9aa1e2fb4699398b454d7864c2)..69d8c407e7033b9aa1e2fb4699398b454d7864c2`:

```
 .github/ci/legacy-jobs.yml                         |   11 +
 agentos/discoveries/DSC-SRC-A1-OCTOBER-ACCRUAL-REQUIRES-COHORT-QUALIFICATION.md |   63 +
 agentos/handoffs/ALPHA-INTELLIGENCE-INTEGRATION-2026-10-03-information-to-price.md |  132 +
 agentos/workstreams/WS-ALPHA-INTELLIGENCE-INTEGRATION.md |   20 +
 research/alpha_intelligence/expectation_market_dynamics/* (audit, receipts, tests) | …
 research/alpha_intelligence/expectation_market_dynamics/information_to_price_audit.py |  663 ++
 research/alpha_intelligence/expectation_market_dynamics/test_information_to_price_audit.py |  379 ++
 tests/test_equity_revisions_src_a1_acceptance.py   |  169 +
 13 files changed, 7524 insertions(+), 1 deletion(-)
```

All paths **OCCUPIED** by **#8312** (writer). `collectors/equity_revisions.py` **not** in this diff (already on main).

### PR #8337 (`13910854…`)

```
 .github/ci/legacy-jobs.yml (intelligence-registry EXP-1 steps)
 engine/k3e_expectation_surface.py
 scripts/query_k3e_expectation_surface.py
 tests/test_k3e_expectation_surface.py
 + receipts/handoffs/agentos
 8 files changed, 6034 insertions(+)
```

**OCCUPIED** by **#8337**.

### PR #8463 (`3d422d75…` held head)

```
 engine/institutional_census/k3e_projection.py
 tests/test_institutional_census_k3e_projection.py
 2 files changed, 406 insertions(+)
```

**OCCUPIED** by **#8463** (current head `014ffa83` same paths).

### Blob occupancy — `collectors/equity_revisions.py` and `engine/k3e_expectation_surface.py`

| Path | `origin/main` blob | `69d8c407` | `13910854` | `3d422d75` |
|------|-------------------|------------|------------|------------|
| `collectors/equity_revisions.py` | `8f1d3d822543fd11e18b5a78b957259d43e4c164` | same | same | same |
| `engine/k3e_expectation_surface.py` | **absent** (`git rev-parse origin/main:…` fatal) | absent | `d83e25b50321147b3077d7cff79f93466ad471a5` | absent |

**E1 lawful ownership:** Mastermind `03_WORK_PACKAGES.md:49` — reuse occupied files via existing writer; E1 may add **new** qualification tests only, e.g. `tests/test_k3e_provider_family_qualification.py`, `tests/test_k3e_semantic_seam_qualification.py`, enrolled under existing **`intelligence-registry`** owner at `13910854:.github/ci/legacy-jobs.yml:4641-4680` (pattern for `test_k3e_expectation_surface.py`). **Not** `tests/test_institutional_census_k3e_projection.py` from #8463 until **#8312** manifest owner composes enrollment (`5988961617`).

---

## Q3 — Semantic seams (E1 inputs; not implemented)

| Seam | Verdict | Evidence |
|------|---------|----------|
| (a) `yfinance` / `yahoo` / alias `P` | PRESENT partial | `69d8c407:collectors/equity_revisions.py:86` `_EXPECTATION_PROVIDER = "yfinance"`; `13910854:engine/k3e_expectation_surface.py:117` default `provider="yfinance"`. **ABSENT:** `yahoo` identifier string and alias `P` mapping — `git grep -n 'yahoo\\|\"P\"' 69d8c407 -- collectors/equity_revisions.py` → prose only; `git grep -n yahoo 13910854 -- engine/k3e_expectation_surface.py` → no matches |
| (b) period-end vs fiscal-period | PRESENT | `69d8c407:248-271` `_period_end_anchors`; `13910854:22-23` `period_end`, `fiscal_period`, `fiscal_year` |
| (c) unit, currency, basis | PRESENT | `13910854:23`, `373-375`; capture on main lacks populated unit/currency/basis in SRC-A1 row builder |
| (d) clocks / bitemporal cutoff | PRESENT | `13910854:21-22`, `117-127` `as_of` cutoff filtering |
| (e) contributor identity | PRESENT | `13910854:24` `contributor_id` |
| (f) purpose / rights | PRESENT | `13910854:20` `rights_class`; `365-371` `RIGHTS_BLOCKED` |

---

## Q4 — Adversarial behaviour today

| Case | MAIN_PIN | #8337 head `13910854` | Test |
|------|----------|------------------------|------|
| (a) Horizon roll ≠ revision | UNHANDLED (no k3e reader) | **HANDLED** `362-364` `NATIVE_PERIOD_CHANGED_NO_REVISION_INFERENCE` | `tests/test_k3e_expectation_surface.py::test_native_rollover_and_missing_anchor` |
| (b) Null baseline ≠ zero | UNHANDLED at K3E layer | **HANDLED** `normalized_baseline.value` always `None` `:389` | `::test_zero_null_and_integral_count_law`, `::test_unknown_or_caller_labels_ids_cannot_enable_normalized_value` |
| (c) Stale / withdrawn → refusal | UNKNOWN | **HANDLED** for `RIGHTS_BLOCKED` `:365-371` | RIGHTS_BLOCKED parametrized tests; explicit “withdrawn” label **UNKNOWN** |
| (d) Unit/currency/basis mismatch | UNHANDLED | **HANDLED** refusal via `baseline_reasons` `:373-375` | `::test_unknown_or_caller_labels_ids_cannot_enable_normalized_value` |

---

## Q5 — Consumer surface (MAIN_PIN)

**K3E expectation/evidence dossier renderer:** **ABSENT.**

- `git grep -n 'k3e\\|expectation_market\\|SRC_A1\\|EXP_1' origin/main -- scripts/ app/ engine/ templates/` → no matches.
- `git ls-tree -r origin/main --name-only site/` filtered for `expectation|k3e` → research HTML about estimates only; no K3E dossier artifact.

**Adjacent surfaces (not Front E dossier):**

- `templates/alt_data.html.j2` — analyst estimate revisions (legacy breadth).
- `templates/basket_detail.html.j2` — basket earnings/revisions narrative.
- `engine/expectation_state.py` — separate expectation state machine (not wired to SRC-A1 parquet in this census).

**Market OS B1A `security_state` dossier:**

- Compiler: `engine/security_state.py`
- Dossier projection: `scripts/build_ticker_pages.py:5356` `build_security_state`
- Schema: `contracts/market_os/security_state.v1.schema.json`

**Relation:** E’s expectation/evidence dossier would **extend** the ticker dossier stack as a **new section/contract**, not replace `security_state` identity/refusal semantics — **no collision** if scoped; today **no main integration** exists.

---

## Q6 — Gate text (Mastermind `d1a8e672`)

**E0 / acceptance path** — `03_WORK_PACKAGES.md:45-53`:

> **E0, acceptance path:** inspect #8312's current exact source acceptance and #8337's reviewed consumer/current integration proof. Consume existing accepted evidence rather than rerun physical-source tests. Do not rebuild either source or EXP-1. Reconcile one canonical publication path and keep the broader normalized surface PARTIAL.

**C19 H04 / MAS-271** — `03_WORK_PACKAGES.md:43,53`:

> **Parent:** Macro #8309/#8312/#8337; **C19 H04/MAS-271 consumes its output.** … **Done:** … Return to #8309 and link the accepted output to **MAS-271**.

**H07 / MAS-274 golden vertical** — `03_WORK_PACKAGES.md:103-111`:

> **Parent:** #1202 product mission and **C19 H07/MAS-274** … **Gate:** current accepted H01/H04/H05/H06 dependencies … **Done:** … Return to **MAS-274** and #1202 with exact consumer proof.

**“Accepted evidence” ladder** — `05_ACCEPTANCE_AND_RED_TEAM.md:11`:

> **Source accepted** | Owner-accepted exact source/contract plus applicable integrated proof | A green historical-base suite or another owner's receipt

**Adversarial E-A…E-G (verbatim)** — `05_ACCEPTANCE_AND_RED_TEAM.md:36-48`:

- **E-A.** Provider family names differ. A plausible `yfinance -> yahoo` mapping remains candidate-only until its owner accepts the seam. An alias known after an observation cannot identify that earlier observation.
- **E-B.** A relative horizon label stays unchanged while fiscal period-end rolls. Do not record this as an analyst revision. Unknown fiscal year/period or share/accounting basis is not inferred from naming conventions.
- **E-C.** Later corrections/restatements coexist with an earlier decision cutoff. Both source and transaction/recorded clocks must be applied; current alias/ontology/governance changes cannot leak backward.
- **E-D.** Actual, guidance and consensus differ in units, currency, period length, fiscal definition, GAAP/adjusted or per-share basis. The reader refuses comparison unless the native qualification explicitly supports a transform. A price dataset cannot supply missing estimate semantics by convenience.
- **E-E.** The raw EXP-1 capture is nonempty but its normalized baseline is null. UI and model consumers must not turn capture presence into accepted consensus or use null as zero.
- **E-F.** A scenario derived from a valuation is underidentified or assumption-sensitive. Show a conditional scenario/range and assumptions; do not label it the market's unique expectation. Risk-neutral derivative information remains distinct from a calibrated physical probability.
- **E-G.** A native financial component is stale, withdrawn, rights-ineligible or from a different generation. The composite answer propagates the specific refusal and cannot substitute model prose as a financial value.

---

## Gaps and refusals

1. **No merged served dossier** on MAIN_PIN — only parquet capture writer (`equity_revisions.py:425`) plus unmerged EXP-1 reader on #8337.
2. **`yfinance → yahoo` not applied** (E-A candidate-only); no owner-accepted crosswalk on inspected heads.
3. **Publication gates:** #8337 hold on #8312; Sol **5988970684** manifest reservation.
4. **#8463:** contract-delta refusal text quoted in Q1; `PublishedCatalogGeneration` isinstance gate per **5988961617**.
5. **UNKNOWN:** withdrawn/stale semantics beyond `RIGHTS_BLOCKED` on `13910854` engine; K3E adversarial handling on any future main consumer before merge.

---

*Machine-readable twin: `e0_expectations_acceptance_path_2026-10-06.json`.*

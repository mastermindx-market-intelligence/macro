# Leadership Lab — Implementation Plan

Spec: `research/leadership_alpha_rs/MASTERPLAN.md` (binding). Base: `8a3310cdf03bc16704d51235172a5bbcf1f9a73e`. Native attended operation: `alpha-rs-leadership-recovery-20261005-astra-001`. Executor: Astra, inline. No source-owner paths are replaced.

## Global constraints

Read-only owner consumption; no legacy formula rewrite; no Prophet/ledger/policy mutation; no scheduled producer or production deployment; no invented calibrated probability. Snapshot recovery is not PIT research. Research ordering is not investment authority. Exact identity/clocks/rights qualifications remain owner dependencies. No new residual/peer/expectation/evidence store. All outputs strictly finite JSON. Source artifacts are read from an explicit immutable Git ref, not the dirty shared checkout. Local preview is not production.

## Task 1 — Freeze archaeological evidence

Files: `research/leadership_alpha_rs/{MASTERPLAN,CENSUS,EXECUTION}.md` and `evidence/source_manifest.json`.
Interface: source manifest identifies pinned repository/ref/path, Git blob and SHA-256, source dates/counts, and limitations. Read only bounded existing product snapshots and old source reports. Unlocated retirement commit remains a named gap.
Verification: independently rerun `git show <pin>:<path>` and compare hashes/counts. Expected: 1602 Alpha rows, 1527 factors, 49 baskets, 2026-10-02. Preserve exact receipts even if main later advances.

## Task 2 — Exact measurement primitives, RED then GREEN

Files: `engine/leadership_lab/{__init__,measurement}.py`, `tests/test_leadership_lab.py`.
Interface: `benchmark_window(stock, benchmark, sessions, through, lookback, skip=0)`; `percentile_ranks(values, eligible, min_observed=20, min_coverage=.8)`; `earnings_multiple_bridge(start, end, cutoff)`.
RED: missing implementation assertions; explicit endpoint/compounding, malformed calendar, incomplete window, stale last row, future invariance, average ties, constant/thin/missing population, nonpositive EPS, incompatible fiscal period/currency/share/accounting basis, future/naive clocks and exact price/EPS/multiple reconciliation.
GREEN: implement minimal pure functions; no IO, trained weights, forecast or authority fields from callers. Outputs carry uncalibrated/research state and source limitations.
Verification: `python3 -m pytest -q tests/test_leadership_lab.py`. Expected: all primitives pass and all invalid cases fail closed.

## Task 3 — Read-only recovery projection, RED then GREEN

Files: `engine/leadership_lab/recovery.py`, same test suite.
Interface: `recover_snapshot(alpha, factors, baskets, source_ref, reference_session, limit=40, sort_by='legacy_alpha')` returns new research-view dictionary; caller inputs unchanged. Preserve full recovered population in JSON; preview may show a disclosed bounded subset. Matched-date factors enrich names/legacy blend via `engine.top_picks.compute_scores`; absent factors do not invent corroboration. Current-roster themes display membership and coverage only; no newly ranked theme score.
RED: missing/future/stale sources, date-mismatched enrichment, malformed/NaN fields, input immutability, arbitrary caller buy/probability fields rejected by whitelist, deterministic ties, same population across alternate sorts and missing constituents retained in group denominator.
GREEN: import incumbent Top Picks computation as labeled legacy replication; return all original ticker records with gaps; probability always null and all investment permissions false. Do not expose protected Prophet candidate or plan content.
Verification: primitive/recovery suite plus existing residual-alpha/Top Picks suites. Expected: new suite and directly affected baseline pass.

## Task 4 — Bounded research page and CLI, RED then GREEN

Files: `scripts/build_leadership_lab.py`, `templates/leadership_lab.html.j2`, `templates/leadership_lab.css`, `tests/test_leadership_lab_page.py`.
Interface: CLI accepts explicit `--source-ref` (full commit hash), `--reference-session`, `--format json|html`; emits to stdout only. The script cannot publish or alter canonical files. It reads the three pinned owner artifacts through Git. HTML uses canonical theme tokens, escaped content, bilingual labels and native details disclosures; source/freshness/missingness visible. No buy buttons, probabilities or synthetic current catalysts.
RED: source ref validation, missing snapshots, deterministic JSON, template existence, escaped hostile source text, no unearned advice, table count/source date labels and preserved research-only authority. Stage local preview outside repository with an explicit shell redirect.
GREEN: render the bounded shortlist and group map, source inventory, method/evidence gaps and rerating integration contract. No shared nav/publisher edits in the research-preview slice; canonical shell/private gating is L5, explicitly not claimed complete.
Verification: page tests; preview at 1440/390, dark/light and EN/ZH where browser available. Record exact available vs missing browser proof. Never call a screenshot a deployed proof.

## Task 5 — Verify, publish and hand off exact continuation

Files: execution record, source manifest, compatible CI ownership entry if required, Agent OS handoff under existing Prophet recovery workstream (validate schema first).
Run focused regression, strict JSON serialization, compilation, diff hygiene, canonical Agent OS validation and unrun-test audit. New tests must be wired into existing CI rather than left unrun; use existing owner job where safe. Do not launch the full 42GB sparse-data estate's test suite without an eligible full-data environment; record bounded proof rather than an untrue full-suite claim.
Review complete diff for scope, authority laundering, freshness, source digest mismatch, deterministic equality, null treatment and renamed duplicates. Independent review is unfulfilled unless an actual non-author reviewer returns evidence.
Commit via attended workspace expected-HEAD fence; push same branch; open PR describing tested capability and unresolved gates. Do not auto-deploy. Record head/PR/check status and exact next L2 source/identity qualification task.

## Pre-flight interface ruling

Tasks 1/3/4 share the same pinned source ref and explicit reference session. Task 2's strict measurements are separate APIs; legacy recovery must not relabel old summed returns as their output. Task 3's full population and Task 4's bounded presentation count are separate. No likelihood field from upstream can override null calibration. Task 5 never treats recovery-mode data as a PIT test.

## Review focus

Untrusted source fields cannot escalate authority; future or mixed-date sources cannot appear current; data gaps remain unavailable; legacy ranks retain their original semantics; original inputs and canonical writers are untouched; current curated membership cannot imply historical backtest validity; negative EPS and NTM roll cannot create a false rerating bridge; no named motivating stock gets special treatment.

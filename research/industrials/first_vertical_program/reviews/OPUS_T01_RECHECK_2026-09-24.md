<!-- Provenance: commissioned by the GMI Industrials first-vertical Fable Meta-CEO seat
     (operation gmi-industrials-fable-ceo-e2e-20260924-chairman-001, session c6467452) as an
     independent `ROUTE: review` / `reviewer` (Opus) child under `MODE: READ_ONLY` — it measured the
     branch against freshly fetched origin/main and executed its own probes; it wrote no repository file.
     The lane reviewers' own verdicts on the same heads were unreliable in both directions (a
     FIX_REQUIRED built on a stale base, then a 0-blocker PASS), so this read-only pass is the
     program's real quality gate for every task PR. -->

**Round:** T01 independent Opus red-team, second pass, on lane round 4's head.

**Verdict:** BLOCKED on the CURE, not on the original findings — B1/B2/M1/M2/M4-M8 all cured, but the M3 cure (binding the real `acquire_results_filing` seam) introduced N1 an undeclared `requests` dependency, N2 a `__import__('.'.join([...]))` dodge that hid that dependency from the transitive-closure guard, and N3 a fake `http_get` that never matched the seam's submissions URL, so both branches were dead. Became lane round 5's ruling.

---

# T01 RE-CHECK (opus, READ_ONLY) — PR #7924 head 6166561524fe812a2bda5bc554cc6f8f905a3edc
base fresh origin/main = b9d23ca4bce4308fa7466c4e0f5d318168a50f6f ; merge-base 8a55040f204c
`git diff --name-only origin/main...origin/claude/ind-t01-dependency-binding | wc -l` => 22 (same owned set)
commits since seat merge e381c109: 38c1020d 23317f9e 2674ddc2 22a0b602 a4c6ccf6 61665615 (6, as commissioned)

## BATCH 1
- ITEM 1 (B1) PASS: `git merge-tree --write-tree origin/main origin/claude/...` rc=0, tree 412714387d2b. CI three-dot diff vs fresh main = `1 file changed, 50 insertions(+)`, one hunk @@ -16876,3 +16876,53 @@ appending ONLY `industrials-result-cash`. The prior m-DEVIATION (am-edition/subsector sibling blocks) is GONE — absorbed by the merge.
- ITEM 7 (M5) PASS: b16d707c..head diff of the CI file inside the industrials block = ONE hunk, comment only (@@ -16790,10 +16885,13 @@): now names `test_curated_exclusive_scopes_cover_their_own_import_closure` and the TRANSITIVE closure + recompute rule. `paths:` list and run line byte-unchanged (no further hunks in that block).

## BATCH 2-5 — proofs
- B2 PROBE (sandbox built with `git archive origin/main engine scripts config/...` + `git archive origin/claude/... tests/ engine/company_intelligence`, PYTHONPATH=sandbox, working tree NEVER touched; `git status --porcelain` empty after):
  `Store True Strict True Bounded True`
  `_put_verified (store, *, key, body, maximum) -> None` ; `prepare_private_publication (stage_dir) -> PreparedPrivatePublication` ; `validate_private_manifest (value)` ; `validate_private_pointer (value)` ; `_pointer_for (prepared)` — all four helper call sites signature-compatible.
  `acquire_results_filing (*, cik, http_get=<_http_get>, accession=None)`; RefreshError True.
- SUITE: `python3 -m pytest tests/test_industrials_dependency_binding.py -q` => `19 passed in 0.60s` (python 3.14.7 locally; CI pins 3.12).
- M3 CAUSALITY PROBE (new MAJOR):
  EMPTY fail_sources -> refresh_seam_unbound, detail `SEC submissions JSON invalid`
  outage -> refresh_source_failed source=ordinary_refresh_outage, detail `SEC submissions JSON invalid`
  BOGUS   -> refresh_source_failed source=totally_unrelated_source_name, SAME detail
  `_SUBMISSIONS_URL.format(cik=987654)` = `https://data.sec.gov/submissions/CIK0000987654.json` — the fake's fixture key `synthetic:northgate` and the fail-source names never occur in that URL, so fake_http_get always returns (200, b""); the 503 branch and the `status: ok` branch are unreachable.
- N1 BLOCKER PROOF: meta-path block allowing only stdlib+repo+pytest/pyyaml =>
  `FAILS under pytest+pyyaml-only env: BLOCKED third-party import: requests`
  chain: helpers.py:413 dynamic `scripts.refresh_event_workspaces` -> :77 `from engine.neuralweb import company_intelligence_reader` -> company_intelligence_reader.py:21 `import requests`. CI step installs only `pip install pytest pyyaml`.
- CHECKS at head: all 12 ci-pack* IN_PROGRESS, contract-delta IN_PROGRESS, `ci-authority/codex/merge-queue-pilot` FAILURE, PR DRAFT. No concluded proof exists for the new tests.

## DISPOSITIONS
B1 CURED | B2 CURED | M1 CURED | M2 CURED | M3 PARTIALLY CURED (N3) | M4 CURED | M5 CURED | M6 CURED (nit N5) | M7 CURED | M8 CURED | m1 CURED | m2 CURED | m3 CURED | m4 SURVIVES-BY-RULING | m5 CURED | m6 SURVIVES-BY-RULING | m7 SURVIVES-BY-RULING
NEW: N1 blocker (undeclared requests), N2 major (deliberate closure evasion), N3 major (fail_sources non-causal), N4 minor (registry Iterable consumed twice), N5/N6/N7 nits.
VERDICT: BLOCK — do not merge, do not let T02/T04 branch yet.

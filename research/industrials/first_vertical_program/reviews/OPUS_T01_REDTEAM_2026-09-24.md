<!-- Provenance: commissioned by the GMI Industrials first-vertical Fable Meta-CEO seat
     (operation gmi-industrials-fable-ceo-e2e-20260924-chairman-001, session c6467452) as an
     independent `ROUTE: review` / `reviewer` (Opus) child under `MODE: READ_ONLY` — it measured the
     branch against freshly fetched origin/main and executed its own probes; it wrote no repository file.
     The lane reviewers' own verdicts on the same heads were unreliable in both directions (a
     FIX_REQUIRED built on a stale base, then a 0-blocker PASS), so this read-only pass is the
     program's real quality gate for every task PR. -->

**Round:** T01 independent Opus red-team, first pass, on lane round 3's head.

**Verdict:** BLOCKED — 2 blockers (B1 branch conflicted with fresh main at the EOF of `.github/ci/legacy-jobs.yml` after a sibling appended a job; B2 the in-suite store satisfied none of the 5 extra members of the `@runtime_checkable` `StrictBoundedReadStore` chain, so the owner's `_put_verified` raised) + 8 majors. B1 was cured by the SEAT by hand (main's bytes + our block appended last, merge commit `e381c109b548`); B2 and M1-M8 became lane round 4's ruling.

---

# T01 RED-TEAM (opus, READ_ONLY) — PR #7924 head b16d707cbb22e48e1460e3334acb217be90a9d15
base: fresh origin/main = 57a026f213e90cc33ec8f263afb2b9ed3a570a62; merge-base = b38ba86ecca6

## BATCH 1 — foreign surface
- `git diff --name-only origin/main...origin/claude/ind-t01-dependency-binding | wc -l` => 22; exactly the owned set (17 fixtures + helpers + test + financial_dossier.py + legacy-jobs.yml + test_ci_pack.py). PASS
- `git rev-parse origin/main:engine/company_intelligence/__init__.py` == branch blob `92b1475e48f8ed483e4d093e8b65e002b4a44857`. byte-identical. PASS
- tests/test_ci_pack.py three-dot = +10 lines only (one CURATED_EXCLUSIVE entry + comment). PASS
- BLOCKER B1: `git merge-tree --write-tree origin/main origin/claude/...` rc=1, stage 1/2/3 entries for `.github/ci/legacy-jobs.yml`; net merged tree contains `<<<<<<< origin/main` markers around the new job. The green contract-delta/ci-pack on the PR merge ref is a STALE-BASE green.
- DEVIATION (m): three-dot CI diff touches TWO sibling job blocks besides the appended one (am-edition `pip install ... jinja2` at main:~349; subsector-rotation `paths:`+run line gaining `tests/test_energy_economic_change_non_regression.py`). Content is byte-identical to what fresh main now carries, so the merge effect is nil, but the branch did author edits outside its owned block.

## FINAL REPORT — STATUS: BLOCK
head b16d707cbb22e48e1460e3334acb217be90a9d15 ; base origin/main 57a026f213e9 ; merge-base b38ba86ecca6
`git diff --name-only origin/main...origin/claude/ind-t01-dependency-binding | wc -l` => 22

### BLOCKERS
B1 merge conflict with fresh main — `.github/ci/legacy-jobs.yml`. `git merge-tree --write-tree origin/main origin/claude/ind-t01-dependency-binding` => rc=1 with stage 1/2/3 entries; merged tree carries `<<<<<<< origin/main` at ~:16841/:16867 around `industrials-result-cash`. The PR's green contract-delta/ci-pack are a STALE-BASE green. FIX: `git merge origin/main` on the branch (no rebase/force-push per R3-repair laws), keep both EOF job blocks, re-push, let checks re-run.
B2 harness cannot execute its one real owner call. `tests/industrials_result_cash_helpers.py:165-194` `_MemoryPublicationStore` implements only `get_bytes_strict_bounded` + `put_bytes`. `engine/earnings_narrative/private_publication.py:455-457` `_bounded_read` does `if not isinstance(store, StrictBoundedReadStore): raise EarningsPrivatePublicationError("private earnings store lacks bounded strict reads")`. `StrictBoundedReadStore` (engine/research_vault/r2_store.py:48-84) is a @runtime_checkable Protocol chain Store -> StrictReadStore -> StrictBoundedReadStore. PROBE: isinstance=False, missing ['exists','get_bytes','get_bytes_strict','list_prefix','upload_time']. So `publish()` RAISES. FIX: add the five no-op/dict-backed members.

### MAJORS
M1 `publish()` is dead code; no test calls it; `prepare_private_publication`/`validate_private_manifest` (2 of R2's 4 owner entry points) never imported.
M2 `helpers.py:221` `self.read_count = self.store.read_count` snapshots BEFORE `_put_verified`; R2 "read_count counts that store's reads" unmet.
M3 `helpers.py:212` `needed: "profile=/issuer= discovery binding"` — R2 forbids assuming that seam; real seam `scripts/refresh_event_workspaces.py:236-237 acquire_results_filing(*, cik, http_get=_http_get, ...)`. `fail_sources` is `del`'d.
M4 `financial_dossier.py:59-61` leaks `identity_not_registered` into top-level `reasons`; R5 closes that set to 6 strings.
M5 legacy-jobs.yml stanza comment says "-> 3 modules. No transitive modules." above 14 transitive entries; closure test is TRANSITIVE.
M6 `financial_dossier.py:94` product code hard-codes `hostname == "example.invalid"`.
M7 `live_admission == 'admissible'` unreachable via documented 1-arg signature; untested.
M8 `test_industrials_dependency_binding.py:119` uses 11-digit `"00009876541"`; the namespace rule (`financial_dossier.py:168-169`) is untested.

### MINORS
m1 `_NINE_M_OR_LATER = 90_000_000` (financial_dossier.py:28) misnamed/undocumented.
m2 `unknown_field:<name>` embeds caller text; no exported closed-reason constant.
m3 `helpers.py:63-65` unit "USD_millions" + scale 1 + currency USD triple-encodes magnitude.
m4 `both_basis_unknown` Q1 end == Q2 start == 2026-04-03; northgate fixtures start 2026-04-02. Two conventions.
m5 `test_route_unbound_client_causes_no_read` vacuous.
m6 `FIXTURE_NAMES` globs at import; `case()` KeyError untested.
m7 `_OWNER_NAMESPACES` hard-coded (financial_dossier.py:30, not :53 as MiniMax said).

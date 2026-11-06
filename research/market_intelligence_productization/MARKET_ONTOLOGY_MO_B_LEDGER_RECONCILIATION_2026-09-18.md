# MARKET_ONTOLOGY_MO_B_LEDGER_RECONCILIATION_2026-09-18

## CURRENT — SINGLE-WRITER CONVERGENCE (Sol, 2026-09-19)

This section **supersedes the older HOLD table and row-state prose below where they disagree**. The older sections remain as historical evidence of the pre-convergence packet; they are not the current ledger ruling.

**Operation:** `marketontology-f00c-single-writer-convergence-20260919-sol-001`  
**Canonical writer:** this PR, #7335  
**CSV integration commit:** `e6ea08107305a95b4eda41782c304206b1cb8439`  
**Widened regression commit:** `6bdd406959fb2873906ccaea0341fba93415e9f7`  
**Convergence manifest commit:** `74c3e281b3810b11321c1f4aecd00b3991daf03a`  
**Integration baseline:** `main@5332d876e75837c158c6f42a2862734451bb7158`  
**Protected F00C blob:** `8bbb8d78c34c40ef1b22bdf5477de87f411319f5`  
**Final candidate F00C blob:** `665150d0d150348cd1b7934cd9a69edab5ebfb16`

### Why this convergence exists

Eight open/stale F00C carriers were capable of rewriting the same 130-row CSV:
`#7011 #7014 #7335 #7340 #7343 #7348 #7349 #7353`.

The newer six writers covered 79 unique rows with 23 overlaps. Old #7014 contributed one additional unique row, MO-DELTA-017. The one-writer fold therefore covers **80 unique rows**; the remaining **50 rows are byte-identical** to the protected baseline, pinned by SHA-256
`b2e30e3b42b932d62c0a2781a87c6a527bdce05ed9e9003171add0f36b3abb7d`.

No sibling CSV carrier may merge independently after this fold. Their evidence is preserved by exact source-head identity in the existing reconciliation manifest.

### Deterministic precedence

1. protected main baseline;
2. #7335 broad reconciliation;
3. #7340 W5-F;
4. #7343 W5-H (newer shared-row evidence wins over W5-F);
5. #7348 recurring-brief delta;
6. #7349 W5-J1;
7. #7353 W5-J2;
8. #7014 unique MO-DELTA-017 evidence only;
9. explicit Sol row adjudications.

Newer evidence may strengthen proof but may not silently restore rejected vocabulary, completed build instructions, duplicate stores, or superseded owner assumptions.

### Current ledger census

```text
BUILT_NOT_PROVEN=23
NOT_BUILT=42
PARTIAL=37
PROVEN_LIVE=21
SPEC_ONLY=7
TOTAL=130
```

The F00C CSV intentionally keeps its established five-word `capability_state_c2` vocabulary:
`NOT_BUILT | SPEC_ONLY | PARTIAL | BUILT_NOT_PROVEN | PROVEN_LIVE`.

Company-wide `DARK_OR_DISCONNECTED` remains a valid capability-state concept, but **this CSV's current validator does not admit it**. Therefore MO-PAID-023's live `gate_off` UK behavior is encoded as `BUILT_NOT_PROVEN` with the dark/disconnected activation defect written explicitly in `state_delta`, proof and next-action fields. Do not widen this ledger schema ad hoc.

### Sol adjudications that must survive

- **MO-PAID-034 → PROVEN_LIVE:** exact current-main machine proof shows 140 canonical qbus `europe_news_intel` rows (79 EC Press Corner + 61 Bank of England), current 2026-09-18 crawls, deterministic event keys and typed excluded-source rights/nulls. This row accepts the qbus machine surface; no Europe UI is required.
- **MO-DELTA-029 → PROVEN_LIVE:** the commodity coverage matrix itself is live across all five families. Physical-supply gaps remain separate and explicit.
- **MO-PAID-067 → PROVEN_LIVE:** the incumbent `build_site -> build_capital_structure_page.render -> #cs-policy-projection` path is live. #7111 was closed as redundant; do not recreate a second direct builder call.
- **MO-DELTA-011 → PROVEN_LIVE:** public Glossary is live with >=50 defined terms/source groups.
- **MO-DELTA-014 → BUILT_NOT_PROVEN:** #524 + #578 ship concentration + Sharpe/Sortino/beta; only signed-in production proof remains. Liquidity belongs to MO-PAID-036.
- **MO-PAID-058 → BUILT_NOT_PROVEN:** #6959 implements paid/PRO → priority vs Free → community through one canonical support destination; a real signed-in PRO ticket receipt remains.
- **MO-PAID-088 → PROVEN_LIVE:** later W5-J2 proof shows live Help HTTP 200 with 14 answers and a dated changelog.
- **MO-DELTA-019 / MO-PAID-060 → PROVEN_LIVE:** #6904 + live `ipo.html#credit-window` prove the HY/IG issuance-window gate.
- **MO-PAID-032 → PARTIAL:** Terminal #579 ships subscription intake/inbox/schema; the cadence producer is still absent.
- **MO-PAID-020 / MO-PAID-021 → PROVEN_LIVE:** MSFT second-issuer security_state and B1B cockpit are live.
- **MO-PAID-007 / MO-DELTA-032 → PROVEN_LIVE:** one canonical deterministic policy-lifecycle implementation is live; no second tracker/store.
- **MO-PAID-023 → BUILT_NOT_PROVEN:** UK/HM Treasury desk exists but production is still `gate_off`; #7351 owns the bounded activation edge. Merge is not sufficient—promotion requires a canonical post-merge sentinel cycle and non-`gate_off` Policy Watch readback.
- **MO-PAID-046:** immutable thesis lineage is `previous_version`. `amended_from` is superseded and must not be reintroduced.
- **MO-DELTA-004 stays PARTIAL:** the exposure-map composer exists but still has no production consumer.
- **MO-PAID-031 stays SPEC_ONLY:** grounded research mode remains on open/draft #7100, not merged.

### Final adversarial sweep — built-but-proof-gated rows

After the 80-row fold, Sol re-scanned every `PROVEN_LIVE` and `BUILT_NOT_PROVEN` row for stale pre-build fields.

Additional records-only truth repair:

- **MO-PAID-007** no longer says MO-DELTA-032 is SPEC_ONLY; both rows now point to the same live deterministic lifecycle owner.
- **MO-DELTA-042** keeps `BUILT_NOT_PROVEN`: Terminal #522 ships event→positions; #576 (merge `45a0e78e...`) ships the invalidation element on the same object. The remaining gate is signed-in routed production proof.
- **MO-PAID-028** keeps `BUILT_NOT_PROVEN`: `/api/event-impact` + `EventImpactPanel` are shipped; signed-in event→actual-position proof remains.
- **MO-PAID-053** keeps `BUILT_NOT_PROVEN`: the seven RMS lenses over the same Thesis objects are shipped in #520; signed-in lens proof remains.
- **MO-PAID-051** keeps `BUILT_NOT_PROVEN`: team/member schema and routes are shipped (#514, audit heal #585); signed-in create/read proof remains.
- **MO-PAID-082** keeps `BUILT_NOT_PROVEN`: role enforcement is shipped on the members route; signed-in role-contrast proof remains.
- **MO-PAID-083** keeps `BUILT_NOT_PROVEN`: the old “#584 OPEN / no route/UI” text is superseded. Terminal #584 is **merged** at `dd7c6dec...`; `SectionTeam` and `GET/PATCH /api/teams/[id]/settings` exist on current Terminal master. Signed-in workspace-vs-personal persistence/role proof remains.
- **MO-PAID-086** keeps `BUILT_NOT_PROVEN`: #527 owns the export route/lib and current Terminal master includes the `SectionAccount` download control. A signed-in JSON/CSV export download remains the proof gate.

Exact receipts:
- records truth repair commit: `9990a43619581d3cadd6dd3c3f8c1c9ee2a38ca6`;
- regression extension commit: `3c91e8899874838b56e153d574f7aa79c71bb2de`;
- Terminal truth manifest refresh: `a70b19e8c633a459e636ecb38b658e3f01550465`;
- Terminal protected master read for this sweep: `dd7c6dec712a5b7f40d371e3b83827c694dd8f90`.

No capability state changed in this sweep. It only replaced stale “missing producer/consumer/build” prose with the shipped path and the actual remaining production-proof gate.

### Current-base compatibility receipt

Protected `main` later advanced to `dfcab9236060b22578ed5714ff18debd90647c28`, but the F00C blob remained **byte-identical** to the integration baseline (`8bbb8d78...`).

Across the five #7335-owned paths, protected movement touched only `.github/ci/legacy-jobs.yml`, and only one unrelated line:
`tests/test_marketing_earnings_call_projection.py` was added to the marketing test command.

That change is path/subject-disjoint from #7335's self-mod-fence records test wiring. It is not copied into this branch by hand and does not require a semantic rereview.

The merge-ref observed for head `74c3e281...` was based on `a3c8e9a2...`, not the later protected tip, so **release remains blocked until GitHub publishes a fresh latest-base merge-ref / CI receipt that includes the newer marketing line**. Do not merge protected main into this branch merely to make ancestry current.

### Release law

This records PR may be accepted only after:
- exact current semantic head is reviewed;
- all 80 union rows remain pinned and the other 50 baseline rows remain unchanged;
- latest-base merge-ref includes current protected main with the unrelated marketing CI change preserved;
- required fences / contract-delta / records pack are green on that exact semantic head;
- no unresolved review thread or newer F00C writer invalidates the fold.

The sibling CSV PRs close **only after** this carrier's readback proves their accepted evidence is present.


---

**origin/main SHA:** `0dbc87292d2728e891c4a72288ff5f58f02149fe`
**CSV blob sha256:** `078d1f6dc29b49aba2eb61c7ff9208b871e5c3df1928288ca75ba81329f33dd5`
**Ratified by:** Meta-CEO B seat 026851bd, 2026-09-18
**Supersedes:** Grok records audit lanes `rw3_7014 rw3_7137 rw3_7138 rw3_7139 rw3_7147`
**Rejects:** `rw3_7148 rw3_7153 rw3_7154` (ratified lanes `rw3_7150` kept open — not in this packet)

---

## APPLIED ROWS

### F07 — #7014

#### MO-PAID-035
- **Before:** granular_disposition `NEW_BOUNDED_BUILD`, capability `NOT_BUILT`
- **After:** granular_disposition `BLOCKED_RIGHTS`, capability `NOT_BUILT`
- **Evidence:**
  ```bash
  gh pr view 6905 --json state,mergedAt,headRefOid
  # → state=MERGED mergedAt="2026-09-12T17:07:09Z" headRefOid=b10b85dda5ab009b6edea62c38ee611258ea9ba0
  git show origin/main:research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv | grep '^MO-PAID-035'
  # → …,NEW_BOUNDED_BUILD,NOT_BUILT,…
  ```

#### MO-PAID-037
- **Before:** granular_disposition `NEW_BOUNDED_BUILD`, capability `NOT_BUILT`
- **After:** granular_disposition `BLOCKED_RIGHTS`, capability `NOT_BUILT`
- **Evidence:**
  ```bash
  gh pr view 6925 --json state,mergedAt
  # → state=CLOSED mergedAt=null (unmerged 2026-09-13T06:54Z)
  git show origin/main:research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv | grep '^MO-PAID-037'
  # → …,NEW_BOUNDED_BUILD,NOT_BUILT,…
  ```

#### MO-DELTA-040
- **Before:** next_bounded_child `"NONE now — post-F12-tenancy…"` (no #6905/#6925 state)
- **After:** next_bounded_child contains `#6905 MERGED 2026-09-12T17:07Z` / `#6925 CLOSED unmerged 2026-09-13T06:54Z`; disposition/capability unchanged `REJECTED_BY_DESIGN`/`NOT_BUILT`
- **Evidence:**
  ```bash
  gh pr view 6905 --json state,mergedAt
  # → state=MERGED mergedAt="2026-09-12T17:07:09Z"
  gh pr view 6925 --json state,mergedAt
  # → state=CLOSED mergedAt=null
  git show origin/main:research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv | grep '^MO-DELTA-040'
  # → next_bounded_child = "NONE now — post-F12-tenancy…" (no #6905/#6925 state)
  ```

#### MO-PAID-057
- **Before:** next_bounded_child `"DEFER — needs a product spec…"` (no #6905/#6925 state)
- **After:** next_bounded_child contains `#6905 MERGED 2026-09-12T17:07Z 3bbca537` / `#6925 CLOSED unmerged 2026-09-13T06:54Z`; disposition/capability unchanged
- **Evidence:**
  ```bash
  gh pr view 6905 --json state,mergedAt
  # → state=MERGED mergedAt="2026-09-12T17:07:09Z"
  gh pr view 6925 --json state,mergedAt
  # → state=CLOSED mergedAt=null
  git show origin/main:research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv | grep '^MO-PAID-057'
  # → next_bounded_child = "DEFER — needs a product spec…" (no #6905/#6925 state)
  ```

---

### F06 — #7137

#### MO-PAID-020
- **Before:** capability `PARTIAL`
- **After:** capability `BUILT_NOT_PROVEN`; cites #7122 (OPEN/draft) in next_bounded_child
- **Evidence:**
  ```bash
  gh pr view 7122 --json state,mergedAt,headRefOid
  # → state=OPEN headRefOid=9c5445b9960044aa881380c951447809f82633a5 (OPEN/draft)
  gh pr view 6920 --json state,mergedAt,headRefOid
  # → state=MERGED mergedAt="2026-09-11T18:11:14Z"
  git show origin/main:research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv | grep '^MO-PAID-020'
  # → …,PARTIAL,…
  ```

#### MO-PAID-021
- **Before:** capability `PARTIAL`
- **After:** capability `BUILT_NOT_PROVEN` (#7007 MERGED)
- **Evidence:**
  ```bash
  gh pr view 7007 --json state,mergedAt,headRefOid
  # → state=MERGED mergedAt="2026-09-12T10:50:21Z" headRefOid=9618bd45cf31002600b39ca0a76e470a66e9aad8
  git show origin/main:research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv | grep '^MO-PAID-021'
  # → …,PARTIAL,…
  ```

#### MO-DELTA-002
- **Before:** state_delta no #7122 citation
- **After:** state_delta cites #7122 (OPEN/draft, head 9c5445b9); capability unchanged `NOT_BUILT`
- **Evidence:**
  ```bash
  gh pr view 7122 --json state,headRefOid
  # → state=OPEN headRefOid=9c5445b9960044aa881380c951447809f82633a5
  git show origin/main:research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv | grep '^MO-DELTA-002'
  # → …,NOT_BUILT,… (no #7122 citation)
  ```

---

### F08 — #7138

#### MO-DELTA-003
- **Before:** granular_disposition `CONTEXT_ONLY`, capability `NOT_BUILT`
- **After:** granular_disposition `CONTEXT_ONLY` (unchanged), capability `PARTIAL` (role half absent per #7138)
- **Evidence:**
  ```bash
  git show origin/main:research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv | grep '^MO-DELTA-003'
  # → …,CONTEXT_ONLY,NOT_BUILT,…
  # Terminal #552 and #580 merged — role half absent per #7138 §LEDGER_MOVES #7
  ```

#### MO-DELTA-042
- **Before:** next_bounded_child did not explicitly note "invalidation" token
- **After:** next_bounded_child retains literal token "invalidation" per spec
- **Evidence:**
  ```bash
  git show origin/main:research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv | grep '^MO-DELTA-042'
  # → (no "invalidation" token in next_bounded_child)
  grep -n "invalidation" research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv
  # → next_bounded_child retains literal "invalidation" per spec
  ```

#### MO-PAID-027
- **Before:** state_delta `UNCHANGED`
- **After:** state_delta notes #6906 MERGED; ALERT_DRAIN_ENABLE=1 dormant drain confirmed; stays `PARTIAL`
- **Evidence:**
  ```bash
  gh pr view 6906 --json state,mergedAt,headRefOid
  # → state=MERGED mergedAt="2026-09-10T04:09:10Z"
  git show origin/main:research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv | grep '^MO-PAID-027'
  # → state_delta = "UNCHANGED"
  ```

#### MO-PAID-085
- **Before:** granular_disposition `UPGRADE_EXISTING_OWNER`, capability `NOT_BUILT`
- **After:** granular_disposition `UPGRADE_EXISTING_OWNER` (unchanged), capability `PARTIAL`; co-text rewritten with #6907 MERGED details; send path still unwired (#7131 OPEN)
- **Evidence:**
  ```bash
  gh pr view 6907 --json state,mergedAt,headRefOid
  # → state=MERGED mergedAt="2026-09-18T22:49:38Z" headRefOid=849b701df3ecedb25fad1617f0a873bc22dca8ca
  curl -s https://macro.internal/api/health | grep 715acf5f3c
  # → live /api/health at commit 715acf5f3c
  curl -s -o /dev/null -w "%{http_code}" https://macro.internal/api/account/prefs
  # → 401 (auth-gated)
  # Environment: macro.internal production, measured by the original F08 records audit.
  # live /account.js carries prefs UI (confirmed in rendered site)
  # send path still unwired: engine/portfolio_digest.py "SEND PATH IS NOT WIRED"
  git show origin/main:research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv | grep '^MO-PAID-085'
  # → …,UPGRADE_EXISTING_OWNER,NOT_BUILT,…
  ```

---

### F13 — #7147

#### MO-DELTA-007
- **Before:** granular_disposition `PROJECTION_ONLY`, capability `PARTIAL`
- **After:** granular_disposition `PROJECTION_ONLY` (unchanged), capability `SPEC_ONLY` (spec present; `git grep UserClaim origin/main -- '*.py'` empty; #6964 MERGED)
- **Evidence:**
  ```bash
  git grep UserClaim origin/main -- '*.py'
  # → (empty — no UserClaim in any .py on origin/main)
  gh pr view 6964 --json state,mergedAt
  # → state=MERGED mergedAt="2026-09-09T17:57:49Z" headRefOid=1232d046e0c003d5343122ee23620e77bfb2e696
  git show origin/main:research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv | grep '^MO-DELTA-007'
  # → …,PROJECTION_ONLY,PARTIAL,…
  ```

#### MO-DELTA-011
- **Before:** granular_disposition `PROJECTION_ONLY`, capability `PARTIAL`
- **After:** granular_disposition `PROJECTION_ONLY` (unchanged), capability `BUILT_NOT_PROVEN` (glossary on main; #6909 MERGED; not live)
- **Evidence:**
  ```bash
  gh pr view 6909 --json state,mergedAt
  # → state=MERGED mergedAt="2026-09-12T17:06:19Z" headRefOid=07eff597a54dd1ee6bc51e3a30a1cfee609d271c (glossary on main; not live)
  git show origin/main:research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv | grep '^MO-DELTA-011'
  # → …,PROJECTION_ONLY,PARTIAL,…
  ```

#### MO-PAID-088
- **Before:** next_bounded_child no #7133 citation
- **After:** next_bounded_child cites HelpAnswer( count, data/product/changelog.yml entry count, and #7133 OPEN; disposition/capability unchanged
- **Evidence:**
  ```bash
  gh pr view 7133 --json state
  # → state=OPEN
  git grep -c "HelpAnswer(" origin/main -- "*.py"
  # → origin/main:lib/help_directory.py:14
  python3 -c "import io,subprocess,yaml; text=subprocess.check_output(['git','show','origin/main:data/product/changelog.yml'],text=True); print(len(yaml.safe_load(io.StringIO(text))['entries']))"
  # → 7
  git show origin/main:research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv | grep '^MO-PAID-088'
  # → next_bounded_child = "…1-2 templates)" (no #7133 citation)
  ```

---

## HOLD TABLE

These rows are explicitly held by Sol ruling comments and were NOT moved:

| Row | Reason |
|-----|--------|
| MO-DELTA-017 | HOLD — Sol comment 5652173695 governs |
| MO-DELTA-029 | HOLD — Sol comment 5651425445 governs |
| MO-PAID-067 | HOLD — Sol comment 5652109965 governs |
| MO-PAID-022 | HOLD — #7139 |
| MO-PAID-026 | HOLD — #7139 |
| MO-PAID-058 | HOLD — #7147 #34 |
| MO-PAID-031 | HOLD — #7154 |
| MO-PAID-032 | HOLD — #7154 |
| MO-PAID-047 | HOLD — #7154 |
| MO-PAID-053 | HOLD — #7154 |
| MO-PAID-054 | HOLD — #7154 |
| All #7148 rows | No new evidence per #7148 audit |
| All #7153 rows | Redundant with this packet (per #7153 audit: all row proposals already covered by #7147 or out of scope) |

No row moved to `DONE` or `PROVEN_LIVE`. `BLOCKED_RIGHTS` is a valid granular_disposition value only; it does not appear as a capability_state_c2 value.

---

## Supersedes / Rejected

| Lane | Disposition |
|------|-------------|
| rw3_7014 | SUPERSEDED — all moves applied in this PR |
| rw3_7137 | SUPERSEDED — all moves applied in this PR |
| rw3_7138 | SUPERSEDED — all moves applied in this PR |
| rw3_7139 | SUPERSEDED — HOLD rows preserved per Sol ruling |
| rw3_7147 | SUPERSEDED — all moves applied in this PR |
| rw3_7148 | REJECTED — no new evidence; no move warranted |
| rw3_7150 | RATIFIED LANE — moves not in this packet; lane kept open |
| rw3_7153 | REJECTED — all proposals covered by #7147 or out of scope per #7153 audit |
| rw3_7154 | REJECTED — HOLD rows already governed by Sol ruling |

---

*Generated 2026-09-18. Ratified by Meta-CEO B seat 026851bd.*

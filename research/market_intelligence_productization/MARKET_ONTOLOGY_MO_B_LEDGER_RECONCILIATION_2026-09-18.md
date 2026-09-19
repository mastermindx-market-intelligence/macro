# MARKET_ONTOLOGY_MO_B_LEDGER_RECONCILIATION_2026-09-18

**origin/main SHA:** `0dbc87292d2728e891c4a72288ff5f58f02149fe`
**CSV blob sha256:** `078d1f6dc29b49aba2eb61c7ff9208b871e5c3df1928288ca75ba81329f33dd5`
**Ratified by:** Meta-CEO B seat 026851bd, 2026-09-18
**Supersedes:** Grok records audit lanes `rw3_7014 rw3_7137 rw3_7138 rw3_7139 rw3_7147`
**Rejects:** `rw3_7148 rw3_7150 rw3_7153 rw3_7154` (no new evidence; redundant with this packet or already resolved)

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
  ```

#### MO-PAID-037
- **Before:** granular_disposition `NEW_BOUNDED_BUILD`, capability `NOT_BUILT`
- **After:** granular_disposition `BLOCKED_RIGHTS`, capability `NOT_BUILT`
- **Evidence:**
  ```bash
  gh pr view 6925 --json state,mergedAt,headRefOid
  # → state=CLOSED mergedAt=null (unmerged 2026-09-13T06:54Z)
  git show origin/main:research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv | grep '^MO-PAID-037'
  ```

#### MO-DELTA-040
- **Before:** next_bounded_child contained `#6905 is OPEN` / `#6925 is OPEN`
- **After:** next_bounded_child contains `#6905 MERGED 2026-09-12T17:07Z 3bbca537` / `#6925 CLOSED unmerged 2026-09-13T06:54Z`
- **Evidence:**
  ```bash
  gh pr view 6905 --json state,mergedAt,headRefOid
  # → state=MERGED mergedAt="2026-09-12T17:07:09Z"
  gh pr view 6925 --json state,mergedAt
  # → state=CLOSED mergedAt=null
  ```

#### MO-PAID-057
- **Before:** next_bounded_child contained `#6905 is OPEN` / `#6925 is OPEN`
- **After:** next_bounded_child contains `#6905 MERGED 2026-09-12T17:07Z 3bbca537` / `#6925 CLOSED unmerged 2026-09-13T06:54Z`
- **Evidence:** same as MO-DELTA-040

---

### F06 — #7137

#### MO-PAID-020
- **Before:** capability `PARTIAL`
- **After:** capability `BUILT_NOT_PROVEN`
- **Evidence:**
  ```bash
  gh pr view 7122 --json state,mergedAt,headRefOid
  # → state=OPEN headRefOid=9c5445b9960044aa881380c951447809f82633a5 (still OPEN/draft)
  gh pr view 6920 --json state,mergedAt,headRefOid
  # → state=MERGED mergedAt="2026-09-11T18:11:14Z" headRefOid=8ad664226a8293e91eef9757905760f725fcb213
  ```

#### MO-PAID-021
- **Before:** capability `PARTIAL`
- **After:** capability `BUILT_NOT_PROVEN`
- **Evidence:**
  ```bash
  gh pr view 7007 --json state,mergedAt,headRefOid
  # → state=MERGED mergedAt="2026-09-12T10:50:21Z" headRefOid=9618bd45cf31002600b39ca0a76e470a66e9aad8
  ```

#### MO-DELTA-002
- **Before:** capability `NOT_BUILT` (no citation of #7122)
- **After:** capability `NOT_BUILT`; state_delta cites #7122 OPEN/draft
- **Evidence:**
  ```bash
  gh pr view 7122 --json state,headRefOid
  # → state=OPEN headRefOid=9c5445b9960044aa881380c951447809f82633a5
  ```

---

### F08 — #7138

#### MO-DELTA-003
- **Before:** granular_disposition `CONTEXT_ONLY`, capability `NOT_BUILT`
- **After:** granular_disposition `PARTIAL`, capability `NOT_BUILT`
- **Evidence:**
  ```bash
  # Terminal #552 and #580 merged — disposition PARTIAL, capability NOT_BUILT (role half absent)
  # No git command available for terminal; evidence per #7138 §LEDGER_MOVES #7
  ```

#### MO-DELTA-042
- **Before:** next_bounded_child did not explicitly note "invalidation" token
- **After:** next_bounded_child retains literal token "invalidation" per spec
- **Evidence:**
  ```bash
  grep -n "invalidation" research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv
  ```

#### MO-PAID-027
- **Before:** state_delta `UNCHANGED`
- **After:** state_delta notes #6906 MERGED; ALERT_DRAIN_ENABLE=1 dormant drain confirmed; stays PARTIAL
- **Evidence:**
  ```bash
  gh pr view 6906 --json state,mergedAt,headRefOid
  # → state=MERGED mergedAt="2026-09-10T04:09:10Z" headRefOid=0a62fa454d777368041a5d22924cb5026e611956
  ```

#### MO-PAID-085
- **Before:** granular_disposition `UPGRADE_EXISTING_OWNER`, capability `NOT_BUILT`
- **After:** granular_disposition `PARTIAL`; co-text rewritten with #6907 MERGED details
- **Evidence:**
  ```bash
  gh pr view 6907 --json state,mergedAt,headRefOid
  # → state=MERGED mergedAt="2026-09-18T22:49:38Z" headRefOid=849b701df3ecedb25fad1617f0a873bc22dca8ca
  curl -s https://macro.internal/api/health | grep 715acf5f3c
  # → live /api/health at commit 715acf5f3c
  curl -s -o /dev/null -w "%{http_code}" https://macro.internal/api/account/prefs
  # → 401 (auth-gated)
  ```

---

### F13 — #7147

#### MO-DELTA-007
- **Before:** granular_disposition `PROJECTION_ONLY`
- **After:** granular_disposition `SPEC_ONLY`
- **Evidence:**
  ```bash
  git grep UserClaim origin/main -- '*.py'
  # → (empty — no UserClaim in any .py on origin/main)
  gh pr view 6964 --json state,mergedAt
  # → state=MERGED
  ```

#### MO-DELTA-011
- **Before:** granular_disposition `PROJECTION_ONLY`
- **After:** granular_disposition `BUILT_NOT_PROVEN`
- **Evidence:**
  ```bash
  gh pr view 6909 --json state,mergedAt
  # → state=MERGED (glossary on main; not live)
  ```

#### MO-PAID-088
- **Before:** next_bounded_child did not cite #7133
- **After:** next_bounded_child cites HelpAnswer( count + changelog.yml entry count + #7133 OPEN
- **Evidence:**
  ```bash
  gh pr view 7133 --json state
  # → state=OPEN
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
| All #7153 rows | Redundant with this packet |

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
| rw3_7150 | (not cited in ratification) |
| rw3_7153 | REJECTED — redundant with #7147 moves |
| rw3_7154 | REJECTED — HOLD rows already governed by Sol ruling |

---

*Generated 2026-09-18. Ratified by Meta-CEO B seat 026851bd.*

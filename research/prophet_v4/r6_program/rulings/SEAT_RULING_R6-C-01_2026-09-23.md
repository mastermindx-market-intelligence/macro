# Seat ruling R6-C-01 — Earnings / D5 dossier readiness (B08 / B14 sequencing)

Seat: Fable Meta-CEO (session 48cdfd56). Operation `prophet-us-fable-meta-ceo-20260923-001`. Date 2026-09-23.
Input: `research/prophet_v4/r6_program/wave0/C_EARNINGS_D5_READINESS_CENSUS_2026-09-23.md` (external lane `pu_c_earnings`, mb, read-only; lane PR #7818 closed as superseded, record cherry-picked `-x` onto #7811).

## Verdict
**One real, source-backed dossier is deliverable today — AAPL FY2026 Q3 (`evt_cik0000320193_2026q3_results`) — as display/reference work only.** D5 carries zero authority by construction (`ALL_FALSE_AUTHORITY`, empty `fusion_bindings`), so a delivered dossier cannot move rank, gate, size or `ENTRY_OPEN` until an explicit Conditional Fusion binding exists. The production route is blocked upstream by B1 episode population (A11 = BUILT_NOT_PROVEN, clears only on a natural scheduled `daily.yml` acceptance — never by dispatch), which is outside this seat's power to hasten and is NOT to be dispatched.

## Dispositions of the eleven ranked blockers
| # | Blocker | Ruling | Unit |
|---|---|---|---|
| 1 | No reachable B1 episode generation | ACCEPT; external clock (natural nightly) | none — do not dispatch `daily.yml`; watch the nightly's own receipt |
| 2 | Allowlist ∩ real events = one issuer (AAPL) | ACCEPT | B08 first unit = AAPL reference dossier from the committed fixture path; broadening the allowlist is an EIO-owned question, routed as a finding, not built here |
| 3 | Consensus unlicensed → beat/miss permanently ABSENT; family `rights` block silent | ACCEPT | doc-truth: state it in the rights block (EIO-owned file → finding to `WS:EARNINGS-INTELLIGENCE-OS`); Prophet-side registry row fixed in unit C-DOC |
| 4 | A13 text says UNRESOLVED though `cik_of_issuer` exists and is proven | ACCEPT | unit C-DOC: rewrite A13 clause 1 to RESOLVED with the identity citation |
| 5 | Clock degradation + adapter strictness divergence (`generated_at <= cut` for every revision) | HOLD for a contract ruling | open item C-05; not a build until the D5 contract owner rules which clock binds a revision |
| 6 | No real correction chain; `source_sha256` only from `issuer_release` | ACCEPT as latent | open item C-06; exercised only when a real chain exists — no synthetic production chain |
| 7 | Rights/coverage registry row stale (“E0 in progress”, `ACCRUING`) | ACCEPT | unit C-DOC: refresh the Earnings row to the WS-EIO state, keep the Wire/CI divergence hazard |
| 8 | #7294 EquityDesk source plane ≠ D5 source | ACCEPT | unit C-DOC: one sentence in the D5 contract naming the two planes and that only the company-intelligence plane feeds D5 |
| 9 | `fact:revenue` units admitted but never normalized (USD vs usd_millions) | ACCEPT as a real consumer-comparability defect | unit C-UNITS: normalize at admission to one unit or refuse mixed units, with a RED→GREEN test on the real-producer (`usd_millions`) vs fixture (`USD`) pair |
| 10 | A7 clause 2 misses two current-body readers | ACCEPT | unit C-DOC: add `load_current_workspace` / `load_workspace_with_disposition` to the forbidden list |
| 11 | No handoff record for #7294; grep hits are digit coincidences | ACCEPT | noted; the #7294 program record is owned by its own seat |

## Sequencing
- **B14 (dossier surface) before B08 (production admission):** the AAPL reference dossier is the first bounded unit and is display-tier; B08's production gate waits on blocker 1's external clock.
- Units commissioned from this ruling: `C-DOC` (doc-only truth repairs 3/4/7/8/10, Prophet-owned files only) and `C-UNITS` (blocker 9, code + test). Both go to the external fabric when a slot frees; neither touches EIO-owned `engine/company_intelligence/**`.

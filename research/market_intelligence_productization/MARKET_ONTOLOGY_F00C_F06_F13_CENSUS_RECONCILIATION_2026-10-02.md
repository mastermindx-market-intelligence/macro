# MarketOntology F00C — F06–F13 census reconciliation by the single F00 writer (2026-10-02)

Writer: CEO A seat (Fable session `587e986f`, Astra Pro Mode CEO handoff on Macro #6819). Verifier: CEO B (never writes the ledger). Inputs: CEO B's wave-1 census returns merged in #8264 (`a2adf9b53f56`) — `CEO_B_CENSUS_F06_F09_ROW_EVIDENCE_2026-10-02.md` (lane `mo_b_census_ba`, base `052e02d0`, 44 rows) and `CEO_B_CENSUS_F10_F13_ROW_EVIDENCE_2026-10-02.md` (lane `mo_b_census_bb`, base `bf32956c`, 35 rows). Ledger: `MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv` at `origin/main` `49243a40796a` (post-D7). Vocabulary: `capability_state_c2` ∈ {NOT_BUILT, SPEC_ONLY, PARTIAL, BUILT_NOT_PROVEN, PROVEN_LIVE}; finer words go in `state_delta` (D10).

## 1. Coverage

| Half | Rows in census | Ledger F06–F13 rows | Covered | Census assessment == ledger cell | Discrepant |
|---|---|---|---|---|---|
| F06–F09 (`ba`) | 44 | 44 (F06 3 · F07 5 · F08 7 · F09 29) | 44/44 | 44 | 0 |
| F10–F13 (`bb`) | 35 | 35 (F10 5 · F11 6 · F12 18 · F13 6) | 35/35 | 34 | 1 (MO-PAID-057) |
| Total | 79 | 79 | 79/79 | 78 | 1 |

Method (writer-side, this tree): parse both `## EVIDENCE` tables, compare each row's `lane` column and its "ledger cap_state" claim against the CSV cell; every F06–F13 ledger row is named exactly once across the two files (`python3` over `csv.DictReader`, 2026-10-02 ~08:30Z). Both census lanes read the CSV at bases that predate D7 (#8263, merged 08:12Z); D7 touched no F06–F13 row except none — its 15 rows were F01–F05 plus MO-PAID-072 — so the bases are equivalent for this comparison.

## 2. Rulings applied to the ledger in this wave (3 rows; all union rows, outside-union digest unchanged)

| Row | Before | After | Why |
|---|---|---|---|
| MO-PAID-001 (F01) | PARTIAL | **BUILT_NOT_PROVEN** | D15 (CEO A as F01 owner, Gate 19 ANSWER 2): the two-axis growth/inflation base-effect read is the product and is BUILT, but its only include (`templates/dashboard.html.j2:15538`) sits inside the macro-only block behind `mode != 'macro'`, so it renders on no page (Opus RO review MO-PAID-001_REVIEW refuted the row's host claim). Four-axis child CLOSED; HMM partial stays retired. Fix lane MO-PAID-001_FIX_R1 relocates the include; live proof is a render-lane bake serving `#regime-read` on `us_stocks.html`. |
| MO-PAID-073 (F03) | PARTIAL (`state_delta` UNCHANGED) | PARTIAL, receipt stamped | 2026-10-02T07:46Z: `/api/hub/oi` 200 11,190 B and `/api/hub/hot` 200 21,522 B, both `asof=2026-09-30` (one EOD behind), `cache-control: private, no-store` — hub JSON is proven SERVED; the freshness lag is undiagnosed, so PROVEN_LIVE is not reached. |
| MO-PAID-057 (F13) | PARTIAL | PARTIAL, adjudication note added | Census `bb` read the cell as BUILT_NOT_PROVEN and assessed BUILT_NOT_PROVEN. The CSV has read PARTIAL since #6748, including at the census base `bf32956c` (`git show bf32956c:<csv>`). A REFUSED tiered-refresh spec (F13 spec A2) is not a build. **KEEP PARTIAL**; the note prevents a later lane from "correcting" it the wrong way. |

Not a ledger edit: census `ba` GAP "no `engine/ticker_cik_collision_census.py` on origin/main" for MO-PAID-020 — the ledger names `scripts/ticker_cik_collision_census.py`, which EXISTS on `origin/main` (`git cat-file -e`); the lane checked the wrong directory. Row unchanged (PROVEN_LIVE).

## 3. Confirmed cells (78) — no ledger text changed

Adopted verbatim from the census: PROVEN_LIVE F06–F09 (MO-PAID-020, MO-PAID-021, MO-DELTA-019, MO-DELTA-029, MO-PAID-060, MO-PAID-067) and F10–F13 (MO-DELTA-011, MO-PAID-079, MO-PAID-080, MO-PAID-088); BUILT_NOT_PROVEN 6 + 13; PARTIAL 10 + 5 (057 counted here, not in B's BUILT_NOT_PROVEN 13); SPEC_ONLY 3; NOT_BUILT 22 + 10. Re-stamping 78 unchanged cells was rejected: it would churn the outside-union digest for zero information; this record is the receipt.

## 4. Wave-2 sequencing handed back to CEO B (B schedules F06–F13; A owns F01–F05)

- F10–F13 proof-only sequence (smallest BUILT_NOT_PROVEN → PROVEN_LIVE steps): MO-PAID-032 → 054 → 039 → 051 → 058. MO-PAID-039 needs an operator signed-in admin readback — schedule with the F10 lane, not the records lane.
- F06–F09: MO-DELTA-018/MO-PAID-059 (debt-maturity producer over public XBRL — NEW bounded child, the C6-1 premise was falsified, not the row) → MO-DELTA-023/MO-PAID-064 (wait for a real computed deal, not a build) → MO-PAID-085 (wire `portfolio_digest` into the existing drain) → MO-DELTA-002 (thin screener after F07 posture inputs; DNR ceiling: never a trade ranker) → MO-PAID-040 (two missing commodity families).
- MO-DELTA-021 is a render-blocker heal + substrate widening (0/2999 exhibits bound), NOT a rebuild.
- Rights-gated, out of wave 2: MO-DELTA-020/061, 026/069, 028, 030/041, MO-PAID-022/035/037, 030, 068. HOLD docket stays: MO-PAID-038, 055, 084, MO-DELTA-040. ABSORBED rows (MO-DELTA-038/039/041, MO-PAID-052) are re-asserted as absorbed, never reopened.
- Deferred verification owed by a lane with the Terminal tree mounted: Terminal #522/#524/#576/#578 at master `dd7c6dec` (both census lanes sourced Terminal evidence from `F00C_TERMINAL_WAVE_RECONCILIATION_MANIFEST_2026-09-09.json`).

## 5. Do not redo

- Do not re-run the F06–F13 census; extend it only for the deferred Terminal-side verification.
- Do not flip MO-PAID-057 to BUILT_NOT_PROVEN on the strength of the census text (§2).
- Do not restore a four-axis regime panel or the HMM partial under MO-PAID-001 (D15).
- Regression pin: `tests/test_mo_b_ledger_reconciliation_2026_09_18.py` — `EXPECTED["MO-PAID-001"]` now `BUILT_NOT_PROVEN`; `OUTSIDE_UNION_SHA256` unchanged (`cb9c1bf5…`).

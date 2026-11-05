# R6-B16-01a — Amendment: third mechanism re-adjudicated; macro-only diagnostic era ratified

- Seat: Fable Meta-CEO 48cdfd56 (claude8) · operation `prophet-us-fable-meta-ceo-20260923-001` · parent #6805 · WS:PROPHET-US-V4-RECOVERY
- Date: 2026-09-23 · Amends: `research/prophet_v4/r6_program/rulings/R6-B16-01_ADMISSION_2026-09-23.md` §1 and §3 item 3 only. Everything else in R6-B16-01 stands: no Cycle proving domain is admitted, B16 is CLOSED / NOT PILOT-READY, B18 stays BLOCKED, no trade and no sector are selected.
- Evidence: `research/prophet_v4/r6_program/wave2/CYCLE_A_ERA_TREATMENT_RECORD_2026-09-23.md` (this PR, independent review PASS at 5fda9675) and the B16-a matrix §2 (`D03_SOURCE_READINESS_MATRIX_2026-09-23.md`, #7842): NEWORDER first realtime 1997-03-26 / 354 months; ISRATIO 1997-04-15 / 354; INDPRO 1997-01-17 / 357; no missing vintage months in any of the three.

## 1. Re-adjudication of the third independent mechanism (R6-D03-01 §1(i))

The era record could not determine any dated break for `AWHMAN` from the fetched BLS/FRED pages, so every era in its §3 is "NO: AWHMAN continuity UNKNOWN". Rule 4 is a per-leg requirement, and an UNKNOWN leg cannot anchor an era. The seat therefore substitutes **`INDPRO` (industrial production: an output mechanism)** for `AWHMAN` (labor utilization) as the third independent mechanism beside **`NEWORDER` (order flow)** and **`ISRATIO` (inventory cycle)**. Independence holds: orders, inventories and output are distinct economic mechanisms, and none is a relabeled subtheme of another (rule 4's no-relabel clause; all three remain capital-goods / total-manufacturing grain, never "machinery"). `AWHMAN` is retained as a diagnostic-only fourth leg until its break history is determined; it anchors nothing.

## 2. Era ratified (source clocks only, before any return inspection)

Determined breaks for the three mechanisms: `NEWORDER` 2001-05-21 and 2025-05-16; `ISRATIO` 2001-06-14 (2025-05-16 benchmark applicability UNKNOWN); `INDPRO` 2002-12 and 2025-11-24. The longest span in which all three are present under a single definitional regime with no determined break is:

| Era | Handling | Ratified use |
|---|---|---|
| 1997-04-15 → 2002-11 | pre-NAICS reconstruction regimes (M3 2001-05, MTIS 2001-06, G.17 2002-12); mixed | diagnostic-only splice; excluded from the ratified window |
| **2002-12 → 2025-05-15** | post-SIC→NAICS for all three; no determined break inside; the 2010-04 M3 semiconductor treatment is recorded on `AMTMUO`/`AMTMVS`, not on these three | **RATIFIED macro-only diagnostic window** (≈ 269 months ≥ 120) |
| 2025-05-16 → latest | post-2025 M3 benchmark, INDPRO 2022-NAICS conversion 2025-11-24; ISRATIO applicability UNKNOWN | new era, too short and partly UNKNOWN; excluded |

The window is derived from publication clocks alone. No return, outcome or ledger artifact was opened to choose it, and it may not be moved by inspecting one.

## 3. What this does and does not admit

- **Admits, once the rights register (#7843) is merged:** a **macro-only, internal-only, retrospective diagnostic** on `NEWORDER`/`ISRATIO`/`INDPRO` over 2002-12 → 2025-05-15, with survivorship reported as a limit (rules 2–3 macro-only clauses) and every FRED leg internal-only (rule 5's private-diagnostic clause, matching the register's FRED posture). It is not a pilot, not public, not a B16 selection, and does not unblock B18. Its commissioning packet must name the three legs, the window, "internal-only", and the no-return-before-preregistration order, and must preregister its endpoints before any return is computed.
- **Does not admit:** any issuer-mapped pilot (rules 2–3 fail at every cut, per the matrix), any public surface (rule 5 unresolved for FRED model use and redistribution), or the Chairman provider question — its precondition (rules 1, 4 and 5 otherwise satisfiable for a public pilot) still fails on rule 5, so it is not yet askable.

## 4. Disposition

Records: this amendment beside R6-B16-01 under `rulings/`; the era record is the evidence of record at 5fda9675. D03 closure = matrix (#7842) + rights register (#7843) + era record (this PR) — all three RULED by the seat; D03 closes at their merge with the residuals named in each.

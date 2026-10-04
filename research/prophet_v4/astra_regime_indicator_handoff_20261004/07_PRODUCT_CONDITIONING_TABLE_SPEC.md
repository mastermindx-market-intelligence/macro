# 07 — Product conditioning-table spec (wave 2 deliverable; filled at C2 adjudication)

Program: prophet-astra-ceo-fable-20261004-001 · Seat: Fable (Claude Code session f273dd7d) · Spec frozen 2026-10-04; verdict cells filled only after C2 is adjudicated by the seat.

## 0. Acceptance gates (what "done" means for this document)

Not done unless: (1) every row of §3 is filled from a lane's `result.json` by key, never retyped; (2) every cell carries its honest-N (events / months / names) and era split; (3) the evidence level (chapter 03 §6) is printed on the table itself; (4) the table states, in its first line, that it is DISPLAY-TIER and proposes nothing to authority (rank, size, gate) — the gauntlet is the promotion gate; (5) the owners named in §1 have acknowledged receipt (ladder rung ACCEPTANCE is theirs, not ours).

## 1. Consumers and boundary

- V4 Prophet owners (carrier #6805; incumbents #7581 / #7180 / #7572 are never seized by this program) receive the table as a PROPOSAL with evidence level stated.
- Prophet management-law owner receives F1's hazard rows (§4) under the same terms.
- Temporal Grain owners receive the clock findings (A1) as context.
- Nothing here is a router: the served Prophet admission path is unchanged by this document. Phase-22 discipline (chapter 06) binds: no conditioning table is consumed by Phase 22 without a prior preregistration.

## 2. Table schema (one row per rotation state × confirmation grain)

| column | source | note |
|---|---|---|
| rotation_state | C1 `rotation_state_daily` tercile (fast / mid / persistent) | C1 controls status printed beside it (`BROKEN` means the state is a label, not a measurement) |
| confirmation_grain | 1D / 2D.p / 3D.p / 1D.M2 / 1D.M3 / 3D.K1 | B1 variant ids under the amended constants (`DEC:B1-MEMORY-FACTOR-DIRECTION`) |
| expected_cost | C2 secondary (a): mean `confirmation_cost_pct`, CI | "cost of waiting" |
| expected_protection | C2 secondary (b): share of false starts avoided, CI | |
| large_winners_excluded | C2 secondary (c), CI | |
| net_excess_h10 / h21 | B1 contrasts, CI | cost-adjusted SPY-excess |
| honest_n | events / months / names, both eras | floors: ≥24 months, ≥100 names, ≥300 events |
| support | ADEQUATE / INSUFFICIENT (C2 cell floors) | |
| evidence_level | 2, final-vintage, survivor-selected | never "validated" |

## 3. Verdict branches (chapter 03 §7, reproduced so the fill is mechanical)

| C2 verdict | B1 verdict | What §2 is filled with |
|---|---|---|
| SUPPORTED | grain effect real | per-state recommended confirmation grain (slow in persistent states, 1D with tighter management in fast states) with cost / protection columns |
| SUPPORTED | memory, not grain | same conditioning expressed as kernel memory on the 1D grain (1D.M2 / 1D.M3 rows) |
| NOT SUPPORTED | any | the table is published EMPTY with the sentence "no timeframe conditioning proposal at evidence level 2; the September 2026 narrative is recorded as not supported"; attention moves to F1 |
| INSUFFICIENT SUPPORT | any | the named gap and the exact lane that closes it |

Fill status (updated by the seat, 2026-10-04): C2 round 0 ACCEPTED on the round-1 inputs (B1 panel sha256 8b170497…, C1 rotation table 9361dbf0…), independently reproduced to six decimals by the Opus review. Verdict = INSUFFICIENT SUPPORT by the pre-declared rule (C1 controls.status BROKEN: AR(1) at lag 21 of the long-period LP series = −0.0404 against the > 0.5 gate). Counterfactual, labelled and never a verdict: with controls PASS the same rule reads NOT SUPPORTED for 3D and for 2D — pooled 3D DiD on H10 net = +0.0035 (95% month-cluster CI [−0.0009, +0.0076]), opposite in sign to the hypothesis, eras +/+ (+0.0033, +0.0051), 0 of 3 phases with DiD < 0 and a CI excluding zero, 3D cost curve non-monotonic (fast 0.048 / mid 0.147 / persistent 0.121). Named gap: C1's primary control. Exact lane that closes it: none in this wave — C1 round 2 adds a pre-declared calibrated-control SENSITIVITY (200 positive-control simulations, 200 block-permuted nulls), but the primary gate is never re-tuned, so the table's rule status stays INSUFFICIENT SUPPORT unless a future, pre-registered control passes. Product fill: §2 is published EMPTY, carrying both sentences — the INSUFFICIENT SUPPORT gap sentence above and the NOT SUPPORTED sentence ("no timeframe conditioning proposal at evidence level 2; the September 2026 narrative is recorded as not supported") because the counterfactual points the same way. Attention moves to F1 (management) and E (family context, display-tier). B1 round-1 verdict under the amended constants = NOT SUPPORTED on 3D / 2D / memory (per-cell rule); B1 round 2 (test hardening, SPY-calendar outcome alignment of 18 events, corrected pooled Δ headline ≈ +7.0e-5 with CI) is in flight and is a confirmation, not a reopening. C2 round 1 (test hardening + re-run on the round-2 inputs) is a confirmation lane; the verdict is DO_NOT_REDO unless an r2 input moves a CI across zero.

## 4. Management annex (F1)

Filled from F1 `result.json` after round 1 under `DEC:F1-EMBARGO-IS-21-NYSE-SESSIONS`: OOS AUC with CI (primary, 21-session purge) and the 22-calendar-day sensitivity row; hazard by horizon bucket; the MIXED / MANAGEMENT / SELECTION verdict by rule. A MANAGEMENT verdict proposes hazard-based exit/review rules by signal age; a SELECTION verdict proposes entry-state screens to the ranker owners; MIXED proposes neither and says so.

## 5. Family annex (E, wave 2)

Filled from E `result.json`: the twelve-test table, winners ranked by |I|/SE or the scoped null. A winner is a CANDIDATE for a conditioning column, display-tier only; it enters this table as context, never as a rule.

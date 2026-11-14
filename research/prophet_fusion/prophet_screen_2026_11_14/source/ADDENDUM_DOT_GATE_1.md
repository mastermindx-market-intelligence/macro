# Addendum: DOT-GATE-1, the double gate retested with the dot (RD, 2026-11-14)

**Governing row:** ceo-dot-gate-1 (CEO, quoting the Chairman: "double gate can be retested with the dot if possible with a small test to see if it works"). A small named test, reported on its own and early. It is a cut of what the trough table already holds, not a new programme. Hashed by the leader before any label is read.

**Governs with.** PLAN_TROUGH_v1 (426ae551), RUN_NOTES_LEADER (a303ba6d), TROUGH_BREADTH_DEF_v1 (d8f18acc), ADDENDUM_TROUGH_WITHINDAY_v1 (c0cc028b) and v1a (05acdf0e), NOTE_DOT_FAMILY_v1 (c6d238b9). Where this file is silent, they govern.

## 1. Event and arms
- **Event.** Every G3 event in EVENTS_G3 (Terminal-twin dot, completed buckets), SCREEN 2013-01-02..2019-12-31 only, dated at known_ts. Same eligibility, folds and hindsight-guard drops as the trough table.
- **Gate flags**, on the stock's own dated basket (R44) on known_ts, leave-one-out (the stock is removed from the basket before anything is computed):
  - **A1 basket dot:** the LOO basket's own G3 dot (house mask on the LOO equal-weight basket close) has known_ts in the last 10 sessions ending on the stock's known_ts.
  - **A2 dot breadth:** LOO basket dot_share_10 ≥ that basket's SCREEN 80th percentile.
  - **A3 floor breadth:** LOO basket floor_share ≥ that basket's SCREEN 80th percentile.
  - **A4 none:** A1, A2 and A3 all false.
  - The 80th-percentile cuts are made per basket on H10c-valid SCREEN days (R1a), with all members (group-level series), printed before any label is joined, and then applied to the LOO value. Days that are not H10c-valid put the event in "gate undefined", counted, not tested.
- A1–A3 overlap. Each is tested as flag-true against A4 (none). A1∨A2∨A3 ("any gate") against A4 is a fourth line. The overlap table (counts of each combination) is printed.

## 2. Outcomes
- **PRIMARY:** real63 at 1.0 ATR_c (plan §2).
- **Description:** real21; signed distance from the true swing low (sessions and %); MAE at 21 and 63; fwd21 and fwd63 relative to SPY.

## 3. Comparisons
- **(i) Same day.** Gated against ungated dots on the same day, by the W1 design: label and flag centred on the day mean, singleton days excluded and counted. The CI is a 2000-draw month-block bootstrap.
- **(ii) Same-month shuffle.** The gate flag is shuffled among dots within the same calendar month × personality tercile, 20,000 draws. The counting p is the share of shuffled effects at least as large as the observed one, two-sided.
- **(iii) Against the old double gate's T1 entry** (description, not counting). The old gate is pass 3's TAILWIND-armed stock T1 entry (`successor/harness/pass3/ENTRIES_stock_t1.csv`, definition BRIEF_PASS3_CONFIRMATION 1010770d, "Group state"), read-only.
  - For each gated dot: the first TAILWIND T1 entry on the same stock within 63 sessions after known_ts, with no undercut of the trough low before it.
  - Print the captured move close(T1)/close(dot) − 1 and the session lag.
  - Print false calls both ways: the share of gated dots that undercut before any TAILWIND T1 or never get one, and the share of TAILWIND T1 entries with no gated dot in the 21 sessions before.
  - One plain sentence each on earliness and on false calls, with the DF2 caveat: completed buckets make our earliness a lower bound on live earliness, and the live false-call rate can be higher than measured.

## 4. Counts and MDE first
- Per arm: events, distinct months, distinct days, base rate, W1 deff, effective n.
- The MDE (80%, two-sided) at Bonferroni α .10/4 for the four lines, by the WD4 planning SE.
- Every line is reported however large its MDE. Above 15 pp it reads "under-powered at this design (MDE X pp)". It is not a null, and the line is not dropped.

## 5. Scope and standing
- **Its own family.** There are four counting lines, at Bonferroni .10/4. They do not enter the trough BH family, and they do not add to m_screen.
  - A1–A3 are the same columns as plan §3g. A DOT-GATE-1 result and a §3g screen result are one piece of evidence, not two.
- **SCREEN only.** Basket-arm features are F1_hold_excluded (plan §0). DOT-GATE-1 makes no HOLD claim, and it is labelled "Stage 1, paper research, SCREEN 2013–19".
- **Grades.** Coverage: 2013–17 survivor-biased, 2018–19 usable. Evidence: ≥ 20 tested, 8–19 limited, < 8 case-based.
- **Order.** It runs as soon as EVENTS_G3 and the basket breadth file are hashed, before W-FEATURES finishes. It joins only the A1–A3 columns to labels, and it opens no other feature.
- **Closing line:** `DOT_GATE_1 COMPLETE n_a1 n_a2 n_a3 n_a4 mde_any=<pp> p_any=<p> <sha8 RESULTS.md>`

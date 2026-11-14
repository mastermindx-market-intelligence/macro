# Run notes: DOT-GATE-1, leader rulings (RD, 2026-11-14)

**Governs with.** ADDENDUM_DOT_GATE_1.md (sha256 939523d7…, leader HASH OK, row dot-gate-1-hash-ok-rulings). Where these notes and the addendum differ, these notes govern.

- **G1. Counting p: shuffle across basket-day clusters within the same day.**
  - The gate flag is basket-level, so the effective unit is the basket-day.
  - The counting p comes from shuffling the flag across basket-day clusters within the same day, with all dots of a basket-day moving together. This matches the W1 same-day statistic, and the shared market move on the day stays fixed. 20,000 draws, two-sided.
  - Days with only one basket carry no contrast. They are counted and excluded.
  - The month × personality-tercile dot-level shuffle (addendum §3(ii)) is printed as description only.
- **G2. "Gate undefined" stays its own counted group, never A4.**
  - As description, also print the any-gate line with undefined treated as A4.
- **G3. One piece of evidence, one family.**
  - DOT-GATE-1 is the pre-registered test of A1–A3.
  - In the trough screen, the §3g columns that equal A1–A3 are description only, pointing to DOT-GATE-1, and are removed from the trough BH family. m_screen is printed both ways.
  - There is no best-of-two-families: a line that fails in one family is not rescued by the other.
- **G4. "Works" is defined before any label is read.** DOT-GATE-1 "works" only if all three hold:
  - (a) the any-gate line passes Bonferroni .10/4 in the favourable direction (real63 higher for gated dots);
  - (b) its point estimate beats a plain comparator at the same share. The comparator flags the dots whose LOO basket has the weakest trailing 63-session relative strength against SPY, taking the same number per year as any-gate. It is description only, but it is required for the "works" wording;
  - (c) fwd63 relative to SPY has the same favourable sign.
  - Otherwise the line reads "no measurable benefit at this power", or, if the MDE is above 15 pp, "under-powered at this design (MDE X pp)".
  - A favourable but uncorrected result reads "a hypothesis for an unseen test", never "works".
- **G5. LOO bias, description only.**
  - Print the share of events flagged A2 under the LOO value against the share under the full-member value.
  - Print the same for A3. The design is unchanged.
- **Order.** EVENTS_G3, BASKET_BREADTH and EVENT_GATE_COLS hashes go to the leader first. DOT-GATE-1 runs only after that.

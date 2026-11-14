# Brief: W-DOTGATE, DOT-GATE-1 (RD, 2026-11-14)

**Governs.** Before you start, check three hashes and stop if any differs:
- `catalogue/trough/ADDENDUM_DOT_GATE_1.md` must begin 939523d7;
- `catalogue/trough/RUN_NOTES_DOT_GATE_1.md` must begin 6326db7e (it governs where the two differ);
- `catalogue/trough/PLAN_TROUGH_v1.md` must begin 426ae551.

Copy these three files and this brief into RUN_LOG first. Then read ADDENDUM_TROUGH_WITHINDAY_v1 (c0cc028b), NOTE_DOT_FAMILY_v1 (c6d238b9) and TROUGH_BREADTH_DEF_v1 (d8f18acc).

**Inputs.** Everything in `catalogue/trough/events_v1/` is read-only:
- `EVENTS_G3.parquet`, `BASKET_BREADTH.parquet` and `EVENT_GATE_COLS.parquet`. Check each against `events_v1/SHA256SUMS`, and also against the hashes the RD gives in the launch message.
- `catalogue/successor/harness/pass3/ENTRIES_stock_t1.csv`, which must begin f38f7d65.
- Panel rev 5, for the LOO basket 63-session RS comparator (G4b) and fwd63 vs SPY. Follow CONSUMER_NOTES C1–C5 and U1, and assert that nothing dated 2024-01-02 or later is loaded.

**You do.**
1. Addendum §1–§4, with G1–G5. Order of work:
   - Print counts and MDE per arm first, to MDE.md, and hash it.
   - Then join labels and run the four counting lines: A1, A2, A3 and any-gate, each against A4, at Bonferroni .10/4.
     - The counting p comes from a within-day basket-day cluster shuffle, 20,000 draws, two-sided (G1).
     - The CI comes from a 2000-draw month-block bootstrap.
   - Description:
     - the month × personality shuffle;
     - the undefined-as-A4 line (G2);
     - the G4b weakest-RS comparator at the same share per year;
     - the LOO-vs-full flag shares for A2 and A3 (G5);
     - the arm-overlap table;
     - real21, distance from the swing low, MAE21/63, and fwd21/fwd63 vs SPY.
2. §3(iii), the old double gate T1 comparison, description only. Write one plain sentence on earliness and one on false calls, plus the DF2 two-sided caveat.
3. VERDICT.md, using only the G4 wording. "works" requires G4 (a), (b) and (c) together. Otherwise use "no measurable benefit at this power", "under-powered at this design (MDE X pp)" or "a hypothesis for an unseen test".
4. Every number carries:
   - the coverage grade (2013–17 survivor-biased, 2018–19 usable);
   - the evidence grade (≥ 20 tested, 8–19 limited, < 8 case-based);
   - the label "Terminal-twin dot, completed buckets; Stage 1, paper research, SCREEN 2013–19".

**You do not.**
- Read any HOLD-window label: dates 2020-01-02 onward are never joined.
- Join any trough feature other than the A1–A3 columns.
- Change any threshold.
- Open any of these: `catalogue/two_speed/astra/`, `catalogue/trough/astra/`, `catalogue/out/`, `catalogue/out_boundary/`, any `*SEALED*` file, `pivots.parquet`, `data/french/sealed_post2019/`, `catalogue/event_table/v3*/` outcome files, SI files.
- Use the network, secrets, git or delegation.
- Write raw prices.
- Edit engine code.

**Environment.**
- Run `date -u` first, and again before every time label.
- Python: `/home/ubuntu2/tmp/rotation-core/v4/.venv/bin/python -P -E -B`, run from /tmp, never with -I. At most 8 processes.
- Output folder: `catalogue/trough/dot_gate_1/`. Write PROGRESS.txt as you go.
- Outputs: MDE.md, RESULTS.md, VERDICT.md, OVERLAP.md, T1_OLDGATE.md, RUN_LOG.txt and SHA256SUMS.

**Closing line:** `DOT_GATE_1 COMPLETE n_a1=<n> n_a2=<n> n_a3=<n> n_a4=<n> n_undef=<n> mde_any=<pp> p_any=<p> verdict=<works|no_benefit|underpowered|hypothesis> <sha8 RESULTS.md>`

**Deadline:** 2 hours from start.

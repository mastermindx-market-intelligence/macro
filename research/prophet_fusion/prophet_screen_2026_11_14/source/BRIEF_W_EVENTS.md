# Brief: W-EVENTS, trough entry v1 (RD, 2026-11-14)

**Governs.** `catalogue/trough/PLAN_TROUGH_v1.md` is binding. Its sha256 must begin 426ae551; if it does not, stop. Leader rulings on the plan, if any, are in `catalogue/trough/RUN_NOTES_LEADER.md`. Copy that file into RUN_LOG first.

**You do** plan §1 (events and the hindsight guard), §2 (labels and the T1 comparison) and §5 (Stage 0), for G3, G1, GW, G2W and GRP-DOT. You also build the minimum Stage 0 needs: the own baskets for GRP-DOT, and the personality tercile used as a permutation stratum (plan §3b scale, prior data only).

**You do not:**
- build the other features;
- join any feature to any label;
- run Stage 1.

You end after Stage 0 and wait for the leader's reply through the RD.

**Environment.**
- Run `date -u` first, and again before every time label.
- Python: `/home/ubuntu2/tmp/rotation-core/v4/.venv/bin/python -P -E -B`, run from /tmp, never with -I. At most 8 processes.
- No network, no secrets, no git, no delegation.
- Output folder: `catalogue/trough/events_v1/`. Write PROGRESS.txt as you go.

**Hard rules.** All of plan §0. Also:
- **Engine.** `ext/macro_main_e999086d` is read-only. Print the sha256 of `engine/stock_identity/replay/grey_dot.py` and of `engine/confluence_tiers.py`. Use `confluence_tiers.py` for the house T1, exactly as `catalogue/successor/harness/pass3/pass3.py` does. Reuse that code by import or copy; do not change its logic.
- **Panel.** Rev 5, per `panel/rev5/CONSUMER_NOTES.md` C1–C5 and U1. Assert that nothing dated 2024-01-02 or later is loaded.
- **Never open:** `catalogue/event_table/v3/` outcome files, `catalogue/two_speed/astra/`, `catalogue/out/`, `catalogue/out_boundary/`, any `*SEALED*` file, `pivots.parquet`, `data/french/sealed_post2019/`, SI per-group files.
- No raw prices in the output folder.

**Outputs.**
- `EVENTS_<table>.parquet`: derived fields and labels only.
- `HINDSIGHT_GUARD.md`: the 300-dot truncation check, plus fire-date parity on NVDA, NFLX and TSLA.
- `COUNTS.md`: events, folds, exclusions, coverage grade by year, S&P 600 description.
- `T1_COMPARISON.md`: pooled description only, no features.
- `STAGE0.md`: per table × window, the counts, base rate, both ICCs, deff, effective n, planning SE, the MDE at the BH rank-1 bound and at the Bonferroni bound, and STOP/PROCEED at 15 pp.
- `SHA256SUMS`.

**Closing line:**
`TROUGH_EVENTS COMPLETE g3_screen=<n> g3_hold=<n> guard=<agree>/300 deff=<x> mde=<pp> stage0=<PROCEED|STOP list> <first 8 hex of STAGE0.md sha256>`

**Deadline:** 2.5 hours from start.

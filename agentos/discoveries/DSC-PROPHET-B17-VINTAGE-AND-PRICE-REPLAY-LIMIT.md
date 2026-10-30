---
key: PROPHET-B17-VINTAGE-AND-PRICE-REPLAY-LIMIT
claim: >
  The existing price-only standout replay cannot produce the historical
  shipped Prophet buy roster, and the vintage-board PIT replay cannot prove
  2014-2025 live availability from this Macro repository's main history.
falsifier: >
  A source-bound pre-2026 main/vintage commit with the full shipped board and
  historically available non-price producer inputs would disprove the Git
  history limit; a demonstrated exact roster-reproduction test using the
  existing price-only replay would disprove its documented capability limit.
  Check GitHub main commit history and run a full-population PIT reproduction
  bound to input availability and first-surface evidence.
so_what: >
  For WS:PROPHET-US-V4-RECOVERY B-17, do not substitute the 2012+ price-gate
  replay or the force-majeure vintage-board replay for missing shipped-roster
  measurement. Seek a separate qualified full-population, time-stamped historical
  admission archive and non-price dependencies; otherwise preserve unknown and
  request an explicit study-scope decision instead of fabricating coverage/lead.
kind: data
verified_at: 2026-10-30
verified_by: >
  GitHub GET /repos/mastermindx-market-intelligence/macro/commits?sha=main&
  until=2025-12-31T23:59:59Z&per_page=1 returned []; same with
  2014-12-31. scripts/replay_standout_pipeline.py at
  0bcc11b27cd8 lines 1084-1093 and 1146-1158 explicitly denies
  board buy[] reconstruction from close-only PIT. scripts/prophet_pit_replay.py
  at the same ref lines 1231-1265 resolves a real first-parent vintage main
  commit before a session bake slot or refuses.
scope:
  - macro
  - WS:PROPHET-US-V4-RECOVERY
  - scripts/replay_standout_pipeline.py
  - scripts/prophet_pit_replay.py
  - research/prophet_v4
confidence: verified
---

# B-17 historical roster evidence is not a price-only replay

**Observed scope, October 30, 2026.** GitHub's `main` commit API returned
no commits at or before 2025-12-31 and none at or before 2014-12-31.
This is evidence about this repo's committed main history, not proof that
other provider archives, object storage, financial-history data, or private
historical admission records do not exist.

The B-17 exact-path `site/factordata/us_standouts.json` history recorded
579 revisions starting June 16, 2026. The already recovered sample has 57
complete snapshots and 32 distinct `as_of` dates through the August 10
frozen cutoff. It yielded **zero of 7,918** C0 episodes with all
34 historical admission dates. That is missing input, not a zero historical
coverage or lead result.

[Production-gate replay source](https://github.com/mastermindx-market-intelligence/macro/blob/0bcc11b27cd884165af61841e0e59b90fd27f124/scripts/replay_standout_pipeline.py)
explicitly diagnoses its output as *not reconstructable as the buy[] board
from close-only PIT*. It computes a 2012+ production signal-gate history,
but ranks and vetoes on the shipped board also involve entry timing,
cross-sectional scoring, sector restrictions and other producer inputs.

[General vintage replay source](https://github.com/mastermindx-market-intelligence/macro/blob/0bcc11b27cd884165af61841e0e59b90fd27f124/scripts/prophet_pit_replay.py)
reconstructs an existing bake session from the newest committed main tree
before the slot, and enforces vintage fidelity and price right-edge controls.
It is for a missed actual session with a real vintage source, not a way to
invent a pre-repository user-visible board or certify historical data
that did not exist at its claimed availability time.

**Implication.** The existing historical price series and C1-relaxed
4,800/7,918 baseline remain usable *as what they are*. B-17's required
union-plus-production-gate full-roster measurement needs historical
full-population board or all historically bound producer inputs with
availability clocks and independent scientific adjudication. A new
PIT replay of current stock-library code with an earlier `as_of` stamp
would not satisfy this dependency.

**Falsifier / change condition.** Find an independent pre-2026 source
archive (Git elsewhere, object storage, dated published boards, or source
provider snapshots) whose complete original population, producer-rule
vintage and observation/serving clocks are demonstrably qualified.
Then use the pinned B-17 original population and ruler without relabeling
C1-relaxed scores as shipped-roster coverage.

## Frozen denominator versus observable repository history — October 30, 2026

A read-only direct Git object extraction of
`228c25d37617a7217c8f65f1613ade701a2fe01a:research/prophet_us_audit/early_admission_bakeoff_episodes.parquet`
returned 8,096,374 bytes, SHA-256
`a55f3e3ecaef13efc6dc0a407375ee3d87e66b6dfb70eacb0c1d3b7249c6feb4`.
The 39,877-row source was filtered by `addon == False` and
`construction == "C0"` (no new population or selector). The result contains
**7,918 C0 episodes**, earliest **2014-12-04**, latest **2026-08-10**.
Relative to the first recovered board-archive source date **2026-06-16**:

- **7,775** C0 episodes (**98.19%**) are before that first archive date;
- **143** (**1.81%**) are on or after the first archive date;
- **zero** are after the original 2026-08-10 frozen cutoff.

Reproduction: `git show 228c25d37617a7217c8f65f1613ade701a2fe01a:research/prophet_us_audit/early_admission_bakeoff_episodes.parquet`
from the original Macro object store; use `pandas.read_parquet`, filter
`~df.addon.astype(bool) & df.construction.eq("C0")`, and split
`pandas.to_datetime(df.date).dt.date` at `2026-06-16`.
The run completed with exit 0 on the original source; SHA-256 and counts
were read back from that single bounded process.

**Interpretation:** 98.19% is **not a measured 0% shipped-roster coverage**.
It is the part of the frozen event denominator for which the recovered
repository board history has no contemporaneous source dates. The 143
later episodes are at most a *date-range eligibility population*, not
proof of admitted or first-visible candidates: the existing 57 archived
snapshots cover only 32 distinct dates, and the B-17 report found **zero
complete 34-session admission windows** even for that later slice.
The next material dependency is independently sourced full-population
historical producer inputs and original availability clocks, or an explicit
scientific ruling about what can and cannot be measured without them.
No redefinition of the frozen denominator, no present-day rerun posing as
historical admission, no promotion of the C1-relaxed baseline.

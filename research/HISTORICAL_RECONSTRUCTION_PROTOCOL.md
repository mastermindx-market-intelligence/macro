# Historical Reconstruction Protocol

**Status:** STANDING. Binds every research, metric and study session in this repo.
**Authority:** Chairman ruling, 2026-11-12. Recorded by the Sector Intelligence COO.
**Amends:** `research/MASTERMIND_TEMPORAL_DATA_STANDARD.md` §5.1 and §11 (rules 1, 8 and 12), as stated in section 5 below.

## 1. The ruling, in the Chairman's words

> "This can likely easily be reproduced through historical data, it isnt something we need PIT data for."

> "We cant just rely on recorded data because that would take ages to have and years to record. So in almost all cases, we should be creating the historical data for most of our metrics and studies. PIT is not a requirement."

> "Make this a fixed protocal within our research framework so future sessions know this too"

## 2. The rule

1. **History is reconstructed, not awaited.** When a metric, a signal input or a study needs a past, build that past from historical data. This is the default for almost every metric and study.
2. **A written-forward record is never a prerequisite.** "We only started recording this on date X" is a reason to reconstruct. It is never a reason to wait, to shorten a study to the recorded span, or to decline the work.
3. **Point-in-time data is not a requirement.** A missing dated membership list, a missing historical label or a missing data vintage does not block building a history or running a study on it.
4. **Never report an input as missing before looking for it.** Check the stores first (section 3). Session checkouts are sparse and omit most of `data/`, so an absent directory proves nothing.

## 3. Before saying "we do not have the history"

Do these in order. Stop at the first that answers.

1. List the store on the default branch: `git ls-tree --name-only origin/main data/<domain>/`. Read `config/sparse_worktree.json` to see what your checkout leaves out.
2. Find the writer and the readers: `git grep -n "<file name>" origin/main -- collectors engine scripts`.
3. Check whether the raw inputs exist even if the derived series does not (price, volume and membership caches). If they do, the history can be rebuilt.
4. Only then state what is missing, naming the paths you checked.

The incident behind this section: on 2026-11-12 a census row read one snapshot file and concluded that sector breadth had no past. `data/breadth/` held a dated sector series, dated index membership and the full price caches. The wrong claim reached the Chairman and another programme before it was corrected.

## 4. How to reconstruct

These are the working rules. Items marked *(COO)* are the recording seat's interpretation of the ruling, not the Chairman's words.

1. **Each value uses only data dated on or before its own date.** A rolling average for a day is built from that day and earlier. This is ordinary correctness, not a point-in-time requirement. *(COO)*
2. **One code path.** The function that computes tonight's value computes the history. Do not fork the maths into a separate backfill script that can drift. *(COO)*
3. **Use the best basis that already exists, at no extra cost.** If the repo already holds dated membership or a vintage store for the input, use it. If it does not, apply today's membership and today's labels to the past and proceed. Do not buy data or build a new point-in-time store to satisfy this protocol. *(COO)*
4. **Label the basis.** Every reconstructed artifact carries, in its own metadata or a sidecar file:
   - `basis`: one of `recorded_forward`, `reconstructed_dated_membership`, `reconstructed_current_membership`, `reconstructed_revised_values`;
   - the span, the build time, the code version, and the input stores read;
   - one plain sentence naming who or what is missing (for example: "names delisted before 2026 are absent").
   *(COO)*
5. **Say the basis in the same sentence as the result.** A finding on a reconstructed series names its basis when it is reported. The label is information for the reader. It is not a gate. *(COO)*
6. **Keep recording forward as well.** The nightly run goes on appending. Where the recorded and the reconstructed series overlap, compare them once and write down the difference. That measures the reconstruction error for free. *(COO)*
7. **Off the render path.** A history build is heavy compute. It runs outside the nightly render budget, and large artifacts go to R2 under the existing rules.

## 5. What this changes in the Temporal Data Standard

- **§5.1, research tier.** The rule was: a research, backtest or calibration caller must raise when a reader answers `pit=False`. It is now: the caller must **check the flag, stamp the basis on its output, and proceed**. Silently using the answer without recording the basis is still a defect.
- **§11 rule 1.** An input without an as-of reader no longer means "you do not have a backtest yet". It means the run is on a reconstructed basis and says so.
- **§11 rule 8.** `members_asof(...)` with `pit=False` is recorded, not refused.
- **§11 rule 12.** The run stamp gains the `basis` field of section 4.4.
- **No code changes with this text.** The fail-closed reader (`lib/dataos/temporal.py`) still raises for a caller that asks for a point-in-time answer it cannot give. A reconstruction does not ask for one: it reads the stores directly and labels its basis.
- **Unchanged.** The rest of the standard stands: where a release-dated or filing-dated reader already exists, use it (§11 rules 2, 3 and 6); timestamps, session calendars, price-store discipline and the entry clock (rules 9 to 11); a self-check must be able to fail (rule 14).

## 6. What this does not change

- **The promotion gate.** Building, displaying and studying are free. Promoting a rule to a scored, ranked or sized use still passes the existing gauntlet and the adjudication coverage gate in `AGENTS.md`, including naming who is missing from the panel.
- **The kill registry.** `research/DO_NOT_REBUILD.md` still binds. A reconstructed history is not a reason to rerun a killed construction.
- **A sealed hold-out.** Where a preregistered protocol has sealed a period, the seal holds for that protocol. Building a data series over that period is allowed. Relating it to outcomes inside the sealed period belongs to the protocol that holds the seal.
- **Data rights and spending.** No purchase of outside data is authorized here.

## 7. Where to look next

- `research/MASTERMIND_TEMPORAL_DATA_STANDARD.md` for clocks, time zones and existing as-of readers.
- `research/MASTERMIND_EVALUATION_STANDARDS.md` for how a result is judged.
- `research/DO_NOT_REBUILD.md` before starting any study.

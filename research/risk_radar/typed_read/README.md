# Typed read harness

A small research harness that describes catalogue turns by regime **type**. It is
paper-only research plumbing: it sizes, ranks and executes nothing, and it applies no
decision.

Run the tests from the repository root:

```
python3 -m pytest research/risk_radar/typed_read -q
```

## What this harness does NOT do

* **It defines no type.** `B`, `N`, `D`, `S`, `U`, the three `U` reason codes and the six
  flag states are name strings taken verbatim from the Research Director's frozen
  `TYPE_SPEC_v1` (+ addendum A/B). Every value in the input is read as an opaque label.
  No label is computed, extended, or invented here.
* **It applies no decision.** Addendum A's 40% coverage line is *reported* per era
  (`within_line: true/false`), never enforced, never turned into a switch.
* **It has been tested only on synthetic labels and synthetic turns.** No real type file,
  no real turn file, and no real leg series has been read by this module. Output 2's guard
  exists so that a real join cannot happen by accident.

## Output 1 — description by type (the default output)

For each era (default `PRE` 2006-01-03..2019-12-31 and `D` 2020-01-02..2023-12-29; extra
eras can be passed on the command line), for the core label and for each of the six flags:

* session count and share of sessions in the era;
* count of catalogue turns whose date falls on a session with that label / state;
* count of distinct clusters among those turns.

**Suppression rule:** any cell with fewer than 8 distinct clusters prints counts only — no
share and no rate. The cell is marked `counts only` and its session share and rates render
as `—`.

Also reported per era, each against the 40% line: the core-`U` share (with its reason-code
breakdown) and each flag's `unavailable` share. A share exactly at 40% counts as within.

A turn whose date is not a labelled session is excluded from every cell and is counted in
the header line instead, so nothing silently disappears.

```
python3 research/risk_radar/typed_read/typed_read.py \
    --types types.csv --turns turns.csv \
    --eras PRE=2006-01-03:2019-12-31 --eras D=2020-01-02:2023-12-29
```

`describe` is the default subcommand, so the `describe` word may be omitted.

## Output 2 — per-leg catch and false calls (guarded)

`per_leg_table(alerts, turns, types, ...)` takes one boolean daily alert series and reports,
per era and per type cell:

* **catch share of clusters**: a cluster is caught when any *used* ON session lies inside
  `[-21, +5]` sessions of any of its turn dates. The declared t+1 shift is applied first: the
  decision at close `t` is used at `t+1`, so a session `s` reads the raw series at `s-1`.
* **false calls**: an ON-start (used-ON after used-OFF) with no turn date inside
  `[-21, +5]` of it, expressed per year of sessions in the cell (252 sessions/year).

Cells under 8 clusters print counts only, exactly as in Output 1. A cluster spanning several
type labels is assigned to the cell of its **earliest** turn date.

### The guard

`per_leg_table` raises `GuardRefusal` unless it is called with:

* `synthetic=True` — the synthetic path, which is the only one this harness's tests use; or
* `ledger_path=` a JSONL ledger **and** `row_id=` a row id present in it, where that row's
  JSON has **`"typed_read_joint": true`** and **`"approved_by_rd": true`**. The flags are read
  from the row itself or from its `primary_spec` object.

A missing file, a missing row, a non-JSON line, or either flag absent/false refuses. The CLI
exits 3 on refusal and prints the reason to stderr.

## Input format

Column names live in **one constant** at the top of `typed_read.py`:

```python
COLUMNS = {
    "date": "date", "core_label": "core_label", "core_reason": "core_reason",
    "flag_rate": "flag_rate", "flag_real_rate": "flag_real_rate",
    "flag_credit": "flag_credit", "flag_credit_level": "flag_credit_level",
    "flag_dollar": "flag_dollar", "flag_easing": "flag_easing",
}
TURN_COLUMNS = {"date": "date", "series": "series", "cluster_id": "cluster_id",
                "kind": "kind"}       # kind is optional
ALERT_COLUMNS = {"date": "date", "alert": "alert"}
```

To read the RD's real file, change the right-hand strings only; no logic below reads a
literal column name (there is a test for that).

Types (CSV or parquet):

| column | allowed values |
|---|---|
| `date` | session date; strictly before 2024-01-02 |
| `core_label` | one of `B N D S U`, exclusive per session |
| `core_reason` | one of `MISSING_INPUT CONFLICTING_STRUCTURE ENTRY_CONFIRMATION`; required for `U`, must be empty otherwise |
| `flag_rate`, `flag_real_rate`, `flag_credit`, `flag_credit_level`, `flag_dollar` | `present` \| `absent` \| `unavailable` |
| `flag_easing` | the same three, or `PRICE_STRESS_EASING_PARTIAL` |

**`unavailable` is never treated as `absent`.** They are counted, stored and reported as
separate states, and the unavailable share is reported on its own for the 40% line.

Turns (CSV or parquet): `date`, `series`, `cluster_id`, optional `kind`. When `kind` is
present only `kind == "top"` rows are read; when it is absent every row is a top turn.

Alerts (CSV or parquet, Output 2 only): `date`, `alert` (boolean or 0/1).

### Strict validation

All of these raise `TypedReadError`: unknown label, unknown reason code, unknown flag state,
blank flag value, duplicate date (types and alerts), a non-`U` label carrying a reason code,
forbidden-for-that-flag state (e.g. `PRICE_STRESS_EASING_PARTIAL` on `flag_rate`), a missing
required column, a turn with no cluster id, unparseable dates, and any date on or after
**2024-01-02** in types, turns, alerts or an era's end bound.

## Spec ambiguities (stated, not resolved by inventing a rule)

1. **`U` without a reason code.** The spec says the `U` reason is one of three codes but does
   not say a `U` row may leave it blank. `REQUIRE_U_REASON = True` makes a blank `U` reason an
   error; set it `False` to read a file that leaves it blank. This harness does not pick a
   default reason.
2. **Reason code on a non-`U` label.** The spec implies empty, so a non-`U` row with a reason
   code is a format error here.
3. **`PRICE_STRESS_EASING_PARTIAL` is a fourth *state*, not a fourth core label.** It is
   accepted only on `flag_easing`. In counting it is neither `absent` nor `unavailable`, so it
   appears as its own row and is not charged to the 40% unavailable line.
4. **PRE's start for the coverage line.** Addendum A §2 counts PRE "from the first date the core
   rule can publish on its input basis", while the block calendar is PRE through 2019-12-31.
   This harness counts every session it is given inside the era's bounds. If the real PRE file
   starts later than 2006-01-03, pass its actual first session as the PRE era start; do not
   let this harness guess.
5. **Cluster-to-cell assignment in Output 2.** The spec does not say which cell a cluster
   belongs to when its turns fall on sessions with different labels. This harness uses the
   label of the cluster's earliest turn date, and says so in the rendered table's definition
   line.
6. **False-call start convention.** The desk scorer counts an *alert run START* (off -> on).
   This harness does the same, on the *used* (t+1-shifted) series, and counts a start as false
   only when no turn date lies within `[-21, +5]`. It deliberately does not add the desk
   scorer's `min_off` all-clear or in-episode matching, which needs episode data that is not
   part of this task's inputs.
7. **Turns on unlabelled sessions.** A turn whose date is not a labelled session is excluded
   from cells and reported in the header, since no cell can claim it.

## Format rulings (Research Director, FORMAT_RULINGS_001, sha256 111b469f…98e5)
1. Every published U row carries exactly one reason code; a blank code refuses the file (`REQUIRE_U_REASON = True`).
2. `PRICE_STRESS_EASING_PARTIAL` counts as available for the 40% line and is reported as its own row.
3. PRE starts at the first session on which the core rule can publish (stated in the description and in the RD's format note); pass that date as the PRE era start. Flag unavailable shares are measured over the same PRE and D eras. D is 2020-01-02..2023-12-29.
4. A cluster takes the published label and flags of its earliest turn's session (Output 1 cluster counts and Output 2). Output 1 also reports, as description, the count of clusters whose turns carry more than one core label.

Per-type catch and false calls in the real read are scored through the desk reference module (bm_ref rev1), not Output 2's simplified count, and only after the joint ledger row exists.

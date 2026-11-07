# Systematic input qualification bridge (Macro #10089)

A thin, read-only gate that sits between a **caller-supplied** R2 price capture
and the systematic backtester. It answers one question, honestly and separately
in two parts: *may these bytes be used as current data?* and *may they be used
as economics?* Those are different questions with different answers, and this
module never collapses them.

| Path | What it is |
|---|---|
| `engine/systematic_inputs.py` | the pure qualification function + capture readers |
| `scripts/qualify_systematic_inputs.py` | the only thing that touches a filesystem |
| `tests/test_systematic_inputs.py` | 108 tests, all fixtures synthetic |
| this file | the contract, the blocker codes, the adapter plan |

## What this is not

It is **not** an ingestion pipeline, a price authority, a corporate-action
adjuster, a dataset registry, or a scheduler. Every one of those has an owner
and this module adds none of them. The parent lane `systematic-10089-ceo-web-01`
owns actual data acquisition; this bridge only qualifies what that lane hands
over, and only inputs a caller explicitly supplies. It performs no network
access, contacts no account, touches no ledger, and has no default output path.

It creates **no new qualification law**. Every decision routes through
contracts that already exist:

- **Session calendar** — `lib.us_cash_calendar` (`is_session`,
  `sessions_between`, `expected_last_session`). No holiday table is hand-coded.
  A missing session is therefore *detected* against the published calendar
  rather than compressed away by comparing counts.
- **Price basis** — `lib.dataos.price.AdjustmentBasis`. The raw-tape refusal is
  the enum's own `unlawful_for` prose, quoted into the output rather than
  re-declared here.
- **Source status, basis and rights** — `lib.dataos.registry.Registry` /
  `DatasetContract`, plus `_is_evidence_pointer` for the R00.02 evidence rule so
  this file cannot drift a second copy of it.
- **Corporate actions** — `lib.dataos.registry.qualify_action_input` is the
  single qualify-first gate. `SUSPECTED` and its reason code come from there.

## The output document

`systematic_input_qualification.v1`, always mode `RESEARCH_ONLY`. It is a
**diagnostic research artifact, not a source ledger** — it records evidence and
readiness, and grants no signal authority.

```
schema                              "systematic_input_qualification.v1"
mode                                "RESEARCH_ONLY"        (never anything else)
as_of                               offset-aware ISO instant
requested_mode                      current | historical_reconstruction
expected_completed_session          the session the caller expects
current_data_ready                  bool  — every non-excluded instrument is
                                          structurally complete AND fresh at the
                                          expected session
economic_inputs_ready               bool  — rights + non-raw basis + CONFIRMED
                                          action evidence + PIT declared + structure
allowed_use                         "inspect_only" | "descriptive_reconstruction"
capital_eligible                    false   (always)
live_orders_enabled                 false   (always)
historical_original_availability_proven   false unless an existing-owner proof
                                          pointer passes the R00.02 evidence test
source / capture / actions          findings + stable blocker codes
instruments[]                       per-symbol structure, freshness, suspected
                                    actions, source digests, retained exclusions
                                    each with `blockers` (structural) and
                                    `action_blockers` (action findings)
```

`current_data_ready` and `economic_inputs_ready` are **deliberately separate
booleans**. Passing structural readiness is not capital or economic eligibility,
and `allowed_use` only reaches `descriptive_reconstruction` when the economics
actually qualified *and* the caller asked for a reconstruction.

### Honest shape for a raw sample

Running the bridge over a raw capture of three complete symbols, one of which is
missing a single mid-range session and two of which show a ~50% move on the same
date:

```
SPY  ready=True   blockers=[]
XLE  ready=False  blockers=['CALENDAR_GAP']  missing_sessions=['2026-08-18']
XLK  ready=True   blockers=[]
     suspected_actions=[{session: 2025-12-05, change_fraction: 0.49985,
                         action_status: 'SUSPECTED', origin: 'price_discontinuity',
                         factor_applied: false}]

current_data_ready    False   (XLE is incomplete, so the declared universe is)
economic_inputs_ready False   (raw basis + no confirmed action + PIT undeclared)
allowed_use           inspect_only
capital_eligible      False
```

That is the correct answer: **structurally fresh symbols, an incomplete one, and
every economic input held for action qualification.** Unknown is not free
execution, and the bridge refuses to make the three look uniform.

## The laws this module will not break

- **A price jump is an inference, never an event.** It may add a `SUSPECTED`
  reason; it never applies a factor and never becomes a confirmation. The
  observed ~50% move is reported with `factor_applied: false` and is routed
  through `qualify_action_input` with `origin="price_discontinuity"`, which can
  only ever answer `SUSPECTED / DISCONTINUITY_INFERRED`.
- **Absence of a jump is not evidence of absence of an action.** A clean tape is
  still economically blocked.
- **A fresh manifest cannot authenticate stale local bytes.** Freshness is
  decided on the *actual* per-file last session read from the frame; the
  receipt's `last_session` is a claim and is compared against the fact, with
  `manifest_claim_matches_actual` reported either way.
- **Stale is not the same as historical reconstruction.** A reconstruction can be
  requested explicitly with `--mode historical_reconstruction`, but it is never
  reported as current, and it never sets `current_data_ready`.
- **A bad instrument is never omitted quietly.** Every symbol in the declared
  universe appears in the output, with an explicit blocked state; per-symbol
  exclusions are retained with their reason.
- **`null` is not `0`.** Null volume and zero volume are counted and reported
  separately, and the zero count is always published so "measured zero zeros"
  is never confused with "not measured". The registry records that native
  parsing normalises missing source volume to zero, so a zero is treated as
  *suspected erased missingness* and refused by a dependent capacity check.
- **Rights are independent and undeclared is not granted.** A right nobody
  evidenced is `unverified`, and dependent use is refused. A `granted` right
  whose evidence pointer is unlawful (a URL, a `data/` path, the row's own
  licensing label) still blocks.
- **`historical_original_availability_proven` does not accept a bare caller
  `true`.** Only an owner proof pointer that passes the existing R00.02 evidence
  test may set it. Economic readiness never flips this field.
- **A whole-file receipt time is a current observation of every historical row
  in that file.** It is not proof of what was knowable at any past decision
  point, and the document says so in `reconstruction_note`. No per-bar past
  receipt is fabricated.

### Capture integrity

The CLI verifies every declared object before qualifying anything, so a capture
that fails integrity never produces a partially-trusted document.

- Strict JSON: duplicate keys (at any nesting depth) and `NaN`/`Infinity` are
  refusals, never a last-wins merge.
- `received_at` must be offset-aware and `<= as_of`; `as_of` must be aware too.
- Declared size and SHA-256 must match the **actual** bytes, with a per-object
  byte bound and a total bound. A declared row count must match the decoded
  frame.
- An object is stat-ed before and after the read; a size/mtime/inode/device
  change between the two observations is a refusal, because the digest would
  otherwise describe bytes that were never one stable file.
- Filenames come **only** from a declared object's key basename. The receipt's
  `local_file` is not parsed at all, so a hostile absolute path in the receipt
  cannot redirect a read. Traversal, absolute names and final-component symlinks
  are refused, and the resolved path's parent must equal the resolved root.
- The output is written atomically (`os.replace`) and is duplicate-safe: a
  byte-identical existing file is left untouched, so a repeated run does not
  churn the output.

## Blocker codes

Stable UPPER_SNAKE, one per decision rule, so a refusal path can branch on the
code rather than on prose. The full set lives on `engine.systematic_inputs.Code`.

| Area | Codes |
|---|---|
| Receipt | `RECEIPT_JSON_INVALID`, `RECEIPT_DUPLICATE_KEY`, `RECEIPT_NOT_OBJECT`, `RECEIPT_TIMESTAMP_NAIVE`, `RECEIPT_TIMESTAMP_AFTER_AS_OF`, `RECEIPT_TIMESTAMP_MISSING`, `RECEIPT_SCOPE_NOT_READ_ONLY` |
| Object | `PATH_ESCAPE`, `PATH_SYMLINK`, `OBJECT_NOT_FOUND`, `OBJECT_NOT_REGULAR_FILE`, `OBJECT_TOO_LARGE`, `OBJECT_CHANGED_DURING_READ`, `OBJECT_SIZE_MISMATCH`, `OBJECT_HASH_MISMATCH`, `OBJECT_ROWS_MISMATCH`, `DUPLICATE_OBJECT_KEY`, `SOURCE_KEY_PREFIX_MISMATCH` |
| Structure | `FRAME_NOT_SUPPLIED`, `FRAME_EMPTY`, `DATE_COLUMN_MISSING`, `SESSION_LABEL_UNPARSEABLE`, `SESSION_LABEL_DUPLICATE`, `SESSION_LABEL_NOT_CHRONOLOGICAL`, `SESSION_LABEL_NOT_A_SESSION`, `SESSION_INDEX_IS_AWARE`, `PRICE_COLUMN_MISSING`, `PRICE_NON_FINITE`, `PRICE_NOT_POSITIVE`, `PRICE_INEQUALITY_VIOLATION`, `VOLUME_NULL`, `VOLUME_NEGATIVE`, `VOLUME_ZERO_SUSPECTED_MISSINGNESS`, `CALENDAR_GAP` |
| Freshness | `EXPECTED_SESSION_NOT_SUPPLIED`, `LAST_SESSION_STALE`, `LAST_SESSION_IN_FUTURE`, `LAST_SESSION_NOT_A_SESSION`, `FRESHNESS_NOT_EVALUABLE`, `MODE_HISTORICAL_NOT_CURRENT` |
| Actions / rights | `SOURCE_NOT_PRODUCED`, `BASIS_NOT_DECLARED`, `BASIS_RAW_UNLAWFUL_FOR_ECONOMICS`, `ACTION_EVIDENCE_MISSING`, `ACTION_EVIDENCE_MALFORMED`, `ACTION_NOT_CONFIRMED`, `ACTION_SOURCE_NOT_PRODUCED`, `PIT_CORPORATE_ACTIONS_NOT_DECLARED`, `RIGHTS_UNDECLARED`, `RIGHTS_NOT_GRANTED`, `RIGHTS_EVIDENCE_UNLAWFUL` |
| Universe | `HISTORICAL_AVAILABILITY_NOT_PROVEN`, `SYMBOL_EXCLUDED` |

`SUSPECTED_ACTION_DISCONTINUITY` is the one code that is **not** in an
instrument's `blockers` list. A suspected jump is an *action* finding, not a
structural defect — the file is still complete and well-formed — so it is
reported in a separate per-instrument `action_blockers` list. That way a clean
`blockers` list can never be misread as "no corporate action happened".

`OBJECT_ROWS_MISMATCH` is emitted whenever the receipt declares a row count that
differs from the decoded frame, so a receipt cannot describe a file it did not
contain. When the receipt omits `rows`, the check is simply not claimed.

## CLI

```
python -m scripts.qualify_systematic_inputs \
    --capture-root /path/to/capture \
    --output /path/to/qualification.json \
    --as-of 2026-10-22T19:05:00Z \
    --expected-session 2026-10-21
```

`--output` is required — there is no default and no production path. Useful
extras: `--expect-receipt-sha256` (fences the receipt file itself),
`--mode historical_reconstruction`, `--action-evidence` / `--economic-evidence`
(JSON), `--universe`, `--volume-requires-positive`, `--jump-fraction`,
`--max-object-bytes` / `--max-total-bytes`, `--fail-on-blocked`.

Exit codes: `0` a document was written (blocked is a valid, useful answer),
`2` usage/registry error, `3` capture integrity failure or `--fail-on-blocked`.

## Adapter plan → `PriceFrame` (PR #10093) — NOT YET IMPORTABLE

`PriceFrame` (`frame`, `available_at`, `adjustment_basis`, `sessions_per_year`,
`synthetic`, `source`, `ticker`, `notes`) is defined by PR #10093, which is
**not merged into this base**. Nothing here imports that module, and nothing
here fabricates a per-bar past receipt to satisfy it. This is the mapping to
apply **after that PR merges and after review**, owned by the parent lane:

| Field | Source of truth | Constraint |
|---|---|---|
| `ticker` | declared universe symbol | must appear in `instruments[]`; an instrument with blockers is still emitted, not dropped |
| `frame` | the parent's captured frame | this bridge emits a **qualification document**, never a frame; it must not become a second data source |
| `available_at` | the whole-file capture receipt time | this is a **current observation of every historical row**. It must be carried with the current-vintage reconstruction limitation attached in `notes`. It is never a claim that the row was knowable at that past date. |
| `adjustment_basis` | `raw` only while `economic_inputs_ready` is false | `sadj`/`tradj` only with an **accepted action-qualified price-view receipt** from the existing owner (`lib.dataos.price_views.admit_action_input` / `admit_revision_set` / `sadj_view`). `raw` for return math stays blocked by `AdjustmentBasis.RAW.unlawful_for`. |
| `sessions_per_year` | the calendar/backtest owner | **never hardcoded here**; the annualisation constant belongs to the backtester |
| `synthetic` | fixture provenance | must be `true` for every fixture in `tests/` — those frames are invented, not market data |
| `source` | registered identity | `dataset_id` + `object_key` + verified `sha256` from `capture.objects_verified[]` |
| `notes` | this document's codes | carry `current_data_ready` / `economic_inputs_ready`, the blocker codes, and `historical_original_availability_proven: false` so no downstream consumer can read a qualified frame as capital-eligible |

Integration requirements on the parent lane, stated plainly:

1. **Data acquisition stays with the parent.** This bridge never fetches.
2. **Corporate-action qualification needs an existing owner.** The live
   `reference.corporate_actions.massive_split_evidence` row is `PROPOSED` with
   opt-in capture only and no declared basis, so `qualify_action_input` answers
   `UNQUALIFIED / SOURCE_NOT_PRODUCED` for it. Until its owner produces it,
   `economic_inputs_ready` stays `false` for every instrument. **This bridge
   does not flip that status and does not fabricate events.**
3. **`point_in_time_corporate_actions` is undeclared (`None`) on the price
   contract.** That is a real gap, reported as
   `PIT_CORPORATE_ACTIONS_NOT_DECLARED`, and it blocks economics even when the
   action evidence itself qualifies.
4. **Resolving the XLE-style gap** is an acquisition/backfill question for the
   parent, not something this module repairs or compresses.

## Scope boundary (Macro #10089 P3)

Direct, disjoint, leaf work under `systematic-10089-20261022`, actual parent
`systematic-10089-ceo-web-01`. New paths only — `engine/systematic_inputs.py`,
`scripts/qualify_systematic_inputs.py`, `tests/test_systematic_inputs.py`,
`research/systematic_inputs/README.md`. No change to `engine/validation.py` or
`engine/systematic_research.py` (PR #10093), UI files (PR #10092), the dataset
registry, corporate-action owners, store collectors, credentials, workflows,
live data, QLedger, accounts, source histories, Paper or broker.

Run:

```
python -m pytest tests/test_systematic_inputs.py -q
```
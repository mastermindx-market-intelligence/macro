# B05 same-read join — independent adversarial review (2026-10-21)

- Review lane: `lane/pro-source-b05review-20261021-r1` (fresh tree at BASE).
- Artifact under attack: `git diff e5dd30c6344e4b62a0beba054ac4da97e00bab36..39b2767ffe21`
  — `engine/prophet_b4_same_read.py` (411 lines, new), `tests/test_prophet_b4_same_read.py`
  (582 lines, new), `.github/ci/legacy-jobs.yml` (one line). Nothing else is in the diff.
- Reviewer did not write the change. Every dismissal below carries the bytes that close it.

## Verdict

**STATUS: PASS_WITH_NOTES** — the frozen spec (points 1–8) is satisfied exactly; two NOTEs
(A1 documentation breadth, A8 packet premise about CI triggering) require no artifact change.
`research/prophet_v4/r7_program/` did not exist at BASE; this report mints the packet's path.

## Spec verdicts (1–8)

1. **PASS — envelope contract.** Entry point
   `evaluate_same_read_entry_availability(repo_root, snapshot, *, candidate_source_event_id,
   candidate_source_receipt, native_live_root, alias_table, strategy_definition,
   signal_gate_artifact=None)` at `engine/prophet_b4_same_read.py:267-277` matches the frozen
   signature exactly. `SAME_READ_SCHEMA = "prophet.b4.same_read/v1"` (:54). `RESULT_KEYS`
   (:57-68) is a module constant holding exactly the ten keys; tested verbatim both
   directions at `tests/test_prophet_b4_same_read.py:162-167`. `unavailable_reasons` and
   `receipts` are sorted str lists on every path (:335, :362, :371, :402, :410; single-element
   paths trivially sorted; `[]` on EVALUATED), asserted :169-172.
2. **PASS — one read.** `build_native_factual_assessment_result` called exactly once (:302,
   inside the try); the pair is taken only from `native.verified_pair()` (:307); the module
   never imports `project_candidate_states`. `read_native_b4_owner_inputs` called exactly
   once (:320-327) with the SAME `snapshot` object passed straight through and the same
   key/receipt. Spies pin all of it: `tests:195-241` — `builder_calls == 1` (:227),
   `reader_calls == 1` (:233), `reader_calls[0][0][1] is world["snapshot"]` (:234), same
   key/receipt (:235-236), projector ran exactly once inside the builder (:239), and the
   module has no `project_candidate_states` attribute (:240).
3. **PASS — binding.** `_BINDING_FIELDS = ("security_id", "episode_id",
   "candidate_generation_id", "market_session")` (:76) are exactly the names the reader
   emits (`engine/prophet_entry_availability_sources.py:1210-1216`, plus `store_symbol`
   which is echoed, not compared). `_binding_mismatches` (:235-264) compares against BOTH
   B3 carriers; any mismatch returns `state=UNAVAILABLE_DATA`, `availability=None`,
   `SAME_READ_BINDING_MISMATCH:<field>` (:360-364). No repair path, no ticker join anywhere
   in the module. Real foreign-read proof: `tests:299-347` (a genuinely different store's
   qualified read types `SAME_READ_BINDING_MISMATCH:candidate_generation_id`).
4. **PASS — refusal passthrough.** `quote_input is None` or non-empty reader
   `unavailable_reasons` → UNAVAILABLE_DATA with the reader's reason strings
   `sorted(str(...))` only — unprefixed, unrenamed (:332-337). Pinned verbatim at
   `tests:350-379` (`["QUOTE_STALE_AT_OWN_READ", "READ_SESSION_CROSS_SESSION"]`). The B4
   evaluator is reached only at :388 with owner-chain inputs; the module never builds a
   facts mapping (the two `{}` kwargs are the composer's documented no-owner value,
   `sources:554-565`).
5. **PASS — facts and attestation.** Single `evaluate_runtime_entry_availability` call
   (:388-400). Owner files are re-read and re-hashed: `"sha256:" + sha256(raw).hexdigest()`
   compared to `owner_reads.<name>.sha256` (:195-200; same digest format as the reader's
   `_sha256_receipt`, `sources:730-731`); any difference or unreadable file →
   `SAME_READ_OWNER_BYTES_CHANGED:<name>` with no retry (:370-373; test `tests:382-402`
   mutates each file after the read). Geometry/metric inputs are `{}` (:397-398), asserted
   by the interposition wrapper (`tests:113-114`). `decision_at` is
   `clocks["live_pass_ts"]` (:377) and `market_session` comes from the binding (:380); the
   module contains no wall-clock read (no `now()`/`_now_utc`/`time` — only ISO parsing at
   :109-119, :146, :160-165). Only the three contract classes are caught (:85-89; catches
   at :308 and :401), typed `"<ExceptionClass>: <message>"` (:105-106); anything else —
   e.g. the reader's snapshot TypeError (`sources:839-842`) or `classify_nbbo`'s
   `ValueError` — propagates.
6. **PASS — outcome honesty.** The B4 row is returned unmodified (:407); the happy test
   reproduces it byte-for-byte against a direct evaluator call (`tests:278-290`). The module
   emits only `EVALUATED`/`UNAVAILABLE_DATA` (:70-71) and never `ENTRY_OPEN`; no-ENTRY_OPEN
   is asserted with future owners injected (`tests:258-259`) and at BASE with no row at all
   (`tests:176-192`). Compact UNKNOWN is never FAIL: the three D01 unknown cases assert
   `OWNER_CONFLUENCE_UNKNOWN` present and `OWNER_CONFLUENCE_NOT_PASSED` absent
   (`tests:472-506`).
7. **PASS — classify_nbbo.** Signature `classify_nbbo(bid, ask, nbbo_ts, *, decision_at,
   max_age_seconds)` (:122-129). Seven outcomes in check order MISSING → INVALID →
   UNCLOCKED → STALE → LOCKED → CROSSED → QUALIFIED (:151-174); timestamp after
   `decision_at` is STALE (:166-167); age exactly at the ceiling is QUALIFIED (strict `>`
   at :168; boundary pair `tests:542-545`). `nbbo_quality` is assigned only to the envelope
   (:295, :382) and never appears among the evaluator kwargs; at BASE it is MISSING because
   the reader's `observed` (`sources:1273-1280`) carries no `bid`/`ask`/`nbbo_ts` →
   :217-218; asserted `tests:191,261,379`.
8. **PASS — determinism.** `json.dumps(first, sort_keys=True) == json.dumps(second,
   sort_keys=True)` under pinned owner clocks (`tests:156-173`). The module adds no entropy:
   no clock, no randomness, and every set-derived output is sorted before leaving.

## Attack surfaces (A1–A8)

**A1 — DISMISSED (fail-loud is correct; unreachable at BASE).** The reader's qualified
return is the only path with `quote_input` non-None, and it populates every field the
defensive raises guard, unconditionally: `result["binding"] = {...}` with all five names
(`sources:1210-1216`); `result["owner_reads"]` with `path` and `sha256` for both
`quotes_full` and `prophet_live` (:1237-1254); `result["clocks"]` (:1255-1264) whose
`live_pass_ts` is the `pass_ts` already parsed by `_utc` at :1037-1040 (a malformed value
fails `LIVE_OWNER_MALFORMED` before any qualified return). Every absent-fact path returns
through `fail()` with `quote_input=None`, which the join passes through at :332-337 BEFORE
the first defensive raise. `not isinstance(payload, Mapping)` (:374-375) cannot fire: the
re-attested bytes are digest-equal to bytes the reader already parsed as a Mapping
(`sources:1009`, `:1028`). `rows != 1` (:356-359) is enforced upstream by `verified_pair`
(`engine/prophet_candidate_state.py:795-804`). Ruling: these six sites describe a reader
that broke its own contract — typing them `UNAVAILABLE_DATA` would dress a reader bug as
data-unavailability; raising is the honest failure. **NOTE (documentation):** the function
docstring (:282-285) says every absent mandatory owner fact types the envelope; the six
defensive raises are outside that coverage. No observable effect at BASE; a future reader
change should either keep these guards or narrow the docstring.

**A2 — DISMISSED.** At BASE the reader raises only for caller-contract violations:
`_trusted_root` (`sources:686-692`, called at :837-838 — "must be an existing absolute
operator directory") and the snapshot type check (:839-842). Its docstring states the law:
"Failure of any check returns a result, never raises — caller-contract violations (wrong
types for the trusted roots or the snapshot) are the one exception and raise
TypeError/ValueError" (:833-835); `RuntimeOwnerFactError(ValueError)` (`:101`) satisfies
that wording. `quote_input_receipt` (:762-776) cannot raise for the reader's own
construction — `_QUOTE_INPUT_RECEIPT_FIELDS` (:755-760) is a subset of the keys built at
:1288-1306. Every ordinary absent fact is a typed refusal via `fail()` (:861-865 and every
check quoted above). The join calling the reader outside any try is therefore correct: an
operator programming error is not an absent owner fact, and the spec's own law (only three
classes caught; others propagate) is consistent with escape.

**A3 — DISMISSED.** The wrapper (`tests:103-125`) captures `source_kwargs` and asserts
`source_kwargs["entry_rows_by_symbol"] == {}` and `source_kwargs["metric_inputs"] == {}`
at `tests:113-114` BEFORE injecting the future-owner fixtures; a non-empty module value
raises `AssertionError` inside the wrapper and fails the test. The wrapper is used by the
happy test (:251) and `_d01_row` (:456), which feeds all five D01 tests. The happy test
additionally pins that the module served the ATTESTED bytes and the owner read's own
clocks (`tests:269-273`: `decision_at == served_live["meta"]["pass_ts"]`,
`quotes_by_symbol == served_quotes["quotes"]`, `live_state_artifact == served_live`,
`signal_gate_artifact is None`).

**A4 — DISMISSED — no None-poisoned carrier exists.** The projection schema is closed
(`candidate_state:442-452`) and REQUIRES top-level `candidate_generation_id` (string,
generation regex, :465-472) and `market_session` (canonical, :473-476) — absence is not a
representable document. Every row's closed key set (:499-516) includes
`candidate_generation_id`, forced equal to the projection's (:520), and `episode_id`/
`security_id` as non-empty text (:526, :531). `verified_pair` re-enforces
projection↔assessment equality for `candidate_generation_id` and `market_session`
(:783-788), `row.security_id == assessment.security_id` (:807), and exactly one bound
episode row (:795-804). The assessment side is equally closed (`security_id`, `episode_id`,
`candidate_generation_id` as text :1407-1408; canonical `market_session` :1413-1418). The
module's expected-carrier table (:247-259) compares exactly the carriers that carry each
field — the projection top level carries no `security_id` and rows carry no
`market_session`, and neither is compared against those carriers — so no legitimate bound
read can produce a false `SAME_READ_BINDING_MISMATCH`.

**A5 — DISMISSED — no second, unattested read.** `evaluate_runtime_entry_availability`
(`sources:660-679`) is pure delegation: `compose_runtime_owner_facts(**source_kwargs)` then
`evaluate_entry_availability`. The composer (:483-657) consumes only its parameters; the
sole disk read in the sources module is `_read_owner_bytes` (:734-736), called only inside
`read_native_b4_owner_inputs` (:997-998 read, :1154-1160 re-read). The session-policy
helper `engine/prophet_entry_policy.py::evaluate_session_eligibility` contains no file-read
calls (grep clean). The only bytes the join hands the composer are the ones it re-hashed
itself (:366-375).

**A6 — DISMISSED — nothing is minted.** `receipts` is the union of:
`str(assessment.get("source_receipt"))` (:315 — regex-pinned non-None by
`candidate_state:1421-1424`, so `str()` is identity), `str(projection.get("projection_id"))`
(:316 — bound to the provenance digest by `candidate_state:772-779`), the reader's
`quote_input["source_receipt"]` added only `if isinstance(receipt, str)` (:338-341; minted
by the reader at `sources:1307`), and the row's `source_receipts` added only when a list
(:408-409). No digest, stamp, or receipt string originates in this module.

**A7 — DISMISSED.** The only reason producers are: the reader's own strings (sorted
passthrough :335), `SAME_READ_BINDING_MISMATCH:<field>` (:261),
`SAME_READ_OWNER_BYTES_CHANGED:<name>` (:371), and `_typed_reason` =
`f"{type(exc).__name__}: {exc}"` (:105-106, used at :309 and :402). No other format exists
in the module.

**A8 — DISMISSED with a premise correction (NOTE).** Exactly one line changed
(`legacy-jobs.yml:27114`), same 8-space indentation and `python -m pytest … -q` form,
appended to the `run:` line naming `tests/test_prophet_whynot_receipts.py`; the
`prophet-anticipation-intake` job block (27065-27115) has no `paths:` filter. However the
packet's inference "so the new file runs on every PR" is not how this manifest executes:
every job must declare `if: ${{ false }}` so GitHub allocates no duplicate runner
(`scripts/run_ci_pack.py:1578-1584`) and the steps are packed by a planner; this job
declares `gate: data` (`legacy-jobs.yml:27085`), so it is packed by `data-health.yml`'s
`--gate data` invocation (`data-health.yml:133`), which triggers on the nightly `daily`
`workflow_run`, a 13:30 UTC schedule sweep, and manual dispatch — not per PR. The edit is
exactly the one line the frozen artifact description prescribes and matches the incumbent
whynot suite's placement; the suite also runs green wherever the pack executes. The repo's
own static closure guard passes at BASE: "OK — every module a gated suite reads can start
the job that runs it" (0 trigger gaps; 141 suites in 14 data-marked jobs are excluded from
the PR closure gate by design). No artifact change required; the packet's trigger claim is
corrected for the D01 record.

## Evidence

- pytest (packet scope, one run):
  `python3 -m pytest -q -p no:cacheprovider tests/test_prophet_b4_same_read.py
  tests/test_prophet_strategy_definition.py tests/test_prophet_candidate_state.py
  tests/test_signal_gate_validity_contract.py`
  → `256 passed in 3.57s` (exit 0). New suite alone → `30 passed in 1.52s`.
- `git diff --stat e5dd30c6344e4b62a0beba054ac4da97e00bab36..39b2767ffe21`:
  `.github/ci/legacy-jobs.yml | 2 +-`, `engine/prophet_b4_same_read.py | 411 +`,
  `tests/test_prophet_b4_same_read.py | 582 +` — 3 files, +994/−1. No other file touched.
- Key quoted bytes appear inline above (reader qualified return, closed schemas,
  `_trusted_root`, planner gate law, data-health trigger).

## Gaps

- No network by rule: the reader's real vendor/live-lane provenance was exercised only
  through the existing fixture world, as in the incumbent suites.
- The nightly `data-health` pack itself was not executed here; its behavior is cited from
  its workflow bytes and the planner source.
- `data/prophet/ledger*`, scoreboard, track-record, outcome and returns paths were not
  opened (excluded by rule).
- `research/prophet_v4/r7_program/` did not exist at BASE (`git ls-tree` empty); this
  report creates the packet's directory. `r6_program/` uses a different layout
  (reviews/rulings/wave*), so `source/` is a new convention carried by the packet itself.

## Deviations

- None in method or scope. The only addition beyond a literal reading is the A8 premise
  correction and the A1 documentation NOTE, both reported rather than repaired, per the
  rule that a repair is a separate fix lane.

SESSION END: PROVEN_OUTCOME

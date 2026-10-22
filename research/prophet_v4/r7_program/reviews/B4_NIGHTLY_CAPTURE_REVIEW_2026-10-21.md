# B4 nightly capture — adversarial review (ROUTE: review, MODE: READ_ONLY)
PR: #9959
Head: b2efcfade9dc23f29c63b559ffe13874006596de (parent1 lane f249b541b692bf55a73a9db7fca89d60126b13e8)
Parent-2 base: 562fc7dd02a95792c1a3f59dee2e147f5ffddf20
STATUS: FAIL

Two BLOCKING findings (F1 verdict trace persisted in `facts`; F2 null-security_id key collision kills the census). All cited TREE files are byte-identical to `git show b2efcfa:<path>` (checked with cmp).

## Per-spec-point verdicts

1. TARGET — PASS. `capture_dir` = `_store_dir(root).parent / "b4_capture"` (script:203-211); `_repo_root, _store_dir, resolve_board_as_of` are imported from `engine.us_prophet_w3` (script:75), not copied. W3 files are never written; the only write is `_merge_and_write` on `capture_path` (script:516-526). NOTE: the script always passes an explicit root, so the target is `ROOT/data/...`, while W3's root=None path uses `config.data_dir()` (w3:200-204). These are equal today (`config.yml` `storage.data_dir: data`). The divergence is latent.
2. DISCIPLINE — PARTIAL. The lane gate (script:538-550) runs before any read; the first read is `resolve_board_as_of` (script:565). The only `mkdir` is at script:516, after the gate. `stamp_date` comes only from `resolve_board_as_of`, and None means exit 3 (script:565-571). `_now` is called once (script:581). `_now` is defined at script:198-200 and has no other call site; there is no CLI clock. Findings F3 (durable `--root`) and F4 (`--dry-run --nightly` needs the armed lane and is untested).
3. ROW — FAIL (F1). `schema`/`ROW_KEYS` are closed (script:81-106, 337-340). `facts` is None unless state == EVALUATED (script:370, 310-314). The lane DEVIATION `VERDICT_FIELDS=("state","entry_open","chase_state","availability_id")` (script:118) is REJECTED: `blockers` and `reasons` are the evaluator's decision trace and encode the verdict injectively. Key classification is below. The D11 fence exempts only the row-level `state` (script:346-348) and checks every other scalar against `AVAILABILITY_STATES` (script:349-354). That part is correct, but the check is token-equality only, so it cannot catch a trace encoding.
4. ENUMERATION — FAIL (F2). The script does one snapshot read (`_load_snapshot`, script:578). Measured: capture-module loads=1. The owner reader does N attestation re-loads (sources:884; measured `{'capture': 1, 'sources': 3}` for 3 candidates), see F6. Candidates come from the `us_prophet_rank.candidates/v1` rows filtered on stamp (script:252-260). An absent stamp means exit 3 (script:573-577). The derivation is byte-identical to the builder (quoted below). `STRATEGY_DEFINITIONS` holds one definition (script:122-124). "One row per (candidate × strategy)" breaks when ≥2 candidates have security_id None (F2).
5. OWNER INPUTS — PASS. `NATIVE_LIVE_ROOT = Path("/var/lib/macro-live")` (script:130). `--live-root` is refused with `--nightly` (script:538-543, test:417-436). `resolve_alias_table()` returns None (script:186-195). The captured reason is the adapter's `IDENTITY_ALIAS_UNRESOLVED` (test:448). `signal_gate_artifact=None` (script:424). Literal fallbacks: `"nbbo_quality": "MISSING"` in the script's own fallback envelope (script:435). This mirrors the same-read default (same_read:295) and is not a guessed fact. The `candidate_generation_id` fallback is `snapshot.generation_id` (script:307), the run's own read (NOTE, feeds F2).
6. KEY + IDEMPOTENCE — FAIL (F2). The key is `(stamp_date, security_id, candidate_generation_id, strategy_definition_id)` (script:441-447). The conflict body EXCLUDES `captured_at`, so the "every rerun is a conflict" attack is closed (script:454-459): `material = {key: value for key, value in row.items() if key != "captured_at"}`. Keep-first applies (script:509-513), and the idempotence test reruns with a different clock and gets exit 0 with a byte-identical file (test:343-360). A conflict raises `CaptureConflictError` before any write (script:500-503, 511-512); main returns 2 (script:671-682). The write is temp + `replace` (script:516-526), canonical JSON with `sort_keys`, lines sorted by key. NOTE F8.
7. RUN DOCUMENT — PARTIAL. All fields are present (script:622-635); target is None in report mode (script:611). Exits are 3/2/0 (script:668-684). SHOULD_FIX F12: `CaptureDayFileError` (script:182, raised script:469/476/481) is not caught in `main`, so a malformed committed day file produces a traceback and exit 1.
8. ZERO AUTHORITY + CONSUMER FENCE — PASS. The fence test (test:454-467) greps `scripts/build_*.py`, the three engine modules and `templates/**` for both `b4_capture` and `capture_prophet_b4_same_read`, so a `from scripts import capture_prophet_b4_same_read` form is caught. The docstring says ZERO AUTHORITY and "first run is capture-only" (script:3, 15-16); it is pinned by test:470-475. NOTE F7.
9. CI — PASS. Manifest line legacy-jobs.yml:27136. Closure lines 27218-27223 (`engine/us_prophet_grades.py`, `engine/us_prophet_w3.py`, `scripts/capture_prophet_b4_same_read.py`; all three are in the real import chain: script:75 → w3:62). The run step at 27289-27290 is adjacent to the B05 step at 27283-27284. The job `washout-turn-organ` (26210) has `scope: exclusive` (26239). YAML parses. The ci_pack closure test passed. NOTE F11.

Deviation (a) `--root` — FINDING F3 (SHOULD_FIX): it is accepted in durable mode as well as report mode.
Deviation (b) per-candidate catch — PASS with NOTE F9. `_CONTRACT_ERRORS` (script:149-154) is a typed owner family (all four are ValueError subclasses: sources:101, prophet_entry_availability:108, prophet_candidate_state:80, us_candidate_episode:91), never bare `Exception`.

## Evaluator key classification (prophet_entry_availability.py:459-489; closed set validated at :499-509)
FACT (input echo or arithmetic over owner inputs): schema, definition, episode_id, candidate_generation_id, candidate_state_projection_id, security_id, identity_epoch, strategy_definition_id, strategy_id, strategy_version, horizon, horizon_role, entry_policy_version, evaluated_at, market_session, zone, current_price, current_price_basis, quote_asof, quote_age_seconds, invalidation, distance_to_zone_pct, risk_to_invalidation_pct, move_since_first_trigger_pct, move_since_anchor_pct, extension_atr, owner_status (owner geometry input), source_receipts.
VERDICT (removed by the lane): state, entry_open, chase_state (derived from the unpersisted chase_above), availability_id (digest over the state-bearing material).
VERDICT TRACE (NOT removed — F1): blockers, reasons. Both are produced by the state-decision branch (:353-449).

## Findings
- F1 BLOCKING — the verdict is persisted in encoded form through `facts.blockers`/`facts.reasons`.
  - `reasons == ["CURRENT_PRICE_INSIDE_OWNER_ZONE","FRESH_QUOTE","LIQUIDITY_FILLABLE","OWNER_CONFLUENCE_PASSED","RISK_WITHIN_LANE_CEILING"]` is emitted iff state == ENTRY_OPEN (prophet_entry_availability.py:440-449).
  - `PAST_OWNER_CHASE_BOUNDARY` ⇔ RAN_DONT_CHASE (:408); `OWNER_STATUS_APPROACHING` ⇒ APPROACHING_ENTRY (:432); `EPISODE_NOT_ACTIVE:*` ⇒ INVALIDATED (:357).
  - `_facts_without_verdict` (script:310-314) keeps both lists. Demonstrated: `_assert_row_is_lawful` ACCEPTS a row whose `facts.reasons` is the ENTRY_OPEN list, and one whose `facts.blockers` is `["PAST_OWNER_CHASE_BOUNDARY"]`. D11 rule 3 (ENTRY_OPEN never persisted / never created) is violated in substance as soon as any owner makes a row reach ENTRY_OPEN.
  - The docstring claim that the verdict is "re-derivable from those facts plus the pinned strategy definition" (script:36-38) is also unsupported. The deterministic gates, quote freshness, chase_above and lifecycle are absent from the output row, so the only re-derivation path from the persisted facts is the blockers/reasons trace itself.
  - Test gap: `test_evaluated_row_persists_facts_only_and_round_trips_the_verdict` (test:307-337) reaches only availability verdict UNAVAILABLE_DATA (measured: blockers = six `*_UNKNOWN`, reasons = [], fresh state UNAVAILABLE_DATA). Its "round trip" re-evaluates the live world rather than deriving the verdict from persisted facts.
  - Repair direction (seat decides): strip or neutralise `blockers`/`reasons` (or persist only the gate/freshness inputs), and add a test that drives a synthetic ENTRY_OPEN availability row through `_capture_row`.
- F2 BLOCKING — the capture key is not unique when security_id is None.
  - Mechanism: when B3 refuses (the same-read module returns `episode_id=None, binding=None`, same_read:308-310), or when the script's own fallback envelope fires (script:426-438 discards the bound episode/binding), `security_id` is None and `candidate_generation_id` falls back to the snapshot id. Every such candidate then shares the key `(stamp, None, gen, psd)`. The bodies differ (ticker, source id), so `_merge_and_write` raises `CaptureConflictError`.
  - Reproduced against the real owner chain with the packet's own fixtures (2 episode-bound tickers plus 2 unbound tickers ZZZ1/ZZZ2). Report mode: `rows 4, counts_by_reason {"CandidateStateContractError: candidate source key has no OPENED/OBSERVED relation in the native B1 ledger": 2, "IDENTITY_ALIAS_UNRESOLVED": 2}`. `--nightly`: exit 2, `conflict ["2026-09-17","None","peg:0f95e6a2…","psd:b89769f1…"]`, and no capture dir was created.
  - Impact: the typed-unavailable census, which is the stated deliverable (script:16-17), is lost for the whole night, and the exit 2 falsely reports a conflict. It recurs every night that has ≥2 unbound candidates (e.g., capture ordered before B1 intake).
  - Repair direction: key on `candidate_source_event_id` when security_id is None (a seat ruling on the F22 key), or refuse with a typed reason. Add a ≥2-unbound-candidate test.
- F3 SHOULD_FIX — `--root` is accepted with `--nightly` (script:552, 656-659). This lets a durable append be redirected to any directory tree, and the durable tests themselves exercise `--nightly --root` (test:127). Restrict `--root` to report mode (or to tests through `run(root=...)`), as `--live-root` already is.
- F4 SHOULD_FIX — `--dry-run --nightly` refuses unless `COLLECT_LANE=nightly` (script:544-550 run before the dry-run branch at 610-614). No test covers `--dry-run` at all. Either make the dry-run preview lane-independent or pin the current behaviour with a test.
- F12 SHOULD_FIX — `CaptureDayFileError` escapes `main` as a traceback with exit 1. Spec 7 requires exits 0/2/3 and no traceback for a typed refusal. There is no test with a malformed committed day file.
- F5 NOTE — `CaptureConflictError.existing_digest/incoming_digest` hold full row bodies, not digests (script:174-179, 502, 512), and the conflict document prints them (script:676-677).
- F6 NOTE — the owner reader re-loads the HEAD snapshot per candidate as an attestation (sources:884). Total loads are 1+N. The test comment "never a second read per candidate" (test:254-256) counts only the capture module's own read.
- F7 NOTE — the fence test uses cwd-relative paths and `continue`s on a non-file (test:455-464), so it becomes vacuous when run outside the repo root. There is no positive control. A dynamic import string (`importlib.import_module("scripts."+name)`) would escape the needle.
- F8 NOTE — the temp name `.{name}.tmp` is fixed and there is no fsync before `replace` (script:517-526). This is acceptable for a single nightly writer.
- F9 NOTE — the script widens the same-read catch family with `EpisodeContractError` (script:149-154 vs same_read:85-89). A store-level corruption raised mid-chain would become a per-row reason instead of refusing the run. It is still a typed family, not a bare catch.
- F11 NOTE — `washout-turn-organ` carries `if: ${{ false }}` (legacy-jobs.yml:26218); this is pre-existing, and the job runs through ci_pack routing. This review did not observe a CI run.

## Evidence
- `git diff --stat 562fc7dd..b2efcfa`: `.github/ci/legacy-jobs.yml | 13 +`, `scripts/capture_prophet_b4_same_read.py | 688 +`, `tests/test_capture_prophet_b4_same_read.py | 475 +`; 3 files, 1176 insertions. No other hunk.
- pytest (TREE): `tests/test_capture_prophet_b4_same_read.py tests/test_prophet_b4_same_read.py tests/test_us_prophet_w3.py` → `100 passed in 6.40s`.
- ci_pack closure: `1 passed, 203 deselected in 157.30s`. YAML: `yaml ok`.
- Lane gate (script:544-550): `if nightly and not ledger_lane.nightly_advance_enabled(): raise TypedRefusal("NIGHTLY_LANE_NOT_ARMED", ...)`. It precedes the root check (552) and the first read `resolve_board_as_of` (565).
- `_now` call site: script:581 `captured_at = _now_iso(_now())`. This is the only call; the definition is at script:198-200.
- Receipt derivations, side by side:
  - builder scripts/build_stock_library.py:1719-1720:
    - `source_key = "candidate:{stamp_date}:{ticker}:{board_definition}".format(**native_row)`
    - `source_receipt = "sha256:" + sha256(canonical_json(native_row).encode()).hexdigest()`
  - script:243-248:
    - `source_event_id = "candidate:{stamp_date}:{ticker}:{board_definition}".format(**native_row)`
    - `"sha256:" + sha256(canonical_json(native_row).encode("utf-8")).hexdigest()`
  - `.encode()` defaults to utf-8, so the bytes are identical. Both use rows from `read_today_candidate_source_rows(root)`.
- CI lines: 27136 `- "tests/test_capture_prophet_b4_same_read.py"`; 27221-27223 closure; 27289-27290 `name: Prophet B4 nightly capture ...` / `run: python -m pytest tests/test_capture_prophet_b4_same_read.py -q`; B05 step at 27283-27284.

## Gaps
- No CI run observed; no production host run (/var/lib/macro-live is absent here).
- F1 was demonstrated at the guard level plus static evaluator branches. No end-to-end ENTRY_OPEN world was built, because no owner publishes PASS gates at BASE.

## Deviations
- Ran reproduction snippets via stdin (python3 -) inside TempDirectory against the TREE; no files written except this report and pytest/__pycache__ artefacts under the TREE export.

## Addendum — closing checks
- Spec 4 `STRATEGY_DEFINITIONS`: engine/prophet_strategy_definition.py exposes exactly one builder, `build_early_leadership_sector_rotation_definition` (:189), and has no registry or list. The script's one-element list (script:122-124) equals the registered set at HEAD. VERIFIED.
- Spec 8 fence: the full-tree grep for `b4_capture|capture_prophet_b4_same_read` across engine/, scripts/, lib/ and templates/ matches only the script itself, so no consumer exists. VERIFIED.
- Spec 5 literal fallbacks: only `"MISSING"` (script:435). `or []` appears at script:390-391; these normalise the envelope's own lists and invent no fact. argparse `default=None` only. VERIFIED.

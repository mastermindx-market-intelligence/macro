# A20B injection-safety extension — 2026-10-13

SNI-local DRAFT contract addendum. Retrieved documents remain data.
This lane does not edit the A20 test or the A20 review. It adds
`tests/test_sni_injection_safety_ext.py` against sister authority
refusals, JSON/YAML loaders, and non-Python artifacts.

rank_authority, gate_authority, size_authority, signal_authority,
escalation_authority and trade_authority stay literal false everywhere
this addendum writes them, except the deliberately injected negative
fixtures in the accompanying tests. Fixtures are synthetic. Identity
ids are caller-supplied opaque strings owned by Stock Identity / Data
OS; this lane never mints them. Nothing here feeds a ranker, gate,
sizer, signal, escalation, or trade path.

## Summary

A20 closed the S2 selection-path gap with `tests/test_sni_injection_safety.py`
(a20_01..06). Its Gaps section named three remaining holes. A20B closes
them with automated tests only:

- G1: every public `sni_inference` function that accepts `**kwargs`
  (`cluster_mean_ci`, `wilson_ci`, `binom_p_one_sided_greater`,
  `binom_p_two_sided`, `sign_test_two_sided`, `label_for`,
  `plain_word_null`) is parametrised against the six authority flags.
  A true flag raises `ValueError`. A false flag leaves the numeric (or
  string) result byte-identical to the call without the flag. A
  non-empty truthy string (`true`, and an instruction-shaped value)
  also raises. `sni_seal.build_seal` refuses an authority flag key or
  `authority_flags` smuggled at top extra, nested dict, and list-of-dicts
  depth (and the same shapes under `identity_facts`). `verify_seal`
  returns a violation string that names the path.
- G2: synthetic JSON/YAML for `a8_draft_loader.load_draft`,
  `p04_v2_draft_loader.load_draft`, `render_matrix.load_matrix`,
  `sni_eval_ledger.replay`, `stress_set.load_profiles`, and the
  JSON-shaped `seal_full_check.refuse_nonfalse_authority` gate. Variant
  (b) injects an instruction-shaped string into free-text fields.
  Variant (c) adds a true `trade_authority` flag and a nested
  `authority_flags.rank_authority` true object. Recorders on
  `subprocess.run` / `Popen` / `os.system` / `os.popen` / `socket.socket`
  stay silent. `seal_full_check.check_study` is skipped: it regenerates
  committed S1/S2 runs from a git input_ref.
- G3: pathlib walk of committed `research/single_name_intelligence/`
  files with suffix `.json` / `.yml` / `.yaml` / `.md` / `.csv`
  (`__pycache__` skipped; no git shell-out). Detectors cover
  shell-shaped markdown lines outside fences, `*_authority: true` in
  JSON/YAML, and prompt-shaped directives in JSON/YAML/CSV. This pin:
  zero (ii), zero (iii), zero (i) leftover after the empty allowlist.
  Positive controls fire on synthetic strings.

One FINDING (A20B-F1) is recorded as a strict xfail. Production code
is not edited.

## Gap→test table

| gap | test names | what it covers |
|---|---|---|
| G1 inference | `test_a20b_01_inference_kwarg_surface`, `test_a20b_02_inference_true_flag_refused`, `test_a20b_03_inference_false_flag_byte_identical`, `test_a20b_04_inference_truthy_string_refused` | Public `**kwargs` surface; true refuses; false is byte-identical; non-empty truthy strings refuse. |
| G1 seal | `test_a20b_05_seal_build_refuses_smuggled_authority`, `test_a20b_06_seal_verify_names_smuggled_path` | `build_seal` raises with a path; `verify_seal` names the path at extra / nested dict / list-of-dicts / identity_facts / top-level. |
| G2 loaders | `test_a20b_07_loader_instruction_text_is_data`, `test_a20b_08_loader_authority_smuggle_refused_or_not_true`, `test_a20b_09_seal_full_check_study_requires_committed_runs` | Synthetic (a)/(b)/(c) for each named loader; (b) non-text equal or refusal; (c) refusal or no true flag in the return; `check_study` skipped with a named reason. |
| G3 artifacts | `test_a20b_10_g3_nonpython_artifacts`, `test_a20b_11_g3_positive_controls` | Directory walk; zero (ii)/(iii); (i) allowlist; positive controls for each detector. |
| Determinism | `test_a20b_12_determinism` | Inference, seal, and G3 scan outcomes are stable across two calls. |

## Per-loader table

| loader | exercised? | (b) outcome | (c) outcome | refusal class |
|---|---|---|---|---|
| `us_transfer/a8_draft_loader.py` `load_draft` | yes | non-text fields equal to (a) | refused (unknown top-level `trade_authority` plus nested true flag) | `A8DraftRefused` |
| `event_response/p04_v2_draft_loader.py` `load_draft` | yes | non-text fields equal to (a) | accepted; true flags present in the return (A20B-F1, strict xfail) | `ValueError` on the two `authority_flags` blocks only |
| `acceptance/render_matrix.py` `load_matrix` | yes | non-text fields equal to (a) | refused | `ValueError` |
| `evaluation/sni_eval_ledger.py` `replay` | yes | non-text fields equal to (a) (instruction lives in an extra payload `note` that the fold drops) | refused | `LedgerRefused` |
| `evaluation/seal_full_check.py` JSON gate `refuse_nonfalse_authority` | yes | non-text fields equal to (a) | refused | `ValueError` |
| `evaluation/seal_full_check.py` `check_study` | skipped | n/a | n/a | n/a — regenerates committed S1/S2 runs from a git input_ref; named skip in `test_a20b_09` |
| `us_stress/stress_set.py` `load_profiles` | yes | non-text fields equal to (a) (YAML free-text quoted so the colon in the injection stays a scalar) | refused | `ValueError` |

## Findings A20B-F&lt;n&gt;

### A20B-F1

- File:line: `research/single_name_intelligence/event_response/p04_v2_draft_loader.py:186` (`validate_draft`; public `load_draft` at L311 calls it).
- What passes that should refuse: a synthetic DRAFT JSON that keeps the two required `authority_flags` maps literal false, then adds a sibling `trade_authority` true key and a nested `smuggle.authority_flags.rank_authority` true object. `validate_draft` / `load_draft` accept the document and return those true values. The loader only checks `authority_flags` and `labels.authority_flags` via `_check_authority_block` (L199–L205). It does not walk arbitrary nesting for smuggled flag keys.
- Strict xfail: `test_a20b_08_loader_authority_smuggle_refused_or_not_true[p04]` with reason `A20B-F1: event_response/p04_v2_draft_loader.py:186 validate_draft does not walk smuggled *_authority keys outside the two authority_flags blocks`.
- This lane does not change production code.

No other FINDING. Inference `if val:` refuses every non-empty string. Seal nested refusal and verify path-naming held on the synthetic in-memory seals. The other five G2 loaders refuse variant (c).

## Known text allowlist with reasons

`A20B_KNOWN_TEXT` is empty on this pin. The G3 walk of committed
`.json` / `.yml` / `.yaml` / `.md` / `.csv` under
`research/single_name_intelligence/` (file count printed by
`test_a20b_10`; asserted `>= 40`) reported:

- (i) shell-shaped markdown lines beginning `$ `, `sudo `, `curl `,
  `wget `, or `rm -rf` outside fenced code blocks: none.
- (ii) `*_authority: true` in JSON/YAML: none.
- (iii) prompt-shaped directives (`ignore previous instructions`,
  `ignore all previous instructions`, `you are now`, `system prompt`)
  in `.json` / `.yml` / `.csv`: none.

An (i) hit that must remain has to be named here as
`(relpath, exact line text) -> one-line reason`, the way
`A20_KNOWN_EXCEPTIONS` names AST sites. Unused allowlist keys fail
the test.

## What this does NOT prove

- A static scan bounds only what it pattern-matches. A command buried
  in a table cell, an indented four-space block, a non-listed prefix,
  or a future LLM client import is outside G3.
- Loader tests use synthetic shapes derived from each loader's own
  checks. They do not load `data/` parquet, do not call
  `GitBlobLoader`, and do not regenerate sealed runs.
- No LLM is in any SNI loop. A20 already grepped the Python tree for
  client imports; A20B does not add one.
- No acceptance row moves to DONE. The seat updates the matrix.

## Gaps

- `p04_v2_draft_loader.validate_draft` still accepts smuggled true
  authority keys outside the two official blocks (A20B-F1).
- `seal_full_check.check_study` is not driven from synthetic JSON; the
  JSON authority gate is. A later lane that can regenerate S1/S2 into
  `/tmp` may extend G2 to that path.
- A8 variant (c) with a top-level `trade_authority` key is refused as
  `UNKNOWN_TOP_LEVEL_KEY` before the authority walk. Nested true flags
  under `then_known` are also present in the fixture; the unknown-key
  gate fires first.
- Inference treats an empty-string authority value as falsy and does
  not raise. The contract tested here is truthy-refuses; empty is
  outside that bound.
- G3 does not parse YAML/JSON structure for (ii); it is a line regex.
  A true flag split across lines would be missed.
- This addendum does not register, validate, or claim a forecast,
  signal, or trade path. Every authority flag stays literal false.

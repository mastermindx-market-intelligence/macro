# Independent v4 interpreter-witness review — 18 October 2026

Reviewer: `/root/forward_activation_review`. Candidate author: `/root/release_repair_design`. Scope: only the v3-to-v4 change in `test_python_fixture_launcher_preserves_spaced_interpreter_and_arguments`, before root's focused native validation.

**Disposition: accept this bounded regression correction for native validation.** It verifies that the selected interpreter wrapper actually executed, preserves exact alias/arguments, and checks the underlying runtime without assuming that macOS reports an external interpreter symlink's literal spelling. No test execution or passing v4 result is claimed by this review.

## Exact source and preserved scope

| Cloud candidate | Bytes | SHA256 |
|---|---:|---|
| `release_review/ci_contract_candidate_v3/tests/test_deploy_provenance.py` | 49,407 | `4f91f32c0b81d0038fdcbbe51f1d36d1b975096abd1b47c887ce0ea93f6e701a` |
| `release_review/ci_contract_candidate_v4/tests/test_deploy_provenance.py` | 50,039 | `80ebb89997b575aed4b8986fdec11f27a1987c0ec5cb3e3d80ad8041c9ae7d10` |

Static AST comparison confirms exactly one changed function, at v4 lines 101–143. There are no added/removed functions. The generator, complete transport function, all other helpers, all 40 pre-existing test-function ASTs and module-level non-function ASTs are unchanged. The existing tests' 188 assertions therefore remain unchanged; this correction changes only the newly added regression's setup, observation and expected-runtime check.

The [v3 review](HELPER_V3_INTERPRETER_PATH_REVIEW_2026-10-18.md) remains dated static evidence. Root subsequently reported a native selection with 113 passed and one failed as observed at 10:08:18Z: all 59 existing owner cases and 54 companion cases passed, while the new regression's literal external-symlink `sys.executable` expectation failed. Those are attributed root observations, not independently executed or raw-log-verified here. They are not relabeled as a v3 pass or a v4 result.

## Why the corrected regression discriminates the intended failure

At lines 106–111, the test records the original Python executable, its normalized real path and the parent's `prefix`/`base_prefix` before monkeypatching. It then creates an executable shell wrapper beneath a directory containing both a space and an apostrophe. At lines 115–119, that wrapper exports `FAKE_INTERPRETER_EXECUTION_WITNESS` from quoted `"$0"` and uses `exec` with the separately shell-quoted original Python path and quoted `"$@"`.

The generator receives this selected wrapper as `sys.executable`. Its existing quoting/argv restoration is unchanged. The child's environment explicitly removes any inherited witness at lines 134–135. The final JSON equality at lines 140–143 requires the exact selected wrapper path as witness, the exact invoked alias and argument list, the normalized original executable and both original runtime-prefix values.

| Counterfactual implementation | Why this regression rejects it |
|---|---|
| Generator bypasses the selected wrapper and invokes the original/base Python directly | The child receives no inherited witness and the wrapper does not run; the required witness is absent even if Python and argv otherwise match. |
| Generator selects Python through PATH | PATH points only to the empty fixture directory; fallback lookup cannot supply the chosen wrapper or Python. |
| Unquoted interpreter or sibling path splits at spaces/apostrophes | The child cannot execute the intended command or produce the required witness/runtime/argv equality. |
| Launcher loses the symlink alias or changes empty, quoted, spaced, shell-looking or option-looking arguments | The complete alias/argument vector comparison fails. The original argument list remains unchanged. |
| A different virtual environment resolves to the same underlying executable | Normalized executable equality alone might not distinguish it, but the required `prefix` and `base_prefix` bindings also remain. |

Normalizing the underlying Python path does not erase selected-wrapper identity: the separate witness carries that identity. In this reviewed code, only the chosen wrapper sets the witness; the generator does not manufacture it, and the parent removes it from the child environment. This is a stronger direct check of wrapper execution than comparing Python's platform-dependent reporting of an external symlink.

## Execution boundary

This review used only local source reads, text diff and standard-library AST comparison. It did not execute the generator, new regression, fixture, helper or tests; import first-party source; or use native/network tools. No source file was changed; only this new review was written.

The focused native result must bind the exact v4 bytes. Broader suite, CI, source-landing and deployment outcomes remain with the existing owner and require their own observations. The earlier v3 native failure remains preserved evidence. The helper and shared transport/root/SHA controls have not changed in this successor.

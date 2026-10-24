# Independent v3 fixture interpreter-path review — 18 October 2026

Reviewer: `/root/forward_activation_review`. Candidate author: `/root/release_repair_design`. Scope: the v2-to-v3 delta in the existing owner test `tests/test_deploy_provenance.py`, before root's native application/validation.

**Disposition: no blocking semantic defect found in this bounded delta; qualified for the existing owner's native validation.** The change preserves the exact chosen Python interpreter when its path contains spaces, while retaining the invoked fixture alias and every argument. This is static source qualification, not a passing test result, source landing or deployment acceptance.

## Exact source identities

| Cloud source copy | Bytes | SHA256 |
|---|---:|---|
| `release_review/ci_contract_candidate_v2/tests/test_deploy_provenance.py` | 47,847 | `0da8a0d094b3b6f20bdedbdc427481a6425d709736621e7c5554a125cf78cc48` |
| `release_review/ci_contract_candidate_v3/tests/test_deploy_provenance.py` | 49,407 | `4f91f32c0b81d0038fdcbbe51f1d36d1b975096abd1b47c887ce0ea93f6e701a` |

I read the diff, new launcher/regression and complete shared transport body, and compared source ASTs using the standard library. I did not execute the generator, fixture, helper or tests; import first-party source; use native/network tools; or change candidate source. Only this review file was written.

## Launcher and quoting

The new `_write_python_executable` at v3 lines 87–98 creates a sibling Python source file and an executable shell launcher. The launcher has an absolute `/bin/sh` shebang and uses shell `exec` with separately `shlex.quote`-quoted `sys.executable` and sibling-program paths. It appends quoted `"$0"` and `"$@"`. Consequently path spaces/apostrophes are handled as argument content, and argument strings are forwarded without shell re-evaluation, word splitting or glob expansion. Python selection does not fall back to PATH.

The child initially receives the sibling program path, invoked shell alias and original arguments. Its leading `sys.argv = sys.argv[1:]` removes only the sibling-program slot, restoring the invocation shape expected by the existing body: alias at `argv[0]`, unchanged original arguments thereafter. The shell uses `exec`, so it does not introduce a lingering shell parent between the helper and fixture Python process. This preserves the existing parent-directed signal-control shape rather than adding another shell process to signal.

The fixture launcher changes from `bin/transport.py` to `bin/transport`, whose sibling program is `bin/transport.py`. All ten existing command aliases remain symlinks to the launcher at v3 lines 354–355. The body still selects its branch using `Path(sys.argv[0]).name` at line 171. Thus `ssh`, `rsync`, `python3` and the other admitted aliases reach their existing branches; the sibling filename does not replace the invoked alias for dispatch. The body does not use `__file__` for that dispatch.

## Preserved transport and authority controls

The complete raw shared transport body is byte-identical between v2 and v3: **10,814 bytes**, SHA256 `2436aa576015958c9d5ae8c167b95ef14804eafa41e86d2a163b11dee65fd190`. Its preserved relevant controls include:

| v3 lines | Preserved behavior |
|---|---|
| 184–194 | Only the declared fake SSH argument shape/host is accepted; its command is handled locally through the existing fixture shell path. No real SSH delegation is introduced. |
| 195–219 | The existing fixture path checks and fake-host handling precede the admitted local rsync call. The real rsync peer directory is prepended only for that already-confined subprocess. |
| 284–292 | The fake Python alias accepts only the forward-evaluation CLI shape; it requires a nonempty absolute release-state root, resolves it strictly and compares it to the admitted fixture live-data root. |
| 295–306 | `init` and `finalize` require exactly one supplied deployment SHA equal to the expected target; missing, duplicate or wrong values remain rejected. |
| 308–336 | Marker/status/failure simulation remains the same after those checks. No application or forward module import is added. |

The wrapper restores the original argv layout before these conditions run. It does not insert a script path or extra argument where the CLI parser expects `-m`, the command or a SHA option. This is preservation of the existing bounded fixture controls, not a new claim that the fixture safely accepts arbitrary hostile shell commands or paths.

## Assertion preservation and discriminating regression

All **40 existing test-function ASTs** are unchanged, including decorators and their **188 assertion nodes**. All other pre-existing helper-function ASTs except the deliberately changed `_fake_transport` are unchanged. Module-level non-function ASTs are unchanged. The transport-body identity above independently excludes a hidden change to its root/SHA, service, rollback or observer logic.

The only new definitions are `_write_python_executable` and `test_python_fixture_launcher_preserves_spaced_interpreter_and_arguments` at v3 lines 101–125. The new regression:

- Creates a Python symlink beneath a directory containing both a space and an apostrophe, then makes that exact path the generator's chosen interpreter.
- Places the launcher/sibling and invoked alias at paths containing spaces.
- Supplies an empty argument, a multiword argument, quotes, literal shell syntax/glob characters and an option-looking argument.
- Uses an empty PATH directory, then asserts successful execution and exact JSON equality for both the interpreter identity and full alias/argument vector.

This discriminates the failed direct-Python-shebang form and would also reject a launcher that loses the alias, expands argument contents or selects Python through PATH. It does not weaken or replace any prior control. The new regression checks generic symlink/argv behavior; the existing owner suite supplies the subsequent runtime coverage of the actual SSH/rsync/Python aliases.

## Remaining validation boundary

No v3 test was run by this reviewer. The previously reported native 59-case result belongs to v2, not these bytes. The new unparameterized regression adds one test to the unchanged existing test definitions; actual native collection and completion must be reported by root for the exact v3 hash. Interpreter symlink behavior, platform execution and the complete owning suite remain native observations to obtain, not facts established by AST comparison.

The deployment helper and companion owner files are outside this v3 delta and were not reread or modified here. Existing source-custody, CI, publication and production boundaries remain unchanged. This review supplies no provider/model execution, waiver, whole-CI acceptance or deployment authorization.

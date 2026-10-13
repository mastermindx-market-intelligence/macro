# Existing owner parser and MU bootstrap: independent source review

## Verdict

**PASS_CORRECTED_PRE_EXECUTION_SOURCE_REVIEW.** Reusing only the existing host-owner parser is compatible with the narrow MU capture scope. No concrete ownership conflict or remaining required correction was found in the corrected wrapper.

The one reporting defect was corrected before execution. The original field claimed that the file was read once after a parser that can return an empty mapping on an OSError. The corrected field records a parser invocation. This does not assert successful reading or the absence of credential keys.

This review did not import the helper, call the parser, read credentials, invoke the wrapper/child, contact the native host or make a provider request. Actual execution remains a separate principal action.

## Exact source and author correction

| Subject | Bytes | SHA-256 |
|---|---:|---|
| Existing host-runner helper | 67,554 | 20335fb0f694ca904e130a2b9016f379161c10946adb2e15dbfc5bdff3addd69 |
| Original unexecuted wrapper | 28,311 | b6ab3f96a68834b8616b2c98545cfccaa379c0db5f760c447d941a9ca8d02509 |
| Corrected wrapper | 28,296 | bd88bb68b15894a85f71fa7ac75f5a4a7fcce43518804f9b27e28f5fdc14b2f3 |
| Action 002 | 18,367 | de5f94b084726522352b44966a928bd2c410f9260901c63833603f2d51817ac1 |

The helper snapshot contains 63,377 UTF-8 characters and 1,359 lines. Independently computing its Git blob identity yields **a5df3ba140cb9fa9827642d3f90f1ed2e69ce057**, matching the pinned [existing source at 7af7a978](https://github.com/mastermindx-market-intelligence/macro/blob/7af7a9785d74c1b420b23de3be0eac6946cc2200/scripts/close_pass_host_runner.py).

I parsed the complete module and read every top-level executable statement, class declaration and function/default/decorator declaration, the full load_env_file body, and adjacent ownership/environment-caller context. I did not turn the other host-runner/publisher function bodies into a new execution audit.

The original wrapper is preserved as run_owner_bootstrap_002_unexecuted_pre_review.py.txt. The corrected wrapper is **exactly** that file with owner_environment_file_read_once_by_existing_parser replaced once by owner_environment_parser_called_once. No other byte changes occurred.

The action differs from the already reviewed first action only by the fresh RUNROOT identifier 001→002. Inverting that replacement reproduces the first action bytes exactly. This preserves its actual source call, clocks, status handling, immutable intake, pinned read, same-artifact repeat and authority boundaries.

## Ownership follows the incumbent source

The helper's lines 83–86 explicitly describe PRIMARY as the owner of Git objects, the remote and the .env file. They also distinguish this ownership from executable lane code and prohibit touching the primary's Git state. Existing build_env at lines 614–642 obtains its environment through load_env_file(primary / ".env"). Reusing that parser with the same owner path is therefore grounded in existing source, rather than a newly invented credential source.

The principal's metadata-only probe, PID 46863 / exit 0, reports that the actual Git common directory and first registered worktree bind the primary to /Users/chriswong/Documents/Cluade/Macro Dashboard. It reports a regular, nonsymlink, 1,225-byte owner file with mode 0600 and uid/euid 501. The reported probe receipt is 3,279 bytes, SHA-256 5c218ba77b23446d41490adf13e99b5da2b3661f0cff06789d3377049b7fc31b.

Those probe facts are principal-attributed; this reviewer did not repeat the probe or read the file. The reviewed wrapper revalidates the actual Git relationship and exact owner-file metadata before use and checks metadata again after parsing and at postflight. It never searches for alternative credential files or changes the primary's Git state.

This does not assert that the owner file contains a usable Massive key, that the scheduled production owner is currently running, or that any source has been promoted. It provides the specific incumbent owner path for the authorized attempt.

## Actual import behavior

The helper has standard-library imports only at module top level. Non-main loading constructs paths/defaults and a New York ZoneInfo object, inserts the helper's repository root into sys.path, constructs a small NamedTuple class, and defines functions. Callable defaults are references; they do not launch their functions.

No environment-file read, Git command, subprocess, shell execution, lock, checkout/reset, repository-module probe or publishing action occurs at top level. The main call is protected by __name__ == "__main__". The wrapper supplies the non-main run name economic_network_owner_env_bootstrap and selects only the returned load_env_file function.

The import is not completely effect-free: sys.path changes and path/timezone metadata may be read. Those effects are distinct from credential parsing or production execution. They occur in the outer wrapper; the source action runs in a new isolated Python -I -B subprocess.

## Parser contract and its limits

The full parser at lines 593–611 reads the given Path as UTF-8 and returns a dictionary. It does not call a shell, interpolate variables, evaluate backslashes or commands, mutate os.environ, or log values.

Its exact conventions are:

- Strip line whitespace; skip blank lines, whole-line comments and lines without an equals sign.
- Remove an optional literal export prefix.
- Split at the first equals sign and strip the key.
- Skip empty keys; trim the value's surrounding whitespace, then double-quote characters, then single-quote characters.
- Use the last assignment for a repeated key.

This is a permissive existing parser, not a complete shell or strict dotenv implementation. Inline comments remain literal; balanced quotes are not checked; multiline and escape semantics are not added. The wrapper must preserve the returned values, rather than silently reinterpret them. It does so.

The parser returns an empty mapping on OSError. Therefore an empty result alone does not distinguish a failed read from no matching/nonempty keys. UTF-8 decoding errors are not caught by that parser, and the wrapper suppresses their unexpected payloads publicly.

The parser also has no internal byte cap or descriptor-based hostile-race abstraction. The reviewed use is of one prechecked, small, trusted owner file, with before/after metadata checks. This review does not claim those checks defeat arbitrary malicious filesystem replacement or supply a new generic credential-reading framework.

## Wrapper scope and value handling

The wrapper verifies exact helper and action bytes, loads the helper under the non-main name, and invokes only load_env_file. It does not use build_env, run, main, shell source, lane preparation or publishing functions.

Both Massive aliases are removed from the inherited child environment. Only nonempty parsed MASSIVE_API_KEY and POLYGON_API_KEY strings are then copied unchanged. Other parsed owner-file keys are not forwarded. The existing ambient environment remains inherited; the two-name restriction concerns additions from the owner file, not all pre-existing process variables.

The parsed mapping is neither logged nor persisted. Its temporary references are dropped before the child call. Only the authorized child process environment receives the selected values. The wrapper publishes key names and metadata, not values.

Child stdout and stderr go to exclusive private files. The public outer receipt summarizes the child's actual PID, exit, source status, counts, result-file identity and source/read/repeat outcome. The unchanged child retains provider rows privately and keeps its existing public metadata projection.

The first attempt's public identity and absent source store are checked again. Its missing-credentials refusal is preserved as a real historical attempt; no old result is edited or reclassified.

## Finding R1 and resolution

**P2 — read receipt semantics.** The original field owner_environment_file_read_once_by_existing_parser=True exceeded what the parser's return could establish, because OSError is swallowed into an empty mapping.

The sole accepted correction is owner_environment_parser_called_once=True. It reports the normal parser invocation while leaving read success and key availability to actual evidence. The source parser and native action remain unchanged. No extra credential read, provider call or test was necessary to make this correction.

The one-field diff was independently verified against the preserved original wrapper. There are no remaining required corrections in this bounded source/bootstrap review.

## Execution limits

This is pre-execution source evidence. Active credentials, provider response, actual F, source storage, pinned read and repeat require the actual result. If the new child again refuses, the refusal must remain visible. If a started child has no terminal exit or a later export fails, reconcile its actual PID and root effects before retrying; generic failure is not proof of no effect.

The accepted Massive grant is unchanged. K-vintage, D-close price, canonical issuer/class/share identity, real WP02 selection, Graph1 and predictive admission remain withheld. Loading a credential through an incumbent owner parser does not create any of those authorities.

All reviewer native/provider calls, credential reads, helper imports, parser calls, wrapper/child execution and Git/native writes are zero. The source/delta inspection commands all exited zero; exact local receipt chunks are listed in RECEIPT.json.

**STOP — corrected source/bootstrap review complete.**


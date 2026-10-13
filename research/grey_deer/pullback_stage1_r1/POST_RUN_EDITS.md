# Stage-1 runner edits after the frozen run (2026-10-12)

The payload in this directory records `script_blob_sha` `9eeba12d9f668dbe8940f4f25109a3da1cbe75be`.
That blob is the runner that produced this output. It is the file at commit `80d8a9fc76d2` on
PR #8938 (`refs/pull/8938/head` keeps it after the squash merge).

One edit landed afterwards, before merge:

| Edit | Why | Effect on computation |
|---|---|---|
| The module-load repo pin became unconditional: `if str(ROOT) not in sys.path:` was removed, `sys.path.insert(0, str(ROOT))` stays | `tests/test_check_script_import_pinning.py` accepts only an unconditional `__file__`-derived pin as a strong pin | None. It changes which directory wins import resolution, not any function, constant, seed or draw count |

So a rerun at main records a different `script_blob_sha`, while every other field is unchanged. Do not
read that difference as a code change in the estimator.

To check: `git diff 9eeba12d9f668dbe8940f4f25109a3da1cbe75be <main blob> --` shows the pin hunk
and nothing else.

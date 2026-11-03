# Static release-scope catalogue — bounded source review, 18 October 2026

**Recommendation: root may use this source as a qualified read-only changed-path and positive-import catalogue for the specified commits, with a verified repository-root argument and a new caller-owned output outside that repository. It is not a conservative complete import closure.** Two source findings below limit the graph's accuracy and the generality of its output-path guard. Neither an unreached path nor an empty dynamic-site list establishes inertness. This review grants no release permission and does not resolve the held source candidate's CI or companion custody.

## Identity and review scope

Reviewed only `release_review/candidate_scope_static.py`: **322 lines, 16,836 bytes**, SHA256 **`1ccb858a4f41ee62e909cc651c64d4ecc5aa525051432b45883854f6d0216c17`**. Intended arguments identify candidate **`797c760f3e18eb6993579f56986103de9d9fdcb4`**, predecessor **`732cf7be88e7159b4995a8885fbd381cd1484e3e`**, and root `app.main`. These are caller bindings; the generic script does not hardcode them.

The review consisted of source reading, source-hash verification and static reasoning. The catalogue was not run or imported. No Git command, first-party module, candidate tree, live system, price row or application data was accessed by this reviewer. The examples below are source-level counterexamples, not executed fixture results. Only this report was written; the reviewed script was not edited.

## Findings

### F1 — Recognized loader aliases can silently lose a first-party edge

**Severity: moderate accuracy defect. Location: `scan`, lines 210–221 and 238–249; `dynamic_call`, lines 195–205.** `loader_names` holds one loader kind per identifier. Import aliases are collected across every lexical scope, so a later visited nested alias overwrites an outer alias even when the nested function is never called.

Consider an empty tracked `pkg/__init__.py` and a tracked `pkg/child.py`, with this source at the scanned entry:

```python
from builtins import __import__ as load

def unused():
    from importlib import import_module as load

load("pkg", fromlist=["child"])
```

The actual outer loader is `__import__`; its fromlist can load `pkg.child`. The catalogue's first pass overwrites `loader_names["load"]` with `"import_module"`. Its second pass reaches `pkg` but skips fromlist handling, which runs only for `"__import__"`. If no other edge names the child, `pkg/child.py` remains unreached. The call is reported as a resolved literal import, with no ambiguity or unresolved-dynamic record for the lost fromlist.

The existing limitation about missing scope/rebinding analysis is useful, but the single-value table can **under-approximate even an otherwise recognized literal import form**. Consequently, reported reached paths are useful positive evidence; remaining paths and absence of unresolved sites are not a safe exclusion filter.

**Smallest correction:** retain all possible recognized loader kinds for an alias and conservatively process their applicable semantics, or explicitly record the alias ambiguity while retaining the `__import__` fromlist possibility. A full Python scope interpreter is unnecessary. Before correction, qualify the output as a partial static catalogue rather than complete conservative closure. No claim is made that this counterexample occurs in the specified candidate; that tree was not inspected.

### F2 — The outside-output check binds the supplied directory, not the actual Git root

**Severity: moderate boundary defect for generic invocation; avoidable in the intended fixed invocation. Location: `Objects.git`, lines 62–68; `main`, lines 279–283.** Any existing directory is accepted as `--repo`. Git can discover a repository above that directory, while the output guard checks only whether the resolved output is underneath the supplied directory.

For an actual worktree `/repo`, the arguments `--repo /repo/subdir --output /repo/report.json` pass the source's outside-directory check. Git reads `/repo`'s objects, while the report is created inside `/repo`. The reported `source.repo` remains `/repo/subdir`; the script does not record or verify the discovered worktree root. Similarly, checking for a literal `.git` path component is not a general determination of all possible Git metadata directories.

Full commit/blob identity checks still bind the bytes read to the requested object IDs; this finding does not allow a different commit's contents to pass those checks. It concerns actual repository context and the promised output boundary.

**Smallest correction:** establish the actual worktree root through a read-only Git context query and require the supplied repository argument to match it, then apply the output guard to that root. For this bounded use, root can instead rely on its already verified native worktree-root custody and use an exact new caller-owned path under the admitted temporary directory. No additional source mutation or broad repository scan is needed to avoid the illustrated case. Do not pass an arbitrary nested directory and claim that this script independently certified the outside-repository boundary.

## Working source properties

- Git commands are argument arrays without a shell. The script reads fixed commit objects, recursive tree listings and reached blobs. It contains no checkout, fetch, installer, provider, service or first-party execution call. Ambient `GIT_*` variables are removed; replacement objects and optional locks are disabled, and lazy fetch/transports are refused through the supplied environment settings.
- Commit and read-blob contents are checked against their Git object digests. Every changed tracked path is retained by comparing mode, type and object ID over the union of both trees. A rename appears as a deletion and addition; it is not silently omitted. Unreached changed files retain their Git IDs, while SHA256 content hashes are supplied for actually read source blobs. Those are different proof scopes.
- Lexical imports, possible local from-import submodules and package initializers are included across branches and deferred functions. Symlink/nonordinary Python entries are not followed as source: their mode produces a retained incomplete-parse/error record. Known star, nonliteral and loader gaps are explicitly represented where recognized.
- Initial commit/tree read failures and Git-process timeouts fail the invocation. Caught per-file object/parser failures remain visible in `parser_or_object_errors` and in each source's parse status; they are not silently converted into successful parses. Other uncaught failures prevent a completed report. A successful process exit alone does not mean every file parsed: the catalogue intentionally permits a report containing per-file errors.
- The JSON payload is constructed before opening the output. Mode `"x"` prevents overwriting an existing target under ordinary trusted-directory semantics, including an existing final-component symlink at open time. An I/O failure can leave a newly created partial report, so completion requires the process result and a valid report, not file existence alone. Parent-directory path changes are not an adversarial-filesystem guarantee of this script.

## How root can use the result

For the specified fixed invocation, use the complete changed-path catalogue, object identities, positively reached sources and explicitly recorded gaps to prioritize further release review. Keep `parser_or_object_errors`, parse statuses, dynamic sites, external/unresolved edges and `LIMITATIONS` attached to the result. `root_resolved` means a local resolution candidate was found; it does not establish that the entry parsed, executed or produced a complete graph.

The graph covers only the candidate's tracked `.py` paths under its declared root-import assumption. It does not traverse the predecessor's deleted modules, installed/compiled/generated sources, alternate import roots, all dynamic loaders, configuration, templates, service wiring or data/schema effects. The predecessor commit is a Git comparison at an observed live marker, not fresh inspection of every installed or loaded runtime file. Python startup and the chosen Git executable also remain properties of the caller's trusted runtime, not effects independently attested by the report's constant `first_party_imports_executed: false` field.

**Scoped conclusion:** read-only catalogue use is acceptable within that known invocation envelope. F1 requires correction before claiming conservative coverage of recognized import forms; F2 requires either the verified caller envelope or a source correction before claiming that the script itself enforces an outside-actual-repository output. No result from this aid certifies source CI, writer custody, deployment scope, runtime compatibility or production acceptance.

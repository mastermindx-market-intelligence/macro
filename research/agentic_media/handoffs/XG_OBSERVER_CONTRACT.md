# XG novelty observer — contract v1.1

Status: **specification, unbuilt**. Owning card: `t_2bb26bfe`. Author seat: engineering.
v1.1 amends v1 with four collection-layer gaps raised by the board seat: no defined verdict for
an unsupported schema, `baseline_allowlist` held to a lower standard than the snapshot, no
representation of what collection failed to see, and no content-addressing of the snapshot at
consumption. This file is a contract, not an implementation. Nothing here grants permission,
binds an account, or enables a runtime operation.

## Purpose

The harness gate chain validates *intent*: is this identity admitted, is this proxy declared,
is this slot inside the box ceiling. It cannot see that the box is **already running something
the registry never declared**. On 2026-11-07 a parallel automation worker drove three CDP-attached
Chrome instances on `mini1` while the harness PR was an unsigned draft; no gate in the chain would
have reported it, because every gate asked about declared things.

The observer closes that gap by enumerating reality and diffing it against declaration.

## Two rules, both load-bearing

1. **Readback proves state, not ownership.** The observer may report a resource as
   `undeclared`. It must never report an identity as `known`, `authorized`, or `ours`.
   Attribution is a separate evidence path with a separate owner (process, manifest, or
   payment trail) — never inferred from a snapshot.
2. **A self-report cannot be the observer.** The snapshot must be produced by a process
   independent of the subject's own tree. A worker's own README, health script, or
   environment report is corroborating material, not observation. The snapshot carries its
   provenance so the distinction is checkable after the fact.

## Snapshot contract

Transport: one JSON document per host per sweep. The harness consumes it as a **pure input**;
no import from `tools/xguerrilla/` and no shared helper module, so the observer can be built,
tested and merged while the harness PR is still a draft.

```jsonc
{
  "schema_version": 1,
  "host": "mini1",
  "taken_at": "2026-11-07T22:47:00-07:00",
  "observer": "hermes",                       // seat that ran the sweep
  "provenance": {
    "ssh_target": "mini1",
    "commands": ["launchctl list", "lsof -nP -iTCP -sTCP:LISTEN", "ps axo pid,ppid,command"],
    "tools": {"macos": "26.5", "lsof": "4.91"},   // tool identity
    "mutating": false
  },
  "collected": {                              // what the sweep could and could not see
    "hosts_attempted": ["mini1","mini2","mini3","mini4"],
    "hosts_returned": ["mini1","mini2"],
    "commands_run": [{"cmd": "lsof -nP -iTCP -sTCP:LISTEN", "exit": 0}],
    "command_failures": [{"host": "mini3", "cmd": "ssh", "error": "timeout"}]
  },
  "launchd":   [{"label": "com.xg.proxyauth", "plist_path": "...", "pid": 60367, "loaded_at": "..."}],
  "listeners": [{"port": 9333, "bind_addr": "127.0.0.1", "pid": 60112, "proc": "Google Chrome"}],
  "chrome":    [{"pid": 60112, "cdp_port": 9333, "proxy_server": "http://<redacted>",
                 "profile_dir": "~/xg/profiles/smoke", "ppid": 1, "started_at": "..."}],
  "cdp_sessions": [{"pid": 60367, "local": "127.0.0.1:5xxxx", "remote": "127.0.0.1:9333", "state": "ESTABLISHED"}]
}
```

Requirements:

- **Read-only.** No process killed, no file written on the observed host, no port touched.
- **No credential values.** `proxy_server` is host:port only. Users, passwords and TOTP seeds
  never enter a snapshot, a log, or a report. An observed credential file is reported by path
  and mode, never by content.
- **Provenance is mandatory.** A snapshot without `observer` + `commands` + `taken_at` is
  rejected rather than trusted.
- **`mutating: true` is a rejection condition**, not a warning.
- **`collected` is mandatory.** A host that did not answer, a command that exited non-zero, or a
  truncated listing must appear in `command_failures`. An empty array in a collection block means
  *collection was complete and found nothing*, never *collection didn't happen*.
- **Tool identity is recorded** (`macos`, `lsof`, and any other tool whose output the diff
  depends on). Without it, a later "quiet" may only mean a different command produced
  different output.

## Verdicts

Five outcomes. The rule refuses rather than guesses:

| verdict | meaning | effect on launch |
|---|---|---|
| `declared` | observed and in the registry | pass |
| `baseline` | observed and in `baseline_allowlist` | pass |
| `undeclared` | observed in neither | **refuse** |
| `refused: collection_incomplete` | `collected` shows a host or command that did not answer | **refuse** |
| `refused: schema_unsupported` | `schema_version` unknown, or registry `registry_revision` newer than the consumer understands | **refuse** |

`refused: schema_unsupported` is the anti-fail-open clause. Three verdicts with no home for an
input the consumer does not understand leaves best-effort parsing as the only available
behaviour — fail-open, the same defect in a new coat as "every gate asked about declared things".

**Version discipline:** `schema_version` is 1 only because no consumer exists yet. Once the
first consumer ships, any *required* field addition bumps to 2, and a v1 consumer meeting a v2
snapshot refuses rather than tolerating unknown fields.

## Content addressing at consumption

`~/.hermes/reports/` is a mutable user directory. The harness therefore takes
`{path, sha256, taken_at}` — never a bare path — and writes the sha256 into the **admission
receipt**. "The sweep ran" is otherwise an assertion; a sha is a readback. A file whose sha no
longer matches the receipt is evidence of tampering or staleness, not of a quieter box.

## Diff rule

Inputs: (a) the snapshot, (b) the identity registry, (c) the versioned `baseline_allowlist`.

- observed and declared → `declared`.
- observed and in `baseline_allowlist` → `baseline` (stock OS; not ours, not novel).
- observed in **neither** → `undeclared` → **launch refuses.**
- collection incomplete or schema unsupported → **launch refuses.**

## `baseline_allowlist` — held to the snapshot's standard

This is the one input that can turn `undeclared` into a pass, so it carries the same discipline
as an admission receipt. Each entry:

```yaml
- match: "proc=ARDAgent, port=3283"
  reason: "stock macOS Remote Desktop agent, pre-existing"
  added_by: engineering
  added_at: 2026-11-07
  host_seed_sha: "<sha256 of the clean-host snapshot it was derived from>"
```

Rules: no entry without `reason` and `added_by`; an allowlist whose `host_seed_sha` does not
match the clean-host snapshot it claims is **refused**, not trimmed. An allowlist that grows
without those fields is an escape hatch, and escape hatches are how a novelty check becomes a
formality.

## Binding by port, not by count

`cdp_port` is part of the identity binding. A CDP port that is open and not bound to a declared
identity is an **undeclared identity**, not merely an extra process. During the 2026-11-07
incident the box went from two CDP instances to three (9333, 9222, 9223) while a hold was in
force; a count-based ceiling describes that as "3 of 6, fine". A port-bound registry describes
it correctly.

Box capacity is carried as `{box, measured_ceiling}` — measured, not nominal. On `mini1`,
`ChatGPT.app` plus Codex renderers hold roughly 3.2 GB of 16 GB and ~28 helper processes run
per Chrome instance, so the binding constraint on concurrency is often process count, not memory.

## Acceptance evidence (required before this leaves draft)

1. Unit tests for the diff rule, including the three-way `declared` / `baseline` / `undeclared`
   split and a fixture where a stock OS service is present.
2. A rejection test: a snapshot missing `provenance` or carrying `mutating: true` is refused.
3. **The first fleet sweep** recorded verbatim as the fixture — real ports, real helper counts,
   four hosts — so the suite notices if the emitted shape has already drifted from this contract.
4. A negative test proving the observer reports `undeclared` and never `known`.
5. **Schema-refusal test:** a `schema_version: 2` snapshot, and a registry revision newer than
   the consumer knows, both yield `refused: schema_unsupported`.
6. **Collection-refusal test:** a snapshot with non-empty `collected.command_failures`, and one
   from a host that did not answer, both yield `refused: collection_incomplete` — and *neither*
   passes as "no findings".
7. **Allowlist-refusal test:** an entry missing `reason`/`added_by`, and an allowlist whose
   `host_seed_sha` mismatches, are both refused.
8. **Content-addressing test:** a snapshot whose sha256 no longer matches the value recorded in
   the admission receipt is refused.

Absent those eight, the observer is a document, not an artifact.

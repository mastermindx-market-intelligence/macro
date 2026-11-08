# XG novelty observer — contract v1

Status: **specification, unbuilt**. Owning card: `t_2bb26bfe`. Author seat: engineering.
This file is a contract, not an implementation. Nothing here grants permission, binds an
account, or enables a runtime operation.

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
    "mutating": false
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

## Diff rule

Inputs to the check: (a) the snapshot, (b) the identity registry, (c) the versioned
`baseline_allowlist`.

- A resource observed and declared → `declared`.
- A resource observed and in `baseline_allowlist` → `baseline` (stock OS; not ours, not novel).
- A resource observed in **neither** → `undeclared` → **launch refuses.** Not a warning, not a
  log line: refuse.

`baseline_allowlist` is versioned separately from the registry and seeded from a known-clean
host (on macOS: `ARDAgent` on `*:3283` and similar stock services). Without it a novelty check
fails closed on the operating system itself, forever, and gets disabled by the first person
who needs to ship.

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
3. A recorded fixture sweep from one real host, with the raw JSON stored in the test tree.
4. A negative test proving the observer reports `undeclared` and never `known`.

Absent those four, the observer is a document, not an artifact.

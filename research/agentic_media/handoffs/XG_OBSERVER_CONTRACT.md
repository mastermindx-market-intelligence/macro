# XG novelty observer — contract v1.6

Status: **specification, unbuilt**. Owning card: `t_2bb26bfe`. Author seat: engineering.
v1.6 fixes two defects found by reading the artifacts rather than the reports: a pinned fixture
that did not contain the value it was pinned for, and a staleness rule whose input does not exist.
It also promotes `bind_addr` from a schema rule with no consumer to a classified field.
Nothing here grants permission, binds an account, or enables a runtime operation.

## Purpose

The harness gate chain validates *intent*. It cannot see that the box is **already running
something the registry never declared**. The observer enumerates reality and diffs it against
declaration.

## Six rules, all load-bearing

1. **Readback proves state, not ownership.** Report `undeclared`; never `known`, `authorized`, or
   `ours`. Attribution is separate evidence with a separate owner — argv, plist, manifest, payment.
2. **A self-report cannot be the observer.** A README, health script, `DevToolsActivePort`,
   environment report: corroboration, never observation.
3. **A diff across a tool change is not a time series.** Matching `sweep_script_sha256` and tool
   identity or `refused: tool_changed`.
4. **A bound socket is not an endpoint.** `lsof` proves the port is held; only a probe proves
   something is served.
5. **A process is not its bundle.** Staleness is a *time* comparison, not a version-string
   comparison: a process is stale when `started_at` is older than the mounted framework directory
   it runs from. This fires for processes that answer 404, which the endpoint-based version had no
   way to reach.
6. **A field with no consumer is a comment.** Every schema rule names the reader that acts on it.
   `bind_addr` was nullable-by-accident for six rounds because nothing classified on it; it now
   classifies, and it is how a wildcard listener entered the record.

## Snapshot contract

Pure input for the harness: no import from `tools/xguerrilla/`, no shared helper module.

```jsonc
{
  "schema_version": 1,
  "host": "mini1",
  "taken_at": "2026-11-08T08:52:17Z",
  "observer": "hermes",
  "provenance": {
    "ssh_target": "mini1",
    "commands": ["launchctl print", "lsof -nP -iTCP -sTCP:LISTEN", "ps axo pid,ppid,lstart,command",
                 "curl /json/version", "lsof -p <pid> (framework map)"],
    "tools": {"macos": "27.0 (26A428)", "lsof": "4.91"},
    "sweep_script_sha256": "f99242c4ef2ebbed4b776beca5fe6c6f87e8d7531df8bc89ba0be6025011b286",
    "mutating": false
  },
  "collection_status": "complete",
  "collected": { "hosts_attempted": ["mini1","mini2","mini3","mini4"], "hosts_returned": ["mini1"],
                 "commands_run": [{"cmd": "lsof -nP -iTCP -sTCP:LISTEN", "exit": 0}],
                 "command_failures": [{"host": "mini2", "cmd": "ssh", "error": "Could not resolve hostname"}] },
  "listeners": [{"port": 9223, "bind_addr": "127.0.0.1", "pid": 35984, "proc": "Google Chrome"},
                {"port": 3283, "bind_addr": "*", "pid": 34487, "proc": "ARDAgent"}],
  "endpoints": [{"port": 9223, "http": 200, "serving": true, "browser": "Chrome/155.0.8059.40", "peers": 1},
                {"port": 9222, "http": 404, "serving": false, "browser": null, "peers": 0}],
  "host_software": {"app": "/Applications/Google Chrome.app",
                    "framework_versions": [{"version": "155.0.8059.40", "mtime": "2026-10-12T19:06:33-07:00"},
                                           {"version": "156.0.8078.80", "mtime": "2026-11-02T15:27:50-08:00"},
                                           {"version": "157.0.8103.38", "mtime": "2026-11-03T16:32:54-08:00"}]},
  "chrome": [{"pid": 35984, "started_at": "2026-10-23T15:39:13-07:00", "cdp_port": 9223,
              "profile_dir": "~/.local/share/mastermind-runtime/chrome-automation",
              "mounted_framework": "155.0.8059.40"}],
  "connection_count": 3,
  "cdp_sessions": [{"pid": 17665, "local": "127.0.0.1:60998", "remote_port": 9223, "state": "ESTABLISHED"}],
  "socket_ends":  [{"pid": 35984, "local_port": 9223, "peer": "127.0.0.1:60998", "state": "ESTABLISHED"}],
  "launchd": [{"label": "com.mastermind.peekaboo-bridge", "pid": 17533, "start_interval_s": 60,
               "runs": 21944, "bootout_authority": null}]
}
```

### Shape rules

- `cdp_sessions` client-side only; echoes in `socket_ends[]`; `len(cdp_sessions) == connection_count`;
  dedupe key `(pid, remote_port)`.
- Single types: `hosts_returned` always a list; ports always integers.
- `bind_addr` non-nullable, and **every listener is classified**, not just CDP ports. A non-loopback
  bind is `undeclared` until a declaration of record exists; it is never silently out of scope
  because the registry was scoped to three ports.
- `socket_ends` advisory; no count may be derived from it.
- The manifest carries `schema_version` and `sweep_script_sha256`.
- Verdicts occupy three keys: `socket_verdicts[]`, `artifact_verdict`, `comparison_verdict`.
- **`mounted_framework` is read from `lsof -p <pid>`**, not inferred from argv or from the app
  bundle. It is the only honest discriminator: Chrome retains old version directories, so a
  `(deleted)` mapping scan returns **0 rows on a five-week-old renderer**.

## Verdicts

**Socket:** `declared` | `baseline` | `undeclared` (refuse) | `bound_no_endpoint` (not registrable).
`baseline` may never admit a Chrome CDP listener, nor a GUI-automation agent reachable off-box.

**Artifact:** `complete` | `refused: collection_incomplete` | `refused: schema_unsupported`.

**Comparison:** `comparable` | `refused: tool_changed`.

**Gate (blocks a launch):**

| gate | condition | meaning |
|---|---|---|
| `refused: unowned_bridge` | `bootout_authority` null and bridge `attached` or `armed` | nobody on record can stop the surface |
| `refused: stale_binary` | `chrome[].started_at` < mtime of `mounted_framework` | process executing a pre-update image |
| `refused: endpoint_absent` | `bound_no_endpoint` on a port the registry would bind | socket without an identity |

### Staleness, measured (mini1, 2026-11-08)

Framework dirs on disk: `155.0.8059.40` (Oct 12), `156.0.8078.80` (Nov 2), `157.0.8103.38` (Nov 3).
`Info.plist` and `Contents/MacOS/Google Chrome` both mtime **Nov 3 16:32**; bundle version **157**.
`lsof -p 35984` and `lsof -p 34493` both map `Versions/155.0.8059.40`. Both processes started
Oct 23, so both have skipped **two** in-place updates, and `(deleted)` mappings = **0** for each.
The endpoint-based rule could only ever see 35984 (serving) and never 34493 (404). The
`started_at`-vs-framework rule sees both, plus all four instrumented-profile siblings.

### Bridge states

`attached` | `armed` (process alive, keepalive loaded, zero sessions) | `absent`. `armed` refuses:
on mini1 the Peekaboo bridge was `armed` at 08:52Z — pid 17533 resident since 05:02:01,
`runs = 21944`, sessions zero.

## Sampling, not scalars

`connection_count` on this stack is **bistable at heartbeat phase**: three runs inside 08:52:00–08:52:17
read `2`, `3`, `3`, with Peekaboo's local port moving `63278 → 65011` inside seventeen seconds.
A fixture therefore **may not assert a scalar** `connection_count`. It asserts the **persistent set**
— `17665 → 9223` and the `com.xg.proxyauth` child → `9333`, present in every run — and treats the
Peekaboo attach as the periodic term it is. Any comparison of counts must sample across ≥ one full
`StartInterval` (60 s) or report the heartbeat as drift.

## Registry addition (delta on v1)

```yaml
binding:
  cdp_port: 9223
  browser_version: "155.0.8059.40"
  mounted_framework_at_admission: "155.0.8059.40"   # re-checked at launch against lsof
owner_bridge:
  label: com.mastermind.peekaboo-bridge
  plist_sha256: "<sha>"
  start_interval_s: 60
  state: armed
  bootout_authority: null
```

## Accepted fixture

**Pinned:** sweep **2026-11-08T08:52:17Z**, `script_sha256 f99242c4ef2ebbed4b776beca5fe6c6f87e8d7531df8bc89ba0be6025011b286`,
manifest **`5497ef0d818f7b271e3db1082874f8410b70b34b707006e6002788848f6a007c`**, mini1 payload
`connection_count: 3`, three client rows (17533→9223:65011, 17665→9223, 67710→9333).

Correction recorded in the artifact rather than in chat: an earlier version of this section pinned
the same manifest as `connection_count: 2`. The manifest was right and the pin was wrong — 2 was
read from a report, not from the payload. The adjacent 08:52:00 manifest (`b188d51c64bf6fd7…`)
is the run where Peekaboo is absent. Both are kept as the bistability evidence.

Gaps the fixture does not close, and must not pretend to: `host_software` and `mounted_framework`
are **absent** from all three payloads (`071251`, `085200`, `085217`), so acceptance item 12 cannot
be satisfied by this fixture. It needs one run with the framework section emitted.

**Superseded, not diffable:** `5458165275ab…` (v1.3 shape), `362919cc…` (v1.2), `68589392…` (pre-dedupe).

## Acceptance evidence (required before this leaves draft)

1. Diff-rule unit tests: `declared` / `baseline` / `undeclared` / `bound_no_endpoint`.
2. `provenance` missing or `mutating: true` → refused.
3. The pinned fixture stored verbatim, **asserting the persistent set, not a connection count**.
4. Negative test: observer reports `undeclared`, never `known`.
5. `schema_version: 2` or newer registry revision → `refused: schema_unsupported`.
6. Non-empty `command_failures` / silent host → `refused: collection_incomplete`, never "no findings".
7. Allowlist entry missing `reason`/`added_by`, or `host_seed_sha` mismatch → refused.
8. Snapshot sha256 not matching the admission receipt → refused.
9. Two snapshots differing only in `sweep_script_sha256` → `refused: tool_changed`, no delta emitted.
10. Endpoint test: held socket + 404 → `bound_no_endpoint`, never an exposure.
11. Bridge test: null `bootout_authority` with bridge `attached` **or** `armed` → `refused: unowned_bridge`.
12. Staleness test: a process whose `started_at` precedes its `mounted_framework` mtime →
    `refused: stale_binary`; the fixture must include a **404-answering** process, or the test
    proves only the easy case.
13. Wildcard test: a listener with `bind_addr` not loopback and no declaration of record →
    `undeclared`, emitted in `socket_verdicts[]` — not omitted for being outside the CDP scope.
14. Sampling test: three runs spanning one `StartInterval`; the assertion is on the persistent set
    and the verdict is stable, not on a scalar that flips with the heartbeat.

Absent those fourteen, the observer is a document, not an artifact.

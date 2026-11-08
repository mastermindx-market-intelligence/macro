# XG novelty observer — contract v1.5

Status: **specification, unbuilt**. Owning card: `t_2bb26bfe`. Author seat: engineering.
v1.4 split the verdicts, added `connection_count`, `bound_no_endpoint` and the `unowned_bridge`
gate. v1.5 adds: the **served-vs-on-disk browser version check** (`refused: stale_binary`), the
bridge **armed/attached** distinction, and the re-pinned accepted fixture. Nothing here grants
permission, binds an account, or enables a runtime operation.

## Purpose

The harness gate chain validates *intent*. It cannot see that the box is **already running
something the registry never declared**. The observer enumerates reality and diffs it against
declaration.

## Five rules, all load-bearing

1. **Readback proves state, not ownership.** The observer may report a resource as `undeclared`.
   It must never report an identity as `known`, `authorized`, or `ours`. Attribution is separate
   evidence with a separate owner — argv, plist, manifest, payment trail.
2. **A self-report cannot be the observer.** The snapshot comes from a process independent of the
   subject's tree. A README, a health script, `DevToolsActivePort`, an env report: corroboration,
   never observation.
3. **A diff across a tool change is not a time series.** Compare only snapshots with matching
   `sweep_script_sha256` and tool identity; otherwise `refused: tool_changed`.
4. **A bound socket is not an endpoint.** `lsof` proves a port is held; only a probe proves
   something is served. Nothing is said about exposure or drivability before the probe.
5. **A process is not its bundle.** `/json/version` reports the version the process *executed*;
   the app bundle reports the version *on disk*. They diverge after an in-place update that never
   restarted the process, and the divergence is what matters, not either number alone.

## Snapshot contract

One JSON document per host per sweep, consumed as a **pure input** (no import from
`tools/xguerrilla/`, no shared helper module), so the observer can ship while the harness PR is a
draft.

```jsonc
{
  "schema_version": 1,
  "host": "mini1",
  "taken_at": "2026-11-08T08:52:17Z",
  "observer": "hermes",
  "provenance": {
    "ssh_target": "mini1",
    "commands": ["launchctl print", "lsof -nP -iTCP -sTCP:LISTEN", "ps axo pid,ppid,command", "curl /json/version"],
    "tools": {"macos": "27.0 (26A428)", "lsof": "4.91"},
    "sweep_script_sha256": "f99242c4ef2ebbed4b776beca5fe6c6f87e8d7531df8bc89ba0be6025011b286",
    "mutating": false
  },
  "collection_status": "complete",
  "collected": { "hosts_attempted": ["mini1","mini2","mini3","mini4"],
                 "hosts_returned": ["mini1"],
                 "commands_run": [{"cmd": "lsof -nP -iTCP -sTCP:LISTEN", "exit": 0}],
                 "command_failures": [{"host": "mini2", "cmd": "ssh", "error": "Could not resolve hostname"}] },
  "listeners": [{"port": 9223, "bind_addr": "127.0.0.1", "pid": 35984, "proc": "Google Chrome"}],
  "endpoints": [{"port": 9223, "http": 200, "serving": true, "browser": "Chrome/155.0.8059.40",
                 "protocol": "1.3", "peers": 1}],
  "host_software": [{"bundle": "/Applications/Google Chrome.app", "version": "157.0.8103.38",
                     "info_plist_mtime": "2026-11-03T16:32:55-08:00"}],
  "connection_count": 2,
  "cdp_sessions": [{"pid": 17665, "local": "127.0.0.1:60998", "remote_port": 9223, "state": "ESTABLISHED"}],
  "socket_ends":  [{"pid": 35984, "local_port": 9223, "peer": "127.0.0.1:60998", "state": "ESTABLISHED"}],
  "launchd": [{"label": "com.mastermind.peekaboo-bridge", "plist_path": "...", "pid": 17533,
               "start_interval_s": 60, "runs": 21944, "bootout_authority": null}]
}
```

### Shape rules

- **`cdp_sessions` is client-side only**; echoes live in `socket_ends[]`. `connection_count` is the
  number to read, and `len(cdp_sessions) == connection_count`. Dedupe key is `(pid, remote_port)` —
  a local port changes on every keepalive reconnect and would score phantom churn.
- **Single types everywhere**: `hosts_returned` always a list of names; ports always integers.
- **`bind_addr` non-nullable** on every listener. `*` or `0.0.0.0` on a CDP surface is an incident.
- **`socket_ends` is advisory.** An absent echo during a reconnect is normal; no count may be
  derived from it, and a consumer must never infer a fault from one.
- **The manifest carries its own `schema_version` and `sweep_script_sha256`**, so a
  manifest-vs-manifest diff is self-evaluating.
- **Verdicts occupy three keys, never one**: `socket_verdicts[]`, `artifact_verdict`,
  `comparison_verdict`. A per-port table must never be asked to print an artifact verdict.

## Verdicts

**Socket:** `declared` | `baseline` | `undeclared` (**refuse**) | `bound_no_endpoint`
(**not registrable** — a socket with no identity). `baseline` may never admit a Chrome CDP
listener; that would launder a product into the operating system.

**Artifact:** `complete` | `refused: collection_incomplete` | `refused: schema_unsupported`.

**Comparison:** `comparable` | `refused: tool_changed`.

**Gate (blocks a launch, evaluated per identity):**

| gate verdict | condition | meaning |
|---|---|---|
| `refused: unowned_bridge` | `owner_bridge.bootout_authority` is null and the bridge is `attached` **or** `armed` | nobody on record can stop the surface the driver would ride |
| `refused: stale_binary` | `endpoints[].browser` major ≠ `host_software[].version` major for the app that owns the process | the process is executing a pre-update image |
| `refused: endpoint_absent` | `bound_no_endpoint` on a port the registry would bind | a socket with no identity cannot be admitted |

### Why `stale_binary` exists

Measured on mini1, 2026-11-08: all three Chrome mains run the **same** bundle,
`/Applications/Google Chrome.app`, whose on-disk version is `157.0.8103.38` (Info.plist mtime
Nov 3). Yet `:9223` serves `Chrome/155.0.8059.40` and `:9333` serves `Chrome/157.0.8103.38`. Same
bundle, different served majors — because pid 35984 has been running since Oct 23 and survived the
in-place update. This is **not** two installs and **not** a frozen browser without an update path;
it is a long-lived process executing an unpatched binary image, two majors behind the disk. That
distinction changes the remediation (restart the process, not reinstall the app) and it is only
visible when served and on-disk versions are both recorded.

### Bridge states

`owner_bridge.state`: `attached` (live client sessions) | `armed` (process alive, keepalive loaded,
zero sessions) | `absent`. **`armed` is a refusal too**, because the next attach is one
`StartInterval` tick away — on mini1 the Peekaboo bridge was observed `armed` at 08:52Z: pid 17533
resident since 05:02:01, keepalive `runs = 21944`, `connection_count` down to 2. "It stopped" was
half true, and only the snapshot says which half.

## Registry addition (delta on v1)

```yaml
binding:
  cdp_port: 9223
  browser_version: "155.0.8059.40"   # served version, recorded at admission, re-checked at launch
owner_bridge:
  label: com.mastermind.peekaboo-bridge
  plist_path: /Users/mini1/Library/LaunchAgents/com.mastermind.peekaboo-bridge.plist
  plist_sha256: "<sha>"
  start_interval_s: 60
  state: armed                       # attached | armed | absent
  bootout_authority: null            # a seat or a human; null ⇒ refused: unowned_bridge
```

## Content addressing

The harness takes `{path, sha256, taken_at}` — never a bare path — and writes the sha256 into the
admission receipt. `~/.hermes/reports/` is a mutable user directory.

## Accepted fixture

**Pinned:** run of **2026-11-08T08:52:17Z**, `sweep.py` v1.4 with `endpoints[]`,
`script_sha256 f99242c4ef2ebbed4b776beca5fe6c6f87e8d7531df8bc89ba0be6025011b286`,
manifest sha256 **`5497ef0d818f7b271e3db1082874f8410b70b34b707006e6002788848f6a007c`**,
`connection_count: 2`, `endpoints`: 9222 `bound_no_endpoint` / 9223 serving 155 / 9333 serving 157.

**Single-run caveat:** `connection_count: 2` is one observation on a new parser. Per rule 3 the
prior 3 is not comparable, so 2 is not yet a stable baseline — it becomes one only when a second
run on the same `script_sha256` reproduces it.

**Superseded and not diffable:** `5458165275ab…` (v1.3 shape, `92ddfb15…`), `362919cc…` (v1.2),
`68589392…` (pre-dedupe). The v1.3 → v1.4 `3 → 2` change is the canonical example of rule 3 in
practice: it spans a parser change, so it is a re-baseline, not a delta.

## Acceptance evidence (required before this leaves draft)

1. Diff-rule unit tests: `declared` / `baseline` / `undeclared` / `bound_no_endpoint`.
2. `provenance` missing or `mutating: true` → refused.
3. The pinned fixture above, stored verbatim, **plus** a second run on the same script sha.
4. Negative test: observer reports `undeclared`, never `known`.
5. `schema_version: 2`, or a newer registry revision → `refused: schema_unsupported`.
6. Non-empty `command_failures` / a host that did not answer → `refused: collection_incomplete`,
   and neither passes as "no findings".
7. Allowlist entry missing `reason`/`added_by`, or `host_seed_sha` mismatch → refused.
8. Snapshot sha256 not matching the admission receipt → refused.
9. Two snapshots differing only in `sweep_script_sha256` → `refused: tool_changed`, with **no**
   connection-count delta emitted.
10. Endpoint test: held socket + 404/empty probe → `bound_no_endpoint`, never an exposure.
11. Bridge test: `bootout_authority: null` with bridge `attached` **or** `armed` →
    `refused: unowned_bridge` at launch, not a warning at snapshot time.
12. Version test: served major ≠ on-disk major → `refused: stale_binary`, and the fixture proves
    the same-bundle-two-versions case rather than two installs.

Absent those twelve, the observer is a document, not an artifact.

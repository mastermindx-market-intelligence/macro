# XG novelty observer — contract v1.4

Status: **specification, unbuilt**. Owning card: `t_2bb26bfe`. Author seat: engineering.
v1.3 added parser identity (`refused: tool_changed`). v1.4 adds: the socket/artifact/comparison
verdict split, `connection_count` as the readable number, `bind_addr` as non-nullable, the
`bound_no_endpoint` class, the `refused: unowned_bridge` gate, and a correction — a
`DevToolsActivePort` file is corroboration and a bound socket is not an endpoint.
Nothing here grants permission, binds an account, or enables a runtime operation.

## Purpose

The harness gate chain validates *intent*: is this identity admitted, is this proxy declared,
is this slot inside the box ceiling. It cannot see that the box is **already running something
the registry never declared**. The observer closes that gap by enumerating reality and diffing it
against declaration.

## Four rules, all load-bearing

1. **Readback proves state, not ownership.** The observer may report a resource as
   `undeclared`. It must never report an identity as `known`, `authorized`, or `ours`.
   Attribution is a separate evidence path with a separate owner — process argv, plist, manifest,
   payment trail — never inferred from a snapshot.
2. **A self-report cannot be the observer.** The snapshot must be produced by a process
   independent of the subject's own tree. A worker's own README, health script,
   `DevToolsActivePort`, or environment report is corroborating material, not observation.
3. **A diff across a tool change is not a time series.** Two snapshots may be compared only when
   their `sweep_script_sha256` and tool identities match. Otherwise `refused: tool_changed` —
   not "the box changed", and not a delta.
4. **A bound socket is not an endpoint.** `lsof` proves a port is held; it does not prove anything
   serves on it. An endpoint exists only if the CDP probe answers. Everything that would be said
   about a port — exposure, drivability, identity — is said only after the probe.

## Snapshot contract

One JSON document per host per sweep. The harness consumes it as a **pure input**; no import from
`tools/xguerrilla/`, no shared helper module, so the observer can be built, tested and merged
while the harness PR is still a draft.

```jsonc
{
  "schema_version": 1,
  "host": "mini1",
  "taken_at": "2026-11-08T07:12:51Z",
  "observer": "hermes",
  "provenance": {
    "ssh_target": "mini1",
    "commands": ["launchctl print", "lsof -nP -iTCP -sTCP:LISTEN", "ps axo pid,ppid,command", "curl /json/version"],
    "tools": {"macos": "27.0 (26A428)", "lsof": "4.91"},
    "sweep_script_sha256": "92ddfb15aee058760b6f0e156f284a25410f9ee904ff2ce1c169d2e1ae63e66e",
    "mutating": false
  },
  "collection_status": "complete",            // complete | incomplete — never a verdict word
  "collected": {
    "hosts_attempted": ["mini1","mini2","mini3","mini4"],
    "hosts_returned": ["mini1"],
    "commands_run": [{"cmd": "lsof -nP -iTCP -sTCP:LISTEN", "exit": 0}],
    "command_failures": [{"host": "mini2", "cmd": "ssh", "error": "Could not resolve hostname"}]
  },
  "listeners": [{"port": 9223, "bind_addr": "127.0.0.1", "pid": 35984, "proc": "Google Chrome"}],
  "endpoints": [{"port": 9223, "probe": "400", "serving": true,
                 "browser": "Chrome/155.0.8059.40", "protocol": "1.3", "peers": 2},
                {"port": 9222, "probe": "404", "serving": false, "peers": 0}],
  "connection_count": 3,                      // the number to read; see cdp_sessions
  "cdp_sessions": [{"pid": 17533, "local": "127.0.0.1:63278", "remote_port": 9223, "state": "ESTABLISHED"}],
  "socket_ends":  [{"pid": 35984, "local_port": 9223, "peer": "127.0.0.1:60998", "state": "ESTABLISHED"}],
  "launchd": [{"label": "com.mastermind.peekaboo-bridge", "plist_path": "...", "pid": 17533,
               "start_interval_s": 60, "bootout_authority": null}]
}
```

### Shape rules

- **`cdp_sessions` holds client-side rows only.** Server echoes live in `socket_ends[]`.
  `connection_count` is the single readable number, and `len(cdp_sessions) == connection_count`.
  Dedupe key is **`(pid, remote_port)`** — never the local port: a keepalive that reconnects every
  minute changes the local port on each reconnect, and a local-port key scores that as phantom churn.
- **Types are single, everywhere.** `hosts_returned` is always a list of names, never `null` or a
  count. `port`, `cdp_port`, `remote_port` are integers, so they join an integer registry.
- **`bind_addr` is non-nullable** on every listener. If a CDP surface ever reads `*` or `0.0.0.0`,
  that is an incident, and the schema must make it visible rather than absent.
- **`socket_ends` is advisory, not a completeness claim.** The echo of a client row may be missing
  when a sweep races a reconnect — a local port on its fourth value in one session is normal. A
  consumer must never infer a fault from an absent echo, and must never derive a connection count
  from `socket_ends`.
- **The manifest carries its own identity.** Manifest-level `schema_version` and
  `sweep_script_sha256`, so a manifest-vs-manifest comparison can evaluate `refused: tool_changed`
  without opening any snapshot.
- **Verdicts do not share one field.** Three subjects, three keys, evaluated separately:

```jsonc
{
  "socket_verdicts":     [{"port": 9223, "verdict": "undeclared"}],
  "artifact_verdict":    {"verdict": "complete"},
  "comparison_verdict":  {"verdict": "comparable", "vs": "<previous manifest sha256>"}
}
```

  A per-port table must never have to print an artifact verdict, and a consumer iterating ports
  must not be able to drop a comparison refusal silently.

## Verdicts

**Socket** (`declared` / `baseline` / `undeclared` / `bound_no_endpoint`)

| verdict | meaning | effect |
|---|---|---|
| `declared` | observed, a declaration-of-record exists (argv flag, plist→script), and the live socket matches it | pass |
| `baseline` | stock OS service with allowlist provenance | pass |
| `undeclared` | observed, no declaration of record | **refuse** |
| `bound_no_endpoint` | port held, no CDP endpoint answers (404/empty, zero peers) | **not registrable** — a socket with no identity |

`baseline` can never include a Chrome CDP listener: admitting it would launder a product into the
operating system.

**Artifact** (`complete` / `refused: collection_incomplete` / `refused: schema_unsupported`)

**Comparison** (`comparable` / `refused: tool_changed`)

**Gate** (`refused: unowned_bridge`) — raised when the identity's `binding.cdp_port` is served by a
process whose owning bridge declares no `bootout_authority`. The driver returns this refusal rather
than attaching. Rationale: the `com.mastermind.peekaboo-bridge` agent is a `StartInterval 60`
keepalive that restarted 24 minutes after the xg scaffold; "we stopped the driver" is true while
the bridge reconnects within a minute. A rule that only labels sockets can describe an attach
afterwards; it cannot prevent one. Labelling a port is not enough — the registry must bind
**process identity and bootout authority** for any bridge a driver would ride.

## Registry addition (delta on v1)

```yaml
binding:
  cdp_port: 9223
owner_bridge:                        # who can stop it, not who benefits from it
  label: com.mastermind.peekaboo-bridge
  plist_path: /Users/mini1/Library/LaunchAgents/com.mastermind.peekaboo-bridge.plist
  plist_sha256: "<sha>"
  start_interval_s: 60
  bootout_authority: null            # a seat or a human; null ⇒ refused: unowned_bridge
```

## Content addressing

The harness takes `{path, sha256, taken_at}` — never a bare path — and writes the sha256 into the
admission receipt. `~/.hermes/reports/` is a mutable user directory; "the sweep ran" is otherwise
an assertion.

## Accepted fixture

Run 2 of **2026-11-08T07:12:51Z**, `sweep.py` **v1.3**,
`script_sha256 92ddfb15aee058760b6f0e156f284a25410f9ee904ff2ce1c169d2e1ae63e66e`,
manifest sha256 **`5458165275ab3446d38f06c147c318a4f4caa8b1aeee5dbeca4e2286cbcf007e`**.
`connection_count: 3` in that fixture means three connections. Superseded and not to be diffed
against: `362919cc…` (v1.2 shape), `68589392…` (pre-dedupe).

## Acceptance evidence (required before this leaves draft)

1. Diff-rule unit tests: `declared` / `baseline` / `undeclared` / `bound_no_endpoint`.
2. `provenance` missing or `mutating: true` → refused.
3. The accepted fixture above, stored verbatim in the test tree.
4. Negative test: observer reports `undeclared`, never `known`.
5. `schema_version: 2` and a newer registry revision → `refused: schema_unsupported`.
6. Non-empty `command_failures`, and a host that did not answer → `refused: collection_incomplete`,
   and neither passes as "no findings".
7. Allowlist entry missing `reason`/`added_by`, or `host_seed_sha` mismatch → refused.
8. Snapshot sha256 no longer matching the admission receipt → refused.
9. Two snapshots differing only in `sweep_script_sha256` → `refused: tool_changed`, and
   specifically no connection-count delta.
10. **Endpoint test:** a fixture port with a held socket and a 404/empty probe must classify
    `bound_no_endpoint` and must never be reported as an exposure or a drivable surface.
11. **Bridge test:** an entry whose `bootout_authority` is null yields `refused: unowned_bridge`
    at launch, not a warning at snapshot time.

Absent those eleven, the observer is a document, not an artifact.

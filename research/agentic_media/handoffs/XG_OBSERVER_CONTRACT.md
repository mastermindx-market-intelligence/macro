# XG novelty observer — contract v1.8

Status: **specification, unbuilt**. Owning card: `t_2bb26bfe`. Author seat: engineering.
v1.7 corrects an inversion v1.6 shipped: the staleness rule compared `started_at` against the
**mounted** framework's mtime, which is *false* for both stale renderers on mini1 — a gate that
would have green-lit the restart card as unnecessary. Staleness is now identity
(`mounted_framework != versions_current`), no clock. v1.7 also adds the egress coverage block and
the remote-control surface class. v1.8 swaps the fixture pin and adds rule 8: an enumerated
collection must prove its own completeness, because an empty array is a claim of absence.
Nothing here grants permission, binds an account, or enables a
runtime operation.

## Purpose

The harness gate chain validates *intent*. It cannot see that the box is **already running
something the registry never declared**. The observer enumerates reality and diffs it against
declaration.

## Eight rules, all load-bearing

1. **Readback proves state, not ownership.** Report `undeclared`; never `known`, `authorized`, or
   `ours`. Attribution is separate evidence with a separate owner.
2. **A self-report cannot be the observer.** A README, health script, `DevToolsActivePort`,
   environment report: corroboration, never observation.
3. **A diff across a tool change is not a time series.** Matching `sweep_script_sha256` and tool
   identity, or `refused: tool_changed`.
4. **A bound socket is not an endpoint.** `lsof` proves the port is held; only a probe proves
   something is served.
5. **Staleness is identity, not time.** A process is stale when the framework it has mounted
   differs from the framework the app currently points at:
   `chrome[].mounted_framework != versions_current` ⇒ stale. No mtime, no timezone, no skew
   between `ps lstart` and file times, and it survives a restore or a `touch`.
6. **A field with no consumer is a comment.** Every rule names the reader that acts on it. This
   cut both ways in one commit: `bind_addr` had no reader for six rounds (ARDAgent `*:3283` went
   unnamed), and `external_estab` shipped with no reader at all — an inventory nobody classifies
   is worse than none, because it creates the impression of coverage.
7. **A row must prove itself.** A verdict field is recomputable from its own row, not by joining a
   sibling object. `stale_binary` carries `mounted_framework` and `versions_current` beside it.
8. **An enumerated collection must prove its completeness.** An empty array is a claim that nothing
   exists, so every enumerated collection carries a cross-check against an independent source. A
   `remote_control_surfaces: []` on a host with a wildcard ARD listener, a remote-mode
   `desktop-commander` and two studio-direct tunnels is not "no surfaces" — it is a failed
   enumeration, and a consumer reading it as absence fails open on the gate that matters most.

## Snapshot contract

Pure input for the harness: no import from `tools/xguerrilla/`, no shared helper module.

```jsonc
{
  "schema_version": 1,
  "host": "mini1",
  "taken_at": "2026-11-08T09:30:59Z",
  "observer": "hermes",
  "provenance": {
    "ssh_target": "mini1",
    "commands": ["launchctl print", "lsof -nP -iTCP -sTCP:LISTEN", "ps axo pid,ppid,lstart,command",
                 "curl /json/version", "lsof -p <pid> (framework map)"],
    "tools": {"macos": "27.0 (26A428)", "lsof": "4.91"},
    "sweep_script_sha256": "14191528c8a57aaacd2597ba2c0b6ce578b29b9379d2e03cc231d8d2e36cd396",
    "mutating": false
  },
  "collection_status": "complete",
  "collected": { "hosts_attempted": ["mini1","mini2","mini3","mini4"], "hosts_returned": ["mini1"],
                 "commands_run": [{"cmd": "lsof -nP -iTCP -sTCP:LISTEN", "exit": 0}],
                 "command_failures": [{"host": "mini2", "cmd": "ssh", "error": "Could not resolve hostname"}] },
  "listeners": [{"port": 9223, "bind_addr": "127.0.0.1", "pid": 35984, "proc": "Google Chrome"},
                {"port": 3283, "bind_addr": "*", "pid": 34487, "proc": "ARDAgent"}],
  "endpoints": [{"port": 9223, "http": 200, "serving": true, "browser": "Chrome/155.0.8059.40", "peers": 1}],
  "host_software": {"chrome": {"plist_version": "157.0.8103.38",
                               "versions_current": "157.0.8103.38",
                               "framework_versions": [{"version": "155.0.8059.40", "mtime_epoch": 1791857193},
                                                      {"version": "156.0.8078.80", "mtime_epoch": 1793729270},
                                                      {"version": "157.0.8103.38", "mtime_epoch": 1793781174}]}},
  "chrome": [{"pid": 35984, "started_at": "2026-10-23T15:39:13-07:00", "cdp_port": 9223,
              "mounted_framework": "155.0.8059.40", "versions_current": "157.0.8103.38",
              "stale_binary": true}],
  "external_estab": [{"pid": 34351, "remote": "172.64.149.246:443", "classification": "undeclared",
                      "owner_command": "desktop-commander remote"}],
  "external_estab_coverage": {"rows": 38, "owner_resolved": 5, "owner_unresolved": 33,
                              "ps_rows_captured": 500, "ps_truncated": true},
  "remote_control_surfaces": [{"kind": "inbound", "port": 3283, "bind_addr": "*", "proc": "ARDAgent",
                               "declared_by": null},
                              {"kind": "outbound", "pid": 34351, "proc": "desktop-commander",
                               "mode": "remote", "declared_by": null},
                              {"kind": "tunnel", "label": "com.mastermind.studio-direct-tunnel.c2-personal-mini1",
                               "declared_by": null}],
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
- `bind_addr` non-nullable, and **every listener is classified**, not only CDP ports.
- **`framework_versions[]` contains real versions only.** The literal token `Current` is a symlink,
  not a version; a `version` field whose value is `Current` breaks any sort, count or join.
- **Each `chrome[]` row carries `mounted_framework` and `versions_current`**, so `stale_binary` is
  recomputable from its own row (rule 7).
- **`external_estab` ships with `external_estab_coverage`.** A count of `undeclared` rows is not a
  claim of coverage; the artifact states how many owners resolved and whether `ps` was truncated.
- **Verdicts occupy three keys**: `socket_verdicts[]`, `artifact_verdict`, `comparison_verdict`.

## Verdicts

**Socket:** `declared` | `baseline` | `undeclared` (refuse) | `bound_no_endpoint` (not registrable).
`baseline` may never admit a Chrome CDP listener nor a GUI-automation agent reachable off-box.

**Artifact:** `complete` | `refused: collection_incomplete` | `refused: schema_unsupported`.

**Comparison:** `comparable` | `refused: tool_changed`.

**Gate (blocks a launch):**

| gate | condition | meaning |
|---|---|---|
| `refused: unowned_bridge` | `bootout_authority` null and bridge `attached` or `armed` | nobody on record can stop the surface |
| `refused: stale_binary` | `mounted_framework != versions_current` | process executing a pre-update image |
| `refused: endpoint_absent` | `bound_no_endpoint` on a port the registry would bind | socket without an identity |
| `refused: unowned_remote_control` | any `remote_control_surfaces[]` entry with `declared_by: null` | a command path exists that no one on record authorised |

### Staleness, measured and corrected (mini1, 2026-11-08)

```
Versions on disk           155.0.8059.40 (Oct 12) → 156.0.8078.80 (Nov 2) → 157.0.8103.38 (Nov 3)
Current → 157.0.8103.38    bundle plist_version 157.0.8103.38
pid 34493  mounted 155.0.8059.40  → stale_binary true   (human default profile)
pid 35984  mounted 155.0.8059.40  → stale_binary true   (automation profile)
pids 10248/11186/14673/17802 mounted 157.0.8103.38 → false
```

Both stale processes started Oct 23 — after the 155 framework dir (Oct 12) and before the 156/157
updates. **The v1.6 predicate (`started_at` < mounted-framework mtime) therefore evaluated false and
admitted both.** That inversion is recorded here rather than quietly fixed: a gate that fails open
on its only two positive cases is worse than no gate, because it certifies them. `lsof` reports
zero `(deleted)` mappings on both, because Chrome retains old version dirs — the mapped framework
path is the only honest discriminator.

**Non-fire is unproven on this host.** All four non-stale processes started Nov 7, after the Nov 3
install, so they would pass *any* predicate including the broken one. A discriminating non-fire
needs a survivor — started before the install, mounted at `Current` — and none exists on mini1. The
acceptance item therefore asserts **fires on the real stale set** and requires a **synthetic
survivor row** for the non-fire half, or the item is stated as "non-fire unproven here".

### Remote-control surfaces

Three distinct command paths exist on the host that will hold posting credentials, and no seat
claims any of them: ARD inbound on `*:3283` (the only off-box-reachable listener); `desktop-commander
remote` at pid 34351, egressing to `172.64.149.246:443`; and the loaded labels
`com.mastermind.studio-direct-tunnel.c2-personal-mini1` / `-private` (pids 35946, 35949). The tool is
known to the org record; the **mini1 instance** is known to none. `remote_control_surfaces[]` carries
`declared_by`, and a null blocks admission.

## Sampling, not scalars

`connection_count` is bistable at heartbeat phase (2, 3, 3 within 17 s; Peekaboo's local port
moves once per keepalive tick). Fixtures assert the **persistent set** — `17665 → 9223` and the
`com.xg.proxyauth` child → `9333` — and any count comparison samples ≥ one `StartInterval` (60 s).

## Accepted fixture

**Pinned:** sweep **2026-11-08T09:44:47Z**, `script_sha256 9f7e2a55b52ff809562caeac3fd712321550a999aecad4e44ae84f687c7a78f8`,
manifest sha256 **`0d88c68abbd31a2f6dc5ed025544b89a4fe288c60550b4f130f6b2aa66ee6ea5`**, mini1 payload,
`hosts_returned: ["mini1"]`.

Read on the payload by this seat, first-hand:

- `chrome[]` 6 rows, **6/6 self-verifying**: 34493/35984 `mounted 155 / current 157 / stale true`;
  10248, 11186, 14673, 17802 `mounted 157 / current 157 / stale false`.
- `framework_versions` = three real versions; `Current` token stripped.
- `external_estab_coverage`: **rows 34, resolved 34, unresolved 0, ps_rows_captured 892,
  ps_truncated false**; 29 of the 34 are non-private. Coverage is stated, not inferred from prose.
- `listeners[]` carry `owner_command` for every port: `*:3283` ARDAgent; `45019` tunnel-client
  (`studio-direct-private`); `45018` studio-direct-mcp node; `52194`/`29979` Paper.app (GUI,
  loopback — not `baseline`, which is stock OS only, and not evidence of a command path).
- **`remote_control_surfaces[]` is EMPTY (0 entries) against four known surfaces.** Under rule 8
  that is a failed enumeration, not an absence: this pin satisfies items 12 and 15, and
  **does not satisfy item 16**.

**Superseded, not diffable:** `3b0f6eb9…` (pre-coverage; no owner_command on egress),
`dc13765d…`/`091652` (pre-row-fix), `5497ef0d…` (v1.5 pin, itself
mis-pinned as 2), `5458165275ab…`, `362919cc…`, `68589392…`.

## Acceptance evidence (required before this leaves draft)

1. Diff-rule unit tests: `declared` / `baseline` / `undeclared` / `bound_no_endpoint`.
2. `provenance` missing or `mutating: true` → refused.
3. The pinned fixture stored verbatim, asserting the persistent set.
4. Negative test: observer reports `undeclared`, never `known`.
5. `schema_version: 2` or newer registry revision → `refused: schema_unsupported`.
6. Non-empty `command_failures` / silent host → `refused: collection_incomplete`, never "no findings".
7. Allowlist entry missing `reason`/`added_by`, or `host_seed_sha` mismatch → refused.
8. Snapshot sha256 not matching the admission receipt → refused.
9. Two snapshots differing only in `sweep_script_sha256` → `refused: tool_changed`, no delta emitted.
10. Endpoint test: held socket + 404 → `bound_no_endpoint`, never an exposure.
11. Bridge test: null `bootout_authority` with bridge `attached` or `armed` → `refused: unowned_bridge`.
12. **Fire test:** rows 34493/35984 of the pinned fixture yield `refused: stale_binary`.
12b. **Non-fire test:** a **synthetic survivor row** (`started_at` before install,
    `mounted == versions_current`) must yield no refusal. Non-fire is unproven on real hardware.
13. Wildcard test: non-loopback listener with no declaration of record → `undeclared` in
    `socket_verdicts[]`, never omitted for being outside the CDP scope.
14. Sampling test: three runs spanning one `StartInterval`; assertion on the persistent set.
15. **Coverage test:** an `external_estab` block whose coverage is incomplete must emit
    `undeclared` **with** `external_estab_coverage`, and the report layer must never present
    "N undeclared" as if the owners were known.
16. **Remote-control test:** the array must contain the four known surfaces (ARD `*:3283`,
    `desktop-commander` remote, `studio-direct-tunnel`, `studio-direct-mcp`), each
    `declared_by: null` → `refused: unowned_remote_control`. A consumer meeting an **empty** array
    yields `refused: enumeration_incomplete`, never a pass. **Unsatisfied as of the v1.8 pin.**

Absent those sixteen, the observer is a document, not an artifact.

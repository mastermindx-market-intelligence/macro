# XG novelty observer — contract v2.0

Status: **specification, unbuilt**. Owning card: `t_2bb26bfe`. Author seat: engineering.
v2.0 fixes v1.9's arithmetic: the completeness identity summed **rows** across two tables that
share processes, so a correct enumeration failed it. It now operates on **distinct pids**, with a
stated precedence and a fifth vocabulary term (`forwarded`) assigned by owner role rather than bind
address. Pattern matching may **label** a row; it may never **remove** one. Nothing here grants permission, binds an account, or enables a runtime operation.

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
5. **Staleness is identity, not time.** `mounted_framework != versions_current` ⇒ stale. No clock,
   no timezone, `touch`-proof.
6. **A field with no consumer is a comment.** Every rule names the reader that acts on it. This cut
   both ways in one commit: `bind_addr` had no reader for six rounds, and `external_estab` shipped
   with no reader at all.
7. **A row must prove itself.** A verdict field is recomputable from its own row, not by joining a
   sibling object.
8. **An enumerated collection must prove its completeness, in three states, arithmetically.**
   - A **missing** key ⇒ `refused: enumeration_not_collected` (the collection never ran).
   - An **empty** array ⇒ `refused: enumeration_incomplete` (it ran, found nothing — possible, and
     must be justified by the cross-check).
   - A **populated** array with any `declared_by: null` ⇒ `refused: unowned_remote_control`.
   `payload.get(k, [])` collapses states one and two and is therefore banned. Completeness is then checked by **arithmetic on process identity, not row counts and not
   pattern matching**:

   ```
   U = distinct(pids ∈ listeners[]) ∪ distinct(pids ∈ non_loopback_egress[])
   every pid in U is assigned exactly one surface_class
   sum(surface_class buckets) == |U|
   rows_total = len(listeners) + len(non_loopback_egress)   # reported, never asserted
   ```

   Rows double-count processes — on the v1.9 pin, 12 listener rows are 11 pids and 42 egress rows
   are 17 pids, with 2 pids in both — so a row-sum identity (`12 + 25 = 37` against a true union of
   `11 + 17 − 2 = 26`) **fails on a correct enumeration**, and the double-counted pids are the
   load-bearing ones: the two Chrome instances, the tunnel-client, the sshd forward. Precedence,
   highest first: `inbound_remote > forwarded > remote_control_candidate > cdp > loopback_service >
   unclassified_egress`. **Pattern matching assigns a label; it never removes a row.** A pid in
   `non_loopback_egress` that matches no pattern lands in `unclassified_egress[]` — counted, named,
   joined to the union. That closes the asymmetry where a sixth mechanism that only egresses would
   appear as an anonymous public row and never join the surface array.

   **Classification is by owner role, never by bind address.** `127.0.0.1:4141` is loopback-bound on
   this host and is still one end of an SSH forward — `loopback_service` would launder the single
   most volatile mechanism on the box, the one a third party creates and destroys at will.

## Snapshot contract

Pure input for the harness: no import from `tools/xguerrilla/`, no shared helper module.

```jsonc
{
  "schema_version": 1,
  "host": "mini1",
  "taken_at": "2026-11-08T09:44:47Z",
  "observer": "hermes",
  "provenance": {
    "ssh_target": "mini1",
    "commands": ["launchctl print", "lsof -nP -iTCP -sTCP:LISTEN", "ps axo pid,ppid,lstart,command",
                 "curl /json/version", "lsof -p <pid> (framework map)"],
    "tools": {"macos": "27.0 (26A428)", "lsof": "4.91"},
    "sweep_script_sha256": "9f7e2a55b52ff809562caeac3fd712321550a999aecad4e44ae84f687c7a78f8",
    "mutating": false
  },
  "collection_status": "complete",
  "collected": { "hosts_attempted": ["mini1","mini2","mini3","mini4"], "hosts_returned": ["mini1"],
                 "commands_run": [{"cmd": "lsof -nP -iTCP -sTCP:LISTEN", "exit": 0}],
                 "command_failures": [{"host": "mini2", "cmd": "ssh", "error": "Could not resolve hostname"}] },
  "listeners": [{"port": 9223, "bind_addr": "127.0.0.1", "pid": 35984, "proc": "Google Chrome",
                 "owner_command": "…/Google Chrome --user-data-dir=…", "surface_class": "cdp"},
                {"port": 3283, "bind_addr": "*", "pid": 34487, "proc": "ARDAgent",
                 "owner_command": "/System/Library/CoreServices/RemoteManagement/ARDAgent.app/…",
                 "surface_class": "inbound_remote"},
                {"port": 4141, "bind_addr": "127.0.0.1", "pid": 87248, "proc": "sshd-sess",
                 "owner_command": "sshd-session: mini1", "surface_class": "remote_control_candidate"}],
  "endpoints": [{"port": 9223, "http": 200, "serving": true, "browser": "Chrome/155.0.8059.40", "peers": 1}],
  "host_software": {"chrome": {"plist_version": "157.0.8103.38", "versions_current": "157.0.8103.38",
                               "framework_versions": [{"version": "155.0.8059.40"}, {"version": "156.0.8078.80"}, {"version": "157.0.8103.38"}]}},
  "chrome": [{"pid": 35984, "started_at": "2026-10-23T15:39:13-07:00", "cdp_port": 9223,
              "mounted_framework": "155.0.8059.40", "versions_current": "157.0.8103.38", "stale_binary": true}],
  "external_estab": [{"pid": 34351, "remote": "172.64.149.246:443", "classification": "undeclared",
                      "owner_command": "desktop-commander remote", "address_class": "public"}],
  "external_estab_coverage": {"rows": 34, "owner_resolved": 34, "owner_unresolved": 0,
                              "public_rows": 25, "loopback_rows": 9, "unparseable_rows": 0,
                              "classification_histogram": {"undeclared": 34},
                              "ps_rows_captured": 892, "ps_truncated": false},
  "remote_control_surfaces": [{"kind": "inbound", "port": 3283, "proc": "ARDAgent", "declared_by": null}],
  "remote_control_surfaces_coverage": {"expected": 5, "enumerated": 5},
  "unclassified_listeners": [],
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
- **Every surface row carries `surface_class` as a field**, not inside a display string. The v2.0
  pin's rows encode it as `"*:3283 (inbound_remote)"`, which forces a consumer to regex human prose
  to recover a machine field — rule 7 one layer down, the same failure as `payload.get(k, [])`.
- `forwarded` surfaces carry `direction: "local" | "remote" | "unknown"` — and `unknown` is the only
  honest value for a session this host did not launch (see *Direction is not recoverable*).
- `unclassified_egress[]` sits beside `unclassified_listeners[]`; both are counted rows, never
  drops.
- `bind_addr` non-nullable; every listener classified, not only CDP ports.
- `framework_versions[]` holds real versions only — `Current` is a symlink token and breaks joins.
- Each `chrome[]` row carries `mounted_framework` and `versions_current`.
- **`external_estab_coverage` carries the split and its predicate.** Loopback/private =
  `127.0.0.0/8`, `::1`, `10/8`, `172.16/12`, `192.168/16`, `169.254/16`, `fc00::/7`; IPv6 peers are
  bracket-normalised before parsing. A count without a written predicate is an opinion — this round
  produced two different public counts for one payload from exactly that gap (25 vs 29; the 4-row
  difference was bracket-framed IPv6, not traffic).
- **Verdicts occupy three keys**: `socket_verdicts[]`, `artifact_verdict`, `comparison_verdict`.

## Verdicts

**Socket:** `declared` | `baseline` | `undeclared` (refuse) | `bound_no_endpoint` (not registrable).

**Artifact:** `complete` | `refused: collection_incomplete` | `refused: schema_unsupported`.

**Comparison:** `comparable` | `refused: tool_changed`.

**Gate (blocks a launch):**

| gate | condition | meaning |
|---|---|---|
| `refused: unowned_bridge` | `bootout_authority` null, bridge `attached` or `armed` | nobody on record can stop the surface |
| `refused: stale_binary` | `mounted_framework != versions_current` | process executing a pre-update image |
| `refused: endpoint_absent` | `bound_no_endpoint` on a bound port | socket without an identity |
| `refused: enumeration_not_collected` | key missing | the collection never ran |
| `refused: enumeration_incomplete` | array empty, or bucket sum ≠ row count | ran, incomplete or unexplained |
| `refused: unowned_remote_control` | any surface with `declared_by: null` | a command path no one authorised |

### Staleness, measured

```
disk: 155.0.8059.40 (Oct 12) → 156.0.8078.80 (Nov 2) → 157.0.8103.38 (Nov 3); Current → 157
pid 34493 mounted 155 → stale true (human default profile)
pid 35984 mounted 155 → stale true (automation profile)
pids 10248/11186/14673/17802 mounted 157 → false
```

Both stale processes started Oct 23, after the 155 dir and before 156/157 — so the v1.6
`started_at`-vs-mounted-mtime predicate evaluated **false** and admitted both. The inversion is
recorded here rather than quietly fixed. `lsof` reports zero `(deleted)` mappings on both: Chrome
retains old version dirs, so the mapped framework path is the only honest discriminator.
**Non-fire is unproven on this host** — all four non-stale processes started Nov 7, after the
install, and would pass any predicate including the broken one.

### Surfaces the host actually carries

`*:3283` ARDAgent (inbound, off-box reachable) · `34351` desktop-commander `remote` → egress
`172.64.149.246:443` · `35946` tunnel-client `studio-direct-private` (`127.0.0.1:45019` + egress
`172.66.0.243:443`) · `35949` studio-direct-mcp node (`127.0.0.1:45018`) · `87248` **`sshd-session`
forward on `127.0.0.1:4141`** · plus `4188`/`4290` `preview-server.mjs` and `4190` `vite --host`
serving from `/private/tmp/aerlor-r5-design-first`. Twelve listener rows, six mechanisms, every one
now named by owner string and carried in a bucket.

### Direction is not recoverable, so prevention is the control

`-L` and `-R` both produce a listening socket owned by `sshd`; the difference lives in the **client's**
argv, which never appears in a server-side census. A `direction` field will therefore read `unknown`
for every third-party session, forever — more enumeration cannot close it. Enumeration is detection;
the only prevention available on a credential-bearing host is configuration: `AllowTcpForwarding no`
(or `no` for the automation account), decided by whoever owns the host policy. A per-session `who`
tells you who is logged in now; it does not tell you what the forward was for.

## Sampling, not scalars

`connection_count` is bistable at heartbeat phase (2, 3, 3 in 17 s). Egress rows move with workload
(38 → 34 between runs). Fixtures assert the **persistent set** and the **invariants**
(`owner_resolved == rows`, `ps_truncated == false`, bucket sum identity), never a raw count.

## Accepted fixture

**Pinned:** sweep **2026-11-08T10:01:53Z**, `script_sha256 ba55e88e83d64beabeec2b95fe121e5dba10e6591486c2b08477591fd4d4f47f`,
manifest **`sweep-manifest-2026-11-08T100153.929843_0000.json`**, sha256
**`18524c3df5063cc7ba656339ac30491fb98b6754be1530bcd3818d316bf22be1`**, `hosts_returned: ["mini1"]`.
Supersedes `0d88c68a…` (v1.9 pin), which lacked `remote_control_surfaces` entirely.

Read first-hand on the payload: `remote_control_surfaces[]` **present, 5 rows, `declared_by: null`
on all five**, with `evidence{listener[], egress[]}` per row; `remote_control_surfaces_coverage
{expected 5, enumerated 5}`; `unclassified_listeners: []`; `surface_class` histogram
`{loopback_service 5, cdp 3, remote_control_candidate 2, inbound_remote 1, forwarded 1}` = 12 rows,
unclassified 0; coverage `{rows 42, resolved 42, unresolved 0, public_rows 29, loopback_rows 13,
unparseable_rows 0, histogram {undeclared: 42}, ps_rows_captured 896, ps_truncated false}`;
`listeners` 12 rows / **11 distinct pids**, `non_loopback_egress` 42 rows / **17 distinct pids**,
**union 26**, intersection 2 — so the v1.9 row-sum identity would have computed 29 against a true 26
on this very pin. Chrome staleness unchanged (34493/35984 true, four false).

**Gaps this pin does not close, and must not pretend to:** `remote_control_surfaces` is **absent**
in every payload to date (`093059` and `094447` both lack the key), and the coverage block carries
no public/private split. This pin therefore satisfies items 12 and 15 and **does not satisfy item 16**.

**Superseded, not diffable:** `3b0f6eb9…` (pre-coverage), `dc13765d…`/`091652` (pre-row-fix),
`5497ef0d…` (v1.5 pin, itself mis-pinned as 2), `5458165275ab…`, `362919cc…`, `68589392…`.

## Acceptance evidence (required before this leaves draft)

1. Diff-rule unit tests: `declared` / `baseline` / `undeclared` / `bound_no_endpoint`.
2. `provenance` missing or `mutating: true` → refused.
3. The pinned fixture stored verbatim, asserting the persistent set.
4. Negative test: observer reports `undeclared`, never `known`.
5. `schema_version: 2` or newer registry revision → `refused: schema_unsupported`.
6. Non-empty `command_failures` / silent host → `refused: collection_incomplete`.
7. Allowlist entry missing `reason`/`added_by`, or `host_seed_sha` mismatch → refused.
8. Snapshot sha256 not matching the admission receipt → refused.
9. Two snapshots differing only in `sweep_script_sha256` → `refused: tool_changed`, no delta emitted.
10. Endpoint test: held socket + 404 → `bound_no_endpoint`, never an exposure.
11. Bridge test: null `bootout_authority` with bridge `attached` or `armed` → `refused: unowned_bridge`.
12. **Fire test:** rows 34493/35984 → `refused: stale_binary`.
12b. **Non-fire test:** synthetic survivor row (`started_at` before install, `mounted == current`) →
    no refusal. Non-fire is unproven on hardware.
13. Wildcard test: non-loopback listener with no declaration → `undeclared` in `socket_verdicts[]`.
14. Sampling test: three runs spanning one `StartInterval`; assertion on the persistent set.
15. **Coverage test:** incomplete coverage emits `undeclared` **with** the coverage block and the
    written predicate; the report layer may never present "N undeclared" as if owners were known.
16. **Remote-control test, three states plus the sshd case:** missing key →
    `enumeration_not_collected`; `[]` → `enumeration_incomplete`; populated with `declared_by: null`
    → `unowned_remote_control`. An **`sshd-session`-owned listener must be one of the test rows**,
    classified `forwarded` by owner role with `direction: "unknown"`. Satisfaction requires the
    **pid-union** identity (`sum(buckets) == |U|`) plus `unclassified_listeners[]` **and**
    `unclassified_egress[]`, and `surface_class` as a row field rather than inside `evidence[]`
    strings. **Satisfied in substance by the v2.0 pin** (5/5 surfaces, class histogram complete,
    unclassified empty); **still failing the field-level form** until `surface_class` moves out of
    the `"*:3283 (inbound_remote)"` display strings.

Absent those sixteen, the observer is a document, not an artifact.

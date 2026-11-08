# XG novelty observer — contract v2.2

Status: **specification, unbuilt**. Owning card: `t_2bb26bfe`. Author seat: engineering.
v2.2 removes `excluded_pids` as a category. An exclusion list is where a banned predicate goes to
survive: the first run of it dropped two CDP-attached processes under the label
`private_only_egress` — the loopback filter that dropped Peekaboo, renamed and applied to pids
instead of rows. Classification is now total, and CDP attachment is derived, not pattern-matched.

v2.1 recorded the `relay` bucket, splits `direction` from `direction_source`, fixes an example
fixture that contradicted the precedence it sat above (both my error, caught by @chief-of-staff),
and states which attribution sources do not work so nobody re-runs them.

v2.0 fixed v1.9's arithmetic: the completeness identity summed **rows** across two tables that
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

   **The egress half is never scoped to public peers.** A remote-control mechanism that only
   touches loopback is still a remote-control mechanism — the first run of this derivation filtered
   egress to public peers and dropped **Peekaboo (`17533`, peer `127.0.0.1:9223`)**, the very armed
   bridge `refused: unowned_bridge` exists for. Loopback peers are evidence, not exclusions.

   **`surface_union.total` must be reproducible by a second party.** Measured on the v2.1 pin:
   11 listener pids, 23 egress pids, so the broad predicate gives **30** and the loopback-excluding
   predicate gives **26** — while the artifact reports **27**. Neither written form reproduces the
   headline, and nothing in the block lets a reader bridge the gap. That is the 25-vs-29 public-count
   failure all over again: a number is only an invariant when its membership can be reconstructed.
   The block must therefore carry `pids: [...]` (or a `pid_set_sha256` over it) plus
   `excluded_pids: [{pid, reason}]`, so `|histogram| == |pids|` is checkable and every exclusion is
   named. A total of 27 with 30 candidates and no exclusion list is an opinion.

   **There are no exclusions.** Every pid in the broad union receives a class; `unclassified_egress`
   is the catch-all and `local_service` names a daemon with no command role (Tailscale's local API).
   `excluded_pids` is deleted, because on its first run it removed `17665` — **`chrome-devtools-mcp`,
   ESTABLISHED to `127.0.0.1:9223`** — and `76156` — **the Playwright driver from
   `/Users/mini1/xg/venv`, ESTABLISHED to `127.0.0.1:9333`** — under the reason `private_only_egress`.
   Both are control surfaces by every definition this contract has; the exclusion list is how the
   Peekaboo defect survives a fix that names it.

   **CDP attachment is derived, not matched.** Any pid appearing client-side in `cdp_sessions[]` is
   `remote_control_candidate`, full stop — the row already proves a process is talking to a debug
   port. Name patterns are a *supplement* for mechanisms that never touch CDP; they may add a row,
   never subtract one. This is the structural answer to the pattern-vs-role question: the strongest
   evidence of a control surface is a live connection to one, and it is already in the payload.

   **`sshd-session`-owned egress is a `relay` bucket**: it is this host's own forwarding and jump
   traffic, i.e. the census measuring itself. Three `ssh -W` jumps from the workstation inflate
   `non_loopback_egress` by exactly the number of jumps open at capture time, which is why the row
   count moved 34 → 40 → 42 → 47. `relay` rows are counted and named, never removed — and a relay
   row promoted to `forwarded` by precedence keeps its own `surface_class`, so the array length and
   the bucket count can differ by an explainable one instead of an unexplained one.

   **Classification is by owner role, never by bind address.** `127.0.0.1:4141` is loopback-bound on
   this host and is still one end of an SSH forward — `loopback_service` would launder the single
   most volatile mechanism on the box, the one a third party creates and destroys at will.

## Snapshot contract

Pure input for the harness: no import from `tools/xguerrilla/`, no shared helper module.

```jsonc
{
  "schema_version": 1, "host": "mini1", "taken_at": "2026-11-08T10:14:25Z", "observer": "hermes",
  "provenance": {"ssh_target": "mini1", "mutating": false,
                 "sweep_script_sha256": "4d53d155812810f3d8883a3d1b96647ea15e00a12a9e4583b1d275b73dd1ca18"},
  "collection_status": "complete",
  "collected": {"hosts_attempted": ["mini1","mini2","mini3","mini4"], "hosts_returned": ["mini1"],
                "command_failures": [{"host": "mini2", "error": "Could not resolve hostname"}]},
  "listeners": [{"port": 4141, "bind_addr": "127.0.0.1", "pid": 87248, "proc": "sshd-sess",
                 "owner_command": "sshd-session: mini1", "surface_class": "forwarded",
                 "direction": "unknown", "direction_source": "server_side_census"},
                {"port": 3283, "bind_addr": "*", "pid": 34487, "proc": "ARDAgent",
                 "owner_command": "…/ARDAgent.app/Contents/MacOS/ARDAgent",
                 "surface_class": "inbound_remote"}],
  "relay_egress": [{"pid": 75729, "owner_command": "sshd-session: mini1", "surface_class": "relay",
                    "peers": ["100.105.179.12:22", "[fe80:7::cc9:fb10:443d:471c]:58942"]}],
  "unclassified_egress": [{"pid": 34523, "owner_command": "…", "surface_class": "unclassified_egress"}],
  "unclassified_listeners": [],
  "remote_control_surfaces": [{"pid": 17533, "surface_class": "remote_control_candidate",
                               "owner_command": "…/Peekaboo --background-bridge-host",
                               "listener_surfaces": [], "egress_peers": ["127.0.0.1:9223"],
                               "declared_by": null},
                              {"pid": 87248, "surface_class": "forwarded",
                               "listener_surfaces": [{"port": 4141, "surface_class": "forwarded",
                                                      "direction": "unknown",
                                                      "direction_source": "server_side_census"}],
                               "egress_peers": ["[fe80:7::cc9:fb10:443d:471c]:50447"],
                               "declared_by": null}],
  "remote_control_surfaces_coverage": {"expected": 6, "enumerated": 6,
    "identity": "distinct pids in {inbound_remote, forwarded, remote_control_candidate} ∪ any egress owner with a remote-control role, public or loopback"},
  "surface_union": {"total": 27, "axis": "surface_class", "denominator": 27,
    "histogram": {"forwarded": 1, "unclassified_egress": 10, "relay": 4,
                  "remote_control_candidate": 4, "loopback_service": 4,
                  "inbound_remote": 1, "cdp": 3},
    "rows_total_listeners": 12, "rows_total_egress": 47},
  "listener_surface_histogram": {"axis": "surface_class", "denominator": 12,
    "histogram": {"cdp": 3, "inbound_remote": 1, "remote_control_candidate": 2,
                  "loopback_service": 5, "forwarded": 1}},
  "external_estab_coverage": {"collected": true, "host_scope": "mini1", "rows": 47,
    "owner_resolved": 47, "owner_unresolved": 0, "public_rows": 30, "loopback_rows": 17,
    "unparseable_rows": 0, "declaration_histogram": {"undeclared": 47},
    "ps_rows_captured": 902, "ps_truncated": false}
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

### Direction, and where it comes from

`-L` and `-R` both leave a listening socket owned by `sshd`; the distinction lives in the client's
argv, which a server-side census never sees. So direction is a two-field claim:

```
direction:        "local" | "remote" | "unknown"
direction_source: "client_argv_observed" | "server_side_census"
```

`server_side_census` ⇒ `direction: "unknown"`, always. The pair was recovered for real on this
estate: mini1 `87248` ↔ workstation `ssh -N -o ExitOnForwardFailure=yes … -R 127.0.0.1:4141:127.0.0.1:4141 mini1`,
parent `glm_tunnel.sh` from a September handoff kit, live ~13 days. `-R` means **mini1's** 4141 is an
ingress to the **workstation's** loopback listener — trust inverted: the credential-bearing automation
box can reach a service bound to the developer machine. Enumeration could never have said that;
client-side observation did.

**Corollary that matters more than the field:** for a session this host did not launch, direction is
unrecoverable *by construction*, so the control cannot be enumeration. It is configuration —
`AllowTcpForwarding no` for the automation account — plus the discipline that any forward we create
gets a card and an expiry.

### Attribution sources that do not work

`who -u` on mini1 reports only `console` and `ttys000` (both resident since Oct 23, the console idle
16 days). `last` shows **none** of the five live `sshd` sessions. macOS sshd does not record ssh
logins in utmp here, so **utmp-based attribution is a dead end** — do not write a test that depends
on it. Live sessions are attributable by `ps` **ppid pairing** (`76000 zsh → 76357 sshd-session`),
which the payload already carries, and the observer excludes itself by parentage rather than by
guessing a pid.

## Sampling, not scalars

`connection_count` is bistable at heartbeat phase (2, 3, 3 in 17 s). Egress rows move with workload
(38 → 34 between runs). Fixtures assert the **persistent set** and the **invariants**
(`owner_resolved == rows`, `ps_truncated == false`, bucket sum identity), never a raw count.

## Accepted fixture

**Pinned:** sweep **2026-11-08T10:18:45Z**, `script_sha256
2448881a890b1535451650140dd8838a054f2dbd8acf09cdb1db844df16d05c3`, manifest
**`sweep-manifest-2026-11-08T101845.743503_0000.json`**, sha256
**`dc2df0f37eea5015f1145fc45a730f71316331ebc70f2d035b7aa621f92334cd`**,
`hosts_returned: ["mini1"]`. Supersedes `18524c3d…` (5 surfaces — **missing the Peekaboo bridge**)
and `0d88c68a…` (no `remote_control_surfaces` at all).

Read first-hand on the payload: `remote_control_surfaces[]` **6 rows, `declared_by: null` on all
six**; `surface_union {total 27, pids 27, sum(histogram) 27}` — **the identity is now reproducible**,
and `declaration_histogram {axis, denominator, counts {undeclared: 43}}` can no longer be compared
against a 27-pid union or a 12-row listener table by accident; `relay_egress` 4 rows with
`promoted_to` on the promoted row (87248: relay → forwarded), so the array-vs-bucket gap is explained
where it occurs; `remote_control_surfaces_coverage.identity` no longer contains the word that dropped
Peekaboo; coverage `{rows 43, resolved 43, public 28, loopback 15, unparseable 0, ps 899, truncated
false, collected true, host_scope "mini1"}`; link-local peer uniformity across every relay row holds
in this run too.

**This pin passes reproducibility and fails role:** the 27 is exactly `30 − 3`, and the three
exclusions include two CDP-attached processes. Honest summary: an artifact that can be audited is not
the same as an artifact that is right, and this one is now auditable enough to show its own error.

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
    classified `forwarded` by owner role with `direction`/`direction_source` present. Satisfaction
    requires the **pid-union** identity, `unclassified_listeners[]` **and** `unclassified_egress[]`,
    the egress half **not** scoped to public peers, an enumerable `surface_union.pids` with
    `excluded_pids[]`, and **`surface_class` on every `remote_control_surfaces[]` row** — not only on the `listeners[]` rows it nests. **Satisfied in
    substance by the v2.1 pin (6/6, all null); still failing form**: the six surface rows carry no
    `surface_class` of their own, and `remote_control_surfaces_coverage.identity` still says
    "public egress owners", the wording that excluded Peekaboo.
17. **No-exclusions test:** no pid appears in an `excluded_pids`-shaped list. The broad union is
    total; every member carries a class. Two named regression rows: `17665` (`chrome-devtools-mcp`
    → 9223) and `76156` (Playwright, `xg/venv` → 9333) must both appear as
    `remote_control_candidate`, derived from `cdp_sessions[]`.
18. **Census-self-noise test:** with `relay` bucketed, `rows_total_egress` is stable across two
    consecutive runs taken with no workload change, and every `relay` row names its peers. This is a
    test of the census, not an invariant in the artifact — row counts remain workload facts.
19. **Per-host coverage:** every coverage ratio names its `host_scope`; a multi-host ratio may not be
    computed from a single-host block, and an unreachable host appears as
    `collected: false, reason: collection_incomplete`, never as zero.

Absent those sixteen, the observer is a document, not an artifact.

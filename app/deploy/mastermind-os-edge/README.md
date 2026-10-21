# Mastermind OS public-origin deployment input

This directory pins the asset input used by the `mcp.mastermind-x.com` site in
`../Caddyfile`. The gateway, request authorization, Executive opt-in and renderer
remain owned by Mastermind. Macro owns the base Caddyfile that its updater
installs. This change adds the missing host to that existing source.

## Source and installed-byte provenance

| Input | Identity |
| --- | --- |
| Mastermind renderer and template | `b66e64ad57b50f77253eeacf62ac72dc165a50aa` |
| Renderer | `ops/executive_os/os_public_edge.py` |
| Template | `ops/executive_os/os_public_edge.caddy.template` |
| Retained installed MCP release | `91c1cac5a20a01f4bf1ac9e92e55613fd4640e1f` |
| Nine-file manifest snapshot SHA-256 (indented JSON) | `3fc4a5f952afa87144a4f30dcbdf10aa3e93de3b289add8906e921b9de7e2282` |
| Installed raw manifest SHA-256 (compact JSON) | `98ae8aad4b6ae16e0ef60361cc3d0b4ac8df9e21f3b9f3026eee4c4d015c4b48` |
| Rendered host block SHA-256, including final newline | `9c6965fb31f296fbc8fb0b5813075ee27763021d58561930430ced270de63744` |
| Qualified Macro baseline | `a2c2930ad3611e8137054b8f732243f935256060` |
| Baseline Caddyfile SHA-256 | `91e6670d68ad69235dc3f80088c3a69ca930ee8a3f9a4ae24ecd74f8b3e7e959` |

The rendered bytes were originally staged from Mastermind `c7867a45f76c1c2ec31ce3408e86781bb76c94fa`.
The renderer/template and their relevant inputs are unchanged at the pinned
Mastermind revision above. The manifest is a retained, sealed deployment input
for the installed release; it is not evidence that a newer build is installed.
Its nine rows retain exact paths, byte counts, MIME types and SHA-256 digests.
A fresh October 21 read verified all nine installed regular files (root-owned,
mode 0444), byte counts, digests and canonical MIME types. The installed manifest
uses compact JSON; this snapshot uses indented JSON. Their parsed values are
identical, with canonical value SHA-256
`af739803551d254a8bb67dcf751dc180da5df3b72950f81a7e9f31d7a59a96b2`.
The MCP service remained running at PID 85849, and its configuration digest
`7604f1e966d5a20eab1361c88268ee001006eb0307dba4c9d3e17e454eadcf1d`
matched the earlier disabled-Executive-opt-in receipt.
Future publication must use the canonical Mastermind renderer and its manifest
qualification. Do not hand-expand this allowlist or create a second publisher.

References: [Mastermind parent #1143](https://github.com/mastermindx-market-intelligence/Mastermind/issues/1143),
[canonical renderer](https://github.com/mastermindx-market-intelligence/Mastermind/blob/b66e64ad57b50f77253eeacf62ac72dc165a50aa/ops/executive_os/os_public_edge.py),
[transition contract](https://github.com/mastermindx-market-intelligence/Mastermind/blob/b66e64ad57b50f77253eeacf62ac72dc165a50aa/docs/OS_PUBLIC_EDGE_TRANSITION.md).

## Route contract

The exact hostname forwards only the renderer's enumerated GET paths and three
Executive POST paths to the existing loopback relay `127.0.0.1:49152`. Asset
paths name the retained installed bytes. The POST body limit adapts to 64,000
bytes. The final route aborts every unmatched request.

Both proxy branches strip the renderer's forwarded identity headers and set the
canonical Host, HTTPS scheme and loopback forwarded address. The site does not
synthesize an authenticated user or promote a bearer. Gateway authentication and
the disabled Executive opt-in remain independent controls. Merely publishing
the route does not enable submit, install a gateway release, launch a worker or
prove that newer Workspace endpoints exist in the old installed release.

No existing Caddyfile byte is changed before the appended site. The production
unit continues to select `/etc/caddy/Caddyfile.combined`, importing the base,
`livingstonpan.caddy` and `mm-travel.caddy`. Those files and the unit are outside
this change.

## Qualification and its limits

[The retained qualification receipt](qualification.json) binds the source and
manifest hashes, the missing-host RED, all 17 passing focused cases, installed
asset checks, and the unchanged VPS before/after state.

`tests/test_os_public_edge_caddy.py` invokes the actual Caddy adapter with the
same stdin filename for the original configuration and the candidate. It checks:

- One exact host, its complete route structure, literal paths and methods, the
  sole loopback upstream, forwarded-header rules, body-limit order and abort.
- Preservation of the entire existing adapted configuration after removing only
  that host and its one exact TLS subject. Every array retains its order.
- Consistent bijective renaming of Caddy-generated `Route.group` identifiers
  across each server's full route and error tree, including nested routes.
  The new site's group cannot collide with an existing group.
- Rejection of deliberate route/policy reordering, unrelated TLS subjects,
  group collisions, wildcard assets, extra methods, changed upstreams, forged
  forwarded identity, a larger body limit and a permissive fallback.

Caddy 2.11.4 also adapted the actual VPS combined-file shape with the existing
imports. The source-only operation used stdin; before/after file and live-config
hashes matched. Neither adaptation starts a server, obtains a certificate,
reloads a service nor proves public reachability.

The previously unresolved equivalence report omitted one expected difference:
Caddy adds `mcp.mastermind-x.com` beside `admin.mastermind-x.com` in the existing
public automatic-certificate policy. The internal-issuer policy is unchanged.
The comparator removes only the new exact subject, preserving policy order and
every other TLS setting. It never ignores the TLS subtree or changes to other
hosts. This establishes a conservative structural proof, not a general solver
for equivalent Caddy programs.

## Release state: DRAFT / HOLD-FOR-SOL

**Do not merge or arm this deployment-bearing configuration until Sol releases
the concrete dependency gate.** Macro's current updater can install a changed
base Caddyfile, so merging to the default branch can publish it.

An October 21 read observed the root cron entry invoking the installed updater
every three minutes. Both its installed and repository copies had SHA-256
`dbfa190fe81c47149050fbdfec2fd90c34fb2cd93bb2b4db5b467465532ea4d9`,
with the old reload-or-restart block and without the protective deferral. No
scheduled/manual entry was closed, and no complete old-image drain was proved.

[Macro #9340](https://github.com/mastermindx-market-intelligence/macro/pull/9340)
owns the updater protection and the unresolved scheduled/manual entry and
old-process-inode custody. Its source tests alone do not establish that every
actual entry uses the protective code. This PR does not modify or replace that
work. Keep this change Draft, without `merge-on-green` or native auto-merge.

Sol's release condition is: consume #9340's actual entry/custody proof, reconcile
the installed gateway release/manifest and current combined Caddy inputs, and
approve the ordinary existing-owner deployment and rollback. Public certificate
issuance, strict origin SNI, authenticated GET behavior and required public
negative-path proofs must then be verified separately through the existing
deployment authority. No TLS verification weakening, alternate startup drop-in,
out-of-band host patch or replacement updater is authorized by this artifact.

The original CODEX issuer remains EFFECT_UNKNOWN / DO_NOT_RETRY; the original
Business operation remains NOT_SUBMITTED. R1 renewal/install/acceptance and the
held #1515, #1473 and #1542 actions remain outside this source change.

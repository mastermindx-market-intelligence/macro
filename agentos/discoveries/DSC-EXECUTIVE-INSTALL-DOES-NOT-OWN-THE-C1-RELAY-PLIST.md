---
key: EXECUTIVE-INSTALL-DOES-NOT-OWN-THE-C1-RELAY-PLIST
claim: >
  An Executive OS install writes the `control`, `worker.codex` and `backup` launchd plists to the installed
  generation but NEVER the C1 `sol-state-relay` plist, whose generation is separately owned by
  `ops/executive_os/prepare-c1-sol-state-relay.sh`; after the 2026-09-17 21:20Z install the installed plist
  generations read `8b231e82` for control/worker.codex/backup, `4c148709` for the C1 relay plist and
  `46bea208` for MCP, so there is no single "installed generation" for the Executive OS.
falsifier: >
  On the install host, read each Executive OS plist's installed release pointer before and after a recorded
  install run: if the C1 `sol-state-relay` plist moves with the control plist (or `install.sh` is found
  writing the relay plist path), this claim is false. Acceptance of the install does not depend on this
  read; only the "separately owned" claim does.
so_what: >
  Never compute one installed generation for the Executive OS: read each plist. A generation-vector read
  that assumes the C1 relay follows the control install will report a stale relay as upgraded by a merge
  that never touched it, and will misattribute a genuinely stale relay to an install failure. Anyone
  reconciling a relay/control generation split reads `prepare-c1-sol-state-relay.sh`'s ownership before
  proposing an install-side repair.
kind: landmine
verified_at: 2026-09-17
verified_by: >
  Sol ruling edge `1789680829.787409`, which records the post-install plist generation vector
  (`control`/`worker.codex`/`backup` = `8b231e82`, C1 `sol-state-relay` = `4c148709`, MCP = `46bea208`) and
  states that `install.sh` never writes the relay plist while `ops/executive_os/prepare-c1-sol-state-relay.sh`
  owns it. Carried, not re-run: this records-only fold read no host plist and ran no service command.
scope:
  - mastermind
  - ops/executive_os/install.sh
  - ops/executive_os/prepare-c1-sol-state-relay.sh
confidence: verified
---

## Why the generations split

The Executive OS install ceremony owns the lifecycle of the `control`, `worker.codex` and `backup`
launchd services: an install materializes their plists pointing at the newly installed release tree. The
C1 `sol-state-relay` plist is outside that set. Its writer is
`ops/executive_os/prepare-c1-sol-state-relay.sh`, a separate script with its own invocation, so a
successful install leaves the relay on whatever generation last prepared it — `4c148709` in the
2026-09-17 observation — while the control-side plists move to the installed generation `8b231e82`. MCP
is a third, separately recorded generation (`46bea208`).

## What it costs to get wrong

Two failures follow from collapsing the vector into one number. First, a reconciliation that reads the
control plist and reports "the Executive OS is on `8b231e82`" overstates the relay's currency, which is
exactly the class of overclaim a currentness repair exists to remove. Second, when the relay legitimately
disagrees with the control generation, a session that does not know the ownership split reads it as an
install defect and proposes re-running the install or repointing the relay — an install/relay action
nobody authorized.

## Currentness

2026-09-17: the install of generation `8b231e82` completed (rc=0, verify ok) and Sol accepted the state as
UNARMED / STOPPED with the services kept stopped. The generation vector above is the accepted
post-install vector; it is not a claim that the services are running or armed.

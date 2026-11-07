---
key: MCP-GENERATION-HAS-NO-ARMED-PUBLISHER-ON-MASTER
claim: >
  Protected master (read at 877b1e7f, 2026-10-05) carries no armed writer of the installed MCP
  generation: ops/executive_os/install.sh never touches config/executive-mcp.json, the
  com.mastermind.executive.mcp.plist or network-runtimes; the only generation-shaped source is
  ops/executive_os/release_owner_publication_plan.py, a permanently disarmed planner that compiles
  the exact MCP install document (validated by executive_mcp_entry.validate_document) and detached
  payloads as requirements for a later privileged publisher and, by its own docstring, neither
  inspects nor mutates a host; every other reference (control_plane/executive_installed_peer.py,
  control_plane/executive_release_observation.py, ops/executive_os/coo_principal_host.py,
  install_mosyle_credential.py, executive_mcp_entry.py) only reads or observes the generation.
  The live generation on the M2 host (release_sha 5b244a2b, plist WorkingDirectory the same
  release) was therefore published out-of-band by the host owner's ceremony.
falsifier: >
  At protected master run
  `git grep -n -E 'executive-mcp\.json|executive_mcp_install|com\.mastermind\.executive\.mcp\.plist|network-runtimes' -- ops scripts control_plane integrations`
  and `grep -n -E 'executive-mcp|mcp\.plist|network-runtimes' ops/executive_os/install.sh`.
  Falsified when any hit writes those paths (write_text, open-for-write, os.replace, plutil or
  launchctl bootstrap under /Library/Application Support/MastermindExecutive), when install.sh
  gains MCP generation handling, or when release_owner_publication_plan.py loses its
  release_commit_remains_permanently_disarmed predicate and starts mutating a host.
so_what: >
  Any MCP-only refresh (Mastermind #1219 restart-gateway --expected-sha X) qualifies a generation
  that only the host owner's out-of-band ceremony publishes; it is lawful only after that
  publication receipt for X, never as a substitute for it. The release/host owner must record the
  pairing in one sentence (generation for X = the disarmed planner's compiled document for X,
  published by the ceremony) before #1219 leaves draft; the seat never authors a publisher, and
  install.sh is not one. Reproducibility of the MCP generation remains a by-hand gap owned by the
  release owner (WS P2).
kind: constraint
verified_at: 2026-10-05
verified_by: >
  Fable seat read-only whole-tree read at origin/master 877b1e7f on 2026-10-05 (Mastermind #1219
  issuecomment-5990732208 and its precision sweep): git grep over ops/, scripts/, control_plane/,
  integrations/ (all hits readers or observers); install.sh grep empty;
  release_owner_publication_plan.py docstring L1-7 and predicates L419/L574
  (release_commit_remains_permanently_disarmed); Sol host receipt #1219 issuecomment-5991756560
  (config release_sha 5b244a2b, plist WorkingDirectory the same release, MCP running).
scope:
  - mastermind
  - mastermind:ops/executive_os/install.sh
  - mastermind:ops/executive_os/release_owner_publication_plan.py
  - mastermind:ops/executive_os/service-control.sh
  - WS:EXECUTIVE-AUTONOMY-V1-CLOSURE
confidence: verified
---

## Why this matters

The gateway-refresh verb (#1219) and every future MCP-only release step assume a generation
producer that master does not have in armed form. Naming the gap pins the one pairing the release
owner must rule on before the refresh can be used, and keeps the seat and the lanes from inventing
a second publisher beside the host owner's ceremony.

---
key: CLAUDE-PARALL-SHARED-RUNTIME-CANARY-LIVE
claim: >
  On the authorized Mac Studio, one isolated Claude Desktop seat can use a fresh Parall wrapper
  and its own existing Parall data directory while launching the single current signed Anthropic
  runtime, instead of carrying a private 800+ MB Claude application copy. The first canary was
  logged into the intended Claude 8 account, the Claude Computer use settings showed both
  Accessibility and Screen recording as Granted, and the same canary was then promoted to the
  visible /Applications/Claude 8.app path and cold-relaunched as that path while continuing to
  launch the shared runtime with the same isolated data directory. The superseded Claude 8 wrapper
  and dedicated runtime were not needed by the promoted seat and were removed after process and
  native-host reconciliation.
falsifier: >
  Run `ps -axo pid=,ppid=,command= | grep -E 'Claude 8.app/Contents/MacOS/Claude|Mastermind Claude Runtime/Claude.app'`
  after a cold seat launch and inspect `/Applications/Claude 8.app/Contents/Info.plist` with
  `/usr/libexec/PlistBuddy -c 'Print :ParallExecutable'` and `-c 'Print :ParallDataStorage'`.
  Falsify this topology for fleet rollout if the promoted wrapper does not launch the shared runtime
  with its intended isolated Parall data directory, if the seat loses its intended account/login or
  either macOS Computer use grant, if it reads or writes another seat's Parall data, if
  Claude Code/browser/computer-use requires a seat-private Anthropic application bundle, or if the
  shared browser native-host/updater path resolves back into a removed per-seat runtime. Also falsify
  broad rollout if a second independently migrated idle seat cannot reproduce the same separation
  without changing the first seat's account or permissions.
so_what: >
  Use the shared signed Claude runtime plus one Parall wrapper/data directory per seat as the
  current migration candidate, but roll it out one idle seat at a time. For each seat: create a
  fresh Parall shortcut through Parall's supported Create Shortcut flow, point it at the shared
  runtime, reuse that seat's exact existing data directory, prove intended-account login and both
  Computer use grants, cold-relaunch the promoted wrapper, then census live processes and browser
  native-host manifests before deleting that seat's old private runtime. Never bulk-stop active
  Claude seats, never hand-edit Parall checksum/metadata to manufacture a shortcut, and do not
  rename or delete retained profile data merely to make its directory label match the seat name.
kind: runtime
verified_at: 2026-09-14
verified_by: >
  Chairman screenshot of Claude Desktop Computer use settings on the canary showing Accessibility
  Granted and Screen recording Granted after logging into the intended Claude 8 account; Mac Studio
  Remote Desktop Commander process/plist/Finder observations on 2026-09-14; canary bundle
  app.parall.mac.b44844d46fd3b75d9e218717d141bd26 with ParallExecutable
  /Users/chriswong/Applications/Mastermind Claude Runtime/Claude.app/Contents/MacOS/Claude and
  ParallDataStorage /Users/chriswong/Library/Application Support/Parall/Claude 2; shared runtime
  version 1.52386.6; cold relaunch observed /Applications/Claude 8.app/Contents/MacOS/Claude (Parall)
  launching the shared runtime with --user-data-dir=/Users/chriswong/Library/Application Support/Parall/Claude 2;
  Finder displayed name Claude 8; com.anthropic.claude_browser_extension native-host manifest pointed
  at the shared runtime; no remaining process or wrapper targeted /Applications/Claude Runtimes/Claude 8
  before its 833 MB runtime directory and /Applications/Claude 8 Runtime symlink were removed.
scope:
  - WS:EXECUTIVE-CAPACITY-FABRIC
confidence: verified
---

## Evidence

The pre-migration layout gave each Parall seat its own copied Claude application bundle. The old
Claude 8 wrapper pointed at `/Applications/Claude Runtimes/Claude 8/Claude.app`, while the fresh
canary pointed at the current Anthropic-signed runtime under
`~/Applications/Mastermind Claude Runtime/Claude.app` and retained isolation through
`~/Library/Application Support/Parall/Claude 2`.

The Chairman logged the canary into the intended Claude 8 account and enabled Computer use. Claude's
settings surface showed both macOS gates as `Granted`. The host then promoted that exact Parall
wrapper to `/Applications/Claude 8.app` without altering its Parall checksum, bundle identity,
runtime target or data target. After the first live process was deliberately stopped, a cold launch
from `/Applications/Claude 8.app` produced a wrapper process at that new path and a child process at
the shared runtime with the same `--user-data-dir` value. Finder independently reported the visible
application name as `Claude 8`; the stale running `Claude 2 Canary` Dock item disappeared after the
cold relaunch.

Before deleting the old private runtime, the host reconciled Chrome native messaging. The installed
`com.anthropic.claude_browser_extension` manifest already targeted the shared runtime's
`chrome-native-host`. Two pre-migration native-host processes still executing from the old Claude 8
runtime were terminated by exact PID, then a fresh census showed no process or wrapper targeting the
old runtime. Only then were the old 833 MB runtime and its `Claude 8 Runtime` symlink removed. The old
`~/Library/Application Support/Parall/Claude 8` profile directory was deliberately retained as
rollback/account-state evidence; the promoted live seat still uses its proven `Parall/Claude 2`
data directory.

## Boundary

This is one-seat production evidence, not proof that every existing seat can be converted without a
seat-specific issue. It proves the architecture is viable enough to continue sequential canaries. It
does not authorize mass migration, profile deletion, or interruption of seats carrying live work.
The next independently useful proof is the next idle seat migrated through the same supported Parall
creation flow with login, TCC and cold-relaunch evidence collected before its old runtime is removed.

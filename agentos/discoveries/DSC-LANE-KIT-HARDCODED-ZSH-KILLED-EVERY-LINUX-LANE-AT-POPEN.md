---
key: LANE-KIT-HARDCODED-ZSH-KILLED-EVERY-LINUX-LANE-AT-POPEN
claim: >
  The meta-CEO external-lane kit (`~/.claude/projects/-Users-chriswong-Documents-Cluade-Macro-Dashboard/handoff_kits/meta-ceo-b-2026-09-08/ext/lane_runtime.py`,
  copied by the launcher to `<host>:~/lanes/ext/` on every run) passed `executable="/bin/zsh"`
  to every `shell=True` subprocess, so on the Linux lane host ubuntu1 - which has `/usr/bin/bash`
  and no zsh - every lane died inside `Popen` with `FileNotFoundError` before fetch, checkout
  or any packet step, and the Mac hosts never showed the defect. Patched 2026-10-05: the
  interpreter is chosen by `_owned_shell()` (prefer `/bin/zsh`, else `/bin/bash`, else the
  platform default); backup kept as `lane_runtime.py.bak-20261005-zsh`.
falsifier: >
  `grep -n "_owned_shell" <kit>/ext/lane_runtime.py` returning nothing, or a lane launched on a
  host without `/bin/zsh` after this date dying at `Popen` with `FileNotFoundError: /bin/zsh`.
so_what: >
  A lane that dies within seconds on a Linux host with no packet output is a runtime/shell
  defect, not a packet defect: check `which zsh bash` on the host and confirm the host's
  `~/lanes/ext/lane_runtime.py` carries `_owned_shell` (the launcher re-copies the kit, so
  the fix propagates on the next launch). Mac-host green never proves Linux-host green for
  this kit; any further kit change that touches process spawning must be tried on ubuntu1.
kind: runtime
verified_at: 2026-10-05
verified_by: >
  Research Vault seat 0e657eec: ubuntu1 lanes `rv_f4_lineage_u1` r1 and `rv_f5_segment_u1` r1
  stdout ended in the `FileNotFoundError` traceback from `lane_runtime.py`; after the patch the
  relaunched `rv_f4_lineage_u1` ran its full Cursor packet on ubuntu1 and pushed PR #8472's
  repair commit 74bc480e1d6a.
scope: [macro, fleet-lane-hosts, meta-ceo-kit]
confidence: verified
---

## Detail

The kit is account-local (not tracked in this repository); this record exists so a Codex,
Sol or future Claude seat that inherits the kit path knows the Linux host works and why an
older copy would not. Related host provisioning gate: DSC:LANE-HOST-CLONE-MUST-FETCH-THE-PR-BRANCH-PREFIX.

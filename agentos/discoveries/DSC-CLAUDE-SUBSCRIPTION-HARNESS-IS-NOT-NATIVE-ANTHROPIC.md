---
key: CLAUDE-SUBSCRIPTION-HARNESS-IS-NOT-NATIVE-ANTHROPIC
claim: >
  The merged Mastermind "Claude subscription worker" is the Claude Code HARNESS used to reach
  third-party subscription providers, not an implemented native Anthropic Fable/Opus worker. At
  protected Mastermind master 7642aea155d2817219135b24246b55c1d7611c66 the reviewed catalog
  `config/subscription_provider_profiles.v1.json` contains exactly three profiles — `glm-coding-plan`
  (provider `glm`), `alibaba-token-plan-personal` (provider `alibaba`) and `minimax-token-plan`
  (provider `minimax`) — and no Anthropic/native profile; `control_plane/worker_adapter.py` carries no
  `claude-code` descriptor, only `claude-compatible-subscription` whose implementation string is
  `control_plane.claude_subscription_worker.ClaudeSubscriptionWorkerAdapter`; and
  `control_plane/claude_worker.py` plus `tests/test_executive_claude_worker.py` do not exist. Native
  Anthropic capacity remains owned by the PF1 wave (`claude-code` / `ClaudeCodeWorkerAdapter`), whose
  only live carrier is the provider-free protocol falsifier PR #455, OPEN/DRAFT/HOLD at
  0a368935ece318c1b7f3301337f75d3a58d61006 — a falsifier, not a worker.
falsifier: >
  At the then-current protected Mastermind master, run all four reads and require every one to flip:
  `git show <master>:config/subscription_provider_profiles.v1.json` listing an Anthropic/native
  provider profile rather than exactly glm/alibaba/minimax;
  `git show <master>:control_plane/worker_adapter.py | grep -n claude` returning a `claude-code`
  descriptor rather than only `claude-compatible-subscription`;
  `git ls-tree <master> control_plane/claude_worker.py tests/test_executive_claude_worker.py`
  returning blobs rather than empty output; and PR #455 (or its accepted successor on the same PF1
  custody) merged with an exercised native adapter. A merged #581, a green check, a passing review, a
  fixture corpus or a proposed-scenario count falsifies none of it — #581 merged as
  27a5d893ca28f7006c1007dffa51e677c9c7a4ab while all four reads above still held.
so_what: >
  A future session sizing, routing, promising or reporting "native Claude/Anthropic capacity" in the
  Executive fabric must not count the merged subscription harness, its profiles, its fixtures or a
  #581/#676-style acceptance as that capacity, and must not build a replacement native worker: the
  native path is PF1's, and the next dependency is PF1-F0 custody plus the currently missing native
  `ClaudeCodeWorkerAdapter` with a dedicated native-auth worker principal through the existing common
  broker. Treating the compatible-provider alias as native capacity (rejection class E11) is the exact
  error this record exists to stop.
kind: architecture
verified_at: 2026-09-16
verified_by: >
  Protected Mastermind master 7642aea155d2817219135b24246b55c1d7611c66 (`git -C
  /Users/chriswong/Documents/Cluade/Mastermind fetch -q origin master && git rev-parse origin/master`).
  Profiles: `git show origin/master:config/subscription_provider_profiles.v1.json` — top-level keys
  `schema`, `verified_at`, `profiles`; the three provider values are glm, alibaba, minimax. Descriptor
  table: `git show origin/master:control_plane/worker_adapter.py | grep -n claude` — exactly three hits,
  lines 56/57/59, all inside the `claude-compatible-subscription` entry (positive control: the grep
  fires on this file, so the absence of `claude-code` is an instrument-verified null, not an empty
  pattern). Absence: `git ls-tree origin/master control_plane/claude_worker.py
  tests/test_executive_claude_worker.py` — empty output, exit 0. PF1 plan present: `git ls-tree
  origin/master docs/superpowers/plans/2026-08-27-hybrid-workforce-pf1-claude-worker.md` — blob
  5ec3b062264c4146a7c92e1576f1753f788bd440. Harness identity: `git show
  origin/master:control_plane/claude_subscription_worker.py` — docstring `:1` "Fixed-profile Claude Code
  worker for subscription-backed model providers", `adapter_id = "claude-compatible-subscription"`
  `:264`, imports `control_plane.subscription_provider_profiles` `:64`. PR state: `gh pr view 581 -R
  mastermindx-market-intelligence/Mastermind --json state,mergeCommit,title` — MERGED,
  27a5d893ca28f7006c1007dffa51e677c9c7a4ab, "[HF1-D] Add fixed-profile Claude subscription worker";
  `gh pr view 455 -R mastermindx-market-intelligence/Mastermind --json
  state,isDraft,headRefOid,title` — OPEN, isDraft true, 0a368935ece318c1b7f3301337f75d3a58d61006,
  "[PF1-F0][HOLD] Provider-free Claude CLI protocol falsifier". Adjudicated by Sol rulings R21/R22
  (2026-09-16, orch/fabric/SOL_RULINGS_2026-09-15_2300Z.md).
scope:
  - WS:EXECUTIVE-CAPACITY-FABRIC
confidence: verified
---

## Evidence

The confusion this record closes is a naming collision, not a disagreement about bytes. Mastermind
contains a file called `control_plane/claude_subscription_worker.py` and a worker adapter descriptor
whose id begins with `claude-`, and PR #581 is titled "Add fixed-profile Claude subscription worker".
None of that is native Anthropic capacity. The word "Claude" in all three names refers to the **Claude
Code CLI harness** — the local tool the worker drives — and the providers it is pointed at are supplied
by `config/subscription_provider_profiles.v1.json`, which at protected master
`7642aea155d2817219135b24246b55c1d7611c66` contains exactly three profiles:

| Profile id | `provider` |
|---|---|
| `glm-coding-plan` | `glm` |
| `alibaba-token-plan-personal` | `alibaba` |
| `minimax-token-plan` | `minimax` |

There is no Anthropic profile, and `claude_subscription_worker.py` reaches those profiles directly
(`from control_plane.subscription_provider_profiles import ...` at `:64`, `get_profile(...)` at `:135`).
Its own docstring is explicit at `:1`: "Fixed-profile Claude Code worker for subscription-backed model
providers." The adapter it registers is `claude-compatible-subscription` (`:264`) — *compatible*, which
is the distinction the id itself is carrying.

The native seam is absent rather than disabled. `control_plane/worker_adapter.py` holds four
descriptors; grepping it for `claude` returns three hits, all inside `claude-compatible-subscription`,
and no `claude-code` descriptor exists. Because that grep fires on this file, the absence is an
instrument-verified null and not a mis-typed pattern. `control_plane/claude_worker.py` and
`tests/test_executive_claude_worker.py` return no blobs from `git ls-tree` at the same pin.

What does exist for the native path is a plan and a falsifier. `docs/superpowers/plans/2026-08-27-
hybrid-workforce-pf1-claude-worker.md` is present (blob `5ec3b062264c4146a7c92e1576f1753f788bd440`), and
PF1's only live carrier is Mastermind PR #455, "[PF1-F0][HOLD] Provider-free Claude CLI protocol
falsifier", OPEN and DRAFT at `0a368935ece318c1b7f3301337f75d3a58d61006`. A provider-free protocol
falsifier is an instrument for disproving assumptions about the CLI boundary. It is not a worker, it
executes no native provider turn, and merging it would not create one.

## Consequence

`WS:EXECUTIVE-CAPACITY-FABRIC` already forbids inventing a second provider lifecycle plane and already
records that source capability is not production capability. This record adds the one distinction those
rows do not draw: **a compatible-provider alias is not native capacity, whatever its file is called.**

Three specific errors are now closed by name:

1. **A #581 merge is not native readiness.** #581 is merged as
   `27a5d893ca28f7006c1007dffa51e677c9c7a4ab`, and every byte-level read above still holds after that
   merge. The merge delivered a harness for three third-party subscription providers.
2. **#581-era fixtures cannot become production proof.** Fixture corpora, static check counts, killed
   mutants and proposed scenarios are engineering evidence about source; none is an executed provider
   canary, and none may be relabelled as one.
3. **The native gap is not a licence to build a replacement.** The missing piece is PF1's, and it is
   named in `WS:EXECUTIVE-CAPACITY-FABRIC`'s PF1 wave: PF1-F0 custody and its current protocol gate,
   plus a native `ClaudeCodeWorkerAdapter` carrying a dedicated native-auth worker principal — no
   token-in-environment shortcut — through the existing common broker. Standing up a parallel native
   worker outside PF1 creates a second writer for one operation.

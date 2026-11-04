# D03 T38 — Leader Radar render-failure coherence

## Result and scope

Leader Radar now prepares the next JSON and HTML before replacing either published output. A missing template with an existing page, a Jinja parse/render error, or a partial failure inside the existing page writer retains the previously published files byte-for-byte. A first build with neither a template nor a page retains the existing JSON-only contract.

This is the Leader Radar portion of D03 acceptance case T38 in [the D03 source assignment](https://github.com/mastermindx-market-intelligence/macro/pull/10617). It does not close the Foresight or Pick Lab portions of T38, the whole D03 acceptance matrix, or any release gate.

**HOLD-FOR-SOL:** keep the implementation PR DRAFT. No Ready/un-draft, label changes, queue entry, auto-merge, merge, or deployment until Chairman/Sol explicitly releases this exact change. Local tests, browser proof, a pushed branch, and a PR are separate from production proof or user acceptance.

## Source and custody

- Protected Mastermind source-law pin: `8eb375fe081339be759888f74a7c93d855727190`.
- Macro base: `5a2439d7a99548f6373893980e1952c495abfa48`.
- Operation: `d03-radar-render-coherence-20261104-c2`.
- Writer/carrier: this resumed ChatGPT root session through Studio Direct C2 Personal on m2studio.
- Branch: `claude/ssd-d03-radar-render-coherence-20261104-c2-90803ae2c4d5b4db`.
- Workspace: `/Volumes/Mastermind 2/agent-workspaces/claude/14851c4656838a3b/d03-radar-render-coherence-20261104-c2-90803ae2c4d5b4db`.
- Maintenance exception: repair an existing D03 T38 acceptance defect under the existing source assignment. No new workstream, lifecycle owner, publisher service, or control plane was introduced.

The initial mmx workspace attempt failed and was reconciled as NOT_APPLIED with no remaining worktree before the canonical SSD helper created this workspace. There is one source writer and one publication branch for this repair.

## Behavior and limits

Both outputs are serialized/rendered to temporary siblings in their final directories. HTML still goes through `lib.pages.write_page`, retaining the data-base and Shared Shell injection at the correct depth. Output permissions are preserved (new output defaults to 0644), and staged files are cleaned up.

Preparation failures emit a bare line-start GitHub warning that explicitly says the published files are unchanged and exit 0 is not freshness proof. An error during replacement emits a different warning: the output vintages may differ and both files must be inspected.

Each file replacement is atomic, but the **pair is not a filesystem transaction**. A process interruption or error between replacements can still leave mixed generations. This patch does not add rollback or a version-pointer publication system. The fault-injection test for second-replacement failure preserves that honest boundary.

Payload computation, classifications, ranking, populations, clocks, schema, the kill switch, and nightly ledger/state ownership are unchanged. In particular, nightly data stores can already advance before output publication; this fix does not roll them back. The builder retains its existing return-payload and nonfatal exit conventions.

## Verification

| Check | Result |
|---|---|
| Ten new integration cases on the original builder | 8 failed, 2 passed |
| New cases after repair | All 10 passed within the broader run |
| Radar builder suite | 172 passed |
| Lifecycle suite | 141 passed |
| Shared page/shim suite | 20 passed across the initial run and the scoped fixture rerun |
| Annotation line-start suite | 4 passed |
| Total distinct selected tests | 337 passed |
| Real-template Chromium journey | Passed; four observed states |
| Diff review | Only `build()` changed among production functions; no functions added/removed |
| Whitespace check | `git diff --check` passed |

The initial combined run had 335 passes and two missing-fixture failures because the sparse workspace intentionally omits `site/`. The two checks were then rerun against nine **exact base-commit page blobs**, with both passing. Only those fixture pages were temporarily materialized; their bytes were removed afterward and the original sparse index flags restored. No test was skipped, weakened, or changed to clear the fixture errors. The test logs retain the initial failure and its resolution.

Commands:

```bash
python3 -m pytest tests/test_build_leader_radar.py tests/test_leader_lifecycle.py tests/test_site_shim.py tests/test_gh_annotation_line_start.py -q --tb=short
python3 -m pytest tests/test_site_shim.py::test_committed_representative_pages_reinject_within_prescan_window tests/test_site_shim.py::test_hand_authored_pages_carry_charset_in_prescan_window -q --tb=short
python3 research/design_candidates/production_design_20261102/evidence/d03-radar-render-coherence-20261104/verify_browser.py
git diff --check
```

The ten added cases cover parsing/rendering with and without prior outputs, a missing template with an existing pair or page alone, the JSON-only fallback, partial page-writer failure, successful matching publication with asset paths/permissions and express byte-stability, and a second-replacement failure.

No CI workflow or pack-weight registration changed; the cases are in the existing `tests/test_build_leader_radar.py` suite already selected by the `leader-radar-unit` job.

## Browser proof

The verifier uses synthetic stale market inputs in a temporary directory, the repository's actual Radar template and assets, Chromium, and a loopback HTTP server. External browser requests are blocked. The browser and server close at the end.

1. Publish and load the initial 2024-07-12 vintage at 1440×1000, English/light.
2. Advance synthetic inputs to 2024-07-15 and deliberately break the Jinja template. Reload the page and fetch its JSON over HTTP. The visible freshness text and both output hashes remain identical to step 1.
3. Restore the template. Both outputs advance to 2024-07-15 and the visible freshness label follows.
4. Load the repaired output at 390×844, Chinese/dark. The translated freshness token matches the JSON date.

All four states had zero JavaScript page errors. Screenshots were inspected for the displayed freshness, readable primary content, asset loading, and mobile wrapping. This is scoped publication proof; it is not a new visual acceptance of the entire existing Radar design or the D03 matrix.

See `browser/manifest.json` for the observed dates, hashes, viewport/language/theme, and warning. The four PNGs capture the actual served page. `verify_browser.py` reproduces the journey; `verification-summary.json` binds the source and test hashes.

## Continuation frontier

- Recovered D03 source assignment and previously accepted mobile matrix remain the continuity owner.
- The active T35, T36, T43, and T46 branches keep their existing writers. This repair does not consume their dirty files.
- Original Prophet PR #9495 and its T004 work remain untouched.
- R8 operation `prophet-r8-20261103-desktop-dark-colors-200` on board `ZE5-0` remains EFFECT_UNKNOWN; no retry or re-home.
- Held UX Fabric `prophet-page-revamp-20261102-ux-refinement` remains unretried.
- Paper file `01M3NT5Y3G5HTJHVR0K5W2MDJM` and D03 boards were actually inspected during recovery; no Paper edit was needed for this builder repair.
- Next: verify exact-head PR checks, repair only genuine introduced failures, and persist the held PR/head/CI result on #10617. Then reconcile ownership before taking any remaining T38 Foresight/Pick Lab work. Do not mark D03 complete or deploy this branch.

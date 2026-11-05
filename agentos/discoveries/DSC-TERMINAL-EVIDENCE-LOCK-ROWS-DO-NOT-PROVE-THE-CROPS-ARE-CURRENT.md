---
key: TERMINAL-EVIDENCE-LOCK-ROWS-DO-NOT-PROVE-THE-CROPS-ARE-CURRENT
claim: >
  A Terminal evidence packet's lock rows do not show that its crops depict the current product.
  The rows are `layoutFiles` in terminal/docs/pr-crops/<packet>/EVIDENCE.yml, `fileSha256` in
  EVIDENCE.json, or `sourceFiles` in manifest.json, each the sha256 of a source the crops depict.
  A row that matches its file shows only that someone last wrote the file's hash into it. It does
  not show that anyone recaptured or looked at the crops. Three failure modes, all present in
  b-pl-6-batch-2 before Terminal PR #890 recaptured it (a0e4333e0, 2026-10-09):
  - Unread. If no vitest reads a packet's rows, nothing fails when a row goes stale. On a0e4333e0,
    16 of the 34 packets with rows have no gate, and 11 of those have stale rows. Batch 2's
    LevelsView.tsx row was stale for 18 days, from #693 (cf35757b2) to #890. In that window, six
    commits re-pinned the packet's i18n.tsx row and none touched a crop or the LevelsView row. One of
    them, the merge 1edfc1b8d, wrote a 40-hex git blob id into the sha256 slot.
  - Re-pinned. A row is rewritten without a recapture. #581 (c93815932) changed batch 2's i18n.tsx
    row from a3079322, the file at capture, to 271f79cd, touching no other file in the packet.
    271f79cd is not even the file's hash at c93815932 (1d571257). Before that, #542 (4fa11197a) had
    changed the `gpGuardrail` label that GuidePanel.tsx draws from "Guardrail" to "When not to trust
    it". The crop showed "Guardrail" until #890.
  - Too narrow. #589 (702d81bb3) and #716 (7f98bfd98) changed what batch 2's crops show without
    touching any of its six locked files.
  A gate does not close the gap. It moves a packet from "unread" to "re-pinned": every gate style
  accepts a re-pin made only in EVIDENCE.yml.
  - The plain gates compare each row with the file
    (terminal/lib/__tests__/b_pl_6Batch2Evidence.test.ts:76) and check only that the crops exist
    (:80-86).
  - f12_9TeamOwnershipTransferEvidence.test.ts:151-169 compares the rows with the bytes at
    `capturedAtHead`, so it passes once `capturedAtHead` is moved as well. Since that gate landed
    (3cdcd746b), 22 non-merge commits changed a b-f12-9 source row. Only 7 of them touched a crop,
    and 13 of the other 15 moved `capturedAtHead`.
  - f12_5AccountPolishEvidence.test.ts asks for an R3 deviation comment only while `capturedAtHead`
    is the original capture head e73e5bdc (:81, :111). Otherwise a row with no comment needs none
    (:117-118). Master's `capturedAtHead` is already bfe98ed4f, so the check is inert.
  Across all 18 gates, excluding merge commits, 118 of the 204 source-row changes made after the
  packet's current gate existed touched no crop. That is 36 distinct commits.
falsifier: >
  Re-run the probe in a scratch worktree of current Terminal master, and never push it:
  - append a comment line to terminal/components/settings/SectionTeam.tsx,
    terminal/components/settings/SectionAccount.tsx and terminal/components/levels/LevelsView.tsx,
    then commit;
  - in the b-f12-9, b-f12-5 and b-pl-6-batch-2 EVIDENCE.yml files, replace those three files' old
    hashes with the new ones. Set `capturedAtHead` in b-f12-9 and b-f12-5 to the scratch commit;
  - run `cd terminal && npx vitest run lib/__tests__/f12_9TeamOwnershipTransferEvidence.test.ts
    lib/__tests__/f12_5AccountPolishEvidence.test.ts lib/__tests__/b_pl_6Batch2Evidence.test.ts`.
  If any of the three gates fails while no crop is touched, the claim is false. This only counts if
  the control still fails. Leave `capturedAtHead` alone, and f12_9 must fail with "hash does not
  match the file bytes at capturedAtHead". If the control passes, the probe is broken.
  The history half is false if any of these holds:
  - `git show --stat c93815932 -- terminal/docs/pr-crops/b-pl-6-batch-2/` lists a crop;
  - `git show 4fa11197a -- terminal/lib/i18n.tsx | grep gpGuardrail` shows no label change;
  - `git show --name-only 702d81bb3 7f98bfd98` names one of batch 2's six locked files;
  - `terminal/docs/pr-crops/b-pl-6-batch-2/GuidePanel-1440.png` has the same blob at c968e81bf
    and a0e4333e0.
so_what: >
  - Never cite a packet's crops as showing the current product because its rows match, or because
    its gate is green.
  - To judge a packet, compare `git log -1 --format=%cI -- '<packet>/*.png'` with the history of
    every file that draws the surface, not only the locked ones. Better, recapture with the packet's
    terminal/e2e/tools/capture_*.cjs and diff the crops.
  - A re-pin that changes only hashes needs two things written beside the row: why the pixels
    cannot change, and the check that shows it. b-f12-5's 2026-10-05 F12-CLIPBOARD note is the
    model: the change is logic-only, and no captured frame exercises a copy action.
  - When re-pinning, check every row in the packet, not only the file your change touched.
  - A new packet adds its gate in the same PR. The gate is a tripwire that makes a stale row fail,
    not proof that the crops are current.
  - Rows kept "as records" under the 2026-09-11T12 Option A ruling record the last re-pin, not the
    capture. Recover a capture-time value with `git log -p -- <packet>/EVIDENCE.yml`.
  - The f12_7 and f12_10 gates narrow the lock set: `informationalFiles` plus
    `NEVER_ASSERTED = ["terminal/lib/i18n.tsx"]`. That keeps unrelated i18n edits from failing
    master, but it would also have hidden #542. Locking the LEX keys a surface renders is the
    finer-grained alternative.
  - A gate that resists re-pins has to bind crops to sources outside EVIDENCE.yml. Two ways: the
    capture script writes the lock set into each PNG's metadata, or CI recaptures packets whose
    sources changed and diffs the pixels.
kind: landmine
verified_at: 2026-10-09
verified_by: >
  All on Terminal origin/master a0e4333e01d337982357bf0be271cee701f81a8b, the merge of #890:
  - Census. Each lock row was compared with `git show a0e4333e0:<path> | shasum -a 256`. A packet
    counts as gated when a test file names it and reads a lock key. Result: 38 packets, 34 with rows,
    18 gated (all fresh), 16 ungated (11 stale, 5 fresh), 4 without rows. The same script at
    4d6a9ac81 reported batch 2 stale (the negative case).
  - Re-pin counts. Each count is a `git log --no-merges` commit that removes and adds a non-image
    lock row holding a 64-hex value, split by whether the commit touched a .png in the packet.
    - After each packet's current gate file was added: 118 touched no crop, 86 touched one.
    - b-f12-9 since 3cdcd746b: 22 commits, 7 with a crop.
    - Packets that are ungated now: 43 of 54 touched no crop.
  - Batch 2 history. `git log -p a0e4333e0 -- terminal/docs/pr-crops/b-pl-6-batch-2/EVIDENCE.yml`.
    `git show a5045c087:terminal/lib/i18n.tsx | shasum -a 256` gives a3079322, and the same at
    c93815932 gives 1d571257. The gpGuardrail anchors are terminal/lib/i18n.tsx:2788 and
    terminal/components/GuidePanel.tsx:572 at a0e4333e0. Commit-to-PR mapping comes from
    `gh api repos/mastermindx-market-intelligence/mastermind-terminal/commits/<sha>/pulls`.
  - Option A packets. `git log -S<packet> -- terminal ':(exclude)terminal/docs'` finds no test that
    names b-f08-6-alert-prefs, b-f12-b5-1-grants, b-f12-b5-2-team-workspaces or b-pl-6-batch-3, ever.
    Batch 1's first gate is 20c35ddf1 (2026-10-03) and batch 2's is a0e4333e0. The same search finds
    batch 1's gate (the positive control).
  - #890's single unmodified `node e2e/tools/capture_pl6_batch2.cjs` run changed 11 of 16 crops.
    #542, #589, #693 and #716 explain the LevelsView and GuidePanel changes. The ChartConductor
    differences come from capture timing, as the PR body says.
  - Probe. A local commit dbf0b5e4e, never pushed, appended a comment line to SectionTeam.tsx,
    SectionAccount.tsx and LevelsView.tsx. With only the EVIDENCE.yml rows and `capturedAtHead`
    re-pinned and no crop touched, the three gates gave `Tests 18 passed (18)`. The control left
    `capturedAtHead` alone and failed f12_9 with "SectionTeam.tsx hash does not match the file bytes
    at capturedAtHead".
scope:
  - terminal
  - "terminal/docs/pr-crops/**"
  - "terminal/lib/__tests__/*Evidence.test.ts"
  - "terminal/e2e/tools/capture_*.cjs"
  - "WS:MARKET-OS"
related:
  - "DSC:A-CAPTURE-TOOL-EDIT-REQUIRES-A-RECAPTURE-BECAUSE-THE-MANIFEST-PINS-THE-MODULE-SHA"
  - "DSC:TERMINAL-N-BUBBLE-IN-390-CROPS-IS-THE-NEXTJS-DEV-INDICATOR"
  - "DEC:EVIDENCE-CORPUS-IS-A-GATED-SURFACE"
  - "DEC:TERMINAL-SHELL-IS-DARK-ONLY-EVIDENCE-MATRIX-2026-09-06"
  - "WS:MARKET-OS"
confidence: verified
---

Batch 2, in order. All Terminal PRs; dates are merge dates. The packet was captured at a5045c087
on 2026-09-09 and landed with #541 (db69d0723). The changes that followed:
- #542 relabelled GuidePanel's "Guardrail" as "When not to trust it" (2026-09-10).
- #589 renamed "CP · Candle Painter" to "MC · Mastermind Candles" (09-15).
- #581 re-pinned the i18n.tsx row with no recapture (09-19).
- #693 added an exact-price bar that now strikes through the Levels labels (09-21).
- #716 grew the mobile tabs by 34px (09-22).

Between 09-24 and 10-06, six more commits rewrote the i18n.tsx row. At #890, eleven of the
sixteen crops changed.

This is the Terminal sibling of DSC-A-CAPTURE-TOOL-EDIT-REQUIRES-A-RECAPTURE-BECAUSE-THE-MANIFEST-PINS-THE-MODULE-SHA.
There, a metadata-only restamp re-attributes old pixels to a new module. Here, a hash-only re-pin
re-attributes old pixels to new source.

agentos/handoffs/MARKET-ONTOLOGY-META-CEO-B-2026-09-11.md:78 already recorded the "too narrow"
mode. The b-f12-b5-3 crops were captured when the settings rail had seven rows, and the product
now renders eleven. Nothing fired because the packet pins no wrapper.

Two earlier rulings need reading in this light.
- The PROOF-SHOT LAW (agentos/handoffs/MARKET-ONTOLOGY-META-CEO-B-2026-09-13.md:297-299) says
  evidence is the EVIDENCE.yml layoutFiles rows and their crops. The rows date the last re-pin,
  so the crops' own capture date is what counts.
- Option A (agentos/handoffs/MARKET-ONTOLOGY-META-CEO-B-2026-09-11T12.md:80 and :256-258) kept
  fourteen stale rows in six packets as records, on the premise that their evidence test "no
  longer exists". The earlier handoff (MARKET-ONTOLOGY-META-CEO-B-2026-09-11.md:79) had it right:
  "They have no evidence test". None of the six packets had ever had one. "Historical" there does
  not mean "was once verified".

The f12_7 and f12_10 `informationalFiles` rows (`asserted: false`) do not record the capture
either. b-f12-7's EVIDENCE.yml says they "are recorded for provenance only", but both hold
85830659, which #802 (64c1ea5e2) wrote on 2026-10-06, after the 2026-09-27 capture. At a0e4333e0,
terminal/lib/i18n.tsx hashes to 63689cd6, so these rows are stale too.

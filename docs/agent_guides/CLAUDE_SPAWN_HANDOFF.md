## Spawn-handoff law (STANDING — quality does not travel by pointer; onboarding postmortem 2026-07-23)

A spawned/chipped session starts with ONLY its prompt + the target repo's CLAUDE/AGENTS file. The onboarding flow shipped broken-and-ugly despite a correct masterplan AND correct model tiers (Fable loop + Opus builders): reference shots existed only as prose, acceptance gates sat at §6/§7 of a referenced doc, the target repo's agent laws were 5 lines of Next.js warnings, and the PR self-merged with no visual artifact. Tiering is NOT the quality lever — binding context is. When commissioning build work (chips, handoffs, cross-repo especially):

1. **Acceptance gates INLINE in the spawn prompt**, phrased "not done unless": fresh end-to-end happy path with zero manual workarounds (a race you reload around is a bug you own); per-step visual crops vs the reference (light+dark+zh where applicable) posted in the PR body; entry points actually wired. A masterplan pointer is context, not enforcement.
2. **Reference images = committed files** (`mockups/refs/<program>/`) with paths in the prompt. Never hand off a look in prose — the session cannot see your screenshots.
3. **Design-spec-first**: flagship user-facing surfaces get exact markup/CSS pinned in the spawned session's main loop (frontend-design skill + target repo design docs) BEFORE builders assemble anything. "Component assembly" on unpinned design = house-idiom drift, even with Opus.
4. **No child-agent self-merge on first pass** of flagship UI — the spawned builder returns its PR + visual artifact to the commissioning main session. The main session reviews it and completes the normal squash-merge/live chain in the same task unless the operator explicitly requests a hold or a genuine check is red.
5. **Masterplans for user-facing builds carry ACCEPTANCE GATES as §0** at the top of the file, not buried mid-doc.
6. **Audit the target repo's CLAUDE/AGENTS file before spawning** — if it carries no design/verification laws, fix that first (charting-app `terminal/AGENTS.md` got its laws 2026-07-23).
7. **The build surface follows the FUNNEL, not the plumbing** — where the auth/billing machinery lives never decides where the user experience lives (onboarding sheet belonged to the landing, not the terminal app).

<!-- Repository-root-relative paths and controls are unchanged by relocation. -->

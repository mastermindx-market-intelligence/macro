# Policy Watch Current Analysis R2 — Implementation Plan

> **Owner:** Sol. Execute this plan test-first and carry it through merge and public verification.

**Goal:** Make the existing Policy Watch market-view analysis explicitly dated and visibly separate its snapshot date, future review checkpoints, and the official-source freshness shown above.

**Architecture:** Keep the existing `policy_intent.json` authority and page composition. The builder derives a display-safe date only from `desk.state_asof`; the template renders one canonical `.dtp` analysis clock inside the existing Market views section. No new collector, model call, state store, scoring path, section, or forecast authority is introduced.

**Non-goals:** Do not change R1 official-source acquisition, the FOMC calendar, policy-event lifecycle, UK desk, historical intel date, 44-call ledger, #6788 pre-turn architecture, ranking, sizing, trade logic, or publication topology.

---

## Task 1: Pin the date-authority contract with failing tests

**Files:**
- Modify: `tests/test_policy_watch_ui.py`

1. Add a focused render test with a dated desk fixture.
2. Require `data-analysis-as-of="YYYY-MM-DD"`, bilingual Analysis snapshot labels, and the authority-separation sentence.
3. Require that review dates are described as checkpoints rather than source freshness.
4. Require an honest unavailable state when `state_asof` is absent or malformed.
5. Run only the new tests and confirm they fail because the contract is not implemented.

## Task 2: Derive a typed display date in the builder

**Files:**
- Modify: `scripts/build_policy_watch.py`
- Test: `tests/test_policy_watch_ui.py`

1. Add a small helper that accepts only a real `YYYY-MM-DD` desk snapshot date.
2. Reuse the existing locale-free EN/ZH date formatter.
3. Pass `analysis_asof_iso`, `analysis_asof_en`, and `analysis_asof_zh` into the template.
4. Do not infer from `generated_at`, build time, intel vintage, file mtime, or review dates.
5. Run helper tests and confirm green.

## Task 3: Render the bounded R2 component

**Files:**
- Modify: `templates/policy_watch.html.j2`
- Test: `tests/test_policy_watch_ui.py`

1. Keep the existing seven L1 sections unchanged.
2. Inside `#views`, add one `.dtp-row` analysis clock using canonical `.dtp-chip` and `.dtp-asof` components.
3. Show the desk snapshot date when valid; otherwise show a bilingual unavailable state.
4. Add one short bilingual sentence: review dates are checkpoints, while official updates above use source/fetch times.
5. Keep all view cards, track record, risks, calls, UK desk, and lifecycle intact.
6. Run focused Policy Watch tests and confirm green.

## Task 4: Render and verify production-shaped output

**Files:**
- Update: `site/policy_watch.html`
- Add: `mockups/evidence/policy-watch-current-analysis-r2/*`

1. Run `python3 -m scripts.build_policy_watch` in the full worktree.
2. Inspect `git status`; revert only unrelated history-appender side effects, if any.
3. Serve the rendered site locally.
4. Capture desktop/mobile × EN/ZH × dark/light browser evidence.
5. Assert 44 full calls, the UK desk, current official panel, analysis snapshot date, no raw/malformed timestamps, no console/request failures, and no horizontal overflow.
6. Run design-system, runtime-style, visual-evidence, template/site, and focused pytest checks.

## Task 5: Preserve durable release evidence and ship

**Files:**
- Add or update: `agentos/handoffs/MARKET-OS-2026-09-13-policy-watch-r2.md`

1. Read `agentos/README.md` and the handoff schema before writing.
2. Record R1 public proof, the R2 authority/date boundary, exact verification commands, and do-not-redo constraints.
3. Validate Agent OS records.
4. Commit, push, open an ordinary PR, add `merge-on-green`, and remain through concluded CI.
5. Squash-merge only after binding checks conclude green.
6. Verify `origin/main`, public deployment, and the same eight browser cells on the canonical URL.

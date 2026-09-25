# Shared Workspace Shell First Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land a reversible shared-workspace frame on institutional Research report pages without changing their SEO, paywall, excerpt, search, theme/language, Terminal, account, market-data, or publication ownership.

**Architecture:** The existing `_site_nav.html.j2` remains the sole owner of product header search and controls. A new workspace-sidebar partial owns only the new coarse application IA; an opt-in header mode suppresses the old mega-link row on shell consumers but keeps the canonical search and control row. Research report pages are the first low-collision consumer and keep all current content inside a reading-mode workspace.

**Tech Stack:** Jinja2 templates, existing Mastermind theme CSS variables, pytest/Jinja render tests, existing Research page builder.

**Spec:** `research/market_os/SHARED_SHELL_FIRST_ADOPTION_CONTRACT_2026-09-24.md`

## Global Constraints

- Keep `_site_nav.html.j2` the only source of `.nav-ctrls`; do not create a second search/theme/lang/Terminal owner.
- Preserve the existing report slug, canonical, JSON-LD, excerpt, paywall, related-report and sitemap contracts byte-semantically.
- The first slice introduces no JavaScript state, localStorage key, route registry, auth store, watchlist store, market-data owner, modal/body-lock owner or retry plane.
- Existing non-shell product pages render the legacy top navigation unchanged.
- Workspace-shell adoption is explicit per template; no global HTML transformation.
- Research pages live one directory below site root, so all sidebar hrefs use the existing `nav_prefix`.
- Minimum standalone controls remain at least the project 40px floor where this slice adds controls.
- No browser-production acceptance follows from source tests alone.

## Review Focus

- Nested `/research/*.html` hrefs must not lose the `../` prefix.
- Opt-in shell mode must hide the old link row only through desktop CSS while preserving it for the existing mobile fallback; search, Terminal, theme and language controls remain canonical.
- Normal pages must render the old header structure unchanged when shell mode is absent.
- Research paywall/public-excerpt ordering and SEO markup must remain intact.
- Sidebar active state must be presentational only; it must not mutate route, market, account or personal state.

---

### Task 1: Pin the opt-in shell contract

**Files:**
- Create: `tests/test_workspace_shell.py`
- Modify: `tests/test_research_pages.py`

**Interfaces:**
- Consumes: existing `templates/_site_nav.html.j2`, Research test helper `_norm_render`.
- Produces: failing structural requirements for `workspace_shell`, `workspace_active`, `workspace_scope`, and the new sidebar partial.

- [ ] **Step 1: Write failing canonical-header tests**
- [ ] **Step 2: Write failing Research integration tests**
- [ ] **Step 3: Run RED:** `python -m pytest -q tests/test_workspace_shell.py tests/test_research_pages.py --tb=short`
- [ ] **Step 4: Commit RED tests**

### Task 2: Add the reusable shell primitives

**Files:**
- Create: `templates/_workspace_sidebar.html.j2`
- Create: `templates/_workspace_shell_styles.html.j2`
- Modify: `templates/_site_nav.html.j2`

**Interfaces:**
- Consumes: `nav_prefix`, `workspace_active`, `workspace_scope`.
- Produces: one coarse sidebar and an opt-in topbar mode while preserving the canonical header controls.

- [ ] **Step 1:** Keep `_navlinks.html.j2` in the canonical header, add an opt-in workspace class/scope marker, and hide the legacy link row only on desktop shell CSS so the existing mobile menu remains the fallback.
- [ ] **Step 2:** Add one canonical coarse sidebar: Overview, Markets, Sectors & themes, Stocks & setups, Options, Research; Watchlists, Portfolio, My alerts, Ask Mastermind, All tools. No JS or persistent state.
- [ ] **Step 3:** Add shared shell styling. Desktop uses a 216px sidebar and existing header as topbar; narrow screens fall back to the canonical header rather than inventing an unreviewed drawer.
- [ ] **Step 4:** Run `python -m pytest -q tests/test_workspace_shell.py tests/test_product_chrome.py --tb=short`.
- [ ] **Step 5:** Commit primitives.

### Task 3: Adopt the Research report family

**Files:**
- Modify: `templates/research_report.html.j2`
- Test: `tests/test_research_pages.py`

**Interfaces:**
- Consumes: Task 2 shell primitives.
- Produces: Research report pages inside the shared workspace while keeping current report semantics.

- [ ] **Step 1:** Set `workspace_shell=true`, `workspace_active="research"`, `workspace_scope="all"`; include sidebar and canonical site-nav and wrap the existing report content without rewriting it.
- [ ] **Step 2:** Keep the reading column near its current width on desktop and stack normally on narrow screens.
- [ ] **Step 3:** Run `python -m pytest -q tests/test_workspace_shell.py tests/test_product_chrome.py tests/test_research_pages.py --tb=short`.
- [ ] **Step 4:** Render an isolated temporary fixture and assert one site-nav, one sidebar, one nav-ctrls, prefixed sidebar hrefs, excerpt before paywall, and zero writes to `site/`.
- [ ] **Step 5:** Commit Research adoption.

### Task 4: Candidate verification and branch evidence

**Files:**
- Modify: `research/market_os/SHARED_SHELL_FIRST_ADOPTION_CONTRACT_2026-09-24.md`
- Modify: `agentos/handoffs/MARKET-OS-SHARED-SHELL-2026-09-24.md`

- [ ] **Step 1:** Re-run the exact targeted suite from a clean worktree.
- [ ] **Step 2:** Run `git diff --check origin/main...HEAD` and `python scripts/check_template_site_sync.py`; record exact results without manufacturing a bake.
- [ ] **Step 3:** Confirm this implementation slice did not change route registry, auth, personal state, market data, `theme.js`, `nav_market.js`, deployment, or site output.
- [ ] **Step 4:** Persist exact candidate evidence and push the existing branch.
- [ ] **Step 5:** Keep release held until permitted browser/visual proof and same-task current-vs-candidate comparison pass.

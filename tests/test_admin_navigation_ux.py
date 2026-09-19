"""Admin shell UX guardrails for navigation and progressive disclosure.

These source-level tests keep the admin console usable as its page count grows. They
intentionally test the shipped static shell rather than backend behavior.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "admin" / "static" / "index.html").read_text(encoding="utf-8")
APP = (ROOT / "admin" / "static" / "app.js").read_text(encoding="utf-8")
CSS = (ROOT / "admin" / "static" / "styles.css").read_text(encoding="utf-8")


def test_admin_navigation_has_search_and_keyboard_access():
    assert 'id="navSearch"' in APP
    assert 'placeholder="Find an admin page…"' in APP
    assert 'data-nav-group' in APP
    assert 'data-nav-label=' in APP
    assert 'tabindex="0" role="button"' in APP
    assert 'e.key === "Enter" || e.key === " "' in APP
    assert 'No matching pages' in APP


def test_mobile_navigation_is_a_drawer_not_a_horizontal_page_strip():
    assert 'id="sidebarToggle"' in INDEX
    assert 'aria-controls="sidebar"' in INDEX
    assert 'id="sidebarScrim"' in INDEX
    assert '.sidebar.open' in CSS
    assert 'transform:translateX(-102%)' in CSS
    assert '.sidebar-scrim.show' in CSS
    assert 'body.nav-open' in CSS
    assert 'if (e.key === "Escape") setSidebarOpen(false)' in APP
    assert 'if (window.matchMedia("(max-width: 900px)").matches) setSidebarOpen(false)' in APP


def test_overview_keeps_primary_copy_concise_and_diagnostics_progressive():
    assert 'Key alerts — check in with Fable' not in APP
    assert 'Brief for Fable' not in APP
    assert '<div class="section">Needs attention</div>' in APP
    assert 'title="Copy the full alert context">Copy brief</button>' in APP
    assert 'class="tech-details"' in APP
    assert 'Program-watch data was not returned. This is not an all-clear.' in APP
    assert 'Deploy actions are unavailable.' in APP


def test_research_tools_do_not_repeat_internal_proprietary_disclaimers_on_every_card():
    assert '<div class="rt-kicker">Research workspace</div>' in APP
    assert '<p>Diagnostics, calibration, and internal research methods.</p>' in APP
    assert 'Internal diagnostics for model votes and neural-system output.' not in APP
    assert 'Proprietary cross-market, liquidity, and risk diagnostics.' not in APP
    assert 'Admin-only research workspace.' in APP


def test_experiments_table_hides_secondary_details_until_needed():
    assert 'Long-running tests and data collections, with the next review date and action.' in APP
    assert '<summary>Source</summary>' in APP
    assert '<details class="row-actions">' in APP
    assert '<summary class="btn">Actions</summary>' in APP
    assert '>Mark acted</button>' in APP
    assert '>Snooze</button>' in APP
    assert '>Dismiss</button>' in APP
    assert '>Override</button>' in APP
    assert '.row-actions-menu' in CSS


def test_site_access_keeps_provider_details_out_of_primary_copy():
    assert 'Country detection not configured' in APP
    assert '<summary>Technical details</summary>' in APP
    assert 'Country source is resolved by <code>/api/gate/check</code>' in APP
    assert '<div class="section">Blocked IPs ' in APP
    assert '<div class="section">Always allowed ' in APP
    assert '<div class="section">Blocked countries ' in APP
    assert 'Names via browser Intl.DisplayNames' not in APP
    assert 'Off = fail-open.' not in APP


def test_second_sweep_keeps_config_and_provider_jargon_progressive():
    assert 'Subscribers &amp; entitlements' in APP
    assert 'writes user_entitlements' not in APP
    assert 'This user is linked to Stripe.' in APP
    assert 'Subscription.modify, no proration' not in APP

    assert '<div class="section">Settings</div>' in APP
    assert '<div class="lab">Deep deliberation</div>' in APP
    assert '<summary>Config key</summary><code>prophet.autopsy_cap_per_cycle</code>' in APP
    assert 'Fable deliberation enabled' not in APP

    assert 'Revenue unavailable' in APP
    assert 'Connect Stripe to load live revenue.' in APP
    assert 'Stripe is not configured on this server' not in APP
    assert 'Recent sessions <span class="sub">— grouped into visits; replay shows the full path.</span>' in APP


def test_second_sweep_reduces_dense_row_actions_and_raw_paths():
    assert APP.count('<details class="row-actions">') >= 2
    assert 'Recent live-site alerts and the action taken on each.' in APP
    assert 'operator capture ledger (L4 instrumentation)' not in APP
    assert '<summary>Source</summary>' in APP
    assert 'Followers — not tracked yet' not in APP


def test_macro_thesis_advanced_input_is_collapsed():
    assert '<summary style="cursor:pointer;font-weight:650">Register a thesis</summary>' in APP
    assert '<span>Advanced thesis input (JSON)</span>' in APP
    assert '<span>Thesis JSON</span>' not in APP
    assert 'Retro theses are hindsight examples and are kept separate from the forward track record.' in APP


def test_support_email_and_ai_surfaces_use_operator_language():
    assert 'Open a ticket to read the conversation, reply, and update its status.' in APP
    assert 'POST /api/support/ticket' not in APP
    assert 'Manage who can receive email, suppressions, campaigns, and delivery history.' in APP
    assert 'Segments come from <code>app/email_segments.py</code>' not in APP

    assert 'Mastermind AI is unavailable' in APP
    assert 'Run-cycle and bot settings are temporarily unavailable.' in APP
    assert 'The nightly loop reviews its data dependencies, records issues, and queues approved follow-up work.' in APP
    assert 'Every night the bot audits the Neural Web data it trades against.' not in APP


def test_intelligence_pages_keep_machine_details_secondary():
    assert '▸ Diagnostics' in APP
    assert 'Operator HQ — full diagnostic detail' not in APP
    assert 'Current data is not available yet. The description and data flow below are still available.' in APP
    assert 'Research-only causal candidates; no production authority.' in APP
    assert 'CHF epistemic infrastructure' not in APP
    assert 'Current context data is not available yet' in APP
    assert 'Current causal data is not available yet' in APP


def test_strategy_pages_hide_model_and_schema_jargon():
    assert '<div class="cmp-explain-h">Campaign framework</div>' in APP
    assert '<div class="section">Live opportunities ' in APP
    assert 'Opportunity bus populates after first nightly run.' not in APP
    assert 'campaign engine — seeded, not yet active' not in APP

    assert '<span>Personas defined</span>' in APP
    assert '<th>Content path</th>' in APP
    assert '<th>Promotion rules</th>' in APP
    assert 'desk_network accounts with no spec' not in APP

    assert 'Display-only · annotate_only · not_a_signal' not in APP
    assert '<div class="section">Candidate funnel</div>' in APP
    assert '<div class="section">Model review</div>' in APP
    assert '<div class="section">Bias checks</div>' in APP


def test_response_quality_page_uses_admin_language_not_storage_plumbing():
    assert '<span class="mb-hero-name">Response quality</span>' in APP
    assert '>⟳ Refresh</button>' in APP
    assert '>⚡ Classify conflicts</button>' in APP
    assert 'Response logs — evaluation corpus' not in APP
    assert 'Refresh from R2' not in APP
    assert 'Classify conflicts (LLM)' not in APP
    assert 'Weekly answer quality (auto-eval)' not in APP
    assert 'Refresh after the assistant has answered on Macro or Terminal.' in APP


def test_control_room_and_system_pages_have_human_loading_and_status_states():
    assert 'class="control-room-load" role="status">Opening Control Room…' in APP
    assert 'Control Room is taking longer than expected.' in APP
    assert '.control-room-load {' in CSS
    assert 'Service status is unavailable from this host.' in APP
    assert '>running</span>' in APP
    assert 'Server metrics are unavailable from this host.' in APP


def test_content_and_health_pages_prioritize_operator_status():
    assert 'card("Live site"' in APP
    assert '>Online</div>' in APP
    assert '>Offline</div>' in APP
    assert ' · partial scan' in APP
    assert 'TRUNCATED' not in APP
    assert 'Nightly data health and feed freshness.' in APP
    assert 'no_creds: ["s-mut", "setup needed"]' in APP
    assert 'card("Paused feeds"' in APP


def test_master_brain_page_hides_workflow_and_config_internals_from_primary_copy():
    assert '<span class="mb-hero-name">Nightly orchestration</span>' in APP
    assert '>⏱; Run nightly pipeline</button>' not in APP  # icon is an HTML entity in source
    assert 'Run nightly pipeline</button>' in APP
    assert '<div class="section">Settings</div>' in APP
    assert '<div class="lab">Include AI feedback</div>' in APP
    assert '<div class="section">AI requests ' in APP
    assert '<div class="section" style="margin-top:14px">Instructions ' in APP
    assert 'config.yml &middot; orchestrator' not in APP
    assert 'Wake orchestrator' not in APP
    assert 'daily.yml dispatched' not in APP


def test_row_action_menus_expand_inside_scrolling_tables():
    assert '.row-actions-menu {' in CSS
    assert 'position: static;' in CSS
    assert 'margin-top: 6px;' in CSS
    assert 'position: absolute;' not in CSS[CSS.index('.row-actions-menu {'):CSS.index('.row-actions-menu .btn')]


def test_remaining_admin_copy_avoids_host_model_and_ledger_jargon():
    assert 'systemctl status admin' not in APP
    assert 'bot · VPS' not in APP
    assert 'prophet_status.json not yet written' not in APP
    assert 'us_track_history.json not yet written' not in APP
    assert 'word-salad shape the operator called out' not in APP
    assert 'Armed by operator' not in APP
    assert 'read-only · config/marketing.yml' not in APP
    assert 'not measured on this payload' not in APP
    assert "the VPS's next pull restores the halt" not in APP
    assert "This build can't list them without running the preview" not in APP
    assert 'runner follows the repo variable either way' not in APP
    assert '<b>Operator action.</b>' not in APP
    assert 'Decision recorded to operator ledger' not in APP


def test_mastermind_ai_uses_instruction_and_request_language():
    assert '["llm_review", "bool", "AI review"' in APP
    assert '["directives_max_open", "int", "Max open instructions"' in APP
    assert '<div><div class="lab">Guest access</div>' in APP
    assert '<div class="section">Settings</div>' in APP
    assert 'data mismatch${refl.contract_drift_n === 1 ? "" : "es"}' in APP
    assert '<div class="section" style="margin:0 0 8px">Instructions ' in APP
    assert '>manual</span>' in APP
    assert 'No instructions queued.' in APP


def test_observatory_and_ai_status_use_reader_language():
    assert 'System map is available now; freshness and review activity appear after the nightly pipeline runs.' in APP
    assert 'Each lobe below is a shared intelligence component.' in APP
    assert 'Lobe map sourced live from the signal registry' not in APP
    assert 'No AI requests are currently open.' in APP
    assert 'No nudges from the bot in the current feedback artifact.' not in APP
    assert 'data mismatch${driftN === 1 ? "" : "es"}' in APP


def test_narrow_publisher_rows_and_research_glow_do_not_force_overflow():
    assert '.golive-row {' in CSS
    assert 'grid-template-columns: 22px minmax(0, 1fr);' in CSS
    assert '.golive-aside {' in CSS
    assert 'white-space: normal;' in CSS
    assert '.rt-page::before {' in CSS
    assert 'width: min(420px, 100%);' in CSS

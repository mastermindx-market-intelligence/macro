"""BioCatalyst's public shell, client boundary, and build integration tests."""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from scripts.build_biocatalyst import render_from_state


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"


def _render() -> str:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=True,
        undefined=StrictUndefined,
    )
    return env.get_template("biocatalyst.html.j2").render(
        generated_utc="2026-08-02T12:00:00Z",
        active_section="research",
        active_page="biocatalyst",
    )


def test_biocatalyst_shell_is_bilingual_shared_navigation_only_and_data_free():
    source = (TEMPLATES / "biocatalyst.html.j2").read_text(encoding="utf-8")
    html = _render()

    assert source.count('{% include "_site_nav.html.j2" %}') == 1
    assert "<nav" not in source
    assert html.count('class="site-nav"') == 1
    assert html.count('class="l-en"') >= 20
    assert html.count('class="l-zh"') >= 20
    assert "BioCatalyst Intelligence" in html
    assert "Trial Intelligence Workspace" in html
    assert "试验智能工作台" in html

    # The static shell explains the product but cannot disclose a study, a
    # generated list, or an opaque internal record reference before site_full
    # has been enforced by the API.
    assert re.search(r"\bNCT\d{8}\b", html) is None
    for forbidden in (
        '"trials"',
        '"nct_id"',
        "canonical_study",
        "source_snapshot",
        "generation_id",
        "raw_object_key",
    ):
        assert forbidden not in html


def test_biocatalyst_shell_has_one_accessible_three_pane_trial_intelligence_workbench():
    html = _render()
    for identifier in (
            "bci-filter-pane",
            "bci-queue-pane",
            "bci-inspector-pane",
            "bci-window-control",
            "bci-mode-control",
            "bci-mode-milestones",
            "bci-mode-screen",
            "bci-mode-peers",
            "bci-mode-changes",
            "bci-mode-prospective",
            "bci-decision-stance",
            "bci-decision-why",
            "bci-braid",
            "bci-braid-plot",
            "bci-braid-foot",
            "bci-query-chips",
            "bci-panel-foot",
            "bci-facets",
            "bci-cohort-input",
            "bci-cohort-run",
            "bci-sponsor-filter",
            "bci-intervention-filter",
            "bci-study-type-filter",
            "bci-pc-from",
            "bci-pc-to",
            "bci-review-filter",
            "bci-field-filter",
            "bci-change-kind-filter",
            "bci-search",
        "bci-phase-filter",
        "bci-status-filter",
        "bci-condition-filter",
        "bci-queue",
            "bci-inspector-body",
            "bci-refresh",
            "bci-load-more",
            "bci-page-status",
            "bci-brain-launch",
    ):
        assert f'id="{identifier}"' in html or f'class="{identifier}"' in html
    ids = re.findall(r'\bid="([^"]+)"', html)
    assert len(ids) == len(set(ids))
    assert 'role="radiogroup"' in html
    assert 'role="radio"' in html
    assert 'role="tablist"' in html
    assert 'role="tab"' in html
    assert 'id="bci-queue-pane" role="tabpanel" aria-labelledby="bci-mode-milestones"' in html
    assert html.count('aria-controls="bci-queue-pane"') == 5
    assert "Dates and field updates are recorded by ClinicalTrials.gov" in html
    assert "A registry listing is not government validation" in html
    assert "Review the source record—no trade call." in html
    assert "请查看来源记录，不作交易判断。" in html
    js = (TEMPLATES / "biocatalyst.js").read_text(encoding="utf-8")
    # The Change Tape surface is keyed by the replay-verified field classes the
    # /trials/change-tape route actually serves.
    for kind in (
        "registry_status",
        "enrollment",
        "milestone_date_constraint",
        "site_list",
        "intervention",
        "endpoint_record_delta",
    ):
        assert f"'{kind}'" in js
    assert 'id="bci-change-kind-filter" aria-label="Updated field"' in html
    assert "<option" in html
    assert re.search(r"<option[^>]*>\s*<span", html) is None


def _assert_operational_clock_boundary(js: str) -> None:
    # This observed client clock is not a source, registry date or milestone calculator.
    clock = "  function clientCheckTimestamp() {\n    return new Date().toISOString();\n  }"
    assert js.count(clock) == 1
    clinical_source = js.replace(clock, "")
    assert "new Date" not in clinical_source
    assert clinical_source.count("clientCheckTimestamp()") == 2
    assert "state.failedCheckAt = clientCheckTimestamp();" in clinical_source
    assert "state.lastSuccessAt = clientCheckTimestamp();" in clinical_source


def test_operational_clock_boundary_rejects_clinical_clock_inference():
    js = (TEMPLATES / "biocatalyst.js").read_text(encoding="utf-8")
    _assert_operational_clock_boundary(js)
    for inferred in ("\nvar clinicalDate = new Date();", "\nvar sourceDate = clientCheckTimestamp();"):
        try:
            _assert_operational_clock_boundary(js + inferred)
        except AssertionError:
            pass
        else:
            raise AssertionError("a client clock cannot originate clinical/source dates")


def test_biocatalyst_client_uses_authenticated_source_fact_pages_and_current_dossiers_only():
    js = (TEMPLATES / "biocatalyst.js").read_text(encoding="utf-8")
    for token in (
            "/api/biocatalyst/v1/trials",
            "/api/biocatalyst/v1/catalyst-radar",
            "/api/biocatalyst/v1/trials/change-tape",
            "/api/biocatalyst/v1/trials:screen",
            "/api/biocatalyst/v1/trials:screen/facets",
            "/api/biocatalyst/v1/trial-peer-sets:resolve",
            "headers.Authorization = 'Bearer ' + token",
        "window.MDXAuth.client",
        "credentials: 'same-origin'",
        "cache: 'no-store'",
        "textContent",
        "encodeURIComponent(id)",
        "rel = 'noopener noreferrer'",
        "URLSearchParams",
        "aria-selected",
        "ArrowDown",
        "Escape",
        "langchange",
        "Primary endpoints",
        "Secondary endpoints",
        "bci-endpoint",
        "Registry record updates",
        "V' + group.before + ' → V' + group.after",
        "Submitted ",
        "Before: ",
        "After: ",
        "historyUnavailableCopy",
        "historyKindLabel",
            "Registry field updated",
            "登记字段更新",
            "incomplete_chain",
            "next_cursor",
            "milestone_kind",
            "next_365d",
            "last_30d",
            "change_kind",
            "before_display_version",
            "after_display_version",
            "change_tape_coverage",
            "protocol_change_asserted",
            "materiality_assessed",
            "correction_assessed",
            "validateChangeEnvelope(payload)",
            "validateChangePage(payload.change_tape, existingRows)",
            "validateChangePagination(payload, existingRows, cursor",
            "makeChangeRow",
            "bci-tape-delta",
            "bci-tape-path",
            "Change Tape",
            "AbortController",
            "generation-restarted",
            "first-load",
            "page-loading",
            "locked",
            "empty",
            "Evidence & trust",
            "current_only",
            "ACTUAL",
            "ESTIMATED",
            "UNKNOWN",
            "DATE_PARTS",
            "URLSearchParams",
            "Load more",
        ):
            assert token in js
    assert "innerHTML" not in js
    _assert_operational_clock_boundary(js)
    assert "fetchTrialPages" not in js
    assert "limit=250" not in js
    assert "localStorage" not in js
    assert "sessionStorage" not in js
    assert "clinicaltrials.gov/study/" in js
    legacy_js = js.split("var WMN_API = '/api/biocatalyst/v1/what-matters-next';", 1)[0]
    assert "probability" not in legacy_js.lower()
    assert "normalized.replace(/_/g, ' ')" not in js
    for forbidden in (
        "protocol amendment",
        "activated",
        "closed",
        "delay",
        "velocity",
        "forecast",
        "pdufa",
        "approval",
    ):
        assert forbidden not in legacy_js.lower()


def test_biocatalyst_assets_have_responsive_motion_and_focus_guards():
    css = (TEMPLATES / "biocatalyst.css").read_text(encoding="utf-8")
    for token in (
        "@media (min-width: 1121px)",
        "@media (max-width: 1120px)",
        "@media (max-width: 760px)",
        ":focus-visible",
        "prefers-reduced-motion",
        ".bci-inspector-pane.is-open",
        ".bci-scrim",
        ".bci-inspector-close,.bci-scrim { display: none !important; }",
        ".bci-window-options",
        ".bci-mode-control",
        ".bci-tape-card",
        ".bci-tape-delta",
        ".bci-braid-lag",
        ".bci-stamp-mark",
        ".bci-peer-cell.is-uncovered",
        ".bci-facet.is-active",
        ".bci-load-more",
        ".bci-evidence-strip",
        ".bci-date-type.is-actual",
        "body.bci-page #mmb-launch { display: none !important; }",
        ".bci-brain-launch { display: inline-flex;",
        "backdrop-filter: none",
        "min-height: 0; height: 100%; overflow: hidden",
        "animation: none !important",
    ):
        assert token in css
    assert "animation-duration: 2s" not in css


def test_catalyst_radar_cards_do_not_shrink_inside_desktop_scroll_queue():
    """Radar rows must expand to their content instead of clipping at 96px."""

    css = (TEMPLATES / "biocatalyst.css").read_text(encoding="utf-8")
    rule = re.search(r"\.bci-radar-card\s*\{(?P<body>[^}]*)\}", css)

    assert rule is not None
    assert re.search(r"(?:^|;)\s*flex-shrink:\s*0\s*(?:;|$)", rule.group("body"))


def test_biocatalyst_modes_default_to_milestones_and_preserve_verified_pages():
    """Audit the UI contract around the non-inferential milestone endpoint.

    These assertions intentionally inspect the public runtime source so a future
    visual refactor cannot silently widen the default request, merge malformed
    pages, leak a paid page after access loss, or strand keyboard focus in the
    compact inspector.
    """

    html = _render()
    js = (TEMPLATES / "biocatalyst.js").read_text(encoding="utf-8")

    assert 'data-window="90"' in html
    assert re.search(r'class="bci-window is-active"[^>]*aria-checked="true"[^>]*data-window="90"', html)
    assert re.search(r'class="bci-window"[^>]*aria-checked="false"[^>]*data-window="30"', html)
    assert "mode: 'milestones'" in js
    # The literal pins the FULL live state initializer, including the radar
    # mode's real horizon default (horizon: DEFAULT_RADAR_HORIZON = '365') --
    # window: '90' here is First-seen Tape's own default, still live and
    # unrelated to the radar's own horizon default appended at the end.
    assert (
        "filters: { field: 'primary_completion', change_kind: '', prospective_change_kind: '', window: '90', "
        "q: '', phase: '', status: '', condition: '', sponsor: '', intervention: '', study_type: '', "
        "pc_from: '', pc_to: '', review_state: 'all', horizon: DEFAULT_RADAR_HORIZON }"
    ) in js
    assert "WINDOW_VALUES[windowName] ? windowName : '90'" in js
    assert "change_kind: '', prospective_change_kind: '', window: '90', q: '', phase: '', status: '', condition: ''" in js
    assert "RADAR_WINDOWS = { '180': 'next_180d', '365': 'next_365d'" in js
    assert "PROSPECTIVE_WINDOWS = { '30': 'last_30d', '90': 'last_90d'" in js

    for token in (
        "function isAccessError(error)",
        "error.status === 402",
        "function restartableAppendError(error)",
        "error.status === 400 || error.status === 409",
        "validateMilestoneEnvelope(payload)",
        "queryMatchesCurrentFilters(query)",
        "effectiveWindowIsSane",
        "partialDateMatchesPrecision",
        "kind === state.filters.field",
        "function validateMilestonePage(items, existingRows)",
        "function validateMilestonePagination(payload, existingRows, requestedCursor, previousPayload)",
        "Duplicate milestone identity",
        "Milestone total changed during pagination",
        "Repeated milestone cursor",
        "append-unavailable",
        "Last verified page",
        "state.rows.length && !state.accessLocked",
        "function lockWorkspace()",
        "aria-modal",
        "function trapInspectorFocus(event)",
        "document.activeElement === ui.inspector",
        "state.returnFocus",
        "function syncQueueSelection()",
        "trigger && document.contains(trigger)",
        "returnTrialId",
        "data-date-type",
        "Registry date type:",
        "Retry loading more ' + noun",
        "window.addEventListener('resize', function () {",
        "syncInspectorDialog();",
        "closeInspector({ restoreFocus: false, writeUrl: false, render: false })",
        "abort('detailController'); state.detailToken += 1",
        "function paintLockedWorkspace()",
        "function paintAppendFailure()",
        "function paintUnavailableWorkspace()",
        "function paintIntegrityWorkspace()",
        "function paintSourceOutageWorkspace()",
        "function paintClientFaultWorkspace()",
        "function handleHydrationFailure(error, options)",
    ):
        assert token in js

    # Access errors clear all prior rows before the finally block can repaint;
    # transient append failures instead retain the last verified cursor/rows.
    assert "state.rows = []; state.nextCursor = ''; state.payload = null" in js
    assert "if (options.append && state.rows.length && kind !== 'integrity_block' && kind !== 'client_fault') { preserveAppendFailure(); return; }" in js
    load_body = js[js.index("function loadMilestones(") : js.index("function applyFilters()")]
    assert "handleHydrationFailure(error, { append: append," in load_body
    assert "handleUnavailable(error," not in load_body
    assert "paintUnavailableWorkspace()" not in load_body
    assert "throw markHydration(contractError, 'integrity_block', 200);" in load_body
    assert "throw markHydration(displayError, 'client_fault', 200);" in load_body
    assert "kind === 'integrity_block' || state.contractFailed" not in js
    select_body = js[js.index("function selectTrial(") : js.index("function updateMetadata(")]
    assert "else if (kind === 'source_outage')" in select_body
    assert "This dossier could not be shown" in select_body
    assert "Nothing is inferred." in select_body

    # Entitlement loss invalidates both concurrent request lanes before any paid
    # rows are cleared, so a late dossier response cannot repaint the workspace.
    lock_body = js[js.index("function lockWorkspace()") : js.index("function paintAppendFailure()")]
    assert lock_body.index("abort('detailController')") < lock_body.index("state.rows = []")
    assert lock_body.index("state.detailToken += 1") < lock_body.index("state.rows = []")

    close_body = js[js.index("function closeInspector(options)") : js.index("function detailLoading()")]
    assert "showInspectorEmpty(tr('Trial dossier'" in close_body
    assert close_body.index("state.detail = null") < close_body.index("showInspectorEmpty")

    # Runtime language changes must repaint exceptional states directly instead
    # of routing an append failure through updateMetadata(), which clears it.
    language_body = js[js.index("document.addEventListener('langchange'") : js.index("window.addEventListener('popstate'")]
    assert "syncControls(); localizeControls();" in language_body
    assert language_body.index("state.accessLocked") < language_body.index("state.appendFailed")
    assert language_body.index("state.appendFailed") < language_body.index("updateMetadata(state.payload)")
    assert "announce(state.rows.length ? tr('Loaded '" in language_body
    assert "announce(tr('Retrieving ' + activeNoun()" in language_body


def test_biocatalyst_change_tape_client_contract_is_mode_bound_and_fail_closed():
    """Change Tape reads the replay-verified tape, and only what it actually carries.

    The tape route serves a field-class ledger: which registry field changed,
    between which submitted versions, and when the replay verified it. Newer
    rows also carry bounded exact JSON values, an RFC 6901 source pointer, and
    explicit predecessor lineage. The browser must validate that optional
    extension as one unit, preserve older rows, and never turn lineage into a
    correction assessment. Endpoint-alignment candidates remain needs_review.
    """

    js = (TEMPLATES / "biocatalyst.js").read_text(encoding="utf-8")
    css = (TEMPLATES / "biocatalyst.css").read_text(encoding="utf-8")
    html = _render()

    for token in (
        "var CHANGE_API = '/api/biocatalyst/v1/trials/change-tape'",
        "function utf8Length(value)",
        "function validTapeValueEntry(entry)",
        "function validTapeExtension(change, versions)",
        "function validTapeChange(change)",
        "function validTapeItem(item)",
        "function validateChangeEnvelope(payload)",
        "function changeQueryMatchesCurrentFilters(query)",
        "function tapeNctFilter()",
        "function changeIdentity(item)",
        "function validateChangePage(items, existingRows)",
        "function validateChangePagination(payload, existingRows, requestedCursor, previousPayload)",
        "Duplicate registry change identity",
        "Repeated registry change cursor",
        "Incomplete registry change pagination",
        "function setMode(value, trigger)",
        "abort('listController'); state.listToken += 1; abort('detailController'); state.detailToken += 1",
        "function isChangeMode()",
        "activeApi()",
        "activeWindow()",
        "setMode(button.getAttribute('data-mode'), button)",
        "ArrowRight",
        "safeJson",
        "fullTimestamp",
        "replay_verified_record_history",
        "committed_trial_record",
        "unavailable_without_retained_activation_proofs",
        "source_versions",
        "exact_operation_index",
        "semantic_resolution",
        "registry_field_class_only",
        "protocol_change_asserted') === false",
        "materiality_assessed') === false",
        "correction_assessed') === false",
        "validTapeExtension(change, versions)",
        "typeof exact === 'undefined' && typeof lineage === 'undefined'",
        "tape_value_budget_exhausted",
        "value_bytes_not_representable",
        "predecessor_source_version",
        "predecessor_exact_operation_index",
        "prior_tape_row",
        "predecessorVersion > beforeVersion",
        "clean(valueAt(beforeValue, 'state')) !== beforeState",
        "operation === 'remove' ? 'clears_prior_recorded_value'",
        "truncated ? byteLength > 4096",
        "isChangeMode()) { rows = validateChangePage(payload.change_tape, existingRows);",
    ):
        assert token in js
    assert js.count("function validateChangeEnvelope(payload)") == 1
    assert "function validChangeEnvelope(payload)" not in js

    # The legacy derived-change feed and its display-version diff vocabulary are
    # gone from the tape lane; nothing may quietly read the unverified endpoint.
    assert "'/api/biocatalyst/v1/trials/changes'" not in js
    assert "function validRegistryChange(change)" not in js
    assert "total_display_safe_changes" not in js

    # A needs_review row is labelled as unchecked, never as a protocol change or
    # a business event, and an endpoint delta may only ever be needs_review.
    assert "Not checked yet" in js
    assert "尚未核对" in js
    assert "fieldClass === 'endpoint_record_delta' ? (reviewState === 'needs_review' && resolution === 'unresolved')" in js

    # Exact values are tier one when present; technical provenance stays in a
    # dossier disclosure. Older pre-extension rows retain the state fallback.
    for token in (
        "function tapeValueLabel(entry)",
        "function tapeValueSide(label, entry)",
        "function tapeExactDelta(exact, detail)",
        "function tapeLineageLabel(lineage)",
        "valueAt(change, 'exact_values')",
        "Source & lineage",
        "Source position",
        "Recorded lineage",
        "Correction status",
        "Not assessed",
        "Prefix shown · original ",
        "exact recorded JSON values",
        "does not carry exact value disclosure",
    ):
        assert token in js
    assert "Open a row for the source position and recorded lineage." in js
    assert "function recordStateLabel(name)" in js
    assert "not on the record" in js
    for token in (
        ".bci-tape-exact {",
        ".bci-tape-value code {",
        ".bci-tape-exact.is-detail",
        ".bci-tape-disclosure {",
        "white-space: pre-wrap",
        "overflow-wrap: anywhere",
    ):
        assert token in css

    assert "localStorage" not in js
    assert "sessionStorage" not in js
    assert "innerHTML" not in js
    assert "No trade call" not in js  # claim stays in the bilingual shell, not data handling
    assert 'data-mode="milestones"' in html
    assert 'data-mode="changes"' in html
    assert 'aria-selected="true"' in html

    # The browser accepts the same bounded JSON value domain as the API and
    # renders exact JSON literals in the dossier. Queue cards are explicitly a
    # compact preview, so blank, whitespace-only, and long values are never
    # silently recast as absent facts.
    for token in (
        "Array.from(value).length <= 12000",
            "value.length <= 512",
        "Object.keys(value).length > 100",
        "Array.from(key).length <= 256",
        "depth > 12",
        "JSON.stringify(value)",
        "data-row-key",
        "state.selectedKey",
        "rowKey === state.selectedKey",
        "ui.queuePane.setAttribute('aria-labelledby', button.id)",
        "AUTHORITY_ALLOWED_USES = ['display', 'context', 'explain']",
        "AUTHORITY_FORBIDDEN_USES = ['originate_signal', 'rank_security', 'select_security', 'size_position', 'gate_decision', 'execute_trade', 'raise_authority']",
        "Object.keys(authority).sort().join('|') === 'allowed_uses|classification|decision_authority|forbidden_uses'",
        "validAuthority(payload.authority)",
        "!fullTimestamp(payloadAsOf)",
        "var activeRow = selectedRow();",
        "state.selectedKey && rowIdentity(item) === state.selectedKey",
        "function activeSingularNoun()",
        "if (isProspectiveMode()) return tr('first-seen observation', '首次观测记录');",
    ):
        assert token in js
    assert "Choose a registry milestone to read the current trial record" not in js
    assert "Choose a registry milestone when full access is confirmed" not in js
    assert "clean(String(value))" not in js
    assert "var selectedRow = state.rows.filter(function (item) { return nctOf(item.trial) === state.selectedId; })[0];" not in js


def test_biocatalyst_first_seen_tape_is_prospective_current_only_and_never_recasts_its_clock():
    """First-seen Tape is an observation ledger, not a third history presentation.

    The browser must reject payloads that blur a collector-observation interval
    into a source event time, reveal non-display-safe operations, or carry a
    row identity that collapses multiple observations for the same NCT.
    """

    html = _render()
    js = (TEMPLATES / "biocatalyst.js").read_text(encoding="utf-8")
    css = (TEMPLATES / "biocatalyst.css").read_text(encoding="utf-8")

    assert 'id="bci-mode-prospective"' in html
    assert 'data-mode="prospective"' in html
    assert 'data-label-en="First-seen Tape"' in html
    assert 'data-label-zh="首次观测记录"' in html
    assert html.count('aria-controls="bci-queue-pane"') == 5

    for token in (
        "/api/biocatalyst/v1/trials/prospective-changes",
        "PROSPECTIVE_WINDOWS",
        "function isProspectiveMode()",
        "function validProspectiveEvidence(evidence, id, observedAt)",
        "function validObservedInterval(interval, observedAt)",
        "function validProspectiveChange(change)",
        "function validProspectiveChangeItem(item)",
        "function observationTimestampLabel(value)",
        "function prospectiveQueryMatchesCurrentFilters(query)",
        "function effectiveProspectiveWindowIsSane(window, apiWindow)",
        "function validateProspectiveEnvelope(payload)",
        "function prospectiveIdentity(item)",
        "function validateProspectivePage(items, existingRows)",
        "function validateProspectivePagination(payload, existingRows, requestedCursor, previousPayload)",
        "Duplicate prospective observation identity",
        "Repeated prospective cursor",
        "Incomplete prospective pagination",
        "prospective_changes",
        "prospective_change",
        "change_id",
        "first_observed_at",
        "observed_interval",
        "at_or_before",
        "observation_at_or_before_utc",
        "prospective_current_only",
        "current_trial_record",
        "coverage_state",
        "pre_baseline_trials",
        "total_exact_operation_count",
        "display_change_count",
        "omitted_operation_count",
        "changes.length <= 128",
        "['present', 'missing']",
        "PROSPECTIVE_CHANGE_KIND_VALUES",
        "makeProspectiveRow",
        "bci-prospective-card",
        "bci-observation-preview",
        "First observed",
        "Observed at / before",
        "no display-safe detail",
        "function prospectiveObservationSection(prospectiveChange)",
        "showDetail(detail, queueEvidence, queueItem)",
        "if (isProspectiveMode()) ui.inspectorBody.appendChild(prospectiveObservationSection",
    ):
        assert token in js

    prospective_row = js[js.index("function makeProspectiveRow") : js.index("function syncQueueSelection")]
    prospective_detail = js[js.index("function prospectiveObservationSection") : js.index("function historySection")]
    assert "Submitted " not in prospective_row
    assert "version" not in prospective_row.lower()
    assert "history" not in prospective_row.lower()
    assert "Submitted " not in prospective_detail
    assert "version" not in prospective_detail.lower()
    assert "history" not in prospective_detail.lower()
    assert "observationTimestampLabel(" in prospective_row
    assert "observationTimestampLabel(" in prospective_detail

    # A prospective response binds to the same request and current-record scope.
    # It accepts only the prospective vocabulary, retains that selection across
    # ordinary tab switches, and never carries a retrospective kind into the
    # prospective request or control surface.
    query_body = js[js.index("function prospectiveQueryMatchesCurrentFilters") : js.index("function effectiveProspectiveWindowIsSane")]
    assert "change_kind: activeChangeKind() || 'all'" in query_body
    assert "state.filters.prospective_change_kind" in js
    assert "state.mode === 'prospective' && PROSPECTIVE_CHANGE_KIND_VALUES[changeKind] ? changeKind : ''" in js
    assert "assign('change_kind', (isChangeMode() || isProspectiveMode()) ? activeChangeKind() : '', true);" in js
    assert "if (isProspectiveMode()) {" in js
    assert "if (activeChangeKind()) params.set('change_kind', activeChangeKind());" in js
    assert "ui.changeKindControl.hidden = !(isChangeMode() || isProspectiveMode());" in js
    assert "function paintChangeKindOptions()" in js
    assert "All observed fields" in js
    assert "All registry fields" in js
    assert "Observed field" in js
    assert "Registry field" in js
    prospective_catalog = js[js.index("var PROSPECTIVE_CHANGE_KIND_CATALOG") : js.index("var PROSPECTIVE_WINDOWS")]
    for kind in (
        "registry_status",
        "enrollment_target",
        "enrollment_actual",
        "enrollment_count",
        "enrollment_type",
        "primary_completion_date",
        "completion_date",
        "site_set",
        "endpoint_record",
    ):
        assert f"'{kind}'" in prospective_catalog
    for historical_kind in (
        "endpoint_added",
        "endpoint_removed",
        "endpoint_role_changed",
        "enrollment_changed",
        "registry_status_changed",
        "study_date_changed",
        "intervention_added",
    ):
        assert historical_kind not in prospective_catalog
    set_mode_body = js[js.index("function setMode(value, trigger)") : js.index("function openBrain")]
    assert "state.filters.change_kind = '';" not in set_mode_body
    assert "} else params.set('milestone_kind', state.filters.field);" in js

    legacy_js = js.split("var WMN_API = '/api/biocatalyst/v1/what-matters-next';", 1)[0]
    for forbidden in (
        "probability",
        "forecast",
        "pdufa",
        "approval",
        "localStorage",
        "sessionStorage",
        "innerHTML",
    ):
        assert forbidden not in legacy_js.lower()

    for token in (
        ".bci-mode-control { display: grid; grid-template-columns: minmax(0, 1fr);",
        ".bci-mode-prospective.is-active",
        ".bci-prospective-card",
        ".bci-observation-receipt",
        ".bci-observation-preview.is-omitted",
        ".bci-observation-section",
        ".bci-observation-delta",
        "@media (max-width: 760px)",
        "@media (max-width: 450px)",
    ):
        assert token in css


def test_biocatalyst_mobile_uses_an_inline_mastermind_entry_not_a_fixed_filter_overlay():
    """The global fixed launcher must not intercept the phone filter controls."""

    html = _render()
    js = (TEMPLATES / "biocatalyst.js").read_text(encoding="utf-8")
    css = (TEMPLATES / "biocatalyst.css").read_text(encoding="utf-8")

    assert 'id="bci-condition-filter"' in html
    assert 'id="bci-brain-launch"' in html
    assert html.index('id="bci-condition-filter"') < html.index('id="bci-brain-launch"')
    assert "window.MMBrain.open" in js
    assert "body.bci-page #mmb-launch { display: none !important; }" in css
    assert ".bci-brain-launch { display: inline-flex;" in css


def test_biocatalyst_renderer_writes_only_the_shell_and_paired_assets(tmp_path: Path):
    # The builder must be testable without mutating the repository's served
    # tree. It only needs the template family, so a directory symlink preserves
    # the real include graph while redirecting all emitted site bytes.
    (tmp_path / "templates").symlink_to(TEMPLATES, target_is_directory=True)
    page = render_from_state(tmp_path)
    html = page.read_text(encoding="utf-8")
    assert page == tmp_path / "site" / "biocatalyst.html"
    assert re.search(r"\bNCT\d{8}\b", html) is None
    assert (tmp_path / "site" / "biocatalyst.css").read_bytes() == (TEMPLATES / "biocatalyst.css").read_bytes()
    assert (tmp_path / "site" / "biocatalyst.js").read_bytes() == (TEMPLATES / "biocatalyst.js").read_bytes()
    assert not list((tmp_path / "site").glob(".biocatalyst.*.tmp"))
    assert 'src="biocatalyst.js"' in html
    assert 'href="biocatalyst.css"' in html


def test_biocatalyst_has_public_workbench_assets_with_a_site_full_api_boundary():
    policy = yaml.safe_load((ROOT / "config" / "site_access.yml").read_text(encoding="utf-8"))
    public = policy["public"]["exact"]
    assert "/biocatalyst.html" in public
    assert "/biocatalyst.css" in public
    assert "/biocatalyst.js" in public

    page_source = (TEMPLATES / "biocatalyst.html.j2").read_text(encoding="utf-8")
    api_source = (ROOT / "app" / "biocatalyst.py").read_text(encoding="utf-8")
    assert "/api/biocatalyst/" not in page_source
    assert "require_site_full_user" in api_source
    assert "enforce_site_full" in api_source


def test_biocatalyst_is_wired_into_the_site_renderer_and_research_navigation():
    site_builder = (ROOT / "scripts" / "build_site.py").read_text(encoding="utf-8")
    nav = (TEMPLATES / "_navlinks.html.j2").read_text(encoding="utf-8")
    plans = (TEMPLATES / "plans.html.j2").read_text(encoding="utf-8")
    assert "scripts.build_biocatalyst" in site_builder
    assert "biocatalyst.html render failed" in site_builder
    assert nav.count("biocatalyst.html") == 1
    assert "BioCatalyst Intelligence" in nav
    assert plans.count("BioCatalyst Trial Watch") == 2
    assert "probability" not in plans.lower()
    assert "forecast" in plans.lower()  # explicit non-forecast boundary


def test_render_lane_owns_and_narrows_biocatalyst_builder():
    render = (ROOT / ".github" / "workflows" / "render.yml").read_text(
        encoding="utf-8"
    )
    assert '- "scripts/build_biocatalyst.py"' in render
    assert "templates/biocatalyst.*" in render
    assert "scripts/build_biocatalyst.py) echo macro;;" in render


def test_biocatalyst_runtime_is_valid_javascript():
    node = shutil.which("node")
    if node is None:
        return
    result = subprocess.run(
        [node, "--check", str(TEMPLATES / "biocatalyst.js")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

def test_biocatalyst_what_matters_next_is_primary_decision_surface():
    """V3 lands as a real user-facing consumer without weakening Trial truth law."""

    html = _render()
    js = (TEMPLATES / "biocatalyst.js").read_text(encoding="utf-8")
    css = (TEMPLATES / "biocatalyst.css").read_text(encoding="utf-8")

    assert 'id="bci-wmn"' in html
    assert html.index('id="bci-wmn"') < html.index('class="bci-information"')
    assert 'id="bci-wmn-queue"' in html
    assert 'id="bci-wmn-detail"' in html
    assert 'href="#bci-trial-intelligence"' in html
    assert "What Matters Next" in html
    assert "下一步看什么" in html
    assert "Biotech Decision Intelligence" in html
    assert "生物科技决策智能" in html

    for token in (
        "var WMN_API = '/api/biocatalyst/v1/what-matters-next';",
        "var WMN_DETAIL_API = '/api/biocatalyst/v1/what-matters-next/detail';",
        "biocatalyst_what_matters_next.v1",
        "biocatalyst_wmn_detail.v1",
        "research_priority_only",
        "trade_origination === false",
        "changes_availability === false",
        "position_sizing === false",
        "prophet_admission === false",
        "NOT_ESTIMABLE",
        "function makeWmnRow(",
        "function showWmnDetail(",
        "function selectWhatMattersNextRow(",
        "function showGenerationBoundTrialDetail(",
        "window.BioCatalystTrialWorkspace = Object.freeze({",
        "generation_id",
        "event_fact_ref",
        "Research triage only",
    ):
        assert token in js

    assert "Catalyst Score" not in html
    assert "Catalyst Score" not in js
    assert "generic catalyst score" not in js.lower()
    for token in (
        ".bci-wmn",
        ".bci-wmn-card",
        ".bci-wmn-lane",
        ".bci-wmn-estimate",
        ".bci-wmn-missing",
        ".bci-wmn-detail",
    ):
        assert token in css

    for legacy_mode in ("milestones", "screen", "peers", "changes", "prospective"):
        assert f'data-mode="{legacy_mode}"' in html
    assert "Trial Screen" in html
    assert "First-seen Tape" in html


def test_biocatalyst_wmn_trial_detail_stays_generation_bound_and_reuses_trial_inspector():
    """A WMN registry event may open Trial Intelligence, but never by fetching latest."""

    js = (TEMPLATES / "biocatalyst.js").read_text(encoding="utf-8")
    wmn = js[js.index("var WMN_API = '/api/biocatalyst/v1/what-matters-next';"):]

    assert "function selectWhatMattersNextRow(" in wmn
    assert "function validGenerationBoundTrial(trial)" in wmn
    assert "payload.trial!==null" in wmn
    assert "window.BioCatalystTrialWorkspace" in wmn
    assert "trialWorkspace.showGenerationBoundTrialDetail(payload.trial,trigger)" in wmn

    # The legacy selector owns latest-record reads. The WMN path must only use
    # its generation-bound detail endpoint and the narrow render bridge.
    assert "TRIAL_API + '/'" not in wmn
    assert "selectTrial(" not in wmn
    assert "fetchJson(WMN_DETAIL_API+'?'+params.toString()" in wmn

    legacy = js[:js.index("var WMN_API = '/api/biocatalyst/v1/what-matters-next';")]
    bridge = legacy[legacy.index("function showGenerationBoundTrialDetail("):]
    assert "fetchJson(" not in bridge.split("function updateMetadata(payload)", 1)[0]
    assert "openInspector(" in bridge
    assert "showDetail(detail, null, null)" in bridge


def test_biocatalyst_wmn_uses_frozen_research_lane_copy_not_internal_act_now_label():
    html = _render()
    js = (TEMPLATES / "biocatalyst.js").read_text(encoding="utf-8")

    assert 'value="ACT_NOW" data-label-en="Review soon" data-label-zh="近期核查"' in html
    assert "ACT NOW</option>" not in html
    for token in (
        "ACT_NOW:['Review soon','近期核查']",
        "RECONCILE:['Needs review','需要核实']",
        "RESEARCH_NEXT:['Research next','后续研究']",
        "MONITOR:['Monitor','持续关注']",
        "The scheduled window is entirely within the next 7 calendar days. Check its evidence.",
        "Resolve the highlighted source, timing or identity gap before relying on this record.",
        "This window overlaps the next 90 calendar days; its full timing precision remains shown.",
        "A later schedule or resolved event history; this is not a return forecast.",
    ):
        assert token in js
    assert "Act now — research" not in js


def test_biocatalyst_wmn_exposes_every_frozen_research_horizon():
    html = _render()
    js = (TEMPLATES / "biocatalyst.js").read_text(encoding="utf-8")
    for horizon in ("7", "30", "90", "180", "365"):
        assert f'data-horizon="{horizon}"' in html
        assert f"'{horizon}': true" in js


_WMN_REQUEST_RACE_DRIVER = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

// Execute the shipped WMN controller. Only its DOM and transport are simulated;
// aborted requests deliberately still settle to exercise ownership, not abort.
class Element {
  constructor(tag = 'div') {
    this.tagName = tag; this.children = []; this.attributes = {}; this.listeners = {};
    this.dataset = {}; this.options = []; this.value = ''; this._text = '';
    this.className = ''; this.disabled = false; this.hidden = false;
    this.classList = { toggle: () => {}, add: () => {}, remove: () => {} };
  }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(' '); }
  get firstChild() { return this.children[0] || null; }
  appendChild(child) { this.children.push(child); return child; }
  removeChild(child) { this.children.splice(this.children.indexOf(child), 1); return child; }
  setAttribute(key, value) { this.attributes[key] = String(value); }
  getAttribute(key) { return this.attributes[key] ?? null; }
  addEventListener(type, callback) { (this.listeners[type] ||= []).push(callback); }
  dispatch(type) { for (const callback of this.listeners[type] || []) callback({ preventDefault() {}, stopPropagation() {} }); }
  focus() {}
  querySelectorAll(selector) {
    if (selector === '[data-horizon]') return [];
    const result = [];
    for (const child of this.children) {
      if (selector === '.bci-wmn-card' && child.className.split(' ').includes('bci-wmn-card')) result.push(child);
      result.push(...child.querySelectorAll(selector));
    }
    return result;
  }
}
const ids = ['bci-wmn', 'bci-wmn-queue', 'bci-wmn-detail', 'bci-wmn-status',
  'bci-wmn-asof', 'bci-wmn-coverage', 'bci-wmn-search', 'bci-wmn-view',
  'bci-wmn-lane', 'bci-wmn-refresh', 'bci-wmn-load-more'];
const nodes = Object.fromEntries(ids.map(id => [id, new Element()]));
const requests = [], timers = new Map(), trialOpens = [];
let timerId = 0;
const document = {
  readyState: 'complete', documentElement: new Element('html'),
  getElementById: id => nodes[id] || null, createElement: tag => new Element(tag),
  createTextNode: value => { const node = new Element('#text'); node.textContent = value; return node; },
  listeners: {},
  addEventListener: Element.prototype.addEventListener,
  dispatch: Element.prototype.dispatch,
};
const window = {
  setTimeout(callback, delay) { timers.set(++timerId, { callback, delay }); return timerId; },
  clearTimeout(id) { timers.delete(id); },
  BioCatalystTrialWorkspace: { showGenerationBoundTrialDetail: trial => trialOpens.push(trial) },
};
const fetch = (url, options) => new Promise((resolve, reject) => requests.push({ url, options, resolve, reject }));
const source = fs.readFileSync(process.argv[1], 'utf8');
const marker = source.indexOf('var WMN_API = ');
assert.ok(marker > 0, 'the shipped What Matters Next controller must exist');
const start = source.lastIndexOf('(function () {', marker);
assert.ok(start >= 0);
vm.runInNewContext(source.slice(start), { document, window, fetch, AbortController, URLSearchParams, console });
const authority = { classification: 'research_priority_only', trade_origination: false,
  changes_availability: false, position_sizing: false, prophet_admission: false };
function row(symbol) {
  const estimate = { state: 'NOT_ESTIMABLE', value: null, reason_code: 'owner_not_admitted', evidence_refs: [] };
  return { event_fact_ref: 'event-' + symbol, event_family: 'issuer_readout_guidance',
    row_key: { issuer_id: 'issuer-' + symbol }, timing: {},
    issuer: { state: 'resolved', securities: [{ display_symbol: symbol }] },
    links: { stock_research: [] }, research_priority: { disposition: 'SELECTED', lane: 'MONITOR',
      method_id: 'biocatalyst.research_triage.v1', authority },
    probability: estimate, materiality: estimate, historical_response: estimate, incorporation: estimate };
}
function envelope(symbol, generation = 'G', cursor = null) {
  return { contract_id: 'biocatalyst_what_matters_next.v1', schema_version: '1.0.0',
    method_id: 'biocatalyst.research_triage.v1', generation_id: generation, authority,
    coverage: {}, pagination: { limit: 50, total: 2, next_cursor: cursor }, rows: [row(symbol)] };
}
function dossier(symbol) {
  return { contract_id: 'biocatalyst_wmn_detail.v1', schema_version: '1.0.0', generation_id: 'G',
    authority, event: row(symbol), related_events: [], trial: { nct_id: 'NCT00000001', title: 'Old trial' } };
}
const flush = () => new Promise(resolve => setImmediate(resolve));
async function reply(index, payload, status = 200) {
  assert.ok(requests[index], 'expected request ' + index);
  requests[index].resolve({ status, ok: status >= 200 && status < 300, json: () => Promise.resolve(payload) });
  await flush();
}
async function changeView() {
  nodes['bci-wmn-view'].value = 'history'; nodes['bci-wmn-view'].dispatch('change'); await flush();
}
async function changeLanguage(locale) {
  document.documentElement.setAttribute('data-lang', locale);
  document.dispatch('langchange');
  await flush();
}
function currentRows(symbol) {
  assert.match(nodes['bci-wmn-queue'].textContent, new RegExp(symbol));
  assert.notEqual(nodes['bci-wmn'].dataset.state, 'error');
  assert.notEqual(nodes['bci-wmn'].dataset.state, 'locked');
}
async function run() {
  await flush();
  assert.equal(requests.length, 1);
  const scenario = process.argv[2];
  if (scenario === 'replace_pending' || scenario === 'stale_list_error') {
    await changeView();
    assert.equal(requests.length, 2, 'a changed filter must replace the pending request');
    assert.equal(requests[0].options.signal.aborted, true);
    assert.match(requests[1].url, /view=history/);
    assert.doesNotMatch(requests[1].url, /horizon_days=/);
    if (scenario === 'replace_pending') {
      await reply(0, envelope('OLD'));
      assert.equal(nodes['bci-wmn-refresh'].disabled, true, 'old finally must not clear current loading');
      assert.equal(nodes['bci-wmn-queue'].getAttribute('aria-busy'), 'true');
      assert.doesNotMatch(nodes['bci-wmn-queue'].textContent, /OLD/);
      await reply(1, envelope('NEW'));
    } else {
      await reply(1, envelope('NEW'));
      requests[0].reject(new Error('late transport failure')); await flush();
    }
    currentRows('NEW');
    assert.equal(nodes['bci-wmn-refresh'].disabled, false);
  } else if (scenario === 'stale_detail_success' || scenario === 'stale_detail_error') {
    await reply(0, envelope('OLD'));
    nodes['bci-wmn-queue'].querySelectorAll('.bci-wmn-card')[0].dispatch('click'); await flush();
    assert.equal(requests.length, 2);
    await changeView();
    assert.equal(requests.length, 3);
    await reply(2, envelope('NEW'));
    if (scenario === 'stale_detail_success') await reply(1, dossier('OLD'));
    else { requests[1].reject(new Error('late detail failure')); await flush(); }
    assert.equal(requests[1].options.signal.aborted, true, 'replacement queue must cancel selected detail');
    assert.match(nodes['bci-wmn-detail'].textContent, /Choose an event/);
    assert.doesNotMatch(nodes['bci-wmn-detail'].textContent, /OLD|Dossier unavailable/);
    assert.equal(trialOpens.length, 0, 'a superseded detail cannot open the trial workspace');
    currentRows('NEW');
  } else if (scenario === 'stale_refresh_409' || scenario === 'stale_refresh_generation') {
    await reply(0, envelope('OLD', 'G', 'cursor-1'));
    nodes['bci-wmn-load-more'].dispatch('click'); await flush();
    if (scenario === 'stale_refresh_409') await reply(1, {}, 409);
    else await reply(1, envelope('STALE', 'OTHER'));
    assert.equal(timers.size, 1);
    await changeView(); await reply(2, envelope('NEW'));
    for (const [id, timer] of [...timers]) { timers.delete(id); timer.callback(); }
    await flush();
    assert.equal(requests.length, 3, 'old recovery timer must not replace a newer query');
    currentRows('NEW');
  } else if (scenario === 'current_refresh_409' || scenario === 'current_refresh_generation') {
    await reply(0, envelope('OLD', 'G', 'cursor-1'));
    nodes['bci-wmn-load-more'].dispatch('click'); await flush();
    if (scenario === 'current_refresh_409') await reply(1, {}, 409);
    else await reply(1, envelope('STALE', 'OTHER'));
    assert.equal(timers.size, 1);
    for (const [id, timer] of [...timers]) { timers.delete(id); timer.callback(); }
    await flush();
    assert.equal(requests.length, 3, 'the current recovery must refresh after its finally');
    assert.doesNotMatch(requests[2].url, /cursor=/);
    await reply(2, envelope('NEW', 'OTHER'));
    currentRows('NEW');
  } else if (scenario === 'detail_replaced_error') {
    const first = envelope('FIRST'); first.rows.push(row('SECOND'));
    await reply(0, first);
    const cards = nodes['bci-wmn-queue'].querySelectorAll('.bci-wmn-card');
    cards[0].dispatch('click'); await flush();
    cards[1].dispatch('click'); await flush();
    const second = dossier('SECOND'); second.trial = null;
    await reply(2, second);
    await reply(1, {}, 409);
    assert.match(nodes['bci-wmn-detail'].textContent, /SECOND/);
    assert.doesNotMatch(nodes['bci-wmn-detail'].textContent, /Research cut changed/);
  } else if (scenario === 'repeated_replacement') {
    await changeView();
    nodes['bci-wmn-view'].value = 'reconcile'; nodes['bci-wmn-view'].dispatch('change'); await flush();
    assert.equal(requests.length, 3);
    await reply(0, {}, 403);
    await reply(1, envelope('OLD'));
    assert.equal(nodes['bci-wmn-refresh'].disabled, true);
    assert.notEqual(nodes['bci-wmn'].dataset.state, 'locked');
    await reply(2, envelope('NEW')); currentRows('NEW');
  } else if (scenario === 'append') {
    await reply(0, envelope('FIRST', 'G', 'cursor-1'));
    nodes['bci-wmn-load-more'].dispatch('click'); await flush();
    nodes['bci-wmn-load-more'].dispatch('click'); await flush();
    assert.equal(requests.length, 2, 'only one append may be in flight');
    assert.match(requests[1].url, /cursor=cursor-1/);
    await reply(1, envelope('SECOND'));
    currentRows('FIRST'); currentRows('SECOND');
    assert.equal(nodes['bci-wmn-load-more'].hidden, true);
  } else if (scenario === 'current_lock') {
    await reply(0, {}, 403);
    assert.equal(nodes['bci-wmn'].dataset.state, 'locked');
    assert.match(nodes['bci-wmn-queue'].textContent, /Full access is required/);
    assert.equal(nodes['bci-wmn-refresh'].disabled, false);
  } else if (['language_locked', 'language_error', 'language_append_locked', 'language_append_error'].includes(scenario)) {
    const append = scenario.includes('_append_');
    const locked = scenario.endsWith('_locked');
    if (append) {
      await reply(0, envelope('FIRST', 'G', 'cursor-1'));
      nodes['bci-wmn-load-more'].dispatch('click');
      await flush();
    }
    await reply(append ? 1 : 0, {}, locked ? 403 : 503);
    const requestCount = requests.length;
    for (const locale of ['zh', 'en']) {
      await changeLanguage(locale);
      const expectedQueue = locked
        ? (locale === 'zh'
          ? '需要完整访问权限才能显示生物科技研究优先项。'
          : 'Full access is required before biotechnology research priorities can be shown.')
        : (locale === 'zh'
          ? '“下一步看什么”暂时不可用。不会推断任何研究优先级。'
          : 'What Matters Next is temporarily unavailable. No research priority is inferred.');
      const expectedStatus = locked
        ? (locale === 'zh' ? '需要完整访问权限' : 'Full access required')
        : (locale === 'zh' ? '决策智能数据暂不可用' : 'Decision-intelligence cut unavailable');
      assert.equal(nodes['bci-wmn'].dataset.state, locked ? 'locked' : 'error');
      assert.equal(nodes['bci-wmn-queue'].textContent, expectedQueue);
      assert.equal(nodes['bci-wmn-status'].textContent, expectedStatus);
      assert.equal(nodes['bci-wmn-queue'].querySelectorAll('.bci-wmn-card').length, 0,
        'language change must not resurrect rows after a failed request');
      assert.equal(nodes['bci-wmn-asof'].textContent, '');
      assert.equal(nodes['bci-wmn-coverage'].children.length, 0);
      assert.equal(nodes['bci-wmn-load-more'].hidden, true);
      assert.equal(nodes['bci-wmn-queue'].getAttribute('aria-busy'), 'false');
      assert.equal(nodes['bci-wmn-refresh'].disabled, false);
      assert.equal(requests.length, requestCount, 'localization must not refetch');
    }
  } else if (scenario === 'language_pending' || scenario === 'language_append_pending') {
    const append = scenario === 'language_append_pending';
    if (append) {
      await reply(0, envelope('FIRST', 'G', 'cursor-1'));
      nodes['bci-wmn-load-more'].dispatch('click');
      await flush();
    }
    const pendingIndex = append ? 1 : 0;
    const requestCount = requests.length;
    await changeLanguage('zh');
    assert.equal(nodes['bci-wmn-queue'].getAttribute('aria-busy'), 'true');
    assert.equal(nodes['bci-wmn-refresh'].disabled, true);
    assert.equal(nodes['bci-wmn-load-more'].disabled, true);
    assert.equal(requests.length, requestCount, 'language change must not replace the request');
    assert.equal(requests[pendingIndex].options.signal.aborted, false);
    if (append) {
      currentRows('FIRST');
      assert.equal(nodes['bci-wmn-load-more'].hidden, false);
    } else {
      assert.match(nodes['bci-wmn-queue'].textContent, /Loading research priorities|正在加载研究优先项/);
    }
    await reply(pendingIndex, envelope(append ? 'SECOND' : 'NEW'));
    if (append) {
      currentRows('FIRST');
      currentRows('SECOND');
    } else currentRows('NEW');
    assert.equal(nodes['bci-wmn-queue'].getAttribute('aria-busy'), 'false');
    assert.equal(nodes['bci-wmn-refresh'].disabled, false);
    assert.equal(nodes['bci-wmn-load-more'].disabled, false);
    assert.equal(nodes['bci-wmn-load-more'].hidden, true);
  } else throw new Error('unknown scenario ' + scenario);
}
run().catch(error => { console.error(error); process.exitCode = 1; });
"""


@pytest.mark.parametrize("asset", ["templates/biocatalyst.js", "site/biocatalyst.js"])
@pytest.mark.parametrize("scenario", ['replace_pending', 'stale_list_error', 'stale_detail_success', 'stale_detail_error', 'stale_refresh_409', 'stale_refresh_generation', 'current_refresh_409', 'current_refresh_generation', 'detail_replaced_error', 'repeated_replacement', 'append', 'current_lock', 'language_locked', 'language_error', 'language_append_locked', 'language_append_error', 'language_pending', 'language_append_pending'])
def test_what_matters_next_async_request_ownership(asset: str, scenario: str) -> None:
    node = shutil.which("node")
    assert node is not None, "Node is required for the shipped-client ownership regression"
    subprocess.run(
        [node, "-e", _WMN_REQUEST_RACE_DRIVER, str(ROOT / asset), scenario],
        check=True, capture_output=True, text=True, timeout=15,
    )

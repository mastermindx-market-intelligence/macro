"""Static contract pins for the four Sector Intelligence receivers (SIC-RCV).

Pure-python text checks against research/sector_completion_20261021/RECEIVER_CONTRACTS.md:
no browser, no network, no site/ or data/ fixtures, no engine imports (keeps the suite
on the tier-gate job's minimal venv line — see the run line at
.github/ci/legacy-jobs.yml:6289). If one of these fails, the CONTRACT changed or an
observed receiver drifted from it; update both together.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "research" / "sector_completion_20261021" / "RECEIVER_CONTRACTS.md"
LEGACY_JOBS = ROOT / ".github" / "ci" / "legacy-jobs.yml"

#: every page template / JS surface the contract names, per receiver.
PAGE_TEMPLATES = [
    "templates/research_vault.html.j2",
    "templates/research_index.html.j2",
    "templates/research_report.html.j2",
    "templates/research_screener.html.j2",
    "templates/fif_saved_briefcase.js",
    "templates/watchlist.html.j2",
    "templates/watchlist.js",
    "templates/watchstore.js",
    "templates/watchlist_risk.js",
    "templates/account.js",
    "templates/dashboard.html.j2",
    "templates/us_stocks_v2.html.j2",
    "templates/us_stocks_lab.html.j2",
    "templates/_sector_prophet_context.html.j2",
    "templates/_sector_prophet_context.js.j2",
    "templates/confluence_screener.html.j2",
    "templates/sector.html.j2",
    "templates/sector_cycles.js",
    "templates/mtf.js",
    "templates/theme.js",
]

#: (parameter literal, cited reader file) — every URL parameter the contract lists.
PARAM_READS = [
    ("si_sector", "templates/_sector_prophet_context.js.j2"),
    ("life", "templates/dashboard.html.j2"),
    ("#wl=", "templates/watchlist.js"),
    ("symbol", "templates/theme.js"),
    ("sym", "templates/theme.js"),
]

#: (storage key / endpoint string, cited file) — quoted verbatim in the contract.
STORAGE_STRINGS = [
    ("mastermind.filing_forensics.saved_research.v1", "templates/fif_saved_briefcase.js"),
    ("mdash.watchlist.v1", "templates/watchlist.js"),
    ("mdash.ws.mode.v1", "templates/watchlist.js"),
    ("mdash.ws.entry.v1", "templates/watchlist.js"),
    ("mm.pact.watchlist_add", "templates/watchlist.js"),
    ("mdash.wl.", "templates/watchstore.js"),
    ("mdash.watchstore.folded.v1", "templates/watchstore.js"),
    ("mdash.pf.v1", "templates/watchstore.js"),
    ("mdash.watchstore.pf_folded.v1", "templates/watchstore.js"),
    ("wl_auth_reloaded", "templates/watchstore.js"),
    ("mdx_stocktable_us", "templates/dashboard.html.j2"),
    ("localStorage.setItem('lang', lg)", "templates/theme.js"),
    ("sb-", "templates/account.js"),
    ("-auth-token", "templates/account.js"),
    ("/api/account/prefs", "templates/account.js"),
    ("/api/account/email", "templates/account.js"),
    ("factor_betas.json", "templates/watchlist_risk.js"),
    ("transmission_chains.json", "templates/watchlist_risk.js"),
    ("/rest/v1/watchlists", "scripts/run_watchlist_sentinel.py"),
    ("watchlist_alerts.jsonl", "scripts/run_watchlist_sentinel.py"),
    ("watchlist_sentinel_states.json", "scripts/run_watchlist_sentinel.py"),
    ("watchlist_sentinel_cooldown.json", "scripts/run_watchlist_sentinel.py"),
    ("signal_gate.json", "scripts/run_watchlist_sentinel.py"),
    ("DISCORD_WEBHOOK_WATCHLIST", "scripts/run_watchlist_sentinel.py"),
    ("/rest/v1/", "engine/fif_saved_research_notifications.py"),
    ("alert_outbox", "engine/fif_saved_research_notifications.py"),
    ("Filing Forensics", "engine/fif_saved_research_notifications.py"),
]

#: (output-path string, builder source) — every builder output the contract records.
BUILDER_OUTPUTS = [
    ("us_stocks.html", "scripts/build_site.py"),
    ("watchlist.html", "scripts/build_site.py"),
    ("sector.html.j2", "scripts/build_site.py"),
    ('f"{fund}.html"', "scripts/build_site.py"),
    ("premiumdata", "scripts/build_site.py"),
    ("us_stocks.json", "scripts/build_site.py"),
    ("us_stocks_v2.html", "scripts/build_stock_board_v2.py"),
    ("us_stocks_lab.html", "engine/pick_lab/render.py"),
    ("research_vault.html", "scripts/build_research_vault.py"),
    ("catalog.json", "scripts/build_research_vault.py"),
    ("research_screener.html", "scripts/build_research_screener.py"),
    ("research_screener.json", "scripts/build_research_screener.py"),
    ("confluence_screener.html", "scripts/build_confluence_screener.py"),
    ("confluence_screener.json", "scripts/build_confluence_screener.py"),
    ("tech_confluence.json", "scripts/build_confluence_screener.py"),
]

#: contract section headings, in the frozen order.
CONTRACT_SECTIONS = [
    "## Research receiver",
    "## Watch/save owner",
    "## Prophet/Screener destination",
    "## Sector Dossier page",
    "## Cross-receiver facts",
    "## Gaps",
    "## Evidence",
]

#: surfaces the contract records as reading NO url parameter (grep → 0 hits).
#: RI05 MAJOR-2: research_vault.html.j2 left this list — its #si-research-entry
#: island reads URL state (new URL(document.URL).searchParams evades the three
#: patterns below, which is exactly the pin evasion the repair closes); the
#: island's exact six-parameter set is pinned negatively below.
NO_PARAM_SURFACES = [
    "templates/research_index.html.j2",
    "templates/research_report.html.j2",
    "templates/research_screener.html.j2",
    "templates/sector.html.j2",
    "templates/confluence_screener.html.j2",
    "templates/mtf.js",
]

_PARAM_PATTERNS = ("URLSearchParams", "location.search", "location.hash")

#: the SIC-I05R receiver island's exact parameter set (RI05 MAJOR-2).
RESEARCH_ENTRY_PARAMS = {
    "si_subject",
    "si_q",
    "si_snap",
    "si_obs",
    "si_ev",
    "si_origin",
}


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_every_contract_template_exists():
    missing = [p for p in PAGE_TEMPLATES if not (ROOT / p).is_file()]
    assert not missing, f"contract names templates that do not exist: {missing}"


def test_every_contract_parameter_appears_in_its_reader():
    missing = [
        (param, path)
        for param, path in PARAM_READS
        if param not in _read(path)
    ]
    assert not missing, f"reader files no longer contain the contract parameters: {missing}"


def test_every_contract_storage_string_appears_in_its_file():
    missing = [
        (key, path)
        for key, path in STORAGE_STRINGS
        if key not in _read(path)
    ]
    assert not missing, f"cited files no longer contain the contract strings: {missing}"


def test_every_builder_output_path_appears_in_builder_source():
    missing = [
        (out, path)
        for out, path in BUILDER_OUTPUTS
        if out not in _read(path)
    ]
    assert not missing, f"builders no longer name these contract outputs: {missing}"


def test_no_param_surfaces_still_read_nothing():
    """Research/dossier/confluence surfaces: the contract's NOT FOUND pre-fill rows."""
    for path in NO_PARAM_SURFACES:
        text = _read(path)
        hits = [p for p in _PARAM_PATTERNS if p in text]
        assert not hits, f"{path} now reads url state ({hits}); contract NOT FOUND rows drifted"


def test_research_vault_island_reads_exactly_the_six_si_params():
    """RI05 MAJOR-2 negative pin: the vault island is the one research surface
    that reads URL state, and it reads exactly the six si_* parameters — any
    seventh reader (raw('…') or a direct searchParams.get('…')) fails this."""
    html = _read("templates/research_vault.html.j2")
    start = html.index("/* SIC-I05R")
    script = html[start:html.index("</script>", start)]
    reads = set(re.findall(r"raw\('([^']+)'\)", script))
    reads |= set(re.findall(r"(?:searchParams|params)\.get\('([^']+)'\)", script))
    assert reads == RESEARCH_ENTRY_PARAMS, (
        f"the research entry island must read exactly {sorted(RESEARCH_ENTRY_PARAMS)}, "
        f"found {sorted(reads)}"
    )


def test_served_prophet_page_is_dashboard_in_stocks_mode():
    """The contract's premise correction: /us_stocks.html renders dashboard.html.j2."""
    src = _read("scripts/build_site.py")
    assert 'env.get_template("dashboard.html.j2")' in src
    assert 'write_page(site / "us_stocks.html"' in src
    assert '_dash.render' in src
    # and the v2 template is NOT what serves that path
    v2 = _read("scripts/build_stock_board_v2.py")
    assert 'write_page(site / "us_stocks_v2.html"' in v2


def test_prophet_partial_included_in_stocks_mode_only():
    tpl = _read("templates/dashboard.html.j2")
    assert (
        '{% if mode == "stocks" %}{% include "_sector_prophet_context.html.j2" %}{% endif %}'
        in tpl
    )


def test_si_sector_identity_only_path_to_screener():
    """si_sector never filters on arrival; the filter owner is USStockTable."""
    partial = _read("templates/_sector_prophet_context.js.j2")
    assert "params.getAll('si_sector')" in partial
    assert "us_stocks.html?si_sector=" in partial
    dash = _read("templates/dashboard.html.j2")
    assert "_selectSector" in dash and "setSectorFilter" in dash


def test_watchlist_share_hash_reader_and_strip():
    js = _read("templates/watchlist.js")
    assert "consumeShareHash" in js
    assert "h.match(/^#wl=(.+)$/)" in js
    assert "history.replaceState(null, '', location.pathname + location.search)" in js


def test_supabase_cfg_baked_by_watchlist_builder():
    tpl = _read("templates/watchlist.html.j2")
    assert "SUPABASE_CFG" in tpl
    src = _read("scripts/build_site.py")
    assert "supabase_cfg_json" in src


def test_dossier_identifier_membership_and_links():
    src = _read("scripts/build_site.py")
    assert 'US_SECTOR_PAGE.get(fund, "sectors/" + fund + ".html")' in src
    tpl = _read("templates/sector.html.j2")
    assert "../stock.html#" in tpl
    assert '{% include "_site_nav.html.j2" %}' in tpl
    assert "_public_nav" not in tpl
    cycles = _read("templates/sector_cycles.js")
    assert "function sectorPageHref(" in cycles and "US_SECTOR_PAGE" in cycles
    collector = _read("collectors/sector_holdings.py")
    assert "As of" in collector and "history.parquet" in collector


def test_langchange_listener_census():
    """Cross-receiver fact: only the watch family + the Prophet partial re-render on langchange."""
    for path in (
        "templates/watchlist.js",
        "templates/watchstore.js",
        "templates/account.js",
        "templates/_sector_prophet_context.js.j2",
    ):
        assert "langchange" in _read(path), f"{path} lost its langchange listener"


def test_contract_file_sections_in_frozen_order():
    text = CONTRACT.read_text(encoding="utf-8")
    pos = -1
    for heading in CONTRACT_SECTIONS:
        idx = text.find(heading)
        assert idx > pos, f"contract section {heading!r} missing or out of order"
        pos = idx


def test_contract_records_premise_correction_and_verdicts():
    text = CONTRACT.read_text(encoding="utf-8")
    assert "Premise correction" in text
    flat = " ".join(text.split())
    assert "NOT FOUND" in flat


def test_legacy_jobs_gate_line_lists_contract_suite():
    """The one CI line this packet edits must keep the gate suite and add this file."""
    yml = LEGACY_JOBS.read_text(encoding="utf-8")
    line = (
        "run: python -m pytest tests/test_sector_central_gate.py "
        "tests/test_sector_central_contract.py tests/test_sector_receiver_contracts.py -q"
    )
    assert line in yml, "tier-gate run line no longer registers test_sector_receiver_contracts.py"
    # the neighbouring suites' registrations are untouched
    assert "run: python -m pytest tests/test_sector_central.py -q" in yml

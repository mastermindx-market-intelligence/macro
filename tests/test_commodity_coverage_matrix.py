"""Tests for engine.commodity_coverage_matrix (B-F09-6, MO-DELTA-029)."""
from __future__ import annotations

import re

import pytest
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from engine.commodity_coverage_matrix import FAMILIES, PUBLIC_SOURCES, compute_coverage_matrix

_REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
_STATES = {"covered", "partial", "none"}
_BANNED_JARGON = re.compile(r"\.py|/|z-score|\bn=\d|percentile|falsifier|refuted|证伪")
_BANNED_CAUSAL = re.compile(r"drives|causes|will push|leads to|推动|导致|将带动")


def _fake_root(tmp_path, *, energy_producer=True, energy_price_artifact=True,
               energy_supply_artifacts=True):
    root = tmp_path
    (root / "engine").mkdir(parents=True, exist_ok=True)
    (root / "data" / "yahoo").mkdir(parents=True, exist_ok=True)
    (root / "data" / "eia").mkdir(parents=True, exist_ok=True)
    if energy_producer:
        (root / "engine" / "commodity_inputs.py").write_text("# fake\n")
        (root / "engine" / "commodity_supply_context.py").write_text("# fake\n")
    if energy_price_artifact:
        # ALL-of (MAJOR-1 fix): energy's price cell names oil/gas/fuels across
        # 4 tickers, so a "covered" fixture must create every one of them, not
        # a single stand-in.
        for tk in ("CL_F", "NG_F", "HO_F", "RB_F"):
            (root / "data" / "yahoo" / f"{tk}.parquet").write_bytes(b"x")
        (root / "data" / "yahoo" / "GC_F.parquet").write_bytes(b"x")
        (root / "data" / "yahoo" / "HG_F.parquet").write_bytes(b"x")
        (root / "data" / "yahoo" / "ZC_F.parquet").write_bytes(b"x")
    if energy_supply_artifacts:
        for f in ("crude_stocks", "crude_production", "crude_imports"):
            (root / "data" / "eia" / f"{f}.parquet").write_bytes(b"x")
    return root


def test_1_frozen_registry_five_families_in_order():
    ids = [f["id"] for f in FAMILIES]
    assert ids == ["energy", "precious", "base", "agri", "techmat"]


def test_2_every_row_carries_bilingual_strings_and_valid_state(tmp_path):
    root = _fake_root(tmp_path)
    rows = compute_coverage_matrix(root=root)["rows"]
    assert len(rows) == 5
    for r in rows:
        assert r["family_en"] and r["family_zh"]
        assert r["state"] in _STATES
        for k in ("state_en", "state_zh", "price_en", "price_zh", "supply_en", "supply_zh"):
            assert isinstance(r[k], str) and r[k]


def test_3_techmat_present_and_none():
    # techmat has no producers declared at all — verify from the frozen registry
    # directly (no filesystem needed) that its axes are unset.
    techmat = next(f for f in FAMILIES if f["id"] == "techmat")
    assert techmat["price"] is None and techmat["supply"] is None


def test_3b_techmat_row_state_is_none(tmp_path):
    root = _fake_root(tmp_path)
    rows = compute_coverage_matrix(root=root)["rows"]
    techmat = next(r for r in rows if r["id"] == "techmat")
    assert techmat["state"] == "none"
    assert techmat["price_en"] == "Not covered yet"
    assert techmat["supply_en"] == "Not covered yet"


def test_4_covered_axis_names_existing_producer_and_public_source(tmp_path):
    root = _fake_root(tmp_path)
    rows = compute_coverage_matrix(root=root)["rows"]
    energy = next(r for r in rows if r["id"] == "energy")
    assert energy["state"] == "covered"
    assert energy["sources"], "covered rows must carry at least one source"
    for s in energy["sources"]:
        assert (root / s["producer"]).exists()
        assert s["source_en"] in PUBLIC_SOURCES or s["source_zh"] in PUBLIC_SOURCES


def test_5_glance_strings_contain_no_jargon_no_paths(tmp_path):
    root = _fake_root(tmp_path)
    rows = compute_coverage_matrix(root=root)["rows"]
    for r in rows:
        for k in ("family_en", "family_zh", "state_en", "state_zh",
                  "price_en", "price_zh", "supply_en", "supply_zh"):
            assert not _BANNED_JARGON.search(r[k]), (k, r[k])
    # producer paths only ever appear inside sources[*].producer
    for r in rows:
        for s in r["sources"]:
            assert "/" in s["producer"] or s["producer"].endswith(".py")


def test_6_filesystem_derived_deleting_artifact_flips_state(tmp_path):
    root = _fake_root(tmp_path)
    rows = compute_coverage_matrix(root=root)["rows"]
    assert next(r for r in rows if r["id"] == "energy")["state"] == "covered"

    (root / "data" / "eia" / "crude_stocks.parquet").unlink()
    rows2 = compute_coverage_matrix(root=root)["rows"]
    energy2 = next(r for r in rows2 if r["id"] == "energy")
    assert energy2["state"] == "partial"
    # producer still exists, artifact gone: an UNKNOWN, not shaped as an EMPTY.
    assert energy2["supply_en"] == "Built, waiting on data"

    # deleting the producer module also degrades the axis (no producer -> no read)
    (root / "engine" / "commodity_supply_context.py").unlink()
    rows3 = compute_coverage_matrix(root=root)["rows"]
    energy3 = next(r for r in rows3 if r["id"] == "energy")
    assert energy3["state"] == "partial"


def test_7_no_causal_overstatement(tmp_path):
    root = _fake_root(tmp_path)
    rows = compute_coverage_matrix(root=root)["rows"]
    for r in rows:
        for k in ("price_en", "price_zh", "supply_en", "supply_zh"):
            assert not _BANNED_CAUSAL.search(r[k]), (k, r[k])


def test_8_render_diff_contained_between_markers():
    tpl_dir = _REPO_ROOT / "templates"
    env = Environment(loader=FileSystemLoader(str(tpl_dir)), autoescape=True,
                       undefined=StrictUndefined)
    # commodities.html.j2 is a large real-data page; we only exercise the
    # coverage-matrix insertion, so we can't fully render it here without the
    # full site context. Instead assert statically that the inserted block in
    # the template source is fully bounded by its own markers.
    src = (tpl_dir / "commodities.html.j2").read_text()
    start = src.index("coverage-matrix:start")
    end = src.index("coverage-matrix:end")
    assert start < end
    block = src[start:end]
    # sanity: nothing outside {coverage} usage leaks past the markers
    assert "cov-panel" in block


def test_9_multi_commodity_claims_are_backed_by_one_artifact_per_named_commodity():
    """B3 review MAJOR-5: a family whose cell copy names N commodities must
    check N filesystem artifacts — one ticker standing proxy for every named
    commodity is exactly the overclaim the review measured (e.g. "precious"
    printed gold/silver/platinum/palladium on GC_F.parquet alone)."""
    by_id = {f["id"]: f for f in FAMILIES}
    assert len(by_id["energy"]["price"]["artifacts"]) >= 3    # oil, gas, fuels
    assert len(by_id["precious"]["price"]["artifacts"]) == 4  # gold/silver/platinum/palladium
    assert len(by_id["agri"]["price"]["artifacts"]) == 8      # corn..cotton
    for fam_id in ("energy", "precious", "agri"):
        artifacts = by_id[fam_id]["price"]["artifacts"]
        assert len(set(artifacts)) == len(artifacts), "no duplicate tickers"
        for artifact in artifacts:
            assert artifact.startswith("data/yahoo/") and artifact.endswith(".parquet")


def test_10_partial_artifact_set_never_claims_full_multi_commodity_coverage(tmp_path):
    """B3 round-2 review MAJOR-1: `_axis_cell` was ANY-of over `artifacts`, so
    with only `data/yahoo/GC_F.parquet` on disk the precious row still reported
    state 'partial'/'covered'-shaped copy naming gold/silver/platinum/palladium
    (measured live). The check must be ALL-of: every ticker the cell text names
    has to actually exist before that text is shown as a 'read' claim."""
    root = tmp_path
    (root / "engine").mkdir(parents=True, exist_ok=True)
    (root / "data" / "yahoo").mkdir(parents=True, exist_ok=True)
    (root / "engine" / "commodity_inputs.py").write_text("# fake\n")
    # Only ONE of the four precious-metal tickers on disk. precious has no
    # supply axis (FAMILIES[1]["supply"] is None), so "covered" (price+supply)
    # is never reachable for this family — the axis under test is the PRICE
    # cell's own read/not-read claim, not the row's overall state.
    (root / "data" / "yahoo" / "GC_F.parquet").write_bytes(b"x")

    rows = compute_coverage_matrix(root=root)["rows"]
    precious = next(r for r in rows if r["id"] == "precious")
    assert precious["price_en"] != "Daily prices for gold, silver, platinum and palladium"
    assert not precious["sources"], "a partial artifact set must not cite itself as a read source"

    # Now complete the set: all four exist -> the full claim is finally honest.
    for tk in ("SI_F", "PL_F", "PA_F"):
        (root / "data" / "yahoo" / f"{tk}.parquet").write_bytes(b"x")
    rows2 = compute_coverage_matrix(root=root)["rows"]
    precious2 = next(r for r in rows2 if r["id"] == "precious")
    assert precious2["state"] == "partial"  # "prices only" — precious has no supply axis
    assert precious2["price_en"] == "Daily prices for gold, silver, platinum and palladium"
    assert precious2["sources"], "a complete artifact set must now cite its source"


# ---------------------------------------------------------------------------
# B-F09-B5-1 — semis / critical-tech source census (append-only; tests 11-20)
# ---------------------------------------------------------------------------

_CENSUS = _REPO_ROOT / "research" / "market_intelligence_productization" / \
    "MARKET_ONTOLOGY_F09_SEMIS_SOURCE_CENSUS_2026-09-09.md"

_CENSUS_START = "<!-- census-table:start -->"
_CENSUS_END = "<!-- census-table:end -->"
_CENSUS_HEADER = [
    "candidate_source",
    "sub_domain",
    "what_it_would_cover",
    "public_or_commercial",
    "integrated_today",
    "licence_required",
    "verification_method",
    "provenance",
    "status",
    "verified_negative_statement",
]
_STATUS_VOCAB = {
    "PUBLIC-BUILDABLE",
    "PUBLIC-BUILDABLE-DARK",
    "COMMERCIAL-GATE",
    "VERIFIED-NEGATIVE",
    "OUT-OF-SCOPE-THIS-PACKET",
}
_IN_SUBDOMAINS = (
    "ai_semiconductors",
    "semicap_equipment",
    "rare_earth_critical_min",
    "nuclear_power",
)
_ADJACENT_SUBDOMAINS = ("solar", "grid_electrification")
_IN_TERMINAL = {
    "PUBLIC-BUILDABLE",
    "PUBLIC-BUILDABLE-DARK",
    "COMMERCIAL-GATE",
    "VERIFIED-NEGATIVE",
}
_PROVENANCE_VOCAB = {"KNOWN-FROM-REPO", "KNOWN-FROM-MODEL-KNOWLEDGE"}
_INTEGRATED_PATH = re.compile(r"^[\w./-]+\.(py|yml|yaml|md|csv):\d+$")
_SEP_CELL = re.compile(r"^:?-+:?$")
_FORBIDDEN_STATUS = re.compile(r"(?i)unverified|unknown|tbd|pending|n/?a")
_MATRIX_CSV = (
    _REPO_ROOT / "research" / "market_intelligence_productization" /
    "MARKET_ONTOLOGY_F09_COMMODITY_COVERAGE_MATRIX_2026-09-02.csv"
)


def _split_md_row(line: str) -> list[str]:
    raw = line.strip()
    if not raw.startswith("|"):
        return []
    tmp = raw.replace("\\|", "\x00")
    parts = [p.replace("\x00", "|").strip() for p in tmp.split("|")]
    if parts and parts[0] == "":
        parts = parts[1:]
    if parts and parts[-1] == "":
        parts = parts[:-1]
    return parts


def _census_table_rows():
    text = _CENSUS.read_text(encoding="utf-8")
    start = text.index(_CENSUS_START)
    end = text.index(_CENSUS_END)
    block = text[start + len(_CENSUS_START):end]
    rows = []
    for line in block.splitlines():
        cells = _split_md_row(line)
        if not cells:
            continue
        if all(_SEP_CELL.match(c) for c in cells):
            continue
        rows.append(cells)
    return rows


def _census_data_rows():
    rows = _census_table_rows()
    assert rows, "census table is empty"
    header, data = rows[0], rows[1:]
    assert header == _CENSUS_HEADER
    return data


def test_census_exists_and_is_marker_bounded():
    assert _CENSUS.exists()
    text = _CENSUS.read_text(encoding="utf-8")
    assert text.count(_CENSUS_START) == 1
    assert text.count(_CENSUS_END) == 1
    assert text.index(_CENSUS_START) < text.index(_CENSUS_END)


def test_census_table_header_is_the_frozen_ten_columns():
    rows = _census_table_rows()
    assert rows, "no table rows inside census markers"
    assert rows[0] == _CENSUS_HEADER


def test_census_every_row_status_is_in_the_closed_vocabulary():
    for cells in _census_data_rows():
        assert len(cells) == 10, cells
        status = cells[8]
        assert status, cells
        assert status in _STATUS_VOCAB, status


def test_census_no_row_is_left_unverified():
    text = _CENSUS.read_text(encoding="utf-8")
    start = text.index(_CENSUS_START)
    end = text.index(_CENSUS_END)
    block = text[start:end]
    for cells in _census_data_rows():
        status = cells[8]
        assert not _FORBIDDEN_STATUS.search(status), status
        assert "UNVERIFIED" not in status
    # Literal UNVERIFIED never appears in column 9 of the table block.
    for line in block.splitlines():
        cells = _split_md_row(line)
        if len(cells) != 10:
            continue
        if all(_SEP_CELL.match(c) for c in cells):
            continue
        if cells == _CENSUS_HEADER:
            continue
        assert "UNVERIFIED" not in cells[8], cells[8]


def test_census_every_in_scope_subdomain_reaches_a_terminal_status():
    by_sub = {s: [] for s in _IN_SUBDOMAINS}
    for cells in _census_data_rows():
        sub, status = cells[1], cells[8]
        if sub in by_sub:
            by_sub[sub].append(status)
        if status == "OUT-OF-SCOPE-THIS-PACKET":
            assert sub in _ADJACENT_SUBDOMAINS, (sub, status)
        else:
            if sub in _ADJACENT_SUBDOMAINS:
                raise AssertionError(
                    f"adjacent sub-domain {sub} must be OUT-OF-SCOPE-THIS-PACKET"
                )
    for sub, statuses in by_sub.items():
        assert statuses, f"no rows for in-scope sub-domain {sub}"
        for status in statuses:
            assert status in _IN_TERMINAL, (sub, status)


def test_census_commercial_gate_rows_name_vendor_and_licence_class():
    banned = {"", "unknown", "TBD", "n/a"}
    for cells in _census_data_rows():
        if cells[8] != "COMMERCIAL-GATE":
            continue
        assert cells[0], cells
        assert cells[5], cells
        assert cells[3] == "COMMERCIAL", cells
        assert cells[5] not in banned, cells[5]


def test_census_verified_negative_rows_carry_the_search_performed():
    for cells in _census_data_rows():
        statement = cells[9]
        if cells[8] == "VERIFIED-NEGATIVE":
            assert statement != "n/a", cells
            assert len(statement) >= 40, statement
        else:
            assert statement == "n/a", cells


def test_census_every_row_has_a_verification_method_and_provenance():
    for cells in _census_data_rows():
        method, provenance, status = cells[6], cells[7], cells[8]
        assert method, cells
        assert provenance in _PROVENANCE_VOCAB, provenance
        if provenance == "KNOWN-FROM-MODEL-KNOWLEDGE":
            assert method == "NOT-VERIFIED-NO-NETWORK", cells
            assert status != "PUBLIC-BUILDABLE", cells


def test_census_integrated_today_paths_resolve_or_say_NO():
    for cells in _census_data_rows():
        integrated = cells[4]
        if integrated == "NO":
            continue
        assert _INTEGRATED_PATH.match(integrated), integrated
        path, _line = integrated.rsplit(":", 1)
        assert (_REPO_ROOT / path).exists(), path


def test_semis_matrix_row_cites_the_census():
    lines = _MATRIX_CSV.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 44
    semis = [ln for ln in lines if ln.startswith("semiconductors/critical-tech")]
    assert len(semis) == 1, semis
    assert "MARKET_ONTOLOGY_F09_SEMIS_SOURCE_CENSUS_2026-09-09.md" in semis[0]


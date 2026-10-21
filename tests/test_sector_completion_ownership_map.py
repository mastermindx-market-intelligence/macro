"""B01 contract test — the ownership map IS the code.

Pins research/sector_completion_20261021/B01_OWNERSHIP_MAP.md against the repository:
(a) every writer symbol named by the map exists (importlib+hasattr for engines, an AST
    scan of the file for scripts),
(b) every artifact path literal occurs in its writer file's source,
(c) every Artifacts row in the .md matches the Python data below,
(d) every none_native census row's writer source contains NO string-literal dict key
    matching correction/revision/supersede — the R3A-92 proof that no native correction
    contract exists on those surfaces (comments do not count; only ast.Dict keys).

Network-free, data/-free, site/-free. Run: python3 -m pytest -q -p no:cacheprovider
tests/test_sector_completion_ownership_map.py
"""
from __future__ import annotations

import ast
import importlib
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "research" / "sector_completion_20261021" / "B01_OWNERSHIP_MAP.md"

# One row per Artifacts-table row in the .md (same order). native="none_native" feeds
# the R3A-92 no-correction-key proof; the narr row carries the one native revision
# channel found (authored prev_revision -> _ttl.revision_note) and is excluded from it.
ROWS = [
    dict(artifact="site/sector_central.html",
         writer_file="scripts/build_sector_central.py", writer_symbol="main",
         writer_kind="script", path_literals=("sector_central.html",),
         disposition="incorporated", native="none_native"),
    dict(artifact="site/sector_central_data.js",
         writer_file="scripts/build_sector_central.py", writer_symbol="main",
         writer_kind="script", path_literals=("sector_central_data.js",),
         disposition="incorporated", native="none_native"),
    dict(artifact="site/sectordata/sector_central.json",
         writer_file="scripts/build_sector_central.py", writer_symbol="main",
         writer_kind="script", path_literals=("sector_central.json",),
         disposition="remaining", native="none_native"),
    dict(artifact="site/premiumdata/sector_central.json",
         writer_file="scripts/build_sector_central.py", writer_symbol="write_payload",
         writer_kind="script",
         path_literals=("sector_central.json", "_SC_PAYLOAD_DIR", "_SC_PAYLOAD_NAME"),
         disposition="incorporated", native="none_native"),
    dict(artifact="site/sector_cycles.html",
         writer_file="scripts/build_sector_cycles.py", writer_symbol="main",
         writer_kind="script", path_literals=("sector_cycles.html",),
         disposition="incorporated", native="none_native"),
    dict(artifact="site/sector_cycles_data.js",
         writer_file="scripts/build_sector_cycles.py", writer_symbol="main",
         writer_kind="script", path_literals=("sector_cycles_data.js",),
         disposition="incorporated", native="none_native"),
    dict(artifact="site/sector_cycles_series_data.js",
         writer_file="scripts/build_sector_cycles.py", writer_symbol="main",
         writer_kind="script", path_literals=("sector_cycles_series_data.js",),
         disposition="incorporated", native="none_native"),
    dict(artifact="site/sector_cycles_narr_data.js",
         writer_file="scripts/build_sector_cycles.py", writer_symbol="main",
         writer_kind="script", path_literals=("sector_cycles_narr_data.js",),
         disposition="incorporated",
         native="_ttl.revision_note (from authored prev_revision; scripts/_narrative_ttl.py:217-224)"),
    dict(artifact="site/sector_cycles_dna_data.js",
         writer_file="scripts/build_sector_cycles.py", writer_symbol="main",
         writer_kind="script", path_literals=("sector_cycles_dna_data.js",),
         disposition="incorporated", native="none_native"),
    dict(artifact="site/sectordata/sector_cycles.json",
         writer_file="scripts/build_sector_cycles.py", writer_symbol="main",
         writer_kind="script", path_literals=("sector_cycles.json",),
         disposition="remaining", native="none_native"),
    dict(artifact="site/sector_cycles.css + site/sector_cycles.js",
         writer_file="scripts/build_sector_cycles.py", writer_symbol="main",
         writer_kind="script", path_literals=("sector_cycles.css", "sector_cycles.js"),
         disposition="incorporated", native="none_native"),
    dict(artifact="site/mm_charts.js + site/cycle.css",
         writer_file="scripts/build_sector_cycles.py", writer_symbol="main",
         writer_kind="script", path_literals=("mm_charts.js", "cycle.css"),
         disposition="remaining", native="none_native"),
    dict(artifact="data/us_sector_rotation/latest.json",
         writer_file="engine/us_sector_rotation.py", writer_symbol="write_latest",
         writer_kind="engine", path_literals=("latest.json",),
         disposition="incorporated", native="none_native"),
    dict(artifact="data/sector_cycles/forward_log.parquet",
         writer_file="engine/cycle_forward_log.py", writer_symbol="append_forward_log",
         writer_kind="engine", path_literals=("forward_log.parquet",),
         disposition="incorporated", native="none_native"),
    dict(artifact="data/sector_central/calls.parquet",
         writer_file="engine/sector_central_grader.py", writer_symbol="append_central_log",
         writer_kind="engine", path_literals=("calls.parquet",),
         disposition="incorporated", native="none_native"),
    dict(artifact="site/marketdata/rotation_events.json",
         writer_file="scripts/build_rotation_events.py", writer_symbol="build",
         writer_kind="script", path_literals=("rotation_events.json",),
         disposition="incorporated", native="none_native"),
    dict(artifact="site/marketdata/sector_fragmentation.json",
         writer_file="scripts/build_rotation_events.py", writer_symbol="build",
         writer_kind="script", path_literals=("sector_fragmentation.json",),
         disposition="incorporated", native="none_native"),
    dict(artifact="site/live/shock_state.json",
         writer_file="engine/shock_deescalation.py", writer_symbol="build_intraday",
         writer_kind="engine", path_literals=("shock_state.json",),
         disposition="incorporated", native="none_native"),
    dict(artifact="site/policy_lever.json",
         writer_file="scripts/build_policy_lever.py", writer_symbol="build",
         writer_kind="script", path_literals=("policy_lever.json",),
         disposition="incorporated", native="none_native"),
    dict(artifact="site/basketdata/pulse.json",
         writer_file="engine/group_pulse.py", writer_symbol="write_site_artifact",
         writer_kind="engine", path_literals=("pulse.json",),
         disposition="incorporated", native="none_native"),
    dict(artifact="site/basketdata/etf_pulse.json",
         writer_file="scripts/build_theme_addons.py", writer_symbol="main",
         writer_kind="script", path_literals=("etf_pulse.json",),
         disposition="incorporated", native="none_native"),
    dict(artifact="site/basketdata/vol_sentiment.json",
         writer_file="scripts/build_theme_addons.py", writer_symbol="main",
         writer_kind="script", path_literals=("vol_sentiment.json",),
         disposition="incorporated", native="none_native"),
    dict(artifact="site/basketdata/theme_extension.json",
         writer_file="scripts/build_theme_addons.py", writer_symbol="main",
         writer_kind="script", path_literals=("theme_extension.json",),
         disposition="incorporated", native="none_native"),
    dict(artifact="site/basketdata/baskets.json",
         writer_file="scripts/build_baskets.py", writer_symbol="main",
         writer_kind="script", path_literals=("baskets.json",),
         disposition="incorporated", native="none_native"),
]

_CORRECTION_KEY = re.compile(r"correct|revis|supersede", re.I)


def _source(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _script_defines(rel: str, name: str) -> bool:
    tree = ast.parse(_source(rel))
    return any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name
               for n in tree.body)


def _md_artifact_rows() -> list[list[str]]:
    """Parse the §1 Artifacts table: header, then every pipe row until a non-table line."""
    lines = DOC.read_text(encoding="utf-8").splitlines()
    rows: list[list[str]] = []
    in_table = False
    for ln in lines:
        if ln.startswith("## 2."):
            break
        if ln.startswith("| artifact |") or (in_table and ln.startswith("|")):
            if set(ln.replace("|", "").strip()) <= {"-", " "} and in_table:
                continue  # separator row
            cells = [c.replace("`", "").strip() for c in ln.strip().strip("|").split("|")]
            if cells and cells[0] != "artifact":
                rows.append(cells)
            in_table = True
    return rows


def test_doc_exists_and_sections_pinned():
    text = DOC.read_text(encoding="utf-8")
    for heading in ("## 1. Artifacts", "## 2. Duplicate or competing owners",
                    "## 3. Correction/version census (R3A-92)",
                    "## 4. History provenance census (B11)", "## 5. Findings"):
        assert heading in text, f"missing section {heading!r}"
    assert "none_native" in text, "census vocabulary missing"
    assert "reconstructed_price_history" in text, "reconstruction label missing"


def test_writer_symbols_exist():
    for row in ROWS:
        rel = row["writer_file"]
        if row["writer_kind"] == "engine":
            mod_name = rel[:-3].replace("/", ".")
            mod = importlib.import_module(mod_name)
            assert hasattr(mod, row["writer_symbol"]), \
                f"{mod_name} has no {row['writer_symbol']} (artifact {row['artifact']})"
        else:
            assert _script_defines(rel, row["writer_symbol"]), \
                f"{rel} defines no function {row['writer_symbol']} (artifact {row['artifact']})"


def test_artifact_path_literals_in_writer_source():
    for row in ROWS:
        src = _source(row["writer_file"])
        for lit in row["path_literals"]:
            if lit.startswith("_"):
                assert lit in src, (  # composing constant (e.g. _SC_PAYLOAD_DIR)
                    f"constant {lit!r} not found in {row['writer_file']} "
                    f"(artifact {row['artifact']})")
            else:
                assert f'"{lit}"' in src or f"'{lit}'" in src, (
                    f"literal {lit!r} not found in {row['writer_file']} "
                    f"(artifact {row['artifact']})")


def test_markdown_artifacts_table_matches_rows():
    md_rows = _md_artifact_rows()
    assert len(md_rows) == len(ROWS), (
        f".md Artifacts table has {len(md_rows)} rows, pinned data has {len(ROWS)}")
    for md_cells, row in zip(md_rows, ROWS):
        assert len(md_cells) == 7, f"expected 7 columns, got {len(md_cells)}: {md_cells}"
        artifact, writer, _inputs, _consumer, fields, _fresh, disposition = md_cells
        assert artifact == row["artifact"], f"artifact mismatch: {artifact!r} vs {row['artifact']!r}"
        assert row["writer_file"] in writer and row["writer_symbol"] in writer, \
            f"writer cell {writer!r} lacks {row['writer_file']}:{row['writer_symbol']}"
        assert disposition.split()[0] == row["disposition"], \
            f"{row['artifact']}: disposition {disposition!r} vs {row['disposition']!r}"
        # session/generation column must name exact keys or say none
        assert fields.strip(), f"{row['artifact']}: empty session-fields column"


def test_none_native_rows_have_no_correction_dict_keys():
    """R3A-92: a none_native surface's writer must not carry a correction/revision/
    supersession dict key. Comments and prose do not count — only ast.Dict string keys."""
    scanned = 0
    for row in ROWS:
        if row["native"] != "none_native":
            continue
        src = _source(row["writer_file"])
        hits: list[str] = []
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Dict):
                for key in node.keys:
                    if (isinstance(key, ast.Constant) and isinstance(key.value, str)
                            and _CORRECTION_KEY.search(key.value)):
                        hits.append(f"{row['writer_file']}:{node.lineno}:{key.value}")
        assert not hits, (
            f"census row {row['artifact']} claims none_native but writer has "
            f"correction-ish dict keys: {hits}")
        scanned += 1
    assert scanned >= 20, "census shrank unexpectedly — every written artifact is none_native except narr"


def test_single_native_revision_channel_is_the_narratives_one():
    native_rows = [r for r in ROWS if r["native"] != "none_native"]
    assert len(native_rows) == 1 and native_rows[0]["artifact"] == "site/sector_cycles_narr_data.js"
    ttl_src = _source("scripts/_narrative_ttl.py")
    assert 'entry.get("prev_revision")' in ttl_src
    assert '"revision_note"' in ttl_src
    assert 'revision_note = f"revised {rev_date}' in ttl_src
    # the authored field starts null (migrate_narrative_ttl) — a real, declared channel
    assert '("prev_revision", None)' in _source("scripts/migrate_narrative_ttl.py")


def test_duplicate_owner_claims_are_cited_in_code():
    """The §2 claims the test can mechanically verify: the 48 h guard, the ts-or-asof
    key, the always-written payload rule, and the ungated forward-log append."""
    central = _source("engine/sector_central.py")
    assert 'raw.get("ts") or raw.get("asof")' in central          # two clocks, one guard
    assert "age_h > 48" in central                                 # the 48 h wall-clock rule
    builder = _source("scripts/build_sector_central.py")
    assert "ALWAYS written" in builder                             # premium payload rule
    fwd_log = _source("engine/cycle_forward_log.py")
    assert 'keep="first"' in fwd_log                               # append-only keep-first
    grader = _source("engine/sector_central_grader.py")
    assert "nightly_advance_enabled" in grader                     # the gated contrast


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))

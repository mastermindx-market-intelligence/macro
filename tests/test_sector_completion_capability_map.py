# -*- coding: utf-8 -*-
"""Sector Intelligence capability-map census checks (macro #7646).

`research/sector_completion_20261021/CAPABILITY_MATRIX_2026-10-21.csv` records, for
each of its 134 rows, an observed producer (`canonical_producer_artifact_to_record`)
and an observed Macro route (`actual_macro_route_control_to_record`) against the tree.
This suite re-parses the CSV and asserts that everything citable in those two columns
actually exists in the repository:

* every repo source path token (engine/ scripts/ templates/ tests/ config/ …) exists;
* every `file.py::symbol` / `file.js::function` citation resolves in that file's text;
* every `#anchor` named alongside a template appears in that template's text;
* every JSON artifact key cited as `site/…json[keys]` appears in the writer's source.

Artifacts under `site/` or `data/` split by git: a git-tracked file (a site page, a
committed projection) is asserted whenever the checkout materializes its top dir
(a sparse checkout reports its skip-worktree entries as skips); an untracked file is
a BUILD OUTPUT that exists only after the site build ran, so build outputs are
asserted only in a built checkout — one where at least one cited build output
exists — and every one is skipped (with the reason recorded) in an unbuilt tree
such as a ci-pack checkout. In a built tree a single missing artifact is therefore
a failure, never a skip. The writer's-source key check still runs either way.
Site-root URL fragments (``basket/…``, ``sectors/…``, bare ``stock.html`` …) are page
URLs, not repo paths, and are skipped by classification, never asserted.
"""
from __future__ import annotations

import csv
import io
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
CSV_PATH = REPO / "research" / "sector_completion_20261021" / "CAPABILITY_MATRIX_2026-10-21.csv"

PRODUCER_COL = "canonical_producer_artifact_to_record"
ROUTE_COL = "actual_macro_route_control_to_record"

#: top-level directories whose tokens are repo source paths and must exist
SOURCE_DIRS = {"engine", "scripts", "templates", "tests", "config", "research", "docs", "tools"}
#: site-root URL/artifact fragments — page URLs, never repo source paths
ARTIFACT_URL_DIRS = {
    "basketdata", "marketdata", "sectordata", "premiumdata", "oracledata",
    "factordata", "allocationdata", "themedata", "live", "public",
    "basket", "baskets", "sectors", "subsector", "subsector_nasdaq", "subsector_russell",
    "stock", "plans", "allocation",
}

#: only file-like tokens (extension at the end) are path citations; prose compounds
#: such as "up/down" or "MODEL/PASS" are not
TOKEN_RE = re.compile(
    r"[A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:py|js|j2|css|yml|json|html|csv|md|txt|parquet)")
SYMBOL_RE = re.compile(r"([A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:py|js|j2|css|yml))::([A-Za-z_][A-Za-z0-9_]*)")
ANCHOR_RE = re.compile(r"#([A-Za-z0-9_-]+)")
KEY_RE = re.compile(r"\bsite/[A-Za-z0-9_./-]+\.json\[([^\]]+)\]")


def _read_matrix() -> list[dict]:
    raw = CSV_PATH.read_bytes()
    assert raw[:3] == b"\xef\xbb\xbf", "UTF-8 BOM must stay on the capability matrix"
    with io.StringIO(raw.decode("utf-8-sig")) as fh:
        return list(csv.DictReader(fh))


MATRIX = _read_matrix()


def _path_tokens(cell: str) -> list[str]:
    return TOKEN_RE.findall(cell)


def _classify(token: str) -> str:
    """Return 'assert', 'skip-absent' (site|data artifact), or 'skip-url'."""
    if token.startswith(("site/", "data/")):
        return "skip-absent"
    if "/" not in token:
        # bare filename: a repo-root control file is assertable; anything else
        # (stock.html, lightweight-charts.js …) is a site-root page/asset URL
        return "assert" if token == "config.yml" else "skip-url"
    head = token.split("/", 1)[0]
    if head in SOURCE_DIRS:
        return "assert"
    if head in ARTIFACT_URL_DIRS:
        return "skip-url"
    return "assert"  # unknown slashed token: strict — catch typos


def _symbol_in_file(path: Path, name: str) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix == ".py":
        patterns = (f"def {name}(", f"class {name}", f"{name} =")
    else:
        patterns = (f"function {name}", f"const {name}", f"var {name}",
                    f"let {name}", f"macro {name}", f"name=\"{name}\"")
    return any(p in text for p in patterns)


def _template_files(cell: str) -> list[Path]:
    out = []
    for tok in _path_tokens(cell):
        p = REPO / tok
        if tok.startswith(("site/", "data/")):
            continue
        if p.exists() and p.suffix in (".j2", ".js", ".html", ".css"):
            out.append(p)
    return out


def _artifact_tokens() -> set[str]:
    """Every site//data token cited in the two observed columns."""
    return {
        tok
        for row in MATRIX
        for col in (PRODUCER_COL, ROUTE_COL)
        for tok in _path_tokens(row[col])
        if tok.startswith(("site/", "data/"))
    }


def _git_index(tokens: set[str]) -> tuple[set[str], set[str]]:
    """`git ls-files -t` over the cited tokens: (tracked, skip-worktree).

    H = tracked and checked out, S = tracked but skip-worktree (a sparse checkout).
    A tree without git (an exported tarball) reports nothing, so every token is then
    a build output and the built/unbuilt rule alone decides.
    """
    if not tokens:
        return set(), set()
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO), "ls-files", "-t", "--", *sorted(tokens)],
            capture_output=True, text=True, check=False,
        ).stdout
    except OSError:
        return set(), set()
    tracked: set[str] = set()
    skip_worktree: set[str] = set()
    for line in out.splitlines():
        tag, _, path = line.partition(" ")
        if not path:
            continue
        tracked.add(path)
        if tag == "S":
            skip_worktree.add(path)
    return tracked, skip_worktree


ARTIFACT_TOKENS = _artifact_tokens()
TRACKED_ARTIFACTS, SKIP_WORKTREE_ARTIFACTS = _git_index(ARTIFACT_TOKENS)
BUILD_OUTPUTS = ARTIFACT_TOKENS - TRACKED_ARTIFACTS
CHECKOUT_IS_BUILT = any((REPO / tok).exists() for tok in BUILD_OUTPUTS)


def _check_cell(cell: str, row_id: str, col: str) -> tuple[list[str], list[str]]:
    """Run all assertions for one cell. Returns (failure messages, skip reasons)."""
    fails: list[str] = []
    skips: list[str] = []
    if cell.startswith("NOT FOUND"):
        return fails, skips

    for tok in _path_tokens(cell):
        kind = _classify(tok)
        if kind == "assert":
            if not (REPO / tok).exists():
                fails.append(f"{row_id}/{col}: cited path does not exist: {tok}")
        elif kind == "skip-absent":
            top = tok.split("/", 1)[0]
            if tok in SKIP_WORKTREE_ARTIFACTS:
                skips.append(f"{row_id}/{col}: {tok} — tracked, skip-worktree in this sparse checkout")
            elif tok in TRACKED_ARTIFACTS:
                if (REPO / top).is_dir():
                    if not (REPO / tok).exists():
                        fails.append(f"{row_id}/{col}: tracked site/data file missing: {tok}")
                else:
                    skips.append(f"{row_id}/{col}: {tok} — {top}/ absent from this checkout")
            elif CHECKOUT_IS_BUILT:
                if not (REPO / tok).exists():
                    fails.append(f"{row_id}/{col}: built artifact missing: {tok}")
            else:
                skips.append(f"{row_id}/{col}: {tok} — build output; unbuilt checkout (no cited build output exists)")
        else:
            skips.append(f"{row_id}/{col}: {tok} — site-root page URL, not a repo path")

    for fpath, name in SYMBOL_RE.findall(cell):
        p = REPO / fpath
        if not p.exists():
            fails.append(f"{row_id}/{col}: symbol carrier missing: {fpath}")
        elif not _symbol_in_file(p, name):
            fails.append(f"{row_id}/{col}: {fpath} defines no {name!r}")

    templates = _template_files(cell)
    for anchor in ANCHOR_RE.findall(cell):
        if not templates:
            fails.append(f"{row_id}/{col}: anchor #{anchor} cited with no template file in cell")
        elif not any(anchor in t.read_text(encoding="utf-8", errors="replace") for t in templates):
            names = ", ".join(str(t) for t in templates)
            fails.append(f"{row_id}/{col}: anchor #{anchor} not found in any cited template ({names})")

    if col == PRODUCER_COL:
        py_sources = [REPO / t for t in _path_tokens(cell)
                      if t.endswith(".py") and not t.startswith(("site/", "data/")) and (REPO / t).exists()]
        for keys in KEY_RE.findall(cell):
            if not py_sources:
                fails.append(f"{row_id}/{col}: artifact keys {keys!r} cited with no writer .py in cell")
                continue
            for key in [k.strip() for k in keys.split(",") if k.strip()]:
                if not any(key in p.read_text(encoding="utf-8", errors="replace") for p in py_sources):
                    fails.append(f"{row_id}/{col}: artifact key {key!r} not written by any cited .py")
    return fails, skips


def test_matrix_shape_and_columns() -> None:
    assert len(MATRIX) == 134, f"expected 134 capability rows, found {len(MATRIX)}"
    ids = [r["row_id"] for r in MATRIX]
    assert ids[0] == "R3A-01" and ids[91] == "R3A-92"
    assert ids[92] == "C01" and ids[119] == "C28"
    assert ids[120] == "U01" and ids[133] == "U14"
    for row in MATRIX:
        for col in (PRODUCER_COL, ROUTE_COL):
            assert row[col].strip(), f"{row['row_id']}/{col}: cell must be filled or NOT FOUND"


@pytest.mark.parametrize(
    "row", MATRIX, ids=[r["row_id"] for r in MATRIX]
)
def test_cited_paths_symbols_and_anchors_exist(row: dict) -> None:
    fails: list[str] = []
    skips: list[str] = []
    for col in (PRODUCER_COL, ROUTE_COL):
        f, s = _check_cell(row[col], row["row_id"], col)
        fails += f
        skips += s
    assert not fails, "\n".join(fails)


def test_site_and_data_artifacts_report_skip_reasons(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The build-output skip path must engage exactly when the checkout is unbuilt.

    A ci-pack checkout is a full git tree with no site build (ci run 41443578532,
    job 125273606585 measured the old top-dir rule asserting 26 rows' build
    outputs against a `site/` that held only tracked files): there every cited
    build output is skipped with its reason. A built tree (the render runner, a
    local build) asserts every one, so a single missing artifact fails there.
    """
    all_skips: list[str] = []
    for row in MATRIX:
        for col in (PRODUCER_COL, ROUTE_COL):
            _, skips = _check_cell(row[col], row["row_id"], col)
            all_skips += skips
    assert BUILD_OUTPUTS, "the matrix cites no build output — nothing for this rule to guard"
    build_skips = [s for s in all_skips if "— build output;" in s]
    present = sorted(tok for tok in BUILD_OUTPUTS if (REPO / tok).exists())
    if CHECKOUT_IS_BUILT:
        assert not build_skips, (
            f"built checkout ({len(present)} cited build outputs present), "
            "so no build-output skip reasons expected"
        )
    else:
        assert len(build_skips) >= len(BUILD_OUTPUTS), (
            "unbuilt checkout but the cited build outputs were not all skipped — "
            "the skip rule is not engaging"
        )
        for reason in build_skips[:5]:
            print(f"SKIP: {reason}")
    print(
        f"{len(all_skips)} skipped tokens total; build outputs cited {len(BUILD_OUTPUTS)}, "
        f"present {len(present)}; tracked {len(TRACKED_ARTIFACTS)}, "
        f"skip-worktree {len(SKIP_WORKTREE_ARTIFACTS)}"
    )


def test_every_row_records_something_resolvable() -> None:
    """Beyond NOT FOUND rows, each row must cite at least one real path or symbol."""
    for row in MATRIX:
        for col in (PRODUCER_COL, ROUTE_COL):
            cell = row[col]
            if cell.startswith("NOT FOUND"):
                continue
            has_token = bool(_path_tokens(cell)) or bool(SYMBOL_RE.findall(cell))
            assert has_token, f"{row['row_id']}/{col}: no citable path or symbol in cell"


def test_not_found_rows_are_listed_in_the_map_document() -> None:
    md = (REPO / "research" / "sector_completion_20261021" / "CAPABILITY_MAP_2026-10-21.md").read_text(
        encoding="utf-8")
    nf = [r["row_id"] for r in MATRIX
          if r[PRODUCER_COL].startswith("NOT FOUND") or r[ROUTE_COL].startswith("NOT FOUND")]
    assert nf, "expected at least one NOT FOUND row in the current census"
    section = md.split("## Not found", 1)[1].split("## Observed divergences", 1)[0]
    for row_id in nf:
        assert row_id in section, f"{row_id} recorded NOT FOUND but not listed in the map's Not found section"

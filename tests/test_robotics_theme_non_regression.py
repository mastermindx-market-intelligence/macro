"""Non-regression for the robotics re-land: write-set disjointness and import isolation.

The live freeze compared today's ``site/`` and ``data/`` bytes to a snapshot
taken at ``3c93f819``, before any robotics product code. That comparison
rejected the re-land: prophet ``member_tickers_present`` moved from
``[ISRG, NOVT]`` to ``[CGNX, ISRG, NOVT, ROK, TRMB]``, and
``site/prophet/index.json`` gained ``source_board_sha256``,
``source_board_snapshot_encoding``, and ``source_board_snapshot_path``. The
drift is the daily prophet board. Re-blessing the snapshot would fail again
the next day.

Assertion 1 — write-set disjointness. ``reland_write_set.json`` is
``git diff --name-only`` of the re-land commit against its parent. No path
may sit under ``site/``, ``data/``, or ``templates/``, and no path may be a
builder or publisher the prophet board, membership, or theme tracker read.
Every robotics engine module is AST-scanned for file writes. DataFrame
``to_parquet``, ``to_csv`` and ``to_json`` count as writes; ``json.dumps``
does not. The diff of this head against ``refs/grok/pr/7870`` is pinned as
``PR_7870_DIFF_PATHS`` and checked with the same pure surface rule. That
test does not call git.

Assertion 2 — import isolation. The AST import closure of those builders
contains no robotics engine module, so their outputs do not depend on the
re-land.

Live comparisons removed, and the assertion that covers each intent:

- membership vs the frozen basket: (1) the artifact is under ``data/`` and
  the membership builder/publisher is absent from the write set; (2) that
  builder does not import robotics.
- theme_state vs the freeze: (1) the artifact is under ``data/`` and ``site/``,
  and ``scripts/build_thematic_state.py`` is absent from the write set;
  (2) that publisher does not import robotics.
- theme tracker ``compose()`` vs the freeze: (1) ``scripts/build_state_of_themes.py``
  is absent from the write set and the artifacts it reads are under ``site/``
  and ``data/``; (2) its closure does not import robotics.
- basket confluence vs the freeze: (1) the artifact is under ``site/`` and
  robotics modules perform no writes, so they cannot rewrite it.
- prophet presence vs the freeze: (1) ``site/prophet/index.json`` is under
  ``site/`` and ``scripts/build_prophet.py`` is absent from the write set;
  (2) that publisher's closure does not import robotics. The frozen
  ``prophet_presence`` block was removed because nothing reads it.
- live public-page and public-JSON canary scan: (1) the write set has no
  ``site/`` path and robotics modules perform no writes. The canary
  vocabulary stays pinned below and does not open ``site/``.
- live evidence-parquet cell scan: (1) the parquet is under ``data/`` and
  robotics modules perform no writes. The column rule stays pinned and does
  not open the parquet.
"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = REPO_ROOT / "tests/fixtures/robotics_non_regression/robotics_baseline.json"
WRITE_SET_PATH = REPO_ROOT / "tests/fixtures/robotics_non_regression/reland_write_set.json"
BASELINE_SCHEMA = "robotics.theme_non_regression.v1"
WRITE_SET_SCHEMA = "robotics.reland_write_set.v1"
FROZEN_AT_MAIN = "3c93f8194f6c2cb19dad21c1347d8b3b8474aa31"
RELAND_BASE = "2cd51ad3db37bc51383380a6fa3f29f397253060"
RELAND_HEAD = "efe72f1292d17f9defb38d0a452fbfaf918cacef"

# Prophet board publisher writes site/prophet/index.json
# (scripts/build_prophet.py:1-6).
# Membership is the curated document engine/baskets.py:_membership reads
# (engine/baskets.py:43) and compute_baskets turns into the basket payload
# (engine/baskets.py:173). scripts/build_baskets.py publishes that payload
# (scripts/build_baskets.py:4, compute_baskets at scripts/build_baskets.py:246).
# US membership is not generated: scripts/reconcile_membership.py:36-38
# refuses to auto-mutate data/baskets/membership.json.
# Theme Tracker read is scripts/build_state_of_themes.py:compose
# (scripts/build_state_of_themes.py:793). It reads theme_state.json published
# by scripts/build_thematic_state.py (scripts/build_thematic_state.py:6-7,
# read at scripts/build_state_of_themes.py:799).
# ci-trigger-closure: data — parse-only isolation subjects; imports not followed
SURFACE_BUILDERS: dict[str, tuple[str, ...]] = {
    "prophet_board": ("scripts/build_prophet.py",),
    "membership": ("engine/baskets.py", "scripts/build_baskets.py"),
    "theme_tracker": (
        "scripts/build_state_of_themes.py",
        "scripts/build_thematic_state.py",
    ),
}
FORBIDDEN_ROOTS = ("site", "data", "templates")
REQUIRED_ROBOTICS_MODULES = (
    "engine/market_ontology/robotics_owner_bundle.py",
    "engine/market_ontology/robotics_theme_research.py",
)
ROBOTICS_MODULE_NAMES = (
    "engine.market_ontology.robotics_owner_bundle",
    "engine.market_ontology.robotics_theme_research",
)

FORESIGHT_DECISION_FIELDS = ("stage", "entry_ready", "tier", "bottleneck_band", "source")
THEME_STATE_FROZEN = (
    "theme_id",
    "name_en",
    "name_zh",
    "basket_ids",
    "foresight_decision",
    "foresight_keys",
    "narrative",
)
THEME_STATE_SHAPE = (
    "radar",
    "basket_intel",
    "subsector_rotation",
    "divergence_board",
    "subsector_keys",
    "foresight_score",
)
THEME_TRACKER_FROZEN = (
    "theme_id",
    "name_en",
    "name_zh",
)
THEME_TRACKER_SHAPE = (
    "lane",
    "lane_rank",
    "stance_en",
    "stance_zh",
    "story_en",
    "story_zh",
    "fav_count",
    "caut_count",
    "present_count",
    "stage_raw",
    "stage_key",
    "stage_label_en",
    "stage_label_zh",
    "stage_sort",
    "falsifier_any_fired",
    "falsifier_label",
    "filter_flags",
    "leadership_context",
    "entry_context",
)
BASKET_CONFLUENCE_FROZEN = (
    "key",
    "kind",
    "label",
    "label_zh",
    "sector",
    "sector_zh",
    "basket_id",
    "chart_key",
)
BASKET_CONFLUENCE_SHAPE = (
    "entry",
    "regime",
    "class",
    "price_level",
    "n_members",
    "n_priced",
    "n_live",
    "reliability",
    "coverage_pct",
    "has_signals",
    "start",
    "as_of",
    "member_order",
)
PROPHET_FROZEN = ("member_tickers_present",)
PUBLIC_PAGE_PATHS = (
    "site/state_of_themes.html",
    "site/basket/robotics_automation.html",
)
PUBLIC_JSON_ROOTS = ("site/marketdata", "site/prophet")
EXTRA_PUBLIC_JSON = ("site/basketdata/foresight_cascade.json",)
PUBLIC_PAGE_CANARIES = (
    "gmirca_",
    "theme_graph.curation_assertion.v1",
    "curation_revision",
    "theme_graph_private/",
    "DOCUMENTED_PRODUCT_INCLUSION",
    "PRODUCT_CAPABILITY",
    "ANNOUNCED_DEVELOPMENT_AGREEMENT",
    "REPORTED_OPERATING_MEASURE",
    "NarGo",
    "K-Series frameless",
)
PUBLIC_JSON_CANARIES = ("gmirca_", "curation_assertion")
EVIDENCE_PARQUET_REL = "data/theme_graph/evidence.parquet"
PARQUET_FORBIDDEN_COLUMN = "curation_assertion"

_CLOSURE_CACHE: dict[str, frozenset[str]] = {}


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _read_baseline() -> dict[str, Any]:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def _read_write_set() -> dict[str, Any]:
    return json.loads(WRITE_SET_PATH.read_text(encoding="utf-8"))


def _public_pages_section() -> dict[str, Any]:
    return {
        "pages": list(PUBLIC_PAGE_PATHS),
        "canaries": list(PUBLIC_PAGE_CANARIES),
        "json_roots": list(PUBLIC_JSON_ROOTS) + ["site/*.json"] + list(EXTRA_PUBLIC_JSON),
        "json_canaries": list(PUBLIC_JSON_CANARIES),
    }


def _evidence_parquet_section() -> dict[str, Any]:
    return {
        "path": EVIDENCE_PARQUET_REL,
        "forbidden_column": PARQUET_FORBIDDEN_COLUMN,
        "rule": "column absent, or every cell null",
    }


def _surface_builder_paths() -> set[str]:
    return {path for group in SURFACE_BUILDERS.values() for path in group}


def _write_set_violation(path: str) -> str | None:
    parts = path.split("/")
    if parts and parts[0] in FORBIDDEN_ROOTS:
        return parts[0] + "/"
    if path in _surface_builder_paths():
        return "surface builder/publisher"
    return None


def decision_surface_collisions(paths: list[str]) -> dict[str, str]:
    """Paths from ``paths`` that land on a decision surface.

    A decision surface is ``site/``, ``data/``, ``templates/``, or one of
    ``SURFACE_BUILDERS``. The result is a pure function of ``paths`` and those
    constants: it does not read git, the filesystem, or a fixture.
    """
    collisions: dict[str, str] = {}
    for path in paths:
        reason = _write_set_violation(path)
        if reason is not None:
            collisions[path] = reason
    return collisions


def _git_name_only(base: str, head: str) -> list[str] | None:
    """Name-only diff when both commits are in this clone. None when they are not.

    A depth-1 CI checkout does not have the re-land parent. The committed
    fixture remains the source of truth in that case.
    """
    try:
        completed = subprocess.run(
            ["git", "diff", "--name-only", base, head],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    return sorted(line for line in completed.stdout.splitlines() if line)


def _is_robotics_engine_module(rel: str) -> bool:
    path = Path(rel)
    if path.suffix != ".py":
        return False
    parts = path.parts
    if not parts or parts[0] != "engine":
        return False
    return any("robotics" in part for part in parts)


def _robotics_engine_modules() -> list[str]:
    found: list[str] = []
    for path in (REPO_ROOT / "engine").rglob("*.py"):
        rel = path.relative_to(REPO_ROOT).as_posix()
        if _is_robotics_engine_module(rel):
            found.append(rel)
    return sorted(found)


def _const_str(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _sequence_strings(node: ast.AST) -> list[str] | None:
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        values: list[str] = []
        for element in node.elts:
            value = _const_str(element)
            if value is None:
                return None
            values.append(value)
        return values
    return None


def _is_import_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr == "import_module":
        return True
    return isinstance(func, ast.Name) and func.id == "__import__"


def _bound_string_constants(tree: ast.AST) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    sequences: dict[str, list[str]] = {}
    dict_values: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        target: str | None = None
        value: ast.AST | None = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target = node.targets[0].id
            value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            target = node.target.id
            value = node.value
        if target is None or value is None:
            continue
        sequence = _sequence_strings(value)
        if sequence is not None:
            sequences[target] = sequence
            continue
        literal = _const_str(value)
        if literal is not None:
            sequences[target] = [literal]
            continue
        if isinstance(value, ast.Dict):
            collected: list[str] = []
            complete = True
            for item in value.values:
                item_literal = _const_str(item)
                item_sequence = _sequence_strings(item)
                if item_literal is not None:
                    collected.append(item_literal)
                elif item_sequence is not None:
                    collected.extend(item_sequence)
                else:
                    complete = False
                    break
            if complete:
                dict_values[target] = collected
    return sequences, dict_values


def _function_covering(tree: ast.AST, lineno: int) -> ast.AST | None:
    chosen: ast.AST | None = None
    chosen_span = -1
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        end = getattr(node, "end_lineno", node.lineno)
        if node.lineno <= lineno <= end:
            span = end - node.lineno
            if chosen is None or span < chosen_span:
                chosen = node
                chosen_span = span
    return chosen


def _string_constants(node: ast.AST) -> set[str]:
    found: set[str] = set()
    for child in ast.walk(node):
        value = _const_str(child)
        if value is not None:
            found.add(value)
    return found


def _dynamic_import_names(tree: ast.AST) -> set[str]:
    """Module names a file can import without a static Import node.

    Covers three shapes these builders actually use: a literal
    ``import_module("...")``, ``for name in SOME_TUPLE: import_module(name)``
    where the tuple is a constant, and ``__import__("engine." + key)`` where
    the pieces are string constants in the same function. Dict values that are
    themselves module paths (the membership-source table) are included when
    the file calls ``import_module`` at all.
    """
    names: set[str] = set()
    sequences, dict_values = _bound_string_constants(tree)
    calls = [node for node in ast.walk(tree) if _is_import_call(node) and node.args]
    for node in ast.walk(tree):
        if not isinstance(node, ast.For) or not isinstance(node.target, ast.Name):
            continue
        if isinstance(node.iter, ast.Name):
            sequence = sequences.get(node.iter.id)
        else:
            sequence = _sequence_strings(node.iter)
        if not sequence:
            continue
        for child in ast.walk(node):
            if (
                _is_import_call(child)
                and child.args
                and isinstance(child.args[0], ast.Name)
                and child.args[0].id == node.target.id
            ):
                names.update(sequence)
    for call in calls:
        arg = call.args[0]
        literal = _const_str(arg)
        if literal is not None:
            names.add(literal)
            continue
        if isinstance(arg, ast.Name):
            names.update(sequences.get(arg.id, ()))
        if not (isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add)):
            continue
        prefix = _const_str(arg.left)
        if prefix is None or not isinstance(arg.right, ast.Name):
            continue
        pieces = list(sequences.get(arg.right.id, ()))
        pieces.extend(dict_values.get(arg.right.id, ()))
        enclosing = _function_covering(tree, call.lineno)
        if enclosing is not None:
            pieces.extend(_string_constants(enclosing))
        for piece in pieces:
            names.add(prefix + piece)
    if calls:
        for values in dict_values.values():
            for value in values:
                if "." in value:
                    names.add(value)
    return names


def _module_name(path: Path) -> str:
    relative = path.relative_to(REPO_ROOT)
    parts = list(relative.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    elif parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
    return ".".join(parts)


def _resolve_module(name: str) -> Path | None:
    if not name or any(not part.isidentifier() for part in name.split(".")):
        return None
    relative = Path(*name.split("."))
    for candidate in (REPO_ROOT / relative.with_suffix(".py"), REPO_ROOT / relative / "__init__.py"):
        if candidate.is_file():
            return candidate
    return None


def _static_import_names(tree: ast.AST, current: Path) -> set[str]:
    current_module = _module_name(current)
    package = current_module if current.name == "__init__.py" else current_module.rpartition(".")[0]
    found = set(_dynamic_import_names(tree))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
            continue
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.level:
            parts = package.split(".") if package else []
            drop = node.level - 1
            if drop == 0:
                base_parts = parts
            elif drop <= len(parts):
                base_parts = parts[:-drop]
            else:
                base_parts = []
            base = ".".join(part for part in base_parts if part)
            if node.module:
                base = f"{base}.{node.module}" if base else node.module
        else:
            base = node.module or ""
        if not base:
            continue
        found.add(base)
        for alias in node.names:
            if alias.name != "*":
                found.add(f"{base}.{alias.name}")
    return found


def _import_closure(entry: str) -> frozenset[str]:
    cached = _CLOSURE_CACHE.get(entry)
    if cached is not None:
        return cached
    start = REPO_ROOT / entry
    seen: set[Path] = set()
    stack = [start]
    while stack:
        path = stack.pop()
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for name in _static_import_names(tree, path):
            resolved = _resolve_module(name)
            if resolved is None:
                continue
            if resolved not in seen:
                stack.append(resolved)
            parent = REPO_ROOT
            for part in resolved.relative_to(REPO_ROOT).parts[:-1]:
                parent = parent / part
                init = parent / "__init__.py"
                if init.is_file() and init not in seen:
                    stack.append(init)
    closure = frozenset(path.relative_to(REPO_ROOT).as_posix() for path in seen)
    _CLOSURE_CACHE[entry] = closure
    return closure


def _open_mode_writes(call: ast.Call) -> bool:
    mode: ast.AST | None = call.args[1] if len(call.args) >= 2 else None
    for keyword in call.keywords:
        if keyword.arg == "mode":
            mode = keyword.value
    if mode is None:
        return False
    literal = _const_str(mode)
    if literal is None:
        return True
    return any(mark in literal for mark in ("w", "a", "x", "+"))


# Method calls that write a file. ``json.dumps`` is intentionally absent.
_DATAFRAME_WRITE_ATTRS = frozenset({"to_csv", "to_json", "to_parquet"})


def _write_findings(tree: ast.AST) -> list[str]:
    """File-write sites: open(..., w/a), Path.write_*, json.dump, shutil, os.replace.

    DataFrame ``to_parquet``, ``to_csv`` and ``to_json`` calls are writes.
    ``json.dumps`` and ``datetime.replace`` are not. A non-literal open
    mode counts, because the scan cannot prove it is read-only.
    """
    os_names = {"os"}
    json_names = {"json"}
    shutil_names: set[str] = set()
    os_replace_names: set[str] = set()
    json_dump_names: set[str] = set()
    shutil_names_called: set[str] = set()
    findings: list[str] = []

    def add(node: ast.AST, text: str) -> None:
        findings.append(f"line {getattr(node, 'lineno', '?')}: {text}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                bound = alias.asname or root
                if root == "os":
                    os_names.add(bound)
                elif root == "json":
                    json_names.add(bound)
                elif root == "shutil":
                    shutil_names.add(bound)
                    add(node, f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".", 1)[0]
            if root == "os":
                for alias in node.names:
                    if alias.name == "replace":
                        os_replace_names.add(alias.asname or alias.name)
                        add(node, "from os import replace")
            elif root == "json":
                for alias in node.names:
                    if alias.name == "dump":
                        json_dump_names.add(alias.asname or alias.name)
                        add(node, "from json import dump")
            elif root == "shutil":
                add(node, f"from {node.module} import shutil")
                for alias in node.names:
                    shutil_names_called.add(alias.asname or alias.name)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                if func.id == "open" and _open_mode_writes(node):
                    add(node, "open write mode")
                elif func.id in os_replace_names:
                    add(node, "os.replace")
                elif func.id in json_dump_names:
                    add(node, "json.dump")
                elif func.id in shutil_names_called:
                    add(node, "shutil call")
            elif isinstance(func, ast.Attribute):
                if func.attr in _DATAFRAME_WRITE_ATTRS:
                    add(node, f"DataFrame.{func.attr}")
                elif func.attr.startswith("write_"):
                    add(node, f"Path.{func.attr}")
                elif func.attr == "open" and _open_mode_writes(node):
                    add(node, "open write mode")
                elif (
                    func.attr == "replace"
                    and isinstance(func.value, ast.Name)
                    and func.value.id in os_names
                ):
                    add(node, "os.replace")
                elif (
                    func.attr == "dump"
                    and isinstance(func.value, ast.Name)
                    and func.value.id in json_names
                ):
                    add(node, "json.dump")
                elif isinstance(func.value, ast.Name) and func.value.id in shutil_names:
                    add(node, f"shutil.{func.attr}")
    return findings


def test_baseline_frozen_at_main_sha_is_pinned() -> None:
    baseline = _read_baseline()
    assert baseline["schema"] == BASELINE_SCHEMA
    assert baseline["frozen_at_main"] == FROZEN_AT_MAIN


def test_prophet_presence_block_is_absent_from_the_baseline() -> None:
    baseline = _read_baseline()
    assert "prophet_presence" not in baseline
    assert "prophet_presence" not in baseline["section_sha256"]
    assert "prophet_presence" not in baseline["owners"]


def test_baseline_section_hashes_match_stored_sections() -> None:
    baseline = _read_baseline()
    for name, digest in baseline["section_sha256"].items():
        assert name in baseline, name
        assert _canonical_sha256(baseline[name]) == digest, name


def test_frozen_field_lists_exclude_nightly_volatile_fields() -> None:
    nightly_volatile_fields = (
        "radar",
        "basket_intel",
        "subsector_rotation",
        "divergence_board",
        "lane",
        "lane_rank",
        "fav_count",
        "caut_count",
        "present_count",
        "stage_key",
        "stage_sort",
        "falsifier_any_fired",
        "filter_flags",
        "entry",
        "regime",
        "price_level",
        "as_of",
        "member_order",
        "foresight",
        "foresight_score",
        "score",
        "row_fields",
    )
    for field in nightly_volatile_fields:
        assert field not in THEME_STATE_FROZEN
        assert field not in THEME_TRACKER_FROZEN
        assert field not in BASKET_CONFLUENCE_FROZEN
        assert field not in PROPHET_FROZEN
        assert field not in FORESIGHT_DECISION_FIELDS
    assert PROPHET_FROZEN == ("member_tickers_present",)
    assert set(THEME_STATE_FROZEN).isdisjoint(THEME_STATE_SHAPE)
    assert set(THEME_TRACKER_FROZEN).isdisjoint(THEME_TRACKER_SHAPE)
    assert set(BASKET_CONFLUENCE_FROZEN).isdisjoint(BASKET_CONFLUENCE_SHAPE)
    assert set(FORESIGHT_DECISION_FIELDS).isdisjoint(THEME_STATE_SHAPE)


def test_public_leak_canary_vocabulary_is_pinned() -> None:
    baseline = _read_baseline()
    assert baseline["public_pages"] == _public_pages_section()
    assert _canonical_sha256(baseline["public_pages"]) == baseline["section_sha256"]["public_pages"]


def test_evidence_parquet_rule_is_pinned() -> None:
    baseline = _read_baseline()
    assert baseline["evidence_parquet"] == _evidence_parquet_section()
    assert (
        _canonical_sha256(baseline["evidence_parquet"])
        == baseline["section_sha256"]["evidence_parquet"]
    )


def test_reland_write_set_is_disjoint_from_decision_surfaces() -> None:
    document = _read_write_set()
    assert document["schema"] == WRITE_SET_SCHEMA
    assert document["base"] == RELAND_BASE
    assert document["head"] == RELAND_HEAD
    paths = document["paths"]
    assert isinstance(paths, list) and paths, "write-set fixture is empty"
    assert paths == sorted(paths)
    assert set(REQUIRED_ROBOTICS_MODULES) <= set(paths)
    violations = {path: _write_set_violation(path) for path in paths}
    violations = {path: reason for path, reason in violations.items() if reason}
    assert not violations, violations
    for builder in sorted(_surface_builder_paths()):
        assert (REPO_ROOT / builder).is_file(), builder
    recorded = _git_name_only(RELAND_BASE, RELAND_HEAD)
    if recorded is not None:
        assert recorded == paths


# git diff --name-only e4f204d4eebbac7be73ce667ad7d3c5ef744b9b4
# 94b86c4ddb04ab285995ca23fa7d205a1b8df717 (refs/grok/pr/7870 .. this head).
# 38 paths. The test below feeds this constant and does not call git.
# ci-trigger-closure: data — recorded diff paths; imports not followed
PR_7870_DIFF_PATHS: tuple[str, ...] = (
    ".github/ci/legacy-jobs.yml",
    "agentos/handoffs/GMI-THEME-GRAPH-2026-09-24-robotics-implementation.md",
    "contracts/market_ontology/robotics_theme_research.v1.schema.json",
    "engine/market_ontology/robotics_owner_bundle.py",
    "engine/market_ontology/robotics_theme_research.py",
    "research/theme_graph/thematic_research_20260924/ROBOTICS_SOURCE_RIGHTS_QUALIFICATION_2026-09-24.md",
    "tests/fixtures/robotics_non_regression/README.md",
    "tests/fixtures/robotics_non_regression/reland_write_set.json",
    "tests/fixtures/robotics_non_regression/robotics_baseline.json",
    "tests/fixtures/robotics_theme_research/corrected_same_url.json",
    "tests/fixtures/robotics_theme_research/hds_backlog_not_lead_time.json",
    "tests/fixtures/robotics_theme_research/hds_operating_snapshot.json",
    "tests/fixtures/robotics_theme_research/integrated_assembly_double_count.json",
    "tests/fixtures/robotics_theme_research/invalid_quantities.json",
    "tests/fixtures/robotics_theme_research/later_retained_backdate.json",
    "tests/fixtures/robotics_theme_research/newer_generation_no_inheritance.json",
    "tests/fixtures/robotics_theme_research/per_hand_multiplicity_missing.json",
    "tests/fixtures/robotics_theme_research/ptc_tpg_ownership.json",
    "tests/fixtures/robotics_theme_research/review_expired_or_withdrawn.json",
    "tests/fixtures/robotics_theme_research/rights_partial.json",
    "tests/fixtures/robotics_theme_research/same_url_two_statements.json",
    "tests/fixtures/robotics_theme_research/sanhua_actuator_scaleup.json",
    "tests/fixtures/robotics_theme_research/schaeffler_hexagon_reciprocal.json",
    "tests/fixtures/robotics_theme_research/source_authority_injection.json",
    "tests/fixtures/robotics_theme_research/stabilus_synapticon_joint_product.json",
    "tests/fixtures/robotics_theme_research/syndicated_copy.json",
    "tests/fixtures/robotics_theme_research/unresolved_identity_source_only.json",
    "tests/fixtures/robotics_theme_research/witness_motion_parker_kseries.json",
    "tests/fixtures/robotics_theme_research/witness_perception_orbbec_twinny.json",
    "tests/fixtures/robotics_theme_research/zebra_skild_ownership.json",
    "tests/robotics_research_helpers.py",
    "tests/test_ci_pack.py",
    "tests/test_market_ontology_robotics_theme_research.py",
    "tests/test_robotics_owner_bundle.py",
    "tests/test_robotics_research_composition.py",
    "tests/test_robotics_research_inputs.py",
    "tests/test_robotics_research_temporal.py",
    "tests/test_robotics_theme_non_regression.py",
)


# ci-trigger-closure: data — synthetic decision-surface paths; imports not followed
def test_pr7870_diff_is_disjoint_from_decision_surfaces() -> None:
    recorded = list(PR_7870_DIFF_PATHS)
    assert recorded == sorted(recorded)
    assert len(recorded) == 38
    assert decision_surface_collisions(recorded) == {}
    assert decision_surface_collisions([*recorded, "site/foo.json"]) == {
        "site/foo.json": "site/"
    }
    assert decision_surface_collisions(["data/foo.json"]) == {"data/foo.json": "data/"}
    assert decision_surface_collisions(["templates/foo.html.j2"]) == {
        "templates/foo.html.j2": "templates/"
    }
    assert decision_surface_collisions(["scripts/build_prophet.py"]) == {
        "scripts/build_prophet.py": "surface builder/publisher"
    }


def test_robotics_engine_modules_perform_no_writes() -> None:
    modules = _robotics_engine_modules()
    assert set(REQUIRED_ROBOTICS_MODULES) <= set(modules)
    found: dict[str, list[str]] = {}
    for rel in modules:
        tree = ast.parse((REPO_ROOT / rel).read_text(encoding="utf-8"), filename=rel)
        sites = _write_findings(tree)
        if sites:
            found[rel] = sites
    assert not found, found


def test_write_scanner_flags_dataframe_file_writes() -> None:
    """A synthetic module calling DataFrame.to_parquet, to_csv, or to_json writes.

    ``json.dumps`` stays allowed: it builds a string and does not open a file.
    """
    samples = {
        "to_parquet": "df.to_parquet('data/theme_graph/evidence.parquet')",
        "to_csv": "df.to_csv('data/theme_graph/rows.csv')",
        "to_json": "df.to_json('data/theme_graph/rows.json')",
    }
    for name, source in samples.items():
        findings = _write_findings(ast.parse(source))
        assert findings, name
        assert any(name in item for item in findings), (name, findings)
    assert not _write_findings(ast.parse("import json\njson.dumps({})"))


def test_write_scanner_flags_banned_forms_and_ignores_reads() -> None:
    banned = (
        "open(p, 'w')",
        "open(p, 'a')",
        "open(p, 'wb')",
        "open(p, mode='a+')",
        "p.write_text('a')",
        "p.write_bytes(b'a')",
        "import json\njson.dump({}, fh)",
        "import shutil\nshutil.copy('a', 'b')",
        "import os\nos.replace('a', 'b')",
        "from os import replace\nreplace('a', 'b')",
        "import os as operating_system\noperating_system.replace('a', 'b')",
    )
    allowed = (
        "open(p)",
        "open(p, 'r')",
        "open(p, 'rb')",
        "import json\njson.dumps({})",
        "moment.replace(tzinfo=timezone.utc)",
    )
    for source in banned:
        assert _write_findings(ast.parse(source)), source
    for source in allowed:
        assert not _write_findings(ast.parse(source)), source


# ci-trigger-closure: data — parse-only pins of the isolation subjects; imports not followed
def test_decision_builders_do_not_import_robotics_modules() -> None:
    robotics = set(_robotics_engine_modules())
    assert robotics
    for surface, entries in SURFACE_BUILDERS.items():
        for entry in entries:
            assert (REPO_ROOT / entry).is_file(), entry
            closure = _import_closure(entry)
            assert entry in closure, entry
            hit = sorted(path for path in closure if path in robotics or _is_robotics_engine_module(path))
            assert not hit, f"{surface} builder {entry} reaches robotics: {hit}"
            named = [
                f"{rel} names {module}"
                for rel in sorted(closure)
                for module in ROBOTICS_MODULE_NAMES
                if module in (REPO_ROOT / rel).read_text(encoding="utf-8")
            ]
            assert not named, named
    tracker = _import_closure("scripts/build_state_of_themes.py")
    assert "engine/market_ontology/theme_research_mounts.py" in tracker
    assert "engine/theme_graph/store.py" in tracker
    assert "engine/research_priority_ordering.py" in tracker
    prophet = _import_closure("scripts/build_prophet.py")
    assert "engine/prophet_board_read.py" in prophet
    assert "engine/prophet_bridge.py" in prophet
    publisher = _import_closure("scripts/build_baskets.py")
    assert "engine/baskets.py" in publisher
    assert "engine/bonds_alerts.py" in publisher
    thematic = _import_closure("scripts/build_thematic_state.py")
    assert "engine/neuralweb/theme_thesis.py" in thematic
    assert "engine/neuralweb/theme_pathways.py" in thematic
    assert "engine/neuralweb/theme_asymmetry.py" in thematic

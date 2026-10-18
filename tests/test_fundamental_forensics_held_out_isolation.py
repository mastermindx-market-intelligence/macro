"""Held-out isolation for FIF pack evaluation (A37).

Walks the live engine/app/lib/scripts trees. Does not import engine or app.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELD_OUT_REL = "tests/fixtures/fundamental_forensics_held_out"
HELD_OUT_ROOT = ROOT / "tests" / "fixtures" / "fundamental_forensics_held_out"
CALIBRATION_PREFIX = "tests/fixtures/fundamental_forensics/"
MISTAKEN_NEST = "fixtures/fundamental_forensics/held_out"
TEXT_SUFFIXES = {".py", ".js", ".json", ".yml"}
STATEMENT_GRAPH = ROOT / "engine" / "fundamental_forensics" / "statement_graph.py"
ENGINE_FF = ROOT / "engine" / "fundamental_forensics"

ALLOWED_TEST_NAMES = {
    "test_fundamental_forensics_held_out_isolation.py",
    "test_fundamental_forensics_q0_quality_protocol.py",
}

_GUARDED_TOKEN = "validat" + "ed"
_SCRIPT_FILENAME = "check_" + _GUARDED_TOKEN + "_claims.py"


def _ast_assign(tree: ast.AST, name: str):
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == name and node.value is not None:
                return ast.literal_eval(node.value)
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError(f"{name} not found")


def _iter_production_text_files():
    for folder in ("engine", "app", "lib"):
        base = ROOT / folder
        assert base.is_dir(), f"isolation walk requires live {folder}/"
        for path in base.rglob("*"):
            if path.is_file() and path.suffix in TEXT_SUFFIXES:
                yield path
    scripts = ROOT / "scripts"
    assert scripts.is_dir(), "isolation walk requires live scripts/"
    yield from sorted(scripts.glob("build_*.py"))
    yield from sorted(scripts.glob("render_*.py"))


def _q1_held_out_test(name: str) -> bool:
    return name.startswith("test_fundamental_forensics_q1_held_out_") and name.endswith(".py")


def test_held_out_root_path_is_exact_and_exists() -> None:
    assert HELD_OUT_REL == "tests/fixtures/fundamental_forensics_held_out"
    assert HELD_OUT_ROOT.is_dir()
    assert (HELD_OUT_ROOT / "README.md").is_file()
    rel = HELD_OUT_ROOT.relative_to(ROOT).as_posix()
    assert rel == HELD_OUT_REL


def test_production_surfaces_do_not_name_held_out() -> None:
    paths = list(_iter_production_text_files())
    assert len(paths) > 100, f"stub walk: only {len(paths)} files"
    hits = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        if HELD_OUT_REL in text or MISTAKEN_NEST in text:
            hits.append(path.relative_to(ROOT).as_posix())
    assert hits == [], f"production surfaces name held-out: {hits[:20]}"


def test_golden_aapl_fixtures_stay_under_calibration() -> None:
    tree = ast.parse(STATEMENT_GRAPH.read_text(encoding="utf-8"))
    fixtures = _ast_assign(tree, "GOLDEN_AAPL_FIXTURES")
    assert isinstance(fixtures, dict) and fixtures
    for accession, rel in fixtures.items():
        assert isinstance(rel, str)
        assert rel.startswith(CALIBRATION_PREFIX), f"{accession} -> {rel}"
        assert HELD_OUT_REL not in rel
        assert MISTAKEN_NEST not in rel
        assert not rel.startswith(HELD_OUT_REL)


def test_engine_fundamental_forensics_imports_do_not_name_held_out() -> None:
    py_files = sorted(ENGINE_FF.glob("*.py"))
    assert py_files, "engine/fundamental_forensics/*.py missing"
    offenders = []
    for path in py_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.append(alias.name)
                    if alias.asname:
                        names.append(alias.asname)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    names.append(node.module)
                for alias in node.names:
                    names.append(alias.name)
                    if alias.asname:
                        names.append(alias.asname)
            for name in names:
                if "held_out" in name:
                    offenders.append(f"{path.name}:{name}")
    assert offenders == []


def test_only_allowed_test_modules_contain_held_out_root_string() -> None:
    tests_root = ROOT / "tests"
    offenders = []
    for path in tests_root.rglob("*.py"):
        if path.name in ALLOWED_TEST_NAMES or _q1_held_out_test(path.name):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if HELD_OUT_REL in text or MISTAKEN_NEST in text:
            offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == []


def test_held_out_labels_json_require_sealed_marker() -> None:
    for json_path in HELD_OUT_ROOT.rglob("*.json"):
        if json_path.parent.name != "labels":
            continue
        sealed = json_path.parent / "_SEALED"
        assert sealed.is_file(), f"{json_path} sits in labels/ without _SEALED"
    for labels_dir in HELD_OUT_ROOT.rglob("labels"):
        if not labels_dir.is_dir():
            continue
        jsons = list(labels_dir.glob("*.json"))
        if jsons:
            assert (labels_dir / "_SEALED").is_file()


def test_held_out_readme_omits_guarded_token() -> None:
    text = (HELD_OUT_ROOT / "README.md").read_text(encoding="utf-8")
    stripped = text.replace(_SCRIPT_FILENAME, "")
    assert _GUARDED_TOKEN not in stripped
    assert "已验证" not in text
    assert "经验证" not in text

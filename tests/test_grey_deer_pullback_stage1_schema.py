"""Schema checks for grey_deer_pullback_stage1/v1 result payloads.

The two committed stage-1 JSON artifacts are read from the working tree.
Mutations are deep copies. No price series is loaded.

Run:
    python -m pytest tests/test_grey_deer_pullback_stage1_schema.py -q
"""

from __future__ import annotations

import ast
import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import scripts.research.grey_deer_pullback_stage1_schema as schema  # noqa: E402

ORIGINAL = ROOT / "research/grey_deer/PULLBACK_STAGE1_RESULTS_2026-10-11.json"
RERUN = ROOT / "research/grey_deer/pullback_stage1_r1/PULLBACK_STAGE1_RESULTS_2026-10-11.json"
MODULE = ROOT / "scripts/research/grey_deer_pullback_stage1_schema.py"


@pytest.fixture(scope="module")
def original_text() -> str:
    return ORIGINAL.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def original(original_text: str) -> dict:
    payload = json.loads(original_text)
    assert isinstance(payload, dict)
    return payload


@pytest.fixture(scope="module")
def rerun() -> dict:
    payload = json.loads(RERUN.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _errors(payload: dict, mutate) -> list[str]:
    clone = copy.deepcopy(payload)
    mutate(clone)
    return schema.validate_payload(clone)


def test_committed_payloads_have_zero_errors(original: dict, rerun: dict) -> None:
    assert schema.validate_payload(original) == []
    assert schema.validate_payload(rerun) == []


def test_mutation_missing_key(original: dict) -> None:
    errors = _errors(original, lambda payload: payload.pop("gates"))
    assert any(err == "missing required key: gates" for err in errors)


def test_mutation_eleven_claims(original: dict) -> None:
    errors = _errors(original, lambda payload: payload["gates"].pop())
    assert any("expected 12 claims, found 11" in err for err in errors)


def test_mutation_duplicate_claim(original: dict) -> None:
    def mutate(payload: dict) -> None:
        payload["gates"][1] = copy.deepcopy(payload["gates"][0])

    errors = _errors(original, mutate)
    assert any("duplicate claim" in err for err in errors)


def test_mutation_bad_verdict_word(original: dict) -> None:
    def mutate(payload: dict) -> None:
        payload["gates"][0]["verdict"] = "live promotion"

    errors = _errors(original, mutate)
    assert any("live promotion" in err and "verdict" in err for err in errors)


def test_mutation_p_active_not_blocked(original: dict) -> None:
    def mutate(payload: dict) -> None:
        row = next(item for item in payload["gates"] if item["pop"] == "P-active")
        row["flags"] = [flag for flag in row["flags"] if flag != "OBSERVER_NOT_ON_MAIN"]

    errors = _errors(original, mutate)
    assert any(
        "P-active" in err and "OBSERVER_NOT_ON_MAIN" in err for err in errors
    )


def test_mutation_wrong_budget(original: dict) -> None:
    errors = _errors(original, lambda payload: payload["trial_budget"].__setitem__("budget", 70))
    assert any("trial_budget.budget must be 69" in err and "70" in err for err in errors)


def test_mutation_bad_sha(original: dict) -> None:
    errors = _errors(original, lambda payload: payload["prereg"].__setitem__("blob_sha", "not-a-sha"))
    assert any("prereg.blob_sha" in err and "40 lowercase hex" in err for err in errors)


def test_mutation_episodes_exceed_clusters(original: dict) -> None:
    def mutate(payload: dict) -> None:
        honest = payload["episodes"]["h5"]["binary"]["honest_n"]
        honest["episodes"] = honest["clusters"] + 1

    errors = _errors(original, mutate)
    assert any("episodes (" in err and "> clusters" in err for err in errors)


def test_mutation_lower_bound_above_point(original: dict) -> None:
    def mutate(payload: dict) -> None:
        row = next(item for item in payload["gates"] if item["id"] == "h5/P-all/quantile")
        row["lb"] = row["point"] + 1.0

    errors = _errors(original, mutate)
    assert any("lower bound" in err and "> point" in err for err in errors)


def test_mutation_wrong_schema_string(original: dict) -> None:
    errors = _errors(
        original,
        lambda payload: payload.__setitem__("schema", "grey_deer_pullback_stage1/v2"),
    )
    assert any("grey_deer_pullback_stage1/v1" in err and "grey_deer_pullback_stage1/v2" in err for err in errors)


def test_find_nonfinite_tokens_reports_negative_infinity(original_text: str) -> None:
    # The committed original payload stores gate lower bounds as JSON -Infinity
    # (the markdown gate table renders those as -inf). There is no bare Infinity
    # and no NaN. --strict-json therefore rejects the file.
    hits = schema.find_nonfinite_tokens(original_text)
    assert hits
    assert all(hit.endswith(": -Infinity") for hit in hits)
    assert "gates[0].lb: -Infinity" in hits

    rerun_hits = schema.find_nonfinite_tokens(RERUN.read_text(encoding="utf-8"))
    assert "gates[0].lb: -Infinity" in rerun_hits


def test_find_nonfinite_tokens_synthetic_paths() -> None:
    text = '{"a": [-Infinity, 1, NaN], "b": {"c": Infinity}}'
    assert schema.find_nonfinite_tokens(text) == [
        "a[0]: -Infinity",
        "a[2]: NaN",
        "b.c: Infinity",
    ]


def test_cli_plain_accepts_original_and_strict_json_rejects_it(original_text: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert "-Infinity" in original_text
    assert schema.main(["--path", str(ORIGINAL)]) == 0
    plain = capsys.readouterr()
    assert plain.out == ""

    assert schema.main(["--path", str(ORIGINAL), "--strict-json"]) == 1
    strict = capsys.readouterr()
    assert "gates[0].lb: -Infinity" in strict.out

    assert schema.main(["--path", str(RERUN)]) == 0
    assert schema.main(["--path", str(RERUN), "--strict-json"]) == 1


def test_module_imports_are_stdlib_only() -> None:
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            assert node.module is not None
            modules.add(node.module.split(".")[0])
    assert modules
    assert modules <= set(sys.stdlib_module_names)
    for banned in ("jsonschema", "pandas", "numpy", "scipy", "pyarrow"):
        assert banned not in modules

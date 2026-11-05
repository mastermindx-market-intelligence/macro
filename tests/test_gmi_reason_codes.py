"""GMI explorer reason-code words — every code the proof can emit has plain words.

Pins ``config/gmi_reason_codes.yml`` to ``scripts/gmi_coverage_proof.py``: every
REASON_* module constant, every state constant, and every code actually found in
a live coverage report must resolve to plain EN/ZH words, because the pages may
never print a code.
"""
from __future__ import annotations

import importlib
import re
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

from scripts.gmi_coverage_proof import (
    LEDGER_REMAINDER_STATES,
    LEDGER_STATE_MAP,
    MASTER_ISSUER_STATES,
)

REASON_PREFIX = "REASON_"
CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
THREE_CAPS_RE = re.compile(r"[A-Z]{3,}")
FORBIDDEN = ("validated", "falsif", "refut", "证伪")


def _load_yml() -> dict:
    path = Path(__file__).resolve().parent.parent / "config" / "gmi_reason_codes.yml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def yml() -> dict:
    return _load_yml()


@pytest.fixture(scope="module")
def sections_union(yml: dict) -> set[str]:
    return {code for section in yml.values() for code in section}


@pytest.fixture(scope="module")
def proof_outputs(tmp_path_factory) -> tuple[dict, dict]:
    """The REAL proof, run once into tmp — the STEP-0 command, newest snapshot."""
    import json
    import os
    import subprocess
    import sys

    root = Path(__file__).resolve().parent.parent
    snapshots = sorted((root / "data" / "symbol_directory" / "snapshots").glob("*.parquet"))
    assert snapshots, "no symbol directory snapshot present"
    out = tmp_path_factory.mktemp("gmi_proof")
    env = dict(os.environ, TZ="UTC")
    subprocess.run(
        [sys.executable, "-m", "scripts.gmi_coverage_proof",
         "--symbol-directory", str(snapshots[-1].relative_to(root)),
         "--out", str(out)],
        cwd=root, check=True, env=env,
    )
    report = json.loads((out / "coverage_report.json").read_text(encoding="utf-8"))
    manifest = json.loads((out / "UNIVERSE_MANIFEST.json").read_text(encoding="utf-8"))
    return report, manifest


def reason_constants() -> dict[str, str]:
    import scripts.gmi_coverage_proof as proof

    module = importlib.import_module("scripts.gmi_coverage_proof")
    assert module is proof
    return {name: getattr(proof, name) for name in dir(proof)
            if name.startswith(REASON_PREFIX) and isinstance(getattr(proof, name), str)
            and CODE_RE.match(getattr(proof, name))}


def emitted_codes(report: dict, manifest: dict | None) -> Iterator[str]:
    """Every code a live report (plus its manifest) can carry, walked."""
    for market in report["activity"].values():
        yield from market["remainder_by_reason"]
    for row in report["remainders"]:
        yield row["reason"]
    for key in report["owners"]:
        yield key.split("|", 1)[0]
    for view in report["identity_coverage"].values():
        yield from view["by_identity_status"]
    if manifest:
        for view in manifest["core_markets"].values():
            yield from view["securities_by_eligibility"]
    for market_states in report["graph_side_ledger"].values():
        for key in market_states:
            yield key.split("/", 1)[0]
    for micro in report["taxonomy"]["micros"]:
        yield micro["disposition"]


def test_every_reason_constant_has_words(yml: dict) -> None:
    reasons = yml["reasons"]
    missing = {value for value in reason_constants().values()
               if value not in reasons
               or not reasons[value].get("en")
               or not reasons[value].get("zh")}
    assert not missing, f"REASON_* constants without plain words: {sorted(missing)}"


def test_every_state_constant_has_words(yml: dict) -> None:
    union = {code for section in yml.values() for code in section}
    missing = {state for state in MASTER_ISSUER_STATES if state not in union}
    missing |= {state for state in LEDGER_REMAINDER_STATES if state not in union}
    for states in LEDGER_STATE_MAP.values():
        missing |= {state for state in states if state not in union}
    assert not missing, f"state constants without plain words: {sorted(missing)}"


@pytest.mark.needs_full_checkout("data")
def test_every_emitted_code_has_words(yml: dict, proof_outputs,
                                      sections_union: set[str]) -> None:
    report, manifest = proof_outputs
    missing = {code for code in emitted_codes(report, manifest)
               if code not in sections_union}
    assert not missing, f"emitted codes without plain words: {sorted(missing)}"


def test_master_issuer_states_covered(yml: dict) -> None:
    identity = yml["identity_states"]
    missing = {state for state in MASTER_ISSUER_STATES if state not in identity}
    assert not missing, f"MASTER_ISSUER_STATES missing from identity_states: {sorted(missing)}"


@pytest.mark.parametrize("section", ["reasons", "identity_states", "ledger_states",
                                     "dispositions"])
def test_words_are_plain(yml: dict, section: str) -> None:
    for code, words in yml[section].items():
        assert CODE_RE.match(code), f"{code}: not a CODE"
        for lang in ("en", "zh"):
            value = (words.get(lang) or "").strip()
            assert value, f"{section}.{code}.{lang}: empty"
            assert "_" not in value, f"{section}.{code}.{lang}: underscore"
            assert not THREE_CAPS_RE.search(value), \
                f"{section}.{code}.{lang}: 3+ capitals run"
            low = value.lower()
            for word in FORBIDDEN:
                assert word not in low, f"{section}.{code}.{lang}: {word!r}"
            if lang == "en":
                assert len(value.split()) <= 12, \
                    f"{section}.{code}.en: over 12 words"

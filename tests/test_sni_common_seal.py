"""test_sni_common_seal.py — golden digest, permutation, refusals, verify, render, schema, write."""
import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research/single_name_intelligence/common"))

import sni_seal  # noqa: E402
from sni_seal import (  # noqa: E402
    AUTHORITY_FLAG_KEYS,
    REQUIRED_TOP_LEVEL_KEYS,
    _check_identity_id_values,
    build_seal,
    canonical_json,
    sha256_bytes,
    sha256_text,
    render_seal_md,
    verify_seal,
    write_seal,
)

# pinned on purpose; any canonicalization change must change this test deliberately
GOLDEN_CONTENT_DIGEST = "a3dc7e2c11cb7f46857c2f4daafa53320d5ae2867c9c8d54ee2ee6c5fc3d8b50"

SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "contracts/single_name_intelligence/sni_seal.v1.schema.json"
)

_R2_REQUIRED_KEYS = (
    "schema_version",
    "lane",
    "protocol_ids",
    "cells",
    "budgets",
    "input_manifest",
    "prereg_digest",
    "identity_facts",
    "sealed_at_utc",
    "repo_ref",
    "not_supported",
    "authority_flags",
    "outcome_free",
    "extra",
    "content_digest",
)


def _golden_kwargs(**overrides):
    kwargs = {
        "lane": "sni-a2-seal",
        "protocol_ids": ["sni.p2", "sni.p1"],
        "cells": [
            {"protocol": "sni.p2", "version": "1", "split": "eval", "h": 20},
            {"protocol": "sni.p1", "version": "1", "split": "eval", "h": 5},
        ],
        "budgets": {"event_response": 4, "residual": 2, "sni.p1": 5, "sni.p2": 20},
        "input_manifest": [
            {"path": "b/file.txt", "sha256": "11" * 32},
            {"path": "a/file.txt", "sha256": "22" * 32},
        ],
        "prereg_digest": "ab" * 32,
        "identity_facts": {
            "canonical_issuer_id": None,
            "canonical_security_id": None,
            "display_name": "synthetic-issuer",
            "issuer_id_owner": "Stock Identity / Data OS",
        },
        "sealed_at_utc": "2026-10-12T00:00:00Z",
        "repo_ref": "origin/main",
        "not_supported": ("news_impact", "causal_claim"),
        "extra": {"fixture": "synthetic"},
    }
    kwargs.update(overrides)
    return kwargs


def _probe_kwargs(**overrides):
    kwargs = {
        "lane": "X",
        "protocol_ids": ["P04"],
        "cells": [{"protocol": "P04", "version": 1, "split": "TEST", "h": 1}],
        "budgets": {"P04": 13},
        "input_manifest": [{"path": "a.json", "sha256": "a" * 64}],
        "prereg_digest": "a" * 64,
        "identity_facts": {"issuer_id": None},
        "sealed_at_utc": "2026-10-12T00:00:00Z",
        "repo_ref": "abc",
    }
    kwargs.update(overrides)
    return kwargs


def _recompute_digest(seal):
    body = {key: value for key, value in seal.items() if key != "content_digest"}
    seal["content_digest"] = sha256_text(canonical_json(body))
    return seal


def test_golden_content_digest():
    seal = build_seal(**_golden_kwargs())
    assert seal["content_digest"] == GOLDEN_CONTENT_DIGEST
    assert seal["schema_version"] == "sni_seal.v1"
    assert seal["outcome_free"] is True
    assert all(seal["authority_flags"][key] is False for key in AUTHORITY_FLAG_KEYS)


def test_permutation_identical_digest():
    base = build_seal(**_golden_kwargs())
    cells = [
        {"h": 5, "split": "eval", "version": "1", "protocol": "sni.p1"},
        {"h": 20, "split": "eval", "version": "1", "protocol": "sni.p2"},
    ]
    protocol_ids = ["sni.p1", "sni.p2"]
    manifest = [
        {"sha256": "22" * 32, "path": "a/file.txt"},
        {"sha256": "11" * 32, "path": "b/file.txt"},
    ]
    budgets = {}
    for key, value in (("residual", 2), ("event_response", 4), ("sni.p2", 20), ("sni.p1", 5)):
        budgets[key] = value
    identity_facts = {}
    for key, value in (
        ("issuer_id_owner", "Stock Identity / Data OS"),
        ("display_name", "synthetic-issuer"),
        ("canonical_security_id", None),
        ("canonical_issuer_id", None),
    ):
        identity_facts[key] = value
    extra = {}
    extra["fixture"] = "synthetic"
    other = build_seal(
        lane="sni-a2-seal",
        protocol_ids=protocol_ids,
        cells=cells,
        budgets=budgets,
        input_manifest=manifest,
        prereg_digest="ab" * 32,
        identity_facts=identity_facts,
        sealed_at_utc="2026-10-12T00:00:00Z",
        repo_ref="origin/main",
        not_supported=["causal_claim", "news_impact"],
        extra=extra,
    )
    assert other["content_digest"] == base["content_digest"] == GOLDEN_CONTENT_DIGEST
    assert other["cells"] == base["cells"]
    assert other["protocol_ids"] == base["protocol_ids"]
    assert other["input_manifest"] == base["input_manifest"]


def test_refusals():
    cell = {"protocol": "sni.p1", "version": "1", "split": "eval", "h": 5}
    with pytest.raises(ValueError):
        build_seal(**_golden_kwargs(cells=[cell, dict(cell)]))
    with pytest.raises(ValueError):
        build_seal(**_golden_kwargs(budgets={"residual": 0}))
    with pytest.raises(ValueError):
        build_seal(**_golden_kwargs(extra={"rank_authority": True}))
    with pytest.raises(ValueError):
        build_seal(**_golden_kwargs(prereg_digest="not-a-digest"))
    with pytest.raises(ValueError):
        build_seal(**_golden_kwargs(extra={"x": float("nan")}))


def test_verify():
    seal = build_seal(**_golden_kwargs())
    assert verify_seal(seal) == []

    flipped = copy.deepcopy(seal)
    flipped["cells"][1]["h"] = 21
    digest_violations = verify_seal(flipped)
    assert len(digest_violations) == 1
    assert "content_digest" in digest_violations[0]

    flagged = copy.deepcopy(seal)
    flagged["authority_flags"]["trade_authority"] = True
    flag_violations = verify_seal(flagged)
    assert any("trade_authority" in item for item in flag_violations)

    stripped = copy.deepcopy(seal)
    del stripped["outcome_free"]
    outcome_violations = verify_seal(stripped)
    assert any("outcome_free" in item for item in outcome_violations)

    path = seal["input_manifest"][0]["path"]
    mismatch = verify_seal(seal, file_bytes={path: b"not-the-pinned-bytes"})
    assert any(path in item for item in mismatch)


def test_render():
    seal = build_seal(**_golden_kwargs())
    md = render_seal_md(seal)
    for key in AUTHORITY_FLAG_KEYS:
        assert f"{key}: false" in md
    assert "outcome_free: true" in md
    assert seal["content_digest"] in md
    assert "cells: 2" in md


def test_schema():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    seal = build_seal(**_golden_kwargs())
    jsonschema.validate(seal, schema)
    bad = copy.deepcopy(seal)
    bad["authority_flags"]["trade_authority"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)


def test_write_seal_round_trip(tmp_path):
    seal = build_seal(**_golden_kwargs())
    json_path, _md_path = write_seal(seal, tmp_path)
    loaded = json.loads(json_path.read_text(encoding="utf-8"))
    assert loaded == seal
    assert verify_seal(loaded) == []


def test_r1_01_nested_authority_in_extra():
    with pytest.raises(ValueError):
        build_seal(**_probe_kwargs(extra={"meta": {"trade_authority": True}}))
    with pytest.raises(ValueError):
        build_seal(**_probe_kwargs(extra={"rows": [{"gate_authority": False}]}))


def test_r1_02_authority_in_identity_facts():
    with pytest.raises(ValueError):
        build_seal(
            **_probe_kwargs(identity_facts={"issuer_id": None, "trade_authority": True})
        )


def test_r1_03_verify_injected_authority():
    seal = build_seal(**_probe_kwargs())

    extra_tampered = copy.deepcopy(seal)
    extra_tampered["extra"] = {"trade_authority": True}
    _recompute_digest(extra_tampered)
    extra_violations = verify_seal(extra_tampered)
    assert extra_violations
    assert any("extra.trade_authority" in item for item in extra_violations)

    identity_tampered = copy.deepcopy(seal)
    identity_tampered["identity_facts"] = {"issuer_id": None, "trade_authority": True}
    _recompute_digest(identity_tampered)
    identity_violations = verify_seal(identity_tampered)
    assert identity_violations
    assert any("identity_facts.trade_authority" in item for item in identity_violations)

    cell_tampered = copy.deepcopy(seal)
    cell_tampered["cells"][0]["trade_authority"] = True
    _recompute_digest(cell_tampered)
    cell_violations = verify_seal(cell_tampered)
    assert cell_violations
    assert any("cells[0].trade_authority" in item for item in cell_violations)


def test_r1_04_partial_file_bytes():
    seal = build_seal(**_probe_kwargs())
    missing = verify_seal(seal, file_bytes={})
    assert any(
        "manifest path a.json missing from file_bytes" in item for item in missing
    )

    payload = b'{"synthetic":true}'
    digest = sha256_bytes(payload)
    matched = build_seal(
        **_probe_kwargs(input_manifest=[{"path": "a.json", "sha256": digest}])
    )
    assert verify_seal(matched, file_bytes={"a.json": payload}) == []


def test_r1_05_budgets_mandatory():
    with pytest.raises(ValueError):
        build_seal(**{**_probe_kwargs(), "budgets": {}})
    with pytest.raises(ValueError):
        build_seal(**{**_probe_kwargs(), "budgets": {"P05": 13}})

    seal = build_seal(**_probe_kwargs())
    deleted = copy.deepcopy(seal)
    del deleted["budgets"]
    _recompute_digest(deleted)
    deleted_violations = verify_seal(deleted)
    assert deleted_violations
    assert any("budgets" in item for item in deleted_violations)

    bool_budget = copy.deepcopy(seal)
    bool_budget["budgets"] = {"P04": True}
    _recompute_digest(bool_budget)
    bool_violations = verify_seal(bool_budget)
    assert any("P04" in item for item in bool_violations)


@pytest.mark.parametrize(
    "case",
    [
        "top_level_extra_trade_authority",
        "nonbool_trade_authority_flag",
        "canonical_json_nan",
        "clean_seal_verifies",
        "minted_ticker_identity_id",
    ],
)
def test_r1_06_regression_pins(case):
    if case == "top_level_extra_trade_authority":
        with pytest.raises(ValueError):
            build_seal(**_probe_kwargs(extra={"trade_authority": True}))
        return
    if case == "nonbool_trade_authority_flag":
        seal = build_seal(**_probe_kwargs())
        flagged = copy.deepcopy(seal)
        flagged["authority_flags"]["trade_authority"] = 0
        violations = verify_seal(flagged)
        assert any("trade_authority" in item for item in violations)
        return
    if case == "canonical_json_nan":
        with pytest.raises(ValueError):
            canonical_json({"x": float("nan")})
        return
    if case == "clean_seal_verifies":
        assert verify_seal(build_seal(**_probe_kwargs())) == []
        return
    if case == "minted_ticker_identity_id":
        with pytest.raises(ValueError):
            _check_identity_id_values({"issuer_id": {"ticker": "BABA"}})
        return
    raise AssertionError(f"unhandled case {case}")


def test_r2_04_write_seal_refuses_overwrite(tmp_path):
    seal = build_seal(**_golden_kwargs())
    json_path, _md_path = write_seal(seal, tmp_path)
    before = sha256_bytes(json_path.read_bytes())
    with pytest.raises(FileExistsError):
        write_seal(seal, tmp_path)
    after = sha256_bytes(json_path.read_bytes())
    assert before == after


def test_r2_04_write_seal_refuses_invalid_creates_no_file(tmp_path):
    seal = build_seal(**_golden_kwargs())
    tampered = copy.deepcopy(seal)
    tampered["cells"][0]["h"] = 999
    out = tmp_path / "new_dir"
    out.mkdir()
    with pytest.raises(ValueError):
        write_seal(tampered, out)
    assert list(out.iterdir()) == []


def test_r2_04_write_seal_refuses_if_md_exists(tmp_path):
    seal = build_seal(**_golden_kwargs())
    (tmp_path / "SEAL.md").write_text("preexisting", encoding="utf-8")
    with pytest.raises(FileExistsError):
        write_seal(seal, tmp_path)
    assert not (tmp_path / "SEAL.json").exists()
    assert (tmp_path / "SEAL.md").read_text(encoding="utf-8") == "preexisting"


def test_r2_04_write_seal_rollback_on_second_file_failure(tmp_path, monkeypatch):
    seal = build_seal(**_golden_kwargs())
    real_open = open

    def flaky_open(path, mode="r", *args, **kwargs):
        if Path(path).name == "SEAL.md" and "x" in str(mode):
            raise OSError("simulated md write failure")
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(sni_seal, "open", flaky_open, raising=False)
    with pytest.raises(OSError, match="simulated md write failure"):
        write_seal(seal, tmp_path)
    assert not (tmp_path / "SEAL.json").exists()
    assert not (tmp_path / "SEAL.md").exists()


def test_r2_07_required_key_set_matches_build_seal():
    seal = build_seal(**_golden_kwargs())
    assert tuple(REQUIRED_TOP_LEVEL_KEYS) == _R2_REQUIRED_KEYS
    assert set(seal.keys()) == set(_R2_REQUIRED_KEYS)


@pytest.mark.parametrize("key", _R2_REQUIRED_KEYS)
def test_r2_07_missing_required_key(key):
    seal = copy.deepcopy(build_seal(**_golden_kwargs()))
    del seal[key]
    if key != "content_digest":
        _recompute_digest(seal)
    violations = verify_seal(seal)
    assert violations
    assert any(key in item for item in violations)


def test_r2_07_unknown_top_level_key():
    seal = copy.deepcopy(build_seal(**_golden_kwargs()))
    seal["bonus"] = 1
    _recompute_digest(seal)
    violations = verify_seal(seal)
    assert violations
    assert any("bonus" in item for item in violations)


def test_r2_07_unknown_cell_key():
    seal = copy.deepcopy(build_seal(**_golden_kwargs()))
    seal["cells"][0]["bonus_field"] = 1
    _recompute_digest(seal)
    violations = verify_seal(seal)
    assert violations
    assert any("cells[0] has unknown key bonus_field" in item for item in violations)


def test_r2_07_type_checks():
    seal = build_seal(**_golden_kwargs())
    cases = [
        ("lane", "", "lane"),
        ("repo_ref", "", "repo_ref"),
        ("prereg_digest", "zz", "prereg_digest"),
        ("sealed_at_utc", "not-a-date", "sealed_at_utc"),
        ("protocol_ids", "P04", "protocol_ids"),
        ("not_supported", "news", "not_supported"),
        ("extra", ["nope"], "extra"),
        ("identity_facts", ["nope"], "identity_facts"),
        ("input_manifest", {"path": "a"}, "input_manifest"),
    ]
    for key, bad, named in cases:
        tampered = copy.deepcopy(seal)
        tampered[key] = bad
        _recompute_digest(tampered)
        violations = verify_seal(tampered)
        assert violations, key
        assert any(named in item for item in violations), (key, violations)


def test_r2_09_cells_not_sorted():
    seal = copy.deepcopy(build_seal(**_golden_kwargs()))
    assert len(seal["cells"]) >= 2
    seal["cells"] = list(reversed(seal["cells"]))
    _recompute_digest(seal)
    violations = verify_seal(seal)
    assert "cells not sorted" in violations


def test_r2_09_extra_cell_key():
    seal = copy.deepcopy(build_seal(**_golden_kwargs()))
    seal["cells"][0]["extra_field"] = "synthetic"
    _recompute_digest(seal)
    violations = verify_seal(seal)
    assert "cells[0] has unknown key extra_field" in violations


def test_r2_09_cells_is_not_a_list():
    seal = copy.deepcopy(build_seal(**_golden_kwargs()))
    seal["cells"] = {"protocol": "sni.p1"}
    _recompute_digest(seal)
    violations = verify_seal(seal)
    assert "cells is not a list" in violations
    assert "cells not sorted" not in violations


def test_r2_10_build_refuses_case_variant_in_extra():
    with pytest.raises(ValueError):
        build_seal(**_probe_kwargs(extra={"Trade_Authority": False}))
    with pytest.raises(ValueError):
        build_seal(**_probe_kwargs(extra={"TRADE_AUTHORITY": False}))


def test_r2_10_build_refuses_case_variant_in_identity_facts():
    with pytest.raises(ValueError):
        build_seal(**_probe_kwargs(identity_facts={"x": {"RANK_AUTHORITY": False}}))


def test_r2_10_verify_refuses_padded_case_variant_in_extra():
    seal = copy.deepcopy(build_seal(**_probe_kwargs()))
    seal["extra"] = {" trade_authority ": False}
    _recompute_digest(seal)
    violations = verify_seal(seal)
    assert violations
    assert any("trade_authority" in item.casefold() for item in violations)


def test_r2_10_verify_refuses_case_variant_at_top_level():
    seal = build_seal(**_probe_kwargs())
    for key in ("Trade_Authority", "TRADE_AUTHORITY", "Authority_Flags"):
        tampered = copy.deepcopy(seal)
        tampered[key] = False
        _recompute_digest(tampered)
        violations = verify_seal(tampered)
        assert violations, key
        assert any(
            key in item or "authority" in item.casefold() for item in violations
        ), (key, violations)

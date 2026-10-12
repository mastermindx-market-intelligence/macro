"""test_sni_common_seal.py — golden digest, permutation, refusals, verify, render, schema, write."""
import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research/single_name_intelligence/common"))

from sni_seal import (  # noqa: E402
    AUTHORITY_FLAG_KEYS,
    build_seal,
    render_seal_md,
    verify_seal,
    write_seal,
)

# pinned on purpose; any canonicalization change must change this test deliberately
GOLDEN_CONTENT_DIGEST = "66e09b97ed0151d3a8eaae437e6fa02de06c2d4599ab243f90ebff6df48e428e"

SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "contracts/single_name_intelligence/sni_seal.v1.schema.json"
)


def _golden_kwargs(**overrides):
    kwargs = {
        "lane": "sni-a2-seal",
        "protocol_ids": ["sni.p2", "sni.p1"],
        "cells": [
            {"protocol": "sni.p2", "version": "1", "split": "eval", "h": 20},
            {"protocol": "sni.p1", "version": "1", "split": "eval", "h": 5},
        ],
        "budgets": {"event_response": 4, "residual": 2},
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
    for key, value in (("residual", 2), ("event_response", 4)):
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

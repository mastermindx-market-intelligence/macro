"""A34 guard: the per-pack proof ledger cannot hide a gap.

Z0 closure-matrix row A34 requires per-pack schema/gold/held-out/review/live
proofs where a group summary cannot hide a gap. These hermetic guards keep
``FIF_A34_PACK_PROOF_LEDGER.json`` honest: every registered pack appears once,
the committed document matches a fresh regeneration, every missing proof is a
listed gap, no aggregate field can mask a per-pack gap, and the generator
measures the held-out split by existence checks only — never by reading bytes
under the sealed root.
"""
from __future__ import annotations

import builtins
import importlib.util
import io
import json
import os
from pathlib import Path

import pytest

from engine.fundamental_forensics.specialist_packs import registered_pack_ids

ROOT = Path(__file__).resolve().parent.parent
LEDGER_PATH = ROOT / "research/financial_intelligence_fabric/FIF_A34_PACK_PROOF_LEDGER.json"
PROTOCOL_PATH = ROOT / "research/financial_intelligence_fabric/FIF_Q0_QUALITY_PROTOCOL.json"
GENERATOR_PATH = ROOT / "scripts/fif_a34_pack_proof_ledger.py"

PACK_COUNT = 12
PROOF_ORDER = ("schema", "gold", "held_out", "review", "live")
FORBIDDEN_KEY_TOKENS = ("average", "mean", "score", "percent", "rate")


def _generator():
    spec = importlib.util.spec_from_file_location("fif_a34_pack_proof_ledger", GENERATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _committed() -> dict:
    return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))


def _q0_pack_ids() -> list[str]:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    return [pack["pack_id"] for pack in protocol["packs"]]


def test_a34_ledger_lists_every_registered_pack_once() -> None:
    doc = _committed()
    listed = [pack["pack_id"] for pack in doc["packs"]]
    assert listed == list(registered_pack_ids())
    assert listed == sorted(_q0_pack_ids())
    assert len(listed) == PACK_COUNT
    assert len(set(listed)) == PACK_COUNT


def test_a34_ledger_is_fresh() -> None:
    committed = _committed()
    fresh = _generator().build_ledger()

    def strip(doc: dict) -> dict:
        return {k: v for k, v in doc.items() if k not in ("generated_at", "base_commit")}

    assert strip(committed) == strip(fresh)


def test_a34_every_missing_proof_is_a_listed_gap() -> None:
    doc = _committed()
    for pack in doc["packs"]:
        expected = [proof for proof in PROOF_ORDER if pack["proofs"][proof]["state"] == "missing"]
        assert pack["gaps"] == expected, pack["pack_id"]
        assert doc["gaps_by_pack"][pack["pack_id"]] == pack["gaps"], pack["pack_id"]
    assert set(doc["gaps_by_pack"]) == {pack["pack_id"] for pack in doc["packs"]}


def _iter_keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _iter_keys(value)
    elif isinstance(node, list):
        for value in node:
            yield from _iter_keys(value)


def test_a34_no_aggregate_can_hide_a_gap() -> None:
    doc = _committed()
    # Token match, not substring: the frozen ledger shape's own `generated_at`
    # key contains the letters "rate" inside "generated", so a raw substring
    # ban would reject the mandated timestamp. Matching the forbidden terms
    # against the key's underscore-delimited tokens still catches every
    # aggregate naming (pass_rate, mean_score, coverage_percent, ...) while
    # admitting non-aggregate keys like generated_at.
    for key in _iter_keys(doc):
        tokens = set(str(key).lower().split("_"))
        for forbidden in FORBIDDEN_KEY_TOKENS:
            assert forbidden not in tokens, f"aggregate-sounding key: {key}"
    with_gaps = [pack["pack_id"] for pack in doc["packs"] if pack["gaps"]]
    assert doc["packs_with_gaps"] + doc["packs_complete"] == PACK_COUNT
    assert doc["packs_with_gaps"] == len(with_gaps)
    assert doc["packs_complete"] == PACK_COUNT - len(with_gaps)
    for pack_id in with_gaps:
        pack = next(pack for pack in doc["packs"] if pack["pack_id"] == pack_id)
        assert pack["gaps"], pack_id  # counted as gapped only with a listed gap


def test_a34_ledger_reads_no_held_out_contents(monkeypatch) -> None:
    real_open = builtins.open
    # The sealed root is taken from the generator itself, so this module never
    # names the held-out path and the isolation allowlist stays untouched.
    held_out_root = ROOT / _generator().HELD_OUT_ROOT_REL
    sealed_root = str(held_out_root.resolve())

    def guarded_open(file, *args, **kwargs):
        try:
            resolved = str(Path(file).resolve())
        except (TypeError, ValueError, OSError):
            resolved = ""
        if resolved == sealed_root or resolved.startswith(sealed_root + os.sep):
            raise AssertionError(f"A34 generator opened held-out contents: {file!r}")
        return real_open(file, *args, **kwargs)

    def _guard_path(path_self: Path) -> None:
        resolved = str(path_self.resolve())
        if resolved == sealed_root or resolved.startswith(sealed_root + os.sep):
            raise AssertionError(f"A34 generator read held-out contents: {path_self!r}")

    real_read_text = Path.read_text
    real_read_bytes = Path.read_bytes
    real_path_open = Path.open

    def guarded_read_text(path_self: Path, *args, **kwargs):
        _guard_path(path_self)
        return real_read_text(path_self, *args, **kwargs)

    def guarded_read_bytes(path_self: Path, *args, **kwargs):
        _guard_path(path_self)
        return real_read_bytes(path_self, *args, **kwargs)

    def guarded_path_open(path_self: Path, *args, **kwargs):
        _guard_path(path_self)
        return real_path_open(path_self, *args, **kwargs)

    # Every read route the generator could take (review F2): ``builtins.open``
    # and ``io.open`` are distinct bindings once one is patched, and the
    # ``Path`` readers route through ``io.open``.
    monkeypatch.setattr(builtins, "open", guarded_open)
    monkeypatch.setattr(io, "open", guarded_open)
    monkeypatch.setattr(Path, "read_text", guarded_read_text)
    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)
    monkeypatch.setattr(Path, "open", guarded_path_open)
    doc = _generator().build_ledger()
    assert len(doc["packs"]) == PACK_COUNT

    # The guard itself must fire on each route, or it proves nothing.
    probe = held_out_root / "README.md"
    for route in (
        lambda: open(probe, encoding="utf-8"),
        lambda: io.open(probe, encoding="utf-8"),
        lambda: probe.read_text(encoding="utf-8"),
        lambda: probe.read_bytes(),
        lambda: probe.open(encoding="utf-8"),
    ):
        with pytest.raises(AssertionError):
            route()

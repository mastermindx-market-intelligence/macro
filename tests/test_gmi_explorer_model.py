"""GMI explorer model — the real artifacts build the fixture-shaped model.

Runs the REAL coverage proof once per module (the STEP-0 command), then pins
counts, category partition, display names, rights-withheld behaviour and
determinism of scripts/gmi_explorer/model.py.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from scripts.gmi_explorer import model as model_module
from scripts.gmi_explorer.model import build_model

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def proof(tmp_path_factory) -> dict:
    """The REAL proof, run once into tmp — the STEP-0 command, newest snapshot."""
    snapshots = sorted((ROOT / "data" / "symbol_directory" / "snapshots").glob("*.parquet"))
    assert snapshots, "no symbol directory snapshot present"
    out = tmp_path_factory.mktemp("gmi_proof")
    env = dict(os.environ, TZ="UTC")
    subprocess.run(
        [sys.executable, "-m", "scripts.gmi_coverage_proof",
         "--symbol-directory", str(snapshots[-1].relative_to(ROOT)),
         "--out", str(out)],
        cwd=ROOT, check=True, env=env,
    )
    return json.loads((out / "coverage_report.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def model(proof: dict) -> dict:
    return build_model(proof, None, repo_root=ROOT)


@pytest.mark.needs_full_checkout("data")
def test_totals(model: dict, proof: dict) -> None:
    totals = model["totals"]
    assert totals["micros"] == 371
    assert totals["core"] == 68 == len(proof["taxonomy"]["micros"])
    assert totals["extended"] == 303 == len(proof["taxonomy"]["expansion_micros"])
    assert totals["admitted_micros"] == 1


@pytest.mark.needs_full_checkout("data")
def test_cats_partition(model: dict) -> None:
    cats = model["cats"]
    assert len(cats) == 10
    seen: list[str] = []
    for cat in cats:
        seen.extend(cat["micros"])
    assert len(seen) == 371 == len(set(seen))
    assert set(seen) == set(model["micros"])


@pytest.mark.needs_full_checkout("data")
def test_every_micro_has_names(model: dict) -> None:
    for mid, micro in model["micros"].items():
        assert micro["en"].strip(), f"{mid}: empty en"
        assert micro["zh"].strip(), f"{mid}: empty zh"


@pytest.mark.needs_full_checkout("data")
def test_vcp_core_only(model: dict) -> None:
    core_no_vcp = [mid for mid, m in model["micros"].items()
                   if m["tier"] == "acceptance" and m["vcp"] is None]
    display_with_vcp = [mid for mid, m in model["micros"].items()
                        if m["tier"] == "display" and m["vcp"] is None]
    assert len(core_no_vcp) == 68
    assert display_with_vcp == []


@pytest.mark.needs_full_checkout("data")
def test_disposition_counts_match_report(model: dict, proof: dict) -> None:
    expected = Counter(m["disposition"] for m in proof["taxonomy"]["micros"])
    assert model["disposition_counts"] == dict(expected)


@pytest.mark.needs_full_checkout("data")
def test_kinds(model: dict, proof: dict) -> None:
    assert model["micros"]["theme:hbm_packaging"]["kind"] == "adm"
    held = sum(1 for m in model["micros"].values() if m["kind"] == "held")
    proposed = sum(1 for m in proof["taxonomy"]["micros"]
                   if m["disposition"] == "PROPOSED_ONLY")
    assert held == proposed


@pytest.mark.needs_full_checkout("data")
def test_edges_state_present_for_the_committed_envelope(model: dict) -> None:
    """DEC:GMI-RELATIONSHIP-ENVELOPE-CONTRACT — the committed v1 envelope is read at display tier."""
    store = json.loads((ROOT / model_module.EDGES_PATH).read_text(encoding="utf-8"))
    assert store["schema"] == "company_intelligence.relationship_edges/v1"
    assert model["edges_state"] == "present"
    assert model["edges"] == store["edges"]
    assert len(model["edges"]) > 0
    package = model["edge_package"]
    assert package is not None
    assert set(package) == set(store) - {"edges"}
    assert package["counts"]["edges"] == len(model["edges"])
    assert package["adoption_state"] == "proposed"
    assert not any(package["authority"].values()), "display tier: no authority field may be true"
    parties = {e[side]["issuer_id"] for e in model["edges"] for side in ("from", "to")}
    assert set(model["party_names"]) == parties
    deck = json.loads((ROOT / model_module.DECK_PATH).read_text(encoding="utf-8"))
    assert model["deck"] == deck


def _envelope(edges: list) -> dict:
    return {"schema": model_module.EDGES_SCHEMA, "package_id": "pkg:0123456789abcdef",
            "adoption_state": "proposed", "as_of": "2026-10-21T00:00:00Z",
            "authority": {"rank": False, "size": False, "gate": False},
            "counts": {"edges": len(edges), "non_edges": 3,
                       "edges_by_species": {"supplier_customer": len(edges)}},
            "edges": edges}


def test_read_edges_absent_file(tmp_path: Path) -> None:
    assert model_module.read_edges(tmp_path / "relationship_edges.json") == ([], "empty", None)


def test_read_edges_bare_list(tmp_path: Path) -> None:
    path = tmp_path / "relationship_edges.json"
    path.write_text('[{"edge": "example"}]', encoding="utf-8")
    assert model_module.read_edges(path) == ([{"edge": "example"}], "present", None)


def test_read_edges_envelope(tmp_path: Path) -> None:
    edges = [{"edge": i} for i in range(248)]
    payload = _envelope(edges)
    path = tmp_path / "relationship_edges.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    got_edges, state, package = model_module.read_edges(path)
    assert state == "present"
    assert got_edges == edges and len(got_edges) == 248
    assert package == {k: v for k, v in payload.items() if k != "edges"}
    assert set(package) == set(payload) - {"edges"}


@pytest.mark.parametrize("junk", [
    {"edges": [{"edge": "example"}]},                                  # no schema
    {"schema": "company_intelligence.relationship_edges/v2", "edges": []},  # wrong schema
    {"schema": "company_intelligence.relationship_edges/v1", "edges": {"a": 1}},  # edges not a list
    {"schema": "company_intelligence.relationship_edges/v1"},          # no edges key
    "a string", 42, None,
])
def test_read_edges_junk_shape_is_empty_never_raises(tmp_path: Path, junk) -> None:
    path = tmp_path / "relationship_edges.json"
    path.write_text(json.dumps(junk), encoding="utf-8")
    assert model_module.read_edges(path) == ([], "empty", None)


@pytest.mark.needs_full_checkout("data")
def test_edges_state_present_when_file_exists(model: dict, proof: dict,
                                              tmp_path: Path,
                                              monkeypatch: pytest.MonkeyPatch) -> None:
    fake = tmp_path / "relationship_edges.json"
    fake.write_text('[{"edge": "example"}]', encoding="utf-8")
    monkeypatch.setattr(model_module, "EDGES_PATH", fake)
    patched = build_model(proof, None, repo_root=ROOT)
    assert patched["edges_state"] == "present"
    assert patched["edges"] == [{"edge": "example"}]
    assert patched["edge_package"] is None


@pytest.mark.needs_full_checkout("data")
def test_micron_issuer(model: dict) -> None:
    issuers = {i["ticker"]: i for i in model["issuers"]}
    mu = issuers["MU"]
    assert mu["display_name"] == "Micron Technology"
    assert mu["display_name_source"] == "symbol_directory.security_name"
    assert mu["resolution_state"] == "RESOLVED"
    link = mu["links"][0]
    assert link["micro_id"] == "theme:hbm_packaging"
    assert link["excerpt_text"] is None
    assert link["excerpt_state"] == "rights_withheld"
    assert link["scope"]["counterparty_display_name"] == "NVIDIA"
    # A URL is a pointer, never emitted source text.
    assert link["source"]["url_if_public"].startswith("https://")


@pytest.mark.needs_full_checkout("data")
def test_card_payloads(model: dict) -> None:
    cards = model["card_payloads"]
    assert len(cards) == 371
    for card in cards:
        assert card["reason_en"] and "_" not in card["reason_en"]
        assert card["reason_zh"]
    cat_order = {cat["id"]: i for i, cat in enumerate(model["cats"])}
    kind_rank = {"held": 0, "adm": 1, "acc": 2, "disp": 3}
    keys = [(cat_order[c["cat_id"]], kind_rank[c["kind"]], c["en"].lower())
            for c in cards]
    assert keys == sorted(keys)


@pytest.mark.needs_full_checkout("data")
def test_build_is_deterministic(model: dict, proof: dict) -> None:
    again = build_model(proof, None, repo_root=ROOT)

    def freeze(m: dict) -> str:
        stripped = {k: v for k, v in m.items() if k != "provenance"}
        stripped["provenance"] = {k: v for k, v in m["provenance"].items()
                                  if k != "built_at_utc"}
        return json.dumps(stripped, sort_keys=True)

    assert freeze(model) == freeze(again)

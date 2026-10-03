"""The source-local theme plane — hostile acceptance tests D–M (W3A §5, under §9).

WHAT THESE PROTECT. The local plane's failure modes are all quiet ones, and each test
below is a specific way the plane could look right and be wrong:

* **D** a member leaves ONE subtheme and stays in another — exactly one edge closes. The
  live case exists (the 2026-08-14 vintage does this 26 times); the failure is a plane
  that keys on the ticker instead of (subtheme, ticker) and closes everything.
* **E** a ratified identity break mints the epoch the break says, from the source's own
  tree, with no builder deciding anything.
* **F** the SNDK class: one name in five subthemes keeps five memberships. A plane that
  quietly picks a "primary" label loses four of them and nobody notices.
* **G/H** a local theme with NO canonical mapping survives with its memberships and the
  guard stays green. Null canonical mapping is the lawful steady state, not a defect —
  312 live CN cases and every Finviz subtheme.
* **I** an unseeded concept + a fixture that fails capability.v1 lands `semantic_only` in
  the SIDE-CAR, and no state field anywhere on the node.
* **J** a membership and a contradicting external classification COEXIST; nothing nets.
* **K** as-known-at(T) excludes what was learned at T+5. Bitemporality is only real if
  the belief filter actually removes later knowledge.
* **L** the rights gate refuses unresolved/internal families and passes display ones.
* **M** all FOUR GMI synapse entries carry six literal-false authority booleans.

Plus the amendments: capability re-derives UP when the substrate improves (the
anti-ratchet, §9.3), the materializer's second shrink wall, the adjacent-only vintage
dedupe (an A→B→A revert keeps three vintages and both intervals), and the two canonical
paths agreeing.

Fixture-only: tmp stores, tmp trees, no network, and nothing writes under ``data/``.
"""
from __future__ import annotations

import json

import jsonschema
from pathlib import Path

import pandas as pd
import pytest
import yaml

from engine.theme_graph import (capability, identity, local_sources, materialize,
                                probation, rights, store)
from engine.theme_graph.ontology import compose_neighborhood
from lib import config
from scripts import check_theme_graph_contracts as guard

ROOT = Path(__file__).resolve().parents[1]

SEED_ASOF = "2026-06-27"
V2_ASOF = "2026-08-14"
V3_ASOF = "2026-09-30"
BUILD_DAY = "2026-08-20"
STAMP = "2026-08-20T00:00:00Z"
XWALK_DATE = "2026-07-09"
CN_SEED = "2021-06-15"
THS_DOC_DATE = "2026-06-30"
CMAP_ASOF = "2026-06-27"

KNOWN_CODE = "900001"      # concept with a curated crosswalk row AND a seeded basket
UNSEEDED_CODE = "900002"   # concept with no basket at all


# ---------------------------------------------------------------------------
# Fixture inputs
# ---------------------------------------------------------------------------

def _write(path: Path, doc: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")


def _tree(subthemes: dict[str, list[str]], *, theme: str = "Artificial Intelligence",
          names: dict[str, str] | None = None) -> list[dict]:
    """The committed tree shape: [{theme, key, subsectors:[{key, name, members}]}]."""
    names = names or {}
    return [{
        "theme": theme, "key": theme,
        "subsectors": [
            {"key": key, "name": names.get(key, key.title()),
             "description": f"{key} description", "members": list(members)}
            for key, members in subthemes.items()
        ],
    }]


def _seed_doc(subthemes: dict[str, list[str]], *, asof: str = SEED_ASOF) -> dict:
    trees = _tree(subthemes)
    return {"source": "fixture://finviz", "asof": asof,
            "counts": {"themes": len(trees)}, "themes": trees}


def _history(rows: list[tuple[str, dict[str, list[str]]]]) -> str:
    return "".join(
        json.dumps({"asof": asof, "sha256": "fixture", "tree": _tree(subthemes)},
                   ensure_ascii=False) + "\n"
        for asof, subthemes in rows)


def _ths_membership() -> dict:
    return {
        "version": THS_DOC_DATE, "seed_date": CN_SEED,
        "baskets": {
            f"thsc{KNOWN_CODE}": {
                "name": "Test Concept", "name_zh": "测试概念", "created": CN_SEED,
                "etf_proxy": None, "ths_concept": "测试概念",
                "members": [
                    {"ticker": "600001.SS", "added": CN_SEED, "removed": None},
                    {"ticker": "600002.SS", "added": CN_SEED, "removed": None},
                    {"ticker": "600003.SS", "added": CN_SEED, "removed": None},
                    {"ticker": "600004.SS", "added": CN_SEED, "removed": None},
                ],
            },
        },
    }


def _crosswalk() -> dict:
    return {"version": 3, "date": XWALK_DATE, "themes": [{
        "id": "solar", "name_en": "Solar", "name_zh": "太阳能", "foresight_id": "solar",
        "basket_ids": [], "cn_basket_ids": [], "subsector_keys": [],
        "citrini_basket_ids": [], "theme_node_id": "theme:solar",
        "ths_concept_ids": [KNOWN_CODE], "note": "fixture",
    }]}


@pytest.fixture
def world(tmp_path, monkeypatch):
    """A miniature repo: a data dir, a seed beside it, a crosswalk, an empty breaks table.

    The identity-break table is stubbed EMPTY by default so a future ratified break in the
    committed config cannot silently change what these tests assert; test E opts back into
    the real one deliberately.
    """
    root = tmp_path / "repo"
    data = root / "data"
    _write(root / local_sources.SEED_TREE_FILE, _seed_doc({"aicompute": ["AAA", "BBB"]}))
    _write(data / "baskets_china_ths" / "membership.json", _ths_membership())
    pd.DataFrame([
        {"snapshot_date": THS_DOC_DATE, "basket_id": f"thsc{KNOWN_CODE}",
         "ticker": ticker, "source_shape": "membership"}
        for ticker in ("600001.SS", "600002.SS", "600003.SS", "600004.SS")
    ]).to_parquet(data / "baskets_china_ths" / "membership_history.parquet",
                  index=False)
    _write(data / "baskets_china_ths" / "concept_map.json",
           {"asof": CMAP_ASOF, "map": {"测试概念": KNOWN_CODE, "无篮概念": UNSEEDED_CODE}})
    xwalk = root / "theme_crosswalk.yml"
    xwalk.write_text(yaml.safe_dump(_crosswalk(), allow_unicode=True, sort_keys=False),
                     encoding="utf-8")
    monkeypatch.setattr(identity, "load_breaks", lambda *a, **k: {})
    monkeypatch.setattr(config, "data_dir", lambda: data)
    return {"root": root, "data": data, "xwalk": xwalk}


def _build(world, *, era="reconstruction", belief_time=BUILD_DAY, **kw):
    ths_history = kw.pop("ths_history", None)
    if ths_history is None:
        ths_history = pd.read_parquet(
            world["data"] / "baskets_china_ths" / "membership_history.parquet")
    return materialize.build(era=era, belief_time=belief_time, computed_at=STAMP,
                             data_dir=world["data"], crosswalk_path=world["xwalk"],
                             ths_history=ths_history, **kw)


def _set_tree(world, seed: dict[str, list[str]] | None = None,
              history: list[tuple[str, dict[str, list[str]]]] | None = None,
              *, names: dict[str, str] | None = None, asof: str = SEED_ASOF) -> None:
    if seed is not None:
        doc = _seed_doc(seed, asof=asof)
        if names:
            for sub in doc["themes"][0]["subsectors"]:
                sub["name"] = names.get(sub["key"], sub["name"])
        _write(world["root"] / local_sources.SEED_TREE_FILE, doc)
    hist = world["data"] / "themes_heatmap" / "tree_history.jsonl"
    hist.parent.mkdir(parents=True, exist_ok=True)
    hist.write_text(_history(history or []), encoding="utf-8")


def _member_edges(view, dst_prefix="ltheme:finviz:"):
    return [e for e in view.edges
            if e["type"] == "MEMBER_OF" and e["dst"].startswith(dst_prefix)]


def _price_store(world, symbols, *, sub="baskets/ohlcv") -> None:
    d = world["data"] / sub
    d.mkdir(parents=True, exist_ok=True)
    for sym in symbols:
        pd.DataFrame({"Close": [1.0, 2.0]}).to_parquet(d / f"{sym}.parquet", index=False)


# ---------------------------------------------------------------------------
# D — one membership closes, the others do not
# ---------------------------------------------------------------------------

def test_D_a_member_leaving_one_subtheme_closes_exactly_that_edge(world):
    """The live shape: 26 members left one subtheme each in the 2026-08-14 vintage while
    staying in others. A plane keyed on the ticker rather than (subtheme, ticker) would
    close every membership that name has."""
    _set_tree(world,
              {"aicompute": ["AAA", "BBB"], "aicloud": ["AAA", "CCC"]},
              [(V2_ASOF, {"aicompute": ["BBB"], "aicloud": ["AAA", "CCC"]})])
    view = _build(world)
    closed = [e for e in _member_edges(view) if e["valid_to"]]
    assert len(closed) == 1
    assert closed[0]["src"] == "co:us:AAA"
    assert closed[0]["dst"] == "ltheme:finviz:aicompute"
    assert closed[0]["valid_to"] == V2_ASOF, "closes at the first vintage seen WITHOUT it"
    assert closed[0]["valid_from"] == SEED_ASOF

    survivor = next(e for e in _member_edges(view)
                    if e["src"] == "co:us:AAA" and e["dst"] == "ltheme:finviz:aicloud")
    assert survivor["valid_to"] is None
    # The closing row cites the vintage that observed the absence — a closure dated by
    # the observation that produced it, not by an assumption.
    assert len(closed[0]["evidence_refs"]) == 2


def test_D_a_closed_membership_still_resolves_and_the_guard_stays_green(world, tmp_path):
    _set_tree(world, {"aicompute": ["AAA", "BBB"]},
              [(V2_ASOF, {"aicompute": ["BBB"]})])
    view = _build(world)
    root = _materialise(tmp_path / "store_d", view)
    breaches, _ = guard.audit(root, tmp_path / "no_breaks.yml")
    assert breaches == []
    latest = _latest_belief(root)
    assert any(_is_set(r["valid_to"]) for r in latest), "the closure must be findable"


# ---------------------------------------------------------------------------
# E — a ratified identity break, using the REAL committed rows
# ---------------------------------------------------------------------------

def test_E_a_ratified_identity_break_mints_the_epoch_it_ratified(world, monkeypatch):
    """ABX and GOLD are real ratified rows (2026-08-14, both retired Barrick symbols
    reused). The tree is a fixture; the BREAK TABLE is the committed one, because the
    point of the test is that the plane obeys ratifications it did not author."""
    monkeypatch.setattr(identity, "load_breaks",
                        lambda *a, **k: identity._load_breaks(  # noqa: SLF001
                            str(ROOT / identity.BREAKS_FILE)))
    real = identity.load_breaks()
    assert ("us", "ABX") in real and ("us", "GOLD") in real, (
        "fixture premise gone: the committed break rows are what this test rides on")

    _set_tree(world, {"goldminers": ["ABX", "GOLD", "AAA"]})
    view = _build(world)
    minted = {n["node_id"]: n for n in view.nodes if n["kind"] == "company"}
    assert "co:us:ABX#2" in minted and "co:us:GOLD#2" in minted
    assert minted["co:us:ABX#2"]["identity_epoch"] == 2
    assert "co:us:ABX" not in minted, "epoch 1 must not be minted beside its own break"
    assert minted["co:us:AAA"]["identity_epoch"] == 1
    assert {e["src"] for e in _member_edges(view)} == {
        "co:us:ABX#2", "co:us:GOLD#2", "co:us:AAA"}


def test_E_an_unratified_epoch_cannot_be_invented(world):
    """With the break table empty, the same symbols mint at epoch 1. A builder may not
    decide on its own that two listings are different companies."""
    _set_tree(world, {"goldminers": ["ABX", "GOLD"]})
    view = _build(world)
    assert {n["node_id"] for n in view.nodes
            if n["kind"] == "company" and n["market_scope"] == "us"} == {
        "co:us:ABX", "co:us:GOLD"}


# ---------------------------------------------------------------------------
# F — the SNDK class: one name, many subthemes
# ---------------------------------------------------------------------------

def test_F_a_name_in_five_subthemes_keeps_five_memberships(world):
    keys = ["aicompute", "aicloud", "aidata", "aimodels", "hardwarestorage"]
    _set_tree(world, {k: ["SNDK", "AAA"] for k in keys})
    view = _build(world)
    sndk = [e for e in _member_edges(view) if e["src"] == "co:us:SNDK"]
    assert len(sndk) == 5
    assert {e["dst"] for e in sndk} == {f"ltheme:finviz:{k}" for k in keys}
    assert all(e["valid_to"] is None for e in sndk)
    # One company node, five edges — never five variant twins.
    assert len([n for n in view.nodes if n["node_id"].startswith("co:us:SNDK")]) == 1


def test_F_a_dot_dash_variant_resolves_to_the_existing_node_not_a_twin(world):
    """The vendor writes BRK-B where the store may hold BRK.B. Two spellings of one
    listing would split its memberships in half, invisibly."""
    doc = {"version": "2026-08-01", "seed_date": "2023-05-09", "baskets": {"mega": {
        "name": "Mega", "created": "2023-05-09",
        "members": [{"ticker": "BRK.B", "added": "2023-05-09", "removed": None}]}}}
    _write(world["data"] / "baskets" / "membership.json", doc)
    _set_tree(world, {"aicompute": ["BRK-B"]})
    view = _build(world)
    companies = {n["node_id"] for n in view.nodes if n["kind"] == "company"}
    assert "co:us:BRK.B" in companies
    assert "co:us:BRK-B" not in companies, "a variant twin splits one company in two"
    assert {e["src"] for e in _member_edges(view)} == {"co:us:BRK.B"}
    assert view.local_plane["finviz"]["company_resolution"][
        "resolved_dot_dash_variant"] == 1


# ---------------------------------------------------------------------------
# G / H — null canonical mapping is the lawful steady state
# ---------------------------------------------------------------------------

def test_G_a_finviz_node_with_no_canonical_mapping_survives_guard_green(world, tmp_path):
    _set_tree(world, {"aicompute": ["AAA", "BBB"]})
    view = _build(world)
    assert not [e for e in view.edges
                if e["src"].startswith("ltheme:finviz:")], (
        "the Finviz plane mints ZERO ltheme→theme edges — that is the structural proof "
        "that no company→canonical composition path exists through it")
    assert [n for n in view.nodes if n["node_id"] == "ltheme:finviz:aicompute"]
    assert len(_member_edges(view)) == 2
    breaches, _ = guard.audit(_materialise(tmp_path / "store_g", view),
                              tmp_path / "no_breaks.yml")
    assert breaches == []


def test_H_an_unmapped_ths_concept_survives_guard_green(world, tmp_path):
    _set_tree(world, {"aicompute": ["AAA"]})
    view = _build(world)
    unmapped = f"ltheme:ths:{UNSEEDED_CODE}"
    assert [n for n in view.nodes if n["node_id"] == unmapped]
    assert not [e for e in view.edges if e["src"] == unmapped]
    breaches, _ = guard.audit(_materialise(tmp_path / "store_h", view),
                              tmp_path / "no_breaks.yml")
    assert breaches == []


# ---------------------------------------------------------------------------
# I — capability lives in the side-car, never on the node
# ---------------------------------------------------------------------------

def test_I_an_unseeded_concept_is_semantic_only_in_the_sidecar(world):
    _set_tree(world, {"aicompute": ["AAA"]})
    view = _build(world)
    unseeded = f"ltheme:ths:{UNSEEDED_CODE}"
    node = next(n for n in view.nodes if n["node_id"] == unseeded)
    assert set(node) == set(store.NODE_COLUMNS)
    assert "capability" not in node, "capability is a side-car, never a node column"
    assert node["status"] == "canonical"

    row = next(r for r in view.capability if r["node_id"] == unseeded)
    assert row["capability"] == "semantic_only"
    assert "0 live members" in row["capability_basis"]
    assert "capability.v1" in row["capability_basis"]


def test_I_four_members_with_no_price_substrate_are_semantic_only(world):
    """capability.v1 counts members that RESOLVE TO A PRICE FILE, not members. Four
    unpriced names are four names, not a measurable aggregate."""
    _set_tree(world, {"aicompute": ["AAA"]})
    view = _build(world)
    seeded = f"ltheme:ths:{KNOWN_CODE}"
    row = next(r for r in view.capability if r["node_id"] == seeded)
    assert row["capability"] == "semantic_only"
    assert "0/4" in row["capability_basis"]
    assert "basket join" in row["capability_basis"], (
        "the basis must say WHICH membership path answered — a basket join and a direct "
        "source claim are different facts")


def test_capability_re_derives_upward_when_the_substrate_improves(world):
    """The anti-ratchet (§9.3). Same graph, better price coverage, second build: the
    verdict moves UP. On a write-once node column it could never move at all."""
    _set_tree(world, {"aicompute": ["AAA", "BBB", "CCC"]})
    first = _build(world)
    node = "ltheme:finviz:aicompute"
    assert next(r for r in first.capability
                if r["node_id"] == node)["capability"] == "semantic_only"

    _price_store(world, ["AAA", "BBB", "CCC"])
    second = _build(world, belief_time="2026-08-21")
    row = next(r for r in second.capability if r["node_id"] == node)
    assert row["capability"] == "measurement_candidate"
    assert "3/3" in row["capability_basis"]
    assert "data/baskets/ohlcv/" in row["capability_basis"], "the basis names the substrate"
    # And the two derivations coexist in the side-car, newest wins in the view.
    assert not [r for r in second.capability if r["capability"] == "measurable"], (
        "measurable is W3B's verdict; W3A may not mint it by classifying")


def test_capability_needs_three_not_two(world):
    """The definitional minimum is arithmetic: two names are a pair, not a cross-section.
    A boundary test, because an off-by-one here is invisible in aggregate."""
    _set_tree(world, {"aicompute": ["AAA", "BBB", "CCC"]})
    _price_store(world, ["AAA", "BBB"])
    view = _build(world)
    row = next(r for r in view.capability if r["node_id"] == "ltheme:finviz:aicompute")
    assert row["capability"] == "semantic_only"
    assert "2/3" in row["capability_basis"]


def test_the_cn_substrate_path_is_the_one_the_beta_module_consumes(world):
    """§9.10 asked for the CN store to be VERIFIED, not assumed. engine/cn_global_beta is
    a pure compute module — it reads no store at all; its caller
    scripts/c1_cn_global_beta.py::_panel() reads the panel named here. Recorded in code so
    the next wave inherits the finding rather than re-deriving it."""
    assert capability.CN_SUBSTRATE_PANEL == "china_search/closes.parquet"
    assert "c1_cn_global_beta" in capability.CN_SUBSTRATE_OWNER
    panel = ROOT / "data" / capability.CN_SUBSTRATE_PANEL
    if not panel.exists():
        pytest.skip("CN panel not materialised in this checkout")
    import pyarrow.parquet as pq

    names = pq.ParquetFile(panel).schema.names
    assert any(str(c).endswith((".SS", ".SZ")) for c in names), (
        "the panel's columns are A-share symbols — the join key capability.v1 uses")


def test_a_cn_concept_resolves_members_through_the_panel(world):
    """CN members resolve against the wide panel's COLUMNS, not per-ticker files."""
    _set_tree(world, {"aicompute": ["AAA"]})
    panel_dir = world["data"] / "china_search"
    panel_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({sym: [1.0, 2.0] for sym in
                  ("600001.SS", "600002.SS", "600003.SS")}).to_parquet(
        panel_dir / "closes.parquet", index=False)
    view = _build(world)
    row = next(r for r in view.capability if r["node_id"] == f"ltheme:ths:{KNOWN_CODE}")
    assert row["capability"] == "measurement_candidate"
    assert "3/4" in row["capability_basis"]
    assert "china_search/closes.parquet" in row["capability_basis"]


# ---------------------------------------------------------------------------
# J — corroboration coexists, nothing nets
# ---------------------------------------------------------------------------

def test_J_a_contradicting_external_classification_coexists_and_nets_nothing(world,
                                                                            tmp_path):
    """A provider saying "not in this theme" does not delete a membership. Both rows
    survive, the edge keeps resolving, and a consumer that wants one answer has to say
    which receipt it trusts."""
    _set_tree(world, {"aicompute": ["AAA"]})
    view = _build(world)
    counter = {
        "evidence_id": "ev:externalcounter1", "kind": "external_classification",
        "published_at": "2026-08-19", "effective_at": None,
        "source_ref": "fixture://provider/classification.json",
        "licensing_internal_ok": True, "licensing_display_ok": False,
        "licensing_redistribution_ok": False, "retention": None, "computed_at": STAMP,
        "provider": "fixture_provider", "claim_type": "membership",
    }
    root = _materialise(tmp_path / "store_j", view, extra_evidence=[counter])
    breaches, _ = guard.audit(root, tmp_path / "no_breaks.yml")
    assert breaches == []

    evidence = pd.read_parquet(root / "evidence.parquet")
    assert len(evidence[evidence["kind"] == "external_classification"]) == 1
    membership = next(e for e in _member_edges(view))
    assert membership["valid_to"] is None, "a counter-claim closes nothing"
    assert "ev:externalcounter1" not in membership["evidence_refs"]

    schema = json.loads((ROOT / "contracts" / "theme_graph" /
                         "evidence.v1.schema.json").read_text(encoding="utf-8"))
    import jsonschema

    jsonschema.validate(counter, schema)


def test_W3A_mints_zero_external_classification_rows(world):
    """The class ships EMPTY: the contract exists so the first external row cannot arrive
    without one, not because anything ingested a provider this wave."""
    _set_tree(world, {"aicompute": ["AAA"]})
    view = _build(world)
    assert not [e for e in view.evidence if e["kind"] == "external_classification"]
    assert all(e["provider"] is None and e["claim_type"] is None for e in view.evidence)


# ---------------------------------------------------------------------------
# K — as-known-at(T)
# ---------------------------------------------------------------------------

def test_K_as_known_at_T_excludes_a_membership_learned_at_T_plus_5(world, tmp_path):
    """Bitemporality is only real if the belief filter removes later knowledge. The
    membership is VALID from the vintage date; it was BELIEVED five days after T, and an
    as-of-T answer must not see it."""
    _set_tree(world, {"aicompute": ["AAA"]})
    early = _build(world, belief_time="2026-08-15")
    _set_tree(world, {"aicompute": ["AAA", "LATE"]})
    late = _build(world, belief_time="2026-08-20")

    root = _materialise(tmp_path / "store_k", early)
    all_rows = pd.concat([pd.read_parquet(root / "edges.parquet"),
                          pd.DataFrame(late.edges).reindex(
                              columns=list(store.EDGE_COLUMNS))], ignore_index=True)
    all_rows.to_parquet(root / "edges.parquet", index=False)

    T = "2026-08-15"
    as_known = all_rows[all_rows["belief_time"] <= T]
    assert not (as_known["src"] == "co:us:LATE").any(), (
        "a membership learned at T+5 must be invisible to an as-known-at(T) read")
    assert (all_rows["src"] == "co:us:LATE").any(), "…and present without the filter"
    # The later row's valid_from predates T: validity and belief are different clocks,
    # which is the entire point of storing both.
    late_row = all_rows[all_rows["src"] == "co:us:LATE"].iloc[0]
    assert late_row["valid_from"] <= T < late_row["belief_time"]


# ---------------------------------------------------------------------------
# L — the rights gate
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("cls", ["unresolved", "internal_only"])
def test_L_the_rights_gate_refuses_a_family_that_may_not_be_emitted(tmp_path, cls):
    reg = tmp_path / "sources.yml"
    reg.write_text(yaml.safe_dump({"version": 1, "families": {
        "vendor_x": {"rights_class": cls, "auth_class": "keyless_public"}}}),
        encoding="utf-8")
    with pytest.raises(rights.RightsRefusal, match="public emission refused"):
        rights.assert_public_emission_allowed("vendor_x", path=reg)
    assert rights.emission_allowed("vendor_x", path=reg) is False
    # …and the derived mint-time booleans say the same thing.
    assert rights.licensing_for_family("vendor_x", path=reg) == (True, False, False)


@pytest.mark.parametrize("cls,auth,expected", [
    ("derived_display_ok", "keyless_public", (True, True, False)),
    ("direct_display_ok", "house", (True, True, True)),
])
def test_L_the_rights_gate_passes_the_display_classes(tmp_path, cls, auth, expected):
    reg = tmp_path / "sources.yml"
    reg.write_text(yaml.safe_dump({"version": 1, "families": {
        "vendor_y": {"rights_class": cls, "auth_class": auth}}}), encoding="utf-8")
    rights.assert_public_emission_allowed("vendor_y", path=reg)      # must not raise
    assert rights.licensing_for_family("vendor_y", path=reg) == expected


def test_L_an_unregistered_family_fails_closed(tmp_path):
    reg = tmp_path / "sources.yml"
    reg.write_text(yaml.safe_dump({"version": 1, "families": {}}), encoding="utf-8")
    with pytest.raises(rights.RightsRefusal, match="no row in"):
        rights.rights_class("nobody_wrote_this_down", path=reg)
    with pytest.raises(rights.RightsRefusal):
        rights.assert_public_emission_allowed("nobody_wrote_this_down", path=reg)


def test_L_both_live_vendor_families_are_registered_and_refuse_today(world):
    """The live posture, read from the committed registry: both vendor families exist as
    ROWS (so nothing fails closed by accident) and both refuse emission while unresolved.
    Asserted through the gate, not against a hard-coded class, so an operator resolving a
    family updates one file and not this test."""
    for family in ("finviz_themes", "ths_concepts"):
        cls = rights.rights_class(family)
        assert cls in rights.RIGHTS_CLASSES
        assert rights.emission_allowed(family) == (cls in rights.EMISSION_OK)
    assert "mastermind_curated" in rights.known_families()


def test_L_the_guard_fails_closed_on_an_unregistered_source_family(world, tmp_path):
    _set_tree(world, {"aicompute": ["AAA"]})
    view = _build(world)
    nodes = [dict(n) for n in view.nodes]
    target = next(n for n in nodes if n["node_id"] == "ltheme:finviz:aicompute")
    meta = json.loads(target["source_meta"])
    meta["rights_family"] = "family_nobody_reviewed"
    target["source_meta"] = json.dumps(meta, ensure_ascii=False, sort_keys=True)
    root = _materialise(tmp_path / "store_l", view, nodes=nodes)
    breaches, _ = guard.audit(root, tmp_path / "no_breaks.yml")
    assert any("family_nobody_reviewed" in b and "fails CLOSED" in b for b in breaches)


def test_the_guard_refuses_a_basket_id_in_the_finviz_namespace(world, tmp_path):
    """F18 closed structurally: the suite exists for company identity only."""
    _set_tree(world, {"aicompute": ["AAA"]})
    view = _build(world)
    nodes = [dict(n) for n in view.nodes]
    nodes.append({**nodes[0], "node_id": "basket:finviz_themes:aicompute",
                  "kind": "basket", "source_meta": None})
    root = _materialise(tmp_path / "store_ns", view, nodes=nodes)
    breaches, _ = guard.audit(root, tmp_path / "no_breaks.yml")
    assert any("finviz_themes namespace" in b for b in breaches)


def test_a_mint_time_licensing_snapshot_that_disagrees_only_warns(world, tmp_path):
    """History is a record, not a mistake to be edited: an append-only row minted under
    an older rights class produces a NOTICE naming it, never a breach."""
    _set_tree(world, {"aicompute": ["AAA"]})
    view = _build(world)
    evidence = [dict(e) for e in view.evidence]
    stale = next(e for e in evidence
                 if str(e["source_ref"]).startswith("finviz_themes/"))
    stale["licensing_display_ok"] = True     # what LICENSE_VENDOR used to mint
    root = _materialise(tmp_path / "store_rights_warn", view, evidence=evidence)
    breaches, notices = guard.audit(root, tmp_path / "no_breaks.yml")
    assert breaches == []
    assert any("mint-time licensing" in n for n in notices)


# ---------------------------------------------------------------------------
# M — the synapse authority pin
# ---------------------------------------------------------------------------

def test_M_all_four_gmi_synapse_entries_carry_six_false_authority_booleans():
    reg = yaml.safe_load((ROOT / "config" / "synapse.yml").read_text(encoding="utf-8"))
    entries = ["theme-graph-nodes", "theme-graph-edges", "theme-graph-evidence",
               "theme-graph-capability"]
    for name in entries:
        art = reg["artifacts"][name]
        assert art["owner_program"] == "gmi-theme-graph"
        assert art["tier"] == "display"
        assert art["weights"] == "none"
        assert art["scored_path_surfaces"] == []
        authority = art["authority"]
        assert set(authority) == {"can_rank", "can_size", "can_gate",
                                  "can_originate_signal", "can_add_candidates",
                                  "can_escalate"}
        for key, value in authority.items():
            assert value is False, f"{name}.{key} is not literal false"


def test_M_the_capability_sidecar_is_registered_with_its_contract():
    reg = yaml.safe_load((ROOT / "config" / "synapse.yml").read_text(encoding="utf-8"))
    art = reg["artifacts"]["theme-graph-capability"]
    assert art["path"] == "data/theme_graph/capability.parquet"
    assert art["producer"] == "scripts/build_theme_graph.py"
    assert art["schema"] == "theme_graph.capability.v1"
    assert (ROOT / "contracts" / "theme_graph" / "capability.v1.schema.json").exists()


# ---------------------------------------------------------------------------
# The vintage ladder
# ---------------------------------------------------------------------------

def test_adjacent_identical_vintages_dedupe_but_a_revert_keeps_all_three(world):
    """A→B→A. Collapsing every identical vintage would erase the revert into one
    unbroken interval — precisely the history the ladder exists to keep."""
    _set_tree(world, {"aicompute": ["AAA", "BBB"]},
              [(V2_ASOF, {"aicompute": ["AAA"]}),
               (V3_ASOF, {"aicompute": ["AAA", "BBB"]})])
    view = _build(world)
    assert view.local_plane["finviz"]["vintages"] == [SEED_ASOF, V2_ASOF, V3_ASOF]

    bbb = sorted([e for e in _member_edges(view) if e["src"] == "co:us:BBB"],
                 key=lambda e: e["valid_from"])
    assert len(bbb) == 2, "closure and re-open are two intervals, not one edge edited"
    assert (bbb[0]["valid_from"], bbb[0]["valid_to"]) == (SEED_ASOF, V2_ASOF)
    assert (bbb[1]["valid_from"], bbb[1]["valid_to"]) == (V3_ASOF, None)
    assert bbb[0]["edge_id"] != bbb[1]["edge_id"]


def test_an_adjacent_identical_vintage_is_dropped(world):
    """The live case: the 2026-07-05 tape row is byte-identical to the 2026-06-27 seed,
    so the ladder holds ONE vintage and every membership opens at the seed date."""
    _set_tree(world, {"aicompute": ["AAA"]},
              [("2026-07-05", {"aicompute": ["AAA"]})])
    view = _build(world)
    plane = view.local_plane["finviz"]
    assert plane["vintages"] == [SEED_ASOF]
    assert plane["dropped_adjacent_duplicates"] == ["2026-07-05"]
    assert {e["valid_from"] for e in _member_edges(view)} == {SEED_ASOF}


def test_a_ladder_orders_by_asof_not_by_file_order(world):
    """The tape is appended to; nothing guarantees it is sorted. An out-of-order ladder
    would date every interval by whichever line happened to come first."""
    _set_tree(world, {"aicompute": ["AAA"]},
              [(V3_ASOF, {"aicompute": ["AAA", "CCC"]}),
               (V2_ASOF, {"aicompute": ["AAA", "BBB"]})])
    view = _build(world)
    assert view.local_plane["finviz"]["vintages"] == [SEED_ASOF, V2_ASOF, V3_ASOF]
    bbb = next(e for e in _member_edges(view) if e["src"] == "co:us:BBB")
    assert (bbb["valid_from"], bbb["valid_to"]) == (V2_ASOF, V3_ASOF)


def test_a_vintage_older_than_the_build_is_reconstruction_not_observation(world):
    """era says how the row was PRODUCED. A seven-week-old vintage ingested tonight is
    reconstructed history whatever mode the run is in."""
    _set_tree(world, {"aicompute": ["AAA"]})
    view = _build(world, era="observed")
    assert {e["era"] for e in _member_edges(view)} == {"reconstruction"}
    same_day = _build(world, era="observed", belief_time=SEED_ASOF)
    assert {e["era"] for e in _member_edges(same_day)} == {"observed"}


def test_the_labels_are_mint_time_snapshots(world):
    """Node rows are keep-first, so a vendor rename changes no bytes. Test C's original
    'label update only' phrasing is impossible by construction — this asserts what
    actually happens instead."""
    _set_tree(world, {"aicompute": ["AAA"]}, names={"aicompute": "Compute"})
    first = _build(world)
    node = next(n for n in first.nodes if n["node_id"] == "ltheme:finviz:aicompute")
    assert node["name_en"] == "Compute"
    assert json.loads(node["source_meta"])["source_label"] == "Compute"

    _set_tree(world, {"aicompute": ["AAA"]}, names={"aicompute": "Compute & Silicon"})
    second = _build(world)
    renamed = next(n for n in second.nodes if n["node_id"] == "ltheme:finviz:aicompute")
    assert renamed["node_id"] == node["node_id"], "the id is stable across a rename"
    assert renamed["name_en"] == "Compute & Silicon", (
        "the recomputed VIEW sees the new label; the stored ROW keeps the first one — "
        "that half is asserted in the store test below")


def test_the_store_keeps_the_first_label_not_the_rename(world, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path / "store_root")
    _set_tree(world, {"aicompute": ["AAA"]}, names={"aicompute": "Compute"})
    store.write_nodes(_build(world).nodes, lane="nightly")
    _set_tree(world, {"aicompute": ["AAA"]}, names={"aicompute": "Renamed"})
    store.write_nodes(_build(world).nodes, lane="nightly")
    rows = store.read_nodes()
    row = rows[rows["node_id"] == "ltheme:finviz:aicompute"].iloc[0]
    assert row["name_en"] == "Compute", "keep-first: the graph is a join spine, not the "\
                                        "label authority"


def test_source_meta_carries_the_parent_without_minting_a_hierarchy(world):
    _set_tree(world, {"aicompute": ["AAA"]})
    view = _build(world)
    meta = json.loads(next(n for n in view.nodes
                           if n["node_id"] == "ltheme:finviz:aicompute")["source_meta"])
    assert meta["source_family"] == "finviz_themes"
    assert meta["grain"] == "finviz_subtheme"
    assert meta["rights_family"] == "finviz_themes"
    assert meta["parent_source_label"] == "Artificial Intelligence"
    # No refresh receipt in this fixture → the layer is UNKNOWN. None, never the theme's
    # enumeration ordinal — the ordinal happened to be 0 here too, which is exactly how
    # the original wrong-value bug passed this test (diff-review F1).
    assert meta["supergroup_index"] is None
    assert meta["key_aliases"] == []
    # No node for the parent theme, and no PARENT_OF edge: hierarchy is a later wave's.
    assert not [n for n in view.nodes
                if n["node_id"] == "ltheme:finviz:Artificial Intelligence"]
    assert not [e for e in view.edges if e["type"] == "PARENT_OF"]


def test_a_zh_concept_name_never_enters_an_id(world):
    _set_tree(world, {"aicompute": ["AAA"]})
    view = _build(world)
    ths = [n for n in view.nodes if n["node_id"].startswith("ltheme:ths:")]
    assert ths
    for node in ths:
        assert identity.LOCAL_THEME_ID_RE.match(node["node_id"])
        assert node["node_id"].split(":")[2].isdigit()
        assert node["name_zh"], "the zh label rides name_zh, where it belongs"
    with pytest.raises(ValueError, match="does not match"):
        identity.local_theme_node_id("ths", "测试概念")


# ---------------------------------------------------------------------------
# The join law + the two paths agreeing
# ---------------------------------------------------------------------------

def test_the_two_canonical_paths_agree_over_the_shared_crosswalk_rows(world, tmp_path):
    _set_tree(world, {"aicompute": ["AAA"]})
    view = _build(world)
    basket = f"basket:baskets_china_ths:thsc{KNOWN_CODE}"
    concept = f"ltheme:ths:{KNOWN_CODE}"
    expresses = [e for e in view.edges if e["type"] == "EXPRESSES"]
    assert {"theme:solar"} == {e["dst"] for e in expresses
                               if e["src"] == basket and e["dst"].startswith("theme:")}
    assert {"theme:solar"} == {e["dst"] for e in expresses if e["src"] == concept}
    assert {concept} == {e["dst"] for e in expresses
                         if e["src"] == basket and e["dst"].startswith("ltheme:")}
    breaches, _ = guard.audit(_materialise(tmp_path / "store_join", view),
                              tmp_path / "no_breaks.yml")
    assert breaches == []


def test_the_guard_catches_two_paths_that_disagree(world, tmp_path):
    """The negative control: a concept resolving to a different theme than the basket
    expressing it must breach, or the agreement check proves nothing."""
    _set_tree(world, {"aicompute": ["AAA"]})
    view = _build(world)
    nodes = [dict(n) for n in view.nodes]
    nodes.append({**nodes[0], "node_id": "theme:other", "kind": "theme",
                  "market_scope": "global", "source_meta": None})
    edges = [dict(e) for e in view.edges]
    concept = f"ltheme:ths:{KNOWN_CODE}"
    rogue = next(e for e in edges
                 if e["src"] == concept and e["dst"].startswith("theme:"))
    rogue["dst"] = "theme:other"
    rogue["edge_id"] = materialize.edge_id_for("EXPRESSES", concept, "theme:other",
                                               rogue["valid_from"])
    root = _materialise(tmp_path / "store_disagree", view, nodes=nodes, edges=edges)
    breaches, _ = guard.audit(root, tmp_path / "no_breaks.yml")
    assert any("vocabulary resolution" in b for b in breaches)


def test_a_mapping_that_moved_is_not_a_disagreement_with_itself(world, tmp_path):
    """The append-only trap: a crosswalk mapping that legitimately MOVED leaves both rows
    on disk. Checked against the full history, a correct history reads as a breach — so
    the agreement check runs on the latest-belief LIVE view."""
    _set_tree(world, {"aicompute": ["AAA"]})
    view = _build(world)
    nodes = [dict(n) for n in view.nodes]
    nodes.append({**nodes[0], "node_id": "theme:old", "kind": "theme",
                  "market_scope": "global", "source_meta": None})
    concept = f"ltheme:ths:{KNOWN_CODE}"
    basket = f"basket:baskets_china_ths:thsc{KNOWN_CODE}"
    edges = [dict(e) for e in view.edges]
    superseded = []
    for src in (concept, basket):
        row = dict(next(e for e in edges
                        if e["src"] == src and e["dst"].startswith("theme:")))
        row.update({"dst": "theme:old", "belief_time": "2026-01-01",
                    "valid_to": "2026-07-09",
                    "edge_id": materialize.edge_id_for("EXPRESSES", src, "theme:old",
                                                       "2026-01-01"),
                    "valid_from": "2026-01-01"})
        superseded.append(row)
    root = _materialise(tmp_path / "store_moved", view, nodes=nodes,
                        edges=[*edges, *superseded])
    breaches, _ = guard.audit(root, tmp_path / "no_breaks.yml")
    assert breaches == [], "a closed older mapping is history, not a contradiction"


def test_the_guard_refuses_an_edge_pairing_that_is_not_in_the_table(world, tmp_path):
    """A company→theme MEMBER_OF is the derived edge W1b refused. If one ever appears,
    it appears as DATA, so the guard checks the pairing rather than trusting the writer."""
    _set_tree(world, {"aicompute": ["AAA"]})
    view = _build(world)
    edges = [dict(e) for e in view.edges]
    smuggled = dict(edges[0])
    smuggled.update({"type": "MEMBER_OF", "src": "co:us:AAA", "dst": "theme:solar",
                     "edge_id": "member_of:co:us:AAA->theme:solar@2026-06-27"})
    root = _materialise(tmp_path / "store_pairing", view, edges=[*edges, smuggled])
    breaches, _ = guard.audit(root, tmp_path / "no_breaks.yml")
    assert any("not a pairing this type may carry" in b for b in breaches)


# ---------------------------------------------------------------------------
# The materializer's second shrink wall
# ---------------------------------------------------------------------------

def test_the_second_wall_refuses_a_mass_closure_without_the_flag(world):
    """A hand-edited tree never passes through the refresh contract's interlocks, so the
    write path carries its own wall."""
    _set_tree(world, {"aicompute": ["AAA", "BBB", "CCC", "DDD"]})
    stored = pd.DataFrame(_build(world).edges).reindex(columns=list(store.EDGE_COLUMNS))

    _set_tree(world, {"aicompute": ["AAA", "BBB", "CCC", "DDD"]},
              [(V2_ASOF, {"aicompute": ["AAA"]})])
    shrunk = _build(world).edges
    refusals = materialize.source_shrink_refusals(shrunk, stored)
    assert any("finviz_themes" in r for r in refusals)
    assert any("--allow-source-shrink finviz_themes" in r for r in refusals)
    assert materialize.source_shrink_refusals(
        shrunk, stored, allow={"finviz_themes"}) == []


def test_the_second_wall_lets_ordinary_churn_through(world):
    """1 of 12 closing is 8.3% — under the 10% wall (§9.2: observed genuine churn is
    ~1.1%/7wk; the wall exists for the 11.5% distributed truncation, not for churn).
    A wall that fires on normal churn gets disabled, which is worse than not having one."""
    members = [f"M{i:02d}" for i in range(12)]
    _set_tree(world, {"aicompute": members})
    stored = pd.DataFrame(_build(world).edges).reindex(columns=list(store.EDGE_COLUMNS))
    _set_tree(world, {"aicompute": members}, [(V2_ASOF, {"aicompute": members[1:]})])
    assert materialize.source_shrink_refusals(_build(world).edges, stored) == []


def test_the_second_wall_boundary_sits_at_ten_percent(world):
    """Boundary pin for MAX_SOURCE_SHRINK=0.10 (diff-review F2): 2/20 = 10.0% passes
    (strictly-greater wall), 3/20 = 15% refuses — and the 25% constant this replaced
    would have let the canonical 11.5% truncation straight through."""
    members = [f"M{i:02d}" for i in range(20)]
    _set_tree(world, {"aicompute": members})
    stored = pd.DataFrame(_build(world).edges).reindex(columns=list(store.EDGE_COLUMNS))
    _set_tree(world, {"aicompute": members}, [(V2_ASOF, {"aicompute": members[2:]})])
    assert materialize.source_shrink_refusals(_build(world).edges, stored) == []
    _set_tree(world, {"aicompute": members}, [(V2_ASOF, {"aicompute": members[3:]})])
    refusals = materialize.source_shrink_refusals(_build(world).edges, stored)
    assert len(refusals) == 1 and "finviz_themes" in refusals[0]


def test_the_second_wall_measures_per_family(world):
    """A family that is not shrinking must not be dragged into another family's refusal —
    and a family with no stored live edges cannot 'shrink' at all."""
    _set_tree(world, {"aicompute": ["AAA", "BBB", "CCC", "DDD"]})
    view = _build(world)
    stored = pd.DataFrame(view.edges).reindex(columns=list(store.EDGE_COLUMNS))
    _set_tree(world, {"aicompute": ["AAA", "BBB", "CCC", "DDD"]},
              [(V2_ASOF, {"aicompute": ["AAA"]})])
    refusals = materialize.source_shrink_refusals(_build(world).edges, stored)
    assert len(refusals) == 1 and "finviz_themes" in refusals[0]
    assert materialize.source_shrink_refusals([], stored) == []


# ---------------------------------------------------------------------------
# The probation queue
# ---------------------------------------------------------------------------

def test_the_probation_queue_is_append_only_and_ratifies_nothing(tmp_path):
    path = tmp_path / "proposals.jsonl"
    row = probation.make_proposal(
        kind="mapping", subject={"basket": "basket:baskets:solar_us",
                                 "local_theme": "ltheme:finviz:aicompute"},
        evidence={"jaccard": 0.6}, proposed_by="overlap_stats")
    assert row["status"] == "proposed" and row["ratified_by"] is None
    added, skipped = probation.append_proposals([row], path)
    assert (added, skipped) == (1, 0)
    # Re-running a proposer re-proposes nothing: the id is a hash of the SUBJECT.
    again = probation.make_proposal(
        kind="mapping", subject={"basket": "basket:baskets:solar_us",
                                 "local_theme": "ltheme:finviz:aicompute"},
        evidence={"jaccard": 0.9}, proposed_by="overlap_stats")
    assert again["proposal_id"] == row["proposal_id"]
    assert probation.append_proposals([again], path) == (0, 1)
    assert len(probation.read_proposals(path)) == 1
    assert probation.ratified(probation.read_proposals(path)) == []


def test_a_proposal_cannot_be_born_ratified(tmp_path):
    with pytest.raises(ValueError, match="unknown proposal kind"):
        probation.make_proposal(kind="promote_now", subject={}, proposed_by="coverage_gap")
    with pytest.raises(ValueError, match="unknown proposer"):
        probation.make_proposal(kind="mapping", subject={}, proposed_by="a_hunch")
    bad = probation.make_proposal(kind="mapping", subject={"x": 1},
                                  proposed_by="overlap_stats")
    bad["status"] = "ratified"
    assert any("names its author" in e for e in probation.validate(bad))
    with pytest.raises(ValueError, match="malformed"):
        probation.append_proposals([bad], tmp_path / "p.jsonl")


# ---------------------------------------------------------------------------
# Coverage-gap + overlap diagnostics
# ---------------------------------------------------------------------------

def test_coverage_gap_case_a_fires_on_the_lithium_shape(world):
    """Three names that co-occur in the question, each covered individually, sharing no
    concept with each other. A zero-membership check sees nothing here."""
    from scripts import theme_coverage_gaps as gaps

    _set_tree(world, {"aicompute": ["AAA", "SHARED"], "aicloud": ["BBB", "SHARED2"],
                      "aidata": ["CCC", "SHARED3"]})
    view = _build(world)
    nodes = pd.DataFrame(view.nodes)
    report = gaps.analyse(["co:us:AAA", "co:us:BBB", "co:us:CCC", "co:us:NOPE"],
                          nodes, view.edges, breadth_floor=100)
    case_a = report["case_a_cooccurrence"]
    assert case_a["isolated_ids"] == ["co:us:AAA", "co:us:BBB", "co:us:CCC"]
    assert case_a["pairs_sharing_a_concept"] == []
    assert case_a["zero_membership_ids"] == []
    assert report["unresolved"] == {
        "co:us:NOPE": "no company node with this id or symbol"}

    # …and a pair that DOES share a concept is not reported as a gap.
    paired = gaps.analyse(["co:us:AAA", "co:us:SHARED"], nodes, view.edges)
    assert paired["case_a_cooccurrence"]["isolated_ids"] == []
    assert paired["case_a_cooccurrence"]["pairs_sharing_a_concept"][0]["shared"] == 1


def test_coverage_gap_case_d_prints_its_floor_and_the_distribution(world):
    from scripts import theme_coverage_gaps as gaps

    _set_tree(world, {"broad": [f"T{i}" for i in range(12)], "narrow": ["T0", "NARROW"]})
    view = _build(world)
    nodes = pd.DataFrame(view.nodes)
    report = gaps.analyse(["co:us:T1", "co:us:T0"], nodes, view.edges, breadth_floor=10)
    case_d = report["case_d_breadth"]
    assert case_d["reporting_floor_members"] == 10
    assert "not a truth claim" in case_d["floor_note"]
    assert case_d["breadth_distribution"]["max_members"] == 12
    assert case_d["broad_only_ids"] == ["co:us:T1"], (
        "T0 also sits in a narrow concept, so its coverage is not broad-only")


def test_the_overlap_proposer_prints_a_null_baseline_and_mints_no_edges(world):
    from scripts import propose_basket_ltheme_relations as overlap

    def _members(symbols):
        return [{"ticker": s, "added": "2023-05-09", "removed": None} for s in symbols]

    members = [f"M{i}" for i in range(10)]
    baskets = {"twin": {"name": "Twin", "created": "2023-05-09",
                        "members": _members(members)}}
    # Four decoy baskets, so the shuffle has a real universe to draw from. With a
    # 50-name pool a random 10-name basket overlaps the 10-name concept by ~2, which is
    # the whole point: the floor's yield under the null is what says whether 0.5 means
    # anything at this size.
    for b in range(4):
        # Symbols stay inside the company-id grammar ([A-Za-z0-9.-]): an underscore is
        # refused at mint time, which would silently empty these baskets and leave the
        # shuffle with a single basket to permute against itself.
        baskets[f"other{b}"] = {
            "name": f"Other {b}", "created": "2023-05-09",
            "members": _members([f"X{b}{i}" for i in range(10)])}
    _write(world["data"] / "baskets" / "membership.json",
           {"version": "2026-08-01", "seed_date": "2023-05-09", "baskets": baskets})
    _set_tree(world, {"mirror": members, "unrelated": [f"Z{i}" for i in range(10)]})
    view = _build(world)

    report = overlap.build_report(view.edges, suite="baskets", floor=0.5, shuffles=20,
                                  seed=7)
    assert report["edges_minted"] == 0
    pair = next(p for p in report["pairs"] if p["basket"] == "basket:baskets:twin")
    assert pair["local_theme"] == "ltheme:finviz:mirror"
    assert pair["containment_of_basket"] == 1.0 and pair["jaccard"] == 1.0
    assert not [p for p in report["pairs"] if p["basket"].endswith(("other0", "other1",
                                                                    "other2", "other3"))]

    null = report["null_baseline"]
    assert null["shuffles"] == 20 and null["seed"] == 7
    assert "degenerate" in null["what_was_shuffled"]
    assert null["mean"] < report["observed_pairs"], (
        "a null that yields as much as the real grouping would say the floor is noise")
    rows = overlap.proposals_from(report)
    assert all(r["kind"] == "mapping" and r["status"] == "proposed" for r in rows)
    assert all("null_baseline" in r["evidence"] for r in rows)


# ---------------------------------------------------------------------------
# Contract conformance of everything the plane emits
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("kind", ["nodes", "edges", "evidence", "capability"])
def test_every_local_plane_row_validates_against_its_committed_contract(world, kind):
    import jsonschema

    _set_tree(world, {"aicompute": ["AAA", "BBB"]},
              [(V2_ASOF, {"aicompute": ["AAA"]})])
    view = _build(world)
    schema = json.loads((ROOT / "contracts" / "theme_graph" /
                         f"{kind}.v1.schema.json").read_text(encoding="utf-8"))
    rows = getattr(view, kind)
    assert rows, f"no {kind} emitted — a vacuous validation proves nothing"
    for row in rows:
        jsonschema.validate(row, schema)


def test_a_store_missing_the_w3a_columns_is_a_notice_not_a_breach(world, tmp_path):
    """The migration window: a store written before the additive columns existed was
    contract-valid when it was written. A guard that reds the whole fleet between a merge
    and the next nightly is a scheduled red, not a finding."""
    _set_tree(world, {"aicompute": ["AAA"]})
    view = _build(world)
    root = _materialise(tmp_path / "store_pre", view)
    for name, drop in (("nodes", ["source_meta"]), ("evidence", ["provider", "claim_type"])):
        df = pd.read_parquet(root / f"{name}.parquet").drop(columns=drop)
        df.to_parquet(root / f"{name}.parquet", index=False)
    (root / "capability.parquet").unlink()
    breaches, notices = guard.audit(root, tmp_path / "no_breaks.yml")
    assert breaches == []
    assert any("predates the W3A additive column" in n for n in notices)
    # …but a missing CORE column is still drift.
    df = pd.read_parquet(root / "edges.parquet").drop(columns=["date_provenance"])
    df.to_parquet(root / "edges.parquet", index=False)
    assert any("column set drift" in b
               for b in guard.audit(root, tmp_path / "no_breaks.yml")[0])


def test_the_guard_selftest_still_passes():
    assert guard.selftest() == 0


# ---------------------------------------------------------------------------
# Helpers that write fixture stores
# ---------------------------------------------------------------------------

def _is_set(v: object) -> bool:
    return not (v is None or (isinstance(v, float) and v != v))


def _materialise(root: Path, view, *, nodes=None, edges=None, evidence=None,
                 extra_evidence=()) -> Path:
    """Write a view to a fixture store directory. Never touches ``data/``."""
    root.mkdir(parents=True, exist_ok=True)
    (root.parent / "no_breaks.yml").write_text("breaks: []\n", encoding="utf-8")
    payload = {
        "nodes": (nodes if nodes is not None else view.nodes, store.NODE_COLUMNS),
        "edges": (edges if edges is not None else view.edges, store.EDGE_COLUMNS),
        "evidence": ([*(evidence if evidence is not None else view.evidence),
                      *extra_evidence], store.EVIDENCE_COLUMNS),
        "capability": (view.capability, store.CAPABILITY_COLUMNS),
    }
    for name, (rows, columns) in payload.items():
        pd.DataFrame(rows).reindex(columns=list(columns)).to_parquet(
            root / f"{name}.parquet", index=False)
    return root


def _latest_belief(root: Path) -> list[dict]:
    df = pd.read_parquet(root / "edges.parquet")
    ordered = df.sort_values(["edge_id", "belief_time", "computed_at"], kind="stable")
    return ordered.drop_duplicates(subset=["edge_id"], keep="last").to_dict("records")


# ---------------------------------------------------------------------------
# Supergroup layer (diff-review F1): receipts are the ONLY source; never ordinals
# ---------------------------------------------------------------------------

def _write_supergroup_receipt(world, groups: list[dict]) -> None:
    rdir = world["data"] / "themes_heatmap" / "tree_refresh_receipts"
    rdir.mkdir(parents=True, exist_ok=True)
    (rdir / "20260815T000000Z.json").write_text(
        json.dumps({"promoted": True, "supergroups": groups}), encoding="utf-8")


def test_supergroup_index_comes_from_the_receipt_never_the_theme_ordinal(world):
    """Two themes in ONE group must share an index — the theme ordinal cannot fake this.

    The original defect stamped enumerate() ordinals (40 singleton groups on the real
    tree); a one-theme fixture passed because ordinal 0 == group 0. This fixture makes
    the two values diverge: theme 'Cloud' is ordinal 1 but group 0.
    """
    tree = [
        {"theme": "Artificial Intelligence", "key": "Artificial Intelligence",
         "subsectors": [{"key": "aicompute", "name": "Compute", "description": "",
                         "members": ["AAA"]}]},
        {"theme": "Cloud", "key": "Cloud",
         "subsectors": [{"key": "cloudinfra", "name": "Infra", "description": "",
                         "members": ["BBB"]}]},
        {"theme": "Metals", "key": "Metals",
         "subsectors": [{"key": "metalsgold", "name": "Gold", "description": "",
                         "members": ["CCC"]}]},
    ]
    _write(world["root"] / local_sources.SEED_TREE_FILE,
           {"asof": SEED_ASOF, "themes": tree})
    (world["data"] / "themes_heatmap" / "tree_history.jsonl").parent.mkdir(
        parents=True, exist_ok=True)
    (world["data"] / "themes_heatmap" / "tree_history.jsonl").write_text(
        "", encoding="utf-8")
    _write_supergroup_receipt(world, [
        {"group": "1", "themes": ["Artificial Intelligence", "Cloud"]},
        {"group": "2", "themes": ["Metals"]},
    ])
    view = _build(world)
    got = {}
    for n in view.nodes:
        if str(n["node_id"]).startswith("ltheme:finviz:"):
            got[n["node_id"]] = json.loads(n["source_meta"])["supergroup_index"]
    assert got["ltheme:finviz:aicompute"] == 0
    assert got["ltheme:finviz:cloudinfra"] == 0   # ordinal 1 — the group wins
    assert got["ltheme:finviz:metalsgold"] == 1   # ordinal 2 — the group wins


def test_supergroup_absent_from_receipt_is_none_not_a_guess(world):
    _set_tree(world, {"aicompute": ["AAA"]})
    _write_supergroup_receipt(world, [{"group": "1", "themes": ["Something Else"]}])
    view = _build(world)
    meta = json.loads(next(n for n in view.nodes
                           if n["node_id"] == "ltheme:finviz:aicompute")["source_meta"])
    assert meta["supergroup_index"] is None


def test_load_supergroups_handles_missing_dir_and_torn_receipt(tmp_path):
    assert local_sources.load_supergroups(tmp_path / "nope") == {}
    rdir = tmp_path / "receipts"
    rdir.mkdir()
    (rdir / "20260101T000000Z.json").write_text("{torn", encoding="utf-8")
    assert local_sources.load_supergroups(rdir) == {}

# ---------------------------------------------------------------------------
# D2D exact ontology-neighborhood reader — graph truth + probation context
# ---------------------------------------------------------------------------

_ONTOLOGY_SCHEMA = json.loads(
    (ROOT / "contracts" / "theme_graph" / "ontology_neighborhood.v1.schema.json").read_text()
)

def _ont_node(node_id: str, kind: str, *, name: str | None = None) -> dict:
    return {
        "node_id": node_id,
        "kind": kind,
        "name_en": name,
        "name_zh": None,
        "market_scope": "global",
        "tier": "theme" if kind == "theme" else None,
        "status": "canonical",
        "merged_into": None,
        "birth_date": "2026-01-01",
        "retire_date": None,
        "identity_epoch": 1,
        "external_ids": "{}",
        "provenance": "test",
        "computed_at": "2026-01-01T00:00:00Z",
        "engine_version": "theme_graph.v1",
        "source_meta": None,
    }


def _ont_edge(
    edge_id: str,
    type_: str,
    src: str,
    dst: str,
    *,
    valid_from: str = "2026-01-01",
    valid_to: str | None = None,
    belief_time: str = "2026-01-01",
    computed_at: str = "2026-01-01T00:00:00Z",
) -> dict:
    return {
        "edge_id": edge_id,
        "type": type_,
        "src": src,
        "dst": dst,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "evidence_time": valid_from,
        "belief_time": belief_time,
        "era": "observed",
        "source_class": "curated",
        "date_provenance": "curated_changelog",
        "evidence_refs": ["ev:test"],
        "confidence_basis": "test.v1",
        "computed_at": computed_at,
        "engine_version": "theme_graph.v1",
    }


def _ont_proposal(
    proposal_id: str,
    subject: dict,
    *,
    status: str = "proposed",
    ratified_by: str | None = None,
    created: str = "2026-02-01T00:00:00Z",
    adjudicated_at: str | None = None,
) -> dict:
    return {
        "proposal_id": proposal_id,
        "kind": "mapping",
        "subject": subject,
        "evidence": {"overlap": 9},
        "evidence_refs": ["research/example.json"],
        "proposed_by": "overlap_stats",
        "created": created,
        "status": status,
        "ratified_by": ratified_by,
        "adjudicated_at": (
            adjudicated_at
            if adjudicated_at is not None
            else ("2026-02-02T00:00:00Z" if status != "proposed" else None)
        ),
        "note": "_ont_proposal only",
    }


class _OntologyStore:
    def __init__(self, *, nodes=(), edges=(), proposals=(), lifecycle=()):
        self._nodes = list(nodes)
        self._edges = list(edges)
        self._proposals = list(proposals)
        self._lifecycle = list(lifecycle)

    def read_nodes(self):
        return list(self._nodes)

    def read_edges(self):
        return list(self._edges)

    def read_proposals(self):
        return list(self._proposals)

    def read_node_lifecycle(self):
        return list(self._lifecycle)


def _ont_rights(node_id: str) -> dict | None:
    if node_id.startswith("ltheme:finviz:"):
        return {
            "family": "finviz",
            "rights_class": "internal_computation_only",
            "public_display_allowed": False,
        }
    return None


def _ont_compose(store: _OntologyStore, node_id: str, *, cutoff: str = "2026-06-01") -> dict:
    result = compose_neighborhood(
        store,
        node_id=node_id,
        asof="2026-06-01",
        knowledge_cutoff=cutoff,
        rights_resolver=_ont_rights,
    )
    jsonschema.validate(result, _ONTOLOGY_SCHEMA)
    return result


def test_ontology_belief_cutoff_is_applied_before_latest_belief_and_valid_time() -> None:
    local = "ltheme:finviz:ai"
    theme = "theme:ai_semiconductors"
    store = _OntologyStore(
        nodes=[_ont_node(local, "local_theme"), _ont_node(theme, "theme")],
        edges=[
            _ont_edge("e1", "EXPRESSES", local, theme),
            _ont_edge(
                "e1",
                "EXPRESSES",
                local,
                theme,
                valid_to="2026-05-01",
                belief_time="2026-08-01",
                computed_at="2026-08-01T00:00:00Z",
            ),
        ],
    )

    before_close_was_known = _ont_compose(store, local, cutoff="2026-07-01")
    after_close_was_known = _ont_compose(store, local, cutoff="2026-09-01")

    assert [r["edge_id"] for r in before_close_was_known["relations"]] == ["e1"]
    assert before_close_was_known["canonical_mapping"] == {
        "state": "MAPPED",
        "theme_node_ids": [theme],
    }
    assert after_close_was_known["relations"] == []
    assert after_close_was_known["canonical_mapping"] == {
        "state": "UNMAPPED",
        "theme_node_ids": [],
    }


def test_ontology_datetime_inputs_normalize_to_date_only_clocks() -> None:
    import datetime as dt

    local = "ltheme:finviz:ai"
    result = compose_neighborhood(
        _OntologyStore(nodes=[_ont_node(local, "local_theme")]),
        node_id=local,
        asof=dt.datetime(2026, 6, 1, 14, 30),
        knowledge_cutoff=dt.datetime(2026, 6, 1, 23, 59),
        rights_resolver=_ont_rights,
    )

    jsonschema.validate(result, _ONTOLOGY_SCHEMA)
    assert result["asof"] == "2026-06-01"
    assert result["knowledge_cutoff"] == "2026-06-01"


def test_ontology_proposed_mapping_is_visible_but_never_graph_truth() -> None:
    basket = "basket:baskets:utilities"
    local = "ltheme:finviz:utilities"
    store = _OntologyStore(
        nodes=[_ont_node(basket, "basket"), _ont_node(local, "local_theme")],
        proposals=[_ont_proposal("prop:1111111111111111", {"basket": basket, "local_theme": local})],
    )

    result = _ont_compose(store, local)

    assert result["availability"] == {"state": "OK", "reason": None}
    assert result["relations"] == []
    assert result["canonical_mapping"]["state"] == "UNMAPPED"
    assert result["curation"] == {
        "state": "PROPOSED",
        "proposal_ids": ["prop:1111111111111111"],
        "counts": {"proposed": 1, "ratified": 0, "rejected": 0},
    }
    assert result["proposals"][0]["truth_status"] == "PROPOSAL_ONLY"


def test_ontology_ratified_proposal_without_edge_is_explicitly_not_materialized() -> None:
    local = "ltheme:finviz:ai"
    theme = "theme:ai_semiconductors"
    store = _OntologyStore(
        nodes=[_ont_node(local, "local_theme"), _ont_node(theme, "theme")],
        proposals=[
            _ont_proposal(
                "prop:2222222222222222",
                {"local_theme": local, "canonical_theme": theme},
                status="ratified",
                ratified_by="curator:test",
            )
        ],
    )

    result = _ont_compose(store, local)

    assert result["curation"]["state"] == "RATIFIED_NOT_MATERIALIZED"
    assert result["canonical_mapping"]["state"] == "UNMAPPED"
    assert result["relations"] == []


def test_ontology_graph_mapping_is_truth_even_when_a_proposal_also_exists() -> None:
    local = "ltheme:finviz:ai"
    theme = "theme:ai_semiconductors"
    store = _OntologyStore(
        nodes=[_ont_node(local, "local_theme"), _ont_node(theme, "theme")],
        edges=[_ont_edge("e1", "EXPRESSES", local, theme)],
        proposals=[_ont_proposal("prop:3333333333333333", {"local_theme": local})],
    )

    result = _ont_compose(store, local)

    assert result["canonical_mapping"]["state"] == "MAPPED"
    assert result["relations"][0]["truth_status"] == "GRAPH_TRUTH"
    assert result["relations"][0]["rights"] == [_ont_rights(local)]
    assert result["curation"]["state"] == "PROPOSED"



def test_ontology_ratified_mapping_is_materialized_only_for_its_exact_theme_target() -> None:
    local = "ltheme:finviz:ai"
    theme = "theme:ai_semiconductors"
    other = "theme:defense_aerospace"
    store = _OntologyStore(
        nodes=[_ont_node(local, "local_theme"), _ont_node(theme, "theme"), _ont_node(other, "theme")],
        edges=[_ont_edge("e1", "EXPRESSES", local, theme)],
        proposals=[
            _ont_proposal(
                "prop:4444444444444444",
                {"local_theme": local, "canonical_theme": other},
                status="ratified",
                ratified_by="curator:test",
            )
        ],
    )

    result = _ont_compose(store, local)

    assert result["canonical_mapping"]["theme_node_ids"] == [theme]
    assert result["curation"]["state"] == "RATIFIED_NOT_MATERIALIZED"

def test_ontology_lookup_is_exact_id_only_and_never_fuzzy_matches_a_label() -> None:
    local = _ont_node("ltheme:finviz:ai", "local_theme", name="AI")
    result = _ont_compose(_OntologyStore(nodes=[local]), "AI")

    assert result["availability"] == {
        "state": "SUBJECT_NOT_FOUND",
        "reason": "exact node_id is absent",
    }
    assert result["subject"] is None
    assert result["relations"] == []


def test_ontology_relations_are_stably_ordered_by_semantics_and_ids_not_scores() -> None:
    subject = "theme:ai"
    store = _OntologyStore(
        nodes=[
            _ont_node(subject, "theme"),
            _ont_node("ltheme:finviz:z", "local_theme"),
            _ont_node("ltheme:finviz:a", "local_theme"),
        ],
        edges=[
            _ont_edge("e-z", "EXPRESSES", "ltheme:finviz:z", subject),
            _ont_edge("e-a", "EXPRESSES", "ltheme:finviz:a", subject),
        ],
    )

    result = _ont_compose(store, subject)

    assert [r["peer_node_id"] for r in result["relations"]] == [
        "ltheme:finviz:a",
        "ltheme:finviz:z",
    ]
    assert result["ordering"] == "type,direction,peer_node_id,edge_id; never score"
    assert result["canonical_mapping"] == {
        "state": "SUBJECT_IS_CANONICAL",
        "theme_node_ids": [subject],
    }


def _ont_lifecycle(
    node_id: str,
    *,
    status: str = "retired",
    retire_date: str | None = "2026-07-01",
    computed_at: str = "2026-08-01T00:00:00Z",
) -> dict:
    return {
        "schema": "gmi.node_lifecycle/v1",
        "node_id": node_id,
        "status": status,
        "retire_date": retire_date,
        "merged_into": None,
        "reason": "identity_break",
        "evidence": "test",
        "ratified_by": "curator:test",
        "computed_at": computed_at,
        "engine_version": "theme_graph.v1",
    }


def test_ontology_future_proposals_and_adjudications_obey_knowledge_cutoff() -> None:
    local = "ltheme:finviz:ai"
    theme = "theme:ai_semiconductors"
    store = _OntologyStore(
        nodes=[_ont_node(local, "local_theme"), _ont_node(theme, "theme")],
        proposals=[
            _ont_proposal(
                "prop:5555555555555555",
                {"local_theme": local, "canonical_theme": theme},
                created="2026-08-01T00:00:00Z",
            ),
            _ont_proposal(
                "prop:6666666666666666",
                {"local_theme": local, "canonical_theme": theme},
                status="ratified",
                ratified_by="curator:test",
                created="2026-01-01T00:00:00Z",
                adjudicated_at="2026-08-01T00:00:00Z",
            ),
        ],
    )

    before = _ont_compose(store, local, cutoff="2026-06-01")

    assert [row["proposal_id"] for row in before["proposals"]] == [
        "prop:6666666666666666"
    ]
    assert before["proposals"][0]["status"] == "proposed"
    assert before["proposals"][0]["ratified_by"] is None
    assert before["proposals"][0]["adjudicated_at"] is None
    assert before["proposals"][0]["note"] == store._proposals[1]["note"]
    assert before["curation"] == {
        "state": "PROPOSED",
        "proposal_ids": ["prop:6666666666666666"],
        "counts": {"proposed": 1, "ratified": 0, "rejected": 0},
    }

    after = _ont_compose(store, local, cutoff="2026-09-01")

    assert [row["proposal_id"] for row in after["proposals"]] == [
        "prop:6666666666666666",
        "prop:5555555555555555",
    ]
    decided = next(
        row for row in after["proposals"]
        if row["proposal_id"] == "prop:6666666666666666"
    )
    assert decided["status"] == "ratified"
    assert decided["ratified_by"] == "curator:test"
    assert decided["adjudicated_at"] == "2026-08-01T00:00:00Z"
    assert after["curation"]["counts"] == {
        "proposed": 1,
        "ratified": 1,
        "rejected": 0,
    }


def test_ontology_canonical_subject_requires_exact_live_mapping_relation() -> None:
    local = "ltheme:finviz:ai"
    theme = "theme:ai_semiconductors"
    store = _OntologyStore(
        nodes=[_ont_node(local, "local_theme"), _ont_node(theme, "theme")],
        proposals=[
            _ont_proposal(
                "prop:7777777777777777",
                {"local_theme": local, "canonical_theme": theme},
                status="ratified",
                ratified_by="curator:test",
            )
        ],
    )

    result = _ont_compose(store, theme)

    assert result["relations"] == []
    assert result["curation"]["state"] == "RATIFIED_NOT_MATERIALIZED"


def test_ontology_exact_live_mapping_materializes_from_both_query_sides() -> None:
    local = "ltheme:finviz:ai"
    theme = "theme:ai_semiconductors"
    store = _OntologyStore(
        nodes=[_ont_node(local, "local_theme"), _ont_node(theme, "theme")],
        edges=[_ont_edge("e-map", "EXPRESSES", local, theme)],
        proposals=[
            _ont_proposal(
                "prop:8888888888888888",
                {"local_theme": local, "canonical_theme": theme},
                status="ratified",
                ratified_by="curator:test",
            )
        ],
    )

    from_local = _ont_compose(store, local)
    from_theme = _ont_compose(store, theme)

    assert from_local["curation"]["state"] == "RATIFIED_AND_MATERIALIZED"
    assert from_theme["curation"]["state"] == "RATIFIED_AND_MATERIALIZED"


def test_repository_store_reads_raw_nodes_and_full_lifecycle(monkeypatch) -> None:
    from engine.theme_graph.ontology import RepositoryStore

    calls: list[tuple[str, bool, bool]] = []

    def fake_nodes(*, current: bool = False, strict: bool = False):
        calls.append(("nodes", current, strict))
        return []

    def fake_lifecycle(*, latest: bool = True, strict: bool = False):
        calls.append(("lifecycle", latest, strict))
        return []

    monkeypatch.setattr(store, "read_nodes", fake_nodes)
    monkeypatch.setattr(store, "read_node_lifecycle", fake_lifecycle)

    repository = RepositoryStore()
    assert repository.read_nodes() == []
    assert repository.read_node_lifecycle() == []
    assert calls == [("nodes", False, True), ("lifecycle", False, True)]


def test_ontology_subject_visibility_obeys_birth_and_knowledge_clocks() -> None:
    local = _ont_node("ltheme:finviz:ai", "local_theme")
    local["birth_date"] = "2026-07-01"
    local["computed_at"] = "2026-08-01T00:00:00Z"
    store_view = _OntologyStore(nodes=[local])

    before_birth = compose_neighborhood(
        store_view,
        node_id=local["node_id"],
        asof="2026-06-01",
        knowledge_cutoff="2026-09-01",
        rights_resolver=_ont_rights,
    )
    before_known = compose_neighborhood(
        store_view,
        node_id=local["node_id"],
        asof="2026-09-01",
        knowledge_cutoff="2026-07-01",
        rights_resolver=_ont_rights,
    )
    visible = compose_neighborhood(
        store_view,
        node_id=local["node_id"],
        asof="2026-09-01",
        knowledge_cutoff="2026-09-01",
        rights_resolver=_ont_rights,
    )
    assert before_birth["availability"]["state"] == "SUBJECT_NOT_FOUND"
    assert before_known["availability"]["state"] == "SUBJECT_NOT_FOUND"
    assert visible["availability"]["state"] == "OK"


def test_ontology_lifecycle_overlay_obeys_effective_and_knowledge_clocks() -> None:
    local = "ltheme:finviz:ai"
    theme = "theme:ai_semiconductors"
    store_view = _OntologyStore(
        nodes=[_ont_node(local, "local_theme"), _ont_node(theme, "theme")],
        edges=[_ont_edge("e-map", "EXPRESSES", local, theme)],
        lifecycle=[_ont_lifecycle(local), _ont_lifecycle(theme)],
    )

    before_effective = compose_neighborhood(
        store_view,
        node_id=local,
        asof="2026-06-01",
        knowledge_cutoff="2026-09-01",
        rights_resolver=_ont_rights,
    )
    before_known = compose_neighborhood(
        store_view,
        node_id=local,
        asof="2026-07-15",
        knowledge_cutoff="2026-07-15",
        rights_resolver=_ont_rights,
    )
    visible = compose_neighborhood(
        store_view,
        node_id=local,
        asof="2026-07-15",
        knowledge_cutoff="2026-09-01",
        rights_resolver=_ont_rights,
    )

    assert before_effective["subject"]["status"] == "canonical"
    assert before_effective["relations"][0]["peer"]["status"] == "canonical"
    assert before_known["subject"]["status"] == "canonical"
    assert before_known["relations"][0]["peer"]["status"] == "canonical"
    assert visible["subject"]["status"] == "retired"
    assert visible["relations"][0]["peer"]["status"] == "retired"


def test_probation_decision_clock_contract_is_fail_closed() -> None:
    schema = json.loads(
        (ROOT / "contracts" / "theme_graph" / "probation_proposal.v1.schema.json")
        .read_text()
    )
    proposed = probation.make_proposal(
        kind="mapping",
        subject={"basket": "basket:baskets:defense", "local_theme": "ltheme:finviz:defense"},
        proposed_by="overlap_stats",
        created="2026-01-01T00:00:00Z",
    )
    ratified = dict(
        proposed,
        status="ratified",
        ratified_by="curator:test",
    )

    assert any("adjudicated_at" in error for error in probation.validate(ratified))
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(ratified, schema)

    ratified["adjudicated_at"] = "2026-01-02T00:00:00Z"
    assert probation.validate(ratified) == []
    jsonschema.validate(ratified, schema)

    impossible = dict(proposed, adjudicated_at="2026-01-02T00:00:00Z")
    assert any("still proposed" in error for error in probation.validate(impossible))
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(impossible, schema)


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("asof,cutoff,expected", [
    ("2026-06-01", "2026-04-15", "retired"),
    ("2026-06-01", "2026-06-01", "canonical"),
    ("2026-07-01", "2026-06-01", "retired"),
    ("2026-02-01", "2026-06-01", "canonical"),
])
def test_latest_lifecycle_belief_precedes_effective_time(reverse, asof, cutoff, expected):
    """A postponed retirement must not resurrect the superseded correction."""
    local, theme = "ltheme:finviz:ai", "theme:ai_semiconductors"
    rows = [_ont_lifecycle(node, retire_date=retire, computed_at=computed)
            for node in (local, theme) for retire, computed in [
                ("2026-03-01", "2026-04-01T00:00:00Z"),
                ("2026-07-01", "2026-05-01T00:00:00Z")]]
    view = _OntologyStore(
        nodes=[_ont_node(local, "local_theme"), _ont_node(theme, "theme")],
        edges=[_ont_edge("e-map", "EXPRESSES", local, theme)],
        lifecycle=list(reversed(rows)) if reverse else rows)
    result = compose_neighborhood(view, node_id=local, asof=asof,
        knowledge_cutoff=cutoff, rights_resolver=_ont_rights)
    assert result["subject"]["status"] == expected
    assert result["relations"][0]["peer"]["status"] == expected


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("older,newer", [
    ("2026-05-01T10:00:00+02:00", "2026-05-01T09:00:00Z"),
    ("2026-05-01T09:00:00Z", "2026-05-01T09:00:00.500Z"),
])
def test_ontology_lifecycle_orders_clock_instants(reverse, older, newer):
    local, theme = "ltheme:finviz:ai", "theme:ai_semiconductors"
    rows = [_ont_lifecycle(node, retire_date=retire, computed_at=stamp)
            for node in (local, theme) for retire, stamp in [
                ("2026-03-01", older), ("2026-07-01", newer)]]
    schema = json.loads((ROOT / "contracts/theme_graph/node_lifecycle.v1.schema.json").read_text())
    for row in rows:
        jsonschema.validate(row, schema)
    view = _OntologyStore(
        nodes=[_ont_node(local, "local_theme"), _ont_node(theme, "theme")],
        edges=[_ont_edge("e-map", "EXPRESSES", local, theme)],
        lifecycle=list(reversed(rows)) if reverse else rows)
    result = compose_neighborhood(view, node_id=local, asof="2026-06-01",
        knowledge_cutoff="2026-06-01", rights_resolver=_ont_rights)
    assert result["subject"]["status"] == "canonical"
    assert result["relations"][0]["peer"]["status"] == "canonical"


@pytest.mark.parametrize("surface", ["subject", "peer", "lifecycle", "created", "adjudicated"])
@pytest.mark.parametrize("stamp", ["2026-06-01T23:30:00-02:00", "2026-06-02T01:30:00Z"])
def test_ontology_knowledge_cutoff_uses_utc_day(surface, stamp):
    local, theme = "ltheme:finviz:ai", "theme:ai_semiconductors"
    nodes = [_ont_node(local, "local_theme"), _ont_node(theme, "theme")]
    proposal = _ont_proposal("prop:aaaaaaaaaaaaaaaa", {
        "local_theme": local, "canonical_theme": theme}, created="2026-01-01T00:00:00Z")
    lifecycle = []
    if surface in {"subject", "peer"}:
        nodes[int(surface == "peer")]["computed_at"] = stamp
    elif surface == "lifecycle":
        lifecycle = [_ont_lifecycle(node, retire_date="2026-03-01", computed_at=stamp)
                     for node in (local, theme)]
    elif surface == "created":
        proposal["created"] = stamp
    else:
        proposal.update(status="ratified", ratified_by="curator:test", adjudicated_at=stamp)
    view = _OntologyStore(nodes=nodes, lifecycle=lifecycle, proposals=[proposal],
        edges=[_ont_edge("e-map", "EXPRESSES", local, theme)])
    result = compose_neighborhood(view, node_id=local, asof="2026-06-01",
        knowledge_cutoff="2026-06-01", rights_resolver=_ont_rights)
    if surface == "subject":
        assert result["availability"]["state"] == "SUBJECT_NOT_FOUND"
    elif surface == "peer":
        # A known edge survives; unavailable peer context must stay null.
        assert result["relations"][0]["peer"] is None
    elif surface == "lifecycle":
        assert result["subject"]["status"] == "canonical"
        assert result["relations"][0]["peer"]["status"] == "canonical"
    elif surface == "created":
        assert result["proposals"] == []
    else:
        assert result["proposals"][0]["status"] == "proposed"
        assert result["proposals"][0]["ratified_by"] is None
        assert result["proposals"][0]["adjudicated_at"] is None


@pytest.mark.parametrize("clock", ["2026-05-01", "2026-05-01T00:00:00"])
def test_ontology_legacy_clock_forms_remain_compatible(clock):
    local = "ltheme:finviz:ai"
    node = dict(_ont_node(local, "local_theme"), computed_at=clock)
    result = compose_neighborhood(_OntologyStore(nodes=[node]), node_id=local,
        asof="2026-06-01", knowledge_cutoff="2026-06-01", rights_resolver=_ont_rights)
    assert result["availability"]["state"] == "OK"


_REVIEW_ID = "prop:aaaaaaaaaaaaaaaa"
_REVIEW_LOCAL = "ltheme:finviz:ai"
_REVIEW_THEME = "theme:ai_semiconductors"


def _review_proposal(view, *, cutoff="2026-06-01", asof="2026-06-01", proposal_id=_REVIEW_ID):
    from engine.theme_graph import ontology
    from referencing import Registry, Resource
    composer = getattr(ontology, "compose_proposal_review", None)
    assert callable(composer), "exact-proposal review consumer is missing"
    result = composer(view, proposal_id=proposal_id, asof=asof,
                      knowledge_cutoff=cutoff, rights_resolver=_ont_rights)
    neighborhood = json.loads((ROOT / "contracts/theme_graph/ontology_neighborhood.v1.schema.json").read_text())
    schema = json.loads((ROOT / "contracts/theme_graph/ontology_proposal_review.v1.schema.json").read_text())
    registry = Registry().with_resource(neighborhood["$id"], Resource.from_contents(neighborhood))
    jsonschema.Draft202012Validator(schema, registry=registry).validate(result)
    return result


def _review_view(*, status="proposed", present=False):
    proposal = _ont_proposal(_REVIEW_ID,
        {"local_theme": _REVIEW_LOCAL, "canonical_theme": _REVIEW_THEME},
        status=status, ratified_by="curator:test" if status == "ratified" else None)
    return _OntologyStore(nodes=[_ont_node(_REVIEW_LOCAL, "local_theme"),
        _ont_node(_REVIEW_THEME, "theme")], proposals=[proposal],
        edges=[_ont_edge("exact-map", "EXPRESSES", _REVIEW_LOCAL, _REVIEW_THEME)] if present else [])


@pytest.mark.parametrize("status", ["proposed", "ratified", "rejected"])
@pytest.mark.parametrize("present", [False, True])
def test_proposal_review_separates_decision_from_exact_graph_relation(status, present):
    view = _review_view(status=status, present=present)
    before = json.dumps(view.__dict__, sort_keys=True)
    result = _review_proposal(view)
    assert result["availability"]["state"] == "OK"
    assert result["proposal"]["status"] == status
    assert result["proposal"]["truth_status"] == "PROPOSAL_ONLY"
    assert result["proposal"]["evidence"] == {"overlap": 9}
    assert result["relation"]["state"] == ("RELATION_PRESENT" if present else "RELATION_ABSENT")
    assert result["relation"]["edge_ids"] == (["exact-map"] if present else [])
    assert [x["node_id"] for x in result["endpoints"]] == [_REVIEW_LOCAL, _REVIEW_THEME]
    assert result["authority_ceiling"] == "research_internal_only"
    assert json.dumps(view.__dict__, sort_keys=True) == before


def test_proposal_review_missing_and_future_are_indistinguishable():
    missing = _review_proposal(_OntologyStore())
    view = _review_view()
    view._proposals[0]["created"] = "2026-06-01T23:30:00-02:00"
    assert _review_proposal(view) == missing
    assert missing["availability"]["state"] == "PROPOSAL_NOT_FOUND"
    assert missing["proposal"] is None
    assert missing["endpoints"] == []


@pytest.mark.parametrize("status", ["ratified", "rejected"])
def test_proposal_review_hides_later_decision(status):
    view = _review_view(status=status)
    view._proposals[0]["adjudicated_at"] = "2026-06-01T23:30:00-02:00"
    result = _review_proposal(view)
    assert result["proposal"]["status"] == "proposed"
    assert result["proposal"]["ratified_by"] is None
    assert result["proposal"]["adjudicated_at"] is None
    assert result["proposal"]["note"] == view._proposals[0]["note"]


def test_proposal_review_duplicate_visible_identity_fails_closed():
    view = _review_view()
    view._proposals.append(dict(view._proposals[0]))
    with pytest.raises(ValueError, match="duplicate"):
        _review_proposal(view)


@pytest.mark.parametrize("subject", [
    {"local_theme": _REVIEW_LOCAL, "canonical_theme": _REVIEW_THEME, "basket": "basket:baskets:ai"},
    {"local_theme": "AI", "canonical_theme": _REVIEW_THEME},
    {"unowned_label": "AI"},
])
def test_proposal_review_unsupported_subject_is_not_inferred(subject):
    view = _review_view(); view._proposals[0]["subject"] = subject
    result = _review_proposal(view)
    assert result["relation"]["state"] == "UNSUPPORTED_SUBJECT"
    assert result["endpoints"] == []


@pytest.mark.parametrize("mode", ["target_missing", "target_future", "edge_future", "edge_closed", "wrong_type", "wrong_target"])
def test_proposal_review_requires_both_visible_endpoints_and_exact_live_edge(mode):
    view = _review_view(present=True)
    if mode == "target_missing": view._nodes.pop()
    elif mode == "target_future": view._nodes[-1]["computed_at"] = "2026-07-01T00:00:00Z"
    elif mode == "edge_future": view._edges[0]["belief_time"] = "2026-07-01"
    elif mode == "edge_closed": view._edges[0]["valid_to"] = "2026-05-01"
    elif mode == "wrong_type": view._edges[0]["type"] = "MEMBER_OF"
    else: view._edges[0]["dst"] = "theme:another"
    result = _review_proposal(view)
    expected = "ENDPOINT_UNAVAILABLE" if mode.startswith("target_") else "RELATION_ABSENT"
    assert result["relation"]["state"] == expected
    assert result["relation"]["edge_ids"] == []


def test_proposal_review_basket_mapping_keeps_source_rights():
    basket = "basket:baskets:ai"
    view = _review_view()
    view._proposals[0]["subject"] = {"basket": basket, "local_theme": _REVIEW_LOCAL}
    view._nodes.append(_ont_node(basket, "basket"))
    view._edges = [_ont_edge("basket-map", "EXPRESSES", basket, _REVIEW_LOCAL)]
    result = _review_proposal(view)
    assert result["relation"]["source_node_id"] == basket
    assert result["relation"]["target_node_id"] == _REVIEW_LOCAL
    assert result["relation"]["edge_ids"] == ["basket-map"]
    assert result["endpoints"][0]["relations"][0]["rights"][0]["public_display_allowed"] is False


@pytest.mark.parametrize("bad_id", ["AI", " prop:aaaaaaaaaaaaaaaa", "prop:AAAAAAAAAAAAAAAA"])
def test_proposal_review_requires_exact_proposal_identity(bad_id):
    with pytest.raises(ValueError, match="proposal_id"):
        _review_proposal(_review_view(), proposal_id=bad_id)


def test_proposal_review_cli_dispatches_without_changing_node_mode(monkeypatch, capsys):
    from scripts import query_theme_ontology as cli
    view = _review_view()
    monkeypatch.setattr(cli, "RepositoryStore", lambda: view)
    assert cli.main(["--proposal-id", _REVIEW_ID, "--asof", "2026-06-01"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["schema"] == "gmi.theme_ontology_proposal_review/v1"
    assert result["proposal_id"] == _REVIEW_ID
    assert cli.main(["--node-id", _REVIEW_LOCAL, "--asof", "2026-06-01"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result == compose_neighborhood(view, node_id=_REVIEW_LOCAL, asof="2026-06-01")
    with pytest.raises(SystemExit) as exc:
        cli.main(["--node-id", _REVIEW_LOCAL, "--proposal-id", _REVIEW_ID, "--asof", "2026-06-01"])
    assert exc.value.code == 2


def test_proposal_review_rejects_malformed_selected_row():
    view = _review_view(status="ratified")
    view._proposals[0]["ratified_by"] = None
    with pytest.raises(ValueError, match="malformed"):
        _review_proposal(view)


def test_proposal_review_reads_each_owner_once_for_both_endpoints():
    from types import SimpleNamespace
    view = _review_view(present=True)
    calls = {}
    def once(name):
        def read():
            calls[name] = calls.get(name, 0) + 1
            assert calls[name] == 1, f"reread owner table {name}"
            return getattr(view, name)()
        return read
    names = ("read_nodes", "read_edges", "read_node_lifecycle", "read_proposals")
    snapshot_source = SimpleNamespace(**{name: once(name) for name in names})
    assert _review_proposal(snapshot_source)["relation"]["state"] == "RELATION_PRESENT"
    assert calls == dict.fromkeys(names, 1)


def test_proposal_review_unsupported_kind_retains_unresolved_evidence():
    view = _review_view()
    view._proposals[0]["kind"] = "key_rename"
    result = _review_proposal(view)
    assert result["proposal"]["kind"] == "key_rename"
    assert result["proposal"]["truth_status"] == "PROPOSAL_ONLY"
    assert result["relation"]["state"] == "UNSUPPORTED_SUBJECT"
    assert result["endpoints"] == []


def test_proposal_review_default_rights_resolver_reaches_real_edges(monkeypatch, capsys):
    from engine.theme_graph import ontology
    from scripts import query_theme_ontology as cli
    calls = []
    def canonical_resolver(node_id):
        calls.append(node_id)
        return _ont_rights(node_id)
    monkeypatch.setattr(ontology, "_default_rights_resolver", canonical_resolver)
    view = _review_view(present=True)
    result = ontology.compose_proposal_review(view, proposal_id=_REVIEW_ID, asof="2026-06-01")
    assert result["relation"]["state"] == "RELATION_PRESENT"
    assert _REVIEW_LOCAL in calls
    assert result["endpoints"][0]["relations"][0]["rights"][0]["public_display_allowed"] is False
    monkeypatch.setattr(cli, "RepositoryStore", lambda: view)
    assert cli.main(["--proposal-id", _REVIEW_ID, "--asof", "2026-06-01"]) == 0
    assert json.loads(capsys.readouterr().out)["relation"]["state"] == "RELATION_PRESENT"


@pytest.mark.parametrize("status", ["ratified", "rejected"])
@pytest.mark.parametrize("created,decided,predates", [
    ("2026-06-01T23:30:00", "2026-06-02T00:30:00Z", False),
    ("2026-06-01T23:30:00Z", "2026-06-02T00:30:00", False),
    ("2026-06-01", "2026-06-01T00:00:00Z", False),
    ("2026-06-02T00:00:00", "2026-06-01T23:30:00Z", True),
    ("2026-06-01T23:30:00-02:00", "2026-06-02T00:30:00", True),
    ("2026-06-02T01:00:00", "2026-06-01T23:30:00-02:00", False),
])
def test_probation_mixed_legacy_clock_validation(status, created, decided, predates):
    candidate = _ont_proposal(_REVIEW_ID,
        {"local_theme": _REVIEW_LOCAL, "canonical_theme": _REVIEW_THEME},
        status=status, ratified_by="curator:test" if status == "ratified" else None,
        created=created, adjudicated_at=decided)
    schema = json.loads((ROOT / "contracts/theme_graph/probation_proposal.v1.schema.json").read_text())
    jsonschema.validate(candidate, schema)
    before = json.dumps(candidate, sort_keys=True)
    errors = probation.validate(candidate)
    assert errors == (["adjudicated_at predates created"] if predates else [])
    assert json.dumps(candidate, sort_keys=True) == before


@pytest.mark.parametrize("status", ["ratified", "rejected"])
@pytest.mark.parametrize("cutoff", ["2026-06-01", "2026-06-02"])
def test_proposal_review_mixed_legacy_clock_public_paths(status, cutoff, monkeypatch, capsys):
    from scripts import query_theme_ontology as cli
    view = _review_view(status=status)
    view._proposals[0].update(created="2026-06-01T23:30:00",
                              adjudicated_at="2026-06-02T00:30:00Z")
    before = json.dumps(view.__dict__, sort_keys=True)
    expected = "proposed" if cutoff == "2026-06-01" else status
    review = _review_proposal(view, cutoff=cutoff, asof="2026-06-02")
    assert review["proposal"]["status"] == expected
    assert review["proposal"]["truth_status"] == "PROPOSAL_ONLY"
    assert review["relation"]["state"] == "RELATION_ABSENT"
    node = _ont_compose(view, _REVIEW_LOCAL, cutoff=cutoff)
    assert node["proposals"][0]["status"] == expected
    monkeypatch.setattr(cli, "RepositoryStore", lambda: view)
    assert cli.main(["--proposal-id", _REVIEW_ID, "--asof", "2026-06-02",
                     "--knowledge-cutoff", cutoff]) == 0
    assert json.loads(capsys.readouterr().out)["proposal"]["status"] == expected
    if expected == "proposed":
        assert review["proposal"]["adjudicated_at"] is None
        assert review["proposal"]["ratified_by"] is None
    assert json.dumps(view.__dict__, sort_keys=True) == before


# Independent historical report: consumes already-produced neighborhood documents.
def _change_report_module():
    import importlib.util
    assert importlib.util.find_spec("engine.theme_graph.change_report"), "historical change report is missing"
    from engine.theme_graph import change_report
    return change_report


def _change_documents():
    local = "ltheme:finviz:memory"
    nodes = [_ont_node(local, "local_theme", name="Memory Chips")]
    nodes += [_ont_node("co:us:" + x, "company", name=x) for x in "ABC"]
    edges = [_ont_edge("a", "MEMBER_OF", "co:us:A", local, valid_to="2026-05-01"),
             _ont_edge("b", "MEMBER_OF", "co:us:B", local),
             _ont_edge("c", "MEMBER_OF", "co:us:C", local, valid_from="2026-05-01")]
    view = _OntologyStore(nodes=nodes, edges=edges)
    return [compose_neighborhood(view, node_id=local, asof=day,
        knowledge_cutoff="2026-06-01", rights_resolver=_ont_rights)
        for day in ("2026-04-01", "2026-06-01")]


def _report(before=None, after=None):
    if before is None: before, after = _change_documents()
    result = _change_report_module().build_change_report(before, after)
    from referencing import Registry, Resource
    ns = json.loads((ROOT / "contracts/theme_graph/ontology_neighborhood.v1.schema.json").read_text())
    schema = json.loads((ROOT / "contracts/theme_graph/ontology_change_report.v1.schema.json").read_text())
    registry = Registry().with_resource(ns["$id"], Resource.from_contents(ns))
    jsonschema.Draft202012Validator(schema, registry=registry).validate(result)
    return result


def test_gmi_change_report_names_membership_changes_and_preserves_evidence():
    result = _report()
    assert result["comparison_basis"] == "EFFECTIVE_DATE_CHANGE"
    assert result["summary"]["memberships_added"] == result["summary"]["memberships_removed"] == 1
    rows = {x["peer_node_id"]: x for x in result["relation_changes"]}
    assert rows["co:us:A"]["change"] == "REMOVED"
    assert rows["co:us:A"]["before"][0]["evidence_refs"] == ["ev:test"]
    assert rows["co:us:C"]["after"][0]["peer"]["name_en"] == "C"
    assert "co:us:B" not in rows and result["mapping_changed"] is False
    assert result["authority_ceiling"] == "research_internal_only"


def test_gmi_change_report_evidence_updates_are_not_membership_turnover():
    import copy
    before, _ = _change_documents(); after = copy.deepcopy(before)
    after["knowledge_cutoff"] = "2026-07-01"
    after["relations"][0]["evidence_refs"] = ["ev:later-correction"]
    result = _report(before, after)
    assert result["comparison_basis"] == "KNOWLEDGE_REVISION"
    assert result["summary"]["memberships_added"] == result["summary"]["memberships_removed"] == 0
    assert result["relation_changes"][0]["change"] == "UPDATED"
    assert "evidence_refs" in result["relation_changes"][0]["changed_fields"]


@pytest.mark.parametrize("missing,expected", [("baseline", "BASELINE_UNAVAILABLE"),
    ("target", "TARGET_UNAVAILABLE"), ("both", "BOTH_UNAVAILABLE")])
def test_gmi_change_report_unavailable_is_not_zero_membership(missing, expected):
    before, after = _change_documents()
    absent = compose_neighborhood(_OntologyStore(), node_id=before["node_id"], asof="2026-01-01")
    if missing in ("baseline", "both"): before = absent
    if missing in ("target", "both"): after = absent
    result = _report(before, after)
    assert result["availability"]["state"] == expected
    assert result["summary"] is None and result["relation_changes"] == []
    assert result["mapping_changed"] is None


@pytest.mark.parametrize("basis", ["IDENTICAL_CLOCKS", "BOTH_CLOCKS_CHANGED"])
def test_gmi_change_report_clock_labels_and_no_input_mutation(basis):
    import copy
    before, after = _change_documents()
    if basis == "IDENTICAL_CLOCKS": after = copy.deepcopy(before)
    else: after["knowledge_cutoff"] = "2026-07-01"
    saved = json.dumps([before, after], sort_keys=True)
    result = _report(before, after)
    assert result["comparison_basis"] == basis
    assert len(result["input_digests"]["baseline"]) == 64
    result["baseline"]["subject"]["name_en"] = "changed output"
    assert json.dumps([before, after], sort_keys=True) == saved
    assert "not capital flows" in " ".join(result["limitations"])


@pytest.mark.parametrize("damage", ["schema", "identity", "calendar", "unknown_field"])
def test_gmi_change_report_refuses_invalid_or_mismatched_inputs(damage):
    before, after = _change_documents()
    if damage == "schema": after["schema"] = "other/v1"
    elif damage == "identity": after["node_id"] = "ltheme:finviz:other"
    elif damage == "calendar": after["asof"] = "2026-02-31"
    else: after["hidden_score"] = 100
    with pytest.raises(ValueError): _report(before, after)


def test_gmi_change_report_keeps_distinct_evidence_rows_and_stable_order():
    import copy
    before, after = _change_documents()
    additional = copy.deepcopy(after["relations"][0]); additional["edge_id"] = "second-proof"
    after["relations"].append(additional)
    first = _report(before, after); after["relations"].reverse()
    second = _report(before, after)
    assert first["relation_changes"] == second["relation_changes"]
    updated = next(x for x in first["relation_changes"] if x["change"] == "UPDATED")
    assert len(updated["after"]) == 2


def test_gmi_change_report_markdown_escapes_untrusted_labels():
    before, after = _change_documents(); after["subject"]["name_en"] = "<script>alert(1)</script>|[x]"
    result = _report(before, after)
    text = _change_report_module().render_markdown(result)
    assert "<script>" not in text and "co:us:A" in text and "co:us:C" in text


def test_gmi_change_report_cli_real_input_output_and_input_protection(tmp_path, capsys):
    import importlib.util
    assert importlib.util.find_spec("scripts.explain_theme_changes"), "change-report CLI missing"
    from scripts import explain_theme_changes as cli
    before, after = _change_documents()
    baseline, target = tmp_path / "before.json", tmp_path / "after.json"
    baseline.write_text(json.dumps(before)); target.write_text(json.dumps(after))
    args = ["--baseline", str(baseline), "--target", str(target)]
    assert cli.main(args) == 0
    assert json.loads(capsys.readouterr().out)["summary"]["memberships_added"] == 1
    assert cli.main(args + ["--format", "markdown"]) == 0
    assert "MEMBER_OF" in capsys.readouterr().out
    original = baseline.read_bytes()
    assert cli.main(args + ["--out", str(baseline)]) == 2
    assert baseline.read_bytes() == original
    assert json.loads(capsys.readouterr().err)["code"] == "CHANGE_REPORT_UNAVAILABLE"


def test_gmi_change_report_decision_change_does_not_invent_a_mapping():
    view = _review_view(status="ratified", present=False)
    before, after = [compose_neighborhood(view, node_id=_REVIEW_LOCAL, asof="2026-06-01",
        knowledge_cutoff=cutoff, rights_resolver=_ont_rights) for cutoff in ("2026-02-01", "2026-02-03")]
    result = _report(before, after)
    assert result["proposal_changes"][0]["before"][0]["status"] == "proposed"
    assert result["proposal_changes"][0]["after"][0]["status"] == "ratified"
    assert result["summary"]["proposals_updated"] == 1
    assert result["relation_changes"] == [] and result["mapping_changed"] is False
    assert result["curation_changed"] is True


def test_gmi_change_report_subject_revision_is_not_membership_change():
    import copy
    before, _ = _change_documents(); after = copy.deepcopy(before)
    after["knowledge_cutoff"] = "2026-07-01"; after["subject"]["status"] = "retired"
    result = _report(before, after)
    assert result["subject_changed_fields"] == ["status"]
    assert result["comparison_basis"] == "KNOWLEDGE_REVISION"
    assert not any(result["summary"].values())


def test_gmi_change_report_human_brief_names_subject_correction():
    import copy
    before, _ = _change_documents(); after = copy.deepcopy(before)
    after["subject"]["status"] = "retired"; after["knowledge_cutoff"] = "2026-07-01"
    report = _report(before, after)
    text = _change_report_module().render_markdown(report)
    assert "status: canonical → retired" in text


def _overlap_review():
    view = _review_view(present=True)
    for ticker in ("AAA", "BBB", "CCC"):
        view._nodes.append(_ont_node("co:us:" + ticker, "company", name=ticker))
    for index, (ticker, target) in enumerate((("AAA", _REVIEW_LOCAL), ("BBB", _REVIEW_LOCAL),
                                            ("BBB", _REVIEW_THEME), ("CCC", _REVIEW_THEME))):
        view._edges.append(_ont_edge("member-" + str(index), "MEMBER_OF", "co:us:" + ticker, target))
    return _review_proposal(view)


def _overlap_report(document):
    import importlib.util
    assert importlib.util.find_spec("engine.theme_graph.membership_evidence"), "membership evidence consumer missing"
    from engine.theme_graph.membership_evidence import build_overlap_evidence
    from referencing import Registry, Resource
    result = build_overlap_evidence(document)
    path = ROOT / "contracts/theme_graph"
    neighborhood = json.loads((path / "ontology_neighborhood.v1.schema.json").read_text())
    registry = Registry().with_resource(neighborhood["$id"], Resource.from_contents(neighborhood))
    schema = json.loads((path / "ontology_overlap_evidence.v1.schema.json").read_text())
    jsonschema.Draft202012Validator(schema, registry=registry).validate(result)
    return result


def test_gmi_overlap_exact_company_evidence_and_descriptive_counts():
    result = _overlap_report(_overlap_review())
    assert result["availability"]["state"] == "OK"
    assert result["counts"] == dict(source=2, target=2, shared=1, source_only=1, target_only=1, union=3)
    assert result["ratios"] == dict(source_containment=0.5, target_containment=0.5, jaccard=1 / 3)
    assert [row["node_id"] for row in result["shared"]] == ["co:us:BBB"]
    assert result["shared"][0]["source_memberships"][0]["evidence_refs"] == ["ev:test"]
    assert result["shared"][0]["source_memberships"][0]["rights"][0]["public_display_allowed"] is False
    assert result["reported_evidence"] == {"overlap": 9}
    assert result["proposal_status"] == "proposed"
    assert result["mapping_relation_state"] == "RELATION_PRESENT"
    assert result["authority_ceiling"] == "research_internal_only"


@pytest.mark.parametrize("status", ["proposed", "ratified", "rejected"])
def test_gmi_overlap_never_turns_overlap_into_approval(status):
    document = _overlap_review(); proposal = document["proposal"]
    proposal.update(status=status, ratified_by="curator:test" if status == "ratified" else None,
                    adjudicated_at=None if status == "proposed" else "2026-02-02T00:00:00Z")
    report = _overlap_report(document)
    assert report["proposal_status"] == status
    assert report["counts"]["shared"] == 1
    assert not ({"approved", "recommendation", "score", "rank", "weight"} & set(report))


def test_gmi_overlap_duplicate_evidence_does_not_inflate_members():
    import copy
    document = _overlap_review(); row = next(r for r in document["endpoints"][0]["relations"] if r["peer_node_id"] == "co:us:BBB")
    extra = copy.deepcopy(row); extra["edge_id"] = "independent-proof"; extra["evidence_refs"] = ["ev:second"]
    document["endpoints"][0]["relations"].append(extra)
    result = _overlap_report(document)
    assert result["counts"]["shared"] == 1
    assert len(result["shared"][0]["source_memberships"]) == 2


@pytest.mark.parametrize("field", ["node_id", "asof", "knowledge_cutoff", "proposal_id"])
def test_gmi_overlap_rejects_incoherent_review_binding(field):
    document = _overlap_review()
    if field == "proposal_id": document["proposal"][field] = "prop:bbbbbbbbbbbbbbbb"
    else: document["endpoints"][0][field] = "theme:wrong" if field == "node_id" else "2026-05-01"
    with pytest.raises(ValueError): _overlap_report(document)


def test_gmi_overlap_sorting_immutability_and_no_label_based_merging():
    import copy
    document = _overlap_review(); before = copy.deepcopy(document)
    left = document["endpoints"][0]
    for row in left["relations"]:
        if row.get("peer"): row["peer"]["name_en"] = "SAME NAME"
    expected = _overlap_report(document)
    for endpoint in document["endpoints"]: endpoint["relations"].reverse()
    actual = _overlap_report(document)
    for key in ("shared", "source_only", "target_only", "counts", "ratios"):
        assert actual[key] == expected[key]
    assert actual["counts"]["union"] == 3
    restored = copy.deepcopy(before); _overlap_report(restored)
    assert restored == before


def test_gmi_overlap_does_not_use_other_relationships_as_membership():
    document = _overlap_review()
    for endpoint in document["endpoints"]:
        for row in endpoint["relations"]:
            if row["peer_node_id"] == "co:us:BBB": row["type"] = "EXPRESSES"
    report = _overlap_report(document)
    assert report["counts"] == dict(source=1, target=1, shared=0, source_only=1, target_only=1, union=2)
    assert report["ratios"]["jaccard"] == 0


def test_gmi_overlap_cli_json_and_markdown_preserve_input(tmp_path, capsys):
    _overlap_report(_overlap_review())
    from scripts.explain_theme_overlap import main
    source = tmp_path / "review.json"; source.write_text(json.dumps(_overlap_review()))
    before = source.read_bytes()
    assert main(["--review", str(source)]) == 0
    assert json.loads(capsys.readouterr().out)["counts"]["shared"] == 1
    output = tmp_path / "brief.md"
    assert main(["--review", str(source), "--format", "markdown", "--out", str(output)]) == 0
    text = output.read_text(); assert "co:us:BBB" in text and "ev:test" in text
    assert main(["--review", str(source), "--out", str(source)]) == 2
    assert main(["--review", str(source), "--out", str(output)]) == 2
    assert source.read_bytes() == before and output.read_text() == text


def _overlap_count_review():
    basket = "basket:baskets:utilities"
    view = _review_view(present=False)
    view._proposals[0]["subject"] = {"basket": basket, "local_theme": _REVIEW_LOCAL}
    view._proposals[0]["evidence"] = {"basket_size": 2, "subtheme_size": 2, "overlap": 1}
    view._nodes.append(_ont_node(basket, "basket"))
    for ticker in ("AAA", "BBB", "CCC"):
        view._nodes.append(_ont_node("co:us:" + ticker, "company", name=ticker))
    for i, (ticker, dst) in enumerate((("AAA", basket), ("BBB", basket),
                                      ("BBB", _REVIEW_LOCAL), ("CCC", _REVIEW_LOCAL))):
        view._edges.append(_ont_edge("count-member-" + str(i), "MEMBER_OF", "co:us:" + ticker, dst))
    return _review_proposal(view)


def _overlap_count_comparison(document):
    report = _overlap_report(document)
    assert "reported_count_comparison" in report, "reported versus observed count comparison is missing"
    return report, report["reported_count_comparison"]


@pytest.mark.parametrize("size,state,delta", [(2, "REPORTED_COUNTS_EQUAL", 0),
    (3, "REPORTED_COUNTS_DIFFER", -1)])
def test_gmi_overlap_reported_count_comparison(size, state, delta):
    document = _overlap_count_review(); document["proposal"]["evidence"]["basket_size"] = size
    report, comparison = _overlap_count_comparison(document)
    assert comparison["state"] == state and comparison["same_vintage_verified"] is False
    assert comparison["fields"][0] == dict(field="basket_size", reported=size, observed=2, delta=delta)
    assert report["reported_evidence"]["basket_size"] == size


@pytest.mark.parametrize("value", [None, True, -1, "2", 2.0, {}])
def test_gmi_overlap_reported_counts_never_coerce_invalid_statistics(value):
    document = _overlap_count_review()
    document["proposal"]["evidence"]["basket_size"] = value
    report, comparison = _overlap_count_comparison(document)
    assert comparison["state"] == "REPORTED_COUNTS_PARTIAL"
    assert comparison["invalid_fields"] == ["basket_size"]
    assert all(row["field"] != "basket_size" for row in comparison["fields"])
    assert report["reported_evidence"]["basket_size"] == value


def test_gmi_overlap_reported_counts_missing_is_not_zero():
    document = _overlap_count_review(); del document["proposal"]["evidence"]["overlap"]
    _, comparison = _overlap_count_comparison(document)
    assert comparison["state"] == "REPORTED_COUNTS_PARTIAL"
    assert comparison["missing_fields"] == ["overlap"]
    assert all(row["field"] != "overlap" for row in comparison["fields"])


def test_gmi_overlap_reported_counts_respect_subject_metric_semantics():
    document = _overlap_review()
    document["proposal"]["evidence"] = {"basket_size": 2, "subtheme_size": 2, "overlap": 1}
    _, comparison = _overlap_count_comparison(document)
    assert comparison["state"] == "NOT_EVALUATED"
    assert comparison["reason"] == "unsupported_metric_semantics"
    assert comparison["fields"] == []


@pytest.mark.parametrize("empty_side", [0, 1, "both"])
def test_gmi_overlap_empty_membership_evidence_abstains(empty_side):
    document = _overlap_count_review()
    for i, endpoint in enumerate(document["endpoints"]):
        if empty_side == "both" or i == empty_side:
            endpoint["relations"] = [r for r in endpoint["relations"] if r["type"] != "MEMBER_OF"]
    report, comparison = _overlap_count_comparison(document)
    assert report["availability"]["state"] == "INSUFFICIENT_MEMBERSHIP_EVIDENCE"
    assert report["ratios"] is None
    assert comparison["state"] == "NOT_EVALUATED" and comparison["fields"] == []


def test_gmi_overlap_null_member_metadata_preserves_recorded_membership():
    document = _overlap_count_review()
    for endpoint in document["endpoints"]:
        for row in endpoint["relations"]:
            if row["peer_node_id"] == "co:us:BBB": row["peer"] = None
    report = _overlap_report(document)
    assert report["counts"]["shared"] == 1
    assert report["metadata_unavailable_ids"] == ["co:us:BBB"]
    assert len(report["shared"][0]["source_memberships"]) == 1


def test_gmi_overlap_unavailable_endpoint_is_not_an_empty_set():
    view = _review_view(); view._nodes.pop()
    report = _overlap_report(_review_proposal(view))
    assert report["availability"]["state"] == "ENDPOINT_UNAVAILABLE"
    assert report["counts"] is None and report["ratios"] is None


def test_gmi_overlap_unavailable_proposal_does_not_compare_counts():
    document = _review_proposal(_OntologyStore())
    report, comparison = _overlap_count_comparison(document)
    assert report["availability"]["state"] == "PROPOSAL_UNAVAILABLE"
    assert comparison["state"] == "NOT_EVALUATED" and comparison["fields"] == []


def test_gmi_overlap_conflicting_evidence_identity_refuses():
    import copy
    document = _overlap_count_review()
    row = document["endpoints"][0]["relations"][0]
    duplicate = copy.deepcopy(row); duplicate["evidence_refs"] = ["ev:conflicting"]
    document["endpoints"][0]["relations"].append(duplicate)
    with pytest.raises(ValueError, match="conflicting"):
        _overlap_report(document)


def test_gmi_overlap_count_difference_is_visible_in_human_brief():
    from engine.theme_graph.membership_evidence import render_markdown
    document = _overlap_count_review(); document["proposal"]["evidence"]["basket_size"] = 3
    report, _ = _overlap_count_comparison(document)
    text = render_markdown(report)
    assert "basket_size: reported 3; recorded 2; difference -1." in text
    assert "Same-vintage comparability is not established" in text


_SECURITY_KEY = "SEC:US-XNAS-AAA"
_ISSUER_KEY = "ISS:US-XNAS-AAA"


def _security_row(node_id="co:us:AAA", security_id=_SECURITY_KEY, issuer_id=_ISSUER_KEY):
    return dict(schema="gmi.identity_resolution/v1", node_id=node_id,
        graph_kind="company", market_scope="us", graph_identity_epoch=1,
        source_native_symbol="NOT_A_JOIN_KEY", resolution_asof="2026-09-18",
        resolution_state="RESOLVED", issuer_id=issuer_id, security_id=security_id,
        listing_key=security_id.removeprefix("SEC:"), join_method="vendor_alias",
        master_generated_at="2026-09-18T00:00:00Z", master_symbol_directory_snapshot=None,
        master_code_version="fixture", refusal_reason=None, source_receipts='{"fixture":true}',
        computed_at="2026-09-18T17:42:27Z", engine_version="theme_graph.v1")


def _security_query(rows=None, view=None, **kwargs):
    import importlib.util
    assert importlib.util.find_spec("engine.theme_graph.security_navigation"), "exact security navigation is missing"
    from engine.theme_graph import security_navigation as navigation
    rows = [_security_row()] if rows is None else rows
    view = _OntologyStore(nodes=[_ont_node(r["node_id"], "company") for r in rows]) if view is None else view
    result = navigation.compose_security_neighborhoods(view, rows,
        identity_kind=kwargs.pop("identity_kind", "security"),
        identity_id=kwargs.pop("identity_id", _SECURITY_KEY),
        asof=kwargs.pop("asof", "2026-06-01"), rights_resolver=_ont_rights, **kwargs)
    _security_validate(result)
    return result


def _security_validate(result):
    from referencing import Registry, Resource
    root = ROOT / "contracts/theme_graph"
    registry = Registry()
    for name in ("ontology_neighborhood.v1", "identity_resolution.v1"):
        schema = json.loads((root / (name + ".schema.json")).read_text())
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    schema = json.loads((root / "security_neighborhoods.v1.schema.json").read_text())
    jsonschema.Draft202012Validator(schema, registry=registry).validate(result)


def test_gmi_security_preserves_every_same_security_graph_binding():
    rows = [_security_row("co:us:OLD"), _security_row("co:us:NEW")]
    result = _security_query(rows)
    assert [x["node_id"] for x in result["bindings"]] == ["co:us:NEW", "co:us:OLD"]
    assert result["counts"] == dict(matched_nodes=2, available_nodes=2, unavailable_nodes=0)
    assert all(x["resolution"]["security_id"] == _SECURITY_KEY for x in result["bindings"])
    assert result["identity_basis"] == "LATEST_PUBLISHED_OWNER_REFERENCE"
    assert result["historical_identity_claim"] is False
    assert result["knowledge_cutoff_applies_to"] == "GRAPH_NEIGHBORHOODS_ONLY"
    assert result["bindings"][0]["resolution"]["computed_at"] == "2026-09-18T17:42:27Z"


def test_gmi_security_issuer_query_preserves_separate_share_classes():
    rows = [_security_row(), _security_row("co:us:AAB", "SEC:US-XNAS-AAB")]
    result = _security_query(rows, identity_kind="issuer", identity_id=_ISSUER_KEY)
    assert {x["resolution"]["security_id"] for x in result["bindings"]} == {_SECURITY_KEY, "SEC:US-XNAS-AAB"}


@pytest.mark.parametrize("rows,state", [([], "IDENTITY_OWNER_UNAVAILABLE"),
    ([_security_row(security_id="SEC:US-XNAS-OTHER")], "NO_GRAPH_BINDING")])
def test_gmi_security_absence_does_not_become_an_empty_theme_set(rows, state):
    result = _security_query(rows)
    assert result["availability"]["state"] == state
    assert result["bindings"] == [] and result["counts"] is None


@pytest.mark.parametrize("kind,key", [("ticker", "AAA"), ("security", "AAA"),
    ("security", " SEC:US-XNAS-AAA"), ("issuer", _SECURITY_KEY),
    ("security", "SEC:"), ("security", "SEC:US XNAS AAA")])
def test_gmi_security_never_resolves_a_label_or_mismatched_id_kind(kind, key):
    with pytest.raises(ValueError): _security_query(identity_kind=kind, identity_id=key)


@pytest.mark.parametrize("mutation", ["duplicate", "refused", "missing_listing", "missing_clock", "noncompany"])
def test_gmi_security_invalid_owner_binding_fails_closed(mutation):
    rows = [_security_row()]
    if mutation == "duplicate": rows.append(dict(rows[0]))
    elif mutation == "refused": rows[0]["resolution_state"] = "AMBIGUOUS"
    elif mutation == "missing_listing": rows[0]["listing_key"] = None
    elif mutation == "missing_clock": rows[0]["computed_at"] = None
    else: rows[0]["node_id"] = "theme:AAA"
    with pytest.raises(ValueError): _security_query(rows)


@pytest.mark.parametrize("visible,state", [(0, "GRAPH_SUBJECTS_UNAVAILABLE"),
    (1, "PARTIAL_GRAPH_VISIBILITY"), (2, "OK")])
def test_gmi_security_graph_visibility_stays_separate_from_identity(visible, state):
    rows = [_security_row("co:us:OLD"), _security_row("co:us:NEW")]
    view = _OntologyStore(nodes=[_ont_node(r["node_id"], "company") for r in rows[:visible]])
    result = _security_query(rows, view=view)
    assert result["availability"]["state"] == state
    assert len(result["bindings"]) == 2
    assert result["counts"]["available_nodes"] == visible
    assert result["counts"]["unavailable_nodes"] == 2 - visible


def test_gmi_security_preserves_all_local_memberships_and_rights():
    view = _OntologyStore(nodes=[_ont_node("co:us:AAA", "company"),
        _ont_node("ltheme:finviz:first", "local_theme"), _ont_node("ltheme:finviz:second", "local_theme")],
        edges=[_ont_edge("edge-a", "MEMBER_OF", "co:us:AAA", "ltheme:finviz:first"),
               _ont_edge("edge-b", "MEMBER_OF", "co:us:AAA", "ltheme:finviz:second")])
    result = _security_query(view=view)
    neighborhood = result["bindings"][0]["neighborhood"]
    assert {r["peer_node_id"] for r in neighborhood["relations"]} == {"ltheme:finviz:first", "ltheme:finviz:second"}
    assert all(r["rights"][0]["public_display_allowed"] is False for r in neighborhood["relations"])
    result = _security_query(view=view, knowledge_cutoff="2025-12-31")
    assert result["availability"]["state"] == "GRAPH_SUBJECTS_UNAVAILABLE"
    assert result["bindings"][0]["resolution"]["security_id"] == _SECURITY_KEY


def test_gmi_security_owner_rows_and_graph_tables_are_not_rewritten_or_reread():
    import copy
    from types import SimpleNamespace
    rows = [_security_row("co:us:OLD"), _security_row("co:us:NEW")]
    before = copy.deepcopy(rows)
    view = _OntologyStore(nodes=[_ont_node(r["node_id"], "company") for r in rows])
    calls = {}
    def once(name):
        def read():
            calls[name] = calls.get(name, 0) + 1
            assert calls[name] == 1
            return getattr(view, name)()
        return read
    names = ("read_nodes", "read_node_lifecycle", "read_edges", "read_proposals")
    result = _security_query(rows, view=SimpleNamespace(**{n: once(n) for n in names}))
    assert rows == before and calls == dict.fromkeys(names, 1)
    result["bindings"][0]["resolution"]["source_receipts"] = "changed output"
    assert rows == before


def test_gmi_security_null_issuer_never_acquires_an_inferred_issuer():
    row = _security_row(issuer_id=None)
    assert _security_query([row])["bindings"][0]["resolution"]["issuer_id"] is None
    assert _security_query([row], identity_kind="issuer", identity_id=_ISSUER_KEY)["availability"]["state"] == "NO_GRAPH_BINDING"


def test_gmi_security_cli_uses_only_native_owner_and_preserves_existing_outputs(monkeypatch, tmp_path, capsys):
    _security_query()
    from scripts import query_theme_security as cli
    calls = []
    def reader(*, latest):
        calls.append(latest)
        return [_security_row()]
    monkeypatch.setattr(cli.identity_owner, "read_identity_resolution", reader)
    monkeypatch.setattr(cli, "RepositoryStore", lambda: _OntologyStore(nodes=[_ont_node("co:us:AAA", "company")]))
    args = ["--security-id", _SECURITY_KEY, "--asof", "2026-06-01"]
    assert cli.main(args) == 0
    result = json.loads(capsys.readouterr().out)
    _security_validate(result)
    assert result["bindings"][0]["node_id"] == "co:us:AAA" and calls == [True]
    output = tmp_path / "security.json"
    assert cli.main(args + ["--out", str(output)]) == 0
    saved = output.read_bytes()
    assert cli.main(args + ["--out", str(output)]) == 2
    assert output.read_bytes() == saved
    with pytest.raises(SystemExit):
        cli.main(args + ["--issuer-id", _ISSUER_KEY])


def _worklist_rows():
    from engine.theme_graph import probation
    rows = [_ont_proposal(f"prop:{i:016x}", {"local_theme": "ltheme:finviz:ai", "canonical_theme": f"theme:{i}"},
        created=f"2026-01-0{i}T00:00:00Z") for i in (1, 2, 3)]
    for row in rows:
        row["proposal_id"] = probation.proposal_id(row["kind"], row["subject"])
    return rows


def _worklist(rows=None, **kwargs):
    import importlib.util
    assert importlib.util.find_spec("engine.theme_graph.proposal_worklist"), "proposal worklist consumer missing"
    from engine.theme_graph.proposal_worklist import compose_worklist
    from referencing import Registry, Resource
    result = compose_worklist(_worklist_rows() if rows is None else rows,
        asof=kwargs.pop("asof", "2026-02-01"), **kwargs)
    root = ROOT / "contracts/theme_graph"
    ns = json.loads((root / "ontology_neighborhood.v1.schema.json").read_text())
    registry = Registry().with_resource(ns["$id"], Resource.from_contents(ns))
    schema = json.loads((root / "proposal_worklist.v1.schema.json").read_text())
    jsonschema.Draft202012Validator(schema, registry=registry).validate(result)
    return result


def test_gmi_worklist_browses_existing_queue_without_mutation():
    import copy
    rows = _worklist_rows(); before = copy.deepcopy(rows)
    result = _worklist(rows)
    assert result["counts"] == {"visible": 3, "matching": 3, "returned": 3}
    assert result["items"][0]["review_query"] == {"proposal_id": rows[0]["proposal_id"], "asof": "2026-02-01", "knowledge_cutoff": "2026-02-01"}
    assert all(item["proposal"]["truth_status"] == "PROPOSAL_ONLY" for item in result["items"])
    assert rows == before


@pytest.mark.parametrize("status", ["ratified", "rejected"])
def test_gmi_worklist_cutoff_hides_future_rows_and_decisions(status):
    rows = _worklist_rows()
    rows[0].update(status=status, ratified_by="curator:test" if status == "ratified" else None,
        adjudicated_at="2026-03-01T00:00:00Z", note="creation note")
    rows[-1]["created"] = "2026-03-01T00:00:00Z"
    result = _worklist(rows)
    assert result["counts"]["visible"] == 2
    assert result["facets"]["status"] == {"proposed": 2, "ratified": 0, "rejected": 0}
    assert result["items"][0]["proposal"]["note"] == "creation note"
    assert result["items"][0]["proposal"]["adjudicated_at"] is None
    rows[-1]["subject"] = {"future": "changed"}
    from engine.theme_graph import probation
    rows[-1]["proposal_id"] = probation.proposal_id(rows[-1]["kind"], rows[-1]["subject"])
    assert _worklist(rows) == result


@pytest.mark.parametrize("filters,expected", [({"kind": "mapping"}, 2),
    ({"proposed_by": "refresh_identity"}, 1), ({"subject_id": "theme:1"}, 1),
    ({"subject_id": "theme:not-present"}, 0), ({"status": "rejected"}, 1)])
def test_gmi_worklist_exact_filters(filters, expected):
    rows = _worklist_rows()
    rows[1].update(kind="key_rename", proposed_by="refresh_identity")
    from engine.theme_graph import probation
    rows[1]["proposal_id"] = probation.proposal_id(rows[1]["kind"], rows[1]["subject"])
    rows[2].update(status="rejected", adjudicated_at="2026-01-05T00:00:00Z")
    result = _worklist(rows, **({"status": "all"} | filters))
    assert result["counts"]["matching"] == expected
    assert result["counts"]["visible"] == 3
    assert result["availability"]["state"] == ("OK" if expected else "NO_MATCH")


def test_gmi_worklist_pages_bind_same_visible_snapshot_and_preserve_order():
    rows = _worklist_rows(); first = _worklist(rows, limit=2)
    second = _worklist(list(reversed(rows)), limit=2, offset=first["page"]["next_offset"], expected_snapshot=first["snapshot_sha256"])
    assert [x["proposal"]["proposal_id"] for x in first["items"] + second["items"]] == [r["proposal_id"] for r in rows]
    assert second["page"]["next_offset"] is None
    rows[0]["note"] = "new visible evidence"
    with pytest.raises(ValueError, match="snapshot"):
        _worklist(rows, offset=2, expected_snapshot=first["snapshot_sha256"])


@pytest.mark.parametrize("bad", [{"limit": 0}, {"limit": 101}, {"limit": True},
    {"offset": -1}, {"offset": 1}, {"status": "approved"}, {"kind": "fuzzy"},
    {"proposed_by": "anonymous"}, {"subject_id": "AI"}, {"expected_snapshot": "invalid"}])
def test_gmi_worklist_rejects_unsafe_selection_arguments(bad):
    with pytest.raises(ValueError): _worklist(**bad)


def test_gmi_worklist_empty_queue_is_distinct_from_no_matching_filter():
    result = _worklist([])
    assert result["availability"]["state"] == "EMPTY"
    assert result["counts"] == {"visible": 0, "matching": 0, "returned": 0}
    assert result["items"] == []


def test_gmi_worklist_duplicate_visible_identity_fails_closed():
    rows = _worklist_rows(); rows.append(dict(rows[0]))
    with pytest.raises(ValueError, match="duplicate"): _worklist(rows)


@pytest.mark.parametrize("raw", ['{"proposal_id":"a","proposal_id":"b"}', 'not JSON', '[]'])
def test_gmi_worklist_strict_queue_reader_refuses_ambiguous_rows(tmp_path, raw):
    from engine.theme_graph import probation
    path = tmp_path / "proposals.jsonl"; path.write_text(raw + "\n")
    with pytest.raises(ValueError): probation.read_proposals(path, strict=True)


def test_gmi_worklist_strict_queue_missing_file_is_not_empty(tmp_path):
    from engine.theme_graph import probation
    path = tmp_path / "missing.jsonl"
    assert probation.read_proposals(path) == []
    with pytest.raises(FileNotFoundError): probation.read_proposals(path, strict=True)
    path.write_text("")
    assert probation.read_proposals(path, strict=True) == []


def test_gmi_worklist_utc_creation_sort_not_lexical_sort():
    rows = _worklist_rows()[:2]
    rows[0]["created"] = "2026-01-01T09:00:00Z"
    rows[1]["created"] = "2026-01-01T10:00:00+02:00"
    assert _worklist(rows)["items"][0]["proposal"]["proposal_id"] == rows[1]["proposal_id"]


def test_gmi_worklist_malformed_visible_row_is_not_silently_omitted():
    rows = _worklist_rows(); rows[1]["subject"] = []
    with pytest.raises(ValueError, match="proposal"): _worklist(rows)


def test_gmi_worklist_cli_pages_link_to_existing_exact_review(monkeypatch, tmp_path, capsys):
    _worklist()
    from scripts import list_theme_proposals as cli
    path = tmp_path / "proposals.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in _worklist_rows()) + "\n")
    monkeypatch.setattr(cli, "proposal_path", lambda: path)
    assert cli.main(["--asof", "2026-02-01", "--limit", "2"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["items"][0]["review_query"]["proposal_id"] == _worklist_rows()[0]["proposal_id"]
    output = tmp_path / "worklist.md"
    assert cli.main(["--asof", "2026-02-01", "--format", "markdown", "--out", str(output)]) == 0
    assert _worklist_rows()[0]["proposal_id"] in output.read_text()
    assert "PROPOSAL_ONLY" in output.read_text()
    original = path.read_bytes()
    assert cli.main(["--asof", "2026-02-01", "--out", str(path)]) == 2
    assert path.read_bytes() == original


@pytest.mark.parametrize("status", ["ratified", "rejected"])
def test_gmi_review_creation_note_survives_decision_cutoff(status):
    from engine.theme_graph.ontology import compose_proposal_review
    view = _review_view(status=status)
    view._proposals[0].update(note="proposal-era evidence", adjudication_note="later decision reason",
        created="2026-01-01", adjudicated_at="2026-03-01")
    result = compose_proposal_review(view, proposal_id=_REVIEW_ID, asof="2026-02-01", rights_resolver=_ont_rights)
    assert result["proposal"]["note"] == "proposal-era evidence"
    assert result["proposal"]["adjudication_note"] is None


@pytest.mark.parametrize("field", ["proposal_id", "status"])
def test_gmi_review_overlap_cli_rejects_duplicate_json_keys(tmp_path, capsys, field):
    from scripts.explain_theme_overlap import main
    document = _overlap_review()
    raw = json.dumps(document)
    value = document["proposal_id"] if field == "proposal_id" else "proposed"
    needle = json.dumps(field) + ": " + json.dumps(value)
    raw = raw.replace(needle, needle + ", " + needle, 1)
    path = tmp_path / "ambiguous.json"; path.write_text(raw)
    assert main(["--review", str(path)]) == 2
    assert "duplicate JSON key" in capsys.readouterr().err


def test_gmi_review_decision_note_has_separate_visibility_and_validation():
    from engine.theme_graph import probation
    from engine.theme_graph.ontology import compose_proposal_review
    view = _review_view(status="rejected")
    view._proposals[0]["adjudication_note"] = "curator rationale"
    result = compose_proposal_review(view, proposal_id=_REVIEW_ID, asof="2026-06-01", rights_resolver=_ont_rights)
    assert result["proposal"]["adjudication_note"] == "curator rationale"
    row = _worklist_rows()[0]; row["adjudication_note"] = "unearned decision"
    assert probation.validate(row)


def test_gmi_strict_reader_preserves_legacy_forgiving_default(tmp_path):
    from engine.theme_graph import probation
    path = tmp_path / "legacy.jsonl"
    raw = '\nnot JSON\n[]\n{"proposal_id":"first","proposal_id":"last"}\n'
    path.write_text(raw)
    assert probation.read_proposals(path) == [{"proposal_id": "last"}]
    assert path.read_text() == raw


@pytest.mark.parametrize("bad", ['{"subject":{"basket":"a","basket":"b"}}', '{"truncated":'])
def test_gmi_strict_reader_never_returns_a_partial_queue(tmp_path, bad):
    from engine.theme_graph import probation
    path = tmp_path / "proposals.jsonl"
    raw = '{"proposal_id":"first"}\n' + bad + '\n'
    path.write_text(raw)
    with pytest.raises(ValueError, match="line 2"):
        probation.read_proposals(path, strict=True)
    assert path.read_text() == raw


@pytest.mark.parametrize("kind", ["oversized", "too_deep"])
def test_gmi_overlap_cli_uses_bounded_loader_and_refuses_without_output(tmp_path, capsys, kind):
    import sys
    from scripts.explain_theme_changes import MAX_INPUT_BYTES
    from scripts.explain_theme_overlap import main
    path, output = tmp_path / "review.json", tmp_path / "report.json"
    depth = sys.getrecursionlimit() + 100
    raw = ' ' * (MAX_INPUT_BYTES + 1) if kind == "oversized" else '[' * depth + '0' + ']' * depth
    path.write_text(raw)
    assert main(["--review", str(path), "--out", str(output)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    refusal = json.loads(captured.err)
    assert refusal["code"] == "OVERLAP_EVIDENCE_UNAVAILABLE"
    if kind == "oversized":
        assert "8 MiB" in refusal["message"]
    assert not output.exists()
    assert path.read_text() == raw


@pytest.mark.parametrize("damage", ["missing", "malformed", "nonobject", "duplicate", "nested_duplicate", "too_deep"])
def test_gmi_review_drilldown_refuses_changed_raw_queue(monkeypatch, tmp_path, capsys, damage):
    """The real adapter must not weaken raw-input guarantees after worklist selection."""
    import sys
    from engine.theme_graph import store
    from scripts import list_theme_proposals as worklist_cli, query_theme_ontology as review_cli
    path, output = tmp_path / "proposals.jsonl", tmp_path / "review.json"
    row = _worklist_rows()[0]
    original = json.dumps(row) + "\n"
    path.write_text(original, encoding="utf-8")
    monkeypatch.setattr(store, "probation_path", lambda: path)
    assert worklist_cli.main(["--asof", "2026-02-01"]) == 0
    item = json.loads(capsys.readouterr().out)["items"][0]
    query = item["review_query"]
    assert query["proposal_id"] == row["proposal_id"]
    if damage == "missing":
        path.unlink()
        raw = None
    else:
        depth = sys.getrecursionlimit() + 100
        bad = {"malformed": "not JSON", "nonobject": "[]",
               "duplicate": '{"proposal_id":"a","proposal_id":"b"}',
               "nested_duplicate": '{"evidence":{"count":1,"count":2}}',
               "too_deep": "[" * depth + "0" + "]" * depth}[damage]
        raw = original + bad + "\n"
        path.write_text(raw, encoding="utf-8")
    args = ["--proposal-id", query["proposal_id"], "--asof", query["asof"],
            "--knowledge-cutoff", query["knowledge_cutoff"], "--out", str(output)]
    assert review_cli.main(args) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    refusal = json.loads(captured.err)
    assert refusal["code"] == "ONTOLOGY_QUERY_UNAVAILABLE"
    assert not output.exists()
    if raw is None:
        assert not path.exists()
    else:
        assert path.read_text(encoding="utf-8") == raw
        assert "line 2" in refusal["message"]


def test_gmi_review_drilldown_empty_queue_is_genuine_absence(monkeypatch, tmp_path, capsys):
    from engine.theme_graph import store
    from scripts import query_theme_ontology as review_cli
    path = tmp_path / "proposals.jsonl"
    path.write_text("", encoding="utf-8")
    monkeypatch.setattr(store, "probation_path", lambda: path)
    assert review_cli.main(["--proposal-id", _worklist_rows()[0]["proposal_id"],
                            "--asof", "2026-02-01"]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out)["availability"]["state"] == "PROPOSAL_NOT_FOUND"
    assert path.read_bytes() == b""


@pytest.mark.parametrize("queue_state", ["missing", "nonobject", "empty"])
def test_gmi_repository_neighborhood_distinguishes_unreadable_queue_from_empty(monkeypatch, tmp_path, capsys, queue_state):
    """The adapter's other consumer must retain graph truth without inventing queue absence."""
    from engine.theme_graph import store
    from scripts import query_theme_ontology as cli
    path = tmp_path / "proposals.jsonl"
    monkeypatch.setattr(store, "probation_path", lambda: path)
    monkeypatch.setattr(store, "read_nodes", lambda **kwargs: [_ont_node("co:us:AAA", "company")])
    monkeypatch.setattr(store, "read_node_lifecycle", lambda **kwargs: [])
    monkeypatch.setattr(store, "read_edges", lambda **kwargs: [])
    if queue_state != "missing":
        path.write_text("[]\n" if queue_state == "nonobject" else "", encoding="utf-8")
    status = cli.main(["--node-id", "co:us:AAA", "--asof", "2026-06-01"])
    captured = capsys.readouterr()
    if queue_state == "empty":
        assert status == 0 and captured.err == ""
        result = json.loads(captured.out)
        assert result["availability"]["state"] == "OK"
        assert result["counts"]["proposals"] == 0
        assert path.read_bytes() == b""
    else:
        assert status == 2 and captured.out == ""
        assert json.loads(captured.err)["code"] == "ONTOLOGY_QUERY_UNAVAILABLE"
        assert path.exists() == (queue_state == "nonobject")


@pytest.mark.parametrize("damage", ["missing_id", "missing_subject", "bad_kind", "evidence_type", "extra_field", "decision_clock", "nonfinite", "duplicate_id"])
def test_gmi_review_refuses_schema_corruption_before_absence(monkeypatch, tmp_path, capsys, damage):
    from engine.theme_graph import store
    from scripts import list_theme_proposals as worklist_cli, query_theme_ontology as review_cli
    path, output = tmp_path / "proposals.jsonl", tmp_path / "review.json"
    row = _worklist_rows()[0]
    path.write_text(json.dumps(row) + "\n")
    monkeypatch.setattr(store, "probation_path", lambda: path)
    assert worklist_cli.main(["--asof", "2026-02-01"]) == 0
    query = json.loads(capsys.readouterr().out)["items"][0]["review_query"]
    if damage == "missing_id": row.pop("proposal_id")
    elif damage == "missing_subject": row.pop("subject")
    elif damage == "bad_kind": row["kind"] = "approved"
    elif damage == "evidence_type": row["evidence"] = []
    elif damage == "extra_field": row["auto_approve"] = True
    elif damage == "decision_clock": row.update(status="rejected", adjudicated_at="2025-01-01")
    elif damage == "nonfinite": row["evidence"] = {"count": float("nan")}
    raw = json.dumps(row) + "\n"
    if damage == "duplicate_id": raw += raw
    path.write_text(raw)
    assert review_cli.main(["--proposal-id", query["proposal_id"], "--asof", query["asof"], "--out", str(output)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err)["code"] == "ONTOLOGY_QUERY_UNAVAILABLE"
    assert not output.exists() and path.read_text() == raw


# D2D inventory is a read-only discovery entry into the existing exact reader.
def _inventory_view():
    names = ["ltheme:finviz:ai", "ltheme:ths:300001", "ltheme:ths:300002", "ltheme:ths:300003"]
    nodes = [_ont_node(x, "local_theme", name="AI") for x in names]
    nodes += [_ont_node("theme:a", "theme"), _ont_node("theme:b", "theme"), _ont_node("co:us:AAA", "company")]
    edges = [_ont_edge("edge:a", "EXPRESSES", names[0], "theme:a"),
             _ont_edge("edge:b", "EXPRESSES", names[0], "theme:b"),
             _ont_edge("edge:member", "MEMBER_OF", "co:us:AAA", names[1])]
    proposed = _ont_proposal("prop:0000000000000011", {"local_theme": names[1], "canonical_theme": "theme:a"}, created="2026-01-01")
    rejected = _ont_proposal("prop:0000000000000012", {"local_theme": names[2], "canonical_theme": "theme:a"}, created="2026-01-01")
    rejected.update(status="rejected", adjudicated_at="2026-02-01")
    from engine.theme_graph import probation
    for row in (proposed, rejected):
        row["proposal_id"] = probation.proposal_id(row["kind"], row["subject"])
    return _OntologyStore(nodes=nodes, edges=edges, proposals=[proposed, rejected])


def _inventory(view=None, **kwargs):
    import importlib.util
    assert importlib.util.find_spec("engine.theme_graph.ontology_inventory"), "ontology inventory missing"
    from engine.theme_graph.ontology_inventory import compose_inventory
    from referencing import Registry, Resource
    result = compose_inventory(_inventory_view() if view is None else view,
        asof=kwargs.pop("asof", "2026-03-01"), rights_resolver=_ont_rights, **kwargs)
    root = ROOT / "contracts/theme_graph"
    schema = json.loads((root / "ontology_neighborhood.v1.schema.json").read_text())
    registry = Registry().with_resource(schema["$id"], Resource.from_contents(schema))
    schema = json.loads((root / "ontology_inventory.v1.schema.json").read_text())
    jsonschema.Draft202012Validator(schema, registry=registry).validate(result)
    return result


def test_gmi_inventory_closed_denominator_and_many_parents_without_forced_mapping():
    import copy
    view = _inventory_view(); before = copy.deepcopy(vars(view)); result = _inventory(view)
    assert result["counts"] == dict(visible=4, matching=4, returned=4, mapped=1, unmapped=3, with_proposals=2, without_proposals=2)
    assert result["counts"]["mapped"] + result["counts"]["unmapped"] == result["counts"]["visible"]
    assert sum(result["facets"]["source_family"].values()) == 4
    items = {x["node"]["node_id"]: x for x in result["items"]}
    assert items["ltheme:finviz:ai"]["canonical_mapping"]["theme_node_ids"] == ["theme:a", "theme:b"]
    assert items["ltheme:ths:300001"]["canonical_mapping"]["state"] == "UNMAPPED"
    assert items["ltheme:ths:300001"]["curation"]["state"] == "PROPOSED"
    assert items["ltheme:ths:300002"]["curation"]["state"] == "REJECTED"
    assert items["ltheme:ths:300003"]["curation"]["state"] == "NONE"
    assert items["ltheme:finviz:ai"]["rights"]["public_display_allowed"] is False
    assert vars(view) == before


def test_gmi_inventory_drilldown_is_the_existing_exact_owner_projection():
    view = _inventory_view()
    from engine.theme_graph.ontology import compose_neighborhood
    for item in _inventory(view)["items"]:
        document = compose_neighborhood(view, **item["neighborhood_query"], rights_resolver=_ont_rights)
        assert item["node"] == document["subject"]
        assert item["canonical_mapping"] == document["canonical_mapping"]
        assert item["curation"] == document["curation"]
        assert item["neighborhood_counts"] == document["counts"]


def test_gmi_inventory_uses_owner_effective_and_knowledge_clocks():
    view = _inventory_view()
    future = _ont_node("ltheme:ths:future", "local_theme"); future["computed_at"] = "2026-04-01T00:00:00Z"
    view._nodes.append(future)
    view._edges[0].update(belief_time="2026-04-01", computed_at="2026-04-01T00:00:00Z")
    result = _inventory(view, knowledge_cutoff="2026-01-15")
    assert result["counts"]["visible"] == 4
    assert result["items"][0]["canonical_mapping"]["theme_node_ids"] == ["theme:b"]
    assert result["items"][2]["curation"]["state"] == "PROPOSED"
    assert all(x["neighborhood_query"]["knowledge_cutoff"] == "2026-01-15" for x in result["items"])


def test_gmi_inventory_ratification_does_not_manufacture_graph_mapping():
    view = _inventory_view(); view._proposals[0].update(status="ratified", ratified_by="curator", adjudicated_at="2026-02-01")
    row = _inventory(view)["items"][1]
    assert row["canonical_mapping"]["state"] == "UNMAPPED"
    assert row["curation"]["state"] == "RATIFIED_NOT_MATERIALIZED"


@pytest.mark.parametrize("filters,count", [({"source_family":"ths_concepts"},3), ({"mapping":"unmapped"},3),
    ({"curation":"without_proposals"},2), ({"curation":"with_proposals"},2), ({"curation":"rejected"},1),
    ({"source_family":"unknown_owner"},0)])
def test_gmi_inventory_exact_filters_keep_full_denominator(filters, count):
    result = _inventory(**filters)
    assert result["counts"]["visible"] == 4 and result["counts"]["matching"] == count
    assert result["availability"]["state"] == ("OK" if count else "NO_MATCH")


def test_gmi_inventory_digest_bound_pages_preserve_source_order_independence():
    view = _inventory_view(); first = _inventory(view, limit=2)
    view._nodes.reverse(); view._edges.reverse(); view._proposals.reverse()
    second = _inventory(view, limit=2, offset=2, expected_snapshot=first["snapshot_sha256"])
    ids = [x["node"]["node_id"] for x in first["items"] + second["items"]]
    assert len(ids) == len(set(ids)) == 4 and ids == sorted(ids)
    assert second["page"]["next_offset"] is None
    view._proposals[0]["note"] = "changed evidence"
    with pytest.raises(ValueError, match="snapshot"):
        _inventory(view, limit=2, offset=2, expected_snapshot=first["snapshot_sha256"])


@pytest.mark.parametrize("arguments", [{"limit":0},{"limit":101},{"limit":True},{"offset":-1},{"offset":1},
    {"expected_snapshot":"wrong"},{"mapping":"approved"},{"curation":"approve"},{"source_family":" ths_concepts"}])
def test_gmi_inventory_refuses_ambiguous_selection(arguments):
    with pytest.raises(ValueError): _inventory(**arguments)


def test_gmi_inventory_refuses_duplicate_local_identity_and_malformed_proposals():
    view = _inventory_view(); view._nodes.append(dict(view._nodes[0]))
    with pytest.raises(ValueError, match="duplicate"): _inventory(view)
    view = _inventory_view(); view._proposals[0].pop("proposal_id")
    with pytest.raises(ValueError, match="proposal"): _inventory(view)


def test_gmi_inventory_unavailable_graph_is_not_an_empty_curation_queue():
    missing = _inventory(_OntologyStore())
    assert missing["availability"]["state"] == "GRAPH_UNAVAILABLE" and missing["counts"] is None
    empty = _inventory(_OntologyStore(nodes=[_ont_node("co:us:AAA", "company")]))
    assert empty["availability"]["state"] == "EMPTY" and empty["counts"]["visible"] == 0


def test_gmi_inventory_reads_each_canonical_source_only_once():
    view = _inventory_view(); calls = {}
    for name in ["read_nodes", "read_edges", "read_node_lifecycle", "read_proposals"]:
        original = getattr(view, name)
        def counted(original=original, name=name):
            calls[name] = calls.get(name, 0) + 1
            return original()
        setattr(view, name, counted)
    _inventory(view)
    assert calls == {name: 1 for name in calls}


def test_gmi_inventory_cli_json_markdown_and_output_preservation(monkeypatch, tmp_path, capsys):
    _inventory()
    from scripts import list_theme_ontology as cli
    source = tmp_path / "input.parquet"; source.write_bytes(b"source")
    monkeypatch.setattr(cli, "source_paths", lambda: [source])
    monkeypatch.setattr(cli, "RepositoryStore", _inventory_view)
    assert cli.main(["--asof", "2026-03-01", "--mapping", "unmapped"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["counts"]["matching"] == 3
    assert cli.main(["--asof", "2026-03-01", "--format", "markdown"]) == 0
    assert "UNMAPPED" in capsys.readouterr().out
    assert cli.main(["--asof", "2026-03-01", "--out", str(source)]) == 2
    assert source.read_bytes() == b"source"
    capsys.readouterr(); source.unlink()
    out = tmp_path / "new.json"
    assert cli.main(["--asof", "2026-03-01", "--out", str(out)]) == 2
    assert json.loads(capsys.readouterr().err)["code"] == "ONTOLOGY_INVENTORY_UNAVAILABLE"
    assert not out.exists()


# Real file boundaries required by structural and inventory consumers.
def _gmi_integrity_files(tmp_path, monkeypatch):
    from engine.theme_graph import store, probation
    view = _inventory_view()
    for row in view._proposals:
        row["proposal_id"] = probation.proposal_id(row["kind"], row["subject"])
    paths = {}
    for kind, values, columns in [
        ("nodes", view._nodes, store.NODE_COLUMNS),
        ("edges", view._edges, store.EDGE_COLUMNS),
        ("node_lifecycle", [], store.NODE_LIFECYCLE_COLUMNS),
    ]:
        path = tmp_path / (kind + ".parquet")
        pd.DataFrame(values, columns=columns).to_parquet(path, index=False)
        monkeypatch.setattr(store, kind + "_path", lambda path=path: path)
        paths[kind] = path
    path = tmp_path / "proposals.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in view._proposals))
    monkeypatch.setattr(store, "probation_path", lambda: path)
    paths["proposals"] = path
    return paths


@pytest.mark.parametrize("kind", ["nodes", "edges", "node_lifecycle"])
@pytest.mark.parametrize("damage", ["truncated", "missing", "wrong_columns"])
def test_gmi_integrity_graph_file_refuses_before_inventory(tmp_path, monkeypatch, capsys, kind, damage):
    from scripts import list_theme_ontology as cli
    paths = _gmi_integrity_files(tmp_path, monkeypatch)
    path = paths[kind]
    if damage == "missing": path.unlink()
    elif damage == "truncated": path.write_bytes(b"PAR1broken")
    else: pd.DataFrame({"unrelated": [1]}).to_parquet(path, index=False)
    before = path.read_bytes() if path.exists() else None
    output = tmp_path / "inventory.json"
    assert cli.main(["--asof", "2026-03-01", "--out", str(output)]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and not output.exists()
    assert json.loads(captured.err)["code"] == "ONTOLOGY_INVENTORY_UNAVAILABLE"
    assert (path.read_bytes() if path.exists() else None) == before


def test_gmi_integrity_valid_empty_parquet_is_not_corruption(tmp_path, monkeypatch, capsys):
    from engine.theme_graph import store
    from scripts import list_theme_ontology as cli
    paths = _gmi_integrity_files(tmp_path, monkeypatch)
    pd.DataFrame(columns=store.EDGE_COLUMNS).to_parquet(paths["edges"], index=False)
    assert cli.main(["--asof", "2026-03-01"]) == 0
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert captured.err == "" and result["counts"]["mapped"] == 0
    assert result["counts"]["visible"] == 4


@pytest.mark.parametrize("damage", ["subject", "kind", "id"])
def test_gmi_integrity_proposal_payload_identity_refuses(tmp_path, monkeypatch, capsys, damage):
    from engine.theme_graph import probation
    from scripts import list_theme_proposals as worklist, query_theme_ontology as review
    paths = _gmi_integrity_files(tmp_path, monkeypatch)
    rows = probation.read_proposals(paths["proposals"], strict=True)
    row = rows[0]; original_id = row["proposal_id"]
    if damage == "subject": row["subject"]["local_theme"] = "ltheme:finviz:altered"
    elif damage == "kind": row["kind"] = "split"
    else: row["proposal_id"] = "prop:" + "0" * 16
    raw = "".join(json.dumps(r) + "\n" for r in rows); paths["proposals"].write_text(raw)
    for cli, args in [(worklist, ["--asof", "2026-03-01"]),
                      (review, ["--proposal-id", original_id, "--asof", "2026-03-01"])]:
        assert cli.main(args) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and "identity" in json.loads(captured.err)["message"]
    assert paths["proposals"].read_text() == raw


# Source-native structural references; never a new classification master.
def _gmi_structure_view():
    company = _ont_node("co:us:AAA", "company")
    sector = _ont_node("basket:baskets:us_sector_tech", "basket", name="Technology")
    sector["external_ids"] = json.dumps({"suite":"baskets", "basket_id":"us_sector_tech"})
    other = _ont_node("basket:baskets:us_sector_energy", "basket", name="Energy")
    other["external_ids"] = json.dumps({"suite":"baskets", "basket_id":"us_sector_energy"})
    local = _ont_node("ltheme:finviz:ai", "local_theme", name="Technology")
    local["source_meta"] = json.dumps({"source_family":"finviz_themes", "source_local_id":"ai",
        "parent_source_key":"Artificial Intelligence", "parent_source_label":"Artificial Intelligence"})
    theme = _ont_node("theme:ai", "theme")
    edges = [_ont_edge("e:tech", "MEMBER_OF", company["node_id"], sector["node_id"]),
             _ont_edge("e:energy", "MEMBER_OF", company["node_id"], other["node_id"]),
             _ont_edge("e:local", "MEMBER_OF", company["node_id"], local["node_id"]),
             _ont_edge("e:mapping", "EXPRESSES", local["node_id"], theme["node_id"])]
    return _OntologyStore(nodes=[company,sector,other,local,theme], edges=edges)


def _gmi_structure_owner():
    return {"unmapped_baskets":[{"id":"us_sector_tech", "reason":"Sector context; not a theme."},
        {"id":"us_sector_energy", "reason":"Sector context; not a theme."}]}


def _gmi_structure(view=None, node_id="co:us:AAA", **kwargs):
    import importlib.util
    assert importlib.util.find_spec("engine.theme_graph.structural_navigation"), "structural navigation missing"
    from engine.theme_graph.structural_navigation import compose_structure
    from referencing import Registry,Resource
    result = compose_structure(_gmi_structure_view() if view is None else view, node_id=node_id,
        asof=kwargs.pop("asof","2026-06-01"), owner_document=kwargs.pop("owner_document",_gmi_structure_owner()),
        owner_sha256="a"*64, rights_resolver=_ont_rights, **kwargs)
    root=ROOT/"contracts/theme_graph"
    existing=json.loads((root/"ontology_neighborhood.v1.schema.json").read_text())
    registry=Registry().with_resource(existing["$id"],Resource.from_contents(existing))
    schema=json.loads((root/"structural_context.v1.schema.json").read_text())
    jsonschema.Draft202012Validator(schema,registry=registry).validate(result)
    return result


def test_gmi_structure_preserves_all_sector_and_local_parent_references():
    import copy
    view=_gmi_structure_view(); before=copy.deepcopy(vars(view)); result=_gmi_structure(view)
    assert [r["basket_id"] for r in result["sector_references"]] == ["us_sector_energy","us_sector_tech"]
    assert result["counts"] == {"sector_references":2,"source_parent_references":1,"member_queries":0}
    parent=result["source_parent_references"][0]
    assert parent["parent_source_key"] == "Artificial Intelligence"
    assert parent["reference_kind"] == "SOURCE_LOCAL_PARENT_REFERENCE"
    assert parent["rights"]["public_display_allowed"] is False
    assert result["historical_classification_claim"] is False
    assert result["owner_reference_basis"] == "LATEST_STORED_CROSSWALK"
    assert vars(view) == before


def test_gmi_structure_round_trip_sector_members_and_local_mapping():
    company=_gmi_structure()
    for ref in company["sector_references"]:
        sector=_gmi_structure(node_id=ref["node_id"])
        assert sector["subject_reference"]["basket_id"] == ref["basket_id"]
        assert sector["member_queries"] == [{"node_id":"co:us:AAA","asof":"2026-06-01","knowledge_cutoff":"2026-06-01"}]
    local=_gmi_structure(node_id="ltheme:finviz:ai")
    assert local["neighborhood"]["canonical_mapping"]["theme_node_ids"] == ["theme:ai"]
    assert len(local["source_parent_references"]) == 1
    assert local["sector_references"] == []


@pytest.mark.parametrize("damage", ["unregistered", "different_suite", "id_mismatch", "name_only"])
def test_gmi_structure_never_classifies_by_label_or_unregistered_prefix(damage):
    view=_gmi_structure_view(); owner=_gmi_structure_owner(); sector=view._nodes[1]
    if damage=="unregistered": owner["unmapped_baskets"] = owner["unmapped_baskets"][1:]
    elif damage=="different_suite": sector["external_ids"]=json.dumps({"suite":"baskets_hk","basket_id":"us_sector_tech"})
    elif damage=="id_mismatch": sector["external_ids"]=json.dumps({"suite":"baskets","basket_id":"us_sector_energy"})
    else: sector["external_ids"]="{}"
    result=_gmi_structure(view,owner_document=owner)
    assert [r["basket_id"] for r in result["sector_references"]] == ["us_sector_energy"]


@pytest.mark.parametrize("cutoff,asof,expected", [("2026-02-01","2026-06-01",2),("2026-06-01","2026-06-01",1),("2026-06-01","2026-02-01",2)])
def test_gmi_structure_delegates_membership_clocks_to_existing_reader(cutoff,asof,expected):
    view=_gmi_structure_view(); correction=dict(view._edges[0])
    correction.update(valid_to="2026-03-01",belief_time="2026-04-01",computed_at="2026-04-01T00:00:00Z")
    view._edges.append(correction)
    assert len(_gmi_structure(view,knowledge_cutoff=cutoff,asof=asof)["sector_references"]) == expected


def test_gmi_structure_proposals_never_create_sector_membership():
    view=_gmi_structure_view(); view._edges=[]
    view._proposals=[_ont_proposal("prop:0000000000000001",{"company":"co:us:AAA","basket":"basket:baskets:us_sector_tech"})]
    result=_gmi_structure(view)
    assert result["sector_references"] == []
    assert result["coverage"]["industry"]["state"] == "OWNER_NOT_BOUND"
    assert result["coverage"]["subindustry"]["state"] == "OWNER_NOT_BOUND"


@pytest.mark.parametrize("owner", [{},{"unmapped_baskets":None},{"unmapped_baskets":[{"id":"us_sector_tech","reason":"x"}]*2}])
def test_gmi_structure_ambiguous_owner_is_not_missing_classification(owner):
    with pytest.raises(ValueError): _gmi_structure(owner_document=owner)


def test_gmi_structure_absent_graph_subject_remains_absent():
    result=_gmi_structure(node_id="co:us:UNKNOWN")
    assert result["neighborhood"]["availability"]["state"] == "SUBJECT_NOT_FOUND"
    assert result["sector_references"] == [] and result["source_parent_references"] == []


def test_gmi_structure_existing_cli_mode_preserves_output_and_owner_input(monkeypatch,tmp_path,capsys):
    _gmi_structure()
    from scripts import query_theme_ontology as cli
    from engine.theme_graph import structural_navigation as structure
    owner=tmp_path/"crosswalk.yml";owner.write_text("unmapped_baskets:\n  - id: us_sector_tech\n    reason: Sector context\n")
    monkeypatch.setattr(structure,"CROSSWALK_PATH",owner)
    monkeypatch.setattr(cli,"RepositoryStore",_gmi_structure_view)
    args=["--node-id","co:us:AAA","--asof","2026-06-01","--structure"]
    assert cli.main(args)==0
    result=json.loads(capsys.readouterr().out)
    assert result["sector_references"][0]["basket_id"]=="us_sector_tech"
    assert cli.main(args+["--format","markdown"])==0
    assert "OWNER_NOT_BOUND" in capsys.readouterr().out
    original=owner.read_bytes()
    assert cli.main(args+["--out",str(owner)])==2
    assert owner.read_bytes()==original
    capsys.readouterr();owner.unlink()
    assert cli.main(args)==2 and capsys.readouterr().out==""



def test_gmi_structure_parent_family_must_match_the_existing_node_owner():
    view = _gmi_structure_view()
    metadata=json.loads(view._nodes[3]["source_meta"])
    metadata["source_family"]="unrelated_owner"
    view._nodes[3]["source_meta"]=json.dumps(metadata)
    with pytest.raises(ValueError,match="source-local"):
        _gmi_structure(view)


@pytest.mark.parametrize("raw", ["unmapped_baskets: []\nunmapped_baskets: []\n", "unmapped_baskets: [", " "*(1024*1024+1)])
def test_gmi_structure_owner_loader_rejects_ambiguous_or_unreadable_input(monkeypatch,tmp_path,raw):
    from engine.theme_graph import structural_navigation as module
    path=tmp_path/"owner.yml";path.write_text(raw)
    monkeypatch.setattr(module,"CROSSWALK_PATH",path)
    with pytest.raises(ValueError):module.load_structural_owner()
    assert path.read_text()==raw

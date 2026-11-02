"""Product projection over finalized selection-cohort read packets."""
import ast
import copy
import json
from pathlib import Path

import jsonschema
import pytest
import yaml

from engine.theme_graph.selection_cohort import (
    FLAGS,
    compose_selection_cohort,
    validate_selection_cohort,
)
from engine.theme_graph import rights
from engine.theme_graph.selection_cohort_projection import (
    PROJECTION_LIMITATIONS,
    SCHEMA,
    project_selection_cohort_for_product,
    write_product_projection,
)
from tests.test_theme_graph_selection_cohort import (
    OLD,
    SHA,
    inputs,
    member,
    selection,
    state,
)

ROOT = Path(__file__).resolve().parents[1]
PROJECTION_SCHEMA_PATH = ROOT / "contracts/theme_graph/selection_cohort_projection.v1.schema.json"


def _schema_validator():
    schema = json.loads(PROJECTION_SCHEMA_PATH.read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(schema)


def _wrapper(explanation):
    return dict(
        schema="mastermind.selection_cohort_source.v1",
        status="AVAILABLE",
        reason_codes=[],
        receipt={"placeholder": True},
        explanation=explanation,
        **{flag: False for flag in FLAGS},
    )


def _fixture_read_packet(n=4):
    kw = inputs(n)
    for i, sid in enumerate([f"owner-row-{j}" for j in range(n)]):
        reasons = kw["membership_reads"][sid].get("memberships", [])
        if i == 1:
            reasons.append(member(i, "ltheme:finviz:ai"))
            kw["state_reads"]["ltheme:finviz:ai"] = state("ltheme:finviz:ai")
        if i == 2:
            reasons.append(member(i, "basket:baskets:house"))
    packet = compose_selection_cohort(selection(n), **kw)
    validate_selection_cohort(packet)
    return packet


def test_t1_schema_contract_and_rejects_forbidden_fields():
    packet = _fixture_read_packet()
    out = project_selection_cohort_for_product(_wrapper(packet))
    validator = _schema_validator()
    validator.validate(out)
    with pytest.raises(jsonschema.ValidationError):
        validator.validate({**out, "extra": True})
    with pytest.raises(jsonschema.ValidationError):
        validator.validate({**out, "can_rank": True})
    bad_row = dict(out["selected"][0], owner_score=1)
    with pytest.raises(jsonschema.ValidationError):
        validator.validate({**out, "selected": [bad_row] + out["selected"][1:]})


def test_t2_order_preservation_byte_identical():
    packet = _fixture_read_packet(4)
    out = project_selection_cohort_for_product(_wrapper(packet))
    assert json.dumps([r["selection_id"] for r in out["selected"]], sort_keys=True) == json.dumps(
        [r["source"]["selection_id"] for r in packet["selected"]], sort_keys=True
    )
    for prow, srow in zip(out["selected"], packet["selected"]):
        assert json.dumps(prow["reason_codes"], sort_keys=True) == json.dumps(
            srow["reason_codes"], sort_keys=True
        )
        assert json.dumps(prow["original_reasons"], sort_keys=True) == json.dumps(
            srow["source"]["original_reasons"], sort_keys=True
        )
        expected_display = []
        sid = srow["source"]["selection_id"]
        for concept in packet["concepts"]:
            if sid not in concept.get("selected_ids", []):
                continue
            node_id = concept["node_id"]
            family = rights.family_for_node_id(node_id)
            if family is None:
                continue
            if not rights.licensing_for_family(family)[1]:
                continue
            expected_display.append({"node_id": node_id, "kind": concept["kind"]})
        assert json.dumps(prow["concepts_display"], sort_keys=True) == json.dumps(
            expected_display, sort_keys=True
        )


def test_t3_authority_reasserted_false_on_tampered_input():
    packet = _fixture_read_packet(3)
    wrapper = _wrapper(packet)
    wrapper["can_rank"] = True
    packet["can_escalate"] = True
    out = project_selection_cohort_for_product(wrapper)
    assert out["authority_ceiling"] == "research_internal_only"
    assert all(out[f] is False for f in FLAGS)
    _schema_validator().validate(out)


def _canonical_theme_member(i: int, node: str = "theme:canonical"):
    return dict(
        member_node_id=f"co:fixture:{i}",
        node_id=node,
        kind="canonical_theme",
        source_family=None,
        native_id=None,
        node_kind="theme",
        canonical_node_ids=[node],
        canonical_nodes=[
            {
                "node_id": node,
                "kind": "theme",
                "receipt_ref": f"fixture://canonical/{node}",
                "receipt_sha256": SHA,
            }
        ],
        evidence_ref=f"fixture://membership/{i}/{node}",
        evidence_sha256=SHA,
        effective_from=OLD,
        effective_until=None,
        known_from=OLD,
        rights_status="ALLOWED",
        rights_receipt_ref="fixture://rights/allowed",
    )


def _finviz_member(i: int, slug: str = "ai"):
    node = f"ltheme:finviz:{slug}"
    row = member(i, node)
    row["source_family"] = "finviz"
    row["native_id"] = slug
    return row


def test_t4_rights_fail_closed_counts_and_no_withheld_leakage():
    kw = inputs(3)
    kw["membership_reads"]["owner-row-0"]["memberships"] = [
        member(0, "ltheme:ths:battery"),
        _finviz_member(0),
        _canonical_theme_member(0),
    ]
    kw["state_reads"]["ltheme:finviz:ai"] = state("ltheme:finviz:ai")
    packet = compose_selection_cohort(selection(3), **kw)
    validate_selection_cohort(packet)
    out = project_selection_cohort_for_product(_wrapper(packet))
    concept_rights = out["concept_rights"]
    assert concept_rights["n_concepts_total"] == 3
    assert concept_rights["n_concepts_displayable"] == 0
    assert concept_rights["n_concepts_withheld"] == 3
    assert concept_rights["withheld_reasons"]["RIGHTS_INTERNAL_ONLY"] == 2
    assert concept_rights["withheld_reasons"]["RIGHTS_FAMILY_UNRESOLVED"] == 1
    dumped = json.dumps(out, sort_keys=True)
    for forbidden in ("ltheme:ths:battery", "ltheme:finviz:ai", "theme:canonical"):
        assert forbidden not in dumped
    basket_family_display = rights.family_for_node_id("basket:baskets:house")
    assert basket_family_display == "mastermind_curated"
    assert rights.licensing_for_family(basket_family_display)[1] is True
    row0 = out["selected"][0]
    assert row0["n_concepts"] == 3
    assert row0["concepts_display"] == []
    assert row0["n_concepts_withheld"] == 3


def test_t4b_displayable_concept_via_rights_path(tmp_path):
    reg = yaml.safe_load(rights.registry_path().read_text())
    reg["families"]["finviz_themes"]["rights_class"] = "derived_display_ok"
    reg_path = tmp_path / "theme_sources.yml"
    reg_path.write_text(yaml.safe_dump(reg))
    assert rights.licensing_for_family("finviz_themes", path=reg_path)[1] is True

    kw = inputs(3)
    kw["membership_reads"]["owner-row-0"]["memberships"] = [
        member(0, "ltheme:ths:battery"),
        _finviz_member(0),
        _canonical_theme_member(0),
    ]
    kw["membership_reads"]["owner-row-2"]["memberships"] = [_finviz_member(2)]
    kw["state_reads"]["ltheme:finviz:ai"] = state("ltheme:finviz:ai")
    packet = compose_selection_cohort(selection(3), **kw)
    validate_selection_cohort(packet)

    out = project_selection_cohort_for_product(_wrapper(packet), rights_path=reg_path)
    _schema_validator().validate(out)

    concept_rights = out["concept_rights"]
    assert concept_rights == {
        "n_concepts_total": 3,
        "n_concepts_displayable": 1,
        "n_concepts_withheld": 2,
        "withheld_reasons": {
            "RIGHTS_INTERNAL_ONLY": 1,
            "RIGHTS_FAMILY_UNRESOLVED": 1,
        },
    }
    row0, row1, row2 = out["selected"]
    assert row0["n_concepts"] == 3
    assert json.dumps(row0["concepts_display"]) == json.dumps(
        [{"node_id": "ltheme:finviz:ai", "kind": "local_theme"}]
    )
    assert row0["n_concepts_withheld"] == 2
    assert row1["n_concepts"] == 1
    assert row1["concepts_display"] == []
    assert row1["n_concepts_withheld"] == 1
    assert row2["n_concepts"] == 1
    assert json.dumps(row2["concepts_display"]) == json.dumps(
        [{"node_id": "ltheme:finviz:ai", "kind": "local_theme"}]
    )
    assert row2["n_concepts_withheld"] == 0

    dumped = json.dumps(out, sort_keys=True)
    assert "ltheme:ths:battery" not in dumped
    assert "theme:canonical" not in dumped
    for concept in packet["concepts"]:
        if concept["node_id"] == "ltheme:ths:battery":
            assert concept.get("native_id") not in dumped
            for cid in concept.get("canonical_node_ids") or []:
                if cid:
                    assert cid not in dumped
    for item in row0["concepts_display"] + row2["concepts_display"]:
        assert set(item.keys()) == {"node_id", "kind"}

    out_no_rights = project_selection_cohort_for_product(_wrapper(packet))
    assert out_no_rights["concept_rights"]["n_concepts_displayable"] == 0

    reg_bad = yaml.safe_load(rights.registry_path().read_text())
    reg_bad["families"]["finviz_themes"]["rights_class"] = "bogus_class"
    reg_bad_path = tmp_path / "theme_sources_bogus.yml"
    reg_bad_path.write_text(yaml.safe_dump(reg_bad))
    out_bogus = project_selection_cohort_for_product(
        _wrapper(packet), rights_path=reg_bad_path
    )
    assert out_bogus["concept_rights"]["n_concepts_displayable"] == 0
    assert out_bogus["concept_rights"]["withheld_reasons"]["RIGHTS_INTERNAL_ONLY"] == 2


def test_t5_honest_unavailable_paths():
    validator = _schema_validator()
    cases = [
        (None, "WRAPPER_MISSING"),
        (dict(schema="mastermind.selection_cohort_source.v1", status="UNAVAILABLE", reason_codes=["NO_SOURCE"], explanation=None), "SOURCE_UNAVAILABLE:NO_SOURCE"),
        (dict(schema="mastermind.selection_cohort_source.v1", status="AVAILABLE", reason_codes=[], explanation=None), "EXPLANATION_UNAVAILABLE"),
        (_wrapper(dict(schema="wrong.schema/v1")), "READ_PACKET_INVALID"),
    ]
    for wrapper, reason in cases:
        out = project_selection_cohort_for_product(wrapper)
        assert out["availability"] == {"status": "UNAVAILABLE", "overlap": "UNAVAILABLE"}
        assert out["unavailable_reason"] == reason
        assert out["n_selected"] == 0 and out["selected"] == []
        assert out["limitations"] == list(PROJECTION_LIMITATIONS)
        validator.validate(out)
    bad = _fixture_read_packet(3)
    bad["selected"][0]["source"]["selection_id"] = "tampered"
    out = project_selection_cohort_for_product(_wrapper(bad))
    assert out["unavailable_reason"] == "READ_PACKET_INVALID"


def test_t6_purity_and_no_clock_or_network_imports():
    packet = _fixture_read_packet(3)
    wrapper = _wrapper(packet)
    a = project_selection_cohort_for_product(copy.deepcopy(wrapper))
    b = project_selection_cohort_for_product(copy.deepcopy(wrapper))
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    source = (ROOT / "engine/theme_graph/selection_cohort_projection.py").read_text()
    assert "datetime.now(" not in source
    assert "time.time(" not in source
    assert "utcnow(" not in source
    assert "requests" not in source
    assert "urllib" not in source


def test_t7_writer_paths_market_guard_and_builder_seams(tmp_path):
    packet = _fixture_read_packet(3)
    us_path = write_product_projection(tmp_path, "us", _wrapper(packet))
    cn_path = write_product_projection(tmp_path, "cn", None)
    assert us_path == tmp_path / "neuralwebdata" / "selection_cohort" / "us.json"
    assert cn_path == tmp_path / "neuralwebdata" / "selection_cohort" / "cn.json"
    expected = (
        json.dumps(
            project_selection_cohort_for_product(_wrapper(packet)),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
        + b"\n"
    )
    assert us_path.read_bytes() == expected
    with pytest.raises(ValueError):
        write_product_projection(tmp_path, "xx", None)
    us_src = (ROOT / "scripts/build_site.py").read_text()
    cn_src = (ROOT / "scripts/build_china.py").read_text()
    assert us_src.count('write_product_projection(site, "us", vm.get("us_selection_cohort_internal") or _us_w3c_refusal)') == 1
    assert cn_src.count('write_product_projection(site, "cn", vm.get("cn_selection_cohort_internal") or _cn_w3c_refusal)') == 1
    assert us_src.count('write_product_projection(site, "us", vm.get("us_selection_cohort_internal"))') == 0
    assert cn_src.count('write_product_projection(site, "cn", vm.get("cn_selection_cohort_internal"))') == 0
    ast.parse(us_src)
    ast.parse(cn_src)

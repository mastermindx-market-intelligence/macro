"""A new reviewed pass can advance header clocks without rewriting old rows."""
from copy import deepcopy
import json
import pytest
from engine.government_revenue import program_ontology as po
from scripts import curate_government_program_ontology as curator
from tests.test_government_program_oversight import oversight_graph, capacity_claim
from tests.fixtures.government_program_ontology import builders as b

NOW = '2026-10-14T12:10:00+00:00'


def test_explicit_forward_header_clocks_admit_new_known_claim_without_rewriting_history(tmp_path):
    graph = oversight_graph()
    prior = deepcopy(graph)
    target = tmp_path / 'program_ontology.json'
    target.write_text(json.dumps(graph))
    row = capacity_claim(graph, known_at=NOW, valid_from=NOW)
    worksheet = b.worksheet(reviewed_at=NOW, coverage=[{'scope':'public_capacity','subject_type':'program','subject_id':row['program_id']}], rows=[{'action':'admit','target_kind':'public_capacity_assertion','candidate_row':row}])
    source = tmp_path / 'worksheet.json'; source.write_text(json.dumps(worksheet))
    result = curator.curate_worksheet(source, target_path=target, graph_known_at=NOW, graph_effective_at=NOW)
    assert result['rejected_count'] == 0 and result['written']
    stored = json.loads(target.read_text())
    assert stored['graph_known_at'] == stored['graph_effective_at'] == NOW
    assert stored['graph_id'] == prior['graph_id']
    for key in ['evidence','programs','role_assertions','milestones','overrides','public_oversight_assertions']:
        assert stored[key] == prior[key]
    assert stored['public_capacity_assertions'] == [row]
    assert po.load_program_ontology_graph(stored)


@pytest.mark.parametrize('field,value', [('graph_known_at','2020-01-01T00:00:00+00:00'),('graph_effective_at','2020-01-01T00:00:00+00:00'),('graph_known_at','2026-10-14T12:10:00Z'),('graph_effective_at','not-a-date'),('graph_known_at',' 2026-10-14T12:10:00+00:00'),('graph_effective_at','2026-02-31T00:00:00+00:00')])
def test_explicit_invalid_or_backward_header_clock_refuses_without_write(tmp_path,field,value):
    target = tmp_path / 'program_ontology.json'; target.write_text(json.dumps(oversight_graph()))
    before = target.read_bytes()
    source = tmp_path / 'worksheet.json'; source.write_text(json.dumps(b.worksheet()))
    with pytest.raises(curator.CurateError):
        curator.curate_worksheet(source,target_path=target,**{field:value})
    assert target.read_bytes() == before


def test_omitted_clocks_preserve_existing_artifact(tmp_path):
    graph = oversight_graph()
    target = tmp_path / "program_ontology.json"
    target.write_text(json.dumps(graph))
    loaded = curator._load_base_graph(target, graph_id=None, graph_known_at=None, graph_effective_at=None)
    assert loaded == graph
    loaded["programs"].clear()
    assert json.loads(target.read_text()) == graph


def test_forward_check_only_keeps_original_file(tmp_path):
    target = tmp_path / "program_ontology.json"
    graph = oversight_graph(); target.write_text(json.dumps(graph))
    before = target.read_bytes()
    source = tmp_path / "worksheet.json"
    source.write_text(json.dumps(b.worksheet(reviewed_at=NOW)))
    result = curator.curate_worksheet(source, target_path=target, graph_known_at=NOW, graph_effective_at=NOW, check_only=True)
    assert result["rejected_count"] == 0 and result["written"] is False
    assert target.read_bytes() == before

"""The sole producer's ACTIVITY_MEMBERSHIP_STATE narrow mode (GMI M2 step 1).

ORCH-PIPE 2026-10-22: ``python -m scripts.build_thematic_state --mode
ACTIVITY_MEMBERSHIP_STATE`` folds the committed activity-membership history events
(``data/theme_graph/probation/activity_history_events.jsonl``), projects the CURRENT
beliefs, and writes ONE display/diagnostic artifact
(``data/theme_graph/activity_membership_state.v1.json``) — NOT_QUALIFIED by
construction. LEGACY is byte-identical with and without a prior activity run.
"""
from __future__ import annotations

import ast
import datetime as dt
import json
import re
import shutil
import sys
from pathlib import Path

import pytest

from engine.neuralweb import envelope
from engine.neuralweb import theme_state_generation as g
from lib import config
from scripts import build_thematic_state as builder
from tests.test_theme_graph_activity_membership_history import MU_NODE, T1, TARGET, _append
from tests.test_theme_state_generation import artifact
from tests.test_theme_state_production import EMITTED, production_world  # noqa: F401

REPO = Path(__file__).resolve().parents[1]
MODE = "ACTIVITY_MEMBERSHIP_STATE"
ARTIFACT = Path("data/theme_graph/activity_membership_state.v1.json")
EVENTS = Path("data/theme_graph/probation/activity_history_events.jsonl")
EDGES_SCHEMA = REPO / "contracts/theme_graph/edges.v1.schema.json"
# After every fixture event clock (T1 = 2026-10-11), zoned so the fold admits it.
ACT_STAMP = "2026-10-19T00:00:00+00:00"
WARN = "::warning title=gmi-activity-membership-state::"
TIMING_RE = (r"\[thematic_state\] activity_membership_state timing read_s=\d+\.\d{3} "
             r"fold_s=\d+\.\d{3} serialize_s=\d+\.\d{3} bytes=\d+ peak_rss_mib=(\d+|na)")
AUTHORITY_FALSE = {"may_rank": False, "may_size": False, "may_gate": False,
                   "may_publish": False, "may_materialize_edges": False,
                   "may_qualify": False}


@pytest.fixture(autouse=True)
def nightly(monkeypatch):
    monkeypatch.setenv("COLLECT_LANE", "nightly")


def _legacy_build(root, monkeypatch):
    monkeypatch.setattr(builder, "compose", lambda **kw: artifact())
    return builder.build(root, mode="LEGACY", generated_at=EMITTED)


def _tree(root):
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(Path(root).rglob("*")) if p.is_file()}


def _forbid(monkeypatch, calls, owner, *names):
    def make(name):
        def spy(*args, **kwargs):
            calls.append(name)
            raise AssertionError(f"{name} must not be called")
        return spy

    for name in names:
        monkeypatch.setattr(owner, name, make(name))


def _seed_graph(root, monkeypatch, *, edges=None):
    """A tiny strict-readable graph in the world's own store (nodes MU + target)."""
    from engine.theme_graph import store

    monkeypatch.setattr(config, "data_dir", lambda: Path(root) / "data")
    nodes = [
        {"node_id": MU_NODE, "kind": "company", "name_en": "Fixture Micro",
         "computed_at": ACT_STAMP, "engine_version": "theme_graph.v1"},
        {"node_id": TARGET, "kind": "theme", "name_en": "Fixture Theme",
         "computed_at": ACT_STAMP, "engine_version": "theme_graph.v1"},
    ]
    assert store.write_nodes(nodes, lane="nightly") == 2
    if edges:
        assert store.write_edges(edges, lane="nightly") == len(edges)


def _events_bytes(events):
    return b"".join(json.dumps(e, sort_keys=True).encode("utf-8") + b"\n" for e in events)


def _seed_events(root, events):
    path = root / EVENTS
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_events_bytes(events))


def _seed(root, monkeypatch, *, events=(), edges=None):
    _seed_graph(root, monkeypatch, edges=edges)
    if events:
        _seed_events(root, events)


def _baked_activity_edge():
    """The store row a nightly bake would have carried for the projected belief."""
    from engine.theme_graph import materialize

    return {
        "edge_id": materialize.edge_id_for("MEMBER_OF", MU_NODE, TARGET, T1[:10]),
        "type": "MEMBER_OF", "src": MU_NODE, "dst": TARGET,
        "valid_from": T1[:10], "valid_to": None, "evidence_time": T1[:10],
        "belief_time": ACT_STAMP[:10], "era": "observed", "source_class": "curated",
        "date_provenance": "activity_history", "evidence_refs": [],
        "confidence_basis": "activity_history.v1", "computed_at": ACT_STAMP,
        "engine_version": "theme_graph.v1",
    }


def _artifact(root):
    return json.loads((root / ARTIFACT).read_text(encoding="utf-8"))


# ------------------------------------------------------------------ positive paths


def test_absent_events_file_writes_honest_empty_artifact(production_world, monkeypatch, capsys):
    _seed_graph(production_world, monkeypatch)
    assert builder.build(production_world, mode=MODE, generated_at=ACT_STAMP) == 0
    payload = _artifact(production_world)
    assert payload["schema"] == "gmi.activity_membership_state/v1"
    assert payload["mode"] == MODE
    assert payload["generated_at"] == ACT_STAMP
    assert payload["events_path"] == EVENTS.as_posix()
    assert payload["events_sha256"] is None and payload["event_count"] == 0
    assert payload["fold"] == {"current": 0, "history": 0, "retained": 0, "refused": 0,
                               "excluded_after_cutoff": 0, "refused_rows": []}
    assert payload["projected_edges"] == [] and payload["projected_evidence_count"] == 0
    assert payload["projection_refusals"] == []
    assert payload["graph_agreement"]["status"] == "AGREE"
    assert payload["graph_agreement"]["graph_activity_count"] == 0
    assert payload["graph_agreement"]["projected_count"] == 0
    assert payload["graph_agreement"]["missing_in_graph"] == []
    assert payload["graph_agreement"]["extra_in_graph"] == []
    assert payload["graph_agreement"]["rule"] == "latest_belief MEMBER_OF activity_history valid_to null"
    assert payload["qualification"] == {"status": "NOT_QUALIFIED",
                                        "reason_codes": ["D2E_UNSEALED"]}
    assert payload["authority"] == AUTHORITY_FALSE
    out = capsys.readouterr().out
    assert "activity_membership_state=written" in out
    assert WARN not in out


def test_empty_events_file_hashes_the_empty_ledger(production_world, monkeypatch):
    import hashlib

    _seed_graph(production_world, monkeypatch)
    _seed_events(production_world, [])
    assert builder.build(production_world, mode=MODE, generated_at=ACT_STAMP) == 0
    payload = _artifact(production_world)
    assert payload["event_count"] == 0
    assert payload["events_sha256"] == hashlib.sha256(b"").hexdigest()
    assert payload["projected_edges"] == []


def test_granted_accept_append_projects_one_contract_valid_member_of(production_world, monkeypatch):
    import jsonschema

    event = _append()  # GRANTED + ACCEPT, MU -> theme:hbm_packaging
    _seed(production_world, monkeypatch, events=[event])
    assert builder.build(production_world, mode=MODE, generated_at=ACT_STAMP) == 0
    payload = _artifact(production_world)
    (row,) = payload["projected_edges"]
    assert set(row) == {
        "edge_id", "type", "src", "dst", "valid_from", "valid_to", "evidence_time",
        "belief_time", "era", "source_class", "date_provenance", "evidence_refs",
        "confidence_basis", "economic_share", "trading_beta", "attention_share",
        "economic_share_formula_id", "trading_beta_formula_id", "attention_share_formula_id",
        "economic_share_display", "trading_beta_display", "attention_share_display",
        "computed_at", "engine_version"}
    assert row["type"] == "MEMBER_OF" and row["src"] == MU_NODE and row["dst"] == TARGET
    assert row["date_provenance"] == "activity_history"
    assert row["confidence_basis"] == "activity_history.v1"
    assert row["valid_from"] == T1[:10] and row["valid_to"] is None
    assert row["belief_time"] == ACT_STAMP[:10] and row["computed_at"] == ACT_STAMP
    assert row["era"] == "observed" and row["source_class"] == "curated"
    jsonschema.Draft202012Validator(
        json.loads(EDGES_SCHEMA.read_text(encoding="utf-8"))).validate(row)
    assert payload["projected_evidence_count"] == 1
    assert payload["projection_refusals"] == []
    # The graph carries no activity edge yet: the projection is reported, not agreed.
    assert payload["graph_agreement"]["status"] == "DISAGREE"
    assert payload["graph_agreement"]["missing_in_graph"] == [row["edge_id"]]
    assert payload["graph_agreement"]["missing_in_graph_count"] == 1
    assert payload["graph_agreement"]["extra_in_graph"] == []
    # The mode only ever writes its own artifact; the store parquets are untouched.
    from engine.theme_graph import store

    assert store.read_edges(latest_belief=True)["edge_id"].tolist() == []


def test_graph_carrying_the_projected_edge_agrees(production_world, monkeypatch):
    _seed(production_world, monkeypatch, events=[_append()],
          edges=[_baked_activity_edge()])
    assert builder.build(production_world, mode=MODE, generated_at=ACT_STAMP) == 0
    payload = _artifact(production_world)
    (row,) = payload["projected_edges"]
    assert payload["graph_agreement"]["status"] == "AGREE"
    assert payload["graph_agreement"]["missing_in_graph"] == []
    assert payload["graph_agreement"]["extra_in_graph"] == []
    assert payload["graph_agreement"]["graph_activity_count"] == 1
    assert payload["graph_agreement"]["projected_count"] == 1


def test_absent_endpoint_node_is_refused_and_never_projected(production_world, monkeypatch):
    event = _append(source="co:us:ABSENT")
    _seed(production_world, monkeypatch, events=[event])
    assert builder.build(production_world, mode=MODE, generated_at=ACT_STAMP) == 0
    payload = _artifact(production_world)
    assert payload["projected_edges"] == [] and payload["projected_evidence_count"] == 0
    (refusal,) = payload["projection_refusals"]
    assert refusal["code"] == "ACTIVITY_ENDPOINT_NODE_ABSENT"
    assert refusal["missing"] == ["co:us:ABSENT"]
    assert refusal["membership_id"] == event["membership_id"]
    assert payload["fold"]["current"] == 1  # the fold believed it; the projection refused


def test_not_granted_append_is_fold_refused_and_never_projected(production_world, monkeypatch):
    event = _append(use="NOT_GRANTED")
    _seed(production_world, monkeypatch, events=[event])
    assert builder.build(production_world, mode=MODE, generated_at=ACT_STAMP) == 0
    payload = _artifact(production_world)
    assert payload["fold"]["refused"] == 1 and payload["fold"]["current"] == 0
    (row,) = payload["fold"]["refused_rows"]
    assert row["reason"] == "GRAPH_MEMBERSHIP_USE_NOT_GRANTED"
    assert row["event_sha256"] == event["event_sha256"]
    assert payload["projected_edges"] == []
    assert payload["projection_refusals"] == []


# ------------------------------------------------------------------ fail-open paths


def test_writer_returns_false_on_a_malformed_events_line(production_world, monkeypatch):
    _seed(production_world, monkeypatch, events=[_append()])
    (production_world / EVENTS).write_bytes(_events_bytes([_append()]) + b"{broken\n")
    assert builder._write_activity_membership_state(production_world, ACT_STAMP) is False


@pytest.mark.parametrize("case", ["malformed_line", "root_mismatch", "fold_refusal"])
def test_fail_open_single_warning_and_prior_bytes_preserved(
        production_world, tmp_path, monkeypatch, capsys, case):
    _seed(production_world, monkeypatch, events=[_append()])
    assert builder.build(production_world, mode=MODE, generated_at=ACT_STAMP) == 0
    prior = (production_world / ARTIFACT).read_bytes()
    capsys.readouterr()
    if case == "malformed_line":
        (production_world / EVENTS).write_bytes(b"{broken\n")
        fragment = "ACTIVITY_EVENTS_FILE_INVALID"
    elif case == "root_mismatch":
        monkeypatch.setattr(config, "data_dir", lambda: tmp_path / "elsewhere" / "data")
        fragment = "GRAPH_STORE_ROOT_MISMATCH"
    else:
        _seed_events(production_world, [dict(_append(), event_sha256="0" * 64)])
        fragment = "EVENT_DIGEST_MISMATCH"

    assert builder.build(production_world, mode=MODE, generated_at=ACT_STAMP) == 0
    out = capsys.readouterr().out
    warnings = [line for line in out.splitlines() if line.startswith("::")]
    assert len(warnings) == 1 and warnings[0].startswith(WARN)
    assert fragment in warnings[0]
    assert "activity_membership_state=skipped" in out
    assert (production_world / ARTIFACT).read_bytes() == prior


# ------------------------------------------------------------------ isolation + LEGACY


def test_mode_writes_only_its_one_path(production_world, monkeypatch, capsys):
    _seed(production_world, monkeypatch, events=[_append()])
    before = _tree(production_world)
    calls: list[str] = []
    _forbid(monkeypatch, calls, g, "entry_preflight", "cas_entry", "prepare_generation",
            "publish_generation", "append_legacy")
    _forbid(monkeypatch, calls, builder, "compose", "run_optional_stages",
            "_write_shadow_graph_state")

    assert builder.build(production_world, mode=MODE, generated_at=ACT_STAMP) == 0
    after = _tree(production_world)
    out = capsys.readouterr().out

    assert calls == []
    assert set(before) - set(after) == set()
    changed = {path for path in after if before.get(path) != after[path]}
    expected = {ARTIFACT.as_posix()} | ({g.LOCK} if g.LOCK not in before else set())
    assert changed == expected
    if g.LOCK in changed:
        assert after[g.LOCK] == b""
    assert "activity_membership_state=written" in out
    assert "legacy accepted" not in out
    timing = [line for line in out.splitlines()
              if line.startswith("[thematic_state] activity_membership_state timing")]
    assert len(timing) == 1 and re.fullmatch(TIMING_RE, timing[0])


def test_legacy_outputs_are_byte_identical_with_and_without_a_prior_activity_run(
        production_world, tmp_path, monkeypatch):
    world_a = production_world
    _seed(world_a, monkeypatch, events=[_append()])
    world_b = tmp_path / "legacy-only-copy"
    shutil.copytree(world_a, world_b)

    # Pin every wall read on the LEGACY path so the two runs differ only by what the
    # modes themselves do (the fixture's EMITTED clock pins the artifacts otherwise).
    class Pinned(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            instant = dt.datetime(2026, 10, 4, 12, 0, 0, tzinfo=dt.timezone.utc)
            return instant.astimezone(tz) if tz is not None else instant.replace(tzinfo=None)

    monkeypatch.setattr(dt, "datetime", Pinned)
    monkeypatch.setattr(envelope, "datetime", Pinned)

    assert builder.build(world_a, mode=MODE, generated_at=ACT_STAMP) == 0
    assert (world_a / ARTIFACT).is_file() and not (world_b / ARTIFACT).exists()
    assert _legacy_build(world_a, monkeypatch) == 0
    assert _legacy_build(world_b, monkeypatch) == 0

    for world in (world_a, world_b):
        for legacy_path in ("data/neuralweb/theme_state.json",
                            "site/neuralwebdata/theme_state.json"):
            payload = json.loads((world / legacy_path).read_text(encoding="utf-8"))
            assert payload["produced_at"] == "2026-10-04T12:00:00Z", (world, legacy_path)

    for legacy_path in ("data/neuralweb/theme_state.json",
                        "site/neuralwebdata/theme_state.json",
                        "data/neuralweb/theme_phase_history.jsonl"):
        assert (world_a / legacy_path).is_file(), legacy_path
        assert (world_a / legacy_path).read_bytes() == (world_b / legacy_path).read_bytes(), \
            legacy_path
    tree_a, tree_b = _tree(world_a), _tree(world_b)
    assert set(tree_a) ^ set(tree_b) == {ARTIFACT.as_posix()}
    for path, content in tree_b.items():
        assert tree_a[path] == content, path


# ------------------------------------------------------------------ CLI + AST + determinism


def test_cli_mode_exits_zero_and_never_runs_optional_stages(production_world, monkeypatch, capsys):
    _seed(production_world, monkeypatch, events=[_append()])

    def _no_stages(root):
        raise AssertionError("run_optional_stages must not run in the activity mode")

    monkeypatch.setattr(builder, "run_optional_stages", _no_stages)
    monkeypatch.setattr(sys, "argv", ["build_thematic_state.py", "--mode", MODE,
                                      "--root", str(production_world)])
    with pytest.raises(SystemExit) as caught:
        builder.main()
    assert caught.value.code == 0
    assert "activity_membership_state=written" in capsys.readouterr().out


def test_ast_activity_writer_dispatched_only_from_its_own_mode():
    tree = ast.parse(Path(builder.__file__).read_text(encoding="utf-8"))
    build_fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build")

    def writer_calls(nodes, name):
        return [n for node in nodes for n in ast.walk(node)
                if isinstance(n, ast.Call) and getattr(n.func, "id", None) == name]

    def mode_blocks(comparator):
        return [node for node in ast.walk(build_fn)
                if (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
                    and getattr(node.test.left, "id", None) == "mode"
                    and isinstance(node.test.ops[0], ast.Eq)
                    and getattr(node.test.comparators[0], "id", None) == comparator)]

    guarded = []
    for node in mode_blocks("_ACTIVITY_MEMBERSHIP_STATE_MODE"):
        guarded += writer_calls(node.body, "_write_activity_membership_state")
        assert isinstance(node.body[-1], ast.Return)
    assert len(guarded) == 1
    assert writer_calls([build_fn], "_write_activity_membership_state") == guarded
    module_calls = writer_calls(
        [n for n in tree.body if not (isinstance(n, ast.FunctionDef) and n.name == "build")],
        "_write_activity_membership_state")
    assert module_calls == []
    # The shadow writer's dispatch is untouched: still only its own mode block.
    shadow_guarded = []
    for node in mode_blocks("_GRAPH_SHADOW_STATE_MODE"):
        shadow_guarded += writer_calls(node.body, "_write_shadow_graph_state")
        assert isinstance(node.body[-1], ast.Return)
    assert len(shadow_guarded) == 1
    assert writer_calls([build_fn], "_write_shadow_graph_state") == shadow_guarded


def test_determinism_same_stamp_and_inputs_identical_bytes(production_world, monkeypatch):
    _seed(production_world, monkeypatch, events=[_append()])
    assert builder.build(production_world, mode=MODE, generated_at=ACT_STAMP) == 0
    first = (production_world / ARTIFACT).read_bytes()
    assert builder.build(production_world, mode=MODE, generated_at=ACT_STAMP) == 0
    assert (production_world / ARTIFACT).read_bytes() == first

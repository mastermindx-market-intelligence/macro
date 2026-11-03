"""Load-side binding of the activity-history ledger to its bridge receipts.

``engine/theme_graph/activity_history_bridge.load_bound_activity_events`` is the ONE
helper both loaders read ``activity_history_events.jsonl`` through
(``scripts/build_theme_graph.py`` -> None + one line-start ``::warning``;
``scripts/build_thematic_state.py`` -> ``ValueError("<CODE>: ...")``). An event is
kept only when a bridge receipt row binds it (outcome == action, identical
``event_sha256``/``event_id``), the curation receipt bytes on disk — a real,
non-empty file, never the sha256 of no bytes — hash to the event's
``curation.receipt_sha256``, the row's ``use_ruling_sha256`` is the content of a real
ruling file, the target is a ``micro_theme``/``sub_theme``, and that ruling's
``graph_membership_use_grant`` grants the event's own subject, target, species,
scope and proposal id for the evidence edition it carries.

The positive world is PR #10628's real MU ledger (byte copies under
``tests/fixtures/gmi_activity_binding/``) plus the real curation receipt, the real
C01 ruling and the real crosswalk, copied into a hermetic tmp root.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import inspect
import json
import shutil
import textwrap
from pathlib import Path

import pytest

from engine.theme_graph import activity_history_bridge as bridge
from engine.theme_graph import materialize

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "gmi_activity_binding"
EVENTS_FIXTURE = FIXTURES / "activity_history_events.pr10628.jsonl"
RECEIPTS_FIXTURE = FIXTURES / "activity_history_bridge_receipts.pr10628.jsonl"
REAL_RULING = "research/theme_graph/issuer_disclosures_20261011/C01_GRAPH_MEMBERSHIP_USE_RULING.json"
REAL_CURATION = ("research/theme_graph/activity_curation_receipts/"
                 "actprop_287edbf7e04b8aba873b7493.json")

EVENTS_FIXTURE_SHA = "2f9902c9c7f3e73e90fa2cef9f5c3c3670eda2f38793a3f1c7e5aa786b97eda5"
RECEIPTS_FIXTURE_SHA = "859f103a9261536b5846f394bc4ed6c9ef6633144c9d4c1e13abf8aecf72c7f1"
REAL_RULING_SHA = "1443c6e47b1da8bef15eb5672c96c91d4bcc3481da93bf159d66ab973eabfc7f"
REAL_CURATION_SHA = "d6796b514e76ab8fb99df95d22ef96d5f8a4831684a7bb50191188341b962597"
MU_EVENT_ID = "actevt:8d821abab4be45ba8bf866cd"
MU_MEMBERSHIP_ID = "actmem:dbdf774cb011d26f3c6d6936"
AFTER_KNOWLEDGE = "2026-11-03T00:00:00Z"   # MU knowledge_at is 2026-11-02T23:49:45Z
BAKE_WARNING = "::warning title=theme graph activity history refused::"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _jsonl(rows) -> bytes:
    return b"".join(json.dumps(r, sort_keys=True).encode("utf-8") + b"\n" for r in rows)


MU_EVENT = json.loads(EVENTS_FIXTURE.read_text(encoding="utf-8"))
MU_ROW = json.loads(RECEIPTS_FIXTURE.read_text(encoding="utf-8"))


def _redigest(event: dict) -> dict:
    """The event re-digested honestly (what a writer bypassing the bridge would do)."""
    event = copy.deepcopy(event)
    digest = materialize.activity_history_event_digest(event)
    event["event_sha256"] = digest
    event["event_id"] = "actevt:" + digest[:24]
    return event


def _retarget(event: dict, *, source=None, target=None) -> dict:
    event = copy.deepcopy(event)
    if source:
        event["endpoints"]["source_node_id"] = source
    if target:
        event["endpoints"]["target_node_id"] = target
    event["membership_id"] = materialize.activity_membership_id(
        source_node_id=event["endpoints"]["source_node_id"],
        target_node_id=event["endpoints"]["target_node_id"],
        species=event["species"], scope=event["scope"])
    return _redigest(event)


def _row_for(event: dict, **overrides) -> dict:
    row = dict(MU_ROW, event_id=event["event_id"], event_sha256=event["event_sha256"])
    row.update(overrides)
    return row


def _ruling_granting(world, name: str, *, revises=None, source_sha256=None,
                     **grant) -> tuple[str, str]:
    """A HERMETIC ruling revision inside the tmp root's default ruling glob: the real
    C01 document with ``graph_membership_use_grant`` fields replaced. It exists only
    under ``tmp_path`` (the committed research/ ruling is never edited) and binds only
    the test's own tmp ledger. Returns (repo-relative path, sha256)."""
    doc = json.loads((ROOT / REAL_RULING).read_text(encoding="utf-8"))
    doc["graph_membership_use_grant"].update(grant)
    if revises is not None:
        doc["revises_ruling_sha256"] = revises
    if source_sha256 is not None:
        doc["source"] = dict(doc["source"], sha256=source_sha256)
    rel = f"research/theme_graph/test_grants/{name}_GRAPH_MEMBERSHIP_USE_RULING.json"
    raw = json.dumps(doc, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    (world.root / rel).parent.mkdir(parents=True, exist_ok=True)
    (world.root / rel).write_bytes(raw)
    return rel, _sha(raw)


def _a_sub_theme() -> str:
    tiers = bridge.activity_target_tiers_from_crosswalk_path(
        ROOT / bridge.DEFAULT_CROSSWALK_PATH)
    return sorted(n for n, t in tiers.items() if t == "sub_theme")[0]


class World:
    """A hermetic repo root holding the real MU ledger and its real binding inputs."""

    def __init__(self, tmp_path: Path):
        self.root = tmp_path / "repo"
        for rel in (REAL_RULING, REAL_CURATION, bridge.DEFAULT_CROSSWALK_PATH):
            dst = self.root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, dst)
        self.events_path = self.root / bridge.DEFAULT_EVENTS_PATH
        self.receipts_path = self.root / bridge.DEFAULT_BRIDGE_RECEIPTS_PATH
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(EVENTS_FIXTURE, self.events_path)
        shutil.copyfile(RECEIPTS_FIXTURE, self.receipts_path)
        self.tier_reads = 0

    def write(self, *, events=None, rows=None):
        if events is not None:
            self.events_path.write_bytes(_jsonl(events))
        if rows is not None:
            self.receipts_path.write_bytes(_jsonl(rows))

    def crosswalk_tiers(self):
        self.tier_reads += 1
        return bridge.activity_target_tiers_from_crosswalk_path(
            self.root / bridge.DEFAULT_CROSSWALK_PATH)

    def load(self, **overrides):
        kwargs = dict(events_path=self.events_path,
                      bridge_receipts_path=self.receipts_path,
                      receipts_dir=self.root / bridge.DEFAULT_RECEIPTS_DIR,
                      ruling_root=self.root, target_tiers=self.crosswalk_tiers)
        kwargs.update(overrides)
        return bridge.load_bound_activity_events(**kwargs)


@pytest.fixture
def world(tmp_path):
    return World(tmp_path)


@pytest.fixture
def bake(world, monkeypatch):
    from scripts import build_theme_graph as bake

    monkeypatch.setattr(bake.store, "probation_path",
                        lambda: world.events_path.parent / "proposals.jsonl")
    monkeypatch.setattr(bake, "_ACTIVITY_BINDING_ROOT", world.root)
    return bake


def _warnings(capsys) -> list[str]:
    return [ln for ln in capsys.readouterr().out.splitlines() if ln.startswith("::")]


# ---------------------------------------------------------------------------
# The fixtures ARE PR #10628's bytes, bound to the real curation receipt and ruling
# ---------------------------------------------------------------------------

def test_fixtures_pin_the_pr10628_ledger_and_its_real_binding_inputs():
    assert _sha(EVENTS_FIXTURE.read_bytes()) == EVENTS_FIXTURE_SHA
    assert _sha(RECEIPTS_FIXTURE.read_bytes()) == RECEIPTS_FIXTURE_SHA
    assert _sha((ROOT / REAL_RULING).read_bytes()) == REAL_RULING_SHA
    assert _sha((ROOT / REAL_CURATION).read_bytes()) == REAL_CURATION_SHA
    assert MU_EVENT["event_id"] == MU_EVENT_ID
    assert MU_EVENT["event_sha256"] == materialize.activity_history_event_digest(MU_EVENT)
    assert MU_ROW["use_ruling_sha256"] == REAL_RULING_SHA
    assert MU_ROW["curation_receipt_sha256"] == REAL_CURATION_SHA
    assert set(bridge.ACTIVITY_BINDING_CODES) == {
        "ACTIVITY_EVENTS_FILE_INVALID", "BRIDGE_RECEIPTS_FILE_INVALID",
        "ACTIVITY_EVENT_UNBOUND", "ACTIVITY_CURATION_RECEIPT_MISMATCH",
        "ACTIVITY_USE_RULING_UNBOUND", "ACTIVITY_TARGET_TIER_NOT_ADMITTED",
        "ACTIVITY_USE_GRANT_MISMATCH", "ACTIVITY_TARGET_TAXONOMY_UNREADABLE"}


# ---------------------------------------------------------------------------
# MU positive: the real event binds and folds to exactly one current membership
# ---------------------------------------------------------------------------

def _assert_mu_folds_to_one_current_membership(events):
    assert [e["event_id"] for e in events] == [MU_EVENT_ID]
    fold = materialize.apply_activity_membership_events(events,
                                                        knowledge_cutoff=AFTER_KNOWLEDGE)
    assert [m["membership_id"] for m in fold["current"]] == [MU_MEMBERSHIP_ID]
    assert fold["refused"] == [] and fold["history"] == []
    assert fold["excluded_after_cutoff"] == []


def test_mu_event_binds_with_its_repo_relative_ruling_path(world):
    assert not Path(MU_ROW["use_ruling_path"]).is_absolute()
    loaded = world.load()
    assert loaded["events_sha256"] == EVENTS_FIXTURE_SHA
    assert loaded["events"] == [MU_EVENT]
    _assert_mu_folds_to_one_current_membership(loaded["events"])


def test_mu_event_binds_through_an_absolute_ruling_path_by_sha_alone(world):
    """Rows written before paths were recorded repo-relative carry another host's
    absolute path: it is never trusted as a location, never rewritten, and binds
    through ``use_ruling_sha256`` alone."""
    absolute = ("/Users/someone-else/Documents/macro-main/"
                "research/theme_graph/issuer_disclosures_20261011/"
                "C01_GRAPH_MEMBERSHIP_USE_RULING.json")
    assert not Path(absolute).exists()
    world.write(rows=[dict(MU_ROW, use_ruling_path=absolute)])
    receipts_before = world.receipts_path.read_bytes()
    events_before = world.events_path.read_bytes()
    loaded = world.load()
    _assert_mu_folds_to_one_current_membership(loaded["events"])
    assert world.receipts_path.read_bytes() == receipts_before
    assert world.events_path.read_bytes() == events_before


def test_a_sub_theme_target_is_admitted(world):
    tiers = world.crosswalk_tiers()
    sub_theme = sorted(n for n, t in tiers.items() if t == "sub_theme")[0]
    moved = _retarget(MU_EVENT, target=sub_theme)
    # The tier is admitted; the cited ruling must ALSO grant that target (a row citing
    # the real C01 ruling, which grants theme:hbm_packaging, is refused below).
    rel, sha = _ruling_granting(world, "S01", target_node_id=sub_theme)
    world.write(events=[moved],
                rows=[_row_for(moved, use_ruling_path=rel, use_ruling_sha256=sha)])
    assert [e["event_id"] for e in world.load()["events"]] == [moved["event_id"]]


def test_an_unreadable_curation_receipt_is_a_typed_refusal_never_a_traceback(world):
    path = world.root / REAL_CURATION
    path.unlink()
    path.mkdir()   # read_bytes() now raises IsADirectoryError, an OSError
    with pytest.raises(bridge.BridgeRefusal) as exc:
        world.load()
    assert exc.value.code == "ACTIVITY_CURATION_RECEIPT_MISMATCH"
    assert "RECEIPT_UNREADABLE" in str(exc.value)
    with pytest.raises(bridge.BridgeRefusal) as exc:
        bridge.read_curation_receipt_bytes(world.root / bridge.DEFAULT_RECEIPTS_DIR,
                                           MU_EVENT["evidence_lineage"]["proposal_id"])
    assert exc.value.code == "RECEIPT_UNREADABLE"


def test_an_absent_curation_receipt_reads_as_none_never_as_empty_bytes(world):
    receipts_dir = world.root / bridge.DEFAULT_RECEIPTS_DIR
    assert bridge.read_curation_receipt_bytes(receipts_dir, NO_SUCH_PID) is None
    assert bridge.read_curation_receipt_bytes(
        receipts_dir, MU_EVENT["evidence_lineage"]["proposal_id"]) == (
            ROOT / REAL_CURATION).read_bytes()


def test_absent_and_blank_ledgers_never_read_the_taxonomy(world):
    world.events_path.unlink()
    assert world.load() is None
    world.events_path.write_bytes(b"\n\n")
    assert world.load()["events"] == []
    assert world.tier_reads == 0


# ---------------------------------------------------------------------------
# Forged NVDA APPEND: the fold alone accepts it; BOTH loaders refuse it
# ---------------------------------------------------------------------------

FORGED_NVDA = _retarget(MU_EVENT, source="co:us:NVDA")
EMPTY_SHA = _sha(b"")
NO_SUCH_PID = "actprop:" + "0" * 24


def test_the_fold_alone_would_accept_a_forged_but_honestly_digested_append():
    """Why the binding lives at the I/O layer: the pure fold validates shape and
    digest, and a forged event satisfies both."""
    fold = materialize.apply_activity_membership_events([FORGED_NVDA],
                                                        knowledge_cutoff=AFTER_KNOWLEDGE)
    assert [m["endpoints"]["source_node_id"] for m in fold["current"]] == ["co:us:NVDA"]
    assert fold["refused"] == []


def test_forged_nvda_append_is_refused_by_the_helper(world):
    world.write(events=[MU_EVENT, FORGED_NVDA], rows=[MU_ROW])
    with pytest.raises(bridge.BridgeRefusal) as exc:
        world.load()
    assert exc.value.code == "ACTIVITY_EVENT_UNBOUND"
    assert f"line 2 ('{FORGED_NVDA['event_id']}')" in str(exc.value)


def test_forged_nvda_append_refuses_the_whole_ledger_in_the_graph_builder(
        world, bake, capsys):
    world.write(events=[MU_EVENT, FORGED_NVDA], rows=[MU_ROW])
    assert bake._activity_history_events() is None
    warnings = _warnings(capsys)
    assert len(warnings) == 1 and warnings[0].startswith(BAKE_WARNING)
    assert "ACTIVITY_EVENT_UNBOUND" in warnings[0]


def test_the_graph_builder_reads_the_bound_mu_ledger(world, bake, capsys):
    assert bake._activity_history_events() == [MU_EVENT]
    assert capsys.readouterr().out == ""


def test_the_graph_builder_reads_events_only_through_the_shared_helper(
        world, bake, monkeypatch):
    calls = []
    real = bridge.load_bound_activity_events

    def spy(**kwargs):
        calls.append(kwargs)
        return real(**kwargs)

    monkeypatch.setattr(bake.activity_history_bridge, "load_bound_activity_events", spy)
    assert bake._activity_history_events() == [MU_EVENT]
    assert len(calls) == 1
    assert Path(calls[0]["events_path"]) == world.events_path
    assert Path(calls[0]["bridge_receipts_path"]) == world.receipts_path
    assert Path(calls[0]["ruling_root"]) == world.root


def test_the_graph_builder_source_never_parses_the_events_file_itself():
    from scripts import build_theme_graph as bake

    source = inspect.getsource(bake._activity_history_events)
    assert "load_bound_activity_events" in source
    for forbidden in ("json.loads", "read_text", "read_bytes", "open("):
        assert forbidden not in source


# ---------------------------------------------------------------------------
# Every refusal code, through the helper AND through the graph builder
# ---------------------------------------------------------------------------

def _events_raw(raw: bytes):
    def mutate(world):
        world.events_path.write_bytes(raw)
    return mutate


def _receipts_raw(raw: bytes):
    def mutate(world):
        world.receipts_path.write_bytes(raw)
    return mutate


def _rows(*rows_fn):
    def mutate(world):
        world.write(rows=[fn() for fn in rows_fn])
    return mutate


def _events_and_rows(events, rows):
    def mutate(world):
        world.write(events=events, rows=rows)
    return mutate


def _unlink(rel):
    def mutate(world):
        (world.root / rel).unlink()
    return mutate


def _append_bytes(rel, extra=b" "):
    def mutate(world):
        path = world.root / rel
        path.write_bytes(path.read_bytes() + extra)
    return mutate


def _row_ruling_path_to_another_ruling(world):
    other = world.root / "research/theme_graph/other_ruling/X01_GRAPH_MEMBERSHIP_USE_RULING.json"
    other.parent.mkdir(parents=True, exist_ok=True)
    other.write_bytes(b'{"another": "ruling"}\n')
    world.write(rows=[dict(MU_ROW, use_ruling_path=other.relative_to(world.root).as_posix())])


def _ruling_moved_outside_the_glob(world):
    moved = world.root / "research/not_a_ruling_dir/C01.json"
    moved.parent.mkdir(parents=True, exist_ok=True)
    (world.root / REAL_RULING).rename(moved)
    world.write(rows=[dict(MU_ROW, use_ruling_path=moved.relative_to(world.root).as_posix())])


def _event_curation_claim_changed(world):
    event = copy.deepcopy(MU_EVENT)
    event["curation"]["receipt_sha256"] = "c" * 64
    event = _redigest(event)
    world.write(events=[event], rows=[_row_for(event, curation_receipt_sha256="c" * 64)])


def _event_recorded_at_rewritten(world):
    event = copy.deepcopy(MU_EVENT)
    event["clocks"]["recorded_at"] = "2026-11-04T00:00:00Z"
    world.write(events=[_redigest(event)])


def _retargeted_with_row(target):
    def mutate(world):
        moved = _retarget(MU_EVENT, target=target)
        world.write(events=[moved], rows=[_row_for(moved)])
    return mutate


def _empty_hash_curation_forgery(*, alone: bool):
    """Attack A: a proposal id with NO curation receipt on file, claiming sha256(b"")
    — the digest an absent receipt used to read as — on a forged NVDA membership with
    its own self-consistent bridge row citing the real C01 ruling."""
    def mutate(world):
        event = copy.deepcopy(FORGED_NVDA)
        event["evidence_lineage"]["proposal_id"] = NO_SUCH_PID
        event["curation"]["receipt_sha256"] = EMPTY_SHA
        event = _redigest(event)
        row = _row_for(event, proposal_id=NO_SUCH_PID, curation_receipt_sha256=EMPTY_SHA)
        assert not bridge.curation_receipt_path(
            world.root / bridge.DEFAULT_RECEIPTS_DIR, NO_SUCH_PID).exists()
        if alone:
            world.write(events=[event], rows=[row])
        else:
            world.write(events=[MU_EVENT, event], rows=[MU_ROW, row])
    return mutate


def _curation_receipt_emptied_and_claimed_empty(world):
    (world.root / REAL_CURATION).write_bytes(b"")
    event = copy.deepcopy(MU_EVENT)
    event["curation"]["receipt_sha256"] = EMPTY_SHA
    event = _redigest(event)
    world.write(events=[event], rows=[_row_for(event, curation_receipt_sha256=EMPTY_SHA)])


def _curation_receipt_emptied(world):
    (world.root / REAL_CURATION).write_bytes(b"")


def _curation_receipt_unreadable(world):
    path = world.root / REAL_CURATION
    path.unlink()
    path.mkdir()


def _mutated_with_row(change):
    """MU with ``change`` applied, membership id recomputed, honestly re-digested,
    and given its own self-consistent bridge row citing the real C01 ruling."""
    def mutate(world):
        event = copy.deepcopy(MU_EVENT)
        change(event)
        event = _retarget(event)
        world.write(events=[event], rows=[_row_for(event)])
    return mutate


def _mu_citing_a_ruling(name, **ruling_changes):
    """The real MU event, its row re-pointed at a hermetic ruling revision whose
    content differs from C01 only by ``ruling_changes``."""
    def mutate(world):
        rel, sha = _ruling_granting(world, name, **ruling_changes)
        world.write(rows=[dict(MU_ROW, use_ruling_path=rel, use_ruling_sha256=sha)])
    return mutate


def _mu_citing_a_non_ruling_document(world):
    rel = "research/theme_graph/test_grants/J01_GRAPH_MEMBERSHIP_USE_RULING.json"
    raw = b'{"another": "document"}\n'
    (world.root / rel).parent.mkdir(parents=True, exist_ok=True)
    (world.root / rel).write_bytes(raw)
    world.write(rows=[dict(MU_ROW, use_ruling_path=rel, use_ruling_sha256=_sha(raw))])


def _crosswalk_bytes(raw: bytes):
    def mutate(world):
        (world.root / bridge.DEFAULT_CROSSWALK_PATH).write_bytes(raw)
    return mutate


def _row_drop(key):
    row = dict(MU_ROW)
    del row[key]
    return row


REFUSALS = [
    # (case id, mutate(world) -> optional helper kwargs, expected code, bake-reachable)
    ("events_malformed_line",
     _events_raw(EVENTS_FIXTURE.read_bytes() + b"not json\n"),
     "ACTIVITY_EVENTS_FILE_INVALID", True),
    ("events_line_not_an_object", _events_raw(b"[1, 2]\n"),
     "ACTIVITY_EVENTS_FILE_INVALID", True),
    ("events_not_utf8", _events_raw(b"\xff\xfe\n"), "ACTIVITY_EVENTS_FILE_INVALID", True),
    ("receipt_row_extra_key", _rows(lambda: dict(MU_ROW, note="hand-written")),
     "BRIDGE_RECEIPTS_FILE_INVALID", True),
    ("receipt_row_missing_key", _rows(lambda: _row_drop("recorded_at")),
     "BRIDGE_RECEIPTS_FILE_INVALID", True),
    ("receipt_row_outcome_outside_the_bridge_vocabulary",
     _rows(lambda: dict(MU_ROW, outcome="CORRECT")), "BRIDGE_RECEIPTS_FILE_INVALID", True),
    ("receipts_malformed_json", _receipts_raw(RECEIPTS_FIXTURE.read_bytes() + b"{torn\n"),
     "BRIDGE_RECEIPTS_FILE_INVALID", True),
    ("receipts_not_utf8", _receipts_raw(b"\xff\xfe\n"), "BRIDGE_RECEIPTS_FILE_INVALID", True),
    ("receipts_file_absent", _unlink(bridge.DEFAULT_BRIDGE_RECEIPTS_PATH),
     "ACTIVITY_EVENT_UNBOUND", True),
    ("forged_nvda_append", _events_and_rows([MU_EVENT, FORGED_NVDA], [MU_ROW]),
     "ACTIVITY_EVENT_UNBOUND", True),
    ("row_names_another_event_sha", _rows(lambda: dict(MU_ROW, event_sha256="e" * 64)),
     "ACTIVITY_EVENT_UNBOUND", True),
    ("row_outcome_is_not_the_event_action", _rows(lambda: dict(MU_ROW, outcome="SKIPPED")),
     "ACTIVITY_EVENT_UNBOUND", True),
    ("row_use_differs", _rows(lambda: dict(MU_ROW, graph_membership_use="NOT_GRANTED")),
     "ACTIVITY_EVENT_UNBOUND", True),
    ("row_names_another_proposal",
     _rows(lambda: dict(MU_ROW, proposal_id="actprop:000000000000000000000000")),
     "ACTIVITY_EVENT_UNBOUND", True),
    ("event_recorded_at_rewritten_and_redigested", _event_recorded_at_rewritten,
     "ACTIVITY_EVENT_UNBOUND", True),
    ("curation_receipt_bytes_changed", _append_bytes(REAL_CURATION),
     "ACTIVITY_CURATION_RECEIPT_MISMATCH", True),
    ("curation_receipt_deleted", _unlink(REAL_CURATION),
     "ACTIVITY_CURATION_RECEIPT_MISMATCH", True),
    ("row_curation_sha_differs", _rows(lambda: dict(MU_ROW, curation_receipt_sha256="a" * 64)),
     "ACTIVITY_CURATION_RECEIPT_MISMATCH", True),
    ("event_curation_claim_differs_from_the_bytes", _event_curation_claim_changed,
     "ACTIVITY_CURATION_RECEIPT_MISMATCH", True),
    # Finding 1 (attack A): an ABSENT receipt is never the empty-bytes digest.
    ("empty_hash_curation_for_a_nonexistent_proposal",
     _empty_hash_curation_forgery(alone=True), "ACTIVITY_CURATION_RECEIPT_MISMATCH", True),
    ("empty_hash_curation_forgery_beside_the_real_mu_event",
     _empty_hash_curation_forgery(alone=False), "ACTIVITY_CURATION_RECEIPT_MISMATCH", True),
    ("curation_receipt_emptied_and_claimed_as_the_empty_digest",
     _curation_receipt_emptied_and_claimed_empty, "ACTIVITY_CURATION_RECEIPT_MISMATCH", True),
    ("curation_receipt_emptied", _curation_receipt_emptied,
     "ACTIVITY_CURATION_RECEIPT_MISMATCH", True),
    # Finding 4: an unreadable receipt is the typed refusal, never a traceback.
    ("curation_receipt_unreadable", _curation_receipt_unreadable,
     "ACTIVITY_CURATION_RECEIPT_MISMATCH", True),
    ("ruling_deleted", _unlink(REAL_RULING), "ACTIVITY_USE_RULING_UNBOUND", True),
    ("ruling_modified", _append_bytes(REAL_RULING), "ACTIVITY_USE_RULING_UNBOUND", True),
    ("row_ruling_sha_names_no_file", _rows(lambda: dict(MU_ROW, use_ruling_sha256="0" * 64)),
     "ACTIVITY_USE_RULING_UNBOUND", True),
    ("row_relative_path_is_another_ruling", _row_ruling_path_to_another_ruling,
     "ACTIVITY_USE_RULING_UNBOUND", True),
    ("ruling_outside_the_default_glob", _ruling_moved_outside_the_glob,
     "ACTIVITY_USE_RULING_UNBOUND", True),
    ("row_absolute_path_with_a_wrong_sha",
     _rows(lambda: dict(MU_ROW, use_ruling_path=str(ROOT / REAL_RULING),
                        use_ruling_sha256="b" * 64)),
     "ACTIVITY_USE_RULING_UNBOUND", True),
    ("row_ruling_path_empty", _rows(lambda: dict(MU_ROW, use_ruling_path="")),
     "ACTIVITY_USE_RULING_UNBOUND", True),
    ("target_is_a_theme_tier_node", _retargeted_with_row("theme:memory_storage"),
     "ACTIVITY_TARGET_TIER_NOT_ADMITTED", True),
    ("target_is_a_macro_category", _retargeted_with_row("theme:semiconductors_hardware"),
     "ACTIVITY_TARGET_TIER_NOT_ADMITTED", True),
    ("target_is_no_known_node", _retargeted_with_row("theme:not_a_declared_node"),
     "ACTIVITY_TARGET_TIER_NOT_ADMITTED", True),
    # Finding 2 (attack B): the cited ruling must GRANT the event's own membership.
    ("forged_nvda_with_its_own_row_and_mus_real_curation",
     _events_and_rows([MU_EVENT, FORGED_NVDA], [MU_ROW, _row_for(FORGED_NVDA)]),
     "ACTIVITY_USE_GRANT_MISMATCH", True),
    ("forged_nvda_alone_with_its_own_row",
     _events_and_rows([FORGED_NVDA], [_row_for(FORGED_NVDA)]),
     "ACTIVITY_USE_GRANT_MISMATCH", True),
    ("grant_names_another_target",
     _mutated_with_row(lambda e: e["endpoints"].update(target_node_id=_a_sub_theme())),
     "ACTIVITY_USE_GRANT_MISMATCH", True),
    ("grant_names_another_species",
     _mutated_with_row(lambda e: e.update(species="supply_agreement")),
     "ACTIVITY_USE_GRANT_MISMATCH", True),
    ("grant_names_another_scope_platform",
     _mutated_with_row(lambda e: e["scope"].update(platform="NVIDIA B200")),
     "ACTIVITY_USE_GRANT_MISMATCH", True),
    ("grant_names_another_counterparty",
     _mutated_with_row(lambda e: e["scope"].update(counterparty_issuer_id="ISS:US-XNAS-AMD")),
     "ACTIVITY_USE_GRANT_MISMATCH", True),
    ("grant_proposal_ids_omit_the_event_proposal",
     _mu_citing_a_ruling("P01", proposal_ids=["actprop:" + "1" * 24]),
     "ACTIVITY_USE_GRANT_MISMATCH", True),
    ("grant_is_not_granted", _mu_citing_a_ruling("N01", graph_membership_use="NOT_GRANTED"),
     "ACTIVITY_USE_GRANT_MISMATCH", True),
    ("grant_allows_display", _mu_citing_a_ruling("D01", display=True),
     "ACTIVITY_USE_GRANT_MISMATCH", True),
    ("ruling_revises_another_ruling", _mu_citing_a_ruling("R01", revises="f" * 64),
     "ACTIVITY_USE_GRANT_MISMATCH", True),
    ("ruling_covers_another_source_edition",
     _mu_citing_a_ruling("E01", source_sha256="e" * 64),
     "ACTIVITY_USE_GRANT_MISMATCH", True),
    ("ruling_is_not_a_source_purpose_ruling", _mu_citing_a_non_ruling_document,
     "ACTIVITY_USE_GRANT_MISMATCH", True),
    ("crosswalk_invalid_yaml", _crosswalk_bytes(b"themes: [unterminated\n"),
     "ACTIVITY_TARGET_TAXONOMY_UNREADABLE", True),
    ("crosswalk_not_a_mapping", _crosswalk_bytes(b"- a\n- b\n"),
     "ACTIVITY_TARGET_TAXONOMY_UNREADABLE", True),
    ("crosswalk_absent", _unlink(bridge.DEFAULT_CROSSWALK_PATH),
     "ACTIVITY_TARGET_TAXONOMY_UNREADABLE", True),
    ("no_tier_map_supplied", lambda world: {"target_tiers": None},
     "ACTIVITY_TARGET_TAXONOMY_UNREADABLE", False),
    ("tier_map_reader_raises",
     lambda world: {"target_tiers": lambda: (_ for _ in ()).throw(OSError("store gone"))},
     "ACTIVITY_TARGET_TAXONOMY_UNREADABLE", False),
    ("tier_map_is_not_a_mapping", lambda world: {"target_tiers": lambda: ["theme:x"]},
     "ACTIVITY_TARGET_TAXONOMY_UNREADABLE", False),
]


def test_the_refusal_table_names_every_binding_code():
    assert {code for _, _, code, _ in REFUSALS} == set(bridge.ACTIVITY_BINDING_CODES)


@pytest.mark.parametrize("case,mutate,code,_bake", REFUSALS, ids=[r[0] for r in REFUSALS])
def test_helper_refuses_the_whole_ledger_with_the_named_code(world, case, mutate, code, _bake):
    overrides = mutate(world) or {}
    with pytest.raises(bridge.BridgeRefusal) as exc:
        world.load(**overrides)
    assert exc.value.code == code, str(exc.value)
    assert str(exc.value).startswith(f"{code}: ")


@pytest.mark.parametrize("case,mutate,code",
                         [(c, m, k) for c, m, k, b in REFUSALS if b],
                         ids=[r[0] for r in REFUSALS if r[3]])
def test_graph_builder_refuses_with_the_same_code(world, bake, capsys, case, mutate, code):
    mutate(world)
    assert bake._activity_history_events() is None
    warnings = _warnings(capsys)
    assert len(warnings) == 1 and warnings[0].startswith(BAKE_WARNING)
    assert f": {code}: " in warnings[0]


def test_checks_run_in_order_and_the_taxonomy_is_read_only_when_needed(world):
    # Unbound AND mis-tiered: the first failing check (binding) names the refusal, and
    # the taxonomy is never read for it.
    moved = _retarget(MU_EVENT, target="theme:memory_storage")
    world.write(events=[moved], rows=[MU_ROW])
    with pytest.raises(bridge.BridgeRefusal) as exc:
        world.load()
    assert exc.value.code == "ACTIVITY_EVENT_UNBOUND"
    assert world.tier_reads == 0
    # Curation mismatch outranks a missing ruling.
    world.write(events=[MU_EVENT], rows=[dict(MU_ROW, curation_receipt_sha256="a" * 64)])
    (world.root / REAL_RULING).unlink()
    with pytest.raises(bridge.BridgeRefusal) as exc:
        world.load()
    assert exc.value.code == "ACTIVITY_CURATION_RECEIPT_MISMATCH"
    assert world.tier_reads == 0
    # A mis-tiered target outranks an ungranted one: (d) names it before (e).
    moved = _retarget(MU_EVENT, target="theme:memory_storage")
    world.write(events=[moved], rows=[_row_for(moved)])
    (world.root / REAL_RULING).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / REAL_RULING, world.root / REAL_RULING)
    with pytest.raises(bridge.BridgeRefusal) as exc:
        world.load()
    assert exc.value.code == "ACTIVITY_TARGET_TIER_NOT_ADMITTED"


def test_a_hermetic_grant_for_the_forged_nvda_membership_is_what_admits_it(world):
    """The grant check is the discriminator for attack B: the SAME forged row binds
    once (and only once) a ruling actually grants co:us:NVDA."""
    rel, sha = _ruling_granting(world, "G01", subject_node_id="co:us:NVDA")
    world.write(events=[FORGED_NVDA],
                rows=[_row_for(FORGED_NVDA, use_ruling_path=rel, use_ruling_sha256=sha)])
    assert [e["event_id"] for e in world.load()["events"]] == [FORGED_NVDA["event_id"]]


# ---------------------------------------------------------------------------
# Repo-relative ruling paths
# ---------------------------------------------------------------------------

def test_repo_relative_ruling_path_records_paths_under_the_root_relative(tmp_path):
    rel = "research/theme_graph/x/A_GRAPH_MEMBERSHIP_USE_RULING.json"
    assert bridge.repo_relative_ruling_path(rel, root=tmp_path) == rel
    assert bridge.repo_relative_ruling_path(str(tmp_path / rel), root=tmp_path) == rel
    outside = "/elsewhere/host/A_GRAPH_MEMBERSHIP_USE_RULING.json"
    assert bridge.repo_relative_ruling_path(outside, root=tmp_path) == outside
    # The default root is the repo, never the process cwd.
    assert bridge.repo_relative_ruling_path(str(ROOT / REAL_RULING)) == REAL_RULING


def test_cli_default_ruling_paths_are_repo_relative():
    from scripts import bridge_activity_history as cli

    paths = cli._default_ruling_paths()
    assert REAL_RULING in paths
    assert all(not Path(p).is_absolute() for p in paths)


# ---------------------------------------------------------------------------
# The fold stays PURE: the binding never moved into materialize
# ---------------------------------------------------------------------------

def test_apply_activity_membership_events_does_no_io():
    tree = ast.parse(textwrap.dedent(inspect.getsource(
        materialize.apply_activity_membership_events)))
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert not names & {"open", "Path", "bridge", "activity_history_bridge"}
    assert not attrs & {"read_text", "read_bytes", "write_text", "write_bytes", "open",
                        "glob", "exists", "load_bound_activity_events"}
    assert set(inspect.signature(
        materialize.apply_activity_membership_events).parameters) == {
            "events", "knowledge_cutoff"}


# ---------------------------------------------------------------------------
# The real ledger (present once PR #10628 is on main)
# ---------------------------------------------------------------------------

@pytest.mark.needs_full_checkout("data")
def test_the_real_ledger_is_bound_and_both_readers_agree(monkeypatch, capsys):
    events_path = ROOT / bridge.DEFAULT_EVENTS_PATH
    if not events_path.exists():
        pytest.skip("no activity history ledger on this checkout")
    loaded = bridge.load_bound_activity_events(
        events_path=events_path,
        bridge_receipts_path=ROOT / bridge.DEFAULT_BRIDGE_RECEIPTS_PATH,
        receipts_dir=ROOT / bridge.DEFAULT_RECEIPTS_DIR, ruling_root=ROOT,
        target_tiers=lambda: bridge.activity_target_tiers_from_crosswalk_path(
            ROOT / bridge.DEFAULT_CROSSWALK_PATH))
    assert MU_EVENT_ID in {e["event_id"] for e in loaded["events"]}
    from scripts import build_theme_graph as bake

    monkeypatch.setattr(bake, "_ACTIVITY_BINDING_ROOT", ROOT)
    monkeypatch.setattr(bake.store, "probation_path",
                        lambda: events_path.parent / "proposals.jsonl")
    assert bake._activity_history_events() == loaded["events"]
    assert _warnings(capsys) == []

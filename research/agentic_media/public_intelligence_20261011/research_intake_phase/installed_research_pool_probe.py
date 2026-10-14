"""Read-only installed planner acceptance with isolated historical fixtures.

Run after protected landing: python -B probe.py /opt/macro reviewed-manifest.json.
No actual report is qualified, generated, staged or published by this probe.
"""
import contextlib
import copy
from datetime import date
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

root = Path(sys.argv[1]).resolve()
expected = json.loads(Path(sys.argv[2]).read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert {rel: sha(root / rel) for rel in expected} == expected, "reviewed source manifest drift"
sys.path.insert(0, str(root))
from engine.press import desk_planner as P, writer as W


def head():
    return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()


def snapshot():
    paths = [root / "config/press.yml", root / "data/press/published.jsonl",
             root / "data/research_vault/catalog.json"]
    paths += list((root / "data/press/staging").glob("*.json"))
    paths += list((root / "content/seo/blog").glob("*.md"))
    return {str(p.relative_to(root)): sha(p) for p in paths if p.is_file()}


cfg0 = P.load_config(root)
assert cfg0["desks"]["research_desk"]["candidate_pool"] == 8
assert cfg0["desks"]["research_desk"]["cadence_per_day"] == 1
assert cfg0["desks"]["research_note"]["cadence_per_day"] == 0
before_head, before = head(), snapshot()
controls = []
clock = date(2026, 7, 26)


def item(i):
    return {"id": f"pool-{i:02d}", "title": "Historical fixture: rates and households",
            "institution": "Fixture desk", "published_at": "2026-07-25T09:00:00Z",
            "summary_points": ["The desk reports household spending growth of 3 percent."],
            "pages": 8, "top_pick": False, "tags": [], "tickers": []}


with tempfile.TemporaryDirectory(prefix="mmx-research-pool-") as directory:
    parent = Path(directory)

    def fixture(name):
        path = parent / name
        (path / "data/research_vault").mkdir(parents=True)
        (path / "data/press/staging").mkdir(parents=True)
        cfg = copy.deepcopy(cfg0)
        # Only fixture destinations; the shipped production path definitions are unchanged.
        assert cfg["paths"]["staging_dir"] == "data/press/staging"
        assert cfg["paths"]["ledger"] == "data/press/published.jsonl"
        return path, cfg

    def plan(path, cfg, blocked=()):
        with contextlib.redirect_stdout(io.StringIO()):
            return P.plan(["research_desk", "research_note"], root=path, cfg=cfg,
                          as_of=clock.isoformat(), extra_blocked_refs=blocked)

    with patch.object(W, "write", side_effect=AssertionError("writer reached")) as writer:
        for ranked in (True, False):
            for mechanism in ("published", "staged", "explicit"):
                name = f"{mechanism}-{'ranked' if ranked else 'fallback'}"
                path, cfg = fixture(name)
                if not ranked:
                    cfg.pop("research_triage")
                    cfg["desks"]["research_desk"].pop("triage_tier")
                items = [item(i) for i in range(10)]
                catalog = path / "data/research_vault/catalog.json"
                catalog.write_text(json.dumps({"items": items}))
                with contextlib.redirect_stdout(io.StringIO()):
                    order, metadata = P._triage_order(cfg, clock, path, items)
                ids = order or [row["id"] for row in items]
                blocked = ["research_vault:" + rid for rid in ids[:8]]
                extra = []
                if mechanism == "published":
                    (path / cfg["paths"]["ledger"]).write_text(json.dumps({"sources": blocked}) + "\n")
                elif mechanism == "staged":
                    (path / cfg["paths"]["staging_dir"] / "held.json").write_text(
                        json.dumps({"id": "held", "status": "approval_required", "sources": blocked}))
                else:
                    extra = blocked

                def fixture_snapshot():
                    return {str(p.relative_to(path)): sha(p) for p in path.rglob("*") if p.is_file()}

                initial = fixture_snapshot()
                slots = plan(path, cfg, extra)
                assert [slot["sources"] for slot in slots] == [["research_vault:" + ids[8]]]
                assert slots[0]["desk"] == "research_desk"
                assert slots[0]["triage"]["rank"] == metadata.get(ids[8], {}).get("rank")
                assert initial == fixture_snapshot()
                controls.append(name)

        path, cfg = fixture("pool-bound")
        cfg.pop("research_triage")
        cfg["desks"]["research_desk"].pop("triage_tier")
        items = [item(i) for i in range(10)]
        for row in items[1:9]:
            row["summary_points"] = ["The current regime is a front-end signal."]
            assert not P._press_safe(row["summary_points"][0])
        catalog = path / "data/research_vault/catalog.json"
        catalog.write_text(json.dumps({"items": items}))
        assert plan(path, cfg, ["research_vault:pool-00"]) == []
        controls.append("eight-unblocked-candidate-budget-preserved")

        items = [dict(item(0), published_at="2026-07-27T09:00:00Z"),
                 dict(item(1), published_at="2026-07-04T09:00:00Z")]
        catalog.write_text(json.dumps({"items": items}))
        assert plan(path, cfg) == []
        controls.append("future-and-out-of-window-refusal")

        catalog.write_text(json.dumps({"items": [item(0)]}))
        cfg["desks"]["research_desk"]["cadence_per_day"] = 0
        assert plan(path, cfg) == []
        controls.append("zero-cadence-and-dark-note-preserved")
        assert writer.call_count == 0

assert before == snapshot() and before_head == head()
assert {rel: sha(root / rel) for rel in expected} == expected
print(json.dumps({"probe_passed": True, "controls": controls, "head": before_head,
    "execution_location": "installed_vps" if root == Path("/opt/macro") else "local_source",
    "checked_source_sha256": expected, "real_provider_calls": 0,
    "production_inputs_unchanged": True, "production_staging_writes": 0,
    "public_writes": 0, "d14_credit": 0,
    "scope": "Historical isolated planner fixtures; not source or publication approval"}, indent=2))

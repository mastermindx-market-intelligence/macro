"""Due dates request attention; only a live reader may report a new result.

Synthetic fixtures only. These tests use the existing producer and admin consumer.
"""
from datetime import date, datetime, timezone
import json
import pytest
from engine import experiments_registry as registry
from admin import experiments as admin

TODAY = date(2026, 9, 16)


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 16, 12, tzinfo=timezone.utc)
    monkeypatch.setattr(registry, "datetime", Clock)


def row(**changes):
    return dict({"id": "fixture", "name": "Fixture", "what": "Test only",
                 "kind": "track_record", "status": "accruing", "hook": "static",
                 "come_back_on": "2026-09-15"}, **changes)


def produce(monkeypatch, entries, hooks=None):
    seed = {"audited": "2026-06-30", "experiments": entries}
    monkeypatch.setattr(registry, "_read_json", lambda p: seed if p == registry.SEED else None)
    monkeypatch.setattr(registry, "_load_machine_registry_entries", lambda: [])
    if hooks is not None:
        monkeypatch.setattr(registry, "_HOOKS", hooks)
    return registry.compute()


def test_due_seed_does_not_manufacture_results(monkeypatch):
    payload = produce(monkeypatch, [row()])
    actual = payload["experiments"][0]
    assert actual["ready"] is False
    assert actual["result_ready"] is False
    assert actual["review_due"] is True
    assert actual["reader_status"] == "unwired"
    assert payload["ready_count"] == payload["result_ready_count"] == 0
    assert payload["review_due_count"] == payload["attention_count"] == 1


def test_real_reader_result_is_distinct_from_due_date(monkeypatch):
    payload = produce(monkeypatch, [row(hook="fixture", come_back_on="2099-01-01")],
                      {"fixture": lambda e: {"status": "null", "ready": True, "state": "graded"}})
    actual = payload["experiments"][0]
    assert actual["result_ready"] is True
    assert actual["reader_status"] == "observed"
    assert actual["review_due"] is False
    assert payload["result_ready_count"] == 1


@pytest.mark.parametrize("bad", ["true", "false", 1, [], {}, None])
def test_reader_readiness_must_be_a_boolean(monkeypatch, bad):
    actual = produce(monkeypatch, [row(hook="fixture")],
                     {"fixture": lambda e: {"state": "live", "ready": bad}})["experiments"][0]
    assert actual["result_ready"] is False


@pytest.mark.parametrize("status", ["validated", "proven", "gate_open", "no_go",
                                    "closed", "closed_no_go", "complete", "shipped", "retired"])
def test_concluded_records_do_not_reopen_on_a_calendar_date(monkeypatch, status):
    actual = produce(monkeypatch, [row(status=status)])["experiments"][0]
    assert actual["review_due"] is False
    assert actual["ready"] is False


def test_missing_reader_result_is_visible_not_a_fake_live_state(monkeypatch):
    actual = produce(monkeypatch, [row(hook="fixture")],
                     {"fixture": lambda e: {}})["experiments"][0]
    assert actual["reader_status"] == "unavailable"
    assert actual["review_due"] is True
    assert actual["result_ready"] is False


def test_reader_exception_preserves_review_without_inventing_a_result(monkeypatch):
    def broken(e):
        raise RuntimeError("fixture")
    actual = produce(monkeypatch, [row(hook="fixture")], {"fixture": broken})["experiments"][0]
    assert actual["reader_status"] == "error"
    assert actual["review_due"] is True
    assert actual["result_ready"] is False


def test_admin_does_not_trust_legacy_combined_ready(monkeypatch):
    monkeypatch.setattr(admin, "_today", lambda: TODAY)
    actual = admin._decorate(row(ready=True, state_live=True))
    assert actual["ready"] is False
    assert actual["result_ready"] is False
    assert actual["review_due"] is True
    assert actual["readiness_reason"] == "review_due"
    assert actual["reader_status"] == "legacy_unknown"


def test_admin_recalculates_dates_but_not_scientific_results(monkeypatch):
    payload = produce(monkeypatch, [row(come_back_on="2026-09-17")])
    monkeypatch.setattr(admin, "_today", lambda: date(2026, 9, 18))
    actual = admin._decorate(payload["experiments"][0])
    assert actual["review_due"] is True
    assert actual["result_ready"] is False


def test_admin_summary_counts_attention_once_and_exposes_both_reasons(monkeypatch, tmp_path):
    entries = [row(id="due"), row(id="result", hook="result", status="measuring"),
               row(id="scheduled", come_back_on="2026-09-20")]
    payload = produce(monkeypatch, entries, {"result": lambda e: {"ready": True, "state": "new"}})
    path = tmp_path / "experiments.json"
    path.write_text(json.dumps(payload))
    monkeypatch.setattr(admin, "_REGISTRY", path)
    monkeypatch.setattr(admin, "_today", lambda: TODAY)
    panel = admin.panel()
    assert panel["result_ready_count"] == panel["ready_count"] == 1
    assert panel["review_due_count"] == 2
    assert panel["attention_count"] == 2
    assert panel["experiments"][0]["id"] == "result"
    summary = admin.alert_summary()
    assert summary["attention_count"] == 2
    assert summary["result_ready_count"] == 1
    assert summary["review_due_count"] == 2
    assert summary["soonest"]["id"] == "scheduled"


def test_notification_names_due_review_without_claiming_results(monkeypatch, tmp_path):
    payload = produce(monkeypatch, [row()])
    from scripts import notify
    captured = []
    monkeypatch.setattr(registry.config, "load", lambda: {"notify": {"experiments_alerts": True}})
    monkeypatch.setattr(notify, "send_telegram", captured.append)
    monkeypatch.setattr(notify, "send_discord", lambda msg: None)
    path = tmp_path / "previous.json"
    registry._notify_newly_ready(path, payload)
    assert len(captured) == 1
    assert "review due" in captured[0].lower()
    assert "results ready" not in captured[0].lower()
    path.write_text(json.dumps(payload))
    registry._notify_newly_ready(path, payload)
    assert len(captured) == 1


@pytest.mark.parametrize("bad", ["true", "false", 1])
def test_qledger_reader_does_not_convert_truthy_strings_to_readiness(monkeypatch, bad):
    monkeypatch.setattr(registry, "_read_json", lambda p: {
        "promotion_readiness": {"fixture": {"5": {"n_dates": 30, "ready": bad}}}})
    out = registry._refresh_qledger_promotion({"claim_family": "fixture"})
    assert out["ready"] is False
    assert out["status"] == "accruing"


def render_experiments(payload):
    import shutil
    import subprocess
    from pathlib import Path
    node = shutil.which("node")
    assert node, "Node is required for the real JavaScript renderer contract"
    root = Path(__file__).resolve().parents[1]
    code = r"""
import fs from 'node:fs';
import vm from 'node:vm';
const source = fs.readFileSync(process.argv[1], 'utf8');
const payload = JSON.parse(process.argv[2]);
const begin = source.indexOf('/* ---- EXPERIMENTS & DATA COLLECTION');
const end = source.indexOf('/* ---- SITE ACCESS GATE', begin);
if (begin < 0 || end < begin) throw Error('Renderer boundary missing');
const view = {innerHTML: '', querySelectorAll: () => []};
const context = {RENDER: {}, api: async () => payload, $: () => view,
 card: (title, body) => `<section><h2>${title}</h2>${body}</section>`,
 esc: x => String(x ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;'),
 window: {}, post: () => {throw Error('No actions allowed in render test')}, toast: () => {}};
await vm.runInNewContext(source.slice(begin, end) + ';RENDER.experiments()', context);
process.stdout.write(view.innerHTML);
"""
    return subprocess.check_output([node, "--input-type=module", "-e", code,
                                    str(root / "admin/static/app.js"), json.dumps(payload)],
                                   text=True, timeout=10)


def test_real_renderer_separates_due_reviews_from_new_results(monkeypatch):
    payload = produce(monkeypatch, [row()], {})
    html = render_experiments({"ok": True, "today": TODAY.isoformat(), **payload})
    assert 'data-followup-kind="review_due"' in html
    assert 'data-followup-kind="result_ready"' not in html
    assert 'No new result reported' in html
    assert 'No live reader' in html
    assert 'experiments running' not in html


def test_real_renderer_does_not_trust_legacy_ready_boolean():
    html = render_experiments({"ok": True, "n": 1, "ready_count": 1,
                               "experiments": [row(ready=True)]})
    assert 'ready ✓' not in html
    assert 'data-followup-kind="result_ready"' not in html
    assert 'Counts need a registry refresh' in html


def test_real_renderer_shows_a_null_result_as_a_result_not_validation(monkeypatch):
    payload = produce(monkeypatch, [row(hook="fixture")],
                      {"fixture": lambda e: {"status": "null", "ready": True, "state": "graded null"}})
    html = render_experiments({"ok": True, **payload})
    assert 'data-followup-kind="result_ready"' in html
    assert 'graded null' in html
    assert '>validated<' not in html



def test_legacy_snapshot_reports_unknown_result_status_instead_of_certified_zero(monkeypatch, tmp_path):
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps({"n": 1, "ready_count": 1, "experiments": [row(ready=True)]}))
    monkeypatch.setattr(admin, "_REGISTRY", path)
    monkeypatch.setattr(admin, "_today", lambda: TODAY)
    payload = admin.panel()
    assert payload["result_status_unknown_count"] == 1
    assert payload["result_ready_count"] == 0
    assert 'Counts need a registry refresh' in render_experiments(payload)


def test_followup_tests_are_enrolled_in_existing_admin_ci():
    from pathlib import Path
    import yaml
    root = Path(__file__).resolve().parents[1]
    manifest = yaml.safe_load((root / ".github/ci/legacy-jobs.yml").read_text())
    job = manifest["jobs"]["admin-live-runs"]
    commands = "\n".join(str(step.get("run", "")) for step in job["steps"])
    assert 'tests/test_experiment_followup.py' in commands
    assert any(step.get("uses", "").startswith("actions/setup-node@") for step in job["steps"])



def test_reader_failure_does_not_describe_a_wired_reader_as_unwired(monkeypatch):
    def failed(e):
        raise RuntimeError("fixture")
    payload = produce(monkeypatch, [row(hook="fixture", state="Dated registry note")],
                      {"fixture": failed})
    html = render_experiments({"ok": True, **payload})
    assert 'Reader failed' in html
    assert 'no live reader is wired' not in html
    assert 'Dated registry note' in html


@pytest.mark.parametrize("job_id", ["biocatalyst-serving", "unrun-picks-boards"])
def test_followup_dependency_keeps_existing_consumers_in_ci_scope(job_id):
    """The registry's shared helper must not disappear from scoped consumer CI."""
    from pathlib import Path
    import yaml
    from scripts.run_ci_pack import _matches_any
    root = Path(__file__).resolve().parents[1]
    manifest = yaml.safe_load((root / ".github/ci/legacy-jobs.yml").read_text())
    paths = manifest["jobs"][job_id]["paths"]
    assert _matches_any(paths, "engine/experiments_registry.py")
    assert _matches_any(paths, "engine/experiment_followup.py"), (
        f"{job_id} reaches the follow-up helper through the registry but does not "
        "run when that helper changes"
    )

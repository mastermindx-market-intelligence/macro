"""Successful transaction cues, using real git blobs and the canonical exporter."""
import json
from pathlib import Path
import subprocess
import os
import re

import pytest
import yaml

from scripts import check_shared_shell_publication_delta as guard
from tests.test_export_shared_shell_routes import _git, _write, _commit, fixture_registry_row


@pytest.fixture()
def publication(tmp_path, monkeypatch):
    repo = tmp_path / "publication"
    repo.mkdir()
    _git(repo, "init", "--quiet")
    pin = _commit(repo, "root")
    registry = {
        "schema": "mastermind.page_registry.v1", "generated_at": "2026-11-02T00:00:00Z",
        "sources": {"macro": {"sha": pin}, "terminal": {"sha": "b" * 40},
                    "mastermind": {"sha": "c" * 40, "available": True}},
        "pages": [fixture_registry_row("/stocks/<id>.html", kind="family")],
    }
    _write(repo, guard.SOURCE_PATHS["registry"], json.dumps(registry))
    _write(repo, guard.SOURCE_PATHS["access_policy"], "deny:\n  exact: []\n  prefixes: []\n")
    _write(repo, guard.SOURCE_PATHS["exporter"], Path(guard.exporter.__file__).read_text())
    _write(repo, "site/stocks/old.html", "<!doctype html><title>old</title>")
    before = _commit(repo, "accepted public source")
    monkeypatch.setattr(guard, "ROOT", repo)

    def finish():
        after = _commit(repo, "successful publication")
        _git(repo, "update-ref", "refs/remotes/origin/main", after)
        return after

    return repo, before, finish


def test_no_html_fast_path_never_probes_documents(publication, monkeypatch):
    repo, before, finish = publication
    _write(repo, "site/data.json", "{}")
    after = finish()
    monkeypatch.setattr(guard.exporter, "document_inventory", lambda *_: pytest.fail("full scan"))
    assert guard.publication_delta(before, after) is None


def test_content_only_change_is_not_an_admission(publication, tmp_path):
    repo, before, finish = publication
    _write(repo, "site/stocks/old.html", "<!doctype html><title>new stamp</title>")
    output = tmp_path / "no-cue.json"
    assert guard.emit(before, finish(), output) is False
    assert not output.exists()


def test_real_new_and_withdrawn_members_keep_changed_exclusions(publication, tmp_path, monkeypatch):
    repo, before, finish = publication
    (repo / "site/stocks/old.html").unlink()
    _write(repo, "site/stocks/new.html", "<!doctype html><title>new</title>")
    _write(repo, "site/stocks/fragment.html", "<p>fragment</p>")
    _write(repo, "site/unregistered.html", "<!doctype html><title>unknown</title>")
    after = finish()
    original = guard.exporter.document_inventory
    calls = []

    def probe(root, ref, paths):
        calls.append((ref, list(paths)))
        return original(root, ref, paths)

    monkeypatch.setattr(guard.exporter, "document_inventory", probe)
    output = tmp_path / "cue.json"
    assert guard.emit(before, after, output)
    cue = json.loads(output.read_text())
    assert cue["added"] == ["/stocks/new.html"]
    assert cue["removed"] == ["/stocks/old.html"]
    assert cue["changed_html_count"] == 4
    assert cue["excluded_after"] == [
        {"path": "/stocks/fragment.html", "reason": "html_fragment"},
        {"path": "/unregistered.html", "reason": "unregistered"},
    ]
    assert calls[0] == (before, ["/stocks/old.html"])
    assert calls[1][0] == after and len(calls[1][1]) == 3
    assert not cue["accepted"] and cue["review_required"]
    assert not cue["full_inventory_review_required"]
    assert after in cue["owner_action"][3]


def test_excluded_new_paths_alone_do_not_create_false_admission_cue(publication):
    repo, before, finish = publication
    _write(repo, "site/stocks/fragment.html", "<p>fragment</p>")
    _write(repo, "site/unknown.html", "<!doctype html><title>unknown</title>")
    assert guard.publication_delta(before, finish()) is None


@pytest.mark.parametrize("source", ["registry", "access_policy"])
def test_policy_change_requires_full_review_even_without_html_delta(publication, source):
    repo, before, finish = publication
    path = repo / guard.SOURCE_PATHS[source]
    if source == "registry":
        doc = json.loads(path.read_text())
        doc["pages"][0]["lifecycle"] = "lab"
        path.write_text(json.dumps(doc))
    else:
        path.write_text("deny:\n  exact: [/stocks/old.html]\n  prefixes: []\n")
    cue = guard.publication_delta(before, finish())
    assert cue["policy_changed"][source] and cue["full_inventory_review_required"]
    assert cue["changed_html_count"] == 0 and cue["added"] == cue["removed"] == []


def test_wrong_loaded_exporter_cannot_emit_a_publication_claim(publication):
    repo, before, finish = publication
    _write(repo, guard.SOURCE_PATHS["exporter"], "# different exporter\n")
    with pytest.raises(ValueError, match="loaded exporter"):
        guard.publication_delta(before, finish())


def test_changed_classifier_cue_does_not_invent_the_old_classification(publication):
    repo, _, finish = publication
    source = Path(guard.exporter.__file__).read_text()
    _write(repo, guard.SOURCE_PATHS["exporter"], source + "\n# prior classifier\n")
    before = _commit(repo, "prior classifier")
    _write(repo, guard.SOURCE_PATHS["exporter"], source)
    _write(repo, "site/stocks/new.html", "<!doctype html><title>new</title>")
    cue = guard.publication_delta(before, finish())
    assert cue["full_inventory_review_required"]
    assert cue["membership_comparison"] == "not_computed_exporter_changed"
    assert cue["added"] == cue["removed"] == []


@pytest.mark.parametrize("malformed", ["deny:\n  exact: /stocks/new.html\n", "deny: false\n", "false\n"])
def test_malformed_serving_policy_cannot_weaken_admission(publication, tmp_path, malformed):
    repo, before, finish = publication
    _write(repo, guard.SOURCE_PATHS["access_policy"], malformed)
    _write(repo, "site/stocks/new.html", "<!doctype html><title>new</title>")
    with pytest.raises(ValueError, match="policy"):
        guard.emit(before, finish(), tmp_path / "never.json")
    assert not (tmp_path / "never.json").exists()


def test_cli_distinguishes_cue_no_change_and_invalid_source(publication, tmp_path, monkeypatch):
    repo, before, finish = publication
    _write(repo, "site/stocks/new.html", "<!doctype html><title>new</title>")
    after = finish()
    output = tmp_path / "cue.json"
    monkeypatch.setattr("sys.argv", ["guard", "--before", before, "--after", after,
                                     "--output", str(output)])
    assert guard.main() == 3 and output.exists()
    _write(repo, "site/stocks/new.html", "<!doctype html><title>new content</title>")
    newest = finish()
    output = tmp_path / "no-cue.json"
    monkeypatch.setattr("sys.argv", ["guard", "--before", after, "--after", newest,
                                     "--output", str(output)])
    assert guard.main() == 0 and not output.exists()
    monkeypatch.setattr("sys.argv", ["guard", "--before", "main", "--after", newest,
                                     "--output", str(output)])
    assert guard.main() == 1 and not output.exists()


@pytest.mark.parametrize("identity", ["HEAD", "A" * 40, "1" * 39])
def test_mutable_or_malformed_identity_refused_before_output(publication, tmp_path, identity):
    _, before, finish = publication
    after = finish()
    output = tmp_path / "refused.json"
    with pytest.raises(ValueError, match="exact lowercase"):
        guard.emit(before, identity, output)
    assert not output.exists()
    with pytest.raises(ValueError, match="distinct"):
        guard.emit(after, after, output)


def test_unprotected_and_reversed_commits_refused(publication, tmp_path):
    repo, before, finish = publication
    after = finish()
    _git(repo, "update-ref", "refs/remotes/origin/main", before)
    for old, new in [(before, after), (after, before)]:
        with pytest.raises(subprocess.CalledProcessError):
            guard.emit(old, new, tmp_path / "never.json")
    assert not (tmp_path / "never.json").exists()


@pytest.mark.parametrize("invalid", ["missing", "unavailable", "bad-sha", "bad-schema"])
def test_missing_or_unqualified_source_preserves_no_artifact(publication, tmp_path, invalid):
    repo, before, finish = publication
    path = repo / guard.SOURCE_PATHS["registry"]
    doc = json.loads(path.read_text())
    if invalid == "missing":
        path.unlink()
    else:
        if invalid == "unavailable":
            doc["sources"]["terminal"]["available"] = False
        elif invalid == "bad-sha":
            doc["sources"]["mastermind"]["sha"] = "master"
        else:
            doc["schema"] = "other"
        path.write_text(json.dumps(doc))
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        guard.emit(before, finish(), tmp_path / "never.json")
    assert not (tmp_path / "never.json").exists()


def test_existing_receipt_is_not_replaced(publication, tmp_path):
    _, before, finish = publication
    output = tmp_path / "retained.json"
    output.write_text("original")
    with pytest.raises(ValueError, match="replace"):
        guard.emit(before, finish(), output)
    assert output.read_text() == "original"


def test_workflow_seam_records_only_success_and_keeps_failure_audit():
    workflow = yaml.safe_load((Path(__file__).resolve().parents[1] /
                               ".github/workflows/earnings-public-wire.yml").read_text())
    steps = workflow["jobs"]["publish"]["steps"]
    publish = next(step for step in steps if step.get("id") == "publication")
    script = publish["run"]
    success = script.index("if push_do origin HEAD:main; then")
    output = script.index("published_sha=%s")
    assert output > success > script.index("if git diff --cached --quiet; then")
    assert script[success:output].count("push_won") == 1
    classify = next(step for step in steps if step.get("id") == "shared_shell_delta")
    assert classify["if"] == "${{ steps.publication.outputs.published_sha != '' }}"
    assert "exit \"$delta_rc\"" in classify["run"]
    retain = next(step for step in steps if step.get("uses") == "actions/upload-artifact@v4")
    assert "always()" in retain["if"] and "artifact_written" in retain["if"]
    assert steps[-1]["name"] == "earnings archive staleness tripwire"
    assert steps[-1]["if"] == "always()"


@pytest.mark.parametrize("attempts", [(1,), (1, 1), (1, 0), (0,)])
def test_actual_success_shell_branch_emits_one_exact_transaction_only(tmp_path, attempts):
    workflow = yaml.safe_load((Path(__file__).resolve().parents[1] /
                               ".github/workflows/earnings-public-wire.yml").read_text())
    script = next(step for step in workflow["jobs"]["publish"]["steps"]
                  if step.get("id") == "publication")["run"]
    branch = re.search(r"if push_do origin HEAD:main; then\n.*?\n\s*fi", script, re.S)[0]
    prefix = 'push_won(){ :; }; git(){ printf "%s\\n" "$AFTER"; }; WIRE_BASE="$BEFORE"\n'
    body = prefix + "\n".join(f"push_do(){{ return {rc}; }};\n{branch}" for rc in attempts)
    output = tmp_path / "outputs"
    before, after = "a" * 40, "b" * 40
    result = subprocess.run(["bash", "-c", body], capture_output=True, text=True,
                            env={**os.environ, "BEFORE": before, "AFTER": after,
                                 "GITHUB_OUTPUT": str(output), "PUSH_ATTEMPT": "2"})
    assert result.returncode == 0
    if 0 in attempts:
        assert output.read_text() == f"base_sha={before}\npublished_sha={after}\n"
    else:
        assert not output.exists()

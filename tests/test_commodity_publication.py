"""The publication guard preserves accepted R3 through a real stale-render race."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from scripts import check_commodity_publication as guard


def git(repo, *args):
    result = subprocess.run(
        ["git", "-C", str(repo), *args], text=True, capture_output=True, check=True
    )
    return result.stdout.strip()


def page(*, revision=6, schema="mmx.commodities.workspace.v1", stamp="accepted",
         mount=True, payload=True, extra="", assets=""):
    value = {
        "schema": schema, "projection_revision": revision,
        "fingerprint": "a" * 64, "as_of": None, "display_only": True, "live": False,
        "assets": [], "chains": [],
        "research": {"effect": "export_only", "monitoring_active": False},
    }
    body = f'<section id="commodity-workspace">{stamp}</section>' if mount else stamp
    script = '<script id="cw-data" type="application/json">' + json.dumps(value) + "</script>"
    return "<html><head>" + assets + "</head><body>" + body + (script if payload else "") + extra + "</body></html>"


def commit(repo, message):
    git(repo, "add", ".")
    git(repo, "-c", "user.name=Publication test", "-c", "user.email=publication@example.test",
        "commit", "-qm", message)
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "site").mkdir()
    destination = tmp_path / "site" / "commodities.html"
    destination.write_text(page())
    (tmp_path / "site" / "other.html").write_text("accepted other page")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "source.json").write_text('{"unchanged":true}')
    commit(tmp_path, "accepted research workspace")
    return tmp_path


def test_valid_same_revision_keeps_candidate_without_claiming_freshness(repo):
    destination = repo / guard.PAGE
    candidate = page(stamp="another observation with the same projection")
    destination.write_text(candidate)
    result = guard.verify_publication(repo, "main", heal=True)
    assert result["action"] == "kept"
    assert destination.read_text() == candidate
    assert result["freshness_verified"] is False


@pytest.mark.parametrize("broken", [
    page(mount=False), page(payload=False), page(revision=5),
    page(extra='<script id="cw-data" type="application/json">{}</script>'),
    page().replace('id="commodity-workspace"', 'id="commodity-workspace"></section><section id="commodity-workspace"'),
    page().replace('"projection_revision": 6', '"projection_revision": true'),
    page().replace('"display_only": true', '"display_only": false'),
    page().replace('"live": false', '"live": true'),
    page().replace('"monitoring_active": false', '"monitoring_active": true'),
    page().replace('"effect": "export_only"', '"effect": "monitor"'),
    page().replace('"fingerprint": "' + "a" * 64 + '"', '"fingerprint": "bad"'),
    page().replace('"as_of": null', '"as_of": NaN'),
    page().replace('"live": false', '"live": true, "live": false'),
    page().replace('type="application/json"', 'type="text/javascript"'),
    '<section id="commodity-workspace"></section><script id="cw-data" type="application/json">{bad</script>',
])
def test_bad_candidate_restores_whole_accepted_page_only(repo, broken):
    accepted = git(repo, "rev-parse", "main")
    destination = repo / guard.PAGE
    expected = destination.read_bytes()
    source_before = (repo / "data/source.json").read_bytes()
    other_before = (repo / "site/other.html").read_bytes()
    destination.write_text(broken)
    result = guard.verify_publication(repo, accepted, heal=True)
    assert result["action"] == "restored"
    assert result["accepted_commit"] == accepted
    assert destination.read_bytes() == expected
    assert (repo / "data/source.json").read_bytes() == source_before
    assert (repo / "site/other.html").read_bytes() == other_before
    assert git(repo, "status", "--porcelain") == ""


def test_missing_candidate_file_can_restore_accepted_regular_page(repo):
    destination = repo / guard.PAGE
    expected = destination.read_bytes()
    destination.unlink()
    assert guard.verify_publication(repo, "main", heal=True)["action"] == "restored"
    assert destination.read_bytes() == expected


@pytest.mark.parametrize("broken", [
    "legacy only", page(payload=False),
    page(extra='<script id="cw-data" type="application/json">{}</script>'),
])
def test_invalid_accepted_page_refuses_without_rewriting_candidate(repo, broken):
    destination = repo / guard.PAGE
    destination.write_text(broken)
    commit(repo, "invalid accepted fixture")
    candidate = page(stamp="candidate kept on refusal")
    destination.write_text(candidate)
    with pytest.raises(guard.PublicationError, match="accepted"):
        guard.verify_publication(repo, "main", heal=True)
    assert destination.read_text() == candidate


def test_unreadable_accepted_ref_is_not_clean(repo):
    destination = repo / guard.PAGE
    before = destination.read_bytes()
    with pytest.raises(guard.PublicationError, match="resolve"):
        guard.verify_publication(repo, "refs/heads/not-present", heal=True)
    assert destination.read_bytes() == before


@pytest.mark.parametrize("candidate", [
    page(revision=7), page(schema="mmx.commodities.workspace.v2")
])
def test_unreviewed_contract_transition_is_not_silently_overwritten(repo, candidate):
    destination = repo / guard.PAGE
    destination.write_text(candidate)
    with pytest.raises(guard.PublicationError, match="unsupported"):
        guard.verify_publication(repo, "main", heal=True)
    assert destination.read_text() == candidate


def test_explicitly_supported_revision_can_advance_without_restoration(repo, monkeypatch):
    monkeypatch.setattr(guard, "PROJECTION_REVISION", 7)
    destination = repo / guard.PAGE
    candidate = page(revision=7, stamp="reviewed successor")
    destination.write_text(candidate)
    assert guard.verify_publication(repo, "main", heal=True)["action"] == "kept"
    assert destination.read_text() == candidate


def test_older_accepted_page_cannot_heal_newer_required_contract(repo, monkeypatch):
    monkeypatch.setattr(guard, "PROJECTION_REVISION", 7)
    destination = repo / guard.PAGE
    destination.write_text("legacy only")
    with pytest.raises(guard.PublicationError, match="revision"):
        guard.verify_publication(repo, "main", heal=True)
    assert destination.read_text() == "legacy only"


def test_pinned_accepted_commit_is_not_a_later_moving_branch(repo):
    accepted = git(repo, "rev-parse", "main")
    destination = repo / guard.PAGE
    expected = destination.read_bytes()
    destination.write_text(page(stamp="later main"))
    commit(repo, "later accepted page")
    destination.write_text("stale renderer")
    result = guard.verify_publication(repo, accepted, heal=True)
    assert result["accepted_commit"] == accepted
    assert destination.read_bytes() == expected


def test_real_rebase_race_repairs_only_commodity_page(repo):
    destination = repo / guard.PAGE
    destination.write_text("legacy page")
    initial = commit(repo, "legacy baseline")
    git(repo, "checkout", "-qb", "accepted")
    destination.write_text(page())
    accepted = commit(repo, "introduce workspace")
    git(repo, "checkout", "-qb", "stale-render", initial)
    destination.write_text("newer render from legacy source")
    (repo / "site/other.html").write_text("independent new rendering")
    commit(repo, "render legacy source")
    git(repo, "rebase", "-X", "theirs", accepted)
    assert "commodity-workspace" not in destination.read_text()
    result = guard.verify_publication(repo, accepted, heal=True)
    assert result["action"] == "restored"
    assert destination.read_text() == page()
    assert (repo / "site/other.html").read_text() == "independent new rendering"
    assert git(repo, "diff", "--name-only") == guard.PAGE
    assert json.loads((repo / "data/source.json").read_text()) == {"unchanged": True}


def test_missing_fallback_asset_refuses_before_any_page_write(repo):
    destination = repo / guard.PAGE
    destination.write_text(page(assets='<link rel="stylesheet" href="assets/css/old.css?v=1">'))
    css = repo / "site/assets/css/old.css"
    css.parent.mkdir(parents=True)
    css.write_text("body{}")
    accepted = commit(repo, "accepted externalized page")
    destination.write_text("stale renderer")
    css.unlink()
    with pytest.raises(guard.PublicationError, match="asset"):
        guard.verify_publication(repo, accepted, heal=True)
    assert destination.read_text() == "stale renderer"


def test_existing_css_and_js_allow_exact_whole_page_recovery(repo):
    destination = repo / guard.PAGE
    assets = '<link rel="stylesheet" href="/assets/css/old.css?v=1"><script src="assets/js/old.js"></script>'
    destination.write_text(page(assets=assets))
    for name in ["site/assets/css/old.css", "site/assets/js/old.js"]:
        asset = repo / name
        asset.parent.mkdir(parents=True, exist_ok=True)
        asset.write_text("/* accepted */")
    accepted = commit(repo, "accepted assets")
    expected = destination.read_bytes()
    destination.write_text("stale")
    assert guard.verify_publication(repo, accepted, heal=True)["action"] == "restored"
    assert destination.read_bytes() == expected


def test_metadata_candidate_is_checked_as_git_tree_not_clean_worktree(repo):
    accepted = git(repo, "rev-parse", "main")
    destination = repo / guard.PAGE
    destination.write_text("stale metadata replay")
    candidate = commit(repo, "bad replay candidate")
    git(repo, "checkout", "--detach", accepted)
    before = destination.read_bytes()
    with pytest.raises(guard.PublicationError, match="candidate"):
        guard.verify_publication(repo, accepted, candidate_ref=candidate)
    assert destination.read_bytes() == before
    assert git(repo, "status", "--porcelain") == ""


def test_committed_candidate_cannot_pass_using_uncommitted_repair(repo):
    accepted = git(repo, "rev-parse", "main")
    destination = repo / guard.PAGE
    expected = destination.read_bytes()
    destination.write_text("stale published tree")
    candidate = commit(repo, "old renderer")
    destination.write_bytes(expected)
    with pytest.raises(guard.PublicationError, match="candidate"):
        guard.verify_publication(repo, accepted, candidate_ref=candidate)
    assert destination.read_bytes() == expected


def test_committed_asset_check_ignores_uncommitted_asset_file(repo):
    accepted = git(repo, "rev-parse", "main")
    destination = repo / guard.PAGE
    destination.write_text(page(assets='<script src="assets/js/missing.js"></script>'))
    candidate = commit(repo, "page without committed script")
    asset = repo / "site/assets/js/missing.js"
    asset.parent.mkdir(parents=True)
    asset.write_text("/* only worktree */")
    with pytest.raises(guard.PublicationError, match="asset"):
        guard.verify_publication(repo, accepted, candidate_ref=candidate)


def test_read_only_git_candidate_preserves_worktree(repo):
    accepted = git(repo, "rev-parse", "main")
    destination = repo / guard.PAGE
    destination.write_text("uncommitted content must stay untouched")
    result = guard.verify_publication(repo, accepted, candidate_ref=accepted)
    assert result["action"] == "kept"
    assert result["candidate_commit"] == accepted
    assert destination.read_text() == "uncommitted content must stay untouched"


@pytest.mark.parametrize("outside", [False, True])
def test_symlinked_site_directory_refuses_without_writing_target(repo, outside):
    site = repo / "site"
    target = repo.parent / (repo.name + "-outside") if outside else repo / "relocated-site"
    site.rename(target)
    site.symlink_to(target, target_is_directory=True)
    destination = target / "commodities.html"
    destination.write_text("stale renderer through a symlink")
    other_before = (target / "other.html").read_bytes()
    source_before = (repo / "data/source.json").read_bytes()
    with pytest.raises(guard.PublicationError, match="real site directory"):
        guard.verify_publication(repo, "main", heal=True)
    assert destination.read_text() == "stale renderer through a symlink"
    assert (target / "other.html").read_bytes() == other_before
    assert (repo / "data/source.json").read_bytes() == source_before
    assert site.is_symlink()

"""Consolidated AI Daily Brief page (aibrief.html) render + nav-cleanup regression.

The old deterministic daily brief (scripts/daily_brief.py -> brief.html, plus the
china/hk variants) was retired and replaced by ONE static page that surfaces the
three EXISTING AI briefs written by engine/master_brain.py
(master_brief.json / china_brief.json / btc_brief.json) as toggle tabs.

ABX v2 (2026-07-19): the three lens brief BODIES are now SERVER-rendered by the
shared macro templates/_aibrief_body.html.j2 (build_aibrief.py loads the JSONs into
master_brief / china_brief / btc_brief). templates/aibrief.js was slimmed to the
overnight-cortex panel only. These tests render the REAL template (same Jinja env
as scripts/build_aibrief) and guard, at the source level, that no template ever
re-links the deleted brief pages.
"""
from __future__ import annotations

import json

import pytest
import jinja2

from engine import i18n
from lib import config


def _env() -> jinja2.Environment:
    """Mirror scripts/build_aibrief.main()'s template environment."""
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(config.ROOT / "templates"))
    env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    return env


def _render(**briefs) -> str:
    """Render aibrief.html.j2 with the server-side panels absent (fail-open) and any
    passed lens briefs. Absent briefs render the honest 'not generated yet' note."""
    panels = {
        "ctx_strip": {"absent": True},
        "fwd_panel": {"absent": True, "events": [], "rebal_note_en": None, "rebal_note_zh": None},
        "record_panel": {"absent": True},
    }
    return _env().get_template("aibrief.html.j2").render(
        as_of="2026-06-14 12:00 UTC", **panels, **briefs
    )


def _committed_brief(name: str) -> dict:
    return json.loads((config.ROOT / "site" / name).read_text())


def test_three_lens_panels_present():
    """One .ai-brief panel per lens (server-rendered — no client fetch stubs)."""
    html = _render()
    assert html.count("ai-brief") >= 3
    # the client-fetch attributes are GONE (bodies are server-rendered now)
    assert "data-brief-src" not in html
    assert "data-brief-body" not in html


def test_committed_briefs_render_server_side():
    """The committed (v1-shaped) briefs render into the page via the shared macro —
    the v2 body must fail open on v1 payloads (no tldr → summary lead, no crash)."""
    html = _render(
        master_brief=_committed_brief("master_brief.json"),
        china_brief=_committed_brief("china_brief.json"),
        btc_brief=_committed_brief("btc_brief.json"),
    )
    # server-rendered macro body present (namespace .aib2-*), badge is house law
    assert '"aib2"' in html or 'class="aib2"' in html
    assert "not a signal source" in html
    # v1 payloads have no tldr → the summary lead-card fallback renders, no stance pill
    assert "aib2-lead" in html


def test_absent_brief_shows_honest_note():
    """No brief for a lens → an honest 'not generated yet' note, never a stray body."""
    html = _render()  # all briefs absent
    assert "has not generated yet" in html
    assert '"aib2"' not in html  # no empty body frame when all absent


def test_toggle_tabs_present():
    """Three market toggle buttons, one per lens."""
    html = _render()
    assert 'data-lens="macro"' in html
    assert 'data-lens="china"' in html
    assert 'data-lens="btc"' in html
    assert "Macro" in html and "China" in html and "Bitcoin" in html
    # exactly one panel is active by default (class-driven visibility)
    assert html.count("brief-tab active") == 1


def test_required_assets_loaded():
    """The page needs theme.css/.js + aibrief.js (cortex panel is still client-side)."""
    html = _render()
    assert 'href="theme.css"' in html
    assert 'src="theme.js"' in html
    assert 'src="aibrief.js"' in html


def test_per_lens_cadence_copy_no_blanket_daily_claim():
    """SPEC §7: the page no longer claims a blanket 'each day' refresh — BTC is every
    three days. The intro must state the split cadence honestly."""
    html = _render()
    assert "every three days" in html  # BTC honesty
    # the retired blanket claim must be gone
    assert "Regenerated automatically each day after the close" not in html


def test_static_nav_button_present():
    """The renamed 'AI Daily Brief' entry lives in the nav-ctrls cluster."""
    html = _render()
    assert "AI Daily Brief" in html
    assert 'class="ai-brief-link' in html
    assert 'class="nav-ctrls"' in html


def test_page_does_not_link_old_brief_pages():
    """The new page must not reference the retired brief HTML files. NOTE: the exact
    href= form matters — 'aibrief.html' contains the substring 'brief.html'."""
    html = _render()
    assert 'href="brief.html"' not in html
    assert 'href="china_brief.html"' not in html
    assert 'href="hk_brief.html"' not in html
    # The header's external entry is Terminal. The old "Mastermind" nav pill was
    # removed 2026-08-01 — theme.js injects mm_brain.js sitewide, which mounts its
    # own bottom-right launcher, so the pill was a duplicate entry point.
    #
    # Scoped to `.nav-ctrls` since 2026-08-07: the guard was written when NO Bot
    # link existed anywhere, so a whole-page substring read as "the header has no
    # Bot pill". The Bot now has a legitimate Research mega-menu card, and the
    # header contract is what this line always meant. theme.js:1492 strips any
    # `.nav-ctrls a[href*="bot.mastermind-x.com"]` at runtime; the SOURCE must not
    # lean on that, so the control cluster ships without one.
    ctrls = html[html.find('<div class="nav-ctrls">'):]
    ctrls = ctrls[:ctrls.find("</nav>")]
    assert ctrls, "the shared header lost its .nav-ctrls control cluster"
    assert 'href="https://app.mastermind-x.com"' in ctrls
    assert "bot.mastermind-x.com" not in ctrls


def test_no_template_links_deleted_brief_pages():
    """Source-level guard across EVERY template: the deterministic brief pages are
    gone, so nothing may link brief.html / china_brief.html / hk_brief.html (in any
    relative form). Locks in the nav cleanup against future drift."""
    bad = ('href="brief.html"', 'href="../brief.html"',
           'href="china_brief.html"', 'href="../china_brief.html"',
           'href="hk_brief.html"', 'href="../hk_brief.html"')
    offenders = []
    for path in sorted((config.ROOT / "templates").glob("*.html.j2")):
        src = path.read_text()
        for needle in bad:
            if needle in src:
                offenders.append(f"{path.name}: {needle}")
    assert not offenders, "templates still link retired brief pages: " + "; ".join(offenders)


# Publication must prove modal content, not just a date or a render watermark.
def _publication_fixture(root):
    from pathlib import Path

    payload = {"lens": "china", "state_asof": "2026-11-03",
               "summary": "Growth & demand have cooled.", "regime_read": "Liquidity is tight.",
               "confidence": "medium", "conflicts": ["Credit: demand remains weak"],
               "watch_items": ["Policy: watch the next release"],
               "zh": {"summary": "增长与需求降温。", "regime_read": "流动性收紧。"}}
    (root / "templates").mkdir()
    (root / "site").mkdir()
    template = (Path(config.ROOT) / "templates/_aibrief_body.html.j2").read_text()
    (root / "templates/_aibrief_body.html.j2").write_text(template)
    (root / "site/china_brief.json").write_text(json.dumps(payload))
    (root / "site/master_brief.json").write_text(json.dumps({
        "lens": "macro", "state_asof": "2026-11-03",
        "summary": "US macro outlook remains cautious.",
    }))
    (root / "site/btc_brief.json").write_text(json.dumps({
        "lens": "btc", "state_asof": "2026-11-03",
        "summary": "Bitcoin liquidity and funding remain mixed.",
    }))
    _publication_pages(root, payload)
    return payload


def _publication_pages(root, payload):
    for region, prefix in (("china", "cnx"), ("hk", "hkx")):
        source = (
            '{% import "_aibrief_body.html.j2" as aib %}'
            '<section id="' + prefix + '-dlg-aibrief">'
            '{% call aib.aibrief_body(brief, "china", show_catalysts=False) %}'
            '<div class="' + prefix + '-receipt">Caller-owned receipt <a href="aibrief.html">link</a></div>'
            '{% endcall %}</section>'
        )
        (root / ("site/" + region + ".html")).write_text(_env().from_string(source).render(brief=payload))
    # The standalone page embeds all three lenses; it must be checked too when
    # the renderer owns macro scope, not silently left at its previous epoch.
    macro = json.loads((root / "site/master_brief.json").read_text())
    btc = json.loads((root / "site/btc_brief.json").read_text())
    (root / "site/aibrief.html").write_text(
        _render(master_brief=macro, china_brief=payload, btc_brief=btc)
    )


def test_brief_publication_compares_bilingual_component_with_footer_variations(tmp_path):
    from scripts import check_aibrief_publication as pub

    _publication_fixture(tmp_path)
    china = tmp_path / "site/china.html"
    html = china.read_text().replace('class="aib2"', 'class="aib2 css-generated"')
    html = html.replace("Growth & demand", "Growth &amp; demand")
    html = html.replace("Caller-owned receipt", "A different nightly footer")
    china.write_text(html)
    assert pub.check(tmp_path, "china+hk") == ["china", "hk"]


@pytest.mark.parametrize("same_date", [True, False])
def test_brief_publication_refuses_old_content_even_with_a_new_date(tmp_path, same_date):
    from scripts import check_aibrief_publication as pub

    payload = _publication_fixture(tmp_path)
    payload["summary"] = "The latest narrative is materially different."
    payload["zh"]["summary"] = "最新解读已经变化。"
    if not same_date:
        payload["state_asof"] = "2026-11-04"
        for region in ("china", "hk"):
            page = tmp_path / ("site/" + region + ".html")
            page.write_text(page.read_text().replace("2026-11-03", "2026-11-04"))
    (tmp_path / "site/china_brief.json").write_text(json.dumps(payload))
    with pytest.raises(pub.PublicationError, match="does not match"):
        pub.check(tmp_path, "china+hk")


@pytest.mark.parametrize("mutation", ["wrong_lens", "missing", "old_chinese"])
def test_brief_publication_refuses_incomplete_modal_adoption(tmp_path, mutation):
    from scripts import check_aibrief_publication as pub

    _publication_fixture(tmp_path)
    page = tmp_path / "site/hk.html"
    html = page.read_text()
    if mutation == "wrong_lens":
        html = html.replace('data-lens="china"', 'data-lens="macro"')
    elif mutation == "missing":
        html = "<div>Previous page without its brief</div>"
    else:
        html = html.replace("增长与需求降温。", "旧的中文解读。")
    page.write_text(html)
    assert pub.check(tmp_path, "china") == ["china"]
    with pytest.raises(pub.PublicationError):
        pub.check(tmp_path, "all")


def test_brief_publication_checks_commit_after_replay_not_only_worktree(tmp_path):
    import subprocess
    from scripts import check_aibrief_publication as pub

    def git(*args):
        return subprocess.run(["git", "-C", str(tmp_path), *args],
                              capture_output=True, text=True, check=True).stdout.strip()

    payload = _publication_fixture(tmp_path)
    git("init", "-q", "-b", "main")
    git("config", "user.name", "brief-test")
    git("config", "user.email", "brief-test@example.invalid")
    git("config", "commit.gpgsign", "false")
    git("add", ".")
    git("commit", "-qm", "first complete brief")
    assert pub.check(tmp_path, "all", "HEAD") == ["china", "hk", "macro"]
    payload["summary"] = "A newer accepted brief landed during publication."
    (tmp_path / "site/china_brief.json").write_text(json.dumps(payload))
    git("add", "site/china_brief.json")
    git("commit", "-qm", "replayed candidate has a new input and old pages")
    _publication_pages(tmp_path, payload)  # correct worktree must not certify stale HEAD
    assert pub.check(tmp_path, "all") == ["china", "hk", "macro"]
    with pytest.raises(pub.PublicationError, match="does not match"):
        pub.check(tmp_path, "all", "HEAD")


def test_brief_publication_is_wired_to_both_exact_push_candidates():
    from pathlib import Path
    import yaml

    root = Path(config.ROOT)
    workflow = yaml.safe_load((root / ".github/workflows/render.yml").read_text())
    steps = workflow["jobs"]["render"]["steps"]
    publisher = next(s["run"] for s in steps if s.get("name", "").startswith("commit rendered site"))
    replay = 'scripts.check_aibrief_publication --scope "${{ steps.pick.outputs.scope }}" --candidate-ref "$PUBLISH_COMMIT"'
    committed = 'scripts.check_aibrief_publication --scope "${{ steps.pick.outputs.scope }}" --candidate-ref HEAD'
    assert publisher.index(replay) < publisher.index('if push_do origin "$PUBLISH_REF:refs/heads/main"')
    assert publisher.index(committed) < publisher.index("if push_do;")
    guard = next(s["run"] for s in steps if s.get("name") == "guard — finalized site has no dead references")
    assert "scripts.check_aibrief_publication" in guard

@pytest.mark.parametrize("region,prefix", [("china", "cnx"), ("hk", "hkx")])
@pytest.mark.parametrize("duplicate_first", [True, False])
def test_brief_publication_refuses_duplicate_target_dialogs(tmp_path, region, prefix, duplicate_first):
    from scripts import check_aibrief_publication as pub

    _publication_fixture(tmp_path)
    page = tmp_path / ("site/" + region + ".html")
    correct = page.read_text()
    old = '<section id="' + prefix + '-dlg-aibrief">Old modal without the brief</section>'
    page.write_text(old + correct if duplicate_first else correct + old)
    with pytest.raises(pub.PublicationError, match="exactly one target"):
        pub.check(tmp_path, region)


# Early durable AI Brief cut: hermetic Git fixtures, never a live main push.
@pytest.fixture
def _brief_checkpoint_tree(tmp_path):
    import subprocess

    root = tmp_path / "source"
    root.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.test"], check=True)

    def payload(lens, asof="2026-10-16", generated="2026-10-18T06:50:00+00:00", degraded=None):
        return {
            "schema": "master_brief.v2", "lens": lens, "state_asof": asof,
            "generated_at": generated, "summary": "A grounded lens narrative",
            "degraded_reason": degraded,
        }

    for lens, name in (("macro", "master_brief.json"), ("china", "china_brief.json"), ("btc", "btc_brief.json")):
        raw = json.dumps(payload(lens)).encode()
        for rel in (f"data/regime/{name}", f"site/{name}"):
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
    (root / "site/aibrief.html").write_text("<!DOCTYPE html><html>Old daily brief</html>")
    for name in ("theme.css", "theme.js", "aibrief.js"):
        (root / "site" / name).write_text("unchanged shared asset")
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "accepted baseline"], check=True)
    head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    return root, head, payload


def _new_china_brief(root, payload, *, degraded=None, asof="2026-11-03",
                     generated="2026-11-04T03:00:00+00:00"):
    raw = json.dumps(payload("china", asof, generated, degraded)).encode()
    for rel in ("site/china_brief.json", "data/regime/china_brief.json"):
        (root / rel).write_bytes(raw)
    (root / "site/aibrief.html").write_text("<!DOCTYPE html><html>Fresh China brief</html>")


def test_early_checkpoint_manifest_is_narrow_and_durable(_brief_checkpoint_tree):
    import hashlib
    from scripts.ci.aibrief_checkpoint_manifest import generated_manifest

    root, base, payload = _brief_checkpoint_tree
    assert generated_manifest(root, base) == []
    _new_china_brief(root, payload)
    manifest = dict(generated_manifest(root, base))
    assert set(manifest) == {
        "site/china_brief.json", "data/regime/china_brief.json"
    }
    for rel, digest in manifest.items():
        assert hashlib.sha256((root / rel).read_bytes()).hexdigest() == digest
    assert "master_brief.json" not in " ".join(manifest)
    assert "btc_brief.json" not in " ".join(manifest)


@pytest.mark.parametrize("defect", [
    "missing_pair", "mismatched_pair", "degraded_provider", "regressed_date",
    "regressed_generation", "wrong_lens", "missing_timezone", "invalid_json",
    "symlink_pair",
])
def test_early_checkpoint_refuses_partial_or_stale_publication(
    _brief_checkpoint_tree, defect
):
    import os
    from scripts.ci.aibrief_checkpoint_manifest import CheckpointRefused, generated_manifest

    root, base, payload = _brief_checkpoint_tree
    _new_china_brief(root, payload)
    if defect == "missing_pair":
        (root / "data/regime/china_brief.json").unlink()
    elif defect == "mismatched_pair":
        (root / "site/china_brief.json").write_text("{}")
    elif defect == "degraded_provider":
        _new_china_brief(root, payload, degraded="provider_unavailable")
    elif defect == "regressed_date":
        _new_china_brief(root, payload, asof="2026-10-15")
    elif defect == "regressed_generation":
        _new_china_brief(root, payload, generated="2026-10-17T01:00:00Z")
    elif defect == "wrong_lens":
        raw = json.dumps(payload("macro", "2026-11-03", "2026-11-04T03:00:00Z")).encode()
        for rel in ("site/china_brief.json", "data/regime/china_brief.json"):
            (root / rel).write_bytes(raw)
    elif defect == "missing_timezone":
        _new_china_brief(root, payload, generated="2026-11-04T03:00:00")
    elif defect == "invalid_json":
        for rel in ("site/china_brief.json", "data/regime/china_brief.json"):
            (root / rel).write_text("not JSON")
    elif defect == "symlink_pair":
        target = root / "site/china_brief.json"
        target.unlink()
        target.symlink_to("../data/regime/china_brief.json")
    with pytest.raises(CheckpointRefused):
        generated_manifest(root, base)


def test_aibrief_early_checkpoint_workflow_precedes_long_dashboard():
    import yaml
    from pathlib import Path

    repo = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load((repo / ".github/workflows/daily.yml").read_text())
    steps = workflow["jobs"]["engine"]["steps"]
    by_id = {s.get("id"): (i, s) for i, s in enumerate(steps) if s.get("id")}
    brief_page_idx = next(i for i, s in enumerate(steps) if s.get("name") == "AI Daily Brief page (build_aibrief)")
    checkpoint_idx, early = by_id["aibrief_early_checkpoint"]
    assert by_id["master_brain"][0] < checkpoint_idx < brief_page_idx < by_id["regime_dashboard"][0]
    assert early["if"] == "steps.regime_inputs.outcome == 'success'"
    assert early["continue-on-error"] is True
    assert 0 < early["timeout-minutes"] <= 12
    assert early["run"] == "bash scripts/ci/daily_engine_aibrief_checkpoint.sh"

    shell = (repo / "scripts/ci/daily_engine_aibrief_checkpoint.sh").read_text()
    assert '. "$ROOT/scripts/ci/push_retry.sh"' in shell
    assert 'push_on_main_ok' in shell and 'push_do origin HEAD:main' in shell
    assert "scripts/ci/aibrief_checkpoint_manifest.py" in shell
    assert 'git diff --quiet "$SOURCE_HEAD" origin/main' in shell
    assert "worktree add -b" in shell
    assert "git add data/ site/" not in shell
    assert "git push --force" not in shell
    # The old broad publisher is unchanged and still runs late in the job.
    assert by_id["regime_dashboard"][0] < next(
        i for i, s in enumerate(steps)
        if s.get("name") == "commit engine outputs"
    )

    # The context consumer must see this run's deterministic liquidity outputs.
    def producer_step(module):
        command = f"python -m {module}"
        matches = [
            (i, step) for i, step in enumerate(steps)
            if command in str(step.get("run", ""))
        ]
        assert len(matches) == 1, f"{module} must have exactly one producer step"
        assert sum(str(step.get("run", "")).count(command) for step in steps) == 1
        return matches[0]

    netliq_idx, netliq = producer_step("scripts.build_netliq_daily")
    plumbing_idx, plumbing = producer_step("scripts.build_liquidity_plumbing")
    scorer_idx = next(
        i for i, step in enumerate(steps)
        if step.get("name") == "master brain scorer (durability loop; deterministic, resilient)"
    )
    core_checkpoint_idx = next(
        i for i, step in enumerate(steps)
        if step.get("name") == "checkpoint core engine outputs to main (durable before tail desks)"
    )
    assert (
        by_id["regime_inputs"][0] < netliq_idx < plumbing_idx < scorer_idx
        < by_id["master_brain"][0] < checkpoint_idx < brief_page_idx
        < by_id["regime_dashboard"][0] < core_checkpoint_idx
    )
    for step in (netliq, plumbing):
        assert step.get("if") == "steps.regime_inputs.outcome == 'success'"


@pytest.mark.parametrize("changed,expected_scope", [
    ("master_brief.json", "macro"),
    ("china_brief.json", "macro+china+hk"),
    ("btc_brief.json", "macro"),
    (None, None),
])
def test_brief_render_completion_adopts_all_lenses(
    _brief_checkpoint_tree, tmp_path, changed, expected_scope
):
    """Prove the real completion gate and scope picker against a Git history."""
    import os
    import subprocess
    from pathlib import Path
    import yaml

    root, baseline, _payload = _brief_checkpoint_tree
    def commit(message):
        subprocess.run(["git", "-C", str(root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "--allow-empty", "-qm", message], check=True)

    # A full render from the original baseline is the newest covering watermark.
    commit(f"render: site re-render 2026-10-18 (scope=all, from={baseline})")
    if changed:
        (root / "site" / changed).write_text(f"accepted new {changed}")
        commit("nightly: new accepted AI Brief input")
    flow = yaml.safe_load((Path(__file__).resolve().parents[1] / ".github/workflows/render.yml").read_text())
    gate = next(s["run"] for s in flow["jobs"]["brief_render_gate"]["steps"] if s.get("id") == "brief")
    picker = next(s["run"] for s in flow["jobs"]["render"]["steps"] if s.get("id") == "pick")
    env = {**os.environ, "GITHUB_OUTPUT": str(tmp_path / "render_gate_output")}
    subprocess.run(["bash", "-euo", "pipefail", "-c", gate], cwd=root, env=env, check=True)
    verdict = (tmp_path / "render_gate_output").read_text()
    assert ("needed=true" in verdict) == (changed is not None), verdict

    # workflow_run completion is the path used by GitHub-token nightly pushes.
    env["GITHUB_OUTPUT"] = str(tmp_path / "render_scope_output")
    picker = picker.replace("${{ github.event_name }}", "workflow_run")
    picker = picker.replace("${{ github.event.inputs.scope }}", "all")
    subprocess.run(["bash", "-c", picker], cwd=root, env=env, check=True)
    scoped = (tmp_path / "render_scope_output").read_text()
    if expected_scope:
        assert f"scope={expected_scope}" in scoped, scoped
    else:
        assert "skip=true" in scoped, scoped


def test_aibrief_checkpoint_unreadable_accepted_source_fails_closed(
    _brief_checkpoint_tree, monkeypatch
):
    from types import SimpleNamespace
    from scripts.ci import aibrief_checkpoint_manifest as chk

    root, base, payload = _brief_checkpoint_tree
    _new_china_brief(root, payload)
    monkeypatch.setattr(chk.subprocess, "run", lambda *a, **kw: SimpleNamespace(
        returncode=128, stdout=b"", stderr=b"missing object"
    ))
    with pytest.raises(chk.CheckpointRefused, match="unreadable accepted source"):
        chk.generated_manifest(root, base)


@pytest.mark.parametrize("lens,name", [
    ("macro", "master_brief.json"),
    ("china", "china_brief.json"),
    ("btc", "btc_brief.json"),
])
def test_standalone_ai_brief_cannot_advance_watermark_with_stale_lens(
    tmp_path, lens, name
):
    from scripts import check_aibrief_publication as pub

    _publication_fixture(tmp_path)
    assert pub.check(tmp_path, "macro") == ["macro"]
    assert pub.check(tmp_path, "macro+china+hk") == ["china", "hk", "macro"]
    rel = tmp_path / "site" / name
    newer = json.loads(rel.read_text())
    newer["summary"] = f"New {lens} analysis with changed source inputs"
    rel.write_text(json.dumps(newer))
    with pytest.raises(pub.PublicationError, match="site/aibrief.html"):
        pub.check(tmp_path, "macro")
    _publication_pages(tmp_path, json.loads((tmp_path / "site/china_brief.json").read_text()))
    assert pub.check(tmp_path, "macro+china+hk") == ["china", "hk", "macro"]


@pytest.mark.parametrize(
    "summary,tldr,regime_read,accepted",
    [
        (None, [], None, False),
        ("", [], "", False),
        (None, None, None, False),
        ("A verified narrative", [], None, True),
        (None, ["A verified top-line finding"], None, True),
        (None, [], "A verified regime observation", True),
    ],
)
def test_early_checkpoint_requires_nonempty_narrative_before_publication(
    _brief_checkpoint_tree, summary, tldr, regime_read, accepted,
):
    """A fresh healthy timestamp with an inert LLM reply cannot displace last-good."""
    from scripts.ci.aibrief_checkpoint_manifest import (
        CheckpointRefused, generated_manifest,
    )

    root, base, make_payload = _brief_checkpoint_tree
    brief = make_payload(
        "china", asof="2026-11-03",
        generated="2026-11-04T09:00:00+00:00", degraded=None,
    )
    brief.update(summary=summary, tldr=tldr, regime_read=regime_read)
    raw = json.dumps(brief).encode()
    for rel in ("data/regime/china_brief.json", "site/china_brief.json"):
        (root / rel).write_bytes(raw)

    if accepted:
        rows = dict(generated_manifest(root, base))
        assert set(rows) == {
            "data/regime/china_brief.json", "site/china_brief.json"
        }
    else:
        with pytest.raises(CheckpointRefused, match="no rendered narrative"):
            generated_manifest(root, base)

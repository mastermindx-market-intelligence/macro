"""A PASSING ``--selftest`` must publish no GitHub annotation.

MEASURED 2026-09-25, run 36099187934 (job 107957833159, the ``fence-pack`` job on
PR #7908). ``scripts/sync_chat_nav.py --selftest`` proves the chat-nav guard by
drifting a mkdtemp copy of templates/chat.html and requiring the guard to go red.
The guard duly printed

    ::error::templates/chat.html's header no longer matches _site_nav.html.j2 …

and the step then printed ``selftest PASS`` and exited 0. GitHub's annotation
collector scrapes ``::error::`` out of a step's stdout REGARDLESS of the step's
exit status, so that line landed as a red annotation on the PR — on every PR that
ran the fence pack, whether or not it touched a template. Its remedy text tells
the reader to hand-edit templates/chat.html, which is the exact practice that
guard exists to abolish, and the file it named was never in the diff. It cost one
session several diagnostic round-trips before the log order gave it away.

``scripts/check_template_site_sync.py --selftest`` had the same defect in the same
job: its ``wrongway.html`` fixture exists only under mkdtemp, and the refusal it
is built to provoke published ``::error title=template-site-sync wrong-direction
fix refused::`` from a green step.

Both now route findings through a ``report(level, title, message, *, annotate)``
helper and pass ``annotate=False`` from ``selftest()``. The text is unchanged and
still printed (prefixed ``selftest: fixture …``) — a selftest that proves only
"the function returned False" would be a weaker selftest, and the point is that
the guard says the right THING.

So every guard here is pinned in BOTH directions. Quiet is worthless if it was
bought by disarming the check, which is the one way a fix like this goes wrong:

  * the ``--selftest`` run emits no line-start workflow command, keeps its text,
    and still exits 0;
  * the REAL path still emits that workflow command, ``::`` prefix and all, when
    it meets real drift.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.check_template_site_sync import check as tss_check  # noqa: E402
from scripts.sync_chat_nav import check as nav_check  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

#: What GitHub's collector scrapes. A workflow command is only a command when it
#: STARTS the line (tests/test_audit_unrun_tests.py::
#: test_annotations_start_the_line_and_flush pins the same rule for the census),
#: so line-start is exactly the right test — and exactly what the fix withholds.
_ANNOTATION_PREFIX = "::"


def _workflow_commands(stdout: str) -> list[str]:
    return [line for line in stdout.splitlines() if line.startswith(_ANNOTATION_PREFIX)]


def _run_selftest(script: str) -> subprocess.CompletedProcess[str]:
    """The guard's own CI step, run the way CI runs it.

    A subprocess and not an in-process call to ``selftest()``: the defect was
    about the BYTES a CI step puts on stdout, which is the only thing the
    annotation collector ever sees.
    """
    return subprocess.run(
        [sys.executable, script, "--selftest"],
        cwd=ROOT, capture_output=True, text=True, timeout=300,
    )


# --------------------------------------------------------------- sync_chat_nav

#: The selftest renders the REAL templates/ and copies the real site/chat.html
#: into its fixture. CI always checks out the full tree; a sparse session worktree
#: (policy R8) omits site/, and there the guard cannot run at all.
_HAS_CHAT_PAIR = (ROOT / "templates" / "chat.html").is_file() and (
    ROOT / "site" / "chat.html").is_file()


@pytest.mark.skipif(not _HAS_CHAT_PAIR,
                    reason="sparse worktree: templates/chat.html + site/chat.html absent")
def test_chat_nav_selftest_publishes_no_annotation() -> None:
    r = _run_selftest("scripts/sync_chat_nav.py")
    assert r.returncode == 0, f"selftest failed:\n{r.stdout}\n{r.stderr}"
    assert "selftest PASS" in r.stdout, f"selftest did not run to completion:\n{r.stdout}"
    assert not _workflow_commands(r.stdout), (
        "the chat-nav selftest published a GitHub annotation from a PASSING run — it "
        f"will appear red on every PR that runs the fence pack: {_workflow_commands(r.stdout)}"
    )


@pytest.mark.skipif(not _HAS_CHAT_PAIR,
                    reason="sparse worktree: templates/chat.html + site/chat.html absent")
def test_chat_nav_selftest_still_prints_the_drift_TEXT() -> None:
    """Quiet, not silent: the words are what make the selftest worth running."""
    r = _run_selftest("scripts/sync_chat_nav.py")
    assert "selftest: fixture error [chat-nav-sync drift]" in r.stdout, (
        f"the selftest no longer reports the drift it deliberately created:\n{r.stdout}")
    assert "The header is GENERATED" in r.stdout, (
        f"the drift message lost its remedy text:\n{r.stdout}")


def test_chat_nav_real_drift_still_publishes_the_annotation(tmp_path: Path) -> None:
    """Positive control. A real hand-edit must still go red, with the ``::`` prefix."""
    if not _HAS_CHAT_PAIR:
        pytest.skip("sparse worktree: templates/chat.html + site/chat.html absent")
    shutil.copytree(ROOT / "templates", tmp_path / "templates")
    (tmp_path / "site").mkdir()
    shutil.copy2(ROOT / "site" / "chat.html", tmp_path / "site" / "chat.html")

    page = tmp_path / "templates" / "chat.html"
    text = page.read_text(encoding="utf-8")
    assert text.count('<div class="nav-links">') == 1
    page.write_text(
        text.replace('<div class="nav-links">',
                     '<div class="nav-links">\n    <a href="whitehouse.html">X</a>', 1),
        encoding="utf-8")

    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ok = nav_check(tmp_path)          # exactly what main() calls — no annotate kwarg
    assert ok is False, "the gate did not fire on a hand-added menu link"
    assert any(line.startswith("::error title=chat-nav-sync drift::")
               for line in buf.getvalue().splitlines()), (
        f"real drift no longer publishes its annotation:\n{buf.getvalue()}")


# ------------------------------------------------------- check_template_site_sync

def test_template_site_sync_selftest_publishes_no_annotation() -> None:
    r = _run_selftest("scripts/check_template_site_sync.py")
    assert r.returncode == 0, f"selftest failed:\n{r.stdout}\n{r.stderr}"
    assert "selftest PASS" in r.stdout, f"selftest did not run to completion:\n{r.stdout}"
    assert not _workflow_commands(r.stdout), (
        "the template↔site-sync selftest published a GitHub annotation from a PASSING "
        f"run, about a mkdtemp fixture: {_workflow_commands(r.stdout)}")


def test_template_site_sync_selftest_still_prints_the_refusal_TEXT() -> None:
    r = _run_selftest("scripts/check_template_site_sync.py")
    assert "selftest: fixture error [template-site-sync wrong-direction fix refused]" in r.stdout, (
        f"the selftest no longer reports the refusal it exists to provoke:\n{r.stdout}")


def test_template_site_sync_real_refusal_still_publishes_the_annotation(tmp_path: Path) -> None:
    """Positive control: the wrong-direction refusal is a real, blocking finding."""
    (tmp_path / "templates").mkdir()
    (tmp_path / "site").mkdir()
    # The 2026-07-26 chat.html shape: the SITE copy is the fresh one, and the
    # template's ?v= contradicts the asset on disk, so templates/ -> site/ would
    # ship bytes the edge pins for a year.
    (tmp_path / "site" / "app.js").write_text("var live = 1;\n")
    live = hashlib.sha256((tmp_path / "site" / "app.js").read_bytes()).hexdigest()[:8]
    (tmp_path / "templates" / "wrongway.html").write_text(
        '<script src="app.js?v=deadbeef" defer></script>\n')
    (tmp_path / "site" / "wrongway.html").write_text(
        f'<script src="app.js?v={live}" defer></script>\n<link href="extra.css">\n')

    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        diverged = tss_check(tmp_path, fix=True)   # what main() calls — no annotate kwarg
    assert diverged == ["wrongway.html"]
    assert getattr(tss_check, "refused", []) == ["wrongway.html"]
    assert any(
        line.startswith("::error title=template-site-sync wrong-direction fix refused::")
        for line in buf.getvalue().splitlines()), (
        f"a real wrong-direction refusal no longer publishes its annotation:\n{buf.getvalue()}")

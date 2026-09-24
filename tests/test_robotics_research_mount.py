"""tests/test_robotics_research_mount.py — R4a robotics vertical mount partial.

Hermetic tests for templates/_robotics_research_mount.html.j2, the Robotics
vertical partial of the basket-intelligence include seam. The partial mirrors
the T10b semiconductor partial (templates/_theme_research_mount.html.j2) in
every law EXCEPT the gate: it renders ONLY for
`theme_research_anchor == "robotics_automation"` — exact identity equality,
not the ^[a-z0-9_]+$ grammar check — so two verticals can never both mount on
one page.

Laws under test (mirroring L4–L7 of the semiconductor partial):
  L4 — anchor absent/empty/any-other-value → the partial emits nothing at all
       (zero bytes besides whitespace).
  L5 — mount shape pinned: stylesheet link, one <section> with the robotics
       identity attributes (anchor id, slices, two API paths, hidden,
       aria-labelledby) PLUS the seat-requested per-mount identity attributes
       `data-schema-id="robotics_theme_research.v1"` and `data-slice-labels`
       (a JSON object of {slice: [en, zh]}), bilingual title, verbatim note,
       deferred client script.
  L6 — every visible string flows through `t('en','zh')` (`.l-en`/`.l-zh`
       spans); no text node carries both scripts; no raw slug shown.
  L7 — no analytical data, payload, figure, token or URL beyond the two asset
       paths and the two API paths.

The aggregator include line that would pull this partial into
templates/_basket_intelligence_mounts.html.j2 is owned by the SHELL WRITER
per the #7669 ruling (issuecomment-5808986207) — this suite documents that it
is deliberately absent today, so the flip to one robotics mount is a
deliberate later change, not drift.
"""
from __future__ import annotations

import json
import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest

# Reuse the sibling seam suite's synthetic-root + env helpers — the env
# construction (FileSystemLoader + autoescape + jinja2.Undefined) stays in ONE
# place rather than being re-invented here.
try:  # the sibling suite lives on the shared foundation (#7870); this carrier
    # must stay collectable on main alone (RR9), so the import is guarded and the
    # three tests that need the shared seam/client are strict-xfailed until it lands.
    from tests.test_basket_intelligence_mounts import (
        _make_basket_root,
        _render_basket_detail,
    )
    HAS_SHARED = True
except ImportError:  # pragma: no cover — main without the T10b seam
    HAS_SHARED = False

    def _make_basket_root(*_a, **_k):  # type: ignore[misc]
        raise ImportError("tests.test_basket_intelligence_mounts is not on this base")

    def _render_basket_detail(*_a, **_k):  # type: ignore[misc]
        raise ImportError("tests.test_basket_intelligence_mounts is not on this base")

_SHARED_XFAIL = pytest.mark.xfail(
    condition=not HAS_SHARED,
    strict=True,
    reason="shared T10b seam, semiconductor partial and theme-research client (#7870) "
           "are not on this base; flips loudly the day they land",
)

REPO_ROOT = Path(__file__).parent.parent
R4A_BASE_COMMIT = "8e478b2feed0"          # lane base (#7870 head, T10 + T10b)
PARTIAL_NAME = "_robotics_research_mount.html.j2"
ANCHOR = "robotics_automation"

MOUNT_SIGNATURES = (
    # Signatures unique to the ROBOTICS mount. Deliberately NOT
    # `data-anchor-theme-id="robotics_automation"` — the semiconductor
    # partial echoes the anchor verbatim and (known shared defect, see
    # test_semiconductor_partial_also_renders_for_robotics_anchor_today)
    # mounts for it today, so that attribute is not robotics-identifying.
    'data-schema-id="robotics_theme_research.v1"',
    'data-slices="precision_motion,perception"',
    "Robotics industry research",
    "机器人产业研究",
)


def _render_partial(context: dict | None = None) -> str:
    """Render the robotics partial directly against templates/.

    Uses the SAME environment construction the sibling seam suite's
    `_render_basket_detail` builds (FileSystemLoader over the templates dir,
    autoescape=True, undefined=jinja2.Undefined) — no second, differently
    configured environment. `context=None` renders with the anchor ABSENT.
    """
    import jinja2

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(REPO_ROOT / "templates")),
        autoescape=True,
        undefined=jinja2.Undefined,
    )
    return env.get_template(PARTIAL_NAME).render(**(context or {}))


def _section_block(html: str) -> str:
    """Slice out ONLY the mount section (L7 checks must not see page bytes)."""
    m = re.search(
        r"(<section[^>]*data-theme-research-mount.*?</section>)", html, re.DOTALL
    )
    assert m, "could not isolate the robotics theme-research mount section"
    return m.group(1)


# ---------------------------------------------------------------------------
# 1 — L4: silent without anchor, and for any non-robotics anchor (identity)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "anchor",
    [
        None,                    # absent from the render context entirely
        "",                      # empty string
        "ai_semiconductors",     # the OTHER vertical's anchor — must not mount
        "robotics automation",   # invalid grammar (space) AND wrong identity
        "ROBOTICS_AUTOMATION",   # exact equality: case matters
        "robotics_automationx",  # near-miss identity
    ],
)
def test_silent_without_anchor_and_for_other_anchor(anchor):
    """Any anchor value other than exactly `robotics_automation` — including
    absent and empty — produces ZERO non-whitespace output: no mount, no asset
    tags, no section, no title."""
    ctx = {} if anchor is None else {"theme_research_anchor": anchor}
    html = _render_partial(ctx)
    assert re.sub(r"\s+", "", html) == "", (
        f"partial must be fully silent for anchor={anchor!r}; got: {html!r}"
    )
    assert "data-theme-research-mount" not in html
    assert "theme-research.js" not in html
    assert "theme-research.css" not in html


# ---------------------------------------------------------------------------
# 2 — L5: mounted for the robotics anchor, exact shape
# ---------------------------------------------------------------------------

def test_mounted_for_robotics_anchor():
    """anchor == "robotics_automation" renders exactly one mount with the
    pinned shape: identity attributes, hidden, both asset tags exactly once,
    both API paths, and the two extra identity attributes with parseable
    slice-label JSON."""
    html = _render_partial({"theme_research_anchor": ANCHOR})

    # Exactly one mount
    assert html.count("data-theme-research-mount") == 1
    # Anchor identity + slice list
    assert f'data-anchor-theme-id="{ANCHOR}"' in html
    assert 'data-slices="precision_motion,perception"' in html
    # Hidden until an entitled client response reveals it
    assert re.search(
        r"<section[^>]*data-theme-research-mount[^>]*\bhidden\b", html
    ), "mount section must carry the hidden attribute"
    # Both asset tags present, exactly once each
    assert html.count('rel="stylesheet" href="../assets/css/theme-research.css"') == 1
    assert (
        html.count(
            '<script defer src="../assets/js/theme-research.js?v=20260924a"></script>'
        ) == 1
    )
    # Both API paths
    assert 'data-api-query="/api/themes/v1/research/query"' in html
    assert 'data-api-evidence="/api/themes/v1/research/evidence"' in html

    # The two seat-requested per-mount identity attributes, labels JSON parses
    assert 'data-schema-id="robotics_theme_research.v1"' in html
    m = re.search(r"data-slice-labels='([^']+)'", html)
    assert m, "data-slice-labels attribute missing from the section"
    labels = json.loads(m.group(1))
    assert labels == {
        "precision_motion": ["Precision Motion", "精密运动"],
        "perception": ["Perception", "感知"],
    }, f"unexpected slice-labels payload: {labels}"

    # Bilingual title
    assert "Robotics industry research" in html
    assert "机器人产业研究" in html


# ---------------------------------------------------------------------------
# 3 — L7: no payload, no JSON, no figures, no internal markers
# ---------------------------------------------------------------------------

def test_no_payload_or_json_in_partial():
    """The mounted partial carries no application/json, no generation string,
    no internal markers, and no digits-only figure anywhere — the only digit
    run outside the section is the asset version query `?v=20260924a`
    (`v1` inside `robotics_theme_research.v1` and the API paths is
    alphanumeric, never a standalone figure)."""
    html = _render_partial({"theme_research_anchor": ANCHOR})

    assert "application/json" not in html
    assert "generation" not in html
    assert "gmirca_" not in html
    assert "curation" not in html

    section = _section_block(html)
    assert not re.search(r"\b\d+(?:\.\d+)?\b", section), (
        "the mount section must carry no digits-only figure at rest"
    )

    outside = html.replace(section, "")
    digit_runs = re.findall(r"\d+", outside)
    assert digit_runs == ["20260924"], (
        f"outside the section the only digits must be the asset version "
        f"query; got {digit_runs}"
    )

    # The two API paths AND the two asset hrefs are the ONLY URLs in the
    # partial (mirrors the sibling seam suite's pin), and no http(s):// at all.
    allowed = {
        "../assets/css/theme-research.css",
        "../assets/js/theme-research.js?v=20260924a",
        "/api/themes/v1/research/query",
        "/api/themes/v1/research/evidence",
    }
    urls = re.findall(r'(?:href|src)="([^"]+)"|/api/[^"\s]+', html)
    offending = [u for u in urls if u and u not in allowed]
    assert not offending, f"unexpected URL(s) in the partial: {offending}"
    assert not re.search(r"https?://", html), (
        "the partial must not embed any http(s):// URL — display-tier only"
    )


def test_no_raw_slug_as_visible_text():
    """Internal slugs and schema ids live only in data attributes; the visible
    text of the mount never shows them (bilingual toggle rule: labels, never
    scorer/slice slugs)."""
    html = _render_partial({"theme_research_anchor": ANCHOR})
    section = _section_block(html)
    visible = re.sub(r"<[^>]+>", " ", section)
    for slug in ("precision_motion", "perception", "robotics_automation",
                 "robotics_theme_research", "theme_research"):
        assert slug not in visible, f"raw slug {slug!r} rendered as visible text"


# ---------------------------------------------------------------------------
# 4 — L6: bilingual strings toggle, never dual
# ---------------------------------------------------------------------------

class _TextNodeAudit(HTMLParser):
    """Collect non-whitespace text nodes with the class list of every open
    ancestor element, so each node can be checked for .l-en/.l-zh custody."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._stack: list[list[str]] = []
        self.text_nodes: list[tuple[str, list[str]]] = []

    def handle_starttag(self, tag, attrs):
        classes = (dict(attrs).get("class") or "").split()
        self._stack.append(classes)

    def handle_endtag(self, tag):
        if self._stack:
            self._stack.pop()

    def handle_data(self, data):
        if data.strip():
            classes = [c for entry in self._stack for c in entry]
            self.text_nodes.append((data, classes))


_LATIN = re.compile(r"[A-Za-z]")
_CJK = re.compile("[一-鿿]")


def test_bilingual_strings_toggle_not_dual():
    """Every visible text node inside the section sits inside an `.l-en` or
    `.l-zh` span, and no text node mixes Latin and CJK — the languages toggle,
    they are never rendered together in one node."""
    html = _render_partial({"theme_research_anchor": ANCHOR})
    section = _section_block(html)

    audit = _TextNodeAudit()
    audit.feed(section)
    assert audit.text_nodes, "no text nodes found inside the mount section"

    for text, classes in audit.text_nodes:
        assert "l-en" in classes or "l-zh" in classes, (
            f"text node {text!r} is not inside an .l-en/.l-zh span "
            f"(ancestor classes: {classes})"
        )
        has_latin = bool(_LATIN.search(text))
        has_cjk = bool(_CJK.search(text))
        assert not (has_latin and has_cjk), (
            f"text node {text!r} carries both Latin and CJK — languages must "
            f"toggle, never render together"
        )


# ---------------------------------------------------------------------------
# 5 — the aggregator line is the shell writer's; zero robotics mounts TODAY
# ---------------------------------------------------------------------------

@_SHARED_XFAIL
def test_aggregator_untouched_and_would_include_us(tmp_path):
    """Two facts, both deliberate:

    (a) The three shell-owned templates are byte-identical to the lane base —
        this lane did not touch the aggregator, the semiconductor partial or
        the basket shell.
    (b) Rendering basket_detail.html.j2 through the REAL aggregator with
        anchor=robotics_automation yields ZERO robotics mounts TODAY: per the
        #7669 ruling (issuecomment-5808986207) the aggregator include line for
        this partial is owned by the SHELL WRITER and is serialized, so it is
        deliberately absent here. The robotics partial IS placed in the
        synthetic root, so the ONLY thing standing between it and the page is
        that missing include line — the day the shell writer adds it, this
        count flips 0 → 1 and this assertion is the deliberate later change.
    """
    # (a) shell-owned templates untouched vs the lane base commit
    result = subprocess.run(
        ["git", "diff", "--numstat", R4A_BASE_COMMIT, "--",
         "templates/_basket_intelligence_mounts.html.j2",
         "templates/_theme_research_mount.html.j2",
         "templates/basket_detail.html.j2"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"git diff failed:\nSTDOUT={result.stdout}\nSTDERR={result.stderr}"
    )
    assert result.stdout.strip() == "", (
        f"shell-owned templates changed vs {R4A_BASE_COMMIT}: "
        f"{result.stdout!r}"
    )

    # (b) zero robotics mounts through the real aggregator today. NOTE: the
    # semiconductor partial DOES (defect) mount for this anchor — the
    # signatures below are robotics-identifying and disjoint from its output.
    root = _make_basket_root(tmp_path, extra_partials=(PARTIAL_NAME,))
    html = _render_basket_detail(root, context={"theme_research_anchor": ANCHOR})
    for signature in MOUNT_SIGNATURES:
        assert signature not in html, (
            f"basket_detail must carry ZERO robotics mounts today (aggregator "
            f"line pending the shell writer per #7669); found {signature!r}"
        )


# ---------------------------------------------------------------------------
# 6 — KNOWN SHARED DEFECT: semiconductor partial gates on grammar, not identity
# ---------------------------------------------------------------------------

@_SHARED_XFAIL
def test_semiconductor_partial_also_renders_for_robotics_anchor_today():
    """KNOWN SHARED DEFECT — documented, NOT fixed here (the semiconductor
    partial is not this lane's file).

    templates/_theme_research_mount.html.j2 gates only on the ^[a-z0-9_]+$
    grammar, so `theme_research_anchor="robotics_automation"` (valid grammar,
    foreign vertical) still mounts the SEMICONDUCTOR section today. The first
    assert pins that current behaviour. The DESIRED behaviour (it must NOT
    mount for a foreign vertical) is expressed right after and xfails today;
    the day the shared owner adds identity gating, the FIRST assert fails
    loudly, un-xfailing this pair and telling its owner to delete it.
    """
    import jinja2

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(REPO_ROOT / "templates")),
        autoescape=True,
        undefined=jinja2.Undefined,
    )
    html = env.get_template("_theme_research_mount.html.j2").render(
        theme_research_anchor=ANCHOR
    )

    # CURRENT behaviour — the defect, asserted so it cannot drift silently.
    assert "data-theme-research-mount" in html, (
        "CURRENT behaviour changed: the semiconductor partial no longer mounts "
        "for a foreign vertical anchor — the identity gate has landed. Remove "
        "this documented-defect pair and flip the desired assertion."
    )

    # DESIRED behaviour — xfail today. pytest 9's pytest.xfail() helper takes
    # no `strict` kwarg (verified via inspect), so strict-flip semantics are
    # carried structurally by the CURRENT assert above failing first on fix
    # day, which turns this test from xfail to a loud failure.
    try:
        assert "data-theme-research-mount" not in html, (
            "DESIRED: the semiconductor partial must not mount for "
            "anchor=robotics_automation"
        )
    except AssertionError:
        pytest.xfail(
            reason="shared partial gates on grammar, not identity; "
                   "request posted on #7870"
        )


# ---------------------------------------------------------------------------
# 7 — the two extra identity attributes are inert to the current client
# ---------------------------------------------------------------------------

@_SHARED_XFAIL
def test_client_reads_only_declared_mount_attributes():
    """site/assets/js/theme-research.js reads exactly the four declared mount
    attributes off the MOUNT element (anchor id, slices, the two API paths)
    and nothing else — so this partial's `data-schema-id` and
    `data-slice-labels` are inert today, carried for the seat's future client
    revision only."""
    js = (REPO_ROOT / "site" / "assets" / "js" / "theme-research.js").read_text(
        encoding="utf-8"
    )
    mount_reads = set(
        re.findall(r"MOUNT\.getAttribute\(\s*['\"]([^'\"]+)['\"]\s*\)", js)
    )
    # The four declared mount attributes are all read from MOUNT
    assert {
        "data-anchor-theme-id",
        "data-slices",
        "data-api-query",
        "data-api-evidence",
    } <= mount_reads, f"client mount reads shrank: {sorted(mount_reads)}"
    # The client never reads MOUNT.dataset
    assert not re.search(r"MOUNT\.dataset", js)
    # The two extra identity attributes are never read — inert today
    assert "data-schema-id" not in mount_reads
    assert "data-slice-labels" not in mount_reads
    assert "data-schema-id" not in js
    assert "data-slice-labels" not in js

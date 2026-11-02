"""Tests for scripts/build_product_page_registry.py.

Two halves:

  * a SCHEMA suite that runs against the committed
    ``data/product_experience/page_registry.json`` — this is the CI drift guard,
    and it is the only part that touches a real artifact;
  * DERIVATION units built on tmp_path fixtures with an injected ``run_git``
    callable, so no test reads a sister repo, calls git, calls gh, or touches
    the network.  Everything here is TZ-agnostic (CI runs UTC).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from scripts import build_product_page_registry as reg

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY = REPO_ROOT / "data" / "product_experience" / "page_registry.json"
OVERRIDES = REPO_ROOT / "config" / "product_experience" / "page_registry_overrides.yml"


# ---------------------------------------------------------------------------
# committed artifact — schema invariants (the CI drift guard)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def committed() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def test_committed_registry_passes_schema_invariants(committed):
    problems = reg.validate(committed)
    assert problems == [], "\n".join(problems)


def test_committed_registry_covers_all_three_repos(committed):
    counts: dict[str, int] = {}
    for row in committed["pages"]:
        counts[row["repo"]] = counts.get(row["repo"], 0) + 1
    # Floors, not exact counts: the census grows with the product.
    assert counts.get("macro", 0) >= 60, counts
    assert counts.get("terminal", 0) >= 13, counts
    assert counts.get("mastermind", 0) >= 7, counts


_IMMUTABLE_SHA_RE = re.compile(r"[0-9a-f]{40}")


def _terminal_source_problems(terminal: dict) -> list[str]:
    """Provenance ``sources.terminal`` may record — exactly what the builder's
    ``--terminal-ref`` accepts: the mutable default (``origin/master``) or an
    explicit immutable commit.  An immutable ref qualifies only when it IS the
    resolved sha; a ref naming any other object than the one the rows were
    derived from is false provenance, and so is every weaker ref shape."""
    ref, sha = terminal.get("ref"), terminal.get("sha")
    if not isinstance(sha, str) or not _IMMUTABLE_SHA_RE.fullmatch(sha):
        return [f"terminal sha {sha!r} is not a resolved 40-hex commit"]
    if ref == "origin/master":
        return []
    if isinstance(ref, str) and _IMMUTABLE_SHA_RE.fullmatch(ref):
        if ref == sha:
            return []
        return [f"terminal ref {ref!r} does not match the resolved sha"]
    return [f"terminal ref {ref!r} is neither origin/master nor the resolved sha"]


def test_committed_registry_records_a_terminal_sha(committed):
    terminal = committed["sources"]["terminal"]
    assert terminal["available"] is True
    assert _terminal_source_problems(terminal) == []


def test_terminal_source_helper_rejects_an_immutable_ref_off_the_resolved_sha():
    """A 40-hex ref is only qualified when it names the same commit as the
    recorded sha — a pinned ref plus a sha from another object is exactly the
    false provenance this guard exists for."""
    problems = _terminal_source_problems({"ref": "b" * 40, "sha": "c" * 40})
    assert problems and "does not match" in problems[0]


def test_terminal_source_helper_rejects_weak_refs_and_takes_supported_forms():
    weak = [{"ref": "HEAD", "sha": "a" * 40},
            {"ref": "claude/a-branch", "sha": "a" * 40},
            {"ref": "A" * 40, "sha": "a" * 40},
            {"ref": "", "sha": "a" * 40},
            {"ref": "a" * 40, "sha": "tooshort"}]
    assert all(_terminal_source_problems(case) for case in weak)
    assert _terminal_source_problems({"ref": "origin/master", "sha": "a" * 40}) == []
    assert _terminal_source_problems({"ref": "a" * 40, "sha": "a" * 40}) == []


def test_committed_page_ids_are_unique(committed):
    ids = [row["page_id"] for row in committed["pages"]]
    assert len(ids) == len(set(ids))


def test_committed_rows_never_use_null_for_unknown(committed):
    for row in committed["pages"]:
        for field, value in row.items():
            assert value is not None, f"{row['page_id']}.{field} is null"


def test_every_committed_row_cites_evidence(committed):
    missing = [row["page_id"] for row in committed["pages"]
               if not row["source_evidence"]]
    assert missing == []


def test_committed_overrides_all_resolve(committed):
    known = {row["page_id"] for row in committed["pages"]}
    stale = sorted(set(reg.load_overrides(OVERRIDES)) - known)
    assert stale == [], f"stale overrides: {stale}"


def test_committed_overrides_only_set_overridable_fields():
    for page_id, entry in reg.load_overrides(OVERRIDES).items():
        for key in entry:
            assert key in reg.OVERRIDABLE or key in reg.OVERRIDE_META, \
                f"{page_id}: {key} is derived-only"


# ---------------------------------------------------------------------------
# fake macro repo
# ---------------------------------------------------------------------------

SITE_ACCESS = """
schema: site_access.v1
public:
  exact:
    - /
    - /index.html
    - /alpha.html
    - /delta.html
  prefixes:
    - /stocks/
free_registered:
  exact:
    - /beta.html
  prefixes: []
deny:
  exact:
    - /status.html
  prefixes: []
premium:
  default_tier: essential
  enforced_early:
    exact: []
    prefixes:
      - /premiumdata/
"""

NAVLINKS = """
<div class="nav-links">
  <a class="nav-brand" href="{{ NP }}start.html">Home</a>
  <div class="nav-dd">
    <a class="nav-link" href="{{ NP }}alpha.html">{{ t('United States', '美国') }}</a>
    <div class="nav-dd-menu">
      <a class="nav-mega-item" href="{{ NP }}beta.html">Beta</a>
    </div>
  </div>
  <div class="nav-dd">
    <a class="nav-link" href="{{ NP }}gamma.html">{{ t('Research', '研究') }}</a>
  </div>
</div>
"""

PUBLIC_NAV = """
<nav><a href="{{ rel }}index.html">Home</a><a href="{{ rel }}alpha.html">Alpha</a></nav>
"""

# Mirrors the real footer's shape: a brand tagline that is NOT a column heading,
# per-column bare `<p>` headings (one translated, one plain), a link the navs
# also carry, and a bottom strip that repeats links under no heading at all.
PUBLIC_FOOTER = """
<footer class="public-footer">
  <div class="f-brand">
    <p class="ft">{{ t('A tagline, not a column heading.', '一句标语。') }}</p>
  </div>
  <div class="f-cols">
    <div class="f-col">
      <p>{{ t('Platform', '平台') }}</p>
      <a href="{{ rel }}alpha.html">Alpha</a>
      <a href="{{ rel }}delta.html">Delta</a>
    </div>
    <div class="f-col">
      <p>Legal</p>
      <a href="{{ rel }}products/handmade.html">Handmade</a>
    </div>
  </div>
  <div class="f-bot">
    <span>© 2026</span>
    <span class="f-legal"><a href="{{ rel }}products/handmade.html">Handmade</a>
      · <a href="{{ rel }}delta.html">Delta</a></span>
  </div>
</footer>
"""

BUILDER = '''
from lib.pages import write_page

def main(site):
    tmpl = env.get_template("alpha.html.j2")
    write_page(site / "alpha.html", tmpl.render())
    write_page(site / "beta.html", env.get_template("beta.html.j2").render())
    write_page(site / "delta.html", env.get_template("delta.html.j2").render())
    out = site / "stocks"
    for t in tickers:
        write_page(out / f"{t}.html", ticker_tmpl.render())
'''

PAGES_PY = '''
HAND_AUTHORED_PAGES = frozenset({
    "products/handmade.html",
})
'''

SEO_PY = '''
_EXCLUDE_PREFIXES = frozenset({"_mockup"})
_EXCLUDE_NAMES = frozenset({"status", "alpha_lab"})
'''

TRACKED = [
    "site/index.html",
    "site/alpha.html",
    "site/alpha_lab.html",
    "site/beta.html",
    "site/gamma.html",
    "site/delta.html",
    "site/status.html",
    "site/products/index.html",
    "site/products/handmade.html",
    "site/stocks/index.html",
    "site/stocks/AAPL.html",
    "site/stocks/MSFT.html",
]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture()
def macro_repo(tmp_path: Path) -> Path:
    root = tmp_path / "macro"
    _write(root / "config" / "site_access.yml", SITE_ACCESS)
    _write(root / "templates" / "_navlinks.html.j2", NAVLINKS)
    _write(root / "templates" / "_public_nav.html.j2", PUBLIC_NAV)
    _write(root / "templates" / "_public_footer.html.j2", PUBLIC_FOOTER)
    _write(root / "templates" / "alpha.html.j2",
           "<html data-theme='light'>{{ t('Hi', '你好') }}</html>")
    _write(root / "templates" / "beta.html.j2", "<html>plain</html>")
    _write(root / "templates" / "delta.html.j2",
           "<html data-theme='light'>fetch('/premiumdata/delta.json')</html>")
    _write(root / "templates" / "index.html", "<html>{{ t('Home', '首页') }}</html>")
    _write(root / "templates" / "gamma.html", "<html>plain copy</html>")
    _write(root / "scripts" / "build_demo.py", BUILDER)
    _write(root / "lib" / "pages.py", PAGES_PY)
    _write(root / "lib" / "seo.py", SEO_PY)
    return root


def fake_git(tracked: list[str] | None = None, sha: str = "a" * 40):
    listing = "\n".join(TRACKED if tracked is None else tracked) + "\n"

    def _git(root: Path, args: list[str]):
        if args[:2] == ["ls-files", "site/*.html"]:
            return listing
        if args[0] == "rev-parse":
            return sha + "\n"
        if args[0] == "status":
            return ""
        return None
    return _git


def rows_by_id(rows: list[dict]) -> dict[str, dict]:
    return {row["page_id"]: row for row in rows}


# ---------------------------------------------------------------------------
# macro derivation
# ---------------------------------------------------------------------------

def test_macro_derives_routes_builders_and_templates(macro_repo):
    rows, source = reg.derive_macro(macro_repo, git=fake_git())
    index = rows_by_id(rows)
    alpha = index["macro:alpha"]
    assert alpha["route"] == "/alpha.html"
    assert alpha["route_kind"] == "page"
    assert alpha["builder"] == ["scripts/build_demo.py"]
    assert alpha["source_template"] == "templates/alpha.html.j2"
    assert alpha["generated"] is True
    assert "scripts/build_demo.py:6" in alpha["source_evidence"]
    assert source["available"] is True
    assert source["tracked_html_pages"] == len(TRACKED)


def test_macro_nav_family_comes_from_the_nav_templates(macro_repo):
    index = rows_by_id(reg.derive_macro(macro_repo, git=fake_git())[0])
    assert index["macro:alpha"]["nav_family"] == "product_nav.united_states"
    assert index["macro:beta"]["nav_family"] == "product_nav.united_states"
    assert index["macro:gamma"]["nav_family"] == "product_nav.research"
    # index.html is only in the public nav
    assert index["macro:index"]["nav_family"] == "public_nav.public"
    # A page no nav and no footer names is an ORPHAN and says so — it is not
    # "unknown".
    assert index["macro:alpha_lab"]["nav_family"] == "none"


def test_macro_footer_rescues_a_page_the_navs_do_not_link(macro_repo):
    """The public footer is a link inventory too, so a page only IT names is
    not an orphan — and it carries the footer COLUMN that names it."""
    index = rows_by_id(reg.derive_macro(macro_repo, git=fake_git())[0])
    assert index["macro:delta"]["nav_family"] == "footer.platform"
    # a column heading with no t() helper reads just as well
    assert index["macro:products_handmade"]["nav_family"] == "footer.legal"


def test_macro_nav_outranks_the_footer_for_the_same_route(macro_repo):
    """alpha.html sits in both navs AND in the footer: the footer is the
    lowest-precedence source, so it never overwrites a nav family."""
    index = rows_by_id(reg.derive_macro(macro_repo, git=fake_git())[0])
    alpha = index["macro:alpha"]
    assert alpha["nav_family"] == "product_nav.united_states"
    assert "templates/_public_footer.html.j2" not in alpha["source_evidence"]


def test_macro_footer_sourced_row_cites_the_footer_template(macro_repo):
    """The family and the file it came from move together."""
    evidence = rows_by_id(reg.derive_macro(macro_repo, git=fake_git())[0])[
        "macro:delta"]["source_evidence"]
    assert "templates/_public_footer.html.j2" in evidence
    assert "templates/_navlinks.html.j2" not in evidence
    assert "templates/_public_nav.html.j2" not in evidence


def test_footer_bottom_strip_never_moves_a_route_to_another_column():
    """The `f-bot` strip repeats links under no heading; FIRST occurrence wins,
    so a repeated route keeps the column that named it rather than the column
    that happens to be open when the strip is reached."""
    footer = reg.parse_footer(PUBLIC_FOOTER, group_prefix="footer")
    assert footer["/products/handmade.html"] == "footer.legal"
    assert footer["/delta.html"] == "footer.platform"


def test_footer_reads_only_a_bare_paragraph_as_a_column_heading():
    """`<p class="ft">` is the brand tagline, not a heading — letting it open a
    group would file the first column under a marketing sentence."""
    footer = reg.parse_footer(PUBLIC_FOOTER, group_prefix="footer")
    assert set(footer.values()) == {"footer.platform", "footer.legal"}
    # a link that precedes every heading still lands somewhere honest
    assert reg.parse_footer('<a href="x.html">X</a>', group_prefix="footer") == \
        {"/x.html": "footer.brand"}


def test_macro_lifecycle_from_lab_suffix_and_deny_bucket(macro_repo):
    index = rows_by_id(reg.derive_macro(macro_repo, git=fake_git())[0])
    assert index["macro:alpha_lab"]["lifecycle"] == "lab"
    status = index["macro:status"]
    assert status["lifecycle"] == "internal"
    assert status["payload_tier"] == "internal"
    assert status["access_shell"] == "unknown"
    assert any("deny" in note for note in status["notes"])


def test_macro_payload_tier_splits_public_from_gated(macro_repo):
    index = rows_by_id(reg.derive_macro(macro_repo, git=fake_git())[0])
    assert index["macro:alpha"]["payload_tier"] == "public"
    # free_registered: the shell is anonymous, the payload is not public
    assert index["macro:beta"]["payload_tier"] == "public_shell_premium_payload"
    assert "site_access.v1:free_registered" in index["macro:beta"]["known_contracts"]
    assert index["macro:alpha"]["access_shell"] == "anonymous"


def test_macro_public_shell_over_a_premium_payload_is_its_own_tier(macro_repo):
    """A public page whose template fetches a premium-enforced payload is NOT
    simply "public" — the split between shell and payload is the product."""
    index = rows_by_id(reg.derive_macro(macro_repo, git=fake_git())[0])
    assert index["macro:delta"]["payload_tier"] == "public_shell_premium_payload"


def test_macro_unknown_stays_the_literal_unknown(macro_repo):
    """A page no builder claims keeps "unknown" — never a guess, never null."""
    index = rows_by_id(reg.derive_macro(macro_repo, git=fake_git())[0])
    lab = index["macro:alpha_lab"]
    assert lab["source_template"] == "unknown"
    assert lab["builder"] == []
    assert lab["generated"] == "unknown"
    assert lab["bilingual"] == "unknown"
    assert lab["themes"] == "unknown"
    assert all(value is not None for value in lab.values())


def test_macro_plain_copy_pair_is_not_reported_as_generated(macro_repo):
    gamma = rows_by_id(reg.derive_macro(macro_repo, git=fake_git())[0])["macro:gamma"]
    assert gamma["generated"] is False
    assert gamma["source_template"] == "templates/gamma.html"


def test_macro_hand_authored_page_gets_its_own_row(macro_repo):
    index = rows_by_id(reg.derive_macro(macro_repo, git=fake_git())[0])
    hand = index["macro:products_handmade"]
    assert hand["generated"] is False
    assert hand["source_template"] == "site/products/handmade.html"
    assert "macro:products_index" in index  # family hubs keep their own row


def test_macro_collapses_a_directory_into_one_family_row(macro_repo):
    index = rows_by_id(reg.derive_macro(macro_repo, git=fake_git())[0])
    family = index["macro:stocks_family"]
    assert family["route_kind"] == "family"
    assert family["route"] == "/stocks/<t>.html"
    assert family["builder"] == ["scripts/build_demo.py"]
    assert any("2 committed pages" in note for note in family["notes"])
    # the members themselves do NOT get rows; the hub does
    assert "macro:stocks_aapl" not in index
    assert "macro:stocks_index" in index


def test_macro_chrome_facts_read_the_template_not_a_blanket_rule(macro_repo):
    index = rows_by_id(reg.derive_macro(macro_repo, git=fake_git())[0])
    assert index["macro:alpha"]["bilingual"] is True
    assert index["macro:alpha"]["themes"] == ["light", "dark"]
    assert index["macro:alpha"]["locales"] == ["en", "zh"]
    # beta.html.j2 has neither the translation helper nor a theme attribute
    assert index["macro:beta"]["bilingual"] is False
    assert index["macro:beta"]["themes"] == "unknown"


def test_macro_survives_a_repo_with_no_git(macro_repo):
    rows, source = reg.derive_macro(macro_repo, git=lambda root, args: None)
    assert source["sha"] == "unknown"
    assert source["page_inventory"] == "write_page() call sites only"
    # the builder's own write sites still produce rows
    assert "macro:alpha" in rows_by_id(rows)


# ---------------------------------------------------------------------------
# path-expression resolution
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("expr,names,expected", [
    ("site / 'x.html'", {}, ("/x.html", False)),
    ("site_root / 'x.html'", {}, ("/x.html", False)),
    ("config.ROOT / 'site' / 'x.html'", {}, ("/x.html", False)),
    ("Path(a.root).resolve() if a.root else _REPO / 'site' / 'x.html'", {},
     ("/x.html", False)),
    ("Path(config.load()['storage']['site_dir']) / 'sectors' / f'{fund}.html'", {},
     ("/sectors/<fund>.html", True)),
    ("out / f'{ticker}.html'", {"out": "site / 'stocks'"},
     ("/stocks/<ticker>.html", True)),
    ("site / f'strategy_{spec.key}.html'", {}, ("/strategy_<key>.html", True)),
    ("site / _PAGE", {"_PAGE": "'named.html'"}, ("/named.html", False)),
    ("out_dir / (bid + '.html')", {"out_dir": "site / out_name"},
     ("/<out_name>/<bid>.html", True)),
])
def test_resolve_path_expr(expr, names, expected):
    assert reg._resolve_path_expr(expr, names) == expected


def test_resolve_path_expr_refuses_an_unanchored_expression():
    assert reg._resolve_path_expr("destination", {}) is None
    assert reg._resolve_path_expr("tmp_dir / 'x.html'", {}) is None


def test_family_pattern_refuses_a_pattern_that_matches_everything():
    """`/<name>.html` names no page in particular, so it attributes none."""
    assert reg._family_pattern("/<name>.html") is None
    assert reg._family_pattern("/alpha.html") is None
    pattern = reg._family_pattern("/fund_<slug>.html")
    assert pattern is not None
    assert pattern.match("/fund_berkshire.html")
    assert not pattern.match("/alpha.html")
    assert not pattern.match("/stocks/fund_x.html")


# ---------------------------------------------------------------------------
# terminal / mastermind derivation (injected git, no sister repo)
# ---------------------------------------------------------------------------

TERMINAL_TREE = "\n".join([
    "terminal/app/page.tsx",
    "terminal/app/layout.tsx",
    "terminal/app/(shell)/discover/page.tsx",
    "terminal/app/(shell)/options/page.tsx",
    "terminal/app/(shell)/admin/page.tsx",
    "terminal/app/dev/theater/page.tsx",
    "terminal/app/x/[slug]/page.tsx",
])

TERMINAL_FILES = {
    "terminal/components/AppNav.tsx":
        'export const TOP = [\n  { k: "discover", label: "Discover", href: "/discover" },\n];\n',
    "terminal/app/layout.tsx": '<html lang="en" data-theme="dark">',
    "terminal/lib/i18n.tsx": 'export type Lang = "en" | "zh";',
    "terminal/app/(shell)/discover/page.tsx": 'import SignupGate from "x";',
    "terminal/app/(shell)/options/page.tsx": 'import { hasLiveOptions } from "y";',
    "terminal/app/(shell)/admin/page.tsx": 'import { isAdminRequest } from "z";',
    "terminal/app/page.tsx": "export default function Landing() {}",
    "terminal/app/dev/theater/page.tsx": "export default function Theater() {}",
    "terminal/app/x/[slug]/page.tsx": "export default function Slug() {}",
}


def fake_terminal_git(root: Path, args: list[str]):
    if args[0] == "ls-tree":
        return TERMINAL_TREE + "\n"
    if args[0] == "rev-parse":
        return "b" * 40 + "\n"
    if args[0] == "show":
        return TERMINAL_FILES.get(args[1].split(":", 1)[1])
    return None


def test_terminal_routes_strip_route_groups_and_mark_families(tmp_path):
    root = tmp_path / "charting-app"
    root.mkdir()
    rows, source = reg.derive_terminal(root, "origin/master", git=fake_terminal_git)
    index = rows_by_id(rows)
    assert source["sha"] == "b" * 40
    assert index["terminal:landing"]["route"] == "/"
    assert index["terminal:discover"]["route"] == "/discover"   # (shell) dropped
    assert index["terminal:x_slug"]["route"] == "/x/<slug>"
    assert index["terminal:x_slug"]["route_kind"] == "family"


def test_terminal_gate_markers_drive_access_shell(tmp_path):
    root = tmp_path / "charting-app"
    root.mkdir()
    index = rows_by_id(reg.derive_terminal(root, "origin/master",
                                           git=fake_terminal_git)[0])
    assert index["terminal:discover"]["access_shell"] == "signed_in"
    assert index["terminal:options"]["access_shell"] == "paid"
    assert index["terminal:options"]["payload_tier"] == "premium"
    assert index["terminal:admin"]["access_shell"] == "admin"
    # No marker is NOT proof of anonymity — the overrides file carries that fact.
    assert index["terminal:landing"]["access_shell"] == "unknown"


def test_terminal_theme_locale_and_dev_lifecycle(tmp_path):
    root = tmp_path / "charting-app"
    root.mkdir()
    index = rows_by_id(reg.derive_terminal(root, "origin/master",
                                           git=fake_terminal_git)[0])
    assert index["terminal:discover"]["themes"] == ["dark"]
    assert index["terminal:discover"]["locales"] == ["en", "zh"]
    assert index["terminal:discover"]["bilingual"] is True
    assert index["terminal:discover"]["nav_family"] == "app_nav.rail"
    assert index["terminal:dev_theater"]["lifecycle"] == "dev_only"


def test_missing_sister_repo_is_recorded_not_fatal(tmp_path):
    rows, source = reg.derive_terminal(tmp_path / "absent", "origin/master",
                                       git=fake_terminal_git)
    assert rows == []
    assert source["available"] is False
    assert "reason" in source

    rows, source = reg.derive_mastermind(tmp_path / "absent",
                                         git=lambda root, args: None)
    assert rows == []
    assert source["available"] is False


MASTERMIND_WEB = '''
from fastapi import APIRouter
router = APIRouter()

@router.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(_STATIC / "index.html", media_type="text/html")

@router.get("/portfolio_desk", include_in_schema=False)
def portfolio_desk_page():
    return FileResponse(_STATIC / "portfolio_desk.html", media_type="text/html")

@router.get("/theme.css", include_in_schema=False)
def theme_css():
    return FileResponse(_STATIC / "theme.css", media_type="text/css")

@router.get("/api/performance")
def performance():
    return {"ok": True}
'''


def test_mastermind_html_routes_only(tmp_path):
    root = tmp_path / "Mastermind"
    _write(root / "app" / "web.py", MASTERMIND_WEB)
    rows, source = reg.derive_mastermind(
        root, git=lambda r, a: "master\n" if a[1:2] == ["--abbrev-ref"] else "c" * 40)
    index = rows_by_id(rows)
    assert sorted(index) == ["mastermind:index", "mastermind:portfolio_desk"]
    assert index["mastermind:portfolio_desk"]["route"] == "/portfolio_desk"
    assert index["mastermind:portfolio_desk"]["access_shell"] == "anonymous"
    assert index["mastermind:portfolio_desk"]["payload_tier"] == "public"
    assert index["mastermind:index"]["source_template"] == "app/static/index.html"
    assert source["html_routes"] == 2


# ---------------------------------------------------------------------------
# overrides
# ---------------------------------------------------------------------------

def test_overrides_merge_onto_the_derived_row():
    rows = [reg.blank_row("macro:alpha", "macro", "/alpha.html")]
    errors = reg.apply_overrides(rows, {
        "macro:alpha": {
            "priority": "P0",
            # DS-PR-1 re-key: `ranked_decision_board` became `discovery_board`
            # when the archetype vocabulary closed (reg.ARCHETYPES).
            "archetype": "discovery_board",
            "primary_user_question": "Which names are set up?",
            "evidence": ["docs/x.md"],
            "note": "seeded by hand",
        },
    }, source_name="test.yml")
    assert errors == []
    assert rows[0]["priority"] == "P0"
    assert rows[0]["archetype"] == "discovery_board"
    assert "docs/x.md" in rows[0]["source_evidence"]
    assert "seeded by hand" in rows[0]["notes"]


def test_override_on_an_unknown_page_id_is_a_hard_error():
    rows = [reg.blank_row("macro:alpha", "macro", "/alpha.html")]
    errors = reg.apply_overrides(rows, {"macro:ghost": {"priority": "P0"}},
                                 source_name="test.yml")
    assert len(errors) == 1
    assert "macro:ghost" in errors[0]


def test_override_cannot_set_a_derived_field():
    rows = [reg.blank_row("macro:alpha", "macro", "/alpha.html")]
    errors = reg.apply_overrides(rows, {"macro:alpha": {"builder": ["nope.py"]}},
                                 source_name="test.yml")
    assert len(errors) == 1
    assert "builder" in errors[0]
    assert rows[0]["builder"] == []


# ---------------------------------------------------------------------------
# whole-build behaviour
# ---------------------------------------------------------------------------

def _build(macro_repo: Path, tmp_path: Path) -> dict:
    doc, errors = reg.build_registry(
        repo_root=macro_repo,
        terminal_root=tmp_path / "absent-terminal",
        terminal_ref="origin/master",
        mastermind_root=tmp_path / "absent-mastermind",
        site_dir=None,
        as_of="2026-08-11T00:00:00Z",
        overrides_path=tmp_path / "no-overrides.yml",
        git=fake_git(),
    )
    assert errors == []
    return doc


def test_build_is_deterministic_under_a_pinned_as_of(macro_repo, tmp_path):
    first = json.dumps(_build(macro_repo, tmp_path), indent=2, sort_keys=False)
    second = json.dumps(_build(macro_repo, tmp_path), indent=2, sort_keys=False)
    assert first == second
    assert json.loads(first)["generated_at"] == "2026-08-11T00:00:00Z"


def test_build_sorts_rows_by_repo_then_route(macro_repo, tmp_path):
    pages = _build(macro_repo, tmp_path)["pages"]
    keys = [(row["repo"], row["route"], row["page_id"]) for row in pages]
    assert keys == sorted(keys)


def test_build_output_validates(macro_repo, tmp_path):
    assert reg.validate(_build(macro_repo, tmp_path)) == []


def test_validate_catches_a_missing_field_and_a_null(macro_repo, tmp_path):
    doc = _build(macro_repo, tmp_path)
    doc["pages"][0].pop("owner")
    doc["pages"][1]["nav_family"] = None
    problems = reg.validate(doc)
    assert any("missing fields" in p for p in problems)
    assert any("null" in p for p in problems)


def test_validate_catches_a_duplicate_page_id(macro_repo, tmp_path):
    doc = _build(macro_repo, tmp_path)
    doc["pages"].append(dict(doc["pages"][0]))
    assert any("duplicate page_id" in p for p in reg.validate(doc))


def test_annotation_starts_the_line(capsys):
    """GitHub drops any annotation that does not start the line (house law)."""
    reg.annotate("boom")
    out = capsys.readouterr().out.splitlines()
    assert out and out[0].startswith("::error title=page-registry::")


def test_gmi_source_classification_does_not_grant_a_new_shell_audience():
    """Actual source overrides must close the real exporter, not just describe a hold."""
    import copy
    from scripts.export_shared_shell_routes import derive_projection

    routes = {
        "macro:gmi": "/gmi.html",
        "macro:gmi_index": "/gmi-index.html",
        "macro:gmi_coverage": "/gmi-coverage.html",
        "macro:gmi_issuer_mu": "/gmi-issuer-mu.html",
        "macro:gmi_relationships": "/gmi-relationships.html",
        "macro:gmi_states": "/gmi-states.html",
        "macro:expectation_surface": "/expectation_surface.html",
        "macro:consumer_cyclical_plnt": "/consumer_cyclical_plnt.html",
    }
    rows = []
    for page_id, route in routes.items():
        row = reg.blank_row(page_id, "macro", route)
        # The published HTML shell policy is independent of downstream purpose.
        row.update(lifecycle="live", access_shell="anonymous",
                   payload_tier="public_shell_premium_payload")
        row["known_contracts"] = ["site_access.v1:default_insider"]
        rows.append(row)
    original = copy.deepcopy(rows)
    overlay = reg.load_overrides(OVERRIDES)
    assert reg.apply_overrides(rows, {key: overlay[key] for key in routes},
                               source_name=str(OVERRIDES)) == []
    held = {"macro:gmi_issuer_mu", "macro:gmi_relationships",
            "macro:expectation_surface"}
    for before, after in zip(original, rows):
        assert "site_access.v1:default_insider" in after["known_contracts"]
        if after["page_id"] in held:
            assert all(after[key] == before[key]
                       for key in ("lifecycle", "access_shell", "payload_tier"))
            assert "shared_shell:admission_withheld" in after["known_contracts"]
    index = rows_by_id(rows)
    assert index["macro:gmi_states"]["lifecycle"] == "internal"
    assert index["macro:consumer_cyclical_plnt"]["lifecycle"] == "parked"
    pin = "a" * 40
    doc = {"schema": reg.SCHEMA, "generated_at": "2026-11-02T00:00:00Z",
           "sources": {"macro": {"sha": pin}, "terminal": {"sha": "b" * 40},
                       "mastermind": {"sha": "c" * 40}}, "pages": rows}
    # PLNT is a diagnostic builder write, not committed HTML. Keep it out of
    # the tracked inventory; its parked row must also reject a stale copy.
    tracked = [path for key, path in routes.items()
               if key != "macro:consumer_cyclical_plnt"]
    def project(candidate, paths):
        return derive_projection(candidate, paths, {"exact": [], "prefixes": []},
                                 {}, registry_digest="fixture", inventory_ref=pin,
                                 document_paths=set(paths))
    result = project(doc, tracked)
    assert result["legacyPaths"] == ["/gmi-coverage.html", "/gmi-index.html", "/gmi.html"]
    reasons = {entry["path"]: entry["reason"]
               for entry in result["coverage"]["excluded"]}
    assert reasons == {
        "/expectation_surface.html": "consumer_admission_withheld",
        "/gmi-issuer-mu.html": "consumer_admission_withheld",
        "/gmi-relationships.html": "consumer_admission_withheld",
        "/gmi-states.html": "lifecycle_internal",
    }
    assert {entry["href"] for entry in result["directory"]} == set(result["legacyPaths"])
    stale = project(doc, tracked + [routes["macro:consumer_cyclical_plnt"]])
    assert {entry["path"]: entry["reason"] for entry in stale["coverage"]["excluded"]}[
        "/consumer_cyclical_plnt.html"] == "lifecycle_parked"
    # A hypothetical exact-surface qualification must not qualify a sibling.
    # Removing this marker in a fixture is not a real purpose grant.
    qualified = copy.deepcopy(doc)
    for row in qualified["pages"]:
        if row["page_id"] == "macro:gmi_relationships":
            row["known_contracts"].remove("shared_shell:admission_withheld")
    admitted = project(qualified, tracked)
    assert set(admitted["legacyPaths"]) - set(result["legacyPaths"]) == {
        "/gmi-relationships.html"}
    assert "/gmi-issuer-mu.html" not in admitted["legacyPaths"]


# Source-shaped render-table attribution fixtures; builders are parsed, never run.
def _gmi_write_fixture(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# fixtures — a source-shaped builder with the GMI symbols renamed
# ---------------------------------------------------------------------------

# Shaped line-for-line like scripts/build_gmi_explorer.py's render path: a
# module-literal route table, a literal issuer pair, a table loop whose body
# writes `site / page`, then the pair unpack and the issuer family loop.
GADGET_BUILDER = '''
from lib.pages import write_page

GADGET_TABLE = {
    "gadget.html": ("gadget_map.html.j2", "map"),
    "gadget-index.html": ("gadget_index.html.j2", "index"),
    "gadget-relationships.html": ("gadget_relationships.html.j2", "relationships"),
    "gadget-coverage.html": ("gadget_coverage.html.j2", "coverage"),
    "gadget-states.html": ("gadget_states.html.j2", "states"),
}
ISSUER_TABLE = ("gadget_issuer.html.j2", "issuer")


def render_site(model, site_dir):
    site = Path(site_dir)
    env = make_env(model)
    written = []
    for page, (template, page_key) in GADGET_TABLE.items():
        write_page(site / page, env.get_template(template).render(
            model=model, nav_prefix="", page_key=page_key))
        written.append(site / page)
    template, page_key = ISSUER_TABLE
    for issuer in model["issuers"]:
        page = f"gadget-issuer-{issuer['ticker'].lower()}.html"
        write_page(site / page, env.get_template(template).render(
            model=model, nav_prefix="", page_key=page_key, issuer=issuer))
        written.append(site / page)
    return written
'''

GADGET_BASE = """<html data-theme="light" data-lang>{{ t('Body', '正文') }}</html>"""

GADGET_MAP = """{% extends "_gadget_base.html.j2" %}
<p>{{ t('Map', '地图') }}</p>
"""

GADGET_PLAIN = "<p>no helper, no theme</p>\n"

GMI_FIXTURE_ACCESS = """
schema: site_access.v1
public:
  exact:
    - /
    - /index.html
  prefixes: []
free_registered:
  exact: []
  prefixes: []
deny:
  exact: []
  prefixes: []
premium:
  default_tier: essential
  enforced_early:
    exact: []
    prefixes: []
"""

GMI_FIXTURE_TRACKED = [
    "site/index.html",
    "site/gadget.html",
    "site/gadget-index.html",
    "site/gadget-relationships.html",
    "site/gadget-coverage.html",
    "site/gadget-states.html",
    "site/gadget-issuer-mu.html",
]


def _gmi_fake_git(tracked: list[str], sha: str = "a" * 40):
    listing = "\n".join(tracked) + "\n"

    def _git(root: Path, args: list[str]):
        if args[:2] == ["ls-files", "site/*.html"]:
            return listing
        if args[0] == "rev-parse":
            return sha + "\n"
        return None
    return _git


def _gmi_rows_by_id(rows: list[dict]) -> dict[str, dict]:
    return {row["page_id"]: row for row in rows}


@pytest.fixture()
def gmi_gadget_repo(tmp_path: Path) -> Path:
    root = tmp_path / "macro"
    _gmi_write_fixture(root / "scripts" / "build_gadget_explorer.py", GADGET_BUILDER)
    _gmi_write_fixture(root / "config" / "site_access.yml", GMI_FIXTURE_ACCESS)
    _gmi_write_fixture(root / "templates" / "_gadget_base.html.j2", GADGET_BASE)
    _gmi_write_fixture(root / "templates" / "gadget_map.html.j2", GADGET_MAP)
    for name in ("gadget_index.html.j2", "gadget_relationships.html.j2",
                 "gadget_coverage.html.j2", "gadget_issuer.html.j2"):
        _gmi_write_fixture(root / "templates" / name, GADGET_MAP)  # themed via the chain
    _gmi_write_fixture(root / "templates" / "gadget_states.html.j2", GADGET_PLAIN)
    _gmi_write_fixture(root / "lib" / "pages.py", "HAND_AUTHORED_PAGES = frozenset()\n")
    _gmi_write_fixture(root / "lib" / "seo.py",
           '_EXCLUDE_PREFIXES = frozenset()\n_EXCLUDE_NAMES = frozenset()\n')
    _gmi_write_fixture(root / "templates" / "_navlinks.html.j2", "")
    _gmi_write_fixture(root / "templates" / "_public_nav.html.j2", "")
    _gmi_write_fixture(root / "templates" / "_public_footer.html.j2", "")
    return root


# ---------------------------------------------------------------------------
# the five concrete table bindings plus the tracked issuer family
# ---------------------------------------------------------------------------

EXPECTED_GADGET_SITES = {
    ("/gadget.html", False, "gadget_map.html.j2"),
    ("/gadget-index.html", False, "gadget_index.html.j2"),
    ("/gadget-relationships.html", False, "gadget_relationships.html.j2"),
    ("/gadget-coverage.html", False, "gadget_coverage.html.j2"),
    ("/gadget-states.html", False, "gadget_states.html.j2"),
    ("/gadget-issuer-<lower>.html", True, "gadget_issuer.html.j2"),
}


def test_gmi_five_table_pages_and_issuer_family_resolve_concretely(gmi_gadget_repo):
    sites, unresolved = reg.scan_write_sites(gmi_gadget_repo / "scripts")
    got = {(s.route, s.is_family, s.template)
           for s in sites if s.builder == "scripts/build_gadget_explorer.py"}
    assert got == EXPECTED_GADGET_SITES
    # nothing the builder writes is left as a coverage gap
    assert unresolved == []


def test_gmi_table_pages_derive_with_builder_and_template(gmi_gadget_repo):
    index = _gmi_rows_by_id(reg.derive_macro(gmi_gadget_repo, git=_gmi_fake_git(GMI_FIXTURE_TRACKED))[0])
    expected_templates = {
        "macro:gadget": "templates/gadget_map.html.j2",
        "macro:gadget_index": "templates/gadget_index.html.j2",
        "macro:gadget_relationships": "templates/gadget_relationships.html.j2",
        "macro:gadget_coverage": "templates/gadget_coverage.html.j2",
        "macro:gadget_states": "templates/gadget_states.html.j2",
    }
    for page_id, template in expected_templates.items():
        row = index[page_id]
        assert row["builder"] == ["scripts/build_gadget_explorer.py"], page_id
        assert row["source_template"] == template, page_id
        assert row["generated"] is True, page_id
        assert any("build_gadget_explorer.py:" in ev
                   for ev in row["source_evidence"]), page_id


def test_gmi_tracked_issuer_page_attributed_through_the_family_write(gmi_gadget_repo):
    """site/gadget-issuer-mu.html is committed; the family write names its
    template, and the row says the attribution came through the family."""
    index = _gmi_rows_by_id(reg.derive_macro(gmi_gadget_repo, git=_gmi_fake_git(GMI_FIXTURE_TRACKED))[0])
    row = index["macro:gadget_issuer_mu"]
    assert row["builder"] == ["scripts/build_gadget_explorer.py"]
    assert row["source_template"] == "templates/gadget_issuer.html.j2"
    assert any("attributed through the builder's family write" in note
               for note in row["notes"])


def test_gmi_no_false_issuer_attribution_on_the_table_pages(gmi_gadget_repo):
    """The module-wide assign map binds `page` to the ISSUER f-string; before
    the fix every table write misresolved onto that family route.  Each table
    route must carry exactly its own concrete site, and no table page may be
    attributed as (or through) the issuer family."""
    sites, _ = reg.scan_write_sites(gmi_gadget_repo / "scripts")
    mine = [s for s in sites if s.builder == "scripts/build_gadget_explorer.py"]
    by_route: dict[str, list] = {}
    for site in mine:
        by_route.setdefault(site.route, []).append(site)
    for route in ("/gadget.html", "/gadget-index.html",
                  "/gadget-relationships.html", "/gadget-coverage.html",
                  "/gadget-states.html"):
        assert len(by_route[route]) == 1, route
        assert by_route[route][0].is_family is False, route
        assert by_route[route][0].template is not None, route
    family_routes = [s.route for s in mine if s.is_family]
    assert family_routes == ["/gadget-issuer-<lower>.html"]
    index = _gmi_rows_by_id(reg.derive_macro(gmi_gadget_repo, git=_gmi_fake_git(GMI_FIXTURE_TRACKED))[0])
    assert index["macro:gadget"]["builder"] == ["scripts/build_gadget_explorer.py"]


def test_gmi_bilingual_and_themes_derive_through_the_template_chain(gmi_gadget_repo):
    """gadget_map.html.j2 itself carries no chrome; the chain to
    _gadget_base.html.j2 (t() helper + data attrs) is what makes it bilingual
    and themed."""
    index = _gmi_rows_by_id(reg.derive_macro(gmi_gadget_repo, git=_gmi_fake_git(GMI_FIXTURE_TRACKED))[0])
    assert index["macro:gadget"]["bilingual"] is True
    assert index["macro:gadget"]["themes"] == ["light", "dark"]
    assert index["macro:gadget"]["locales"] == ["en", "zh"]
    # a page whose template has neither the helper nor a theme attribute
    assert index["macro:gadget_states"]["bilingual"] is False
    assert index["macro:gadget_states"]["themes"] == "unknown"


# ---------------------------------------------------------------------------
# refusals — dynamic, reassigned, mutated, unrelated, off-root
# ---------------------------------------------------------------------------

DYNAMIC_TEMPLATE_BUILDER = '''
from lib.pages import write_page

LOOSE_TABLE = {
    "loose.html": (TEMPLATE_NAME, "loose"),
}
TEMPLATE_NAME = pick_template()


def render_site(model, site_dir):
    site = Path(site_dir)
    for page, (template, page_key) in LOOSE_TABLE.items():
        write_page(site / page, env.get_template(template).render())
'''

REASSIGNED_TABLE_BUILDER = '''
from lib.pages import write_page

FLIP_TABLE = {"flip.html": ("flip.html.j2", "flip")}


def render_site(model, site_dir):
    site = Path(site_dir)
    FLIP_TABLE = {"other.html": ("other.html.j2", "other")}
    for page, (template, page_key) in FLIP_TABLE.items():
        write_page(site / page, env.get_template(template).render())
'''

MUTATED_TABLE_BUILDER = '''
from lib.pages import write_page

MUT_TABLE = {"mut.html": ("mut.html.j2", "mut")}


def render_site(model, site_dir):
    site = Path(site_dir)
    MUT_TABLE.update({"extra.html": ("extra.html.j2", "extra")})
    for page, (template, page_key) in MUT_TABLE.items():
        write_page(site / page, env.get_template(template).render())
'''

UNRELATED_DICT_BUILDER = '''
from lib.pages import write_page

LABELS = {"title.html": "A title", "body.html": "A body"}


def render_site(model, site_dir):
    site = Path(site_dir)
    write_page(site / "plain.html", env.get_template("plain.html.j2").render())
'''

TRAVERSAL_BUILDER = '''
from lib.pages import write_page

BAD_TABLE = {
    "sub/escape.html": ("escape.html.j2", "escape"),
    "climb.html": ("../evil.html.j2", "climb"),
    "format.html": ("{name}.html.j2", "format"),
    "good.html": ("good.html.j2", "good"),
}
OUT_DIR = tmp / "elsewhere"


def render_site(model, site_dir):
    site = Path(site_dir)
    for page, (template, page_key) in BAD_TABLE.items():
        write_page(OUT_DIR / page, env.get_template(template).render())
'''


def _gmi_builder_fixture(root: Path, name: str, source: str) -> None:
    _gmi_write_fixture(root / "scripts" / name, source)


def test_gmi_dynamic_template_value_mints_nothing(tmp_path):
    root = tmp_path / "macro"
    _gmi_builder_fixture(root, "build_loose.py", DYNAMIC_TEMPLATE_BUILDER)
    sites, _ = reg.scan_write_sites(root / "scripts")
    assert [s for s in sites if s.builder == "scripts/build_loose.py"] == []


def test_gmi_reassigned_table_is_refused(tmp_path):
    """A table that is a different mapping in another scope is ambiguous; the
    census refuses it rather than guessing which mapping the loop saw."""
    root = tmp_path / "macro"
    _gmi_builder_fixture(root, "build_flip.py", REASSIGNED_TABLE_BUILDER)
    sites, _ = reg.scan_write_sites(root / "scripts")
    assert [s for s in sites if s.builder == "scripts/build_flip.py"] == []


def test_gmi_mutated_table_is_refused(tmp_path):
    root = tmp_path / "macro"
    _gmi_builder_fixture(root, "build_mut.py", MUTATED_TABLE_BUILDER)
    sites, _ = reg.scan_write_sites(root / "scripts")
    assert [s for s in sites if s.builder == "scripts/build_mut.py"] == []


def test_gmi_unrelated_dict_constant_mints_no_pages(tmp_path):
    """A dict of strings that is not a render table produces no route, no row
    and no builder attribution."""
    root = tmp_path / "macro"
    _gmi_builder_fixture(root, "build_labels.py", UNRELATED_DICT_BUILDER)
    sites, _ = reg.scan_write_sites(root / "scripts")
    mine = [s for s in sites if s.builder == "scripts/build_labels.py"]
    assert [(s.route, s.template) for s in mine] == [("/plain.html", "plain.html.j2")]


def test_gmi_traversal_off_root_and_format_entries_are_refused(tmp_path):
    """A table entry with a directory part, a climbing template or a brace
    placeholder is not a concrete page; and a loop that does not write under
    the site root attributes nothing even when its table is literal."""
    root = tmp_path / "macro"
    _gmi_builder_fixture(root, "build_bad.py", TRAVERSAL_BUILDER)
    sites, unresolved = reg.scan_write_sites(root / "scripts")
    mine = [s for s in sites if s.builder == "scripts/build_bad.py"]
    assert mine == []
    # the write went somewhere that is not the site root: reported, not guessed
    assert any("OUT_DIR / page" in expr for _f, expr in unresolved)


def test_gmi_wrong_root_write_is_reported_unresolved_not_attributed(tmp_path):
    root = tmp_path / "macro"
    _gmi_builder_fixture(root, "build_bad.py", TRAVERSAL_BUILDER)
    rows, _source = reg.derive_macro(root, git=_gmi_fake_git(
        ["site/index.html", "site/good.html"]))
    index = _gmi_rows_by_id(rows)
    assert "macro:good" in index
    # none of the refused entries became a row
    assert "macro:sub_escape" not in index
    assert "macro:climb" not in index
    assert "macro:format" not in index
    assert "macro:escape" not in index


def test_gmi_table_loop_write_to_a_non_page_shape_stays_unresolved(tmp_path):
    """`site / f'{page}.html'` in a table loop is not the shape the binding
    vouches for: the module-wide map must not get it either."""
    root = tmp_path / "macro"
    _gmi_builder_fixture(root, "build_odd.py", '''
from lib.pages import write_page

ODD_TABLE = {"odd.html": ("odd.html.j2", "odd")}


def render_site(model, site_dir):
    site = Path(site_dir)
    for page, (template, page_key) in ODD_TABLE.items():
        write_page(site / (page + ".tmp"), env.get_template(template).render())
''')
    sites, unresolved = reg.scan_write_sites(root / "scripts")
    assert [s for s in sites if s.builder == "scripts/build_odd.py"] == []
    assert any("page + '.tmp'" in expr.replace('"', "'")
               for _f, expr in unresolved)


# ---------------------------------------------------------------------------
# the real GMI builder — integration against this repo's own scripts
# ---------------------------------------------------------------------------

REAL_GMI_BUILDER = REPO_ROOT / "scripts" / "build_gmi_explorer.py"


def test_gmi_real_gmi_builder_binds_all_six_surfaces():
    sites, _unresolved = reg.scan_write_sites(REPO_ROOT / "scripts")
    mine = [s for s in sites if s.builder == "scripts/build_gmi_explorer.py"]
    got = {(s.route, s.is_family, s.template) for s in mine}
    assert got == {
        ("/gmi.html", False, "gmi_map.html.j2"),
        ("/gmi-index.html", False, "gmi_index.html.j2"),
        ("/gmi-relationships.html", False, "gmi_relationships.html.j2"),
        ("/gmi-coverage.html", False, "gmi_coverage.html.j2"),
        ("/gmi-states.html", False, "gmi_states.html.j2"),
        ("/gmi-issuer-<lower>.html", True, "gmi_issuer.html.j2"),
    }


@pytest.mark.parametrize("mutation,table,root,iteration,body", [
    ("alias = TABLE\nalias['safe.html'] = ('wrong.html.j2', 'x')", None, None, None, ""),
    ("del TABLE['safe.html']", None, None, None, ""),
    ("", '{"safe.html": ("safe.html.j2", "safe"), **unknown}', None, None, ""),
    ("", '{"safe.html": ("/absolute.html.j2", "safe")}', None, None, ""),
    ("", '{"safe.html": ("safe.html.j2", "safe"), "bad.html": (unknown, "x")}', None, None, ""),
    ("", None, "pretend_site_dir", None, ""),
    ("", None, None, "TABLE.items(**options)", ""),
    ("", None, None, None, '        page = "other.html"\n'),
    ("", None, None, None, '        template = "other.html.j2"\n'),
    ("", "read_dynamic_table()", None, None, ""),
])
def test_gmi_uncertain_render_table_cannot_inherit_another_loop_binding(
        tmp_path, mutation, table, root, iteration, body):
    table = table or '{"safe.html": ("safe.html.j2", "safe")}'
    root = root or "site"
    iteration = iteration or "TABLE.items()"
    source = f'''TABLE = {table}
{mutation}
def render():
    for page, (template, key) in {iteration}:
{body}        write_page({root} / page, env.get_template(template).render())
    page = "unrelated.html"
'''
    _gmi_builder_fixture(tmp_path, "build_unsafe.py", source)
    sites, unresolved = reg.scan_write_sites(tmp_path / "scripts")
    assert sites == []
    assert unresolved, "An uncertain lexical binding must remain a reported gap"

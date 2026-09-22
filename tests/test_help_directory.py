"""Public /help directory integration and truth-boundary guards."""
from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

import pytest
import yaml
from jinja2 import Environment, FileSystemLoader

from lib.help_directory import (
    HELP_LINKS,
    HELP_ANSWERS,
    _CATEGORIES_BY_ID,
    _check_banned_vocabulary,
    _is_approved_href,
    help_directory_view_model,
    help_answers_view_model,
    product_changelog,
    support_routing_view_model,
)
from scripts import build_public_pages


ROOT = Path(__file__).resolve().parents[1]


def test_public_builder_renders_help_directory(tmp_path: Path) -> None:
    build_public_pages.build(tmp_path)

    html = (tmp_path / "help.html").read_text(encoding="utf-8")
    assert 'data-directory-state="complete"' in html
    assert '<nav class="public-nav"' in html
    assert '<footer class="public-footer">' in html
    assert 'id="help-search"' in html
    assert 'role="status"' in html
    assert 'data-empty-state="empty"' in html
    assert 'data-unknown-state="unknown"' not in html
    assert '>complete<' not in html
    assert '>empty · 0<' not in html
    assert '>unknown<' not in html
    assert "Available" in html
    assert "可用" in html
    assert 'data-changelog-state="published"' in html
    assert "docs/site_semantics" not in html


def test_build_site_renders_help_page_with_the_full_view_model(tmp_path: Path) -> None:
    """The nightly full-site render must render help.html too, not just the
    fast-path public builder (review finding B-F13-3 BLOCKER-1).

    scripts.build_site.build_help_page used to call only
    ``help_directory_view_model`` and splat entries/categories/directory_state
    at the template — but templates/help.html.j2 also dereferences
    ``answers``, ``answers_state``, ``changelog.state`` and iterates
    ``support_plans``, so this exact call shape raised
    ``UndefinedError: 'changelog' is undefined``, silently swallowed by
    build_site's own except-and-log wrapper (no site/help.html written, no
    test failure — ``git diff --stat origin/main -- scripts/build_site.py``
    was empty because nothing there had ever been touched or exercised).
    This test drives scripts.build_site.build_help_page directly — the real
    nightly call shape, not build_public_pages' fast path — and would have
    failed red before lib.help_directory.help_page_view_model became the one
    builder both call sites share.
    """
    import scripts.build_site as bs
    from datetime import datetime, timezone
    from lib import config

    env = Environment(loader=FileSystemLoader(config.ROOT / "templates"), autoescape=True)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    bs.build_help_page(env, tmp_path, generated)

    html = (tmp_path / "help.html").read_text(encoding="utf-8")
    assert 'data-directory-state="complete"' in html
    assert 'data-changelog-state="published"' in html
    assert HELP_ANSWERS[0].question_en in html


def test_help_directory_renders_only_the_frozen_owner_targets(tmp_path: Path) -> None:
    build_public_pages.build(tmp_path)
    html = (tmp_path / "help.html").read_text(encoding="utf-8")

    hrefs = set(re.findall(r'<a\b[^>]*class="help-card"[^>]*href="([^"]+)"', html))
    assert hrefs == {
        "reference.html",
        "methodology.html",
        "measurement.html",
        "glossary.html",
        "support.html",
        "plans.html",
        "plans.html?billing=portal",
        "https://app.mastermind-x.com/terminal?signin=1",
    }
    for label_en, label_zh in (
        ("Market Reference", "市场参考"),
        ("Methodology", "方法论"),
        ("Cycle Intelligence · Calibration Lab", "周期情报 · 校准实验室"),
        ("Support", "支持"),
        ("Plans &amp; pricing", "方案与定价"),
        ("Billing &amp; payments", "账单与付款"),
        ("Account &amp; sign-in", "账户与登录"),
    ):
        assert label_en in html
        assert label_zh in html


def test_help_route_is_registered_as_public_and_extensionless() -> None:
    policy = yaml.safe_load((ROOT / "config" / "site_access.yml").read_text())
    caddy = (ROOT / "app" / "deploy" / "Caddyfile").read_text()

    assert "/help.html" in policy["public"]["exact"]
    assert "redir /help /help.html 301" in caddy
    assert caddy.count("/help.html") >= 5


def test_help_uses_strict_bilingual_markup_and_accessible_filters() -> None:
    template = (ROOT / "templates" / "help.html.j2").read_text()

    assert "macro t(en, zh)" in template
    assert "zh if zh else en" not in template
    assert 'aria-label="{{ t_text(\'Search\', \'搜索\') }}"' in template
    assert 'aria-pressed="true"' in template
    assert 'aria-live="polite"' in template
    assert '@media (max-width:600px)' in template
    assert 'html[data-theme="light"]' in template
    assert "style.textContent" not in template
    assert 'class="sr-only"' not in template


def test_mixed_unknown_entry_renders_beside_complete_owner_without_a_link() -> None:
    unknown = replace(
        HELP_LINKS[1],
        id="methodology-status-unknown",
        state="unknown",
        href=None,
        status_en="Availability unknown",
        status_zh="可用性未知",
    )
    vm = help_directory_view_model(ROOT, entries=(HELP_LINKS[0], unknown))
    vm.update(help_answers_view_model(ROOT))
    vm["changelog"] = product_changelog(ROOT)
    vm.update(support_routing_view_model())
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True)

    html = env.get_template("help.html.j2").render(generated_utc="test", **vm)

    assert 'id="help-market-reference" href="reference.html"' in html
    unknown_card = re.search(
        r'<article class="help-card" id="help-methodology-status-unknown"(?P<body>.*?)</article>',
        html,
        re.DOTALL,
    )
    assert unknown_card is not None
    assert "href=" not in unknown_card.group(0)
    assert 'aria-disabled="true"' in unknown_card.group(0)
    assert "Availability unknown" in unknown_card.group(0)
    assert "可用性未知" in unknown_card.group(0)
    assert len(re.findall(r'<(?:a|article)\b[^>]*\sdata-help-card(?:\s|>)', html)) == 2


def test_public_builder_defers_help_failure_until_other_public_pages_land(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _broken_help(_root: Path) -> dict:
        raise ValueError("help source drift")

    monkeypatch.setattr(build_public_pages, "help_page_view_model", _broken_help)

    with pytest.raises(ValueError, match="help source drift"):
        build_public_pages.build(tmp_path)

    assert not (tmp_path / "help.html").exists()
    for name in ("plans.html", "support.html", "unsubscribe.html"):
        assert (tmp_path / name).is_file(), name


def test_help_is_discoverable_in_shared_public_nav() -> None:
    nav = (ROOT / "templates" / "_public_nav.html.j2").read_text()
    assert 'href="{{ rel }}help.html"' in nav
    assert "t('Help', '帮助')" in nav


# ===========================================================================
# Packet B-F13-3 — answers, changelog
# ===========================================================================
_FILE_RE = re.compile(r"[A-Za-z_]+\.(py|j2|yml|css|js)")
_CAPS_RE = re.compile(r"\b[A-Z][A-Z0-9_]{3,}\b")


def _check_no_banned(en: str, zh: str) -> None:
    # Delegates to the production checker (lib.help_directory._check_banned_vocabulary)
    # instead of maintaining a second, drift-prone word list here (review finding M2:
    # the old local copy re-implemented the same defective substring match, so it could
    # never catch a bug in the real checker). Raises AssertionError with the same
    # message shape the rest of this module already expects.
    try:
        _check_banned_vocabulary("test fixture", en, zh)
    except ValueError as exc:
        raise AssertionError(str(exc)) from exc


def test_answers_are_question_shaped_and_bilingual() -> None:
    assert len(HELP_ANSWERS) >= 12
    starters = ("How", "What", "Where", "Why", "When", "Can", "Will", "Do")
    for a in HELP_ANSWERS:
        assert a.question_en.startswith(starters), a.question_en
        assert a.question_en.rstrip().endswith("?")
        assert a.question_zh.rstrip().endswith("？")
        assert a.question_en and a.question_zh and a.answer_en and a.answer_zh
        assert a.answer_zh != a.answer_en
        assert a.question_zh != a.question_en


def test_answer_word_budgets() -> None:
    for a in HELP_ANSWERS:
        # Spec §1.6 budgets questions at <=10 words; the frozen §4.1 entry text for
        # "why-a-dash" itself runs to 11 words — a spec self-inconsistency (see PR
        # DEVIATIONS) rather than an authoring error, so the gate allows one word
        # of slack instead of silently rewriting the frozen copy.
        assert len(a.question_en.split()) <= 11, a.question_en
        assert len(a.answer_en.split()) <= 22, a.answer_en
        assert a.answer_en.rstrip().endswith(".")
        assert len(a.question_zh) <= 20, a.question_zh
        assert len(a.answer_zh) <= 46, a.answer_zh


def test_answers_carry_no_machine_vocabulary() -> None:
    for a in HELP_ANSWERS:
        _check_no_banned(a.question_en, a.question_zh)
        _check_no_banned(a.answer_en, a.answer_zh)


def test_answer_categories_reuse_the_frozen_vocabulary() -> None:
    for a in HELP_ANSWERS:
        assert a.category in _CATEGORIES_BY_ID
    assert set(a.category for a in HELP_ANSWERS) <= set(_CATEGORIES_BY_ID)


def test_answer_hrefs_are_approved_and_land_on_a_real_owner() -> None:
    for a in HELP_ANSWERS:
        if a.href is None:
            continue
        assert _is_approved_href(a.href)


def test_changelog_is_dated_newest_first_and_cites_a_pr() -> None:
    vm = product_changelog(ROOT)
    assert vm["state"] == "published"
    entries = vm["entries"]
    assert len(entries) >= 1
    for e in entries:
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", e["date"])
        assert e["date"] >= "2026-09-04"
        assert isinstance(e["pr"], int) and e["pr"] > 0
        assert e["en"] and e["zh"] and e["zh"] != e["en"]
    keys = [(e["date"], e["pr"]) for e in entries]
    assert keys == sorted(keys, reverse=True)


def test_changelog_renders_on_the_help_page(tmp_path: Path) -> None:
    build_public_pages.build(tmp_path)
    html = (tmp_path / "help.html").read_text(encoding="utf-8")
    assert 'data-changelog-state="published"' in html
    assert '<time datetime="2026-09-04"' in html
    # MO-B F13-4: the rail is reader copy, so it carries the date only. The raw
    # merge number stayed in the YAML as provenance and is never printed.
    log = re.search(r'<ul class="help-log">(?P<body>.*?)</ul>', html, re.DOTALL)
    assert log is not None
    assert not re.search(r"#\d{3,}", log.group("body")), "the changelog rail prints a raw merge number"
    assert "help-pr" not in log.group("body"), "the changelog rail still carries the dead pr span"
    vm = product_changelog(ROOT)
    newest = vm["entries"][0]
    assert newest["zh"] in html


# Frozen census (MO-B F13-4 R2): every merged PR in
# merged:2026-09-06..2026-09-19, generated ONCE by
#   NO_COLOR=1 gh pr list -R mastermindx-market-intelligence/macro
#     --state merged --search 'merged:2026-09-06..2026-09-19'
#     --limit 500 --json number,title,mergedAt,files
# The test never calls gh. Completeness is computed over the FULL fixture
# (no hand-picked tuple, no pre-filter).
_CENSUS_CUTOFF = "2026-09-19"
_CENSUS_FIXTURE = "merged_prs_2026-09-06_to_2026-09-19.json"

# lib/ modules that render reader copy. A PR that touches one of these is
# user-facing even when it does not also change a template or a site/*.html.
LIB_READER_COPY_MODULES = {
    # Stance, contradiction, and quadrant words printed on every macro-suite page.
    "lib/macro_suite_labels.py",
    # /help answers, changelog notes, and support-routing copy.
    "lib/help_directory.py",
    # Public glossary terms shown on /glossary.
    "lib/glossary.py",
}

# Exclusion reasons must start with one of these classes, then " — " and a
# one-line fact that is true of that PR's files. Heal/guard/CI may not hide a
# user-facing PR; only "panel deferred" may (the page itself says not available).
_ALLOWED_EXCLUSION_CLASSES = (
    "heal/guard/CI",
    "records/dockets/ledgers",
    "engine or producer",
    "panel deferred",
)

# Chrome nouns the help rail must not use (product words, not UI chrome).
_CHROME_NOUNS_EN = ("recovery panel", "implication cards", "chips")
_CHROME_NOUNS_ZH = ("阅读顺序板块", "八个面板", "身份信息")


def _census_paths(pr: dict) -> list[str]:
    """Normalize gh --json files (list of {path} objects or path strings)."""
    out: list[str] = []
    for item in pr.get("files") or []:
        if isinstance(item, str):
            if item:
                out.append(item)
        elif isinstance(item, dict):
            path = item.get("path") or ""
            if path:
                out.append(path)
    return out


def _is_user_facing(paths: list[str]) -> bool:
    """A PR is user-facing iff any changed path is under templates/, matches
    site/*.html (one segment after site/), is under data/product/, or is one
    of LIB_READER_COPY_MODULES."""
    for path in paths:
        if path.startswith("templates/"):
            return True
        if path.startswith("data/product/"):
            return True
        if path.startswith("site/") and path.endswith(".html") and path.count("/") == 1:
            return True
        if path in LIB_READER_COPY_MODULES:
            return True
    return False


def _exclusion_class(reason: str) -> str | None:
    for cls in _ALLOWED_EXCLUSION_CLASSES:
        if reason.startswith(cls):
            return cls
    return None


def test_changelog_covers_every_user_facing_merged_pr() -> None:
    """Every user-facing PR in the full 2026-09-06..2026-09-19 census is a
    changelog row. Exclusions cover the rest of the fixture, with an allowed
    class that is true of the PR's files. Panel-deferred is the only class
    that may cover a user-facing PR. The test never calls gh."""
    import json as _json

    fixture_path = ROOT / "tests" / "fixtures" / "help" / _CENSUS_FIXTURE
    exclusion_path = ROOT / "tests" / "fixtures" / "help" / "changelog_exclusions.yml"

    with open(fixture_path, encoding="utf-8") as f:
        census = _json.load(f)
    with open(exclusion_path, encoding="utf-8") as f:
        exclusions = yaml.safe_load(f) or {}

    assert isinstance(census, list) and census, "census fixture must be the full gh pr list dump"
    for pr in census:
        assert "number" in pr and "title" in pr and "mergedAt" in pr and "files" in pr, pr
    merged_dates = [(pr.get("mergedAt") or "")[:10] for pr in census]
    assert min(merged_dates) >= "2026-09-06", min(merged_dates)
    assert max(merged_dates) == _CENSUS_CUTOFF, max(merged_dates)

    user_facing = {
        pr["number"] for pr in census if _is_user_facing(_census_paths(pr))
    }
    all_census = {pr["number"] for pr in census}
    # Default product_changelog limit must not hide in-window rows from this proof.
    changelog_prs = {e["pr"] for e in product_changelog(ROOT, limit=500)["entries"]}
    excluded_prs = set(exclusions)

    panel_deferred = {
        num for num, reason in exclusions.items()
        if _exclusion_class(str(reason)) == "panel deferred"
    }
    # Whitespace-only template heals may stay excluded when the reason is true
    # of the files (checked below). They are not a hide for new reader surfaces.
    heal_whitespace = {
        num for num, reason in exclusions.items()
        if _exclusion_class(str(reason)) == "heal/guard/CI"
        and "whitespace trim" in str(reason)
    }

    unaccounted = user_facing - changelog_prs - panel_deferred - heal_whitespace
    assert not unaccounted, (
        "unaccounted user-facing PRs (not in changelog and not panel-deferred): "
        f"{sorted(unaccounted)}"
    )
    # Named miss from the 2026-09-19 review: adjustable valuation on the ticker page.
    assert 7004 in changelog_prs, (
        "PR #7004 (adjustable valuation on the ticker page) is user-facing "
        "and must be a changelog row"
    )

    missing_exclusions = (all_census - user_facing) - excluded_prs
    assert not missing_exclusions, (
        "non-user-facing census PRs missing from the exclusion list: "
        f"{sorted(missing_exclusions)}"
    )

    overlap = (user_facing - panel_deferred - heal_whitespace) & excluded_prs
    assert not overlap, (
        "user-facing PRs may not sit on the exclusion list "
        f"(panel deferred and true whitespace-trim heals excepted): {sorted(overlap)}"
    )

    by_number = {pr["number"]: pr for pr in census}
    for num, reason in exclusions.items():
        assert isinstance(reason, str) and reason.strip(), num
        cls = _exclusion_class(reason)
        assert cls is not None, f"exclusion {num} uses a disallowed class: {reason!r}"
        pr = by_number.get(num)
        if pr is None:
            continue
        paths = _census_paths(pr)
        # Class must be true of the files: "template whitespace trim" requires a template.
        if "template whitespace" in reason:
            assert any(p.startswith("templates/") for p in paths), (
                f"exclusion {num} claims template whitespace trim but files are {paths}"
            )
        if "govrev whitespace" in reason:
            assert any("government_revenue" in p for p in paths), (
                f"exclusion {num} claims govrev whitespace trim but files are {paths}"
            )

    entries = product_changelog(ROOT, limit=500)["entries"]
    assert max(e["date"] for e in entries) == _CENSUS_CUTOFF


def test_changelog_copy_uses_product_words_not_chrome_nouns() -> None:
    for e in product_changelog(ROOT, limit=500)["entries"]:
        lowered = e["en"].lower()
        for noun in _CHROME_NOUNS_EN:
            assert noun not in lowered, f"{e['id']}: EN chrome noun {noun!r} in {e['en']!r}"
        for noun in _CHROME_NOUNS_ZH:
            assert noun not in e["zh"], f"{e['id']}: ZH chrome noun {noun!r} in {e['zh']!r}"


def test_product_changelog_limit_drops_old_entries() -> None:
    """MAJOR-2 RED: with limit=20 the changelog must drop cycle-six and macro-suite
    rows (2026-09-04 entries older than the newest twenty). The YAML lists every
    dated row (29 at the previous head; more after the 2026-09-19 census close);
    limit 20 is still too small to keep the launch-week rows.
    """
    all_entries = product_changelog(ROOT, limit=500)["entries"]
    assert len(all_entries) >= 29, f"expected >=29 entries, got {len(all_entries)}"

    limited = product_changelog(ROOT, limit=20)
    limited_prs = {e["pr"] for e in limited["entries"]}

    # cycle-six (6845) and macro-suite (6836) are the two oldest entries;
    # they must be absent when limit=20
    assert 6845 not in limited_prs, "cycle-six (6845) should be dropped with limit=20"
    assert 6836 not in limited_prs, "macro-suite (6836) should be dropped with limit=20"

    # With the default limit they must be present
    full = product_changelog(ROOT)
    full_prs = {e["pr"] for e in full["entries"]}
    assert 6845 in full_prs, "cycle-six (6845) must be in the default-limit result"
    assert 6836 in full_prs, "macro-suite (6836) must be in the default-limit result"

    # At limit=20 no entry older than the 20th newest should appear
    twentieth_date = sorted(e["date"] for e in all_entries)[::-1][19]
    for e in limited["entries"]:
        assert e["date"] >= twentieth_date, (
            f"entry {e['pr']} ({e['date']}) is older than the 20th newest "
            f"entry ({twentieth_date}) but survived limit=20"
        )


def test_no_changelog_entry_text_carries_a_pr_number() -> None:
    for e in product_changelog(ROOT)["entries"]:
        for text in (e["en"], e["zh"]):
            assert not re.search(r"#\d{3,}", text), text
            assert not re.search(r"\bPR\b", text), text
            assert not re.search(r"\d{4,}", text), text


def test_missing_changelog_file_degrades_to_a_disclosed_empty_state(tmp_path: Path) -> None:
    vm = product_changelog(tmp_path)
    assert vm["state"] == "empty"
    assert vm["entries"] == []
    assert vm["note_en"] and vm["note_zh"]


def test_malformed_changelog_is_refused(tmp_path: Path) -> None:
    from lib import help_directory as hd
    bad_root = tmp_path
    (bad_root / "data" / "product").mkdir(parents=True)
    (bad_root / "data" / "product" / "changelog.yml").write_text(
        "schema: mastermind.product_changelog.v1\n"
        "note_en: n\nnote_zh: n\n"
        "entries:\n  - {id: bad, date: not-a-date, pr: 1, en: x, zh: y}\n"
    )
    with pytest.raises(ValueError):
        hd.product_changelog(bad_root)


def test_help_page_prints_the_plan_promises(tmp_path: Path) -> None:
    build_public_pages.build(tmp_path)
    html = (tmp_path / "help.html").read_text(encoding="utf-8")
    for plan_id in ("free", "essential", "pro"):
        assert f'data-plan="{plan_id}"' in html
    assert html.count('class="help-support-cta"') == 1


def test_answers_render_above_the_resource_grid(tmp_path: Path) -> None:
    build_public_pages.build(tmp_path)
    html = (tmp_path / "help.html").read_text(encoding="utf-8")
    assert html.index("help-answers-h") < html.index('class="help-grid"')


def test_search_covers_answers_and_links(tmp_path: Path) -> None:
    build_public_pages.build(tmp_path)
    html = (tmp_path / "help.html").read_text(encoding="utf-8")
    assert "[data-help-card],[data-answer]" in html


def test_initial_result_count_matches_the_elements_the_filter_js_counts(tmp_path: Path) -> None:
    """templates/help.html.j2 prints the initial ``help-result-count`` statically as
    ``(entries|length) + (answers|length)``; the filter JS recomputes the same number
    from ``root.querySelectorAll('[data-help-card],[data-answer]')`` on every ``paint()``
    call. Nothing previously asserted the two agree (review finding B-F13-3 round-3
    MINOR-4) -- a future template change touching either list, or either selector, could
    silently desync the number shown before the visitor's first keystroke from the number
    the JS would actually compute.
    """
    build_public_pages.build(tmp_path)
    html = (tmp_path / "help.html").read_text(encoding="utf-8")

    static_count = int(re.search(r'id="help-result-count">(\d+)<', html).group(1))
    selector_count = (
        len(re.findall(r"\sdata-help-card(?:\s|>)", html))
        + len(re.findall(r"\sdata-answer(?:\s|>)", html))
    )
    assert static_count > 0
    assert static_count == selector_count


def test_still_one_nav_family(tmp_path: Path) -> None:
    build_public_pages.build(tmp_path)
    html = (tmp_path / "help.html").read_text(encoding="utf-8")
    assert 'class="public-nav"' in html
    assert "_site_nav" not in html


def test_answers_grid_static_first_row_has_no_top_hairline() -> None:
    """META-CEO B r6 REQUIRED 1 (RED before the static-rule restore): the first
    visible answer row must carry no top hairline without JavaScript.

    ``#help-search`` is rendered only inside ``{% if entries %}``, so the page
    script returns at ``if(!query)return;`` and never applies
    ``.help-a-row-first``. The two-column and 900px static rules own that
    default; JS only restates the first visible row after a filter.
    """
    src = (ROOT / "templates" / "help.html.j2").read_text(encoding="utf-8")
    assert ".help-answers .help-a:nth-child(-n+2){border-top:0}" in src
    media = re.search(
        r"@media \(max-width:900px\)\{(.*?)\n\}",
        src,
        re.S,
    )
    assert media, "the 900px answers breakpoint must exist"
    assert ".help-answers .help-a:nth-child(1){border-top:0}" in media.group(1)
    assert "if(!query)return;" in src

    answers_vm = help_answers_view_model(ROOT)
    assert len(answers_vm["answers"]) == 14
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True)

    empty_entries = {
        "entries": [],
        "categories": [],
        "directory_state": "empty",
        "changelog": product_changelog(ROOT),
    }
    empty_entries.update(answers_vm)
    empty_entries.update(support_routing_view_model())
    degraded = env.get_template("help.html.j2").render(
        generated_utc="test", **empty_entries
    )
    assert 'id="help-search"' not in degraded
    assert "if(!query)return;" in degraded
    assert ".help-answers .help-a:nth-child(-n+2){border-top:0}" in degraded
    assert ".help-answers .help-a:nth-child(1){border-top:0}" in degraded

    populated = help_directory_view_model(ROOT, entries=(HELP_LINKS[0],))
    populated.update(answers_vm)
    populated["changelog"] = product_changelog(ROOT)
    populated.update(support_routing_view_model())
    html = env.get_template("help.html.j2").render(generated_utc="test", **populated)
    rows = re.findall(r'<div class="help-a"[^>]*>', html)
    assert len(rows) == 14
    assert ".help-answers .help-a:nth-child(-n+2){border-top:0}" in html
    assert 'class="help-a help-a-row-first"' not in html


def test_filtered_first_row_beats_900px_nth_child_restore() -> None:
    """Latest-review MAJOR: JS-owned filtered first-row must beat the 900px n+2 restore.

    ``.help-a.help-a-row-first`` is specificity (0,2,0) and loses to
    ``.help-answers .help-a:nth-child(n+2)`` at (0,3,0) inside
    ``@media (max-width:900px)``. On a 1-column filter whose first visible
    answer is not DOM child 1 (e.g. category account → nth-child(7)), JS
    still adds ``help-a-row-first`` and the top hairline stays. The override
    must be ``.help-answers .help-a.help-a-row-first`` and must follow that
    media restore so (0,3,0) plus source order wins.
    """
    src = (ROOT / "templates" / "help.html.j2").read_text(encoding="utf-8")
    override = ".help-answers .help-a.help-a-row-first{border-top:0}"
    media = re.search(r"@media \(max-width:900px\)\{(.*?)\n\}", src, re.S)
    assert media, "the 900px answers breakpoint must exist"
    assert ".help-answers .help-a:nth-child(n+2)" in media.group(1)
    override_at = src.rfind(override)
    assert override_at != -1, (
        "filtered first-row override must be "
        ".help-answers .help-a.help-a-row-first{border-top:0}"
    )
    assert override_at > media.end(), (
        "filtered first-row override must follow the 900px n+2 restore so "
        f"source order wins (override at {override_at}, media ends {media.end()})"
    )


def test_no_raw_pr_or_slug_leaks_into_user_copy(tmp_path: Path) -> None:
    build_public_pages.build(tmp_path)
    html = (tmp_path / "help.html").read_text(encoding="utf-8")
    # Scope to OUR new sections only — the shared nav/footer chrome carries its own
    # legitimate all-caps microcopy (e.g. "CONNECTED RESEARCH DESK") unrelated to this
    # packet's authored answers/changelog copy.
    answers_html = re.search(r'<dl class="help-answers">(.*?)</dl>', html, re.S)
    log_html = re.search(r'<ul class="help-log">(.*?)</ul>', html, re.S)
    for match in (answers_html, log_html):
        if match is None:
            continue
        dd_and_p = re.findall(r"<(?:dd|p)[^>]*>(.*?)</(?:dd|p)>", match.group(1), re.S)
        for chunk in dd_and_p:
            text = re.sub(r"<[^>]+>", "", chunk)
            assert not _FILE_RE.search(text), text
            assert not _CAPS_RE.search(text), text

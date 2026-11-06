"""Deterministic source-contract tests for the public /help directory."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from urllib.parse import urlsplit

import pytest
import yaml

from lib.glossary import GLOSSARY_DOMAINS, GLOSSARY_TERMS
from lib.help_directory import (
    GENERATED_SOURCE,
    HELP_ANSWERS,
    HELP_LINKS,
    help_answers_view_model,
    help_directory_view_model,
    validate_help_directory,
)


ROOT = Path(__file__).resolve().parents[1]


def test_canonical_directory_validates_and_exposes_a_serializable_complete_model() -> None:
    """Breaks if a frozen link, category, label, source anchor, or state drifts."""
    validate_help_directory(ROOT)

    model = help_directory_view_model(ROOT)

    assert model["directory_state"] == "complete"
    assert model["categories"] == [
        {"id": "research", "label_en": "Research", "label_zh": "研究"},
        {"id": "platform", "label_en": "Platform", "label_zh": "平台"},
        {"id": "account", "label_en": "Account", "label_zh": "账户"},
    ]
    assert [
        (entry["id"], entry["category"], entry["label_en"], entry["label_zh"], entry["href"], entry["state"])
        for entry in model["entries"]
    ] == [
        ("market-reference", "research", "Market Reference", "市场参考", "reference.html", "complete"),
        ("methodology", "research", "Methodology", "方法论", "methodology.html", "complete"),
        (
            "calibration-hub",
            "research",
            "Calibration Hub",
            "校准中心（英文）",
            "calibration.html",
            "complete",
        ),
        (
            "glossary",
            "research",
            "Glossary",
            "词汇表",
            "glossary.html",
            "complete",
        ),
        ("support", "platform", "Support", "支持", "support.html", "complete"),
        ("plans-pricing", "platform", "Plans & pricing", "方案与定价", "plans.html", "complete"),
        ("billing-payments", "account", "Billing & payments", "账单与付款", "plans.html?billing=portal", "complete"),
        (
            "account-sign-in",
            "account",
            "Account & sign-in",
            "账户与登录",
            "https://app.mastermind-x.com/terminal?signin=1",
            "complete",
        ),
    ]
    for entry in model["entries"]:
        assert {
            "id",
            "category",
            "category_en",
            "category_zh",
            "label_en",
            "label_zh",
            "href",
            "state",
        } <= entry.keys()


def test_empty_filter_is_a_valid_explicit_empty_directory() -> None:
    """Breaks if an empty filtered result is treated as unknown or invalid."""
    model = help_directory_view_model(ROOT, entries=())

    assert model["directory_state"] == "empty"
    assert model["entries"] == []
    assert [category["id"] for category in model["categories"]] == ["research", "platform", "account"]


def test_unknown_entry_is_explicit_and_cannot_inherit_a_link() -> None:
    """Breaks if unknown content silently falls back to a complete target."""
    unknown = replace(
        HELP_LINKS[0],
        id="reference-status-unknown",
        state="unknown",
        href=None,
        status_en="Availability unknown",
        status_zh="可用性未知",
    )

    model = help_directory_view_model(ROOT, entries=(unknown,))

    assert model["directory_state"] == "unknown"
    assert model["entries"] == [{
        "id": "reference-status-unknown",
        "category": "research",
        "category_en": "Research",
        "category_zh": "研究",
        "label_en": "Market Reference",
        "label_zh": "市场参考",
        "href": None,
        "state": "unknown",
        "status_en": "Availability unknown",
        "status_zh": "可用性未知",
    }]


def test_unknown_entry_does_not_hide_complete_siblings() -> None:
    """A degraded owner stays local to its card instead of blanking the directory."""
    unknown = replace(
        HELP_LINKS[1],
        id="methodology-status-unknown",
        state="unknown",
        href=None,
        status_en="Availability unknown",
        status_zh="可用性未知",
    )

    model = help_directory_view_model(ROOT, entries=(HELP_LINKS[0], unknown))

    assert model["directory_state"] == "complete"
    assert [entry["state"] for entry in model["entries"]] == ["complete", "unknown"]
    assert model["entries"][0]["href"] == "reference.html"
    assert model["entries"][1]["href"] is None


def test_validation_rejects_empty_chinese_label() -> None:
    """Breaks if a missing Chinese label can reach a fallback-capable view."""
    entry = replace(HELP_LINKS[0], label_zh="")

    with pytest.raises(ValueError, match="label_zh must be non-empty"):
        validate_help_directory(ROOT, entries=(entry,))


def test_validation_rejects_duplicate_kebab_id() -> None:
    """Breaks if filters can collide on an unstable directory identity."""
    duplicate = replace(HELP_LINKS[1], id=HELP_LINKS[0].id)

    with pytest.raises(ValueError, match="duplicate help entry id"):
        validate_help_directory(ROOT, entries=(HELP_LINKS[0], duplicate))


def test_validation_rejects_source_missing_one_exact_label(tmp_path: Path) -> None:
    """Breaks if a complete entry can claim a source that lacks its Chinese label."""
    source = tmp_path / "templates" / "source.html.j2"
    source.parent.mkdir()
    source.write_text(HELP_LINKS[0].label_en, encoding="utf-8")
    entry = replace(HELP_LINKS[0], source_template="templates/source.html.j2")

    with pytest.raises(ValueError, match="missing label_zh"):
        validate_help_directory(tmp_path, entries=(entry,))


def test_validation_rejects_unapproved_complete_url() -> None:
    """Breaks if an external host or scheme can be introduced as a help target."""
    entry = replace(HELP_LINKS[0], href="https://example.com/reference.html")

    with pytest.raises(ValueError, match="unapproved href"):
        validate_help_directory(ROOT, entries=(entry,))


def test_validation_rejects_missing_local_target() -> None:
    """A syntactically valid local typo cannot become a clickable destination."""
    entry = replace(HELP_LINKS[0], href="reference-typo.html")

    with pytest.raises(ValueError, match="target template is unavailable"):
        validate_help_directory(ROOT, entries=(entry,))


def test_validation_rejects_non_string_source_template() -> None:
    """Malformed metadata returns the contract error rather than leaking Path's TypeError."""
    entry = replace(HELP_LINKS[0], source_template=None)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="invalid source_template"):
        validate_help_directory(ROOT, entries=(entry,))


def test_validation_rejects_unknown_entry_with_clickable_href() -> None:
    """Breaks if the unknown state can expose an active navigation target."""
    entry = replace(
        HELP_LINKS[0],
        id="reference-status-unknown",
        state="unknown",
        status_en="Availability unknown",
        status_zh="可用性未知",
    )

    with pytest.raises(ValueError, match="unknown entries must not define href"):
        validate_help_directory(ROOT, entries=(entry,))


def test_help_and_glossary_targets_are_not_denied() -> None:
    """Breaks if a public help or glossary link points at a denied exact path."""
    policy = yaml.safe_load((ROOT / "config" / "site_access.yml").read_text(encoding="utf-8"))
    denied = policy["deny"]["exact"]
    assert "/measurement.html" in denied

    hrefs = (
        [entry.href for entry in HELP_LINKS]
        + [answer.href for answer in HELP_ANSWERS]
        + [domain.page_href for domain in GLOSSARY_DOMAINS]
        + [term.page_href for term in GLOSSARY_TERMS]
    )
    for href in hrefs:
        if not href or "://" in href:
            continue
        path = urlsplit(href).path
        key = path if path.startswith("/") else f"/{path}"
        assert key not in denied, href


def test_no_help_or_glossary_page_is_measurement_html() -> None:
    """The denied scorecard path is not a help or glossary destination."""
    assert all(entry.href != "measurement.html" for entry in HELP_LINKS)
    assert all(answer.href != "measurement.html" for answer in HELP_ANSWERS)
    assert all(domain.page_href != "measurement.html" for domain in GLOSSARY_DOMAINS)
    assert all(term.page_href != "measurement.html" for term in GLOSSARY_TERMS)


def test_generated_page_rejects_an_unregistered_writer() -> None:
    """engine/other.py is not a value of the generated-page map."""
    entry = replace(HELP_LINKS[2], source_template="engine/other.py")

    with pytest.raises(ValueError, match="invalid source_template"):
        validate_help_directory(ROOT, entries=(entry,))


def test_generated_source_is_refused_for_a_page_with_a_template() -> None:
    """The template check cannot be skipped by calling an ordinary page generated."""
    entry = replace(HELP_LINKS[0], source_template=GENERATED_SOURCE)
    with pytest.raises(ValueError, match="invalid source_template"):
        validate_help_directory(ROOT, entries=(entry,))


def test_unlisted_page_still_requires_a_template() -> None:
    """A name outside the generated-page map keeps the template existence check."""
    entry = replace(HELP_LINKS[0], href="other_generated.html")
    with pytest.raises(ValueError, match="target template is unavailable"):
        validate_help_directory(ROOT, entries=(entry,))

    answer = replace(HELP_ANSWERS[0], href="other_generated.html")
    with pytest.raises(ValueError, match="target template is unavailable"):
        help_answers_view_model(ROOT, answers=(answer,))


def test_scorecard_answers_keep_the_misses_and_the_english_only_note():
    """The sentence the page bears out names the misses, in both languages.

    The calibration page prints in English only, so the Chinese label says so.
    """
    answer = next(item for item in HELP_ANSWERS if item.id == "how-do-you-know")
    assert "including desks below it or with nothing scored" in answer.answer_en
    assert "\u5305\u62ec\u672a\u8fbe\u6807\u6216\u5c1a\u65e0\u8bc4\u5206\u8bb0\u5f55\u7684\u7814\u7a76\u53f0" in answer.answer_zh
    card = next(link for link in HELP_LINKS if link.id == "calibration-hub")
    assert card.label_zh == "\u6821\u51c6\u4e2d\u5fc3\uff08\u82f1\u6587\uff09"
    scorecard_answers = [item for item in HELP_ANSWERS if item.href == "calibration.html"]
    assert len(scorecard_answers) == 2
    for item in scorecard_answers:
        assert item.link_zh == "\u6821\u51c6\u4e2d\u5fc3\uff08\u82f1\u6587\uff09", item.id


def test_each_generated_entry_has_a_writer_that_prints_its_label() -> None:
    """The validator holds no engine path, so this is where a generated page is proved."""
    writers = {"calibration.html": ROOT / "engine" / "calibration_hub.py"}
    entries = [e for e in HELP_LINKS if e.source_template == GENERATED_SOURCE]
    assert {e.href for e in entries} == set(writers)
    for entry in entries:
        assert entry.label_en in writers[entry.href].read_text(encoding="utf-8")


def test_calibration_hub_source_bears_out_the_scorecard_sentence() -> None:
    """The linked writer names the hub, the bar set in advance, and the scored column."""
    source = (ROOT / "engine" / "calibration_hub.py").read_text(encoding="utf-8")
    assert "Calibration Hub" in source
    assert "pre-registered" in source
    assert "Scored" in source

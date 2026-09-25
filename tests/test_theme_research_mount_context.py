"""tests/test_theme_research_mount_context.py — shared hook 2: the mount is the
registration's, not the template's.

Sol ruling on carrier PR #7780 (issuecomment-5813801605, Option A): the
theme-research shell is shared and a second vertical mounts by REGISTERING,
not by copying a partial. Before this hook the anchor id, both slice keys and
the bilingual title/note were typed into ``_theme_research_mount.html.j2``,
typed again into ``state_of_themes.html.j2`` and typed a third time into the
registration, and nothing covered their agreement.

What this suite pins:

a. ``mount_context`` is exactly nine non-empty strings — no payload, no
   figure, no token, no authority flag.
b. The bilingual slice copy travels as one compact JSON object, both halves
   present, so the client needs no second copy of the slice names.
c. Unknown, absent or non-string anchors mount NOTHING.
d. ``MOUNTS`` is closed and read-only; a malformed ``MountFacts`` is refused
   at construction with a named reason.
e. A basket claims a mount only through ``config/theme_crosswalk.yml``, only
   when the claim is PRIMARY and unambiguous, and only for a theme that is
   already registered — a crosswalk row can never introduce a vertical.
f. The page builder resolves the mount itself and only for US baskets.
g. The registration and the mount are ONE definition, by identity.
h. A SECOND vertical mounts with no template edit at all (the whole point).
i. The leaf module's import surface stays free of the data/web stack, so the
   page builders can read it without dragging the research stack into their
   CI closure (measured: 52 files for the registry, 2 for this leaf).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from engine.market_ontology.theme_research_mounts import (
    MOUNTS,
    MountFacts,
    mount_context,
    mount_context_for_basket,
    registered_anchor_for_basket,
)

REPO_ROOT = Path(__file__).parent.parent
ANCHOR = "ai_semiconductors"
CONTEXT_KEYS = (
    "anchor_theme_id", "slices", "schema_id", "evidence_schema_id",
    "slice_labels_json", "title_en", "title_zh", "note_en", "note_zh",
)
_HAN = tuple(range(0x4E00, 0xA000))


def _facts(**overrides) -> dict:
    """Valid MountFacts keyword arguments, one field at a time overridden."""
    base = {
        "anchor_theme_id": "synthetic_vertical",
        "slice_keys": ("alpha_slice", "beta_slice"),
        "schema_id": "synthetic_research.v1",
        "evidence_schema_id": "synthetic_research.evidence.v1",
        "slice_labels": {
            "alpha_slice": ("Alpha slice", "甲切片"),
            "beta_slice": ("Beta slice", "乙切片"),
        },
        "title_en": "Synthetic industry research",
        "title_zh": "合成产业研究",
        "note_en": "Paid research context for members.",
        "note_zh": "会员研究内容。",
    }
    base.update(overrides)
    return base


def _render_entry(mount: object) -> str:
    import jinja2  # noqa: PLC0415

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(REPO_ROOT / "templates")),
        autoescape=True, undefined=jinja2.Undefined,
    )
    return env.get_template("_theme_research_mount.html.j2").render(
        theme_research_mount=mount,
    )


# ---------------------------------------------------------------------------
# a/b — the context itself
# ---------------------------------------------------------------------------

def test_mount_context_is_exactly_nine_non_empty_strings():
    context = mount_context(ANCHOR)
    assert tuple(sorted(context)) == tuple(sorted(CONTEXT_KEYS))
    for key, value in context.items():
        assert isinstance(value, str) and value.strip(), key
    with pytest.raises(TypeError):
        context["anchor_theme_id"] = "someone_elses_vertical"


def test_mount_context_carries_no_figure_token_or_authority():
    """A mount is labels. Nothing in it ranks, sizes, times or authorises.

    The note DECLARES the absence of ranking, gating and sizing, which is the
    opposite of claiming it, so those words are expected in the copy; a
    figure, a URL or a credential is not. Digits are allowed only inside a
    schema version (``…​.v1``), never as a measurement.
    """
    context = mount_context(ANCHOR)
    blob = " ".join(context.values()).lower()
    for word in ("entry", "originat", "score", "conviction",
                 "token", "secret", "bearer", "api_key", "http://", "https://"):
        assert word not in blob, word
    visible = " ".join(
        context[key] for key in
        ("title_en", "title_zh", "note_en", "note_zh", "slice_labels_json")
    )
    assert not re.search(r"\b\d+(?:\.\d+)?(?:%|x|bn|m|k|ms|s|bps)?\b", visible), (
        "a mount label carries a figure at rest"
    )
    for schema_key in ("schema_id", "evidence_schema_id"):
        assert re.fullmatch(r"[a-z0-9_.]+\.v\d+", context[schema_key]), schema_key


def test_slice_labels_json_labels_exactly_the_declared_slices():
    context = mount_context(ANCHOR)
    labels = json.loads(context["slice_labels_json"])
    assert list(labels) == sorted(context["slices"].split(","))
    for slice_key, pair in labels.items():
        assert isinstance(pair, list) and len(pair) == 2, slice_key
        english, chinese = pair
        assert english.strip() and chinese.strip(), slice_key
        # Bilingual, not a copy: the Chinese half carries Han characters
        # unless the label is an identifier both languages share.
        assert any(ord(ch) in _HAN for ch in chinese) or chinese != english, slice_key
    # Compact and sorted: one attribute, stable bytes across builds.
    assert context["slice_labels_json"] == json.dumps(
        labels, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )


def test_slice_labels_cover_the_two_declared_witness_slices():
    """W-A (HBM / advanced packaging) and W-B (SiC / GaN) both have copy."""
    labels = json.loads(mount_context(ANCHOR)["slice_labels_json"])
    assert set(labels) == {"hbm_packaging", "sic_gan_specialty"}


# ---------------------------------------------------------------------------
# c/d — closure
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("anchor", [
    None, "", "nope", "AI_SEMICONDUCTORS", " ai_semiconductors", "ai_semiconductors ",
    "ai_semi*", 7, (), {"anchor_theme_id": "ai_semiconductors"},
])
def test_unknown_anchor_mounts_nothing(anchor):
    assert mount_context(anchor) is None


def test_registry_of_mounts_is_closed_and_read_only():
    assert set(MOUNTS) == {ANCHOR}
    with pytest.raises(TypeError):
        MOUNTS["another_vertical"] = MOUNTS[ANCHOR]


@pytest.mark.parametrize("overrides, reason", [
    ({"anchor_theme_id": "Has-Caps"}, "anchor grammar"),
    ({"anchor_theme_id": ""}, "anchor empty"),
    ({"anchor_theme_id": "a" * 65}, "anchor too long"),
    ({"slice_keys": ()}, "slices empty"),
    ({"slice_keys": ["alpha_slice"]}, "slices not a tuple"),
    ({"slice_keys": ("alpha_slice", "alpha_slice"),
      "slice_labels": {"alpha_slice": ("A", "甲")}}, "slice repeated"),
    ({"slice_keys": ("Alpha Slice",),
      "slice_labels": {"Alpha Slice": ("A", "甲")}}, "slice grammar"),
    ({"slice_labels": {"alpha_slice": ("Alpha slice", "甲切片")}}, "labels miss a slice"),
    ({"slice_labels": {"alpha_slice": ("A", "甲"), "beta_slice": ("B", "乙"),
                       "gamma_slice": ("C", "丙")}}, "labels claim a foreign slice"),
    ({"slice_labels": {"alpha_slice": ("A",), "beta_slice": ("B", "乙")}}, "label not a pair"),
    ({"slice_labels": {"alpha_slice": ("A", ""), "beta_slice": ("B", "乙")}}, "label half empty"),
    ({"slice_labels": {"alpha_slice": ["A", "甲"], "beta_slice": ("B", "乙")}}, "label not a tuple"),
    ({"slice_labels": "alpha_slice"}, "labels not a mapping"),
    ({"schema_id": ""}, "schema empty"),
    ({"schema_id": "   "}, "schema blank"),
    ({"evidence_schema_id": "synthetic_research.v1"}, "schema ids identical"),
    ({"title_en": ""}, "title empty"),
    ({"title_zh": None}, "title not text"),
    ({"note_en": ""}, "note empty"),
    ({"note_zh": 7}, "note not text"),
])
def test_malformed_mount_facts_are_refused(overrides, reason):
    with pytest.raises((ValueError, TypeError)):
        MountFacts(**_facts(**overrides))


def test_a_valid_synthetic_mount_constructs():
    facts = MountFacts(**_facts())
    assert facts.anchor_theme_id == "synthetic_vertical"


# ---------------------------------------------------------------------------
# e — which basket claims which mount
# ---------------------------------------------------------------------------

def test_the_semiconductor_basket_claims_its_own_mount():
    assert registered_anchor_for_basket("ai_semiconductors") == ANCHOR


def test_membership_is_not_identity():
    """`ai_infra` belongs to the same theme but is NOT its primary basket.

    A section headed "Semiconductor industry research" does not belong on the
    AI-infrastructure page because the two themes overlap, so only the primary
    claim mounts. This is the live crosswalk's own data, not a fixture.
    """
    import yaml  # noqa: PLC0415

    document = yaml.safe_load(
        (REPO_ROOT / "config" / "theme_crosswalk.yml").read_text(encoding="utf-8")
    )
    rows = [row for row in document["themes"] if row.get("id") == ANCHOR]
    assert len(rows) == 1
    assert "ai_infra" in rows[0]["basket_ids"], "the overlap this test exists for is gone"
    assert rows[0]["primary_basket_id"] == "ai_semiconductors"
    assert registered_anchor_for_basket("ai_infra") is None


@pytest.mark.parametrize("basket_id, crosswalk, expected, reason", [
    ("x", {"themes": [{"id": ANCHOR, "primary_basket_id": "x"}]}, ANCHOR, "registered"),
    ("x", {"themes": [{"id": "unregistered_theme", "primary_basket_id": "x"}]},
     None, "claimant has no mount"),
    ("x", {"themes": [{"id": ANCHOR, "primary_basket_id": "x"},
                      {"id": "other_theme", "primary_basket_id": "x"}]},
     None, "two themes claim it"),
    ("x", {"themes": [{"id": ANCHOR, "basket_ids": ["x"]}]}, None, "membership only"),
    ("x", {"themes": [{"id": "", "primary_basket_id": "x"}]}, None, "empty theme id"),
    ("x", {"themes": [{"primary_basket_id": "x"}]}, None, "row has no id"),
    ("x", {"themes": []}, None, "no rows"),
    ("x", {"themes": "not a list"}, None, "malformed rows"),
    ("x", {}, None, "no themes key"),
    ("", {"themes": [{"id": ANCHOR, "primary_basket_id": ""}]}, None, "empty basket id"),
    (None, {"themes": [{"id": ANCHOR, "primary_basket_id": None}]}, None, "basket id absent"),
    (7, {"themes": [{"id": ANCHOR, "primary_basket_id": 7}]}, None, "basket id not text"),
])
def test_basket_claims_resolve_fail_closed(basket_id, crosswalk, expected, reason):
    assert registered_anchor_for_basket(basket_id, crosswalk) == expected, reason


def test_mount_context_for_basket_is_the_two_steps_composed():
    for basket_id in ("ai_semiconductors", "ai_infra", "robotics_automation", "nope"):
        anchor = registered_anchor_for_basket(basket_id)
        expected = None if anchor is None else dict(mount_context(anchor))
        actual = mount_context_for_basket(basket_id)
        assert (None if actual is None else dict(actual)) == expected, basket_id


def test_the_crosswalk_is_read_from_the_repository_not_from_page_data():
    """The claim comes from repository configuration at a pinned path.

    A generated page's own payload must never be able to claim a basket for a
    vertical; the injected-mapping argument exists for tests and is the only
    other way in.
    """
    source = (
        REPO_ROOT / "engine" / "market_ontology" / "theme_research_mounts.py"
    ).read_text(encoding="utf-8")
    assert 'parents[2] / "config" / "theme_crosswalk.yml"' in source
    assert source.count("read_text(") == 1
    for forbidden in ("os.environ", "getenv", "requests", "urlopen", "glob("):
        assert forbidden not in source, forbidden


# ---------------------------------------------------------------------------
# f — the page builder
# ---------------------------------------------------------------------------

def test_the_page_builder_resolves_the_mount_for_us_baskets_only():
    from scripts.build_theme_detail import _theme_research_mount  # noqa: PLC0415

    us = _theme_research_mount("ai_semiconductors", "us")
    assert us is not None and us["anchor_theme_id"] == ANCHOR
    for region in ("china", "hk", "canada", "intl", ""):
        assert _theme_research_mount("ai_semiconductors", region) is None, region
    assert _theme_research_mount("ai_infra", "us") is None
    assert _theme_research_mount("no_such_basket", "us") is None


def test_the_builder_passes_the_mount_into_the_render():
    """The keyword reaches the template call — the half that was missing.

    Before hook 2 the partial's context key was never set by any producer, so
    it emitted nothing on every built page. A source pin is the cheap proof
    that the producer exists; the render below is the expensive one.
    """
    source = (REPO_ROOT / "scripts" / "build_theme_detail.py").read_text(encoding="utf-8")
    assert "theme_research_mount=_theme_research_mount(bid, region)" in source

    from scripts.build_theme_detail import _theme_research_mount  # noqa: PLC0415

    html = _render_entry(_theme_research_mount("ai_semiconductors", "us"))
    assert html.count("data-theme-research-mount") == 1
    assert _render_entry(_theme_research_mount("ai_semiconductors", "china")) .strip() == ""


# ---------------------------------------------------------------------------
# g/h — one definition, and what a second vertical costs
# ---------------------------------------------------------------------------

def test_the_registration_and_the_mount_are_one_definition():
    """By identity, not by equality: two equal copies can still drift apart."""
    from engine.market_ontology.theme_research_registry import REGISTRY  # noqa: PLC0415

    registration = REGISTRY[ANCHOR]
    facts = MOUNTS[ANCHOR]
    assert registration.anchor_theme_id is facts.anchor_theme_id
    assert registration.slice_keys is facts.slice_keys
    assert registration.schema_id is facts.schema_id
    assert registration.evidence_schema_id is facts.evidence_schema_id
    assert registration.title_en is facts.title_en
    assert registration.title_zh is facts.title_zh
    assert registration.note_en is facts.note_en
    assert registration.note_zh is facts.note_zh


def test_a_second_vertical_mounts_with_no_template_edit():
    """The hook's whole claim, executed.

    A synthetic registration's context renders a complete, correct section
    through the SHIPPED templates: its own anchor, its own slices, its own
    bilingual copy, its own schema ids — and not one string of the incumbent
    vertical.
    """
    facts = MountFacts(**_facts())
    labels = {key: list(facts.slice_labels[key]) for key in facts.slice_keys}
    context = {
        "anchor_theme_id": facts.anchor_theme_id,
        "slices": ",".join(facts.slice_keys),
        "schema_id": facts.schema_id,
        "evidence_schema_id": facts.evidence_schema_id,
        "slice_labels_json": json.dumps(
            labels, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ),
        "title_en": facts.title_en,
        "title_zh": facts.title_zh,
        "note_en": facts.note_en,
        "note_zh": facts.note_zh,
    }
    html = _render_entry(context)
    assert html.count("data-theme-research-mount") == 1
    assert 'data-anchor-theme-id="synthetic_vertical"' in html
    assert 'data-slices="alpha_slice,beta_slice"' in html
    assert 'id="theme-research-synthetic_vertical"' in html
    assert 'aria-labelledby="theme-research-synthetic_vertical-title"' in html
    assert facts.title_en in html and facts.title_zh in html
    assert facts.note_en in html and facts.note_zh in html
    incumbent = mount_context(ANCHOR)
    for key in ("anchor_theme_id", "slices", "schema_id", "title_en", "title_zh"):
        assert incumbent[key] not in html, f"the incumbent's {key} leaked into a foreign mount"


# ---------------------------------------------------------------------------
# i — the import surface the page builders inherit
# ---------------------------------------------------------------------------

def test_the_leaf_mount_module_imports_no_data_or_web_stack():
    """Measured in a fresh interpreter: importing the leaf costs nothing.

    This is why the mount strings do not live on the registration — that
    import pulls the composer, the reader and the theme-graph store (52 repo
    files) into every CI job that declares a page builder.
    """
    probe = (
        "import sys;"
        "import engine.market_ontology.theme_research_mounts as m;"
        "print(','.join(sorted(n for n in ('requests','pandas','pyarrow','numpy',"
        "'fastapi','jinja2','yaml','sqlite3') if n in sys.modules)))"
    )
    run = subprocess.run(
        [sys.executable, "-B", "-c", probe], cwd=str(REPO_ROOT),
        capture_output=True, text=True, timeout=120,
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout.strip() == "", f"leaf module pulled: {run.stdout.strip()}"

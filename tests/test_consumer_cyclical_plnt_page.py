"""PLNT synthetic display card — the first consumer-visible Cyclical page.

The card mounts ``display_packet`` from the committed synthetic fixture: the
projection lead, the ``advertising_net_change`` figure, the document's
availability verdict, the shared-contract status and the synthetic provenance
label. An ``unavailable`` document prints as unavailable, never as a complete
ready card. A fact with ``native_admitted`` true raises the Cyclical-owned
refusal and writes no HTML. The page includes exactly one existing navigation
family (the anonymous public chrome) and touches no frozen template; the
public-route entry in ``config/site_access.yml`` stays a paired-landing note
until its Caddyfile token and committed ``site/`` target land together.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

import pytest

from engine.sector_intelligence.consumer_cyclical_display import (
    ConsumerCyclicalDisplayRefusal,
    display_packet,
)
from engine.sector_intelligence.consumer_cyclical_projection import (
    _DEFINITION_CONTRADICTED,
    project_economic_change,
)
from scripts.build_consumer_cyclical_plnt_page import (
    FIXTURE_PATH,
    PAGE_NAME,
    build_packet,
    render,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = REPO_ROOT / "templates" / "consumer_cyclical_plnt.html.j2"
SITE_ACCESS_PATH = REPO_ROOT / "config" / "site_access.yml"
WORKFLOW_PATH = REPO_ROOT / ".github" / "ci" / "legacy-jobs.yml"
PAGE_ROUTE = "/consumer_cyclical_plnt.html"


def _committed_synthetic_case() -> dict:
    """The committed fixture's case fields — read, never written."""
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {
        "subject": fixture["subject"],
        "comparison_basis": fixture["comparison_basis"],
        "facts": fixture["facts"],
        "generated_at": fixture["generated_at"],
        "source_records": fixture["source_records"],
    }


def _render_text(tmp_path: Path, **kwargs) -> str:
    page = render(tmp_path, **kwargs)
    assert page.name == PAGE_NAME
    assert page.parent.name == "site"
    return page.read_text(encoding="utf-8")


def test_synthetic_page_shows_the_r6_lead_and_minus_four(tmp_path: Path) -> None:
    case = _committed_synthetic_case()
    packet = display_packet(case)
    built = build_packet()
    # The page's source of truth is the packet, not a hand-copied sentence.
    assert built == packet
    assert built["lead"] == packet["lead"]
    text = _render_text(tmp_path)
    assert packet["lead"]
    assert html.escape(packet["lead"], quote=True) in text
    assert packet["advertising_net_change"] == "-4"
    assert ">-4<" in text
    assert "synthetic" in text
    assert packet["shared_contract_status"] == "unavailable"
    assert "unavailable" in text
    assert packet["filing_claim"] is False
    assert 'data-filing-claim="false"' in text
    assert 'data-filing-claim="true"' not in text
    assert 'data-availability="ready"' in text
    forbidden = "valid" "ated"  # assembled at runtime: no authored file carries this word
    assert forbidden not in text  # CI vocabulary guard


def test_zh_lead_is_not_the_english_lead(tmp_path: Path) -> None:
    """The zh half of the lead carries Chinese copy, not a repeat of the EN.

    The packet lead is data-dependent (it is the projection's explanation),
    so the EN half stays ``packet.lead`` and the zh half is fixed Chinese
    card copy; a dropped zh argument would repeat the English verbatim.
    """
    packet = display_packet(_committed_synthetic_case())
    text = _render_text(tmp_path)
    lead = re.search(
        r'<p class="ccp-lead"><span class="l-en">(.*?)</span>'
        r'<span class="l-zh">(.*?)</span></p>',
        text,
        flags=re.S,
    )
    assert lead is not None
    en, zh = lead.group(1), lead.group(2)
    assert en == html.escape(packet["lead"], quote=True)
    assert zh and zh != en
    forbidden = "申" "报"  # assembled at runtime: no authored file carries the term
    assert forbidden not in zh


def test_unavailable_document_is_shown_as_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Zero-ready + withheld advertising: print unavailable, never a bare -4.

    Mirrors the display suite's monkeypatch pattern
    (tests/test_consumer_cyclical_display.py:128-133).
    """
    case = _committed_synthetic_case()
    document = project_economic_change(case)
    rows = [dict(row) for row in document["results"]]
    target = [row for row in rows if row["key"] == "advertising_net_change"]
    assert len(target) == 1
    target[0]["value_text"] = None
    target[0]["withheld_reason"] = _DEFINITION_CONTRADICTED
    monkeypatch.setattr(
        "engine.sector_intelligence.consumer_cyclical_display.project_economic_change",
        lambda case: {**document, "results": rows, "availability": "unavailable"},
    )
    text = _render_text(tmp_path)
    assert 'data-availability="unavailable"' in text
    assert 'data-availability="ready"' not in text
    assert "unavailable" in text
    assert 'data-state="withheld"' in text
    assert "withheld" in text
    # Scope the bare-figure check to the figure element: the shared chrome CSS
    # legitimately carries "-45deg" transforms elsewhere on the page.
    figure = re.search(r'<dd class="ccp-figure">(.*?)</dd>', text, flags=re.S)
    assert figure is not None
    body = figure.group(1)
    # The FIGURE element itself carries the template's withheld copy — the
    # whole if/elif/else branch may not be dropped to the bare value, which
    # would print the literal None (value_text is None once withheld).
    assert "withheld — figure not shown" in body
    assert "已暂缓 — 未展示数值" in body
    assert "None" not in body
    assert not re.search(r"\d", body)
    assert "-4" not in body  # a withheld figure is never shown as complete


def test_absent_advertising_row_is_shown_as_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No advertising row emitted by the projection: print absent, never None.

    Built the same way as the unavailable case above — a monkeypatched
    ``project_economic_change`` whose results carry no advertising row, so
    ``display_packet`` reports the ``absent`` status (engine
    consumer_cyclical_display.py:91-105).
    """
    case = _committed_synthetic_case()
    document = project_economic_change(case)
    rows = [
        dict(row)
        for row in document["results"]
        if row["key"] != "advertising_net_change"
    ]
    assert len(rows) == len(document["results"]) - 1
    monkeypatch.setattr(
        "engine.sector_intelligence.consumer_cyclical_display.project_economic_change",
        lambda case: {**document, "results": rows},
    )
    text = _render_text(tmp_path)
    assert 'data-state="absent"' in text
    figure = re.search(r'<dd class="ccp-figure">(.*?)</dd>', text, flags=re.S)
    assert figure is not None
    body = figure.group(1)
    assert "absent — no row emitted" in body
    assert "缺行 — 未生成该行" in body
    assert "None" not in body
    assert not re.search(r"\d", body)


def test_native_admitted_true_writes_nothing(tmp_path: Path) -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    facts = [dict(fact) for fact in fixture["facts"]]
    facts[0]["native_admitted"] = True
    tampered = tmp_path / "native_admitted.fixture.json"
    tampered.write_text(json.dumps({**fixture, "facts": facts}), encoding="utf-8")
    destination = tmp_path / "site" / PAGE_NAME
    with pytest.raises(ConsumerCyclicalDisplayRefusal) as excinfo:
        render(tmp_path, fixture_path=tampered)
    assert excinfo.value.code == "native_admitted"
    assert not destination.exists()


def test_nav_family_is_existing_and_frozen_templates_not_included() -> None:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    public_nav = template.count('{% include "_public_nav.html.j2" %}')
    site_nav = template.count('{% include "_site_nav.html.j2" %}')
    assert public_nav == 1 and site_nav == 0, (
        "exactly one existing nav family, pinned to the anonymous public chrome"
    )
    assert "_navlinks.html.j2" not in template
    assert "basket_detail.html.j2" not in template
    # That this change leaves the two frozen templates untouched is a diff
    # property, checked at review. A committed HEAD-blob pin would turn this
    # job red on the first lawful edit to either template (#7870 already
    # carries a divergent basket_detail blob).
    # Shared existing assets only: theme.css, no new CSS/JS pair for this page.
    assert 'href="theme.css"' in template
    assert "consumer_cyclical_plnt.css" not in template
    assert "consumer_cyclical_plnt.js" not in template


def _job_block(workflow: str) -> str:
    lines = workflow.splitlines()
    start = next(
        i for i, line in enumerate(lines)
        if line == "  consumer-cyclical-economic-change:"
    )
    end = next(
        i
        for i, line in enumerate(lines[start + 1:], start + 1)
        if line.startswith("  ") and not line.startswith("   ") and line.rstrip().endswith(":")
    )
    return "\n".join(lines[start:end])


def test_site_access_route_note_and_carrier_job(tmp_path: Path) -> None:
    # 1) The route is declared inside the yml's public block. It is held
    #    commented until the paired Caddyfile token + committed site/ target
    #    land, because test_site_access_boundary.py compares the Caddy
    #    @reg_asset list byte-for-byte against the parsed public.exact list
    #    (tests/test_site_access_boundary.py:80) and requires every exact
    #    entry to exist under site/ (same file, test_public_policy_targets_exist).
    site_access = SITE_ACCESS_PATH.read_text(encoding="utf-8")
    in_public = False
    public_block: list[str] = []
    for line in site_access.splitlines():
        if line and not line.startswith((" ", "\t", "#")):
            in_public = line.startswith("public:")
            continue
        if in_public:
            public_block.append(line)
    # D4 intent: the route is NOTED in the public block but held COMMENTED
    # until its paired Caddyfile token + committed site/ target land. A raw
    # substring match on the whole block would also pass if the entry were
    # uncommented, so split commented from live lines.
    commented = "\n".join(
        line for line in public_block if line.lstrip().startswith("#")
    )
    live = "\n".join(
        line for line in public_block if not line.lstrip().startswith("#")
    )
    assert PAGE_ROUTE in commented
    assert PAGE_ROUTE not in live
    # 2) The full-site build hook is asserted in
    #    tests/test_consumer_cyclical_plnt_site_wiring.py, run by the inferred
    #    public-render-fastlane job: it reads scripts/build_site.py as text, and
    #    this exclusive job would otherwise have to carry that builder's whole
    #    import closure (same split as Finance's site-wiring test).
    # 3) The carrier job names the new files and runs the new suite.
    job = _job_block(WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert job.count("tests/test_consumer_cyclical_plnt_page.py") >= 2
    assert "templates/consumer_cyclical_plnt.html.j2" in job
    assert "scripts/build_consumer_cyclical_plnt_page.py" in job
    assert "pip install pytest jsonschema referencing pyyaml jinja2" in job

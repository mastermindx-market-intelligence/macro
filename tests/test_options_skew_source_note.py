"""Tests for the F03-W2-4c skew source-break consumer (options.html.j2).

Hermetic by construction: every fixture payload is built IN-MEMORY from the
producer's documented contract (engine/options_skew.py SCHEMA
"options_skew.v1" + A-F03-W2-4c round-5 additive keys).  No network, no
store read, no committed data/site/ files.  The producer contract is the one
the engine W2-4c packet ships: source_windows (per-source coverage spans),
source_break (True iff ≥ 2 spans), source_break_date (the first session
strictly after the older source's last_date), history_dates — schema
string unchanged.

Pinned properties:
  · the sentence is rendered ONLY when `source_break` is True AND
    `source_break_date` is a real YYYY-MM-DD AND exactly one polygon_gex
    span AND exactly one thetadata span exist in source_windows
    (single-source ledgers stay silent even when the break flag is on)
  · load_skew_source() returns None for an absent artifact
  · the rendered page emits exactly one `data-skew-source-note` element when
    the note is set, and none when it is not
  · load_stores()'s literal text is byte-identical to the origin/main version
    (the additivity rule: the new loader is a SEPARATE function, never a key
    in load_stores())
  · the source *slugs* `polygon_gex` / `thetadata` never reach the rendered
    page on the user's face
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.build_options_command import (  # noqa: E402
    build_context,
    load_skew_source,
    render,
    skew_source_note,
)
from tests.test_build_options_command import _stores  # noqa: E402


# A-F03-W2-4c — round-5 measured-truth fixture (the live ledger, after the
# 2026-08-14..2026-09-18 backfill; research/…/MARKET_ONTOLOGY_F03_W2_4C_…md
# §"Coverage spans measured on the live ledger"): polygon_gex on 33 session
# dates 2026-06-22..2026-08-13, thetadata on 64 session dates 2026-06-22..
# 2026-09-21, first ThetaData-only session = 2026-08-14.  The capture
# fixture (mockups/evidence/…/EVIDENCE.yml) writes these exact dates to the
# rendered page so the crops and the research note table describe the same
# ledger picture.
_ROUND5_PAYLOAD = {
    "schema": "options_skew.v1",
    "source_break": True,
    "source_break_date": "2026-08-14",
    "history_dates": 64,
    "source_windows": [
        {"source": "polygon_gex", "first_date": "2026-06-22",
         "last_date": "2026-08-13", "n_dates": 33},
        {"source": "thetadata", "first_date": "2026-06-22",
         "last_date": "2026-09-21", "n_dates": 64},
    ],
}


def test_round5_payload_yields_the_exact_sentence():
    """Round-5 two-span payload produces the spec's exact EN/ZH sentences."""
    pair = skew_source_note(_ROUND5_PAYLOAD)
    assert pair is not None
    en, zh = pair
    expected_en = (
        "Put-skew history comes from two sources. The earlier Polygon feed "
        "covers 22 Jun 2026–13 Aug 2026 alongside ThetaData end-of-day "
        "option chains; from 14 Aug 2026 the history is ThetaData only. "
        "A skew change that crosses 14 Aug 2026 is not directly comparable."
    )
    expected_zh = (
        "认沽偏度历史来自两个来源：较早的 Polygon 数据覆盖"
        "2026年6月22日–2026年8月13日，与 ThetaData 日终期权链并行；"
        "自2026年8月14日起仅使用 ThetaData。跨越2026年8月14日的偏度变化不可直接比较。"
    )
    assert en == expected_en
    assert zh == expected_zh


def test_source_break_false_returns_none():
    """(b) source_break False → None, no sentence when there is no break."""
    payload = {"source_break": False, "source_break_date": _ROUND5_PAYLOAD["source_break_date"],
               "source_windows": _ROUND5_PAYLOAD["source_windows"]}
    assert skew_source_note(payload) is None
    # Even with multiple windows but a False break flag, stay silent.
    payload_no_break = {
        "source_break": False,
        "source_break_date": None,
        "source_windows": [
            {"source": "thetadata", "first_date": "2026-06-22", "last_date": "2026-06-23", "n_dates": 2},
        ],
    }
    assert skew_source_note(payload_no_break) is None


def test_one_source_present_returns_none():
    """A break flag with only one source in the windows is still silent —
    the sentence names two sources, not one.  This pins the gate that
    prevents fabricating a "second source" sentence on a single-source ledger."""
    payload = {
        "source_break": False,
        "source_break_date": None,
        "source_windows": [
            {"source": "thetadata", "first_date": "2026-06-22", "last_date": "2026-06-23", "n_dates": 2},
        ],
    }
    assert skew_source_note(payload) is None
    payload_break_only_theta = {
        "source_break": True,
        "source_break_date": "2026-08-14",
        "source_windows": [
            {"source": "thetadata", "first_date": "2026-06-22", "last_date": "2026-06-23", "n_dates": 2},
            {"source": "thetadata", "first_date": "2026-07-06", "last_date": "2026-07-07", "n_dates": 2},
        ],
    }
    assert skew_source_note(payload_break_only_theta) is None
    payload_break_only_poly = {
        "source_break": True,
        "source_break_date": "2026-08-14",
        "source_windows": [
            {"source": "polygon_gex", "first_date": "2026-06-22", "last_date": "2026-06-23", "n_dates": 2},
            {"source": "polygon_gex", "first_date": "2026-07-06", "last_date": "2026-07-07", "n_dates": 2},
        ],
    }
    assert skew_source_note(payload_break_only_poly) is None


def test_break_date_null_returns_none():
    """source_break True but source_break_date missing/null → None.

    The round-5 gate requires ALL of: source_break truthy, source_break_date
    a real YYYY-MM-DD, one polygon_gex span, one thetadata span.  Without the
    break date the consumer cannot name the boundary; stay silent."""
    payload = {
        "source_break": True,
        "source_break_date": None,
        "source_windows": _ROUND5_PAYLOAD["source_windows"],
    }
    assert skew_source_note(payload) is None
    payload_blank = {
        "source_break": True,
        "source_break_date": "",
        "source_windows": _ROUND5_PAYLOAD["source_windows"],
    }
    assert skew_source_note(payload_blank) is None


def test_load_skew_source_returns_none_when_file_absent(tmp_path):
    """(c) load_skew_source() returns None when site/options_skew/latest.json is absent."""
    # tmp_path is empty — no site/options_skew/latest.json — so the loader must
    # silently report None.
    assert load_skew_source(tmp_path) is None


def test_load_skew_source_reads_the_payload(tmp_path):
    """A written site/options_skew/latest.json is parsed verbatim."""
    site_dir = tmp_path / "site" / "options_skew"
    site_dir.mkdir(parents=True)
    (site_dir / "latest.json").write_text(json.dumps(_ROUND5_PAYLOAD))
    loaded = load_skew_source(tmp_path)
    assert loaded == _ROUND5_PAYLOAD


def test_render_with_note_emits_one_element(tmp_path):
    """(d) Rendering build_context + render with the note set emits exactly
    one `data-skew-source-note` element, and none when unset.

    The render needs templates/options.html.j2 + a working build_context()
    against the real REPO templates dir — that's where render()'s Jinja
    FileSystemLoader lives.  We render against REPO, not tmp_path, and pass
    the in-memory skew_source dict in (no site/options_skew/latest.json file
    is written or needed)."""
    from engine import i18n  # noqa: PLC0415
    html = render(REPO, stores=_stores(), skew_source=_ROUND5_PAYLOAD)
    occurrences = re.findall(r'data-skew-source-note', html)
    assert len(occurrences) == 1, (
        "the Directional read foot must emit exactly one skew-source-note element "
        "when the payload carries a real break"
    )
    assert "earlier Polygon feed covers 22 Jun 2026–13 Aug 2026" in html
    assert "from 14 Aug 2026 the history is ThetaData only" in html
    visible = re.sub(r'<[^>]+>', ' ', html)
    assert "polygon_gex" not in visible, (
        "the source slug polygon_gex must never reach the page"
    )
    assert "thetadata" not in visible, (
        "the source slug thetadata must never reach the page"
    )
    # Unset payload → no element.
    html_unset = render(REPO, stores=_stores(), skew_source=None)
    assert "data-skew-source-note" not in html_unset


def test_load_stores_source_text_is_byte_identical_to_origin_main():
    """(e) load_stores() in scripts/build_options_command.py is pinned
    BYTE-FOR-BYTE by tests/test_render_options_workspace_scope.py.  A
    keyword added to load_stores would break that probe.  This guard
    catches the regression here too, before the wider suite can see it."""
    boc_path = REPO / "scripts" / "build_options_command.py"
    text = boc_path.read_text(encoding="utf-8")
    head = "def load_stores(root: Path)"
    end = "\n\n\n"
    start = text.find(head)
    assert start >= 0, "load_stores() not found in build_options_command.py"
    body = text[start:].split("\n\n", 1)[0]
    # Additivity only: the new key never enters load_stores — the new artifact
    # has its OWN loader (load_skew_source, defined above).
    assert "options_skew" not in body, (
        "load_stores() must NOT read site/options_skew/latest.json — that "
        "artifact is loaded by load_skew_source() per the load_stores pin "
        "(tests/test_render_options_workspace_scope.py)."
    )
    # Pin against origin/main as a baseline.
    try:
        origin = subprocess.check_output(
            ["git", "show", "origin/main:scripts/build_options_command.py"],
            cwd=str(REPO), stderr=subprocess.STDOUT,
        ).decode("utf-8")
    except subprocess.CalledProcessError:
        pytest.skip("origin/main ref unavailable in this checkout")
    origin_start = origin.find(head)
    if origin_start < 0:
        pytest.skip("origin/main copy of build_options_command.py missing load_stores")
    origin_body = origin[origin_start:].split("\n\n", 1)[0]
    assert body == origin_body, (
        "load_stores()'s literal text diverged from origin/main.  The pin "
        "in tests/test_render_options_workspace_scope.py forbids new keys; "
        "add the new store via a SEPARATE loader (load_skew_source)."
    )
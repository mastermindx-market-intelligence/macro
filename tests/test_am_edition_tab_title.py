"""P12.T42: tab-title RCDATA over an unchanged retained published payload."""
from __future__ import annotations

import html
import json
from pathlib import Path
import re

from scripts.build_am_edition import render_html


def test_retained_edition_title_is_plain_text_with_exact_as_of():
    raw = (Path(__file__).parent / "fixtures/am_edition_title_snapshot_2e17ae66.json").read_bytes()
    payload = json.loads(raw)
    original = json.dumps(payload, sort_keys=True)
    rendered = render_html(payload)
    # HTML title is RCDATA: span syntax here is literal tab text, not bilingual DOM.
    title = re.search(r"<title>(.*?)</title>", rendered, re.S)
    assert title is not None
    text = html.unescape(title.group(1))
    assert "<" not in text and ">" not in text
    assert text == f"Morning Edition · 早间版 — {payload['generated_at']}"
    assert json.dumps(payload, sort_keys=True) == original

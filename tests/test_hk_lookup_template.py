"""Compile the full HK lookup body and preserve copy and shell-owner hooks."""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_NAME = "hk_lookup.html.j2"
GENERATED_UTC = "SOURCE_RENDER_QUALIFICATION"
STATE_DISPLAY_JSON = "{}"


def _render_body() -> str:
    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        autoescape=False,
    )
    template = env.get_template(TEMPLATE_NAME)
    return template.render(
        state_display_json=STATE_DISPLAY_JSON,
        generated_utc=GENERATED_UTC,
    )


def test_hk_lookup_template_compiles_and_renders() -> None:
    body = _render_body()
    # Visible English help literal — apostrophe must survive into the body.
    assert "company's own reporting currency" in body
    # Actual full-template output must carry the shell-owner hooks.
    assert "mmx:shell-location" in body
    assert "MMXSharedShell" in body

"""Render one technology economic-change dossier mapping to an HTML fragment.

Pure display. The caller supplies the dossier and the template path. This
module reads that template once, fetches nothing, writes nothing, and
consults no clock. It does not import the composer.
"""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import jinja2

__all__ = ["TEMPLATE_RELATIVE_PATH", "render_technology_dossier_page"]

#: The one fragment this renderer knows. A string literal so exclusive scope
#: records this file and not the templates tree.
TEMPLATE_RELATIVE_PATH = "templates/_technology_economic_change_page.html.j2"


def render_technology_dossier_page(
    dossier: Mapping[str, Any],
    template_path: str | Path = TEMPLATE_RELATIVE_PATH,
) -> str:
    """Return the company-first fragment for ``dossier``.

    ``template_path`` is the only file read. Values are printed from the
    mapping; this function does not fill a missing ticker or a refused view.
    """
    if not isinstance(dossier, Mapping):
        raise TypeError("dossier must be a mapping")
    source = Path(template_path).read_bytes()
    environment = jinja2.Environment(
        autoescape=True,
        undefined=jinja2.StrictUndefined,
    )
    template = environment.from_string(source.decode("utf-8"))
    return template.render(dossier=dossier)

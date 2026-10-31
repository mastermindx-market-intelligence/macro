#!/usr/bin/env python3
"""INTL-GS-W2B (IM14 dossier) evidence fixture: production, abstain-all and
specimen variants, all through the REAL lib.intl_gs_dossier_view module and
the REAL templates/intl_workspace/dossier.html.j2 template.

Imports the W2F foundation fixture (tests/intl_gs_fixture_site.py) and never
edits it; the foundation's --stub-coverage is never used for W2B evidence.

CLI:
    python3 tests/intl_gs_dossier_fixture.py --out <dir>
    python3 tests/intl_gs_dossier_fixture.py --print-html      (production variant)
    python3 tests/intl_gs_dossier_fixture.py --print-abstain   (abstain-all variant)
    python3 tests/intl_gs_dossier_fixture.py --print-specimen  (board-11 specimen)

The specimen payload is derived from a real build_view output (deep copy) and
then carries specimen=True plus the board-11 Brazil numbers; no production
code path can set the specimen flag (tests/test_intl_gs_dossier.py proves it).
"""
import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jinja2 import Environment  # noqa: E402

from tests.intl_gs_fixture_site import _env, _vm  # noqa: E402
from tests.test_intl_gs_foundation import (  # noqa: E402
    W2FX_EVALUATED, W2FX_GRANT, _w2fx_admitted)

EVALUATED_AT = W2FX_EVALUATED  # 2026-10-09T20:30:00+00:00 — the fixture's as-of instant


def production_observation_set(data_root):
    """The production variant over SYNTHETIC closes (the W2FX recipe): numbers
    reach the page only through the Wave 1 observation contract."""
    from lib.intl_gs_observations import build_observation_set
    selected, inputs = _w2fx_admitted(data_root)
    return build_observation_set(selected, publication_inputs=inputs,
                                 evaluated_at=W2FX_EVALUATED,
                                 data_root=data_root, rights=W2FX_GRANT)


def render_intl_page(observations):
    """The real intl.html via the render_fixture seam with an observation set."""
    from lib.intl_surveillance_mount import attach_surveillance
    from lib.intl_library_mount import render_international_pages
    vm = _vm()
    vm["intl_workspace"] = attach_surveillance(vm["intl_workspace"],
                                               observations=observations)
    catalogue = json.loads((ROOT / "config/intl_library_catalogue.json")
                           .read_text(encoding="utf-8"))
    pages = render_international_pages(_env().get_template("intl.html.j2"), vm,
                                       catalogue=catalogue)
    return pages[0]


def _specimen_panel():
    """Board-11 Brazil specimen panel: a deep copy of the real 1m /
    usd_unhedged dossier panel payload with specimen numbers substituted and
    specimen=True set — only this test fixture can do that."""
    import lib.intl_gs_dossier_view as dossier
    from engine import intl_global_universe as _universe
    from engine.intl_workspace_overview import build_workspace_overviews
    from lib.intl_macro_mount import _contexts
    from lib.intl_workspace_binding import binding_version

    universe = _universe.load_universe()
    rights = _universe.load_rights_matrix()
    workspace = build_workspace_overviews(None)
    version, generation = binding_version(workspace)
    contexts = _contexts(workspace["panels"], workspace["config"], version, generation)
    panels = dossier.build_view(universe=universe, rights=rights, contexts=contexts,
                                workspace=workspace, observations=None)
    panel = deepcopy(next(p for p in panels
                          if p["context"]["horizon"] == "1m"
                          and p["context"]["currency_basis"] == "usd_unhedged"))
    payload = panel["payload"]
    payload["specimen"] = True

    def _market(market_id):
        return next(m for m in payload["markets"] if m["id"] == market_id)

    # Board 11 hero: Brazil +3.4% USD · Unhedged.
    br = _market("BR")
    br["hero"] = {
        "qualified": True, "value_pct": 3.4,
        "clock": {"datetime": "2026-10-07T00:00:00",
                  "en": "7 Oct 00:00 UTC", "zh": "10月7日 00:00 UTC"},
        "reason_pairs": None, "reason_tokens": [],
    }
    # Decomposition verbatim from the contract shape: 1.2 + 2.2 + 0.0 = 3.4.
    br["decomposition"] = {
        "available": True,
        "local_pct": 1.2, "fx_pct": 2.26, "usd_pct": 3.4,
        "additive_fx_contribution_pp": 2.2, "interaction_pp": 0.0,
        "identity_residual": 0.0,
        "identity_en": ("Identity check: local +1.20% + FX contribution +2.20pp "
                        "+ interaction +0.00pp = USD +3.40% (residual 0.00pp)."),
        "identity_zh": ("恒等式：本币 +1.20% + 汇率贡献 +2.20pp + 交互项 +0.00pp "
                        "= 美元 +3.40%（残差 0.00pp）。"),
        "reason_pairs": None,
    }
    # Board-11 σ decomposition bars (specimen only; build_view never sets rows).
    br["sigma_rows"] = [
        {"label_en": "Local", "label_zh": "本币", "pct": 0.9},
        {"label_en": "FX", "label_zh": "汇率", "pct": 1.6},
        {"label_en": "Common", "label_zh": "共同", "pct": 0.4},
        {"label_en": "Residual", "label_zh": "残差", "pct": 0.5},
    ]
    # Board-11 typed edges (specimen only).
    br["typed_edges"] = [
        {"edge": "rates", "label_en": "Rates", "label_zh": "利率",
         "window": "20D", "state": "complete"},
        {"edge": "fx", "label_en": "FX", "label_zh": "汇率",
         "window": "20D", "state": "partial"},
        {"edge": "carry", "label_en": "Carry", "label_zh": "套息",
         "window": "20D", "state": "empty"},
        {"edge": "risk", "label_en": "Risk appetite", "label_zh": "风险偏好",
         "window": "20D", "state": "abstain"},
    ]
    # Specimen peers incl. Chile Qualified (dashed warn) and Peru Abstain
    # (dashed muted), per board 11 / E5.
    br["peers"] = [
        {"id": "CO", "name_en": "Colombia", "name_zh": "哥伦比亚", "state": "number",
         "qualified": True, "value_pct": 1.1,
         "clock": {"datetime": "2026-10-07T00:00:00",
                   "en": "7 Oct 00:00 UTC", "zh": "10月7日 00:00 UTC"}},
        {"id": "CL", "name_en": "Chile", "name_zh": "智利", "state": "qualified",
         "qualified": False, "value_pct": None, "clock": None},
        {"id": "PE", "name_en": "Peru", "name_zh": "秘鲁", "state": "abstain",
         "qualified": False, "value_pct": None, "clock": None,
         "reason_pairs": [("No admitted source", "无已准入数据源")],
         "reason_tokens": ["no_admitted_source"]},
        {"id": "MX", "name_en": "Mexico", "name_zh": "墨西哥", "state": "number",
         "qualified": True, "value_pct": -0.7,
         "clock": {"datetime": "2026-10-07T00:00:00",
                   "en": "7 Oct 00:00 UTC", "zh": "10月7日 00:00 UTC"}},
        {"id": "AR", "name_en": "Argentina", "name_zh": "阿根廷", "state": "number",
         "qualified": True, "value_pct": 2.3,
         "clock": {"datetime": "2026-10-07T00:00:00",
                   "en": "7 Oct 00:00 UTC", "zh": "10月7日 00:00 UTC"}},
    ]
    # E4: the corrected grammar lives in the specimen variant only.
    payload["corrections"] = [{
        "old": "+3.6%", "new": "+3.4%",
        "clock_en": "9 Oct 15:00 UTC", "clock_zh": "10月9日 15:00 UTC",
        "datetime": "2026-10-09T15:00:00+00:00",
    }]
    panel["context_id"] = "im-gs-dossier-specimen"
    return panel


def render_specimen_page():
    """The board-11 Brazil specimen page through the SAME dossier template."""
    template = _env().from_string(
        '<!DOCTYPE html>\n'
        '<html lang="en" data-theme="dark">\n'
        '<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<title>INTL-GS dossier specimen</title>\n'
        '<link rel="stylesheet" href="theme.css">\n'
        '<link rel="stylesheet" href="intl_workspace.css">\n'
        '<link rel="stylesheet" href="intl_workspace_surveillance.css">\n'
        '<script defer src="theme.js"></script>\n'
        '</head>\n'
        '<body>\n'
        '<div class="intl-gs">\n'
        "{% with gs_panel=panel %}{% include 'intl_workspace/dossier.html.j2' %}{% endwith %}\n"
        '</div>\n'
        '</body>\n'
        '</html>\n')
    return template.render(panel=_specimen_panel())


def write_site(out_dir, data_root):
    """The W2B evidence site: the foundation pages (no stub), then the
    production variant over intl.html, the abstain-all page and the specimen
    page. Returns the number of files written by this module."""
    import shutil
    from tests.intl_gs_fixture_site import write_site as foundation_write_site
    out = Path(out_dir)
    foundation_write_site(out)  # intl.html + intl-gs-states.html + assets (no stub)
    observations = production_observation_set(data_root)
    (out / "intl.html").write_text(render_intl_page(observations), encoding="utf-8")
    (out / "intl-abstain.html").write_text(render_intl_page(None), encoding="utf-8")
    (out / "intl-gs-dossier-specimen.html").write_text(render_specimen_page(),
                                                       encoding="utf-8")
    return 3


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", help="write the W2B evidence site (3 extra pages)")
    parser.add_argument("--data-root", default="/tmp/intl-gs-w2b-data",
                        help="scratch dir for the synthetic closes (default /tmp/intl-gs-w2b-data)")
    parser.add_argument("--print-html", action="store_true")
    parser.add_argument("--print-abstain", action="store_true")
    parser.add_argument("--print-specimen", action="store_true")
    args = parser.parse_args(argv)
    if args.print_html:
        root = Path(args.data_root); root.mkdir(parents=True, exist_ok=True)
        sys.stdout.write(render_intl_page(production_observation_set(root)))
    if args.print_abstain:
        sys.stdout.write(render_intl_page(None))
    if args.print_specimen:
        sys.stdout.write(render_specimen_page())
    if args.out:
        root = Path(args.data_root); root.mkdir(parents=True, exist_ok=True)
        written = write_site(args.out, root)
        print(f"wrote {args.out}/intl.html (production), intl-abstain.html, "
              f"intl-gs-dossier-specimen.html (+{written} pages)", file=sys.stderr)
    if not (args.out or args.print_html or args.print_abstain or args.print_specimen):
        parser.error("nothing to do: pass --out and/or --print-*")


if __name__ == "__main__":
    main()

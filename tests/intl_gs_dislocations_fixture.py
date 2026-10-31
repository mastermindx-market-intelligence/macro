#!/usr/bin/env python3
"""INTL-GS-W3U dislocation-explorer fixture site (test/evidence only).

Builds a REAL IM12 observation set for the seven legacy markets (JP KR TW IN
AU GB EZ — the only ids ``build_observation`` accepts) at one horizon the
workspace config declares, on both bases the builder reads, with real
``engine.intl_global_observation.build_observation`` outputs and real IM15
engine semantics. Nothing here is imported by lib/, scripts/ or templates/.

Scenarios (the §7 arithmetic of one five-market Asia-Pacific peer group makes
a Complete row and a Restricted row mutually exclusive — a rights-unconfirmed
market is excluded as ``not_qualified`` from every sibling receipt, which
makes those rows Qualified; recorded in the lane record):
- ``restricted`` (default): TW rights unconfirmed -> one Restricted row (TW),
  four Qualified rows (JP KR IN AU, reason ``not_qualified`` x1), two Abstain
  rows (GB EZ, ``insufficient_peers``: Europe carries only two markets).
- ``complete``: every market qualified -> five Complete rows + the two Abstain
  Europe rows.
- ``--withheld``: every observation abstains (incumbent withheld) -> every
  market abstains ``subject_not_qualified``; zero ranked rows.

JP is shifted so |modified z| > 7 (attention AND scatter/resbar clamp); the
rest sit inside the reference range.

Variants:
- ``production``: the real builder, no fragility (the honest production state).
- ``specimen``: sys.modules['lib.intl_gs_dislocations_view'] is temporarily
  replaced by a thin wrapper calling ``build_payload(..., fragility=...,
  specimen=True)`` — restored in a finally block; production code never sees
  the fixture. SPECIMEN_FRAGILITY covers >60 (JP 72), ==60 (KR 60), <60
  (IN 41) and a ranked market with no value (AU).

CLI:
    python3 tests/intl_gs_dislocations_fixture.py --variant specimen \
        --scenario restricted --out /tmp/w3u_site
    python3 tests/intl_gs_dislocations_fixture.py --print-html
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import types
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.intl_global_observation import build_observation  # noqa: E402
from engine.intl_global_universe import load_universe  # noqa: E402
from engine.intl_workspace_overview import build_workspace_overviews  # noqa: E402

BUILDER_MODULE = "lib.intl_gs_dislocations_view"

RIGHTS = {"decision_ref": "chairman:2026-10-09:user-facing-redistribution-confirmed",
          "scope": "intl-index-fx-eod-user-facing-v1"}
INCUMBENT = {"quality": "qualified", "reason": None,
             "decision_ref": "derived-evaluation:sha256:w3u"}
EVIDENCE = "saved-parquet:sha256:w3u-one|saved-parquet:sha256:w3u-two"
SOURCE_REFERENCE = "intl-supplied-close:sha256:w3u-fixture"

#: window endpoints (ISO dates) per horizon: one window ending 2026-10-07.
HORIZON_WINDOWS = {
    "1m": ("2026-09-07T00:00:00", "2026-10-07T00:00:00"),
    "3m": ("2026-07-07T00:00:00", "2026-10-07T00:00:00"),
    "6m": ("2026-04-07T00:00:00", "2026-10-07T00:00:00"),
    "12m": ("2025-10-07T00:00:00", "2026-10-07T00:00:00"),
    "ytd": ("2025-12-31T00:00:00", "2026-10-07T00:00:00"),
    "7m": ("2026-03-07T00:00:00", "2026-10-07T00:00:00"),
}

#: (local_pct, fx_pct) per market — JP is the |z| > 7 attention market.
RETURNS = {
    "JP": (7.5, 0.5),
    "KR": (-1.0, -0.2),
    "TW": (0.4, -0.1),
    "IN": (0.5, 0.3),
    "AU": (-0.2, -0.2),
    "GB": (0.9, 0.1),
    "EZ": (0.2, 0.0),
}
SCENARIO_RETURNS = {"complete": {"TW": (0.3, 0.0)}}

#: Specimen-only fragility values (fixture wrapper; never production).
SPECIMEN_FRAGILITY = {"JP": 72, "KR": 60, "IN": 41}


def _identity(market_id: str, horizon: str, basis: str) -> dict:
    window_start, window_end = HORIZON_WINDOWS[horizon]
    return {
        "universe_id": market_id,
        "market_id": market_id,
        "index_id": f"^W3U{market_id}",
        "fx_id": f"{market_id}W3U=X",
        "horizon": horizon,
        "currency_basis": basis,
        "return_basis": "price",
        "window_start": window_start,
        "window_end": window_end,
        "source_content_sha256": hashlib.sha256(
            f"w3u:{market_id}:{horizon}:{basis}".encode()).hexdigest(),
    }


def _clocks() -> dict:
    return {
        "observation": {"at": "2026-10-07T00:00:00", "precision": "session_date"},
        "source_publication": {"at": "2026-10-09T15:00:00+00:00", "precision": "exact"},
        "ingestion": {"at": "2026-10-09T15:00:00+00:00", "precision": "exact"},
        "computation": {"at": "2026-10-09T20:30:00+00:00", "precision": "exact"},
    }


def _observation(market_id: str, horizon: str, basis: str, *, local: float,
                 fx: float, rights_unconfirmed: bool = False,
                 incumbent_withheld: bool = False) -> dict:
    if basis == "local":
        values = {"local_pct": local}
    else:
        usd = (1.0 + local / 100.0) * (1.0 + fx / 100.0) * 100.0 - 100.0
        values = {"local_pct": local, "usd_pct": usd, "fx_pct": fx}
    return build_observation(
        identity=_identity(market_id, horizon, basis),
        clocks=_clocks(), values=values,
        rights=None if rights_unconfirmed else dict(RIGHTS),
        incumbent=({"quality": "withheld", "reason": "fixture withheld",
                    "decision_ref": "derived-evaluation:sha256:w3u-withheld"}
                   if incumbent_withheld else dict(INCUMBENT)),
        evidence_ref=EVIDENCE)


def build_set(scenario: str = "restricted", horizon: str = "1m",
              withheld: bool = False) -> dict:
    """A real IM12 observation set on both bases the builder reads."""
    returns = dict(RETURNS)
    returns.update(SCENARIO_RETURNS.get(scenario, {}))
    restricted = scenario == "restricted" and not withheld
    usd, local = [], []
    for market in ("AU", "EZ", "GB", "IN", "JP", "KR", "TW"):
        pair = returns[market]
        usd.append(_observation(
            market, horizon, "usd_unhedged", local=pair[0], fx=pair[1],
            rights_unconfirmed=restricted and market == "TW",
            incumbent_withheld=withheld))
        local.append(_observation(
            market, horizon, "local", local=pair[0], fx=pair[1],
            rights_unconfirmed=restricted and market == "TW",
            incumbent_withheld=withheld))
    return {
        "contract_version": "intl-global-observation-v1",
        "status": "withheld" if withheld else "admitted",
        "source_reference": SOURCE_REFERENCE,
        "bases": {"local": local, "usd_unhedged": usd},
    }


def universe() -> dict:
    return load_universe()


def workspace() -> dict:
    return build_workspace_overviews(None)


def market_name(market_id: str) -> str:
    holder = ((universe().get("jurisdictions") or {}).get(market_id)
              or (universe().get("aggregates") or {}).get(market_id) or {})
    return holder.get("name", market_id)


def _specimen_wrapper():
    import lib.intl_gs_dislocations_view as real_builder

    module = types.ModuleType(BUILDER_MODULE)
    module.__doc__ = "Test-only specimen wrapper (fixture, never committed use)."

    def build_view(*, universe, rights, contexts, workspace, observations=None):
        payload = real_builder.build_payload(
            universe=universe, workspace=workspace, observations=observations,
            fragility=SPECIMEN_FRAGILITY, specimen=True)
        if payload is None:
            return []
        context = {"horizon": payload["horizon"]}
        if "usd_unhedged" in ((workspace or {}).get("config") or {}).get("bases", []):
            context["currency_basis"] = "usd_unhedged"
        return [dict(view="dislocations", context_id="im-gs-dislocations",
                     context=context, payload=payload)]

    module.build_view = build_view
    return module


def render_page(variant: str = "production", scenario: str = "restricted",
                observations: dict | None = None) -> str:
    """The real intl.html with this fixture's observation set attached."""
    import importlib.util
    from jinja2 import Environment, FileSystemLoader

    from engine import i18n
    from lib.intl_library_mount import render_international_pages
    from lib.intl_surveillance_mount import attach_surveillance

    site = importlib.util.spec_from_file_location(
        "intl_gs_fixture_site", ROOT / "tests/intl_gs_fixture_site.py")
    fixture_site = importlib.util.module_from_spec(site)
    site.loader.exec_module(fixture_site)

    observation_set = observations if observations is not None else build_set(scenario)
    injected = False
    previous = sys.modules.get(BUILDER_MODULE)
    try:
        if variant == "specimen":
            sys.modules[BUILDER_MODULE] = _specimen_wrapper()
            injected = True
        vm = fixture_site._vm()
        vm["intl_workspace"] = attach_surveillance(vm["intl_workspace"],
                                                   observations=observation_set)
        catalogue = json.loads(
            (ROOT / "config/intl_library_catalogue.json").read_text(encoding="utf-8"))
        env = Environment(loader=FileSystemLoader(str(ROOT / "templates")),
                          autoescape=False)
        env.globals.update(t=i18n.t, tr=i18n.tr, td=i18n.td)
        pages = render_international_pages(env.get_template("intl.html.j2"), vm,
                                           catalogue=catalogue)
        return pages[0]
    finally:
        if injected:
            # restore whatever occupied the slot before the wrapper (a test's
            # patched instance must survive a specimen render), never leave the
            # wrapper installed
            if previous is None:
                sys.modules.pop(BUILDER_MODULE, None)
            else:
                sys.modules[BUILDER_MODULE] = previous


def write_site(out_dir: str, *, variant: str = "production",
               scenario: str = "restricted") -> int:
    """The W2 fixture site (assets + states page) with this view's page."""
    import importlib.util

    site = importlib.util.spec_from_file_location(
        "intl_gs_fixture_site_w3u", ROOT / "tests/intl_gs_fixture_site.py")
    fixture_site = importlib.util.module_from_spec(site)
    site.loader.exec_module(fixture_site)
    copied = fixture_site.write_site(out_dir)
    (Path(out_dir) / "intl.html").write_text(
        render_page(variant=variant, scenario=scenario), encoding="utf-8")
    return copied + 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--variant", choices=("production", "specimen"),
                        default="production")
    parser.add_argument("--scenario", choices=("restricted", "complete"),
                        default="restricted")
    parser.add_argument("--withheld", action="store_true",
                        help="every observation abstains (withheld set)")
    parser.add_argument("--out", help="write the fixture site to this directory")
    parser.add_argument("--print-html", action="store_true")
    parser.add_argument("--print-payload", action="store_true",
                        help="print the builder payload as JSON")
    args = parser.parse_args(argv)
    if args.print_html:
        observations = build_set(args.scenario, withheld=args.withheld)
        sys.stdout.write(render_page(variant=args.variant, scenario=args.scenario,
                                     observations=observations))
    if args.print_payload:
        import lib.intl_gs_dislocations_view as builder
        payload = builder.build_payload(
            universe=universe(), workspace=workspace(),
            observations=build_set(args.scenario, withheld=args.withheld),
            **({"fragility": SPECIMEN_FRAGILITY, "specimen": True}
               if args.variant == "specimen" else {}))
        sys.stdout.write(json.dumps(payload, indent=1, sort_keys=True,
                                    ensure_ascii=False))
    if args.out:
        copied = write_site(args.out, variant=args.variant, scenario=args.scenario)
        print(f"wrote {args.out}/intl.html ({copied} files)", file=sys.stderr)
    if not (args.out or args.print_html or args.print_payload):
        parser.error("nothing to do: pass --out, --print-html and/or --print-payload")


if __name__ == "__main__":
    main()

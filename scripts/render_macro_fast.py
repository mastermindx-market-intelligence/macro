"""DEV-ONLY fast re-render of macro.html / us_stocks.html from a cached view-model.

A full `python -m scripts.build_site` is ~4 minutes. While iterating on the
dashboard template / CSS, that loop is too slow. This re-renders all dashboards
from a pickled view-model without recomputing producers, reusing the production
build_site gates / splits / payload writer so that the protected entitlement
boundary is preserved exactly as the canonical full build ships it.

Usage:
    # once: produce the cache (a normal full build, but it also dumps the VM)
    MACRO_DUMP_VM=1 python -m scripts.build_site
    # then, after every template/theme.css edit:
    python -m scripts.render_macro_fast
    cp templates/theme.css site/theme.css   # if you edited theme.css

The template + theme.css are re-read from disk on every run, so edits show up
immediately. This is NOT on the daily/commit path — build_site remains the
source of truth; this only re-renders using its last cached data. The stocks
page in particular writes its protected JSON payload from the SAME cached
generation as the public page, so a template-only edit can never silently
overwrite public rows with protected ones.
"""
import pickle
import re as _re
import sys
from copy import deepcopy
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import config  # noqa: E402
from lib.pages import write_page  # noqa: E402


def _build_env(*, stocks: bool = False) -> Environment:
    """Preserve the original nonstock env; stocks uses the production globals."""
    env = Environment(loader=FileSystemLoader(config.ROOT / "templates"),
                      autoescape=stocks)
    env.filters["min"] = lambda seq: min(seq)
    env.filters["regex_replace"] = (
        lambda s, pattern, repl: _re.sub(pattern, repl, s)
        if isinstance(s, str) else s
    )
    from engine import i18n
    env.globals.update(td=i18n.td, tr=i18n.tr, zip=zip)
    if stocks:
        from scripts import build_site as _build
        from lib.seo import SITE_BASE
        from engine.macro_news import CHANNEL_LABEL
        env.globals.update(t_pctile=i18n.t_pctile, SITE_BASE=SITE_BASE,
                           CHANNEL_LABEL=CHANNEL_LABEL,
                           us_stance_projection=_build.us_stance_projection)
    return env


def _compose_stocks_mode(env: Environment, src_vm: dict, generated: str,
                         site: Path) -> None:
    """Stock-mode composition: same gate cfg / board_locked_rows / plan
    relations / episode joins / repair context / full protected tail as the
    canonical full build. We derive plan-relation fields in a deep copy
    of `src_vm`, preserving the full VM used by the other render modes.
    The cache file stays byte-identical. No fresh clock, no producer re-run, no second
    split algorithm — we reuse the exact same helpers build_site.py ships.
    """
    from scripts import build_site as _build

    vm = deepcopy(src_vm)

    _us_gate_cfg = _build._us_board_gate_cfg()
    _us_today_featured = _build._us_today_featured_preview(
        vm.get("us_standouts"), _us_gate_cfg["today_preview_rows"])
    _us_shell_su, _us_gate, _us_locked = _build._split_us_board(
        vm.get("us_standouts"), _us_gate_cfg["preview_rows"],
        gated=_us_gate_cfg["gated"])
    _us_life_shell, _us_life_gate, _us_life_locked = _build._split_us_prophet_board(
        vm.get("us_prophet_book"), _us_gate_cfg["preview_rows"],
        gated=_build._us_life_gate_cfg())
    _us_life_episodes = _build._us_prophet_episode_map(
        (vm.get("us_prophet_book") or {}).get("plans") or [])
    _us_life_repair = _build._us_life_repair_context(
        vm, _us_life_shell, _us_life_gate, _us_gate_cfg["preview_rows"])
    _us_pov, _us_pgate, _us_plocked = _build._split_us_panels(
        vm, _us_gate_cfg["panel_preview_rows"], gated=_us_gate_cfg["panels"],
        board_locked_rows=_us_locked)
    _us_plan_state, _us_plan_by_ticker = _build._plan_relations_for(
        vm.get("us_prophet_book"), vm.get("us_prophet_book_error"))
    vm["plan_rel_by_ticker"] = _us_plan_by_ticker
    vm["plan_rel"] = {"state": _us_plan_state, "plans": []}
    _build._write_us_payload(
        env, site, _us_gate, locked_rows=_us_locked,
        us_standouts=vm.get("us_standouts"),
        top_setups=vm.get("top_setups"),
        built=generated,
        today_rows=_us_today_featured,
        pgate=_us_pgate,
        panel_blocks=_build._render_us_panel_payload(
            env, _us_pgate, _us_plocked, vm,
            (_us_plan_state, _us_plan_by_ticker)),
        life_gate=_us_life_gate, locked_plans=_us_life_locked,
        cand_map=_us_life_repair["us_candidate_map"],
        trg_map={r.get("ticker"): r
                 for r in ((vm.get("top_setups") or {}).get("buy") or [])
                 if r.get("ticker")},
        episode_map=_us_life_episodes,
        plan_relations=(_us_plan_state, _us_plan_by_ticker))
    out_st = site / "us_stocks.html"
    write_page(out_st, env.get_template("dashboard.html.j2").render(
        **{**vm, **_us_pov, "us_standouts": _us_shell_su,
           "gate": _us_gate, "pgate": _us_pgate,
           "us_prophet_book": _us_life_shell, "life_gate": _us_life_gate,
           "us_prophet_episodes": _us_life_episodes,
           "us_prophet_book_error": vm.get("us_prophet_book_error"),
           **_us_life_repair}, mode="stocks"))


def main() -> int:
    site = config.ROOT / config.load()["storage"]["site_dir"]
    cache = config.data_dir() / "_dev_macro_vm.pkl"
    if not cache.exists():
        print(f"no VM cache at {cache}\n"
              f"run once: MACRO_DUMP_VM=1 python -m scripts.build_site",
              file=sys.stderr)
        return 1
    with open(cache, "rb") as fh:
        blob = pickle.load(fh)
    vm = blob["vm"]
    generated = blob.get("generated")  # SAME cached generation; no fresh clock

    env = _build_env()

    # Keep the original page order and nonstock environment unchanged.
    out = site / "macro.html"
    write_page(out, env.get_template("dashboard.html.j2").render(**vm, mode="macro"))
    print(f"wrote {out} ({out.stat().st_size/1024:.0f} KB)")

    # Use the same cached generation for the protected payload and public page.
    _compose_stocks_mode(_build_env(stocks=True), vm, generated, site)
    out = site / "us_stocks.html"
    print(f"wrote {out} ({out.stat().st_size/1024:.0f} KB)")

    out = site / "news.html"
    write_page(out, env.get_template("news.html.j2").render(**vm))
    print(f"wrote {out} ({out.stat().st_size/1024:.0f} KB)")
    out = site / "macro_signals.html"
    write_page(out, env.get_template("macro_signals.html.j2").render(**vm))
    print(f"wrote {out} ({out.stat().st_size/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

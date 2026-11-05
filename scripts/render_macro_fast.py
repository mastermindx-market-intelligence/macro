"""DEV-ONLY fast re-render of macro.html / us_stocks.html from a cached view-model.

A full `python -m scripts.build_site` is ~4 minutes. While iterating on the
dashboard template / CSS, that loop is too slow. This re-renders both dashboards
from a pickled view-model in well under a second.

Usage:
    # once: produce the cache (a normal full build, but it also dumps the VM)
    MACRO_DUMP_VM=1 python -m scripts.build_site
    # then, after every template/theme.css edit:
    python -m scripts.render_macro_fast
    cp templates/theme.css site/theme.css   # if you edited theme.css

The template + theme.css are re-read from disk on every run, so edits show up
immediately. This is NOT on the daily/commit path — build_site remains the source
of truth; this only re-renders using its last cached data.
"""
import pickle
import re
import subprocess
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import i18n  # noqa: E402
from engine.i18n import td as _td  # noqa: E402
from engine.i18n import tr as _tr  # noqa: E402
from engine.macro_news import CHANNEL_LABEL  # noqa: E402
from engine.prophet_opportunity_presentation import present_us_candidate  # noqa: E402
from lib import config  # noqa: E402
from lib.pages import write_page  # noqa: E402
from lib.seo import SITE_BASE  # noqa: E402
from scripts.build_site import us_stance_projection  # noqa: E402


_TODAY_BINDING_ATTRS = (
    "data-today-total", "data-today-visible", "data-today-source-sha256",
    "data-today-pair-id", "data-today-selection-receipt", "data-today-served",
)


def _today_source_binding(html: str) -> tuple[tuple[str, str], ...] | None:
    """The actual published source/entitlement partition, never visual copy."""
    section = re.search(r'<section\b[^>]*\bid="us-today"[^>]*>', html)
    if section is None:
        return None
    attrs = []
    for key in _TODAY_BINDING_ATTRS:
        match = re.search(r'\s' + re.escape(key) + r'="([^"]*)"', section.group())
        if match is None:
            return None
        attrs.append((key, match.group(1)))
    return tuple(attrs)


def _tracked_today_binding(repo_root: Path) -> tuple[tuple[str, str], ...] | None:
    """Read Git's committed carrier; a dirty working output is not authority."""
    try:
        result = subprocess.run(
            ["git", "show", "HEAD:site/us_stocks.html"], cwd=repo_root,
            capture_output=True, check=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return _today_source_binding(result.stdout.decode("utf-8", "replace"))


def main() -> int:
    site = config.ROOT / config.load()["storage"]["site_dir"]
    cache = config.data_dir() / "_dev_macro_vm.pkl"
    if not cache.exists():
        print(f"no VM cache at {cache}\n"
              f"run once: MACRO_DUMP_VM=1 python -m scripts.build_site", file=sys.stderr)
        return 1
    with open(cache, "rb") as fh:
        blob = pickle.load(fh)
    vm = blob["vm"]

    env = Environment(loader=FileSystemLoader(config.ROOT / "templates"))
    env.filters["min"] = lambda seq: min(seq)
    # Mirror the production build_site.py filter: templates use
    # `|regex_replace(...)` for the one-integer-law strip.
    import re as _re
    env.filters["regex_replace"] = (
        lambda s, pattern, repl: _re.sub(pattern, repl, s)
        if isinstance(s, str) else s
    )
    # Keep this DEV renderer on the build_site.py template contract. These
    # functions are imported from their canonical owners, never reimplemented.
    env.globals.update(
        td=i18n.td, tr=i18n.tr, t_pctile=i18n.t_pctile, zip=zip,
        SITE_BASE=SITE_BASE, CHANNEL_LABEL=CHANNEL_LABEL,
        us_stance_projection=us_stance_projection,
        present_us_candidate=present_us_candidate,
    )
    tmpl = env.get_template("dashboard.html.j2")

    # Compute every page before writes. A cached VM can contain an entitled
    # roster even when the Git carrier is public-only. Never overwrite ANY
    # public page when the source partition/pins do not match committed state.
    pages = {
        "macro.html": tmpl.render(**vm, mode="macro"),
        "us_stocks.html": tmpl.render(**vm, mode="stocks"),
        "news.html": env.get_template("news.html.j2").render(**vm),
        "macro_signals.html": env.get_template("macro_signals.html.j2").render(**vm),
    }
    tracked = _tracked_today_binding(config.ROOT)
    candidate = _today_source_binding(pages["us_stocks.html"])
    if tracked is None or candidate is None or tracked != candidate:
        old = dict(tracked or ())
        new = dict(candidate or ())
        drift = [key for key in _TODAY_BINDING_ATTRS if old.get(key) != new.get(key)]
        print(
            "REFUSED_STALE_PROPHET_VM: cached source/entitlement binding "
            "differs from committed site/us_stocks.html; no output written. "
            f"changed_fields={drift} "
            f"committed_visible={old.get('data-today-visible')} "
            f"candidate_visible={new.get('data-today-visible')}",
            file=sys.stderr,
        )
        return 2
    for name, content in pages.items():
        out = site / name
        write_page(out, content)
        print(f"wrote {out} ({out.stat().st_size/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

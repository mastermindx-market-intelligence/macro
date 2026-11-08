"""Scratch render of the China Sector Central page for the wave's visual evidence.

Renders templates/sector_central_china.html.j2 the way
scripts/build_china_sector_central.py renders it (same Jinja environment, same
three reader contexts, same injection), into an output directory outside the
tree. Every input is a HEAD blob. Nothing is computed: the builder's main() also
runs compute(), the central log and the grader, so it is never called here.

lib.config.data_dir, lib.config.site_dir and lib.store._path point at
nonexistent paths before any engine import, so a stray read fails loudly and
is counted in the written map.

Usage: python3 render_cn.py <out_dir>
Outputs: <out_dir>/sector_central_china.html, the two shared-shell assets the
injection versions against, and <out_dir>/_cn_written.json.
"""
import sys

sys.dont_write_bytecode = True

import hashlib  # noqa: E402
import json  # noqa: E402
import subprocess  # noqa: E402
import traceback  # noqa: E402
from collections import Counter  # noqa: E402
from pathlib import Path  # noqa: E402

EV = Path(__file__).resolve().parent
WT = EV.parents[2]
EV_REL = "mockups/evidence/"
GENERATED_UTC = "2026-11-05 12:00 UTC"
sys.path.insert(0, str(WT))


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def git(*a: str, binary: bool = False):
    r = subprocess.run(["git", "-C", str(WT), *a], capture_output=True, check=True)
    return r.stdout if binary else r.stdout.decode()


def blob(rel: str) -> bytes:
    return git("cat-file", "blob", f"HEAD:{rel}", binary=True)


def guard(stage: str) -> dict:
    lines = git("status", "--porcelain", "-uall").splitlines()
    bad = [ln for ln in lines if not ln[3:].strip('"').startswith(EV_REL)]
    if bad:
        raise SystemExit(f"guard[{stage}]: worktree change outside {EV_REL}: {bad[:5]}")
    for d in ("data", "site"):
        if (WT / d).exists():
            raise SystemExit(f"guard[{stage}]: WT/{d} exists")
    return {"stage": stage, "outside_ev": 0, "wt_data": False, "wt_site": False}


# ---- fences: installed before any engine import ------------------------------------
from lib import config, store  # noqa: E402

FENCES: Counter = Counter()


def _caller() -> str:
    fr = traceback.extract_stack()[-3]
    try:
        f = str(Path(fr.filename).resolve().relative_to(WT))
    except ValueError:
        f = Path(fr.filename).name
    return f"{f}:{fr.lineno}:{fr.name}"


def _fence_data_dir():
    FENCES[("config.data_dir", _caller(), "")] += 1
    return Path("/nonexistent-cn-data-fence")


def _fence_site_dir():
    FENCES[("config.site_dir", _caller(), "")] += 1
    return Path("/nonexistent-cn-site-fence")


def _fence_store_path(group: str, name: str):
    FENCES[("store._path", _caller(), f"{group}/{name}")] += 1
    return Path("/nonexistent-cn-store-fence") / group / f"{name}.parquet"


config.data_dir = _fence_data_dir
config.site_dir = _fence_site_dir
store._path = _fence_store_path

WRITTEN: dict[str, dict] = {}
OUT: Path


def put(rel: str, data: bytes, source: str, transform: str = "copy") -> None:
    if rel in WRITTEN:
        if WRITTEN[rel]["sha256"] != sha(data):
            raise SystemExit(f"non-identical overwrite in one run: {rel}")
        return
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    WRITTEN[rel] = {"sha256": sha(data), "bytes": len(data), "source": source, "transform": transform}


def put_head(rel: str) -> None:
    put(rel, blob(f"site/{rel}"), f"HEAD:site/{rel}")


def write_page_cn(rel: str, html: str, prefix: str) -> None:
    from lib.pages import inject_text
    from lib.shared_shell import inject_shared_shell_text
    v = sha((OUT / "shared_shell_bridge.js").read_bytes())[:8]
    cv = sha((OUT / "shared_shell.css").read_bytes())[:8]
    r = inject_text(html, prefix)
    r = inject_shared_shell_text(r, prefix, site_dir=OUT, response_kind="content", version=v, css_version=cv)
    put(rel, r.encode("utf-8"), "render", "jinja+inject_text+inject_shared_shell_text")


def contexts() -> tuple[dict, dict]:
    """The builder's three reader contexts, derived exactly as it derives them."""
    reads = {}

    def j(rel: str):
        b = blob(f"site/{rel}")
        reads[f"HEAD:site/{rel}"] = {"sha256": sha(b), "bytes": len(b)}
        return json.loads(b)

    theme_context = j("basketdata/theme_context_cn.json")
    sleeve_stats = None
    _sd = j("factordata/cn_reversal_sleeve.json")
    _sf = (_sd.get("sizing") or {}).get("sleeve_factor")
    _nm = _sd.get("n_members")
    if _sf is not None and _nm is not None:
        sleeve_stats = {"n_members": int(_nm), "sleeve_factor": float(_sf)}
        _full = ((_sd.get("rederive_stats") or {}).get("primary") or {}).get("full") or {}
        if _full.get("sharpe") is not None:
            sleeve_stats["sharpe"] = float(_full["sharpe"])
        if _full.get("n") is not None:
            sleeve_stats["n_rebalances"] = int(_full["n"])
    _an = j("chinabasketdata/act_now_cn.json")
    ctx = {
        "theme_context": theme_context,
        "sleeve_stats": sleeve_stats,
        "act_now_v2": _an.get("act_now_v2"),
        "sectors_by_ticker": _an.get("sectors_by_ticker") or {},
        "generated_utc": GENERATED_UTC,
    }
    return ctx, reads


def main() -> int:
    global OUT
    if len(sys.argv) != 2:
        raise SystemExit("usage: render_cn.py <out_dir>")
    OUT = Path(sys.argv[1]).resolve()
    if OUT == WT or WT in OUT.parents:
        raise SystemExit("out_dir must be outside the worktree")
    guards = [guard("before")]
    put_head("shared_shell_bridge.js")
    put_head("shared_shell.css")
    from jinja2 import Environment, FileSystemLoader
    from engine import i18n
    env = Environment(loader=FileSystemLoader(str(WT / "templates")), autoescape=True)
    env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    ctx, reads = contexts()
    html = env.get_template("sector_central_china.html.j2").render(**ctx)
    write_page_cn("sector_central_china.html", html, "")
    guards.append(guard("after"))
    fences = [{"fn": fn, "caller": c, "arg": a, "n": n} for (fn, c, a), n in sorted(FENCES.items())]
    out = {
        "head": git("rev-parse", "HEAD").strip(),
        "template_sha256": sha(blob("templates/sector_central_china.html.j2")),
        "generated_utc": GENERATED_UTC,
        "reads": reads,
        "written": WRITTEN,
        "fences": fences,
        "guards": guards,
        "sleeve_stats_keys": sorted((ctx["sleeve_stats"] or {}).keys()),
        "act_now_v2_present": ctx["act_now_v2"] is not None,
        "n_sectors_by_ticker": len(ctx["sectors_by_ticker"]),
    }
    (OUT / "_cn_written.json").write_text(json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("head", "sleeve_stats_keys", "act_now_v2_present",
                                          "n_sectors_by_ticker", "fences")}, indent=1))
    print({k: v["bytes"] for k, v in WRITTEN.items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

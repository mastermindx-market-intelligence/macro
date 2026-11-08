#!/usr/bin/env python3
"""L6.4 evidence renderer for the Sector Cycles wave (#7646).

Renders the four Cycles views from this worktree's HEAD templates and the
committed HEAD site payloads into an OUT directory outside the worktree:

  V1 sector_central.html      V2 sector_cycles.html
  V3 sectors/XLK.html         V4 sector_cycles_china.html

Every cycles entity is labelled FIXTURE before it is written. The renderer
never writes WT/site or WT/data, never calls a builder main(), a store
writer, a forward log or a live collector, and fences config.data_dir,
config.site_dir and store._path onto nonexistent paths so any read through
them is recorded and any write through them fails. Price history for V3 is
read read-only from the render tree given by --rt.

Outputs: OUT/** (served by serve_l6.py), OUT/_l6_written.json, and
EV/fixtures/FIXTURES.json plus the small variant fixtures.
"""
import sys

sys.dont_write_bytecode = True

import argparse  # noqa: E402
import copy  # noqa: E402
import hashlib  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
import subprocess  # noqa: E402
import traceback  # noqa: E402
from collections import Counter  # noqa: E402
from pathlib import Path  # noqa: E402

EV = Path(__file__).resolve().parent
WT = EV.parents[2]
EV_REL = "mockups/evidence/sector-cycles-20261105/"
FONT_PIN_REL = "mockups/evidence/prophet-p0b-zero-fouc/inputs/browser-data/p0b-font-pin"
sys.path.insert(0, str(WT))

DEVS: list[str] = []
GAPS: list[str] = []
CHECKS: dict[str, object] = {}
VARIANTS: dict[str, dict] = {}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def git(*a: str, binary: bool = False):
    r = subprocess.run(["git", "-C", str(WT), *a], capture_output=True, check=True)
    return r.stdout if binary else r.stdout.decode()


def blob(rel: str) -> bytes:
    return git("cat-file", "blob", f"HEAD:{rel}", binary=True)


def blob_exists(rel: str) -> bool:
    return subprocess.run(["git", "-C", str(WT), "cat-file", "-e", f"HEAD:{rel}"],
                          capture_output=True).returncode == 0


def guard(stage: str) -> dict:
    lines = git("status", "--porcelain", "-uall").splitlines()
    bad = [ln for ln in lines if not ln[3:].strip('"').startswith(EV_REL)]
    if bad:
        raise SystemExit(f"guard[{stage}]: worktree change outside {EV_REL}: {bad[:5]}")
    for d in ("data", "site"):
        if (WT / d).exists():
            raise SystemExit(f"guard[{stage}]: WT/{d} exists")
    return {"stage": stage, "outside_ev": 0, "wt_data": False, "wt_site": False}


# ---- fences: installed before any engine/scripts import --------------------------
from lib import config, store  # noqa: E402

FENCES: Counter = Counter()
_FENCE_DATA = Path("/nonexistent-l6-data-fence")
_FENCE_SITE = Path("/nonexistent-l6-site-fence")
_FENCE_STORE = Path("/nonexistent-l6-store-fence")


def _safe(name: str) -> str:
    return name.replace("^", "_").replace("=", "_").replace("/", "_").replace(" ", "_")


def _caller() -> str:
    fr = traceback.extract_stack()[-3]
    try:
        f = str(Path(fr.filename).resolve().relative_to(WT))
    except ValueError:
        f = Path(fr.filename).name
    return f"{f}:{fr.lineno}:{fr.name}"


def _fence_data_dir():
    FENCES[("config.data_dir", _caller(), "")] += 1
    return _FENCE_DATA


def _fence_site_dir():
    FENCES[("config.site_dir", _caller(), "")] += 1
    return _FENCE_SITE


def _fence_store_path(group: str, name: str):
    FENCES[("store._path", _caller(), f"{group}/{name}")] += 1
    return _FENCE_STORE / group / f"{_safe(name)}.parquet"


config.data_dir = _fence_data_dir
config.site_dir = _fence_site_dir
store._path = _fence_store_path

import pandas as pd  # noqa: E402

# ---- read-only render-tree reads ---------------------------------------------------
RT: Path = Path("/nonexistent")
READS: dict[str, dict] = {}


def _record_read(key: str, b: bytes | None) -> None:
    if b is None:
        READS.setdefault(key, {"status": "absent"})
    else:
        READS.setdefault(key, {"status": "ok", "sha256": sha(b), "bytes": len(b)})


def rt_read(group: str, name: str):
    p = RT / "data" / group / f"{_safe(name)}.parquet"
    key = f"data/{group}/{_safe(name)}.parquet"
    if not p.exists():
        _record_read(key, None)
        return None
    b = p.read_bytes()
    _record_read(key, b)
    df = pd.read_parquet(io.BytesIO(b))
    df.index = pd.to_datetime(df.index)
    return df.sort_index()


def latest_top10_rt(fund: str):          # collectors.sector_holdings.latest_top10 over rt_read
    df = rt_read("sector_holdings", fund)
    if df is None or df.empty:
        return None
    return df.loc[[df.index.max()]].sort_values("rank")


_SNAP: dict = {}


def latest_fundamentals_rt(ticker: str) -> dict:  # ...latest_fundamentals over rt_read
    if "df" not in _SNAP:
        _SNAP["df"] = rt_read("stock_fundamentals", "snapshots")
    df = _SNAP["df"]
    if df is None or df.empty:
        return {}
    row = df.iloc[-1]
    out = {}
    for col, v in row.items():
        t, _, f = str(col).partition("__")
        if t == ticker and pd.notna(v):
            out[f] = v
    return out


# ---- writes into OUT -----------------------------------------------------------------
OUT: Path = Path("/nonexistent")
WRITTEN: dict[str, dict] = {}


def put(rel: str, data: bytes, source: str, transform: str = "copy") -> None:
    if rel in WRITTEN:
        if WRITTEN[rel]["sha256"] != sha(data):
            raise SystemExit(f"non-identical overwrite in one run: {rel}")
        return
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    WRITTEN[rel] = {"sha256": sha(data), "bytes": len(data), "source": source, "transform": transform}


def put_head(rel: str, dest: str | None = None) -> None:
    put(dest or rel, blob(f"site/{rel}"), f"HEAD:site/{rel}")


def put_head_opt(rel: str) -> bool:
    if blob_exists(f"site/{rel}"):
        put_head(rel)
        return True
    GAPS.append(f"HEAD:site/{rel} absent; not written")
    return False


def put_tpl(name: str) -> None:
    put(name, blob(f"templates/{name}"), f"HEAD:templates/{name}")


def js_payload(prefix: str, obj, *, ensure_ascii: bool) -> bytes:
    return (prefix + json.dumps(obj, separators=(",", ":"), ensure_ascii=ensure_ascii) + ";\n").encode("utf-8")


def parse_js_payload(b: bytes, prefix: str):
    s = b.decode("utf-8")
    if not (s.startswith(prefix) and s.endswith(";\n")):
        raise SystemExit(f"unexpected payload framing for {prefix}")
    return json.loads(s[len(prefix):-2])


def same(name: str, mine: bytes, head: bytes) -> str:
    if mine == head:
        verdict = "byte-equal"
    else:
        try:
            a = json.loads(mine.decode().split("=", 1)[1].rstrip(";\n")) if mine[:7] == b"window." else json.loads(mine)
            h = json.loads(head.decode().split("=", 1)[1].rstrip(";\n")) if head[:7] == b"window." else json.loads(head)
        except ValueError:
            raise SystemExit(f"self-check {name}: not byte-equal and not parseable")
        if a != h:
            raise SystemExit(f"self-check {name}: re-derivation differs from HEAD")
        verdict = "json-equal"
    CHECKS[f"rederive:{name}"] = verdict
    return verdict


# ---- page writes (lib.pages.write_page without its site-root side effects) -----------
def write_page_l6(rel: str, html: str, prefix: str) -> None:
    from lib.pages import inject_text
    from lib.shared_shell import inject_shared_shell_text
    v = sha((OUT / "shared_shell_bridge.js").read_bytes())[:8]
    cv = sha((OUT / "shared_shell.css").read_bytes())[:8]
    r = inject_text(html, prefix)
    r = inject_shared_shell_text(r, prefix, site_dir=OUT, response_kind="content", version=v, css_version=cv)
    put(rel, r.encode("utf-8"), "render", "jinja+inject_text+inject_shared_shell_text")


def label_fixture(d: dict, family_keys) -> tuple[dict, dict]:
    lab = copy.deepcopy(d)
    counts = {}
    for fam in family_keys:
        ents = lab.get(fam)
        if not isinstance(ents, list):
            continue
        n = 0
        for e in ents:
            if isinstance(e, dict) and "id" in e:
                if "label" in e:
                    raise SystemExit(f"entity already carries a label: {fam}/{e.get('id')}")
                e["label"] = "FIXTURE"
                n += 1
        counts[fam] = n
    return lab, counts


def split_with_extras(data: dict, head_core: dict):
    from scripts._cycles_payload import split_cycles_payload
    core, series = split_cycles_payload(data)
    extras = [k for k in head_core if k not in core]
    for k in extras:
        core[k] = head_core[k]
    return core, series, extras


def main() -> int:
    global OUT, RT
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--rt", required=True)
    ap.add_argument("--generated", default="2026-11-05 00:00")
    args = ap.parse_args()
    OUT = Path(args.out).resolve()
    RT = Path(args.rt).resolve()
    for p, what in ((OUT, "--out"), (RT, "--rt")):
        try:
            p.relative_to(WT)
            raise SystemExit(f"{what} must resolve outside the worktree: {p}")
        except ValueError:
            pass
    head = git("rev-parse", "HEAD").strip()
    guards = [guard("before")]
    OUT.mkdir(parents=True, exist_ok=True)

    # shell assets first: write_page_l6 hashes the OUT copies for the ?v= stamps
    put_tpl("shared_shell_bridge.js")
    put_tpl("shared_shell.css")
    put_head_opt("data_base.js")

    # fonts: the pin's site faces, verified against font-pin.json; the pin dir itself
    pin_dir = WT / FONT_PIN_REL
    pin = json.loads((pin_dir / "font-pin.json").read_text(encoding="utf-8"))
    for rel, want in sorted(pin["site_faces"].items()):
        b = (RT / "site" / rel).read_bytes()
        if sha(b) != want:
            raise SystemExit(f"font digest mismatch: {rel}")
        put(rel, b, f"RT:site/{rel}", "copy (font-pin site_faces digest verified)")
    for f in sorted((RT / "site" / "fonts").iterdir()):
        rel = f"fonts/{f.name}"
        if rel not in WRITTEN and f.is_file():
            put(rel, f.read_bytes(), f"RT:site/{rel}", "copy (not in font-pin site_faces)")
    for name, want in sorted(pin["files"].items()):
        b = (pin_dir / name).read_bytes()
        if sha(b) != want:
            raise SystemExit(f"font-pin digest mismatch: {name}")
        put(f"p0b-font-pin/{name}", b, f"WT:{FONT_PIN_REL}/{name}", "copy (font-pin files digest verified)")
    put("p0b-font-pin/font-pin.json", (pin_dir / "font-pin.json").read_bytes(), f"WT:{FONT_PIN_REL}/font-pin.json")
    CHECKS["font_pin"] = {"schema": pin.get("schema"), "files": len(pin["files"]), "site_faces": len(pin["site_faces"])}

    from scripts._cycles_payload import FAMILY_KEYS, split_cycles_payload
    from jinja2 import Environment, FileSystemLoader
    from engine import i18n

    def cycles_env():
        env = Environment(loader=FileSystemLoader(str(WT / "templates")), autoescape=False)
        env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
        return env

    # ---- US cycles payloads --------------------------------------------------------
    P_CORE, P_SER = "window.SECTOR_CYCLES=", "window.SECTOR_CYCLES_SERIES="
    us = json.loads(blob("site/sectordata/sector_cycles.json"))
    head_core_b = blob("site/sector_cycles_data.js")
    head_ser_b = blob("site/sector_cycles_series_data.js")
    head_core = parse_js_payload(head_core_b, P_CORE)
    core, series, extras = split_with_extras(us, head_core)
    CHECKS["us_core_extra_keys_from_head"] = extras
    same("sector_cycles_data.js", js_payload(P_CORE, core, ensure_ascii=True), head_core_b)
    same("sector_cycles_series_data.js", js_payload(P_SER, series, ensure_ascii=True), head_ser_b)
    same("sectordata/sector_cycles.json",
         json.dumps(us, separators=(",", ":")).encode("utf-8"), blob("site/sectordata/sector_cycles.json"))
    us_lab, us_counts = label_fixture(us, FAMILY_KEYS)
    CHECKS["us_labelled"] = us_counts
    core_l, series_l, _ = split_with_extras(us_lab, head_core)
    for fam in FAMILY_KEYS:
        for e in core_l.get(fam) or []:
            if isinstance(e, dict) and "id" in e and e.get("label") != "FIXTURE":
                raise SystemExit(f"label lost in split: {fam}/{e['id']}")
    put("sector_cycles_data.js", js_payload(P_CORE, core_l, ensure_ascii=True), "HEAD:site/sectordata/sector_cycles.json",
        "label=FIXTURE on every entity; split_cycles_payload; HEAD core extras appended " + ",".join(extras))
    put("sector_cycles_series_data.js", js_payload(P_SER, series_l, ensure_ascii=True),
        "HEAD:site/sectordata/sector_cycles.json", "label=FIXTURE; split_cycles_payload (series half)")
    put("sectordata/sector_cycles.json", json.dumps(us_lab, separators=(",", ":")).encode("utf-8"),
        "HEAD:site/sectordata/sector_cycles.json", "label=FIXTURE on every entity")
    put_head("sector_cycles_narr_data.js")
    put_head("sector_cycles_dna_data.js")

    # ---- China cycles payloads -----------------------------------------------------
    cn = json.loads(blob("site/chinasectordata/sector_cycles.json"))
    cn_core_b = blob("site/sector_cycles_china_data.js")
    cn_ser_b = blob("site/sector_cycles_china_series_data.js")
    cn_head_core = parse_js_payload(cn_core_b, P_CORE)
    c_core, c_series, c_extras = split_with_extras(cn, cn_head_core)
    CHECKS["cn_core_extra_keys_from_head"] = c_extras
    same("sector_cycles_china_data.js", js_payload(P_CORE, c_core, ensure_ascii=False), cn_core_b)
    same("sector_cycles_china_series_data.js", js_payload(P_SER, c_series, ensure_ascii=False), cn_ser_b)
    cn_lab, cn_counts = label_fixture(cn, FAMILY_KEYS)
    CHECKS["cn_labelled"] = cn_counts
    # HEAD's China payload predates L6.5o (8ada88c9), which made the China producer stamp
    # rs_21d_rank. Re-stamp each family with that producer's own stamper, as compute() does
    # (sectors and baskets ranked apart), so the leadership list sorts on the lens it shows.
    # The payload carries rs_63d rounded to 0.1, so two records the producer ordered on full
    # precision can tie here. The 63d rank it re-derives must equal HEAD's except inside such
    # a tie, and the tied records must hold the same rank set. HEAD's rs_rank is then kept.
    from engine.sector_cycles import _stamp_rs_ranks
    cn_restamp, cn_tie_swaps, cn_21d_ties = {}, {}, {}
    for fam in ("sectors", "baskets"):
        recs = cn_lab.get(fam) or []
        before = [(r.get("now") or {}).get("rs_rank") for r in recs]
        _stamp_rs_ranks(recs)
        groups = {}
        for r, b in zip(recs, before):
            groups.setdefault(r["now"].get("rs_63d"), []).append((b, r["now"].get("rs_rank")))
        swaps = 0
        for v, pairs in groups.items():
            if sorted(b for b, _ in pairs) != sorted(a for _, a in pairs) or (len(pairs) == 1 and pairs[0][0] != pairs[0][1]):
                raise SystemExit(f"rs_rank re-derivation differs from HEAD outside a rounded tie: {fam} rs_63d={v}")
            swaps += sum(1 for b, a in pairs if b != a)
        for r, b in zip(recs, before):
            r["now"]["rs_rank"] = b
        cn_tie_swaps[fam] = swaps
        v21 = [r["now"].get("rs_21d") for r in recs if r["now"].get("rs_21d") is not None]
        cn_21d_ties[fam] = sum(1 for v in set(v21) if v21.count(v) > 1)
        cn_restamp[fam] = sum(1 for r in recs if r["now"].get("rs_21d_rank") is not None)
    CHECKS["cn_rs_21d_rank_restamped"] = cn_restamp
    CHECKS["cn_rs_rank_rounded_tie_swaps_kept_head"] = cn_tie_swaps
    CHECKS["cn_rs_21d_rounded_tie_values"] = cn_21d_ties
    cl_core, cl_series, _ = split_with_extras(cn_lab, cn_head_core)
    put("sector_cycles_china_data.js", js_payload(P_CORE, cl_core, ensure_ascii=False),
        "HEAD:site/chinasectordata/sector_cycles.json", "label=FIXTURE; rs_21d_rank re-stamped (L6.5o stamper); split_cycles_payload")
    put("sector_cycles_china_series_data.js", js_payload(P_SER, cl_series, ensure_ascii=False),
        "HEAD:site/chinasectordata/sector_cycles.json", "label=FIXTURE; split_cycles_payload (series half)")
    put("chinasectordata/sector_cycles.json",
        json.dumps(cn_lab, separators=(",", ":"), ensure_ascii=False).encode("utf-8"),
        "HEAD:site/chinasectordata/sector_cycles.json", "label=FIXTURE on every entity; rs_21d_rank re-stamped (L6.5o stamper)")
    from scripts.build_china_sector_cycles import _basket_cycle_map
    head_map_b = blob("site/chinasectordata/sector_cycles_basket_map.json")
    same("chinasectordata/sector_cycles_basket_map.json",
         json.dumps(_basket_cycle_map(cn), separators=(",", ":"), ensure_ascii=False).encode("utf-8"), head_map_b)
    lab_map = _basket_cycle_map(cn_lab)
    if lab_map == json.loads(head_map_b):
        put("chinasectordata/sector_cycles_basket_map.json", head_map_b,
            "HEAD:site/chinasectordata/sector_cycles_basket_map.json", "copy (labelled map is JSON-equal to HEAD)")
    else:
        put("chinasectordata/sector_cycles_basket_map.json",
            json.dumps(lab_map, separators=(",", ":"), ensure_ascii=False).encode("utf-8"),
            "_basket_cycle_map(labelled)", "computed")
    put_head("sector_cycles_china_narr_data.js")
    put_head("sector_cycles_china_dna_data.js")

    # ---- V2 / V4 pages ---------------------------------------------------------------
    from scripts.build_sector_cycles import PAGE_ASSETS, SHARED_ASSETS, cycles_page_ctx
    for a in PAGE_ASSETS:
        put_tpl(a)
    for a in SHARED_ASSETS:
        put_head(a)
    html = cycles_env().get_template("sector_cycles.html.j2").render(cycles_ctx=cycles_page_ctx(us_lab))
    write_page_l6("sector_cycles.html", html, "")
    try:
        cn_ctx = cycles_page_ctx(cn_lab, require_generation=False)
        CHECKS["v4_cycles_ctx"] = "ok"
    except Exception as e:  # noqa: BLE001 — mirrors the builder's fallback
        cn_ctx = None
        CHECKS["v4_cycles_ctx"] = f"None ({type(e).__name__})"
    html = cycles_env().get_template("sector_cycles_china.html.j2").render(cycles_ctx=cn_ctx)
    write_page_l6("sector_cycles_china.html", html, "")

    # ---- V1 Sector Central -----------------------------------------------------------
    import scripts.build_sector_central as bsc
    for rel in ("basketdata/action_board.json", "basketdata/baskets.json", "basketdata/si_handoff.json",
                "basketdata/foresight_cascade.json", "marketdata/subsector_rotation.json",
                "factordata/us_standouts.json", "live/basket_pulse.json", "heatmap.js"):
        put_head(rel)
    for rel in ("marketdata/rotation_events.json", "marketdata/sector_fragmentation.json"):
        put_head_opt(rel)
    data = json.loads(blob("site/sectordata/sector_central.json"))
    sc_js = js_payload("window.SECTOR_CENTRAL=", data, ensure_ascii=False)
    sc_json = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    same("sector_central_data.js", sc_js, blob("site/sector_central_data.js"))
    same("sectordata/sector_central.json", sc_json, blob("site/sectordata/sector_central.json"))
    put("sector_central_data.js", sc_js, "HEAD:site/sectordata/sector_central.json", "re-serialised (self-checked)")
    put("sectordata/sector_central.json", sc_json, "HEAD:site/sectordata/sector_central.json", "re-serialised (self-checked)")
    env = Environment(loader=FileSystemLoader(str(WT / "templates")), autoescape=True)
    env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    ctx, _ = bsc._read_secondary(OUT / "basketdata" / "si_handoff.json")
    ctx = ctx or {}
    action_doc, ab = bsc._read_secondary(OUT / "basketdata" / "action_board.json")
    action_doc = action_doc or {}
    action_board = bsc.drop_sizing_chips(action_doc.get("action_board"))
    basket_doc, bk = bsc._read_secondary(OUT / "basketdata" / "baskets.json")
    basket_doc = basket_doc or {}
    bottoming = None
    if bk["status"] == "ok":
        bottoming = bsc.build_bottoming_context(((basket_doc.get("theme_intel") or {}).get("act_now")), action_board)
    g = bsc._gate_cfg()
    pgate, _locked = bsc.split_actnow(action_board, g["preview_rows"], gated=g["gated"])
    ti = basket_doc.get("theme_intel")
    source_as_of = (action_doc.get("as_of") or ((ti or {}).get("as_of") if isinstance(ti, dict) else None)
                    or basket_doc.get("as_of") or data.get("as_of") or "")
    cycles_ctx = bsc.cycles_context(OUT, data)
    html = env.get_template("sector_central.html.j2").render(
        flows_html=None, pgate=pgate, bottoming=bottoming,
        theme_context=ctx.get("theme_context"), factor_season=ctx.get("factor_season"), flow=ctx.get("flow"),
        basket_member_syms=ctx.get("basket_member_syms") or [], action_board=action_board,
        source_as_of=source_as_of, baskets_sha256=bk["sha256"] or "", action_board_sha256=ab["sha256"] or "",
        accumulation=[], accumulation_universe_n=None, theme_tape=bsc._theme_tape_view(OUT),
        fast_lens=(data.get("market") or {}).get("fast_lens") or {}, cycles_ctx=cycles_ctx,
        generated_utc=ctx.get("generated_utc") or data.get("as_of") or "")
    write_page_l6("sector_central.html", html, "")
    CHECKS["v1_inputs"] = {"si_handoff": ctx and "ok", "action_board": ab["status"], "baskets": bk["status"],
                           "gate": g, "source_as_of": source_as_of, "cycles_ctx": bool(cycles_ctx)}
    missing = []
    for a in ("product-nav-icons.css", "dashboard-icons.css", "dashboard-icons.js", "sector_cycles.css",
              "sector_cycles.js", "sector_cycles_states.js", "sector_cycles_face.js", "sector_cycles_compare.js",
              "sector_cycles_platform.js", "sector_cycles_states.css", "sector_cycles_platform.css",
              "subsector_rotation.js", "rotation_events.js", "desk_watch.js", "rotation_glance.css",
              "time_machine.js", "forming_narratives.js", "si_workspace.js"):
        if blob_exists(f"templates/{a}"):
            put_tpl(a)
        else:
            missing.append(a)
    if missing:
        GAPS.append(f"central assets absent from HEAD templates: {missing}")
    for req in ("sector_cycles_data.js", "sector_cycles_series_data.js", "sector_cycles_narr_data.js",
                "sector_cycles_dna_data.js", "mm_charts.js", "cycle.css", "heatmap.js"):
        if req not in WRITTEN:
            raise SystemExit(f"V1 required asset not written: {req}")

    # ---- V3 sectors/XLK.html ---------------------------------------------------------
    import re as _re
    import scripts.build_site as bs
    from engine import ticker_alerts
    from engine.conditions import sector_macro_beta
    from engine.cycles import LADDER, STATE_DISPLAY, analyze
    from engine.playbook import SECTOR_NAMES
    from lib.seo import SITE_BASE
    from engine.macro_news import CHANNEL_LABEL
    env3 = Environment(loader=FileSystemLoader(str(WT / "templates")), autoescape=True)
    env3.filters["min"] = lambda seq: min(seq)
    env3.filters["regex_replace"] = lambda s, pattern, repl: _re.sub(pattern, repl, s) if isinstance(s, str) else s
    env3.globals.update(td=i18n.td, tr=i18n.tr, t_pctile=i18n.t_pctile, zip=zip, SITE_BASE=SITE_BASE,
                        CHANNEL_LABEL=CHANNEL_LABEL)
    env3.globals["us_stance_projection"] = bs.us_stance_projection
    cal_p = RT / "data" / "regime" / "ladder_calibration.json"
    cal_b = cal_p.read_bytes() if cal_p.exists() else None
    _record_read("data/regime/ladder_calibration.json", cal_b)
    calibration = json.loads(cal_b) if cal_b else None
    put_head("live/shock_state.json")
    shock = json.loads((OUT / "live" / "shock_state.json").read_text(encoding="utf-8"))
    liq = drag = None
    spy = rt_read("yahoo", "SPY")
    bench = spy["close"] if spy is not None else None
    acfg = config.load().get("alerts", {})
    adays, amax = int(acfg.get("ticker_timeline_days", 120)), int(acfg.get("ticker_max_events", 50))
    fund = "XLK"
    etf = rt_read("yahoo", fund)
    beta = sector_macro_beta(fund)
    res = analyze(etf["close"], liquidity=liq, macro_drag=drag, macro_beta=beta)
    holdings, members = [], []
    t10 = latest_top10_rt(fund)
    for _, r in t10.iterrows():
        tick = str(r["ticker"]).replace(".", "-")
        df = rt_read("stocks", tick)
        try:
            mw = float(r.get("weight_pct"))
            mw = mw if mw == mw else None
        except (TypeError, ValueError):
            mw = None
        thin = df is None or len(df) < 300
        members.append({"ticker": tick, "name": str(r.get("name", "")).title(), "weight": mw, "resolved": not thin,
                        "reason": (None if not thin else "no_price_history" if df is None else "insufficient_history")})
        if thin:
            continue
        h = analyze(df["close"], df.get("high"), liquidity=liq, macro_drag=drag, macro_beta=beta)
        if not h.get("ladder"):
            continue
        h["mtf_json"] = json.dumps(h.get("mtf", {}))
        holdings.append({"ticker": tick, "name": str(r.get("name", "")).title(), "weight_pct": r["weight_pct"],
                         **h, "fundamentals": latest_fundamentals_rt(tick)})
    s = {"fund": fund, "name": SECTOR_NAMES.get(fund, fund), "mtf_json": json.dumps(res.get("mtf", {})), **res,
         "holdings": holdings, "members": members, "rate_infl": None, "dollar_ctx": None, "accumulation": None}
    ec = etf["close"].dropna()
    s["as_of"] = str(ec.index.max().date())
    from engine.technicals import snapshot as _snap
    s["tech"] = _snap(ec)
    try:
        from engine import sector_signals as _ssig
        sig = _ssig.sector_signal(ec, SECTOR_NAMES.get(fund, fund), spy_close=bench, ticker=fund, put_absent=False)
        if sig.get("ok"):
            sig["signal_en"] = _ssig.signal_line(sig)
            sig["signal_zh"] = _ssig.signal_line(sig, zh=True)
        s["confluence"] = sig
    except Exception as e:  # noqa: BLE001 — mirrors the builder
        s["confluence"] = None
        GAPS.append(f"V3 confluence None ({type(e).__name__})")
    feed = ticker_alerts.build_feed(fund, ec, etf.get("high"), bench, res.get("ladder"), str(ec.index.max().date()),
                                    days=adays, max_events=amax)
    tpl = env3.get_template("sector.html.j2")

    def render_xlk(sv):
        return tpl.render(s=sv, state_styles=bs.STATE_STYLES, calibration=calibration, ladder_order=LADDER,
                          state_display=STATE_DISPLAY, alerts=feed, generated_utc=args.generated, shock_state=shock)

    write_page_l6("sectors/XLK.html", render_xlk(s), "../")
    CHECKS["v3"] = {"members": len(members), "holdings": len(holdings),
                    "unresolved": [m["ticker"] for m in members if not m["resolved"]],
                    "etf_last": str(ec.index.max().date()), "etf_has_high": "high" in etf.columns,
                    "calibration": cal_b is not None, "generated_utc": args.generated}
    put_tpl("sector_dossier.js")
    for a in ("mtf.js", "theme.js", "theme.css"):
        put_head(a)

    # ---- variants: _variants/<v>/<served path>, selected by the X-L6-Variant header ---
    un = copy.deepcopy(core_l)
    first = next(e for e in un["sectors"] if isinstance(e, dict) and "id" in e)
    dropped = sorted(k for k in (first.get("now") or {}) if k.startswith("doctrine_"))
    for k in dropped:
        del first["now"][k]
    put("_variants/unstamped/sector_cycles_data.js", js_payload(P_CORE, un, ensure_ascii=True),
        "sector_cycles_data.js", f"sectors[{first['id']}].now: removed {dropped}")
    VARIANTS["unstamped"] = {"entity": first["id"], "removed": dropped, "serves": ["sector_cycles_data.js"]}
    pulse = json.loads(blob("site/live/basket_pulse.json"))
    for v, stamp in (("pulse_gt5d", "2026-10-26T19:38:46.535556+00:00"),
                     ("pulse_le5d", "2026-11-02T19:38:46.535556+00:00")):
        pv = copy.deepcopy(pulse)
        for k in ("as_of_utc", "as_of_quotes"):
            if k not in pv:
                raise SystemExit(f"basket_pulse lacks {k}")
            pv[k] = stamp
        b = json.dumps(pv, ensure_ascii=False, indent=1).encode("utf-8")
        put(f"_variants/{v}/live/basket_pulse.json", b, "HEAD:site/live/basket_pulse.json",
            f"as_of_utc=as_of_quotes={stamp}")
        fx = EV / "fixtures" / f"basket_pulse__{v}.json"
        fx.parent.mkdir(parents=True, exist_ok=True)
        fx.write_bytes(b)
        VARIANTS[v] = {"as_of": stamp, "serves": ["live/basket_pulse.json"], "sha256": sha(b),
                       "fixture": f"fixtures/{fx.name}"}
    sv = copy.deepcopy(s)
    extra = {"ticker": "FIXTURE", "name": "Fixture member (no price history)", "weight": None,
             "resolved": False, "reason": "no_price_history"}
    sv["members"] = sv["members"] + [extra]
    from lib.pages import inject_text
    from lib.shared_shell import inject_shared_shell_text
    vv = sha((OUT / "shared_shell_bridge.js").read_bytes())[:8]
    cvv = sha((OUT / "shared_shell.css").read_bytes())[:8]
    r = inject_shared_shell_text(inject_text(render_xlk(sv), "../"), "../", site_dir=OUT, response_kind="content",
                                 version=vv, css_version=cvv)
    put("_variants/xlk_unresolved/sectors/XLK.html", r.encode("utf-8"), "render", "members + one FIXTURE unresolved")
    VARIANTS["xlk_unresolved"] = {"added_member": extra, "serves": ["sectors/XLK.html"]}

    guards.append(guard("after"))
    DEVS.extend([
        "DEV-L6-5: no data dir; engine.cycles falls back to CYCLE_PRESETS bands and risk calibration 1.0",
        "fences: config.data_dir/config.site_dir/store._path patched to nonexistent paths (no mkdir); calls recorded",
        "V3 price history and ladder_calibration.json read read-only from the --rt render tree",
        f"V3 generated_utc pinned to {args.generated!r}",
        "lane ran seat-direct (Fabric offered no darwin/arm64 host for the pin)",
        "labelled fixtures are re-derived by this script from HEAD blobs, not stored (2.0 MB + 1.2 MB)",
    ])
    GAPS.extend([
        "fixture chip is face-only (SC_FACE.card); grid/inspector rows carry no chip",
        "V1 rendered from HEAD sector_central.json: no accumulation rows, no flows section",
        "V3 without liquidity/macro drag, dollar_ctx, accumulation, rate_infl, alpha_leaders, notable",
        "V3 alert feed: no ladder history, RT yahoo ETF frame has no high column; put_absent=False",
        "China sleeve_chip present only as committed in HEAD (cn_sleeve_chip not called)",
        "US turn_record carried from the HEAD core payload (backtest_turn_record not called)",
        "V1 publication + grader blocks as committed in the HEAD central json",
    ])
    fences = [{"fn": fn, "caller": c, "arg": a, "n": n} for (fn, c, a), n in sorted(FENCES.items())]
    written = {"head": head, "out": str(OUT), "files": dict(sorted(WRITTEN.items()))}
    (OUT / "_l6_written.json").write_text(json.dumps(written, indent=1, sort_keys=True), encoding="utf-8")
    fixtures = {"schema": "sector_cycles.l6_fixtures.v1", "head": head, "rt": str(RT),
                "written": {k: {"sha256": v["sha256"], "source": v["source"], "transform": v["transform"]}
                            for k, v in sorted(WRITTEN.items()) if not k.startswith(("fonts/", "p0b-font-pin/"))},
                "reads": dict(sorted(READS.items())), "fences": fences, "checks": CHECKS, "variants": VARIANTS,
                "devs": DEVS, "gaps": GAPS, "guards": guards}
    (EV / "fixtures" / "FIXTURES.json").write_text(json.dumps(fixtures, indent=1, sort_keys=True, default=str),
                                                   encoding="utf-8")
    guard("final")
    print(json.dumps({"head": head, "written": len(WRITTEN), "reads": len(READS), "fence_sites": len(fences),
                      "checks": CHECKS, "variants": sorted(VARIANTS), "gaps": len(GAPS)}, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""D03 T42 evidence: real cohort producer, unchanged output, actual page builder.
Synthetic data only. No product edits, live data, policy changes, or publication.
"""
from __future__ import annotations
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch
import zipfile

BASE = "ffda5424b75bbbb26e33a4d328043bbfb480e6ff"
EXPECTED = {
    "engine/top_maturation.py": "86497282e630d55dcc6ac32e0d5b8439cc032a3ccb6a8216603f8b9ade7bf095",
    "tests/test_top_maturation.py": "4cbaebdd734f37e48826e54eee87f7baa14a615b9d5acb4b2ebd8caafddf2efb",
    "scripts/build_top_maturation.py": "21308abcff39c61cbb8b1c760342d9af37b164886f218b0329d01a93b468b3d6",
    "scripts/build_winner_health_page.py": "be6fb99b48d9de9a432d063557e93574ad8336837abd7571006e5e4978d7bd3e",
    "templates/winner_health.html.j2": "545454c3650de638e82fec0b06582ad994adb3efe385a3baf293531577f3997f",
}
SOURCE_FILES = tuple(EXPECTED) + (
    "engine/top_anatomy.py", "engine/session_anchor.py", "templates/theme.css",
    "templates/theme.js", "templates/_lens.html.j2", "lib/config.py", "lib/pages.py",
    "lib/shared_shell.py",
)
STATE_KEYS = ("extended_healthy", "extended_watch", "thinning", "breaking", "no_read")
FOCUS = {"AAA", "BBB", "CCC", "DBRK", "DFLT", "DOLD"}

def require(value, message):
    if not value:
        raise AssertionError(message)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def json_default(value):
    if hasattr(value, "item"):
        return value.item()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    raise TypeError(type(value).__name__)

def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2,
                               default=json_default, allow_nan=False) + "\n")

def row_map(ctx, key):
    tier = next(t for t in ctx["tiers"] if t["key"] == key)
    return {r["ticker"]: (state, r) for state, rows in tier["states"].items() for r in rows}

def source_preflight(root):
    drift = subprocess.check_output(["git", "diff", "--name-only", BASE, "--",
        "templates", "scripts", "lib", "engine", "site", "config.yml",
        "tests/test_top_maturation.py"], cwd=root, text=True)
    require(not drift.strip(), "product/helper source drift: " + drift)
    hashes = {p: digest(root / p) for p in SOURCE_FILES}
    for path, sha in EXPECTED.items():
        require(hashes[path] == sha, "source hash drift: " + path)
    return hashes

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    root, out = args.root.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    require(not (out / "producer-proof.json").exists(), "existing producer proof must be preserved")
    hashes = source_preflight(root)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    sys.path.insert(0, str(root))
    import numpy as np
    import pandas as pd
    from engine import top_maturation as tm, session_anchor
    from scripts import build_winner_health_page as builder
    from lib import config, pages

    module_spec = importlib.util.spec_from_file_location(
        "d03_t42_committed_synthetic_helpers", root / "tests/test_top_maturation.py")
    helpers = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(helpers)

    producer_lines = (root / "engine/top_maturation.py").read_text().splitlines()
    markers = {
        "readability_gate": "        if not is_readable_row(ev, tot):",
        "classification_call": "        state = classify(fired)",
        "classified": "        if off_band:",
        "analogue_call": "        analog = _analog(vec, lib, base, drawdown_pct, track)",
    }
    gate = next(i + 1 for i, line in enumerate(producer_lines) if line == markers["readability_gate"])
    classify_line = next(i + 1 for i, line in enumerate(producer_lines) if line == markers["classification_call"])
    analog_line = next(i + 1 for i, line in enumerate(producer_lines) if line == markers["analogue_call"])
    watched = {gate: "readability_gate", gate + 7: "unreadable_off_band_exit",
               classify_line: "classification_call", classify_line + 1: "classified",
               classify_line + 4: "nonbreaking_off_band_exit",
               classify_line + 5: "breaking_off_band_retained",
               analog_line: "analogue_call"}
    require(producer_lines[gate + 6].strip() == "continue", "unreadable trace boundary drift")
    require(producer_lines[classify_line + 3].strip() == "continue", "nonbreaking trace boundary drift")
    require(producer_lines[classify_line + 4].strip() == "n_off_band_kept += 1", "retention trace drift")
    require(tm.MEMBERSHIP_WINDOW_SESSIONS == 21, "membership window drift")
    trace = []
    def observer(frame, event, arg):
        if frame.f_code is not tm._build_tier.__code__:
            return None
        if event == "line" and frame.f_lineno in watched:
            v = frame.f_locals
            if v.get("base") in FOCUS:
                stage = watched[frame.f_lineno]
                rec = {"line": frame.f_lineno, "stage": stage, "tier": v["tier"],
                       "ticker": v["base"], "segment": v["seg"],
                       "off_band": bool(v["off_band"]),
                       "evaluated": int(v["ev"]), "total": int(v["tot"])}
                if stage in {"classified", "nonbreaking_off_band_exit",
                             "breaking_off_band_retained", "analogue_call"}:
                    rec["state"] = v["state"]
                if stage != "readability_gate" and stage != "unreadable_off_band_exit":
                    rec["fired"] = list(v.get("fired", []))
                trace.append(rec)
        return observer

    results = {}
    with tempfile.TemporaryDirectory(prefix="d03-t42-synthetic-") as td:
        temp = Path(td)
        data = temp / "data"
        data.mkdir()
        helpers._store(data, membership=True)
        for key, seed in (("r63", 8), ("atrz", 9)):
            library = helpers._library(seed=seed)
            if key == "r63":
                library["late_gain_share"] = np.linspace(0.01, 0.11, len(library)).astype("float32")
            library.to_parquet(data / tm._tier_rel(tm.LIBRARY_REL, key), index=False)
            thresholds = helpers._thresholds()
            if key == "r63":
                thresholds["thresholds"]["late_verticality_p90"] = float(library["late_gain_share"].quantile(0.9))
            thresholds["ext_variant"] = key
            thresholds["thresholds"]["running_hot_p90"] = 70.0
            save_json(data / tm._tier_rel(tm.THRESHOLDS_REL, key), thresholds)
        calendar = pd.bdate_range("2024-01-01", periods=700)
        asof = calendar[-1].date().isoformat()
        inputs = [{"path": str(p.relative_to(data)), "sha256": digest(p), "bytes": p.stat().st_size}
                  for p in sorted(data.rglob("*")) if p.is_file()]
        with zipfile.ZipFile(out / "synthetic-inputs-normal.zip", "w", zipfile.ZIP_DEFLATED) as archive:
            for record in inputs:
                info = zipfile.ZipInfo(record["path"], date_time=(2026, 11, 4, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, (data / record["path"]).read_bytes())
        save_json(out / "synthetic-input-manifest.json", {
            "fixture_only": True, "helper_source": hashes["tests/test_top_maturation.py"],
            "helper": "_store(membership=True), defaults:26 baseline names,700 bars",
            "tier_libraries": {"primary": {"seed": 7}, "r63": {"seed": 8}, "atrz": {"seed": 9}},
            "r63_atrz_fixture_threshold": {"running_hot_p90": 70.0},
            "r63_counting_fixture": {"late_gain_share": "600 deterministic values from0.01 to0.11",
                                     "late_verticality_p90": "actual 90th percentile of this synthetic tier library"},
            "asof": asof, "calendar": "synthetic business-day index; no live session file",
            "inputs": inputs,
        })
        page_root = temp / "page"
        page_root.mkdir()
        (page_root / "templates").symlink_to(root / "templates", target_is_directory=True)
        (page_root / "config.yml").write_text("storage:\n  data_dir: data\n  site_dir: site\n")
        for name in ("readable", "primary-unreadable"):
            if name == "primary-unreadable":
                thresholds = helpers._thresholds()
                thresholds["thresholds"] = {"episode_age_p90": 92.0}
                save_json(data / tm.THRESHOLDS_REL, thresholds)
                save_json(out / "primary-unreadable-thresholds.json", thresholds)
            trace.clear()
            log = []
            print(json.dumps({"phase": "producer-start", "case": name}), flush=True)
            started = time.monotonic()
            with ExitStack() as stack:
                stack.enter_context(patch.dict(os.environ))
                os.environ.pop("COLLECT_LANE", None)
                os.environ.pop("US_LANE", None)
                stack.enter_context(patch.object(socket.socket, "connect",
                    side_effect=AssertionError("synthetic producer network is forbidden")))
                stack.enter_context(patch.object(tm, "_load_names_zh", return_value={}))
                stack.enter_context(patch.object(session_anchor, "reference_sessions",
                    return_value=calendar))
                sys.settrace(observer)
                try:
                    ctx, diag = tm.build_context(data, out_root=temp / ("cache-" + name),
                        repo_root=None, asof=asof, log=log.append)
                finally:
                    sys.settrace(None)
            seconds = round(time.monotonic() - started, 3)
            case_dir = out / name
            case_dir.mkdir()
            save_json(case_dir / "producer-context.json", ctx)
            save_json(case_dir / "producer-diagnostics.json", diag)
            save_json(case_dir / "producer-gate-trace.json", list(trace))
            (case_dir / "producer.log").write_text("\n".join(log) + "\n")
            require(ctx["schema"] == "winner_health.v2", "schema mismatch")
            require([t["key"] for t in ctx["tiers"]] == ["primary", "r63", "atrz"], "tier order")
            require(not {"extended_n", "states", "theme_counts"} & set(ctx), "cross-tier aggregate")
            tiers = {t["key"]: t for t in ctx["tiers"]}
            for key, tier in tiers.items():
                require(tier["readable"] is True, "fixture should exercise all readable tiers")
                require(set(tier["states"]) == set(STATE_KEYS), "state keys")
                require(tier["extended_n"] == sum(map(len, tier["states"].values())), "per-tier count")
                for state, rows in tier["states"].items():
                    require(all(r["state"] == state for r in rows), "inconsistent row state")
                    if key != "primary":
                        require([r["ticker"] for r in rows] == sorted(r["ticker"] for r in rows),
                                "widened cohort alphabetic ordering")
                    elif state != "no_read":
                        gains = [r["r126"] for r in rows if r["r126"] is not None]
                        require(gains == sorted(gains, reverse=True), "primary gain order")
            primary, r63 = row_map(ctx, "primary"), row_map(ctx, "r63")
            primary_trace = [x for x in trace if x["tier"] == "primary"]
            events = lambda ticker: [x for x in primary_trace if x["ticker"] == ticker]
            stages = lambda ticker: {x["stage"] for x in events(ticker)}
            ledger = diag["ledger_rows"]
            ledger_names = [r["ticker"] for r in ledger]
            require(len(ledger_names) == len(set(ledger_names)), "ledger is not primary-only per ticker")
            require(all(r["ticker"] in primary and primary[r["ticker"]][0] == r["state"]
                        for r in ledger), "ledger differs from primary board")
            require("DOLD" not in primary and not events("DOLD"), "outside-window control included")
            pdiag = diag["tiers"]["primary"]
            require(pdiag["n_off_band_candidates"] == 2, "fixture off-band membership changed")
            require(pdiag["n_off_band_candidates"] ==
                    pdiag["n_off_band_on_board"] + pdiag["n_off_band_dropped"],
                    "candidate accounting")
            if name == "readable":
                require(primary["AAA"][0] == "extended_healthy", "AAA primary expectation")
                require(r63["AAA"][0] == "extended_watch", "AAA r63 expectation")
                require({"running_hot", "late_verticality"} <=
                        {leg["key"] for leg in r63["AAA"][1]["legs"]},
                        "r63 lacks its own counting-library-cut witness")
                require(primary["DBRK"][0] == "breaking", "breaking control missing")
                db = next(r for r in ledger if r["ticker"] == "DBRK")
                require(db["off_band"] is True and
                        {"below_50d", "drawdown_from_high"} <= set(db["fired"]),
                        "breaking control lacks structural/ledger witness")
                require("DFLT" not in primary and "DFLT" not in ledger_names, "nonbreaking escaped filter")
                require("breaking_off_band_retained" in stages("DBRK") and
                        "analogue_call" in stages("DBRK"), "retained path not observed")
                require("nonbreaking_off_band_exit" in stages("DFLT") and
                        "classification_call" in stages("DFLT") and
                        "analogue_call" not in stages("DFLT"), "nonbreaking filter ordering")
                require(pdiag["n_off_band_on_board"] == 1 and pdiag["n_off_band_dropped"] == 1,
                        "normal off-band counts")
            else:
                require(primary["AAA"][0] == "no_read", "in-band unreadable positive control missing")
                checks = primary["AAA"][1]["checks"]
                require(checks["evaluated"] < (checks["total"] + 1) // 2,
                        "unreadable row meets majority")
                for ticker in ("DBRK", "DFLT"):
                    require(ticker not in primary and ticker not in ledger_names, "unreadable off-band kept")
                    require("unreadable_off_band_exit" in stages(ticker), "unreadable exit not observed")
                    require(not {"classification_call", "analogue_call"} & stages(ticker),
                            "unreadable off-band entered downstream computation")
                require(pdiag["n_off_band_on_board"] == 0 and pdiag["n_off_band_dropped"] == 2,
                        "unreadable off-band counts")
                require(r63["AAA"][0] == "extended_watch", "other cohort affected by primary inputs")
            # This is the existing publisher's diagnostic projection, not a run of
            # its publication/ledger CLI. Original producer rows remain unchanged.
            artifact = dict(ctx)
            artifact["_diagnostics"] = {k: v for k, v in diag.items() if k != "ledger_rows"}
            save_json(case_dir / "consumer-artifact.json", artifact)
            with patch.object(config, "ROOT", page_root), patch.object(pages, "_shim_checked", False), \
                 patch.object(socket.socket, "connect",
                    side_effect=AssertionError("page builder network is forbidden")):
                actual = builder.build(page_root, fixture=case_dir / "consumer-artifact.json")
                require(actual == page_root / "site/winner_health.html", "unexpected page destination")
                rendered = actual.read_bytes()
                (case_dir / "rendered.html.gz").write_bytes(gzip.compress(rendered, mtime=0))
            unique = {r["ticker"] for t in ctx["tiers"] for rows in t["states"].values() for r in rows}
            results[name] = {
                "status": "PASS", "producer_seconds": seconds,
                "tiers": {k: {"count": t["extended_n"],
                              "states": {s: [r["ticker"] for r in rows] for s, rows in t["states"].items()},
                              "off_band": diag["tiers"][k]["n_off_band_on_board"]}
                          for k, t in tiers.items()},
                "independent_count_sum": sum(t["extended_n"] for t in ctx["tiers"]),
                "unique_names_for_evidence_only": len(unique),
                "ledger_tickers": ledger_names,
                "source_rows_modified": False, "trace_events": len(trace),
                "producer_context_sha256": digest(case_dir / "producer-context.json"),
                "diagnostics_sha256": digest(case_dir / "producer-diagnostics.json"),
                "consumer_artifact_sha256": digest(case_dir / "consumer-artifact.json"),
                "rendered_html_sha256": hashlib.sha256(rendered).hexdigest(),
            }
            require(results[name]["independent_count_sum"] > len(unique), "overlap fixture is not discriminating")
            print(json.dumps({"phase": "producer-pass", "case": name,
                              "seconds": seconds, "tiers": {k: v["count"] for k, v in results[name]["tiers"].items()},
                              "primary_off_band": pdiag["n_off_band_on_board"]}), flush=True)
    after = source_preflight(root)
    require(after == hashes, "source changed during evidence run")
    report = {
        "task": "D03 T42", "status": "SCOPED_PRODUCER_AND_BUILDER_PROOF",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "baseline": BASE, "checkout_head": head, "source_hashes": hashes, "source_after": after,
        "versions": {"python": sys.version, "numpy": np.__version__, "pandas": pd.__version__},
        "synthetic_only": True, "product_source_unchanged": True,
        "producer_runs": 2, "membership_window_sessions": tm.MEMBERSHIP_WINDOW_SESSIONS,
        "default_trailing_sessions": tm.PANEL_TRAILING_SESSIONS,
        "trace": {"method": "read-only sys.settrace observation; no algorithm stubs/wrappers",
                  "lines": watched, "producer_sha256": hashes["engine/top_maturation.py"]},
        "isolation": [
            "All tape, metadata, libraries, cache, context and rendered writes use a temporary root.",
            "Only name translation and reference-session inputs are deterministic fixtures.",
            "COLLECT_LANE and US_LANE are absent for these synthetic runs; restored afterwards.",
            "Socket connections forbidden for producer and builder; no live collector or endpoint.",
            "Real masks, features, readability, classification, membership, sorting and analogues execute.",
            "Consumer artifacts use exact existing diagnostics projection; publisher/ledger CLI not run.",
            "Builder explicit fixture mode bypasses historical artifact freshness admission by design.",
            "repo_root=None: no fabricated stock destinations; consumer ticker labels remain plain text."
        ],
        "cases": results,
        "limits": [
            "This proves the four scoped cohort/membership cases, not market outcomes or trading authority.",
            "No W07 composition, T43 freshness, T44 analogue disclosure, shared LENS repair or final acceptance.",
            "Browser validation is separate and must consume these retained exact rendered bytes."
        ],
    }
    save_json(out / "producer-proof.json", report)
    print(json.dumps({"phase": "complete", "status": report["status"],
                      "report": str(out / "producer-proof.json"),
                      "report_sha256": digest(out / "producer-proof.json")}), flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

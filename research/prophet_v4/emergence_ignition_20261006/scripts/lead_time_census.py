#!/usr/bin/env python3
"""Read pinned Git objects; measure preserved publication clocks, never fills.

Writes research results only. No collectors, production imports, or network calls.
Git may fetch an absent promisor object according to the supplied repository's config.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path

PIN = "731a23fb64b9f6f1a321c77618f927f1a58d2d41"
CUTOFF = "2026-10-06"
SELECTED = {"NVDA", "FORM", "PWR", "WDC", "TSLA", "ADM", "PRIM", "INTC", "ISRG"}
CHECKPOINTS = {
    "sep25_failed": "4a1882bf510a642674d110c3c5c5dec3111e8ea2",
    "sep26_clean": "74e8f45060e815a2cb7c515ae09f258919ab9da2",
}


def parsed(value):
    if not isinstance(value, str) or "T" not in value:
        return None
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except ValueError:
        return None


def elapsed(start, end):
    a, b = parsed(start), parsed(end)
    return round((b-a).total_seconds(), 6) if a and b else None


def summarize(values):
    x = sorted(v for v in values if v is not None)
    if not x:
        return {"n": 0, "minimum": None, "median": None, "maximum": None}
    return {"n": len(x), "minimum": x[0], "median": statistics.median(x), "maximum": x[-1]}


class Source:
    def __init__(self, repo):
        self.repo = str(Path(repo).resolve())
        self.manifest = {}

    def git(self, *args):
        return subprocess.check_output(["git", "-C", self.repo, *args], stderr=subprocess.PIPE)

    def read(self, ref, path):
        b = self.git("show", f"{ref}:{path}")
        self.manifest[f"{ref}:{path}"] = {
            "ref": ref, "path": path, "bytes": len(b),
            "git_blob": hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest(),
            "sha256": hashlib.sha256(b).hexdigest(),
        }
        return json.loads(b)

    def paths(self, ref, directory):
        return self.git("ls-tree", "-r", "--name-only", ref, directory).decode().splitlines()

    def commit_time(self, ref):
        return self.git("show", "-s", "--format=%cI", ref).decode().strip()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False, sort_keys=True)+"\n")


def write_csv(path, rows):
    if not rows:
        path.write_text("")
        return
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def census(repo, ref, output):
    src = Source(repo)
    receipt_rows, plan_rows = [], []
    source_errors = []
    for path in src.paths(ref, "data/prophet/origination_receipts"):
        if not path.endswith(".json"):
            continue
        d = src.read(ref, path)
        if str(d.get("recorded_utc", ""))[:10] > CUTOFF:
            continue
        s = d.get("source") or {}
        stale = s.get("staleness") or {}
        inputs = stale.get("inputs") or {}
        panel = inputs.get("panel") or {}
        observation = stale.get("observed_at_utc")
        recorded = d.get("recorded_utc")
        delay = elapsed(observation, recorded)
        backfill = "backfill" in path.lower()
        clean = (s.get("delayed") is False and s.get("unknown") is False
                 and panel.get("mixed_vintage") is False)
        row = {
            "receipt_path": path, "receipt_id": d.get("receipt_id"),
            "run_id": (d.get("run") or {}).get("id"),
            "backfill": backfill, "recorded_utc": recorded,
            "source_observed_at_utc": observation,
            "source_asof": s.get("source_asof"), "board_asof": s.get("board_asof"),
            "source_delayed": s.get("delayed"), "source_unknown": s.get("unknown"),
            "source_mixed_vintage": panel.get("mixed_vintage"),
            "clean_witness": clean, "source_to_receipt_seconds": delay,
            "admitted_count": (d.get("selection") or {}).get("admitted_count"),
            "originated_count": (d.get("selection") or {}).get("originated_count"),
            "source_board_sha256": s.get("sha256"),
        }
        receipt_rows.append(row)
        for o in d.get("originations", []):
            b = o.get("board_row") or {}
            signal = b.get("signal") or {}
            entry = b.get("entry_signal") or {}
            if isinstance(entry, str):
                entry = {"entry_status": entry}
            plan_rows.append({
                "receipt_id": d.get("receipt_id"), "plan_id": o.get("plan_id"),
                "ticker": o.get("asset"), "recorded_utc": recorded,
                "backfill": backfill, "source_observed_at_utc": observation,
                "clean_witness": clean, "formation_date": o.get("formation_date"),
                "signal_asof": signal.get("asof"),
                "tier": signal.get("tier_cascade"),
                "tier_event_date": signal.get("tier_event_date"),
                "tier_observed_date": signal.get("tier_observed_date"),
                "tier_provisional": signal.get("tier_observation_provisional"),
                "signal_eligible": signal.get("eligible"),
                "source_entry_status": entry.get("status", entry.get("entry_status")),
                "plan_sha256_at_origination": o.get("plan_sha256"),
                "plan_path": o.get("plan_path"),
            })
    receipt_rows.sort(key=lambda r: (r.get("recorded_utc") or "", r["receipt_path"]))
    plan_rows.sort(key=lambda r: (r.get("recorded_utc") or "", r.get("plan_id") or ""))
    if len({r["receipt_id"] for r in receipt_rows}) != len(receipt_rows):
        raise ValueError("Duplicate receipt identities")
    checkpoints = {}
    for name, commit in CHECKPOINTS.items():
        try:
            d = src.read(commit, "site/prophet/index.json")
            intake = d.get("intake") or {}
            checkpoints[name] = {
                "commit": commit, "git_committed_at": src.commit_time(commit),
                "index": {k:d.get(k) for k in ["asof", "source_asof", "source_board_asof",
                            "source_delayed", "source_mixed_vintage", "source_unknown"]},
                "intake_scalar_fields": {k:v for k,v in intake.items() if not isinstance(v, (dict,list))},
                "intake_keys": list(intake),
            }
        except (subprocess.CalledProcessError, ValueError) as e:
            source_errors.append({"ref":commit,"path":"site/prophet/index.json","error":type(e).__name__})
    clean_forward = [r for r in receipt_rows if r["clean_witness"] and not r["backfill"]]
    nvda = next((r for r in plan_rows if r["plan_id"] == "NVDA-BULL-20260917"), None)
    nvda_clocks = None
    if nvda:
        plan_git = src.commit_time(CHECKPOINTS["sep26_clean"])
        alert_git = src.commit_time("a374fd966466d342154e5147efec48281f77b501")
        alert = "2026-09-25T09:02:33Z"  # inherited exact receipt, parent PR #8495
        nvda_clocks = {
            "alert_generated_at": alert, "alert_first_git_at": alert_git,
            "preserved_clean_source_clock": nvda["source_observed_at_utc"],
            "origination_receipt_at": nvda["recorded_utc"], "plan_first_git_at": plan_git,
            "reader_visible_at": None,
            "reader_visible_reason": "No matching historical production-reader receipt in committed sources inspected",
            "alert_to_git_seconds": elapsed(alert, alert_git),
            "alert_to_clean_source_witness_seconds": elapsed(alert, nvda["source_observed_at_utc"]),
            "clean_source_witness_to_origination_seconds": elapsed(nvda["source_observed_at_utc"],nvda["recorded_utc"]),
            "origination_to_plan_git_seconds": elapsed(nvda["recorded_utc"],plan_git),
            "alert_to_plan_git_seconds": elapsed(alert,plan_git),
            "first_current_B4_open_at": None,
            "B4_reason": "Legacy entry_status / stale alert is not canonical current Entry Availability proof",
            "executable_fill_at": None,
            "fill_reason": "No trade fill receipt; final-plan later regular-session bars above no-chase ceiling in inherited source audit",
        }
    summary = {
        "status":"DISCOVERY_OPERATIONAL_CENSUS_NO_TRADING_AUTHORITY", "source_pin":ref,
        "historical_cutoff_inclusive":CUTOFF,
        "receipts":len(receipt_rows), "backfill_receipts":sum(r["backfill"] for r in receipt_rows),
        "forward_receipts":sum(not r["backfill"] for r in receipt_rows),
        "originated_plan_rows":len(plan_rows), "unique_plan_ids":len({r["plan_id"] for r in plan_rows}),
        "unique_tickers":len({r["ticker"] for r in plan_rows}),
        "receipt_time_span":[receipt_rows[0]["recorded_utc"],receipt_rows[-1]["recorded_utc"]] if receipt_rows else [],
        "clean_forward_receipts":len(clean_forward),
        "clean_forward_source_observed_to_receipt_seconds":summarize(r["source_to_receipt_seconds"] for r in clean_forward),
        "negative_intervals":sum(r["source_to_receipt_seconds"] is not None and r["source_to_receipt_seconds"]<0 for r in receipt_rows),
        "checkpoints":checkpoints,"nvda_clocks":nvda_clocks,"source_errors":source_errors,
        "limitations":[
            "Receipt census is selected on successful originations and is not all opportunities or failed runs.",
            "A source-observed clock is a preserved clean-source witness, not proof of earliest availability.",
            "Git commit time proves repository preservation, not production reader visibility or remote push time.",
            "Source entry_status is a legacy board proxy, not independent B4 current-action acceptance.",
            "Date-only event or basis fields are not precise publication timestamps and are not subtracted as times.",
            "No zero is substituted for unknown reader/fill clocks; no executable P&L or fraction of alpha recovered is inferred.",
            "Backfill receipts are separately disclosed and excluded from forward latency summaries.",
        ],
    }
    output.mkdir(parents=True,exist_ok=True)
    write_csv(output/"operational_receipts.csv",receipt_rows)
    write_csv(output/"operational_selected_plan_origins.csv",[r for r in plan_rows if r["ticker"] in SELECTED])
    write_json(output/"operational_lead_time.json",summary)
    write_json(output/"operational_source_manifest.json",list(src.manifest.values()))
    print(json.dumps({k:v for k,v in summary.items() if k not in ["checkpoints","limitations"]},indent=2))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo",required=True,type=Path)
    p.add_argument("--ref",default=PIN)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    target=a.output.resolve()
    for protected in ["data","site","engine","scripts","templates"]:
        if target.is_relative_to((a.repo/protected).resolve()):
            p.error("Output cannot be a production path")
    census(a.repo,a.ref,target)


if __name__ == "__main__":
    main()

"""Read recorded first-parent versions at next-session decision cutoffs.

A Git committer timestamp is NOT an observed push, source availability,
subscriber delivery, or execution timestamp. This is a version-history
reconstruction, with those clocks explicitly unknown.
"""
import argparse
import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lib.nyse_calendar import session_n_forward

PATHS = (
    "data/regime/latest.json",
    "data/market_state/latest.json",
    "data/risk_envelope/latest.json",
    "site/rr_banner.json",
)


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--ref", required=True)
    ap.add_argument("--case-csv", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    if a.output.exists():
        raise ValueError("OUTPUT_ALREADY_EXISTS")
    with a.case_csv.open() as f:
        dates = sorted({row["date"] for row in csv.DictReader(f)})
    cache, records = {}, []
    for day in dates:
        next_session = session_n_forward(datetime.fromisoformat(day).date(), 1)
        if next_session is None:
            raise ValueError("NEXT_SESSION_UNAVAILABLE")
        cutoff = datetime.combine(next_session, time(9, 30),
                                  ZoneInfo("America/New_York")).astimezone(ZoneInfo("UTC"))
        for path in PATHS:
            commit_line = git(a.repo, "log", "--first-parent", "--max-count=1",
                              "--format=%H|%cI", "--before=" + cutoff.isoformat(),
                              a.ref, "--", path).strip()
            record = {
                "price_origin_date": day, "research_decision_cutoff": cutoff.isoformat(),
                "artifact": path, "available_at": None, "delivered_at": None,
                "first_executable_price_at": None,
                "qualification": "RECORDED_VERSION_NOT_OBSERVED_ISSUANCE",
            }
            if not commit_line:
                records.append({**record, "status": "NO_VERSION_IN_AVAILABLE_HISTORY"})
                continue
            commit, committed_at = commit_line.split("|", 1)
            key = (commit, path)
            if key not in cache:
                raw = git(a.repo, "show", f"{commit}:{path}")
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    data = {"parse_status": "JSON_UNREADABLE"}
                cache[key] = (data, hashlib.sha256(raw.encode()).hexdigest(),
                              git(a.repo, "rev-parse", f"{commit}:{path}").strip())
            data, digest, blob = cache[key]
            radar = data.get("risk_radar") or {}
            alert = data.get("alert")
            selected = {
                "asof": data.get("asof", data.get("as_of", data.get("date"))),
                "source_session": data.get("source_session"),
                "built_at": data.get("built_at"),
                "generated_utc": data.get("generated_utc"),
                "observed_at": data.get("observed_at"), "produced_at": data.get("produced_at"),
                "state": data.get("state"), "verdict": data.get("verdict"),
                "score": data.get("score"), "data_state": data.get("data_state"),
                "risk_state": data.get("risk_state"),
                "radar": {k: radar.get(k) for k in
                          ("asof", "state", "ungated_state", "top_score", "alert", "can_force")},
                "measured_state": data.get("measured_state"),
                "hazard_summary": data.get("hazard_summary"),
                "legacy_alert": alert if isinstance(alert, bool) or alert is None
                                else {k: alert.get(k) for k in ("asof", "severity", "state", "score")},
            }
            records.append({
                **record, "status": "RECORDED", "version_commit": commit,
                "recorded_committer_time": committed_at, "blob_sha": blob,
                "content_sha256": digest, "source_fields": selected,
            })
    output = {
        "schema": "grey_deer.recorded_version_replay.v1",
        "source_ref": a.ref, "source_history_shallow": git(a.repo, "rev-parse", "--is-shallow-repository").strip(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "case_csv_sha256": hashlib.sha256(a.case_csv.read_bytes()).hexdigest(),
        "calendar_code_sha256": hashlib.sha256((ROOT / "lib/nyse_calendar.py").read_bytes()).hexdigest(),
        "assumptions": [
            "First-parent version reconstructed under recorded Git committer clocks.",
            "No push/ingestion/entitlement/paint/execution timestamp is inferred.",
            "Price census uses revised data; these native recorded messages remain a separate evidence layer.",
            "Next-session 09:30 New York is an analytical cutoff, not a verified executed trade.",
        ],
        "records": records,
    }
    a.output.write_text(json.dumps(output, sort_keys=True, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"records": len(records), "price_dates": len(dates),
                      "versions": len(cache), "missing": sum(r["status"] != "RECORDED" for r in records),
                      "output": str(a.output)}))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build the R33 integration candidate from pinned committed owner inputs.

This is a source integration rehearsal, not a deployed-feed receipt. The Macro
generator runs normally in an isolated output root. The unchanged Bonds renderer
receives its committed bond-health snapshot through its existing view-model
function; optional historical charts and alert rebuilding are deliberately
omitted. No source collection, event evaluation, alert writes or release occurs.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT_REF = "80f270c44bcdf11f5e71dacc05b11a0875a01d7f"
INPUTS = (
    "data/macro_snapshots/latest.json",
    "data/neuralweb/world_state.json",
    "data/regime/latest.json",
    "data/macro_snapshots/transitions.jsonl",
    "data/bonds/bond_health.json",
)
OPTIONAL_INPUTS = ("data/bonds/calibration.json",)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def prepare(output: Path, input_ref: str) -> dict:
    output = output.resolve()
    if output == ROOT or ROOT in output.parents:
        raise ValueError("Use an isolated output directory outside the source checkout.")
    output.mkdir(parents=True, exist_ok=True)
    marker = output / ".r33-integration-candidate"
    if any(output.iterdir()) and not marker.exists():
        raise ValueError("Refusing to reuse a nonempty directory without this runner's marker.")
    marker.write_text("R33 isolated candidate; never a production acceptance receipt.\n")
    input_sha = subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "--verify", input_ref + "^{commit}"], text=True
    ).strip()
    source_sha = subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
    ).strip()
    receipts = []
    for name in INPUTS + OPTIONAL_INPUTS:
        proc = subprocess.run(
            ["git", "-C", str(ROOT), "show", input_sha + ":" + name], capture_output=True
        )
        target = output / name
        if proc.returncode:
            if name in INPUTS:
                raise RuntimeError("Required committed owner input unavailable: " + name)
            target.unlink(missing_ok=True)
            receipts.append({"path": name, "state": "absent_at_pin"})
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(proc.stdout)
        blob = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", input_sha + ":" + name], text=True
        ).strip()
        receipts.append({"path": name, "git_blob": blob, "bytes": len(proc.stdout),
                         "sha256": sha(proc.stdout), "state": "committed_owner_input"})
    templates = output / "templates"
    if not templates.exists():
        templates.symlink_to(ROOT / "templates", target_is_directory=True)
    elif not templates.is_symlink() or templates.resolve() != ROOT / "templates":
        raise ValueError("Candidate templates must point at this source checkout.")
    sys.path.insert(0, str(ROOT))
    import pandas as pd
    from jinja2 import Environment, FileSystemLoader
    from lib import config
    from lib.pages import write_page
    from engine.i18n import tr, td
    from scripts import build_macro_context as macro
    from scripts import build_bonds as bonds

    cfg = deepcopy(config.load())
    cfg["storage"]["site_dir"] = "site"
    cfg["storage"]["data_dir"] = "data"
    data = output / "data"
    site = output / "site"
    site.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack:
        stack.enter_context(patch.object(config, "ROOT", output))
        stack.enter_context(patch.object(config, "load", lambda: cfg))
        stack.enter_context(patch.object(config, "data_dir", lambda: data))
        stack.enter_context(patch.object(config, "site_dir", lambda: site))
        if macro.main() != 0:
            raise RuntimeError("Existing Macro generator did not complete.")
        snap = json.loads((data / "bonds/bond_health.json").read_text())
        vm = bonds._vm(snap, pd.DataFrame(), bonds._load_calibration())
        asof = snap["as_of"]
        display_date = pd.Timestamp(asof).strftime("%b %d, %Y")
        compass = snap.get("bond_compass")
        xasset = snap.get("bond_cross_asset")
        xasset_vm = bonds._xasset_vm(xasset)
        tail, head = bonds._tailwind_counts(xasset_vm)
        agree_en, agree_zh = bonds._agree_band(
            ((compass or {}).get("duration") or {}).get("agreement")
        )
        cc_vm = bonds.build_corp_credit_vm(data_root=data)
        chart_keys = (
            "health", "curve_now", "spreads", "credit", "real", "move", "corr",
            "sovereign", "policy_path", "intl_yields", "tp_decomp", "xasset_betas",
        )
        env = Environment(loader=FileSystemLoader(str(templates)), autoescape=True)
        env.globals.update(tr=tr, td=td)
        ctx = dict(
            C=bonds.C, as_of=display_date, as_of_zh=bonds._fmt_asof_zh(asof),
            as_of_iso=asof, built=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            span="Historical charts omitted in source integration rehearsal",
            vm=vm, charts={key: "" for key in chart_keys}, credit_cycle=None,
            fed_path=snap.get("fed_path"), treasury_supply=None, usd_link=None,
            intl=snap.get("intl_bonds"), compass=compass, xasset=xasset, xasset_vm=xasset_vm,
            timeline=[], timeline_days=cfg["bonds"]["alerts"]["timeline_days"], n_alerts=0,
            cc_vm=cc_vm, glance=bonds._glance(vm), key_levels=[],
            hero=bonds._hero_pack(vm, display_date, (vm.get("health") or {}).get("phase_key")),
            changed=[], watching=bonds._watching(vm),
            div_card=bonds.divergence_card_state(
                cc_vm.get("divergence_ready"), cc_vm.get("divergence_ready_date"),
                cc_vm.get("divergence_last_obs"), asof,
            ),
            n_tailwind=tail, n_headwind=head, agree_en=agree_en, agree_zh=agree_zh,
        )
        html = env.get_template("bonds.html.j2").render(**ctx)
        write_page(site / "bonds.html", html)
    publication_bytes = (data / "macro_context/decision_workspaces.json").read_bytes()
    mirrored = (site / "macro-context-data/decision_workspaces.json").read_bytes()
    assert publication_bytes == mirrored
    pub = json.loads(publication_bytes)
    hub = json.loads((data / "macro_context/latest.json").read_text())
    assert set(hub) == {"asof", "macro_context_id", "n_transitions_14d", "headline_en", "headline_zh"}
    assert hub == pub["hub"]
    artifacts = {}
    for relative in ("bonds.html", "macro_context.html", "macro-context-data/decision_workspaces.json"):
        body = (site / relative).read_bytes()
        artifacts[relative] = {"bytes": len(body), "sha256": sha(body)}
    source_paths = [
        "scripts/build_macro_context.py", "templates/bonds.html.j2",
        "templates/_bonds_source_adapter.js.j2", "templates/_bonds_source_inspector.js.j2",
        "templates/_bonds_source_inspector.css.j2",
    ]
    report = {
        "schema": "r33.bonds_source_integration_build.v1",
        "acceptance": "BUILT_NOT_PROVEN",
        "kind": "isolated_candidate_from_committed_owner_inputs",
        "source_head_before_delta": source_sha,
        "input_commit": input_sha,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": receipts,
        "source_files": {name: sha((ROOT / name).read_bytes()) for name in source_paths if (ROOT / name).exists()},
        "publisher": pub["publication"],
        "hub_keys": sorted(hub),
        "data_site_bytes_identical": True,
        "artifacts": artifacts,
        "scope_limits": [
            "Existing Macro main ran with pinned JSON owner inputs, without auxiliary history charts.",
            "Existing Bonds template and view-model function used committed bond-health source; full Bonds main was not run.",
            "No historical chart rebuild, alert rebuild, data collection, event evaluation, source admission, saved research, monitoring or calibration.",
            "No deployment, live origin response, session entitlement proof or production acceptance.",
        ],
    }
    (output / "build-receipt.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--input-ref", default=DEFAULT_INPUT_REF)
    args = parser.parse_args()
    report = prepare(args.output_dir, args.input_ref)
    print(json.dumps({"acceptance": report["acceptance"], "input_commit": report["input_commit"],
                      "component_clocks": report["publisher"]["component_clocks"],
                      "artifacts": report["artifacts"]}, ensure_ascii=False))

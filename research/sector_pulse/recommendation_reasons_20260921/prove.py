"""Compare the unchanged policy and replay explanations on immutable theme evidence.

This does not publish data or run a nightly. Snapshot replay uses rounded exposed
inputs, so a mismatch with the stored verdict is disclosed, never overwritten.
"""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from engine import theme_scoring as candidate


def read_blob(ref: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{ref}:{path}"], cwd=ROOT)


def legacy_policy(ref: str):
    source = read_blob(ref, "engine/theme_scoring.py").decode()
    tree = ast.parse(source)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_reco")
    module = ast.Module(body=[fn], type_ignores=[])
    namespace = dict(vars(candidate))
    exec(compile(ast.fix_missing_locations(module), "frozen_legacy_reco", "exec"), namespace)
    return namespace["_reco"]


def policy_parity(ref: str) -> dict:
    old = legacy_policy(ref)
    labels = ("dominant", "emerging", "neutral", "fading", "deteriorating", "unknown")
    macros = (-.3, -.25, -.1, 0., .2, float("nan"))
    crowds = (0., .599, .6, .649, .65, .9, float("nan"))
    shapes = ({}, {"rs_pctile": .849}, {"rs_pctile": .85}, {"rs_pctile": .95},
              {"ext_abs": .5, "rs_pctile": .95}, {"ext_abs": 1.999}, {"ext_abs": 2.0})
    count = 0
    for label, macro, crowd, shape, sign, expansion in itertools.product(
            labels, macros, crowds, shapes, (-1, 0, 1), (False, True)):
        fp = {"long_sign": sign, **shape}
        tape = {"volhole": {"state": "EXPANSION_DOWN"}} if expansion else None
        before = old(label, macro, crowd, fp, tape=tape)
        after, _ = candidate._reco_decision(label, macro, crowd, fp, tape=tape)
        if before != after or candidate._reco(label, macro, crowd, fp, tape=tape) != before:
            raise AssertionError((label, macro, crowd, fp, tape, before, after))
        count += 1
    return {"cases": count, "mismatches": 0, "baseline_ref": ref,
            "baseline_function": "engine/theme_scoring.py:_reco"}


def replay(ref: str) -> tuple[dict, dict]:
    raw = read_blob(ref, "site/basketdata/baskets.json")
    payload = json.loads(raw)
    after = deepcopy(payload)
    rows = after["theme_intel"]["themes"]
    records, unmatched = [], []
    for row in rows:
        fp = {key: row.get(key) for key in ("long_sign", "rs_pctile", "ext_abs")}
        parts = row.get("components") or {}
        macro = parts.get("macro") or 0.0
        crowd = parts.get("crowding")
        if crowd is None:
            unmatched.append({"id": row["id"], "reason": "missing_crowding_input"})
            continue
        base, reason = candidate._reco_decision(row["label"], macro, crowd, fp,
                                                row.get("mtf"), row.get("tape"))
        final = "hold" if (row.get("regime_demoted") or row.get("chase_demoted")) else base
        if final != row["reco"]:
            unmatched.append({"id": row["id"], "stored": row["reco"], "replayed": final,
                              "reason": "rounded_snapshot_does_not_reproduce_verdict"})
            continue
        explanation = candidate._recommendation_explanation(
            final, reason, regime_demoted=bool(row.get("regime_demoted")),
            chase_demoted=bool(row.get("chase_demoted")),
            clean_entry=((row.get("textures") or {}).get("clean_entry") or {}).get("flag"))
        records.append({"id": row["id"], "name": row.get("name"), "reco": row["reco"],
                        "before_en": row.get("reco_why_en"), "after": explanation,
                        "base_reason": reason})
        row.update(reco_why_en=explanation["en"], reco_why_zh=explanation["zh"],
                   reco_reason_code=explanation["code"], reco_base_reason_code=reason)
    # All state/price/rank/permission data must remain identical. Only explanatory
    # fields may change, including in the JSON later handed to the real renderer.
    stripped = deepcopy(after)
    original_rows = {r["id"]: r for r in payload["theme_intel"]["themes"]}
    for row in stripped["theme_intel"]["themes"]:
        for key in ("reco_reason_code", "reco_base_reason_code"):
            row.pop(key, None)
        for key in ("reco_why_en", "reco_why_zh"):
            if key in original_rows[row["id"]]:
                row[key] = original_rows[row["id"]][key]
            else:
                row.pop(key, None)
    assert stripped == payload
    report = {"source_ref": ref, "source_path": "site/basketdata/baskets.json",
              "source_sha256": hashlib.sha256(raw).hexdigest(),
              "source_as_of": payload["theme_intel"]["as_of"],
              "candidate_engine_sha256": hashlib.sha256(Path(candidate.__file__).read_bytes()).hexdigest(),
              "policy_parity": policy_parity(ref), "themes": len(rows),
              "replayed": len(records), "unmatched": unmatched,
              "all_non_explanation_data_unchanged": True, "records": records,
              "limitations": ["Rounded stored inputs, not a full nightly rebuild.",
                              "Not live market or deployed-browser proof.",
                              "No ranking, entry permission, portfolio or return claim."]}
    return report, after


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report, payload = replay(args.source_ref)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "proof.json").write_text(json.dumps(report, indent=2) + "\n")
    (args.out / "candidate-baskets.json").write_text(json.dumps(payload, ensure_ascii=False))
    print(json.dumps({k: report[k] for k in ("source_as_of", "policy_parity", "themes",
                                            "replayed", "unmatched", "all_non_explanation_data_unchanged")}, indent=2))


if __name__ == "__main__":
    main()

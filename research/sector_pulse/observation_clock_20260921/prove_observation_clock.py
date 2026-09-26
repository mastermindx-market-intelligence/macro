"""Reproduce pulse clock defects from immutable Git inputs; never query live data.

Run from the repository with --source-ref COMMIT --output PATH. This is an
observation-clock proof, not a point-in-time availability or performance study.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import types
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import pandas as pd
from engine import sector_pulse as candidate
from engine.theme_scoring import _extended, _reco


def prove(source_ref: str) -> dict:
    def read(path: str) -> bytes:
        return subprocess.check_output(["git", "show", f"{source_ref}:{path}"], cwd=ROOT)

    paths = ["engine/sector_pulse.py", "site/basketdata/baskets.json",
             "data/signal_archive/baskets.parquet"]
    raw = {path: read(path) for path in paths}
    incumbent = types.ModuleType("sector_pulse_incumbent")
    exec(compile(raw[paths[0]], paths[0], "exec"), incumbent.__dict__)
    ti = json.loads(raw[paths[1]])["theme_intel"]
    archive = pd.read_parquet(io.BytesIO(raw[paths[2]]))
    with patch("engine.signal_archive.load_archive", return_value=archive), \
         patch.object(incumbent, "_load_theme_intel", return_value=ti), \
         patch.object(candidate, "_load_theme_intel", return_value=ti), \
         patch.object(incumbent, "_heat_calibration", return_value={}), \
         patch.object(candidate, "_heat_calibration", return_value={}):
        before = incumbent.build_pulse("us")
        after = candidate.build_pulse("us")
    if before is None or after is None:
        raise RuntimeError("Both real-source projections must be available")
    authority = ("id", "rank", "score", "label", "reco")
    unchanged = [[r.get(k) for k in authority] for r in before["themes"]] == [
        [r.get(k) for k in authority] for r in after["themes"]]
    if not unchanged:
        raise AssertionError("Pulse correction changed canonical recommendation authority")
    columns = ("id", "rank", "score", "reco", "heat", "rank_delta_1d",
               "rank_delta_5d", "score_delta_5d")
    selected = {"ai_semiconductors", "cybersecurity", "mag7", "memory_storage"}
    def project(payload: dict) -> list[dict]:
        return [{k: row.get(k) for k in columns} for row in payload["themes"]
                if row["id"] in selected]
    legacy = {"long_sign": 1, "rs_pctile": 0.95}
    alternative = {**legacy, "ext_abs": 0.5}
    return {
        "schema": "sector_pulse_observation_clock_proof.v1",
        "source_ref": source_ref,
        "source_sha256": {path: hashlib.sha256(value).hexdigest() for path, value in raw.items()},
        "candidate_engine_sha256": hashlib.sha256(Path(candidate.__file__).read_bytes()).hexdigest(),
        "theme_as_of": ti["as_of"], "archive_last_as_of": str(archive["asof"].max()),
        "authority_fields_unchanged": unchanged, "n_themes": len(after["themes"]),
        "history": after["history"], "before": project(before), "after": project(after),
        "relative_strength_extension_discriminator": {
            "synthetic_only": True,
            "legacy": {"inputs": legacy, "extended": _extended(legacy, 0.85),
                       "reco": _reco("dominant", 0.2, 0.1, legacy)},
            "absolute": {"inputs": alternative, "extended": _extended(alternative, 0.85),
                         "reco": _reco("dominant", 0.2, 0.1, alternative)},
            "authority_changed": False,
        },
        "limitations": ["Committed September 18 observation, not September 21 live evidence.",
                        "No logged-at/PIT replay or forward-return claim.",
                        "Calibration enrichment omitted identically from both projections.",
                        "The extension discriminator is not a measured US price or a promoted strategy."],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = prove(args.source_ref)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("theme_as_of", "archive_last_as_of",
                                           "authority_fields_unchanged", "history", "after")}, indent=2))


if __name__ == "__main__":
    main()

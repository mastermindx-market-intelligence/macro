#!/usr/bin/env python3
"""Build an industry-context research sidecar from existing native source artifacts.

This is an explicit foreground research command, not a collector or scheduler.
Source mode reads one immutable public repository revision, verifies Git blob
identities, and keeps raw vendor bytes in memory. It never overwrites live board,
K3E sources, rank, trading policy or site outputs. Optional full enriched board
stays in the supplied private output directory; only aggregate proof is intended
for source publication.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import re
import sys

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from engine.k3e_expectation_surface import inspect_expectation_surface
from engine.prophet_industry_context_sources import build_board_context, LANES

REPOSITORY = "mastermindx-market-intelligence/macro"
PATHS = {
    "board": "site/factordata/us_standouts.json",
    "industry_ranks": "data/stage_analysis/industry_ranks.json",
    "taxonomy": "data/stage_analysis/backfill/equitydesk_overview.parquet",
    "revisions": "data/revisions/latest.parquet",
    "observations": "data/revisions/expectation_observations.parquet",
    "attempts": "data/revisions/expectation_attempts.parquet",
    "aliases": "data/reference/vendor_aliases.parquet",
}


def read_source(session: requests.Session, revision: str, key: str) -> tuple[bytes, dict]:
    path = PATHS[key]
    meta = session.get(f"https://api.github.com/repos/{REPOSITORY}/contents/{path}",
                       params={"ref": revision}, timeout=30)
    meta.raise_for_status()
    descriptor = meta.json()
    if descriptor.get("type") != "file" or descriptor.get("size", 0) > 100_000_000:
        raise ValueError("unsupported source shape or size")
    response = session.get(f"https://raw.githubusercontent.com/{REPOSITORY}/{revision}/{path}", timeout=60)
    response.raise_for_status()
    raw = response.content
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if blob != descriptor.get("sha") or len(raw) != descriptor.get("size"):
        raise ValueError("source bytes do not match immutable Git blob")
    return raw, {"path": path, "git_blob_id": blob, "sha256": hashlib.sha256(raw).hexdigest(),
                 "bytes": len(raw), "source_revision": revision}


def parquet(raw: bytes, *, filters=None, columns=None) -> pd.DataFrame:
    # Match the native inspection CLI's synchronous nullable decoding.
    frame = pd.read_parquet(io.BytesIO(raw), engine="pyarrow", use_threads=False,
                            pre_buffer=False, filters=filters, columns=columns)
    return frame


def run(revision: str, output: Path, *, native_k3e_limit: int = 5, write_enriched_board: bool = False) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("full immutable source revision required")
    if not 0 <= native_k3e_limit <= 20:
        raise ValueError("bounded native inspection limit required")
    session = requests.Session()
    raw, provenance = {}, {}
    for key in ("board", "industry_ranks", "taxonomy", "revisions"):
        raw[key], provenance[key] = read_source(session, revision, key)
    board, industry = json.loads(raw["board"]), json.loads(raw["industry_ranks"])
    taxonomy = parquet(raw["taxonomy"], columns=["ticker", "region", "gics_industry"])
    revisions = parquet(raw["revisions"])
    as_of = board["as_of"]
    # A date-tagged snapshot is not granted an invented historical publication clock.
    cutoff = as_of + "T23:59:59Z"
    candidates = sorted({row["ticker"] for lane in LANES for row in board.get(lane, [])
                         if isinstance(row, dict) and isinstance(row.get("ticker"), str)})
    native = {}
    native_summary = {}
    selected = candidates[:native_k3e_limit]
    if selected:
        for key in ("observations", "attempts", "aliases"):
            raw[key], provenance[key] = read_source(session, revision, key)
        observations = parquet(raw["observations"], filters=[("ticker_compat", "in", selected)])
        attempts = parquet(raw["attempts"], filters=[("ticker_compat", "in", selected)])
        aliases = parquet(raw["aliases"])
        records = lambda frame: frame.astype(object).where(pd.notna(frame), None).to_dict("records")
        obs_records, att_records, alias_records = records(observations), records(attempts), records(aliases)
        native_provenance = {"source_revision": revision, "inputs": {
            PATHS[key]: {k: provenance[key][k] for k in ("git_blob_id", "sha256")}
            for key in ("observations", "attempts", "aliases")}}
        for ticker in selected:
            result = inspect_expectation_surface(obs_records, att_records,
                source_provenance=native_provenance, ticker=ticker, metric="EPS", horizon="+1y",
                as_of=cutoff, composed_at=cutoff, identity_aliases=alias_records)
            native[ticker] = {"expectation": result}
            payload = result.get("semantic_payload", {})
            native_summary[ticker] = {
                "query_identity": payload.get("query_identity"),
                "latest_status": payload.get("latest_captured_snapshot", {}).get("status"),
                "normalized_status": payload.get("normalized_baseline", {}).get("status"),
                "identity_gate": payload.get("identity_gate"),
                "period_continuity": payload.get("period_continuity"),
            }
        print("NATIVE_K3E_READ", len(selected), "tickers", len(observations), "source observations", flush=True)
    refs = {key: f"{revision}:{PATHS[key]}@{provenance[key]['git_blob_id']}"
            for key in ("board", "industry_ranks", "taxonomy", "revisions")}
    result = build_board_context(board, industry, taxonomy, revisions, source_refs=refs, k3e_inputs=native)
    groups = result["context"]["groups"]
    diagnostics = Counter()
    coupling = Counter()
    for group in groups.values():
        expectations = group["expectations"]
        diagnostics.update(x["status"] for x in expectations.get("diagnostics", []))
        coupling.update(expectations.get("k3e_component_states", {}))
    covered = sum(group["expectations"].get("status") == "OBSERVED_RESEARCH_CONTEXT" for group in groups.values())
    proof = {"schema": "prophet.industry_context_consumer_proof.v1", "as_of": as_of,
             "source_revision": revision, "source_inputs": provenance,
             "source_board_definition": board.get("board_definition"),
             "coverage": result["coverage"], "industry_groups": len(groups),
             "groups_with_at_least_half_eps_drift_coverage": covered,
             "membership": result["identity"], "member_observation_states": dict(diagnostics),
             "native_k3e_inspections": native_summary, "coupling_states_in_eligible_members": dict(coupling),
             "native_board_fields_preserved": result["preserved_native_board"],
             "financial_influence": False, "forecast_probabilities_emitted": False,
             "publication": "LOCAL_RESEARCH_CONSUMER_NOT_PRODUCTION_DEPLOYMENT",
             "limitations": ["Current reconstructed taxonomy; issuer identity and historical membership are not certified.",
                             "Latest revision snapshots may postdate the board cutoff and are then excluded.",
                             "Legacy estimate drifts are observed context, not normalized K3E admission.",
                             "Native GICS coordinates are not passed into a French49 historical forecast model.",
                             "A source artifact read does not establish current production-page freshness."]}
    output.mkdir(parents=True, exist_ok=True)
    (output / "industry_context_consumer_proof.json").write_text(json.dumps(proof, indent=2, allow_nan=False) + "\n")
    (output / "industry_context_read.json").write_text(json.dumps(result["context"], indent=2, allow_nan=False) + "\n")
    if write_enriched_board:
        (output / "industry_context_enriched_board.json").write_text(json.dumps(result["board"], indent=2, allow_nan=False) + "\n")
    print("CONSUMER_PROOF", json.dumps({"as_of": as_of, "coverage": proof["coverage"],
              "groups": len(groups), "covered_groups": covered, "member_states": dict(diagnostics),
              "native_k3e_queries": len(native_summary), "coupling_states": dict(coupling),
              "native_fields_preserved": True}), flush=True)
    return proof


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--native-k3e-limit", type=int, default=5)
    parser.add_argument("--write-enriched-board", action="store_true")
    args = parser.parse_args()
    run(args.source_revision, args.output, native_k3e_limit=args.native_k3e_limit,
        write_enriched_board=args.write_enriched_board)

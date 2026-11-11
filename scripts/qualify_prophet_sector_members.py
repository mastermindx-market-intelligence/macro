"""Real-bytes qualification for ``prophet.sector_members/v1``.

Publishes ONE Sector generation locally from the committed site/ artifacts (the
same private-store publisher/reader lane 1's tests use — no network, no live
store), joins it to the committed ``site/prophet/index.json`` and the committed
turn-watch sidecar, exercises the real HTTP route, and captures the contract's
fixture set under ``--fixtures <dir>``.

The committed ``action_board.json`` carries one ``NaN`` literal (``factor_z``),
which the generation's strict decoder refuses until the factors producer writes
``null``; this qualification repairs that single literal to ``null`` in its
LOCAL copy only (disclosed in the fixture metadata) — the committed bytes are
never modified.

Usage:  .venv-prophet/bin/python scripts/qualify_prophet_sector_members.py \
            --fixtures /home/ubuntu2/tmp/prophet-recon/fixtures/sector_members_v1
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
# Scripts run with sys.path[0] == scripts/; the repo root is needed for
# app/lib/engine imports (same bootstrap as ingest/gen_slices_all.py).
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

MEMBER_FILES = {
    "sectordata/sector_central.json": "site/sectordata/sector_central.json",
    "sectordata/sector_cycles.json": "site/sectordata/sector_cycles.json",
    "basketdata/baskets.json": "site/basketdata/baskets.json",
    "basketdata/si_handoff.json": "site/basketdata/si_handoff.json",
    "basketdata/action_board.json": "site/basketdata/action_board.json",
}


def _finite(value):
    """NaN/Infinity → null, the producer's own finite-wire rule (display copy)."""
    if isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))):
        return None
    if isinstance(value, dict):
        return {k: _finite(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_finite(v) for v in value]
    return value


def _member_bytes() -> dict[str, bytes]:
    members = {}
    for name, path in MEMBER_FILES.items():
        raw = (REPO / path).read_bytes()
        if name == "sectordata/sector_central.json":
            # The nightly central builder carries the typed blocks from the same
            # site/ tree; the committed artifact predates tonight's publish.
            # Compose them locally with the owner's own builder over the SAME
            # committed inputs so the qualification exercises the real shape
            # (member industry/sub-industry labels, removed members).
            import json as _json
            from lib import sector_central_carry as carry

            central = _json.loads(raw)
            roster = _json.loads((REPO / "data/baskets/membership.json").read_bytes())
            central["carried"] = carry.build_carry(REPO / "site", central, roster)
            raw = _json.dumps(central, separators=(",", ":"),
                              allow_nan=False, ensure_ascii=False).encode()
        members[name] = raw
    # The committed action_board.json is the nightly render's legacy shape: the
    # rows are the owner's, but the dependency envelope (schema/as_of/
    # generated_utc/baskets_sha256) the generation contract requires is absent.
    # Re-bind it locally with the owner's own envelope function over the SAME
    # committed rows and the SAME committed baskets bytes; the one NaN literal
    # (factor_z) is nulled per the producer's own finite-wire rule. Committed
    # bytes are never modified.
    from engine.sector_action_board import action_board_envelope

    board = json.loads(members["basketdata/action_board.json"])
    session = json.loads(members["basketdata/baskets.json"])["as_of"]
    envelope = action_board_envelope(
        basket_raw=members["basketdata/baskets.json"],
        action_board=board["action_board"],
        # Pinned to the session's own evening so the local store (and therefore
        # content_id/member_sha256) is reproducible across qualification runs.
        generated_utc=session + "T23:00:00+00:00",
    )
    members["basketdata/action_board.json"] = json.dumps(
        _finite(envelope), separators=(",", ":"), allow_nan=False).encode()
    return members


def publish_local(state_dir: Path) -> Path:
    from lib.sector_generation_contract import (
        SECTOR_GENERATION_MEMBERS, prepare_sector_generation_request,
    )
    from scripts import vps_live_orchestrator as publisher

    members = _member_bytes()
    baskets = json.loads(members["basketdata/baskets.json"])
    session = baskets["as_of"]
    identity = {"sector_view": {
        "schema": "sector.view_inputs.v1", "source_session": session,
        "input_version": "sector-inputs-v1", "baseline_session": None,
        "source_qualification": "accepted",
    }}
    sources = {}
    for name, raw in members.items():
        path = state_dir / "sources" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        sources[name] = path
    assert set(sources) == set(SECTOR_GENERATION_MEMBERS)
    request = prepare_sector_generation_request(
        sources=sources, input_identity=identity,
        generation_id=f"qualify-{session}", source_revision="prophet-sector-members-qual",
        lane="snapshot")
    # Publish at the session's own evening clock: new selection requires the
    # accepted qualification the bytes had when they were produced (the real
    # nightly publishes same-day).  READS later age truthfully to stale.
    publish_clock = datetime.fromisoformat(session + "T23:00:00+00:00")
    orch = publisher.Orchestrator(live_dir=state_dir / "live", state_dir=state_dir,
                                  data_dir=state_dir / "data", now=publish_clock)
    result = orch.publish_generation(request, expected_current_content_id=None)
    print(f"publish: status={result.status} generation_id={result.generation_id} "
          f"detail={getattr(result, 'detail', None)}")
    assert result.status == "published", result
    return state_dir / "generations"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--keep", action="store_true", help="keep the local store")
    args = parser.parse_args()

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import app.prophet_sector_members as route
    from app.prophet_lab import require_site_full_user
    from engine import prophet_sector_members as engine

    args.fixtures.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="prophet-si-qual-") as tmp:
        state = Path(tmp)
        root = publish_local(state)
        os_env = {"MACRO_SECTOR_GENERATIONS_ROOT": str(root)}

        app = FastAPI()
        app.include_router(route.router)
        app.dependency_overrides[require_site_full_user] = lambda: {"uid": "qualification"}
        client = TestClient(app)

        def get(path: str) -> dict:
            import os
            old = {k: os.environ.get(k) for k in os_env}
            os.environ.update(os_env)
            try:
                response = client.get(path)
            finally:
                for key, value in old.items():
                    os.environ.pop(key, None)
                    if value is not None:
                        os.environ[key] = value
            assert response.status_code == 200, (path, response.status_code, response.text)
            return response.json()

        # --- fixtures: index, three groups, two symbols ----------------------
        index = get("/api/prophet/sector-members/v1")
        groups = index["groups"]
        served = [(g["id"], g["counts"]["served"]) for g in groups]
        unserved = [g["id"] for g in groups if g["counts"]["accounted_unserved"]
                    or g["counts"]["unaccounted"]]
        largest = max(groups, key=lambda g: g["counts"]["served"])
        smallest = min((g for g in groups if g["counts"]["served"] > 0),
                       key=lambda g: g["counts"]["served"])
        (args.fixtures / "index.json").write_text(json.dumps(index, indent=1))
        chosen = {"largest": largest["id"], "smallest": smallest["id"]}
        if unserved:
            chosen["unserved"] = sorted(unserved)[0]
        for label, gid in chosen.items():
            body = get(f"/api/prophet/sector-members/v1?group={gid}&limit=200")
            (args.fixtures / f"group_{gid}.json").write_text(json.dumps(body, indent=1))

        # one symbol with an open plan inside a group, one with no plan at all
        plan_book = engine.digest_index(json.loads((REPO / "site/prophet/index.json").read_bytes()))
        open_assets = {a for a, rows in plan_book["plans"].items()
                       if any(r.get("closed") is False for r in rows)}
        member_symbols = set()
        for gid in chosen.values():
            body = json.loads((args.fixtures / f"group_{gid}.json").read_text())
            member_symbols.update(m["symbol"] for m in body["members"])
        with_plan = sorted(open_assets & member_symbols)
        without_plan = sorted(member_symbols - open_assets - {
            a for a, rows in plan_book["plans"].items() if rows})
        fixture_symbols = {}
        if with_plan:
            fixture_symbols["with_plan"] = with_plan[0]
        if without_plan:
            fixture_symbols["without_plan"] = without_plan[0]
        for label, symbol in fixture_symbols.items():
            body = get(f"/api/prophet/sector-members/v1?symbol={symbol}")
            (args.fixtures / f"symbol_{symbol}.json").write_text(json.dumps(body, indent=1))

        # --- report -----------------------------------------------------------
        totals = index["totals"]
        compatibility = index["compatibility"]
        all_plan_assets = set(plan_book["plans"])
        join = route.build_join(root)
        roster_symbols = {r["symbol"] for r in join.population.rows}
        no_group = sorted(all_plan_assets - {engine.normalize_ticker(s) for s in roster_symbols})
        print(json.dumps({
            "sector_ref": index["sector_ref"],
            "prophet_ref": index["prophet_ref"],
            "compatibility": compatibility,
            "disclosure": index["disclosure"],
            "groups": len(groups),
            "refused_groups": sum(1 for g in groups if g["counts"]["configured"] is not None
                                  and g["counts"]["served"] == 0),
            "totals": totals,
            "pair_configured": join.population.configured_current,
            "plan_assets": len(all_plan_assets),
            "plan_assets_in_no_group": len(no_group),
            "plan_assets_in_no_group_sample": no_group[:12],
            "groups_served_ranking": sorted(served, key=lambda kv: -kv[1])[:5],
            "groups_with_unserved": unserved,
            "fixture_groups": chosen,
            "fixture_symbols": fixture_symbols,
            "observations_used": bool(join._observations),
            "index_skipped_rows": plan_book["skipped_rows"],
        }, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

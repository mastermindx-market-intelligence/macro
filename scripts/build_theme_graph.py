"""Materialize the GMI theme graph — nodes, edges, evidence (masterplan §4.1, W1b).

TWO MODES.

``--backfill`` (one-shot, era=reconstruction)
    Builds the whole graph from the live membership documents, the crosswalk and the
    THS concept map, and stamps every row ``era="reconstruction"`` with ``belief_time``
    = the run's own date. It refuses to run over a populated edge store unless
    ``--force-backfill`` is passed: a second reconstruction would append a whole
    duplicate history under a new belief_time and make the store's own diff meaningless.

default (nightly, era=observed)
    Recomputes tonight's view, diffs it against the stored latest-belief view, and
    appends ONLY what changed. Lane-gated: ledger writes require ``COLLECT_LANE=nightly``
    (fail-closed, defaultless). Off-lane the whole computation still runs and its
    summary is logged — a render lane computes and discards, exactly like every other
    ledger here.

Both modes also re-derive the CAPABILITY side-car (W3A §9.3) — never a node column,
because node rows are write-once and a capability written onto one would be a ratchet
that outlived every later substrate improvement — and both pass through the source-family
SHRINK WALL: a build that would close more than a quarter of a family's live memberships
refuses unless ``--allow-source-shrink <family>`` says the restructure is real. That wall
sits on the write path rather than the refresh path on purpose: a hand-edited input never
goes near a refresh run, and in an append-only store its closures are permanent.

Non-fatal by construction: this is a display-tier product data plane (all six synapse
authority booleans false). A failure here degrades context, never a decision, so the
nightly step must not take the collect lane down with it.

Run: python -m scripts.build_theme_graph [--backfill] [--force-backfill]
     [--allow-source-shrink FAMILY]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import basket_membership_pit  # noqa: E402
from engine.theme_graph import materialize, probation, store  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("build_theme_graph")

_WITNESS_MARKER = "theme_graph_meta_written "
_WITNESS_SOURCES = (
    "scripts/build_theme_graph.py", "scripts/check_theme_graph_contracts.py",
    "scripts/ci/daily_engine_regional_desk_builders.sh", ".github/workflows/daily.yml",
)
_WITNESS_OUTPUTS = (
    "nodes.parquet", "node_lifecycle.parquet", "edges.parquet", "evidence.parquet",
    "capability.parquet", "identity_resolution.parquet", "probation/proposals.jsonl",
)


def _witness_hash(path: Path) -> dict:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"sha256": digest.hexdigest(), "bytes": path.stat().st_size}


def _emit_meta_write_receipt(meta: dict, materialization_computed_at: str) -> None:
    """A post-write diagnostic, never a replacement for either generation clock."""
    try:
        receipt = {
            "witness_id": os.environ.get("THEME_GRAPH_WITNESS_ID"),
            "meta_computed_at": meta["computed_at"],
            "materialization_computed_at": materialization_computed_at,
            "meta_sha256": _witness_hash(store.meta_path())["sha256"],
            **{key: meta[key] for key in ("lane", "mode", "era", "belief_time")},
        }
        print(_WITNESS_MARKER + json.dumps(receipt, sort_keys=True), flush=True)
    except Exception:  # diagnostics cannot change a completed graph write
        log.exception("theme graph metadata receipt unavailable")


def start_nightly_witness() -> str:
    """Called by the existing builder band; stdout is only its fresh scratch path."""
    try:
        identity = {key: os.environ.get(key) for key in (
            "GITHUB_REPOSITORY", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT",
            "GITHUB_EVENT_NAME", "GITHUB_JOB", "GITHUB_SHA", "GITHUB_WORKFLOW_REF",
        )}
        run_id, attempt, job = (identity[key] or "" for key in (
            "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_JOB"))
        if not (run_id.isdigit() and attempt.isdigit()
                and re.fullmatch(r"[A-Za-z0-9_-]+", job)):
            raise ValueError("missing or invalid run/attempt/job identity")
        directory = Path(tempfile.mkdtemp(
            prefix=f"theme-graph-witness-{run_id}-{attempt}-{job}-",
            dir=os.environ["RUNNER_TEMP"]))
        root = Path(__file__).resolve().parents[1]
        errors = [f"missing_identity:{key}" for key, value in identity.items() if not value]
        try:
            head = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True,
                stderr=subprocess.DEVNULL).strip()
        except (OSError, subprocess.CalledProcessError):
            head = None
            errors.append("actual_head_unavailable")
        sources = {}
        for name in _WITNESS_SOURCES:
            try:
                sources[name] = _witness_hash(root / name)
            except OSError:
                errors.append(f"source_unavailable:{name}")
        manifest = {
            "schema": "theme_graph_nightly_witness/v1",
            "capture_status": "incomplete", "acceptance": "not_evaluated",
            "witness_id": directory.name, "started_at": datetime.now(timezone.utc).isoformat(),
            "run_identity": identity, "actual_head_sha": head,
            "source_files": sources, "errors": errors,
        }
        (directory / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        # Only this freshly created directory can become the workflow's upload input.
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write(f"theme_graph_witness={directory}\n")
        return str(directory)
    except Exception:  # retention is advisory, just like the existing band
        log.exception("theme graph witness start unavailable")
        return ""


def finish_nightly_witness(directory: str, band_dir: str) -> None:
    """Retain only this owner's receipts before the unrelated parallel barrier."""
    if not directory:
        return
    try:
        target, band = Path(directory), Path(band_dir)
        manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
        errors = manifest["errors"]
        files = {}
        for slug in ("theme_graph", "theme_graph_guard"):
            for suffix in ("log", "rc", "sec"):
                name = f"{slug}.{suffix}"
                try:
                    shutil.copyfile(band / name, target / name)
                    files[name] = _witness_hash(target / name)
                    if suffix == "rc" and (target / name).read_text().strip() != "0":
                        errors.append(f"nonzero_or_invalid_rc:{slug}")
                    if suffix == "sec" and not (target / name).read_text().strip().isdigit():
                        errors.append(f"invalid_seconds:{slug}")
                except OSError:
                    errors.append(f"receipt_unavailable:{name}")
        meta_path = store.meta_path()
        try:
            shutil.copyfile(meta_path, target / "_meta.json")
            files["_meta.json"] = _witness_hash(target / "_meta.json")
            meta = json.loads((target / "_meta.json").read_text(encoding="utf-8"))
            lines = (target / "theme_graph.log").read_text(encoding="utf-8").splitlines()
            markers = [json.loads(line[len(_WITNESS_MARKER):]) for line in lines
                       if line.startswith(_WITNESS_MARKER)]
            if len(markers) != 1:
                errors.append("post_write_marker_missing_or_ambiguous")
            else:
                marker = markers[0]
                manifest["post_write_receipt"] = marker
                if (marker.get("witness_id") != manifest["witness_id"]
                        or marker.get("meta_sha256") != files["_meta.json"]["sha256"]
                        or marker.get("meta_computed_at") != meta.get("computed_at")
                        or any(marker.get(key) != meta.get(key)
                               for key in ("lane", "mode", "era", "belief_time"))):
                    errors.append("post_write_marker_metadata_mismatch")
        except (OSError, ValueError, TypeError):
            errors.append("metadata_or_post_write_marker_unreadable")
        # The native guard is advisory: rc=0 alone does not mean no contract breach.
        guard = target / "theme_graph_guard.log"
        if guard.exists() and re.search(r"::(?:warning|error)\b", guard.read_text()):
            errors.append("guard_warning_or_error")
        outputs = {}
        for name in _WITNESS_OUTPUTS:
            try:
                outputs[name] = _witness_hash(meta_path.parent / name)
            except OSError:
                errors.append(f"graph_output_unavailable:{name}")
        manifest.update(
            files=files, graph_output_files=outputs,
            finished_at=datetime.now(timezone.utc).isoformat(),
            capture_status="incomplete" if errors else "complete")
        pending = target / "manifest.pending.json"
        pending.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
        pending.replace(target / "manifest.json")
    except Exception:  # initial manifest stays incomplete if final capture fails
        log.exception("theme graph witness finish unavailable")


def _newest_raw_snapshot() -> tuple[str, dict] | None:
    """The newest RAW 同花顺 dump, classified by the seeder's own discriminator.

    The snapshots directory is mixed-shape (raw vendor dumps and byte-copies of
    membership.json share it), so the shape question has exactly one owner:
    ``scripts.seed_china_ths_baskets.classify_snapshot_shape``. Importing it beats
    re-deriving the rule here — two copies of a shape rule is how the two halves drift
    apart and the graph starts "corroborating" a membership against itself.
    """
    try:
        from scripts import seed_china_ths_baskets as seed  # noqa: PLC0415
        raws = seed.raw_snapshots()
    except Exception as exc:  # noqa: BLE001 — corroboration is additive, never fatal
        log.warning("no raw THS snapshot available (%s) — THS memberships will carry "
                    "their membership-document receipt only", exc)
        return None
    if not raws:
        log.info("no raw THS snapshot on disk — THS memberships carry their "
                 "membership-document receipt only")
        return None
    return raws[-1]


def _capability_counts(rows: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in rows:
        key = str(r.get("capability"))
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items()))


def _identity_resolution_state_counts(rows: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in rows:
        key = str(r.get("resolution_state"))
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items()))


def _retired_node_ids() -> frozenset[str]:
    """Node_ids whose latest node_lifecycle status is retired/merged (V4-D2B3, R-A6).

    Read here — the impure orchestrator — and handed to materialize.build() as a plain
    frozenset; materialize itself reads no store (purity, R-A6). An empty/absent
    lifecycle table (pre-correction checkouts) yields an empty set, a no-op.
    """
    lifecycle = store.read_node_lifecycle(latest=True)
    if lifecycle.empty:
        return frozenset()
    retired = lifecycle[lifecycle["status"].isin(store.RETIRED_LIKE_STATUSES)]
    return frozenset(str(n) for n in retired["node_id"])


def _relation_event_sources() -> tuple[Path, Path]:
    """Separate versioned owner input; the v1 proposal queue stays unchanged."""
    return (store.probation_path().parent / "relation_events.v2.jsonl",
            Path(__file__).resolve().parent.parent / "config/theme_crosswalk.yml")


def _relation_action_owner_reader():
    """Chairman gate #5 (2026-10-06): the probation owner's own ledger is the sole action authority; read-only resolver, fails closed."""
    return probation.RelationActionOwnerReader(_relation_event_sources()[0])


def run(*, backfill: bool, force_backfill: bool,
        allow_source_shrink: tuple[str, ...] = ()) -> int:
    lane = store.collect_lane()
    era = "reconstruction" if backfill else "observed"
    try:
        store.preflight_existing_stores()
    except store.GraphIntegrityError as exc:
        log.error("theme graph prior-state integrity refusal: %s", exc)
        return 1
    stored = store.read_edges(latest_belief=True)

    if backfill and not stored.empty and not force_backfill:
        log.error("edges.parquet already holds %d edges — refusing a second backfill. "
                  "A repeat reconstruction appends a duplicate history under a new "
                  "belief_time and the store can no longer say what changed. Pass "
                  "--force-backfill only if that is genuinely what you want.", len(stored))
        return 1

    try:
        ths_history = basket_membership_pit.read_history(
            basket_membership_pit.SUITE_THS, strict=True, include_collection_records=True)
    except Exception as exc:  # noqa: BLE001 — corrupt owner state must fail closed
        log.error("theme graph: THS PIT history is present but unreadable (%s) — "
                  "refusing to publish an empty-history interpretation", exc)
        return 1
    view = materialize.build(era=era, raw_snapshot=_newest_raw_snapshot(),
                             ths_history=ths_history,
                             retired_node_ids=_retired_node_ids())
    ths_plane = view.local_plane.get("build_ths_plane")
    if isinstance(ths_plane, dict) and ths_plane.get("error"):
        log.error("theme graph: THS association plane failed (%s) — refusing to "
                  "publish a graph with silently missing canonical joins",
                  ths_plane["error"])
        return 1
    # BLOCKER 3: build_ths_membership_history is now the SOLE producer of THS
    # MEMBER_OF edges (build_family(THS_SUITE) is deliberately skipped). A build
    # that failed to produce that plane must not silently look identical to one
    # that legitimately produced zero PIT rows — fail the build outright rather
    # than let materialize.build()'s own additive-plane try/except swallow it.
    ths_per_suite = view.per_suite.get(materialize.THS_SUITE)
    if ths_per_suite is None:
        log.error("theme graph: THS membership plane did not run — refusing to "
                  "build (a swallowed exception here must not look like a "
                  "legitimate zero-membership night)")
        return 1

    # B1: retract the superseded membership_doc.v1 THS MEMBER_OF generation so the
    # PIT re-key cannot leave both generations live. Retraction reuses the stored
    # edge_id and lands through changed_edges. MAJOR 1: only the (src, dst) pairs
    # the PIT plane actually re-observed are retracted — an uncovered pair is a
    # disclosed coverage gap, never a fabricated exit.
    belief_time = materialize.utc_today()
    pit_birth = materialize.ths_membership_pit_birth(ths_history)
    pit_pairs = {
        (str(e["src"]), str(e["dst"])) for e in view.edges
        if str(e.get("type")) == "MEMBER_OF"
        and str(e.get("confidence_basis")) == "membership_pit.ths.v1"
    }
    run_computed_at = (view.edges[0]["computed_at"]
                       if view.edges else materialize.utc_now_stamp())
    membership_closings: list[dict] = []
    if pit_birth and not stored.empty:
        membership_closings = materialize.supersede_ths_membership_doc_edges(
            stored, valid_to=pit_birth, belief_time=belief_time, era=era,
            computed_at=run_computed_at, pit_pairs=pit_pairs)
        if membership_closings:
            log.info("THS membership_doc→pit cutover: retracting %d open membership_doc.v1 "
                     "MEMBER_OF edges covered by PIT history (valid_from=valid_to=%s)",
                     len(membership_closings), pit_birth)
    try:
        expression_closings = materialize.supersede_ths_canonical_expression_edges(
            stored, view.edges, belief_time=belief_time, era=era,
            computed_at=run_computed_at)
    except ValueError as exc:
        log.error("theme graph: THS canonical expression supersession refused (%s)", exc)
        return 1
    if expression_closings:
        log.info("THS canonical expression refresh: closing %d superseded live edge(s)",
                 len(expression_closings))
    try:
        event_path, curation_path = _relation_event_sources()
        relation_events = probation.read_relation_events(
            event_path, source_path=curation_path, emitted_at=run_computed_at,
            owner_action_reader=_relation_action_owner_reader())
        event_closings, event_evidence = materialize.apply_relation_events(
            stored, view.edges, relation_events, belief_time=belief_time,
            era=era, computed_at=run_computed_at)
    except (ValueError, OSError) as exc:
        log.error("theme graph: owner relation event refused (%s)", exc)
        return 1
    view.evidence.extend(event_evidence)
    closings = membership_closings + expression_closings + event_closings
    computed = list(view.edges) + closings
    edges = computed if backfill else materialize.changed_edges(computed, stored)

    # SECOND WALL (§2). The refresh contract's interlocks guard the path a refresh takes;
    # this one guards the path every WRITE takes, so a hand-edited or truncated input
    # that never went through a refresh still cannot mass-close a source family. Refusing
    # here is cheap; un-closing 2,000 permanent rows in an append-only store is not.
    # Only exact validated owner closures and superseded legacy rows are explained
    # changes. Uncovered pairs and collateral loss still enter the shrink numerator.
    allow = set(allow_source_shrink)
    # The guard derives exact explained legacy/PIT closures from this same
    # validated owner input. A THS cutover never waives collateral loss.
    refusals = materialize.source_shrink_refusals(
        edges, stored, allow=allow, owner_membership_history=ths_history)
    if refusals:
        for r in refusals:
            log.error("theme graph shrink wall: %s", r)
        print("::warning title=theme graph source shrink refused::" + "; ".join(refusals),
              flush=True)
        return 1

    log.info("theme graph computed: %d nodes, %d edges (%d to append), %d evidence rows, "
             "%d capability rows %s, %d identity resolution rows %s; era=%s lane=%r",
             len(view.nodes), len(view.edges), len(edges), len(view.evidence),
             len(view.capability), _capability_counts(view.capability),
             len(view.identity_resolution),
             _identity_resolution_state_counts(view.identity_resolution), era, lane)
    if view.company_mint_refusals:
        # V4-D2B3 — a titled ::notice, never a warning: a refused mint is the fence
        # WORKING, not a failure. Bare print, line-start, flushed (GitHub annotation law).
        log.info("  %d company mint refusal(s): %s", len(view.company_mint_refusals),
                 json.dumps(view.company_mint_refusals, ensure_ascii=False, sort_keys=True)[:600])
        print("::notice title=theme graph — company mint refusal(s)::"
              + json.dumps(view.company_mint_refusals, ensure_ascii=False, sort_keys=True),
              flush=True)
    for family, report in sorted(view.local_plane.items()):
        log.info("  local plane %s: %s", family, json.dumps(report, ensure_ascii=False,
                                                            sort_keys=True)[:600])
    for suite, why in sorted(view.skipped_suites.items()):
        log.info("  suite %s skipped: %s", suite, why)
    if view.unknown_ths_codes:
        # Weekly THS concept drift. Reported, never fatal — a renamed board is not a
        # broken build, and a build that died on one would take the whole plane down
        # every time 同花顺 reorganised its taxonomy.
        log.info("  %d crosswalk THS code(s) not in the current concept map: %s",
                 len(view.unknown_ths_codes), ", ".join(view.unknown_ths_codes))

    allow = bool(backfill)
    added_nodes = store.write_nodes(view.nodes, lane=lane, allow_backfill=allow)
    added_ev = store.write_evidence(view.evidence, lane=lane, allow_backfill=allow)
    added_edges = store.write_edges(edges, lane=lane, allow_backfill=allow)
    # Re-derived every run, never carried forward: a node whose price coverage improved
    # is re-classified UP tonight, which is the whole reason capability is a side-car and
    # not a write-once node column.
    added_cap = store.write_capability(view.capability, lane=lane, allow_backfill=allow)
    # V4-D2A: same re-derivation discipline — a node NOT_IN_MASTER tonight may resolve
    # tomorrow as the Data OS master's coverage grows.
    added_idres = store.write_identity_resolution(view.identity_resolution, lane=lane,
                                                   allow_backfill=allow)

    meta = {
        "computed_at": materialize.utc_now_stamp(),
        "engine_version": store.ENGINE_VERSION,
        "mode": "backfill" if backfill else "nightly",
        "era": era,
        "belief_time": materialize.utc_today(),
        "lane": lane,
        "counts": {
            "nodes": int(len(store.read_nodes())),
            "edges": int(len(store.read_edges(latest_belief=False))),
            "edges_latest_belief": int(len(store.read_edges())),
            "evidence": int(len(store.read_evidence())),
            "capability": int(len(store.read_capability())),
            "identity_resolution": int(len(store.read_identity_resolution())),
            # V4-D2B3 — current-view row count (one per node with a lifecycle act);
            # the nightly bake never WRITES this table (R-D2B3-5), only reads it.
            "node_lifecycle": int(len(store.read_node_lifecycle())),
        },
        "rows_appended": {"nodes": added_nodes, "edges": added_edges,
                          "evidence": added_ev, "capability": added_cap,
                          "identity_resolution": added_idres},
        "identity_resolution_state_counts":
            _identity_resolution_state_counts(view.identity_resolution),
        "per_suite": view.per_suite,
        "skipped_suites": view.skipped_suites,
        "ths_unmapped_concept_count": view.ths_unmapped_concept_count,
        "unknown_ths_codes": view.unknown_ths_codes,
        # The local plane's own report: the vintage ladder it read, and the company-mint
        # resolution table printed rather than estimated (§9.13).
        "local_plane": view.local_plane,
        "unknown_ths_concepts": view.unknown_ths_concepts,
        "capability_counts": _capability_counts(view.capability),
        # V4-D2B3 (R-D2B3-4 / R-A1) — one typed refusal per structurally-suppressed
        # company mint this build. Empty on every night nothing tried to re-mint a
        # corrected symbol; present and non-empty is the resurrection fence WORKING.
        "company_mint_refusals": view.company_mint_refusals,
    }
    if store.write_meta(meta, lane=lane, allow_backfill=allow):
        log.info("wrote %s — appended %d nodes / %d edges / %d evidence rows",
                 store.meta_path(), added_nodes, added_edges, added_ev)
        _emit_meta_write_receipt(meta, run_computed_at)
    else:
        log.info("off-lane: computed %d nodes / %d edges / %d evidence rows and wrote "
                 "nothing (COLLECT_LANE=%r)", len(view.nodes), len(edges),
                 len(view.evidence), lane)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--backfill", action="store_true",
                    help="one-shot era=reconstruction build of the whole graph")
    ap.add_argument("--force-backfill", action="store_true",
                    help="allow --backfill over a populated edge store (rarely right)")
    ap.add_argument("--allow-source-shrink", action="append", default=[],
                    metavar="FAMILY",
                    help="permit this source family's live memberships to shrink past "
                         "the wall (repeatable). For a REAL vendor restructure — the "
                         "flag exists so the decision has a name attached")
    a = ap.parse_args(argv)
    try:
        return run(backfill=a.backfill, force_backfill=a.force_backfill,
                   allow_source_shrink=tuple(a.allow_source_shrink))
    except Exception:  # noqa: BLE001 — display-tier plane; never break the collect lane
        log.exception("theme graph build failed")
        print("::warning title=theme graph build failed::"
              "scripts.build_theme_graph raised; the graph plane is stale for this run. "
              "Display-tier only — no decision path depends on it — but a repeat means "
              "the membership/crosswalk inputs moved under it.", flush=True)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

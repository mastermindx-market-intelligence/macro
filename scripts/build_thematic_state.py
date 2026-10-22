"""scripts/build_thematic_state.py — TIL W0 Thematic State builder.

Mirrors scripts/build_mechanism_pathways.py conventions.

Writes:
    data/neuralweb/theme_state.json          (primary; git-committed)
    site/neuralwebdata/theme_state.json      (site mirror)
    data/neuralweb/theme_phase_history.jsonl (append-only PIT tape; nightly sole advancer)

Display/context tier only. Authority block: is_context_only=True, all promotion flags False.
Fail-open: missing source → stale_legs entry + null block; always exits 0.
Composition is adapter-cheap (reads existing committed artifacts only — no network calls).

Runs AFTER build_foresight and build_baskets steps in the engine lane.

Usage:
    python -m scripts.build_thematic_state [--root /path/to/repo]
    python -m scripts.build_thematic_state --mode GRAPH_SHADOW_STATE   # gate #8 shadow only
    python -m scripts.build_thematic_state --mode ACTIVITY_MEMBERSHIP_STATE   # activity fold only
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import tempfile
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent
sys.path.insert(0, str(_REPO_ROOT))

from engine.neuralweb.thematic_state import compose, append_phase_history
from engine.neuralweb.envelope import stamp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("build_thematic_state")

_ARTIFACT_ID = "theme-state"
_DATA_PATH = "data/neuralweb/theme_state.json"
_SITE_PATH = "site/neuralwebdata/theme_state.json"
_HISTORY_PATH = "data/neuralweb/theme_phase_history.jsonl"
_SHADOW_GRAPH_STATE_PATH = "data/theme_graph/shadow_theme_state.v1.json"
# Seat ruling G1-RC1 (2026-10-06): the graph theme_state/v1 shadow for the
# selection_cohort_reads owner is its own narrow mode, run off-render
# (daily.yml oracle_offrender), never inside LEGACY / the engine job.
_GRAPH_SHADOW_STATE_MODE = "GRAPH_SHADOW_STATE"
# ORCH-PIPE GMI M2 step 1 (2026-10-22): the activity-membership history fold runs in
# the sole producer through its own narrow mode — fold the committed events, project
# the CURRENT beliefs, and write ONE display/diagnostic artifact, the way the shadow
# mode above writes its one shadow. NOT_QUALIFIED by construction (D2E eligibility is
# separately unsealed); LEGACY never runs the fold and gains no new input.
_ACTIVITY_MEMBERSHIP_STATE_MODE = "ACTIVITY_MEMBERSHIP_STATE"
_ACTIVITY_MEMBERSHIP_STATE_PATH = "data/theme_graph/activity_membership_state.v1.json"
_ACTIVITY_HISTORY_EVENTS_PATH = "data/theme_graph/probation/activity_history_events.jsonl"


def _jsonable(value):
    """Plain-JSON conversion for pandas NaN/NaT/numpy leakage on read-back rows."""
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, float) and value != value:  # NaN
        return None
    if value is not None and hasattr(value, "item"):
        try:
            return _jsonable(value.item())
        except (ValueError, AttributeError):  # noqa: TRY300 — keep the raw object
            pass
    if value is not None and hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _peak_rss_mib() -> str:
    try:
        import resource

        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return f"{peak / (1024 * 1024 if sys.platform == 'darwin' else 1024):.0f}"
    except Exception:  # noqa: BLE001 - telemetry only
        return "na"


def _write_shadow_graph_state(root: Path, generated_at: str | None) -> bool:
    """Capture -> state-only compose -> validate -> atomic write of the shadow ONLY.

    Fail-open: any failure prints one ::warning and leaves the prior shadow untouched.
    """
    from datetime import datetime, timezone

    from engine.neuralweb import theme_state_adapter as adapter
    from engine.neuralweb import theme_state_generation as generation
    from engine.theme_graph import theme_state
    from engine.theme_graph.theme_state_owner_readers import StateQualificationReader

    capture_s = compose_s = serialize_s = None
    raw = None
    try:
        phase_started = time.perf_counter()
        known_at = generated_at or datetime.now(timezone.utc).isoformat()
        bundle = adapter.capture_owner_bundle(
            root, owner_readers=StateQualificationReader(root),
            effective_at=known_at[:10], known_at=generated_at,
        )
        capture_s = time.perf_counter() - phase_started

        phase_started = time.perf_counter()
        emitted_at = generated_at or datetime.now(timezone.utc).isoformat()
        state = adapter.compose_state_only_from_owner_bundle(bundle, generated_at=emitted_at)
        compose_s = time.perf_counter() - phase_started

        phase_started = time.perf_counter()
        theme_state.validate_state(state)
        assert state.get("schema") == theme_state.SCHEMA
        raw = json.dumps(
            state, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False,
        ).encode("utf-8") + b"\n"
        serialize_s = time.perf_counter() - phase_started

        with generation.family_lock(root):
            generation.write_atomic(root, _SHADOW_GRAPH_STATE_PATH, raw)
        return True
    except Exception as exc:
        msg = str(exc).splitlines()[0][:300] if str(exc) else ""
        log.warning(
            "shadow graph state failed: %s: %s", type(exc).__name__, exc,
        )
        print(
            f"::warning title=gmi-shadow-graph-state::{type(exc).__name__}: {msg}",
            flush=True,
        )
        return False
    finally:
        print(
            "[thematic_state] shadow_graph_state timing "
            + (f"capture_s={capture_s:.3f}" if capture_s is not None else "capture_s=na")
            + " "
            + (f"compose_s={compose_s:.3f}" if compose_s is not None else "compose_s=na")
            + " "
            + (f"serialize_s={serialize_s:.3f}" if serialize_s is not None else "serialize_s=na")
            + " "
            + (f"bytes={len(raw)}" if raw is not None else "bytes=na")
            + f" peak_rss_mib={_peak_rss_mib()}",
            flush=True,
        )


def _write_activity_membership_state(root: Path, generated_at: str | None) -> bool:
    """Fold -> project -> atomic write of the activity-membership state ONLY.

    Fail-open: any failure prints one ::warning and leaves the prior artifact untouched.
    """
    from datetime import datetime, timezone

    import hashlib

    from engine.neuralweb import theme_state_generation as generation
    from engine.theme_graph import materialize, store

    read_s = fold_s = serialize_s = None
    raw = None
    try:
        phase_started = time.perf_counter()
        stamp = generated_at or datetime.now(timezone.utc).isoformat()
        # The producer never reads a graph outside its own root.
        if store.store_dir().resolve() != (Path(root) / "data" / "theme_graph").resolve():
            raise RuntimeError(
                "GRAPH_STORE_ROOT_MISMATCH: "
                f"store_dir={store.store_dir()} root={Path(root)}")
        events_path = Path(root) / _ACTIVITY_HISTORY_EVENTS_PATH
        try:
            events_bytes = events_path.read_bytes()
        except FileNotFoundError:
            events_bytes = None
        if events_bytes is None:
            events, events_sha256 = [], None
        else:
            events_sha256 = hashlib.sha256(events_bytes).hexdigest()
            events = []
            for lineno, line in enumerate(events_bytes.decode("utf-8").splitlines(), start=1):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except ValueError as exc:
                    raise ValueError(
                        f"ACTIVITY_EVENTS_FILE_INVALID: line {lineno}: {exc}") from exc
                if not isinstance(event, dict):
                    raise ValueError(f"ACTIVITY_EVENTS_FILE_INVALID: line {lineno}")
                events.append(event)
        edges_df = store.read_edges(latest_belief=True, strict=True)
        nodes_df = store.read_nodes(strict=True)
        read_s = time.perf_counter() - phase_started

        phase_started = time.perf_counter()
        fold = materialize.apply_activity_membership_events(events, knowledge_cutoff=stamp)
        node_ids = {str(node_id) for node_id in nodes_df["node_id"].tolist()
                    if isinstance(node_id, str)}
        existing_edge_ids = {
            str(edge_id) for edge_id in edges_df.loc[
                edges_df["date_provenance"] != "activity_history", "edge_id"].tolist()
            if isinstance(edge_id, str)}
        edges_rows, evidence_rows, projection_refusals = (
            materialize.project_activity_memberships(
                fold, events=events, belief_time=stamp[:10], era="observed",
                computed_at=stamp, node_ids=node_ids, edge_ids=existing_edge_ids))
        activity_mask = (
            (edges_df["type"] == "MEMBER_OF")
            & (edges_df["date_provenance"] == "activity_history")
            & edges_df["valid_to"].isna())
        graph_activity = {str(edge_id) for edge_id in edges_df.loc[
            activity_mask, "edge_id"].tolist() if isinstance(edge_id, str)}
        projected_ids = {str(row["edge_id"]) for row in edges_rows}
        missing_in_graph = sorted(projected_ids - graph_activity)
        extra_in_graph = sorted(graph_activity - projected_ids)
        graph_agreement = {
            "rule": "latest_belief MEMBER_OF activity_history valid_to null",
            "status": "AGREE" if projected_ids == graph_activity else "DISAGREE",
            "graph_activity_count": len(graph_activity),
            "projected_count": len(projected_ids),
            "missing_in_graph": missing_in_graph[:50],
            "missing_in_graph_count": len(missing_in_graph),
            "extra_in_graph": extra_in_graph[:50],
            "extra_in_graph_count": len(extra_in_graph),
        }
        fold_s = time.perf_counter() - phase_started

        phase_started = time.perf_counter()
        payload = {
            "schema": "gmi.activity_membership_state/v1",
            "generated_at": stamp,
            "mode": _ACTIVITY_MEMBERSHIP_STATE_MODE,
            "events_path": _ACTIVITY_HISTORY_EVENTS_PATH,
            "events_sha256": events_sha256,
            "event_count": len(events),
            "fold": {
                "current": len(fold["current"]), "history": len(fold["history"]),
                "retained": len(fold["retained"]), "refused": len(fold["refused"]),
                "excluded_after_cutoff": len(fold["excluded_after_cutoff"]),
                "refused_rows": fold["refused"],
            },
            "projected_edges": [_jsonable(row) for row in edges_rows],
            "projected_evidence_count": len(evidence_rows),
            "projection_refusals": [_jsonable(row) for row in projection_refusals],
            "graph_agreement": graph_agreement,
            "qualification": {"status": "NOT_QUALIFIED",
                              "reason_codes": ["D2E_UNSEALED"]},
            "authority": {"may_rank": False, "may_size": False, "may_gate": False,
                          "may_publish": False, "may_materialize_edges": False,
                          "may_qualify": False},
        }
        raw = json.dumps(
            payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False,
        ).encode("utf-8") + b"\n"
        serialize_s = time.perf_counter() - phase_started

        with generation.family_lock(root):
            generation.write_atomic(root, _ACTIVITY_MEMBERSHIP_STATE_PATH, raw)
        return True
    except Exception as exc:
        msg = str(exc).splitlines()[0][:300] if str(exc) else ""
        log.warning(
            "activity membership state failed: %s: %s", type(exc).__name__, exc,
        )
        print(
            f"::warning title=gmi-activity-membership-state::{type(exc).__name__}: {msg}",
            flush=True,
        )
        return False
    finally:
        print(
            "[thematic_state] activity_membership_state timing "
            + (f"read_s={read_s:.3f}" if read_s is not None else "read_s=na")
            + " "
            + (f"fold_s={fold_s:.3f}" if fold_s is not None else "fold_s=na")
            + " "
            + (f"serialize_s={serialize_s:.3f}" if serialize_s is not None else "serialize_s=na")
            + " "
            + (f"bytes={len(raw)}" if raw is not None else "bytes=na")
            + f" peak_rss_mib={_peak_rss_mib()}",
            flush=True,
        )


def _atomic_write_json(path: Path, payload: dict) -> None:
    """Write JSON atomically via temp-file + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".tmp_{path.name}_",
        suffix=".json",
        delete=False,
    ) as tf:
        tf.write(text)
        tmp_path = Path(tf.name)
    tmp_path.replace(path)


def build(root: Path, *, mode: str = "LEGACY", bundle=None,
          generated_at: str | None = None) -> int:
    """Sole producer; legacy default, read-only shadow, held successor delivery."""
    from datetime import datetime, timezone
    from engine.neuralweb import theme_state_generation as generation
    root = Path(root)
    try:
        if mode not in {"LEGACY", "SHADOW", "SUCCESSOR", _GRAPH_SHADOW_STATE_MODE,
                        _ACTIVITY_MEMBERSHIP_STATE_MODE}:
            raise generation.GenerationUnavailable("UNKNOWN_SOURCE_MODE")
        if mode == _GRAPH_SHADOW_STATE_MODE:
            # Shadow only: no legacy entry preflight/CAS/compose/history, no optional stages.
            written = _write_shadow_graph_state(root, generated_at)
            print(f"[thematic_state] shadow_graph_state={'written' if written else 'skipped'}", flush=True)
            return 0
        if mode == _ACTIVITY_MEMBERSHIP_STATE_MODE:
            # Activity fold only: no legacy entry preflight/CAS/compose/history, no optional stages.
            written = _write_activity_membership_state(root, generated_at)
            print(f"[thematic_state] activity_membership_state={'written' if written else 'skipped'}", flush=True)
            return 0
        # Immutable entry preflight before ANY directory, temporary or output.
        entry = generation.entry_preflight(root, legacy_api=True)
        if mode != "LEGACY":
            from engine.neuralweb import theme_state_adapter as adapter
            now = generated_at or datetime.now(timezone.utc).isoformat()
            if bundle is None:
                bundle = adapter.capture_owner_bundle(root, effective_at=now[:10], known_at=now)
            if mode == "SHADOW":
                result = adapter.compose_production_from_owner_bundle(bundle, generated_at=now)
                log.info("controlled same-input shadow: %s", result["shadow"]["production_binding"])
                return 0
            plan = generation.prepare_generation(bundle, root=root, generated_at=now,
                activation_at=now, entry=entry)
            # No CLI/caller mode injects a rights grant or the fixture-only verifier.
            generation.publish_generation(root, plan)
            return 0

        try:
            artifact = compose(root=root)
        except Exception as exc:  # legacy source fail-open remains, prior bytes do not
            log.error("compose() failed unexpectedly: %s", exc)
            artifact = {
                "schema": "neuralweb.theme_state.v1",
                "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "authority": {"is_context_only": True, "may_rank": False, "may_gate": False,
                              "may_size": False, "may_escalate": False},
                "themes": [], "stale_legs": [f"compose exception: {exc}"],
            }
        try:
            artifact = stamp(artifact, artifact_id=_ARTIFACT_ID)
        except Exception as exc:
            log.warning("envelope stamp failed (legacy non-fatal): %s", exc)
        now = datetime.now(timezone.utc).isoformat()
        tail, n_rows = generation.plan_phase_history(artifact, entry["history"], recorded_at=now)
        raw = json.dumps(artifact, ensure_ascii=False, indent=2, default=str, allow_nan=False).encode("utf-8")
        with generation.family_lock(root):
            generation.cas_entry(root, entry)
            if entry["current"] is not None:
                raise generation.GenerationUnavailable("ACCEPTED_GENERATION_REQUIRES_SUCCESSOR")
            generation.write_atomic(root, _DATA_PATH, raw)
            generation.write_atomic(root, _SITE_PATH, raw)
            from engine.neuralweb.thematic_state import _ledger_advance_enabled
            if _ledger_advance_enabled() and (tail or not entry["history_exists"]):
                generation.write_atomic(root, _HISTORY_PATH, entry["history"].raw + tail)
        print(f"[thematic_state] legacy accepted; phase_history +{n_rows if _ledger_advance_enabled() else 0}", flush=True)
        return 0
    except Exception as exc:
        log.error("ThemeState unaccepted: %s", exc)
        return 1


# ── Optional TIL stages (W1/W2/W3) — auto-discovered, tolerant ────────────
# Contract (TIL PR-0): each stage module exposes `run_stage(root: Path) -> None`,
# owns its own artifacts (paths pre-registered in config/synapse.yml), never
# raises fatally, and stays display/context tier. Stages land in later waves;
# absence is a skip, not an error. This dispatcher exists so the W1/W2/W3
# builder lanes never have to edit this script (or daily.yml/dag.yml)
# concurrently — zero shared-file merge races.
_OPTIONAL_STAGES = (
    "engine.neuralweb.theme_thesis",     # W1 (PR-C) thesis ledger
    "engine.neuralweb.theme_pathways",   # W2 (PR-D) beneficiary/loser pathway graph
    "engine.neuralweb.theme_asymmetry",  # W3 (PR-E) per-leg asymmetry panel
)


def run_optional_stages(root: Path) -> None:
    """Run any present optional TIL stage modules. Absent module → skip."""
    import importlib

    for mod_name in _OPTIONAL_STAGES:
        try:
            mod = importlib.import_module(mod_name)
        except ImportError:
            log.info("optional stage %s absent — skipped", mod_name)
            continue
        fn = getattr(mod, "run_stage", None)
        if fn is None:
            log.warning("optional stage %s has no run_stage() — skipped", mod_name)
            continue
        t0 = time.perf_counter()
        try:
            fn(root)
            log.info("stage %s done in %.2fs", mod_name, time.perf_counter() - t0)
        except Exception as exc:  # noqa: BLE001
            log.error("stage %s failed (non-fatal): %s", mod_name, exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build thematic state artifacts (TIL W0)")
    parser.add_argument(
        "--root", default=None,
        help="Repo root path (default: inferred from script location)",
    )
    parser.add_argument("--mode", choices=("LEGACY", "SHADOW", "SUCCESSOR", _GRAPH_SHADOW_STATE_MODE,
                                           _ACTIVITY_MEMBERSHIP_STATE_MODE),
                        default="LEGACY")
    args = parser.parse_args()
    root = Path(args.root).resolve() if args.root else _REPO_ROOT
    code = build(root, mode=args.mode)
    if code == 0 and args.mode == "LEGACY":
        run_optional_stages(root)
    sys.exit(code)


if __name__ == "__main__":
    main()

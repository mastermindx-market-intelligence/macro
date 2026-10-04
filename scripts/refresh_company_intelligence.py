"""Refresh and safely promote the Company Intelligence read model.

This is the small, off-render producer bridge between the two source-of-truth
planes and the public Company Intelligence API:

* the immutable earnings score/history generation in R2; and
* Terminal's ``/data/tx/index.json`` commit marker.

It intentionally has no model call.  A new score/history generation or a new
Terminal transcript index is enough to deterministically rebuild the company
views.  Source retrieval, local validation, immutable generation validation,
and the root-manifest promotion happen in that order.  If any prerequisite is
unavailable, the prior published marker is left untouched.

The script owns only a temporary child of ``--work-dir``.  It never writes the
git checkout's data directory, so a scheduled run cannot create a backfill
ledger or interfere with the nightly render lane.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
from typing import Any, Callable, Mapping
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.company_intelligence.health import validate_generation
from engine.earnings_transcript_intake import parse_global_index
from scripts.build_company_intelligence import main as build_company_intelligence
from scripts.fetch_earnings_scores import (
    _manifest_contract,
    _validate_parquet,
    fetch as fetch_earnings_scores,
)
from scripts.publish_company_intelligence_r2 import PUBLISH_CONFLICT, publish


DEFAULT_TX_INDEX_URL = "https://app.mastermind-x.com/data/tx/index.json"
# The standalone earnings worker runs three times after the close and can drain
# hundreds of calls per invocation. A >3-calendar-day gap between Terminal's
# causal call tape and the newest healthy Terminal-linked score is therefore a
# producer outage, not ordinary scheduling jitter. Keep this deliberately much
# looser than the worker's expected same-evening cadence to avoid weekend noise.
DEFAULT_SCORE_MAX_LAG_DAYS = 3
SCORE_FRESHNESS_STALE = 3


class RefreshError(RuntimeError):
    """A source is unavailable or invalid; retaining the last root marker is safer."""


class ScoreFreshnessError(RefreshError):
    """The score plane is structurally valid but too stale to advance v1."""


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    temporary.replace(path)


def fetch_transcript_index(
    url: str,
    destination: Path,
    *,
    opener: Callable[..., Any] = urlopen,
    timeout_seconds: float = 25.0,
) -> dict[str, Any]:
    """Fetch and schema-check Terminal's commit marker before persisting it.

    The score worker treats this index as its atomic reader-visible commit
    marker.  We use the exact same parser here so a malformed or partial HTTP
    response never manufactures a degraded Company Intelligence generation.
    """
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "mastermind-company-intelligence/1"})
    try:
        response = opener(request, timeout=timeout_seconds)
        with closing(response):
            raw = response.read()
        payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - network errors must retain last-good marker
        raise RefreshError(f"terminal transcript index unavailable: {exc}") from exc
    try:
        refs, metadata = parse_global_index(payload)
    except Exception as exc:  # noqa: BLE001 - parser owns the strict v1 contract
        raise RefreshError(f"terminal transcript index invalid: {exc}") from exc
    if not isinstance(payload, dict):  # parse_global_index currently guarantees this; keep the write contract explicit.
        raise RefreshError("terminal transcript index must be a JSON object")
    _write_json(destination, payload)
    print(
        "company intelligence: terminal transcript index "
        f"symbols={metadata['symbol_count']} bodies={len(refs)} generated_at={metadata['generated_at'] or 'unknown'}"
    )
    return payload


def ensure_earnings_inputs(data_dir: Path) -> dict[str, Any]:
    """Require the same complete, validated earnings generation as Stage Analysis.

    ``fetch_earnings_scores`` is intentionally fail-soft for the render lane.
    This producer cannot be fail-soft: publishing an empty/partial tree would
    hide a healthy last-good generation, so its follow-up gate is fail-closed.
    """
    earnings_dir = data_dir / "earnings_calls"
    manifest_path = earnings_dir / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise RefreshError(f"earnings manifest unavailable after fetch: {exc}") from exc
    valid, reason = _manifest_contract(manifest if isinstance(manifest, dict) else None)
    if not valid or not isinstance(manifest, dict):
        raise RefreshError(f"earnings manifest rejected after fetch: {reason or 'invalid'}")
    for name, filename in (("scores", "scores.parquet"), ("history", "history.parquet")):
        block = manifest.get(name)
        if not isinstance(block, dict):
            raise RefreshError(f"earnings {name} block missing; full history is required")
        path = earnings_dir / filename
        if not path.is_file():
            raise RefreshError(f"earnings {filename} missing after fetch")
        healthy, why = _validate_parquet(path, block, name)
        if not healthy:
            raise RefreshError(f"earnings {filename} invalid after fetch: {why}")
    return manifest



def _parse_as_of_day(value: str | date) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError as exc:
        raise RefreshError(f"invalid freshness as_of date: {value!r}") from exc


def _context_only_true(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def assert_earnings_score_freshness(
    data_dir: Path,
    terminal_index: Mapping[str, Any],
    *,
    as_of: str | date,
    max_lag_days: int = DEFAULT_SCORE_MAX_LAG_DAYS,
) -> dict[str, Any]:
    """Refuse a silently dead qualitative-score producer before publication.

    Integrity alone is insufficient: a byte-valid R2 score generation can stay
    frozen for weeks while Terminal continues publishing transcripts. Compare
    only causal Terminal dates (never future-labelled rows) with healthy
    *Terminal-linked transcript* scores. Degraded provider receipts, 8-K rows,
    and legacy rows without a stable Terminal record id cannot make the producer
    look fresh.

    This is intentionally a coarse dead-producer tripwire, not a coverage SLA.
    It does not require every recent transcript to have scored; that remains the
    worker queue/retry owner's job.
    """

    if max_lag_days < 0:
        raise ValueError("max_lag_days must be >= 0")
    as_of_day = _parse_as_of_day(as_of)
    try:
        refs, metadata = parse_global_index(terminal_index)
    except Exception as exc:  # noqa: BLE001 - same strict source contract
        raise RefreshError(f"terminal transcript index invalid for freshness check: {exc}") from exc

    terminal_days = [
        date.fromisoformat(ref.call_date)
        for ref in refs
        if ref.call_date and date.fromisoformat(ref.call_date) <= as_of_day
    ]
    if not terminal_days:
        report = {
            "state": "not_observed",
            "as_of": as_of_day.isoformat(),
            "terminal_generated_at": metadata.get("generated_at") or None,
            "terminal_latest_call_date": None,
            "score_latest_call_date": None,
            "lag_days": None,
            "max_lag_days": int(max_lag_days),
        }
        print("company intelligence: earnings score freshness " + json.dumps(report, sort_keys=True))
        return report

    scores_path = Path(data_dir) / "earnings_calls" / "scores.parquet"
    try:
        import pandas as pd  # noqa: PLC0415

        scores = pd.read_parquet(scores_path)
    except Exception as exc:  # noqa: BLE001
        raise RefreshError(f"earnings score freshness unreadable: {exc}") from exc

    required = {"call_date", "source", "source_record_id", "sentiment", "performance", "confidence"}
    missing = sorted(required - set(scores.columns))
    if missing:
        raise RefreshError(
            "earnings score freshness missing required column(s): " + ", ".join(missing)
        )

    healthy = scores.copy()
    if "degraded_reason" in healthy.columns:
        healthy = healthy[
            healthy["degraded_reason"].fillna("").astype(str).str.strip().eq("")
        ]
    if "is_context_only" in healthy.columns:
        healthy = healthy[healthy["is_context_only"].map(_context_only_true)]
    healthy = healthy[
        healthy["source"].fillna("").astype(str).str.strip().str.lower().eq("transcript")
    ]
    healthy = healthy[
        healthy["source_record_id"].fillna("").astype(str).str.startswith("defeatbeta:")
    ]
    for field in ("sentiment", "performance", "confidence"):
        healthy = healthy[pd.to_numeric(healthy[field], errors="coerce").notna()]

    score_days = pd.to_datetime(healthy["call_date"], errors="coerce", utc=True)
    causal_score_days = score_days[
        score_days.notna() & score_days.dt.date.le(as_of_day)
    ]
    terminal_latest = max(terminal_days)
    score_latest = (
        causal_score_days.max().date()
        if len(causal_score_days)
        else None
    )
    lag_days = (
        max(0, (terminal_latest - score_latest).days)
        if score_latest is not None
        else None
    )
    report = {
        "state": "fresh" if lag_days is not None and lag_days <= max_lag_days else "stale",
        "as_of": as_of_day.isoformat(),
        "terminal_generated_at": metadata.get("generated_at") or None,
        "terminal_latest_call_date": terminal_latest.isoformat(),
        "score_latest_call_date": score_latest.isoformat() if score_latest else None,
        "lag_days": lag_days,
        "max_lag_days": int(max_lag_days),
    }
    print("company intelligence: earnings score freshness " + json.dumps(report, sort_keys=True))
    if score_latest is None:
        raise ScoreFreshnessError(
            "earnings score freshness stale: Terminal has causal calls but no "
            "healthy Terminal-linked transcript score is observable"
        )
    if lag_days is not None and lag_days > max_lag_days:
        raise ScoreFreshnessError(
            "earnings score freshness stale: newest healthy Terminal-linked score "
            f"{score_latest.isoformat()} lags newest causal Terminal call "
            f"{terminal_latest.isoformat()} by {lag_days} calendar days "
            f"(max {max_lag_days})"
        )
    return report


def refresh(
    work_dir: Path,
    *,
    tx_index_url: str = DEFAULT_TX_INDEX_URL,
    as_of: str | None = None,
    dry_run: bool = False,
    out_dir: Path | None = None,
    fetch_scores: Callable[..., int] = fetch_earnings_scores,
    publish_generation: Callable[..., int] = publish,
) -> int:
    """Fetch → build → integrity-check → promote one safe generation.

    ``PUBLISH_CONFLICT`` is returned unchanged for the caller to classify as a
    safe lost compare-and-swap race (not a partial publication).
    """
    root = Path(work_dir)
    root.mkdir(parents=True, exist_ok=True)
    run_as_of = as_of or datetime.now(timezone.utc).date().isoformat()
    with tempfile.TemporaryDirectory(prefix="company-intelligence-", dir=root) as temporary:
        scratch = Path(temporary)
        source_dir = scratch / "source"
        # The normal producer owns a disposable output tree. A dependent,
        # post-publication sidecar may request an explicit handoff directory so
        # it can verify the *same* immutable CIE marker/tree after this refresh
        # has promoted it. Source inputs remain temporary in every mode.
        output_dir = Path(out_dir) if out_dir is not None else scratch / "output"
        rc = fetch_scores(data_dir=source_dir, dry_run=False)
        if rc != 0:
            raise RefreshError(f"earnings fetch failed with exit code {rc}")
        ensure_earnings_inputs(source_dir)
        tx_index = scratch / "tx-index.json"
        tx_payload = fetch_transcript_index(tx_index_url, tx_index)
        score_freshness_error: ScoreFreshnessError | None = None
        try:
            assert_earnings_score_freshness(
                source_dir,
                tx_payload,
                as_of=run_as_of,
            )
        except ScoreFreshnessError as exc:
            # Keep building the validated output tree so the workflow can still
            # advance its path-independent event-workspace sibling before it
            # reports the stale score lane. The v1 marker itself remains held.
            score_freshness_error = exc
        earnings_dir = source_dir / "earnings_calls"
        build_rc = build_company_intelligence([
            "--scores", str(earnings_dir / "scores.parquet"),
            "--history", str(earnings_dir / "history.parquet"),
            "--earnings-manifest", str(earnings_dir / "manifest.json"),
            "--tx-index", str(tx_index),
            "--out-dir", str(output_dir),
            "--as-of", run_as_of,
        ])
        if build_rc != 0:
            raise RefreshError(f"company intelligence build failed with exit code {build_rc}")
        health = validate_generation(output_dir)
        if health["status"] != "ready":
            raise RefreshError(
                "company intelligence generation rejected: "
                + ", ".join(str(item) for item in health["warnings"])
            )
        print(
            "company intelligence: validated "
            f"generation={health.get('generation_id')} companies={health['company_count']} events={health['event_count']}"
        )
        if score_freshness_error is not None:
            print(
                "company intelligence: v1 root held for stale earnings score plane: "
                + str(score_freshness_error),
                file=sys.stderr,
            )
            return SCORE_FRESHNESS_STALE
        publish_rc = publish_generation(output_dir, dry_run=dry_run)
        if publish_rc == PUBLISH_CONFLICT:
            print("company intelligence: root-manifest promotion lost a safe compare-and-swap race")
        elif publish_rc != 0:
            raise RefreshError(f"company intelligence publish failed with exit code {publish_rc}")
        elif dry_run:
            print("company intelligence: dry-run validated; root manifest not promoted")
        else:
            print("company intelligence: immutable generation published and root marker promoted")
        return publish_rc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True, help="Scratch parent; only a temporary child is written")
    parser.add_argument("--terminal-tx-index-url", default=DEFAULT_TX_INDEX_URL)
    parser.add_argument("--as-of", default=None, help="ISO date used only for freshness status (default: current UTC date)")
    parser.add_argument("--out-dir", type=Path, default=None, help="Optional persistent validated generation handoff directory")
    parser.add_argument("--dry-run", action="store_true", help="Fetch/build/validate but do not promote the root marker")
    args = parser.parse_args(argv)
    try:
        return refresh(
            args.work_dir,
            tx_index_url=args.terminal_tx_index_url,
            as_of=args.as_of,
            dry_run=args.dry_run,
            out_dir=args.out_dir,
        )
    except RefreshError as exc:
        print(f"company intelligence: refresh refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

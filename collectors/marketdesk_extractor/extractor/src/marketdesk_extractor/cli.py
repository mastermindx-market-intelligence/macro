"""`marketdesk` command-line interface."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from . import db
from .config import Config
from .utils import get_logger, setup_logging

log = get_logger("cli")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _open_conn(cfg: Config):
    cfg.ensure_dirs()
    conn = db.connect(cfg.database_url)
    db.init_db(conn)
    return conn


def _with_client(cfg: Config, fn):
    """Open an authenticated browser session, build the client, call ``fn(conn, client)``."""
    from .auth import BrowserSession
    from .marketdesk import MarketDeskClient

    conn = _open_conn(cfg)
    with BrowserSession(cfg) as sess:
        if not sess.is_authenticated():
            log.error("Not authenticated. Run `marketdesk auth` and log in first.")
            return 2
        client = MarketDeskClient(sess.context, cfg)
        fn(conn, client)
    conn.close()
    return 0


# --- command handlers ------------------------------------------------------
def cmd_auth(cfg: Config, args) -> int:
    from .auth import run_auth_flow
    ok = run_auth_flow(cfg, timeout_s=args.timeout)
    print("Authenticated." if ok else "Auth failed / timed out.")
    return 0 if ok else 2


def cmd_discover(cfg: Config, args) -> int:
    from .discover import discover

    def go(conn, client):
        res = discover(cfg, conn, client, limit=args.limit,
                       since_hours=args.since_hours, backfill=args.backfill)
        print(res.summary())
    return _with_client(cfg, go)


def cmd_download(cfg: Config, args) -> int:
    from .download import download_pending

    def go(conn, client):
        res = download_pending(cfg, conn, client, limit=args.limit, force=args.force)
        print(res.summary())
    return _with_client(cfg, go)


def cmd_parse(cfg: Config, args) -> int:
    from .pipeline import parse_pending
    conn = _open_conn(cfg)
    res = parse_pending(cfg, conn, limit=args.limit)
    conn.close()
    print(res.summary())
    return 0


def cmd_upload(cfg: Config, args) -> int:
    from .pipeline import upload_pending
    conn = _open_conn(cfg)
    res = upload_pending(cfg, conn, limit=args.limit, force=args.force)
    conn.close()
    print(res.summary())
    return 0


def cmd_publish_vault(cfg: Config, args) -> int:
    from .pipeline import publish_vault_pending
    conn = _open_conn(cfg)
    if not cfg.vault_enabled:
        conn.close()
        print("vault disabled (set VAULT_ENABLED=true + VAULT_R2_BUCKET). no-op.")
        return 0
    res = publish_vault_pending(cfg, conn, limit=args.limit, force=args.force)
    conn.close()
    print(res.summary())
    return 0


def cmd_manifest(cfg: Config, args) -> int:
    from .pipeline import write_manifest
    conn = _open_conn(cfg)
    date_str = _today() if args.date in (None, "today") else args.date
    path = write_manifest(cfg, conn, date_str, upload=not args.no_upload)
    conn.close()
    print(f"wrote {path}")
    return 0


def cmd_run(cfg: Config, args) -> int:
    from .pipeline import run
    report = run(
        cfg, limit=args.limit, since_hours=args.since_hours, backfill=args.backfill,
        do_parse=not args.no_parse, do_upload=not args.no_upload,
        do_manifest=not args.no_manifest,
    )
    print(report.summary())
    return 0


def cmd_status(cfg: Config, args) -> int:
    conn = _open_conn(cfg)
    counts = db.counts_by_status(conn)
    last = db.get_meta(conn, "last_successful_run", "never")
    conn.close()
    total = sum(counts.values())
    print(f"papers total: {total}")
    for status, n in sorted(counts.items()):
        print(f"  {status:<14} {n}")
    print(f"last_successful_run: {last}")
    return 0


def cmd_storage_check(cfg: Config, args) -> int:
    status = cfg.assert_storage_ready()
    if status is None:
        print("external storage guard: disabled")
    else:
        print(status.describe())
    return 0


def cmd_cleanup(cfg: Config, args) -> int:
    from .cleanup import prune_local
    conn = _open_conn(cfg)
    res = prune_local(
        cfg, conn,
        older_than_days=args.older_than_days, dry_run=args.dry_run,
        require_r2=not args.no_require_r2, require_vault=args.require_vault,
        include_markdown=args.include_markdown, include_metadata=args.include_metadata,
    )
    conn.close()
    print(res.summary())
    return 0


def cmd_trickle(cfg: Config, args) -> int:
    from .trickle import run_trickle
    run_trickle(
        cfg, once=args.once, dry_run=args.dry_run,
        max_iterations=args.max_iterations,
    )
    return 0


def cmd_filter(cfg: Config, args) -> int:
    """Re-run the institution/topic exclusion rules over EXISTING papers.

    Re-runnable + idempotent. ``--dry-run`` computes + prints (per-reason counts,
    total excluded/restored, resulting kept candidates + kept/day, and ~8 sample
    titles per reason) and writes NOTHING.
    """
    from .filters import REASONS, default_tagged_patterns, reclassify

    conn = _open_conn(cfg)
    tagged = default_tagged_patterns() if cfg.exclude_title_patterns_enabled else []
    res = reclassify(
        conn,
        exclude_institutions=set(cfg.exclude_institutions),
        tagged_patterns=tagged,
        dry_run=args.dry_run,
    )
    conn.close()

    print(res.summary())
    print(
        f"  rules: {len(cfg.exclude_institutions)} excluded institutions, "
        f"title patterns {'ON' if cfg.exclude_title_patterns_enabled else 'OFF'}"
    )
    if args.dry_run:
        for reason in REASONS:
            titles = res.samples.get(reason, [])
            if not titles:
                continue
            print(f"  sample [{reason}] ({res.excluded_by_reason.get(reason, 0)} total):")
            for t in titles:
                print(f"    - {t}")
    return 0


def cmd_backlog(cfg: Config, args) -> int:
    """Report the deferred-papers ledger (what the download cap left behind).

    Read-only. ``--json PATH`` additionally dumps the FULL candidate list (not
    just the printed top N) as the input contract for future backfill tooling.
    """
    from .backlog import build_report, export_json, render
    from .utils import utc_now

    conn = _open_conn(cfg)
    rep = build_report(
        conn, utc_now(), new_window_hours=cfg.new_window_hours, top_n=args.top
    )
    conn.close()
    print(render(rep))
    if args.json:
        path = export_json(rep, args.json)
        print(f"\nwrote {path} ({rep.total} candidates)")
    return 0


def cmd_retry_failed(cfg: Config, args) -> int:
    conn = _open_conn(cfg)
    rows = db.get_by_status(conn, ["FAILED"])
    for r in rows:
        db.set_status(conn, r["blob_id"], "DISCOVERED", error_message=None)
    conn.close()
    print(f"reset {len(rows)} FAILED papers to DISCOVERED. "
          f"Run `marketdesk run` (or download/parse/upload) to retry.")
    return 0


# --- parser ----------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="marketdesk", description=__doc__)
    p.add_argument("--env", default=None, help="path to a .env file (default: ./.env)")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("auth", help="interactive login (headed), saves session profile")
    sp.add_argument("--timeout", type=int, default=300)
    sp.set_defaults(func=cmd_auth)

    sp = sub.add_parser("discover", help="find + score new papers (no download)")
    sp.add_argument("--limit", type=int, default=None)
    sp.add_argument("--since-hours", type=int, default=None)
    sp.add_argument("--backfill", action="store_true")
    sp.set_defaults(func=cmd_discover)

    sp = sub.add_parser("download", help="download pending blobs")
    sp.add_argument("--pending", action="store_true", help="(default) download pending")
    sp.add_argument("--limit", type=int, default=None)
    sp.add_argument("--force", action="store_true", help="also retry FAILED")
    sp.set_defaults(func=cmd_download)

    sp = sub.add_parser("parse", help="parse downloaded PDFs to markdown")
    sp.add_argument("--pending", action="store_true")
    sp.add_argument("--limit", type=int, default=None)
    sp.set_defaults(func=cmd_parse)

    sp = sub.add_parser("upload", help="upload artifacts to R2 (+Dropbox)")
    sp.add_argument("--pending", action="store_true")
    sp.add_argument("--limit", type=int, default=None)
    sp.add_argument("--force", action="store_true", help="re-upload even if key exists")
    sp.set_defaults(func=cmd_upload)

    sp = sub.add_parser("publish-vault",
                        help="publish COMPLETE papers to the Research Vault R2 bucket")
    sp.add_argument("--limit", type=int, default=None)
    sp.add_argument("--force", action="store_true",
                    help="re-publish even if the vault keys already exist")
    sp.set_defaults(func=cmd_publish_vault)

    sp = sub.add_parser("manifest", help="write (and upload) a daily JSONL manifest")
    sp.add_argument("--date", default="today", help="YYYY-MM-DD or 'today'")
    sp.add_argument("--no-upload", action="store_true")
    sp.set_defaults(func=cmd_manifest)

    sp = sub.add_parser("run", help="discover -> download -> parse -> upload -> manifest")
    sp.add_argument("--limit", type=int, default=None)
    sp.add_argument("--since-hours", type=int, default=None)
    sp.add_argument("--backfill", action="store_true")
    sp.add_argument("--no-parse", action="store_true")
    sp.add_argument("--no-upload", action="store_true")
    sp.add_argument("--no-manifest", action="store_true")
    sp.set_defaults(func=cmd_run)

    sp = sub.add_parser("cleanup", help="prune local PDFs already archived in R2 (reclaim disk)")
    sp.add_argument("--older-than-days", type=int, default=7,
                    help="only prune papers downloaded more than N days ago (default 7)")
    sp.add_argument("--dry-run", action="store_true", help="report what would be pruned; delete nothing")
    sp.add_argument("--no-require-r2", action="store_true",
                    help="prune even if not confirmed in R2 (unsafe; default requires R2 copy)")
    sp.add_argument("--require-vault", action="store_true",
                    help="prune only papers durable in the Research Vault bucket "
                         "(vault_key set); use when the main R2 archive is off")
    sp.add_argument("--include-markdown", action="store_true", help="also prune local .md files")
    sp.add_argument("--include-metadata", action="store_true", help="also prune local metadata .json files")
    sp.set_defaults(func=cmd_cleanup)

    sp = sub.add_parser(
        "trickle",
        help="demand-aware multi-account download loop (newest-first + backfill, "
             "never re-trips the rolling 24h cap)",
    )
    sp.add_argument("--once", action="store_true",
                    help="run a single tick then exit")
    sp.add_argument("--dry-run", action="store_true",
                    help="compute + print the per-account plan; download NOTHING")
    sp.add_argument("--max-iterations", type=int, default=None,
                    help="stop after N ticks (default: run forever)")
    sp.set_defaults(func=cmd_trickle)

    sp = sub.add_parser(
        "filter",
        help="re-run the institution/topic exclusion rules over existing papers "
             "(marks noise SKIPPED_EXCLUDED; restores rows that no longer match)",
    )
    sp.add_argument("--dry-run", action="store_true",
                    help="compute + print per-reason counts, kept/day, and sample "
                         "titles; write NOTHING")
    sp.set_defaults(func=cmd_filter)

    sp = sub.add_parser(
        "backlog",
        help="report the deferred-papers ledger (candidates the download cap "
             "left behind) — the backfill plan for when more accounts exist",
    )
    sp.add_argument("--top", type=int, default=30,
                    help="how many top-scoring candidates to print (default 30)")
    sp.add_argument("--json", default=None, metavar="PATH",
                    help="also write the FULL candidate list to a JSON file")
    sp.set_defaults(func=cmd_backlog)

    sp = sub.add_parser("status", help="show DB status counts")
    sp.set_defaults(func=cmd_status)

    sp = sub.add_parser(
        "storage-check",
        help="verify the configured external volume identity, paths, and free-space floor",
    )
    sp.set_defaults(func=cmd_storage_check)

    sp = sub.add_parser("retry-failed", help="reset FAILED papers for another attempt")
    sp.set_defaults(func=cmd_retry_failed)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    cfg = Config.from_env(args.env)
    try:
        cfg.ensure_dirs()
    except Exception as e:  # noqa: BLE001 - logging may live on the missing volume
        print(f"marketdesk storage preflight failed: {e}", file=sys.stderr)
        return 1
    setup_logging(cfg.log_dir, console=cfg.log_console)
    try:
        return args.func(cfg, args)
    except KeyboardInterrupt:
        log.warning("interrupted")
        return 130
    except Exception as e:  # noqa: BLE001
        log.exception("fatal: %s", e)
        if not cfg.log_console:
            print(f"marketdesk fatal: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
